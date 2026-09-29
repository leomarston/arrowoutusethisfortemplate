#!/usr/bin/env python3
"""lives_ref.py — C3's INDEPENDENT reference of the lives chain (SPEC-architecture §4.17 "LivesTests"; SPEC-gameplay §8).

Written from the rules, not from the Swift code:
  * max 5 lives; a life is TAKEN when a level starts and GIVEN BACK when that attempt is won (fail.md §6);
  * one life per 1800 s on one continuous clock: `anchor` = start of the running period, the next life at anchor + 1800,
    None exactly when full; take: if full, anchor = t; tick: gained = floor((t - anchor + 1e-6) / 1800), anchor += gained*1800;
    give back: count + 1 (capped), anchor kept unless full again;
  * unlimited lives: checked at the START only (a level started under it takes and refunds nothing); grants stack
    until = max(until, t) + d;
  * the kill rule: an attempt still running at launch is a failed attempt (its life stays spent);
  * Refill (900 coins): lives to max, not when full or under unlimited;
  * TIME: t = the rewind-safe world clock = max(floor(wall), highWater), and highWater is raised; a repaired clock more
    than 30 days behind the mark REBASES (highWater = floor(wall)) and every stored absolute time moves by the same step.

`python3 lives_ref.py`          prints a summary of the self-checks (the phone ledgers of fail.md §6 / economy.md §2b);
`python3 lives_ref.py --emit F` writes the 200 random scripts + the expected state after every operation to F (JSON);
the Swift LivesTests replays them through `Economy` and must match exactly (Tests/Fixtures/c3_lives_scripts.json).
"""
import json, math, random, sys

MAX = 5
REFILL = 1800.0
EPS = 1e-6
REFILL_PRICE = 900
REBASE_AFTER = 30 * 86400


class Player:
    def __init__(self, count=MAX, anchor=None, until=None, hw=0, coins=1000):
        self.count = count
        self.anchor = anchor          # float seconds since 1970 or None
        self.until = until            # float or None
        self.hw = hw                  # int
        self.coins = coins
        self.active = False
        self.free = False
        self.started = None

    def copy(self):
        p = Player(self.count, self.anchor, self.until, self.hw, self.coins)
        p.active, p.free, p.started = self.active, self.free, self.started
        return p

    # ---- the clock
    def clock(self, wall):
        device = math.floor(wall)
        before = self.hw
        if self.hw - device > REBASE_AFTER:
            self.hw = device
        elif device > self.hw:
            self.hw = device
        t = self.hw
        if before > 0 and t < before:           # a rebase: keep the remaining durations
            d = float(t - before)
            if self.anchor is not None:
                self.anchor += d
            if self.until is not None:
                self.until += d
            if self.started is not None:
                self.started += d
        return float(t)

    # ---- the chain
    def tick(self, t):
        if self.count < 0:
            self.count = 0
        if self.count >= MAX:
            self.anchor = None
            return 0
        a = t if self.anchor is None else min(self.anchor, t)
        el = t - a
        gained = int(math.floor((el + EPS) / REFILL)) if el > 0 else 0
        new = min(MAX, self.count + gained)
        added = new - self.count
        self.count = new
        self.anchor = None if new >= MAX else a + gained * REFILL
        return added

    def take(self, t):
        self.tick(t)
        if self.count <= 0:
            return
        if self.count >= MAX:
            self.anchor = t
        self.count -= 1
        if self.count >= MAX:
            self.anchor = None

    def give(self, t):
        self.tick(t)
        self.count = min(MAX, self.count + 1)
        if self.count >= MAX:
            self.anchor = None

    def unlimited(self, t):
        return self.until is not None and self.until > t

    # ---- operations (the Economy API)
    def start(self, wall):
        if self.active:
            return 'attemptInProgress'
        t = self.clock(wall)
        self.tick(t)
        free = self.unlimited(t)
        if not free and self.count <= 0:
            return 'noLives'
        if not free:
            self.take(t)
        self.free = free
        self.active = True
        self.started = t
        return 'ok'

    def finish(self, wall, won):
        if not self.active:
            return 'none'
        t = self.clock(wall)
        if won and not self.free:
            self.give(t)
        self.active = False
        self.free = False
        self.started = None
        return 'ok'

    def launch(self, wall):
        t = self.clock(wall)
        self.tick(t)
        if self.until is not None and self.until <= t:
            self.until = None
        if self.active:
            self.finish(wall, won=False)
            self.clock(wall)                    # the event hook reads the clock too (no change)
            return 'killed'
        return 'ok'

    def grant(self, wall, seconds):
        t = self.clock(wall)
        if seconds > 0:
            base = t if self.until is None else max(self.until, t)
            self.until = base + seconds
        return 'ok'

    def refill(self, wall):
        t = self.clock(wall)
        self.tick(t)
        if self.count >= MAX or self.unlimited(t):
            return 'no'
        if self.coins < REFILL_PRICE:
            return 'no'
        self.coins -= REFILL_PRICE
        self.count = MAX
        self.anchor = None
        return 'ok'

    def status(self, wall):
        c = self.copy()
        t = c.clock(wall)
        c.tick(t)
        if c.unlimited(t):
            return ['unlimited', c.until]
        if c.count >= MAX:
            return ['full']
        a = t if c.anchor is None else c.anchor
        return ['counting', c.count, a + REFILL]

    def snapshot(self):
        return {'count': self.count, 'anchor': self.anchor, 'until': self.until, 'hw': self.hw, 'coins': self.coins,
                'active': self.active, 'free': self.free}


