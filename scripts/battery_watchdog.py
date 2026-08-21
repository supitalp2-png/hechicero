#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import time
from typing import Any

from battery_common import (
    DATA_DIR,
    atomic_write_json,
    init_ina219,
    load_config,
    now_iso,
    read_mpd_status,
    read_sensor_snapshot,
    run_command,
)


LAST_SESSION_PATH = DATA_DIR / "last_session.json"
DEFAULT_CRITICAL_LEVEL = 7
DEFAULT_POLL_SECONDS = 30


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("battery_watchdog")


class GpioSignalMonitor:
    def __init__(self, pin: int | None):
        self.pin = pin
        self.gpio = None
        if pin is None:
            return
        try:
            import RPi.GPIO as GPIO  # type: ignore
        except Exception:
            return
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.gpio = GPIO

    def triggered(self) -> bool:
        if self.pin is None or self.gpio is None:
            return False
        try:
            return self.gpio.input(self.pin) == 0
        except Exception:
            return False

    def close(self) -> None:
        if self.gpio is not None:
            try:
                self.gpio.cleanup(self.pin)
            except Exception:
                pass


def capture_last_session(battery_level: int | None, simulate: bool = False) -> dict[str, Any]:
    # ⚠️ TICKET-121 (2026-08-17) — un test ne doit jamais laisser de fausse
    # trace. `web/index.php::battery_resume_payload()` n'agit que si
    # `shutdown_reason === 'battery_critical'` : un `--simulate-critical`
    # écrivant ce motif faisait afficher au bureau d'admin une « reprise après
    # coupure batterie » qui n'avait jamais eu lieu. On écrit donc bien le
    # fichier (c'est ce que le test doit prouver), mais avec un motif que
    # l'admin ignore.
    mpd = read_mpd_status()
    payload = {
        "shutdown_reason": "simulation" if simulate else "battery_critical",
        "shutdown_at": now_iso(),
        "battery_level": battery_level,
        "mpd_file": mpd.get("current") or None,
        "mpd_elapsed": round(float(mpd.get("elapsed") or 0), 1),
    }
    atomic_write_json(LAST_SESSION_PATH, payload)
    return payload


# ── Redémarrage automatique à la remise sous tension (TICKET-128) ─────────
#
# ⚠️ CE BLOC A AFFIRMÉ LE CONTRAIRE DE LA VÉRITÉ PENDANT QUATRE JOURS.
# Il décrivait l'écriture ci-dessous comme une « coupure matérielle » qui
# aurait demandé au HAT d'éteindre sa sortie. La documentation du fabricant
# est pourtant explicite, et le titre de sa section suffit : **« Boot When
# Power Applied »**.
#
#   « After changing the value of the 0x01 register to 0x55, the MCU will
#     start detecting the charging port after 30 seconds, and if power is
#     available then pull the GPIO3 pin low to BOOT the Raspberry Pi. »
#
# Écrire 0x55 dans 0x2d/0x01 arme donc le **démarrage automatique quand
# l'alimentation revient**. C'est l'inverse d'une coupure. La fonction, son
# nom, son message de journal et le ticket disaient tous faux — et le journal
# le répétait à chaque arrêt d'urgence.
#
# 💡 D'où venait l'erreur : le code a été déduit de la démo du fabricant en bas
# de `scripts/INA219.py`, qui écrit ce registre juste avant `poweroff`. La
# séquence *ressemble* à un armement de coupure. **Lire un comportement dans
# l'ordre des appels au lieu de la documentation produit une explication
# cohérente et fausse** — et rien ne vient jamais la contredire, puisque le
# code « marche ».
#
# ── CE QUE ÇA APPORTE RÉELLEMENT, ET QUI EST UTILE ────────────────────────
# Après un arrêt sur batterie critique, la radio **redémarre seule** dès que
# papa rebranche le chargeur. Sans ce registre, elle resterait éteinte jusqu'à
# une intervention. Pour un appareil que l'enfant utilise seul, c'est précieux.
# On garde donc l'écriture — on corrige seulement ce qu'on en dit.
#
# ⚠️ Note du fabricant : « The Raspberry Pi needs to be turned off immediately
# after setting 0x01 to 0x55, otherwise the start when power applied function
# cannot be enabled. » L'ordre écriture → `shutdown` est donc bien impératif,
# mais pour cette raison-là, pas pour éviter une coupure en pleine écriture.
#
# 🔴 CE QUI RESTE NON RÉSOLU : rien ici ne protège les cellules d'une décharge
# profonde après l'arrêt de l'OS. Le HAT continue de fournir du 5 V à un Pi
# « halted ». La seule vraie barrière est la protection intégrée des cellules.
# Décision de Thomas (2026-08-18) : on s'en remet à elle, l'interrupteur
# physique n'étant pas accessible.
HAT_I2C_BUS = 1
HAT_I2C_ADDR = "0x2d"
HAT_BOOT_REG = "0x01"
HAT_BOOT_VALUE = "0x55"


