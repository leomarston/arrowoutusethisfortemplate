#!/usr/bin/env python3
"""batch C (levels 21-30) checks, run with ~/.venvs/mf3d/bin/python from anywhere:
  chk.py verify JSON [--frame F] [--out OVERLAY]   vextract.verify on a level JSON (+ blobs split heads / corners / elsewhere)
  CELL_EXCL=0.7 chk.py verify2 JSON               VIDEO-SKIN render (3x supersampled, rounded corners + heads, sub-px
                                                  registration); obstacles excluded per cell (+-0.7 pitch) instead of per bbox;
                                                  prints/stores (-verify2.json) IoU and every missed/extra blob >= 10 px with its
                                                  thickness (px / longest side: slivers ~1-2, a reversed head ~5, 77-114 px)
  chk.py solve JSON                               greedy solver on research/bot/bot.py ray() + tape bundles + box counters (every
                                                  removed arrow) + pipe counters (passes); + 30 random free-move orders; DFS if stuck
Companions: obst.py (obstacle presence + counter OCR timeline), corr.py (model passes/counters vs the video), fix.py (the hand
fixes of L23/L25/L29), build.py (writes research/levels/L0NN.json), grid.py / sbs.py (look-at images).
Work files: research/video-frames/work/levelsC/ (gitignored)."""
import json, os, sys
import numpy as np
from scipy import ndimage
MZ = '/Users/yago/Downloads/app-factory/apps/mazeout'
sys.path.insert(0, MZ + '/research/video-tools')
sys.path.insert(0, MZ + '/research/bot')
import vextract as vx
import bot as B

DIRS = vx.DIRS


def board_from_json(js):
    fp = js['fit_px']
    c0, r0 = fp['c0'], fp['r0']
    arrows = [dict(id=a['id'], cells=[(c[0] + c0, c[1] + r0) for c in a['cells']], dir=a['dir']) for a in js['arrows']
              if a.get('layer', 1) == 1]
    obst = [dict(o, cells=[(c[0] + c0, c[1] + r0) for c in o['cells']]) for o in js['obstacles']]
    cs = [c for a in arrows for c in a['cells']] + [c for o in obst for c in o['cells']]
    bounds = (min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs))
    fit = dict(pitch=fp['pitch'], x0=fp['x0'], y0=fp['y0'], stroke=fp['stroke'], resid_px=fp.get('resid_px', 0))
    return dict(fit=fit, arrows=arrows, obstacles=obst, bounds=bounds, anomalies=js.get('anomalies', []))


