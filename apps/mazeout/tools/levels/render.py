#!/usr/bin/env python3
"""render.py — the OVERLAY PROOF of the bundled levels (CONTENT, L1 acceptance; SPEC.md §5.7: recorded levels IoU ≥ 0.99, video
levels ≥ 0.97, with 1-px tolerance).

Every bundled level whose source is "recorded" (the owner's phone, v552) or "video" (the owner's videos) is drawn FROM THE
BUNDLE (App/Resources/Levels/level_NNNN.json: its start-visible arrows, cells tail→head, head direction) over the capture it
was read from, and the two ink masks are compared:
  capture ink   phone shot: black strokes (luminance < 128, grey); video frame: research/video-tools/vextract.ink_mask
                (the video skin's saturated blue strokes).
  our ink       the level's arrows rendered at the capture's geometry: round-capped, round-joined strokes through the cell
                centres and a triangular head per direction (STYLE §A for the phone: stroke 0.22 p, head base 0.616 p, length
                0.61 p, tip 0.36 p past the head centre for ← →, 0.30 ↑, 0.435 ↓, corner r 0.047 p). Pixels are decided at their
                centres (an exact distance field, the 50 % coverage rule of the capture's antialiasing).
  registration  the research JSON's grid (phone: origin_pt / pitch_pt; video: fit_px) refined sub-pixel (dx, dy, pitch ×(1±0.4 %))
                and the drawing style (stroke widths, head sizes) fitted per level in small bounded steps: the CELLS never move,
                so the score measures the model (which cells, which head), not a guessed look.
  excluded      the obstacle art (tape bands, keys, doors, boxes, pipes and their badges) ± a margin, the tutorial hand and
                labels the video reader flagged, everything outside the board. What lies under an obstacle is proven by
                `lvtool diff` (cell for cell against the research reads) instead.
  scores        IoU = |ours ∩ capture| / |ours ∪ capture|; tol1 = 1 − (capture ink > 1 px from ours + our ink > 1 px from the
                capture) / |union| (vextract's definition). Diagnostics: the deepest missed / extra pixel (distance to the
                nearest matched pixel: a missing or extra stroke or head is ≥ half a stroke deep, antialiasing noise ≤ 1-2 px)
                and the worst arrow's coverage (share of its drawn pixels on capture ink).
  gate          tol1 ≥ 0.99 (recorded) / ≥ 0.97 (video); the report adds depth ≤ 1.5 px and coverage ≥ 0.9 as a second,
                local check (IoU alone barely moves when one short arrow of a 100-arrow board is wrong: see --negative).

  python3 tools/levels/render.py [--levels 32,33] [--out build/l1/overlay] [--negative] [--sheet]
  python3 tools/levels/render.py --reveals [--levels 33] [--negative]
      WHAT THE DOORS HIDE: every door of a recorded level, its hidden arrows (from the bundle) drawn over the bot's round shot
      where that door is first open (research/bot/tmp, named by design/tools/work/reveals/Lnnn.json); at that shot every
      arrow it hid is still in place, so inside the door rectangle ALL ink must be those arrows (a two-sided proof).
Since the level re-order + provenance strip (PUBLISH item 12): the bundle no longer says where a board came from, so every
bundled board is joined to its design/levels.json record first (design/tools/level_order.py: the gameplay must be equal, the
capture / _from come back) and its research files are found by its RESEARCH slot (v552's number), not by the level it ships at.
Output files and rows keep the shipped level number; rows add `board` (e.g. "v552 L69") when the two differ.
Writes <out>/L0NN-overlay.png (capture faded; red = capture ink we do not draw, orange = our ink the capture lacks, green
centre lines = the model), <out>/report.json and, with --sheet, contact sheets of the overlays to LOOK at.
"""
import json
import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(APP, 'research', 'video-tools'))
import vextract  # noqa: E402  (read-only: the video skin's ink mask)
sys.path.insert(0, os.path.join(APP, 'design', 'tools'))
import level_order as LO  # noqa: E402  (board identity after the re-order)

LEVELS = os.path.join(APP, 'App', 'Resources', 'Levels')
RESEARCH = os.path.join(APP, 'research', 'levels')
PHONE_S = 1178.0 / 393.0
D = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
SUBST = {}          # was {level: V2 board}; the V2 boards are found from their provenance now (level_order.research_json)
GATE = {'recorded': 0.99, 'video': 0.97}
DEPTH_GATE = 1.5          # px (see prove())


def load_board(path):
    """A bundled level with its design/levels.json provenance (capture, _from, _rslot) restored and checked."""
    return LO.with_provenance(json.load(open(path)))


def research_file(b):
    b = b if '_rslot' in b else LO.with_provenance(b)
    if b['level'] in SUBST:                                   # an explicit override (none by default)
        return os.path.join(RESEARCH, 'video', 'V2-L%03d.json' % SUBST[b['level']])
    return LO.research_json(b)


