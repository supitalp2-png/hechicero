# Backlog Hechicero

> Convention : `TICKET-### — [type] — Titre — (prio) — owner`
> Dernière mise à jour : 2026-06-25 (session 5)

---

# ✔️ Terminé

- [x] TICKET-001 — infra — Structure projet + liens Apache
- [x] TICKET-002 — infra — Monitoring batterie (INA219 + service systemd)
- [x] TICKET-003 — audio — HiFiBerry Amp4 + MPD opérationnel
- [x] TICKET-024 — audio — Lecture Webradio
- [x] TICKET-025 — backend — Ingestion RSS (Radio France)
- [x] TICKET-026 — backend — Génération automatique de `data.json`
- [x] TICKET-028 — web — Nettoyage et finalisation du lecteur (2026-06-21)
      - ✅ Paramètre `path` uniformisé dans `playTrack()` et `playBtn`
      - ✅ Balise orpheline `<a href="radio.php">` supprimée
      - ✅ Texte de debug retiré de l'écran player
      - ✅ Polling MPD conditionnel (démarré à l'ouverture player, stoppé au retour)
- [x] TICKET-032 — infra — Installation Raspberry Pi OS avec bureau
- [x] TICKET-033 — hardware — Installation écran tactile + tests IHM
- [x] TICKET-034 — web — Activation du volume logiciel MPD
- [x] TICKET-039 — web — Démarrage automatique du lecteur (mode kiosque) (2026-06-21)
- [x] TICKET-041 — UX — Appui sur image = pause/lecture (2026-06-22)
      - ✅ overlay `.art-overlay` sur la jaquette player, toggle pause/play au tap
- [x] TICKET-042 — UX — Barre de progression dans l'écran player (2026-06-22)
      - ✅ `#prog-fill` + scrubbing tactile via `touchstart/touchmove` sur la barre
- [x] TICKET-043 — UX — Reprise automatique de la position de lecture (2026-06-22)
      - ✅ position sauvegardée dans `localStorage` (`hech_prog`), restaurée au lancement d'un épisode
- [x] TICKET-044 — UX — Flèches épisode suivant / précédent (2026-06-22)
      - ✅ boutons ⏮⏭ (`btn-prev` / `btn-next`) dans le player
- [x] TICKET-051 — web — Affichage batterie dans la barre de statut (2026-06-22)
      - ✅ `navigator.getBattery()` bloqué dans Chromium → fallback `fetch('../status.json')` toutes les 30 s
      - ✅ Champ lu : `d.percent` (validé sur le Pi : `{"percent": 91, ...}`)
      - ✅ Détection charge via `d.state`
      - ✅ Validé après reboot : batterie visible dans la barre de statut
- [x] TICKET-052 — UX — Barre de statut : heure 15px/600, batterie 14px, hauteur 32px (2026-06-22)
- [x] TICKET-053 — UX — Grille 2 colonnes épisodes + webradios, scroll tactile (2026-06-22)
- [x] TICKET-054 — backend — Jaquettes par épisode dans data.json (2026-06-22)
      - ✅ writer.py : champ `image` ajouté par épisode
      - ✅ index.html : ep-thumb utilise `ch.image` avec fallback jaquette podcast
- [x] TICKET-060 — UX — Webradio en premier dans la grille (2026-06-22)
      - ✅ `grid.insertBefore(w, grid.firstChild)` dans `renderPodcasts()`
- [x] TICKET-062 — content — Ajout 11 podcasts FR + 3 podcasts ES (2026-06-22)
      - FR : Olma, Allô Olma, Bestioles, Bestioles sous l'océan, Bestioles fossiles, Bestioles olympiques
      - ES : Cráneo, Camaleón, Buenas noches Cráneo (Cumbre Kids — accent latinoaméricain)
      - Professeur Caillou : RSS migré vers Aerion (saison 2 potentiellement disponible)
      - Typo corrigé : `bestiolesympiques` → `bestiolesolympiques`
- [x] TICKET-005 — web — Interface d'administration complète (2026-06-23)
      - ✅ `web/index.php` : état système, gestion podcasts/radios, config volume, synchro
      - ✅ Mode normal / expert (localStorage)
      - ✅ Deux colonnes FR | ES pour podcasts et radios
      - ✅ Formulaires en haut (mode expert), edit inline par item
      - ✅ Copier l'URL du flux (mode expert)
      - ✅ Select max épisodes (5/10/20/50/∞) modifiable par podcast
      - ✅ Image webradio : URL → téléchargement automatique sur le Pi (shell curl)
      - ✅ Validation des flux avant ajout (RSS + stream)
      - ✅ Responsive automatique via media query (≤900px → colonne unique)
      - ✅ Batterie : chemin STATUS_JSON corrigé (`web/status.json`)
- [x] TICKET-049 — web — Images podcasts non affichées (2026-06-23)
      - ✅ `cover.jpg` téléchargée automatiquement depuis le flux RSS à chaque ingest
      - ✅ `writer.py` utilise `/podcasts/{id}/cover.jpg` dans `data.json`
      - Fallback : `images/{id}.jpg` si cover absente
- [x] TICKET-063 — UX — Barres de progression synchronisation (2026-06-23)
      - ✅ `progress.py` : fichier JSON temps réel `/tmp/hechicero_progress.json`
      - ✅ `ingest.py` : appels progress à chaque podcast + épisode
      - ✅ IHM : barre podcasts (dorée) + barre épisodes (bleue) + message final
      - ✅ Erreurs résumées proprement (pas de log brut dans l'IHM)
      - ✅ Logs techniques en accordéon mode expert uniquement
- [x] TICKET-064 — backend — Cover podcast téléchargée automatiquement à l'ingest (2026-06-23)
      - ✅ `models.py` : champ `cover_image` dans `PodcastMeta`
      - ✅ `ingest.py` : téléchargement `cover.jpg` depuis l'image RSS épisode 1
      - ✅ `writer.py` : `cover_web` injecté dans `data.json` à la place de `images/{id}.jpg`
      - ✅ `writer.py` : radios lues depuis `podcasts.json` (source de vérité unique)
- [x] TICKET-065 — infra — Permissions Pi + cron nocturne (2026-06-23)
      - ✅ `sudo chown -R thomas:www-data` + `chmod 775` sur podcasts/, web/lecteur/, data/, logs/
      - ✅ `thomas` ajouté au groupe www-data (plus de conflits futurs)
      - ✅ `php-mbstring` installé (Fatal Error sur slugify() résolu)
      - ✅ Cron 3h du matin : `umask 002 && python3 ingest.py`
- [x] TICKET-066 — infra — SSL proxycast.radiofrance.fr (2026-06-23)
      - ✅ `SSL_NO_VERIFY_HOSTS` étendu à `radio-france-rss.aerion.workers.dev`
      - ✅ Le flag `verify=False` suit maintenant la chaîne de redirection → épisodes téléchargés
- [x] TICKET-067 — infra — Robustesse logs ingest (2026-06-23)
      - ✅ `utils.py` : fallback `/tmp/hechicero_rss_ingest.log` si `logs/` non accessible par www-data
- [x] TICKET-055 — feature — Statistiques d'écoute + dashboard parent (2026-06-24)
      - ✅ `web/tracking.php` : SQLite via PDO, table `play_events`, actions start/progress/end/stats
      - ✅ `web/dashboard.php` : bar chart FR/ES style Kibana + camembert répartition journée
      - ✅ `scripts/seed_tracking.py` : générateur de données de test (20 écoutes simulées)
      - ✅ Lien 📊 Dashboard dans l'admin
      - Phase 2 → TICKET-070
- [x] TICKET-069 — UX — Enchainement automatique des épisodes (2026-06-24)
      - ✅ Détection transition `play → stop` dans `refreshStatus()` via `lastMpdState`
      - ✅ `playTrack(currentIdx + 1)` si épisodes restants, sinon stop propre
- [x] TICKET-023 — audio — Son de démarrage (chime) au lancement du lecteur (2026-06-24)
      - ✅ `playStartupChime(volume)` — accord chaud C4–G4–C5–E5 via Web Audio API (pas de fichier audio)
      - ✅ Reverb léger, attaque douce, queue ~3 s
      - ✅ Config dans `web/lecteur/config.json` : `chime_enabled`, `chime_volume` (0–100)
      - ⚠️ À tester sur Pi : Chromium peut bloquer l'AudioContext sans interaction utilisateur préalable

---

# 🔥 Priorité haute (en cours)

- [ ] TICKET-022 — web — Lecteur embarqué (IHM enfant)
- [ ] TICKET-027 — infra — Service systemd + timer pour ingestion RSS
      - Note : le cron (`0 3 * * *`) est actif en production — ce ticket vise à migrer vers un timer systemd propre
- [ ] TICKET-031 — hardware/feature — Sortie casque avec bascule automatique haut-parleurs
      - Contrainte : HiFiBerry Amp4 conservé (pas de sortie casque native)
      - Solution validée :
          • Dongle USB audio (ex: UGREEN ~8€) → Amazon FR → sortie casque
          • Jack 3.5mm commuté PJ-392 panel-mount → Gotronic ou AliExpress
          • Résistor pull-up 10kΩ entre contact switch du jack et GPIO 3.3V
          • Script Python GPIO : détecte insertion → mpc disable sortie speakers + mpc enable sortie casque
          • MPD configuré avec 2 audio_output : HiFiBerry (ALSA hw:0) + USB (ALSA hw:1)
      - Priorité : moyenne (à traiter après TICKET-050 refonte IHM)
- [ ] TICKET-035 — docs — Mise à jour des documents essentiels (phase 1)
- [ ] TICKET-038 — hardware — Bouton physique RUN pour démarrage du Raspberry Pi 5
      - Problème : le Pi 5 ne démarre pas automatiquement avec le Waveshare UPS HAT (D)
      - Objectif : ajouter un bouton externe relié aux broches RUN
      - Priorité : Haute (bloquant pour usage enfant)
- [ ] TICKET-040 — web — `app.js` mort à supprimer ou refactoriser
      - `app.js` contient une ancienne version de la logique, non connectée à `index.html`
      - Décision : soit supprimer, soit externaliser la logique de `index.html` vers `app.js`
- [ ] TICKET-050 — UX — Refonte visuelle de l'IHM enfant
      - Architecture 5 écrans validée et implémentée
      - Reste : images, finitions, polish
- [ ] TICKET-073 — bug/audio — Chime : race condition touchstart avant fin du fetch parental_status
      - Symptôme : le chime ne se joue pas au démarrage malgré `chime_enabled: true`
      - Cause : le listener `touchstart` est posé DANS le callback de `loadParentalConfig()` (fetch async)
        Si l'enfant (ou un event fantôme) touche l'écran avant que le fetch revienne, le touch est manqué
        Le listener se pose après — et attend un prochain touch qui ne vient pas
      - Fix : mémoriser si un touch s'est produit avant la fin du fetch, jouer le chime immédiatement dans ce cas
        ```js
        let pendingChimeTouch = false;
        document.addEventListener('touchstart', () => { pendingChimeTouch = true; }, { once: true });
        // puis dans loadParentalConfig() callback :
        if (parentalCfg.chime_enabled !== false) {
          if (pendingChimeTouch) {
            playStartupChime((parentalCfg.chime_volume ?? 15) / 100);
          } else {
            const chimeOnFirstTouch = () => playStartupChime((parentalCfg.chime_volume ?? 15) / 100);
            document.addEventListener('touchstart', chimeOnFirstTouch, { once: true });
          }
        }
        ```
      - Fichier : `web/lecteur/index.html` (section `loadParentalConfig` + init)

- [ ] TICKET-072 — bug/UX — Mini-lecteur : affiche la radio au lieu du podcast en cours
      - Symptôme : la barre du bas affiche "EN DIRECT / Mon Petit France Inter" même quand un épisode podcast tourne
      - Cause probable : l'état du mini-lecteur n'est pas mis à jour lors du passage radio → podcast
      - Fix : dans `refreshStatus()`, détecter le contexte (radio vs podcast) et mettre à jour le mini-lecteur en conséquence
- [ ] TICKET-068 — content — Typo ID podcast `bestiolesossiles` (manque le 'f')
      - ID actuel dans `podcasts.json` : `bestiolesossiles`
      - Label : "Les Bestioles fossiles"
      - Dossier sur disque créé avec cet ID → ne pas renommer sans migration manuelle des fichiers audio
      - À corriger lors d'une prochaine maintenance (renommer dossier + mettre à jour podcasts.json)
- [ ] TICKET-061 — content — Saison 2 Professeur Caillou introuvable
      - RSS actuel (`podcast_9cfc0cf4`) : 10 épisodes, saison 2 absente
      - Épisodes saison 2 (mai 2025) : L'or, lithium, silicium, néodyme, cuivre, indium
      - RSS alternatif `rss_25664.xml` inexistant
      - Piste : chercher manuellement les URLs directes via kidcasts.fr ou radiofrance.fr
- [ ] TICKET-059 — backend — Durée des épisodes absente (affiche "--:--")
      - Cause : le flux Aerion ne publie pas `itunes:duration` pour Les Odyssées
      - Fix : après téléchargement, lire la durée réelle avec `ffprobe` et l'écrire dans `meta.json`
      - writer.py injecte le champ `duree` dans `data.json`
- [ ] TICKET-057 — UX/infra — Démarrage rapide de l'IHM enfant
      - Chromium met plusieurs secondes à démarrer après le boot
      - Piste 1 : optimiser les flags Chromium dans le service kiosque
      - Piste 2 : splash screen système affiché pendant le boot
      - Piste 3 : `--app=` mode au lieu du mode kiosque classique
      - Objectif : IHM visible en moins de 10 secondes après l'allumage

---

# 🟡 Priorité moyenne

- [ ] TICKET-004 — content — Gestion multi-podcasts (FR/ES)
      - `data.json` ne contient que du contenu FR (lesodyssees)
      - Ajouter au moins un podcast ES pour valider le filtre langue
- [ ] TICKET-007 — web — Interface configuration `podcasts.json`
- [ ] TICKET-029 — backend — Quotas stockage (`max_episodes`)
- [ ] TICKET-036 — web — Mode "grands boutons" optimisé tactile
- ~~TICKET-NAV~~ — UX — Navigation par flèches directionnelles dans la grille
      - **Non retenu** (2026-06-23) : navigation par menu tactile validée par le persona enfant
      - Le tap sur une jaquette suffit — aucune flèche directionnelle nécessaire
- [ ] TICKET-045 — UX — Taille des jaquettes ≥ 300×300 px (spec UX A5-1.2)
- [ ] TICKET-048 — backend — Script de vérification d'intégrité audio/images/data.json
      - Détecter : fichiers manquants, orphelins, M4A déguisés en .mp3, taille 0
      - Sortie lisible : [OK] / [WARN] / [ERR] par podcast et par type de problème
      - Script standalone : `scripts/rss_ingest/check_integrity.py`
- [ ] TICKET-071 — feature/parental — Contrôle parental : grille horaire + verrou langue
      - Grille 7 jours × 7 créneaux (0-7h et 22-24h toujours verrouillés)
      - Interrupteur global on/off
      - Verrou par langue : drapeau grisé → impossible de naviguer vers les podcasts de cette langue
      - Comportement fin de plage : finir l'épisode en cours, puis stop + retour home
      - Config uniquement depuis l'admin web (jamais depuis l'écran tactile)
      - Stockage : `data/parental.json` (écriture atomique)
- [ ] TICKET-070 — feature/analytics — Dashboard enrichi (style audimat podcast)
      - Funnel de complétion : abandon rapide / début / moitié / presque / terminé
      - Heatmap semaine × heure (intensité = minutes écoutées)
      - Top 5 épisodes rejoués
      - Streak : jours consécutifs avec écoute (card + icône 🔥)
- [ ] TICKET-058 — feature/UX — Série podcast "Décisions Prises" + easter egg
      - Série 7 épisodes générés par IA, FR + ES, dialogue deux voix
      - Easter egg : série cachée, déclencheur = 3 taps sur "Hechicero"
      - Hints progressifs : hint 1 vague, hint 2 explicite après ~1h
      - Voir `docs/55-PODCAST_SERIE_DECISIONS.md`

---

# 🟢 Priorité basse

- [ ] TICKET-008 — infra — Endpoint `/health`
- [ ] TICKET-010 — infra — Rotation logs
- [ ] TICKET-011 — sec — Durcir unités systemd
- [ ] TICKET-012 — test — Tests unitaires ingestion RSS
- [ ] TICKET-014 — docs — Procédure de mise à jour
- [ ] TICKET-017 — monitoring — Exporter Prometheus
- [ ] TICKET-020 — web — Page admin avancée
- [ ] TICKET-030 — feature — Égaliseur audio paramétrable
- [ ] TICKET-037 — UX — Animations simples (fade/slide) dans l'IHM enfant
- [ ] TICKET-046 — UX — Favoris (cœur) accessibles rapidement (spec persona enfant)
- [ ] TICKET-047 — UX — Défilement automatique (carrousel) arrêtable par l'enfant
- [ ] TICKET-056 — R&D — Exploration client lourd natif (PyQt5 ou Kivy)
      - Condition : lenteurs constatées OU besoin GPIO profond OU envie d'apprendre
      - Décision actuelle : on garde le web, on revient sur ce ticket en projet 2.0

---

# 🧩 Notes
- Le backlog suit les principes du manifeste
- Chaque ticket doit pointer vers un fichier de documentation
- Les tickets hardware sont isolés pour éviter les régressions
- Les tickets UX (041–047) sont issus de l'audit `UX Design/NaviguerDansLeContenus.md`
- **Repo public : aucun prénom personnel dans les fichiers versionnés** (voir `15-INVARIANTS.md` §6.4)
- Prénoms réels autorisés uniquement dans `private/` (exclu du repo, voir `private/podcast-easteregg/CLAUDE.md`)
