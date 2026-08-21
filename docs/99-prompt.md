Tu es dans le contexte du projet **Hechicero**. Reprends à partir de ce prompt.

> *Mis à jour le 2026-08-21.*

# 1. Contexte général du projet

Hechicero est une enceinte audio **DIY**, **locale**, **hors-cloud**, destinée aux enfants.  
Elle repose sur :

- Raspberry Pi 5  
- Waveshare UPS HAT (D)  
- HiFiBerry Amp4  
- MPD (Music Player Daemon)  
- Interface enfant HTML/JS  
- Interface admin Apache/PHP  
- Scripts Python (monitoring + ingestion RSS)

Le projet doit être **robuste**, **simple**, **maintenable**, **documenté**, et utilisable **hors réseau**.

---

# 2. Architecture du projet

Arborescence réelle :

~/hechicero/
├── data/              # config.json, parental.json, tracking.db
│                      # battery_stats.json, battery_history.json, last_session.json (gitignorés)
├── docs/              # documentation
├── podcasts/          # contenus téléchargés (RSS)
│     └── <podcast_id>/
│          ├── audio/
│          ├── images/
│          └── meta.json
├── private/           # exclu du repo — scripts avec prénoms réels
├── scripts/           # Python : monitoring + ingestion RSS
│     ├── battery_common.py        # helpers partagés (INA219, MPD, écriture atomique)
│     ├── battery_tracker.py       # collecte, cycles, estimations
│     ├── battery_tracker.service  # service systemd
│     ├── battery_watchdog.py      # arrêt propre sur seuil critique
│     ├── play_tracker.py          # suivi lecture MPD idle (event-driven)
│     ├── play_tracker.service     # service systemd
│     └── rss_ingest/
├── UX Design/         # maquettes, notes UX
└── web/               # interface web (admin + lecteur)
      ├── admin/
      │     └── battery_dashboard.php   # dashboard alimentation parent
      ├── css/
      │     └── hechicero-admin.css     # CSS partagé des 3 pages admin
      ├── js/
      │     └── chart.min.js            # Chart.js 4.4.3 local (zéro CDN)
      ├── index.php
      ├── dashboard.php
      ├── tracking.php
      └── lecteur/
            ├── index.html      # fichier unique (HTML + CSS + JS)
            ├── config.json     # config avancée (chime, sleep, volumes)
            ├── data.json
            └── images/

> `app.js` et `style.css` sont du code mort (TICKET-040) — les styles et la logique sont intégrés dans `index.html`.

Règles fondamentales :
- Le **lecteur** lit `data.json` et contrôle MPD.  
- Le **backend** met à jour `data.json` et télécharge les podcasts.  
- L’**admin** affiche le statut et les infos techniques.  
- Le lecteur doit fonctionner **hors réseau**.  
- Les écritures critiques doivent être **atomiques**.  

---

# 3. Briques du système

### 🔹 Monitoring batterie
- INA219 + Python (`battery_tracker.py`, `battery_watchdog.py`, `battery_common.py`)
- `battery_tracker.service` (systemd, `Restart=on-failure`)
- Écrit `data/battery_stats.json` + `data/battery_history.json` (atomique, 664)
- Dashboard parent : `web/admin/battery_dashboard.php`  

### 🔹 Audio
- MPD + ALSA + HiFiBerry Amp4  
- Volume logiciel obligatoire  
- Support flux MP3 + fichiers locaux  

### 🔹 Lecteur embarqué (IHM enfant)
- HTML/CSS/JS  
- Fonctionne hors-ligne  
- Lit `data.json`  
- Tourne sur l’écran tactile via Chromium  

### 🔹 Admin locale
- Apache + PHP  
- Statut batterie, tests audio, diagnostics  

### 🔹 Backend RSS
- Lecture RSS  
- Téléchargement épisodes  
- Génération `meta.json`  
- Mise à jour `data.json`  

---

# 4. Méthode de travail

> ⚠️ **Réécrit le 2026-08-21.** Cette section décrivait un trio Thomas / Claude / Copilot
> Pro, où Claude rédigeait des briefs que Copilot exécutait. **Ce n'est plus le
> fonctionnement** : l'IA écrit le code directement.

**Thomas** apporte les idées, les contraintes, les arbitrages — et **tous les tests sur le
matériel réel**. C'est lui qui appuie sur les boutons, écoute le son, constate les pannes.
Aucune livraison n'est déclarée saine sans son retour.

**L'IA** analyse, écrit le code, les tests et la documentation.

Boucle : *idée → analyse → code → test sur le Pi → retour → itération*.

Le projet est aussi une démarche d'apprentissage pour Thomas : comprendre l'architecture,
les décisions techniques, et l'IA comme outil de travail.

