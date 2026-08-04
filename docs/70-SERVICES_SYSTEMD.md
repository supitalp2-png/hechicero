# Services systemd — Projet Hechicero

Ce document centralise tous les services systemd utilisés par le projet Hechicero.
Il décrit :
- les services existants
- leurs rôles
- leurs fichiers `.service` et `.timer`
- les règles de sécurité
- les commandes d’installation et de debug

Objectif : garantir un système **robuste**, **prévisible**, **auto‑récupérant**.

---

## 1. Liste des services

| Service | Fichier | Rôle | Actif |
|---|---|---|---|
| `battery_tracker.service` | `scripts/battery_tracker.service` | Collecte batterie, cycles, estimations | ✅ |
| `battery_watchdog.service` | `scripts/battery_watchdog.service` | Arrêt propre sur batterie critique | ✅ |
| `play_tracker.service` | `scripts/play_tracker.service` | Suivi de lecture MPD (event-driven, idle player mixer) | ✅ |
| `hechicero-idle.service` | `~/.config/systemd/user/` | Extinction écran après inactivité (swayidle + wlr-randr) | ✅ (user) |
| RSS cron 3h | `crontab -l` | Ingestion podcasts | ✅ |
| `hechicero-kiosk.service` | `~/.config/systemd/user/` | Relancer Chromium (optionnel) | non activé, décision Thomas (débug manuel préféré) |
| `button_toggle_test.service` | `scripts/button_toggle_test.service` | Bring-up bouton GPIO test (bascule HP/casque) — TEMPORAIRE | ❌ désactivé, remplacé par `buttons_daemon.service` |
| `buttons_daemon.service` | `scripts/buttons_daemon.service` | Daemon définitif des 9 boutons GPIO (TICKET-091/101) | ✅ |
| `wifi_watch.service` | `scripts/wifi_watch.service` | Logger diagnostic coupures Wi-Fi (TICKET-109) — TEMPORAIRE | ✅ |
| `wifi_roam.service` | `scripts/wifi_roam.service` | Roaming auto multi-AP box/répéteur, hors DFS (TICKET-110) | à installer |
| `audio_eq_apply.service` | `scripts/audio_eq_apply.service` | Réapplique l'égaliseur alsaequal au boot (TICKET-030) | à installer, jamais testé |

> `hechicero-monitor.service` (ancien service batterie basé sur `get_status.py`) — **désactivé session 11**. Remplacé par `battery_tracker.service`. Ne pas réactiver.

---

## 2. Service batterie — battery_tracker

Fichier : `/etc/systemd/system/battery_tracker.service`

```ini
[Unit]
Description=Hechicero Battery Tracker
After=network.target mpd.service

[Service]
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/battery_tracker.py
Restart=on-failure
RestartSec=10
User=thomas

[Install]
WantedBy=multi-user.target
```

### Installation
```bash
sudo cp scripts/battery_tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now battery_tracker
```

### Debug
```bash
systemctl status battery_tracker
journalctl -u battery_tracker -f
cat data/battery_stats.json
```

---

## 3. Service suivi de lecture — play_tracker

Fichier : `/etc/systemd/system/play_tracker.service`

Écoute les événements MPD (`idle player mixer`) en temps réel. Enregistre chaque session de lecture dans `data/tracking.db` (table `play_events`) avec : podcast/radio identifié, durée écoutée, volume moyen, langue.

Avantages vs tracking JS : fonctionne quelle que soit l'interface (PC, Pi, terminal), résistant aux coupures (sessions réparées via `/proc/uptime` au démarrage).

```ini
[Unit]
Description=Hechicero Play Tracker (MPD idle)
After=mpd.service
Requires=mpd.service

[Service]
Type=simple
User=thomas
WorkingDirectory=/home/thomas/hechicero/scripts
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/play_tracker.py
Restart=always
RestartSec=15
```

### Installation
```bash
sudo cp scripts/play_tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now play_tracker
```

### Debug
```bash
systemctl status play_tracker
journalctl -u play_tracker -f
python3 -c "import sqlite3; c=sqlite3.connect('/home/thomas/hechicero/data/tracking.db'); print(c.execute('SELECT id,podcast_id,is_radio,listened_s,volume_pct FROM play_events ORDER BY id DESC LIMIT 5').fetchall())"
```

---

## 4. Service watchdog — battery_watchdog

