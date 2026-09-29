#!/usr/bin/env python3
"""calib_s2.py — every observable of phone session 2 (research/social-dynamics.md, 25 Sep 2026) measured on one parameter
set of the offline world, so the calibration can be read as a before/after table.

    python3 design/social/tools/calib_s2.py v552 build/soc1b/calib-after.json [--quick]
    ... [--soc1]    the 'before' column of SOC1b (SOC1's shipped parameters)
    ... [--soc1b]   the 'before' column of SOC1c (SOC1b's shipped parameters: unique names, Sky Jump 5/7/9)

The model is selected through Packages/PathCore/Tests/tools/soc_model.py (the same switch the fixtures use). Everything
here only READS the model; the numbers it prints are the ones quoted in design/SPEC-social.md §14 and build/soc1b.
Phone times are Europe/Istanbul (UTC+3); the model runs in UTC.
"""
import os, sys, json, re, time, statistics
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(APP, 'Packages', 'PathCore', 'Tests', 'tools'))
import soc_model as M                                                         # noqa: E402
MODEL = sys.argv[1] if len(sys.argv) > 1 else 'v552'
OUT = sys.argv[2] if len(sys.argv) > 2 else None
QUICK = '--quick' in sys.argv
SOC1 = '--soc1' in sys.argv          # the 'before' column: SOC1's shipped parameters (25 Sep 11:27)
from socialsim import shipped as SH                                           # noqa: E402
if SOC1:
    for k in list(SH.ARCH):
        for key in ('custom', 'honey', 'sess'):
            SH.ARCH[k].pop(key, None)
    SH.ARCH = {k: v for k, v in SH.ARCH.items() if v}
    SH.WEIGHTS = {'TR': 0.5}
    from socialsim import names as _N
    SH.CUSTOM_WEIGHTS = _N.CUSTOM_WEIGHTS; SH.VARIANTS = None
    SH.WEEKLY_BANDS = [(1, 1.10, 1.80, True), (2, 0.90, 1.20, True), (2, 0.65, 0.90, True), (2, 0.40, 0.65, True),
                       (2, 0.08, 0.40, False)]
    SH.STREAK_BANDS = [(5, 1.00, 1.80, True), (10, 0.75, 1.00, True), (14, 0.50, 0.75, True), (12, 0.25, 0.50, True),
                       (8, 0.02, 0.25, False)]
    SH.STREAK_AT_JOIN = False; SH.STREAK_MATCH = None; SH.STREAK_TIE_BY_NAME = False; SH.STREAK_FAIL_Q = (0.06, 0.24)
    SH.ROCKET_ROLES = ['hot', 'hot', 'warm', 'idle']; SH.ROCKET_HOLDS = {r: (14.0, 40.0) for r in SH.ROCKET_ROLES}
    SH.SKY_DROPS = None
    SH.DRAW = None; SH.SKY_LEVELS = [5, 7, 9]; SH.STYLE_SYSTEMATIC = False
SOC1B = '--soc1b' in sys.argv        # the 'before' column of SOC1c: SOC1b's shipped names (unique first-come slots), Sky 5/7/9
if SOC1B:
    SH.CUSTOM_WEIGHTS = [('given', 0.12), ('word', 0.01), ('compound', 0.20), ('invented', 0.28), ('caps', 0.02),
                         ('underscore', 0.005), ('initials', 0.005), ('mixed', 0.33), ('leet', 0.03)]
    SH.VARIANTS = dict(inventedLower=45, inventedUpper=8, givenUpper=8, compoundDigits=35, mixedLower=25)
    SH.DRAW = None
    SH.STYLE_SYSTEMATIC = False     # SOC1b's per-cohort style rounding (the reference's)
    SH.SKY_LEVELS = [5, 7, 9]
    SH.SKY_DROPS = [(10.0, 16.0, 1, 5, 10), (11.0, 14.0, 2, 12, 18), (7.5, 10.0, 2, 14, 24)]
M.use(MODEL)
from socialsim import core as K, population as Pp, names as Nm, events as E, data as D   # noqa: E402
from datetime import datetime, timezone                                      # noqa: E402


def trt(h, m, d=25):
    """Europe/Istanbul wall clock on Sep <d> 2026 -> UTC seconds."""
    return int(datetime(2026, 9, d, h, m, tzinfo=timezone.utc).timestamp()) - 3 * 3600


