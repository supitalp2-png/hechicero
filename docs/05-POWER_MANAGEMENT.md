# Power Management — Projet Hechicero

> Dernière mise à jour : 2026-08-21
> Ce document est la **référence unique** pour l'alimentation et la batterie.
> Il absorbe l'ancienne spec `docs/80-ALIMENTATION.md` (session 7, 2026-06-26), supprimée le 2026-08-04 :
> les deux fichiers décrivaient le même sujet, l'un en spec à implémenter, l'autre en état réel,
> et ils divergeaient. Matériel : voir `docs/80-hardware.md`.

---

## 1. Objectif

L'autonomie en mobilité est le point faible historique du projet. Sans mesure précise, impossible de dimensionner la batterie ni de donner à l'enfant une information utile.

L'objectif n'est **pas** de mesurer une capacité en mAh, mais un **temps d'écoute réel**.

- Suivi fiable de l'état batterie (niveau, tension, courant)
- Autonomie exprimée en temps d'écoute
- Alertes progressives : 30 min → 10 min → arrêt propre
- Prévention des corruptions de carte SD par shutdown ordonné

**Autonomie cible : 3 heures** — un grand trajet en voiture ou une matinée autonome. Référence de départ, affinée par les mesures réelles.

---

## 2. Les deux personas

Ils expliquent *pourquoi* l'IHM enfant et le dashboard parent n'affichent pas les mêmes choses — à relire avant de toucher à l'affichage batterie.

### Persona Enfant

Une seule question : *est-ce que j'ai assez de batterie pour ce que je veux faire ?*

- Jauge en **temps restant**, jamais en pourcentage : « Il te reste 2h30 d'écoute »
- Popup discret au branchement : « Recharge estimée : 1h45 » (modèle Android)
- Pas de chiffres bruts, pas d'unités techniques
- Deux alertes seulement (§6)

### Persona Parent Geek

- Pourcentage visible **en complément** du temps restant
- Dashboard alimentation dédié (`web/admin/battery_dashboard.php`), séparé du dashboard d'écoute
- Objectif : comprendre pour décider — redimensionner la batterie ou optimiser la consommation

---

## 3. Architecture — trois scripts

| Script | Rôle | Service systemd |
|---|---|---|
| `scripts/battery_common.py` | Helpers partagés (INA219, MPD, écriture atomique) | — |
| `scripts/battery_tracker.py` | Collecte, détection de cycles, estimations | `battery_tracker.service` ✅ |
| `scripts/battery_watchdog.py` | Surveillance du seuil critique, arrêt propre | `battery_watchdog.service` ✅ |

> `scripts/get_status.py` + `hechicero-monitor.service` — **supprimés en session 11**. Ne plus utiliser.

---

## 4. Fichiers de données

| Fichier | Contenu | Écrit par |
|---|---|---|
| `data/battery_history.json` | Cycles complets avec datapoints | `battery_tracker.py` |
| `data/battery_stats.json` | État courant + estimations | `battery_tracker.py` |
| `data/last_session.json` | Position MPD au moment du shutdown critique | `battery_watchdog.py` |
| `data/config.json` | Seuils (`critical_level_percent`, etc.) | admin PHP |

> ⚠️ Ces fichiers sont dans `.gitignore` — jamais versionnés.
> ⚠️ Permissions obligatoires : `rw-rw-r--` (664) — `battery_common.py` les applique après chaque écriture.

### Remise à zéro des mesures après remplacement des cellules

À faire **uniquement** quand la batterie est physiquement changée : l'historique décrit alors un accumulateur qui n'existe plus et fausse `estimated_autonomy_minutes` ainsi que `consumption_by_mode`. Procédure validée le 2026-08-17 (TICKET-126) :

```bash
sudo systemctl stop battery_tracker battery_watchdog
rm -f ~/hechicero/data/{battery_history.json,battery_stats.json,last_session.json} \
      ~/hechicero/data/battery_*.json.*
sudo systemctl start battery_tracker battery_watchdog
sleep 100 && python3 -c "import json;s=json.load(open('/home/thomas/hechicero/data/battery_stats.json'));print(s.get('cycles_recorded'), s.get('model_confidence'))"
```

Attendu : `0 low`.

