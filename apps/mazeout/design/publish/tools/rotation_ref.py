#!/usr/bin/env python3
"""Arrow Out — weekly event rotation, the FINAL reference (T7 EV-REF; design/publish/events.md §4, PLAN-P §4.1).

The featured events of event-week w are a pure function of w, one constant seed and the tunables in CONFIG: the same
calendar on every device, forever, with no server and no stored table. PathCore's `EventRotation` (C3, package B1) is a
bit-exact port. Its tests read the fixture this script writes (A1 calendar, A3 clock, A4 segmentation) and re-check the
A2 properties on their own plan.

  python3 rotation_ref.py                    # A2 report over 1,043 and 1,044 weeks + the calendar around today
  python3 rotation_ref.py --json [N]         # the fixture for weeks 0..N-1 (default 1044) -> stdout (= the file, byte for byte)
  python3 rotation_ref.py --fixture [PATH]   # write the 1,044-week fixture (default fixtures/rotation_1044.json)
  python3 rotation_ref.py --check [PATH]     # PATH == a fresh regeneration byte for byte, and A2 holds; exit 1 otherwise
  python3 rotation_ref.py --selftest         # hash KATs, two independent generators agree, the published table,
                                             # pins, clamp, negative controls all CAUGHT, a seed sweep; exit 1 on a failure

FINAL choices (T7, 2026-09-28; each one is a tunable in social.json `events.rotation`, the block CONFIG spells out):
  * seed   0x524F544154494F4E ("ROTATION"): a constant, never the install seed (one calendar for everyone, events.md §4.1.2).
  * epoch  1777273200 = Mon 2026-04-27 07:00:00 UTC = week 0 = the EVENT calendar anchor (`EventRules.Calendar.epoch`
           default, socialsim core.EPOCH). It is pinned HERE, on its own, and is NOT the social world epoch: OD9 / ruling 38
           move only the world ("release Monday - 4 weeks", social-intl.md M8), so a slipped release never changes a week.
           Same anchor as every event => the rotation rolls at the same instant as the Claw/Weekly/Streak rolls, and the
           rotation's w is the same number the Claw state keys its week with.
  * pins   {} (OD12 default: no pinned week). A pin replaces one week verbatim and ENTERS the history, so every week after it
           is re-derived: add pins only before a release and regenerate the fixture (weeks before the pin never change).
  * The hash primitives are VENDORED below (a golden reference must not move when design/social is edited); --selftest
    proves them equal to design/social/fixtures/core.json, the KATs the Swift SocialHash is pinned against.

PORTING RULES (Swift, B1):
  1. week(t) = floorDiv(t.seconds - rotation.epoch, 604800) on the rewind-safe SocialTime. plan(w) for w < 0 = plan(0).
  2. Iterate w' = 0...w with the O(1) state (ladderLast, ladderRun, raceLastSingle, raceSingleRun, lastDouble); the three
     draws of week w' are SocialHash.u01(seed, "ladder", w'), u01(seed, "race", w'), u01(seed, "raceDouble", w')
     (stateless: drawing one never shifts another). Every comparison is a strict `<` on doubles.
       ladder: pin | w' has no history -> ladder[0] if u < 0.5 else ladder[1] | ladderRun >= maxRun -> the other
               | u < pSwitch -> the other | else the same.
       race:   pin | w' > 0 and (lastDouble == nil or w' - lastDouble >= doubleMinGap) and ud < pDouble -> DOUBLE
               | no single yet -> race[0] if u < 0.5 else race[1]
               | raceSingleRun >= maxRun or u < pSwitch -> the other single | else the same single.
       A Double week leaves raceLastSingle/raceSingleRun untouched (singles runs skip Double weeks).
  3. Segmentation (events.md §4.4) is per player and never changes the calendar: live(plan, level) below.
  4. rotation.enabled == false (the kill switch, also the compiled default) = the v552 plan: Claw + Rocket + Sky + the two
     always-on events, each behind its own unlock; Balloon Rise never.
"""
import sys, os, json, datetime, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
DEFAULT_FIXTURE = os.path.join(HERE, 'fixtures', 'rotation_1044.json')
FIXTURE_WEEKS = 1044            # weeks 0..1043 = 20 years from the anchor (events.md §8.4 A1)
A2_WEEKS = (1043, 1044)         # A2 is checked over the first 1,043 weeks (PLAN-P T7) and over the whole fixture

