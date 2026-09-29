"""Exit tracker along the arrow's OWN path + its forward ray (level JSON geometry, board offset auto-fitted on the
pre-tap frame). Per real frame: head tip s and tail edge s (pt along the path, s = 0 at the tail cell centre).
Ink = dark (L < 110) or saturated (max-min > 90, not the vacated-dot blue). Stops when the head reaches the HUD /
booster zone or the screen edge. Usage: exittrack.py NAME -> out/exittrack_NAME.txt (+ data for exitfit2.py)"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
LV = os.path.join(mf.SP, '..', 'levels')
DIRS = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}
# name: clip, level, arrow id, t window, pre-tap reference time, extra (dx,dy) search centre
CASES = {
 'L47-headtap': ('S1-L47-headtap-long-exit.mov', 47, 21, (0.0, 2.6), 0.05),
 'L52-a':       ('S1-L52-three-exits.mov', 52, 3, (0.0, 1.2), 0.05),
 'L52-b':       ('S1-L52-three-exits.mov', 52, 5, (0.0, 1.9), 0.05),
 'L52-c':       ('S1-L52-three-exits.mov', 52, 0, (0.0, 3.6), 0.05),
 'L50-box':     ('S1-L50-box-break.mov', 50, 10, (0.0, 1.6), 0.05),
 'L50-last':    ('S1-L50-win-seq-1.mov', 50, 9, (0.0, 1.2), 0.05),
}
SC = 3
def polyline(cells, dirn, pitch, ox, oy, extend_cells=60, step=0.25):
    pts = [np.array((ox + c * pitch, oy + r * pitch)) for c, r in cells]
    dx, dy = DIRS[dirn]
    pts.append(pts[-1] + np.array((dx, dy)) * extend_cells * pitch)
    u = (pts[0] - pts[1]) / np.linalg.norm(pts[0] - pts[1])
    pts = [pts[0] + u * 0.4 * pitch] + pts
    S = []
    for a, b in zip(pts[:-1], pts[1:]):
        L = np.linalg.norm(b - a)
        for k in np.arange(0, L, step): S.append(a + (b - a) * k / L)
    S = np.array(S); s = np.arange(len(S)) * step - 0.4 * pitch
    return S, s
def classify(v):
    v = v.astype(int); L = v.mean(-1); sat = v.max(-1) - v.min(-1)
    dot = (np.abs(v[..., 0] - 197) < 30) & (np.abs(v[..., 1] - 225) < 25) & (v[..., 2] > 225)
    return (L < 110) | ((sat > 90) & ~dot)
def occluded(x, y):
    return (y < 146) or (y > 770 and (x < 84 or x > 309)) or x < 0.5 or x > 392.5 or y < 0.5 or y > 851.5
def run(name):
    clip, lvl, aid, (t0, t1), tref = CASES[name]
    d = json.load(open(os.path.join(LV, f'L{lvl:03d}.json'))); p = d['pitch_pt']; ox, oy = d['origin_pt']
    a = [x for x in d['arrows'] if x['id'] == aid][0]
    body = (len(a['cells']) - 1) * p
    # crop = bbox of path + ray (clipped to the screen) + margin for the offset search
    S0, s0 = polyline(a['cells'], a['dir'], p, ox, oy)
    vis = np.array([not occluded(x, y) for x, y in S0])
    xs, ys = S0[vis, 0], S0[vis, 1]
    M = 16
    cx, cy = max(0, xs.min() - M), max(0, ys.min() - M); cw, ch = min(393, xs.max() + M) - cx, min(852, ys.max() + M) - cy
    t, px = mf.raw(clip, t0, t1, width=int(round(cw * SC)), crop=[cx, cy, cw, ch], tag=f'ex_{name}')
    H, W = px.shape[1:3]
    def sample(f, S):
        ii = np.clip(np.round((S[:, 1] - cy) * SC).astype(int), 0, H - 1); jj = np.clip(np.round((S[:, 0] - cx) * SC).astype(int), 0, W - 1)
        return f[ii, jj]
    # offset search on the reference frame: maximise dark coverage of the BODY samples
    kref = int(np.argmin(np.abs(t - tref)))
    bodymask = s0 <= body
    best = (-1, 0, 0)
    for dx in np.arange(-14, 14.01, 0.5):
        for dy in np.arange(-14, 14.01, 0.5):
            S = S0[bodymask] + (dx, dy)
            v = sample(px[kref], S); L = v.astype(int).mean(-1)
            sc = (L < 110).mean()
            if sc > best[0]: best = (sc, dx, dy)
    sc, dx, dy = best
    S = S0 + (dx, dy)
    occ = np.array([occluded(x, y) for x, y in S])
    lines = [f'== {name}: {clip} L{lvl} arrow {aid} dir {a["dir"]} cells {len(a["cells"])} body {body:.2f} pt pitch {p} ; board offset ({dx:+.1f},{dy:+.1f}) pt, body dark coverage {sc:.3f}']
    ink0 = classify(sample(px[kref], S)) & ~occ
    i0 = np.where(ink0)[0]; r = i0[0]
    while r + 1 < len(ink0) and ink0[r + 1]: r += 1
    head0 = s0[r]; tail0 = s0[i0[0]]
    first_occ = s0[np.where(occ & (s0 > body))[0][0]] if (occ & (s0 > body)).any() else s0[-1]
    lines.append(f'   rest head tip s={head0:.2f} (beyond head centre {head0-body:.2f} pt = {(head0-body)/p:.3f} pitch), tail edge s={tail0:.2f}; ray visible until s={first_occ:.1f} (then HUD/booster/screen edge)')
    lines.append('   t      head_s   tail_s   dhead_pt  dtail_pt  headRGB')
    data = []
    prev = head0
    for k in range(len(t)):
        v = sample(px[k], S); ink = classify(v) & ~occ
        # head: furthest s with >= 70% ink in the 4 pt behind it, not jumping back
        cs = np.concatenate([[0], np.cumsum(ink)])
        n = 16
        good = [i for i in range(n, len(ink)) if ink[i] and (cs[i + 1] - cs[i + 1 - n]) >= 0.7 * n]
        if not good: continue
        hi = max(good); head = s0[hi]
        tl = [i for i in range(len(ink) - n) if ink[i] and (cs[i + n] - cs[i]) >= 0.7 * n]
        tail = s0[min(tl)] if tl else float('nan')
        hv = tuple(int(x) for x in v[max(hi - 12, 0)])
        lines.append(f'   {t[k]:.3f}  {head:7.2f}  {tail:7.2f}  {head-head0:7.2f}  {tail-tail0:7.2f}  {hv}')
        data.append((t[k], head - head0, tail - tail0, head >= first_occ - 1))
    open(os.path.join(mf.SP, 'out', f'exittrack_{name}.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:3])); print('   ...', len(data), 'frames')
    return data, p, body, head0, first_occ
if __name__ == '__main__':
    for n in (sys.argv[1:] or CASES):
        run(n)
