#!/usr/bin/env python3
"""vextract — read a level board out of a frame of the owner's gameplay videos (video skin: blue strokes on light blue,
592x1280 px, H.264), write it in the phone player's level-JSON schema, verify it (overlay + ink IoU) and REPLAY the video's taps
against it. Adapted from research/bot/bot.py (same grid comb fit, cell/edge graph, occlusion bridging, head test).

  python3 vextract.py read FRAME.png [--out L.json] [--overlay O.png] [--level N] [--video V1|V2] [--t SEC]
  python3 vextract.py level V1|V2 N [--t SEC] [--outdir DIR]        # start frame from the index (research/video-index.json or
                                                                      # video-frames/work/V?.index.json) -> JSON + overlay + IoU
  python3 vextract.py replay V1|V2 N [--json L.json] [--report R.json] [--sheet]   # tap/exit/bump replay check (see replay())
  python3 vextract.py compare A.json B.json                           # cell-by-cell comparison of two level JSONs

Output JSON = the phone schema (research/levels/L032.json: level, source, shot, zoom, pitch_pt, stroke_pt, origin_pt, cols, rows,
mask, arrows[{id, cells[[c,r]...] tail->head, dir}], obstacles[{kind, cells, bbox_px, mean_rgb}], taped_arrow_ids, timer_s, hearts,
tag, anomalies, occlusion_inferred, pipes[{cells, ends[{cell, out}]}], door_cells, reader) plus:
  "source": "video", "video": "V1|V2", "t": <frame time s>, "frame": <path>,
  obstacles[].counter (curtain / box / pipe counters, OCR), "blocker_cells" (cells of boxes + curtains: they block rays while their
  counter > 0), "elevators": [{"cells", "arrow_ids"}] (platforms; arrows under them are HIDDEN in a start frame),
  "verify": {"ink_iou", "ink_px", "render_px", "missed_ink_px", "extra_px"}.
Coordinates: px = full-res frame pixels; pt = px * 393/592 (the videos are a 393-pt-wide phone).
"""
import json, math, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(RES)))
FR = os.path.join(RES, 'video-frames')
WORK = os.path.join(FR, 'work')
VGRAB, VOCR = os.path.join(HERE, 'vgrab'), os.path.join(HERE, 'vocr')
W_PX, H_PX = 592, 1280
SCALE = W_PX / 393.0                 # px per pt
BAND_Y0, BAND_Y1 = 180, 1122         # board band (HUD above, booster bar top edge at ~1126), full-res px
DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
DIRNAME = {v: k for k, v in DIRS.items()}
BG = np.array([239, 245, 255])


def rel(p):
    return os.path.relpath(p, os.path.dirname(os.path.dirname(RES)))   # repo-relative ('apps/mazeout/...') -> keep 'research/...'


def relres(p):
    return os.path.relpath(p, os.path.dirname(RES))


def load(path):
    return np.array(Image.open(path).convert('RGB')).astype(np.int16)


# ------------------------------------------------------------------------------------------------ masks
def band_mask(shape):
    m = np.zeros(shape[:2], bool)
    m[BAND_Y0:BAND_Y1] = True
    return m


def ink_mask(im):
    """arrow strokes: saturated BLUE (core ~ (21,116,254), dark rim ~ (15,66,210)); cyan (boxes, pipes incl. their darker shaded
    side ~(48,176,240), exiting arrows) and the lavender elevator shade are excluded by G < 0.66 B, G < 185 and R < 130
    (measured on V2 L21: stroke G/B median 0.46, p95 0.63; pipe G/B p5 0.69)"""
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    return (b > 150) & (b - r > 100) & (g < 185) & (r < 130) & (g * 100 < 66 * b) & band_mask(im.shape)


def colour_mask(im, ink):
    """obstacles (pink ties, purple curtains, cyan boxes / pipes, badges, tutorial hand): saturated, not stroke-blue"""
    mx, mn = im.max(2), im.min(2)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    cyan = (g >= 170) & (b > 200) & (r < 170) & (b - r > 60)
    sat = ((mx - mn) > 70) & ~ink
    # anti-aliased stroke rims blend blue into the background and look cyan: drop everything within 2 px of stroke ink
    rim = ndimage.binary_dilation(ink, iterations=2)
    return (sat | cyan) & band_mask(im.shape) & ~rim


def shade_mask(im, ink):
    """elevator platforms: lavender-grey (~(215,218,238)) low-saturation areas darker than the board background"""
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    mean = (r + g + b) / 3
    m = (mean > 180) & (mean < 234) & ((im.max(2) - im.min(2)) < 45) & (b >= r) & (b - r < 40) & ~ink & band_mask(im.shape)
    m = ndimage.binary_opening(m, structure=np.ones((5, 5), bool))
    return m


# ------------------------------------------------------------------------------------------------ grid fit (bot.py)
def comb_fit(vals, weights, pmin, pmax):
    vals = np.asarray(vals, float); w = np.asarray(weights, float)
    ps = np.arange(pmin, pmax, 0.05)
    sc = np.array([abs((w * np.exp(2j * np.pi * vals / p)).sum() / w.sum()) for p in ps])
    return ps, sc


def stroke_width(ink):
    runs = []
    ys = np.nonzero(ink.any(1))[0]
    for y in ys[::5]:
        d = np.diff(np.concatenate([[0], ink[y].astype(int), [0]]))
        s, e = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        runs += list(e - s)
    runs = np.array(runs)
    return float(np.median(runs[(runs > 2) & (runs < 30)])) if len(runs) else 8.0


def fit_grid(ink):
    stroke = stroke_width(ink)
    L = max(9, int(round(stroke * 2.2)))
    vert = ndimage.binary_opening(ink, structure=np.ones((L, 1), bool))
    horz = ndimage.binary_opening(ink, structure=np.ones((1, L), bool))
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
    pmin, pmax = max(stroke * 2.2, 10), 120
    ps, sx = comb_fit(xs, xw, pmin, pmax)
    _, sy = comb_fit(ys_, yw, pmin, pmax)
    sc = (sx * len(xs) + sy * len(ys_)) / (len(xs) + len(ys_))
    top = sc.max()
    cand = np.nonzero(sc >= 0.93 * top)[0]
    i = cand.max()
    lo, hi = max(0, i - 40), min(len(ps), i + 40)
    p = ps[lo + int(np.argmax(sc[lo:hi]))]

    def origin(vals, w):
        z = (np.asarray(w) * np.exp(2j * np.pi * np.asarray(vals) / p)).sum()
        return (np.angle(z) / (2 * np.pi) * p) % p
    x0, y0 = origin(xs, xw), origin(ys_, yw)
    kx = np.round((np.array(xs) - x0) / p); ky = np.round((np.array(ys_) - y0) / p)
    A = np.zeros((len(xs) + len(ys_), 3)); b = np.zeros(len(xs) + len(ys_)); Wt = np.concatenate([xw, yw]).astype(float)
    A[:len(xs), 0] = kx; A[:len(xs), 1] = 1; b[:len(xs)] = xs
    A[len(xs):, 0] = ky; A[len(xs):, 2] = 1; b[len(xs):] = ys_
    sw = np.sqrt(Wt)
    sol, *_ = np.linalg.lstsq(A * sw[:, None], b * sw, rcond=None)
    p2, x02, y02 = sol
    resid = b - A @ sol
    return dict(pitch=float(p2), x0=float(x02), y0=float(y02), stroke=stroke,
                resid_px=float(np.sqrt(np.average(resid ** 2, weights=Wt))), comb=float(top))


# ------------------------------------------------------------------------------------------------ obstacles
def blob_hues(pix):
    r, g, b = pix[:, 0].astype(int), pix[:, 1].astype(int), pix[:, 2].astype(int)
    return dict(
        pink=((r > 200) & (g < 120) & (b > 80) & (b < 190)).mean(),
        purple=((r > 110) & (r < 215) & (b > 170) & (g < 150) & (b - g > 60)).mean(),
        cyan=((g >= 170) & (b > 200) & (r < 170)).mean(),
        yellow=((r > 220) & (g > 150) & (b < 90)).mean(),
        navy=((r < 90) & (g < 110) & (b > 90) & (b < 200)).mean(),
    )


def classify_blob(pix, area, p, filled, bbox):
    """video skin classes: tape_pink (Linked Arrows tie), curtain (V1 purple crate + counter), box (V2 cyan box + bomb counter),
    pipe (V2 light-blue tube, 1 cell thick), hand (tutorial pointer), unknown"""
    h = blob_hues(pix)
    x0, y0, x1, y1 = bbox
    w_, h_ = (x1 - x0) / p, (y1 - y0) / p
    fill = area / max(1.0, float(filled.sum()))
    if h['yellow'] > 0.25:
        return 'hand'
    if h['navy'] > 0.5 and h['cyan'] < 0.1 and h['purple'] < 0.1:
        return 'text'                 # V1 'Level N' tag, tutorial captions
    if h['pink'] > 0.35:
        return 'tape_pink'
    if h['purple'] > 0.3:
        return 'curtain'
    if h['cyan'] > 0.3:
        # V2 box = saturated pure cyan (R < 25 on most cyan pixels, ~(0,192,240)) around a bomb counter; pipe = lighter tube
        # (R 30-140, ~(64,192,240)) with a white highlight stripe. Measured: box R<25 share 0.79-0.86, pipe 0.00-0.04,
        # pipe counter badge / mouth ring 0.3-0.4 (small; merged into the pipe they touch).
        r = pix[:, 0].astype(int); g = pix[:, 1].astype(int); b = pix[:, 2].astype(int)
        cy = (g >= 170) & (b > 200) & (r < 170)
        pure = ((r < 25) & cy).sum() / max(1, cy.sum())
        if pure >= 0.6:
            return 'box'
        if pure <= 0.15:
            return 'pipe'
        return 'pipe_part'
    return 'unknown'


