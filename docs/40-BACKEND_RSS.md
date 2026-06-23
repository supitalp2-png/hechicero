# Backend RSS — Projet Hechicero

Ce document décrit la brique backend responsable de l’ingestion des podcasts,
du téléchargement des épisodes et de la génération des fichiers utilisés par le lecteur.

---

## 1. Objectif
Le backend a pour rôle :
- de lire les flux RSS (podcasts)
- de télécharger les épisodes audio
- de générer les métadonnées (`meta.json`)
- de produire `data.json` pour le lecteur embarqué

Il fonctionne **hors réseau**, sauf pour la récupération des flux RSS.

---

## 2. Architecture du backend
Le backend est composé de scripts Python situés dans :
`~/hechicero/scripts/`

Structure recommandée :
```
scripts/
├── get_status.py          # monitoring batterie
└── rss_ingest/
      ├── ingest.py        # orchestrateur principal
      ├── parser.py        # parsing RSS (feedparser)
      ├── downloader.py    # téléchargement audio + images
      ├── writer.py        # génération data.json
      ├── progress.py      # suivi temps réel (→ /tmp/hechicero_progress.json)
      ├── utils.py         # log, atomic_write_json
      └── models.py        # dataclasses Episode, PodcastConfig, PodcastMeta
```

Chaque fichier a un rôle clair et isolé.

---

## 3. Pipeline d’ingestion
Le pipeline complet est le suivant :

1. Lecture du flux RSS  
   - via `feedparser`
   - extraction des épisodes

2. Téléchargement des fichiers audio  
   - stockage dans `~/hechicero/podcasts/<id>/audio/`

3. Téléchargement des images  
   - stockage dans `~/hechicero/podcasts/<id>/images/`

4. Génération de `meta.json`  
   - titre
   - durée
   - chemins audio
   - date de publication

5. Mise à jour de `web/lecteur/data.json`  
   - radios
   - podcasts
   - images
   - épisodes

---

## 4. Organisation des fichiers podcasts
Chaque podcast est stocké dans :
`~/hechicero/podcasts/<podcast_id>/`

Structure :
```
<podcast_id>/
├── audio/
│     └── *.mp3
├── images/
│     └── <ep_id>.jpg     # jaquette par épisode
├── cover.jpg              # couverture du podcast (téléchargée depuis le RSS)
└── meta.json
```

Règles :
- pas d’accents dans les noms de fichiers
- pas d’espaces
- formats autorisés : `.mp3`, `.jpg`, `.png`

---

## 5. Fichier `data.json`
`data.json` est la **source unique** du lecteur embarqué.
Il est généré automatiquement par le backend.

Contient :
- radios
- podcasts
- épisodes
- images
- chemins audio locaux

Le lecteur ne modifie jamais ce fichier.

---

## 6. Fichiers de configuration (podcasts.json)
Le backend lit un fichier de configuration listant les podcasts à ingérer.

### Format recommandé
```
{
  "podcasts": [
    {
      "id": "les_odyssees",
      "name": "Les Odyssées",
      "rss": "https://...",
      "lang": "fr",
      "enabled": true
    }
  ]
}
```

### Règles
- `id` : unique, sans espace, sans accent  
- `rss` : URL valide  
- `enabled` : permet d’activer/désactiver un podcast  
- `lang` : `fr`, `es`, `en`…  

### Ajouter un podcast
- ajouter un bloc dans `podcasts.json`  
- lancer manuellement l’ingestion ou attendre le timer  

### Désactiver un podcast
- passer `enabled` à `false`  
- les fichiers existants ne sont pas supprimés  

---

## 7. Gestion des erreurs
Le backend doit être **robuste** et **ne jamais casser `data.json`**.

### Flux RSS invalide
- ignorer le flux  
- log interne  
- ne pas écraser les données existantes  

### Fichier audio manquant
- skip de l’épisode  
- log  

### Image introuvable
- utiliser une image par défaut  

### JSON corrompu
- ne jamais écraser un JSON valide  
- écriture atomique obligatoire  

### Stratégie retry
- 3 tentatives  
- délai progressif  

---

## 8. Invariants du backend
- ne jamais supprimer un épisode existant sans règle explicite  
- ne jamais écraser un JSON valide  
- toujours écrire via fichier temporaire  
- toujours valider le JSON avant rename  
- ne jamais dépendre d’un service externe  

---

## 9. Service systemd (ingestion automatique)
Un service systemd + un timer permettent :
- une ingestion périodique
- une reprise automatique en cas d’erreur

Statut actuel :
- scripts fonctionnels
- service systemd opérationnel

---

## 10. Tests de validation
### 🔹 Test RSS
```
python3 scripts/rss_ingest/ingest.py
```

### 🔹 Vérifier les fichiers téléchargés
```
ls ~/hechicero/podcasts/<id>/audio/
```

### 🔹 Vérifier `data.json`
```
cat ~/hechicero/web/lecteur/data.json
```

---

## 11. Critères d’acceptation
- tous les épisodes sont téléchargés  
- `meta.json` est valide  
- `data.json` est mis à jour  
- le lecteur affiche les nouveaux contenus  
- aucun JSON corrompu  
- aucune dépendance réseau en lecture  

---

## 12. Évolutions prévues
- gestion des doublons de titres dans `normalize_id()` (risque de collision)
- durées des épisodes via `ffprobe` pour les flux sans `itunes:duration` (TICKET-059)

## 13. Notes d'architecture
- `progress.py` écrit `/tmp/hechicero_progress.json` en temps réel
- L'admin PHP lit ce fichier via `?action=get_progress` toutes les 2 secondes
- Les radios sont gérées dans `data/podcasts.json` (clé `radios`) par l'admin PHP
- `writer.py` lit les radios depuis `podcasts.json` et les injecte dans `data.json` à chaque ingest
- La cover podcast (`cover.jpg`) est téléchargée depuis l'image du premier épisode du flux RSS
