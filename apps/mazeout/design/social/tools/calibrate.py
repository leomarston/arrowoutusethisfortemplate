#!/usr/bin/env python3
"""World calibration numbers quoted in SPEC-social.md §2.9. Writes design/social/bench/calibration.json."""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from socialsim import population as Pp, core as K
from datetime import datetime, timezone
def ts(*a): return int(datetime(*a, tzinfo=timezone.utc).timestamp())
out = {}
W = Pp.World()
t_v2 = ts(2026, 7, 30, 15, 27)
W.extend_to(t_v2)
out['v2_world_top8'] = [W.level(c, j, t_v2) for (_, _, c, j) in W.top(t_v2, 8)]
out['v2_original_top8'] = [11635, 10040, 9120, 9051, 8795, 8443, 8135, 8122]
N = W.joined(t_v2)
out['v2_joined'] = N
out['v2_share_at_least'] = {L: round(W.count_ge(L, t_v2) / N, 3) for L in (6, 11, 21, 51, 101, 201, 501, 1001, 2001, 5001)}
out['v2_VN_rank_at_L11'] = W.rank_of_level(11, t_v2, 'VN')
dates = [('2026-09-25', ts(2026, 9, 25)), ('2026-10-15', ts(2026, 10, 15)), ('2027-04-27', ts(2027, 4, 27)),
         ('2027-09-25', ts(2027, 9, 25)), ('2028-09-25', ts(2028, 9, 25))]
rows = []
for name, t in dates:
    W.extend_to(t)
    t0 = time.time()
    r = dict(date=name, joined=W.joined(t), cohorts=len(W.cohorts),
             top1=W.level(*W.top(t, 1)[0][2:], t), top100=W.level(*W.top(t, 100)[-1][2:], t))
    for iso in ('US', 'GB', 'DE', 'TR', 'BR', 'VN'):
        r[iso] = W.joined(t, iso)
    r['rank_world_L60'] = W.rank_of_level(60, t)
    r['rank_TR_L60'] = W.rank_of_level(60, t, 'TR')
    r['rank_US_L60'] = W.rank_of_level(60, t, 'US')
    r['rank_US_L500'] = W.rank_of_level(500, t, 'US')
    r['query_s'] = round(time.time() - t0, 2)
    rows.append(r)
    print(r, flush=True)
out['by_date'] = rows
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bench', 'calibration.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != 'by_date'}, indent=1))
