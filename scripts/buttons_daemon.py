#!/usr/bin/env python3
"""Daemon des 9 boutons physiques (TICKET-091/031) — GPIO direct.

Remplace `button_toggle_test.py` (scopé à un seul bouton, GPIO17, TEMPORAIRE)
par un daemon unique qui poll les 9 broches GPIO dans une seule boucle et
dispatche chaque appui vers un handler dédié à la broche.

Phase 1 (ce script, à ce stade) : seul GPIO17 a un vrai handler
(`handle_hp_casque`, bascule HP/casque via `radio.php`, repris tel quel de
`button_toggle_test.py`). Les 8 autres broches n'ont pas encore de fonction
assignée : elles sont seulement journalisées ("Bouton GPIOxx appuyé") pour
permettre d'identifier, bouton par bouton, quelle broche correspond à quel
bouton physique sur le boîtier. Une fois cette correspondance connue et les
actions `radio.php` (play/pause/next/prev/volume/favoris) confirmées, les
handlers de phase 2 remplaceront les logs par de vrais appels d'action
(cf. TICKET-091 dans `docs/90-BACKLOG.md`).

Câblage attendu (même convention que GpioSignalMonitor de battery_watchdog.py
et que button_toggle_test.py) : chaque bouton entre son GPIO (numérotation
BCM) et la masse (GND), pull-up interne activé → repos = HIGH, appui = LOW.

Détection par polling (pas par `add_event_detect()`) : sur Raspberry Pi 5, la
détection par interruption de RPi.GPIO est peu fiable (puce GPIO RP1, mal
supportée par cette bibliothèque) — confirmé lors du bring-up GPIO17
(2026-07-06, cf. `button_toggle_test.py`). Antirebond à trois niveaux, par
broche (chaque broche a son propre état/anti-rebond, indépendant des autres) :
  1. Polling rapproché (`--poll-ms`) de toutes les broches à chaque tour.
  2. Confirmation logicielle après un front descendant (relecture après
     `CONFIRM_DELAY_S`).
  3. Garde-fou global par broche (`MIN_TOGGLE_INTERVAL_S`) entre deux appuis
     acceptés sur la même broche.

Usage :
    sudo python3 scripts/buttons_daemon.py [--poll-ms 10] [--debug]

Ctrl+C pour arrêter proprement (libère tous les GPIO).
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time
import urllib.request

LOGGER = logging.getLogger("buttons_daemon")

RADIO_BASE = "http://localhost/lecteur/radio.php"
CONFIRM_DELAY_S = 0.008       # relecture de la broche après le front, pour confirmer
MIN_TOGGLE_INTERVAL_S = 0.4   # garde-fou par broche entre deux appuis acceptés

# Plan GPIO final validé le 2026-07-07 (voir mémoire project_hechicero_buttons_gpio) :
# GPIO17 déjà câblé et validé (bascule HP/casque). Les 8 autres sont libres,
# fonctions à assigner (play/pause/next/précédent/vol+/vol-/favoris — 7
# fonctions pour 8 broches, une reste en réserve). GPIO4 volontairement
# absent : réservé MUTE ampli sur HiFiBerry Amp4 (cf. mémoire, doc HiFiBerry).
PINS = [17, 23, 27, 5, 6, 13, 16, 12, 25]


def http_get(query: str) -> dict | None:
    try:
        with urllib.request.urlopen(f"{RADIO_BASE}?{query}", timeout=3) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        LOGGER.warning("Appel radio.php échoué (%s) : %s", query, e)
        return None


def http_get_text(query: str) -> str | None:
    """Comme http_get, mais pour les actions qui répondent en texte brut
    (protocole MPD), pas en JSON — ex: action=status."""
    try:
        with urllib.request.urlopen(f"{RADIO_BASE}?{query}", timeout=3) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        LOGGER.warning("Appel radio.php échoué (%s) : %s", query, e)
        return None


def current_mode() -> str | None:
    data = http_get("action=get_output")
    return data.get("mode") if data else None


def mpd_state() -> str | None:
    """État MPD ('play' / 'pause' / 'stop'), lu via action=status (texte brut
    protocole MPD, pas JSON). Utilisé pour donner un sens directionnel à
    play/pause : radio.php n'expose qu'un toggle unique (action=pause)."""
    raw = http_get_text("action=status")
    if raw is None:
        return None
    m = re.search(r"^state: (\w+)$", raw, re.MULTILINE)
    return m.group(1) if m else None


def handle_hp_casque(pin: int) -> None:
    """GPIO17 — bascule HP/casque. Handler définitif, repris de button_toggle_test.py."""
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


def handle_unassigned(pin: int) -> None:
    """Phase 1 — broche pas encore assignée : on journalise pour identifier
    quel GPIO correspond à quel bouton physique du boîtier."""
    LOGGER.info("Bouton GPIO%s appuyé (fonction pas encore assignée — phase 1 identification)", pin)


def handle_play_pause(pin: int) -> None:
    """Play/pause — un seul bouton physique, toggle à chaque appui.

    Revenu sur la décision "2 boutons distincts" (play strict / pause strict,
    cf. ancienne version de ce handler) : le nouveau boîtier a un bouton
    physique de moins que prévu (7 emplacements utilisables pour 8 fonctions),
    Thomas a choisi de fusionner play+pause en un seul bouton pour compenser
    plutôt que de sacrifier une autre fonction (2026-07-08). Comportement
    confirmé par Thomas en conditions réelles : appui → play, ré-appui →
    pause, ré-appui → play, etc. — exactement le toggle déjà exposé par
    `action=pause` de radio.php, pas besoin de vérifier l'état MPD avant
    d'agir (contrairement à l'ancienne version directionnelle handle_play/
    handle_pause).
    """
    result = http_get("action=pause")
    LOGGER.info("Play/pause (GPIO%s) — réponse radio.php : %s", pin, result)


def handle_next(pin: int) -> None:
    """Épisode suivant — action=next_episode (TICKET-091). Sans effet si la
    lecture en cours n'est pas un épisode de podcast (webradio, arrêt) ou si
    on est déjà au dernier épisode de la série (radio.php répond ok:false)."""
    result = http_get("action=next_episode")
    LOGGER.info("Épisode suivant (GPIO%s) — réponse radio.php : %s", pin, result)


def handle_prev(pin: int) -> None:
    """Épisode précédent — action=prev_episode (TICKET-091). Voir handle_next."""
    result = http_get("action=prev_episode")
    LOGGER.info("Épisode précédent (GPIO%s) — réponse radio.php : %s", pin, result)


def handle_vol_up(pin: int) -> None:
    """Volume + — réutilise `action=volup` (+5, borné à 100 côté serveur)."""
    result = http_get("action=volup")
    LOGGER.info("Volume + (GPIO%s) — réponse radio.php : %s", pin, result)


def handle_vol_down(pin: int) -> None:
    """Volume - — réutilise `action=voldown` (-5, borné à 0 côté serveur)."""
    result = http_get("action=voldown")
    LOGGER.info("Volume - (GPIO%s) — réponse radio.php : %s", pin, result)


# Dispatch par broche. Les broches absentes de ce dict tombent sur
# handle_unassigned via .get(pin, handle_unassigned) dans la boucle.
#
# GPIO17 est câblé et validé (bascule HP/casque — bouton "source" du boîtier
# réel, situé à côté de la prise jack, décision 2026-07-08). Les autres
# broches (23, 27, 5, 6, 13, 16, 12, 25) sont câblées et détectées (bring-up
# 2026-07-07) mais pas encore reliées à un bouton physique précis — Thomas
# finalisera la correspondance GPIO ↔ bouton une fois les boutons montés
# dans le boîtier.
#
# Boîtier réel (2026-07-08) : 7 boutons utilisables en ligne (dont le
# "source"/HP-casque) + 1 bouton isolé dans l'emplacement antenne, laissé en
# réserve complète (aucune fonction). Comme il y a un bouton de moins que
# prévu à l'origine, play et pause sont fusionnés en un seul bouton toggle
# (handle_play_pause) plutôt que d'en sacrifier une autre fonction. 6
# fonctions restent donc à répartir sur les 6 broches hors GPIO17 :
#   handle_play_pause, handle_vol_up, handle_vol_down, handle_next,
#   handle_prev, et handle_favori (à écrire — reporté, TICKET-046).
# Layout ergonomique proposé (ordre physique, à côté du bouton source) :
#   vol- · précédent · play/pause · suivant · vol+ · favori
# Assignation GPIO définitive en attente du câblage réel, ex. une fois connu :
#   23: handle_vol_down,
#   27: handle_prev,
#   5:  handle_play_pause,
#   6:  handle_next,
#   13: handle_vol_up,
#   16: (favori, à écrire)
#   12, 25 : non câblés sur ce boîtier (7 positions seulement, pas 9)
#
# handle_favori toujours absent du code : TICKET-046 (fonctionnalité favoris)
# n'a jamais été codée dans l'app (pas de champ à faire basculer côté
# serveur) — reporté. Le bouton qui lui est destiné restera en
# handle_unassigned (log seul) jusqu'à ce que TICKET-046 soit traité pour de
# vrai.
HANDLERS = {
    17: handle_hp_casque,
}


class ButtonState:
    """Anti-rebond indépendant par broche (état HIGH/LOW + horodatage du
    dernier appui accepté)."""

    __slots__ = ("last_state", "last_press")

    def __init__(self) -> None:
        self.last_state = 1  # GPIO.HIGH
        self.last_press = 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--poll-ms", type=int, default=10, help="Intervalle de polling en ms (défaut : 10)")
    parser.add_argument("--debug", action="store_true", help="Logs DEBUG (front par front, utile pour identifier le câblage)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    import RPi.GPIO as GPIO  # import ici : permet --help hors Pi sans RPi.GPIO installé

    GPIO.setmode(GPIO.BCM)
    for pin in PINS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    states = {pin: ButtonState() for pin in PINS}
    poll_interval_s = args.poll_ms / 1000

    LOGGER.info(
        "Écoute de %d boutons (GPIO %s, polling %sms) — Ctrl+C pour arrêter",
        len(PINS), ", ".join(str(p) for p in PINS), args.poll_ms,
    )

    try:
        while True:
            for pin in PINS:
                st = states[pin]
                state = GPIO.input(pin)
                if state != st.last_state:
                    LOGGER.debug("Broche GPIO%s : %s -> %s", pin, "HIGH" if st.last_state else "LOW", "HIGH" if state else "LOW")

                if state == GPIO.LOW and st.last_state == GPIO.HIGH:
                    # Front descendant détecté par polling — confirmation avant d'agir
                    time.sleep(CONFIRM_DELAY_S)
                    if GPIO.input(pin) == GPIO.LOW:
                        now = time.monotonic()
                        if now - st.last_press >= MIN_TOGGLE_INTERVAL_S:
                            st.last_press = now
                            LOGGER.info("Appui confirmé sur GPIO%s", pin)
                            HANDLERS.get(pin, handle_unassigned)(pin)
                        else:
                            LOGGER.debug("GPIO%s : front ignoré (trop proche du précédent, garde-fou)", pin)
                    else:
                        LOGGER.debug("GPIO%s : front ignoré (rebond court, non confirmé)", pin)

                st.last_state = state

            time.sleep(poll_interval_s)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup(PINS)
        LOGGER.info("GPIO libérés, arrêt propre")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
