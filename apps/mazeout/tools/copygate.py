#!/usr/bin/env python3
"""tools/copygate.py — "does it look like the same screen at a glance?" (PLAN-P T10 / gate G4a; art-direction.md §2.1).

Metric (art-direction.md §2.1, reproduced to the third decimal by `selftest`):
  1. both images -> RGB (an opaque RGBA drops its alpha; a translucent one is composited over --bg),
     optional crop in points of a 393-pt-wide screen;
  2. resized to 98 px wide, height proportional, PIL LANCZOS; the taller one is cut to the shorter one's height (top-aligned);
  3. PIL GaussianBlur(radius 1);
  4. SSIM on luma (Y = 0.299 R + 0.587 G + 0.114 B, float), data range 255, 7x7 uniform window, sample covariance,
     K1 0.01 / K2 0.03, borders of 3 px cropped before the mean (== skimage.metrics.structural_similarity defaults);
  5. chroma overlap: CIELAB (sRGB, D65/2°) a*b* 2-D histogram, 16x16 bins over ±80 (pixels outside are dropped), each
     histogram normalised to sum 1, overlap = sum(min(h_ours, h_theirs)) (histogram intersection). A kind may set
     `chroma_min` (R1 recalibration): pixels with CIELAB chroma below it are left out of both histograms (popups and
     pages sit on the same neutral dim / board in both games, ~51 % of the Paused frame, which alone pins the overlap
     near 0.5 whatever the chrome colours are; art/review/concepts/copygate-calibration.json).
Pure numpy + scipy + Pillow (no scikit-image needed; `selftest` cross-checks against scikit-image when it is installed).

A pair PASSES (is "not a copy") when SSIM < ssim_max AND overlap < overlap_max for its kind (tools/copygate.json;
ssim_max null = SSIM is informative only for that kind). SPEC rulings 49 + 51 (FIX-2 lane B): a WHOLE screen (screen / popup /
page) is judged on its chroma overlap, its SSIM is informative; the replaced art regions (kind 'art') stay hard on both; and a
popup / page's chrome ΔE00 rule (> chrome_de00_min) counts only the ui regions whose ORIGINAL colour is in a family the D1
direction moves (`chrome_moved`, A5's metric from build/p/A5/gate.py: chrome-blue, go-green, berry, the title plank; the red
close X, red Hard panels, cream cards, the coin pill and neutral rails are kept families and only reported).

usage:
  copygate.py pair OURS.png THEIRS.png [--kind screen] [--crop x,y,w,h] [--json]
  copygate.py pairs PAIRS.json [--out REPORT.json] [--sheet DIR]
        PAIRS.json = [{"id":..,"ours":..,"theirs":..,"kind":..,"crop":[x,y,w,h]?}, ...] (paths relative to the app root)
  copygate.py sweep CAPTURE_DIR [--manifest tools/capture/manifest.json] [--lang en] [--kind-map JSON]
        [--out REPORT.json] [--sheet DIR] [--ids a,b|@FILE]   every manifest capture <id>-<lang>.png vs its `ref`
  copygate.py selftest [--json]   reproduces art-direction.md §2.1's six numbers (exit 1 if any differs by > 0.0015)
Exit codes: 0 = all pass (or selftest reproduced), 1 = a pair failed the gate / selftest mismatch, 2 = usage / missing input.
`--sheet DIR` writes blind side-by-side sheets (labels A/B in a seeded random order + key.json) for the G4b reviewer.
"""
import argparse
import json
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
CONFIG = os.path.join(HERE, "copygate.json")
THUMB_W = 98
SCREEN_PT = 393.0

