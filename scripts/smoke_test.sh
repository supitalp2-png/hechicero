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

# ── TICKET-129 — PHP en UTC, tout le reste en heure locale ─────────────────
# Bug surveillé : sans `date.timezone`, PHP retombe sur UTC alors que Python et
# le shell écrivent en heure locale. Deux heures d'écart entre journaux croisés,
# précisément quand on croise des journaux — c'est-à-dire pendant une panne.
# A mordu QUATRE fois (TICKET-102, 127, 136, 138) avant d'être traité à la
# racine. Les trois premières fois, on a posé une rustine à l'endroit qui
# faisait mal : une correction posée au point de douleur ne corrige que ce point.
#
# ⚠️ On vérifie le fuseau EFFECTIF, pas la présence du fichier : c'est la seule
# preuve que l'amorçage est réellement appliqué.
if [ -f "$ROOT/web/bootstrap.php" ]; then
    tz=$(php -r "require '$ROOT/web/bootstrap.php'; echo date_default_timezone_get();" 2>/dev/null)
    if [ "$tz" = "Europe/Paris" ]; then
        pass "PHP en heure locale — fuseau effectif $tz (TICKET-129)"
    else
        fail "PHP en fuseau '${tz:-?}' au lieu d'Europe/Paris — 2 h d'écart avec les journaux Python (TICKET-129)"
    fi
else
    fail "web/bootstrap.php absent — PHP repartira en UTC (TICKET-129)"
fi

# Chaque point d'entrée doit l'inclure. Un seul oubli et cette page-là reste en
# UTC, ce qui est pire qu'un défaut uniforme : l'incohérence devient locale et
# donc introuvable.
manquants=""
for page in web/index.php web/health.php web/tracking.php web/dashboard.php \
            web/lecteur/radio.php web/admin/audio_eq.php web/admin/backup_dashboard.php \
            web/admin/battery_dashboard.php web/admin/domotique.php web/admin/favoris.php; do
    [ -f "$ROOT/$page" ] || continue
    grep -q "bootstrap.php" "$ROOT/$page" || manquants="$manquants $(basename "$page")"
done
if [ -n "$manquants" ]; then
    fail "point(s) d'entrée PHP sans amorçage de fuseau :$manquants (TICKET-129)"
else
    pass "tous les points d'entrée PHP amorcent le fuseau (TICKET-129)"
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

# ── TICKET-130 — le filet de sauvegarde des configs est-il réellement armé ?
# Bug surveillé : neuf podcasts ont disparu de data/podcasts.json en silence.
# Le verrou de fichier empêche la mise à jour perdue, les copies horodatées
# rendent une perte récupérable. Mais un mécanisme de protection livré sans
# avoir jamais tourné est une fausse sécurité — c'était le cas au commit
# e081296, où data/config_backups/ n'existait même pas.
# Contrôle purement passif : on regarde, on n'écrit pas.
if grep -q "acquire_json_lock" "$ROOT/web/index.php" \
   && grep -q "mutate_json" "$ROOT/web/index.php"; then
    pass "admin : verrou de fichier présent sur les écritures de config"
else
    fail "admin : verrou de fichier absent — les écritures concurrentes peuvent perdre des entrées (TICKET-130)"
fi

# Précision de l'horodatage : à la seconde, deux écritures rapprochées
# écrasaient la même sauvegarde et il n'en restait qu'une sur cinq.
if grep -q "Ymd_His_v" "$ROOT/web/index.php"; then
    pass "admin : sauvegardes horodatées à la milliseconde (rafale préservée)"
else
    warn "admin : horodatage des sauvegardes à la seconde — une rafale d'écritures n'en laissera qu'une (TICKET-130)"
fi

BK="$ROOT/data/config_backups"
if [ -d "$BK" ]; then
    n_bk=$(find "$BK" -type f 2>/dev/null | wc -l)
    pass "admin : $n_bk sauvegarde(s) de config disponible(s) dans data/config_backups/"
else
    warn "data/config_backups/ absent — le filet n'a jamais servi, donc jamais été prouvé (TICKET-130)"
    echo "     → l'exercer : curl -s \"http://localhost/?action=toggle_podcast&id=olma&enabled=1\""
fi

# ── TICKET-136 — plus personne ne lit le fichier d'état mort ───────────────
# Bug surveillé : `web/status.json` était écrit par scripts/get_status.py,
# supprimé en session 11. Son dernier horodatage datait du 2026-06-28 — la
# page d'accueil de l'admin ET l'écran de l'enfant (en repli) ont affiché
# CINQUANTE JOURS de données figées, sans que personne le remarque : les
# valeurs restaient plausibles (91 %, 4,092 V).
# Leçon : un repli vers des données périmées masque la panne au lieu de la
# montrer. Mieux vaut n'afficher rien.
# ⚠️ Chercher un FETCH, pas la chaîne « status.json » n'importe où : le
# commentaire qui documente ce correctif la contient forcément, et le test
# échouait sur sa propre explication. Un garde-fou qui crie au loup sur sa
# propre documentation fait douter de toute la suite.
if grep -qE "fetch\(\s*['\"][^'\"]*status\.json" "$ROOT/web/lecteur/index.html" 2>/dev/null; then
    fail "l'écran enfant lit encore status.json (fichier mort depuis la session 11) — TICKET-136"
else
    pass "écran enfant : plus de repli vers le fichier d'état mort"
fi
if grep -q 'read_json(STATUS_JSON)' "$ROOT/web/index.php" 2>/dev/null; then
    fail "l'admin lit encore STATUS_JSON (fichier mort) au lieu de battery_stats.json — TICKET-136"
else
    pass "admin : bandeau batterie alimenté par battery_stats.json"
fi

# La fraîcheur doit être exposée : c'est ce qui rend une donnée figée visible.
if grep -q "'stale'" "$ROOT/web/index.php" 2>/dev/null; then
    pass "admin : fraîcheur de la mesure batterie exposée (garde anti-donnée figée)"
