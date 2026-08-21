#!/usr/bin/env python3
"""recalibrer_table_batterie.py — reconstruire la table tension→pourcentage
depuis des décharges réellement mesurées (TICKET-137, réécrit par TICKET-143).

── POURQUOI ────────────────────────────────────────────────────────────────
`battery_common._LIPO_TABLE` convertit une tension en pourcentage, et **tout
l'affichage du projet en dépend** : écran enfant, tableau de bord, seuils
d'alerte et d'arrêt. La table livrée le 2026-08-21 a été mesurée sur les
cellules réelles (EVE INR21700/58E, 2 en parallèle). Ce script sert à la
**réévaluer** quand de nouveaux cycles sont disponibles.

── CE QUE LA VERSION PRÉCÉDENTE FAISAIT DE FAUX (TICKET-143) ───────────────
Elle a proposé une table plaçant **85 points de pourcentage sur 80 mV** —
physiquement impossible. Cause : elle retenait le cycle le plus profond **sans
exiger qu'il soit CLOS**. Sur un cycle en cours, `level_end` est absent donc
vaut 0, la profondeur était calculée à 96 points au lieu de 30, et toute la
conversion mAh/point s'effondrait.

⚠️ **Elle n'a pas planté.** Elle a rendu un tableau bien formaté, plausible au
premier regard, assorti de son propre avertissement rassurant. **Un outil
d'analyse qui se trompe sans échouer est plus dangereux qu'un outil cassé** :
on lui fait confiance. Ce script refuse désormais de conclure quand il ne peut
pas — voir le verdict en fin d'exécution.

── LA LEÇON DE TICKET-142, INTÉGRÉE ICI ────────────────────────────────────
La version précédente ne rapportait l'accord entre cycles qu'en **millivolts**.
C'est ce qui a produit la régression du 2026-08-21 : « 6,4 mV de désaccord
médian » a été lu comme une réussite, alors que dans la zone plate (75-85 %)
**10 mV valent 10 POINTS de pourcentage**. Une métrique exprimée dans une autre
unité que le produit ne valide rien.

➡️ Ce script rapporte donc systématiquement les deux, et **c'est la valeur en
points qui décide** du verdict.

    python3 scripts/recalibrer_table_batterie.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from battery_common import _LIPO_TABLE, load_config  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]
HISTORIQUE = RACINE / "data" / "battery_history.json"

MIN_POINTS_CYCLE = 20      # sous ce nombre de relevés, un cycle ne décrit rien
MIN_MAH_CYCLE = 500        # sous cette énergie, ce n'est pas une vraie décharge
NIVEAUX = list(range(95, 4, -5))
# Au-delà de cet écart entre cycles, la courbe n'est pas reproductible et on
# refuse de proposer une table. 5 points, c'est déjà l'ordre de grandeur de
# l'erreur qu'on cherche à corriger.
DESACCORD_MAX_POINTS = 5.0


def horodatage(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(s) if s else None
    except Exception:
        return None


def cycles_exploitables(cycles: list[dict], v_plein: float,
                        r_ohm: float = 0.034) -> tuple[list[tuple[int, list[dict]]], list[str]]:
    """Décharges CLOSES, valides, fournies, et **parties d'une batterie pleine**.

    ⚠️ `discharge_end` est la condition qui manquait à la version d'origine
    (TICKET-143) : sur un cycle EN COURS, `level_end` est absent donc vaut 0, la
    profondeur était calculée à 96 points au lieu de 30, et la table proposée
    plaçait 85 points sur 80 mV.

    ⚠️ **Le départ à pleine charge est tout aussi indispensable, et c'est plus
    subtil.** Chaque cycle est normalisé sur SA PROPRE énergie délivrée. Le
    « 50 % restant » d'une décharge partie de 54 % ne désigne donc pas le même
    état que celui d'une décharge partie du plein : comparer les deux revient à
    comparer des grandeurs différentes portant le même nom. Sans ce filtre, le
    script rapportait 500 mV de désaccord là où deux cycles complets s'accordent
    à 6 mV.

    Le critère porte sur la TENSION de départ, pas sur le niveau enregistré :
    c'est justement le niveau qu'on cherche à recalibrer, s'y fier serait
    circulaire.
    """
    retenus, ecartes = [], []
    for i, c in enumerate(cycles):
        if not c.get("discharge_end") or c.get("invalid"):
            continue
        pts = [p for p in (c.get("datapoints") or [])
               if p.get("charging") is False
               and p.get("voltage_v") is not None
               and p.get("current_ma") is not None]
        if len(pts) < MIN_POINTS_CYCLE:
            continue
        pts.sort(key=lambda p: p["t"])
        depart = pts[0]["voltage_v"] + abs(pts[0]["current_ma"]) / 1000.0 * r_ohm
        if depart < v_plein:
            ecartes.append(f"cycle {i:2d} — départ à {depart:.3f} V (< {v_plein:.2f} V) : "
                           f"décharge partielle, non comparable")
            continue
        retenus.append((i, pts))
    return retenus, ecartes


def courbe(points: list[dict], r_ohm: float) -> tuple[list[tuple[float, float]], float]:
    """(tension_à_vide, mAh cumulés) le long de la décharge, et le total."""
    mah = 0.0
    serie: list[tuple[float, float]] = []
    for a, b in zip(points, points[1:]):
        ta, tb = horodatage(a["t"]), horodatage(b["t"])
        if not ta or not tb:
            continue
        h = (tb - ta).total_seconds() / 3600.0
        if h <= 0 or h > 0.5:            # trou : rien à intégrer
            continue
        mah += (abs(a["current_ma"]) + abs(b["current_ma"])) / 2 * h
        serie.append((a["voltage_v"] + abs(a["current_ma"]) / 1000.0 * r_ohm, mah))
    return serie, mah


def tension_au_niveau(serie: list[tuple[float, float]], capacite: float,
                      total: float, pct: int) -> float | None:
    """Tension à vide au niveau `pct`, rapporté à la CAPACITÉ DE LA BATTERIE.

    ⚠️ Surtout PAS à l'énergie délivrée par ce cycle-là. Tous les cycles retenus
    partent du plein, mais pas tous ne vont au bout : normaliser chacun sur son
    propre total ferait désigner par « 50 % restant » un état différent d'un
    cycle à l'autre. Un cycle qui n'a délivré que 2503 mAh serait comparé à un
    cycle de 8892 mAh comme si les deux décrivaient la même plage.

    C'est la même erreur de fond que TICKET-142 : donner le même nom à deux
    grandeurs qui n'en sont pas une. Elle produisait ici 500 mV de désaccord
    apparent entre des courbes qui, correctement rapportées, s'accordent à 6 mV.

    Renvoie `None` si le cycle n'est pas descendu jusqu'à ce niveau.
    """
    cible = capacite * (1 - pct / 100.0)
    if cible > total:
        return None                      # ce cycle ne va pas si bas
    for voc, m in serie:
        if m >= cible:
            return voc
    return None


def ajuster_resistance(jeux: list[list[dict]], capacite: float) -> tuple[float, float]:
    """R qui fait le mieux COÏNCIDER les courbes de plusieurs cycles.

    Bien plus robuste que l'ancienne méthode (un seul saut de courant, qui
    donnait des quartiles de 9 à 35 mΩ selon le saut retenu). Ici on exploite
    le fait que des cycles aux profils de courant différents ne se superposent
    qu'à la bonne valeur de R.

    ⚠️ Le minimum est souvent PLAT : si le courant de décharge varie peu d'un
    cycle à l'autre, R est faiblement contraint. Le script le dit.
    """
    if len(jeux) < 2:
        return 0.034, float("nan")
    meilleur_r, meilleur_ecart = 0.0, float("inf")
    for pas in range(0, 121, 2):
        r = pas / 1000.0
        courbes = [courbe(pts, r) for pts in jeux]
        ecarts = []
        for niveau in NIVEAUX:
            vs = [v for s, t in courbes if (v := tension_au_niveau(s, capacite, t, niveau)) is not None]
            if len(vs) >= 2:
                ecarts.append(max(vs) - min(vs))
        if not ecarts:
            continue
        ecarts.sort()
        median = ecarts[len(ecarts) // 2]
        if median < meilleur_ecart:
            meilleur_r, meilleur_ecart = r, median
    return meilleur_r, meilleur_ecart


def points_par_mv(table: list[tuple[float, int]], v: float) -> float:
    """Sensibilité locale : combien de points de % vaut 1 mV à cette tension.

    C'est cette conversion qui manquait à la version précédente, et c'est elle
    qui décide si un accord en millivolts vaut quelque chose.
    """
    for i in range(len(table) - 1):
        v_haut, p_haut = table[i]
        v_bas, p_bas = table[i + 1]
        if v_bas <= v <= v_haut and v_haut > v_bas:
            return (p_haut - p_bas) / ((v_haut - v_bas) * 1000.0)
    return 0.0


def main() -> int:
    if not HISTORIQUE.exists():
        print(f"Historique introuvable : {HISTORIQUE}")
        return 1
    cycles = json.loads(HISTORIQUE.read_text(encoding="utf-8")).get("cycles", [])
    config = load_config()
    v_plein = float(config.get("full_voltage_v", 4.10))
    retenus, ecartes = cycles_exploitables(cycles, v_plein)

    if ecartes:
        print("── Cycles écartés ──")
        for m in ecartes:
            print(f"   {m}")
        print()

    if len(retenus) < 2:
        print(f"Seulement {len(retenus)} décharge(s) complète(s) exploitable(s).")
        print("Il en faut au moins DEUX, parties d'une batterie pleine : une")
        print("courbe unique ne se vérifie pas, et une décharge partielle n'est")
        print("pas comparable à une décharge complète.")
        return 1

    jeux = []
    print("── Cycles retenus (décharges closes, valides) ──")
    for idx, pts in retenus:
        _, total = courbe(pts, 0.034)
        if total < MIN_MAH_CYCLE:
            print(f"   cycle {idx:2d} — écarté : {total:.0f} mAh seulement")
            continue
        jeux.append(pts)
        print(f"   cycle {idx:2d} — {len(pts):4d} pts, {total:5.0f} mAh, "
              f"{pts[0]['t'][:16]} → {pts[-1]['t'][:16]}")
    if len(jeux) < 2:
        print("\nPas assez de cycles fournis pour comparer. On s'arrête.")
        return 1

    capacite = float(config.get("battery_usable_mah", 0)) or max(
        courbe(pts, 0.034)[1] for pts in jeux)
    print(f"\n── Capacité de référence : {capacite:.0f} mAh")
    print("   (tous les niveaux sont rapportés À CETTE capacité, jamais à")
    print("    l'énergie propre de chaque cycle — voir tension_au_niveau)")

    r, ecart_mv = ajuster_resistance(jeux, capacite)
    print(f"\n── Résistance interne ajustée : {r*1000:.0f} mΩ")
    print(f"   (valeur qui fait le mieux coïncider les {len(jeux)} cycles)")
    print(f"   désaccord médian résiduel : {ecart_mv*1000:.1f} mV")
    print(f"   affaissement à −2200 mA : {r*2.2*1000:.0f} mV")

    courbes = [courbe(pts, r) for pts in jeux]
    capacites = [t for _, t in courbes]
    print(f"\n── Énergie délivrée : {' · '.join(f'{c:.0f}' for c in capacites)} mAh")
    print(f"   (les cycles peu profonds ne renseignent que le HAUT de la courbe)")

    # ── Le tableau qui décide : l'accord, en mV ET EN POINTS ────────────────
    print("\n── Accord entre cycles, dans les DEUX unités")
    print("   ⚠️ C'est la colonne « points » qui décide. Un accord de 6 mV est")
    print("      excellent à 50 % et sans aucune valeur à 80 % (TICKET-142).\n")
    print("   niveau   V_oc moyenne   écart mV   sensibilité   écart POINTS")
    pire_points, table_proposee, par_niveau = 0.0, [], {}
    for niveau in NIVEAUX:
        vs = [v for s, t in courbes if (v := tension_au_niveau(s, capacite, t, niveau)) is not None]
        if len(vs) < 2:
            continue
        moy = sum(vs) / len(vs)
        ecart = (max(vs) - min(vs)) * 1000.0
        sens = points_par_mv(_LIPO_TABLE, moy)
        en_points = ecart * sens
        pire_points = max(pire_points, en_points)
        par_niveau[niveau] = en_points
        drapeau = "  ← INEXPLOITABLE" if en_points > DESACCORD_MAX_POINTS else ""
        print(f"   {niveau:4d} %   {moy:8.3f} V   {ecart:7.1f}   "
              f"{sens:6.2f} pt/mV   {en_points:7.1f}{drapeau}")
        table_proposee.append((round(moy, 3), niveau))

    # Jusqu'où la tension est-elle exploitable ? On cherche le niveau le plus
    # HAUT à partir duquel toutes les bandes inférieures tiennent la limite.
    # Un refus global serait trompeur : le bas de la courbe est souvent
    # parfaitement reproductible alors que le plateau haut ne l'est jamais.
    plafond = None
    for niveau, ecart in sorted(par_niveau.items(), reverse=True):
        if ecart > DESACCORD_MAX_POINTS:
            plafond = niveau
        else:
            break

    print(f"\n── Verdict — pire désaccord : {pire_points:.1f} point(s) de pourcentage")
    # ⚠️ Refus TOTAL seulement si AUCUNE bande ne tient — pas si la plus haute
    # échoue. Le plateau du haut ne sera jamais reproductible : s'en servir pour
    # rejeter tout le reste reviendrait à jeter une courbe basse parfaitement
    # exploitable, qui est justement celle dont dépend la sécurité.
    if plafond is not None and plafond <= min(par_niveau):
        print("   ⛔ Aucune bande ne tient la limite — la courbe n'est pas")
        print("   reproductible du tout. Aucune table n'est proposée : la")
        print("   remplacer sur ces données rejouerait la régression TICKET-142.")
        return 2

    if plafond is not None:
        print(f"   ⚠️ La tension ne dit RIEN au-dessus de {plafond} % "
              f"(désaccord > {DESACCORD_MAX_POINTS:.0f} pts).")
        print("   ➡️ C'est le domaine du comptage coulométrique (TICKET-142), pas")
        print("      celui d'une table. Ne pas chercher à y gagner en précision")
        print("      en resserrant les paliers : on ne ferait qu'amplifier le bruit.")
        print(f"\n   ✅ Reproductible jusqu'à {plafond - 5} %. Table proposée pour cette")
        print("      plage (tensions À VIDE) :\n")
    else:
        print("   ✅ Reproductible sur toute la plage. Table proposée "
              "(tensions À VIDE) :\n")

    precedent = None
    corriges = []
    for v, p in table_proposee:
        if plafond is not None and p >= plafond:
            continue
        mesure = v
        if precedent is not None and v >= precedent:
            # ⚠️ La tension MONTE alors que la charge baisse : physiquement
            # impossible, donc bruit pur dans cette bande. On force la monotonie
            # (sans quoi `percent_from_voltage()` diviserait par zéro) mais on le
            # DIT. Réparer en silence donnerait à lire une table d'apparence
            # propre dont certains points sont fabriqués et non mesurés — c'est
            # précisément le travers que ce ticket corrige.
            v = round(precedent - 0.005, 3)
            corriges.append((p, mesure, v))
        precedent = v
        print(f"    ({v:.3f}, {p:3d}),")

    if corriges:
        print(f"\n   ⚠️ {len(corriges)} palier(s) NON MESURÉ(S) — valeurs forcées pour")
        print("      rétablir la monotonie, car la tension mesurée y REMONTE :")
        for p, mesure, force in corriges:
            print(f"        {p:3d} % : mesuré {mesure:.3f} V (incohérent) → forcé à {force:.3f} V")
        print("      Ces paliers ne décrivent aucune mesure. C'est le signe que la")
        print("      tension n'a plus de pouvoir de discrimination dans cette bande.")
    print("\n⚠️ Ces tensions sont des tensions À VIDE : elles ne valent QUE si")
    print("   `tension_a_vide()` est appliquée avant la conversion. Échanger la")
    print("   table sans la compensation rend le calcul PLUS FAUX qu'avant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