def ocr_counter(frame_path, bbox, pad=4):
    """counter digits (white, dark outline) on a curtain / box bomb / pipe badge. Vision is flaky on this font at a single scale
    (V2 L12 box '8': read at 3x only), so try the bbox and its centre 70 % at scales 3, 2, 4, 5 and take the first number."""
    if not frame_path or not os.path.exists(VOCR):
        return None
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    crops = [[max(0, x0 - pad), max(0, y0 - pad), w + 2 * pad, h + 2 * pad],
             [int(x0 + 0.15 * w), int(y0 + 0.15 * h), int(0.7 * w), int(0.7 * h)]]
    tr = str.maketrans({'O': '0', 'o': '0', 'S': '5', 'l': '1', 'I': '1', 'B': '8', 'Z': '2', 'g': '9', 'T': '7'})
    for sc in ('3', '2', '4', '5'):
        for crop in crops:
            try:
                r = subprocess.run([VOCR, '--crop'] + [str(int(c)) for c in crop] + ['--scale', sc, frame_path], capture_output=True,
                                   text=True, timeout=30)
                d = json.loads(r.stdout.strip().splitlines()[0])
            except Exception:
                continue
            for wd in d.get('words', []):
                if wd.get('conf', 0) < 0.5:
                    continue
                m = re.fullmatch(r'\s*(\d{1,3})\s*', wd['s'].translate(tr))
                if m:
                    return int(m.group(1))
    return None


def ocr_white_digits(im, frame_path, bbox, p, pad=0):
    """fallback: crop tightly around the white digit pixels (min channel > 225, compact blobs) inside bbox (+pad) and OCR that"""
    x0, y0, x1, y1 = [int(v) for v in bbox]
    x0, y0 = max(0, int(x0 - pad)), max(0, int(y0 - pad)); x1, y1 = int(x1 + pad), int(y1 + pad)
    sub = im[y0:y1, x0:x1]
    wh = sub.min(2) > 225
    lab, n = ndimage.label(wh)
    boxes = []
    for j, sl in enumerate(ndimage.find_objects(lab)):
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if 0.15 * p <= hh <= 0.9 * p and ww <= 0.9 * p and (lab[sl] == j + 1).sum() >= 10:
            boxes.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    if not boxes:
        return None
    # digits of one number sit side by side at the same height: take the row of the tallest blob
    boxes.sort(key=lambda b: -(b[3] - b[1]))
    ref = boxes[0]
    row = [b for b in boxes if abs((b[1] + b[3]) / 2 - (ref[1] + ref[3]) / 2) < 0.3 * p]
    bx0 = min(b[0] for b in row); by0 = min(b[1] for b in row); bx1 = max(b[2] for b in row); by1 = max(b[3] for b in row)
    m = 0.25 * p
    return ocr_counter(frame_path, [int(x0 + bx0 - m), int(y0 + by0 - m), int(x0 + bx1 + m), int(y0 + by1 + m)])


