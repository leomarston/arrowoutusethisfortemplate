#!/usr/bin/env python3
"""soc_fixtures.py — SOC1's extra golden vectors (on top of design/social/fixtures), from the UNMODIFIED Python reference
(design/social/tools/socialsim) run with one of SOC1's parameter sets (soc_model.py):

    python3 Packages/PathCore/Tests/tools/soc_fixtures.py reference   # -> Tests/Fixtures/soc_reference_{world,events}.json
    python3 Packages/PathCore/Tests/tools/soc_fixtures.py v552        # -> Tests/Fixtures/soc_v552_{world,events}.json

World boards at 24 times across 3+ years (joined, gid limits, top-25, ranks World/Country, neighbour ids, materialised
rows), 1,500 nicknames/avatars spread over the 3-year world, a LOCAL partition, Weekly/Streak groups, Rocket races,
Sky Jump curves, user pace; for the shipped model also 3,000+ drawn nicknames (SOC1c). Doubles are Python repr() strings (Swift `Double(String)` restores the same bits).
Never edit a fixture by hand: fix the Swift, or change BOTH implementations and regenerate (noting why).
"""
import os, sys, json, random, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import soc_model as M                                    # noqa: E402  (must precede the socialsim imports)
from socialsim import core as K, population as Pp, names as Nm, events as E, data as D   # noqa: E402
from datetime import datetime, timezone                  # noqa: E402

MODEL = sys.argv[1] if len(sys.argv) > 1 else 'v552'
M.use(MODEL)
OUT = os.path.normpath(os.path.join(HERE, '..', 'Fixtures'))
R = repr


def ts(*a):
    return int(datetime(*a, tzinfo=timezone.utc).timestamp())


def dump(name, obj):
    path = os.path.join(OUT, 'soc_%s_%s.json' % (MODEL, name))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=None, separators=(',', ':'))
    print('wrote', path, os.path.getsize(path), 'bytes', flush=True)


t_start = time.time()
TIMES = [ts(2026, 4, 28, 12, 0), ts(2026, 5, 10, 18, 30), ts(2026, 6, 1, 3, 0), ts(2026, 7, 1, 21, 15),
         ts(2026, 7, 30, 15, 27), ts(2026, 8, 20, 9, 0), ts(2026, 9, 25, 1, 31), ts(2026, 10, 5, 18, 0),
         ts(2026, 11, 11, 11, 11), ts(2026, 12, 24, 20, 0), ts(2027, 2, 1, 7, 0), ts(2027, 3, 15, 13, 45),
         ts(2027, 4, 27, 7, 0), ts(2027, 6, 10, 22, 0), ts(2027, 8, 1, 5, 30), ts(2027, 9, 25, 12, 0),
         ts(2027, 11, 20, 16, 0), ts(2028, 1, 15, 2, 0), ts(2028, 3, 30, 19, 0), ts(2028, 6, 1, 12, 0),
         ts(2028, 9, 25, 8, 0), ts(2029, 1, 10, 21, 0), ts(2029, 5, 5, 5, 5), ts(2029, 9, 20, 14, 0)]
W = Pp.World()
W.extend_to(TIMES[-1] + 2 * 86400)


def row(c, j, t):
    nm, st = W.name(c, j)
    return [W.gid(c, j), nm, st, W.avatar(c, j, st), W.level(c, j, t)]


# ---------------------------------------------------------------- world boards at 24 times
boards = []
for t in TIMES:
    b = dict(t=t, joined=W.joined(t), gidLimit=W.gid_limit(t))
    tp = W.top(t, 25)
    b['top'] = [[g, R(P)] for (P, g, _, _) in tp]
    b['topRows'] = [row(c, j, t) for (_, _, c, j) in tp[:10]]
    b['rank'] = {str(x): W.rank_of_level(x, t) for x in (1, 11, 62, 300)}
    b['country'] = {iso: dict(joined=W.joined(t, iso), rank={str(x): W.rank_of_level(x, t, iso) for x in (11, 62, 300)})
                    for iso in ('TR', 'US', 'GB', 'VN')}
    ab, be = W.neighbours(62, t, 5, 5)
    b['nb62'] = dict(above=[[g, R(P)] for (P, g, _, _) in ab], below=[[g, R(P)] for (P, g, _, _) in be])
    ab, be = W.neighbours(62, t, 6, 6, 'TR')
    b['nbTR62'] = dict(above=[[g, R(P)] for (P, g, _, _) in ab], below=[[g, R(P)] for (P, g, _, _) in be],
                       rows=[row(c, j, t) for (_, _, c, j) in ab + be])
    tpc = W.top(t, 12, 'TR')
    b['topTR'] = [row(c, j, t) for (_, _, c, j) in tpc]
    boards.append(b)
    print('board', datetime.fromtimestamp(t, timezone.utc).date(), 'joined', b['joined'], 'top1',
          1 + int(float(b['top'][0][1])) if b['top'] else None, '%.0fs' % (time.time() - t_start), flush=True)

