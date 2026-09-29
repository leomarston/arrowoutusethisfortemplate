"""Per-cue sound analysis from the owner's videos (event-locked). For each cue class: aligned onsets, median envelope
(5 ms), attack/decay, the strongest partials over time (50 ms frames) and a median spectrogram image in ../motion-frames/.
out/cues.txt"""
import sys, os, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
from PIL import Image
SR = 44100
def load(f):
    w = wave.open(os.path.join(mf.SP, '..', 'sound-refs', f)); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return x
XA = load('YT1-L01-20-full.wav'); XB = load('YT2-L11-38-full.wav')
def parse(key):
    out = []
    for l in open(os.path.join(mf.SP, 'out', f'sound_inv_{key}.txt')):
        p = l.split(); out.append((float(p[0]), float(p[2]), float(p[4])))
    return out
A = parse('A'); B = parse('B')
CLASSES = {
  'click (UI button)':      [('A', t) for t, L, pk in A if L < 0.06] + [('B', t) for t, L, pk in B if L < 0.06],
  'coin collect A (home)':  [('A', t) for t, L, pk in A if 2.5 < L < 3.0],
  'coin collect B (home)':  [('B', t) for t, L, pk in B if 1.3 < L < 1.8 and pk > -30],
  'win jingle B':           [('B', t) for t, L, pk in B if 4.4 < L < 4.8],
  'unlock chime B':         [('B', t) for t, L, pk in B if 1.9 < L < 2.2],
  'pre-level whoosh B':     [('B', t) for t, L, pk in B if 0.15 < L < 0.3],
}
def refine(x, t):
    a = int((t - 0.02) * SR); seg = x[a:a + int(0.06 * SR)]
    env = np.abs(seg); k = np.argmax(env > 0.02 * env.max() + 1e-6)
    return (a + k) / SR
def stft(seg, n=2048, hop=512):
    win = np.hanning(n); fr = []
    for i in range(0, max(1, len(seg) - n), hop): fr.append(np.abs(np.fft.rfft(seg[i:i + n] * win)))
    return np.array(fr)
def nm(fq):
    if fq <= 0: return '-'
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    m = 69 + 12 * np.log2(fq / 440.0); k = int(round(m)); c = int(round((m - k) * 100))
    return f"{names[k % 12]}{k // 12 - 1}{c:+d}c"
lines = []
for name, evs in CLASSES.items():
    if not evs: continue
    L = {'click (UI button)': 0.08, 'coin collect A (home)': 3.0, 'coin collect B (home)': 1.9, 'win jingle B': 4.9, 'unlock chime B': 2.3, 'pre-level whoosh B': 0.35}[name]
    segs = []
    for key, t in evs:
        x = XA if key == 'A' else XB
        t0 = refine(x, t); segs.append(x[int(t0 * SR):int(t0 * SR) + int(L * SR)])
    n = min(len(s) for s in segs); S = np.stack([s[:n] for s in segs])
    # identical copies? correlation of each to the first
    corr = [float(np.corrcoef(S[0], s)[0, 1]) for s in S[1:6]]
    med = np.median(S, 0)
    hop = int(0.005 * SR); m = n // hop
    env = 20 * np.log10(np.sqrt((med[:m * hop].reshape(m, hop) ** 2).mean(1)) + 1e-9)
    pk = env.max(); ipk = int(np.argmax(env))
    above = np.where(env > pk - 20)[0]; len20 = (above[-1] + 1) * 0.005 if len(above) else 0
    above40 = np.where(env > pk - 40)[0]; len40 = (above40[-1] + 1) * 0.005 if len(above40) else 0
    lines.append(f"== {name}: n={len(evs)}  corr(first vs next 5) {[round(c, 3) for c in corr]}")
    lines.append(f"   peak {20*np.log10(np.abs(med).max()+1e-9):.1f} dBFS (median of aligned copies), RMS-peak at {ipk*5} ms, length above -20 dB {len20*1000:.0f} ms, above -40 dB {len40*1000:.0f} ms")
    lines.append('   envelope dB every 25 ms: ' + ' '.join(f"{v:.0f}" for v in env[::5][:80]))
    F = stft(med); f = np.fft.rfftfreq(2048, 1 / SR)
    for i in range(0, len(F), max(1, len(F) // 24)):
        row = F[i].copy(); row[f < 60] = 0
        idx = np.argsort(row)[::-1]; peaks = []
        for j in idx:
            if all(abs(f[j] - p) > 25 for p in peaks) and row[j] > row.max() * 0.2: peaks.append(f[j])
            if len(peaks) >= 4: break
        if row.max() < 1e-3: continue
        lines.append(f"   t={i*512/SR*1000:6.0f} ms  " + '  '.join(f"{p:7.1f} Hz {nm(p)}" for p in peaks))
    # spectrogram image
    Fi = 20 * np.log10(F.T[f <= 12000] + 1e-6); Fi = np.clip((Fi - (Fi.max() - 70)) / 70, 0, 1)
    im = Image.fromarray((255 * (1 - Fi[::-1])).astype(np.uint8)).resize((max(200, int(n / SR * 400)), 300))
    im.save(os.path.join(mf.SP, '..', 'motion-frames', 'spec_' + name.split(' (')[0].replace(' ', '_') + '.png'))
open(os.path.join(mf.SP, 'out', 'cues.txt'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
