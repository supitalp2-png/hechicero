#!/usr/bin/env python3
"""analyse_bande_morte.py — choisir `charge_deadband_ma` sur des mesures (TICKET-133).

── LA QUESTION ─────────────────────────────────────────────────────────────
En maintien de charge, le HAT consomme puis recharge par à-coups : le courant
oscille autour de zéro. Avec une bande morte trop étroite, la classification
bascule charge/décharge à chaque oscillation et fabrique des micro-cycles.
Thomas propose 200 mA au lieu de 10. Ce script vérifie.

── LA CONTREPARTIE, ET POURQUOI ON NE PEUT PAS SE CONTENTER D'ÉLARGIR ──────
Dans la bande morte, on CONSERVE l'état précédent. Si l'état précédent est
« charge » et qu'une décharge réelle s'installe sous le seuil, l'appareil se
croit en charge. Or `battery_watchdog` déclenche l'arrêt d'urgence sur
`not charging` : une bande trop large peut **empêcher l'arrêt de se produire**.

La bande doit donc tenir confortablement entre :
  · le HAUT des oscillations de maintien de charge  (sinon micro-cycles)
  · le BAS des courants de décharge réelle          (sinon arrêt jamais armé)

Si ces deux valeurs se chevauchent, aucun seuil ne convient et il faut une
autre approche (hystérésis temporelle, ou confirmation sur N relevés).

    python3 scripts/analyse_bande_morte.py
"""
from __future__ import annotations

import json
from pathlib import Path

HISTORIQUE = Path("/home/thomas/hechicero/data/battery_history.json")
# Au-dessus de ce niveau, on considère être en fin de charge / maintien : c'est
# là que le chargeur fait du sur-place et que les oscillations apparaissent.
NIVEAU_MAINTIEN = 80
CANDIDATS = [10, 25, 50, 100, 150, 200, 300, 500]


def centiles(valeurs: list[float], parts: list[int]) -> dict[int, float]:
    if not valeurs:
        return {}
    v = sorted(valeurs)
    return {p: v[min(len(v) - 1, int(len(v) * p / 100))] for p in parts}


def main() -> int:
    with HISTORIQUE.open(encoding="utf-8") as fh:
        cycles = json.load(fh).get("cycles", [])

    points = []
    for c in cycles:
        for p in c.get("datapoints", []):
            if isinstance(p.get("current_ma"), (int, float)):
                points.append(p)
    if not points:
        print("Aucun point avec current_ma.")
        return 1

    print(f"{len(points)} points de mesure exploitables\n")

    # ── 1. Maintien de charge : de quelle amplitude oscille-t-on ? ─────────
    # ⚠️ NE PAS filtrer sur `charging` — erreur commise le 2026-08-18 et
    # corrigée le jour même. Avec la règle du signe, un courant négatif est
    # classé « décharge » PAR CONSTRUCTION : le filtrer sur `charging == true`
    # revient à chercher des valeurs négatives dans un ensemble d'où on vient
    # de les retirer. Le script concluait « aucun courant négatif en maintien »
    # alors que le tableau de bord en montrait à −122 mA.
    # C'est le pire biais possible pour un outil d'analyse : il confirme
    # toujours ce que le code croit déjà. On sélectionne donc sur le NIVEAU
    # seul, qui est indépendant de la classification qu'on évalue.
    maintien = [p["current_ma"] for p in points
                if (p.get("level") or 0) >= NIVEAU_MAINTIEN]
    print(f"── Maintien de charge (niveau >= {NIVEAU_MAINTIEN} %, {len(maintien)} points)")
    if maintien:
        negatifs = [abs(c) for c in maintien if c < 0]
        faibles = [c for c in maintien if abs(c) < 500]
        print(f"   min {min(maintien):+.0f} mA   max {max(maintien):+.0f} mA")
        print(f"   points sous 500 mA en valeur absolue : {len(faibles)}")
        if negatifs:
            cn = centiles(negatifs, [50, 90, 95, 99])
            print(f"   creux NÉGATIFS ({len(negatifs)} points) — amplitude à couvrir :")
            for p, v in cn.items():
                print(f"      {p}e centile : {v:.0f} mA")
            print(f"      maximum     : {max(negatifs):.0f} mA")
        else:
            print("   aucun courant négatif en maintien : les oscillations ne")
            print("   traversent pas zéro, une bande étroite suffirait déjà.")
    else:
        print("   (pas encore de données — refaire tourner après un cycle complet)")

    # ── 2. Décharge réelle : quel est le courant le PLUS FAIBLE observé ? ──
    # C'est la borne haute absolue pour la bande morte : au-delà, on cesserait
    # de reconnaître une décharge authentique.
    decharge = [abs(p["current_ma"]) for p in points
                if not p.get("charging") and p["current_ma"] < 0]
    print(f"\n── Décharge réelle ({len(decharge)} points)")
    if decharge:
        cd = centiles(decharge, [1, 5, 10, 50])
        print(f"   minimum absolu : {min(decharge):.0f} mA   <-- BORNE HAUTE pour la bande")
        for p, v in cd.items():
            print(f"   {p}e centile : {v:.0f} mA")
    else:
        print("   (aucune décharge enregistrée)")

    # ── 3. Combien de bascules chaque candidat produirait-il ? ─────────────
    # On rejoue la règle sur la suite chronologique réelle et on compte les
    # changements d'état. Moins de bascules = moins de faux cycles.
    print("\n── Bascules charge/décharge simulées sur l'historique")
    print("   (moins il y en a, moins on fabrique de faux cycles)")
    suite = [p["current_ma"] for p in points]
    for bande in CANDIDATS:
        etat, bascules = None, 0
        for courant in suite:
            if courant > bande:
                nouvel = True
            elif courant < -bande:
                nouvel = False
            else:
                nouvel = etat if etat is not None else True
            if etat is not None and nouvel != etat:
                bascules += 1
            etat = nouvel
        sur = "" if (not decharge or bande < min(decharge)) else "  ⛔ DÉPASSE le plus faible courant de décharge"
        print(f"   ±{bande:4} mA : {bascules:4} bascule(s){sur}")

    # ── 4. Verdict ────────────────────────────────────────────────────────
    print("\n── Lecture")
    if decharge:
        borne = min(decharge)
        print(f"   Toute bande >= {borne:.0f} mA rendrait invisible la décharge la plus")
        print(f"   faible jamais mesurée — et le watchdog ne déclencherait plus.")
        print(f"   Garder une marge : viser au plus la moitié, soit {borne/2:.0f} mA.")
    if maintien:
        negatifs = [abs(c) for c in maintien if c < 0]
        if negatifs:
            print(f"   Il faut couvrir des creux allant jusqu'à {max(negatifs):.0f} mA en maintien.")
            if decharge and max(negatifs) >= min(decharge) / 2:
                print("   ⚠️ CHEVAUCHEMENT : les creux de maintien approchent les vraies")
                print("      décharges. Un simple seuil ne suffira pas — il faudrait")
                print("      confirmer la décharge sur plusieurs relevés consécutifs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
