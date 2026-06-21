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
- `index.html` : point d’entrée
- `app.js` : logique de navigation et commandes MPD
- `style.css` : styles adaptés au tactile
- `data.json` : catalogue local (radios + podcasts)
- `images/` : jaquettes
- `audio/` : fichiers audio statiques (démos)

### 3.2 Rôle des fichiers
- **index.html** : squelette minimal, tout est injecté par JS
- **app.js** :
  - charge `data.json`
  - génère les écrans (Accueil → Radios → Podcasts → Lecture)
  - gère les événements tactiles
  - envoie les commandes à MPD
- **data.json** :
  - généré automatiquement par le backend
  - contient radios, podcasts, images, chemins audio

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

## 6. Navigation du Lecteur
1. **Accueil**
   - Bouton “Radios”
   - Bouton “Podcasts”

2. **Radios**
   - Liste des radios issues de `data.json`
   - Lecture via MPD (flux web)

3. **Podcasts**
   - Liste des podcasts
   - Liste des épisodes

4. **Lecture**
   - Titre
   - Jaquette
   - Bouton Play/Pause
   - Barre de progression (optionnelle)
   - Bouton Retour

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

## 12. État réel au 2026-06-21

### Implémenté et validé
- Navigation fonctionnelle bout en bout : accueil → podcasts → épisodes → lecteur
- Filtre par langue via drapeaux FR/🇨🇴 (champ `langue` dans `data.json`)
- Commandes MPD via `radio.php` (play, pause, playfile, volup, voldown, status)
- Paramètre `path` uniformisé dans toutes les actions (`playTrack`, `playBtn`)
- Polling MPD conditionnel (actif uniquement sur l'écran lecteur)
- Bouton webradio France Inter fonctionnel
- Mode kiosque Chromium au boot (TICKET-039 ✅)
- Pipeline RSS → téléchargement → conversion M4A→MP3 → MPD opérationnel
- `normalize_path` retourne des URI absolues `file://` (compatible MPD music_directory `/var/lib/mpd/music`)

### Batterie (TICKET-051) — fix appliqué, non validé
- `navigator.getBattery()` bloqué dans Chromium sur Pi — l'icône batterie restait absente
- Fix (2026-06-21) : dual approach dans `index.html`
  - essaie `getBattery` d'abord ; fallback : `fetch('../status.json')` toutes les 30 s
  - champ lu : `d.percent` (validé : `{"percent": 91, "voltage_v": 4.1, "current_ma": 19, ...}`)
  - détection charge : `d.state.toLowerCase().includes('charge') && !includes('sur batterie')`
- **À valider** sur le Pi à la prochaine session

### En cours — Refonte visuelle (TICKET-050)
Architecture cible validée le 2026-06-21 :
- **5 écrans** : Accueil → Podcasts+Radio → [Catalogue radio | Épisodes] → Lecteur
- **Viewport** : 1024×600 px paysage (écran CUQI 7 pouces IPS)
- **Design** : dark mode, accent cyan (#00c8ff), accent radio ambre (#c8a050), boutons arrondis
- **Écran lecteur** : layout splitté (jaquette gauche 45% / contrôles droite 55%)
- **Barre de statut** : heure + batterie (fallback status.json) + indicateur charge
- **Boutons retour** : pill-shaped, 36px, suffisamment grands pour usage tactile enfant
- Tickets couverts : 041 (tap image), 042 (progress bar), 043 (reprise localStorage), 044 (flèches épisodes), 045 (jaquettes ≥ 300px)

### Non implémenté
- Contenu ES dans `data.json` (TICKET-004)
- Catalogue radios hispanófonas (TICKET-050, phase 2)
- `app.js` : code mort à supprimer (TICKET-040)
- Images podcasts non affichées (TICKET-049)

---

## 13. Évolutions prévues
- Refonte visuelle complète `index.html` (TICKET-050) ← EN COURS
- Images podcasts : jaquette podcast + image par épisode dans `data.json` (TICKET-049)
- Contenu ES : podcasts en espagnol (TICKET-004)
- Script d'intégrité audio/images/data.json (TICKET-048)
- Carrousel pour les jaquettes (TICKET-047)
- Favoris (TICKET-046)
- Animations simples (fade, slide) (TICKET-037)
- Son de confirmation au lancement (TICKET-023)
- Support des boutons physiques (GPIO)

---

## 14. Référence UX
Les règles UX détaillées sont décrites dans :
- `docs/25-UX_GUIDELINES.md`
- dossier `UX Design/` (vision, personas, parcours, spécifications)

Le lecteur doit rester strictement aligné avec ces documents.
