#!/usr/bin/env python3
"""Property tests of the social-simulation reference (the Swift SocialTests mirror these one to one).
    python3 design/social/tools/tests.py            # the prototype ('reference'), ~1 min, prints PASS/FAIL per test
    python3 design/social/tools/tests.py v552       # the same properties on the shipped model (socialsim/shipped.py)
    python3 design/social/tools/tests.py v2         # the v2 world (socialsim/v2.py: M1-M8) + the v2-only checks 15-22
"""
import os, sys, random, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
MODEL = sys.argv[1] if len(sys.argv) > 1 else 'reference'
from socialsim import shipped as SH
if MODEL == 'v552':
    SH.apply()
elif MODEL == 'v2':
    from socialsim import v2 as V2
    V2.apply([a[5:] for a in sys.argv if a.startswith('--off')])   # --offM2 etc. (ablations)
SHIPPED = MODEL in ('v552', 'v2')
from socialsim import core as K, population as Pp, names as Nm, events as E, data as D
from socialsim.clock import SocialClock
from datetime import datetime, timezone

def ts(*a):
    return int(datetime(*a, tzinfo=timezone.utc).timestamp())

RESULTS = []
def check(name, ok, detail=''):
    RESULTS.append((name, ok))
    print(('PASS ' if ok else 'FAIL ') + name + ('  ' + detail if detail else ''), flush=True)

T_NOW = ts(2026, 9, 25, 1, 0) if MODEL != 'v2' else ts(2026, 12, 25, 1, 0)   # v2's world starts 2026-09-07
W = Pp.World(); W.extend_to(T_NOW + 8 * 86400)
rng = random.Random(42)

