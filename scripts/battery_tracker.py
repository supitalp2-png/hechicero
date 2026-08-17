#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from battery_common import (
    DATA_DIR,
    PROJECT_ROOT,
    atomic_write_json,
    init_ina219,
    load_config,
    load_json,
    now_iso,
    read_mpd_status,
    read_screen_on,
    read_sensor_snapshot,
)


HISTORY_PATH = DATA_DIR / "battery_history.json"
STATS_PATH   = DATA_DIR / "battery_stats.json"
LEVEL_DELTA_THRESHOLD = 2
ESTIMATE_WINDOW = 10
SHUTDOWN_LEVEL_PCT = 7    # doit correspondre à DEFAULT_CRITICAL_LEVEL dans battery_watchdog
MIN_CYCLE_DEPTH_PCT = 3   # décharge minimum pour qu'un cycle soit valide (évite les micro-cycles CV)
MIN_CYCLE_DURATION_MIN = 5  # durée minimum en minutes
REAL_DISCHARGE_MA_THRESHOLD = -50  # même seuil de bruit que estimated_autonomy_minutes_live
# TICKET-133 : au-delà de ce trou, le tracker NE TOURNAIT PAS — appareil hors
# tension (arrêt d'urgence) ou service arrêté.
#
# ⚠️ Le trou se mesure sur `stats["last_updated"]`, PAS sur l'écart entre deux
# datapoints. Raison : `should_record_point()` n'enregistre un point que sur
# transition ou variation de niveau, donc plusieurs minutes peuvent séparer
# deux points pendant une décharge stable — un simple rebranchement aurait été
# signalé comme un arrêt. `battery_stats.json` est en revanche réécrit à
# CHAQUE tour de boucle (60 s), qu'un point soit retenu ou non : un écart
# important y est sans ambiguïté.
#
# 3 minutes = trois tours manqués. Le vrai trou mesuré le 2026-08-17 entre
# l'arrêt d'urgence et le rebranchement était de 5 minutes ; un seuil à 10
# l'aurait laissé passer.
GAP_MINUTES_THRESHOLD = 3
# TICKET-134 : en dessous de ce niveau, on enregistre chaque échantillon sans
# filtre de variation. Le coude de fin de décharge est rapide et ne se rejoue
# pas — mieux vaut quelques centaines de points de plus qu'une courbe tronquée
# là où elle est la plus instructive.
VERBOSE_BELOW_LEVEL = 20


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("battery_tracker")


def load_history() -> dict[str, Any]:
    history = load_json(HISTORY_PATH, {"cycles": []})
    if not isinstance(history, dict):
        return {"cycles": []}
    cycles = history.get("cycles")
    if not isinstance(cycles, list):
        history["cycles"] = []
    return history


def load_stats() -> dict[str, Any]:
    stats = load_json(STATS_PATH, {})
    return stats if isinstance(stats, dict) else {}


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def minutes_between(start: str | None, end: str | None) -> int | None:
    start_dt = parse_iso(start)
    end_dt = parse_iso(end)
    if not start_dt or not end_dt:
        return None
    delta = end_dt - start_dt
    return max(0, int(round(delta.total_seconds() / 60)))


