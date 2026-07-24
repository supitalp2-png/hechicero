#!/bin/bash
# Logger Wi-Fi temporaire (diagnostic coupures) — 1 ligne / 30s
# Inclut la température SoC (vcgencmd) depuis le 2026-07-18 (TICKET-109) :
# throttling thermique détecté (vcgencmd get_throttled=0xe0000, pas d'undervoltage)
# et 77.9'C mesuré à chaud — on corrèle température et creux de signal.
LOG=/home/thomas/hechicero/data/wifi_watch.log
while true; do
  L=$(iw dev wlan0 link 2>/dev/null)
  TEMP=$(vcgencmd measure_temp 2>/dev/null | grep -oE '[0-9.]+')
  if [[ "$L" == Connected* ]]; then
    echo "$(date '+%F %T') OK $(awk '/Connected/{b=$3} /freq:/{f=$2} /signal:/{s=$2} /rx bitrate:/{r=$3} /tx bitrate:/{t=$3} END{print "bssid="b" freq="f" sig="s"dBm rx="r" tx="t}' <<<"$L") temp=${TEMP}C"
  else
    echo "$(date '+%F %T') DISCONNECTED temp=${TEMP}C"
  fi
  sleep 30
done >> "$LOG"