- ⚠️ **L'ordre n'est pas négociable.** `battery_tracker` écrit `battery_history.json` et `battery_stats.json` à **chaque** tour de boucle (60 s par défaut) ; `battery_watchdog` est le seul auteur de `last_session.json`. Supprimer à chaud, c'est voir un fichier réapparaître dans la minute et croire la remise à zéro faite.
- Le glob `battery_*.json.*` récupère les fichiers temporaires orphelins de `atomic_write_text()` (`tempfile.mkstemp(prefix=path.name + ".")`), laissés derrière par une coupure d'alimentation en pleine écriture.
- **Ne jamais toucher à `data/tracking.db`** : historique d'écoute, sans rapport avec la batterie.
- **Le niveau (%) n'a pas besoin d'être réinitialisé** : `percent_from_voltage()` est une table tension→pourcentage, sans mémoire. Seul le modèle d'estimation réapprend.
- **À faire branché au secteur**, pour que le premier cycle de décharge mesuré parte d'une batterie pleine.
- **Vérifier ensuite `charge_deadband_ma`** (`data/config.json`, 200 mA) : c'est le SIGNE du courant qui décide charge/décharge, cette bande n'absorbe que le bruit autour de zéro. ⚠️ `charge_threshold_ma` — l'ancien seuil unique — subsiste dans la config **sans aucun effet** ; ne pas s'en servir. Il classait « décharge » des courants positifs jusqu'à +300 mA, fabriquant de faux cycles où le niveau montait.
- **Vérifier aussi `battery_usable_mah`** (8894 mAh, mesuré) et `internal_resistance_ohm` (0,034) : le comptage coulométrique et la compensation d'affaissement en dépendent. Des cellules différentes changent les deux.

### Schéma `data/battery_history.json`

```json
{
  "cycles": [
    {
      "discharge_start": "2026-06-01T14:00:00",
      "level_start": 87,
      "discharge_end": "2026-06-01T16:30:00",
      "level_end": 12,
      "duration_minutes": 150,
      "dominant_mode": "podcast",
      "datapoints": [
        {"t": "2026-06-01T14:00:00", "level": 87, "mpd_mode": "podcast", "screen": true},
        {"t": "2026-06-01T14:08:00", "level": 85, "mpd_mode": "podcast", "screen": true}
      ],
      "charge_start": "2026-06-01T16:31:00",
      "charge_end": "2026-06-01T18:45:00",
      "charge_duration_minutes": 134
    }
  ]
}
```

### Schéma `data/battery_stats.json`

```json
{
  "current_level": 73,
  "status": "discharging",
  "current_mpd_mode": "podcast",
  "estimated_autonomy_minutes": 112,
  "estimated_charge_time_minutes": 73,
  "last_updated": "2026-06-26T10:00:00",
  "cycles_recorded": 8,
  "model_confidence": "low",
  "consumption_by_mode": {
    "webradio": 4.2,
    "podcast": 3.1,
    "idle": 1.8
  }
}
```

`model_confidence` : `"low"` < 3 cycles, `"medium"` 3–9, `"high"` ≥ 10.

---

## 5. De la tension au pourcentage

C'est la chaîne dont dépend **tout** l'affichage du projet : écran enfant, tableau de bord,
seuils d'alerte et d'arrêt. Elle compte quatre étages, et **chacun est indispensable aux
autres**.

```
INA219  ──►  rafale + médiane  ──►  V_oc = V − I·R  ──►  table mesurée  ──►  comptage
            (bruit capteur)        (affaissement)       (< 70 %)          (> 70 %)
```

### 1. Rafale et médiane — absorber le bruit

Cinq lectures rapprochées, on garde la **médiane**. Pas la moyenne : une seule valeur
aberrante déplace une moyenne, il en faut la moitié pour déplacer une médiane. Le signal
oscille réellement de −210 à +1459 mA d'un relevé à l'autre ; un creux isolé faisait
annoncer « charge arrêtée ».

### 2. Compensation d'affaissement — `V_oc = V − I·R`

La table donne des tensions **à vide**, l'INA219 mesure **sous charge**. À −2,2 A et
R = 34 mΩ, l'écart vaut **75 mV**, soit environ 8 points de pourcentage : c'est ce qui
faisait plonger la jauge dès qu'un podcast démarrait, alors que rien n'avait été consommé.