# 4b. Règles de travail avec Thomas

- Toujours **une seule action à la fois**.  
- Toujours **clair, structuré, sans surcharge**.  
- Toujours **cohérent avec l’arborescence réelle**.  
- Toujours **mettre à jour les docs** quand une brique évolue.  
- Toujours **proposer les commandes exactes** à exécuter sur le RPi.  
- Toujours **attendre le retour de commande** avant d’avancer.  
- Toujours **expliquer ce qu’on fait et pourquoi**.  
- Toujours **penser MVP** avant complexité.  

Thomas préfère :
- les explications claires  
- les étapes progressives  
- les retours propres  
- les fichiers continus sans rupture  
- les docs cohérentes et maintenables  

---

# 5. Style attendu

Tu dois être :
- précis  
- pédagogique  
- structuré  
- cohérent  
- stable  
- fiable  

Tu dois éviter :
- le blabla inutile  
- les suppositions  
- les dépendances cachées  
- les frameworks lourds  
- la magie noire  

---

# 6. Ce que tu ne dois PAS faire

Pour garantir la stabilité du projet :

- ne jamais inventer des fichiers ou des dossiers  
- ne jamais modifier l’arborescence sans validation  
- ne jamais proposer de dépendances cloud  
- ne jamais proposer de frameworks lourds (React, Vue, Angular…)  
- ne jamais proposer de solutions non reproductibles  
- ne jamais ignorer les invariants du manifeste  
- ne jamais écrire ou modifier un fichier critique sans préciser où  
- ne jamais casser `data.json`  
- ne jamais casser MPD  
- ne jamais casser le mode kiosque  

Objectif : **zéro surprise, zéro magie, zéro casse**.

---

# 7. Objectifs du projet

### Court terme (MVP)
- Monitoring batterie  
- Webradio MPD  
- Lecteur embarqué  
- Admin locale  
- Arborescence cohérente  

### Moyen terme
- Ingestion RSS  
- Génération automatique de `data.json`  
- Gestion du contenu  

### Long terme
- Profils enfants  
- IHM native  
- Extensions matérielles  

---

# 8. Invariants

> La liste complète et à jour est dans **`15-INVARIANTS.md`** — la recopier ici la
> périmerait, comme ce fut le cas du §10. Voici seulement ce qui doit être présent à
> l'esprit dès la première ligne de code.

- le lecteur fonctionne **hors réseau**, sans cloud, sans compte
- `data.json` doit toujours rester **valide** — deux écrivains, clés disjointes
- MPD démarre automatiquement, en pause (`restore_paused`)
- **volume haut-parleurs plafonné à 80**, gain casque à 6 dB — sécurité auditive
- **aucun prénom réel** dans un fichier versionné : le dépôt est public
- **robustesse avant fonctionnalités**

⚠️ Et la règle qui porte tout le reste :

> **Un bug corrigé sans test de garde n'est pas corrigé, il est en sursis.**
> Le test doit être vérifié **en échec sur le code d'avant** — sinon il ne couvre rien.

Trois corollaires, chacun payé par un bug réel :

- **Vérifier un comportement, pas un texte.** Un garde qui cherche une chaîne casse au
  premier remaniement et finit par échouer sur sa propre documentation.
- **Valider dans l'unité de l'utilisateur.** 6 mV d'accord valent 1 point à 30 % de
  batterie et 10 points à 80 %.
- **Le code servi n'est pas celui qui s'exécute.** Recharger le kiosque, relancer le
  service, avant de conclure d'un test.

---

# 9. Phrase de reset

> “Tu es dans le contexte Hechicero. Reprends à partir de ce prompt.”

---

# 10. Où trouver l'état réel du projet

> ⚠️ **Section vidée le 2026-08-21, volontairement.** Elle contenait un instantané figé au
> **2026-06-30** — près de deux mois de retard, et une liste de « tickets ouverts
> prioritaires » dont la totalité était close depuis.
>
> **Un prompt de reprise qui recopie l'état du projet le périme mécaniquement.** Pire : il
> le périme à l'endroit exact où une IA le lira en premier, et le croira.

| Question | Où répondre |
|---|---|
| Qu'est-ce qui reste à faire ? | `90-BACKLOG.md` — l'état des lieux en tête |
| Pourquoi cette décision ? | `91-ARCHIVE-TICKETS.md`, par numéro |
| Quels pièges ne pas rejouer ? | **`75-NON_REGRESSION.md`** — à lire avant toute modification |
| Quelles règles sont absolues ? | `15-INVARIANTS.md` |
| Est-ce que ça marche encore ? | `./scripts/smoke_test.sh` |

## Source de vérité des fichiers de données

