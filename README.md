# Hechicero 🎙️

Hechicero est une enceinte audio tactile DIY, conçue pour un enfant de 7 ans.

Elle permet d'écouter des podcasts en français et en espagnol, et des webradios, sans aucun compte, sans abonnement, sans cloud. L'appareil fonctionne de façon autonome, même sans connexion réseau.

---

## L'idée en une phrase

Une Tonies ou une Merlin, mais faite maison — ouverte, réparable, bilingue, et belle.

---

## Ce que voit l'enfant

Un écran tactile. De grandes images. Deux drapeaux pour choisir la langue. Des jaquettes de podcasts. Il appuie, ça joue. Pas de texte à lire, pas de menu caché, pas de risque de se perdre.

---

## Le matériel

- **Raspberry Pi 5** — le cerveau
- **HiFiBerry Amp4** — l'amplificateur audio, branché sur des enceintes passives
- **Waveshare UPS HAT (D)** — batterie intégrée avec monitoring
- **Écran CUQI 7" IPS 1024×600** — interface tactile en mode paysage
- Le tout dans un boîtier fait maison

---

## Comment ça marche

Le Pi tourne sous Raspberry Pi OS. L'interface enfant est une page web affichée en plein écran dans Chromium (mode kiosque). La lecture audio passe par MPD. Les podcasts sont téléchargés automatiquement depuis des flux RSS et stockés localement.

Trois briques indépendantes :

1. **Le lecteur** (HTML/CSS/JS) — l'interface que l'enfant voit
2. **Le backend** (Python) — ingestion RSS, génération du catalogue, monitoring batterie
3. **L'administration** (Apache + PHP) — pour le parent qui veut configurer

---

## Comment ce projet est développé

Ce projet utilise un workflow d'**IA agentique en trio** :

- **Thomas** apporte les idées, les contraintes, les tests sur le vrai matériel
- **Claude** (c'est moi) traduit les intentions en briefs techniques précis, coordonne, documente, garde la cohérence
- **Copilot Pro** dans VSCode exécute le code à partir des briefs

C'est une boucle continue : *idée → brief → code → test sur le Pi → retour → itération*.

Ce n'est pas du "vibe coding" : chaque changement est réfléchi, documenté, et validé sur le matériel réel avant de passer à la suite. L'IA accélère l'exécution sans remplacer le jugement humain.

---

## L'état du projet

Le projet est en développement actif. Les grandes briques fonctionnent :
- Lecture de webradios (France Inter, etc.)
- Téléchargement et lecture de podcasts locaux (Les Odyssées)
- Interface tactile 5 écrans en mode kiosque
- Monitoring batterie
- Conversion automatique des fichiers M4A en MP3 pour MPD

Le détail des tickets et des décisions techniques est dans `docs/`.

---

## Documentation

| Fichier | Contenu |
|---|---|
| `docs/00-manifeste.md` | Vision et principes du projet |
| `docs/05-POWER_MANAGEMENT.md` | Monitoring batterie, service systemd, shutdown propre |
| `docs/10-choix_techniques.md` | Choix d'architecture et matériel |
| `docs/15-INVARIANTS.md` | Règles absolues du projet (jamais à violer) |
| `docs/20-SETUP_SYSTEME.md` | Installation complète sur Raspberry Pi 5 |
| `docs/25-UX_GUIDELINES.md` | Règles UX IHM enfant et parent |
| `docs/30-LECTEUR.md` | Interface enfant (5 écrans, MPD, config.json) |
| `docs/40-BACKEND_RSS.md` | Pipeline d'ingestion RSS |
| `docs/50-PODCASTS_CONFIG.md` | Format et règles du fichier podcasts.json |
| `docs/55-PODCAST_SERIE_DECISIONS.md` | Série "Décisions Prises" + easter egg |
| `docs/60-KIOSK_MODE.md` | Configuration mode kiosque Chromium |
| `docs/70-SERVICES_SYSTEMD.md` | Services systemd (batterie, RSS, kiosque) |
| `docs/80-hardware.md` | Matériel, câblage, comportements Pi 5 |
| `docs/90-BACKLOG.md` | Tickets ouverts et fermés |
| `docs/99-prompt.md` | Prompt de reprise de session pour Claude |

---

---

## Licence & partage

Ce projet est partagé librement. Tu peux t'en inspirer, le forker, l'adapter, le faire évoluer.

Une seule condition : **un petit merci** — un message, une étoile GitHub, une mention dans ton propre projet. Rien de contractuel, juste un geste humain.

Ce travail est documenté en détail parce que si un jour quelqu'un veut reprendre le projet, l'améliorer, ou simplement comprendre comment c'est construit, il doit pouvoir le faire sans point de départ zéro. Tout est là : les choix, les erreurs, les raisons, le backlog.

---

*Hechicero signifie "sorcier" en espagnol. C'est le nom de code du projet.*