# 1. perm is a bijection and perm_inv inverts it
ok = True
for n in (1, 2, 3, 7, 64, 100, 1000, 4097):
    key = K.h64(1, 'p', n)
    img = [K.perm(x, n, key) for x in range(n)]
    ok &= sorted(img) == list(range(n))
    ok &= all(K.perm_inv(K.perm(x, n, key), n, key) == x for x in range(0, n, max(1, n // 50)))
check('perm bijection + inverse', ok)

# 2. members are sorted by level inside every cohort (monotone in u) at random times
bad = 0; n_checks = 0
live = [c for c in W.cohorts if c.n > 1 and c.join0 - c.span < T_NOW]
for _ in range(400):
    c = rng.choice(live)
    t = rng.uniform(c.join0 - c.span, T_NOW)
    prev = -1.0
    for j in range(0, c.n, max(1, c.n // 30)):
        P = W.progress(c, j, t)
        P = -1.0 if P is None else P
        n_checks += 1
        if P < prev - 1e-9:
            bad += 1
        prev = P
check('level monotone in u inside cohorts', bad == 0, '%d checks' % n_checks)

# 3. a member's progress never decreases with time
bad = 0; n_checks = 0
for _ in range(300):
    c = rng.choice(live); j = rng.randrange(c.n)
    times = sorted(rng.uniform(c.join0 - c.span, T_NOW) for _ in range(40))
    prev = -1.0
    for t in times:
        P = W.progress(c, j, t)
        P = -1.0 if P is None else P
        n_checks += 1
        if P < prev - 1e-9:
            bad += 1
        prev = P
check('progress non-decreasing in time', bad == 0, '%d checks' % n_checks)

# 4. continuity across local midnight (no jump at the day boundary)
worst = 0.0
for _ in range(300):
    c = rng.choice(live); j = rng.randrange(c.n)
    u, lam, J, T1, F, T2 = W.member(c, j)
    t = rng.uniform(J, T_NOW)
    dl, minute = K.local_day_minute(t, c.off)
    mid = (dl + 1) * 86400 - c.off * 60
    a = W.progress(c, j, mid - 0.001); b = W.progress(c, j, mid)
    if a is not None and b is not None:
        worst = max(worst, b - a)
check('continuous at local midnight', worst < 0.01, 'max jump %.2e levels' % worst)

# 5. session windows are ordered, non-overlapping, inside the day, and the max member uses its full quota
bad = 0
for _ in range(500):
    c = rng.choice(live); dl = rng.randrange(0, 200)
    s = W.sessions(c, dl)
    if not s:
        continue
    starts, f, pace, m = s
    L = [fj * c.lam_max * m / pace for fj in f]
    for k in range(len(starts)):
        if starts[k] < 0 or starts[k] + L[k] > 1439.0 + 1e-6:
            bad += 1
        if k and starts[k] < starts[k - 1] + L[k - 1] + D.SESSION_GAP - 1e-6:
            bad += 1
    if abs(sum(f) - 1.0) > 1e-12:
        bad += 1
check('session windows valid', bad == 0)

# 6. count_ge (per-cohort binary search) == brute force, for a country and random times/levels
bad = 0
iso_cohorts = [c for c in W.cohorts if c.iso == 'TR' and c.join0 - c.span < T_NOW]
if Pp.COUNTRY_BLOCKS:     # v2 (M1): a cohort's members belong to several countries — brute force over the members
    iso_members = [(c, j) for c in W.cohorts if c.join0 - c.span < T_NOW for j in range(c.n) if W.iso_of(c, j) == 'TR']
else:
    iso_members = [(c, j) for c in iso_cohorts for j in range(c.n)]
for _ in range(12):
    t = rng.uniform(T_NOW - 60 * 86400, T_NOW)
    x = rng.choice([2, 5, 11, 30, 56, 120, 400, 1500])
    brute = sum(1 for (c, j) in iso_members if W.level(c, j, t) >= x)
    if brute != W.count_ge(x, t, 'TR'):
        bad += 1
check('count_ge equals brute force (TR)', bad == 0)

# 7. top-k equals brute force (TR) and is sorted
t = T_NOW - 3 * 86400
allp = []
for (c, j) in iso_members:
        P = W.progress(c, j, t)
        if P is not None:
            allp.append((P, W.gid(c, j)))
allp.sort(key=lambda x: (-x[0], x[1]))
tk = W.top(t, 50, 'TR')
check('top-k equals brute force (TR)', [g for (_, g, _, _) in tk] == [g for (_, g) in allp[:50]])

# 8. neighbours: above rows are all > user level, below rows <= user level, ranks consistent with count_ge
bad = 0
for x in (3, 12, 40, 90, 300):
    ab, be = W.neighbours(x, t, 10, 10, 'TR')
    R = W.rank_of_level(x, t, 'TR')
    lv_above = [W.level(c, j, t) for (_, _, c, j) in ab]
    lv_below = [W.level(c, j, t) for (_, _, c, j) in be]
    if any(l <= x for l in lv_above) or any(l > x for l in lv_below):
        bad += 1
    if lv_above != sorted(lv_above) or lv_below != sorted(lv_below, reverse=True):
        bad += 1
    # the player just above the user is exactly the R-1 th player in the brute order
    if ab and allp:
        want = [g for (P, g) in allp if 1 + math.floor(P) >= x + 1]
        if want and want[-1] != ab[0][1]:
            bad += 1
check('neighbours consistent with rank', bad == 0)

# 9. the reference: no two players share a nickname in a sample of 60k shared-world players (case/accent-insensitive).
#    The shipped model (names.DRAW, SOC1c) draws names with replacement like the original (two "Bobby" in its World
#    top 15): names repeat, the player's identity is its gid; the chance that two names met on a board match must sit in
#    the phone's range (1 repeated pair in 1,721 row pairs of its boards: 95 % CI 1.5e-5 .. 3.2e-3).
seen = {}; dup = 0; blocked = 0; n = 0; toolong = 0; gids = set()
for c in W.cohorts[:1500]:
    for j in range(c.n):
        nm, st = W.name(c, j)
        k = D.key(nm)
        if k in seen:
            dup += 1
        seen[k] = seen.get(k, 0) + 1
        gids.add(W.gid(c, j))
        n += 1
        if st != 'fallback' and Nm.is_blocked(nm):
            blocked += 1
        if SHIPPED and len(nm) > SH.MAX_NAME:
            toolong += 1
    if n > 60000:
        break
if Nm.DRAW is None:
    check('nicknames unique (60k players)', dup == 0, '%d names' % n)
else:
    # board-like rows: the non-tourist players (tourists never reach a board and keep player_ names)
    board = {}
    for c in W.cohorts[:1500]:
        if Pp.ARCH[c.a]['key'] == 'tourist':
            continue
        for j in range(c.n):
            k = D.key(W.name(c, j)[0]); board[k] = board.get(k, 0) + 1
    nb = sum(board.values())
    q = sum(m * (m - 1) for m in board.values()) / (nb * (nb - 1))
    check('nicknames drawn: repeats at the phone\'s rate, identity = gid', 1.5e-5 <= q <= 3.2e-3 and len(gids) == n,
          '%d names, %d repeats; board-like pair rate %.2e over %d rows' % (n, dup, q, nb))
check('no blocked nickname shown', blocked == 0)
check('no nickname longer than the username rule', toolong == 0)

# 9b. every 'player_' name comes from one bijection with disjoint slot ranges (shared, LOCAL, user, fallbacks)
names_seen = set(); ok = True
for base, step in ((0, 1), (Nm.LOCAL_DEFAULT_BASE, 1), (Nm.USER_DEFAULT_BASE, 7919), (Nm.D36_7 - 80000, 1)):
    for i in range(20000):
        nm = Nm.default_name(base + i * step, 0)
        ok &= nm not in names_seen and len(nm) == 14 and nm.startswith('player_')
        names_seen.add(nm)
check('default names: one bijection, disjoint ranges', ok)

# 10. the shared world does not depend on the install: a LOCAL partition leaves the shared names/levels untouched
W2 = Pp.World(local=('IS', 0, 'nordic') if MODEL != 'v2' else ('ZZ', 0, 'en')); W2.extend_to(T_NOW)
same = True
for c in W.cohorts[:800]:
    if c.p > W2.periods - 1:
        break
    c2 = [q for q in W2.cohorts if q.ck == c.ck and not q.local][0]
    if c2.n != c.n or c2.gid0 != c.gid0:
        same = False; break
    j = c.n // 2 if c.n else 0
    if c.n and (W.name(c, j) != W2.name(c2, j) or W.level(c, j, T_NOW) != W2.level(c2, j, T_NOW)):
        same = False; break
check('LOCAL partition leaves the shared world identical', same)

# 11. Sky Jump: players count never increases, winners in range, share = pool // winners
ok = True
for a in range(300):
    stage = 1 + a % 3
    sj = E.SkyJump(99, a, stage)
    wlo, whi = (3, 12) if E.SKY_DROPS is None else E.SKY_DROPS[stage - 1][3:5]
    ok &= all(x >= y for x, y in zip(sj.alive, sj.alive[1:])) and wlo <= sj.alive[-1] <= whi and sj.share == sj.pool // sj.alive[-1]
    if E.SKY_DROPS is not None:        # shipped: 8-16 drop per level from the stage's first step, none before it
        lo, hi, first = E.SKY_DROPS[stage - 1][:3]
        d = [sj.alive[k - 1] - sj.alive[k] for k in range(1, sj.N)]
        ok &= all(x == 0 for x in d[:first - 1]) and all(int(lo) - 1 <= x <= int(hi) + 2 for x in d[first - 1:])
check('Sky Jump survivor curve', ok)

# 12. Rocket Race: displayed rival progress is monotone in time and a rival's finish never moves into the past
ok = True
for a in range(20):
    t0 = T_NOW - rng.uniform(0, 20) * 86400
    rr = E.RocketRace(W, 5, a, 1, t0, 110.0)
    for i in range(4):
        prev = -1
        for m in range(0, 240, 3):
            p = rr.rival_progress(i, t0 + m * 60, None)
            ok &= p >= prev; prev = p
    # user reaches N-1 later -> a finish time <= that moment must not change
    f_before = [rr.finish_time(i, None) for i in range(4)]
    un = t0 + 1800
    f_after = [rr.finish_time(i, un) for i in range(4)]
    for fb, fa in zip(f_before, f_after):
        if fb is not None and fb <= un:
            ok &= fa == fb
check('Rocket Race progress monotone + past-stable', ok)

# 12b. group contests: member scores monotone in time, standings sorted and contain the user exactly once,
#      the group grows over the window (arrivals) and never shrinks
ok = True
W.extend_to(T_NOW + 9 * 86400)
WK, STK = (SH.Weekly, SH.Streak) if SHIPPED else (E.WeeklyContest, E.StreakRace)
SIZES = {WK: 10 if SHIPPED else E.WEEKLY_GROUP, STK: 50 if SHIPPED else E.STREAK_GROUP}
for cls, ref in ((WK, 90.0), (STK, 15.0)):
    for inst in range(3):
        t0 = T_NOW - inst * 2 * 86400 - 3600 * 5
        if cls is WK:
            g = cls(W, 11 + inst, K.event_week(t0), t0, ref)
        else:
            g = cls(W, 11 + inst, K.event_day(t0), t0, ref)
        prev_rows = 0
        prev_scores = [None] * len(g.members)
        for h in range(0, int((g.we - t0) / 3600) + 1, 3):
            t = t0 + h * 3600
            st = g.standings(t, 0, t0, 'Hsheh')
            ok &= sum(1 for x in st if x[2] < 0) == 1
            if g.TIE_BY_NAME:          # score desc, then the name key ascending (phone: ties listed alphabetically)
                keys = [(x[0], D.key('Hsheh' if x[2] < 0 else W.name(*g.members[x[2]])[0])) for x in st]
                ok &= keys == sorted(keys)
            else:
                ok &= [(x[0], x[1]) for x in st] == sorted((x[0], x[1]) for x in st)
            ok &= len(st) >= prev_rows; prev_rows = len(st)
            for i in range(len(g.members)):
                sc = g.member_score(i, t)
                if prev_scores[i] is not None:
                    ok &= sc is not None and sc >= prev_scores[i]
                prev_scores[i] = sc
        ok &= len(g.members) == SIZES[cls] - 1
check('group contests: monotone scores, sorted standings, growing groups', ok)

# 12c. clock set back: displayed levels never decrease; a >30-day repair rebases exactly once
clk = SocialClock(); ok = True
players = [(c, c.n // 2) for c in live[::97] if c.n][:40]
prev = {}
seq = [T_NOW - 5 * 3600, T_NOW - 4 * 3600, T_NOW - 7 * 3600, T_NOW - 6 * 3600, T_NOW - 3 * 3600, T_NOW - 3 * 86400, T_NOW]
for dev in seq:
    t = clk.now(dev)
    for c, j in players:
        L = W.level(c, j, t)
        ok &= L >= prev.get((c.idx, j), 0)
        prev[(c.idx, j)] = L
clk2 = SocialClock(T_NOW + 400 * 86400); t2 = clk2.now(T_NOW)
ok &= clk.rebased == 0 and clk2.rebased == 1 and t2 == T_NOW
check('clock set back never rewinds; far-future repair rebases once', ok)

# 13. Streak multiplier ladder
s = E.Streak(); pts = [s.win() for _ in range(7)]; s.fail(); pts.append(s.win())
check('streak ladder 1,5,10,25,100,100,100 then reset', pts == [1, 5, 10, 25, 100, 100, 100, 1])

# 14. event calendar: day starts 07:00 UTC, weeks start Monday 07:00 UTC
d = K.event_day(ts(2026, 9, 25, 6, 59, 59)); d2 = K.event_day(ts(2026, 9, 25, 7, 0, 0))
w1 = K.event_week(ts(2026, 9, 28, 6, 59)); w2 = K.event_week(ts(2026, 9, 28, 7, 0))
check('event day/week boundaries', d2 == d + 1 and w2 == w1 + 1 and datetime.fromtimestamp(K.event_week_start(w2), timezone.utc).weekday() == 0)

if MODEL == 'v2':
    import tests_v2
    tests_v2.run(W, T_NOW, check, rng)

print('\n[%s] %d/%d passed' % (MODEL, sum(1 for _, ok in RESULTS if ok), len(RESULTS)))