⚠️ Le **signe** compte. En décharge (courant négatif) la tension mesurée est plus basse
qu'à vide ; en charge elle est plus haute. La formule `V − I·R` traite les deux cas, le
signe du courant faisant le travail. Se tromper de signe **doublerait** l'erreur.

📌 R = 34 mΩ est le meilleur accord entre deux cycles profonds, mais **le minimum est plat
entre 20 et 60 mΩ** : le courant de décharge varie trop peu (1540-2170 mA) pour le
contraindre finement. À prendre comme un ordre de grandeur.

### 3. Table mesurée — fiable en dessous de 70 %

`_LIPO_TABLE` a été établie par intégration du courant sur **deux décharges profondes
indépendantes** (2026-08-18 et 2026-08-19), qui ont délivré 8892 et 8896 mAh — à 0,05 %
près. L'ancienne table était une courbe générique jamais recalée : elle **sur-évaluait de
4 à 8 points** et annonçait encore 7 % à la coupure réelle.

⚠️ **CES TENSIONS SONT DES TENSIONS À VIDE.** Les comparer à une lecture brute rend le
calcul **plus faux qu'avant**. Table et compensation vont par paire ; deux tests du smoke
test les maintiennent liées.

### 4. Comptage coulométrique — au-dessus de 70 %

Entre 75 et 85 %, la table étale 5 points sur **5 mV**. Autrement dit **10 mV valent
10 points**. Aucune table de tension ne peut répondre dans cette bande : c'est le plateau
de la chimie Li-ion, pas un défaut de mesure.

Au-dessus du seuil, on **intègre le courant** depuis le dernier point d'ancrage. Ce qui
rend ce mécanisme acceptable, c'est qu'il est **ancré** :

- sous 70 %, la table fait autorité et **recale toute dérive** — la courbe y est franche ;
- une batterie pleine (≥ 4,10 V **et** |I| ≤ 150 mA) ancre franchement à 100 % ;
- au-delà de **10 minutes de trou** de mesure, l'ancrage est abandonné.

La dérive ne peut donc s'accumuler que sur **une traversée** de la bande haute. ⚠️ Le
garde-fou du trou est essentiel : **un compteur qui intègre à travers un trou dérive sans
le dire**, ce qui est le pire défaut possible pour ce genre de mécanisme.

⚠️ Les **deux** conditions du plein sont indispensables. Les arrêts de charge anormaux du
TICKET-140 présentent exactement la signature d'un courant nul (0,91 mA pendant des heures)
mais à **54 % et 70 %**. Un critère fondé sur le seul courant afficherait **100 % avec un
tiers de l'énergie**.

`battery_stats.json` publie `level_table` à côté de `level` : **leur écart mesure la dérive
du comptage.** Sans lui, une dérive serait indétectable sans refaire un cycle complet.

### 📌 L'erreur à ne pas refaire

La table mesurée a d'abord été validée sur un **désaccord médian de 6,4 mV** entre les deux
cycles, annoncé comme une réussite. Personne n'a converti ces millivolts en **points de
pourcentage** — or la conversion dépend de la pente : 10 mV valent 0,8 point à 30 % et
**10 points à 80 %**. Résultat mesuré sur l'appareil : la table annonçait **86 %** là où la
réalité était **77,9 %**, soit **pire que l'ancienne table** qu'elle remplaçait.

> **Une métrique de validation exprimée dans une autre unité que le produit ne valide
> rien.** Convertir dans l'unité de l'utilisateur avant de conclure.

L'outil `scripts/recalibrer_table_batterie.py` applique désormais cette règle : il affiche
la sensibilité locale (points par mV) et **c'est l'écart en points qui décide** s'il
propose une table ou refuse.

---

## 6. Ce qu'on mesure

### Par cycle de décharge

- Niveau au débranchement du secteur (%)
- Niveau au rebranchement (%)
- Durée totale du cycle (minutes)
- Mode MPD dominant : webradio / podcast local / veille
- → Ratio calculé : minutes d'écoute par % consommé

### Par cycle de recharge

- Durée pour passer du niveau de fin de décharge à ~100 %
- → Ratio calculé : minutes de charge par % récupéré

### À chaque point de mesure

Un point est enregistré si l'un de ces six critères est rempli :

