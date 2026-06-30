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
SHUTDOWN_LEVEL_PCT = 7  # doit correspondre à DEFAULT_CRITICAL_LEVEL dans battery_watchdog


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
        }
    )


def dominant_mode_for_cycle(cycle: dict[str, Any]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for point in cycle.get("datapoints", []):
        counts[point.get("mpd_mode") or "idle"] += 1
    if not counts:
        return "idle"
    return max(counts.items(), key=lambda item: item[1])[0]


def close_discharge(cycle: dict[str, Any], sample: dict[str, Any]) -> None:
    if not cycle.get("discharge_start"):
        cycle["discharge_start"] = sample["timestamp"]
        cycle["level_start"] = sample["level"]
    cycle["discharge_end"] = sample["timestamp"]
    cycle["level_end"] = sample["level"]
    cycle["duration_minutes"] = minutes_between(cycle.get("discharge_start"), cycle.get("discharge_end"))
    cycle["dominant_mode"] = dominant_mode_for_cycle(cycle)
    cycle["charge_start"] = sample["timestamp"]


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
        if cycle.get("discharge_end") and cycle.get("duration_minutes") is not None
    ]
    recent = complete_cycles[-window:]

    discharge_ratios = []
    charge_ratios = []
    for i, cycle in enumerate(recent):
        level_start = cycle.get("level_start")
        level_end = cycle.get("level_end")
        duration = cycle.get("duration_minutes")
        if isinstance(level_start, (int, float)) and isinstance(level_end, (int, float)) and isinstance(duration, (int, float)):
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


def build_sample(sensor: Any, config: dict[str, Any], simulate: bool = False) -> dict[str, Any]:
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
        sensor_data = read_sensor_snapshot(sensor, config)

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

    record_point, transitioned = should_record_point(stats, sample, last_point)
    if not compute_only and record_point:
        cycle = ensure_open_cycle(history, sample)
        if transitioned and cycle.get("datapoints"):
            if sample["status"] == "charging":
                close_discharge(cycle, sample)
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

    if not compute_only and cycle and sample["status"] == "charging":
        cycle.setdefault("charge_start", sample["timestamp"])
        cycle["level_end"] = sample["level"]

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
    sample = build_sample(sensor, config, simulate=simulate)
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