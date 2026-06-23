# Configuration des Podcasts — Projet Hechicero

Ce document décrit le format et les règles du fichier `podcasts.json`,
utilisé par le backend pour déterminer quels podcasts ingérer.

Il définit :
- la structure du fichier
- les champs obligatoires
- les règles de nommage
- la gestion des langues
- l’activation/désactivation des flux
- les invariants associés

---

## 1. Emplacement du fichier
Le fichier de configuration doit être placé dans :

`~/hechicero/data/podcasts.json`

Le backend le lit à chaque exécution de `ingest.py`.

---

## 2. Structure générale
Le fichier doit contenir un objet JSON avec une clé unique `podcasts`.

Exemple minimal :
```
{
  "podcasts": [
    {
      "id": "les_odyssees",
      "label": "Les Odyssées",
      "rss": "https://...",
      "language": "fr",
      "enabled": true,
      "image": "images/les_odyssees.jpg",
      "max_episodes": 20
    }
  ],
  "radios": [
    {
      "id": "franceinter",
      "name": "Mon Petit France Inter",
      "desc": "Généraliste · Radio France",
      "lang": "fr",
      "url": "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3",
      "image": "images/radio/franceinter.jpg",
      "image_url": "https://..."
    }
  ]
}
```

> ⚠️ Les noms de champs exacts sont `label` (pas `name`) et `language` (pas `lang`) pour les podcasts.  
> Pour les radios, les champs sont `name`, `lang`, `url`, `image`, `image_url`.

---

## 3. Champs obligatoires
Chaque entrée doit contenir les champs suivants :

### 🔹 `id`
Identifiant unique du podcast.  
Règles :
- pas d’accents  
- pas d’espaces  
- pas de majuscules  
- stable dans le temps (détermine le nom du dossier sur disque)

Exemples valides :
- `lesodyssees`
- `bestioles`
- `professeurcaillou`

> ⚠️ L’ID est normalisé par `slugify()` dans l’interface admin (suppression des caractères non alphanumériques).  
> Ne jamais changer l’ID d’un podcast après création : les fichiers audio seraient orphelins.

### 🔹 `label`
Nom lisible du podcast (affiché dans l’IHM et dans l’admin).

### 🔹 `rss`
URL du flux RSS.  
Doit être une URL valide, accessible, et stable.

### 🔹 `language`
Langue du podcast.  
Valeurs recommandées :
- `fr`
- `es`
- `en`

### 🔹 `enabled`
Booléen permettant d’activer ou désactiver un podcast.

---

## 4. Champs optionnels
### 🔹 `max_episodes`
Nombre maximum d’épisodes à conserver localement.  
Si absent → conserver tout.

### 🔹 `image`
URL d’une image de couverture personnalisée.  
Si absent → utiliser l’image du flux RSS.

---

## 5. Règles de nommage
Les identifiants (`id`) doivent respecter :
- snake_case  
- ASCII uniquement  
- pas d’espaces  
- pas de caractères spéciaux  

Ces identifiants déterminent :
- le nom du dossier dans `~/hechicero/podcasts/`  
- le nom des sous-dossiers `audio/` et `images/`  
- le nom du fichier `meta.json`  

Exemple :
`id = "les_odyssees"` → `~/hechicero/podcasts/les_odyssees/`

---

## 6. Ajouter un podcast
1. Ajouter une entrée dans `podcasts.json`  
2. Vérifier que l’ID respecte les règles  
3. Lancer manuellement l’ingestion :
```
python3 ~/hechicero/scripts/rss_ingest/ingest.py
```
4. Vérifier :
- création du dossier  
- téléchargement des épisodes  
- génération de `meta.json`  
- mise à jour de `data.json`  

---

## 7. Désactiver un podcast
Mettre :
```
"enabled": false
```

Effets :
- le backend ignore le flux  
- les fichiers existants ne sont pas supprimés  
- le podcast n’apparaît plus dans `data.json`  

---

## 8. Gestion des langues
Le champ `lang` permet :
- de filtrer les contenus  
- de préparer une future IHM multilingue  
- de séparer les contenus FR / ES / EN  

Aucun comportement automatique n’est encore implémenté côté lecteur.

---

## 9. Invariants du fichier `podcasts.json`
- le fichier doit toujours être un JSON valide  
- aucun ID ne doit changer une fois créé  
- aucun flux ne doit être supprimé sans raison explicite  
- les URLs doivent être stables  
- les podcasts désactivés doivent rester listés  

---

## 10. Exemple complet
```
{
  "podcasts": [
    {
      "id": "lesodyssees",
      "label": "Les Odyssées",
      "rss": "https://radio-france-rss.aerion.workers.dev/rss/<uuid>",
      "language": "fr",
      "enabled": true,
      "image": "images/lesodyssees.jpg",
      "max_episodes": 20
    },
    {
      "id": "bestioles",
      "label": "Bestioles",
      "rss": "https://radio-france-rss.aerion.workers.dev/rss/<uuid>",
      "language": "fr",
      "enabled": false,
      "image": "images/bestioles.jpg",
      "max_episodes": 10
    }
  ],
  "radios": [
    {
      "id": "franceinter",
      "name": "Mon Petit France Inter",
      "desc": "Généraliste · Radio France",
      "lang": "fr",
      "url": "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3",
      "image": "images/radio/franceinter.jpg",
      "image_url": "https://upload.wikimedia.org/..."
    }
  ]
}
```

> La clé `radios` est gérée exclusivement par l'interface admin PHP.  
> Ne pas la modifier manuellement sauf en cas de maintenance.

---

## 11. Notes
- Ce fichier est lu à chaque ingestion  
- Toute erreur JSON bloque l’ingestion  
- Toujours valider le fichier avant commit  

---
