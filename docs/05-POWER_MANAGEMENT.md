# Power Management — Projet Hechicero

> Dernière mise à jour : 2026-08-04
> Ce document est la **référence unique** pour l'alimentation et la batterie.
> Il absorbe l'ancienne spec `docs/80-ALIMENTATION.md` (session 7, 2026-06-26), supprimée le 2026-08-04 :
> les deux fichiers décrivaient le même sujet, l'un en spec à implémenter, l'autre en état réel,
> et ils divergeaient. Matériel : voir `docs/80-hardware.md`.

---

## 1. Objectif

L'autonomie en mobilité est le point faible historique du projet. Sans mesure précise, impossible de dimensionner la batterie ni de donner à l'enfant une information utile.

L'objectif n'est **pas** de mesurer une capacité en mAh, mais un **temps d'écoute réel**.

- Suivi fiable de l'état batterie (niveau, tension, courant)
- Autonomie exprimée en temps d'écoute
- Alertes progressives : 30 min → 10 min → arrêt propre
- Prévention des corruptions de carte SD par shutdown ordonné

**Autonomie cible : 3 heures** — un grand trajet en voiture ou une matinée autonome. Référence de départ, affinée par les mesures réelles.

---

## 2. Les deux personas

Ils expliquent *pourquoi* l'IHM enfant et le dashboard parent n'affichent pas les mêmes choses — à relire avant de toucher à l'affichage batterie.

### Persona Enfant

Une seule question : *est-ce que j'ai assez de batterie pour ce que je veux faire ?*

- Jauge en **temps restant**, jamais en pourcentage : « Il te reste 2h30 d'écoute »
- Popup discret au branchement : « Recharge estimée : 1h45 » (modèle Android)
- Pas de chiffres bruts, pas d'unités techniques
- Deux alertes seulement (§6)

### Persona Parent Geek

- Pourcentage visible **en complément** du temps restant
- Dashboard alimentation dédié (`web/admin/battery_dashboard.php`), séparé du dashboard d'écoute
- Objectif : comprendre pour décider — redimensionner la batterie ou optimiser la consommation

---

## 3. Architecture — trois scripts

| Script | Rôle | Service systemd |
|---|---|---|
| `scripts/battery_common.py` | Helpers partagés (INA219, MPD, écriture atomique) | — |
| `scripts/battery_tracker.py` | Collecte, détection de cycles, estimations | `battery_tracker.service` ✅ |
| `scripts/battery_watchdog.py` | Surveillance du seuil critique, arrêt propre | `battery_watchdog.service` ✅ |

> `scripts/get_status.py` + `hechicero-monitor.service` — **supprimés en session 11**. Ne plus utiliser.

---

## 4. Fichiers de données

| Fichier | Contenu | Écrit par |
|---|---|---|
| `data/battery_history.json` | Cycles complets avec datapoints | `battery_tracker.py` |
| `data/battery_stats.json` | État courant + estimations | `battery_tracker.py` |
| `data/last_session.json` | Position MPD au moment du shutdown critique | `battery_watchdog.py` |
| `data/config.json` | Seuils (`critical_level_percent`, etc.) | admin PHP |

> ⚠️ Ces fichiers sont dans `.gitignore` — jamais versionnés.
> ⚠️ Permissions obligatoires : `rw-rw-r--` (664) — `battery_common.py` les applique après chaque écriture.

### Schéma `data/battery_history.json`

```json
{
  "cycles": [
    {
      "discharge_start": "2026-06-01T14:00:00",
      "level_start": 87,
      "discharge_end": "2026-06-01T16:30:00",
      "level_end": 12,
      "duration_minutes": 150,
      "dominant_mode": "podcast",
      "datapoints": [
        {"t": "2026-06-01T14:00:00", "level": 87, "mpd_mode": "podcast", "screen": true},
        {"t": "2026-06-01T14:08:00", "level": 85, "mpd_mode": "podcast", "screen": true}
      ],
      "charge_start": "2026-06-01T16:31:00",
      "charge_end": "2026-06-01T18:45:00",
      "charge_duration_minutes": 134
    }
  ]
}
```

### Schéma `data/battery_stats.json`

```json
{
  "current_level": 73,
  "status": "discharging",
  "current_mpd_mode": "podcast",
  "estimated_autonomy_minutes": 112,
  "estimated_charge_time_minutes": 73,
  "last_updated": "2026-06-26T10:00:00",
  "cycles_recorded": 8,
  "model_confidence": "low",
  "consumption_by_mode": {
    "webradio": 4.2,
    "podcast": 3.1,
    "idle": 1.8
  }
}
```

`model_confidence` : `"low"` < 3 cycles, `"medium"` 3–9, `"high"` ≥ 10.

---

## 5. Ce qu'on mesure

### Par cycle de décharge

- Niveau au débranchement du secteur (%)
- Niveau au rebranchement (%)
- Durée totale du cycle (minutes)
- Mode MPD dominant : webradio / podcast local / veille
- → Ratio calculé : minutes d'écoute par % consommé

### Par cycle de recharge

- Durée pour passer du niveau de fin de décharge à ~100 %
- → Ratio calculé : minutes de charge par % récupéré

### À chaque point de mesure

Mesure **événementielle + delta** : un point est enregistré si

- transition détectée (branchement, débranchement, changement de mode MPD)
- **ou** variation du niveau ≥ 2 % depuis le dernier point

Format d'un point : `{timestamp, level, charging, mpd_mode, screen_on}`.

Les estimations s'affinent automatiquement au fil des cycles complets.