| Critère | Pourquoi |
|---|---|
| transition charge ↔ décharge | c'est l'événement structurant du cycle |
| changement de mode MPD | la consommation dépend du mode |
| variation de niveau ≥ 2 points | le filtre historique |
| changement de statut | idem |
| **5 minutes écoulées** | cadence plancher — rend un PLATEAU observable |
| **courant : variation ≥ 300 mA, ou franchissement de la bande morte** | « le courant a cessé de couler » est un événement majeur |

Format : `{t, level, charging, mpd_mode, screen, current_ma, voltage_v}`.

⚠️ **Les deux derniers critères ont été ajoutés par TICKET-141, et voici pourquoi.**
Jusqu'au 2026-08-19, un point n'était écrit que sur **changement**. Conséquence : quand le
système tenait un plateau, aucun critère ne se déclenchait et **rien n'était enregistré**.
Mesure de l'aveuglement : sur un plateau de 30 minutes, l'ancien code retenait **zéro
point**. Trous constatés le 2026-08-19 : 38, 147 et 49 minutes.

Pire, le **courant n'était pas un critère du tout**. Dans la nuit du 18 au 19, il s'est
effondré de +1111 à −60 mA pendant 6 h 53 — l'événement entier du TICKET-140 — et cela n'a
été capté que par accident, parce que le niveau bougeait au même moment : **3 points en
6 h 53**.

> **Un échantillonnage déclenché par le changement ne peut pas documenter une absence de
> changement.** L'enregistreur devenait muet exactement pendant le phénomène qu'on
> cherchait à étudier.

**Rétention** : 30 jours en pleine résolution, puis un point par heure. La purge tourne
**dans le tracker**, pas dans un cron — une purge confiée à un service tiers finit par ne
plus tourner sans que personne ne s'en aperçoive. L'historique n'est réécrit que s'il a
changé : avant ce garde-fou, le fichier entier était réécrit toutes les 60 s, soit
**283 Mo d'écriture par jour** sur la carte SD pour un fichier le plus souvent inchangé.

### ⚠️ Piège corrigé — `level_end` écrasé pendant la charge (2026-07-06)

`level_end` continuait d'être mis à jour **après** la fin de la décharge, pendant la recharge. Résultat : les vrais cycles profonds étaient enregistrés avec un `level_end` remonté et se retrouvaient invalidés à tort, pendant que des dizaines de micro-cycles factices polluaient l'historique (51 relevés, autonomie annoncée à 12 h contre 1,5–3 h réelles).

Corrigé le 2026-07-06 ; l'historique existant a été réparé par un script de migration à usage unique, supprimé du dépôt le 2026-08-04. **Ne pas réintroduire d'écriture de `level_end` hors de la phase de décharge.**

---

## 7. Alertes et seuils

| Seuil | Pour qui | Message | Comportement |
|---|---|---|---|
| 30 min restantes | Enfant | « Il te reste 30 minutes, pense à brancher ta radio » | Bandeau discret, jamais pendant la lecture |
| 10 min restantes | Enfant | Alerte plus visible | Actionnable immédiatement |
| Avertissement (10 %) | Système | *(aucun message)* | Journalisé |
| Critique (**5 %**) | Système | *(aucun message)* | Arrêt propre après 60 s de grâce |

Les alertes destinées à l'enfant sont exprimées en **temps**, jamais en pourcentage.

⚠️ **Le seuil « 5 % » a changé de signification le 2026-08-21 sans changer de nom.** Avec
l'ancienne table appliquée à la tension brute, il se déclenchait à 3,350 V ; avec la table
mesurée appliquée à la tension à vide, il se déclenche à **3,458 V**, soit 108 mV plus tôt
et environ 14 minutes d'autonomie en moins. Décision assumée : ces minutes se situent là où
la tension s'effondre et où les cellules souffrent le plus. **Un seuil dont le nom ne
change pas alors que sa signification physique change est un piège classique** — le
revérifier après toute modification de la table.

---

## 8. Arrêt propre (`battery_watchdog`)

### Mécanisme

**Le polling est la seule protection réelle.** Toutes les 30 s, le watchdog lit le niveau ;
sous le seuil critique (5 %), il attend 60 s de grâce puis déclenche l'arrêt.

