# Backlog Hechicero

> Convention : `TICKET-### — [type] — Titre — (prio) — owner`
> Dernière mise à jour : 2026-08-04 — **TICKET-114 (rafraîchissement auto du catalogue) et TICKET-115 (réveil fiable de l'écran) livrés et clos** ; TICKET-116 (gain casque) appliqué, pas encore testé en voiture. Passe de remise au propre du dépôt le même jour (TICKET-118) : fuite de prénom neutralisée, fichiers morts supprimés, `.gitignore` durci, `80-ALIMENTATION.md` fusionné dans `05-POWER_MANAGEMENT.md`, collision TICKET-090 résolue (l'ancien « nettoyage fichiers morts » devient TICKET-117).
> Mise à jour 2026-07-24 — TICKET-113 (bureau d'icônes admin + page domotique + harmonisation nav) livré ET validé/clos ; TICKET-112 domotique validé en prod (lampe+volet chambre) ; **raffinement gestion lumière (ampoule grise éteinte / jaune+halo allumée, curseur = intensité qui allume, tap ampoule = on/off) appliqué des DEUX côtés (web/admin/domotique.php ET web/lecteur/index.html), pas encore testé en réel**. Souci connu : retour de position du BSO (§8 doc).

---

# 🔥 Priorité haute

- [~] TICKET-116 — audio — Gain casque trop faible en écoute nomade (voiture) (2026-08-03)
      - Demande de Thomas : niveau au casque insuffisant en voiture.
      - 🔍 Chaîne vérifiée de bout en bout, **aucune atténuation cachée** : mixer `Headphone` du DAC KT USB Audio à 100 % / 0.00 dB, EQ plat à 50, mapping IHM correct (`headphones_max = 100`), `mpc volume` atteint bien 100.
      - **Conclusion : le DAC KT USB Audio est le facteur limitant**, pas un bridage logiciel.
      - 🛠️ Appliqué : `volume_normalization "yes"` dans `/etc/mpd.conf` ; bandes EQ casque 1 kHz / 2 kHz / 4 kHz passées de 50 à 70 (~+5 dB) via `amixer -D eqcasque` — cf. TICKET-030 pour la mécanique des profils EQ.
      - ⏳ Reste : test réel en voiture. Si toujours insuffisant, le levier suivant est matériel (DAC ou ampli casque), pas logiciel.

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

# 🟢 Priorité basse / À décider

- [~] TICKET-112 — feature/sécurité — Écran « Chambre » : contrôle domotique (Legrand/Netatmo via passerelle VM) depuis l'IHM enfant (2026-07-19, MAJ 2026-07-24)
      - ✅ **2026-07-24 — Phases 1 et 2 TERMINÉES et validées en réel (sur les équipements du bureau, avant bascule chambre).** Architecture Home Assistant ABANDONNÉE au profit d'une **VM passerelle FastAPI + API Netatmo Connect directe** (VM Debian déjà en place, 192.168.1.3).
          - Spike OAuth : app Netatmo déclarée, token + refresh OK, modules identifiés, lampe (on/off + `brightness` 0-100) et volet (`target_position` 0-100) pilotés en réel.
          - Découverte clé : l'orientation des lames du BSO n'est PAS pilotable via `setstate` (couplée mécaniquement à la position) → l'IHM n'a qu'un seul axe de position 0-100 (0 = occultation totale = nuit).
          - Service passerelle : FastAPI (`app.py` sur la VM), endpoints `/lampe` et `/volet`, whitelist 2 modules, refresh token auto, cache (quota Netatmo ~500/j), service systemd `hechicero-passerelle` — survit au reboot VM.
          - Écran : `web/chambre.html` (page autonome, aucun secret) sert sur le Pi (`http://192.168.1.86/chambre.html`) et pilote lampe + volet du bureau via la passerelle — base de l'intégration Phase 3.
          - Sécurité : aucun secret ni ID de module ni prénom hors de la VM ; l'IHM ne connaît que 2 actions génériques.
          - 🐛 **Souci connu** : le retour d'état de **position réelle du BSO** ne s'affiche pas correctement dans `web/chambre.html` (la commande marche, c'est le feedback de position qui est à fiabiliser). Détail : `docs/95-DOMOTIQUE_CHAMBRE.md` §8.
          - **Détails complets : `docs/95-DOMOTIQUE_CHAMBRE.md`.**
      - 🛠️ **2026-07-24 — Phase 3 (intégration IHM) CODÉE, pas encore testée en réel.** Transposition de `web/chambre.html` dans l'IHM enfant `web/lecteur/index.html` comme vrai écran du lecteur :
          - Nouvel écran `#chambre` (markup + CSS scopé `.ch-*` / `#chambre`, accent cyan dédié `--ch-cyan`, IDs préfixés `ch-*` pour zéro collision avec l'existant — vérifié, notamment le `ch-title` des chapitres est distinct). Enregistré dans `ALL_SCREENS`.
          - Logique lampe + volet transposée fidèlement du prototype (halo animé, lissage de position, badge `moving`, timeout 6s → « hors ligne »). **Fetch passerelle uniquement à l'ouverture de l'écran** (`startChambre`/`stopChambre`) : rien n'est appelé au boot ni écran fermé (kiosque démarre passerelle éteinte OK, quota Netatmo préservé). Appels navigateur→passerelle en direct (`CH_GW='http://192.168.1.3:8000'`, aucun secret côté navigateur).
          - **Mini-lecteur** : apparaît automatiquement en bas de l'écran Chambre pendant une lecture (comportement natif des écrans non-lecteur, demande de Thomas) — la lecture n'est jamais coupée par l'ouverture de l'écran.
          - **Bouton GPIO23** (`buttons_daemon.py`) : passe de `handle_unassigned` à `handle_chambre` (dans `HANDLERS`, toggle simple). Émet `request_screen=chambre` (mécanisme `request_screen`/`get_ui_request` réutilisé des favoris, `radio.php` déjà générique — aucune modif PHP). Côté JS, `pollUiRequest` gère `chambre` en toggle (ouvre / revient à l'écran précédent).
          - **Réveil écran** (demande Thomas) : (a) veille « navigateur » `#sleep-overlay` levée côté JS quand la demande arrive ; (b) dalle physiquement éteinte (DPMS) réveillée par `buttons_daemon.py` via `screen_dpms.sh on` — lancé en **thread détaché** (jamais bloquer la boucle GPIO) et via `runuser` root→thomas avec env Wayland (pas `sudo`, cassé par NoNewPrivileges du durcissement TICKET-011). En sortie de veille, la Chambre s'ouvre (pas de toggle-close).
          - ⚠️ **À valider en réel (point le plus incertain)** : le réveil DPMS depuis le daemon root vers la session Wayland de `thomas` (`runuser` + env). Tester d'abord la commande à la main avant de se fier au bouton.
      - ⏳ Reste : test réel Phase 3 (voir plan de test), correction du feedback position BSO (§8 doc), Phase 4 (bascule `LAMPE_ID`/`VOLET_ID` sur la chambre côté VM, restreindre CORS, test reboot Freebox).
      - 🗄️ Cadrage historique ci-dessous (hypothèse Home Assistant) conservé pour mémoire — architecture retenue = `docs/95-DOMOTIQUE_CHAMBRE.md` :
      - ⏸️ **EN PAUSE (état au 2026-07-19, désormais dépassé — repris et livré le 2026-07-24, voir ci-dessus)** (décision Thomas, le jour même de l'ouverture) : le cadrage a révélé que le prérequis n'est pas une petite config mais **l'installation et la prise en main complètes d'un Home Assistant** (VM Freebox), soit un chantier à part entière avant même de commencer à coder côté Hechicero. Thomas préfère ne pas engager ce temps maintenant. Le cadrage ci-dessous reste entièrement valable pour la reprise — rien n'est à refaire.
      - Demande de Thomas : nouvel écran permettant de piloter la lumière et le volet de la chambre de son fils depuis Hechicero.
      - ⚠️ **Prémisse corrigée en cours de cadrage (2026-07-19)** : le ticket a d'abord été écrit en supposant une instance **Home Assistant existante** — c'est faux. Thomas a **Google Home**, et les appareils réels sont du **Legrand / Netatmo** (gamme "with Netatmo", app Home + Control). Ne pas repartir de l'hypothèse HA-déjà-en-place dans les prochaines sessions.
      - Recherche faite : **Google Home est une impasse** — les "Home APIs" ouvertes par Google sont des SDK **mobiles uniquement** (Android/iOS, certification obligatoire), inutilisables depuis un serveur PHP/Python sur le Pi. On contourne donc Google Home entièrement et on parle directement à Legrand.
      - **API Legrand/Netatmo (dev.netatmo.com, "Home + Control")** : existe et est documentée, volets roulants supportés (`NLV` = interrupteur volet, `NLLV` = interrupteur volet avec niveau 0-100%). MAIS **cloud uniquement, aucune API locale** → 3 conséquences : (1) nécessite Internet, pas juste le Wi-Fi ; (2) OAuth2 avec **renouvellement de jeton toutes les 3h**, re-validation manuelle si un renouvellement échoue (point fragile connu) ; (3) limites de débit d'appels → l'affichage de l'état réel doit rester à une cadence raisonnable, surtout pas le polling 1s des favoris.
      - 💡 **Piste à explorer en priorité à la reprise (Thomas, 2026-07-19)** : il possède **déjà une machine Home Assistant quelque part**, pas encore mise en service. Si elle est remise en route, elle remplace avantageusement la VM Freebox (pas de limite 2 Go/2 vCPU, pas de dépendance au comportement de la box au reboot). **Première question à poser à la reprise : quel matériel, où, dans quel état ?** — avant de repartir sur le scénario VM Freebox ci-dessous, qui reste le plan B.
      - **Architecture retenue (2026-07-19, sous réserve de la piste ci-dessus)** : **Home Assistant en VM sur la Freebox Ultra**, comme couche de traduction entre Hechicero et Legrand. Écarté : (a) API Legrand en direct depuis le Pi — obligerait à réimplémenter tout le cycle OAuth2/refresh 3h et sa gestion d'échec ; (b) HA sur le Pi Hechicero — **refusé délibérément**, le Pi est déjà en throttling thermique (TICKET-109, ventilateur TICKET-111 pas encore monté), ce serait exactement la régression que Thomas interdit.
        - Freebox Ultra : VM supportées, **2 vCPU et 2 Go de RAM non extensibles** (contrairement à la Delta, extensible jusqu'à 14 Go) — suffisant pour HA + intégration Netatmo seule, mais plafonne pour un usage HA plus large plus tard.
        - Avantages : Freebox allumée en permanence et câblée (pas de dépendance au Wi-Fi entre HA et le réseau), HA gère nativement le renouvellement des jetons Legrand, zéro charge ajoutée sur le Pi.
        - ⚠️ Point de vigilance tiré de TICKET-109 (épisode 4) : la Freebox réapplique parfois ses paramètres après un redémarrage — **vérifier que la VM redémarre bien automatiquement après un reboot box**.
      - Décisions UX prises avec Thomas (2026-07-19) :
        - Volet : boutons Ouvrir/Stop/Fermer **et** curseur de position (0-100%) — nécessite un module `NLLV` (avec niveau) ; à confirmer sur son installation réelle.
        - État réel affiché pour la lumière et le volet (interrogé, pas supposé) — cohérent avec le reste de l'app (volume, sortie audio, lecture en cours).
        - Vérification d'accessibilité : tester que **Home Assistant répond vraiment**, pas juste que le Wi-Fi est connecté.
        - Config (URL, jeton, entités) : **fichier texte édité en SSH**, jamais de formulaire dans l'admin web (le jeton ne doit pas transiter par une page web non authentifiée, même en réseau local).
        - Écran **toujours disponible**, indépendant des horaires du contrôle parental (l'enfant doit pouvoir éteindre sa lumière le soir même après l'heure limite d'écoute).
        - Fermeture de l'écran : retour à **l'écran précédent** (le bouton peut être pressé depuis n'importe où, contrairement à l'écran favoris).
      - Déclencheur : bouton physique GPIO23 (bouton isolé antenne, jusque-là en réserve) — appui = ouvre l'écran, ré-appui = le ferme (toggle simple, pas tap-ou-maintien comme GPIO16/17/27).
      - ⚠️ **Règle absolue de Thomas** : aucune régression sur l'existant, et **sécurité stricte** — aucun mot de passe/jeton/nom d'entité (les noms d'entités contiennent le prénom de l'enfant) ne doit jamais se retrouver dans un fichier poussé sur GitHub (cf. [[feedback_no_child_name_public]], étendu ici aux identifiants HA/Legrand). Le navigateur kiosque ne doit jamais voir le jeton ni les vrais entity_id : tout passe par un proxy PHP côté serveur qui lit une config hors dépôt.
      - Thomas a déjà un compte développeur Netatmo (dev.netatmo.com).
      - 🔍 **Cadrage 2026-07-19 : architecture et UX décidées, rien codé.**
      - ⏳ Reste à faire à la reprise : (0) **d'abord** faire le point sur la machine Home Assistant que Thomas possède déjà (matériel, emplacement, état) — si exploitable, elle remplace l'étape 1 ; (1) sinon installer HAOS en VM sur la Freebox Ultra, (2) connecter l'intégration Netatmo/Legrand, (3) relever les vrais `entity_id` de la lumière et du volet, (4) créer un jeton d'accès longue durée HA, (5) seulement ensuite coder l'écran + le proxy PHP côté Hechicero.

- [ ] TICKET-111 — hardware — Ventilateur GPIO/PWM pour dissipation thermique (2026-07-18) (renuméroté depuis TICKET-110, en collision avec le ticket roaming — 2026-07-18)
      - Demande de Thomas : boîtier chaud, ventilateur silencieux souhaité. Corroboré par TICKET-109 (`vcgencmd get_throttled = 0xe0000` le 2026-07-18 : capping fréquence + throttling + limite thermique constatés depuis le dernier boot)
      - Ventilateur déjà acheté par Thomas — **en attente qu'il soit mis en place physiquement** avant de configurer/tester quoi que ce soit côté logiciel
      - Plan retenu : essayer d'abord le connecteur PWM dédié du Pi 5 (séparé du header 40 broches GPIO, ne consomme donc aucun des GPIO déjà utilisés — boutons, I2C batterie, I2S audio). Si inaccessible une fois les HAT (ampli + batterie) empilés → repli sur un montage GPIO libre avec un transistor/MOSFET (un GPIO seul ne peut pas alimenter un moteur directement) — ⚠️ GPIO16 n'est plus disponible depuis TICKET-046 (favori), seul GPIO6 reste vraiment libre
      - Activation prévue : `dtoverlay=pwm-fan` dans `/boot/firmware/config.txt` (section `[all]`) — pas encore ajouté, contrôle automatique de la vitesse selon la température, seuils ajustables ensuite (`fan_temp0`, `fan_temp0_hyst`, etc.) si besoin de le rendre plus/moins agressif
      - ⏳ Reste à faire : Thomas monte le ventilateur dans le boîtier, puis on active l'overlay et on vérifie (`vcgencmd measure_temp`, `cat /sys/class/thermal/cooling_device*/type`)

---

# ✔️ Terminé

- [x] TICKET-118 — infra/sécurité — Remise au propre du dépôt et de la documentation (2026-08-04)
      - 🔴 **Fuite corrigée** : `docs/55-PODCAST_SERIE_DECISIONS.md` contenait le prénom réel de l'enfant dans une consigne d'orthographe, alors que le fichier déclare lui-même deux fois « aucun prénom réel (repo public) ». La consigne est rapatriée dans `private/podcast-easteregg/00-contexte.md`, seul endroit autorisé.
      - ✅ **Historique git réécrit** le 2026-08-04 (`git filter-repo --replace-text`) : `git log --all -S` ne trouve plus le prénom. Sauvegarde de l'historique d'origine dans `~/hechicero-github-avant-filtrage.git` (clone mirror de GitHub, 113 Mo). ⚠️ GitHub peut conserver un temps les objets devenus inaccessibles — purge complète = demande de GC ou recréation du dépôt.
      - 🧹 Fichiers morts supprimés et `.gitignore` durci — détail dans TICKET-117.
      - 📚 **Doc** : `80-ALIMENTATION.md` (spec du 2026-06-26) fusionnée dans `05-POWER_MANAGEMENT.md`, qui devient la référence unique batterie — les deux décrivaient le même sujet et divergeaient, et le numéro 80 était en collision avec `80-hardware.md`. Ajout au passage du piège `level_end` (bug des cycles batterie du 2026-07-06) et de la réserve TICKET-011 sur le chemin `shutdown`.
      - 📚 `30-LECTEUR.md` : sections « Non implémenté » et « Évolutions prévues » purgées — elles annonçaient encore comme à venir les favoris, les boutons GPIO, le chime et le script d'intégrité (tous livrés), plus le carrousel et les animations (annulés).
      - 📚 `README.md` : index de la doc corrigé (ajout de `85-SAUVEGARDE_RESTAURATION.md` et `95-DOMOTIQUE_CHAMBRE.md`, qui manquaient). `web/index.php` : commentaire renvoyant à un fichier inexistant (`95-RESTAURATION_URGENCE.md`) corrigé.
      - ✅ Vérifié : `web/podcasts` est un **lien symbolique** vers `~/hechicero/podcasts` — pas de duplication des 28 Go de médias.
      - ✅ Vérifié : les 45 renvois croisés entre docs pointent tous vers des fichiers existants. **Ne pas renuméroter les docs en masse** — c'est ce qui casserait ces renvois.
      - 💥 **Incident au cours de cette passe, à ne jamais reproduire** : `git filter-repo` a été lancé dans le même bloc de commandes que le ménage, **avant le commit**. Son `reset --hard` final a effacé tout le travail non committé — TICKET-114, TICKET-115 et toute la doc du jour. Tout a été réécrit dans la foulée. Règles retenues : (1) une opération destructive d'historique se lance **seule**, jamais enchaînée ; (2) **commit et push d'abord**, sans exception ; (3) une sauvegarde de dépôt se fait par `git clone --mirror` (113 Mo), jamais par `cp -a` d'un dossier qui contient 28 Go de médias.

- [x] TICKET-117 — infra — Nettoyage fichiers morts dans le dépôt (renuméroté depuis TICKET-090 le 2026-08-04, en collision avec le ticket batterie « 51 micro-cycles factices »)
      - ✅ Session 12 : `app.js`, `style.css`, `lecture.html` supprimés via `git rm`
      - ✅ **Deuxième passe le 2026-08-04** : suppression des patchs à usage unique (`patch_ticket114.py`, `patch_ticket115b.py`), des sauvegardes `*.pre-ticket*` et `*.bak`/`*.old`, du bring-up `button_toggle_test.py` + `.service` (remplacé par `buttons_daemon`), de l'artefact lgpio `.lgd-nfy0` et des scripts de migration déjà passés (`fix_durations.py`, `fix_battery_cycles.py`, `seed_tracking.py`, `analyze_bewitched.py`).
      - ✅ `.gitignore` durci pour que ça ne revienne pas : `*.bak`, `*.old`, `*.orig`, `*.rej`, `*.pre-ticket*`, `*~`, `.lgd-nfy0`. Correction au passage de `podcasts/` → `podcasts/*` (la négation `!podcasts/.gitkeep` était inerte : git ne ré-inclut jamais un fichier sous un dossier exclu), avec ajout explicite de `web/podcasts` — un motif contenant un `/` est ancré à la racine et ne couvre plus le lien symbolique par héritage.

- [x] TICKET-115 — bug/UX — Écran noir intermittent : réveil fiable de la dalle (2026-08-02, réécrit et **corrigé le 2026-08-04**)
      - ✅ **Confirmé corrigé par Thomas le 2026-08-04.**
      - Symptôme : par intermittence l'écran restait noir après une extinction de veille, seul un reboot ramenait l'image. VNC continuait de fonctionner (sortie virtuelle) — c'est ce qui a masqué le problème si longtemps.
      - 🔍 **Diagnostic pris en direct pendant la panne** (pas une hypothèse de plus) : `wlr-randr` affichait HDMI-A-1 « Enabled: yes », le bon mode courant, EDID du JRP7003 lu correctement ; `dmesg | grep -i hdmi` : aucun événement depuis le boot. Le Pi se croyait en train d'afficher.
      - **Cause racine** : `wlr-randr --on --preferred` ne déclenche **aucun modeset** quand le connecteur est déjà actif ET déjà au mode préféré. Reposer le même mode est un no-op → la dalle, elle bel et bien éteinte, n'est jamais réveillée.
      - Séquence qui ramène l'image : `--mode 1280x720@60` ; `sleep 3` ; `--mode 1024x600@59.821`.
      - 🐛 **Régression de la 1ère version du correctif** : rebond de mode systématique dans l'action `on`. Or `buttons_daemon.py` appelle `screen_dpms.sh on` à **chaque** appui du bouton antenne GPIO23 (écran Chambre) → l'écran déjà allumé s'éteignait et clignotait à chaque pression.
      - 🛠️ **Réécriture 2026-08-04** de `scripts/screen_dpms.sh` (124 lignes, 5820 octets, md5 `933e04d7a2b435b333d7de67b5f1a247`) :
        - `off` → `wlr-randr --output HDMI-A-1 --off`
        - `on` → lit l'état ; si « Enabled: yes » **ne fait rien** (chemin swayidle resume + bouton GPIO23, zéro clignotement) ; sinon rebond `1280x720@60` → 3 s → `1024x600@59.821`
        - `rescue` → force le rebond quel que soit l'état. Nécessaire parce que le cas « Enabled: yes mais dalle noire » **n'est pas détectable depuis le Pi** (tous les indicateurs sont au vert) : c'est l'humain qui constate et tranche, en SSH.
        - `status` → `wlr-randr`
        - Journalisation de chaque bascule dans `data/screen_dpms.log`.
      - ✅ Les 4 actions testées et conformes au log. Observation utile : pendant un rebond manuel, un **second appel concurrent** à `on` (swayidle resume) a été correctement absorbé en no-op au lieu d'empiler un deuxième rebond.
      - 📌 **Leçon de livraison** : le fichier avait été détruit la veille par un **heredoc collé en SSH tronqué en cours de route**. Méthode retenue : écriture directe via le partage Samba, puis vérification `ls -l` / `md5sum` côté Pi **avant** exécution. Jamais de heredoc, jamais de script de patch transféré.
      - Commande de secours si l'écran affiche « Not Support » : `export WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/run/user/1000` puis `wlr-randr --output HDMI-A-1 --mode 1024x600@59.821`.

- [x] TICKET-114 — bug/UX — Rafraîchissement automatique du catalogue dans le lecteur (2026-08-03, réécrit le 2026-08-04)
      - Problème : après un ingest ou un ajout via l'admin, il fallait recharger Chromium à la main pour voir les nouveaux podcasts.
      - **Cause exacte** : `loadData()` était bien rappelé toutes les 5 min, mais **sans jamais re-rendre l'écran affiché**. `goToPodcasts()` était le seul endroit qui enchaînait chargement puis rendu → tant que l'enfant ne quittait pas la grille pour y revenir, rien ne changeait, même après des heures.
      - 🛠️ `web/lecteur/radio.php` : action `data_version` renvoyant `{mtime, size}` de `data.json`. Deux `stat()`, assez léger pour un polling à 10 s, au lieu de retransférer les ~700 Ko du catalogue. mtime **et** size : mtime seul rate une réécriture dans la même seconde, size seule rate un remplacement de même taille.
      - 🛠️ `web/lecteur/index.html` : `pollCatalogVersion()` toutes les 10 s compare la signature ; au changement, `refreshCatalogInPlace()` recharge `data.json` et re-rend l'écran visible. Le tick 5 min appelle désormais `refreshCatalogInPlace()` au lieu de `loadData()` — c'est ce qui bouche le trou d'origine.
      - ⚠️ **Précaution 1 à ne pas casser en refactorant** : la position de lecture est ré-ancrée sur le **chemin audio** (`findEpisodeByAudio()`), pas sur `currentIdx` — l'ingest insère les nouveaux épisodes en tête de liste, donc l'index désignerait un autre épisode et `next`/`prev` partiraient sur le mauvais. Même famille de piège que TICKET-108.
      - ⚠️ **Précaution 2** : les écrans `player` et `radio-player` ne sont **jamais** re-rendus — la lecture en cours ne doit pas clignoter parce qu'un ingest s'est terminé en arrière-plan.
      - ⏳ **Validation** : `php -l` sans erreur et endpoint vérifié en curl. Le test visuel de bout en bout (nouveaux podcasts apparaissant seuls sur la grille pendant un ingest complet) n'a pas encore été confirmé formellement.

- [x] TICKET-113 — UX/admin — Refonte navigation admin en « bureau » d'icônes façon iPhone (2026-07-24)
      - ✅ **Validé et clos par Thomas le 2026-07-24** (bureau + panneaux, page domotique admin, nav unifiée ‹ Bureau/Lecteur, header « style board » pour les panneaux, État système sur l'accueil, icônes agrandies, icône webradio réparée, sous-titres nettoyés).
      - Demande de Thomas : la page d'admin (`web/index.php`) devient un bureau d'icônes façon vieil iPhone — grosses icônes carrées arrondies avec label, **pensé mobile** (l'admin se consulte depuis un téléphone). But : rendre la navigation plus cohérente **sans trop toucher aux boards déjà en place**.
      - Icônes prévues : ⚙️ Veille + son de démarrage · 🕐 Heures autorisées d'écoute · 🎧 Gérer podcasts + webradios · 📊 Dashboard écoute (`dashboard.php`) · 🔋 Batterie (`battery_dashboard.php`) · ❤️ Favoris (`favoris.php`) · 🎚️ Égaliseur (`audio_eq.php`) · 📻 Ouvrir le lecteur (`/lecteur/`) · 🏠 Domotique · 💾 Sauvegardes (`backup_dashboard.php`, **Expert only**).
      - On garde le toggle **Normal/Expert** (Expert révèle l'icône Sauvegardes), mécanisme `.expert-only`/`body.expert` déjà en place.
      - **Décisions de cadrage (2026-07-24)** :
        - Les 3 fonctions aujourd'hui en sections DANS `index.php` (veille/son = section « Administration avancée » ; horaires = section « Contrôle parental » ; podcasts = sections Ajouter/Podcasts/Webradios/Sync) → **vue dédiée par icône** : taper l'icône masque le bureau et affiche un panneau plein écran avec juste cette fonction + bouton « retour au bureau ». Le contenu interne des sections NE CHANGE PAS (mêmes markup/JS), on ne fait que les envelopper dans des conteneurs montrés/masqués → risque de régression minimal. NB : le contrôle des **langues** (dans la section parental) n'a pas d'icône dédiée → à loger dans le panneau Horaires (parental).
        - **Domotique** : nouvelle page admin dédiée (`web/admin/domotique.php` à créer) qui **reprend le look de l'écran Chambre du lecteur** (ampoule + suns, volet à lamelles, curseurs à gros pouce), parle à la passerelle `192.168.1.3:8000` (aucun secret, comme `chambre.html`). Pensée pour accueillir **plus tard** des règles d'administration (ex. volet ouvrable seulement 8h–19h, veilleuse nuit auto-extinction 10 min) — fonctions futures, pas dans ce ticket.
        - Boards déjà autonomes (dashboard, batterie, EQ, favoris, sauvegardes) : **on n'y touche pas**, le bureau fait juste un lien ; au plus un petit « retour au bureau ».
      - ✅ Maquette validée par Thomas (2026-07-24).
      - 🛠️ **Partie A faite (index.php)** : bureau `#springboard` (10 icônes carrées colorées, 3 col mobile / 5 desktop) ajouté après le header ; état de vue dans `body[data-view]` (attribut, PAS `body.className` que `setMode()` réécrit) ; `showView()` bascule accueil ↔ panneaux ; barre `#panel-back` (retour). Les 7 sections existantes reçoivent `data-panel` (veille / horaires / podcasts) sans toucher leur contenu interne ; CSS masque les sections hors panneau (override du `!important` de `.expert-only`), l'expert-only continue de gérer le contenu expert AU SEIN d'un panneau. Section « Administration avancée » renommée « Veille & son de démarrage » et **dé-expert-only** (accessible en normal via son icône, demande Thomas). `.ha-nav` (barre de liens du header) masquée sur l'admin, remplacée par le bureau. Icône Sauvegardes = `expert-only`. Aucune modif du JS existant (loadStatus/loadConfig/etc. inchangés).
      - 🛠️ **Partie B faite** : `web/admin/domotique.php` (nouveau) — reprend le look de l'écran Chambre (ampoule + suns, volet à lamelles, curseurs à gros pouce, toggle volet = consigne, animation de position, statut passerelle). Standalone, parle à `192.168.1.3:8000`, aucun secret. Header admin (`ha-page`/`ha-nav`) avec lien « ‹ Bureau » vers `/`. Placeholder commenté pour les règles futures (volet 8h-19h, veilleuse nuit 10 min).
      - 🛠️ **Harmonisation nav + retours (2026-07-24)** :
        - Nav unifiée sur TOUS les boards (battery_dashboard, dashboard, favoris, audio_eq, backup_dashboard, domotique) : la longue barre (Admin/Écoute/Batterie/Favoris/Audio/Lecteur) est remplacée par **‹ Bureau + 📻 Lecteur** en haut à droite (modèle du board Domotique). La navigation passe par le bureau d'icônes. Lecteur enfant non touché.
        - Palette déjà partagée : `index.php` charge `hechicero-admin.css` et n'écrase pas les couleurs de base → bureau + boards ont la même palette navy/or que Batterie (rien à faire).
        - Cartes du board Favoris alignées sur `.ha-panel` (fond `--surface`, rayon 16, ombre).
        - Sous-titres « TICKET-… » (Favoris, Égaliseur, Domotique) remplacés par du texte propre.
        - 🐛 **Bug corrigé** : icônes des webradios cassées dans le board Favoris — le champ `image` est relatif au lecteur, préfixé désormais par `/lecteur/` (fallback `image_url`).
      - ✅ Testé et validé par Thomas le 2026-07-24 (nav harmonisée, headers de panneaux « style board », État système sur l'accueil, icônes agrandies).

- [x] TICKET-046 — UX — Favoris (cœur) accessibles rapidement
      - ✅ **Validé en conditions réelles et clos par Thomas le 2026-07-19.**
      - 🔍 Cadrage fait avant dev. Existant côté matériel : GPIO23 (bouton isolé, emplacement antenne) déjà câblé et réservé pour ce bouton depuis TICKET-101 (2026-07-08), branché en `handle_unassigned` dans `buttons_daemon.py` en attendant ce ticket — voir [[project_hechicero_buttons_gpio]].
      - Existant côté UX design : persona enfant (`UX Design/personnae.md`) demande explicitement "Favoris accessibles rapidement (cœur)" et évoque l'idée "double-tap = cœur" comme interaction magique. Parcours parent (`UX Design/NaviguerDansLeContenus.md`) prévoit aussi une gestion des favoris côté admin.
      - Aucune structure de données favoris n'existait avant (`data.json` n'a pas de champ favori, et il est régénéré par l'ingestion RSS — donc pas un bon endroit pour stocker un choix persistant de l'enfant).
      - Référence externe (Merlin, l'enceinte que le fils de Thomas utilise) : bouton ♥ physique avec 3 usages — 1) pendant la navigation, ouvre directement la liste des titres favoris ; 2) pendant l'écoute, ajoute/retire le titre en cours (cœur bleu affiché sur la jaquette) ; 3) appui long = batterie + date/heure (fonction annexe).
      - ✅ **Cahier des charges figé (2026-07-19)** :
        - Portée : favori par **épisode**, pas par podcast entier (confirmé avec l'enfant).
        - Déclencheur : bouton physique dédié = **GPIO16** (confirmé sur le boîtier réel via `buttons_daemon.py` en mode identification — dernier bouton de la ligne des 7, jusque-là en réserve). GPIO23 (bouton isolé antenne) réservé pour un usage futur différent, pas le favori (devenu TICKET-112) — cf. [[project_hechicero_buttons_gpio]].
        - Tap court = ajoute/retire le favori sur l'épisode en cours d'écoute.
        - Appui long = ouvre un écran dédié listant les favoris (façon Merlin).
        - Retour visuel à l'ajout : un cœur apparaît et se fixe sur la jaquette/icône de l'épisode. Pas de son.
        - Côté parent : favoris visibles et gérables (suppression) depuis l'admin web.
        - Point technique : les `id` d'épisode dans `data.json` sont des slugs du titre seul (`normalize_id()` dans `scripts/rss_ingest/parser.py`), pas garantis uniques entre podcasts différents — clé de stockage `favoris.json` = composite `podcast_id/episode_id`.
      - 🛠️ **Implémenté le 2026-07-19** :
        - `data/favoris.json` (hors dépôt) : dict clé `type:podcastId/episodeId` (episode) ou `type:radioId` (radio) → `{type, podcast_id/episode_id ou radio_id, added_at}`.
        - `web/lecteur/radio.php` : actions `toggle_favori`, `get_favoris`, `remove_favori`, `request_screen`/`get_ui_request` (polling pour l'ouverture d'écran via appui long).
        - `scripts/buttons_daemon.py` : GPIO16 dans `TAP_OR_HOLD` (tap = `handle_favori_toggle`, maintien = `handle_favori_screen`).
        - `web/lecteur/index.html` : écran `#favoris`, badge cœur (`.fav-heart`/`.is-fav`) animé (`favPop`), polling `pollUiRequest` (1s) et `fetchFavoris` (1s après ajustement).
        - `web/admin/favoris.php` (nouveau) : liste + suppression, lien nav "❤️ Favoris" sur 4 pages admin.
        - `.gitignore` : `data/favoris.json`, `data/ui_request.json`, `data/nav_context.json` ajoutés.
      - 🛠️ **Retours Thomas après tests réels, tous traités** : cœur agrandi + animation `favPop` ; délai d'apparition resserré à 1s ; webradios rendues favorisables (`favori_key()` préfixée par type, `find_current_radio()`) ; navigation suivant/précédent au sein des favoris (`favNavQueue`/`favNavIdx`, `playFavItem()`) étendue aux boutons physiques GPIO17/27 via un contexte partagé côté serveur (`data/nav_context.json`, action `set_nav_context`) — **`buttons_daemon.py` n'a pas eu besoin d'être modifié pour cette dernière extension**, toute l'intelligence est dans `radio.php`. `now_playing` détecte désormais aussi les webradios (avant : épisodes seulement).
      - ✅ **Validé de bout en bout par Thomas le 2026-07-19** (cœur, favoris webradio, retrait par second appui, navigation suivant/précédent écran + bouton physique).

- [x] Correction — bug — Reprise automatique de la lecture au démarrage à froid de MPD (2026-07-19)
      - Découvert par Thomas juste après le test réel de shutdown de `battery_watchdog` (TICKET-011) : au redémarrage du Pi, le podcast s'est remis à jouer tout seul, sans action sur l'IHM — comportement non prévu dans la séquence de démarrage à froid.
      - Cause : `/etc/mpd.conf` définit `state_file "/var/lib/mpd/state"` (config Debian par défaut, jamais retouchée par le projet) sans `restore_paused`. Par défaut MPD restaure aussi l'état play/pause sauvegardé, pas seulement la position — comme MPD avait été relancé plusieurs fois en état "playing" pendant les manips TICKET-030 de la veille et le test de shutdown du matin, l'état sauvegardé était "playing".
      - Fix : ajout de `restore_paused "yes"` juste après `state_file` dans `/etc/mpd.conf`, puis `sudo systemctl restart mpd`. Garde la reprise de position (utile) mais force l'état "en pause" au démarrage.
      - ✅ Validé en conditions réelles par Thomas le 2026-07-19 : `mpc status` après redémarrage MPD affiche `[paused]` sur la piste en cours, plus d'auto-play.
      - Documenté dans `docs/20-SETUP_SYSTEME.md` §6.1.

- [x] TICKET-109 — bug/hardware — Coupures Wi-Fi récurrentes + signal anormalement faible à 30cm de la Freebox (2026-07-18)
      - **Épisode 1 (2026-07-15/16, résolu)** : Freebox en "WPA 2/3 - Compatibilité" → association Wi-Fi en boucle (faux message "Secrets were required"). Fix : Freebox basculée en WPA2-AES pur. Aussi fait : power management Wi-Fi désactivé définitivement (`wifi-powersave-off.conf`, `wifi.powersave=2`), MAC remise permanente (`2c:cf:67:cc:4a:2d`, le random cassait le bail DHCP), firmware `brcm80211` blanchi après re-test.
      - **Épisode 2 (2026-07-16, résolu)** : récidive, cause différente — même SSID "El CORAL GOURMET" diffusé en 2.4GHz (BSSID `3A:07:16:3C:3D:80`, canal 11) ET 5GHz DFS (BSSID `...:88`, canal 128) ; sans BSSID épinglé, le Pi retentait le 5GHz DFS et échouait. Fix : BSSID épinglé sur le 2.4GHz (`nmcli connection modify "El CORAL GOURMET" 802-11-wireless.bssid 3A:07:16:3C:3D:80`).
      - **Épisode 3 (2026-07-18, résolu)** : nouvelle coupure à 12:29:46 (reconnexion auto en 10s, même BSSID — le fix BSSID tient, donc pas du roaming). Anomalie centrale : **signal -59 à -71 dBm et débits parfois plancher (rx jusqu'à 1-2 Mbit/s) à 30cm de la borne**, attendu ≈ -35/-40 dBm. Large balayage de causes mené (interférence canal 11, régulatoire/txpower, thermique, Bluetooth, blindage RF du boîtier) — la plupart écartées, cause finale rattachée à la distance/signal réel plutôt qu'à un défaut matériel (cf. TICKET-110 ci-dessous, découvert en creusant l'épisode 4).
      - **Épisode 4 (2026-07-18 soir) — panne totale après 4 jours d'absence, résolu** : après 2 semaines de fonctionnement normal, Thomas part 4 jours, revient, plus aucune connexion Wi-Fi. Un répéteur Wi-Fi officiel Free a été installé entre-temps (60cm de Hechicero). Diagnostic : Freebox repassée en **"WPA 2/3 - Compatibilité (recommandé)"** au lieu du WPA2-AES pur fixé le 16/07 — exact même bug que l'épisode 1. Cause à 100% côté Freebox (mise à jour Freebox Server 4.12.2 du 3/07 et/ou réapplication des paramètres du compte Free en ligne à chaque reboot, qui écrase les modifs locales FreeboxOS). **Fix** : rebasculé sur WPA2-AES pur. **Confirmé résolu** : logs NetworkManager montrent l'échec avant fix (`no secrets`) puis succès immédiat après (`scanning → associating → 4way_handshake → completed`). Rien côté Pi (apt/firmware propres).
      - **Point de vigilance pour l'avenir** : si la Freebox réapplique bien les paramètres du compte Free à chaque reboot, ce même bug peut revenir après un futur redémarrage box. À vérifier : si le réglage WPA2-AES peut être fixé côté espace abonné Free en ligne pour survivre à un reboot.
      - ✅ **Clos le 2026-07-18** (confirmé par Thomas) : test réel de 30 min (déplacement dans l'appart, radio allumée) — zéro `disconnect`/`deauth` dans les logs NetworkManager, le fix WPA2/3-Compatibilité de l'épisode 4 tient.
      - Détail complet du balayage (épisode 3) et lien avec TICKET-110 : voir mémoire `project_hechicero_wifi_dropouts` et [[reference_samba]] (l'instabilité affectait aussi l'accès Q:\).

- [x] TICKET-110 — feature/infra — Roaming automatique multi-AP (box + répéteur Free) (2026-07-18)
      - Contexte : Hechicero est mobile (bureau/salon). Répéteur Wi-Fi officiel Free installé le 18/07, même SSID "El CORAL GOURMET" diffusé par la box ET le répéteur, plusieurs BSSID chacun. Sans intervention le Pi restait figé sur le BSSID épinglé au démarrage (nécessaire depuis TICKET-109 épisode 2 pour éviter un BSSID 5GHz DFS de la box).
      - Découverte en creusant TICKET-109 épisode 4 : une fois reconnecté, le Pi restait épinglé sur la box (signal -66dBm) alors que le répéteur à 60cm affichait -31dBm après bascule manuelle du BSSID — toute la piste "signal marginal/thermique/boîtier" explorée dans TICKET-109 était probablement en réalité de la distance à la box, pas un problème matériel.
      - **Implémenté et installé** : `scripts/wifi_roam.py` + `scripts/wifi_roam.service` (voir `docs/70-SERVICES_SYSTEMD.md` §7sexies) — scan toutes les 60s, exclut les BSSID sur fréquence DFS (~5250-5725MHz), bascule vers le plus fort du reste si le gain est net (≥8dB) et confirmé sur 2 scans consécutifs (anti-flapping, `MARGIN_DB=8`/`CONFIRM_COUNT=2`). Log dans `data/wifi_roam.log`. Coexiste avec `wifi_watch.service` (TICKET-109, lecture seule) sans conflit.
      - ✅ **Clos le 2026-07-18** (décision Thomas) : code relu et validé — anti-flapping fonctionne comme prévu. Observé en conditions réelles : dip à -62dBm avec meilleur candidat à -46dBm détecté, mais confirmé une seule fois sur les 2 scans consécutifs requis → pas de bascule déclenchée (comportement anti-flap voulu, pas un bug). Pas encore observé de vraie bascule effective de bout en bout (dégradation soutenue 2+ min) ; Thomas fera un test physique (déplacer Hechicero bureau/salon) le 2026-07-19.

- [x] TICKET-079 — UX/saisonnier — Mode Noël (décembre uniquement) (2026-07-18, ajusté le même jour après retours Thomas)
      - Neige animée (`#noel-snow`, flocons générés en JS, animation CSS `noel-fall`) — overlay global fixed, visible sur tous les écrans (accueil, grilles, lecteur) **et sur l'écran de veille** (`z-index:10050`, au-dessus de `#sleep-overlay` à `9999`)
      - Chapeau de Noël (SVG inline, `noelHatMarkup()`) sur le coin des jaquettes podcast (`renderPodcasts()`) **et** des jaquettes d'épisodes (`renderChapters()`, variante `.noel-hat-sm`) — forme conique fléchie + pompon, incliné à -42°, plus marqué qu'à l'origine
      - Traîneau du Père Noël (2 rennes + traîneau + Père Noël, SVG inline, coloré) traversant l'écran toutes les 60-90s — rennes repositionnés **devant** le traîneau dans le sens du déplacement (bug initial : rennes derrière, donc poussaient le traîneau), `z-index:9000` (sous l'overlay de veille, volontairement absent pendant la veille)
      - Guirlande lumineuse (`#noel-garland`) : câble en chaînette réelle (`y = cosh(x)`, x ∈ [-1,1], converti en coordonnées SVG dans `catenaryY()`/`catenaryPoint()`, fonctions génériques réutilisées par le mode anniversaire ci-dessous), pas des scallops répétés comme au premier essai — câble visible (double trait sombre + liseré clair) avec 24 ampoules multicolores clignotant en asynchrone, positionnée en haut de tous les écrans **et de l'écran de veille** (`z-index:10040`)
      - Garde `new Date().getMonth() === 11` + override de test `?noel=1` / `?noel=0` dans l'URL (`isNoelActive()`)
      - Zéro dépendance réseau/CDN, tout inline dans `web/lecteur/index.html`
      - ⏳ Non testé en conditions réelles sur le Pi par Thomas (ajustements validés par retours sur captures d'écran uniquement)
      - Fichier modifié : `web/lecteur/index.html`

- [x] TICKET-079bis — UX/saisonnier — Mode Anniversaire (20 novembre uniquement) (2026-07-18)
      - Même architecture que TICKET-079 (mode Noël), réutilise les fonctions génériques `catenaryY()`/`catenaryPoint()`/`catenaryWireD()` pour la guirlande
      - Confettis colorés qui tombent en continu (`#anniv-confetti`, rotation aléatoire), overlay global visible sur tous les écrans et sur l'écran de veille (`z-index:10050`)
      - Chapeau de fête (cône + pois + pompon, `annivHatMarkup()`) sur les jaquettes podcast, les jaquettes d'épisodes (`.anniv-hat-sm`) et la grande jaquette de l'écran lecteur
      - Guirlande de fanions triangulaires sur la même courbe en chaînette que la guirlande de Noël (`#anniv-garland`), qui ondulent légèrement (`anniv-flag-sway`), visible aussi sur l'écran de veille (`z-index:10040`)
      - Banderole "Joyeux Anniversaire !" / "¡Feliz Cumpleaños!" (texte alterné FR/ES à chaque passage) qui traverse l'écran toutes les 60-90s, style ruban avec pointes + texte en dégradé or (`.gv-gold`, même style que le logo Hechicero) — cachée pendant la veille comme le traîneau de Noël
      - Garde `getMonth()===10 && getDate()===20` (20 novembre) + override de test `?anniv=1` / `?anniv=0` dans l'URL (`isAnnivActive()`)
      - Zéro dépendance réseau/CDN, tout inline dans `web/lecteur/index.html`
      - ⏳ Non testé en conditions réelles sur le Pi par Thomas
      - Fichier modifié : `web/lecteur/index.html`

- [x] TICKET-037 — ❌ Annulé (2026-07-18) — UX — Animations simples (fade/slide) dans l'IHM enfant
- [x] TICKET-047 — ❌ Annulé (2026-07-18) — UX — Défilement automatique (carrousel) arrêtable par l'enfant
- [x] TICKET-056 — ❌ Annulé (2026-07-18) — R&D — Exploration client lourd natif (PyQt5/Kivy) — décision projet 2.0

- [x] TICKET-017 — monitoring — Export Prometheus (métriques batterie/écoute) (2026-07-18)
      - Nouvel endpoint `web/metrics.php` (format d'exposition texte Prometheus, sur le modèle de `health.php` — pas d'authentification, réseau local uniquement)
      - Batterie (source `data/battery_stats.json`, déjà écrit par `battery_tracker.py`) : `hechicero_battery_level_percent`, `_charging`, `_voltage_volts`, `_current_milliamps`, `_power_watts`, `_screen_on`, `_estimated_autonomy_minutes[_live]`, `_cycles_recorded`, `_stats_age_seconds` (fraîcheur de la mesure)
      - Santé système (mêmes checks que `health.php`) : `hechicero_disk_used_percent`, `hechicero_disk_free_bytes`, `hechicero_mpd_up`, `hechicero_up`
      - Écoute (source `data/tracking.db`, déjà écrit par `play_tracker.py`) : compteurs cumulés `hechicero_listen_seconds_total{langue,type}` (podcast/radio × fr/es), `hechicero_episodes_completed_total`, `hechicero_play_sessions_total` ; gauge `hechicero_headphone_seconds_today` (remise à zéro quotidienne, cohérent avec le dashboard fatigue auditive existant)
      - Aucune nouvelle collecte : réutilise entièrement les données déjà produites par `battery_tracker.py`/`play_tracker.py` — le ticket portait sur l'export, pas sur de nouvelles métriques
      - Résilience : une erreur SQLite (base verrouillée/absente) n'empêche pas l'export des métriques batterie/santé (`try/catch` isolé, expose `hechicero_tracking_db_error` à la place)
      - ✅ **Validé en conditions réelles par Thomas le 2026-07-18** (`curl http://192.168.1.86/metrics.php`), 2 bugs trouvés au premier run et corrigés dans la foulée :
        - `hechicero_battery_stats_age_seconds` à -7185 (au lieu d'un petit positif) : `battery_tracker.py` écrit `last_updated` en heure locale naïve (`datetime.now()`, pas d'offset UTC) ; PHP l'interprétait par défaut en UTC → décalage ~2h (CEST). Fix : `date_default_timezone_set('Europe/Paris')` dans `metrics.php`. Confirmé après fix : `age_s=33`
        - `hechicero_headphone_seconds_today` à -30.452 (temps d'écoute casque négatif, impossible) : bug pré-existant dans `play_tracker.py`, 3 endroits calculaient `elapsed - open_elapsed_offset` sans le clamp à 0 déjà présent ailleurs dans le fichier (cas typique : repeat/single qui boucle sur le même fichier, l'`elapsed` MPD retombe à ~0 avant que l'event de bouclage soit traité par le tracker → `listened_s` négatif écrit tel quel en base). Ce bug corrompait déjà silencieusement le dashboard fatigue auditive existant (`dashboard.php`/`tracking.php`), pas seulement ce nouvel export. Fix : `max(0.0, ...)` aux 3 endroits (heartbeat, mixer-only, fermeture de session) + défense en profondeur `MAX(0, ...)` dans la requête SQL de `metrics.php`. Confirmé après fix : `16.913`
        - Correctif ponctuel donné à Thomas pour les lignes déjà corrompues en base : `sqlite3 data/tracking.db "UPDATE play_events SET listened_s = 0 WHERE listened_s < 0;"`
      - Fichiers modifiés : `web/metrics.php` (créé), `scripts/play_tracker.py` (fix clamp)

- [x] TICKET-030 — feature — Égaliseur audio paramétrable (2026-07-18)
      - Décisions prises avec Thomas avant codage (cf. [[project_hechicero_ticket030_eq]] en mémoire) : scope complet (page admin dédiée + 2 profils indépendants HP/casque), moteur **alsaequal** (plugin ALSA/LADSPA, `libasound2-plugin-equal` — solution native recommandée par HiFiBerry elle-même pour ce matériel, cf. guide officiel https://www.hifiberry.com/docs/software/guide-adding-equalization-using-alsaeq/), granularité **10 bandes natives** (31Hz→16kHz, pas de regroupement en 3 curseurs)
      - Config système : deux instances alsaequal indépendantes dans `/etc/asound.conf` (`ctl.eqhp`/`ctl.eqcasque`, chacune enroulant respectivement `hw:CARD=sndrpihifiberry` et `hw:CARD=Audio`), `mpd.conf` pointé sur ces devices virtuels au lieu du hardware direct — détail complet et **validé** dans `docs/20-SETUP_SYSTEME.md` §6.4
      - `scripts/audio_eq_apply.py` : lit `data/audio_eq.json` (gains en dB, -12..+12, par bande × par profil) et les applique via `amixer -D eqhp/eqcasque sset ...` — nécessaire car alsaequal ne persiste rien entre deux boots. `scripts/audio_eq_apply.service` réapplique au démarrage
      - `web/admin/audio_eq.php` (page Expert) : 2 onglets HP/casque, 10 curseurs verticaux par onglet, 4 préréglages pré-chargeables (Plat, Basses renforcées, Voix claire, Chaud et rond)
      - Loudness (compensation Fletcher-Munson à bas volume) **non implémenté** — hors du scope décidé avec Thomas, à traiter séparément si besoin
      - ✅ **Validé en conditions réelles le 2026-07-18 — Thomas confirme : "l'équaliseur change vraiment, le son est agréable !"**. Trois bugs réels trouvés et corrigés en direct sur le Pi (post-mortem complet dans `docs/20-SETUP_SYSTEME.md` §6.4 et §6.4.1, à relire avant de retoucher cette config) :
        1. **Noms de contrôle amixer** : pas `31Hz` comme deviné, mais `'00. 31 Hz'` (préfixe numérique + espace) — confirmé via `--list-controls`, corrigé dans `BAND_LABELS`. `cset name=...` (interface raw) ne fonctionne pas sur ces contrôles "simples" → `sset` obligatoire
        2. **"Indépendance" cassée par un détail alsaequal non documenté ailleurs** : par défaut alsaequal stocke son état dans `$HOME/.alsaequal.bin` (par utilisateur, pas par ctl nommé) — `eqhp`/`eqcasque` semblaient partager leur état car tous les tests tournaient sous `thomas`. Fix : paramètre `controls` avec un chemin distinct par instance (`data/alsaequal_hp.bin`/`data/alsaequal_casque.bin`) — réglé ce même problème ET l'erreur de permission `www-data` (qui a `$HOME=/var/www`, non inscriptible) d'un coup. `www-data` ajouté au groupe `audio`
        3. **Incident en cascade** : pré-créer les fichiers `controls` avec `touch` (fichier vide) fait planter alsaequal en `SIGBUS` — arrivé pendant que MPD tournait, ce qui a fait planter MPD 3× en rafale et grillé le disjoncteur anti-boucle de l'unité systemd **`mpd.socket`** (distincte de `mpd.service`, activation par socket). L'IHM tactile a été inutilisable ~20 min (`radio.php` parle à MPD via `/run/mpd/socket`, contrairement à `mpc` en CLI qui passe par TCP et semblait donc fonctionner) — récupéré via `systemctl reset-failed mpd.socket` + séquence stop/start précise, procédure documentée en §6.4.1 pour la prochaine fois
      - Fichiers créés : `web/admin/audio_eq.php`, `scripts/audio_eq_apply.py`, `scripts/audio_eq_apply.service` ; modifiés : `web/index.php`, `web/dashboard.php`, `web/admin/battery_dashboard.php` (nav), `.gitignore` (`data/audio_eq.json`), `docs/20-SETUP_SYSTEME.md`, `docs/70-SERVICES_SYSTEMD.md`

- [x] TICKET-011 — sec — Durcir unités systemd (`ProtectSystem`, `NoNewPrivileges`) (2026-07-19)
      - Déploiement volontairement progressif après la soirée TICKET-030 (services testés dans l'ordre : `wifi_watch`/`play_tracker` → `battery_tracker`/`audio_eq_apply` → `wifi_roam`/`button_toggle_test` → `buttons_daemon`/`battery_watchdog`), un lot validé en conditions réelles avant de passer au suivant
      - Ajouté aux 8 `.service` dans `scripts/` : `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=strict` + `ReadWritePaths=/home/thomas/hechicero/data`, `ProtectHome=read-only` — tous ces services ne lisent/écrivent que dans `data/`, rien ailleurs
      - ⚠️ **Volontairement PAS de `PrivateDevices=true`** sur `buttons_daemon`/`button_toggle_test` (GPIO) ni sur `audio_eq_apply` (`/dev/snd`, carte son) — cette option aurait cassé l'accès matériel, exactement le genre de piège vécu la veille au soir avec l'égaliseur (fichier `controls` vide → SIGBUS → cascade jusqu'à `mpd.socket`). `ProtectSystem`/`ProtectHome` n'affectent pas `/dev`, `/proc`, `/sys` — seul `PrivateDevices` le ferait
      - Validation en conditions réelles pour 7 des 8 services (logs qui continuent de s'écrire après redémarrage, bouton physique play/stop testé, égaliseur toujours accessible via `amixer`) — voir [[project_hechicero_ticket011_hardening]] en mémoire pour le détail service par service
      - ⏳ **`battery_watchdog` : chemin `sudo shutdown -h now` non testé** — son flag `--simulate-critical` s'arrête juste avant l'exec du shutdown (ne teste que l'écriture de `data/last_session.json`), impossible de valider sans provoquer un vrai arrêt. Le raisonnement (exec d'un binaire ne nécessite qu'un accès lecture+exécution, compatible avec `ProtectSystem=strict` en lecture seule) est solide mais pas prouvé empiriquement. Si besoin d'une vraie preuve un jour : baisser temporairement `critical_level_percent` dans `data/config.json` au-dessus du niveau de batterie courant, en présence de Thomas pour rallumer ensuite
      - Fichiers modifiés : les 8 `.service` dans `scripts/` (`battery_tracker`, `play_tracker`, `battery_watchdog`, `buttons_daemon`, `button_toggle_test`, `wifi_roam`, `wifi_watch`, `audio_eq_apply`)

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

- [x] TICKET-010 — infra — Rotation logs (2026-07-18)
      - Deux fichiers grossissaient sans limite : `/tmp/hechicero_ingest.log` (cron RSS nocturne) et `data/sleep_debug.log` (traceur TICKET-102, toujours actif — un ajout par événement écran de veille côté lecteur).
      - Les logs des services systemd (`battery_tracker`, `battery_watchdog`, `play_tracker`, `buttons_daemon`, `hechicero-idle`) ne sont pas concernés : ils passent par `journalctl`, qui a sa propre rétention (`journald.conf`).
      - **Fix** : `scripts/hechicero-logrotate.conf` (nouveau, versionné) — rotation quotidienne, `copytruncate` (pas de signal process nécessaire), 7 jours pour le log d'ingestion, 14 jours pour le traceur veille.
      - ✅ Clos le 2026-07-18
      - Fichiers modifiés : `scripts/hechicero-logrotate.conf` (nouveau), `docs/70-SERVICES_SYSTEMD.md` (§7quater)
      - À installer côté Pi : `sudo cp scripts/hechicero-logrotate.conf /etc/logrotate.d/hechicero`

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
- [x] TICKET-117 — voir la section Terminé plus haut (ex-TICKET-090 « nettoyage fichiers morts », renuméroté le 2026-08-04 pour lever la collision avec le ticket batterie ci-dessous)
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
      - ✅ **Mapping GPIO ↔ bouton confirmé le 2026-07-08** (test bouton par bouton, gauche à droite) : GPIO25 = source (HP/casque), GPIO13 = vol−, GPIO17 = précédent, GPIO12 = play/pause, GPIO27 = suivant, GPIO5 = vol+, GPIO16 = favori (TICKET-046, confirmé et codé le 2026-07-19 — pas GPIO23 comme envisagé un temps ici), GPIO23 = bouton isolé antenne, réserve pour un usage futur non défini, GPIO6 = non câblé
      - ⚠️ GPIO17 n'est pas le bouton source dans le câblage réel (contrairement au bring-up breadboard du 2026-07-06) — c'est GPIO25. Sans impact, le dispatch est purement logiciel (`HANDLERS` dans `buttons_daemon.py`)
      - ✅ Handlers assignés dans `HANDLERS` (`scripts/buttons_daemon.py`)
      - ✅ Service systemd créé : `scripts/buttons_daemon.service` (remplace `button_toggle_test.service`, voir `docs/70-SERVICES_SYSTEMD.md` §7ter pour l'installation)
      - ✅ Service installé et testé en conditions réelles par Thomas (2026-07-08) : 3 bugs trouvés et corrigés —
          • suivant/précédent ne faisaient rien : `radio.php` lisait `mpd_status()['file']`, or la commande MPD `status` n'a PAS de champ `file:` (seul `currentsong` l'a) → ajout de `mpd_currentsong()`, utilisé par `next_episode`/`prev_episode`/`now_playing`
          • latence perçue au play/pause : polling `syncPlaybackState()`/`syncAudioMode()` resserré de 300ms à 100ms dans `index.html`
          • maintien du bouton volume ne répétait pas : rebond mécanique pendant le maintien lu à tort comme un relâchement (bloqué ensuite par le garde-fou anti-rebond) → hystérésis dédiée (`RELEASE_CONFIRM_S`), relâchement confirmé seulement après 50ms de HIGH continu
      - ✅ **Nouveau (2026-07-08)** : suivant/précédent passent en tap-ou-maintien (`TAP_OR_HOLD` dans `buttons_daemon.py`) — tap bref = épisode suivant/précédent (inchangé), maintien > `HOLD_THRESHOLD_S` (0.4s) = recherche par à-coups de `SEEK_STEP_S` (5s) dans l'épisode en cours. Nouvelle action `seek_relative` dans `radio.php` (`seekcur ±N` MPD, recherche relative à la position actuelle). Recherche en secondes fixes (pas en % de la durée) — pratique standard des lecteurs de podcasts (Apple Podcasts, YouTube). Pas encore testé en conditions réelles par Thomas — valeurs `SEEK_STEP_S`/`HOLD_THRESHOLD_S` à ajuster si besoin
      - ⏳ Reste à faire : Thomas teste le tap/maintien suivant-précédent. GPIO16/favori : voir TICKET-046, codé le 2026-07-19.

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
