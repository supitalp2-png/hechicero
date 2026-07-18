# Backlog Hechicero

> Convention : `TICKET-### — [type] — Titre — (prio) — owner`
> Dernière mise à jour : 2026-07-18 (TICKET-108 clos et déplacé en Terminé — clic épisode jouait le mauvais podcast)

---

# 🔥 Priorité haute

- [ ] TICKET-058 — feature/UX — Série podcast "Décisions Prises" + easter egg
      - Première découverte : 3 taps sur "Hechicero" à l'écran d'accueil → déverrouille + lance l'épisode 0 automatiquement
      - Accès ensuite : menu secret séparé (PAS fusionné au catalogue normal) — geste d'accès plus simple qu'au premier déverrouillage (proposition à valider : simple clic sur "Hechicero")
      - Épisode 0 ne se relance pas auto à chaque entrée dans le menu — devient un épisode normal de la liste après sa 1ère lecture
      - Hints progressifs : hint 1 vague (après X jours), hint 2 explicite (après ~1h si pas trouvé)
      - Hints jamais pendant la lecture, one-shot, disparus après découverte
      - 8 épisodes planifiés (épisode 0 d'ouverture + 7) — scripts en cours dans `docs/55-PODCAST_SERIE_DECISIONS.md`
      - Ton : léger mais sérieux (blagues assumées, sans exclure le sérieux)
      - Production : voix papa + voix IA (Descript/ElevenLabs)

---

# 🟡 Priorité moyenne

- [ ] TICKET-079 — UX/saisonnier — Mode Noël (décembre uniquement)
      - Neige animée sur la page d'accueil
      - Chapeau de Noël sur le coin des jaquettes podcast
      - Traîneau du Père Noël qui passe de temps en temps en fond d'écran
      - Actif uniquement du 1er au 31 décembre (`new Date().getMonth() === 11`)
      - Aucune dépendance réseau, aucun CDN

---

# 🟢 Priorité basse / À décider

- [ ] TICKET-030 — feature — Égaliseur audio paramétrable
      - Spécifié le 2026-07-03 (pas codé — priorité donnée à TICKET-085) :
      - Besoin : ajouter un peu de basses / son plus "rond", + clarté (compensation loudness). Deux profils indépendants : HP et casque.
      - Nouvelle page d'admin dédiée pour régler et sauvegarder les deux profils
      - Piste technique : le HiFiBerry Amp4 est un DAC pur (pas d'EQ matériel) → plugin ALSA logiciel (type `alsaequal`/LADSPA) inséré entre MPD et la carte son, une chaîne par sortie (HP / casque) dans `/etc/asound.conf` ; `/etc/mpd.conf` doit pointer vers ces devices virtuels au lieu du hardware direct
      - Loudness : compensation graves/aigus à bas volume (courbe Fletcher-Munson) — vrai loudness dynamique = complexe ; version simplifiée envisagée = preset EQ activé sous un seuil de volume donné
      - Estimation : ~45 min config système (asound.conf/mpd.conf, hors dépôt, à tester en live comme TICKET-031) + ~45 min page admin + sauvegarde par profil + ~20-30 min pour le loudness simplifié — total ~1h30-2h + itérations d'écoute
      - ⚠️ Comme pour TICKET-031, la configuration système ne peut être testée qu'en conditions réelles sur le Pi (pas de test à distance possible)
- [ ] TICKET-037 — UX — Animations simples (fade/slide) dans l'IHM enfant
- [ ] TICKET-046 — UX — Favoris (cœur) accessibles rapidement
- [ ] TICKET-047 — UX — Défilement automatique (carrousel) arrêtable par l'enfant
- [ ] TICKET-056 — R&D — Exploration client lourd natif (PyQt5/Kivy) — décision projet 2.0
- [ ] TICKET-010 — infra — Rotation logs
- [ ] TICKET-011 — sec — Durcir unités systemd (`ProtectSystem`, `NoNewPrivileges`)
- [ ] TICKET-017 — monitoring — Export Prometheus (métriques batterie/écoute)

---

# ✔️ Terminé

- [x] TICKET-102 — bug — Écran de veille et coupure d'écran cassés après l'intégration hardware finale (2026-07-08 → corrigé 2026-07-09)
      - Épisode 1 (2026-07-08 matin) : port HDMI en dur (`HDMI-A-2`) alors que l'écran était sur `HDMI-A-1` après l'intégration → `scripts/screen_dpms.sh` corrigé. Puis rendu Chromium figé (glitch au changement de port) → résolu par relance kiosk
      - Épisode 2 (2026-07-08 soir) : récidive avec un symptôme différent (écran réactif au toucher, donc pas de figement cette fois) → tracer temporaire installé (`logSleepEvent()` → action `sleep_log` de `radio.php` → `data/sleep_debug.log`) à la demande explicite de Thomas après plusieurs occurrences du même bug ("on va arrêter de penser que c'est un souci de pas de bol")
      - ✅ **Cause réelle trouvée le 2026-07-09** grâce au tracer : `checkParentalTime()` (vérif horaires parentaux, `setInterval` 30s) rechargeait la config et appelait `resetSleepTimer()` **à chaque tick, inconditionnellement** — dès que `sleep_delay` dépassait 30s, ce refresh périodique repoussait perpétuellement le timer d'inactivité, qui ne pouvait alors **jamais** atteindre son délai naturellement. C'était un vrai bug de logique, pas du hasard ni un Chromium capricieux
      - **Fix** : `applySleepConfig()` (`web/lecteur/index.html`) ne reset le timer que si la config a réellement changé (ou 1er chargement), plus à chaque refresh périodique sans rapport avec une vraie activité. Confirmé par Thomas le soir même : veille déclenchée exactement 120s après le dernier clic réel
      - Traceur (`sleep_log`/`logSleepEvent()`) laissé en place pour l'instant, à retirer une fois le fix confirmé stable dans la durée
      - Fichiers modifiés : `scripts/screen_dpms.sh`, `web/lecteur/radio.php` (action `sleep_log`), `web/lecteur/index.html` (`logSleepEvent()` + fix `applySleepConfig()`), `docs/30-LECTEUR.md`, `docs/70-SERVICES_SYSTEMD.md` (§6, wlopm→wlr-randr + table des services)
      - Découverte annexe (pas liée au bug, séparée en TICKET-106) : un objet git corrompu dans `~/hechicero`

- [x] TICKET-103 — bug — Coupure du flux webradio après une pause/reprise (2026-07-09)
      - Symptôme : sur une webradio, pause puis reprise relançait bien le son, mais le flux finissait par se couper peu après — MPD bufferisait en arrière-plan pendant la pause, `play` rejouait un buffer devenu obsolète.
      - **Fix** : action `pause` de `radio.php` distingue webradio/podcast — `stop` complet + mémorisation de l'URL sur pause webradio, reconnexion fraîche (`mpd_add_and_play()`) à la reprise au lieu de rejouer le buffer figé. Podcasts inchangés (pause/reprise à la même position).
      - ✅ Clos le 2026-07-17 (confirmé par Thomas)
      - Fichier modifié : `web/lecteur/radio.php`

- [x] TICKET-107 — bug/feature — Ingestion RSS : conserver les épisodes qui sortent du flux (surtout "Les Odyssées")
      - Trouvé le 2026-07-17 en auditant les orphelins post-ingestion (suite TICKET-104/105) : `ingest.py` reconstruisait `meta.json` **entièrement** à partir du flux RSS courant à chaque passage (pas de fusion avec l'historique). Résultat : tout épisode que le diffuseur (Radio France notamment) retire ou retitre dans son flux disparaissait silencieusement de `data.json`, alors même que le fichier audio/image restait sur le disque (jamais supprimé, invariant 1.5) — inaccessible depuis le lecteur.
      - Décision Thomas (2026-07-17) : conserver les épisodes déjà téléchargés en priorité, tant pis si ça garde occasionnellement une bande-annonce déjà présente dans un ancien `meta.json`.
      - ✅ Implémenté : `scripts/rss_ingest/parser.py::merge_episodes()` fusionne l'historique local (`meta.json` existant) avec le flux frais avant toute troncature `max_episodes` — la version fraîche l'emporte en cas de même id (métadonnées à jour), le reste est conservé tel quel et re-trié (même logique saison/numéro/date que `parse_rss()`). Câblé dans `ingest.py::ingest()`.
      - ✅ **Validé en conditions réelles le 2026-07-17** : ingestion complète relancée sur le Pi. Découverte en creusant les orphelins restants (`aladinetlesorciermalfique`, `shhrazadeconteusedegnie`, `lesincroyablesaventuresdesindbadlemarin`, `lestroisprincesamoureux`) : ces épisodes n'étaient déjà plus dans `meta.json` **avant** ce correctif (perdus lors d'une ingestion antérieure) — la fusion ne peut pas les récupérer rétroactivement, seulement empêcher que ça se reproduise désormais. Mais bonne surprise : Radio France les a en fait **republiés sous un nouveau titre/id** dans une saison "Les 1001 nuits" (`Les 1001 nuits 1/4 : Shéhérazade conteuse de génie`, `2/4 : Aladin et le sorcier maléfique`, `3/4 : Les incroyables aventures de Sindbad le marin`, `4/4 : Les trois princes amoureux`) et "Peter Pan et Wendy" → "Wendy & Peter Pan" — donc bien présents dans `data.json`/le lecteur, juste sous un id différent. Seuls restent introuvables : `odysesdudimanche03aot2025`/`odysesdudimanche20juillet2025` (rediffusions "best of" du dimanche, probablement non republiées telles quelles) — fichiers conservés sur disque, pas de perte, juste plus référencés.
      - Anciens fichiers orphelins (`aladinetlesorciermalfique.mp3` etc., doublons de contenu maintenant présent sous un nouvel id) : nettoyage disque optionnel, pas urgent.
      - ⚠️ Effet de bord accepté : plus de purge automatique, l'archive locale ne fait que grossir avec le temps (pas de souci d'espace disque identifié à ce stade, mais à surveiller si un flux change radicalement d'un coup)
      - Fichiers modifiés : `scripts/rss_ingest/parser.py`, `scripts/rss_ingest/ingest.py`, `docs/40-BACKEND_RSS.md`

- [x] TICKET-085 — infra — Sauvegarde de la carte SD (ghost durci, manuel uniquement)
      - Doc complète : `docs/85-SAUVEGARDE_RESTAURATION.md` (restauration Windows pas-à-pas + mise en place système)
      - Conçu et implémenté le 2026-07-03 — étendu en cours de session d'un simple script manuel vers un système complet, puis **simplifié le même jour** : pas de sauvegarde quotidienne automatique ("on ne sauvegarde que les évolutions majeures, soyons économes") — **durcie uniquement**, déclenchée à la main via l'admin :
          • Une seule sauvegarde vers NAS Freebox (SMB/CIFS) : **durcie**, remplacée quand Thomas valide un état stable via l'admin (bascule atomique — jamais d'état sans version durcie valide)
          • `scripts/backup_manager.py` — orchestration complète (montage NAS, `dd | gzip`, état JSON, bascule atomique)
          • `data/backup_config.json` (non-secret, versionné) + `/etc/hechicero-nas-credentials` (secret, root uniquement, hors dépôt)
          • Règle sudoers dédiée pour laisser l'admin web déclencher une validation durcie (root requis pour lire `/dev/mmcblk0` et monter le NAS) sans donner un accès root complet à www-data
          • Page admin `web/admin/backup_dashboard.php` : version durcie actuelle, taille, bouton de validation — lien visible **seulement en mode Expert** de l'admin principale (persona parent geek, pas l'autre parent)
          • `README.md` régénéré automatiquement sur le NAS à chaque sauvegarde (secours si le dépôt n'est pas accessible)
          • **Aucun SSH requis à l'usage** : clic sur "Valider une nouvelle version durcie" dans l'admin → `index.php` déclenche `backup_manager.py validate` en tâche de fond via la règle sudoers → montage NAS, ghost, bascule atomique, tout est géré côté serveur. SSH n'est nécessaire qu'une seule fois, à la mise en place initiale (§3 de la doc : fichier d'identifiants, paquets, règle sudoers) — jamais ensuite.
      - Scripts manuels créés initialement (`scripts/ghost_sd_prepare.sh`, `scripts/ghost_sd_backup.sh`) conservés pour un usage ponctuel/disque externe, mais le flux normal passe désormais par `backup_manager.py`
      - Notes réseau utiles pour la suite : `mafreebox.freebox.fr` résout vers une IP publique Free depuis le Pi (pas la Freebox locale) → utiliser l'IP de la passerelle locale (`ip route`, voir `data/backup_config.json` pour la valeur retenue — pas republiée ici, dépôt public) ; montage CIFS anonyme (`guest`) suffit pour lister les partages mais pas pour écrire, un compte Freebox est nécessaire
      - ⚠️ `dd` lit le disque système pendant qu'il tourne (pas d'arrêt des services) — snapshot pas garanti parfaitement cohérent
      - ✅ Déploiement sur le Pi réel terminé le 2026-07-03 : fichier d'identifiants, règles sudoers (www-data + thomas), paquets, hook git installé. Premier ghost réel fait (~107 GiB), enregistré comme durcie initiale. Testé de bout en bout sans montage manuel préalable (`sync_private` remonte le NAS tout seul via les identifiants).
      - ⏳ Reste : premier clic "valider durcie" *depuis l'admin web* (le tout premier a été fait en ligne de commande faute de bouton pas encore cliqué) — sinon le système est pleinement opérationnel
      - Fichiers systemd `hechicero-backup-daily.service`/`.timer` créés puis abandonnés (design quotidien annulé) — à supprimer du dépôt (`git rm etc/systemd/system/hechicero-backup-daily.*`)
      - **Ajout 2026-07-03 (même session)** : `private/` (hors git, jamais sur GitHub — réflexion perso, futurs contenus non publics type easter egg) synchronisé vers un dossier dédié du NAS, automatiquement à chaque `git commit` via un hook `.git/hooks/post-commit` (template versionné : `scripts/git_hooks_post_commit.sh`) — nouvelle commande `backup_manager.py sync_private`, règle sudoers dédiée pour l'utilisateur `thomas` (voir `docs/85-SAUVEGARDE_RESTAURATION.md` §3.3, §3.6, §5). Zéro SSH à l'usage, comme pour la durcie. `rsync` sans `--delete` : n'efface jamais rien côté NAS.
      - Penser à vérifier/documenter aussi les configs système hors git avant tout (cf. [[project_backups]] en mémoire : UPower.conf, mpd.conf, kiosk.sh, Apache vhosts, Plymouth theme) — capturées dans le ghost complet, mais bon à savoir si restauration partielle

- [x] TICKET-108 — bug — Clic sur un épisode joue un épisode d'un autre podcast (2026-07-18)
      - Symptôme rapporté par Thomas : dans la liste d'épisodes de "Tina", cliquer sur un épisode lançait un épisode des "Odyssées du Louvre".
      - Cause : `currentPodcast` (variable globale JS) servait à deux choses distinctes — le podcast dont la liste est affichée (posé par `openPodcast()`) ET le podcast réellement en cours de lecture sur MPD (resynchronisé toutes les 3s par `syncNowPlaying()`, nécessaire pour refléter les changements faits par bouton physique GPIO, TICKET-091). La boucle de poll qui déclenche cette resynchro n'est jamais arrêtée en quittant l'écran lecteur : elle continue de tourner en fond même en navigant vers la liste d'épisodes d'un autre podcast, et réécrit silencieusement `currentPodcast`. Un tap sur une ligne pendant cette fenêtre utilisait alors le mauvais `currentPodcast` avec l'index de la ligne cliquée.
      - **Fix** : `renderChapters()` capture le podcast réellement parcouru dans une variable locale (`browsedPodcast`, figée à l'affichage, immune à la resynchro en arrière-plan) et la réaffirme sur `currentPodcast` juste avant `playTrack()`, dans le handler de clic de chaque ligne.
      - ✅ Clos le 2026-07-18 (confirmé par Thomas)
      - Fichier modifié : `web/lecteur/index.html` (`renderChapters()`)

- [x] TICKET-104 — bug — Podcast TINA : images identiques, ordre incohérent, navigation bloquée en fin de saison (2026-07-09)
      - Symptômes rapportés par Thomas (généralisables à tous les podcasts RSS, pas seulement TINA — ex. Professeur Caillou) : images toujours identiques sur l'écran lecteur, épisodes affichés à l'envers, navigation suivant/précédent bloquée en fin de saison
      - Diagnostic : `web/lecteur/index.html` fixait `player-art.src` sur la jaquette du podcast entier au lieu de `ch.image` (image de l'épisode/saison) ; `parser.py` ne triait ni dédupliquait les épisodes (flux RSS pas fiable, saisons dupliquées avec dates incohérentes) ; navigation bloquée en conséquence directe de l'ordre incohérent
      - **Fix implémenté** : `ch.image || podcast.image` dans `index.html` ; dédup par id + tri chronologique à deux niveaux (saison puis numéro de titre/date) dans `parser.py` ; filtre des bandes-annonces et auto-promo Radio France ; troncature `max_episodes` par la fin (`[-max:]`) ; suppression des `reverse()` devenus inutiles
      - ✅ Suite du diagnostic (2026-07-09) : jaquette fausse (résolu, images à retélécharger), lien symbolique `web/podcasts` manquant vers `~/hechicero/podcasts` créé (404 corrigés), filtre promo élargi à "appli(cation) Radio France", tri intra-saison par numéro de titre (résout l'ordre 2 avant 1)
      - ✅ **Validé le 2026-07-17** : ingestion complète relancée sur les 23 podcasts, `check_integrity.py` confirme 0 erreur — dédup/tri/filtre tous corrects, plus de doublons ni d'ordre incohérent
      - Fichiers modifiés : `web/lecteur/index.html`, `web/lecteur/radio.php`, `scripts/rss_ingest/parser.py`, `scripts/rss_ingest/ingest.py`

- [x] TICKET-105 — bug — Synchronisation admin en échec : "Permission denied" sur meta.json.tmp, plante toute la synchro (2026-07-09)
      - Symptôme : la synchro déclenchée depuis l'admin web (tourne en `www-data`) s'arrêtait en erreur fatale à 10/22 podcasts, `PermissionError` sur `lesodysseesduchateaudeversailles/meta.json.tmp` — permission de groupe manquante sur ce dossier précis vs l'ingestion cron (tourne en `thomas`, `umask 002`)
      - **Fix implémenté (robustesse)** : chaque podcast traité dans son propre bloc `try/except` dans `ingest.py` — un podcast en échec n'interrompt plus les suivants ; `data.json` reconstruit à partir de tous les `meta.json` sur disque
      - ✅ **Cause racine corrigée le 2026-07-17** : `chgrp -R www-data` + `chmod -R g+w` sur le dossier fautif, confirmé par `check_integrity.py` (le podcast passe en `[OK]`) et une synchronisation complète des 23 podcasts sans erreur de permission
      - Fichier modifié : `scripts/rss_ingest/ingest.py`

- [x] TICKET-057 — UX/infra — Démarrage rapide de l'IHM enfant
      - Chromium mettait plusieurs secondes à démarrer après le boot
      - ✅ Clos le 2026-07-17 (confirmé par Thomas)

- [x] TICKET-068 — content — Typo ID podcast `bestiolesossiles` (manque le 'f')
      - ID interne dans `podcasts.json` : `bestiolesossiles` (manque le 'f' de "fossiles")
      - ✅ Clos le 2026-07-17 (décision Thomas) : accepté tel quel — le `label` affiché ("Les Bestioles fossiles") est correct, seul l'`id` technique (jamais visible par l'enfant ni dans l'admin) a la coquille. Renommer impliquerait de migrer le dossier audio sur disque pour un bénéfice nul, pas fait.

- [x] TICKET-087 — feature/parental — Limiteur d'exposition sonore
      - ✅ Clos le 2026-07-17 (décision Thomas) : le tracking `play_events.volume_pct` (moyenne MPD par session, enregistré depuis session 9) est jugé suffisant tel quel. Portée réduite : pas de dashboard "volume moyen par jour/podcast" ni d'avertissement de dépassement dans l'IHM enfant — abandonnés, pas nécessaires.

- [x] TICKET-001 — infra — Structure projet + liens Apache
- [x] TICKET-002 — infra — Monitoring batterie (INA219 + service systemd)
- [x] TICKET-003 — audio — HiFiBerry Amp4 + MPD opérationnel
- [x] TICKET-004 — content — Gestion multi-podcasts FR/ES
- [x] TICKET-005 — web — Interface d'administration complète (`web/index.php`)
- [x] TICKET-007 — web — Interface configuration `podcasts.json` (via admin)
- [x] TICKET-012 — test — Tests unitaires ingestion RSS
- [x] TICKET-014 — docs — Procédure de mise à jour documentée
- [x] TICKET-022 — web — Lecteur embarqué IHM enfant (`web/lecteur/index.html`)
- [x] TICKET-023 — audio — Son de démarrage (chime)
      - ✅ Accord grave, généré en WAV via `generate_chime.py`, joué via MPD
      - ✅ `kiosk.sh` : Chromium en arrière-plan, chime après sleep (délai réglable)
      - ✅ Config `chime_enabled` / `chime_volume` dans admin
- [x] TICKET-024 — audio — Lecture Webradio
- [x] TICKET-025 — backend — Ingestion RSS (Radio France)
- [x] TICKET-026 — backend — Génération automatique de `data.json`
- [x] TICKET-027 — infra — Ingestion nocturne (cron 3h, `umask 002`)
- [x] TICKET-028 — web — Nettoyage et finalisation du lecteur
- [x] TICKET-029 — backend — Quotas stockage (`max_episodes`)
- [x] TICKET-032 — infra — Installation Raspberry Pi OS avec bureau
- [x] TICKET-033 — hardware — Installation écran tactile + tests IHM
- [x] TICKET-034 — web — Activation du volume logiciel MPD
- [x] TICKET-035 — docs — Mise à jour des documents essentiels
- [x] TICKET-036 — web — Mode "grands boutons" optimisé tactile
- [x] TICKET-038 — hardware — Bouton physique RUN pour démarrage du Raspberry Pi 5
      - ✅ Installé : bouton momentané chromé M16, fils rouge+bleu → broches RUN Pi 5
      - Logé dans un trou ∅16mm de la tranche supérieure chromée
- [x] TICKET-039 — web — Démarrage automatique du lecteur (mode kiosque)
- [x] TICKET-040 — web — `app.js` supprimé (code mort)
- [x] TICKET-041 — UX — Appui sur image = pause/lecture
- [x] TICKET-042 — UX — Barre de progression + scrubbing tactile
- [x] TICKET-043 — UX — Reprise automatique de la position de lecture
- [x] TICKET-044 — UX — Flèches épisode suivant / précédent
- [x] TICKET-045 — UX — Taille des jaquettes ≥ 300×300 px
- [x] TICKET-049 — web — Images podcasts téléchargées automatiquement à l'ingest
- [x] TICKET-050 — UX — Refonte visuelle IHM enfant (5 écrans, polish)
- [x] TICKET-051 — web — Affichage batterie dans la barre de statut
- [x] TICKET-052 — UX — Barre de statut : heure + batterie
- [x] TICKET-053 — UX — Grille 2 colonnes + scroll tactile
- [x] TICKET-054 — backend — Jaquettes par épisode dans `data.json`
- [x] TICKET-055 — feature — Statistiques d'écoute + dashboard parent
      - ✅ Session 9 : refonte tracking event-driven côté serveur (`play_tracker.py`, MPD idle)
      - ✅ `volume_pct` (moyenne MPD) enregistré par session pour futur limiteur d'exposition
      - ✅ Bug radio corrigé : auto-next ne se déclenche plus quand on lance la webradio pendant un podcast
- [x] TICKET-059 — backend — Durée des épisodes via ffprobe
      - ✅ `fix_durations.py` : 365 épisodes corrigés
      - ✅ `downloader.py` : `probe_duration()` appelé après chaque téléchargement
- [x] TICKET-060 — UX — Webradio en premier dans la grille
- [x] TICKET-062 — content — Ajout 11 podcasts FR + 3 podcasts ES
- [x] TICKET-063 — UX — Barres de progression synchronisation
- [x] TICKET-064 — backend — Cover podcast téléchargée automatiquement à l'ingest
- [x] TICKET-065 — infra — Permissions Pi + cron nocturne
- [x] TICKET-066 — infra — SSL proxycast.radiofrance.fr
- [x] TICKET-067 — infra — Robustesse logs ingest
- [x] TICKET-069 — UX — Enchainement automatique des épisodes
- [x] TICKET-071 — feature/parental — Contrôle parental : grille horaire + verrou langue
      - ✅ `isNowAllowed()`, `isLangAllowed()`, polling 30s, retour home en fin de plage
- [x] TICKET-072 — bug/UX — Mini-lecteur affiche radio au lieu du podcast en cours
- [x] TICKET-073 — bug/audio — Chime race condition → déplacé dans `kiosk.sh`
- [x] TICKET-074 — bug/UX — Screensaver : refonte complète 6 modes Great Vibes
- [x] TICKET-075 — (fusionné avec TICKET-076)
- [x] TICKET-076 — UX/infra — Écran de démarrage Plymouth personnalisé (Great Vibes or)
- [x] TICKET-077 — UX — Écran de veille thémé Great Vibes (retro/modern/classic × horloge)
- [x] TICKET-078 — bug — Police Great Vibes cassée (woff2 4.5KB → TTF 445KB)
- [x] TICKET-070 — feature/analytics — Dashboard enrichi (funnel, heatmap, streak, top épisodes rejoués)
      - ✅ Tout implémenté dans `web/dashboard.php`
- [x] TICKET-080 — backend/infra — Service de collecte batterie (`scripts/battery_tracker.py`)
      - ✅ Mesure événementielle, corrélation MPD, écriture atomique, systemd actif
- [x] TICKET-081 — UX/admin — Dashboard alimentation parent (`web/admin/battery_dashboard.php`)
      - ✅ 6 blocs, Chart.js local, lien depuis l'admin
- [x] TICKET-082 — UX/enfant — Affichage autonomie + alertes 30/10 min IHM enfant
      - ✅ Temps restant, popup branchement, alertes non intrusives
- [x] TICKET-083 — infra/sécurité — Arrêt propre sur batterie critique
      - ✅ `scripts/battery_watchdog.py`, sauvegarde session, shutdown ordonné
- [x] TICKET-084 — backend — Modèle d'estimation d'autonomie (affinement progressif)
      - ✅ Ratios calculés après chaque cycle, `model_confidence` affiché
- [x] TICKET-086 — backend — Déduplication tracking JS vs play_tracker
      - ✅ Session 11 : 54 lignes de tracking JS supprimées de `web/lecteur/index.html`
- [x] TICKET-088 — bug/backend — `play_tracker.py` n'écrivait pas `listened_s` à la fermeture
      - MPD retourne `elapsed=0` quand l'état passe à "stop" → `listened_s` était systématiquement 0
      - Fix session 11 : `db_close_session` utilise `ts_end - ts_start` comme fallback si `listened_s == 0`
      - Fix session 12 : fallback capé à `duration_s` (évite `listened_s >> duration_s` si session laissée ouverte)
      - Fix DB session 12 : 10 lignes corrompues nettoyées (`listened_s` capé à `duration_s`)
      - ✅ `scripts/play_tracker.py` corrigé
- [x] TICKET-048 — backend — Script de vérification d'intégrité audio/images/data.json
      - ✅ `scripts/rss_ingest/check_integrity.py` : déjà implémenté (découvert session 12)
      - Détecte : fichiers manquants, orphelins, M4A déguisés, taille 0, divergences meta/data.json, covers absentes
      - `--podcast <id>` pour cibler un podcast ; exit code 0/1/2 (OK/WARN/ERR)
- [x] TICKET-008 — infra — Endpoint `/health` (monitoring externe)
      - ✅ Session 13 : `web/health.php` — JSON avec MPD, batterie, disque, ingest, uptime
      - HTTP 200 si tout OK, 503 si dégradé — batterie stale si > 5 min sans mise à jour
- [x] TICKET-089 — bug/backend — `battery_watchdog.py` : errno 121 code mort
      - Fix session 12 : réinitialisation INA219 déplacée à l'intérieur de `read_level()`
      - ✅ `scripts/battery_watchdog.py` corrigé
- [x] TICKET-090 — infra — Nettoyage fichiers morts dans le repo
      - ✅ Session 12 : fichiers morts supprimés via `git rm`
- [x] TICKET-096 — bug/infra — Hechicero s'éteignait au débranchement du chargeur
      - Cause : upower voyait la batterie INA219 à 0% (pas de driver ACPI) → HybridSleep au retrait du secteur
      - Fix : `CriticalPowerAction=Ignore` + `AllowRiskyCriticalPowerAction=true` dans `/etc/UPower/UPower.conf`
      - ✅ Config système hors git — à capturer dans TICKET-085 (ghost SD)
- [x] TICKET-097 — bug/infra — Extinction écran non fonctionnelle sur Pi 5 + labwc
      - `wlopm` échoue : `zwlr_output_power_management_v1` non supporté par HDMI-A-2
      - sysfs DRM `/sys/class/drm/card1-HDMI-A-2/dpms` en lecture seule même en root sur Pi 5
      - Fix : `scripts/screen_dpms.sh` utilise `wlr-randr --off/--on` (zwlr_output_management_v1)
      - ✅ `scripts/idle_screen.sh` mis à jour — pas de sudo requis
- [x] TICKET-099 — bug/ingest — acast 403 Forbidden : User-Agent manquant dans downloader.py
      - sphinx.acast.com bloquait les requêtes sans User-Agent → 0 MP3 téléchargés pour habiaunavez
      - Fix : `DEFAULT_HEADERS` avec User-Agent générique ajouté à toutes les requêtes
      - ✅ `scripts/rss_ingest/downloader.py` corrigé — habiaunavez 296 MP3 OK

- [x] TICKET-098 — bug/UX — Screensaver ne s'activait pas sur le kiosk Pi
      - Cause : écran tactile CTP `wch.cn USB2IIC_CTP_CONTROL` génère des `touchstart` fantômes sans `touchend`
      - Ces events réinitialisaient le timer screensaver en permanence
      - Fix : `wakeUp` n'écoute plus que `click` + `keydown` (un vrai tap génère `click` après `touchend`)
      - ✅ `web/lecteur/index.html` mis à jour
      - ✅ `play_tracker.py` (serveur, MPD idle) est désormais seule source de vérité
- [x] TICKET-100 — bug/UX — Radios et podcasts non instantanés sur le lecteur
      - Cause : lecteur chargeait `data.json` une seule fois au boot ; radios attendaient le cron de 3h
      - Fix PHP : `add/edit/delete_radio` → `sync_radios_to_data_json()` met `data.json` à jour immédiatement
      - Fix PHP : `delete_podcast` → retrait immédiat de `data.json`
      - Fix PHP : `add_podcast` → ingest ciblé `--podcast <id>` déclenché en background
      - Fix JS : `openRadioCatalog()` et `goToPodcasts()` rechargent `data.json` à chaque visite
      - Fix JS : `setInterval` 5 min pour config/parental (veille, contrôle parental) sans redémarrage kiosque
      - ✅ `web/index.php` + `web/lecteur/index.html` mis à jour

- [x] TICKET-061 — content — Saison 2 Professeur Caillou
      - ✅ Session 11 : 13 épisodes S2 déjà présents dans `data.json` — rien à faire
- [x] TICKET-088 — bug/tracking — `listened_s` corrompu → épisodes à 56071% de complétion
      - ✅ Session 12 : fallback `ts_end - ts_start` non borné → valeur cap à `min(elapsed, duration_s)`
      - ✅ Cap SQL dans `tracking.php` : `MIN(listened_s * 100.0 / duration_s, 100.0)`
      - ✅ Nettoyage DB : `UPDATE play_events SET listened_s=duration_s WHERE listened_s>duration_s`
- [x] TICKET-089 — bug/UX — Écran ne s'éteint pas malgré l'option activée en admin
      - ✅ Session 12 : `swayidle` mourait au boot (Wayland pas prêt), PID mort jamais relancé
      - ✅ `idle_screen.sh` : détection process mort via `kill -0 $PID`, relance automatique
- [x] TICKET-090 — bug/batterie — 51 micro-cycles factices + autonomie 12h (réelle 1.5–3h)
      - ✅ Session 12 : `charge_threshold_ma` 50 → 300 mA (élimine oscillations phase CV)
      - ✅ Formule linéaire → courbe LiPo interpolée (`battery_common.py`)
      - ✅ Filtre cycles valides : `consumed ≥ 3%` ET `duration ≥ 5 min` ET pas `invalid`
      - ✅ Estimation live basée sur `current_ma` INA219 + `battery_capacity_mah = 6600` mAh
      - ✅ Dashboard alimentation : n'affiche que les cycles valides, "Activité 24h" remplace cycle en cours
      - ✅ `battery_history.json` réinitialisé (51 cycles invalides effacés)

- [x] TICKET-095 — hardware — Vérifier courant max USB-C à réception
      - ✅ Fermé 2026-07-08 — ≥3A confirmé à réception, composant XMSJSIY gardé tel quel
- [x] TICKET-092 — hardware — Trouver prise USB-A panel mount clavier de secours
      - ❌ Annulé 2026-07-08 — accès direct au Raspberry Pi en ouvrant le boîtier si besoin de debug, pas besoin de port dédié
- [x] TICKET-094 — hardware — Trancher format switch général batterie (fente 25×8mm)
      - ❌ Annulé 2026-07-08 — plus besoin d'un switch général batterie
- [x] TICKET-093 — hardware — Trouver LED témoin alimentation ∅6mm
      - ❌ Annulé 2026-07-08 — pas envie de le faire
- [x] TICKET-091 — hardware — Choisir méthode interface GPIO boutons-poussoirs
      - Décision : (1) GPIO direct Pi 5 + `RPi.GPIO`, en **polling** (10ms) — pas MCP23017 I²C ni Pico USB HID, ni interruptions (`add_event_detect()` peu fiable sur Pi 5/RP1, 1er appui détecté seul)
      - Validée par bring-up le 2026-07-06/07 (9 broches, anti-rebond confirmé), puis par le mapping GPIO ↔ bouton et le service systemd définitif de TICKET-101
      - ✅ Documentée le 2026-07-16 dans `docs/10-choix_techniques.md` (§ Boutons physiques : GPIO direct + polling) — décision et justification actées formellement, en plus des notes de suivi ci-dessous et dans [[TICKET-101]]
      - Reste de l'historique détaillé (plan GPIO, layout boîtier, handlers, actions `radio.php`) : voir TICKET-101, qui a repris et clos le travail restant
- [x] TICKET-101 — hardware — Finalisation boutons physiques : mapping GPIO ↔ bouton + service systemd définitif
      - Suite de TICKET-091 (choix d'interface GPIO + bring-up déjà validés) et TICKET-031 (bouton "source" HP/casque)
      - ✅ **Mapping GPIO ↔ bouton confirmé le 2026-07-08** (test bouton par bouton, gauche à droite) : GPIO25 = source (HP/casque), GPIO13 = vol−, GPIO17 = précédent, GPIO12 = play/pause, GPIO27 = suivant, GPIO5 = vol+, GPIO16 = réserve (pas de fonction décidée), GPIO23 = favori (bouton isolé antenne, pas encore câblé côté logiciel — TICKET-046), GPIO6 = non câblé
      - ⚠️ GPIO17 n'est pas le bouton source dans le câblage réel (contrairement au bring-up breadboard du 2026-07-06) — c'est GPIO25. Sans impact, le dispatch est purement logiciel (`HANDLERS` dans `buttons_daemon.py`)
      - ✅ Handlers assignés dans `HANDLERS` (`scripts/buttons_daemon.py`)
      - ✅ Service systemd créé : `scripts/buttons_daemon.service` (remplace `button_toggle_test.service`, voir `docs/70-SERVICES_SYSTEMD.md` §7ter pour l'installation)
      - ✅ Service installé et testé en conditions réelles par Thomas (2026-07-08) : 3 bugs trouvés et corrigés —
          • suivant/précédent ne faisaient rien : `radio.php` lisait `mpd_status()['file']`, or la commande MPD `status` n'a PAS de champ `file:` (seul `currentsong` l'a) → ajout de `mpd_currentsong()`, utilisé par `next_episode`/`prev_episode`/`now_playing`
          • latence perçue au play/pause : polling `syncPlaybackState()`/`syncAudioMode()` resserré de 300ms à 100ms dans `index.html`
          • maintien du bouton volume ne répétait pas : rebond mécanique pendant le maintien lu à tort comme un relâchement (bloqué ensuite par le garde-fou anti-rebond) → hystérésis dédiée (`RELEASE_CONFIRM_S`), relâchement confirmé seulement après 50ms de HIGH continu
      - ✅ **Nouveau (2026-07-08)** : suivant/précédent passent en tap-ou-maintien (`TAP_OR_HOLD` dans `buttons_daemon.py`) — tap bref = épisode suivant/précédent (inchangé), maintien > `HOLD_THRESHOLD_S` (0.4s) = recherche par à-coups de `SEEK_STEP_S` (5s) dans l'épisode en cours. Nouvelle action `seek_relative` dans `radio.php` (`seekcur ±N` MPD, recherche relative à la position actuelle). Recherche en secondes fixes (pas en % de la durée) — pratique standard des lecteurs de podcasts (Apple Podcasts, YouTube). Pas encore testé en conditions réelles par Thomas — valeurs `SEEK_STEP_S`/`HOLD_THRESHOLD_S` à ajuster si besoin
      - ⏳ Reste à faire : Thomas teste le tap/maintien suivant-précédent ; décider plus tard de GPIO16 (réserve) et coder TICKET-046 pour GPIO23 (favori)

- [x] TICKET-031 — hardware/feature — Sortie casque avec bouton physique de bascule HP/casque
      - Contrainte : HiFiBerry Amp4 conservé (pas de sortie casque native)
      - Solution retenue :
          • DAC USB : KT USB Audio — branché, fonctionnel ✅
          • Jack : XMSJSIY TRS 3.5mm panel mount ∅22mm chromé — monté dans le boîtier ✅
          • MPD : 2 sorties configurées — `My ALSA Device` (HiFiBerry, HP) + `Casque USB` (DAC USB) ✅
          • ⚠️ Référencer les cartes par **nom** (`hw:CARD=sndrpihifiberry,DEV=0` / `hw:CARD=Audio,DEV=0`), jamais par numéro (`hw:N,0`) — le numéro de carte ALSA n'est pas stable d'un boot à l'autre sur ce Pi (cf. bug ci-dessous)
      - ✅ Implémenté session 14 (partiel) — bascule manuelle depuis l'IHM enfant :
          • Bouton pill dans la statusbar (toujours visible sur tous les écrans)
          • Volume mémorisé par mode (HP / casque) en localStorage
          • Séquence bascule : volume d'abord, sortie ensuite (évite pic sonore)
          • `radio.php` : get_output / set_output (MPD enableoutput/disableoutput)
          • `currentVolumeMax()` : VOLUME_MAX_SPEAKERS ou VOLUME_MAX_HEADPHONES selon mode
      - 🐛 Bug corrigé le 2026-07-03 — son sorti par le casque au boot alors que HP affiché/attendu :
          • Cause : `/etc/mpd.conf` référençait les cartes par numéro (`hw:2,0`/`hw:3,0`) ; ce numéro a dérivé entre le setup initial et aujourd'hui (HiFiBerry et DAC USB ont échangé leurs numéros) → corrigé en référençant par nom
          • `radio.php` `set_output` répondait `ok:true` même quand la commande n'atteignait pas MPD (socket pas prêt au boot) → corrigé pour vérifier la vraie réponse
          • `~/kiosk.sh` force désormais HP + volume 20% IHM avant Chromium, avec retry qui vérifie le vrai `ok:true`
          • ✅ Confirmé fonctionnel par Thomas après reboot complet
      - 🎨 Widget dashboard fatigue auditive (session 2026-07-03) — `dashboard.php` :
          • Icône oreille : silhouette tracée depuis `web/oreille.svg` (référence déposée par Thomas), couleur dynamique selon fatigue (vert/jaune/orange/rouge)
          • Zone concha/canal interne en blanc 90% opacité (le noir était invisible sur le fond bleu nuit)
          • Jauge verticale à côté (100% en haut → 0% en bas, dot qui descend avec la fatigue)
      - ❌ **Détection automatique du branchement casque abandonnée définitivement** (décision Thomas, confirmée le 2026-07-08 puis re-confirmée le 2026-07-17) : comparateur d'impédance LM393 testé sur plaque d'essai, ne fonctionne pas (tension ~1,1V que le casque soit branché ou débranché, le DAC USB pilote activement sa sortie). Piste de repli — jack à contact mécanique switché câblé sur GPIO — également irréalisable en pratique. **Le bouton physique manuel est la solution définitive**, pas une étape transitoire. Détail schéma/essais dans `docs/80-hardware.md` §"Sortie casque + détection".
      - ✅ **Test de mise en route bouton GPIO validé le 2026-07-06** (`scripts/button_toggle_test.py`, bring-up TICKET-091) :
          • Bouton physique (pull-up, appui = LOW) bascule HP↔casque de bout en bout, testé après reboot complet
          • Détection par **polling** (10ms), pas par `add_event_detect()` — peu fiable sur Pi 5/RP1
          • Antirebond à 3 niveaux (polling rapproché + confirmation logicielle + garde-fou global 400ms)
          • 🐛 Bug critique trouvé et corrigé en même temps : `radio.php` action `get_output` utilisait une regex qui supposait `outputenabled` juste après `outputname` — MPD 0.24 insère une ligne `plugin: alsa` entre les deux, donc la detection retombait toujours sur "hp", jamais "casque". Remplacé par un vrai parsing par bloc `outputid` (`mpd_output_enabled()`)
          • 🔄 **Volume mémorisé par mode déplacé côté serveur** (`data/audio_output_state.json`, plus seulement `localStorage` navigateur) — `set_output` gère lui-même la mémoire de volume et la séquence "volume d'abord, sortie ensuite", quel que soit l'appelant (IHM, GPIO)
          • Le "mode qu'on quitte" est déterminé par l'état réel MPD (`outputs`), jamais par une valeur mémorisée seule
          • Écran resynchronisé sur l'état réel toutes les 300ms (`syncAudioMode()`)
      - ✅ **Montage physique terminé** (confirmé par Thomas le 2026-07-17) : jack XMSJSIY monté dans le boîtier (simple passe-plat, pas de contact switché à exploiter), DAC USB câblé, bouton "source" GPIO25 câblé et fonctionnel en conditions réelles (mapping final TICKET-101), service `buttons_daemon.service` actif — plus rien en attente côté matériel pour ce ticket.
      - Le code IHM (bouton pill, logo, volumes mémorisés) reste définitif et cohabite avec le bouton physique GPIO.

- [x] TICKET-106 — infra — Objet git corrompu dans `~/hechicero` (`git log`/`git fsck` cassés)
      - Découvert le 2026-07-09 en marge du diagnostic TICKET-102 : `git log`/`git fsck --full` échouaient avec `error: garbage at end of loose object ... fatal: ... is corrupt` (objet `4236ac6e...`)
      - `git show HEAD:<fichier>` et `git commit`/`git push` fonctionnaient malgré tout (l'objet corrompu n'était pas un blob HEAD courant)
      - ✅ Clos le 2026-07-17 : `git log` refonctionne normalement (vérifié), et Thomas confirme que git se comporte normalement à l'usage (commits/push réguliers sans souci depuis). Cause jamais identifiée avec certitude — pas de `git fsck --full` complet re-exécuté pour confirmation formelle, mais accepté comme non bloquant vu l'usage normal prolongé.

---

# 🧩 Notes
- Repo public : aucun prénom personnel dans les fichiers versionnés (voir `15-INVARIANTS.md` §6.4)
- Prénoms réels autorisés uniquement dans `private/` (exclu du repo)
- Les tickets hardware (031, 038) sont isolés pour éviter les régressions logiciel
