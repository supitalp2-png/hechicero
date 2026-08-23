#!/usr/bin/env python3
"""kiosk_freeze_watch.py — guetteur de gel du kiosque (TICKET-127).

POURQUOI CE SCRIPT EXISTE
─────────────────────────
Le 2026-08-17, l'écran d'Hechicero est resté noir et figé. Tout le reste allait
bien : MPD jouait, les boutons GPIO répondaient, `wlr-randr` annonçait
`Enabled: yes` au mode natif, et `data/screen_dpms.log` ne contenait aucun `off`
— la dalle n'avait donc jamais été éteinte. Seul un hard reset a rétabli
l'image.

La trace décisive était dans `data/sleep_debug.log` : après un `activate_sleep`
à 07:47:38, la boucle de 5 minutes de la page a écrit `apply_sleep_config` à
07:47:48 puis 07:52:48, et **plus jamais**. La page avait cessé d'exécuter du
JavaScript, en laissant l'overlay de veille comme dernière image peinte.

Ce qui manquait pour corriger sur des faits : savoir à quelle seconde le JS
meurt, et dans quel état se trouvaient Chromium, la mémoire et l'alimentation à
cet instant précis. Un `journalctl` consulté deux heures plus tard ne le dit
plus.

CE QU'IL FAIT
─────────────
Il lit `data/kiosk_heartbeat.json`, écrit toutes les 15 s par la page
(`radio.php?action=kiosk_beat`). Quand le battement dépasse STALE_AFTER_S, il
écrit **un seul** instantané médico-légal dans `data/kiosk_freeze.log`, puis se
tait jusqu'au retour du battement.

CE QU'IL NE FAIT PAS
────────────────────
Il **n'agit jamais**. Pas de relance de Chromium, pas de rebond de mode, pas de
`mpc`. Décision de Thomas (2026-08-17) : on observe d'abord, on décide ensuite.
Un guetteur qui répare masque la panne et fait perdre la fenêtre d'observation.

Deux pièges du projet respectés :
  - **Jamais `mpc`** : face à un MPD figé, `mpc` n'échoue pas, il attend, et le
    guetteur se figerait avec lui. On sonde `/run/mpd/socket` sous délai de
    garde (leçon de TICKET-122).
  - **Toute commande sous `timeout`** : un instantané ne doit jamais pouvoir
    bloquer indéfiniment, sinon le guetteur meurt en silence au pire moment.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path("/home/thomas/hechicero")
DATA_DIR = PROJECT_ROOT / "data"
HEARTBEAT_PATH = DATA_DIR / "kiosk_heartbeat.json"
FREEZE_LOG = DATA_DIR / "kiosk_freeze.log"

POLL_SECONDS = 20
# 60 s = quatre battements manqués. Assez pour ne pas crier sur un hoquet
# réseau ou une seconde de charge CPU, assez court pour attraper l'état de la
# machine pendant que la panne est encore fraîche.
STALE_AFTER_S = 60

# ── TICKET-147 — un saut d'horloge n'est pas un gel ──────────────────────────
# Les DEUX seules alertes émises par ce guetteur depuis sa mise en service
# étaient fausses, et pour la même raison :
#
#   22/08 09:28:32  timesyncd: Initial clock synchronization
#   22/08 09:28:44  GEL DÉTECTÉ — battement silencieux depuis 77 s
#   23/08 11:39:23  timesyncd: Initial clock synchronization
#   23/08 11:39:35  GEL DÉTECTÉ — battement silencieux depuis 516 s
#
# Le Pi démarre sans réseau : son horloge repart de la dernière date connue,
# puis **bondit** quand le NTP répond. `age` compare deux heures murales — le
# dernier battement, écrit avant le bond, et `time.time()` d'après. L'écart
# mesuré n'est pas un silence, c'est la taille du saut. Dans les deux cas la
# page n'avait jamais cessé de tourner : « battement REVENU » arrive 21 s plus
# tard avec un âge de 4 à 5 s.
#
# ⚠️ Ce n'est pas un détail cosmétique. Un guetteur qui crie au loup rend
# invisible le vrai gel qu'il est censé attraper — toute l'instrumentation du
# TICKET-127 ne valait plus rien.
#
# Deux protections, indépendantes :
#   1. On surveille la dérive entre l'horloge murale et l'horloge monotone.
#      Elle est constante sauf quand le système REPOSITIONNE l'heure. Un écart
#      brusque = un pas d'horloge, et l'évaluation du tour est jetée.
#   2. Un silence doit être confirmé sur deux tours consécutifs. Un vrai gel
#      dure ; un artefact ne survit pas au tour suivant. Coût : 20 s de retard
#      sur l'instantané, ce qui ne change rien à sa valeur médico-légale.
SAUT_HORLOGE_S = 2.0
CONFIRMATIONS = 2
# Garde-fou de taille : ce journal est en append. Un instantané fait ~3 ko ;
# à 400 ko on a de la place pour une centaine d'épisodes, largement de quoi
# comprendre. Au-delà on repart à zéro plutôt que de remplir la carte SD —
# c'est ce qui est arrivé à data/sleep_debug.log (plusieurs Mo, octets NUL).
MAX_LOG_BYTES = 400_000
CMD_TIMEOUT = 5


def run(cmd: list[str], timeout: int = CMD_TIMEOUT) -> str:
    """Exécute une commande et renvoie sa sortie. N'échoue jamais : un
    instantané partiel vaut infiniment mieux qu'un guetteur mort."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        return out.strip() or "(vide)"
    except FileNotFoundError:
        return f"(commande absente : {cmd[0]})"
    except subprocess.TimeoutExpired:
        return f"(délai de garde dépassé après {timeout}s)"
    except Exception as e:  # noqa: BLE001
        return f"(erreur : {e})"