def cmd_verify(path, frame=None, out=None, minpx=12):
    js = json.load(open(path))
    frame = frame or os.path.join(MZ, js['frame'])
    im = vx.load(frame)
    b = board_from_json(js)
    ver, missed, extra = vx.verify(im, b)
    fp = js['fit_px']; p = fp['pitch']
    rep = dict(verify=ver, blobs=[])
    for name, m in (('missed', missed), ('extra', extra)):
        lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=1))
        for k in range(1, n + 1):
            ys, xs = np.nonzero((lab == k) & m)
            if len(ys) < minpx:
                continue
            cx, cy = xs.mean(), ys.mean()
            cc = (float((cx - fp['x0']) / p - fp['c0']), float((cy - fp['y0']) / p - fp['r0']))
            rep['blobs'].append(dict(kind=name, px=int(len(ys)), at_px=[int(cx), int(cy)], cell=[round(cc[0], 2), round(cc[1], 2)]))
    rep['blobs'].sort(key=lambda r: -r['px'])
    # head-free score: drop a disc of 0.62 pitch around every head tip region (triangle heads vs the video's rounded heads)
    hm = np.zeros(missed.shape, bool)
    yy, xx = np.mgrid[0:hm.shape[0], 0:hm.shape[1]]
    heads = []
    for a in b['arrows']:
        c = a['cells'][-1]; d = DIRS[a['dir']]
        hx = fp['x0'] + (c[0] + 0.15 * d[0]) * p; hy = fp['y0'] + (c[1] + 0.15 * d[1]) * p
        heads.append((hx, hy))
        y0_, y1_, x0_, x1_ = int(hy - p), int(hy + p) + 1, int(hx - p), int(hx + p) + 1
        sub = (yy[y0_:y1_, x0_:x1_] - hy) ** 2 + (xx[y0_:y1_, x0_:x1_] - hx) ** 2 <= (0.62 * p) ** 2
        hm[y0_:y1_, x0_:x1_] |= sub
    ink_ = vx.ink_mask(im)
    excl = np.zeros(ink_.shape, bool)
    for o in b['obstacles']:
        if o['kind'] == 'elevator':
            continue
        x0, y0, x1, y1 = o['bbox_px']
        excl[max(0, y0 - 3):y1 + 3, max(0, x0 - 3):x1 + 3] = True
    ink_ = ink_ & ~excl
    rm = vx.render(b, ink_.shape, head_tip=ver['head']['tip'], head_base=ver['head']['base'], head_half=ver['head']['half'],
                   width=ver['stroke_px']) & ~excl
    uni = (rm | ink_) & ~hm
    mis2 = missed & ~hm; ext2 = extra & ~hm
    rep['verify']['ink_iou_tol1px_bodies'] = round(1 - (mis2.sum() + ext2.sum()) / max(1, uni.sum()), 4)
    joints = []
    for a in b['arrows']:
        cs_ = a['cells']
        joints.append(cs_[0])
        for i in range(1, len(cs_) - 1):
            d1 = (cs_[i][0] - cs_[i - 1][0], cs_[i][1] - cs_[i - 1][1]); d2 = (cs_[i + 1][0] - cs_[i][0], cs_[i + 1][1] - cs_[i][1])
            if d1 != d2:
                joints.append(cs_[i])
    jpx = [(fp['x0'] + c[0] * p, fp['y0'] + c[1] * p) for c in joints]
    for r in rep['blobs']:
        x, y = r['at_px']
        r['near_head'] = any((x - hx) ** 2 + (y - hy) ** 2 <= (0.75 * p) ** 2 for hx, hy in heads)
        r['near_joint'] = any((x - hx) ** 2 + (y - hy) ** 2 <= (0.6 * p) ** 2 for hx, hy in jpx)
    out = out or os.path.splitext(path)[0] + '-overlay.png'
    vx.overlay(im, b, out, note='%s IoU %.3f (tol1 %.3f)' % (os.path.basename(path), ver['ink_iou'], ver['ink_iou_tol1px']),
               missed=missed, extra=extra)
    rep['overlay'] = out
    print(json.dumps(rep['verify']))
    body = [r for r in rep['blobs'] if not r['near_head'] and not r['near_joint']]
    print('blobs >= %d px: %d (at heads %d, at corners/tails %d, elsewhere %d); elsewhere:' % (minpx, len(rep['blobs']),
          sum(r['near_head'] for r in rep['blobs']), sum((not r['near_head']) and r['near_joint'] for r in rep['blobs']), len(body)))
    rep['suspicious'] = body
    for r in body[:40]:
        print('  ', r['kind'], r['px'], 'px at', r['at_px'], 'cell', r['cell'])
    return rep