# ---------------------------------------------------------------- 1,500 players spread over the 3-year world
rng = random.Random(1552)
T_END = TIMES[-1]
players = []
live = [c for c in W.cohorts if c.n > 0 and c.join0 - c.span < T_END]
for k in range(1500):
    c = live[rng.randrange(len(live))]
    j = rng.randrange(c.n)
    t = TIMES[k % len(TIMES)]
    P = W.progress(c, j, t)
    players.append([c.idx, j] + row(c, j, t) + [t, None if P is None else R(P)])
cohorts = []
for c in W.cohorts[::97]:
    cohorts.append([c.idx, c.ck, c.p, c.b, c.a, c.day, c.n, c.gid0, c.iso, c.off, c.culture, R(c.v), R(c.pace), R(c.T), R(c.Tl),
                    R(c.join0), None if c.R is None else R(c.R), [[st, lo, hi, base] for (st, lo, hi), base in zip(c.style_cum, c.style_base)]])

# ---------------------------------------------------------------- LOCAL partition (a country missing from the table)
T_L = ts(2027, 3, 1, 12, 0)
WL = Pp.World(local=('IS', 0, 'nordic')); WL.extend_to(T_L)
lc = [c for c in WL.cohorts if c.local and c.n > 0][:12]
local = dict(t=T_L, cohortCount=len(WL.cohorts), rows=[[c.idx, c.gid0, c.n] + [WL.name(c, j)[0] for j in range(min(3, c.n))]
                                                     + [WL.level(c, c.n - 1, T_L)] for c in lc],
             rankIS62=WL.rank_of_level(62, T_L, 'IS'), joinedIS=WL.joined(T_L, 'IS'),
             topIS=[[g, R(P)] for (P, g, _, _) in WL.top(T_L, 10, 'IS')])

# ---------------------------------------------------------------- nickname decoding of this model (styles x cultures x slots)
# (the reference's vectors are in design/social/fixtures/names.json; the shipped model adds the 'leet' style and the case /
# digit variants of names.VARIANTS)
names = []
for st in Nm.STYLES_V2:
    if st == 'default':
        continue
    for cu in (D.CULTURES if st in Nm.CULTURE_STYLES else ['en']):
        for slot in (0, 1, 17, 999, 2500, 40001, 123456, 5000000):
            names.append([st, cu if st in Nm.CULTURE_STYLES else '*', slot, Nm.decode(st, slot, cu)])
# drawn nicknames (the shipped model, SOC1c: names.DRAW; duplicates allowed): every style x culture x 24 player keys, so
# the head / popularity / uniform picks, the number rounds and the per-player case variants are all pinned
drawn = []
if Nm.DRAW is not None:
    for st in Nm.STYLES_V2:
        if st == 'default':
            continue
        for cu in (D.CULTURES if st in Nm.CULTURE_STYLES else ['en']):
            for g in list(range(12)) + [977, 4099, 65537, 1 << 20, 3 << 24, 1 << 33, (1 << 40) + 5, (1 << 40) + 77777,
                                         123456789, 987654321, 2 ** 31 - 1, 2 ** 35 + 3]:
                key = K.h64(W.seed, 'nick', g)
                drawn.append([st, cu if st in Nm.CULTURE_STYLES else '*', g, str(key), Nm.drawn(st, cu, key)])
world = dict(model=MODEL, cohortCount=len(W.cohorts), members=W.next_gid, boards=boards, players=players,
             cohorts=cohorts, local=local, names=names, variants=Nm.VARIANTS,
             customWeights=[[st, w] for st, w in Nm.CUSTOM_WEIGHTS])
if Nm.DRAW is not None:              # (the reference fixture keeps its SOC1 shape byte for byte)
    world.update(draw=Nm.DRAW, drawn=drawn, skyLevels=E.SKY_LEVELS, styleSystematic=Pp.STYLE_SYSTEMATIC)
dump('world', world)

# ---------------------------------------------------------------- events
ev = dict(model=MODEL, weekly=[], streak=[], rocket=[], sky=[], pace=[])
WK = M.weekly_cls()
ST = M.streak_cls()
for n, (t0, ref, seed, wins_before) in enumerate([(ts(2026, 9, 25, 0, 6), 60.0, 12345, ()),
                                                  (ts(2026, 12, 2, 19, 40), 140.0, 777, ((-7200, -5400), (-3600, -1800))),
                                                  (ts(2027, 6, 14, 8, 0), 35.0, 99, ()),
                                                  (ts(2028, 9, 26, 22, 30), 400.0, 2024, ((-9000, -8000),))]):
    wins = [(t0 + a, t0 + b) for (a, b) in wins_before]
    g = WK(W, seed, K.event_week(t0), t0, ref, wins)
    checks = []
    for dt, us, ur in ((3600, 3, t0 + 3000), (86400, 30, t0 + 80000), (6 * 86400, 120, t0 + 5 * 86400), (9 * 86400, 5, t0 + 100)):
        st = g.standings(t0 + dt, us, ur)
        checks.append(dict(dt=dt, userScore=us, userReached=R(float(ur)), rows=[[x[2], -x[0], R(float(x[1]))] for x in st]))
    ev['weekly'].append(dict(t0=t0, ref=R(ref), seed=seed, week=K.event_week(t0), windows=[[a, b] for a, b in wins],
                             members=[W.gid(c, j) for c, j in g.members], arrive=[R(a) for a in g.arrive], base=g.base,
                             checks=checks))