# ------------------------------------------------------------------------------------------------ board reader
def read_board(im, fit=None, frame_path=None):
    ink0 = ink_mask(im)
    colour = colour_mask(im, ink0)
    col_close = ndimage.binary_closing(colour, iterations=2)
    col_filled = ndimage.binary_fill_holes(col_close)
    lab, n = ndimage.label(col_filled)
    blobs = []
    if fit is None:
        # obstacle art (navy counter badges look like ink) is removed before the fit
        big = np.zeros_like(col_filled)
        for i, sl in enumerate(ndimage.find_objects(lab)):
            if (lab[sl] == i + 1).sum() >= 150:
                big[sl] |= lab[sl] == i + 1
        fit = fit_grid(ink0 & ~ndimage.binary_dilation(big, iterations=3))
    p, X0, Y0, stroke = fit['pitch'], fit['x0'], fit['y0'], fit['stroke']
    for i, sl in enumerate(ndimage.find_objects(lab)):
        comp = lab[sl] == i + 1
        area = int(comp.sum())
        if area < max(120, 0.12 * p * p):
            continue
        pix = im[sl][comp & colour[sl]]
        if len(pix) < 30:
            continue
        bbox = [int(sl[1].start), int(sl[0].start), int(sl[1].stop), int(sl[0].stop)]
        kind = classify_blob(pix, int((comp & colour[sl]).sum()), p, comp, bbox)
        blobs.append(dict(sl=sl, comp=comp, kind=kind, bbox=bbox, mean=[int(v) for v in pix.mean(0)]))
    # pipe tube + mouth rings + counter badge are separate colour blobs: union every pipe/pipe_part blob (and small unknown bits)
    # lying within 8 px of each other into one pipe
    pp_ = [bl for bl in blobs if bl['kind'] in ('pipe', 'pipe_part') or (bl['kind'] == 'unknown' and bl['comp'].sum() < 3.0 * p * p)]
    par = list(range(len(pp_)))

    def fnd(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for i1 in range(len(pp_)):
        for i2 in range(i1 + 1, len(pp_)):
            a_, b_ = pp_[i1]['bbox'], pp_[i2]['bbox']
            if a_[0] <= b_[2] + 8 and b_[0] <= a_[2] + 8 and a_[1] <= b_[3] + 8 and b_[1] <= a_[3] + 8:
                if 'unknown' in (pp_[i1]['kind'], pp_[i2]['kind']) and not {'pipe', 'pipe_part'} & {pp_[i1]['kind'], pp_[i2]['kind']}:
                    continue
                par[fnd(i1)] = fnd(i2)
    groups = {}
    for k_, bl in enumerate(pp_):
        groups.setdefault(fnd(k_), []).append(bl)
    merged = []
    for g_ in groups.values():
        if len(g_) == 1:
            if g_[0]['kind'] == 'pipe_part':
                g_[0]['kind'] = 'pipe'
            continue
        ux0 = min(bl['bbox'][0] for bl in g_); uy0 = min(bl['bbox'][1] for bl in g_)
        ux1 = max(bl['bbox'][2] for bl in g_); uy1 = max(bl['bbox'][3] for bl in g_)
        m = np.zeros((uy1 - uy0, ux1 - ux0), bool)
        for bl in g_:
            x0, y0, x1, y1 = bl['bbox']
            m[y0 - uy0:y1 - uy0, x0 - ux0:x1 - ux0] |= bl['comp']
            bl['kind'] = 'merged'
        merged.append(dict(sl=(slice(uy0, uy1), slice(ux0, ux1)), comp=m, kind='pipe', bbox=[ux0, uy0, ux1, uy1],
                           mean=[int(v) for v in np.mean([bl['mean'] for bl in g_], axis=0)]))
    blobs = [bl for bl in blobs if bl['kind'] != 'merged'] + merged
    obst_mask = np.zeros(ink0.shape, bool)
    for bl in blobs:
        if bl['kind'] not in ('hand', 'text'):
            obst_mask[bl['sl']] |= bl['comp']
    hand_mask = np.zeros(ink0.shape, bool)
    for bl in blobs:
        if bl['kind'] == 'hand':
            hand_mask[bl['sl']] |= ndimage.binary_dilation(bl['comp'], iterations=6)
    # obstacle art that looks like ink (the pipe's counter badge, bomb outlines): ink components lying mostly within 8 px of an
    # obstacle blob and too short to be a stroke run
    near = ndimage.binary_dilation(obst_mask, iterations=8)
    ilab, inn = ndimage.label(ink0)
    for i, sl in enumerate(ndimage.find_objects(ilab)):
        comp = ilab[sl] == i + 1
        span = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)
        if (comp & near[sl]).sum() >= 0.6 * comp.sum() and span < 1.6 * p:
            obst_mask[sl] |= comp
    occ = ndimage.binary_dilation(obst_mask | hand_mask, iterations=3)
    ink = ink0 & ~ndimage.binary_dilation(obst_mask, iterations=2)
    H, W = ink.shape
    ys, xs = np.nonzero(ink | obst_mask)
    if len(xs) == 0:
        return dict(fit=fit, arrows=[], bounds=None, anomalies=['empty board'], occl=[], obstacles=[], pipes=[], blobs=blobs)
    c_lo = int(math.floor((xs.min() - X0) / p)); c_hi = int(math.ceil((xs.max() - X0) / p))
    r_lo = int(math.floor((ys.min() - Y0) / p)); r_hi = int(math.ceil((ys.max() - Y0) / p))
    rad = max(2, int(stroke * 0.3))

    def C(c, r):
        return X0 + c * p, Y0 + r * p

    def win(m, x, y, rr):
        xi, yi = int(round(x)), int(round(y))
        if yi - rr < 0 or xi - rr < 0 or yi + rr + 1 > H or xi + rr + 1 > W:
            return np.zeros((1, 1), bool)
        return m[yi - rr:yi + rr + 1, xi - rr:xi + rr + 1]

    def status(x, y, rr=rad):
        # >= 0.3 (not 0.5): with ROUNDED corners a thin stroke leaves the corner cell's centre window only ~45 % inked
        # (V1 L6, stroke 4 px); a neighbouring stroke is a full pitch away, so the lower bar adds no false cells
        if win(ink, x, y, rr).mean() >= 0.3:
            return True
        if win(occ, x, y, rr).mean() > 0.3:
            return None
        return False

    # thin strokes (4 px on dense boards) with ROUNDED corners sit up to ~2 px off the grid centreline near a turn: an edge sample
    # counts as ink when a short line PERPENDICULAR to the edge (+-max(2, 0.15 pitch)) crosses >= 2 ink pixels
    ptol = max(2, int(round(0.15 * p)))

    def status_e(x, y, horizontal):
        xi, yi = int(round(x)), int(round(y))
        if yi - ptol < 0 or xi - ptol < 0 or yi + ptol + 1 > H or xi + ptol + 1 > W:
            return False
        line = ink[yi - ptol:yi + ptol + 1, xi] if horizontal else ink[yi, xi - ptol:xi + ptol + 1]
        if line.sum() >= 2:
            return True
        if win(occ, x, y, max(1, rad - 1)).mean() > 0.3:
            return None
        return False

    cell = {}
    for c in range(c_lo, c_hi + 1):
        for r in range(r_lo, r_hi + 1):
            cell[(c, r)] = status(*C(c, r))
    # cells inside solid obstacles (box, curtain, pipe) never become arrow cells by inference
    solid = set()
    for bl in blobs:
        if bl['kind'] not in ('box', 'curtain', 'pipe'):
            continue
        sl, comp = bl['sl'], bl['comp']
        for (c, r) in list(cell):
            x, y = C(c, r)
            xi, yi = int(round(x)) - sl[1].start, int(round(y)) - sl[0].start
            if 0 <= xi < comp.shape[1] and 0 <= yi < comp.shape[0] and comp[yi, xi]:
                solid.add((c, r))
                if cell[(c, r)] is None:
                    cell[(c, r)] = False
    edge = {}
    for c in range(c_lo, c_hi + 1):
        for r in range(r_lo, r_hi + 1):
            for dc, dr in ((1, 0), (0, 1)):
                a, b = C(c, r), C(c + dc, r + dr)
                vals = [status_e(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), dc == 1) for t in (0.5, 0.62, 0.74, 0.38, 0.26)]
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

    occl = []
    # a cell whose centre is hidden by a light knot (the Linked tie's X centre is white-pink) but whose two opposite edges both
    # carry ink is a straight pass-through (V2 L23 middle bundle arrow)
    for (c, r), v in list(cell.items()):
        if v is True or (c, r) in solid:
            continue
        if (E((c, r - 1), (c, r)) is True and E((c, r), (c, r + 1)) is True) or \
           (E((c - 1, r), (c, r)) is True and E((c, r), (c + 1, r)) is True):
            cell[(c, r)] = True
            occl.append(['pass-through', [c, r]])
    # straight continuation through occluded edges (an obstacle or the tutorial hand lying across a stroke)
    for (u, v), val in list(edge.items()):
        if val is not True:
            continue
        for a0, a1 in ((u, v), (v, u)):
            s = (a1[0] - a0[0], a1[1] - a0[1])
            w_, run = a1, []
            while True:
                nx = (w_[0] + s[0], w_[1] + s[1])
                if E(w_, nx) is None:
                    run.append((w_, nx)); w_ = nx; continue
                break
            if not run:
                continue
            nx = (w_[0] + s[0], w_[1] + s[1])
            after = E(w_, nx)
            if any(x_ in solid for e_ in run for x_ in e_):
                continue
            if after is True or cell.get(w_) is True:
                for e_ in run:
                    setE(*e_, True)
                    for cc in e_:
                        if cell.get(cc) is None:
                            cell[cc] = True
                occl.append([list(run[0][0]), list(w_)])
    # partially visible edges: every VISIBLE sample is ink and at least two are visible
    for (u, v), val in list(edge.items()):
        if val is not None or u in solid or v in solid:
            continue
        a, b = C(*u), C(*v)
        vis = [status_e(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]), v[1] == u[1]) for t in (0.12, 0.2, 0.28, 0.36, 0.64, 0.72, 0.8, 0.88)]
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
    adj = {k: [] for k, v in cell.items() if v}
    for (a, b), v in edge.items():
        if v and a in adj and b in adj:
            adj[a].append(b); adj[b].append(a)
    anomalies, seen, arrows = [], set(), []
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
        heads = []
        for e in ends:
            outs = [DIRS[k] for k in DIRS] if len(comp) == 1 else [(e[0] - adj[e][0][0], e[1] - adj[e][0][1])]
            for d in outs:
                x, y = C(*e)
                # the head tip reaches ~1.25-2 strokes beyond the head cell centre (phone: 0.37 pitch); on dense boards the head
                # is small relative to the pitch, and its apex pixels are blended (not ink): test at min(0.27 pitch, 0.9 stroke)
                # (V1 L19: tip ends 7 px out at pitch 27 px; V2 L33 reveal: 8.7 px out, stroke 7 px). A tail's round cap
                # ends 0.5 stroke out, so 0.9 stroke still separates heads from tails.
                td = min(0.27 * p, 0.9 * stroke)
                hx, hy = x + td * d[0], y + td * d[1]
                bx, by = x - 0.05 * p * d[0], y - 0.05 * p * d[1]
                wcount = 0
                for k in np.linspace(-0.45 * p, 0.45 * p, 31):
                    xi, yi = int(round(bx + k * d[1])), int(round(by + k * d[0]))
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
        path, prev, cur = [h['cell']], None, h['cell']
        while True:
            nxt = [v for v in adj[cur] if v != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            path.append(cur)
        arrows.append(dict(cells=path[::-1], dir=DIRNAME[h['d']]))
    # ---- obstacles -> cells
    obst, pipes = [], []
    for bl in blobs:
        if bl['kind'] == 'text':
            continue
        sl, comp = bl['sl'], bl['comp']
        cov = []
        for c in range(c_lo - 1, c_hi + 2):
            for r in range(r_lo - 1, r_hi + 2):
                x, y = C(c, r)
                xi, yi = int(round(x)) - sl[1].start, int(round(y)) - sl[0].start
                if 0 <= xi < comp.shape[1] and 0 <= yi < comp.shape[0] and comp[yi, xi]:
                    cov.append((c, r))
        o = dict(kind=bl['kind'], cells=[list(c) for c in cov], bbox_px=bl['bbox'], mean_rgb=bl['mean'])
        if bl['kind'] in ('curtain', 'box', 'pipe'):
            o['counter'] = ocr_counter(frame_path, bl['bbox']) if bl['kind'] != 'pipe' else None
            if o['counter'] is None and bl['kind'] != 'pipe':
                o['counter'] = ocr_white_digits(im, frame_path, bl['bbox'], p)
        if bl['kind'] == 'pipe':
            tube = set(cov)
            ends = {}
            for (c_, r_) in tube:
                nb = [(c_ + dx, r_ + dy) for dx, dy in DIRS.values() if (c_ + dx, r_ + dy) in tube]
                if len(nb) == 1:
                    ends[(c_, r_)] = (c_ - nb[0][0], r_ - nb[0][1])
            if len(ends) != 2:
                anomalies.append('pipe with %d ends (cells %s)' % (len(ends), sorted(tube)[:8]))
            # the pipe counter badge sits at a mouth: OCR a 1.8-cell window around each end cell (then the whole bbox)
            cnt = None
            # 1) the badge digit: a compact WHITE blob (0.2-0.8 pitch tall) inside the pipe's box (the tube's white highlight is a
            #    long stripe); OCR a 1.3-pitch window around it
            x0b, y0b, x1b, y1b = bl['bbox']
            sub = im[y0b:y1b, x0b:x1b]
            wh = (sub.min(2) > 225)
            wl, wn = ndimage.label(wh)
            for j, wsl in enumerate(ndimage.find_objects(wl)):
                hh, ww = wsl[0].stop - wsl[0].start, wsl[1].stop - wsl[1].start
                if 0.2 * p <= hh <= 0.8 * p and ww <= 0.8 * p and (wl[wsl] == j + 1).sum() >= 12:
                    cy_ = y0b + (wsl[0].start + wsl[0].stop) / 2; cx_ = x0b + (wsl[1].start + wsl[1].stop) / 2
                    cnt = ocr_counter(frame_path, [int(cx_ - 0.65 * p), int(cy_ - 0.65 * p), int(cx_ + 0.65 * p), int(cy_ + 0.65 * p)])
                    if cnt is not None:
                        break
            for (c_, r_) in (list(ends) if cnt is None else []):
                x, y = C(c_, r_)
                d_ = ends[(c_, r_)]
                # the badge sits just inside the mouth: centre the window one cell back along the tube
                wx, wy = x - d_[0] * 0.9 * p, y - d_[1] * 0.9 * p
                cnt = ocr_counter(frame_path, [int(wx - 1.0 * p), int(wy - 1.0 * p), int(wx + 1.0 * p), int(wy + 1.0 * p)])
                if cnt is not None:
                    break
            if cnt is None:
                cnt = ocr_counter(frame_path, bl['bbox'])
            if cnt is None:
                cnt = ocr_white_digits(im, frame_path, bl['bbox'], p, pad=0.3 * p)
            o['counter'] = cnt
            pipes.append(dict(cells=tube, ends=ends, counter=o['counter']))
        if bl['kind'] == 'hand':
            o['note'] = 'tutorial pointer (not a board object); strokes under it inferred by straight continuation'
        obst.append(o)
    # ---- elevators (V2 L31+: hatched lavender platforms carrying a layer of arrows). Per cell: the share of lavender pixels
    # (mean 170-233, B-R 5-45, low saturation) in the cell square with stroke ink (+2 px rim) and obstacles removed >= 20 %.
    rim = ndimage.binary_dilation(ink0 | obst_mask, iterations=2)
    shade_cells = set()
    for c in range(c_lo - 1, c_hi + 2):
        for r in range(r_lo - 1, r_hi + 2):
            x, y = C(c, r)
            x0_, x1_ = int(round(x - 0.45 * p)), int(round(x + 0.45 * p))
            y0_, y1_ = int(round(y - 0.45 * p)), int(round(y + 0.45 * p))
            if x0_ < 0 or y0_ < BAND_Y0 or x1_ > W or y1_ > BAND_Y1:
                continue
            sub = im[y0_:y1_, x0_:x1_][~rim[y0_:y1_, x0_:x1_]]
            if len(sub) < 0.15 * p * p:
                continue
            mean = sub.mean(1)
            lav = (mean > 170) & (mean < 233) & ((sub[:, 2] - sub[:, 0]) >= 5) & ((sub[:, 2] - sub[:, 0]) <= 45) & \
                  ((sub.max(1) - sub.min(1)) < 50)
            # hatched platform rim ~50 % lavender stripes, inner lanes ~100 %, plain board ~1 % (grid dots)
            if lav.mean() >= 0.2:
                shade_cells.add((c, r))
    elevators = []
    seen_e = set()
    for c0_ in sorted(shade_cells):
        if c0_ in seen_e:
            continue
        comp, st = [], [c0_]; seen_e.add(c0_)
        while st:
            u = st.pop(); comp.append(u)
            for dx, dy in DIRS.values():
                v = (u[0] + dx, u[1] + dy)
                if v in shade_cells and v not in seen_e:
                    seen_e.add(v); st.append(v)
        if len(comp) < 4:
            continue
        xs_ = [C(*u)[0] for u in comp]; ys_ = [C(*u)[1] for u in comp]
        bb = [int(min(xs_) - p / 2), int(min(ys_) - p / 2), int(max(xs_) + p / 2), int(max(ys_) + p / 2)]
        elevators.append(dict(cells=sorted(comp), bbox_px=bb))
    for a_i, a in enumerate(arrows):
        a['id'] = a_i
    for el in elevators:
        cs = set(el['cells'])
        el['arrow_ids'] = [a['id'] for a in arrows if all(tuple(c) in cs for c in a['cells'])]
        obst.append(dict(kind='elevator', cells=[list(c) for c in el['cells']], bbox_px=el['bbox_px'], mean_rgb=None,
                         arrow_ids=el['arrow_ids']))
    return dict(fit=fit, arrows=arrows, bounds=[c_lo, r_lo, c_hi, r_hi], anomalies=anomalies, occl=occl, obstacles=obst,
                hidden=[list(h) for h in hidden], pipes=pipes, blobs=blobs, _cell=cell, _edge=edge)


# ------------------------------------------------------------------------------------------------ render + IoU
def render(board, shape, head_tip=0.40, head_base=0.22, head_half=0.30, width=None):
    """our own re-render of the board strokes as a bool mask (lines through cell centres, round caps, triangle heads)"""
    fit = board['fit']; p = fit['pitch']
    sw = width or fit['stroke']
    img = Image.new('L', (shape[1], shape[0]), 0)
    dr = ImageDraw.Draw(img)
    C = lambda c, r: (fit['x0'] + c * p, fit['y0'] + r * p)
    for a in board['arrows']:
        pts = [C(*c) for c in a['cells']]
        d = DIRS[a['dir']]
        hx, hy = pts[-1]
        base = (hx - d[0] * head_base * p, hy - d[1] * head_base * p)
        line = pts[:-1] + [base] if len(pts) > 1 else [(hx - d[0] * 0.3 * p, hy - d[1] * 0.3 * p), base]
        if len(pts) == 1:
            line = [base, base]
        dr.line(line, fill=255, width=max(1, int(round(sw))), joint='curve')
        rr = sw / 2
        for (x, y) in line[:1] + pts[1:-1]:
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
        tip = (hx + d[0] * head_tip * p, hy + d[1] * head_tip * p)
        l = (base[0] - d[1] * head_half * p, base[1] + d[0] * head_half * p)
        r_ = (base[0] + d[1] * head_half * p, base[1] - d[0] * head_half * p)
        dr.polygon([tip, l, r_], fill=255)
    return np.array(img) > 0


def verify(im, board):
    """ink IoU of our re-render vs the frame's stroke mask, outside obstacles/hand/elevator badges. Head geometry is fitted
    (3x3x3 grid) so the score measures the MODEL (cells, paths, heads), not a guessed head size."""
    ink = ink_mask(im)
    excl = np.zeros(ink.shape, bool)
    for o in board['obstacles']:
        if o['kind'] == 'elevator':
            continue
        x0, y0, x1, y1 = o['bbox_px']
        excl[max(0, y0 - 3):y1 + 3, max(0, x0 - 3):x1 + 3] = True
    ink_ = ink & ~excl
    best = None
    sw0 = board['fit']['stroke']
    for sw in (sw0 - 1, sw0, sw0 + 1):
        for tip in (0.34, 0.40, 0.46):
            for half in (0.24, 0.30, 0.36):
                for base in (0.16, 0.22):
                    rm = render(board, ink.shape, head_tip=tip, head_base=base, head_half=half, width=sw) & ~excl
                    inter = (rm & ink_).sum(); uni = (rm | ink_).sum()
                    iou = inter / max(1, uni)
                    if best is None or iou > best[0]:
                        best = (iou, tip, half, base, rm, sw)
    iou, tip, half, base, rm, sw = best
    # tolerance version: a pixel counts as matched if the other mask has a pixel within 1 px (JPEG/H.264 edge blur)
    ink_d = ndimage.binary_dilation(ink_, iterations=1)
    rm_d = ndimage.binary_dilation(rm, iterations=1)
    missed = ink_ & ~rm_d
    extra = rm & ~ink_d
    tol = 1 - (missed.sum() + extra.sum()) / max(1, (rm | ink_).sum())
    return dict(ink_iou=round(float(iou), 4), ink_iou_tol1px=round(float(tol), 4), ink_px=int(ink_.sum()), render_px=int(rm.sum()),
                missed_ink_px=int(missed.sum()), extra_px=int(extra.sum()),
                head=dict(tip=tip, half=half, base=base), stroke_px=sw), missed, extra


# ------------------------------------------------------------------------------------------------ overlay
def overlay(im, board, path, note='', missed=None, extra=None):
    img = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))
    img = Image.blend(img, Image.new('RGB', img.size, (255, 255, 255)), 0.55)
    arr = np.array(img)
    if missed is not None:
        arr[missed] = (255, 0, 0)       # frame ink our model does not draw
    if extra is not None:
        arr[extra] = (255, 160, 0)      # model ink the frame does not have
    img = Image.fromarray(arr)
    dr = ImageDraw.Draw(img)
    fit = board['fit']; p = fit['pitch']
    C = lambda c, r: (fit['x0'] + c * p, fit['y0'] + r * p)
    if board.get('bounds'):
        c_lo, r_lo, c_hi, r_hi = board['bounds']
        for c in range(c_lo, c_hi + 1):
            for r in range(r_lo, r_hi + 1):
                x, y = C(c, r); dr.point((x, y), fill=(150, 150, 150))
    pal = [(230, 25, 75), (60, 180, 75), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 190, 190), (240, 50, 230),
           (128, 128, 0), (0, 0, 128), (170, 110, 40)]
    for a in board['arrows']:
        col = pal[a['id'] % len(pal)]
        pts_ = [C(*c) for c in a['cells']]
        if len(pts_) > 1:
            dr.line(pts_, fill=col, width=max(2, int(p * 0.12)))
        x, y = pts_[-1]; d = DIRS[a['dir']]
        tip = (x + d[0] * p * 0.4, y + d[1] * p * 0.4)
        l = (x - d[1] * p * 0.22, y + d[0] * p * 0.22); rr = (x + d[1] * p * 0.22, y - d[0] * p * 0.22)
        dr.polygon([tip, l, rr], fill=col)
        tx, ty = C(*a['cells'][0])
        dr.ellipse([tx - 3, ty - 3, tx + 3, ty + 3], outline=col, width=1)
        mx, my = C(*a['cells'][len(a['cells']) // 2])
        dr.text((mx + 2, my - 10), str(a['id']), fill=(0, 0, 0))
    for o in board['obstacles']:
        colr = {'elevator': (120, 120, 255), 'unknown': (255, 0, 0)}.get(o['kind'], (255, 0, 200))
        dr.rectangle(o['bbox_px'], outline=colr, width=2)
        lab = o['kind'] + ('' if o.get('counter') is None else ' %s' % o['counter'])
        dr.text((o['bbox_px'][0], o['bbox_px'][1] - 11), lab, fill=colr)
        for c in o['cells']:
            x, y = C(*c)
            dr.rectangle([x - 2, y - 2, x + 2, y + 2], outline=colr)
    dr.text((8, BAND_Y0 - 30), 'pitch %.2fpx (%.2fpt) stroke %.1f resid %.2f arrows %d %s' % (
        p, p / SCALE, fit['stroke'], fit['resid_px'], len(board['arrows']), note), fill=(0, 0, 0))
    for i, an in enumerate(board.get('anomalies', [])[:6]):
        dr.text((8, BAND_Y1 + 4 + 12 * i), 'ANOMALY ' + an[:110], fill=(255, 0, 0))
    img.save(path)


# ------------------------------------------------------------------------------------------------ JSON (phone schema)
def to_json(board, level, video=None, t=None, frame=None, timer=None, hearts=3, tag=None, verify_=None):
    cs = [tuple(c) for a in board['arrows'] for c in a['cells']]
    for o in board['obstacles']:
        if o['kind'] not in ('hand',):
            cs += [tuple(c) for c in o['cells']]
    c0 = min(c[0] for c in cs); r0 = min(c[1] for c in cs)
    c1 = max(c[0] for c in cs); r1 = max(c[1] for c in cs)
    fit = board['fit']
    N = lambda c: [c[0] - c0, c[1] - r0]
    arrows = [dict(id=a['id'], cells=[N(c) for c in a['cells']], dir=a['dir']) for a in board['arrows']]
    obst = []
    for o in board['obstacles']:
        q = dict(kind=o['kind'], cells=[N(c) for c in o['cells']], bbox_px=o['bbox_px'], mean_rgb=o['mean_rgb'])
        for k in ('counter', 'arrow_ids', 'note'):
            if k in o:
                q[k] = o[k]
        obst.append(q)
    taped = set()
    for o in board['obstacles']:
        if o['kind'] == 'tape_pink':
            cs_ = set(map(tuple, o['cells']))
            for a in board['arrows']:
                if any(tuple(c) in cs_ for c in a['cells']):
                    taped.add(a['id'])
    pipes = [dict(cells=[N(c) for c in sorted(pp['cells'])], ends=[dict(cell=N(c), out=DIRNAME[d]) for c, d in pp['ends'].items()],
                  counter=pp.get('counter')) for pp in board['pipes']]
    blockers = sorted({tuple(N(c)) for o in board['obstacles'] if o['kind'] in ('box', 'curtain') for c in o['cells']})
    out = dict(level=level, source='video', video=video, t=t, frame=relres(frame) if frame else None, shot=relres(frame) if frame else None,
               zoom='fit', pitch_pt=round(fit['pitch'] / SCALE, 3), stroke_pt=round(fit['stroke'] / SCALE, 2),
               origin_pt=[round((fit['x0'] + c0 * fit['pitch']) / SCALE, 2), round((fit['y0'] + r0 * fit['pitch']) / SCALE, 2)],
               cols=c1 - c0 + 1, rows=r1 - r0 + 1, mask=None, arrows=arrows, obstacles=obst, taped_arrow_ids=sorted(taped),
               timer_s=timer, hearts=hearts, tag=tag, anomalies=board.get('anomalies', []),
               occlusion_inferred=board.get('occl', []), pipes=pipes, door_cells=[], blocker_cells=[list(c) for c in blockers],
               elevators=[dict(cells=o['cells'], arrow_ids=o.get('arrow_ids', [])) for o in obst if o['kind'] == 'elevator'],
               fit_px=dict(pitch=round(fit['pitch'], 4), x0=round(fit['x0'], 3), y0=round(fit['y0'], 3), c0=c0, r0=r0,
                           stroke=round(fit['stroke'], 2), resid_px=round(fit['resid_px'], 3)),
               verify=verify_, reader='video-tools/vextract.py (bot.py reader adapted to the video skin)')
    return out


# ------------------------------------------------------------------------------------------------ index helpers
def load_index(V):
    for p in (os.path.join(RES, 'video-index.json'), os.path.join(WORK, V + '.index.json')):
        if os.path.exists(p):
            d = json.load(open(p))
            levels = d['levels'] if 'levels' in d else d
            L = [x for x in levels if x.get('video') == V]
            if L:
                return L
    raise SystemExit('no index for ' + V)


def level_entry(V, n):
    for L in load_index(V):
        if L['level'] == n:
            return L
    raise SystemExit('level %d not in the %s index' % (n, V))


def grab(V, times, outdir, jpg=True):
    """exact frames (vgrab, tolerance 0) as JPEG q0.9 (a replay needs hundreds; PNGs are ~1 MB each). Callers delete outdir."""
    import shutil
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir, exist_ok=True)
    args = ['%.3f:f%04d' % (t, i) for i, t in enumerate(times)]
    for k in range(0, len(args), 200):
        subprocess.run([VGRAB, V, outdir, '--quiet'] + (['--jpg'] if jpg else []) + args[k:k + 200], check=True)
    ext = '.jpg' if jpg else '.png'
    return [os.path.join(outdir, 'f%04d%s' % (i, ext)) for i in range(len(times))]


def cleanup(d):
    import shutil
    if os.path.isdir(d):
        shutil.rmtree(d)


def extract_level(V, n, t=None, outdir=None):
    L = level_entry(V, n)
    t = L['t_board'] if t is None else t
    outdir = outdir or os.path.join(WORK, 'extract')
    os.makedirs(outdir, exist_ok=True)
    frame = os.path.join(FR, V, 'L%03d-start.png' % n) if abs(t - L['t_board']) < 1e-3 else None
    if frame is None or not os.path.exists(frame):
        frame = os.path.join(FR, V, 'grab', 'L%03d-t%07d.png' % (n, int(round(t * 1000))))
        os.makedirs(os.path.dirname(frame), exist_ok=True)
        subprocess.run([VGRAB, V, os.path.dirname(frame), '--quiet', '%.3f:%s' % (t, os.path.basename(frame)[:-4])], check=True)
    im = load(frame)
    board = read_board(im, frame_path=frame)
    ver, missed, extra = verify(im, board)
    tsec = None
    if L.get('timer_start'):
        m, s_ = L['timer_start'].split(':'); tsec = int(m) * 60 + int(s_)
    js = to_json(board, n, V, round(t, 3), frame, timer=tsec, hearts=L.get('hearts_start', 3), tag=L.get('tag'), verify_=ver)
    if js.get('elevators'):
        js = reveal(V, n, js)
        cleanup(os.path.join(WORK, 'reveal', '%s-L%03d' % (V, n)))
    base = os.path.join(outdir, '%s-L%03d' % (V, n))
    json.dump(js, open(base + '.json', 'w'), indent=1)
    overlay(im, board, base + '-overlay.png', note='%s L%d t=%.2f IoU %.3f (tol1 %.3f)' % (V, n, t, ver['ink_iou'], ver['ink_iou_tol1px']),
            missed=missed, extra=extra)
    return js, base


# ------------------------------------------------------------------------------------------------ elevator reveal
def lav_share(im, js, cells):
    """share of lavender (platform) pixels over the given cells' squares, stroke ink removed"""
    fp = js['fit_px']; p = fp['pitch']
    ink = ndimage.binary_dilation(ink_mask(im), iterations=2)
    tot = lav = 0
    for c in cells:
        x = fp['x0'] + (c[0] + fp['c0']) * p; y = fp['y0'] + (c[1] + fp['r0']) * p
        y0_, y1_, x0_, x1_ = int(y - 0.45 * p), int(y + 0.45 * p), int(x - 0.45 * p), int(x + 0.45 * p)
        sub = im[y0_:y1_, x0_:x1_][~ink[y0_:y1_, x0_:x1_]]
        if not len(sub):
            continue
        mean = sub.mean(1); br = sub[:, 2] - sub[:, 0]
        lav += int(((mean > 170) & (mean < 233) & (br >= 5) & (br <= 45) & ((sub.max(1) - sub.min(1)) < 50)).sum())
        tot += len(sub)
    return lav / max(1, tot)


def reveal(V, n, js, step=0.25, write=True):
    """ELEVATORS: find when each platform activates (its lavender share collapses after its arrows have gone) and read the
    arrows it uncovers from the first stable frame after that, ON THE SAME GRID (fit fixed). The uncovered arrows are appended to
    js['arrows'] with "layer": 2 and "under_elevator": k; js['elevators'][k] gets "t_active" and "hidden_arrow_ids"."""
    els = js.get('elevators') or []
    if not els:
        return js
    L = level_entry(V, n)
    t0, t1 = L['t_board'], L['t_clear'] + 0.3
    times = list(np.arange(t0, t1, step))
    fdir = os.path.join(WORK, 'reveal', '%s-L%03d' % (V, n))
    paths = grab(V, times, fdir)
    fp = js['fit_px']
    fit = dict(pitch=fp['pitch'], x0=fp['x0'], y0=fp['y0'], stroke=fp.get('stroke', js['stroke_pt'] * SCALE), resid_px=0, comb=0)
    base_lav = [lav_share(load(paths[0]), js, e['cells']) for e in els]
    next_id = max(a['id'] for a in js['arrows']) + 1
    for k, e in enumerate(els):
        if e.get('t_active') is not None:
            continue
        cells = set(map(tuple, e['cells']))
        t_act = None
        for i, (t, pth) in enumerate(zip(times, paths)):
            if lav_share(load(pth), js, e['cells']) < 0.35 * base_lav[k]:
                t_act = t
                break
        if t_act is None:
            e['t_active'] = None
            continue
        # first frame >= 0.5 s after activation whose ink inside the region is stable over the next frame
        prev = None
        chosen = None
        for t, pth in zip(times, paths):
            if t < t_act + 0.5:
                continue
            im = load(pth)
            ink = ink_mask(im)
            cnt = 0
            for c in cells:
                x = fp['x0'] + (c[0] + fp['c0']) * fp['pitch']; y = fp['y0'] + (c[1] + fp['r0']) * fp['pitch']
                cnt += int(ink[int(y) - 2:int(y) + 3, int(x) - 2:int(x) + 3].mean() >= 0.5)
            if prev is not None and abs(cnt - prev[1]) <= max(1, 0.03 * cnt) and cnt > 0:
                chosen = prev[0]
                break
            prev = (pth, cnt, t)
        if chosen is None:
            e['t_active'] = round(t_act, 3)
            e['hidden_arrow_ids'] = []
            e['note'] = 'activation seen, no stable reveal frame'
            continue
        im = load(chosen)
        b = read_board(im, fit=dict(fit), frame_path=chosen)
        new_ids = []
        # the platform's border column/row can fall under the 20 % lavender cut: accept arrows lying entirely in the region
        # grown by one cell, with at least half of their cells in the core, that are not an already-known arrow
        grown = set(cells) | {(c[0] + dx, c[1] + dy) for c in cells for dx, dy in DIRS.values()}
        known = {tuple(map(tuple, a_['cells'])) for a_ in js['arrows'] if a_['id'] not in e.get('arrow_ids', [])}
        for a in b['arrows']:
            nc = [(c[0] - fp['c0'], c[1] - fp['r0']) for c in a['cells']]
            inside = sum(1 for c in nc if c in cells) / len(nc)
            if all(c in grown for c in nc) and inside >= 0.5 and tuple(nc) not in known:
                js['arrows'].append(dict(id=next_id, cells=[list(c) for c in nc], dir=a['dir'], layer=2, under_elevator=k))
                new_ids.append(next_id)
                next_id += 1
        e['t_active'] = round(t_act, 3)
        e['reveal_frame_t'] = round([t for t, pth in zip(times, paths) if pth == chosen][0], 3)
        e['hidden_arrow_ids'] = new_ids
        keep = os.path.join(FR, V, 'L%03d-elevator%d-reveal.png' % (n, k))
        Image.open(chosen).convert('RGB').save(keep)
        e['reveal_frame'] = relres(keep)
        newcells = [tuple(map(tuple, a_['cells'])) for a_ in js['arrows'] if a_.get('under_elevator') == k]
        bb = dict(b, arrows=[a for a in b['arrows'] if tuple((c[0] - fp['c0'], c[1] - fp['r0']) for c in a['cells']) in newcells])
        overlay(im, bb, os.path.join(WORK, 'extract', '%s-L%03d-elevator%d-overlay.png' % (V, n, k)),
                note='%s L%d elevator %d hidden layer, t=%.2f' % (V, n, k, e['reveal_frame_t']))
    if write:
        js['reveal'] = 'elevator layers read by vextract.reveal() from later frames on the start-frame grid'
    return js


# ------------------------------------------------------------------------------------------------ model + replay
class Model:
    """the game state of a level JSON: arrows present, counters, pipes; rays per the phone rules (bot.py ray/free_arrows)"""

    def __init__(self, js):
        self.js = js
        self.A = {a['id']: dict(a, cells=[tuple(c) for c in a['cells']]) for a in js['arrows']}
        self.alive = {i for i, a in self.A.items() if a.get('layer', 1) == 1}
        self.cell_of = {}
        for a in self.A.values():
            for c in a['cells']:
                self.cell_of.setdefault(c, []).append(a['id'])
        self.elevators = [dict(e, active=False) for e in js.get('elevators', [])]
        cs = [c for a in self.A.values() for c in a['cells']] + [tuple(c) for o in js['obstacles'] for c in o['cells']]
        self.bounds = (min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs))
        self.blockers = []     # [{cells:set, counter:int|None, kind}]
        for o in js['obstacles']:
            if o['kind'] in ('box', 'curtain'):
                self.blockers.append(dict(cells=set(map(tuple, o['cells'])), counter=o.get('counter'), counter0=o.get('counter'),
                                          kind=o['kind'], broken=False, removed=0))
        self.pipes = []
        for k, pp in enumerate(js.get('pipes', [])):
            self.pipes.append(dict(k=k, cells=set(map(tuple, pp['cells'])), ends={tuple(e['cell']): DIRS[e['out']] for e in pp['ends']},
                                   counter=pp.get('counter'), counter0=pp.get('counter'), passes=0))
        self.pipes_all = list(self.pipes)
        self.tapes = []
        for o in js['obstacles']:
            if o['kind'] == 'tape_pink':
                cs_ = set(map(tuple, o['cells']))
                ids = [a['id'] for a in self.A.values() if any(c in cs_ for c in a['cells'])]
                if ids:
                    self.tapes.append(ids)

    def activate_due(self, t=None):
        """RULE (V2 L32, heart lost 0.6 s after the last platform arrow was tapped, 0.3 s BEFORE the platform visibly dropped):
        an elevator activates the moment its last platform arrow leaves; its hidden layer is live (blocks rays) at once."""
        out = []
        for k, e in enumerate(self.elevators):
            if e['active'] or not e.get('hidden_arrow_ids'):
                continue
            if any(i in self.alive for i in e.get('arrow_ids', [])):
                continue
            e['active'] = True
            self.alive |= set(e.get('hidden_arrow_ids', []))
            out.append(k)
        return out

    def group(self, aid):
        for g in self.tapes:
            if aid in g:
                return [i for i in g if i in self.alive]
        return [aid]

    def ray(self, aid, info=None):
        c0, r0, c1, r1 = self.bounds
        a = self.A[aid]
        d = DIRS[a['dir']]
        c, r = a['cells'][-1]
        out, hops = [], 0
        while True:
            c, r = c + d[0], r + d[1]
            if c < c0 - 1 or c > c1 + 1 or r < r0 - 1 or r > r1 + 1:
                break
            hit = None
            for k, pp in enumerate(self.pipes):
                if (c, r) in pp['cells']:
                    hit = (k, pp)
                    break
            if hit and hops < 4:
                k, pp = hit
                o = pp['ends'].get((c, r))
                if o is not None and o == (-d[0], -d[1]) and len(pp['ends']) == 2:
                    other = [e for e in pp['ends'] if e != (c, r)][0]
                    d = pp['ends'][other]
                    c, r = other
                    hops += 1
                    if info is not None:
                        info.setdefault('pipes', []).append(k)
                    continue
            out.append((c, r))
        return out

    def blockers_of(self, aid, ignore=()):
        """what blocks arrow aid's ray now: [('arrow', id) | ('box'/'curtain', idx) | ('pipe', idx)]"""
        res = []
        for c in self.ray(aid):
            os_ = [o for o in self.cell_of.get(c, []) if o in self.alive and o not in ignore and o != aid]
            if os_:
                res.append(('arrow', os_[0]))
                continue
            for k, b in enumerate(self.blockers):
                if c in b['cells'] and not b['broken']:
                    res.append((b['kind'], k))
            for k, pp in enumerate(self.pipes):
                if c in pp['cells']:
                    res.append(('pipe', k))
        return res

    def free(self, aid):
        g = self.group(aid)
        bl = []
        for i in g:
            bl += self.blockers_of(i, ignore=g)
        return not bl, bl

    def remove(self, ids):
        for i in ids:
            info = {}
            self.ray(i, info)
            self.alive.discard(i)
            for b in self.blockers:
                b['removed'] += 1
                if b['counter'] is not None:
                    b['counter'] -= 1
                    if b['counter'] <= 0:
                        b['broken'] = True
            for k in info.get('pipes', []):
                pp = self.pipes[k]
                pp['passes'] += 1
                if pp['counter'] is not None:
                    pp['counter'] -= 1
            self.pipes = [pp for pp in self.pipes if pp['counter'] is None or pp['counter'] > 0]

    def drop_pipe(self, k_all):
        self.pipes = [pp for pp in self.pipes if pp['k'] != k_all]


