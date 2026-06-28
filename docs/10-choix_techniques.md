# Choix Techniques — Projet Hechicero

## 1. Introduction
Ce document décrit les choix techniques majeurs du projet Hechicero.  
Il complète le manifeste (`00-MANIFESTE.md`) en expliquant **comment** les principes fondateurs se traduisent dans l’architecture réelle.

---

## 2. Système d’exploitation
### 🔹 Choix : Raspberry Pi OS **avec bureau**
Raison :
- nécessité de Chromium pour l’IHM enfant (lecteur web)
- meilleure compatibilité tactile
- développement plus simple de l’interface

Conséquence :
- le projet n’est plus “headless”, mais reste **embarqué** et **autonome**

---

## 3. Matériel
### 🔹 Raspberry Pi 5
Cœur du système, suffisamment puissant pour :
- MPD
- IHM web
- ingestion RSS

### 🔹 HiFiBerry Amp4
Rôle : amplification + sortie enceintes passives  
Justification :
- qualité audio
- compatibilité ALSA
- intégration simple avec MPD

### 🔹 Écran tactile
Modèle : **CUQI 7 pouces IPS HD 1024×600** (compatible Raspberry Pi 3/4/5)  
Rôle : interface enfant principale  
Orientation : **paysage** (1024×600 px)  
Décision :
- l’IHM enfant tourne **directement sur l’écran** via Chromium en mode kiosque
- viewport cible pour l’IHM enfant : **1024×600 px paysage**
- grille podcasts : 3–4 colonnes
- écran lecteur : layout splitté (jaquette gauche / contrôles droite)

### 🔹 Waveshare UPS HAT (D)
Rôle : autonomie + monitoring batterie  
Capteur INA219 utilisé pour :
- tension
- courant
- état batterie

---

## 4. Architecture logicielle
### 🔹 Séparation stricte en trois briques
1. **Backend**  
   - ingestion RSS  
   - génération `data.json`  
   - monitoring batterie  

2. **Lecteur embarqué (IHM enfant)**  
   - HTML/CSS/JS  
   - fonctionne hors réseau  
   - communique avec MPD  

3. **Interface d’administration**  
   - Apache + PHP  
   - diagnostics, logs, statut batterie  

### 🔹 Justification
- modularité  
- robustesse  
- possibilité de remplacer une brique sans casser le reste  

### 🔹 Cohérence UX
L’architecture logicielle doit permettre de respecter les règles définies dans :
- `docs/25-UX_GUIDELINES.md`
- dossier `UX Design/` (vision, personas, parcours, spécifications)

Ces règles UX sont considérées comme des contraintes techniques à part entière.

---

## 5. Audio : MPD + ALSA
### 🔹 Choix : MPD comme moteur audio principal
Raisons :
- stable
- léger
- parfait pour un système embarqué
- support natif des flux web + fichiers locaux

### 🔹 Volume logiciel obligatoire
La HiFiBerry Amp4 **n’a pas de contrôle de volume matériel**.  
Décision :
mixer_type "software"
→ permet à l’IHM enfant de contrôler le volume  
→ évite les niveaux sonores dangereux  

### 🔹 Architecture audio validée
Lecteur HTML/JS → MPD → ALSA → Amp4 → Enceintes

### 🔹 Webradio
Flux Radio France testés et validés :
- lecture stable  
- reconnexion automatique  
- volume logiciel fonctionnel  

---

## 6. IHM enfant (Lecteur)
### 🔹 Choix : commencer en **HTML/CSS/JS**
Raisons :
- rapidité de développement  
- facilité de debug  
- compatibilité immédiate avec l’écran tactile  
- migration possible vers une IHM native plus tard  

### 🔹 Fonctionnement hors réseau
Le lecteur utilise uniquement :
- `data.json`  
- MPD local  
→ aucune dépendance cloud  

### 🔹 Données statiques
`data.json` est la **source unique** pour :
- radios  
- podcasts  
- images  

---

## 7. Backend (Ingestion RSS)
### 🔹 Choix : scripts Python
Raisons :
- simplicité  
- lisibilité  
- robustesse  

### 🔹 Pipeline validé
RSS → téléchargement épisodes → `meta.json` → `data.json` → lecteur  

### 🔹 Service systemd (à finaliser)
Un timer déclenchera l’ingestion périodique.

---

## 8. Monitoring batterie
### 🔹 Choix : INA219 + Python
- lecture tension / courant  
- calcul état batterie  
- écriture atomique dans `web/status.json`  

### 🔹 Service systemd
- redémarrage automatique  
- robustesse en cas de coupure  

---

## 9. Comportement du Raspberry Pi 5 au boot
### 🔹 Problème
Le Raspberry Pi 5 **ne démarre pas automatiquement** lorsque le Waveshare UPS HAT (D) est alimenté.
Il attend un signal logique équivalent à l’appui sur le bouton POWER.

### 🔹 Conséquence
Un **bouton RUN externe** est nécessaire pour un usage normal.

### 🔹 Choix technique
- utiliser les broches RUN du Pi 5  
- ajouter un bouton poussoir externe  
- possibilité d’ajouter un transistor pour simuler l’appui  

### 🔹 Justification
- indispensable pour un usage enfant  
- contourne la limitation matérielle du Pi 5  
- compatible avec le HAT  

---

## 10. Invariants techniques
Ces règles ne doivent **jamais** être violées :
- le lecteur doit fonctionner hors réseau  
- `data.json` doit toujours être valide  
- écriture atomique obligatoire pour les fichiers critiques  
- MPD doit démarrer automatiquement au boot  
- aucune dépendance cloud  

---

## 11. Conclusion
Ces choix techniques garantissent un système :
- robuste  
- simple  
- maintenable  
- évolutif  
- adapté à un usage enfant  

Ils sont alignés avec le manifeste et servent de base à toutes les évolutions futures.

---

## Références pour le RTFM :

- Waveshare UPS HAT (D) — Documentation officielle  
  https://www.waveshare.com/wiki/UPS_HAT_(D)

- HiFiBerry Amp4 — Documentation officielle  
  https://www.hifiberry.com/docs/hardware/amp4/
