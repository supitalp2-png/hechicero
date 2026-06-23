import json
import os
from pathlib import Path
from utils import atomic_write_json, log
from models import PodcastMeta

# Racine du projet sur le système de fichiers
_HECHICERO_BASE = Path("/home/thomas/hechicero")

def _to_web_path(absolute_path: str) -> str:
    """Convertit un chemin absolu hechicero en chemin web (/podcasts/...)."""
    try:
        return "/" + Path(absolute_path).relative_to(_HECHICERO_BASE).as_posix()
    except ValueError:
        return absolute_path

def write_meta(podcast_id: str, meta: PodcastMeta):
    path = Path(f"/home/thomas/hechicero/podcasts/{podcast_id}/meta.json")
    data = {
        "id": meta.id,
        "label": meta.label,
        "language": meta.language,
        "episodes": [e.__dict__ for e in meta.episodes]
    }
    atomic_write_json(path, data)
    log(f"Wrote meta.json for {podcast_id}")

def update_data_json(all_podcasts):
    path = Path("/home/thomas/hechicero/web/lecteur/data.json")
    podcasts_cfg_path = Path("/home/thomas/hechicero/data/podcasts.json")

    # Les radios sont gérées par l'interface admin dans podcasts.json.
    # On les relit à chaque ingest pour répercuter les ajouts/suppressions de l'admin.
    try:
        if podcasts_cfg_path.exists():
            with open(podcasts_cfg_path) as f:
                cfg = json.load(f)
            radios = cfg.get("radios", [])
        else:
            radios = []
    except (json.JSONDecodeError, OSError):
        log("WARNING: podcasts.json illisible, radios non incluses dans data.json.")
        radios = []

    data = {"radios": radios, "podcasts": []}

    # Remplacer la section podcasts
    data["podcasts"] = []
    for meta in all_podcasts:
        cover_web = _to_web_path(meta.cover_image) if meta.cover_image else f"images/{meta.id}.jpg"
        data["podcasts"].append({
            "id": meta.id,
            "titre": meta.label,
            "langue": meta.language,
            "image": cover_web,
            "chapitres": [
                {
                    "id": e.id,
                    "titre": e.title,
                    "audio": _to_web_path(e.local_audio) if e.local_audio else "",
                    "image": _to_web_path(e.local_image) if e.local_image else "",
                    "duree": e.duration
                }
                for e in meta.episodes
                # On inclut tous les épisodes, audio vide = épisode pas encore téléchargé.
                # Le lecteur gère le cas audio="" (sera retéléchargé au prochain ingest).
            ]
        })

    atomic_write_json(path, data)
    log("Updated data.json")
