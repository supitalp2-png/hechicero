import requests
from pathlib import Path
from utils import log, md5sum
import time

CHUNK_SIZE = 256 * 1024  # 256 KB — évite de charger l'entier MP3 en RAM

def download_file(url: str, dest: Path) -> Path | None:
    if dest.exists():
        log(f"Already exists: {dest}")
        return dest

    log(f"Downloading: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")

    for attempt in range(3):
        try:
            with requests.get(url, timeout=30, stream=True) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        f.write(chunk)
            tmp.rename(dest)  # écriture atomique
            log(f"Downloaded: {dest}")
            return dest
        except Exception as e:
            log(f"Error downloading {url} (attempt {attempt + 1}/3): {e}")
            if tmp.exists():
                tmp.unlink()
            time.sleep(2 ** attempt)  # back-off exponentiel

    log(f"Failed to download: {url}")
    return None

def download_episode(podcast_id: str, ep):
    base = Path(f"/home/thomas/hechicero/podcasts/{podcast_id}")

    audio_path = base / "audio" / f"{ep.id}.mp3"
    image_path = base / "images" / f"{ep.id}.jpg"

    if ep.audio_url:
        downloaded = download_file(ep.audio_url, audio_path)
        if downloaded:
            ep.local_audio = str(downloaded)

    if ep.image_url:
        downloaded = download_file(ep.image_url, image_path)
        if downloaded:
            ep.local_image = str(downloaded)

    return ep
