#!/usr/bin/env python3
"""
clic_confirmation.py — Accusé de réception sonore (TICKET-149).

POURQUOI UN SON
───────────────
Le signalement d'un écran noir se fait par une combinaison de boutons, et par
définition **l'écran est noir** : la confirmation ne peut pas être visuelle.
Sans retour, Thomas ne saurait pas si son appui a été pris en compte, et
appuierait plusieurs fois — ce qui produirait des constats en double.

DEUX CHEMINS, DANS CET ORDRE
────────────────────────────
1. `aplay` directement sur ALSA. Gratuit : ne touche ni à la file de lecture ni
   à la position. Fonctionne quand rien ne joue — le cas le plus probable,
   puisque l'écran s'éteint après une longue inactivité.
2. Si le périphérique est occupé, on passe par MPD, ce qui **interrompt** la
   lecture ~1 s. Décision de Thomas (2026-08-25) : quand l'écran est noir
   l'appareil est déjà en panne, une brève coupure est un prix dérisoire. On
   restaure tout de même la piste et la position — la perdre serait gratuit.

⚠️ **Jamais `mpc` sans délai de garde.** Face à un MPD figé, `mpc` n'échoue
pas : il attend. Le daemon des boutons resterait bloqué et l'appareil perdrait
ses boutons physiques (leçon TICKET-122, zone Z1). Toutes les commandes ici
passent par la socket avec un `settimeout`, ou par `subprocess` avec `timeout`.
"""
from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SON = PROJECT_ROOT / "sounds" / "clic_incident.wav"
MPD_SOCKET = "/run/mpd/socket"

APLAY_TIMEOUT = 4
MPD_TIMEOUT = 3.0
VOLUME_CLIC = 55

# ── Pourquoi les échecs sont bruyants ici ────────────────────────────────────
# Première version : chaque chemin renvoyait False sur exception, sans un mot.
# Résultat le 2026-08-26 — « clic de confirmation : aucun », et rien pour
# savoir lequel des deux avait échoué ni pourquoi. Un outil de diagnostic qui
# tait ses erreurs fait perdre exactement le temps qu'il devait faire gagner.
# Toutes les raisons partent sur stderr : elles n'encombrent pas la sortie
# normale, et `buttons_daemon` les capture déjà dans son journal.
RAISONS: list[str] = []


def _raison(chemin: str, message: str) -> None:
    RAISONS.append(f"{chemin} : {message}")
    print(f"  ↳ {chemin} a échoué — {message}", file=sys.stderr)


ETAT_SORTIE = PROJECT_ROOT / "data" / "audio_output_state.json"
PERIPH_PAR_MODE = {"hp": "eqhp", "casque": "eqcasque"}


def periph_actif() -> str:
    """
    Périphérique ALSA de la sortie **réellement en service**.

    ⚠️ Ne JAMAIS s'en remettre au périphérique par défaut. `pcm.!default` pointe
    sur `hw:CARD=Audio`, c'est-à-dire le DAC USB du casque. Un `aplay` nu joue
    donc dans le casque quoi qu'il arrive — et renvoie 0. Constaté le
    2026-08-26 : Thomas écoutait sur les haut-parleurs, n'a rien entendu, et le
    script s'est déclaré satisfait.

    La leçon dépasse ce script : **juger un son sur un code de retour ne prouve
    rien.** ALSA rend 0 dès qu'il a écrit les échantillons quelque part, pas
    quand quelqu'un les a entendus. Il faut donc viser explicitement la sortie
    active, qui est celle que MPD utilise (`eqhp` ou `eqcasque`).
    """
    try:
        import json
        mode = json.loads(ETAT_SORTIE.read_text(encoding="utf-8")).get("mode", "hp")
    except Exception:
        mode = "hp"
    return PERIPH_PAR_MODE.get(mode, "eqhp")


