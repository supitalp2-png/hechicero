# Non-régression — Registre des zones à risque

> Dernière mise à jour : 2026-08-05 — création du registre.

Ce document est la **mémoire des pannes** du projet. Il existe parce que sur Hechicero,
les bugs ne reviennent pas par hasard : ils reviennent toujours **aux mêmes endroits**.

Règle fondatrice :

> **Toute panne constatée doit repartir avec un test de garde.**
> Un bug corrigé sans test ajouté n'est pas corrigé, il est en sursis.

L'exécutable de ce document, c'est `scripts/smoke_test.sh`. Ce fichier-ci en est la
carte : il dit *pourquoi* chaque test existe, et *quelles zones ne sont pas encore
couvertes*.

---

## 1. Les trois moments

### 🔸 1.1 Avant une modification — évaluer le risque

Avant d'écrire la moindre ligne, on regarde si le changement touche une zone du §3.
Si oui : **on annonce le risque, on nomme le bug historique correspondant, et on
attend une validation explicite.** Pas de « je pense que ça passe ».

Le format d'alerte attendu :

```
⚠️ RISQUE DE RÉGRESSION — Zone Z2 (services durcis)
   Historique  : TICKET-011 → TICKET-120, boutons physiques morts 2 semaines sans alerte
   Ce qui peut casser : le service ne pourra plus écrire son tube dans scripts/
   Vérification après : test 5 du smoke test + retrait manuel du fichier de travail
   → Tu valides ce risque ?
```

### 🔸 1.2 Après une modification — vérifier que ça marche encore

Le minimum non négociable : **la radio joue toujours**. Le smoke test le prouve.
Voir §4 pour le bloc de commandes.

Aucune livraison n'est déclarée saine tant que le smoke test n'est pas passé au vert
(ou que ses avertissements ne sont pas expliqués un par un).

### 🔸 1.3 Après un bug — apprendre

Dès qu'une panne est comprise, avant même de la corriger :

1. Ajouter ou compléter une zone au §3 (le piège, pas seulement le symptôme).
2. Écrire le test de garde dans `scripts/smoke_test.sh`.
3. Vérifier que **le nouveau test échoue sur le code d'avant le correctif**. Un test
   de garde qui n'aurait pas attrapé le bug d'origine ne sert à rien.
4. Mettre à jour le §5 si la zone passait de « non couverte » à « couverte ».

---

## 2. Ce qui compte comme « la radio fonctionne »

Par ordre de gravité. Les trois premiers sont bloquants : si l'un tombe, l'objet est
mort pour l'enfant, et aucune fonctionnalité ne justifie de les casser.

| # | Fonction vitale | Preuve |
|---|-----------------|--------|
| V1 | MPD répond et peut jouer | sonde socket Unix sous `timeout` (jamais `mpc`) |
| V2 | L'écran s'allume et l'IHM répond au toucher | `screen_dpms.sh status` + rendu kiosque |
| V3 | Le catalogue se charge (`data.json` valide) | endpoint `data_version` + rechargement observé |
| V4 | Les boutons physiques répondent | `buttons_daemon` vivant **et** tube lgpio recréable |
| V5 | Lecture d'un podcast **local**, réseau coupé | invariant §1.1 de `15-INVARIANTS.md` |
| V6 | Webradio, réseau présent | dépend du réseau, donc jamais bloquant |

---

## 3. Registre des zones à risque

### 🔴 Z1 — MPD : démon, socket, flux réseau

**Le piège** : MPD se fige **sans crasher et sans rien journaliser**. `systemctl status`
affiche `active (running)` pendant que plus rien ne joue. Quand un flux HTTP meurt sans
`FIN` ni `RST` (partage de connexion qui disparaît), la socket devient un trou noir, le
thread `io` reste parqué en tenant le verrou du flux, et tout le démon s'empile derrière.

**Le piège dans le piège** : `mpc` **n'échoue pas** face à un MPD figé — il attend. Tout
test qui passe par `mpc` se fige avec lui et ne rapporte jamais rien. C'est ce qui a permis
à un MPD bloqué de passer 24 h inaperçu.