# ------------------------------------------------------------------ solver (bot.py ray/free rules + counters)
def solve(js, verbose=False, dfs_limit=200000):
    arrows = {a['id']: dict(a, cells=[tuple(c) for c in a['cells']]) for a in js['arrows']}
    alive0 = frozenset(i for i, a in arrows.items() if a.get('layer', 1) == 1)
    tapes = []
    for o in js['obstacles']:
        if o['kind'] == 'tape_pink':
            cs = set(map(tuple, o['cells']))
            ids = sorted(a['id'] for a in arrows.values() if any(c in cs for c in a['cells']))
            if ids:
                tapes.append(ids)
    # merge overlapping tape groups
    merged = []
    for g in tapes:
        g = set(g)
        for m in [m for m in merged if m & g]:
            g |= m; merged.remove(m)
        merged.append(g)
    unit_of = {}
    for g in merged:
        for i in g:
            unit_of[i] = tuple(sorted(g))
    boxes = [dict(cells=set(map(tuple, o['cells'])), counter=o.get('counter')) for o in js['obstacles'] if o['kind'] in ('box', 'curtain')]
    pipes = [dict(cells=set(map(tuple, pp['cells'])), ends={tuple(e['cell']): DIRS[e['out']] for e in pp['ends']}, counter=pp.get('counter'))
             for pp in js.get('pipes', [])]
    cs = [c for a in arrows.values() for c in a['cells']] + [tuple(c) for o in js['obstacles'] for c in o['cells']]
    bounds = (min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs))
    for b in boxes:
        if b['counter'] is None:
            raise SystemExit('box without counter')
    for pp in pipes:
        if pp['counter'] is None:
            raise SystemExit('pipe without counter')
    n_boxes, n_pipes = len(boxes), len(pipes)

    def state_board(pipe_left):
        return dict(bounds=bounds, pipes=[dict(cells=pipes[k]['cells'], ends=pipes[k]['ends']) for k in range(n_pipes) if pipe_left[k] > 0])

    def units(alive):
        seen = set(); out = []
        for i in sorted(alive):
            u = unit_of.get(i, (i,))
            u = tuple(x for x in u if x in alive)
            if u and u not in seen:
                seen.add(u); out.append(u)
        return out

    def free_units(alive, removed, pipe_left):
        bd = state_board(pipe_left)
        live_pipes = [k for k in range(n_pipes) if pipe_left[k] > 0]
        occ = {}
        for i in alive:
            for c in arrows[i]['cells']:
                occ[c] = i
        blk = set()
        for b in boxes:
            if removed < b['counter']:
                blk |= b['cells']
        for k in live_pipes:
            blk |= pipes[k]['cells']
        res = []
        for u in units(alive):
            ok = True; passes = []
            for i in u:
                info = {}
                r = B.ray(bd, arrows[i], info)
                for c in r:
                    if (c in occ and occ[c] not in u) or c in blk:
                        ok = False; break
                if not ok:
                    break
                passes += [live_pipes[k] for k in info.get('pipes', [])]
            if ok:
                res.append((u, passes))
        return res

    def apply(alive, removed, pipe_left, u, passes):
        pl = list(pipe_left)
        for k in passes:
            pl[k] -= 1
        return alive - set(u), removed + len(u), tuple(pl)

    # greedy: prefer units that do not pass a pipe, then the lowest id
    alive, removed, pl = alive0, 0, tuple(pp['counter'] for pp in pipes)
    seq = []
    while alive:
        fr = free_units(alive, removed, pl)
        if not fr:
            break
        fr.sort(key=lambda x: (len(x[1]) > 0, x[0]))
        u, passes = fr[0]
        seq.append(dict(unit=list(u), pipe_passes=passes, removed_before=removed))
        alive, removed, pl = apply(alive, removed, pl, u, passes)
    greedy_ok = not alive
    res = dict(greedy_solved=greedy_ok, greedy_steps=len(seq), greedy_left=sorted(alive), arrows=len(alive0),
               units=len(units(alive0)), tape_groups=[list(g) for g in merged], boxes=[b['counter'] for b in boxes],
               pipes=[pp['counter'] for pp in pipes])
    # pipe-agnostic check: does ANY greedy order get stuck? (random orders)
    import random
    stuck = 0; trials = 30
    for s in range(trials):
        rnd = random.Random(s)
        a_, r_, p_ = alive0, 0, tuple(pp['counter'] for pp in pipes)
        while a_:
            fr = free_units(a_, r_, p_)
            if not fr:
                break
            u, passes = rnd.choice(fr)
            a_, r_, p_ = apply(a_, r_, p_, u, passes)
        stuck += bool(a_)
    res['random_orders_stuck'] = '%d/%d' % (stuck, trials)
    if not greedy_ok:
        # DFS with memo
        seen = set(); nodes = [0]

        def dfs(a_, r_, p_, path):
            if not a_:
                return path
            key = (a_, p_)
            if key in seen or nodes[0] > dfs_limit:
                return None
            seen.add(key); nodes[0] += 1
            for u, passes in sorted(free_units(a_, r_, p_), key=lambda x: (len(x[1]) > 0, x[0])):
                na, nr, np_ = apply(a_, r_, p_, u, passes)
                got = dfs(na, nr, np_, path + [list(u)])
                if got is not None:
                    return got
            return None
        sol = dfs(alive0, 0, tuple(pp['counter'] for pp in pipes), [])
        res['dfs_solved'] = sol is not None
        res['dfs_nodes'] = nodes[0]
        if sol:
            res['dfs_steps'] = len(sol)
    res['sequence'] = seq
    return res


