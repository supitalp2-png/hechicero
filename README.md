# Hechicero 🎙️

Hechicero est une enceinte audio tactile DIY, conçue pour un enfant de 7 ans.

Elle permet d'écouter des podcasts en français et en espagnol, et des webradios, sans aucun compte, sans abonnement, sans cloud. L'appareil fonctionne de façon autonome, sur batterie, même sans connexion réseau.

> *Documentation à jour au 2026-08-21.*

---

## Pourquoi ce projet

Mon fils est bilingue français / espagnol (Colombie), et il adore les podcasts. Jusqu'ici il écoutait sur une enceinte Merlin — un très bon produit, mais fermé : impossible d'y ajouter le moindre contenu soi-même, et son catalogue ne propose rien en espagnol d'Amérique du Sud. Résultat, il se retrouvait à écouter presque uniquement en français, alors qu'il aurait aimé retrouver la même magie dans ses deux langues.

J'ai voulu combler ce manque pour lui. Et j'avais aussi envie, en tant qu'ingénieur, de construire moi-même quelque chose plutôt que d'acheter une énième solution toute faite — de mettre mes compétences au service d'un vrai cadeau pour mon fils, pas juste d'un gadget technique. Hechicero est né de ces deux envies : répondre à un besoin réel, et lui offrir un objet fait par son père, entièrement ouvert, bilingue par construction, et qu'on peut faire évoluer ensemble.

---

## L'idée en une phrase

Une Tonies ou une Merlin, mais faite maison — ouverte, réparable, bilingue, et belle.

---

## Ce que voit l'enfant

Un écran tactile. De grandes images. Deux drapeaux pour choisir la langue. Des jaquettes de podcasts. Il appuie, ça joue. Pas de texte à lire, pas de menu caché, pas de risque de se perdre.

Et neuf boutons physiques sur la façade, parce qu'un enfant de 7 ans n'a pas toujours envie de regarder un écran pour mettre en pause : lecture, volume, épisode suivant et précédent, casque, favoris.

---

## Le matériel

- **Raspberry Pi 5** — le cerveau
- **HiFiBerry Amp4** — l'amplificateur, branché sur des enceintes passives
- **Waveshare UPS HAT (D)** — batterie 2× 21700 (EVE INR21700/58E), avec mesure de tension et de courant
- **Écran JRP7003 7" IPS 1024×600** — tactile, en mode paysage
- **9 boutons-poussoirs** câblés sur le GPIO, plus une prise casque avec bascule automatique
- Le tout dans la carcasse d'un poste **Grundig Concert Boy 206**, avec des façades bois et tissu

---

## Comment ça marche

Le Pi tourne sous Raspberry Pi OS. L'interface enfant est une page web affichée en plein écran dans Chromium (mode kiosque), sous Wayland/labwc. La lecture audio passe par MPD. Les podcasts sont téléchargés automatiquement depuis des flux RSS et stockés localement.

Trois briques indépendantes :

1. **Le lecteur** (HTML/CSS/JS) — les 8 écrans que l'enfant voit
2. **Le backend** (Python) — ingestion RSS, catalogue, suivi batterie et écoute, boutons physiques
3. **L'administration** (Apache + PHP) — pour le parent qui configure, depuis un téléphone

---

## Ce qui fonctionne aujourd'hui

**Écoute** — 39 podcasts et 5 webradios, en français et en espagnol. Lecture locale sans réseau, reprise à la position exacte, enchaînement automatique des épisodes, avance et recul dans l'épisode, favoris.

**Pour le parent** — catalogue et webradios activables un par un, contrôle parental par plage horaire et par langue, égaliseur 10 bandes avec deux profils (haut-parleurs et casque), gain casque séparé, statistiques d'écoute, tableau de bord batterie, sauvegarde de la carte SD.

**Autonomie** — mesure du niveau par table de tension recalibrée sur les cellules réelles, corrigée de l'affaissement sous charge, avec comptage coulométrique en haut de plage. Arrêt propre avant la décharge profonde, prouvé en conditions réelles.

**Détails qui comptent** — écran de veille thémé, mode Noël en décembre et mode anniversaire le jour dit, écran de contrôle de la lampe et du volet de la chambre, écran technique caché ouvert par une combinaison de boutons pour retrouver l'IP en déplacement.

---

## Comment ce projet est développé

Ce projet est construit avec l'aide d'une **IA agentique**, dans une boucle continue :
*idée → analyse → code → test sur le Pi → retour → itération*.

Thomas apporte les idées, les contraintes et **tous les tests sur le vrai matériel** — c'est lui qui appuie sur les boutons, écoute le son et constate les pannes. L'IA analyse, écrit le code, et documente.

Ce n'est pas du « vibe coding ». Chaque changement passe par un registre de non-régression (`docs/75-NON_REGRESSION.md`) qui recense les pièges déjà rencontrés, et par un smoke test de plus de 85 contrôles automatiques. **Un bug corrigé sans test de garde ajouté n'est pas corrigé, il est en sursis** — c'est la règle fondatrice du projet.

Ce qui a le plus fait progresser la qualité tient en deux principes appris à la dure :

- **Vérifier un comportement, pas un texte.** Un test qui cherche une chaîne de caractères finit par échouer sur sa propre documentation.
- **Valider dans l'unité de l'utilisateur.** Une convergence de 6 mV est excellente à mi-décharge et sans aucune valeur sur le plateau haut d'une batterie Li-ion, où elle vaut 10 points de pourcentage.

