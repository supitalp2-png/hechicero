# Mode Kiosque — Projet Hechicero

Chromium affiche le lecteur en plein écran au démarrage, sans barre d'adresse ni
interaction système visible.

> *Mis à jour le 2026-08-21.*
>
> ⚠️ **Ce document décrivait une configuration X11/LXDE qui n'a jamais correspondu au
> système actuel** : `~/.config/lxsession/`, `xset`, `xserver-command` dans `lightdm.conf`.
> Le Pi tourne sous **Wayland avec le compositeur labwc**. Rien de tout cela n'avait le
> moindre effet. Réécrit intégralement le 2026-08-21.

---

## 1. Pré-requis

- Raspberry Pi OS **avec bureau** (Wayland / labwc)
- `chromium` — ⚠️ le binaire s'appelle `chromium`, **pas** `chromium-browser`
- Lecteur servi par Apache sur `http://localhost/lecteur/`
- `wtype` (paquet apt) — indispensable, voir §5

---

## 2. Démarrage

Le script `~/kiosk.sh` est lancé à l'ouverture de session. Il fait trois choses, **dans cet
ordre**, et l'ordre compte :

```bash
# 1. Forcer la sortie haut-parleurs et un volume bas AVANT Chromium
for i in $(seq 1 15); do
  resp=$(curl -sf "http://localhost/lecteur/radio.php?action=set_output&mode=hp")
  echo "$resp" | grep -q '"ok":true' && break
  sleep 1
done
curl -sf "http://localhost/lecteur/radio.php?action=setvol&vol=13" >/dev/null

# 2. Chromium en arrière-plan
chromium --ozone-platform=wayland --noerrdialogs --disable-infobars \
         --kiosk http://localhost/lecteur &

# 3. Le chime, après le chargement de la page
sleep 6 && python3 /home/thomas/hechicero/scripts/play_chime.py
```

**Pourquoi la bascule audio est côté shell et pas en JavaScript** — pour ne dépendre
d'aucun état MPD restauré au boot. Sans elle, une session précédente terminée sur
« casque à fond » se retrouverait sur les haut-parleurs au démarrage suivant (TICKET-031).

⚠️ **La boucle vérifie le CONTENU de la réponse (`"ok":true`), pas le succès HTTP.**
`radio.php` répondait autrefois `ok:true` même quand la commande n'atteignait pas MPD —
socket pas encore prête en tout début de boot. La boucle sortait trop tôt sans avoir
basculé. Bug observé le 2026-07-03, corrigé des deux côtés.

⚠️ **Ne jamais remettre le chime avant Chromium** : il jouerait au démarrage de l'OS, pas
à l'apparition du lecteur.

### Relancer sans redémarrer

```bash
bash ~/hechicero/restart-kiosk.sh
```

C'est la version Wayland complète : elle tue Chromium **et** `wf-panel-pi` (qui ferait
apparaître des notifications de bureau), rejoue la séquence audio, puis relance avec
`--ozone-platform=wayland`.

---

## 3. Veille de l'écran — elle est VOULUE

⚠️ **Ce document disait « désactiver l'écran de veille ». C'est l'inverse du besoin :**
l'appareil est sur batterie, et laisser une dalle de 7 pouces allumée en permanence coûte
cher en autonomie.

La veille est gérée par **`hechicero-idle.service`** (service utilisateur), qui pilote
`swayidle` → `scripts/screen_dpms.sh` → `wlr-randr`. Le délai vient de
`screen_off_delay` dans `web/lecteur/config.json`. Détail dans `70-SERVICES_SYSTEMD.md` §6.

**Une seule source de vérité** : l'overlay de veille du navigateur dérive du *même* délai.
Ils étaient autrefois indépendants — 60 s pour l'overlay, 600 s pour la dalle — d'où neuf
minutes de dalle allumée sur page noire, prises pour une panne pendant des semaines
(TICKET-138).

⚠️ **`swayidle` ne voit que les entrées Wayland**, jamais les boutons GPIO lus par un
processus Python. Réveiller la dalle sans toucher l'écran laisserait donc `swayidle` bloqué
en état expiré, et l'écran ne s'éteindrait plus jamais. C'est pourquoi `buttons_daemon`
émet une frappe virtuelle (`wtype -k Shift_L`) à **tout** appui, sur n'importe quelle
broche. Voir `75-NON_REGRESSION.md` zone Z4.

---

## 4. Pas de relance automatique — c'est un choix

Il n'existe **aucun** `hechicero-kiosk.service`, et il ne doit pas en exister.

**Décision de Thomas** : un service qui relance Chromium en boucle masque le problème qui
l'a fait tomber. En cas de crash, on veut le constater, pas le voir disparaître. La reprise
se fait à la main (`restart-kiosk.sh`) ou par un redémarrage.

Conséquence assumée, depuis TICKET-119 : le bouton « Quitter le kiosque » de l'écran
technique ferme réellement Chromium, et **seul un redémarrage ramène la radio**. Il n'y a
sous labwc ni barre des tâches ni lanceur.

---

## 5. ⚠️ Le piège qui coûte le plus de temps

**Chromium garde la page en mémoire.** Modifier `web/lecteur/index.html` ne change
strictement rien à l'écran tant qu'on ne recharge pas :

```bash
sudo runuser -u thomas -- env WAYLAND_DISPLAY=wayland-0 \
  XDG_RUNTIME_DIR=/run/user/1000 /usr/bin/wtype -k F5
```

Sans ça, **on teste l'ancienne version en croyant tester la nouvelle**. Arrivé le
2026-08-21 sur l'écran technique : le daemon écrivait correctement sa demande, le disque
savait la traiter, et rien ne s'affichait.

Deux couches de cache se superposent, et il faut les distinguer :

| Symptôme | Cause | Remède |
|---|---|---|
| La page ne change pas après édition | Chromium garde son DOM en mémoire | `wtype -k F5` |
| Elle ne change pas **même après F5** | Cache HTTP de Chromium | en-tête `no-store` d'Apache — voir `20-SETUP_SYSTEME.md` |

⚠️ **Le smoke test ne peut pas voir le premier cas** : il compare la réponse d'Apache au
fichier du disque, pas ce que Chromium exécute. Il détecte le second (comparaison de `md5`).

---

## 6. Ce qui reste vrai côté enfant

- Chromium démarre automatiquement, plein écran, sans barre d'adresse
- Aucun geste tactile ne quitte le lecteur
- Aucune fenêtre parasite (`wf-panel-pi` est tué au démarrage)
- Aucune mise à jour Chromium visible

**La seule sortie est la combinaison casque + antenne maintenue 3 secondes** — hors de
portée d'un usage accidentel, et documentée comme un outil parent dans `15-INVARIANTS.md`
§2.1.

---

## 7. Tests de validation

| Test | Commande | Attendu |
|---|---|---|
| Démarrage complet | `sudo reboot` | LightDM → labwc → Chromium plein écran → chime |
| Relance manuelle | `bash ~/hechicero/restart-kiosk.sh` | Chromium revient, son sur haut-parleurs, volume bas |
| Page vivante | smoke test §5 | battement de cœur du kiosque de moins de 30 s |
| Déploiement réel | smoke test §3 | `md5` du disque = `md5` de la page servie |
| Veille | ne rien toucher pendant `screen_off_delay` | dalle éteinte **et** overlay affiché, ensemble |
| Réveil non tactile | appuyer sur un bouton physique | dalle rallumée, et `swayidle` réarmé |

⚠️ **Ne pas tester « `pkill chromium` → relance automatique »** : il n'y a pas de relance
automatique. Ce test figurait ici et n'a jamais pu passer.
