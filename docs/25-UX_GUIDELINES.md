# UX Guidelines — Projet Hechicero

Ce document synthétise les règles UX essentielles du projet Hechicero.
Il sert de pont entre la vision UX (dossier `UX Design/`) et les briques techniques.

Objectifs :
- garantir une interface enfant simple, magique et robuste
- assurer la cohérence entre UX, lecteur, backend et mode kiosque
- fournir des règles opérationnelles pour toute évolution future

---

## 1. Principes UX fondamentaux

### 🔹 Simplicité enfant
- aucune lecture nécessaire
- navigation par images, flèches, couleurs
- actions principales : appuyer sur l’image, flèches gauche/droite

### 🔹 Magie
- animations légères (agrandissement, fade)
- retour visuel immédiat
- son de confirmation optionnel

### 🔹 Autonomie
- l’enfant doit pouvoir tout faire seul
- aucune action dangereuse
- aucune sortie possible du mode kiosque

### 🔹 Bilinguisme
- choix de langue via deux drapeaux (🇫🇷 / 🇨🇴)
- filtrage immédiat des contenus

---

## 2. Règles d’or de l’IHM enfant

### 🔹 Écran d’accueil
- deux drapeaux uniquement
- animation courte au lancement

### 🔹 Liste des contenus
- grandes jaquettes (≥ 300×300 px)
- navigation par **menu** : tap sur la jaquette = ouverture directe ✅ validé persona enfant
- flèches directionnelles (haut/bas/gauche/droite) : **non retenu** — le menu tactile suffit

### 🔹 Écran de lecture
- grande image centrale
- barre de progression visible
- appui sur image = pause/lecture
- flèches gauche/droite = épisode précédent/suivant

### 🔹 Reprise automatique
- la position de lecture doit être restaurée

---

## 3. Règles UX pour l’IHM parent

### 🔹 Parent technophile
- tableau de bord complet
- logs, monitoring, état système
- gestion avancée des flux
- simulation de l’IHM enfant

### 🔹 Parent non‑technophile
- interface ultra simple
- “Ajouter un podcast” → coller un lien
- messages clairs, non techniques
- aucune action dangereuse

### 🔹 Dashboard analytics (`/dashboard.php`)
- Graphique FR/ES par jour (style Kibana)
- Camembert répartition par moment de la journée (Matin / Après-midi / Soir / Nuit)
- Funnel de complétion (abandon → épisode terminé)
- Heatmap écoute semaine × heure
- Top épisodes rejoués
- Card streak (jours consécutifs d’écoute)
- Données issues de `tracking.php` (SQLite `play_events`)

### 🔹 Contrôle parental (`/index.php` section dédiée)
- Interrupteur global on/off
- Grille horaire 7 jours × 7 créneaux (0–7h et 22–24h toujours bloqués)
- Verrou par langue : désactiver FR ou ES → drapeau grisé dans le lecteur
- Configuration **uniquement depuis l’admin web** — jamais depuis l’écran tactile
- Comportement fin de plage : l’épisode en cours se termine, puis stop + retour accueil
- Config stockée dans `data/parental.json` (écriture atomique)

---

## 4. Contraintes UX techniques

### 🔹 Performance
- temps de réponse < 200 ms
- animations légères uniquement

### 🔹 Robustesse
- aucune erreur visible pour l’enfant
- aucune dépendance réseau

### 🔹 Sécurité enfant
- aucune sortie du mode kiosque
- aucun lien externe
- volume logiciel limité (max 80 %)

---

## 5. Règles de navigation

### 🔹 Actions principales
- appui sur image = action
- flèches = navigation

### 🔹 Pas de gestes complexes
- pas de pinch-to-zoom
- pas de scroll libre
- pas de menus cachés

---

## 6. Règles de langue
- choix initial via drapeaux
- filtrage immédiat des contenus
- pas de texte obligatoire

---

## 7. Lien avec le dossier `UX Design/`
Les documents détaillés (vision, personas, parcours, spécifications) restent dans :

`UX Design/`

Ce fichier `UX_GUIDELINES.md` en est la synthèse opérationnelle.

---

## 8. Invariants UX
- aucune lecture obligatoire pour l’enfant
- aucune sortie du mode kiosque
- aucune action dangereuse
- aucune dépendance réseau
- navigation par images uniquement
- cohérence totale avec `data.json`

---

## 9. Notes
Ce fichier doit être mis à jour à chaque évolution de l’IHM enfant ou parent.
Il sert de référence pour les futures versions du lecteur.