# ------------------------------------------------------------------------------------------------ vendored hash primitives
# = design/social/tools/socialsim/core.py (mix, splitmix, fnv1a64, h64, unit, u01) = PathCore SocialHash (bit for bit).
M = (1 << 64) - 1
G = 0x9E3779B97F4A7C15


def _mix(z):
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
    return z ^ (z >> 31)


def _splitmix(x):
    return _mix((x + G) & M)


def _fnv1a64(label):
    h = 0xcbf29ce484222325
    for b in label.encode('utf-8'):
        h ^= b
        h = (h * 0x100000001b3) & M
    return h


def h64(seed, label, *xs):
    h = _splitmix((seed ^ _fnv1a64(label)) & M)
    for x in xs:
        h = _splitmix(h ^ (x & M))
    return h


def unit(h):
    return (h >> 11) * (1.0 / 9007199254740992.0)


def u01(seed, label, *xs):
    return unit(h64(seed, label, *xs))


# ------------------------------------------------------------------------------------------------ the FINAL configuration
WEEK = 604800
EPOCH = 1777273200              # Mon 2026-04-27 07:00:00 UTC (asserted below)
LABELS = ("ladder", "race", "raceDouble")
DOUBLE = "double"               # the race code of a Double Race week (both race events)

# social.json `events.rotation` exactly as it ships (the Swift compiled default differs only in "enabled": false).
CONFIG = {
    "enabled": True,
    "epoch": EPOCH,
    "seed": "0x524F544154494F4E",
    "always": ["streakRace", "weeklyContest"],
    "ladder": ["clawChallenge", "balloonRise"],
    "race": ["rocketRace", "skyJump"],
    "pSwitch": 0.65,
    "pDouble": 0.22,
    "doubleMinGap": 3,
    "maxRun": 2,
    "pins": {},
    "announceCap": 2,
    "teaserHours": 24,
    "notifyWindow": [10, 21],
}
# social.json `unlocks` after B1 (the level a player must have REACHED; events.md §4.2; balloonRise takes the Claw's L33).
UNLOCKS = {"streakRace": 30, "clawChallenge": 33, "balloonRise": 33, "skyJump": 40, "weeklyContest": 50, "rocketRace": 55}

assert EPOCH % 86400 == 7 * 3600, "the anchor must be 07:00 UTC"
assert datetime.datetime.fromtimestamp(EPOCH, datetime.timezone.utc).weekday() == 0, "the anchor must be a Monday"


def floordiv(a, b):
    return a // b               # Python floors; Swift needs a floor-division helper (EventSchedule.floorDiv)


def week_of(t, cfg=CONFIG):
    """Event week of epoch second t (weeks start Monday 07:00 UTC)."""
    return floordiv(int(t) - int(cfg["epoch"]), WEEK)


def week_start(w, cfg=CONFIG):
    return int(cfg["epoch"]) + w * WEEK