---

## Reprendre ce projet

Cette documentation est écrite pour quelqu'un qui voudrait comprendre le projet, le
reprendre, ou en construire un semblable. Voici l'ordre qui fait gagner le plus de temps.

**Pour décider si ça vous intéresse** — lisez `00-manifeste.md` (les principes, et
pourquoi certaines facilités ont été refusées) puis `10-choix_techniques.md` (ce qui a
été choisi, et surtout ce qui a été écarté et pour quelle raison).

**Pour construire la même chose** — `80-hardware.md` donne le matériel et le câblage
exact, `20-SETUP_SYSTEME.md` l'installation de bout en bout, `60-KIOSK_MODE.md` et
`70-SERVICES_SYSTEMD.md` la mise en service. Comptez que le câblage GPIO et l'audio
sont les deux étapes où l'on perd du temps.

**Avant de modifier quoi que ce soit** — `15-INVARIANTS.md` (les règles qu'on ne
transgresse jamais, comme la limite de volume des haut-parleurs) et surtout
`75-NON_REGRESSION.md`. Ce dernier recense les pièges déjà payés : un service durci qui
ne peut plus écrire son fichier de travail, un `wlr-randr` qui ne fait rien sans le dire,
`swayidle` qui ne voit pas les boutons GPIO, une table de conversion qui ne vaut rien
sans sa compensation. **Ce document existe parce que sur ce projet, les bugs reviennent
toujours aux mêmes endroits.**

**Pour comprendre une décision précise** — `90-BACKLOG.md` liste les tickets clos en une
ligne, et `91-ARCHIVE-TICKETS.md` contient le raisonnement complet de chacun : le
symptôme, ce qui a été mesuré, les hypothèses écartées et pourquoi. Les erreurs de
diagnostic y sont conservées, pas effacées — savoir qu'une piste a déjà été suivie et
démentie vaut souvent plus que la solution finale.

**Avant de livrer** — `./scripts/smoke_test.sh`. Plus de 85 contrôles, moins d'une
minute, sans effet de bord : il tourne pendant que l'enfant écoute.

### Ce qui est spécifique à ce montage

Trois choses ne se transposeront pas telles quelles :

- Le boîtier est une carcasse de **Grundig Concert Boy 206**, avec des découpes faites
  pour ses dimensions.
- L'écran Chambre pilote une installation **Legrand/Netatmo** personnelle, via une
  passerelle décrite dans `95-DOMOTIQUE_CHAMBRE.md`. C'est le module le plus facile à
  retirer si vous n'en avez pas l'usage.
- Le catalogue est un choix de podcasts francophones et hispanophones pour un enfant de
  7 ans. Il se remplace entièrement depuis l'interface d'administration.

---

## Documentation

| Fichier | Contenu |
|---|---|
| `docs/00-manifeste.md` | Vision et principes du projet |
| `docs/05-POWER_MANAGEMENT.md` | Batterie : mesure, seuils, tableau de bord, arrêt propre |
| `docs/10-choix_techniques.md` | Choix d'architecture et matériel |
| `docs/15-INVARIANTS.md` | Règles absolues du projet (jamais à violer) |
| `docs/20-SETUP_SYSTEME.md` | Installation complète sur Raspberry Pi 5 |
| `docs/25-UX_GUIDELINES.md` | Règles UX, interfaces enfant et parent |
| `docs/30-LECTEUR.md` | Interface enfant : les 8 écrans, MPD, config |
| `docs/40-BACKEND_RSS.md` | Pipeline d'ingestion RSS |
| `docs/50-PODCASTS_CONFIG.md` | Format et règles de `podcasts.json` |
| `docs/55-PODCAST_SERIE_DECISIONS.md` | Série « Décisions Prises » + easter egg |
| `docs/60-KIOSK_MODE.md` | Mode kiosque Chromium |
| `docs/70-SERVICES_SYSTEMD.md` | Les services systemd et leurs pièges |
| **`docs/75-NON_REGRESSION.md`** | **Registre des zones à risque — la mémoire des pannes** |
| `docs/80-hardware.md` | Matériel, câblage, comportements du Pi 5 |
| `docs/85-SAUVEGARDE_RESTAURATION.md` | Sauvegarde de la carte SD et restauration |
| `docs/90-BACKLOG.md` | Tickets ouverts, registre des tickets clos |
| `docs/91-ARCHIVE-TICKETS.md` | Le détail de chaque ticket clos, à consulter par numéro |
| `docs/95-DOMOTIQUE_CHAMBRE.md` | Écran Chambre : passerelle Netatmo, lampe et volet |
| `docs/99-prompt.md` | Prompt de reprise de session |

Si vous ne devez en lire qu'un : **`75-NON_REGRESSION.md`**. C'est là que sont les pièges, et pourquoi ils ont coûté cher.

---

## Licence & partage

Ce projet est partagé librement. Vous pouvez vous en inspirer, le forker, l'adapter, le faire évoluer.

Une seule condition : **un petit merci** — un message, une étoile GitHub, une mention dans votre propre projet. Rien de contractuel, juste un geste humain.

Ce travail est documenté en détail parce que si un jour quelqu'un veut reprendre le projet, l'améliorer, ou simplement comprendre comment c'est construit, il doit pouvoir le faire sans repartir de zéro. Tout est là : les choix, les erreurs, les raisons.

---

*Hechicero signifie « sorcier » en espagnol. C'est le nom de code du projet.*
