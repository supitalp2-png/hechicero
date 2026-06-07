# Manifeste du projet Hechicero

## Vision
Créer une enceinte connectée DIY, autonome sur batterie, dédiée à l'apprentissage et à l'écoute de podcasts et webradios en espagnol.  
L’appareil doit être simple, robuste, compréhensible par un enfant, et administrable facilement par un adulte.

## Principes
- **Briques indépendantes**  
  Chaque fonctionnalité (audio, monitoring, lecteur, admin, contenu) est isolée, testable et remplaçable sans casser le reste.

- **Transparence**  
  Chaque choix technique, chaque décision d’architecture et chaque procédure d’installation est documentée dans `docs/`.

- **Robustesse**  
  Le système doit résister aux coupures, aux erreurs, aux redémarrages.  
  → Services systemd, reprise automatique, logs, monitoring batterie.

- **Simplicité UX**  
  Deux interfaces distinctes :
  - **Lecteur embarqué** : interface tactile simple, pensée pour un enfant (type Merlin).
  - **Dashboard Admin** : interface web locale pour configuration, diagnostics et mises à jour.

- **Autonomie**  
  L’appareil doit fonctionner sans réseau, sans cloud, sans dépendances externes.

## Objectifs courts termes
- Monitoring batterie fiable et visible via l’UI locale.
- Lecture audio via HiFiBerry + MPD.
- Lecteur embarqué HTML/JS basé sur `data.json`.
- Interface d’administration locale pour logs, statut et configuration.

## Objectifs moyen terme
- Gestion complète du contenu (podcasts, radios, langues).
- IHM physique (boutons, écran tactile).
- Mode hors-ligne total pour le lecteur.
- Amélioration de l’UX (carrousel, transitions, feedback visuel).

## Objectifs long terme
- Synchronisation optionnelle du contenu (USB, réseau local).
- Mode “profil enfant” avec restrictions.
- Extensions matérielles (LED, capteurs, boutons physiques).
- Migration possible vers une IHM native (Qt, Flutter, Kivy).

## Valeurs du projet
- **DIY** : comprendre, apprendre, construire soi-même.
- **Durabilité** : matériel réparable, logiciel simple et maintenable.
- **Accessibilité** : interface pensée pour les enfants et les non-technophiles.
- **Évolutivité** : chaque brique peut être améliorée ou remplacée.

