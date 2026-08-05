#!/bin/bash
# smoke_test.sh — Vérification rapide de l'état d'Hechicero (~40 s)
#
# Objectif : en une commande, dire si le système est sain après une livraison,
# sans avoir à dérouler un protocole de test manuel.
#
# Ce que ça NE fait pas : valider visuellement l'IHM. Le test 4 contourne
# partiellement la limite en observant le journal Apache — si le navigateur
# kiosque redemande data.json après qu'on ait touché le fichier, c'est que la
# boucle de rafraîchissement (TICKET-114) tourne réellement dans Chromium.
#
# Effets de bord : aucun, sauf un `touch` sur data.json (change la date, pas le
# contenu) — c'est précisément le déclencheur qu'on veut tester.
# N'éteint jamais l'écran, ne touche pas à la lecture en cours.
#
# Usage :  chmod +x scripts/smoke_test.sh && ./scripts/smoke_test.sh

ROOT="/home/thomas/hechicero"
DATA_JSON="$ROOT/web/lecteur/data.json"
ACCESS_LOG="/var/log/apache2/access.log"
# md5 de référence de screen_dpms.sh. À mettre à jour à CHAQUE modification du
# script, sinon le test passe en avertissement et on finit par l'ignorer.
# 2026-08-04 933e04d7… — réécriture TICKET-115bis (off/on/rescue/status)
# 2026-08-05 270794ad… — TICKET-123, journalisation de l'appelant
SCREEN_MD5_ATTENDU="270794add9264a94d72422b66fc4631e"

export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

OK=0; KO=0; WARN=0

pass() { echo "  ✅ $*"; OK=$((OK+1)); }
fail() { echo "  ❌ $*"; KO=$((KO+1)); }
warn() { echo "  ⚠️  $*"; WARN=$((WARN+1)); }
titre() { echo; echo "── $* ──────────────────────────────"; }

titre "1. Script écran (TICKET-115)"

if [ ! -f "$ROOT/scripts/screen_dpms.sh" ]; then
    fail "screen_dpms.sh absent"
