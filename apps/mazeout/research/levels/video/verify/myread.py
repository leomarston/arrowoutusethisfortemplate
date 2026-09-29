#!/usr/bin/env python3
"""Independent board reader for the verifier (does NOT import vextract, bcheck, ccheck, dcheck or bot.py).

usage: myread.py FRAME.png OUT.json [--obst box|pipe|none] [--overlay OUT.png] [--min-y 195] [--max-y 1115]

Method (written from scratch for the adversarial check):
- ink = saturated blue (B >= 170, R <= 90, G <= 0.72 B); obstacle colours: cyan (pipe / V2 box), purple (V1 box), pink (tie).
- grid: vertical-stroke and horizontal-stroke profiles folded modulo a trial pitch; the pitch maximises
  (profile at the teeth) - (profile half a pitch away); the phase is the folded peak. Square cells assumed; if the row fit is weak
  (no horizontal strokes) the row phase comes from stroke ends.
- cells: ink in a small window at the centre; edges: ink at 5 points between two centres (0.25 .. 0.75) -> a head tip (<= 0.5
  pitch) never makes an edge; paths = components of the edge graph; head = the end with ink 0.3 pitch beyond it and a wide base.
- obstacles: per-cell colour share; pipes ordered as a path, ends = degree-1 cells, out = away from the neighbour; counters by vocr.
"""
import json, sys, subprocess, argparse, os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
VOCR = os.path.join(HERE, '..', '..', '..', 'video-tools', 'vocr')
PT = 393.0 / 592.0


def masks(img):
    a = img.astype(np.int32)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    ink = (B >= 170) & (R <= 90) & (G <= 0.72 * B)
    cyan = (B >= 200) & (R <= 150) & (G >= 0.78 * B)
    purple = (R >= 110) & (B >= 170) & (G <= 120) & (R <= 0.9 * B)
    pink = (R >= 180) & (G <= 100) & (B >= 80) & (B <= 170)
    return ink, cyan, purple, pink


