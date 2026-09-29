#!/usr/bin/env python3
"""Measure the board obstacles on the untinted runner shots (looked at only; nothing here is traced or sampled into
an asset). Prints the geometry that art/STYLE.md §A records and writes art/tools/obstacles_measured.json.

    ~/.venvs/mf3d/bin/python art/tools/measure_obstacles.py            # all
    ~/.venvs/mf3d/bin/python art/tools/measure_obstacles.py door key   # some

Lattice per level from research/levels/L0NN.json (pitch_pt, origin_pt = centre of cell (0, 0)); shots are 1178 px
wide for 393 pt (pt = px x 393 / 1178). Every size is reported in px, in pt and as a FRACTION OF THE PITCH (the
board scales with the zoom, so the engine and the generators work in pitch units).

Measured objects
  door   L33 (027) five doors 4 cells wide x 4/8/12/16/20 tall; L34 (036) and L37 (052) for the other sizes
  lock   the purple hexagon lock + its blue socket (L33 doors)
  key    the gold key + purple ribbon on a key arrow (L33 vertical, L34/L37 horizontal)
  tape   pink tape: 4 lanes (L32 003, V and H), 2 lanes (L38 056, H)
  pipe   the blue tube, its gold mouths and the orange counter box (L35 042, L36 047, L38 056)
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
SHOTS = os.path.join(APP, "research", "shots")
LEVELS = os.path.join(APP, "research", "levels")
K = 1178 / 393.0  # px per pt on the phone shots

OUT = {}


def load(shot):
    return np.asarray(Image.open(os.path.join(SHOTS, shot)).convert("RGB")).astype(np.int32)


def lattice(level):
    d = json.load(open(os.path.join(LEVELS, f"L{level:03d}.json")))
    p = d["pitch_pt"] * K
    ox, oy = d["origin_pt"][0] * K, d["origin_pt"][1] * K
    return dict(pitch_px=p, ox=ox, oy=oy, pitch_pt=d["pitch_pt"], cols=d["cols"], rows=d["rows"], json=d)


def hexc(c):
    return "#%02X%02X%02X" % tuple(int(v) for v in c)


def runs(line, tol=16):
    """Run-length segmentation of a pixel line by colour change -> [(start, end, hex median)]."""
    out, s = [], 0
    for i in range(1, len(line) + 1):
        if i == len(line) or np.abs(line[i] - line[s]).max() > tol:
            out.append((s, i - 1, hexc(np.median(line[s:i], 0))))
            s = i
    return out


def comps(mask, min_area):
    lab, n = ndimage.label(mask)
    res = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        area = int((lab[sl] == i + 1).sum())
        if area >= min_area:
            res.append(dict(x0=sl[1].start, x1=sl[1].stop, y0=sl[0].start, y1=sl[0].stop, area=area, label=i + 1))
    return res, lab


def cell_edges(L, c0, r0, c1, r1):
    """Outer pixel edges of the cell block [c0..c1] x [r0..r1]."""
    p = L["pitch_px"]
    return (L["ox"] + (c0 - 0.5) * p, L["oy"] + (r0 - 0.5) * p, L["ox"] + (c1 + 0.5) * p, L["oy"] + (r1 + 0.5) * p)


def to_cells(L, x0, y0, x1, y1):
    p = L["pitch_px"]
    c0 = round((x0 - L["ox"]) / p + 0.5 - 0.25); c1 = round((x1 - L["ox"]) / p - 0.5 + 0.25)
    r0 = round((y0 - L["oy"]) / p + 0.5 - 0.25); r1 = round((y1 - L["oy"]) / p - 0.5 + 0.25)
    return c0, r0, c1, r1


# ------------------------------------------------------------------ doors

def orange_mask(im):
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    return (R > 190) & (G > 95) & (G < 205) & (B < 90) & (R - B > 150)


def measure_doors(shot, level, tag):
    im = load(shot)
    L = lattice(level)
    p = L["pitch_px"]
    cs, _ = comps(orange_mask(im), int(3 * p * p * 0.25))
    doors = []
    for c in sorted(cs, key=lambda c: (c["x0"], c["y0"])):
        w, h = c["x1"] - c["x0"], c["y1"] - c["y0"]
        if w < 1.5 * p or h < 1.5 * p:
            continue  # keys
        c0, r0, c1, r1 = to_cells(L, c["x0"], c["y0"], c["x1"], c["y1"])
        if c0 < 0 or r0 < 0 or c1 >= L["cols"] + 1 or r1 >= L["rows"] + 1:
            continue  # HUD art (the coin), not a door
        ex0, ey0, ex1, ey1 = cell_edges(L, c0, r0, c1, r1)
        d = dict(shot=shot, cells=[c0, r0, c1 - c0 + 1, r1 - r0 + 1], bbox_px=[c["x0"], c["y0"], c["x1"], c["y1"]],
                 inset_px=dict(l=round(c["x0"] - ex0, 1), t=round(c["y0"] - ey0, 1), r=round(ex1 - c["x1"], 1),
                               b=round(ey1 - c["y1"], 1)))
        d["inset_pitch"] = {k: round(v / p, 3) for k, v in d["inset_px"].items()}
        doors.append(d)
    print(f"\n[door] {tag}: {shot} pitch {p:.2f} px ({L['pitch_pt']} pt); {len(doors)} doors (orange frame bbox)")
    for d in doors:
        print(f"  cells (c,r,w,h) {d['cells']}  bbox {d['bbox_px']}  inset px {d['inset_px']}  = pitch {d['inset_pitch']}")
    return im, L, doors


def door_profiles(im, L, d):
    """Centre-line profiles of one door: a column clear of the lock (1/4 of the width) and a row through a slat."""
    p = L["pitch_px"]
    x0, y0, x1, y1 = d["bbox_px"]
    xc = int(x0 + 0.27 * (x1 - x0))
    col = runs(im[y0 - 4:min(y1 + 8, im.shape[0]), xc], 14)
    col = [(a + y0 - 4, b + y0 - 4, c) for a, b, c in col]
    # a row through the middle of the 2nd slat from the bottom
    yr = int(y1 - 1.5 * p)
    row = runs(im[yr, x0 - 6:x1 + 6], 14)
    row = [(a + x0 - 6, b + x0 - 6, c) for a, b, c in row]
    return xc, col, yr, row


def slat_seams(im, x, y0, y1):
    """Dark seam rows of the shutter along column x: local minima of luminance below the slat face."""
    col = im[y0:y1, x].astype(float)
    lum = col @ np.array([0.3, 0.59, 0.11])
    seams = []
    for i in range(2, len(lum) - 2):
        if lum[i] < 120 and lum[i] <= lum[i - 1] and lum[i] <= lum[i + 1] and lum[i] < lum[i - 2] - 20 and lum[i] < lum[i + 2] - 20:
            seams.append(y0 + i)
    return seams


def measure_door_detail(im, L, doors, tag):
    p = L["pitch_px"]
    res = dict(level_pitch_px=round(p, 3), doors=doors)
    # the tallest door gives the cleanest header / slat profile
    d = max(doors, key=lambda d: d["bbox_px"][3] - d["bbox_px"][1])
    x0, y0, x1, y1 = d["bbox_px"]
    xc, col, yr, row = door_profiles(im, L, d)
    print(f"  tallest door {d['cells']}: column x={xc}")
    for a, b, c in col[:24]:
        print(f"    y {a}-{b} ({b - a + 1}) {c}")
    print(f"  row y={yr} (a slat face)")
    for a, b, c in row:
        print(f"    x {a}-{b} ({b - a + 1}) {c}")
    seams = slat_seams(im, xc, y0 + int(0.9 * p), y1 - 4)
    edges = [L["oy"] + (r - 0.5) * p for r in range(0, 60)]
    ph = [round(min((s - e for e in edges), key=abs), 1) for s in seams]
    per = np.diff(seams).tolist()
    print(f"  slat seams {seams}\n    period px {per}  (pitch {p:.2f})  offset vs the row edge {ph}")
    res.update(slat_seams=seams, slat_period_px=per, slat_phase_px=ph)
    # rivets: bright gold discs in the header
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    riv = []
    for dd in doors:
        a0, b0, a1, b1 = dd["bbox_px"]
        hdr = (slice(b0, b0 + int(0.8 * p)), slice(a0, a1))
        m = (R[hdr] > 245) & (G[hdr] > 200) & (B[hdr] < 170)
        cs, lab = comps(m, 6)
        for c in cs:
            cx = a0 + (c["x0"] + c["x1"]) / 2; cy = b0 + (c["y0"] + c["y1"]) / 2
            riv.append(dict(door=dd["cells"], cx_off=round(cx - a0, 1), cx_off_r=round(a1 - cx, 1), cy_off=round(cy - b0, 1),
                            bright_w=c["x1"] - c["x0"]))
    print("  rivet highlight blobs (offset from the frame's left/right and top edges, px):")
    for r_ in riv:
        print("   ", r_)
    res["rivets"] = riv
    OUT.setdefault("door", {})[tag] = res
    return d


def purple_mask(im):
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    return (B > 120) & (R > 80) & (G < 130) & (R - G > 50) & (B - G > 70)


def measure_lock(im, L, doors, tag):
    """The hex lock: the purple component that does not touch the door's inner frame, inside each door."""
    p = L["pitch_px"]
    locks = []
    for d in doors:
        x0, y0, x1, y1 = d["bbox_px"]
        sub = im[y0:y1, x0:x1]
        m = purple_mask(sub)
        cs, lab = comps(m, 200)
        best = None
        for c in cs:
            if c["x0"] > 0.2 * (x1 - x0) and c["x1"] < 0.8 * (x1 - x0) + 60 and c["y0"] > 0.5 * p:
                if best is None or c["area"] > best["area"]:
                    best = c
        if not best:
            continue
        cx = x0 + (best["x0"] + best["x1"]) / 2; cy = y0 + (best["y0"] + best["y1"]) / 2
        w, h = best["x1"] - best["x0"], best["y1"] - best["y0"]
        # the blue socket around it: along the centre row, darker blue than the slat face
        rowl = runs(im[int(cy), int(cx - w):int(cx + w)], 14)
        locks.append(dict(door=d["cells"], w_px=w, h_px=h, w_pitch=round(w / p, 3), h_pitch=round(h / p, 3),
                          centre_dx_pitch=round((cx - (x0 + x1) / 2) / p, 3), centre_dy_pitch=round((cy - (y0 + y1) / 2) / p, 3),
                          centre_px=[round(cx, 1), round(cy, 1)]))
    print(f"\n[lock] {tag}: purple hexagon bbox (w x h) and centre vs the door frame centre, in pitch")
    for l_ in locks:
        print("  ", l_)
    if locks:
        l0 = max(locks, key=lambda l_: l_["w_px"])
        cx, cy = l0["centre_px"]
        print("  centre row through the lock:")
        for a, b, c in runs(im[int(cy), int(cx - 0.9 * p):int(cx + 0.9 * p)], 14):
            print(f"    x {a + int(cx - 0.9 * p)}-{b + int(cx - 0.9 * p)} ({b - a + 1}) {c}")
        print("  centre column through the lock (keyhole):")
        for a, b, c in runs(im[int(cy - 0.9 * p):int(cy + 0.9 * p), int(cx)], 14):
            print(f"    y {a + int(cy - 0.9 * p)}-{b + int(cy - 0.9 * p)} ({b - a + 1}) {c}")
        # the hexagon shape: row half-widths from top to bottom
        x0 = int(cx - 0.9 * p); y0 = int(cy - 0.9 * p)
        sub = purple_mask(im[y0:int(cy + 0.9 * p), x0:int(cx + 0.9 * p)])
        widths = [(y0 + i, int(r.sum())) for i, r in enumerate(sub) if r.sum() > 0]
        print("  purple row widths (y, px) every 4 rows:", widths[::4])
        OUT.setdefault("lock", {})[tag] = dict(locks=locks, row_widths=widths)


