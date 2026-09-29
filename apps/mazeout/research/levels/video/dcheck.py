#!/usr/bin/env python3
"""dcheck — batch-D (V2 L31-38) audit helpers on top of research/video-tools/vextract.py.

  dcheck.py resid  JSON [FRAME] [--layer 1|2|all] [--alive-at T --replay R.json]   # unexplained ink / phantom model ink, by cell
  dcheck.py solve  JSON                                                             # greedy (+DFS fallback) solver, full rules
  dcheck.py diff   VIDEO.json PHONE.json OUT.md                                     # cell-by-cell diff (markdown + ASCII boards)

Rules (the replay-verified video rules, = vextract.Model): a ray is blocked by any live arrow cell, an unbroken box/curtain cell or a
pipe tube cell (a ray entering a pipe mouth against its outward direction leaves by the other mouth); a Linked (tape) bundle moves
as one and each member counts; box/curtain counters fall by 1 per arrow removed anywhere; a pipe breaks after `counter` passes;
an elevator's hidden layer (layer 2) becomes live the moment its last platform arrow leaves.
"""
import json, os, sys, copy
import numpy as np
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(os.path.dirname(HERE))          # apps/mazeout/research
APP = os.path.dirname(RES)                              # apps/mazeout
sys.path.insert(0, os.path.join(RES, 'video-tools'))
import vextract as vx


def board_of(js, ids=None):
    fp = js['fit_px']
    fit = dict(pitch=fp['pitch'], x0=fp['x0'], y0=fp['y0'], stroke=fp['stroke'], resid_px=fp.get('resid_px', 0))
    arrows = [dict(id=a['id'], cells=[(c[0] + fp['c0'], c[1] + fp['r0']) for c in a['cells']], dir=a['dir'])
              for a in js['arrows'] if ids is None or a['id'] in ids]
    return dict(fit=fit, arrows=arrows, obstacles=[o for o in js['obstacles'] if 'bbox_px' in o])


def resid(js, frame, ids=None, region=None, min_px=18):
    im = vx.load(frame)
    b = board_of(js, ids)
    ver, missed, extra = vx.verify(im, b)
    fp = js['fit_px']; p = fp['pitch']
    out = dict(verify=ver, missed=[], extra=[])
    reg = None
    if region is not None:     # cells (json coords) -> px mask, grown by half a cell
        reg = np.zeros(missed.shape, bool)
        for c in region:
            x = fp['x0'] + (c[0] + fp['c0']) * p; y = fp['y0'] + (c[1] + fp['r0']) * p
            reg[int(y - 0.75 * p):int(y + 0.75 * p), int(x - 0.75 * p):int(x + 0.75 * p)] = True
    for name, m in (('missed', missed), ('extra', extra)):
        if reg is not None:
            m = m & reg
        lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=1))
        for k in range(1, n + 1):
            ys, xs = np.nonzero((lab == k) & m)
            if len(ys) < min_px:
                continue
            cx, cy = xs.mean(), ys.mean()
            thick = len(ys) / max(1, max(xs.max() - xs.min(), ys.max() - ys.min()) + 1)
            out[name].append(dict(px=int(len(ys)), thick=round(float(thick), 2), at_px=[int(cx), int(cy)],
                                  cell=[round((cx - fp['x0']) / p - fp['c0'], 2), round((cy - fp['y0']) / p - fp['r0'], 2)],
                                  bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]))
    return out


# ------------------------------------------------------------------------------------------------ solver
def units_free(m):
    """free units now: list of tuples of arrow ids (a Linked bundle is one unit)"""
    seen, res = set(), []
    for i in sorted(m.alive):
        if i in seen:
            continue
        g = tuple(sorted(m.group(i)))
        seen |= set(g)
        ok, _ = m.free(i)
        if ok:
            res.append(g)
    return res


def platform_last(m, g):
    """True if removing unit g empties an elevator platform whose hidden layer is not yet live"""
    for e in m.elevators:
        if e['active'] or not e.get('hidden_arrow_ids'):
            continue
        left = [i for i in e.get('arrow_ids', []) if i in m.alive]
        if left and set(left) <= set(g):
            return True
    return False


def step(m, g):
    m.remove(list(g))
    m.activate_due()


def solve(js, limit=200000):
    m0 = vx.Model(js)
    m0.activate_due()
    nodes = [0]
    best = [None]

    def dfs(m, seq):
        nodes[0] += 1
        if nodes[0] > limit:
            return None
        if not m.alive and all(e['active'] or not e.get('hidden_arrow_ids') for e in m.elevators):
            return seq
        fr = units_free(m)
        if not fr:
            return None
        # greedy order: never empty a platform while anything else is free; else anything
        fr.sort(key=lambda g: (platform_last(m, g), g))
        for g in fr:
            m2 = copy.deepcopy(m)
            step(m2, g)
            r = dfs(m2, seq + [list(g)])
            if r is not None:
                return r
            if nodes[0] > limit:
                return None
        return None

    # pure greedy first (no backtracking), then DFS
    m = copy.deepcopy(m0); seq = []
    while True:
        if not m.alive and all(e['active'] or not e.get('hidden_arrow_ids') for e in m.elevators):
            return dict(solved=True, method='greedy', taps=len(seq), seq=seq, nodes=len(seq))
        fr = units_free(m)
        if not fr:
            break
        fr.sort(key=lambda g: (platform_last(m, g), g))
        step(m, fr[0]); seq.append(list(fr[0]))
    stuck = dict(alive=sorted(m.alive), after=len(seq))
    r = dfs(copy.deepcopy(m0), [])
    if r is not None:
        return dict(solved=True, method='dfs', taps=len(r), seq=r, nodes=nodes[0], greedy_stuck=stuck)
    return dict(solved=False, greedy_stuck=stuck, nodes=nodes[0])


