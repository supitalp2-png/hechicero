# Invariants — Projet Hechicero

Ce document définit les règles **absolues** du projet Hechicero.

> *Mis à jour le 2026-08-21.*
>
> ⚠️ **Un invariant peut être amendé, jamais contourné en silence.** Quand une règle est
> levée — comme « aucun menu caché » l'a été le 2026-08-21 — l'amendement est écrit ici,
> daté, avec ce qui la remplace. Un document de règles qui décrit autre chose que le
> système perd toute autorité, et le lecteur suivant prend la fonctionnalité pour un bug.

Les invariants garantissent :
- la robustesse
- la maintenabilité
- la sécurité enfant
- la cohérence du système
- la reproductibilité

---

## 1. Invariants techniques

### 🔹 1.1 Fonctionnement hors réseau
Le lecteur doit fonctionner **sans WiFi**, **sans Internet**, **sans cloud**.
Aucune dépendance externe n’est autorisée.

### 🔹 1.2 `data.json` est la source unique
- Le lecteur lit uniquement `data.json`.
- Le fichier doit toujours être **valide**, **complet**, **cohérent**.

⚠️ **Amendement du 2026-08-21.** La règle disait « le backend est le seul à pouvoir le
modifier ». C'était faux : l'administration y écrit aussi, par
`sync_radios_to_data_json()` (`web/index.php`), pour que l'ajout, la suppression ou la
**désactivation** d'une webradio soit visible immédiatement — sans quoi il faudrait
attendre l'ingestion nocturne.

**La règle réelle est donc** : deux écrivains, l'ingestion et l'administration, qui
touchent des clés **disjointes** — `podcasts` pour l'un, `radios` pour l'autre. Chacun
écrit de façon atomique et ne relit jamais l'autre pour le réécrire.

📌 C'est exactement le schéma qui a coûté neuf podcasts disparus (TICKET-130) sur
`podcasts.json` : deux sources d'autorité sur un même fichier. **Si un fichier en a deux,
il faut au minimum que la divergence soit bruyante** — d'où le contrôle de cohérence du
smoke test §2, qui vérifie que les radios servies à l'enfant sont bien incluses dans les
radios activées.

### 🔹 1.3 Écriture atomique obligatoire
Tout fichier critique doit être écrit ainsi :
1. écrire dans `<file>.tmp`  
2. valider  
3. `mv <file>.tmp <file>`  

### 🔹 1.4 MPD doit toujours démarrer automatiquement
- MPD doit être actif au boot  
- MPD ne doit jamais être bloqué par un fichier corrompu  

### 🔹 1.5 Aucun script ne doit supprimer un fichier audio existant
Sauf règle explicite (ex : quotas).

### 🔹 1.6 Aucun JSON ne doit être écrasé s’il est valide
En cas d’erreur → conserver l’ancien.

---

## 2. Invariants UX (Lecteur enfant)

### 🔹 2.1 Interface fermée — **pour l'enfant**
- aucun lien externe
- aucune navigation libre
- rien d'atteignable au doigt qui sorte du lecteur

⚠️ **Amendement du 2026-08-21.** La règle interdisait « aucun menu caché » et « aucune
possibilité de quitter Chromium ». Les deux ont été **délibérément levées** par
TICKET-119, et il faut le dire plutôt que laisser croire à une régression.

Un appui **simultané de 3 secondes** sur les boutons casque et antenne ouvre un écran
technique, qui permet notamment de fermer Chromium. C'est un outil **parent**, pour les
situations où rien d'autre n'est disponible — retrouver l'IP en déplacement, configurer un
réseau à la dalle.

**Ce qui protège l'enfant reste entier**, et c'est là que se déplace l'invariant :

- la combinaison est **hors de portée d'un usage accidentel** — deux boutons éloignés,
  maintenus ensemble trois secondes ;
- l'écran technique **n'expose aucun secret** (pas de jeton, pas d'identifiant de la
  passerelle domotique) et **n'offre aucun contournement du contrôle parental** ;
- il **revient automatiquement à la radio** après le délai de veille, donc l'enfant ne peut
  pas s'y retrouver bloqué ;
- il est protégé par l'obscurité, rien de plus : **ne jamais y mettre quoi que ce soit dont
  la divulgation poserait problème**.

### 🔹 2.2 Simplicité absolue
- grands boutons  
- zéro texte inutile  
- zéro configuration visible  

### 🔹 2.3 Volume logiciel limité

| Réglage | Plafond **invariant** | Valeur au 2026-08-21 | Où |
|---|---|---|---|
| `speakers_max` | **≤ 80** — jamais au-delà | 66 | `web/lecteur/config.json` |
| `headphones_max` | 100 assumé | 99 | idem |
| `gain_db` (casque) | **0 à 6 dB** | 4 | `data/audio_eq.json` |

Le plafond des haut-parleurs à 80 est un **invariant de sécurité auditive**. La valeur
courante (66) est un réglage ; le plafond, lui, ne se négocie pas.

Casque à 100 assumé — décision du 2026-07-17 : l'impédance plus élevée du casque de
l'enfant limite d'elle-même la puissance réelle.

