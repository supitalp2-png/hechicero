#!/bin/bash
# Télécharge les polices Google Fonts pour utilisation hors réseau.
# À lancer UNE SEULE FOIS sur le Pi avec connexion internet.
# Usage : bash scripts/download_fonts.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FONTS_DIR="$SCRIPT_DIR/../web/fonts"
mkdir -p "$FONTS_DIR"

echo "Téléchargement de Great Vibes..."
CSS=$(curl -s -A "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0" \
  "https://fonts.googleapis.com/css2?family=Great+Vibes&display=swap")

URL=$(echo "$CSS" | grep -oE 'https://fonts\.gstatic\.com/[^)]+\.woff2' | head -1)

if [ -z "$URL" ]; then
  echo "ERREUR: impossible de récupérer l'URL de la police."
  echo "Vérifier la connexion internet ou télécharger manuellement depuis :"
  echo "  https://fonts.google.com/specimen/Great+Vibes"
  echo "  → Placer le fichier woff2 dans web/fonts/GreatVibes-Regular.woff2"
  exit 1
fi

curl -s -L "$URL" -o "$FONTS_DIR/GreatVibes-Regular.woff2"
SIZE=$(wc -c < "$FONTS_DIR/GreatVibes-Regular.woff2")
echo "OK — Great Vibes sauvegardé : $FONTS_DIR/GreatVibes-Regular.woff2 (${SIZE} bytes)"