# art-direction.md §2.1 (VERIFIED numbers; the P1 pass used these files). ours, theirs, ssim, overlap.
CALIBRATION = [
    ("paused-vs-007", "build/compare/captures/pause-en.png", "research/shots/007-L32-pause.png", 0.928, 0.879, "copy"),
    ("home-v11-vs-002", "build/fixa1/shots/v11-home.png", "research/shots/002-home-L32.png", 0.527, 0.838, "copy"),
    ("loading-vs-store8", "build/compare/captures/loading-en.png", "research/store/iphone-8.png", 0.473, 0.672, "copy"),
    ("control-002-vs-069", "research/shots/002-home-L32.png", "research/shots/069-skyjump-screen.png", 0.183, 0.401, "control"),
    ("control-002-vs-003", "research/shots/002-home-L32.png", "research/shots/003-L32-start.png", 0.121, 0.132, "control"),
    ("control-ourhome-vs-ourloading", "build/fixa1/shots/v11-home.png", "build/compare/captures/loading-en.png", 0.145, 0.513,
     "control"),
]


def rel(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def load_config():
    with open(CONFIG) as f:
        return json.load(f)


def load_rgb(path, crop=None, bg=(128, 128, 128)):
    im = Image.open(rel(path))
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        a = np.asarray(im)[..., 3]
        if a.min() < 255:
            base = Image.new("RGBA", im.size, tuple(bg) + (255,))
            im = Image.alpha_composite(base, im)
    im = im.convert("RGB")
    if crop:
        s = im.size[0] / SCREEN_PT
        x, y, w, h = crop
        im = im.crop((int(round(x * s)), int(round(y * s)), int(round((x + w) * s)), int(round((y + h) * s))))
    return im


def thumb(im):
    w, h = im.size
    t = im.resize((THUMB_W, max(1, round(THUMB_W * h / w))), Image.LANCZOS)
    return np.asarray(t.filter(ImageFilter.GaussianBlur(1))).astype(np.float64)


def luma(a):
    return a @ np.array([0.299, 0.587, 0.114])


def ssim(x, y, data_range=255.0, win=7):
    """== skimage.metrics.structural_similarity(x, y, data_range=...) for 2-D float images (its defaults)."""
    x = x.astype(np.float64)
    y = y.astype(np.float64)
    ux, uy = uniform_filter(x, win), uniform_filter(y, win)
    uxx, uyy, uxy = uniform_filter(x * x, win), uniform_filter(y * y, win), uniform_filter(x * y, win)
    n = win * win
    cov = n / (n - 1.0)
    vx, vy, vxy = cov * (uxx - ux * ux), cov * (uyy - uy * uy), cov * (uxy - ux * uy)
    c1, c2 = (0.01 * data_range) ** 2, (0.03 * data_range) ** 2
    s = ((2 * ux * uy + c1) * (2 * vxy + c2)) / ((ux * ux + uy * uy + c1) * (vx + vy + c2))
    p = (win - 1) // 2
    return float(s[p:-p, p:-p].mean())


def rgb2lab(a):
    """sRGB uint8-range float -> CIELAB (D65, 2°), == skimage.color.rgb2lab."""
    c = np.clip(a / 255.0, 0, 1)
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.412453, 0.357580, 0.180423], [0.212671, 0.715160, 0.072169], [0.019334, 0.119193, 0.950227]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16.0 / 116.0)
    L = 116.0 * f[..., 1] - 16.0
    return np.stack([L, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])], -1)


def chroma_hist(a, cmin=0.0):
    lab = rgb2lab(a)
    aa, bb = lab[..., 1].ravel(), lab[..., 2].ravel()
    if cmin > 0:
        keep = np.hypot(aa, bb) >= cmin
        aa, bb = aa[keep], bb[keep]
    h, _, _ = np.histogram2d(aa, bb, bins=16, range=[[-80, 80], [-80, 80]])
    return h / max(h.sum(), 1.0)


