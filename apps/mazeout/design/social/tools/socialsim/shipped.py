# socialsim/shipped.py — the SHIPPED parameter set ('v552') of the offline world, as a patch over the prototype.
#
# The prototype (data.py / population.py / names.py / events.py as written) stays the `reference` model, pinned bit for bit
# by design/social/fixtures. `apply()` turns this process into the shipped model by changing PARAMETERS and switching on
# the shipped mechanisms that live, off by default, in the reference modules: the honeymoon (population: archetype key
# 'honey'), names.VARIANTS + the 'leet' style, names.DRAW (drawn nicknames, duplicates allowed), GroupContest.TIE_BY_NAME,
# the RocketRace roles/holds, events.SKY_DROPS and events.SKY_LEVELS.
# Swift: SocialModel.swift `.v552`, Names.swift `SocialNameStyle.v552`, RaceBots.swift `SocialGroupSpec.v552*` /
# `SocialRocketSpec.v552` / `SocialSkySpec.v552`, SocialConfig.swift defaults (App/Resources/Tuning/social.json).
#
# Calibration history (SPEC-social §13, §14):
#   SOC1  (25 Sep 11:27) — world sizes/levels to the phone's session-1 boards (World #1-#278, Turkey rank 455 at L62),
#                          Weekly = 10 players, Streak Race = 50 rows.
#   SOC1b (25 Sep)       — phone session 2 (research/social-dynamics.md): name-style mix, bursty Weekly rivals, World
#                          grinders, the Turkey rank slope, Streak Race arrivals/gains/ties, the Rocket sprinter, Sky Jump
#                          drop-outs. Before/after numbers: build/soc1b/calibration.md (tools/calib_s2.py).
#   SOC1c (25 Sep)       — orchestrator: nicknames are DRAWN with replacement (duplicates allowed like the original's two
#                          "Bobby"), so plain first names reach the phone's ~14 % and digits drop toward its ~7 %; Sky Jump
#                          stage 3 = 10 levels / 10000 (phone sessions 2 and 3). build/soc1c/calibration.md.
from . import core as K, data as D, population as Pp, names as Nm, events as E

# ---------------------------------------------------------------- world (population)
# SOC1: shares/λ/life/lapse re-fitted to the session-1 boards. SOC1b (none of it moves the World top: grinders' λ and
# life are unchanged, the honeymoon skips enthusiasts and grinders):
#   custom  who set a nickname: the phone's boards show ~14-18 % player_xxxxxxx (Streak Race 9/49, Weekly 1/9, World top
#           2/23, Turkey 3/20) against SOC1's 42 %; tourists (who never reach a board: V2's Country rows at L11-14 were
#           all default) stay mostly default.
#   honey   new players play (1 + 1.0) x their volume until 5 days after their join week ends: the phone's Turkey rank
#           fell ~3.6 places per level won at L62-L84 (455 -> 375), i.e. few players linger there (SOC1's world: 5.3).
#   sess    sessions per play day: the phone's Weekly rivals moved in bursts spread over the day and ~40 % stayed idle for
#           the rest of it (4 of 9 from 06:39 to 14:47): more, shorter sessions for casual/regular/enthusiast/dabbler/
#           returner. Grinders 3-6 -> 1-3: the World top rows are static for hours and a few climb ~35 levels an hour for
#           1-2 h (Crazzijj +66 in 1.9 h, Wilbert +41 in 1 h) — fewer, longer sessions.
ARCH = {
    'tourist': dict(share=0.4844, custom=0.08),
    'dabbler': dict(lam=([0, 1], [5.0, 18.0]), life=([0, 1], [1.0, 8.0]), lapse=(10.0, 45.0), custom=0.80, honey=(1.0, 5.0),
                    sess=(1, 4)),
    'casual': dict(share=0.16, lam=([0, 0.6, 0.9, 1], [4.0, 8.0, 14.0, 20.0]), life=([0, 0.5, 1], [10.0, 30.0, 80.0]),
                   lapse=(30.0, 150.0), custom=0.84, honey=(1.0, 5.0), sess=(1, 4)),
    'regular': dict(share=0.09, lam=([0, 0.5, 0.9, 1], [6.0, 10.0, 16.0, 22.0]), life=([0, 0.5, 1], [30.0, 90.0, 300.0]),
                    custom=0.86, honey=(1.0, 5.0), sess=(2, 5)),
    'enthusiast': dict(share=0.006, lam=([0, 0.5, 0.9, 1], [10.0, 20.0, 32.0, 42.0]), life=([0, 0.5, 1], [60.0, 200.0, 600.0]),
                       custom=0.88, sess=(3, 6)),
    'grinder': dict(share=0.0006, lam=([0, 0.5, 0.9, 0.98, 1], [25.0, 50.0, 88.0, 100.0, 108.0]), custom=0.90, sess=(1, 3)),
    'returner': dict(custom=0.84, honey=(1.0, 5.0), sess=(1, 3)),
}
# TR 2.0 (reference) -> 0.5 (SOC1) -> 0.30 (SOC1b, with the honeymoon more Turkish players pass L62). A country is a set
# of whole cohorts, so the Turkey board moves in lumps of one cohort (0.29 -> rank 346, 0.30 -> 420, 0.32 -> 527 at L62).
WEIGHTS = {'TR': 0.30}
MAX_NAME = 16                   # the player's own username rule: longer nicknames are replaced like blocked ones
AVATARS = 8                     # the 8 shipped portraits (CONSISTENCY V-24)
EXTRA_STEMS = ['maze']          # the original's title word stays out of every nickname

