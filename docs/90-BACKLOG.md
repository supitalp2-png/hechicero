# Backlog Hechicero

> `TICKET-### — [type] — Titre (date)` · `[ ]` à faire · `[x]` clos ou annulé
> ⚠️ **Pas d'état « en cours »** : quatre tickets y ont dormi, invisibles à la fois des
> ouverts et des clos. Ce qui avance se suit dans l'état des lieux, pas dans une case.
> Un ticket clos ou annulé descend **immédiatement** dans « Terminé ».

## 📌 État des lieux

*2026-08-23 — 3 ouverts, 140 clos*

### À faire

| # | Sujet | État |
|---|---|---|
| 140 | Arrêt de charge nocturne, alimentation présente | instrumenté 23/08, attend une nuit branché |
| 122 | Récupération du chien de garde MPD | logique testée, action non éprouvée |
| 058 | Série podcast « Décisions Prises » | 2 épisodes écrits |

### À observer

*Livré et testé, mais rien ne remplace l'usage.*

| # | À vérifier |
|---|---|
| 127 | Le prochain gel réel du kiosque — plus rien à coder |
| 119 | Retour auto à la radio après 10 min |
| 146 | Le graphique par langue après redressement de la base |
| 138 | Plus d'écran noir sur dalle allumée après un `wtype -k F5` |
| 141 | Cadence plancher, et purge au-delà de 30 jours |

✅ **137 · 139 · 142 confirmés par l'usage (2026-08-23).** Deux décharges complètes
sous le nouveau code : 24 à 34 min par tranche de 10 %, pour 27-28 min attendus d'une
jauge linéaire. Le cycle du 2026-08-21 04:48, resté sur l'ancien code, montre à
l'inverse 200 min bloquées entre 90 et 99 % — le défaut d'origine, dans la même
journée. Autonomie mesurée : **4 h 15** de la pleine charge à l'arrêt.

---

# 📋 Détail des tickets ouverts

- [x] TICKET-147 — instrumentation — Le guetteur de gel comptait un saut d'horloge comme un silence (2026-08-23)
      - Les **deux seules** alertes depuis la mise en service tombaient à moins de 15 s
        d'une resynchronisation NTP :
        ```
        22/08 09:28:32  timesyncd: Initial clock synchronization
        22/08 09:28:44  GEL DÉTECTÉ — battement silencieux depuis 77 s
        23/08 11:39:23  timesyncd: Initial clock synchronization
        23/08 11:39:35  GEL DÉTECTÉ — battement silencieux depuis 516 s
        ```
      - Le Pi démarre sans réseau : son horloge repart de la dernière date connue, puis
        **bondit** quand le NTP répond. `age` comparait deux heures murales — le dernier
        battement, écrit avant le bond, et `time.time()` d'après. L'écart mesuré n'était
        pas un silence, c'était la taille du saut. La page n'avait jamais cessé de
        tourner : « battement REVENU » arrive 21 s plus tard, avec un âge de 4 à 5 s.
      - ⚠️ **Ce n'était pas cosmétique** : 2 alertes sur 2 étaient fausses. Un guetteur
        qui crie au loup rend invisible le gel qu'il est censé attraper — toute
        l'instrumentation du 127 ne valait plus rien.
      - **Correctif**, deux protections indépendantes :
        1. surveiller la dérive entre horloge murale et horloge monotone. Elle est
           constante sauf quand le système repositionne l'heure ; un écart brusque
           (> 2 s) fait jeter l'évaluation du tour. `time.monotonic()` seul ne suffisait
           pas : le battement est horodaté par le navigateur, dans un autre processus.
        2. exiger deux tours consécutifs de silence. Un vrai gel dure, un artefact non.
           Coût : 20 s de retard sur l'instantané, sans effet sur sa valeur.
      - La décision est sortie dans une classe `DetecteurGel`, testable sans Pi, sans
        Chromium et sans attendre une panne.
      - **Garde** : `scripts/test_kiosk_freeze.py`, 16 décisions. Il rejoue les deux
        fausses alertes avec leurs vrais chiffres, **et** vérifie qu'un vrai gel reste
        détecté — à force de filtrer le bruit on rend un détecteur aveugle. Éprouvé sur
        l'ancienne logique (`saut_max_s=inf, confirmations=1`) : elle produit bien les
        deux fausses alertes, la nouvelle les filtre, et les deux attrapent le vrai gel.