⚠️ `GpioSignalMonitor` existe dans le code et prétend intercepter un signal de coupure
imminente du HAT **en priorité** sur le polling. En pratique il est **inerte** : la clé
`ups_hat_signal_gpio` n'existe pas dans `data/config.json`, donc la broche vaut `None` et
`triggered()` renvoie toujours `False`. Ce mécanisme n'a jamais fonctionné. Soit on câble
et on documente la broche, soit on supprime le code — le laisser ainsi entretient la
croyance d'une protection qui n'existe pas.

### Séquence

1. Sauvegarder la position MPD dans `data/last_session.json`
2. `mpc stop`
3. `sync` — vidage du cache disque
4. Armer le redémarrage à la remise sous tension (registre `0x2d/0x01 ← 0x55`)
5. `shutdown -h now` — **sans `sudo`**

Au redémarrage, la position est restaurée par la logique de reprise — l'enfant ne voit rien.

⚠️ **Pas de `sudo` à l'étape 5, et ce n'est pas un détail.** Le service tourne déjà en
`User=root`, donc `sudo` n'apportait rien — et son unité porte `NoNewPrivileges=true`, qui
**casse `sudo`**. L'appel échouait, en silence, parce que `run_command()` avale l'exception
et le code de retour. **La protection contre la décharge profonde n'a pas fonctionné du
2026-07-19 au 2026-08-17.** Ne jamais réintroduire `sudo` dans ce chemin.

⚠️ **L'étape 4 n'est PAS une coupure d'alimentation**, contrairement à ce que le code a
affirmé pendant quatre jours. La documentation Waveshare titre sa section « Boot When Power
Applied » : ce registre arme le **démarrage automatique quand le courant revient**. C'est
utile — la radio repart seule quand on rebranche — mais **rien ne coupe l'alimentation
après l'arrêt de l'OS**. Voir §11.

### Test de simulation

```bash
python3 scripts/battery_watchdog.py --simulate-critical
cat data/last_session.json
```

> ✅ **Prouvé deux fois en conditions réelles**, sans simulation : coupures du
> **2026-08-18 à 12:22:20** (décharge 97 % → 5 %) et du **2026-08-20 à 01:29:05**
> (83 % → 5 %). Les deux ont laissé une trace propre dans `data/last_session.json` et le
> Pi s'est bien éteint. `battery_watchdog` était le dernier des 8 services durcis dont le
> comportement d'arrêt n'avait jamais été vérifié.

---

## 9. Service `battery_tracker`

Fichier : `/etc/systemd/system/battery_tracker.service`
(source dans le repo : `scripts/battery_tracker.service`)

```ini
[Unit]
Description=Hechicero Battery Tracker
After=network.target mpd.service

[Service]
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/battery_tracker.py
Restart=on-failure
RestartSec=10
User=thomas

[Install]
WantedBy=multi-user.target
```

### Activer

```bash
sudo cp scripts/battery_tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now battery_tracker
```

### Vérifier

```bash
systemctl status battery_tracker
journalctl -u battery_tracker -f
cat data/battery_stats.json
```

---

## 10. Dashboard parent

`web/admin/battery_dashboard.php`, accessible depuis le bureau d'icônes admin (TICKET-113).

| Bloc | Contenu |
|---|---|
| 1 — Situation actuelle | Statut (secteur / batterie / charge), niveau + temps restant, mode MPD, durée dans cet état |
| 2 — Cycle en cours | Courbe temps écoulé × niveau, en temps réel |
| 3 — Profils de consommation | Barres : %/heure par mode (webradio / podcast / veille écran) — **le graphique qui tranche** entre optimiser la conso et redimensionner la batterie |
| 4 — Historique des cycles | Tableau (date, durée, niveaux, mode dominant, autonomie réelle) + courbes de décharge superposées (anomalies, dégradation) |
| 5 — Courbes de recharge | Superposition des cycles — visualise la courbe CC/CV typique LiPo |
| 6 — Estimations et fiabilité | Autonomie et temps de recharge estimés, nombre de cycles ayant servi au calcul |

---

## 11. Démarrage — bouton physique RUN

Le Pi 5 ne démarre pas automatiquement quand le Waveshare UPS HAT (D) est alimenté : il attend un front logique sur la ligne RUN.