def presence(im, js, ids):
    """fraction of each arrow's cell centres that still show stroke ink (1 = in place, 0 = gone / turned cyan). Ink = the blue
    stroke OR black: in V2 an arrow that bumped is redrawn BLACK until it leaves (V2 L32 1235.3-1242, 1249.4-1250.6)."""
    black = (im.max(2) < 90) & band_mask(im.shape)
    ink = ink_mask(im) | black
    fp = js['fit_px']
    p = fp['pitch']
    rad = max(2, int(js['stroke_pt'] * SCALE * 0.3))
    out = {}
    A = {a['id']: a for a in js['arrows']}
    for i in ids:
        vals = []
        for c in A[i]['cells']:
            x = fp['x0'] + (c[0] + fp['c0']) * p
            y = fp['y0'] + (c[1] + fp['r0']) * p
            xi, yi = int(round(x)), int(round(y))
            w = ink[max(0, yi - rad):yi + rad + 1, max(0, xi - rad):xi + rad + 1]
            vals.append(w.mean() >= 0.4 if w.size else False)
        out[i] = float(np.mean(vals)) if vals else 0.0
    return out


def obstacle_presence(im, js, cell_sets):
    """per obstacle: share of its cells whose centre (5x5 median) still shows obstacle colour (saturated non-stroke or dark art)"""
    fp = js['fit_px']; p = fp['pitch']
    ink = ink_mask(im)
    out = []
    for cs in cell_sets:
        hit = tot = 0
        for c in cs:
            x = int(round(fp['x0'] + (c[0] + fp['c0']) * p)); y = int(round(fp['y0'] + (c[1] + fp['r0']) * p))
            if y < 2 or x < 2 or y + 3 > im.shape[0] or x + 3 > im.shape[1]:
                continue
            q = np.median(im[y - 2:y + 3, x - 2:x + 3].reshape(-1, 3), axis=0)
            tot += 1
            if ink[y, x]:
                continue
            sat = q.max() - q.min()
            if sat > 60 or q.mean() < 170:
                hit += 1
        out.append(hit / max(1, tot))
    return out