def cmd_solve(path):
    js = json.load(open(path))
    r = solve(js)
    print(json.dumps({k: v for k, v in r.items() if k != 'sequence'}))
    return r


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'verify':
        fr = a[a.index('--frame') + 1] if '--frame' in a else None
        out = a[a.index('--out') + 1] if '--out' in a else None
        cmd_verify(a[1], fr, out)
    elif a[0] == 'solve':
        cmd_solve(a[1])


# ------------------------------------------------------------------ verify2: video-skin renderer (rounded corners + heads, sub-px fit)
from PIL import Image, ImageDraw
import math
SS = 3
CELL_EXCL = float(os.environ.get('CELL_EXCL', '0'))


def render2(arrows, box, prm):
    """arrows: [(cells in grid coords, (dx,dy))]; box = (bx0, by0, bx1, by1) px crop; prm: pitch x0 y0 k sw rc tip half base rr"""
    bx0, by0, bx1, by1 = box
    W, H = bx1 - bx0, by1 - by0
    img = Image.new('L', (W * SS, H * SS), 0)
    dr = ImageDraw.Draw(img)
    p = prm['pitch'] * prm['k']
    cx0 = prm['cx']; cy0 = prm['cy']    # scale centre (px)

    def P(c):
        x = prm['x0'] + c[0] * prm['pitch']; y = prm['y0'] + c[1] * prm['pitch']
        x = cx0 + (x - cx0) * prm['k'] + prm['dx']; y = cy0 + (y - cy0) * prm['k'] + prm['dy']
        return ((x - bx0) * SS, (y - by0) * SS)
    sw = prm['sw'] * SS; rc = prm['rc'] * SS; pS = p * SS
    heads = []
    for cells, d in arrows:
        pts = [P(c) for c in cells]
        hx, hy = pts[-1]
        base = (hx - d[0] * prm['base'] * pS, hy - d[1] * prm['base'] * pS)
        if len(pts) == 1:
            line = [(hx - d[0] * 0.3 * pS, hy - d[1] * 0.3 * pS), base]
        else:
            line = pts[:-1] + [base]
        # round the corners
        out = [line[0]]
        for i in range(1, len(line) - 1):
            V = line[i]; A_ = line[i - 1]; B_ = line[i + 1]
            din = (V[0] - A_[0], V[1] - A_[1]); dout = (B_[0] - V[0], B_[1] - V[1])
            ni = math.hypot(*din) or 1; no = math.hypot(*dout) or 1
            din = (din[0] / ni, din[1] / ni); dout = (dout[0] / no, dout[1] / no)
            if abs(din[0] * dout[1] - din[1] * dout[0]) < 0.5:
                out.append(V); continue
            r_ = min(rc, 0.49 * ni, 0.49 * no)
            C = (V[0] - din[0] * r_ + dout[0] * r_, V[1] - din[1] * r_ + dout[1] * r_)
            u = (-dout[0], -dout[1]); v = din
            for j in range(9):
                th = j / 8 * math.pi / 2
                out.append((C[0] + r_ * (u[0] * math.cos(th) + v[0] * math.sin(th)), C[1] + r_ * (u[1] * math.cos(th) + v[1] * math.sin(th))))
        out.append(line[-1])
        dr.line(out, fill=255, width=max(1, int(round(sw))), joint='curve')
        rr_ = sw / 2
        for (x, y) in (out[0], out[-1]):
            dr.ellipse([x - rr_, y - rr_, x + rr_, y + rr_], fill=255)
        tip = (hx + d[0] * prm['tip'] * pS, hy + d[1] * prm['tip'] * pS)
        l = (base[0] - d[1] * prm['half'] * pS, base[1] + d[0] * prm['half'] * pS)
        r2 = (base[0] + d[1] * prm['half'] * pS, base[1] - d[0] * prm['half'] * pS)
        heads.append([tip, l, r2])
    arr = np.array(img) > 0
    rr = prm['rr'] * SS
    if heads:
        for tri in heads:
            xs = [q[0] for q in tri]; ys = [q[1] for q in tri]
            ax0, ay0 = int(min(xs)) - 2, int(min(ys)) - 2
            ax1, ay1 = int(max(xs)) + 3, int(max(ys)) + 3
            pw, ph = ax1 - ax0, ay1 - ay0
            pim = Image.new('L', (pw, ph), 0)
            ImageDraw.Draw(pim).polygon([(q[0] - ax0, q[1] - ay0) for q in tri], fill=255)
            pa = np.array(pim) > 0
            if rr >= 1:
                R = int(round(rr)); yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
                st = (xx ** 2 + yy ** 2) <= R * R
                pa = ndimage.binary_opening(pa, structure=st)
            y0c, x0c = max(0, ay0), max(0, ax0)
            y1c, x1c = min(arr.shape[0], ay1), min(arr.shape[1], ax1)
            if y1c > y0c and x1c > x0c:
                arr[y0c:y1c, x0c:x1c] |= pa[y0c - ay0:y1c - ay0, x0c - ax0:x1c - ax0]
    cov = arr.reshape(H, SS, W, SS).mean((1, 3))
    return cov >= 0.5


