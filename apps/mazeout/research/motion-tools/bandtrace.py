"""0.1 s spectral trace (level + 4 strongest partials with note names) of a stretch of an owner video's audio.
Usage: bandtrace.py A|B START END [LABEL] -> appends to out/bandtrace.txt. Used to split the YT-A unlock chime out of the
coin cue's segment (A 73.6-78.6, 180.3-185.4) and to check a plain coin cue (A 94.5-97.5)."""
import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
key, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]); lab = sys.argv[4] if len(sys.argv) > 4 else ''
f = {'A': 'YT1-L01-20-full.wav', 'B': 'YT2-L11-38-full.wav'}[key]
w = wave.open(os.path.join(mf.SP, '..', 'sound-refs', f)); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
def nm(fq):
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']; m = 69 + 12 * np.log2(fq / 440); k = int(round(m))
    return f"{names[k % 12]}{k // 12 - 1}{int(round((m - k) * 100)):+d}c"
seg = x[int(a * sr):int(b * sr)]; n = 4096; hop = int(0.1 * sr); out = [f"== {key} {a}-{b} {lab}"]
for i in range(0, len(seg) - n, hop):
    S = np.abs(np.fft.rfft(seg[i:i + n] * np.hanning(n))); fr = np.fft.rfftfreq(n, 1 / sr); S[fr < 60] = 0
    e = 20 * np.log10(np.sqrt((seg[i:i + n] ** 2).mean()) + 1e-9); pk = []
    for j in np.argsort(S)[::-1]:
        if all(abs(fr[j] - p) > 30 for p in pk) and S[j] > S.max() * 0.25: pk.append(fr[j])
        if len(pk) >= 4: break
    out.append(f"  {a + i / sr:8.2f} {e:6.1f} dB  " + '  '.join(f"{p:6.0f} {nm(p)}" for p in pk))
open(os.path.join(mf.SP, 'out', 'bandtrace.txt'), 'a').write('\n'.join(out) + '\n'); print('\n'.join(out[:3]), '...')
