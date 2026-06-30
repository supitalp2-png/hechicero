# Power Management — Projet Hechicero

> Dernière mise à jour : 2026-06-28 (session 11)
> Spec complète : `docs/80-ALIMENTATION.md`

Ce document décrit la gestion de l’alimentation et de la batterie du système Hechicero.

---

## 1. Objectif

- Suivi fiable de l’état batterie (niveau, tension, courant)
- Mesure de l’autonomie réelle en **temps d’écoute** (pas en mAh)
- Affichage du temps restant à l’enfant et au parent
- Alertes progressives : 30 min → 10 min → arrêt propre
- Prévention des corruptions de carte SD par shutdown ordonné

---

## 2. Architecture — trois scripts

| Script | Rôle | Service systemd |
|---|---|---|
| `scripts/battery_common.py` | Helpers partagés (INA219, MPD, écriture atomique) | — |
| `scripts/battery_tracker.py` | Collecte des données, détection cycles, estimations | `battery_tracker.service` ✅ |
| `scripts/battery_watchdog.py` | Surveillance seuil critique, arrêt propre | `battery_watchdog.service` ✅ |

> `scripts/get_status.py` + `hechicero-monitor.service` — **supprimés de la rotation session 11**. Ne plus utiliser.

---

## 3. Fichiers de données

| Fichier | Contenu | Écrit par |
|---|---|---|
| `data/battery_history.json` | Cycles complets avec datapoints | `battery_tracker.py` |
| `data/battery_stats.json` | État courant + estimations | `battery_tracker.py` |
| `data/last_session.json` | Position MPD au moment du shutdown critique | `battery_watchdog.py` |
| `data/config.json` | Seuils (critical_level_percent, etc.) | admin PHP |

> ⚠️ Ces fichiers sont dans `.gitignore` — ils ne sont jamais versionnés.
> ⚠️ Permissions obligatoires : `rw-rw-r--` (664) — `battery_common.py` les applique après chaque écriture.

---

## 4. Service battery_tracker

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

## 5. Stratégie de mesure

- Mesure **événementielle + delta** : un point est enregistré si transition détectée (charge ↔ décharge, changement mode MPD) OU si le niveau a varié de ≥ 2%
- Corrélation avec l’état MPD à chaque point : `webradio` / `podcast` / `idle`
- Les estimations s’affinent automatiquement au fil des cycles complets

---

## 6. Alertes et seuils

| Seuil | Déclencheur | Action |
|---|---|---|
| 30 min restantes | `battery_tracker.py` → `battery_stats.json` | IHM enfant affiche bandeau discret |
| 10 min restantes | idem | IHM enfant affiche alerte visible |
| Critique (7% défaut) | `battery_watchdog.py` ou GPIO HAT | Arrêt propre automatique |

---

## 7. Arrêt propre (battery_watchdog)

Séquence déclenchée au seuil critique :
1. Sauvegarder position MPD dans `data/last_session.json`
2. `mpc stop`
3. `sync` (flush filesystem)
4. `sudo shutdown -h now`

Au redémarrage, l’IHM enfant propose de reprendre là où on s’est arrêté.

### Test simulation
```bash
python3 scripts/battery_watchdog.py --simulate-critical
cat data/last_session.json
```

---

## 10. Démarrage — bouton physique RUN

### Comportement
Le Pi 5 ne démarre pas automatiquement quand le Waveshare UPS HAT (D) est alimenté — il attend un front logique sur la ligne RUN.

### Solution installée ✅
Bouton-poussoir momentané 16mm chromé, câblé sur les broches RUN du Pi 5 (fils rouge + bleu), logé dans un trou ∅16mm de la tranche supérieure chromée du boîtier.

Appui court → démarrage. Appui court quand allumé → reset.

---

## 11. Comportement attendu en cas de coupure
### 🔹 Si la batterie tombe à 0 %
- le HAT coupe physiquement l’alimentation  
- le Pi s’éteint brutalement si aucun shutdown n’a été anticipé  

### 🔹 Rôle du script `battery_watchdog.py`
- détecter le seuil critique (polling + signal GPIO HAT)  
- sauvegarder la session MPD dans `data/last_session.json`  
- déclencher `shutdown -h now`  

### 🔹 Rôle de l’IHM enfant
- afficher un message “Batterie faible”  
- empêcher le lancement de nouveaux contenus  
- réduire automatiquement le volume  

### 🔹 Rôle de l’interface admin
- afficher l’état critique  
- proposer un bouton “shutdown propre”  

### 🔹 Rôle du système
- déclencher un `shutdown now` si `shutdown_pending` existe  
- éviter toute corruption de fichiers  

### 🔹 Après coupure
- le Pi ne redémarre pas automatiquement (limitation matérielle)  
- l’utilisateur doit appuyer sur le bouton RUN  

---