def derive_horloge() -> float:
    """
    Écart entre l'horloge murale et l'horloge monotone.

    Cette valeur ne bouge pas tant que personne ne repositionne l'heure. Elle
    saute exactement de la taille du pas quand NTP corrige l'horloge — c'est le
    seul signal fiable pour distinguer « le temps a passé » de « l'heure a
    changé ». `time.monotonic()` seul ne suffirait pas : le battement est
    horodaté par le navigateur, dans un autre processus.
    """
    return time.time() - time.monotonic()


class DetecteurGel:
    """
    Décide si un silence du battement est un vrai gel (TICKET-147).

    Sépare la décision de tout le reste — fichiers, commandes, journaux — pour
    qu'elle soit vérifiable sans Pi, sans Chromium et sans attendre une panne.

    `evaluer()` renvoie :
      'saut_horloge' — l'heure a été repositionnée, ce tour ne compte pas
      'suspect'      — silence constaté, pas encore confirmé
      'alerte'       — silence confirmé : prendre l'instantané (une seule fois)
      'retour'       — le battement est revenu après une alerte
      'ok'           — rien à signaler
    """

    def __init__(self, seuil_s: float = STALE_AFTER_S,
                 saut_max_s: float = SAUT_HORLOGE_S,
                 confirmations: int = CONFIRMATIONS) -> None:
        self.seuil_s = seuil_s
        self.saut_max_s = saut_max_s
        self.confirmations = max(1, confirmations)
        self._derive: float | None = None
        self._consecutifs = 0
        self._signale = False
        self.dernier_saut_s = 0.0

    def evaluer(self, age_s: float, derive_s: float) -> str:
        saut = None if self._derive is None else derive_s - self._derive
        self._derive = derive_s

        if saut is not None and abs(saut) > self.saut_max_s:
            # L'heure vient d'être repositionnée : `age_s` est faux de la taille
            # du pas. On repart de zéro plutôt que de conclure sur une mesure
            # qu'on sait corrompue.
            self.dernier_saut_s = saut
            self._consecutifs = 0
            return "saut_horloge"

        if age_s < 0:
            # Battement daté dans le futur — horloge partie en arrière, ou page
            # et système désaccordés. Jamais un gel.
            self._consecutifs = 0
            return "saut_horloge"

        if age_s > self.seuil_s:
            self._consecutifs += 1
            if self._signale:
                return "ok"
            if self._consecutifs >= self.confirmations:
                self._signale = True
                return "alerte"
            return "suspect"

        self._consecutifs = 0
        if self._signale:
            self._signale = False
            return "retour"
        return "ok"


