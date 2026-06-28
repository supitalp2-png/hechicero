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
| `hechicero-idle.service` | `~/.config/systemd/user/` | Extinction écran après inactivité (swayidle + wlopm) | ✅ (user) |
| RSS cron 3h | `crontab -l` | Ingestion podcasts | ✅ |
| `hechicero-kiosk.service` | `~/.config/systemd/user/` | Relancer Chromium (optionnel) | selon config |

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

Appelle `scripts/idle_screen.sh` qui relit `web/lecteur/config.json` toutes les 30 secondes. Si `screen_off_enabled` ou `screen_off_delay` change, swayidle est relancé avec le nouveau délai. Éteint l'écran via `wlopm --off \*`, le rallume au premier toucher/clic via `wlopm --on \*`.

Dépendances : `swayidle`, `wlopm` (paquets apt). `WAYLAND_DISPLAY=wayland-0`, `XDG_RUNTIME_DIR=/run/user/1000`.

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
