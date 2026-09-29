#!/usr/bin/env python3
"""fixtures_v2.py — the golden vectors of the v2 world for B2's Swift port (bit for bit, Debug and -O).

Writes into a STAGING folder (default build/p/T6/fixtures_v2/, never Packages/**: B2 copies them to
Packages/PathCore/Tests/Fixtures when it lands the Swift port):
  soc_v2_world.json, soc_v2_events.json  the SAME schema as soc_v552_* (Packages/PathCore/Tests/tools/soc_fixtures.py is run
                                         unmodified on the v2 model; its board times are moved by +19 weeks = the same world
                                         ages, since v2's world starts 2026-09-07)
  soc_v2_intl.json                       the v2-only sections (social-intl §6.3 item 7): 40 cohorts' blocks, per-member
                                         cultures, native / Latin draws per culture, the region map (every isoRegions code),
                                         two LOCAL codes, shards, member lags, the M11 row tilt, country boards for 12 countries
    python3 design/social/tools/v2/fixtures_v2.py [OUTDIR]
B2's soc_model.py needs one more branch: use('v2') -> `from socialsim import v2; v2.apply()`.
"""
import os, sys, json, time, random
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, '..'))
APP = os.path.normpath(os.path.join(TOOLS, '..', '..', '..'))
PKG_TOOLS = os.path.join(APP, 'Packages', 'PathCore', 'Tests', 'tools')
sys.path.insert(0, TOOLS)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(APP, 'build', 'p', 'T6', 'fixtures_v2')
os.makedirs(OUT, exist_ok=True)

from socialsim import v2 as V2                                                  # noqa: E402
V2.apply()
from socialsim import core as K, population as Pp, names as Nm, data as D, events as E   # noqa: E402

SHIFT = V2.WORLD_EPOCH - K.EPOCH
R = repr