def dead_ends(js, trials=300, seed=1):
    """random-order play (always a free unit, uniformly): how often does the level dead-end? (0 = no order can fail)"""
    import random
    rnd = random.Random(seed)
    fails = 0
    for _ in range(trials):
        m = vx.Model(js); m.activate_due()
        while True:
            if not m.alive:
                break
            fr = units_free(m)
            if not fr:
                fails += 1
                break
            step(m, rnd.choice(fr))
    return fails


# ------------------------------------------------------------------------------------------------ diff
CH = {'up': '^', 'down': 'v', 'left': '<', 'right': '>'}


def ascii_board(js, shift=(0, 0), W=None, H=None, layer=1):
    W = W or js['cols']; H = H or js['rows']
    g = [['.' for _ in range(W)] for _ in range(H)]
    for o in js.get('obstacles', []):
        ch = {'box': '#', 'curtain': '#', 'door': 'D', 'elevator': ':', 'tape_pink': 'x', 'pipe': 'P'}.get(o['kind'])
        if not ch or o['kind'] in ('tape_pink',):
            continue
        for c in o['cells']:
            x, y = c[0] + shift[0], c[1] + shift[1]
            if 0 <= x < W and 0 <= y < H:
                g[y][x] = ch
    for pp in js.get('pipes', []):
        for c in pp['cells']:
            x, y = c[0] + shift[0], c[1] + shift[1]
            if 0 <= x < W and 0 <= y < H:
                g[y][x] = 'P'
    for a in js['arrows']:
        if a.get('layer', 1) != layer:
            continue
        cs = a['cells']
        for i, c in enumerate(cs):
            x, y = c[0] + shift[0], c[1] + shift[1]
            if not (0 <= x < W and 0 <= y < H):
                continue
            if i == len(cs) - 1:
                g[y][x] = CH[a['dir']]
            else:
                n = cs[i + 1]
                g[y][x] = '-' if n[1] == c[1] else '|'
    return [''.join(r) for r in g]


def keyset(js, dx=0, dy=0, layer=None):
    return {(tuple((c[0] + dx, c[1] + dy) for c in a['cells']), a['dir'])
            for a in js['arrows'] if layer is None or a.get('layer', 1) == layer}


def best_shift(A, B, R=12):
    """B shifted by (dx,dy) onto A: maximise identical arrows, then common occupied cells"""
    ca = {c for k in keyset(A, layer=1) for c in k[0]}
    ka = keyset(A, layer=1)
    best = None
    for dx in range(-R, R + 1):
        for dy in range(-R, R + 1):
            kb = keyset(B, dx, dy)
            cb = {c for k in kb for c in k[0]}
            s = (len(ka & kb), len(ca & cb))
            if best is None or s > best[0]:
                best = (s, (dx, dy))
    return best


