import calendar
import feedparser
from models import Episode
from utils import log
from pathlib import Path
from typing import Optional
from email.utils import parsedate_to_datetime
import re

def normalize_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())

# Bug TINA (2026-07-09, generique a tous les podcasts RSS) : items non-episode
# a exclure entierement (ni telecharges, ni affiches) - Thomas ne les veut pas.
# 1) "bande-annonce" (avec/sans tiret ou espace)
# 2) auto-promo Radio France ("Retrouvez tous les episodes sur l'appli Radio
#    France", "Voyagez dans le temps avec Tina, en avant-premiere sur
#    l'application Radio France", etc.) - meme trouve sur des podcasts
#    differents (TINA, La Discomobile), donc phrase generique cote Radio
#    France, pas specifique a un podcast.
_TRAILER_RE = re.compile(r"^bande[\s-]?annonce", re.IGNORECASE)
_PROMO_RE = re.compile(r"appli(?:cation)?\s+radio\s+france", re.IGNORECASE)

def is_filler(title: str) -> bool:
    t = (title or "").strip()
    return bool(_TRAILER_RE.match(t)) or bool(_PROMO_RE.search(t))

# Detection saison + numero d'episode dans la saison (TICKET-104, 2026-07-09,
# demande Thomas : itunes:season en priorite, motif de titre "N/M" en repli —
# PAS d'heuristique par ecart de date, invalidee explicitement pour des
# podcasts a sortie irreguliere comme Bestioles). Motif de titre attendu :
# "Nom de la saison N/M : ..." (ex: "Tina et les boucliers de Mars 3/10 : Le
# complot" -> saison "Tina et les boucliers de Mars", numero 3). Retourne
# (None, None) si rien n'est detectable (ex: Professeur Caillou) — pas de
# separation visuelle cote lecteur, tri par date uniquement (cf. plus bas).
_SEASON_EP_RE = re.compile(r"^(.*\S)\s+(\d+)\s*/\s*\d+\s*:")

def detect_season(entry, title: str) -> tuple[Optional[str], Optional[int]]:
    raw_season = entry.get("itunes_season")
    m = _SEASON_EP_RE.match(title or "")
    ep_num = int(m.group(2)) if m else None
    if raw_season:
        return str(raw_season).strip(), ep_num
    if m:
        return m.group(1).strip(), ep_num
    return None, None

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
    raw_episodes = []  # (sort_key_date, season, ep_num_in_season, Episode)
    for entry in feed.entries:
        if is_filler(entry.title):
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
        season, ep_num_in_season = detect_season(entry, entry.title)

        raw_episodes.append((sort_key, season, ep_num_in_season, Episode(
            id=ep_id,
            title=entry.title,
            audio_url=audio_url,
            local_audio="",
            image_url=image_url,
            local_image=None,
            published=entry.get("published", ""),
            duration=parse_duration(entry.get("itunes_duration")),
            season=season
        )))

    # Ordre chronologique explicite (episode 1 -> dernier), plutot que de se
    # fier a l'ordre du flux RSS : certains flux ne sont pas strictement du
    # plus recent au plus ancien sur toute leur longueur (saisons multiples,
    # republications en lot avec dates incoherentes) - trouve en diagnostiquant
    # TINA (2026-07-09).
    #
    # Tri a deux niveaux plutot qu'un simple tri par date individuelle :
    # 1) grouper par saison, ordonner les groupes par leur date la plus
    #    ancienne (place chaque saison au bon endroit chronologiquement,
    #    tolerant aux quelques dates incoherentes internes a une saison)
    # 2) a l'interieur d'une meme saison, trier par le numero d'episode
    #    extrait du titre (fiable) plutot que par date individuelle — trouve
    #    en diagnostiquant TINA saison "ceinture d'Alexandre le Grand" :
    #    l'episode 2 n'existe que dans une republication en lot avec une date
    #    incoherente (anterieure a l'episode 1), donc un tri par date seule
    #    le place a tort avant l'episode 1. Le numero de titre n'a pas ce
    #    probleme. Repli sur la date individuelle si pas de saison detectee
    #    (ex: Professeur Caillou, Bestioles) — comportement inchange pour eux.
    season_min_date: dict[str, int] = {}
    for sort_key, season, _ep_num, _ep in raw_episodes:
        if season is None:
            continue
        if season not in season_min_date or sort_key < season_min_date[season]:
            season_min_date[season] = sort_key

    def final_sort_key(item):
        sort_key, season, ep_num, _ep = item
        group_key = season_min_date[season] if season is not None else sort_key
        secondary_key = ep_num if (season is not None and ep_num is not None) else sort_key
        return (group_key, secondary_key)

    raw_episodes.sort(key=final_sort_key)
    keyed_episodes = [(sort_key, ep) for sort_key, _season, _ep_num, ep in raw_episodes]
    # Retourne aussi l'image du podcast au niveau du <channel> (feed_image) :
    # bug 2026-07-09 (La Discomobile) — ingest.py utilisait episodes[0].image_url
    # comme jaquette du podcast, ce qui marchait par coincidence quand le flux
    # etait newest-first. Depuis le tri chronologique ci-dessus, episodes[0]
    # peut etre un item promotionnel non-episode (ex: "Retrouvez tous les
    # episodes sur l'appli Radio France") dont l'image est un avatar generique
    # Radio France, pas la vraie jaquette de l'emission. L'image de <channel>
    # est la source fiable, independante de l'ordre des episodes.
    return [ep for _, ep in keyed_episodes], feed_image