def main():
    t0 = time.time()
    # ---------------------------------------------------------------- 1. soc_fixtures.py, unmodified logic, model v2
    src = open(os.path.join(PKG_TOOLS, 'soc_fixtures.py'), encoding='utf-8').read()
    reps = [("import soc_model as M                                    # noqa: E402  (must precede the socialsim imports)",
             "import soc_model as M\nM.MODEL = 'v552'   # soc_model's class switch: the shipped Weekly / Streak classes"),
            ("MODEL = sys.argv[1] if len(sys.argv) > 1 else 'v552'\nM.use(MODEL)", "MODEL = 'v2'"),
            ("OUT = os.path.normpath(os.path.join(HERE, '..', 'Fixtures'))", "OUT = %r" % OUT),
            ("HERE = os.path.dirname(os.path.abspath(__file__))", "HERE = %r" % PKG_TOOLS),
            ("W = Pp.World()\nW.extend_to(TIMES[-1] + 2 * 86400)",
             "TIMES = [x + %d for x in TIMES]\nW = Pp.World()\nW.extend_to(TIMES[-1] + 2 * 86400)" % SHIFT)]
    for a, b in reps:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    # soc_model.weekly_cls / streak_cls pick the shipped classes when MODEL != 'reference'
    g = {'__name__': '__soc_fixtures_v2__', '__file__': os.path.join(PKG_TOOLS, 'soc_fixtures.py')}
    sys.argv = ['soc_fixtures.py', 'v2']
    exec(compile(src, 'soc_fixtures.py(v2)', 'exec'), g)
    W = g['W']
    # ---------------------------------------------------------------- 2. the v2-only sections
    T = K.event_week_start(K.event_week(V2.WORLD_EPOCH + 30 * K.WEEK)) + 5 * 3600 + 1234
    W.extend_to(T + 9 * 86400)
    rng = random.Random(2002)
    shared = [c for c in W.cohorts if not c.local and c.n > 0 and c.join0 - c.span < T]
    pick = shared[:12] + [shared[i] for i in sorted(rng.sample(range(12, len(shared)), 28))]
    blocks = []
    for c in pick:
        rows = Pp.BUCKET_ROWS[D.BUCKETS[c.b]]
        blocks.append(dict(idx=c.idx, ck=c.ck, p=c.p, b=c.b, a=c.a, day=c.day, n=c.n, gid0=c.gid0, off=c.off,
                           v=R(c.v), pace=R(c.pace),
                           blocks=[[rows[ri].iso, s0, e0] for (ri, s0, e0) in c.blocks],
                           members=[[j, R(W.u_of(c, j)), R(W.lag(c, j)), W.iso_of(c, j), W.culture_of(c, j),
                                     W.name(c, j)[0], W.name(c, j)[1], W.avatar(c, j, W.name(c, j)[1]), W.level(c, j, T)]
                                    for j in sorted(j for j in {0, 1, c.n // 3, c.n // 2, c.n - 2, c.n - 1} if 0 <= j < c.n)]))
    draws = []
    for cu in D.CULTURES:
        toks = Nm.data()['cultures'].get(cu, [])
        if not toks:
            continue
        for st in ('given', 'mixed', 'underscore'):
            for gk in (0, 1, 7, 977, 65537, 1 << 33, (1 << 40) + 5, 987654321):
                key = K.h64(W.seed, 'nick', gk)
                draws.append([st, cu, gk, str(key), list(Nm.draw_index(st, cu, key)), Nm.drawn(st, cu, key)])
        for i in (0, 1, len(toks) // 2, len(toks) - 1):
            for vr in (0, 1, 2, 3, 5, 8, 13, 21):
                draws.append(['given-build', cu, i, vr, Nm.build('given', i, 0, cu, vr=vr)])
    boards = []
    for iso in ('US', 'TR', 'SK', 'SI', 'JP', 'KR', 'CN', 'BE', 'CH', 'CA', 'IS', 'NZ'):
        for t in (T - 20 * 86400, T):
            ab, be = W.neighbours(62, t, 6, 6, iso)
            boards.append(dict(iso=iso, t=t, joined=W.joined(t, iso), rank62=W.rank_of_level(62, t, iso),
                               top=[[g2, R(P)] for (P, g2, _, _) in W.top(t, 15, iso)],
                               above=[g2 for (_, g2, _, _) in ab], below=[g2 for (_, g2, _, _) in be],
                               rows=[[W.gid(c, j), W.name(c, j)[0], W.iso_of(c, j), W.level(c, j, t)] for (_, _, c, j) in W.top(t, 5, iso)]))
    local = []
    for code in ('ZZ', 'XA'):
        WL, iso = V2.world_for_home(code)
        WL.extend_to(T)
        lc = [c for c in WL.cohorts if c.local and c.n > 0][:10]
        local.append(dict(code=code, cohortCount=len(WL.cohorts),
                          cohorts=[[c.idx, c.ck, c.gid0, c.n, c.salt] + [WL.name(c, j)[0] for j in range(min(3, c.n))]
                                   + [WL.level(c, c.n - 1, T)] for c in lc],
                          joined=WL.joined(T, code), rank62=WL.rank_of_level(62, T, code),
                          top=[[g2, R(P)] for (P, g2, _, _) in WL.top(T, 10, code)]))
    shards = [[c.idx, c.ck, c.p, c.b, c.a, c.n] for c in W.cohorts if c.p == 1 and c.b == D.BUCKETS.index('EUR_C')]
    intl = dict(model='v2', t=T, worldEpoch=V2.WORLD_EPOCH, strata=Pp.COUNTRY_STRATA, shardTarget=Pp.SHARD_TARGET,
                lagMin=Pp.MEMBER_LAG_MIN, rowTilt=Pp.ROW_TILT, nativeT=Nm.NATIVE_T, kanaP=Nm.KANA_P, draw=Nm.DRAW, cultures=D.CULTURES,
                buckets=[[b, D.BUCKET_OFF[b]] for b in D.BUCKETS],
                countries=[[r.iso, r.weight, r.off, [[cu, w] for cu, w in r.mix], r.bucket] for r in D.COUNTRY_ROWS],
                regions={k: list(v) for k, v in sorted(D.REGION.items())},
                blocks=blocks, draws=draws, boards=boards, local=local, shardsEURC1=shards,
                cohortCount=len(W.cohorts), members=W.next_gid)
    path = os.path.join(OUT, 'soc_v2_intl.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(intl, f, ensure_ascii=False, indent=None, separators=(',', ':'))
    print('wrote', path, os.path.getsize(path), 'bytes; total %.0fs' % (time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