def get_open_cycle(cycles: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not cycles:
        return None
    last_cycle = cycles[-1]
    if last_cycle.get("charge_end") or not last_cycle.get("charge_start"):
        if last_cycle.get("discharge_end") and last_cycle.get("charge_end"):
            return None
    return last_cycle


def new_cycle(sample: dict[str, Any]) -> dict[str, Any]:
    cycle = {"datapoints": []}
    if sample["status"] == "discharging":
        cycle["discharge_start"] = sample["timestamp"]
        cycle["level_start"] = sample["level"]
    else:
        cycle["charge_start"] = sample["timestamp"]
        cycle["level_end"] = sample["level"]
    return cycle


def append_datapoint(cycle: dict[str, Any], sample: dict[str, Any]) -> None:
    cycle.setdefault("datapoints", []).append(
        {
            "t": sample["timestamp"],
            "level": sample["level"],
            "charging": sample["charging"],
            "mpd_mode": sample["mpd_mode"],
            "screen": sample["screen_on"],
            "current_ma": sample.get("current_ma"),
            # TICKET-133 : la TENSION est la mesure primaire — le niveau n'en
            # est qu'une lecture de table (percent_from_voltage). Sans elle,
            # impossible de rejouer un diagnostic après coup ni de vérifier la
            # marge réelle au moment d'une coupure. Deux octets de plus par
            # point, et on cesse de raisonner sur une valeur dérivée.
            "voltage_v": sample.get("voltage_v"),
        }
    )


def active_discharge_minutes(cycle: dict[str, Any]) -> float | None:
    """Durée passée en décharge *réelle* (courant significatif), pas juste
    "non en charge". Un Pi branché sur secteur avec la batterie déjà pleine
    a un courant quasi nul mais est classé "discharging" faute d'état
    intermédiaire — sans ce filtre, ce temps gonfle artificiellement le
    ratio minutes/% et fausse l'autonomie estimée (ex: 182h calculées pour
    un Pi qui tient en réalité quelques heures).

    Retourne None si les datapoints n'ont pas de current_ma enregistré
    (cycles capturés avant l'ajout de ce champ) — dans ce cas on retombe sur
    duration_minutes (comportement historique, imprécis mais pas pire
    qu'avant) plutôt que de fabriquer un chiffre à partir de rien.
    """
    points = cycle.get("datapoints", [])
    discharge_points = [p for p in points if not p.get("charging", False)]
    if not discharge_points or all(p.get("current_ma") is None for p in discharge_points):
        return None

    total_seconds = 0.0
    for previous, current in zip(discharge_points, discharge_points[1:]):
        ma = current.get("current_ma")
        if ma is None or ma > REAL_DISCHARGE_MA_THRESHOLD:
            continue  # courant trop faible : probablement sur secteur, pas une vraie décharge
        start_dt = parse_iso(previous.get("t"))
        end_dt = parse_iso(current.get("t"))
        if not start_dt or not end_dt:
            continue
        total_seconds += max(0.0, (end_dt - start_dt).total_seconds())

    return total_seconds / 60


def dominant_mode_for_cycle(cycle: dict[str, Any]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for point in cycle.get("datapoints", []):
        counts[point.get("mpd_mode") or "idle"] += 1
    if not counts:
        return "idle"
    return max(counts.items(), key=lambda item: item[1])[0]


def close_discharge(cycle: dict[str, Any], sample: dict[str, Any],
                    gap_minutes: int | None = None) -> None:
    """Ferme la phase de décharge d'un cycle.

    ── TICKET-133 (2026-08-17) — pourquoi ce n'est pas `sample` qui fait foi ──
    L'ancienne version figeait `level_end` et `discharge_end` sur l'échantillon
    de BASCULE vers la charge. Or une décharge profonde se termine par l'arrêt
    d'urgence du Pi : la bascule n'est observée qu'au **redémarrage**, une fois
    rebranché. Résultat, mesuré sur le premier vrai cycle du 2026-08-17 :

        réel     : 85 %  ->  15 %   (arrêt à 20:07, ~212 min de lecture)
        enregistré : 85 % -> 28 %   avec 212 min incluant le temps hors tension

    `level_end: 28` était le niveau APRÈS rebranchement (la tension remonte dès
    que la charge cesse), pas le point bas atteint. Le ratio minutes/% en était
    faussé, donc l'autonomie estimée aussi.

    ⚠️ Ce n'est pas un cas rare : **tout** cycle profond finit par un arrêt,
    donc tous étaient faussés de la même façon — précisément ceux qui portent
    le plus d'information.

    On retient donc le **minimum réellement observé** et l'horodatage du
    **dernier point de décharge**, pas ceux de la bascule.
    """
    if not cycle.get("discharge_start"):
        cycle["discharge_start"] = sample["timestamp"]
        cycle["level_start"] = sample["level"]

    points_decharge = [p for p in cycle.get("datapoints", []) if not p.get("charging", False)]

    if points_decharge:
        niveaux = [p.get("level") for p in points_decharge if isinstance(p.get("level"), (int, float))]
        cycle["level_end"] = min(niveaux) if niveaux else sample["level"]
        cycle["discharge_end"] = points_decharge[-1].get("t") or sample["timestamp"]
        # Trou = le tracker ne tournait pas : Pi éteint (arrêt d'urgence) ou
        # service arrêté. Mesuré sur `stats["last_updated"]` par l'appelant, et
        # non sur l'écart entre datapoints — voir GAP_MINUTES_THRESHOLD.
        # On le rend explicite plutôt que de le noyer dans la durée : un cycle
        # avec `gap_minutes` se relit sans avoir à recalculer.
        if gap_minutes is not None and gap_minutes >= GAP_MINUTES_THRESHOLD:
            cycle["gap_minutes"] = gap_minutes
            cycle["gap_reason"] = "tracker à l'arrêt (appareil hors tension ?) entre le dernier relevé et la reprise"
    else:
        cycle["level_end"] = sample["level"]
        cycle["discharge_end"] = sample["timestamp"]

    cycle["duration_minutes"] = minutes_between(cycle.get("discharge_start"), cycle.get("discharge_end"))
    cycle["dominant_mode"] = dominant_mode_for_cycle(cycle)
    cycle["charge_start"] = sample["timestamp"]
    # Invalider les micro-cycles : phase CV en fin de charge ou bruit de mesure
    consumed = (cycle.get("level_start") or 0) - cycle["level_end"]
    duration = cycle.get("duration_minutes") or 0
    if consumed < MIN_CYCLE_DEPTH_PCT or duration < MIN_CYCLE_DURATION_MIN:
        cycle["invalid"] = True


def close_charge(cycle: dict[str, Any], sample: dict[str, Any]) -> None:
    if not cycle.get("charge_start"):
        cycle["charge_start"] = sample["timestamp"]
    cycle["charge_end"] = sample["timestamp"]
    cycle["charge_duration_minutes"] = minutes_between(cycle.get("charge_start"), cycle.get("charge_end"))


def ensure_open_cycle(history: dict[str, Any], sample: dict[str, Any]) -> dict[str, Any]:
    cycles = history.setdefault("cycles", [])
    cycle = get_open_cycle(cycles)
    if cycle is None:
        cycle = new_cycle(sample)
        cycles.append(cycle)
    return cycle


def should_record_point(stats: dict[str, Any], sample: dict[str, Any], last_point: dict[str, Any] | None) -> tuple[bool, bool]:
    if last_point is None:
        return True, True

    # ── TICKET-134 — tout enregistrer en bas de décharge ──────────────────
    # On ne SAIT PAS comment ces cellules se comportent en fin de décharge :
    # c'est précisément ce qu'on cherche à mesurer. Le filtre normal
    # (variation >= 2 points) convient à la partie linéaire, mais si le coude
    # final est rapide il l'échantillonnera trop grossièrement — et cette
    # courbe-là ne se rejoue pas sans refaire 12 h de cycle.
    # En dessous de ce niveau on enregistre donc TOUS les échantillons.
    # Quelques centaines de points de plus contre le risque de rater la seule
    # zone qui décide jusqu'où on peut descendre : le choix est vite fait.
    # Repère, à lire avec précaution : les anciennes cellules (18650) chutaient
    # de 49 % à 13 % en 4 min sous −2,9 A. Ce n'était PAS une défaillance mais
    # de l'affaissement dû à leur résistance interne. Des cellules différentes
    # donneront une autre pente — d'où la mesure.
    if not sample.get("charging") and sample.get("level") is not None \
            and sample["level"] <= VERBOSE_BELOW_LEVEL:
        return True, stats.get("status") != sample["status"]

    transition = last_point.get("charging") != sample["charging"]
    mpd_changed = last_point.get("mpd_mode") != sample["mpd_mode"]
    delta_reached = abs(int(last_point.get("level", sample["level"])) - sample["level"]) >= LEVEL_DELTA_THRESHOLD
    state_changed = stats.get("status") != sample["status"]
    return transition or mpd_changed or delta_reached or state_changed, transition or state_changed


def compute_consumption_by_mode(history: dict[str, Any]) -> dict[str, float | None]:
    totals: dict[str, dict[str, float]] = {
        "webradio": {"drop": 0.0, "hours": 0.0},
        "podcast": {"drop": 0.0, "hours": 0.0},
        "idle": {"drop": 0.0, "hours": 0.0},
    }

    for cycle in history.get("cycles", []):
        points = cycle.get("datapoints", [])
        for previous, current in zip(points, points[1:]):
            start_dt = parse_iso(previous.get("t"))
            end_dt = parse_iso(current.get("t"))
            if not start_dt or not end_dt:
                continue
            hours = max(0.0, (end_dt - start_dt).total_seconds() / 3600)
            if hours <= 0:
                continue
            drop = max(0.0, float(previous.get("level", 0)) - float(current.get("level", 0)))
            mode = previous.get("mpd_mode") or "idle"
            bucket = totals.setdefault(mode, {"drop": 0.0, "hours": 0.0})
            bucket["drop"] += drop
            bucket["hours"] += hours

    result: dict[str, float | None] = {}
    for mode, values in totals.items():
        hours = values["hours"]
        result[mode] = round(values["drop"] / hours, 2) if hours > 0 else None
    return result


def compute_estimates(history: dict[str, Any], stats: dict[str, Any], window: int = ESTIMATE_WINDOW, shutdown_pct: int = SHUTDOWN_LEVEL_PCT, capacity_mah: int = 0) -> dict[str, Any]:
    complete_cycles = [
        cycle for cycle in history.get("cycles", [])
        if cycle.get("discharge_end")
        and cycle.get("duration_minutes") is not None
        and not cycle.get("invalid", False)
        and ((cycle.get("level_start") or 0) - (cycle.get("level_end") or 0)) >= MIN_CYCLE_DEPTH_PCT
    ]
    recent = complete_cycles[-window:]

    discharge_ratios = []
    charge_ratios = []
    for i, cycle in enumerate(recent):
        level_start = cycle.get("level_start")
        level_end = cycle.get("level_end")
        # Durée de décharge *réelle* (courant significatif) si dispo, sinon
        # on retombe sur la durée totale du cycle (comportement historique).
        duration = active_discharge_minutes(cycle)
        if duration is None:
            duration = cycle.get("duration_minutes")
        if isinstance(level_start, (int, float)) and isinstance(level_end, (int, float)) and isinstance(duration, (int, float)) and duration > 0:
            consumed = level_start - level_end
            if consumed > 0:
                discharge_ratios.append(duration / consumed)

        charge_duration = cycle.get("charge_duration_minutes")
        # Le niveau atteint après la recharge = level_start du cycle suivant
        # (évite de supposer que la batterie revient à 100%, elle peut plafonner à ~65%)
        level_after_charge = recent[i + 1].get("level_start") if i + 1 < len(recent) else None
        if (
            isinstance(level_end, (int, float))
            and isinstance(charge_duration, (int, float))
            and isinstance(level_after_charge, (int, float))
        ):
            recovered = level_after_charge - level_end
            if recovered > 0:
                charge_ratios.append(charge_duration / recovered)

    current_level = float(stats.get("current_level") or 0)
    # Autonomie : niveau utilisable = niveau actuel - seuil d'arrêt d'urgence
    usable_level = max(0.0, current_level - shutdown_pct)
    ratio_discharge = sum(discharge_ratios) / len(discharge_ratios) if discharge_ratios else None
    ratio_charge = sum(charge_ratios) / len(charge_ratios) if charge_ratios else None
    cycles_recorded = len(complete_cycles)
    if cycles_recorded >= 10:
        confidence = "high"
    elif cycles_recorded >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    # Estimations historiques (ratio cycles passés)
    stats["estimated_autonomy_minutes"] = int(round(usable_level * ratio_discharge)) if ratio_discharge else None
    stats["estimated_charge_time_minutes"] = int(round((100 - current_level) * ratio_charge)) if ratio_charge else None

    # Estimation courant réel (INA219 live) — plus fiable si battery_capacity_mah est configuré
    current_ma = float(stats.get("current_ma") or 0)
    charging = bool(stats.get("charging"))
    if capacity_mah > 0:
        if not charging and current_ma < -50:
            # Décharge : courant mesurable et > seuil de bruit
            discharge_ma = abs(current_ma)
            remaining_mah = capacity_mah * usable_level / 100.0
            stats["estimated_autonomy_minutes_live"] = int(round(remaining_mah / discharge_ma * 60))
        else:
            stats.pop("estimated_autonomy_minutes_live", None)

        if charging and current_ma > 100:
            # Charge CC : extrapolation + facteur 1.4 pour estimer la phase CV
            remaining_to_charge_mah = capacity_mah * (100 - current_level) / 100.0
            stats["estimated_charge_time_minutes_live"] = int(round(remaining_to_charge_mah / current_ma * 60 * 1.4))
        else:
            stats.pop("estimated_charge_time_minutes_live", None)
    else:
        stats.pop("estimated_autonomy_minutes_live", None)
        stats.pop("estimated_charge_time_minutes_live", None)

    stats["cycles_recorded"] = cycles_recorded
    stats["model_confidence"] = confidence
    stats["consumption_by_mode"] = compute_consumption_by_mode(history)
    return stats


def build_sample(sensor: Any, config: dict[str, Any], simulate: bool = False,
                 previous_charging: bool | None = None) -> dict[str, Any]:
    if simulate:
        stats = load_stats()
        status = stats.get("status") or "discharging"
        level = int(stats.get("current_level", 73) or 73)
        charging = status == "charging"
        sensor_data = {
            "level": level,
            "voltage_v": round(3.0 + (level / 100.0) * 1.2, 3),
            "current_ma": 650.0 if charging else -480.0,
            "power_w": 3.2,
            "charging": charging,
            "status": status,
        }
    else:
        # TICKET-133 : l'état précédent alimente l'hystérésis de la bande morte.
        # Il est relu depuis battery_stats.json à chaque tour — le tracker n'a
        # pas d'état en mémoire, c'est le disque qui fait foi (cf. la procédure
        # de remise à zéro de TICKET-126).
        sensor_data = read_sensor_snapshot(sensor, config, previous_charging=previous_charging)

    mpd = read_mpd_status()
    screen_on = read_screen_on()
    sample = {
        **sensor_data,
        "timestamp": now_iso(),
        "screen_on": screen_on,
        "mpd_state": mpd["state"],
        "mpd_mode": mpd["mode"],
        "mpd_url": mpd["current"],
    }
    return sample


def update_history_and_stats(sample: dict[str, Any], *, compute_only: bool = False) -> tuple[dict[str, Any], dict[str, Any], bool]:
    history = load_history()
    stats = load_stats()
    cycles = history.setdefault("cycles", [])
    cycle = get_open_cycle(cycles)
    last_point = None
    if cycle is not None:
        datapoints = cycle.get("datapoints", [])
        if datapoints:
            last_point = datapoints[-1]

    # TICKET-133 : le tracker a-t-il cessé de tourner depuis le dernier relevé ?
    # `stats["last_updated"]` est réécrit à chaque tour (60 s), même sans
    # datapoint retenu — c'est donc le seul témoin fiable d'un appareil hors
    # tension. Calculé ici, où l'on dispose encore de l'ancien `stats`.
    gap_minutes = minutes_between(stats.get("last_updated"), sample["timestamp"])

    record_point, transitioned = should_record_point(stats, sample, last_point)
    if not compute_only and record_point:
        cycle = ensure_open_cycle(history, sample)
        if transitioned and cycle.get("datapoints"):
            if sample["status"] == "charging":
                close_discharge(cycle, sample, gap_minutes=gap_minutes)
            else:
                close_charge(cycle, sample)
                cycle = new_cycle(sample)
                cycles.append(cycle)
        elif sample["status"] == "charging" and cycle.get("discharge_end") and not cycle.get("charge_start"):
            cycle["charge_start"] = sample["timestamp"]

        append_datapoint(cycle, sample)

    if not compute_only and cycle and sample["status"] == "discharging" and "level_start" not in cycle:
        cycle["level_start"] = sample["level"]
        cycle["discharge_start"] = sample["timestamp"]

    # ⚠️ Ne PAS toucher à level_end ici pour chaque échantillon "charging" :
    # level_end doit représenter le niveau au moment où la décharge s'est
    # arrêtée (figé une seule fois par close_discharge()), pas le niveau
    # courant qui monte pendant la charge. Bug corrigé le 2026-07-06 : ce
    # bloc écrasait level_end à chaque poll pendant toute la charge, donc au
    # moment de la transition suivante il contenait le niveau de FIN de
    # charge (~95%) au lieu du point bas réel de la décharge — ce qui
    # rendait "consumed" (level_start - level_end) faux, voire négatif, et
    # invalidait à tort de vrais cycles profonds (ex: décharge 94%→39% sur
    # plusieurs jours, mesurée comme si le niveau avait *monté*).
    # charge_start est déjà couvert par close_discharge() et par le bloc
    # elif un peu plus haut (ligne ~317) — rien d'autre à faire ici.

    stats.update(
        {
            "current_level": sample["level"],
            "status": sample["status"],
            "current_mpd_mode": sample["mpd_mode"],
            "current_mpd_state": sample["mpd_state"],
            "current_mpd_url": sample["mpd_url"],
            "screen_on": sample["screen_on"],
            "charging": sample["charging"],
            "voltage_v": sample["voltage_v"],
            "current_ma": sample["current_ma"],
            "power_w": sample["power_w"],
            "last_updated": sample["timestamp"],
        }
    )
    if transitioned:
        stats["current_state_since"] = sample["timestamp"]
    else:
        stats.setdefault("current_state_since", sample["timestamp"])

    return history, stats, record_point


def write_outputs(history: dict[str, Any], stats: dict[str, Any]) -> None:
    atomic_write_json(HISTORY_PATH, history)
    atomic_write_json(STATS_PATH, stats)


def _shutdown_pct_from_config(config: dict[str, Any]) -> int:
    return int(config.get("critical_level_percent", config.get("shutdown_threshold_percent", SHUTDOWN_LEVEL_PCT)))


def collect_once(sensor: Any, config: dict[str, Any], simulate: bool = False, compute_only: bool = False) -> tuple[dict[str, Any], dict[str, Any], bool]:
    # TICKET-133 : état de charge du relevé précédent, lu sur disque.
    etat_precedent = load_stats().get("charging")
    sample = build_sample(sensor, config, simulate=simulate,
                          previous_charging=etat_precedent if isinstance(etat_precedent, bool) else None)
    history, stats, recorded = update_history_and_stats(sample, compute_only=compute_only)
    compute_estimates(
        history, stats,
        shutdown_pct=_shutdown_pct_from_config(config),
        capacity_mah=int(config.get("battery_capacity_mah", 0)),
    )
    write_outputs(history, stats)
    return sample, stats, recorded


def main() -> int:
    parser = argparse.ArgumentParser(description="Hechicero battery tracker")
    parser.add_argument("--test", action="store_true", help="Effectue une collecte unique et affiche le résultat")
    parser.add_argument("--compute-estimates", action="store_true", help="Recalcule les estimations à partir de l'historique")
    parser.add_argument("--simulate", action="store_true", help="Force une mesure simulée quand le matériel n'est pas disponible")
    args = parser.parse_args()

    config = load_config()
    sensor = init_ina219(int(config.get("ina219_addr", 0x43)))
    simulate = args.simulate or sensor is None

    if args.compute_estimates:
        stats = load_stats()
        history = load_history()
        sample = build_sample(sensor, config, simulate=simulate)
        stats.update(
            {
                "current_level": sample["level"],
                "status": sample["status"],
                "current_mpd_mode": sample["mpd_mode"],
                "current_mpd_state": sample["mpd_state"],
                "current_mpd_url": sample["mpd_url"],
                "screen_on": sample["screen_on"],
                "charging": sample["charging"],
                "voltage_v": sample["voltage_v"],
                "current_ma": sample["current_ma"],
                "power_w": sample["power_w"],
                "last_updated": sample["timestamp"],
            }
        )
        compute_estimates(
            history, stats,
            shutdown_pct=_shutdown_pct_from_config(config),
            capacity_mah=int(config.get("battery_capacity_mah", 0)),
        )
        atomic_write_json(STATS_PATH, stats)
        print(f"estimated_autonomy_minutes={stats.get('estimated_autonomy_minutes')}")
        print(f"estimated_autonomy_minutes_live={stats.get('estimated_autonomy_minutes_live')}")
        print(f"estimated_charge_time_minutes={stats.get('estimated_charge_time_minutes')}")
        print(f"estimated_charge_time_minutes_live={stats.get('estimated_charge_time_minutes_live')}")
        return 0

    if args.test:
        sample, stats, recorded = collect_once(sensor, config, simulate=simulate)
        print(
            f"level={sample['level']}% status={sample['status']} "
            f"mpd_mode={sample['mpd_mode']} screen_on={sample['screen_on']} recorded={recorded}"
        )
        print(f"battery_stats={STATS_PATH}")
        return 0

    interval = int(config.get("battery_check_interval_seconds", 60))
    startup_delay = int(config.get("battery_startup_delay_seconds", 30))
    LOGGER.info("Battery tracker starting from %s — attente %ss stabilisation INA219", PROJECT_ROOT, startup_delay)
    time.sleep(startup_delay)
    _alerted_30 = False  # garde-fous pour ne pas répéter l'alerte 30 min dans le même cycle
    _alerted_10 = False  # idem pour 10 min
    while True:
        try:
            sample, stats, recorded = collect_once(sensor, config, simulate=simulate)
            LOGGER.info(
                "Battery sample level=%s%% status=%s mpd=%s autonomy=%smin recorded=%s",
                sample["level"],
                sample["status"],
                sample["mpd_mode"],
                stats.get("estimated_autonomy_minutes"),
                recorded,
            )
            # DEBUG LOG — seuils d'alerte
            autonomy = stats.get("estimated_autonomy_minutes")
            if autonomy is not None and not sample["charging"]:
                if autonomy <= 10 and not _alerted_10:
                    LOGGER.warning("SEUIL 10 MIN atteint — autonomy=%smin level=%s%%", autonomy, sample["level"])
                    _alerted_10 = True
                elif autonomy <= 30 and not _alerted_30:
                    LOGGER.warning("SEUIL 30 MIN atteint — autonomy=%smin level=%s%%", autonomy, sample["level"])
                    _alerted_30 = True
            if sample["charging"]:
                _alerted_30 = False
                _alerted_10 = False
        except OSError as e:
            if e.errno == 121:
                LOGGER.warning("INA219 errno 121 — tentative de ré-initialisation du capteur")
                try:
                    sensor = init_ina219(int(config.get("ina219_addr", 0x43)))
                except Exception:
                    LOGGER.exception("Ré-initialisation INA219 échouée")
            else:
                LOGGER.exception("Battery tracker iteration failed (OSError)")
        except Exception:
            LOGGER.exception("Battery tracker iteration failed")
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())