**Solution installée ✅** — bouton-poussoir momentané 16 mm chromé, câblé sur les broches RUN (fils rouge + bleu), logé dans un trou ⌀16 mm de la tranche supérieure du boîtier.

Appui court → démarrage. Appui court quand allumé → reset.

---

## 12. Comportement en cas de coupure

### Si la batterie tombe à 0 %

- La protection basse tension **intégrée aux cellules** coupe vers 3,15 V
- Le Pi s'éteint brutalement si aucun arrêt propre n'a été anticipé

⚠️ **RIEN NE PROTÈGE LES CELLULES APRÈS L'ARRÊT DE L'OS** (TICKET-144). `shutdown -h now`
arrête le système, mais le HAT continue de fournir du 5 V à un Pi « halted » : les cellules
se vident **après** l'arrêt d'urgence, sans surveillance ni limite de temps.

On s'est cru protégé du 2026-08-17 au 2026-08-21 par une fonction nommée
`arm_hat_power_cutoff()` qui **n'a jamais rien coupé** — elle armait en réalité le
démarrage à la remise sous tension. L'erreur venait d'une déduction faite sur la *séquence
d'appels* de la démo constructeur plutôt que sur sa documentation.

**Risque assumé** (décision du 2026-08-21) : l'interrupteur physique du HAT n'est pas
accessible dans le boîtier, et l'appareil n'est jamais rangé longtemps. Mais un appareil
laissé éteint et débranché plusieurs semaines descendra jusqu'à la coupure constructeur, et
**rien ne le signalera**. Si les cellules vieillissent anormalement vite, c'est la première
piste à rouvrir.

### Rôle de l'IHM enfant

- Afficher « Batterie faible »
- Empêcher le lancement de nouveaux contenus
- Réduire automatiquement le volume

### Rôle de l'interface admin

- Afficher l'état critique
- Proposer un bouton « shutdown propre »

### Après coupure

Le Pi **redémarre seul quand le chargeur est rebranché**, à condition que le registre
`0x2d/0x01` ait été armé à `0x55` avant l'arrêt — ce que fait `battery_watchdog`. C'est le
seul effet réel de ce registre.

Sans cet armement (arrêt non anticipé, coupure brutale), le redémarrage demande un appui sur
le bouton RUN.

---

## 13. Question ouverte — arrêt de charge inexpliqué (TICKET-140)

Le chargeur du HAT cesse parfois de charger **alimentation présente**, à des niveaux
variables. Reproduit trois fois : à 54 % (6 h 53), à 70 % (4 h 36) et à 96 % (1 h 07 — ce
dernier étant une terminaison normale, la batterie étant pleine).

**Établi** : ce n'est pas une coupure secteur. Pendant l'arrêt, le courant vaut ~0 mA
(0,91 mA constant, soit le zéro du capteur). Si l'alimentation externe avait disparu, le Pi
allumé aurait tiré −400 à −900 mA sur les cellules. L'alimentation était donc là ; c'est le
**chargeur** qui a cessé, à 3,88 V — loin des 4,2 V d'une cellule pleine.

**Établi aussi** : la reprise vient d'une **sollicitation**, pas de l'heure. Le démarrage
d'une webradio fait plonger la tension sous un seuil de reprise, et le chargeur repart.

**Écarté** : un temporisateur de sécurité de ~6 h. Prédiction posée puis **démentie** — la
charge du lendemain a traversé l'heure attendue et atteint 97 %.

**Écarté aussi** : notre propre code. Aucun chemin n'écrit dans le HAT hors de l'arrêt
critique.

**Piste suivante** : la température. La plupart des chargeurs Li-ion inhibent la charge hors
d'une fenêtre thermique, et le Pi 5 tourne à 67-68 °C sous le HAT. Rien n'est journalisé à
ce jour — c'est le premier relevé à ajouter.

---

## 14. Contraintes techniques à respecter

- **Zéro CDN externe** — Chart.js est servi localement (`web/js/chart.min.js`)
- Ne jamais casser `data.json` ni MPD
- `battery_history.json` et `battery_stats.json` : écriture atomique (tmp + rename)
- `battery_tracker.py` tourne en systemd avec `Restart=on-failure`
- Pour tout travail sur le GPIO de coupure : vérifier la datasheet du HAT UPS (D)
