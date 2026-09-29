#!/usr/bin/env python3
"""Maze Out perception bot (research tool, phone session 1).

  python3 research/bot/bot.py read SHOT.png [--level N] [--tag K]   # read one shot, write overlay, print board
  python3 research/bot/bot.py play --seconds 150 --level N [--gap 0.25] [--max-rounds R] [--dry]   # first, slow loop (kept)
  python3 research/bot/bot.py play2 --level N [--seconds 170] [--stop-key] [--ignore-anomalies]   # FAST loop used from L33 on:
        one read → whole greedy schedule (tape bundles, pipe teleports, door blockers) in ONE 'phone taps' call → re-read
  python3 research/bot/go.py LEVEL NNN [--here]   # home → Play → start shot → read/dump → play2 → end popup → Continue → home
  python3 research/bot/bot.py dump SHOT.png --level N [--zoom fit] [--timer 180] [--hearts 3] [--tag "Hard Level"]

Board model (measured on L32, 003-L32-start.png, shot = 1178x2556 px, pt = px*393/1178):
  * arrows = black (0,0,0) strokes, ~12 px (4 pt) wide at fit zoom, round caps; the stroke joins CELL CENTRES of a hidden
    square grid (pitch ~53.5 px = 17.9 pt at fit zoom on L32);
  * a tail ends exactly at its cell centre (round cap radius = half stroke);
  * the head is a filled triangle whose tip is ~0.37 pitch beyond the head cell centre, base ~0.2 pitch behind it;
  * obstacles are COLOURED (pink tape etc.) and occlude the ink below: treated as unknown, resolved by straight continuation;
  * faint grey dots (vacated cells) are not ink.
Everything is measured from the image at run time (pitch/origin fitted by a comb fit), so any zoom works.
"""
import json, math, os, subprocess, sys, time
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

PHONE = '/Users/yago/Downloads/app-factory/tools/phonedriver/phone'
ROOT = '/Users/yago/Downloads/app-factory/apps/mazeout/research'
BOT = os.path.join(ROOT, 'bot')
OVL = os.path.join(BOT, 'overlay')
LEVELS = os.path.join(ROOT, 'levels')
LOG = os.path.join(BOT, 'log.jsonl')
TMP = os.path.join(BOT, 'tmp')
SCALE = 1178 / 393.0             # px per pt for 'shot'
BOARD_Y0, BOARD_Y1 = int(125 * SCALE), int(745 * SCALE)   # board band in px (HUD above, boosters below)
DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
DIRNAME = {v: k for k, v in DIRS.items()}

for d in (OVL, LEVELS, TMP):
    os.makedirs(d, exist_ok=True)


def sh(args, timeout=30):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def shot(path):
    r = sh([PHONE, 'shot', path], timeout=30)
    if r.returncode != 0 or not os.path.exists(path):
        raise RuntimeError('shot failed: ' + r.stdout + r.stderr)
    return np.array(Image.open(path).convert('RGB')).astype(np.int16)


def pt(xpx, ypx):
    return xpx / SCALE, ypx / SCALE


# ------------------------------------------------------------------------------------------------ guard
def guard(im):
    """HUD present + not dimmed. Returns (ok, reason, info)."""
    def patch(x0, y0, x1, y1):
        return im[int(y0 * SCALE):int(y1 * SCALE), int(x0 * SCALE):int(x1 * SCALE)].reshape(-1, 3)
    pb = patch(340, 76, 364, 100)                 # pause button (blue)
    blue = (((pb[:, 2] > 110) & (pb[:, 2] > pb[:, 0] + 60)) | ((pb[:, 0] > 170) & (pb[:, 1] < 90) & (pb[:, 2] < 110))).mean()
    pill = patch(150, 60, 245, 72)               # 'Level N' tab / pill (light blue-ish)
    pill_l = pill.mean()
    info = dict(pause_blue=round(float(blue), 3), pill_mean=round(float(pill_l), 1))
    # reference (undimmed, 003): pause blue fraction ~0.6+, pill mean ~ 150-230
    if blue < 0.25:
        return False, 'pause button not found / dimmed', info
    # board background: look for white in the margins of the board band (at fit the margins are white)
    band = im[BOARD_Y0:BOARD_Y1]
    white = (band.min(2) > 240).mean()
    info['white_frac'] = round(float(white), 3)
    if white < 0.35:
        return False, 'board dimmed (white fraction %.2f)' % white, info
    return True, 'ok', info


# ------------------------------------------------------------------------------------------------ perception
def masks(im):
    band = np.zeros(im.shape[:2], bool)
    band[BOARD_Y0:BOARD_Y1] = True
    mx, mn = im.max(2), im.min(2)
    ink = (mx < 100) & band
    # a BUMPED arrow turns red (238,10,19) and stays red for the rest of the level (L47, shots/110): still an arrow → ink
    r_, g_, b_ = im[..., 0].astype(int), im[..., 1].astype(int), im[..., 2].astype(int)
    red = (r_ > 150) & (r_ - g_ > 80) & (np.abs(g_ - b_) < 50) & (g_ < 140) & band
    # its anti-aliased rim (e.g. (249,179,183)) would otherwise be a thin 'unknown' colour blob
    rim = ndimage.binary_dilation(red, iterations=3) & (r_ > 180) & (r_ - g_ > 35) & (np.abs(g_ - b_) < 50) & band
    ink = ink | red | rim
    colour = ((mx - mn) > 60) & band & ~ink
    return ink, colour


def comb_fit(vals, weights, pmin, pmax):
    vals = np.asarray(vals, float); w = np.asarray(weights, float)
    best = []
    ps = np.arange(pmin, pmax, 0.05)
    sc = []
    for p in ps:
        z = (w * np.exp(2j * np.pi * vals / p)).sum() / w.sum()
        sc.append(abs(z))
    sc = np.array(sc)
    return ps, sc