else
    warn "admin : la fraîcheur n'est plus exposée — une donnée figée redeviendrait invisible (TICKET-136)"
fi

# ── TICKET-127 — le code servi est-il bien celui du disque ? ───────────────
# Bug surveillé : le 2026-08-17, une modification d'index.html a été déployée,
# vérifiée sur le disque et validée par un smoke test vert… sans jamais
# atteindre l'écran. Chromium servait sa copie en cache. Aucun contrôle ne
# pouvait le voir, parce que tous regardaient le FICHIER, jamais la RÉPONSE.
# C'est la pire famille de panne du projet : on croit avoir corrigé, et c'est
# l'ancien code qui tourne — ce qui fausse en plus tous les diagnostics
# suivants.
if md5_disque=$(md5sum "$IDX" 2>/dev/null | cut -d' ' -f1); then
    md5_servi=$(curl -sf --max-time 5 http://localhost/lecteur/ | md5sum | cut -d' ' -f1)
    if [ -z "$md5_servi" ] || [ "$md5_servi" = "d41d8cd98f00b204e9800998ecf8427e" ]; then
        warn "page /lecteur/ illisible depuis le serveur — contrôle du cache sauté (Apache tourne-t-il ?)"
    elif [ "$md5_disque" = "$md5_servi" ]; then
        pass "la page servie est identique au fichier du disque (pas de cache serveur)"
    else
        fail "la page SERVIE diffère du fichier sur le disque — une modification d'index.html n'atteindrait pas l'écran"
        echo "     → disque=$md5_disque  servi=$md5_servi"
    fi
fi

# En-tête anti-cache (TICKET-127). C'est le filet qui empêche Chromium de
# resservir un ancien index.html depuis son profil, que `restart-kiosk.sh`
# ne remet pas à zéro (pas de --incognito).
# ⚠️ La conf Apache est encadrée par <IfModule headers_module> : si mod_headers
# n'est pas chargé, elle ne s'applique PAS et Apache démarre quand même. Le
# silence est donc possible — d'où ce contrôle, qui lit la réponse réelle.
entetes=$(curl -sf -I --max-time 5 http://localhost/lecteur/ 2>/dev/null)
if [ -z "$entetes" ]; then
    warn "en-têtes de /lecteur/ illisibles — contrôle anti-cache sauté"
elif echo "$entetes" | grep -qi "cache-control:.*no-store"; then
    pass "en-tête anti-cache présent sur la page du lecteur"
else
    warn "pas de Cache-Control no-store sur /lecteur/ — Chromium peut resservir un ancien index.html (TICKET-127)"
    echo "     → sudo a2enmod headers && sudo a2enconf apache-hechicero-nocache && sudo systemctl reload apache2"
fi

# ── TICKET-127 — le battement de cœur est-il armé ? ────────────────────────
if grep -q "setInterval(kioskHeartbeat, KIOSK_BEAT_MS)" "$IDX"; then
    pass "battement de cœur du kiosque armé"
else
    fail "setInterval(kioskHeartbeat, ...) absent — un gel de la page redeviendrait indétectable"
fi

# ── Zone Z4 — le battement ne doit JAMAIS réarmer le timer de veille ───────
# Bug surveillé : TICKET-102. `checkParentalTime` tournait toutes les 30 s et
# appelait resetSleepTimer() à chaque passage ; comme 30 s < sleep_delay, le
# compte à rebours d'inactivité était perpétuellement repoussé et l'écran de
# veille ne pouvait JAMAIS s'afficher. Le battement de TICKET-127 tourne à
# 15 s, soit encore plus vite : s'il touchait au timer, il rejouerait le même
# bug en pire. On vérifie donc le corps de la fonction, pas le fichier entier.
corps_beat=$(sed -n '/^function kioskHeartbeat()/,/^}/p' "$IDX")
if [ -z "$corps_beat" ]; then
    warn "fonction kioskHeartbeat() introuvable sous sa forme attendue — contrôle Z4 sauté"
elif echo "$corps_beat" | grep -qE "resetSleepTimer|clearTimeout|sleepTimer"; then
    fail "kioskHeartbeat() touche au timer de veille — l'écran ne s'endormira plus (piège TICKET-102)"
else
    pass "battement sans effet sur le timer de veille (zone Z4 préservée)"
fi

# ── TICKET-138 — UNE SEULE veille, pas deux minuteries désaccordées ────────
# Bug surveillé : l'overlay JS lisait `sleep_delay` (60 s) pendant que swayidle
# éteignait la dalle sur `screen_off_delay` (600 s). Entre les deux, 540 s de
# DALLE ALLUMÉE SUR PAGE NOIRE — signalé plusieurs fois comme une panne, cherché
# comme un gel du kiosque, introuvable parce que rien n'était cassé : c'est le
# DÉSACCORD des deux réglages qui produisait le symptôme.
if grep -q "Number(cfg.screen_off_delay ?? cfg.sleep_delay" "$IDX"; then
    pass "veille unique : l'overlay dérive du délai d'extinction physique (TICKET-138)"
else
    fail "l'overlay de veille ne dérive plus de screen_off_delay — retour à deux minuteries désaccordées (TICKET-138)"
fi

# ⚠️ CE GARDE DEVIENT CRITIQUE AVEC TICKET-138. Toutes les boucles périodiques
# de l'IHM (30 s au plus long) sont maintenant BEAUCOUP plus courtes que le
# délai de veille passé de 60 s à 600 s. Si `applySleepConfig` réarmait le timer
# à chaque passage au lieu de le faire seulement quand la config a changé, la
# veille ne se déclencherait PLUS JAMAIS — exactement TICKET-102, mais avec une
# marge dix fois plus favorable au bug qu'avant.
corps_apply=$(sed -n '/^function applySleepConfig(cfg)/,/^}/p' "$IDX")
if [ -z "$corps_apply" ]; then
    warn "applySleepConfig() introuvable sous sa forme attendue — contrôle Z4 sauté"
elif echo "$corps_apply" | grep -q "} else if (changed) {"; then
    pass "applySleepConfig ne réarme le timer que si la config a changé (piège TICKET-102)"
else
    fail "applySleepConfig réarme le timer sans garde 'changed' — la veille ne se déclenchera plus (TICKET-102/138)"
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

# ── TICKET-127 — le kiosque exécute-t-il encore du JavaScript ? ────────────
# Bug surveillé : le 2026-08-17 la page a cessé d'exécuter du JS entre 07:52:48
# et 07:57:48, en laissant l'overlay de veille comme dernière image peinte.
# Écran noir figé, tactile sans effet — et TOUS les indicateurs habituels au
# vert : mpd actif, boutons actifs, `wlr-randr` annonçant `Enabled: yes`, aucun
# `off` dans screen_dpms.log. Aucun test existant ne pouvait voir ça, parce
# qu'aucun ne regardait la page elle-même.
# Le battement de cœur est le seul témoin : une page vivante écrit
# data/kiosk_heartbeat.json toutes les 15 s.
if ou=$(service_actif kiosk_freeze_watch "kiosk_freeze_watch.py"); then
    pass "kiosk_freeze_watch actif ($ou)"
else
    warn "kiosk_freeze_watch inactif — un gel du kiosque ne laisserait aucune trace (TICKET-127)"
fi

BEAT="$ROOT/data/kiosk_heartbeat.json"
if [ -f "$BEAT" ]; then
    # `date -r` donne le mtime : ça mesure la dernière écriture réussie, pas ce
    # que la page prétend. Indépendant du contenu du fichier, donc increvable.
    age=$(( $(date +%s) - $(date -r "$BEAT" +%s) ))
    ecran=$(sed -n 's/.*"screen":"\([^"]*\)".*/\1/p' "$BEAT")
    veille=$(sed -n 's/.*"overlay":\([a-z]*\).*/\1/p' "$BEAT")
    if [ "$age" -le 60 ]; then
        pass "kiosque vivant — battement il y a ${age}s (écran=${ecran:-?} veille=${veille:-?})"
    else
        fail "kiosque MUET depuis ${age}s — la page n'exécute plus de JS (TICKET-127)"
        echo "     → l'écran est probablement noir et figé sur sa dernière image"
        echo "     → relevé : tail -60 data/kiosk_freeze.log"
        echo "     → sortie de panne sans reboot : ./scripts/screen_dpms.sh rescue"
    fi
else
    warn "data/kiosk_heartbeat.json absent — la page n'a jamais battu depuis l'ajout du traceur (recharger le kiosque)"
fi

# ── TICKET-123 — les boutons signalent-ils l'activité au compositeur ? ─────
# Bug surveillé : swayidle n'observe que les entrées Wayland et ne voit jamais
# les boutons GPIO, lus par un processus Python. Après un réveil non tactile
# il reste bloqué en état « déjà expiré » et l'écran ne s'éteint plus jamais.
# Prouvé le 2026-08-17 : réveil par le bouton antenne, puis 25 min sans
# toucher l'écran, aucun `off`.
# ⚠️ Rappel de la zone Z4 : appeler screen_dpms.sh on ne remplace PAS un
# événement d'entrée. Tout nouveau déclencheur de réveil doit signaler
# l'activité, sinon il fige de nouveau le cycle de veille.
if grep -q "signaler_activite()" "$ROOT/scripts/buttons_daemon.py"; then
    pass "boutons : activité signalée au compositeur (swayidle peut réarmer)"
else
    fail "buttons_daemon ne signale plus l'activité — l'écran ne s'éteindra plus après un réveil bouton (TICKET-123)"
fi

if [ -x /usr/bin/wtype ]; then
    pass "wtype installé (frappe virtuelle pour le signal d'activité)"
else
    fail "wtype absent — le signal d'activité est inopérant. sudo apt install wtype (TICKET-123)"
fi

# ── TICKET-121 — le chemin d'arrêt critique est-il exécutable ? ────────────
# Bug surveillé : `battery_watchdog.py` appelait `sudo shutdown`, alors que son
# unité porte NoNewPrivileges=true — qui casse sudo. L'appel échouait EN
# SILENCE (run_command avale l'exception et le code de retour), donc la
# protection contre la décharge profonde n'a jamais tourné depuis le
# durcissement de juillet 2026. Et le seul chemin qui l'aurait révélé,
# --simulate-critical, était cassé lui aussi (dépaquetage à 2 valeurs d'un
# tuple de 3). Les deux défauts se couvraient l'un l'autre.
# Ce contrôle est statique et sans effet de bord : il ne déclenche AUCUN arrêt.
if grep -nE '^[^#]*run_command\(\["sudo"' "$ROOT/scripts/battery_watchdog.py" >/dev/null 2>&1; then
    fail "battery_watchdog.py appelle encore sudo — NoNewPrivileges le bloquera en silence (TICKET-121)"
else
    pass "arrêt critique sans sudo (compatible NoNewPrivileges)"
fi

if grep -q "level, _, _ = read_level" "$ROOT/scripts/battery_watchdog.py"; then
    pass "--simulate-critical dépaquette bien les 3 valeurs de read_level()"
else
    fail "dépaquetage de read_level() incorrect — --simulate-critical lèvera un ValueError (TICKET-121)"
fi

# Un test ne doit pas laisser de fausse trace : `--simulate-critical` écrivait
# shutdown_reason=battery_critical, et le bureau d'admin affichait alors une
# reprise après coupure batterie qui n'avait jamais eu lieu.
if grep -q '"simulation" if simulate else "battery_critical"' "$ROOT/scripts/battery_watchdog.py"; then
    pass "--simulate-critical marque last_session.json comme simulation (pas de fausse reprise admin)"
else
    fail "--simulate-critical écrit shutdown_reason=battery_critical — l'admin croira à une vraie coupure (TICKET-121)"
fi

# Et l'état actuel du fichier : une simulation oubliée doit être signalée.
LS="$ROOT/data/last_session.json"
if [ -f "$LS" ] && grep -q '"shutdown_reason": *"battery_critical"' "$LS" 2>/dev/null; then
    quand=$(sed -n 's/.*"shutdown_at": *"\([^"]*\)".*/\1/p' "$LS")
    warn "dernière coupure sur batterie critique : $quand — l'admin proposera une reprise"
    echo "     → normal après une vraie décharge complète ; effacer une fois vu : rm data/last_session.json"
fi

# ── TICKET-133 — détection charge/décharge et clôture de cycle ─────────────
# Bugs surveillés, tous deux mesurés le 2026-08-17 :
#  · un SEUIL UNIQUE à 300 mA classait « décharge » des courants POSITIFS
#    (+257 mA, +17 mA en phase CV), fabriquant de faux cycles où le niveau
#    montait — et ce booléen sert au watchdog pour décider d'éteindre le Pi ;
#  · toute décharge profonde se termine par l'arrêt d'urgence, donc la bascule
#    vers la charge n'est vue qu'au redémarrage : le point bas enregistré était
#    celui d'APRÈS rebranchement (28 % au lieu de 15 %), et la durée incluait
#    le temps hors tension. Les cycles les plus instructifs étaient les plus faux.
# Tests unitaires : aucun capteur, aucun fichier, aucun réseau.
BATT_TEST="$ROOT/scripts/test_batterie.py"
if [ -f "$BATT_TEST" ]; then
    if sortie_batt=$(timeout 15 python3 "$BATT_TEST" 2>&1); then
        pass "batterie : $(echo "$sortie_batt" | grep -c '^  ok') test(s) unitaire(s) OK (TICKET-133)"
    else
        fail "batterie : test unitaire en échec — détection de charge ou clôture de cycle fausse"
        echo "$sortie_batt" | grep -A2 'ÉCHEC' | head -12 | sed 's/^/     /'
    fi
else
    warn "test_batterie.py absent — détection charge/décharge non couverte (TICKET-133)"
fi

# Le seuil unique ne doit pas revenir : c'est lui qui classait « décharge »
# des courants positifs.
if grep -q 'charging = current_ma > float(config.get("charge_threshold_ma"' "$ROOT/scripts/battery_common.py" 2>/dev/null; then
    fail "battery_common : retour au seuil unique — les courants positifs faibles seront classés décharge (TICKET-133)"
else
    pass "détection de charge par le signe du courant + bande morte (TICKET-133)"
fi

# ── TICKET-141 — l'enregistreur doit rester capable de voir un plateau ──────
# Bug surveillé : `should_record_point()` n'écrivait que sur CHANGEMENT, donc
# rien pendant un plateau. Mesuré le 2026-08-19 : des trous de 38, 147 et 49 min
# dans la courbe de charge, et 3 points seulement pendant les 6 h 53 d'arrêt de
# charge nocturne. Le courant n'était même pas un critère d'enregistrement.
# Les tests unitaires (§ ci-dessus) couvrent le comportement ; ici on garde les
# trois constantes, parce que les remettre à zéro rendrait l'enregistreur
# aveugle sans faire échouer un seul test de logique.
manques=""
for const in RECORD_FLOOR_SECONDS CURRENT_DELTA_MA RETENTION_FULL_DAYS; do
    grep -qE "^${const} *= *[1-9]" "$ROOT/scripts/battery_tracker.py" 2>/dev/null || manques="$manques $const"
done
if [ -n "$manques" ]; then
    fail "battery_tracker : constante(s) d'enregistrement manquante(s) ou nulle(s) :$manques — retour à l'enregistreur aveugle (TICKET-141)"
else
    pass "enregistreur batterie : cadence plancher, critère de courant et rétention en place (TICKET-141)"
fi

# La purge doit rester appelée par le tracker lui-même. Confiée à un cron, elle
# finirait par ne plus tourner sans que personne ne s'en aperçoive — et on ne le
# découvrirait qu'une fois la carte SD usée par la réécriture d'un fichier obèse.
if grep -q "purge_history(history)" "$ROOT/scripts/battery_tracker.py" 2>/dev/null; then
    pass "purge d'historique automatique, dans le tracker (TICKET-141)"
else
    fail "battery_tracker : purge_history() n'est plus appelée — l'historique grossira sans fin (TICKET-141)"
fi

# L'historique ne doit PAS être réécrit à chaque tour de boucle : 196 ko × 1440
# réécritures = 283 Mo/jour d'écriture SD pour un fichier le plus souvent
# inchangé. `battery_stats.json`, lui, doit continuer d'être écrit à chaque tour
# (son last_updated est le seul témoin d'un arrêt du tracker).
if grep -q "write_history=bool(recorded or purges)" "$ROOT/scripts/battery_tracker.py" 2>/dev/null; then
    pass "historique batterie écrit seulement s'il a changé (TICKET-141)"
else
    warn "battery_tracker : l'historique semble réécrit inconditionnellement — usure inutile de la carte SD (TICKET-141)"
fi

# ── TICKET-137 — la table mesurée et sa compensation vont PAR PAIRE ─────────
# Bug surveillé, et c'est le plus vicieux de la zone Z8 : `_LIPO_TABLE` contient
# désormais des tensions À VIDE. Si quelqu'un retire la compensation d'affaissement
# en gardant la table (ou règle la résistance à zéro), le niveau devient PLUS FAUX
# qu'avec l'ancienne courbe générique — et rien ne plante. Un podcast en cours
# ferait perdre 8 points instantanément.
# ⚠️ CE GARDE A DÉJÀ CRIÉ AU LOUP (2026-08-21). Il cherchait la chaîne littérale
# `percent_from_voltage(tension_a_vide(`, que le refactor de TICKET-142 a scindée
# en deux lignes : échec rapporté alors que rien n'était cassé. **Un test qui
# vérifie une FORME DE CODE casse au premier remaniement légitime, et fait
# douter de toute la suite.** La vérification de fond est désormais un test de
# COMPORTEMENT dans test_batterie.py (§16, capteur fictif : on regarde ce que
# read_sensor_snapshot RÉPOND). Ici on ne garde qu'un contrôle de présence, lâche
# et donc stable.
corps_snap=$(sed -n '/^def read_sensor_snapshot(/,/^def /p' "$ROOT/scripts/battery_common.py")
if echo "$corps_snap" | grep -q "tension_a_vide("; then
    pass "table batterie lue via la compensation d'affaissement (TICKET-137)"
else
    fail "battery_common : la table (tensions À VIDE) est lue sans tension_a_vide() — niveau plus faux qu'avant (TICKET-137)"
fi

# La résistance interne doit être non nulle dans la config EFFECTIVE (défauts
# fusionnés compris) : à zéro, la compensation est neutre et le piège ci-dessus
# se referme silencieusement.
r_eff=$(cd "$ROOT/scripts" && timeout 10 python3 -c "
from battery_common import load_config
print(load_config().get('internal_resistance_ohm', 0))
" 2>/dev/null)
if [ -n "$r_eff" ] && python3 -c "import sys; sys.exit(0 if float('$r_eff') > 0 else 1)" 2>/dev/null; then
    pass "résistance interne active — ${r_eff} Ω (compensation d'affaissement effective)"
else
    fail "résistance interne nulle ou absente (${r_eff:-?}) — la table en tensions à vide sera lue sur du brut (TICKET-137)"
fi

# ── TICKET-139 — lisser avant de décider ───────────────────────────────────
# Bug surveillé : un creux isolé à −210 mA franchissait la bande morte et faisait
# annoncer « charge arrêtée » ; 72 mV de tension faisaient sauter le niveau de 9
# points en 4 min. La rafale + médiane absorbe ces valeurs aberrantes. Elle est
# aussi le PRÉALABLE à la nouvelle table, qui étale 20 points sur 40 mV en haut
# de courbe et amplifie donc le bruit d'environ sept fois.
if grep -q "mediane(tensions)" "$ROOT/scripts/battery_common.py" 2>/dev/null \
   && grep -qE "^ *\"sensor_burst_samples\": *[2-9]" "$ROOT/scripts/battery_common.py" 2>/dev/null; then
    pass "lecture capteur lissée par médiane sur rafale (TICKET-139)"
else
    fail "battery_common : retour à l'échantillon unique — un creux isolé fera basculer l'état (TICKET-139)"
fi

# ── TICKET-142 — comptage coulométrique au-dessus du plateau ───────────────
# Bug surveillé : le 2026-08-21, la table mesurée annonçait 86 % là où la
# batterie était réellement à 78 %. Entre 75 et 85 %, 10 mV valent 10 points :
# aucune table de tension ne peut répondre dans cette bande.
if grep -q "level, nouvel_ancrage = niveau_coulometrique(" "$ROOT/scripts/battery_common.py" 2>/dev/null \
   && grep -q "coulomb_state=coulomb_state" "$ROOT/scripts/battery_tracker.py" 2>/dev/null; then
    pass "comptage coulométrique branché au-dessus du plateau (TICKET-142)"
else
    fail "battery_common : comptage coulométrique absent — le niveau sera faux de ~9 points au-dessus de 70 % (TICKET-142)"
fi

# L'ancrage doit être PERSISTÉ, sinon il repart de la table à chaque
# redémarrage du service et le comptage ne sert à rien.
if grep -q '"coulomb_state": sample.get("coulomb_state")' "$ROOT/scripts/battery_tracker.py" 2>/dev/null; then
    pass "ancrage du comptage persisté dans battery_stats.json (TICKET-142)"
else
    fail "battery_tracker : l'ancrage n'est plus persisté — le comptage repart de zéro à chaque redémarrage (TICKET-142)"
fi

# ⚠️ LE GARDE-FOU CENTRAL. Un compteur qui intègre à travers un trou de mesure
# dérive SANS LE DIRE — c'est le pire défaut possible pour ce mécanisme, et la
# seule raison pour laquelle il est acceptable ici est qu'il s'invalide.
if grep -qE "^_COULOMB_TROU_MAX_S *= *[1-9]" "$ROOT/scripts/battery_common.py" 2>/dev/null \
   && grep -q "ecoule_s > _COULOMB_TROU_MAX_S" "$ROOT/scripts/battery_common.py" 2>/dev/null; then
    pass "comptage invalidé après un trou de mesure (garde anti-dérive silencieuse, TICKET-142)"
else
    fail "battery_common : le comptage n'est plus invalidé sur trou de mesure — dérive silencieuse (TICKET-142)"
fi

# ⚠️ L'ancrage sur batterie pleine doit exiger la TENSION autant que le courant.
# Les arrêts de charge anormaux du TICKET-140 ont un courant quasi nul (0,91 mA
# pendant des heures) à **54 % et 70 %** : un critère fondé sur le seul courant
# les prendrait pour une batterie pleine et afficherait 100 % avec un tiers de
# l'énergie — pile le genre de faux positif qui trompe sans rien casser.
if grep -q "voc_v >= seuil_v and abs(current_ma) <= seuil_i" "$ROOT/scripts/battery_common.py" 2>/dev/null; then
    pass "batterie pleine reconnue sur tension ET courant (TICKET-142/140)"
else
    fail "battery_common : critère de batterie pleine affaibli — un arrêt de charge anormal serait pris pour un plein (TICKET-142)"
fi

# Capacité utile non nulle dans la config EFFECTIVE : à zéro, le mécanisme se
# neutralise et on retombe silencieusement sur la table fausse.
cap_eff=$(cd "$ROOT/scripts" && timeout 10 python3 -c "
from battery_common import load_config
print(load_config().get('battery_usable_mah', 0))
" 2>/dev/null)
if [ -n "$cap_eff" ] && python3 -c "import sys; sys.exit(0 if float('$cap_eff') > 0 else 1)" 2>/dev/null; then
    pass "capacité utile configurée — ${cap_eff} mAh (comptage effectif)"
else
    fail "capacité utile nulle ou absente (${cap_eff:-?}) — le comptage se neutralise (TICKET-142)"
fi

# ── TICKET-143 — l'outil de recalibration doit refuser de se tromper ───────
# Bug surveillé : `recalibrer_table_batterie.py` retenait le cycle EN COURS
# (`level_end` absent → profondeur 96 au lieu de 30) et proposait une table
# plaçant 85 points de pourcentage sur 80 mV. **Il n'a pas planté** : il a rendu
# un tableau bien formaté et plausible, avec son propre avertissement rassurant.
# Un outil d'analyse qui se trompe sans échouer est plus dangereux qu'un outil
# cassé, parce qu'on le croit.
RECAL="$ROOT/scripts/recalibrer_table_batterie.py"
if [ ! -f "$RECAL" ]; then
    warn "recalibrer_table_batterie.py absent — recalibration non outillée (TICKET-143)"
else
    manque=""
    # Les deux filtres sans lesquels la comparaison n'a aucun sens.
    grep -q 'c.get("discharge_end")' "$RECAL" || manque="$manque cycles-clos"
    grep -q "depart < v_plein" "$RECAL" || manque="$manque depart-plein"
    # La leçon de TICKET-142 : le verdict doit se prononcer EN POINTS, pas en mV.
    grep -q "DESACCORD_MAX_POINTS" "$RECAL" || manque="$manque verdict-en-points"
    # Et il ne doit plus dépendre d'un chemin absolu.
    # Ancré hors commentaire (`^[^#]*`) : sans ça, une simple mention du vieux
    # chemin dans la doc du script ferait échouer ce garde. Défaut trouvé par
    # l'audit du 2026-08-21, AVANT qu'il ne morde.
    grep -qE '^[^#]*"/home/thomas/hechicero' "$RECAL" && manque="$manque chemin-en-dur"
    if [ -n "$manque" ]; then
        fail "recalibrer_table_batterie.py : garde-fou(s) manquant(s) :$manque — l'outil peut à nouveau proposer une table absurde (TICKET-143)"
    else
        pass "outil de recalibration : cycles clos, départ plein, verdict en points (TICKET-143)"
    fi
fi

# ── TICKET-132 — un avertissement permanent qui ne signale rien ────────────
# Chaque appui play/pause produisait un WARNING alors que l'action marchait :
# radio.php répond du HTML pour `pause`, et json.loads() échouait dessus. Un
# journal saturé de faux avertissements fait ignorer les vrais.
# Test de COMPORTEMENT (urlopen remplacé), pas un grep — voir §5bis du registre.
BTN_TEST="$ROOT/scripts/test_boutons.py"
if [ -f "$BTN_TEST" ]; then
    if sortie_btn=$(timeout 15 python3 "$BTN_TEST" 2>&1); then
        pass "boutons : $(echo "$sortie_btn" | grep -c '^  ok') test(s) unitaire(s) OK (TICKET-132)"
    else
        fail "boutons : http_get() confond « pas du JSON » et « en panne » (TICKET-132)"
        echo "$sortie_btn" | grep -A2 'ÉCHEC' | head -8 | sed 's/^/     /'
    fi
else
    warn "test_boutons.py absent — bruit de journal des boutons non couvert (TICKET-132)"
fi

# ── TICKET-128 — ce registre arme un DÉMARRAGE, pas une coupure ────────────
# Ce test annonçait « coupure matérielle du HAT disponible ». C'était faux :
# écrire 0x55 dans 0x2d/0x01 arme le **redémarrage automatique à la remise sous
# tension** (doc Waveshare, section « Boot When Power Applied »). L'erreur venait
# d'une lecture de la démo constructeur, qui écrit ce registre juste avant
# `poweroff` — la séquence ressemblait à un armement de coupure.
# --check-hat ne fait qu'une DÉTECTION, aucune écriture : lançable en écoute.
if hat=$(timeout 10 python3 "$ROOT/scripts/battery_watchdog.py" --check-hat 2>&1 | head -1); then
    pass "redémarrage auto au rebranchement disponible — $hat"
else
    warn "MCU du HAT 0x2d non détecté — l'arrêt d'urgence fonctionnera, mais la radio ne repartira pas seule au rebranchement ($hat)"
fi

# Le nom de la fonction ne doit plus jamais affirmer une coupure : c'est ce
# mensonge, répété dans le journal à chaque arrêt d'urgence, qui a fait croire
# pendant quatre jours que les cellules étaient protégées après l'arrêt de l'OS.
# ⚠️ ANCRÉ SUR DU CODE, PAS SUR UNE MENTION. Un `grep` nu sur le nom trouve
# aussi la docstring qui explique le renommage — ce garde a échoué exactement
# comme ça à sa première exécution, et c'était la TROISIÈME fois dans la même
# journée (voir aussi `status.json` et la compensation d'affaissement).
# Règle : un garde-fou se prononce sur une DÉFINITION ou un APPEL, jamais sur
# l'apparition d'une chaîne. Sinon il finit par échouer sur sa propre
# explication, et un test qui crie au loup sur sa documentation fait douter de
# toute la suite.
if grep -qE "^[[:space:]]*(def )?arm_hat_power_cutoff\(" "$ROOT/scripts/battery_watchdog.py" 2>/dev/null; then
    fail "battery_watchdog : arm_hat_power_cutoff() de retour — ce registre arme un DÉMARRAGE, pas une coupure (TICKET-128)"
else
    pass "registre 0x2d nommé pour ce qu'il fait : armer le démarrage (TICKET-128)"
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

# ── Garde TICKET-121 : généralisation à TOUT `Requires=` ───────────────────
# Le contrôle ci-dessus ne cherchait que `Requires=mpd`. L'audit du
# 2026-08-17 a trouvé `Requires=NetworkManager.service` dans
# wifi_roam.service : même piège, autre dépendance. Un redémarrage de
# NetworkManager — c'est-à-dire précisément quand le Wi-Fi va mal — arrêtait
# le service chargé du roaming, sans le relancer.
# Panne LATENTE : ce service n'est pas encore installé, elle se serait
# déclenchée des semaines plus tard sans lien apparent.
# Aucune unité de ce projet n'a de raison légitime de porter `Requires=` :
# tout ce qu'on écrit doit survivre à la panne de ce dont il dépend.
tous_requires=$(grep -l '^Requires=' "$ROOT"/scripts/*.service 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')
if [ -z "$tous_requires" ]; then
    pass "aucun Requires= dans les unités du dépôt (tout survit à sa dépendance)"
else
    fail "Requires= dans : $tous_requires → l'arrêt de la dépendance les tuera. Utiliser Wants="
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
    # ⚠️ MESSAGE CORRIGÉ LE 2026-08-17 (TICKET-125). L'ancien affirmait deux
    # choses fausses, et un mauvais conseil dans un test de garde est pire
    # qu'aucun conseil :
    #   1. « le son de démarrage est concerné » — FAUX. play_chime.py passe par
    #      MPD (« via MPD, pas de click DAC »), donc par eqhp/eqcasque.
    #   2. « Remplacer par CARD=sndrpihifiberry » — FAUX et dangereux. La carte
    #      numérotée était la 2, c'est-à-dire le DAC USB du CASQUE (`Audio`) ;
    #      la HiFiBerry est la 3. Suivre ce conseil aurait déplacé la sortie par
    #      défaut des écouteurs vers les haut-parleurs — un changement de
    #      comportement déguisé en correction.
    # Vérifié : aucun script du projet n'emprunte le périphérique par défaut
    # (tous les amixer précisent -D). L'enjeu se limite à un aplay tapé à la
    # main — d'où un `warn` et non un `fail`.
    if grep -qE '^\s*(slave\.pcm\s+"hw:[0-9]|card\s+[0-9])' /etc/asound.conf; then
        warn "asound.conf : le périphérique par DÉFAUT est numéroté — les numéros dérivent d'un boot à l'autre, et c'est un périphérique USB (débranchable). Installer scripts/asound.conf, qui le nomme CARD=Audio (= le DAC du casque, comportement inchangé)"
    else
        pass "asound.conf : périphérique par défaut référencé par nom"
    fi

    # Garde TICKET-125 : la copie versionnée doit rester alignée sur /etc.
    # Sans ce contrôle, on corrige le dépôt en croyant avoir corrigé le Pi —
    # exactement le piège de la zone Z12 (le fichier n'est pas ce qui tourne).
    if [ -r "$ROOT/scripts/asound.conf" ]; then
        if diff -q <(grep -vE '^\s*#|^\s*$' /etc/asound.conf) \
                   <(grep -vE '^\s*#|^\s*$' "$ROOT/scripts/asound.conf") >/dev/null 2>&1; then
            pass "asound.conf : /etc identique à la copie du dépôt"
        else
            warn "asound.conf : /etc DIFFÈRE de scripts/asound.conf — l'un des deux n'est pas à jour"
            echo "     → comparer : diff /etc/asound.conf scripts/asound.conf"
        fi
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

titre "9. Intégrité du catalogue (zone Z9)"

# Dette de test de la zone Z9, ouverte depuis la création du registre :
# `check_integrity.py` existait mais n'était lancé qu'à la main, donc jamais.
# Il vérifie que chaque épisode de data.json a bien son fichier audio et son
# image, repère les fichiers orphelins (présents sur le disque, absents du
# catalogue), et détecte les .mp3 qui sont en réalité des .m4a — un piège qui
# fait échouer la lecture sans message clair.
#
# Sûr à lancer pendant que l'enfant écoute : le script est en LECTURE SEULE,
# il ne supprime ni ne réécrit rien. Codes de sortie : 0 sain, 1 avertissement,
# 2 erreur.
#
# ⚠️ Sous `timeout` : le script parcourt tous les dossiers audio et lit des
# en-têtes de fichiers. Sur un gros catalogue il peut s'allonger, et le smoke
# test doit rester sous la minute — sinon il ne sera plus lancé du tout.
INTEG="$ROOT/scripts/rss_ingest/check_integrity.py"
if [ ! -f "$INTEG" ]; then
    warn "check_integrity.py introuvable — intégrité du catalogue non vérifiée"
else
    sortie_integ=$(timeout 25 python3 "$INTEG" 2>&1)
    code_integ=$?

    if [ "$code_integ" -eq 124 ]; then
        warn "check_integrity.py a dépassé 25 s — catalogue non vérifié (le lancer à la main)"
    elif [ "$code_integ" -gt 2 ]; then
        warn "check_integrity.py a échoué (code $code_integ) — $(echo "$sortie_integ" | tail -1)"
    else
        # ⚠️ TRI PAR GRAVITÉ RÉELLE — corrigé le 2026-08-17, le jour même de
        # l'intégration. `check_integrity.py` classe en ERR **deux situations
        # opposées**, et les confondre rend le test inutile :
        #
        #   (a) un épisode du catalogue dont le FICHIER manque
        #       → l'enfant appuie et rien ne joue. C'est cassé. `fail`.
        #   (b) des fichiers présents sur le disque dont le catalogue ne parle
        #       pas ("absent de data.json") → le podcast a été retiré de
        #       data/podcasts.json et ses fichiers sont restés. Rien n'est
        #       cassé : c'est du poids mort sur la carte SD. `warn`.
        #
        # Au premier lancement, (b) produisait 359 lignes ERR pour 9 podcasts
        # retirés de la config — la suite entière passait au rouge alors que
        # tout fonctionnait. Un `fail` qui crie au loup fait ignorer les vrais.
        err_reelles=$(echo "$sortie_integ" | grep '^\[ERR\]' | grep -v 'absent de data.json')
        pods_hors_catalogue=$(echo "$sortie_integ" | grep '^\[ERR\].*podcast absent de data.json' \
                              | sed 's/^\[ERR\] \([^ ]*\) .*/\1/' | sort -u)
        n_reelles=$(echo "$err_reelles" | grep -c . )
        n_pods=$(echo "$pods_hors_catalogue" | grep -c . )
        n_orph=$(echo "$sortie_integ" | grep -c 'orphelin\|orpheline')

        if [ "$n_reelles" -gt 0 ]; then
            fail "catalogue : $n_reelles problème(s) RÉEL(S) — des épisodes du catalogue n'ont pas leur fichier"
            echo "$err_reelles" | head -10 | sed 's/^/     /'
        else
            pass "catalogue : aucun épisode cassé (tous les fichiers référencés sont présents)"
        fi

        if [ "$n_pods" -gt 0 ]; then
            warn "$n_pods podcast(s) sur disque mais hors catalogue — fichiers inutiles, rien de cassé"
            echo "$pods_hors_catalogue" | sed 's/^/     · /'
            echo "     → retirés de data/podcasts.json ; leurs fichiers occupent la carte SD"
            echo "     → place occupée : du -sh podcasts/{$(echo "$pods_hors_catalogue" | paste -sd,)}"
        fi

        # ── TICKET-130 — la config a-t-elle perdu des podcasts ? ───────────
        # Bug surveillé : entre le 2026-08-03 et le 2026-08-05, NEUF podcasts
        # ont disparu de data/podcasts.json alors que tous leurs fichiers
        # restaient sur le disque. Personne ne l'a vu pendant deux semaines —
        # c'est le silence qui a coûté cher, pas la disparition.
        #
        # Cause : data/podcasts.json est **suivi par git ET réécrit par l'IHM
        # admin**. Les neuf avaient été ajoutés depuis l'admin, donc jamais
        # committés ; une opération git les a ramenés à l'état HEAD.
        # Décision de Thomas (2026-08-17) : on garde le fichier versionné.
        # Ce contrôle est donc le garde-fou qui rend le choix tenable — il
        # transforme deux semaines de silence en une ligne de sortie.
        #
        # ⚠️ `warn` et non `fail` : un écart peut être légitime (podcast retiré
        # volontairement dont on n'a pas encore effacé le dossier). Ce qui
        # compte est qu'il soit VU.
        n_cfg=$(python3 -c "import json;print(len(json.load(open('$ROOT/data/podcasts.json')).get('podcasts',[])))" 2>/dev/null)
        n_dirs=$(find "$ROOT/podcasts" -maxdepth 2 -name meta.json 2>/dev/null | wc -l)
        if [ -z "$n_cfg" ]; then
            warn "data/podcasts.json illisible — impossible de vérifier la perte de podcasts (TICKET-130)"
        elif [ "$n_cfg" -eq "$n_dirs" ]; then
            pass "config et disque d'accord — $n_cfg podcast(s) configurés, autant sur disque"
        elif [ "$n_cfg" -lt "$n_dirs" ]; then
            warn "$((n_dirs - n_cfg)) podcast(s) sur disque absent(s) de la config — disparition possible (TICKET-130)"
            echo "     → data/podcasts.json = $n_cfg entrées · podcasts/ = $n_dirs dossiers"
            echo "     → restauration : python3 scripts/restore_lost_podcasts.py"
            echo "     → penser à committer data/podcasts.json après tout ajout depuis l'admin"
        else
            warn "$((n_cfg - n_dirs)) podcast(s) configuré(s) sans dossier sur disque — jamais ingérés ?"
        fi

        # ── TICKET-131 — ordre des épisodes ────────────────────────────────
        # Bug surveillé : les Explorateurs de l'Univers s'affichaient à
        # l'envers (8, 7, 6 … 1). Cause dans les DONNÉES, pas dans le tri :
        # l'éditeur a publié les neuf épisodes à une minute d'écart en
        # commençant par le dernier, donc les dates sont l'inverse de l'ordre
        # narratif.
        # Le correctif touche l'ordre d'affichage de TOUS les podcasts, d'où
        # de vrais tests unitaires : ils prouvent que le cas cassé est réparé
        # ET qu'Olma (numérotation qui redémarre) et Tina (saisons) n'ont pas
        # bougé. Aucun effet de bord : ni fichier, ni réseau.
        TRI="$ROOT/scripts/rss_ingest/test_tri_episodes.py"
        if [ -f "$TRI" ]; then
            if sortie_tri=$(timeout 15 python3 "$TRI" 2>&1); then
                pass "tri des épisodes : $(echo "$sortie_tri" | grep -c '^  ok') test(s) unitaire(s) OK (TICKET-131)"
            else
                fail "tri des épisodes : test unitaire en échec — l'ordre d'affichage est faux quelque part"
                echo "$sortie_tri" | grep -A2 'ÉCHEC' | head -12 | sed 's/^/     /'
            fi
        else
            warn "test_tri_episodes.py absent — l'ordre des épisodes n'est plus couvert (TICKET-131)"
        fi

        if [ "$n_orph" -gt 0 ]; then
            warn "$n_orph fichier(s) orphelin(s) — surtout des bandes-annonces écartées par TICKET-104/105"
            echo "     → liste : python3 scripts/rss_ingest/check_integrity.py | grep orphelin"
        fi
    fi
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