def hat_present() -> bool:
    """Le MCU du HAT (0x2d) répond-il sur le bus I2C ?

    On ne tente JAMAIS l'écriture sans cette vérification : écrire à
    l'aveugle sur une adresse I2C qui n'est pas celle qu'on croit peut
    reconfigurer un tout autre composant. Reproduit la vérification de la
    démo du fabricant.
    """
    out = run_command(
        ["i2cdetect", "-y", "-r", str(HAT_I2C_BUS), HAT_I2C_ADDR, HAT_I2C_ADDR],
        timeout=5,
    )
    # La sortie est un tableau ; on cherche la cellule "2d" (et non "--").
    return "2d" in out.split()


def armer_demarrage_a_la_remise_sous_tension() -> bool:
    """Arme le redémarrage automatique du Pi quand l'alimentation revient.

    ⚠️ Cette fonction s'appelait `arm_hat_power_cutoff()` et prétendait couper
    la sortie du HAT. Elle n'a jamais rien coupé : voir le bloc ci-dessus.

    N'est jamais fatale : si le HAT est absent ou l'écriture échoue, on
    journalise et `shutdown` fait son travail. Seul le redémarrage automatique
    est perdu.
    """
    if not hat_present():
        LOGGER.warning(
            "HAT introuvable à l'adresse %s — redémarrage automatique au "
            "rebranchement NON armé ; l'arrêt se fera normalement, mais il "
            "faudra rallumer la radio à la main", HAT_I2C_ADDR,
        )
        return False
    try:
        completed = subprocess.run(
            ["i2cset", "-y", str(HAT_I2C_BUS), HAT_I2C_ADDR, HAT_BOOT_REG, HAT_BOOT_VALUE],
            capture_output=True, text=True, timeout=5, check=False,
        )
        if completed.returncode != 0:
            LOGGER.error(
                "écriture i2cset échouée (code %s) — stderr=%r",
                completed.returncode, (completed.stderr or "").strip(),
            )
            return False
        LOGGER.info(
            "redémarrage au rebranchement armé (%s reg %s <- %s) — la radio "
            "repartira seule dès que le chargeur sera rebranché",
            HAT_I2C_ADDR, HAT_BOOT_REG, HAT_BOOT_VALUE,
        )
        return True
    except Exception:
        LOGGER.exception("écriture i2cset échouée — exception")
        return False


