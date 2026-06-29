#!/bin/bash
# idle_screen.sh — Extinction écran selon config.json
# Relit la config toutes les 30s et relance swayidle si elle change ou s'il est mort.

CONFIG="/home/thomas/hechicero/web/lecteur/config.json"

export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

SWAYIDLE_PID=""
LAST_CONFIG=""

cleanup() {
    [ -n "$SWAYIDLE_PID" ] && kill "$SWAYIDLE_PID" 2>/dev/null
    exit 0
}
trap cleanup TERM INT

read_config() {
    python3 -c "
import json
try:
    c = json.load(open('$CONFIG'))
    enabled = c.get('screen_off_enabled', True)
    delay   = int(c.get('screen_off_delay', 600))
    print(1 if enabled else 0, delay)
except Exception:
    print(1, 600)
"
}

while true; do
    CURRENT_CONFIG=$(read_config)

    # Détecter si swayidle est mort (crash ou échec de connexion Wayland au démarrage)
    SWAYIDLE_DEAD=0
    if [ -n "$SWAYIDLE_PID" ] && ! kill -0 "$SWAYIDLE_PID" 2>/dev/null; then
        SWAYIDLE_DEAD=1
        SWAYIDLE_PID=""
    fi

    if [ "$CURRENT_CONFIG" != "$LAST_CONFIG" ] || [ "$SWAYIDLE_DEAD" = "1" ]; then
        [ -n "$SWAYIDLE_PID" ] && kill "$SWAYIDLE_PID" 2>/dev/null
        wait "$SWAYIDLE_PID" 2>/dev/null
        SWAYIDLE_PID=""
        LAST_CONFIG="$CURRENT_CONFIG"

        ENABLED=$(echo "$CURRENT_CONFIG" | awk '{print $1}')
        DELAY=$(echo "$CURRENT_CONFIG" | awk '{print $2}')

        if [ "$ENABLED" = "1" ] && [ "$DELAY" -gt 0 ]; then
            swayidle -w \
                timeout "$DELAY"  'wlopm --off \*' \
                resume            'wlopm --on \*' &
            SWAYIDLE_PID=$!
        fi
    fi

    sleep 30
done
