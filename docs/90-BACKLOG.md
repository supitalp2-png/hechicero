# Backlog Hechicero

> Convention : `TICKET-### — [type] — Titre — (prio) — owner`
> Dernière mise à jour : 2026-06-22

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
- [x] TICKET-052 — UX — Barre de statut : heure 15px/600, batterie 14px, hauteur 32px (2026-06-22)
- [x] TICKET-053 — UX — Grille 2 colonnes épisodes + webradios, scroll tactile (2026-06-22)
- [x] TICKET-054 — backend — Jaquettes par épisode dans data.json (2026-06-22)
      - ✅ writer.py : champ `image` ajouté par épisode
      - ✅ index.html : ep-thumb utilise `ch.image` avec fallback jaquette podcast
- [x] TICKET-060 — UX — Webradio en premier dans la grille (2026-06-22)
      - ✅ `grid.insertBefore(w, grid.firstChild)` dans `renderPodcasts()`
- [x] TICKET-051 — web — Affichage batterie dans la barre de statut (2026-06-22)
      - ✅ `navigator.getBattery()` bloqué dans Chromium → fallback `fetch('../status.json')` toutes les 30 s
      - ✅ Champ lu : `d.percent` (validé sur le Pi : `{"percent": 91, ...}`)
      - ✅ Détection charge via `d.state`
      - ✅ Validé après reboot : batterie visible dans la barre de statut

---

# 🔥 Priorité haute (en cours)

- [ ] TICKET-022 — web — Lecteur embarqué (IHM enfant)
- [ ] TICKET-027 — infra — Service systemd + timer pour ingestion RSS
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
- [ ] TICKET-049 — web — Images podcasts non affichées
      - Cause 1 : jaquette podcast (`images/lesodyssees.jpg`) jamais téléchargée
      - Cause 2 : images par épisode non incluses dans `data.json`
      - Fix : télécharger la jaquette podcast dans `web/lecteur/images/` + ajouter champ `image` par épisode dans writer.py
- [ ] TICKET-050 — UX — Refonte visuelle de l'IHM enfant
      - Architecture 5 écrans validée et implémentée
      - Reste : images, finitions, polish
- [ ] TICKET-052 — UX — Barre de statut : agrandir heure et indicateur batterie ← EN COURS
      - Taille actuelle trop petite pour être lue confortablement
      - Heure : font-size 15px, font-weight 600
      - Batterie : font-size 14px
      - Hauteur barre : 32px si nécessaire
- [ ] TICKET-053 — UX — Grille épisodes et webradios en 2 colonnes ← EN COURS
      - Passer à `display: grid; grid-template-columns: 1fr 1fr; gap: 12px`
      - Hauteur min 80px par carte, surface entière cliquable
- [x] TICKET-060 — UX — Webradio en premier dans la grille de contenu (2026-06-22)
      - ✅ `grid.insertBefore(w, grid.firstChild)` dans `renderPodcasts()`
- [ ] TICKET-061 — content — Saison 2 Professeur Caillou introuvable
      - RSS actuel (`podcast_9cfc0cf4`) : 10 épisodes, saison 2 absente
      - Épisodes saison 2 (mai 2025) : L'or, lithium, silicium, néodyme, cuivre, indium
      - RSS alternatif `rss_25664.xml` inexistant
      - Piste : chercher manuellement les URLs directes via kidcasts.fr ou radiofrance.fr
- [ ] TICKET-059 — backend — Durée des épisodes absente (affiche "--:--")
      - Cause : le flux Aerion ne publie pas `itunes:duration` pour Les Odyssées
      - Fix : après téléchargement, lire la durée réelle avec `ffprobe` et l'écrire dans `meta.json`
      - writer.py injecte le champ `duree` dans `data.json`
- [x] TICKET-054 — backend — Jaquettes par épisode dans data.json (2026-06-22)
      - ✅ writer.py : champ `image` ajouté par épisode (`ch.image || currentPodcast.image`)
      - ✅ index.html : `ep-thumb` utilise `ch.image` avec fallback jaquette podcast
      - Relancer `python3 main.py` pour régénérer data.json avec les images
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
- [ ] TICKET-005 — web — Dashboard Admin (config flux) ← PRIORITÉ REMONTÉE
      - Interface d'administration locale : ajout/suppression podcasts, état système, logs
      - Objectif : permettre à un parent de gérer les contenus sans toucher au terminal
      - Stack : Apache + PHP (déjà en place)
- [ ] TICKET-007 — web — Interface configuration `podcasts.json`
- [ ] TICKET-029 — backend — Quotas stockage (`max_episodes`)
- [ ] TICKET-036 — web — Mode "grands boutons" optimisé tactile
- [ ] TICKET-041 — UX — Appui sur image = pause/lecture (spec UX A5-1.3)
- [ ] TICKET-042 — UX — Barre de progression dans l'écran player (spec UX A5-1.3)
- [ ] TICKET-043 — UX — Reprise automatique de la position de lecture (spec UX A5-4.2)
      - Sauvegarder position dans `localStorage` par épisode
- [ ] TICKET-044 — UX — Flèches épisode suivant / précédent (spec UX A5-1.3)
- [ ] TICKET-045 — UX — Taille des jaquettes ≥ 300×300 px (spec UX A5-1.2)
- [ ] TICKET-048 — backend — Script de vérification d'intégrité audio/images/data.json
      - Détecter : fichiers manquants, orphelins, M4A déguisés en .mp3, taille 0
      - Sortie lisible : [OK] / [WARN] / [ERR] par podcast et par type de problème
      - Script standalone : `scripts/rss_ingest/check_integrity.py`
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
- [ ] TICKET-023 — audio — Startup sound (son rigolo au lancement — spec persona enfant)
- [ ] TICKET-030 — feature — Égaliseur audio paramétrable
- [ ] TICKET-037 — UX — Animations simples (fade/slide) dans l'IHM enfant
- [ ] TICKET-046 — UX — Favoris (cœur) accessibles rapidement (spec persona enfant)
- [ ] TICKET-047 — UX — Défilement automatique (carrousel) arrêtable par l'enfant
- [ ] TICKET-055 — feature — Statistiques d'écoute + dashboard parent
      - Tracer épisodes, durée, langue, heure d'écoute
      - Métriques : heures par langue, épisodes les plus écoutés, progression par podcast
      - Stockage léger local (SQLite ou JSON append)
      - Dashboard parent avec graphiques
- [ ] TICKET-056 — R&D — Exploration client lourd natif (PyQt5 ou Kivy)
      - Condition : lenteurs constatées OU besoin GPIO profond OU envie d'apprendre
      - Décision actuelle : on garde le web, on revient sur ce ticket en projet 2.0

---

# 🧩 Notes
- Le backlog suit les principes du manifeste
- Chaque ticket doit pointer vers un fichier de documentation
- Les tickets hardware sont isolés pour éviter les régressions
- Les tickets UX (041–047) sont issus de l'audit `UX Design/NaviguerDansLeContenus.md`
- **Repo public : aucun prénom personnel dans les fichiers versionnés** (voir `15-INVARIANTS.md` §6.0)