def de2000(lab1, lab2):
    """CIEDE2000 colour difference (Sharma et al. 2005), vectorised over the last axis."""
    L1, a1, b1 = np.moveaxis(np.asarray(lab1, float), -1, 0)
    L2, a2, b2 = np.moveaxis(np.asarray(lab2, float), -1, 0)
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = np.where(C1p * C2p == 0, 0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hpm = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = (1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6))
         - 0.20 * np.cos(np.radians(4 * hpm - 63)))
    dtheta = 30 * np.exp(-(((hpm - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25.0 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def region_lab(path, rects):
    """Mean colour (-> Lab) of each rect (pt on a 393-pt-wide screen) at full resolution."""
    a = np.asarray(load_rgb(path)).astype(np.float64)
    s = a.shape[1] / SCREEN_PT
    out = []
    for x, y, w, h in rects:
        crop = a[int(round(y * s)):int(round((y + h) * s)), int(round(x * s)):int(round((x + w) * s))]
        out.append(rgb2lab(crop.reshape(-1, 3).mean(0)) if crop.size else np.array([np.nan] * 3))
    return np.array(out)


def chrome_delta(ours, theirs, regions):
    """art-direction.md §2.1 popup/page rule: chrome ΔE00 vs theirs, over the shot's `ui` regions (tools/compare/regions.json)."""
    ui = [r for r in regions if r.get("kind") == "ui"]
    if not ui:
        return None
    d = de2000(region_lab(ours, [r["r"] for r in ui]), region_lab(theirs, [r["r"] for r in ui]))
    return {"n": len(ui), "median": float(np.nanmedian(d)), "min": float(np.nanmin(d)),
            "per_region": {r["name"]: round(float(v), 1) for r, v in zip(ui, d)}}


# SPEC ruling 51 (2026-09-29; ported from build/p/A5/gate.py by FIX-2 lane B): the chrome ΔE00 rule's region families.
MOVED_FAMILIES = ("chrome-blue", "go-green", "berry", "plank")
KEPT_BY_NAME = (("close", "danger-red (close X: red stays red, art §3.1)"),
                ("coinGroup", "coin pill (gold coin + near-white pill: generic)"),
                ("strip.rail", "neutral black rail"))


def lab_hex(lab):
    """CIELAB (D65) -> 'rrggbb' (the inverse of rgb2lab, clipped to sRGB)."""
    L, a, b = [float(v) for v in lab]
    fy = (L + 16.0) / 116.0
    fx, fz = fy + a / 500.0, fy - b / 200.0
    f = np.array([fx, fy, fz])
    xyz = np.where(f ** 3 > 0.008856, f ** 3, (f - 16.0 / 116.0) / 7.787) * np.array([0.95047, 1.0, 1.08883])
    m = np.array([[0.412453, 0.357580, 0.180423], [0.212671, 0.715160, 0.072169], [0.019334, 0.119193, 0.950227]])
    lin = np.clip(np.linalg.solve(m, xyz), 0, 1)
    srgb = np.where(lin > 0.0031308, 1.055 * lin ** (1 / 2.4) - 0.055, 12.92 * lin)
    return "".join("%02X" % int(round(v * 255)) for v in np.clip(srgb, 0, 1))


def region_family(name, hexv):
    """-> ("moved" | "kept", why) for one ui region, by its name and its ORIGINAL colour (A5's rule)."""
    for key, why in KEPT_BY_NAME:
        if key in name:
            return "kept", why
    if "ribbon" in name or "title" in name:
        return "moved", "plank (title ribbon)"
    import palette_map as P  # lazy (palette_map imports this module); window_family ONLY — never its build / apply
    fam, _ = P.window_family(hexv)
    if fam in MOVED_FAMILIES:
        return "moved", fam
    return "kept", fam or "gap"


def chrome_moved(ours, theirs, regions):
    """Ruling 51: the chrome ΔE00 median over only the ui regions whose ORIGINAL colour the D1 direction moves (None = no ui
    regions; median None = only kept-family regions). Per-region ΔE00 rounded to 0.1 as `chrome_delta` reports them."""
    ui = [r for r in regions if r.get("kind") == "ui"]
    if not ui:
        return None
    lt = region_lab(theirs, [r["r"] for r in ui])
    d = de2000(region_lab(ours, [r["r"] for r in ui]), lt)
    moved, kept = {}, {}
    for r, lab, v in zip(ui, lt, d):
        hexv = lab_hex(lab)
        cls, why = region_family(r["name"], hexv)
        (moved if cls == "moved" else kept)[r["name"]] = {"de00": round(float(v), 1), "theirs": "#" + hexv, "family": why}
    med = float(np.median([v["de00"] for v in moved.values()])) if moved else None
    return {"n": len(moved), "median": med, "moved": moved, "kept": kept}


def measure(ours, theirs, crop=None, crop_theirs=None, bg=(128, 128, 128), cmin=0.0):
    A = thumb(load_rgb(ours, crop, bg))
    B = thumb(load_rgb(theirs, crop_theirs if crop_theirs is not None else crop, bg))
    h = min(A.shape[0], B.shape[0])
    A, B = A[:h], B[:h]
    out = {"ssim": ssim(luma(A), luma(B)), "overlap": float(np.minimum(chroma_hist(A, cmin), chroma_hist(B, cmin)).sum()),
           "thumb_px": [THUMB_W, h]}
    if cmin > 0:
        out["chroma_min"] = cmin
    return out


def kind_cmin(cfg, kind):
    return float((cfg.get("kinds", {}).get(kind) or {}).get("chroma_min") or 0.0)


def judge(m, kind, cfg):
    k = cfg["kinds"].get(kind)
    if k is None:
        raise SystemExit(f"copygate: unknown kind {kind!r} (tools/copygate.json kinds: {sorted(cfg['kinds'])})")
    ok_s = True if k.get("ssim_max") is None else m["ssim"] < k["ssim_max"]
    ok_o = True if k.get("overlap_max") is None else m["overlap"] < k["overlap_max"]
    ok_c, cmin = True, k.get("chrome_de00_min")
    cm = m.get("chrome_moved")
    if cmin is not None and cm is not None:
        ok_c = cm["median"] is None or cm["median"] > cmin      # ruling 51: only the moved families count
    elif cmin is not None and m.get("chrome"):
        ok_c = m["chrome"]["median"] > cmin                      # no region families known: every ui region (R1)
    return {"kind": kind, "ssim_max": k.get("ssim_max"), "overlap_max": k.get("overlap_max"), "chrome_de00_min": cmin,
            "chrome_checked": bool(cmin is not None and (cm is not None or m.get("chrome"))),
            "chrome_rule": "moved families (ruling 51)" if cm is not None else ("all ui regions (R1)" if m.get("chrome") else None),
            "ssim_ok": ok_s, "overlap_ok": ok_o, "chrome_ok": ok_c, "pass": bool(ok_s and ok_o and ok_c)}


def row_text(r):
    j = r["judge"]
    s_lim = "info" if j["ssim_max"] is None else f"<{j['ssim_max']:.2f}"
    o_lim = "info" if j["overlap_max"] is None else f"<{j['overlap_max']:.2f}"
    txt = (f"{'PASS' if j['pass'] else 'FAIL'}  {r['id']:<34s} kind={j['kind']:<6s} ssim {r['ssim']:.3f} ({s_lim})  "
           f"overlap {r['overlap']:.3f} ({o_lim})")
    if r.get("chrome"):
        lim = "info" if j["chrome_de00_min"] is None else f">{j['chrome_de00_min']:.0f}"
        cm = r.get("chrome_moved")
        if cm is not None:
            mv = "n/a (kept families only)" if cm["median"] is None else f"{cm['median']:.1f}"
            txt += f"  chromeΔE00 moved {mv} ({lim}, n={cm['n']}; all {r['chrome']['median']:.1f} info)"
        else:
            txt += f"  chromeΔE00 median {r['chrome']['median']:.1f} ({lim}, n={r['chrome']['n']})"
    return txt


def blind_sheets(rows, outdir, seed=552):
    """G4b: one PNG per pair, the two images side by side labelled only A / B (order random, seeded); key.json maps back."""
    os.makedirs(outdir, exist_ok=True)
    rng = random.Random(seed)
    key = []
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 36)
    except Exception:
        font = ImageFont.load_default()
    for n, r in enumerate(rows, 1):
        imgs = [("ours", load_rgb(r["ours"], r.get("crop"))), ("theirs", load_rgb(r["theirs"], r.get("crop_theirs", r.get("crop"))))]
        if rng.random() < 0.5:
            imgs.reverse()
        H = 900
        scaled = [im.resize((max(1, round(im.size[0] * H / im.size[1])), H), Image.LANCZOS) for _, im in imgs]
        if not r.get("crop"):
            # hide the status band (the simulator draws the Dynamic Island there): a tell, not part of the art
            for s in scaled:
                ImageDraw.Draw(s).rectangle((0, 0, s.size[0], round(52 * s.size[0] / SCREEN_PT)), fill=(40, 40, 40))
        W = sum(s.size[0] for s in scaled) + 60
        sheet = Image.new("RGB", (W, H + 60), (255, 255, 255))
        x = 20
        d = ImageDraw.Draw(sheet)
        for lab, s in zip("AB", scaled):
            sheet.paste(s, (x, 50))
            d.text((x, 5), lab, fill=(0, 0, 0), font=font)
            x += s.size[0] + 20
        name = f"pair-{n:03d}.png"
        sheet.save(os.path.join(outdir, name))
        key.append({"sheet": name, "id": r["id"], "A": imgs[0][0], "B": imgs[1][0]})
    with open(os.path.join(outdir, "key.json"), "w") as f:
        json.dump({"seed": seed, "note": "do not show this file to the reviewer", "pairs": key}, f, indent=1)


def run_pairs(pairs, cfg, out=None, sheet=None, quiet=False):
    rows, missing = [], []
    for p in pairs:
        if not (os.path.exists(rel(p["ours"])) and os.path.exists(rel(p["theirs"]))):
            missing.append(p["id"])
            continue
        m = measure(p["ours"], p["theirs"], p.get("crop"), p.get("crop_theirs"), cmin=kind_cmin(cfg, p.get("kind", "screen")))
        if p.get("regions") and not p.get("crop"):
            m["chrome"] = chrome_delta(p["ours"], p["theirs"], p["regions"])
            m["chrome_moved"] = chrome_moved(p["ours"], p["theirs"], p["regions"])     # ruling 51
        r = dict(p, **m)
        r.pop("regions", None)
        r["judge"] = judge(m, p.get("kind", "screen"), cfg)
        rows.append(r)
        if not quiet:
            print(row_text(r))
    for mid in missing:
        print(f"MISSING {mid}: an input file does not exist", file=sys.stderr)
    fails = [r["id"] for r in rows if not r["judge"]["pass"]]
    report = {"tool": "tools/copygate.py", "thresholds": cfg["kinds"], "thresholds_status": cfg.get("status"),
              "pairs": rows, "missing": missing, "failed": fails, "pass": not fails and not missing}
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w") as f:
            json.dump(report, f, indent=1)
    if sheet:
        blind_sheets(rows, sheet)
    print(f"copygate: {len(rows) - len(fails)}/{len(rows)} pass, {len(fails)} fail, {len(missing)} missing")
    return 0 if report["pass"] else (2 if missing and not fails else 1)


def cmd_selftest(args):
    have_sk = True
    try:
        from skimage.color import rgb2lab as sk_lab
        from skimage.metrics import structural_similarity as sk_ssim
    except Exception:
        have_sk = False
    ok, rows = True, []
    for pid, a, b, es, eo, role in CALIBRATION:
        if not (os.path.exists(rel(a)) and os.path.exists(rel(b))):
            print(f"SKIP {pid}: missing input ({a} / {b}) — research/ and build/ files are local-only")
            ok = False
            rows.append({"id": pid, "status": "missing"})
            continue
        m = measure(a, b)
        ds, do = m["ssim"] - es, m["overlap"] - eo
        good = abs(ds) <= 0.0015 and abs(do) <= 0.0015
        ok &= good
        line = f"{'OK ' if good else 'BAD'} {pid:<32s} ssim {m['ssim']:.4f} (doc {es:.3f}, Δ{ds:+.4f})  overlap {m['overlap']:.4f} (doc {eo:.3f}, Δ{do:+.4f})  [{role}]"
        row = {"id": pid, "ssim": m["ssim"], "overlap": m["overlap"], "doc_ssim": es, "doc_overlap": eo, "ok": good, "role": role}
        if have_sk:
            A = thumb(load_rgb(a))
            B = thumb(load_rgb(b))
            h = min(A.shape[0], B.shape[0])
            A, B = A[:h], B[:h]
            s2 = sk_ssim(luma(A), luma(B), data_range=255)
            la, lb = sk_lab(np.clip(A, 0, 255) / 255), sk_lab(np.clip(B, 0, 255) / 255)
            ha = np.histogram2d(la[..., 1].ravel(), la[..., 2].ravel(), bins=16, range=[[-80, 80], [-80, 80]])[0]
            hb = np.histogram2d(lb[..., 1].ravel(), lb[..., 2].ravel(), bins=16, range=[[-80, 80], [-80, 80]])[0]
            o2 = float(np.minimum(ha / ha.sum(), hb / hb.sum()).sum())
            same = abs(s2 - m["ssim"]) < 1e-9 and abs(o2 - m["overlap"]) < 1e-9
            ok &= same
            line += f"  skimage {'==' if same else '!='} ({s2:.6f}/{o2:.6f})"
            row["skimage_equal"] = same
        print(line)
        rows.append(row)
    cfg = load_config()
    # the documented copies must FAIL today's gate and the unrelated controls must PASS it (screen thresholds)
    sep = []
    for r in rows:
        if "ssim" not in r:
            continue
        j = judge(r, "screen", cfg)
        expect_pass = r["role"] == "control"
        sep.append(j["pass"] == expect_pass)
        print(f"    gate(screen) on {r['id']}: {'pass' if j['pass'] else 'fail'} (expected {'pass' if expect_pass else 'fail'})")
    ok &= all(sep)
    # FIX-2 B negative control: the original against ITSELF must FAIL every kind with a hard threshold (the gate can see a copy);
    # a popup with ui regions must also fail the ruling-51 chrome rule on its moved families (ΔE00 0)
    same = "research/shots/007-L32-pause.png"
    if os.path.exists(rel(same)):
        for kind, k in sorted(cfg["kinds"].items()):
            if all(k.get(t) is None for t in ("ssim_max", "overlap_max", "chrome_de00_min")):
                print(f"    self-pair kind {kind}: no hard threshold (informative kind), skipped")
                continue
            m = measure(same, same, cmin=kind_cmin(cfg, kind))
            j = judge(m, kind, cfg)
            print(f"    self-pair kind {kind}: {'pass' if j['pass'] else 'FAIL'} (expected FAIL)")
            ok &= not j["pass"]
        regs = {s["id"]: s["regions"] for s in json.load(open(os.path.join(ROOT, "tools/compare/regions.json")))["shots"]}
        cm = chrome_moved(same, same, regs.get("pause", []))
        good = cm is not None and cm["n"] > 0 and cm["median"] == 0.0
        print(f"    self-pair chrome_moved on the Paused regions: n {cm and cm['n']} median {cm and cm['median']} (expected n > 0, 0.0)")
        ok &= good
    else:
        print(f"SKIP self-pair negative control: {same} missing")
        ok = False
    print("copygate selftest:", "REPRODUCED art-direction.md §2.1" if ok else "MISMATCH")
    if args.json:
        print(json.dumps({"ok": ok, "rows": rows}, indent=1))
    return 0 if ok else 1


def parse_crop(s):
    return [float(v) for v in s.split(",")] if s else None


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("pair")
    p.add_argument("ours")
    p.add_argument("theirs")
    p.add_argument("--kind", default="screen")
    p.add_argument("--crop", help="x,y,w,h in pt (393-pt-wide screen), both images")
    p.add_argument("--crop-theirs", help="x,y,w,h in pt for THEIRS only")
    p.add_argument("--json", action="store_true")
    q = sub.add_parser("pairs")
    q.add_argument("file")
    q.add_argument("--out")
    q.add_argument("--sheet")
    w = sub.add_parser("sweep")
    w.add_argument("captures")
    w.add_argument("--manifest", default=os.path.join(ROOT, "tools/capture/manifest.json"))
    w.add_argument("--lang", default="en")
    w.add_argument("--kind-map", help="JSON {capture id or prefix*: kind}; default = copygate.json sweep_kinds")
    w.add_argument("--regions", default=os.path.join(ROOT, "tools/compare/regions.json"),
                   help="per-shot ui regions for the chrome ΔE00 rule ('' = off)")
    w.add_argument("--out")
    w.add_argument("--sheet")
    w.add_argument("--ids", help="only these capture ids: a comma list or @FILE (a comma / newline list), e.g. V2's 51 EN screens")
    s = sub.add_parser("selftest")
    s.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 2
    if args.cmd == "selftest":
        return cmd_selftest(args)
    cfg = load_config()
    if args.cmd == "pair":
        for f in (args.ours, args.theirs):
            if not os.path.exists(rel(f)):
                print(f"copygate: missing {f}", file=sys.stderr)
                return 2
        m = measure(args.ours, args.theirs, parse_crop(args.crop), parse_crop(args.crop_theirs), cmin=kind_cmin(cfg, args.kind))
        r = dict(id=os.path.basename(args.ours), ours=args.ours, theirs=args.theirs, **m)
        r["judge"] = judge(m, args.kind, cfg)
        print(json.dumps(r, indent=1) if args.json else row_text(r))
        return 0 if r["judge"]["pass"] else 1
    if args.cmd == "pairs":
        with open(args.file) as f:
            pairs = json.load(f)
        return run_pairs(pairs, cfg, args.out, args.sheet)
    if args.cmd == "sweep":
        with open(args.manifest) as f:
            caps = json.load(f)["captures"]
        kmap = cfg.get("sweep_kinds", {})
        if args.kind_map:
            with open(args.kind_map) as f:
                kmap = json.load(f)

        def kind_of(cid):
            if cid in kmap:
                return kmap[cid]
            for k, v in kmap.items():
                if k.endswith("*") and cid.startswith(k[:-1]):
                    return v
            return "screen"
        regs = {}
        if args.regions and os.path.exists(args.regions):
            with open(args.regions) as f:
                regs = {s["id"]: s["regions"] for s in json.load(f)["shots"]}
        only = None
        if args.ids:
            txt = open(rel(args.ids[1:])).read() if args.ids.startswith("@") else args.ids
            only = {x.strip() for x in txt.replace("\n", ",").split(",") if x.strip()}
        pairs = []
        for c in caps:
            if not c.get("ref") or args.lang not in c.get("langs", [args.lang]):
                continue
            if only is not None and c["id"] not in only:
                continue
            ours = os.path.join(args.captures, f"{c['id']}-{args.lang}.png")
            pairs.append({"id": c["id"], "ours": ours, "theirs": c["ref"], "kind": kind_of(c["id"]), "regions": regs.get(c["id"])})
        return run_pairs(pairs, cfg, args.out, args.sheet)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
