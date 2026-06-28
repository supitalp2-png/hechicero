#!/bin/bash
# commit_photos.sh — Redimensionne les photos de Photos/ vers docs/photos/ et commite
#
# Usage : bash scripts/commit_photos.sh
# - Traite uniquement les photos nouvelles ou modifiées depuis le dernier commit
# - Redimensionne à 1920px max, qualité 82%
# - Commit + push automatique

set -e
cd "$(dirname "$0")/.."

SRC="Photos"
DST="docs/photos"
QUALITY=82
MAX_PX=1920

if ! command -v convert &>/dev/null; then
  echo "ImageMagick requis : sudo apt install imagemagick"
  exit 1
fi

mkdir -p "$DST"

new=0
updated=0

while IFS= read -r src; do

  # Nom de destination : sous-dossier_fichier (ex: 01-vue-ensemble_01-projet.jpg)
  subdir=$(basename "$(dirname "$src")")
  filename=$(basename "$src")
  dst="$DST/${subdir}_${filename}"

  # Traiter si destination absente ou source plus récente
  if [ ! -f "$dst" ] || [ "$src" -nt "$dst" ]; then
    echo "  → $dst"
    convert "$src" -resize "${MAX_PX}x${MAX_PX}>" -quality "$QUALITY" "$dst"
    if [ ! -f "$dst" ] 2>/dev/null || git ls-files --error-unmatch "$dst" 2>/dev/null; then
      updated=$((updated + 1))
    else
      new=$((new + 1))
    fi
  fi
done < <(find "$SRC" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | sort)

total=$((new + updated))

if [ "$total" -eq 0 ]; then
  echo "Aucune photo nouvelle ou modifiée. Rien à commiter."
  exit 0
fi

echo ""
echo "$total photo(s) traitée(s) ($new nouvelle(s), $updated mise(s) à jour)"
echo ""

# Compter les photos dans le dossier destination
nb=$(ls "$DST"/*.jpg "$DST"/*.png 2>/dev/null | wc -l)

git add "$DST/"
git diff --cached --stat

echo ""
read -rp "Message de commit (Entrée = défaut) : " msg
msg="${msg:-docs/photos : mise à jour photos boîtier ($nb photos)}"

git commit -m "$msg"
git push
echo ""
echo "✓ Photos commitées et poussées."
