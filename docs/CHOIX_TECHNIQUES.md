# Choix Techniques et Matériels — Hechicero

## 1. Architecture générale

Hechicero repose sur une séparation stricte entre trois briques :

### 🔹 Backend (technique)
- Monitoring batterie (INA219 + Python)
- Ingestion des podcasts (RSS → fichiers locaux)
- Génération des données statiques (`data.json`)
- Services systemd pour les tâches récurrentes

### 🔹 Lecteur embarqué (IHM enfant)
- HTML/CSS/JS pur
- Fonctionne **sans réseau**
- Lit les flux MPD (webradio + fichiers locaux)
- S’appuie sur un fichier unique : `web/lecteur/data.json`

### 🔹 Interface d’administration (IHM adulte)
- Accessible via le réseau local
- Apache + PHP
- Affiche : statut batterie, logs, configuration

---

## 2. Architecture matérielle

### 🔹 Raspberry Pi 5
- OS : Raspberry Pi OS Lite
- Rôle : cœur du système

### 🔹 Waveshare UPS HAT (D)
- Mesure tension / courant via INA219
- Permet un shutdown propre

### 🔹 HiFiBerry Amp4
- Ampli audio intégré
- Sortie directe vers enceintes passives
- Compatible ALSA → MPD

### 🔹 Écran tactile
- Interface enfant type Merlin
- Navigation simple (haut / bas / gauche / droite / OK)

---

## 3. Architecture audio

### 🔹 Chaîne audio complète
Lecteur HTML/JS → MPD → ALSA → HiFiBerry Amp4 → Enceintes

### 🔹 Justification des choix
- **MPD** : robuste, léger, parfait pour un système embarqué
- **ALSA** : standard Linux, compatible Amp4
- **Flux web + fichiers locaux** : même API MPD
- **Séparation totale** entre IHM et moteur audio

---

## 4. Organisation des répertoires

Arborescence réelle du projet :

~/hechicero/
│
├── data/              # config.json, fichiers internes
├── docs/              # documentation du projet
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

### 🔹 Règles de cohérence
- **Les fichiers téléchargés (podcasts)** vont dans `~/hechicero/podcasts/`
- **Le lecteur** ne contient que :
  - les images statiques
  - les fichiers audio *manuels* (ex : démo)
  - `data.json`
- **Le backend** met à jour `data.json` mais ne touche jamais à l’IHM

---

## 5. Approche logicielle

### 🔹 Monitoring batterie
- Python + INA219
- Service systemd
- Écriture atomique dans `web/status.json`

### 🔹 Ingestion podcasts
- Script Python
- Lecture RSS
- Téléchargement des épisodes
- Génération de `meta.json`
- Mise à jour de `web/lecteur/data.json`

### 🔹 Lecteur embarqué
- HTML minimal
- JavaScript pur
- Navigation dynamique
- Compatible tactile
- Fonctionne hors-ligne

### 🔹 Admin Web
- Apache + PHP
- Accès local uniquement
- Affiche statut batterie + logs

---

## 6. Bonnes pratiques retenues

### 🔹 Permissions
- `web/status.json` : `644`, propriétaire `thomas:www-data`
- Dossiers traversables (`x`) pour les services systemd
- `scripts/` en lecture seule pour www-data

### 🔹 Écriture atomique
- Toujours écrire dans `*.tmp` puis `mv`

### 🔹 Robustesse
- Services systemd avec :
  - Restart=always
  - TimeoutStopSec
  - ProtectSystem=full (à durcir plus tard)

### 🔹 IHM Lecteur
- Données statiques (JSON)
- Pas de dépendance réseau
- Architecture évolutive (future IHM native possible)

---

## 7. Références

- Waveshare UPS HAT (D) — Documentation officielle  
  https://www.waveshare.com/wiki/UPS_HAT_(D)

- HiFiBerry Amp4 — Documentation officielle  
  https://www.hifiberry.com/docs/hardware/amp4/

- MPD (Music Player Daemon) — Documentation  
  https://www.musicpd.org/doc/html/user.html

- ALSA — Documentation  
  https://www.alsa-project.org/wiki/Main_Page

- Apache HTTP Server — Documentation  
  https://httpd.apache.org/docs/

- Radio France — Flux MP3  
  https://www.radiofrance.fr