def fold_fit(profile, pmin, pmax, step=0.01, bins=128):
    xs = np.arange(len(profile), dtype=np.float64)
    w = profile.astype(np.float64)
    best = (-1e18, None, None)
    for p in np.arange(pmin, pmax, step):
        ph = (xs % p) / p
        h = np.bincount((ph * bins).astype(int) % bins, weights=w, minlength=bins)
        n = np.bincount((ph * bins).astype(int) % bins, minlength=bins).astype(np.float64)
        m = h / np.maximum(n, 1)
        # smooth lightly
        m = (np.roll(m, 1) + 2 * m + np.roll(m, -1)) / 4
        score = m - np.roll(m, bins // 2)
        k = int(np.argmax(score))
        if score[k] > best[0]:
            best = (score[k], p, k)
    sc, p, k = best
    # refine phase: centroid of the folded profile around the peak
    ph = (xs % p) / p
    idx = (ph * bins).astype(int) % bins
    h = np.bincount(idx, weights=w, minlength=bins) / np.maximum(np.bincount(idx, minlength=bins), 1)
    ks = [(k + d) % bins for d in range(-6, 7)]
    ang = np.array([(k + d) for d in range(-6, 7)], dtype=np.float64)
    wts = np.array([h[j] for j in ks]) - np.median(h)
    wts = np.clip(wts, 0, None)
    kc = (ang * wts).sum() / max(wts.sum(), 1e-9)
    phase = ((kc + 0.5) / bins) * p
    return p, phase % p, sc


def run_len_perp(ink, x, y, dx, dy, maxr):
    """length of the continuous ink run through (x,y) perpendicular to direction (dx,dy)."""
    px, py = -dy, dx
    H, W = ink.shape
    def at(t):
        xi, yi = int(round(x + px * t)), int(round(y + py * t))
        return 0 <= xi < W and 0 <= yi < H and ink[yi, xi]
    if not at(0) and not at(1) and not at(-1):
        return 0
    n = 0
    t = 0
    while t < maxr and (at(t) or at(t + 1)):
        t += 1
    a = t
    t = 0
    while t < maxr and (at(-t) or at(-t - 1)):
        t += 1
    return a + t


def band_has(ink, x, y, dx, dy, half):
    px, py = -dy, dx
    H, W = ink.shape
    for t in np.arange(-half, half + 0.01, 1.0):
        xi, yi = int(round(x + px * t)), int(round(y + py * t))
        if 0 <= xi < W and 0 <= yi < H and ink[yi, xi]:
            return True
    return False


def read(path, obst='none', min_y=195, max_y=1115, overlay=None):
    img = np.asarray(Image.open(path).convert('RGB'))
    H, W, _ = img.shape
    ink, cyan, purple, pink = masks(img)
    band = np.zeros_like(ink)
    band[min_y:max_y, :] = True
    ink &= band
    cyan &= band
    purple &= band
    pink &= band
    # vertical / horizontal stroke pixels
    k = 4
    V = ink.copy()
    V[k:-k] &= ink[:-2 * k] & ink[2 * k:]
    V[:k] = False; V[-k:] = False
    Hh = ink.copy()
    Hh[:, k:-k] &= ink[:, :-2 * k] & ink[:, 2 * k:]
    Hh[:, :k] = False; Hh[:, -k:] = False
    prof_x = V.sum(axis=0)
    prof_y = Hh.sum(axis=1)
    px_, phx, scx = fold_fit(prof_x, 19.0, 46.0)
    py_, phy, scy = fold_fit(prof_y, 19.0, 46.0)
    info = {'pitch_x_px': round(px_, 3), 'pitch_y_px': round(py_, 3), 'score_x': round(scx, 2), 'score_y': round(scy, 2)}
    p = px_
    if prof_y.sum() < 0.1 * prof_x.sum() or abs(py_ - px_) > 0.5:
        info['row_fit'] = 'weak: square cells + phase from stroke ends'
        # rows: phase from the extreme ink rows of vertical strokes; tails/caps end at centre +- stroke/2; heads extend further.
        ys = np.where(V.any(axis=1))[0]
        # use the most common (mod p) of stroke-end rows as a fallback: centre = end +- stroke/2
        top = ys.min(); bot = ys.max()
        phy = None
        cand = []
        for yv in range(top, bot + 1):
            cand.append(yv)
        # choose the phase maximising cells whose centres have ink across the columns
        best = (-1, 0)
        for ph in np.arange(0, p, 0.25):
            s = 0
            for yc in np.arange(ph, H, p):
                yi = int(round(yc))
                if min_y <= yi < max_y:
                    s += ink[yi, :].sum()
            best = max(best, (s, ph))
        phy = best[1]
    else:
        p = (px_ + py_) / 2
        info['pitch_used'] = 'mean of x and y'
    info['pitch_px'] = round(p, 3)
    info['phase_px'] = [round(phx, 3), round(phy, 3)]
    xs = np.arange(phx, W, p)
    ys = np.arange(phy, H, p)
    ys = ys[(ys >= min_y) & (ys < max_y)]
    xs = xs[(xs >= 2) & (xs < W - 2)]
    nx, ny = len(xs), len(ys)
    r = max(2, int(round(0.12 * p)))
    r_ob = max(3, int(round(0.30 * p)))

    def share(m, x, y, rad):
        x0, x1 = int(round(x - rad)), int(round(x + rad)) + 1
        y0, y1 = int(round(y - rad)), int(round(y + rad)) + 1
        return m[max(0, y0):y1, max(0, x0):x1].mean()

    occ = np.zeros((nx, ny), bool)
    obcell = np.zeros((nx, ny), bool)
    pinkcell = np.zeros((nx, ny), bool)
    # pipes: any pale/cyan blue that is not arrow ink and not background, eroded by 2 px (kills 1-px anti-aliasing along
    # arrow strokes and grid dots; keeps the tube, the mouth rings and the badge disc)
    from scipy.ndimage import binary_erosion
    a_ = img.astype(np.int32)
    pipeish = (a_[..., 0] <= 215) & (a_[..., 2] >= 150) & (a_[..., 1] >= 0.74 * a_[..., 2]) & ~ink & band
    pipeish = binary_erosion(pipeish, iterations=2)
    obm = {'pipe': pipeish, 'box': cyan | purple, 'none': None}[obst]
    ob_thr = {'pipe': 0.15, 'box': 0.30, 'none': 1}[obst]
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            if obm is not None and share(obm, x, y, r_ob) >= ob_thr:
                obcell[i, j] = True
            if share(pink, x, y, r_ob) >= 0.20:
                pinkcell[i, j] = True
            if not obcell[i, j] and share(ink, x, y, r) >= 0.25:
                occ[i, j] = True
    # stroke width estimate
    widths = []
    edges = {}
    for i in range(nx):
        for j in range(ny):
            if not occ[i, j]:
                continue
            for di, dj in ((1, 0), (0, 1)):
                i2, j2 = i + di, j + dj
                if i2 >= nx or j2 >= ny or not occ[i2, j2]:
                    continue
                x, y = xs[i], ys[j]
                ok = True
                for t in (0.25, 0.4, 0.5, 0.6, 0.75):
                    if not band_has(ink, x + di * p * t, y + dj * p * t, di, dj, max(2.0, 0.10 * p)):
                        ok = False
                        break
                if ok:
                    edges.setdefault((i, j), []).append((i2, j2))
                    edges.setdefault((i2, j2), []).append((i, j))
                    widths.append(run_len_perp(ink, x + di * p * 0.5, y + dj * p * 0.5, di, dj, int(p)))
    stroke = float(np.median(widths)) if widths else 6.0
    info['stroke_px'] = stroke
    # components
    seen = set()
    arrows = []
    anomalies = []
    for i in range(nx):
        for j in range(ny):
            if not occ[i, j] or (i, j) in seen:
                continue
            comp = []
            st = [(i, j)]
            seen.add((i, j))
            while st:
                c = st.pop()
                comp.append(c)
                for n in edges.get(c, []):
                    if n not in seen:
                        seen.add(n)
                        st.append(n)
            deg = {c: len(edges.get(c, [])) for c in comp}
            if len(comp) == 1:
                anomalies.append({'kind': 'single_cell', 'cell': comp[0]})
                continue
            ends = [c for c in comp if deg[c] == 1]
            if max(deg.values()) > 2 or len(ends) != 2:
                anomalies.append({'kind': 'not_a_path', 'cells': sorted(comp), 'deg3': [c for c in comp if deg[c] > 2]})
                continue
            # order from ends[0]
            order = [ends[0]]
            prev = None
            cur = ends[0]
            while True:
                nxt = [n for n in edges[cur] if n != prev]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                order.append(cur)
            # head test on both ends
            def headscore(end, nb):
                di, dj = end[0] - nb[0], end[1] - nb[1]
                x, y = xs[end[0]], ys[end[1]]
                # reach: how far the ink continues beyond the end cell centre along the arrow's line (tail cap ~ stroke/2,
                # head tip ~ 0.3-0.5 pitch); width: perpendicular run just behind the centre (head base is wide)
                t, gap, reach = 0.0, 0.0, 0.0
                while t < 0.7 * p:
                    if band_has(ink, x + di * t, y + dj * t, di, dj, 1.0):
                        reach, gap = t, 0.0
                    else:
                        gap += 0.5
                        if gap > 1.5:
                            break
                    t += 0.5
                w = run_len_perp(ink, x + di * 0.05 * p, y + dj * 0.05 * p, di, dj, int(p))
                return reach, w
            (r0_, w0), (r1_, w1) = headscore(order[0], order[1]), headscore(order[-1], order[-2])
            s0, s1 = r0_ + 0.5 * w0, r1_ + 0.5 * w1
            if s1 >= s0:
                cells = order
            else:
                cells = order[::-1]
            if abs(r1_ - r0_) < 0.10 * p or (r1_ - r0_) * (w1 - w0) < 0:
                anomalies.append({'kind': 'head_ambiguous', 'cells': [cells[0], cells[-1]], 'reach': [r0_, r1_], 'widths': [w0, w1]})
            di, dj = cells[-1][0] - cells[-2][0], cells[-1][1] - cells[-2][1]
            d = {(1, 0): 'right', (-1, 0): 'left', (0, 1): 'down', (0, -1): 'up'}[(di, dj)]
            arrows.append({'cells': cells, 'dir': d})
    # obstacles
    obstacles = []
    if obst != 'none':
        seen = set()
        for i in range(nx):
            for j in range(ny):
                if not obcell[i, j] or (i, j) in seen:
                    continue
                comp = []
                st = [(i, j)]
                seen.add((i, j))
                while st:
                    c = st.pop()
                    comp.append(c)
                    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        n = (c[0] + di, c[1] + dj)
                        if 0 <= n[0] < nx and 0 <= n[1] < ny and obcell[n] and n not in seen:
                            seen.add(n)
                            st.append(n)
                ob = {'kind': obst, 'cells': sorted(comp)}
                cx = [xs[c[0]] for c in comp]
                cy = [ys[c[1]] for c in comp]
                ob['bbox_px'] = [int(min(cx) - p / 2), int(min(cy) - p / 2), int(max(cx) + p / 2), int(max(cy) + p / 2)]
                if obst == 'pipe':
                    s = set(comp)
                    nb = {c: [n for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)) if n in s] for c in comp}
                    ends = [c for c in comp if len(nb[c]) == 1]
                    ob['ends'] = []
                    for e in ends:
                        n = nb[e][0]
                        d = {(1, 0): 'right', (-1, 0): 'left', (0, 1): 'down', (0, -1): 'up'}[(e[0] - n[0], e[1] - n[1])]
                        ob['ends'].append({'cell': e, 'out': d})
                    if len(ends) != 2 or max(len(v) for v in nb.values()) > 2:
                        ob['anomaly'] = 'pipe not a simple path'
                obstacles.append(ob)
        if obst == 'box':
            # the lock/bomb and rounded corners are not box colour: merge blobs within one cell, keep the bounding rectangle
            merged = True
            while merged:
                merged = False
                for a1 in range(len(obstacles)):
                    for a2 in range(a1 + 1, len(obstacles)):
                        A, B = obstacles[a1]['cells'], obstacles[a2]['cells']
                        if min(abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) for p1 in A for p2 in B) <= 2:
                            obstacles[a1]['cells'] = sorted(set(A) | set(B))
                            del obstacles[a2]
                            merged = True
                            break
                    if merged:
                        break
            for ob in obstacles:
                cs = ob['cells']
                ob['raw_cells'] = len(cs)
                i0, i1 = min(c[0] for c in cs), max(c[0] for c in cs)
                j0, j1 = min(c[1] for c in cs), max(c[1] for c in cs)
                ob['cells'] = [(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)]
                ob['bbox_px'] = [int(xs[i0] - p / 2), int(ys[j0] - p / 2), int(xs[i1] + p / 2), int(ys[j1] + p / 2)]
    # normalise to the bounding box of arrows + obstacles
    allc = [c for a in arrows for c in a['cells']] + [c for o in obstacles for c in o['cells']]
    c0 = min(c[0] for c in allc); r0 = min(c[1] for c in allc)
    c1 = max(c[0] for c in allc); r1 = max(c[1] for c in allc)
    sh = lambda c: [int(c[0] - c0), int(c[1] - r0)]
    out_arrows = [{'id': k, 'cells': [sh(c) for c in a['cells']], 'dir': a['dir']} for k, a in enumerate(arrows)]
    out_obst = []
    for o in obstacles:
        oo = dict(o)
        oo['cells'] = [sh(c) for c in o['cells']]
        if 'ends' in oo:
            oo['ends'] = [{'cell': sh(e['cell']), 'out': e['out']} for e in o['ends']]
        out_obst.append(oo)
    for an in anomalies:
        for key in ('cell',):
            if key in an:
                an[key] = sh(an[key])
        for key in ('cells', 'deg3'):
            if key in an:
                an[key] = [sh(c) for c in an[key]]
    origin_px = (xs[c0], ys[r0])
    res = {'reader': 'verify/myread.py (independent)', 'frame': path, 'cols': int(c1 - c0 + 1), 'rows': int(r1 - r0 + 1),
           'pitch_pt': round(p * PT, 3), 'origin_pt': [round(origin_px[0] * PT, 2), round(origin_px[1] * PT, 2)],
           'stroke_pt': round(stroke * PT, 2), 'arrows': out_arrows, 'obstacles': out_obst, 'anomalies': anomalies, 'fit': info}
    if overlay:
        im = Image.fromarray(img).convert('RGB')
        big = Image.new('RGB', (W * 2, H), 'white')
        big.paste(im, (0, 0))
        dr = ImageDraw.Draw(big)
        pal = [(230, 25, 75), (60, 180, 75), (245, 130, 48), (145, 30, 180), (0, 130, 200), (240, 50, 230), (128, 128, 0), (0, 0, 0)]
        for o in obstacles:
            for c in o['cells']:
                x, y = W + xs[c[0]], ys[c[1]]
                dr.rectangle([x - p / 2 + 1, y - p / 2 + 1, x + p / 2 - 1, y + p / 2 - 1], fill=(170, 230, 250) if o['kind'] == 'pipe' else (220, 190, 250))
            for e in o.get('ends', []):
                c = e['cell']
                x, y = W + xs[c[0]], ys[c[1]]
                dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(0, 0, 0))
        for k2, a in enumerate(arrows):
            col = pal[k2 % len(pal)]
            pts = [(W + xs[c[0]], ys[c[1]]) for c in a['cells']]
            dr.line(pts, fill=col, width=3)
            x, y = pts[-1]
            dx, dy = a['cells'][-1][0] - a['cells'][-2][0], a['cells'][-1][1] - a['cells'][-2][1]
            tip = (x + dx * 0.45 * p, y + dy * 0.45 * p)
            b1 = (x - dy * 0.3 * p, y + dx * 0.3 * p)
            b2 = (x + dy * 0.3 * p, y - dx * 0.3 * p)
            dr.polygon([tip, b1, b2], fill=col)
            tx, ty = pts[0]
            dr.ellipse([tx - 3, ty - 3, tx + 3, ty + 3], outline=col, width=2)
        for an in anomalies:
            cs = an.get('cells') or [an.get('cell')]
            for c in cs:
                if c is None:
                    continue
                x, y = W + xs[c[0] + c0], ys[c[1] + r0]
                dr.rectangle([x - p / 2, y - p / 2, x + p / 2, y + p / 2], outline=(255, 0, 0), width=2)
        # grid points on the frame side
        for x in xs:
            for y in ys:
                dr.point((x, y), fill=(255, 0, 0))
        big.save(overlay)
    return res


