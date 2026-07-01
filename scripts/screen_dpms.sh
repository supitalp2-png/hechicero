#!/bin/bash
# screen_dpms.sh — Extinction/allumage écran via wlr-randr (Pi 5 + labwc)
#
# wlopm échoue : zwlr_output_power_management_v1 non supporté par HDMI-A-2
# sysfs DRM dpms : lecture seule sur Pi 5 même en root
# Solution : wlr-randr désactive/réactive le connecteur via zwlr_output_management_v1

OUTPUT="HDMI-A-2"
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