Fichier : `/etc/systemd/system/battery_watchdog.service`

Surveille le niveau batterie toutes les N secondes. Si le niveau tombe sous `shutdown_threshold_percent` (défini dans `data/config.json`), sauvegarde l'état MPD et déclenche `shutdown -h now`. Tourne en `root` pour avoir le droit d'arrêter le système.

```ini
[Unit]
Description=Hechicero Battery Watchdog
After=battery_tracker.service
Wants=battery_tracker.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/thomas/hechicero/scripts
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/battery_watchdog.py
Restart=always
RestartSec=15
```

### Installation
```bash
sudo cp scripts/battery_watchdog.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now battery_watchdog
```

### Debug
```bash
systemctl status battery_watchdog
journalctl -u battery_watchdog -f
```

---

## 5. Ingestion RSS — Cron nocturne

> ⚠️ L'ingestion RSS est gérée par **cron** (crontab de l'utilisateur `thomas`), pas par un service systemd.  
> Le service/timer ci-dessous est documenté pour référence mais n'est pas activé.

### Cron actif (à 3h du matin)
```
crontab -e  # en tant que thomas
```
Ligne active :
```
0 3 * * * umask 002 && python3 /home/thomas/hechicero/scripts/rss_ingest/ingest.py >> /tmp/hechicero_ingest.log 2>&1
```

`umask 002` garantit que les fichiers créés sont lisibles/modifiables par le groupe `www-data`.

### Vérifier le cron
```
crontab -l
```

### Logs
```
tail -f /tmp/hechicero_ingest.log
```

### Service systemd (non activé — pour référence)
```
[Unit]
Description=Hechicero RSS Ingestion

[Service]
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/rss_ingest/ingest.py
WorkingDirectory=/home/thomas/hechicero/scripts/rss_ingest
User=thomas
Restart=on-failure
```

Timer : `OnBootSec=5min`, `OnUnitActiveSec=6h`

> Si on bascule vers le timer systemd, désactiver le cron pour éviter les conflits.

---

## 6. Service extinction écran — hechicero-idle

Fichier : `~/.config/systemd/user/hechicero-idle.service`

Appelle `scripts/idle_screen.sh` qui relit `web/lecteur/config.json` toutes les 30 secondes. Si `screen_off_enabled` ou `screen_off_delay` change, swayidle est relancé avec le nouveau délai. Éteint/rallume l'écran via `scripts/screen_dpms.sh` (`wlr-randr --output HDMI-A-1 --off`/`--on --preferred`) — **pas `wlopm`** : `wlopm` échoue sur Pi 5 + labwc (`zwlr_output_power_management_v1` non supporté), remplacé par `wlr-randr` le 2026-07-08 (TICKET-102). Le nom de sortie (`HDMI-A-1`) dépend du port physique du Pi 5 — à revérifier via `wlr-randr` si l'écran est un jour rebranché sur l'autre port.

Dépendances : `swayidle`, `wlr-randr` (paquets apt). `WAYLAND_DISPLAY=wayland-0`, `XDG_RUNTIME_DIR=/run/user/1000`.

