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

Antirebond à trois niveaux — volontairement redondant, un seul rebond
parasite suffit à rendre le truc pénible à l'usage :
  1. `bouncetime` RPi.GPIO : ignore tout nouveau front dans les X ms qui
     suivent le dernier détecté (filtre matériel classique).
  2. Confirmation logicielle : après un front descendant, on attend un court
     instant puis on relit la broche — si elle n'est plus à l'état bas, le
     front était du bruit, on annule sans rien faire.
  3. Garde-fou global : même si (1) et (2) laissaient passer quelque chose,
     aucune nouvelle bascule n'est acceptée avant MIN_TOGGLE_INTERVAL_S après
     la précédente.

Usage :
    python3 scripts/button_toggle_test.py [--pin 17] [--bouncetime-ms 250]

Ctrl+C pour arrêter proprement (libère le GPIO).
"""
from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("button_toggle_test")

RADIO_BASE = "http://localhost/lecteur/radio.php"
CONFIRM_DELAY_S = 0.03        # relecture de la broche après le front, pour confirmer
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
    parser.add_argument("--bouncetime-ms", type=int, default=250, help="Antirebond RPi.GPIO en ms (défaut : 250)")
    args = parser.parse_args()

    import RPi.GPIO as GPIO  # import ici : permet --help hors Pi sans RPi.GPIO installé

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(args.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    last_toggle = 0.0

    def on_press(channel: int) -> None:
        nonlocal last_toggle
        time.sleep(CONFIRM_DELAY_S)
        if GPIO.input(channel) != GPIO.LOW:
            LOGGER.debug("Front ignoré (rebond court, non confirmé)")
            return
        now = time.monotonic()
        if now - last_toggle < MIN_TOGGLE_INTERVAL_S:
            LOGGER.debug("Front ignoré (trop proche du précédent, garde-fou)")
            return
        last_toggle = now
        LOGGER.info("Appui confirmé sur GPIO%s", channel)
        toggle_output()

    GPIO.add_event_detect(args.pin, GPIO.FALLING, callback=on_press, bouncetime=args.bouncetime_ms)

    LOGGER.info("Écoute du bouton sur GPIO%s (BCM) — Ctrl+C pour arrêter", args.pin)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup(args.pin)
        LOGGER.info("GPIO libéré, arrêt propre")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
