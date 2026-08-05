#!/usr/bin/env python3
"""
mpd_watchdog.py — Détecte un MPD figé et le remet en route (TICKET-122).

POURQUOI CE SCRIPT EXISTE
-------------------------
Le 2026-08-05, MPD est resté bloqué plus de 24 h en affichant `active (running)`
à systemd. Thomas était parti plusieurs heures avec son téléphone alors que le
Pi jouait une webradio via son partage de connexion. Le lien a disparu **sans
fermeture propre de la liaison TCP** : ni FIN, ni RST, puisque l'autre bout n'a
jamais su. La socket est restée `ESTABLISHED` indéfiniment.

Preuves relevées pendant la panne (détail dans docs/90-BACKLOG.md, TICKET-122) :
  - zéro CPU consommé, donc attente et non boucle folle ;
  - `ss -tnpo` sans champ `timer:` : aucune sonde keepalive, le noyau ne peut
    PAS découvrir que le pair est mort — MPD ne fait que lire ce flux, il
    n'émet rien, donc il n'y a aucune retransmission à expirer ;
  - thread `io` parqué en `io_cqring_wait` (lecture io_uring qui ne se termine
    jamais), et thread principal en `futex_wait` derrière lui ;
  - socket d'écoute avec une connexion en attente que personne n'accepte.

C'est une limite de MPD : le plugin d'entrée `curl` n'a de délai de garde que
sur la connexion initiale, aucun sur un flux qui stagne. Sur un appareil nomade
dont le réseau disparaît régulièrement, le cas se reproduira. Rien dans la
supervision existante ne le détecte : systemd voit le service vivant, et
`scripts/smoke_test.sh` l'interrogeait via `mpc`, qui se fige avec lui.

DEUX RÔLES
----------
1. GUÉRIR — sonder le socket Unix (le même que `radio.php`) avec un délai
   court ; après N échecs consécutifs, appliquer la séquence de récupération
   de docs/20-SETUP_SYSTEME.md §6.4.1. L'ordre y est impératif.
2. PRÉVENIR — si MPD répond, joue un flux **réseau**, et que la connectivité a
   disparu, arrêter proprement la lecture avant que MPD ne se fige. Un podcast
   local n'est jamais interrompu : Hechicero doit marcher hors réseau.

PRUDENCE DÉLIBÉRÉE
------------------
C'est l'enceinte d'un enfant : un chien de garde trop nerveux ferait plus de
dégâts que la panne. D'où les garde-fous : plusieurs échecs consécutifs avant
d'agir, et un plafond de récupérations par heure au-delà duquel on se contente
de journaliser. Mieux vaut rester en panne visible que boucler sur des
redémarrages.
"""

import argparse
import json
import logging
import os
import socket
import subprocess
import sys
import time
from collections import deque
from logging.handlers import RotatingFileHandler

# ── Réglages ──────────────────────────────────────────────────────────────
MPD_SOCKET = "/run/mpd/socket"   # le même transport que web/lecteur/radio.php
PROBE_TIMEOUT_S = 3.0            # généreux : radio.php se contente de 1,5 s
INTERVAL_S = 30                  # entre deux sondes
ECHECS_AVANT_ACTION = 3          # ~90 s de panne confirmée avant d'agir
OFFLINE_AVANT_STOP = 2           # ~60 s sans route avant de couper un flux
MAX_RECUPS_PAR_HEURE = 3         # au-delà : on journalise et on n'insiste plus

LOG_PATH = "/home/thomas/hechicero/data/mpd_watchdog.log"

log = logging.getLogger("mpd_watchdog")


def _init_log(verbeux: bool) -> None:
    log.setLevel(logging.DEBUG if verbeux else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                            "%Y-%m-%d %H:%M:%S")
    try:
        fichier = RotatingFileHandler(LOG_PATH, maxBytes=512_000, backupCount=2)
        fichier.setFormatter(fmt)
        log.addHandler(fichier)
    except OSError as e:
        # data/ est dans ReadWritePaths ; si ça échoue on continue sans fichier
        print(f"journal fichier indisponible ({e})", file=sys.stderr)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    log.addHandler(console)


# ── Dialogue MPD ──────────────────────────────────────────────────────────
class MpdInjoignable(Exception):
    """MPD n'a pas répondu dans le délai imparti."""


def _lire_jusqu_a_fin(f, deadline: float) -> list:
    """Lit les lignes jusqu'à OK/ACK. Lève MpdInjoignable si le délai expire.

    On ne lit jamais sans échéance : c'est tout l'intérêt de ce script de ne
    pas se figer comme le fait `mpc`.
    """
    lignes = []
    while True:
        if time.monotonic() > deadline:
            raise MpdInjoignable("délai dépassé pendant la lecture")
        ligne = f.readline()
        if not ligne:
            raise MpdInjoignable("connexion fermée par MPD")
        ligne = ligne.decode("utf-8", "replace").rstrip("\n")
        if ligne.startswith("OK"):
            return lignes
        if ligne.startswith("ACK"):
            raise MpdInjoignable(f"erreur MPD : {ligne}")
        lignes.append(ligne)