⚠️ Ce mécanisme (coupure d'écran système, niveau compositeur Wayland) est **indépendant** de l'overlay de veille JS affiché dans `web/lecteur/index.html` (voir `docs/30-LECTEUR.md` §"Écran de veille") — les deux peuvent avoir des bugs distincts, voir `docs/90-BACKLOG.md` TICKET-102.

```ini
[Unit]
Description=Hechicero Screen Idle (éteint écran après inactivité)
After=graphical-session.target

[Service]
ExecStart=/bin/bash /home/thomas/hechicero/scripts/idle_screen.sh
Restart=on-failure
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_RUNTIME_DIR=/run/user/1000

[Install]
WantedBy=default.target
```

### Installation / mise à jour
```bash
cat > ~/.config/systemd/user/hechicero-idle.service << 'EOF'
[Unit]
Description=Hechicero Screen Idle (éteint écran après inactivité)
After=graphical-session.target

[Service]
ExecStart=/bin/bash /home/thomas/hechicero/scripts/idle_screen.sh
Restart=on-failure
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_RUNTIME_DIR=/run/user/1000

[Install]
WantedBy=default.target
EOF
chmod +x ~/hechicero/scripts/idle_screen.sh
systemctl --user daemon-reload
systemctl --user restart hechicero-idle.service
```

### Config (via admin web → Expert → Écran de veille)
- `screen_off_enabled` : true/false
- `screen_off_delay` : 600 / 900 / 1200 / 1800 (secondes)
- Prise en compte dans les 30 secondes sans redémarrage du service.

### Debug
```bash
systemctl --user status hechicero-idle.service
journalctl --user -u hechicero-idle.service -f
```

---

## 7. Service kiosque (optionnel)
Ce service est utilisé uniquement si l’on souhaite relancer Chromium automatiquement.

Fichier : `~/.config/systemd/user/hechicero-kiosk.service`

```
[Unit]
Description=Hechicero Kiosk Mode
After=graphical-session.target

[Service]
ExecStart=/usr/bin/chromium-browser --kiosk --incognito http://localhost/lecteur/
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
```

### Installation
```
systemctl --user daemon-reload
systemctl --user enable --now hechicero-kiosk.service
```

### Debug
```
journalctl --user -u hechicero-kiosk.service -f
```

---

## 7bis. Service test bouton GPIO — button_toggle_test (TEMPORAIRE)

Fichier : `/etc/systemd/system/button_toggle_test.service`

⚠️ **Service de test/bring-up (TICKET-091/031), pas définitif.** Bascule HP/casque à
chaque appui sur un bouton-poussoir câblé en GPIO17 (pull-up, appui = LOW) — ce
comportement lui-même est définitif (bouton physique manuel, détection auto
abandonnée), seul ce script/service précis est temporaire. À remplacer par
`buttons_daemon.service` une fois le câblage des autres boutons terminé (§7ter).
Tourne en `root` : accès GPIO.

```ini
[Unit]
Description=Hechicero Button Toggle Test (bring-up GPIO, TICKET-091/031)
After=network.target mpd.service
Requires=mpd.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/thomas/hechicero/scripts
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/button_toggle_test.py --pin 17
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Installation
```bash
sudo cp scripts/button_toggle_test.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now button_toggle_test
```

### Debug
```bash
systemctl status button_toggle_test
journalctl -u button_toggle_test -f
```

### Désinstallation (une fois remplacé par le service définitif)
```bash
sudo systemctl disable --now button_toggle_test
sudo rm /etc/systemd/system/button_toggle_test.service
sudo systemctl daemon-reload
```

---

## 7ter. Script boutons GPIO définitif — buttons_daemon.py (service actif, TICKET-091/101)

Fichier : `scripts/buttons_daemon.py` — service : `scripts/buttons_daemon.service`

Successeur de `button_toggle_test.service` (§7bis) : un seul daemon qui poll les
9 broches GPIO (17, 23, 27, 5, 6, 13, 16, 12, 25) dans une seule boucle et
dispatche chaque appui vers un handler dédié, au lieu d'un script scopé à une
seule broche. Polling (pas `add_event_detect()`, peu fiable sur Pi 5/RP1),
anti-rebond à trois niveaux, indépendant par broche.

**État au 2026-07-08 (TICKET-101, mapping final confirmé bouton par bouton sur
le boîtier réel) :**
- GPIO25 = source (HP/casque, `handle_hp_casque`) — **pas GPIO17** comme sur la
  breadboard de bring-up du 2026-07-06, sans impact (dispatch logiciel)
- GPIO13 = vol−, GPIO17 = précédent, GPIO12 = play/pause (fusionné), GPIO27 =
  suivant, GPIO5 = vol+
- GPIO16 = favori (TICKET-046, codé le 2026-07-19) — tap = bascule le favori
  sur l'épisode/webradio en cours, maintien = ouvre l'écran dédié favoris
- GPIO23 = bouton isolé antenne — écran Chambre domotique (TICKET-112) :
  toggle ouvre/ferme l'écran + réveille la dalle si en veille DPMS
- GPIO6 = non câblé

Suivant/précédent gèrent le tap-ou-maintien (`TAP_OR_HOLD`) : tap = épisode
suivant/précédent, maintien > `HOLD_THRESHOLD_S` (0.4s) = recherche par pas de
`SEEK_STEP_S` (5s) dans l'épisode en cours (`seek_relative` côté `radio.php`).
Valeurs de départ, **pas encore confirmées par Thomas en usage réel prolongé**.

Service `buttons_daemon.service` créé, installé et actif sur le Pi (confirmé
2026-07-08) — remplace `button_toggle_test.service`, qui doit rester arrêté
(`sudo systemctl stop button_toggle_test`, ne pas réactiver : conflit GPIO
sinon, `lgpio.error: GPIO busy`).

### Installation
```bash
sudo cp scripts/buttons_daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now buttons_daemon.service
```

### ⚠️ Le tube lgpio doit vivre dans `/run`, jamais dans le dépôt (2026-08-04)

La bibliothèque **lgpio** (utilisée par `RPi.GPIO` sur Pi 5) crée un tube nommé
`.lgd-nfy<N>` **dans le répertoire courant du processus** pour la remontée
d'événements GPIO. Tant que `WorkingDirectory` pointait sur `scripts/`, ce tube
atterrissait dans le dépôt — un fichier binaire parasite qu'on finissait par
prendre pour un déchet.

Le vrai problème est ailleurs : depuis le durcissement **TICKET-011**,
`ProtectSystem=strict` et `ProtectHome=read-only` rendent `scripts/`
**non inscriptible** pour ce service. lgpio ne pouvait donc plus créer son tube.
Ça n'a rien cassé pendant deux semaines uniquement parce qu'un `.lgd-nfy0`
créé **avant** le durcissement traînait encore et se laissait simplement ouvrir.
**La panne était armée et invisible.** Le jour où ce fichier a été supprimé
(ménage du dépôt, 2026-08-04), le service est entré en boucle de crash :

```
xCreatePipe: Can't set permissions (436) for .../scripts/.lgd-nfy0, No such file or directory
FileNotFoundError: [Errno 2] No such file or directory: '.lgd-nfy-3'
```

(`-3` n'est pas un numéro de handle mais un code d'erreur retourné par lgpio.)

Correctif retenu — `systemd` fournit le répertoire lui-même :

```ini
RuntimeDirectory=hechicero-buttons
RuntimeDirectoryMode=0750
WorkingDirectory=/run/hechicero-buttons
```

`RuntimeDirectory=` crée `/run/hechicero-buttons` au démarrage, le rend
inscriptible **malgré `ProtectSystem=strict`**, et le nettoie à l'arrêt. Le tube
ne peut plus manquer, ne pollue plus le dépôt, et ne s'écrit plus sur la carte SD.
Le dossier appartient à root en 0750 : `ls` sans `sudo` renvoie
`Permission denied`, c'est normal.

> 🔎 **Le même piège vaut pour les 7 autres services durcis** : si l'un d'eux
> écrit un fichier de travail hors de ses `ReadWritePaths`, il tient peut-être
> debout uniquement grâce à un fichier antérieur au durcissement. À auditer.

### Reste à faire
- Valider en usage réel prolongé `SEEK_STEP_S`/`HOLD_THRESHOLD_S` (suivant/précédent en maintien)
- TICKET-046 (favoris, GPIO16) codé le 2026-07-19, pas encore testé en conditions réelles — voir `docs/90-BACKLOG.md`
- GPIO23 (bouton antenne) = écran Chambre domotique (TICKET-112), plus en réserve

---

## 7quater. Rotation des logs — logrotate (TICKET-010, 2026-07-18)

Ces fichiers de logs applicatifs grossissent indéfiniment sans rotation
native et ne sont pas couverts par journald (car pas issus d'un service
systemd) :

- `/tmp/hechicero_ingest.log` — sortie du cron d'ingestion RSS (§5), un
  ajout par nuit
- `~/hechicero/data/sleep_debug.log` — traceur temporaire écran de veille
  (TICKET-102, `radio.php?action=sleep_log`), un ajout à chaque événement
  côté lecteur (checkParentalTime, resynchro admin…) — toujours en place,
  voir `docs/30-LECTEUR.md`
- `~/hechicero/data/wifi_watch.log` — traceur temporaire coupures Wi-Fi
  (TICKET-109, `wifi_watch.service`), une ligne toutes les 30s — ajouté
  2026-07-18, voir §7quinquies

> Les logs des services systemd (`battery_tracker`, `battery_watchdog`,
> `play_tracker`, `buttons_daemon`, `hechicero-idle`) passent par
> `journalctl` et ont leur propre rétention (`SystemMaxUse` dans
> `/etc/systemd/journald.conf`) — pas concernés par ce ticket, à vérifier
> séparément si l'espace disque de la carte SD devient un jour un problème.

Fichier : `scripts/hechicero-logrotate.conf` (versionné dans le dépôt).

```
/tmp/hechicero_ingest.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 0664 thomas www-data
}

