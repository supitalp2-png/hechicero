# Power Management — Hechicero

## Objectif

Assurer un suivi fiable de l’état batterie via l’interface web, prévenir les coupures brutales,
et permettre un shutdown propre lorsque la tension devient critique.

---

## 1. Fichiers clés

- `scripts/get_status.py`  
  Lit INA219, calcule l’état batterie, écrit `web/status.json` (écriture atomique).

- `web/status.json`  
  Fichier lu par l’interface admin.

- `data/config.json`  
  Contient les seuils (warning, critical) et l’intervalle de polling.

- `data/shutdown_pending`  
  Fichier créé lorsque le seuil critique est atteint.

---

## 2. Installation rapide

### 2.1 Créer l’utilisateur système (optionnel mais recommandé)

sudo useradd --system --create-home --shell /usr/sbin/nologin hechicero

### 2.2 Ajouter les groupes nécessaires

sudo usermod -aG i2c,audio,gpio,www-data hechicero

### 2.3 Permissions

sudo chown -R hechicero:hechicero /home/thomas/hechicero
sudo chmod -R 750 /home/thomas/hechicero/scripts
sudo chown -R hechicero:www-data /home/thomas/hechicero/web

---

## 3. Service systemd

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

## 4. Format attendu de `status.json`

{
  "percent": 98,
  "voltage_v": 4.188,
  "current_ma": 0,
  "power_w": 0.006,
  "state": "Sur batterie 🔋",
  "alert": null,
  "ts": 1780818044
}

### Champs
- **percent** : pourcentage estimé
- **voltage_v** : tension mesurée
- **current_ma** : courant instantané
- **power_w** : puissance
- **state** : secteur / batterie
- **alert** : warning / critical / null
- **ts** : timestamp UNIX

---

## 5. Fréquences

- **Frontend (admin web)** : polling toutes les 10 s  
  (modifiable dans `web/index.php`)

- **Backend (get_status.py)** : intervalle configurable dans `data/config.json`

---

## 6. Recommandations techniques

### Écriture atomique

- écrire dans `status.json.tmp`
- puis `mv status.json.tmp status.json`

### Permissions

- `status.json` : `644`
- propriétaire : `thomas:www-data`

### Validation JSON

- utiliser `json.dumps()`  
- flush + fsync avant rename

### Tests

- simuler valeurs extrêmes  
- vérifier affichage admin  
- vérifier création de `shutdown_pending`

---

## 7. Shutdown propre

Lorsque la batterie atteint le seuil critique :

1. `data/shutdown_pending` est créé  
2. `status.json` contient `alert: "critical"`  
3. un service externe peut déclencher un `sudo shutdown now`  

---

## 8. Critères d’acceptation

- Le dashboard web affiche % / état / alertes  
- `status.json` est mis à jour périodiquement  
- Le système détecte les seuils warning / critical  
- Le fichier `shutdown_pending` est créé au bon moment  
- Aucun JSON corrompu  
