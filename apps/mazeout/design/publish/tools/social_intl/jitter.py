import sys, statistics
sys.path.insert(0, '/Users/yago/Downloads/app-factory/apps/mazeout/Packages/PathCore/Tests/tools')
import soc_model as M; M.use('v552')
from socialsim import population as Pp, core as K
from datetime import datetime, timezone
T = int(datetime(2026, 9, 28, 18, tzinfo=timezone.utc).timestamp())
def run(jit):
    W = Pp.World()
    if jit:
        W.u_of = lambda c, j: (j + K.u01(W.seed, 'uj', c.ck, j)) / c.n   # stratified: u strictly increasing in j
    W.extend_to(T + 86400)
    out = {}
    for iso in ('NL', 'HU', 'ES', 'KR', 'TR'):
        tp = W.top(T, 20, iso)
        lv = [W.level(c, j, T) for (_, _, c, j) in tp]
        gaps = [a - b for (a, b), (x, y) in zip(zip(lv, lv[1:]), zip(tp, tp[1:])) if x[2].idx == y[2].idx]
        cv = statistics.pstdev(gaps) / statistics.mean(gaps) if len(gaps) > 2 and statistics.mean(gaps) > 0 else None
        out[iso] = (lv[:8], None if cv is None else round(cv, 2))
    # monotone-in-j check on 300 cohorts at 3 times
    bad = 0
    for c in [c for c in W.cohorts if c.n > 3][:300]:
        for t in (T - 86400 * 30, T, T + 3600 * 5):
            L = [W.level(c, j, t) for j in range(c.n)]
            bad += sum(1 for a, b in zip(L, L[1:]) if b < a)
    out['monotone_violations'] = bad
    return out
for jit in (False, True):
    print('jitter' if jit else 'today ', run(jit))
