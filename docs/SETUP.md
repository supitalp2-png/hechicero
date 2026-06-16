Setup Hechicero — Installation & Structure du Système

Ce document décrit l’installation complète du système Hechicero sur un Raspberry Pi 5, ainsi que l’arborescence finale attendue pour garantir un fonctionnement cohérent entre les briques : monitoring, audio, lecteur embarqué, admin locale et ingestion podcasts.

1. Pré-requis système

1.1 Mise à jour du système

sudo apt update && sudo apt upgrade -y

1.2 Paquets nécessaires

sudo apt install -y \
    python3-pip python3-smbus i2c-tools \
    git apache2 php jq \
    mpd mpc

2. Activation du matériel

2.1 Activer I2C (INA219)

sudo raspi-config

Menu → Interface Options → I2C → Enable

2.2 Vérifier la présence du capteur INA219

sudo i2cdetect -y 1

3. Structure du projet

Arborescence attendue :

~/hechicero/
│
├── data/              # config.json, fichiers internes
├── docs/              # documentation
├── podcasts/          # fichiers téléchargés (RSS)
│     └── <podcast_id>/
│          ├── audio/
│          ├── images/
│          └── meta.json
├── scripts/           # scripts Python (monitoring, ingestion)
├── UX Design/         # maquettes, notes UX
└── web/               # interface web (admin + lecteur)
      ├── index.php
      ├── status.json
      └── lecteur/
            ├── index.html
            ├── app.js
            ├── style.css
            ├── data.json
            ├── images/
            └── audio/

3.1 Vérifier l’arborescence

sudo find ~/hechicero -maxdepth 4 -printf "%M %u:%g %p -> %l\n"

4. Configuration MPD (Audio)

4.1 Redémarrer MPD après installation

sudo systemctl restart mpd

4.2 Tester la lecture Webradio

mpc clear
mpc add "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3"
mpc play

Si tu entends la radio → audio OK.

5. Monitoring Batterie (INA219)

5.1 Script Python

Le script scripts/get_status.py :

lit tension / courant via INA219

calcule l’état de la batterie

écrit web/status.json (écriture atomique)

5.2 Service systemd

Fichier /etc/systemd/system/hechicero-status.service :

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

5.3 Activer le service

sudo systemctl daemon-reload
sudo systemctl enable --now hechicero-status.service

5.4 Vérifier le statut

systemctl status hechicero-status.service

6. Interface Web (Admin)

6.1 Apache sert le dossier web/

Le fichier index.php affiche :

statut batterie

tests audio

diagnostics simples

6.2 Vérifier que status.json est lisible

cat ~/hechicero/web/status.json

7. Lecteur embarqué (IHM enfant)

Le lecteur est dans :

~/hechicero/web/lecteur/

Il utilise :

index.html

app.js

style.css

data.json

7.1 Vérifier que data.json existe

ls -l ~/hechicero/web/lecteur/data.json

8. Podcasts (Backend)

8.1 Dossier racine

mkdir -p ~/hechicero/podcasts

8.2 Les sous-dossiers seront créés automatiquement par le script RSS :

~/hechicero/podcasts/<id>/audio/
~/hechicero/podcasts/<id>/images/
~/hechicero/podcasts/<id>/meta.json

8.3 Le backend mettra à jour :

~/hechicero/web/lecteur/data.json

9. Tests rapides

9.1 Tester MPD

mpc clear && mpc add "<url>" && mpc play

9.2 Tester le monitoring

cat ~/hechicero/web/status.json

9.3 Tester l’IHM

Ouvrir dans un navigateur local :

http://<ip_du_rpi>/lecteur/

10. Rappel pour la prochaine étape

Thomas : exécute cette commande et donne-moi le résultat :

ls -1 ~/hechicero/podcasts

Cela me permettra de valider que la brique Podcasts est prête pour l’ingestion RSS.