# Lecteur Embarqué — Projet Hechicero

Ce document décrit la brique “Lecteur embarqué”, l’interface principale destinée à l’enfant.
Il reflète l’état actuel du développement et les choix techniques validés.

---

## 1. Objectif
Fournir une interface tactile simple, robuste et autonome pour écouter :
- des webradios
- des podcasts locaux
- des contenus statiques

Le lecteur doit fonctionner **même sans réseau**, directement sur l’écran tactile du Raspberry Pi.

---

## 2. Principes
- **Simplicité enfant** : grands boutons, navigation claire, zéro texte inutile.
- **Autonomie totale** : aucune dépendance réseau, aucune API externe.
- **Robustesse** : pas d’écriture disque, pas de logique complexe côté client.
- **Séparation stricte** : le lecteur ne dépend pas de l’interface d’administration.
- **Données statiques** : un seul fichier `data.json` comme source de vérité.

---

## 3. Architecture du Lecteur

### 3.1 Structure des fichiers
Le lecteur est localisé dans :
`~/hechicero/web/lecteur/`

Contenu :
- `index.html` : **fichier unique** — HTML + CSS + JS intégrés
- `data.json` : catalogue local (radios + podcasts), généré par le backend
- `images/` : jaquettes podcasts (`{id}.jpg`) et radios (`radio/{id}.jpg`)

> `app.js` et `style.css` sont du code mort — les styles et la logique sont intégrés dans `index.html` (TICKET-040 ✅). Fichiers à supprimer (TICKET-090).

### 3.2 Rôle des fichiers
- **index.html** : contient toute la logique — chargement de `data.json`, rendu des 5 écrans, événements tactiles, commandes MPD
- **data.json** : généré automatiquement par le backend (`writer.py`), jamais modifié par le lecteur
- **config.json** : configuration avancée lue au démarrage du lecteur (via `radio.php?action=parental_status`)

Format de `config.json` :
```json
{
  "volume": {
    "speakers_max": 80,
    "headphones_max": 60
  },
  "chime_enabled": true,
  "chime_volume": 15,
  "sleep_enabled": true,
  "sleep_delay": 300,
  "sleep_mode": "retro_clock",
  "screen_off_enabled": true,
  "screen_off_delay": 600
}
```

Ce fichier est écrit par `web/index.php` (action `save_config`) via écriture atomique. Il ne doit jamais être modifié manuellement.

---

## 4. Fonctionnement sur écran tactile
Le lecteur tourne dans **Chromium**, en mode plein écran.

Décisions récentes :
- utilisation de Raspberry Pi OS **avec bureau**
- affichage direct sur l’écran tactile
- boutons larges et zones cliquables généreuses
- aucune barre d’adresse, aucun élément du navigateur visible

Objectif : une expérience type “Merlin” pour enfant.

---

## 5. Structure de `data.json`
`data.json` est la **source unique** du lecteur.
Il contient :
- la liste des radios
- la liste des podcasts
- les chemins audio locaux
- les images associées

Règles :
- pas d’accents dans les noms de fichiers
- pas d’espaces
- formats autorisés : `.jpg`, `.png`, `.mp3`
- chemins audio des podcasts → `~/hechicero/podcasts/<id>/audio/*.mp3`

---

## 6. Navigation du Lecteur (5 écrans)

```
Accueil (drapeaux FR / 🇨🇴)
   └─→ Grille (podcasts + webradio — filtrés par langue)
          ├─→ Catalogue webradio  →  Player radio (streaming live)
          └─→ Liste épisodes      →  Player podcast (fichier local)
```

1. **Accueil** : deux drapeaux, sélection de la langue active
2. **Grille** : tuile Webradio (toujours en tête) + jaquettes podcasts en grille 2 colonnes
3. **Catalogue webradio** : liste des stations (image + nom + indicateur live animé)
4. **Liste épisodes** : vignette + titre + durée par épisode, scroll tactile, clic = lecture directe
5. **Player** : jaquette (gauche 45%) + titre + barre de progression + Play/Pause + ⏮⏭ (droite 55%) + volume

---

