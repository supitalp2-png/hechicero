# Hardware — Projet Hechicero

Ce document décrit l’ensemble du matériel utilisé dans le projet Hechicero,
ainsi que les contraintes, câblages, comportements et invariants associés.

Objectifs :
- centraliser toutes les informations matérielles  
- éviter les erreurs de câblage  
- documenter les comportements spécifiques du Raspberry Pi 5  
- garantir un système stable, réparable et reproductible  

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

### 🔹 Écran tactile — Waveshare 7" 1024×600
- interface enfant principale  
- connecté en HDMI + USB (tactile)
- nécessite Raspberry Pi OS avec bureau  
- 4 trous de montage aux coins (vis M3)

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
- ne déclenche pas RUN → pas de boot automatique  
- nécessite un bouton externe  

### 🔹 Broches utiles
- I2C (INA219)  
- GPIO pass‑through  

### 🔹 Comportement en cas de batterie vide
- coupe physiquement l’alimentation  
- le Pi s’éteint brutalement si aucun shutdown anticipé  

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
- **Matériau** : contreplaqué bouleau 4 mm
- **Découpe** : laser (service en ligne — Snijlab, Sculpteo, LaserBoost)
- **Finition** : teinte ébène ou noyer + tissu acoustique noir tendu (mousse 3 mm intercalée)
- **Fixation** : vis M3 tête fraisée, noyées sous le tissu — inserts laiton M3 dans le bois
- ⚠️ **Gabarit 1:1 à valider en carton avant commande laser**

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
4. Commande découpe laser (Snijlab / Sculpteo / LaserBoost)
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

### 🔹 Boutons-poussoirs (trous ∅16mm)

| Fonction | Composant | Statut |
|---|---|---|
| RUN (démarrage Pi 5) | Momentané chromé M16, fils rouge+bleu → GPIO | ✅ installé |
| Volume + | Gebildet 16mm 5A inox tête haute bornes à vis | commandé |
| Volume – | idem | commandé |
| Lecture / Pause | idem | commandé |
| Piste suivante | idem | commandé |
| Piste précédente | idem | commandé |
| Trous restants (~4) | Bouchons flush chromés ∅16mm vissés par l’intérieur | à trouver |

**Interface GPIO** : non tranchée. Options : GPIO direct / MCP23017 I²C (préféré, évite conflit HiFiBerry) / Pico USB HID → voir TICKET-091.

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
- **DAC USB** : UGREEN USB→Jack 3.5mm TRRS, classe USB Audio, zéro driver → commandé  
  Fixé en permanence à l’intérieur du boîtier.

**Détection insertion casque — circuit LM393 :**  
Le DAC USB étant branché en permanence, udev ne génère aucun événement lors de l’insertion du casque dans le jack. La détection passe par un comparateur d’impédance.

Principe : la charge du casque (16–32Ω) fait chuter la tension sur la sortie audio du DAC. Le LM393 compare cette tension à une Vref et bascule un GPIO.

```
DAC sortie L ──┬── R1 (1kΩ) ──── IN+ (LM393 pin 3)
               │
              R2 (100Ω) ── GND
Vref (1.65V) ─────────────── IN- (LM393 pin 2)
OUT (LM393 pin 1) ── R3 pull-up 10kΩ → 3.3V ── GPIO Pi 5
```

Composants : LM393 DIP-8 ×10 (HUABAN) + résistances 1kΩ/100Ω/10kΩ + plaque pastillée (kit PCB Kubii) → commandés.  
⚠️ Schéma définitif à produire une fois le LM393 en main.

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
| Jack casque | XMSJSIY TRS ∅22mm | commandé |
| DAC USB | UGREEN USB→Jack TRRS | commandé |
| LM393 ×10 | HUABAN DIP-8 | commandé |
| Foret étagé | TOOLMAYS ∅4-32mm M35 AlTiN | commandé |
| Kit PCB + résistances | Kubii | commandé |
| Visserie M3 + entretoises | Vis M3 + YIXISI laiton | commandé |
| LED témoin alim | — | à chercher |
| Switch général batterie | — | à trouver |
| Tissu acoustique | Diarypiece 140×50cm | validé |
| Colle textile | 3M Spray Mount 77/90 | recommandée |

---