def verify2(js, im, fit_params=True, log=False):
    fp = js['fit_px']
    c0, r0 = fp['c0'], fp['r0']
    arrows = [([(c[0] + c0, c[1] + r0) for c in a['cells']], DIRS[a['dir']]) for a in js['arrows'] if a.get('layer', 1) == 1]
    ink = vx.ink_mask(im)
    excl = np.zeros(ink.shape, bool)
    p = fp['pitch']
    for o in js['obstacles']:
        if o['kind'] == 'elevator':
            continue
        if CELL_EXCL:
            h = CELL_EXCL * p
            for c in o['cells']:
                x = fp['x0'] + (c[0] + c0) * p; y = fp['y0'] + (c[1] + r0) * p
                excl[max(0, int(y - h)):int(y + h) + 1, max(0, int(x - h)):int(x + h) + 1] = True
            continue
        x0, y0, x1, y1 = o['bbox_px']
        excl[max(0, y0 - 3):y1 + 3, max(0, x0 - 3):x1 + 3] = True
    xs = [fp['x0'] + c[0] * p for cs, _ in arrows for c in cs]; ys = [fp['y0'] + c[1] * p for cs, _ in arrows for c in cs]
    bx0, by0 = max(0, int(min(xs) - 1.2 * p)), max(vx.BAND_Y0, int(min(ys) - 1.2 * p))
    bx1, by1 = min(ink.shape[1], int(max(xs) + 1.2 * p)), min(vx.BAND_Y1, int(max(ys) + 1.2 * p))
    box = (bx0, by0, bx1, by1)
    inkc = (ink & ~excl)[by0:by1, bx0:bx1]
    exc = excl[by0:by1, bx0:bx1]
    # ink outside the crop box counts as missed
    outside = int((ink & ~excl).sum() - inkc.sum())
    prm = dict(pitch=p, x0=fp['x0'], y0=fp['y0'], k=1.0, dx=0.0, dy=0.0, sw=float(fp['stroke']), rc=0.5 * fp['stroke'],
               tip=0.40, half=0.30, base=0.22, rr=1.5, cx=(bx0 + bx1) / 2, cy=(by0 + by1) / 2)

    def score(pr):
        rm = render2(arrows, box, pr) & ~exc
        inter = (rm & inkc).sum(); uni = (rm | inkc).sum() + outside
        return inter / max(1, uni), rm
    best, _ = score(prm)
    if fit_params:
        steps = [('dx', [-1.0, -0.5, 0.5, 1.0]), ('dy', [-1.0, -0.5, 0.5, 1.0]), ('k', [-0.003, -0.0015, 0.0015, 0.003]),
                 ('sw', [-1.0, -0.5, 0.5, 1.0, 1.5]), ('rc', [-0.3 * fp['stroke'], 0.3 * fp['stroke'], 0.6 * fp['stroke']]),
                 ('tip', [-0.06, 0.06]), ('half', [-0.06, 0.06]), ('base', [-0.06, 0.06]), ('rr', [-1.0, 1.0, 2.0]),
                 ('dx', [-0.5, -0.25, 0.25, 0.5]), ('dy', [-0.5, -0.25, 0.25, 0.5]), ('sw', [-0.5, 0.5])]
        for rnd in range(2):
            for key, deltas in steps:
                cur = prm[key]; bv = cur
                for dlt in deltas:
                    t = dict(prm); t[key] = cur + dlt
                    if key in ('sw', 'rr', 'rc') and t[key] < 0:
                        continue
                    s, _ = score(t)
                    if s > best + 1e-5:
                        best, bv = s, cur + dlt
                prm[key] = bv
    iou, rm = score(prm)
    ink_d = ndimage.binary_dilation(inkc, iterations=1)
    rm_d = ndimage.binary_dilation(rm, iterations=1)
    missed = inkc & ~rm_d; extra = rm & ~ink_d
    tol = 1 - (missed.sum() + extra.sum() + outside) / max(1, (rm | inkc).sum() + outside)
    fullm = np.zeros(ink.shape, bool); fulle = np.zeros(ink.shape, bool)
    fullm[by0:by1, bx0:bx1] = missed; fulle[by0:by1, bx0:bx1] = extra
    fullm |= (ink & ~excl) & ~np.pad(np.ones((by1 - by0, bx1 - bx0), bool), ((by0, ink.shape[0] - by1), (bx0, ink.shape[1] - bx1)))
    res = dict(ink_iou2=round(float(iou), 4), ink_iou2_tol1px=round(float(tol), 4), missed_px=int(fullm.sum()), extra_px=int(fulle.sum()),
               params={k_: round(float(v), 4) for k_, v in prm.items() if k_ not in ('pitch', 'x0', 'y0', 'cx', 'cy')})
    return res, fullm, fulle


