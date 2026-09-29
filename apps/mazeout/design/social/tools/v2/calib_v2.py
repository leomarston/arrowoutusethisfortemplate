#!/usr/bin/env python3
"""calib_v2.py — the calibration guards of the v2 world (T6 acceptance, PLAN-P §4.1; social-intl §6.3 item 6) -> JSON.

    python3 design/social/tools/v2/calib_v2.py [OUT.json] [--quick] [--fit-tr] [--weeks launch,age22,age52] [--off M2,...]

1. The phone guards of SocialCalibrationTests (World #1-#7 / #24 / #89 / #132 / #278, Turkey rank at L62 = 455 +- 15 %,
   Turkey #2-#7 within 40 %, the Turkey slope L62-L84, the Streak-board name mix and repeat rate, the Weekly burstiness),
   measured at the SAME WORLD AGE as the phone's shots: the phone saw the original's world on 25 Sep 2026, 150.8 days after
   ITS epoch (27 Apr 2026); v2's world starts 2026-09-07 (M8), so every phone moment is shifted by +19 weeks (DECISION: the
   guards pin the model's shape at a given world age; the calendar date is irrelevant to them).
2. Per-country realism (social-intl §6.3-6), for every country with >= 1,000 players at the start of each reference week
   (launch week Mon 2026-10-05 07:00 UTC = world age 4 weeks; age 22 weeks = the audit's; age 52 weeks):
     dead daytime hours <= 20 / 112   (7 local days x local 08-23, the country's model offset: an hour is dead when no row of
                                       the Country top 100 gained a level during it)
     same-cohort adjacent pairs in the Country top 20 <= 8 / 19    (worst of local 20:00 on the 7 days)
     no equal-gap run > 3 in the Country top 20                    (a run = consecutive equal non-zero level gaps; worst of 7)
     top first name <= 4 % of the first-name rows of the Country top 200 (local 20:00, day 0)
3. --fit-tr: bisection of the TR weight to the phone's 455 at L62 (prints the weight; the table keeps a rounded value).
"""
import os, sys, json, time, math, statistics, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..')))
ARGS = sys.argv[1:]
OFF = []
if '--off' in ARGS:
    OFF = ARGS[ARGS.index('--off') + 1].split(',')
from socialsim import v2 as V2                                                   # noqa: E402
if not os.environ.get('SOC_CALIB_NOAPPLY'):          # ablation.py's v552 baseline imports this module on the shipped model
    V2.apply(OFF)
from socialsim import core as K, population as Pp, names as Nm, data as D, events as E, shipped as SH   # noqa: E402
from datetime import datetime, timezone                                         # noqa: E402

QUICK = '--quick' in ARGS
OUT = next((a for a in ARGS if a.endswith('.json')), None)
SHIFT = V2.WORLD_EPOCH - K.EPOCH if 'M8' not in OFF else 0     # 19 weeks: the phone's world age -> ours
T0 = time.time()


def log(*a):
    print('[%5.0fs]' % (time.time() - T0), *a, flush=True)


def ts(*a):
    return int(datetime(*a, tzinfo=timezone.utc).timestamp())


def trt(h, m, d=25):
    return ts(2026, 9, d, h, m) - 3 * 3600 + SHIFT


PHONE_T = 1790299860 + SHIFT           # 2026-09-25 01:31 UTC (04:31 TRT), shifted to the same world age


def iso_offset(iso):
    rows = [r for r in D.COUNTRY_ROWS if r.iso == iso]
    return max(rows, key=lambda r: r.weight).off