def board_note(b):
    return '' if b['_rslot'] == b['level'] else ' = %s' % LO.label(b)


# ------------------------------------------------------------------------------------------------ geometry + style
class Geo:
    """cell (c, r) -> capture px, with a sub-pixel refinement (dx, dy, k = pitch scale about the board centre)"""

    def __init__(self, b, rj):
        self.phone = b['source'] == 'recorded'
        if self.phone:
            s = PHONE_S
            self.p0 = rj['pitch_pt'] * s
            self.x00, self.y00 = rj['origin_pt'][0] * s, rj['origin_pt'][1] * s
        else:
            fp = rj['fit_px']
            self.p0 = fp['pitch']
            self.x00 = fp['x0'] + fp['c0'] * fp['pitch']
            self.y00 = fp['y0'] + fp['r0'] * fp['pitch']
        self.cc = (b['cols'] - 1) / 2.0
        self.rc = (b['rows'] - 1) / 2.0
        self.dx = self.dy = 0.0
        self.k = 1.0

    @property
    def p(self):
        return self.p0 * self.k

    def xy(self, c, r):
        xc = self.x00 + self.cc * self.p0 + self.dx
        yc = self.y00 + self.rc * self.p0 + self.dy
        return xc + (c - self.cc) * self.p, yc + (r - self.rc) * self.p


def default_style(phone, rj):
    if phone:   # STYLE §A (pitch units)
        return dict(wv=0.22, wh=0.22, tip_h=0.36, tip_up=0.30, tip_down=0.435, length=0.61, half=0.308, rad=0.047,
                    fillet=0.125)     # MA §3.2.1 / CONSISTENCY G-4: the drawn path's corners are filleted (0.125 p)
    sw = rj['fit_px'].get('stroke', 6.0) / rj['fit_px']['pitch']
    return dict(wv=sw, wh=sw, tip_h=0.42, tip_up=0.38, tip_down=0.44, length=0.62, half=0.30, rad=0.03, fillet=0.0)


STEPS = dict(wv=0.006, wh=0.006, tip_h=0.02, tip_up=0.02, tip_down=0.02, length=0.03, half=0.015, rad=0.015, fillet=0.03)
BOUNDS = dict(wv=(0.12, 0.30), wh=(0.10, 0.30), tip_h=(0.25, 0.55), tip_up=(0.22, 0.55), tip_down=(0.25, 0.60),
              length=(0.45, 0.80), half=(0.22, 0.40), rad=(0.0, 0.08), fillet=(0.0, 0.25))


# ------------------------------------------------------------------------------------------------ rendering (exact, at pixel centres)
def seg_dist(X, Y, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return np.hypot(X - ax, Y - ay)
    t = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0, 1)
    return np.hypot(X - (ax + t * vx), Y - (ay + t * vy))


def tri_mask(X, Y, A, B, C, rad):
    """rounded triangle: the triangle shrunk about its incentre by `rad`, then everything within `rad` of it"""
    a = math.dist(B, C); b_ = math.dist(A, C); c = math.dist(A, B)
    per = a + b_ + c
    area = abs((B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])) / 2
    inr = 2 * area / per if per else 0
    if rad > 0 and inr > rad:
        ix = (a * A[0] + b_ * B[0] + c * C[0]) / per
        iy = (a * A[1] + b_ * B[1] + c * C[1]) / per
        f = 1 - rad / inr
        A, B, C = [(ix + (P[0] - ix) * f, iy + (P[1] - iy) * f) for P in (A, B, C)]
    else:
        rad = 0

    def side(P, Q):
        return (X - P[0]) * (Q[1] - P[1]) - (Y - P[1]) * (Q[0] - P[0])
    s1, s2, s3 = side(A, B), side(B, C), side(C, A)
    inside = ((s1 >= 0) & (s2 >= 0) & (s3 >= 0)) | ((s1 <= 0) & (s2 <= 0) & (s3 <= 0))
    if rad <= 0:
        return inside
    d = np.minimum(np.minimum(seg_dist(X, Y, *A, *B), seg_dist(X, Y, *B, *C)), seg_dist(X, Y, *C, *A))
    return inside | (d <= rad)


