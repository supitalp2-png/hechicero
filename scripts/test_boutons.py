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



# ── TICKET-119 — combinaison casque (GPIO25) + antenne (GPIO23) ────────────
# Temps SIMULÉ : la logique est isolée du GPIO dans EtatCombinaison, donc elle
# se vérifie sans matériel et sans attendre 3 secondes réelles. Une logique
# restée dans la boucle de polling n'aurait jamais été testée.
print()
c = bd.EtatCombinaison()

# Un seul bouton, même longtemps : rien ne se déclenche.
verifie("casque seul à t=0", c.evaluer(True, False, 0.0), "attente")
verifie("casque seul à t=10 s", c.evaluer(True, False, 10.0), "attente")

# Les deux boutons, mais relâchés avant 3 s : rien.
c = bd.EtatCombinaison()
verifie("les deux, début", c.evaluer(True, True, 100.0), "en_cours")
verifie("les deux, à 2,9 s : pas encore", c.evaluer(True, True, 102.9), "en_cours")
verifie("relâché avant 3 s : abandonné", c.evaluer(False, True, 102.95), "relachee")

# Les deux boutons tenus 3 s : déclenchement, UNE SEULE FOIS.
c = bd.EtatCombinaison()
c.evaluer(True, True, 200.0)
verifie("à 2,99 s : toujours rien", c.evaluer(True, True, 202.99), "en_cours")
verifie("à 3,00 s : déclenche", c.evaluer(True, True, 203.0), "declencher")
verifie("maintenu au-delà : ne se répète PAS", c.evaluer(True, True, 205.0), "en_cours")
verifie("maintenu 10 s : toujours pas de répétition", c.evaluer(True, True, 210.0), "en_cours")

# ⚠️ Après relâchement, la combinaison doit se réarmer — sinon elle ne
# fonctionnerait qu'une fois par démarrage du service.
verifie("relâchement", c.evaluer(False, False, 211.0), "relachee")
c.evaluer(True, True, 300.0)
verifie("deuxième usage : déclenche à nouveau", c.evaluer(True, True, 303.0), "declencher")

# Le seuil est bien 3 s, pas une valeur approchante.
verifie("seuil de maintien à 3 s", bd.COMBO_HOLD_S, 3.0)
verifie("les deux broches visées sont l'antenne et le casque",
        sorted(bd.COMBO_PINS), [23, 25])


print()
if echecs:
    print(f"⛔ {len(echecs)} test(s) en échec : {', '.join(echecs)}")
    raise SystemExit(1)
print("🟢 boutons : tous les tests passent")
