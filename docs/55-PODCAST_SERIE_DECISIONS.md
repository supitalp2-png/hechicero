# Série Podcast — "Décisions Prises"

> *Mis à jour le 2026-08-21 — contenu inchangé, TICKET-058 toujours ouvert (2 épisodes écrits, production audio à faire).*

Série podcast générée par IA, intégrée dans Hechicero, en FR et en ES.

---

## Format

- **Voix** : dialogue deux voix (Papa + co-animateur)
- **Durée** : 10–15 min par épisode
- **Langues** : FR et ES
- **Règle absolue** : on construit le contenu de chaque épisode AVANT d'écrire le script

---

## Easter egg — Le cadeau dans le cadeau

La série est **cachée dans l'interface**. Le petit ne sait pas qu'elle existe avant de la découvrir. Elle n'est pas sur l'écran d'accueil. Elle se mérite, elle se trouve.

C'est le cadeau dans le cadeau.

### Mécanisme de découverte (validé)

**Première découverte** : appuyer **3 fois** sur le titre "Hechicero" dans l'écran d'accueil → la série se déverrouille, l'**épisode 0 se lance automatiquement**.

**Accès ensuite** : la série ne rejoint PAS le catalogue normal des podcasts — elle reste dans un **menu secret séparé**. Une fois débloqué une première fois, l'accès à ce menu redevient plus simple qu'un triple tap (proposition à valider : un simple clic sur "Hechicero" depuis l'écran d'accueil).

### Système de hints progressifs

Pour que le petit ne reste pas bloqué trop longtemps sans savoir que quelque chose l'attend, un système d'indices s'active automatiquement :

**Hint 1 — vague et mystérieux** (déclenché après une durée à définir depuis la première mise en service officielle) :
> "AS-TU ESSAYÉ D'APPUYER PLUSIEURS FOIS SUR CERTAINS BOUTONS ?"

Message affiché discrètement dans l'interface (bandeau, popup légère), puis disparaît. Ne révèle rien de précis — juste une invitation à explorer.

**Hint 2 — explicite** (déclenché après ~1h de première utilisation si l'easter egg n'a pas encore été trouvé) :
> "APPUIE 3 FOIS SUR HECHICERO"

Ce hint ne s'affiche qu'une seule fois. Une fois l'easter egg découvert, les hints ne réapparaissent jamais.

### Principes UX à respecter
- Les hints ne doivent jamais apparaître pendant la lecture
- Ton : mystérieux et invitant, jamais condescendant
- La découverte doit rester une surprise même avec les hints — le hint 1 laisse une marge d'exploration
- La série reste dans son propre menu secret, séparée des podcasts normaux — jamais mélangée au catalogue habituel, même après déverrouillage
- L'épisode 0 ne se relance pas automatiquement à chaque entrée dans le menu secret : il devient un épisode normal de la liste, au même titre que EP1-EP7, après sa première lecture automatique

---

## Plan de la série (épisode 0 d'ouverture + 7 épisodes)

Alternance technique / histoire / personnel.

| # | Titre | Registre |
|---|---|---|
| 0 | Bienvenue | ouverture / cadeau |
| 1 | Pourquoi papa a fait ça | histoire personnelle |
| 2 | C'est quoi l'électronique ? | technique |
| 3 | Comment fonctionne le cerveau de papa | personnel / intime |
| 4 | Les gens derrière le projet | humain |
| 5 | L'algo et le code | Histoire grand H + technique |
| 6 | C'est quoi un OS ? | technique (Linux) |
| 7 | C'est quoi un podcast ? | méta + clôture de série |

### Épisode 0 — format particulier

Contrairement aux épisodes 1 à 7 (dialogue deux voix), l'épisode 0 est une **voix unique** : Papa s'adresse directement à l'enfant au moment même de la découverte. Très court (~1-2 min). Il annonce le cadeau, dit l'essentiel ("un cadeau pour te dire à quel point je t'aime"), et invite à en reparler avec Papa et Maman.

À décider (technique, voir TICKET-058) : l'épisode 0 se lance-t-il automatiquement juste après le déverrouillage (3 taps), ou apparaît-il simplement en tête de la série dans le catalogue ?

---

## Personnages

