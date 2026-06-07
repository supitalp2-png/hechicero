# Brique Lecteur — Hechicero

## Objectif
Fournir une interface embarquée simple, robuste et autonome pour écouter des podcasts et webradios en espagnol.  
Le lecteur est destiné à l’écran tactile du Raspberry Pi et doit fonctionner même sans réseau.

## Principes
- **Autonomie totale** : aucune dépendance réseau, toutes les données sont locales.  
- **Simplicité UX** : navigation pensée pour un enfant (type Merlin).  
- **Séparation stricte** : le lecteur ne dépend pas de l’interface d’administration.  
- **Données statiques** : structure JSON simple, modifiable facilement.  
- **Évolutivité** : architecture compatible avec une future IHM native.

## Architecture du Lecteur

### Structure des fichiers
web/lecteur/
│
├── index.html        # Point d’entrée du lecteur
├── lecture.html      # Écran de lecture (optionnel selon implémentation)
├── app.js            # Logique de navigation et rendu
├── style.css         # Styles du lecteur
│
├── data.json         # Base de données locale (podcasts, chapitres)
│
├── images/           # Jaquettes des podcasts
│   └── cuentasticos.jpg
│
└── audio/            # Fichiers audio locaux
└── cuentasticos_ep1.mp3


### Rôle des fichiers
- **index.html**  
  Contient la structure minimale de l’IHM. Le contenu dynamique est injecté par `app.js`.

- **app.js**  
  - charge `data.json`  
  - génère les écrans (Accueil → Podcasts → Chapitres → Lecture)  
  - gère les événements (clics, retour, lecture audio)  
  - prépare la compatibilité future avec une IHM tactile native

- **data.json**  
  Base de données locale. Exemple minimal :

    ```json
    {
      "podcasts": [
        {
          "id": "cuentasticos",
          "titre": "Cuentásticos",
          "langue": "ES",
          "image": "images/cuentasticos.jpg",
          "chapitres": [
            {
              "id": "ep1",
              "titre": "La princesa valiente",
              "audio": "audio/cuentasticos_ep1.mp3",
              "duree": 312
            }
          ]
        }
      ]
    }
    
images/  
  Contient les jaquettes. Règles : pas d’accents ; pas d’espaces ; format .jpg ou .png.

audio/  
  Contient les fichiers audio locaux. Règles : MP3 ; noms simples, sans espaces ni accents.

Navigation du Lecteur
  Accueil
  
  Logo ou titre
  
  Bouton Entrer
  
  Choix du podcast
  
  Liste des podcasts issus de data.json
  
  Affichage des jaquettes
  
  Choix du chapitre
  
  Liste des épisodes du podcast sélectionné
  
  Lecture
  
  Titre du chapitre
  
  Bouton Play / Pause
  
  Barre de progression (optionnelle)
  
  Retour au chapitre précédent
  
  Contraintes techniques
  Le lecteur doit être servi par Apache via l’alias /hechicero/.
  
  fetch("data.json") nécessite un serveur web (pas de file://).
  
  Le lecteur doit fonctionner même si l’admin est hors service.
  
  Le lecteur ne doit jamais écrire sur le disque (lecture seule).
  
  Évolutions prévues
  Carrousel pour les jaquettes
  
  Animations simples (fade, slide)
  
  Mode hors-ligne complet
  
  Support des webradios
  
  Intégration avec boutons physiques (GPIO)
  
  Migration possible vers une IHM native (Qt, Flutter, Kivy)
  
  Critères d’acceptation
  Le lecteur charge data.json sans erreur.
  
  Les jaquettes s’affichent correctement.
  
  La navigation fonctionne sur écran tactile.
  
  La lecture audio fonctionne via MPD.
  
  Le lecteur reste fonctionnel sans réseau.
