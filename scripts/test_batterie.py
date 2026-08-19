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

from battery_common import detecter_charge          # noqa: E402
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


print()
if echecs:
    print(f"⛔ {len(echecs)} test(s) en échec : {', '.join(echecs)}")
    raise SystemExit(1)
print("🟢 batterie : tous les tests passent")