def jouer_aplay() -> bool:
    """
    Chemin sans effet de bord, sur la sortie active.

    Faux si le périphérique est occupé — c'est précisément le signal qu'il faut
    passer par MPD, qui le détient.
    """
    if not SON.exists():
        _raison("aplay", f"son introuvable : {SON}")
        return False
    periph = periph_actif()
    try:
        p = subprocess.run(["aplay", "-q", "-D", periph, str(SON)],
                           capture_output=True, text=True, timeout=APLAY_TIMEOUT)
        if p.returncode == 0:
            return True
        _raison("aplay", f"-D {periph} → code {p.returncode} : "
                         f"{(p.stderr or p.stdout or '').strip()[:200]}")
        return False
    except Exception as e:  # noqa: BLE001
        _raison("aplay", f"-D {periph} → {type(e).__name__}: {e}")
        return False


class MpdBref:
    """
    Client MPD minimal, sur socket, avec délai de garde sur chaque échange.

    ⚠️ **Lire ligne par ligne, jamais en cherchant une sous-chaîne.** Première
    version : j'attendais `b"OK\\n"` dans le tampon. Mais la bannière d'accueil
    de MPD vaut `OK MPD 0.23.12\\n` — elle ne contient pas la sous-chaîne
    `OK\\n`. Le client attendait donc une réponse déjà reçue, jusqu'au délai de
    garde, et le diagnostic annonçait « socket injoignable » sur un MPD en
    parfaite santé (2026-08-26). Un faux négatif sur la santé de MPD est
    particulièrement coûteux ici : c'est exactement le symptôme du TICKET-122.

    Le protocole est délimité par des lignes : une réponse se termine par une
    ligne valant exactement `OK`, ou commençant par `ACK `. On lit donc avec un
    `makefile`, qui gère le tamponnage correctement.
    """

    def __init__(self, socket_connectee=None) -> None:
        # `socket_connectee` n'existe que pour les tests : il permet de
        # brancher une socketpair et de vérifier le dialogue sans MPD ni Pi.
        # Sans ça le bug de la bannière n'aurait jamais pu être couvert — il
        # n'apparaît qu'au contact du vrai protocole.
        if socket_connectee is not None:
            self.s = socket_connectee
        else:
            self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.s.settimeout(MPD_TIMEOUT)
            self.s.connect(MPD_SOCKET)
        self.f = self.s.makefile("rwb")
        self.banniere = self.f.readline().decode("utf-8", "replace").strip()
        if not self.banniere.startswith("OK MPD"):
            raise RuntimeError(f"bannière inattendue : {self.banniere!r}")

    def cmd(self, ligne: str) -> str:
        self.f.write((ligne + "\n").encode("utf-8"))
        self.f.flush()
        lignes: list[bytes] = []
        while True:
            l = self.f.readline()
            if not l:                      # socket fermée
                break
            if l == b"OK\n":
                break
            lignes.append(l)
            if l.startswith(b"ACK "):      # erreur : MPD n'enverra pas de OK
                break
        return b"".join(lignes).decode("utf-8", "replace")

    def status(self) -> dict[str, str]:
        d: dict[str, str] = {}
        for l in self.cmd("status").splitlines():
            if ": " in l:
                k, v = l.split(": ", 1)
                d[k] = v
        return d

    def fermer(self) -> None:
        for objet in (getattr(self, "f", None), self.s):
            try:
                if objet is not None:
                    objet.close()
            except Exception:
                pass


