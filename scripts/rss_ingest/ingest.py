import json
from pathlib import Path
from parser import parse_rss
from downloader import download_episode
from writer import write_meta, update_data_json
from models import PodcastConfig, PodcastMeta
from utils import log

CONFIG_PATH = Path("/home/thomas/hechicero/data/podcasts.json")

def load_config():
    with open(CONFIG_PATH) as f:
        raw = json.load(f)
    return [PodcastConfig(**p) for p in raw["podcasts"] if p["enabled"]]

def ingest():
    log("=== Starting RSS ingestion ===")

    configs = load_config()
    all_meta = []

    for cfg in configs:
        log(f"Processing podcast: {cfg.id}")

        episodes = parse_rss(cfg)
        episodes = episodes[:cfg.max_episodes]

        downloaded = []
        for ep in episodes:
            downloaded.append(download_episode(cfg.id, ep))

        meta = PodcastMeta(
            id=cfg.id,
            label=cfg.label,
            episodes=downloaded
        )

        write_meta(cfg.id, meta)
        all_meta.append(meta)

    update_data_json(all_meta)
    log("=== RSS ingestion complete ===")

if __name__ == "__main__":
    ingest()
