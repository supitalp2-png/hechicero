#!/usr/bin/env python3
"""
reparer_langues_tracking.py — Redresse la colonne `langue` de tracking.db.

TICKET-146. `build_track_index()` lisait les clés `langue`/`lang` alors que les
podcasts de podcasts.json déclarent leur langue sous `language`. Le champ étant
absent, tout podcast retombait sur la valeur par défaut `fr` — y compris les
podcasts espagnols. Les webradios n'étaient pas touchées (elles utilisent bien
`lang`), ce qui a masqué le bug : le graphique « temps par langue » affichait
bien de l'espagnol, mais uniquement celui des radios.

Ce script relit la langue déclarée de chaque podcast et corrige les événements
historiques. Il ne touche jamais aux événements radio (is_radio=1), déjà justes.

Usage :
    python3 scripts/reparer_langues_tracking.py            # simulation
    python3 scripts/reparer_langues_tracking.py --appliquer # écrit
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from battery_common import DATA_DIR, load_json          # noqa: E402
from play_tracker import lire_langue                    # noqa: E402

DB_PATH = DATA_DIR / "tracking.db"
PODCASTS_PATH = DATA_DIR / "podcasts.json"


def langues_declarees() -> dict[str, str]:
    """podcast_id → langue déclarée dans podcasts.json."""
    data = load_json(PODCASTS_PATH, {})
    return {
        p["id"]: lire_langue(p)
        for p in data.get("podcasts", [])
        if p.get("id")
    }


def analyser(conn: sqlite3.Connection, declarees: dict[str, str]) -> tuple[list, list]:
    """
    Retourne (corrections, inconnus).

    corrections : [(podcast_id, langue_actuelle, langue_correcte, nb, secondes)]
    inconnus    : [(podcast_id, nb, secondes)] — plus dans podcasts.json,
                  laissés tels quels : on n'a plus de quoi trancher.
    """
    corrections: list = []
    inconnus: list = []

    rows = conn.execute(
        """SELECT podcast_id, langue, COUNT(*) AS n, COALESCE(SUM(listened_s), 0) AS s
           FROM play_events
           WHERE is_radio = 0
           GROUP BY podcast_id, langue"""
    ).fetchall()

    for pid, actuelle, n, secondes in rows:
        correcte = declarees.get(pid)
        if correcte is None:
            inconnus.append((pid, n, secondes))
        elif correcte != actuelle:
            corrections.append((pid, actuelle, correcte, n, secondes))

    corrections.sort(key=lambda c: -c[4])
    inconnus.sort(key=lambda c: -c[2])
    return corrections, inconnus


def appliquer(conn: sqlite3.Connection, corrections: list) -> int:
    total = 0
    for pid, actuelle, correcte, _n, _s in corrections:
        cur = conn.execute(
            "UPDATE play_events SET langue=? WHERE podcast_id=? AND langue=? AND is_radio=0",
            (correcte, pid, actuelle),
        )
        total += cur.rowcount
    conn.commit()
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--appliquer", action="store_true",
                    help="écrit réellement (sans ce drapeau : simulation)")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"❌ base introuvable : {DB_PATH}")
        return 1

    declarees = langues_declarees()
    if not declarees:
        print("❌ aucun podcast lu depuis podcasts.json — abandon (rien ne serait corrigé"
              " correctement)")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    corrections, inconnus = analyser(conn, declarees)

    if not corrections:
        print("✅ aucune correction nécessaire — toutes les langues sont cohérentes")
        conn.close()
        return 0

    print(f"{'podcast':<32} {'base':>5} → {'réel':<5} {'évts':>6} {'écoute':>10}")
    print("─" * 68)
    total_evts = total_sec = 0
    for pid, actuelle, correcte, n, secondes in corrections:
        print(f"{pid:<32} {actuelle:>5} → {correcte:<5} {n:>6} {secondes/3600:>9.1f} h")
        total_evts += n
        total_sec += secondes
    print("─" * 68)
    print(f"{'TOTAL':<32} {'':>5}   {'':<5} {total_evts:>6} {total_sec/3600:>9.1f} h")

    if inconnus:
        print(f"\n⚠️  {len(inconnus)} podcast(s) absent(s) de podcasts.json, laissés tels quels :")
        for pid, n, secondes in inconnus:
            print(f"   {pid:<32} {n:>6} évts  {secondes/3600:>6.1f} h")

    if not args.appliquer:
        print("\n🔍 SIMULATION — rien n'a été écrit.")
        print("   Relancer avec --appliquer pour corriger.")
        conn.close()
        return 0

    sauvegarde = DB_PATH.with_suffix(f".db.avant-146-{time.strftime('%Y%m%d-%H%M%S')}")
    conn.close()
    shutil.copy2(DB_PATH, sauvegarde)
    print(f"\n💾 sauvegarde : {sauvegarde.name}")

    conn = sqlite3.connect(str(DB_PATH))
    modifies = appliquer(conn, corrections)
    conn.close()
    print(f"✅ {modifies} événement(s) corrigé(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
