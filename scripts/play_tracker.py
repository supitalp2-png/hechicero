#!/usr/bin/env python3
"""
play_tracker.py — Suivi de lecture event-driven via MPD idle.

Principes :
  • Connexion MPD persistante, `idle player` : zéro poll quand rien ne se passe
  • Mesure le flux audio réel, indépendamment du client (Chromium, PC, etc.)
  • Heartbeat toutes les 5 min pendant la lecture → listened_s toujours à jour
  • Démarrage : répare les sessions non fermées (coupure courant / reboot)
    via /proc/uptime comme borne supérieure conservative

Cycle de vie d'une session :
  MPD play (nouveau fichier) → INSERT play_events (ts_end=NULL)
  MPD idle → UPDATE listened_s (heartbeat)
  MPD stop / changement de fichier → UPDATE ts_end + listened_s + completed
  Reboot / crash → ts_end = heure de boot, listened_s = dernier heartbeat
"""
from __future__ import annotations

import logging
import socket
import sqlite3
import time
from pathlib import Path
from typing import Any

from battery_common import DATA_DIR, PROJECT_ROOT, load_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("play_tracker")

DB_PATH = DATA_DIR / "tracking.db"
PODCASTS_PATH = DATA_DIR / "podcasts.json"
MPD_SOCKET = "/run/mpd/socket"
HEARTBEAT_S = 300    # 5 minutes entre heartbeats
RECONNECT_S = 15     # délai avant reconnexion MPD après erreur


# ─── Base de données ──────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS play_events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_start     INTEGER NOT NULL,
            ts_end       INTEGER DEFAULT NULL,
            podcast_id   TEXT NOT NULL,
            episode_id   TEXT DEFAULT NULL,
            langue       TEXT NOT NULL DEFAULT 'fr',
            is_radio     INTEGER NOT NULL DEFAULT 0,
            station_name TEXT DEFAULT NULL,
            duration_s   REAL DEFAULT 0,
            listened_s   REAL NOT NULL DEFAULT 0,
            completed    INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ts  ON play_events(ts_start)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pod ON play_events(podcast_id)")
    # Migrations : ajout de colonnes si absentes (base existante)
    for ddl in [
        "ALTER TABLE play_events ADD COLUMN volume_pct   INTEGER DEFAULT NULL",
        "ALTER TABLE play_events ADD COLUMN output_mode  TEXT    DEFAULT NULL",
    ]:
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass  # colonne déjà présente
    conn.commit()
    return conn


