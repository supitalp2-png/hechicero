# Backlog Hechicero

> **Convention** : `TICKET-### — [type] — Titre (date)`
> **États** : `[ ]` à faire · `[~]` en cours · `[x]` terminé ou annulé (→ section « Terminé »)
> **Dernière mise à jour : 2026-08-17**

## 📌 État des lieux — ce qui est ouvert

*Mis à jour le 2026-08-21. **Cette table ne liste QUE ce qui est ouvert** — un ticket
terminé descend immédiatement dans la section Terminé. Le détail de chaque ticket est
plus bas.*

| Ticket | Sujet | Où ça en est |
|---|---|---|
| **145** | Activer/désactiver les webradios depuis l'admin | ✅ **livré le 2026-08-21** — bascule comme les podcasts, effet immédiat sur l'écran enfant. **À essayer en réel** |
| **140** | Arrêt de charge nocturne, alimentation présente | 🔬 reproduit **3 fois** (54 %, 70 %, 96 %) ; temporisateur 6 h démenti — **cause inconnue**, désormais observable grâce au 141 |
| **127** | Vrai gel du kiosque du 2026-08-17 | l'épisode du 19/08 n'en était **pas** un (c'était le 138). Le gel du 17/08 reste **non expliqué** ; battement de cœur en place pour le prochain |
| **122** | MPD se fige si le réseau disparaît en webradio | logique de décision **couverte** (9 tests, 2026-08-21) ; la **récupération** — SIGKILL + redémarrage — reste non éprouvée |
| **058** | Série podcast « Décisions Prises » + easter egg | 2 épisodes écrits |

### ⏳ Livré mais pas encore éprouvé en conditions réelles

Ces tickets sont clos côté code et tests, mais **rien ne remplace l'usage**. À surveiller
dans les jours qui viennent :

| Ticket | Ce qui reste à observer |
|---|---|
| **119** | Le retour automatique à la radio après 10 min sans toucher l'écran technique |
| **138** | Qu'une veille survienne bien au bout de **600 s**, et que dalle et overlay s'éteignent ensemble. Si l'écran ne s'endort plus du tout, c'est TICKET-102 qui revient |
| **137 · 139 · 142** | Que le niveau affiché reste cohérent sur un cycle complet. `level_table` est publié à côté de `level` : leur écart mesure la dérive du comptage |
| **141** | Que la cadence plancher tienne, et que la purge s'exerce quand l'historique dépassera 30 jours |

**Clos le 2026-08-17** : 112 · 116 · 123 · 124 · 125 · 131 · 079 · 079bis · 017 (supprimé)
**Clos le 2026-08-18** : 134 (décharge profonde mesurée) · 136 (bandeau batterie figé 50 j)
**Clos le 2026-08-19** : 141 (enregistreur aveugle aux plateaux)
**Clos le 2026-08-21** : 119 (écran technique caché) · 111 (ventilateur, annulé) · 132 (bruit de journal) · 144 (risque assumé) · 145 (webradios activables) · 137 · 139 · 142 (chaîne de mesure batterie) · 143 (outil de recalibration) · 128 (registre HAT : démarrage, pas coupure) · 138 (veille unique) · 129 (PHP en UTC, après 4 morsures) · 121 (arrêt critique prouvé 2× en réel) · 126 · 130 · 133

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

---

# 🔥 Priorité haute

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
      - 🛠️ **À instrumenter ce soir** : journaliser la **température** (Pi et HAT si exposée) à chaque relevé. La plupart des chargeurs Li-ion inhibent la charge hors d'une fenêtre thermique, et le Pi 5 tourne à 67-68 °C sous le HAT. C'est le second candidat sérieux après le temporisateur.
      - 🔗 **À croiser avec TICKET-137** : `cycles_recorded: 2` et `model_confidence: "low"`. Cette journée de charge fournit un cycle de plus vers les 3-4 nécessaires à la recalibration de la table. Si le plateau est réel, il change aussi la capacité utile retenue pour le calcul d'autonomie (9 560 mAh envisagés).

- [~] TICKET-133 — bug/batterie — Détection charge/décharge par le signe du courant, et cycles faussés par l'arrêt d'urgence (2026-08-17)
      - ✅ **D'ABORD, LA BONNE NOUVELLE : l'arrêt d'urgence FONCTIONNE.** La décharge complète du 2026-08-17 est descendue à **15 %** et le Pi s'est éteint. C'est la preuve en conditions réelles du correctif de TICKET-121 — le `shutdown` sans `sudo`, bloqué en silence par `NoNewPrivileges` depuis juillet. Ce chemin n'avait jamais été exercé.
        - 📌 **Et j'avais lu les données de travers** : `battery_history.json` annonçait `level_end: 28`, j'en ai conclu que la décharge s'était arrêtée à 28 %. C'est le **graphique de l'admin** montré par Thomas qui a rétabli la vérité — la descente allait bien jusqu'à 15. Leçon : lire les points de mesure, pas les champs agrégés qui en dérivent.
      - 🔋 **Marge au moment de la coupure, pour la question du seuil** : niveau 15 % ⇒ **≈ 3,49 V** (table `_LIPO_TABLE`), sous une charge de **−2038 mA** (webradio + écran). La démonstration du fabricant, elle, ne coupe qu'en dessous de **3,15 V** maintenue 30 s. **Il reste donc une marge confortable** et le seuil de 15 % est prudent — descendre à 10 % (≈ 3,44 V) resterait au-dessus du seuil constructeur même avec l'affaissement sous forte charge. ⚠️ **Décision de Thomas : on ne touche à aucun seuil pour l'instant**, à réinterroger après plusieurs cycles.
      - ═══ DÉFAUT 1 — un seuil unique classait « décharge » des courants POSITIFS ═══
      - **Mesures du 2026-08-17**, appareil sur secteur, cellule presque pleine (phase CV) :
        | Heure | Courant | Ancienne classification |
        |---|---|---|
        | 15:25:02 | **+257,71 mA** | décharge (257 < 300) |
        | 15:26:02 | **+17,83 mA** | décharge (17 < 300) |
        | 15:47:03 | +683,67 mA | charge |
      - **Les trois courants sont positifs** — le courant ENTRE dans la batterie dans les trois cas. La règle `charging = current_ma > charge_threshold_ma` n'a **pas de zone morte** : tout ce qui est sous le seuil est déclaré décharge, y compris un courant positif. D'où trois faux cycles en 75 min, pendant lesquels **le niveau montait** (84→86 %, 82→86 %, 85→88 %). C'est le bug de juillet 2026 qui revenait, et le point de surveillance ouvert le matin même par TICKET-126.
      - ⚠️ **Ce n'était pas qu'un problème de statistiques** : `battery_watchdog` se sert du même booléen (`if not charging and level < critical_level`). Un courant faible mais positif était vu comme « pas en charge » — donc un arrêt possible alors que l'appareil est branché. Combinaison peu probable en pratique (à bas niveau le chargeur est en phase CC, à fort courant), mais le mécanisme était bien sur le chemin de l'arrêt d'urgence.
      - 🛠️ **Correctif — `battery_common.detecter_charge()`**, règle demandée par Thomas : le **signe** du courant décide, avec une bande morte de **±10 mA** (`charge_deadband_ma`) dans laquelle on **conserve l'état précédent** (hystérésis). C'est physiquement juste — le signe dit dans quel sens l'énergie circule ; la bande morte n'absorbe que le bruit de l'INA219 autour de zéro. `charge_threshold_ma` n'est plus utilisé (toléré dans un config.json existant, sans effet).
        - **Amorçage sûr** : sans état précédent et dans la bande morte, la fonction répond **charge**. Un courant quasi nul signifie que la batterie ne se vide pratiquement pas ; répondre « décharge » risquerait un arrêt injustifié. En cas de doute, on ne coupe pas le courant à un appareil qu'un enfant écoute peut-être.
        - Les deux appelants transmettent désormais l'état précédent : le tracker le relit dans `battery_stats.json` (le disque fait foi, cf. TICKET-126), le watchdog le garde d'un tour de boucle à l'autre — et ne le mémorise que si la lecture capteur a réussi.
      - ═══ DÉFAUT 2 — tout cycle profond était mal enregistré ═══
      - `close_discharge()` figeait `level_end` et `discharge_end` sur l'échantillon de **bascule** vers la charge. Or une décharge profonde se termine par l'arrêt du Pi : la bascule n'est observée qu'au **redémarrage**, une fois rebranché, quand la tension est déjà remontée.
        | | Réel | Enregistré |
        |---|---|---|
        | Décharge | 85 % → **15 %** | 85 % → **28 %** |
        | Durée | ~207 min | 212 min, **temps hors tension inclus** |
      - ⚠️ **Systématique, pas occasionnel** : *toute* décharge profonde finit par un arrêt, donc **tous** les cycles profonds étaient faussés de la même façon — précisément ceux qui portent le plus d'information. L'`estimated_autonomy_minutes: 43` calculé sur ce cycle ne valait donc rien.
      - 🛠️ **Correctif** : on retient le **minimum réellement observé** parmi les points de décharge et l'horodatage du **dernier relevé**, pas ceux de la bascule. Un trou de plus de 10 minutes est signalé explicitement (`gap_minutes`, `gap_reason`) plutôt que noyé dans la durée.
      - 📈 **Compréhension — la tension est désormais enregistrée à chaque point** (`voltage_v` dans les `datapoints`). Le niveau n'est qu'une lecture de table à partir d'elle (`percent_from_voltage`) ; sans la tension, impossible de rejouer un diagnostic ou de vérifier une marge après coup. C'est ce qui a manqué ce soir pour répondre directement à la question du HAT.
      - ✅ **Tests unitaires — `scripts/test_batterie.py`, 22 assertions**, sur les mesures réelles du jour : les courants +257 et +17 mA, la bande morte dans les deux sens, l'amorçage sûr pour le watchdog, la clôture avec trou (point bas 15, durée 207, gap 5 min), un cycle normal inchangé, et le micro-cycle CV toujours invalidé. Intégrés au smoke test §5, plus une garde qui échoue si le seuil unique revient.
      - 📊 **Tableau de bord alimentation revu** (`web/admin/battery_dashboard.php`), sur les quatre manques révélés par la soirée :
        - **Tension et courant sur 24 h, en DEUX graphes empilés** partageant l'axe du temps. ⚠️ Première version tentée : les deux séries superposées sur un double axe — illisible, et pour une raison structurelle, pas cosmétique : le courant couvre −4000 à +2000 mA quand la tension tient dans 60 mV. Le courant écrasait tout. Ligne pointillée à 0 mA sur le graphe de courant : c'est la frontière charge/décharge, donc la lecture qui compte depuis que le signe décide. C'était le manque le plus criant : tout le tableau raisonnait en **pourcentage**, qui n'est qu'une conversion de la tension. Pour répondre à la question de la marge du HAT, il a fallu reconstruire la tension depuis le niveau — l'information brute n'était affichée nulle part. Le courant y figure avec son signe, dont dépend désormais la classification.
        - **Colonne « Fiabilité »** dans l'historique des cycles : un cycle interrompu par l'arrêt d'urgence affiche `⚠ trou N min` au lieu de se présenter comme une mesure propre. C'est précisément ce qui a fait lire « décharge jusqu'à 28 % » alors que la vraie descente allait à 15 %.
        - **Alerte sur les valeurs impossibles** : « Podcast 102 %/h » était affiché comme un fait. Au-delà de 100 %/h la batterie se viderait en moins d'une heure — c'est le symptôme d'un cycle incomplet, désormais nommé comme tel.
        - **Ligne du seuil d'arrêt** sur les courbes de décharge, lue depuis `config.json` (pas codée en dur) : la marge se juge d'un coup d'œil, ce qui servira quand le seuil sera réinterrogé.
        - Le graphe tension reste vide tant que les relevés ne se sont pas accumulés — la tension n'est enregistrée que depuis ce soir. Le panneau l'explique plutôt que d'afficher un cadre vide.
      - ⏳ **Reste** : les cycles de charge/décharge de Thomas alimenteront un modèle enfin correct. Le seuil de coupure sera réinterrogé à ce moment-là, pas avant.

- [~] TICKET-130 — bug/données — Neuf podcasts ont disparu de la config, en silence, pendant deux semaines (2026-08-17)
      - **Symptôme (Thomas)** : « mini vulgaire je suis certain de l'avoir ajouté, il a disparu de la liste ? ». Découvert par hasard, en intégrant `check_integrity.py` au smoke test — pas par un utilisateur, pas par une alerte.
      - 🔍 **Établi par les faits, pas par déduction** :
        - `git log -S'minivulgaire' -- data/podcasts.json` ne renvoie **rien** : ces podcasts n'ont **jamais** figuré dans une version committée du fichier.
        - Le fichier n'a **jamais dépassé 24 entrées** en 14 commits (1 → 2 → 18 → 20 → 21 → 23 → 24, stable depuis le 2026-08-05).
        - Pourtant `podcasts/minivulgaire/meta.json` est daté du **2026-08-03 03:00:17** — l'heure du cron d'ingestion. Ils étaient donc bien dans la config cette nuit-là, puisque l'ingestion ne travaille que depuis elle.
        - Les `meta.json` des neuf forment un **bloc contigu** en date de modification, tous plus anciens que ceux des 24 actifs (rafraîchis chaque nuit) : leur date est figée au moment où ils ont quitté la config.
      - 🔴 **Cause racine — `data/podcasts.json` est à la fois suivi par git et réécrit à l'exécution par l'IHM admin.** Les neuf avaient été ajoutés depuis l'admin, donc dans le fichier de travail et jamais dans un commit. Une opération git les a ramenés à l'état HEAD. Aucun message, aucune erreur.
        - **Contexte probable** : le 2026-08-04, TICKET-118 a réécrit l'historique (`git filter-repo`) pour la fuite de prénom, avec clone miroir. Le calendrier colle (ingestion le 3, réécriture le 4, fichier à 24 le 5) mais ce n'est **pas prouvé** — le `reflog` n'a pas été relevé. À laisser en probable.
        - 📌 **Le `.gitignore` du 2026-08-04 a exclu tous les « purs états runtime »… sauf les deux que l'admin écrit** : `data/podcasts.json` et `data/parental.json`. L'oubli est exactement là où il fait mal.
      - ✅ **Aucune perte de contenu** : audio, images et `meta.json` des neuf sont intacts. Rien à retélécharger.
      - 🛠️ **Réparation — `scripts/restore_lost_podcasts.py`** (`--apply` pour écrire, simulation par défaut, sauvegarde horodatée avant écriture). `meta.json` ne stocke **pas** l'URL du flux ; elles ont été retrouvées dans `data/ingest_full_20260802_1928.log`, qui journalise `Podcast : <label> (<id>)` puis `Parsing RSS: <url>`. **C'est la seule raison pour laquelle cette réparation est possible** — sans ce journal, il aurait fallu retrouver neuf flux à la main.
      - **Décision de Thomas (2026-08-17) : le fichier reste versionné.** Contrepartie assumée : il faut **committer `data/podcasts.json` après chaque ajout depuis l'admin**, sans quoi le prochain `checkout` recommencera.
      - ✅ **Garde-fou livré** (smoke test §9) : comparaison du nombre d'entrées de la config au nombre de `podcasts/*/meta.json`. Un écart devient visible en une seconde. `warn` et non `fail` — un écart peut être légitime (podcast retiré dont le dossier subsiste) ; ce qui compte est qu'il soit vu. **C'est ce contrôle qui rend le choix de garder le fichier dans git tenable** : le vrai défaut n'était pas la disparition, c'étaient les deux semaines de silence.
      - ✅ **Restauration effectuée le 2026-08-17 à 16:43:07 par `restore_lost_podcasts.py --apply`**, puis `ingest.py` a reconstruit `data.json` (643 Ko → 821 Ko). Les 33 podcasts sont de nouveau dans l'IHM enfant, sans un octet retéléchargé. Smoke test : **50 OK · 0 échec**, §9 « config et disque d'accord — 33 podcasts ».
        - 📌 **Erreur de lecture de ma part, à ne pas reproduire** : un second passage du script affichait « déjà présent, ignoré » pour les neuf, et j'en ai conclu que Thomas les avait remis à la main. Faux. La preuve était sous les yeux dans `git status` : le fichier `data/podcasts.json.avant_restauration_20260817_164307` **ne peut être créé que par le script, et seulement quand il a des entrées à ajouter** (la sauvegarde intervient après le `if not a_ajouter: return`). Leçon : quand une trace horodatée contredit une interprétation, c'est la trace qui a raison.
      - 🧹 **Deux effets de bord du commit `e081296`, tous deux de la même famille que le bug lui-même** :
        1. La **sauvegarde du script a été versionnée** (`data/podcasts.json.avant_restauration_…`). C'est une copie de sécurité locale, pas de l'historique — git a déjà le sien. Ajouté au `.gitignore` (`data/config_backups/`, `data/*.avant_restauration_*`, `data/*.json.bak-*`) et à retirer du suivi.
        2. **`web/lecteur/config.json` a été emporté par le `git add -A`** alors qu'il n'avait pas été modifié à la main : c'est l'admin qui l'écrit. **Troisième fichier de la même catégorie** après `podcasts.json` et `parental.json` — suivi par git ET réécrit à l'exécution. Il court donc le même risque de disparition silencieuse.
      - ✅ **Verrou validé en réel le 2026-08-17** : `toggle_podcast` appelé **cinq fois en parallèle** (`curl … &` puis `wait`) → **33 podcasts avant, 33 après**. C'est exactement la situation qui perdait des entrées ; elle ne les perd plus. Le test se fait par `curl` sur `index.php?action=toggle_podcast`, sans passer par l'IHM — plus rapide et reproductible.
      - 🐛 **Défaut trouvé PAR ce test, dans mon propre correctif** : deux écritures rapprochées ne laissaient **qu'une seule sauvegarde**. L'horodatage était à la seconde (`date('Ymd_His')`), les deux `curl` sont tombés dans la même seconde, et le second `copy()` a écrasé le premier. **Or le cas qui justifie ce filet est précisément la rafale d'écritures** — celle contre laquelle le verrou protège. Une copie sur cinq, et la plus récente (donc potentiellement déjà abîmée), n'aurait servi à rien. Corrigé en `Ymd_His_v` (millisecondes) **et en heure locale explicite** : PHP tournant en UTC (TICKET-129), les noms affichaient `145507` pendant que `ls` montrait `16:55`, soit deux heures d'écart dans un listing qu'on consulte en urgence.
        - 📌 **Leçon** : un mécanisme de sauvegarde ne se valide pas en le lisant, mais en l'exerçant dans le cas qui l'a motivé. Le premier essai a suffi à trouver le défaut.
      - ✅ **Tests de garde ajoutés** (smoke test §3) : présence du verrou (`acquire_json_lock` + `mutate_json`), horodatage à la milliseconde, et existence de `data/config_backups/` — un `warn` explicite tant que le filet n'a jamais servi, avec la commande pour l'exercer. Parce qu'au commit `e081296` il était livré sans avoir jamais tourné.
      - ⏳ **Reste** : **`data/parental.json` et `web/lecteur/config.json` courent exactement le même risque** — même statut, même IHM. Le verrou et les sauvegardes les couvrent désormais (ils sont dans `BACKED_UP_FILES`), mais **ce mécanisme n'a encore jamais été exercé** : `data/config_backups/` n'existait pas au moment du commit, donc aucune écriture admin n'a eu lieu depuis. À valider avant de s'y fier.
      - 📌 **Leçon** : un fichier ne peut pas avoir deux sources d'autorité. S'il en a deux, il faut au minimum que la divergence soit bruyante.

- [~] TICKET-127 — bug/instrumentation — Écran noir figé : la page cesse d'exécuter du JavaScript (2026-08-17)
      - **Symptôme (Thomas)** : « par moment l'écran se met en veille et n'arrive pas à sortir de la veille. La dalle tactile fonctionne, les boutons fonctionnent, Hechicero lit les fichiers, mais quand on appuie sur l'écran il reste désespérément noir. » Et : « je suis obligé de faire un hard reset pour rétablir le fonctionnement de l'écran. »
      - ❌ **Ce n'est PAS TICKET-115** (dalle éteinte, `--on --preferred` no-op). Relevé pendant la panne : `screen_dpms.log` n'a **aucun `off`** depuis la veille 10:51, et `wlr-randr` donne `Enabled: yes` sur `1024x600@59.821 (preferred, current)`. Le DPMS n'a jamais été sollicité — la dalle affichait bel et bien quelque chose.
      - ❌ **Ce n'est pas non plus le filtre anti-touchers-fantômes** (hypothèse initiale : `index.html` n'écoute que `click`/`keydown`, `touchstart`/`pointerdown` étant exclus depuis TICKET-098, donc une dalle qui émet des `touchstart` sans `touchend` ne produirait jamais de `click` et `wakeUp()` ne partirait jamais). Piste séduisante, mais fausse ici : rien ne s'exécutait plus du tout.
      - 🔍 **Cause établie — le moteur de rendu s'est arrêté.** Dans `data/sleep_debug.log` :
        - `07:47:38  activate_sleep already_active=false` — l'overlay de veille s'affiche
        - `07:47:48  apply_sleep_config` · `07:52:48  apply_sleep_config` — puis **plus rien, jamais**
        - La boucle de 5 min (`index.html`, `setInterval(… loadParentalConfig(); refreshCatalogInPlace() …)`) aurait dû réécrire cette ligne à 07:57:48, 08:02:48, etc.
        - **Et ce n'est pas une panne réseau ou PHP** : dans `loadParentalConfig()`, `applySleepConfig(parentalCfg)` est appelé **hors du `try/catch`** — même avec le fetch en échec, le fallback s'applique et la ligne part quand même. Son silence ne peut donc venir que de l'arrêt de l'exécution.
        - ➜ **La page a cessé d'exécuter du JavaScript entre 07:52:48 et 07:57:48, en laissant l'overlay de veille comme dernière image peinte.** Écran noir, mais figé, pas éteint.
      - **Pourquoi tout le reste semblait normal** : `buttons_daemon` et MPD sont des processus séparés qui ne passent pas par la page — d'où des boutons et un son parfaitement vivants. Le tactile « fonctionnait » aussi : le digitaliseur émettait bien des événements, mais plus personne ne les écoutait. Et le hard reset marche parce qu'il recharge la page.
      - ⚠️ **Ambiguïté du premier relevé, à ne pas reproduire** : les étapes `curl request_screen` et `screen_dpms.sh rescue` ont été collées dans le même bloc, donc on ne sait pas laquelle a rétabli l'image. C'est important : si c'est le `rescue`, le rebond de mode force Chromium à re-peindre et on a une **sortie de panne sans reboot**. Au prochain épisode : `curl` seul, attendre 3 s, puis `rescue`.
      - 🛠️ **Instrumentation livrée le 2026-08-17 — on corrige sur des faits, pas sur des suppositions** (demande explicite de Thomas) :
        - **Battement de cœur** — `radio.php?action=kiosk_beat`, appelé toutes les 15 s par `index.html`, **écrase** `data/kiosk_heartbeat.json` (ts, overlay affiché ou non, écran courant, âge de la page, nº de battement, état MPD). Écrasement et non append : c'est un **état**, pas un journal, donc le fichier reste à quelques centaines d'octets — contrairement à `data/sleep_debug.log`, qui a fini à plusieurs Mo avec des octets NUL après une coupure de courant.
        - **Guetteur** — `scripts/kiosk_freeze_watch.py` + `.service`, sonde le battement toutes les 20 s. Au-delà de 60 s de silence (quatre battements manqués), écrit **un seul** instantané dans `data/kiosk_freeze.log`, puis se tait jusqu'au retour du battement, qu'il journalise aussi.
        - **Contenu de l'instantané** : le dernier battement connu (donc l'état de l'IHM juste avant la mort) · **`vcgencmd get_throttled` / `measure_volts` / `measure_temp`** · `wlr-randr` · processus Chromium avec `stat`, `wchan` et RSS · `free -m` · `dmesg` · `journalctl` utilisateur ET système des 10 dernières minutes · sonde du socket MPD.
        - **`get_throttled` est le suspect nº 1** : la panne apparaît juste après le remplacement des cellules (TICKET-126). Un Pi 5 en sous-tension fige le GPU avant de rebooter, et ça se lit dans un registre — pas dans une hypothèse. Bits 0-3 = état instantané, bits 16-19 = événements survenus depuis le boot.
        - **Il observe uniquement.** Aucune relance de Chromium, aucun rebond de mode automatique (décision de Thomas) : un guetteur qui répare masque la panne et fait perdre la fenêtre d'observation.
        - Pièges du projet respectés : **jamais `mpc`** (sonde directe de `/run/mpd/socket` sous délai de garde — leçon TICKET-122), toute commande sous `timeout`, **pas de `Requires=`** dans l'unité (leçon TICKET-121), pas de `PrivateDevices` (casserait `vcgencmd`), écritures confinées à `data/` via `ReadWritePaths`.
      - ✅ **Tests de garde ajoutés** (`scripts/smoke_test.sh`) : §3 le battement est armé **et** `kioskHeartbeat()` ne touche pas au timer de veille (contrôle du corps de la fonction — voir ci-dessous) ; §5 le service tourne et le battement a moins de 60 s, sinon **`fail`** avec la sortie de panne à afficher. Aucun test existant ne pouvait voir cette panne : aucun ne regardait la page elle-même.
      - ⚠️ **Risque de régression accepté par Thomas (zone Z4)** : le battement tourne à 15 s, soit bien plus vite que `sleep_delay` (120 s). C'est exactement la configuration qui a produit TICKET-102 — `checkParentalTime` à 30 s appelait `resetSleepTimer()` et repoussait le compte à rebours à l'infini, l'écran de veille ne s'affichait plus jamais. Mitigation : `kioskHeartbeat()` ne fait **qu'un fetch**, et le smoke test échoue s'il trouve `resetSleepTimer`, `clearTimeout` ou `sleepTimer` dans son corps.
      - ⏰ **Correction d'horodatage — les journaux ne sont pas dans le même fuseau.** PHP tourne en **UTC** ; le shell (`screen_dpms.log`) et Python (`kiosk_freeze.log`) écrivent en **heure locale**, soit +2 h l'été. Donc le « 07:52:48 » de `sleep_debug.log` cité plus haut correspond à **09:52:48 sur l'horloge de la maison** — juste après le smoke test de 09:44, ce qui reste cohérent avec la conclusion. Le battement expose désormais `local` en plus de `ts` (epoch, celui que le guetteur compare) et `iso` (UTC). ✅ Vérifié : le contrôle parental n'est **pas** concerné, les horaires sont évalués côté navigateur, `parental_status` ne sert que le planning brut.
      - 🧨 **Effet de bord découvert en installant l'instrumentation — le code déployé n'atteignait pas l'écran.** Après ajout du battement, `data/kiosk_heartbeat.json` refusait d'apparaître. Diagnostic : `php -l` valide, `curl` sur `action=kiosk_beat` créait bien le fichier, `curl` sur `/lecteur/` renvoyait le nouveau JS — mais **Chromium exécutait sa copie en cache**. `restart-kiosk.sh` ne lance pas Chromium en `--incognito` (contrairement au `.desktop`), son profil survit aux relances, et aucun en-tête anti-cache n'était envoyé. **C'est la pire famille de panne du projet** : on croit avoir corrigé, l'ancien code tourne, et tous les diagnostics suivants sont faussés. Promu en **zone Z12** du registre.
        - Correctif livré : `scripts/apache-hechicero-nocache.conf` — `mod_headers` (absent, activé) + `Cache-Control: no-store` sur `^/lecteur/?$` et `^/lecteur/.+\.html$`. `<LocationMatch>` et non `<Directory>` : filtre sur l'URL, donc indépendant du `DocumentRoot` (`/var/www/html`, `~/hechicero/web` y étant lié) et reproductible sur une image SD fraîche. `.htaccess` était exclu (`AllowOverride None` dans `apache2.conf`). Limité au HTML : polices, images et sons restent en cache.
        - Vérifié en réel : `apachectl configtest` → `Syntax OK`, puis `curl -sI /lecteur/` renvoie bien les trois en-têtes.
        - Tests de garde : smoke test §3 compare le `md5` d'`index.html` sur le disque à celui de la **page servie** (`fail` si écart) et lit `Cache-Control` dans la **réponse** (`warn` si absent). La leçon : les contrôles existants regardaient tous le fichier, jamais la réponse.
      - ✅ **Instrumentation validée en réel le 2026-08-17** : smoke test **41 OK · 0 échec · 1 avertissement** (TICKET-125, connu). Le battement vit (`écran=home veille=true`, 10 s), `kiosk_freeze_watch` tourne, et l'instantané `--test` répond. Surtout, l'état sain se distingue maintenant du gel : **overlay affiché + battement frais = veille normale ; overlay affiché + battement vieux = gel**. Cette distinction était impossible le matin même.
      - ✅ **Risque Z4 levé par la mesure** : l'overlay de veille s'est bien activé malgré le battement à 15 s (`veille=true` dans le battement). La mitigation tient.
      - ⏳ **Reste à faire** : **attendre le prochain épisode**. Le battement date le gel, il ne l'explique pas encore — la cause sortira de l'instantané (`get_throttled` en tête de liste). Et au prochain écran noir : `curl request_screen` **seul**, attendre 3 s, puis `rescue` — pour savoir enfin lequel des deux rétablit l'image.