# ------------------------------------------------------------------ key

def gold_mask(im):
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    return (R > 200) & (G > 110) & (G < 225) & (B < 110) & (R - B > 120)


def measure_key(shot, level, box, tag):
    im = load(shot)
    L = lattice(level)
    p = L["pitch_px"]
    x0, y0, x1, y1 = box
    sub = im[y0:y1, x0:x1]
    g = gold_mask(sub)
    pu = purple_mask(sub)
    both = g | pu
    ys, xs = np.nonzero(both)
    gy, gx = np.nonzero(g)
    py_, px_ = np.nonzero(pu)
    bb = [int(x0 + xs.min()), int(y0 + ys.min()), int(x0 + xs.max() + 1), int(y0 + ys.max() + 1)]
    gb = [int(x0 + gx.min()), int(y0 + gy.min()), int(x0 + gx.max() + 1), int(y0 + gy.max() + 1)]
    pb = [int(x0 + px_.min()), int(y0 + py_.min()), int(x0 + px_.max() + 1), int(y0 + py_.max() + 1)]
    W, H = bb[2] - bb[0], bb[3] - bb[1]
    res = dict(shot=shot, bbox_px=bb, w_pitch=round(W / p, 3), h_pitch=round(H / p, 3), gold_bbox=gb, ribbon_bbox=pb,
               pitch_px=round(p, 2))
    vertical = H > W
    # the ring: the gold component rows/cols with a hole (a run of non-gold between two gold runs)
    if vertical:
        prof = [(y0 + i, int(r.sum())) for i, r in enumerate(g)]
    else:
        prof = [(x0 + i, int(c.sum())) for i, c in enumerate(g.T)]
    res["gold_profile_every3"] = prof[::3]
    # arrow line: black pixels in the box -> the shaft centre line
    blk = (sub.sum(-1) < 120)
    if vertical:
        cols = np.nonzero(blk.sum(0) > 0.3 * blk.shape[0])[0]
        res["arrow_line_px"] = float(x0 + cols.mean()) if len(cols) else None
    else:
        rows = np.nonzero(blk.sum(1) > 0.3 * blk.shape[1])[0]
        res["arrow_line_px"] = float(y0 + rows.mean()) if len(rows) else None
    print(f"\n[key] {tag}: {shot} bbox {bb} = {W} x {H} px = {W / p:.3f} x {H / p:.3f} pitch; gold {gb}; ribbon {pb}; "
          f"arrow line at {res['arrow_line_px']}")
    print("  gold count per line (every 3rd):", res["gold_profile_every3"])
    # the ring hole: along the arrow line, the gold runs
    if vertical:
        xl = int(round(res["arrow_line_px"] + 0.28 * p))
        line = runs(im[bb[1]:bb[3], xl], 18)
        print(f"  column x={xl} (right of the shaft):")
        for a, b, c in line:
            print(f"    y {a + bb[1]}-{b + bb[1]} ({b - a + 1}) {c}")
    OUT.setdefault("key", {})[tag] = res