def jouer_via_mpd() -> bool:
    """
    Interrompt la lecture le temps du clic, puis rétablit piste et position.

    Assumé : l'écran est noir, donc l'appareil est déjà en panne.
    """
    if not SON.exists():
        _raison("mpd", f"son introuvable : {SON}")
        return False
    mpd = None
    try:
        mpd = MpdBref()
        st = mpd.status()
        etat = st.get("state", "stop")
        piste = st.get("song")
        position = st.get("elapsed")
        volume = st.get("volume")

        mpd.cmd("pause 1")
        mpd.cmd(f"setvol {VOLUME_CLIC}")
        # `addid` place le fichier sans vider la file : la playlist de l'enfant
        # survit, seule la position de lecture bouge le temps du clic.
        #
        # ⚠️ Schéma `file://` obligatoire : le son est hors du dossier musique
        # de MPD, un chemin nu serait rejeté. Et surtout, PAS un fichier dans
        # /tmp comme le fait play_chime.py — buttons_daemon.service porte
        # `PrivateTmp=true`, son /tmp n'est pas celui de MPD, qui ne verrait
        # jamais le fichier. Un fichier du dépôt est visible des deux côtés.
        rep = mpd.cmd(f'addid "file://{SON}"')
        ident = None
        for l in rep.splitlines():
            if l.startswith("Id: "):
                ident = l.split(": ", 1)[1]
        if ident is None:
            _raison("mpd", f"addid refusé — réponse : {rep.strip()[:200]}")
            return False
        mpd.cmd(f"playid {ident}")
        import time
        time.sleep(1.0)
        mpd.cmd("stop")
        mpd.cmd(f"deleteid {ident}")

        if volume:
            mpd.cmd(f"setvol {volume}")
        if piste is not None:
            mpd.cmd(f"play {piste}")
            if position:
                mpd.cmd(f"seekcur {position}")
            if etat != "play":
                mpd.cmd("pause 1")
        return True
    except Exception as e:  # noqa: BLE001
        _raison("mpd", f"{type(e).__name__}: {e}")
        return False
    finally:
        if mpd is not None:
            mpd.fermer()


def confirmer() -> str:
    """Renvoie le chemin utilisé : 'aplay', 'mpd' ou 'aucun'."""
    if jouer_aplay():
        return "aplay"
    if jouer_via_mpd():
        return "mpd"
    return "aucun"


def diagnostiquer() -> None:
    """Ce qu'il faut savoir quand aucun son ne sort. Aucune lecture, aucun effet."""
    import json
    print("── sortie audio active ──")
    try:
        print(f"  {ETAT_SORTIE.name} : {ETAT_SORTIE.read_text(encoding='utf-8').strip()}")
    except Exception as e:  # noqa: BLE001
        print(f"  illisible : {e}")
    print(f"  périphérique visé : {periph_actif()}")
    print(f"  son : {SON} ({'présent' if SON.exists() else 'ABSENT'}"
          + (f", {SON.stat().st_size} octets)" if SON.exists() else ")"))

    print("── état MPD ──")
    try:
        m = MpdBref()
        print(f"  bannière : {m.banniere}")
        st = m.status()
        print(f"  state={st.get('state')} song={st.get('song')} "
              f"elapsed={st.get('elapsed')} volume={st.get('volume')}")
        # Le point qui reste incertain : MPD accepte-t-il un fichier hors de
        # son dossier musique ? On le lui demande sans jouer quoi que ce soit.
        rep = m.cmd(f'addid "file://{SON}"')
        ident = next((l.split(": ", 1)[1] for l in rep.splitlines()
                      if l.startswith("Id: ")), None)
        if ident:
            print(f"  addid file:// accepté (Id={ident}) — retiré aussitôt")
            m.cmd(f"deleteid {ident}")
        else:
            print(f"  addid file:// REFUSÉ : {rep.strip()[:200]}")
        m.fermer()
    except Exception as e:  # noqa: BLE001
        print(f"  socket injoignable : {type(e).__name__}: {e}")

    print("── périphériques ALSA déclarés ──")
    print(subprocess.run(["aplay", "-L"], capture_output=True, text=True,
                         timeout=10).stdout[:700] or "(rien)")


if __name__ == "__main__":
    if "--diag" in sys.argv:
        diagnostiquer()
        sys.exit(0)
    resultat = confirmer()
    print(f"clic de confirmation : {resultat}")
    if resultat == "aucun":
        print("Raisons : " + " | ".join(RAISONS) if RAISONS else "Raisons : aucune capturée",
              file=sys.stderr)
        print("Diagnostic : python3 scripts/clic_confirmation.py --diag", file=sys.stderr)
    sys.exit(0 if resultat != "aucun" else 1)