def diff(a_path, b_path, out_md):
    A = json.load(open(a_path)); B = json.load(open(b_path))
    (ident, common), (dx, dy) = best_shift(A, B)
    ka = keyset(A, layer=1); kb = keyset(B, dx, dy)
    ca = {c for k in ka for c in k[0]}; cb = {c for k in kb for c in k[0]}
    # partial matches: same cell set, different dir; same head cell+dir; any overlap
    same_cells_diff_dir = [(x, y) for x in ka for y in kb if set(x[0]) == set(y[0]) and x != y]
    same_head = [(x, y) for x in ka for y in kb if x[0][-1] == y[0][-1] and x[1] == y[1] and x != y]
    lines = []
    L = A['level']
    lines.append('# L%03d: video (V2) vs phone (v552) — cell-by-cell diff' % L)
    lines.append('')
    lines.append('Generated by `research/levels/video/dcheck.py diff` from `%s` (A, video) and `%s` (B, phone).' % (
        os.path.relpath(a_path, APP), os.path.relpath(b_path, APP)))
    lines.append('Best integer shift of B onto A (maximises identical arrows, then shared occupied cells): dx=%d, dy=%d.' % (dx, dy))
    lines.append('')
    ob = lambda js: ', '.join(sorted({('%s(%s)' % (o['kind'], o.get('counter')) if o.get('counter') is not None else o['kind'])
                                     for o in js['obstacles']})) or 'none'
    hid = sum(1 for a in A['arrows'] if a.get('layer', 1) == 2)
    rows = [('grid (cols x rows)', '%dx%d' % (A['cols'], A['rows']), '%dx%d' % (B['cols'], B['rows'])),
            ('pitch pt', A.get('pitch_pt'), B.get('pitch_pt')),
            ('arrows (visible at start)', len(A['arrows']) - hid, len(B['arrows'])),
            ('hidden-layer arrows (elevator)', hid, '-'),
            ('occupied cells (visible layer)', len(ca), len(cb)),
            ('obstacles', ob(A), ob(B)),
            ('Linked (taped) arrows', len(A.get('taped_arrow_ids', [])), len(B.get('taped_arrow_ids', []))),
            ('pipes', len(A.get('pipes', [])), len(B.get('pipes', []))),
            ('timer s', A.get('timer_s'), B.get('timer_s')),
            ('tag', A.get('tag'), B.get('tag')),
            ('identical arrows (same cells + dir)', ident, ident),
            ('occupied cells in common', common, common),
            ('cells only in A / only in B', len(ca - cb), len(cb - ca)),
            ('same cells, other direction', len(same_cells_diff_dir), len(same_cells_diff_dir)),
            ('same head cell + dir, other body', len(same_head), len(same_head))]
    lines.append('| | A = video V2 | B = phone v552 |')
    lines.append('|---|---|---|')
    for r in rows:
        lines.append('| %s | %s | %s |' % r)
    lines.append('')
    tot = max(len(ka), len(kb))
    verdict = 'SAME LEVEL' if ident == len(ka) == len(kb) else ('DIFFERENT LEVELS' if ident <= 0.2 * tot else 'PARTIAL MATCH')
    lines.append('**Verdict: %s** — %d of %d/%d arrows identical at the best shift; %d of %d/%d occupied cells shared.' % (
        verdict, ident, len(ka), len(kb), common, len(ca), len(cb)))
    lines.append('')
    if ident:
        lines.append('Identical arrows (A coordinates): ' + '; '.join('%s %s' % (list(map(list, k[0])), k[1]) for k in sorted(ka & kb)))
        lines.append('')
    # cell-by-cell map on the union frame
    xs = [c[0] for c in ca | cb] + [0, A['cols'] - 1]; ys = [c[1] for c in ca | cb] + [0, A['rows'] - 1]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    W, H = x1 - x0 + 1, y1 - y0 + 1
    ga = ascii_board(A, (-x0, -y0), W, H)
    gb = ascii_board(B, (dx - x0, dy - y0), W, H)
    gd = []
    for y in range(H):
        row = ''
        for x in range(W):
            a_, b_ = ga[y][x], gb[y][x]
            occA = a_ not in '.'; occB = b_ not in '.'
            c = (x + x0, y + y0)
            if (c in ca) and (c in cb):
                row += '=' if a_ == b_ else '~'
            elif c in ca:
                row += 'A'
            elif c in cb:
                row += 'B'
            elif occA or occB:
                row += 'o'
            else:
                row += '.'
        gd.append(row)
    lines.append('Cell map legend: A/B boards: `^ v < >` head, `-` `|` body (towards the next cell), `#` box/curtain, `:` elevator platform,')
    lines.append('`D` door, `P` pipe, `.` empty. Diff: `=` same arrow glyph in both, `~` both occupied but different glyph, `A` only in the')
    lines.append('video board, `B` only in the phone board, `o` obstacle-only cell, `.` empty in both. Column/row 0 = A\'s (0,0) shifted by (%d,%d).' % (x0, y0))
    lines.append('')
    lines.append('```')
    lines.append('%-*s   %-*s   %s' % (W, 'A video', W, 'B phone', 'diff'))
    for y in range(H):
        lines.append('%s   %s   %s' % (ga[y], gb[y], gd[y]))
    lines.append('```')
    if hid:
        lines.append('')
        lines.append('Hidden layer of the video board (elevator layer 2, revealed when the platform empties):')
        lines.append('```')
        for r in ascii_board(A, (-x0, -y0), W, H, layer=2):
            lines.append(r)
        lines.append('```')
    open(out_md, 'w').write('\n'.join(lines) + '\n')
    return dict(shift=[dx, dy], identical=ident, arrows=[len(ka), len(kb)], cells=[len(ca), len(cb)], common=common, verdict=verdict)


# ------------------------------------------------------------------------------------------------ head audit
def head_audit(js, frame, ids=None):
    """per arrow: ink width across the path just behind the head tip vs at the tail end (a reversed or mis-headed arrow shows a
    wide triangle at its TAIL or only a thin stroke at its head). Returns suspicious arrows."""
    im = vx.load(frame)
    ink = vx.ink_mask(im)
    fp = js['fit_px']; p = fp['pitch']; sw = fp['stroke']
    P = lambda c: (fp['x0'] + (c[0] + fp['c0']) * p, fp['y0'] + (c[1] + fp['r0']) * p)

    def width(x, y, d):
        # max run of ink along the perpendicular of d through (x,y), within +-0.45 p
        px_, py_ = -d[1], d[0]
        best = run = 0
        for s in np.arange(-0.45 * p, 0.45 * p + 0.01, 0.5):
            xi, yi = int(round(x + px_ * s)), int(round(y + py_ * s))
            if 0 <= yi < ink.shape[0] and 0 <= xi < ink.shape[1] and ink[yi, xi]:
                run += 0.5; best = max(best, run)
            else:
                run = 0
        return best

    out = []
    for a in js['arrows']:
        if ids is not None and a['id'] not in ids:
            continue
        cs = a['cells']; d = vx.DIRS[a['dir']]
        hx, hy = P(cs[-1])
        wh = max(width(hx + d[0] * f * p, hy + d[1] * f * p, d) for f in (0.0, 0.08, 0.16))
        # tail: the direction from the second cell to the first (outward); single-cell arrows: opposite of dir
        if len(cs) > 1:
            t0, t1 = cs[0], cs[1]; td = (t0[0] - t1[0], t0[1] - t1[1])
        else:
            td = (-d[0], -d[1])
        tx, ty = P(cs[0])
        wt = max(width(tx + td[0] * f * p, ty + td[1] * f * p, td) for f in (0.0, 0.08, 0.16))
        # beyond the tail: ink continuing past the tail end = the arrow is longer than modelled
        bx, by = tx + td[0] * 0.5 * p, ty + td[1] * 0.5 * p
        beyond = ink[int(by) - 1:int(by) + 2, int(bx) - 1:int(bx) + 2].mean()
        flag = []
        if wh < 1.5 * sw:
            flag.append('thin-head')
        if wt >= 1.5 * sw and wt > 0.8 * wh:
            flag.append('wide-tail')
        if flag:
            out.append(dict(id=a['id'], head=list(cs[-1]), dir=a['dir'], tail=list(cs[0]), w_head=wh, w_tail=wt, beyond_tail=round(float(beyond), 2), flags=flag))
    return out


