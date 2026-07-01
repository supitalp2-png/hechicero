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