def render(arrows, geo, st, shape, box):
    """bool mask over `box` (x0, y0, x1, y1) of the capture; per-arrow masks for the coverage diagnostic"""
    x0, y0, x1, y1 = box
    out = np.zeros((y1 - y0, x1 - x0), bool)
    per = []
    p = geo.p
    for a in arrows:
        pts = [geo.xy(*c) for c in a['cells']]
        d = D[a['dir']]
        hx, hy = pts[-1]
        tip = {'left': st['tip_h'], 'right': st['tip_h'], 'up': st['tip_up'], 'down': st['tip_down']}[a['dir']] * p
        T = (hx + d[0] * tip, hy + d[1] * tip)
        Bc = (T[0] - d[0] * st['length'] * p, T[1] - d[1] * st['length'] * p)
        h = st['half'] * p
        L_ = (Bc[0] - d[1] * h, Bc[1] + d[0] * h)
        R_ = (Bc[0] + d[1] * h, Bc[1] - d[0] * h)
        xs = [q[0] for q in pts] + [T[0], L_[0], R_[0]]
        ys = [q[1] for q in pts] + [T[1], L_[1], R_[1]]
        m = max(st['wv'], st['wh']) * p / 2 + 2
        bx0, by0 = max(x0, int(math.floor(min(xs) - m))), max(y0, int(math.floor(min(ys) - m)))
        bx1, by1 = min(x1, int(math.ceil(max(xs) + m)) + 1), min(y1, int(math.ceil(max(ys) + m)) + 1)
        if bx1 <= bx0 or by1 <= by0:
            per.append(None)
            continue
        mk = np.zeros((by1 - by0, bx1 - bx0), bool)

        def window(xs_, ys_, m_):
            wx0, wy0 = max(bx0, int(math.floor(min(xs_) - m_))), max(by0, int(math.floor(min(ys_) - m_)))
            wx1, wy1 = min(bx1, int(math.ceil(max(xs_) + m_)) + 1), min(by1, int(math.ceil(max(ys_) + m_)) + 1)
            if wx1 <= wx0 or wy1 <= wy0:
                return None
            Xw, Yw = np.meshgrid(np.arange(wx0, wx1) + 0.5, np.arange(wy0, wy1) + 0.5)
            return Xw, Yw, (slice(wy0 - by0, wy1 - by0), slice(wx0 - bx0, wx1 - bx0))
        # the centre line with its corners filleted (radius f, capped at half a pitch): straight runs between the tangent
        # points + quarter arcs; each piece (and the head) only inside its own window (same pixels, far fewer evaluations)
        f = min(st.get('fillet', 0.0) * p, 0.5 * p)
        runs = []                     # (ax, ay, qx, qy) straight pieces
        arcs = []                     # (cx, cy, e1, e2, w): centre, the two directions bounding the quarter, width
        cuts = [0.0] * len(pts)       # how far each vertex is cut back by its fillet
        for k in range(1, len(pts) - 1):
            d1 = (pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1])
            d2 = (pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
            n1, n2 = math.hypot(*d1), math.hypot(*d2)
            if f <= 0 or n1 == 0 or n2 == 0:
                continue
            u1, u2 = (d1[0] / n1, d1[1] / n1), (d2[0] / n2, d2[1] / n2)
            if abs(u1[0] * u2[0] + u1[1] * u2[1]) > 1e-6:
                continue              # straight through (not a corner)
            cuts[k] = f
            cx, cy = pts[k][0] - u1[0] * f + u2[0] * f, pts[k][1] - u1[1] * f + u2[1] * f
            w = (st['wv'] + st['wh']) / 2 * p
            arcs.append((cx, cy, (-u2[0], -u2[1]), u1, w))
        for k in range(len(pts) - 1):
            (ax, ay), (qx, qy) = pts[k], pts[k + 1]
            n = math.hypot(qx - ax, qy - ay)
            if n == 0:
                continue
            ux, uy = (qx - ax) / n, (qy - ay) / n
            a_ = (ax + ux * cuts[k], ay + uy * cuts[k])
            q_ = (qx - ux * cuts[k + 1], qy - uy * cuts[k + 1])
            w = (st['wv'] if abs(qx - ax) < abs(qy - ay) else st['wh']) * p
            runs.append((a_[0], a_[1], q_[0], q_[1], w))
        for ax, ay, qx, qy, w in runs:
            win = window((ax, qx), (ay, qy), w / 2 + 2)
            if win is None:
                continue
            Xw, Yw, sl = win
            mk[sl] |= seg_dist(Xw, Yw, ax, ay, qx, qy) <= w / 2
        for cx, cy, e1, e2, w in arcs:
            win = window((cx, cx + (e1[0] + e2[0]) * f), (cy, cy + (e1[1] + e2[1]) * f), f + w / 2 + 2)
            if win is None:
                continue
            Xw, Yw, sl = win
            dx_, dy_ = Xw - cx, Yw - cy
            sector = (dx_ * e1[0] + dy_ * e1[1] >= 0) & (dx_ * e2[0] + dy_ * e2[1] >= 0)
            mk[sl] |= sector & (np.abs(np.hypot(dx_, dy_) - f) <= w / 2)
        win = window((T[0], L_[0], R_[0]), (T[1], L_[1], R_[1]), 2)
        if win is not None:
            Xw, Yw, sl = win
            mk[sl] |= tri_mask(Xw, Yw, T, L_, R_, st['rad'] * p)
        out[by0 - y0:by1 - y0, bx0 - x0:bx1 - x0] |= mk
        per.append((bx0 - x0, by0 - y0, mk))
    return out, per


# ------------------------------------------------------------------------------------------------ capture masks
def capture_ink(im, phone):
    if phone:
        f = im.astype(np.int16)
        lum = (0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2])
        return (lum < 128) & ((f.max(2) - f.min(2)) < 80)
    return vextract.ink_mask(im.astype(np.int16))


