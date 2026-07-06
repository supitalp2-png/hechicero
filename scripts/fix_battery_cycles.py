#!/usr/bin/env python3
"""Répare les cycles batterie enregistrés avant le correctif du 2026-07-06.

Bug : `battery_tracker.py` écrasait `level_end` à chaque échantillon pendant
toute la phase de charge (au lieu de le figer une seule fois à la fin de la
décharge), donc `level_end` contenait le niveau de fin de charge (~95%) au
lieu du vrai point bas de la décharge. Résultat : la profondeur de décharge
("consumed" = level_start - level_end) était fausse, parfois négative, et de
vrais cycles profonds étaient invalidés à tort.

Ce script recalcule `level_end` pour chaque cycle qui a un `discharge_end`,
à partir du dernier point de `datapoints` où `charging` est faux (le vrai
niveau au moment où la décharge s'est arrêtée) — puis réévalue le flag
`invalid` avec les mêmes seuils que battery_tracker.py.

Usage :
    python3 scripts/fix_battery_cycles.py            # dry-run, affiche ce qui changerait
    python3 scripts/fix_battery_cycles.py --apply     # applique et sauvegarde
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

HISTORY_PATH = Path(__file__).resolve().parents[1] / "data" / "battery_history.json"
MIN_CYCLE_DEPTH_PCT = 3
MIN_CYCLE_DURATION_MIN = 5


def true_discharge_end_level(cycle: dict) -> int | None:
    last_discharge_point = None
    for point in cycle.get("datapoints", []):
        if not point.get("charging", False):
            last_discharge_point = point
    return last_discharge_point.get("level") if last_discharge_point else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Applique et sauvegarde (sinon dry-run)")
    args = parser.parse_args()

    history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    cycles = history.get("cycles", [])
    changed = 0

    for i, cycle in enumerate(cycles):
        if not cycle.get("discharge_end"):
            continue  # cycle en cours, rien à réparer

        true_end = true_discharge_end_level(cycle)
        if true_end is None:
            continue

        old_end = cycle.get("level_end")
        if old_end == true_end:
            continue

        level_start = cycle.get("level_start") or 0
        duration = cycle.get("duration_minutes") or 0
        consumed = level_start - true_end
        new_invalid = consumed < MIN_CYCLE_DEPTH_PCT or duration < MIN_CYCLE_DURATION_MIN

        print(f"Cycle {i} ({cycle.get('discharge_start')}) : level_end {old_end} -> {true_end} "
              f"(consumed {level_start - (old_end or 0)} -> {consumed}, invalid {cycle.get('invalid')} -> {new_invalid})")

        if args.apply:
            cycle["level_end"] = true_end
            cycle["invalid"] = new_invalid
        changed += 1

    if changed == 0:
        print("Rien à réparer.")
        return 0

    if args.apply:
        backup = HISTORY_PATH.with_suffix(".json.bak")
        shutil.copy(HISTORY_PATH, backup)
        HISTORY_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n{changed} cycle(s) corrigé(s). Sauvegarde de l'ancien fichier : {backup}")
    else:
        print(f"\n{changed} cycle(s) seraient corrigés. Relance avec --apply pour appliquer.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