- **Papa** (narrateur principal) : le papa qui a construit Hechicero
- **Le petit** : son fils, 7 ans, appelé par son prénom dans les dialogues audio
- **Le collègue** : chef de projet IT, papa, pragmatique et bienveillant, donne son avis éclairé
- **La directrice** : exigeante et disponible, apprend à tenir sous la pression
- **La maman** : sceptique au départ, convaincue par l'effort pas le résultat ; partage avec Papa la valeur fondamentale de l'essai — essayer vraiment, c'est déjà réussir quelque chose

Le collègue, la directrice et la maman apparaissent dans l'épisode 4 dédié ET en aparté dans d'autres épisodes.

> Note : les prénoms réels des personnages sont connus de l'auteur et seront utilisés dans les scripts audio — ils ne sont pas consignés ici (repo public).

---

## Conventions d'écriture

- **Ton** : léger mais sérieux — on aime faire des blagues, ça n'empêche pas d'aborder des choses sérieuses. Chaleureux, sincère, compréhensible pour un enfant de 7 ans. Vraies histoires, pas de leçons de morale.
- **Adresse affectueuse** : "mon fils", jamais "mon grand"
- **Orthographe du prénom** : une graphie précise est imposée (sans tréma) — consignée dans `private/podcast-easteregg/00-contexte.md`, jamais ici (repo public).
- **Cerveau de papa** : pas de vocabulaire médical ni d'étiquette diagnostique. Décrire l'effet concret : besoin de mordre dans du complexe pour être calme, et le revers obsessionnel.
- **Épisode algo/code** : inclure Al-Khwarizmi (étapes logiques) et Jacquard (donner des instructions à une machine).

---

## Matière narrative — EP1 : la maturation d'un projet

> Ce bloc est la matière brute pour l'épisode 1. Papa parle à "le petit" (prénom réel dans `private/` uniquement — voir invariant §6.0).
> Aucun prénom réel dans ce fichier (repo public).

### Le déclic — pourquoi Hechicero, vraiment

Tout part d'une observation simple. Le petit adore écouter des histoires sur son Merlin, en français — il en apprend énormément, il progresse, il y prend un vrai plaisir. Mais le Merlin a ses limites : il ne permet pas de faire tout ce qu'on voudrait, et surtout, rien d'équivalent n'existe en espagnol. Papa se dit alors : et si je pouvais lui offrir la même chose, mais dans les deux langues ?

C'est le déclic de départ. Pas un projet technique pour le plaisir de la technique — une envie précise, pour le petit.

### Le message central

Mais pour construire un objet comme ça, il faut d'abord comprendre une chose : un projet, ce n'est pas une idée qui apparaît seule comme une épiphanie. Il faut la mûrir, la digérer, la faire grandir. L'échec n'est pas la fin — c'est souvent le signe qu'on est encore plus proche de la solution.

### La vraie histoire d'Hechicero — les étapes

**Avant même de rencontrer le petit — l'école d'ingénieur**

Pendant ses études d'ingénieur en électronique, papa commence à bricoler avec un ami. Cet ami est très fort en électronique — papa, lui, il aimait juste ça. Ensemble ils fabriquent une horloge pour afficher l'heure. L'ami monte de son côté un ampli hi-fi classe AB qui sort un son magnifique. Papa veut faire pareil, mais n'a pas l'argent ni la connaissance. Mais il apprend une chose fondamentale : on peut bricoler des choses.

Même duo, même esprit : ils montent une webradio pour leur école d'ingénieur. Ça part d'une discussion autour d'une bière — "et si on le faisait ?" — et ils le font.

**Le premier vrai projet — la radio TSF**

Un jour, papa tombe sur une vieille radio TSF dans une brocante. L'objet est tellement beau qu'il veut le transformer. Il l'achète, le démonte pour voir comment c'est fait. L'idée : y mettre un Raspberry Pi pour en faire un lecteur de webradio.

Ça ne marche pas. Linux le bat. Il n'a pas le temps d'apprendre toutes les subtilités du système pour réussir à lire des flux, paramétrer des choses. Il se lasse. Il abandonne.

**D'autres projets — certains abandonnés, quelques-uns réussis**

Il y a d'autres tentatives entre-temps. Certaines s'arrêtent. D'autres aboutissent. Chaque fois, l'idée originale — une radio bricolée, un son fait maison, quelque chose pour un enfant — reste quelque part.