def exclusion(b, rj, geo, shape):
    """obstacle art ± margin (pitch units), video blobs the reader flagged (hand, labels)"""
    ex = np.zeros(shape[:2], bool)
    p = geo.p

    def rect(cells, m, extra=None):
        xs, ys = zip(*[geo.xy(*c) for c in cells])
        xa, xb = int(min(xs) - m * p), int(math.ceil(max(xs) + m * p))
        ya, yb = int(min(ys) - m * p), int(math.ceil(max(ys) + m * p))
        ex[max(0, ya):max(0, yb + 1), max(0, xa):max(0, xb + 1)] = True
    for o in b['obstacles']:
        k = o['kind']
        if k == 'tape':
            rect(o['cells'], 0.62)
        elif k == 'key':
            rect(o['cells'], 0.8)
        elif k in ('door', 'box', 'curtain'):
            rect(o['cells'], 0.72)
        elif k == 'pipe':
            for c in o['cells']:
                rect([c], 0.66)
            if o.get('counter_at'):
                rect([o['counter_at']], 0.9)
        elif k == 'elevator':
            pass          # the platform is under its arrows (lavender, not ink)
    if not geo.phone and rj is not None:
        for o in rj.get('obstacles', []):
            if o['kind'] in ('hand', 'text', 'unknown') and o.get('bbox_px'):
                x0, y0, x1, y1 = o['bbox_px']
                ex[max(0, y0 - 4):y1 + 5, max(0, x0 - 4):x1 + 5] = True
    return ex


def board_box(b, geo, shape):
    cs = [c for a in b['arrows'] for c in a['cells']] + [c for o in b['obstacles'] for c in o['cells']]
    xs, ys = zip(*[geo.xy(*c) for c in cs])
    m = 1.2 * geo.p
    x0, y0 = max(0, int(min(xs) - m)), max(0, int(min(ys) - m))
    x1, y1 = min(shape[1], int(max(xs) + m)), min(shape[0], int(max(ys) + m))
    if not geo.phone:
        y0, y1 = max(y0, vextract.BAND_Y0), min(y1, vextract.BAND_Y1)
    return x0, y0, x1, y1


def score(R, I, valid):
    R = R & valid
    I = I & valid
    uni = (R | I).sum()
    inter = (R & I).sum()
    Rd = ndimage.binary_dilation(R, iterations=1)
    Id = ndimage.binary_dilation(I, iterations=1)
    missed = I & ~Rd
    extra = R & ~Id
    return dict(iou=inter / max(1, uni), tol1=1 - (missed.sum() + extra.sum()) / max(1, uni), union=int(uni),
                missed=missed, extra=extra, Rd=Rd, Id=Id)


def depth(mask, other_dilated):
    """deepest pixel of `mask` measured to the nearest pixel NOT in the mask (px)"""
    if not mask.any():
        return 0.0
    return float(ndimage.distance_transform_edt(mask).max())


