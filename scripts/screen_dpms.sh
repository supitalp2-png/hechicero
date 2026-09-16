#!/bin/bash
# screen_dpms.sh — Extinction/allumage écran (Pi 5 + labwc)
#
# ⚠️ CE QUI SUIT A CHANGÉ LE 2026-09-16, LIRE AVANT DE TOUCHER AU SCRIPT.
#
# Historique des méthodes, et pourquoi on en est à la troisième :
#   1. `wlopm` — REFUSÉ à l'origine : labwc n'exposait pas
#      `zwlr_output_power_management_v1`.
#   2. `wlr-randr --off/--on` — retenu faute de mieux, avec un rebond de mode
#      pour forcer un modeset (TICKET-115).
#   3. **`wlopm` à nouveau, et c'est la bonne** — depuis labwc 0.20.1 /
#      wlroots 0.20.2, le protocole est exposé. Vérifié le 2026-09-16 :
#      `wlopm` répond `HDMI-A-1 on`, et pendant une extinction par wlopm
#      `wlr-randr` rapporte toujours `Enabled: yes`.
#
# 🔴 ET SURTOUT : la même mise à jour a rendu `wlr-randr --off` DESTRUCTEUR.
# Une fois la sortie désactivée, tout rallumage échoue — y compris un `--on`
# nu — avec `failed to apply configuration`, code 1. Seul un redémarrage
# récupère. C'est le TICKET-154, et c'est pour ça que ce script n'appelle
# plus jamais `--off`.
#
# `sysfs DRM dpms` : lecture seule sur Pi 5 même en root, écarté depuis toujours.
#
# 📌 Une note périmée dans un en-tête coûte cher : celle qui disait « wlopm
# échoue » datait d'un an et a fait chercher ailleurs pendant toute la soirée
# du 16/09. Redater les affirmations sur l'environnement quand il change.
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

# ── TICKET-149 — l'EXPOSITION, la mesure qui manquait ─────────────────────────
# On sait depuis le 2026-08-25 que la panne est dans la dalle : son récepteur
# HDMI décroche quand le signal est coupé et ne se re-verrouille pas au retour.
# Ce qu'on ignore, c'est ce qui déclenche le décrochage. La première suspecte
# était la durée sans signal — 60 s récupère, 1 h 48 non — mais le journal la
# dément : une extinction de 13 h 54 (22/08 20:52 → 23/08 10:46) s'est réveillée
# sans incident. Le phénomène est donc INTERMITTENT.
#
# Impossible de trancher sans compter. On enregistre à chaque réveil la durée
# d'extinction qui vient de s'écouler et la température du SoC, pour pouvoir un
# jour croiser ces valeurs avec les pannes constatées (`ecran_noir.py`).
#
# ⚠️ Aucun fichier d'état : la durée est relue dans le journal lui-même. Un
# service durci ne peut pas écrire n'importe où (zone Z2), et un fichier d'état
# de plus est un fichier de plus à perdre.
duree_extinction() {
    local depuis maintenant
    # ⚠️ `grep -a` obligatoire. Ce journal finit par contenir des octets NUL —
    # même mal que `sleep_debug.log` en son temps — et grep bascule alors en
    # mode binaire : il répond « binary file matches » au lieu de la ligne.
    # Le champ `extinction=` restait donc vide à jamais, et comme le rapport
    # filtre justement sur lui, il n'aurait plus jamais compté un seul réveil.
    # Un silence parfaitement crédible, et faux (constaté le 2026-08-26).
    depuis=$(tac "$LOGFILE" 2>/dev/null \
        | grep -a -m1 -E '\] off ' \
        | cut -d'[' -f1)
    [ -z "$depuis" ] && { echo "inconnue"; return; }
    depuis=$(date -d "$depuis" +%s 2>/dev/null) || { echo "inconnue"; return; }
    maintenant=$(date +%s)
    echo "$(( maintenant - depuis ))s"
}

temperature_soc() {
    local brut
    brut=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null) || { echo "?"; return; }
    echo "$(( brut / 1000 ))C"
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