def ink_recall(im, js, ids):
    """share of the frame's stroke ink lying within 3 px of the re-rendered arrows (of `ids`) that are present under js' transform:
    ~1 when the transform is right (every visible stroke belongs to a live arrow), low for a spurious alignment"""
    fp = js['fit_px']
    pr = presence(im, js, ids)
    A = {a['id']: a for a in js['arrows']}
    b = dict(fit=dict(pitch=fp['pitch'], x0=fp['x0'], y0=fp['y0'], stroke=fp.get('stroke', 6.0)),
             arrows=[dict(A[i], cells=[(c[0] + fp['c0'], c[1] + fp['r0']) for c in A[i]['cells']]) for i in ids if pr[i] >= 0.5])
    ink = ink_mask(im)
    if not b['arrows'] or ink.sum() == 0:
        return 0.0
    rm = ndimage.binary_dilation(render(b, ink.shape), iterations=3)
    return float((ink & rm).sum() / ink.sum())


def register(im, js, ids):
    """new board transform for a frame whose grid moved: fit_grid on its ink, then the integer (dc, dr) offset maximising the mean
    presence of the given (live) arrows -> {pitch, x0, y0, score} (x0/y0 already include the offset)"""
    ink = ink_mask(im)
    try:
        f = fit_grid(ink)
    except RuntimeError:
        return None
    fp = js['fit_px']
    A = {a['id']: a for a in js['arrows']}
    cells = [c for i in ids for c in A[i]['cells']]
    if not cells:
        return None
    ys, xs = np.nonzero(ink)
    # estimate: align the live arrows' cell bbox with the ink bbox, then search +-4 cells around it
    cmin = min(c[0] for c in cells) + fp['c0']; rmin = min(c[1] for c in cells) + fp['r0']
    dc0 = int(round((xs.min() - f['x0']) / f['pitch'])) - cmin
    dr0 = int(round((ys.min() - f['y0']) / f['pitch'])) - rmin
    best = None
    for dc in range(dc0 - 4, dc0 + 5):
        for dr in range(dr0 - 4, dr0 + 5):
            cand = dict(js, fit_px=dict(fp, pitch=f['pitch'], x0=f['x0'] + dc * f['pitch'], y0=f['y0'] + dr * f['pitch']))
            pr = presence(im, cand, ids)
            sc = float(np.mean(list(pr.values())))
            if best is None or sc > best['score']:
                best = dict(pitch=f['pitch'], x0=f['x0'] + dc * f['pitch'], y0=f['y0'] + dr * f['pitch'], score=sc)
    return best


