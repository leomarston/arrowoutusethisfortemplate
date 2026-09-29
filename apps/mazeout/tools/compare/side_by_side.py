#!/usr/bin/env python3
"""VERIFY V2 side-by-side comparison (GAMEPROMPT §9 step 1: layout ±2 pt, ΔE ≤ 6). Copied as-is from
apps/matchfactory/tools/compare/side_by_side.py (e10a076); only this docstring changed. The 393 x 852 pt canvas is also
Maze Out's (iPhone 15/16, every capture of the phone and the simulator).

    tools/compare/side_by_side.py ref.png ours.png --rects name:x,y,w,h[:kind] ... [--out sbs.png] [--json out.json]

Both images are converted to sRGB (a PNG without a profile is taken as sRGB; the simulator writes sRGB) and resampled to the
393 x 852 pt canvas at 3 px/pt. For every region (points):
  dE      CIEDE2000 between the region's mean CIELAB colours (D65): the V2 acceptance metric, pass at <= 6;
  dL      mean L* difference (ours - ref): brighter (+) or darker (-);
  dEblk   median CIEDE2000 over 3 x 3 pt blocks: how much the region's structure differs (layout, content), advisory;
  ref / ours  the mean colour as sRGB hex.
The side-by-side image puts the reference left and ours right, with every region outlined (green pass, red fail) and
numbered; the numbers index the JSON/table rows.
"""
import argparse, io, json, sys
import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont

PT_W, PT_H, SCALE = 393, 852, 3
_SRGB = ImageCms.createProfile("sRGB")


def load(path):
    im = Image.open(path)
    icc = im.info.get("icc_profile")
    im = im.convert("RGB")
    if icc:
        try:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            if "sRGB" not in (ImageCms.getProfileDescription(src) or ""):
                im = ImageCms.profileToProfile(im, src, _SRGB, outputMode="RGB")
        except Exception:
            pass
    return im.resize((PT_W * SCALE, PT_H * SCALE), Image.LANCZOS)


def srgb_to_lab(a):
    """a: float array (..., 3) in 0..255 sRGB -> CIELAB (D65)."""
    c = a / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ M.T
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    L = 116 * f[..., 1] - 16
    A = 500 * (f[..., 0] - f[..., 1])
    B = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, A, B], axis=-1)


def de2000(lab1, lab2):
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    C1 = np.hypot(a1, b1); C2 = np.hypot(a2, b2); Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25.0 ** 7)))
    a1p = (1 + G) * a1; a2p = (1 + G) * a2
    C1p = np.hypot(a1p, b1); C2p = np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360; h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1; dCp = C2p - C1p
    dh = h2p - h1p
    dh = np.where(C1p * C2p == 0, 0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp = (L1 + L2) / 2; Cbp = (C1p + C2p) / 2
    hs = h1p + h2p
    hbp = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = (1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6))
         - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dth = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25.0 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp; Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def hexcol(rgb):
    return "#%02X%02X%02X" % tuple(int(round(v)) for v in rgb)


def measure(ref, ours, regions, threshold=6.0):
    A = np.asarray(ref); B = np.asarray(ours)
    rows = []
    for i, rg in enumerate(regions):
        x, y, w, h = rg["r"]
        x0, y0 = int(round(x * SCALE)), int(round(y * SCALE)); x1, y1 = int(round((x + w) * SCALE)), int(round((y + h) * SCALE))
        LA = srgb_to_lab(A[y0:y1, x0:x1].astype(np.float32)); LB = srgb_to_lab(B[y0:y1, x0:x1].astype(np.float32))
        la = LA.reshape(-1, 3); lb = LB.reshape(-1, 3)
        ma, mb = la.mean(0), lb.mean(0)
        de = float(de2000(ma.astype(np.float64), mb.astype(np.float64)))
        # 3 x 3 pt blocks
        bs = 3 * SCALE
        hh, ww = (y1 - y0) // bs, (x1 - x0) // bs
        if hh and ww:
            ba = LA[:hh * bs, :ww * bs].reshape(hh, bs, ww, bs, 3).mean((1, 3))
            bb = LB[:hh * bs, :ww * bs].reshape(hh, bs, ww, bs, 3).mean((1, 3))
            blk = float(np.median(de2000(ba, bb)))
        else:
            blk = de
        rows.append({"i": i + 1, "name": rg["name"], "kind": rg.get("kind", "ui"), "r": rg["r"], "dE": round(de, 2),
                     "dL": round(float(mb[0] - ma[0]), 2), "dEblk": round(blk, 2),
                     "ref": hexcol(A[y0:y1, x0:x1].reshape(-1, 3).astype(np.float64).mean(0)),
                     "ours": hexcol(B[y0:y1, x0:x1].reshape(-1, 3).astype(np.float64).mean(0)),
                     "pass": de <= threshold})
    return rows


def sbs_image(ref, ours, rows, title="", k=1.5):
    W, H = int(PT_W * k), int(PT_H * k)
    a = ref.resize((W, H), Image.LANCZOS); b = ours.resize((W, H), Image.LANCZOS)
    out = Image.new("RGB", (2 * W + 12, H + 26), (255, 255, 255))
    out.paste(a, (0, 26)); out.paste(b, (W + 12, 26))
    d = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12)
    except Exception:
        font = ImageFont.load_default()
    d.text((4, 6), f"REF  {title}", fill=(0, 0, 0), font=font); d.text((W + 16, 6), "OURS", fill=(0, 0, 0), font=font)
    for r in rows:
        x, y, w, h = r["r"]
        col = (40, 220, 90) if r["pass"] else (255, 50, 50)
        for ox in (0, W + 12):
            d.rectangle([ox + x * k, 26 + y * k, ox + (x + w) * k, 26 + (y + h) * k], outline=col, width=2)
            d.text((ox + x * k + 2, 26 + y * k + 1), f"{r['i']}", fill=col, font=font)
        d.text((W + 12 + x * k + 14, 26 + y * k + 1), f"{r['dE']:.1f}", fill=col, font=font)
    return out


def parse_rect(s):
    parts = s.split(":")
    x, y, w, h = (float(v) for v in parts[1].split(","))
    return {"name": parts[0], "r": [x, y, w, h], "kind": parts[2] if len(parts) > 2 else "ui"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref"); ap.add_argument("ours")
    ap.add_argument("--rects", nargs="*", default=[])
    ap.add_argument("--out", default=None); ap.add_argument("--json", default=None)
    ap.add_argument("--threshold", type=float, default=6.0)
    a = ap.parse_args()
    ref, ours = load(a.ref), load(a.ours)
    regions = [parse_rect(s) for s in a.rects] or [{"name": "full", "r": [0, 52, PT_W, PT_H - 52], "kind": "ui"}]
    rows = measure(ref, ours, regions, a.threshold)
    for r in rows:
        print(f"{r['i']:>2} {r['name']:<24} {r['kind']:<5} dE {r['dE']:5.2f}  dL {r['dL']:+6.2f}  blk {r['dEblk']:5.2f}  ref {r['ref']} ours {r['ours']}  {'ok' if r['pass'] else 'FAIL'}")
    if a.out:
        sbs_image(ref, ours, rows).save(a.out)
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