def phone_guards(W):
    res = {}
    top = [W.level(c, j, PHONE_T) for (_, _, c, j) in W.top(PHONE_T, 300)]
    phone = [(1, 14669, 0.10), (2, 13344, 0.15), (3, 13115, 0.15), (4, 12699, 0.15), (5, 12003, 0.15), (6, 11536, 0.15),
             (7, 11386, 0.15), (24, 8400, 0.15), (89, 5154, 0.15), (132, 4300, 0.15), (278, 3096, 0.15)]
    rows = []
    for rank, lv, tol in phone:
        ours = top[rank - 1]
        rel = (ours - lv) / lv
        rows.append(dict(rank=rank, phone=lv, ours=ours, rel=round(rel, 3), tol=tol, ok=abs(rel) <= tol))
    res['world'] = dict(rows=rows, ok=all(r['ok'] for r in rows), joined=W.joined(PHONE_T))
    tr = W.rank_of_level(62, PHONE_T, 'TR')
    trtop = [W.level(c, j, PHONE_T) for (_, _, c, j) in W.top(PHONE_T, 7, 'TR')]
    trp = [10824, 3323, 3193, 2575, 2401, 1604, 1349]
    top_ok = [abs(trtop[k] - trp[k]) / trp[k] <= 0.40 for k in range(1, 7)] if len(trtop) == 7 else [False]
    res['turkey'] = dict(rankL62=tr, phone=455, rel=round((tr - 455) / 455, 3), ok=abs(tr - 455) / 455 <= 0.15,
                         top7=trtop, phoneTop7=trp, top2to7_within40=all(top_ok), joined=W.joined(PHONE_T, 'TR'))
    obs = [(4, 31, 62, 455), (12, 11, 64, 448), (12, 37, 68, 438), (13, 11, 72, 412), (13, 35, 77, 396), (14, 1, 80, 386),
           (14, 17, 84, 375)]
    ours = [W.rank_of_level(L, trt(h, m), 'TR') for (h, m, L, r) in obs]
    slope = (ours[0] - ours[-1]) / 22.0
    res['turkeySlope'] = dict(ranks=ours, phone=[r for (_, _, _, r) in obs], slope=round(slope, 2),
                              ok=all(abs(o - r[3]) / r[3] <= 0.15 for o, r in zip(ours, obs)) and 2.7 <= slope <= 4.6)
    return res


GIVEN = None


def name_class(n):
    """calib_s2.py / SocialCalibrationTests.nameClass (the phone's classifier)."""
    import re
    global GIVEN
    if GIVEN is None:
        GIVEN = set()
        for cu, toks in Nm.data()['cultures'].items():
            for nat, lat in toks:
                GIVEN.add(D.key(nat))
    if re.fullmatch(r'player_[a-z0-9]{7}', n):
        return 'default'
    letters = [ch for ch in n if ch.isalpha()]
    has_digit = any(ch.isdigit() for ch in n)
    humps = sum(1 for a, b in zip(n, n[1:]) if a.islower() and b.isupper())
    if humps >= 1 and not n[:2].isupper():
        return 'camelCase'
    if letters and all(ch.isupper() for ch in letters) and not has_digit and len(letters) >= 3 and '_' not in n:
        return 'allCaps'
    if has_digit or '_' in n:
        return 'digitsLeet'
    if letters and all(ch.islower() for ch in letters):
        return 'lowercase'
    if n[:1].isupper() and all(ch.islower() for ch in letters[1:]):
        return 'firstName' if D.key(n) in GIVEN else 'capitalised'
    return 'other'


