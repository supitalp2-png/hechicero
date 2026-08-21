# Backend RSS — Projet Hechicero

> *Mis à jour le 2026-08-21.*

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

Structure réelle :
```
scripts/
├── battery_common.py      # helpers partagés (INA219, MPD, écriture atomique)
├── battery_tracker.py     # collecte batterie, cycles, estimations
├── battery_watchdog.py    # arrêt propre sur seuil critique
├── play_tracker.py        # suivi lecture MPD (event-driven, idle player mixer)
├── idle_screen.sh         # extinction écran (swayidle + wlopm)
└── rss_ingest/
      ├── ingest.py              # orchestrateur principal
      ├── parser.py              # parsing RSS (feedparser), filtre/dédup/tri, fusion historique
      ├── scraper_radionacional.py  # scraping HTML pour les podcasts source_type=html_radionacional
      ├── downloader.py          # téléchargement audio + images
      ├── writer.py              # génération data.json
      ├── check_integrity.py     # vérification intégrité audio/images/data.json (ignore les podcasts enabled:false)
      ├── progress.py            # suivi temps réel (→ /tmp/hechicero_progress.json)
      ├── utils.py               # log, atomic_write_json
      └── models.py              # dataclasses Episode, PodcastConfig, PodcastMeta
```

> `get_status.py` — ancien moniteur batterie, **désactivé session 11**. Ne plus utiliser.

Chaque fichier a un rôle clair et isolé.

---

## 3. Pipeline d’ingestion
Le pipeline complet est le suivant :

1. Lecture du flux RSS  
   - via `feedparser` (ou `scraper_radionacional.py` si `source_type: html_radionacional`)
   - extraction des épisodes
   - filtre des items non-épisode (bandes-annonces, auto-promo "appli(cation) Radio France") — `is_filler()`, TICKET-104
   - déduplication par id (garde la 1re occurrence rencontrée dans le flux) — certains flux republient le même épisode plusieurs fois avec des dates incohérentes, TICKET-104
   - tri chronologique à deux niveaux : saisons ordonnées par leur date la plus ancienne, puis à l'intérieur d'une saison par numéro d'épisode extrait du titre (plus fiable que la date individuelle) — TICKET-104

1bis. Fusion avec l'historique local (TICKET-107, 2026-07-17)  
   - les épisodes déjà présents dans l'ancien `meta.json` mais qui ont
     disparu du flux RSS actuel (fenêtre glissante, fréquent chez Radio
     France — constaté sur "Les Odyssées") sont **conservés**, jamais
     supprimés silencieusement de `data.json`
   - en cas de même id, la version fraîche du flux l'emporte (métadonnées à
     jour) ; les fichiers déjà téléchargés ne sont pas retéléchargés
   - `scripts/rss_ingest/parser.py::merge_episodes()`

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
└── meta.json
```

La **cover podcast** est téléchargée depuis le RSS et enregistrée directement dans :
`web/lecteur/images/{id}.jpg` — chemin web-accessible via Apache.
C'est ce chemin qui est injecté dans `data.json` comme `"image": "images/{id}.jpg"` (relatif au lecteur).

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
      "id": "lesodyssees",
      "label": "Les Odyssées",
      "rss": "https://...",
      "language": "fr",
      "enabled": true,
      "image": "images/lesodyssees.jpg",
      "max_episodes": 20,
      "source_type": "rss"
    }
  ]
}
```

> ⚠️ Les champs exacts sont `label` (pas `name`) et `language` (pas `lang`).
> `source_type` est optionnel (défaut `"rss"` via `feedparser`) — mettre `"html_radionacional"` pour un podcast scrapé en HTML (`scraper_radionacional.py`, ex. `profentucasa`, actuellement désactivé).
> Voir `docs/50-PODCASTS_CONFIG.md` pour le format complet avec la section `radios`.

