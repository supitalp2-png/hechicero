#!/bin/bash
# test_decharge_profonde.sh — prépare et annule la campagne de mesure TICKET-134
#
# ── OBJECTIF ────────────────────────────────────────────────────────────────
# Un seul cycle de décharge (12 h aller-retour, contrainte de temps de Thomas)
# pour répondre à : jusqu'où peut-on descendre avant que le Pi décroche ?
#
# ── CE QU'ON ACCEPTE ET CE QU'ON REFUSE ─────────────────────────────────────
# ACCEPTÉ  : une coupure non maîtrisée du Pi. Risque carte SD couvert par une
#            sauvegarde complète faite avant.
# REFUSÉ   : dégrader les cellules. Elles ont un jour.
#
# ── POURQUOI 5 % ET PAS PLUS BAS ────────────────────────────────────────────
# Table LiPo du projet (battery_common._LIPO_TABLE), tensions mesurées SOUS
# CHARGE :   15 % = 3,49 V   10 % = 3,44 V   5 % = 3,35 V   0 % = 3,00 V
# Le constructeur du HAT coupe à 3,15 V (cf. démo dans scripts/INA219.py).
#
# À −2 A l'affaissement est important : une cellule lue à 3,35 V en pleine
# consommation remonte bien au-dessus de 3,5 V dès que la charge cesse. 5 %
# affiché laisse donc une marge réelle sur les 3,15 V, et une marge encore
# plus grande sur la limite chimique (~3,0 V au repos).
# En dessous, l'interpolation de la table devient hasardeuse (3 % ≈ 3,21 V) et
# on s'approche vraiment du seuil constructeur. 5 % est le plus bas défendable.
#
# ⚠️ CE QU'ON NE TOUCHE PAS : la protection matérielle du HAT (registre 0x2d et
# le circuit de protection du pack). Elle n'est pas désactivable depuis le Pi,
# et c'est tant mieux — c'est le vrai filet de sécurité des cellules.
#
# Usage :
#   sudo ./scripts/test_decharge_profonde.sh armer      # avant le test
#   sudo ./scripts/test_decharge_profonde.sh restaurer  # après, IMPÉRATIF
#   ./scripts/test_decharge_profonde.sh etat

set -u
CONFIG="/home/thomas/hechicero/data/config.json"
SAUVEGARDE="/home/thomas/hechicero/data/config.json.avant_test_decharge"

# Réglages de campagne. Intervalles resserrés parce qu'on ignore la forme du
# coude de fin de décharge sur ces cellules — c'est l'objet de la mesure. Un
# relevé par minute pourrait n'en donner que deux ou trois points.
SEUIL_TEST=5          # au lieu de 15
INTERVALLE_TEST=15    # secondes, au lieu de 60
POLL_WATCHDOG=10      # secondes, au lieu de 30

appliquer() {
    python3 - "$CONFIG" "$1" "$2" "$3" <<'PY'
import json, sys
chemin, seuil, intervalle, poll = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
with open(chemin, encoding="utf-8") as fh:
    cfg = json.load(fh)
cfg["shutdown_threshold_percent"] = seuil
cfg["battery_check_interval_seconds"] = intervalle
cfg["battery_watchdog_poll_seconds"] = poll
tmp = chemin + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    json.dump(cfg, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
import os; os.replace(tmp, chemin)
print(f"seuil={seuil}%  intervalle={intervalle}s  poll_watchdog={poll}s")
PY
}

case "${1:-etat}" in
  armer)
      if [ -f "$SAUVEGARDE" ]; then
          echo "⚠️  Une sauvegarde existe déjà : le test semble déjà armé."
          echo "    Lancer 'restaurer' d'abord si ce n'est pas voulu."
          exit 1
      fi
      cp "$CONFIG" "$SAUVEGARDE"
      echo "Config d'origine sauvegardée dans $SAUVEGARDE"
      appliquer "$SEUIL_TEST" "$INTERVALLE_TEST" "$POLL_WATCHDOG"
      systemctl restart battery_tracker battery_watchdog
      echo
      echo "✅ Armé. Débranche le secteur et laisse tourner."
      echo "   ⚠️  NE PAS OUBLIER : sudo $0 restaurer  (après le test)"
      ;;

  restaurer)
      if [ ! -f "$SAUVEGARDE" ]; then
          echo "⚠️  Pas de sauvegarde — le test n'était pas armé, ou déjà restauré."
          echo "    Remise aux valeurs nominales quand même."
          appliquer 15 60 30
      else
          cp "$SAUVEGARDE" "$CONFIG"
          rm -f "$SAUVEGARDE"
          echo "Config d'origine restaurée."
      fi
      systemctl restart battery_tracker battery_watchdog
      python3 -c "
import json;c=json.load(open('$CONFIG'))
print('seuil =', c.get('shutdown_threshold_percent'), '%  intervalle =', c.get('battery_check_interval_seconds'), 's')"
      ;;

  etat)
      python3 -c "
import json,os
c=json.load(open('$CONFIG'))
arme = os.path.exists('$SAUVEGARDE')
print('MODE TEST ARMÉ' if arme else 'configuration nominale')
print('  seuil d\'arrêt      :', c.get('shutdown_threshold_percent'), '%')
print('  intervalle tracker  :', c.get('battery_check_interval_seconds'), 's')
print('  poll watchdog       :', c.get('battery_watchdog_poll_seconds', 30), 's')"
      ;;

  *)
      echo "Usage: $0 armer|restaurer|etat" >&2
      exit 1
      ;;
esac
