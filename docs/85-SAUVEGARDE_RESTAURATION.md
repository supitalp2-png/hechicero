# Sauvegarde & Restauration — TICKET-085

Ce document couvre deux choses : comment **restaurer** une carte SD morte
(procédure d'urgence, pensée pour aller vite), et comment le système de
**sauvegarde automatique** est mis en place (pour réinstaller ou dépanner).

Une copie simplifiée de la partie restauration est aussi maintenue
automatiquement dans `Backup Hechicero/README.md` sur le NAS, à côté des
images — utile si ce dépôt n'est pas accessible au moment où on en a besoin.

---

## 1. Vue d'ensemble

Deux types de sauvegarde, toutes deux des images bootables complètes (`dd`
compressé en `.img.gz`) de la carte SD — système, configuration, code et
données inclus. Stockées sur le NAS Freebox : `\\Freebox_Server\Disque 1\Backup Hechicero`.

- **Durcie** (`hechicero_durcie.img.gz`) — une seule à la fois, remplacée
  manuellement quand Thomas valide un état stable du projet (bouton dans
  l'admin, mode Expert → 💾 Sauvegardes). C'est la version à restaurer par
  défaut en cas de pépin.
- **Quotidienne** (`hechicero_daily_YYYY-MM-DD.img.gz`) — automatique, chaque
  nuit à 3h. Les 7 dernières sont conservées (rotation), les plus vieilles
  sont supprimées automatiquement. Utile pour revenir juste avant un problème
  précis plutôt qu'à la dernière version durcie.

Le Pi n'est pas toujours allumé ou en réseau la nuit : le timer système
(`Persistent=true`) rattrape la sauvegarde manquée au démarrage suivant, et
le script ne plante jamais si le NAS est injoignable — il note l'échec dans
`data/backup_state.json` (visible dans l'admin) et réessaiera la nuit
suivante.

---

## 2. Restaurer une carte SD morte (procédure d'urgence)

Se fait entièrement **depuis un PC Windows** — pas besoin de toucher au Pi
avant la toute dernière étape.

1. Ouvre l'explorateur de fichiers Windows, va sur `\\Freebox_Server\Disque 1\Backup Hechicero`
2. Repère le fichier à restaurer :
   - **`hechicero_durcie.img.gz`** → cas normal, dernière version stable validée
   - **`hechicero_daily_<date>.img.gz`** → si tu veux revenir à une nuit précise
3. Installe **Raspberry Pi Imager** si besoin : https://www.raspberrypi.com/software/
4. Lance Raspberry Pi Imager
5. **"CHOOSE OS"** → tout en bas de la liste → **"Use custom"** → sélectionne le `.img.gz` directement (pas besoin de le décompresser à la main, Raspberry Pi Imager gère le `.gz` nativement)
6. **"CHOOSE STORAGE"** → sélectionne la nouvelle carte SD
   - ⚠️ **Vérifie bien que c'est la bonne carte** — tout son contenu actuel sera écrasé, sans confirmation possible après
7. **"WRITE"** → attendre la fin (plusieurs minutes selon la taille de la carte et la vitesse de la clé/carte)
8. Éjecter proprement la carte, l'insérer dans le Raspberry Pi, brancher l'alimentation
9. Hechicero doit démarrer directement dans sa configuration habituelle — rien d'autre à faire

Si l'image ne boote pas ou que quelque chose cloche : réessayer avec la
sauvegarde quotidienne la plus récente avant celle qui a été tentée, ou
contacter... enfin, se contacter soi-même avec du café.

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

### 3.4 Timer système (sauvegarde quotidienne à 3h)

Les fichiers sont déjà dans le dépôt : `etc/systemd/system/hechicero-backup-daily.service`
et `.timer`. À copier sur le système :

```bash
sudo cp ~/hechicero/etc/systemd/system/hechicero-backup-daily.service /etc/systemd/system/
sudo cp ~/hechicero/etc/systemd/system/hechicero-backup-daily.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hechicero-backup-daily.timer
```

Vérifier :
```bash
systemctl list-timers hechicero-backup-daily.timer
```

### 3.5 Test manuel (sans attendre 3h)

```bash
sudo python3 ~/hechicero/scripts/backup_manager.py daily
cat ~/hechicero/data/backup_state.json
```

### 3.6 Config non-secrète

`data/backup_config.json` (dans le dépôt, versionné) : IP du NAS, nom du
partage, sous-dossier, nombre de sauvegardes quotidiennes conservées. Modifier
et committer normalement si besoin (ex : changer d'IP réseau, augmenter la
rétention).

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
- **Espace NAS insuffisant** : la rotation ne supprime que les sauvegardes
  quotidiennes (`retention.daily_keep` dans `backup_config.json`), jamais la
  durcie. Vérifier l'espace libre avec `df -h /mnt/nas_backup` pendant que
  le NAS est monté.
