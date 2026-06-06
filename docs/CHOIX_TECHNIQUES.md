# Choix Techniques et Matériels

## Organisation (Architecture)
- **Déploiement** : Utilisation de liens symboliques pour servir le site web depuis le répertoire projet `~/hechicero/web` vers `/var/www/html`. Cela permet de garder le code source en dehors des dossiers système Apache.

## Matériel
- **Cerveau** : Raspberry Pi 5 (OS Lite).
- **Alimentation** : Waveshare UPS HAT (D).
- **Audio** : HiFiBerry Amp4 (pour piloter 2 HP passifs Bose).

## Approche Logicielle
- **Monitoring** : Scripts Python (accès I2C via SMBus) + Export texte.
- **Audio** : Music Player Daemon (MPD) pour gérer la lecture.
- **Web** : Architecture LAMP (Linux, Apache, PHP) légère.

## Organisation des répertoires
- `~/hechicero/scripts/` : Scripts de traitement (logique).
- `~/hechicero/data/` : Fichiers de données temporaires (échanges).
- `~/hechicero/web/` : Interface publique (Apache).


## Références (RTFM)
- [Waveshare UPS HAT (D) Wiki](https://www.waveshare.com/wiki/UPS_HAT_(D))
- [HiFiBerry Amp4 Documentation](https://www.hifiberry.com/docs/)