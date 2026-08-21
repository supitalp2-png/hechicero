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
bootable complète (`dd` compressé en `.img.gz`, nom `hechicero_durcie.img.gz`)
de la carte SD — système, configuration, code et données inclus — stockée
sur un NAS local. Adresse et chemin réseau exacts : voir `data/backup_config.json`
dans le dépôt, ou directement le `README.md` présent à côté de l'image sur
le NAS (pas republié ici volontairement — ce document est public sur GitHub).

Une seule version à la fois ("durcie"), remplacée quand Thomas valide un état
stable du projet (bouton dans l'admin, mode Expert → 💾 Sauvegardes) — pas de
sauvegarde après chaque petit changement, seulement pour les évolutions
majeures. Écriture sur un fichier temporaire puis bascule atomique : jamais
d'état sans version durcie valide, même si le process est interrompu en
cours de route.

Le script ne plante jamais si le NAS est injoignable — il note l'échec dans
`data/backup_state.json` (visible dans l'admin) plutôt que de planter.

En plus de la durcie, le contenu de `private/` (jamais suivi par git, jamais
sur GitHub) est synchronisé vers un dossier séparé du NAS **automatiquement à
chaque commit** — voir §5.

---

## 2. Restaurer une carte SD morte (procédure d'urgence)

Se fait entièrement **depuis un PC Windows** — pas besoin de toucher au Pi
avant la toute dernière étape.

1. Ouvre l'explorateur de fichiers Windows, va sur le dossier de sauvegarde
   sur ton NAS (chemin réseau exact : `data/backup_config.json` dans le
   dépôt, champs `host`/`share`/`subdir`)
2. Récupère `hechicero_durcie.img.gz`
3. Installe **Raspberry Pi Imager** si besoin : https://www.raspberrypi.com/software/
4. Lance Raspberry Pi Imager
5. **"CHOOSE OS"** → tout en bas de la liste → **"Use custom"** → sélectionne le `.img.gz` directement (pas besoin de le décompresser à la main, Raspberry Pi Imager gère le `.gz` nativement)
6. **"CHOOSE STORAGE"** → sélectionne la nouvelle carte SD
   - ⚠️ **Vérifie bien que c'est la bonne carte** — tout son contenu actuel sera écrasé, sans confirmation possible après
7. **"WRITE"** → attendre la fin (plusieurs minutes selon la taille de la carte et la vitesse de la clé/carte)
8. Éjecter proprement la carte, l'insérer dans le Raspberry Pi, brancher l'alimentation
9. Hechicero doit démarrer directement dans sa configuration habituelle — rien d'autre à faire

**Optionnel — remettre le code à jour :** la version durcie n'est refaite que pour
les évolutions majeures, alors que le code est poussé sur GitHub plus souvent.
Après le redémarrage, si tu veux repartir avec le code le plus récent (pas
juste celui de la dernière version durcie) :
```bash
cd ~/hechicero && git pull
```
Le dépôt git est déjà présent sur l'image (inclus dans le ghost complet) —
pas besoin de le re-cloner, un simple `git pull` suffit. Sans risque : la
configuration système (mpd.conf, kiosk.sh, UPower...) n'est pas touchée par
un `git pull`, seuls le code et les docs suivis par git le sont.

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
sudo apt install -y cifs-utils smbclient rsync
```

### 3.3 Règle sudoers (permet à l'admin web *et* au hook git de déclencher une sauvegarde sans mot de passe)

```bash
sudo visudo -f /etc/sudoers.d/hechicero-backup
```
Contenu (deux lignes — la première pour le bouton de l'admin web, la
seconde pour le hook git post-commit qui synchronise `private/`) :
```
www-data ALL=(root) NOPASSWD: /usr/bin/python3 /home/thomas/hechicero/scripts/backup_manager.py validate*
thomas ALL=(root) NOPASSWD: /usr/bin/python3 /home/thomas/hechicero/scripts/backup_manager.py sync_private
```
`visudo` valide la syntaxe automatiquement avant d'enregistrer — ne pas
éditer ce fichier avec un éditeur classique.

⚠️ **Le MODE du fichier compte autant que sa syntaxe, et c'est le piège.** Un fichier
sudoers dont les permissions ne sont pas `0440` est **ignoré en silence** par sudo : aucune
erreur, aucun journal, la règle n'existe simplement plus.

C'est arrivé sur ce fichier même, découvert par hasard le 2026-08-21 en posant une autre
règle :

```
/etc/sudoers.d/hechicero-backup: bad permissions, should be mode 0440
```

**La sauvegarde durcie avait donc perdu ses droits depuis une date inconnue**, et on ne
l'aurait constaté qu'au moment d'en avoir besoin — c'est-à-dire au pire moment.

```bash
sudo chmod 0440 /etc/sudoers.d/hechicero-backup
sudo visudo -c        # doit dire "parsed OK" pour CHAQUE fichier
```

📌 Le smoke test §7 vérifie désormais le mode de **toutes** les règles `hechicero-*`.
`visudo -c` reste le contrôle de référence : il liste tous les fichiers, un par un.

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

### 3.6 Installer le hook git post-commit (synchro private/)

```bash
cp ~/hechicero/scripts/git_hooks_post_commit.sh ~/hechicero/.git/hooks/post-commit
chmod +x ~/hechicero/.git/hooks/post-commit
```
Une fois fait, **plus jamais besoin d'y penser** : chaque `git commit`
déclenche automatiquement une synchro de `private/` vers le NAS en tâche de
fond (§5). Le hook n'est pas suivi par git (dossier `.git/` jamais versionné)
— à refaire une seule fois après une réinstallation complète.

---

## 4. Dépannage

- **"NAS injoignable" dans l'admin** : vérifier que le NAS répond (`ping`
  l'IP configurée dans `data/backup_config.json`, depuis le Pi), que le Pi
  a bien du réseau, que le partage réseau est toujours actif côté NAS.
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
- **`private/` ne se synchronise pas après un commit** : vérifier que le hook
  est bien installé (`ls -la .git/hooks/post-commit`, doit exister et être
  exécutable), que la règle sudoers `thomas` est bien en place (§3.3,
  `sudo -l -U thomas` doit lister la commande), et regarder
  `data/private_sync.log` et la clé `private_sync` de `data/backup_state.json`
  pour la dernière erreur enregistrée.

---

## 5. Contenu privé (`private/`) — synchronisation vers le NAS

`private/` contient de la réflexion perso, des noms réels, et à terme des
éléments non publics du projet (ex : futurs podcasts easter egg) — exclu de
git (`.gitignore`), donc jamais sur GitHub qui est public.

Comme ce dossier n'est pas suivi par git, il n'était protégé par rien entre
deux versions durcies (qui ne sont faites que pour les évolutions majeures).
Pour éviter de perdre ce contenu en cas de carte SD morte, `scripts/backup_manager.py
sync_private` copie `private/` vers un dossier dédié du NAS (séparé de l'image
durcie) — déclenché automatiquement à chaque `git commit` via le hook
`.git/hooks/post-commit` (installation : §3.6).

Points clés :
- **Aucun SSH requis à l'usage** — comme pour la durcie, tout se passe tout
  seul une fois le hook et la règle sudoers en place (§3.3, §3.6).
- **Ne supprime jamais rien côté NAS** (`rsync` sans `--delete`) : une
  suppression accidentelle en local n'efface pas la copie de sauvegarde,
  contrairement à la durcie qui remplace la version précédente —
  volontairement moins strict sur ce point.
- Échoue silencieusement si le NAS est injoignable au moment du commit — pas
  de blocage, juste une entrée dans `data/private_sync.log` et
  `data/backup_state.json` (`private_sync.ok: false`).
- Pas de restauration automatique documentée ici : en cas de besoin, c'est
  une simple copie de fichiers à récupérer manuellement depuis le NAS.
