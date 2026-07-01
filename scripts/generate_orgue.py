#!/usr/bin/env python3
"""
Génère un jingle orgue moderne pour Hechicero.
Reprend les notes du son Bewitched : F, Ab, Bb (accord Bb7 = Sib dominant 7),
transposées 3 octaves plus bas → F3, Ab3, Bb3.
Timbre Hammond (synthèse additive) + reverb spatiale.
Résultat : sounds/boot_orgue.wav
"""
import numpy as np
import wave
import os
import subprocess
import tempfile

RATE   = 44100
TOTAL  = 4.0   # durée totale avant post-traitement

# --- Synthèse orgue type Hammond (drawbars) ---
def organ_tone(freq, duration):
    t = np.linspace(0, duration, int(RATE * duration), endpoint=False)
    harmonics = [
        (1, 0.80),   # 8'  fondamentale
        (2, 0.45),   # 4'  octave
        (3, 0.22),   # 2⅔' quinte
        (4, 0.15),   # 2'  double octave
        (6, 0.07),   # 1⅓'
    ]
    sig = sum(g * np.sin(2 * np.pi * freq * n * t) for n, g in harmonics)
    return sig / 0.80  # normaliser par le gain max

def envelope(sig, attack, hold, release):
    n   = len(sig)
    env = np.zeros(n)
    a   = int(attack  * RATE)
    h   = int(hold    * RATE)
    r   = int(release * RATE)
    if a > 0:            env[:a]           = np.linspace(0, 1, a)
    eh = min(a + h, n); env[a:eh]         = 1.0
    er = min(eh + r, n)
    if er > eh:          env[eh:er]        = np.linspace(1, 0, er - eh)
    return sig * env

# --- Notes du Bewitched transposées -3 octaves ---
# Original : A#6 (Bb) ↔ F6, avec Ab6 de passage → Bb7
# Ici      : F3 → Bb3 → Ab3 → accord Bb3+F4+Ab4 en suspension
#
#  freq       start  atk   hold  rel   gain
notes = [
    (174.61,   0.00,  0.04, 0.10, 0.22, 0.65),   # F3  (note de départ)
    (233.08,   0.18,  0.04, 0.10, 0.22, 0.62),   # Bb3 (Sib — oscillation principale)
    (207.65,   0.36,  0.04, 0.10, 0.22, 0.55),   # Ab3 (Lab — note de passage)
    (233.08,   0.54,  0.05, 0.12, 0.28, 0.60),   # Bb3 (retour, comme dans l'original)
    # Accord final Bb7 qui reste en suspension
    (174.61,   0.78,  0.07, 1.00, 1.50, 0.48),   # F3
    (233.08,   0.78,  0.07, 1.00, 1.50, 0.45),   # Bb3
    (349.23,   0.80,  0.07, 1.00, 1.50, 0.38),   # F4  (octave)
    (415.30,   0.82,  0.07, 1.00, 1.50, 0.28),   # Ab4 (Lab — couleur Bb7)
]

mix = np.zeros(int(RATE * TOTAL))
for freq, start, atk, hold, rel, gain in notes:
    dur = atk + hold + rel + 0.1
    tone = envelope(organ_tone(freq, dur), atk, hold, rel)
    s = int(start * RATE)
    e = min(s + len(tone), len(mix))
    mix[s:e] += tone[:e - s] * gain

# Normaliser
peak = np.max(np.abs(mix))
if peak > 0:
    mix = mix / peak * 0.82

# WAV stéréo 16-bit
pcm    = (mix * 32767).astype(np.int16)
stereo = np.column_stack([pcm, pcm])

raw_path = tempfile.mktemp(suffix='_raw.wav')
with wave.open(raw_path, 'w') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(RATE)
    wf.writeframes(stereo.tobytes())

# --- Post-traitement ffmpeg : EQ + reverb spatiale ---
out_dir  = os.path.join(os.path.dirname(__file__), '..', 'sounds')
out_path = os.path.join(out_dir, 'boot_orgue.wav')
os.makedirs(out_dir, exist_ok=True)

filters = ','.join([
    'equalizer=f=10000:width_type=o:width=2:g=5',   # air/brillance
    'equalizer=f=5000:width_type=o:width=2:g=2',    # présence
    'equalizer=f=350:width_type=o:width=2:g=-4',    # retire la boîte
    'highpass=f=60',                                  # retire grondement
    'apad=pad_dur=3',                                 # silence pour la queue
    # Reverb diffuse (10 taps courts → salle grande salle propre)
    'aecho=0.9:0.55:8|17|30|46|65|90|120|160|210|270:0.17|0.15|0.13|0.11|0.09|0.07|0.05|0.04|0.03|0.02',
    'extrastereo=m=2.8',                              # largeur stéréo
    'atrim=end=4.2',
    'afade=t=out:st=3.0:d=1.2',
    'adelay=200|200',                                 # silence DAC au démarrage
    'aresample=44100',
    'aformat=s16',
])

subprocess.run(
    ['ffmpeg', '-y', '-i', raw_path, '-af', filters,
     '-ac', '2', '-ar', '44100', out_path],
    check=True
)
os.unlink(raw_path)
print(f"✅ Généré : {out_path}")
print(f"   Écoute : aplay {out_path}")
