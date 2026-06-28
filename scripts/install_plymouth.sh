#!/bin/bash
# Installe l'image de boot validée dans le thème Plymouth.
# Lancer après avoir vérifié generate_plymouth.sh
set -e

PNG_OUT="/tmp/hechicero-boot.png"
THEME_DIR="/usr/share/plymouth/themes/hechicero"

if [ ! -f "$PNG_OUT" ]; then
  echo "ERREUR: $PNG_OUT introuvable. Lancer d'abord : bash scripts/generate_plymouth.sh"
  exit 1
fi

echo "Installation du thème Plymouth..."
sudo mkdir -p "$THEME_DIR"
sudo cp "$PNG_OUT" "$THEME_DIR/hechicero-boot.png"

sudo tee "$THEME_DIR/hechicero.plymouth" > /dev/null << 'EOF'
[Plymouth Theme]
Name=Hechicero
Description=Hechicero boot splash - Or
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/hechicero
ScriptFile=/usr/share/plymouth/themes/hechicero/hechicero.script
EOF

sudo tee "$THEME_DIR/hechicero.script" > /dev/null << 'EOF'
wallpaper_image = Image("hechicero-boot.png");
screen_width  = Window.GetWidth();
screen_height = Window.GetHeight();
scaled = wallpaper_image.Scale(screen_width, screen_height);
sprite = Sprite(scaled);
sprite.SetX(0);
sprite.SetY(0);
sprite.SetZ(-100);
EOF

sudo plymouth-set-default-theme hechicero
sudo update-initramfs -u

echo ""
echo "=== Terminé — sudo reboot pour voir le résultat ==="
