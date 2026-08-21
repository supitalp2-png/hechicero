# Hardware — Projet Hechicero

> *Mis à jour le 2026-08-21.*

Ce document décrit l’ensemble du matériel utilisé dans le projet Hechicero,
ainsi que les contraintes, câblages, comportements et invariants associés.

Objectifs :
- centraliser toutes les informations matérielles  
- éviter les erreurs de câblage  
- documenter les comportements spécifiques du Raspberry Pi 5  
- garantir un système stable, réparable et reproductible  

---

## 0. Statut — Intégration matérielle terminée (2026-07-08)

✅ **L'assemblage physique du boîtier est terminé.** Écran + haut-parleurs montés et câblés sur
la nouvelle façade intérieure, boîtier Grundig Concert Boy 206 (2e exemplaire acheté) refermé,
les 7 boutons de la tranche supérieure + le bouton isolé (emplacement antenne) installés et
câblés. Produit fini testé fonctionnel (photos `Photos/01-vue-ensemble/02` et `03` — écran allumé,
splash Hechicero). Détail chronologique des étapes dans `Photos/03-interieur/06` à `10` et
`Photos/05-test-fit/06`-`07`.

Ce qui reste à faire n'est plus matériel mais **logiciel** : mapping GPIO ↔ bouton physique,
assignation des handlers dans `scripts/buttons_daemon.py`, service systemd définitif (voir
`docs/90-BACKLOG.md` TICKET-091). Voir §12 ci-dessous pour le détail des choix de boutons/sortie
audio retenus.

---

## 1. Liste du matériel

### 🔹 Raspberry Pi 5
- cœur du système  
- ports USB 3, HDMI, GPIO 40 broches  
- bouton POWER physique intégré  
- broches RUN pour démarrage/reset  

### 🔹 Waveshare UPS HAT (D)
- alimentation + batterie  
- capteur INA219 intégré  
- connecteur GPIO pass‑through  
- ne déclenche **pas** le démarrage automatique du Pi 5  

### 🔹 HiFiBerry Amp4
- amplification audio  
- sortie enceintes passives  
- pas de contrôle de volume matériel  
→ volume logiciel obligatoire  
- **nom de carte ALSA : `sndrpihifiberry`** — c'est la sortie **haut-parleurs**

### 🔹 DAC USB — KT USB Audio (sortie casque)
- **Ajouté à cette liste le 2026-08-17** : il manquait, alors que c'est la
  seconde sortie audio de l'appareil.
- Assure la **sortie casque**, distincte de l'ampli HiFiBerry
- **Nom de carte ALSA : `Audio`** (marque « KTMicro KT USB Audio »)
- ⚠️ Identifié comme le **facteur limitant du niveau au casque** (TICKET-116) :
  aucune atténuation cachée côté logiciel, c'est le DAC lui-même. D'où le gain
  d'égalisation dédié (TICKET-124, réglé à 4 dB).
- ⚠️ **Toujours le désigner par son NOM** (`hw:CARD=Audio`), jamais par un
  numéro : les numéros de carte ALSA changent d'un démarrage à l'autre, et ce
  périphérique est en USB — donc débranchable et déplaçable d'un port à
  l'autre, ce qui décale toute la numérotation. Voir TICKET-125 et
  `scripts/asound.conf`.

### 🔹 Écran tactile — **JRP JRP7003** 7" 1024×600
- interface enfant principale  
- connecté en HDMI + USB (tactile)
- nécessite Raspberry Pi OS avec bureau  
- 4 trous de montage aux coins (vis M3)
- ⚠️ **Corrigé le 2026-08-17** : ce document annonçait un Waveshare. L'EDID lu
  par `wlr-randr` donne `HDMI-A-1 "JRP JRP7003 0"`. Le mode natif est
  **1024x600@59.821**.
