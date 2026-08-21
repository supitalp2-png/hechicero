from __future__ import annotations

import json
import os
import socket
import stat
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "battery_check_interval_seconds": 60,
    # TICKET-133 : bande morte (±mA) autour de zéro. Le SIGNE du courant décide
    # de la charge ou de la décharge ; cette bande n'absorbe que le bruit de
    # l'INA219 autour de zéro. Remplace `charge_threshold_ma`, un seuil unique
    # qui classait « décharge » des courants positifs jusqu'à +300 mA.
    # 200 mA, valeur retenue le 2026-08-18 sur mesures : en maintien de charge
    # le courant oscille entre ~+1000 mA et **−122 mA**, donc il traverse zéro.
    # Une bande de 10 mA laissait chaque creux basculer en « décharge » et
    # fabriquait des micro-cycles. 200 mA les absorbe tout en restant 3 à 15 fois
    # sous une décharge réelle (600-800 mA au repos, 1600-3400 mA en lecture) :
    # le watchdog continue de voir toute vraie décharge.
    "charge_deadband_ma": 200,
    # ⚠️ Conservé pour ne pas casser un config.json existant qui le contient,
    # mais PLUS UTILISÉ depuis le 2026-08-17. Ne pas s'en servir.
    "charge_threshold_ma": 50,
    "warn_threshold_percent": 20,
    "shutdown_threshold_percent": 8,
    "grace_seconds_before_shutdown": 60,
    "ina219_addr": 0x43,
    # ── TICKET-139 — lisser avant de décider ────────────────────────────────
    # Chaque lecture de l'INA219 était prise pour argent comptant, alors que le
    # signal oscille de −210 à +1459 mA d'un relevé à l'autre. Conséquences
    # mesurées le 2026-08-19 : un creux passager à −210 mA faisait annoncer
    # « charge arrêtée », et 72 mV de variation de tension faisaient sauter le
    # niveau de 61 à 70 % en quatre minutes.
    # On prend donc plusieurs lectures rapprochées et on garde la MÉDIANE — pas
    # la moyenne : une seule valeur aberrante suffit à déplacer une moyenne,
    # alors qu'il en faut la moitié pour déplacer une médiane.
    "sensor_burst_samples": 5,
    "sensor_burst_interval_s": 0.2,
    # ── TICKET-137 — résistance interne, pour la compensation d'affaissement ─
    # Mesurée le 2026-08-21 en cherchant le R qui fait coïncider les courbes de
    # deux décharges profondes indépendantes (cycles 12 et 18) : le désaccord
    # médian tombe de 12,0 mV à 6,4 mV. ⚠️ Le minimum est PLAT entre 20 et
    # 60 mΩ — le courant de décharge varie peu (1540-2170 mA), donc R n'est pas
    # finement déterminé. À prendre comme un ordre de grandeur, pas comme une
    # constante physique. À réévaluer si un cycle à faible courant devient
    # disponible : c'est lui qui donnerait le bras de levier qui manque.
    "internal_resistance_ohm": 0.034,
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


# ── TICKET-137 — table MESURÉE sur les cellules réelles (2026-08-21) ────────
#
# L'ancienne table était une courbe générique d'accumulateur à poche, héritée du
# montage d'origine et jamais recalée. Les cellules sont deux EVE INR21700/58E
# (Li-ion NMC, 5600 mAh chacune). Elle sur-évaluait le niveau de **4 à 8 points**
# sur presque toute la plage — et annonçait encore 7 % à la coupure réelle.
#
# Établie par intégration du courant sur **deux décharges profondes
# indépendantes** (cycles 12 du 2026-08-18 et 18 du 2026-08-19), qui ont délivré
# 8892 et 8896 mAh — à 0,05 % près. Désaccord médian entre les deux courbes :
# **6,4 mV** après compensation d'affaissement.
#
# ⚠️ CES TENSIONS SONT DES TENSIONS À VIDE. Elles ne doivent JAMAIS être
# comparées à une lecture brute de l'INA219 : passer par `tension_a_vide()`.
# Échanger la table sans la compensation rendrait le calcul plus faux qu'avant,
# et c'est la raison pour laquelle les deux ont été livrées ensemble.
#
# ⚠️ ENTRE 75 ET 95 %, LA TENSION NE DISTINGUE PRESQUE RIEN : 20 points de
# pourcentage étalés sur 40 mV, contre 60 mV dans l'ancienne table. C'est le
# plateau de la chimie Li-ion, pas un défaut de mesure — mais cela rend le haut
# de la jauge intrinsèquement imprécis, et **environ sept fois plus sensible au
# bruit** que l'ancienne table. C'est pourquoi le lissage (TICKET-139) est un
# PRÉALABLE et non un confort. Un espacement minimal de 5 mV est imposé entre
# paliers pour ne pas créer de falaise plus fine que le bruit résiduel.
# La vraie réponse à ce plateau serait un comptage coulométrique ; écarté pour
# l'instant (mécanisme neuf, dérive à gérer).
_LIPO_TABLE = [
    (4.146, 100), (4.067, 95), (4.058, 90), (4.036, 85),
    (4.031, 80),  (4.026, 75), (3.992, 70), (3.943, 65),
    (3.901, 60),  (3.859, 55), (3.837, 50), (3.800, 45),
    (3.763, 40),  (3.731, 35), (3.676, 30), (3.639, 25),
    (3.586, 20),  (3.528, 15), (3.502, 10), (3.458,  5),
    (3.392,   0),
]