# ---------------------------------------------------------------- nicknames (names.DRAW + names.VARIANTS + the style mix)
# The phone's ~113 names (§H), classified like calib_s2.py: player_ 14 %, plain first names 14 %, other capitalised
# names/handles 34 %, lowercase 15 %, CamelCase Adjective+Noun 12 % (a third with 2 digits), ALL CAPS 4 %, digits/leet 7 %;
# two different "Bobby" in the World top 15.
# SOC1b kept every nickname unique (first-come slots) and could not get there: a finite first-name list means later
# joiners' first names carry numbers (firstName 0.5 %, digits 24 %). SOC1c (orchestrator) DRAWS custom nicknames with
# replacement (names.drawn): first names by popularity (index floor(n u^2) over the most-common-first lists), a number on
# numberP % of them (2 digits 75 %), case/spelling variants per player. With no uniqueness to protect, the mix moves back to
# first names; the leet share stays the phone's short/odd handles (L8M, K710, 0xBK).
CUSTOM_WEIGHTS = [('given', 0.24), ('word', 0.01), ('compound', 0.14), ('invented', 0.36), ('caps', 0.02),
                  ('underscore', 0.005), ('initials', 0.005), ('mixed', 0.19), ('leet', 0.03)]
# SOC1c: per-cohort style counts by systematic apportionment (population.STYLE_SYSTEMATIC): the reference's
# last-style-takes-the-remainder rounding put 'leet' on ~12 % of the World top 100 (small cohorts) instead of 3 %.
STYLE_SYSTEMATIC = True
VARIANTS = dict(inventedLower=25, inventedUpper=8, givenUpper=8, compoundDigits=35, mixedLower=17)
DRAW = dict(numberP=dict(given=5, word=5, invented=5, caps=5, underscore=5, initials=5, mixed=5), twoDigitP=75,
            headP=40, headN=50)

# ---------------------------------------------------------------- Weekly Contest (10 players)
# SOC1's bands (they fit the phone's ratios: rivals ~[2.3 1.4 .85 .82 .68 .68 .56 .18 .12] x the player's own progress);
# SOC1b: the two idle members are online at the join too (Boo +6 and Mema +4 in the first 85 min, then nothing all day).
WEEKLY_BANDS = [(1, 1.10, 1.80, True), (2, 0.90, 1.20, True), (2, 0.65, 0.90, True), (2, 0.40, 0.65, True),
                (2, 0.08, 0.40, True)]
WEEKLY_MATCH = (1800.0, 5400.0)          # sameHours = playing in [t0 - 30 min, t0 + 90 min] (online around the join)
WEEKLY_PER_PLAY_DAY = False              # r = member's calendar-average levels x 7 / ref (True: per PLAYED day x 7)

# ---------------------------------------------------------------- Streak Race (50 rows)
# SOC1b (phone session 2 §D): the race the player joins starts with every rival at 0 (listed alphabetically), ~2/3 of
# them score within the first hour and the rest stay 0 for hours (17 at +69 min, 11 at +4 h); equal scores are listed
# alphabetically (case-insensitive). Members = players who play within 2 h after the join (+ 8 idle ones). The phone's
# leaders ran long unbroken x100 streaks (4081, 3645, 3573 three hours in): a heavier top band and a lower fail chance
# per win (2-12 % instead of 6-30 %) bring ours to ~70-90 % of that (their +2583-in-28-min jumps are not human-paced).
STREAK_BANDS = [(5, 1.20, 2.20, True), (10, 0.75, 1.20, True), (14, 0.40, 0.75, True), (12, 0.10, 0.40, True),
                (8, 0.02, 0.10, False)]