class Rotation:
    """The generator as the O(1)-state machine the Swift port copies (PORTING RULES 2)."""

    def __init__(self, cfg=CONFIG):
        self.cfg = cfg
        self.seed = int(cfg["seed"], 16) & M
        self.ladder = tuple(cfg["ladder"])
        self.race = tuple(cfg["race"])
        assert len(self.ladder) == 2 and len(self.race) == 2 and len(set(self.ladder + self.race)) == 4
        self.p_switch = float(cfg["pSwitch"])
        self.p_double = float(cfg["pDouble"])
        self.gap = max(1, int(cfg["doubleMinGap"]))
        self.max_run = max(1, int(cfg["maxRun"]))
        self.pins = {}
        for k, v in cfg.get("pins", {}).items():
            lad, rac = v["ladder"], v["race"]
            if lad not in self.ladder or rac not in self.race + (DOUBLE,):
                raise ValueError("pin %s: unknown pick %r" % (k, v))
            self.pins[int(k)] = (lad, rac)
        self._weeks = []
        self._st = [None, 0, None, 0, None]   # ladderLast, ladderRun, raceLastSingle, raceSingleRun, lastDouble
        self.margins = []                      # |u - threshold| of every generated decision (robustness report)

    @staticmethod
    def _other(x, pair):
        return pair[1] if x == pair[0] else pair[0]

    def _step(self, w):
        lad_last, lad_run, r_last, r_run, last_dbl = self._st
        s = self.seed
        u = u01(s, "ladder", w)
        if w in self.pins:
            lad = self.pins[w][0]
        elif lad_last is None:
            lad = self.ladder[0] if u < 0.5 else self.ladder[1]
            self.margins.append(abs(u - 0.5))
        elif lad_run >= self.max_run:
            lad = self._other(lad_last, self.ladder)
        else:
            lad = self._other(lad_last, self.ladder) if u < self.p_switch else lad_last
            self.margins.append(abs(u - self.p_switch))
        lad_run = lad_run + 1 if lad == lad_last else 1
        lad_last = lad

        u = u01(s, "race", w)
        ud = u01(s, "raceDouble", w)
        if w in self.pins:
            rac = self.pins[w][1]
        else:
            dbl_ok = w > 0 and (last_dbl is None or w - last_dbl >= self.gap)
            if dbl_ok:
                self.margins.append(abs(ud - self.p_double))
            if dbl_ok and ud < self.p_double:
                rac = DOUBLE
            elif r_last is None:
                rac = self.race[0] if u < 0.5 else self.race[1]
                self.margins.append(abs(u - 0.5))
            elif r_run >= self.max_run:
                rac = self._other(r_last, self.race)
            else:
                rac = self._other(r_last, self.race) if u < self.p_switch else r_last
                self.margins.append(abs(u - self.p_switch))
        if rac == DOUBLE:
            last_dbl = w
        else:
            r_run = r_run + 1 if rac == r_last else 1
            r_last = rac
        self._st = [lad_last, lad_run, r_last, r_run, last_dbl]
        return lad, rac

    def weeks(self, n):
        while len(self._weeks) < n:
            self._weeks.append(self._step(len(self._weeks)))
        return self._weeks[:n]

    def plan(self, w):
        """(ladder EventID, race code) of week w; w < 0 is clamped to week 0 (PORTING RULES 1)."""
        w = max(0, w)
        return self.weeks(w + 1)[w]


def race_ids(code, cfg=CONFIG):
    return list(cfg["race"]) if code == DOUBLE else [code]


def live(plan, level, cfg=CONFIG, unlocks=UNLOCKS):
    """Events.md §4.4 segmentation: what THIS player sees in a week with `plan`.
    ladder: the pick from its unlock (both members unlock at L33, so no fallback).
    race:   Double -> each member from its own unlock (L40-54 = Sky only); a single pick the player has not unlocked is
            replaced by the other member if that one is unlocked (a Rocket week shows Sky to L40-54), else nothing."""
    if not cfg.get("enabled", True):
        return live_all_on(level, cfg, unlocks)
    lad, rac = plan
    ladder = lad if level >= unlocks[lad] else None
    if rac == DOUBLE:
        race = [x for x in cfg["race"] if level >= unlocks[x]]
    elif level >= unlocks[rac]:
        race = [rac]
    else:
        o = Rotation._other(rac, tuple(cfg["race"]))
        race = [o] if level >= unlocks[o] else []
    always = [x for x in cfg["always"] if level >= unlocks[x]]
    return {"always": always, "ladder": ladder, "race": race}


def live_all_on(level, cfg=CONFIG, unlocks=UNLOCKS):
    """The kill switch (rotation.enabled == false): the v552 plan. Balloon Rise (not in v552) is never live."""
    lad = cfg["ladder"][0]
    return {"always": [x for x in cfg["always"] if level >= unlocks[x]],
            "ladder": lad if level >= unlocks[lad] else None,
            "race": [x for x in cfg["race"] if level >= unlocks[x]]}


# ------------------------------------------------------------------------------------------------ A2 properties
A2_SPEC = {"maxRun": 2, "doubleMinGap": 3, "ladderShare": (0.40, 0.60), "raceAbsence": 2, "unchangedShare": 0.08}


def _max_run(seq, pred):
    m = c = 0
    for x in seq:
        c = c + 1 if pred(x) else 0
        m = max(m, c)
    return m


def _max_equal_run(seq):
    m = c = 0
    prev = object()
    for x in seq:
        c = c + 1 if x == prev else 1
        prev = x
        m = max(m, c)
    return m


