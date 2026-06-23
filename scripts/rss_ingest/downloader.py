import requests
import subprocess
import urllib3
from pathlib import Path
from utils import log
import time

CHUNK_SIZE = 256 * 1024  # 256 KB — évite de charger l'entier MP3 en RAM

# proxycast.radiofrance.fr présente une chaîne SSL incomplète non validée par Python.
# On désactive la vérification uniquement pour ce domaine.
# proxycast.radiofrance.fr présente une chaîne SSL incomplète.
# radio-france-rss.aerion.workers.dev redirige vers ce même hôte,
# donc verify=False doit être activé dès l'URL d'origine pour suivre la redirection.
SSL_NO_VERIFY_HOSTS = {"proxycast.radiofrance.fr", "radio-france-rss.aerion.workers.dev"}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def is_m4a_container(path: Path) -> bool:
    """Détecte si le fichier est un conteneur M4A/MP4 (malgré l'extension .mp3).
    Les fichiers M4A ont le marqueur 'ftyp' à l'offset 4.
    """
    try:
        with open(path, "rb") as f:
            f.seek(4)
            return f.read(4) == b"ftyp"
    except Exception:
        return False


def convert_m4a_to_mp3(src: Path, dest: Path) -> bool:
    """Convertit un fichier M4A/AAC en vrai MP3 via ffmpeg.
    Supprime src en cas de succès.
    """
    tmp = dest.with_suffix(".converting.mp3")
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(src),
                "-vn",                      # ignore la jaquette embarquée
                "-codec:a", "libmp3lame",
                "-q:a", "2",                # VBR ~190 kbps
                str(tmp),
            ],
            capture_output=True,
            timeout=600,
        )
        if result.returncode == 0:
            tmp.rename(dest)
            src.unlink()
            log(f"Converted M4A→MP3: {dest}")
            return True
        else:
            log(f"ffmpeg error for {src}: {result.stderr.decode()[-300:]}")
            if tmp.exists():
                tmp.unlink()
            return False
    except Exception as e:
        log(f"Conversion exception for {src}: {e}")
        if tmp.exists():
            tmp.unlink()
        return False


def download_file(url: str, dest: Path) -> Path | None:
    if dest.exists():
        log(f"Already exists: {dest}")
        return dest

    log(f"Downloading: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")

    from urllib.parse import urlparse
    verify_ssl = urlparse(url).hostname not in SSL_NO_VERIFY_HOSTS

    for attempt in range(3):
        try:
            with requests.get(url, timeout=30, stream=True, verify=verify_ssl) as r:
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
            # Radio France sert parfois du AAC/M4A renommé en .mp3.
            # MPD ne détecte pas le conteneur MP4 via l'extension → durée erronée + bruit.
            # On convertit en vrai MP3 si nécessaire.
            if is_m4a_container(downloaded):
                log(f"M4A container detected in {downloaded.name}, converting…")
                raw = downloaded.with_suffix(".m4a.raw")
                downloaded.rename(raw)
                if not convert_m4a_to_mp3(raw, downloaded):
                    # Échec de conversion : on remet l'original pour ne pas perdre le fichier
                    raw.rename(downloaded)
                    log(f"Kept original (conversion failed): {downloaded}")
            ep.local_audio = str(downloaded)

    if ep.image_url:
        downloaded = download_file(ep.image_url, image_path)
        if downloaded:
            ep.local_image = str(downloaded)

    return ep