T0 = time.time()
W = Pp.World()
W.extend_to(trt(23, 0) + 9 * 86400)
res = dict(model=MODEL)


def log(*a):
    print('[%5.0fs]' % (time.time() - T0), *a, flush=True)


# ------------------------------------------------------------------ name styles (the phone's ~113 names, same classifier)
GIVEN = set()
for cu, toks in Nm.data()['cultures'].items():
    for nat, fol in toks:
        GIVEN.add(D.key(nat))
OBSERVED = dict(
    weekly=['Guy', 'player_qqpvpjp', 'LoudRat', 'SneakyFalconer51', 'ChillKnight71', 'MagicGoose', 'Ttam', 'Boo', 'Mema'],
    world=['player_ah8prp7', 'Winner', 'ezbee', 'Tetety', 'Sunshine', 'Limminator', 'Crazzijj', 'Han', 'Bobby', 'Caco17',
           'Neil', 'Debbie', 'SweetiePie', 'Alex56k', 'Bobby', 'Wilbert', 'Joe', 'Stacx251', 'Ptr', 'Negona', 'Arrowcrusher',
           'player_s4emvud', 'Longy'],
    turkey=['Mrmş', 'Namnam', 'Dug', 'Hakki', 'player_g5r28yh', 'Seyhan', 'Ayba', 'Cxddds', 'Anan', 'Berkay', 'Kurtville',
            'player_7zcs7no', 'xdxdxd', 'turko', 'rng', 'Gulyabani', 'player_8jgl4qr', 'ecr', 'mern', 'cey'],
    streak=['player_0k30dg3', 'Hana', 'mort', 'Raikouhou', 'OKTOBERFEST', 'vidboy120', 'freedom', 'bennysnaps', 'LazyDragon',
            'ASLAN', '0xBK', 'yasemin', 'Pjr', 'L8M', 'player_wot5mkn', 'Ginger', 'sha256mechanic', 'BrightHawk', 'serkan',
            'player_7gv2330', 'Miguel', 'Linda', 'Elke', 'oddgull', 'ANADOLU', 'Sezzy', 'Papa', 'GoldenWitch56',
            'player_4bmn1kj', 'Gii', 'niamh', 'player_l3z5twc', 'Babs', 'ChillRat', 'Henri', 'K710', 'karl', 'KernowCat',
            'Lesley', 'Lol', 'Marlou', 'player_270hbzd', 'player_2nbw6lp', 'player_cxxmndk', 'player_i5z8uwy', 'QueenK',
            'Sarah', 'SleepyMoose', 'TheRedUnicorn'],
    rocket=['Emilia', 'quints375', 'Elo', 'DER', 'Tin', 'doost', 'Truth', 'player_nvbfr9z', 'Lol', 'Incog', 'Caz', 'ned'],
)
CATS = ['default', 'firstName', 'capitalised', 'lowercase', 'camelCase', 'allCaps', 'digitsLeet', 'other']


def classify(n):
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


def mix(names):
    c = {k: 0 for k in CATS}
    for n in names:
        c[classify(n)] += 1
    tot = max(1, len(names))
    return dict(n=len(names), share={k: round(v / tot, 3) for k, v in c.items()})


