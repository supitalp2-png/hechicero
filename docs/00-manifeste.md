# Manifeste du projet Hechicero

> Ce document dit **pourquoi** le projet est fait ainsi. Les autres disent comment.
> Si vous reprenez ce travail et qu'une décision vous surprend, la réponse est
> probablement ici — ou dans `75-NON_REGRESSION.md`, qui garde la mémoire des pannes.
>
> *Mis à jour le 2026-08-21.*

---

## 1. Ce qu'est Hechicero

Une enceinte à podcasts pour un enfant de 7 ans, bilingue français/espagnol, construite
dans la carcasse d'un poste de radio des années 1960. Elle fonctionne **sur batterie et
sans réseau**, parce qu'un enfant ne doit pas dépendre d'une box qui redémarre.

Elle doit être compréhensible, réparable, évolutive — et surtout **fiable au quotidien**.
Ce n'est pas un démonstrateur technique : c'est un objet dont quelqu'un se sert tous les
jours, et qui doit marcher quand on appuie sur le bouton.

---

## 2. Les principes qui décident

### 🔹 L'enfant d'abord, toujours

Devant un arbitrage entre élégance technique et expérience de l'enfant, l'enfant gagne.
Un exemple concret : les actions des boutons physiques ne sont jamais différées pour
simplifier le code — sauf pour deux d'entre eux, sur 300 ms, parce qu'il n'y avait pas
d'autre moyen d'ajouter une combinaison sans effets de bord. **Sept boutons sur neuf
gardent leur réactivité immédiate.**

Corollaire : **une panne silencieuse est pire qu'une panne bruyante.** Un indicateur qui
affiche une valeur périmée mais plausible est plus nuisible qu'un indicateur absent.

### 🔹 Briques indépendantes

Chaque fonction est isolée et remplaçable : batterie, audio, lecteur, administration,
ingestion, boutons. Une brique évolue sans casser les autres.

⚠️ **La contrepartie est réelle** : quand deux briques doivent s'accorder, personne ne
surveille l'accord. Le bug le plus long à trouver du projet venait de deux minuteries de
veille correctes séparément et incohérentes ensemble. **Deux réglages libres finissent
toujours par diverger** — il faut une source unique de vérité.

### 🔹 Autonomie réelle

Sans réseau, sans cloud, sans compte, sans API externe. Un podcast téléchargé se lit même
si la box est morte. Toute évolution qui rendrait une fonction **locale** dépendante du
réseau doit être refusée.

### 🔹 Sécurité de l'enfant, non négociable

Le volume des haut-parleurs est plafonné (`speakers_max ≤ 80`), et le gain casque est
borné séparément. Ces limites sont posées **dans le code partagé**, jamais dans les pages
qui l'appellent : un futur appelant les oublierait. Voir `15-INVARIANTS.md`.

### 🔹 Le dépôt est public, l'enfant ne l'est pas

Aucun prénom réel dans un fichier, un nom de fichier, un commentaire ou un message de
commit. On écrit « mon fils », « le petit », « papa ». Un prénom parti dans un commit
reste dans l'historique git — ça ne se rattrape pas. `scripts/check_privacy.sh` est le
filet, jamais la seule barrière.

---

## 3. Les règles apprises à la dure

Elles ne viennent pas d'une méthode, mais de bugs payés cher. Chacune a un ticket derrière.

**Un bug corrigé sans test de garde n'est pas corrigé, il est en sursis.**
C'est la règle fondatrice de `75-NON_REGRESSION.md`. Les pannes de ce projet reviennent
toujours aux mêmes endroits.

**Vérifier un comportement, pas un texte.**
Un test qui cherche une chaîne de caractères casse au premier remaniement légitime, et
finit par échouer sur sa propre documentation. Trois gardes s'y sont fait prendre le même
jour. Le bon test exécute la fonction et regarde ce qu'elle répond.

**Valider dans l'unité de l'utilisateur.**
Une convergence de 6 mV est excellente à mi-décharge et sans aucune valeur sur le plateau
haut d'une batterie Li-ion, où elle vaut 10 points de pourcentage. Une métrique exprimée
dans une autre unité que le produit ne valide rien.

**Une correction posée au point de douleur ne corrige que ce point.**
Le fuseau horaire de PHP a mordu quatre fois. Les trois premières, on a posé une rustine
là où ça faisait mal, et le défaut est revenu ailleurs sous un autre visage.

**Le pire bug est le bug latent.**
Un durcissement qui ne casse rien aujourd'hui parce qu'un vieux fichier traîne encore, et
qui tuera l'appareil dans trois semaines — ou à la première restauration de sauvegarde.
Devant tout changement de configuration système, se demander : *est-ce que ça marcherait
sur une carte SD fraîche ?*

**Instrumenter plutôt que deviner.**
Sur un bug qui revient, une hypothèse de plus ne vaut rien. Poser une mesure qui produira
une preuve au prochain déclenchement. Cette règle a résolu le bug de l'écran noir — et,
mieux, elle a permis de l'**innocenter** : l'instrumentation a prouvé que la piste
suivie depuis des semaines était la mauvaise.

**Le code servi n'est pas toujours le code qui s'exécute.**
Le kiosque garde sa page en mémoire. Une modification du lecteur exige un rechargement,
sinon on teste l'ancienne version en croyant tester la nouvelle.

---

## 4. Ce qui a été refusé, et pourquoi

| Refusé | Raison |
|---|---|
| Client lourd natif (Qt, Kivy) | La page web fait le travail ; réécrire tout aurait coûté des mois pour un gain nul côté enfant |
| Relance automatique du kiosque | Choix assumé : un redémarrage manuel vaut mieux qu'un service qui masque un problème |
| Uniformiser les réponses de `radio.php` en JSON | L'interface enfant lit du texte MPD brut ; le changement casserait le lecteur |
| Ventilateur GPIO | Le throttling thermique existe mais reste sans effet sur la lecture audio |
| Coupure matérielle de la batterie à l'arrêt | Risque assumé après mesure ; l'interrupteur du HAT n'est pas accessible dans le boîtier |
| Régler l'égaliseur 10 bandes sur l'écran tactile | Impraticable au doigt sur 7 pouces, et l'administration le fait déjà bien depuis un téléphone |

---

## 5. Ce que Hechicero n'est pas

Pas une enceinte cloud. Pas un produit commercial. Pas une usine à gaz. Pas un système
dépendant d'API externes.

C'est un projet **personnel, pédagogique et familial**, conçu pour durer — et documenté
pour que quelqu'un d'autre puisse le reprendre.
