# A0 – Vision du Projet

## Objectif global
Créer une enceinte tactile pour enfant, simple, magique et bilingue, permettant d’écouter des podcasts en français et en espagnol, avec une interface adaptée à un enfant de 7 ans et une administration accessible aux parents.

## Pourquoi ce projet ?
- Offrir à l’enfant une expérience d’écoute autonome, intuitive et ludique.
- Permettre la découverte de contenus en espagnol sud-américain.
- Créer un objet pédagogique et technologique à partager en famille.
- Proposer une alternative ouverte, personnalisable et évolutive aux enceintes commerciales.

## Valeurs clés
- **Simplicité** : l’enfant doit comprendre l’interface sans lire.
- **Magie** : animations, transitions, interactions visuelles.
- **Autonomie** : l’enfant navigue seul, sans risque.
- **Bilinguisme** : accès clair et immédiat aux deux langues.
- **Robustesse** : système stable, maintenable, documenté.
- **Évolutivité** : MVP rapide, améliorations possibles ensuite.

## Publics cibles
- **Enfant utilisateur (7 ans, bilingue)** : interface simple, visuelle, centrée sur les images.
- **Parent administrateur (technophile)** : configuration avancée, monitoring, gestion des flux.
- **Parent non‑technophile** : interface d’administration ultra simplifiée.

## Résultat attendu
Une enceinte tactile qui :
- affiche de grandes jaquettes,
- lit les podcasts immédiatement,
- permet de choisir la langue via deux drapeaux,
- propose un écran d’écoute clair,
- reprend la lecture au même endroit,
- se configure facilement via une interface web.

# A1 – Problème & Opportunité

## Problème
Les enfants bilingues (ou en apprentissage) n’ont pas d’enceinte simple, tactile et adaptée à leur âge pour écouter des podcasts en autonomie.  
Les solutions existantes sont :
- trop complexes,
- trop textuelles,
- pas adaptées à un enfant de 7 ans,
- rarement bilingues,
- peu personnalisables,
- dépendantes d’un écosystème fermé.

Les parents, eux, rencontrent d’autres difficultés :
- configurer les contenus est souvent compliqué,
- les interfaces d’administration sont techniques,
- les systèmes sont peu transparents (pas de logs, pas de monitoring),
- impossible de tester l’IHM sans matériel.

## Opportunité
Créer une enceinte :
- **simple** pour l’enfant,
- **bilingue** (français / espagnol),
- **magique** (animations, images, transitions),
- **ouverte** et **personnalisable**,
- **administrable facilement** par un parent technophile,
- **sans risque** pour un parent non‑technophile.

## Pourquoi maintenant ?
- Explosion des contenus audio pour enfants.
- Besoin croissant de solutions bilingues.
- Disponibilité de matériel tactile abordable.
- Envie de créer un objet pédagogique et familial.

# A2 – Utilisateurs & Besoins

## 1. Enfant Utilisateur (7 ans, bilingue)

### Besoins principaux
- Naviguer sans lire : uniquement avec des images, flèches, couleurs.
- Comprendre immédiatement où il est dans l’interface.
- Voir de grandes jaquettes pour reconnaître les contenus.
- Avoir un retour visuel clair (agrandissement, animation, son).
- Lancer la lecture en appuyant sur l’image.
- Mettre pause en appuyant sur l’image.
- Reprendre la lecture au même endroit.
- Choisir la langue via deux drapeaux (🇫🇷 / 🇨🇴).
- Explorer facilement : flèches, défilement automatique, images multiples.

### Contraintes
- Lecteur débutant.
- Patience limitée.
- Doit pouvoir utiliser l’enceinte seul, sans supervision.

---

## 2. Parent Administrateur (technophile)

### Besoins principaux
- Interface web claire pour gérer les contenus.
- Ajouter / retirer des flux facilement.
- Tester l’IHM sans matériel tactile.
- Accéder à des logs, un état système, un monitoring minimal.
- Organiser les contenus (playlists, langues, favoris).
- Comprendre l’usage (historique, favoris).
- Maintenir un système stable, documenté, évolutif.

### Contraintes
- Temps limité.
- Souhait d’un MVP rapide mais propre.
- Besoin d’une architecture robuste et maintenable.

---

## 3. Parent Non‑Technophile (utilisateur occasionnel)

### Besoins principaux
- Interface d’administration ultra simple.
- Ajouter un podcast en collant un lien.
- Voir si un contenu est actif ou non.
- Supprimer un contenu sans risque.
- Recevoir des messages d’erreur clairs, non techniques.
- Ne jamais pouvoir casser le système.

