# Backlog Hechicero

> Convention : `TICKET-### — [type] — Titre — (prio) — owner`
> Dernière mise à jour : 2026-06-30 (session 12 — batterie + bugs)

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

- [ ] TICKET-031 — hardware/feature — Sortie casque avec bascule automatique haut-parleurs
      - Contrainte : HiFiBerry Amp4 conservé (pas de sortie casque native)
      - Solution retenue (2026-06-30) :
          • DAC USB : UGREEN USB→Jack TRRS, fixé en permanence (zéro driver) → commandé
          • Jack : XMSJSIY TRS 3.5mm panel mount ∅22mm chromé → commandé
          • Détection casque : circuit LM393 (comparateur impédance) → voir §12 de 80-hardware.md
          • GPIO Pi 5 lit la sortie LM393 → bascule MPD entre HiFiBerry (HP) et DAC USB (casque)
          • MPD : 2 audio_output — HiFiBerry (ALSA hw:0) + DAC USB (ALSA hw:1)
      - ⚠️ Schéma LM393 définitif à produire une fois composants reçus

- [ ] TICKET-058 — feature/UX — Série podcast "Décisions Prises" + easter egg
      - Easter egg : série cachée, déclencheur = 3 taps sur "Hechicero" à l'écran d'accueil
      - Une fois découverte, la série apparaît dans le catalogue comme un podcast normal
      - Hints progressifs : hint 1 vague (après X jours), hint 2 explicite (après ~1h si pas trouvé)
      - Hints jamais pendant la lecture, one-shot, disparus après découverte
      - 7 épisodes planifiés — scripts en cours dans `docs/55-PODCAST_SERIE_DECISIONS.md`
      - Production : voix papa + voix IA (Descript/ElevenLabs)

---

# 🔧 Hardware — En attente réception

- [ ] TICKET-091 — hardware — Choisir méthode interface GPIO boutons-poussoirs
      - Options : (1) GPIO direct Pi 5, (2) MCP23017 I²C (préféré, évite conflit HiFiBerry), (3) Pico USB HID
      - Décider avant câblage des 5 boutons Gebildet
      - Impacte : config MPD, scripts Python GPIO

- [ ] TICKET-092 — hardware — Trouver prise USB-A panel mount clavier de secours
      - Cible : femelle USB-A, corps métal chromé, montage ∅16-19mm
      - Usage : accès clavier physique de maintenance sans ouvrir le boîtier

- [ ] TICKET-093 — hardware — Trouver LED témoin alimentation ∅6mm
      - Cible : LED métal panel mount 5-6mm chromée pré-câblée, rouge ou blanche
      - Câblage : résistance série 220Ω (5V) ou 100Ω (3.3V) depuis rail Pi

- [ ] TICKET-094 — hardware — Trancher format switch général batterie (fente 25×8mm)
      - Option A : agrandir fente à ~25×13mm → rocker switch 10A standard
      - Option B : utiliser trou ∅16mm existant → toggle switch fileté M16 haute puissance chromé
      - Contrainte : ≥5A continu / ~10A pic démarrage

- [ ] TICKET-095 — hardware — Vérifier courant max USB-C à réception
      - Composant : XMSJSIY panel mount USB-C
      - Cible minimale : ≥3A (Pi 5 + HiFiBerry Amp4)
      - Si insuffisant : chercher alternative

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

- [ ] TICKET-087 — feature/parental — Limiteur d'exposition sonore
      - `play_events.volume_pct` (moyenne MPD par session) est enregistré depuis session 9
      - Dashboard : afficher volume moyen par jour / par podcast
      - Config : seuil max volume dans `config.json` + avertissement si dépassé (IHM enfant)

- [x] TICKET-088 — bug/backend — `play_tracker.py` n'écrivait pas `listened_s` à la fermeture
      - MPD retourne `elapsed=0` quand l'état passe à "stop" → `listened_s` était systématiquement 0
      - Fix session 11 : `db_close_session` utilise `ts_end - ts_start` comme fallback si `listened_s == 0`
      - Fix session 12 : fallback capé à `duration_s` (évite `listened_s >> duration_s` si session laissée ouverte)
      - Fix DB session 12 : 10 lignes corrompues nettoyées (`listened_s` capé à `duration_s`)
      - ✅ `scripts/play_tracker.py` corrigé

- [ ] TICKET-048 — backend — Script de vérification d'intégrité audio/images/data.json
      - Détecter : fichiers manquants, orphelins, M4A déguisés en .mp3, taille 0
      - Sortie lisible : [OK] / [WARN] / [ERR] par podcast et par type de problème
      - Script standalone : `scripts/rss_ingest/check_integrity.py`


- [ ] TICKET-057 — UX/infra — Démarrage rapide de l'IHM enfant
      - Chromium met plusieurs secondes à démarrer après le boot
      - Piste : optimiser les flags Chromium, splash screen système

- [x] TICKET-089 — bug/backend — `battery_watchdog.py` : errno 121 code mort
      - Fix session 12 : réinitialisation INA219 déplacée à l'intérieur de `read_level()`
      - ✅ `scripts/battery_watchdog.py` corrigé

- [x] TICKET-090 — infra — Nettoyage fichiers morts dans le repo
      - ✅ Session 12 : fichiers morts supprimés via `git rm`

---

# 🟢 Priorité basse / À décider

- [ ] TICKET-030 — feature — Égaliseur audio paramétrable
- [ ] TICKET-037 — UX — Animations simples (fade/slide) dans l'IHM enfant
- [ ] TICKET-046 — UX — Favoris (cœur) accessibles rapidement
- [ ] TICKET-047 — UX — Défilement automatique (carrousel) arrêtable par l'enfant
- [ ] TICKET-056 — R&D — Exploration client lourd natif (PyQt5/Kivy) — décision projet 2.0
- [x] TICKET-008 — infra — Endpoint `/health` (monitoring externe)
      - ✅ Session 12 : `web/health.php` — JSON avec MPD, batterie, disque, ingest, uptime
      - HTTP 200 si tout OK, 503 si dégradé — batterie stale si > 5 min sans mise à jour
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
      - ✅ `play_tracker.py` (serveur, MPD idle) est désormais seule source de vérité
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

---

# 🧩 Notes
- Repo public : aucun prénom personnel dans les fichiers versionnés (voir `15-INVARIANTS.md` §6.4)
- Prénoms réels autorisés uniquement dans `private/` (exclu du repo)
- Les tickets hardware (031, 038) sont isolés pour éviter les régressions logiciel
