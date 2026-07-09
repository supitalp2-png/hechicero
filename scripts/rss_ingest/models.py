from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Episode:
    id: str
    title: str
    audio_url: str
    local_audio: str
    image_url: Optional[str]
    local_image: Optional[str]
    published: str
    duration: Optional[int]
    # Identifiant de saison (TICKET-104, 2026-07-09) : itunes:season du flux si
    # present, sinon deduit du titre (ex: "Tina et les boucliers de Mars 3/10 : ..."
    # -> "Tina et les boucliers de Mars"). None si aucune saison detectable
    # (ex: Professeur Caillou, Bestioles) - pas de separation visuelle dans ce cas.
    season: Optional[str] = None

@dataclass
class PodcastConfig:
    id: str
    label: str
    rss: str
    enabled: bool
    language: str
    image: str
    max_episodes: int
    source_type: str = "rss"

@dataclass
class PodcastMeta:
    id: str
    label: str
    language: str
    cover_image: Optional[str]
    episodes: List[Episode]
