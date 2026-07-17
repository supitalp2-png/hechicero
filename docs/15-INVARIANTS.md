# Invariants — Projet Hechicero

Ce document définit les règles **absolues** du projet Hechicero.
Elles ne doivent jamais être violées, quelles que soient les évolutions futures.

Les invariants garantissent :
- la robustesse
- la maintenabilité
- la sécurité enfant
- la cohérence du système
- la reproductibilité

---

## 1. Invariants techniques

### 🔹 1.1 Fonctionnement hors réseau
Le lecteur doit fonctionner **sans WiFi**, **sans Internet**, **sans cloud**.
Aucune dépendance externe n’est autorisée.

### 🔹 1.2 `data.json` est la source unique
- Le lecteur lit uniquement `data.json`.
- Le backend est le seul à pouvoir le modifier.
- Le fichier doit toujours être **valide**, **complet**, **cohérent**.

### 🔹 1.3 Écriture atomique obligatoire
Tout fichier critique doit être écrit ainsi :
1. écrire dans `<file>.tmp`  
2. valider  
3. `mv <file>.tmp <file>`  

### 🔹 1.4 MPD doit toujours démarrer automatiquement
- MPD doit être actif au boot  
- MPD ne doit jamais être bloqué par un fichier corrompu  

### 🔹 1.5 Aucun script ne doit supprimer un fichier audio existant
Sauf règle explicite (ex : quotas).

### 🔹 1.6 Aucun JSON ne doit être écrasé s’il est valide
En cas d’erreur → conserver l’ancien.

---

## 2. Invariants UX (Lecteur enfant)

### 🔹 2.1 Interface fermée
- aucun lien externe  
- aucune navigation libre  
- aucun menu caché  
- aucune possibilité de quitter Chromium  

### 🔹 2.2 Simplicité absolue
- grands boutons  
- zéro texte inutile  
- zéro configuration visible  

### 🔹 2.3 Volume logiciel limité
- Haut-parleurs : volume max = 80% pour sécurité enfant (`speakers_max` dans `config.json`).
- Casque : plafond logiciel à 100% assumé (`headphones_max` dans `config.json`) — décision Thomas (2026-07-17) : le casque de l'enfant a une impédance plus élevée que les haut-parleurs, ce qui limite lui-même la puissance d'écoute réelle même à 100% logiciel. Pas besoin d'un plafond logiciel plus bas côté casque.

### 🔹 2.4 Aucune action dangereuse
Le lecteur ne doit jamais :
- écrire sur le disque  
- modifier des fichiers système  
- lancer des commandes shell  

### 🔹 2.5 Alignement UX
Le lecteur doit respecter les règles définies dans `25-UX_GUIDELINES.md`.

---

## 3. Invariants de robustesse

### 🔹 3.1 Le système doit survivre aux coupures
- pas de corruption  
- pas de crash au boot  
- pas de dépendance réseau  

### 🔹 3.2 Les services systemd doivent redémarrer automatiquement
- batterie  
- ingestion RSS  
- MPD  

### 🔹 3.3 Aucun fichier critique ne doit être laissé partiellement écrit
(d’où l’écriture atomique).

---

## 4. Invariants de sécurité enfant

### 🔹 4.1 Aucun contenu non prévu
- pas de YouTube  
- pas de web externe  
- pas de liens cliquables  

### 🔹 4.2 Aucun risque auditif
- volume logiciel limité  
- pas de pics sonores  

### 🔹 4.3 Aucun risque d’usage
- interface stable  
- pas de crash visible  
- pas de messages techniques  

---

## 5. Invariants de maintenance

### 🔹 5.1 Arborescence stable
Aucun fichier ne doit être déplacé sans mise à jour documentaire.

### 🔹 5.2 Documentation obligatoire
Toute nouvelle brique doit avoir un fichier dans `docs/`.

### 🔹 5.3 Pas de dépendances opaques
- pas de frameworks lourds  
- pas de services cloud  
- pas de bibliothèques non maintenues  

### 🔹 5.4 Scripts lisibles
- Python simple  
- pas de magie  
- pas de side-effects cachés  

---

## 6. Invariants documentaires

### 🔹 6.1 Chaque fichier doit être autonome
Pas de dépendance implicite entre documents.

### 🔹 6.2 Préfixe `` pour les blocs à coller
Pour éviter l’interprétation par l’IHM.

### 🔹 6.3 Numérotation par dizaines
Permet d’insérer des fichiers sans casser l’ordre.

### 🔹 6.4 Aucun prénom personnel dans les fichiers versionnés (repo public)

Le repo est public. Aucun prénom réel (enfant, adulte, personnage) ne doit apparaître dans les fichiers versionnés.

**Règle** : utiliser `le petit`, `papa`, `le collègue`, `la maman`, `la directrice` dans tous les fichiers `docs/`.

**Exception autorisée** : le dossier `docs/private/` est exclu du repo (`.gitignore`). Les scripts audio, les notes de production avec prénoms réels, et tout contenu personnalisé s’y trouvent.

**Structure attendue** :
```
private/                          ← dans .gitignore — prénoms réels autorisés ici
  podcast-easteregg/
    ep1-script-notes.md
    ep2-script-notes.md
    ...
docs/
  55-PODCAST_SERIE_DECISIONS.md   ← version publique, sans prénoms
```

Cette règle s’applique à tous les fichiers : docs, scripts, JSON de config, commentaires de code.

---

## 7. Invariants du projet

- robustesse avant fonctionnalités  
- simplicité avant complexité  
- local avant cloud  
- enfant avant adulte  
- documentation avant implémentation  

---

## 8. Rappel
Ces invariants sont **non négociables**.
Toute évolution doit les respecter.
Toute proposition doit être évaluée à leur lumière.