### ⚠️ Piège corrigé — `level_end` écrasé pendant la charge (2026-07-06)

`level_end` continuait d'être mis à jour **après** la fin de la décharge, pendant la recharge. Résultat : les vrais cycles profonds étaient enregistrés avec un `level_end` remonté et se retrouvaient invalidés à tort, pendant que des dizaines de micro-cycles factices polluaient l'historique (51 relevés, autonomie annoncée à 12 h contre 1,5–3 h réelles).

Corrigé le 2026-07-06 ; l'historique existant a été réparé par un script de migration à usage unique, supprimé du dépôt le 2026-08-04. **Ne pas réintroduire d'écriture de `level_end` hors de la phase de décharge.**

---

## 6. Alertes et seuils

| Seuil | Pour qui | Message | Comportement |
|---|---|---|---|
| 30 min restantes | Enfant | « Il te reste 30 minutes, pense à brancher ta radio » | Bandeau discret, jamais pendant la lecture |
| 10 min restantes | Enfant | Alerte plus visible | Actionnable immédiatement |
| Critique (7 % par défaut) | Système | *(aucun message)* | Arrêt propre automatique |

Les alertes destinées à l'enfant sont exprimées en **temps**, jamais en pourcentage.

---

## 7. Arrêt propre (`battery_watchdog`)

### Mécanisme

Le Waveshare UPS HAT (D) expose un GPIO de signal de coupure imminente, intercepté **en priorité** sur le polling de niveau. Fallback polling : sous le seuil critique (7 % par défaut), déclencher l'arrêt.

### Séquence

1. Sauvegarder la position MPD dans `data/last_session.json`
2. `mpc stop`
3. `sync` (flush filesystem)
4. `sudo shutdown -h now`

Au redémarrage, la position est restaurée par la logique existante de reprise de lecture — l'enfant ne voit rien.

### Test de simulation

```bash
python3 scripts/battery_watchdog.py --simulate-critical
cat data/last_session.json
```

> ⚠️ **Point non prouvé** : depuis le durcissement systemd (TICKET-011), `battery_watchdog.service` tourne avec `ProtectSystem=strict`. Le chemin `shutdown` est le seul des 8 services durcis à ne pas avoir été validé en conditions réelles — voir `docs/70-SERVICES_SYSTEMD.md`.

---

## 8. Service `battery_tracker`

Fichier : `/etc/systemd/system/battery_tracker.service`
(source dans le repo : `scripts/battery_tracker.service`)

```ini
[Unit]
Description=Hechicero Battery Tracker
After=network.target mpd.service

[Service]
ExecStart=/usr/bin/python3 /home/thomas/hechicero/scripts/battery_tracker.py
Restart=on-failure
RestartSec=10
User=thomas

[Install]
WantedBy=multi-user.target
```

### Activer

```bash
sudo cp scripts/battery_tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now battery_tracker
```

### Vérifier

```bash
systemctl status battery_tracker
journalctl -u battery_tracker -f
cat data/battery_stats.json
```

---

## 9. Dashboard parent

`web/admin/battery_dashboard.php`, accessible depuis le bureau d'icônes admin (TICKET-113).

| Bloc | Contenu |
|---|---|
| 1 — Situation actuelle | Statut (secteur / batterie / charge), niveau + temps restant, mode MPD, durée dans cet état |
| 2 — Cycle en cours | Courbe temps écoulé × niveau, en temps réel |
| 3 — Profils de consommation | Barres : %/heure par mode (webradio / podcast / veille écran) — **le graphique qui tranche** entre optimiser la conso et redimensionner la batterie |
| 4 — Historique des cycles | Tableau (date, durée, niveaux, mode dominant, autonomie réelle) + courbes de décharge superposées (anomalies, dégradation) |
| 5 — Courbes de recharge | Superposition des cycles — visualise la courbe CC/CV typique LiPo |
| 6 — Estimations et fiabilité | Autonomie et temps de recharge estimés, nombre de cycles ayant servi au calcul |

---

## 10. Démarrage — bouton physique RUN

Le Pi 5 ne démarre pas automatiquement quand le Waveshare UPS HAT (D) est alimenté : il attend un front logique sur la ligne RUN.

**Solution installée ✅** — bouton-poussoir momentané 16 mm chromé, câblé sur les broches RUN (fils rouge + bleu), logé dans un trou ⌀16 mm de la tranche supérieure du boîtier.

Appui court → démarrage. Appui court quand allumé → reset.

---

## 11. Comportement en cas de coupure

### Si la batterie tombe à 0 %

- Le HAT coupe physiquement l'alimentation
- Le Pi s'éteint brutalement si aucun shutdown n'a été anticipé

### Rôle de l'IHM enfant

- Afficher « Batterie faible »
- Empêcher le lancement de nouveaux contenus
- Réduire automatiquement le volume

### Rôle de l'interface admin

- Afficher l'état critique
- Proposer un bouton « shutdown propre »

### Après coupure

Le Pi **ne redémarre pas** automatiquement (limitation matérielle) : appui sur le bouton RUN obligatoire.

---

## 12. Contraintes techniques à respecter

- **Zéro CDN externe** — Chart.js est servi localement (`web/js/chart.min.js`)
- Ne jamais casser `data.json` ni MPD
- `battery_history.json` et `battery_stats.json` : écriture atomique (tmp + rename)
- `battery_tracker.py` tourne en systemd avec `Restart=on-failure`
- Pour tout travail sur le GPIO de coupure : vérifier la datasheet du HAT UPS (D)