def fit_grid(ink):
    # stroke width: median horizontal run length of ink pixels over a few rows
    runs = []
    ys = np.nonzero(ink.any(1))[0]
    for y in ys[::7]:
        row = ink[y]
        d = np.diff(np.concatenate([[0], row.astype(int), [0]]))
        s, e = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        runs += list(e - s)
    runs = np.array(runs)
    stroke = float(np.median(runs[(runs > 3) & (runs < 40)])) if len(runs) else 12.0
    L = max(9, int(round(stroke * 2.2)))
    vert = ndimage.binary_opening(ink, structure=np.ones((L, 1), bool))
    horz = ndimage.binary_opening(ink, structure=np.ones((1, L), bool))
    # thin segments only (strokes, not heads): components of vert / horz
    xs, xw, ys_, yw = [], [], [], []
    lab, n = ndimage.label(vert)
    for sl in ndimage.find_objects(lab):
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        if w <= stroke * 1.6 and h >= L:
            xs.append((sl[1].start + sl[1].stop - 1) / 2.0); xw.append(h)
    lab, n = ndimage.label(horz)
    for sl in ndimage.find_objects(lab):
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        if h <= stroke * 1.6 and w >= L:
            ys_.append((sl[0].start + sl[0].stop - 1) / 2.0); yw.append(w)
    if len(xs) < 2 or len(ys_) < 2:
        raise RuntimeError('too few strokes to fit a grid')
    pmin, pmax = max(stroke * 2.2, 14), 200
    ps, sx = comb_fit(xs, xw, pmin, pmax)
    _, sy = comb_fit(ys_, yw, pmin, pmax)
    sc = (sx * len(xs) + sy * len(ys_)) / (len(xs) + len(ys_))
    top = sc.max()
    cand = np.nonzero(sc >= 0.93 * top)[0]
    p = ps[cand.max()]
    # local refine around p
    i = cand.max()
    lo, hi = max(0, i - 40), min(len(ps), i + 40)
    p = ps[lo + int(np.argmax(sc[lo:hi]))]

    def origin(vals, w):
        z = (np.asarray(w) * np.exp(2j * np.pi * np.asarray(vals) / p)).sum()
        return (np.angle(z) / (2 * np.pi) * p) % p
    x0, y0 = origin(xs, xw), origin(ys_, yw)
    # least-squares refine pitch + origins with integer assignments
    kx = np.round((np.array(xs) - x0) / p); ky = np.round((np.array(ys_) - y0) / p)
    A = np.zeros((len(xs) + len(ys_), 3)); b = np.zeros(len(xs) + len(ys_)); W = np.concatenate([xw, yw]).astype(float)
    A[:len(xs), 0] = kx; A[:len(xs), 1] = 1; b[:len(xs)] = xs
    A[len(xs):, 0] = ky; A[len(xs):, 2] = 1; b[len(xs):] = ys_
    sw = np.sqrt(W)
    sol, *_ = np.linalg.lstsq(A * sw[:, None], b * sw, rcond=None)
    p2, x02, y02 = sol
    resid = b - A @ sol
    return dict(pitch=float(p2), x0=float(x02), y0=float(y02), stroke=stroke,
                resid_px=float(np.sqrt(np.average(resid ** 2, weights=W))), comb=float(top))