/home/thomas/hechicero/data/sleep_debug.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 0664 www-data www-data
}

# TICKET-109 — logger diagnostic Wi-Fi (wifi_watch.service), temporaire
/home/thomas/hechicero/data/wifi_watch.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 0664 thomas thomas
}
```

`copytruncate` évite d'avoir à signaler le processus écrivain (cron déjà
terminé pour l'un, PHP sans handle persistant pour l'autre) — logrotate
copie puis vide le fichier en place, aucun redémarrage nécessaire.

### Installation
```bash
sudo cp scripts/hechicero-logrotate.conf /etc/logrotate.d/hechicero
sudo logrotate -d /etc/logrotate.d/hechicero   # test à blanc
```

### Debug / forcer une rotation
```bash
sudo logrotate -f /etc/logrotate.d/hechicero
ls -la /tmp/hechicero_ingest.log* /home/thomas/hechicero/data/sleep_debug.log*
```

logrotate est déjà exécuté quotidiennement par le cron.daily standard de
Raspberry Pi OS (paquet `logrotate`, préinstallé) — aucun timer/service
supplémentaire à créer.

---

## 7quinquies. Logger Wi-Fi — wifi_watch (diagnostic temporaire, TICKET-109)

⚠️ **Service de diagnostic, pas définitif.** Instrumentation ajoutée le
2026-07-18 suite aux coupures Wi-Fi récurrentes (épisodes des 15-16-18/07,
voir `docs/90-BACKLOG.md` TICKET-109) — à retirer une fois la cause
confirmée et le correctif validé dans la durée (même logique que le traceur
`sleep_debug.log` de TICKET-102).

Fichier : `scripts/wifi_watch.sh` — service : `scripts/wifi_watch.service`

Toutes les 30 secondes, interroge `iw dev wlan0 link` et ajoute une ligne à
`data/wifi_watch.log` :
- si connecté : horodatage, BSSID, fréquence, signal (dBm), débits rx/tx
- si déconnecté : horodatage + `DISCONNECTED`

Objectif : distinguer une dégradation progressive (atténuation RF /
interférence) d'une chute sèche depuis un signal stable (décision box ou
bug driver) au prochain décrochage, sans dépendre d'un diagnostic a
posteriori basé sur des suppositions.

```ini
[Unit]
Description=Hechicero Wifi Watch (diagnostic temporaire coupures Wi-Fi, TICKET-109)
After=network.target

