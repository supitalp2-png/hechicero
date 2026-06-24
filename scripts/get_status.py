#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# get_status.py - Hechicero battery monitor (writes web/status.json)
import json
import time
import logging
import os
import tempfile
from pathlib import Path

# Local INA219 driver (assumed in same folder)
from INA219 import INA219

# Paths
BASE = Path.home() / "hechicero"
DATA_DIR = BASE / "data"
WEB_DIR = BASE / "web"
CFG_PATH = DATA_DIR / "config.json"
STATUS_PATH = WEB_DIR / "status.json"
SHUT_FLAG = DATA_DIR / "shutdown_pending"

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Load config (fail-safe defaults)
def load_config():
    try:
        with open(CFG_PATH, "r") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    # defaults
    cfg.setdefault("battery_check_interval_seconds", 60)
    cfg.setdefault("charge_threshold_ma", 50)
    cfg.setdefault("warn_threshold_percent", 20)
    cfg.setdefault("shutdown_threshold_percent", 8)
    cfg.setdefault("grace_seconds_before_shutdown", 60)
    return cfg

cfg = load_config()

# INA219 instance (address may be 0x43 or 0x40 depending on wiring)
INA_ADDR = cfg.get("ina219_addr", 0x43)
try:
    ina = INA219(addr=INA_ADDR)
except Exception as e:
    logging.exception("Failed to init INA219 at addr %s", hex(INA_ADDR))
    ina = None

def atomic_write(path: Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(data)
        os.chmod(tmp, 0o644)   # lisible par www-data
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise

def read_sensor():
    if ina is None:
        raise RuntimeError("INA219 not initialized")
    v = ina.getBusVoltage_V()
    i_ma = -ina.getCurrent_mA()
    p_w = ina.getPower_W()
    return float(v), float(i_ma), float(p_w)

def percent_from_voltage(v):
    # linear mapping 3.0V -> 0%, 4.2V -> 100%
    pct = int((v - 3.0) / 1.2 * 100)
    return max(0, min(100, pct))

def build_status():
    v, i_ma, p_w = read_sensor()
    pct = percent_from_voltage(v)
    state = "En charge ⚡" if i_ma > cfg["charge_threshold_ma"] else "Sur batterie 🔋"
    alert = None
    if pct <= cfg["shutdown_threshold_percent"]:
        alert = "CRITIQUE: seuil d'arrêt imminent"
    elif pct <= cfg["warn_threshold_percent"]:
        alert = "Alerte: batterie faible"
    return {
        "percent": pct,
        "voltage_v": round(v, 3),
        "current_ma": int(i_ma),
        "power_w": round(p_w, 3),
        "state": state,
        "alert": alert,
        "ts": int(time.time())
    }

def handle_shutdown_logic(status):
    # mark pending shutdown but do NOT poweroff automatically
    if status["percent"] <= cfg["shutdown_threshold_percent"]:
        if not SHUT_FLAG.exists():
            atomic_write(SHUT_FLAG, str(int(time.time())))
            logging.warning("Shutdown pending flagged at %s", SHUT_FLAG)
        else:
            try:
                t0 = int(SHUT_FLAG.read_text().strip())
            except Exception:
                t0 = int(time.time())
            if int(time.time()) - t0 >= cfg["grace_seconds_before_shutdown"]:
                # annotate status to recommend manual action
                status["alert"] = "CRITIQUE: shutdown recommandé (action manuelle requise)"
                status["shutdown_recommended"] = True
                logging.warning("Battery critical: shutdown recommended")
    else:
        if SHUT_FLAG.exists():
            try:
                SHUT_FLAG.unlink()
            except Exception:
                pass

def main_loop():
    backoff = 1
    while True:
        try:
            status = build_status()
            handle_shutdown_logic(status)
            atomic_write(STATUS_PATH, json.dumps(status, ensure_ascii=False))
            backoff = 1
        except Exception as e:
            logging.exception("Error reading sensor or writing status")
            err = {"percent": None, "state": "Erreur", "alert": "Erreur lecture capteur", "ts": int(time.time())}
            try:
                atomic_write(STATUS_PATH, json.dumps(err, ensure_ascii=False))
            except Exception:
                logging.exception("Failed to write error status")
            time.sleep(backoff)
            backoff = min(300, backoff * 2)
        time.sleep(cfg.get("battery_check_interval_seconds", 60))

if __name__ == "__main__":
    main_loop()