def read_board(im, fit=None):
    ink, colour = masks(im)
    col_filled = ndimage.binary_fill_holes(ndimage.binary_closing(colour, iterations=3))
    occ = ndimage.binary_dilation(col_filled, iterations=3)
    ink = ink & ~ndimage.binary_dilation(col_filled, iterations=2)   # dark outlines of obstacles are not arrow ink
    if fit is None:
        fit = fit_grid(ink)
    p, X0, Y0, stroke = fit['pitch'], fit['x0'], fit['y0'], fit['stroke']
    H, W = ink.shape
    ys, xs = np.nonzero(ink | colour)
    if len(xs) == 0:
        return dict(fit=fit, arrows=[], cells={}, bounds=None, anomalies=['empty board'], occl=[])
    c_lo = int(math.floor((xs.min() - X0) / p)) - 0
    c_hi = int(math.ceil((xs.max() - X0) / p)) + 0
    r_lo = int(math.floor((ys.min() - Y0) / p)) - 0
    r_hi = int(math.ceil((ys.max() - Y0) / p)) + 0
    # renumber so that the leftmost/topmost possibly-used centre is 0 later
    rad = max(2, int(stroke * 0.3))

    def C(c, r):
        return X0 + c * p, Y0 + r * p

    def win(m, x, y, rr):
        xi, yi = int(round(x)), int(round(y))
        if yi - rr < 0 or xi - rr < 0 or yi + rr + 1 > H or xi + rr + 1 > W:
            return np.zeros((1, 1), bool)
        return m[yi - rr:yi + rr + 1, xi - rr:xi + rr + 1]

    def status(x, y, rr=rad):
        w = win(ink, x, y, rr)
        if w.mean() >= 0.5:
            return True
        o = win(occ, x, y, rr)
        if o.mean() > 0.3:
            return None
        return False

    cell = {}
    for c in range(c_lo, c_hi + 1):
        for r in range(r_lo, r_hi + 1):
            cell[(c, r)] = status(*C(c, r))
    # pre-pass: cells inside DOOR/PIPE blobs never become arrow cells by inference
    solid = set()
    plab, pn = label_blobs(ndimage.binary_closing(colour, iterations=2), im=im)
    for i, sl in enumerate(ndimage.find_objects(plab)):
        comp = plab[sl] == i + 1
        area = int(comp.sum())
        if area < 150:
            continue
        kind = classify_blob(im[sl][comp], area, p)
        if kind not in ('door', 'pipe'):
            continue
        filled = ndimage.binary_fill_holes(comp)
        for (c, r) in list(cell):
            x, y = C(c, r)
            xi, yi = int(round(x)) - sl[1].start, int(round(y)) - sl[0].start
            if 0 <= xi < filled.shape[1] and 0 <= yi < filled.shape[0] and filled[yi, xi]:
                solid.add((c, r))
                if cell[(c, r)] is None:
                    cell[(c, r)] = False
    edge = {}
    for c in range(c_lo, c_hi + 1):
        for r in range(r_lo, r_hi + 1):
            for dc, dr in ((1, 0), (0, 1)):
                a, b = C(c, r), C(c + dc, r + dr)
                vals = []
                for t in (0.5, 0.62, 0.74, 0.38, 0.26):
                    vals.append(status(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), max(1, rad - 1)))
                if all(v is True for v in vals):
                    e = True
                elif any(v is False for v in vals):
                    e = False
                else:
                    e = None
                edge[((c, r), (c + dc, r + dr))] = e

    def E(u, v):
        k = (u, v) if (u, v) in edge else (v, u)
        return edge.get(k, False)

    def setE(u, v, val):
        k = (u, v) if (u, v) in edge else (v, u)
        edge[k] = val

    # straight-continuation through occluded edges
    occl = []
    for (u, v), val in list(edge.items()):
        if val is not True:
            continue
        for a0, a1 in ((u, v), (v, u)):
            s = (a1[0] - a0[0], a1[1] - a0[1])
            w, run = a1, []
            while True:
                nx = (w[0] + s[0], w[1] + s[1])
                if E(w, nx) is None:
                    run.append((w, nx)); w = nx; continue
                break
            if not run:
                continue
            nx = (w[0] + s[0], w[1] + s[1])
            after = E(w, nx)
            if any(x_ in solid for e_ in run for x_ in e_):
                continue
            if after is True or cell.get(w) is True:
                for e_ in run:
                    setE(*e_, True)
                    for cc in e_:
                        if cell.get(cc) is None:
                            cell[cc] = True
                occl.append([list(run[0][0]), list(w)])
    # key rule: a key lies ALONG a straight arrow segment; bridge the cells under it along its long axis
    key_lock = set()
    klab, kn = label_blobs(colour, im=im)
    for i, sl in enumerate(ndimage.find_objects(klab)):
        comp = klab[sl] == i + 1
        area = int(comp.sum())
        if area < 150 or area > 3.0 * p * p:
            continue
        pix = im[sl][comp]
        rr, gg, bb = pix[:, 0].astype(int), pix[:, 1].astype(int), pix[:, 2].astype(int)
        if ((rr > 200) & (gg > 130) & (gg < 215) & (bb < 90)).mean() < 0.15:
            continue
        y0k, y1k, x0k, x1k = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        horiz = (x1k - x0k) >= (y1k - y0k)
        cx, cy = (x0k + x1k) / 2, (y0k + y1k) / 2
        if horiz:
            r = int(round((cy - Y0) / p))
            cs = [c for c in range(c_lo, c_hi + 1) if x0k - p * 0.6 <= X0 + c * p <= x1k + p * 0.6]
            line = [(c, r) for c in cs]
        else:
            c = int(round((cx - X0) / p))
            rs = [r for r in range(r_lo, r_hi + 1) if y0k - p * 0.6 <= Y0 + r * p <= y1k + p * 0.6]
            line = [(c, r) for r in rs]
        # bridge along the key's axis (between visible ink cells), and forbid perpendicular links out of cells under the key
        if len(line) >= 2:
            inside = [q for q in line if x0k <= C(*q)[0] <= x1k and y0k <= C(*q)[1] <= y1k] if False else None
            filled_k = ndimage.binary_fill_holes(comp)
            under = []
            for q in line:
                xq, yq = C(*q)
                xi, yi = int(round(xq)) - x0k, int(round(yq)) - y0k
                if 0 <= xi < filled_k.shape[1] and 0 <= yi < filled_k.shape[0] and filled_k[yi, xi]:
                    under.append(q)
            idx = [line.index(q) for q in under] if under else []
            if idx:
                lo_, hi_ = max(0, min(idx) - 1), min(len(line) - 1, max(idx) + 1)
                seg = line[lo_:hi_ + 1]
                for u_, v_ in zip(seg[:-1], seg[1:]):
                    if u_ in solid or v_ in solid:
                        continue
                    setE(u_, v_, True)
                    for cc in (u_, v_):
                        cell[cc] = True
                for q in under:
                    for dd in ((0, 1), (0, -1)) if horiz else ((1, 0), (-1, 0)):
                        nq = (q[0] + dd[0], q[1] + dd[1])
                        if (q, nq) in edge or (nq, q) in edge:
                            setE(q, nq, False)
                            key_lock.add((q, nq))
                occl.append(['key-bridge', [list(x) for x in seg]])
    # partially visible edges: every VISIBLE sample is ink and at least one is visible → connected
    for (u, v), val in list(edge.items()):
        if val is not None:
            continue
        if u in solid or v in solid or (u, v) in key_lock or (v, u) in key_lock:
            continue
        a, b = C(*u), C(*v)
        vis = []
        for t in (0.12, 0.2, 0.28, 0.36, 0.64, 0.72, 0.8, 0.88):
            vis.append(status(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), max(1, rad - 1)))
        vv = [x for x in vis if x is not None]
        if len(vv) >= 2 and all(vv):
            edge[(u, v)] = True
            for cc in (u, v):
                if cell.get(cc) is None:
                    cell[cc] = True
            occl.append(['partial', list(u), list(v)])
    for k in list(edge):
        if edge[k] is None:
            edge[k] = False
    hidden = [k for k, v in cell.items() if v is None]
    for k in hidden:
        cell[k] = False

    # graph + components
    adj = {k: [] for k, v in cell.items() if v}
    for (a, b), v in edge.items():
        if v and a in adj and b in adj:
            adj[a].append(b); adj[b].append(a)
    anomalies = []
    seen = set(); arrows = []
    for s0 in sorted(adj):
        if s0 in seen:
            continue
        comp, st = [], [s0]; seen.add(s0)
        while st:
            u = st.pop(); comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v); st.append(v)
        deg = {u: len(adj[u]) for u in comp}
        if any(d > 2 for d in deg.values()):
            anomalies.append('degree>2 at %s' % [list(u) for u in comp if deg[u] > 2])
        ends = [u for u in comp if deg[u] <= 1]
        if len(comp) == 1:
            ends = comp
        if len(ends) != 2 and len(comp) > 1:
            anomalies.append('component without 2 ends (loop?) %s' % [list(u) for u in comp][:6])
            continue
        # head test: ink ~0.28 pitch beyond the end, outward
        heads = []
        for e in ends:
            if len(comp) == 1:
                outs = [DIRS[k] for k in DIRS]
            else:
                nb = adj[e][0]
                outs = [(e[0] - nb[0], e[1] - nb[1])]
            for d in outs:
                x, y = C(*e)
                hx, hy = x + 0.27 * p * d[0], y + 0.27 * p * d[1]
                # width across the stroke at 0.05p behind the centre: triangle base is wide
                bx, by = x - 0.05 * p * d[0], y - 0.05 * p * d[1]
                wcount = 0
                for k in np.linspace(-0.45 * p, 0.45 * p, 31):
                    px_, py_ = bx + k * d[1], by + k * d[0]
                    xi, yi = int(round(px_)), int(round(py_))
                    if 0 <= yi < H and 0 <= xi < W and ink[yi, xi]:
                        wcount += 1
                width = wcount * (0.9 * p / 30)
                tip = win(ink, hx, hy, max(1, rad - 1)).mean() >= 0.5
                tip_hidden = win(occ, hx, hy, max(1, rad - 1)).mean() > 0.3
                heads.append(dict(cell=e, d=d, tip=bool(tip) or bool(tip_hidden), width=width))
        hs = [h for h in heads if h['tip'] and h['width'] > stroke * 1.5]
        if len(comp) == 1 and not hs:
            x_, y_ = C(*comp[0])
            if win(occ, x_, y_, int(p * 0.6)).mean() > 0.05:
                occl.append(['ignored-stub-near-obstacle', list(comp[0])])
                continue
        if len(hs) != 1:
            anomalies.append('arrow %s: %d heads (%s)' % ([list(u) for u in comp][:4], len(hs),
                             [(list(h['cell']), h['tip'], round(h['width'], 1)) for h in heads]))
            if not hs:
                continue
        h = hs[0]
        # order tail -> head
        path = [h['cell']]
        prev = None
        cur = h['cell']
        while True:
            nxt = [v for v in adj[cur] if v != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            path.append(cur)
        path = path[::-1]
        arrows.append(dict(cells=path, dir=DIRNAME[h['d']]))
    # obstacles: coloured blobs
    lab, n = label_blobs(ndimage.binary_closing(colour, iterations=2) & (masks_band(im)), im=im)
    obst = []
    door_cells = set()
    pipes = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        comp = lab[sl] == i + 1
        area = int(comp.sum())
        if area < 150:
            continue
        pix = im[sl][comp]
        mean = pix.mean(0)
        x0, x1, y0, y1 = sl[1].start, sl[1].stop, sl[0].start, sl[0].stop
        filled = ndimage.binary_fill_holes(comp)
        cells_cov = []
        for (c, r) in cell:
            x, y = C(c, r)
            xi, yi = int(round(x)) - x0, int(round(y)) - y0
            if 0 <= xi < x1 - x0 and 0 <= yi < y1 - y0 and filled[yi, xi]:
                cells_cov.append([c, r])
        kind = classify_blob(pix, area, p)
        if kind in ('door', 'box'):
            door_cells |= set(map(tuple, cells_cov))
        if kind == 'pipe':
            tube = set(map(tuple, cells_cov))
            ends = {}
            for (c_, r_) in tube:
                nb = [(c_ + dx, r_ + dy) for dx, dy in DIRS.values() if (c_ + dx, r_ + dy) in tube]
                if len(nb) == 1:
                    ends[(c_, r_)] = (c_ - nb[0][0], r_ - nb[0][1])
            pipes.append(dict(cells=tube, ends=ends))
        obst.append(dict(bbox_px=[int(x0), int(y0), int(x1), int(y1)], area=area,
                         mean_rgb=[int(v) for v in mean], cells=cells_cov, kind=kind))
    # parts of a box (its silver counter ring, digits, corner bolts) are not obstacles of their own
    boxes = [o['bbox_px'] for o in obst if o['kind'] == 'box']
    if boxes:
        def inside(bb):
            return any(bb[0] >= B[0] - 6 and bb[1] >= B[1] - 6 and bb[2] <= B[2] + 6 and bb[3] <= B[3] + 6 for B in boxes)
        drop_pipe_cells = [set(map(tuple, o['cells'])) for o in obst if o['kind'] != 'box' and inside(o['bbox_px']) and o['kind'] == 'pipe']
        for o in obst:
            if o['kind'] != 'box' and inside(o['bbox_px']):
                o['kind'] = 'box_part'
        pipes = [pp for pp in pipes if not any(pp['cells'] == dc for dc in drop_pipe_cells)]
    # session 2 (L65): a box that TOUCHES a door merges into the door blob; its silver counter badge then reads 'unknown'.
    # An unknown blob of < 1.5 cells lying inside a door blob's bbox is such a badge (additive rule; nothing else changes).
    doors_bb = [o['bbox_px'] for o in obst if o['kind'] == 'door']
    for o in obst:
        bb = o['bbox_px']
        if o['kind'] == 'unknown' and o['area'] < 1.5 * p * p and any(
                bb[0] >= B[0] and bb[1] >= B[1] and bb[2] <= B[2] and bb[3] <= B[3] for B in doors_bb):
            o['kind'] = 'box_part'
    for a_i, a in enumerate(arrows):
        a['id'] = a_i
    bounds = [c_lo, r_lo, c_hi, r_hi]
    # an 'arrow' whose cells all sit inside a door is door artwork, not an arrow
    arrows = [a for a in arrows if not all(tuple(c) in door_cells for c in a['cells'])]
    for a_i, a in enumerate(arrows):
        a['id'] = a_i
    for pp in pipes:
        if len(pp['ends']) != 2:
            anomalies.append('pipe with %d ends (cells %s)' % (len(pp['ends']), sorted(pp['cells'])[:8]))
    return dict(fit=fit, arrows=arrows, bounds=bounds, anomalies=anomalies, occl=occl, obstacles=obst,
                hidden=[list(h) for h in hidden], door_cells=sorted([list(c) for c in door_cells]), pipes=pipes)


def masks_band(im):
    band = np.zeros(im.shape[:2], bool)
    band[BOARD_Y0:BOARD_Y1] = True
    return band


def classify_blob(pix, area, p):
    r, g, b = pix[:, 0].astype(int), pix[:, 1].astype(int), pix[:, 2].astype(int)
    pink = ((r > 200) & (g < 120) & (b > 100) & (b < 190)).mean()
    blue = ((b > 200) & (r < 160) & (g > 120)).mean()
    gold = ((r > 200) & (g > 130) & (g < 215) & (b < 90)).mean()
    purple = ((r > 110) & (b > 170) & (g < 110)).mean()
    if pink > 0.5:
        return 'tape_pink'
    if area > 2.5 * p * p and purple > 0.3 and blue < 0.1:
        return 'box'            # L50: purple slab with a silver counter; 'Clear required amount of arrows to break the BOX!'
    if area > 2.5 * p * p and blue > 0.25 and purple > 0.02:
        return 'door'
    if blue > 0.25 and purple <= 0.02:
        return 'pipe'
    if area < 3.0 * p * p and gold > 0.15 and purple > 0.03:
        return 'key'
    if area < 1.0 * p * p and purple > 0.4:
        return 'key'           # a key's purple ring split off when the gold body merged into a touching pipe (L49)
    return 'unknown'


def label_blobs(mask, erode=9, small_px=12000, im=None):
    """Label colour blobs, splitting blobs that touch through thin necks (a key ring touching a pipe): erode, label, then give
    every mask pixel the label of the nearest eroded core."""
    core = ndimage.binary_erosion(mask, iterations=erode)
    lab, n = ndimage.label(core)
    if n == 0:
        return ndimage.label(mask)
    dist, (iy, ix) = ndimage.distance_transform_edt(lab == 0, return_indices=True)
    full = lab[iy, ix] * mask * (dist <= erode + 1)
    # tiny blobs that vanished under the erosion keep their own labels
    rest = mask & (full == 0)
    rl, rn = ndimage.label(rest)
    full = np.where(rest, rl + n, full)
    N = n + rn
    # re-merge SMALL pieces that touch each other (a key's ring + body): union-find over adjacent small labels
    sizes = ndimage.sum(mask, full, range(1, N + 1))
    small = {i + 1 for i, sz in enumerate(sizes) if 0 < sz < small_px}
    parent = list(range(N + 1))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    objs = ndimage.find_objects(full)
    hue = {}
    def hclass(i):
        if i in hue:
            return hue[i]
        sl = objs[i - 1]
        h = 'x'
        if im is not None and sl is not None:
            px_ = im[sl][full[sl] == i].astype(int)
            if len(px_):
                r_, g_, b_ = px_[:, 0], px_[:, 1], px_[:, 2]
                fr = dict(pink=((r_ > 200) & (g_ < 120) & (b_ > 100) & (b_ < 190)).mean(),
                          gold=((r_ > 200) & (g_ >= 150) & (b_ < 110)).mean(),
                          orange=((r_ > 180) & (g_ > 50) & (g_ < 150) & (b_ < 100)).mean(),
                          purple=((r_ > 110) & (b_ > 170) & (g_ < 110)).mean(),
                          blue=((b_ > 200) & (r_ < 160) & (g_ > 120)).mean())
                h = max(fr, key=fr.get)
        hue[i] = h
        return h
    def compatible(i, j):
        a_, b_ = hclass(i), hclass(j)
        if a_ == b_:
            return True
        return {a_, b_} <= {'gold', 'purple', 'orange'} and 'pink' not in (a_, b_) and not ({a_, b_} == {'orange', 'purple'})
    for i in small:
        sl = objs[i - 1]
        if sl is None:
            continue
        y0, y1 = max(0, sl[0].start - 3), sl[0].stop + 3
        x0, x1 = max(0, sl[1].start - 3), sl[1].stop + 3
        sub = full[y0:y1, x0:x1]
        dil = ndimage.binary_dilation(sub == i, iterations=3)
        for j in np.unique(sub[dil]):
            if j and j != i and j in small and compatible(i, j):
                parent[find(j)] = find(i)
    # an orange/red counter box or gold mouth rim split off a pipe/door merges back into the big blob it touches
    # (but never a key: a group that contains a purple ring piece stays a key)
    grp_purple = {}
    for i in small:
        if hclass(i) == 'purple':
            grp_purple[find(i)] = True
    if im is not None:
        for i in small:
            if grp_purple.get(find(i)):
                continue
            sl = objs[i - 1]
            if sl is None:
                continue
            pix = im[sl][full[sl] == i].astype(int)
            if len(pix) == 0:
                continue
            orange = ((pix[:, 0] > 180) & (pix[:, 1] > 50) & (pix[:, 1] < 215) & (pix[:, 2] < 120)).mean()
            if orange < 0.4:
                continue
            y0, y1 = max(0, sl[0].start - 4), sl[0].stop + 4
            x0, x1 = max(0, sl[1].start - 4), sl[1].stop + 4
            sub = full[y0:y1, x0:x1]
            dil = ndimage.binary_dilation(sub == i, iterations=4)
            bigs = [j for j in np.unique(sub[dil]) if j and j not in small]
            if bigs:
                parent[find(i)] = find(int(bigs[0]))
    remap = np.array([find(x) for x in range(N + 1)])
    return remap[full], N


def classify_colour(mean):
    r, g, b = mean
    if r > 200 and g < 120 and b > 100 and b < 190:
        return 'tape_pink'
    return 'unknown'


# ------------------------------------------------------------------------------------------------ solver
def taped_ids(board):
    ids = set()
    for o in board.get('obstacles', []):
        if o['kind'] == 'tape_pink':
            cs = set(map(tuple, o['cells']))
            for a in board['arrows']:
                if any(tuple(c) in cs for c in a['cells']):
                    ids.add(a['id'])
    return ids


def ray(board, a, info=None):
    """Cells on the head's ray to the board edge. Pipes: entering a pipe END against its outward direction teleports the ray
    to the other end (continuing outward there); hitting a tube cell any other way leaves that cell in the ray (it blocks,
    because pipe cells are in the blocker set via pipe_cells())."""
    c_lo, r_lo, c_hi, r_hi = board['bounds']
    d = DIRS[a['dir']]
    c, r = a['cells'][-1]
    out = []
    pipes = board.get('pipes', [])
    hops = 0
    while True:
        c, r = c + d[0], r + d[1]
        if c < c_lo - 1 or c > c_hi + 1 or r < r_lo - 1 or r > r_hi + 1:
            break
        hit = None
        for k, pp in enumerate(pipes):
            if (c, r) in pp['cells']:
                hit = (k, pp)
                break
        if hit and hops < 4:
            k, pp = hit
            o = pp['ends'].get((c, r))
            if o is not None and (o[0] == -d[0] and o[1] == -d[1]) and len(pp['ends']) == 2:
                other = [e for e in pp['ends'] if e != (c, r)][0]
                d = pp['ends'][other]
                c, r = other
                hops += 1
                if info is not None:
                    info.setdefault('pipes', []).append(k)
                continue
        out.append((c, r))
    return out


def pipe_cells(board):
    s_ = set()
    for pp in board.get('pipes', []):
        s_ |= pp['cells']
    return s_


def apply_overrides(im, board, level):
    """bot/overrides/Lnnn.json: arrows verified by eye that the reader cannot trace (e.g. under a key touching a pipe).
    An override arrow is added while ink is still present at its 'present_if_ink' cells; read pieces inside it are dropped."""
    path = os.path.join(BOT, 'overrides', 'L%03d.json' % level)
    if not level or not os.path.exists(path):
        return board
    ov = json.load(open(path))
    ink, _ = masks(im)
    f = board['fit']; p = f['pitch']
    for oa in ov.get('add_arrows', []):
        cells = [tuple(c) for c in oa['cells']]
        present = True
        for c in oa.get('present_if_ink', [cells[0]]):
            x, y = f['x0'] + c[0] * p, f['y0'] + c[1] * p
            w = ink[int(y) - 3:int(y) + 4, int(x) - 3:int(x) + 4]
            if w.mean() < 0.5:
                present = False
        cs = set(cells)
        board['arrows'] = [a for a in board['arrows'] if not (set(map(tuple, a['cells'])) <= cs)]
        board['anomalies'] = [an for an in board['anomalies'] if not any(('[%d, %d]' % c) in an for c in cells)]
        if present:
            board['arrows'].append(dict(cells=[list(c) for c in cells], dir=oa['dir'], override=True))
    for i, a in enumerate(board['arrows']):
        a['id'] = i
    return board


def free_arrows(board, allow_taped=False):
    occ = {}
    for a in board['arrows']:
        for c in a['cells']:
            occ[tuple(c)] = a['id']
    for c in board.get('door_cells', []):
        occ[tuple(c)] = 'door'
    for c in pipe_cells(board):
        occ[tuple(c)] = 'pipe'
    taped = taped_ids(board)
    res = []
    for a in board['arrows']:
        if a['id'] in taped and not allow_taped:
            continue
        blockers = [occ[c] for c in ray(board, a) if c in occ]
        if not blockers:
            res.append(a)
    return res


def batch(board, frees):
    """Non-interacting subset: no arrow's ray/body touches another's ray/body in the batch."""
    used = set(); out = []
    for a in frees:
        cs = set(map(tuple, a['cells'])) | set(ray(board, a))
        if cs & used:
            continue
        used |= cs; out.append(a)
    return out


def tap_point(board, a):
    """Cell centre on the arrow's body, away from other arrows; never the head cell if the arrow has >1 cell."""
    fit = board['fit']; p = fit['pitch']
    occ = {}
    for b in board['arrows']:
        for c in b['cells']:
            occ[tuple(c)] = b['id']
    cells = [tuple(c) for c in a['cells']]
    cand = cells[:-1] if len(cells) > 1 else cells
    best, bs = None, None
    n = len(cand)
    for i, c in enumerate(cand):
        nb = sum(1 for d in DIRS.values() if occ.get((c[0] + d[0], c[1] + d[1]), a['id']) != a['id'])
        centrality = abs(i - (n - 1) / 2) / max(1, n)
        s = nb + centrality
        if bs is None or s < bs:
            best, bs = c, s
    x = fit['x0'] + best[0] * p; y = fit['y0'] + best[1] * p
    return best, pt(x, y)


def plan(board, max_taps=40):
    """Full greedy schedule from one read: units (arrows, tape groups) tapped in dependency order; a unit is tapped only
    >= G taps after each of its blockers (G by blocker length), since the runner spaces taps ~0.7 s apart."""
    A = {a['id']: a for a in board['arrows']}
    taped = taped_ids(board)
    units = []
    for g in tape_groups(board):
        units.append(dict(ids=g, rep=A[g[0]], tail=True))
    for a in board['arrows']:
        if a['id'] not in taped:
            units.append(dict(ids=[a['id']], rep=a, tail=False))
    cell_unit = {}
    for k, u in enumerate(units):
        u['k'] = k
        u['cells'] = set()
        for i in u['ids']:
            u['cells'] |= set(map(tuple, A[i]['cells']))
        u['rays'] = set()
        for i in u['ids']:
            u['rays'] |= set(ray(board, A[i]))
        for c in u['cells']:
            cell_unit[c] = k
    doors = set(map(tuple, board.get('door_cells', []))) | pipe_cells(board)
    for u in units:
        u['block'] = {cell_unit[c] for c in u['rays'] if c in cell_unit and cell_unit[c] != u['k']}
        u['door'] = bool(u['rays'] & doors)
        inf = {}
        for i in u['ids']:
            ray(board, A[i], inf)
        u['pipe'] = bool(inf.get('pipes'))
    gone, when, seq = set(), {}, []
    while len(seq) < max_taps:
        idx = len(seq)
        cand = [u for u in units if u['k'] not in gone and not u['door'] and u['block'] <= gone]
        if not cand:
            break
        ok = []
        for u in cand:
            good = True
            for b in u['block']:
                L = len(units[b]['cells']) // max(1, len(units[b]['ids']))
                G = 1 if L <= 10 else (2 if L <= 22 else 3)
                if idx - when[b] < G:
                    good = False
            if good:
                ok.append(u)
        if not ok:
            break
        u = ok[0]
        gone.add(u['k']); when[u['k']] = idx; seq.append(u)
        if u['pipe']:
            break          # a pipe passage changes the pipe (counter / break): re-read before planning further
    taps = []
    fit = board['fit']
    for u in seq:
        if u['tail']:
            c = u['rep']['cells'][0]
            xy = pt(fit['x0'] + c[0] * fit['pitch'], fit['y0'] + c[1] * fit['pitch'])
        else:
            c, xy = tap_point(board, u['rep'])
        taps.append((u, tuple(c), xy))
    return taps


def tape_groups(board):
    out = []
    for o in board.get('obstacles', []):
        if o['kind'] != 'tape_pink':
            continue
        cs = set(map(tuple, o['cells']))
        ids = [a['id'] for a in board['arrows'] if any(tuple(c) in cs for c in a['cells'])]
        if ids:
            out.append(ids)
    return out


# ------------------------------------------------------------------------------------------------ overlay
def overlay(im, board, path, note=''):
    img = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))
    img = Image.blend(img, Image.new('RGB', img.size, (255, 255, 255)), 0.55)
    dr = ImageDraw.Draw(img)
    fit = board['fit']; p = fit['pitch']
    C = lambda c, r: (fit['x0'] + c * p, fit['y0'] + r * p)
    if board.get('bounds'):
        c_lo, r_lo, c_hi, r_hi = board['bounds']
        for c in range(c_lo, c_hi + 1):
            for r in range(r_lo, r_hi + 1):
                x, y = C(c, r); dr.point((x, y), fill=(150, 150, 150))
    frees = {a['id'] for a in free_arrows(board)}
    taped = taped_ids(board)
    palette = [(230, 25, 75), (60, 180, 75), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 190, 190),
               (240, 50, 230), (128, 128, 0), (0, 0, 128), (170, 110, 40)]
    for a in board['arrows']:
        col = palette[a['id'] % len(palette)]
        pts_ = [C(*c) for c in a['cells']]
        if len(pts_) > 1:
            dr.line(pts_, fill=col, width=max(3, int(p * 0.14)))
        x, y = pts_[-1]; d = DIRS[a['dir']]
        tip = (x + d[0] * p * 0.4, y + d[1] * p * 0.4)
        l = (x - d[1] * p * 0.22, y + d[0] * p * 0.22); rr = (x + d[1] * p * 0.22, y - d[0] * p * 0.22)
        dr.polygon([tip, l, rr], fill=col)
        tx, ty = C(*a['cells'][0])
        dr.ellipse([tx - 5, ty - 5, tx + 5, ty + 5], outline=col, width=2)
        lab = str(a['id']) + ('F' if a['id'] in frees else '') + ('T' if a['id'] in taped else '')
        mx, my = C(*a['cells'][len(a['cells']) // 2])
        dr.text((mx + 4, my - 14), lab, fill=(0, 0, 0))
    for o in board.get('obstacles', []):
        dr.rectangle(o['bbox_px'], outline=(255, 0, 200) if o['kind'] != 'unknown' else (255, 0, 0), width=3)
        dr.text((o['bbox_px'][0], o['bbox_px'][1] - 14), o['kind'], fill=(200, 0, 150))
    dr.text((20, BOARD_Y0 - 40), 'pitch %.2fpx (%.2fpt) stroke %.1f resid %.2f arrows %d free %d %s' % (
        p, p / SCALE, fit['stroke'], fit['resid_px'], len(board['arrows']), len(frees), note), fill=(0, 0, 0))
    for i, an in enumerate(board.get('anomalies', [])[:8]):
        dr.text((20, BOARD_Y1 + 10 + 16 * i), 'ANOMALY ' + an[:150], fill=(255, 0, 0))
    img.save(path)


# ------------------------------------------------------------------------------------------------ level json
def normalise(board):
    """Cells re-based so the bounding box of all arrow cells starts at (0,0)."""
    cs = [c for a in board['arrows'] for c in a['cells']]
    for o in board.get('obstacles', []):
        cs += [tuple(c) for c in o['cells']]
    if not cs:
        return board, (0, 0), (0, 0)
    c0 = min(c[0] for c in cs); r0 = min(c[1] for c in cs)
    c1 = max(c[0] for c in cs); r1 = max(c[1] for c in cs)
    return (c0, r0), (c1 - c0 + 1, r1 - r0 + 1)


def dump_level(board, level, shot_path, zoom='open', timer=None, hearts=3, tag=None, extra=None, suffix=''):
    (c0, r0), (cols, rows) = normalise(board)
    fit = board['fit']
    if suffix:
        # a later state (e.g. arrows revealed by a door): use the START json's cell frame (same origin_pt) so cells line up
        ref = os.path.join(LEVELS, 'L%03d.json' % level)
        if os.path.exists(ref):
            R_ = json.load(open(ref))
            c0 = int(round((R_['origin_pt'][0] * SCALE - fit['x0']) / fit['pitch']))
            r0 = int(round((R_['origin_pt'][1] * SCALE - fit['y0']) / fit['pitch']))
            cols, rows = R_['cols'], R_['rows']
    arrows = [dict(id=a['id'], cells=[[c - c0, r - r0] for c, r in a['cells']], dir=a['dir']) for a in board['arrows']]
    obst = [dict(kind=o['kind'], cells=[[c - c0, r - r0] for c, r in o['cells']], bbox_px=o['bbox_px'],
                 mean_rgb=o['mean_rgb']) for o in board.get('obstacles', [])]
    taped = taped_ids(board)
    out = dict(level=level, source='recorded', shot=os.path.relpath(shot_path, os.path.dirname(ROOT)), zoom=zoom,
               pitch_pt=round(fit['pitch'] / SCALE, 3), stroke_pt=round(fit['stroke'] / SCALE, 2),
               origin_pt=[round((fit['x0'] + c0 * fit['pitch']) / SCALE, 2), round((fit['y0'] + r0 * fit['pitch']) / SCALE, 2)],
               cols=cols, rows=rows, mask=None,
               arrows=arrows, obstacles=obst, taped_arrow_ids=sorted(taped), timer_s=timer, hearts=hearts, tag=tag,
               anomalies=board.get('anomalies', []), occlusion_inferred=board.get('occl', []))
    if extra:
        out.update(extra)
    path = os.path.join(LEVELS, 'L%03d%s.json' % (level, suffix))
    with open(path, 'w') as f:
        json.dump(out, f, indent=1)
    return path


def log(rec):
    rec['t'] = round(time.time(), 3)
    with open(LOG, 'a') as f:
        f.write(json.dumps(rec) + '\n')


# ------------------------------------------------------------------------------------------------ play loop
def board_diff(a, b):
    A = a[BOARD_Y0:BOARD_Y1].astype(np.int16); B = b[BOARD_Y0:BOARD_Y1].astype(np.int16)
    return float((np.abs(A - B).max(2) > 40).mean())


def settle(prev_path, max_wait=2.5):
    t0 = time.time()
    a = shot(prev_path)
    while time.time() - t0 < max_wait:
        time.sleep(0.4)
        b = shot(prev_path)
        d = board_diff(a, b)
        if d < 0.01 * 0.2:   # < 0.2 % of the band (the band is mostly white; 1 % of it is a big change)
            return b, d
        a = b
    return a, None


def pause_game():
    r = sh([os.path.join(ROOT, 'tools', 'pause.sh')], timeout=40)
    print('pause:', r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr)


def free_groups(board, frees):
    """taped arrows are tappable only when EVERY arrow under the same tape is free (group rule, to be verified)."""
    fr = {a['id'] for a in frees}
    out = []
    for o in board.get('obstacles', []):
        if o['kind'] != 'tape_pink':
            continue
        cs = set(map(tuple, o['cells']))
        ids = [a['id'] for a in board['arrows'] if any(tuple(c) in cs for c in a['cells'])]
        if ids and all(i in fr for i in ids):
            out.append(ids)
    return out


RUN = time.strftime('%H%M%S')
IGNORE_ANOMS = '--ignore-anomalies' in sys.argv
DOORS = {}
LASTFIT = [None]
READFAIL = [0]
TAPPED = [0]
TAPCAP = int(sys.argv[sys.argv.index('--tapcap') + 1]) if '--tapcap' in sys.argv else 0   # stop after N taps in total (clip of the Nth+1)
LEAVE = int(sys.argv[sys.argv.index('--leave') + 1]) if '--leave' in sys.argv else 0   # stop with N arrows left (win clip)


def play(level, seconds=150, gap=0.25, max_rounds=60, dry=False, allow_taped=False, stop_key=False):
    t_end = time.time() + seconds
    rnd = 0
    first_dump = not os.path.exists(os.path.join(LEVELS, 'L%03d.json' % level))
    k = 0
    while time.time() < t_end and rnd < max_rounds:
        rnd += 1
        spath = os.path.join(TMP, 'L%03d-%s-r%02d.png' % (level, RUN, rnd))
        im = shot(spath)
        ok, why, info = guard(im)
        if not ok:
            print('STOP guard: %s %s' % (why, info)); log(dict(level=level, event='guard_stop', why=why, info=info))
            return 'guard'
        board = read_board(im)
        while os.path.exists(os.path.join(OVL, 'L%03d-%d.png' % (level, k))):
            k += 1
        opath = os.path.join(OVL, 'L%03d-%d.png' % (level, k))
        overlay(im, board, opath, note='round %d' % rnd)
        if board['anomalies']:
            pause_game()
            print('STOP anomalies:', board['anomalies'], 'overlay', opath)
            log(dict(level=level, event='anomaly_stop', anomalies=board['anomalies'], overlay=opath))
            return 'anomaly'
        unknown = [o for o in board['obstacles'] if o['kind'] == 'unknown']
        if unknown:
            pause_game()
            print('STOP unknown blob(s):', [(o['bbox_px'], o['mean_rgb']) for o in unknown], 'overlay', opath)
            log(dict(level=level, event='unknown_stop', blobs=[(o['bbox_px'], o['mean_rgb']) for o in unknown]))
            return 'unknown'
        if first_dump and rnd == 1:
            dump_level(board, level, spath)
        if not board['arrows']:
            print('board empty'); return 'empty'
        frees = free_arrows(board, allow_taped=allow_taped)
        groups = free_groups(board, free_arrows(board, allow_taped=True))
        if not frees and not groups:
            pause_game()
            print('STOP no free arrows (%d left); overlay %s' % (len(board['arrows']), opath))
            log(dict(level=level, event='no_free', left=len(board['arrows'])))
            return 'stuck'
        if TAPCAP:
            left_ = TAPCAP - TAPPED[0]
            if left_ <= 0:
                pause_game()
                print('TAPCAP reached (%d taps; game PAUSED); next plan:' % TAPPED[0])
                for u, c, xy in taps[:3]:
                    print('  next unit', u['ids'], u['rep']['dir'], 'tap', [round(v, 1) for v in xy])
                return 'cap'
            taps = taps[:left_]
        if stop_key:
            kc = set()
            for o in board.get('obstacles', []):
                if o['kind'] == 'key':
                    kc |= set(map(tuple, o['cells']))
            kf = [a for a in frees if any(tuple(c) in kc for c in a['cells'])]
            if kf:
                pause_game()
                print('STOP key arrow free:', [(a['id'], a['dir'], tap_point(board, a)) for a in kf], 'overlay', opath)
                return 'key'
        bt = batch(board, frees)
        taps = []
        for a in bt:
            cell, (x, y) = tap_point(board, a)
            taps.append((a, cell, (x, y)))
        used = set()
        for a in bt:
            used |= set(map(tuple, a['cells'])) | set(ray(board, a))
        A = {a['id']: a for a in board['arrows']}
        for g in groups:
            cs = set()
            for i in g:
                cs |= set(map(tuple, A[i]['cells'])) | set(ray(board, A[i]))
            if cs & used:
                continue
            used |= cs
            rep = A[g[0]]; c = rep['cells'][0]; fit = board['fit']
            taps.append((dict(rep, id=rep['id'], group=g), tuple(c), pt(fit['x0'] + c[0] * fit['pitch'], fit['y0'] + c[1] * fit['pitch'])))
        spec = ';'.join('%.1f,%.1f' % (x, y) for _, _, (x, y) in taps)
        print('round %d: %d arrows, %d free, tapping %d: %s' % (rnd, len(board['arrows']), len(frees), len(taps), spec))
        if dry:
            return 'dry'
        r = sh([PHONE, 'taps', spec, str(gap)], timeout=60)
        for a, cell, (x, y) in taps:
            log(dict(level=level, round=rnd, arrow_id=a['id'], group=a.get('group'), cells=a['cells'], dir=a['dir'], tap=[round(x, 1), round(y, 1)],
                     result='tapped', out=r.stdout.strip()[-200:]))
        time.sleep(0.35)
        settle(os.path.join(TMP, 'settle.png'))
    return 'timeout'


def play2(level, seconds=170, max_rounds=40, stop_key=False):
    """Fast loop: one read → whole greedy schedule in ONE 'taps' call → re-read. No settle (exiting arrows are blue, not ink)."""
    t_end = time.time() + seconds
    first_dump = not os.path.exists(os.path.join(LEVELS, 'L%03d.json' % level))
    unknown_retry = 0
    stuck_retry = 0
    for rnd in range(1, max_rounds + 1):
        if time.time() > t_end:
            pause_game(); print('time budget over (paused)'); return 'timeout'
        spath = os.path.join(TMP, 'L%03d-%s-r%02d.png' % (level, RUN, rnd))
        im = shot(spath)
        ok, why, info = guard(im)
        if not ok:
            print('STOP guard: %s %s' % (why, info)); log(dict(level=level, event='guard_stop', why=why, info=info))
            return 'guard'
        try:
            try:
                board = read_board(im)
            except (RuntimeError, ValueError):
                if LASTFIT[0] is None:
                    raise
                board = read_board(im, fit=LASTFIT[0])      # 1-2 arrows left: too few strokes to fit → reuse the last grid
            board = apply_overrides(im, board, level)
            READFAIL[0] = 0
            if len(board['arrows']) >= 4:
                LASTFIT[0] = board['fit']
        except (RuntimeError, ValueError) as e:
            READFAIL[0] += 1
            print('read failed (%s) — board empty/transition?' % e)
            if READFAIL[0] >= 4:
                pause_game(); print('STOP: 4 read failures in a row (paused)'); return 'readfail'
            time.sleep(0.6); continue
        opath = os.path.join(OVL, 'L%03d-%s-r%02d.png' % (level, RUN, rnd))
        unknown = [o for o in board['obstacles'] if o['kind'] == 'unknown']
        if (unknown or (board['anomalies'] and not IGNORE_ANOMS)) and unknown_retry < 3:
            unknown_retry += 1; time.sleep(0.7); continue
        if (board['anomalies'] and not IGNORE_ANOMS) or unknown:
            overlay(im, board, opath, note='round %d' % rnd)
            pause_game()
            print('STOP anomalies/unknown:', board['anomalies'], [(o['bbox_px'], o['mean_rgb']) for o in unknown], 'overlay', opath)
            log(dict(level=level, event='stop', anomalies=board['anomalies'], unknown=[o['bbox_px'] for o in unknown], overlay=opath))
            return 'anomaly'
        unknown_retry = 0
        nd = sum(1 for o in board['obstacles'] if o['kind'] in ('door', 'box'))
        if rnd == 1:
            overlay(im, board, opath, note='round 1')
            DOORS[level] = nd
        elif nd < DOORS.get(level, nd) and not board['anomalies']:
            k = DOORS.get(level) - nd
            dump_level(board, level, spath, suffix='-open%d' % k,
                       extra=dict(note='state after %d door(s) opened (arrows revealed); cells in the START json frame' % k))
            overlay(im, board, os.path.join(OVL, 'L%03d-open%d.png' % (level, k)), note='after %d door(s) opened' % k)
            print('door opened → dumped L%03d-open%d.json' % (level, k))
            DOORS[level] = nd
        if first_dump and rnd == 1:
            dump_level(board, level, spath)
        if not board['arrows']:
            time.sleep(0.5); continue
        taps = plan(board)
        if LEAVE and taps and len(board['arrows']) <= LEAVE + len(taps) and not any(o['kind'] in ('door', 'key') for o in board.get('obstacles', [])):
            keep = max(0, len(board['arrows']) - LEAVE)
            if keep < len(taps):
                taps = taps[:keep]
                if not taps:
                    pause_game()
                    print('LEAVE: %d arrows left untapped for the win clip (game PAUSED)' % len(board['arrows']))
                    for u, c, xy in plan(board):
                        print('  last unit', u['ids'], u['rep']['dir'], 'tap', [round(v, 1) for v in xy])
                    return 'leave'
        if TAPCAP:
            left_ = TAPCAP - TAPPED[0]
            if left_ <= 0:
                pause_game()
                print('TAPCAP reached (%d taps; game PAUSED); next plan:' % TAPPED[0])
                for u, c, xy in taps[:3]:
                    print('  next unit', u['ids'], u['rep']['dir'], 'tap', [round(v, 1) for v in xy])
                return 'cap'
            taps = taps[:left_]
        if stop_key:
            kc = set()
            for o in board.get('obstacles', []):
                if o['kind'] == 'key':
                    kc |= set(map(tuple, o['cells']))
            for j, (u, c, xy) in enumerate(taps):
                if any(tuple(cc) in kc for cc in u['cells']):
                    taps = taps[:j]
                    if not taps:
                        overlay(im, board, opath); pause_game()
                        print('STOP key unit free:', u['ids'], xy); return 'key'
                    break
        if not taps and stuck_retry < 3:
            stuck_retry += 1; time.sleep(0.8); continue
        if not taps:
            overlay(im, board, opath, note='stuck'); pause_game()
            print('STOP stuck (%d arrows left) overlay %s' % (len(board['arrows']), opath))
            log(dict(level=level, event='no_free', left=len(board['arrows']), overlay=opath))
            return 'stuck'
        stuck_retry = 0
        spec = ';'.join('%.1f,%.1f' % xy for _, _, xy in taps)
        print('round %d: %d arrows, tapping %d' % (rnd, len(board['arrows']), len(taps)), flush=True)
        t0 = time.time()
        r = sh([PHONE, 'taps', spec, '0.05'], timeout=300)
        TAPPED[0] += len(taps)
        for u, c, (x, y) in taps:
            log(dict(level=level, round=rnd, ids=u['ids'], cells=u['rep']['cells'], dir=u['rep']['dir'], tap=[round(x, 1), round(y, 1)],
                     result='tapped'))
        log(dict(level=level, round=rnd, event='taps_done', n=len(taps), secs=round(time.time() - t0, 2), out=r.stdout.strip()[-300:]))
        time.sleep(0.45)
    return 'rounds'


def main():
    args = sys.argv[1:]
    def opt(name, default=None, cast=str):
        if name in args:
            i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return cast(v)
        return default
    def flag(name):
        if name in args:
            args.remove(name); return True
        return False
    cmd = args.pop(0)
    if cmd == 'read':
        level = opt('--level', 0, int); tag = opt('--tag', 'x')
        path = args[0]
        im = np.array(Image.open(path).convert('RGB')).astype(np.int16)
        print('guard', guard(im))
        b = read_board(im)
        o = os.path.join(OVL, 'L%03d-%s.png' % (level, tag))
        overlay(im, b, o)
        print('fit', b['fit']); print('bounds', b['bounds'], 'arrows', len(b['arrows']))
        print('anomalies', b['anomalies']); print('obstacles', [(o_['kind'], o_['bbox_px'], o_['mean_rgb'], o_['cells']) for o_ in b['obstacles']])
        print('free', [a['id'] for a in free_arrows(b)]); print('taped', sorted(taped_ids(b)))
        print('overlay', o)
    elif cmd == 'dump':
        level = opt('--level', 0, int); zoom = opt('--zoom', 'open'); timer = opt('--timer', None, int)
        hearts = opt('--hearts', 3, int); tag = opt('--tag', None)
        path = args[0]
        im = np.array(Image.open(path).convert('RGB')).astype(np.int16)
        b = read_board(im)
        print(dump_level(b, level, path, zoom=zoom, timer=timer, hearts=hearts, tag=tag))
    elif cmd == 'play2':
        level = opt('--level', 0, int); secs = opt('--seconds', 170, float)
        print('result', play2(level, secs, stop_key=flag('--stop-key')))
    elif cmd == 'plan':
        path = args[0]
        im = np.array(Image.open(path).convert('RGB')).astype(np.int16)
        b = read_board(im)
        for u, c, xy in plan(b):
            print(u['ids'], u['rep']['dir'], c, [round(v, 1) for v in xy], 'blockers', sorted(u['block']))
    elif cmd == 'play':
        level = opt('--level', 0, int); secs = opt('--seconds', 150, float); gap = opt('--gap', 0.25, float)
        mr = opt('--max-rounds', 60, int)
        print('result', play(level, secs, gap, mr, dry=flag('--dry'), allow_taped=flag('--allow-taped'), stop_key=flag('--stop-key')))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