def tap_cell(js, x, y):
    fp = js['fit_px']; p = fp['pitch']
    return ((x - fp['x0']) / p - fp['c0'], (y - fp['y0']) / p - fp['r0'])


def arrows_near(js, model, x, y, tol=0.85):
    """live arrows with a cell centre (or the head tip, ~0.35 cell beyond the head cell) within tol cells of the touch point,
    nearest first -> [(dist, id)]"""
    cx, cy = tap_cell(js, x, y)
    best = {}
    for i in model.alive:
        ds = [math.hypot(c[0] - cx, c[1] - cy) for c in model.A[i]['cells']]
        hc = model.A[i]['cells'][-1]; dd = DIRS[model.A[i]['dir']]
        ds.append(math.hypot(hc[0] + 0.35 * dd[0] - cx, hc[1] + 0.35 * dd[1] - cy) / 0.8)
        d = min(ds)
        if d <= tol:
            best[i] = d
    return sorted((d, i) for i, d in best.items())


def arrow_at(js, model, x, y, tol=0.75):
    c = arrows_near(js, model, x, y, tol)
    return c[0][1] if c else None


def replay(V, n, js_path=None, report=None, sheet=False, pre_dt=0.12, post_dt=0.6):
    """REPLAY CHECK of a level JSON against the video.
    For every board tap in the index (time order):
      1. SYNC: frame at t - pre_dt; every modelled arrow whose blue ink is already gone left without a detected tap (the touch
         disc is missed when it lands on a moving rainbow/cyan arrow) -> removed in a greedy FREE-first order, each checked:
         'gone_free' (consistent) or 'gone_blocked' (the model says it could not have left: a model error).
      2. MAP the touch point to the nearest live arrow cell (<= 0.75 cell; head tip counts). No arrow -> 'late' when an arrow
         near the point just left (detected after the exit started) else 'miss'.
      3. VIDEO outcome: bump = the index put a confirmed heart loss on this tap; exit = the arrow (or its whole Linked bundle)
         lost its blue ink by t + post_dt (a leaving arrow turns cyan/rainbow at once, so 0.6 s is enough and avoids later
         traffic over the same cells); stay = neither.   MODEL verdict: free / blocked (by arrows, boxes/curtains, pipes).
         ok  <=>  (exit and free) or (bump and blocked).
    At the level end every remaining arrow must be gone (again checked free-first)."""
    L = level_entry(V, n)
    if js_path is None:
        js_path = os.path.join(WORK, 'extract', '%s-L%03d.json' % (V, n))
    js0 = json.load(open(js_path))
    model = Model(js0)
    js = dict(js0, fit_px=dict(js0['fit_px']))      # working copy: the board transform can change (zoom / pan / re-fit)
    taps = [t for t in L['taps'] if t['y'] <= 1130 and t['t'] >= L['t_board']]
    acts = sorted(e['t_active'] for e in js.get('elevators', []) if e.get('t_active') is not None)
    times = []
    for tp in taps:
        posts = []
        for dt in (0.25, post_dt, 1.5):
            tpost = tp['t'] + dt
            # an elevator activating inside the window paints its hidden layer over the same cells: judge the exit before that
            for ta in acts:
                # t_active (platform colour gone) lags the visible reveal by ~0.4 s (V2 L33: tap 1292.03, layer drawn 1292.4,
                # lavender gone 1292.67): judge at t + 0.3 (a leaving arrow loses its blue at once)
                if tp['t'] < ta <= tpost + 0.5:
                    tpost = tp['t'] + 0.3
            posts.append(tpost)
        times += [tp['t'] - pre_dt] + posts
    times.append(L['t_clear'] + 0.4)
    fdir = os.path.join(WORK, 'replay', '%s-L%03d' % (V, n))
    paths = grab(V, times, fdir)
    log = []
    st = dict(taps=len(taps), mapped=0, exit_free=0, exit_blocked=0, bump_blocked=0, bump_free=0, stay_free=0, stay_blocked=0,
              miss=0, late=0, gone_free=0, gone_blocked=0)
    recent = []      # (t, arrow id) removed by sync

    def note_breaks(t):
        for k, b in enumerate(model.blockers):
            if b['broken'] and 't_zero' not in b and not any(x.get('event') == 'blocker_broken' and x.get('blocker') == k for x in log):
                b['t_zero'] = t
                log.append(dict(t=round(t, 3), event='blocker_counter_zero', blocker=k, kind=b['kind'], counter=b['counter0'],
                                arrows_removed_so_far=b['removed']))
                st['blockers_broken'] = st.get('blockers_broken', 0) + 1

    def sync(im, t):
        # the video says the platform dropped (t_active): any platform arrow still alive in the model left unseen (its cells are
        # re-inked by the new layer, so presence cannot tell) -> remove it (free-checked) and activate
        for k, e in enumerate(model.elevators):
            if not e['active'] and e.get('t_active') is not None and t >= e['t_active'] + 0.5:
                rest = [i for i in e.get('arrow_ids', []) if i in model.alive]
                for i in rest:
                    f, bl = model.free(i)
                    model.remove([i])
                    st['gone_free' if f else 'gone_blocked'] += 1
                    log.append(dict(t=round(t, 3), event='gone_at_elevator_drop', arrow=i, model='free' if f else 'blocked',
                                    **({} if f else {'ok': False, 'blockers': sorted(set(map(tuple, bl)))[:6]})))
        for k in model.activate_due(t):
            log.append(dict(t=round(t, 3), event='elevator_active', elevator=k,
                            hidden_arrows=model.elevators[k].get('hidden_arrow_ids', [])))
        # boxes / curtains: the video shows when each one breaks; the model's counter must agree (it breaks on the exit that takes
        # the counter to 0). An unread counter (OCR failed) is taken from the video.
        op = obstacle_presence(im, js, [b['cells'] for b in model.blockers])
        for k, b in enumerate(model.blockers):
            if not b['broken'] and op[k] < 0.3:
                b['broken'] = True
                log.append(dict(t=round(t, 3), event='blocker_broken', blocker=k, kind=b['kind'], counter=b['counter0'],
                                arrows_removed_so_far=b['removed'], ok=b['counter0'] is None or b['removed'] == b['counter0'],
                                note='counter unread: taken from the video' if b['counter0'] is None else ''))
                st['blockers_broken'] = st.get('blockers_broken', 0) + 1
                if b['counter0'] is not None and b['removed'] != b['counter0']:
                    st['counter_mismatch'] = st.get('counter_mismatch', 0) + 1
            elif b['broken'] and op[k] >= 0.6 and not b.get('flag_still') and t - b.get('t_zero', -1e9) > 1.0:
                # an exiting rainbow arrow sliding over the old cells also looks 'coloured': flag only if it persists >= 1 s
                b.setdefault('still_seen', []).append(t)
                if b['still_seen'][-1] - b['still_seen'][0] < 1.0:
                    continue
                b['flag_still'] = True
                log.append(dict(t=round(t, 3), event='blocker_still_there', blocker=k, counter=b['counter0'],
                                arrows_removed_so_far=b['removed'], ok=False))
                st['counter_mismatch'] = st.get('counter_mismatch', 0) + 1
                b['broken'] = False
        # pipes: the video shows when a pipe shatters (its passes counter hit 0); an unread counter is taken from the video
        live_k = {pp['k'] for pp in model.pipes}
        pp_op = obstacle_presence(im, js, [pp['cells'] for pp in model.pipes_all])
        for pp, v in zip(model.pipes_all, pp_op):
            if pp['k'] in live_k and v < 0.3:
                model.drop_pipe(pp['k'])
                log.append(dict(t=round(t, 3), event='pipe_broken', pipe=pp['k'], counter=pp['counter0'], passes_so_far=pp['passes'],
                                ok=pp['counter0'] is None or pp['passes'] == pp['counter0']))
                st['pipes_broken'] = st.get('pipes_broken', 0) + 1
                if pp['counter0'] is not None and pp['passes'] != pp['counter0']:
                    st['counter_mismatch'] = st.get('counter_mismatch', 0) + 1
        # a hidden layer is live the moment its elevator activates but is only DRAWN from the reveal frame on
        unseen = {i for e in model.elevators if e['active'] and (e.get('reveal_frame_t') or 0) > t for i in e.get('hidden_arrow_ids', [])}
        pr = presence(im, js, sorted(model.alive - unseen))
        gone = [i for i, v in pr.items() if v < 0.3]
        if len(gone) >= max(5, 0.4 * len(pr)):
            # many arrows 'vanished' at once: the board moved (pinch zoom / pan, or a video CUT with a zoom in between).
            # Re-fit the grid on this frame and search the integer cell offset that puts the live arrows back on ink.
            ids_live = sorted(model.alive - unseen)
            reg = register(im, js, ids_live)
            ok_reg = False
            if reg is not None and reg['score'] >= 0.7:
                cand = dict(js, fit_px=dict(js['fit_px'], pitch=reg['pitch'], x0=reg['x0'], y0=reg['y0']))
                r_new, r_cur = ink_recall(im, cand, ids_live), ink_recall(im, js, ids_live)
                # adopt only if the new grid explains clearly more of the frame's ink (a burst of undetected exits also makes many
                # arrows 'vanish' while the board did not move: V2 L35 1486.3)
                ok_reg = r_new >= 0.85 and r_new > r_cur + 0.2
            if ok_reg:
                log.append(dict(t=round(t, 3), event='board_moved', old=dict(pitch=round(js['fit_px']['pitch'], 2),
                                x0=round(js['fit_px']['x0'], 1), y0=round(js['fit_px']['y0'], 1)),
                                new=dict(pitch=round(reg['pitch'], 2), x0=round(reg['x0'], 1), y0=round(reg['y0'], 1)),
                                score=round(reg['score'], 3)))
                st['board_moves'] = st.get('board_moves', 0) + 1
                js['fit_px'].update(pitch=reg['pitch'], x0=reg['x0'], y0=reg['y0'])
                pr = presence(im, js, sorted(model.alive - unseen))
                gone = [i for i, v in pr.items() if v < 0.3]
        while gone:
            prog = False
            for i in list(gone):
                f, bl = model.free(i)
                if f:
                    model.remove([i]); gone.remove(i); prog = True
                    st['gone_free'] += 1; recent.append((t, i)); note_breaks(t)
                    log.append(dict(t=round(t, 3), event='gone_without_tap', arrow=i, model='free'))
            if not prog:
                for i in gone:
                    f, bl = model.free(i)
                    model.remove([i]); st['gone_blocked'] += 1; recent.append((t, i))
                    log.append(dict(t=round(t, 3), event='gone_without_tap', arrow=i, model='blocked',
                                    blockers=sorted(set(map(tuple, bl)))[:6], ok=False))
                gone = []
    for k, tp in enumerate(taps):
        sync(load(paths[4 * k]), tp['t'] - pre_dt)
        post0 = load(paths[4 * k + 1])
        post = load(paths[4 * k + 2])
        post2 = load(paths[4 * k + 3])
        rec = dict(t=tp['t'], x=tp['x'], y=tp['y'], cell=[round(v, 2) for v in tap_cell(js, tp['x'], tp['y'])])
        # the touch disc's centroid is pulled off the stroke it covers (stroke pixels under it are not grey), so a touch between
        # two arrows is ambiguous: among the arrows within 0.85 cell, the one the VIDEO shows leaving is the one the game took
        near = arrows_near(js, model, tp['x'], tp['y'], 0.85)
        aid = near[0][1] if near and near[0][0] <= 0.75 else None
        if len(near) > 1:
            ids_ = [i for _, i in near]
            p0, pa, pb = presence(post0, js, ids_), presence(post, js, ids_), presence(post2, js, ids_)
            # the tapped arrow changes colour at once: the one gone by +0.25 s wins, then +0.6 s, then +1.5 s (a SECOND tap 0.3 s
            # later can take the neighbour: V1 L19 429.56, V2 L35 1421.07; an exit sliding over the cells can re-ink one later)
            leaving = [i for i in ids_ if p0[i] < 0.3] or [i for i in ids_ if pa[i] < 0.3] or [i for i in ids_ if pb[i] < 0.3]
            if leaving and aid not in leaving:
                rec['disambiguated'] = dict(nearest=aid, taken=leaving[0], candidates=[[round(d, 2), i] for d, i in near])
                aid = leaving[0]
        if aid is None:
            cx, cy = tap_cell(js, tp['x'], tp['y'])
            lately = [i for (tt, i) in recent if tp['t'] - tt <= 0.8 and any(math.hypot(c[0] - cx, c[1] - cy) <= 1.0 for c in model.A[i]['cells'])]
            rec['event'] = 'late' if lately else 'miss'
            if lately:
                rec['arrow'] = lately[-1]
            st[rec['event']] += 1
            log.append(rec)
            continue
        st['mapped'] += 1
        g = model.group(aid)
        free, bl = model.free(aid)
        po = presence(post, js, g)
        exited = all(v < 0.3 for v in po.values())
        if not exited:                      # long arrows can still be sliding out after 0.6 s
            po2 = presence(post2, js, g)
            if all(v < 0.3 for v in po2.values()):
                exited, po = True, po2
        vid = 'bump' if tp.get('outcome') == 'bump' else ('exit' if exited else 'stay')
        verdict = 'free' if free else 'blocked'
        if vid == 'stay' and (tp.get('weak') or tp.get('near_hand')):
            vid = 'stay_weak'          # a one-frame / debris / tutorial-hand-shadow 'touch' that did nothing: most likely no touch
            st.setdefault('stay_weak', 0)
        st['%s_%s' % (vid, verdict)] = st.get('%s_%s' % (vid, verdict), 0) + 1
        rec.update(event='tap', arrow=aid, group=g, video=vid, model=verdict, blockers=sorted(set(map(tuple, bl)))[:6],
                   ok=(vid == 'exit' and free) or (vid == 'bump' and not free), presence_after=round(min(po.values()), 2))
        log.append(rec)
        if vid == 'exit':
            model.remove(g)
            note_breaks(tp['t'])
            for kk in model.activate_due():
                log.append(dict(t=round(tp['t'], 3), event='elevator_active', elevator=kk,
                                hidden_arrows=model.elevators[kk].get('hidden_arrow_ids', [])))
    sync(load(paths[-1]), L['t_clear'] + 0.4)
    cleanup(fdir)
    st['arrows'] = len(js['arrows'])
    st['hidden_layer_arrows'] = sum(1 for a in js['arrows'] if a.get('layer', 1) > 1)
    st['left_at_end'] = sorted(model.alive)
    st['consistent'] = st['exit_free'] + st['bump_blocked'] + st['gone_free']
    st['inconsistent'] = st['exit_blocked'] + st['bump_free'] + st['gone_blocked']
    st['unexplained_stays'] = st['stay_free']
    out = dict(video=V, level=n, json=relres(js_path), rule=replay.__doc__.split('\n')[0], stats=st, log=log)
    report = report or os.path.join(WORK, 'extract', '%s-L%03d-replay.json' % (V, n))
    json.dump(out, open(report, 'w'), indent=1, default=lambda o: list(o) if isinstance(o, (set, tuple)) else str(o))
    return out


