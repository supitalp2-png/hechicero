"""
Suivi de progression de l'ingestion — écrit dans /tmp/hechicero_progress.json
pour que l'interface admin puisse afficher des barres de progression en temps réel.
"""
import json
import time
from pathlib import Path

PROGRESS_FILE = Path("/tmp/hechicero_progress.json")

_state: dict = {}


def _save() -> None:
    try:
        PROGRESS_FILE.write_text(json.dumps(_state, ensure_ascii=False))
    except Exception:
        pass


def start(total_podcasts: int) -> None:
    global _state
    _state = {
        "status":          "running",
        "total_podcasts":  total_podcasts,
        "done_podcasts":   0,
        "current_label":   "Démarrage…",
        "current_id":      "",
        "total_episodes":  0,
        "done_episodes":   0,
        "errors":          [],
        "started_at":      int(time.time()),
        "finished_at":     None,
    }
    _save()


def start_podcast(id_: str, label: str, total: int) -> None:
    _state.update({
        "current_id":     id_,
        "current_label":  label,
        "total_episodes": total,
        "done_episodes":  0,
    })
    _save()


def episode_done(error: str = None) -> None:
    _state["done_episodes"] = _state.get("done_episodes", 0) + 1
    if error:
        _state["errors"].append(error)
    _save()


def podcast_done() -> None:
    _state["done_podcasts"] = _state.get("done_podcasts", 0) + 1
    _save()


def finish() -> None:
    _state.update({
        "status":        "done",
        "finished_at":   int(time.time()),
        "current_label": "Terminé",
    })
    _save()


def fatal_error(msg: str) -> None:
    _state.update({
        "status":        "error",
        "finished_at":   int(time.time()),
        "current_label": "Erreur",
    })
    _state.setdefault("errors", []).append(msg)
    _save()