⚠️ **Ajout du 2026-08-21 : le gain casque est un troisième chemin vers le volume**, séparé
de la courbe d'égalisation (TICKET-124) et réglable depuis **deux écrans** — l'admin et
l'écran technique. Son plafond de 6 dB est donc posé **dans la bibliothèque partagée**
`web/admin/eq_gain.php`, jamais dans les pages qui l'appellent : un futur appelant
l'oublierait, et ce serait un contournement silencieux du garde-fou auditif.

📌 **Les haut-parleurs n'ont pas de gain**, et ne doivent jamais en avoir — ce serait
rouvrir par la bande le plafond de 80.

### 🔹 2.4 Aucune action dangereuse
Le lecteur ne doit jamais :
- écrire sur le disque  
- modifier des fichiers système  
- lancer des commandes shell  

### 🔹 2.5 Alignement UX
Le lecteur doit respecter les règles définies dans `25-UX_GUIDELINES.md`.

---

## 3. Invariants de robustesse

### 🔹 3.1 Le système doit survivre aux coupures
- pas de corruption  
- pas de crash au boot  
- pas de dépendance réseau  

### 🔹 3.2 Les services systemd doivent redémarrer automatiquement
- batterie  
- ingestion RSS  
- MPD  

### 🔹 3.3 Aucun fichier critique ne doit être laissé partiellement écrit
(d’où l’écriture atomique).

---

## 4. Invariants de sécurité enfant

### 🔹 4.1 Aucun contenu non prévu
- pas de YouTube  
- pas de web externe  
- pas de liens cliquables  

### 🔹 4.2 Aucun risque auditif
- volume logiciel limité  
- pas de pics sonores  

### 🔹 4.3 Aucun risque d’usage
- interface stable  
- pas de crash visible  
- pas de messages techniques  

---

## 5. Invariants de maintenance

### 🔹 5.1 Arborescence stable
Aucun fichier ne doit être déplacé sans mise à jour documentaire.

### 🔹 5.2 Documentation obligatoire
Toute nouvelle brique doit avoir un fichier dans `docs/`.

### 🔹 5.3 Pas de dépendances opaques
- pas de frameworks lourds  
- pas de services cloud  
- pas de bibliothèques non maintenues  

### 🔹 5.4 Scripts lisibles
- Python simple
- pas de magie
- pas de side-effects cachés

### 🔹 5.5 Un bug corrigé sans test de garde n'est pas corrigé

C'est la règle fondatrice de `75-NON_REGRESSION.md`, et elle a sa place ici : sur ce
projet, **les pannes reviennent toujours aux mêmes endroits**. Toute panne comprise
repart avec un test qui l'empêche de revenir, et ce test doit être **vérifié en échec sur
le code d'avant le correctif** — sans quoi il ne couvre rien.

Trois règles en découlent, chacune payée par un bug réel :

- **Vérifier un comportement, pas un texte.** Un garde qui cherche une chaîne de caractères
  casse au premier remaniement légitime et finit par échouer sur sa propre documentation.
  Trois s'y sont fait prendre le même jour.
- **Valider dans l'unité de l'utilisateur.** Une convergence de 6 mV est excellente à
  mi-décharge et sans valeur sur le plateau haut d'une batterie, où elle vaut 10 points.
- **Une correction posée au point de douleur ne corrige que ce point.** Le fuseau horaire
  de PHP a mordu quatre fois avant d'être traité à la racine.

### 🔹 5.6 Le code servi n'est pas toujours le code qui s'exécute

Le kiosque garde sa page en mémoire ; un service Python garde son module. Après toute
modification, **relancer ou recharger** avant de conclure quoi que ce soit d'un test.

---

## 6. Invariants documentaires

### 🔹 6.1 Chaque fichier doit être autonome
Pas de dépendance implicite entre documents.

### 🔹 6.2 Préfixe `` pour les blocs à coller
Pour éviter l’interprétation par l’IHM.

### 🔹 6.3 Numérotation par dizaines
Permet d’insérer des fichiers sans casser l’ordre.

### 🔹 6.4 Aucun prénom personnel dans les fichiers versionnés (repo public)

Le repo est public. Aucun prénom réel (enfant, adulte, personnage) ne doit apparaître dans les fichiers versionnés.

**Règle** : utiliser `le petit`, `papa`, `le collègue`, `la maman`, `la directrice` dans tous les fichiers `docs/`.

**Exception autorisée** : le dossier `docs/private/` est exclu du repo (`.gitignore`). Les scripts audio, les notes de production avec prénoms réels, et tout contenu personnalisé s’y trouvent.

**Structure attendue** :
```
private/                          ← dans .gitignore — prénoms réels autorisés ici
  podcast-easteregg/
    ep1-script-notes.md
    ep2-script-notes.md
    ...
docs/
  55-PODCAST_SERIE_DECISIONS.md   ← version publique, sans prénoms
```

Cette règle s’applique à tous les fichiers : docs, scripts, JSON de config, commentaires de code.

---

## 7. Invariants du projet

- robustesse avant fonctionnalités  
- simplicité avant complexité  
- local avant cloud  
- enfant avant adulte  
- documentation avant implémentation  

---

## 8. Rappel
Ces invariants sont **non négociables**.
Toute évolution doit les respecter.
Toute proposition doit être évaluée à leur lumière.
