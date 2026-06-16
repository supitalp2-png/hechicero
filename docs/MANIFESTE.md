# Manifeste du projet Hechicero

## 1. Vision

Créer une enceinte connectée **DIY**, **autonome**, **robuste**, dédiée à l’apprentissage et à l’écoute de contenus audio (podcasts, histoires, webradios), avec une interface pensée pour un enfant et une administration simple pour un adulte.

Hechicero doit être :
- compréhensible,
- maintenable,
- réparable,
- évolutif,
- et utilisable hors réseau.

---

## 2. Principes fondateurs

### 🔹 Briques indépendantes
Chaque fonctionnalité est isolée :
- Monitoring batterie  
- Audio (MPD + Amp4)  
- Lecteur embarqué  
- Admin locale  
- Ingestion podcasts  

Une brique peut évoluer sans casser les autres.

### 🔹 Transparence
Chaque choix technique, chaque décision d’architecture, chaque procédure d’installation est documentée dans `docs/`.

### 🔹 Robustesse
Le système doit résister :
- aux coupures,
- aux erreurs,
- aux redémarrages.

Les services critiques tournent sous **systemd** avec reprise automatique.

### 🔹 Simplicité UX
Deux interfaces distinctes :
- **Lecteur embarqué** : simple, tactile, pensée pour un enfant.
- **Dashboard Admin** : interface locale pour configuration, diagnostics et mises à jour.

### 🔹 Autonomie
L’appareil doit fonctionner :
- sans réseau,
- sans cloud,
- sans dépendances externes.

---

## 3. Objectifs court terme (MVP)

- Monitoring batterie fiable (INA219 + service systemd)
- Audio local + Webradio via MPD
- Lecteur embarqué HTML/JS basé sur `data.json`
- Admin locale minimale (statut batterie, tests audio)
- Arborescence cohérente (`web/`, `scripts/`, `podcasts/`, `data/`)

---

## 4. Objectifs moyen terme

- Ingestion complète des podcasts (RSS → fichiers locaux)
- Génération automatique de `data.json`
- Gestion du contenu (radios, podcasts, langues)
- Amélioration de l’UX (carrousel, transitions, feedback visuel)
- Mode hors-ligne total pour le lecteur

---

## 5. Objectifs long terme

- Synchronisation locale (USB, réseau local)
- Profils enfants (restrictions, favoris)
- Extensions matérielles (LED, capteurs, boutons physiques)
- Migration possible vers une IHM native (Qt, Flutter, Kivy)
- Mode “parent technophile” : logs, monitoring avancé, outils de debug

---

## 6. Valeurs du projet

### 🔹 DIY
Comprendre, apprendre, construire soi-même.  
Le projet doit rester accessible, documenté, reproductible.

### 🔹 Durabilité
Matériel réparable, logiciel simple et maintenable.  
Pas de dépendances opaques.

### 🔹 Accessibilité
Interface pensée pour :
- les enfants,
- les non-technophiles,
- les parents qui veulent partager leur passion.

### 🔹 Évolutivité
Chaque brique peut être améliorée ou remplacée sans réécrire tout le système.

---

## 7. Ce que Hechicero n’est pas

- Pas une enceinte cloud  
- Pas un produit commercial  
- Pas une usine à gaz  
- Pas un système dépendant d’API externes

Hechicero est un **projet personnel**, **pédagogique**, **familial**, conçu pour durer.