def properties(weeks, cfg=CONFIG):
    """A2 (events.md §8.4) over `weeks` = [(ladder, raceCode)], with the SPEC thresholds (never the config's own values,
    so a mutated config is caught). Returns (measured, failures)."""
    n = len(weeks)
    L = [w[0] for w in weeks]
    R = [w[1] for w in weeks]
    singles = [x for x in R if x != DOUBLE]
    dbl = [i for i, x in enumerate(R) if x == DOUBLE]
    gaps = [b - a for a, b in zip(dbl, dbl[1:])]
    lad0, lad1 = cfg["ladder"]
    rk, sk = cfg["race"]
    m = {
        "weeks": n,
        "ladderMaxRun": _max_equal_run(L),
        "racePickMaxRun": _max_equal_run(R),
        "raceSingleMaxRun": _max_equal_run(singles),
        "doubleWeeks": len(dbl),
        "doubleShare": round(len(dbl) / n, 6),
        "doubleMinGap": min(gaps) if gaps else None,
        "doubleMaxGap": max(gaps) if gaps else None,
        "ladderShare": {lad0: round(L.count(lad0) / n, 6), lad1: round(L.count(lad1) / n, 6)},
        "ladderMaxAbsence": {lad0: _max_run(L, lambda x: x != lad0), lad1: _max_run(L, lambda x: x != lad1)},
        "raceShare": {rk: round(R.count(rk) / n, 6), sk: round(R.count(sk) / n, 6), DOUBLE: round(len(dbl) / n, 6)},
        "raceMaxAbsence": {rk: _max_run(R, lambda x: x == sk), sk: _max_run(R, lambda x: x == rk)},
        "raceMaxPresence": {rk: _max_run(R, lambda x: x != sk), sk: _max_run(R, lambda x: x != rk)},
        "unchangedWeeks": sum(1 for i in range(1, n) if weeks[i] == weeks[i - 1]),
    }
    m["unchangedShare"] = round(m["unchangedWeeks"] / (n - 1), 6)
    f = []
    s = A2_SPEC
    if m["ladderMaxRun"] > s["maxRun"]:
        f.append("ladder max run %d > %d" % (m["ladderMaxRun"], s["maxRun"]))
    if m["racePickMaxRun"] > s["maxRun"]:
        f.append("race pick max run %d > %d" % (m["racePickMaxRun"], s["maxRun"]))
    if m["raceSingleMaxRun"] > s["maxRun"]:
        f.append("race single max run (Double weeks skipped) %d > %d" % (m["raceSingleMaxRun"], s["maxRun"]))
    if m["doubleMinGap"] is not None and m["doubleMinGap"] < s["doubleMinGap"]:
        f.append("Double gap %d < %d" % (m["doubleMinGap"], s["doubleMinGap"]))
    for k, v in m["ladderShare"].items():
        if not (s["ladderShare"][0] <= v <= s["ladderShare"][1]):
            f.append("ladder share %s %.3f outside %s" % (k, v, s["ladderShare"]))
    for k, v in m["raceMaxAbsence"].items():
        if v > s["raceAbsence"]:
            f.append("race event %s absent %d weeks > %d" % (k, v, s["raceAbsence"]))
    if m["unchangedShare"] > s["unchangedShare"]:
        f.append("unchanged weeks %.3f > %.2f" % (m["unchangedShare"], s["unchangedShare"]))
    return m, f


# ------------------------------------------------------------------------------------------------ the fixture
SEG_LEVELS = (1, 29, 30, 32, 33, 39, 40, 45, 49, 50, 54, 55, 60, 500)


