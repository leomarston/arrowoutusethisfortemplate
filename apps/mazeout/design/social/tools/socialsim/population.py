# socialsim/population.py — the simulated world of Arrow Out players (reference for PathCore/Social/Population).
#
# The world is identical on every device: it is derived from WORLD_SEED only (the install seed never touches it), so two
# friends comparing phones see the same World / Country boards at the same moment.
#
# Structure. Players join in COHORTS. A cohort = (join period p [a week from EPOCH], timezone bucket, archetype[, join day]).
# Tourists (short-lived) get one cohort per join DAY, every other archetype one per join WEEK. Each cohort has one country
# (picked from its bucket by weight), hence one culture (names) and one UTC offset (diurnal rhythm), one daily-volume
# pattern and one daily session schedule shared by all its members ("they play at the same hours").
# Members j = 0..n-1 sit at quantiles u_j = (j + v_c) / n. Every member parameter is a monotone function of u:
#   higher u -> joins earlier, plays more per day (lam), stays longer (life), bigger install session (first).
# Because a higher-u member's active interval CONTAINS a lower-u member's and it plays at least as much in every session,
# level(u, t) is non-decreasing in u at every t (proved in SPEC-social.md §3.3). So inside a cohort the members are
# always sorted by j, and "how many players are at level >= x" is a binary search per cohort (O(C log n), never O(N)).
import math
from .core import (h64, u01, below, interp, perm, floordiv, posmod, fl, round_half_up, EPOCH, DAY, WEEK, M,
                   local_day_minute, dow_of_local_day)
from . import data as D
from . import names as Nm

WORLD_SEED = 0x41524F57204F5554        # "AROW OUT" — the one shared world (never per install)
BASE_DAY = 20552                        # a local day number that is a multiple of PATTERN (28): 734 * 28
MINUTES = 1440.0
LOCAL_SHARE = 0.003
# Per-cohort nickname-style counts. False (the reference): each style's count is rounded on its own and clipped by what
# is left, and the LAST style takes the remainder — in a small cohort that remainder is several times the style's weight
# (with 'leet' last: ~10 % of the names in cohorts under 10 players instead of 3 %, and the World top is made of such
# cohorts). True (shipped, SOC1c): systematic apportionment — one offset u per cohort, count_i = floor(C * W_i + u) -
# floor(C * W_(i-1) + u) over the cumulative weights W — so every style's expected count is exactly C * w_i at every
# cohort size, the counts always sum to C and nothing is clipped.
STYLE_SYSTEMATIC = False

# ---------------------------------------------------------------- v2 switches (design/publish/social-intl.md §6; all OFF here)
# socialsim/v2.py turns them on. With every switch off this module is the reference / v552 byte for byte (the fixtures prove it).
# M1 COUNTRY_BLOCKS: a shared cohort no longer has ONE country. Its n members are split into contiguous index blocks, one per
#    row of its bucket, sized by systematic apportionment of the row weights (one offset u per cohort, label 'cblk') in a
#    per-cohort hashed row order (label 'cord'). A member's country (and culture) is its block's row. Sessions, levels and ids
#    do not depend on the blocks; country queries run over (cohort, block) units.
COUNTRY_BLOCKS = False
# M1 strata: the member range is first cut into COUNTRY_STRATA equal strata (z_k = floor(k n / S)) and the rows are
#    apportioned inside EVERY stratum (offset 'cblk' and row order 'cord' keyed by the stratum), so a country's members are
#    spread over the whole quantile range of a cohort instead of one contiguous slice: its level distribution follows the
#    cohort's, and a cohort feeds a country's top with one small block, not a run of neighbours. 1 = the audit's prototype.
COUNTRY_STRATA = 1
# M2 U_JITTER: stratified quantile jitter, u_j = (j + u01(S,'uj',ck,j)) / n instead of (j + v) / n. u stays increasing in j,
#    so containment, monotonicity and the per-cohort binary search stay exact; the evenly spaced "ladders" disappear.
U_JITTER = False
# M4 LOCAL_V2: the device-only LOCAL partition (only for a region code that no table row / alias knows) is keyed by its ISO:
#    the cohort keys and the per-member name/avatar keys are salted with the 16-bit code, so two unknown regions never share
#    a skeleton. Its offset/culture come from the caller (v2: the static default, never the device).
LOCAL_V2 = False
# M5 MEMBER_CULTURE: a member's name culture is drawn from its row's culture mix (label 'mcul' on the member's id).
MEMBER_CULTURE = False
# M8 WORLD_EPOCH: the world's own epoch (join period 0); None = core.EPOCH. The event calendar keeps core.EPOCH.
WORLD_EPOCH = None
# M9 SHARD_TARGET: a weekly cohort (p, b, a) of E expected players is split into s = max(1, floor(E / T + 0.5)) independent
#    cohorts (own size dither, pace, volume pattern, sessions, quantile offsets: key ck + (k << 24)), so a young world's
#    boards are not made of a few huge lockstep groups. T is one number or {archetype key: T} (a missing key: no split).
#    None = one cohort (reference / v552).
SHARD_TARGET = None
# M9 MIN_SHARDS: {archetype key: k} — a weekly cohort of that archetype is split into at least k shards even when its bucket is
#    small (a band of few players otherwise plays on 1-2 session schedules per archetype and its countries' boards have
#    dead hours). None / a missing key = no minimum. Only used together with SHARD_TARGET.
MIN_SHARDS = None
# M10 MEMBER_LAG_MIN: member j lives on its cohort's clock delayed by lag(u) = LAG x (1 - u) minutes (the top member not at
#    all). Progress Q(u, t) = P(u, t - lag(u)) stays non-decreasing in t and in u (P is non-decreasing in both and lag is
#    non-increasing in u), so containment and the binary search stay exact; a cohort's members no longer level up in the
#    same minute. 0 = off.
MEMBER_LAG_MIN = 0
# M11 ROW_TILT: {iso: {archetype key: factor}} — inside M1's block apportionment a row weighs weight x factor for cohorts of
#    that archetype (a missing iso / key: 1). It changes WHICH country a member belongs to, never a level or an id, so the
#    World board is untouched; a country's archetype mix leans away from the bucket's. v2 uses it for Turkey only, fitted to
#    the phone's Turkey board (tools/v2/fit_tr.py). None = off.
ROW_TILT = None

