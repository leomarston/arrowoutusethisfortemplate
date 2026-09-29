#!/usr/bin/env python3
"""Week-long activity audit of Country boards (shipped v552 reference, read-only).
For each country: over 7 local days x local hours 08..23, how many hours show NO level change in the Country top 100
(+ the L60 +-10 window) during that hour; and how many distinct cohorts the top 100 comes from."""
import os, sys, json, collections
APP = '/Users/yago/Downloads/app-factory/apps/mazeout'
sys.path.insert(0, os.path.join(APP, 'Packages', 'PathCore', 'Tests', 'tools'))
import soc_model as M
M.use('v552')
from socialsim import population as Pp, data as D
from datetime import datetime, timezone
REAL = dict(US=-240, GB=60, DE=120, FR=120, ES=120, IT=120, BR=-180, TR=180, JP=540, KR=540, CN=480, PL=120, SK=120,
            SI=120, IN=330, SA=180, PT=60, NL=120, VN=420, PE=-300, HU=120, CZ=120)
TABLE = {r.iso for r in D.COUNTRY_ROWS}
START = int(datetime(2026, 9, 28, 0, 0, tzinfo=timezone.utc).timestamp())
shared = Pp.World(); shared.extend_to(START + 9 * 86400)
out = {}
for iso, off in REAL.items():
    W = shared
    if iso not in TABLE:
        W = Pp.World(local=(iso, off, D.EXTRA_CULTURE.get(iso, 'en'))); W.extend_to(START + 9 * 86400)
    dead = 0; total = 0; movers = []
    cohorts = set()
    for day in range(7):
        for h in range(8, 24):
            t = START + day * 86400 + h * 3600 - off * 60
            top = [(c, j) for (_, _, c, j) in W.top(t, 100, iso)]
            if day == 0 and h == 20:
                cohorts = {c.idx for (c, j) in top}
            n = sum(1 for (c, j) in top if W.level(c, j, t) > W.level(c, j, t - 3600))
            movers.append(n)
            total += 1
            if n == 0:
                dead += 1
    out[iso] = dict(N=W.joined(START, iso), dead_daytime_hours=dead, of=total, median_movers=sorted(movers)[len(movers) // 2],
                    top100_cohorts=len(cohorts))
    print(iso, out[iso], flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
