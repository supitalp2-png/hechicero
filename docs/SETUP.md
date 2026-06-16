# Setup Hechicero — Installation & Structure du Système

Ce document décrit l’installation complète du système Hechicero sur un Raspberry Pi 5, ainsi que l’arborescence finale attendue pour garantir un fonctionnement cohérent entre les briques : monitoring, audio, lecteur embarqué, admin locale et ingestion podcasts.

---

# 1. Pré-requis système

## 1.1 Mise à jour du système

sudo apt update && sudo apt upgrade -y

## 1.2 Paquets nécessaires

sudo apt install -y \
    python3-feedparser python3-requests \
    python3-smbus i2c-tools \
    git apache2 php jq \
    mpd mpc

---

# 2. Activation du matériel

## 2.1 Activer I2C (INA219)

sudo raspi-config

Menu → Interface Options → I2C → Enable

## 2.2 Vérifier la présence du capteur INA219

sudo i2cdetect -y 1

---

# 3. Structure du projet

Arborescence attendue :

~/hechicero/
│
├── data/
│     ├── podcasts.json        # configuration des flux
│     └── batterie.txt         # interne
│
├── docs/                      # documentation
│
├── podcasts/                  # téléchargements RSS (ignoré par Git)
│     └── <podcast_id>/
│          ├── audio/
│          ├── images/
│          └── meta.json
│
├── scripts/
│     ├── get_status.py        # monitoring batterie
│     └── rss_ingest/          # ingestion RSS
│           ├── ingest.py
│           ├── parser.py
│           ├── downloader.py
│           ├── writer.py
│           ├── utils.py
│           └── models.py
│
├── UX Design/
│
└── web/
      ├── index.php            # admin locale
      ├── status.json          # état batterie
      └── lecteur/
            ├── index.html
            ├── app.js
            ├── style.css
            ├── data.json      # généré automatiquement
            ├── images/
            └── audio/

---

# 4. Configuration MPD (Audio)

## 4.1 Redémarrer MPD

sudo systemctl restart mpd

## 4.2 Tester la lecture Webradio

mpc clear
mpc add "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3"
mpc play

---

# 5. Monitoring Batterie (INA219)

## 5.1 Service systemd

/etc/systemd/system/hechicero-status.service :

[Unit]
Description=Hechicero Battery Monitor
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/get_status.py
Restart=always
User=thomas
WorkingDirectory=/home/thomas/hechicero/scripts
ProtectSystem=full

[Install]
WantedBy=multi-user.target

## 5.2 Activer

sudo systemctl daemon-reload
sudo systemctl enable --now hechicero-status.service

---

# 6. Interface Web (Admin)

Servie par Apache dans ~/hechicero/web/.

Affiche :
- statut batterie
- tests audio
- diagnostics simples

---

# 7. Lecteur embarqué (IHM enfant)

Localisé dans :

~/hechicero/web/lecteur/

Utilise :
- data.json (généré automatiquement)
- MPD pour la lecture

---

# 8. Podcasts (Backend RSS)

## 8.1 Dossier racine

mkdir -p ~/hechicero/podcasts

## 8.2 Le backend crée automatiquement :

~/hechicero/podcasts/<id>/audio/
~/hechicero/podcasts/<id>/images/
~/hechicero/podcasts/<id>/meta.json

## 8.3 Le backend met à jour :

~/hechicero/web/lecteur/data.json

---

# 9. Tests rapides

### MPD
mpc clear && mpc add "<url>" && mpc play

### Monitoring
cat ~/hechicero/web/status.json

### Lecteur
http://<ip_du_rpi>/lecteur/

---

# 10. Prochaine étape

Installer le service systemd pour l’ingestion RSS.