# ---------------------------------------------------------------------------------------------- the phone ledgers
def self_checks():
    import datetime as dt
    def at(hms):                              # 2026-09-25 local TRT (UTC+3)
        h, m, s = map(int, hms.split(':'))
        return dt.datetime(2026, 9, 25, h - 3, m, s, tzinfo=dt.timezone.utc).timestamp()
    out = []
    # fail.md §6: L62 #2 start 05:18:07 from 5 Full → fail → at 05:28:22 "4, 19:45" (next 05:48:07)
    p = Player(hw=0)
    p.start(at('05:18:07')); p.finish(at('05:25:40'), won=False)
    st = p.status(at('05:28:22'))
    out.append(('L62 #2: 4 lives, next life 05:48:07', st == ['counting', 4, at('05:48:07')]))
    # #3 start 05:30:44, #4 Try Again 05:46:37, quit → at 05:49:25 "3, 28:42" (next 06:18:07)
    p.start(at('05:30:44')); p.finish(at('05:46:17'), won=False)
    p.start(at('05:46:37')); p.finish(at('05:49:00'), won=False)
    st = p.status(at('05:49:25'))
    out.append(('after the quit: 3 lives, next 06:18:07', st == ['counting', 3, at('06:18:07')]))
    # economy.md §2b: the tick at 06:18:07 (3 → 4, next 06:48:07)
    out.append(('tick 06:18:07', p.status(at('06:18:06')) == ['counting', 3, at('06:18:07')]
                and p.status(at('06:18:07')) == ['counting', 4, at('06:48:07')]))
    # direct test 06:54:20 start from 5 Full, failed 07:20:35, closed 07:28:47 → "5 Full" (the life came back 07:24:20)
    q = Player()
    q.start(at('06:54:20')); q.finish(at('07:28:47'), won=False)
    out.append(('start 06:54:20, fail 26 min later → 5 Full at 07:29', q.status(at('07:29:00')) == ['full']))
    # L55: ∞ 30m (Rocket Race join 03:47) + ∞ 1h (Claw step 5, 03:52) → "1h 20m" at ~03:57
    r = Player()
    r.grant(at('03:47:00'), 1800); r.grant(at('03:52:00'), 3600)
    left = r.status(at('03:57:00'))[1] - at('03:57:00')
    out.append(('∞ 30m + 1h = 1h 20m at the L55 home', left == 80 * 60))
    # a level started under ∞ costs nothing even if ∞ ends before the fail (fail.md §2 #1)
    u = Player(); u.grant(at('04:43:00'), 1800)
    u.start(at('04:57:00')); u.finish(at('05:15:42'), won=False)
    out.append(('started under ∞ → 5 Full after the fail', u.status(at('05:15:42')) == ['full']))
    return out


