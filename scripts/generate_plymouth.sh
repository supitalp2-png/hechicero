#!/bin/bash
# Génère l'image de boot Hechicero depuis hechicero-gold.html
# Usage : bash scripts/generate_plymouth.sh
set -e

HTML_SRC="/home/thomas/hechicero/web/splash/hechicero-gold.html"
PNG_OUT="/tmp/hechicero-boot.png"

echo "=== Génération de l'image de boot Hechicero ==="

if [ ! -f "$HTML_SRC" ]; then
  echo "ERREUR: $HTML_SRC introuvable."
  exit 1
fi

# 1. Screenshot via Chromium headless
echo "Rendu via Chromium headless..."
chromium \
  --headless=new \
  --screenshot="$PNG_OUT" \
  --window-size=1024,600 \
  --hide-scrollbars \
  --no-sandbox \
  --disable-gpu \
  --run-all-compositor-stages-before-draw \
  "file://$HTML_SRC" 2>/tmp/chromium-headless.log

if [ ! -s "$PNG_OUT" ]; then
  echo "ERREUR: Chromium n'a pas généré l'image."
  cat /tmp/chromium-headless.log
  exit 1
fi
echo "Screenshot : $PNG_OUT ($(wc -c < "$PNG_OUT") bytes)"

# 2. Copie de l'aperçu (pas de swap — Plymouth affiche les couleurs telles quelles)
cp /tmp/hechicero-boot.png /home/thomas/hechicero/web/hechicero-preview.png
echo "Aperçu sauvegardé : Q:\\web\\hechicero-preview.png"

echo ""
echo ">>> Ouvrir Q:\web\hechicero-preview.png pour valider"
echo "    (l'aperçu semble teal/cyan — c'est normal, Plymouth l'affichera en or)"
echo ">>> Si OK : bash scripts/install_plymouth.sh && sudo reboot"
