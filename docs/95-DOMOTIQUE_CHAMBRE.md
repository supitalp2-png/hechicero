# Écran « Chambre » — Contrôle domotique (Legrand/Netatmo via passerelle VM)

> Brique optionnelle : pilotage de la lumière et du volet de la chambre depuis l'IHM enfant.
> Statut au 2026-07-24 : **Phases 1 et 2 terminées et validées en réel** (sur les équipements
> du bureau, en attendant la bascule sur la chambre). Reste Phase 3 (écran dans Hechicero) et
> Phase 4 (bascule IDs chambre + validation). Historique de cadrage : `90-BACKLOG.md` TICKET-112.

---

## 1. Objectif

Ajouter un écran dans l'IHM enfant pour piloter **la lumière** (variateur 0-100%) et **le volet**
(position 0-100%) de la chambre, **sans modifier** l'installation domotique existante
(Legrand / Netatmo, gamme « with Netatmo », gateway Home + Control).

---

## 2. Contrainte de sécurité (non négociable)

Le repo est public et l'IHM tourne dans un navigateur accessible à un enfant. Donc :

- **Aucun secret** (client_id, client_secret, tokens OAuth) ni **identifiant de module**
  (les noms/ID contiennent ou révèlent le prénom de l'enfant et la cartographie du domicile)
  ne doit se retrouver dans le dépôt ni dans le navigateur kiosque.
- Tous les secrets et les vrais ID de modules vivent **uniquement** sur la VM passerelle,
  dans un fichier hors dépôt (`config.env`, `token.json`, `chmod 600`).
- L'IHM enfant ne connaît que **2 actions génériques** (`/lampe`, `/volet`) exposées par la
  passerelle. Elle ne voit jamais de token ni d'ID Netatmo.

---

## 3. Architecture

```
IHM enfant Hechicero (Pi, 192.168.1.86, Chromium kiosque, JS, ZÉRO secret)
  -> fetch HTTP -> Passerelle (VM, 192.168.1.3:8000, FastAPI)
       whitelist stricte de 2 modules (lampe, volet) — IDs en config hors dépôt
       tokens OAuth Netatmo détenus ici uniquement, refresh automatique
     -> API Netatmo Connect (cloud Legrand)
       -> lampe + volet de la chambre
```

### VM passerelle
- Debian 13 (Trixie) ARM64 sur la Freebox Ultra. Hostname `Passerelle-Hechicero`,
  IP `192.168.1.3` (bail statique DHCP), user `thomas`, SSH par clé.
- Dossier de travail : `~/passerelle-hechicero/spike/` (venv Python, hors dépôt Hechicero).

### Dérogation à l'invariant « zéro cloud »
Cette brique dépend d'une **API cloud** (Netatmo) et donc d'Internet — c'est la **seule
exception** documentée à l'invariant `15-INVARIANTS.md` §1.1 (au même titre que les webradios).
Le reste du lecteur (podcasts, MPD, navigation) reste 100% hors-ligne. Une coupure Internet ne
doit dégrader **que** l'écran Chambre, jamais le reste.

---

## 4. Ce qu'expose réellement l'API Netatmo (relevé au spike, 2026-07-24)

- **Lumière** : module type `NLFN`. Expose `on` (bool) **et** `brightness` (0-100).
  -> variation 0-100% confirmée. Commande : `setstate` avec `{"on": bool, "brightness": 0-100}`.
- **Volet** : module type `NLLV`, `appliance_type: orientable_sun_shade`. Expose
  `current_position` et `target_position` (0-100, pas de 1%).
  -> position pilotable. Commande : `setstate` avec `{"target_position": 0-100}`.
  - L'orientation des lames n'est PAS pilotable en temps réel via `setstate` (6 noms de
    propriété testés, tous refusés). Sur ce BSO, l'orientation est **couplée mécaniquement à la
    position** : à 0% le volet est totalement fermé (occultation = nuit). **L'IHM n'a donc qu'un
    seul axe : la position 0-100%.**
- Librairie : utiliser `homepluscontrol` en version **GitHub** (la version PyPI est l'ancienne
  API Legrand `eliotbylegrand.com`, dépréciée). La passerelle ne s'en sert que pour l'auth.
- Quota API Netatmo limité (~500 appels/jour) : la passerelle met l'état en cache quelques
  secondes, l'IHM ne fait pas de polling continu.

---

## 5. Service passerelle (FastAPI)

Fichier : `~/passerelle-hechicero/spike/app.py` (sur la VM). Gère lui-même l'auth (refresh token)
et appelle l'API brute `homestatus`/`setstate` sur les 2 seuls modules whitelistés.

### Endpoints
| Méthode | Route | Corps / réponse |
|---|---|---|
| GET | `/health` | `{"ok": true}` |
| GET | `/lampe` | `{"on": bool, "brightness": 0-100}` |
| POST | `/lampe` | corps `{"on": bool, "brightness"?: 0-100}` |
| GET | `/volet` | `{"position": 0-100}` |
| POST | `/volet` | corps `{"position": 0-100}` |

### Gestion du token
- `token.json` (hors dépôt, chmod 600) : `access_token` + `refresh_token`.
- Refresh auto sur erreur 401/403 (+ proactif avant expiration), persistance du nouveau token.
- Token initial via « Generate Token » de dev.netatmo.com (scopes
  `read_magellan write_magellan read_bubendorff write_bubendorff`).

### Service systemd (sur la VM)
Fichier `/etc/systemd/system/hechicero-passerelle.service`, `Restart=always`, activé au boot,
**testé : survit au reboot VM** (2026-07-24). ExecStart :
`/home/thomas/passerelle-hechicero/spike/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000`.

### config.env (hors dépôt, sur la VM)
Clés : `NETATMO_CLIENT_ID`, `NETATMO_CLIENT_SECRET`, `NETATMO_REDIRECT_URI`, `HOME_ID`,
`BRIDGE_ID`, `LAMPE_ID`, `VOLET_ID` (cible = bureau pour les tests, à basculer sur la chambre
en Phase 4). Valeurs réelles jamais versionnées.

---

## 6. IHM enfant (écran Chambre) — spécification validée

Style cohérent avec le lecteur (dark, accent cyan `#00c8ff`, gros éléments tactiles).

- **Lumière** : curseur vertical d'intensité 0-100% (0 en bas) + appui sur l'ampoule = on/off
  (rallume à la dernière intensité mémorisée). Instantanée.
- **Volet** : curseur vertical de position (ouvert en haut, fermé/nuit en bas) + appui sur la
  fenêtre = ouvre/ferme. La position réelle (lue via `/volet`) rejoint la consigne, avec repère
  et badge « en mouvement » (le volet met plusieurs secondes à bouger).
- **Accès** : bouton physique **GPIO23** (bouton isolé « antenne », en réserve) — sélecteur de
  fonction extensible (bascule entre l'écran en cours et l'écran Chambre).
- **Toujours disponible**, indépendant des horaires du contrôle parental.
- **Robustesse** : si la passerelle/Netatmo ne répond pas, afficher « hors ligne » sans geler le
  reste du lecteur.

Prototype fonctionnel : `web/chambre.html` (page autonome) pilote déjà la lampe et le volet du
bureau via la passerelle — base de l'intégration Phase 3 dans `web/lecteur/index.html`.

---

## 7. Avancement

- ✅ **Phase 1 — Spike OAuth** : app déclarée, tokens, modules listés, lampe et volet pilotés.
  Auth + refresh + lecture + écriture validés en réel.
- ✅ **Phase 2 — Service passerelle** : FastAPI, 2 endpoints, whitelist, refresh auto, cache,
  systemd, résilience reboot VM — validés sur les modules du bureau.
- ⏳ **Phase 3 — Écran dans Hechicero** : intégrer dans `web/lecteur/index.html`, brancher GPIO23
  (`scripts/buttons_daemon.py`, réutiliser le mécanisme `request_screen`/`get_ui_request` de
  l'écran favoris), gérer l'état hors-ligne.
- ⏳ **Phase 4 — Bascule chambre + validation** : passer `LAMPE_ID`/`VOLET_ID` sur la chambre
  (config.env VM), restreindre le CORS à l'origine du Pi, tester un reboot Freebox, valider en réel.

---

## 8. Problèmes connus / à corriger

- ⚠️ **Retour d'état de position du BSO non fonctionnel dans `web/chambre.html`** (constaté
  2026-07-24) : l'affichage de la **position réelle** du volet ne se met pas à jour correctement
  (le curseur/dessin ne reflète pas la position lue via `GET /volet` pendant/après le mouvement).
  À investiguer en Phase 3 — pistes : le `current_position` renvoyé par Netatmo met du temps à
  refléter le mouvement réel (et le cache passerelle de quelques secondes s'ajoute) ; ou bug dans
  la boucle de polling/animation côté page. La **commande** du volet fonctionne, c'est uniquement
  le **retour d'information** de position qui est à fiabiliser.

---

## 9. Non-régression (rappels)

- La boucle GPIO (`buttons_daemon.py`) ne doit pas être perturbée en ajoutant le handler GPIO23.
- L'écran Chambre reste hors du système d'horaires (`data/parental.json`).
- Le lecteur doit continuer à fonctionner sans Internet pour tout sauf l'écran Chambre.
- Aucun secret ni ID de module ni prénom dans le dépôt ni le navigateur (cf. §2 et
  `15-INVARIANTS.md` §6.4).