- ⚠️ **Le nom de sortie dépend du port HDMI physique** (`HDMI-A-1` ou
  `HDMI-A-2`), pas du modèle d'écran. Il est codé dans `scripts/screen_dpms.sh`
  et doit être mis à jour si l'écran change de port. Vérifier avec `wlr-randr`.

### 🔹 Enceintes passives
- 2 drivers avec chassis carré plastique (~50×50mm, 4 trous de fixation aux coins)
- membrane ∅38mm, frame ∅50mm (découpe panneau bois ∅46mm), profondeur 35mm
- chassis posé sur le panneau bois, vissé par 4 vis aux coins
- montage individuel dans la façade : driver gauche / driver droit (stéréo)
- câblage : sortie L Amp4 → driver gauche, sortie R Amp4 → driver droit
- connexion via bornier à vis du HiFiBerry Amp4

### 🔹 Boîtier — Grundig Concert Boy 206 (1966)
- carcasse radio vintage récupérée
- dimensions extérieures : 360 × 210 × 110 mm
- revêtement vinyle noir + bandeau chrome aluminium
- poignée métal chromée centrale (transport)
- façades avant et arrière remplacées : contreplaqué bouleau 4mm découpé laser, tissu acoustique tendu
- antenne d'origine supprimée

### 🔹 Bouton RUN externe
- indispensable pour démarrer le Pi 5 avec le HAT  
- équivalent à un appui sur le bouton POWER
- à câbler sur l'un des boutons d'origine du dessus du Concert Boy (GPIO Pi 5)

---

## 2. Comportement du Raspberry Pi 5 au boot
Le Raspberry Pi 5 **ne démarre pas automatiquement** lorsqu’il est alimenté via un HAT.

### 🔹 Pourquoi ?
Le Pi 5 attend un **front logique** sur la ligne RUN (ou un appui sur le bouton POWER).
Le Waveshare UPS HAT (D) n’envoie **aucun signal RUN** au boot.

### 🔹 Conséquence
→ Le Pi reste éteint tant qu’un bouton n’est pas pressé.  
→ Inacceptable pour un usage enfant.  

### 🔹 Solution
Ajouter un **bouton RUN externe** relié aux broches RUN du Pi 5.

---

## 3. Broches RUN du Raspberry Pi 5
Les broches RUN sont situées sur un connecteur 2 broches dédié.

### 🔹 Fonction
- court‑circuiter RUN = démarrage ou reset  
- équivalent au bouton POWER  

### 🔹 Câblage bouton RUN
```
[Bouton poussoir]
  ├──> RUN
  └──> GND
```

### 🔹 Règles
- bouton **momentané** (push button)  
- pas de résistance nécessaire  
- câblage court pour éviter les parasites  

---

## 4. Waveshare UPS HAT (D)
### 🔹 Rôle
- alimentation sur batterie  
- mesure tension/courant via INA219  
- protection contre les coupures  

### 🔹 Limitations
- ne déclenche pas RUN au premier démarrage → bouton externe nécessaire
- **aucune coupure d'alimentation pilotable par logiciel** — voir ci-dessous

### 🔹 Broches et registres utiles

| Adresse I2C | Rôle |
|---|---|
| `0x43` | INA219 — tension, courant, puissance |
| `0x2d` | MCU du HAT — registre `0x01` |

⚠️ **Écrire `0x55` dans `0x2d/0x01` arme le DÉMARRAGE à la remise sous tension, pas une
coupure.** La documentation Waveshare titre cette section « Boot When Power Applied ». Le
projet a cru pendant quatre jours qu'il s'agissait d'une coupure matérielle : l'erreur
venait d'une déduction faite sur la **séquence d'appels** de la démo constructeur — qui
écrit ce registre juste avant `poweroff` — au lieu de sa documentation (TICKET-128).

**Effet réel, et il est utile** : après un arrêt propre, la radio **repart seule** dès que
le chargeur est rebranché. `battery_watchdog` l'arme avant chaque arrêt critique.

### 🔹 Comportement en cas de batterie vide

