#!/usr/bin/env python3
"""
test_kiosk_freeze.py — Tests de garde du guetteur de gel (TICKET-147).

Les deux seules alertes émises par le guetteur depuis sa mise en service étaient
fausses : elles suivaient une resynchronisation NTP de moins de 15 s. Le Pi
démarre sans réseau, son horloge bondit quand le NTP répond, et le dernier
battement — écrit avant le bond — paraît vieux d'exactement le saut.

Ces tests portent sur la DÉCISION (`DetecteurGel.evaluer`), pas sur le texte du
journal : on lui donne des séquences d'âges et de dérives d'horloge, et on
vérifie ce qu'il conclut. Ils tournent sans Pi, sans Chromium et sans panne.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiosk_freeze_watch import DetecteurGel   # noqa: E402

ok = 0
ko = 0


def verifie(nom: str, condition: bool, detail: str = "") -> None:
    global ok, ko
    if condition:
        ok += 1
    else:
        ko += 1
        print(f"  ❌ {nom}" + (f" — {detail}" if detail else ""))


def rejouer(sequence: list[tuple[float, float]], **kw) -> list[str]:
    """Déroule une suite de (âge du battement, dérive d'horloge) → verdicts."""
    d = DetecteurGel(**kw)
    return [d.evaluer(age, derive) for age, derive in sequence]


# ── 1. Le cas nominal : tout va bien ─────────────────────────────────────────
# Dérive constante (personne ne touche à l'heure), battements frais.
verdicts = rejouer([(5, 100.0), (12, 100.0), (8, 100.0), (15, 100.0)])
verifie("battements frais → aucune alerte", set(verdicts) == {"ok"}, str(verdicts))


# ── 2. Un vrai gel EST détecté ───────────────────────────────────────────────
# C'est la garde la plus importante : à force de filtrer le bruit, on peut
# rendre un détecteur incapable de détecter. Le silence grandit, l'horloge ne
# bouge pas.
verdicts = rejouer([(20, 100.0), (80, 100.0), (100, 100.0), (120, 100.0), (140, 100.0)])
verifie("vrai gel → alerte levée", "alerte" in verdicts, str(verdicts))
verifie("vrai gel → confirmation avant l'alerte",
        verdicts.index("suspect") < verdicts.index("alerte"), str(verdicts))
verifie("vrai gel → un seul instantané", verdicts.count("alerte") == 1, str(verdicts))


# ── 3. Les deux fausses alertes réelles, avec leurs chiffres ─────────────────
# 22/08 : saut NTP puis âge apparent de 77 s. 23/08 : saut puis 516 s.
# Dans les deux cas la page tournait — le battement est revenu 21 s plus tard.
for jour, age_apparent, saut in (("22/08", 77.0, 77.0), ("23/08", 516.0, 516.0)):
    verdicts = rejouer([
        (10, 100.0),                    # tout va bien
        (age_apparent, 100.0 + saut),   # NTP repositionne l'heure
        (5, 100.0 + saut),              # battement suivant, horloge stable
        (12, 100.0 + saut),
    ])
    verifie(f"{jour} : saut NTP reconnu comme tel", verdicts[1] == "saut_horloge", str(verdicts))
    verifie(f"{jour} : aucune alerte sur le saut", "alerte" not in verdicts, str(verdicts))

# Et l'horloge qui recule (correction en arrière) ne doit rien déclencher non plus.
verdicts = rejouer([(10, 100.0), (300, 100.0 - 300), (8, 100.0 - 300)])
verifie("saut d'horloge en arrière ignoré", "alerte" not in verdicts, str(verdicts))

# Battement daté dans le futur : impossible physiquement, jamais un gel.
verdicts = rejouer([(10, 100.0), (-45, 100.0), (-45, 100.0), (-45, 100.0)])
verifie("battement dans le futur ignoré", "alerte" not in verdicts, str(verdicts))


# ── 4. Un gel qui COMMENCE juste après un saut d'horloge ─────────────────────
# Le filtre ne doit pas devenir un angle mort permanent : une fois l'heure
# stabilisée, un silence qui persiste doit être vu.
verdicts = rejouer([
    (10, 100.0),
    (200, 400.0),   # saut d'horloge, ignoré
    (220, 400.0),   # horloge stable, silence réel
    (240, 400.0),
    (260, 400.0),
])
verifie("gel réel après un saut → alerte quand même", "alerte" in verdicts, str(verdicts))


# ── 5. Un hoquet d'un seul tour ne déclenche rien ────────────────────────────
verdicts = rejouer([(10, 100.0), (90, 100.0), (6, 100.0), (9, 100.0)])
verifie("silence d'un seul tour → pas d'alerte", "alerte" not in verdicts, str(verdicts))
verifie("silence d'un seul tour → marqué suspect", "suspect" in verdicts, str(verdicts))


# ── 6. Réarmement : le retour du battement, puis un second gel ───────────────
verdicts = rejouer([
    (10, 100.0),
    (80, 100.0), (100, 100.0),   # 1er gel → suspect puis alerte
    (5, 100.0),                  # retour
    (80, 100.0), (100, 100.0),   # 2e gel → doit ré-alerter
])
verifie("retour du battement signalé", "retour" in verdicts, str(verdicts))
verifie("second gel → nouvelle alerte", verdicts.count("alerte") == 2, str(verdicts))


# ── 7. La dérive minuscule du quartz ne compte pas pour un saut ──────────────
# L'horloge murale et l'horloge monotone divergent lentement (correction NTP en
# douceur, adjtime). Quelques dixièmes de seconde ne doivent rien déclencher.
verdicts = rejouer([(10, 100.0), (12, 100.3), (11, 100.6), (13, 100.9)])
verifie("dérive lente ≠ saut d'horloge", "saut_horloge" not in verdicts, str(verdicts))

print(f"\n{ok} test(s) OK, {ko} échec(s)")
sys.exit(1 if ko else 0)