## 7. Intégration MPD
Le lecteur **ne lit pas directement** les fichiers audio.
Il envoie des commandes à MPD :
- `mpc clear`
- `mpc add <url>`
- `mpc play`
- `mpc pause`
- `mpc stop`

MPD gère :
- les flux web
- les fichiers locaux
- les erreurs
- la file d’attente

### Volume logiciel
Obligatoire pour la HiFiBerry Amp4 :
`mixer_type "software"`

→ permet un contrôle du volume depuis l’IHM enfant  
→ évite les niveaux sonores dangereux  

---

## 8. Fonctionnement hors réseau
Le lecteur doit fonctionner **même sans WiFi**.

Garanties :
- `data.json` est local
- MPD lit les fichiers locaux
- les flux web sont optionnels
- aucune dépendance cloud

---

## 9. Sécurité enfant
Le lecteur doit être **100% safe** pour un enfant, même sans supervision.

Règles :
- aucun lien externe  
- aucune navigation libre  
- aucun texte cliquable non prévu  
- aucun menu caché  
- volume logiciel limité (max 80%)  
- aucune possibilité de quitter Chromium  
- aucune commande système exposée  

Objectif : un environnement **fermé**, **prévisible**, **sans risque**.

---

## 10. Contraintes de performance
Pour garantir une expérience fluide :
- pas d’animations lourdes  
- pas de JS bloquant  
- pas de bibliothèques externes  
- pas de CDN  
- images optimisées (≤ 200 KB)  
- DOM minimal  

Le lecteur doit fonctionner **sans lag** sur un Raspberry Pi 5.

---

## 11. Critères d’acceptation
- `data.json` chargé sans erreur  
- jaquettes affichées correctement  
- navigation tactile fluide  
- lecture MPD fonctionnelle (flux + fichiers locaux)  
- lecteur utilisable hors réseau  
- volume logiciel opérationnel  
- respect des règles de sécurité enfant  

---

## 12. État réel au 2026-06-24

### Implémenté et validé
- Son de démarrage (chime) : accord grave C2–G2–C3–G3–E4 via Web Audio API, sans fichier audio — `playStartupChime(volume)` (TICKET-023 ✅)
  - Sine pour les basses (C2/G2/C3), triangle pour les aigus (G3/E4) — deux oscillateurs ±3 cents par note (chorus naturel)
  - Reverb profond (delay 0.35 s, feedback 0.42), attaque 0.4 s, queue 6 s — ambiance orgue/carillon
  - Config : `chime_enabled` / `chime_volume` dans `web/lecteur/config.json`
  - Déclenché au premier `touchstart` après le chargement (contourne la politique autoplay de Chromium)
