#!/usr/bin/env python3
"""
seed_tracking.py — Génère des données de test réalistes dans tracking.db
Usage : python3 ~/hechicero/scripts/seed_tracking.py [--days N]

Simule ~3 mois d'écoute d'un enfant de 7 ans :
- Écoute plus le week-end et le mercredi (pas d'école)
- Heure d'écoute : matin (7h-9h), après-midi (14h-18h), soirée (18h-21h)
- FR majoritaire (~70%), ES croissant au fil du temps
- Progression réaliste dans les séries (épisodes dans l'ordre)
- Quelques radios en direct
- Streaks, pauses (vacances scolaires), regain après les vacances
"""
import sqlite3, random, time, math, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--days', type=int, default=90)
parser.add_argument('--keep', action='store_true', help='Garder les données existantes')
args = parser.parse_args()

DB = Path.home() / "hechicero/data/tracking.db"

# ── Catalogue ─────────────────────────────────────────────────────────────
PODCASTS_FR = [
    ("professeurcaillou",   780,  12),
    ("olma",                1200, 23),
    ("thomaspesquet",       900,  23),
    ("yoko",                660,  15),
    ("bestioles",           840,  20),
    ("bestiolesoceean",     900,  18),
    ("cest-pas-sorcier",    1440, 10),
]
PODCASTS_ES = [
    ("kranio",              1500, 15),
    ("camaleon",            1100, 12),
    ("buenasnoches",        600,  10),
]
RADIOS = [
    ("monpetitfranceinter", "Mon Petit France Inter"),
    ("radionationale",      "Radio Nacional"),
]

# ── Plages horaires réalistes ──────────────────────────────────────────────
# (heure_debut, heure_fin, poids)
SLOTS = [
    (7,  9,  15),   # matin avant école
    (12, 14, 10),   # pause déjeuner
    (14, 18, 35),   # après-midi (mercredi + week-end surtout)
    (18, 21, 30),   # soirée
    (21, 22,  8),   # avant dodo (plus rare)
    (9,  12,  2),   # exceptionnel matin semaine
]

def pick_hour(slots_def):
    pairs   = [(h0, h1) for h0, h1, _ in slots_def]
    weights = [w        for _,  _,  w in slots_def]
    h0, h1  = random.choices(pairs, weights=weights)[0]
    return random.uniform(h0, h1)

def is_school_day(day_of_week, week_num):
    """Lundi=0..Dimanche=6. Mercredi et week-end = pas école."""
    if day_of_week in (2, 5, 6):  # Mer, Sam, Dim
        return False
    # Vacances scolaires toutes les 7 semaines (approx)
    if week_num % 7 in (0, 1):
        return False
    return True

# ── Suivi de progression dans chaque série ────────────────────────────────
series_progress = {}  # podcast_id → indice épisode courant

def next_episode(pod_id, n_episodes):
    if pod_id not in series_progress:
        series_progress[pod_id] = 0
    ep = series_progress[pod_id]
    series_progress[pod_id] = (ep + 1) % n_episodes
    return f"ep{ep + 1:03d}"

# ── Connexion BDD ──────────────────────────────────────────────────────────
con = sqlite3.connect(DB)
con.execute("""CREATE TABLE IF NOT EXISTS play_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_start INTEGER NOT NULL, ts_end INTEGER,
    podcast_id TEXT NOT NULL, episode_id TEXT,
    langue TEXT NOT NULL DEFAULT 'fr',
    is_radio INTEGER NOT NULL DEFAULT 0,
    station_name TEXT, duration_s REAL DEFAULT 0,
    listened_s REAL NOT NULL DEFAULT 0,
    completed INTEGER NOT NULL DEFAULT 0
)""")
if not args.keep:
    con.execute("DELETE FROM play_events")
    print("🗑  Données existantes effacées")

now   = int(time.time())
rows  = []
DAYS  = args.days