- La protection basse tension **intégrée aux cellules** coupe vers 3,15 V
- Le Pi s'éteint brutalement si aucun arrêt propre n'a été anticipé

🔴 **RIEN NE PROTÈGE LES CELLULES APRÈS L'ARRÊT DE L'OS** (TICKET-144). `shutdown -h now`
arrête le système, mais le HAT continue de fournir du 5 V à un Pi « halted » : les cellules
se vident **après** l'arrêt d'urgence, sans surveillance ni limite de temps.

⚠️ Ce paragraphe affirmait « coupe physiquement l'alimentation ». C'est faux, et c'était
la conséquence directe de l'erreur sur le registre `0x55`.

**Risque assumé** (décision du 2026-08-21) : l'interrupteur `OFF/ON` du HAT n'est pas
accessible dans le boîtier, et l'appareil n'est jamais rangé longtemps. Mais un appareil
laissé éteint et débranché plusieurs semaines descendra jusqu'à la coupure constructeur, et
**rien ne le signalera**. Si les cellules vieillissent anormalement vite, première piste à
rouvrir.

### 🔹 Accumulateurs — remplacés le 2026-08-16 (TICKET-126)

| | Valeur |
|---|---|
| Référence | **EVE INR21700/58E** — marquage `1QBM110H` |
| Format | 21700 cylindrique, Li-ion NMC (`INR`) |
| Capacité unitaire | **5600 mAh** — 20,16 Wh |
| Nombre | **2**, montés en **parallèle** (système 1S : tensions observées 3,4 → 4,2 V) |
| **Capacité totale** | **11 200 mAh — 40,3 Wh** |
| Tension nominale | 3,6 V · pleine 4,2 V · coupure constructeur 2,5 V (**plancher pratique retenu : 3,0 V**) |