def db_open_session(conn: sqlite3.Connection, meta: dict[str, Any], ts_start: int, volume_pct: int | None = None, output_mode: str | None = None) -> int:
    cur = conn.execute(
        """INSERT INTO play_events
           (ts_start, podcast_id, episode_id, langue, is_radio, station_name, duration_s, volume_pct, output_mode)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ts_start,
            meta["podcast_id"],
            meta.get("episode_id"),
            meta.get("langue", "fr"),
            1 if meta.get("is_radio") else 0,
            meta.get("station_name"),
            meta.get("duration_s", 0),
            volume_pct,
            output_mode,
        ),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def db_close_session(conn: sqlite3.Connection, sid: int, ts_end: int, listened_s: float, volume_avg: int | None = None) -> None:
    row = conn.execute("SELECT ts_start, duration_s FROM play_events WHERE id=?", (sid,)).fetchone()
    duration_s = float(row["duration_s"] or 0) if row else 0.0
    # MPD retourne elapsed=0 quand l'état est "stop" → la position est perdue.
    # Fallback : ts_end - ts_start, capé à duration_s pour éviter les valeurs aberrantes
    # (ex : session jamais fermée proprement → ts_end - ts_start >> durée réelle).
    if listened_s == 0 and row:
        elapsed = float(ts_end - row["ts_start"])
        listened_s = min(elapsed, duration_s) if duration_s > 0 else elapsed
    completed = 1 if duration_s > 0 and listened_s >= 0.9 * duration_s else 0
    conn.execute(
        "UPDATE play_events SET ts_end=?, listened_s=?, completed=?, volume_pct=? WHERE id=?",
        (ts_end, listened_s, completed, volume_avg, sid),
    )
    conn.commit()


def db_heartbeat(conn: sqlite3.Connection, sid: int, listened_s: float, volume_avg: int | None = None) -> None:
    conn.execute(
        "UPDATE play_events SET listened_s=?, volume_pct=? WHERE id=?",
        (listened_s, volume_avg, sid),
    )
    conn.commit()


# ─── Réparation au démarrage ──────────────────────────────────────────────────

def boot_timestamp() -> int:
    """Retourne le timestamp Unix du dernier démarrage du Pi."""
    try:
        uptime_s = float(Path("/proc/uptime").read_text().split()[0])
        return int(time.time() - uptime_s)
    except Exception:
        return 0


def heal_interrupted_sessions(conn: sqlite3.Connection) -> None:
    """
    Ferme les sessions non terminées du run précédent.

    Cas typiques : coupure courant, reboot, crash du service.
    On scelle chaque session avec ts_end = heure de boot (borne supérieure
    conservative). listened_s reste à la dernière valeur heartbeat connue,
    ce qui donne une estimation fiable même sans ts_end exact.
    """
    boot_ts = boot_timestamp()
    if not boot_ts:
        return

    rows = conn.execute(
        "SELECT id, ts_start, listened_s, duration_s FROM play_events WHERE ts_end IS NULL"
    ).fetchall()

    healed = 0
    for row in rows:
        # Marge de 10s pour ne pas fermer une session qui vient juste de s'ouvrir
        if row["ts_start"] < boot_ts - 10:
            listened_s = float(row["listened_s"] or 0)
            duration_s = float(row["duration_s"] or 0)
            completed = 1 if duration_s > 0 and listened_s >= 0.9 * duration_s else 0
            conn.execute(
                "UPDATE play_events SET ts_end=?, completed=? WHERE id=?",
                (boot_ts, completed, row["id"]),
            )
            LOGGER.info(
                "Session réparée id=%d ts_start=%d listened_s=%.0fs → ts_end=%d (boot)",
                row["id"], row["ts_start"], listened_s, boot_ts,
            )
            healed += 1

    if healed:
        conn.commit()


# ─── Identification des pistes ────────────────────────────────────────────────

def build_track_index() -> dict[str, Any]:
    """
    Construit deux index depuis podcasts.json :
      pods[podcast_id]  → langue
      radios[url]       → {id, name, langue}
    """
    data = load_json(PODCASTS_PATH, {})

    pods: dict[str, str] = {}
    for p in data.get("podcasts", []):
        pid = p.get("id", "")
        if pid:
            pods[pid] = (p.get("langue") or p.get("lang") or "fr").lower()

    radios: dict[str, dict[str, str]] = {}
    for r in data.get("radios", []):
        url = r.get("url", "")
        if url:
            radios[url] = {
                "id": r.get("id", "radio"),
                "name": r.get("name", ""),
                "langue": (r.get("langue") or r.get("lang") or "fr").lower(),
            }

    return {"pods": pods, "radios": radios}


def identify(file_uri: str, duration_s: float, index: dict[str, Any]) -> dict[str, Any] | None:
    """
    Identifie une piste MPD et retourne un dict compatible play_events.
    Retourne None si la piste n'est pas reconnaissable.
    """
    if not file_uri:
        return None

    # ── Webradio (URL HTTP) ─────────────────────────────────────────────────
    if file_uri.startswith(("http://", "https://")):
        station = index["radios"].get(file_uri)
        if station:
            return {
                "podcast_id": station["id"],
                "episode_id": None,
                "langue": station["langue"],
                "is_radio": True,
                "station_name": station["name"],
                "duration_s": 0,
            }
        # URL inconnue (station ajoutée mais pas dans podcasts.json)
        label = file_uri.split("/")[-1][:80] or file_uri[:80]
        return {
            "podcast_id": "radio",
            "episode_id": None,
            "langue": "fr",
            "is_radio": True,
            "station_name": label,
            "duration_s": 0,
        }

    # ── Podcast (chemin local) ──────────────────────────────────────────────
    # MPD peut retourner un chemin absolu (/home/thomas/hechicero/podcasts/...)
    # ou relatif (podcasts/...). On normalise en chemin relatif à PROJECT_ROOT.
    p = Path(file_uri)
    try:
        p = p.relative_to(PROJECT_ROOT)
    except ValueError:
        pass  # déjà relatif ou chemin hors projet

    parts = p.parts
    if "podcasts" not in parts:
        return None   # fichier local non reconnu (chime, etc.)

    pod_idx = parts.index("podcasts")
    if pod_idx + 1 >= len(parts):
        return None

    podcast_id = parts[pod_idx + 1]
    episode_id = Path(file_uri).stem
    langue = index["pods"].get(podcast_id, "fr")

    return {
        "podcast_id": podcast_id,
        "episode_id": episode_id,
        "langue": langue,
        "is_radio": False,
        "station_name": None,
        "duration_s": duration_s,
    }


# ─── Client MPD (socket Unix brut, sans dépendance externe) ──────────────────

class MpdClient:
    """
    Client MPD léger sur socket Unix.
    Implémente le minimum nécessaire : status, currentsong, idle player.
    """
    BUFSIZE = 8192

    def __init__(self, socket_path: str = MPD_SOCKET) -> None:
        self.path = socket_path
        self._sock: socket.socket | None = None

    def connect(self) -> None:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(self.path)
        s.settimeout(3.0)
        self._sock = s
        s.recv(self.BUFSIZE)   # lire le greeting "OK MPD x.x.x\n" (pas de "OK\n" seul)
        LOGGER.info("Connecté à MPD (%s)", self.path)

    def disconnect(self) -> None:
        if self._sock:
            try:
                self._sock.sendall(b"close\n")
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _recv(self, timeout: float = 3.0) -> list[str]:
        assert self._sock
        self._sock.settimeout(timeout)
        buf = b""
        while True:
            chunk = self._sock.recv(self.BUFSIZE)
            if not chunk:
                raise ConnectionError("MPD a fermé la connexion")
            buf += chunk
            text = buf.decode("utf-8", errors="ignore")
            if text.endswith("OK\n") or "\nOK\n" in text or "ACK " in text:
                return [line for line in text.splitlines() if line]

    def _send(self, data: bytes) -> None:
        assert self._sock
        self._sock.sendall(data)

    @staticmethod
    def _parse(lines: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in lines:
            if ": " in line and not line.startswith(("OK", "ACK")):
                k, _, v = line.partition(": ")
                result[k.strip()] = v.strip()
        return result

    def status_and_song(self) -> tuple[dict[str, str], dict[str, str]]:
        self._send(b"status\n")
        status = self._parse(self._recv())
        self._send(b"currentsong\n")
        song = self._parse(self._recv())
        return status, song

    def get_output_mode(self) -> str:
        """Retourne 'casque' si la sortie USB (output 1) est active, 'hp' sinon."""
        self._send(b"outputs\n")
        lines = self._recv()
        current_id: str | None = None
        for line in lines:
            if line.startswith("outputid: "):
                current_id = line.split(": ", 1)[1].strip()
            elif line == "outputenabled: 1" and current_id == "1":
                return "casque"
        return "hp"

    def wait_event(self) -> set[str]:
        """
        Envoie `idle player mixer output`, attend jusqu'à HEARTBEAT_S secondes.
        Retourne l'ensemble des sous-systèmes qui ont changé :
          {'player'}          → play/pause/stop/changement de piste
          {'mixer'}           → changement de volume uniquement
          {'output'}          → bascule HP/casque (enableoutput/disableoutput)
          set()               → timeout heartbeat, rien n'a changé
          (combinaisons possibles si plusieurs surviennent dans le même idle)
        Dans tous les cas, la connexion est prête pour d'autres commandes.
        """
        assert self._sock
        self._send(b"idle player mixer output\n")

        deadline = time.monotonic() + HEARTBEAT_S
        buf = b""

        while True:
            remaining = deadline - time.monotonic()

            if remaining <= 0:
                self._send(b"noidle\n")
                self._sock.settimeout(3.0)
                try:
                    chunk = self._sock.recv(self.BUFSIZE)
                    if chunk:
                        buf += chunk
                except socket.timeout:
                    pass
                text = buf.decode("utf-8", errors="ignore")
                return {line.split(": ", 1)[1] for line in text.splitlines()
                        if line.startswith("changed: ")}

            self._sock.settimeout(min(remaining, 10.0))
            try:
                chunk = self._sock.recv(self.BUFSIZE)
                if not chunk:
                    raise ConnectionError("MPD a fermé la connexion")
                buf += chunk
                text = buf.decode("utf-8", errors="ignore")
                if "OK\n" in text or "ACK " in text:
                    return {line.split(": ", 1)[1] for line in text.splitlines()
                            if line.startswith("changed: ")}
            except socket.timeout:
                continue   # recalcule remaining et recommence


# ─── Boucle principale ────────────────────────────────────────────────────────

def run() -> None:
    conn = get_db()
    heal_interrupted_sessions(conn)
    index = build_track_index()

    # État courant
    open_id: int | None = None    # id de la session play_events en cours
    open_file: str | None = None  # fichier MPD de cette session
    open_mode: str | None = None  # 'hp' | 'casque' de la session en cours
    open_elapsed_offset: float = 0.0  # elapsed MPD au dernier découpage (bascule sortie)
    prev_state: str = "stopped"
    # Volume : liste de mesures pour calcul de la moyenne pondérée par session
    vol_samples: list[int] = []

    mpd = MpdClient()
    LOGGER.info("play_tracker démarré")

    def parse_volume(status: dict[str, str]) -> int | None:
        """Extrait le volume MPD (0-100) depuis le status, None si indisponible."""
        raw = status.get("volume", "")
        try:
            v = int(raw)
            return v if 0 <= v <= 100 else None
        except (ValueError, TypeError):
            return None

    def vol_avg() -> int | None:
        """Retourne la moyenne des échantillons de volume, ou None."""
        valid = [v for v in vol_samples if v is not None]
        return round(sum(valid) / len(valid)) if valid else None

    while True:
        try:
            mpd.connect()

            # ── Synchronisation de l'état initial ──────────────────────────
            status, song = mpd.status_and_song()
            prev_state = status.get("state", "stopped")
            cur_file = song.get("file", "")

            if prev_state == "play" and cur_file:
                elapsed = float(status.get("elapsed", 0) or 0)
                duration = float(status.get("duration", 0) or 0)
                vol = parse_volume(status)
                meta = identify(cur_file, duration, index)
                if meta:
                    ts_start = int(time.time() - elapsed) if elapsed < 60 else int(time.time())
                    mode = mpd.get_output_mode()
                    open_id = db_open_session(conn, meta, ts_start, vol, mode)
                    open_file = cur_file
                    open_mode = mode
                    open_elapsed_offset = 0.0
                    vol_samples = [vol] if vol is not None else []
                    LOGGER.info("Session initiale : %s id=%d vol=%s%% mode=%s", meta["podcast_id"], open_id, vol, mode)

            # ── Boucle d'événements ─────────────────────────────────────────
            while True:
                changed = mpd.wait_event()

                if not changed:
                    # Heartbeat (timeout) : mise à jour listened_s + volume
                    if open_id:
                        status, _ = mpd.status_and_song()
                        if status.get("state") == "play":
                            # max(0.0, ...) : MPD peut renvoyer un elapsed < open_elapsed_offset
                            # (ex: repeat/single qui boucle sur le même fichier, elapsed retombe
                            # à ~0 avant que l'event "player" du bouclage soit traité) — sans ce
                            # clamp, un listened_s négatif est écrit tel quel en base et fausse
                            # tous les totaux qui en dépendent (dashboard fatigue auditive,
                            # export Prometheus TICKET-017). Même pattern que la bascule de
                            # sortie HP/casque ci-dessous, qui était déjà clampée.
                            elapsed = max(0.0, float(status.get("elapsed", 0) or 0) - open_elapsed_offset)
                            vol = parse_volume(status)
                            if vol is not None:
                                vol_samples.append(vol)
                            db_heartbeat(conn, open_id, elapsed, vol_avg())
                            LOGGER.debug("Heartbeat id=%d elapsed=%.0fs vol=%s%%", open_id, elapsed, vol)
                    continue

                # ── Bascule de sortie (HP ↔ casque) en cours de lecture ─────
                # Sans ça, le mode enregistré reste figé sur celui du début de
                # la piste — on scinde la session en deux pour attribuer
                # correctement le temps écouté à chaque mode (widget fatigue
                # auditive : mesure de sécurité, doit être exact).
                if "output" in changed:
                    new_mode = mpd.get_output_mode()
                    if open_id and new_mode != open_mode:
                        status, song = mpd.status_and_song()
                        if status.get("state") == "play":
                            elapsed_raw = float(status.get("elapsed", 0) or 0)
                            duration = float(status.get("duration", 0) or 0)
                            vol = parse_volume(status)
                            if vol is not None:
                                vol_samples.append(vol)
                            listened_leg = max(0.0, elapsed_raw - open_elapsed_offset)
                            now = int(time.time())
                            db_close_session(conn, open_id, now, listened_leg, vol_avg())
                            LOGGER.info(
                                "Session scindée (bascule sortie %s→%s) id=%d listened=%.0fs",
                                open_mode, new_mode, open_id, listened_leg,
                            )
                            meta = identify(open_file or "", duration, index)
                            if meta:
                                open_id = db_open_session(conn, meta, now, vol, new_mode)
                                open_elapsed_offset = elapsed_raw
                                open_mode = new_mode
                                vol_samples = [vol] if vol is not None else []
                                LOGGER.info("Nouvelle session (suite bascule) id=%d mode=%s", open_id, new_mode)
                            else:
                                open_id = None
                                open_file = None
                        else:
                            open_mode = new_mode
                    elif open_id is None:
                        open_mode = new_mode
                    if changed == {"output"}:
                        continue
                    changed.discard("output")

                if "mixer" in changed and "player" not in changed:
                    # Volume changé sans event player → juste enregistrer le nouveau volume
                    status, _ = mpd.status_and_song()
                    vol = parse_volume(status)
                    if vol is not None and open_id:
                        vol_samples.append(vol)
                        elapsed = max(0.0, float(status.get("elapsed", 0) or 0) - open_elapsed_offset)
                        db_heartbeat(conn, open_id, elapsed, vol_avg())
                        LOGGER.info("Volume changé : %d%% (moy session : %s%%)", vol, vol_avg())
                    continue

                if "player" not in changed:
                    continue

                # ── Événement player ────────────────────────────────────────
                status, song = mpd.status_and_song()
                new_state = status.get("state", "stopped")
                new_file = song.get("file", "")
                elapsed = float(status.get("elapsed", 0) or 0)
                duration = float(status.get("duration", 0) or 0)
                vol = parse_volume(status)
                now = int(time.time())

                file_changed = bool(new_file) and new_file != open_file

                LOGGER.info(
                    "event : %s→%s  file=%s  elapsed=%.0fs  vol=%s%%",
                    prev_state, new_state, new_file or "(none)", elapsed, vol,
                )

                # Fermer la session courante si stop ou changement de fichier
                if open_id and (new_state == "stop" or file_changed):
                    if vol is not None:
                        vol_samples.append(vol)
                    listened_final = max(0.0, elapsed - open_elapsed_offset)
                    db_close_session(conn, open_id, now, listened_final, vol_avg())
                    LOGGER.info("Session fermée id=%d listened=%.0fs vol_avg=%s%%", open_id, listened_final, vol_avg())
                    open_id = None
                    open_file = None
                    open_elapsed_offset = 0.0
                    vol_samples = []

                # Ouvrir une nouvelle session si on lit un nouveau fichier
                # pause→play ne recrée pas de session (open_id reste valide)
                if new_state == "play" and new_file and (file_changed or prev_state == "stop" or open_id is None):
                    meta = identify(new_file, duration, index)
                    if meta:
                        ts_start = int(time.time() - elapsed) if elapsed < 30 else now
                        vol_samples = [vol] if vol is not None else []
                        mode = mpd.get_output_mode()
                        open_id = db_open_session(conn, meta, ts_start, vol, mode)
                        open_file = new_file
                        open_mode = mode
                        open_elapsed_offset = 0.0
                        LOGGER.info(
                            "Nouvelle session : %s  id=%d  langue=%s  radio=%s  vol=%s%%  mode=%s",
                            meta["podcast_id"], open_id, meta["langue"], meta.get("is_radio"), vol, mode,
                        )

                prev_state = new_state

        except (ConnectionError, OSError) as exc:
            LOGGER.warning("MPD déconnecté : %s — reconnexion dans %ds", exc, RECONNECT_S)
            mpd.disconnect()
            if open_id:
                db_close_session(conn, open_id, int(time.time()), 0, vol_avg())
                open_id = None
                open_file = None
                vol_samples = []
            time.sleep(RECONNECT_S)

        except Exception:
            LOGGER.exception("Erreur inattendue — pause 30s")
            time.sleep(30)


if __name__ == "__main__":
    run()