def cmd_verify2(path, frame=None, out=None, minpx=10):
    js = json.load(open(path))
    frame = frame or os.path.join(MZ, js['frame'])
    im = vx.load(frame)
    res, missed, extra = verify2(js, im)
    fp = js['fit_px']; p = fp['pitch']
    blobs = []
    for name, m in (('missed', missed), ('extra', extra)):
        lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=1))
        for k in range(1, n + 1):
            ys, xs = np.nonzero((lab == k) & m)
            if len(ys) < minpx:
                continue
            cx, cy = xs.mean(), ys.mean()
            thick = round(len(ys) / max(1, max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)), 2)
            blobs.append(dict(kind=name, px=int(len(ys)), thick=thick, at_px=[int(cx), int(cy)],
                              cell=[round(float((cx - fp['x0']) / p - fp['c0']), 2), round(float((cy - fp['y0']) / p - fp['r0']), 2)]))
    blobs.sort(key=lambda r: -r['px'])
    res['blobs_ge_%dpx' % minpx] = len(blobs)
    res['max_blob_px'] = max([b_['px'] for b_ in blobs] or [0])
    res['max_compact_blob_px'] = max([b_['px'] for b_ in blobs if b_['thick'] >= 3] or [0])
    print(json.dumps(res))
    for r in blobs[:25]:
        print('  ', r['kind'], r['px'], 'px thick', r['thick'], 'at', r['at_px'], 'cell', r['cell'])
    b = board_from_json(js)
    out = out or os.path.splitext(path)[0] + '-overlay2.png'
    vx.overlay(im, b, out, note='%s IoU2 %.3f (tol1 %.3f)' % (os.path.basename(path), res['ink_iou2'], res['ink_iou2_tol1px']),
               missed=missed, extra=extra)
    res['blobs'] = blobs
    res['cell_excl'] = CELL_EXCL
    json.dump(res, open(os.path.splitext(path)[0] + '-verify2.json', 'w'), indent=1)
    return res