[Service]
Type=simple
User=thomas
ExecStart=/bin/bash /home/thomas/hechicero/scripts/wifi_watch.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Installation
```bash
sudo cp scripts/wifi_watch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wifi_watch
```

### Debug
```bash
systemctl status wifi_watch
tail -f /home/thomas/hechicero/data/wifi_watch.log
```

### Désinstallation (une fois la cause confirmée et le fix stable)
```bash
sudo systemctl disable --now wifi_watch
sudo rm /etc/systemd/system/wifi_watch.service
sudo systemctl daemon-reload
```

Note : le script cible `wlan0` en dur. En cas de bascule vers un dongle
Wi-Fi USB (`wlan1`, voir TICKET-109), modifier la variable d'interface
dans `wifi_watch.sh` avant de relancer le service.

---

## 7sexies. Roaming automatique multi-AP — wifi_roam (TICKET-110, 2026-07-18)

Hechicero est mobile (bureau/salon). Un répéteur Wi-Fi officiel Free a été
installé — même SSID "El CORAL GOURMET" diffusé par la box ET le répéteur,
chacun avec plusieurs BSSID (2.4GHz + 5GHz). Sans intervention, le Pi reste
figé sur le BSSID épinglé au démarrage (nécessaire depuis TICKET-109
épisode 2 pour éviter le roaming vers un BSSID 5GHz DFS de la box, qui
échoue systématiquement — CAC radar, pas un problème de signal).

Fichier : `scripts/wifi_roam.py` — service : `scripts/wifi_roam.service`

Toutes les 60 secondes : scanne les BSSID diffusant le SSID du projet,
**exclut ceux sur fréquence DFS** (~5250-5725 MHz, canaux 52-140 ETSI —
c'est spécifiquement cette plage qui posait problème, pas la force du
signal), garde le plus fort du reste. Si un autre BSSID que celui en cours
est meilleur d'au moins 8 dB, confirmé sur 2 scans consécutifs (anti-
flapping en zone limite entre pièces), rebascule le BSSID épinglé de la
connexion NetworkManager et reconnecte. Log dans `data/wifi_roam.log`.

