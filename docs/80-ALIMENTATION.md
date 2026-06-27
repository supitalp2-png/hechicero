# Gestion de l'alimentation — Projet Hechicero

> Dernière mise à jour : 2026-06-26 (session 7)
> Tickets associés : TICKET-080, 081, 082, 083, 084

---

## Contexte et objectif

Hechicero tourne sur Raspberry Pi 5 + Waveshare UPS HAT (D). L'autonomie en mobilité est un point faible du projet : sans mesure précise, impossible de dimensionner la batterie correctement ou de donner à l'enfant une information utile sur l'autonomie restante.

L'objectif n'est **pas** de mesurer la capacité en mAh, mais en **temps d'écoute réel**.

**Autonomie cible : 3 heures** — correspond à un grand trajet en voiture ou à une matinée autonome. Ce chiffre est une référence de départ, à affiner par les mesures réelles.

---

## Les deux personas

### Persona Enfant

Une seule question : *est-ce que j'ai assez de batterie pour ce que je veux faire ?*

- Jauge en temps restant, pas en pourcentage : "Il te reste 2h30 d'écoute"
- Popup discret au branchement : "Recharge estimée : 1h45" (comme Android)
- Pas de chiffres bruts, pas d'unités techniques
- Deux alertes (voir §Alertes)

### Persona Parent Geek

- Pourcentage visible en complément du temps restant sur l'IHM principale
- Dashboard dédié alimentation (page admin séparée) avec graphiques et historique
- Objectif : comprendre ce qui se passe pour décider d'agir (redimensionner la batterie, optimiser la consommation)

---

## Alertes et seuils

| Seuil | Pour qui | Message | Comportement |
|---|---|---|---|
| 30 min restantes | Enfant | "Il te reste 30 minutes, pense à brancher ta radio" | Bandeau discret, jamais pendant la lecture |
| 10 min restantes | Enfant | Alerte plus visible | Actionnable immédiatement |
| Critique | Système | (aucun message) | Arrêt propre automatique |

Les alertes sont exprimées en **temps**, jamais en pourcentage.

---

## Ce qu'on mesure (TICKET-080)

### Par cycle de décharge

- Niveau au moment où le secteur est débranché (%)
- Niveau au moment où le secteur est rebranché (%)
- Durée totale du cycle (minutes)
- Mode MPD dominant pendant le cycle : webradio / podcast local / veille
- → Ratio calculé : minutes d'écoute par % de batterie consommé

### Par cycle de recharge

- Durée pour passer du niveau de fin de décharge à ~100%
- → Ratio calculé : minutes de charge par % récupéré

### À chaque point de mesure

Mesure **événementielle + delta** : on enregistre un point si :
- transition détectée (branchement, débranchement, changement mode MPD)
- OU variation du niveau > 2% depuis le dernier point

À chaque point : `{timestamp, level, charging, mpd_mode, screen_on}`

---

## Schéma des données

### `data/battery_history.json`

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

### `data/battery_stats.json`

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

## Dashboard parent (TICKET-081)

Page PHP dédiée, accessible depuis le menu admin. Séparée du dashboard d'écoute.

### Bloc 1 — Situation actuelle

Lecture immédiate en haut de page :
- Statut : sur secteur / sur batterie / en charge
- Niveau actuel (%) + temps restant estimé
- Mode MPD actif
- Depuis combien de temps dans cet état

### Bloc 2 — Courbe du cycle en cours

Si sur batterie ou en recharge :
- Axe X : temps écoulé depuis début du cycle
- Axe Y : niveau (%)
- Courbe en temps réel du cycle actuel

### Bloc 3 — Profils de consommation par mode

Graphique en barres :
- Vitesse de décharge en %/heure selon le mode : webradio / podcast local / veille écran
- Calculé sur l'ensemble des cycles enregistrés
- **Graphique clé** pour décider si on optimise la consommation ou redimensionne la batterie

### Bloc 4 — Historique des cycles

- Tableau : date, durée, niveau début/fin, mode dominant, autonomie réelle obtenue
- Graphique avec courbes de décharge superposées (détecte anomalies + dégradation capacité)

### Bloc 5 — Courbes de recharge

- Superposition des cycles de recharge
- Visualise la courbe CC/CV typique LiPo (rapide au début, plateau final lent)

### Bloc 6 — Estimations et fiabilité

- Autonomie estimée (basée sur N derniers cycles)
- Temps de recharge estimé
- Indicateur de fiabilité : nombre de cycles ayant servi au calcul

---

## Arrêt propre sur batterie critique (TICKET-083)

### Mécanisme

Le Waveshare UPS HAT (D) expose un GPIO de signal de coupure imminente. Ce signal doit être intercepté **en priorité** sur le polling de niveau.

Fallback polling : si le niveau tombe sous le seuil critique (à définir lors de l'implémentation, typiquement 5–8%), déclencher l'arrêt.

### Séquence d'arrêt

1. Sauvegarder position MPD (podcast id + position en secondes)
2. Sauvegarder état interface (écran actif, langue sélectionnée)
3. Arrêter MPD proprement
4. Arrêter Apache (optionnel, graceful)
5. `sync` — forcer l'écriture des caches disque sur la carte SD
6. `shutdown -h now`

### Au redémarrage

La position MPD est restaurée automatiquement via la logique existante de reprise de lecture. L'enfant ne voit rien.

---

## Ordre d'implémentation recommandé pour Coco

```
TICKET-080 → TICKET-084 → TICKET-083 → TICKET-082 → TICKET-081
```

**Pourquoi cet ordre :**
- 080 est le fondement (sans données, rien ne fonctionne)
- 084 calcule les estimations (nécessaire pour 082 et 081)
- 083 est isolé et critique en sécurité (implémentation indépendante)
- 082 affiche les résultats côté enfant
- 081 affiche les résultats côté parent (le plus complexe, en dernier)

---

## Contraintes techniques à respecter

- Zéro CDN externe — les graphiques Chart.js doivent être servis localement
- Ne jamais casser `data.json` ni MPD
- `battery_history.json` et `battery_stats.json` : écriture atomique (tmp + rename)
- Le service `battery_tracker.py` doit tourner en systemd avec `Restart=on-failure`
- Vérifier la datasheet du HAT UPS D pour le GPIO de signal de coupure

---
