#!/usr/bin/env python3
"""T9 AUDIO-2 gate helper: our cues next to v552's event-locked medians. COMPARISON ONLY, never derivation.

It reads the reference captures in research/sound-refs (the phone's v552 home-return clip, the phone Play click, the
owner's two videos) only to MEASURE them, next to the same measurements of our rendered files; nothing it reads is
written into any sound or tool (the outputs are numbers and pictures under build/p/T9/compare, gitignored evidence).
It lives outside tools/audio* on purpose: the audio kit's provenance scan forbids any reference to research/ there.

Per cue (research/sounds.md §2 event times; research/motion-tools/out/sound_inv_{A,B}.txt segment inventories):
  - event-locked reference: every copy aligned on its onset (first sample over 2 % of the local max, as cues.py),
    then the per-sample MEDIAN of the aligned copies (n = copies; n = 1 where v552 played the cue once on the phone);
  - octave bands 63 Hz - 16 kHz: energy over the cue window (STFT power summed over time), dB re the strongest band. PASS when every band that
    either side has within 20 dB of its strongest band differs by <= 3 dB;
  - envelope (RMS, 5 ms window, 1 ms hop, power smoothed over min(25 ms, 5 % of the window)): attack = onset (first
    frame within 30 dB of the max) -> the first frame within 1 dB of the max, decay = from there to the last frame
    within 20 dB of the max. PASS when both are within +-20 ms. coinCollect uses band envelopes
    instead (coin_env_metrics: the glitter swell's rise and the G7 ring's 20 dB fall after the last clink);
  - a side-by-side spectrogram (log frequency 60 Hz - 16 kHz, 70 dB range re each side's peak) with both envelopes.

    python3 design/publish/tools/audio_v552_compare.py [--ours build/p/T9/wav] [--old App/Resources/Sounds]
                                                        [--out build/p/T9/compare]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import wave

import numpy as np
from PIL import Image, ImageDraw

APP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
REFS = os.path.join(APP, "research", "sound-refs")
INV = os.path.join(APP, "research", "motion-tools", "out")
PHONE_SEQ = "phone_S1-L50-win-seq-2-continue.wav"     # v552: Continue -> home -> the whole home-return sequence
PHONE_PLAY = "phone_S1-L48-play-intro.wav"            # v552: the Play-button click
BANDS = [63.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0]


def read(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def read_window(path: str, t0: float, dur: float) -> tuple[np.ndarray, int]:
    """Only [t0, t0 + dur) of a (long) capture: the videos are ~2,200 s, never loaded whole."""
    with wave.open(path, "rb") as w:
        ch, sr, n = w.getnchannels(), w.getframerate(), w.getnframes()
        a = max(0, int(round(t0 * sr)))
        w.setpos(min(a, n))
        raw = w.readframes(max(0, min(int(round(dur * sr)), n - a)))
    x = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def onset_in(x: np.ndarray, sr: int, pre: float) -> int:
    """cues.py's alignment: in the 60 ms from `pre` s before the nominal time, the first sample over 2 % of the max."""
    a = max(0, int((pre - 0.02) * sr))
    seg = np.abs(x[a:a + int(0.06 * sr)])
    return a + int(np.argmax(seg > 0.02 * seg.max() + 1e-9))


def inventory(key: str) -> list[tuple[float, float, float]]:
    out = []
    for line in open(os.path.join(INV, f"sound_inv_{key}.txt"), encoding="utf-8"):
        p = line.split()
        out.append((float(p[0]), float(p[2]), float(p[4])))
    return out


def median_of(path: str, times: list[float], length: float, refine_on: bool = True
              ) -> tuple[np.ndarray, int, int, np.ndarray]:
    """Event-locked median: each copy read around its time, aligned on its onset, then the per-sample median. Also the
    median of the 40 ms that end 5 ms before each onset (the background: earlier cues still ringing, capture noise)."""
    segs, bgs, sr = [], [], 44100
    pre = 0.06
    for t in times:
        x, sr = read_window(path, t - pre, length + 0.2)
        k = onset_in(x, sr, pre) if refine_on else int(round(pre * sr))
        s = x[k:k + int(round(length * sr))]
        b = x[max(0, k - int(0.045 * sr)):k - int(0.005 * sr)]
        if len(s) == int(round(length * sr)):
            segs.append(s)
            bgs.append(b)
    nb = min(len(b) for b in bgs)
    return np.median(np.stack(segs), axis=0), sr, len(segs), np.median(np.stack([b[-nb:] for b in bgs]), axis=0)