def mediane(valeurs: list[float]) -> float:
    """Médiane d'une liste non vide.

    TICKET-139. Médiane et pas moyenne : sur un signal qui comporte des valeurs
    aberrantes isolées (un creux de courant à −210 mA au milieu d'une charge à
    +900 mA), **une seule** valeur suffit à déplacer une moyenne, alors qu'il en
    faut la moitié pour déplacer une médiane. C'est précisément ce genre de
    creux isolé qui faisait annoncer « charge arrêtée ».
    """
    if not valeurs:
        raise ValueError("mediane() sur une liste vide")
    ordonnees = sorted(valeurs)
    milieu = len(ordonnees) // 2
    if len(ordonnees) % 2:
        return ordonnees[milieu]
    return (ordonnees[milieu - 1] + ordonnees[milieu]) / 2


def tension_a_vide(voltage_v: float, current_ma: float, resistance_ohm: float) -> float:
    """Tension de la cellule corrigée de sa chute ohmique interne.

    TICKET-137. `_LIPO_TABLE` associe des pourcentages à des tensions **à
    vide**. Or l'INA219 mesure la tension **sous charge**, plus basse de I·R.
    Sans cette correction, le niveau affiché plonge dès qu'un podcast démarre :
    à −2,2 A et R = 34 mΩ, l'affaissement vaut 75 mV, soit environ 8 points de
    pourcentage — alors qu'aucune énergie n'a encore été consommée.

    ⚠️ Le signe compte. En DÉCHARGE (courant négatif) la tension mesurée est
    plus basse que la tension à vide : on ajoute I·R. En CHARGE (courant
    positif) elle est plus HAUTE : on retranche. D'où `- current·R` dans les
    deux cas, le signe du courant faisant le travail. Se tromper de signe
    doublerait l'erreur au lieu de l'annuler.
    """
    if resistance_ohm <= 0:
        return voltage_v
    return voltage_v - (current_ma / 1000.0) * resistance_ohm


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

    # TICKET-139 : rafale de lectures + médiane, au lieu d'un échantillon unique.
    # Une lecture isolée d'un signal qui oscille de ±1400 mA ne décrit rien.
    n = max(1, int(config.get("sensor_burst_samples", 5)))
    pause = float(config.get("sensor_burst_interval_s", 0.2))
    tensions: list[float] = []
    courants: list[float] = []
    puissances: list[float] = []
    for i in range(n):
        tensions.append(float(sensor.getBusVoltage_V()))
        courants.append(float(-sensor.getCurrent_mA()))
        puissances.append(float(sensor.getPower_W()))
        if i < n - 1 and pause > 0:
            time.sleep(pause)

    voltage_v = mediane(tensions)
    current_ma = mediane(courants)
    power_w = mediane(puissances)

    # TICKET-137 : la table donne des tensions À VIDE. Sous charge, la chute
    # ohmique interne (V = V_oc − I·R) fait lire une tension plus basse que
    # l'état réel de la cellule — d'où le niveau qui plonge dès qu'un podcast
    # démarre alors que rien n'a été consommé. On corrige AVANT de convertir.
    r_interne = float(config.get("internal_resistance_ohm", 0.0))
    level = percent_from_voltage(tension_a_vide(voltage_v, current_ma, r_interne))

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