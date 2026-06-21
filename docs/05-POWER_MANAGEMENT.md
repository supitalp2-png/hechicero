# Power Management — Projet Hechicero

Ce document décrit la gestion de l’alimentation et de la batterie du système Hechicero.
Il couvre le monitoring, les services systemd et les règles de robustesse.

---

## 1. Objectif
Assurer :
- un suivi fiable de l’état batterie
- une mise à jour régulière du statut dans l’interface web
- la prévention des coupures brutales
- un shutdown propre lorsque la tension devient critique

---

## 2. Fichiers clés
- `scripts/get_status.py`  
  Lit le capteur, calcule l’état batterie, écrit `web/status.json` (écriture atomique).

- `web/status.json`  
  Fichier lu par l’interface admin.

- `data/config.json`  
  Contient les seuils (warning, critical) et l’intervalle de polling.

- `data/shutdown_pending`  
  Fichier créé lorsque le seuil critique est atteint.

---

## 3. Installation rapide

### 3.1 Créer l’utilisateur système (optionnel)
sudo useradd --system --create-home --shell /usr/sbin/nologin hechicero

### 3.2 Ajouter les groupes nécessaires
sudo usermod -aG i2c,audio,gpio,www-data hechicero

### 3.3 Permissions
sudo chown -R hechicero:hechicero /home/thomas/hechicero
sudo chmod -R 750 /home/thomas/hechicero/scripts
sudo chown -R hechicero:www-data /home/thomas/hechicero/web

---

## 4. Service systemd
Fichier : `/etc/systemd/system/hechicero-battery.service`

[Unit]
Description=Hechicero Battery Monitor
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/get_status.py
Restart=always
User=thomas
WorkingDirectory=/home/thomas/hechicero/scripts
ProtectSystem=full

[Install]
WantedBy=multi-user.target

### Activer le service
sudo systemctl daemon-reload
sudo systemctl enable --now hechicero-battery.service

### Vérifier le statut
systemctl status hechicero-battery.service

---

## 5. Format attendu de `status.json`
{
  "percent": 98,
  "voltage_v": 4.188,
  "current_ma": 0,
  "power_w": 0.006,
  "state": "Sur batterie",
  "alert": null,
  "ts": 1780818044
}

Champs :
- percent : pourcentage estimé  
- voltage_v : tension mesurée  
- current_ma : courant instantané  
- power_w : puissance  
- state : secteur / batterie  
- alert : warning / critical / null  
- ts : timestamp UNIX  

---

## 6. Fréquences
- Frontend (admin web) : polling toutes les 10 s  
- Backend (get_status.py) : intervalle configurable dans `data/config.json`

---

## 7. Recommandations techniques
### Écriture atomique
- écrire dans `status.json.tmp`
- puis `mv status.json.tmp status.json`

### Permissions
- `status.json` : `644`
- propriétaire : `thomas:www-data`

### Validation JSON
- utiliser `json.dumps()`
- flush + fsync avant rename

---

## 8. Shutdown propre
Lorsque la batterie atteint le seuil critique :
1. `data/shutdown_pending` est créé  
2. `status.json` contient `alert: "critical"`  
3. un service externe peut déclencher un `sudo shutdown now`  

---

## 9. Critères d’acceptation
- statut batterie affiché correctement  
- `status.json` mis à jour régulièrement  
- seuils warning / critical détectés  
- fichier `shutdown_pending` créé au bon moment  
- aucun JSON corrompu  

---

## 10. Démarrage automatique et bouton physique
### Problème actuel
Lorsque le Waveshare UPS HAT (D) est alimenté, le Raspberry Pi 5 **ne démarre pas automatiquement**.
Il reste éteint tant que le bouton physique du Raspberry Pi n’est pas pressé.

### Hypothèse
Le Pi 5 nécessite un front logique sur la ligne RUN pour démarrer.
Le HAT ne génère pas ce signal.

### Objectif
Ajouter un **bouton RUN externe** pour un usage normal.

### Pistes techniques
- bouton poussoir sur broches RUN  
- transistor pour simuler l’appui  
- vérifier si le HAT expose une broche ON/OFF  

---

## 11. Comportement attendu en cas de coupure
### 🔹 Si la batterie tombe à 0 %
- le HAT coupe physiquement l’alimentation  
- le Pi s’éteint brutalement si aucun shutdown n’a été anticipé  

### 🔹 Rôle du script `get_status.py`
- détecter la tension critique  
- créer `data/shutdown_pending`  
- signaler l’état “critical” dans `status.json`  

### 🔹 Rôle de l’IHM enfant
- afficher un message “Batterie faible”  
- empêcher le lancement de nouveaux contenus  
- réduire automatiquement le volume  

### 🔹 Rôle de l’interface admin
- afficher l’état critique  
- proposer un bouton “shutdown propre”  

### 🔹 Rôle du système
- déclencher un `shutdown now` si `shutdown_pending` existe  
- éviter toute corruption de fichiers  

### 🔹 Après coupure
- le Pi ne redémarre pas automatiquement (limitation matérielle)  
- l’utilisateur doit appuyer sur le bouton RUN  

---