def references() -> dict[str, dict]:
    seq = os.path.join(REFS, PHONE_SEQ)
    ya, yb = os.path.join(REFS, "YT1-L01-20-full.wav"), os.path.join(REFS, "YT2-L11-38-full.wav")
    A, B = inventory("A"), inventory("B")
    refs: dict[str, dict] = {}

    def put(sid, res, src, **kw):
        m, sr, n, bg = res
        refs[sid] = {"sig": m, "sr": sr, "n": n, "bg": bg, "src": src, **kw}

    # the click: the phone's Play click (v552; digital silence before it) + the video copies (= the v552 click)
    play, psr = read(os.path.join(REFS, PHONE_PLAY))
    k = int(np.argmax(np.abs(play) > 0.02 * np.max(np.abs(play))))
    put("uiClick", median_of(os.path.join(REFS, PHONE_PLAY), [k / psr], 0.035, refine_on=False),
        "v552 phone Play click")
    m, sr, n, bg = median_of(ya, [t for t, L, pk in A if L < 0.06], 0.035)
    refs["uiClick"]["alt"] = {"sig": m, "sr": sr, "n": n, "bg": bg, "src": "owner video A click median"}
    # the v552 home-return sequence on the phone: research/sounds.md §2.1 / phone_cues onsets (measured there; no
    # re-alignment, which would trigger on the previous cues' tails), windows cut before the next cue
    put("clawToken", median_of(seq, [0.225], 0.55, refine_on=False), "v552 phone, onset 0.225 s (to the merge)")
    put("clawMerge", median_of(seq, [0.805], 1.07, refine_on=False), "v552 phone, onset 0.805 s (to the ticks)")
    put("clawTick", median_of(seq, [1.910, 1.955, 2.020, 2.085, 2.125, 2.170, 2.250], 0.040, refine_on=False),
        "v552 phone, median of the 7 count-up ticks")
    put("clawComplete", median_of(seq, [2.270], 0.16, refine_on=False), "v552 phone, onset 2.270 s")
    put("streakPop", median_of(seq, [3.050], 0.13, refine_on=False),
        "v552 phone, pop 1 at 3.050 s (pops 2-3 overlap the coin cue)")
    put("coinCollect", median_of(ya, [t for t, L, pk in A if 2.5 < L < 3.0], 2.9),
        "owner video A coin cue median (= the v552 cue)")
    put("unlockChime", median_of(yb, [t for t, L, pk in B if 1.9 < L < 2.2], 2.2),
        "owner video B unlock median (not met on the phone)")
    return refs


