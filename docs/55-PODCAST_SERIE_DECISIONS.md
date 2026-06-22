# Série Podcast — "Décisions Prises"

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

**Déclencheur** : appuyer **3 fois** sur le titre "Hechicero" dans l'écran d'accueil → la série se déverrouille et apparaît dans le catalogue.

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
- Une fois déverrouillé, la série apparaît dans le catalogue comme n'importe quel podcast (avec sa propre jaquette)

---

## Plan de la série (7 épisodes)

Alternance technique / histoire / personnel.

| # | Titre | Registre |
|---|---|---|
| 1 | Pourquoi papa a fait ça | histoire personnelle |
| 2 | C'est quoi l'électronique ? | technique |
| 3 | Comment fonctionne le cerveau de papa | personnel / intime |
| 4 | Les gens derrière le projet | humain |
| 5 | L'algo et le code | Histoire grand H + technique |
| 6 | C'est quoi un OS ? | technique (Linux) |
| 7 | C'est quoi un podcast ? | méta + clôture de série |

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

- **Ton** : chaleureux, sincère, compréhensible pour un enfant de 7 ans. Vraies histoires, pas de leçons de morale.
- **Cerveau de papa** : pas de vocabulaire médical ni d'étiquette diagnostique. Décrire l'effet concret : besoin de mordre dans du complexe pour être calme, et le revers obsessionnel.
- **Épisode algo/code** : inclure Al-Khwarizmi (étapes logiques) et Jacquard (donner des instructions à une machine).

---

## État des scripts

| Épisode | État |
|---|---|
| EP1 — Pourquoi papa a fait ça | Brouillon écrit — à retravailler |
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
- Pas de référence dans `data.json` principal — fichier séparé ou entrée masquée
- Le mécanisme de découverte (easter egg) est à concevoir — TICKET-058
- Disponible FR + ES → traduction ou double enregistrement à définir

---

## Références

- Brouillons EP1/EP2/EP3 : à ajouter dans `docs/podcast_scripts/` quand validés (fichiers non versionnés)
- TICKET-058 dans `90-BACKLOG.md` pour le suivi technique