**Le bon moment arrive**

Et puis un jour, tout s'aligne. L'idée a eu le temps de grandir. Papa rencontre des gens, des passionnés qui n'ont peur de rien. Et surtout : l'IA arrive. Pouvoir poser toutes les questions et obtenir les réponses exactes dont on a besoin — formidable accélérateur. Hechicero commence.

### Ce que ça dit au petit

> Version avec prénom réel → `private/ep1-script-notes.md`

- Ça a commencé par une envie simple : te donner en espagnol ce que tu aimais déjà en français.
- Un projet, ça se mûrit. L'idée d'Hechicero a commencé à germer dans la tête de papa bien avant ta naissance.
- Un échec, c'est rarement une fin. La radio TSF n'a pas marché — mais elle a appris quelque chose. Et cette chose-là a servi plus tard.
- Les bons moments, on ne les choisit pas toujours — mais on peut s'y préparer en continuant à avancer.
- L'important, c'est d'essayer vraiment. Essayer vraiment, c'est déjà réussir quelque chose.

---

## État des scripts

| Épisode | État |
|---|---|
| EP0 — Bienvenue | Script écrit (voix unique Papa), voir `private/podcast-easteregg/ep00-brouillon-fr.md` |
| EP1 — Pourquoi papa a fait ça | Brouillon écrit (déclic Merlin/espagnol → école ingénieur → radio TSF → le bon moment), voir `private/podcast-easteregg/ep01-brouillon-fr.md` — à valider |
| EP2 — C'est quoi l'électronique ? | Brouillon écrit — à retravailler |
| EP3 — Comment fonctionne le cerveau de papa | Brouillon écrit — à retravailler |
| EP4 — Les gens derrière le projet | Plan en cours — pas de script |
| EP5 — L'algo et le code | Plan en cours — pas de script |
| EP6 — C'est quoi un OS ? | Plan en cours — pas de script |
| EP7 — C'est quoi un podcast ? | Plan en cours — pas de script |

**Aucun script définitif validé à ce jour.**

---

## Production audio — approche envisagée

Cette phase sera un jalon important du projet — pour le petit, mais aussi pour papa. Le moment où on produit les épisodes signifiera que le reste est suffisamment abouti pour qu'on s'y consacre. Un beau cadeau dans le cadeau.

### Format envisagé — 3 ingrédients

- **La vraie voix de papa** pour les passages personnels, les histoires vraies, les émotions. Ce que l'IA ne peut pas remplacer.
- **Une voix IA** pour le co-animateur (scripté, neutre, complémentaire).
- **Des vraies voix** pour certains personnages dans l'épisode 4 (le collègue, la maman, la directrice) — enregistrement simple depuis un téléphone.

### Outils envisagés (à valider quand on arrivera à cette phase)

**Descript** — workflow tout-en-un : enregistrement, génération voix IA, montage par édition de texte, nettoyage audio automatique (Studio Sound). Voice cloning possible pour corriger une phrase sans se réenregistrer. Plan Creator ~$15/mois.

**ElevenLabs** — référence qualité pour la génération de voix IA. Plan Creator $22/mois (~100 min/mois + voice cloning). À utiliser en complément d'Audacity si Descript ne convient pas.

**Audacity** (gratuit, open source) — montage final si on sépare les outils.

### Décision

Rien n'est figé. On verra exactement ce qu'on fait quand on arrivera à cette phase. L'essentiel est documenté pour ne pas repartir de zéro.

---

## Intégration dans Hechicero

- Les fichiers audio seront stockés comme les autres podcasts : `podcasts/decisions_prises/audio/`
- **Pas de fusion avec le catalogue normal** — pas de référence dans `data.json` principal, fichier séparé, menu secret dédié (pas un podcast parmi les autres)
- Le mécanisme d'accès (première découverte 3 taps + EP0 auto, puis accès simplifié — proposition : simple clic sur "Hechicero") est à concevoir techniquement — TICKET-058
- Disponible FR + ES → traduction ou double enregistrement à définir

---

## Références

- Brouillons EP1/EP2/EP3 : à ajouter dans `docs/podcast_scripts/` quand validés (fichiers non versionnés)
- TICKET-058 dans `90-BACKLOG.md` pour le suivi technique
