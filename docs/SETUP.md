# Setup Hechicero - Reconstruction du Système

## 1. Installation des dépendances de base
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-smbus i2c-tools git apache2 php

## 2. Configuration I2C
# Activer I2C via raspi-config
sudo raspi-config # (Interfacing Options -> I2C -> Enable)

## 3. Gestion du serveur Web (TODO: À migrer vers /web)
# Actuellement lié à la racine du projet
sudo rm -rf /var/www/html
sudo ln -s /home/thomas/hechicero/web /var/www/html
sudo chown -R www-data:www-data /home/thomas/hechicero/web