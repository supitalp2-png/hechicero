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

> `app.js` est présent dans le dépôt mais est du code mort (TICKET-040 — à supprimer).
> `style.css` n’existe plus, les styles sont intégrés dans `index.html`.

### 3.2 Rôle des fichiers
- **index.html** : contient toute la logique — chargement de `data.json`, rendu des 5 écrans, événements tactiles, commandes MPD
- **data.json** : généré automatiquement par le backend (`writer.py`), jamais modifié par le lecteur
- **config.json** : configuration avancée lue au démarrage du lecteur (via `radio.php?action=parental_status`)

Format de `config.json` :
```json
{
  "speakers_max": 80,
  "headphones_max": 60,
  "chime_enabled": true,
  "chime_volume": 15,
  "sleep_enabled": true,
  "sleep_delay": 300,
  "sleep_mode": "dim"
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
- Son de démarrage (chime) : accord C4–G4–C5–E5 via Web Audio API, sans fichier audio — `playStartupChime(volume)` (TICKET-023 ✅)
  - Config : `chime_enabled` / `chime_volume` dans `web/lecteur/config.json`
  - ⚠️ À tester sur Pi : Chromium peut bloquer l'AudioContext sans interaction préalable (fallback `touchstart` documenté dans `brief-session-next.md`)
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
- Barre de statut : heure + batterie (fallback `status.json`) + indicateur charge (TICKET-052 ✅)
- Reprise automatique de la position de lecture via `localStorage` (TICKET-043 ✅)
- Barre de progression + scrubbing tactile (TICKET-042 ✅)
- Appui sur la jaquette player = pause/lecture via overlay (TICKET-041 ✅)
- Flèches ⏮⏭ épisode précédent/suivant dans le player (TICKET-044 ✅)
- Barres de progression synchronisation en temps réel dans l'IHM parent (TICKET-063 ✅)
- Volume logiciel MPD depuis l'IHM enfant (TICKET-034 ✅)
- Webradio en premier dans la grille (TICKET-060 ✅)
- Enchainement automatique épisodes : détection transition `play → stop` via `lastMpdState` (TICKET-069 ✅)
- Tracking SQLite : `tracking.php` + `startTracking()` / `endTracking()` / progress toutes les 60 s (TICKET-055 ✅)

### Architecture technique
- `index.html` : fichier unique (HTML + CSS + JS)
- Viewport : 1024×600 px paysage (CUQI 7" IPS)
- Dark mode, accent cyan `#00c8ff`, accent radio ambre `#c8a050`
- Cover podcasts : `web/lecteur/images/{id}.jpg` (chemin relatif dans `data.json`)
- Audio épisodes : chemin filesystem MPD (`/home/thomas/hechicero/podcasts/{id}/audio/*.mp3`)
- Variables tracking : `trackingId`, `trackingPollCount`, `lastElapsed`, `lastMpdState`

### Non implémenté (tickets ouverts)
- Bug mini-lecteur : affiche la radio au lieu du podcast en cours (TICKET-072)
- Contrôle parental : grille horaire + verrou langue (TICKET-071)
- Durées des épisodes via ffprobe (TICKET-059)
- Son de confirmation / retour visuel au choix (TICKET-023)
- Contenu ES complet dans `data.json` (TICKET-004)
- `app.js` : code mort à supprimer (TICKET-040)

---

## 13. Évolutions prévues
- Durées épisodes via `ffprobe` (TICKET-059)
- Script d'intégrité audio/images/data.json (TICKET-048)
- Carrousel pour les jaquettes (TICKET-047)
- Favoris (TICKET-046)
- Animations simples (fade, slide) (TICKET-037)
- Son de confirmation au lancement (TICKET-023)
- Support des boutons physiques (GPIO)
- Série easter egg "Décisions Prises" (TICKET-058)

---

## 14. Référence UX
Les règles UX détaillées sont décrites dans :
- `docs/25-UX_GUIDELINES.md`
- dossier `UX Design/` (vision, personas, parcours, spécifications)

Le lecteur doit rester strictement aligné avec ces documents.
