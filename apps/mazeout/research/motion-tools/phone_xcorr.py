"""Match phone (v552) audio against reference cues: the v552 Play click (S1-L48-play-intro) and the owner-video cues
(YT-A click/coin, YT-B unlock) -> where each cue occurs in S1-L50-win-seq-2-continue (normalised cross-correlation,
envelope-free). -> out/phone_xcorr.txt"""
import os, sys, wave
import numpy as np
from scipy.signal import resample_poly, correlate
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
REF = os.path.join(mf.SP, '..', 'sound-refs')
def load(f):
    w = wave.open(os.path.join(REF, f)); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if sr != 48000: x = resample_poly(x, 480, sr // 100).astype(np.float32)
    return x
X = load('phone_S1-L50-win-seq-2-continue.wav')
P1 = load('phone_S1-L48-play-intro.wav'); P2 = load('phone_S1-L49-play-intro-superhard.wav')
nz = np.nonzero(P1)[0]; click = P1[nz[0]:nz[-1] + 1]
nz2 = np.nonzero(P2)[0]; click2 = P2[nz2[0]:nz2[-1] + 1]
lines = [f'v552 Play click: {len(click)/48000*1000:.1f} ms, peak {20*np.log10(np.abs(click).max()):.1f} dBFS; click(L48) vs click(L49) corr {np.corrcoef(click[:min(len(click),len(click2))], click2[:min(len(click),len(click2))])[0,1]:.3f}']
yta_click = load('cue_click_YTA_27.12.wav')
# align the YT-A click with the phone click by max xcorr
c = correlate(yta_click, click, mode='full'); k = np.argmax(np.abs(c)) - (len(click) - 1)
seg = yta_click[max(k, 0):max(k, 0) + len(click)]
if len(seg) == len(click):
    lines.append(f'YT-A click vs v552 click: corr {np.corrcoef(seg, click)[0,1]:.3f} (after alignment, 48 kHz)')
def ncc_scan(x, tpl, name, thr=0.5):
    tpl = tpl - tpl.mean(); n = len(tpl); e = np.sqrt((tpl ** 2).sum())
    c = correlate(x, tpl, mode='valid')
    x2 = np.concatenate([[0], np.cumsum(x.astype(np.float64) ** 2)]); en = np.sqrt(x2[n:] - x2[:-n] + 1e-12)
    ncc = c / (e * en + 1e-9)
    hits = []; i = 0
    while i < len(ncc):
        if ncc[i] > thr:
            j = i + int(np.argmax(ncc[i:i + 2400])); hits.append((j / 48000, ncc[j])); i = j + 2400
        else: i += 1
    lines.append(f'{name} (len {n/48000*1000:.0f} ms) hits NCC>{thr}: ' + ', '.join(f'{a:.3f}s ({b:.2f})' for a, b in hits))
ncc_scan(X, click, 'v552 click in win-seq-2')
coin = load('cue_coin_YTA_94.52.wav')
# the YT-A coin cue's clink part (1.0-1.5 s of the cue) as template
ncc_scan(X, coin[int(1.00 * 48000):int(1.45 * 48000)], 'YT-A coin clinks (cue 1.00-1.45 s)', 0.3)
ncc_scan(X, coin[int(0.00 * 48000):int(0.9 * 48000)], 'YT-A coin swell (cue 0-0.9 s)', 0.3)
unl = load('cue_unlock_YTB_75.80.wav')
ncc_scan(X, unl[:int(1.0 * 48000)], 'YT-B unlock chime (first 1 s)', 0.3)
open(os.path.join(mf.SP, 'out', 'phone_xcorr.txt'), 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines))
