# Setup Hechicero - Reconstruction du Système

## 1. Installation des dépendances de base
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-smbus i2c-tools git apache2 php

## 2. Configuration I2C
# Activer I2C via raspi-config
sudo raspi-config # (Interfacing Options -> I2C -> Enable)

## 3. Configuration du serveur Web (Lien symbolique)
# Assure que le dossier source existe
mkdir -p /home/thomas/hechicero/web
# Supprimer le dossier par défaut d'Apache s'il existe
sudo rm -rf /var/www/html
# Créer le lien vers le dossier web du projet (Source -> Destination)
sudo ln -s /home/thomas/hechicero/web /var/www/html
# Donner les droits à l'utilisateur web
sudo chown -R www-data:www-data /home/thomas/hechicero/web
sudo chmod -R 755 /home/thomas/hechicero/web


## 4. Service Monitoring (Systemd)
# Créer /etc/systemd/system/hechicero.service
# Contenu :
# [Unit]
# Description=Service monitoring Hechicero
# [Service]
# ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/get_status.py
# WorkingDirectory=/home/thomas/hechicero/scripts
# Restart=always
# User=thomas
# [Install]
# WantedBy=multi-user.target

# Activation :
sudo systemctl daemon-reload
sudo systemctl enable hechicero
sudo systemctl start hechicero