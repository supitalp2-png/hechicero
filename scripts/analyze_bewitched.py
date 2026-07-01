#!/usr/bin/env python3
"""
Détecte les notes du son Bewitched (2.54s → 3.65s).
Lance : python3 scripts/analyze_bewitched.py
"""
import numpy as np
import subprocess

RATE = 44100

result = subprocess.run([
    'ffmpeg', '-v', 'quiet', '-ss', '2.54', '-t', '1.1',
    '-i', 'sounds/bewitched.mp3',
    '-ac', '1', '-ar', str(RATE), '-f', 's16le', 'pipe:1'
], capture_output=True)

data = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32) / 32768.0

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def freq_to_note(f):
    if f <= 0: return '?'
    n = 12 * np.log2(f / 440.0) + 69
    name = NOTES[int(round(n)) % 12]
    octave = int(round(n)) // 12 - 1
    return f"{name}{octave} ({f:.0f} Hz)"

window = 4096
hop    = 1024
print(f"{'Temps':>7}  Note détectée")
print("-" * 32)
seen = []
for i in range(0, len(data) - window, hop):
    frame = data[i:i+window]
    energy = np.sqrt(np.mean(frame**2))
    if energy < 0.015:
        continue
    spectrum = np.abs(np.fft.rfft(frame * np.hanning(window)))
    freqs    = np.fft.rfftfreq(window, 1.0/RATE)
    # cherche le pic entre 150 Hz et 4000 Hz
    mask = (freqs > 150) & (freqs < 4000)
    peak_freq = freqs[mask][np.argmax(spectrum[mask])]
    note = freq_to_note(peak_freq)
    if not seen or seen[-1] != note:
        print(f"{i/RATE:>6.3f}s  {note}")
        seen.append(note)
