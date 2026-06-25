#!/bin/bash
# Relance Chromium en mode kiosque depuis SSH (Wayland)
pkill chromium 2>/dev/null
pkill wf-panel-pi 2>/dev/null || true   # supprime toutes les notifications desktop
sleep 1
WAYLAND_DISPLAY=wayland-0 \
XDG_RUNTIME_DIR=/run/user/$(id -u) \
XDG_SESSION_TYPE=wayland \
nohup chromium \
  --ozone-platform=wayland \
  --noerrdialogs --disable-infobars --kiosk \
  http://localhost/lecteur \
  &>/tmp/chromium.log &
echo "Chromium relancé (PID $!)"
# Chime après 6s — le temps que Chromium charge la page
(sleep 6 && python3 /home/thomas/hechicero/scripts/play_chime.py) &