def perform_shutdown_sequence(battery_level: int | None, simulate: bool = False) -> dict[str, Any]:
    payload = capture_last_session(battery_level, simulate=simulate)
    run_command(["mpc", "stop"])
    if os.name != "nt":
        run_command(["sync"], timeout=10)
    if simulate:
        # On va jusqu'à la DÉTECTION du HAT, jamais jusqu'à l'écriture : c'est
        # ce qui rend ce mode réellement utile pour valider le chemin d'arrêt
        # sans risquer une coupure.
        detecte = hat_present() if os.name != "nt" else False
        print(f"shutdown simulé — HAT 0x2d détecté : {detecte}")
        print("   (aucune écriture i2cset, aucun arrêt : mode simulation)")
        return payload
    if os.name != "nt":
        # `sync` a déjà eu lieu juste au-dessus. L'écriture doit précéder
        # immédiatement l'arrêt : le fabricant précise que sans cela, le
        # redémarrage au rebranchement ne s'arme pas.
        armer_demarrage_a_la_remise_sous_tension()
        # ⚠️ TICKET-121 (2026-08-17) — PAS de `sudo` ici.
        # Ce service tourne déjà en `User=root`, donc `sudo` n'apporte rien —
        # et surtout son unité porte `NoNewPrivileges=true`, qui **casse
        # sudo** (même piège que le réveil DPMS de TICKET-112, qui a dû
        # passer par `runuser`). L'appel échouait donc, et en silence :
        # `run_command()` avale l'exception ET le code de retour, il ne
        # renvoie que stdout. Résultat : la protection contre la décharge
        # profonde ne s'est jamais exécutée depuis le durcissement de
        # juillet 2026, sans laisser la moindre trace.
        #
        # On appelle donc `shutdown` directement, et on **journalise le
        # résultat** : un arrêt d'urgence qui échoue sans bruit est pire que
        # pas d'arrêt du tout, puisqu'on croit être protégé.
        try:
            completed = subprocess.run(
                ["shutdown", "-h", "now"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if completed.returncode != 0:
                LOGGER.error(
                    "SHUTDOWN ÉCHOUÉ (code %s) — stdout=%r stderr=%r",
                    completed.returncode,
                    (completed.stdout or "").strip(),
                    (completed.stderr or "").strip(),
                )
            else:
                LOGGER.warning("Arrêt demandé au système (niveau %s%%)", battery_level)
        except Exception:
            LOGGER.exception("SHUTDOWN ÉCHOUÉ — exception pendant l'appel")
    else:
        LOGGER.warning("Shutdown skipped: unsupported OS")
    return payload


def read_level(sensor: Any, config: dict[str, Any], previous_charging: bool | None = None) -> tuple[int | None, bool, Any]:
    """
    Lit le niveau batterie. Retourne (level, charging, sensor).
    En cas d'errno 121 (INA219 I2C timeout), tente une ré-initialisation et retourne (None, False, nouveau_sensor).
    Toute autre exception retourne (None, False, sensor) sans planter le watchdog.

    ⚠️ TICKET-133 : `previous_charging` alimente l'hystérésis de la bande morte.
    Sans lui, un courant quasi nul serait tranché arbitrairement à chaque
    relevé — et ce booléen décide de l'extinction du Pi. La boucle principale
    le transmet d'un tour à l'autre.

    ⚠️ En cas d'ERREUR de lecture, on renvoie `charging=False`, comme avant.
    C'est volontairement conservateur du point de vue de la mesure — mais sans
    conséquence sur l'arrêt, car `level` vaut alors `None` et la boucle ne
    déclenche rien tant qu'elle n'a pas un niveau valide.
    """
    try:
        snapshot = read_sensor_snapshot(sensor, config, previous_charging=previous_charging)
        return int(snapshot["level"]), bool(snapshot["charging"]), sensor
    except OSError as e:
        if e.errno == 121:
            LOGGER.warning("INA219 errno 121 — tentative de ré-initialisation")
            try:
                sensor = init_ina219(int(config.get("ina219_addr", 0x43)))
            except Exception:
                LOGGER.exception("Ré-initialisation INA219 échouée")
        else:
            LOGGER.warning("Erreur lecture INA219 : %s", e)
        return None, False, sensor
    except Exception as e:
        LOGGER.warning("Erreur lecture INA219 : %s", e)
        return None, False, sensor


def main() -> int:
    parser = argparse.ArgumentParser(description="Hechicero battery watchdog")
    parser.add_argument("--simulate-critical", action="store_true", help="Simule un arrêt critique sans exécuter le shutdown")
    # TICKET-128 : vérifier la présence du MCU sans RIEN écrire. Contrôle à
    # risque nul, lançable pendant que l'enfant écoute.
    parser.add_argument("--check-hat", action="store_true", help="Vérifie que le MCU du HAT (0x2d) répond (aucune écriture)")
    args = parser.parse_args()

    if args.check_hat:
        present = hat_present()
        print(f"MCU du HAT 0x2d détecté : {present}")
        if not present:
            print("  → redémarrage automatique au rebranchement indisponible ;")
            print("     l'arrêt d'urgence fonctionnera, mais il faudra rallumer à la main")
            print("  → i2c-tools installé ? bus 1 actif ? (i2cdetect -y 1)")
        return 0 if present else 1

    config = load_config()
    sensor = init_ina219(int(config.get("ina219_addr", 0x43)))
    critical_level = int(config.get("critical_level_percent", config.get("shutdown_threshold_percent", DEFAULT_CRITICAL_LEVEL)))
    poll_seconds = int(config.get("battery_watchdog_poll_seconds", DEFAULT_POLL_SECONDS))
    gpio_pin = config.get("ups_hat_signal_gpio")
    gpio_monitor = GpioSignalMonitor(int(gpio_pin) if gpio_pin is not None else None)

    try:
        if args.simulate_critical:
            # ⚠️ TICKET-121 (2026-08-17) : `read_level()` renvoie TROIS valeurs
            # (level, charging, sensor). Ce dépaquetage n'en attendait que deux
            # et levait un `ValueError` immédiat — or c'est le SEUL chemin qui
            # permette de tester l'arrêt critique. Les deux défauts se
            # couvraient l'un l'autre : le chemin réel était cassé (sudo +
            # NoNewPrivileges) et le chemin de test qui l'aurait révélé aussi.
            # D'où un service resté « non prouvé » depuis TICKET-011.
            level, _, _ = read_level(sensor, config)
            perform_shutdown_sequence(level if level is not None else critical_level, simulate=True)
            return 0

        LOGGER.info("Battery watchdog started")
        # TICKET-133 : l'état de charge précédent alimente l'hystérésis de la
        # bande morte. `None` au premier tour — detecter_charge() répond alors
        # « charge » dans la bande morte, ce qui évite un arrêt injustifié au
        # démarrage sur un courant quasi nul.
        charging: bool | None = None
        while True:
            triggered = gpio_monitor.triggered()
            level, charging_lu, sensor = read_level(sensor, config, previous_charging=charging)
            # On ne mémorise l'état que si la lecture a réussi : en cas
            # d'erreur capteur, read_level() renvoie False par défaut, et le
            # garder fausserait l'hystérésis du tour suivant.
            if level is not None:
                charging = charging_lu
            if triggered:
                LOGGER.warning("Critical battery GPIO triggered")
                perform_shutdown_sequence(level, simulate=False)
                return 0
            if level is not None and not charging_lu and level < critical_level:
                LOGGER.warning("Critical battery level detected: %s%%", level)
                perform_shutdown_sequence(level, simulate=False)
                return 0
            time.sleep(poll_seconds)
    finally:
        gpio_monitor.close()


if __name__ == "__main__":
    raise SystemExit(main())