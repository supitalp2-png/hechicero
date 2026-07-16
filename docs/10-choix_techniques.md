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

### 🔹 Boîtier : carcasse Grundig Concert Boy 206
Rôle : châssis extérieur du projet (vintage, bois + tissu, tranche supérieure chromée).
Décision : réutiliser un poste radio ancien plutôt qu'un boîtier neuf, pour l'esthétique et la
philosophie DIY/réparation du projet. Un 2e exemplaire du même modèle a été acheté en 2026-07-08
pour l'intégration finale (le premier avait servi aux mesures/gabarits, voir `Photos/04-mesures`
et `05-test-fit`). **Intégration matérielle terminée le 2026-07-08** : écran + haut-parleurs
montés sur la nouvelle façade intérieure, boîtier refermé et fonctionnel — voir `docs/80-hardware.md` §0 et §12.

### 🔹 Sortie casque : bouton physique manuel (pas de détection automatique)
Rôle : basculer la sortie audio entre haut-parleurs (HiFiBerry Amp4) et casque (DAC USB UGREEN).
Deux pistes de détection automatique du branchement ont été testées et **abandonnées
définitivement** :
- comparateur d'impédance LM393 (le DAC USB impose sa tension de sortie, mesure passive inefficace)
- jack à contact mécanique switché câblé sur GPIO (irréalisable en pratique)

Décision finale (2026-07-08) : un bouton-poussoir dédié ("source", GPIO17, à côté de la prise
jack) bascule manuellement HP/casque — solution définitive, pas une étape transitoire. Logique
serveur (volume mémorisé par mode, séquencement anti-pic sonore) dans `radio.php`
(`get_output`/`set_output`), identique que le déclencheur soit ce bouton ou le tap écran. Détail :
`docs/80-hardware.md` §"Sortie casque + détection", `docs/90-BACKLOG.md` TICKET-031.

### 🔹 Boutons physiques : GPIO direct + polling (TICKET-091)
9 broches GPIO (`RPi.GPIO`, `scripts/buttons_daemon.py`) plutôt qu'un MCP23017 I²C ou un Pico USB
HID — plus simple, suffisant pour ce nombre de boutons. Détection par **polling** (~10ms), pas
par interruptions (`add_event_detect()` peu fiable sur la puce GPIO RP1 du Pi 5). Layout du
boîtier réel (7 boutons en ligne + 1 isolé) : bouton "source" (HP/casque) à côté du jack, puis
volume−, précédent, lecture/pause (fusionnés, un bouton de moins que prévu), suivant, volume+,
favori (réservé, fonctionnalité non codée) ; le bouton isolé (emplacement antenne) reste sans
fonction. Détail : `docs/80-hardware.md` §12, `docs/90-BACKLOG.md` TICKET-091.

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
Il attend un signal logique sur la ligne RUN.

### 🔹 Solution retenue ✅
Bouton-poussoir momentané 16mm chromé câblé sur les broches RUN du Pi 5, logé dans la tranche supérieure du boîtier Concert Boy 206. Installé et fonctionnel.

### 🔹 Justification
- indispensable pour un usage enfant  
- contourne la limitation matérielle du Pi 5  
- bouton intégré de façon invisible dans le design du boîtier  

→ Détails hardware : `docs/80-hardware.md` §12

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
