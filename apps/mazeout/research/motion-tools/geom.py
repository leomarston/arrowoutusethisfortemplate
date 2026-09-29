"""Arrow geometry from lossless start shots (3 px/pt) + the level JSONs (the shot each JSON was read from):
stroke width (integrated darkness across straight segments), tail cap (centre-line extension + end width profile),
corner rounding (outer/inner edge along the diagonal), arrowhead (width profile along the head axis), per pitch.
-> out/geom.txt"""
import os, sys, json
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mf
R = os.path.join(mf.SP, '..')
LV = {32: 'shots/003-L32-start.png', 34: 'shots/036-L034-start.png', 35: 'shots/042-L035-start.png', 40: 'shots/071-L040-start.png',
      45: 'shots/097-L045-start.png', 50: 'shots/135-L050-start.png', 52: 'shots/145-L052-start.png', 59: 'shots/190-L059-start.png'}
DIRS = {'left': (-1, 0), 'right': (1, 0), 'up': (0, -1), 'down': (0, 1)}
out = []
def P(s):
    print(s); out.append(s)
def dark(img, xs, ys, k):
    # bilinear sample of darkness (1 - L/255) at pt coords
    return map_coordinates(img, [np.asarray(ys) * k - 0.5, np.asarray(xs) * k - 0.5], order=1, mode='nearest')
