#!/usr/bin/env python3
"""Test de mise en route — bouton GPIO qui bascule HP/casque à chaque appui.

Objectif : premier test simple du câblage bouton-poussoir (TICKET-091, pas
encore tranché entre GPIO direct / MCP23017 / Pico USB HID). Réutilise
`radio.php` (get_output/set_output) comme unique source de vérité pour l'état
audio — le script ne parle jamais directement à MPD, il appelle l'endpoint
déjà testé et utilisé par l'IHM enfant.

Câblage attendu (même convention que `GpioSignalMonitor` dans
battery_watchdog.py) : bouton entre le GPIO choisi (numérotation BCM) et la
masse (GND), pull-up interne activé → repos = HIGH, appui = LOW.

Détection par polling (lecture répétée de la broche), pas par interruption
(`add_event_detect`) : sur Raspberry Pi 5, la détection par interruption de
RPi.GPIO est peu fiable (puce GPIO RP1, mal supportée par cette bibliothèque)
— un premier appui pouvait être détecté puis plus aucun ensuite. Même
principe que `GpioSignalMonitor` (battery_watchdog.py), avec un intervalle de
polling bien plus rapide (10ms par défaut), adapté à un appui humain.

Antirebond à trois niveaux — volontairement redondant, un seul rebond
parasite suffit à rendre le truc pénible à l'usage :
  1. Polling rapproché (`--poll-ms`) : détecte le front descendant dès qu'il
     apparaît, sans dépendre d'une interruption matérielle.
  2. Confirmation logicielle : après un front descendant, on attend un court
     instant puis on relit la broche — si elle n'est plus à l'état bas, le
     front était du bruit, on annule sans rien faire.
  3. Garde-fou global : même si (1) et (2) laissaient passer quelque chose,
     aucune nouvelle bascule n'est acceptée avant MIN_TOGGLE_INTERVAL_S après
     la précédente.

Usage :
    python3 scripts/button_toggle_test.py [--pin 17] [--poll-ms 10]

Ctrl+C pour arrêter proprement (libère le GPIO).
"""
from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.request

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("button_toggle_test")

RADIO_BASE = "http://localhost/lecteur/radio.php"
CONFIRM_DELAY_S = 0.008       # relecture de la broche après le front, pour confirmer
MIN_TOGGLE_INTERVAL_S = 0.4   # garde-fou global entre deux bascules acceptées


def http_get(query: str) -> dict | None:
    try:
        with urllib.request.urlopen(f"{RADIO_BASE}?{query}", timeout=3) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        LOGGER.warning("Appel radio.php échoué (%s) : %s", query, e)
        return None


def current_mode() -> str | None:
    data = http_get("action=get_output")
    return data.get("mode") if data else None


def toggle_output() -> None:
    mode = current_mode()
    if mode is None:
        LOGGER.warning("Mode actuel inconnu (MPD injoignable ?) — bascule annulée")
        return
    target = "hp" if mode == "casque" else "casque"
    result = http_get(f"action=set_output&mode={target}")
    if result and result.get("ok"):
        LOGGER.info("Bascule OK : %s -> %s", mode, target)
    else:
        LOGGER.warning("Bascule échouée vers %s (réponse : %s)", target, result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pin", type=int, default=17, help="GPIO BCM du bouton (défaut : 17 — à adapter au câblage réel)")
    parser.add_argument("--poll-ms", type=int, default=10, help="Intervalle de polling en ms (défaut : 10)")
    args = parser.parse_args()

    import RPi.GPIO as GPIO  # import ici : permet --help hors Pi sans RPi.GPIO installé

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(args.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Polling manuel plutôt que add_event_detect() : sur Raspberry Pi 5, la
    # détection par interruption de RPi.GPIO est connue pour être peu fiable
    # (puce GPIO RP1, différente des Pi précédents, mal supportée par cette
    # bibliothèque) — un appui pouvait être détecté puis plus aucun ensuite.
    # Même principe de polling que GpioSignalMonitor (battery_watchdog.py),
    # juste avec un intervalle bien plus rapide, adapté à un bouton humain.
    poll_interval_s = args.poll_ms / 1000
    last_state = GPIO.HIGH
    last_toggle = 0.0

    LOGGER.info("Écoute du bouton sur GPIO%s (BCM, polling %sms) — Ctrl+C pour arrêter", args.pin, args.poll_ms)
    try:
        while True:
            state = GPIO.input(args.pin)
            if state != last_state:
                LOGGER.debug("Broche GPIO%s : %s -> %s", args.pin, "HIGH" if last_state else "LOW", "HIGH" if state else "LOW")
            if state == GPIO.LOW and last_state == GPIO.HIGH:
                # Front descendant détecté par polling — confirmation avant d'agir
                time.sleep(CONFIRM_DELAY_S)
                if GPIO.input(args.pin) == GPIO.LOW:
                    now = time.monotonic()
                    if now - last_toggle >= MIN_TOGGLE_INTERVAL_S:
                        last_toggle = now
                        LOGGER.info("Appui confirmé sur GPIO%s", args.pin)
                        toggle_output()
                    else:
                        LOGGER.debug("Front ignoré (trop proche du précédent, garde-fou)")
                else:
                    LOGGER.debug("Front ignoré (rebond court, non confirmé)")
            last_state = state
            time.sleep(poll_interval_s)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup(args.pin)
        LOGGER.info("GPIO libéré, arrêt propre")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
