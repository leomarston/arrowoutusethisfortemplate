"""Helpers for motion analysis of phone recordings (393x852 pt screen)."""
import os, subprocess, wave, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SP = os.path.dirname(os.path.abspath(__file__))
MFX = os.path.join(SP, "mfx")
V = "/Users/yago/Downloads/app-factory/apps/mazeout/research/video"
W = os.path.join(SP, "w")
os.makedirs(W, exist_ok=True)


def raw(video, start=0, end=999, width=131, fps=240, crop=None, tag=None):
    tag = tag or f"{os.path.basename(video)}_{start}_{end}_{width}_{crop}".replace(" ", "")
    out = os.path.join(W, tag + ".bin")
    if not os.path.exists(out):
        cmd = [MFX, "raw", os.path.join(V, video), out, str(fps), str(start), str(end), str(width)]
        if crop:
            cmd += [str(c) for c in crop]
        subprocess.run(cmd, check=True, capture_output=True)
    d = open(out, "rb").read()
    h = np.frombuffer(d[:16], dtype=np.int32)
    w, hh, n = int(h[1]), int(h[2]), int(h[3])
    t = np.frombuffer(d[16:16 + 8 * n], dtype=np.float64).copy()
    px = np.frombuffer(d[16 + 8 * n:], dtype=np.uint8).reshape(n, hh, w, 3)
    os.remove(out)
    return t, px


def frames(video, outdir, start, end, width=393, fps=240, crop=None):
    cmd = [MFX, "frames", os.path.join(V, video), outdir, str(fps), str(start), str(end), str(width)]
    if crop:
        cmd += [str(c) for c in crop]
    subprocess.run(cmd, check=True, capture_output=True)
    fs = sorted(f for f in os.listdir(outdir) if f.endswith(".jpg"))
    return [os.path.join(outdir, f) for f in fs]


def sheet(paths_or_imgs, labels, out, cols=8, cell_w=None, pad=2, font_size=12):
    imgs = [Image.open(p) if isinstance(p, str) else p for p in paths_or_imgs]
    if cell_w:
        imgs = [im.resize((cell_w, int(im.height * cell_w / im.width)), Image.LANCZOS) for im in imgs]
    cw = max(i.width for i in imgs)
    ch = max(i.height for i in imgs)
    rows = (len(imgs) + cols - 1) // cols
    lab_h = font_size + 4
    S = Image.new("RGB", (cols * (cw + pad), rows * (ch + lab_h + pad)), (255, 255, 255))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", font_size)
    except Exception:
        font = ImageFont.load_default()
    d = ImageDraw.Draw(S)
    for k, (im, lab) in enumerate(zip(imgs, labels)):
        x = (k % cols) * (cw + pad)
        y = (k // cols) * (ch + lab_h + pad)
        d.text((x + 2, y), str(lab), fill=(200, 0, 0), font=font)
        S.paste(im, (x, y + lab_h))
    S.save(out, quality=88)
    return S.size


def audio(video, start=None, end=None, tag=None):
    tag = tag or f"{os.path.basename(video)}_{start}_{end}"
    out = os.path.join(W, tag + ".wav")
    if not os.path.exists(out):
        cmd = [MFX, "audio", os.path.join(V, video), out]
        if start is not None:
            cmd += [str(start), str(end)]
        subprocess.run(cmd, check=True, capture_output=True)
    w = wave.open(out)
    sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return sr, x, out


def envelope(x, sr, hop_ms=5):
    hop = int(sr * hop_ms / 1000)
    n = len(x) // hop
    e = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    return np.arange(n) * hop / sr, 20 * np.log10(e + 1e-9)


def onsets(x, sr, hop_ms=5, rise_db=9, floor_db=-50, min_gap=0.06):
    t, e = envelope(x, sr, hop_ms)
    k = max(1, int(30 / hop_ms))
    res = []
    last = -1
    for i in range(k, len(e)):
        base = e[i - k:i].min()
        if e[i] > floor_db and e[i] - base > rise_db and (t[i] - last) > min_gap and e[i] >= e[i - 1]:
            # walk to local peak
            j = i
            while j + 1 < len(e) and e[j + 1] >= e[j]:
                j += 1
            res.append((t[i], e[j]))
            last = t[i]
    return res


def describe(x, sr, t0, dur=0.4):
    """Spectral summary of a sound starting at t0: peak freqs, centroid, length above -20 dB of peak."""
    a = int(t0 * sr)
    seg = x[a:a + int(dur * sr)]
    if len(seg) < 256:
        return {}
    t, e = envelope(seg, sr, 5)
    pk = e.max()
    above = np.where(e > pk - 20)[0]
    length = (above[-1] + 1) * 0.005 if len(above) else 0
    attack = (np.argmax(e) + 1) * 0.005
    n = 4096
    spec = np.abs(np.fft.rfft(seg[: min(len(seg), int(max(length, 0.05) * sr))] * np.hanning(min(len(seg), int(max(length, 0.05) * sr))), n))
    f = np.fft.rfftfreq(n, 1 / sr)
    spec[f < 60] = 0
    cen = float((f * spec).sum() / (spec.sum() + 1e-9))
    idx = np.argsort(spec)[::-1]
    peaks = []
    for i in idx:
        if all(abs(f[i] - p) > 40 for p in peaks):
            peaks.append(float(f[i]))
        if len(peaks) >= 5:
            break
    return {"peak_db": round(float(pk), 1), "len_s": round(length, 3), "attack_s": round(attack, 3),
            "centroid_hz": round(cen), "peaks_hz": [round(p) for p in peaks]}


def spectrogram_img(x, sr, out, fmax=8000, hop=256, nfft=2048, px_per_s=400, height=300):
    win = np.hanning(nfft)
    n = (len(x) - nfft) // hop
    if n <= 0:
        return
    S = np.stack([np.abs(np.fft.rfft(x[i * hop:i * hop + nfft] * win)) for i in range(n)], 1)
    f = np.fft.rfftfreq(nfft, 1 / sr)
    S = S[f <= fmax]
    S = 20 * np.log10(S + 1e-6)
    S = np.clip((S - (S.max() - 70)) / 70, 0, 1)
    img = Image.fromarray((255 * (1 - S[::-1])).astype(np.uint8))
    img = img.resize((int(len(x) / sr * px_per_s), height))
    img.save(out)
