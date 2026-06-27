import hashlib
import logging
import os
from pathlib import Path
import tempfile
import json

BASE_DIR = Path(__file__).resolve().parents[2]
_preferred_log = BASE_DIR / "logs" / "rss_ingest.log"

# Essaie le dossier projet, retombe sur /tmp si l'utilisateur courant
# (www-data quand lancé depuis l'IHM) n'a pas accès en écriture.
try:
    _preferred_log.parent.mkdir(parents=True, exist_ok=True)
    _preferred_log.touch(exist_ok=True)
    LOG_PATH = _preferred_log
except PermissionError:
    LOG_PATH = Path(tempfile.gettempdir()) / "hechicero_rss_ingest.log"

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log(msg):
    logging.info(msg)
    print(msg)

def md5sum(path: Path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_write_json(path: Path, data: dict):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)
