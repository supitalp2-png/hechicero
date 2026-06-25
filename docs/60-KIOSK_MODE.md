# Mode Kiosque — Projet Hechicero

Ce document décrit la configuration du **mode kiosque** pour l’IHM enfant.
Le lecteur doit démarrer automatiquement, en plein écran, sans possibilité de sortir.

Objectifs :
- démarrage automatique de Chromium au boot  
- affichage du lecteur en plein écran  
- aucune barre d’adresse  
- aucune interaction système visible  
- aucune sortie possible du mode kiosque  
- désactivation de l’écran de veille  

---

## 1. Pré-requis
- Raspberry Pi OS **avec bureau**  
- Chromium installé  
- Lecteur accessible via : `http://localhost/lecteur/`

---

## 2. Script de démarrage (`~/kiosk.sh`)

Le démarrage kiosque est géré par `~/kiosk.sh`, appelé depuis `~/.config/lxsession/LXDE-pi/autostart`.

Contenu actuel :
```bash
#!/bin/bash
chromium --noerrdialogs --disable-infobars --kiosk http://localhost/lecteur &
sleep 12
python3 /home/thomas/hechicero/scripts/play_chime.py
```

Points clés :
- Chromium lancé **en arrière-plan** (`&`) pour ne pas bloquer le script
- Le chime joue après un délai (ajustable) pour attendre que la page soit chargée
- **Ne pas remettre le chime avant Chromium** — il jouerait au boot de l’OS, pas à l’affichage du lecteur

Appelé depuis :
```
# ~/.config/lxsession/LXDE-pi/autostart
@/home/thomas/kiosk.sh
```

Pour relancer Chromium depuis SSH sans reboot :
```bash
bash ~/hechicero/restart-kiosk.sh
```

---

## 3. Désactiver l’écran de veille
### 3.1 Via raspi-config
```
sudo raspi-config
```
Display Options → Screen Blanking → Disable

### 3.2 Via LightDM (plus robuste)
```
sudo sed -i 's/^#xserver-command=.*/xserver-command=X -s 0 -dpms/' /etc/lightdm/lightdm.conf
```

### 3.3 Via LXDE (fallback)
Éditer :
```
nano ~/.config/lxsession/LXDE/autostart
```
Ajouter :
```
@xset s off
@xset -dpms
@xset s noblank
```

---

## 4. Relance automatique de Chromium (optionnel)
Créer un service systemd utilisateur :
```
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/hechicero-kiosk.service
```

Contenu :
```
[Unit]
Description=Hechicero Kiosk Mode
After=graphical-session.target

[Service]
ExecStart=/usr/bin/chromium-browser --kiosk --incognito http://localhost/lecteur/
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
```

Activer :
```
systemctl --user enable --now hechicero-kiosk.service
```

Effets :
- Chromium redémarre automatiquement en cas de crash  
- l’enfant ne voit jamais le bureau  

---

## 5. Invariants du mode kiosque
Ces règles ne doivent **jamais** être violées :

- Chromium doit démarrer automatiquement  
- le lecteur doit être en plein écran  
- aucune barre d’adresse  
- aucune possibilité de quitter le lecteur  
- aucune interaction système visible  
- écran de veille désactivé  
- aucune fenêtre parasite  
- aucune mise à jour Chromium visible  

---

## 6. Tests de validation
### 🔹 Test 1 : reboot complet
```
sudo reboot
```
Attendu :
- écran noir → LightDM → Chromium plein écran → lecteur  

### 🔹 Test 2 : crash Chromium
```
pkill chromium
```
Attendu :
- relance automatique  

### 🔹 Test 3 : écran tactile
- boutons cliquables  
- pas de scroll parasite  

### 🔹 Test 4 : sortie impossible
- aucun geste ne doit quitter Chromium  

---

## 7. Notes
- Le mode kiosque est **critique** pour l’usage enfant  
- Toute modification doit être testée sur un reboot complet  
- Le fichier autostart est prioritaire sur le service systemd utilisateur  

---
