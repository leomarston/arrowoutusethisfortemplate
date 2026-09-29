#!/usr/bin/env python3
"""200 nicknames as the owner would meet them + example views. Writes design/social/bench/samples.json.
    python3 design/social/tools/sample_names.py
"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from socialsim import population as Pp, events as E, core as K, data as D
from datetime import datetime, timezone
def ts(*a): return int(datetime(*a, tzinfo=timezone.utc).timestamp())
T = ts(2026, 10, 12, 18, 0)
W = Pp.World(); W.extend_to(T + 9 * 86400)
# (a) 200 custom nicknames, evenly spread over the world (every k-th custom-named player)
custom = []
total = W.gid_limit(T)
step = 0
for c in W.cohorts:
    if c.p > K.event_week(T):
        break
    for j in range(c.n):
        nm, st = W.name(c, j)
        if st not in ('default', 'fallback'):
            custom.append((nm, st, c.iso))
k = max(1, len(custom) // 200)
sample = custom[::k][:200]
styles = collections.Counter(st for _, st, _ in sample)
# (b) views
def rows(lst, t):
    return [(W.row(c, j, t)['name'], W.level(c, j, t)) for (_, _, c, j) in lst]
top = rows(W.top(T, 12), T)
ab, be = W.neighbours(56, T, 5, 5, 'TR')
R = W.rank_of_level(56, T, 'TR')
wk = E.WeeklyContest(W, 777, K.event_week(T), T, 90.0)
st = wk.standings(T + 30 * 3600, 21, T + 29 * 3600)
weekly = [('YOU' if i < 0 else W.name(*wk.members[i])[0], -s) for (s, _, i) in st[:12]]
sr = E.StreakRace(W, 777, K.event_day(T), T, 18.0)
st2 = sr.standings(T + 5 * 3600, 342, T + 4 * 3600)
streak = [('YOU' if i < 0 else W.name(*sr.members[i])[0], -s) for (s, _, i) in st2[:12]]
rr = E.RocketRace(W, 777, 3, 1, T, 105.0)
rocket = [(W.name(c, j)[0], rr.rival_progress(i, T + 9 * 60, None)) for i, (c, j) in enumerate(rr.rivals)]
out = dict(t=T, customShare=round(len(custom) / total, 3), sample200=[n for n, _, _ in sample], styles=dict(styles),
           worldTop12=top, countryTR=dict(rank=R, above=rows(list(reversed(ab)), T), below=rows(be, T)),
           weeklyTop12_after30h=weekly, streakRace_after5h=streak, rocketRace_after9min=rocket)
path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bench', 'samples.json'))
json.dump(out, open(path, 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k != 'sample200'}, ensure_ascii=False, indent=0))
print('\n'.join(', '.join(out['sample200'][i:i + 10]) for i in range(0, 200, 10)))