# ------------------------------------------------------------------------------------------------ one level
def prove(b, rj, cap_path, fit=True, arrows_override=None, region=None):
    """`region(geo, shape) -> (box, valid)` replaces the board box and the obstacle exclusion (the reveal proof)"""
    im = np.array(Image.open(cap_path).convert('RGB'))
    geo = Geo(b, rj)
    st = default_style(geo.phone, rj)
    arrows = arrows_override if arrows_override is not None else \
        [a for a in b['arrows'] if a.get('hidden_by') is None and a.get('layer', 1) == 1]
    ink_full = capture_ink(im, geo.phone)
    if region is None:
        box = board_box(b, geo, im.shape)
        x0, y0, x1, y1 = box
        # the exclusion is decided once, on the research grid (its margins are ≥ 0.6 pitch; the refinement moves < 3 px)
        valid = ~exclusion(b, rj, geo, im.shape)[y0:y1, x0:x1]
    else:
        box, valid = region(geo, im.shape)
        x0, y0, x1, y1 = box
    I_valid = ink_full[y0:y1, x0:x1] & valid

    def evaluate():
        R, per = render(arrows, geo, st, im.shape, box)
        return score(R, ink_full[y0:y1, x0:x1], valid), R, per, valid

    def iou_only():
        R, _ = render(arrows, geo, st, im.shape, box)
        R &= valid
        return (R & I_valid).sum() / max(1, (R | I_valid).sum())

    best = iou_only()
    if fit:
        def try_set(setter, vals):
            nonlocal best
            cur = None
            for v in vals:
                old = setter(None)
                setter(v)
                s = iou_only()
                if s > best + 1e-9:
                    best, cur = s, v
                else:
                    setter(old)
            return cur

        def g_dx(v):
            if v is None:
                return geo.dx
            geo.dx = v

        def g_dy(v):
            if v is None:
                return geo.dy
            geo.dy = v

        def g_k(v):
            if v is None:
                return geo.k
            geo.k = v
        for rnd in range(3):
            start_best = best
            sc = [1.0, 0.5, 0.25][rnd]
            for g, s in ((g_dx, sc), (g_dy, sc)):
                c = g(None)
                try_set(g, [c - 2 * s, c - s, c + s, c + 2 * s])
            c = geo.k
            try_set(g_k, [c * (1 - 0.002 * sc), c * (1 + 0.002 * sc), c * (1 - 0.004 * sc), c * (1 + 0.004 * sc)])
            for key in ('wv', 'wh', 'tip_h', 'tip_up', 'tip_down', 'length', 'half', 'rad', 'fillet'):
                if geo.phone and key == 'wh':
                    continue          # the phone draws one stroke width (STYLE §A); wh follows wv

                def setter(v, key=key):
                    if v is None:
                        return st[key]
                    st[key] = min(max(v, BOUNDS[key][0]), BOUNDS[key][1])
                    if geo.phone and key == 'wv':
                        st['wh'] = st['wv']
                c = st[key]
                s = STEPS[key] * (1.0 if rnd < 2 else 0.5)
                try_set(setter, [c - 2 * s, c - s, c + s, c + 2 * s])
            if abs(geo.dx) > 3 or abs(geo.dy) > 3 or abs(geo.k - 1) > 0.006:
                break                 # the registration must stay a refinement
            if rnd >= 1 and best - start_best < 2e-5:
                break                 # converged
    sc_, R, per, valid = evaluate()
    I = ink_full[y0:y1, x0:x1] & valid
    w = min(st['wv'], st['wh']) * geo.p
    worst_cov, worst_id = 1.0, None
    for a, pm in zip(arrows, per):
        if pm is None:
            continue
        ox, oy, mk = pm
        sub_valid = valid[oy:oy + mk.shape[0], ox:ox + mk.shape[1]]
        sub_I = sc_['Id'][oy:oy + mk.shape[0], ox:ox + mk.shape[1]]
        m = mk & sub_valid
        if m.sum() < 10:
            continue
        cov = (m & sub_I).sum() / m.sum()
        if cov < worst_cov:
            worst_cov, worst_id = cov, a['id']
    res = dict(level=b['level'], source=b['source'], capture=os.path.relpath(cap_path, APP),
               iou=round(float(sc_['iou']), 4), tol1=round(float(sc_['tol1']), 4), union_px=sc_['union'],
               missed_px=int(sc_['missed'].sum()), extra_px=int(sc_['extra'].sum()),
               max_missed_depth_px=round(depth(sc_['missed'], None), 2), max_extra_depth_px=round(depth(sc_['extra'], None), 2),
               stroke_px=round(w, 2), worst_arrow_coverage=round(float(worst_cov), 3), worst_arrow=worst_id,
               arrows_drawn=len(arrows), excluded_share=round(float((~valid).mean()), 3),
               registration=dict(dx=round(geo.dx, 3), dy=round(geo.dy, 3), pitch_scale=round(geo.k, 5), pitch_px=round(geo.p, 3)),
               style={k: round(v, 4) for k, v in st.items()})
    # 1-px-tolerance residue is at most one (diagonal) pixel deep (EDT ≤ 1.42); a missing / extra stroke or head part of any
    # shipped stroke width (≥ 3.5 px) is ≥ 2 px deep
    res['depth_ok'] = max(res['max_missed_depth_px'], res['max_extra_depth_px']) <= DEPTH_GATE
    res['coverage_ok'] = res['worst_arrow_coverage'] >= 0.9
    res['gate'] = GATE[b['source']]
    res['pass'] = res['tol1'] >= res['gate']
    return res, dict(im=im, box=box, missed=sc_['missed'], extra=sc_['extra'], geo=geo, arrows=arrows, valid=valid)


