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
      "name": "Les Odyssées",
      "rss": "https://...",
      "lang": "fr",
      "enabled": true
    }
  ]
}
```

---

## 3. Champs obligatoires
Chaque entrée doit contenir les champs suivants :

### 🔹 `id`
Identifiant unique du podcast.  
Règles :
- pas d’accents  
- pas d’espaces  
- pas de majuscules  
- stable dans le temps  

Exemples valides :
- `les_odyssees`
- `bestioles`
- `professeur_caillou`

### 🔹 `name`
Nom lisible du podcast (affiché dans l’IHM enfant).

### 🔹 `rss`
URL du flux RSS.  
Doit être une URL valide, accessible, et stable.

### 🔹 `lang`
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
      "id": "les_odyssees",
      "name": "Les Odyssées",
      "rss": "https://...",
      "lang": "fr",
      "enabled": true,
      "max_episodes": 20
    },
    {
      "id": "bestioles",
      "name": "Bestioles",
      "rss": "https://...",
      "lang": "fr",
      "enabled": false
    }
  ]
}
```

---

## 11. Notes
- Ce fichier est lu à chaque ingestion  
- Toute erreur JSON bloque l’ingestion  
- Toujours valider le fichier avant commit  

---
