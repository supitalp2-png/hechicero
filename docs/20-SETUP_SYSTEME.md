# Installation & Setup du Système — Projet Hechicero

Ce document décrit l’installation complète du système Hechicero sur un Raspberry Pi 5, dans sa configuration actuelle.
Il reflète les choix techniques décrits dans `10-CHOIX_TECHNIQUES.md`.

---

## 1. Pré-requis

### 🔹 Matériel
- Raspberry Pi 5
- Carte microSD (32 Go minimum)
- HiFiBerry Amp4
- Écran tactile compatible Raspberry Pi
- Waveshare UPS HAT (D)
- Enceintes passives

### 🔹 OS recommandé
**Raspberry Pi OS avec bureau**
Raisons :
- nécessaire pour Chromium (IHM enfant)
- meilleure compatibilité tactile

---

## 2. Installation du système

### 2.1 Installer Raspberry Pi OS (avec bureau)
Utiliser Raspberry Pi Imager :
- OS : Raspberry Pi OS (32-bit) — Desktop
- Activer SSH si souhaité
- Configurer WiFi (optionnel)

Démarrer le Pi et effectuer les mises à jour :
```
sudo apt update && sudo apt upgrade -y
```

---

## 3. Configuration de l’écran tactile

### 3.1 Vérifier la détection
L’écran doit être reconnu automatiquement par Raspberry Pi OS.

### 3.2 Rotation (si nécessaire)
```
sudo nano /boot/firmware/config.txt
```
Ajouter par exemple :
```
display_lcd_rotate=2
```

### 3.3 Désactiver l’écran de veille
```
sudo raspi-config
```
Menu → Display Options → Screen Blanking → Disable

---

## 4. Installation des dépendances

### 4.1 Paquets système
```
sudo apt install -y \
    mpd mpc \
    apache2 php \
    python3 python3-pip python3-requests python3-feedparser \
    python3-smbus i2c-tools \
    jq git chromium-browser
```

### 4.2 Activer I2C (INA219)
```
sudo raspi-config
```
Menu → Interface Options → I2C → Enable

Vérifier :
```
sudo i2cdetect -y 1
```

---

## 5. Installation du projet Hechicero

### 5.1 Cloner le dépôt
```
cd ~
git clone https://github.com/<ton_repo>/hechicero
```

### 5.2 Arborescence attendue
```
~/hechicero/
├── data/
├── docs/
├── podcasts/
├── scripts/
├── UX Design/
└── web/
```

---

## 6. Configuration MPD

### 6.1 Fichier `/etc/mpd.conf`
Points essentiels :
- utiliser la carte HiFiBerry (`hw:2,0`)
- activer le volume logiciel

Extrait :
```
audio_output {
    type        "alsa"
    name        "HiFiBerry Amp4"
    device      "hw:2,0"
    mixer_type  "software"
}
```

### 6.2 Redémarrer MPD
```
sudo systemctl restart mpd
```

### 6.3 Test audio
```
mpc clear
mpc add "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3"
mpc play
```

---

## 7. Installation du backend (RSS + batterie)

### 7.1 Monitoring batterie
Le script `scripts/get_status.py` :
- lit INA219  
- calcule l’état batterie  
- écrit `web/status.json` (écriture atomique)  

### 7.2 Service systemd batterie
Fichier : `/etc/systemd/system/hechicero-battery.service`

Activer :
```
sudo systemctl daemon-reload
sudo systemctl enable --now hechicero-battery.service
```

### 7.3 Ingestion RSS (service + timer)
Créer `/etc/systemd/system/hechicero-rss.service` :
```
[Unit]
Description=Hechicero RSS Ingestion

[Service]
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/rss_ingest/ingest.py
WorkingDirectory=/home/thomas/hechicero/scripts/rss_ingest
User=thomas
Restart=on-failure
```

Créer `/etc/systemd/system/hechicero-rss.timer` :
```
[Unit]
Description=Run RSS ingestion every 6 hours

[Timer]
OnBootSec=5min
OnUnitActiveSec=6h

[Install]
WantedBy=timers.target
```

Activer :
```
sudo systemctl daemon-reload
sudo systemctl enable --now hechicero-rss.timer
```

---

## 8. Interface Web (Admin)
Servie par Apache dans `~/hechicero/web/`.
Fonctionnalités actuelles :
- statut batterie  
- tests audio  
- diagnostics simples  

---

## 9. Lecteur embarqué (IHM enfant)
Localisé dans :
`~/hechicero/web/lecteur/`

Fonctionne via Chromium en mode plein écran.

Utilise :
- `data.json`  
- MPD local  
→ fonctionne hors réseau  

---

## 10. Mode kiosque (Chromium)
Créer le fichier autostart :
```
mkdir -p ~/.config/autostart
nano ~/.config/autostart/hechicero.desktop
```

Contenu :
```
[Desktop Entry]
Type=Application
Name=Hechicero Lecteur
Exec=chromium-browser --kiosk --incognito http://localhost/lecteur/
```

### Désactiver l’écran de veille (LXDE)
```
sudo sed -i 's/^#xserver-command=.*/xserver-command=X -s 0 -dpms/' /etc/lightdm/lightdm.conf
```

### Relance automatique de Chromium en cas de crash
Option : créer un service systemd utilisateur (non obligatoire).

### 10.4 Cohérence UX
Le mode kiosque doit garantir :
- aucune sortie possible
- affichage immédiat du lecteur
- respect des règles UX définies dans `25-UX_GUIDELINES.md`


---

## 11. Tests de validation

### 🔹 Test MPD
```
mpc status
```

### 🔹 Test batterie
```
cat ~/hechicero/web/status.json
```

### 🔹 Test lecteur
Ouvrir Chromium → `http://localhost/lecteur/`