- `data/podcasts.json` → podcasts **et** radios (écrit par l'admin PHP)
- `web/lecteur/config.json` → chime, veille, extinction écran, limites de volume
- `data/config.json` → seuils et paramètres batterie
- `data/audio_eq.json` → égaliseur 10 bandes ×2 profils, **et le gain casque**
- `data/battery_stats.json` → état courant (`level`, et `level_table` pour la dérive)
- `data/battery_history.json` → cycles, purgés au-delà de 30 jours
- `web/lecteur/data.json` → catalogue servi à l'enfant. ⚠️ **Deux écrivains** : l'ingestion
  pour `podcasts`, l'admin pour `radios` — clés disjointes
- `web/` → seul répertoire servi par Apache ; `/podcasts/` n'est **pas** accessible en HTTP
- `data/tracking.db` → SQLite, historique d'écoute (gitignorée)

⚠️ **La source de vérité du mapping GPIO est `scripts/buttons_daemon.py`** (`PINS`,
`HANDLERS`, `TAP_OR_HOLD`, `COMBO_PINS`), pas la documentation.

# 11. Notes de session — leçons retenues

**Session 3 — bugs Copilot en cascade :**
- Filtre `if e.local_audio` dans `writer.py` : les épisodes sont TOUJOURS dans `data.json`
- Source des radios : `data/podcasts.json`, pas `data.json`
- Webroot Apache = `web/`, pas la racine du projet

**Session 6-7 — alimentation et UI :**
- `chart.min.js` : Coco a écrit un stub 6KB au lieu du vrai Chart.js (200KB) → toujours vérifier la taille
- `battery_stats.json` créé avec permissions `rw-------` → `www-data` ne peut pas lire → fix dans `battery_common.py`
- I2C errno 121 au redémarrage du service : erreur transitoire, se résout seule en quelques secondes

**Session 10 — extinction écran et stabilité batterie :**
- `battery_tracker.py` crashait au démarrage : log debug `/tmp/hechicero_battery_debug.log` créé par root → `PermissionError` → supprimer les blocs debug dès qu'ils sont validés
- `battery_watchdog.service` n'existait pas malgré le script → toujours créer le `.service` en même temps que le script
- `wlopm` et `swayidle` nécessitent `WAYLAND_DISPLAY=wayland-0` (pas `wayland-1`) sur ce Pi
- Courbes charge/décharge en temps relatif : `x = (ms - t0) / 60000` pour superposer les cycles
- `idle_screen.sh` : wrapper bash qui poll `config.json` toutes les 30s → swayidle relancé si délai change, pas besoin de redémarrer le service

**Session 8/9 — tracking et batterie :**
- Dashboard batterie : axe X Chart.js doit être `type: 'linear'` + `callback: ms => fmtTime(ms)`, pas `type: 'time'`
- Trous de données batterie : insérer `{x: prevMs+1, y: null}` si gap > 2h + `spanGaps: false`
- INA219 errno 121 persistant (8min+) : ajouter `reinit_ina219()` dans le catch, pas seulement un log
- `play_tracker.py` : MPD renvoie des chemins absolus (`/home/thomas/hechicero/podcasts/...`) → utiliser `Path.relative_to(PROJECT_ROOT)` avant de parser
- `idle player mixer` : les changements de volume sont des events `mixer`, pas `player` — écouter les deux
- Auto-next bug : quand `openRadioPlayer` appelle `mpd clear`, le poll voit `stop` et relance le podcast → fix : `currentPodcast = null; currentIdx = -1` avant l'appel MPD

**Session 11 — stabilisation :**
- TICKET-088 : `play_tracker.py` — MPD retourne `elapsed=0` quand état passe à "stop" → `listened_s` était 0 systématiquement → fix : `ts_end - ts_start` comme fallback
- Tracking JS supprimé de `index.html` : `play_tracker.py` est désormais seule source de vérité (plus de doublons)
- `get_status.py` et `hechicero-monitor.service` définitivement supprimés — ne pas les recréer
- Samba + git : ne jamais faire `git add / commit / push` depuis Windows (Q:\) — les index.lock corrompent le repo → toujours git sur le Pi en SSH

**Session 12 — hardware boîtier :**
- Chassis HP : les HP ont un chassis carré ~50×50mm (pas rond) avec 4 trous de vis aux coins — toujours modéliser en `cube()` pas `cylinder()`
- Bande vinyle gauche : `VINYL_W = 25mm` (pas 337mm qui est la largeur utile de la façade)
- commit_photos.sh : les originaux restent dans `Photos/` sur le Pi (jamais dans git), les copies redimensionnées vont dans `docs/photos/` — nommage `sousrep_fichier.jpg`
- Git sur Pi seulement : `git add / commit / push` uniquement en SSH sur le Pi — jamais via Samba
