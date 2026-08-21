# Installation & Setup du Système — Projet Hechicero

Ce document décrit l’installation complète du système Hechicero sur un Raspberry Pi 5, dans sa configuration actuelle.
Il reflète les choix techniques décrits dans `10-CHOIX_TECHNIQUES.md`.

> *Mis à jour le 2026-08-21.*

---

## 1. Pré-requis

### 🔹 Matériel
- Raspberry Pi 5
- Carte microSD (32 Go minimum)
- HiFiBerry Amp4
- Écran tactile compatible Raspberry Pi
- Waveshare UPS HAT (D)
- Enceintes passives

### 🔹 OS recommandé
**Raspberry Pi OS avec bureau**
Raisons :
- nécessaire pour Chromium (IHM enfant)
- meilleure compatibilité tactile

---

## 2. Installation du système

### 2.1 Installer Raspberry Pi OS (avec bureau)
Utiliser Raspberry Pi Imager :
- OS : Raspberry Pi OS (32-bit) — Desktop
- Activer SSH si souhaité
- Configurer WiFi (optionnel)

Démarrer le Pi et effectuer les mises à jour :
```
sudo apt update && sudo apt upgrade -y
```

---

## 3. Configuration de l’écran tactile

### 3.1 Vérifier la détection
L’écran doit être reconnu automatiquement par Raspberry Pi OS.

### 3.2 Rotation (si nécessaire)
```
sudo nano /boot/firmware/config.txt
```
Ajouter par exemple :
```
display_lcd_rotate=2
```

### 3.3 Écran de veille — ne pas le désactiver

⚠️ **Corrigé le 2026-08-21.** Cette section disait de désactiver la veille via
`raspi-config → Screen Blanking`. Deux raisons de ne pas le faire :

1. **C'est une recette X11**, sans effet sous Wayland/labwc.
2. **La veille est voulue** : l'appareil est sur batterie, et une dalle de 7 pouces
   allumée en permanence coûte cher en autonomie.

Elle est gérée par `hechicero-idle.service` (swayidle + `wlr-randr`), avec le délai
`screen_off_delay` de `web/lecteur/config.json`. Voir `70-SERVICES_SYSTEMD.md` §6 et
`60-KIOSK_MODE.md` §3.

---

## 4. Installation des dépendances

### 4.1 Paquets système
```
sudo apt install -y \
    mpd mpc \
    apache2 php \
    python3 python3-pip python3-requests python3-feedparser \
    python3-smbus i2c-tools \
    jq git chromium          # ⚠️ le paquet s'appelle `chromium`, pas `chromium-browser`
```

### 4.2 Activer I2C (INA219)
```
sudo raspi-config
```
Menu → Interface Options → I2C → Enable

Vérifier :
```
sudo i2cdetect -y 1
```

---

## 5. Installation du projet Hechicero

### 5.1 Cloner le dépôt
```
cd ~
git clone https://github.com/<ton_repo>/hechicero
```

### 5.2 Arborescence attendue
```
~/hechicero/
├── data/
├── docs/
├── podcasts/
├── scripts/
├── UX Design/
└── web/
```

---

## 6. Configuration MPD

### 6.1 Fichier `/etc/mpd.conf`
Points essentiels :
- utiliser la carte HiFiBerry
- activer le volume logiciel
- ⚠️ **référencer les cartes ALSA par nom (`hw:CARD=...`), jamais par numéro (`hw:2,0`)** — l'ordre d'énumération des cartes (HiFiBerry vs DAC USB casque) n'est pas garanti stable d'un boot à l'autre ; un numéro fixe a fini par pointer vers le mauvais périphérique (bug du 2026-07-03, cf. [[project_hechicero_audio_output]])
- ⚠️ **`restore_paused "yes"` juste après `state_file`, obligatoire.** Config Debian par défaut : `state_file "/var/lib/mpd/state"` sans `restore_paused` → MPD restaure aussi l'état play/pause au démarrage, pas juste la position. Si MPD a été relancé en état "playing" avant un redémarrage du Pi, la lecture repart toute seule au boot, sans action sur l'IHM (bug découvert le 2026-07-19). `restore_paused "yes"` garde la reprise de position mais force l'état pause au démarrage.

