#!/usr/bin/env python3
"""bcheck — batch-B (levels 11-20, V1 + V2) extraction audit on top of research/video-tools/vextract.py and research/bot/bot.py.

  bcheck.py rebuild V1|V2 N             # re-read the index start frame with a ROBUST grid refit -> levels/video/V?-L0NN.json
                                          (+ overlay video-frames/work/B/V?-L0NN-overlay.png); arrows/obstacles must equal the index
                                          agent's extraction (work/extract/V?-L0NN.json), counters are kept from it
  bcheck.py verify JSON [FRAME] [--save]  # ink IoU three ways + residual classes + per-arrow head/tail check (reversed heads)
  bcheck.py solve JSON...                 # solvability: bot.py plan() re-planned per tap + the replay's rule model (vextract.Model)
  bcheck.py diff A.json B.json            # cell-by-cell: arrows (cells + dir), obstacles (kind curtain==box, counter, cells), tapes
  bcheck.py final N [--from V1|V2]        # research/levels/L0NN.json (phone schema, source "video") from the chosen video's JSON

ROBUST FIT. vextract's grid fit is a weighted least-squares over stroke-segment centre lines. A few segments are not arrow strokes:
the dark outline of a V2 box (x 85 / y 362 on V2 L11: resid 3.56 px -> the grid drifted ~1 px across the board) and the base of
wide arrow heads. The refit drops segments off-grid by > 0.3 pitch, then > 3 px, then > 2 px, and re-solves (pitch, x0, y0).
It never changes a cell: every rebuilt board is compared arrow-by-arrow with the index agent's extraction.

VERIFY. (1) vextract.verify on the JSON's own transform; (2) the same render moved by a sub-pixel registration search (dx, dy in
+-1 px, pitch +-0.06 px: vextract draws on integer pixel centres while the stroke centres are measured as (start+stop-1)/2, a
~0.5 px bias); (3) plus a wider head-geometry search (tip 0.40-0.58 pitch, half-width 0.26-0.42). Cells/paths never vary, so (3)
measures the MODEL. Residual px are classed head (<= 0.7 pitch of a head tip) / tail (<= 0.35 pitch of a tail) / body; body
clusters >= 25 px are listed (a missing or extra segment is ~1 pitch x stroke = 100+ px). Per arrow: missed/extra px at its head
and tail; a reversed head shows as ~1 head triangle of EXTRA at the model head and MISSED at the model tail (negative control on
V1 L14 with arrows 3 and 10 reversed: both flagged, while the board IoU only fell 0.9845 -> 0.9711, i.e. still above 0.97).

SOLVE. Rules = the replay-verified video rules: a ray is blocked by a live arrow cell or an unbroken box/curtain cell; a Linked
(tape) bundle moves as one; every removed arrow (each bundle member) lowers every box/curtain counter by 1; at 0 the box is gone.
No pipes/elevators in L11-20. These obstacles are monotone (removing an arrow only frees rays, counters only fall), so a greedy
clear is complete: greedy stuck <=> unsolvable.
"""
import contextlib, copy, io, json, os, sys
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(os.path.dirname(HERE))            # apps/mazeout/research
APP = os.path.dirname(RES)
sys.path.insert(0, os.path.join(RES, 'video-tools'))
sys.path.insert(0, os.path.join(RES, 'bot'))
import vextract as vx
with contextlib.redirect_stdout(io.StringIO()):
    import bot

WB = os.path.join(vx.WORK, 'B')
os.makedirs(WB, exist_ok=True)


# ------------------------------------------------------------------------------------------------ robust grid refit
def _segments(ink, stroke):
    L = max(9, int(round(stroke * 2.2)))
    out = {'x': [], 'y': []}
    for name, st in (('x', np.ones((L, 1), bool)), ('y', np.ones((1, L), bool))):
        lb, _ = ndimage.label(ndimage.binary_opening(ink, structure=st))
        for sl in ndimage.find_objects(lb):
            h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
            if name == 'x' and w <= stroke * 1.6 and h >= L:
                out['x'].append(((sl[1].start + sl[1].stop - 1) / 2.0, h))
            elif name == 'y' and h <= stroke * 1.6 and w >= L:
                out['y'].append(((sl[0].start + sl[0].stop - 1) / 2.0, w))
    return out


