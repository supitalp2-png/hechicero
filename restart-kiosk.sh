#!/bin/bash
# Relance Chromium en mode kiosque depuis SSH (Wayland)
pkill chromium 2>/dev/null
pkill wf-panel-pi 2>/dev/null || true   # supprime toutes les notifications desktop
sleep 1

# ⚠️ Sécurité audio (TICKET-031) — pas de détection matérielle casque/HP :
# on force la sortie sur les HP + un volume enfant bas AVANT de lancer
# Chromium, pour ne jamais hériter d'un état "casque à fond" resté actif
# côté MPD depuis la session précédente. On vérifie le vrai contenu de la
# réponse (pas juste le succès HTTP) : radio.php pouvait répondre ok:true
# même si la commande n'avait pas atteint MPD.
for i in $(seq 1 15); do
  resp=$(curl -sf "http://localhost/lecteur/radio.php?action=set_output&mode=hp")
  if echo "$resp" | grep -q '"ok":true'; then
    break
  fi
  sleep 1
done
curl -sf "http://localhost/lecteur/radio.php?action=setvol&vol=13" >/dev/null  # 20% IHM ≈ 13% MPD (speakers_max=66)

WAYLAND_DISPLAY=wayland-0 \
XDG_RUNTIME_DIR=/run/user/$(id -u) \
XDG_SESSION_TYPE=wayland \
nohup chromium \
  --ozone-platform=wayland \
  --noerrdialogs --disable-infobars --kiosk \
  http://localhost/lecteur \
  &>/tmp/chromium.log &
echo "Chromium relancé (PID $!)"
# Chime après 6s — le temps que Chromium charge la page
(sleep 6 && python3 /home/thomas/hechicero/scripts/play_chime.py) &
