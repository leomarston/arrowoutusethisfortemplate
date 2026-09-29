import sys, heapq
sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/Packages/PathCore/Tests/tools')
import soc_model as M; M.use('v552')
from socialsim import population as Pp, data as D, core as K
from datetime import datetime, timezone
T = int(datetime(2026, 9, 28, 18, tzinfo=timezone.utc).timestamp())
W = Pp.World(); W.extend_to(T + 86400)
def blocks(c, mode):
    if c.n == 0: return []
    if mode == 'before': return [(c.iso, 0, c.n)]
    rows = Pp.BUCKET_ROWS[D.BUCKETS[c.b]]; tot = sum(r.weight for r in rows)
    order = sorted(range(len(rows)), key=lambda i: K.h64(W.seed, 'cord', c.ck, i)); u = K.u01(W.seed, 'cblk', c.ck)
    out = []; cw = 0.0; prev = 0; s = 0
    for k, i in enumerate(order):
        cw += rows[i].weight
        cur = c.n if k == len(order) - 1 else min(c.n, int(K.fl(c.n * (cw / tot) + u)))
        if cur - prev > 0: out.append((rows[i].iso, s, s + cur - prev)); s += cur - prev
        prev = cur
    return out
def top(t, k, iso, mode):
    h = []
    for c in W.cohorts:
        for (bi, s, e) in blocks(c, mode):
            if bi != iso: continue
            P = W.progress(c, e - 1, t)
            if P is not None: h.append((-P, c.gid0 + e - 1, c.idx, e - 1, s))
    heapq.heapify(h); out = []
    while h and len(out) < k:
        nP, g, ci, j, s = heapq.heappop(h); c = W.cohorts[ci]; out.append((c, j))
        if j - 1 >= s:
            P = W.progress(c, j - 1, t)
            if P is not None: heapq.heappush(h, (-P, c.gid0 + j - 1, ci, j - 1, s))
    return out
print('same-cohort adjacent pairs in the Country top 20 (a pair from one cohort = an evenly spaced "ladder" step)')
for iso in ('US', 'DE', 'FR', 'ES', 'IT', 'BR', 'TR', 'JP', 'KR', 'PL', 'IN', 'SA', 'NL', 'HU', 'PE'):
    r = {}
    for mode in ('before', 'after'):
        tp = top(T, 20, iso, mode)
        r[mode] = (sum(1 for a, b in zip(tp, tp[1:]) if a[0].idx == b[0].idx), [W.level(c, j, T) for (c, j) in tp[:6]])
    print('%s  before %2d/19 %s   after %2d/19 %s' % (iso, r['before'][0], r['before'][1], r['after'][0], r['after'][1]))