else
    md5=$(md5sum "$ROOT/scripts/screen_dpms.sh" | awk '{print $1}')
    if [ "$md5" = "$SCREEN_MD5_ATTENDU" ]; then
        pass "screen_dpms.sh conforme (md5 $md5)"
    else
        warn "screen_dpms.sh modifié depuis la livraison (md5 $md5)"
    fi
    if bash -n "$ROOT/scripts/screen_dpms.sh" 2>/dev/null; then
        pass "syntaxe bash correcte"
    else
        fail "erreur de syntaxe bash"
    fi
    # Les 4 actions doivent être déclarées
    for act in "off" "on" "rescue" "status"; do
        if grep -q "^\s*${act}|" "$ROOT/scripts/screen_dpms.sh"; then
            pass "action '$act' présente"
        else
            fail "action '$act' MANQUANTE"
        fi
    done
    # Comportement anti-clignotement : sur écran ALLUMÉ, 'on' ne doit rien faire.
    # C'est la régression du bouton GPIO23 (TICKET-115bis) qu'on surveille ici.
    #
    # ⚠️ On vérifie l'état AVANT d'appeler quoi que ce soit (corrigé le
    # 2026-08-05). L'ancienne version appelait `on` sans regarder : si l'écran
    # était éteint, le test le RALLUMAIT. Effet de bord interdit par le
    # registre — et surtout, depuis TICKET-123, un réveil qui ne vient pas du
    # tactile laisse swayidle bloqué et l'écran allumé indéfiniment. Le smoke
    # test pouvait donc déclencher lui-même le bug qu'il est censé surveiller.
    if command -v wlr-randr >/dev/null 2>&1; then
        etat_ecran=$(wlr-randr 2>/dev/null | awk '
            $1 == "HDMI-A-1"  { inblock = 1; next }
            /^[^[:space:]]/   { inblock = 0 }
            inblock && $1 == "Enabled:" { print $2; exit }')
        if [ "$etat_ecran" = "yes" ]; then
            "$ROOT/scripts/screen_dpms.sh" on >/dev/null 2>&1
            if tail -1 "$ROOT/data/screen_dpms.log" 2>/dev/null | grep -q "déjà actif"; then
                pass "appui bouton antenne : no-op confirmé (pas de clignotement)"
            else
                fail "écran allumé mais 'on' n'a pas été un no-op — régression du clignotement GPIO23"
            fi
        elif [ "$etat_ecran" = "no" ]; then
            pass "écran en veille — test du no-op sauté (le réveiller depuis un test figerait swayidle, TICKET-123)"
        else
            warn "état de l'écran illisible via wlr-randr — test du no-op sauté"
        fi
    else
        warn "wlr-randr indisponible (pas de session Wayland ici ?) — test écran sauté"
    fi
fi

titre "2. Backend lecteur (TICKET-114)"

if php -l "$ROOT/web/lecteur/radio.php" >/dev/null 2>&1; then
    pass "radio.php : syntaxe PHP correcte"
else
    fail "radio.php : ERREUR DE SYNTAXE"
    php -l "$ROOT/web/lecteur/radio.php"
fi

rep=$(curl -s --max-time 5 "http://localhost/lecteur/radio.php?action=data_version")
mtime=$(echo "$rep" | sed -n 's/.*"mtime":\([0-9]*\).*/\1/p')
size=$(echo "$rep" | sed -n 's/.*"size":\([0-9]*\).*/\1/p')
if [ -n "$mtime" ] && [ "$mtime" -gt 0 ] 2>/dev/null && [ -n "$size" ] && [ "$size" -gt 0 ] 2>/dev/null; then
    pass "endpoint data_version OK (mtime=$mtime, size=$size)"
else
    fail "endpoint data_version : réponse inattendue → $rep"
fi

titre "3. Frontend lecteur (TICKET-114)"

IDX="$ROOT/web/lecteur/index.html"
for sym in "pollCatalogVersion" "refreshCatalogInPlace" "findEpisodeByAudio"; do
    if grep -q "$sym" "$IDX"; then
        pass "$sym présent"
    else
        fail "$sym MANQUANT"
    fi
done
if grep -q "setInterval(pollCatalogVersion, 10000)" "$IDX"; then
    pass "polling catalogue armé à 10 s"
else
    fail "setInterval(pollCatalogVersion, 10000) absent"
fi
# Le trou d'origine : le tick 5 min appelait loadData() sans jamais re-rendre.
if grep -q "loadParentalConfig(); refreshCatalogInPlace();" "$IDX"; then
    pass "tick 5 min corrigé (refreshCatalogInPlace, plus loadData seul)"
else
    fail "le tick 5 min appelle encore loadData() — le bug d'origine est de retour"
fi
# Précaution 2 : les écrans de lecture ne doivent jamais être re-rendus.
if grep -q "currentScreen === 'player' || currentScreen === 'radio-player') return;" "$IDX"; then
    pass "garde-fou anti-clignotement de la lecture en place"
else
    warn "garde-fou 'player/radio-player' non trouvé sous sa forme attendue — à relire"
fi

titre "4. Boucle de rafraîchissement vue depuis le serveur"

# On ne peut pas observer le rendu du navigateur depuis le shell. En revanche,
# si le kiosque tourne, il interroge data_version toutes les 10 s et, quand la
# signature bouge, il redemande data.json. Les deux traces sont dans le journal
# Apache : c'est la preuve indirecte que la boucle vit réellement.
# Le journal Apache appartient à root:adm. Plutôt que de lancer TOUT le script
# en sudo (ce qui casserait wlr-randr et mpc, qui ont besoin de la session de
# `thomas`), on n'élève que cette lecture, et seulement si sudo ne demande pas
# de mot de passe.
log_lire() {
    if [ -r "$ACCESS_LOG" ]; then cat "$ACCESS_LOG"
    else sudo -n cat "$ACCESS_LOG" 2>/dev/null
    fi
}

if [ -n "$(log_lire | head -1)" ]; then
    n_poll=$(log_lire | tail -n 300 | grep -c "data_version")
    if [ "$n_poll" -gt 0 ]; then
        pass "le kiosque interroge bien data_version ($n_poll appels récents)"
        # `data.json` est régénéré tantôt par l'ingestion (thomas), tantôt par
        # l'admin PHP (www-data) : son propriétaire n'est donc pas garanti.
        # Un `touch` refusé ne prouve RIEN sur TICKET-114 — le test n'a
        # simplement pas pu s'exécuter. D'où le warn et non le fail
        # (faux échec constaté le 2026-08-05).
        if touch "$DATA_JSON" 2>/dev/null; then
            declencheur="direct"
        elif sudo -n touch "$DATA_JSON" 2>/dev/null; then
            declencheur="sudo"
        else
            declencheur=""
        fi

        if [ -z "$declencheur" ]; then
            warn "touch impossible sur data.json ($(stat -c '%U:%G %a' "$DATA_JSON" 2>/dev/null)) — test de rechargement sauté, PAS une panne de TICKET-114"
        else
            lignes_avant=$(log_lire | wc -l)
            echo "     … touch data.json ($declencheur) puis attente de 15 s"
            touch "$DATA_JSON" 2>/dev/null || sudo -n touch "$DATA_JSON" 2>/dev/null
            sleep 15
            nouveaux=$(log_lire | tail -n +$((lignes_avant + 1)))
            if echo "$nouveaux" | grep -q "lecteur/data.json"; then
                pass "changement détecté ET catalogue rechargé par le kiosque — TICKET-114 vivant"
            else
                fail "aucun rechargement de data.json en 15 s — la détection ne fonctionne pas"
            fi
        fi
    else
        warn "aucun appel data_version récent : le kiosque tourne-t-il ? (relancer Chromium)"
    fi
else
    warn "journal Apache illisible (droits) — test 4 sauté. Pour l'activer : sudo usermod -aG adm thomas puis reconnexion"
fi

titre "5. Services"

# Piège rencontré le 2026-08-04 : `hechicero-idle` est une unité **utilisateur**
# (~/.config/systemd/user/), invisible depuis le scope système — d'où un faux
# négatif alors que le service tournait très bien. On interroge donc les deux
# scopes, puis on retombe sur la présence du processus : ce qui compte ici,
# c'est que la fonction soit vivante, pas la façon dont elle est déclarée.
service_actif() {
    local svc="$1" motif="$2"
    if systemctl is-active --quiet "$svc" 2>/dev/null;        then echo "unité système";     return 0; fi
    if systemctl --user is-active --quiet "$svc" 2>/dev/null; then echo "unité utilisateur"; return 0; fi
    if [ -n "$motif" ] && pgrep -f "$motif" >/dev/null 2>&1;   then echo "processus vivant";  return 0; fi
    return 1
}

verifier_service() {
    local svc="$1" motif="$2" ou
    if ou=$(service_actif "$svc" "$motif"); then
        pass "$svc actif ($ou)"
    else
        warn "$svc : ni unité système, ni unité utilisateur, ni processus — à vérifier"
    fi
}

verifier_service mpd             "/usr/bin/mpd"
verifier_service buttons_daemon  "buttons_daemon.py"
verifier_service hechicero-idle  "idle_screen.sh"
verifier_service battery_tracker "battery_tracker.py"
verifier_service play_tracker    "play_tracker.py"
verifier_service battery_watchdog "battery_watchdog.py"

# ⚠️ NE PAS revenir à `mpc status` ici (TICKET-122, 2026-08-05). Quand MPD se
# fige — thread principal bloqué sur un verrou, socket d'écoute qui n'accepte
# plus — `mpc` ne renvoie pas une erreur : il attend, et le smoke test se fige
# avec lui sans jamais rien rapporter. C'est exactement ce qui a permis à un
# MPD bloqué de passer 24 h inaperçu. On sonde donc le socket Unix (le même que
# radio.php) avec un délai de garde.
if reponse=$(timeout 10 python3 "$ROOT/scripts/mpd_watchdog.py" --probe 2>&1 | tail -1); then
    pass "MPD répond — $reponse"
else
    fail "MPD ne répond pas — $reponse"
    echo "     → récupération : sudo python3 scripts/mpd_watchdog.py --recover"
fi

if ou=$(service_actif mpd_watchdog "mpd_watchdog.py"); then
    pass "mpd_watchdog actif ($ou)"
else
    warn "mpd_watchdog inactif — un MPD figé ne serait plus détecté (TICKET-122)"
fi

titre "6. Unités systemd — pièges de la zone Z2"

# Zone Z2 du registre docs/75-NON_REGRESSION.md. Ces quatre contrôles sont
# statiques et instantanés, mais ils couvrent des pannes qui ont réellement
# coûté cher — et surtout des pannes LATENTES, invisibles tant qu'un vieux
# fichier traîne ou tant que personne ne redémarre le service dont elles
# dépendent.

# ── Garde TICKET-122 : `Requires=` propage l'ARRÊT ────────────────────────
# buttons_daemon, play_tracker et audio_eq_apply portaient
# `Requires=mpd.service`. Conséquence : réparer MPD (ou simplement le
# redémarrer) éteignait les boutons physiques ET arrêtait le suivi d'écoute,
# silencieusement pour ce dernier. Ce test échoue sur le code d'avant le
# correctif du 2026-08-05 — c'est ce qui en fait un vrai test de garde.
coupables=$(grep -l '^Requires=mpd' "$ROOT"/scripts/*.service 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')
if [ -z "$coupables" ]; then
    pass "aucune unité ne porte Requires=mpd.service (pas de propagation d'arrêt)"
else
    fail "Requires=mpd.service dans : $coupables → un redémarrage de MPD les tuera. Utiliser Wants="
fi

# ── Garde TICKET-120 : un service durci n'écrit pas dans le dépôt ─────────
# lgpio crée son tube .lgd-nfy<N> dans le répertoire courant. Avec
# WorkingDirectory dans scripts/ — non inscriptible depuis le durcissement —
# buttons_daemon ne pouvait plus le recréer, et ne survivait que grâce à un
# fichier antérieur. Panne armée pendant deux semaines.
if grep -q '^WorkingDirectory=/run/' "$ROOT/scripts/buttons_daemon.service" 2>/dev/null \
   && grep -q '^RuntimeDirectory=' "$ROOT/scripts/buttons_daemon.service" 2>/dev/null; then
    pass "buttons_daemon : répertoire de travail volatil sous /run (tube lgpio recréable)"
else
    fail "buttons_daemon : WorkingDirectory doit être sous /run avec RuntimeDirectory= — sinon lgpio ne peut plus créer son tube"
fi

# ── Garde : PrivateDevices casse GPIO et audio ────────────────────────────
# Règle absolue du registre (Z2). Vécu sur l'égaliseur (/dev/snd) et
# potentiellement sur /dev/gpiochip*.
if grep -l '^PrivateDevices=\(yes\|true\)' "$ROOT"/scripts/*.service >/dev/null 2>&1; then
    fail "PrivateDevices= présent dans une unité — casse l'accès GPIO et audio"
else
    pass "aucun PrivateDevices= dans les unités"
fi

# ── Garde : dérive entre le dépôt et ce qui tourne réellement ─────────────
# Une unité corrigée dans le dépôt mais jamais recopiée dans
# /etc/systemd/system/ donne l'illusion que le correctif est livré. Le test
# comparerait alors du code qui ne tourne pas.
derive=""
for u in "$ROOT"/scripts/*.service; do
    nom=$(basename "$u")
    installe="/etc/systemd/system/$nom"
    [ -f "$installe" ] || continue
    cmp -s "$u" "$installe" || derive="$derive $nom"
done
if [ -z "$derive" ]; then
    pass "unités installées identiques à celles du dépôt"
else
    warn "dérive dépôt ↔ /etc/systemd/system :$derive — recopier puis daemon-reload"
fi

titre "7. Vie privée du dépôt public (zone Z10)"

# Le dépôt est public : un prénom réel parti dans un commit reste dans
# l'historique git, ça ne se rattrape pas. Une fuite a déjà dû être neutralisée
# (TICKET-118). La liste des prénoms cherchés vit dans private/ (hors dépôt) —
# elle ne peut pas être écrite dans un script versionné.
if [ -x "$ROOT/scripts/check_privacy.sh" ] || [ -f "$ROOT/scripts/check_privacy.sh" ]; then
    sortie=$(bash "$ROOT/scripts/check_privacy.sh" 2>&1)
    code=$?
    case $code in
        0) pass "$(echo "$sortie" | tail -1 | sed 's/^✅ //')" ;;
        1) fail "prénom réel trouvé dans des fichiers suivis par git — NE PAS COMMITTER"
           echo "$sortie" | sed 's/^/     /' ;;
        *) warn "vérification vie privée impossible — $(echo "$sortie" | head -1)" ;;
    esac
else
    warn "scripts/check_privacy.sh absent — aucun filet contre une fuite de prénom"
fi

titre "8. Chaîne audio (zone Z6)"

# Zone Z6 du registre. Elle n'avait aucune garde automatique alors qu'elle a
# déjà fait planter MPD (TICKET-030). Tous les contrôles ci-dessous sont en
# lecture seule : rien n'est appliqué, aucun son n'est modifié.

# ── Numéros de carte ALSA instables ───────────────────────────────────────
# Les numéros hw:N,0 changent d'un boot à l'autre (vécu le 2026-07-03 : cartes
# 2 et 3 inversées). Toute référence par numéro finit par pointer la mauvaise
# carte, et le son sort au mauvais endroit — ou pas du tout.
# La référence matérielle ne vit PAS dans mpd.conf (corrigé le 2026-08-05) :
# depuis TICKET-030, les sorties MPD pointent vers les plugins alsaequal
# (`eqhp` / `eqcasque`), et c'est /etc/asound.conf qui nomme les vraies cartes.
# Chercher hw:CARD= dans mpd.conf ne pouvait donc rien donner.
if [ -r /etc/asound.conf ]; then
    if grep -qE 'slave\.pcm.*(plug)?hw:CARD=' /etc/asound.conf; then
        pass "asound.conf : cartes des sorties MPD référencées par nom (hw:CARD=)"
    else
        fail "asound.conf : aucune sortie référencée par nom — les numéros de carte dérivent d'un boot à l'autre"
    fi

    # Le périphérique ALSA par défaut est un chemin distinct de celui de MPD.
    # Tout ce qui ne précise pas -D l'emprunte : son de démarrage, aplay,
    # Chromium. S'il est numéroté, une ré-énumération l'envoie sur la mauvaise
    # carte — le chime de boot partirait dans le HDMI.
    if grep -qE '^\s*(slave\.pcm\s+"hw:[0-9]|card\s+[0-9])' /etc/asound.conf; then
        warn "asound.conf : le périphérique par DÉFAUT est numéroté ($(grep -cE '^\s*(slave\.pcm\s+"hw:[0-9]|card\s+[0-9])' /etc/asound.conf) ligne(s)) — MPD n'est pas concerné, mais le son de démarrage si. Remplacer par CARD=sndrpihifiberry"
    else
        pass "asound.conf : périphérique par défaut référencé par nom"
    fi
else
    warn "/etc/asound.conf illisible — contrôle des cartes ALSA sauté"
fi

# mpd.conf doit pointer vers les plugins d'égalisation, pas vers le matériel.
if [ -r /etc/mpd.conf ]; then
    if grep -qE '^[^#]*device[^#]*"hw:[0-9]' /etc/mpd.conf; then
        fail "mpd.conf référence une carte par NUMÉRO (hw:N) — instable d'un boot à l'autre"
        grep -nE '^[^#]*device[^#]*"hw:[0-9]' /etc/mpd.conf | sed 's/^/     /'
    elif grep -qE '^[^#]*device[^#]*"eq(hp|casque)"' /etc/mpd.conf; then
        pass "mpd.conf : sorties dirigées vers les plugins alsaequal (eqhp/eqcasque)"
    else
        warn "mpd.conf : sorties ni numérotées ni sur eqhp/eqcasque — à relire"
    fi
else
    warn "/etc/mpd.conf illisible — contrôle des sorties MPD sauté"
fi

# ── États binaires alsaequal ──────────────────────────────────────────────
# 840 octets = sain. Un fichier vide ou tronqué fait planter alsaequal en
# SIGBUS (mmap sur taille 0), ce qui peut emporter MPD et griller le
# disjoncteur de mpd.socket — incident TICKET-030, récupération en §6.4.1.
for prof in hp casque; do
    f="$ROOT/data/alsaequal_$prof.bin"
    if [ ! -f "$f" ]; then
        warn "alsaequal_$prof.bin absent (normal si l'égaliseur n'a jamais tourné)"
    else
        taille=$(stat -c %s "$f")
        if [ "$taille" -eq 840 ]; then
            pass "alsaequal_$prof.bin sain (840 octets)"
        else
            fail "alsaequal_$prof.bin fait $taille octets au lieu de 840 — risque de SIGBUS, voir §6.4.1"
        fi
    fi
done

# ── Sécurité auditive de l'enfant ─────────────────────────────────────────
# speakers_max ≤ 80 est un invariant, pas un réglage. Et le gain casque
# (TICKET-124) doit rester dans 0..6 dB : au-delà, l'écrêtage devient
# systématique et la distorsion audible.
sortie_vol=$(python3 - "$ROOT" <<'PY' 2>&1
import json, sys, pathlib
root = pathlib.Path(sys.argv[1])
faute = False
detail = []

try:
    cfg = json.loads((root / "web/lecteur/config.json").read_text())
    smax = cfg.get("volume", {}).get("speakers_max")
    if smax is None:
        detail.append("speakers_max absent de config.json")
    elif smax > 80:
        detail.append(f"speakers_max = {smax} > 80 — INVARIANT DE SÉCURITÉ AUDITIVE")
        faute = True
    else:
        detail.append(f"speakers_max = {smax}")
except Exception as e:
    detail.append(f"config.json illisible ({e})")

eqp = root / "data/audio_eq.json"
if eqp.exists():
    try:
        gain = json.loads(eqp.read_text()).get("profiles", {}).get("casque", {}).get("gain_db", 0)
        if not (0 <= gain <= 6):
            detail.append(f"gain casque = {gain} dB hors de 0..6")
            faute = True
        else:
            detail.append(f"gain casque = {gain} dB")
    except Exception as e:
        detail.append(f"audio_eq.json illisible ({e})")

print(" · ".join(detail))
sys.exit(1 if faute else 0)
PY
)
if [ $? -eq 0 ]; then
    pass "limites de volume conformes — $sortie_vol"
else
    fail "limite de volume violée — $sortie_vol"
fi

titre "Résultat"
echo "  $OK OK · $KO échec(s) · $WARN avertissement(s)"
echo
if [ "$KO" -gt 0 ]; then
    echo "  ⛔ Au moins un test a échoué — ne pas considérer la livraison comme saine."
    exit 1
fi
if [ "$WARN" -gt 0 ]; then
    echo "  🟡 Aucun échec, mais des points à regarder ci-dessus."
    exit 0
fi
echo "  🟢 Tout est vert."
exit 0