Extrait (noms de cartes à vérifier avec `aplay -l` / `cat /proc/asound/cards`) :
```
audio_output {
    type        "alsa"
    name        "My ALSA Device"
    device      "hw:CARD=sndrpihifiberry,DEV=0"
    mixer_type  "software"
}
audio_output {
    type        "alsa"
    name        "Casque USB"
    device      "hw:CARD=Audio,DEV=0"
    mixer_type  "software"
}
```

### 6.2 Redémarrer MPD
```
sudo systemctl restart mpd
```

### 6.3 Test audio
```
mpc clear
mpc add "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3"
mpc play
```

### 6.4 Égaliseur audio (TICKET-030, alsaequal)

✅ **Validé en conditions réelles le 2026-07-18** — cette procédure est celle
qui a réellement fonctionné après plusieurs incidents en direct (voir
`docs/90-BACKLOG.md` TICKET-030 pour le récit complet). **Suivre l'ordre
exact ci-dessous**, deux pièges sinon :
1. Ne **jamais** pré-créer les fichiers `controls` avec `touch` — un fichier
   vide fait planter alsaequal en `SIGBUS` (mmap sur fichier de taille 0),
   et si ça arrive pendant que MPD tourne, **ça peut faire planter MPD
   lui-même** et griller le disjoncteur anti-boucle de `mpd.socket` (cf.
   §6.4.1 ci-dessous pour la procédure de récupération si ça arrive quand
   même).
2. `www-data` doit être dans le groupe `audio` **avant** de tester la page
   admin, sinon `Operation not permitted` / `Mixer attach ... error`.

La HiFiBerry Amp4 est un DAC pur, sans égaliseur matériel — traitement
logiciel via le plugin ALSA "equal" (paquet `libasound2-plugin-equal`),
suivant le guide officiel HiFiBerry :
https://www.hifiberry.com/docs/software/guide-adding-equalization-using-alsaeq/

Deux instances **indépendantes** sont nécessaires (une par sortie HP/casque
existante, cf. §6.1) :

```bash
sudo apt-get install -y libasound2-plugin-equal
sudo usermod -aG audio www-data
sudo systemctl restart apache2
```

