#!/usr/bin/env python3
"""recalibrer_table_batterie.py — reconstruire la table tension→pourcentage
depuis une décharge réellement mesurée (TICKET-136).

── POURQUOI ────────────────────────────────────────────────────────────────
`battery_common._LIPO_TABLE` est une courbe GÉNÉRIQUE d'accumulateur à poche,
héritée du montage d'origine. Les cellules actuelles sont des EVE INR21700/58E
(Li-ion NMC, 2 en parallèle, 11 200 mAh). La table n'a jamais été recalée sur
elles — tout le pourcentage affiché, partout dans le projet, en dépend.

Le cycle du 2026-08-18 fournit enfin la matière : une décharge complète avec
tension ET courant relevés toutes les 15 s.

── DEUX CORRECTIONS QUE LA TABLE ACTUELLE NE FAIT PAS ──────────────────────
1. **L'AFFAISSEMENT.** La tension mesurée dépend du courant tiré : à −2,2 A
   elle est bien plus basse qu'au repos. La table actuelle mélange les deux,
   donc le pourcentage affiché chute dès qu'on lance une lecture — alors que
   la charge stockée n'a pas bougé. On corrige avec V_oc = V + |I| × R, où R
   est la résistance interne mesurée sur un saut de charge réel.

2. **LA RÉPARTITION.** La table actuelle suppose une courbe. On la remplace
   par la répartition réelle de l'énergie : on intègre le courant dans le
   temps (comptage coulométrique) pour savoir combien de mAh ont été délivrés
   entre deux tensions, et on en déduit le pourcentage.

⚠️ LIMITE ASSUMÉE : la décharge s'arrête au seuil d'arrêt, pas à vide. Sous
ce point la courbe est extrapolée jusqu'à 3,0 V et signalée comme telle.

    python3 scripts/recalibrer_table_batterie.py
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

HISTORIQUE = Path("/home/thomas/hechicero/data/battery_history.json")
# En dessous de ce courant, on considère qu'il n'y a pas de charge utile :
# ces points ne servent pas à estimer la résistance interne.
COURANT_MINI_MA = 300
TENSION_VIDE = 3.00     # 0 % par convention du projet, extrapolé


def horodatage(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def main() -> int:
    with HISTORIQUE.open(encoding="utf-8") as fh:
        cycles = json.load(fh).get("cycles", [])

    # Le cycle de référence : la décharge la plus profonde disposant de la
    # tension. Les points antérieurs au 2026-08-17 ne l'ont pas.
    meilleur, profondeur = None, 0
    for c in cycles:
        pts = [p for p in c.get("datapoints", [])
               if not p.get("charging") and p.get("voltage_v") is not None]
        if len(pts) < 20:
            continue
        d = (c.get("level_start") or 0) - (c.get("level_end") or 0)
        if d > profondeur:
            meilleur, profondeur = pts, d

    if not meilleur:
        print("Aucune décharge exploitable avec tension. Refaire un cycle complet.")
        return 1

    print(f"Cycle retenu : {len(meilleur)} points, profondeur {profondeur} points de %")
    print(f"   de {meilleur[0]['t']} à {meilleur[-1]['t']}")
    print(f"   tension {meilleur[0]['voltage_v']} V -> {meilleur[-1]['voltage_v']} V\n")

    # ── 1. Résistance interne, depuis le plus grand saut de courant ────────
    # Entre deux relevés consécutifs proches dans le temps, une variation
    # brutale du courant à charge quasi identique donne R = ΔV / ΔI.
    meilleur_saut, R = 0.0, None
    for a, b in zip(meilleur, meilleur[1:]):
        ta, tb = horodatage(a["t"]), horodatage(b["t"])
        if not ta or not tb or (tb - ta).total_seconds() > 60:
            continue
        di = b["current_ma"] - a["current_ma"]
        dv = b["voltage_v"] - a["voltage_v"]
        if abs(di) > abs(meilleur_saut) and abs(di) > 500 and di != 0:
            # V = Voc + I*R  (I négatif en décharge) -> R = ΔV / ΔI
            r = dv / (di / 1000.0)
            if 0.005 < r < 0.5:        # garde-fou : R plausible pour 2x21700
                meilleur_saut, R = di, r

    if R is None:
        R = 0.05
        print(f"── Résistance interne : non mesurable sur ce cycle, valeur par défaut {R:.3f} Ω")
    else:
        print(f"── Résistance interne mesurée : {R*1000:.0f} mΩ")
        print(f"   (sur un saut de courant de {meilleur_saut:.0f} mA)")
    print(f"   À −2200 mA, l'affaissement vaut donc {2.2*R*1000:.0f} mV\n")

    # ── 2. Comptage coulométrique + tension à vide ─────────────────────────
    echantillons = []      # (mAh_cumules, V_oc)
    mah = 0.0
    for a, b in zip(meilleur, meilleur[1:]):
        ta, tb = horodatage(a["t"]), horodatage(b["t"])
        if not ta or not tb:
            continue
        h = (tb - ta).total_seconds() / 3600.0
        if h <= 0 or h > 0.5:          # trou : on ne peut rien intégrer
            continue
        i_moyen = (abs(a["current_ma"]) + abs(b["current_ma"])) / 2
        mah += i_moyen * h
        v_oc = b["voltage_v"] + abs(b["current_ma"]) / 1000.0 * R
        echantillons.append((mah, v_oc))

    if not echantillons:
        print("Intégration impossible (trous dans les relevés).")
        return 1

    total = echantillons[-1][0]
    print(f"── Énergie délivrée sur ce cycle : {total:.0f} mAh")
    print(f"   pour {profondeur} points de pourcentage annoncés par la table actuelle")
    print(f"   soit {total/max(1,profondeur):.0f} mAh par point — la table actuelle")
    print(f"   en suppose {11200/100:.0f}. Écart : {total/max(1,profondeur)/(11200/100)*100-100:+.0f} %\n")

    # ── 3. La table proposée ───────────────────────────────────────────────
    # Le pourcentage est la fraction d'énergie RESTANTE sur ce cycle.
    print("── Table proposée (à comparer à _LIPO_TABLE)")
    print("   Format : (tension_à_vide, pourcentage)\n")
    cibles = list(range(100, -1, -5))
    lignes = []
    for pct in cibles:
        vise = total * (100 - pct) / 100.0
        if vise > total:
            continue
        proche = min(echantillons, key=lambda e: abs(e[0] - vise))
        if abs(proche[0] - vise) > total * 0.06:
            continue                    # hors de la plage réellement mesurée
        lignes.append((round(proche[1], 3), pct))

    # Dédoublonnage : la tension doit être strictement décroissante.
    propre = []
    for v, p in lignes:
        if not propre or v < propre[-1][0]:
            propre.append((v, p))

    for v, p in propre:
        print(f"    ({v:.2f}, {p:3}),")
    if propre and propre[-1][1] > 0:
        print(f"    ({TENSION_VIDE:.2f},   0),   # extrapolé — la décharge s'arrête au seuil")

    print("\n── Comparaison avec la table actuelle, aux mêmes pourcentages")
    actuelle = {100: 4.20, 90: 4.11, 80: 4.02, 70: 3.95, 60: 3.87, 50: 3.79,
                40: 3.71, 30: 3.63, 20: 3.55, 10: 3.44, 5: 3.35, 0: 3.00}
    for v, p in propre:
        if p in actuelle:
            ecart = v - actuelle[p]
            signe = "table actuelle PESSIMISTE" if ecart < -0.005 else (
                    "table actuelle OPTIMISTE" if ecart > 0.005 else "identique")
            print(f"   {p:3} % : mesuré {v:.3f} V  vs  table {actuelle[p]:.2f} V"
                  f"   ({ecart:+.3f} V — {signe})")

    print("\n⚠️ Ne pas remplacer la table sans avoir lu l'écart ci-dessus.")
    print("   Un seul cycle ne suffit pas à figer une courbe : refaire tourner")
    print("   ce script après deux ou trois décharges et comparer les tables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