if __name__ == '__main__' and sys.argv[1] == 'verify2':
    a = sys.argv[1:]
    fr = a[a.index('--frame') + 1] if '--frame' in a else None
    cmd_verify2(a[1], fr)


def rounds(js):
    """dependency depth: remove ALL free units at once per round (pipes: passes applied in id order within a round)"""
    arrows = {a['id']: dict(a, cells=[tuple(c) for c in a['cells']]) for a in js['arrows']}
    tapes = []
    for o in js['obstacles']:
        if o['kind'] == 'tape_pink':
            cs = set(map(tuple, o['cells']))
            ids = sorted(a['id'] for a in arrows.values() if any(c in cs for c in a['cells']))
            if ids:
                tapes.append(set(ids))
    unit_of = {i: tuple(sorted(g)) for g in tapes for i in g}
    boxes = [(set(map(tuple, o['cells'])), o['counter']) for o in js['obstacles'] if o['kind'] in ('box', 'curtain')]
    pipes = [dict(cells=set(map(tuple, pp['cells'])), ends={tuple(e['cell']): DIRS[e['out']] for e in pp['ends']}, counter=pp['counter'])
             for pp in js.get('pipes', [])]
    cs = [c for a in arrows.values() for c in a['cells']] + [tuple(c) for o in js['obstacles'] for c in o['cells']]
    bounds = (min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs))
    alive = set(arrows); removed = 0; left = [pp['counter'] for pp in pipes]; n = 0; widths = []
    while alive:
        live = [k for k in range(len(pipes)) if left[k] > 0]
        bd = dict(bounds=bounds, pipes=[dict(cells=pipes[k]['cells'], ends=pipes[k]['ends']) for k in live])
        occ = {c: i for i in alive for c in arrows[i]['cells']}
        blk = set().union(*[b for b, cnt in boxes if removed < cnt] or [set()]) | set().union(*[pipes[k]['cells'] for k in live] or [set()])
        us = {tuple(x for x in unit_of.get(i, (i,)) if x in alive) for i in alive}
        free = []
        for u in us:
            ok = True; ps = []
            for i in u:
                info = {}
                for c in B.ray(bd, arrows[i], info):
                    if (c in occ and occ[c] not in u) or c in blk:
                        ok = False; break
                if not ok:
                    break
                ps += [live[k] for k in info.get('pipes', [])]
            if ok:
                free.append((u, ps))
        if not free:
            return dict(rounds=None, stuck=sorted(alive))
        n += 1; widths.append(sum(len(u) for u, _ in free))
        for u, ps in free:
            alive -= set(u); removed += len(u)
            for k in ps:
                left[k] -= 1
    return dict(rounds=n, arrows_per_round=widths)
