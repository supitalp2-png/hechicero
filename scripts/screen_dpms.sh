#!/bin/bash
# screen_dpms.sh — Extinction/allumage écran via wlr-randr (Pi 5 + labwc)
#
# wlopm échoue : zwlr_output_power_management_v1 non supporté
# sysfs DRM dpms : lecture seule sur Pi 5 même en root
# Solution : wlr-randr désactive/réactive le connecteur via zwlr_output_management_v1
#
# ⚠️ OUTPUT dépend du port HDMI physique du Pi 5 (HDMI-A-1 ou HDMI-A-2) — pas
# du modèle d'écran. Si l'écran est rebranché sur l'autre port (ex: après une
# intervention hardware), ce nom doit être mis à jour. Vérifier avec `wlr-randr`
# (cherche "Enabled: yes" et le mode "current"). Changé le 2026-07-08 :
# HDMI-A-2 → HDMI-A-1 (écran JRP JRP7003, rebranché pendant l'intégration finale).

OUTPUT="HDMI-A-1"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

case "${1:-off}" in
    off|Off|OFF)
        wlr-randr --output "$OUTPUT" --off
        ;;
    on|On|ON)
        wlr-randr --output "$OUTPUT" --on --preferred
        ;;
    *)
        echo "Usage: $0 off|on" >&2
        exit 1
        ;;
esac