```ini
[Unit]
Description=Hechicero Wifi Roam (bascule auto vers le signal le plus fort, hors DFS) - TICKET-110
After=network.target NetworkManager.service
Requires=NetworkManager.service

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/wifi_roam.py
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
```

### Installation
```bash
sudo cp scripts/wifi_roam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wifi_roam
```

### Debug
```bash
systemctl status wifi_roam
tail -f /home/thomas/hechicero/data/wifi_roam.log
```

### Paramètres ajustables (en tête de `wifi_roam.py`)
- `MARGIN_DB` (8) : gain minimum requis pour basculer
- `CONFIRM_COUNT` (2) : scans consécutifs avant bascule
- `INTERVAL_S` (60) : fréquence de scan

Tourne en root (le scan actif `iw scan` nécessite `CAP_NET_ADMIN`).
Coexiste sans conflit avec `wifi_watch.service` (lecture seule, pas
d'action) — les deux peuvent tourner en parallèle.

---

## 7septies. Égaliseur audio — audio_eq_apply (TICKET-030, non testé)

⚠️ **Jamais testé en conditions réelles** — écrit sans accès SSH au Pi. Voir
`docs/20-SETUP_SYSTEME.md` §6.4 pour la config `asound.conf`/`mpd.conf`
préalable (obligatoire, sinon ce service n'a rien à faire).

Fichier : `scripts/audio_eq_apply.py` — service : `scripts/audio_eq_apply.service`

alsaequal (plugin ALSA utilisé pour l'égaliseur, cf. §6.4) ne persiste pas
son état entre deux démarrages — ce service le réapplique une fois au boot
à partir de `data/audio_eq.json` (écrit par l'admin web
`/admin/audio_eq.php`). `Type=oneshot` + `RemainAfterExit=yes` : il tourne
une fois puis reste "actif" pour `systemctl status`, pas un daemon.

```ini
[Unit]
Description=Hechicero Audio EQ Apply (alsaequal, TICKET-030)
After=mpd.service
Requires=mpd.service

[Service]
Type=oneshot
User=thomas
WorkingDirectory=/home/thomas/hechicero/scripts
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/audio_eq_apply.py
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Installation
```bash
sudo cp scripts/audio_eq_apply.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now audio_eq_apply
```

### Debug
```bash
systemctl status audio_eq_apply
journalctl -u audio_eq_apply
python3 ~/hechicero/scripts/audio_eq_apply.py --list-controls
python3 ~/hechicero/scripts/audio_eq_apply.py --dry-run
```

---

## 8. Règles de sécurité systemd
Pour garantir la robustesse :

- tous les services doivent avoir `Restart=always` ou `on-failure`  
- aucun service ne doit tourner en root sauf nécessité absolue  
- `WorkingDirectory` doit être explicite  
- `ProtectSystem=full` recommandé pour les scripts  
- les chemins doivent être absolus  
- les logs doivent être lisibles via `journalctl`  

---

## 9. Invariants systemd
Ces règles ne doivent **jamais** être violées :

- un service ne doit jamais bloquer le boot  
- un service ne doit jamais écrire hors de son dossier  
- un service ne doit jamais supprimer des fichiers audio  
- un service ne doit jamais écraser un JSON valide  
- un service doit toujours redémarrer automatiquement  
- un service doit toujours avoir un `WorkingDirectory` clair  

---

## 10. Tests de validation
### 🔹 Test 1 : reboot complet
```
sudo reboot
```
Attendu :
- service batterie actif  
- timer RSS actif  
- aucun échec systemd  

### 🔹 Test 2 : crash volontaire
```
pkill -f battery_tracker.py
```
Attendu :
- redémarrage automatique de `battery_tracker`  

### 🔹 Test 3 : ingestion manuelle
```bash
python3 ~/hechicero/scripts/rss_ingest/ingest.py
```
Attendu :
- mise à jour des podcasts (voir logs `/tmp/hechicero_ingest.log`)  

---

## 11. Notes
- Tous les services doivent être documentés ici  
- Toute modification doit être testée sur un reboot complet  
- Le système doit rester robuste même en cas de coupure  

---