def overlay_png(b, res, vis, path):
    im = Image.fromarray(vis['im'])
    x0, y0, x1, y1 = vis['box']
    crop = im.crop((x0, y0, x1, y1))
    crop = Image.blend(crop, Image.new('RGB', crop.size, (255, 255, 255)), 0.6)
    arr = np.array(crop)
    arr[~vis['valid']] = (arr[~vis['valid']] * 0.75 + np.array([200, 200, 200]) * 0.25).astype(np.uint8)
    arr[vis['missed']] = (255, 0, 0)
    arr[vis['extra']] = (255, 150, 0)
    crop = Image.fromarray(arr)
    dr = ImageDraw.Draw(crop)
    geo = vis['geo']
    for a in vis['arrows']:
        pts = [(geo.xy(*c)[0] - x0, geo.xy(*c)[1] - y0) for c in a['cells']]
        dr.line(pts, fill=(0, 160, 0), width=1)
    scale = 900.0 / max(crop.size)
    if scale < 1:
        crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
    canvas = Image.new('RGB', (crop.width, crop.height + 34), (255, 255, 255))
    canvas.paste(crop, (0, 34))
    d2 = ImageDraw.Draw(canvas)
    d2.text((4, 2), 'L%d %s  IoU %.4f  tol1 %.4f (gate %.2f) %s' % (b['level'], b['source'], res['iou'], res['tol1'], res['gate'],
                                                                   'PASS' if res['pass'] else 'FAIL'), fill=(0, 0, 0))
    d2.text((4, 17), 'depth missed/extra %.1f/%.1f px (stroke %.1f)  worst arrow cov %.3f  %s' % (
        res['max_missed_depth_px'], res['max_extra_depth_px'], res['stroke_px'], res['worst_arrow_coverage'],
        os.path.basename(res['capture'])), fill=(0, 0, 0))
    canvas.save(path)


