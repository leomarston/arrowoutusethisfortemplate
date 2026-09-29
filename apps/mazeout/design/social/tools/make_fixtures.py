#!/usr/bin/env python3
"""Golden vectors for PathCore's SocialTests (Swift must reproduce every value EXACTLY; doubles are written with repr(),
which round-trips: Swift `Double("…")!` parses them to the identical bit pattern).
    python3 design/social/tools/make_fixtures.py      # writes design/social/fixtures/*.json
Never edit a fixture by hand to make Swift pass — fix the Swift (or change BOTH and regenerate, noting why).
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from socialsim import core as K, population as Pp, names as Nm, events as E, data as D
from datetime import datetime, timezone

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fixtures'))
os.makedirs(OUT, exist_ok=True)

def ts(*a):
    return int(datetime(*a, tzinfo=timezone.utc).timestamp())

def dump(name, obj):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print('wrote', name)

# ---------------------------------------------------------------- hash / perm / calendar
hv = []
for seed, label, xs in [(0, '', []), (1, 'cn', [5]), (0x41524F57204F5554, 'ccountry', [123456]),
                        (42, 'ss', [7, 20600, 2]), (0xFFFFFFFFFFFFFFFF, 'avatar', [-1]), (7, 'weekly', [22])]:
    h = K.h64(seed, label, *xs)
    hv.append(dict(seed=str(seed), label=label, xs=xs, h64=str(h), unit=repr(K.unit(h))))
pv = []
for n, key in [(2, 1), (7, 99), (100, 12345), (4097, 0xDEADBEEF), (36 ** 7, 777), (2207, 0x6E616D65)]:
    pv.append(dict(n=n, key=str(key), map=[[x, K.perm(x, n, key)] for x in (0, 1, n // 3, n // 2, n - 1)]))
cal = []
for t in (ts(2026, 4, 27, 6, 59, 59), ts(2026, 4, 27, 7, 0, 0), ts(2026, 9, 25, 0, 6), ts(2026, 9, 28, 7, 0), ts(2030, 1, 1)):
    cal.append(dict(t=t, eventDay=K.event_day(t), eventWeek=K.event_week(t),
                    local=[[off] + list(K.local_day_minute(t, off)) for off in (-480, 0, 180, 330, 540)]))
dump('core.json', dict(h64=hv, perm=pv, calendar=cal, epoch=K.EPOCH))

# ---------------------------------------------------------------- names
nv = []
for st in Nm.STYLES:
    cults = D.CULTURES if st in Nm.CULTURE_STYLES else ['en']
    for cu in cults:
        for slot in (0, 1, 17, 999, 2500, 123456):
            if st == 'default':
                nv.append(dict(style=st, culture='*', slot=slot, name=Nm.default_name(slot, 0)))
            else:
                nv.append(dict(style=st, culture=cu if st in Nm.CULTURE_STYLES else '*', slot=slot, name=Nm.decode(st, slot, cu)))
        if st not in Nm.CULTURE_STYLES:
            break
blk = [(s, Nm.is_blocked(s)) for s in ['Kate23', 'player_5h1tabc', 'Arthur3', 'SunnyOtter', 'kanye', 'Peacock', 'ass_x',
                                       'Cassandra', 'DSMShark', 'Naz1', 'GOLDEN']]
dump('names.json', dict(decode=nv, blocked=[dict(name=s, blocked=b) for s, b in blk],
                        number=[dict(r=r, key=str(k), s=Nm.number(r, k)) for r, k in [(1, 5), (9, 5), (10, 5), (57, 99), (500, 3), (12345, 8)]]))

# ---------------------------------------------------------------- world
T = ts(2026, 9, 25, 1, 0)
W = Pp.World(); W.extend_to(T)
coh = []
for c in W.cohorts[:40] + W.cohorts[1000:1010] + W.cohorts[-10:]:
    coh.append(dict(idx=c.idx, ck=c.ck, p=c.p, b=c.b, a=c.a, day=c.day, n=c.n, gid0=c.gid0, iso=c.iso, off=c.off,
                    culture=c.culture, v=repr(c.v), pace=repr(c.pace), m=[repr(x) for x in c.m], ml=[repr(x) for x in c.ml],
                    join0=repr(c.join0), R=None if c.R is None else repr(c.R),
                    styles=[[st, lo, hi, base] for (st, lo, hi), base in zip(c.style_cum, c.style_base)]))
sess = []
for c in [W.cohorts[i] for i in (3, 77, 500, 1500, 2400) if i < len(W.cohorts)]:
    for dl in (40, 41, 150):
        s = W.sessions(c, dl)
        sess.append(dict(idx=c.idx, dl=dl, sessions=None if not s else dict(starts=[repr(x) for x in s[0]],
                                                                              f=[repr(x) for x in s[1]], pace=repr(s[2]), m=repr(s[3]))))
mem = []
import random
rng = random.Random(5)
for _ in range(160):
    c = rng.choice([q for q in W.cohorts if q.n > 0 and q.join0 - q.span < T])
    j = rng.randrange(c.n)
    u, lam, J, T1, F, T2 = W.member(c, j)
    for t in (J - 10, J + 600, (J + T) / 2.0, T, T1 + 3 * 86400):
        P = W.progress(c, j, t)
        mem.append(dict(idx=c.idx, j=j, t=repr(float(t)), P=None if P is None else repr(P), level=W.level(c, j, t)))
nm = []
for _ in range(120):
    c = rng.choice([q for q in W.cohorts if q.n > 0])
    j = rng.randrange(c.n)
    name, st = W.name(c, j)
    nm.append(dict(idx=c.idx, j=j, gid=W.gid(c, j), name=name, style=st, avatar=W.avatar(c, j, st)))
dump('world.json', dict(t=T, cohortCount=len(W.cohorts), members=W.next_gid, gidLimit=W.gid_limit(T),
                        cohorts=coh, sessions=sess, progress=mem, names=nm))

# ---------------------------------------------------------------- queries
q = []
for (y, mo, d, h), x, iso in [((2026, 7, 30, 15), 11, 'VN'), ((2026, 9, 25, 1), 56, 'TR'), ((2026, 9, 25, 1), 56, None),
                              ((2026, 9, 25, 1), 3, 'US'), ((2026, 9, 25, 1), 900, 'GB')]:
    t = ts(y, mo, d, h)
    ab, be = W.neighbours(x, t, 5, 5, iso)
    q.append(dict(t=t, level=x, iso=iso, countGE=W.count_ge(x + 1, t, iso), rank=W.rank_of_level(x, t, iso),
                  above=[g for (_, g, _, _) in ab], below=[g for (_, g, _, _) in be]))
tops = []
for t, iso in [(ts(2026, 7, 30, 15), None), (T, None), (T, 'TR')]:
    tops.append(dict(t=t, iso=iso, top=[[g, W.level(c, j, t)] for (_, g, c, j) in W.top(t, 25, iso)]))
dump('queries.json', dict(rank=q, top=tops))

# ---------------------------------------------------------------- events
W.extend_to(T + 9 * 86400)
wk = E.WeeklyContest(W, 12345, K.event_week(T), T, 120.0, [(T - 7200, T - 5400), (T - 3600, T - 1800)])
st = E.StreakRace(W, 12345, K.event_day(T), T, 20.0)
rr = E.RocketRace(W, 12345, 1, 1, T, 110.0)
sj = [dict(attempt=a, stage=s, alive=E.SkyJump(12345, a, s).alive, share=E.SkyJump(12345, a, s).share)
      for a, s in [(1, 1), (2, 1), (3, 2), (4, 3)]]
dump('events.json', dict(
    t=T, installSeed=12345,
    weekly=dict(week=K.event_week(T), ref=120.0, members=[W.gid(c, j) for c, j in wk.members],
                arrive=[repr(a) for a in wk.arrive], base=wk.base,
                standings48h=[[x[2], -x[0]] for x in wk.standings(T + 48 * 3600, 30, T + 40 * 3600)]),
    streak=dict(day=K.event_day(T), ref=20.0, members=[W.gid(c, j) for c, j in st.members], arrive=[repr(a) for a in st.arrive],
                s0=st.s0, q=[repr(x) for x in st.q],
                scores6h=[st.member_score(i, T + 6 * 3600) for i in range(len(st.members))],
                standings6h=[[x[2], -x[0]] for x in st.standings(T + 6 * 3600, 400, T + 5 * 3600)]),
    rocket=dict(raceId=1, stage=1, spw=110.0, rivals=[W.gid(c, j) for c, j in rr.rivals], hold=[repr(x) for x in rr.hold],
                delta=[repr(x) for x in rr.delta], natural=[None if x is None else repr(x) for x in rr.natural],
                progress=[[m, [rr.rival_progress(i, T + m * 60, None) for i in range(4)]] for m in (5, 10, 20, 40, 90)]),
    sky=sj))
