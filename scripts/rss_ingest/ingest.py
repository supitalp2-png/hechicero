import json
import os
import sys
import argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from parser import parse_rss
from downloader import download_episode
from writer import write_meta, update_data_json
from models import PodcastConfig, PodcastMeta
from utils import log
import progress

CONFIG_PATH = Path("/home/thomas/hechicero/data/podcasts.json")

def load_config(podcast_id=None):
    with open(CONFIG_PATH) as f:
        raw = json.load(f)
    configs = [PodcastConfig(**p) for p in raw["podcasts"] if p["enabled"]]
    if podcast_id:
        configs = [cfg for cfg in configs if cfg.id == podcast_id]
    return configs

def ingest(podcast_id=None):
    log("=== Démarrage synchronisation ===")
    configs = load_config(podcast_id)
    if podcast_id and not configs:
        raise ValueError(f"Podcast introuvable ou désactivé: {podcast_id}")

    progress.start(len(configs))
    all_meta = []

    for cfg in configs:
        log(f"Podcast : {cfg.label} ({cfg.id})")
        if cfg.source_type == "html_radionacional":
            from scraper_radionacional import scrape_radionacional
            episodes = scrape_radionacional(cfg)
        else:
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

        # Télécharger la cover dans web/lecteur/images/ (accessible Apache)
        cover_local = None
        if episodes and episodes[0].image_url:
            from downloader import download_file
            cover_url = episodes[0].image_url
            cover_path = Path(f"/home/thomas/hechicero/web/lecteur/images/{cfg.id}.jpg")
            result = download_file(cover_url, cover_path)
            if result:
                cover_local = str(result)

        meta = PodcastMeta(
            id=cfg.id,
            label=cfg.label,
    