def envelope(x: np.ndarray, sr: int, win: float = 0.005, hop: float = 0.001) -> tuple[np.ndarray, float]:
    W, H = max(1, int(win * sr)), max(1, int(hop * sr))
    pad = np.concatenate([x, np.zeros(W)])
    m = max(1, (len(x)) // H)
    e = np.array([math.sqrt(float(np.mean(pad[i * H:i * H + W] ** 2))) for i in range(m)])
    return 20 * np.log10(e + 1e-9), hop


def env_metrics(x: np.ndarray, sr: int) -> dict:
    """Envelope = 5 ms RMS at a 1 ms hop, its power smoothed over min(25 ms, 5 % of the window) so a plateau's grain or
    beating does not decide where 'the peak' is. onset = the first frame within 30 dB of the max; top = the first frame
    within 1 dB of the max; attack = onset -> top; decay = top -> the last frame within 20 dB of the max."""
    e, hop = envelope(x, sr)
    k = max(1, int(min(0.025, 0.05 * len(x) / sr) / hop))
    if k > 1:
        e = 10 * np.log10(np.convolve(10 ** (e / 10), np.ones(k) / k, mode="same") + 1e-18)
    pk = float(np.max(e))
    i0 = int(np.argmax(e >= pk - 30.0))
    it = int(np.argmax(e >= pk - 1.0))
    above = np.nonzero(e >= pk - 20.0)[0]
    i20 = int(above[-1]) if len(above) else it
    return {"attack_ms": round((it - i0) * hop * 1000, 1), "decay_ms": round((i20 - it) * hop * 1000, 1),
            "span20_ms": round((i20 - i0 + 1) * hop * 1000, 1), "smooth_ms": k,
            "peak_dbfs": round(20 * math.log10(np.max(np.abs(x)) + 1e-9), 2)}


def band_env(x: np.ndarray, sr: int, lo: float, hi: float, smooth: float = 0.0) -> np.ndarray:
    """dB envelope (5 ms RMS, 1 ms hop) of one band (FFT brick mask); `smooth` s = a moving average of the power first."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    X[(f < lo) | (f > hi)] = 0.0
    e = envelope(np.fft.irfft(X, len(x)), sr)[0]
    if smooth > 0:
        k = max(1, int(smooth / 0.001))
        p = np.convolve(10 ** (e / 10), np.ones(k) / k, mode="same")
        e = 10 * np.log10(p + 1e-18)
    return e


def coin_env_metrics(x: np.ndarray, sr: int) -> dict:
    """coinCollect only: its generic peak is ambiguous (5 near-equal clinks) and the 13-copy video median smears the
    clink train, so: attack = the glitter swell's rise (5.5-8 kHz band, from 30 dB under to 3 dB under its level before
    1.0 s), decay = the G7 ring's fall after the last clink (2.9-3.4 kHz band, from its last maximum after 1.3 s to
    20 dB under it)."""
    g = band_env(x, sr, 5500.0, 8000.0, smooth=0.025)          # the swell, not its individual grains
    top = float(np.max(g[:1000]))
    i0 = int(np.argmax(g >= top - 30.0))
    i1 = int(np.argmax(g >= top - 3.0))
    r = band_env(x, sr, 2900.0, 3400.0)
    j = 1300 + int(np.argmax(r[1300:1700]))
    below = np.nonzero(r[j:] < r[j] - 20.0)[0]
    k = j + (int(below[0]) if len(below) else len(r) - j)
    return {"attack_ms": float(i1 - i0), "decay_ms": float(k - j), "span20_ms": float(k - i0),
            "peak_dbfs": round(20 * math.log10(np.max(np.abs(x)) + 1e-9), 2),
            "metric": "coin: glitter-swell rise / G7 ring 20 dB fall after the last clink"}


def band_powers(x: np.ndarray, sr: int) -> list[float]:
    """Energy per octave band summed over time: an STFT (Hann 10 ms, hop 2.5 ms, the signal padded by one frame on
    both sides so the onset counts fully), power summed per band over every frame, per second of signal."""
    win = max(64, int(0.010 * sr))
    hop = max(16, win // 4)
    pad = np.concatenate([np.zeros(win), x, np.zeros(win)])
    frames = 1 + (len(pad) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(frames)[:, None]
    nfft = 1 << int(math.ceil(math.log2(win * 4)))
    P = (np.abs(np.fft.rfft(pad[idx] * np.hanning(win), nfft, axis=1)) ** 2).sum(axis=0) * hop / sr
    f = np.fft.rfftfreq(nfft, 1.0 / sr)
    out = []
    for fc in BANDS:
        m = (f >= fc / math.sqrt(2)) & (f < fc * math.sqrt(2))
        out.append(float(np.sum(P[m])) / (len(x) / sr) if np.any(m) else 0.0)
    return out


def band_levels(x: np.ndarray, sr: int) -> list[float]:
    """dB re the strongest octave band."""
    out = band_powers(x, sr)
    top = max(out) or 1.0
    return [round(10 * math.log10(v / top + 1e-12), 1) for v in out]


def compare(ours: np.ndarray, osr: int, ref: np.ndarray, rsr: int, bg: np.ndarray | None = None,
            coin: bool = False) -> dict:
    """Bands: the reference's band powers minus its background (the 40 ms before onset), dB re its strongest band. A band
    counts (is 'primary') when either side has it within 20 dB of its strongest band AND the reference cue rises >= 6 dB
    above the reference background there (else the reference band is another cue's tail or noise)."""
    bo = band_levels(ours, osr)
    pr = band_powers(ref, rsr)
    pb = band_powers(bg, rsr) if bg is not None and len(bg) > 16 else [0.0] * len(BANDS)
    # the reference cue's own band power = its window minus the background (earlier cues' tails, capture noise)
    own = [max(c - d0, 1e-3 * c, 1e-30) for c, d0 in zip(pr, pb)]
    top = max(own)
    br = [round(10 * math.log10(v / top), 1) for v in own]
    rows, worst = [], 0.0
    for fc, a, b, c, d0 in zip(BANDS, bo, br, pr, pb):
        snr = 99.0 if d0 <= 0 else round(10 * math.log10(c / d0 + 1e-12), 1)
        primary = (a >= -20.0 or b >= -20.0) and snr >= 6.0
        d = round(a - b, 1)
        rows.append({"band_hz": fc, "ours_db": a, "v552_db": b, "delta_db": d, "ref_snr_db": min(snr, 99.0),
                     "primary": primary})
        if primary:
            worst = max(worst, abs(d))
    em = coin_env_metrics if coin else env_metrics
    eo, er = em(ours, osr), em(ref, rsr)
    da, dd = eo["attack_ms"] - er["attack_ms"], eo["decay_ms"] - er["decay_ms"]
    return {"bands": rows, "worst_primary_band_delta_db": round(worst, 1), "bands_pass": worst <= 3.0,
            "env_ours": eo, "env_v552": er, "attack_delta_ms": round(da, 1), "decay_delta_ms": round(dd, 1),
            "env_pass": abs(da) <= 20.0 and abs(dd) <= 20.0}


# ---------------------------------------------------------------------------------------------------------------------
# pictures

_ANCHORS = np.array([[0.00, 0, 0, 4], [0.15, 28, 16, 68], [0.30, 79, 18, 123], [0.45, 129, 37, 129],
                     [0.60, 181, 54, 122], [0.72, 229, 80, 100], [0.84, 251, 135, 97], [0.93, 254, 194, 135],
                     [1.00, 252, 253, 191]])


def spec_img(x: np.ndarray, sr: int, width: int, height: int, dur: float) -> Image.Image:
    x = np.concatenate([x, np.zeros(max(0, int(dur * sr) - len(x)))])[:int(dur * sr)]
    win = 1024 if dur > 0.3 else 256
    hop = max(8, (len(x) - win) // width) if len(x) > win else 8
    pad = np.concatenate([np.zeros(win // 2), x, np.zeros(win)])
    frames = 1 + (len(pad) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(frames)[:, None]
    S = np.abs(np.fft.rfft(pad[idx] * np.hanning(win), axis=1))
    db = 20 * np.log10(S + 1e-9)
    db -= db.max()
    f = np.fft.rfftfreq(win, 1.0 / sr)
    rows = np.geomspace(16000.0, 60.0, height)
    img = np.stack([np.interp(rows, f, db[j]) for j in range(frames)], axis=1)
    cols = np.linspace(0, frames - 1, width)
    img = np.stack([np.interp(cols, np.arange(frames), img[r]) for r in range(height)])
    v = np.clip((img + 70.0) / 70.0, 0, 1)
    rgb = np.stack([np.interp(v, _ANCHORS[:, 0], _ANCHORS[:, c + 1]) for c in range(3)], axis=-1).astype(np.uint8)
    im = Image.fromarray(rgb)
    d = ImageDraw.Draw(im)
    for fr in (100, 250, 500, 1000, 2000, 4000, 8000):
        yy = int(np.argmin(np.abs(rows - fr)))
        d.line([(0, yy), (6, yy)], fill=(120, 255, 120))
        d.text((8, yy - 6), f"{fr if fr < 1000 else str(fr // 1000) + 'k'}", fill=(120, 255, 120))
    # envelope overlay (0 .. -60 dB re peak)
    e, hop_s = envelope(x, sr)
    e = e - e.max()
    xs = np.linspace(0, width - 1, len(e))
    ys = np.clip(-e / 60.0, 0, 1) * (height - 1)
    d.line(list(zip(xs.tolist(), ys.tolist())), fill=(80, 200, 255), width=1)
    return im


def sheet(name: str, panels: list[tuple[str, np.ndarray, int]], dur: float, out: str) -> None:
    W, H = 420, 240
    ims = [spec_img(x, sr, W, H, dur) for _, x, sr in panels]
    canvas = Image.new("RGB", (len(ims) * (W + 10) + 10, H + 40), (250, 250, 247))
    d = ImageDraw.Draw(canvas)
    for i, (im, (label, _, _)) in enumerate(zip(ims, panels)):
        canvas.paste(im, (10 + i * (W + 10), 30))
        d.text((10 + i * (W + 10), 8), label, fill=(20, 20, 20))
    d.text((canvas.width - 190, 8), f"{name}  0-{dur * 1000:.0f} ms", fill=(90, 90, 90))
    canvas.save(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ours", default=os.path.join(APP, "build", "p", "T9", "wav"))
    ap.add_argument("--old", default=os.path.join(APP, "App", "Resources", "Sounds"))
    ap.add_argument("--out", default=os.path.join(APP, "build", "p", "T9", "compare"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    refs = references()
    report, lines = {}, []
    for sid, r in refs.items():
        ours, osr = read(os.path.join(a.ours, sid + ".wav"))
        L = min(len(ours) / osr, len(r["sig"]) / r["sr"])
        o, ref = ours[:int(L * osr)], r["sig"][:int(L * r["sr"])]
        c = compare(o, osr, ref, r["sr"], r.get("bg"), coin=sid == "coinCollect")
        entry = {"reference": r["src"], "n_copies": r["n"], "window_s": round(L, 3), "new": c}
        panels = [("OURS (T9 kit)", o, osr), (f"v552 ({r['src'][:44]}, n={r['n']})", ref, r["sr"])]
        oldp = os.path.join(a.old, sid + ".wav")
        if os.path.exists(oldp):
            old, oldsr = read(oldp)
            old = old[:int(L * oldsr)]
            entry["old"] = compare(old, oldsr, ref, r["sr"], r.get("bg"), coin=sid == "coinCollect")
            panels.insert(1, ("before (the sine recipes)", old, oldsr))
        if r.get("alt"):
            al = r["alt"]
            entry["alt_reference"] = {"src": al["src"], "n": al["n"],
                                      "new": compare(o, osr, al["sig"][:int(L * al["sr"])], al["sr"], al.get("bg"))}
        sheet(sid, panels, L, os.path.join(a.out, f"{sid}.png"))
        report[sid] = entry
        verdict = "PASS" if c["bands_pass"] and c["env_pass"] else "FAIL"
        lines.append(f"{sid:13} {verdict}  bands worst {c['worst_primary_band_delta_db']:4.1f} dB  attack "
                     f"{c['env_ours']['attack_ms']:6.1f} vs {c['env_v552']['attack_ms']:6.1f} ms ({c['attack_delta_ms']:+.1f})"
                     f"  decay {c['env_ours']['decay_ms']:6.1f} vs {c['env_v552']['decay_ms']:6.1f} ms "
                     f"({c['decay_delta_ms']:+.1f})   ref: {r['src']} n={r['n']}")
        lines.append("              bands " + "  ".join(f"{int(b['band_hz']) if b['band_hz'] < 1000 else str(int(b['band_hz'] // 1000)) + 'k'}:"
                                                  f"{b['ours_db']:+.0f}/{b['v552_db']:+.0f}{'*' if b['primary'] else ('~' if b['ref_snr_db'] < 6 else '')}"
                                                  for b in c["bands"]))
        if "old" in entry:
            oc = entry["old"]
            lines.append(f"              before: bands worst {oc['worst_primary_band_delta_db']:.1f} dB, attack "
                         f"{oc['attack_delta_ms']:+.1f} ms, decay {oc['decay_delta_ms']:+.1f} ms")
        if "alt_reference" in entry:
            ac = entry["alt_reference"]["new"]
            lines.append(f"              vs {entry['alt_reference']['src']} (n={entry['alt_reference']['n']}): bands worst "
                         f"{ac['worst_primary_band_delta_db']:.1f} dB, attack {ac['attack_delta_ms']:+.1f} ms, decay "
                         f"{ac['decay_delta_ms']:+.1f} ms")
    lines.append("tapTick       n/a (v552 plays no tap sound; the owner's option, unmapped)")
    json.dump(report, open(os.path.join(a.out, "compare.json"), "w"), indent=1)
    open(os.path.join(a.out, "compare.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