# ------------------------------------------------------------------ tape

def pink_mask(im):
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    return (R > 170) & (G < 150) & (B > 70) & (B < 200) & (R - G > 90)


def measure_tape(shot, level, tag):
    im = load(shot)
    L = lattice(level)
    p = L["pitch_px"]
    cs, _ = comps(pink_mask(im), int(0.3 * p * p))
    tapes = []
    for c in cs:
        w, h = c["x1"] - c["x0"], c["y1"] - c["y0"]
        long_, short = max(w, h), min(w, h)
        lanes = round((long_ / p - 0.47) + 1)
        tapes.append(dict(bbox_px=[c["x0"], c["y0"], c["x1"], c["y1"]], w=w, h=h, orient="V" if h > w else "H",
                          long_pitch=round(long_ / p, 3), short_pitch=round(short / p, 3), lanes=lanes,
                          long_minus_lanes=round(long_ / p - (lanes - 1), 3)))
    print(f"\n[tape] {tag}: {shot} pitch {p:.2f} px")
    for t in tapes:
        print("  ", t)
    # strap angle on the biggest: the X's bright straps (R > 245) principal directions
    OUT.setdefault("tape", {})[tag] = dict(pitch_px=round(p, 3), tapes=tapes)
    if tapes:
        t = max(tapes, key=lambda t: t["w"] * t["h"])
        x0, y0, x1, y1 = t["bbox_px"]
        mid = (y0 + y1) // 2 if t["orient"] == "V" else (x0 + x1) // 2
        if t["orient"] == "V":
            line = runs(im[mid, x0 - 4:x1 + 4], 16)
            print(f"  row y={mid} across the band:")
            for a, b, c in line:
                print(f"    x {a + x0 - 4}-{b + x0 - 4} ({b - a + 1}) {c}")
        else:
            line = runs(im[y0 - 4:y1 + 8, mid], 16)
            print(f"  column x={mid} across the band:")
            for a, b, c in line:
                print(f"    y {a + y0 - 4}-{b + y0 - 4} ({b - a + 1}) {c}")