# ------------------------------------------------------------------------------------------------ compare
def compare(a_path, b_path, shift=None):
    """cell-by-cell comparison: arrows as (cells, dir) keys, best integer shift of B onto A"""
    A = json.load(open(a_path)); B = json.load(open(b_path))
    ka = {(tuple(map(tuple, x['cells'])), x['dir']) for x in A['arrows']}
    best = None
    shifts = [shift] if shift else [(dx, dy) for dx in range(-3, 4) for dy in range(-3, 4)]
    for dx, dy in shifts:
        kb = {(tuple((c[0] + dx, c[1] + dy) for c in x['cells']), x['dir']) for x in B['arrows']}
        m = len(ka & kb)
        if best is None or m > best[0]:
            best = (m, (dx, dy), kb)
    m, sh, kb = best
    onlyA = sorted(ka - kb, key=lambda k: k[0][0]); onlyB = sorted(kb - ka, key=lambda k: k[0][0])
    cellsA = {c for k in ka for c in k[0]}; cellsB = {c for k in kb for c in k[0]}
    return dict(a=relres(a_path) if a_path.startswith(RES) else a_path, b=relres(b_path) if b_path.startswith(RES) else b_path,
                shift_b=sh, arrows_a=len(ka), arrows_b=len(kb), identical_arrows=m,
                only_in_a=[dict(cells=list(map(list, k[0])), dir=k[1]) for k in onlyA],
                only_in_b=[dict(cells=list(map(list, k[0])), dir=k[1]) for k in onlyB],
                cells_a=len(cellsA), cells_b=len(cellsB), cells_common=len(cellsA & cellsB),
                grid_a=[A['cols'], A['rows']], grid_b=[B['cols'], B['rows']],
                pitch_pt=[A.get('pitch_pt'), B.get('pitch_pt')], origin_pt=[A.get('origin_pt'), B.get('origin_pt')])