def sheets(paths, out_dir, per=6):
    out = []
    for k in range(0, len(paths), per):
        ims = [Image.open(p) for p in paths[k:k + per]]
        w = max(i.width for i in ims)
        h = max(i.height for i in ims)
        cols = 3
        rows = (len(ims) + cols - 1) // cols
        sh = Image.new('RGB', (w * cols, h * rows), (230, 230, 230))
        for i, im in enumerate(ims):
            sh.paste(im, ((i % cols) * w, (i // cols) * h))
        p = os.path.join(out_dir, 'sheet-%02d.png' % (k // per))
        sh.save(p)
        out.append(p)
    return out


# ------------------------------------------------------------------------------------------------ negative controls
def mutations(b):
    vis = [a for a in b['arrows'] if a.get('hidden_by') is None and a.get('layer', 1) == 1]
    covered = {tuple(c) for o in b['obstacles'] if o['kind'] in ('tape', 'key') for c in o['cells']}
    free = [a for a in vis if not any(tuple(c) in covered for c in a['cells'])]
    muts = []
    short = min(free, key=lambda a: (len(a['cells']), a['id']))
    muts.append(('shortest arrow %d (%d cells) dropped' % (short['id'], len(short['cells'])),
                 [a for a in vis if a['id'] != short['id']]))
    straight = [a for a in free if len({a['dir']}) == 1 and all(
        (q[0] - p[0], q[1] - p[1]) == D[a['dir']] for p, q in zip(a['cells'], a['cells'][1:]))]
    if straight:
        s = min(straight, key=lambda a: (len(a['cells']), a['id']))
        opp = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}[s['dir']]
        rev = dict(s, cells=list(reversed(s['cells'])), dir=opp)
        muts.append(('straight arrow %d head flipped' % s['id'], [rev if a['id'] == s['id'] else a for a in vis]))
    longest = max(free, key=lambda a: (len(a['cells']), -a['id']))
    if len(longest['cells']) >= 3:
        cut = dict(longest, cells=longest['cells'][1:])
        muts.append(('arrow %d one cell shorter at its tail' % longest['id'], [cut if a['id'] == longest['id'] else a for a in vis]))
    return muts


# ------------------------------------------------------------------------------------------------ what the doors hide
def reveal_region(b, door, geo_shape_arrows):
    """the door's rectangle ± 0.5 cell, minus the art on the hidden arrows (keys, tapes) and minus the footprint of every
    start-visible arrow near the rectangle (present or already gone at that shot: not part of this proof)"""
    def fn(geo, shape):
        p = geo.p
        xs, ys = zip(*[geo.xy(*c) for c in door['cells']])
        x0, y0 = max(0, int(min(xs) - 1.2 * p)), max(0, int(min(ys) - 1.2 * p))
        x1, y1 = min(shape[1], int(max(xs) + 1.2 * p)), min(shape[0], int(max(ys) + 1.2 * p))
        H, W = y1 - y0, x1 - x0
        valid = np.zeros((H, W), bool)
        ax0, ay0 = int(min(xs) - 0.5 * p) - x0, int(min(ys) - 0.5 * p) - y0
        ax1, ay1 = int(math.ceil(max(xs) + 0.5 * p)) - x0, int(math.ceil(max(ys) + 0.5 * p)) - y0
        valid[max(0, ay0):ay1 + 1, max(0, ax0):ax1 + 1] = True
        hidden_ids = set(door.get('reveals', []))

        def cut(cells, m):
            cx, cy = zip(*[geo.xy(*c) for c in cells])
            a0, b0 = int(min(cx) - m * p) - x0, int(min(cy) - m * p) - y0
            a1, b1 = int(math.ceil(max(cx) + m * p)) - x0, int(math.ceil(max(cy) + m * p)) - y0
            valid[max(0, b0):max(0, b1 + 1), max(0, a0):max(0, a1 + 1)] = False
        for o in b['obstacles']:
            if o['kind'] == 'key' and set(o.get('arrows', [])) & hidden_ids:
                cut(o['cells'], 0.8)
            if o['kind'] == 'tape' and set(o.get('arrows', [])) & hidden_ids:
                cut(o['cells'], 0.62)
        # every OTHER obstacle's art (the neighbouring doors' frames and shading, pipes, boxes, visible keys and tapes), with
        # the start proof's margins; this door's own rectangle stays in
        others = dict(b, obstacles=[o for o in b['obstacles'] if o['id'] != door['id']])
        valid &= ~exclusion(others, None, geo, shape)[y0:y1, x0:x1]
        near = [a for a in b['arrows'] if a.get('hidden_by') is None and any(
            min(abs(c[0] - d[0]) + abs(c[1] - d[1]) for d in door['cells']) <= 2 for c in a['cells'])]
        if near:
            st = dict(wv=0.30, wh=0.30, tip_h=0.45, tip_up=0.45, tip_down=0.50, length=0.70, half=0.40, rad=0.0)
            R, _ = render(near, geo, st, shape, (x0, y0, x1, y1))
            valid &= ~ndimage.binary_dilation(R, iterations=2)
        return (x0, y0, x1, y1), valid
    return fn


def prove_reveals(argv, out, only):
    rows = []
    for name in sorted(os.listdir(LEVELS)):
        if not name.startswith('level_'):
            continue
        b = load_board(os.path.join(LEVELS, name))
        if b['source'] != 'recorded' or not any(o['kind'] == 'door' for o in b['obstacles']):
            continue
        if only and b['level'] not in only:
            continue
        rj = json.load(open(research_file(b)))
        bf = json.load(open(os.path.join(APP, 'design', 'tools', 'work', 'reveals', 'L%03d.json' % b['_rslot'])))
        shot_of = {d['order']: d['shot'] for d in bf['doors']}
        for door in sorted([o for o in b['obstacles'] if o['kind'] == 'door'], key=lambda o: o['order']):
            hidden = [a for a in b['arrows'] if a.get('hidden_by') == door['id']]
            shot = os.path.join(APP, 'research', 'bot', 'tmp', shot_of[door['order']])
            res, vis = prove(b, rj, shot, arrows_override=hidden, region=reveal_region(b, door, None))
            res.update(door=door['id'], order=door['order'], hidden_arrows=len(hidden), shot=os.path.relpath(shot, APP))
            if b['_rslot'] != b['level']:
                res['board'] = LO.label(b)
            png = os.path.join(out, 'L%03d-%s-reveal-overlay.png' % (b['level'], door['id']))
            overlay_png(b, res, vis, png)
            if '--negative' in argv and len(hidden) >= 2:
                res['negative_controls'] = []
                for mname, arrows in mutations(dict(b, arrows=[dict(a, hidden_by=None) for a in hidden], obstacles=[])):
                    mres, _ = prove(b, rj, shot, arrows_override=arrows, region=reveal_region(b, door, None))
                    res['negative_controls'].append(dict(mutation=mname, tol1=mres['tol1'],
                                                         caught_by_iou_gate=mres['tol1'] < res['gate'],
                                                         caught_by_local_check=not (mres['depth_ok'] and mres['coverage_ok'])))
            rows.append(res)
            print('L%03d%s door %s (order %d) %2d hidden arrows on %s: IoU %.4f tol1 %.4f %s | depth %.1f/%.1f cov %.3f%s' % (
                b['level'], board_note(b), door['id'], door['order'], len(hidden), os.path.basename(shot), res['iou'], res['tol1'],
                'PASS' if res['pass'] else 'FAIL', res['max_missed_depth_px'], res['max_extra_depth_px'],
                res['worst_arrow_coverage'], '' if res['depth_ok'] and res['coverage_ok'] else '  LOCAL-FLAG'), flush=True)
            for nc in res.get('negative_controls', []):
                print('      negative: %-40s tol1 %.4f -> %s' % (nc['mutation'], nc['tol1'], 'CAUGHT (%s)' % ', '.join(
                    x for x, y in (('IoU', nc['caught_by_iou_gate']), ('local', nc['caught_by_local_check'])) if y)
                    if nc['caught_by_iou_gate'] or nc['caught_by_local_check'] else 'MISSED'), flush=True)
    summ = dict(doors=len(rows), hidden_arrows=sum(r['hidden_arrows'] for r in rows), passed=sum(r['pass'] for r in rows),
                min_tol1=min([r['tol1'] for r in rows] or [None]),
                local_flags=['L%d %s' % (r['level'], r['door']) for r in rows if not (r['depth_ok'] and r['coverage_ok'])],
                table=rows)
    json.dump(summ, open(os.path.join(out, 'reveals-report.json' if not only else 'reveals-report-partial.json'), 'w'), indent=1)
    print('render --reveals: %d doors, %d hidden arrows, %d pass (min tol1 %s); local flags %s' % (
        len(rows), summ['hidden_arrows'], summ['passed'], summ['min_tol1'], summ['local_flags'] or 'none'))
    return 0 if summ['passed'] == len(rows) else 1


def main(argv):
    out = argv[argv.index('--out') + 1] if '--out' in argv else os.path.join(APP, 'build', 'l1', 'overlay')
    only = {int(x) for x in argv[argv.index('--levels') + 1].split(',')} if '--levels' in argv else None
    os.makedirs(out, exist_ok=True)
    if '--reveals' in argv:
        return prove_reveals(argv, out, only)
    rows, pngs = [], []
    t0 = time.time()
    for name in sorted(os.listdir(LEVELS)):
        if not name.startswith('level_'):
            continue
        b = load_board(os.path.join(LEVELS, name))
        if b['source'] not in GATE or (only and b['level'] not in only):
            continue
        rj = json.load(open(research_file(b)))
        cap = os.path.join(APP, b['capture'])
        res, vis = prove(b, rj, cap)
        if b['_rslot'] != b['level']:
            res['board'] = LO.label(b)
        png = os.path.join(out, 'L%03d-overlay.png' % b['level'])
        overlay_png(b, res, vis, png)
        pngs.append(png)
        if '--negative' in argv:
            res['negative_controls'] = []
            for mname, arrows in mutations(b):
                geo_fixed = dict(dx=res['registration']['dx'], dy=res['registration']['dy'])
                mres, _ = prove(b, rj, cap, fit=True, arrows_override=arrows)
                caught_iou = mres['tol1'] < res['gate']
                caught_local = not (mres['depth_ok'] and mres['coverage_ok'])
                res['negative_controls'].append(dict(mutation=mname, tol1=mres['tol1'], iou=mres['iou'],
                                                     max_missed_depth_px=mres['max_missed_depth_px'],
                                                     max_extra_depth_px=mres['max_extra_depth_px'],
                                                     worst_arrow_coverage=mres['worst_arrow_coverage'],
                                                     caught_by_iou_gate=caught_iou, caught_by_local_check=caught_local))
        rows.append(res)
        print('L%03d %-8s IoU %.4f tol1 %.4f gate %.2f %s | depth %.1f/%.1f px (stroke %.1f) cov %.3f%s%s' % (
            b['level'], b['source'], res['iou'], res['tol1'], res['gate'], 'PASS' if res['pass'] else 'FAIL',
            res['max_missed_depth_px'], res['max_extra_depth_px'], res['stroke_px'], res['worst_arrow_coverage'],
            '' if res['depth_ok'] and res['coverage_ok'] else '  LOCAL-FLAG', board_note(b)), flush=True)
        for nc in res.get('negative_controls', []):
            print('      negative: %-40s tol1 %.4f  depth %.1f/%.1f cov %.3f -> %s' % (
                nc['mutation'], nc['tol1'], nc['max_missed_depth_px'], nc['max_extra_depth_px'], nc['worst_arrow_coverage'],
                'CAUGHT (%s)' % ', '.join(x for x, y in (('IoU', nc['caught_by_iou_gate']), ('local', nc['caught_by_local_check'])) if y)
                if nc['caught_by_iou_gate'] or nc['caught_by_local_check'] else 'MISSED'), flush=True)
    sh = sheets(pngs, out) if '--sheet' in argv else []
    summ = dict(levels=len(rows), passed=sum(r['pass'] for r in rows),
                recorded=dict(n=sum(r['source'] == 'recorded' for r in rows),
                              min_tol1=min([r['tol1'] for r in rows if r['source'] == 'recorded'] or [None]),
                              passed=sum(r['pass'] for r in rows if r['source'] == 'recorded')),
                video=dict(n=sum(r['source'] == 'video' for r in rows),
                           min_tol1=min([r['tol1'] for r in rows if r['source'] == 'video'] or [None]),
                           passed=sum(r['pass'] for r in rows if r['source'] == 'video')),
                local_flags=[r['level'] for r in rows if not (r['depth_ok'] and r['coverage_ok'])],
                sheets=[os.path.relpath(p, APP) for p in sh], seconds=round(time.time() - t0, 1), table=rows)
    rp = os.path.join(out, 'report.json' if not only else 'report-partial.json')
    json.dump(summ, open(rp, 'w'), indent=1)
    print('render: %d levels, %d pass the IoU gate (recorded %d/%d, min tol1 %s; video %d/%d, min tol1 %s); local flags %s' % (
        len(rows), summ['passed'], summ['recorded']['passed'], summ['recorded']['n'], summ['recorded']['min_tol1'],
        summ['video']['passed'], summ['video']['n'], summ['video']['min_tol1'], summ['local_flags'] or 'none'))
    return 0 if summ['passed'] == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