# ------------------------------------------------------------------ pipe

def cyan_mask(im):
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    return (B > 200) & (G > 150) & (R < 170) & (B - R > 70)


def measure_pipe(shot, level, tag):
    im = load(shot)
    L = lattice(level)
    p = L["pitch_px"]
    cs, lab = comps(cyan_mask(im), int(0.5 * p * p))
    print(f"\n[pipe] {tag}: {shot} pitch {p:.2f} px; tube components (cyan):")
    res = dict(pitch_px=round(p, 3), tubes=[])
    for c in cs:
        m = lab[c["y0"]:c["y1"], c["x0"]:c["x1"]] == c["label"]
        # tube width: the modal run length of the mask along rows and columns
        rw = [int(r.sum()) for r in m if 0 < r.sum() < 2 * p]
        cw = [int(col.sum()) for col in m.T if 0 < col.sum() < 2 * p]
        wmode = np.bincount(rw + cw).argmax() if (rw or cw) else 0
        t = dict(bbox_px=[c["x0"], c["y0"], c["x1"], c["y1"]], width_px=int(wmode), width_pitch=round(wmode / p, 3))
        res["tubes"].append(t)
        print("  ", t)
    # gold caps (mouth rims) and the orange counter box
    gm = gold_mask(im)
    gcs, _ = comps(gm, int(0.05 * p * p))
    print("  gold/orange components (caps, counter box):")
    for c in gcs:
        w, h = c["x1"] - c["x0"], c["y1"] - c["y0"]
        if w > 3 * p or h > 3 * p:
            continue
        print(f"    bbox {[c['x0'], c['y0'], c['x1'], c['y1']]} {w} x {h} px = {w / p:.3f} x {h / p:.3f} pitch")
        res.setdefault("gold", []).append(dict(bbox_px=[c["x0"], c["y0"], c["x1"], c["y1"]], w_pitch=round(w / p, 3), h_pitch=round(h / p, 3)))
    OUT.setdefault("pipe", {})[tag] = res
    return im, L, res


