# Power Management - Hechicero

## Objectif
Afficher l'état batterie via l'interface web et gérer des pré-alertes pour éviter un shutdown violent.

## Fichiers clés
- `scripts/get_status.py` : lit INA219, écrit `web/status.json`, gère shutdown_pending.
- `web/index.php` : dashboard web (lit `/status.json`).
- `data/config.json` : seuils et intervalles.
- `data/shutdown_pending` : timestamp créé quand seuil critique atteint.

## Installation rapide
1. Créer utilisateur système :
   sudo useradd --system --create-home --shell /usr/sbin/nologin hechicero
2. Ajouter groupes :
   sudo usermod -aG i2c,audio,gpio,www-data hechicero
3. Copier fichiers dans le repo (emplacements indiqués).
4. Permissions :
   sudo chown -R hechicero:hechicero /home/thomas/hechicero
   sudo chmod -R 750 /home/thomas/hechicero/scripts
   sudo chown -R hechicero:www-data /home/thomas/hechicero/web
5. Activer service :
   sudo systemctl daemon-reload
   sudo systemctl enable --now hechicero-battery
6. Vérifier :
   sudo journalctl -u hechicero-battery -f
   curl -s http://localhost/status.json | jq .

## Critères d'acceptation
- Le dashboard web affiche % / état / alertes.
- `web/status.json` est mis à jour périodiquement.
- Quand % <= shutdown_threshold, `data/shutdown_pending` est créé et `status.json` contient `shutdown_recommended` après le délai.


# Power Management — Lecture et format des données

## Format attendu de `status.json`
```json
{
  "percent": 98,
  "voltage_v": 4.188,
  "current_ma": 0,
  "power_w": 0.006,
  "state": "Sur batterie 🔋",
  "alert": null,
  "ts": 1780818044
}


Fréquences
Frontend : polling toutes les 10 s (modifiable dans web/index.php : setInterval(refresh, 10000)).

Backend : intervalle d'écriture dépend du sleep dans scripts/get_status.py — documenter la valeur actuelle dans le script ou via config.json.

Recommandations techniques
Écriture atomique : écrire dans /home/thomas/hechicero/web/status.json.tmp puis mv vers status.json.

Permissions : status.json en -rw-r--r-- (644) et appartenant à thomas:www-data si Apache sert le fichier.

Validation : le script doit valider le JSON avant écriture (ex. json.dumps + fsync).

Tests : simuler valeurs extrêmes et vérifier affichage et alertes.

Code

---

### `docs/prompt.md`
```markdown
STOP. Retour à la réalité : reprends ton rôle de partenaire d'ingénierie. Oublie ce 