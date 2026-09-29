#!/usr/bin/env python3
"""Spectrogram PNGs of our rendered sounds (log-frequency 30 Hz - 20 kHz, -96..0 dBFS) + a waveform strip.
Copied as-is from apps/matchfactory/tools/audio/spectro.py (05424db); only this line was added. Compare our picture
with the original's event-locked median spectrogram (research/motion-tools evavg.py) side by side: comparison, not
derivation (GAMEPROMPT §7.2 "Audio").

    python3 tools/audio/spectro.py OUT_DIR [wav ...]     # default: every Sounds/*.wav and Music/*.wav
    python3 tools/audio/spectro.py OUT_DIR --sheet       # also a contact sheet of all sounds
"""
from __future__ import annotations

import glob
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import dsp
import specs

# a magma-like ramp: black -> purple -> orange -> pale yellow
_ANCHORS = np.array([
    [0.00, 0, 0, 4], [0.15, 28, 16, 68], [0.30, 79, 18, 123], [0.45, 129, 37, 129], [0.60, 181, 54, 122],
    [0.72, 229, 80, 100], [0.84, 251, 135, 97], [0.93, 254, 194, 135], [1.00, 252, 253, 191]])


def colormap(v: np.ndarray) -> np.ndarray:
    v = np.clip(v, 0.0, 1.0)
    out = np.empty(v.shape + (3,), dtype=np.uint8)
    for c in range(3):
        out[..., c] = np.interp(v, _ANCHORS[:, 0], _ANCHORS[:, c + 1]).astype(np.uint8)
    return out


def spectrogram(x: np.ndarray, width: int, height: int, fmin: float = 30.0, fmax: float = 20000.0,
                floor_db: float = -96.0) -> np.ndarray:
    mono = x.mean(axis=1) if x.ndim == 2 else x
    n = len(mono)
    win = 2048 if n > dsp.SR * 3 else 1024
    hop = max(16, (n - win) // max(1, width - 1)) if n > win else 16
    pad = np.concatenate([np.zeros(win // 2), mono, np.zeros(win)])
    frames = 1 + (len(pad) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(frames)[:, None]
    w = np.hanning(win)
    spec = np.abs(np.fft.rfft(pad[idx] * w, axis=1)) / (np.sum(w) / 2)
    db = 20 * np.log10(spec + 1e-9)
    freqs = np.fft.rfftfreq(win, 1.0 / dsp.SR)
    # resample to a log-frequency axis (rows) and to `width` columns
    rows = np.geomspace(fmax, fmin, height)
    img = np.empty((height, frames))
    for j in range(frames):
        img[:, j] = np.interp(rows, freqs, db[j])
    cols = np.linspace(0, frames - 1, width)
    img2 = np.empty((height, width))
    for r in range(height):
        img2[r] = np.interp(cols, np.arange(frames), img[r])
    return (img2 - floor_db) / (-floor_db)


def render(path: str, out_png: str, title: str | None = None) -> str:
    x, sr, _ = dsp.read_wav(path)
    dur = len(x) / sr
    width = int(min(1400, max(420, dur * 900))) if dur < 5 else 1400
    sh, wh = 240, 56
    spec = spectrogram(x, width, sh)
    img = Image.new("RGB", (width + 44, sh + wh + 34), (18, 18, 22))
    img.paste(Image.fromarray(colormap(spec)), (44, 30))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    mono = x.mean(axis=1) if x.ndim == 2 else x
    peak = dsp.a2db(float(np.max(np.abs(mono))) if mono.size else 0)
    name = title or os.path.basename(path)
    d.text((6, 8), f"{name}   {dur:.3f} s   peak {dsp.a2db(float(np.max(np.abs(x)))):.1f} dBFS   "
                   f"rms {dsp.rms_db(x):.1f} dBFS", fill=(230, 230, 230), font=font)
    for f in (50, 100, 200, 500, 1000, 2000, 5000, 10000):
        y = 30 + int((math.log(20000 / f) / math.log(20000 / 30)) * (sh - 1))
        d.line([(40, y), (44, y)], fill=(200, 200, 200))
        d.text((2, y - 5), f"{f // 1000}k" if f >= 1000 else str(f), fill=(170, 170, 170), font=font)
    # waveform (peak per column)
    y0 = 30 + sh + 4
    cols = np.array_split(np.abs(mono), width)
    for i, c in enumerate(cols):
        v = float(np.max(c)) if len(c) else 0.0
        h = int(v * (wh - 6))
        d.line([(44 + i, y0 + wh // 2 - h // 2), (44 + i, y0 + wh // 2 + h // 2)], fill=(120, 190, 255))
    # time ticks
    step = 0.1 if dur <= 1.5 else (0.5 if dur <= 5 else 5.0)
    k = 0
    while k * step <= dur + 1e-9:
        xx = 44 + int(k * step / dur * (width - 1))
        d.line([(xx, y0 + wh - 2), (xx, y0 + wh + 2)], fill=(200, 200, 200))
        if k % (2 if dur <= 1.5 else 1) == 0:
            d.text((xx + 2, y0 + wh - 8), f"{k * step:g}", fill=(170, 170, 170), font=font)
        k += 1
    img.save(out_png)
    return out_png


def sheet(pngs: list[str], out_png: str, cols: int = 3) -> str:
    ims = [Image.open(p) for p in pngs]
    cw = max(i.width for i in ims)
    ch = max(i.height for i in ims)
    rows = math.ceil(len(ims) / cols)
    s = Image.new("RGB", (cols * cw, rows * ch), (10, 10, 12))
    for k, im in enumerate(ims):
        s.paste(im, ((k % cols) * cw, (k // cols) * ch))
    s.save(out_png)
    return out_png


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    out = argv[0]
    rest = [a for a in argv[1:] if not a.startswith("--")]
    os.makedirs(out, exist_ok=True)
    wavs = rest or sorted(glob.glob(os.path.join(specs.SOUNDS_DIR, "*.wav"))) + \
        sorted(glob.glob(os.path.join(specs.MUSIC_DIR, "*.wav")))
    pngs = []
    for w in wavs:
        pngs.append(render(w, os.path.join(out, os.path.splitext(os.path.basename(w))[0] + ".png")))
    if "--sheet" in argv:
        sfx_pngs = [p for p, w in zip(pngs, wavs) if os.sep + "Music" + os.sep not in w]
        sheet(sfx_pngs, os.path.join(out, "_sheet_sounds.png"))
    print(f"spectro.py: {len(pngs)} PNGs in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
