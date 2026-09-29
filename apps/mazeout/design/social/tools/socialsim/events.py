# socialsim/events.py — Weekly Contest, Streak Race, Rocket Race, Sky Jump, Claw Challenge and the win-streak multiplier.
# Reference for PathCore/Social/Events. Opponents are members of the shared World (identity: name, avatar, country);
# their event progress is derived from their World activity (levels they win after the event starts), so an opponent who
# is "asleep" in its own timezone does not move. Everything an event needs is re-derivable from:
#   install seed + event instance id + the user's own timestamps (stored). Nothing about opponents is stored.
import math
from .core import h64, u01, below, fl, round_half_up, interp, EPOCH, DAY, WEEK, event_day, event_week, event_day_start, event_week_start
from . import population as Pp

STEPS = [1, 5, 10, 25, 100]          # the x1 x5 x10 x25 x100 chips

class Streak:
    """The win-streak multiplier shared by Streak Race, Claw Challenge and the fail flow ("You will lose your streak!").
    step 0..4 = x1..x100. A win scores STEPS[step] points and then advances the step; a failed level resets to x1."""
    def __init__(self, step=0):
        self.step = step
    def win(self):
        pts = STEPS[self.step]
        if self.step < 4:
            self.step += 1
        return pts
    def fail(self):
        self.step = 0

UNLOCK = dict(streakRace=30, claw=33, skyJump=40, weekly=50, rocketRace=55)
ROCKET_RETRY_COOLDOWN = 0            # a lost race can be re-joined at once (phone: 'Join' badge right after the loss)
ROCKET_MAX_RACES_PER_DAY = 99        # no daily cap seen
SKY_RETRY_COOLDOWN = 30 * 60
SKY_MAX_RUNS_PER_DAY = 2

# --------------------------------------------------------------------------- user pace (from the stored win history)

