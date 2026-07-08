#!/usr/bin/env python3
"""Daemon des 8 boutons physiques du boîtier Hechicero — GPIO direct.

Remplace `button_toggle_test.py` (scopé à un seul bouton, GPIO17, TEMPORAIRE)
par un daemon unique qui poll les 9 broches GPIO (8 boutons câblés + 1 broche
en réserve) dans une seule boucle et dispatche chaque appui vers un handler
dédié à la broche.

**Mapping GPIO ↔ bouton physique confirmé le 2026-07-08** (test bouton par
bouton, gauche à droite sur la tranche supérieure du boîtier réel) :
  GPIO25 → source (bascule HP/casque)
  GPIO13 → volume - (maintien = répétition)
  GPIO17 → précédent (tap) / recul de SEEK_STEP_S s dans l'épisode (maintien)
  GPIO12 → play/pause
  GPIO27 → suivant (tap) / avance de SEEK_STEP_S s dans l'épisode (maintien)
  GPIO5  → volume + (maintien = répétition)
  GPIO16 → réserve, pas de fonction pour l'instant
  GPIO23 → favori (bouton isolé, emplacement antenne) — pas encore câblé côté
           logiciel, TICKET-046 (fonctionnalité favoris) jamais codée
  GPIO6  → non câblé à un bouton (broche libre inutilisée)

Boutons "tap ou maintien" (2026-07-08, GPIO17/27) : un appui bref garde le
comportement historique (épisode suivant/précédent) ; un appui tenu plus de
HOLD_THRESHOLD_S bascule en recherche et avance/recule de SEEK_STEP_S
secondes par à-coup dans l'épisode en cours (`action=seek_relative` côté
radio.php, `seekcur +N`/`seekcur -N` côté MPD). Recherche en secondes fixes,
pas en pourcentage de la durée — pratique standard des lecteurs de podcasts
(Apple Podcasts, YouTube...), un % serait incohérent entre un épisode de
5 minutes et un de 2 heures.

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

# Mapping GPIO ↔ bouton confirmé le 2026-07-08 (voir mémoire
# project_hechicero_buttons_gpio et docstring du module). GPIO4 volontairement
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
    """Bouton "source" — bascule HP/casque. Handler définitif, repris de
    button_toggle_test.py. Câblé sur GPIO25 dans le boîtier réel (pas GPIO17,
    qui n'était que le pin de la breadboard de test du 2026-07-06) — voir
    mapping confirmé le 2026-07-08 en tête de fichier."""
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
    """Tap court sur "suivant" — action=next_episode (TICKET-091). Sans effet
    si la lecture en cours n'est pas un épisode de podcast (webradio, arrêt)
    ou si on est déjà au dernier épisode de la série (radio.php répond
    ok:false). Le maintien de ce même bouton fait autre chose : voir
    handle_seek_forward / TAP_OR_HOLD."""
    result = http_get("action=next_episode")
    LOGGER.info("Épisode suivant (GPIO%s) — réponse radio.php : %s", pin, result)


def handle_prev(pin: int) -> None:
    """Tap court sur "précédent" — action=prev_episode (TICKET-091). Voir
    handle_next. Le maintien fait handle_seek_back à la place."""
    result = http_get("action=prev_episode")
    LOGGER.info("Épisode précédent (GPIO%s) — réponse radio.php : %s", pin, result)


def handle_seek_forward(pin: int) -> None:
    """Maintien du bouton "suivant" — avance de SEEK_STEP_S secondes dans
    l'épisode en cours (2026-07-08, à la place d'un saut d'épisode répété).
    `action=seek_relative` utilise `seekcur +N` côté MPD (relatif à la
    position actuelle, pas un `seekcur` absolu)."""
    result = http_get(f"action=seek_relative&delta={SEEK_STEP_S}")
    LOGGER.debug("Avance rapide +%ss (GPIO%s) — réponse : %s", SEEK_STEP_S, pin, result)


def handle_seek_back(pin: int) -> None:
    """Maintien du bouton "précédent" — recule de SEEK_STEP_S secondes.
    Voir handle_seek_forward."""
    result = http_get(f"action=seek_relative&delta=-{SEEK_STEP_S}")
    LOGGER.debug("Retour rapide -%ss (GPIO%s) — réponse : %s", SEEK_STEP_S, pin, result)


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
# Mapping confirmé le 2026-07-08 (test bouton par bouton, gauche à droite) —
# voir docstring du module pour le détail complet par position physique.
# GPIO17 et GPIO27 (précédent/suivant) n'utilisent PAS ce dict : ce sont des
# boutons "tap ou maintien" (TAP_OR_HOLD ci-dessous), dispatchés à part.
# GPIO16 (dernier bouton de la ligne) et GPIO23 (bouton isolé, emplacement
# antenne, destiné au favori) restent volontairement en handle_unassigned :
# GPIO16 est une vraie réserve ("on verra plus tard ce qu'on en fait", Thomas
# 2026-07-08) ; GPIO23/favori attend TICKET-046 (fonctionnalité jamais codée
# dans l'app — pas de champ côté serveur à faire basculer).
HANDLERS = {
    25: handle_hp_casque,   # source
    13: handle_vol_down,
    12: handle_play_pause,
    5:  handle_vol_up,
}


# Boutons "maintien" — répètent leur action tant qu'ils restent appuyés, au
# lieu d'exiger un appui répété. Seulement volume +/- (2026-07-08, demande
# Thomas) : les autres boutons (next/prev/play-pause/source) ne doivent PAS
# répéter en boucle si on les maintient par erreur.
REPEAT_PINS = {5, 13}   # vol_up, vol_down (mapping confirmé 2026-07-08)
REPEAT_INTERVAL_S = 0.2   # cadence de répétition tant que le bouton reste appuyé
RELEASE_CONFIRM_S = 0.05  # HIGH doit tenir ce temps pour confirmer un vrai relâchement (filtre le rebond pendant le maintien)

# Boutons "tap ou maintien" — 2026-07-08, demande Thomas : un tap court garde
# le comportement existant (épisode suivant/précédent), un maintien avance/
# recule de quelques secondes DANS l'épisode en cours à la place (best
# practice podcast : pas fixe de progression, EN SECONDES, jamais en % de la
# durée — un % serait incohérent d'un épisode de 5 min à un de 2h).
TAP_OR_HOLD = {
    27: (handle_next, handle_seek_forward),
    17: (handle_prev, handle_seek_back),
}
HOLD_THRESHOLD_S = 0.4   # durée d'appui à partir de laquelle on bascule tap -> maintien
SEEK_STEP_S = 5          # secondes avancées/reculées à chaque à-coup pendant le maintien


class ButtonState:
    """Anti-rebond indépendant par broche (état HIGH/LOW + horodatage du
    dernier appui accepté et de la dernière répétition en cas de maintien).
    `held_since`/`release_since` servent à la fois aux boutons REPEAT_PINS et
    TAP_OR_HOLD (une broche n'est jamais dans les deux catégories à la fois).
    `is_holding` distingue, pour un bouton TAP_OR_HOLD, si le maintien a déjà
    basculé en mode "recherche" (auquel cas on ne déclenche PAS le tap au
    relâchement)."""

    __slots__ = ("last_state", "last_press", "last_repeat", "held_since", "release_since", "is_holding")

    def __init__(self) -> None:
        self.last_state = 1  # GPIO.HIGH
        self.last_press = 0.0
        self.last_repeat = 0.0
        self.held_since: float | None = None    # non-None tant que le bouton est "maintenu" (confirmé)
        self.release_since: float | None = None  # début d'un HIGH en cours de confirmation de relâchement
        self.is_holding = False                 # TAP_OR_HOLD seulement : maintien déjà basculé en mode recherche


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

                if pin in REPEAT_PINS:
                    # Logique dédiée par hystérésis : un bouton maintenu peut rebondir
                    # (HIGH bref) sans que ce soit un vrai relâchement. Traiter ça comme
                    # un relâchement+re-appui ferait retomber sur le garde-fou anti-rebond
                    # de l'appui simple (MIN_TOGGLE_INTERVAL_S) et bloquerait la répétition
                    # — d'où le bug remonté par Thomas. Le relâchement n'est confirmé
                    # qu'après RELEASE_CONFIRM_S de HIGH continu.
                    now = time.monotonic()
                    if state == GPIO.LOW:
                        st.release_since = None
                        if st.held_since is None:
                            # Pas encore "maintenu" — confirmer le 1er appui comme avant
                            time.sleep(CONFIRM_DELAY_S)
                            if GPIO.input(pin) == GPIO.LOW:
                                if now - st.last_press >= MIN_TOGGLE_INTERVAL_S:
                                    st.last_press = now
                                    st.last_repeat = now
                                    st.held_since = now
                                    LOGGER.info("Appui confirmé sur GPIO%s", pin)
                                    HANDLERS.get(pin, handle_unassigned)(pin)
                            else:
                                LOGGER.debug("GPIO%s : front ignoré (rebond court, non confirmé)", pin)
                        elif now - st.last_repeat >= REPEAT_INTERVAL_S:
                            st.last_repeat = now
                            LOGGER.debug("Répétition (maintien) sur GPIO%s", pin)
                            HANDLERS.get(pin, handle_unassigned)(pin)
                    else:  # HIGH
                        if st.held_since is not None:
                            if st.release_since is None:
                                st.release_since = now
                            elif now - st.release_since >= RELEASE_CONFIRM_S:
                                st.held_since = None
                                st.release_since = None

                elif pin in TAP_OR_HOLD:
                    # Tap ou maintien (2026-07-08, GPIO17/27 précédent/suivant) :
                    # un appui bref déclenche tap_handler (au relâchement, comme
                    # avant) ; un appui qui dépasse HOLD_THRESHOLD_S bascule en
                    # "recherche" et répète hold_handler tant que ça reste appuyé.
                    # Même hystérésis de relâchement que REPEAT_PINS ci-dessus (le
                    # rebond mécanique en cours de maintien ne doit pas être lu
                    # comme un relâchement).
                    tap_handler, hold_handler = TAP_OR_HOLD[pin]
                    now = time.monotonic()
                    if state == GPIO.LOW:
                        st.release_since = None
                        if st.held_since is None:
                            time.sleep(CONFIRM_DELAY_S)
                            if GPIO.input(pin) == GPIO.LOW:
                                if now - st.last_press >= MIN_TOGGLE_INTERVAL_S:
                                    st.last_press = now
                                    st.held_since = now
                                    st.is_holding = False
                            else:
                                LOGGER.debug("GPIO%s : front ignoré (rebond court, non confirmé)", pin)
                        else:
                            held_duration = now - st.held_since
                            if held_duration >= HOLD_THRESHOLD_S:
                                if not st.is_holding:
                                    st.is_holding = True
                                    st.last_repeat = now
                                    LOGGER.info("Maintien (recherche) sur GPIO%s", pin)
                                    hold_handler(pin)
                                elif now - st.last_repeat >= REPEAT_INTERVAL_S:
                                    st.last_repeat = now
                                    hold_handler(pin)
                    else:  # HIGH
                        if st.held_since is not None:
                            if st.release_since is None:
                                st.release_since = now
                            elif now - st.release_since >= RELEASE_CONFIRM_S:
                                if not st.is_holding:
                                    LOGGER.info("Tap confirmé sur GPIO%s", pin)
                                    tap_handler(pin)
                                st.held_since = None
                                st.release_since = None
                                st.is_holding = False

                elif state == GPIO.LOW and st.last_state == GPIO.HIGH:
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
