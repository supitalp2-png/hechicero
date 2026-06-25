#!/usr/bin/env python3
"""
Joue le son de démarrage Hechicero via MPD (pas de click DAC).
Appelé par kiosk.sh au démarrage du Pi.
"""
import json, wave, numpy as np, subprocess, os, tempfile, sys

CONFIG_PATH = '/home/thomas/hechicero/web/lecteur/config.json'
CHIME_PATH  = '/home/thomas/hechicero/sounds/chime.wav'
MPD_SOCKET  = '/run/mpd/socket'

# Lire config.json
chime_enabled = True
chime_volume  = 8
try:
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    chime_enabled = cfg.get('chime_enabled', True)
    chime_volume  = cfg.get('chime_volume', 8)
except Exception as e:
    print(f"[play_chime] config.json illisible : {e}", file=sys.stderr)

if not chime_enabled:
    sys.exit(0)

if not os.path.exists(CHIME_PATH):
    print(f"[play_chime] Fichier introuvable : {CHIME_PATH}", file=sys.stderr)
    sys.exit(1)

volume = max(0.0, min(1.0, chime_volume / 100.0))

# Générer un WAV temporaire au bon volume
with wave.open(CHIME_PATH) as wf:
    frames    = wf.readframes(wf.getnframes())
    rate      = wf.getframerate()
    channels  = wf.getnchannels()
    sampwidth = wf.getsampwidth()

data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
data = (data * volume).clip(-32768, 32767).astype(np.int16)

tmp_path = tempfile.mktemp(suffix='.wav')
try:
    with wave.open(tmp_path, 'w') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        wf.writeframes(data.tobytes())

    # Jouer via MPD → DAC déjà chaud → pas de click
    import time

    def mpc(*args):
        r = subprocess.run(['mpc', '--host', MPD_SOCKET] + list(args),
                           capture_output=True, text=True)
        return r.stdout.strip()

    # Sauvegarder l'état MPD
    was_playing = 'playing' in mpc('status')
    orig_vol    = int([l for l in mpc('volume').splitlines()
                       if 'volume:' in l][0].split(':')[1].strip().rstrip('%') or 0)

    mpc('stop')
    mpc('clear')
    mpc('volume', '50')          # volume chime fixe indépendant du réglage enfant
    mpc('add', f'file://{tmp_path}')
    mpc('play')

    duration = len(data) / (rate * channels)
    time.sleep(duration + 0.3)

    mpc('stop')
    mpc('clear')
    mpc('volume', str(orig_vol))  # restaurer le volume d'origine

finally:
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