**Fichiers** : `/etc/mpd.conf`, `scripts/mpd_watchdog.py`, `web/radio.php`, `web/lecteur/radio.php`

**Historique** : TICKET-122 (figeage réseau) · TICKET-030 (incident `mpd.socket` via alsaequal,
procédure de récupération en §6.4.1) · reprise auto au boot (`restore_paused` absent de `mpd.conf`)

**Test de garde** : smoke test §5 — sonde `/run/mpd/socket` via `mpd_watchdog.py --probe`
sous `timeout 10`, + vérification que `mpd_watchdog` tourne.

**Règles à ne jamais enfreindre** :
- Jamais de `mpc` dans un script de test ou de surveillance.
- Toute sonde MPD porte un délai de garde.
- Ordre impératif de récupération : `stop mpd.service` → `reset-failed` → `start mpd.socket`.

---

### 🔴 Z2 — Services systemd durcis

**Le piège** : depuis le durcissement, `ProtectSystem=strict` rend le dépôt non
inscriptible. Un service qui a besoin d'écrire un fichier de travail dans `scripts/`
**ne tombe pas au moment du durcissement** — il continue de tourner tant qu'un fichier
créé *avant* traîne encore. La panne se déclare des semaines plus tard, sur une action
sans rapport, ou immédiatement sur une image SD fraîchement restaurée.

C'est le pire type de bug du projet : latent, invisible, et **non couvert par la sauvegarde**.

**Fichiers** : les 8 `scripts/*.service`

**Historique** : TICKET-011 (durcissement) → TICKET-120 (boutons physiques morts 2 semaines
plus tard, découvert par hasard) → TICKET-121 (audit des 7 autres, **ouvert**)

**Deuxième piège de la même zone, confirmé le 2026-08-05 (TICKET-122)** : `Requires=`
ne fait pas qu'ordonner le démarrage, il **propage l'arrêt**. `buttons_daemon`,
`play_tracker` et `audio_eq_apply` le portaient sur `mpd.service` : réparer MPD — ou
simplement le redémarrer — éteignait les boutons physiques et arrêtait le suivi
d'écoute. Pour `play_tracker` c'est silencieux : on perdrait des semaines de
statistiques sans rien voir. Les trois sont passés en `Wants=`.

Ces deux pièges ont la même origine : le durcissement de juillet a été appliqué **en
recopiant un modèle d'unité d'un service à l'autre**, sans vérifier ce que chaque
directive impliquait pour ce service précis. L'audit doit donc porter sur **toutes** les
directives, pas seulement `ReadWritePaths`.

**Test de garde** : smoke test §6 — quatre contrôles statiques : absence de
`Requires=mpd`, `WorkingDirectory` sous `/run` avec `RuntimeDirectory=` pour
`buttons_daemon`, absence de `PrivateDevices=`, et **dérive entre le dépôt et
`/etc/systemd/system/`** (une unité corrigée mais jamais recopiée donne l'illusion que le
correctif est livré).
⚠️ **Reste non couvert** : la preuve qu'un service recrée son fichier de travail après
suppression. C'est le faux positif de TICKET-120, et c'est l'objet de TICKET-121.