def _dump(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fixture_text(n=FIXTURE_WEEKS, cfg=CONFIG):
    """Deterministic text: fixed key order, one row per line, no timestamps, LF, a final newline."""
    rot = Rotation(cfg)
    wk = rot.weeks(n)
    seed = rot.seed
    hash_kat = []
    for label in LABELS:
        for w in (0, 1, 22, 23, 1043):
            h = h64(seed, label, w)
            hash_kat.append({"label": label, "w": w, "h64": str(h), "unit": repr(unit(h))})
    clock = []
    for t in (EPOCH - WEEK - 1, EPOCH - 1, EPOCH, EPOCH + WEEK - 1, EPOCH + WEEK,
              week_start(22) - 1, week_start(22), week_start(23) - 1, week_start(1043), week_start(1044) - 1):
        clock.append({"t": t, "week": week_of(t, cfg)})
    combos = [(lad, rac) for lad in cfg["ladder"] for rac in list(cfg["race"]) + [DOUBLE]]
    seg = []
    for lad, rac in combos:
        for lv in SEG_LEVELS:
            seg.append({"ladder": lad, "race": race_ids(rac, cfg), "level": lv, "live": live((lad, rac), lv, cfg)})
    all_on = [{"level": lv, "live": live_all_on(lv, cfg)} for lv in SEG_LEVELS]
    clamp = {"weeks": [-1, -52], "plan": {"ladder": wk[0][0], "race": race_ids(wk[0][1], cfg)}}
    header = [
        ("_about", "Arrow Out weekly event rotation: the golden calendar for weeks 0..%d (events.md §4 + §8.4 A1/A3/A4). "
                   "Generated by design/publish/tools/rotation_ref.py --fixture; never edit by hand. A pin or tunable "
                   "change = regenerate + re-pin the Swift test." % (n - 1)),
        ("config", cfg),
        ("unlocks", UNLOCKS),
        ("weekSeconds", WEEK),
        ("weekCount", n),
        ("hashKAT", hash_kat),
        ("clockKAT", clock),
        ("clamp", clamp),
        ("allOn", all_on),
    ]
    out = ["{"]
    for k, v in header:
        out.append("%s:%s," % (_dump(k), _dump(v)))
    out.append('"segmentation":[')
    out.append(",\n".join(_dump(r) for r in seg))
    out.append("],")
    out.append('"weeks":[')
    out.append(",\n".join(_dump({"w": i, "start": week_start(i, cfg), "ladder": lad, "race": race_ids(rac, cfg)})
                          for i, (lad, rac) in enumerate(wk)))
    out.append("]")
    out.append("}")
    return "\n".join(out) + "\n"


def weeks_from_fixture(obj):
    """[(ladder, raceCode)] from a parsed fixture."""
    res = []
    for i, r in enumerate(obj["weeks"]):
        assert r["w"] == i
        res.append((r["ladder"], DOUBLE if len(r["race"]) == 2 else r["race"][0]))
    return res


# ------------------------------------------------------------------------------------------------ an independent oracle
def oracle_weeks(n, cfg=CONFIG):
    """The rules re-implemented from the prose of events.md §4.3 over the full history (O(n^2), no shared code with
    Rotation except the hash). --selftest requires both to agree for the default and several mutated configs."""
    seed = int(cfg["seed"], 16)
    LAD, RAC = tuple(cfg["ladder"]), tuple(cfg["race"])
    ps, pd = float(cfg["pSwitch"]), float(cfg["pDouble"])
    gap, mr = max(1, int(cfg["doubleMinGap"])), max(1, int(cfg["maxRun"]))
    pins = {int(k): (v["ladder"], v["race"]) for k, v in cfg.get("pins", {}).items()}
    lad, rac = [], []
    for w in range(n):
        if w in pins:
            lad.append(pins[w][0]); rac.append(pins[w][1]); continue
        u = u01(seed, "ladder", w)
        if not lad:
            lad.append(LAD[0] if u < 0.5 else LAD[1])
        else:
            tail = lad[-mr:]
            same_run = len(tail) == mr and all(x == lad[-1] for x in tail)
            flip = LAD[1] if lad[-1] == LAD[0] else LAD[0]
            lad.append(flip if (same_run or u < ps) else lad[-1])
        u = u01(seed, "race", w)
        ud = u01(seed, "raceDouble", w)
        window = rac[max(0, w - (gap - 1)):w]
        if w > 0 and DOUBLE not in window and ud < pd:
            rac.append(DOUBLE); continue
        singles = [x for x in rac if x != DOUBLE]
        if not singles:
            rac.append(RAC[0] if u < 0.5 else RAC[1]); continue
        run = 0
        for x in reversed(singles):
            if x != singles[-1]:
                break
            run += 1
        flip = RAC[1] if singles[-1] == RAC[0] else RAC[0]
        rac.append(flip if (run >= mr or u < ps) else singles[-1])
    return list(zip(lad, rac))


# ------------------------------------------------------------------------------------------------ self-test
# events.md §4.3's published table (weeks 22-35), which the owner-facing docs quote.
PUBLISHED = {22: ("balloonRise", DOUBLE), 23: ("clawChallenge", "skyJump"), 24: ("balloonRise", "skyJump"),
             25: ("balloonRise", DOUBLE), 26: ("clawChallenge", "rocketRace"), 27: ("balloonRise", "skyJump"),
             28: ("clawChallenge", DOUBLE), 29: ("balloonRise", "rocketRace"), 30: ("clawChallenge", "skyJump"),
             31: ("balloonRise", DOUBLE), 32: ("clawChallenge", "skyJump"), 33: ("balloonRise", "rocketRace"),
             34: ("clawChallenge", "rocketRace"), 35: ("balloonRise", "skyJump")}


def _cfg(**kw):
    c = json.loads(json.dumps(CONFIG))
    c.update(kw)
    return c


def selftest(verbose=True):
    fails = []
    notes = []

    def ok(cond, msg):
        if not cond:
            fails.append(msg)
        return cond

    # 1. vendored hash == the KATs the Swift SocialHash is pinned against (design/social/fixtures/core.json)
    core_path = os.path.join(APP, 'design', 'social', 'fixtures', 'core.json')
    try:
        core = json.load(open(core_path))
        k = 0
        for e in core["h64"]:
            h = h64(int(e["seed"]), e["label"], *[int(x) for x in e["xs"]])
            ok(str(h) == e["h64"], "h64 KAT %r" % e)
            ok(repr(unit(h)) == e["unit"], "unit KAT %r" % e)
            k += 1
        notes.append("hash: %d core.json KATs equal (the Swift SocialGoldenTests pins)" % k)
    except (OSError, KeyError, ValueError) as ex:
        fails.append("core.json KATs unreadable: %s" % ex)
    try:                                   # soft cross-check against the live social sim (it may be mid-edit by T6)
        sys.path.insert(0, os.path.join(APP, 'design', 'social', 'tools'))
        from socialsim import core as sc   # noqa: E402
        same = all(sc.u01(s, l, w) == u01(s, l, w) for s in (0, 1, int(CONFIG["seed"], 16))
                   for l in LABELS for w in (0, 1, 7, 22, 1043, -1))
        ok(same, "vendored u01 != socialsim.core.u01")
        notes.append("socialsim.core.u01 cross-check %s; core.EPOCH %s the rotation anchor (mod week %s)" % (
            "equal" if same else "DIFFERENT", "==" if sc.EPOCH == EPOCH else "!=",
            "equal" if (sc.EPOCH - EPOCH) % WEEK == 0 else "DIFFERENT"))
        if (sc.EPOCH - EPOCH) % WEEK != 0:
            fails.append("socialsim core.EPOCH is no longer a Monday 07:00 UTC week boundary")
    except Exception as ex:                # noqa: BLE001
        notes.append("socialsim.core cross-check skipped (%s)" % ex.__class__.__name__)

    # 2. two independent generators agree (default + mutated configs + pins)
    variants = {
        "default": CONFIG,
        "gap1": _cfg(doubleMinGap=1), "gap2": _cfg(doubleMinGap=2), "gap5": _cfg(doubleMinGap=5),
        "maxRun1": _cfg(maxRun=1), "maxRun3": _cfg(maxRun=3), "pSwitch0.3": _cfg(pSwitch=0.3),
        "pDouble0.5": _cfg(pDouble=0.5), "seed+1": _cfg(seed=hex(int(CONFIG["seed"], 16) + 1)),
        "pins": _cfg(pins={"0": {"ladder": "balloonRise", "race": DOUBLE},
                           "23": {"ladder": "clawChallenge", "race": DOUBLE},
                           "24": {"ladder": "clawChallenge", "race": "rocketRace"}}),
    }
    for name, c in variants.items():
        a = Rotation(c).weeks(FIXTURE_WEEKS)
        b = oracle_weeks(FIXTURE_WEEKS, c)
        ok(a == b, "state machine != oracle for %s (first diff at week %s)" % (
            name, next((i for i in range(len(a)) if a[i] != b[i]), None)))
    notes.append("state machine == history oracle for %d configs x %d weeks" % (len(variants), FIXTURE_WEEKS))

    # 3. the published events.md §4.3 table
    rot = Rotation()
    wk = rot.weeks(FIXTURE_WEEKS)
    for w, p in PUBLISHED.items():
        ok(wk[w] == p, "week %d = %s, events.md §4.3 says %s" % (w, wk[w], p))
    notes.append("events.md §4.3 table (weeks 22-35) reproduced")

    # 4. pins: used verbatim, weeks before the pin unchanged, the history rules resume after it
    pc = variants["pins"]
    pw = Rotation(pc).weeks(60)
    ok(pw[0] == ("balloonRise", DOUBLE) and pw[23] == ("clawChallenge", DOUBLE) and pw[24] == ("clawChallenge", "rocketRace"),
       "pins not applied verbatim")
    p1 = Rotation(_cfg(pins={"30": {"ladder": "clawChallenge", "race": "skyJump"}})).weeks(60)
    ok(p1[:30] == wk[:30], "a pin changed a week before it")
    try:
        Rotation(_cfg(pins={"5": {"ladder": "streakRace", "race": "skyJump"}}))
        fails.append("an invalid pin was accepted")
    except ValueError:
        pass
    notes.append("pins: verbatim, earlier weeks untouched, invalid pick refused")

    # 5. clamp, clock, kill switch
    ok(rot.plan(-1) == wk[0] and rot.plan(-52) == wk[0], "w < 0 is not clamped to week 0")
    ok(week_of(EPOCH - 1) == -1 and week_of(EPOCH) == 0 and week_of(week_start(22)) == 22
       and week_of(week_start(22) - 1) == 21, "week_of boundaries")
    ok(datetime.datetime.fromtimestamp(week_start(22), datetime.timezone.utc).strftime("%a %Y-%m-%d %H:%M") ==
       "Mon 2026-09-28 07:00", "week 22 must start Mon 2026-09-28 07:00 UTC")
    off = _cfg(enabled=False)
    ok(all(live(p, lv, off)["ladder"] != "balloonRise" for p in set(wk) for lv in SEG_LEVELS), "kill switch shows Balloon")
    ok(live(wk[25], 45) == {"always": ["streakRace"], "ladder": "balloonRise", "race": ["skyJump"]}, "A4: L45 Double -> Sky only")
    ok(live(("clawChallenge", "rocketRace"), 45)["race"] == ["skyJump"], "A4: L45 Rocket week -> Sky")
    ok(live(("clawChallenge", "rocketRace"), 35) == {"always": ["streakRace"], "ladder": "clawChallenge", "race": []},
       "A4: L35 -> ladder only")
    ok(live(("clawChallenge", "rocketRace"), 60)["race"] == ["rocketRace"], "A4: L60 follows the calendar")
    ok(live(("balloonRise", DOUBLE), 60)["race"] == ["rocketRace", "skyJump"], "A4: L60 Double -> both")
    notes.append("clamp, clock boundaries, kill switch, A4 segmentation examples")

    # 6. A2 holds on the default over 1,043 and 1,044 weeks; decision margins
    for n in A2_WEEKS:
        m, f = properties(wk[:n])
        ok(not f, "A2 over %d weeks: %s" % (n, f))
    mm = min(rot.margins)
    ok(mm > 1e-9, "a decision sits within 1e-9 of its threshold (%.3g): a 1-ulp JSON parse could flip it" % mm)
    notes.append("A2 holds over %s weeks; smallest |u - threshold| over %d decisions = %.3g" % (
        "/".join(map(str, A2_WEEKS)), len(rot.margins), mm))

    # 7. negative controls: every mutation is CAUGHT (A2 checker or the golden fixture)
    golden = wk
    muts = {
        "maxRun rule dropped": ("a2", _cfg(maxRun=10 ** 6)),
        "Double gap 3 -> 1": ("a2", _cfg(doubleMinGap=1)),
        "pSwitch 0.65 -> 0.05": ("a2", _cfg(pSwitch=0.05)),
        "epoch = world epoch 2026-09-07 (OD9)": ("golden", _cfg(epoch=EPOCH + 19 * WEEK)),
        "label typo raceDouble -> racedouble": ("golden", None),
        "draws keyed w+1": ("golden", None),
        "seed + 1": ("golden", _cfg(seed=hex(int(CONFIG["seed"], 16) + 1))),
        "pDouble 0.22 -> 0.20": ("golden", _cfg(pDouble=0.20)),
    }
    caught = 0
    for name, (how, c) in muts.items():
        if name.startswith("label typo"):
            class R(Rotation):
                def _step(self, w):
                    global u01
                    real = u01
                    u01 = lambda s, l, *x: real(s, "racedouble" if l == "raceDouble" else l, *x)  # noqa: E731
                    try:
                        return Rotation._step(self, w)
                    finally:
                        u01 = real
            got, cfg_used = R().weeks(FIXTURE_WEEKS), CONFIG
        elif name.startswith("draws keyed"):
            class R2(Rotation):
                def _step(self, w):
                    global u01
                    real = u01
                    u01 = lambda s, l, *x: real(s, l, *[v + 1 for v in x])  # noqa: E731
                    try:
                        return Rotation._step(self, w)
                    finally:
                        u01 = real
            got, cfg_used = R2().weeks(FIXTURE_WEEKS), CONFIG
        else:
            got, cfg_used = Rotation(c).weeks(FIXTURE_WEEKS), c
        if how == "a2":
            hit = bool(properties(got[:A2_WEEKS[0]], cfg_used)[1])
        else:
            text = fixture_text(FIXTURE_WEEKS, cfg_used) if name.startswith("epoch") else None
            hit = (got != golden) or (text is not None and text != fixture_text())
        ok(hit, "negative control NOT caught: %s" % name)
        caught += hit
    notes.append("negative controls %d/%d CAUGHT" % (caught, len(muts)))

    # 8. byte-identical twice in-process (the cross-process check is --check / the evidence script)
    a, b = fixture_text(), fixture_text()
    ok(a == b, "fixture text differs between two in-process runs")

    # 9. seed sweep (information: which A2 properties hold by construction, which are statistical)
    struct_fail = stat_fail = 0
    seeds = 200
    for i in range(seeds):
        c = _cfg(seed=hex(h64(0x5EED, "sweep", i)))
        m, f = properties(Rotation(c).weeks(A2_WEEKS[0]), c)
        if any(("run" in x) or ("gap" in x) or ("absent" in x) for x in f):
            struct_fail += 1
        if any(("share" in x) or ("unchanged" in x) for x in f):
            stat_fail += 1
    ok(struct_fail == 0, "a structural A2 property failed for %d/%d random seeds" % (struct_fail, seeds))
    notes.append("seed sweep: structural A2 (runs, gap, absence) held for %d/%d seeds; statistical A2 (shares, "
                 "unchanged) failed for %d/%d seeds (the shipped seed passes)" % (seeds - struct_fail, seeds, stat_fail, seeds))

    if verbose:
        for n_ in notes:
            print("  ok  " + n_)
        for f_ in fails:
            print("  FAIL " + f_)
        print("selftest: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
    return not fails


# ------------------------------------------------------------------------------------------------ CLI
def _report():
    rot = Rotation()
    wk = rot.weeks(FIXTURE_WEEKS)
    for n in A2_WEEKS:
        m, f = properties(wk[:n])
        print("A2 over %d weeks: %s" % (n, "PASS" if not f else "FAIL " + "; ".join(f)))
        print("   " + _dump(m))
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    w0 = week_of(now)
    for w in range(max(0, w0 - 1), w0 + 18):
        lad, rac = rot.plan(w)
        start = datetime.datetime.fromtimestamp(week_start(w), datetime.timezone.utc)
        print("week %4d  %s  ladder %-13s race %s%s" % (w, start.strftime("%a %Y-%m-%d %H:%M UTC"), lad,
                                                        "+".join(race_ids(rac)), "   <- now" if w == w0 else ""))


def main(argv):
    if len(argv) >= 2 and argv[1] == "--json":
        n = int(argv[2]) if len(argv) >= 3 else FIXTURE_WEEKS
        sys.stdout.write(fixture_text(n))
        return 0
    if len(argv) >= 2 and argv[1] == "--fixture":
        path = argv[2] if len(argv) >= 3 else DEFAULT_FIXTURE
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = fixture_text().encode("ascii")
        with open(path, "wb") as fh:
            fh.write(data)
        print("wrote %s (%d bytes, sha256 %s)" % (path, len(data), hashlib.sha256(data).hexdigest()))
        return 0
    if len(argv) >= 2 and argv[1] == "--check":
        path = argv[2] if len(argv) >= 3 else DEFAULT_FIXTURE
        with open(path, "rb") as fh:
            have = fh.read()
        want = fixture_text().encode("ascii")
        bad = []
        if have != want:
            bad.append("fixture != regeneration (sha256 %s vs %s)" % (hashlib.sha256(have).hexdigest(),
                                                                       hashlib.sha256(want).hexdigest()))
        wk = weeks_from_fixture(json.loads(have))
        for n in A2_WEEKS:
            m, f = properties(wk[:n])
            bad += ["A2/%d: %s" % (n, x) for x in f]
            print("A2 over %d weeks: %s  %s" % (n, "PASS" if not f else "FAIL", _dump(m)))
        print("fixture sha256 %s: %s" % (hashlib.sha256(have).hexdigest(), "OK" if not bad else "; ".join(bad)))
        return 0 if not bad else 1
    if len(argv) >= 2 and argv[1] == "--selftest":
        return 0 if selftest() else 1
    _report()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
