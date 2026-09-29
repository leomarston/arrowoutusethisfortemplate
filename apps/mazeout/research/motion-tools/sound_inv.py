"""Sound inventory of the owner's gameplay videos (the phone captures are digital silence).
For every non-silent segment: refined onset (1 ms), length above -40 dBFS, peak, centroid, top spectral peaks,
and a 25 ms pitch track (strongest partial). Output: out/sound_inv_{A,B}.txt; frames at each onset -> motion-frames/snd_{key}.jpg"""
import sys, os, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf, yt
from PIL import Image

def load(key):
    f = {'A': 'YT1-L01-20-full.wav', 'B': 'YT2-L11-38-full.wav'}[key]
    w = wave.open(os.path.join(mf.SP, '..', 'sound-refs', f))
    sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return sr, x

def segments(x, sr, thr=-60, join=0.15):
    hop = int(sr * 0.001); m = len(x) // hop
    e = 20 * np.log10(np.sqrt((x[:m * hop].reshape(m, hop) ** 2).mean(1)) + 1e-9)
    act = np.where(e > thr)[0]
    segs = []
    if len(act) == 0: return segs, e
    a = act[0]; b = act[0]
    for i in act[1:]:
        if (i - b) * hop / sr > join:
            segs.append((a, b)); a = i
        b = i
    segs.append((a, b))
    return [(a * hop / sr, (b + 1) * hop / sr) for a, b in segs], e

def pitch_track(seg, sr, win=0.025):
    n = int(sr * win); out = []
    for i in range(0, len(seg) - n, n):
        s = seg[i:i + n] * np.hanning(n)
        if np.sqrt((s ** 2).mean()) < 1e-3: out.append(0); continue
        S = np.abs(np.fft.rfft(s, 8192)); f = np.fft.rfftfreq(8192, 1 / sr)
        S[f < 80] = 0
        out.append(int(f[np.argmax(S)]))
    return out

def note(fq):
    if fq <= 0: return '-'
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    m = 69 + 12 * np.log2(fq / 440.0); k = int(round(m))
    return f"{names[k % 12]}{k // 12 - 1}{'+' if m - k > 0.25 else '-' if m - k < -0.25 else ''}"

if __name__ == '__main__':
    key = sys.argv[1]
    sr, x = load(key)
    segs, e = segments(x, sr)
    lines = []
    for (a, b) in segs:
        seg = x[int(a * sr):int(b * sr)]
        pk = 20 * np.log10(np.abs(seg).max() + 1e-9)
        d = mf.describe(x, sr, a, dur=min(b - a + 0.02, 6))
        pt = pitch_track(seg, sr)
        pts = ' '.join(note(p) for p in pt[:40])
        lines.append(f"{a:9.3f} len {b - a:6.3f} peak {pk:6.1f} dBFS cen {d.get('centroid_hz')} Hz peaks {d.get('peaks_hz')} | {pts}")
    open(os.path.join(mf.SP, 'out', f'sound_inv_{key}.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