def robust_fit(im, fit0):
    ink0 = vx.ink_mask(im); colour = vx.colour_mask(im, ink0)
    col_filled = ndimage.binary_fill_holes(ndimage.binary_closing(colour, iterations=2))
    lab, _ = ndimage.label(col_filled)
    big = np.zeros_like(col_filled)
    for i, sl in enumerate(ndimage.find_objects(lab)):
        if (lab[sl] == i + 1).sum() >= 150:
            big[sl] |= lab[sl] == i + 1
    ink = ink0 & ~ndimage.binary_dilation(big, iterations=3)       # same exclusion as vextract.read_board
    seg = _segments(ink, fit0['stroke'])
    P, X0, Y0 = fit0['pitch'], fit0['x0'], fit0['y0']
    xs = np.array([s[0] for s in seg['x']]); xw = np.array([s[1] for s in seg['x']], float)
    ys = np.array([s[0] for s in seg['y']]); yw = np.array([s[1] for s in seg['y']], float)
    for thr in (0.3 * P, 3.0, 2.0):
        kx = np.round((xs - X0) / P); ky = np.round((ys - Y0) / P)
        mx = np.abs(xs - (X0 + kx * P)) <= thr; my = np.abs(ys - (Y0 + ky * P)) <= thr
        A = np.zeros((mx.sum() + my.sum(), 3)); b = np.zeros(len(A)); W = np.concatenate([xw[mx], yw[my]])
        A[:mx.sum(), 0] = kx[mx]; A[:mx.sum(), 1] = 1; b[:mx.sum()] = xs[mx]
        A[mx.sum():, 0] = ky[my]; A[mx.sum():, 2] = 1; b[mx.sum():] = ys[my]
        sw = np.sqrt(W)
        sol, *_ = np.linalg.lstsq(A * sw[:, None], b * sw, rcond=None)
        P, X0, Y0 = sol
        rr = float(np.sqrt(np.average((b - A @ sol) ** 2, weights=W)))
    return dict(fit0, pitch=float(P), x0=float(X0), y0=float(Y0), resid_px=rr, used=int(mx.sum() + my.sum()),
                dropped=int((~mx).sum() + (~my).sum()))


def akeys(js):
    return {(tuple(map(tuple, a['cells'])), a['dir']) for a in js['arrows']}