# ── TICKET-153 — le rebond ne doit jamais rester à mi-chemin ────────────────
# Le rebond passe par un mode INTERMÉDIAIRE (1280x720) avant de revenir au mode
# natif. Entre les deux, il y a `sleep 3`. Si le script est tué pendant ce
# sommeil, la dalle reste en 1280x720 alors que le compositeur rend en
# 1024x600 : écran noir, tous les indicateurs au vert.
#
# Ce n'est pas théorique. `buttons_daemon.wake_screen()` lançait ce script avec
# `timeout=5`, alors que le rebond dure 3 s de sommeil + deux `wlr-randr` + le
# démarrage de `runuser` — soit 4 à 5 s. Le chemin BOUTON courait donc contre
# une échéance qu'il atteignait parfois, et il était tué exactement au pire
# endroit. Le chemin TACTILE, lancé par swayidle sans délai de garde, n'a
# jamais eu ce problème. C'est ce que Thomas observait depuis des mois.
#
# Deux protections, et elles sont indépendantes :
#   1. un `trap` remet le mode natif quoi qu'il arrive — y compris sur SIGTERM ;
#   2. un verrou interdit à deux rebonds de s'entrelacer.
restaurer_mode() {
    # Idempotent : reposer le mode natif alors qu'il est déjà en place est un
    # no-op pour wlr-randr. Le coût d'un appel inutile est nul, celui d'une
    # dalle laissée en 1280x720 est un écran noir.
    wlr-randr --output "$OUTPUT" --mode "$MODE" 2>/dev/null
    log_dpms "rebond — mode natif restauré par le filet de sécurité"
}

# ── TICKET-154 — un échec de wlr-randr doit s'entendre ──────────────────────
# Le 2026-09-16, après une mise à jour de Raspberry Pi OS, `wlr-randr` a
# commencé à répondre `failed to apply configuration` / code 1 sur TOUTES les
# commandes de rallumage — y compris un simple `--on` sans mode. La sortie
# restait `Enabled: no`, l'écran noir, et ce script écrivait « terminé ».
#
# Il a fallu une soirée entière pour établir ce qu'un code de retour affiché
# aurait dit en trois minutes. **Ignorer le statut d'une commande, c'est
# transformer une panne bruyante en panne silencieuse.**
executer_wlr() {
    local sortie
    if sortie=$(wlr-randr "$@" 2>&1); then
        return 0
    fi
    log_dpms "⛔ ÉCHEC wlr-randr $* — ${sortie:-(pas de message)}"
    return 1
}

bounce_mode() {
    # Si on est tué maintenant, le mode natif est reposé avant de mourir.
    trap 'restaurer_mode; exit 143' TERM INT HUP
    local rc=0
    executer_wlr --output "$OUTPUT" --on --mode "$BOUNCE_MODE" || rc=1
    sleep "$BOUNCE_DELAY"
    executer_wlr --output "$OUTPUT" --mode "$MODE" || rc=1
    trap - TERM INT HUP
    return $rc
}

# ⚠️ Verrou : deux exécutions concurrentes existent réellement. Le journal du
# 2026-08-28 montre deux invocations à la MÊME seconde (19:44:32). Deux rebonds
# entrelacés émettent des changements de mode dans le désordre.
# `-w 12` : on attend le verrou jusqu'à 12 s — plus long que le rebond — puis on
# renonce plutôt que de s'accumuler. Renoncer est sûr : si un autre rebond vient
# de finir, la dalle est déjà réveillée.
VERROU="/tmp/hechicero-screen-dpms.lock"
prendre_verrou_ou_renoncer() {
    exec 9>"$VERROU" 2>/dev/null || return 0   # /tmp indisponible : on continue
    if ! flock -w 12 9; then
        log_dpms "$1 — verrou occupé 12 s, on renonce (un autre rebond est en cours)"
        return 1
    fi
    return 0
}

# ── TICKET-154 — extinction par wlopm, plus jamais par --off ────────────────
# Depuis la mise à jour du 2026-09-16 (labwc 0.20.1 / wlroots 0.20.2),
# `wlr-randr --off` est une PORTE À SENS UNIQUE : toutes les commandes de
# rallumage échouent ensuite, y compris un simple `--on` sans mode
# (`failed to apply configuration`, code 1). Seul un redémarrage récupère.
#
# La même mise à jour apporte la solution : labwc expose désormais
# `zwlr_output_power_management_v1`, que `wlopm` utilise. Il coupe le
# RÉTROÉCLAIRAGE sans toucher à la configuration de la sortie — vérifié le
# 2026-09-16 : pendant une extinction par wlopm, `wlr-randr` rapporte toujours
# `Enabled: yes`. La porte ne s'ouvre jamais.
#
# 📌 Ce que ça supprime au passage : plus de mode intermédiaire, donc plus de
# `sleep 3`, donc plus de fenêtre où le script peut être tué en plein rebond
# (TICKET-153), et plus de rebond à faire du tout (TICKET-115).
#
# ⚠️ RÈGLE DE SÛRETÉ : si `wlopm` échoue, on NE se rabat PAS sur
# `wlr-randr --off`. Un écran qui reste allumé coûte 664 mA ; un écran qu'on ne
# peut plus rallumer rend l'objet inutilisable pour un enfant de 7 ans. En cas
# de doute, on laisse allumé.
etat_alimentation() {
    # "on", "off", ou vide si wlopm ne répond pas / protocole absent.
    wlopm 2>/dev/null | awk -v out="$OUTPUT" '$1 == out { print $2; exit }'
}

