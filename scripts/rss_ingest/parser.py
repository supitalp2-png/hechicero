import feedparser
from models import Episode
from utils import log
from pathlib import Path
from typing import Optional
import re

def normalize_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())

def parse_duration(raw) -> Optional[int]:
    """Convertit itunes_duration en secondes (int).
    Accepte : 'HH:MM:SS', 'MM:SS', ou un entier brut."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    s = str(raw).strip()
    parts = s.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(s)
    except (ValueError, TypeError):
        return None

def parse_rss(podcast_config):
    log(f"Parsing RSS: {podcast_config.rss}")
    feed = feedparser.parse(podcast_config.rss)

    # Image de couverture au niveau du podcast (utilisée si l'épisode n'en a pas)
    feed_image = None
    if hasattr(feed.feed, "image") and hasattr(feed.feed.image, "href"):
        feed_image = feed.feed.image.href
    elif hasattr(feed.feed, "itunes_image"):
        feed_image = feed.feed.itunes_image.get("href") if isinstance(feed.feed.itunes_image, dict) else None

    episodes = []
    for entry in feed.entries:
        audio_url = None
        image_url = None

        # Trouver l'URL audio (enclosure ou lien audio)
        for enc in entry.get("enclosures", []):
            if enc.get("type", "").startswith("audio"):
                audio_url = enc.get("href") or enc.get("url")
                break
        if not audio_url:
            for link in entry.get("links", []):
                if link.get("type", "").startswith("audio"):
                    audio_url = link["href"]
                    break

        # Trouver l'image (épisode puis podcast)
        if hasattr(entry, "image") and hasattr(entry.image, "href"):
            image_url = entry.image.href
        elif hasattr(entry, "itunes_image"):
            img = entry.itunes_image
            image_url = img.get("href") if isinstance(img, dict) else img
        else:
            image_url = feed_image

        ep_id = normalize_id(entry.title)

        episodes.append(Episode(
            id=ep_id,
            title=entry.title,
            audio_url=audio_url,
            local_audio="",
            image_url=image_url,
            local_image=None,
            published=entry.get("published", ""),
            duration=parse_duration(entry.get("itunes_duration"))
        ))

    return episodes