def read_heartbeat() -> dict | None:
    try:
        with HEARTBEAT_PATH.open("r", encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def mpd_socket_alive() -> str:
    """Sonde /run/mpd/socket — JAMAIS `mpc`, qui attendrait indéfiniment sur un
    MPD figé et emporterait le guetteur avec lui (leçon TICKET-122)."""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect("/run/mpd/socket")
        banner = s.recv(64).decode("utf-8", "replace").strip()
        s.close()
        return f"OK — {banner}"
    except Exception as e:  # noqa: BLE001
        return f"INJOIGNABLE — {type(e).__name__}: {e}"


def chromium_processes() -> str:
    """État des processus Chromium. `stat` et `wchan` sont les colonnes qui
    comptent : un thread en `D` (I/O ininterruptible) ou parqué sur un wchan
    inattendu ne raconte pas la même histoire qu'un processus tué."""
    out = run(["ps", "-eo", "pid,ppid,stat,pcpu,pmem,rss,wchan:24,etime,comm,args"])
    lines = [l for l in out.splitlines() if "chromium" in l.lower() or "PID" in l]
    if not lines:
        return "(aucun processus chromium trouvé — le navigateur a disparu)"
    # On tronque les args, une ligne de commande Chromium fait 800 caractères
    return "\n".join(l[:260] for l in lines[:25])


def snapshot(reason: str, beat: dict | None, age_s: float | None) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts: list[str] = []
    parts.append("=" * 78)
    parts.append(f"[{now}] GEL DÉTECTÉ — {reason}")
    parts.append("=" * 78)

    # 1. Le dernier signe de vie de la page : c'est lui qui date la mort et qui
    #    dit si l'overlay de veille était affiché au moment du gel.
    parts.append("\n── dernier battement ──")
    if beat is None:
        parts.append("(illisible ou absent)")
    else:
        parts.append(
            f"iso={beat.get('iso')}  écran={beat.get('screen')}  "
            f"overlay_veille={beat.get('overlay')}  mpd={beat.get('mpd_state')}"
        )
        parts.append(
            f"âge de la page={beat.get('page_age_s')}s  battements={beat.get('beats')}"
        )
        parts.append(
            f"silence depuis {age_s:.0f}s" if age_s is not None else "silence : durée inconnue"
        )

    # 2. Sous-tension / throttling : LE suspect principal. La panne est apparue
    #    juste après un remplacement de cellules (TICKET-126). Un Pi 5 qui
    #    broute fige le GPU avant de rebooter, et ça ne se lit que dans ce
    #    registre — pas dans une supposition.
    #    Bits : 0=under-voltage now, 1=freq capped, 2=throttled, 3=soft temp
    #    limit ; 16..19 = mêmes événements SURVENUS depuis le boot.
    parts.append("\n── alimentation / throttling (vcgencmd) ──")
    parts.append(f"get_throttled : {run(['vcgencmd', 'get_throttled'])}")
    parts.append(f"measure_volts : {run(['vcgencmd', 'measure_volts'])}")
    parts.append(f"measure_temp  : {run(['vcgencmd', 'measure_temp'])}")

    # 3. Ce que le Pi croit afficher — à confronter à ce qu'on voit.
    parts.append("\n── sortie vidéo (wlr-randr) ──")
    parts.append(run(["wlr-randr"]))

    # 4. Chromium est-il mort, zombie, ou vivant mais muet ?
    parts.append("\n── processus chromium ──")
    parts.append(chromium_processes())

    # 5. Mémoire : un OOM-killer qui fauche le renderer laisse Chromium debout
    #    avec un onglet mort — exactement le symptôme observé.
    parts.append("\n── mémoire ──")
    parts.append(run(["free", "-m"]))

    # 6. Les journaux, pris MAINTENANT. C'est tout l'intérêt : dans deux heures
    #    ils auront défilé.
    parts.append("\n── dmesg (30 dernières lignes) ──")
    parts.append("\n".join(run(["dmesg", "--ctime"]).splitlines()[-30:]))

    parts.append("\n── journal utilisateur, 10 dernières minutes ──")
    parts.append(
        "\n".join(
            run(["journalctl", "--user", "--since", "-10min", "--no-pager"], timeout=10).splitlines()[-40:]
        )
    )

    parts.append("\n── journal système (labwc/chromium/seatd), 10 dernières minutes ──")
    parts.append(
        "\n".join(
            run(["journalctl", "--since", "-10min", "--no-pager"], timeout=10).splitlines()[-40:]
        )
    )

    # 7. Confirmer que l'audio, lui, allait bien : c'est la signature de cette
    #    panne (la page meurt, MPD survit).
    parts.append("\n── socket MPD ──")
    parts.append(mpd_socket_alive())

    parts.append("")
    return "\n".join(p for p in parts if p is not None)


def append_log(text: str) -> None:
    try:
        if FREEZE_LOG.exists() and FREEZE_LOG.stat().st_size > MAX_LOG_BYTES:
            FREEZE_LOG.write_text(
                f"(journal remis à zéro le {datetime.now():%Y-%m-%d %H:%M:%S}, "
                f"il dépassait {MAX_LOG_BYTES} octets)\n",
                encoding="utf-8",
            )
        with FREEZE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(FREEZE_LOG, 0o664)
    except Exception as e:  # noqa: BLE001
        print(f"écriture de {FREEZE_LOG} impossible : {e}", file=sys.stderr, flush=True)


def main() -> int:
    if "--test" in sys.argv:
        # Prend un instantané immédiat, quel que soit l'état du battement.
        # Sert à vérifier que toutes les commandes répondent et que le fichier
        # est bien écrit, SANS attendre une vraie panne.
        beat = read_heartbeat()
        age = None
        if beat and beat.get("ts"):
            age = time.time() - (beat["ts"] / 1000.0)
        text = snapshot("INSTANTANÉ DE TEST (--test), pas une vraie panne", beat, age)
        append_log(text)
        print(text)
        return 0

    print(
        f"kiosk_freeze_watch démarré — sonde {HEARTBEAT_PATH.name} toutes les "
        f"{POLL_SECONDS}s, alerte au-delà de {STALE_AFTER_S}s de silence",
        flush=True,
    )
    detecteur = DetecteurGel()
    while True:
        beat = read_heartbeat()
        if beat is None or not beat.get("ts"):
            # Pas encore de battement (page jamais chargée depuis l'ajout, ou
            # fichier absent). On ne crie pas : ce n'est pas une panne.
            time.sleep(POLL_SECONDS)
            continue

        age = time.time() - (beat["ts"] / 1000.0)
        verdict = detecteur.evaluer(age, derive_horloge())

        if verdict == "saut_horloge":
            # On garde la trace : c'est ce qui a produit deux fausses alertes
            # avant le TICKET-147, et il faut pouvoir le reconnaître si ça
            # recommence. Une ligne, pas un instantané de 3 ko.
            saut = detecteur.dernier_saut_s
            print(f"saut d'horloge de {saut:+.0f}s — évaluation ignorée", flush=True)
            append_log(
                f"[{datetime.now():%Y-%m-%d %H:%M:%S}] saut d'horloge {saut:+.0f}s "
                f"(âge apparent {age:.0f}s) — PAS un gel, évaluation ignorée\n"
            )
        elif verdict == "suspect":
            print(f"silence de {age:.0f}s — attente de confirmation", flush=True)
        elif verdict == "alerte":
            print(f"battement silencieux depuis {age:.0f}s — instantané", flush=True)
            append_log(snapshot(f"battement silencieux depuis {age:.0f}s", beat, age))
        elif verdict == "retour":
            print(f"battement revenu (âge {age:.0f}s) — guetteur réarmé", flush=True)
            append_log(
                f"[{datetime.now():%Y-%m-%d %H:%M:%S}] battement REVENU "
                f"(âge {age:.0f}s, écran={beat.get('screen')}, "
                f"overlay={beat.get('overlay')}, âge page={beat.get('page_age_s')}s)\n"
                f"  → si âge de la page < durée du gel, la page a été rechargée "
                f"(hard reset) ; sinon elle est repartie seule.\n\n"
            )
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