def _string_sort_key(published: str) -> int:
    """Reparse une date RSS deja stockee en string (Episode.published) en
    timestamp epoch. Utilise par merge_episodes() pour retrier apres fusion,
    car les episodes issus de l'historique local n'ont plus le
    published_parsed structure de feedparser (perdu au passage par
    meta.json)."""
    if not published:
        return 0
    try:
        return int(parsedate_to_datetime(published).timestamp())
    except Exception:
        return 0


def merge_episodes(existing: list[Episode], fresh: list[Episode]) -> list[Episode]:
    """Fusionne les episodes deja telecharges localement (existing, lus dans
    l'ancien meta.json) avec ceux du flux RSS actuel (fresh) — TICKET-107,
    demande explicite de Thomas (2026-07-17) : ne jamais perdre un episode
    deja telecharge meme s'il sort du flux RSS (frequent chez Radio France,
    fenetre glissante — vu sur "Les Odyssees").

    Les entrees fresh l'emportent en cas de meme id (metadonnees a jour,
    fichiers deja sur disque donc pas de re-telechargement par
    download_episode()). Les entrees existing sans correspondance dans fresh
    sont conservees telles quelles, y compris d'occasionnels items
    filtres autrement (bandes-annonces) si deja presents dans un ancien
    meta.json — accepte, pas une priorite de filtrer retroactivement.

    Re-trie le resultat avec la meme logique a deux niveaux (saison puis
    numero de titre, sinon date) que parse_rss(), en reparsant les dates
    string plutot que d'utiliser published_parsed (indisponible pour les
    episodes existing)."""
    fresh_ids = {ep.id for ep in fresh}
    kept_old = [ep for ep in existing if ep.id not in fresh_ids]
    combined = kept_old + fresh

    items = []
    for ep in combined:
        sort_key = _string_sort_key(ep.published)
        m = _SEASON_EP_RE.match(ep.title or "")
        ep_num = int(m.group(2)) if m else None
        items.append((sort_key, ep.season, ep_num, ep))

    season_min_date: dict[str, int] = {}
    for sort_key, season, _ep_num, _ep in items:
        if season is None:
            continue
        if season not in season_min_date or sort_key < season_min_date[season]:
            season_min_date[season] = sort_key

    def final_sort_key(item):
        sort_key, season, ep_num, _ep = item
        group_key = season_min_date[season] if season is not None else sort_key
        secondary_key = ep_num if (season is not None and ep_num is not None) else sort_key
        return (group_key, secondary_key)

    items.sort(key=final_sort_key)
    return [ep for _, _, _, ep in items]
