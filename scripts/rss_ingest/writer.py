from pathlib import Path
from utils import atomic_write_json, log
from models import PodcastMeta

def write_meta(podcast_id: str, meta: PodcastMeta):
    path = Path(f"/home/thomas/hechicero/podcasts/{podcast_id}/meta.json")
    data = {
        "id": meta.id,
        "label": meta.label,
        "episodes": [e.__dict__ for e in meta.episodes]
    }
    atomic_write_json(path, data)
    log(f"Wrote meta.json for {podcast_id}")

def update_data_json(all_podcasts):
    path = Path("/home/thomas/hechicero/web/lecteur/data.json")

    # Charger l'existant
    if path.exists():
        import json
        with open(path) as f:
            data = json.load(f)
    else:
        data = {"radios": [], "podcasts": []}

    # Remplacer la section podcasts
    data["podcasts"] = []
    for meta in all_podcasts:
        data["podcasts"].append({
            "id": meta.id,
            "titre": meta.label,
            "image": f"images/{meta.id}.jpg",
            "episodes": [
                {
                    "id": e.id,
                    "titre": e.title,
                    "audio": e.local_audio,
                    "duree": e.duration
                }
                for e in meta.episodes
            ]
        })

    atomic_write_json(path, data)
    log("Updated data.json")