- [x] TICKET-138 — écran — L'overlay de veille partait à 60 s alors que la dalle s'éteignait à 600 s (2026-08-23, 2e passe)
      - **Le correctif d'août était juste, et sans effet.** `applySleepConfig()` calculait
        bien `screen_off_delay ?? sleep_delay ?? 600`, et `config.json` contenait bien
        `screen_off_delay: 600`. Et la page journalisait `delay_ms=60000`.
      - **Cause** : la page ne lit pas `config.json`. Elle reçoit sa configuration de
        `radio.php?action=parental_status`, **qui recopie une liste fixe de clés** —
        `screen_off_delay` n'en faisait pas partie. À l'exécution la clé valait
        `undefined`, le repli `sleep_delay` (60 s) s'appliquait, et swayidle continuait
        d'éteindre à 600 s. Traces DPMS à l'appui : dalle éteinte 607 s après le réveil.
      - 🎯 **La leçon** : on a corrigé le consommateur sans jamais vérifier que le
        producteur envoyait la donnée. Les deux fichiers étaient justes séparément ;
        c'est le contrat entre eux qui était rompu. Un `??` sur une clé absente ne
        proteste pas — il produit une valeur plausible et fausse. Même mécanisme
        exactement que le TICKET-146 le même jour (Z13).
      - **Correctif** : `screen_off_delay` ajouté à la charge utile de `parental_status`.
      - **Garde** : le smoke test extrait les clés `cfg.X` réellement lues par
        `applySleepConfig()` et vérifie que **chacune** est émise par l'endpoint.
        Éprouvé dans les deux sens : il échoue si on retire la clé, et il échoue aussi
        si la fonction ou le bloc devient introuvable.
      - ⚠️ **Nécessite un `wtype -k F5`** pour que le kiosque recharge la page.