for lvl, shot in LV.items():
    d = json.load(open(os.path.join(R, 'levels', f'L{lvl:03d}.json'))); p = d['pitch_pt']; ox, oy = d['origin_pt']
    im = np.array(Image.open(os.path.join(R, shot)).convert('RGB')).astype(float)
    k = im.shape[1] / 393.0
    D = 1 - im.mean(2) / 255.0   # darkness
    occ = {tuple(c): a['id'] for a in d['arrows'] for c in a['cells']}
    widths, capx, caps_w, corners_out, corners_in, heads = [], [], [], [], [], []
    for a in d['arrows']:
        cells = [tuple(c) for c in a['cells']]
        C = [np.array((ox + c * p, oy + r * p)) for c, r in cells]
        # straight interior points: cell i whose neighbours i-1, i+1 are collinear with it
        for i in range(1, len(cells) - 2):
            u = C[i + 1] - C[i]; v = C[i] - C[i - 1]
            if np.allclose(u, v):
                m = (C[i] + C[i + 1]) / 2       # mid between two cell centres (no dot / no corner)
                n = np.array((-u[1], u[0])) / np.linalg.norm(u)
                s = np.arange(-0.45 * p, 0.45 * p, 0.05)
                prof = dark(D, m[0] + n[0] * s, m[1] + n[1] * s, k)
                if prof[0] < 0.02 and prof[-1] < 0.02: widths.append(prof.sum() * 0.05)
        # tail cap: along -u from the tail centre
        u = (C[1] - C[0]) / np.linalg.norm(C[1] - C[0]); n = np.array((-u[1], u[0]))
        s = np.arange(0, 0.5 * p, 0.05)
        prof = dark(D, C[0][0] - u[0] * s, C[0][1] - u[1] * s, k)
        behind = (cells[0][0] - int(u[0]), cells[0][1] - int(u[1]))
        if behind not in occ and prof[-1] < 0.02:
            capx.append(np.interp(0.5, prof[::-1], s[::-1]))   # 50 % point beyond the tail centre
            # width at 0.5, 1.0, 1.5 pt before the cap end (across)
            e = capx[-1]; ws = []
            for back in (0.3, 0.8, 1.3, 2.5):
                q = C[0] - u * (e - back); ss = np.arange(-0.45 * p, 0.45 * p, 0.05)
                pr = dark(D, q[0] + n[0] * ss, q[1] + n[1] * ss, k); ws.append(pr.sum() * 0.05)
            caps_w.append(ws)
        # corners: cell i with a turn; diagonal outward = -(u_in) + u_out ... outer corner direction = (v - u) where v = in-dir
        for i in range(1, len(cells) - 1):
            vin = (C[i] - C[i - 1]) / p; vout = (C[i + 1] - C[i]) / p
            if abs(np.dot(vin, vout)) < 0.01:
                outer = (vin - vout) / np.sqrt(2)      # points to the outside of the turn
                s = np.arange(-0.5 * p, 0.5 * p, 0.05)
                prof = dark(D, C[i][0] + outer[0] * s, C[i][1] + outer[1] * s, k)
                if prof[0] > 0.02 or prof[-1] > 0.02: continue
                ink = np.where(prof > 0.5)[0]
                if len(ink): corners_out.append(s[ink[-1]]); corners_in.append(s[ink[0]])
        # head: width profile along the head axis
        dvec = np.array(DIRS[a['dir']], float); n = np.array((-dvec[1], dvec[0]))
        H = C[-1]; prof_w = []
        ok = True
        for sa in np.arange(-0.45 * p, 0.7 * p, 0.25):
            q = H + dvec * sa; ss = np.arange(-0.48 * p, 0.48 * p, 0.05)
            pr = dark(D, q[0] + n[0] * ss, q[1] + n[1] * ss, k)
            if pr[0] > 0.05 or pr[-1] > 0.05: ok = False; break
            prof_w.append((sa, pr.sum() * 0.05))
        if ok: heads.append(prof_w)
    w = np.median(widths)
    P(f'== L{lvl} {shot} pitch {p:.3f} (JSON stroke {d["stroke_pt"]})')
    P(f'   stroke width (integrated darkness, n={len(widths)}): median {w:.3f} pt = {w/p:.4f} pitch (IQR {np.percentile(widths,25):.3f}-{np.percentile(widths,75):.3f})')
    if capx:
        cw = np.median(np.array(caps_w), 0)
        P(f'   tail cap: 50% point {np.median(capx):.3f} pt beyond the tail centre (= {np.median(capx)/(w/2):.2f} x half-width, n={len(capx)}); width at 0.3/0.8/1.3/2.5 pt before the end: ' + ' / '.join(f'{x:.2f}' for x in cw) + f'  (round cap of r={w/2:.2f} predicts ' + ' / '.join(f'{2*np.sqrt(max(0,(w/2)**2-((w/2)-b)**2)) if b < w/2 else w:.2f}' for b in (0.3, 0.8, 1.3, 2.5)) + ')')
    if corners_out:
        co, ci = np.median(corners_out), np.median(corners_in)
        # sharp miter: outer edge at +w/2*sqrt2, inner at -w/2*sqrt2 ; rounded centreline radius Rc: centreline at -Rc*(sqrt2-1)
        P(f'   corners (n={len(corners_out)}): outer 50% edge at {co:+.3f} pt, inner at {ci:+.3f} pt along the outward diagonal from the cell centre; sharp miter would be +/-{w/2*np.sqrt(2):.3f}; centreline offset {(co+ci)/2:+.3f} pt -> fillet radius Rc ~ {-(co+ci)/2/(np.sqrt(2)-1):.2f} pt = {-(co+ci)/2/(np.sqrt(2)-1)/p:.3f} pitch (outer-edge radius {(-(co+ci)/2/(np.sqrt(2)-1)) + w/2:.2f} pt)')
    if heads:
        Hm = np.median(np.array([[x[1] for x in h] for h in heads]), 0); sa = [x[0] for x in heads[0]]
        maxw = Hm.max(); ib = int(np.argmax(Hm))
        tip = next((sa[j] for j in range(ib, len(Hm)) if Hm[j] < 0.25), np.nan)
        # base = first s where width exceeds 1.5 x stroke
        base = next((sa[j] for j in range(len(Hm)) if Hm[j] > 1.5 * w), np.nan)
        P(f'   head (n={len(heads)}): max width {maxw:.2f} pt = {maxw/p:.3f} pitch at s={sa[ib]:+.2f} pt; base (width>1.5 stroke) at s={base:+.2f} pt = {base/p:+.3f} pitch; tip (width<0.25) at s={tip:+.2f} pt = {tip/p:+.3f} pitch; length base->tip {tip-base:.2f} pt = {(tip-base)/p:.3f} pitch')
        P('   head width profile (s pt: width pt): ' + ' '.join(f'{s_:+.2f}:{v:.2f}' for s_, v in zip(sa, Hm)))
open(os.path.join(mf.SP, 'out', 'geom.txt'), 'w').write('\n'.join(out) + '\n')
