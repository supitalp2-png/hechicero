#!/usr/bin/env python3
"""
Génère le fichier WAV du son de démarrage Hechicero.
Accord grave C2-G2-C3-G3-E4, sine basses + triangle aigus, reverb profond.
Exécuter une seule fois : python3 scripts/generate_chime.py
Résultat : sounds/chime.wav
"""
import numpy as np
import wave
import os

RATE     = 44100
TOTAL    = 7.0      # secondes
ATTACK   = 0.4      # montée lente
HOLD     = 1.0      # plateau
VOLUME   = 1.0      # volume de référence — le scaling se fait dans play_chime.py

NOTES = [
    {'freq':  65.41, 'd': 0.00, 'g': 0.70, 'type': 'sine'},      # C2
    {'freq':  98.00, 'd': 0.10, 'g': 0.60, 'type': 'sine'},      # G2
    {'freq': 130.81, 'd': 0.20, 'g': 0.50, 'type': 'sine'},      # C3
    {'freq': 196.00, 'd': 0.30, 'g': 0.38, 'type': 'triangle'},  # G3
    {'freq': 329.63, 'd': 0.40, 'g': 0.25, 'type': 'triangle'},  # E4
]

n_samples = int(RATE * TOTAL)
t = np.linspace(0, TOTAL, n_samples, endpoint=False)
mix = np.zeros(n_samples, dtype=np.float64)

for note in NOTES:
    for detune_cents in [-3, +3]:
        freq = note['freq'] * (2 ** (detune_cents / 1200.0))
        d_samp = int(note['d'] * RATE)

        phase = 2 * np.pi * freq * t
        if note['type'] == 'sine':
            osc = np.sin(phase)
        else:
            osc = (2 / np.pi) * np.arcsin(np.sin(phase))

        env = np.zeros(n_samples)
        a_end = d_samp + int(ATTACK * RATE)
        h_end = a_end  + int(HOLD   * RATE)

        if a_end > d_samp:
            env[d_samp:a_end] = np.linspace(0, 1, a_end - d_samp)
        if h_end > a_end:
            env[a_end:h_end] = 1.0
        if n_samples > h_end:
            decay_len = n_samples - h_end
            env[h_end:] = np.exp(-3.5 * np.linspace(0, 1, decay_len))

        mix += osc * env * note['g'] * 0.6

# Reverb : delay + feedback
delay_samp = int(0.35 * RATE)
feedback   = 0.42
out = mix.copy()
for i in range(delay_samp, n_samples):
    out[i] += out[i - delay_samp] * feedback

# Normaliser
peak = np.max(np.abs(out))
if peak > 0:
    out = out / peak * VOLUME

# Convertir en 16-bit stéréo (HiFiBerry exige stéréo)
pcm = (out * 32767).astype(np.int16)
# Préfixe 400ms de silence : laisse le DAC se stabiliser (évite le craquement au démarrage)
silence = np.zeros(int(RATE * 0.40), dtype=np.int16)
pcm = np.concatenate([silence, pcm])
stereo = np.column_stack([pcm, pcm])

# Écrire le WAV
out_dir  = os.path.join(os.path.dirname(__file__), '..', 'sounds')
out_path = os.path.join(out_dir, 'chime.wav')
os.makedirs(out_dir, exist_ok=True)

with wave.open(out_path, 'w') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(RATE)
    wf.writeframes(stereo.tobytes())

print(f"Chime généré : {os.path.abspath(out_path)}")
print(f"Durée : {TOTAL}s — {n_samples} samples — stéréo 44100 Hz 16-bit")