- [~] TICKET-126 — maintenance/batterie — Remise à zéro des mesures batterie après remplacement des cellules (2026-08-17)
      - **Contexte** : les cellules ont été **remplacées physiquement** le 2026-08-16 vers 12h.
      - 🔴 **CORRECTION DU 2026-08-17 SOIR — la capacité N'ÉTAIT PAS inchangée.** Les nouvelles cellules sont **2 × EVE INR21700/58E** (5600 mAh, 20,16 Wh chacune, marquage `1QBM110H`), en parallèle : **11 200 mAh**, contre ~6600 pour l'ancien pack de 18650. **+70 %.**
        - `battery_capacity_mah` est resté à 6600 toute la journée. Cette valeur ne sert qu'à `estimated_autonomy_minutes_live` (`capacité × niveau utilisable ÷ courant`) : **l'autonomie temps réel était donc sous-estimée de 41 %**. Corrigé à 11200.
        - 📌 **Comment l'erreur a tenu une journée** : Thomas avait indiqué « capacité inchangée », je l'ai inscrit tel quel sans le recouper avec le matériel réel. La consigne portait sur le fait de ne pas toucher au réglage ; elle ne disait pas que les cellules avaient la même capacité. **Une instruction sur un réglage n'est pas une mesure.** Détail cohérent qui aurait dû alerter : son propre constat « la batterie est nettement plus performante ».
        - Caractéristiques complètes désormais dans `docs/80-hardware.md` §4, y compris le plancher pratique de 3,0 V et le fait que `_LIPO_TABLE` n'a jamais été recalée sur ces cellules. L'ancien historique décrit une batterie qui n'existe plus : il fausse `estimated_autonomy_minutes` et `consumption_by_mode`. Décision Thomas : **suppression définitive, pas d'archive**.
      - **Le niveau (%) n'est PAS concerné.** `percent_from_voltage()` (`battery_common.py`) est une simple table de correspondance tension→pourcentage, sans compteur coulométrique et sans mémoire. Le niveau affiché est donc déjà juste avec les nouvelles cellules dès le premier échantillon. Seul le **modèle d'estimation** (ratios min/%, autonomie, temps de charge) est à réapprendre.
      - 🔍 **Le cycle aberrant existe bien, et il est instructif** (dernier cycle de `data/battery_history.json`, avant remise à zéro) :
        - `2026-08-16T12:04:01` — 49 %, `current_ma` **+277,83**, pourtant `charging: false` : le courant est positif mais **sous le seuil `charge_threshold_ma = 300`**, donc classé « décharge ». Le seuil de 300 mA n'est pas seulement fragile en théorie, il se trompait déjà avec les anciennes cellules.
        - `12:06` → **−2669 mA**, 20 % · `12:07` → −2968 mA, 16 % · `12:08` → −2861 mA, 13 %. **Le niveau chute de 49 % à 13 % en quatre minutes.** Comme le niveau vient de la tension, c'est un **effondrement de tension sous charge** : la résistance interne des vieilles cellules était devenue telle qu'elles ne tenaient plus le courant. C'est la signature de leur fin de vie, pas une erreur de mesure — le remplacement était justifié.
        - Puis **21 heures de trou** (Pi coupé net pendant l'échange, sans arrêt propre), et reprise à `2026-08-17T09:21:47` à 31 %, `charging: true`.
        - **Résultat enregistré** : un cycle `discharge_start 08-16T12:04 (49 %)` → `discharge_end 08-17T09:21 (31 %)`, `duration_minutes: 1278`, **non marqué `invalid`** (18 % consommés ≥ `MIN_CYCLE_DEPTH_PCT`, 1278 min ≥ `MIN_CYCLE_DURATION_MIN`). Il compte donc dans les **29 cycles** de `battery_stats.json` et pollue le modèle : `active_discharge_minutes()` ne retient que ~4 minutes de décharge réelle pour 18 % consommés, soit **0,22 min/%** — une autonomie quasi nulle, injectée telle quelle dans la moyenne.
        - 📌 **Leçon pour le futur** : les garde-fous `invalid` filtrent les micro-cycles *courts*, pas un cycle **interrompu par une coupure d'alimentation**. Un trou de plusieurs heures entre deux échantillons devrait suffire à invalider un cycle. Piste : marquer `invalid` si l'écart entre deux `datapoints` consécutifs dépasse largement `battery_check_interval_seconds` (p. ex. > 10 × l'intervalle). Non implémenté — à ouvrir si le cas se reproduit.
      - 🧹 **Résidu à nettoyer** : `data/battery_history.json.hwy9gf7c` — fichier temporaire de `atomic_write_text()` (`tempfile.mkstemp(prefix=path.name + ".")`), laissé orphelin par la coupure d'alimentation en pleine écriture. Le `os.replace()` n'a jamais eu lieu. Sans danger, mais à supprimer avec le reste.
      - 🛠️ **Procédure appliquée** — l'ordre n'est pas négociable, les services doivent être arrêtés **avant** la suppression :
        1. `sudo systemctl stop battery_tracker battery_watchdog`
        2. `rm -f ~/hechicero/data/{battery_history.json,battery_stats.json,last_session.json} ~/hechicero/data/battery_*.json.*`
        3. `sudo systemctl start battery_tracker battery_watchdog`
        4. contrôle : `cycles_recorded == 0` et `model_confidence == "low"` dans `data/battery_stats.json`
        - 💡 **Pourquoi arrêter les services d'abord** : `battery_tracker` relit bien history/stats **depuis le disque** à chaque tour de boucle (`load_history()` / `load_stats()`), donc il ne réécrirait pas 29 cycles depuis sa mémoire — mais son intervalle est de **60 s** et il écrit systématiquement (`write_outputs()` à chaque `collect_once()`). Supprimer à chaud, c'est une course perdue d'avance : un fichier réapparaît dans la minute et on croit la remise à zéro faite. `battery_watchdog` est arrêté pour la même raison, il est le seul auteur de `last_session.json`.
        - **`data/tracking.db` ne doit PAS être touché** : c'est l'historique d'écoute, il n'a rien à voir avec la batterie.
        - **À faire branché au secteur**, pour que le premier cycle de décharge mesuré parte d'une batterie pleine. Au moment de la remise à zéro la batterie était à 30 % en charge (711 mA) : le premier cycle enregistré sera une charge sans `discharge_end`, donc **exclu de `complete_cycles`** — inoffensif, il ne faussera pas le modèle.
      - ✅ **Remise à zéro effectuée et vérifiée le 2026-08-17 à 09:44:59** : `cycles_recorded: 0`, `model_confidence: "low"`, `estimated_autonomy_minutes: null` et les trois `consumption_by_mode` à `null` — le modèle est bien vide, pas seulement le compteur. `last_session.json` et le temporaire orphelin `.hwy9gf7c` ont disparu. `battery_history.json` recréé propre avec un unique cycle ouvert (`charge_start 09:44:59`, `level_end: 33`, un seul datapoint) : exactement le cycle de charge sans `discharge_end` attendu, donc exclu de `complete_cycles`. `smoke_test.sh` : **35 OK · 0 échec · 1 avertissement** (TICKET-125, connu et volontaire) ; `battery_tracker` et `battery_watchdog` actifs.
      - 🗄️ **Reste dans `data/archive/`** : `battery_history_20260706_2223.json` et `battery_stats_20260706_2223.json`, archive de la passe du 2026-07-06. Elles décrivent **aussi** les anciennes cellules et n'ont donc plus de valeur de référence pour la batterie actuelle. Gitignorées, sans effet sur le modèle (`battery_tracker` ne lit que `data/`, pas `data/archive/`) — à supprimer à l'occasion pour éviter de s'y fier par erreur plus tard.
      - ⏳ **À surveiller après le premier cycle complet — `charge_threshold_ma = 300`** : ce seuil (`data/config.json`) avait été réglé en Session 12 pour la phase CV des **anciennes** cellules, afin d'éliminer les oscillations charge/décharge. Si les nouvelles cellules se comportent autrement, les **faux micro-cycles de juillet 2026 peuvent réapparaître** (cf. les dizaines de cycles `invalid` du 2026-07-15 et du 2026-08-15 dans l'historique supprimé). Le signe à guetter : une rafale de cycles de 1 à 2 minutes dans `battery_history.json`, ou `cycles_recorded` qui grimpe anormalement vite. Correctif alors : ajuster le seuil au courant réel observé en fin de charge (`current_ma` dans `battery_stats.json` quand le niveau plafonne).
      - 🐛 **Défaut annexe trouvé en passant — `battery_watchdog.py:127`** : dans la branche `--simulate-critical`, `level, _ = read_level(sensor, config)` dépaquette **deux** valeurs alors que `read_level()` en retourne **trois** (`level, charging, sensor`) → `ValueError` immédiat. C'est précisément le chemin qui sert à tester l'arrêt critique, ce qui explique sans doute que le `battery_watchdog` soit resté le **seul service non prouvé du durcissement TICKET-011**. Correctif : `level, _, _ = read_level(...)`. À traiter avec TICKET-121.

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

# 🟢 Priorité basse / À décider

# ✔️ Terminé

- [x] TICKET-119 — feature/admin — Écran technique caché, ouvert par combinaison de boutons physiques (2026-08-04) — ✅ **LIVRÉ le 2026-08-21**
      - 🛠️ **Combinaison** : appui simultané de 3 s sur casque (GPIO25) + antenne (GPIO23). ⚠️ **Piège de la zone Z3** : ces deux boutons agissent **à l'appui**, pas au relâchement — sans précaution la combinaison basculait la sortie audio et ouvrait l'écran Chambre au passage. Leur action individuelle est donc différée de 300 ms, **elles seules** ; les sept autres boutons gardent leur réactivité immédiate.
      - 🛠️ **L'écran est une PAGE** (`web/admin/technique.php`) vers laquelle le kiosque navigue, pas un écran de plus dans `index.html`. La lecture continue, MPD étant côté serveur. Contenu : IP de **chaque** interface active, batterie avec `level_table` à côté du niveau, curseur de gain casque, sortie du kiosque.
      - 🔗 **Gain casque dans `web/admin/eq_gain.php`, partagé** avec `audio_eq.php` : deux IHM sur un même réglage divergent (zone Z11). Le plafond de 6 dB y vit aussi — **pas dans les pages**, un futur appelant l'oublierait, et c'est un garde-fou auditif. N'écrase que `gain_db`, jamais les dix bandes (leçon de TICKET-124).
      - 🛠️ **Retour automatique** calé sur `screen_off_delay` : on a quitté le lecteur, son minuteur ne tourne plus. Sans ça, l'enfant retrouverait un écran de réglages au lieu de ses podcasts.
      - 🔓 **Sortie du kiosque** via une règle sudoers étroite (`pkill -u thomas -x chromium`). **Décision de Thomas : pas de relance automatique**, le redémarrage est la porte de sortie assumée. Ce qui se passe ensuite sur le bureau ne relève pas de ce projet.
      - ⚠️ **Le premier essai a échoué, et c'était la zone Z12** : le daemon écrivait bien `{"screen":"technique"}`, le disque savait le traiter, mais **le kiosque tournait encore sur l'ancien `index.html` chargé en mémoire**. Un `wtype -k F5` a suffi. **Le smoke test ne peut pas voir ça** — il compare la réponse d'Apache au disque, pas ce que Chromium exécute. Toute modification de `index.html` exige ce rechargement, sous peine de tester l'ancienne version en croyant tester la nouvelle.
      - ✅ **Éprouvé en réel le 2026-08-21** : combinaison, écran, curseur de gain et **sortie du kiosque**. ⏳ Reste le retour automatique après 10 min — le seul point qui demande d'attendre.
      - 📌 **Écarté volontairement** : les 10 bandes d'égaliseur. Se règlent mal au doigt sur 7 pouces, et `audio_eq.php` le fait déjà très bien depuis un téléphone — or l'intérêt de cet écran est justement d'exister **quand l'admin n'est pas joignable**.
      - **Demande de Thomas** : un **appui long simultané sur le bouton casque (GPIO25, « source ») et le bouton antenne (GPIO23)** ouvre une page d'administration technique affichant l'**adresse IP** d'Hechicero, des **informations batterie**, et permettant de **modifier l'égaliseur**.
      - ⚠️ **Cadrage seulement — rien à implémenter pour l'instant** (décision Thomas, 2026-08-04).
      - **Pourquoi c'est utile** : en mobilité, retrouver l'IP du Pi est aujourd'hui un chemin de croix (partage de connexion du téléphone, câble USB-Ethernet + ICS, cf. TICKET-109/110 et la procédure d'accès de secours). Un écran qui l'affiche directement supprime le besoin de SSH pour la question la plus fréquente.
      - **Contenu envisagé** :
        - IP de **chaque interface active** (`wlan0`, `eth0` USB-Ethernet), pas seulement la première trouvée — c'est précisément quand elles changent qu'on a besoin de l'écran. Plus SSID et qualité du signal.
        - Batterie : niveau, statut (secteur / décharge / charge), autonomie estimée — données déjà disponibles dans `data/battery_stats.json` (cf. `docs/05-POWER_MANAGEMENT.md`).
        - Égaliseur : réglage des 10 bandes pour les 2 profils HP/casque — la mécanique existe déjà (TICKET-030, `alsaequal`, `web/admin/audio_eq.php`, `scripts/audio_eq_apply.py`).
      - **Points à trancher avant de coder** :
        1. **Écran du lecteur ou page admin ?** Naviguer Chromium vers `/admin/` sortirait du kiosque et couperait le fil de la lecture. Le modèle de l'écran Chambre (TICKET-112) — un écran de plus dans `index.html`, avec mini-lecteur conservé — est probablement le bon, quitte à ne réimplémenter que l'essentiel de l'EQ. À arbitrer selon l'effort.
        2. **Détection de la combinaison.** `buttons_daemon.py` gère aujourd'hui chaque broche indépendamment (poll 10 ms, anti-rebond 3 niveaux, `TAP_OR_HOLD`). Une combinaison demande un état supplémentaire : détecter que **les deux** broches sont maintenues, **et supprimer les actions individuelles** — sinon l'appui déclencherait aussi la bascule HP/casque (GPIO25) et l'ouverture de l'écran Chambre (GPIO23). C'est le vrai travail du ticket.
        3. **Fenêtre de tolérance** : les deux boutons ne seront jamais pressés à la milliseconde près. Prévoir un délai de grâce (~300 ms) avant de considérer qu'il s'agit d'un appui simple, donc un léger retard sur les actions de GPIO25 et GPIO23 — à vérifier qu'il reste imperceptible.
        4. **Sortie de l'écran** : retour à l'écran précédent (modèle Chambre), pas retour forcé à l'accueil.
      - **Réutiliser l'existant** : le canal `request_screen` / `get_ui_request` (`radio.php`, déjà générique) sert exactement à ça — le daemon Python écrit la demande, `index.html` la consomme par polling. Aucune modification PHP nécessaire côté transport, comme pour les favoris (TICKET-046) et la Chambre (TICKET-112).
      - **Sécurité / usage** : c'est un écran **parent**. Il ne doit pas exposer de secret (aucun jeton, aucun identifiant de la passerelle domotique) ni offrir de contournement du contrôle parental. La combinaison à deux boutons maintenus est déjà, en soi, une protection raisonnable contre un déclenchement accidentel par l'enfant.
      - ❓ **À confirmer avec Thomas** : l'écran doit-il rester accessible en dehors des horaires autorisés d'écoute (comme l'écran Chambre) ? A priori oui, c'est un outil de dépannage.


- [x] TICKET-111 — hardware — Ventilateur GPIO/PWM pour dissipation thermique (2026-07-18) — ❌ **ANNULÉ le 2026-08-21** (renuméroté depuis TICKET-110, en collision avec le ticket roaming — 2026-07-18)
      - Demande de Thomas : boîtier chaud, ventilateur silencieux souhaité. Corroboré par TICKET-109 (`vcgencmd get_throttled = 0xe0000` le 2026-07-18 : capping fréquence + throttling + limite thermique constatés depuis le dernier boot)
      - Ventilateur déjà acheté par Thomas — **en attente qu'il soit mis en place physiquement** avant de configurer/tester quoi que ce soit côté logiciel
      - Plan retenu : essayer d'abord le connecteur PWM dédié du Pi 5 (séparé du header 40 broches GPIO, ne consomme donc aucun des GPIO déjà utilisés — boutons, I2C batterie, I2S audio). Si inaccessible une fois les HAT (ampli + batterie) empilés → repli sur un montage GPIO libre avec un transistor/MOSFET (un GPIO seul ne peut pas alimenter un moteur directement) — ⚠️ GPIO16 n'est plus disponible depuis TICKET-046 (favori), seul GPIO6 reste vraiment libre
      - Activation prévue : `dtoverlay=pwm-fan` dans `/boot/firmware/config.txt` (section `[all]`) — pas encore ajouté, contrôle automatique de la vitesse selon la température, seuils ajustables ensuite (`fan_temp0`, `fan_temp0_hyst`, etc.) si besoin de le rendre plus/moins agressif
      - ❌ **Décision de Thomas (2026-08-21) : « je ne ferai rien ».** Le ventilateur reste non monté, l'overlay ne sera pas activé. ⚠️ **Le throttling reste donc possible** : `vcgencmd get_throttled = 0xe0000` avait été relevé (TICKET-109). Sans traitement, cela reste un ralentissement thermique en usage prolongé — sans conséquence sur la lecture audio, qui ne sollicite pas le processeur. Ticket clos, pas résolu.
      - ~~Reste à faire~~ : Thomas monte le ventilateur dans le boîtier, puis on active l'overlay et on vérifie (`vcgencmd measure_temp`, `cat /sys/class/thermal/cooling_device*/type`)

---


- [x] TICKET-145 — feature/admin — Activer ou désactiver une webradio, comme un podcast (2026-08-21) — ✅ **LIVRÉ**
      - **Demande de Thomas** : « j'ai ajouté France Inter parce que je bricole seul à la maison ; quand je vais rendre la radio à mon fils je vais désactiver la possibilité qu'il la lise ». Besoin réel : couper une radio **juste avant** de rendre l'appareil.
      - 🔍 **Le point qui décide de tout** : les podcasts sont filtrés par `enabled` **à l'ingestion**, mais les radios étaient **recopiées telles quelles** vers `data.json`. Un simple drapeau en base n'aurait donc rien caché avant l'ingestion nocturne — c'est-à-dire trop tard pour l'usage visé.
      - 🛠️ **Livré** : action `toggle_radio` ; bascule dans les cartes radio de l'admin ; `add_radio` crée la radio activée ; **filtre dans `sync_radios_to_data_json()`** (effet immédiat, le kiosque suit en moins de 10 s via `data_version`) **et dans `writer.py`** — sans ce second filtre, l'ingestion nocturne annulerait le choix du parent quelques heures plus tard, panne différée donc d'autant plus déroutante.
      - ⚠️ **`enabled` absent vaut ACTIVÉE** : les cinq radios existantes n'ont pas le champ. Les faire disparaître silencieusement aurait été pire que le manque.
      - ✅ **Test de garde** : les deux filtres, plus une **vérification de cohérence sur les données réelles** — l'ensemble des radios servies dans `data.json` doit être inclus dans celui des radios activées. C'est ce contrôle-là qui attraperait une régression, les deux autres ne regardant que le code.

- [x] TICKET-144 — batterie/matériel — Après l'arrêt de l'OS, rien ne protège les cellules (2026-08-21) — ❌ **RISQUE ASSUMÉ, ticket clos le 2026-08-21**
      - **Mis au jour par TICKET-128** : on se croyait protégé depuis le 2026-08-17 par une « coupure matérielle du HAT » qui, en réalité, arme un **démarrage** au rebranchement. Elle n'a jamais rien coupé.
      - 🔴 **Le problème réel, entier** : `shutdown -h now` arrête le système, mais le HAT continue de fournir du 5 V à un Pi « halted ». Les cellules se vident donc **après** l'arrêt d'urgence, sans surveillance et sans limite de temps — c'est exactement le scénario que l'arrêt à 5 % était censé éviter.
      - ⚠️ **Ce qui rend ce ticket vicieux** : il ne se manifeste que si l'appareil reste éteint et débranché longtemps. Rien ne le signalera, et la dégradation des cellules est irréversible.
      - **Seule barrière actuelle** : la protection intégrée des cellules (coupure basse tension du HAT à ~3,15 V). Décision de Thomas du 2026-08-18 : on s'en remet à elle, l'interrupteur physique du HAT n'étant pas accessible dans le boîtier.
      - **Pistes écartées** : sortir l'interrupteur `OFF/ON` du HAT en façade du Grundig (percer la carcasse) ; relais bistable piloté par GPIO (le Pi coupe sa propre alimentation avant de s'éteindre).
      - ⏳ **Décision de Thomas (2026-08-21) : on assume.** Cohérent avec sa position du 2026-08-18 — « tant que le Pi est éteint je m'en fous du niveau dans les batteries ». La protection basse tension intégrée des cellules reste le filet, et l'appareil n'est jamais rangé longtemps.
      - 📌 **Risque résiduel, écrit noir sur blanc pour qu'il ne se redécouvre pas par surprise** : un appareil laissé éteint et débranché plusieurs semaines après un arrêt d'urgence descendra jusqu'à la coupure constructeur (~3,15 V). Rien ne le signalera. Si les cellules vieillissent anormalement vite, c'est la première piste à rouvrir.
      - 💡 **Ce que ce ticket aura servi** : révéler qu'on se croyait protégé depuis le 2026-08-17 par `arm_hat_power_cutoff()` — une fonction qui n'a jamais rien coupé (TICKET-128). Assumer un risque connu n'est pas la même chose que l'ignorer sans le savoir.


- [x] TICKET-132 — hygiène — `buttons_daemon` journalise un avertissement à chaque appui play/pause (2026-08-17) — ✅ **CORRIGÉ le 2026-08-21**
      - 🛠️ `http_get()` distingue enfin **échec de transport** (réseau, HTTP, délai → `warning` conservé) et **réponse non-JSON** (→ `debug`). La lecture du corps et son décodage sont désormais deux `try` séparés ; avant, une page HTML parfaitement valide était journalisée comme une panne.
      - ⚠️ **La moitié à ne pas perdre** : supprimer simplement l'avertissement aurait rendu une vraie panne réseau **silencieuse**. On aurait remplacé un journal illisible par un journal muet — un test vérifie explicitement que l'alerte survit à une `OSError`.
      - ✅ **Test de comportement** (`scripts/test_boutons.py`, 5 assertions) : `urlopen` est remplacé et on observe ce qui est journalisé. **Pas un `grep`** — trois gardes textuels s'étaient fait prendre le même jour à trouver leur propre documentation.
      - **Constaté** en validant TICKET-123 : chaque appui sur GPIO12 produit `WARNING Appel radio.php échoué (action=pause) : Expecting value: line 1 column 1`.
      - **L'action fonctionne pourtant parfaitement.** `radio.php` ne renvoie du JSON que pour certaines actions ; pour `pause` il exécute la commande MPD puis **retombe sur la vieille page HTML de débogage** en bas du fichier. `http_get()` tente un `json.loads()`, tombe sur du HTML, avertit, et renvoie `None`.
      - ✅ **Pré-existant, pas une régression du 2026-08-17** : `git log -- web/lecteur/radio.php` montre que le chemin `pause` n'a pas été touché, et `curl action=status` renvoie du texte MPD brut (`volume: 38`), pas du JSON.
      - ⚠️ **Pourquoi ça mérite un ticket malgré tout** : un avertissement permanent qui ne signale rien est exactement ce qui fait ignorer les vrais. Le journal de `buttons_daemon` devient illisible.
      - **Correctif envisagé** : `http_get()` ne doit avertir que sur un **vrai échec réseau ou HTTP**, pas quand la réponse n'est simplement pas du JSON.
      - ❌ **Ne PAS uniformiser les réponses de `radio.php` en JSON** : l'IHM enfant lit `action=status` en **texte MPD brut** (`sendRadio('status')` puis `parseMpd()`). Changer le format casserait le lecteur.


- [x] TICKET-128 — batterie/matériel — « Coupure matérielle » du HAT : la fonction faisait l'INVERSE de ce qu'elle annonçait (2026-08-17) — ✅ **CORRIGÉ le 2026-08-21**
      - **Découvert** dans la démo du fabricant restée au bas de `scripts/INA219.py` (sous `if __name__=='__main__':`, donc du code mort — mais instructif) : le HAT UPS expose un **registre d'extinction**. Écrire `0x55` dans le registre `0x01` du périphérique I2C `0x2d` lui demande de couper sa sortie.
      - **Pourquoi ça compte** : `shutdown -h now` arrête le système d'exploitation, mais **le HAT continue de tirer sur les cellules** — le Pi en état « halted », les LED, tout ce qui reste alimenté. Sur une décharge profonde, arrêter l'OS ne protège donc pas les cellules, ça ralentit seulement leur vidage. C'était une demi-protection, et on ne s'en était jamais aperçu parce que l'arrêt lui-même ne fonctionnait pas (défaut 1 de TICKET-121).
      - 🛠️ **Implémenté le 2026-08-17** dans `battery_watchdog.py` : `hat_present()` puis `arm_hat_power_cutoff()`, armés **après** le `sync` et **avant** le `shutdown`, dans l'ordre de la démo du fabricant.
      - **Trois garde-fous, parce que ce code coupe le courant** :
        1. **Détection obligatoire de `0x2d` avant toute écriture.** Écrire à l'aveugle sur une adresse I2C qui n'est pas celle qu'on croit peut reconfigurer un tout autre composant. Reprend la vérification `i2cdetect` du fabricant.
        2. **Échec non fatal.** HAT absent ou `i2cset` en erreur → journalisé en `ERROR`, et on laisse `shutdown` faire ce qu'il peut. Une protection partielle vaut mieux qu'un chien de garde qui plante.
        3. **`--check-hat`** : vérifie la présence du périphérique **sans rien écrire**. C'est le contrôle à risque nul, intégré au smoke test.
      - 🔴 **TOUT CE QUI PRÉCÈDE EST FAUX — corrigé le 2026-08-21.** La documentation Waveshare est explicite, et le titre de sa section suffit : **« Boot When Power Applied »**.
        > *After changing the value of the 0x01 register to 0x55, the MCU will start detecting the charging port after 30 seconds, and if power is available then pull the GPIO3 pin low to **boot** the Raspberry Pi.*

        Écrire `0x55` dans `0x2d/0x01` arme le **démarrage automatique à la remise sous tension**. C'est l'inverse d'une coupure. **Rien n'a jamais été coupé**, et le journal affirmait le contraire à chaque arrêt d'urgence.
      - 💡 **D'où venait l'erreur, et c'est ce qu'il faut retenir** : le comportement a été déduit de la **séquence d'appels** de la démo constructeur, qui écrit ce registre juste avant `poweroff`. Ça *ressemble* à un armement de coupure. **Lire un comportement dans l'ordre des appels plutôt que dans la documentation produit une explication cohérente et fausse** — et rien ne vient jamais la contredire, puisque le code « marche ».
      - 🛠️ **Corrigé** : `arm_hat_power_cutoff()` → `armer_demarrage_a_la_remise_sous_tension()`, constantes, docstrings, messages de journal et test du smoke test réécrits. **L'écriture est conservée** : elle rend la radio capable de repartir seule dès que le chargeur est rebranché, ce qui est précieux pour un appareil que l'enfant utilise seul.
      - ⚠️ L'ordre écriture → `shutdown` reste impératif, mais pour une autre raison que celle qu'on croyait : *« The Raspberry Pi needs to be turned off immediately after setting 0x01 to 0x55, otherwise the start when power applied function cannot be enabled. »*
      - 🔴 **Conséquence à ne pas manquer** : la décharge profonde après l'arrêt de l'OS **n'est toujours pas traitée**. Le HAT continue de fournir du 5 V à un Pi « halted ». La seule barrière réelle est la protection intégrée des cellules — décision de Thomas du 2026-08-18, l'interrupteur physique n'étant pas accessible. On s'est cru protégé pendant quatre jours par une fonction qui ne faisait pas ce qu'elle disait.
      - ✅ **Test de garde** : le smoke test échoue si `arm_hat_power_cutoff` réapparaît.