def dups(boards):
    """Duplicate nicknames INSIDE a board (case/accent-insensitive key): boards with at least one repeated name, and
    pairs per 100 rows (a name met m times on one board = m(m-1)/2 pairs). Identity is the gid; this is only the display."""
    nb = len(boards); with_dup = 0; pairs = 0; rows = 0; row_pairs = 0; examples = []
    for b in boards:
        cnt = {}
        for nm in b:
            k = D.key(nm)
            cnt[k] = cnt.get(k, 0) + 1
        p = sum(m * (m - 1) // 2 for m in cnt.values())
        if p:
            with_dup += 1
            if len(examples) < 8:
                examples.append(sorted({nm for nm in b if cnt[D.key(nm)] > 1}))
        pairs += p; rows += len(b); row_pairs += len(b) * (len(b) - 1) // 2
    return dict(boards=nb, rows=rows, boardsWithDup=with_dup, shareBoardsWithDup=round(with_dup / max(1, nb), 3),
                pairsPer100Rows=round(100.0 * pairs / max(1, rows), 3), pairs=pairs, rowPairs=row_pairs,
                pairRate=float('%.3g' % (pairs / max(1, row_pairs))), examples=examples)


obs_all = [n for v in OBSERVED.values() for n in v]
res['names_observed'] = dict(pooled=mix(obs_all), **{k: mix(v) for k, v in OBSERVED.items()})
# the phone's boards (World top 23, Turkey ~20, Weekly 9, Streak Race 49, Rocket 12 = one board each here): one repeated
# name, the two "Bobby" of the World top 15
res['dups_observed'] = dict(pooled=dups(list(OBSERVED.values())), **{k: dups([v]) for k, v in OBSERVED.items()})

# ------------------------------------------------------------------ World top 23 (12:09 → 14:01 TRT) and the 7.6 h before
tA, tB, tC = trt(4, 31), trt(12, 9), trt(14, 1)
top = W.top(tB, 23)
res['world'] = dict(
    phone=dict(top23=[14730, 13349, 13154, 12699, 12003, 11536, 11529, 11125, 10969, 10839, 10721, 10651, 10294, 10165,
                      10069, 9681, 9457, 9209, 9075, 8793, 8499, 8499, 8480],
               static15_1h52=9, gains15_1h52=[66, 40, 4, 4, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0], wilbert_per_h=41,
               gains_7h38=[143, 61, 39, 15, 5, 0, 0, 0]),
    ours=dict(top23=[W.level(c, j, tB) for (_, _, c, j) in top]))
g15 = sorted([W.level(c, j, tC) - W.level(c, j, tB) for (_, _, c, j) in top[:15]], reverse=True)
g8 = sorted([W.level(c, j, tB) - W.level(c, j, tA) for (_, _, c, j) in W.top(tA, 8)], reverse=True)
res['world']['ours'].update(static15_1h52=sum(1 for g in g15 if g == 0), gains15_1h52=g15, gains8_7h38=g8,
                            names=[W.name(c, j)[0] for (_, _, c, j) in top])
# the same window on 60 other days / hours (the moment on the phone is one sample)
st_counts, maxg = [], []
boards_world = [res['world']['ours']['names']]
for k in range(0 if QUICK else 60):
    t1 = trt(12, 9) - 3 * 86400 + k * 5 * 3600 + 1234
    boards_world.append([W.name(c, j)[0] for (_, _, c, j) in W.top(t1, 23)])
    tp = W.top(t1, 15)
    gg = [W.level(c, j, t1 + 6720) - W.level(c, j, t1) for (_, _, c, j) in tp]
    st_counts.append(sum(1 for g in gg if g == 0))
    maxg.append(max(gg))
if st_counts:
    res['world']['ours']['static15_1h52_over60windows'] = dict(median=statistics.median(st_counts), min=min(st_counts),
                                                            max=max(st_counts), maxGainMedian=statistics.median(maxg),
                                                            maxGainMax=max(maxg))
log('world', res['world']['ours']['top23'][:8], 'static', res['world']['ours']['static15_1h52'], g15[:5])

# ------------------------------------------------------------------ Turkey: rank slope L62..L84 and the top 7
tr_obs = [(trt(4, 31), 62, 455), (trt(12, 11), 64, 448), (trt(12, 37), 68, 438), (trt(13, 11), 72, 412),
          (trt(13, 35), 77, 396), (trt(14, 1), 80, 386), (trt(14, 17), 84, 375)]
ours = [(L, W.rank_of_level(L, t, 'TR')) for (t, L, _) in tr_obs]
slope_o = (tr_obs[0][2] - tr_obs[-1][2]) / (tr_obs[-1][1] - tr_obs[0][1])
slope_m = (ours[0][1] - ours[-1][1]) / (tr_obs[-1][1] - tr_obs[0][1])
# the density alone (same moment): players per level between L62 and L84 at 12:00 TRT
tm = trt(12, 0)
dens = (W.rank_of_level(62, tm, 'TR') - W.rank_of_level(84, tm, 'TR')) / 22.0
trtop = W.top(trt(12, 11), 7, 'TR')
ab, be = W.neighbours(64, trt(12, 11), 5, 5, 'TR')
res['turkey'] = dict(phone=dict(ranks=[[L, r] for (_, L, r) in tr_obs], slope=round(slope_o, 2),
                                top7=[10841, 3323, 3193, 2575, 2401, 1609, 1349]),
                     ours=dict(ranks=[[L, r] for (L, r) in ours], slope=round(slope_m, 2), densityPerLevel=round(dens, 2),
                               top7=[W.level(c, j, trt(12, 11)) for (_, _, c, j) in trtop],
                               top7names=[W.name(c, j)[0] for (_, _, c, j) in trtop],
                               aroundL64=[W.name(c, j)[0] for (_, _, c, j) in list(reversed(ab)) + be]))
boards_turkey = [[W.name(c, j)[0] for (_, _, c, j) in W.top(trt(12, 11) - 3 * 86400 + k * 5 * 3600, 20, 'TR')]
                 for k in range(4 if QUICK else 40)]
log('turkey', res['turkey']['ours'])

# ------------------------------------------------------------------ Weekly Contest group (joined Fri 03:06 TRT = the phone's)
# The phone's player (the runner's bot) won ~35 levels a day; SocialPace's first-week reference for that pace is
# 5 x 35 = 175 (weekly levels). The phone's group is ONE sample at one hour, so the same join is also measured at 8 hours
# of the day. Windows are relative to the join: +85 min (04:31 TRT), +3.5 h -> +9 h (06:39 -> 12:08), +9 h -> +11.2 h
# (12:08 -> 14:17), static = no level from +3.5 h to +11.2 h. `shares` = each rival's part of the group's progress in the
# first 11.2 h (the phone player is a bot about twice as fast as a ref-175 player, so shapes compare better than totals).
WK = M.weekly_cls()
join = trt(3, 6)
wk_obs = dict(top85=27, leader_3h30_9h=45, movers_3h30_9h=5, movers_9h_11h12=1, static_3h30_11h12=round(4 / 9, 2),
              at11h12=[79, 47, 29, 28, 23, 23, 19, 6, 4],
              shares11h12=[round(x / 258, 3) for x in [79, 47, 29, 28, 23, 23, 19, 6, 4]])
names_w = []
boards_w = []
def weekly_rows(joins, ns, ref):
    rows = []
    for jn in joins:
        for s in range(ns):
            g = WK(W, 7000 + s, K.event_week(jn), jn, ref, [])
            sc = lambda i, t: g.member_score(i, t) or 0
            idx = range(len(g.members))
            at11 = sorted([sc(i, jn + 11.2 * 3600) for i in idx], reverse=True)
            rows.append(dict(top85=max(sc(i, jn + 85 * 60) for i in idx),
                             g1=sorted([sc(i, jn + 9 * 3600) - sc(i, jn + 3.5 * 3600) for i in idx], reverse=True),
                             g2=sum(1 for i in idx if sc(i, jn + 11.2 * 3600) > sc(i, jn + 9 * 3600)),
                             static=sum(1 for i in idx if sc(i, jn + 11.2 * 3600) == sc(i, jn + 3.5 * 3600)),
                             at11=at11, shares=[x / max(1, sum(at11)) for x in at11]))
            if jn == join:
                names_w.extend(W.name(c, j)[0] for (c, j) in g.members)
                boards_w.append([W.name(c, j)[0] for (c, j) in g.members] + ['Hsheh'])
    med = statistics.median
    return dict(groups=len(rows), top85=med(r['top85'] for r in rows), leader_3h30_9h=med(r['g1'][0] for r in rows),
                movers_3h30_9h=round(statistics.mean(sum(1 for x in r['g1'] if x > 0) for r in rows), 2),
                movers_9h_11h12=round(statistics.mean(r['g2'] for r in rows), 2),
                static_3h30_11h12=round(statistics.mean(r['static'] for r in rows) / 9, 2),
                at11h12=[med(r['at11'][k] for r in rows) for k in range(9)],
                shares11h12=[round(statistics.mean(r['shares'][k] for r in rows), 3) for k in range(9)])
res['weekly'] = dict(phone=wk_obs, ref=175.0,
                     ours=dict(phoneHour=weekly_rows([join], 8 if QUICK else 40, 175.0),
                               allHours=weekly_rows([join + h * 3 * 3600 + 86400 for h in range(8)], 1 if QUICK else 5, 175.0),
                               phoneHour_ref90=weekly_rows([join], 8 if QUICK else 20, 90.0)))
log('weekly', res['weekly']['ours']['phoneHour'])

# ------------------------------------------------------------------ Streak Race (50 rows; the phone joined at ~11:03 TRT)
# Relative to the join: +69 min (12:12), +97 min (12:40), +3 h (14:03); the player's daily reference 30 (the bot won
# ~35 levels on its active days). Also measured at 6 other join hours.
ST = M.streak_cls()
sj = trt(11, 3)
st_obs = dict(atJoin='all 49 rivals at 0, listed alphabetically', top69=1941, zeros69=17, zeros3h=11,
              top3gain_97m_3h=[111, 82, 0], static_69m_3h=0.47, top6_97m=[4081, 3551, 3445, 2052, 1941, 1692],
              top6_3h=[4081, 3633, 3556, 2082, 1941, 1723])
names_s = []
boards_s = []
def streak_rows(joins, ns):
    rows = []
    for jn in joins:
        for s in range(ns):
            g = ST(W, 9000 + s, K.event_day(jn), jn, 30.0, [])
            sc = lambda i, t: g.member_score(i, t) or 0
            idx = range(len(g.members))
            at = lambda t: sorted([sc(i, t) for i in idx], reverse=True)
            a69 = at(jn + 69 * 60)
            by = sorted(idx, key=lambda i: -sc(i, jn + 97 * 60))
            rows.append(dict(zj=sum(1 for x in at(jn) if x == 0), top69=a69[0], z69=sum(1 for x in a69 if x == 0),
                             z3h=sum(1 for x in at(jn + 3 * 3600) if x == 0),
                             g3=sorted([sc(i, jn + 3 * 3600) - sc(i, jn + 97 * 60) for i in by[:3]], reverse=True),
                             static=sum(1 for i in idx if sc(i, jn + 3 * 3600) == sc(i, jn + 69 * 60)),
                             a97=at(jn + 97 * 60)[:6], a3h=at(jn + 3 * 3600)[:6]))
            if jn == sj:
                names_s.extend(W.name(c, j)[0] for (c, j) in g.members)
                boards_s.append([W.name(c, j)[0] for (c, j) in g.members] + ['Hsheh'])
    med = statistics.median
    return dict(races=len(rows), zerosAtJoin=med(r['zj'] for r in rows), top69=med(r['top69'] for r in rows),
                zeros69=med(r['z69'] for r in rows), zeros3h=med(r['z3h'] for r in rows),
                top3gain_97m_3h=[med(r['g3'][k] for r in rows) for k in range(3)],
                static_69m_3h=round(statistics.mean(r['static'] for r in rows) / 49, 2),
                top6_97m=[med(r['a97'][k] for r in rows) for k in range(6)], top6_3h=[med(r['a3h'][k] for r in rows) for k in range(6)])
g0 = ST(W, 9000, K.event_day(sj), sj, 30.0, [])
tie = g0.standings(sj, 0, float(sj), 'Hsheh') if hasattr(g0, 'standings_by_name') else None
res['streak'] = dict(phone=st_obs, ref=30.0,
                     ours=dict(phoneHour=streak_rows([sj], 3 if QUICK else 12),
                               allHours=streak_rows([sj + h * 3 * 3600 + 86400 for h in range(6)], 1 if QUICK else 3),
                               tiesAtJoin=[('Hsheh' if i < 0 else W.name(*g0.members[i])[0]) for (_, _, i) in tie][:12] if tie else None))
log('streak', res['streak']['ours']['phoneHour'])
# more Streak Race boards at the phone's join, names only (the duplicate-name rate needs many independent boards)
boards_s_more = []
for s_ in range(20 if QUICK else 150):
    g_ = ST(W, 19000 + s_, K.event_day(sj), sj, 30.0, [])
    boards_s_more.append([W.name(c, j)[0] for (c, j) in g_.members] + ['Hsheh'])
log('streak boards for names', len(boards_s_more))

# ------------------------------------------------------------------ Rocket Race (joins 12:15, 12:28, 12:44 TRT + S1 03:43)
names_r = []
boards_r = []
joins = [trt(12, 15), trt(12, 28), trt(12, 44), trt(3, 43)]
rocket = dict()
for stage in (1, 2, 3):
    rk = []
    for k in range(12 if QUICK else 60):
        t0 = joins[k % 4] + (k // 4) * 5400 + (86400 if stage > 1 else 0)
        rr = E.RocketRace(W, 5000 + k, k + 1, stage, t0, 110.0)
        fin = [rr.finish_time(i, None) for i in range(4)]
        first = min([f for f in fin if f is not None], default=None)
        others = sorted([rr.rival_progress(i, first - 1, None) for i in range(4)], reverse=True)[1:] if first else None
        pl = lambda spl: [t0 + spl * (q + 1) for q in range(rr.N)]
        rk.append(dict(first=None if first is None else (first - t0) / 60, others=others, h90=rr.outcome(pl(90))[0],
                       h120=rr.outcome(pl(120))[0], h180=rr.outcome(pl(180))[0], h360=rr.outcome(pl(360))[0]))
        if stage == 1:
            names_r.extend(W.name(c, j)[0] for (c, j) in rr.rivals)
            boards_r.append([W.name(c, j)[0] for (c, j) in rr.rivals] + ['Hsheh'])
    fins = [r['first'] for r in rk if r['first'] is not None]
    win = lambda key: round(sum(1 for r in rk if r[key] == 'win') / len(rk), 2)
    rocket['stage%d' % stage] = dict(races=len(rk), firstFinishMin_q1_med_q3=[round(x, 1) for x in statistics.quantiles(fins, n=4)],
                                     noFinisher=len(rk) - len(fins),
                                     othersAtFinish=[statistics.median(r['others'][q] for r in rk if r['others']) for q in range(3)],
                                     humanWin_1m30=win('h90'), humanWin_2m=win('h120'), humanWin_3m=win('h180'), humanWin_6m=win('h360'))
res['rocket'] = dict(phone=dict(firstFinishMin=[6, 8, 19, '15-20 (S1)'], othersAtFinish=[[3, 2, 1], [3, 1, 1], [4, 3, 1]],
                                player='lost 4 of 4 at ~5-7 min a level'), ours=rocket)
log('rocket', rocket['stage1'])

# ------------------------------------------------------------------ Sky Jump
sk = {1: [], 2: [], 3: []}
for a in range(300):
    for stage in (1, 2, 3):
        s = E.SkyJump(4242 + a, a, stage)
        sk[stage].append(s)
def drops(s):
    return [s.alive[k - 1] - s.alive[k] for k in range(1, s.N)]
res['sky'] = dict(phone=dict(stage1=[100, 82, 64, None, 47, 7], stage2=[100, 100, 88, 75, 62, 49, 36, 15],
                             stage3_first6=[100, 100, 91, 82, 74, 65, 57],
                             stage3=[100, 100, 91, 83, 75, 66, 57, 48, 40, 32, 7], share2=466, share3=1428, levels=[5, 7, 10]),
                  ours={('stage%d' % st): dict(example=sk[st][0].alive, drop_per_level_median=statistics.median(
                      d for s in sk[st] for d in drops(s)[1:]), first_drop_median=statistics.median(drops(s)[0] for s in sk[st]),
                      winners_median=statistics.median(s.alive[-1] for s in sk[st]),
                      winners_range=[min(s.alive[-1] for s in sk[st]), max(s.alive[-1] for s in sk[st])],
                      share_median=statistics.median(s.share for s in sk[st]), levels=sk[st][0].N) for st in (1, 2, 3)})
log('sky', res['sky']['ours'])

# ------------------------------------------------------------------ calendar (reset times)
res['calendar'] = dict(phone=dict(weekly_ends='Mon 28 Sep ~09:00-10:00 TRT', streak_rocket_end='10:00 TRT daily',
                                  sky='24 h from the join'),
                       ours=dict(weekly_ends_utc=datetime.fromtimestamp(K.event_week_start(K.event_week(trt(12, 8)) + 1),
                                                                        timezone.utc).isoformat(),
                                 day_ends_utc=datetime.fromtimestamp(K.event_day_start(K.event_day(trt(12, 12)) + 1),
                                                                     timezone.utc).isoformat()))

# ------------------------------------------------------------------ names on the same boards
res['names_ours'] = dict(world=mix(res['world']['ours']['names']),
                         turkey=mix(res['turkey']['ours']['top7names'] + res['turkey']['ours']['aroundL64']),
                         weekly=mix(names_w), streak=mix(names_s), rocket=mix(names_r),
                         pooled=mix(res['world']['ours']['names'] + res['turkey']['ours']['top7names']
                                    + res['turkey']['ours']['aroundL64'] + names_w + names_s + names_r))
res['dups_ours'] = dict(world=dups(boards_world), turkey=dups(boards_turkey), weekly=dups(boards_w),
                       streak=dups(boards_s + boards_s_more), rocket=dups(boards_r),
                       pooled=dups(boards_world + boards_turkey + boards_w + boards_s + boards_s_more + boards_r))
# the chance that two names met anywhere match (60k different non-tourist players, custom + default names, uniform over players)
_rng = __import__('random').Random(5)
_cs = [c for c in W.cohorts if c.n > 0 and Pp.ARCH[c.a]['key'] != 'tourist' and c.join0 - c.span < trt(12, 0)]
_cum = []; _acc = 0
for c in _cs:
    _acc += c.n; _cum.append(_acc)
import bisect
_cnt = {}
_N = 12000 if QUICK else 60000
_seen = set()
while len(_seen) < _N:                  # 60k DIFFERENT players (a player met twice is not a repeated name)
    x = _rng.randrange(_acc)
    ci = bisect.bisect_right(_cum, x); c = _cs[ci]; j = x - (_cum[ci] - c.n)
    if (ci, j) in _seen:
        continue
    _seen.add((ci, j))
    k = D.key(W.name(c, j)[0])
    _cnt[k] = _cnt.get(k, 0) + 1
res['dups_ours']['anyTwoNames'] = dict(sample=_N, pairRate=float('%.3g' % (sum(m * (m - 1) for m in _cnt.values()) / (_N * (_N - 1)))),
                                      mostCommon=sorted(_cnt.items(), key=lambda kv: -kv[1])[:10])
# SOC1c: nickname style shares by cohort size (the per-cohort count rounding, population.STYLE_SYSTEMATIC) and on the World
# top 100 at 12:09 (the World top is made of small cohorts: the reference rounding over-weighted the LAST style, 'leet')
_tb = trt(12, 9)
_bk = {}
for c in W.cohorts:
    if c.n <= 0 or c.join0 > _tb:
        continue
    d = _bk.setdefault('n<10' if c.n < 10 else 'n<50' if c.n < 50 else 'n>=50', {})
    for st, lo, hi in c.style_cum:
        if st != 'default':
            d[st] = d.get(st, 0) + hi - lo
_top = W.top(_tb, 100)
_ts = {}
for (_, _, c, j) in _top:
    _ts[W.name(c, j)[1]] = _ts.get(W.name(c, j)[1], 0) + 1
res['styles_ours'] = dict(
    weights={st: w for st, w in Nm.CUSTOM_WEIGHTS}, systematic=bool(getattr(Pp, 'STYLE_SYSTEMATIC', False)),
    byCohortSize={b: dict(custom=sum(d.values()), share={st: round(d.get(st, 0) / max(1, sum(d.values())), 3) for st, _ in Nm.CUSTOM_WEIGHTS})
                  for b, d in sorted(_bk.items())},
    worldTop100=_ts, worldTop15=[W.name(c, j)[0] for (_, _, c, j) in _top[:15]])
log('styles', json.dumps(res['styles_ours'], ensure_ascii=False))
log('names', json.dumps({k: v['share'] for k, v in res['names_ours'].items()}))
log('dups', json.dumps({k: {q: v.get(q) for q in ('boards', 'boardsWithDup', 'pairs', 'rowPairs', 'pairRate', 'mostCommon')}
                        for k, v in res['dups_ours'].items()}, ensure_ascii=False))
log('dups observed', json.dumps({k: {q: v[q] for q in ('boards', 'boardsWithDup', 'pairs', 'rowPairs', 'pairRate')}
                                 for k, v in res['dups_observed'].items()}))
log('names observed', json.dumps({k: v['share'] for k, v in res['names_observed'].items()}))
res['seconds'] = round(time.time() - T0)
if OUT:
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
    log('wrote', OUT)