ARCH = D.ARCHETYPES
N_ARCH = len(ARCH)
WEEKLY_ARCH = [i for i, a in enumerate(ARCH) if not a['daily']]
DAILY_ARCH = [i for i, a in enumerate(ARCH) if a['daily']]
IDX_RETURNER = D.ARCH_KEYS.index('returner')

def _check_containment():
    """SPEC-social §2.5: every life table must rise by at least the cohort's join spread per unit of u, so that a higher-u
    member's active interval contains every lower-u member's (=> level monotone in u => binary search is exact)."""
    for a in ARCH:
        span = 1.0 if a['daily'] else 7.0
        xs, ys = a['life']
        for i in range(1, len(xs)):
            slope = (ys[i] - ys[i - 1]) / (xs[i] - xs[i - 1])
            assert slope >= span, (a['key'], slope, span)
        for key in ('lam', 'first', 'lapse', 'life2'):
            if key in a:
                v = a[key]
                ys2 = v[1] if isinstance(v[0], list) else list(v)
                assert all(ys2[i] <= ys2[i + 1] for i in range(len(ys2) - 1)), (a['key'], key)
_check_containment()

def _bucket_rows():
    rows = {b: [] for b in D.BUCKETS}
    for r in D.COUNTRY_ROWS:
        rows[r.bucket].append(r)
    return rows
BUCKET_ROWS = _bucket_rows()
TOTAL_W = sum(r.weight for r in D.COUNTRY_ROWS)
BUCKET_SHARE = [sum(r.weight for r in BUCKET_ROWS[b]) / TOTAL_W for b in D.BUCKETS]

def refresh_tables():
    """Recompute the bucket tables after the country table changed (shipped.apply, v2.apply)."""
    global BUCKET_ROWS, TOTAL_W, BUCKET_SHARE
    BUCKET_ROWS = _bucket_rows()
    TOTAL_W = sum(r.weight for r in D.COUNTRY_ROWS)
    BUCKET_SHARE = [sum(r.weight for r in BUCKET_ROWS[b]) / TOTAL_W for b in D.BUCKETS]

def iso16(iso):
    """A 2-letter region code as a 16-bit integer (the LOCAL salt, M4)."""
    return (ord(iso[0]) << 8) | ord(iso[1])

class Cohort:
    __slots__ = ('idx', 'ck', 'p', 'b', 'a', 'day', 'n', 'gid0', 'iso', 'culture', 'off', 'v', 'pace', 'lam_max',
                 'm', 'pre', 'T', 'ml', 'prel', 'Tl', 'join0', 'span', 'R', 'style_cum', 'style_base', 'local', 'final_frozen_at',
                 'hb', 'hE', 'hDL', 'blocks', 'salt')
    # blocks (M1): [(row index in the bucket or -1 for LOCAL, s, e)] contiguous member ranges, e - s > 0, in index order;
    #   None when the cohort has one country (reference / v552). salt (M4): XOR-ed into a LOCAL member's name/avatar id.
    # join0: time of the latest possible join (u=0 member) = start of the join window + span; members join at
    # join0 - u * span (u=1 joins first).