# ------------------------------------------------------------------------------------------------ track (whole-level ink audit)
def persistent(out, kind, js=None, min_dt=1.0, rad=1.0):
    """components of one kind seen at (about) the same cell in samples >= min_dt apart with no gap sample in between that lacks
    them: exiting arrows (rainbow, moving) and not-yet-logged exits never persist this long; an unmodelled arrow does"""
    tracks = []
    for i, x in enumerate(out):
        for (px, th, c) in x[kind]:
            hit = None
            for tr in tracks:
                if tr['last_i'] == i - 1 and abs(tr['cell'][0] - c[0]) <= rad and abs(tr['cell'][1] - c[1]) <= rad:
                    hit = tr; break
            if hit:
                hit.update(last_i=i, t1=x['t'], n=hit['n'] + 1, px=max(hit['px'], px))
            else:
                tracks.append(dict(cell=[round(float(c[0]), 1), round(float(c[1]), 1)], first_i=i, last_i=i, t0=x['t'], t1=x['t'], n=1, px=px))
    res = [dict(cell=tr['cell'], t0=tr['t0'], t1=tr['t1'], samples=tr['n'], max_px=tr['px']) for tr in tracks if tr['t1'] - tr['t0'] >= min_dt]
    return res



def track(V, n, js_path, rep_path, tmpdir, every=1, min_px=25, min_thick=2.5):
    """Replays the replay log's state (arrows alive, hidden layers, board moves) and, on the frame just before every tap, looks
    for THICK frame ink the model does not explain (an arrow hidden under a pipe/box/elevator that appears later, a mis-read
    hidden layer, a wrong fit after a pan) and model ink the frame lacks (an arrow the model keeps that is gone; V2 draws a
    bumped arrow black, which also shows here). Frames: vgrab JPEG q0.9 in tmpdir (deleted afterwards)."""
    js = json.load(open(js_path)); rep = json.load(open(rep_path))
    L = vx.level_entry(V, n)
    fp0 = dict(js['fit_px'])
    alive = {a['id'] for a in js['arrows'] if a.get('layer', 1) == 1}
    ev = sorted(rep['log'], key=lambda e: e['t'])
    taps = [e for e in ev if e.get('event') in ('tap', 'miss', 'late')]
    samples = [e['t'] - 0.15 for e in taps][::every] + [L['t_clear'] - 0.05]
    els = js.get('elevators', [])
    blackout = [(e['t_active'] - 1.0, e.get('reveal_frame_t', e['t_active']) + 0.25) for e in els if e.get('t_active')]
    samples = [t for t in samples if not any(a <= t <= b for a, b in blackout)]
    paths = vx.grab(V, samples, tmpdir)
    res = []
    i_ev = 0
    fit = dict(fp0)
    drawn = set()
    for t, pth in zip(samples, paths):
        while i_ev < len(ev) and ev[i_ev]['t'] <= t:
            e = ev[i_ev]; i_ev += 1
            k = e.get('event')
            if k == 'tap' and e.get('video') == 'exit':
                alive -= set(e.get('group', [e['arrow']]))
            elif k in ('gone_without_tap', 'gone_at_elevator_drop'):
                alive.discard(e['arrow'])
            elif k == 'elevator_active':
                alive |= set(e['hidden_arrows'])
            elif k == 'board_moved':
                fit.update(pitch=e['new']['pitch'], x0=e['new']['x0'], y0=e['new']['y0'])
        # exited-by-then arrows whose tap is AFTER t are alive; arrows tapped just before t may still be sliding (cyan, not ink)
        jj = dict(js, fit_px=dict(fit))
        r = resid(jj, pth, ids=set(alive), min_px=min_px)
        # pipes/boxes that already broke still carry bbox exclusions in verify(): harmless (only hides ink)
        thick_m = [x for x in r['missed'] if x['thick'] >= min_thick]
        thick_e = [x for x in r['extra'] if x['thick'] >= min_thick]
        res.append(dict(t=round(t, 3), alive=len(alive), tol1=r['verify']['ink_iou_tol1px'],
                        missed=[(x['px'], x['thick'], x['cell']) for x in thick_m], extra=[(x['px'], x['thick'], x['cell']) for x in thick_e]))
    vx.cleanup(tmpdir)
    return res



# ================================================================================================ batch D pipeline (2nd run)
# rebuild (robust refit, hidden layers carried from the index extraction and re-checked) -> verify (layer 1 at the start frame,
# layer 2 at each elevator's reveal frame with every arrow alive at that moment) -> replay (vextract) -> solve (bot.plan greedy with
# the elevator/pipe/box rules + the Model DFS) -> diff vs the phone -> final (L031 only).
import contextlib, io
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(RES, 'bot'))
import bcheck
with contextlib.redirect_stdout(io.StringIO()):
    import bot
WD = os.path.join(vx.WORK, 'D')
os.makedirs(WD, exist_ok=True)
bcheck.WB = WD                       # bcheck.verify(save=True) writes its overlay here


def vid_path(n):
    return os.path.join(HERE, 'V2-L%03d.json' % n)


def akeys(js, layer=None):
    return {(tuple(map(tuple, a['cells'])), a['dir']) for a in js['arrows'] if layer is None or a.get('layer', 1) == layer}


