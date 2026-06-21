# Hardware — Projet Hechicero

Ce document décrit l’ensemble du matériel utilisé dans le projet Hechicero,
ainsi que les contraintes, câblages, comportements et invariants associés.

Objectifs :
- centraliser toutes les informations matérielles  
- éviter les erreurs de câblage  
- documenter les comportements spécifiques du Raspberry Pi 5  
- garantir un système stable, réparable et reproductible  

---

## 1. Liste du matériel

### 🔹 Raspberry Pi 5
- cœur du système  
- ports USB 3, HDMI, GPIO 40 broches  
- bouton POWER physique intégré  
- broches RUN pour démarrage/reset  

### 🔹 Waveshare UPS HAT (D)
- alimentation + batterie  
- capteur INA219 intégré  
- connecteur GPIO pass‑through  
- ne déclenche **pas** le démarrage automatique du Pi 5  

### 🔹 HiFiBerry Amp4
- amplification audio  
- sortie enceintes passives  
- pas de contrôle de volume matériel  
→ volume logiciel obligatoire  

### 🔹 Écran tactile
- interface enfant principale  
- connecté en DSI ou HDMI selon modèle  
- nécessite Raspberry Pi OS avec bureau  

### 🔹 Bouton RUN externe
- indispensable pour démarrer le Pi 5 avec le HAT  
- équivalent à un appui sur le bouton POWER  

---

## 2. Comportement du Raspberry Pi 5 au boot
Le Raspberry Pi 5 **ne démarre pas automatiquement** lorsqu’il est alimenté via un HAT.

### 🔹 Pourquoi ?
Le Pi 5 attend un **front logique** sur la ligne RUN (ou un appui sur le bouton POWER).
Le Waveshare UPS HAT (D) n’envoie **aucun signal RUN** au boot.

### 🔹 Conséquence
→ Le Pi reste éteint tant qu’un bouton n’est pas pressé.  
→ Inacceptable pour un usage enfant.  

### 🔹 Solution
Ajouter un **bouton RUN externe** relié aux broches RUN du Pi 5.

---

## 3. Broches RUN du Raspberry Pi 5
Les broches RUN sont situées sur un connecteur 2 broches dédié.

### 🔹 Fonction
- court‑circuiter RUN = démarrage ou reset  
- équivalent au bouton POWER  

### 🔹 Câblage bouton RUN
```
[Bouton poussoir]
  ├──> RUN
  └──> GND
```

### 🔹 Règles
- bouton **momentané** (push button)  
- pas de résistance nécessaire  
- câblage court pour éviter les parasites  

---

## 4. Waveshare UPS HAT (D)
### 🔹 Rôle
- alimentation sur batterie  
- mesure tension/courant via INA219  
- protection contre les coupures  

### 🔹 Limitations
- ne déclenche pas RUN → pas de boot automatique  
- nécessite un bouton externe  

### 🔹 Broches utiles
- I2C (INA219)  
- GPIO pass‑through  

### 🔹 Comportement en cas de batterie vide
- coupe physiquement l’alimentation  
- le Pi s’éteint brutalement si aucun shutdown anticipé  

---

## 5. HiFiBerry Amp4
### 🔹 Rôle
- amplification audio  
- sortie enceintes passives  

### 🔹 Contraintes
- pas de contrôle de volume matériel  
→ `mixer_type "software"` obligatoire dans MPD  

### 🔹 Alimentation
- alimenté via le GPIO  
- compatible avec le HAT (stacking)  

---

## 6. Écran tactile
### 🔹 Rôle
- interface enfant principale  

### 🔹 Contraintes
- nécessite Raspberry Pi OS avec bureau  
- nécessite Chromium  
- nécessite désactivation de l’écran de veille  

### 🔹 Tests
- toucher précis  
- pas de scroll parasite  
- pas de zoom multitouch  

---

## 7. Schéma d’empilement matériel
Ordre recommandé :
```
[Écran tactile] (DSI/HDMI)
       │
[Raspberry Pi 5]
       │
[Waveshare UPS HAT (D)]
       │
[HiFiBerry Amp4]
       │
[Enceintes passives]
```

---

## 8. Invariants matériels
Ces règles ne doivent **jamais** être violées :

- le Pi 5 doit pouvoir démarrer via RUN  
- aucun câble ne doit bloquer la ventilation  
- aucun script ne doit écrire dans le firmware  
- aucun composant ne doit être alimenté hors spécifications  
- le HAT doit toujours être correctement enfiché  
- l’écran doit rester lisible en plein jour  

---

## 9. Tests de validation
### 🔹 Test 1 : démarrage via RUN
- alimenter le HAT  
- appuyer sur le bouton RUN  
→ le Pi doit démarrer  

### 🔹 Test 2 : coupure batterie
- débrancher l’alimentation  
- laisser la batterie se vider  
→ le Pi doit s’éteindre proprement si `shutdown_pending` existe  

### 🔹 Test 3 : audio
- MPD doit sortir du son via Amp4  

### 🔹 Test 4 : écran tactile
- toucher précis  
- pas de lag  

---

## 10. Notes
- Le matériel doit rester simple, robuste et réparable  
- Toute modification matérielle doit être documentée ici  
- Le bouton RUN est critique pour l’usage enfant  

---
