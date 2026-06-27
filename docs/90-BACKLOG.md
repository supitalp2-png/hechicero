# Backlog Hechicero

> Convention : `TICKET-### — [type] — Titre — (prio) — owner`
> Dernière mise à jour : 2026-06-27 (session 8/9)

---

# 🔥 Priorité haute

- [ ] TICKET-085 — infra — Ghost de la carte SD (image bootable sans audio)
      - Exigence : copier l'image sur une nouvelle carte → ça redémarre et ça fonctionne directement
      - Séquence :
          1. Supprimer `podcasts/*/audio/`, `podcasts/*/images/`, `web/lecteur/images/` sur le Pi
          2. `dd` de la carte SD → image bootable complète
          3. PiShrink pour compresser l'espace vide
          4. Stocker l'image sur disque externe
          5. Relancer l'ingestion RSS pour re-télécharger MP3 et jackets
      - À définir : fréquence (avant chaque sprint hardware minimum)

- [ ] TICKET-083 — infra/sécurité — Arrêt propre sur batterie critique
      - Surveiller le seuil critique via GPIO HAT UPS D (signal avant coupure) + polling niveau
      - Sauvegarder contexte : position MPD (podcast + timestamp), écran actif, langue
      - Arrêter proprement MPD, Apache, scripts monitoring, sync filesystem
      - `shutdown -h now` → redémarrage transparent pour l'enfant
      - Dépend de TICKET-080

- [ ] TICKET-038 — hardware — Bouton physique RUN pour démarrage du Raspberry Pi 5
      - Problème : le Pi 5 ne démarre pas automatiquement avec le Waveshare UPS HAT (D)
      - Objectif : ajouter un bouton externe relié aux broches RUN
      - Priorité : Haute (bloquant pour usage enfant)

- [ ] TICKET-031 — hardware/feature — Sortie casque avec bascule automatique haut-parleurs
      - Contrainte : HiFiBerry Amp4 conservé (pas de sortie casque native)
      - Solution validée :
          • Dongle USB audio (ex: UGREEN ~8€) → sortie casque
          • Jack 3.5mm commuté PJ-392 panel-mount
          • Résistor pull-up 10kΩ entre contact switch du jack et GPIO 3.3V
          • Script Python GPIO : détecte insertion → bascule MPD entre HiFiBerry et USB
          • MPD configuré avec 2 audio_output : HiFiBerry (ALSA hw:0) + USB (ALSA hw:1)

- [ ] TICKET-058 — feature/UX — Série podcast "Décisions Prises" + easter egg
      - Easter egg : série cachée, déclencheur = 3 taps sur "Hechicero" à l'écran d'accueil
      - Une fois découverte, la série apparaît dans le catalogue comme un podcast normal
      - Hints progressifs : hint 1 vague (après X jours), hint 2 explicite (après ~1h si pas trouvé)
      - Hints jamais pendant la lecture, one-shot, disparus après découverte
      - 7 épisodes planifiés — scripts en cours dans `docs/55-PODCAST_SERIE_DECISIONS.md`
      - Production : voix papa + voix IA (Descript/ElevenLabs)

---

# 🟡 Priorité moyenne

- [ ] TICKET-079 — UX/saisonnier — Mode Noël (décembre uniquement)
      - Neige animée sur la page d'accueil
      - Chapeau de Noël sur le coin des jaquettes podcast
      - Traîneau du Père Noël qui passe de temps en temps en fond d'écran
      - Actif uniquement du 1er au 31 décembre (`new Date().getMonth() === 11`)
      - Aucune dépendance réseau, aucun CDN

- [ ] TICKET-068 — content — Typo ID podcast `bestiolesossiles` (manque le 'f')
      - ID actuel dans `podcasts.json` : `bestiolesossiles`
      - Label : "Les Bestioles fossiles"
      - ⚠️ Dossier audio sur disque créé avec cet ID → ne pas renommer sans migration manuelle
      - À corriger lors d'une maintenance : renommer dossier + mettre à jour `podcasts.json`

- [ ] TICKET-086 — backend — Déduplication tracking JS vs play_tracker
      - `play_tracker.py` (serveur, MPD idle) est désormais la source de vérité
      - Le tracking JS dans `lecteur/index.html` (`startTracking`, `startRadioTracking`) crée des doublons pour les podcasts
      - À faire : supprimer les appels JS `startTracking` / `startRadioTracking` / `endTracking` une fois play_tracker validé en prod

- [ ] TICKET-087 — feature/parental — Limiteur d'exposition sonore
      - `play_events.volume_pct` (moyenne MPD par session) est enregistré depuis session 9
      - Dashboard : afficher volume moyen par jour / par podcast
      - Config : seuil max volume dans `config.json` + avertissement si dépassé (IHM enfant)

- [ ] TICKET-061 — content — Saison 2 Professeur Caillou introuvable
      - RSS actuel : 10 épisodes, saison 2 absente
      - Épisodes saison 2 (mai 2025) : L'or, lithium, silicium, néodyme, cuivre, indium
      - Piste : chercher manuellement les URLs directes via kidcasts.fr ou radiofrance.fr

- [ ] TICKET-048 — backend — Script de vérification d'intégrité audio/images/data.json
      - Détecter : fichiers manquants, orphelins, M4A déguisés en .mp3, taille 0
      - Sortie lisible : [OK] / [WARN] / [ERR] par podcast et par type de problème
      - Script standalone : `scripts/rss_ingest/check_integrity.py`


- [ ] TICKET-057 — UX/infra — Démarrage rapide de l'IHM enfant
      - Chromium met plusieurs secondes à démarrer après le boot
      - Piste : optimiser les flags Chromium, splash screen système

---

# 🟢 Priorité basse / À décider

- [ ] TICKET-030 — feature — Égaliseur audio paramétrable
- [ ] TICKET-037 — UX — Animations simples (fade/slide) dans l'IHM enfant
- [ ] TICKET-046 — UX — Favoris (cœur) accessibles rapidement
- [ ] TICKET-047 — UX — Défilement automatique (carrousel) arrêtable par l'enfant
- [ ] TICKET-056 — R&D — Exploration client lourd natif (PyQt5/Kivy) — décision projet 2.0
- [ ] TICKET-008 — infra — Endpoint `/health` (monitoring externe)
- [ ] TICKET-010 — infra — Rotation logs
- [ ] TICKET-011 — sec — Durcir unités systemd (`ProtectSystem`, `NoNewPrivileges`)
- [ ] TICKET-017 — monitoring — Export Prometheus (métriques batterie/écoute)

---

# ✔️ Terminé

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
- [x] TICKET-038 — (voir priorité haute)
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

---

# 🧩 Notes
- Repo public : aucun prénom personnel dans les fichiers versionnés (voir `15-INVARIANTS.md` §6.4)
- Prénoms réels autorisés uniquement dans `private/` (exclu du repo)
- Les tickets hardware (031, 038) sont isolés pour éviter les régressions logiciel