def cohort_key(p, b, a, day):
    return ((p * 16 + b) * 16 + a) * 8 + (day + 1)

class World:
    """Cohort table + member model. `local` = (iso, off_min, culture) of a home country missing from the table
    (then a device-only LOCAL partition exists); None for every country in countries.tsv."""
    def __init__(self, seed=WORLD_SEED, local=None):
        self.seed = seed
        self.epoch = EPOCH if WORLD_EPOCH is None else WORLD_EPOCH
        self.units = {}                     # M1: iso -> [(cohort idx, s, e)] in cohort order
        self.cohorts = []
        self.periods = 0                    # number of complete join periods materialised
        self.style_count = {}               # (style, culture) -> next free slot   (shared world)
        self.local = local
        self.local_style_count = {}
        self._sess_cache = {}
        self.next_gid = 0
        self.next_local_gid = 1 << 40

    # ------------------------------------------------------------- building
    def extend_to(self, t):
        pmax = floordiv(int(t) - self.epoch, WEEK)
        while self.periods <= pmax:
            self._add_period(self.periods)
            self.periods += 1

    def _add_period(self, p):
        S = self.seed
        J = D.weekly_joins(p)
        parts = list(range(len(D.BUCKETS)))
        if self.local is not None:
            parts.append(len(D.BUCKETS))       # LOCAL partition, after the shared buckets
        for b in parts:
            # the LOCAL partition (only on devices whose country is not in the table) adds 0.3 % ON TOP of the shared
            # world, so the shared buckets stay byte-identical on every device
            share = BUCKET_SHARE[b] if b < len(D.BUCKETS) else LOCAL_SHARE
            for a in WEEKLY_ARCH:
                E = J * share * ARCH[a]['share']
                if SHARD_TARGET is None:
                    self._add_cohort(p, b, a, -1, E)
                else:
                    T = SHARD_TARGET.get(ARCH[a]['key']) if isinstance(SHARD_TARGET, dict) else SHARD_TARGET
                    ns = 1 if not T else max(1, int(fl(E / T + 0.5)))
                    if MIN_SHARDS is not None:
                        ns = max(ns, MIN_SHARDS.get(ARCH[a]['key'], 1))
                    for k in range(ns):
                        self._add_cohort(p, b, a, -1, E / ns, k)
            for day in range(7):
                for a in DAILY_ARCH:
                    self._add_cohort(p, b, a, day, J * share * ARCH[a]['share'] / 7.0)

    def _add_cohort(self, p, b, a, day, expected, shard=0):
        S = self.seed
        c = Cohort()
        c.idx = len(self.cohorts)
        c.ck = cohort_key(p, b, a, day) + (shard << 24)
        c.p = p; c.b = b; c.a = a; c.day = day
        c.local = b >= len(D.BUCKETS)
        c.salt = 0
        c.blocks = None
        if c.local and LOCAL_V2:
            h = iso16(self.local[0])
            c.ck = c.ck ^ (h << 32)             # M4: every LOCAL hash (size, pace, pattern, sessions, styles) keyed by the ISO
            c.salt = h << 44                    # ... and the member name / avatar ids (never the gid: fallbacks stay disjoint)
        c.n = int(fl(expected + u01(S, 'cn', c.ck)))
        if c.local:
            c.iso, c.off, c.culture = self.local
            if COUNTRY_BLOCKS:
                c.blocks = [(-1, 0, c.n)] if c.n > 0 else []
        elif COUNTRY_BLOCKS and D.COUNTRIES_V2:
            # M1 + M3: the members are split over every row of the bucket; the cohort plays on the bucket's schedule offset
            c.iso = None; c.culture = None
            c.off = D.BUCKET_OFF[D.BUCKETS[b]]
            c.blocks = self._blocks(c, BUCKET_ROWS[D.BUCKETS[b]])
        else:
            rows = BUCKET_ROWS[D.BUCKETS[b]]
            tot = sum(r.weight for r in rows)
            x = u01(S, 'ccountry', c.ck) * tot
            acc = 0.0
            pick = rows[-1]
            for r in rows:
                acc += r.weight
                if x < acc:
                    pick = r
                    break
            c.iso = pick.iso; c.off = pick.off; c.culture = pick.culture
            if COUNTRY_BLOCKS:
                # M1 alone (the audit's prototype): blocks over the bucket's rows, the picked row's offset
                c.iso = None; c.culture = None
                c.blocks = self._blocks(c, rows)
        c.v = u01(S, 'cv', c.ck)
        lo, hi = D.PACE_RANGE
        c.pace = lo + (hi - lo) * u01(S, 'pace', c.ck)
        arch = ARCH[a]
        c.lam_max = interp(1.0, *arch['lam'])
        # daily-volume pattern (28 days, weekday-aligned), mean over played days = 1
        raw = []
        played = []
        for i in range(D.PATTERN):
            pl = u01(S, 'play', c.ck, i) < arch['rho']
            vlo, vhi = D.VOLUME_RANGE
            v = vlo + (vhi - vlo) * u01(S, 'vol', c.ck, i)
            w = D.WEEKDAY_VOLUME[posmod(i + 3, 7)]
            raw.append(v * w if pl else 0.0)
            played.append(pl)
        if not any(played):
            best = max(range(D.PATTERN), key=lambda i: (u01(S, 'play', c.ck, i), -i))
            vlo, vhi = D.VOLUME_RANGE
            raw[best] = (vlo + (vhi - vlo) * u01(S, 'vol', c.ck, best)) * D.WEEKDAY_VOLUME[posmod(best + 3, 7)]
            played[best] = True
        s = 0.0; k = 0
        for i in range(D.PATTERN):
            if played[i]:
                s += raw[i]; k += 1
        mean = s / k
        c.m = [x / mean for x in raw]
        c.pre = [0.0]
        for x in c.m:
            c.pre.append(c.pre[-1] + x)
        c.T = c.pre[-1]
        # lapsed pattern: after quitting, a member still opens the game on ~1 play-day in 7, at half volume
        c.ml = []
        for i in range(D.PATTERN):
            on = c.m[i] > 0.0 and u01(S, 'lapse', c.ck, i) < D.LAPSE_DAY_P
            c.ml.append(D.LAPSE_VOLUME * c.m[i] if on else 0.0)
        c.prel = [0.0]
        for x in c.ml:
            c.prel.append(c.prel[-1] + x)
        c.Tl = c.prel[-1]
        # join window
        start = self.epoch + p * WEEK + (day * DAY if day >= 0 else 0)
        c.span = float(DAY if day >= 0 else WEEK)
        c.join0 = float(start) + c.span
        # honeymoon (shipped model only; archetypes without 'honey' are the prototype): members play (1 + hb) x their
        # daily volume until hE = the END of the cohort's join window + `days` (capped by each member's T1). One end per
        # cohort keeps containment: a higher-u member joined earlier, so its honeymoon [J, hE] contains a lower one's.
        c.hb = 0.0; c.hE = None; c.hDL = None
        if 'honey' in arch:
            hb, hdays = arch['honey']
            c.hb = hb
            c.hE = c.join0 + hdays * DAY
            c.hDL = local_day_minute(c.hE, c.off)[0] - BASE_DAY     # last local day whose sessions are sized for (1 + hb)
        c.R = None
        if a == IDX_RETURNER:
            glo, ghi = arch['gap']
            gap = glo + (ghi - glo) * u01(S, 'gap', c.ck)
            c.R = float(self.epoch + (p + 1) * WEEK) + (33.0 + gap) * DAY
        # nickname styles: exact per-cohort counts, dense slots per (style, culture)
        custom = int(fl(c.n * arch['custom'] + u01(S, 'ncustom', c.ck)))
        custom = min(custom, c.n)
        counts = {}
        if STYLE_SYSTEMATIC:
            us = u01(S, 'nsys', c.ck)
            prev, cw = 0, 0.0
            for si, (st, w) in enumerate(Nm.CUSTOM_WEIGHTS):
                cw += w
                cur = custom if si == len(Nm.CUSTOM_WEIGHTS) - 1 else min(custom, int(fl(custom * cw + us)))
                counts[st] = cur - prev
                prev = cur
        else:
            rem = custom
            for si, (st, w) in enumerate(Nm.CUSTOM_WEIGHTS):
                if si == len(Nm.CUSTOM_WEIGHTS) - 1:
                    k2 = rem
                else:
                    k2 = min(rem, int(fl(custom * w + u01(S, 'nstyle', c.ck, si))))
                counts[st] = k2
                rem -= k2
        counts_order = [('default', c.n - custom)] + [(st, counts[st]) for st, _ in Nm.CUSTOM_WEIGHTS]
        c.style_cum = []
        c.style_base = []
        acc = 0
        table = self.local_style_count if c.local else self.style_count
        for st, k2 in counts_order:
            cul = c.culture if st in Nm.CULTURE_STYLES else '*'
            keyc = (st, cul)
            base = table.get(keyc, 0)
            c.style_cum.append((st, acc, acc + k2))
            c.style_base.append(base)
            table[keyc] = base + k2
            acc += k2
        if c.local:
            c.gid0 = self.next_local_gid; self.next_local_gid += c.n
        else:
            c.gid0 = self.next_gid; self.next_gid += c.n
        self.cohorts.append(c)
        if c.blocks is not None:
            rows = BUCKET_ROWS[D.BUCKETS[c.b]] if not c.local else None
            for (ri, s0, e0) in c.blocks:
                iso = self.local[0] if ri < 0 else rows[ri].iso
                self.units.setdefault(iso, []).append((c.idx, s0, e0))

    def _blocks(self, c, rows):
        """M1: contiguous member blocks, one per row of the bucket per stratum (systematic apportionment of the row weights
        with one offset u per stratum, the rows in a per-stratum hashed order). Returns [(row index, s, e)] for the
        non-empty blocks, in member order."""
        S = self.seed
        n = c.n
        if n <= 0:
            return []
        if ROW_TILT is None:
            wts = [r.weight for r in rows]
        else:
            akey = ARCH[c.a]['key']
            wts = [r.weight * ROW_TILT[r.iso].get(akey, 1.0) if r.iso in ROW_TILT else r.weight for r in rows]
        tot = 0.0
        for w in wts:
            tot += w
        strata = COUNTRY_STRATA
        out = []
        for k in range(strata):
            z0 = (k * n) // strata
            z1 = ((k + 1) * n) // strata
            m = z1 - z0
            if m <= 0:
                continue
            if strata == 1:
                order = sorted(range(len(rows)), key=lambda i: (h64(S, 'cord', c.ck, i), i))
                u = u01(S, 'cblk', c.ck)
            else:
                order = sorted(range(len(rows)), key=lambda i: (h64(S, 'cord', c.ck, k, i), i))
                u = u01(S, 'cblk', c.ck, k)
            cw = 0.0
            prev = 0
            last = len(order) - 1
            for q, i in enumerate(order):
                cw += wts[i]
                cur = m if q == last else min(m, int(fl(m * (cw / tot) + u)))
                if cur > prev:
                    out.append((i, z0 + prev, z0 + cur))
                prev = cur
        return out

    # ------------------------------------------------------------- member parameters (all monotone in u)
    def u_of(self, c, j):
        if U_JITTER:
            return (j + u01(self.seed, 'uj', c.ck, j)) / c.n
        return (j + c.v) / c.n

    # ------------------------------------------------------------- v2: a member's country and culture (M1, M5)
    def block_of(self, c, j):
        """(row index, s, e) of member j (M1): the last block starting at or before j (blocks tile [0, n) in order)."""
        bl = c.blocks
        lo, hi = 0, len(bl) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if bl[mid][1] <= j:
                lo = mid
            else:
                hi = mid - 1
        blk = bl[lo]
        assert blk[1] <= j < blk[2], (c.idx, j)
        return blk

    def iso_of(self, c, j):
        if c.blocks is None:
            return c.iso
        if c.local:
            return self.local[0]
        return BUCKET_ROWS[D.BUCKETS[c.b]][self.block_of(c, j)[0]].iso

    def culture_of(self, c, j):
        """The member's name culture: the cohort's (reference / v552), its block row's first culture (M1), or a draw from
        the row's culture mix by the member's id (M1 + M5, label 'mcul')."""
        if c.blocks is None or c.local:
            return c.culture
        row = BUCKET_ROWS[D.BUCKETS[c.b]][self.block_of(c, j)[0]]
        mix = row.mix
        if not MEMBER_CULTURE or mix is None or len(mix) == 1:
            return row.culture
        tot = 0.0
        for _, w in mix:
            tot += w
        x = u01(self.seed, 'mcul', self.gid(c, j)) * tot
        acc = 0.0
        for cu, w in mix:
            acc += w
            if x < acc:
                return cu
        return mix[-1][0]

    def ident(self, c, j):
        """The id that keys a member's drawn nickname and avatar: the gid (a LOCAL member's is salted by its ISO, M4)."""
        return self.gid(c, j) ^ c.salt

    def member(self, c, j):
        a = ARCH[c.a]
        u = self.u_of(c, j)
        lam = interp(u, *a['lam'])
        J = c.join0 - u * c.span
        life = interp(u, *a['life'])
        T1 = J + life * DAY
        flo, fhi = a['first']
        F = flo + (fhi - flo) * u
        T2 = None
        if c.R is not None:
            T2 = c.R + interp(u, *a['life2']) * DAY
        return u, lam, J, T1, F, T2

    def lapse_end(self, c, u, T1):
        a = ARCH[c.a]
        if 'lapse' not in a:
            return T1
        lo, hi = a['lapse']
        le = T1 + (lo + (hi - lo) * u) * DAY
        if c.R is not None and le > c.R:
            le = c.R                       # a returner's lapse phase ends when its comeback starts
        return le

    # ------------------------------------------------------------- activity
    def C(self, c, dl):
        """Cumulative daily volume of the cohort before local day dl (days since BASE_DAY)."""
        return floordiv(dl, D.PATTERN) * c.T + c.pre[posmod(dl, D.PATTERN)]

    def sessions(self, c, dl):
        """(starts[min], fractions, pace_day, m) of cohort c on local day dl; None on a rest day."""
        key = (c.idx, dl)
        hit = self._sess_cache.get(key)
        if hit is not None:
            return hit
        S = self.seed
        m = c.m[posmod(dl, D.PATTERN)]
        if m <= 0.0:
            self._sess_cache[key] = False
            return False
        a = ARCH[c.a]
        smin, smax = a['sess']
        k = smin + below(S, 'sk', smax - smin + 1, c.ck, dl)
        weekend = posmod(dl + BASE_DAY + 3, 7) >= 5
        cdf = D.DIURNAL_CDF[1 if weekend else 0]
        starts = []
        for j in range(k):
            x = u01(S, 'ss', c.ck, dl, j)
            h = 0
            while h < 23 and cdf[h + 1] <= x:
                h += 1
            frac = (x - cdf[h]) / (cdf[h + 1] - cdf[h])
            starts.append((h + frac) * 60.0)
        starts.sort()
        ws = [0.5 + u01(S, 'sf', c.ck, dl, j) for j in range(k)]
        tot = 0.0
        for w in ws:
            tot += w
        f = [w / tot for w in ws]
        Q = c.lam_max * m
        if c.hE is not None and dl <= c.hDL:
            Q = c.lam_max * (1.0 + c.hb) * m      # honeymoon days: windows long enough for the top member's bigger share
        pace = c.pace
        need = Q / pace
        if need > D.DAY_BUDGET:
            pace = Q / D.DAY_BUDGET
        L = [fj * Q / pace for fj in f]
        for j in range(1, k):
            lo = starts[j - 1] + L[j - 1] + D.SESSION_GAP
            if starts[j] < lo:
                starts[j] = lo
        limit = MINUTES - 1.0
        for j in range(k - 1, -1, -1):
            if starts[j] > limit - L[j]:
                starts[j] = limit - L[j]
            limit = starts[j] - D.SESSION_GAP
        res = (starts, f, pace, m)
        self._sess_cache[key] = res
        return res

    def lcum(self, c, lam, t, lapsed=False):
        """Levels a member with rate lam has accumulated by time t along the cohort clock (absolute, not since join).
        lapsed=True uses the lapsed pattern (sparse days, half volume) with the same session windows."""
        dlabs, minute = local_day_minute(t, c.off)
        dl = dlabs - BASE_DAY
        k = posmod(dl, D.PATTERN)
        if lapsed:
            base = lam * (floordiv(dl, D.PATTERN) * c.Tl + c.prel[k])
            ml = c.ml[k]
        else:
            base = lam * self.C(c, dl)
        s = self.sessions(c, dl)
        if s and (not lapsed or ml > 0.0):
            starts, f, pace, m = s
            q = lam * (ml if lapsed else m)
            g = 0.0
            for j in range(len(starts)):
                d = minute - starts[j]
                if d > 0.0:
                    a = pace * d
                    b = f[j] * q
                    g += a if a < b else b
            base += g
        return base

    def lag(self, c, j):
        """M10: seconds member j trails its cohort's clock (0 for the top member; 0 when the switch is off)."""
        if not MEMBER_LAG_MIN:
            return 0.0
        return MEMBER_LAG_MIN * 60.0 * (1.0 - self.u_of(c, j))

    def progress(self, c, j, t):
        """Continuous progress P (level = 1 + floor(P)); None if the member has not joined yet at t."""
        u, lam, J, T1, F, T2 = self.member(c, j)
        if MEMBER_LAG_MIN:
            t = t - MEMBER_LAG_MIN * 60.0 * (1.0 - u)       # M10: the member's own (delayed) clock
        if t < J:
            return None
        tA = t if t < T1 else T1
        first = D.FIRST_PACE * ((tA - J) / 60.0)
        if first > F:
            first = F
        if c.hE is None:
            P = first + (self.lcum(c, lam, tA) - self.lcum(c, lam, J))
        else:
            lh = lam * (1.0 + c.hb)
            E1 = c.hE if c.hE < T1 else T1
            tH = tA if tA < E1 else E1
            P = first + (self.lcum(c, lh, tH) - self.lcum(c, lh, J))
            if tA > E1:
                P += self.lcum(c, lam, tA) - self.lcum(c, lam, E1)
        if t > T1:
            LE = self.lapse_end(c, u, T1)
            if LE > T1:
                tL = t if t < LE else LE
                P += self.lcum(c, lam, tL, True) - self.lcum(c, lam, T1, True)
        if T2 is not None and t > c.R:
            tB = t if t < T2 else T2
            P += self.lcum(c, lam, tB) - self.lcum(c, lam, c.R)
        return P

    def level(self, c, j, t):
        P = self.progress(c, j, t)
        return 0 if P is None else 1 + int(fl(P))

    # ------------------------------------------------------------- identity
    def gid(self, c, j):
        return c.gid0 + j

    def style_of(self, c, j):
        q = perm(j, c.n, h64(self.seed, 'style', c.ck))
        for si, (st, lo, hi) in enumerate(c.style_cum):
            if lo <= q < hi:
                return st, c.style_base[si] + (q - lo)
        raise AssertionError

    def name(self, c, j):
        """Nickname of member j (the reference: unique first-come slots; the shipped model: drawn, see names.DRAW; a blocked
        or over-long draw falls back like a blocked slot). All 'player_xxxxxxx' names come from ONE bijection of [0, 36^7) (salt 0) with disjoint slot
        ranges, so they can never collide: shared-world default slots count up from 0, LOCAL ones from 36^7/2, the user's own
        from 36^7/4 (+ install hash), blocklist fallbacks count DOWN from 36^7 - 1 (8 re-salts per player)."""
        st, slot = self.style_of(c, j)
        if st == 'default':
            nm = Nm.default_name(slot + (Nm.LOCAL_DEFAULT_BASE if c.local else 0), 0)
        elif Nm.DRAW is not None:
            # shipped (SOC1c): drawn with replacement by the player's gid — names may repeat, identity is the gid
            nm = Nm.drawn(st, self.culture_of(c, j), h64(self.seed, 'nick', self.ident(c, j)))
        else:
            nm = Nm.decode(st, slot + (Nm.LOCAL_CUSTOM_BASE if c.local else 0), c.culture)
        k = 0
        while Nm.is_blocked(nm):
            g = self.gid(c, j)
            f = (g * 8 + k) if not c.local else ((g - (1 << 40)) * 8 + k + (1 << 31))
            nm = Nm.default_name(Nm.D36_7 - 1 - f, 0)
            st = 'fallback'
            k += 1
        return nm, st

    def avatar(self, c, j, style):
        a = ARCH[c.a]
        p_default_name, p_custom_name = a['avatar']
        p = p_default_name if style in ('default', 'fallback') else p_custom_name
        g = self.ident(c, j)
        if u01(self.seed, 'avatar?', g) >= p:
            return 0
        return 1 + below(self.seed, 'avatar', 14, g)

    # ------------------------------------------------------------- queries (scalar reference: O(C log n))
    def count_ge(self, x, t, iso=None):
        """Players at level >= x at time t (x >= 1), optionally only country iso. Binary search per cohort."""
        if iso is not None and COUNTRY_BLOCKS:
            # M1: per (cohort, block) unit, count = e - max(boundary, s); one binary search per cohort
            tot = 0
            last_ci = -1
            b = 0
            for (ci, s0, e0) in self.units.get(iso, ()):
                if ci != last_ci:
                    b = self.boundary(self.cohorts[ci], x, t)
                    last_ci = ci
                tot += max(0, e0 - max(b, s0))
            return tot
        tot = 0
        for c in self.cohorts:
            if c.n == 0 or (iso is not None and c.iso != iso):
                continue
            if self.level(c, c.n - 1, t) < x:
                continue
            if self.level(c, 0, t) >= x:
                tot += c.n
                continue
            lo, hi = 0, c.n - 1          # level(hi) >= x, level(lo) < x
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if self.level(c, mid, t) >= x:
                    hi = mid
                else:
                    lo = mid
            tot += c.n - hi
        return tot

    def joined(self, t, iso=None):
        return self.count_ge(1, t, iso)

    # ------------------------------------------------------------- leaderboard queries (the Swift algorithms)
    def _cands(self, iso):
        return [c for c in self.cohorts if c.n > 0 and (iso is None or c.iso == iso)]

    def _units(self, iso):
        """The (cohort, s, e) member ranges a query runs over: whole cohorts (World, or a country without M1) or the
        country's blocks (M1)."""
        if iso is not None and COUNTRY_BLOCKS:
            return [(self.cohorts[ci], s0, e0) for (ci, s0, e0) in self.units.get(iso, ())]
        return [(c, 0, c.n) for c in self._cands(iso)]

    def boundary(self, c, x, t):
        """Smallest j with level >= x (c.n if none)."""
        if self.level(c, c.n - 1, t) < x:
            return c.n
        if self.level(c, 0, t) >= x:
            return 0
        lo, hi = 0, c.n - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.level(c, mid, t) >= x:
                hi = mid
            else:
                lo = mid
        return hi

    def rank_of_level(self, x, t, iso=None):
        """Rank the USER gets at level x: every player at a higher level is above; the user leads its own level
        group (V2 Country evidence: the player's green row sits first among the level-11 rows)."""
        return 1 + self.count_ge(x + 1, t, iso)

    def top(self, t, k, iso=None):
        """Top-k players by progress P (descending): list of (P, gid, cohort, j). K-way merge over cohorts."""
        import heapq
        h = []
        for c, s0, e0 in self._units(iso):
            P = self.progress(c, e0 - 1, t)
            if P is not None:
                h.append((-P, c.gid0 + e0 - 1, c.idx, e0 - 1, s0))
        heapq.heapify(h)
        out = []
        while h and len(out) < k:
            negP, g, ci, j, s0 = heapq.heappop(h)
            c = self.cohorts[ci]
            out.append((-negP, g, c, j))
            if j > s0:
                P = self.progress(c, j - 1, t)
                if P is not None:
                    heapq.heappush(h, (-P, c.gid0 + j - 1, ci, j - 1, s0))
        return out

    def neighbours(self, x, t, k_above, k_below, iso=None):
        """Players just above (level >= x+1, smallest P first) and just below (level <= x, largest P first) a user
        at level x. Returns (above, below), each a list of (P, gid, cohort, j) ordered AWAY from the user."""
        import heapq
        ha = []; hb = []
        for c, s0, e0 in self._units(iso):
            b = self.boundary(c, x + 1, t)
            ba = b if b > s0 else s0            # first member of the unit at level >= x + 1
            if ba < e0:
                ha.append((self.progress(c, ba, t), c.gid0 + ba, c.idx, ba, e0))
            bb = (b if b < e0 else e0) - 1      # last member of the unit at level <= x
            if bb >= s0:
                P = self.progress(c, bb, t)
                if P is not None:
                    hb.append((-P, -(c.gid0 + bb), c.idx, bb, s0))
        heapq.heapify(ha); heapq.heapify(hb)
        above = []
        while ha and len(above) < k_above:
            P, g, ci, j, e0 = heapq.heappop(ha)
            c = self.cohorts[ci]
            above.append((P, g, c, j))
            if j + 1 < e0:
                heapq.heappush(ha, (self.progress(c, j + 1, t), c.gid0 + j + 1, ci, j + 1, e0))
        below = []
        while hb and len(below) < k_below:
            nP, ng, ci, j, s0 = heapq.heappop(hb)
            c = self.cohorts[ci]
            below.append((-nP, -ng, c, j))
            if j > s0:
                P = self.progress(c, j - 1, t)
                if P is not None:
                    heapq.heappush(hb, (-P, -(c.gid0 + j - 1), ci, j - 1, s0))
        return above, below

    def row(self, c, j, t):
        nm, st = self.name(c, j)
        return dict(gid=self.gid(c, j), name=nm, avatar=self.avatar(c, j, st), level=self.level(c, j, t),
                    iso=self.iso_of(c, j), style=st)

    def gid_limit(self, t):
        """Number of shared-world ids whose join period has started by t (independent of how far the table is built)."""
        p = floordiv(int(t) - self.epoch, WEEK)
        lim = 0
        for c in self.cohorts:
            if c.local:
                continue
            if c.p > p:
                break
            lim = c.gid0 + c.n
        return lim

    def find(self, gid):
        """cohort, j of a shared-world player id (binary search on gid0)."""
        lo, hi = 0, len(self.cohorts) - 1
        cs = self.cohorts
        # shared cohorts are in gid order; LOCAL ones live at >= 2^40
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if cs[mid].local or cs[mid].gid0 > gid:
                hi = mid - 1
            else:
                lo = mid
        while cs[lo].local or cs[lo].gid0 + cs[lo].n <= gid:
            lo += 1
        return cs[lo], gid - cs[lo].gid0
