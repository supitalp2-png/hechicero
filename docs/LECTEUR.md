# Brique Lecteur — Hechicero

## 1. Objectif

Fournir une interface embarquée simple, robuste et autonome pour écouter :

- des **webradios** (flux MP3)
- des **podcasts locaux** (fichiers téléchargés)
- des **contenus statiques** (démos, histoires)

Le lecteur est destiné à l’écran tactile du Raspberry Pi et doit fonctionner **même sans réseau**.

---

## 2. Principes

- **Autonomie totale**  
  Aucun appel réseau. Toutes les données sont locales.

- **Simplicité enfant**  
  Navigation type Merlin : grands boutons, peu d’options, retour clair.

- **Séparation stricte**  
  Le lecteur ne dépend pas de l’interface d’administration.

- **Données statiques**  
  Un fichier unique : `data.json`.

- **Évolutivité**  
  Compatible avec une future IHM native (Qt, Flutter, Kivy).

---

## 3. Architecture du Lecteur

### 3.1 Structure des fichiers
  web/lecteur/
  │
  ├── index.html        # Point d’entrée du lecteur
  ├── app.js            # Logique de navigation et rendu
  ├── style.css         # Styles du lecteur
  │
  ├── data.json         # Base de données locale (radios + podcasts)
  │
  ├── images/           # Jaquettes des contenus
  │   └── *.jpg / *.png
  │
  └── audio/            # Fichiers audio statiques (démos)
  └── *.mp3

### 3.2 Rôle des fichiers

- **index.html**  
  Squelette minimal de l’IHM. Le contenu dynamique est injecté par `app.js`.

- **app.js**  
  - charge `data.json`  
  - génère les écrans (Accueil → Radios → Podcasts → Lecture)  
  - gère les événements (clics, retour, lecture audio)  
  - communique avec MPD via commandes HTTP/TCP  
  - prépare la compatibilité future avec une IHM native

- **data.json**  
  Catalogue local des contenus.  
  Il est **généré par le backend** (ingestion RSS) et **lu par l’IHM**.

---

## 4. Structure de `data.json`

### 4.1 Exemple minimal (MVP)

    ```json
    {
      "radios": [
        {
          "id": "monpetitfranceinter",
          "label": "Mon Petit France Inter",
          "stream_url": "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3",
          "image": "images/monpetitfranceinter.png"
        }
      ],
      "podcasts": []
    }

  ### 4.2 Exemple complet (avec podcasts locaux)
    ```json
    {
      "radios": [
        {
          "id": "monpetitfranceinter",
          "label": "Mon Petit France Inter",
          "stream_url": "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3",
          "image": "images/monpetitfranceinter.png"
        }
      ],
      "podcasts": [
        {
          "id": "lesodyssees",
          "titre": "Les Odyssées",
          "image": "images/lesodyssees.jpg",
          "episodes": [
            {
              "id": "ep001",
              "titre": "Cléopâtre, reine d’Égypte",
              "audio": "/home/thomas/hechicero/podcasts/lesodyssees/audio/ep001.mp3",
              "duree": 612
            }
          ]
        }
      ]
    }
```
### 4.3 Règles
 - Pas d’accents dans les noms de fichiers
 - Pas d’espaces
 - Formats autorisés : .jpg, .png, .mp3
 - Les chemins audio des podcasts pointent vers :
 - ~/hechicero/podcasts/<id>/audio/*.mp3

## 5. Navigation du Lecteur

1. **Accueil**  
   - Bouton “Radios”  
   - Bouton “Podcasts”

2. **Radios**  
   - Liste des radios issues de `data.json`  
   - Lecture via MPD (flux)

3. **Podcasts**  
   - Liste des podcasts disponibles  
   - Liste des épisodes

4. **Lecture**  
   - Titre  
   - Jaquette  
   - Bouton Play/Pause  
   - Barre de progression (optionnelle)  
   - Bouton Retour

---

## 6. Intégration MPD

Le lecteur ne lit **pas** directement les fichiers audio.  
Il envoie des commandes à MPD :

- `mpc clear`  
- `mpc add <url>`  
- `mpc play`  
- `mpc pause`  
- `mpc stop`

MPD se charge de :

- lire les flux web  
- lire les fichiers locaux  
- gérer les erreurs  
- gérer la file d’attente

---

## 7. Critères d’acceptation

- `data.json` chargé sans erreur  
- jaquettes affichées correctement  
- navigation tactile fluide  
- lecture MPD fonctionnelle (flux + fichiers locaux)  
- lecteur utilisable hors réseau  
- aucune dépendance à l’admin  

---

## 8. Évolutions prévues

- Carrousel pour les jaquettes  
- Animations simples (fade, slide)  
- Mode hors-ligne total (déjà compatible)  
- Support des boutons physiques (GPIO)  
- Migration possible vers une IHM native (Qt, Flutter, Kivy)
