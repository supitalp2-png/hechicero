import re
import time
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from models import Episode
from parser import normalize_id
from utils import log

USER_AGENT = "Mozilla/5.0 (compatible; HechiceroIngest/1.0)"
REQUEST_TIMEOUT = 20
REQUEST_DELAY_SECONDS = 0.5

MESES = {
    "enero": "Jan",
    "febrero": "Feb",
    "marzo": "Mar",
    "abril": "Apr",
    "mayo": "May",
    "junio": "Jun",
    "julio": "Jul",
    "agosto": "Aug",
    "septiembre": "Sep",
    "octubre": "Oct",
    "noviembre": "Nov",
    "diciembre": "Dec",
}


def _fetch_page(url: str) -> tuple[str, BeautifulSoup]:
    """Retourne (html_brut, soup)."""
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)
    html = response.text
    return html, BeautifulSoup(html, "html.parser")


def _extract_meta(soup: BeautifulSoup, property_name: str) -> str:
    tag = soup.find("meta", attrs={"property": property_name})
    if tag and tag.get("content"):
        return tag.get("content").strip()
    return ""


def _extract_published_rfc2822(soup: BeautifulSoup) -> str:
    page_text = soup.get_text(" ", strip=True)
    match = re.search(
        r"\b(\d{1,2})\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+),\s*(\d{4})\b",
        page_text,
    )
    if not match:
        return ""

    day = int(match.group(1))
    month_es = match.group(2).strip().lower()
    year = int(match.group(3))
    month_en = MESES.get(month_es)
    if not month_en:
        return ""

    try:
        dt = datetime.strptime(f"{day:02d} {month_en} {year}", "%d %b %Y").replace(
            tzinfo=timezone.utc
        )
        return format_datetime(dt, usegmt=True)
    except ValueError:
        return ""


def _extract_audio_url(html: str) -> str:
    """Cherche l'URL MP3 dans le HTML brut (indépendant du widget audio Drupal)."""
    match = re.search(
        r'https://radionacional-v3\.s3\.amazonaws\.com/[^\s"\'<>&]+\.mp3',
        html,
    )
    return match.group(0) if match else ""


def _extract_episode_links(soup: BeautifulSoup, listing_url: str) -> list[str]:
    links = []
    seen = set()
    base_domain = "www.radionacional.co"

    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if not href:
            continue

        # Rejeter immédiatement les liens non-HTTP et les partages sociaux
        if href.startswith(("mailto:", "whatsapp:", "tel:")):
            continue

        absolute = urljoin(listing_url, href)
        parsed = urlparse(absolute)

        # Doit être sur radionacional.co uniquement
        if parsed.netloc != base_domain:
            continue

        # Le chemin doit matcher exactement /podcast/profe-en-tu-casa/SLUG
        if not re.match(r"^/podcast/profe-en-tu-casa/[^/]+$", parsed.path):
            continue

        # Pas de query string (évite les pages de pagination)
        if parsed.query:
            continue

        canonical = f"https://{base_domain}{parsed.path}"
        if canonical not in seen:
            seen.add(canonical)
            links.append(canonical)

    return links


def scrape_radionacional(podcast_config) -> list[Episode]:
    log(f"Scraping Radio Nacional: {podcast_config.rss}")

    episodes: list[Episode] = []
    seen_urls: set[str] = set()  # déduplication globale entre toutes les pages
    page = 0

    while len(episodes) < podcast_config.max_episodes:
        listing_url = f"{podcast_config.rss}?page={page}"
        log(f"Scraping listing page {page}: {listing_url}")

        try:
            _, listing_soup = _fetch_page(listing_url)
        except Exception as exc:
            log(f"Erreur listing {listing_url}: {exc}")
            break

        episode_links = _extract_episode_links(listing_soup, podcast_config.rss)
        if not episode_links:
            break

        # Filtrer les URLs déjà vues dans les pages précédentes
        new_links = [url for url in episode_links if url not in seen_urls]
        seen_urls.update(episode_links)
        if not new_links:
            log(f"Page {page}: aucun nouvel épisode, arrêt.")
            break

        for episode_url in new_links:
            if len(episodes) >= podcast_config.max_episodes:
                break

            try:
                episode_html, episode_soup = _fetch_page(episode_url)
            except Exception as exc:
                log(f"Erreur episode {episode_url}: {exc}")
                continue

            title = _extract_meta(episode_soup, "og:title")
            if not title:
                h1 = episode_soup.find("h1")
                title = h1.get_text(strip=True) if h1 else episode_url

            # Les photos stock par épisode sont variées mais sans intérêt.
            # On utilise la cover officielle de la série pour tous les épisodes.
            image_url = "https://radionacional-v3.s3.amazonaws.com/s3fs-public/node/serie/field_image/PORTADAS-WEB-PROFE.jpg"
            published = _extract_published_rfc2822(episode_soup)
            audio_url = _extract_audio_url(episode_html)

            episodes.append(
                Episode(
                    id=normalize_id(title),
                    title=title,
                    audio_url=audio_url,
                    local_audio="",
                    image_url=image_url,
                    local_image=None,
                    published=published,
                    duration=None,
                )
            )

        page += 1

    return episodes
