#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
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
# DEBUG LOG — À SUPPRIMER APRÈS TESTS
_debug_handler = logging.FileHandler("/tmp/hechicero_battery_debug.log")
_debug_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
logging.getLogger().addHandler(_debug_handler)


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


def capture_last_session(battery_level: int | None) -> dict[str, Any]:
    mpd = read_mpd_status()
    payload = {
        "shutdown_reason": "battery_critical",
        "shutdown_at": now_iso(),
        "battery_level": battery_level,
        "mpd_file": mpd.get("current") or None,
        "mpd_elapsed": round(float(mpd.get("elapsed") or 0), 1),
    }
    atomic_write_json(LAST_SESSION_PATH, payload)
    return payload


def perform_shutdown_sequence(battery_level: int | None, simulate: bool = False) -> dict[str, Any]:
    payload = capture_last_session(battery_level)
    run_command(["mpc", "stop"])
    if os.name != "nt":
        run_command(["sync"], timeout=10)
    if simulate:
        print("shutdown simulé")
        return payload
    if os.name != "nt":
        run_command(["sudo", "shutdown", "-h", "now"], timeout=10)
    else:
        LOGGER.warning("Shutdown skipped: unsupported OS")
    return payload


def read_level(sensor: Any, config: dict[str, Any]) -> tuple[int | None, bool]:
    try:
        snapshot = read_sensor_snapshot(sensor, config)
    except Exception:
        return None, False
    return int(snapshot["level"]), bool(snapshot["charging"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Hechicero battery watchdog")
    parser.add_argument("--simulate-critical", action="store_true", help="Simule un arrêt critique sans exécuter le shutdown")
    args = parser.parse_args()

    config = load_config()
    sensor = init_ina219(int(config.get("ina219_addr", 0x43)))
    critical_level = int(config.get("critical_level_percent", config.get("shutdown_threshold_percent", DEFAULT_CRITICAL_LEVEL)))
    poll_seconds = int(config.get("battery_watchdog_poll_seconds", DEFAULT_POLL_SECONDS))
    gpio_pin = config.get("ups_hat_signal_gpio")
    gpio_monitor = GpioSignalMonitor(int(gpio_pin) if gpio_pin is not None else None)

    try:
        if args.simulate_critical:
            level, _ = read_level(sensor, config)
            perform_shutdown_sequence(level if level is not None else critical_level, simulate=True)
            return 0

        LOGGER.info("Battery watchdog started")
        while True:
            triggered = gpio_monitor.triggered()
            level, charging = read_level(sensor, config)
            if triggered:
                LOGGER.warning("Critical battery GPIO triggered")
                perform_shutdown_sequence(level, simulate=False)
                return 0
            if level is not None and not charging and level < critical_level:
                LOGGER.warning("Critical battery level detected: %s%%", level)
                perform_shutdown_sequence(level, simulate=False)
                return 0
            time.sleep(poll_seconds)
    finally:
        gpio_monitor.close()


if __name__ == "__main__":
    raise SystemExit(main())