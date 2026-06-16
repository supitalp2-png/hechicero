import hashlib
import logging
import os
from pathlib import Path
import tempfile
import json

LOG_PATH = "/var/log/hechicero/rss_ingest.log"

logging.basicConfig(
    filename=LOG_PATH,
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
