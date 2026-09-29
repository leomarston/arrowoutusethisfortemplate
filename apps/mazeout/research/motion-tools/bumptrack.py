"""v552 bump: the tapped arrow's tail/head position ALONG ITS OWN PATH (+ the forward ray), body colour, blocker colour,
the contact badge, the screen-edge red vignette and the heart pieces, per real frame (movie time).
Usage: bumptrack.py  -> out/bumptrack_v552.txt"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
LV = os.path.join(mf.SP, '..', 'levels')
DIRS = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}
# clip, level, arrow id, board offset in the clip vs the start JSON (pt), crop (pt) covering path + ray, time window
CASES = [
    ('S1-L47-bump-1.mov', 47, 27, (0.0, -3.4), (220, 318, 125, 50), 0.20, 1.20),
    ('S1-L48-bump-2.mov', 48, 15, (0.0, 0.0), (140, 340, 150, 65), 0.20, 1.20),
]
out = []
def P(s):
    print(s); out.append(s)
def path_pts(cells, dirn, pitch, ox, oy, ray_cells, step=0.25):
    pts = [(ox + c * pitch, oy + r * pitch) for c, r in cells]
    dx, dy = DIRS[dirn]
    pts.append((pts[-1][0] + dx * ray_cells * pitch, pts[-1][1] + dy * ray_cells * pitch))
    # prepend a little behind the tail (opposite to the first segment)
    t0, t1 = np.array(pts[0]), np.array(pts[1]); u = (t0 - t1) / np.linalg.norm(t0 - t1)
    pts = [tuple(t0 + u * 0.4 * pitch)] + pts
    S = [0.0]; samples = []
    for a, b in zip(pts[:-1], pts[1:]):
        a = np.array(a); b = np.array(b); L = np.linalg.norm(b - a)
        for k in np.arange(0, L, step):
            samples.append(a + (b - a) * k / L)
    samples = np.array(samples)
    s = np.arange(len(samples)) * step - 0.4 * pitch      # s = 0 at the tail cell centre
    body_len = (len(cells) - 1) * pitch
    return samples, s, body_len
for clip, lvl, aid, off, crop, t0, t1 in CASES:
    d = json.load(open(os.path.join(LV, f'L{lvl:03d}.json')))
    p = d['pitch_pt']; ox, oy = d['origin_pt']; ox += off[0]; oy += off[1]
    a = [x for x in d['arrows'] if x['id'] == aid][0]
    samples, s, body_len = path_pts(a['cells'], a['dir'], p, ox, oy, 4)
    cx, cy, cw, ch = crop; SC = 4
    t, px = mf.raw(clip, t0, t1, width=int(cw * SC), crop=list(crop))
    te, pe = mf.raw(clip, t0, t1, width=26, crop=[380, 380, 13, 120], tag=clip + 'edgeR')
    tl, pl = mf.raw(clip, t0, t1, width=26, crop=[0, 380, 13, 120], tag=clip + 'edgeL')
    th, ph = mf.raw(clip, t0, t1, width=240, crop=[190, 60, 80, 90], tag=clip + 'heart')
    P(f'== {clip} L{lvl} arrow {aid} dir {a["dir"]} pitch {p} cells {len(a["cells"])} body {body_len:.2f} pt; s = pt along the path from the tail cell centre (head cell centre at s = {body_len:.2f})')
    ij = [(int(round((y - cy) * SC)), int(round((x - cx) * SC))) for x, y in samples]
    ok = [(0 <= i < px.shape[1] and 0 <= j < px.shape[2]) for i, j in ij]
    # frame 0: the blocker = first ink on the ray beyond the head tip gap
    def inkrow(f):
        vals = []
        for (i, j), o in zip(ij, ok):
            if not o: vals.append((255, 255, 255)); continue
            blk = f[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2].reshape(-1, 3).astype(int)
            k = np.argmin(blk.mean(1)); vals.append(tuple(blk[k]))
        v = np.array(vals); L = v.mean(1)
        red = (v[:, 0] - v[:, 1] > 90) & (v[:, 0] > 120)
        return v, (L < 120) | red
    v0, ink0 = inkrow(px[0].astype(int))
    # tail edge and head tip at rest
    idx = np.where(ink0)[0]
    tail0 = s[idx[0]]
    run = idx[0]
    while run + 1 < len(ink0) and ink0[run + 1]: run += 1
    head0 = s[run]
    nxt = np.where(ink0[run + 1:])[0]
    block0 = s[run + 1 + nxt[0]] if len(nxt) else None
    P(f'   rest: tail edge s={tail0:.2f}, head tip s={head0:.2f} (tip beyond head centre {head0 - body_len:.2f} pt = {(head0 - body_len)/p:.3f} pitch), blocker near edge s={block0:.2f}, gap {block0 - head0:.2f} pt = {(block0 - head0)/p:.2f} cells')
    P('   t      tail_s  head_s  disp(tail)  bodyRGB       blockerRGB    Rgreen(edgeR) Lgreen(edgeL) heartRedPx cy')
    for k in range(len(t)):
        v, ink = inkrow(px[k].astype(int))
        ii = np.where(ink & (s < block0 - 0.5))[0]
        if len(ii) == 0: continue
        tail = s[ii[0]]; r = ii[0]
        while r + 1 < len(ink) and ink[r + 1] and s[r + 1] < block0 - 0.3: r += 1
        head = s[r]
        mid = [q for q in range(len(s)) if ink[q] and tail + 3 < s[q] < head - 6]
        body = np.median(v[mid], 0).astype(int) if mid else (0, 0, 0)
        bq = [q for q in range(len(s)) if block0 + 0.3 < s[q] < block0 + 2.5]
        blk = np.median(v[bq], 0).astype(int) if bq else (0, 0, 0)
        ke = int(np.argmin(np.abs(te - t[k]))); kl = int(np.argmin(np.abs(tl - t[k]))); kh = int(np.argmin(np.abs(th - t[k])))
        gR = pe[ke][:, -2:, 1].mean(); gL = pl[kl][:, :2, 1].mean()
        hh = ph[kh].astype(int); redm = (hh[:, :, 0] > 190) & (hh[:, :, 1] < 110)
        ys, xs = np.where(redm)
        hc = (60 + ys.mean() / 3) if len(ys) else float('nan')
        P(f'   {t[k]:.3f}  {tail:6.2f}  {head:6.2f}  {tail - tail0:6.2f}  {tuple(int(x) for x in body)}  {tuple(int(x) for x in blk)}  {gR:5.0f}  {gL:5.0f}  {int(redm.sum()):5d} {hc:6.1f}')
open(os.path.join(mf.SP, 'out', 'bumptrack_v552.txt'), 'w').write('\n'.join(out) + '\n')