def user_pace(wins, t, default_daily=15.0):
    """wins: list of (time, level, firstTry). Returns (daily levels on active days, seconds per win in play, weekly)."""
    recent = [w for w in wins if t - 14 * DAY <= w[0] <= t]
    days = {}
    for w in recent:
        d = event_day(w[0])
        days[d] = days.get(d, 0) + 1
    daily = sorted(days.values())
    daily_ref = daily[len(daily) // 2] if daily else default_daily
    gaps = []
    for a, b in zip(recent, recent[1:]):
        g = b[0] - a[0]
        if 20 <= g <= 900:
            gaps.append(g)
    gaps.sort()
    spw = gaps[len(gaps) // 2] if gaps else 120.0
    weeks = {}
    for w in wins:
        if w[0] <= t:
            k = event_week(w[0])
            weeks[k] = weeks.get(k, 0) + 1
    cur = event_week(t)
    past = sorted(v for k, v in weeks.items() if cur - 4 <= k < cur)
    weekly_ref = past[len(past) // 2] if past else daily_ref * 5.0
    return float(daily_ref), float(min(max(spw, 45.0), 600.0)), float(weekly_ref)

# --------------------------------------------------------------------------- matchmaking

def sample_members(W, t, key_seed, label, count, accept, max_tries=6000):
    """Deterministic rejection sampling of distinct World members joined by t. accept(c, j, attempt) -> bool."""
    out = []
    seen = set()
    total = W.gid_limit(t)
    for a in range(max_tries):
        g = below(key_seed, label, total, a)
        if g in seen:
            continue
        c, j = W.find(g)
        if accept(c, j, a):
            seen.add(g)
            out.append((c, j))
            if len(out) == count:
                break
    return out

def expected_daily(W, c, j, t=None):
    """Expected levels per calendar day of a member at time t (full activity, lapsed phase, or 0)."""
    u, lam, J, T1, F, T2 = W.member(c, j)
    if t is not None and Pp.MEMBER_LAG_MIN:
        t = t - W.lag(c, j)                               # v2 M10: the member's own clock
    full = lam * Pp.ARCH[c.a]['rho']
    if c.hE is not None and t is not None and J <= t < c.hE and t < T1:
        return full * (1.0 + c.hb)                      # shipped: the honeymoon rate
    if t is None or (J <= t < T1) or (T2 is not None and c.R <= t < T2):
        return full
    if T1 <= t < W.lapse_end(c, u, T1):
        return full * Pp.D.LAPSE_DAY_P * Pp.D.LAPSE_VOLUME
    return 0.0

def playing_at(W, c, j, t):
    """Joined and either active or in the lapsed phase (may still come back this week)."""
    return expected_daily(W, c, j, t) > 0.0 and W.member(c, j)[2] <= t - W.lag(c, j)

def active_at(W, c, j, t):
    u, lam, J, T1, F, T2 = W.member(c, j)
    t = t - W.lag(c, j)
    if t < J:
        return False
    if t < T1:
        return True
    return T2 is not None and c.R <= t < T2

def first_time_reaching(W, c, j, target_level, t_lo, t_hi):
    """Earliest time in [t_lo, t_hi] at which level >= target_level (None if not reached by t_hi). Bisection to 1 s."""
    if W.level(c, j, t_hi) < target_level:
        return None
    if W.level(c, j, t_lo) >= target_level:
        return t_lo
    lo, hi = t_lo, t_hi
    while hi - lo > 1.0:
        mid = (lo + hi) / 2.0
        if W.level(c, j, mid) >= target_level:
            hi = mid
        else:
            lo = mid
    return hi

# --------------------------------------------------------------------------- group contests (Weekly Contest, Streak Race)

class GroupContest:
    """A leaderboard group: the user + len(bands) World members picked by stratified matchmaking. Members ARRIVE over the
    window (some before the user joined — they already have points — the rest later, front-loaded), and score only after
    arriving. Standings: score desc, then the moment that score was reached (earlier first); the user's reach moment is
    its last scoring win (or its join time)."""
    KIND = ''
    def __init__(self, W, install_seed, instance, t0, ws, we, ref, bands, recent_windows=(), min_level=1,
                 early_hours=6.0, early_share=None):
        self.W = W; self.t0 = t0; self.ws = ws; self.we = we
        S = h64(install_seed, self.KIND, instance)
        self.S = S
        self.ref = ref
        self.members = []
        taken = set()
        slot = 0
        for count, lo, hi, overlap in bands:
            for k in range(count):
                def accept(c, j, a, lo=lo, hi=hi, overlap=overlap):
                    if (c.idx, j) in taken or not playing_at(W, c, j, t0) or W.level(c, j, t0) < min_level:
                        return False
                    r = self.expected(c, j) / ref
                    if r < lo or r > hi:
                        return False
                    if overlap and recent_windows and a < 1500:
                        # prefer players who were playing while the user was (same hours = visible live duels)
                        return any(W.level(c, j, e) > W.level(c, j, s0) for s0, e in recent_windows[-3:])
                    return True
                got = sample_members(W, t0, S, 'cand%d' % slot, 1, accept)
                if not got:
                    got = sample_members(W, t0, S, 'any%d' % slot, 1,
                                         lambda c, j, a: (c.idx, j) not in taken and playing_at(W, c, j, t0)
                                         and W.level(c, j, t0) >= min_level)
                if got:
                    self.members.append(got[0]); taken.add((got[0][0].idx, got[0][1]))
                slot += 1
        # arrivals
        order = list(range(len(self.members)))
        order.sort(key=lambda i: h64(S, 'order', i))
        if early_share is None:
            n_early = 6 + below(S, 'early', 7)
        else:
            n_early = int(fl(len(self.members) * early_share + u01(S, 'early')))
        self.arrive = [0.0] * len(self.members)
        lo = max(ws, t0 - early_hours * 3600)
        last = max(t0, we - 2 * 3600 if self.KIND == 'streak' else we - 12 * 3600)
        for rank_i, i in enumerate(order):
            if rank_i < n_early:
                a = lo + (t0 - lo) * u01(S, 'arrE', i)
            else:
                x = u01(S, 'arrL', i)
                a = t0 + (last - t0) * x * x
            self.arrive[i] = a
        self.base = [W.level(c, j, a) for (c, j), a in zip(self.members, self.arrive)]

    def expected(self, c, j):
        raise NotImplementedError

    def member_score(self, i, t):
        raise NotImplementedError

    def reached(self, i, t):
        """Moment member i reached its current score (bisection on the monotone score)."""
        s = self.member_score(i, t)
        lo = self.arrive[i]
        if s == 0:
            return lo
        hi = min(t, self.we)
        while hi - lo > 1.0:
            mid = (lo + hi) / 2.0
            if self.member_score(i, mid) >= s:
                hi = mid
            else:
                lo = mid
        return hi

    TIE_BY_NAME = False                  # shipped Streak Race: equal scores are listed alphabetically (phone session 2 §D)

    def standings(self, t, user_score, user_reached, user_name=None):
        if self.TIE_BY_NAME and user_name is not None:
            return self.standings_by_name(t, user_score, user_reached, user_name)
        rows = []
        for i in range(len(self.members)):
            s = self.member_score(i, t)
            if s is None:
                continue
            rows.append((-s, self.reached(i, t), i))
        rows.append((-user_score, user_reached, -1))
        rows.sort()
        return rows                      # rank = index + 1; i == -1 is the user

    def standings_by_name(self, t, user_score, user_reached, user_name):
        """Score desc, then the name's case- and accent-insensitive key (code-point order), then the reach moment, then
        the index (the user = -1). Rows keep the (−score, reached, i) shape of standings()."""
        from . import data as D
        rows = []
        for i, (c, j) in enumerate(self.members):
            s = self.member_score(i, t)
            if s is None:
                continue
            rows.append((-s, D.key(self.W.name(c, j)[0]), self.reached(i, t), i))
        rows.append((-user_score, D.key(user_name), user_reached, -1))
        rows.sort()
        return [(a, r, i) for (a, _, r, i) in rows]

# Weekly Contest -------------------------------------------------------------

WEEKLY_PRIZES = [2000, 1000, 500]
WEEKLY_MIN_TARGET = 35.0             # a group is never matched below a light-casual week (35 levels)
# (count, r_lo, r_hi, prefer same-hours players) — r = member's expected weekly levels / the user's reference
WEEKLY_BANDS = [(1, 1.05, 1.70, False),   # the champion
                (5, 0.92, 1.18, True),    # close rivals, online at the user's hours when possible
                (8, 0.70, 0.92, True),
                (12, 0.45, 0.70, False),
                (13, 0.20, 0.45, False),
                (10, 0.04, 0.20, False)]
WEEKLY_GROUP = 1 + sum(b[0] for b in WEEKLY_BANDS)

class WeeklyContest(GroupContest):
    """Week w's group, formed when the user first opens the Weekly tab or wins a level in week w (level >= 50).
    Score = levels won since arriving in the group."""
    KIND = 'weekly'
    def __init__(self, W, install_seed, w, t0, weekly_ref, recent_windows=()):
        self.w = w
        ws = event_week_start(w)
        GroupContest.__init__(self, W, install_seed, w, t0, ws, ws + WEEK, max(WEEKLY_MIN_TARGET, weekly_ref),
                              WEEKLY_BANDS, recent_windows, min_level=50, early_hours=6.0)

    def expected(self, c, j):
        return expected_daily(self.W, c, j, self.t0) * 7.0

    def member_score(self, i, t):
        if t < self.arrive[i]:
            return None
        c, j = self.members[i]
        return max(0, self.W.level(c, j, min(t, self.we)) - self.base[i])

# Streak Race ----------------------------------------------------------------

STREAK_PRIZES = [2000, 1000, 500, 100, 100, 100, 100, 100, 100, 100]   # ranks 1..10; 2..6 seen on the phone (shot 203)
STREAK_MIN_TARGET = 8.0
STREAK_BANDS = [(2, 1.15, 2.00, False),
                (4, 0.90, 1.15, True),
                (5, 0.60, 0.90, True),
                (5, 0.30, 0.60, False),
                (3, 0.08, 0.30, False)]
STREAK_GROUP = 1 + sum(b[0] for b in STREAK_BANDS)

class StreakRace(GroupContest):
    """Event day d's race. Score = the multiplier chip value of each win (x1 x5 x10 x25 x100), a fail resets to x1.
    Members carry a streak into the day and fail with their own probability before each win."""
    KIND = 'streak'
    FAIL_Q = (0.06, 0.24)                # a member's fail probability before each win: lo + span * u01 (shipped: SH)
    def __init__(self, W, install_seed, day, t0, daily_ref, recent_windows=()):
        self.day = day
        ds = event_day_start(day)
        self.end = ds + DAY
        GroupContest.__init__(self, W, install_seed, day, t0, ds, ds + DAY, max(STREAK_MIN_TARGET, daily_ref),
                              STREAK_BANDS, recent_windows, min_level=UNLOCK['streakRace'], early_hours=24.0,
                              early_share=min(1.0, max(0.0, (t0 - ds) / DAY)))
        S = self.S
        self.s0 = []
        self.q = []
        qlo, qspan = self.FAIL_Q
        for i in range(len(self.members)):
            x = u01(S, 's0', i)
            self.s0.append(0 if x < 0.5 else 1 if x < 0.7 else 2 if x < 0.82 else 3 if x < 0.9 else 4)
            self.q.append(qlo + qspan * u01(S, 'q', i))

    def expected(self, c, j):
        return expected_daily(self.W, c, j, self.t0)

    def member_score(self, i, t):
        if t < self.arrive[i]:
            return None
        c, j = self.members[i]
        n = max(0, self.W.level(c, j, min(t, self.we)) - self.base[i])
        s = self.s0[i]; pts = 0
        for k in range(n):
            if u01(self.S, 'fail', i, k) < self.q[i]:
                s = 0
            pts += STEPS[s]
            if s < 4:
                s += 1
        return pts

# --------------------------------------------------------------------------- Rocket Race

ROCKET_LEVELS = [5, 7, 9]
ROCKET_HOLD_MIN = (14.0, 40.0)       # a finishing rival waits at N-1 at most this long after the race starts ...
ROCKET_DELTA = (0.45, 1.85)          # ... or this many of the user's median level times after the user reaches N-1
ROCKET_PRIZES = [(500, 45), (1000, 90), (2000, 180)]   # coins, minutes of infinite lives (stage 1 = evidence)

class RocketRace:
    """5 lanes: first to beat N levels after joining wins the stage. Rivals are World members in or near a session;
    a rival that would reach N is HELD at N-1 until min(t0 + hold, userReachedNminus1 + delta) (rubber band)."""
    ROLES = ['hot', 'hot', 'warm', 'idle']
    SPRINT_MINUTES = 15.0                # 'sprint': beats the stage's N levels within this many minutes x N/5 (shipped)
    HOLD_BY_ROLE = None                  # role -> (lo, hi) minutes; None = ROCKET_HOLD_MIN for every lane

    def __init__(self, W, install_seed, race_id, stage, t0, sec_per_win):
        self.W = W; self.t0 = t0; self.stage = stage
        self.N = ROCKET_LEVELS[stage - 1]
        S = h64(install_seed, 'rocket', race_id)
        self.S = S
        self.end = event_day_start(event_day(t0) + 1)
        roles = self.ROLES
        N = self.N
        sprint = self.SPRINT_MINUTES * 60.0 * N / 5.0
        self.rivals = []
        for r_i, role in enumerate(roles):
            def accept(c, j, a, role=role):
                if not active_at(W, c, j, t0):
                    return False
                L0 = W.level(c, j, t0)
                if role == 'sprint':
                    return W.level(c, j, t0 + sprint) - L0 >= N
                if role == 'hot':
                    return W.level(c, j, t0 + 20 * 60) - L0 >= 2
                if role == 'busy':
                    return W.level(c, j, t0 + 20 * 60) - L0 >= 1
                if role == 'steady':
                    return 1 <= W.level(c, j, t0 + 20 * 60) - L0 <= 3
                if role == 'warm':
                    return W.level(c, j, t0 + 20 * 60) == L0 and W.level(c, j, t0 + 150 * 60) - L0 >= 2
                return W.level(c, j, t0 + 180 * 60) == L0
            got = sample_members(W, t0, S, 'cand%d' % r_i, 1,
                                 lambda c, j, a: accept(c, j, a) and (c, j) not in self.rivals)
            if not got:     # fallback: any active member
                got = sample_members(W, t0, S, 'any%d' % r_i, 1, lambda c, j, a: active_at(W, c, j, t0))
            self.rivals.append(got[0])
        self.base = [W.level(c, j, t0) for c, j in self.rivals]
        hr = [ROCKET_HOLD_MIN if self.HOLD_BY_ROLE is None else self.HOLD_BY_ROLE[r] for r in roles]
        self.hold = [t0 + (hr[i][0] + (hr[i][1] - hr[i][0]) * u01(S, 'hold', i)) * 60 for i in range(4)]
        self.delta = [sec_per_win * (ROCKET_DELTA[0] + (ROCKET_DELTA[1] - ROCKET_DELTA[0]) * u01(S, 'delta', i))
                      for i in range(4)]
        self.natural = []
        for i, (c, j) in enumerate(self.rivals):
            self.natural.append(first_time_reaching(W, c, j, self.base[i] + self.N, t0, self.end))

    def finish_time(self, i, user_nm1_time):
        nat = self.natural[i]
        if nat is None:
            return None
        gate = self.hold[i]
        if user_nm1_time is not None:
            gate = min(gate, user_nm1_time + self.delta[i])
        f = max(nat, gate)
        return f if f <= self.end else None

    def rival_progress(self, i, t, user_nm1_time):
        c, j = self.rivals[i]
        f = self.finish_time(i, user_nm1_time)
        if f is not None and t >= f:
            return self.N
        n = self.W.level(c, j, min(t, self.end)) - self.base[i]
        return max(0, min(n, self.N - 1))

    def outcome(self, user_times):
        """user_times: sorted times of the user's wins since joining. Returns ('win'|'lose'|'none', finish time)."""
        nm1 = user_times[self.N - 2] if len(user_times) >= self.N - 1 else None
        rival_first = None
        for i in range(4):
            f = self.finish_time(i, nm1)
            if f is not None and (rival_first is None or f < rival_first):
                rival_first = f
        u = user_times[self.N - 1] if len(user_times) >= self.N else None
        if u is not None and u <= self.end and (rival_first is None or u < rival_first):
            return 'win', u
        if rival_first is not None:
            return 'lose', rival_first
        return 'none', self.end

# --------------------------------------------------------------------------- Sky Jump

SKY_LEVELS = [5, 7, 9]
SKY_POOLS = [5000, 7000, 10000]

SKY_DROPS = None      # shipped: per stage (drop_lo, drop_hi, first_step, winners_lo, winners_hi) — see shipped.py

class SkyJump:
    """100 players; beat N levels in a row on the first try within 24 h of joining. The 'Players' count is a function of
    the USER's step (evidence: 100 -> 82 -> 64 -> .. -> 47 after 4 steps -> 7 winners)."""
    def __init__(self, install_seed, attempt_id, stage):
        S = h64(install_seed, 'sky', attempt_id)
        self.S = S; self.N = SKY_LEVELS[stage - 1]; self.pool = SKY_POOLS[stage - 1]
        if SKY_DROPS is not None:
            self._absolute(S, SKY_DROPS[stage - 1])
            return
        alive = [100]
        for k in range(1, self.N):
            h = 0.13 + 0.12 * u01(S, 'haz', k)
            drop = int(round_half_up((alive[-1] - 1) * h))
            alive.append(alive[-1] - drop)
        others = 2 + int(fl(10.0 * (u01(S, 'w1') + u01(S, 'w2')) / 2.0))
        others = min(others, alive[-1] - 1)
        alive.append(1 + others)
        self.alive = alive                  # alive[k] = 'Players' shown after the user's k-th win; alive[N] = winners
        self.share = self.pool // alive[-1]

    def _absolute(self, S, spec):
        """Shipped curve (phone session 2 §F): a near-constant number of players drops out per level — a per-attempt rate d
        in [lo, hi], each step d ± 1 — starting at the user's step `first` (the counter stayed at 100 after the first win
        in stages 2 and 3), and the winners W in [w_lo, w_hi] share the pool (stage 2: 100 100 88 75 62 49 36 -> 15)."""
        lo, hi, first, wlo, whi = spec
        d = lo + (hi - lo) * u01(S, 'hazd')
        alive = [100]
        for k in range(1, self.N):
            drop = 0 if k < first else int(round_half_up(d + 2.0 * u01(S, 'haz', k) - 1.0))
            alive.append(max(2, alive[-1] - max(0, drop)))
        w = wlo + int(fl((whi - wlo + 1) * u01(S, 'win')))
        alive.append(max(2, min(w, alive[-1] - 1)))
        self.alive = alive
        self.share = self.pool // alive[-1]

# --------------------------------------------------------------------------- Claw Challenge (evidence-only ladder)

CLAW_THRESHOLDS_KNOWN = [1, 200, 300, 400, 300, 500]     # steps 1..6 seen on the phone; 7..20 UNKNOWN (phone session)