### Contraintes
- Peu à l’aise avec l’informatique.
- Ne lit pas la documentation.
- Se décourage vite si l’interface est confuse.


# A3 – Parcours Utilisateur

## 1. Parcours de l’Enfant (7 ans, bilingue)

### 1.1. Allumer l’enceinte
- L’enfant touche l’écran.
- Une animation courte apparaît (effet “magique”).
- Deux drapeaux s’affichent : 🇫🇷 et 🇨🇴.

### 1.2. Choisir la langue
- L’enfant appuie sur un drapeau.
- L’interface bascule immédiatement dans la langue choisie.
- Les contenus affichés correspondent à cette langue.

### 1.3. Choisir un podcast
- L’enfant voit de grandes jaquettes.
- Il navigue avec les flèches (haut/bas/gauche/droite).
- Quand il appuie sur une jaquette :
  - elle s’agrandit légèrement,
  - un son rigolo confirme le choix.

### 1.4. Lancer la lecture
- L’enfant appuie sur la grande image.
- La lecture démarre immédiatement.
- L’écran d’écoute apparaît :
  - grande image,
  - barre de progression,
  - flèches avant/arrière.

### 1.5. Mettre pause
- L’enfant appuie sur l’image → pause.
- Il réappuie → lecture.

### 1.6. Reprendre plus tard
- L’enfant revient sur le même podcast.
- La lecture reprend automatiquement au même endroit.

---

## 2. Parcours du Parent Administrateur (technophile)

### 2.1. Accéder à l’interface web
- Le parent ouvre l’URL locale de l’interface d’administration.
- Il voit un tableau de bord clair : état système, logs, contenus.

### 2.2. Ajouter un podcast
- Il colle un flux RSS.
- L’interface récupère automatiquement :
  - titre,
  - jaquette,
  - épisodes.
- Le parent peut choisir la langue du contenu.

### 2.3. Organiser les contenus
- Il peut :
  - activer/désactiver des podcasts,
  - créer des playlists,
  - gérer les favoris,
  - trier par langue.

### 2.4. Tester l’IHM
- Le parent peut simuler l’écran tactile depuis le navigateur.
- Il vérifie les animations, transitions, interactions.

### 2.5. Monitoring
- Accès aux logs,
- État du système,
- Historique d’écoute.

---

## 3. Parcours du Parent Non‑Technophile

### 3.1. Accéder à l’interface simplifiée
- Le parent arrive sur une interface épurée :
  - “Ajouter un podcast”
  - “Supprimer un podcast”
  - “Voir les contenus”

### 3.2. Ajouter un podcast
- Il clique sur “Ajouter”.
- Il colle un lien.
- Un message clair apparaît :
  - “C’est bon, le podcast est ajouté.”

### 3.3. Supprimer un podcast
- Il clique sur une icône poubelle.
- Une confirmation simple apparaît.
- Aucun risque de casser le système.

### 3.4. Vérifier les contenus
- Les jaquettes s’affichent.
- Un indicateur montre si le podcast est actif.


# A4 – Architecture Fonctionnelle

## 1. Vue d’ensemble
L’architecture sépare clairement :
- **l’IHM enfant** (simple, tactile, magique),
- **l’IHM parent** (web, administration),
- **le moteur audio** (lecture, favoris, historique),
- **la gestion des contenus** (podcasts, radios, langues).

Cette séparation garantit :
- robustesse,
- maintenabilité,
- évolutivité,
- simplicité d’usage pour l’enfant.

---

## 2. Composants principaux

### 2.1. Interface Enfant (IHM tactile)
- Affichage des jaquettes.
- Navigation par flèches.
- Sélection par appui sur l’image.
- Écran d’écoute (image + barre de progression).
- Pause/lecture par appui sur l’image.
- Choix de la langue via deux drapeaux.
- Reprise automatique de la lecture.

### 2.2. Interface Parent (Web Admin)
- Tableau de bord (état système, logs).
- Gestion des flux RSS.
- Activation/désactivation de contenus.
- Organisation par langue.
- Historique d’écoute.
- Simulation de l’IHM enfant.

### 2.3. Moteur Audio
- Lecture des podcasts.
- Gestion des épisodes.
- Avancement et reprise.
- Favoris.
- Radios en direct.

### 2.4. Gestion des Contenus
- Récupération des flux RSS.
- Téléchargement des jaquettes.
- Stockage local des métadonnées.
- Association langue → contenu.

---

## 3. Flux Fonctionnels