- Fix screensaver : remplacement de `pointermove` par `pointerdown/touchstart/click` — évite les events fantômes sur Pi
- Navigation 5 écrans fonctionnelle bout en bout (TICKET-050 ✅)
- Filtre par langue via drapeaux FR/🇨🇴 (champ `langue` dans `data.json`)
- Commandes MPD via `radio.php` (play, pause, playfile, volup, voldown, status, seekcur, seekid)
- Polling MPD conditionnel (actif uniquement sur l'écran lecteur)
- Webradio France Inter + Radio Nacional fonctionnelles
- Mode kiosque Chromium au boot (TICKET-039 ✅)
- Pipeline RSS → téléchargement → MPD opérationnel (18 podcasts, 2 radios)
- Jaquettes podcasts dans `web/lecteur/images/{id}.jpg` (accessible Apache) (TICKET-049 ✅)
- Images épisodes dans liste épisodes avec fallback jaquette podcast (TICKET-054 ✅)
- Grille 2 colonnes pour podcasts et épisodes (TICKET-053 ✅)
- Barre de statut : heure + batterie (`/index.php?action=battery_data` → `battery_stats.json`) + indicateur charge (TICKET-052 ✅)
- Reprise automatique de la position de lecture via `localStorage` (TICKET-043 ✅)
- Barre de progression + scrubbing tactile (TICKET-042 ✅)
- Appui sur la jaquette player = pause/lecture via overlay (TICKET-041 ✅)
- Flèches ⏮⏭ épisode précédent/suivant dans le player (TICKET-044 ✅)
- Barres de progression synchronisation en temps réel dans l'IHM parent (TICKET-063 ✅)
- Volume logiciel MPD depuis l'IHM enfant (TICKET-034 ✅)
- Webradio en premier dans la grille (TICKET-060 ✅)
- Enchainement automatique épisodes : détection transition `play → stop` via `lastMpdState` (TICKET-069 ✅)
- Tracking lecture côté serveur via `play_tracker.py` (MPD idle) — source de vérité unique (TICKET-086 ✅)
- Bug mini-lecteur radio corrigé (TICKET-072 ✅)
- Contrôle parental : grille horaire + verrou langue (TICKET-071 ✅)
- Durées épisodes via ffprobe (TICKET-059 ✅)
- Extinction écran automatique : `hechicero-idle.service` + `idle_screen.sh` (session 10 ✅)
- Alertes batterie 30 min / 10 min, popup branchement (TICKET-082 ✅)
- Radios et podcasts mis à jour en temps réel sans redémarrage kiosque (TICKET-100 ✅)
  - PHP : add/edit/delete radio → `sync_radios_to_data_json()` met `data.json` à jour immédiatement
  - PHP : delete_podcast → retrait immédiat de `data.json`
  - PHP : add_podcast → ingest ciblé `--podcast <id>` déclenché en background
  - Lecteur : `openRadioCatalog()` et `goToPodcasts()` rechargent `data.json` à chaque visite
  - Lecteur : `setInterval` 5 min pour config/parental (veille, contrôle parental)
- Bascule sortie audio HP/Casque — TICKET-031 partiel ✅
  - DAC USB KT USB Audio branché sur card 3 ALSA (HiFiBerry = card 2)
  - MPD configuré avec 2 sorties : `My ALSA Device` (hw:2,0) + `Casque USB` (hw:3,0)
  - Bouton pill dans la statusbar (icône haut-parleur / casque SVG, surligné cyan en mode casque)
  - `radio.php` : actions `get_output` / `set_output` (enableoutput/disableoutput MPD 0-indexed)
  - Volume mémorisé par mode (localStorage `hechicero_vol_hp` / `hechicero_vol_casque`, IHM 0–100%)
  - `currentVolumeMax()` retourne `VOLUME_MAX_SPEAKERS` ou `VOLUME_MAX_HEADPHONES` selon `audioMode`
  - Séquence bascule : volume réglé AVANT la bascule MPD (évite le pic sonore)
  - ⚠️ Temporaire : bascule manuelle depuis l'IHM — sera remplacée par détection GPIO LM393

### Architecture technique
- `index.html` : fichier unique (HTML + CSS + JS)
- Viewport : 1024×600 px paysage (CUQI 7" IPS)
- Dark mode, accent cyan `#00c8ff`, accent radio ambre `#c8a050`
- Cover podcasts : `web/lecteur/images/{id}.jpg` (chemin relatif dans `data.json`)
- Audio épisodes : chemin filesystem MPD (`/home/thomas/hechicero/podcasts/{id}/audio/*.mp3`)
- Batterie : `/index.php?action=battery_data` (primaire) → fallback `../status.json` (lecture seule, fichier statique)

### Non implémenté (tickets ouverts)
- Son de confirmation / retour visuel au choix (TICKET-023)
- Contenu ES complet dans `data.json` (TICKET-004)
- Nettoyage fichiers morts : `app.js`, `style.css`, `lecture.html`, `*.bak` (TICKET-090)

---

## 13. Évolutions prévues
- Script d'intégrité audio/images/data.json (TICKET-048)
- Carrousel pour les jaquettes (TICKET-047)
- Favoris (TICKET-046)
- Animations simples (fade, slide) (TICKET-037)
- Son de confirmation au lancement (TICKET-023)
- Support des boutons physiques (GPIO)
- Série easter egg "Décisions Prises" (TICKET-058)
- Limiteur exposition sonore (TICKET-087)

---

## 14. Référence UX
Les règles UX détaillées sont décrites dans :
- `docs/25-UX_GUIDELINES.md`
- dossier `UX Design/` (vision, personas, parcours, spécifications)

Le lecteur doit rester strictement aligné avec ces documents.