for t0, ref, seed, wins_before in [(ts(2026, 9, 24, 10, 0), 20.0, 12345, ()), (ts(2026, 9, 25, 1, 46), 45.0, 555, ((-3000, -600),)),
                                   (ts(2027, 1, 3, 7, 0), 8.0, 31, ()), (ts(2028, 2, 29, 23, 0), 90.0, 4242, ())]:
    wins = [(t0 + a, t0 + b) for (a, b) in wins_before]
    g = ST(W, seed, K.event_day(t0), t0, ref, wins)
    checks = []
    for dt, us, ur in ((0, 0, t0), (1800, 16, t0 + 1500), (6 * 3600, 400, t0 + 5 * 3600), (26 * 3600, 900, t0 + 7 * 3600)):
        st = g.standings(t0 + dt, us, ur, 'Hsheh')            # the user's name orders equal scores when TIE_BY_NAME
        checks.append(dict(dt=dt, userScore=us, userReached=R(float(ur)), rows=[[x[2], -x[0], R(float(x[1]))] for x in st],
                           scores=[g.member_score(i, t0 + dt) for i in range(len(g.members))]))
    ev['streak'].append(dict(t0=t0, ref=R(ref), seed=seed, day=K.event_day(t0), windows=[[a, b] for a, b in wins],
                             members=[W.gid(c, j) for c, j in g.members], arrive=[R(a) for a in g.arrive], base=g.base,
                             s0=g.s0, q=[R(x) for x in g.q], checks=checks))
for race_id, stage, t0, spw, seed in [(1, 1, ts(2026, 9, 25, 0, 43), 110.0, 12345), (2, 2, ts(2026, 11, 2, 18, 5), 95.0, 12345),
                                      (3, 3, ts(2027, 5, 20, 12, 0), 150.0, 9), (7, 1, ts(2028, 4, 4, 4, 4), 60.0, 77),
                                      (8, 1, ts(2029, 7, 7, 20, 0), 200.0, 5), (4, 1, ts(2026, 9, 25, 9, 15), 110.0, 20260925),
                                      (5, 1, ts(2026, 9, 25, 9, 28), 110.0, 20260925), (6, 1, ts(2026, 9, 25, 9, 44), 110.0, 20260925),
                                      # stages 2-3 at many hours: they pin the sprint window's N/5 scaling (SOC1b mutation m12)
                                      ] + [(20 + k, 2 + k % 2, ts(2026, 9, 25, 0, 30) + k * 7 * 3600 + (k // 4) * 86400, 100.0, 777 + k)
                                           for k in range(16)]:
    rr = E.RocketRace(W, seed, race_id, stage, t0, spw)
    user = [t0 + 90 * k for k in range(1, rr.N + 1)]
    nm1 = user[rr.N - 2]
    ev['rocket'].append(dict(raceId=race_id, stage=stage, t0=t0, spw=R(spw), seed=seed, N=rr.N, end=rr.end,
                             rivals=[W.gid(c, j) for c, j in rr.rivals], base=rr.base, hold=[R(x) for x in rr.hold],
                             delta=[R(x) for x in rr.delta], natural=[None if x is None else R(x) for x in rr.natural],
                             finish=[None if rr.finish_time(i, None) is None else R(rr.finish_time(i, None)) for i in range(4)],
                             finishUser=[None if rr.finish_time(i, nm1) is None else R(rr.finish_time(i, nm1)) for i in range(4)],
                             progress=[[m, [rr.rival_progress(i, t0 + m * 60, None) for i in range(4)],
                                        [rr.rival_progress(i, t0 + m * 60, nm1) for i in range(4)]] for m in (1, 4, 9, 16, 30, 60, 240)],
                             userTimes=user, outcome=list(rr.outcome(user)[:1]) + [R(float(rr.outcome(user)[1]))],
                             outcomeSlow=[rr.outcome([t0 + 1800 * k for k in range(1, rr.N + 1)])[0],
                                          R(float(rr.outcome([t0 + 1800 * k for k in range(1, rr.N + 1)])[1]))]))
for a in range(40):
    sj = E.SkyJump(1000 + a * 7, a, 1 + a % 3)
    ev['sky'].append(dict(seed=1000 + a * 7, attempt=a, stage=1 + a % 3, alive=sj.alive, share=sj.share))
prng = random.Random(9)
for k in range(6):
    t = ts(2026, 10, 1) + k * 5 * 86400
    wins = []
    x = t - 30 * 86400
    while x < t:
        x += prng.choice([30, 60, 95, 130, 400, 1200, 5000, 30000, 86400])
        wins.append((x, 1, True))
    wins = [w for w in wins if w[0] <= t]
    d, s, wk = E.user_pace(wins, t)
    ev['pace'].append(dict(t=t, wins=[w[0] for w in wins], daily=R(d), spw=R(s), weekly=R(wk)))
dump('events', ev)
print('done %.0fs' % (time.time() - t_start))