### Règles
- `id` : unique, sans espace, sans accent  
- `rss` : URL valide  
- `enabled` : permet d’activer/désactiver un podcast — `check_integrity.py` ignore les podcasts désactivés (pas une erreur si leur `meta.json` diverge de `data.json`)
- `language` : `fr`, `es`, `en`…  

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
- l’épisode est **inclus dans `data.json`** avec `"audio": ""`
- le lecteur affiche l’épisode (titre + durée) mais ne peut pas le lire
- le prochain ingest télécharge l’audio manquant et met à jour `data.json`
- log de l’erreur dans les logs ingest  

### Image introuvable
- utiliser une image par défaut  

### JSON corrompu
- ne jamais écraser un JSON valide  
- écriture atomique obligatoire  

### Stratégie retry
- 3 tentatives  
- délai progressif  

### Podcast en échec (permission, réseau…) — TICKET-105, 2026-07-09/17
- chaque podcast est traité dans son propre bloc `try/except` dans `ingest.py`
- un podcast en échec est loggé comme erreur de progression mais n'interrompt jamais les suivants
- `data.json` est ensuite reconstruit à partir de **tous** les `meta.json` présents sur disque (pas seulement ceux traités avec succès dans la session en cours) — un podcast en échec garde sa dernière version valide au lieu de disparaître du lecteur

---

## 8. Invariants du backend
- ne jamais supprimer un épisode existant sans règle explicite  
- ne jamais écraser un JSON valide  
- toujours écrire via fichier temporaire  
- toujours valider le JSON avant rename  
- ne jamais dépendre d’un service externe  

---

## 9. Ingestion automatique
L’ingestion est déclenchée par **cron** (crontab de l’utilisateur `thomas`).

Ligne active :
```
0 3 * * * umask 002 && python3 /home/thomas/hechicero/scripts/rss_ingest/ingest.py >> /tmp/hechicero_ingest.log 2>&1
```

> ⚠️ Le service/timer systemd (`hechicero-rss.timer`) est **désactivé** pour éviter les conflits.
> Ne pas réactiver sans désactiver le cron d’abord. Voir `docs/70-SERVICES_SYSTEMD.md`.

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
- Aucune évolution majeure planifiée à ce stade. Les deux points historiquement listés ici sont faits : dédup/tri fiables par id + numéro d'épisode (TICKET-104, remplace le risque de collision de `normalize_id()`) et durées via `ffprobe` pour les flux sans `itunes:duration` (TICKET-059, `probe_duration()` dans `downloader.py`).
- Piste ouverte, non commencée : purge/rotation de l'archive locale — TICKET-107 (2026-07-17) a supprimé toute purge automatique des épisodes disparus du flux RSS pour ne jamais perdre de contenu déjà téléchargé ; l'archive ne fait donc que grossir avec le temps. Pas de souci d'espace disque identifié à ce stade, mais à surveiller.

## 13. Notes d'architecture
- `progress.py` écrit `/tmp/hechicero_progress.json` en temps réel
- L'admin PHP lit ce fichier via `?action=get_progress` toutes les 2 secondes
- Les radios sont gérées dans `data/podcasts.json` (clé `radios`) par l'admin PHP
- `writer.py` lit les radios depuis `podcasts.json` et les injecte dans `data.json` à chaque ingest — **en écartant celles dont `enabled` vaut `false`** (TICKET-145, 2026-08-21)

  ⚠️ **Ce filtre n'est pas décoratif.** Sans lui, l'ingestion nocturne **réinstallerait**
  une radio que le parent vient de désactiver depuis l'admin, quelques heures plus tard et
  sans rien signaler. Une panne différée est d'autant plus déroutante que rien ne la relie
  à l'action qui l'a causée. `enabled` absent = activée, pour les radios antérieures.
- La cover podcast est téléchargée en priorité depuis l'image de `<channel>` (fiable, indépendante de l'ordre des épisodes) ; repli sur l'image du premier épisode (`episodes[0].image_url`) seulement si le flux n'expose pas d'image de channel — corrigé TICKET-104 (2026-07-09), voir `parser.py` (`feed_cover_url`)
