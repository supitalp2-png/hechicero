from __future__ import annotations

import json
import os
import socket
import stat
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "battery_check_interval_seconds": 60,
    # TICKET-133 : bande morte (±mA) autour de zéro. Le SIGNE du courant décide
    # de la charge ou de la décharge ; cette bande n'absorbe que le bruit de
    # l'INA219 autour de zéro. Remplace `charge_threshold_ma`, un seuil unique
    # qui classait « décharge » des courants positifs jusqu'à +300 mA.
    "charge_deadband_ma": 10,
    # ⚠️ Conservé pour ne pas casser un config.json existant qui le contient,
    # mais PLUS UTILISÉ depuis le 2026-08-17. Ne pas s'en servir.
    "charge_threshold_ma": 50,
    "warn_threshold_percent": 20,
    "shutdown_threshold_percent": 8,
    "grace_seconds_before_shutdown": 60,
    "ina219_addr": 0x43,
}


def resolve_project_root() -> Path:
    script_root = Path(__file__).resolve().parents[1]
    preferred = Path("/home/thomas/hechicero")
    if preferred.exists():
        return preferred
    return script_root


PROJECT_ROOT = resolve_project_root()
DATA_DIR = PROJECT_ROOT / "data"
WEB_DIR = PROJECT_ROOT / "web"
CONFIG_PATH = DATA_DIR / "config.json"


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def atomic_write_text(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
        os.replace(tmp_path, path)
        try:
            os.chmod(
                path,
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH,
            )
        except Exception:
            pass
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, data: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
    )


def load_config() -> dict[str, Any]:
    config = load_json(CONFIG_PATH, {})
    merged = DEFAULT_CONFIG.copy()
    if isinstance(config, dict):
        merged.update(config)
    return merged


# Table de décharge LiPo 1S standard (courbe réelle, vs linéaire 3.0–4.2V)
# La formule linéaire surestimait le niveau (~+20 pts autour de 3.7V).
# Source : courbe typique LiPo polymère / Li-Ion 18650, 25°C, décharge lente.
_LIPO_TABLE = [
    (4.20, 100), (4.15, 95), (4.11, 90), (4.08, 85),
    (4.02, 80),  (3.98, 75), (3.95, 70), (3.91, 65),
    (3.87, 60),  (3.83, 55), (3.79, 50), (3.75, 45),
    (3.71, 40),  (3.67, 35), (3.63, 30), (3.59, 25),
    (3.55, 20),  (3.49, 15), (3.44, 10), (3.35,  5),
    (3.00,   0),
]


def percent_from_voltage(voltage_v: float) -> int:
    """Convertit la tension LiPo 1S en pourcentage de capacité (courbe non-linéaire)."""
    if voltage_v >= _LIPO_TABLE[0][0]:
        return 100
    if voltage_v <= _LIPO_TABLE[-1][0]:
        return 0
    for i in range(len(_LIPO_TABLE) - 1):
        v_hi, pct_hi = _LIPO_TABLE[i]
        v_lo, pct_lo = _LIPO_TABLE[i + 1]
        if v_lo <= voltage_v <= v_hi:
            t = (voltage_v - v_lo) / (v_hi - v_lo)
            return max(0, min(100, int(round(pct_lo + t * (pct_hi - pct_lo)))))
    return 0


def init_ina219(addr: int) -> Any | None:
    try:
        from INA219 import INA219  # type: ignore
    except Exception:
        return None

    try:
        return INA219(addr=addr)
    except Exception:
        return None


def detecter_charge(current_ma: float, deadband_ma: float, precedent: bool | None) -> bool:
    """Charge ou décharge ? Signe du courant, avec une bande morte à hystérésis.

    ── POURQUOI CETTE FONCTION EXISTE (TICKET-133, 2026-08-17) ────────────────
    L'ancienne règle tenait en une ligne, et elle était fausse :

        charging = current_ma > charge_threshold_ma      # seuil unique à 300 mA

    Un seuil UNIQUE n'a pas de zone morte : tout ce qui est en dessous est
    déclaré « décharge », **y compris un courant positif**. Mesuré le
    2026-08-17, appareil sur secteur et cellule presque pleine (phase CV) :

        15:25  current_ma = +257,71  ->  classé « décharge »   (257 < 300)
        15:26  current_ma =  +17,83  ->  classé « décharge »   (17  < 300)
        15:47  current_ma = +683,67  ->  classé « charge »     (683 > 300)

    Les trois courants sont POSITIFS — le courant entre dans la batterie dans
    les trois cas. La classification basculait au gré des oscillations du
    chargeur, fabriquant de faux cycles de décharge pendant lesquels le niveau
    *montait* (84 % -> 86 %, 82 % -> 86 %, 85 % -> 88 %). C'est le bug de
    juillet 2026 qui revenait.

    ── LA RÈGLE, DEMANDÉE PAR THOMAS ─────────────────────────────────────────
    Le signe du courant décide, avec une bande morte de ±deadband_ma :
        courant > +bande   -> charge
        courant < -bande   -> décharge
        entre les deux     -> on GARDE l'état précédent (hystérésis)

    C'est physiquement juste : le signe dit dans quel sens l'énergie circule.
    La bande morte n'est là que pour absorber le bruit de mesure de l'INA219
    autour de zéro, pas pour arbitrer entre charge et décharge.

    ⚠️ `precedent=None` (premier échantillon, ou capteur qui vient d'être
    réinitialisé) et courant dans la bande morte -> on répond **charge**.
    Ce n'est pas arbitraire : `battery_watchdog` se sert de ce booléen pour
    décider d'éteindre le Pi. Un courant quasi nul signifie que la batterie ne
    se vide pratiquement pas ; répondre « décharge » risquerait un arrêt
    injustifié, répondre « charge » ne fait que différer un arrêt qui n'est de
    toute façon pas urgent. En cas de doute, on ne coupe pas le courant à un
    appareil qu'un enfant est peut-être en train d'écouter.
    """
    if current_ma > deadband_ma:
        return True
    if current_ma < -deadband_ma:
        return False
    return True if precedent is None else precedent