def rebuild(V, n):
    L = vx.level_entry(V, n)
    orig = json.load(open(os.path.join(vx.WORK, 'extract', '%s-L%03d.json' % (V, n))))
    t = L['t_board']
    frame = os.path.join(vx.FR, V, 'L%03d-start.png' % n)
    im = vx.load(frame)
    b0 = vx.read_board(im, frame_path=frame)
    f = robust_fit(im, b0['fit'])
    b = vx.read_board(im, fit=f, frame_path=frame)
    ver, missed, extra = vx.verify(im, b)
    tsec = None
    if L.get('timer_start'):
        m_, s_ = L['timer_start'].split(':'); tsec = int(m_) * 60 + int(s_)
    js = vx.to_json(b, n, V, round(t, 3), frame, timer=tsec, hearts=L.get('hearts_start', 3), tag=L.get('tag'), verify_=ver)
    notes = []
    oc = [(o['kind'], o.get('counter'), sorted(map(tuple, o['cells']))) for o in orig['obstacles']]
    for o in js['obstacles']:
        match = [x for x in oc if x[0] == o['kind'] and x[2] == sorted(map(tuple, o['cells']))]
        if not match:
            notes.append('obstacle %s %s not in the index extraction' % (o['kind'], o['cells'][:2]))
        elif match[0][1] != o.get('counter'):
            notes.append('counter %s -> %s (index OCR kept)' % (o.get('counter'), match[0][1]))
            o['counter'] = match[0][1]
    ka, kb = akeys(orig), akeys(js)
    js['fit_px']['robust'] = dict(used=f['used'], dropped=f['dropped'], orig_pitch=round(b0['fit']['pitch'], 4),
                                  orig_resid_px=round(b0['fit']['resid_px'], 3))
    js['batchB'] = dict(reader='vextract read_board + robust grid refit (levels/video/bcheck.py)',
                        same_arrows_as_index_extract='%d/%d' % (len(ka & kb), len(ka)),
                        index_extract_iou_tol1=orig['verify']['ink_iou_tol1px'], notes=notes)
    out = os.path.join(HERE, '%s-L%03d.json' % (V, n))
    json.dump(js, open(out, 'w'), indent=1)
    vx.overlay(im, b, os.path.join(WB, '%s-L%03d-overlay.png' % (V, n)),
               note='%s L%d t=%.2f robust IoU %.3f (tol1 %.3f)' % (V, n, t, ver['ink_iou'], ver['ink_iou_tol1px']), missed=missed, extra=extra)
    print(json.dumps(dict(json=vx.relres(out), arrows=len(kb), same_as_index='%d/%d' % (len(ka & kb), len(ka)), grid=[js['cols'], js['rows']],
                          pitch_pt=js['pitch_pt'], resid_px=[round(b0['fit']['resid_px'], 2), round(f['resid_px'], 2)],
                          tol1=[orig['verify']['ink_iou_tol1px'], ver['ink_iou_tol1px']], notes=notes)))


# ------------------------------------------------------------------------------------------------ verify
def _board(js):
    fp = js['fit_px']; c0, r0 = fp['c0'], fp['r0']
    arrows = [dict(a, cells=[(c[0] + c0, c[1] + r0) for c in a['cells']]) for a in js['arrows'] if a.get('layer', 1) == 1]
    obst = [dict(o, cells=[(c[0] + c0, c[1] + r0) for c in o['cells']]) for o in js['obstacles'] if 'bbox_px' in o]
    return dict(fit=dict(pitch=fp['pitch'], x0=fp['x0'], y0=fp['y0'], stroke=fp['stroke'], resid_px=fp.get('resid_px', 0)),
                arrows=arrows, obstacles=obst)


def _score(ink_, rm):
    missed = ink_ & ~ndimage.binary_dilation(rm, iterations=1)
    extra = rm & ~ndimage.binary_dilation(ink_, iterations=1)
    return 1 - (missed.sum() + extra.sum()) / max(1, (rm | ink_).sum()), missed, extra