def main():
    want = set(sys.argv[1:]) or {"door", "lock", "key", "tape", "pipe"}
    if want & {"door", "lock"}:
        for shot, level, tag in (("027-L33-start.png", 33, "L33"), ("036-L034-start.png", 34, "L34"), ("052-L037-start.png", 37, "L37")):
            im, L, doors = measure_doors(shot, level, tag)
            if "door" in want:
                measure_door_detail(im, L, doors, tag)
            if "lock" in want:
                measure_lock(im, L, doors, tag)
    if "key" in want:
        measure_key("027-L33-start.png", 33, (40, 805, 130, 955), "L33-down")
        measure_key("027-L33-start.png", 33, (195, 1250, 285, 1400), "L33-up")
        measure_key("052-L037-start.png", 37, (75, 1550, 260, 1625), "L37-right")
        measure_key("036-L034-start.png", 34, (195, 800, 360, 875), "L34-right")
    if "tape" in want:
        measure_tape("003-L32-start.png", 32, "L32")
        measure_tape("056-L038-start.png", 38, "L38")
    if "pipe" in want:
        measure_pipe("042-L035-start.png", 35, "L35")
        measure_pipe("047-L036-start.png", 36, "L36")
        measure_pipe("056-L038-start.png", 38, "L38")
    dst = os.path.join(HERE, "obstacles_measured.json")
    old = json.load(open(dst)) if os.path.exists(dst) else {}
    old.update(OUT)
    json.dump(old, open(dst, "w"), indent=1)
    print("\nwrote", os.path.relpath(dst, APP))


if __name__ == "__main__":
    main()
