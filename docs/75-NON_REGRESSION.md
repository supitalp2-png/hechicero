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

**Test de garde** : smoke test §6 — absence de `Requires=mpd`, **absence de tout
`Requires=`** (généralisé le 2026-08-17 : l'ancien test ne cherchait que `mpd`, c'est
pourquoi `Requires=NetworkManager` dans `wifi_roam.service` était passé), `WorkingDirectory`
sous `/run` avec `RuntimeDirectory=` pour `buttons_daemon`, absence de `PrivateDevices=`, et
**dérive entre le dépôt et `/etc/systemd/system/`** (une unité corrigée mais jamais recopiée
donne l'illusion que le correctif est livré).
Plus, en §5 : absence de `sudo` dans le chemin d'arrêt critique, dépaquetage correct de
`read_level()`, marquage `simulation` du fichier de reprise, alerte si un `battery_critical`
traîne dans `last_session.json`, et détection du HAT. **Les quatre premiers échouent sur le
code d'avant le 2026-08-17** — ce sont donc de vrais tests de garde.
⚠️ **Reste non couvert** : la preuve qu'un service recrée son fichier de travail après
suppression (le faux positif de TICKET-120), et **le test réel d'arrêt critique** — laisser
la batterie descendre sous 15 % en étant présent. Aucun contrôle statique ne prouvera que le
Pi s'éteint vraiment.

**Troisième piège, et le plus coûteux — un durcissement retire un privilège dont le CODE
avait besoin (2026-08-17, TICKET-121)** : `NoNewPrivileges=true` **casse `sudo`**. Or
`battery_watchdog.py` appelait `sudo shutdown -h now`. Le service tournant déjà en
`User=root`, ce `sudo` n'apportait rien — et ne pouvait qu'échouer.

**Pourquoi personne ne l'a vu pendant un mois** : `run_command()` (`battery_common.py`)
avale l'exception **et** le code de retour, il ne renvoie que `stdout`. L'échec était donc
totalement muet. La protection contre la décharge profonde n'a jamais fonctionné depuis le
2026-07-19.

**Et le pire** : `--simulate-critical`, le seul chemin permettant de l'éprouver, était cassé
lui aussi (dépaquetage de deux valeurs sur un tuple de trois). **Les deux défauts se
couvraient l'un l'autre** — le chemin réel muet, et le chemin de vérification inutilisable.
D'où un service resté « le seul non prouvé » pendant un mois sans que ce soit un mystère.

⚠️ **Règle qui en découle** : quand on ajoute une directive de durcissement, **chercher dans
le code les endroits qui utilisaient le privilège retiré** — ne pas se contenter de relire
l'unité. `grep -n "sudo" scripts/*.py` a trouvé en une seconde ce qu'un mois d'usage
apparemment normal avait caché. Les candidats à vérifier : `sudo`, `setuid`, l'écriture hors
`ReadWritePaths`, l'accès à `/dev`, et les sockets d'autres sessions.

⚠️ **Corollaire sur les journaux** : un chemin d'urgence doit **journaliser son échec**. Un
arrêt d'urgence qui rate en silence est pire que pas d'arrêt du tout, puisqu'on se croit
protégé.

⚠️ **Un test ne doit jamais laisser de fausse trace** : `--simulate-critical` écrivait
`last_session.json` avec `shutdown_reason: "battery_critical"`, motif exact sur lequel
`web/index.php::battery_resume_payload()` déclenche la bannière de reprise. Le bureau
d'admin annonçait donc une coupure batterie qui n'avait jamais eu lieu. Le fichier est
toujours écrit — c'est l'objet du test — mais avec le motif `simulation`.

**Résultat de l'audit du 2026-08-17** : les 9 unités passées en revue sur toutes leurs
directives. Trois défauts réels (le `sudo`, le dépaquetage, `Requires=NetworkManager` dans
`wifi_roam.service`), un test menteur, un couplage inutile (`Wants=battery_tracker` dans
`battery_watchdog.service`), et une fausse alerte instructive (`sudo poweroff` dans
`INA219.py`, sous `__main__`, qui a mené à TICKET-128). Les 6 autres unités sont saines.

**Règles** :
- Un service durci **n'écrit jamais dans le dépôt**.
- Répertoire de travail volatil → `RuntimeDirectory=` (systemd le crée et le nettoie).
- État persistant → `data/`, déjà dans `ReadWritePaths`.
- **Jamais `PrivateDevices=`** (casse l'accès GPIO et audio).
- **Jamais `Requires=`** : aucune unité de ce projet n'a de raison d'être arrêtée parce que
  sa dépendance redémarre. `Wants=` + `After=`.
- **Jamais `sudo` dans un script lancé par une unité durcie** — `NoNewPrivileges` le bloque.
  Si le privilège est nécessaire, c'est `User=root` ou `runuser`.
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

**Troisième piège, le plus contre-intuitif (2026-08-05, TICKET-123)** : `swayidle`
n'observe **que les entrées Wayland**. Il ne sait pas si la dalle est allumée, et il ne
voit **jamais** les boutons GPIO, lus par un processus Python. Son cycle est : compter le
délai → lancer `off` → **rester en état « déjà expiré »** jusqu'à une entrée réelle →
lancer `resume` → et seulement alors réarmer.

Donc **réveiller la dalle autrement que par le tactile laisse `swayidle` bloqué**, et
l'écran reste allumé indéfiniment. Prouvé : trois `on` à 18:34, 18:38 et 18:41 n'ont pas
empêché l'extinction programmée de 18:52.

⚠️ **Conséquence pour toute évolution** : appeler `screen_dpms.sh on` **ne remplace pas**
un événement d'entrée. Tout nouveau déclencheur de réveil (bouton, capteur, commande
distante) doit aussi signaler l'activité au compositeur, sinon il fige le cycle de veille.

✅ **Corrigé le 2026-08-17** : `buttons_daemon.signaler_activite()` émet une frappe clavier
virtuelle (`wtype -k Shift_L`, protocole Wayland) à **tout front descendant, sur n'importe
quelle broche**. Le compositeur la compte comme de l'activité, swayidle sort de son état
expiré et réarme.

**Détails qui comptent** :
- Le signal est posé dans la **boucle de polling**, pas dans les handlers : un seul point
  couvre les neuf boutons, y compris les « tap ou maintien » dispatchés à part, et un futur
  bouton en bénéficiera sans qu'on y pense.
- `Shift_L` est une modificatrice **seule** : aucun caractère inséré, aucun clic, donc aucun
  effet possible sur l'IHM enfant. On signale une présence, on ne pilote pas la page.
- **Étranglé à 5 s** : un rebond GPIO ou un bouton maintenu ne doit pas lancer une rafale de
  sous-processus.
- Best-effort en thread détaché, comme `wake_screen()` : ne jamais ralentir la boucle GPIO.
- `wtype` absent → un `warning` une seule fois, et le daemon continue.

**Bénéfice secondaire, au moins aussi important au quotidien** : un enfant qui n'utilise
**que** les boutons physiques voyait son écran s'éteindre au bout de 20 minutes alors qu'il
était en train de s'en servir. Ce n'est plus le cas.

💡 **Méthode de test à réutiliser** — le premier essai a demandé 25 minutes d'attente pour
rien. Il y a beaucoup plus rapide : quand swayidle est **déjà bloqué en état expiré**, le
premier vrai événement d'entrée déclenche son `resume` **immédiatement**, donc une ligne
`[sh<-swayidle] on` dans `data/screen_dpms.log` en une seconde. Cette ligne suffit à prouver
qu'il s'est débloqué — inutile d'attendre l'extinction suivante.

**Test de garde** : smoke test §5 — présence de `signaler_activite()` dans
`buttons_daemon.py` et de l'exécutable `wtype`. Les deux en `fail` : sans l'un ou l'autre, le
cycle de veille se refige silencieusement.

**Quatrième piège — DEUX RÉGLAGES CORRECTS, FAUX UNE FOIS DISSOCIÉS (2026-08-19,
TICKET-138)** : `sleep_delay` (60 s) pilotait l'overlay de veille JS, `screen_off_delay`
(600 s) l'extinction physique par `swayidle`. Deux minuteries indépendantes, sans aucun
lien. Entre les deux : **540 secondes de dalle allumée sur page noire**. En plein jour
l'horloge rétro est illisible, donc l'appareil paraît en panne.

⚠️ **Ce document affirmait que c'était « normal, pas un bug »** — et c'est exactement ce
qui a fait durer le problème des semaines. Signalé plusieurs fois par Thomas, cherché
comme un gel du kiosque (TICKET-127), introuvable : **rien n'était cassé**. Chaque moitié
faisait son travail. Le battement de cœur a innocenté la piste du gel en trente secondes
(2886 battements ininterrompus pendant l'épisode).

> **Cherché comme une panne de composant, un désaccord de configuration est
> introuvable.** Le réflexe « qu'est-ce qui a échoué ? » est aveugle à ce type de bug.

✅ **Corrigé le 2026-08-21** : l'overlay dérive désormais de `screen_off_delay`. Une seule
source de vérité — **aligner les deux nombres n'aurait pas suffi**, deux réglages libres
se désaccordent au premier passage dans l'admin. `sleep_delay` n'est plus qu'un repli.

🔴 **Conséquence à ne pas manquer** : le délai de veille passe de 60 s à **600 s**, alors
que **toutes** les boucles périodiques de l'IHM tournent entre 100 ms et 60 s. Le garde
`changed` de `applySleepConfig` — jusqu'ici une simple optimisation — devient la **seule**
chose qui empêche TICKET-102 de revenir. La marge qui nous protégeait est passée de ×5 à
÷10 en défaveur. Deux tests du smoke test §3 le verrouillent.

**Règle** : toute nouvelle boucle périodique côté IHM doit être vérifiée contre le délai
de veille avant d'être ajoutée — et ce délai vaut maintenant 600 s, donc **aucune** boucle
existante n'est naturellement à l'abri.

**Instrumentation disponible** : depuis TICKET-123, `data/screen_dpms.log` préfixe chaque
ligne de l'appelant sur deux niveaux (`[père<-aïeul]`). Un réveil inexpliqué s'attribue
désormais en une ligne.

**Quatrième piège — un écran noir n'est pas forcément un écran éteint (2026-08-17,
TICKET-127)** : la page peut **cesser d'exécuter du JavaScript** et rester affichée sur sa
dernière image peinte. Si cette image était l'overlay de veille, on obtient un écran noir
que rien ne lève — et **tous les indicateurs habituels restent au vert** : MPD joue, les
boutons GPIO répondent (ils ne passent pas par la page), `wlr-randr` annonce `Enabled: yes`
au mode natif, et `screen_dpms.log` ne contient aucun `off` puisque la dalle n'a jamais été
éteinte. Seul un rechargement de la page rétablit l'image.

⚠️ **Le réflexe de diagnostic à avoir**, dans cet ordre — il évite de repartir sur la
mauvaise piste comme la première fois :

| Observation | Ce que ça veut dire |
|---|---|
| un `off` récent dans `screen_dpms.log` | la dalle a été éteinte → piste DPMS, `screen_dpms.sh rescue` |
| aucun `off`, et `Enabled: yes` | la dalle affiche quelque chose → **c'est la page**, pas l'écran |
| `data/kiosk_heartbeat.json` vieux de plus de 60 s | la page n'exécute plus de JS → TICKET-127 |
| battement frais mais écran noir | overlay de veille bien vivant → chercher côté événements d'entrée |

**Comment on l'a prouvé, et pourquoi c'est solide** : dans `data/sleep_debug.log`, la boucle
de 5 min a écrit `apply_sleep_config` à 07:47:48 puis 07:52:48, et plus jamais. Ce n'était
pas une panne réseau : dans `loadParentalConfig()`, `applySleepConfig()` est appelé **hors
du `try/catch`** — même fetch en échec, la ligne partait quand même. Son silence ne peut
donc venir que de l'arrêt de l'exécution.

**Instrumentation** : la page envoie un battement toutes les 15 s
(`radio.php?action=kiosk_beat`) qui **écrase** `data/kiosk_heartbeat.json` — un état, pas un
journal, donc pas de fichier qui gonfle. `scripts/kiosk_freeze_watch.py` le surveille et,
au-delà de 60 s de silence, écrit **un seul** instantané dans `data/kiosk_freeze.log` :
`vcgencmd get_throttled` (sous-tension — suspect nº 1 depuis le changement de cellules,
TICKET-126), `wlr-randr`, état des processus Chromium (`stat`, `wchan`, RSS), `free -m`,
`dmesg`, `journalctl` des 10 dernières minutes, sonde du socket MPD. **Il observe
uniquement** : aucune relance de Chromium, aucun rebond de mode (décision de Thomas — un
guetteur qui répare masque la panne).

⚠️ **Contrainte sur le battement** : à 15 s il est bien plus rapide que `sleep_delay`
(120 s). Il ne doit donc **jamais** appeler `resetSleepTimer()`, sinon il rejoue le piège de
TICKET-102 en pire. Vérifié automatiquement : le smoke test §3 lit le corps de
`kioskHeartbeat()` et échoue s'il y trouve `resetSleepTimer`, `clearTimeout` ou
`sleepTimer`.

**Test de garde** : smoke test §3 (battement armé + absence d'effet sur le timer de veille)
et §5 (service actif + fraîcheur du battement, `fail` au-delà de 60 s).

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

**Le gain casque est séparé de la courbe (TICKET-124, 2026-08-05)** : `bands_db` porte la
**forme**, `gain_db` porte le **niveau**. Les mélanger faisait perdre le gain réglé pour la
voiture dès qu'on chargeait un preset. Le gain n'existe **que** sur le profil casque, borné
à 0..6 dB : les haut-parleurs restent tenus par `speakers_max ≤ 80`, et on ne leur ouvre
pas de porte dérobée.

Pourquoi ce gain fonctionne là où monter le volume ne suffisait plus : le boost alsaequal
intervient **après** l'étage de volume de MPD, déjà à 100, et après le mixer du DAC, déjà à
0 dB. C'est la dernière marge disponible dans la chaîne.

Écrêtage assumé : chaque bande est plafonnée indépendamment à +12 dB. Sur un profil déjà
haut, les bandes saturées s'alignent et **la courbe s'aplatit**. L'IHM prévient avant
d'enregistrer, et `audio_eq_apply.py` journalise les bandes écrêtées.

**Où vit réellement la référence matérielle** (constaté le 2026-08-05, contre-intuitif) :
`mpd.conf` ne contient **aucun** `hw:`. Depuis TICKET-030, ses deux sorties pointent vers
les plugins alsaequal `eqhp` / `eqcasque`, et c'est `/etc/asound.conf` qui nomme les
cartes — correctement, par `plughw:CARD=sndrpihifiberry` et `plughw:CARD=Audio`.

⚠️ **Piège résiduel dans `asound.conf`** : le périphérique **par défaut** est encore
numéroté (`slave.pcm "hw:2,0"`, `card 2`). MPD ne l'emprunte pas, mais **tout ce qui ne
précise pas `-D` le fait** : son de démarrage, `aplay`, Chromium. Après une
ré-énumération des cartes, le chime de boot partirait dans le HDMI. Non corrigé à ce jour.

**Test de garde** : smoke test §8 — sorties MPD dirigées vers `eqhp`/`eqcasque` et non
vers du matériel numéroté · `hw:CARD=` présent dans `asound.conf` · avertissement si le
périphérique par défaut reste numéroté · taille des deux `.bin` à 840 octets ·
`speakers_max ≤ 80` · `gain_db` dans 0..6.

**Règle de sécurité enfant** : `speakers_max` ne dépasse jamais 80, et le gain casque ne
dépasse jamais 6 dB. Ce sont des invariants, pas des réglages.

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

**Second piège, celui de l'observabilité (2026-08-19, TICKET-141)** :
`should_record_point()` n'enregistrait un point que sur **changement** — bascule
charge/décharge, changement de mode MPD, variation de niveau ≥ 2 points, statut. Donc
**rien pendant un plateau**. Formulé autrement, et c'est la leçon à retenir :

> **Un échantillonnage déclenché par le changement ne peut pas documenter une
> absence de changement.**

L'enregistreur devenait muet exactement pendant le phénomène qu'on cherchait à étudier.
Pire, le **courant n'était pas un critère du tout** : la nuit du 2026-08-18, il s'est
effondré de +1111 à −60 mA pendant 6 h 53 et cela n'a été capté que par accident, parce
que le niveau bougeait au même moment — **3 points en 6 h 53**. Mesure de l'aveuglement :
sur un plateau de 30 minutes, l'ancien code retenait **0 point**.

**Troisième piège, la contrepartie (TICKET-141)** : `collect_once()` réécrivait
l'historique **entier** toutes les 60 s, qu'un point ait été retenu ou non — 196 ko ×
1440 = **283 Mo d'écriture par jour** sur la carte SD. Il n'existait **aucune purge** :
le fichier grossissait indéfiniment. Ajouter une cadence d'enregistrement sans borner la
rétention transforme une amélioration de diagnostic en **usure de carte SD** — panne
latente typique, invisible six mois durant.

⚠️ **Le piège dans le correctif lui-même** : `should_record_point()` renvoie un tuple dont
le **second élément** pilote `close_discharge()` / `close_charge()` / `new_cycle()`.
Ajouter la cadence plancher ou le courant à ce second élément fabriquerait **un faux cycle
toutes les 5 minutes**. Il doit rester strictement `transition or state_changed`.

**Quatrième piège — la table et sa compensation vont PAR PAIRE (2026-08-21, TICKET-137)** :
`_LIPO_TABLE` contient désormais des tensions **à vide**, mesurées. L'INA219, lui, mesure
sous charge. Retirer `tension_a_vide()` en gardant la table — ou régler
`internal_resistance_ohm` à zéro — rend le niveau **plus faux qu'avec l'ancienne courbe
générique**, et **rien ne plante**. À −2,2 A l'écart vaut 75 mV, soit environ 8 points :
la jauge plongerait dès qu'un podcast démarre, alors que rien n'a été consommé.

C'est le même schéma que le durcissement systemd de la zone Z2 : **deux éléments corrects
séparément, faux une fois dissociés.** Deux tests du smoke test §5 les maintiennent liés.

**Cinquième piège, et la leçon la plus transférable du projet — VALIDER DANS LA
MAUVAISE UNITÉ (2026-08-21, TICKET-142)** : la table mesurée a été validée sur un
**désaccord médian de 6,4 mV** entre deux cycles, annoncé comme une réussite. Personne
n'a converti ces millivolts en **points de pourcentage** — or cette conversion dépend
entièrement de la pente locale :

| bande | largeur | ce que valent 10 mV |
|---|---|---|
| 75-80 % | 5,0 mV | **10 points** |
| 80-85 % | 5,0 mV | **10 points** |
| 90-95 % | 9,0 mV | **5,6 points** |
| 0-70 % | 26-66 mV | 0,8 à 1,9 point |

6 mV d'accord, c'est excellent à 50 % et **sans aucune valeur à 80 %**. Résultat mesuré
sur l'appareil : la table annonçait **86 %** là où l'intégration du courant depuis la
charge pleine donnait **77,9 %**. L'ancienne table générique, elle, tombait juste — par
compensation de deux erreurs opposées (elle sur-évaluait, et l'usage de la tension brute
sous-évaluait d'autant en décharge). **Le correctif avait donc dégradé la partie de la
plage où l'enfant passe le plus clair de son temps.**

> **Une métrique de validation exprimée dans une autre unité que le produit ne valide
> rien.** Convertir dans l'unité de l'utilisateur avant de conclure.

**Remède livré (TICKET-142)** : comptage coulométrique **ancré**. Sous 70 %, la table
fait autorité — la courbe y est franche et se recale d'elle-même. Au-dessus, on intègre
le courant depuis le dernier ancrage. La dérive ne peut s'accumuler que sur **une seule
traversée** de la bande haute avant remise à zéro, ce qui est la seule raison rendant le
mécanisme acceptable. ⚠️ Et il **s'invalide au-delà de 10 min de trou de mesure** : un
compteur qui intègre à travers un trou dérive *sans le dire*, ce qui est le pire défaut
possible pour ce genre de mécanisme. Vérifié sur la journée réelle du 2026-08-21 : **78 %
contre 77,9 % de référence.**

**Sixième piège — le haut de la courbe n'est pas mesurable par la tension** : entre 75 et
95 %, la table mesurée étale 20 points de pourcentage sur **40 mV** (contre 60 mV pour
l'ancienne). C'est le plateau de la chimie Li-ion, pas un défaut. Conséquence pratique :
la nouvelle table est **environ sept fois plus sensible au bruit** dans cette zone. Le
lissage de TICKET-139 en est donc le **préalable**, pas un confort — livrer la table seule
aurait aggravé le sautillement qu'on cherchait à corriger. Un espacement minimal de 5 mV
entre paliers évite de créer une falaise plus fine que le bruit résiduel.

⚠️ **Changement de sens silencieux, à ne pas oublier** : le seuil de coupure s'appelle
toujours « 5 % » mais ne désigne plus la même tension — 3,458 V à vide au lieu de 3,350 V,
soit **108 mV plus tôt** et ~14 min d'autonomie en moins. Décision de Thomas du
2026-08-21 : garder 5 %, parce que ces 14 minutes se situent là où la tension s'effondre
et où les cellules souffrent le plus. **Un seuil dont le nom ne change pas alors que sa
signification physique change est un piège classique** : le vérifier après toute
modification de la table.

**Fichiers** : `scripts/battery_tracker.py`, `scripts/battery_watchdog.py`,
`scripts/battery_common.py`, `data/tracking.db`

**Historique** : bug cycles batterie (réparé 2026-07-06) · TICKET-011 (`battery_watchdog`
est le seul des 8 services durcis dont le comportement d'arrêt n'a **jamais été prouvé**)
· TICKET-141 (enregistreur aveugle aux plateaux, 2026-08-19)

**Test de garde** : `scripts/test_batterie.py` — 44 assertions, dont 14 pour TICKET-141
(plateau, effondrement de courant, franchissement de la bande morte, **non-déclenchement
de transition**, purge et son idempotence). Les 4 assertions clés ont été **vérifiées en
échec sur le code d'avant le correctif**. Smoke test §5 : présence des trois constantes,
appel de `purge_history()`, écriture conditionnelle de l'historique.

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

**Test de garde** : `scripts/check_privacy.sh`, intégré au smoke test (§7).
`private/forbidden_names.txt` **existe depuis le 2026-08-05** — la garde est donc active,
et non plus seulement branchée. Ne jamais y ajouter le prénom de l'auteur : il est partout
légitimement (`/home/thomas`, README, unités systemd, auteur des commits) et noierait le
test sous des milliers de faux positifs.

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

### 🔴 Z12 — Déploiement de l'IHM : le code servi n'est pas toujours le code du disque

**Le piège**, et c'est le plus sournois du projet : **on peut modifier `index.html`, le vérifier
sur le disque, lancer un smoke test tout vert, et voir l'ancien code tourner à l'écran.**
Constaté le 2026-08-17 : deux allers-retours de diagnostic perdus à chercher un bug dans du
code qui n'était pas exécuté. Rien ne le signalait — le fichier était bon, PHP était bon,
Apache répondait 200.

**Deux causes cumulées** :

1. `restart-kiosk.sh` ne lance pas Chromium en `--incognito` (contrairement au `.desktop` du
   mode kiosque), donc son profil et son cache HTTP survivent aux relances.
2. Aucun en-tête anti-cache n'était envoyé sur le HTML du lecteur.

**Pourquoi aucun test ne pouvait le voir** : tous les contrôles regardaient le **fichier**,
jamais la **réponse**. C'est la leçon générale de cette zone — pour tout ce qui traverse un
serveur ou un cache, vérifier ce qui arrive, pas ce qui est stocké.

**Fichiers** : `scripts/apache-hechicero-nocache.conf`, `restart-kiosk.sh`,
`/etc/apache2/conf-enabled/`

**Historique** : TICKET-127

**Correctif** : `mod_headers` + `Cache-Control: no-store` sur `^/lecteur/?$` et
`^/lecteur/.+\.html$` via `<LocationMatch>` (indépendant du `DocumentRoot`, donc reproductible
sur une image SD fraîche). Volontairement limité au HTML : polices, images et sons restent en
cache, ils pèsent et ne changent presque jamais.

⚠️ **La conf est encadrée par `<IfModule headers_module>`** : sans ce garde-fou, un
`mod_headers` absent empêcherait Apache de démarrer et l'IHM de l'enfant serait morte. Mais
cela rend l'échec **silencieux** — d'où l'obligation d'un test qui lit la réponse réelle.

**Test de garde** : smoke test §3 — comparaison du `md5` d'`index.html` sur le disque avec
celui de la page servie (`fail` si différence), et présence de `Cache-Control: no-store` dans
les en-têtes réellement renvoyés (`warn` si absent).

**Dépannage** : si le cache reprend malgré tout,
`pkill chromium; rm -rf ~/.cache/chromium; ./restart-kiosk.sh`.

---

## 5. Dette de test — zones sans garde automatique

Par ordre d'urgence. C'est la liste de travail de ce document.

| Zone | Ce qui manque | Ticket |
|------|---------------|--------|
| Z2 services durcis | Prouver qu'un service recrée ses fichiers de travail après suppression (les directives d'unité sont désormais couvertes, §6 du smoke test) | TICKET-121 |
| ~~Z6 audio~~ | ✅ **couvert** depuis le 2026-08-05 (smoke test §8) | TICKET-124 |
| ~~Z4 écran — page vivante~~ | ✅ **couvert** depuis le 2026-08-17 : le battement de cœur détecte un kiosque qui n'exécute plus de JS (smoke test §3 et §5) | TICKET-127 |
| Z4 écran — cause du gel | Le battement **date** le gel, il ne l'**explique** pas. La cause reste à établir sur l'instantané du prochain épisode. | TICKET-127 |
| Z3 boutons | Prouver qu'un appui produit une action (pas juste « service actif »). **Partiellement couvert** depuis le 2026-08-17 : le smoke test vérifie que `signaler_activite()` est présent et que `wtype` est installé, mais pas qu'un appui déclenche bien sa commande MPD. | TICKET-132 |
| Z7 hors réseau | Lecture d'un podcast local, réseau coupé | — |
| ~~Z9 intégrité~~ | ✅ **couvert** depuis le 2026-08-17 : `check_integrity.py` intégré au smoke test §9, sous `timeout 25`. Il existait depuis longtemps mais n'était lancé qu'à la main, donc jamais. ⚠️ **Le tri par gravité est essentiel** : le script classe en `ERR` autant « un épisode du catalogue sans son fichier » (cassé → `fail`) que « des fichiers hors catalogue » (poids mort → `warn`). Sans ce tri, 9 podcasts retirés de la config faisaient passer 359 lignes en `ERR` et la suite entière au rouge, alors que tout fonctionnait. | — |
| Z11 domotique | Cohérence lumière entre `domotique.php` et `lecteur/index.html` | — |
| ~~Z8 batterie — arrêt d'urgence~~ | ✅ **PROUVÉ EN RÉEL le 2026-08-17** : décharge complète jusqu'à **15 %**, le Pi s'est éteint. Premier exercice réussi du chemin réparé par TICKET-121 (le `shutdown` sans `sudo`). Marge relevée : ≈ 3,49 V sous −2038 mA, contre 3,15 V au seuil constructeur. | TICKET-121 |
| ~~Z8 batterie — cycles~~ | ✅ **couvert** depuis le 2026-08-17 : `scripts/test_batterie.py`, 24 assertions sur les mesures réelles (détection charge/décharge par le signe + bande morte, clôture de cycle interrompue par l'arrêt). Smoke test §5. | TICKET-133 |
| Z8 batterie — modèle d'autonomie | Les estimations reposent sur un seul cycle, lui-même faussé avant le correctif de TICKET-133. À réévaluer après plusieurs cycles complets — c'est aussi à ce moment-là que le seuil de coupure de 15 % pourra être réinterrogé. | TICKET-133 |
| Z8 batterie — coupure HAT | Le registre `0x2d` est détecté et armé avant l'arrêt, mais **rien ne prouve que la coupure soit différée** et non immédiate. `--simulate-critical` s'arrête volontairement avant l'écriture I2C. | TICKET-128 |
| ~~Z8 batterie — observabilité~~ | ✅ **couvert** depuis le 2026-08-19 : cadence plancher de 5 min, courant devenu critère d'enregistrement, purge à 30 j. `test_batterie.py` passe à 44 assertions ; les 4 clés **vérifiées en échec sur le code d'avant** (l'ancien retenait **0 point** sur un plateau de 30 min). | TICKET-141 |
| ~~Z8 batterie — table de conversion~~ | ✅ **couvert** depuis le 2026-08-21 : table mesurée sur **deux décharges profondes indépendantes** (6,4 mV de désaccord médian), compensation d'affaissement (R = 34 mΩ), lissage par médiane sur rafale. **62 assertions** ; 4 des 5 clés **vérifiées en échec sur l'ancienne table**. Smoke test §5 : couplage table/compensation, résistance non nulle, rafale active. | TICKET-137 · TICKET-139 |
| ~~Z8 batterie — haut de courbe (75-95 %)~~ | ✅ **couvert** depuis le 2026-08-21 : comptage coulométrique ancré sous 70 %, invalidé après 10 min de trou. Rejeu de la journée réelle : **78 % contre 77,9 %** de référence, là où la table seule se trompait de 9 points. 84 assertions ; 4 tests du comptage ont d'abord **échoué sur le garde-fou de trou**, ce qui a prouvé qu'il mord. | TICKET-142 |
| Z8 batterie — R mal contraint | R = 34 mΩ est le meilleur accord entre les deux cycles, mais le minimum est **plat entre 20 et 60 mΩ** : le courant de décharge varie trop peu (1540-2170 mA) pour donner du bras de levier. À réévaluer si un cycle à faible courant devient disponible. | TICKET-137 |
| Z8 batterie — arrêt de charge nocturne | Le chargeur s'est arrêté de 00:16 à 07:09 le 2026-08-19 **alimentation présente**, à 61 %. Piste du temporisateur 6 h **démentie** (charge poursuivie jusqu'à 97 % le lendemain). Cause inconnue — **était indiagnosticable avant TICKET-141**, à reprendre sur les données du prochain épisode. | TICKET-140 |

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