def event_guards(W):
    res = {}
    sj = trt(11, 3)
    names = []
    for seed in range(20):
        g = SH.Streak(W, 9000 + seed, K.event_day(sj), sj, 30.0, [])
        names += [W.name(c, j)[0] for (c, j) in g.members]
    n = float(len(names))
    share = lambda f: sum(1 for x in names if f(x)) / n
    cls = collections.Counter(name_class(x) for x in names)
    mix = {k: round(v / n, 3) for k, v in cls.items()}
    dflt = share(lambda x: x.startswith('player_'))
    checks = dict(default=0.08 <= dflt <= 0.26,
                  camel=share(lambda x: any(ch.isupper() for ch in x) and any(ch.isupper() for ch in x[1:]) and any(ch.islower() for ch in x)) > 0.08,
                  lower=share(lambda x: not x.startswith('player_') and all(ch.islower() for ch in x if ch.isalpha()) and any(ch.isalpha() for ch in x)) > 0.05,
                  allcaps=share(lambda x: all(ch.isupper() for ch in x)) > 0.003,
                  firstName=0.08 <= mix.get('firstName', 0) <= 0.22, digits=0.02 < mix.get('digitsLeet', 0) <= 0.12,
                  capitalised=0.20 <= mix.get('capitalised', 0) <= 0.45)
    res['boardNameMix'] = dict(mix=mix, default=round(dflt, 3), checks=checks, ok=all(checks.values()), rows=len(names))
    pairs = rowpairs = with_rep = 0
    for seed in range(100 if not QUICK else 30):
        g = SH.Streak(W, 19000 + seed, K.event_day(sj), sj, 30.0, [])
        cnt = collections.Counter(D.key(W.name(c, j)[0]) for (c, j) in g.members)
        p = sum(m * (m - 1) // 2 for m in cnt.values())
        with_rep += p > 0
        pairs += p
        rowpairs += len(g.members) * (len(g.members) - 1) // 2
    rate = pairs / rowpairs
    res['nameRepeats'] = dict(rate=float('%.3g' % rate), boardsWithRepeat=with_rep, ok=with_rep > 0 and 1.5e-5 <= rate <= 3.2e-3)
    join = trt(3, 6)
    idle = tot = movers = 0
    for seed in range(12):
        g = SH.Weekly(W, 7000 + seed, K.event_week(join), join, 175.0, [])
        for i in range(len(g.members)):
            a = g.member_score(i, join + 3.5 * 3600) or 0
            b = g.member_score(i, join + 9 * 3600) or 0
            c = g.member_score(i, join + 11.2 * 3600) or 0
            tot += 1
            idle += c == a
            movers += b > a
    res['weeklyBurstiness'] = dict(idleShare=round(idle / tot, 3), moversPerGroup=round(movers / 12, 2),
                                   ok=0.30 <= idle / tot <= 0.72 and movers / 12 > 2.0)
    zeros = []
    for seed in range(12):
        g = SH.Streak(W, 9000 + seed, K.event_day(sj), sj, 30.0, [])
        zeros.append(sum(1 for i in range(len(g.members)) if (g.member_score(i, sj + 69 * 60) or 0) == 0))
    med = statistics.median(zeros)
    res['streakZeros69'] = dict(median=med, ok=8 <= med <= 32)
    return res


def first_token(W, c, j):
    """The key of the first name a member's nickname is built on (given / name+suffix / underscore styles), or None."""
    st, _ = W.style_of(c, j)
    if st not in Nm.POPULAR_STYLES:
        return None
    cu = W.culture_of(c, j)
    t = Nm.draw_index(st, cu, K.h64(W.seed, 'nick', W.ident(c, j)))[1]
    d = Nm.data()
    lat = d['mixedTokens'][cu][t] if st == 'mixed' else d['cultures'][cu][t][1]
    return D.key(lat)


def country_week(W, iso, ws, first_name=True):
    off = iso_offset(iso)
    dead = 0
    movers = []
    ladder = []
    runs = []
    for day in range(7):
        for hh in range(8, 24):
            # the local wall clock of the model offset: ws is Monday 07:00 UTC, (ws - 7 h - off) is local Monday 00:00
            t = (ws - 7 * 3600) + day * 86400 + hh * 3600 - off * 60
            tp = W.top(t, 100, iso)
            n = sum(1 for (_, _, c, j) in tp if W.level(c, j, t) > W.level(c, j, t - 3600))
            movers.append(n)
            dead += n == 0
        t20 = (ws - 7 * 3600) + day * 86400 + 20 * 3600 - off * 60
        tp = W.top(t20, 20, iso)
        lv = [W.level(c, j, t20) for (_, _, c, j) in tp]
        ladder.append(sum(1 for a, b in zip(tp, tp[1:]) if a[2].idx == b[2].idx))
        gaps = [a - b for a, b in zip(lv, lv[1:])]
        best = cur = 0
        for k in range(len(gaps)):
            if gaps[k] > 0 and k > 0 and gaps[k] == gaps[k - 1]:
                cur += 1
            else:
                cur = 1 if gaps[k] > 0 else 0
            best = max(best, cur)
        runs.append(best)
    res = dict(deadHours=dead, medianMovers=sorted(movers)[len(movers) // 2], ladderPairsWorst=max(ladder),
               ladderPairs=ladder, equalGapRunWorst=max(runs))
    if first_name:
        t20 = (ws - 7 * 3600) + 20 * 3600 - off * 60
        toks = [first_token(W, c, j) for (_, _, c, j) in W.top(t20, 200, iso)]
        toks = [x for x in toks if x is not None]
        cnt = collections.Counter(toks)
        if toks:
            k1, m = cnt.most_common(1)[0]
            res['firstNameRows'] = len(toks)
            res['topFirstName'] = [k1, m, round(m / len(toks), 3)]
        else:
            res['firstNameRows'] = 0
            res['topFirstName'] = None
    res['okStructure'] = dead <= 20 and max(ladder) <= 8 and max(runs) <= 3
    tf = res.get('topFirstName')
    res['okTopName4pct'] = not first_name or not tf or tf[2] <= 0.04
    # the same statistic for 60-90 people drawn from the REAL first-name frequencies stays <= 5 in 99 % of samples
    # (tools/v2/names_mc.py); the 4 % line fails 72-82 % of such real samples (see calib notes)
    res['okTopNameRealistic'] = not first_name or not tf or tf[1] <= 5
    res['ok'] = res['okStructure'] and res['okTopName4pct']
    return res


def realism(W, label, ws):
    isos = sorted({r.iso for r in D.COUNTRY_ROWS})
    big = [(iso, W.joined(ws, iso)) for iso in isos]
    big = sorted([x for x in big if x[1] >= 1000], key=lambda x: -x[1])
    if QUICK:
        big = big[:8]
    out = {}
    for iso, n in big:
        r = country_week(W, iso, ws)
        r['players'] = n
        out[iso] = r
        tf = r.get('topFirstName') or [None, 0, 0.0]
        log(label, iso, n, 'dead', r['deadHours'], 'ladder', r['ladderPairsWorst'], 'run', r['equalGapRunWorst'],
            'top first name x%d of %d rows (%.1f %%)' % (tf[1], r.get('firstNameRows', 0), 100 * tf[2]),
            'OK' if r['ok'] else 'FAIL' + ('' if r['okStructure'] else ' structure') + ('' if r['okTopName4pct'] else ' name4pct'))
    fails = [iso for iso, r in out.items() if not r['ok']]
    struct = [iso for iso, r in out.items() if not r['okStructure']]
    name4 = [iso for iso, r in out.items() if not r['okTopName4pct']]
    namer = [iso for iso, r in out.items() if not r['okTopNameRealistic']]
    return dict(weekStart=datetime.fromtimestamp(ws, timezone.utc).isoformat(), worldAgeDays=round((ws - W.epoch) / 86400, 1),
                players=W.joined(ws), countries=len(out), fails=fails, ok=not fails, structureFails=struct,
                topName4pctFails=name4, topNameRealisticFails=namer, byCountry=out)


def draw_probs(n):
    """P(first-name index t) of names.draw_index for a list of n names (the v2 draw, M7), exactly as the hash draw does it:
    headP x min(n, 300) // 300 % over the H = max(1, min(headN, n // 6)) first names, else tailUniformP % uniform over the
    list and the rest floor(n u^2) (P(t < k) = sqrt(k / n))."""
    Dw = Nm.DRAW
    if Dw.get('headScaled'):
        H = max(1, min(Dw['headN'], n // 6))
        hp = (Dw['headP'] * min(n, 300) // 300) / 100.0
        tu = Dw['tailUniformP'] / 100.0
    else:
        H = min(Dw['headN'], n)
        hp = Dw['headP'] / 100.0
        tu = 0.0
    p = [0.0] * n
    for i in range(H):
        p[i] += hp / H
    for i in range(n):
        p[i] += (1.0 - hp) * (tu / n + (1.0 - tu) * (math.sqrt((i + 1) / n) - math.sqrt(i / n)))
    return p


def expected_top_name():
    """Per country: the EXPECTED share of its most common first name among its first-name rows (given / name+suffix /
    underscore styles, weighted by the style mix and the rows' culture mixes). This is the draw's own concentration, free
    of the sampling noise of one board (social-intl P1-1 argued with it: 10.6 % for a 39-name list vs ~2 % for 'en')."""
    d = Nm.data()
    w_style = {st: w for st, w in Nm.CUSTOM_WEIGHTS if st in Nm.POPULAR_STYLES}
    tot_w = sum(w_style.values())
    cache = {}

    def dist(cu):
        if cu not in cache:
            out = collections.Counter()
            for st, w in w_style.items():
                toks = d['mixedTokens'][cu] if st == 'mixed' else [t[1] for t in d['cultures'][cu]]
                for t, q in enumerate(draw_probs(len(toks))):
                    out[D.key(toks[t])] += w / tot_w * q
            cache[cu] = out
        return cache[cu]
    res = {}
    by_iso = collections.defaultdict(list)
    for r in D.COUNTRY_ROWS:
        by_iso[r.iso].append(r)
    for iso, rows in sorted(by_iso.items()):
        wsum = sum(r.weight for r in rows)
        agg = collections.Counter()
        for r in rows:
            mt = sum(w for _, w in r.mix)
            for cu, w in r.mix:
                for k, q in dist(cu).items():
                    agg[k] += r.weight / wsum * w / mt * q
        res[iso] = round(max(agg.values()), 4)
    return res


def regions_check():
    """Every Locale.Region.isoRegions code (data_v2/ios_regions.tsv, from Foundation on the build Mac) resolves to a board:
    a table row, an alias of a row, or a UN M.49 numeric region's representative row (M3)."""
    codes = []
    for l in open(os.path.join(D.DATA_V2, 'ios_regions.tsv'), encoding='utf-8'):
        if l.strip() and not l.startswith('#'):
            codes.append(l.split('\t')[0])
    row_isos = {r.iso for r in D.COUNTRY_ROWS}
    kinds = collections.Counter()
    unresolved = []
    for c in codes:
        kind, iso = D.resolve_region(c)
        kinds[kind] += 1
        if kind == 'unknown' or iso not in row_isos:
            unresolved.append(c)
    return dict(codes=len(codes), kinds=dict(kinds), rows=len(D.COUNTRY_ROWS), countries=len(row_isos),
                unresolved=unresolved, ok=not unresolved and len(codes) >= 280)


def fit_tr():
    """Bisection of TR's weight: rank at L62 at the phone's world age -> 455."""
    lo, hi = 0.05, 1.5
    hist = []
    for it in range(14):
        w = (lo + hi) / 2
        for r in D.COUNTRY_ROWS:
            if r.iso == 'TR':
                r.weight = w
        Pp.refresh_tables()
        W = Pp.World()
        W.extend_to(PHONE_T + 86400)
        rk = W.rank_of_level(62, PHONE_T, 'TR')
        hist.append((round(w, 4), rk))
        log('TR weight', round(w, 4), 'rank', rk)
        if rk < 455:
            lo = w
        else:
            hi = w
    return hist


def main():
    if '--fit-tr' in ARGS:
        print(json.dumps(fit_tr()))
        return
    res = dict(model='v2', off=OFF, shift_days=SHIFT / 86400, when=time.strftime('%Y-%m-%d %H:%M:%S'),
               trWeight=[r.weight for r in D.COUNTRY_ROWS if r.iso == 'TR'])
    weeks = dict(launch=ts(2026, 10, 5, 7), age22=V2.WORLD_EPOCH + 22 * K.WEEK, age52=V2.WORLD_EPOCH + 52 * K.WEEK)
    sel = ARGS[ARGS.index('--weeks') + 1].split(',') if '--weeks' in ARGS else list(weeks)
    W = Pp.World()
    W.extend_to(max([PHONE_T + 10 * 86400] + [weeks[k] + 8 * 86400 for k in sel]))
    log('world built', len(W.cohorts), 'cohorts')
    res['regions'] = regions_check()
    log('regions', json.dumps({k: v for k, v in res['regions'].items() if k != 'unresolved'}))
    res['expectedTopFirstName'] = expected_top_name()
    log('expected top first-name share: max %.4f' % max(res['expectedTopFirstName'].values()))
    res['phone'] = phone_guards(W)
    log('phone', json.dumps({k: v.get('ok') for k, v in res['phone'].items()}), 'TR', res['phone']['turkey']['rankL62'])
    res['events'] = event_guards(W)
    log('events', json.dumps({k: v.get('ok') for k, v in res['events'].items()}))
    res['realism'] = {}
    for k in sel:
        res['realism'][k] = realism(W, k, weeks[k])
    res['ok'] = (all(v.get('ok') for v in res['phone'].values()) and all(v.get('ok') for v in res['events'].values())
                 and all(v['ok'] for v in res['realism'].values()) and res['regions']['ok'])
    # the T6 acceptance (PLAN-P row T6 SOC-PY), one line each
    acc = {}
    real = res['realism']
    acc['countriesEvaluated'] = {k: v['countries'] for k, v in real.items()}
    acc['deadHoursLe20'] = {k: [iso for iso, r in v['byCountry'].items() if r['deadHours'] > 20] for k, v in real.items()}
    acc['ladderPairsLe8'] = {k: [iso for iso, r in v['byCountry'].items() if r['ladderPairsWorst'] > 8] for k, v in real.items()}
    acc['equalGapRunLe3'] = {k: [iso for iso, r in v['byCountry'].items() if r['equalGapRunWorst'] > 3] for k, v in real.items()}
    acc['topFirstNameLe4pct'] = {k: v['topName4pctFails'] for k, v in real.items()}
    acc['topFirstNameLe5rows'] = {k: v['topNameRealisticFails'] for k, v in real.items()}
    acc['expectedTopFirstNameLe4pct'] = [iso for iso, x in res['expectedTopFirstName'].items() if x > 0.04]
    acc['turkeyRankL62'] = dict(ours=res['phone']['turkey']['rankL62'], phone=455, rel=res['phone']['turkey']['rel'],
                                ok=res['phone']['turkey']['ok'])
    acc['isoRegionsResolve'] = res['regions']['ok']
    acc['structureOk'] = all(not x for d in (acc['deadHoursLe20'], acc['ladderPairsLe8'], acc['equalGapRunLe3']) for x in d.values())
    acc['topFirstNameLe4pctOk'] = all(not x for x in acc['topFirstNameLe4pct'].values())
    res['acceptance'] = acc
    res['seconds'] = round(time.time() - T0)
    if OUT:
        os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
        with open(OUT, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(dict(acceptance=res['acceptance'], ok=res['ok'], phone={k: v.get('ok') for k, v in res['phone'].items()},
                          events={k: v.get('ok') for k, v in res['events'].items()},
                          realism={k: dict(ok=v['ok'], countries=v['countries'], structureFails=v['structureFails'],
                                           topName4pctFails=v['topName4pctFails'], topNameRealisticFails=v['topNameRealisticFails'])
                                   for k, v in res['realism'].items()}), indent=1))


if __name__ == '__main__':
    main()