# ---------------------------------------------------------------------------------------------- random scripts
OPS = ['start', 'win', 'loss', 'launch', 'grant', 'refill', 'status']


def script(seed):
    rng = random.Random(seed)
    base_ms = 1_790_300_000_000 + rng.randrange(0, 86_400_000)
    count = rng.choice([5, 5, 5, 4, 3, 2, 1, 0])
    anchor = None
    if count < MAX:
        anchor = float(base_ms // 1000 - rng.randrange(0, 1800))
    until = float(base_ms // 1000 + rng.randrange(60, 7200)) if rng.random() < 0.2 else None
    hw = 0 if rng.random() < 0.3 else base_ms // 1000 - rng.randrange(0, 600)
    coins = rng.choice([0, 500, 900, 1000, 5000])
    p = Player(count, anchor, until, hw, coins)
    init = p.snapshot()
    ops = []
    wall_ms = base_ms
    for _ in range(rng.randrange(30, 60)):
        x = rng.random()
        if x < 0.55:
            wall_ms += rng.randrange(0, 900_000)
        elif x < 0.75:
            wall_ms += rng.randrange(900_000, 7_200_000)
        elif x < 0.80:
            wall_ms += rng.randrange(86_400_000, 3 * 86_400_000)
        elif x < 0.95:
            wall_ms -= rng.randrange(1_000, 7_200_000)                      # the device clock set back
        elif x < 0.98:
            wall_ms -= rng.randrange(2 * 86_400_000, 10 * 86_400_000)       # set back by days
        else:
            wall_ms -= rng.randrange(31 * 86_400_000, 40 * 86_400_000)      # > 30 days: the clock rebases
        op = rng.choices(OPS, weights=[5, 2, 4, 1, 0.35, 0.6, 3])[0]
        wall = wall_ms / 1000.0
        arg = 0
        if op == 'start':
            res = p.start(wall)
        elif op == 'win':
            res = p.finish(wall, won=True)
        elif op == 'loss':
            res = p.finish(wall, won=False)
        elif op == 'launch':
            res = p.launch(wall)
        elif op == 'grant':
            arg = rng.choice([1800, 2700, 3600])
            res = p.grant(wall, arg)
        elif op == 'refill':
            res = p.refill(wall)
        else:
            res = 'ok'
        st = p.status(wall) + [None, None]
        # one compact row per operation (the Swift test reads the same order; ROW below)
        ops.append([op, wall_ms, arg, res, p.count, p.anchor, p.until, p.hw, p.coins, int(p.active), int(p.free),
                    st[0], st[1], st[2]])
    return {'seed': seed, 'init': init, 'ops': ops}


ROW = ['op', 'wallMs', 'arg', 'result', 'count', 'anchor', 'until', 'hw', 'coins', 'active', 'free',
       'status', 'statusA', 'statusB']


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--emit':
        doc = {'_about': 'C3 lives chain: 200 random scripts from Tests/tools/lives_ref.py (regenerate with '
                         'python3 Tests/tools/lives_ref.py --emit Tests/Fixtures/c3_lives_scripts.json)',
               'refillSeconds': REFILL, 'max': MAX, 'refillPrice': REFILL_PRICE, 'row': ROW,
               'scripts': [script(s) for s in range(200)]}
        with open(sys.argv[2], 'w') as f:
            json.dump(doc, f, sort_keys=True, separators=(',', ':'))
            f.write('\n')
        n = sum(len(sc['ops']) for sc in doc['scripts'])
        print('wrote %d scripts, %d operations' % (len(doc['scripts']), n))
        return
    ok = True
    for name, good in self_checks():
        print('%s  %s' % ('ok  ' if good else 'FAIL', name))
        ok &= good
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
