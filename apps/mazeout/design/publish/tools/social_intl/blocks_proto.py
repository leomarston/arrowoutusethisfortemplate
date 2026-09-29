#!/usr/bin/env python3
"""PROTOTYPE (scratchpad only, never shipped): per-member country BLOCKS inside the bucket cohorts.
Each shared cohort of bucket b splits its n members into contiguous index blocks, one per country row of b, sized by
systematic apportionment of the row weights (one offset u per cohort), in a per-cohort hashed row order. Sessions, levels,
gids stay exactly as today (only which country a member belongs to changes). Measures the same activity metrics as
intl_week.py so the before/after can be compared."""
import os, sys, json, heapq
sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/Packages/PathCore/Tests/tools')
import soc_model as M
M.use('v552')
from socialsim import population as Pp, data as D, core as K
from datetime import datetime, timezone

MODE = sys.argv[1]            # 'before' | 'after'
W = Pp.World()
START = int(datetime(2026, 9, 28, 0, 0, tzinfo=timezone.utc).timestamp())
W.extend_to(START + 40 * 86400)

def blocks(c):
    """[(iso, s, e)] contiguous member ranges of cohort c."""
    if MODE == 'before':
        return [(c.iso, 0, c.n)] if c.n > 0 else []
    rows = Pp.BUCKET_ROWS[D.BUCKETS[c.b]]
    tot = sum(r.weight for r in rows)
    order = sorted(range(len(rows)), key=lambda i: K.h64(W.seed, 'cord', c.ck, i))
    u = K.u01(W.seed, 'cblk', c.ck)
    out = []; cw = 0.0; prev = 0; s = 0
    for k, i in enumerate(order):
        cw += rows[i].weight
        cur = c.n if k == len(order) - 1 else min(c.n, int(K.fl(c.n * (cw / tot) + u)))
        cnt = cur - prev; prev = cur
        if cnt > 0:
            out.append((rows[i].iso, s, s + cnt)); s += cnt
    return out
BL = {c.idx: blocks(c) for c in W.cohorts}

def top(t, k, iso):
    h = []
    for c in W.cohorts:
        if c.n == 0: continue
        for (bi, s, e) in BL[c.idx]:
            if bi != iso: continue
            P = W.progress(c, e - 1, t)
            if P is not None: h.append((-P, c.gid0 + e - 1, c.idx, e - 1, s))
    heapq.heapify(h); out = []
    while h and len(out) < k:
        nP, g, ci, j, s = heapq.heappop(h); c = W.cohorts[ci]
        out.append((c, j))
        if j - 1 >= s:
            P = W.progress(c, j - 1, t)
            if P is not None: heapq.heappush(h, (-P, c.gid0 + j - 1, ci, j - 1, s))
    return out

def joined(t, iso):
    n = 0
    for c in W.cohorts:
        for (bi, s, e) in BL[c.idx]:
            if bi == iso:
                b = W.boundary(c, 1, t)
                n += max(0, e - max(b, s))
    return n

def rank_at(L, t, iso):
    n = 0
    for c in W.cohorts:
        for (bi, s, e) in BL[c.idx]:
            if bi == iso:
                b = W.boundary(c, L + 1, t)
                n += max(0, e - max(b, s))
    return 1 + n

OFF = dict(TR=180, FR=120, ES=120, IT=120, PL=120, KR=540, JP=540, NL=120, HU=120, PE=-300, PT=60, CZ=120, DE=120, US=-240)
res = {}
for iso, off in OFF.items():
    dead = 0; mv = []; coh = set()
    for day in range(7):
        for hh in range(8, 24):
            t = START + day * 86400 + hh * 3600 - off * 60
            tp = top(t, 100, iso)
            if day == 0 and hh == 20: coh = {c.idx for (c, j) in tp}
            n = sum(1 for (c, j) in tp if W.level(c, j, t) > W.level(c, j, t - 3600))
            mv.append(n); dead += (n == 0)
    T = START + 18 * 3600
    o0 = [c.gid0 + j for (c, j) in top(T, 50, iso)]
    o30 = [c.gid0 + j for (c, j) in top(T + 30 * 86400, 50, iso)]
    res[iso] = dict(N=joined(T, iso), dead=dead, median_movers=sorted(mv)[len(mv) // 2], top100_cohorts=len(coh),
                    top5=[W.level(c, j, T) for (c, j) in top(T, 5, iso)], order_changed_30d=sum(a != b for a, b in zip(o0, o30)),
                    rank_L62=rank_at(62, T, iso))
    print(MODE, iso, res[iso], flush=True)
json.dump(res, open('blocks_%s.json' % MODE, 'w'), indent=1)