- [ ] TICKET-140 — matériel/batterie — Le chargeur du HAT termine la charge à ~61 % et ne reprend qu'à la sollicitation (2026-08-19)
      - **Signalé par Thomas** : « je ne comprends pas l'arrêt de recharge entre minuit en gros et 7h30 ». Ses heures, lues sur le tableau de bord, sont exactes : **00:16 → 07:09**.
      - 📊 **Établi par les données** — charge franche de 18:14:48 à 00:12 (2 % → 61 %, 1100-1300 mA), puis :
        ```
        00:12:30   61 %   3,880 V  +1111 mA   charge normale
        00:16:30   54 %   3,820 V     −60 mA   ← effondrement
        02:37:33   52 %   3,808 V      +1 mA
        07:09:39   51 %   3,800 V    −173 mA   webradio démarre
        07:10:39   51 %   3,796 V    −340 mA   la batterie fournit le surplus, la tension plonge
        07:14:39   54 %   3,820 V    +491 mA   ← le chargeur se réveille
        ```
      - ✅ **Ce n'est pas une coupure secteur.** Pendant les 6 h 53, le courant vaut −60 / +1 / −173 mA. Si l'alimentation externe avait disparu, le Pi — allumé, écran actif — aurait tiré **−400 à −900 mA** sur les cellules. Il ne l'a pas fait. L'alimentation était présente et alimentait la charge de travail : **c'est le chargeur qui a cessé de pousser du courant dans les cellules**, à 3,88 V, très loin des 4,2 V d'une cellule pleine.
      - ✅ **La reprise est déclenchée par la sollicitation, pas par l'heure.** Le démarrage de la webradio fait plonger la tension à 3,796 V, et le chargeur repart 5 min après. Comportement classique d'un chargeur **terminé** qui attend un **seuil de reprise**. Sans la radio du matin, il serait probablement resté muet.
      - ❌ **Écarté : notre propre code.** `arm_hat_power_cutoff()` (TICKET-128) n'est appelé que dans le chemin d'arrêt critique, qui n'a pas tourné cette nuit. Le `i2cset 0x2d 0x01 0x55` de `INA219.py` est du code de démonstration Waveshare sous `__main__`, atteignable seulement sous 3,15 V.
      - ❓ **Non établi : pourquoi il termine à 61 %.** `charge_start 18:14:48` → effondrement `00:16:30` = **6 h 02**, ce qui évoque un temporisateur de sécurité. ⚠️ **Une seule occurrence** — l'historique complet ne contient que deux effondrements soutenus : celui-ci et un à ~98 % le 08-18 (terminaison normale, batterie pleine). **Piste, pas conclusion** : c'est exactement le raisonnement à un seul point qui a produit l'erreur du TICKET-139 le matin même.
      - 🔬 **Prédiction falsifiable** : la charge ayant repris à **07:14:39**, un temporisateur de ~6 h l'aurait arrêtée vers **13:14**.
      - ❌ **PRÉDICTION DÉMENTIE (2026-08-19)** : la charge a traversé 13:14 sans broncher et s'est poursuivie jusqu'à **15:17, à 97 % / 4,168 V**. **Il n'y a pas de temporisateur de 6 h**, et **la batterie atteint bien le plein** — contrairement à ce que je supposais le matin. La cause de l'arrêt nocturne à 61 % **redevient entièrement inconnue**.
      - 🔭 **Mais on sait désormais pourquoi on ne peut pas l'observer** : voir TICKET-141. Le courant n'étant pas un critère d'enregistrement, l'effondrement de +1111 à −60 mA n'a laissé que 3 points en 6 h 53. **Corriger l'enregistreur est un préalable** à tout diagnostic de ce ticket.
      - 🔁 **Observé en fin de journée — le HAT cycle en haut de charge** : `17:44 −411 mA` · `17:54 +156` · `17:59 +330` · `18:48 −395`. Une fois plein, le chargeur coupe et laisse le Pi puiser dans les cellules jusqu'au seuil de reprise, puis recharge. Sans danger, mais **consomme des cycles pour rien** et fausse le comptage.
      - ✅ **Instrumenté le 2026-08-23.** Chaque point de données porte désormais deux mesures de plus :
        - `temperature_c` — `/sys/class/thermal/thermal_zone0/temp`, un fichier et non un sous-processus, dans une boucle qui tourne toutes les minutes. ⚠️ **C'est la température du SoC, pas des cellules** : on n'en lira aucun seuil JEITA directement, seulement une **corrélation**. Si les arrêts nocturnes tombent sur les points les plus froids, la piste thermique tient ; s'ils y sont indifférents, elle est morte et on cherche ailleurs. C'est précisément l'arbitrage qu'on ne peut pas faire aujourd'hui.
        - `throttled` — registre `vcgencmd get_throttled`, documenté par la fondation. Il tranche une question que la température ne tranche pas : **l'alimentation a-t-elle décroché ?** Un bit de sous-tension pendant un arrêt de charge signifierait que ce n'est pas le chargeur qui renonce mais l'amont qui ne suit plus — deux pannes opposées, aujourd'hui indiscernables. Registre documenté : on ne devine aucune sémantique, contrairement au registre `0x2d` du HAT (TICKET-128).
      - Visible sur le tableau de bord, troisième cadre sous tension et courant — **même axe de temps**, c'est la superposition qui sert. Pas de double axe : le fichier documente pourquoi (le courant écrase tout).
      - ⚠️ **Ce ticket reste ouvert.** On n'a rien corrigé, on s'est seulement donné les moyens de conclure. Il faut maintenant **une nuit branché** avec un épisode capturé.
      - 🔗 **À croiser avec TICKET-137** : `cycles_recorded: 2` et `model_confidence: "low"`. Cette journée de charge fournit un cycle de plus vers les 3-4 nécessaires à la recalibration de la table. Si le plateau est réel, il change aussi la capacité utile retenue pour le calcul d'autonomie (9 560 mAh envisagés).

