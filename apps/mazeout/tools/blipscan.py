#!/usr/bin/env python3
"""tools/blipscan.py — one-frame anomalies ("blips") in a 60 Hz screen recording, per region (PLAN-P T10 / gate G5; owner item 5).

Definition (PLAN-P §4.1 T10): frame i is a blip when i != i-1 and i != i+1 while i-1 ~= i+1 — something appears for one frame
and the picture returns to what it was. Tested PER PIXEL and grouped into blobs, so a glitch in one corner is found while the
rest of the screen animates:

  1. frames are decoded at --width px (default 197 = 0.5 px/pt on a 393-pt screen) with their real presentation times;
  2. exact / codec-noise duplicates (<= --dup-px pixels change by > --dup-tau) are merged, so a glitch frame the recorder held
     for two captures still counts as ONE frame; each unique frame keeps its on-screen duration;
  3. for every unique triple (a, b, c) = (i-1, i, i+1), per pixel with D = max |RGB difference|:
         m = min(D(a,b), D(b,c)) > --tau          (b differs from both neighbours)
         D(a,c) < --kappa * m                      (and the neighbours agree with each other, relative to the jump)
     (--max-run 2 also tests runs of two unique frames b1 b2 between a and c);
  4. those pixels are grouped into blobs (8-connected after a 1-px dilation); a blob is a BLIP when
         its area >= --min-px (analysis pixels),
         the run's on-screen duration <= --max-ms,
         within the blob's neighbourhood (bbox + margin) the reverting pixels outnumber the pixels where a and c still
         differ (ratio >= --rho) — a moving particle or an expanding ring leaves its old and new place in D(a,c) and
         fails this, a glitch does not,
         and the blob's content in b is NOT found displaced in a or in c along a consistent path (motion check: a fast
         small object whose trail leaves the neighbourhood; skipped with --no-motion-check).
Output: one line per blip (time, duration, bbox in pt, area, regions) and a JSON report (--out), optionally evidence strips
(--evidence DIR: a | b | c crops with the blob outlined + the mask). Regions: the named bands of an Arrow Out screen
(status 0-52 pt, top 52-160, middle 160-700, bottom 700-852) plus a 4 x 8 grid cell, or --regions JSON {name: [x,y,w,h] pt}.

usage:
  blipscan.py scan INPUT [INPUT ...] [--start S --end E] [--out REPORT.json] [--evidence DIR] [params]
        INPUT = .mov/.mp4/.m4v (decoded by tools/vstream.swift, built on first use into build/tools/vstream),
                a directory of frame images (sorted; time from 'f<ms>' in the name, else index / --fps), or an .npz (t, frames)
  blipscan.py selftest [--n-per-clip 40] [--seed 552] [--out REPORT.json]
        0 false positives on 5 clean v552 clips (research/video) + 100 % of injected synthetic 1-frame blips caught
  blipscan.py survey CLIP [CLIP ...]   the FP survey (like selftest's clean half, any clips; research/video names allowed)
Exit codes: scan 0 = no blips, 1 = blips found, 2 = input error; selftest/survey 0 = pass, 1 = fail.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
VIDEO_DIR = os.path.join(ROOT, "research", "video")
VSTREAM_SRC = os.path.join(HERE, "vstream.swift")
VSTREAM_BIN = os.path.join(ROOT, "build", "tools", "vstream")
SCREEN_PT = (393.0, 852.0)

DEFAULTS = dict(width=197, tau=40, kappa=0.5, min_px=28, max_ms=50.0, rho=1.0, rho_lo=0.3, dup_tau=16, dup_px=2, max_run=1,
                status_pt=52, margin_px=6, margin_frac=0.25, motion_check=True, motion_radius_px=120, jitter_px=3,
                particle_max_px=160, particle_window_px=25, particle_min_movers=5)

# the 5 clean v552 clips of the self-test: one per A3 scenario family (taps/exits/combo, pause open/close, home ->
# settings -> home, win celebration with confetti + fireworks, Play -> level intro (zoom, draw-in, HUD drop))
SELFTEST_CLIPS = [
    "S2-L078-combo-6-quick.mov",          # arrow taps: 6 quick exits, combo colours, ripples (owner: "click on an arrow")
    "S3-L092-pause-open-close.mov",       # pause open (dim + punch) and close (owner: "open the pause menu")
    "S3-home-settings-open-close.mov",    # home idle (puppets, badges) -> Settings page -> home (owner: "go back to menu")
    "S1-L48-play-intro.mov",              # Play -> level cut -> intro zoom, draw-in, HUD drop (the Play -> intro carry-over)
    "S1-weekly-contest-open.mov",         # home -> Leaderboard tab slide + the staged Weekly tutorial pops
]
# Not in the clean set, on purpose (their one-frame events are REAL v552 effects; see the survey in the T10 report):
# celebrations (confetti pieces seen for one frame), win -> home coin flights (spinning coins at 30 Hz capture), a
# worker's lip flap, bump extremes, the unlock title pop. Scan such recordings with --ignore windows and triage the
# evidence strips.
BANDS = {"status": (0, 0, 393, 52), "top": (0, 52, 393, 108), "middle": (0, 160, 393, 540), "bottom": (0, 700, 393, 152)}


# ----------------------------------------------------------------------------------------------------------- input
def ensure_vstream():
    if os.path.exists(VSTREAM_BIN) and os.path.getmtime(VSTREAM_BIN) >= os.path.getmtime(VSTREAM_SRC):
        return VSTREAM_BIN
    os.makedirs(os.path.dirname(VSTREAM_BIN), exist_ok=True)
    subprocess.run(["nice", "-n", "19", "swiftc", "-O", "-o", VSTREAM_BIN, VSTREAM_SRC], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return VSTREAM_BIN


def resolve(path):
    if os.path.exists(path):
        return path
    cand = os.path.join(VIDEO_DIR, path)
    return cand if os.path.exists(cand) else path


def read_frames(path, width=197, start=None, end=None, fps=60.0):
    """Yields (t, uint8 HxWx3 RGB). Movies are streamed (constant memory)."""
    path = resolve(path)
    if os.path.isdir(path):
        from PIL import Image
        files = sorted(f for f in os.listdir(path) if f.lower().endswith((".png", ".jpg", ".jpeg")))
        for k, f in enumerate(files):
            m = re.search(r"f(\d+)", f)
            t = int(m.group(1)) / 1000.0 if m else k / fps
            if (start is not None and t < start) or (end is not None and t > end):
                continue
            im = Image.open(os.path.join(path, f)).convert("RGB")
            h = int(round(width * im.size[1] / im.size[0]))
            yield t, np.asarray(im.resize((width, h), Image.BILINEAR))
        return
    if path.endswith(".npz"):
        z = np.load(path)
        for t, f in zip(z["t"], z["frames"]):
            if (start is None or t >= start) and (end is None or t <= end):
                yield float(t), f
        return
    exe = ensure_vstream()
    cmd = [exe, path, str(width)] + ([str(start if start is not None else 0), str(end if end is not None else 1e9)]
                                     if (start is not None or end is not None) else [])
    p = subprocess.Popen(["nice", "-n", "19"] + cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    hdr = p.stdout.read(16)
    if len(hdr) < 16:
        raise SystemExit(f"blipscan: cannot decode {path}: {p.stderr.read().decode()[:300]}")
    magic, w, h, _ = np.frombuffer(hdr, dtype="<i4")
    n = w * h * 4
    while True:
        tb = p.stdout.read(8)
        if len(tb) < 8:
            break
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        bgra = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
        yield float(np.frombuffer(tb, dtype="<f8")[0]), bgra[..., 2::-1].copy()
    p.wait()


# -------------------------------------------------------------------------------------------------------- analysis
def cheb(x, y):
    return np.abs(x.astype(np.int16) - y.astype(np.int16)).max(axis=2)


class Unique:
    __slots__ = ("t", "img", "raw", "dur", "n")

    def __init__(self, t, img, raw):
        self.t, self.img, self.raw, self.dur, self.n = t, img, raw, None, 1


def dedupe(frames, P):
    """Merges duplicate captures; yields Unique frames with .dur set (the last one gets dur = None)."""
    last = None
    for k, (t, img) in enumerate(frames):
        if last is not None:
            if (cheb(last.img, img) > P["dup_tau"]).sum() <= P["dup_px"]:
                last.n += 1
                continue
            last.dur = t - last.t
            yield last
        last = Unique(t, img, k)
    if last is not None:
        yield last


def region_names(bbox_pt, regions):
    x0, y0, x1, y1 = bbox_pt
    out = []
    for name, (rx, ry, rw, rh) in regions.items():
        if x0 < rx + rw and x1 > rx and y0 < ry + rh and y1 > ry:
            out.append(name)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cell = f"r{min(7, max(0, int(cy // (SCREEN_PT[1] / 8))))}c{min(3, max(0, int(cx // (SCREEN_PT[0] / 4))))}"
    return out, cell


def _masked_search(other, b, chg, sl, mask, R):
    """Masked SSD of b's blob pixels against `other` at every displacement |d| <= R (FFT correlation), restricted to places
    where `chg` (other vs b changed) covers >= half the blob: the object must have LEFT that place (or ARRIVED there), so a
    static look-alike elsewhere never explains the blob. Returns (rms_best, (dx, dy)) or (None, None)."""
    from scipy.signal import fftconvolve
    H, W = b.shape[:2]
    y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
    h, w = y1 - y0, x1 - x0
    wy0, wy1, wx0, wx1 = y0 - R, y1 + R, x0 - R, x1 + R
    py0, px0 = max(0, -wy0), max(0, -wx0)
    py1, px1 = max(0, wy1 - H), max(0, wx1 - W)
    O = other[max(0, wy0):min(H, wy1), max(0, wx0):min(W, wx1)].astype(np.float64)
    C = chg[max(0, wy0):min(H, wy1), max(0, wx0):min(W, wx1)].astype(np.float64)
    V = np.ones(C.shape)
    pad = ((py0, py1), (px0, px1))
    O = np.pad(O, pad + ((0, 0),))
    C = np.pad(C, pad)
    V = np.pad(V, pad)
    m = mask.astype(np.float64)
    T = b[y0:y1, x0:x1].astype(np.float64) * m[..., None]
    k = m[::-1, ::-1]
    n = m.sum()
    ssd = fftconvolve((O * O).sum(2), k, mode="valid") + (T * T).sum()
    for ch in range(3):
        ssd -= 2 * fftconvolve(O[..., ch], T[::-1, ::-1, ch], mode="valid")
    rms = np.sqrt(np.maximum(ssd, 0) / (3 * n))
    moved = fftconvolve(C, k, mode="valid") / n
    inside = fftconvolve(V, k, mode="valid") / n
    ok = (moved >= 0.5) & (inside >= 0.95)
    ok[R, R] = False                                  # d = 0 is the blob itself
    if not ok.any():
        return None
    # masked mean colour at every shift (the loose test: a spinning coin changes shape, not colour)
    mb = (b[y0:y1, x0:x1].astype(np.float64)[mask]).mean(0)
    cd = np.zeros(ok.shape)
    for ch in range(3):
        cd = np.maximum(cd, np.abs(fftconvolve(O[..., ch], k, mode="valid") / n - mb[ch]))
    rms = np.where(ok, rms, np.inf)
    cd = np.where(ok, cd, np.inf)
    iy, ix = np.unravel_index(np.argmin(rms), rms.shape)
    jy, jx = np.unravel_index(np.argmin(cd), cd.shape)
    return {"rms": float(rms[iy, ix]), "d": (int(ix - R), int(iy - R)), "cd": float(cd[jy, jx]), "d_cd": (int(jx - R), int(jy - R)),
            "cd_map": cd}


def particle_field(a, run, c, sl, blob, P, rev=None):
    """True when the blob is one small piece among >= particle_min_movers other small moving pieces nearby (confetti,
    sparks): each piece moves further than its size per frame, so every frame 'reverts' somewhere. A small glitch inside
    a confetti burst is therefore not reported (documented limit); a large one still is."""
    H, W = a.shape[:2]
    mg = P["particle_window_px"]
    y0, y1 = max(0, sl[0].start - mg), min(H, sl[0].stop + mg)
    x0, x1 = max(0, sl[1].start - mg), min(W, sl[1].stop + mg)
    mov = (cheb(a[y0:y1, x0:x1], run[0][y0:y1, x0:x1]) > P["tau"]) | (cheb(run[-1][y0:y1, x0:x1], c[y0:y1, x0:x1]) > P["tau"])
    own = np.zeros_like(mov)
    own[sl[0].start - y0:sl[0].stop - y0, sl[1].start - x0:sl[1].stop - x0] = ndimage.binary_dilation(blob[sl], iterations=2)
    lab, n = ndimage.label(mov & ~own, structure=np.ones((3, 3)))
    # a window clipped by the screen edge holds proportionally fewer pieces (pieces also enter from off screen there)
    full = (sl[0].stop - sl[0].start + 2 * mg) * (sl[1].stop - sl[1].start + 2 * mg)
    need = max(2, int(np.ceil(P["particle_min_movers"] * max(0.4, mov.size / full))))
    if n < need:
        return False
    sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
    small = sizes[(sizes >= 4) & (sizes <= P["particle_max_px"])]
    if len(small) < need:
        return False
    if rev is None:
        return True
    # a particle FIELD also reverts elsewhere in the same frame (other pieces doing the same one-frame hop); continuous
    # animation around a glitch (a breathing character, a sliding page) does not
    r = rev[y0:y1, x0:x1] & ~own
    lr, nr = ndimage.label(r, structure=np.ones((3, 3)))
    if nr < 1:
        return False
    rs = ndimage.sum(np.ones_like(lr), lr, index=np.arange(1, nr + 1))
    return int((rs >= 4).sum()) >= max(1, int(round(2 * min(1.0, mov.size / full))))


def jitter_explains(a, run, c, sl, mask, J):
    """True when the blob's content in the run is a neighbour's content moved by <= J px and/or scaled by <= 3 % about the
    blob (a wobble, the turning point of a scale punch or pop, sub-pixel resampling): the same thing jiggling in place, not
    something appearing."""
    y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
    H, W = a.shape[:2]
    cy, cx = (y0 + y1 - 1) / 2.0, (x0 + x1 - 1) / 2.0
    yy, xx = np.nonzero(mask)
    yy, xx = yy + y0, xx + x0
    for b, nb in ((run[0], a), (run[-1], c)):
        vb = b[yy, xx].astype(float)
        if vb.std(0).mean() < 20:
            # flat content (a layer went missing, a flat rect) matches any flat patch nearby: never "jitter"
            continue
        rms0 = np.sqrt(((nb[yy, xx].astype(float) - vb) ** 2).mean())
        nbf = nb.astype(float)
        for sc in (1.0, 0.97, 0.98, 0.99, 1.01, 1.02, 1.03):
            for dy in range(-J, J + 1):
                for dx in range(-J, J + 1):
                    if sc == 1.0 and (dx, dy) == (0, 0):
                        continue
                    # where the blob pixel's content sits in the neighbour under scale sc about the blob centre + shift
                    sy = cy + (yy - cy) / sc + dy
                    sx = cx + (xx - cx) / sc + dx
                    if sy.min() < 0 or sx.min() < 0 or sy.max() > H - 1 or sx.max() > W - 1:
                        continue
                    iy, ix = np.floor(sy).astype(int), np.floor(sx).astype(int)
                    fy, fx = (sy - iy)[:, None], (sx - ix)[:, None]
                    iy1, ix1 = np.minimum(iy + 1, H - 1), np.minimum(ix + 1, W - 1)
                    v = (nbf[iy, ix] * (1 - fy) * (1 - fx) + nbf[iy, ix1] * (1 - fy) * fx + nbf[iy1, ix] * fy * (1 - fx)
                         + nbf[iy1, ix1] * fy * fx)
                    e = np.sqrt(((v - vb) ** 2).mean())
                    if e <= 40 and e <= 0.5 * rms0:
                        return True
    return False


def loose_ok(a, b, sl, mask):
    """The colour-only (shape-free) explanations apply to small, one-colour pieces (coins, confetti, shards) whose colour is
    NEW at that place (not already there in the neighbour): a flat background or a multi-coloured layer never qualifies."""
    if mask.sum() > 400:
        return False
    y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
    core = ndimage.binary_erosion(mask, structure=np.ones((2, 2)))
    m = core if core.sum() >= 4 else mask          # colour statistics without the anti-aliased rim
    vb = b[y0:y1, x0:x1][m].astype(float)
    if vb.std(0).mean() > 45:
        return False
    va = a[y0:y1, x0:x1][m].astype(float)
    return float(np.abs(va.mean(0) - vb.mean(0)).max()) > 50


def border_explains(a, run, c, sl, mask, R, tau):
    """A piece touching the screen edge that is leaving (found in a, moving outward, its next place off screen) or entering
    (found in c, coming from off screen): the continuation cannot be seen, so motion_explains cannot pair it."""
    H, W = a.shape[:2]
    y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
    edge = []
    if y0 <= 1:
        edge.append((0, -1))
    if y1 >= H - 1:
        edge.append((0, 1))
    if x0 <= 1:
        edge.append((-1, 0))
    if x1 >= W - 1:
        edge.append((1, 0))
    if not edge:
        return False
    if not (loose_ok(a, run[0], sl, mask) and loose_ok(c, run[-1], sl, mask)):
        return False
    for nb, other in ((a, run[0]), (c, run[-1])):
        X = _masked_search(nb, other, cheb(nb, other) > tau, sl, mask, R)
        if X is None:
            continue
        for iy, ix in np.argwhere(X["cd_map"] <= 35):
            d = np.array([ix - R, iy - R], float)
            if np.hypot(*d) < 2:
                continue
            # leaving: the piece came from -d_a direction... in a it sits at +d (behind); motion = -d; must point outward
            move = -d if nb is a else d
            if any(move[0] * ex + move[1] * ey > 0.5 * np.hypot(*move) for ex, ey in edge):
                return True
    return False


def motion_explains(a, run, c, sl, mask, R, tau):
    """True when the blob of the run's first frame is found displaced in a (at a place the object has left) AND in c (at a
    place it has reached), with displacements pointing opposite ways: an object moving along a path (coins, confetti,
    sparks faster than their own size per frame), not something that appears and vanishes."""
    b = run[0]
    if mask.sum() < 4:
        return False
    y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
    rms0 = np.sqrt(((a[y0:y1, x0:x1].astype(float) - b[y0:y1, x0:x1].astype(float)) ** 2)[mask].mean())
    A = _masked_search(a, b, cheb(a, b) > tau, sl, mask, R)
    C = _masked_search(c, run[-1], cheb(c, run[-1]) > tau, sl, mask, R)
    if A is None or C is None:
        return False
    good = lambda e: e <= 40 and e <= 0.5 * rms0  # noqa: E731
    if good(A["rms"]) and good(C["rms"]) and A["d"][0] * C["d"][0] + A["d"][1] * C["d"][1] < 0:
        return True
    # loose path (small one-colour compact pieces only): the same colour left a place d_a and reached d_c ~ -d_a
    core = ndimage.binary_erosion(mask, structure=np.ones((2, 2))).sum()
    if core < 0.5 * mask.sum() or not (loose_ok(a, b, sl, mask) and loose_ok(c, run[-1], sl, mask)):
        return False
    pa = np.argwhere(A["cd_map"] <= 35)
    pc = np.argwhere(C["cd_map"] <= 35)
    if not len(pa) or not len(pc):
        return False
    if len(pa) > 300:
        pa = pa[np.argsort(A["cd_map"][pa[:, 0], pa[:, 1]])[:300]]
    if len(pc) > 300:
        pc = pc[np.argsort(C["cd_map"][pc[:, 0], pc[:, 1]])[:300]]
    da = (pa - R)[:, ::-1].astype(float)          # (dx, dy)
    dc = (pc - R)[:, ::-1].astype(float)
    la, lc = np.hypot(da[:, 0], da[:, 1]), np.hypot(dc[:, 0], dc[:, 1])
    keep_a, keep_c = la >= 2, lc >= 2
    da, la, dc, lc = da[keep_a], la[keep_a], dc[keep_c], lc[keep_c]
    if not len(da) or not len(dc):
        return False
    # an accelerating / curving / fluttering path: d_c points within 45 deg of -d_a, |d_c| / |d_a| in [0.4, 2.5]
    cos = -(da @ dc.T) / (la[:, None] * lc[None, :])
    ratio = lc[None, :] / la[:, None]
    return bool(((cos >= np.cos(np.radians(45))) & (ratio >= 0.4) & (ratio <= 2.5)).any())


def ignored(b, ignore):
    """--ignore entries: {"t0": s, "t1": s, "rect": [x, y, w, h] pt (optional, default whole screen), "why": "..."}."""
    for g in ignore or ():
        if g.get("t0", -1e9) <= b["t"] <= g.get("t1", 1e9):
            x, y, w, h = g.get("rect", (0, 0, SCREEN_PT[0], SCREEN_PT[1]))
            bb = b["bbox_pt"]
            if bb[0] >= x - 1 and bb[1] >= y - 1 and bb[2] <= x + w + 1 and bb[3] <= y + h + 1:
                return g.get("why", "ignored")
    return None


def analyse(frames, P, regions=None, evidence=None, label="", trace=False):
    regions = regions or BANDS
    t0 = time.time()
    uniq = []
    blips = []
    n_raw = 0
    width = None
    stats = {"candidates": 0, "rejected_area": 0, "rejected_duration": 0, "rejected_ratio": 0, "rejected_jitter": 0,
             "rejected_particles": 0, "rejected_border": 0, "rejected_motion": 0}
    if trace:
        stats["trace"] = []
    win = []
    for u in dedupe(frames, P):
        n_raw = u.raw + u.n
        width = u.img.shape[1]
        win.append(u)
        uniq.append((u.t, u.dur, u.raw, u.n))
        if len(win) > P["max_run"] + 2:
            win.pop(0)
        for k in range(1, P["max_run"] + 1):
            if len(win) < k + 2:
                continue
            seq = win[-(k + 2):]
            a, run, c = seq[0], seq[1:-1], seq[-1]
            if any(r.dur is None for r in run):
                continue
            blips.extend(test_run(a, run, c, P, regions, stats, evidence, label))
    s = SCREEN_PT[0] / width if width else 1.0
    # a run of 2 that contains a run-1 blip at the same place is the same event: keep the run-1 entry
    blips = merge_overlaps(blips)
    return {"frames": n_raw, "unique_frames": len(uniq), "width_px": width, "pt_per_px": s,
            "t_first": uniq[0][0] if uniq else None, "t_last": uniq[-1][0] if uniq else None,
            "blips": blips, "stats": stats, "seconds": round(time.time() - t0, 2)}


def merge_overlaps(blips):
    out = []
    for b in sorted(blips, key=lambda b: (b["raw_frame"], b["run"])):
        dup = False
        for o in out:
            if abs(o["raw_frame"] - b["raw_frame"]) <= 2 and not (
                    b["bbox_pt"][0] > o["bbox_pt"][2] or b["bbox_pt"][2] < o["bbox_pt"][0] or
                    b["bbox_pt"][1] > o["bbox_pt"][3] or b["bbox_pt"][3] < o["bbox_pt"][1]):
                dup = True
                break
        if not dup:
            out.append(b)
    return out


def test_run(a, run, c, P, regions, stats, evidence, label):
    dur = sum(r.dur for r in run)
    dac = cheb(a.img, c.img)
    m = None
    for r in run:
        x = np.minimum(cheb(a.img, r.img), cheb(r.img, c.img))
        m = x if m is None else np.minimum(m, x)
    rev = (m > P["tau"]) & (dac < P["kappa"] * m)
    if P["status_pt"]:
        # the iOS status band (clock, battery, Dynamic Island) is drawn by the system, never by the app: not analysed
        # (the same convention as tools/compare)
        rev[:int(round(P["status_pt"] * rev.shape[1] / SCREEN_PT[0]))] = False
    if rev.sum() < P["min_px"]:
        return []
    stats["candidates"] += 1
    if dur * 1000.0 > P["max_ms"]:
        stats["rejected_duration"] += 1
        return []
    lab, n = ndimage.label(ndimage.binary_dilation(rev, iterations=1), structure=np.ones((3, 3)))
    out = []
    width = a.img.shape[1]
    s = SCREEN_PT[0] / width
    still = dac > P["tau"]
    H, W = rev.shape
    trace = stats.get("trace")

    def reject(why, sl):
        stats["rejected_" + why] += 1
        if trace is not None:
            trace.append({"raw_frame": run[0].raw, "why": why,
                          "bbox_pt": [round(sl[1].start * s, 1), round(sl[0].start * s, 1), round(sl[1].stop * s, 1),
                                      round(sl[0].stop * s, 1)]})

    for idx, sl in enumerate(ndimage.find_objects(lab), 1):
        comp = (lab[sl] == idx) & rev[sl]
        area = int(comp.sum())
        # >= 2 px thick somewhere: a 1-px edge line left by a scaling panel is not a glitch
        core = int(ndimage.binary_erosion(comp, structure=np.ones((2, 2))).sum())
        if area < P["min_px"] or core < max(3, P["min_px"] // 4) or core < 0.15 * area:
            reject("area", sl)
            continue
        mg = max(P["margin_px"], int(P["margin_frac"] * max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)))
        y0, y1 = max(0, sl[0].start - mg), min(H, sl[0].stop + mg)
        x0, x1 = max(0, sl[1].start - mg), min(W, sl[1].stop + mg)
        c3 = int(still[y0:y1, x0:x1].sum())
        ratio = area / max(1, c3)
        if ratio < P["rho_lo"]:
            reject("ratio", sl)
            if trace is not None:
                trace[-1]["ratio"] = round(ratio, 3)
            continue
        if P["motion_check"] and area <= P["particle_max_px"] and particle_field(a.img, [r.img for r in run], c.img, sl, lab == idx, P, rev):
            reject("particles", sl)
            continue
        if P["motion_check"] and jitter_explains(a.img, [r.img for r in run], c.img, sl, comp, P["jitter_px"]):
            reject("jitter", sl)
            continue
        if P["motion_check"] and border_explains(a.img, [r.img for r in run], c.img, sl, comp, P["motion_radius_px"], P["tau"]):
            reject("border", sl)
            continue
        if P["motion_check"] and motion_explains(a.img, [r.img for r in run], c.img, sl, comp, P["motion_radius_px"], P["tau"]):
            reject("motion", sl)
            continue
        bb = [round(sl[1].start * s, 1), round(sl[0].start * s, 1), round(sl[1].stop * s, 1), round(sl[0].stop * s, 1)]
        names, cell = region_names(bb, regions)
        b = {"t": round(run[0].t, 4), "raw_frame": run[0].raw, "run": len(run), "dur_ms": round(dur * 1000, 1),
             "tier": "blip" if ratio >= P["rho"] else "suspect",
             "bbox_pt": bb, "area_pt2": round(area * s * s, 1), "px": area, "still_px": c3, "ratio": round(ratio, 2),
             "regions": names, "cell": cell}
        out.append(b)
        if evidence:
            save_evidence(evidence, label, b, a.img, [r.img for r in run], c.img, sl, comp)
    return out


def save_evidence(outdir, label, b, a, run, c, sl, comp):
    from PIL import Image, ImageDraw
    os.makedirs(outdir, exist_ok=True)
    H, W = a.shape[:2]
    mg = 30
    y0, y1 = max(0, sl[0].start - mg), min(H, sl[0].stop + mg)
    x0, x1 = max(0, sl[1].start - mg), min(W, sl[1].stop + mg)
    tiles = [a] + list(run) + [c]
    mask = np.zeros((H, W, 3), np.uint8)
    mask[sl][comp] = (255, 0, 0)
    tiles.append(mask)
    crops = [Image.fromarray(np.ascontiguousarray(t[y0:y1, x0:x1])).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.NEAREST)
             for t in tiles]
    cw, ch = crops[0].size
    sheet = Image.new("RGB", (len(crops) * (cw + 6), ch + 18), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    names = ["i-1"] + ["i" if k == 0 else f"i+{k}" for k in range(len(run))] + [f"i+{len(run)}", "mask"]
    for k, (cimg, nm) in enumerate(zip(crops, names)):
        sheet.paste(cimg, (k * (cw + 6), 18))
        d.text((k * (cw + 6) + 2, 2), nm, fill=(200, 0, 0))
        d.rectangle((k * (cw + 6) + (sl[1].start - x0) * 3, 18 + (sl[0].start - y0) * 3,
                     k * (cw + 6) + (sl[1].stop - x0) * 3, 18 + (sl[0].stop - y0) * 3), outline=(255, 0, 255))
    sheet.save(os.path.join(outdir, f"{label or 'clip'}-t{b['t']:.3f}-f{b['raw_frame']}.png"))


def params_from(args):
    P = dict(DEFAULTS)
    for k in DEFAULTS:
        v = getattr(args, k, None)
        if v is not None:
            P[k] = v
    if getattr(args, "no_motion_check", False):
        P["motion_check"] = False
    return P


def add_params(ap):
    ap.add_argument("--width", type=int)
    ap.add_argument("--tau", type=int, help="per-pixel jump threshold (max |RGB diff|, 0-255)")
    ap.add_argument("--kappa", type=float, help="neighbours agree when D(a,c) < kappa * jump")
    ap.add_argument("--min-px", dest="min_px", type=int, help="minimum blob area in analysis pixels")
    ap.add_argument("--max-ms", dest="max_ms", type=float, help="longest on-screen duration of a blip run")
    ap.add_argument("--rho", type=float, help="tier 'blip' when reverting px / still-different px near the blob >= rho")
    ap.add_argument("--rho-lo", dest="rho_lo", type=float,
                    help="tier 'suspect' when rho_lo <= ratio < rho (a glitch over content that is itself moving)")
    ap.add_argument("--max-run", dest="max_run", type=int, help="1 = strict one-frame definition, 2 = also 2-frame runs")
    ap.add_argument("--no-motion-check", action="store_true", help="skip the jitter and motion explanations")
    ap.add_argument("--jitter-px", dest="jitter_px", type=int)
    ap.add_argument("--motion-radius-px", dest="motion_radius_px", type=int)
    ap.add_argument("--regions", help="JSON {name: [x, y, w, h] pt}")
    ap.add_argument("--status-pt", dest="status_pt", type=float, help="ignore the top N pt (iOS status band; default 52, 0 = off)")


def fmt(b):
    return (f"  {b.get('tier', 'blip').upper():7s} t={b['t']:.3f}s frame {b['raw_frame']} run {b['run']} dur {b['dur_ms']:.0f} ms  bbox_pt "
            f"{b['bbox_pt']}  area {b['area_pt2']:.0f} pt2  ratio {b['ratio']}  regions {','.join(b['regions'])} cell {b['cell']}")


def cmd_scan(args):
    P = params_from(args)
    regions = BANDS
    if args.regions:
        with open(args.regions) as f:
            regions = {k: tuple(v) for k, v in json.load(f).items()}
    ignore = []
    if args.ignore:
        with open(args.ignore) as f:
            ignore = json.load(f)
    reports, total = [], 0
    for inp in args.inputs:
        if not os.path.exists(resolve(inp)):
            print(f"blipscan: missing input {inp}", file=sys.stderr)
            return 2
        label = os.path.splitext(os.path.basename(inp.rstrip("/")))[0]
        r = analyse(read_frames(inp, P["width"], args.start, args.end), P, regions, args.evidence, label)
        r["input"] = inp
        kept, skipped = [], []
        for b in r["blips"]:
            why = ignored(b, ignore)
            (skipped if why else kept).append(dict(b, ignored=why) if why else b)
        r["blips"], r["ignored"] = kept, skipped
        per = {}
        for b in r["blips"]:
            for nm in b["regions"] or [b["cell"]]:
                per[nm] = per.get(nm, 0) + 1
        r["per_region"] = per
        total += len(r["blips"])
        reports.append(r)
        nb = sum(1 for b in r["blips"] if b["tier"] == "blip")
        print(f"{inp}: {r['frames']} frames ({r['unique_frames']} unique) {r['t_first']:.3f}..{r['t_last']:.3f}s  "
              f"blips {nb}  suspects {len(r['blips']) - nb}  per region {per}  ignored {len(skipped)}  [{r['seconds']} s]")
        for b in r["blips"]:
            print(fmt(b))
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump({"tool": "tools/blipscan.py", "params": P, "regions": regions, "reports": reports, "blips_total": total},
                      f, indent=1)
    return 1 if total else 0


# -------------------------------------------------------------------------------------------------------- self-test
def draw_blip(img, kind, rng, pool, s):
    """Applies one synthetic glitch to img (HxWx3 uint8, in place). s = px per pt. Returns bbox in px (x0, y0, x1, y1)."""
    from PIL import Image, ImageDraw
    H, W = img.shape[:2]
    P2 = lambda v: int(round(v * s))  # noqa: E731
    if kind == "xbadge":           # the "gone error" badge: a red disc with a white X, 7-14 pt radius
        r = P2(rng.uniform(7.5, 14))
        cx, cy = rng.integers(r, W - r), rng.integers(P2(60) + r, H - r)
        im = Image.fromarray(img)
        d = ImageDraw.Draw(im)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(229, 57, 53))
        k = max(1, r // 2)
        d.line((cx - k, cy - k, cx + k, cy + k), fill=(255, 255, 255), width=max(1, r // 3))
        d.line((cx - k, cy + k, cx + k, cy - k), fill=(255, 255, 255), width=max(1, r // 3))
        img[:] = np.asarray(im)
        return (cx - r, cy - r, cx + r, cy + r)
    if kind == "arrowflash":       # an arrow drawn for one frame at a wrong place / state (start-state, red)
        L, th = P2(rng.uniform(25, 120)), max(2, P2(rng.uniform(5, 7)))
        col = [(20, 20, 20), (229, 57, 53)][int(rng.integers(0, 2))]
        horiz = rng.random() < 0.5
        w_, h_ = (L + 2 * th, 3 * th) if horiz else (3 * th, L + 2 * th)
        x0, y0 = rng.integers(0, W - w_), rng.integers(P2(60), H - h_)
        im = Image.fromarray(img)
        d = ImageDraw.Draw(im)
        if horiz:
            ym = y0 + h_ // 2
            d.line((x0, ym, x0 + L, ym), fill=col, width=th)
            d.polygon([(x0 + L, y0), (x0 + L + 2 * th, ym), (x0 + L, y0 + h_)], fill=col)
        else:
            xm = x0 + w_ // 2
            d.line((xm, y0, xm, y0 + L), fill=col, width=th)
            d.polygon([(x0, y0 + L), (xm, y0 + L + 2 * th), (x0 + w_, y0 + L)], fill=col)
        img[:] = np.asarray(im)
        return (x0, y0, x0 + w_, y0 + h_)
    if kind in ("staleLayer", "fullPage"):   # another page's pixels for one frame (a parked layer showing)
        src = pool[int(rng.integers(0, len(pool)))]
        src = src[:H, :W] if src.shape[0] >= H else np.pad(src, ((0, H - src.shape[0]), (0, 0), (0, 0)), mode="edge")
        if kind == "fullPage":
            img[:] = src
            return (0, 0, W, H)
        w_, h_ = P2(rng.uniform(60, 393)), P2(rng.uniform(60, 400))
        w_, h_ = min(w_, W), min(h_, H)
        x0, y0 = rng.integers(0, W - w_ + 1), rng.integers(0, H - h_ + 1)
        img[y0:y0 + h_, x0:x0 + w_] = src[y0:y0 + h_, x0:x0 + w_]
        return (x0, y0, x0 + w_, y0 + h_)
    if kind == "dimLead":          # the popup dim for one frame without its panel
        w_, h_ = P2(rng.uniform(150, 393)), P2(rng.uniform(150, 700))
        w_, h_ = min(w_, W), min(h_, H)
        x0, y0 = rng.integers(0, W - w_ + 1), rng.integers(0, H - h_ + 1)
        al = rng.uniform(0.5, 0.9)
        img[y0:y0 + h_, x0:x0 + w_] = (img[y0:y0 + h_, x0:x0 + w_] * (1 - al)).astype(np.uint8)
        return (x0, y0, x0 + w_, y0 + h_)
    if kind == "shiftedLayer":     # a layer drawn at a wrong offset for one frame
        w_, h_ = P2(rng.uniform(40, 200)), P2(rng.uniform(40, 200))
        dx, dy = P2(rng.uniform(40, 150)) * (1 if rng.random() < 0.5 else -1), P2(rng.uniform(-60, 60))
        x0, y0 = rng.integers(max(0, -dx), min(W - w_, W - w_ - dx) + 1), rng.integers(max(0, -dy), min(H - h_, H - h_ - dy) + 1)
        img[y0 + dy:y0 + dy + h_, x0 + dx:x0 + dx + w_] = img[y0:y0 + h_, x0:x0 + w_].copy()
        return (x0 + dx, y0 + dy, x0 + dx + w_, y0 + dy + h_)
    if kind == "flat":             # a missing / wrong-colour layer: a flat saturated rect
        w_, h_ = P2(rng.uniform(12, 150)), P2(rng.uniform(12, 150))
        x0, y0 = rng.integers(0, W - w_), rng.integers(P2(52), H - h_)
        img[y0:y0 + h_, x0:x0 + w_] = rng.choice([(255, 255, 255), (16, 162, 239), (255, 207, 0), (0, 228, 0), (20, 20, 20)])
        return (x0, y0, x0 + w_, y0 + h_)
    raise ValueError(kind)


KINDS = ["xbadge", "arrowflash", "staleLayer", "fullPage", "dimLead", "shiftedLayer", "flat"]


def effective_px(orig, new, bbox, tau, top=0):
    x0, y0, x1, y1 = bbox
    y0 = max(y0, top)
    if y1 <= y0:
        return 0
    return int((cheb(orig[y0:y1, x0:x1], new[y0:y1, x0:x1]) > tau).sum())


def overlaps(bb_pt, bbox_px, s, pad=2.0):
    x0, y0, x1, y1 = [v * s for v in bbox_px]
    return not (bb_pt[0] > x1 + pad or bb_pt[2] < x0 - pad or bb_pt[1] > y1 + pad or bb_pt[3] < y0 - pad)


def cmd_selftest(args):
    P = params_from(args)
    rng = np.random.default_rng(args.seed)
    clips = args.clips or SELFTEST_CLIPS
    missing = [c for c in clips if not os.path.exists(resolve(c))]
    if missing:
        print("blipscan selftest: missing clips (research/video is local-only):", missing)
        return 1
    report = {"params": P, "clips": [], "seed": args.seed}
    fp_total, inj_total, caught_total, below_floor = 0, 0, 0, 0
    per_kind = {k: [0, 0] for k in KINDS}
    tiers = {"blip": 0, "suspect": 0}
    scope = {"in_definition": [0, 0], "in_transition": [0, 0]}
    frames_cache = {}
    # a pool of "other page" frames (for staleLayer / fullPage): one frame from each clip's middle
    for c in clips:
        fr = list(read_frames(c, P["width"]))
        frames_cache[c] = fr
    pool = [frames_cache[c][len(frames_cache[c]) // 2][1] for c in clips]
    for ci, c in enumerate(clips):
        fr = frames_cache[c]
        clean = analyse(iter(fr), P, label=os.path.basename(c), evidence=args.evidence)
        fp = len(clean["blips"])
        fp_total += fp
        print(f"CLEAN {c}: {clean['frames']} frames ({clean['unique_frames']} unique)  detections (blip + suspect) {fp}  "
              f"stats {clean['stats']}")
        for b in clean["blips"]:
            print(fmt(b))
        # injection: frames spaced >= 5 apart, not in the first/last 3; the pool frame of this clip is excluded
        n = len(fr)
        cand = np.arange(3, n - 3)
        rng.shuffle(cand)
        chosen = []
        for j in cand:
            if all(abs(j - k) >= 5 for k in chosen):
                chosen.append(int(j))
            if len(chosen) >= args.n_per_clip:
                break
        other_pool = [p for k, p in enumerate(pool) if k != ci]
        s = SCREEN_PT[0] / fr[0][1].shape[1]
        inj = {}
        new = [(t, im) for t, im in fr]
        for j in sorted(chosen):
            kind = KINDS[len(inj) % len(KINDS)]
            for _ in range(20):
                im = fr[j][1].copy()
                bbox = draw_blip(im, kind, rng, other_pool, 1.0 / s)
                eff = effective_px(fr[j][1], im, bbox, P["tau"], int(round(P["status_pt"] / s)))
                # the floor: the glitch must change >= min_px + 16 analysis pixels (160 pt2 at the default 0.5 px/pt, a
                # 14-pt disc = the smallest board's x badge) by more than tau against the frame it replaces
                if eff >= P["min_px"] + 16:
                    break
            else:
                below_floor += 1
                continue
            new[j] = (fr[j][0], im)
            # the definition's premise, "i-1 ~= i+1" in the glitch's region: how much of the region itself changes across
            # the injected frame in the ORIGINAL clip (a real transition, zoom or slide under the glitch)
            x0, y0, x1, y1 = [int(v) for v in bbox]
            under = float((cheb(fr[j - 1][1][y0:y1, x0:x1], fr[j + 1][1][y0:y1, x0:x1]) > P["tau"]).mean())
            inj[j] = {"kind": kind, "bbox_px": [int(v) for v in bbox], "eff_px": eff, "under_change": round(under, 3),
                      "in_definition": under <= 0.25}
        res = analyse(iter(new), P, label=os.path.basename(c) + "-inj", trace=True)
        found = {j: None for j in inj}
        extra = []
        for b in res["blips"]:
            hit = [j for j in inj if b["raw_frame"] == j and overlaps(b["bbox_pt"], inj[j]["bbox_px"], s)]
            if hit:
                for j in hit:
                    if found[j] != "blip":
                        found[j] = b["tier"]
            else:
                extra.append(b)
        for j, v in inj.items():
            key = "in_definition" if v["in_definition"] else "in_transition"
            scope[key][0] += 1
            scope[key][1] += int(bool(found[j]))
            per_kind[v["kind"]][0] += 1
            per_kind[v["kind"]][1] += int(bool(found[j]))
            v["caught_as"] = found[j] or None
        inj_total += len(inj)
        caught_total += sum(1 for v in found.values() if v)
        tiers["blip"] += sum(1 for v in found.values() if v == "blip")
        tiers["suspect"] += sum(1 for v in found.values() if v == "suspect")
        missed = [dict(frame=j, **inj[j]) for j in inj if not found[j]]
        # detections away from the injected frames: those are false positives of the injected run too
        extra_fp = [b for b in extra if all(abs(b["raw_frame"] - j) > 2 for j in inj)]
        print(f"INJ   {c}: injected {len(inj)}  caught {sum(1 for v in found.values() if v)}  missed {len(missed)}  "
              f"other detections {len(extra)} (away from injections: {len(extra_fp)})")
        for m in missed:
            why = sorted({tr["why"] for tr in res["stats"]["trace"]
                          if tr["raw_frame"] == m["frame"] and overlaps(tr["bbox_pt"], m["bbox_px"], s)}) or ["no candidate blob"]
            m["why"] = why
            print(f"    MISSED frame {m['frame']} kind {m['kind']} bbox_px {m['bbox_px']} eff_px {m['eff_px']}  "
                  f"under_change {m['under_change']} ({'in definition' if m['in_definition'] else 'during a transition'})  "
                  f"rejected by {why}")
        res["stats"].pop("trace", None)
        fp_total += len(extra_fp)
        report["clips"].append({"clip": c, "frames": clean["frames"], "unique": clean["unique_frames"], "clean_blips": clean["blips"],
                                "clean_stats": clean["stats"], "injected": len(inj), "caught": sum(1 for v in found.values() if v),
                                "injections": {str(j): v for j, v in inj.items()},
                                "missed": missed, "extra_detections": extra, "extra_fp": extra_fp})
    report.update({"false_positives": fp_total, "injected": inj_total, "caught": caught_total, "caught_by_tier": tiers,
                   "below_floor_skipped": below_floor,
                   "per_kind": {k: {"injected": v[0], "caught": v[1]} for k, v in per_kind.items()},
                   "scope": {k: {"injected": v[0], "caught": v[1]} for k, v in scope.items()},
                   "pass": fp_total == 0 and scope["in_definition"][1] == scope["in_definition"][0] > 0})
    print("per kind:", {k: f"{v[1]}/{v[0]}" for k, v in per_kind.items()}, " caught as:", tiers)
    print(f"blipscan selftest: false positives {fp_total} (need 0); caught {scope['in_definition'][1]}/"
          f"{scope['in_definition'][0]} one-frame blips whose region satisfies i-1 ~= i+1 (need 100 %); informative: "
          f"{scope['in_transition'][1]}/{scope['in_transition'][0]} injected on top of a real transition in the same region; "
          f"all {caught_total}/{inj_total} -> {'PASS' if report['pass'] else 'FAIL'}")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(report, f, indent=1)
    return 0 if report["pass"] else 1


def cmd_survey(args):
    P = params_from(args)
    bad = 0
    rows = []
    for c in args.clips:
        r = analyse(read_frames(c, P["width"]), P, label=os.path.basename(c), evidence=args.evidence)
        bad += len(r["blips"])
        rows.append({"clip": c, "frames": r["frames"], "unique": r["unique_frames"], "blips": r["blips"], "stats": r["stats"]})
        nb = sum(1 for b in r["blips"] if b["tier"] == "blip")
        print(f"{c}: {r['frames']} frames ({r['unique_frames']} unique)  blips {nb}  suspects {len(r['blips']) - nb}  "
              f"{r['stats']}  [{r['seconds']} s]")
        for b in r["blips"]:
            print(fmt(b))
    if args.out:
        with open(args.out, "w") as f:
            json.dump({"params": P, "clips": rows, "blips_total": bad}, f, indent=1)
    print(f"survey: {bad} detections over {len(args.clips)} clips")
    return 0 if bad == 0 else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("scan")
    s.add_argument("inputs", nargs="+")
    s.add_argument("--start", type=float)
    s.add_argument("--end", type=float)
    s.add_argument("--out")
    s.add_argument("--evidence")
    s.add_argument("--ignore", help='JSON list of {"t0","t1","rect":[x,y,w,h] pt,"why"}: known legit one-frame effects '
                   '(confetti, coin flights); ignored blips are still listed in the report under "ignored"')
    add_params(s)
    t = sub.add_parser("selftest")
    t.add_argument("--clips", nargs="*")
    t.add_argument("--n-per-clip", dest="n_per_clip", type=int, default=40)
    t.add_argument("--seed", type=int, default=552)
    t.add_argument("--out")
    t.add_argument("--evidence")
    add_params(t)
    v = sub.add_parser("survey")
    v.add_argument("clips", nargs="+")
    v.add_argument("--out")
    v.add_argument("--evidence")
    add_params(v)
    args = ap.parse_args(argv)
    if args.cmd == "scan":
        return cmd_scan(args)
    if args.cmd == "selftest":
        return cmd_selftest(args)
    if args.cmd == "survey":
        return cmd_survey(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
