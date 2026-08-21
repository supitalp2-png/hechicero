#!/usr/bin/env python3
"""Tests de `mpd_watchdog` — TICKET-122.

Le chien de garde est installé depuis le 2026-08-05 et **n'a jamais été
éprouvé** : il faudrait qu'un flux meure vraiment pour le voir agir. Ces tests
couvrent ce qui est couvrable **sans risque** — la logique de décision — et
laissent explicitement de côté ce qui ne l'est pas : le SIGKILL et le
redémarrage du service.

⚠️ Ne prouve donc PAS que la récupération fonctionne. Prouve qu'on décide de la
déclencher au bon moment, ce qui est la moitié qui se teste à froid.

Tests de COMPORTEMENT : aucune socket, aucun service, aucun réseau touché.
    python3 scripts/test_mpd_watchdog.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mpd_watchdog as mw  # noqa: E402

echecs: list[str] = []


def verifie(nom: str, obtenu, attendu) -> None:
    if obtenu == attendu:
        print(f"  ok   {nom}")
    else:
        print(f"  ÉCHEC {nom}\n       obtenu  : {obtenu}\n       attendu : {attendu}")
        echecs.append(nom)


# ── 1. Reconnaître un flux réseau ──────────────────────────────────────────
# C'est ce qui distingue une webradio (dont le flux peut mourir sans que MPD
# s'en aperçoive) d'un podcast local, qui ne pose jamais ce problème.
verifie("flux https reconnu comme réseau",
        mw.est_flux_reseau({"file": "https://stream.radiofrance.fr/franceinter.m3u8"}), True)
verifie("flux http reconnu comme réseau",
        mw.est_flux_reseau({"file": "http://icecast.radiofrance.fr/x.mp3"}), True)
verifie("podcast local n'est PAS un flux réseau",
        mw.est_flux_reseau({"file": "/home/pi/podcasts/lesodyssees/audio/ep1.mp3"}), False)
verifie("aucun fichier en cours : pas un flux réseau",
        mw.est_flux_reseau({}), False)

# ── 2. Détection de route ──────────────────────────────────────────────────
# ⚠️ En cas d'ERREUR de la commande, la fonction doit répondre True — « dans le
# doute, ne rien couper ». Un chien de garde qui coupe la musique parce qu'il
# n'a pas réussi à lire la table de routage serait pire que le bug qu'il traite.
import subprocess  # noqa: E402

vrai_run = subprocess.run


class Res:
    def __init__(self, sortie): self.stdout = sortie


subprocess.run = lambda *a, **k: Res("default via 192.168.1.1 dev wlan0\n")
verifie("route présente", mw.a_une_route(), True)

subprocess.run = lambda *a, **k: Res("")
verifie("aucune route", mw.a_une_route(), False)


def _boom(*a, **k):
    raise OSError("commande indisponible")


subprocess.run = _boom
verifie("commande en échec : on répond « route présente » (ne rien couper)",
        mw.a_une_route(), True)
subprocess.run = vrai_run

# ── 3. Le seuil avant action ───────────────────────────────────────────────
# 3 échecs consécutifs à 30 s d'intervalle ≈ 90 s de panne confirmée. Agir au
# premier échec redémarrerait MPD sur un simple hoquet, en pleine écoute.
verifie("action après 3 échecs, pas au premier", mw.ECHECS_AVANT_ACTION, 3)
verifie("plafond horaire de récupérations défini", mw.MAX_RECUPS_PAR_HEURE > 0, True)

print()
if echecs:
    print(f"⛔ {len(echecs)} test(s) en échec : {', '.join(echecs)}")
    raise SystemExit(1)
print("🟢 chien de garde MPD : tous les tests passent")
print("   ⚠️ la RÉCUPÉRATION (SIGKILL + redémarrage) reste non éprouvée — "
      "voir TICKET-122")
