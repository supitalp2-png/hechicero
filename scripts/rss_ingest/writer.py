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

    # Préserver les radios depuis data.json existant (géré par l'interface admin)
    try:
        if path.exists():
            with open(path) as f:
                existing = json.load(f)
            radios = existing.get("radios", [])
        else:
            radios = []
    except (json.JSONDecodeError, OSError):
        log("WARNING: data.json illisible, radios préservées à vide.")
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
                    "duree": e.duration  # int secondes
                }
                for e in meta.episodes
                if e.local_audio  # exclure les épisodes non téléchargés
            ]
        })

    atomic_write_json(path, data)
    log("Updated data.json")
