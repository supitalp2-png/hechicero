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
- GPIO16 = réserve, pas de fonction décidée
- GPIO23 = favori (bouton isolé antenne) — assigné logiquement mais pas câblé
  côté logiciel, TICKET-046 (favoris) jamais codé
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

### Reste à faire
- Valider en usage réel prolongé `SEEK_STEP_S`/`HOLD_THRESHOLD_S` (suivant/précédent en maintien)
- Décider de l'usage de GPIO16 (réserve)
- Coder TICKET-046 (favoris) pour activer GPIO23

---

## 7quater. Rotation des logs — logrotate (TICKET-010, 2026-07-18)

Deux fichiers de logs applicatifs grossissent indéfiniment sans rotation
native et ne sont pas couverts par journald (car pas issus d'un service
systemd) :

- `/tmp/hechicero_ingest.log` — sortie du cron d'ingestion RSS (§5), un
  ajout par nuit
- `~/hechicero/data/sleep_debug.log` — traceur temporaire écran de veille
  (TICKET-102, `radio.php?action=sleep_log`), un ajout à chaque événement
  côté lecteur (checkParentalTime, resynchro admin…) — toujours en place,
  voir `docs/30-LECTEUR.md`

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