def interroger_mpd(commandes) -> dict:
    """Ouvre le socket, joue les commandes, renvoie les paires clé/valeur.

    Toute anomalie — connexion refusée, EAGAIN (socket d'écoute saturée parce
    que MPD n'accepte plus), silence — remonte en MpdInjoignable.
    """
    deadline = time.monotonic() + PROBE_TIMEOUT_S
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(PROBE_TIMEOUT_S)
        s.connect(MPD_SOCKET)
    except (OSError, socket.timeout) as e:
        raise MpdInjoignable(f"connexion impossible : {e}") from e

    try:
        with s, s.makefile("rwb") as f:
            banniere = f.readline()
            if not banniere.startswith(b"OK MPD"):
                raise MpdInjoignable(f"bannière inattendue : {banniere!r}")
            resultat = {}
            for cmd in commandes:
                f.write((cmd + "\n").encode())
                f.flush()
                for ligne in _lire_jusqu_a_fin(f, deadline):
                    cle, _, valeur = ligne.partition(": ")
                    resultat[cle] = valeur
            try:
                f.write(b"close\n")
                f.flush()
            except OSError:
                pass
            return resultat
    except (OSError, socket.timeout) as e:
        raise MpdInjoignable(f"échange interrompu : {e}") from e


def sonder() -> dict:
    """Sonde de vivacité. Renvoie l'état, ou lève MpdInjoignable."""
    return interroger_mpd(["status", "currentsong"])


def demander_stop() -> None:
    interroger_mpd(["stop"])


