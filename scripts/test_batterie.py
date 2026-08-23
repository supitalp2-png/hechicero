#!/usr/bin/env python3
"""Tests de la détection charge/décharge et de la clôture de cycle — TICKET-133.

Pourquoi ces tests : les deux corrections touchent le calcul d'autonomie et,
pour la détection de charge, le booléen dont `battery_watchdog` se sert pour
décider d'éteindre le Pi. Ça ne se valide pas à l'œil.

Les cas ne sont pas inventés : ce sont les mesures réelles du 2026-08-17,
relevées dans `data/battery_history.json`.

Sans effet de bord : aucune lecture de fichier, aucun capteur, aucun réseau.
    python3 scripts/test_batterie.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from battery_common import (                        # noqa: E402
    _LIPO_TABLE,
    batterie_pleine,
    detecter_charge,
    mediane,
    niveau_coulometrique,
    percent_from_voltage,
    read_sensor_snapshot,
    tension_a_vide,
)
from battery_tracker import (                       # noqa: E402
    close_discharge,
    purge_history,
    should_record_point,
)

echecs: list[str] = []


def verifie(nom: str, obtenu, attendu) -> None:
    if obtenu == attendu:
        print(f"  ok   {nom}")
    else:
        print(f"  ÉCHEC {nom}\n       obtenu  : {obtenu}\n       attendu : {attendu}")
        echecs.append(nom)


BANDE = 10.0

# ── 1. Le signe décide ─────────────────────────────────────────────────────
verifie("courant franchement positif -> charge", detecter_charge(683.67, BANDE, False), True)
verifie("courant franchement négatif -> décharge", detecter_charge(-2038.35, BANDE, True), False)

# ── 2. LES CAS QUI CASSAIENT — courants positifs faibles, sur secteur ──────
# Mesures réelles du 2026-08-17, phase CV, cellule presque pleine. L'ancienne
# règle (seuil unique à 300 mA) les classait « décharge » alors que le courant
# ENTRE dans la batterie, fabriquant de faux cycles où le niveau montait.
verifie("+257,71 mA (mesuré) -> charge, pas décharge", detecter_charge(257.71, BANDE, True), True)
verifie("+17,83 mA (mesuré) -> charge, pas décharge", detecter_charge(17.83, BANDE, True), True)
verifie("+17,83 mA même en venant de décharge", detecter_charge(17.83, BANDE, False), True)

# ── 3. Bande morte : on garde l'état précédent ─────────────────────────────
verifie("+5 mA en venant de charge -> reste charge", detecter_charge(5.0, BANDE, True), True)
verifie("+5 mA en venant de décharge -> reste décharge", detecter_charge(5.0, BANDE, False), False)
verifie("-5 mA en venant de charge -> reste charge", detecter_charge(-5.0, BANDE, True), True)
verifie("-5 mA en venant de décharge -> reste décharge", detecter_charge(-5.0, BANDE, False), False)
verifie("0 mA en venant de décharge -> reste décharge", detecter_charge(0.0, BANDE, False), False)

# ── 4. Amorçage : sans état précédent, on ne coupe pas le courant ──────────
# `battery_watchdog` éteint le Pi sur `not charging`. Dans le doute (courant
# quasi nul, aucun historique), répondre « charge » évite un arrêt injustifié
# alors que la batterie ne se vide pratiquement pas.
verifie("bande morte sans précédent -> charge (sûr pour le watchdog)", detecter_charge(0.0, BANDE, None), True)
verifie("hors bande sans précédent : le signe tranche", detecter_charge(-500.0, BANDE, None), False)

# ── 5. Bornes exactes de la bande ─────────────────────────────────────────
verifie("+10 mA pile = dans la bande", detecter_charge(10.0, BANDE, False), False)
verifie("+10,1 mA = charge", detecter_charge(10.1, BANDE, False), True)


# ── 5bis. La bande réellement configurée : 200 mA (TICKET-133, 2026-08-18) ─
# Mesures du tableau de bord : en maintien de charge le courant oscille entre
# environ +1000 mA et **−122 mA** — il TRAVERSE zéro. Avec une bande de 10 mA,
# chaque creux basculait en « décharge » et fabriquait un micro-cycle.
# La bande à 200 mA les absorbe.
#
# ⚠️ Et elle reste très en dessous de toute décharge réelle : le Pi seul
# consomme de l'ordre de 600 à 800 mA, et en lecture on mesure 1600 à 3400 mA.
# La marge est d'un facteur 3 au minimum — le watchdog voit donc toujours une
# vraie décharge.
BANDE_REELLE = 200.0
verifie("creux de maintien −122 mA -> reste charge", detecter_charge(-121.92, BANDE_REELLE, True), True)
verifie("pointe de maintien +1000 mA -> charge", detecter_charge(1000.0, BANDE_REELLE, True), True)
verifie("décharge en lecture −1622 mA -> décharge", detecter_charge(-1622.45, BANDE_REELLE, True), False)
verifie("décharge en veille −800 mA -> décharge", detecter_charge(-800.0, BANDE_REELLE, True), False)
verifie("−200 mA pile = dans la bande", detecter_charge(-200.0, BANDE_REELLE, True), True)
verifie("−200,1 mA = décharge", detecter_charge(-200.1, BANDE_REELLE, True), False)


# ── 6. Clôture de cycle interrompue par l'arrêt d'urgence ─────────────────
# Le cas réel du 2026-08-17 : décharge 85 % -> 15 %, arrêt du Pi à 20:07, puis
# rebranchement à 20:12 où la tension remonte à 28 %. L'ancienne version
# retenait 28 % comme point bas et comptait les minutes hors tension.
cycle = {
    "discharge_start": "2026-08-17T16:40:03",
    "level_start": 85,
    "datapoints": [
        {"t": "2026-08-17T16:40:03", "level": 85, "charging": False, "mpd_mode": "webradio"},
        {"t": "2026-08-17T18:30:00", "level": 50, "charging": False, "mpd_mode": "webradio"},
        {"t": "2026-08-17T20:06:07", "level": 15, "charging": False, "mpd_mode": "webradio"},
        {"t": "2026-08-17T20:07:07", "level": 17, "charging": False, "mpd_mode": "webradio"},
    ],
}
bascule = {"timestamp": "2026-08-17T20:12:22", "level": 28}
# gap_minutes est calculé par l'appelant à partir de stats["last_updated"], et
# NON de l'écart entre datapoints : `should_record_point()` n'enregistre un
# point que sur transition ou variation de niveau, donc une décharge stable
# laisse de longs trous parfaitement normaux. `battery_stats.json` est en
# revanche réécrit toutes les 60 s quoi qu'il arrive.
close_discharge(cycle, bascule, gap_minutes=5)

verifie("point bas = minimum observé (15), pas le niveau au rebranchement (28)", cycle["level_end"], 15)
verifie("fin de décharge = dernier relevé, pas la bascule", cycle["discharge_end"], "2026-08-17T20:07:07")
verifie("durée = 207 min, sans le temps hors tension", cycle["duration_minutes"], 207)
# 5 min de trou réel le 2026-08-17 : un seuil à 10 min l'aurait laissé passer.
verifie("trou hors tension signalé", cycle.get("gap_minutes"), 5)
verifie("cycle profond NON invalidé", cycle.get("invalid"), None)

# ── 7. Un cycle normal, sans trou, garde son comportement ─────────────────
cycle_normal = {
    "discharge_start": "2026-08-17T10:00:00",
    "level_start": 90,
    "datapoints": [
        {"t": "2026-08-17T10:00:00", "level": 90, "charging": False, "mpd_mode": "podcast"},
        {"t": "2026-08-17T11:00:00", "level": 70, "charging": False, "mpd_mode": "podcast"},
    ],
}
close_discharge(cycle_normal, {"timestamp": "2026-08-17T11:00:30", "level": 70}, gap_minutes=1)
verifie("cycle sans trou : point bas correct", cycle_normal["level_end"], 70)
verifie("cycle sans trou : aucun gap signalé", cycle_normal.get("gap_minutes"), None)
verifie("cycle sans trou : durée 60 min", cycle_normal["duration_minutes"], 60)

# Cas piège : décharge stable, aucun point retenu pendant 20 min (le niveau ne
# bougeait pas assez), puis rebranchement. Le tracker tournait sans interruption
# — donc AUCUN trou à signaler, même si les datapoints sont très espacés.
stable = {
    "discharge_start": "2026-08-17T12:00:00",
    "level_start": 60,
    "datapoints": [
        {"t": "2026-08-17T12:00:00", "level": 60, "charging": False, "mpd_mode": "idle"},
        {"t": "2026-08-17T12:20:00", "level": 55, "charging": False, "mpd_mode": "idle"},
    ],
}
close_discharge(stable, {"timestamp": "2026-08-17T12:40:00", "level": 55}, gap_minutes=1)
verifie("datapoints espacés mais tracker vivant : aucun gap", stable.get("gap_minutes"), None)

# ── 8. Micro-cycle CV : toujours invalidé ─────────────────────────────────
# 84 % -> 86 % en 22 min, le niveau MONTE : ce n'est pas une décharge.
micro = {
    "discharge_start": "2026-08-17T15:25:02",
    "level_start": 84,
    "datapoints": [
        {"t": "2026-08-17T15:25:02", "level": 84, "charging": False, "mpd_mode": "idle"},
        {"t": "2026-08-17T15:26:02", "level": 82, "charging": False, "mpd_mode": "idle"},
    ],
}
close_discharge(micro, {"timestamp": "2026-08-17T15:47:03", "level": 86}, gap_minutes=1)
verifie("micro-cycle CV toujours invalidé", micro.get("invalid"), True)


# ── 9. TICKET-141 — l'enregistreur ne doit plus être aveugle aux plateaux ──
# Ces cas sont tirés de la panne réelle : dans la nuit du 2026-08-18, le courant
# s'est effondré de +1111 à -60 mA pendant 6 h 53 et l'enregistreur n'a produit
# que 3 points. Chacun des tests ci-dessous ÉCHOUE sur le code d'avant le
# correctif — c'est ce qui en fait des tests de garde et pas de la décoration.

def point(t, level, charging, current_ma, mpd_mode="idle"):
    return {"t": t, "level": level, "charging": charging,
            "current_ma": current_ma, "mpd_mode": mpd_mode}


def echantillon(t, level, charging, current_ma, mpd_mode="idle", status=None):
    return {"timestamp": t, "level": level, "charging": charging,
            "current_ma": current_ma, "mpd_mode": mpd_mode,
            "status": status or ("charging" if charging else "discharging")}


STATS_CHARGE = {"status": "charging"}

# 9a. Plateau : rien ne bouge, mais 5 minutes ont passé -> on enregistre.
#     Avant le correctif : aucun critère déclenché, donc AUCUN point.
plateau_avant = point("2026-08-19T12:00:00", 92, True, 800.0)
verifie(
    "plateau de 5 min sans changement -> point enregistré",
    should_record_point(STATS_CHARGE, echantillon("2026-08-19T12:05:00", 92, True, 800.0), plateau_avant)[0],
    True,
)
verifie(
    "plateau de 4 min -> pas encore de point",
    should_record_point(STATS_CHARGE, echantillon("2026-08-19T12:04:00", 92, True, 800.0), plateau_avant)[0],
    False,
)

# 9b. LE CAS DE LA NUIT DU 18 : le courant s'effondre, le niveau ne bouge pas.
#     Avant le correctif, le courant n'était pas un critère du tout.
verifie(
    "effondrement du courant à niveau constant -> point enregistré",
    should_record_point(STATS_CHARGE, echantillon("2026-08-19T12:01:00", 92, True, -60.0), plateau_avant)[0],
    True,
)

# 9c. Le courant cesse de couler sans variation de 300 mA : bande morte franchie.
faible = point("2026-08-19T12:00:00", 92, True, 120.0)
verifie(
    "le courant cesse de couler (120 -> 10 mA) -> point enregistré",
    should_record_point(STATS_CHARGE, echantillon("2026-08-19T12:01:00", 92, True, 10.0), faible)[0],
    True,
)

# 9d. ⚠️ ZONE Z8 — LE TEST QUI PROTÈGE LES CYCLES.
#     La cadence plancher et le courant ne doivent JAMAIS marquer une
#     transition : sinon close_discharge()/new_cycle() fabriquent un faux cycle
#     à chaque plateau, et le compteur de cycles devient inexploitable.
verifie(
    "cadence plancher ne déclenche PAS de transition de cycle",
    should_record_point(STATS_CHARGE, echantillon("2026-08-19T12:05:00", 92, True, 800.0), plateau_avant)[1],
    False,
)
verifie(
    "effondrement du courant ne déclenche PAS de transition de cycle",
    should_record_point(STATS_CHARGE, echantillon("2026-08-19T12:01:00", 92, True, -60.0), plateau_avant)[1],
    False,
)
verifie(
    "une vraie bascule charge->décharge déclenche bien la transition",
    should_record_point(STATS_CHARGE, echantillon("2026-08-19T12:01:00", 92, False, -400.0), plateau_avant)[1],
    True,
)

# 9e. Un plateau de 30 min doit produire au moins 6 points (1 toutes les 5 min).
#     C'est la formulation directe du défaut signalé par Thomas : « on voit
#     encore une sorte de trou dans la charge ».
retenus = 0
dernier = point("2026-08-19T12:00:00", 92, True, 800.0)
for minute in range(1, 31):
    ech = echantillon(f"2026-08-19T12:{minute:02d}:00", 92, True, 800.0)
    garde, _ = should_record_point(STATS_CHARGE, ech, dernier)
    if garde:
        retenus += 1
        dernier = point(ech["timestamp"], 92, True, 800.0)
verifie("plateau de 30 min -> au moins 6 points", retenus >= 6, True)

# ── 10. TICKET-141 — purge : décimer le vieux, préserver le récent ─────────
maintenant = datetime(2026, 8, 19, 12, 0, 0)


def serie(depart: datetime, nombre: int, pas_minutes: int, charging=True):
    return [
        {"t": (depart + timedelta(minutes=i * pas_minutes)).isoformat(),
         "level": 90, "charging": charging, "current_ma": 800.0, "mpd_mode": "idle"}
        for i in range(nombre)
    ]


# 60 jours : 24 points espacés de 5 min -> doivent être décimés à ~1/h.
vieux = {"datapoints": serie(maintenant - timedelta(days=60), 24, 5)}
hist_vieux = {"cycles": [vieux]}
supprimes = purge_history(hist_vieux, maintenant=maintenant)
verifie("purge : points de plus de 30 j décimés", supprimes > 0, True)
verifie("purge : au moins un point ancien conservé", len(vieux["datapoints"]) >= 1, True)

# 10 jours : ne doit RIEN perdre. La fenêtre de diagnostic est intouchable.
recent = {"datapoints": serie(maintenant - timedelta(days=10), 24, 5)}
hist_recent = {"cycles": [recent]}
avant_purge = len(recent["datapoints"])
verifie("purge : rien touché dans les 30 derniers jours",
        purge_history(hist_recent, maintenant=maintenant), 0)
verifie("purge : tous les points récents conservés", len(recent["datapoints"]), avant_purge)

# Une transition ancienne doit SURVIVRE à la décimation : c'est elle qui date
# l'événement. Décimer aveuglément effacerait ce qu'on cherche à retrouver.
avec_bascule = {"datapoints": serie(maintenant - timedelta(days=60), 6, 5)
                + [{"t": (maintenant - timedelta(days=60) + timedelta(minutes=30)).isoformat(),
                    "level": 90, "charging": False, "current_ma": -400.0, "mpd_mode": "idle"}]
                + serie(maintenant - timedelta(days=60) + timedelta(minutes=35), 6, 5, charging=False)}
hist_bascule = {"cycles": [avec_bascule]}
purge_history(hist_bascule, maintenant=maintenant)
verifie("purge : la transition ancienne est préservée",
        any(p["charging"] is False and p["current_ma"] == -400.0 for p in avec_bascule["datapoints"]),
        True)

# Idempotence : repurger un historique déjà purgé ne doit plus rien supprimer,
# sinon le fichier serait réécrit à chaque tour de boucle — exactement l'usure
# de carte SD qu'on cherche à éviter.
verifie("purge idempotente : deuxième passage sans effet",
        purge_history(hist_vieux, maintenant=maintenant), 0)


# ── 11. TICKET-139 — la médiane, et pourquoi ce n'est pas la moyenne ───────
verifie("médiane, nombre impair d'échantillons", mediane([3.0, 1.0, 2.0]), 2.0)
verifie("médiane, nombre pair", mediane([1.0, 2.0, 3.0, 4.0]), 2.5)
# LE cas réel : une charge à ~900 mA avec un creux isolé à -210 mA. C'est ce
# creux qui faisait annoncer « charge arrêtée » le 2026-08-19.
rafale = [900.0, 880.0, -210.0, 910.0, 890.0]
verifie("creux isolé de -210 mA écarté par la médiane", mediane(rafale), 890.0)
verifie("la moyenne, elle, aurait été tirée vers le bas", round(sum(rafale) / len(rafale)), 674)

# ── 12. TICKET-137 — compensation d'affaissement ──────────────────────────
R = 0.034
# En DÉCHARGE le courant est négatif : la cellule est plus pleine qu'elle n'en
# a l'air. C'est le cas qui faisait plonger la jauge quand un podcast démarrait.
verifie("décharge -2200 mA : +75 mV de correction",
        round(tension_a_vide(3.328, -2200.0, R) - 3.328, 3), 0.075)
# En CHARGE le courant est positif : la cellule est moins pleine qu'elle n'en a
# l'air. Se tromper de signe doublerait l'erreur au lieu de l'annuler.
verifie("charge +1100 mA : -37 mV de correction",
        round(tension_a_vide(3.952, 1100.0, R) - 3.952, 3), -0.037)
verifie("courant nul : aucune correction", tension_a_vide(3.800, 0.0, R), 3.800)
verifie("résistance nulle : fonction neutre", tension_a_vide(3.800, -2200.0, 0.0), 3.800)

# ── 13. TICKET-137 — la table mesurée ─────────────────────────────────────
# Monotonie stricte : percent_from_voltage() interpole entre paliers successifs
# et diviserait par zéro sur deux tensions égales.
verifie("table strictement décroissante en tension",
        all(_LIPO_TABLE[i][0] > _LIPO_TABLE[i + 1][0] for i in range(len(_LIPO_TABLE) - 1)),
        True)
verifie("table strictement décroissante en pourcentage",
        all(_LIPO_TABLE[i][1] > _LIPO_TABLE[i + 1][1] for i in range(len(_LIPO_TABLE) - 1)),
        True)
# Aucun palier plus fin que le bruit résiduel après lissage (5 mV).
# ⚠️ Celui-ci n'est PAS un test de régression : l'ancienne table le passait
# aussi. C'est un invariant de structure, qui protège d'une FUTURE table
# régénérée trop finement dans la zone plate — pas du bug de 2026-08-21.
verifie("aucun palier sous 5 mV",
        min(round(_LIPO_TABLE[i][0] - _LIPO_TABLE[i + 1][0], 4)
            for i in range(len(_LIPO_TABLE) - 1)) >= 0.005,
        True)

# Le cycle du 2026-08-18 s'est arrêté à 3,328 V sous -2194 mA. Avec la
# compensation, la table doit y voir un niveau quasi nul — c'était bien la fin
# de la décharge. L'ancienne table y annonçait encore 4 %.
v_coupure = tension_a_vide(3.328, -2194.0, R)
verifie("à la coupure réelle du 18/08, le niveau est quasi nul",
        percent_from_voltage(v_coupure) <= 2, True)

# Le seuil de 5 % doit tomber sur la tension mesurée, pas sur celle de la vieille
# courbe générique. C'est ce déplacement de 108 mV qui rend la coupure plus
# prudente — décision de Thomas du 2026-08-21.
verifie("seuil 5 % à la tension mesurée", percent_from_voltage(3.458), 5)
verifie("pleine charge reconnue", percent_from_voltage(4.146), 100)
verifie("au-dessus du plein, on plafonne à 100", percent_from_voltage(4.30), 100)
verifie("sous le plancher, on tombe à 0", percent_from_voltage(3.10), 0)

# ⚠️ Le piège que ce test surveille : appliquer la table à une tension BRUTE.
# Elle donne des tensions À VIDE ; sans compensation, un podcast en cours ferait
# perdre ~8 points instantanément alors que rien n'a été consommé.
brut = 3.763 - 2.2 * R          # 40 % réels, vus sous -2,2 A
verifie("sans compensation, la jauge perd des points à tort",
        percent_from_voltage(brut) < 35, True)
verifie("avec compensation, elle retombe sur 40 %",
        percent_from_voltage(tension_a_vide(brut, -2200.0, R)), 40)


# ── 14. TICKET-142 — comptage coulométrique ancré ─────────────────────────
# Le 2026-08-21, la table mesurée annonçait 86 % là où l'intégration du courant
# depuis la charge pleine donnait 77 %. Dans la bande 75-85 %, 10 mV valent
# 10 points : aucune table de tension ne peut y répondre.
CFG = {"coulomb_anchor_percent": 70, "battery_usable_mah": 8894}

# Sous le seuil : la table fait autorité, et l'ancrage est abandonné.
verifie("sous 70 %, la table décide",
        niveau_coulometrique(None, 45, -1600.0, 60.0, CFG), (45, None))
verifie("sous 70 %, aucun ancrage conservé",
        niveau_coulometrique({"mah": 4000.0}, 45, -1600.0, 60.0, CFG)[1], None)

# Au-dessus, sans ancrage : on part du niveau de la table et on s'ancre.
niveau, etat = niveau_coulometrique(None, 85, -1600.0, 60.0, CFG)
verifie("au-dessus de 70 % sans ancrage : on part de la table", niveau, 85)
verifie("... et on mémorise l'ancrage", round(etat["mah"]), round(0.85 * 8894))

# ⚠️ L'intégration se teste en pas de 60 s, comme elle tourne réellement. Un pas
# d'une heure serait REJETÉ par le garde-fou de trou — et c'est voulu : ces
# quatre tests ont d'abord échoué pour cette raison, ce qui a confirmé que le
# garde-fou mord.
def integre(mah_depart: float, courant_ma: float, minutes: int, niveau_table: int):
    etat = {"mah": mah_depart}
    niveau = niveau_table
    for _ in range(minutes):
        niveau, etat = niveau_coulometrique(etat, niveau_table, courant_ma, 60.0, CFG)
        if etat is None:
            break
    return niveau, etat


# Décharge : 1 h à -889,4 mA = -889,4 mAh = -10 points de 8894.
niveau, _ = integre(0.90 * 8894, -889.4, 60, 99)
verifie("décharge d'1 h à -889 mA : -10 points", niveau, 80)
verifie("la table à 99 % est ignorée au profit du comptage", niveau != 99, True)

# Charge : le niveau doit MONTER, et la table à 75 % ne doit pas le retenir.
niveau, _ = integre(0.75 * 8894, +889.4, 60, 75)
verifie("charge d'1 h à +889 mA : +10 points", niveau, 85)

# Saturation : on ne dépasse jamais 100 %, même en surchargeant l'intégrale.
niveau, _ = integre(0.98 * 8894, +5000.0, 60, 99)
verifie("le comptage sature à 100 %", niveau, 100)

# ⚠️ LE GARDE-FOU CENTRAL : un trou de mesure rend l'intégration aveugle sur
# l'intervalle manquant. Sans cette invalidation, la dérive deviendrait
# silencieuse — le pire défaut possible pour un compteur.
etat = {"mah": 0.90 * 8894}
niveau, _ = niveau_coulometrique(etat, 82, -1600.0, 3600.0 * 3, CFG)
verifie("trou de 3 h : on abandonne l'ancrage et on reprend la table", niveau, 82)
niveau, _ = niveau_coulometrique(etat, 82, -1600.0, 599.0, CFG)
verifie("trou de 599 s : encore acceptable, on intègre", niveau != 82, True)

# Retour sous le seuil par le comptage : la table reprend la main ET l'ancrage
# disparaît, sinon la dérive accumulée survivrait au recalage.
etat = {"mah": 0.71 * 8894}
niveau, etat2 = niveau_coulometrique(etat, 68, -1600.0, 3600.0, CFG)
verifie("en repassant sous 70 %, la table reprend", niveau, 68)
verifie("... et l'ancrage est effacé (pas de dérive qui survit)", etat2, None)

# Capacité absente : le mécanisme se neutralise au lieu de diviser par zéro.
verifie("sans capacité configurée, retour à la table",
        niveau_coulometrique({"mah": 100.0}, 88, -1600.0, 60.0, {"coulomb_anchor_percent": 70}),
        (88, None))

# ── 15. TICKET-142 — ancrage sur batterie pleine ──────────────────────────
# Sans ce repère, un démarrage à froid en zone plate amorce le comptage sur la
# valeur FAUSSE de la table et la conserve jusqu'au prochain passage sous 70 %.
CFGP = dict(CFG, full_voltage_v=4.10, full_current_ma=150.0)

# Mesures réelles de fin de charge du 2026-08-21 : 4,156-4,168 V, courant résiduel.
verifie("4,164 V et -18 mA : batterie pleine", batterie_pleine(4.164, -18.0, CFGP), True)
verifie("4,160 V et +25 mA : batterie pleine", batterie_pleine(4.160, 24.8, CFGP), True)

# ⚠️ LE PIÈGE À NE PAS RÉINTRODUIRE — les arrêts de charge anormaux du
# TICKET-140 ont un courant quasi nul (0,91 mA constant pendant des heures)
# mais une tension basse. Les prendre pour une batterie pleine afficherait
# 100 % avec un tiers de l'énergie.
verifie("arrêt anormal à 70 % (3,948 V, 0,91 mA) : PAS pleine",
        batterie_pleine(3.948, 0.91, CFGP), False)
verifie("arrêt anormal à 54 % (3,820 V, -60 mA) : PAS pleine",
        batterie_pleine(3.820, -60.05, CFGP), False)

# Charge en cours à fort courant : pas encore pleine, même à haute tension.
verifie("charge à +1100 mA : pas pleine malgré 4,12 V",
        batterie_pleine(4.12, 1100.0, CFGP), False)
# Décharge franche : jamais pleine.
verifie("décharge à -2200 mA : pas pleine", batterie_pleine(4.12, -2200.0, CFGP), False)

# L'ancrage sur batterie pleine l'emporte sur un état hérité faux.
niveau, etat = niveau_coulometrique({"mah": 0.60 * 8894}, 85, -18.0, 60.0, CFGP, voc_v=4.164)
verifie("batterie pleine : le comptage est recalé à 100 %", niveau, 100)
verifie("... et l'ancrage vaut la capacité entière", round(etat["mah"]), 8894)

# Sans tension fournie, le mécanisme garde son comportement d'avant.
verifie("sans voc_v, aucun ancrage sur batterie pleine",
        niveau_coulometrique({"mah": 0.60 * 8894}, 85, -18.0, 60.0, CFGP)[0] != 100, True)


# ── 16. LA CHAÎNE COMPLÈTE — vérifier le comportement, pas la forme du code ─
# ⚠️ Ce test remplace un garde du smoke test qui cherchait la chaîne littérale
# `percent_from_voltage(tension_a_vide(`. Le refactor de TICKET-142 a scindé
# cette expression en deux lignes : le garde a crié à la régression alors que
# rien n'était cassé. **Un test qui vérifie une FORME DE CODE casse au premier
# remaniement légitime, et fait douter de toute la suite.** On vérifie donc ce
# que la fonction RÉPOND, pas comment elle est écrite.
class CapteurFictif:
    """Capteur immobile. `getCurrent_mA()` est inversé par read_sensor_snapshot."""
    def __init__(self, volts, amperes_ma):
        self._v, self._i = volts, amperes_ma
    def getBusVoltage_V(self):
        return self._v
    def getCurrent_mA(self):
        return -self._i          # read_sensor_snapshot renverse le signe
    def getPower_W(self):
        return abs(self._v * self._i / 1000.0)


CFG_CHAINE = {
    "sensor_burst_samples": 3, "sensor_burst_interval_s": 0.0,
    "internal_resistance_ohm": 0.034, "charge_deadband_ma": 200,
    "coulomb_anchor_percent": 70, "battery_usable_mah": 8894,
    "full_voltage_v": 4.10, "full_current_ma": 150.0,
}

# 3,763 V mesurés sous −2,2 A. Sans compensation la table lit ~31 % ; avec, 40 %.
snap = read_sensor_snapshot(CapteurFictif(3.763 - 2.2 * 0.034, -2200.0), CFG_CHAINE)
verifie("chaîne complète : la compensation est bien appliquée à la lecture",
        snap["level_table"], 40)
verifie("chaîne complète : le brut aurait donné moins",
        percent_from_voltage(3.763 - 2.2 * 0.034) < 40, True)
verifie("chaîne complète : décharge détectée", snap["charging"], False)

# Rafale : la médiane doit être exposée, et le niveau rester cohérent.
verifie("chaîne complète : tension renvoyée arrondie au mV",
        snap["voltage_v"], round(3.763 - 2.2 * 0.034, 3))

# Batterie pleine vue de bout en bout : l'ancrage doit se former à 100 %.
plein = read_sensor_snapshot(CapteurFictif(4.16, -18.0), CFG_CHAINE, elapsed_s=60.0)
verifie("chaîne complète : batterie pleine ancrée à 100 %", plein["level"], 100)
verifie("chaîne complète : ancrage renvoyé au tracker",
        round(plein["coulomb_state"]["mah"]), 8894)


# ── §17 — TICKET-140 : de quoi diagnostiquer un arrêt de charge nocturne ─────
# Trois occurrences, cause inconnue, et les données enregistrées ne permettent
# de trancher aucune des pistes : on ne sait dire ni s'il faisait froid (fenêtre
# JEITA du chargeur) ni si l'alimentation avait décroché (sous-tension). Les
# deux mesures doivent donc VOYAGER JUSQU'AU POINT ENREGISTRÉ — c'est là qu'on
# les relira, pas dans le journal, qui aura défilé.
import battery_tracker as _bt   # noqa: E402

_cycle: dict = {}
_bt.append_datapoint(_cycle, {
    "timestamp": "2026-08-23T03:00:00", "level": 61, "charging": False,
    "mpd_mode": "idle", "screen_on": False, "current_ma": -60.0, "voltage_v": 3.820,
    "temperature_c": 31.4, "throttled": "0x50005",
})
_point = _cycle["datapoints"][0]
verifie("140 : température enregistrée dans le point", _point.get("temperature_c"), 31.4)
verifie("140 : registre throttled enregistré", _point.get("throttled"), "0x50005")

# Et le relevé ne doit JAMAIS tomber parce qu'une mesure est indisponible : le
# suivi de batterie porte l'arrêt propre avant décharge profonde. Une sonde qui
# manque vaut infiniment mieux qu'un tracker mort.
_cycle2: dict = {}
_bt.append_datapoint(_cycle2, {
    "timestamp": "2026-08-23T03:05:00", "level": 61, "charging": False,
    "mpd_mode": "idle", "screen_on": False, "current_ma": -60.0, "voltage_v": 3.820,
})
verifie("140 : mesure absente → clé présente à None",
        _cycle2["datapoints"][0].get("temperature_c", "CLÉ ABSENTE"), None)

# Les deux lecteurs ne lèvent jamais, même hors Pi (aucun thermal_zone, aucun
# vcgencmd) : ils renvoient None. C'est ce qui rend ce test exécutable partout.
try:
    _t = _bt.lire_temperature_c()
    _g = _bt.lire_throttled()
    verifie("140 : lecture température sans exception",
            _t is None or isinstance(_t, float), True)
    verifie("140 : lecture throttled sans exception",
            _g is None or isinstance(_g, str), True)
except Exception as _e:  # noqa: BLE001
    verifie("140 : les sondes ne lèvent jamais", f"exception {_e!r}", "aucune exception")


print()
if echecs:
    print(f"⛔ {len(echecs)} test(s) en échec : {', '.join(echecs)}")
    raise SystemExit(1)
print("🟢 batterie : tous les tests passent")