case "${1:-off}" in
    off|Off|OFF)
        log_dpms "off    — extinction demandée"
        if [ -z "$(etat_alimentation)" ]; then
            log_dpms "⛔ off — wlopm muet (protocole absent ?). Écran laissé ALLUMÉ"
            log_dpms "        volontairement : wlr-randr --off ne se rallume plus (TICKET-154)"
            exit 1
        fi
        if wlopm --off "$OUTPUT" 2>/dev/null; then
            log_dpms "off    — rétroéclairage coupé (wlopm), sortie laissée configurée"
        else
            log_dpms "⛔ off — wlopm a échoué. Écran laissé ALLUMÉ volontairement (TICKET-154)"
            exit 1
        fi
        ;;

    on|On|ON)
        # Chemin automatique : swayidle resume ET bouton antenne GPIO23.
        #
        # ⚠️ LA DÉCISION SE PREND SUR `wlr-randr`, PAS SUR `wlopm`.
        # L'état rapporté par wlopm s'est révélé FAUX le 2026-09-16 : après un
        # débranchement physique du HDMI, il annonce `off` sur un écran qui
        # affiche normalement, et son `--on` échoue. Ma première version s'y
        # fiait : elle croyait l'écran éteint, tentait wlopm, échouait, et se
        # rabattait sur le rebond de mode — donc un CLIGNOTEMENT À CHAQUE APPUI
        # du bouton antenne. C'est la régression du TICKET-115bis, rattrapée
        # par le smoke test avant qu'elle n'arrive sur l'appareil.
        if [ "$(output_enabled)" = "no" ]; then
            # Sortie réellement désactivée (héritage d'un ancien `--off`, ou
            # d'un tiers). Seul le rebond de mode peut la ramener.
            prendre_verrou_ou_renoncer "on" || exit 0
            if [ "$(output_enabled)" = "yes" ]; then
                log_dpms "on     — réveillé par une autre exécution pendant l'attente du verrou"
                exit 0
            fi
            log_dpms "on     — sortie inactive, rebond $BOUNCE_MODE -> $MODE"
            bounce_mode || { log_dpms "on     — ⛔ LE REBOND A ÉCHOUÉ"; exit 1; }
            log_dpms "on     — terminé · extinction=$(duree_extinction) temp=$(temperature_soc)"
        else
            # Sortie configurée : c'est le cas normal depuis le TICKET-154.
            # `wlopm --on` rallume le rétroéclairage et ne fait rien s'il est
            # déjà allumé. JAMAIS de rebond ici — ce chemin est celui du bouton
            # GPIO23, tout effet visible y serait ressenti à chaque pression.
            if wlopm --on "$OUTPUT" 2>/dev/null; then
                log_dpms "on     — déjà actif (sortie configurée), rétroéclairage assuré par wlopm"
            else
                log_dpms "on     — déjà actif (sortie configurée) ; wlopm a refusé, aucun rebond volontairement"
            fi
        fi
        ;;

    rescue|Rescue|RESCUE)
        # Usage manuel : « tout a l'air allumé mais la dalle est noire ». Ce cas
        # est invisible côté Pi, c'est donc l'humain qui tranche. On tente
        # d'abord wlopm, puis le rebond de mode — ce dernier reste la seule
        # arme contre le décrochage du récepteur HDMI (TICKET-149).
        log_dpms "rescue — demandé (alimentation: $(etat_alimentation), $(output_enabled))"
        wlopm --off "$OUTPUT" 2>/dev/null && sleep 1 && wlopm --on "$OUTPUT" 2>/dev/null \
            && log_dpms "rescue — cycle wlopm effectué"
        prendre_verrou_ou_renoncer "rescue" || exit 0
        if bounce_mode; then
            log_dpms "rescue — terminé"
        else
            log_dpms "rescue — ⛔ LE REBOND A ÉCHOUÉ"
            exit 1
        fi
        ;;

    status|Status|STATUS)
        echo "── alimentation (wlopm) ──"
        wlopm 2>/dev/null || echo "(wlopm indisponible)"
        echo "── configuration (wlr-randr) ──"
        wlr-randr
        ;;

    *)
        echo "Usage: $0 off|on|rescue|status" >&2
        exit 1
        ;;
esac