def verify(path, frame=None, save=False):
    js = json.load(open(path))
    frame = frame or os.path.join(APP, js['frame'])
    im = vx.load(frame)
    b = _board(js); fp = js['fit_px']
    ver0, _, _ = vx.verify(im, b)
    ink = vx.ink_mask(im)
    excl = np.zeros(ink.shape, bool)
    for o in b['obstacles']:
        if o['kind'] == 'elevator':
            continue
        x0, y0, x1, y1 = o['bbox_px']; excl[max(0, y0 - 3):y1 + 3, max(0, x0 - 3):x1 + 3] = True
    ink_ = ink & ~excl
    h = ver0['head']; sw0 = ver0['stroke_px']
    best = None
    for dp in (-0.06, -0.03, 0, 0.03, 0.06):
        for dx in (-1.0, -0.5, 0, 0.5, 1.0):
            for dy in (-1.0, -0.5, 0, 0.5, 1.0):
                bb = dict(b, fit=dict(b['fit'], pitch=fp['pitch'] + dp, x0=fp['x0'] + dx, y0=fp['y0'] + dy))
                s, _, _ = _score(ink_, vx.render(bb, ink.shape, head_tip=h['tip'], head_base=h['base'], head_half=h['half'], width=sw0) & ~excl)
                if best is None or s > best[0]:
                    best = (s, dp, dx, dy)
    s1, dp, dx, dy = best
    bb = dict(b, fit=dict(b['fit'], pitch=fp['pitch'] + dp, x0=fp['x0'] + dx, y0=fp['y0'] + dy))
    best2 = None
    for sw in (sw0 - 1, sw0, sw0 + 1):
        for tip in (0.40, 0.46, 0.52, 0.58):
            for half in (0.26, 0.30, 0.34, 0.38, 0.42):
                for base in (0.10, 0.16, 0.22):
                    s, missed, extra = _score(ink_, vx.render(bb, ink.shape, head_tip=tip, head_base=base, head_half=half, width=sw) & ~excl)
                    if best2 is None or s > best2[0]:
                        best2 = (s, sw, tip, half, base, missed, extra)
    s2, sw, tip, half, base, missed, extra = best2
    P = bb['fit']['pitch']; X0 = bb['fit']['x0']; Y0 = bb['fit']['y0']
    heads = np.array([(X0 + (a['cells'][-1][0] + 0.25 * vx.DIRS[a['dir']][0]) * P, Y0 + (a['cells'][-1][1] + 0.25 * vx.DIRS[a['dir']][1]) * P)
                      for a in bb['arrows']])
    tails = np.array([(X0 + a['cells'][0][0] * P, Y0 + a['cells'][0][1] * P) for a in bb['arrows']])
    cls = {}
    for name, m in (('missed', missed), ('extra', extra)):
        ys, xs = np.nonzero(m)
        if len(xs):
            dh = np.min(np.hypot(xs[:, None] - heads[None, :, 0], ys[:, None] - heads[None, :, 1]), 1)
            dt = np.min(np.hypot(xs[:, None] - tails[None, :, 0], ys[:, None] - tails[None, :, 1]), 1)
        else:
            dh = dt = np.array([])
        hd = dh <= 0.7 * P; tl = (~hd) & (dt <= 0.35 * P)
        bm = np.zeros(m.shape, bool)
        bm[ys[~hd & ~tl], xs[~hd & ~tl]] = True
        lab, nb = ndimage.label(ndimage.binary_dilation(bm, iterations=1))
        sizes = ndimage.sum(bm, lab, range(1, nb + 1)) if nb else []
        big = [(int(sz), [int(round(c)) for c in ndimage.center_of_mass(bm, lab, i + 1)[::-1]]) for i, sz in enumerate(sizes) if sz >= 25]
        cls[name] = dict(total=int(m.sum()), head=int(hd.sum()), tail=int(tl.sum()), body=int((~hd & ~tl).sum()), body_clusters_ge25px=big)
    ym, xm = np.nonzero(missed); ye, xe = np.nonzero(extra)
    per = []
    for a in bb['arrows']:
        d = vx.DIRS[a['dir']]
        hx, hy = X0 + (a['cells'][-1][0] + 0.25 * d[0]) * P, Y0 + (a['cells'][-1][1] + 0.25 * d[1]) * P
        tx, ty = X0 + a['cells'][0][0] * P, Y0 + a['cells'][0][1] * P
        per.append(dict(id=a['id'], head_missed=int((np.hypot(xm - hx, ym - hy) <= 0.7 * P).sum()),
                        head_extra=int((np.hypot(xe - hx, ye - hy) <= 0.7 * P).sum()),
                        tail_missed=int((np.hypot(xm - tx, ym - ty) <= 0.45 * P).sum()),
                        tail_extra=int((np.hypot(xe - tx, ye - ty) <= 0.45 * P).sum())))
    hs = sorted(p['head_missed'] + p['head_extra'] for p in per)
    med = hs[len(hs) // 2] if hs else 0
    tri = 0.5 * (2 * half * P) * ((tip + base) * P)
    flagged = [p for p in per if p['head_missed'] + p['head_extra'] > max(3 * med, 0.6 * tri) or p['tail_missed'] > 0.5 * tri]
    out = dict(json=path, frame=vx.relres(frame) if frame.startswith(RES) else frame, vextract_tol1=ver0['ink_iou_tol1px'],
               vextract_raw=ver0['ink_iou'], registered=dict(dpitch=dp, dx=dx, dy=dy, tol1=round(float(s1), 4)),
               best=dict(tol1=round(float(s2), 4), stroke=sw, tip=tip, half=half, base=base), head_triangle_px=round(tri),
               per_arrow_head_median_px=med, per_arrow_flagged=flagged, residual=cls)
    if save:
        vx.overlay(im, dict(bb, fit=dict(bb['fit'], stroke=sw), anomalies=[]),
                   os.path.join(WB, os.path.basename(os.path.splitext(path)[0]) + '-verifyB.png'),
                   note='verifyB tol1 %.4f' % s2, missed=missed, extra=extra)
    return out


# ------------------------------------------------------------------------------------------------ solve
def solve_bot(js):
    arrows = [dict(id=a['id'], cells=[tuple(c) for c in a['cells']], dir=a['dir']) for a in js['arrows'] if a.get('layer', 1) == 1]
    tapes = [o for o in js['obstacles'] if o['kind'] == 'tape_pink']
    boxes = [dict(cells=[tuple(c) for c in o['cells']], counter=o.get('counter')) for o in js['obstacles'] if o['kind'] in ('box', 'curtain')]
    pipes = [dict(cells=set(map(tuple, p['cells'])), ends={tuple(e['cell']): vx.DIRS[e['out']] for e in p['ends']}) for p in js.get('pipes', [])]
    order = []
    while arrows:
        board = dict(arrows=arrows, obstacles=tapes, bounds=(0, 0, js['cols'] - 1, js['rows'] - 1), pipes=pipes,
                     fit=dict(pitch=1.0, x0=0.0, y0=0.0, stroke=0.2),
                     door_cells=[c for b in boxes if b['counter'] is None or b['counter'] > 0 for c in b['cells']])
        with contextlib.redirect_stdout(io.StringIO()):
            taps = bot.plan(board, max_taps=1)
        if not taps:
            return False, order, sorted(a['id'] for a in arrows)
        ids = list(taps[0][0]['ids'])
        order.append(ids)
        arrows = [a for a in arrows if a['id'] not in ids]
        for b in boxes:
            if b['counter'] is not None:
                b['counter'] -= len(ids)
    return True, order, []


def _free_units(m):
    frees, seen = [], set()
    for i in sorted(m.alive):
        if i in seen:
            continue
        g = m.group(i); seen |= set(g)
        if m.free(i)[0]:
            frees.append(g)
    return frees


def solve_model(js):
    m = vx.Model(js); order = []; free0 = None
    while m.alive:
        fr = _free_units(m)
        if free0 is None:
            free0 = len(fr)
        if not fr:
            return False, order, sorted(m.alive), free0
        m.remove(fr[0]); m.activate_due(); order.append(fr[0])
    return True, order, [], free0


def depth(js):
    """waves: every currently free unit leaves at once (the fewest 'rounds' a perfect player needs)"""
    m = vx.Model(js); d = 0
    while m.alive:
        fr = _free_units(m)
        if not fr:
            return None
        for g in fr:
            if all(x in m.alive for x in g):
                m.remove(g)
        m.activate_due(); d += 1
    return d


def box_slack(js):
    """per box: its counter, the largest counter that still leaves the level solvable, and the level with boxes that never break"""
    out = []
    ids = [i for i, o in enumerate(js['obstacles']) if o['kind'] in ('box', 'curtain')]
    n = len([a for a in js['arrows'] if a.get('layer', 1) == 1])
    for i in ids:
        mx = None
        for c in range(0, n + 1):
            j = copy.deepcopy(js); j['obstacles'][i]['counter'] = c
            if solve_model(j)[0]:
                mx = c
        out.append(dict(counter=js['obstacles'][i].get('counter'), max_solvable_counter=mx))
    j = copy.deepcopy(js)
    for i in ids:
        j['obstacles'][i]['counter'] = 10 ** 6
    return out, (solve_model(j)[0] if ids else None)


def solve(path):
    js = json.load(open(path))
    ok_b, ob, left_b = solve_bot(js)
    ok_m, om, left_m, free0 = solve_model(js)
    slack, never = box_slack(js)
    return dict(json=os.path.basename(path), bot_plan=dict(solved=ok_b, taps=len(ob), stuck_with=left_b),
                model=dict(solved=ok_m, taps=len(om), stuck_with=left_m), free_at_start=free0, waves=depth(js),
                boxes=slack, solvable_if_boxes_never_break=never, order=om)


# ------------------------------------------------------------------------------------------------ diff
def diff(a_path, b_path):
    A = json.load(open(a_path)); B = json.load(open(b_path))
    ka, kb = akeys(A), akeys(B)
    norm = lambda k: k.replace('curtain', 'box')
    oa = sorted((norm(o['kind']), o.get('counter'), tuple(sorted(map(tuple, o['cells'])))) for o in A['obstacles'])
    ob = sorted((norm(o['kind']), o.get('counter'), tuple(sorted(map(tuple, o['cells'])))) for o in B['obstacles'])
    return dict(a=os.path.basename(a_path), b=os.path.basename(b_path), grid=[[A['cols'], A['rows']], [B['cols'], B['rows']]],
                arrows=[len(ka), len(kb)], identical_arrows=len(ka & kb),
                only_a=[dict(cells=list(map(list, k[0])), dir=k[1]) for k in ka - kb],
                only_b=[dict(cells=list(map(list, k[0])), dir=k[1]) for k in kb - ka],
                obstacles_identical=oa == ob, obstacles_a=[(o[0], o[1], len(o[2])) for o in oa], obstacles_b=[(o[0], o[1], len(o[2])) for o in ob],
                taped_identical=A['taped_arrow_ids'] == B['taped_arrow_ids'], pitch_pt=[A['pitch_pt'], B['pitch_pt']])


# ------------------------------------------------------------------------------------------------ final
def final(n, V='V2'):
    other = 'V1' if V == 'V2' else 'V2'
    src = os.path.join(HERE, '%s-L%03d.json' % (V, n)); alt = os.path.join(HERE, '%s-L%03d.json' % (other, n))
    js = json.load(open(src)); jo = json.load(open(alt))
    d = diff(src, alt)
    assert d['identical_arrows'] == len(js['arrows']) == len(jo['arrows']) and d['obstacles_identical'] and d['taped_identical'], d
    for o in js['obstacles']:
        if o['kind'] == 'curtain':
            o['video_kind'] = 'curtain'; o['kind'] = 'box'
    if js.get('tag') == 'Hard':
        js['tag'] = 'Hard Level'            # the phone schema's tag string (levels/L054.json); the videos' HUD tab reads "Hard Level"
    elif js.get('tag') == 'Super Hard':
        js['tag'] = 'Super Hard'
    js['level'] = n
    js['source'] = 'video'
    js['video_alt'] = dict(video=other, t=jo['t'], frame=jo['frame'], identical=True,
                           obstacle_skin='curtain (purple slab)' if other == 'V1' else 'box (cyan bomb block)')
    out = os.path.join(RES, 'levels', 'L%03d.json' % n)
    assert os.path.basename(out) not in ['L%03d.json' % k for k in range(32, 47)]
    json.dump(js, open(out, 'w'), indent=1)
    return out


def main():
    a = sys.argv[1:]
    cmd = a.pop(0) if a else ''
    if cmd == 'rebuild':
        rebuild(a[0], int(a[1]))
    elif cmd == 'verify':
        save = '--save' in a; a = [x for x in a if x != '--save']
        print(json.dumps(verify(a[0], a[1] if len(a) > 1 else None, save)))
    elif cmd == 'solve':
        for p in a:
            print(json.dumps(solve(p)))
    elif cmd == 'diff':
        print(json.dumps(diff(a[0], a[1])))
    elif cmd == 'final':
        V = a[a.index('--from') + 1] if '--from' in a else 'V2'
        print(final(int(a[0]), V))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