### 3.1. Lancement d’un podcast
1. L’enfant appuie sur une jaquette.  
2. L’IHM envoie l’ID du contenu au moteur audio.  
3. Le moteur démarre la lecture.  
4. L’IHM affiche l’écran d’écoute.

### 3.2. Pause / Lecture
1. L’enfant appuie sur l’image.  
2. L’IHM envoie “pause” ou “play”.  
3. Le moteur audio exécute l’action.

### 3.3. Reprise de lecture
1. Le moteur audio sauvegarde la position.  
2. Lors d’un retour sur le même contenu, il renvoie la position.  
3. L’IHM reprend automatiquement.

### 3.4. Changement de langue
1. L’enfant appuie sur un drapeau.  
2. L’IHM change la langue active.  
3. La liste des contenus se met à jour.

---

## 4. Contraintes techniques
- Interface enfant ultra simple (pas de texte obligatoire).
- Temps de réponse très court.
- Robustesse face aux erreurs réseau.
- Aucun risque pour l’enfant de casser le système.
- Administration accessible depuis un navigateur.

# A5 – Spécifications Fonctionnelles

## 1. Interface Enfant (IHM tactile)

### 1.1. Écran d’accueil
- Affiche deux drapeaux :
  - 🇫🇷 pour le français
  - 🇨🇴 pour l’espagnol
- Appui sur un drapeau → bascule immédiate de langue.
- Animation courte au lancement.

### 1.2. Liste des contenus
- Grandes jaquettes (minimum 300×300 px).
- Navigation par flèches (haut/bas/gauche/droite).
- Défilement automatique possible.
- Appui sur une jaquette :
  - agrandissement léger,
  - son de confirmation,
  - ouverture du détail.

### 1.3. Écran de lecture
- Grande image du podcast.
- Barre de progression visible.
- Bouton invisible : appui sur l’image = pause/lecture.
- Flèches :
  - gauche = épisode précédent,
  - droite = épisode suivant.
- Reprise automatique de la position sauvegardée.

### 1.4. Gestion de la langue
- Le choix de langue filtre les contenus.
- Le choix est conservé tant que l’appareil reste allumé.
- Pas de texte obligatoire.

---

## 2. Interface Parent (Web Admin)

### 2.1. Tableau de bord
- État système (CPU, RAM, stockage).
- Logs accessibles.
- Historique d’écoute.
- Liste des contenus installés.

### 2.2. Gestion des podcasts
- Ajouter un flux RSS.
- Récupération automatique :
  - titre,
  - jaquette,
  - épisodes.
- Choix de la langue du contenu.
- Activer/désactiver un podcast.
- Supprimer un podcast.

### 2.3. Organisation
- Tri par langue.
- Création de playlists.
- Gestion des favoris.
- Réorganisation simple (drag & drop si possible).

### 2.4. Simulation de l’IHM enfant
- Aperçu de l’écran tactile dans le navigateur.
- Test des interactions :
  - navigation,
  - sélection,
  - lecture.

---

## 3. Interface Parent Simplifiée (non‑technophile)

### 3.1. Accueil
- Trois actions visibles :
  - “Ajouter un podcast”
  - “Supprimer un podcast”
  - “Voir les contenus”

### 3.2. Ajouter un podcast
- Champ unique : coller un lien.
- Message clair :
  - “Podcast ajouté”
  - ou “Lien invalide”.

### 3.3. Supprimer un podcast
- Icône poubelle.
- Confirmation simple.
- Aucune action dangereuse.

### 3.4. Voir les contenus
- Jaquettes visibles.
- Indicateur actif/inactif.

---

## 4. Moteur Audio

### 4.1. Lecture
- Lecture immédiate après sélection.
- Support des flux RSS standards.
- Gestion des radios en direct.

### 4.2. Position de lecture
- Sauvegarde automatique.
- Reprise automatique.

### 4.3. Navigation
- Épisode suivant/précédent.
- Pause/lecture via l’image.

---

## 5. Contraintes techniques

### 5.1. Performance
- Temps de réponse < 200 ms pour les actions courantes.
- Animations fluides.

### 5.2. Robustesse
- Tolérance aux erreurs réseau.
- Pas de crash visible pour l’enfant.

### 5.3. Sécurité
- Interface enfant isolée de l’administration.
- Aucun accès aux réglages système.

### 5.4. Évolutivité
- Architecture modulaire.
- Possibilité d’ajouter :
  - nouveaux types de contenus,
  - nouveaux écrans,
  - nouvelles langues.