STREAK_FAIL_Q = (0.02, 0.10)             # (lo, span): a member's fail chance before each win = lo + span * u01
STREAK_MIN_TARGET = 4.0
STREAK_LAST_ARRIVAL = 12 * 3600          # SOC1's arrivals (unused while STREAK_AT_JOIN)
STREAK_AT_JOIN = True                    # every member arrives at the join with 0 points
STREAK_MATCH = (0.0, 7200.0)             # sameHours = wins a level within 2 h after the join (None: during the event day)
STREAK_TIE_BY_NAME = True

# ---------------------------------------------------------------- Rocket Race
# Phone (4 races): one rival finishes 5 levels 6, 8, 15-20 and 19 min after the join; the others are at [3,2,1],
# [3,1,1], [4,3,1] then; the (slow) player lost all four. A 'sprint' rival (beats N levels within 15 min x N/5 at its own
# pace) finishes at max(its natural finish, min(join + 6..19 min, the player's N-1 + δ)); the others keep SOC1's hold.
ROCKET_ROLES = ['sprint', 'hot', 'steady', 'steady']
ROCKET_HOLDS = {'sprint': (6.0, 19.0), 'hot': (14.0, 40.0), 'steady': (14.0, 40.0)}
ROCKET_SPRINT_MINUTES = 15.0

# ---------------------------------------------------------------- Sky Jump: (drop_lo, drop_hi, first_step, W_lo, W_hi)
# Phone: stage 1 (5 levels, S1) 100 82 64 ? 47 -> 7 winners (5000/7 = 714); stage 2 (7) 100 100 88 75 62 49 36 -> 15
# (7000/15 = 466); stage 3 = 10 levels, PRIZE 10000 (sessions 2 and 3): 100 100 91 82 74 65 57 (S2, failed at 7/10) and
# 100 100 91 83 75 66 57 48 40 32 -> 7 winners (S3: "You win! 1428 — sharing the reward with 6 other winners", 10000/7).
# A near-constant number drops per level (8-13 of 100; stage 3: 8-9), from the 1st win in stage 1 and the 2nd in stages
# 2-3. SOC1c: stage 3 = 10 levels (SKY_LEVELS; social.json events.skyJump.levels switches C3's EventRules with it),
# drop 7.5-9.5 (phone mean 8.5), winners 5-9 (the phone's 7 = the median).
SKY_LEVELS = [5, 7, 10]
SKY_DROPS = [(10.0, 16.0, 1, 5, 10), (11.0, 14.0, 2, 12, 18), (7.5, 9.5, 2, 5, 9)]

MODEL = 'reference'


def apply():
    """Patch the imported reference modules into the shipped model (in memory, once, before building any World)."""
    global MODEL
    if MODEL == 'v552':
        return
    MODEL = 'v552'
    for a in D.ARCHETYPES:
        if a['key'] in ARCH:
            a.update(ARCH[a['key']])
    for r in D.COUNTRY_ROWS:
        if r.iso in WEIGHTS:
            r.weight = WEIGHTS[r.iso]
    Pp.TOTAL_W = sum(r.weight for r in D.COUNTRY_ROWS)
    Pp.BUCKET_SHARE = [sum(r.weight for r in Pp.BUCKET_ROWS[b]) / Pp.TOTAL_W for b in D.BUCKETS]
    Pp._check_containment()

    def avatar_v552(self, c, j, style):
        p_default_name, p_custom_name = Pp.ARCH[c.a]['avatar']
        p = p_default_name if style in ('default', 'fallback') else p_custom_name
        g = self.ident(c, j)              # = the gid (a LOCAL member's is salted by its ISO in v2, M4)
        if K.u01(self.seed, 'avatar?', g) >= p:
            return 0
        return 1 + K.below(self.seed, 'avatar', AVATARS, g)
    Pp.World.avatar = avatar_v552
    base_blocked = Nm.is_blocked
    Nm.is_blocked = lambda name: (len(name) > MAX_NAME or base_blocked(name) or any(s in D.key(name) for s in EXTRA_STEMS))
    Nm.CUSTOM_WEIGHTS = CUSTOM_WEIGHTS
    Nm.VARIANTS = VARIANTS
    Nm.DRAW = DRAW
    Pp.STYLE_SYSTEMATIC = STYLE_SYSTEMATIC
    E.RocketRace.ROLES = ROCKET_ROLES
    E.RocketRace.HOLD_BY_ROLE = ROCKET_HOLDS
    E.RocketRace.SPRINT_MINUTES = ROCKET_SPRINT_MINUTES
    E.SKY_DROPS = SKY_DROPS
    E.SKY_LEVELS = SKY_LEVELS
    E.StreakRace.FAIL_Q = STREAK_FAIL_Q