# ------------------------------------------------------------------------------------------------ CLI
def main():
    a = sys.argv[1:]

    def opt(name, default=None, cast=str):
        if name in a:
            i = a.index(name); v = a[i + 1]; del a[i:i + 2]; return cast(v)
        return default

    def flag(name):
        if name in a:
            a.remove(name); return True
        return False
    cmd = a.pop(0)
    if cmd == 'read':
        out = opt('--out'); ov = opt('--overlay'); n = opt('--level', 0, int); V = opt('--video'); t = opt('--t', None, float)
        path = a[0]
        im = load(path)
        b = read_board(im, frame_path=path)
        ver, missed, extra = verify(im, b)
        js = to_json(b, n, V, t, path, verify_=ver)
        print(json.dumps(dict(arrows=len(js['arrows']), grid=[js['cols'], js['rows']], pitch_pt=js['pitch_pt'], verify=ver,
                              obstacles=[(o['kind'], o.get('counter'), len(o['cells'])) for o in js['obstacles']],
                              anomalies=js['anomalies'])))
        if out:
            json.dump(js, open(out, 'w'), indent=1)
        overlay(im, b, ov or os.path.splitext(out or path)[0] + '-overlay.png', missed=missed, extra=extra)
    elif cmd == 'level':
        V, n = a[0], int(a[1])
        js, base = extract_level(V, n, t=opt('--t', None, float), outdir=opt('--outdir'))
        print(json.dumps(dict(json=base + '.json', overlay=base + '-overlay.png', arrows=len(js['arrows']), grid=[js['cols'], js['rows']],
                              elevators=[dict(t_active=e.get('t_active'), on=len(e['arrow_ids']), hidden=len(e.get('hidden_arrow_ids', [])))
                                         for e in js.get('elevators', [])],
                              pitch_pt=js['pitch_pt'], stroke_pt=js['stroke_pt'], verify=js['verify'],
                              obstacles=[(o['kind'], o.get('counter'), len(o['cells'])) for o in js['obstacles']],
                              anomalies=js['anomalies'])))
    elif cmd == 'replay':
        V, n = a[0], int(a[1])
        out = replay(V, n, js_path=opt('--json'), report=opt('--report'))
        print(json.dumps(out['stats']))
        for r in out['log']:
            if r.get('event') != 'tap' or not r.get('ok'):
                print('  ', json.dumps(r, default=str))
    elif cmd == 'compare':
        print(json.dumps(compare(a[0], a[1]), indent=1))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
