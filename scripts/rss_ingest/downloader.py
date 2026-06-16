import requests
from pathlib import Path
from utils import log, md5sum
import time

def download_file(url: str, dest: Path):
    if dest.exists():
        log(f"Already exists: {dest}")
        return dest

    log(f"Downloading: {url}")
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(r.content)
                log(f"Downloaded: {dest}")
                return dest
        except Exception as e:
            log(f"Error downloading {url}: {e}")
            time.sleep(2)

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
