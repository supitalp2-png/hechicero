import feedparser
from models import Episode
from utils import log
from pathlib import Path
import re

def normalize_id(text: str):
    return re.sub(r"[^a-z0-9]+", "", text.lower())

def parse_rss(podcast_config):
    log(f"Parsing RSS: {podcast_config.rss}")
    feed = feedparser.parse(podcast_config.rss)

    episodes = []
    for entry in feed.entries:
        audio_url = None
        image_url = None

        # Trouver l'audio
        for link in entry.get("links", []):
            if link.get("type", "").startswith("audio"):
                audio_url = link["href"]

        # Trouver l'image
        if "image" in entry:
            image_url = entry.image.href
        elif "itunes_image" in entry:
            image_url = entry.itunes_image

        ep_id = normalize_id(entry.title)

        episodes.append(Episode(
            id=ep_id,
            title=entry.title,
            audio_url=audio_url,
            local_audio="",
            image_url=image_url,
            local_image=None,
            published=entry.get("published", ""),
            duration=entry.get("itunes_duration")
        ))

    return episodes
