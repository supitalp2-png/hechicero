# Choix Techniques et Matériels

## Organisation (Architecture)

- **Déploiement Web** : le dossier `~/hechicero/web` est servi par Apache via un alias.  
  L’interface d’administration et le lecteur embarqué sont deux briques distinctes :
  - `web/index.php` → Dashboard Admin (statut batterie, logs, config)
  - `web/lecteur/` → Lecteur embarqué HTML/JS (IHM du Raspberry Pi)

- **Séparation des responsabilités** :
  - L’Admin est accessible via le réseau local.
  - Le Lecteur est autonome, prévu pour l’écran tactile du RPi.
  - Les deux briques ne partagent que des fichiers statiques (ex. `status.json`).

- **Structure du lecteur** :
  - `lecteur/index.html` → squelette minimal
  - `lecteur/app.js` → moteur d’IHM (navigation, rendu, logique)
  - `lecteur/data.json` → base de données locale (podcasts, chapitres)
  - `lecteur/images/` → jaquettes
  - `lecteur/audio/` → fichiers audio

## Matériel

- **Cerveau** : Raspberry Pi 5 (OS Lite).
- **Alimentation** : Waveshare UPS HAT (D).
- **Audio** : HiFiBerry Amp4 (2 HP passifs Bose).
- **Écran** : écran tactile (IHM type Merlin).


      Choix du HiFiBerry Amp4 comme sortie audio matérielle
      Justification : ampli intégré, qualité, simplicité, support ALSA
      Choix de MPD comme moteur audio :
      robuste
      contrôlable en HTTP / TCP
      compatible avec ton lecteur HTML/JS
      parfait pour un système embarqué
      Architecture audio :
      HTML/JS → API MPD → ALSA → HiFiBerry Amp4 → enceintes


## Approche Logicielle

- **Monitoring** : script Python (`get_status.py`) exécuté en service systemd.  
  Écrit périodiquement `web/status.json` (format JSON strict).

- **Paramétrage** : `config.json` (seuils batterie, intervalle backend).

- **Audio** : Music Player Daemon (MPD) pour lecture fiable et contrôlable.

- **Web** : LAMP (Apache + PHP) pour simplicité locale et compatibilité RPi.

- **Lecteur embarqué** :
  - HTML/CSS minimal
  - JavaScript pur (sans framework)
  - Données locales via `data.json`
  - Navigation générée dynamiquement (pas de pages multiples)
  - Architecture compatible avec une future migration vers une IHM native

## Organisation des répertoires

- `~/hechicero/scripts/` : scripts Python (ex. `get_status.py`).
- `~/hechicero/data/` : fichiers temporaires (shutdown_pending, config).
- `~/hechicero/web/` : interface web (admin + lecteur).
- `~/hechicero/web/lecteur/` : lecteur embarqué autonome.

## Bonnes pratiques retenues

- **Permissions** :
  - Dossiers parents traversables (`x`) pour l’utilisateur du service.
  - `status.json` en `644`, propriétaire `thomas:www-data`.

- **Écriture atomique** :
  - Écrire dans `status.json.tmp` puis `mv` → `status.json`.

- **Isolation** :
  - Utilisateur système `hechicero` recommandé pour la production.

- **IHM Lecteur** :
  - Données statiques (JSON) pour éviter dépendances réseau.
  - Architecture incrémentale : MVP simple → carrousel plus tard.
  - Séparation stricte entre logique (JS) et données (JSON).

## Références

- [Waveshare UPS HAT (D) Wiki](https://www.waveshare.com/wiki/UPS_HAT_(D))
- [HiFiBerry Amp4 Documentation](https://www.hifiberry.com/docs/)