- [ ] TICKET-122 — bug/infra — MPD se fige indéfiniment quand le réseau disparaît pendant une webradio (2026-08-05)
      - **Symptôme** : plus aucune lecture possible, ni podcast ni webradio. `mpc status` → `MPD error: Invalid argument`, `radio.php?action=status` → `MPD connection failed: Resource temporarily unavailable`. Pourtant `systemctl status mpd` affiche `active (running)` **depuis plus de 24 h, sans un seul crash au journal**.
      - **Déclencheur** : Thomas est parti plusieurs heures avec son téléphone, alors que le Pi était sur son partage de connexion et jouait une webradio.
      - 🔍 **Diagnostic complet pris pendant la panne** (ne pas refaire les mesures, elles sont ici) :
        - `ps` : `TIME` figé à `00:02:53` sur 10 s → **zéro CPU consommé**, le processus attend, il ne boucle pas.
        - `ss -tnp` : `ESTAB 0 0 10.152.145.165:41772 → 3.175.86.2:443 users:(("mpd",pid=1030,fd=16))` — une socket HTTPS vers le CDN de la webradio, files d'attente vides, toujours `ESTABLISHED`.
        - `ss -tnpo` : **aucun champ `timer:`** → pas de sonde keepalive, pas de retransmission. Le noyau ne détectera jamais le pair mort ; la socket survivrait jusqu'au reboot.
        - `ss -lnp` : `u_str LISTEN 0 0 /run/mpd/socket` (backlog 0) et `tcp LISTEN 1 5 *:6600` — **une connexion terminée attend d'être acceptée, personne ne la ramasse**. D'où le `EAGAIN` côté clients.
        - Piles noyau (`/proc/<pid>/task/*/stack`) : thread principal `mpd` en **`futex_wait`**, thread `io` en **`io_cqring_wait`**, threads `player` / `decoder:faad` / `output:*` tous en `futex_wait`. Seul `rtio` est normalement parqué en `epoll_wait`.
        - `dmesg` : **aucun événement USB depuis le boot** → le DAC KT USB Audio est hors de cause. `/dev/snd/pcmC2D0p` (HiFiBerry) toujours ouvert par MPD. Les deux `.bin` alsaequal font 840 octets — ce n'est **pas** l'incident `mpd.socket` de §6.4.1.
      - **Cause racine** : le partage de connexion a disparu **sans fermeture propre de la liaison TCP** (ni `FIN` ni `RST` — l'autre bout n'a jamais su). La socket devient un trou noir. La lecture io_uring engagée dessus ne se termine jamais, le thread `io` reste parqué **en tenant le verrou du flux**, et tout le démon s'empile derrière lui jusqu'au thread principal, qui n'accepte donc plus aucune connexion.
      - **C'est une limite de MPD, pas du montage** : le plugin d'entrée `curl` n'a de délai de garde que sur la connexion *initiale*, aucun sur un flux qui stagne. Sur un appareil nomade, ça se reproduira.
      - ❌ **Piste écartée — faire mourir la socket au niveau noyau.** Ce serait le correctif le plus propre (MPD verrait une erreur de flux et s'en remettrait seul, sans redémarrage), mais c'est **impossible ici** : MPD ne fait que *lire* ce flux, il n'émet rien, donc il n'y a aucune retransmission à expirer via `tcp_retries2` ; et libcurl n'arme pas `SO_KEEPALIVE` par défaut, MPD n'exposant aucun réglage pour le faire. D'où l'absence de `timer:` dans `ss -tnpo`. Le noyau est aveugle par construction sur une socket purement réceptrice et inactive.
      - 🛠️ **Correctif implémenté le 2026-08-05 — `scripts/mpd_watchdog.py` + `.service`** :
        - **Guérir** : sonde `/run/mpd/socket` (le même transport que `radio.php`, cf. `fsockopen('unix:///run/mpd/socket', …)`) toutes les 30 s avec un délai de garde de 3 s. Sur MPD figé, la sonde échoue en **0,08 s** avec `EAGAIN` — mesuré. Après **3 échecs consécutifs** (~90 s de panne confirmée), déclenche la récupération.
        - ⚠️ **La séquence §6.4.1 telle quelle NE MARCHE PAS sur un MPD figé** (appris en production le 2026-08-05, deux corrections successives) :
          1. `systemctl stop mpd.service` **expire**. systemd envoie `SIGTERM`, mais le thread principal dort sur un futex et ne le traitera jamais ; systemd attend tout son `TimeoutStopSec` (90 s) avant d'escalader. Pire, le job d'arrêt reste en file et **tous les ordres suivants sur l'unité expirent derrière lui** — c'est pour ça que le `start mpd.socket` échouait aussi. ➜ Aller **directement au `systemctl kill --signal=SIGKILL mpd.service`**.
          2. Ne **pas** attendre ensuite que `mpd.service` devienne inactif : il est **activé par socket**, donc systemd le relance à la première connexion. Mesuré : `is-active` répondait déjà `active` 3 s après le `SIGKILL`. Une attente sur l'inactivité échouerait toujours. ➜ **Sonder directement**, c'est le seul juge valable. La remise à zéro du socket (`stop` → `reset-failed` → `start mpd.socket`) n'est tentée qu'en second recours, si le `SIGKILL` n'a pas suffi.
          - Coût accepté du `SIGKILL` : l'état de lecture MPD n'est pas sauvegardé. Sans conséquence ici — `play_tracker.py` est la source de vérité du suivi d'écoute, et `restore_paused` gère la reprise au démarrage.
        - **Prévenir** : si MPD répond, joue un flux `http(s)` **et** qu'il n'y a plus de route par défaut pendant 2 sondes (~60 s), envoie un `stop` propre avant que MPD ne se fige dessus. Un podcast **local n'est jamais interrompu** — Hechicero doit marcher hors réseau.
        - **Garde-fous** (c'est l'enceinte d'un enfant, un chien de garde nerveux ferait plus de mal que la panne) : plafond de **3 récupérations par heure**, au-delà duquel on journalise sans insister — mieux vaut une panne visible qu'une boucle de redémarrages qui masque la cause. Journal dans `data/mpd_watchdog.log` (rotation intégrée).
        - Détection de connectivité par **absence de route par défaut** : instantané, aucune I/O réseau, donc le chien de garde ne peut pas se bloquer lui-même. Limite assumée : un point d'accès présent mais sans Internet garde sa route — non couvert par la prévention, le volet « guérir » reste le filet.
        - Durcissement au modèle TICKET-011 **corrigé par la leçon TICKET-120** : `ReadWritePaths=…/data` uniquement, **aucune écriture dans le dépôt**. Pas de `Requires=mpd.service` — le chien de garde doit survivre à un MPD arrêté, c'est là qu'il sert.
      - 🐛 **Défaut trouvé grâce au chien de garde, avant sa mise en service — `Requires=mpd.service`.** Trois unités le portaient : `buttons_daemon`, `play_tracker` et `audio_eq_apply`. `Requires=` **propage l'arrêt** : chaque fois que le chien de garde aurait tué MPD pour le réparer, systemd aurait éteint les boutons physiques et arrêté définitivement le suivi d'écoute. Constaté en direct (« les boutons ne fonctionnent pas » juste après le premier `SIGKILL` manuel). `play_tracker` était le plus vicieux : sa disparition est silencieuse, on aurait perdu des semaines de statistiques sans rien voir. ➜ Les trois passent en **`Wants=`** (ordonnancement conservé, propagation d'arrêt supprimée). Vérifié : après `systemctl kill -s KILL mpd.service`, les deux services restent `active` et MPD revient seul par activation de socket.
      - 📌 **C'est le deuxième défaut de conception hérité de TICKET-011 en deux jours**, après le tube lgpio de TICKET-120. Le durcissement de juillet a été appliqué en recopiant un modèle d'unité d'un service à l'autre sans vérifier ce que chaque directive impliquait. Ce n'est plus une hypothèse mais un motif confirmé deux fois — voir TICKET-121.
      - 🛠️ **`scripts/smoke_test.sh` corrigé** : son test MPD passait par `mpc`, qui **ne renvoie pas d'erreur quand MPD est figé — il attend**. Le smoke test se serait figé avec lui sans rien rapporter, ce qui explique qu'un MPD bloqué ait pu passer 24 h inaperçu. Il utilise désormais `mpd_watchdog.py --probe` sous `timeout`, et vérifie au passage que le chien de garde tourne.
      - ⏳ **Reste** : installer le service, puis valider en conditions réelles — couper le partage de connexion pendant une webradio et vérifier dans `data/mpd_watchdog.log` que l'arrêt préventif se déclenche avant tout blocage.
      - 🧹 Détail sans rapport relevé dans `dmesg` : `/etc/systemd/system/audio_eq_apply.service is marked executable` → `sudo chmod 644`.

- [ ] TICKET-058 — feature/UX — Série podcast "Décisions Prises" + easter egg
      - Première découverte : 3 taps sur "Hechicero" à l'écran d'accueil → déverrouille + lance l'épisode 0 automatiquement
      - Accès ensuite : menu secret séparé (PAS fusionné au catalogue normal) — geste d'accès plus simple qu'au premier déverrouillage (proposition à valider : simple clic sur "Hechicero")
      - Épisode 0 ne se relance pas auto à chaque entrée dans le menu — devient un épisode normal de la liste après sa 1ère lecture
      - Hints progressifs : hint 1 vague (après X jours), hint 2 explicite (après ~1h si pas trouvé)
      - Hints jamais pendant la lecture, one-shot, disparus après découverte
      - 8 épisodes planifiés (épisode 0 d'ouverture + 7) — scripts en cours dans `docs/55-PODCAST_SERIE_DECISIONS.md`
      - Ton : léger mais sérieux (blagues assumées, sans exclure le sérieux)
      - Production : voix papa + voix IA (Descript/ElevenLabs)

---

# ✔️ Terminé

**136 tickets clos**, du plus récent au plus ancien. Le détail et les post-mortems
sont dans [`91-ARCHIVE-TICKETS.md`](91-ARCHIVE-TICKETS.md) ; les pièges à ne pas rejouer
dans [`75-NON_REGRESSION.md`](75-NON_REGRESSION.md).

| # | Sujet |
|---|---|
| 145 | Activer ou désactiver une webradio, comme un podcast |
| 144 | Après l'arrêt de l'OS, rien ne protège les cellules |
| 143 | `recalibrer_table_batterie.py` produit une table absurde |
| 142 | Comptage coulométrique ancré au-dessus du plateau |
| 141 | L'enregistreur devient aveugle pendant les plateaux, et ignore le courant |
| 139 | Charge « arrêtée » à 60 % : signal non lissé, pas un plateau |
| 137 | Table tension→pourcentage mesurée sur les cellules réelles + compensation d'affaissement |
| 138 | Deux minuteries de veille désaccordées : dalle allumée, page noire pendant 9 minutes |
| 136 | Le bandeau batterie affichait 50 jours de données figées |
| 135 | Registre de non-régression + gardien automatique |
| 134 | Test de décharge profonde : jusqu'où descendre avant que le Pi décroche |
| 133 | Détection charge/décharge par le signe du courant, et cycles faussés par l'arrêt d'ur… |
| 132 | `buttons_daemon` journalise un avertissement à chaque appui play/pause |
| 131 | Les épisodes des « Explorateurs de l'Univers » s'affichaient à l'envers |
| 130 | Neuf podcasts ont disparu de la config, en silence, pendant deux semaines |
| 129 | PHP tourne en UTC alors que le reste du projet écrit en heure locale |
| 128 | « Coupure matérielle » du HAT : la fonction faisait l'INVERSE de ce qu'elle annonçait |
| 127 | Écran noir figé : la page cesse d'exécuter du JavaScript |
| 126 | Remise à zéro des mesures batterie après remplacement des cellules |
| 125 | Le périphérique ALSA par défaut est référencé par numéro de carte |
| 124 | Gain général du casque, séparé de la courbe d'égalisation |
| 123 | L'écran ne s'éteint plus après un réveil non tactile |
| 121 | Auditer les 8 services durcis : fichiers de travail hors `ReadWritePaths` |
| 120 | Boutons physiques HS : lgpio ne pouvait plus créer son tube dans `scripts/` |
| 119 | Écran technique caché, ouvert par combinaison de boutons physiques |
| 118 | Remise au propre du dépôt et de la documentation |
| 117 | Nettoyage fichiers morts dans le dépôt (renuméroté depuis TICKET-090 le 2026-08-04, e… |
| 116 | Gain casque trop faible en écoute nomade (voiture) |
| 115 | Écran noir intermittent : réveil fiable de la dalle |
| 114 | Rafraîchissement automatique du catalogue dans le lecteur |
| 113 | Refonte navigation admin en « bureau » d'icônes façon iPhone |
| 112 | Écran « Chambre » : contrôle domotique (Legrand/Netatmo via passerelle VM) depuis l'I… |
| 111 | Ventilateur GPIO/PWM pour dissipation thermique |
| 110 | Roaming automatique multi-AP (box + répéteur Free) |
| 109 | Coupures Wi-Fi récurrentes + signal anormalement faible à 30cm de la Freebox |
| 108 | Clic sur un épisode joue un épisode d'un autre podcast |
| 107 | Ingestion RSS : conserver les épisodes qui sortent du flux (surtout "Les Odyssées") |
| 106 | Objet git corrompu dans `~/hechicero` (`git log`/`git fsck` cassés) |
| 105 | Synchronisation admin en échec : "Permission denied" sur meta.json.tmp, plante toute… |
| 104 | Podcast TINA : images identiques, ordre incohérent, navigation bloquée en fin de saison |
| 103 | Coupure du flux webradio après une pause/reprise |
| 102 | Écran de veille et coupure d'écran cassés après l'intégration hardware finale |
| 101 | Finalisation boutons physiques : mapping GPIO ↔ bouton + service systemd définitif |
| 100 | Radios et podcasts non instantanés sur le lecteur |
| 099 | acast 403 Forbidden : User-Agent manquant dans downloader.py |
| 098 | Screensaver ne s'activait pas sur le kiosk Pi |
| 097 | Extinction écran non fonctionnelle sur Pi 5 + labwc |
| 096 | Hechicero s'éteignait au débranchement du chargeur |
| 095 | Vérifier courant max USB-C à réception |
| 094 | Trancher format switch général batterie (fente 25×8mm) |
| 093 | Trouver LED témoin alimentation ∅6mm |
| 092 | Trouver prise USB-A panel mount clavier de secours |
| 091 | Choisir méthode interface GPIO boutons-poussoirs |
| 090 | 51 micro-cycles factices + autonomie 12h (réelle 1.5–3h) |
| 089a | `battery_watchdog.py` : errno 121 code mort ⚠️ |
| 089b | Écran ne s'éteint pas malgré l'option activée en admin ⚠️ |
| 088a | `play_tracker.py` n'écrivait pas `listened_s` à la fermeture ⚠️ |
| 088b | `listened_s` corrompu → épisodes à 56071 % de complétion ⚠️ |
| 087 | Limiteur d'exposition sonore |
| 086 | Déduplication tracking JS vs play_tracker |
| 085 | Sauvegarde de la carte SD (ghost durci, manuel uniquement) |
| 084 | Modèle d'estimation d'autonomie (affinement progressif) |
| 083 | Arrêt propre sur batterie critique |
| 082 | Affichage autonomie + alertes 30/10 min IHM enfant |
| 081 | Dashboard alimentation parent (`web/admin/battery_dashboard.php`) |
| 080 | Service de collecte batterie (`scripts/battery_tracker.py`) |
| 079 | Mode Noël (décembre uniquement) |
| 079bis | Mode Anniversaire (20 novembre uniquement) |
| 078 | Police Great Vibes cassée (woff2 4.5KB → TTF 445KB) |
| 077 | Écran de veille thémé Great Vibes (retro/modern/classic × horloge) |
| 076 | Écran de démarrage Plymouth personnalisé (Great Vibes or) |
| 075 | (fusionné avec TICKET-076) |
| 074 | Screensaver : refonte complète 6 modes Great Vibes |
| 073 | Chime race condition → déplacé dans `kiosk.sh` |
| 072 | Mini-lecteur affiche radio au lieu du podcast en cours |
| 071 | Contrôle parental : grille horaire + verrou langue |
| 070 | Dashboard enrichi (funnel, heatmap, streak, top épisodes rejoués) |
| 069 | Enchainement automatique des épisodes |
| 068 | Typo ID podcast `bestiolesossiles` (manque le 'f') |
| 067 | Robustesse logs ingest |
| 066 | SSL proxycast.radiofrance.fr |
| 065 | Permissions Pi + cron nocturne |
| 064 | Cover podcast téléchargée automatiquement à l'ingest |
| 063 | Barres de progression synchronisation |
| 062 | Ajout 11 podcasts FR + 3 podcasts ES |
| 061 | Saison 2 Professeur Caillou |
| 060 | Webradio en premier dans la grille |
| 059 | Durée des épisodes via ffprobe |
| 057 | Démarrage rapide de l'IHM enfant |
| 056 | R&D — Exploration client lourd natif (PyQt5/Kivy) — décision projet 2.0 |
| 055 | Statistiques d'écoute + dashboard parent |
| 054 | Jaquettes par épisode dans `data.json` |
| 053 | Grille 2 colonnes + scroll tactile |
| 052 | Barre de statut : heure + batterie |
| 051 | Affichage batterie dans la barre de statut |
| 050 | Refonte visuelle IHM enfant (5 écrans, polish) |
| 049 | Images podcasts téléchargées automatiquement à l'ingest |
| 048 | Script de vérification d'intégrité audio/images/data.json |
| 047 | UX — Défilement automatique (carrousel) arrêtable par l'enfant |
| 046 | Favoris (cœur) accessibles rapidement |
| 045 | Taille des jaquettes ≥ 300×300 px |
| 044 | Flèches épisode suivant / précédent |
| 043 | Reprise automatique de la position de lecture |
| 042 | Barre de progression + scrubbing tactile |
| 041 | Appui sur image = pause/lecture |
| 040 | `app.js` supprimé (code mort) |
| 039 | Démarrage automatique du lecteur (mode kiosque) |
| 038 | Bouton physique RUN pour démarrage du Raspberry Pi 5 |
| 037 | UX — Animations simples (fade/slide) dans l'IHM enfant |
| 036 | Mode "grands boutons" optimisé tactile |
| 035 | Mise à jour des documents essentiels |
| 034 | Activation du volume logiciel MPD |
| 033 | Installation écran tactile + tests IHM |
| 032 | Installation Raspberry Pi OS avec bureau |
| 031 | Sortie casque avec bouton physique de bascule HP/casque |
| 030 | Égaliseur audio paramétrable |
| 029 | Quotas stockage (`max_episodes`) |
| 028 | Nettoyage et finalisation du lecteur |
| 027 | Ingestion nocturne (cron 3h, `umask 002`) |
| 026 | Génération automatique de `data.json` |
| 025 | Ingestion RSS (Radio France) |
| 024 | Lecture Webradio |
| 023 | Son de démarrage (chime) |
| 022 | Lecteur embarqué IHM enfant (`web/lecteur/index.html`) |
| 017 | Export Prometheus (métriques batterie/écoute) |
| 014 | Procédure de mise à jour documentée |
| 012 | Tests unitaires ingestion RSS |
| 011 | Durcir unités systemd (`ProtectSystem`, `NoNewPrivileges`) |
| 010 | Rotation logs |
| 008 | Endpoint `/health` (monitoring externe) |
| 007 | Interface configuration `podcasts.json` (via admin) |
| 005 | Interface d'administration complète (`web/index.php`) |
| 004 | Gestion multi-podcasts FR/ES |
| 003 | HiFiBerry Amp4 + MPD opérationnel |
| 002 | Monitoring batterie (INA219 + service systemd) |
| 001 | Structure projet + liens Apache |

# 🧩 Notes

## Collisions de numéros de ticket

Quatre paires ont partagé un numéro. Les tickets **clos ne sont jamais
renumérotés** — leur numéro vit dans l'historique git — ils sont donc
étiquetés `a`/`b`. Seuls les tickets encore vivants ont été renumérotés :

| Numéro | Sort |
|---|---|
| 090 → 117 | renuméroté le 2026-08-04 |
| 123 → 135 | renuméroté le 2026-08-17 ; le bug d'écran **garde 123**, il est cité dans du code vivant |
| 088a / 088b | étiquetés le 2026-08-21, tous deux clos |
| 089a / 089b | étiquetés le 2026-08-21, tous deux clos |

⚠️ **Collision de numéro résolue le 2026-08-17** : `TICKET-123` désignait **deux**
tickets différents — le bug d'écran (corrigé ce jour) et le registre de
non-régression (clos le 2026-08-05). Le bug d'écran **garde le 123**, parce qu'il
est référencé dans du code vivant (`buttons_daemon.py`, `smoke_test.sh`,
`75-NON_REGRESSION.md`). Le registre devient **TICKET-135**. Même remède que la
collision TICKET-090 → TICKET-117 du 2026-08-04.

<details>
<summary>Historique des mises à jour antérieures</summary>

> **2026-08-05** — TICKET-135 (ex-123) : registre de non-régression, 11 zones à risque + gardien. TICKET-122 : chien de garde MPD implémenté.
> **2026-08-04** — TICKET-120 : boutons physiques réparés (lgpio ne pouvait plus créer son tube depuis le durcissement TICKET-011, panne latente depuis le 2026-07-19). Ouverture de TICKET-121 et TICKET-119. TICKET-114 et TICKET-115 livrés et clos. Remise au propre du dépôt (TICKET-118) : fuite de prénom neutralisée, fichiers morts supprimés, `.gitignore` durci, collision TICKET-090 → TICKET-117.
> **2026-07-24** — TICKET-113 (bureau d'icônes admin) livré et clos ; TICKET-112 domotique validé en production.

</details>

- Repo public : aucun prénom personnel dans les fichiers versionnés (voir `15-INVARIANTS.md` §6.4)
- Prénoms réels autorisés uniquement dans `private/` (exclu du repo)
- Les tickets hardware (031, 038) sont isolés pour éviter les régressions logiciel
