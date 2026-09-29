"""Phone (v552) audio: which clips carry sound, the onsets, per-cue partials, and a comparison with the owner-video cues.
Usage: phone_audio.py  -> out/phone_audio.txt, ../sound-refs/phone_*.wav, ../motion-frames/spec_phone_*.png
Times are MOVIE time (edit list applied) = the same clock as mf.raw() video frames."""
import os, sys, wave, glob, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
from PIL import Image
SR_OUT = 48000
REF = os.path.join(mf.SP, '..', 'sound-refs')
lines = []
def P(s):
    print(s); lines.append(s)
def nm(fq):
    if fq <= 0: return '-'
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    m = 69 + 12 * np.log2(fq / 440.0); k = int(round(m)); c = int(round((m - k) * 100))
    return f"{names[k % 12]}{k // 12 - 1}{c:+d}c"
def load(path):
    w = wave.open(path); sr = w.getframerate()
    return sr, np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
def env(x, sr, ms=5):
    hop = int(sr * ms / 1000); n = len(x) // hop
    return 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
def partials(seg, sr, n=4096, k=4, rel=0.2):
    if len(seg) < n: seg = np.pad(seg, (0, n - len(seg)))
    S = np.abs(np.fft.rfft(seg[:n] * np.hanning(n))); f = np.fft.rfftfreq(n, 1 / sr); S[f < 50] = 0
    pk = []
    for j in np.argsort(S)[::-1]:
        if all(abs(f[j] - p) > 30 for p in pk) and S[j] > S.max() * rel: pk.append(f[j])
        if len(pk) >= k: break
    cen = float((f * S).sum() / (S.sum() + 1e-9))
    return pk, cen
clips = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(mf.V, '*.mov')))
P('== audio presence per clip (movie time; 0 = digital zero)')
live = []
for c in clips:
    out = os.path.join(REF, f'phone_{c}.wav')
    if not os.path.exists(out):
        subprocess.run([mf.MFX, 'audio', os.path.join(mf.V, c + '.mov'), out], capture_output=True, timeout=120)
    if not os.path.exists(out):
        P(f'  {c}: no audio track'); continue
    sr, x = load(out)
    nz = np.nonzero(x)[0]
    if len(nz) == 0:
        P(f'  {c}: {len(x)/sr:.2f} s, all zero'); os.remove(out); continue
    P(f'  {c}: {len(x)/sr:.2f} s, peak {20*np.log10(np.abs(x).max()):.1f} dBFS, non-zero {nz[0]/sr:.3f}..{nz[-1]/sr:.3f} s, clipped samples {int((np.abs(x) > 0.999).sum())}')
    live.append((c, sr, x))
for c, sr, x in live:
    P(f'\n== {c}: 20 ms envelope (dBFS), onsets, 50 ms partial trace')
    e = env(x, sr, 20)
    P('  env20: ' + ' '.join(f'{v:.0f}' if v > -100 else '.' for v in e))
    ons = mf.onsets(x, sr, hop_ms=5, rise_db=9, floor_db=-60, min_gap=0.04)
    P('  onsets: ' + ', '.join(f'{t:.3f}({pk:.0f})' for t, pk in ons))
    hop = int(0.05 * sr)
    for i in range(0, len(x) - 2048, hop):
        seg = x[i:i + 2048]
        lev = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9)
        if lev < -60: continue
        pk, cen = partials(x[i:i + 4096], sr, n=4096)
        P(f'  {i/sr:6.2f} {lev:6.1f} dB cen {cen:5.0f}  ' + '  '.join(f'{p:6.0f} {nm(p)}' for p in pk))
    # spectrogram image
    n = 2048; hp = 256; win = np.hanning(n)
    F = np.array([np.abs(np.fft.rfft(x[i:i + n] * win)) for i in range(0, len(x) - n, hp)]).T
    f = np.fft.rfftfreq(n, 1 / sr)
    Fi = 20 * np.log10(F[f <= 12000] + 1e-6); Fi = np.clip((Fi - (Fi.max() - 70)) / 70, 0, 1)
    Image.fromarray((255 * (1 - Fi[::-1])).astype(np.uint8)).resize((max(200, int(len(x) / sr * 300)), 300)).save(
        os.path.join(mf.SP, '..', 'motion-frames', f'spec_phone_{c}.png'))
open(os.path.join(mf.SP, 'out', 'phone_audio.txt'), 'w').write('\n'.join(lines) + '\n')