⚠️ **Le paramètre `controls` ci-dessous est indispensable, pas optionnel.**
Sans lui, alsaequal stocke son état dans `$HOME/.alsaequal.bin` — **par
utilisateur, pas par instance nommée**. Constaté en conditions réelles :
`eqhp` et `eqcasque` semblaient partager le même état (régler l'un
changeait l'autre) simplement parce que tous les tests tournaient sous
`thomas`, donc les deux écrivaient dans le même fichier. Côté web,
`www-data` a `$HOME=/var/www` qu'il ne peut pas écrire → `Failed to open
controls file:/var/www/.alsaequal.bin`. Un `controls` distinct par bloc
règle les deux problèmes (indépendance réelle + permissions).

Ajouter à `/etc/asound.conf` (noms de cartes à vérifier avec `aplay -l`,
mêmes noms que §6.1) :
```
ctl.eqhp {
  type equal;
  controls "/home/thomas/hechicero/data/alsaequal_hp.bin";
}
pcm.plugequal_hp {
  type equal;
  slave.pcm "plughw:CARD=sndrpihifiberry,DEV=0";
  controls "/home/thomas/hechicero/data/alsaequal_hp.bin";
}
pcm.eqhp {
  type plug;
  slave.pcm plugequal_hp;
}

ctl.eqcasque {
  type equal;
  controls "/home/thomas/hechicero/data/alsaequal_casque.bin";
}
pcm.plugequal_casque {
  type equal;
  slave.pcm "plughw:CARD=Audio,DEV=0";
  controls "/home/thomas/hechicero/data/alsaequal_casque.bin";
}
pcm.eqcasque {
  type plug;
  slave.pcm plugequal_casque;
}
```

Créer le dossier d'état (mais **PAS** les fichiers eux-mêmes, cf. piège #1
en tête de §6.4) :
```bash
mkdir -p ~/hechicero/data
```

Modifier `/etc/mpd.conf` (§6.1) pour pointer sur les nouveaux devices
virtuels au lieu du hardware direct :
```
audio_output {
    type        "alsa"
    name        "My ALSA Device"
    device      "eqhp"
    mixer_type  "software"
}
audio_output {
    type        "alsa"
    name        "Casque USB"
    device      "eqcasque"
    mixer_type  "software"
}
```

Puis :
```bash
sudo systemctl restart mpd
mpc status   # doit encore jouer normalement à ce stade
```

**Laisser alsaequal créer lui-même les deux fichiers d'état** (taille et
contenu corrects), puis seulement ajuster les permissions :
```bash
amixer -D eqhp sset '00. 31 Hz' 50
amixer -D eqcasque sset '00. 31 Hz' 50
ls -la ~/hechicero/data/alsaequal_hp.bin ~/hechicero/data/alsaequal_casque.bin   # doit afficher une taille non nulle (~840 octets)
sudo chgrp audio ~/hechicero/data/alsaequal_hp.bin ~/hechicero/data/alsaequal_casque.bin
chmod 664 ~/hechicero/data/alsaequal_hp.bin ~/hechicero/data/alsaequal_casque.bin
groups thomas   # vérifier qu'il est bien membre de audio (sinon: sudo usermod -aG audio thomas)
```

**Vérifier** (avant de toucher à l'admin web) que les deux instances
répondent bien indépendamment :
```bash
amixer -D eqhp sset '00. 31 Hz' 20
amixer -D eqcasque sset '00. 31 Hz' 90
amixer -D eqhp sget '00. 31 Hz'      # doit rester ~20
amixer -D eqcasque sget '00. 31 Hz'  # doit rester ~90
```

Noms de contrôle amixer confirmés le 2026-07-18 (paquet
`libasound2-plugin-equal` 0.6-8+b4, Debian trixie arm64) — préfixe
numérique + espace avant l'unité, ex. `'00. 31 Hz'`, `'05. 1 kHz'`,
`'09. 16 kHz'` (déjà à jour dans `BAND_LABELS`, `scripts/audio_eq_apply.py`).
Si un `apt-get upgrade` change un jour ce format, revérifier avec :
```bash
python3 ~/hechicero/scripts/audio_eq_apply.py --list-controls
```

Réglage manuel de secours (sans passer par l'admin) :
```bash
amixer -D eqhp sset '<bande>' <0-100>     # ex: amixer -D eqhp sset '00. 31 Hz' 70
amixer -D eqcasque sset '<bande>' <0-100>
```
⚠️ Ne **pas** utiliser `amixer cset name=...` (interface "raw", incompatible
avec ces contrôles "simples") ni taper les guillemets à la main sans
échappement — en bash, `amixer -D eqhp sset '00. 31 Hz' 80` fonctionne
(les apostrophes sont pour bash, pas pour amixer, ce qui est correct ici
contrairement à `cset`).

Service qui réapplique les gains sauvegardés à chaque boot (alsaequal ne
persiste rien lui-même) — cf. `docs/70-SERVICES_SYSTEMD.md` :
```bash
sudo cp scripts/audio_eq_apply.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now audio_eq_apply
```

Réglage au quotidien : page admin dédiée `/admin/audio_eq.php` (mode
Expert), 10 curseurs × 2 profils (HP/casque), applique en direct sans
redémarrer MPD.

#### 6.4.1 Récupération si MPD/le socket plante (vécu le 2026-07-18)

Si l'IHM ne répond plus du tout (clics sans effet, `curl
".../radio.php?action=status"` renvoie `MPD connection failed`), **ce
n'est pas forcément un bug de l'IHM** — `radio.php` parle à MPD via le
socket Unix `/run/mpd/socket` (`fsockopen('unix:///run/mpd/socket', ...)`),
alors que `mpc` en ligne de commande sans `--host` passe par TCP
(`localhost:6600`) : `mpc status` peut donc sembler fonctionner en SSH
pendant que l'IHM est en réalité coupée de MPD.

Cause vécue : plusieurs crashs MPD en `SIGBUS` rapprochés (ex. suite à un
fichier `controls` alsaequal vide, cf. piège #1) font sauter le disjoncteur
anti-boucle de systemd sur **`mpd.socket`** (pas `mpd.service` — deux
unités distinctes ici, MPD tourne en activation par socket). Un simple
`systemctl restart mpd` ne suffit pas : `mpd.socket` reste `failed
(service-start-limit-hit)` et personne n'écoute plus sur le socket, d'où
`Connection refused` puis, si le fichier socket est supprimé à la main,
`No such file or directory`.

Diagnostic :
```bash
systemctl status mpd.socket   # chercher "failed" / "service-start-limit-hit"
```

Récupération (dans cet ordre exact — démarrer `mpd.socket` pendant que
`mpd.service` tourne déjà donne "Socket service mpd.service already
active, refusing") :
```bash
sudo systemctl stop mpd.service
sudo systemctl reset-failed mpd.socket
sudo systemctl start mpd.socket
systemctl status mpd.socket   # doit afficher "active (listening)"
curl -s "http://<rpi>/lecteur/radio.php?action=status"   # doit renvoyer du texte MPD, pas une erreur
```

---

## 7. Installation du backend (RSS + batterie)

### 7.1 Monitoring batterie
> ⚠️ `scripts/get_status.py` et `hechicero-monitor.service` sont **supprimés** (session 11). Ne pas utiliser.

Scripts actifs :
- `scripts/battery_tracker.py` — collecte données, estimations → `battery_tracker.service`
- `scripts/battery_watchdog.py` — surveillance seuil critique, arrêt propre → `battery_watchdog.service`

Voir `docs/05-POWER_MANAGEMENT.md` pour le détail complet.

### 7.2 Service systemd batterie
Fichier : `/etc/systemd/system/battery_tracker.service`

Activer :
```
sudo systemctl daemon-reload
sudo systemctl enable --now hechicero-battery.service
```

### 7.3 Ingestion RSS (cron nocturne)

L'ingestion est gérée par **cron** (crontab de l'utilisateur `thomas`), pas par un timer systemd.

Ajouter la ligne suivante dans `crontab -e` (en tant que `thomas`) :
```
0 3 * * * umask 002 && python3 /home/thomas/hechicero/scripts/rss_ingest/ingest.py >> /tmp/hechicero_ingest.log 2>&1
```

`umask 002` garantit que les fichiers créés sont lisibles/modifiables par le groupe `www-data`.

Vérifier :
```
crontab -l
```

Logs :
```
tail -f /tmp/hechicero_ingest.log
```

> Un service/timer systemd (`hechicero-rss.service` / `hechicero-rss.timer`) est documenté dans `docs/70-SERVICES_SYSTEMD.md` pour référence, mais n'est **pas activé** — ne pas l'activer sans désactiver le cron d'abord.

---

## 8. Interface Web (Admin)
Servie par Apache dans `~/hechicero/web/`.
Fonctionnalités actuelles :
- statut batterie  
- tests audio  
- diagnostics simples  

### Configuration Apache — relevé du 2026-08-17

Ces valeurs n'étaient documentées nulle part, et les avoir ignorées a coûté deux
allers-retours de diagnostic sur TICKET-127.

| Élément | Valeur |
|---|---|
| Version | `Apache/2.4.68 (Debian)` — il n'existe pas d'Apache 3, la série stable est la 2.4 |
| `DocumentRoot` | `/var/www/html` (`sites-enabled/000-default.conf`), où `~/hechicero/web` est lié |
| `AllowOverride` | **`None`** partout dans `apache2.conf` → **les `.htaccess` sont ignorés** |
| `mod_headers` | absent à l'origine, activé le 2026-08-17 (`sudo a2enmod headers`) |

> 💡 `grep -r` **saute les liens symboliques** rencontrés en cours de récursion : un
> `grep -r DocumentRoot /etc/apache2/sites-enabled/` ne renvoie rien, alors que
> `grep -R` trouve le vhost. `sites-enabled/` ne contient que des liens.

### En-tête anti-cache du lecteur (TICKET-127)

Sans cet en-tête, **une modification d'`index.html` peut ne jamais atteindre l'écran** :
Chromium ressert sa copie en cache, et `restart-kiosk.sh` ne remet pas son profil à zéro
(pas de `--incognito`). Détail du piège : `docs/75-NON_REGRESSION.md` zone Z12.

```bash
sudo a2enmod headers
sudo cp scripts/apache-hechicero-nocache.conf /etc/apache2/conf-available/
sudo a2enconf apache-hechicero-nocache
sudo apachectl configtest        # DOIT dire "Syntax OK" avant de recharger
sudo systemctl reload apache2
curl -sI http://localhost/lecteur/ | grep -i cache-control   # doit montrer no-store
```

À refaire sur toute réinstallation : la conf vit dans `/etc/apache2/`, hors du dépôt.
Le smoke test §3 le détecte (comparaison du `md5` disque / page servie).

---

## 9. Lecteur embarqué (IHM enfant)
Localisé dans :
`~/hechicero/web/lecteur/`

Fonctionne via Chromium en mode plein écran.

Utilise :
- `data.json`  
- MPD local  
→ fonctionne hors réseau  

---

## 10. Mode kiosque (Chromium)

> ⚠️ **Section réécrite le 2026-08-21.** Elle décrivait une configuration **X11/LXDE** —
> `chromium-browser`, `xserver-command` dans `lightdm.conf` — alors que le Pi tourne sous
> **Wayland avec labwc**. Rien de tout cela n'avait d'effet. Détail complet dans
> `docs/60-KIOSK_MODE.md`, qui fait référence.

Le démarrage passe par `~/kiosk.sh`, qui force la sortie audio sur les haut-parleurs
**avant** de lancer Chromium, puis joue le chime une fois la page chargée :

```bash
chromium --ozone-platform=wayland --noerrdialogs --disable-infobars \
         --kiosk http://localhost/lecteur &
```

⚠️ Le binaire s'appelle **`chromium`**, pas `chromium-browser` — voir §2, le paquet apt
porte le même nom.

### L'écran de veille n'est PAS désactivé

C'est voulu : l'appareil est sur batterie. La veille est gérée par
`hechicero-idle.service` (swayidle + `wlr-randr`), avec le délai `screen_off_delay` de
`web/lecteur/config.json`. Voir `70-SERVICES_SYSTEMD.md` §6.

Les recettes X11 (`xset`, `xserver-command`, raspi-config Screen Blanking) sont **sans
effet** sous Wayland.

### Pas de relance automatique de Chromium

Il n'existe pas de `hechicero-kiosk.service`, et il ne doit pas en exister — **décision de
Thomas** : un service qui relance en boucle masque le problème qui a fait tomber le
kiosque. Reprise à la main par `bash ~/hechicero/restart-kiosk.sh`, ou redémarrage.

### Cohérence UX

- affichage immédiat du lecteur
- aucun geste tactile ne quitte le lecteur
- respect des règles définies dans `25-UX_GUIDELINES.md`

⚠️ Depuis TICKET-119, **une sortie volontaire existe** : combinaison casque + antenne
maintenue 3 secondes, puis bouton « Quitter le kiosque ». C'est un outil parent, hors de
portée d'un usage accidentel. Elle demande la règle sudoers suivante :

```bash
echo 'www-data ALL=(root) NOPASSWD: /usr/bin/pkill -u thomas -x chromium' \
  | sudo tee /etc/sudoers.d/hechicero-kiosque
sudo chmod 0440 /etc/sudoers.d/hechicero-kiosque
sudo visudo -c
```

⚠️ **Le mode `0440` n'est pas cosmétique** : un fichier sudoers mal permissionné est
**ignoré en silence**. C'est ainsi que `hechicero-backup` avait perdu ses droits sans que
rien ne le signale, découvert le 2026-08-21. Le smoke test §7 vérifie désormais le mode de
toutes les règles `hechicero-*`.


---

## 11. Tests de validation

### 🔹 Test MPD
```
mpc status
```

### 🔹 Test batterie
```
cat ~/hechicero/web/status.json
```

### 🔹 Test lecteur
Ouvrir Chromium → `http://localhost/lecteur/`
