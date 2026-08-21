#!/usr/bin/env python3
"""Tests de `buttons_daemon.http_get()` — TICKET-132.

Test de COMPORTEMENT et non de forme : on remplace `urllib.request.urlopen` et
on regarde ce qui est journalisé. Un `grep` sur le code aurait cassé au premier
remaniement, et aurait pu trouver la docstring qui décrit le bug (trois gardes
s'y sont fait prendre le 2026-08-21 — voir 75-NON_REGRESSION §5bis).

Sans effet de bord : aucun réseau, aucun fichier, aucun GPIO.
    python3 scripts/test_boutons.py
"""
from __future__ import annotations

import logging
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import buttons_daemon as bd  # noqa: E402

echecs: list[str] = []
journal: list[tuple[str, str]] = []


class Capteur(logging.Handler):
    def emit(self, record):
        journal.append((record.levelname, record.getMessage()))


bd.LOGGER.addHandler(Capteur())
bd.LOGGER.setLevel(logging.DEBUG)


def verifie(nom: str, obtenu, attendu) -> None:
    if obtenu == attendu:
        print(f"  ok   {nom}")
    else:
        print(f"  ÉCHEC {nom}\n       obtenu  : {obtenu}\n       attendu : {attendu}")
        echecs.append(nom)


class Reponse:
    def __init__(self, corps: str):
        self._corps = corps.encode("utf-8")

    def read(self):
        return self._corps

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def repond(corps: str):
    urllib.request.urlopen = lambda *a, **k: Reponse(corps)


def plante(message: str):
    def _boom(*a, **k):
        raise OSError(message)
    urllib.request.urlopen = _boom


# ── 1. LE CAS DU BUG — `action=pause` renvoie du HTML, pas du JSON ─────────
# radio.php exécute bien la commande MPD puis retombe sur sa vieille page de
# débogage. L'appui FONCTIONNE ; seul le format de retour diffère. Avant le
# correctif, chaque appui produisait un WARNING, et le journal de
# buttons_daemon en devenait illisible.
repond("<html>debug</html>")
journal.clear()
verifie("réponse HTML : rien n'est renvoyé", bd.http_get("action=pause"), None)
verifie("réponse HTML : AUCUN avertissement",
        [n for n, _ in journal if n == "WARNING"], [])

# ── 2. Une vraie réponse JSON reste exploitée ──────────────────────────────
repond('{"ok": true}')
verifie("réponse JSON : renvoyée telle quelle", bd.http_get("action=x"), {"ok": True})

# ── 3. Une VRAIE panne doit continuer d'alerter ────────────────────────────
# ⚠️ C'est la moitié qu'il ne fallait pas perdre en corrigeant le bruit : si on
# avait simplement supprimé le warning, une panne réseau réelle serait devenue
# silencieuse — on aurait remplacé un journal illisible par un journal muet.
plante("connexion refusée")
journal.clear()
verifie("panne réseau : rien n'est renvoyé", bd.http_get("action=x"), None)
verifie("panne réseau : avertissement CONSERVÉ",
        any(n == "WARNING" for n, _ in journal), True)

print()
if echecs:
    print(f"⛔ {len(echecs)} test(s) en échec : {', '.join(echecs)}")
    raise SystemExit(1)
print("🟢 boutons : tous les tests passent")