def read_sensor_snapshot(
    sensor: Any,
    config: dict[str, Any],
    previous_charging: bool | None = None,
) -> dict[str, Any]:
    """Lecture instantanée du capteur.

    `previous_charging` : état de charge du relevé précédent, nécessaire à
    l'hystérésis de detecter_charge(). Les appelants qui bouclent (tracker,
    watchdog) DOIVENT le transmettre — sans lui, l'hystérésis n'existe pas et
    on retombe sur le comportement à seuil unique.
    """
    if sensor is None:
        raise RuntimeError("INA219 unavailable")

    voltage_v = float(sensor.getBusVoltage_V())
    current_ma = float(-sensor.getCurrent_mA())
    power_w = float(sensor.getPower_W())
    level = percent_from_voltage(voltage_v)

    # `charge_threshold_ma` (ancien seuil unique) n'est plus utilisé. Il reste
    # toléré dans config.json sans effet — voir DEFAULT_CONFIG et TICKET-133.
    deadband = float(config.get("charge_deadband_ma", 10))
    charging = detecter_charge(current_ma, deadband, previous_charging)

    return {
        "level": level,
        "voltage_v": round(voltage_v, 3),
        "current_ma": round(current_ma, 2),
        "power_w": round(power_w, 3),
        "charging": charging,
        "status": "charging" if charging else "discharging",
    }


def run_command(command: list[str], timeout: float = 2.0) -> str:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        return ""
    return (completed.stdout or "").strip()


def read_mpd_status() -> dict[str, Any]:
    state = "stopped"
    current = ""
    elapsed = 0.0

    if os.name != "nt":
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            sock.connect("/run/mpd/socket")
            sock.recv(1024)
            sock.sendall(b"status\n")
            status_lines = sock.recv(4096).decode("utf-8", errors="ignore").splitlines()
            sock.sendall(b"currentsong\n")
            song_lines = sock.recv(4096).decode("utf-8", errors="ignore").splitlines()
            sock.sendall(b"close\n")
            sock.close()
            for line in status_lines:
                if line.startswith("state: "):
                    state = line.split(": ", 1)[1].strip()
                elif line.startswith("elapsed: "):
                    try:
                        elapsed = float(line.split(": ", 1)[1].strip())
                    except ValueError:
                        elapsed = 0.0
            for line in song_lines:
                if line.startswith("file: "):
                    current = line.split(": ", 1)[1].strip()
                    break
        except Exception:
            pass

    if not current:
        current = run_command(["mpc", "current", "--format", "%file%"])
    if state == "stopped":
        status_output = run_command(["mpc", "status"])
        lowered = status_output.lower()
        if "[playing]" in lowered:
            state = "playing"
        elif "[paused]" in lowered:
            state = "paused"
        elif lowered.strip():
            state = "stopped"

        for line in status_output.splitlines():
            if "/" in line and ":" in line:
                segment = line.split()[0]
                try:
                    elapsed_str = segment.split("/", 1)[0]
                    parts = [int(value) for value in elapsed_str.split(":")]
                    if len(parts) == 2:
                        elapsed = parts[0] * 60 + parts[1]
                    elif len(parts) == 3:
                        elapsed = parts[0] * 3600 + parts[1] * 60 + parts[2]
                except Exception:
                    elapsed = 0.0
                break

    mode = "idle"
    if current.startswith(("http://", "https://")):
        mode = "webradio"
    elif current:
        mode = "podcast"
    elif state in {"playing", "paused"}:
        mode = "idle"

    return {
        "state": state,
        "current": current,
        "mode": mode,
        "elapsed": elapsed,
    }


def read_screen_on() -> bool:
    output = run_command(["vcgencmd", "display_power"])
    if "display_power=" in output:
        return output.strip().endswith("=1")

    backlight_root = Path("/sys/class/backlight")
    if backlight_root.exists():
        for child in backlight_root.iterdir():
            brightness = child / "brightness"
            if not brightness.exists():
                continue
            try:
                return int(brightness.read_text(encoding="utf-8").strip()) > 0
            except Exception:
                continue
    return True