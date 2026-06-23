import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from parser import parse_rss
from downloader import download_episode
from writer import write_meta, update_data_json
from models import PodcastConfig, PodcastMeta
from utils import log
import progress

CONFIG_PATH = Path("/home/thomas/hechicero/data/podcasts.json")

def load_config():
    with open(CONFIG_PATH) as f:
        raw = json.load(f)
    return [PodcastConfig(**p) for p in raw["podcasts"] if p["enabled"]]

def ingest():
    log("=== Démarrage synchronisation ===")
    configs = load_config()
    progress.start(len(configs))
    all_meta = []

    for cfg in configs:
        log(f"Podcast : {cfg.label} ({cfg.id})")
        episodes = parse_rss(cfg)
        episodes = episodes[:cfg.max_episodes]
        progress.start_podcast(cfg.id, cfg.label, len(episodes))

        downloaded = []
        for ep in episodes:
            try:
                result = download_episode(cfg.id, ep)
                downloaded.append(result)
                # Épisode en erreur si pas d'audio après tentative
                if ep.audio_url and not result.local_audio:
                    progress.episode_done(error=f"{cfg.id}/{ep.id} : téléchargement audio échoué")
                else:
                    progress.episode_done()
            except Exception as e:
                downloaded.append(ep)
                progress.episode_done(error=f"{cfg.id}/{ep.id} : {str(e)[:120]}")

        # Télécharger la cover du podcast depuis le RSS
        cover_local = None
        if episodes and episodes[0].image_url:
            from pathlib import Path
            from downloader import download_file
            cover_url = episodes[0].image_url
            cover_path = Path(f"/home/thomas/hechicero/podcasts/{cfg.id}/cover.jpg")
            result = download_file(cover_url, cover_path)
            if result:
                cover_local = str(result)

        meta = PodcastMeta(
            id=cfg.id,
            label=cfg.label,
            language=cfg.language,
            cover_image=cover_local,
            episodes=downloaded
        )
        write_meta(cfg.id, meta)
        all_meta.append(meta)
        progress.podcast_done()

    update_data_json(all_meta)
    progress.finish()
    log("=== Synchronisation terminée ===")

if __name__ == "__main__":
    try:
        ingest()
    except Exception as e:
        log(f"ERREUR FATALE : {e}")
        progress.fatal_error(str(e)[:300])
