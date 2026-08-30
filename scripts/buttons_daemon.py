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
  GPIO16 → favori (TICKET-046, tap = bascule le favori sur l'épisode en
           cours / maintien = ouvre l'écran dédié favoris) — GPIO confirmé le
           2026-07-19 via ce daemon en mode identification
  GPIO23 → bouton isolé, emplacement antenne — écran Chambre (TICKET-112,
           domotique lampe/volet) : toggle simple, ouvre/ferme l'écran et
           réveille la dalle si elle est en veille DPMS
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
import os
import re
import subprocess
import threading
import time
import urllib.request

LOGGER = logging.getLogger("buttons_daemon")

RADIO_BASE = "http://localhost/lecteur/radio.php"
CONFIRM_DELAY_S = 0.008       # relecture de la broche après le front, pour confirmer
MIN_TOGGLE_INTERVAL_S = 0.4   # garde-fou par broche entre deux appuis acceptés

# Réveil de la dalle physique (TICKET-112, bouton Chambre GPIO23). Ce daemon
# tourne en root, mais l'écran est piloté par wlr-randr dans la session
# Wayland de l'utilisateur `thomas` (cf. scripts/screen_dpms.sh, "pas de sudo
# requis") — il faut donc franchir la frontière utilisateur et fournir l'env
# de session. `runuser` (root -> thomas) évite le piège sudo+NoNewPrivileges
# du durcissement systemd (TICKET-011).
SCREEN_DPMS_SCRIPT = "/home/thomas/hechicero/scripts/screen_dpms.sh"
SCREEN_USER = "thomas"
SCREEN_ENV = {"WAYLAND_DISPLAY": "wayland-0", "XDG_RUNTIME_DIR": "/run/user/1000"}

# Mapping GPIO ↔ bouton confirmé le 2026-07-08 (voir mémoire
# project_hechicero_buttons_gpio et docstring du module). GPIO4 volontairement
# absent : réservé MUTE ampli sur HiFiBerry Amp4 (cf. mémoire, doc HiFiBerry).
PINS = [17, 23, 27, 5, 6, 13, 16, 12, 25]


def http_get(query: str) -> dict | None:
    """Appelle radio.php et renvoie le JSON, ou None si la réponse n'en est pas.

    ── TICKET-132 : ne pas confondre « pas du JSON » et « en panne » ──────────
    Chaque appui sur play/pause produisait :

        WARNING Appel radio.php échoué (action=pause) : Expecting value: line 1 column 1

    **alors que l'action fonctionnait parfaitement.** `radio.php` ne renvoie du
    JSON que pour certaines actions ; pour `pause` il exécute la commande MPD
    puis retombe sur la vieille page HTML de débogage en bas du fichier. Le
    `json.loads()` échouait sur du HTML, et l'exception était journalisée comme
    une panne réseau.

    ⚠️ Un avertissement permanent qui ne signale rien est exactement ce qui fait
    ignorer les vrais : le journal de `buttons_daemon` en devenait illisible.

    On distingue donc les deux cas — l'échec de transport reste un `warning`,
    une réponse non-JSON descend en `debug`. ❌ **Ne PAS uniformiser les
    réponses de `radio.php` en JSON** : l'IHM enfant lit `action=status` en
    texte MPD brut (`sendRadio('status')` puis `parseMpd()`), ce changement
    casserait le lecteur.
    """
    try:
        with urllib.request.urlopen(f"{RADIO_BASE}?{query}", timeout=3) as r:
            corps = r.read().decode("utf-8")
    except Exception as e:
        # Vraie panne : réseau, serveur absent, HTTP en erreur, délai dépassé.
        LOGGER.warning("Appel radio.php échoué (%s) : %s", query, e)
        return None
    try:
        return json.loads(corps)
    except ValueError:
        # Réponse reçue mais pas au format JSON : la commande a bien été
        # exécutée, seul le format de retour diffère. Rien à signaler.
        LOGGER.debug("radio.php (%s) a répondu autre chose que du JSON — normal "
                     "pour cette action", query)
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


def handle_favori_toggle(pin: int) -> None:
    """Tap court sur le bouton favori (GPIO16, TICKET-046) — bascule le
    favori sur l'épisode en cours d'écoute (action=toggle_favori, résolu côté
    serveur à partir du fichier réellement joué par MPD, même principe que
    next_episode/prev_episode). Sans effet sur une webradio ou si rien ne
    joue : radio.php répond ok:false, pas une erreur en soi."""
    result = http_get("action=toggle_favori")
    LOGGER.info("Favori bascule (GPIO%s) — réponse radio.php : %s", pin, result)


def handle_favori_screen(pin: int) -> None:
    """Maintien du bouton favori (GPIO16, TICKET-046) — demande l'ouverture
    de l'écran dédié favoris côté IHM tactile. Pas de canal direct entre ce
    daemon et le navigateur : on écrit juste la demande (action=request_screen,
    data/ui_request.json horodaté), c'est index.html qui la consomme par
    polling."""
    result = http_get("action=request_screen&screen=favoris")
    LOGGER.info("Demande écran favoris (GPIO%s) — réponse radio.php : %s", pin, result)


JOURNAL_ECRAN = "/home/thomas/hechicero/data/screen_dpms.log"


def marquer_appui_bouton() -> None:
    """
    Dépose dans le journal d'écran la trace d'un appui physique (TICKET-153).

    Format aligné sur celui de `screen_dpms.sh` pour que tout se lise dans
    l'ordre chronologique, sans outil :

        2026-08-30 21:14:07 [buttons_daemon] appui — origine du réveil : BOUTON
        2026-08-30 21:14:07 [sh<-swayidle] on — sortie inactive …, rebond …

    Sans cette ligne, un réveil est tactile. Avec elle juste avant, il vient
    d'un bouton. C'est la seule façon de trancher : la frappe virtuelle envoyée
    juste après rend les deux chemins indiscernables côté compositeur.

    Best-effort et silencieux : tracer un appui ne doit jamais gêner un appui.
    Le service est durci, mais `data/` est dans ses `ReadWritePaths` (zone Z2).
    """
    try:
        horodatage = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(JOURNAL_ECRAN, "a", encoding="utf-8") as fh:
            fh.write(f"{horodatage} [buttons_daemon] appui  "
                     f"— origine du réveil : BOUTON\n")
    except Exception:
        pass


def wake_screen() -> None:
    """Rallume la dalle si elle est en veille DPMS (TICKET-112). Best-effort,
    ne lève jamais : un échec de réveil écran ne doit pas empêcher la bascule
    d'écran (l'IHM change quand même, visible dès que la dalle revient). Un
    `wlr-randr --on` alors que l'écran est déjà allumé est un no-op inoffensif.

    Ce daemon est root ; l'écran appartient à la session Wayland de `thomas`.
    On passe par `runuser` (pas `sudo`, cassé par NoNewPrivileges du
    durcissement TICKET-011) en injectant l'env de session Wayland.

    Lancé dans un thread détaché : `wlr-randr` peut prendre ~1s, et on ne veut
    JAMAIS bloquer la boucle de polling GPIO (sinon les autres boutons
    deviennent mous le temps du réveil) — non-régression."""
    def _run():
        try:
            env_prefix = [f"{k}={v}" for k, v in SCREEN_ENV.items()]
            # ⚠️ 20 s, et surtout PAS 5 (TICKET-153). Le rebond de mode dure
            # 3 s de `sleep` + deux `wlr-randr` + le démarrage de `runuser` —
            # soit 4 à 5 s. Avec un délai de garde de 5 s, ce chemin tuait le
            # script **pendant le sommeil**, donc entre les deux changements de
            # mode : la dalle restait en 1280x720 quand le compositeur rendait
            # en 1024x600. Écran noir, tous les indicateurs au vert.
            # Le chemin tactile, lancé par swayidle sans délai de garde, n'a
            # jamais eu ce défaut — d'où l'intuition de Thomas, exacte, que les
            # écrans noirs suivaient les réveils par bouton.
            # Le script porte désormais aussi un `trap` qui repose le mode natif
            # même s'il est tué ; ce délai généreux est la seconde protection.
            subprocess.run(
                ["runuser", "-u", SCREEN_USER, "--", "env", *env_prefix, SCREEN_DPMS_SCRIPT, "on"],
                timeout=20, check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            LOGGER.warning("Réveil écran échoué (non bloquant) : %s", e)
    threading.Thread(target=_run, daemon=True).start()


# ── TICKET-123 — signaler l'activité au compositeur ────────────────────────
# LE PROBLÈME, mesuré le 2026-08-17 : `swayidle` n'observe que les entrées
# Wayland. Les neuf boutons GPIO sont lus par ce daemon, un processus Python
# que le compositeur ne voit jamais. Son cycle est : compter 1200 s → lancer
# `off` → RESTER en état « déjà expiré » jusqu'à une vraie entrée → lancer
# `resume` → et seulement alors réarmer.
#
# Conséquence : réveiller la dalle par un bouton laisse swayidle bloqué. Test
# fait en réel — réveil par le bouton antenne seul, puis 25 minutes sans
# toucher l'écran : AUCUN `off`. Confirmé.
#
# ⚠️ Appeler `screen_dpms.sh on` ne remplace PAS un événement d'entrée : ça
# rallume la dalle sans rien dire au compositeur. C'est la règle déjà inscrite
# en zone Z4 du registre, et c'est exactement le piège dans lequel TICKET-112
# est tombé.
#
# LA CORRECTION : émettre une vraie frappe clavier virtuelle (`wtype`, protocole
# Wayland). Le compositeur la compte comme de l'activité, swayidle sort de son
# état expiré, réarme son compte à rebours, et l'écran s'éteint de nouveau
# normalement 20 minutes plus tard.
#
# Bénéfice secondaire, au moins aussi important au quotidien : un enfant qui
# n'utilise QUE les boutons physiques voyait son écran s'éteindre au bout de
# 20 minutes alors qu'il était en train de s'en servir. Ce n'est plus le cas.
#
# `Shift_L` : touche modificatrice seule. Elle n'insère aucun caractère, ne
# déclenche aucun clic, et ne peut donc rien changer dans l'IHM enfant — on
# veut signaler une présence, pas piloter la page.
WTYPE_BIN = "/usr/bin/wtype"
ACTIVITE_THROTTLE_S = 5.0     # une frappe virtuelle au plus toutes les 5 s
_derniere_activite = 0.0
_wtype_manquant_signale = False


def signaler_activite() -> None:
    """Dit au compositeur « quelqu'un est là ». Best-effort, ne lève jamais.

    Étranglé à une frappe toutes les ACTIVITE_THROTTLE_S : un rebond GPIO ou
    un bouton maintenu ne doit pas déclencher une rafale de sous-processus.
    Le but est de signaler une présence, pas de compter les appuis.

    Thread détaché, comme wake_screen() : ne JAMAIS bloquer la boucle de
    polling GPIO, sinon les autres boutons deviennent mous.
    """
    global _derniere_activite, _wtype_manquant_signale
    maintenant = time.monotonic()
    if maintenant - _derniere_activite < ACTIVITE_THROTTLE_S:
        return
    _derniere_activite = maintenant

    # ── TICKET-153 — tracer l'ORIGINE du réveil ─────────────────────────────
    # Le journal d'écran ne sait pas distinguer un réveil tactile d'un réveil
    # par bouton : les deux arrivent par swayidle, puisque la frappe virtuelle
    # ci-dessous est justement là pour ça (TICKET-123). Le rapport du 149
    # affichait donc « tactile » pour TOUT, y compris les appuis boutons — une
    # attribution fausse, qui a fermé à tort l'hypothèse de Thomas.
    #
    # On dépose donc une marque AVANT la frappe. Un réveil précédé de cette
    # ligne à quelques secondes est un réveil par bouton ; sans elle, c'est un
    # réveil tactile. La marque est écrite dans le journal d'écran lui-même,
    # pour que la corrélation soit une simple lecture chronologique.
    marquer_appui_bouton()

    if not os.path.exists(WTYPE_BIN):
        if not _wtype_manquant_signale:
            LOGGER.warning(
                "wtype absent (%s) — swayidle ne verra pas les boutons, "
                "l'écran restera allumé après un réveil non tactile (TICKET-123). "
                "Installer : sudo apt install wtype", WTYPE_BIN,
            )
            _wtype_manquant_signale = True
        return

    def _run():
        try:
            env_prefix = [f"{k}={v}" for k, v in SCREEN_ENV.items()]
            subprocess.run(
                ["runuser", "-u", SCREEN_USER, "--", "env", *env_prefix, WTYPE_BIN, "-k", "Shift_L"],
                timeout=5, check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            LOGGER.warning("Signal d'activité échoué (non bloquant) : %s", e)
    threading.Thread(target=_run, daemon=True).start()


def handle_chambre(pin: int) -> None:
    """Bouton Chambre (GPIO23, TICKET-112) — toggle de l'écran domotique.
    Deux effets, indépendants et tous deux best-effort :
      1. Réveil de la dalle si elle est éteinte (DPMS) — un appui GPIO n'est
         pas vu comme une activité par le compositeur/swayidle, donc ne
         rallume pas l'écran tout seul.
      2. Demande de bascule d'écran côté IHM (action=request_screen, même
         mécanisme que l'écran favoris) — index.html gère le toggle réel
         (ouvre / revient à l'écran précédent) et le réveil de la veille
         "navigateur" (#sleep-overlay).
    Ordre : on réveille l'écran d'abord pour que la bascule soit visible."""
    wake_screen()
    result = http_get("action=request_screen&screen=chambre")
    LOGGER.info("Bouton Chambre (GPIO%s) — réponse radio.php : %s", pin, result)


# Dispatch par broche. Les broches absentes de ce dict tombent sur
# handle_unassigned via .get(pin, handle_unassigned) dans la boucle.
#
# Mapping confirmé le 2026-07-08 (test bouton par bouton, gauche à droite) —
# voir docstring du module pour le détail complet par position physique.
# GPIO17, GPIO27 (précédent/suivant) et GPIO16 (favori, TICKET-046)
# n'utilisent PAS ce dict : ce sont des boutons "tap ou maintien"
# (TAP_OR_HOLD ci-dessous), dispatchés à part.
# GPIO23 (bouton isolé, emplacement antenne) = bouton Chambre (TICKET-112,
# 2026-07-19) : toggle simple (pas tap-ou-maintien), donc dans ce dict.
HANDLERS = {
    25: handle_hp_casque,   # source
    13: handle_vol_down,
    12: handle_play_pause,
    5:  handle_vol_up,
    23: handle_chambre,     # écran domotique Chambre (TICKET-112)
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
# GPIO16 (favori, TICKET-046) rejoint ce dict le 2026-07-19 : tap = bascule
# le favori, maintien = ouvre l'écran dédié favoris. Même hystérésis de
# relâchement que next/précédent (RELEASE_CONFIRM_S), pas de raison de
# dupliquer une logique dédiée.
TAP_OR_HOLD = {
    27: (handle_next, handle_seek_forward),
    17: (handle_prev, handle_seek_back),
    16: (handle_favori_toggle, handle_favori_screen),
}
HOLD_THRESHOLD_S = 0.4   # durée d'appui à partir de laquelle on bascule tap -> maintien
SEEK_STEP_S = 5          # secondes avancées/reculées à chaque à-coup pendant le maintien


# ── TICKET-119 — combinaison casque + antenne : écran technique caché ──────
#
# Un appui SIMULTANÉ de 3 s sur le bouton casque (GPIO25) et le bouton antenne
# (GPIO23) ouvre l'écran technique. Il sert à retrouver l'IP en mobilité et à
# sortir du kiosque pour configurer un Wi-Fi à la dalle tactile — donc
# précisément quand aucun autre accès n'est disponible.
#
# ⚠️ LE PIÈGE, ET IL EST STRUCTUREL (zone Z3) : ces deux boutons déclenchent
# leur action **à l'appui**, pas au relâchement. Sans précaution, ouvrir l'écran
# caché basculerait au passage la sortie audio (GPIO25) et ouvrirait l'écran
# Chambre (GPIO23). L'utilisateur récupérerait son écran technique par-dessus
# deux effets de bord qu'il n'a pas demandés.
#
# Remède : pour CES DEUX BROCHES SEULEMENT, l'action individuelle est différée
# de COMBO_GRACE_S. Passé ce délai, si l'autre bouton n'est pas également
# enfoncé, on joue l'action normale ; sinon on l'abandonne au profit de la
# combinaison. 300 ms sur une bascule est imperceptible — c'est le prix à payer
# pour que la combinaison n'ait aucun effet de bord.
#
# ⚠️ Les sept autres boutons ne sont PAS touchés : ils gardent leur réactivité
# immédiate. Un différé global aurait rendu la radio molle pour un enfant.
COMBO_PINS = (23, 25)
COMBO_HOLD_S = 3.0        # durée d'appui simultané avant déclenchement
COMBO_GRACE_S = 0.3       # fenêtre pour reconnaître un appui « simultané »


# ── TICKET-149 — combinaison volume + / volume − : signaler un écran noir ────
#
# Demande de Thomas (2026-08-25) : « à la prochaine panne je veux appuyer sur
# deux boutons, que ça capture tout, et qu'un son me le confirme ».
#
# Le contexte impose la forme. Quand la dalle est noire, l'appareil ne peut plus
# rien montrer, et sortir un PC pour lancer une commande en SSH contredit l'idée
# même d'une radio autonome. Le signalement doit donc tenir entièrement dans
# l'objet : deux boutons, un son, rien d'autre.
#
# ⚠️ CES DEUX BROCHES SONT DIFFÉRENTES DE CELLES DE LA COMBINAISON 119. GPIO5 et
# GPIO13 sont des boutons À RÉPÉTITION : maintenus, ils enchaînent les pas de
# volume toutes les 200 ms. Trois secondes d'appui simultané, c'est trente pas.
#
# Le remède du TICKET-119 — différer l'action de 300 ms — est ici À PROSCRIRE :
# Thomas a explicitement demandé que les autres boutons gardent leur réactivité
# immédiate, « un différé global aurait rendu la radio molle pour un enfant ».
# Le volume est justement le bouton où la latence se sent le plus.
#
# Remède retenu : on n'inhibe QUE LA RÉPÉTITION, jamais le premier appui. Les
# deux boutons ne pouvant pas être enfoncés à la microseconde près, il passe au
# plus un pas de volume de chaque côté — et vol+ suivi de vol− s'annulent. Zéro
# latence ajoutée, effet de bord borné à un pas.
COMBO_INCIDENT_PINS = (5, 13)   # volume + et volume −

# 5 s, et pas les 3 s de la combinaison 119. Celle-ci REDÉMARRE l'appareil : un
# enfant de 7 ans est parfaitement capable de tenir deux boutons trois secondes
# par jeu, et la radio s'éteindrait en pleine histoire. Cinq secondes restent
# confortables pour un geste délibéré, et deviennent improbables par accident.
COMBO_INCIDENT_HOLD_S = 5.0

# Chemin du dépôt. WorkingDirectory vaut /run/hechicero-buttons (tube lgpio),
# donc aucun chemin relatif n'est utilisable ici.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EtatCombinaison:
    """Décision de la combinaison, isolée du GPIO pour être testable.

    Séparée volontairement de la boucle de polling : la logique se vérifie
    alors sans matériel, avec du temps simulé (voir `test_boutons.py`). Un test
    qui exigerait deux vraies broches n'aurait jamais été écrit.
    """

    def __init__(self, hold_s: float = COMBO_HOLD_S) -> None:
        self.depuis: float | None = None      # début de l'appui simultané
        self.declenchee = False               # déjà tirée pour cet appui
        # TICKET-149 : la durée est paramétrable depuis qu'il existe une
        # seconde combinaison. Celle de l'écran noir tient 5 s parce qu'elle
        # redémarre l'appareil — voir COMBO_INCIDENT_HOLD_S.
        self.hold_s = hold_s

    def evaluer(self, a_bas: bool, b_bas: bool, maintenant: float) -> str:
        """Renvoie 'declencher', 'en_cours', 'attente' ou 'relachee'.

        - 'attente'     : pas de combinaison en cours, dispatch normal
        - 'en_cours'    : les deux boutons sont enfoncés, on retient leur action
        - 'declencher'  : les 3 s sont atteintes — une seule fois par appui
        - 'relachee'    : combinaison terminée, on réarme
        """
        if a_bas and b_bas:
            if self.depuis is None:
                self.depuis = maintenant
                return "en_cours"
            if not self.declenchee and maintenant - self.depuis >= self.hold_s:
                self.declenchee = True
                return "declencher"
            return "en_cours"
        # Au moins un bouton relâché : la combinaison est finie.
        etait_active = self.depuis is not None
        self.depuis = None
        self.declenchee = False
        return "relachee" if etait_active else "attente"

    def retient(self, maintenant: float) -> bool:
        """Faut-il retenir l'action individuelle d'un bouton de la combinaison ?

        Vrai dès que les deux boutons sont enfoncés depuis moins que la grâce —
        on ne sait pas encore si c'est une combinaison ou deux appuis distincts.
        """
        return self.depuis is not None and maintenant - self.depuis >= 0


def handle_signaler_incident() -> None:
    """
    Écran noir : accuser réception, capturer, puis redémarrer (TICKET-149).

    ── Pourquoi cette routine existe ─────────────────────────────────────────
    La panne est invisible depuis le Pi : tous les indicateurs sont au vert
    pendant qu'elle dure. **Seul un humain qui regarde la dalle peut la
    signaler.** Et comme l'écran est noir, ni le constat ni sa confirmation ne
    peuvent passer par l'écran. Sortir un PC pour lancer une commande en SSH
    contredirait l'idée même d'une radio autonome — d'où deux boutons, un son,
    et l'appareil qui se remet en marche seul.

    ── L'ordre des trois actions n'est pas négociable ────────────────────────
    1. **Le son d'abord.** C'est le seul retour possible sur un écran noir, et
       il doit venir tout de suite : sans lui, Thomas appuierait à nouveau,
       croyant à un raté, et produirait des constats en double.
    2. **Le constat ensuite**, écrit et refermé sur le disque. Un redémarrage
       qui précéderait l'écriture perdrait exactement ce qu'on cherche à
       recueillir depuis des mois.
    3. **Le redémarrage en dernier.** C'est la récupération que le petit
       applique déjà de lui-même (coupure de courant) ; l'automatiser lui rend
       sa radio sans qu'il ait à attendre un adulte, et évite les extinctions
       brutales qui corrompent la carte SD.

    Tourne dans un thread détaché : la capture interroge `wlr-randr`, le noyau
    et le journal. La boucle des boutons ne doit jamais attendre.
    """
    LOGGER.warning("Combinaison volume+ / volume− maintenue %.0f s — "
                   "signalement écran noir puis redémarrage", COMBO_INCIDENT_HOLD_S)

    def lancer(script: str, *args: str, delai: int) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                ["/usr/bin/python3", os.path.join(PROJECT_ROOT, "scripts", script), *args],
                capture_output=True, text=True, timeout=delai,
            )
            return r.returncode == 0, (r.stdout or r.stderr or "").strip()
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    # 1. Accusé de réception sonore
    ok, detail = lancer("clic_confirmation.py", delai=20)
    LOGGER.info("Accusé sonore : %s (%s)", "émis" if ok else "MUET", detail[:80])

    # 2. Constat
    ok, detail = lancer(
        "ecran_noir.py", "signaler",
        "--note", "signalé au bouton (volume +/−) — écran noir constaté, "
                  "redémarrage automatique déclenché dans la foulée",
        delai=40,
    )
    LOGGER.info("Constat écran noir : %s", "enregistré" if ok else f"ÉCHEC — {detail[:120]}")

    if not ok:
        # On redémarre quand même : rendre la radio à l'enfant prime sur le
        # recueil de données. Mais on le journalise fort, sinon une série de
        # constats manquants passerait inaperçue au moment de l'analyse.
        LOGGER.error("Constat non enregistré — redémarrage tout de même, "
                     "cette occurrence sera absente du rapport")

    # 3. Redémarrage propre. `systemctl reboot` et jamais un `sudo` : le service
    # tourne en User=root avec NoNewPrivileges=true, qui casse sudo en silence
    # (leçon TICKET-121, zone Z2).
    LOGGER.warning("Redémarrage demandé (TICKET-149)")
    try:
        subprocess.run(["/usr/bin/systemctl", "reboot"], timeout=15)
    except Exception as e:  # noqa: BLE001
        LOGGER.error("Redémarrage impossible : %s", e)


def handle_ecran_technique() -> None:
    """Ouvre l'écran technique caché (TICKET-119).

    Passe par le canal `request_screen` déjà générique, comme l'écran Chambre :
    le daemon écrit la demande, le kiosque la relève. Aucun nouveau mécanisme.
    """
    LOGGER.info("Combinaison casque+antenne maintenue %.0f s — écran technique", COMBO_HOLD_S)
    rep = http_get("action=request_screen&screen=technique")
    LOGGER.info("Écran technique — réponse radio.php : %s", rep)


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

    combo = EtatCombinaison()
    # TICKET-149 : seconde combinaison, volume+ / volume−, 5 s → signalement
    # d'écran noir puis redémarrage. Même classe de décision, autre durée.
    combo_incident = EtatCombinaison(COMBO_INCIDENT_HOLD_S)
    # Actions différées des deux boutons de la combinaison : {broche: instant}
    differes: dict[int, float] = {}

    try:
        while True:
            # ── TICKET-119 : la combinaison s'évalue AVANT le dispatch ────────
            # Une fois par tour, pas une fois par broche : les deux boutons
            # doivent être lus au même instant, sinon on compare des états
            # décalés de quelques millisecondes.
            maintenant = time.monotonic()
            a_bas = GPIO.input(COMBO_PINS[0]) == GPIO.LOW
            b_bas = GPIO.input(COMBO_PINS[1]) == GPIO.LOW
            verdict = combo.evaluer(a_bas, b_bas, maintenant)

            # ── TICKET-149 — combinaison volume+ / volume− ─────────────────
            # Évaluée au même tour, sur le même instant. `incident_en_cours`
            # sert plus bas à inhiber la RÉPÉTITION du volume : sans lui, cinq
            # secondes d'appui simultané enchaîneraient cinquante pas de volume.
            # Le premier appui de chaque bouton, lui, passe normalement — c'est
            # ce qui évite d'ajouter la moindre latence au volume, et vol+ suivi
            # de vol− s'annulent.
            inc_a = GPIO.input(COMBO_INCIDENT_PINS[0]) == GPIO.LOW
            inc_b = GPIO.input(COMBO_INCIDENT_PINS[1]) == GPIO.LOW
            verdict_incident = combo_incident.evaluer(inc_a, inc_b, maintenant)
            incident_en_cours = verdict_incident == "en_cours"
            if verdict_incident == "declencher":
                threading.Thread(target=handle_signaler_incident, daemon=True).start()

            if verdict == "declencher":
                differes.clear()          # la combinaison l'emporte sur les actions retenues
                threading.Thread(target=handle_ecran_technique, daemon=True).start()
            elif verdict in ("relachee", "attente"):
                # Aucune combinaison : jouer les actions retenues dont la grâce
                # est écoulée. C'est ici que le bouton casque bascule vraiment
                # la sortie audio, 300 ms après l'appui.
                for broche in [p for p, t in differes.items() if maintenant - t >= COMBO_GRACE_S]:
                    del differes[broche]
                    LOGGER.info("Appui confirmé sur GPIO%s (différé %.0f ms)", broche, COMBO_GRACE_S * 1000)
                    HANDLERS.get(broche, handle_unassigned)(broche)

            for pin in PINS:
                st = states[pin]
                state = GPIO.input(pin)
                if state != st.last_state:
                    LOGGER.debug("Broche GPIO%s : %s -> %s", pin, "HIGH" if st.last_state else "LOW", "HIGH" if state else "LOW")
                    # TICKET-123 : tout front descendant, sur N'IMPORTE QUELLE
                    # broche, signale une présence au compositeur.
                    #
                    # Placé ICI et non dans les handlers, volontairement :
                    #   · un seul point d'insertion couvre les neuf boutons,
                    #     y compris les « tap ou maintien » dispatchés à part ;
                    #   · c'est indépendant de la logique de dispatch, donc un
                    #     futur bouton en bénéficiera sans qu'on y pense ;
                    #   · aucun risque de rendre la boucle molle (fonction
                    #     étranglée + thread détaché).
                    # Volontairement AVANT l'anti-rebond : un rebond parasite
                    # reste le signe que quelqu'un a touché l'appareil, et le
                    # throttle de 5 s absorbe les rafales.
                    if state == GPIO.LOW:
                        signaler_activite()

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
                            # TICKET-149 : pendant la combinaison de signalement,
                            # on saute la répétition. On n'annule PAS le premier
                            # appui (aucune latence ajoutée sur le volume), on
                            # empêche seulement les cinquante pas qu'entraîneraient
                            # cinq secondes d'appui simultané.
                            if incident_en_cours and pin in COMBO_INCIDENT_PINS:
                                st.last_repeat = now   # sans quoi la rafale repart au relâchement
                                continue
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
                            if pin in COMBO_PINS:
                                # TICKET-119 : on ne sait pas encore si c'est un
                                # appui isolé ou le début d'une combinaison. On
                                # retient l'action COMBO_GRACE_S ; elle sera
                                # jouée en tête de boucle si l'autre bouton ne
                                # suit pas, ou abandonnée si la combinaison part.
                                differes[pin] = now
                                LOGGER.debug("GPIO%s : action retenue %.0f ms (combinaison possible)",
                                             pin, COMBO_GRACE_S * 1000)
                            else:
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