def ocr_counter(frame, bbox, scale=4):
    x0, y0, x1, y1 = bbox
    try:
        outp = subprocess.run([VOCR, '--crop', str(x0), str(y0), str(x1 - x0), str(y1 - y0), '--scale', str(scale), frame],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception as e:  # noqa
        return None, str(e)
    digits = []
    for line in outp.splitlines():
        try:
            j = json.loads(line)
        except Exception:
            continue
        for ln in j.get('lines', []):
            t = ln.get('text', '') if isinstance(ln, dict) else str(ln)
            dd = ''.join(ch for ch in t if ch.isdigit())
            if dd:
                digits.append(dd)
    return (int(digits[0]) if digits else None), outp[:300]


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('frame')
    ap.add_argument('out')
    ap.add_argument('--obst', default='none', choices=['none', 'pipe', 'box'])
    ap.add_argument('--overlay')
    ap.add_argument('--min-y', type=int, default=195)
    ap.add_argument('--max-y', type=int, default=1115)
    a = ap.parse_args()
    res = read(a.frame, a.obst, a.min_y, a.max_y, a.overlay)
    for o in res['obstacles']:
        o['counter_ocr'], _ = ocr_counter(a.frame, o['bbox_px'])
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({'cols': res['cols'], 'rows': res['rows'], 'arrows': len(res['arrows']), 'obstacles':
                      [(o['kind'], len(o['cells']), o.get('counter_ocr'), o.get('ends')) for o in res['obstacles']],
                      'anomalies': res['anomalies'], 'fit': res['fit']}, indent=None))