- [x] TICKET-143 — outillage — `recalibrer_table_batterie.py` produit une table absurde (2026-08-21) — ✅ **CORRIGÉ le 2026-08-21**
      - 🛠️ **Réécrit.** Quatre défauts corrigés, et deux autres trouvés **en le réparant** :
        1. **Cycles non clos** : il retenait le cycle le plus profond sans exiger `discharge_end`. Sur un cycle en cours, `level_end` est absent donc vaut 0 → profondeur 96 au lieu de 30.
        2. **Départ non plein** : chaque cycle était normalisé sur *sa propre* énergie délivrée. Le « 50 % restant » d'une décharge partie de 54 % ne désigne pas le même état que celui d'une décharge partie du plein. Filtre sur la **tension** de départ — pas sur le niveau enregistré, ce serait circulaire puisque c'est lui qu'on recalibre.
        3. **Normalisation sur le cycle et non sur la batterie** : trouvé après le correctif 2. Un cycle parti plein mais peu profond (2503 mAh) était comparé à une décharge complète (8892 mAh) comme s'ils couvraient la même plage. Rapportait **500 mV** de désaccord là où les courbes s'accordent à 6 mV. **Même erreur de fond que TICKET-142** : donner le même nom à deux grandeurs qui n'en sont pas une.
        4. **Verdict en millivolts** : il ne rapportait que des mV. Il affiche désormais la **sensibilité locale** (points de % par mV) et **c'est l'écart en POINTS qui décide**.
        5. **Refus trop brutal** : ma première version rejetait tout dès que la bande la plus haute échouait. Le plateau haut n'étant *jamais* reproductible, cela aurait jeté la courbe basse — celle dont dépend la sécurité. Il annonce maintenant **jusqu'où** il est fiable.
        6. **Réparation silencieuse de la monotonie** : repéré par Thomas dans la sortie. Les données mesurent 4,031 V à 85 % et **4,037 V à 80 %** — la tension *monte* quand la charge baisse, donc bruit pur. Le script forçait la monotonie (obligatoire, sinon `percent_from_voltage()` divise par zéro) **sans le dire** : on lisait une table d'apparence propre dont un palier était fabriqué, pas mesuré. Il l'annonce désormais explicitement.
        7. Chemin codé en dur, `R` estimée sur un seul saut de courant, table de comparaison recopiée au lieu d'être importée : corrigés.
      - ✅ **Résultat sur les données réelles** : verdict « fiable jusqu'à 90 % », R = **32 mΩ** (j'avais trouvé 34 à la main), et la table proposée **confirme celle déployée** à 3-5 mV près — sur **trois** cycles au lieu de deux. Confirmation indépendante, donc, obtenue en réparant l'outil qui avait failli nous égarer.
      - 📌 **Table non modifiée** : les écarts sont sous le bruit, la changer serait de l'agitation.
      - ✅ **Test de garde** (smoke test §5) : présence des deux filtres, du verdict en points, et absence de chemin absolu. Vérifié en échec sur l'ancienne version.

      - **Trouvé en s'en servant** pour TICKET-137. Le script a proposé une table plaçant **85 points de pourcentage sur 80 mV** — physiquement impossible.
      - 🔍 **Cause** : il sélectionne le cycle **le plus profond** sans exiger qu'il soit **clos**. Sur un cycle en cours, `level_end` est absent et vaut donc 0 : la profondeur est calculée à 96 points au lieu de ~30, et toute la conversion mAh/point s'effondre.
      - ⚠️ **Le vrai danger n'est pas la panne, c'est la crédibilité de la sortie** : le script n'a pas planté. Il a rendu un tableau bien formaté, avec des chiffres plausibles au premier regard, assorti de son propre avertissement rassurant (« refaire tourner après deux ou trois décharges »). **Un outil d'analyse qui se trompe sans échouer est plus dangereux qu'un outil cassé.** L'analyse du 137 a dû être refaite à la main.
      - 🐛 **Second défaut** : chemin codé en dur `/home/thomas/hechicero/data/battery_history.json` au lieu d'un chemin relatif — le script ne tourne que sur le Pi.
      - **À faire** : n'accepter que les cycles avec `discharge_end` **et** `invalid != true` ; chemin relatif ; et afficher l'écart entre cycles **en points de pourcentage** autant qu'en millivolts (leçon de TICKET-142).