for day_offset in range(DAYS):
    day_ts = now - (DAYS - 1 - day_offset) * 86400
    import datetime
    dt = datetime.datetime.fromtimestamp(day_ts)
    dow      = dt.weekday()   # 0=Lun..6=Dim
    week_num = day_offset // 7

    school   = is_school_day(dow, week_num)
    weekend  = dow in (5, 6)
    wednesday = dow == 2

    # Probabilité d'écoute ce jour-là
    listen_prob = 0.55 if school else 0.88

    # Vacances : forte probabilité + plus de sessions
    on_holiday = (week_num % 7 in (0, 1))
    if on_holiday:
        listen_prob = 0.95

    if random.random() > listen_prob:
        continue  # pas d'écoute ce jour

    # Nombre de sessions
    if on_holiday or weekend:
        n_sessions = random.randint(3, 7)
    elif wednesday:
        n_sessions = random.randint(2, 5)
    else:
        n_sessions = random.randint(1, 3)

    # Ratio ES croissant dans le temps (enfant progresse en espagnol)
    es_ratio = 0.15 + 0.30 * (day_offset / DAYS)  # 15% → 45%

    # Sessions du jour
    used_hours = []
    for _ in range(n_sessions):
        # Choisir une heure libre
        for attempt in range(10):
            hour_f = pick_hour(SLOTS)
            if all(abs(hour_f - h) > 0.4 for h in used_hours):
                break
        used_hours.append(hour_f)

        hour    = int(hour_f)
        minute  = int((hour_f - hour) * 60)
        ts_start = int(datetime.datetime(dt.year, dt.month, dt.day, hour, minute).timestamp())

        # Radio ou podcast ?
        if random.random() < 0.10:  # 10% de chance d'écouter la radio
            station_id, station_name = random.choice(RADIOS)
            lang = "fr" if "france" in station_id else "es"
            duration = random.randint(300, 2400)
            listened = duration  # radio = écoute complète
            rows.append((ts_start, ts_start + listened,
                         station_id, None, lang, 1, station_name,
                         duration, listened, 0))
            continue

        # Podcast : FR ou ES ?
        lang = "es" if random.random() < es_ratio else "fr"
        catalog = PODCASTS_ES if lang == "es" else PODCASTS_FR
        pod_id, avg_dur, n_ep = random.choice(catalog)

        ep_id    = next_episode(pod_id, n_ep)
        duration = max(180, avg_dur + random.randint(-90, 90))

        # Complétion : FR mieux que ES (enfant plus à l'aise), améliore avec le temps
        base_fr = 0.72 + 0.15 * (day_offset / DAYS)
        base_es = 0.45 + 0.30 * (day_offset / DAYS)
        pct     = random.uniform(base_fr - 0.15, min(1.0, base_fr + 0.10)) if lang == "fr" \
                  else random.uniform(base_es - 0.15, min(1.0, base_es + 0.15))
        pct     = max(0.05, pct)

        # Parfois écoute très courte (distraction)
        if random.random() < 0.08:
            pct = random.uniform(0.03, 0.20)

        listened  = round(duration * pct)
        completed = 1 if listened >= 0.9 * duration else 0
        ts_end    = ts_start + listened

        rows.append((ts_start, ts_end, pod_id, ep_id, lang, 0, None,
                     duration, listened, completed))

con.executemany("""INSERT INTO play_events
    (ts_start, ts_end, podcast_id, episode_id, langue, is_radio, station_name,
     duration_s, listened_s, completed)
    VALUES (?,?,?,?,?,?,?,?,?,?)""", rows)
con.commit()
con.close()

total_h = sum(r[8] for r in rows) / 3600
fr_rows = [r for r in rows if r[4] == 'fr' and not r[5]]
es_rows = [r for r in rows if r[4] == 'es' and not r[5]]
radio_rows = [r for r in rows if r[5]]
completed = sum(1 for r in rows if r[9])

print(f"✅ {len(rows)} écoutes générées sur {DAYS} jours dans {DB}")
print(f"   {len(fr_rows)} podcasts FR · {len(es_rows)} podcasts ES · {len(radio_rows)} radios")
print(f"   {total_h:.1f}h d'écoute totale · {completed} épisodes terminés")
print(f"   Recharge http://192.168.1.86/dashboard.php")
