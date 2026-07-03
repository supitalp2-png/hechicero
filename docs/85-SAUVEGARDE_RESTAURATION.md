# Sauvegarde & Restauration — TICKET-085

Ce document couvre deux choses : comment **restaurer** une carte SD morte
(procédure d'urgence, pensée pour aller vite), et comment le système de
**sauvegarde** est mis en place (pour réinstaller ou dépanner).

Une copie simplifiée de la partie restauration est aussi maintenue
automatiquement dans `Backup Hechicero/README.md` sur le NAS, à côté de
l'image — utile si ce dépôt n'est pas accessible au moment où on en a besoin.

---

## 1. Vue d'ensemble

Sauvegarde **manuelle uniquement** — pas de rythme automatique. Une image
bootable complète (`dd` compressé en `.img.gz`) de la carte SD — système,
configuration, code et données inclus — stockée sur le NAS Freebox :
`\\Freebox_Server\Disque 1\Backup Hechicero\hechicero_durcie.img.gz`.

Une seule version à la fois ("durcie"), remplacée quand Thomas valide un état
stable du projet (bouton dans l'admin, mode Expert → 💾 Sauvegardes) — pas de
sauvegarde après chaque petit changement, seulement pour les évolutions
majeures. Écriture sur un fichier temporaire puis bascule atomique : jamais
d'état sans version durcie valide, même si le process est interrompu en
cours de route.

Le script ne plante jamais si le NAS est injoignable — il note l'échec dans
`data/backup_state.json` (visible dans l'admin) plutôt que de planter.

---

## 2. Restaurer une carte SD morte (procédure d'urgence)

Se fait entièrement **depuis un PC Windows** — pas besoin de toucher au Pi
avant la toute dernière étape.

1. Ouvre l'explorateur de fichiers Windows, va sur `\\Freebox_Server\Disque 1\Backup Hechicero`
2. Récupère `hechicero_durcie.img.gz`
3. Installe **Raspberry Pi Imager** si besoin : https://www.raspberrypi.com/software/
4. Lance Raspberry Pi Imager
5. **"CHOOSE OS"** → tout en bas de la liste → **"Use custom"** → sélectionne le `.img.gz` directement (pas besoin de le décompresser à la main, Raspberry Pi Imager gère le `.gz` nativement)
6. **"CHOOSE STORAGE"** → sélectionne la nouvelle carte SD
   - ⚠️ **Vérifie bien que c'est la bonne carte** — tout son contenu actuel sera écrasé, sans confirmation possible après
7. **"WRITE"** → attendre la fin (plusieurs minutes selon la taille de la carte et la vitesse de la clé/carte)
8. Éjecter proprement la carte, l'insérer dans le Raspberry Pi, brancher l'alimentation
9. Hechicero doit démarrer directement dans sa configuration habituelle — rien d'autre à faire

---

## 3. Mise en place du système de sauvegarde (installation / réinstallation)

Ces étapes sont déjà faites sur le Hechicero actuel (2026-07-03) — à refaire
seulement en cas de réinstallation complète du système.

### 3.1 Fichier d'identifiants NAS (root uniquement, jamais dans le dépôt git)

```bash
sudo nano /etc/hechicero-nas-credentials
```
Contenu :
```
username=<compte Freebox utilisé pour accéder au partage>
password=<mot de passe correspondant>
```
```bash
sudo chmod 600 /etc/hechicero-nas-credentials
sudo chown root:root /etc/hechicero-nas-credentials
```

### 3.2 Paquets requis

```bash
sudo apt install -y cifs-utils smbclient
```

### 3.3 Règle sudoers (permet à l'admin web de déclencher une validation durcie)

```bash
sudo visudo -f /etc/sudoers.d/hechicero-backup
```
Contenu (une seule ligne) :
```
www-data ALL=(root) NOPASSWD: /usr/bin/python3 /home/thomas/hechicero/scripts/backup_manager.py validate*
```
`visudo` valide la syntaxe automatiquement avant d'enregistrer — ne pas
éditer ce fichier avec un éditeur classique.

### 3.4 Test manuel (optionnel, une seule fois)

Sert juste à vérifier que la mise en place fonctionne avant de faire confiance
au bouton de l'admin. Une fois ce test passé, **plus jamais besoin de SSH** —
chaque validation future se fait entièrement par un clic dans l'admin
(mode Expert → 💾 Sauvegardes → "Valider une nouvelle version durcie") :
la page web déclenche `backup_manager.py validate` côté serveur via la règle
sudoers (§3.3), qui monte le NAS, fait le ghost et bascule la version durcie
tout seul.

```bash
sudo python3 ~/hechicero/scripts/backup_manager.py validate --label "test"
cat ~/hechicero/data/backup_state.json
```

### 3.5 Config non-secrète

`data/backup_config.json` (dans le dépôt, versionné) : IP du NAS, nom du
partage, sous-dossier. Modifier et committer normalement si besoin (ex :
changer d'IP réseau).

---

## 4. Dépannage

- **"NAS injoignable" dans l'admin** : vérifier que le Freebox Server répond
  (`ping 192.168.1.254` depuis le Pi), que le Pi a bien du réseau, que le
  partage `Disque 1` est toujours actif côté Freebox OS.
- **Échec de montage CIFS** : vérifier `/etc/hechicero-nas-credentials`
  (identifiants toujours valides ? mot de passe changé côté Freebox ?).
- **Validation durcie qui ne se lance pas depuis l'admin** : vérifier la
  règle sudoers (§3.3) — `sudo -l -U www-data` doit lister la commande.
- **Sauvegarde bloquée en cours** (`running: true` qui ne redescend jamais) :
  ```bash
  cat /tmp/hechicero_backup_validate.pid
  ps -p $(cat /tmp/hechicero_backup_validate.pid)
  ```
  Si le process n'existe plus, supprimer le fichier PID :
  `sudo rm /tmp/hechicero_backup_validate.pid`