- [x] TICKET-121 — sec/infra — Auditer les 8 services durcis : fichiers de travail hors `ReadWritePaths` (2026-08-04) — ✅ **CLOS le 2026-08-21**
      - ✅ **Ce qui restait ouvert — le test réel d'arrêt sous seuil — est désormais PROUVÉ DEUX FOIS en conditions réelles**, sans simulation : coupure du **2026-08-18 à 12:22:20** (fin du cycle 12, décharge 97 % → 5 %) et du **2026-08-20 à 01:29:05** (fin du cycle 18, 83 % → 5 %). Les deux ont laissé une trace propre dans `data/last_session.json`, et le Pi s'est bien éteint.
      - 💡 **Ce que ça vaut** : `battery_watchdog` était **le seul des huit services durcis dont le comportement d'arrêt n'avait jamais été prouvé** — et pour cause, deux défauts se couvraient l'un l'autre (le `sudo` cassé par `NoNewPrivileges`, et le chemin de test qui aurait dû le révéler, cassé lui aussi). La protection contre la décharge profonde n'a pas fonctionné du 2026-07-19 au 2026-08-17. Elle fonctionne maintenant, et on l'a vue fonctionner.
      - **Déclencheur** : TICKET-120 a révélé une panne **armée depuis deux semaines et totalement invisible**. Depuis le durcissement TICKET-011, `buttons_daemon` ne pouvait plus créer son tube lgpio dans `scripts/` (devenu non inscriptible) ; le service ne survivait que parce qu'un fichier créé **avant** le durcissement traînait encore et se laissait ouvrir. Sa suppression a fait tomber les boutons physiques.
      - **Hypothèse à vérifier** : les 7 autres services durcis peuvent être dans le même état — fonctionnels aujourd'hui uniquement grâce à un fichier antérieur au 2026-07-19, et condamnés au premier nettoyage ou à la première réinstallation depuis une image neuve.
      - ⚠️ **Ce n'est plus une hypothèse — confirmé une deuxième fois le 2026-08-05 (TICKET-122)** : trois unités portaient `Requires=mpd.service`, directive qui **propage l'arrêt**. Un simple redémarrage de MPD éteignait les boutons physiques et arrêtait le suivi d'écoute. Le durcissement de juillet a manifestement été appliqué **en recopiant un modèle d'unité d'un service à l'autre**, sans vérifier ce que chaque directive impliquait pour ce service précis.
      - **L'audit doit donc couvrir TOUTES les directives**, pas seulement `ReadWritePaths` : `Requires=` vs `Wants=`, `WorkingDirectory=`, `ProtectHome=`, `PrivateDevices=`.
      - **Deux pièges déjà catalogués, à chercher systématiquement** : (1) écriture d'un fichier de travail hors `ReadWritePaths`, masquée tant qu'un fichier antérieur au durcissement traîne encore (TICKET-120) ; (2) `Requires=` sur une dépendance susceptible de redémarrer légitimement (TICKET-122).
      - **C'est le pire type de bug pour ce projet** : il ne se déclare pas au durcissement, mais des semaines plus tard, sur une action sans rapport apparent. Et sur une image SD fraîchement restaurée, il se déclarerait immédiatement — donc la sauvegarde ghost ne protège pas de celui-là.
      - **Méthode proposée** (instrumenter plutôt que relire le code) : pour chacun des 8 services, déplacer temporairement ou renommer les fichiers de travail suspects, redémarrer, et vérifier que le service se recrée bien ce dont il a besoin. Alternative moins intrusive : `systemd-analyze security <service>` pour la vue d'ensemble, puis `strace -f -e trace=openat,mkfifo` au démarrage pour repérer les écritures hors `ReadWritePaths`.
      - **Services à passer en revue** : `battery_tracker`, `battery_watchdog`, `play_tracker`, `hechicero-idle`, `audio_eq_apply`, `wifi_watch`, `wifi_roam` (`buttons_daemon` est traité par TICKET-120).
      - **Attention particulière** à `audio_eq_apply` : `alsaequal` écrit des états binaires (`data/alsaequal_hp.bin`, `data/alsaequal_casque.bin`), et l'incident `mpd.socket` de TICKET-030 montre que cette chaîne est fragile.
      - **Règle à graver** ensuite dans `docs/70-SERVICES_SYSTEMD.md` : un service durci ne doit jamais écrire dans le dépôt. Répertoire de travail volatil → `RuntimeDirectory=` (systemd le crée, le rend inscriptible malgré `ProtectSystem=strict`, et le nettoie). État persistant → `data/`, déjà en `ReadWritePaths`.
      - ---
      - ## 🔍 AUDIT RÉALISÉ LE 2026-08-17 — les 9 unités, toutes les directives
      - **Méthode** : relevé exhaustif des directives des 9 `.service` du dépôt (matrice complète), puis confrontation de chaque directive à ce que le script fait réellement. Complété par `grep -n "sudo" scripts/*.py`, qui a livré le défaut le plus grave — il n'était visible ni dans les unités ni dans les journaux.
      - 🔴 **Défaut 1, le plus grave — `battery_watchdog.py` ne pouvait pas éteindre le Pi.** Ligne 83 : `run_command(["sudo", "shutdown", "-h", "now"])`. Or l'unité porte `NoNewPrivileges=true`, qui **casse `sudo`** — c'est établi dans ce projet depuis TICKET-112, où le réveil DPMS a dû passer par `runuser` pour cette raison. Le service tourne déjà en `User=root`, donc ce `sudo` n'apportait rien et ne pouvait qu'échouer.
        - **Et l'échec était silencieux** : `run_command()` (dans `battery_common.py`) avale l'exception *et* le code de retour, il ne renvoie que `stdout`. Aucune trace, aucun journal, rien.
        - **Conséquence** : la protection contre la décharge profonde **n'a jamais fonctionné depuis le durcissement du 2026-07-19**. Un mois. Avec des cellules neuves installées la veille (TICKET-126), c'est la priorité.
        - **Correctif** : appel direct à `shutdown`, plus le code de retour et `stderr` journalisés en `ERROR`. Un arrêt d'urgence qui rate sans bruit est pire que pas d'arrêt du tout : on se croit protégé.
      - 🔴 **Défaut 2 — le chemin de test était cassé aussi, et masquait le défaut 1.** Ligne 127 : `level, _ = read_level(...)` dépaquetait deux valeurs d'une fonction qui en retourne trois → `ValueError` immédiat. Or `--simulate-critical` est **le seul moyen** d'éprouver l'arrêt critique. **Les deux défauts se couvraient l'un l'autre** : le chemin réel cassé, et le chemin qui l'aurait révélé cassé également. Voilà pourquoi ce service est resté « le seul non prouvé » de TICKET-011 pendant un mois. Corrigé en `level, _, _ = read_level(...)`.
      - 🔴 **Défaut 3 — `wifi_roam.service` portait `Requires=NetworkManager.service`.** Exactement le piège de TICKET-122, sur une autre dépendance. `Requires=` propage l'arrêt : au moindre redémarrage de NetworkManager — c'est-à-dire **précisément quand le Wi-Fi va mal** — systemd arrêtait le service chargé du roaming, et ne le relançait pas. Panne purement latente, le service n'étant pas encore installé : elle se serait déclenchée à la première installation, des semaines plus tard, sans lien apparent. Corrigé en `Wants=`.
        - 📌 **Pourquoi la garde existante ne l'a pas vu** : le test de TICKET-122 ne cherchait que `^Requires=mpd`. Il est désormais **généralisé à tout `Requires=`** — aucune unité de ce projet n'a de raison légitime d'en porter un.
      - 🟡 **Défaut 4 — un test qui laissait une fausse trace.** `--simulate-critical` écrivait `last_session.json` avec `shutdown_reason: "battery_critical"`, et `web/index.php::battery_resume_payload()` n'agit que sur ce motif exact : le bureau d'admin affichait donc une « reprise après coupure batterie » qui n'avait jamais eu lieu. Le fichier est toujours écrit (c'est ce que le test doit prouver) mais avec le motif `simulation`, que l'admin ignore.
      - 🟡 **Point mineur** : `battery_watchdog.service` porte `Wants=battery_tracker.service` alors qu'il ne lit aucun fichier du tracker — il sonde l'INA219 directement. Couplage inutile et trompeur (sans danger, `Wants` ne propage pas l'arrêt). À noter : les deux services interrogent le même capteur I2C en parallèle, ce qui explique probablement la gestion de l'`errno 121` présente dans les deux.
      - ✅ **Fausse alerte instructive — `scripts/INA219.py:226` contient `os.system("sudo poweroff")`.** C'est sous `if __name__=='__main__':`, donc la démo du fabricant, jamais exécutée à l'import. Aucun risque — mais cette démo a révélé le **registre d'extinction matériel du HAT**, d'où TICKET-128.
      - ✅ **Les 6 autres unités sont saines** : `battery_tracker`, `buttons_daemon`, `play_tracker`, `audio_eq_apply`, `mpd_watchdog`, `wifi_watch`. Aucun `PrivateDevices`, aucun autre `Requires=`, `ReadWritePaths=data` cohérent avec ce que chacune écrit, `RuntimeDirectory` correct pour le tube lgpio de `buttons_daemon`. Les écritures `alsaequal` d'`audio_eq_apply` visent bien `data/*.bin`, dans le périmètre inscriptible.
      - ✅ **Tests de garde ajoutés** (§5 et §6 du smoke test) : absence de `sudo` dans le chemin d'arrêt, dépaquetage correct de `read_level()`, marquage `simulation` du fichier de reprise, alerte si un `battery_critical` traîne dans `last_session.json`, détection du HAT, et `Requires=` généralisé. **Les quatre premiers échouent sur le code d'avant** — ce sont donc de vrais tests de garde, pas des tautologies.
      - ✅ **Vérifié en réel le 2026-08-17** : `--check-hat` → `True`, `--simulate-critical` va jusqu'au bout et écrit `last_session.json`, smoke test **45 OK · 0 échec · 1 avertissement** (TICKET-125, connu).
      - ⏳ **Reste** : un unique test réel d'arrêt critique, batterie chargée et en étant présent — laisser descendre sous 15 % et vérifier que le Pi s'éteint. C'est la seule preuve qui vaille, et elle n'est pas encore faite. Ne pas laisser l'appareil à l'enfant pendant ce test.
      - 📌 **Leçon** : `grep -n "sudo" scripts/*.py` a trouvé en une seconde ce qu'un mois de fonctionnement apparemment normal avait caché. Quand un durcissement retire un privilège, chercher les endroits du code qui en avaient besoin — pas relire les unités.


- [x] TICKET-129 — infra — PHP tourne en UTC alors que le reste du projet écrit en heure locale (2026-08-17) — ✅ **CORRIGÉ le 2026-08-21**
      - 🛠️ **Livré** : `web/bootstrap.php`, inclus par les **dix** points d'entrée PHP, qui force `date_default_timezone_set('Europe/Paris')`.
      - ⚠️ **Pourquoi pas dans `php.ini`** : il vit hors du dépôt. Une carte SD fraîchement restaurée repartirait en UTC sans que rien ne le signale — la panne latente typique de la zone Z2. **Le fuseau doit voyager avec le code.**
      - 📌 **Ce défaut a mordu QUATRE fois** avant d'être traité à la racine : TICKET-102 (traceur de veille), 127 (chronologie du gel), 136 (fraîcheur batterie périmée de 2 h), 138 (`sleep_debug.log` en UTC face à `screen_dpms.log` en local, sur le même diagnostic). **Les trois premières fois, on a posé une rustine à l'endroit qui faisait mal.**
      - 💡 **La leçon** : une correction posée au point de douleur ne corrige que ce point. Le défaut restait entier partout ailleurs et revenait sous un autre visage — à chaque fois pendant une panne, c'est-à-dire au pire moment.
      - ✅ **Tests de garde** (smoke test §2) : le **fuseau effectif** est vérifié à l'exécution (`php -r`), pas la simple présence du fichier ; et chaque point d'entrée est contrôlé individuellement — un seul oubli laisserait une page en UTC, incohérence locale bien plus difficile à trouver qu'un défaut uniforme.
      - 🔗 Trois rustines locales subsistent (`web/index.php` ×2, `web/lecteur/radio.php`) : désormais redondantes mais **inoffensives** (forcer Paris sur une base déjà en Paris est neutre). Laissées en place volontairement.
      - **Constaté** deux fois, à un mois d'intervalle, sans que la cause soit traitée : le 2026-07-18 sur `hechicero_battery_stats_age_seconds` à −7185 (TICKET-017), et le 2026-08-17 en lisant `data/sleep_debug.log` pour TICKET-127 — son « 07:52:48 » correspondait en réalité à **09:52:48** sur l'horloge de la maison.
      - **Le piège** : `date()` en PHP renvoie de l'UTC (aucun `date.timezone` configuré), tandis que le shell (`data/screen_dpms.log`) et Python (`data/kiosk_freeze.log`, `datetime.now()`) écrivent en heure locale. **Deux heures d'écart entre trois journaux qu'on croise justement pendant une panne.** Chaque fois, on perd du temps ou on tire une conclusion décalée.
      - **Pourquoi ça n'a jamais été réglé** : les deux fois, le contournement était local (`date_default_timezone_set()` dans un seul fichier). Celui de `metrics.php` vient d'ailleurs de disparaître avec le fichier.
      - ✅ **Vérifié : le contrôle parental n'est PAS concerné.** `radio.php?action=parental_status` ne sert que le planning brut ; les horaires sont évalués **côté navigateur**, donc à l'heure locale de l'écran. Le risque de régression sur cette partie est nul.
      - **Piste** : `date.timezone = Europe/Paris` dans le `php.ini` d'Apache, ou un `date_default_timezone_set()` dans un fichier commun inclus par toutes les pages. La première est plus propre mais vit hors du dépôt — donc à versionner et documenter comme la conf Apache et `asound.conf` (zone Z12).
      - **À vérifier avant de livrer** : les horodatages écrits par PHP dans `data/favoris.json` (`added_at`) et `data/sleep_debug.log` deviendraient locaux. Aucun consommateur ne fait de calcul dessus, mais les valeurs déjà en base resteraient en UTC — mélange assumé, à noter dans le fichier.
      - **En attendant** : `data/kiosk_heartbeat.json` expose `ts` (epoch, sans ambiguïté), `iso` (UTC) **et** `local`. C'est le contournement propre, pas la correction.


- [x] TICKET-137 — ANALYSE PRÉPARATOIRE (2026-08-18) — conservée pour l'historique des mesures ; livraison en tête de la section Terminé
      - **`battery_common._LIPO_TABLE` est une courbe générique d'accumulateur à poche**, héritée du montage d'origine. Les cellules sont des EVE INR21700/58E (Li-ion NMC). La table n'a jamais été recalée — et **tout le pourcentage affiché du projet en dépend** : écran enfant, tableau de bord, page d'accueil, seuils d'alerte et d'arrêt.
      - 🔬 **Mesures du cycle du 2026-08-18** (`scripts/recalibrer_table_batterie.py`, 484 points) :
        - **Résistance interne : 53 mΩ** — crédible pour deux 21700 en parallèle. À −2,2 A, l'affaissement vaut **117 mV**, soit ≈ 10 points de pourcentage. **Le niveau affiché plonge donc dès que l'enfant lance un podcast, alors que rien n'a été consommé.** C'est le défaut le plus visible au quotidien.
        - **Énergie délivrée : 8892 mAh** entre 97 % et 4 %, soit ≈ 9560 mAh utiles contre 11 200 nominaux (85 % — normal pour une coupure à 3,33 V sous charge). ➡️ Pour le calcul d'autonomie temps réel, **9560 serait plus juste que 11 200**.
        - **La table actuelle sur-évalue le niveau de 8 à 10 points** dans toute la plage médiane (à 3,798 V elle annonce ~48 % là où la mesure donne 40 %).
      - ⛔ **NE PAS remplacer la table telle quelle** — trois raisons :
        1. La table proposée donne des tensions **à vide** (corrigées de l'affaissement), alors que `percent_from_voltage()` reçoit la tension **brute**. L'échanger sans ajouter la compensation `V_oc = V + |I| × R` rendrait le calcul **plus faux qu'avant**.
        2. Son point à 0 % tombe à 3,44 V — c'est le **seuil d'arrêt**, pas la cellule vide. On afficherait 0 % avec de l'énergie restante, et on perdrait l'autonomie qu'on vient de gagner.
        3. Le plateau haut est mal résolu : 15 points de pourcentage pour 10 mV entre 4,09 et 4,06 V. Un seul cycle ne suffit pas à le décrire.
      - ⏳ **Décision de Thomas (2026-08-18)** : attendre **3 ou 4 cycles**, relancer le script, vérifier que les courbes convergent. Puis livrer **ensemble** la compensation d'affaissement et la nouvelle table, avec les tests unitaires.


- [x] TICKET-142 — batterie/précision — Comptage coulométrique ancré au-dessus du plateau (2026-08-21) — ✅ **CORRIGÉ**
      - 🔴 **Ouvert parce que TICKET-137 avait introduit une régression.** Après déploiement, la nouvelle table annonçait **86 %** alors que l'intégration du courant depuis la charge pleine donnait **77,9 %**. L'ancienne table, elle, disait 75 % — juste à 2 points près.
      - 🔍 **Pourquoi l'ancienne tombait juste** : elle cumulait **deux erreurs opposées** qui s'annulaient en décharge — la table sur-évaluait de 4 à 8 points, et l'usage de la tension **brute** (au lieu de la tension à vide) sous-évaluait d'à peu près autant. Fragile et faux dès qu'on ne décharge pas, mais juste en pratique.
      - ⚠️ **MA FAUTE, et c'est la leçon la plus transférable de tout le projet : j'ai validé dans la mauvaise unité.** J'ai annoncé « 6,4 mV de désaccord médian » comme une réussite sans jamais convertir ces millivolts en **points de pourcentage**. Or :
        | bande | largeur | ce que valent 10 mV |
        |---|---|---|
        | 75-80 % | 5,0 mV | **10 points** |
        | 80-85 % | 5,0 mV | **10 points** |
        | 0-70 % | 26-66 mV | 0,8 à 1,9 point |
        6 mV d'accord est excellent à 50 % et **sans valeur à 80 %**. Mes deux cycles de calibration étaient en désaccord de ~12 **points** dans la zone plate, et je ne l'ai pas vu parce que je regardais des volts. **Le produit s'exprime en pourcents ; je l'ai validé en volts.**
      - 🛠️ **Remède — comptage ancré, et c'est l'ancrage qui le rend sûr** :
        - Sous `coulomb_anchor_percent` (70 %) : la table fait autorité. La courbe y est franche et **se recale d'elle-même**.
        - Au-dessus : intégration du courant depuis le dernier ancrage.
        - La dérive ne peut donc s'accumuler que sur **une seule traversée** de la bande haute — quelques heures — avant remise à zéro. C'est la différence avec un compteur libre, et la seule raison pour laquelle ce mécanisme est acceptable ici.
      - ⚠️ **Garde-fou central** : au-delà de **10 min** de trou entre deux relevés, l'ancrage est **abandonné** et la table reprend. Un compteur qui intègre à travers un trou dérive **sans le dire** — le pire défaut possible pour ce genre de mécanisme. `level_table` est aussi publié dans `battery_stats.json` : sans lui, une dérive serait indétectable sans refaire un cycle complet.
      - 🔗 **Ancrage sur batterie pleine** (ajouté après la première mise en service) : sans lui, un démarrage à froid en zone plate amorce le comptage sur la valeur **fausse** de la table et la conserve jusqu'au prochain passage sous 70 %. `batterie_pleine()` exige **tension ≥ 4,10 V ET |courant| ≤ 150 mA**.
        - ⚠️ **Les deux conditions sont indispensables** : les arrêts de charge anormaux du TICKET-140 ont exactement la signature d'un courant nul (0,91 mA constant pendant des heures) mais à **54 % et 70 %**. Un critère fondé sur le seul courant afficherait **100 % avec un tiers de l'énergie**. Le seuil de tension les exclut (3,80 et 3,94 V). Quatre assertions et un test du smoke test verrouillent ce point.
      - ✅ **Vérifié sur les données réelles** du 2026-08-21, rejouées à travers le mécanisme : **78 % contre 77,9 %** de référence — un dixième de point. Sur le cycle entier, écart maximal **±1,2 point**, y compris en simulant un démarrage à froid en cours de route.
      - 📌 **Limite connue** : le rattrapage d'un démarrage à froid dépend de l'ancrage sur batterie pleine. Un démarrage à 4,05 V — sous le seuil de plein, au-dessus du seuil de table — hériterait de l'erreur de la table jusqu'au prochain passage sous 70 %. Borné à un cycle, non corrigé.
      - ✅ **Tests** : 62 → **84 assertions**. Quatre tests du comptage ont **d'abord échoué**, non par erreur de code mais parce qu'ils simulaient un pas d'une heure que le garde-fou de trou rejette — ce qui a prouvé au passage que le garde-fou mord. Smoke test §5 : mécanisme branché, ancrage persisté, invalidation sur trou, capacité effective non nulle.
      - 📌 **Le watchdog n'utilise PAS le comptage** (il ne transmet pas d'ancrage) et reçoit le niveau de la table. Sans conséquence : il ne décide qu'en bas de plage, précisément là où la table est fiable.

- [x] TICKET-137 + TICKET-139 — batterie/précision — Table mesurée, compensation d'affaissement et lissage (2026-08-21) — ✅ **CORRIGÉ**
      - **Condition posée par Thomas remplie** : après plusieurs cycles, les courbes convergent. Deux décharges profondes indépendantes (cycles 12 du 18/08 et 18 du 19/08) ont délivré **8892 et 8896 mAh** — à 0,05 % près — et leurs courbes tension→charge s'accordent à **6,4 mV** après compensation (12,0 mV sans).
      - 📉 **Ampleur du défaut corrigé** : l'ancienne table, courbe générique jamais recalée, **sur-évaluait de 4 à 8 points** sur presque toute la plage et annonçait encore **7 % à la coupure réelle**.
      - 🛠️ **Livré ensemble, et c'est indispensable** :
        - `tension_a_vide(V, I, R)` — la table donne des tensions **à vide**, l'INA219 mesure **sous charge**. À −2,2 A l'écart vaut 75 mV, soit ~8 points : c'est ce qui faisait plonger la jauge dès qu'un podcast démarrait.
        - `_LIPO_TABLE` remplacée par la courbe mesurée.
        - `mediane()` + rafale de 5 lectures dans `read_sensor_snapshot()`. **Médiane et non moyenne** : une seule valeur aberrante déplace une moyenne, il en faut la moitié pour déplacer une médiane. C'est le creux isolé à −210 mA qui faisait annoncer « charge arrêtée ».
      - ⚠️ **Pourquoi le 139 devait précéder le 137** : la table mesurée étale **20 points de pourcentage sur 40 mV** entre 75 et 95 % (contre 60 mV avant) — le plateau de la chimie Li-ion. Elle est donc **~7× plus sensible au bruit**. Livrer la table sans le lissage aurait aggravé le sautillement qu'on cherchait à corriger.
      - ⚠️ **Changement de sens silencieux du seuil** : « 5 % » désigne maintenant 3,458 V à vide au lieu de 3,350 V, soit **108 mV plus tôt** et ~14 min d'autonomie en moins. **Décision de Thomas : garder 5 %** — ces minutes sont dans la zone où la tension s'effondre et où les cellules souffrent.
      - 🔍 **Défaut trouvé en chemin dans `recalibrer_table_batterie.py`** : il sélectionnait le cycle **en cours**, dont `level_end` est absent, donc profondeur calculée à 96 points au lieu de ~30 — il proposait une table absurde (85 points sur 80 mV). Sa sortie n'était pas exploitable ; l'analyse a été refaite par intégration du courant sur les cycles clos. Le script code aussi en dur `/home/thomas/hechicero` au lieu d'un chemin relatif. **Non corrigé — à reprendre.**
      - 📌 **Limites assumées** : R = 34 mΩ est le meilleur accord entre cycles, mais le minimum est **plat de 20 à 60 mΩ** (le courant de décharge varie trop peu pour contraindre R). Et le haut de courbe reste imprécis — seul un comptage coulométrique y répondrait, écarté pour l'instant.
      - ✅ **Tests** : `test_batterie.py` passe de 44 à **62 assertions**. **4 des 5 clés vérifiées en échec sur l'ancienne table** (la 5ᵉ est un invariant de structure, annoté comme tel). Smoke test §5 : couplage table/compensation, résistance non nulle, rafale active.

- [x] TICKET-139 — mesure/batterie — La charge plafonne vers 60 % : vraie asymptote ou charge annulée par la consommation ? (2026-08-19) — ✅ **CORRIGÉ** (voir TICKET-137+139 ci-dessus)
      - **Signalé par Thomas**, après la refonte du suivi (TICKET-133) : « le dashboard indique que la charge se stoppe mais que la batterie est à 60 % ».
      - 📸 **Instantané pris le 2026-08-19 à 08:26** (`data/battery_stats.json`) :
        ```
        niveau 63 %  ·  3,896 V  ·  +318,82 mA  ·  0,43 W
        charging: true, en charge depuis 07:14:39 (72 min)
        MPD : webradio EN LECTURE (France Inter)  ·  écran allumé
        estimated_charge_time_minutes_live : 1092  ← 18 heures
        cycles_recorded: 2, model_confidence: "low"
        ```
      - ❌ **Ma première analyse était fausse, et Thomas a eu raison d'en douter.** J'avais conclu d'un instantané unique que la consommation de la webradio annulait la charge. **Un seul point, pris au creux d'un signal qui oscille de −210 à +1459 mA.** L'historique complet dément :
        ```
        points en charge, tous cycles :
        webradio   n=136   médiane  +886 mA   (min −173, max +1459)
        idle       n=116   médiane +1059 mA   (min  −60, max +1518)
        ```
        La webradio ne coûte que **173 mA de médiane** — très loin des ~800 mA qu'exigerait mon explication. ⚠️ **Construire une histoire cohérente à partir d'un échantillon d'un signal bruité produit une certitude, pas une connaissance.**
      - 🔍 **Cause racine réelle : aucun lissage, nulle part.** L'état charge/décharge **et** le niveau sont calculés chacun sur un **échantillon instantané**. Séquence mesurée le 2026-08-19 :
        ```
        08:29:41   61 %   3,880 V   −210 mA   charging: FALSE   webradio
        08:30:41   65 %   3,912 V   +224 mA   charging: true    webradio
        08:31:41   69 %   3,940 V   +992 mA   charging: true    webradio  ← radio toujours allumée
        08:33:41   70 %   3,952 V  +1111 mA   charging: true    idle
        ```
        1. **L'état bascule sur un seul échantillon.** À 08:29 un creux passager à −210 mA franchit la bande morte de 200 mA (TICKET-133) → le tableau de bord annonce « charge arrêtée ». **C'est exactement ce que Thomas a signalé.** Ni plateau, ni arrêt : un artefact d'un point.
        2. **Le niveau saute de 61 à 70 % en quatre minutes**, parce que 72 mV valent 9 points dans cette zone de la table. **Il n'y a donc aucune asymptote à 60 %** — le palier n'existe pas.
      - 🛠️ **À faire — lisser avant de décider** (rien n'est écrit) :
        - Médiane glissante sur N échantillons pour le **courant** avant de trancher charge/décharge. La bande morte seule ne protège pas d'un signal dont l'écart-type dépasse la bande.
        - Même traitement pour la **tension** avant conversion en pourcentage — sinon le niveau affiché restera nerveux même avec une table recalée.
        - Test de garde : injecter une série bruitée avec un creux isolé et vérifier que l'état **ne bascule pas**.
      - ⏳ **Décision de Thomas (2026-08-19)** : reparamétrer proprement la gestion de l'énergie le soir. ✅ **Le test « charge sans radio » est inutile** — l'écart entre modes (173 mA) est noyé dans un bruit de ±1400 mA et demanderait des heures pour être extrait.

- [x] TICKET-141 — mesure/batterie — L'enregistreur devient aveugle pendant les plateaux, et ignore le courant (2026-08-19) — ✅ **CORRIGÉ**
      - 🛠️ **Livré** : cadence plancher `RECORD_FLOOR_SECONDS = 300` (un point au moins toutes les 5 min) · le courant devient critère (`CURRENT_DELTA_MA = 300`, plus le franchissement de la bande morte `CURRENT_ZERO_BAND_MA = 50` — « le courant a cessé de couler » est un événement même à niveau constant) · purge `RETENTION_FULL_DAYS = 30` puis 1 point/h · historique écrit **seulement s'il a changé**.
      - 🔒 **Piège évité, zone Z8** : le second élément du tuple pilote `close_discharge()` / `new_cycle()`. Y ajouter la cadence plancher aurait fabriqué **un faux cycle toutes les 5 minutes**. Il reste strictement `transition or state_changed`, et **trois assertions le vérifient**.
      - 💾 **Contrepartie traitée** : `collect_once()` réécrivait l'historique entier toutes les 60 s — **283 Mo/jour** sur la carte SD pour un fichier le plus souvent inchangé, et **aucune purge n'existait**. Livrer la cadence seule aurait transformé un gain de diagnostic en usure de carte SD (fichier de 22 Mo au bout d'un an, réécrit en continu).
      - ⏱️ **Purge dans le tracker, pas dans un cron** : une purge confiée à un service tiers finit par ne plus tourner sans que personne ne le remarque, et on ne le découvre qu'une fois la carte usée.
      - ✅ **Tests** : `test_batterie.py` passe de 24 à **44 assertions**. Les 4 clés ont été **rejouées contre l'ancienne implémentation et échouent bien** — mesure de l'aveuglement : sur un plateau de 30 min, l'ancien code retenait **0 point**. Smoke test §5 : présence des trois constantes, appel de `purge_history()`, écriture conditionnelle.
      - 📌 **Débloque TICKET-140** : l'arrêt de charge nocturne redevient observable au prochain épisode.
      - **Signalé par Thomas** : « je trouve que le relevé de points de charge est trompeur, on voit encore une sorte de trou dans la charge ». Ce n'est pas un défaut de rendu : **il n'y a réellement aucun point à enregistrer**.
      - 🔍 **Cause** — `should_record_point()` n'écrit un point que sur : bascule `charging`, changement de `mpd_mode`, variation de niveau **≥ 2 points**, ou changement de `status`. Le tracker échantillonne pourtant **toutes les 60 s** (`battery_check_interval_seconds`) et **jette tout le reste**. Pendant un plateau, aucun critère ne se déclenche → trou.
      - 📊 **Trous du 2026-08-19** : `14:39 → 15:17` (38 min) · `15:17 → 17:44` (**147 min**, la terminaison de charge s'y produit sans un seul point) · `17:59 → 18:48` (49 min).
      - 🔴 **Défaut central : le courant n'est pas un critère d'enregistrement.** Ni sa valeur, ni sa variation. La nuit du 18 au 19, il s'est effondré de **+1111 à −60 mA** — le phénomène entier du TICKET-140 — et cela n'a été capté que **par accident**, parce que le niveau avait bougé de 61 à 54 au même moment. D'où **3 points en 6 h 53**.
      - ⚠️ **L'ironie à retenir** : l'enregistreur cesse d'écrire exactement quand le système fait la chose qu'on cherche à étudier (tenir un plateau). On a ensuite passé une journée à s'étonner que les plateaux soient indiagnosticables. **Un échantillonnage déclenché par le changement ne peut pas documenter une absence de changement.**
      - 🛠️ **Ce qui était à faire, et qui est fait** :
        1. **Cadence plancher garantie** : un point au moins toutes les 5 min quoi qu'il arrive, en plus des déclencheurs événementiels. Coût : 288 points/jour, négligeable.
        2. **Ajouter le courant aux critères** : variation ≥ ~300 mA, et franchissement de zéro.
        3. Test de garde : simuler un plateau de 30 min à niveau constant et vérifier qu'il produit ≥ 6 points.
      - 🔗 Distinct du TICKET-139 (lissage des valeurs **affichées**) : ici c'est la **politique d'enregistrement** qui perd l'information avant tout affichage.

- [x] TICKET-138 — bug/veille — Deux minuteries de veille désaccordées : dalle allumée, page noire pendant 9 minutes (2026-08-19) — ✅ **CORRIGÉ le 2026-08-21**
      - 🛠️ **Livré** : l'overlay JS dérive de `screen_off_delay` au lieu de `sleep_delay`. **Une seule source de vérité** — aligner les deux nombres dans `config.json` n'aurait pas suffi, deux réglages libres se désaccordent au premier passage dans l'admin. `sleep_delay` devient un simple repli de compatibilité.
      - 🔴 **Effet de bord identifié et verrouillé** : le délai de veille passe de 60 s à **600 s**, alors que toutes les boucles périodiques de l'IHM tournent entre 100 ms et 60 s. Le garde `changed` de `applySleepConfig` — jusqu'ici une optimisation — devient la **seule** protection contre le retour de TICKET-102 (veille qui ne se déclenche jamais). La marge est passée de ×5 en notre faveur à ÷10 en notre défaveur. **Deux tests de garde** ajoutés au smoke test §3, dont un vérifié en échec sur l'ancienne ligne.
      - 📌 **Le registre de non-régression affirmait que ce comportement était « normal, pas un bug »** — c'est ce qui l'a classé sans suite pendant des semaines. Corrigé dans `75-NON_REGRESSION.md`.
      - ⏳ **Reste à observer en réel** : qu'une veille se déclenche bien au bout de 600 s d'inactivité, et que dalle et overlay s'éteignent ensemble.
      - **Signalé par Thomas** : « j'ai appuyé sur le bouton physique play et la dalle s'est allumée mais l'écran est noir ». Symptôme rapporté plusieurs fois depuis des semaines, jusqu'ici attribué à un gel du kiosque (TICKET-127).
      - ❌ **Ce n'était pas un gel.** Le battement de cœur posé au TICKET-127 a tranché en trente secondes : 2 886 battements ininterrompus, dernier battement à 5 s, `kiosk_freeze.log` muet depuis le 2026-08-17. **La page exécutait du JavaScript pendant tout l'épisode.** L'instrumentation a servi à innocenter une piste, ce qui est exactement son rôle.
      - 🔍 **Cause racine** — `web/lecteur/config.json` porte **deux délais de veille indépendants, sans aucun lien entre eux** :
        - `"sleep_delay": 60` → l'overlay `#sleep-overlay` du navigateur (écran `retro_clock` : fond `#070503`, horloge en `rgba(210,140,12,.35)`)
        - `"screen_off_delay": 600` → l'extinction de la dalle par `swayidle` via `screen_dpms.sh`
      - ➡️ Entre les deux il existe une fenêtre de **540 secondes** où la dalle est allumée et la page affiche un écran quasi noir. **En plein jour l'horloge rétro est illisible** : l'appareil paraît en panne alors que tout fonctionne. C'est le symptôme, entier.
      - 📊 **Chronologie du 2026-08-19** (heure locale ; `sleep_debug.log` est en UTC — TICKET-129 mord une **quatrième** fois) :
        ```
        07:19:21  swayidle éteint la dalle
        08:00:38  appui play → dalle rallumée (rebond de mode) + wake_up keydown was_active=true
                  ↑ la chaîne GPIO → wtype → navigateur fonctionne parfaitement
        08:00:56  click, click, keydown — Thomas manipule l'écran
        08:01:57  activate_sleep — l'overlay revient, 60 s après la dernière interaction
        08:10:57  swayidle éteint la dalle — soit 540 s d'écran noir sur dalle allumée
        08:20:47  appui play → wake_up keydown was_active=true, overlay levé, mpd=play
        ```
      - ⚠️ **Pourquoi ça a résisté si longtemps** : rien n'était cassé. Chaque moitié faisait exactement son travail. Cherchée comme une panne, la cause était introuvable — parce que c'est un **désaccord de configuration**, pas un défaut de code. Le réflexe « quel composant a échoué ? » est aveugle à ce genre de bug.
      - ⏳ **Décision de Thomas (2026-08-19)** : **une seule veille à 600 s** — overlay et dalle s'éteignent au même instant. Plus jamais de dalle allumée sur page noire, et la radio reste lisible 10 minutes après le dernier appui (utile quand l'enfant écoute sans toucher l'écran).
      - 🛠️ **À faire** (rien n'est encore écrit) :
        1. Faire dériver les deux délais d'une **source unique**. Ne pas se contenter d'aligner les deux nombres dans le fichier : deux réglages libres se désaccorderont à nouveau au premier passage dans l'admin. Soit `sleep_delay` disparaît au profit de `screen_off_delay`, soit l'admin les lie explicitement.
        2. **Interdire par construction** `sleep_delay < screen_off_delay` (la combinaison qui produit le bug), avec un test de garde au smoke test.
        3. Vérifier le comportement de l'overlay **pendant la lecture** : aujourd'hui il s'active même si MPD joue. À confirmer avec Thomas — c'est peut-être souhaitable le soir.
      - 🧹 **Second défaut, trouvé en chemin** : `data/sleep_debug.log` pèse **8,2 Mo / 87 698 lignes** et contient **92 601 octets nuls** — écritures concurrentes depuis PHP sans verrou (`grep` le rejette comme binaire). C'était un traceur temporaire du TICKET-102, jamais retiré ni borné. **Décision de Thomas : le garder** — il vient de résoudre ce bug — mais **sous `flock` et avec rotation à 2 Mo**.

- [x] TICKET-136 — bug/affichage — Le bandeau batterie affichait 50 jours de données figées (2026-08-18) — ✅ **CORRIGÉ**
      - **Signalé par Thomas** sur capture de la page d'accueil admin : 91 %, 4,092 V, 49 mA. Ces valeurs venaient de `web/status.json`, dont l'horodatage était **`ts: 1782657996` — le 2026-06-28**.
      - 🔍 **Cause** : `web/status.json` était écrit par `scripts/get_status.py`, **supprimé en session 11** (`05-POWER_MANAGEMENT.md` le note noir sur blanc : « ne plus utiliser »). Le fichier est resté, plus personne ne l'écrivait, et deux consommateurs continuaient de le lire.
      - ⚠️ **Cinquante jours sans que personne le voie, et c'est ça le vrai enseignement** : les valeurs restaient **plausibles**. Un pourcentage de 91 %, une tension de 4,09 V, un courant de 49 mA — rien qui saute aux yeux. Une donnée absurde se repère ; une donnée périmée mais crédible, non.
      - 🔴 **L'écran de l'enfant était touché aussi.** `fetchBatteryStats()` retombait sur `fetchBatteryFromStatus()` (lignes 1384 et 1387) dès que l'appel principal échouait : l'enfant voyait alors les 91 % de juin. **Un repli vers des données périmées masque la panne au lieu de la montrer.** Supprimé — l'indicateur disparaît quand la mesure est indisponible, et l'absence est un signal honnête.
      - 🛠️ **Corrections livrées** :
        - `web/index.php` action `status` lit désormais `data/battery_stats.json` (réécrit toutes les 60 s), plus le fichier mort.
        - **Fraîcheur exposée** (`age_seconds`, `stale`) : au-delà de 3 min sans mise à jour, le panneau se grise et annonce depuis quand. C'est ce qui rend une donnée figée visible.
        - **Signe du courant restauré** : le bandeau affichait « 49 mA » sans dire s'il entrait ou sortait, alors que depuis TICKET-133 c'est le signe qui décide de l'état.
        - **Autonomie estimée ajoutée**, en heures/minutes — et **masquée pendant la charge** : le tracker conserve la dernière moyenne de cycles et la renvoyait telle quelle, ce qui affichait « 39 min » en pleine recharge. Un chiffre juste dans le mauvais contexte trompe plus qu'une absence.
        - ⏰ Le calcul d'âge force le fuseau `Europe/Paris` : `last_updated` est écrit par Python en heure locale, PHP tourne en UTC. Sans ça, tout aurait paru périmé de deux heures en permanence. **TICKET-129 mord une troisième fois.**
      - 📌 **Défaut trouvé dans mon propre test de garde** : il cherchait la chaîne `status.json` n'importe où dans le fichier, donc **y compris dans le commentaire qui documente le correctif**. Il échouait sur sa propre explication. Corrigé pour ne matcher qu'un `fetch(...)` — la vraie signature du défaut. Un garde-fou qui crie au loup sur sa documentation fait douter de toute la suite.
      - ✅ **Tests de garde** (smoke test §3) : plus de `fetch` vers le fichier mort côté enfant, bandeau admin alimenté par `battery_stats.json`, et fraîcheur exposée. **61 contrôles, 0 échec.**
      - 🗑️ `web/status.json` supprimé.

- [x] TICKET-134 — mesure/batterie — Test de décharge profonde : jusqu'où descendre avant que le Pi décroche (2026-08-17) — ✅ **FAIT le 2026-08-18**
      - **Demande de Thomas** : un cycle unique, seuils au plus bas, quitte à subir une coupure non maîtrisée du Pi — risque carte SD accepté et couvert par une sauvegarde complète. **Contrainte de temps** : charge + décharge ≈ 12 h, donc un seul essai, lancé le soir.
      - ⛔ **Non négociable** : ne pas dégrader les cellules. Elles ont un jour.
      - **Pourquoi 5 % et pas plus bas** — table LiPo du projet, tensions mesurées **sous charge** : 15 % = 3,49 V · 10 % = 3,44 V · **5 % = 3,35 V** · 0 % = 3,00 V. Le constructeur du HAT coupe à **3,15 V**. En dessous de 5 %, l'interpolation devient hasardeuse (3 % ≈ 3,21 V) et on approche vraiment le seuil constructeur.
      - ⚠️ **Nuance apportée par les caractéristiques réelles des cellules** (2 × EVE INR21700/58E) : à 3 A de consommation totale on tire 1,5 A par cellule, soit ≈ **0,27 C** — un régime très doux. L'affaissement sous charge sera donc **bien plus faible** qu'avec les anciennes 18650. Conséquence : le pourcentage affiché sera **plus proche de l'état de charge réel**, donc **moins de marge cachée** qu'avec l'ancien pack. La marge reste réelle (3,35 V contre un plancher pratique de 3,0 V), mais plus mince que ce qu'un raisonnement sur les anciennes cellules laissait croire.
      - 🛠️ **Outillage livré** :
        - `scripts/test_decharge_profonde.sh armer|restaurer|etat` — abaisse le seuil à 5 %, resserre le relevé à 15 s et le watchdog à 10 s, sauvegarde `config.json` avant, refuse de s'armer deux fois. **`restaurer` est impératif après le test.**
        - `battery_tracker` enregistre désormais **tous** les échantillons sous 20 % (`VERBOSE_BELOW_LEVEL`) : on ignore la forme du coude de fin de décharge sur ces cellules, et cette courbe ne se rejoue pas sans refaire 12 h.
      - ⚠️ **Ce qu'on ne touche PAS** : la protection matérielle du HAT (registre `0x2d` et circuit de protection du pack). Non désactivable depuis le Pi, et c'est tant mieux — c'est le vrai filet de sécurité des cellules.
      - **Les deux issues sont informatives** : si le watchdog coupe à 5 %, on lit la tension exacte et la marge restante ; si le Pi décroche avant, le dernier point donne la tension de décrochage réelle du HAT — la valeur cherchée.
      - 📌 **Ce que ce test ne dira PAS** : la limite chimique des cellules. Il mesure la limite de l'**électronique du HAT**. La limite des cellules se connaît par la fiche technique (2,5 V coupure, 3,0 V plancher pratique), pas par l'expérience.
      - ⏳ **À relever au réveil** : `journalctl -u battery_watchdog`, les 25 derniers points de `battery_history.json` (avec `voltage_v`), puis **`restaurer`**.

- [x] TICKET-131 — bug — Les épisodes des « Explorateurs de l'Univers » s'affichaient à l'envers (2026-08-17) — ✅ **CORRIGÉ**
      - **Signalé par le petit** : « les épisodes des Explorateurs de l'Univers, ils sont à l'envers ». Il avait raison, et **le tri n'était pas en cause**.
      - 🔍 **La cause est dans les données.** L'éditeur a téléversé les neuf épisodes le même soir, à **une minute d'écart, en commençant par le dernier** : épisode 8 à 19:59, épisode 7 à 20:00, … épisode 1 à 20:06, la présentation à 20:07. Les dates de publication sont donc **exactement l'inverse de l'ordre narratif**, et notre tri chronologique croissant — correct en soi — rendait 8, 7, 6 … 1.
      - Même famille que le bug TINA (republication en lot avec dates incohérentes), mais le correctif TINA ne s'applique qu'**à l'intérieur d'une saison détectée**, et `_SEASON_EP_RE` attend le motif « Nom N/M : ». Ici les titres disent « Episode 8 : » ou « Episode 7. » — aucune saison détectée, donc repli sur la date.
      - 🛠️ **Correctif — `parser.trier_episodes()`**, avec **trois conditions cumulatives** avant de faire confiance aux numéros de titre plutôt qu'aux dates :
        1. **Aucune saison détectée** — sinon le tri à deux niveaux de TICKET-104 est déjà le bon, on n'y touche pas.
        2. **Numéros UNIQUES sur tout le podcast.** ⚠️ **C'est la condition qui a sauvé Olma** : ses titres sont aussi « Episode N. … », mais la numérotation **redémarre** à chaque série (1→32, puis 1→20). Trier par numéro l'aurait entrelacé — une régression sur 55 épisodes pour en réparer 9. Trouvé en relisant les données avant d'écrire le code, pas après.
        3. **Au moins deux tiers des épisodes numérotés** — un seul titre « Episode 1 » ne doit pas faire basculer tout l'ordre d'affichage.
      - 🧹 **Cause racine annexe corrigée — le tri était DUPLIQUÉ** entre `parse_rss()` et `merge_episodes()`. Deux copies de la même logique, donc deux occasions de diverger, et un ordre potentiellement différent selon qu'on recharge le flux ou qu'on fusionne l'historique (TICKET-107). C'est désormais **une seule fonction appelée des deux côtés**.
      - ✅ **PREMIERS TESTS UNITAIRES DU PROJET** — `scripts/rss_ingest/test_tri_episodes.py`, **13 assertions**, sans fichier ni réseau. Ils prouvent dans le même mouvement que le cas cassé est réparé **et** que les cas qui marchaient n'ont pas bougé : Olma (numérotation qui redémarre) et Tina (saisons) sont des cas de non-régression **réels, pas inventés**. Intégrés au smoke test §9.
      - 📌 **Leçon** : un correctif qui touche l'ordre d'affichage de **tous** les podcasts ne se valide pas à l'œil sur celui qui était cassé. La condition d'unicité n'est venue qu'en allant relire les titres d'un autre podcast.
      - ✅ **Clos le 2026-08-17 par Thomas.**

- [x] TICKET-123 — bug — L'écran ne s'éteint plus après un réveil non tactile (2026-08-05) — ✅ **CORRIGÉ ET VALIDÉ le 2026-08-17**
      - ═══ RÉSOLUTION (2026-08-17) ═══
      - 🔬 **Bug d'abord CONFIRMÉ par la mesure**, après un premier protocole raté. Le test valide : laisser **swayidle lui-même** éteindre l'écran (pas un `screen_dpms.sh off` manuel, qui éteint la dalle dans son dos sans toucher à son compteur), puis réveiller **par le bouton antenne seul**, sans jamais toucher la dalle. Résultat : **25 minutes, aucun `off`**. swayidle n'a jamais réarmé.
        - ❌ **Le premier protocole ne prouvait rien** : un `off` manuel laisse swayidle en pleine course, donc l'extinction observée 54 s plus tard était simplement son compte à rebours arrivant à échéance — elle serait survenue de toute façon. Vérifié : `ps -o etime -C swayidle` montrait 7 h 10 sans relance, donc pas de redémarrage non plus.
      - 🛠️ **Correctif — `buttons_daemon.signaler_activite()`** : émission d'une **vraie frappe clavier virtuelle** (`wtype -k Shift_L`, protocole Wayland) à **tout front descendant, sur n'importe quelle broche**. Le compositeur la compte comme de l'activité, swayidle sort de son état « déjà expiré » et réarme son compte à rebours.
        - **Placé dans la boucle de polling, pas dans les handlers** : un seul point couvre les neuf boutons — y compris les « tap ou maintien » dispatchés à part — et tout bouton ajouté plus tard en bénéficiera sans qu'on y pense. C'est exactement l'oubli qui a créé ce bug : TICKET-112 a câblé un réveil de dalle sans signaler l'activité.
        - **`Shift_L`, modificatrice seule** : n'insère aucun caractère, ne déclenche aucun clic, donc aucun effet possible sur l'IHM enfant. On signale une présence, on ne pilote pas la page.
        - **Étranglé à 5 s**, thread détaché, best-effort : un rebond GPIO ne déclenche pas de rafale de sous-processus, et la boucle GPIO n'est jamais ralentie. `wtype` absent → un avertissement une seule fois, le daemon continue.
      - ✅ **Validé en réel le 2026-08-17** : `wtype -k Shift_L` a immédiatement produit `17:08:29 [sh<-swayidle] on` dans `data/screen_dpms.log` — la preuve que swayidle a vu l'activité et lancé son `resume`. Puis `buttons_daemon` redémarré, appui sur GPIO12 confirmé au journal, action MPD exécutée. Smoke test **56 OK · 0 échec**.
      - 💡 **MÉTHODE DE TEST À RÉUTILISER — 5 secondes au lieu de 25 minutes.** Quand swayidle est **déjà bloqué en état expiré**, le premier vrai événement d'entrée déclenche son `resume` **immédiatement**, donc une ligne `[sh<-swayidle] on` dans le journal en une seconde. **Cette ligne suffit à prouver le déblocage** — inutile d'attendre l'extinction suivante. J'ai fait attendre Thomas 25 minutes pour rien avant de m'en apercevoir.
        - ⚠️ Piège de syntaxe rencontré : `wtype -k shift` → `Unknown key`. Les noms de touches sont des **keysyms XKB**, sensibles à la casse : `Shift_L`.
      - 🎁 **Bénéfice secondaire, au moins aussi important au quotidien** : un enfant qui n'utilise **que** les boutons physiques voyait son écran s'éteindre au bout de 20 minutes alors qu'il était en train de s'en servir. Ce n'est plus le cas.
      - 🛡️ **Tests de garde** (smoke test §5) : présence de `signaler_activite()` dans `buttons_daemon.py`, et exécutable `wtype` installé. Les deux en **`fail`** — sans l'un ou l'autre, le cycle de veille se refige en silence. Zone Z4 du registre complétée.
      - ⚠️ **Prérequis d'installation** : `sudo apt install wtype`. À ne pas oublier sur une image SD fraîche — c'est pour ça que le smoke test le vérifie.
      - ❓ **Reste sans réponse, et le restera** : qui a rallumé l'écran le 2026-08-05 à 14:24, maison vide. L'événement précède l'instrumentation des appelants (posée le soir même). Sans importance désormais : le correctif traite les deux causes possibles, bouton parasite comme toucher fantôme.
      - ═══ DIAGNOSTIC D'ORIGINE (2026-08-05) ═══
      - **Symptôme** : l'écran est resté allumé tout un après-midi, maison vide. Thomas : « c'est incompréhensible ».
      - 🔍 **Cause établie, et démontrée** : `swayidle` n'observe **que les entrées Wayland**. Les 9 boutons GPIO sont lus par `buttons_daemon`, un processus Python — **le compositeur ne les voit jamais**. Or le cycle de `swayidle` est : compter 1200 s → lancer `off` → **rester en état « déjà expiré »** jusqu'à une entrée réelle → lancer `resume` → et seulement alors réarmer.
      - **Conséquence** : réveiller la dalle autrement que par le tactile (bouton GPIO23, TICKET-112) laisse `swayidle` bloqué. Il ne réarmera jamais son compte à rebours, et **l'écran reste allumé indéfiniment** jusqu'au prochain vrai toucher.
      - **Preuve** (`data/screen_dpms.log`, 2026-08-05) : trois `on` à 18:34:53, 18:38:16 et 18:41:10 n'ont **pas** empêché l'extinction programmée de 18:52:15. Ces appels ne réarment donc rien. Et le trou : `off` à 13:50:28, `on` à 14:24:11 maison vide, puis **3 h 24 sans rien** jusqu'au retour de Thomas.
      - ❌ **Hypothèses éliminées par la mesure** : `swayidle` relancé en boucle par `idle_screen.sh` (il tourne sans interruption depuis 09:41:08, soit 42 s après le boot) · clause `resume` manquante (`ps -ww` confirme la commande complète) · réglages incorrects (`screen_off_enabled: True`, `screen_off_delay: 1200`).
      - ❌ **Pas une régression de TICKET-115** : ni `idle_screen.sh` ni les délais n'ont été touchés, et le chemin `off` est resté identique. Le mécanisme date de TICKET-112 (2026-07-24), quand GPIO23 a été câblé sur le réveil de l'écran.
      - 🛠️ **Instrumentation posée** (`scripts/screen_dpms.sh`, md5 `270794ad…`) : chaque ligne de journal préfixe désormais l'appelant sur deux niveaux, `[père<-aïeul]` — le parent direct est souvent un simple `sh -c`, le vrai demandeur est au-dessus. Vérifié en bac à sable : `[sh<-swayidle]`, `[python3<-…]`, `[bash<-sshd-session]` sont bien distingués.
      - ⏳ **Question ouverte, bloquante pour le correctif** : **qui a rallumé l'écran à 14:24 alors que la maison était vide ?** Deux appels à 3 s d'intervalle. Si la trace dit `buttons_daemon`, c'est un déclenchement parasite du bouton antenne ; si elle dit `swayidle`, c'est un vrai événement d'entrée survenu tout seul, et les touchers fantômes du panneau `wch.cn` (TICKET-098) reviennent en tête. Les deux appellent des correctifs sans rapport.
      - 💡 **Correctif de fond envisagé** (à valider une fois la trace obtenue) : faire émettre à `buttons_daemon` un **événement d'entrée virtuel via `uinput`** à chaque appui. Le réveil de la dalle deviendrait un effet de bord naturel, `swayidle` verrait l'activité comme pour un toucher, et le compteur se réarmerait seul. Bénéfice secondaire réel : aujourd'hui, un enfant qui n'utilise **que** les boutons physiques voit son écran s'éteindre au bout de 20 min alors qu'il est en train de s'en servir.

- [x] TICKET-125 — audio/infra — Le périphérique ALSA par défaut est référencé par numéro de carte (2026-08-05) — ✅ **CLOS le 2026-08-17**
      - **Trouvé** par la nouvelle garde Z6 du smoke test, alors qu'on cherchait autre chose.
      - `/etc/asound.conf` contient `pcm.!default { slave.pcm "hw:2,0" }` et `ctl.!default { card 2 }`. **Les numéros de carte ALSA dérivent d'un boot à l'autre** — vécu le 2026-07-03, cartes 2 et 3 inversées.
      - **MPD n'est pas concerné** : ses deux sorties pointent vers les plugins `eqhp`/`eqcasque`, qui nomment correctement les cartes (`plughw:CARD=sndrpihifiberry`, `plughw:CARD=Audio`). C'est d'ailleurs pour ça que le piège est passé inaperçu.
      - ~~**Ce qui est concerné** : tout ce qui n'indique pas `-D` — **son de démarrage**, `aplay`, Chromium.~~ ❌ **FAUX, corrigé le 2026-08-17.**
      - **Rien n'est cassé aujourd'hui**, d'où l'avertissement et non l'échec dans le smoke test. Mais c'est un bug latent typique du projet : invisible jusqu'au jour où l'ordre des cartes change, ou sur une image SD fraîchement restaurée.
      - ---
      - ## ✅ TRAITÉ LE 2026-08-17 — et l'avertissement disait deux choses fausses
      - 🔴 **Le message du test de garde conseillait la MAUVAISE carte.** Il disait « Remplacer par `CARD=sndrpihifiberry` ». Or le relevé de `/proc/asound/cards` donne : `0 vc4hdmi0` · `1 vc4hdmi1` · **`2 Audio` = KT USB Audio, le DAC du CASQUE** · `3 sndrpihifiberry` = les haut-parleurs. Appliquer ce conseil aurait **déplacé la sortie par défaut des écouteurs vers les haut-parleurs** — un changement de comportement déguisé en correction. Le bon nom est `CARD=Audio`.
        - 📌 **Un mauvais conseil dans un test de garde est pire qu'aucun conseil** : il fait appliquer une régression avec la conscience tranquille. Le message a été réécrit.
      - 🔴 **Et la justification était fausse aussi** : le son de démarrage **n'emprunte pas** le périphérique par défaut. `scripts/play_chime.py` passe par MPD — sa propre docstring le dit (« via MPD, pas de click DAC »), donc par `eqhp`/`eqcasque`. Vérifié également que **tous** les appels `amixer` du projet précisent `-D` (`audio_eq_apply.py`). Le seul usage réel du périphérique par défaut est un `aplay` ou un `amixer` tapé à la main en SSH.
      - **L'enjeu est donc faible — mais le correctif reste juste**, pour une raison qui n'était pas dans le ticket d'origine : `hw:2,0` désigne un périphérique **USB**, et contrairement à la HiFiBerry (déclarée par overlay), un USB peut être **débranché ou changé de port**, ce qui décale toute la numérotation.
      - 🛠️ **Correctif livré** : `scripts/asound.conf`, **copie versionnée** de `/etc/asound.conf` (qui vivait hors du dépôt, donc perdu sur une image SD fraîche — même problème que la conf Apache de TICKET-127). Seuls deux champs changent : `hw:2,0` → `hw:CARD=Audio,DEV=0` et `card 2` → `card "Audio"`. Toute la partie alsaequal est inchangée.
      - 🔌 **Élément de contexte apporté par Thomas** : il a peut-être changé le port USB du DAC casque le matin même, en remplaçant les cellules. **Conséquence** : l'ancien `hw:2,0` ne désignait peut-être pas la même carte la veille — le périphérique par défaut a pu basculer silencieusement. Vérification tentée via `journalctl -k -b -1`, **non concluante** : les deux boots n'affichent que la ligne générique `registered new interface driver snd-usb-audio`, sans numérotation. À laisser en indéterminé.
        - ✅ **Démonstration en direct de l'intérêt du nommage** : le casque fonctionne parfaitement **après** ce changement de port, parce que `pcm.plugequal_casque` le désignait déjà par `CARD=Audio` et non par un chiffre.
      - ✅ **Tests de garde** : message du contrôle Z6 corrigé, et **nouveau contrôle de dérive** — `/etc/asound.conf` est comparé à `scripts/asound.conf` (hors commentaires et lignes vides). Sans lui on corrigerait le dépôt en croyant avoir corrigé le Pi : exactement le piège de la zone Z12.
      - ✅ **Résultat le 2026-08-17** : smoke test **48 OK · 0 échec · 0 avertissement** — premier passage entièrement vert. L'avertissement traînait depuis le 2026-08-05.
      - ✅ **Confirmé à l'oreille le 2026-08-17**, test à trois branches : `plughw:CARD=sndrpihifiberry` → **haut-parleurs** · `plughw:CARD=Audio` → **casque** · `default` → **casque**. Le périphérique par défaut sonne donc comme le DAC USB : comportement préservé à l'identique, et confirmation directe que l'ancien conseil (`CARD=sndrpihifiberry`) aurait déplacé le son vers les haut-parleurs.
        - 📌 **Méthode à réutiliser** : pour lever un doute sur une sortie audio, ne jamais jouer un seul son en demandant « c'est le bon ? ». Jouer les deux sorties **explicitement nommées**, puis la sortie en question — la comparaison se fait toute seule et ne demande aucune interprétation.
      - ✅ **TICKET-125 clos le 2026-08-17.**
      - 🛠️ **Correctif** : remplacer `hw:2,0` par `hw:CARD=sndrpihifiberry,DEV=0` et `card 2` par `card sndrpihifiberry`. Deux lignes — mais dans `asound.conf`, donc zone Z6 : une erreur de syntaxe coupe **tout** le son. À faire avec MPD arrêté et une vérification `aplay -D default` derrière.
      - ⚠️ `/etc/asound.conf` est hors du dépôt : à capturer dans la sauvegarde ghost (TICKET-085) et à documenter dans `docs/20-SETUP_SYSTEME.md` §6.4.

- [x] TICKET-124 — audio/UX — Gain général du casque, séparé de la courbe d'égalisation (2026-08-05) — ✅ **CLOS le 2026-08-17** (écoute réelle validée à 4 dB, puis 10 h de voiture)
      - **Demande de Thomas**, après avoir trouvé l'astuce lui-même : il avait monté les dix bandes de +5 dB à la main. Il veut **un seul curseur de 0 à 6 dB** qui décale toutes les fréquences du casque, et pouvoir ensuite charger un profil de forme par-dessus.
      - **Le problème que ça règle** : `bands_db` mélangeait la **forme** et le **niveau**. Charger « Voix claire » écrasait le gain réglé pour la voiture, et il fallait tout remonter à la main.
      - 💡 **Pourquoi ce gain marche là où monter le volume ne suffisait plus** : le boost alsaequal intervient **après** l'étage de volume de MPD (déjà à 100) et après le mixer du DAC (déjà à 0 dB). C'est la dernière marge de la chaîne — cf. TICKET-116, où le DAC KT USB Audio a été identifié comme facteur limitant.
      - **Décisions prises avec Thomas** :
        - **Additif avec écrêtage par bande** : résultat = profil + gain, chaque bande plafonnée à +12 dB (limite alsaequal). Conséquence assumée : sur un profil déjà haut, les bandes saturées s'alignent et la courbe s'aplatit. L'IHM prévient **avant** d'enregistrer en nommant les bandes concernées, et `audio_eq_apply.py` les journalise.
        - **Casque uniquement.** Les haut-parleurs restent tenus par `speakers_max ≤ 80` — invariant de sécurité auditive, pas de porte dérobée.
        - **Dans la page Égaliseur**, en haut de l'onglet Casque, à côté des presets. Pas d'accès depuis l'IHM enfant.
        - **Le gain persiste** comme tout réglage. ⚠️ Corollaire à garder en tête : un gain de +6 dB réglé pour la voiture reste actif à la maison, dans le calme.
      - 🛠️ **Implémenté le 2026-08-05** : champ `gain_db` distinct dans `data/audio_eq.json` (profil casque), curseur 0–6 dB dans `web/admin/audio_eq.php` avec avertissement d'écrêtage en direct, application dans `scripts/audio_eq_apply.py`.
      - 🐛 **Piège évité au passage** : le JavaScript de la page sélectionnait les curseurs par `input[type=range]`. Le curseur de gain aurait été pris pour une onzième bande — écrasé par les presets et envoyé dans `bands_db`. Sélecteur restreint à `input[type=range][name="bands[]"]`.
      - 🛡️ **Zone Z6 enfin couverte** : elle n'avait aucune garde automatique malgré TICKET-030. Smoke test §8 — `hw:CARD=` dans `mpd.conf` (échec si un `hw:[0-9]` traîne), taille des `.bin` à 840 octets, `speakers_max ≤ 80`, `gain_db` dans 0..6.
      - 📍 **Gain retenu : 4 dB** (constaté au smoke test du 2026-08-17 ; il était à 5 dB le matin même). **Réglage volontaire de Thomas**, pas une dérive — vérifié auprès de lui. Le smoke test §8 affiche cette valeur à chaque passage : c'est là qu'on la relève avant toute écoute.
      - ✅ **Écoute réelle validée le 2026-08-17** — Thomas : « le casque est parfait, ça marche parfaitement bien ». Le mécanisme gain / forme séparés fait donc ce qu'on lui demandait, au gain de 4 dB. **La partie que le smoke test ne saura jamais juger est faite.**
      - ⏳ **Reste** : le test en voiture (TICKET-116), seul contexte encore non couvert.

- [x] TICKET-116 — audio — Gain casque trop faible en écoute nomade (voiture) (2026-08-03) — ✅ **CLOS le 2026-08-17** : « la radio a survécu à 10 h de voiture »
      - Demande de Thomas : niveau au casque insuffisant en voiture.
      - 🔍 Chaîne vérifiée de bout en bout, **aucune atténuation cachée** : mixer `Headphone` du DAC KT USB Audio à 100 % / 0.00 dB, EQ plat à 50, mapping IHM correct (`headphones_max = 100`), `mpc volume` atteint bien 100.
      - **Conclusion : le DAC KT USB Audio est le facteur limitant**, pas un bridage logiciel.
      - 🛠️ Appliqué : `volume_normalization "yes"` dans `/etc/mpd.conf` ; bandes EQ casque 1 kHz / 2 kHz / 4 kHz passées de 50 à 70 (~+5 dB) via `amixer -D eqcasque` — cf. TICKET-030 pour la mécanique des profils EQ.
      - ⏳ Reste : test réel en voiture. Si toujours insuffisant, le levier suivant est matériel (DAC ou ampli casque), pas logiciel.

- [x] TICKET-112 — feature/sécurité — Écran « Chambre » : contrôle domotique (Legrand/Netatmo via passerelle VM) depuis l'IHM enfant (2026-07-19) — ✅ **CLOS le 2026-08-17** : Thomas confirme que le retour de position du volet fonctionne parfaitement, c'était le dernier point ouvert
      - ✅ **2026-07-24 — Phases 1 et 2 TERMINÉES et validées en réel (sur les équipements du bureau, avant bascule chambre).** Architecture Home Assistant ABANDONNÉE au profit d'une **VM passerelle FastAPI + API Netatmo Connect directe** (VM Debian déjà en place, 192.168.1.3).
          - Spike OAuth : app Netatmo déclarée, token + refresh OK, modules identifiés, lampe (on/off + `brightness` 0-100) et volet (`target_position` 0-100) pilotés en réel.
          - Découverte clé : l'orientation des lames du BSO n'est PAS pilotable via `setstate` (couplée mécaniquement à la position) → l'IHM n'a qu'un seul axe de position 0-100 (0 = occultation totale = nuit).
          - Service passerelle : FastAPI (`app.py` sur la VM), endpoints `/lampe` et `/volet`, whitelist 2 modules, refresh token auto, cache (quota Netatmo ~500/j), service systemd `hechicero-passerelle` — survit au reboot VM.
          - Écran : `web/chambre.html` (page autonome, aucun secret) sert sur le Pi (`http://192.168.1.86/chambre.html`) et pilote lampe + volet du bureau via la passerelle — base de l'intégration Phase 3.
          - Sécurité : aucun secret ni ID de module ni prénom hors de la VM ; l'IHM ne connaît que 2 actions génériques.
          - 🐛 **Souci connu** : le retour d'état de **position réelle du BSO** ne s'affiche pas correctement dans `web/chambre.html` (la commande marche, c'est le feedback de position qui est à fiabiliser). Détail : `docs/95-DOMOTIQUE_CHAMBRE.md` §8.
          - **Détails complets : `docs/95-DOMOTIQUE_CHAMBRE.md`.**
      - 🛠️ **2026-07-24 — Phase 3 (intégration IHM) CODÉE, pas encore testée en réel.** Transposition de `web/chambre.html` dans l'IHM enfant `web/lecteur/index.html` comme vrai écran du lecteur :
          - Nouvel écran `#chambre` (markup + CSS scopé `.ch-*` / `#chambre`, accent cyan dédié `--ch-cyan`, IDs préfixés `ch-*` pour zéro collision avec l'existant — vérifié, notamment le `ch-title` des chapitres est distinct). Enregistré dans `ALL_SCREENS`.
          - Logique lampe + volet transposée fidèlement du prototype (halo animé, lissage de position, badge `moving`, timeout 6s → « hors ligne »). **Fetch passerelle uniquement à l'ouverture de l'écran** (`startChambre`/`stopChambre`) : rien n'est appelé au boot ni écran fermé (kiosque démarre passerelle éteinte OK, quota Netatmo préservé). Appels navigateur→passerelle en direct (`CH_GW='http://192.168.1.3:8000'`, aucun secret côté navigateur).
          - **Mini-lecteur** : apparaît automatiquement en bas de l'écran Chambre pendant une lecture (comportement natif des écrans non-lecteur, demande de Thomas) — la lecture n'est jamais coupée par l'ouverture de l'écran.
          - **Bouton GPIO23** (`buttons_daemon.py`) : passe de `handle_unassigned` à `handle_chambre` (dans `HANDLERS`, toggle simple). Émet `request_screen=chambre` (mécanisme `request_screen`/`get_ui_request` réutilisé des favoris, `radio.php` déjà générique — aucune modif PHP). Côté JS, `pollUiRequest` gère `chambre` en toggle (ouvre / revient à l'écran précédent).
          - **Réveil écran** (demande Thomas) : (a) veille « navigateur » `#sleep-overlay` levée côté JS quand la demande arrive ; (b) dalle physiquement éteinte (DPMS) réveillée par `buttons_daemon.py` via `screen_dpms.sh on` — lancé en **thread détaché** (jamais bloquer la boucle GPIO) et via `runuser` root→thomas avec env Wayland (pas `sudo`, cassé par NoNewPrivileges du durcissement TICKET-011). En sortie de veille, la Chambre s'ouvre (pas de toggle-close).
          - ⚠️ **À valider en réel (point le plus incertain)** : le réveil DPMS depuis le daemon root vers la session Wayland de `thomas` (`runuser` + env). Tester d'abord la commande à la main avant de se fier au bouton.
      - ⏳ Reste : test réel Phase 3 (voir plan de test), correction du feedback position BSO (§8 doc), Phase 4 (bascule `LAMPE_ID`/`VOLET_ID` sur la chambre côté VM, restreindre CORS, test reboot Freebox).
      - 🗄️ Cadrage historique ci-dessous (hypothèse Home Assistant) conservé pour mémoire — architecture retenue = `docs/95-DOMOTIQUE_CHAMBRE.md` :
      - ⏸️ **EN PAUSE (état au 2026-07-19, désormais dépassé — repris et livré le 2026-07-24, voir ci-dessus)** (décision Thomas, le jour même de l'ouverture) : le cadrage a révélé que le prérequis n'est pas une petite config mais **l'installation et la prise en main complètes d'un Home Assistant** (VM Freebox), soit un chantier à part entière avant même de commencer à coder côté Hechicero. Thomas préfère ne pas engager ce temps maintenant. Le cadrage ci-dessous reste entièrement valable pour la reprise — rien n'est à refaire.
      - Demande de Thomas : nouvel écran permettant de piloter la lumière et le volet de la chambre de son fils depuis Hechicero.
      - ⚠️ **Prémisse corrigée en cours de cadrage (2026-07-19)** : le ticket a d'abord été écrit en supposant une instance **Home Assistant existante** — c'est faux. Thomas a **Google Home**, et les appareils réels sont du **Legrand / Netatmo** (gamme "with Netatmo", app Home + Control). Ne pas repartir de l'hypothèse HA-déjà-en-place dans les prochaines sessions.
      - Recherche faite : **Google Home est une impasse** — les "Home APIs" ouvertes par Google sont des SDK **mobiles uniquement** (Android/iOS, certification obligatoire), inutilisables depuis un serveur PHP/Python sur le Pi. On contourne donc Google Home entièrement et on parle directement à Legrand.
      - **API Legrand/Netatmo (dev.netatmo.com, "Home + Control")** : existe et est documentée, volets roulants supportés (`NLV` = interrupteur volet, `NLLV` = interrupteur volet avec niveau 0-100%). MAIS **cloud uniquement, aucune API locale** → 3 conséquences : (1) nécessite Internet, pas juste le Wi-Fi ; (2) OAuth2 avec **renouvellement de jeton toutes les 3h**, re-validation manuelle si un renouvellement échoue (point fragile connu) ; (3) limites de débit d'appels → l'affichage de l'état réel doit rester à une cadence raisonnable, surtout pas le polling 1s des favoris.
      - 💡 **Piste à explorer en priorité à la reprise (Thomas, 2026-07-19)** : il possède **déjà une machine Home Assistant quelque part**, pas encore mise en service. Si elle est remise en route, elle remplace avantageusement la VM Freebox (pas de limite 2 Go/2 vCPU, pas de dépendance au comportement de la box au reboot). **Première question à poser à la reprise : quel matériel, où, dans quel état ?** — avant de repartir sur le scénario VM Freebox ci-dessous, qui reste le plan B.
      - **Architecture retenue (2026-07-19, sous réserve de la piste ci-dessus)** : **Home Assistant en VM sur la Freebox Ultra**, comme couche de traduction entre Hechicero et Legrand. Écarté : (a) API Legrand en direct depuis le Pi — obligerait à réimplémenter tout le cycle OAuth2/refresh 3h et sa gestion d'échec ; (b) HA sur le Pi Hechicero — **refusé délibérément**, le Pi est déjà en throttling thermique (TICKET-109, ventilateur TICKET-111 pas encore monté), ce serait exactement la régression que Thomas interdit.
        - Freebox Ultra : VM supportées, **2 vCPU et 2 Go de RAM non extensibles** (contrairement à la Delta, extensible jusqu'à 14 Go) — suffisant pour HA + intégration Netatmo seule, mais plafonne pour un usage HA plus large plus tard.
        - Avantages : Freebox allumée en permanence et câblée (pas de dépendance au Wi-Fi entre HA et le réseau), HA gère nativement le renouvellement des jetons Legrand, zéro charge ajoutée sur le Pi.
        - ⚠️ Point de vigilance tiré de TICKET-109 (épisode 4) : la Freebox réapplique parfois ses paramètres après un redémarrage — **vérifier que la VM redémarre bien automatiquement après un reboot box**.
      - Décisions UX prises avec Thomas (2026-07-19) :
        - Volet : boutons Ouvrir/Stop/Fermer **et** curseur de position (0-100%) — nécessite un module `NLLV` (avec niveau) ; à confirmer sur son installation réelle.
        - État réel affiché pour la lumière et le volet (interrogé, pas supposé) — cohérent avec le reste de l'app (volume, sortie audio, lecture en cours).
        - Vérification d'accessibilité : tester que **Home Assistant répond vraiment**, pas juste que le Wi-Fi est connecté.
        - Config (URL, jeton, entités) : **fichier texte édité en SSH**, jamais de formulaire dans l'admin web (le jeton ne doit pas transiter par une page web non authentifiée, même en réseau local).
        - Écran **toujours disponible**, indépendant des horaires du contrôle parental (l'enfant doit pouvoir éteindre sa lumière le soir même après l'heure limite d'écoute).
        - Fermeture de l'écran : retour à **l'écran précédent** (le bouton peut être pressé depuis n'importe où, contrairement à l'écran favoris).
      - Déclencheur : bouton physique GPIO23 (bouton isolé antenne, jusque-là en réserve) — appui = ouvre l'écran, ré-appui = le ferme (toggle simple, pas tap-ou-maintien comme GPIO16/17/27).
      - ⚠️ **Règle absolue de Thomas** : aucune régression sur l'existant, et **sécurité stricte** — aucun mot de passe/jeton/nom d'entité (les noms d'entités contiennent le prénom de l'enfant) ne doit jamais se retrouver dans un fichier poussé sur GitHub (cf. [[feedback_no_child_name_public]], étendu ici aux identifiants HA/Legrand). Le navigateur kiosque ne doit jamais voir le jeton ni les vrais entity_id : tout passe par un proxy PHP côté serveur qui lit une config hors dépôt.
      - Thomas a déjà un compte développeur Netatmo (dev.netatmo.com).
      - 🔍 **Cadrage 2026-07-19 : architecture et UX décidées, rien codé.**
      - ⏳ Reste à faire à la reprise : (0) **d'abord** faire le point sur la machine Home Assistant que Thomas possède déjà (matériel, emplacement, état) — si exploitable, elle remplace l'étape 1 ; (1) sinon installer HAOS en VM sur la Freebox Ultra, (2) connecter l'intégration Netatmo/Legrand, (3) relever les vrais `entity_id` de la lumière et du volet, (4) créer un jeton d'accès longue durée HA, (5) seulement ensuite coder l'écran + le proxy PHP côté Hechicero.


- [x] TICKET-135 — process/qualité — Registre de non-régression + gardien automatique (2026-08-05)
      - ⚠️ **Renuméroté le 2026-08-17** : portait le numéro 123, déjà pris par le bug « l'écran ne s'éteint plus après un réveil non tactile ». Le bug d'écran garde le 123 car il est cité dans du code vivant (`buttons_daemon.py`, `smoke_test.sh`, `docs/75-NON_REGRESSION.md`) ; ce ticket-ci, clos et sans référence en code, prend le 135. Même remède que la collision TICKET-090 → TICKET-117.
      - **Déclencheur** : `scripts/smoke_test.sh` grossit ticket par ticket, mais rien ne dit *quand* le lancer, *quelles zones* il ne couvre pas, ni *quel bug* chaque test surveille. La leçon de TICKET-120 (panne latente invisible 2 semaines) ne survit aujourd'hui que dans la mémoire du fil de conversation.
      - 🛠️ **Livré** : `docs/75-NON_REGRESSION.md` — carte des **11 zones à risque** (Z1 MPD · Z2 services durcis · Z3 boutons GPIO · Z4 écran/veille · Z5 `data.json` · Z6 chaîne audio · Z7 Wi-Fi · Z8 batterie · Z9 ingestion RSS · Z10 dépôt public · Z11 domotique), chacune avec son piège, son historique, et le test de garde qui la couvre. Plus : les 6 fonctions vitales (§2), la lecture du verdict du smoke test (§4), la **dette de test** (§5, 8 zones sans garde automatique), et la procédure d'ajout d'un test (§6).
      - 🛠️ **Livré** : gardien automatique côté Cowork — évalue le risque **avant** toute modif touchant une zone connue et demande validation explicite, fournit le bloc de vérification **après**, et transforme chaque bug compris en nouveau test de garde (registre + `smoke_test.sh` dans le même commit).
      - **Règle posée** : un test de garde doit **échouer sur le code d'avant le correctif**. Un test qui passe des deux côtés ne couvre rien.
      - 🛠️ **Livré dans la foulée : `scripts/check_privacy.sh`** (zone Z10, intégré au smoke test §6). Le dépôt est public et une fuite de prénom ne se rattrape pas dans l'historique git. **Difficulté de conception** : un script versionné ne peut pas contenir le prénom qu'il cherche — le filet deviendrait la fuite. Les motifs vivent donc dans `private/forbidden_names.txt` (hors dépôt), et le script vérifie d'abord que ce fichier est bien ignoré par git. Balayage sur `git ls-files` (seul ce qui part sur GitHub compte), `grep -I` pour sauter les binaires. **Motifs à écrire avec des limites de mot** (`\bprenom\b`) : sans elles, un prénom court se retrouve à cheval sur deux mots dans les identifiants d'épisodes espagnols de `data.json`.
      - ➡️ La dette de test du §5 devient la liste de travail : Z2 (TICKET-121) en tête.
      - 📌 **Leçon** : un bug corrigé sans test ajouté n'est pas corrigé, il est en sursis.

- [x] TICKET-120 — bug/infra — Boutons physiques HS : lgpio ne pouvait plus créer son tube dans `scripts/` (2026-08-04)
      - ✅ **Corrigé et confirmé par Thomas le 2026-08-04** — les 9 boutons répondent de nouveau.
      - Symptôme : plus aucun bouton physique. `buttons_daemon.service` apparaissait pourtant `active (running)` par intermittence — en réalité une boucle de crash/redémarrage toutes les 5 s (`Restart=always`).
      - **Cause** : la bibliothèque **lgpio** (utilisée par `RPi.GPIO` sur Pi 5) crée un tube nommé `.lgd-nfy<N>` **dans le répertoire courant** du processus. `WorkingDirectory` pointait sur `scripts/` — or depuis le durcissement **TICKET-011**, `ProtectSystem=strict` + `ProtectHome=read-only` rendent ce dossier **non inscriptible** pour le service.
      - 🔍 **La panne était armée depuis le 2026-07-19 et invisible** : lgpio ne pouvait déjà plus créer le tube, mais un `.lgd-nfy0` créé **avant** le durcissement traînait dans `scripts/` et se laissait simplement ouvrir. Sa suppression, pendant le ménage du dépôt de TICKET-117, a fait tomber le château de cartes.
      - Trace : `xCreatePipe: Can't set permissions (436) for .../scripts/.lgd-nfy0, No such file or directory` puis `FileNotFoundError: '.lgd-nfy-3'` (`-3` est un code d'erreur lgpio, pas un numéro de handle).
      - 🛠️ **Correctif** dans `scripts/buttons_daemon.service` : `RuntimeDirectory=hechicero-buttons` + `RuntimeDirectoryMode=0750` + `WorkingDirectory=/run/hechicero-buttons`. systemd crée le répertoire au démarrage, le rend inscriptible **malgré `ProtectSystem=strict`**, et le nettoie à l'arrêt. Le tube ne peut plus manquer, ne pollue plus le dépôt et ne s'écrit plus sur la carte SD. `ls` sans `sudo` y renvoie `Permission denied` — normal, root:0750.
      - Écarté au passage : `button_toggle_test.service`, toujours installé dans `/etc/systemd/system/` alors que son script a été supprimé du dépôt, est bien `disabled` — pas de conflit GPIO. Reste à désinstaller proprement à l'occasion.
      - ➡️ **Suite** : TICKET-121 — les 7 autres services durcis sont peut-être dans le même état latent.
      - 📌 **Leçon** : un service durci qui écrit dans le dépôt est une panne à retardement. Ce n'est pas le ménage qui a cassé les boutons, c'est le durcissement de juillet ; le ménage n'a fait que révéler la panne. Chercher la cause au bon endroit, pas au plus récent.

- [x] TICKET-118 — infra/sécurité — Remise au propre du dépôt et de la documentation (2026-08-04)
      - 🔴 **Fuite corrigée** : `docs/55-PODCAST_SERIE_DECISIONS.md` contenait le prénom réel de l'enfant dans une consigne d'orthographe, alors que le fichier déclare lui-même deux fois « aucun prénom réel (repo public) ». La consigne est rapatriée dans `private/podcast-easteregg/00-contexte.md`, seul endroit autorisé.
      - ✅ **Historique git réécrit** le 2026-08-04 (`git filter-repo --replace-text`) : `git log --all -S` ne trouve plus le prénom. Sauvegarde de l'historique d'origine dans `~/hechicero-github-avant-filtrage.git` (clone mirror de GitHub, 113 Mo). ⚠️ GitHub peut conserver un temps les objets devenus inaccessibles — purge complète = demande de GC ou recréation du dépôt.
      - 🧹 Fichiers morts supprimés et `.gitignore` durci — détail dans TICKET-117.
      - 📚 **Doc** : `80-ALIMENTATION.md` (spec du 2026-06-26) fusionnée dans `05-POWER_MANAGEMENT.md`, qui devient la référence unique batterie — les deux décrivaient le même sujet et divergeaient, et le numéro 80 était en collision avec `80-hardware.md`. Ajout au passage du piège `level_end` (bug des cycles batterie du 2026-07-06) et de la réserve TICKET-011 sur le chemin `shutdown`.
      - 📚 `30-LECTEUR.md` : sections « Non implémenté » et « Évolutions prévues » purgées — elles annonçaient encore comme à venir les favoris, les boutons GPIO, le chime et le script d'intégrité (tous livrés), plus le carrousel et les animations (annulés).
      - 📚 `README.md` : index de la doc corrigé (ajout de `85-SAUVEGARDE_RESTAURATION.md` et `95-DOMOTIQUE_CHAMBRE.md`, qui manquaient). `web/index.php` : commentaire renvoyant à un fichier inexistant (`95-RESTAURATION_URGENCE.md`) corrigé.
      - ✅ Vérifié : `web/podcasts` est un **lien symbolique** vers `~/hechicero/podcasts` — pas de duplication des 28 Go de médias.
      - ✅ Vérifié : les 45 renvois croisés entre docs pointent tous vers des fichiers existants. **Ne pas renuméroter les docs en masse** — c'est ce qui casserait ces renvois.
      - 💥 **Incident au cours de cette passe, à ne jamais reproduire** : `git filter-repo` a été lancé dans le même bloc de commandes que le ménage, **avant le commit**. Son `reset --hard` final a effacé tout le travail non committé — TICKET-114, TICKET-115 et toute la doc du jour. Tout a été réécrit dans la foulée. Règles retenues : (1) une opération destructive d'historique se lance **seule**, jamais enchaînée ; (2) **commit et push d'abord**, sans exception ; (3) une sauvegarde de dépôt se fait par `git clone --mirror` (113 Mo), jamais par `cp -a` d'un dossier qui contient 28 Go de médias.

- [x] TICKET-117 — infra — Nettoyage fichiers morts dans le dépôt (renuméroté depuis TICKET-090 le 2026-08-04, en collision avec le ticket batterie « 51 micro-cycles factices »)
      - ✅ Session 12 : `app.js`, `style.css`, `lecture.html` supprimés via `git rm`
      - ✅ **Deuxième passe le 2026-08-04** : suppression des patchs à usage unique (`patch_ticket114.py`, `patch_ticket115b.py`), des sauvegardes `*.pre-ticket*` et `*.bak`/`*.old`, du bring-up `button_toggle_test.py` + `.service` (remplacé par `buttons_daemon`), de l'artefact lgpio `.lgd-nfy0` et des scripts de migration déjà passés (`fix_durations.py`, `fix_battery_cycles.py`, `seed_tracking.py`, `analyze_bewitched.py`).
      - ✅ `.gitignore` durci pour que ça ne revienne pas : `*.bak`, `*.old`, `*.orig`, `*.rej`, `*.pre-ticket*`, `*~`, `.lgd-nfy0`. Correction au passage de `podcasts/` → `podcasts/*` (la négation `!podcasts/.gitkeep` était inerte : git ne ré-inclut jamais un fichier sous un dossier exclu), avec ajout explicite de `web/podcasts` — un motif contenant un `/` est ancré à la racine et ne couvre plus le lien symbolique par héritage.

- [x] TICKET-115 — bug/UX — Écran noir intermittent : réveil fiable de la dalle (2026-08-02, réécrit et **corrigé le 2026-08-04**)
      - ✅ **Confirmé corrigé par Thomas le 2026-08-04.**
      - Symptôme : par intermittence l'écran restait noir après une extinction de veille, seul un reboot ramenait l'image. VNC continuait de fonctionner (sortie virtuelle) — c'est ce qui a masqué le problème si longtemps.
      - 🔍 **Diagnostic pris en direct pendant la panne** (pas une hypothèse de plus) : `wlr-randr` affichait HDMI-A-1 « Enabled: yes », le bon mode courant, EDID du JRP7003 lu correctement ; `dmesg | grep -i hdmi` : aucun événement depuis le boot. Le Pi se croyait en train d'afficher.
      - **Cause racine** : `wlr-randr --on --preferred` ne déclenche **aucun modeset** quand le connecteur est déjà actif ET déjà au mode préféré. Reposer le même mode est un no-op → la dalle, elle bel et bien éteinte, n'est jamais réveillée.
      - Séquence qui ramène l'image : `--mode 1280x720@60` ; `sleep 3` ; `--mode 1024x600@59.821`.
      - 🐛 **Régression de la 1ère version du correctif** : rebond de mode systématique dans l'action `on`. Or `buttons_daemon.py` appelle `screen_dpms.sh on` à **chaque** appui du bouton antenne GPIO23 (écran Chambre) → l'écran déjà allumé s'éteignait et clignotait à chaque pression.
      - 🛠️ **Réécriture 2026-08-04** de `scripts/screen_dpms.sh` (124 lignes, 5820 octets, md5 `933e04d7a2b435b333d7de67b5f1a247`) :
        - `off` → `wlr-randr --output HDMI-A-1 --off`
        - `on` → lit l'état ; si « Enabled: yes » **ne fait rien** (chemin swayidle resume + bouton GPIO23, zéro clignotement) ; sinon rebond `1280x720@60` → 3 s → `1024x600@59.821`
        - `rescue` → force le rebond quel que soit l'état. Nécessaire parce que le cas « Enabled: yes mais dalle noire » **n'est pas détectable depuis le Pi** (tous les indicateurs sont au vert) : c'est l'humain qui constate et tranche, en SSH.
        - `status` → `wlr-randr`
        - Journalisation de chaque bascule dans `data/screen_dpms.log`.
      - ✅ Les 4 actions testées et conformes au log. Observation utile : pendant un rebond manuel, un **second appel concurrent** à `on` (swayidle resume) a été correctement absorbé en no-op au lieu d'empiler un deuxième rebond.
      - 📌 **Leçon de livraison** : le fichier avait été détruit la veille par un **heredoc collé en SSH tronqué en cours de route**. Méthode retenue : écriture directe via le partage Samba, puis vérification `ls -l` / `md5sum` côté Pi **avant** exécution. Jamais de heredoc, jamais de script de patch transféré.
      - Commande de secours si l'écran affiche « Not Support » : `export WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/run/user/1000` puis `wlr-randr --output HDMI-A-1 --mode 1024x600@59.821`.

- [x] TICKET-114 — bug/UX — Rafraîchissement automatique du catalogue dans le lecteur (2026-08-03, réécrit le 2026-08-04)
      - Problème : après un ingest ou un ajout via l'admin, il fallait recharger Chromium à la main pour voir les nouveaux podcasts.
      - **Cause exacte** : `loadData()` était bien rappelé toutes les 5 min, mais **sans jamais re-rendre l'écran affiché**. `goToPodcasts()` était le seul endroit qui enchaînait chargement puis rendu → tant que l'enfant ne quittait pas la grille pour y revenir, rien ne changeait, même après des heures.
      - 🛠️ `web/lecteur/radio.php` : action `data_version` renvoyant `{mtime, size}` de `data.json`. Deux `stat()`, assez léger pour un polling à 10 s, au lieu de retransférer les ~700 Ko du catalogue. mtime **et** size : mtime seul rate une réécriture dans la même seconde, size seule rate un remplacement de même taille.
      - 🛠️ `web/lecteur/index.html` : `pollCatalogVersion()` toutes les 10 s compare la signature ; au changement, `refreshCatalogInPlace()` recharge `data.json` et re-rend l'écran visible. Le tick 5 min appelle désormais `refreshCatalogInPlace()` au lieu de `loadData()` — c'est ce qui bouche le trou d'origine.
      - ⚠️ **Précaution 1 à ne pas casser en refactorant** : la position de lecture est ré-ancrée sur le **chemin audio** (`findEpisodeByAudio()`), pas sur `currentIdx` — l'ingest insère les nouveaux épisodes en tête de liste, donc l'index désignerait un autre épisode et `next`/`prev` partiraient sur le mauvais. Même famille de piège que TICKET-108.
      - ⚠️ **Précaution 2** : les écrans `player` et `radio-player` ne sont **jamais** re-rendus — la lecture en cours ne doit pas clignoter parce qu'un ingest s'est terminé en arrière-plan.
      - ⏳ **Validation** : `php -l` sans erreur et endpoint vérifié en curl. Le test visuel de bout en bout (nouveaux podcasts apparaissant seuls sur la grille pendant un ingest complet) n'a pas encore été confirmé formellement.

- [x] TICKET-113 — UX/admin — Refonte navigation admin en « bureau » d'icônes façon iPhone (2026-07-24)
      - ✅ **Validé et clos par Thomas le 2026-07-24** (bureau + panneaux, page domotique admin, nav unifiée ‹ Bureau/Lecteur, header « style board » pour les panneaux, État système sur l'accueil, icônes agrandies, icône webradio réparée, sous-titres nettoyés).
      - Demande de Thomas : la page d'admin (`web/index.php`) devient un bureau d'icônes façon vieil iPhone — grosses icônes carrées arrondies avec label, **pensé mobile** (l'admin se consulte depuis un téléphone). But : rendre la navigation plus cohérente **sans trop toucher aux boards déjà en place**.
      - Icônes prévues : ⚙️ Veille + son de démarrage · 🕐 Heures autorisées d'écoute · 🎧 Gérer podcasts + webradios · 📊 Dashboard écoute (`dashboard.php`) · 🔋 Batterie (`battery_dashboard.php`) · ❤️ Favoris (`favoris.php`) · 🎚️ Égaliseur (`audio_eq.php`) · 📻 Ouvrir le lecteur (`/lecteur/`) · 🏠 Domotique · 💾 Sauvegardes (`backup_dashboard.php`, **Expert only**).
      - On garde le toggle **Normal/Expert** (Expert révèle l'icône Sauvegardes), mécanisme `.expert-only`/`body.expert` déjà en place.
      - **Décisions de cadrage (2026-07-24)** :
        - Les 3 fonctions aujourd'hui en sections DANS `index.php` (veille/son = section « Administration avancée » ; horaires = section « Contrôle parental » ; podcasts = sections Ajouter/Podcasts/Webradios/Sync) → **vue dédiée par icône** : taper l'icône masque le bureau et affiche un panneau plein écran avec juste cette fonction + bouton « retour au bureau ». Le contenu interne des sections NE CHANGE PAS (mêmes markup/JS), on ne fait que les envelopper dans des conteneurs montrés/masqués → risque de régression minimal. NB : le contrôle des **langues** (dans la section parental) n'a pas d'icône dédiée → à loger dans le panneau Horaires (parental).
        - **Domotique** : nouvelle page admin dédiée (`web/admin/domotique.php` à créer) qui **reprend le look de l'écran Chambre du lecteur** (ampoule + suns, volet à lamelles, curseurs à gros pouce), parle à la passerelle `192.168.1.3:8000` (aucun secret, comme `chambre.html`). Pensée pour accueillir **plus tard** des règles d'administration (ex. volet ouvrable seulement 8h–19h, veilleuse nuit auto-extinction 10 min) — fonctions futures, pas dans ce ticket.
        - Boards déjà autonomes (dashboard, batterie, EQ, favoris, sauvegardes) : **on n'y touche pas**, le bureau fait juste un lien ; au plus un petit « retour au bureau ».
      - ✅ Maquette validée par Thomas (2026-07-24).
      - 🛠️ **Partie A faite (index.php)** : bureau `#springboard` (10 icônes carrées colorées, 3 col mobile / 5 desktop) ajouté après le header ; état de vue dans `body[data-view]` (attribut, PAS `body.className` que `setMode()` réécrit) ; `showView()` bascule accueil ↔ panneaux ; barre `#panel-back` (retour). Les 7 sections existantes reçoivent `data-panel` (veille / horaires / podcasts) sans toucher leur contenu interne ; CSS masque les sections hors panneau (override du `!important` de `.expert-only`), l'expert-only continue de gérer le contenu expert AU SEIN d'un panneau. Section « Administration avancée » renommée « Veille & son de démarrage » et **dé-expert-only** (accessible en normal via son icône, demande Thomas). `.ha-nav` (barre de liens du header) masquée sur l'admin, remplacée par le bureau. Icône Sauvegardes = `expert-only`. Aucune modif du JS existant (loadStatus/loadConfig/etc. inchangés).
      - 🛠️ **Partie B faite** : `web/admin/domotique.php` (nouveau) — reprend le look de l'écran Chambre (ampoule + suns, volet à lamelles, curseurs à gros pouce, toggle volet = consigne, animation de position, statut passerelle). Standalone, parle à `192.168.1.3:8000`, aucun secret. Header admin (`ha-page`/`ha-nav`) avec lien « ‹ Bureau » vers `/`. Placeholder commenté pour les règles futures (volet 8h-19h, veilleuse nuit 10 min).
      - 🛠️ **Harmonisation nav + retours (2026-07-24)** :
        - Nav unifiée sur TOUS les boards (battery_dashboard, dashboard, favoris, audio_eq, backup_dashboard, domotique) : la longue barre (Admin/Écoute/Batterie/Favoris/Audio/Lecteur) est remplacée par **‹ Bureau + 📻 Lecteur** en haut à droite (modèle du board Domotique). La navigation passe par le bureau d'icônes. Lecteur enfant non touché.
        - Palette déjà partagée : `index.php` charge `hechicero-admin.css` et n'écrase pas les couleurs de base → bureau + boards ont la même palette navy/or que Batterie (rien à faire).
        - Cartes du board Favoris alignées sur `.ha-panel` (fond `--surface`, rayon 16, ombre).
        - Sous-titres « TICKET-… » (Favoris, Égaliseur, Domotique) remplacés par du texte propre.
        - 🐛 **Bug corrigé** : icônes des webradios cassées dans le board Favoris — le champ `image` est relatif au lecteur, préfixé désormais par `/lecteur/` (fallback `image_url`).
      - ✅ Testé et validé par Thomas le 2026-07-24 (nav harmonisée, headers de panneaux « style board », État système sur l'accueil, icônes agrandies).

- [x] TICKET-046 — UX — Favoris (cœur) accessibles rapidement
      - ✅ **Validé en conditions réelles et clos par Thomas le 2026-07-19.**
      - 🔍 Cadrage fait avant dev. Existant côté matériel : GPIO23 (bouton isolé, emplacement antenne) déjà câblé et réservé pour ce bouton depuis TICKET-101 (2026-07-08), branché en `handle_unassigned` dans `buttons_daemon.py` en attendant ce ticket — voir [[project_hechicero_buttons_gpio]].
      - Existant côté UX design : persona enfant (`UX Design/personnae.md`) demande explicitement "Favoris accessibles rapidement (cœur)" et évoque l'idée "double-tap = cœur" comme interaction magique. Parcours parent (`UX Design/NaviguerDansLeContenus.md`) prévoit aussi une gestion des favoris côté admin.
      - Aucune structure de données favoris n'existait avant (`data.json` n'a pas de champ favori, et il est régénéré par l'ingestion RSS — donc pas un bon endroit pour stocker un choix persistant de l'enfant).
      - Référence externe (Merlin, l'enceinte que le fils de Thomas utilise) : bouton ♥ physique avec 3 usages — 1) pendant la navigation, ouvre directement la liste des titres favoris ; 2) pendant l'écoute, ajoute/retire le titre en cours (cœur bleu affiché sur la jaquette) ; 3) appui long = batterie + date/heure (fonction annexe).
      - ✅ **Cahier des charges figé (2026-07-19)** :
        - Portée : favori par **épisode**, pas par podcast entier (confirmé avec l'enfant).
        - Déclencheur : bouton physique dédié = **GPIO16** (confirmé sur le boîtier réel via `buttons_daemon.py` en mode identification — dernier bouton de la ligne des 7, jusque-là en réserve). GPIO23 (bouton isolé antenne) réservé pour un usage futur différent, pas le favori (devenu TICKET-112) — cf. [[project_hechicero_buttons_gpio]].
        - Tap court = ajoute/retire le favori sur l'épisode en cours d'écoute.
        - Appui long = ouvre un écran dédié listant les favoris (façon Merlin).
        - Retour visuel à l'ajout : un cœur apparaît et se fixe sur la jaquette/icône de l'épisode. Pas de son.
        - Côté parent : favoris visibles et gérables (suppression) depuis l'admin web.
        - Point technique : les `id` d'épisode dans `data.json` sont des slugs du titre seul (`normalize_id()` dans `scripts/rss_ingest/parser.py`), pas garantis uniques entre podcasts différents — clé de stockage `favoris.json` = composite `podcast_id/episode_id`.
      - 🛠️ **Implémenté le 2026-07-19** :
        - `data/favoris.json` (hors dépôt) : dict clé `type:podcastId/episodeId` (episode) ou `type:radioId` (radio) → `{type, podcast_id/episode_id ou radio_id, added_at}`.
        - `web/lecteur/radio.php` : actions `toggle_favori`, `get_favoris`, `remove_favori`, `request_screen`/`get_ui_request` (polling pour l'ouverture d'écran via appui long).
        - `scripts/buttons_daemon.py` : GPIO16 dans `TAP_OR_HOLD` (tap = `handle_favori_toggle`, maintien = `handle_favori_screen`).
        - `web/lecteur/index.html` : écran `#favoris`, badge cœur (`.fav-heart`/`.is-fav`) animé (`favPop`), polling `pollUiRequest` (1s) et `fetchFavoris` (1s après ajustement).
        - `web/admin/favoris.php` (nouveau) : liste + suppression, lien nav "❤️ Favoris" sur 4 pages admin.
        - `.gitignore` : `data/favoris.json`, `data/ui_request.json`, `data/nav_context.json` ajoutés.
      - 🛠️ **Retours Thomas après tests réels, tous traités** : cœur agrandi + animation `favPop` ; délai d'apparition resserré à 1s ; webradios rendues favorisables (`favori_key()` préfixée par type, `find_current_radio()`) ; navigation suivant/précédent au sein des favoris (`favNavQueue`/`favNavIdx`, `playFavItem()`) étendue aux boutons physiques GPIO17/27 via un contexte partagé côté serveur (`data/nav_context.json`, action `set_nav_context`) — **`buttons_daemon.py` n'a pas eu besoin d'être modifié pour cette dernière extension**, toute l'intelligence est dans `radio.php`. `now_playing` détecte désormais aussi les webradios (avant : épisodes seulement).
      - ✅ **Validé de bout en bout par Thomas le 2026-07-19** (cœur, favoris webradio, retrait par second appui, navigation suivant/précédent écran + bouton physique).

- [x] Correction — bug — Reprise automatique de la lecture au démarrage à froid de MPD (2026-07-19)
      - Découvert par Thomas juste après le test réel de shutdown de `battery_watchdog` (TICKET-011) : au redémarrage du Pi, le podcast s'est remis à jouer tout seul, sans action sur l'IHM — comportement non prévu dans la séquence de démarrage à froid.
      - Cause : `/etc/mpd.conf` définit `state_file "/var/lib/mpd/state"` (config Debian par défaut, jamais retouchée par le projet) sans `restore_paused`. Par défaut MPD restaure aussi l'état play/pause sauvegardé, pas seulement la position — comme MPD avait été relancé plusieurs fois en état "playing" pendant les manips TICKET-030 de la veille et le test de shutdown du matin, l'état sauvegardé était "playing".
      - Fix : ajout de `restore_paused "yes"` juste après `state_file` dans `/etc/mpd.conf`, puis `sudo systemctl restart mpd`. Garde la reprise de position (utile) mais force l'état "en pause" au démarrage.
      - ✅ Validé en conditions réelles par Thomas le 2026-07-19 : `mpc status` après redémarrage MPD affiche `[paused]` sur la piste en cours, plus d'auto-play.
      - Documenté dans `docs/20-SETUP_SYSTEME.md` §6.1.

- [x] TICKET-109 — bug/hardware — Coupures Wi-Fi récurrentes + signal anormalement faible à 30cm de la Freebox (2026-07-18)
      - **Épisode 1 (2026-07-15/16, résolu)** : Freebox en "WPA 2/3 - Compatibilité" → association Wi-Fi en boucle (faux message "Secrets were required"). Fix : Freebox basculée en WPA2-AES pur. Aussi fait : power management Wi-Fi désactivé définitivement (`wifi-powersave-off.conf`, `wifi.powersave=2`), MAC remise permanente (`2c:cf:67:cc:4a:2d`, le random cassait le bail DHCP), firmware `brcm80211` blanchi après re-test.
      - **Épisode 2 (2026-07-16, résolu)** : récidive, cause différente — même SSID "El CORAL GOURMET" diffusé en 2.4GHz (BSSID `3A:07:16:3C:3D:80`, canal 11) ET 5GHz DFS (BSSID `...:88`, canal 128) ; sans BSSID épinglé, le Pi retentait le 5GHz DFS et échouait. Fix : BSSID épinglé sur le 2.4GHz (`nmcli connection modify "El CORAL GOURMET" 802-11-wireless.bssid 3A:07:16:3C:3D:80`).
      - **Épisode 3 (2026-07-18, résolu)** : nouvelle coupure à 12:29:46 (reconnexion auto en 10s, même BSSID — le fix BSSID tient, donc pas du roaming). Anomalie centrale : **signal -59 à -71 dBm et débits parfois plancher (rx jusqu'à 1-2 Mbit/s) à 30cm de la borne**, attendu ≈ -35/-40 dBm. Large balayage de causes mené (interférence canal 11, régulatoire/txpower, thermique, Bluetooth, blindage RF du boîtier) — la plupart écartées, cause finale rattachée à la distance/signal réel plutôt qu'à un défaut matériel (cf. TICKET-110 ci-dessous, découvert en creusant l'épisode 4).
      - **Épisode 4 (2026-07-18 soir) — panne totale après 4 jours d'absence, résolu** : après 2 semaines de fonctionnement normal, Thomas part 4 jours, revient, plus aucune connexion Wi-Fi. Un répéteur Wi-Fi officiel Free a été installé entre-temps (60cm de Hechicero). Diagnostic : Freebox repassée en **"WPA 2/3 - Compatibilité (recommandé)"** au lieu du WPA2-AES pur fixé le 16/07 — exact même bug que l'épisode 1. Cause à 100% côté Freebox (mise à jour Freebox Server 4.12.2 du 3/07 et/ou réapplication des paramètres du compte Free en ligne à chaque reboot, qui écrase les modifs locales FreeboxOS). **Fix** : rebasculé sur WPA2-AES pur. **Confirmé résolu** : logs NetworkManager montrent l'échec avant fix (`no secrets`) puis succès immédiat après (`scanning → associating → 4way_handshake → completed`). Rien côté Pi (apt/firmware propres).
      - **Point de vigilance pour l'avenir** : si la Freebox réapplique bien les paramètres du compte Free à chaque reboot, ce même bug peut revenir après un futur redémarrage box. À vérifier : si le réglage WPA2-AES peut être fixé côté espace abonné Free en ligne pour survivre à un reboot.
      - ✅ **Clos le 2026-07-18** (confirmé par Thomas) : test réel de 30 min (déplacement dans l'appart, radio allumée) — zéro `disconnect`/`deauth` dans les logs NetworkManager, le fix WPA2/3-Compatibilité de l'épisode 4 tient.
      - Détail complet du balayage (épisode 3) et lien avec TICKET-110 : voir mémoire `project_hechicero_wifi_dropouts` et [[reference_samba]] (l'instabilité affectait aussi l'accès Q:\).

- [x] TICKET-110 — feature/infra — Roaming automatique multi-AP (box + répéteur Free) (2026-07-18)
      - Contexte : Hechicero est mobile (bureau/salon). Répéteur Wi-Fi officiel Free installé le 18/07, même SSID "El CORAL GOURMET" diffusé par la box ET le répéteur, plusieurs BSSID chacun. Sans intervention le Pi restait figé sur le BSSID épinglé au démarrage (nécessaire depuis TICKET-109 épisode 2 pour éviter un BSSID 5GHz DFS de la box).
      - Découverte en creusant TICKET-109 épisode 4 : une fois reconnecté, le Pi restait épinglé sur la box (signal -66dBm) alors que le répéteur à 60cm affichait -31dBm après bascule manuelle du BSSID — toute la piste "signal marginal/thermique/boîtier" explorée dans TICKET-109 était probablement en réalité de la distance à la box, pas un problème matériel.
      - **Implémenté et installé** : `scripts/wifi_roam.py` + `scripts/wifi_roam.service` (voir `docs/70-SERVICES_SYSTEMD.md` §7sexies) — scan toutes les 60s, exclut les BSSID sur fréquence DFS (~5250-5725MHz), bascule vers le plus fort du reste si le gain est net (≥8dB) et confirmé sur 2 scans consécutifs (anti-flapping, `MARGIN_DB=8`/`CONFIRM_COUNT=2`). Log dans `data/wifi_roam.log`. Coexiste avec `wifi_watch.service` (TICKET-109, lecture seule) sans conflit.
      - ✅ **Clos le 2026-07-18** (décision Thomas) : code relu et validé — anti-flapping fonctionne comme prévu. Observé en conditions réelles : dip à -62dBm avec meilleur candidat à -46dBm détecté, mais confirmé une seule fois sur les 2 scans consécutifs requis → pas de bascule déclenchée (comportement anti-flap voulu, pas un bug). Pas encore observé de vraie bascule effective de bout en bout (dégradation soutenue 2+ min) ; Thomas fera un test physique (déplacer Hechicero bureau/salon) le 2026-07-19.

- [x] TICKET-079 — UX/saisonnier — Mode Noël (décembre uniquement) (2026-07-18, ajusté le même jour après retours Thomas)
      - Neige animée (`#noel-snow`, flocons générés en JS, animation CSS `noel-fall`) — overlay global fixed, visible sur tous les écrans (accueil, grilles, lecteur) **et sur l'écran de veille** (`z-index:10050`, au-dessus de `#sleep-overlay` à `9999`)
      - Chapeau de Noël (SVG inline, `noelHatMarkup()`) sur le coin des jaquettes podcast (`renderPodcasts()`) **et** des jaquettes d'épisodes (`renderChapters()`, variante `.noel-hat-sm`) — forme conique fléchie + pompon, incliné à -42°, plus marqué qu'à l'origine
      - Traîneau du Père Noël (2 rennes + traîneau + Père Noël, SVG inline, coloré) traversant l'écran toutes les 60-90s — rennes repositionnés **devant** le traîneau dans le sens du déplacement (bug initial : rennes derrière, donc poussaient le traîneau), `z-index:9000` (sous l'overlay de veille, volontairement absent pendant la veille)
      - Guirlande lumineuse (`#noel-garland`) : câble en chaînette réelle (`y = cosh(x)`, x ∈ [-1,1], converti en coordonnées SVG dans `catenaryY()`/`catenaryPoint()`, fonctions génériques réutilisées par le mode anniversaire ci-dessous), pas des scallops répétés comme au premier essai — câble visible (double trait sombre + liseré clair) avec 24 ampoules multicolores clignotant en asynchrone, positionnée en haut de tous les écrans **et de l'écran de veille** (`z-index:10040`)
      - Garde `new Date().getMonth() === 11` + override de test `?noel=1` / `?noel=0` dans l'URL (`isNoelActive()`)
      - Zéro dépendance réseau/CDN, tout inline dans `web/lecteur/index.html`
      - ⏳ Non testé en conditions réelles sur le Pi par Thomas (ajustements validés par retours sur captures d'écran uniquement)
      - Fichier modifié : `web/lecteur/index.html`

- [x] TICKET-079bis — UX/saisonnier — Mode Anniversaire (20 novembre uniquement) (2026-07-18)
      - Même architecture que TICKET-079 (mode Noël), réutilise les fonctions génériques `catenaryY()`/`catenaryPoint()`/`catenaryWireD()` pour la guirlande
      - Confettis colorés qui tombent en continu (`#anniv-confetti`, rotation aléatoire), overlay global visible sur tous les écrans et sur l'écran de veille (`z-index:10050`)
      - Chapeau de fête (cône + pois + pompon, `annivHatMarkup()`) sur les jaquettes podcast, les jaquettes d'épisodes (`.anniv-hat-sm`) et la grande jaquette de l'écran lecteur
      - Guirlande de fanions triangulaires sur la même courbe en chaînette que la guirlande de Noël (`#anniv-garland`), qui ondulent légèrement (`anniv-flag-sway`), visible aussi sur l'écran de veille (`z-index:10040`)
      - Banderole "Joyeux Anniversaire !" / "¡Feliz Cumpleaños!" (texte alterné FR/ES à chaque passage) qui traverse l'écran toutes les 60-90s, style ruban avec pointes + texte en dégradé or (`.gv-gold`, même style que le logo Hechicero) — cachée pendant la veille comme le traîneau de Noël
      - Garde `getMonth()===10 && getDate()===20` (20 novembre) + override de test `?anniv=1` / `?anniv=0` dans l'URL (`isAnnivActive()`)
      - Zéro dépendance réseau/CDN, tout inline dans `web/lecteur/index.html`
      - ⏳ Non testé en conditions réelles sur le Pi par Thomas
      - Fichier modifié : `web/lecteur/index.html`

- [x] TICKET-037 — ❌ Annulé (2026-07-18) — UX — Animations simples (fade/slide) dans l'IHM enfant
- [x] TICKET-047 — ❌ Annulé (2026-07-18) — UX — Défilement automatique (carrousel) arrêtable par l'enfant
- [x] TICKET-056 — ❌ Annulé (2026-07-18) — R&D — Exploration client lourd natif (PyQt5/Kivy) — décision projet 2.0

- [x] TICKET-017 — monitoring — Export Prometheus (métriques batterie/écoute) (2026-07-18)
      - Nouvel endpoint `web/metrics.php` (format d'exposition texte Prometheus, sur le modèle de `health.php` — pas d'authentification, réseau local uniquement)
      - Batterie (source `data/battery_stats.json`, déjà écrit par `battery_tracker.py`) : `hechicero_battery_level_percent`, `_charging`, `_voltage_volts`, `_current_milliamps`, `_power_watts`, `_screen_on`, `_estimated_autonomy_minutes[_live]`, `_cycles_recorded`, `_stats_age_seconds` (fraîcheur de la mesure)
      - Santé système (mêmes checks que `health.php`) : `hechicero_disk_used_percent`, `hechicero_disk_free_bytes`, `hechicero_mpd_up`, `hechicero_up`
      - Écoute (source `data/tracking.db`, déjà écrit par `play_tracker.py`) : compteurs cumulés `hechicero_listen_seconds_total{langue,type}` (podcast/radio × fr/es), `hechicero_episodes_completed_total`, `hechicero_play_sessions_total` ; gauge `hechicero_headphone_seconds_today` (remise à zéro quotidienne, cohérent avec le dashboard fatigue auditive existant)
      - Aucune nouvelle collecte : réutilise entièrement les données déjà produites par `battery_tracker.py`/`play_tracker.py` — le ticket portait sur l'export, pas sur de nouvelles métriques
      - Résilience : une erreur SQLite (base verrouillée/absente) n'empêche pas l'export des métriques batterie/santé (`try/catch` isolé, expose `hechicero_tracking_db_error` à la place)
      - ✅ **Validé en conditions réelles par Thomas le 2026-07-18** (`curl http://192.168.1.86/metrics.php`), 2 bugs trouvés au premier run et corrigés dans la foulée :
        - `hechicero_battery_stats_age_seconds` à -7185 (au lieu d'un petit positif) : `battery_tracker.py` écrit `last_updated` en heure locale naïve (`datetime.now()`, pas d'offset UTC) ; PHP l'interprétait par défaut en UTC → décalage ~2h (CEST). Fix : `date_default_timezone_set('Europe/Paris')` dans `metrics.php`. Confirmé après fix : `age_s=33`
        - `hechicero_headphone_seconds_today` à -30.452 (temps d'écoute casque négatif, impossible) : bug pré-existant dans `play_tracker.py`, 3 endroits calculaient `elapsed - open_elapsed_offset` sans le clamp à 0 déjà présent ailleurs dans le fichier (cas typique : repeat/single qui boucle sur le même fichier, l'`elapsed` MPD retombe à ~0 avant que l'event de bouclage soit traité par le tracker → `listened_s` négatif écrit tel quel en base). Ce bug corrompait déjà silencieusement le dashboard fatigue auditive existant (`dashboard.php`/`tracking.php`), pas seulement ce nouvel export. Fix : `max(0.0, ...)` aux 3 endroits (heartbeat, mixer-only, fermeture de session) + défense en profondeur `MAX(0, ...)` dans la requête SQL de `metrics.php`. Confirmé après fix : `16.913`
        - Correctif ponctuel donné à Thomas pour les lignes déjà corrompues en base : `sqlite3 data/tracking.db "UPDATE play_events SET listened_s = 0 WHERE listened_s < 0;"`
      - Fichiers modifiés : `web/metrics.php` (créé), `scripts/play_tracker.py` (fix clamp)
      - 🗑️ **`web/metrics.php` SUPPRIMÉ le 2026-08-17, sur décision de Thomas** : « je ne sais pas à quoi sert metrics.php donc on le vire. » Aucun Prometheus n'a jamais été installé, donc rien ne lisait cet export — c'était du code mort en attente d'un serveur que personne n'avait demandé. Le code mort est une source de pannes latentes et de diagnostics égarés ; il pesait aussi sur le contrôle de vie privée (un fichier de plus à relire à chaque passe).
        - **Ce qu'on garde du ticket, et qui vaut plus que l'export** : les deux bugs qu'il a fait remonter le 2026-07-18 sont dans `play_tracker.py`, pas dans `metrics.php`. Le clamp `max(0.0, …)` aux trois endroits corrigeait un temps d'écoute négatif qui **corrompait déjà silencieusement le dashboard de fatigue auditive**, indépendamment de Prometheus. Ce correctif reste en place.
        - ⏰ **Et il documentait déjà le piège d'horloge de TICKET-127** : `battery_tracker.py` écrit `last_updated` en heure locale naïve, PHP l'interprétait en UTC → 2 h d'écart. `metrics.php` le contournait avec un `date_default_timezone_set('Europe/Paris')` local. **En le supprimant, on perd ce contournement mais pas le problème** : l'incohérence PHP-en-UTC / Python-en-local reste vraie pour tout le projet. C'est ce qui a fait lire « 07:52 » au lieu de « 09:52 » ce matin.
        - ➡️ **Ouvre TICKET-129** : régler le fuseau de PHP à la source plutôt que fichier par fichier.
      - ➡️ **Si l'envie de courbes revient un jour** (usure des cellules sur six mois, temps d'écoute par langue), tout est reconstructible : les données sont déjà produites par `battery_tracker.py` et `play_tracker.py`, et le détail des métriques est conservé ci-dessus. Le ticket ne perd rien, il se met en veille.

      - ➡️ **TICKET-129** (fuseau UTC de PHP) a été **déplacé en priorité haute** le 2026-08-17 : il était rangé ici, dans la section « Terminé », alors qu'il est ouvert.

- [x] TICKET-030 — feature — Égaliseur audio paramétrable (2026-07-18)
      - Décisions prises avec Thomas avant codage (cf. [[project_hechicero_ticket030_eq]] en mémoire) : scope complet (page admin dédiée + 2 profils indépendants HP/casque), moteur **alsaequal** (plugin ALSA/LADSPA, `libasound2-plugin-equal` — solution native recommandée par HiFiBerry elle-même pour ce matériel, cf. guide officiel https://www.hifiberry.com/docs/software/guide-adding-equalization-using-alsaeq/), granularité **10 bandes natives** (31Hz→16kHz, pas de regroupement en 3 curseurs)
      - Config système : deux instances alsaequal indépendantes dans `/etc/asound.conf` (`ctl.eqhp`/`ctl.eqcasque`, chacune enroulant respectivement `hw:CARD=sndrpihifiberry` et `hw:CARD=Audio`), `mpd.conf` pointé sur ces devices virtuels au lieu du hardware direct — détail complet et **validé** dans `docs/20-SETUP_SYSTEME.md` §6.4
      - `scripts/audio_eq_apply.py` : lit `data/audio_eq.json` (gains en dB, -12..+12, par bande × par profil) et les applique via `amixer -D eqhp/eqcasque sset ...` — nécessaire car alsaequal ne persiste rien entre deux boots. `scripts/audio_eq_apply.service` réapplique au démarrage
      - `web/admin/audio_eq.php` (page Expert) : 2 onglets HP/casque, 10 curseurs verticaux par onglet, 4 préréglages pré-chargeables (Plat, Basses renforcées, Voix claire, Chaud et rond)
      - Loudness (compensation Fletcher-Munson à bas volume) **non implémenté** — hors du scope décidé avec Thomas, à traiter séparément si besoin
      - ✅ **Validé en conditions réelles le 2026-07-18 — Thomas confirme : "l'équaliseur change vraiment, le son est agréable !"**. Trois bugs réels trouvés et corrigés en direct sur le Pi (post-mortem complet dans `docs/20-SETUP_SYSTEME.md` §6.4 et §6.4.1, à relire avant de retoucher cette config) :
        1. **Noms de contrôle amixer** : pas `31Hz` comme deviné, mais `'00. 31 Hz'` (préfixe numérique + espace) — confirmé via `--list-controls`, corrigé dans `BAND_LABELS`. `cset name=...` (interface raw) ne fonctionne pas sur ces contrôles "simples" → `sset` obligatoire
        2. **"Indépendance" cassée par un détail alsaequal non documenté ailleurs** : par défaut alsaequal stocke son état dans `$HOME/.alsaequal.bin` (par utilisateur, pas par ctl nommé) — `eqhp`/`eqcasque` semblaient partager leur état car tous les tests tournaient sous `thomas`. Fix : paramètre `controls` avec un chemin distinct par instance (`data/alsaequal_hp.bin`/`data/alsaequal_casque.bin`) — réglé ce même problème ET l'erreur de permission `www-data` (qui a `$HOME=/var/www`, non inscriptible) d'un coup. `www-data` ajouté au groupe `audio`
        3. **Incident en cascade** : pré-créer les fichiers `controls` avec `touch` (fichier vide) fait planter alsaequal en `SIGBUS` — arrivé pendant que MPD tournait, ce qui a fait planter MPD 3× en rafale et grillé le disjoncteur anti-boucle de l'unité systemd **`mpd.socket`** (distincte de `mpd.service`, activation par socket). L'IHM tactile a été inutilisable ~20 min (`radio.php` parle à MPD via `/run/mpd/socket`, contrairement à `mpc` en CLI qui passe par TCP et semblait donc fonctionner) — récupéré via `systemctl reset-failed mpd.socket` + séquence stop/start précise, procédure documentée en §6.4.1 pour la prochaine fois
      - Fichiers créés : `web/admin/audio_eq.php`, `scripts/audio_eq_apply.py`, `scripts/audio_eq_apply.service` ; modifiés : `web/index.php`, `web/dashboard.php`, `web/admin/battery_dashboard.php` (nav), `.gitignore` (`data/audio_eq.json`), `docs/20-SETUP_SYSTEME.md`, `docs/70-SERVICES_SYSTEMD.md`

- [x] TICKET-011 — sec — Durcir unités systemd (`ProtectSystem`, `NoNewPrivileges`) (2026-07-19)
      - Déploiement volontairement progressif après la soirée TICKET-030 (services testés dans l'ordre : `wifi_watch`/`play_tracker` → `battery_tracker`/`audio_eq_apply` → `wifi_roam`/`button_toggle_test` → `buttons_daemon`/`battery_watchdog`), un lot validé en conditions réelles avant de passer au suivant
      - Ajouté aux 8 `.service` dans `scripts/` : `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=strict` + `ReadWritePaths=/home/thomas/hechicero/data`, `ProtectHome=read-only` — tous ces services ne lisent/écrivent que dans `data/`, rien ailleurs
      - ⚠️ **Volontairement PAS de `PrivateDevices=true`** sur `buttons_daemon`/`button_toggle_test` (GPIO) ni sur `audio_eq_apply` (`/dev/snd`, carte son) — cette option aurait cassé l'accès matériel, exactement le genre de piège vécu la veille au soir avec l'égaliseur (fichier `controls` vide → SIGBUS → cascade jusqu'à `mpd.socket`). `ProtectSystem`/`ProtectHome` n'affectent pas `/dev`, `/proc`, `/sys` — seul `PrivateDevices` le ferait
      - Validation en conditions réelles pour 7 des 8 services (logs qui continuent de s'écrire après redémarrage, bouton physique play/stop testé, égaliseur toujours accessible via `amixer`) — voir [[project_hechicero_ticket011_hardening]] en mémoire pour le détail service par service
      - ⏳ **`battery_watchdog` : chemin `sudo shutdown -h now` non testé** — son flag `--simulate-critical` s'arrête juste avant l'exec du shutdown (ne teste que l'écriture de `data/last_session.json`), impossible de valider sans provoquer un vrai arrêt. Le raisonnement (exec d'un binaire ne nécessite qu'un accès lecture+exécution, compatible avec `ProtectSystem=strict` en lecture seule) est solide mais pas prouvé empiriquement. Si besoin d'une vraie preuve un jour : baisser temporairement `critical_level_percent` dans `data/config.json` au-dessus du niveau de batterie courant, en présence de Thomas pour rallumer ensuite
      - Fichiers modifiés : les 8 `.service` dans `scripts/` (`battery_tracker`, `play_tracker`, `battery_watchdog`, `buttons_daemon`, `button_toggle_test`, `wifi_roam`, `wifi_watch`, `audio_eq_apply`)

- [x] TICKET-102 — bug — Écran de veille et coupure d'écran cassés après l'intégration hardware finale (2026-07-08 → corrigé 2026-07-09)
      - Épisode 1 (2026-07-08 matin) : port HDMI en dur (`HDMI-A-2`) alors que l'écran était sur `HDMI-A-1` après l'intégration → `scripts/screen_dpms.sh` corrigé. Puis rendu Chromium figé (glitch au changement de port) → résolu par relance kiosk
      - Épisode 2 (2026-07-08 soir) : récidive avec un symptôme différent (écran réactif au toucher, donc pas de figement cette fois) → tracer temporaire installé (`logSleepEvent()` → action `sleep_log` de `radio.php` → `data/sleep_debug.log`) à la demande explicite de Thomas après plusieurs occurrences du même bug ("on va arrêter de penser que c'est un souci de pas de bol")
      - ✅ **Cause réelle trouvée le 2026-07-09** grâce au tracer : `checkParentalTime()` (vérif horaires parentaux, `setInterval` 30s) rechargeait la config et appelait `resetSleepTimer()` **à chaque tick, inconditionnellement** — dès que `sleep_delay` dépassait 30s, ce refresh périodique repoussait perpétuellement le timer d'inactivité, qui ne pouvait alors **jamais** atteindre son délai naturellement. C'était un vrai bug de logique, pas du hasard ni un Chromium capricieux
      - **Fix** : `applySleepConfig()` (`web/lecteur/index.html`) ne reset le timer que si la config a réellement changé (ou 1er chargement), plus à chaque refresh périodique sans rapport avec une vraie activité. Confirmé par Thomas le soir même : veille déclenchée exactement 120s après le dernier clic réel
      - Traceur (`sleep_log`/`logSleepEvent()`) laissé en place pour l'instant, à retirer une fois le fix confirmé stable dans la durée
      - Fichiers modifiés : `scripts/screen_dpms.sh`, `web/lecteur/radio.php` (action `sleep_log`), `web/lecteur/index.html` (`logSleepEvent()` + fix `applySleepConfig()`), `docs/30-LECTEUR.md`, `docs/70-SERVICES_SYSTEMD.md` (§6, wlopm→wlr-randr + table des services)
      - Découverte annexe (pas liée au bug, séparée en TICKET-106) : un objet git corrompu dans `~/hechicero`

- [x] TICKET-103 — bug — Coupure du flux webradio après une pause/reprise (2026-07-09)
      - Symptôme : sur une webradio, pause puis reprise relançait bien le son, mais le flux finissait par se couper peu après — MPD bufferisait en arrière-plan pendant la pause, `play` rejouait un buffer devenu obsolète.
      - **Fix** : action `pause` de `radio.php` distingue webradio/podcast — `stop` complet + mémorisation de l'URL sur pause webradio, reconnexion fraîche (`mpd_add_and_play()`) à la reprise au lieu de rejouer le buffer figé. Podcasts inchangés (pause/reprise à la même position).
      - ✅ Clos le 2026-07-17 (confirmé par Thomas)
      - Fichier modifié : `web/lecteur/radio.php`

- [x] TICKET-107 — bug/feature — Ingestion RSS : conserver les épisodes qui sortent du flux (surtout "Les Odyssées")
      - Trouvé le 2026-07-17 en auditant les orphelins post-ingestion (suite TICKET-104/105) : `ingest.py` reconstruisait `meta.json` **entièrement** à partir du flux RSS courant à chaque passage (pas de fusion avec l'historique). Résultat : tout épisode que le diffuseur (Radio France notamment) retire ou retitre dans son flux disparaissait silencieusement de `data.json`, alors même que le fichier audio/image restait sur le disque (jamais supprimé, invariant 1.5) — inaccessible depuis le lecteur.
      - Décision Thomas (2026-07-17) : conserver les épisodes déjà téléchargés en priorité, tant pis si ça garde occasionnellement une bande-annonce déjà présente dans un ancien `meta.json`.
      - ✅ Implémenté : `scripts/rss_ingest/parser.py::merge_episodes()` fusionne l'historique local (`meta.json` existant) avec le flux frais avant toute troncature `max_episodes` — la version fraîche l'emporte en cas de même id (métadonnées à jour), le reste est conservé tel quel et re-trié (même logique saison/numéro/date que `parse_rss()`). Câblé dans `ingest.py::ingest()`.
      - ✅ **Validé en conditions réelles le 2026-07-17** : ingestion complète relancée sur le Pi. Découverte en creusant les orphelins restants (`aladinetlesorciermalfique`, `shhrazadeconteusedegnie`, `lesincroyablesaventuresdesindbadlemarin`, `lestroisprincesamoureux`) : ces épisodes n'étaient déjà plus dans `meta.json` **avant** ce correctif (perdus lors d'une ingestion antérieure) — la fusion ne peut pas les récupérer rétroactivement, seulement empêcher que ça se reproduise désormais. Mais bonne surprise : Radio France les a en fait **republiés sous un nouveau titre/id** dans une saison "Les 1001 nuits" (`Les 1001 nuits 1/4 : Shéhérazade conteuse de génie`, `2/4 : Aladin et le sorcier maléfique`, `3/4 : Les incroyables aventures de Sindbad le marin`, `4/4 : Les trois princes amoureux`) et "Peter Pan et Wendy" → "Wendy & Peter Pan" — donc bien présents dans `data.json`/le lecteur, juste sous un id différent. Seuls restent introuvables : `odysesdudimanche03aot2025`/`odysesdudimanche20juillet2025` (rediffusions "best of" du dimanche, probablement non republiées telles quelles) — fichiers conservés sur disque, pas de perte, juste plus référencés.
      - Anciens fichiers orphelins (`aladinetlesorciermalfique.mp3` etc., doublons de contenu maintenant présent sous un nouvel id) : nettoyage disque optionnel, pas urgent.
      - ⚠️ Effet de bord accepté : plus de purge automatique, l'archive locale ne fait que grossir avec le temps (pas de souci d'espace disque identifié à ce stade, mais à surveiller si un flux change radicalement d'un coup)
      - Fichiers modifiés : `scripts/rss_ingest/parser.py`, `scripts/rss_ingest/ingest.py`, `docs/40-BACKEND_RSS.md`

- [x] TICKET-085 — infra — Sauvegarde de la carte SD (ghost durci, manuel uniquement)
      - Doc complète : `docs/85-SAUVEGARDE_RESTAURATION.md` (restauration Windows pas-à-pas + mise en place système)
      - Conçu et implémenté le 2026-07-03 — étendu en cours de session d'un simple script manuel vers un système complet, puis **simplifié le même jour** : pas de sauvegarde quotidienne automatique ("on ne sauvegarde que les évolutions majeures, soyons économes") — **durcie uniquement**, déclenchée à la main via l'admin :
          • Une seule sauvegarde vers NAS Freebox (SMB/CIFS) : **durcie**, remplacée quand Thomas valide un état stable via l'admin (bascule atomique — jamais d'état sans version durcie valide)
          • `scripts/backup_manager.py` — orchestration complète (montage NAS, `dd | gzip`, état JSON, bascule atomique)
          • `data/backup_config.json` (non-secret, versionné) + `/etc/hechicero-nas-credentials` (secret, root uniquement, hors dépôt)
          • Règle sudoers dédiée pour laisser l'admin web déclencher une validation durcie (root requis pour lire `/dev/mmcblk0` et monter le NAS) sans donner un accès root complet à www-data
          • Page admin `web/admin/backup_dashboard.php` : version durcie actuelle, taille, bouton de validation — lien visible **seulement en mode Expert** de l'admin principale (persona parent geek, pas l'autre parent)
          • `README.md` régénéré automatiquement sur le NAS à chaque sauvegarde (secours si le dépôt n'est pas accessible)
          • **Aucun SSH requis à l'usage** : clic sur "Valider une nouvelle version durcie" dans l'admin → `index.php` déclenche `backup_manager.py validate` en tâche de fond via la règle sudoers → montage NAS, ghost, bascule atomique, tout est géré côté serveur. SSH n'est nécessaire qu'une seule fois, à la mise en place initiale (§3 de la doc : fichier d'identifiants, paquets, règle sudoers) — jamais ensuite.
      - Scripts manuels créés initialement (`scripts/ghost_sd_prepare.sh`, `scripts/ghost_sd_backup.sh`) conservés pour un usage ponctuel/disque externe, mais le flux normal passe désormais par `backup_manager.py`
      - Notes réseau utiles pour la suite : `mafreebox.freebox.fr` résout vers une IP publique Free depuis le Pi (pas la Freebox locale) → utiliser l'IP de la passerelle locale (`ip route`, voir `data/backup_config.json` pour la valeur retenue — pas republiée ici, dépôt public) ; montage CIFS anonyme (`guest`) suffit pour lister les partages mais pas pour écrire, un compte Freebox est nécessaire
      - ⚠️ `dd` lit le disque système pendant qu'il tourne (pas d'arrêt des services) — snapshot pas garanti parfaitement cohérent
      - ✅ Déploiement sur le Pi réel terminé le 2026-07-03 : fichier d'identifiants, règles sudoers (www-data + thomas), paquets, hook git installé. Premier ghost réel fait (~107 GiB), enregistré comme durcie initiale. Testé de bout en bout sans montage manuel préalable (`sync_private` remonte le NAS tout seul via les identifiants).
      - ⏳ Reste : premier clic "valider durcie" *depuis l'admin web* (le tout premier a été fait en ligne de commande faute de bouton pas encore cliqué) — sinon le système est pleinement opérationnel
      - Fichiers systemd `hechicero-backup-daily.service`/`.timer` créés puis abandonnés (design quotidien annulé) — à supprimer du dépôt (`git rm etc/systemd/system/hechicero-backup-daily.*`)
      - **Ajout 2026-07-03 (même session)** : `private/` (hors git, jamais sur GitHub — réflexion perso, futurs contenus non publics type easter egg) synchronisé vers un dossier dédié du NAS, automatiquement à chaque `git commit` via un hook `.git/hooks/post-commit` (template versionné : `scripts/git_hooks_post_commit.sh`) — nouvelle commande `backup_manager.py sync_private`, règle sudoers dédiée pour l'utilisateur `thomas` (voir `docs/85-SAUVEGARDE_RESTAURATION.md` §3.3, §3.6, §5). Zéro SSH à l'usage, comme pour la durcie. `rsync` sans `--delete` : n'efface jamais rien côté NAS.
      - Penser à vérifier/documenter aussi les configs système hors git avant tout (cf. [[project_backups]] en mémoire : UPower.conf, mpd.conf, kiosk.sh, Apache vhosts, Plymouth theme) — capturées dans le ghost complet, mais bon à savoir si restauration partielle

- [x] TICKET-108 — bug — Clic sur un épisode joue un épisode d'un autre podcast (2026-07-18)
      - Symptôme rapporté par Thomas : dans la liste d'épisodes de "Tina", cliquer sur un épisode lançait un épisode des "Odyssées du Louvre".
      - Cause : `currentPodcast` (variable globale JS) servait à deux choses distinctes — le podcast dont la liste est affichée (posé par `openPodcast()`) ET le podcast réellement en cours de lecture sur MPD (resynchronisé toutes les 3s par `syncNowPlaying()`, nécessaire pour refléter les changements faits par bouton physique GPIO, TICKET-091). La boucle de poll qui déclenche cette resynchro n'est jamais arrêtée en quittant l'écran lecteur : elle continue de tourner en fond même en navigant vers la liste d'épisodes d'un autre podcast, et réécrit silencieusement `currentPodcast`. Un tap sur une ligne pendant cette fenêtre utilisait alors le mauvais `currentPodcast` avec l'index de la ligne cliquée.
      - **Fix** : `renderChapters()` capture le podcast réellement parcouru dans une variable locale (`browsedPodcast`, figée à l'affichage, immune à la resynchro en arrière-plan) et la réaffirme sur `currentPodcast` juste avant `playTrack()`, dans le handler de clic de chaque ligne.
      - ✅ Clos le 2026-07-18 (confirmé par Thomas)
      - Fichier modifié : `web/lecteur/index.html` (`renderChapters()`)

- [x] TICKET-010 — infra — Rotation logs (2026-07-18)
      - Deux fichiers grossissaient sans limite : `/tmp/hechicero_ingest.log` (cron RSS nocturne) et `data/sleep_debug.log` (traceur TICKET-102, toujours actif — un ajout par événement écran de veille côté lecteur).
      - Les logs des services systemd (`battery_tracker`, `battery_watchdog`, `play_tracker`, `buttons_daemon`, `hechicero-idle`) ne sont pas concernés : ils passent par `journalctl`, qui a sa propre rétention (`journald.conf`).
      - **Fix** : `scripts/hechicero-logrotate.conf` (nouveau, versionné) — rotation quotidienne, `copytruncate` (pas de signal process nécessaire), 7 jours pour le log d'ingestion, 14 jours pour le traceur veille.
      - ✅ Clos le 2026-07-18
      - Fichiers modifiés : `scripts/hechicero-logrotate.conf` (nouveau), `docs/70-SERVICES_SYSTEMD.md` (§7quater)
      - À installer côté Pi : `sudo cp scripts/hechicero-logrotate.conf /etc/logrotate.d/hechicero`

- [x] TICKET-104 — bug — Podcast TINA : images identiques, ordre incohérent, navigation bloquée en fin de saison (2026-07-09)
      - Symptômes rapportés par Thomas (généralisables à tous les podcasts RSS, pas seulement TINA — ex. Professeur Caillou) : images toujours identiques sur l'écran lecteur, épisodes affichés à l'envers, navigation suivant/précédent bloquée en fin de saison
      - Diagnostic : `web/lecteur/index.html` fixait `player-art.src` sur la jaquette du podcast entier au lieu de `ch.image` (image de l'épisode/saison) ; `parser.py` ne triait ni dédupliquait les épisodes (flux RSS pas fiable, saisons dupliquées avec dates incohérentes) ; navigation bloquée en conséquence directe de l'ordre incohérent
      - **Fix implémenté** : `ch.image || podcast.image` dans `index.html` ; dédup par id + tri chronologique à deux niveaux (saison puis numéro de titre/date) dans `parser.py` ; filtre des bandes-annonces et auto-promo Radio France ; troncature `max_episodes` par la fin (`[-max:]`) ; suppression des `reverse()` devenus inutiles
      - ✅ Suite du diagnostic (2026-07-09) : jaquette fausse (résolu, images à retélécharger), lien symbolique `web/podcasts` manquant vers `~/hechicero/podcasts` créé (404 corrigés), filtre promo élargi à "appli(cation) Radio France", tri intra-saison par numéro de titre (résout l'ordre 2 avant 1)
      - ✅ **Validé le 2026-07-17** : ingestion complète relancée sur les 23 podcasts, `check_integrity.py` confirme 0 erreur — dédup/tri/filtre tous corrects, plus de doublons ni d'ordre incohérent
      - Fichiers modifiés : `web/lecteur/index.html`, `web/lecteur/radio.php`, `scripts/rss_ingest/parser.py`, `scripts/rss_ingest/ingest.py`

- [x] TICKET-105 — bug — Synchronisation admin en échec : "Permission denied" sur meta.json.tmp, plante toute la synchro (2026-07-09)
      - Symptôme : la synchro déclenchée depuis l'admin web (tourne en `www-data`) s'arrêtait en erreur fatale à 10/22 podcasts, `PermissionError` sur `lesodysseesduchateaudeversailles/meta.json.tmp` — permission de groupe manquante sur ce dossier précis vs l'ingestion cron (tourne en `thomas`, `umask 002`)
      - **Fix implémenté (robustesse)** : chaque podcast traité dans son propre bloc `try/except` dans `ingest.py` — un podcast en échec n'interrompt plus les suivants ; `data.json` reconstruit à partir de tous les `meta.json` sur disque
      - ✅ **Cause racine corrigée le 2026-07-17** : `chgrp -R www-data` + `chmod -R g+w` sur le dossier fautif, confirmé par `check_integrity.py` (le podcast passe en `[OK]`) et une synchronisation complète des 23 podcasts sans erreur de permission
      - Fichier modifié : `scripts/rss_ingest/ingest.py`

- [x] TICKET-057 — UX/infra — Démarrage rapide de l'IHM enfant
      - Chromium mettait plusieurs secondes à démarrer après le boot
      - ✅ Clos le 2026-07-17 (confirmé par Thomas)

- [x] TICKET-068 — content — Typo ID podcast `bestiolesossiles` (manque le 'f')
      - ID interne dans `podcasts.json` : `bestiolesossiles` (manque le 'f' de "fossiles")
      - ✅ Clos le 2026-07-17 (décision Thomas) : accepté tel quel — le `label` affiché ("Les Bestioles fossiles") est correct, seul l'`id` technique (jamais visible par l'enfant ni dans l'admin) a la coquille. Renommer impliquerait de migrer le dossier audio sur disque pour un bénéfice nul, pas fait.

- [x] TICKET-087 — feature/parental — Limiteur d'exposition sonore
      - ✅ Clos le 2026-07-17 (décision Thomas) : le tracking `play_events.volume_pct` (moyenne MPD par session, enregistré depuis session 9) est jugé suffisant tel quel. Portée réduite : pas de dashboard "volume moyen par jour/podcast" ni d'avertissement de dépassement dans l'IHM enfant — abandonnés, pas nécessaires.

- [x] TICKET-001 — infra — Structure projet + liens Apache
- [x] TICKET-002 — infra — Monitoring batterie (INA219 + service systemd)
- [x] TICKET-003 — audio — HiFiBerry Amp4 + MPD opérationnel
- [x] TICKET-004 — content — Gestion multi-podcasts FR/ES
- [x] TICKET-005 — web — Interface d'administration complète (`web/index.php`)
- [x] TICKET-007 — web — Interface configuration `podcasts.json` (via admin)
- [x] TICKET-012 — test — Tests unitaires ingestion RSS
- [x] TICKET-014 — docs — Procédure de mise à jour documentée
- [x] TICKET-022 — web — Lecteur embarqué IHM enfant (`web/lecteur/index.html`)
- [x] TICKET-023 — audio — Son de démarrage (chime)
      - ✅ Accord grave, généré en WAV via `generate_chime.py`, joué via MPD
      - ✅ `kiosk.sh` : Chromium en arrière-plan, chime après sleep (délai réglable)
      - ✅ Config `chime_enabled` / `chime_volume` dans admin
- [x] TICKET-024 — audio — Lecture Webradio
- [x] TICKET-025 — backend — Ingestion RSS (Radio France)
- [x] TICKET-026 — backend — Génération automatique de `data.json`
- [x] TICKET-027 — infra — Ingestion nocturne (cron 3h, `umask 002`)
- [x] TICKET-028 — web — Nettoyage et finalisation du lecteur
- [x] TICKET-029 — backend — Quotas stockage (`max_episodes`)
- [x] TICKET-032 — infra — Installation Raspberry Pi OS avec bureau
- [x] TICKET-033 — hardware — Installation écran tactile + tests IHM
- [x] TICKET-034 — web — Activation du volume logiciel MPD
- [x] TICKET-035 — docs — Mise à jour des documents essentiels
- [x] TICKET-036 — web — Mode "grands boutons" optimisé tactile
- [x] TICKET-038 — hardware — Bouton physique RUN pour démarrage du Raspberry Pi 5
      - ✅ Installé : bouton momentané chromé M16, fils rouge+bleu → broches RUN Pi 5
      - Logé dans un trou ∅16mm de la tranche supérieure chromée
- [x] TICKET-039 — web — Démarrage automatique du lecteur (mode kiosque)
- [x] TICKET-040 — web — `app.js` supprimé (code mort)
- [x] TICKET-041 — UX — Appui sur image = pause/lecture
- [x] TICKET-042 — UX — Barre de progression + scrubbing tactile
- [x] TICKET-043 — UX — Reprise automatique de la position de lecture
- [x] TICKET-044 — UX — Flèches épisode suivant / précédent
- [x] TICKET-045 — UX — Taille des jaquettes ≥ 300×300 px
- [x] TICKET-049 — web — Images podcasts téléchargées automatiquement à l'ingest
- [x] TICKET-050 — UX — Refonte visuelle IHM enfant (5 écrans, polish)
- [x] TICKET-051 — web — Affichage batterie dans la barre de statut
- [x] TICKET-052 — UX — Barre de statut : heure + batterie
- [x] TICKET-053 — UX — Grille 2 colonnes + scroll tactile
- [x] TICKET-054 — backend — Jaquettes par épisode dans `data.json`
- [x] TICKET-055 — feature — Statistiques d'écoute + dashboard parent
      - ✅ Session 9 : refonte tracking event-driven côté serveur (`play_tracker.py`, MPD idle)
      - ✅ `volume_pct` (moyenne MPD) enregistré par session pour futur limiteur d'exposition
      - ✅ Bug radio corrigé : auto-next ne se déclenche plus quand on lance la webradio pendant un podcast
- [x] TICKET-059 — backend — Durée des épisodes via ffprobe
      - ✅ `fix_durations.py` : 365 épisodes corrigés
      - ✅ `downloader.py` : `probe_duration()` appelé après chaque téléchargement
- [x] TICKET-060 — UX — Webradio en premier dans la grille
- [x] TICKET-062 — content — Ajout 11 podcasts FR + 3 podcasts ES
- [x] TICKET-063 — UX — Barres de progression synchronisation
- [x] TICKET-064 — backend — Cover podcast téléchargée automatiquement à l'ingest
- [x] TICKET-065 — infra — Permissions Pi + cron nocturne
- [x] TICKET-066 — infra — SSL proxycast.radiofrance.fr
- [x] TICKET-067 — infra — Robustesse logs ingest
- [x] TICKET-069 — UX — Enchainement automatique des épisodes
- [x] TICKET-071 — feature/parental — Contrôle parental : grille horaire + verrou langue
      - ✅ `isNowAllowed()`, `isLangAllowed()`, polling 30s, retour home en fin de plage
- [x] TICKET-072 — bug/UX — Mini-lecteur affiche radio au lieu du podcast en cours
- [x] TICKET-073 — bug/audio — Chime race condition → déplacé dans `kiosk.sh`
- [x] TICKET-074 — bug/UX — Screensaver : refonte complète 6 modes Great Vibes
- [x] TICKET-075 — (fusionné avec TICKET-076)
- [x] TICKET-076 — UX/infra — Écran de démarrage Plymouth personnalisé (Great Vibes or)
- [x] TICKET-077 — UX — Écran de veille thémé Great Vibes (retro/modern/classic × horloge)
- [x] TICKET-078 — bug — Police Great Vibes cassée (woff2 4.5KB → TTF 445KB)
- [x] TICKET-070 — feature/analytics — Dashboard enrichi (funnel, heatmap, streak, top épisodes rejoués)
      - ✅ Tout implémenté dans `web/dashboard.php`
- [x] TICKET-080 — backend/infra — Service de collecte batterie (`scripts/battery_tracker.py`)
      - ✅ Mesure événementielle, corrélation MPD, écriture atomique, systemd actif
- [x] TICKET-081 — UX/admin — Dashboard alimentation parent (`web/admin/battery_dashboard.php`)
      - ✅ 6 blocs, Chart.js local, lien depuis l'admin
- [x] TICKET-082 — UX/enfant — Affichage autonomie + alertes 30/10 min IHM enfant
      - ✅ Temps restant, popup branchement, alertes non intrusives
- [x] TICKET-083 — infra/sécurité — Arrêt propre sur batterie critique
      - ✅ `scripts/battery_watchdog.py`, sauvegarde session, shutdown ordonné
- [x] TICKET-084 — backend — Modèle d'estimation d'autonomie (affinement progressif)
      - ✅ Ratios calculés après chaque cycle, `model_confidence` affiché
- [x] TICKET-086 — backend — Déduplication tracking JS vs play_tracker
      - ✅ Session 11 : 54 lignes de tracking JS supprimées de `web/lecteur/index.html`
- [x] TICKET-088 — bug/backend — `play_tracker.py` n'écrivait pas `listened_s` à la fermeture
      - MPD retourne `elapsed=0` quand l'état passe à "stop" → `listened_s` était systématiquement 0
      - Fix session 11 : `db_close_session` utilise `ts_end - ts_start` comme fallback si `listened_s == 0`
      - Fix session 12 : fallback capé à `duration_s` (évite `listened_s >> duration_s` si session laissée ouverte)
      - Fix DB session 12 : 10 lignes corrompues nettoyées (`listened_s` capé à `duration_s`)
      - ✅ `scripts/play_tracker.py` corrigé
- [x] TICKET-048 — backend — Script de vérification d'intégrité audio/images/data.json
      - ✅ `scripts/rss_ingest/check_integrity.py` : déjà implémenté (découvert session 12)
      - Détecte : fichiers manquants, orphelins, M4A déguisés, taille 0, divergences meta/data.json, covers absentes
      - `--podcast <id>` pour cibler un podcast ; exit code 0/1/2 (OK/WARN/ERR)
- [x] TICKET-008 — infra — Endpoint `/health` (monitoring externe)
      - ✅ Session 13 : `web/health.php` — JSON avec MPD, batterie, disque, ingest, uptime
      - HTTP 200 si tout OK, 503 si dégradé — batterie stale si > 5 min sans mise à jour
- [x] TICKET-089 — bug/backend — `battery_watchdog.py` : errno 121 code mort
      - Fix session 12 : réinitialisation INA219 déplacée à l'intérieur de `read_level()`
      - ✅ `scripts/battery_watchdog.py` corrigé
- [x] TICKET-117 — voir la section Terminé plus haut (ex-TICKET-090 « nettoyage fichiers morts », renuméroté le 2026-08-04 pour lever la collision avec le ticket batterie ci-dessous)
- [x] TICKET-096 — bug/infra — Hechicero s'éteignait au débranchement du chargeur
      - Cause : upower voyait la batterie INA219 à 0% (pas de driver ACPI) → HybridSleep au retrait du secteur
      - Fix : `CriticalPowerAction=Ignore` + `AllowRiskyCriticalPowerAction=true` dans `/etc/UPower/UPower.conf`
      - ✅ Config système hors git — à capturer dans TICKET-085 (ghost SD)
- [x] TICKET-097 — bug/infra — Extinction écran non fonctionnelle sur Pi 5 + labwc
      - `wlopm` échoue : `zwlr_output_power_management_v1` non supporté par HDMI-A-2
      - sysfs DRM `/sys/class/drm/card1-HDMI-A-2/dpms` en lecture seule même en root sur Pi 5
      - Fix : `scripts/screen_dpms.sh` utilise `wlr-randr --off/--on` (zwlr_output_management_v1)
      - ✅ `scripts/idle_screen.sh` mis à jour — pas de sudo requis
- [x] TICKET-099 — bug/ingest — acast 403 Forbidden : User-Agent manquant dans downloader.py
      - sphinx.acast.com bloquait les requêtes sans User-Agent → 0 MP3 téléchargés pour habiaunavez
      - Fix : `DEFAULT_HEADERS` avec User-Agent générique ajouté à toutes les requêtes
      - ✅ `scripts/rss_ingest/downloader.py` corrigé — habiaunavez 296 MP3 OK

- [x] TICKET-098 — bug/UX — Screensaver ne s'activait pas sur le kiosk Pi
      - Cause : écran tactile CTP `wch.cn USB2IIC_CTP_CONTROL` génère des `touchstart` fantômes sans `touchend`
      - Ces events réinitialisaient le timer screensaver en permanence
      - Fix : `wakeUp` n'écoute plus que `click` + `keydown` (un vrai tap génère `click` après `touchend`)
      - ✅ `web/lecteur/index.html` mis à jour
      - ✅ `play_tracker.py` (serveur, MPD idle) est désormais seule source de vérité
- [x] TICKET-100 — bug/UX — Radios et podcasts non instantanés sur le lecteur
      - Cause : lecteur chargeait `data.json` une seule fois au boot ; radios attendaient le cron de 3h
      - Fix PHP : `add/edit/delete_radio` → `sync_radios_to_data_json()` met `data.json` à jour immédiatement
      - Fix PHP : `delete_podcast` → retrait immédiat de `data.json`
      - Fix PHP : `add_podcast` → ingest ciblé `--podcast <id>` déclenché en background
      - Fix JS : `openRadioCatalog()` et `goToPodcasts()` rechargent `data.json` à chaque visite
      - Fix JS : `setInterval` 5 min pour config/parental (veille, contrôle parental) sans redémarrage kiosque
      - ✅ `web/index.php` + `web/lecteur/index.html` mis à jour

- [x] TICKET-061 — content — Saison 2 Professeur Caillou
      - ✅ Session 11 : 13 épisodes S2 déjà présents dans `data.json` — rien à faire
- [x] TICKET-088 — bug/tracking — `listened_s` corrompu → épisodes à 56071% de complétion
      - ✅ Session 12 : fallback `ts_end - ts_start` non borné → valeur cap à `min(elapsed, duration_s)`
      - ✅ Cap SQL dans `tracking.php` : `MIN(listened_s * 100.0 / duration_s, 100.0)`
      - ✅ Nettoyage DB : `UPDATE play_events SET listened_s=duration_s WHERE listened_s>duration_s`
- [x] TICKET-089 — bug/UX — Écran ne s'éteint pas malgré l'option activée en admin
      - ✅ Session 12 : `swayidle` mourait au boot (Wayland pas prêt), PID mort jamais relancé
      - ✅ `idle_screen.sh` : détection process mort via `kill -0 $PID`, relance automatique
- [x] TICKET-090 — bug/batterie — 51 micro-cycles factices + autonomie 12h (réelle 1.5–3h)
      - ✅ Session 12 : `charge_threshold_ma` 50 → 300 mA (élimine oscillations phase CV)
      - ✅ Formule linéaire → courbe LiPo interpolée (`battery_common.py`)
      - ✅ Filtre cycles valides : `consumed ≥ 3%` ET `duration ≥ 5 min` ET pas `invalid`
      - ✅ Estimation live basée sur `current_ma` INA219 + `battery_capacity_mah = 6600` mAh
      - ✅ Dashboard alimentation : n'affiche que les cycles valides, "Activité 24h" remplace cycle en cours
      - ✅ `battery_history.json` réinitialisé (51 cycles invalides effacés)

- [x] TICKET-095 — hardware — Vérifier courant max USB-C à réception
      - ✅ Fermé 2026-07-08 — ≥3A confirmé à réception, composant XMSJSIY gardé tel quel
- [x] TICKET-092 — hardware — Trouver prise USB-A panel mount clavier de secours
      - ❌ Annulé 2026-07-08 — accès direct au Raspberry Pi en ouvrant le boîtier si besoin de debug, pas besoin de port dédié
- [x] TICKET-094 — hardware — Trancher format switch général batterie (fente 25×8mm)
      - ❌ Annulé 2026-07-08 — plus besoin d'un switch général batterie
- [x] TICKET-093 — hardware — Trouver LED témoin alimentation ∅6mm
      - ❌ Annulé 2026-07-08 — pas envie de le faire
- [x] TICKET-091 — hardware — Choisir méthode interface GPIO boutons-poussoirs
      - Décision : (1) GPIO direct Pi 5 + `RPi.GPIO`, en **polling** (10ms) — pas MCP23017 I²C ni Pico USB HID, ni interruptions (`add_event_detect()` peu fiable sur Pi 5/RP1, 1er appui détecté seul)
      - Validée par bring-up le 2026-07-06/07 (9 broches, anti-rebond confirmé), puis par le mapping GPIO ↔ bouton et le service systemd définitif de TICKET-101
      - ✅ Documentée le 2026-07-16 dans `docs/10-choix_techniques.md` (§ Boutons physiques : GPIO direct + polling) — décision et justification actées formellement, en plus des notes de suivi ci-dessous et dans [[TICKET-101]]
      - Reste de l'historique détaillé (plan GPIO, layout boîtier, handlers, actions `radio.php`) : voir TICKET-101, qui a repris et clos le travail restant
- [x] TICKET-101 — hardware — Finalisation boutons physiques : mapping GPIO ↔ bouton + service systemd définitif
      - Suite de TICKET-091 (choix d'interface GPIO + bring-up déjà validés) et TICKET-031 (bouton "source" HP/casque)
      - ✅ **Mapping GPIO ↔ bouton confirmé le 2026-07-08** (test bouton par bouton, gauche à droite) : GPIO25 = source (HP/casque), GPIO13 = vol−, GPIO17 = précédent, GPIO12 = play/pause, GPIO27 = suivant, GPIO5 = vol+, GPIO16 = favori (TICKET-046, confirmé et codé le 2026-07-19 — pas GPIO23 comme envisagé un temps ici), GPIO23 = bouton isolé antenne, réserve pour un usage futur non défini, GPIO6 = non câblé
      - ⚠️ GPIO17 n'est pas le bouton source dans le câblage réel (contrairement au bring-up breadboard du 2026-07-06) — c'est GPIO25. Sans impact, le dispatch est purement logiciel (`HANDLERS` dans `buttons_daemon.py`)
      - ✅ Handlers assignés dans `HANDLERS` (`scripts/buttons_daemon.py`)
      - ✅ Service systemd créé : `scripts/buttons_daemon.service` (remplace `button_toggle_test.service`, voir `docs/70-SERVICES_SYSTEMD.md` §7ter pour l'installation)
      - ✅ Service installé et testé en conditions réelles par Thomas (2026-07-08) : 3 bugs trouvés et corrigés —
          • suivant/précédent ne faisaient rien : `radio.php` lisait `mpd_status()['file']`, or la commande MPD `status` n'a PAS de champ `file:` (seul `currentsong` l'a) → ajout de `mpd_currentsong()`, utilisé par `next_episode`/`prev_episode`/`now_playing`
          • latence perçue au play/pause : polling `syncPlaybackState()`/`syncAudioMode()` resserré de 300ms à 100ms dans `index.html`
          • maintien du bouton volume ne répétait pas : rebond mécanique pendant le maintien lu à tort comme un relâchement (bloqué ensuite par le garde-fou anti-rebond) → hystérésis dédiée (`RELEASE_CONFIRM_S`), relâchement confirmé seulement après 50ms de HIGH continu
      - ✅ **Nouveau (2026-07-08)** : suivant/précédent passent en tap-ou-maintien (`TAP_OR_HOLD` dans `buttons_daemon.py`) — tap bref = épisode suivant/précédent (inchangé), maintien > `HOLD_THRESHOLD_S` (0.4s) = recherche par à-coups de `SEEK_STEP_S` (5s) dans l'épisode en cours. Nouvelle action `seek_relative` dans `radio.php` (`seekcur ±N` MPD, recherche relative à la position actuelle). Recherche en secondes fixes (pas en % de la durée) — pratique standard des lecteurs de podcasts (Apple Podcasts, YouTube). Pas encore testé en conditions réelles par Thomas — valeurs `SEEK_STEP_S`/`HOLD_THRESHOLD_S` à ajuster si besoin
      - ⏳ Reste à faire : Thomas teste le tap/maintien suivant-précédent. GPIO16/favori : voir TICKET-046, codé le 2026-07-19.

- [x] TICKET-031 — hardware/feature — Sortie casque avec bouton physique de bascule HP/casque
      - Contrainte : HiFiBerry Amp4 conservé (pas de sortie casque native)
      - Solution retenue :
          • DAC USB : KT USB Audio — branché, fonctionnel ✅
          • Jack : XMSJSIY TRS 3.5mm panel mount ∅22mm chromé — monté dans le boîtier ✅
          • MPD : 2 sorties configurées — `My ALSA Device` (HiFiBerry, HP) + `Casque USB` (DAC USB) ✅
          • ⚠️ Référencer les cartes par **nom** (`hw:CARD=sndrpihifiberry,DEV=0` / `hw:CARD=Audio,DEV=0`), jamais par numéro (`hw:N,0`) — le numéro de carte ALSA n'est pas stable d'un boot à l'autre sur ce Pi (cf. bug ci-dessous)
      - ✅ Implémenté session 14 (partiel) — bascule manuelle depuis l'IHM enfant :
          • Bouton pill dans la statusbar (toujours visible sur tous les écrans)
          • Volume mémorisé par mode (HP / casque) en localStorage
          • Séquence bascule : volume d'abord, sortie ensuite (évite pic sonore)
          • `radio.php` : get_output / set_output (MPD enableoutput/disableoutput)
          • `currentVolumeMax()` : VOLUME_MAX_SPEAKERS ou VOLUME_MAX_HEADPHONES selon mode
      - 🐛 Bug corrigé le 2026-07-03 — son sorti par le casque au boot alors que HP affiché/attendu :
          • Cause : `/etc/mpd.conf` référençait les cartes par numéro (`hw:2,0`/`hw:3,0`) ; ce numéro a dérivé entre le setup initial et aujourd'hui (HiFiBerry et DAC USB ont échangé leurs numéros) → corrigé en référençant par nom
          • `radio.php` `set_output` répondait `ok:true` même quand la commande n'atteignait pas MPD (socket pas prêt au boot) → corrigé pour vérifier la vraie réponse
          • `~/kiosk.sh` force désormais HP + volume 20% IHM avant Chromium, avec retry qui vérifie le vrai `ok:true`
          • ✅ Confirmé fonctionnel par Thomas après reboot complet
      - 🎨 Widget dashboard fatigue auditive (session 2026-07-03) — `dashboard.php` :
          • Icône oreille : silhouette tracée depuis `web/oreille.svg` (référence déposée par Thomas), couleur dynamique selon fatigue (vert/jaune/orange/rouge)
          • Zone concha/canal interne en blanc 90% opacité (le noir était invisible sur le fond bleu nuit)
          • Jauge verticale à côté (100% en haut → 0% en bas, dot qui descend avec la fatigue)
      - ❌ **Détection automatique du branchement casque abandonnée définitivement** (décision Thomas, confirmée le 2026-07-08 puis re-confirmée le 2026-07-17) : comparateur d'impédance LM393 testé sur plaque d'essai, ne fonctionne pas (tension ~1,1V que le casque soit branché ou débranché, le DAC USB pilote activement sa sortie). Piste de repli — jack à contact mécanique switché câblé sur GPIO — également irréalisable en pratique. **Le bouton physique manuel est la solution définitive**, pas une étape transitoire. Détail schéma/essais dans `docs/80-hardware.md` §"Sortie casque + détection".
      - ✅ **Test de mise en route bouton GPIO validé le 2026-07-06** (`scripts/button_toggle_test.py`, bring-up TICKET-091) :
          • Bouton physique (pull-up, appui = LOW) bascule HP↔casque de bout en bout, testé après reboot complet
          • Détection par **polling** (10ms), pas par `add_event_detect()` — peu fiable sur Pi 5/RP1
          • Antirebond à 3 niveaux (polling rapproché + confirmation logicielle + garde-fou global 400ms)
          • 🐛 Bug critique trouvé et corrigé en même temps : `radio.php` action `get_output` utilisait une regex qui supposait `outputenabled` juste après `outputname` — MPD 0.24 insère une ligne `plugin: alsa` entre les deux, donc la detection retombait toujours sur "hp", jamais "casque". Remplacé par un vrai parsing par bloc `outputid` (`mpd_output_enabled()`)
          • 🔄 **Volume mémorisé par mode déplacé côté serveur** (`data/audio_output_state.json`, plus seulement `localStorage` navigateur) — `set_output` gère lui-même la mémoire de volume et la séquence "volume d'abord, sortie ensuite", quel que soit l'appelant (IHM, GPIO)
          • Le "mode qu'on quitte" est déterminé par l'état réel MPD (`outputs`), jamais par une valeur mémorisée seule
          • Écran resynchronisé sur l'état réel toutes les 300ms (`syncAudioMode()`)
      - ✅ **Montage physique terminé** (confirmé par Thomas le 2026-07-17) : jack XMSJSIY monté dans le boîtier (simple passe-plat, pas de contact switché à exploiter), DAC USB câblé, bouton "source" GPIO25 câblé et fonctionnel en conditions réelles (mapping final TICKET-101), service `buttons_daemon.service` actif — plus rien en attente côté matériel pour ce ticket.
      - Le code IHM (bouton pill, logo, volumes mémorisés) reste définitif et cohabite avec le bouton physique GPIO.

- [x] TICKET-106 — infra — Objet git corrompu dans `~/hechicero` (`git log`/`git fsck` cassés)
      - Découvert le 2026-07-09 en marge du diagnostic TICKET-102 : `git log`/`git fsck --full` échouaient avec `error: garbage at end of loose object ... fatal: ... is corrupt` (objet `4236ac6e...`)
      - `git show HEAD:<fichier>` et `git commit`/`git push` fonctionnaient malgré tout (l'objet corrompu n'était pas un blob HEAD courant)
      - ✅ Clos le 2026-07-17 : `git log` refonctionne normalement (vérifié), et Thomas confirme que git se comporte normalement à l'usage (commits/push réguliers sans souci depuis). Cause jamais identifiée avec certitude — pas de `git fsck --full` complet re-exécuté pour confirmation formelle, mais accepté comme non bloquant vu l'usage normal prolongé.

---

# 🧩 Notes
- Repo public : aucun prénom personnel dans les fichiers versionnés (voir `15-INVARIANTS.md` §6.4)
- Prénoms réels autorisés uniquement dans `private/` (exclu du repo)
- Les tickets hardware (031, 038) sont isolés pour éviter les régressions logiciel