**Règles** :
- Un service durci **n'écrit jamais dans le dépôt**.
- Répertoire de travail volatil → `RuntimeDirectory=` (systemd le crée et le nettoie).
- État persistant → `data/`, déjà dans `ReadWritePaths`.
- **Jamais `PrivateDevices=`** (casse l'accès GPIO et audio).
- Validation d'un durcissement = **supprimer le fichier de travail, redémarrer, vérifier
  qu'il se recrée**. Pas « le service est vert ».

---

### 🟠 Z3 — Boutons physiques GPIO

**Le piège** : `buttons_daemon` peut être `active (running)` tout en étant incapable de
lire un appui (cf. Z2). Le mapping des 9 boutons est confirmé mais fragile : `next`/`prev`
sont tap-ou-maintien (maintien = seek 5 s), GPIO16 = favoris, GPIO23 = réveil écran.

**Fichiers** : `scripts/buttons_daemon.py`, `scripts/buttons_daemon.service`

**Historique** : TICKET-120 · TICKET-046 (favoris) · TICKET-112 (GPIO23)

**Test de garde** : partiel — smoke test §5 (service vivant). **La couverture réelle
manque** : rien ne prouve qu'un appui produit une action.

---

### 🟠 Z4 — Écran, veille et DPMS

**Le piège** : `wlr-randr --on --preferred` est un **no-op silencieux** si la sortie est
déjà dans le bon mode — la dalle reste noire alors que la commande renvoie 0. Il faut un
**rebond de mode** pour la réveiller. Symétriquement, `on` sur un écran déjà allumé ne
doit **rien** faire, sinon le bouton antenne fait clignoter l'écran.

Deuxième piège, plus vicieux : un timer périodique peut **réarmer le timer de veille en
boucle**. `checkParentalTime` (30 s) était plus court que `sleep_delay` : l'écran ne
s'éteignait jamais.

**Fichiers** : `scripts/screen_dpms.sh`, `scripts/idle_screen.sh`, `web/lecteur/index.html`

**Historique** : TICKET-115 (écran noir) · TICKET-102 (veille jamais déclenchée)

**Test de garde** : smoke test §1 — md5 de conformité, présence des 4 actions
(`off`/`on`/`rescue`/`status`), syntaxe bash, et vérification du no-op anti-clignotement
dans `data/screen_dpms.log`.

**Règle** : toute nouvelle boucle périodique côté IHM doit être vérifiée contre
`sleep_delay` avant d'être ajoutée.

---

### 🟠 Z5 — `data.json` et rafraîchissement du catalogue

**Le piège** : `data.json` est la **source unique** du lecteur. Deux régressions typiques :
le tick périodique qui recharge les données **sans jamais re-rendre** (le catalogue neuf
n'apparaît pas), et le re-rendu qui frappe pendant la lecture (l'écran de lecture clignote
et l'enfant perd sa place).

**Fichiers** : `web/lecteur/data.json`, `web/lecteur/index.html`, `web/lecteur/radio.php`

**Historique** : TICKET-114 (catalogue auto)

**Test de garde** : smoke test §2, §3 et §4 — syntaxe PHP, endpoint `data_version`,
présence de `pollCatalogVersion` / `refreshCatalogInPlace` / `findEpisodeByAudio`, polling
armé à 10 s, tick 5 min corrigé, garde-fou `player`/`radio-player`, et preuve indirecte
par le journal Apache que le kiosque recharge réellement après un `touch`.

**Règles** : écriture atomique obligatoire (`write_json_atomic()`), et **jamais écraser un
JSON valide** — en cas d'erreur, on garde l'ancien.

---

### 🟠 Z6 — Chaîne audio : ALSA, égaliseur, sorties

**Le piège** : les **numéros de carte ALSA (`hw:N,0`) ne sont pas stables** d'un boot à
l'autre. Toute référence par numéro finit par pointer la mauvaise carte. On référence
**toujours par nom** (`hw:CARD=…`) dans `mpd.conf`.

`alsaequal` écrit des états binaires dans `data/` : deux fichiers de **840 octets** sont
sains ; une taille différente signale l'incident de TICKET-030, dont la récupération passe
par la séquence `mpd.socket` (Z1).

**Fichiers** : `/etc/mpd.conf`, `scripts/audio_eq_apply.py`, `web/admin/audio_eq.php`,
`data/alsaequal_hp.bin`, `data/alsaequal_casque.bin`

**Historique** : bug sortie HP/casque (cartes instables) · TICKET-030 (EQ 10 bandes,
2 profils) · TICKET-116 (gain casque)

**Test de garde** : ⚠️ **manquant**. À écrire : `grep hw:CARD= /etc/mpd.conf` (et absence
de `hw:[0-9]`), taille des deux `.bin`, et `speakers_max ≤ 80` dans `config.json`.

**Règle de sécurité enfant** : `speakers_max` ne dépasse jamais 80. C'est un invariant,
pas un réglage.

---

### 🟡 Z7 — Réseau Wi-Fi

**Le piège** : les coupures Wi-Fi ne sont pas un bug à corriger, c'est une **condition
d'exploitation**. L'invariant est que tout le reste continue de marcher sans réseau. Une
modif qui rend une fonction locale dépendante du réseau est une régression, même si elle
marche parfaitement à la maison.

**Fichiers** : `scripts/wifi_watch.sh`, `scripts/wifi_roam.py`

**Historique** : TICKET-109 / TICKET-110 (4 épisodes) · déclencheur de TICKET-122

**Test de garde** : ⚠️ **manquant**. Le seul test qui vaudrait : couper le réseau et
vérifier qu'un podcast local joue toujours. Manuel pour l'instant.

---

### 🟡 Z8 — Batterie et cycles

**Le piège** : `level_end` était écrasé pendant la charge, ce qui **invalidait à tort les
vrais cycles profonds**. Un bug de mesure, donc silencieux : rien ne casse, les chiffres
sont juste faux.

**Fichiers** : `scripts/battery_tracker.py`, `scripts/battery_watchdog.py`,
`scripts/battery_common.py`, `data/tracking.db`

**Historique** : bug cycles batterie (réparé 2026-07-06) · TICKET-011 (`battery_watchdog`
est le seul des 8 services durcis dont le comportement d'arrêt n'a **jamais été prouvé**)

**Test de garde** : partiel — smoke test §5 (services vivants). La cohérence des cycles
n'est pas vérifiée.

---

### 🟡 Z9 — Ingestion RSS et intégrité du catalogue

**Le piège** : la dédup, le tri et les trailers ont été généralisés ; toute modif du
parseur peut réintroduire des doublons ou des épisodes orphelins (fichier audio sans
entrée, ou l'inverse). La synchronisation admin doit rester **résiliente par podcast** :
un flux cassé ne doit jamais faire tomber l'ingestion des autres.

**Fichiers** : `scripts/rss_ingest/`

**Historique** : TICKET-104 / TICKET-105

**Test de garde** : `scripts/rss_ingest/check_integrity.py` (existant, à intégrer au
smoke test).

---

### 🟡 Z10 — Dépôt public et vie privée

**Le piège** : le dépôt est public. Un prénom réel qui part dans un commit **ne se
rattrape pas** — il reste dans l'historique. Le risque n'est pas théorique : une fuite a
dû être neutralisée en juillet 2026 (TICKET-118).

**Règle** : aucun prénom réel dans les fichiers versionnés — ni docs, ni scripts, ni JSON
de config, ni commentaires, ni messages de commit. On écrit `le petit`, `papa`, `la maman`.
Seul `private/` (exclu par `.gitignore`) accepte les vrais prénoms.

**Test de garde** : `scripts/check_privacy.sh`, intégré au smoke test (§6).

**La difficulté de conception, et sa solution** : un script versionné **ne peut pas
contenir le prénom qu'il cherche** — le filet deviendrait la fuite. Les motifs vivent donc
dans `private/forbidden_names.txt` (hors dépôt), une expression régulière par ligne. Le
script vérifie d'abord que ce fichier est bien ignoré par git : si `private/` cessait
d'être exclu, c'est la liste elle-même qui partirait sur GitHub.

**Écrire les motifs avec des limites de mot** (`\bprenom\b`). Sans elles, un prénom court
se retrouve à cheval sur deux mots dans les identifiants d'épisodes espagnols de
`data.json` (`...microbio` + `ma el` + `universo...`) et le test crie au loup.

Le balayage porte sur `git ls-files`, pas sur le disque : seul ce qui part réellement sur
GitHub compte.

---

### 🟢 Z11 — Domotique chambre et cohérence des deux IHM

**Le piège** : la commande de la lumière existe **en double** — côté admin
(`web/admin/domotique.php`) et côté enfant (`web/lecteur/index.html`). Corriger d'un seul
côté crée une divergence de comportement, qui est une régression UX même si rien ne plante.

**Comportement de référence** : ampoule grise = éteinte, jaune + halo = allumée ; le
curseur règle l'intensité **et** allume ; un tap sur l'ampoule fait on/off.

**Fichiers** : `web/admin/domotique.php`, `web/lecteur/index.html`

**Historique** : TICKET-112 · TICKET-113

**Test de garde** : ⚠️ **manquant**. Une comparaison de la logique entre les deux fichiers.

---

## 4. Lancer la vérification

Bloc à exécuter en SSH sur le Pi après toute livraison :

```bash
cd ~/hechicero && chmod +x scripts/smoke_test.sh && ./scripts/smoke_test.sh
```

Lecture du verdict :

| Sortie | Signification | Suite |
|--------|---------------|-------|
| 🟢 Tout est vert | Livraison saine | On peut committer |
| 🟡 Avertissements | Rien de cassé, mais des points à expliquer **un par un** | Ne pas ignorer en bloc |
| ⛔ Au moins un échec (code 1) | **La livraison n'est pas saine** | On ne commit pas, on corrige |

Si MPD ne répond pas :

```bash
sudo python3 ~/hechicero/scripts/mpd_watchdog.py --recover
```

---

## 5. Dette de test — zones sans garde automatique

Par ordre d'urgence. C'est la liste de travail de ce document.

| Zone | Ce qui manque | Ticket |
|------|---------------|--------|
| Z2 services durcis | Prouver qu'un service recrée ses fichiers de travail après suppression (les directives d'unité sont désormais couvertes, §6 du smoke test) | TICKET-121 |
| Z6 audio | `hw:CARD=` dans `mpd.conf`, taille des `.bin`, `speakers_max ≤ 80` | — |
| Z3 boutons | Prouver qu'un appui produit une action (pas juste « service actif ») | — |
| Z7 hors réseau | Lecture d'un podcast local, réseau coupé | — |
| Z9 intégrité | Intégrer `check_integrity.py` au smoke test | — |
| Z11 domotique | Cohérence lumière entre `domotique.php` et `lecteur/index.html` | — |
| Z8 batterie | Cohérence des cycles ; comportement d'arrêt de `battery_watchdog` | TICKET-011 |

---

## 6. Ajouter un test de garde

1. **Écrire le test avant le correctif** et vérifier qu'il **échoue** sur le code fautif.
   C'est la seule preuve qu'il couvre vraiment quelque chose.
2. Le ranger dans la section thématique de `scripts/smoke_test.sh`, avec un commentaire
   qui dit **quel bug il surveille** — pas ce qu'il fait, le code le dit déjà.
3. `pass` / `fail` / `warn` : `fail` uniquement si la fonction est réellement cassée. Un
   `fail` qui crie au loup fait ignorer les vrais.
4. Effet de bord : aucun. Le smoke test ne doit **jamais** éteindre l'écran ni interrompre
   une lecture en cours — il tourne pendant que l'enfant écoute.
5. Durée : le smoke test complet reste sous la minute. Au-delà, il ne sera plus lancé.
6. Mettre à jour le §3 (zone) et le §5 (dette) de ce document dans le même commit.

---

## 7. Ce que le smoke test ne saura jamais faire

À vérifier à la main, il n'y a pas de raccourci :

- **Le rendu visuel de l'IHM.** Le test 4 contourne partiellement la limite en observant
  le journal Apache, mais personne ne voit l'écran à sa place.
- **Le son réel.** Qu'un flux joue ne dit rien du niveau, de la distorsion, ni de la sortie
  active (HP ou casque).
- **Le toucher.** Aucun test ne remplace un doigt sur la dalle.
- **L'usage par l'enfant.** La vraie validation de ce projet, c'est qu'il l'allume et que
  ça marche sans que personne n'ait rien à faire.