class Weekly(E.GroupContest):
    """The shipped Weekly Contest: 10 players, all arrived within the quarter hour before the player (phone v552)."""
    KIND = 'weekly'

    def __init__(self, W, install_seed, w, t0, weekly_ref, recent_windows=()):
        self.w = w
        ws = K.event_week_start(w)
        # the reference's same-hours rule, applied to the join window instead of the player's last sessions
        match = [(t0 - WEEKLY_MATCH[0], t0 + WEEKLY_MATCH[1])]
        E.GroupContest.__init__(self, W, install_seed, w, t0, ws, ws + K.WEEK, max(E.WEEKLY_MIN_TARGET, weekly_ref),
                                WEEKLY_BANDS, match, min_level=50, early_hours=0.25, early_share=1.0)

    def expected(self, c, j):
        if WEEKLY_PER_PLAY_DAY:
            return E.expected_daily(self.W, c, j, self.t0) / Pp.ARCH[c.a]['rho'] * 7.0
        return E.expected_daily(self.W, c, j, self.t0) * 7.0

    def member_score(self, i, t):
        if t < self.arrive[i]:
            return None
        c, j = self.members[i]
        return max(0, self.W.level(c, j, min(t, self.we)) - self.base[i])


class Streak(E.StreakRace):
    """The shipped Streak Race: 50 rows; scoring = the reference's."""
    @property
    def TIE_BY_NAME(self):
        return STREAK_TIE_BY_NAME

    def expected(self, c, j):
        """Levels per PLAYED day (the player's reference is wins per active day; the reference used per calendar day)."""
        return E.expected_daily(self.W, c, j, self.t0) / Pp.ARCH[c.a]['rho']

    def __init__(self, W, install_seed, day, t0, daily_ref, recent_windows=()):
        saved = (E.STREAK_BANDS, E.STREAK_MIN_TARGET)
        E.STREAK_BANDS, E.STREAK_MIN_TARGET = STREAK_BANDS, STREAK_MIN_TARGET
        ds = K.event_day_start(day)
        # the reference's same-hours rule applied to the event day (SOC1) or to the 2 h after the join (SOC1b)
        window = [(ds, ds + K.DAY)] if STREAK_MATCH is None else [(t0 - STREAK_MATCH[0], t0 + STREAK_MATCH[1])]
        try:
            E.StreakRace.__init__(self, W, install_seed, day, t0, daily_ref, window)
        finally:
            E.STREAK_BANDS, E.STREAK_MIN_TARGET = saved
        if STREAK_AT_JOIN:
            self.arrive = [float(t0)] * len(self.members)
            self.base = [W.level(c, j, t0) for (c, j) in self.members]
            return
        S = self.S
        order = list(range(len(self.members)))
        order.sort(key=lambda i: K.h64(S, 'order', i))
        early_share = min(1.0, max(0.0, (t0 - self.ws) / K.DAY))
        n_early = int(K.fl(len(self.members) * early_share + K.u01(S, 'early')))
        lo = max(self.ws, t0 - 24.0 * 3600)
        last = max(t0, self.we - STREAK_LAST_ARRIVAL)
        for rank_i, i in enumerate(order):
            if rank_i < n_early:
                a = lo + (t0 - lo) * K.u01(S, 'arrE', i)
            else:
                x = K.u01(S, 'arrL', i)
                a = t0 + (last - t0) * x * x
            self.arrive[i] = a
        # a member arrives no later than its first win of the day (it joins the race when it plays)
        for i, (c, j) in enumerate(self.members):
            f = E.first_time_reaching(W, c, j, W.level(c, j, self.ws) + 1, self.ws, self.we)
            if f is not None and f - 1.0 < self.arrive[i]:
                self.arrive[i] = max(self.ws, f - 1.0)
        self.base = [W.level(c, j, a) for (c, j), a in zip(self.members, self.arrive)]