def rebuild(n, V='V2', t=None, frame=None):
    """start frame -> robust grid refit -> read -> JSON; compared arrow by arrow with the index extraction; counters and the
    elevator hidden layers (read on the start grid) are carried from it when the cell frame (c0, r0) is unchanged"""
    L = vx.level_entry(V, n)
    orig = json.load(open(os.path.join(vx.WORK, 'extract', '%s-L%03d.json' % (V, n))))
    if frame is None:
        frame = os.path.join(vx.FR, V, 'L%03d-start.png' % n)
        t = L['t_board'] if t is None else t
    im = vx.load(frame)
    b0 = vx.read_board(im, frame_path=frame)
    f = bcheck.robust_fit(im, b0['fit'])
    b = vx.read_board(im, fit=f, frame_path=frame)
    ver, missed, extra = vx.verify(im, b)
    tsec = None
    if L.get('timer_start'):
        m_, s_ = L['timer_start'].split(':'); tsec = int(m_) * 60 + int(s_)
    js = vx.to_json(b, n, V, round(t, 3), frame, timer=tsec, hearts=L.get('hearts_start', 3), tag=L.get('tag'), verify_=ver)
    notes = []
    same_frame = (js['fit_px']['c0'], js['fit_px']['r0']) == (orig['fit_px']['c0'], orig['fit_px']['r0'])
    if not same_frame:
        notes.append('cell frame moved: c0,r0 %s -> %s' % ((orig['fit_px']['c0'], orig['fit_px']['r0']), (js['fit_px']['c0'], js['fit_px']['r0'])))
    oc = [(o['kind'], o.get('counter'), sorted(map(tuple, o['cells']))) for o in orig['obstacles']]
    for o in js['obstacles']:
        match = [x for x in oc if x[0] == o['kind'] and x[2] == sorted(map(tuple, o['cells']))]
        if not match:
            notes.append('obstacle %s %s not in the index extraction' % (o['kind'], o['cells'][:2]))
        elif match[0][1] != o.get('counter'):
            notes.append('counter %s -> %s (index OCR kept)' % (o.get('counter'), match[0][1]))
            o['counter'] = match[0][1]
    for pp, po in zip(js['pipes'], orig['pipes']):
        if pp.get('counter') != po.get('counter'):
            notes.append('pipe counter %s -> %s (index OCR kept)' % (pp.get('counter'), po.get('counter')))
            pp['counter'] = po.get('counter')
    ka1, kb1 = akeys(orig, 1), akeys(js)
    ids_same = [a['id'] for a in js['arrows']] == [a['id'] for a in orig['arrows'] if a.get('layer', 1) == 1] and \
        all((tuple(map(tuple, a['cells'])), a['dir']) == (tuple(map(tuple, o['cells'])), o['dir'])
            for a, o in zip(js['arrows'], [o for o in orig['arrows'] if o.get('layer', 1) == 1]))
    if orig.get('elevators'):
        if not (same_frame and ids_same):
            raise SystemExit('elevator level: layer 1 differs from the index extraction; re-run vextract.reveal instead')
        for a in orig['arrows']:
            if a.get('layer', 1) == 2:
                js['arrows'].append(dict(a))
        for e, eo in zip(js['elevators'], orig['elevators']):
            assert sorted(map(tuple, e['cells'])) == sorted(map(tuple, eo['cells'])) and e['arrow_ids'] == eo['arrow_ids'], (e, eo)
            for k in ('t_active', 'reveal_frame_t', 'hidden_arrow_ids', 'reveal_frame', 'note'):
                if k in eo:
                    e[k] = eo[k]
        js['reveal'] = orig.get('reveal')
    js['fit_px']['robust'] = dict(used=f['used'], dropped=f['dropped'], orig_pitch=round(b0['fit']['pitch'], 4),
                                  orig_resid_px=round(b0['fit']['resid_px'], 3))
    js['batchD'] = dict(reader='vextract read_board + robust grid refit (bcheck.robust_fit); hidden layers from vextract.reveal (index run)',
                        same_arrows_as_index_extract='%d/%d' % (len(ka1 & kb1), len(ka1)), ids_same=ids_same,
                        index_extract_iou_tol1=orig['verify']['ink_iou_tol1px'], notes=notes)
    out = vid_path(n)
    json.dump(js, open(out, 'w'), indent=1)
    vx.overlay(im, b, os.path.join(WD, '%s-L%03d-overlay.png' % (V, n)),
               note='%s L%d t=%.2f robust IoU %.3f (tol1 %.3f)' % (V, n, t, ver['ink_iou'], ver['ink_iou_tol1px']), missed=missed, extra=extra)
    return dict(json=vx.relres(out), arrows=len(kb1), hidden=sum(1 for a in js['arrows'] if a.get('layer', 1) == 2),
                same_as_index='%d/%d' % (len(ka1 & kb1), len(ka1)), ids_same=ids_same, grid=[js['cols'], js['rows']],
                pitch_pt=js['pitch_pt'], resid_px=[round(b0['fit']['resid_px'], 2), round(f['resid_px'], 2)],
                tol1=[orig['verify']['ink_iou_tol1px'], ver['ink_iou_tol1px']], notes=notes)


def removed_before(rep, t):
    """arrow ids the replay log has removed before time t (tap exits, untapped exits, platform drops)"""
    gone = set()
    for e in rep['log']:
        if e['t'] >= t:
            continue
        k = e.get('event')
        if k == 'tap' and e.get('video') == 'exit':
            gone |= set(e.get('group', [e['arrow']]))
        elif k in ('gone_without_tap', 'gone_at_elevator_drop'):
            gone.add(e['arrow'])
    return gone


