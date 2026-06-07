# Choix Techniques et Matériels

## Organisation (Architecture)
- **Déploiement** : servir le site web depuis le répertoire projet `~/hechicero/web` via un lien symbolique vers `/var/www/html`. Avantage : code source centralisé dans le home; inconvénient : attention aux permissions des dossiers parents.

## Matériel
- **Cerveau** : Raspberry Pi 5 (OS Lite).
- **Alimentation** : Waveshare UPS HAT (D).
- **Audio** : HiFiBerry Amp4 (pour piloter 2 HP passifs Bose).

## Approche Logicielle
- **Monitoring** : script Python exécuté en tant que service systemd (résilience, restart automatique).
- **Paramétrage** : `config.json` prévu pour rendre intervalle et seuils configurables.
- **Audio** : Music Player Daemon (MPD).
- **Web** : LAMP (Apache + PHP) pour simplicité locale.

## Organisation des répertoires
- `~/hechicero/scripts/` : scripts Python (ex. `get_status.py`).
- `~/hechicero/data/` : fichiers de données temporaires.
- `~/hechicero/web/` : frontend (index.php, assets, status.json).

## Bonnes pratiques retenues
- **Permissions** : dossiers parents doivent être traversables (`x`) pour l’utilisateur du service.
- **Fichiers statiques** : `status.json` en `644` et appartenant à `thomas:www-data` si Apache doit le servir.
- **Écriture atomique** : écrire dans un fichier temporaire puis `rename()` pour éviter lectures partielles.
- **Isolation** : envisager un utilisateur système `hechicero` pour la production.

## Références
- [Waveshare UPS HAT (D) Wiki](https://www.waveshare.com/wiki/UPS_HAT_(D))
- [HiFiBerry Amp4 Documentation](https://www.hifiberry.com/docs/)