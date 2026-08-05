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
#
# ── TICKET-115 (2026-08-02) — pourquoi le rebond de mode ──────────────────
# Symptôme : par intermittence l'écran restait noir après une extinction de
# veille, et seul un reboot ramenait l'image. VNC continuait de fonctionner
# (sortie virtuelle), ce qui a longtemps masqué le problème.
#
# Diagnostic pris en direct PENDANT la panne : `wlr-randr` affichait
# HDMI-A-1 « Enabled: yes », le bon mode courant, l'EDID du JRP7003 lu
# correctement, et `dmesg | grep -i hdmi` ne montrait aucun événement depuis le
# boot. Autrement dit le Pi se croyait en train d'afficher.
#
# Cause racine : `wlr-randr --on --preferred` ne déclenche AUCUN modeset quand
# le connecteur est déjà actif ET déjà au mode préféré. Il n'y a rien à
# changer, donc rien n'est envoyé, et la dalle — elle bel et bien éteinte —
# n'est jamais réveillée. Reposer le même mode est un no-op.
# La seule séquence qui ramène l'image à coup sûr est un aller-retour de mode :
#   --mode 1280x720@60 ; sleep 3 ; --mode 1024x600@59.821
#
# ── TICKET-115bis (2026-08-04) — pourquoi `on` ne rebondit PAS toujours ───
# Première version du correctif : rebond systématique dans l'action `on`.
# Régression immédiate : buttons_daemon.py appelle `screen_dpms.sh on` à CHAQUE
# appui du bouton antenne (GPIO23, écran Chambre) pour réveiller la dalle. Sur
# un écran déjà allumé, le rebond éteignait puis rallumait la dalle → l'écran
# clignotait à chaque pression.
#
# Règle retenue :
#   - `on`     = chemin automatique (swayidle resume + bouton GPIO23). S'il est
#                déjà « Enabled: yes », on ne touche à RIEN. Le cas « Enabled:
#                yes mais dalle noire » n'est pas détectable depuis le Pi (tous
#                les indicateurs sont au vert), donc on ne peut pas le corriger
#                ici sans faire clignoter tous les appuis normaux.
#   - `rescue` = même situation, mais déclenchée à la main en SSH quand on
#                CONSTATE l'écran noir. Force le rebond quel que soit l'état.
#
# ⚠️ Avant de modifier l'action `on`, se rappeler qu'elle est aussi le chemin du
# bouton GPIO23 : tout effet visible y sera ressenti à chaque appui.
#
# ── TICKET-123 (2026-08-05) — pourquoi on journalise l'appelant ───────────
# Ce script ne réarme PAS le compte à rebours de swayidle : celui-ci n'observe
# que les entrées Wayland, et les boutons GPIO sont lus par un processus Python
# que le compositeur ne voit jamais. Conséquence : réveiller la dalle autrement
# que par le tactile laisse swayidle bloqué dans son état « déjà expiré », et
# l'écran reste allumé indéfiniment. Prouvé le 2026-08-05 : trois `on` à 18:34,
# 18:38 et 18:41 n'ont pas empêché l'extinction programmée de 18:52.
#
# Le 2026-08-05 à 14:24, la dalle s'est rallumée maison vide, et il a été
# impossible d'attribuer l'appel — d'où cette instrumentation. On remonte deux
# niveaux : le parent direct est souvent un simple `sh -c`, le vrai demandeur
# (swayidle, buttons_daemon, un humain en SSH) se trouve au-dessus.

OUTPUT="HDMI-A-1"
MODE="1024x600@59.821"       # mode natif du JRP7003
BOUNCE_MODE="1280x720@60"    # mode intermédiaire, uniquement pour forcer un modeset
BOUNCE_DELAY=3               # secondes ; en dessous de ~2s la dalle ne suit pas

LOGFILE="/home/thomas/hechicero/data/screen_dpms.log"

export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Calculé une fois : PPID ne change pas pendant la vie du script.
_pere=$(ps -o comm= -p "$PPID" 2>/dev/null | tr -d ' []')
_aieul_pid=$(ps -o ppid= -p "$PPID" 2>/dev/null | tr -d ' ')
_aieul=$(ps -o comm= -p "${_aieul_pid:-0}" 2>/dev/null | tr -d ' []')
APPELANT="${_pere:-?}<-${_aieul:-?}"

log_dpms() {
    # Instrumentation TICKET-115 : le bug était intermittent et n'a été
    # diagnostiqué qu'en attrapant l'état pendant la panne. On garde une trace
    # de chaque bascule pour pouvoir corréler en cas de récidive.
    # TICKET-123 : on y ajoute l'appelant, sans quoi un réveil inexpliqué reste
    # inexplicable.
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$APPELANT] $*" >> "$LOGFILE" 2>/dev/null
}

# Renvoie "yes", "no", ou "" si l'état n'a pas pu être lu.
# wlr-randr liste chaque sortie sur une ligne non indentée ("HDMI-A-1 \"...\"")
# suivie de ses propriétés indentées, dont "Enabled: yes|no".
output_enabled() {
    wlr-randr 2>/dev/null | awk -v out="$OUTPUT" '
        $1 == out            { inblock = 1; next }
        /^[^[:space:]]/      { inblock = 0 }
        inblock && $1 == "Enabled:" { print $2; exit }
    '
}

# Aller-retour de mode : la seule façon de forcer un modeset et de réveiller
# physiquement la dalle. --on est inclus pour couvrir le cas connecteur éteint.
bounce_mode() {
    wlr-randr --output "$OUTPUT" --on --mode "$BOUNCE_MODE"
    sleep "$BOUNCE_DELAY"
    wlr-randr --output "$OUTPUT" --mode "$MODE"
}

case "${1:-off}" in
    off|Off|OFF)
        log_dpms "off    — extinction demandée"
        wlr-randr --output "$OUTPUT" --off
        ;;

    on|On|ON)
        # Chemin automatique : swayidle resume ET bouton antenne GPIO23.
        STATE="$(output_enabled)"
        if [ "$STATE" = "yes" ]; then
            # Déjà actif : ne rien faire. Un rebond ici ferait clignoter
            # l'écran à chaque appui du bouton GPIO23 (régression TICKET-115).
            log_dpms "on     — déjà actif (Enabled: yes), aucune action"
        else
            log_dpms "on     — sortie inactive (Enabled: ${STATE:-inconnu}), rebond $BOUNCE_MODE -> $MODE"
            bounce_mode
            log_dpms "on     — terminé"
        fi
        ;;

    rescue|Rescue|RESCUE)
        # Usage manuel en SSH : « wlr-randr dit Enabled: yes mais l'écran est
        # noir ». Ce cas est invisible côté Pi, donc c'est l'humain qui tranche.
        log_dpms "rescue — rebond forcé $BOUNCE_MODE -> $MODE (état: $(output_enabled))"
        bounce_mode
        log_dpms "rescue — terminé"
        ;;

    status|Status|STATUS)
        # Pratique en SSH quand l'écran est noir : dit ce que le Pi CROIT
        # afficher, ce qui est rarement ce qu'on voit.
        wlr-randr
        ;;

    *)
        echo "Usage: $0 off|on|rescue|status" >&2
        exit 1
        ;;
esac
