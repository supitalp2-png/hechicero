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

    # Charger l'existant (radios conservées, invariant 1.6)
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            log("WARNING: data.json invalide ou illisible, réinitialisation.")
            data = {"radios": [], "podcasts": []}
    else:
        data = {"radios": [], "podcasts": []}

    # Remplacer la section podcasts
    data["podcasts"] = []
    for meta in all_podcasts:
        data["podcasts"].append({
            "id": meta.id,
            "titre": meta.label,
            "langue": meta.language,
            "image": f"images/{meta.id}.jpg",
            "chapitres": [
                {
                    "id": e.id,
                    "titre": e.title,
                    "audio": _to_web_path(e.local_audio) if e.local_audio else "",
                    "duree": e.duration  # int secondes
                }
                for e in meta.episodes
                if e.local_audio  # exclure les épisodes non téléchargés
            ]
        })

    atomic_write_json(path, data)
    log("Updated data.json")