def verify_layer2(n, rep_path):
    """each elevator's hidden layer at its reveal frame: the board of every arrow alive then (layer 1 not yet removed + the hidden
    layers of elevators already active) -> bcheck.verify (IoU 3 ways + per-arrow head/tail flags); flags reported for all arrows"""
    js = json.load(open(vid_path(n))); rep = json.load(open(rep_path))
    out = []
    for k, e in enumerate(js.get('elevators', [])):
        if not e.get('reveal_frame'):
            continue
        t = e['reveal_frame_t']
        gone = removed_before(rep, t)
        act = [j for j, ee in enumerate(js['elevators']) if ee.get('t_active') is not None and ee['t_active'] <= t]
        hid_live = {i for j in act for i in js['elevators'][j].get('hidden_arrow_ids', [])}
        plat_gone = {i for j in act for i in js['elevators'][j].get('arrow_ids', [])}   # an active elevator's platform is empty
        alive = [a for a in js['arrows'] if (a.get('layer', 1) == 1 or a['id'] in hid_live) and a['id'] not in gone | plat_gone]
        tj = dict(js, arrows=[dict(a, layer=1) for a in alive],
                  obstacles=[o for o in js['obstacles'] if o['kind'] in ('pipe', 'box', 'curtain', 'tape_pink')])
        tp = os.path.join(WD, 'V2-L%03d-layer2-e%d.json' % (n, k))
        json.dump(tj, open(tp, 'w'))
        r = bcheck.verify(tp, os.path.join(APP, e['reveal_frame']), save=True)
        hid = set(e.get('hidden_arrow_ids', []))
        r['elevator'] = k; r['t'] = t; r['alive'] = len(alive); r['hidden'] = len(hid)
        r['hidden_flagged'] = [p for p in r['per_arrow_flagged'] if p['id'] in hid]
        out.append(r)
    return out


# ----------------------------------------------------------------------------------- bot.plan greedy with the video rules
def solve_bot_full(js, platform_last=True):
    """research/bot's greedy plan() re-planned after every tap, with the replay-verified rules added around it: unbroken boxes =
    door cells; every removed arrow lowers every box counter; a pipe (live) teleports rays mouth to mouth and breaks after
    `counter` passes (then its cells are free); an elevator's hidden layer joins the board the moment its last platform arrow
    leaves. Elevator heuristic (platform_last): if plan() picks the LAST arrow of a platform whose layer is still hidden, re-plan
    with that platform's arrows frozen (they still block) and take any other unit first."""
    A = {a['id']: dict(id=a['id'], cells=[tuple(c) for c in a['cells']], dir=a['dir']) for a in js['arrows']}
    alive = {a['id'] for a in js['arrows'] if a.get('layer', 1) == 1}
    tapes = [o for o in js['obstacles'] if o['kind'] == 'tape_pink']
    boxes = [dict(cells=[tuple(c) for c in o['cells']], counter=o.get('counter')) for o in js['obstacles'] if o['kind'] in ('box', 'curtain')]
    pipes = [dict(cells=set(map(tuple, p['cells'])), ends={tuple(e['cell']): vx.DIRS[e['out']] for e in p['ends']},
                  counter=p.get('counter'), passes=0) for p in js.get('pipes', [])]
    els = [dict(arrow_ids=set(e.get('arrow_ids', [])), hidden=set(e.get('hidden_arrow_ids', [])), active=False) for e in js.get('elevators', [])]
    cs = [c for a in A.values() for c in a['cells']] + [tuple(c) for o in js['obstacles'] for c in o['cells']]
    bounds = (min(c[0] for c in cs), min(c[1] for c in cs), max(c[0] for c in cs), max(c[1] for c in cs))
    order, deferrals = [], 0

    def board(frozen=()):
        live_pipes = [p for p in pipes if p['counter'] is None or p['counter'] > 0]
        doors = [c for b in boxes if b['counter'] is None or b['counter'] > 0 for c in b['cells']]
        doors += [c for i in frozen for c in A[i]['cells']]
        return dict(arrows=[A[i] for i in sorted(alive) if i not in frozen], obstacles=tapes, bounds=bounds, pipes=live_pipes,
                    fit=dict(pitch=1.0, x0=0.0, y0=0.0, stroke=0.2), door_cells=doors)

    def plan1(frozen=()):
        with contextlib.redirect_stdout(io.StringIO()):
            t = bot.plan(board(frozen), max_taps=1)
        return list(t[0][0]['ids']) if t else None

    while True:
        for e in els:
            if not e['active'] and e['hidden'] and not (e['arrow_ids'] & alive):
                e['active'] = True; alive |= e['hidden']
        if not alive:
            return True, order, [], deferrals
        ids = plan1()
        if ids is None:
            return False, order, sorted(alive), deferrals
        if platform_last:
            for e in els:
                left = e['arrow_ids'] & alive
                if not e['active'] and e['hidden'] and left and left <= set(ids):
                    alt = plan1(frozen=tuple(sorted(left)))
                    if alt is not None:
                        ids = alt; deferrals += 1
                    break
        # pipe passes of this unit (on the board as it is now), then remove
        b = board()
        for i in ids:
            info = {}
            bot.ray(b, A[i], info)
            for k in info.get('pipes', []):
                p = b['pipes'][k]
                p['passes'] += 1
                if p['counter'] is not None:
                    p['counter'] -= 1
        alive -= set(ids)
        order.append(ids)
        for bx in boxes:
            if bx['counter'] is not None:
                bx['counter'] -= len(ids)


