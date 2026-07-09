import calendar
import feedparser
from models import Episode
from utils import log
from pathlib import Path
from typing import Optional
import re

def normalize_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())

# Bug TINA (2026-07-09, generique a tous les podcasts RSS) : "bande-annonce"
# (avec/sans tiret ou espace) - Thomas ne veut pas que ces items soient
# telecharges ni affiches comme episodes.
_TRAILER_RE = re.compile(r"^bande[\s-]?annonce", re.IGNORECASE)

def is_trailer(title: str) -> bool:
    return bool(_TRAILER_RE.match((title or "").strip()))

# Detection de saison (TICKET-104, 2026-07-09, demande Thomas : itunes:season
# en priorite, motif de titre en repli — PAS d'heuristique par ecart de date,
# invalidee explicitement pour des podcasts a sortie irreguliere comme
# Bestioles). Motif de titre attendu : "Nom de la saison N/M : ..." (ex:
# "Tina et les boucliers de Mars 3/10 : Le complot" -> "Tina et les boucliers
# de Mars"). Retourne None si rien n'est detectable (ex: Professeur Caillou) —
# pas de separation visuelle appliquee dans ce cas cote lecteur.
_SEASON_TITLE_RE = re.compile(r"^(.*\S)\s+\d+\s*/\s*\d+\s*:")

def detect_season(entry, title: str) -> Optional[str]:
    raw_season = entry.get("itunes_season")
    if raw_season:
        return str(raw_season).strip()
    m = _SEASON_TITLE_RE.match(title or "")
    if m:
        return m.group(1).strip()
    return None

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

    seen_ids = set()
    keyed_episodes = []  # (cle_tri_chronologique, Episode)
    for entry in feed.entries:
        if is_trailer(entry.title):
            continue

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

        # Doublons (rediffusion / republication en lot sous le meme titre) :
        # certains flux Radio France listent deux fois le meme episode - trouve
        # en diagnostiquant TINA (2026-07-09), plusieurs saisons dupliquees
        # avec un published incoherent sur la 2e occurrence. On ne garde que la
        # 1re occurrence rencontree dans le flux.
        if ep_id in seen_ids:
            continue
        seen_ids.add(ep_id)

        published_parsed = entry.get("published_parsed")
        sort_key = calendar.timegm(published_parsed) if published_parsed else 0

        keyed_episodes.append((sort_key, Episode(
            id=ep_id,
            title=entry.title,
            audio_url=audio_url,
            local_audio="",
            image_url=image_url,
            local_image=None,
            published=entry.get("published", ""),
            duration=parse_duration(entry.get("itunes_duration")),
            season=detect_season(entry, entry.title)
        )))

    # Ordre chronologique explicite (episode 1 -> dernier), plutot que de se
    # fier a l'ordre du flux RSS : certains flux ne sont pas strictement du
    # plus recent au plus ancien sur toute leur longueur (saisons multiples,
    # republications en lot avec dates incoherentes) - trouve en diagnostiquant
    # TINA (2026-07-09). Le tri par published_parsed est robuste face a ca,
    # contrairement a un simple reverse() de l'ordre du flux cote affichage.
    keyed_episodes.sort(key=lambda pair: pair[0])
    return [ep for _, ep in keyed_episodes]