# ── Connectivité ──────────────────────────────────────────────────────────
def a_une_route() -> bool:
    """Y a-t-il encore une route par défaut ?

    Signal choisi parce qu'il est instantané et n'engage aucune I/O réseau —
    on ne veut surtout pas que le chien de garde puisse lui-même se bloquer.
    Quand le téléphone s'en va, l'association Wi-Fi tombe et la route
    disparaît en quelques secondes.

    Limite connue : un point d'accès encore présent mais sans Internet garde sa
    route. Ce cas n'est pas couvert, et c'est assumé — le volet « guérir »
    reste le filet.
    """
    try:
        r = subprocess.run(["ip", "route", "show", "default"],
                           capture_output=True, text=True, timeout=5)
        return bool(r.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        return True  # dans le doute, ne rien couper


def est_flux_reseau(etat: dict) -> bool:
    fichier = etat.get("file", "")
    return fichier.startswith("http://") or fichier.startswith("https://")


# ── Récupération ──────────────────────────────────────────────────────────
def _systemctl(*args, timeout: int = 30) -> bool:
    try:
        r = subprocess.run(["systemctl", *args],
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            log.warning("systemctl %s → %s", " ".join(args),
                        (r.stderr or r.stdout).strip())
        return r.returncode == 0
    except (subprocess.SubprocessError, OSError) as e:
        log.error("systemctl %s a échoué : %s", " ".join(args), e)
        return False


def _service_actif(unite: str) -> bool:
    try:
        r = subprocess.run(["systemctl", "is-active", unite],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() == "active"
    except (subprocess.SubprocessError, OSError):
        return False


def recuperer() -> bool:
    """Séquence de docs/20-SETUP_SYSTEME.md §6.4.1, adaptée à un MPD FIGÉ.

    ⚠️ Leçon du 2026-08-05, apprise en production : `systemctl stop
    mpd.service` **ne marche pas** sur un MPD bloqué. systemd envoie SIGTERM,
    mais le thread principal dort sur un futex et ne traitera jamais ce
    signal ; systemd attend alors tout son `TimeoutStopSec` (90 s par défaut)
    avant d'escalader en SIGKILL. Le job d'arrêt reste en file, et **tous les
    ordres suivants sur cette unité expirent derrière lui** — le
    `start mpd.socket` échouait pour cette seule raison.

    On va donc droit au SIGKILL. Un MPD figé ne s'arrête pas poliment.
    Coût accepté : l'état de lecture MPD n'est pas sauvegardé. C'est sans
    conséquence ici — `play_tracker.py` est la source de vérité du suivi
    d'écoute, et `restore_paused` gère la reprise au démarrage.

    L'ordre reste impératif : `mpd.service` doit être mort AVANT de relancer
    `mpd.socket`, sinon systemd répond « Socket service mpd.service already
    active, refusing ». Et `reset-failed` est indispensable si le disjoncteur
    anti-boucle a sauté.
    """
    log.warning("RÉCUPÉRATION — SIGKILL sur mpd.service (un MPD figé "
                "n'honore pas SIGTERM)")
    _systemctl("kill", "--signal=SIGKILL", "mpd.service", timeout=15)

    # ⚠️ Ne PAS attendre que mpd.service devienne inactif : il est activé par
    # socket, donc systemd le relance dès la première connexion. Mesuré le
    # 2026-08-05 : `is-active` répondait déjà `active` 3 s après le SIGKILL.
    # Une boucle d'attente sur l'inactivité échouerait systématiquement.
    # On sonde directement — c'est le seul juge qui compte.
    for tentative in range(1, 11):          # jusqu'à ~10 s
        time.sleep(1)
        try:
            etat = sonder()
            log.warning("RÉCUPÉRATION réussie en %s s après SIGKILL "
                        "(state=%s)", tentative, etat.get("state", "?"))
            return True
        except MpdInjoignable:
            continue

    # Le SIGKILL seul n'a pas suffi : le socket lui-même est peut-être en
    # échec (disjoncteur anti-boucle systemd, cf. §6.4.1). On le remet à zéro.
    log.warning("RÉCUPÉRATION — SIGKILL insuffisant, remise à zéro de "
                "mpd.socket")
    _systemctl("stop", "mpd.service", timeout=20)
    _systemctl("reset-failed", "mpd.socket", "mpd.service", timeout=15)
    if not _systemctl("start", "mpd.socket", timeout=30):
        log.error("mpd.socket n'a pas démarré")
        return False

    for tentative in range(1, 16):          # jusqu'à ~15 s
        time.sleep(1)
        try:
            etat = sonder()
            log.warning("RÉCUPÉRATION réussie après remise à zéro du socket "
                        "(state=%s)", etat.get("state", "?"))
            return True
        except MpdInjoignable:
            continue

    log.error("RÉCUPÉRATION ÉCHOUÉE — MPD ne répond toujours pas")
    return False


# ── Boucle principale ─────────────────────────────────────────────────────
def boucle() -> int:
    echecs = 0
    offline = 0
    recuperations = deque()          # horodatages, pour le plafond horaire

    log.info("Chien de garde MPD démarré (sonde %s toutes les %s s, "
             "action après %s échecs)", MPD_SOCKET, INTERVAL_S,
             ECHECS_AVANT_ACTION)

    while True:
        try:
            etat = sonder()
        except MpdInjoignable as e:
            echecs += 1
            log.warning("sonde en échec (%s/%s) : %s",
                        echecs, ECHECS_AVANT_ACTION, e)

            if echecs >= ECHECS_AVANT_ACTION:
                maintenant = time.monotonic()
                while recuperations and maintenant - recuperations[0] > 3600:
                    recuperations.popleft()

                if len(recuperations) >= MAX_RECUPS_PAR_HEURE:
                    # Volontaire : au-delà, le problème n'est pas un blocage
                    # ponctuel. Boucler sur des redémarrages rendrait
                    # l'appareil inutilisable et masquerait la vraie cause.
                    log.error("plafond de %s récupérations/heure atteint — "
                              "on n'insiste plus, MPD reste en panne "
                              "(inspecter à la main)", MAX_RECUPS_PAR_HEURE)
                    echecs = 0
                else:
                    recuperations.append(maintenant)
                    recuperer()
                    echecs = 0
        else:
            if echecs:
                log.info("MPD répond de nouveau (state=%s)",
                         etat.get("state", "?"))
            echecs = 0

            # ── Prévention ────────────────────────────────────────────────
            if etat.get("state") == "play" and est_flux_reseau(etat):
                if a_une_route():
                    offline = 0
                else:
                    offline += 1
                    log.warning("flux réseau en lecture sans route par défaut "
                                "(%s/%s)", offline, OFFLINE_AVANT_STOP)
                    if offline >= OFFLINE_AVANT_STOP:
                        log.warning("arrêt préventif de « %s » avant que MPD "
                                    "ne se fige dessus", etat.get("file", "?"))
                        try:
                            demander_stop()
                        except MpdInjoignable as e:
                            log.error("arrêt préventif impossible : %s", e)
                        offline = 0
            else:
                offline = 0

        time.sleep(INTERVAL_S)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--probe", action="store_true",
                   help="sonde unique : code 0 si MPD répond, 1 sinon "
                        "(utilisé par scripts/smoke_test.sh)")
    p.add_argument("--recover", action="store_true",
                   help="force la séquence de récupération §6.4.1 puis sort")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    _init_log(args.verbose)

    if args.probe:
        try:
            etat = sonder()
        except MpdInjoignable as e:
            print(f"MPD INJOIGNABLE : {e}")
            return 1
        print(f"MPD OK (state={etat.get('state', '?')}, "
              f"file={etat.get('file', '-')})")
        return 0

    if args.recover:
        return 0 if recuperer() else 1

    try:
        return boucle()
    except KeyboardInterrupt:
        log.info("arrêt demandé")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