⚠️ **`data/config.json` → `battery_capacity_mah` doit valoir 11200.** Il était
resté à **6600** (l'ancien pack) jusqu'au 2026-08-17, alors que les cellules
avaient déjà changé. Cette valeur ne sert qu'à `estimated_autonomy_minutes_live`
(`capacité × niveau utilisable ÷ courant`) : avec 6600 au lieu de 11200,
**l'autonomie temps réel était sous-estimée de 41 %**. C'est la capacité
physique, pas un réglage — à corriger dès que les cellules changent.

📌 **Ancien pack** : 18650, ~6600 mAh au total. Ils n'étaient **pas défaillants**,
simplement inadaptés. Leur chute de 49 % à 13 % en 4 minutes sous −2,9 A était
de l'**affaissement dû à la résistance interne**, pas une panne — un piège
d'interprétation à ne pas refaire.

🔬 **Conséquence des 21700 sur les mesures** : à 3 A de consommation totale, on
tire 1,5 A par cellule, soit environ **0,27 C** — un régime très doux pour ces
cellules. L'affaissement sous charge est donc **nettement plus faible** qu'avec
les 18650. Le pourcentage affiché en pleine consommation est par conséquent
**plus proche de l'état de charge réel** : il y a moins de marge cachée qu'avant
sous un même pourcentage. À garder en tête pour tout réglage de seuil.

⚠️ **`battery_common._LIPO_TABLE`** est une courbe d'accumulateur à poche. Elle
reste acceptable pour du Li-ion NMC (chimie voisine : 4,2 V pleine, ~3,0 V vide),
mais elle n'a **jamais été recalée sur ces cellules**. Toute décision fine de
seuil devrait s'appuyer sur les tensions réellement enregistrées
(`voltage_v` dans `data/battery_history.json` depuis le 2026-08-17), pas sur la
conversion en pourcentage.

---

## 5. HiFiBerry Amp4
### 🔹 Rôle
- amplification audio  
- sortie enceintes passives  

### 🔹 Contraintes
- pas de contrôle de volume matériel  
→ `mixer_type "software"` obligatoire dans MPD  

### 🔹 Alimentation
- alimenté via le GPIO  
- compatible avec le HAT (stacking)  

---

## 6. Écran tactile
### 🔹 Rôle
- interface enfant principale  

### 🔹 Contraintes
- nécessite Raspberry Pi OS avec bureau  
- nécessite Chromium  
- nécessite désactivation de l’écran de veille  

### 🔹 Tests
- toucher précis  
- pas de scroll parasite  
- pas de zoom multitouch  

---

## 7. Boîtier — Grundig Concert Boy 206

### 🔹 Concept
Radio portable vintage dont les entrailles sont remplacées par l’électronique Hechicero.
La carcasse d’origine (vinyle noir, bandeau chrome, poignée métal) est conservée intégralement.

### 🔹 Décisions façade (2026-06-28)

**Ce qu’on conserve :**
- Bande vinyle/simili-cuir gauche avec logo GRUNDIG : ~50 mm de large (à mesurer précisément avant découpe)
- Bandes chromées haut et bas (CH = 33 mm)
- Poignée métal chromée centrale

**Ce qu’on remplace :**
- Zone centrale : grille HP d’origine + panneau tuner → nouveau panneau contreplaqué bouleau 4 mm
- Panneau bois de X=50 mm jusqu’au montant droit (~303 mm de large, 144 mm de haut)

### 🔹 Layout façade avant
```
┌────────┬──────┬──────────────────────┬──────┐  ← bandeau chrome
│        │      │                      │      │
│ vinyle │ HP ∅ │   Écran 7" tactile   │ HP ∅ │
│ GRUNDIG│  50  │   1024 × 600         │  50  │
│ ~50mm  │  mm  │   (centré panneau)   │  mm  │
│        │      │                      │      │
└────────┴──────┴──────────────────────┴──────┘  ← bandeau chrome
```

Positions dans le modèle OpenSCAD (X depuis bord gauche, estimées) :
- Bande vinyle : 0 → 50 mm
- HP gauche centre : ~83 mm
- Écran gauche : ~117 mm (centré dans panneau ~303 mm)
- HP droit centre : ~320 mm

### 🔹 Panneau bois (nouveau)
- **Matériau** : MDF 3 mm FSC (choix final — surface lisse idéale pour tissu acoustique)
- **Découpe** : Snijlab (Rotterdam) — commande passée le 2026-06-30, livraison estimée 08-07-2026
  - Référence X371513 — "HP visibles.dxf" (cercles ∅44mm membrane) × 1
  - Référence X371514 — "HP invisibles.dxf" (chassis carré 49×49mm) × 1
  - Total : €43.99 TTC (frais DPD inclus)
- **Finition** : tissu acoustique noir tendu (Diarypiece 140×50cm + 3M Spray Mount 77/90)
- **Fixation** : vis M3 tête fraisée, noyées sous le tissu — inserts laiton M3 dans le bois

### 🔹 Tranche du dessus — nouveaux boutons

La bande chromée du dessus conserve ses trous d’origine et reçoit des boutons neufs vissés par dessous.

**Trous existants :**
- 1 petit trou (∅ à mesurer, probablement 6 mm) — vis ou voyant d’origine
- 1 fente rectangulaire (~25 × 8 mm) — interrupteur d’origine
- ~10 trous ronds ∅ 16 mm — anciens potentiomètres

**Boutons installés / à installer :**
- Bouton RUN (démarrage Pi 5) : **déjà installé** — bouton-poussoir momentané 16 mm chrome, fils rouge + bleu
- À ajouter : volume +, volume –, lecture/pause, piste suivante, piste précédente (5 boutons)
- Les trous non utilisés peuvent rester vides ou être obturés par des bouchons ∅ 16 mm

**Type de bouton retenu :** bouton-poussoir momentané anti-vandale 16 mm, corps métallique chromé, tête plate, filetage M16, montage par dessous avec écrou. Ex. : "16mm metal momentary push button switch chrome flat" (Amazon/AliExpress, ~1-3 €/pièce).

### 🔹 Validation gabarit (2026-06-30) ✅

Gabarit papier 1:1 imprimé et testé dans la carcasse :
- Emboîtement correct dans les bandes chromées haut/bas
- Positions HP et écran validées physiquement
- Test fonctionnel : Pi 5 + écran + HP → IHM opérationnelle (Mon Petit France Inter en lecture)
- **Gabarit validé → prêt pour commande découpe laser**

### 🔹 Procédure de validation avant fabrication
1. ✅ Mesurer la largeur exacte de la bande vinyle gauche (VINYL_W = 25mm)
2. ✅ Gabarit papier 1:1 → emboîtage dans la carcasse validé
3. ✅ Test fonctionnel avec composants réels
4. ✅ Commande découpe laser — Snijlab 2026-06-30 (livraison 08-07-2026)
5. Photo de l’intérieur câblé avant fermeture définitive

---

## 8. Schéma d’empilement matériel
Ordre recommandé :
```
[Écran tactile 7"] (HDMI + USB)
       │
[Raspberry Pi 5]
       │
[Waveshare UPS HAT (D)]
       │
[HiFiBerry Amp4]
       │
[HP gauche]   [HP droit]
```

---

## 9. Invariants matériels
Ces règles ne doivent **jamais** être violées :

- le Pi 5 doit pouvoir démarrer via RUN  
- aucun câble ne doit bloquer la ventilation  
- aucun script ne doit écrire dans le firmware  
- aucun composant ne doit être alimenté hors spécifications  
- le HAT doit toujours être correctement enfiché  
- l’écran doit rester lisible en plein jour  

---

## 10. Tests de validation
### 🔹 Test 1 : démarrage via RUN
- alimenter le HAT  
- appuyer sur le bouton RUN  
→ le Pi doit démarrer  

### 🔹 Test 2 : coupure batterie
- débrancher l’alimentation  
- laisser la batterie se vider  
→ le Pi doit s’éteindre proprement si `shutdown_pending` existe  

### 🔹 Test 3 : audio
- MPD doit sortir du son via Amp4  

### 🔹 Test 4 : écran tactile
- toucher précis  
- pas de lag  

---

## 11. Notes
- Le matériel doit rester simple, robuste et réparable  
- Toute modification matérielle doit être documentée ici  
- Le bouton RUN est critique pour l’usage enfant  

---

## 12. Tranche supérieure — Connectique et commandes

### 🔹 Vue d’ensemble
Bande chromée aluminium (longueur ~337mm, tôle ~2-3mm) — conservée et réutilisée.

**Trous existants :**
- 1 petit trou ∅6mm → LED témoin alimentation
- 1 fente rectangulaire 25×8mm → switch général batterie
- ~10 trous ronds ∅16mm → boutons et connecteurs

### 🔹 Boutons-poussoirs (boîtier réel — Grundig Concert Boy, photo 2026-07-08)

Tranche supérieure : 7 boutons-poussoirs identiques en ligne + 1 bouton isolé dans l'ancien
emplacement de l'antenne + la prise jack casque (pas un bouton). Ordre en ligne confirmé par
Thomas le 2026-07-08, du plus proche du jack au plus loin :

✅ **MAPPING DÉFINITIF** — relevé le 2026-08-17 directement dans
`scripts/buttons_daemon.py` (`PINS`, `HANDLERS`, `TAP_OR_HOLD`), qui fait foi.
Tout est câblé et en service.

| Position | Fonction | GPIO (BCM) | Comportement |
|---|---|---|---|
| RUN (démarrage Pi 5) | — | broche RUN | appui = démarrage |
| 1 (à côté du jack) | **Source** — bascule HP ↔ casque | **25** | appui simple |
| 2 | Volume − | **13** | appui + répétition au maintien |
| 3 | Épisode précédent | **17** | **tap** = épisode précédent · **maintien** = recul de 5 s par à-coup |
| 4 | Lecture / Pause | **12** | appui simple (toggle) |
| 5 | Épisode suivant | **27** | **tap** = épisode suivant · **maintien** = avance de 5 s par à-coup |
| 6 | Volume + | **5** | appui + répétition au maintien |
| 7 | **Favori** | **16** | **tap** = ajoute/retire le favori · **maintien** = ouvre l'écran Favoris |
| Bouton isolé (emplacement antenne) | **Écran Chambre** (domotique lampe + volet) | **23** | appui simple (bascule) |

`PINS = [17, 23, 27, 5, 6, 13, 16, 12, 25]` — **GPIO6 est déclaré mais sans
fonction assignée** (tombe sur `handle_unassigned`). C'est la broche de réserve.

⚠️ **GPIO4 volontairement absent** : réservé au MUTE de l'ampli sur le
HiFiBerry Amp4 (documentation officielle HiFiBerry). Ne jamais l'utiliser pour
un bouton.

📌 **Détection par polling** (10 ms), pas `add_event_detect()` : peu fiable sur
Pi 5 / puce RP1 — le premier appui est détecté, les suivants perdus. Anti-rebond
à trois niveaux dans `buttons_daemon.py`.

### 🔹 Combinaison — écran technique (TICKET-119, 2026-08-21)

| Combinaison | Durée | Effet |
|---|---|---|
| **Source (25) + Antenne (23)** simultanés | **3 s** | ouvre l'écran technique caché |

L'écran affiche le SSID et le signal Wi-Fi, les IP de chaque interface, l'état batterie, un
curseur de gain casque, et permet de fermer le kiosque. Voir `30-LECTEUR.md` §6.

⚠️ **Ces deux boutons agissent À L'APPUI, pas au relâchement** — c'est ce qui rend la
combinaison délicate. Sans précaution, l'ouvrir aurait au passage **basculé la sortie audio
et ouvert l'écran Chambre**.

**Remède** : l'action individuelle de **ces deux broches seulement** est différée de
`COMBO_GRACE_S` (300 ms). Passé ce délai, si l'autre bouton n'est pas enfoncé, l'action
part normalement ; sinon elle est abandonnée au profit de la combinaison.

📌 Les **sept autres boutons gardent leur réactivité immédiate**. Un différé global aurait
rendu la radio molle pour un enfant — c'est le genre d'arbitrage où l'usage prime sur la
simplicité du code.

La décision vit dans la classe `EtatCombinaison`, **isolée du GPIO** : elle se teste en
temps simulé, sans matériel ni attente de 3 secondes (`scripts/test_boutons.py`, 18
assertions). Restée dans la boucle de polling, elle n'aurait jamais été testée.

📌 **Depuis le 2026-08-17 (TICKET-123)** : tout front descendant, sur n'importe
quelle broche, émet en plus une frappe clavier virtuelle (`wtype -k Shift_L`)
pour signaler l'activité au compositeur. Sans ça `swayidle` ne voit jamais les
boutons et le cycle de veille de l'écran se fige. Voir `docs/75-NON_REGRESSION.md`
zone Z4.

**Étiquetage (2026-07-17)** : étiquettes transparentes Dymo sur chaque bouton de
la tranche supérieure (`Photos/06-boutons-dessus/13-boutons-etiquettes-dymo.jpg`).

**Étiquetage (2026-07-17)** : étiquettes transparentes Dymo collées sur chacun des boutons de la tranche supérieure pour identifier leur fonction (voir `Photos/06-boutons-dessus/13-boutons-etiquettes-dymo.jpg`).

**Interface GPIO** : tranchée dans la pratique — GPIO direct (`RPi.GPIO`), confirmé par le bring-up (2026-07-06/07). Détection par **polling**, pas `add_event_detect()` (peu fiable sur Pi 5/puce RP1 — 1er appui détecté, suivants perdus). GPIO17 (source/HP-casque) + GPIO23/27/5/6/13/16/12/25 libres — 6 fonctions à répartir dessus (vol-, précédent, play/pause, suivant, vol+, favori), 2 broches resteront non câblées (bouton isolé antenne + réserve). GPIO4 abandonné : réservé MUTE ampli sur HiFiBerry Amp4 (confirmé doc officielle HiFiBerry).
⚠️ Note de planification pré-bring-up, en partie dépassée depuis (le bouton "source" s'est avéré être GPIO25, pas GPIO17, et le favori est GPIO16, pas une des broches encore "à répartir") — mapping définitif confirmé dans `docs/30-LECTEUR.md` et `docs/90-BACKLOG.md` (TICKET-101/TICKET-046).

### 🔹 Alimentation — USB-C

- **Connecteur** : XMSJSIY USB-C panel mount C→C, fileté chromé, câble 1m → commandé
- Filetage à mesurer à réception (proche M22×1.5, ∅~28mm)
- **Foret étagé** : TOOLMAYS ∅4-32mm M35 AlTiN → commandé (agrandissement trous ∅16 → ~28mm)
- Courant max à vérifier à réception (cible ≥3A Pi 5 + Amp4) → voir TICKET-095

### 🔹 USB-A clavier de secours

- Prise USB-A femelle panel mount métal chromé ∅16-19mm → à chercher (voir TICKET-092)

### 🔹 Sortie casque + détection

**Composants retenus :**
- **Jack** : XMSJSIY TRS 3,5mm panel mount ∅22mm fileté chromé, câble 50cm → commandé  
  (trou ∅16mm agrandi à 22mm avec foret étagé)
  ⚠️ **À vérifier à réception** : ce modèle est très probablement un simple passe-plat 3 bornes
  (tip/ring/sleeve, type "extension cable"), **sans contact switché**. Compter les bornes : 3 = pas
  switché, 5-6 = switché (bon modèle). Si 3 bornes, recommander un jack type "TRS Socket with
  Switch" (~3-5€) — voir décision ci-dessous.
- **DAC USB** : UGREEN USB→Jack 3.5mm TRRS, classe USB Audio, zéro driver → commandé  
  Fixé en permanence à l’intérieur du boîtier.

**Détection insertion casque :**  
Le DAC USB étant branché en permanence, udev ne génère aucun événement lors de l’insertion du
casque dans le jack — il faut détecter l'insertion physique autrement.

**Historique — approche comparateur d'impédance LM393, testée et abandonnée (session du
2026-07-03) :**
Principe initial : pont résistif 100kΩ+100kΩ/100kΩ (deux branches gauche/droite) tirant vers
+3,3V, filtré par un RC (10kΩ + 100µF) vers l'entrée du LM393, comparé à une Vref (pont diviseur) —
l'idée étant que la charge du casque (16–32Ω) ferait chuter la tension mesurée.
Testé sur plaque d'essai : **ne fonctionne pas**. Tension mesurée ~1,1V que le casque soit branché
ou débranché — aucune variation détectable.
Diagnostic : le DAC USB (UGREEN) pilote activement sa sortie audio avec une impédance de sortie
basse et un asservissement interne — il impose sa tension de polarisation quoi qu'il y ait en face.
Toute mesure d'impédance passive (pont diviseur) ou injection de courant DC est donc inefficace,
le DAC absorbe/domine toujours le nœud. Seule une injection de tonalité AC hors bande audio
(20-25kHz) avec filtre passe-bande + détecteur d'enveloppe pourrait contourner ça, mais c'est un
niveau de complexité analogique (oscillateur, filtre sélectif) jugé disproportionné pour ce besoin.
→ Abandon complet de cette piste.

**Piste abandonnée elle aussi — jack à contact mécanique switché (2026-07-08) :**
Deuxième approche envisagée après l'échec du LM393 : un jack 3,5mm avec un contact NC/NO physique
s'ouvrant/se fermant purement par l'insertion de la fiche, câblé sur GPIO (pull-up + débounce
logiciel, même principe que `GpioSignalMonitor` de `scripts/battery_watchdog.py`). **Décision
Thomas (2026-07-08) : abandon définitif, irréalisable en pratique.** La détection automatique du
branchement casque n'est plus une piste active pour ce projet.

Les composants LM393/résistances/plaque pastillée déjà commandés ne sont pas perdus (réutilisables
pour d'autres briques électroniques du projet) mais ne servent plus à cette fonction précise.

**Solution retenue et définitive — bouton physique manuel :**
La bascule HP/casque se fait par un bouton-poussoir dédié, appelé "source", situé à côté de la
prise jack sur la tranche supérieure (voir tableau ci-dessous et `docs/90-BACKLOG.md` TICKET-091).
Câblé sur **GPIO25**, géré par `handle_hp_casque` dans `scripts/buttons_daemon.py` — bring-up
validé le 2026-07-07. ⚠️ **Corrigé le 2026-08-21 : ce paragraphe indiquait GPIO17**, qui est
en réalité le bouton « épisode précédent ». La source de vérité est le dict `HANDLERS` de
`buttons_daemon.py`. Ce n'est plus une étape transitoire en attendant une détection automatique :
c'est la solution finale du projet.

Le code IHM déjà en place (bascule manuelle HP/casque dans `radio.php` : `get_output`/`set_output`,
MPD 2 sorties, volumes mémorisés par mode dans `web/lecteur/index.html`) reste inchangé et
définitif — le bouton physique et le tap écran cohabitent, tous deux permanents.

### 🔹 Fente rectangulaire 25×8mm — switch général batterie

**Décision actée** : interrupteur général coupant l’alimentation batterie (≥5A continu / ~10A pic démarrage).

La fente d’origine est trop étroite pour un rocker switch standard (corps ≥13mm). Deux options non tranchées :
1. Agrandir la fente à ~25×13mm → rocker switch 10A standard
2. Utiliser un trou ∅16mm existant → toggle switch fileté M16 haute puissance chromé

→ voir TICKET-094.

### 🔹 Petit trou ∅6mm — LED témoin alimentation

- LED métal 5-6mm panel mount chromée pré-câblée, rouge ou blanche
- Câblage : résistance série 220Ω (5V) ou 100Ω (3.3V) sur rail Pi
- → à commander, voir TICKET-093

### 🔹 Tissu acoustique façade — méthode de montage

- **Tissu** : Diarypiece maille respirante noire 140×50cm — validé
- **Colle** : 3M Spray Mount 77/90, deux passes (support + envers tissu)
- Renfort optionnel : cordon néoprène/contact sur le pourtour (zones de tension aux coins)

Séquence (vis cachées sous tissu) :
1. Visser le panneau bois, têtes affleurantes
2. Coller la mousse fine par-dessus
3. Coller/tendre le tissu par-dessus la mousse

### 🔹 Récapitulatif achats — tranche supérieure

| Composant | Référence | Statut |
|---|---|---|
| Boutons M16 ×5 | Gebildet 16mm 5A inox | commandé |
| USB-C alimentation | XMSJSIY panel mount fileté | commandé |
| USB-A clavier secours | — | à chercher |
| Jack casque (passe-plat) | XMSJSIY TRS ∅22mm | commandé — à vérifier si switché (probablement non) |
| Jack casque switché | Type "TRS Socket with Switch" | à commander si le XMSJSIY n'est pas switché |
| DAC USB | UGREEN USB→Jack TRRS | commandé |
| LM393 ×10 (réutilisable ailleurs) | HUABAN DIP-8 | commandé, plus utilisé pour la détection casque |
| Foret étagé | TOOLMAYS ∅4-32mm M35 AlTiN | commandé |
| Kit PCB + résistances | Kubii | commandé |
| Visserie M3 + entretoises | Vis M3 + YIXISI laiton | commandé |
| LED témoin alim | — | à chercher |
| Switch général batterie | — | à trouver |
| Tissu acoustique | Diarypiece 140×50cm | validé |
| Colle textile | 3M Spray Mount 77/90 | recommandée |

---