def solve_all(n):
    js = json.load(open(vid_path(n)))
    ok_b, ob, left_b, defer = solve_bot_full(js)
    ok_b0, ob0, left_b0, _ = solve_bot_full(js, platform_last=False)
    r = solve(js)
    de = dead_ends(js)
    m = vx.Model(js); m.activate_due()
    free0 = len(units_free(m))
    res = dict(level=n, bot_plan=dict(solved=ok_b, taps=len(ob), stuck_with=left_b, platform_deferrals=defer),
               bot_plan_no_elevator_heuristic=dict(solved=ok_b0, taps=len(ob0), stuck_with=left_b0),
               model=dict(solved=r['solved'], method=r.get('method'), taps=r.get('taps'), greedy_stuck=r.get('greedy_stuck')),
               free_at_start=free0, random_order_dead_ends_of_300=de)
    if any(o['kind'] in ('box', 'curtain') for o in js['obstacles']):
        sl = []
        for i, o in enumerate(js['obstacles']):
            if o['kind'] not in ('box', 'curtain'):
                continue
            # solvability is monotone in a box counter (a lower counter only frees rays sooner): binary search the largest
            def ok(c):
                j = copy.deepcopy(js); j['obstacles'][i]['counter'] = c
                return solve(j, limit=5000)['solved']
            lo, hi = 0, len(js['arrows'])
            if not ok(lo):
                mx = None
            else:
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if ok(mid):
                        lo = mid
                    else:
                        hi = mid - 1
                mx = lo
            sl.append(dict(counter=o.get('counter'), max_solvable_counter=mx))
        j = copy.deepcopy(js)
        for o in j['obstacles']:
            if o['kind'] in ('box', 'curtain'):
                o['counter'] = 10 ** 6
        res['boxes'] = sl
        res['solvable_if_boxes_never_break'] = solve(j, limit=5000)['solved']
    if js.get('pipes'):
        j = copy.deepcopy(js)
        for p in j['pipes']:
            p['counter'] = None
        res['solvable_if_pipes_never_break'] = solve(j, limit=5000)['solved']
    res['order'] = ob
    return res


def run_replay(n):
    rp = os.path.join(WD, 'V2-L%03d-replay.json' % n)
    r = vx.replay('V2', n, js_path=vid_path(n), report=rp)
    return rp, r['stats']


def events(n):
    """walk the replay log through the Model: every removal in video order -> pipe passes (arrow, time, counter after), box
    counter-zero moments, elevator activations, and exits whose ray crossed the cells of a platform that was not yet active
    (does an empty / part-empty platform block rays? the model says no)"""
    js = json.load(open(vid_path(n)))
    rep = json.load(open(os.path.join(WD, 'V2-L%03d-replay.json' % n)))
    m = vx.Model(js)
    plat = [set(map(tuple, e['cells'])) for e in js.get('elevators', [])]
    out = dict(pipe_passes=[], pipe_breaks=[], box_zero=[], elevator=[], platform_crossings=[], exits=0)
    def removal(ids, t, how):
        for i in ids:
            if i not in m.alive:
                continue
            info = {}
            cells = m.ray(i, info)
            for k, e in enumerate(m.elevators):
                if not e['active']:
                    hit = [c for c in cells if c in plat[k]]
                    if hit:
                        left = [a for a in e.get('arrow_ids', []) if a in m.alive and a != i]
                        own = i in e.get('arrow_ids', [])
                        out['platform_crossings'].append(dict(t=t, arrow=i, how=how, elevator=k, cells=len(hit), platform_arrows_left=len(left),
                                                              own_platform=own))
            before = {pp['k']: pp['counter'] for pp in m.pipes}
            m.remove([i])
            out['exits'] += 1
            for k in info.get('pipes', []):
                kk = m.pipes_all[k]['k'] if k < len(m.pipes_all) else k
            for pp in m.pipes_all:
                if pp['k'] in before and pp['counter'] != before[pp['k']]:
                    out['pipe_passes'].append(dict(t=t, arrow=i, pipe=pp['k'], counter_after=pp['counter'], how=how))
                    if pp['counter'] is not None and pp['counter'] <= 0:
                        out['pipe_breaks'].append(dict(t=t, pipe=pp['k'], by_arrow=i))
            for k, b in enumerate(m.blockers):
                if b['broken'] and 'tz' not in b:
                    b['tz'] = t
                    out['box_zero'].append(dict(t=t, box=k, counter=b['counter0'], by_arrow=i))
        for k in m.activate_due():
            out['elevator'].append(dict(t=t, elevator=k, hidden=len(m.elevators[k].get('hidden_arrow_ids', []))))
    for e in sorted(rep['log'], key=lambda e: e['t']):
        k = e.get('event')
        if k == 'tap' and e.get('video') == 'exit':
            removal(e.get('group', [e['arrow']]), e['t'], 'tap')
        elif k in ('gone_without_tap', 'gone_at_elevator_drop'):
            removal([e['arrow']], e['t'], k)
    return out


