"""Describe each v552 cue heard in S1-L50-win-seq-2-continue (the only phone clip with sound besides the Play click):
per window: level, length, centroid, strongest partials at start / middle / end (glides), tick periodicity.
-> out/phone_cues.txt"""
import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
REF = os.path.join(mf.SP, '..', 'sound-refs')
w = wave.open(os.path.join(REF, 'phone_S1-L50-win-seq-2-continue.wav')); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
def nm(fq):
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    m = 69 + 12 * np.log2(fq / 440.0); k = int(round(m)); return f"{names[k % 12]}{k // 12 - 1}{int(round((m - k) * 100)):+d}c"
def peaks(seg, k=5, rel=0.15, n=8192):
    if len(seg) < 256: return [], 0
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n)); f = np.fft.rfftfreq(n, 1 / sr); S[f < 60] = 0
    out = []
    for j in np.argsort(S)[::-1]:
        if all(abs(f[j] - p) > 25 for p, a in out) and S[j] > S.max() * rel: out.append((f[j], 20 * np.log10(S[j] / S.max())))
        if len(out) >= k: break
    return out, float((f * S).sum() / (S.sum() + 1e-9))
WIN = [
 ('A  claw token appears (+1 hex pop, dim)', 0.15, 0.78),
 ('B  x25 badge merges into the token', 0.78, 1.45),
 ('C  claw bar count-up ticks (156->181)', 1.88, 2.27),
 ('D  after the count-up (low glide)', 2.27, 2.75),
 ('E  streak strip: x100 lights (1st low pop)', 3.02, 3.18),
 ('F  2nd low pop', 3.20, 3.36),
 ('G  3rd low pop / x100 badge flash', 3.42, 3.58),
 ('H  coin cue swell (glitter)', 3.18, 4.27),
 ('I  coin clinks at the pill', 4.27, 4.71),
]
lines = []
for name, a, b in WIN:
    seg = x[int(a * sr):int(b * sr)]
    hop = int(0.005 * sr); n = len(seg) // hop
    env = 20 * np.log10(np.sqrt((seg[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    pk = env.max(); ip = int(np.argmax(env)); above = np.where(env > pk - 20)[0]
    on = np.where(env > pk - 30)[0]
    lines.append(f'== {name}: window {a:.2f}-{b:.2f}s; onset {a + on[0]*0.005:.3f}s, peak {20*np.log10(np.abs(seg).max()+1e-9):.1f} dBFS (RMS-peak {pk:.1f} dB at {a+ip*0.005:.3f}s), >-20 dB span {(above[-1]-above[0]+1)*5} ms')
    for lab, s0, s1 in (('start', 0, 0.06), ('mid', 0.4, 0.5), ('end', 0.8, 0.9)):
        L = len(seg); ss = seg[int(s0 * L):int(s0 * L) + max(int(0.06 * sr), int((s1 - s0) * L))]
        pp, cen = peaks(ss)
        lines.append(f'     {lab:5s} cen {cen:6.0f} Hz  ' + '  '.join(f'{f:6.0f} {nm(f)} ({d:.0f})' for f, d in pp))
    if name.startswith('C') or name.startswith('I'):
        # tick onsets inside
        e = env; ons = [a + i * 0.005 for i in range(3, len(e)) if e[i] - e[i - 3] > 4 and e[i] >= e[i - 1] and e[i] > pk - 12]
        ded = []
        for o in ons:
            if not ded or o - ded[-1] > 0.025: ded.append(o)
        lines.append('     tick onsets: ' + ' '.join(f'{o:.3f}' for o in ded) + (f'  (mean period {np.diff(ded).mean()*1000:.1f} ms)' if len(ded) > 2 else ''))
        # per-tick pitch
        pts = []
        for o in ded:
            pp, cen = peaks(x[int(o * sr):int((o + 0.03) * sr)], k=1)
            if pp: pts.append(f'{pp[0][0]:.0f}')
        lines.append('     per-tick strongest partial Hz: ' + ' '.join(pts))
open(os.path.join(mf.SP, 'out', 'phone_cues.txt'), 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines))