def final(n):
    """attach the batch-D checks to levels/video/V2-L0NN.json; for L31 also write research/levels/L031.json (phone schema,
    source "video"). Never writes the phone's recorded L032-L061 files."""
    p = vid_path(n)
    js = json.load(open(p))
    L = vx.level_entry('V2', n)
    v1 = json.load(open(os.path.join(WD, 'V2-L%03d-verify1.json' % n)))
    rep = json.load(open(os.path.join(WD, 'V2-L%03d-replay.json' % n)))
    sol = json.load(open(os.path.join(WD, 'V2-L%03d-solve.json' % n)))
    ev = events(n)
    l2 = []
    f2 = os.path.join(WD, 'V2-L%03d-verify2.jsonl' % n)
    if os.path.exists(f2):
        for line in open(f2):
            r = json.loads(line)
            l2.append(dict(elevator=r['elevator'], frame_t=r['t'], arrows_alive=r['alive'], hidden=r['hidden'],
                           vextract=r['vextract_tol1'], registered=r['registered']['tol1'], model_best=r['best']['tol1'],
                           hidden_heads_flagged=len(r['hidden_flagged']), other_flagged=[q['id'] for q in r['per_arrow_flagged']]))
    st = rep['stats']
    if js.get('tag') == 'Hard':
        js['tag'] = 'Hard Level'          # the phone schema's tag string (as batch B); the HUD tab reads "Hard Level"
    js['checks'] = dict(
        ink_iou_tol1=dict(start_frame=dict(vextract=v1['vextract_tol1'], registered=v1['registered']['tol1'], model_best=v1['best']['tol1'],
                                           heads_flagged=len(v1['per_arrow_flagged']),
                                           body_clusters_ge25px=dict(missed=v1['residual']['missed']['body_clusters_ge25px'],
                                                                     extra=v1['residual']['extra']['body_clusters_ge25px'])),
                          hidden_layers=l2),
        replay=dict(taps=st['taps'], consistent=st['consistent'], inconsistent=st['inconsistent'], unexplained_stays=st['unexplained_stays'],
                    exit_free=st['exit_free'], bump_blocked=st['bump_blocked'], gone_free=st['gone_free'], miss=st['miss'], late=st['late'],
                    left_at_end=st['left_at_end'], blockers_broken=st.get('blockers_broken', 0), board_moves=st.get('board_moves', 0)),
        events=dict(box_zero=ev['box_zero'], pipe_passes=ev['pipe_passes'], pipe_breaks=ev['pipe_breaks'], elevator_active=ev['elevator'],
                    outside_arrows_crossing_an_inactive_platform=[x for x in ev['platform_crossings'] if not x['own_platform']]),
        solver=dict(bot_plan=sol['bot_plan'], bot_plan_no_elevator_heuristic=sol['bot_plan_no_elevator_heuristic'], model=sol['model'],
                    free_at_start=sol['free_at_start'], waves=bcheck.depth(js), random_order_dead_ends_of_300=sol['random_order_dead_ends_of_300'],
                    **{k: sol[k] for k in ('boxes', 'solvable_if_boxes_never_break', 'solvable_if_pipes_never_break') if k in sol}),
        play=dict(t_board=L['t_board'], t_first_tap=L['t_first_tap'], t_clear=L['t_clear'], t_win=L['t_win'], timer_start=L['timer_start'],
                  timer_left_at_clear=L['timer_at_clear'], hearts=[L['hearts_start'], L['hearts_end']], heart_drops=L['heart_drops'],
                  taps=L['n_taps'], reward=L['reward'], tag=L['tag'], popup_before=[b['text'][:4] for b in L['before'] if b['kind'] == 'unlock'][:1]))
    json.dump(js, open(p, 'w'), indent=1)
    out = [p]
    if n <= 31:
        dst = os.path.join(RES, 'levels', 'L%03d.json' % n)
        assert not (32 <= n <= 61)
        fj = dict(js)
        fj['batchD'] = dict(js['batchD'], final_from='V2 (the only video that shows this level)')
        json.dump(fj, open(dst, 'w'), indent=1)
        out.append(dst)
    return out

if __name__ == '__main__':
    a = sys.argv[1:]
    cmd = a.pop(0)
    if cmd == 'resid':
        js = json.load(open(a[0]))
        frame = a[1] if len(a) > 1 and not a[1].startswith('--') else os.path.join(APP, js['frame'])
        print(json.dumps(resid(js, frame, ids={x['id'] for x in js['arrows'] if x.get('layer', 1) == 1}), indent=1))
    elif cmd == 'solve':
        js = json.load(open(a[0]))
        r = solve(js)
        r2 = dead_ends(js)
        r['random_order_dead_ends_of_300'] = r2
        print(json.dumps({k: v for k, v in r.items() if k != 'seq'}), json.dumps(r.get('seq'))[:300])
    elif cmd == 'track':
        V, n = a[0], int(a[1])
        jp = a[2] if len(a) > 2 else os.path.join(RES, 'video-frames', 'work', 'extract', '%s-L%03d.json' % (V, n))
        rp = os.path.join(RES, 'video-frames', 'work', 'extract', '%s-L%03d-replay.json' % (V, n))
        tmp = os.environ.get('DCHECK_TMP', '/tmp/dcheck-%s-%d' % (V, n))
        out = track(V, n, jp, rp, tmp)
        print(json.dumps(dict(samples=len(out), median_tol1=float(np.median([x['tol1'] for x in out])))))
        for kind in ('missed', 'extra'):
            for pz in persistent(out, kind, js=json.load(open(jp))):
                print('  PERSISTENT', kind, json.dumps(pz, default=float))
        if '-v' in a:
            for x in out:
                if x['missed'] or x['extra']:
                    print('  ', json.dumps(x, default=float))
    elif cmd == 'diff':
        print(json.dumps(diff(a[0], a[1], a[2])))
    elif cmd == 'rebuild':
        print(json.dumps(rebuild(int(a[0]))))
    elif cmd == 'verify1':
        print(json.dumps(bcheck.verify(vid_path(int(a[0])), save=True)))
    elif cmd == 'verify2':
        n = int(a[0])
        for r in verify_layer2(n, os.path.join(WD, 'V2-L%03d-replay.json' % n)):
            print(json.dumps(r))
    elif cmd == 'final':
        print(final(int(a[0])))
    elif cmd == 'events':
        print(json.dumps(events(int(a[0])), indent=0))
    elif cmd == 'replay':
        print(json.dumps(run_replay(int(a[0]))))
    elif cmd == 'solveall':
        r = solve_all(int(a[0]))
        json.dump(r, open(os.path.join(WD, 'V2-L%03d-solve.json' % int(a[0])), 'w'))
        print(json.dumps({k: v for k, v in r.items() if k != 'order'}))


