#!/usr/bin/env python3
"""Arrow Out — "Up & Away" (EventID "balloonRise"), the reference state machine + its golden trace (B1 EVENTS-P).

RULES SOURCE: build/p/PH0/balloon.md (PH-0b, the ORIGINAL's v582 event recorded on the owner's phone, 2026-09-28 01:26-02:48
TRT; VERIFIED rows are marked there). It REPLACES T7's model of design/publish/events.md §5 (10 steps of puffs, 3 balloons, a
fall to the step start), which was inferred before the phone capture existed: T7's script and trace are kept in
build/p/B1/t7/ (balloon_ref.section5.py, balloon_trace.section5.json) for the record. SPEC.md ruling 42(c) (contract amend 4)
fixed the outcome shapes to these rules. PathCore C3 (`Events/BalloonRise.swift`) is a bit-exact port; its tests read the
fixture this script writes (events.md §8.4 A6).

  python3 balloon_ref.py                     # print the main trace in a readable form
  python3 balloon_ref.py --fixture [PATH]    # write fixtures/balloon_trace.json
  python3 balloon_ref.py --check [PATH]      # PATH == regeneration byte for byte; exit 1 otherwise
  python3 balloon_ref.py --selftest          # invariants, the v582 rows re-played, negative controls CAUGHT

THE RULES (balloon.md §0, §4, §5; VERIFIED unless marked):
  * ONE counter: levels won in a row ("streak"). Each counted win adds +1, whatever the tag (a Super Hard win gave +1).
  * ANY failed level (Level Failed by time or hearts, Quit, a killed app — the same losses that reset the multiplier) resets it
    to 0 — from 3 AND from 1 (VERIFIED), past checkpoints do not protect it. A paid continue is not a failed level: it never
    reaches the loss hook, so the counter is kept (balloon.md §5: UNKNOWN on the phone, INFERRED yes; the multiplier works the
    same way, VERIFIED).
  * 10 platforms at 2, 5, 8, 13, 20, 28, 36, 46, 77, 120 wins in a row. Each chest pays ONCE per event: reaching 2 again after
    a reset paid nothing (VERIFIED coins 8718 -> 8738 = the level's +20 only). The reward table is the phone's (§4); platform 1's
    content was never shown (already claimed): coins INFERRED from the open coin-chest art, 50 = DECISION (below platform 4's
    100, the table's smallest coin prize).
  * No rivals. The Profile's 7th tile is the best streak ever reached ("max streak", VERIFIED 3 after the session's best run):
    `best` survives the weekly roll.
  * Paying the last platform (120 in a row) completes the event: wins["balloonRise"] += 1 (like the Claw's ladder). The counter
    keeps counting past 120 (goal nil); nothing more is paid until the next event.
  * The event runs for one event week (Monday 07:00 UTC; balloon.md §6 VERIFIED the end at the weekly reset) in the rotation's
    ladder slot (rotation_ref.py). The roll ends the week: streak and paid platforms reset, claims already earned stay claims,
    `best` stays. Unlock L33 (DECISION: the Claw's; UNKNOWN on the phone, balloon.md §6).
  * Joined on a home visit (Events.refresh) or by the first counted win of the week. A won level counts when its number >= the
    unlock (EventSchedule.counts); liveness uses the player's reached level (the rotation's segmentation).
  * The "fall" page (balloon.md §5, VERIFIED once from 3; NOT shown from 1): inserted into the fail flow after the last band
    step when the lost streak >= `fallPageMinStreak` = 2. DECISION: the two readings the phone left open ("a checkpoint was
    passed" / "the streak was >= 2") coincide, because platform 1 sits at 2.
  * The fail chain's bands carry NO balloon wording (VERIFIED: "No balloon wording on either band"): step B keeps the multiplier
    lines; in an Up & Away week the Claw is not live, so its token line is not shown.
"""
import sys, os, json, copy, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rotation_ref as rot  # noqa: E402

APP = rot.APP
PH0B = os.path.join(APP, 'build', 'p', 'PH0', 'balloon.md')
RULES_SOURCE = "build/p/PH0/balloon.md (PH-0b, the v582 phone capture)"
DEFAULT_FIXTURE = os.path.join(HERE, 'fixtures', 'balloon_trace.json')
EVENT = "balloonRise"

# social.json `events.balloonRise` (C3's layout, next to `events.rotation`); the grant shape is rules.json's (Grant §15):
# "hint" = the bulb, "freeze" = the hourglass (balloon.md §4: "the same icon as the in-level booster at the bottom left").
RULES = {
    "platforms": [
        {"at": 2, "grant": {"coins": 50}},
        {"at": 5, "grant": {"unlimitedLives": 900}},
        {"at": 8, "grant": {"boosters": {"hint": 1}}},
        {"at": 13, "grant": {"coins": 100}},
        {"at": 20, "grant": {"boosters": {"freeze": 1}, "unlimitedLives": 900}},
        {"at": 28, "grant": {"coins": 150, "unlimitedLives": 900}},
        {"at": 36, "grant": {"boosters": {"hint": 1}, "unlimitedLives": 1800}},
        {"at": 46, "grant": {"coins": 500, "unlimitedLives": 3600}},
        {"at": 77, "grant": {"boosters": {"freeze": 1}, "unlimitedLives": 3600}},
        {"at": 120, "grant": {"boosters": {"freeze": 1, "hint": 1}, "coins": 1200, "unlimitedLives": 3600}},
    ],
    "fallPageMinStreak": 2,
}
UNLOCK = rot.UNLOCKS[EVENT]


def empty(best=0):
    """Not joined this week (also what an old save decodes to, with best 0)."""
    return {"week": None, "streak": 0, "paid": 0, "best": best}


def grant_value(g):
    return (g.get("coins", 0), g.get("unlimitedLives", 0), sum(g.get("boosters", {}).values()))


class Player:
    """One player's Up & Away state + what it earned (claims, wins). Pure: every hook takes the event week explicitly."""

    def __init__(self, rules=RULES, rotation=None):
        self.r = rules
        self.rot = rotation or rot.Rotation()
        self.s = empty()
        self.claims = []
        self.wins = 0

    def n(self):
        return len(self.r["platforms"])

    def at(self, i):
        return self.r["platforms"][i]["at"]

    def is_live(self, w, level):
        """The rotation's ladder pick for this player (rot.live: kill switch + segmentation)."""
        return rot.live(self.rot.plan(w), level, self.rot.cfg)["ladder"] == EVENT

    def goal(self, total):
        """The next platform's count above `total` (nil after the last)."""
        for p in self.r["platforms"]:
            if p["at"] > total:
                return p["at"]
        return None

    def roll(self, w):
        if self.s["week"] is not None and self.s["week"] != w:
            self.s = empty(self.s["best"])

    def join(self, w):
        if self.s["week"] is None:
            self.s = {"week": w, "streak": 0, "paid": 0, "best": self.s["best"]}

    # -- hooks (Events.refresh / onWin / onLoss)
    def refresh(self, w, level):
        self.roll(w)
        if self.is_live(w, level):
            self.join(w)
        return []

    def win(self, w, won_level, player_level, tag):
        self.roll(w)
        if not self.is_live(w, player_level) or won_level < UNLOCK:
            return []
        self.join(w)
        s = self.s
        s["streak"] += 1
        s["best"] = max(s["best"], s["streak"])
        steps = []
        while s["paid"] < self.n() and s["streak"] >= self.at(s["paid"]):
            s["paid"] += 1
            grant = copy.deepcopy(self.r["platforms"][s["paid"] - 1]["grant"])
            self.claims.append({"event": EVENT, "kind": "balloonStep", "step": s["paid"], "week": s["week"], "grant": grant})
            steps.append({"balloonStep": {"step": s["paid"], "reward": grant}})
            if s["paid"] == self.n():
                self.wins += 1
        o = {"added": 1, "total": s["streak"]}
        g = self.goal(s["streak"])
        if g is not None:
            o["goal"] = g
        return [{"balloonStreak": o}] + steps

    def loss(self, w):
        self.roll(w)
        s = self.s
        if s["week"] != w or s["streak"] <= 0:
            return []
        frm = s["streak"]
        s["streak"] = 0
        return [{"balloonFell": {"from": frm}}]

    # -- reads (Events.status / the fail flow), side-effect free
    def fall_page(self, out):
        """The fail flow inserts the fall page after the last band step when the lost streak was >= fallPageMinStreak."""
        for o in out:
            if "balloonFell" in o:
                return o["balloonFell"]["from"] >= self.r["fallPageMinStreak"]
        return False

    def bar(self, w):
        s = self.s
        if s["week"] != w:
            return None
        g = self.goal(s["streak"])
        nxt = None                      # the goal platform's reward while it is unpaid (the bar's right end)
        if g is not None:
            i = [p["at"] for p in self.r["platforms"]].index(g)
            if i >= s["paid"]:
                nxt = self.r["platforms"][i]["grant"]
        return {"streak": s["streak"], "goal": g, "paid": s["paid"], "complete": s["paid"] >= self.n(), "nextReward": nxt}


# ------------------------------------------------------------------------------------------------ the scripted traces
def _t(w, minutes):
    return rot.week_start(w) + minutes * 60


def main_script():
    """One player from L40 through weeks 22 (Up & Away) -> 23 (Treasure Climb) -> 24, 25 (Up & Away twice).
    Each op: (kind, week, minute, level, tag); level = the won level for a win (the player then reaches level + 1), the
    player's level otherwise. Covers: platform 1 paid; a fail from 2 (fall page); 2 again pays nothing; a paid continue keeps
    the counter; a fail from 1 (no fall page); a 122-win run paying platforms 2..10 (completion, goal nil past 120); the roll
    into a Claw week (state reset, best kept, hooks inert); a new Up & Away week pays platform 1 again; a second roll."""
    ops = [("refresh", 22, 10, 40, None),
           ("win", 22, 20, 40, "superHard"),          # 1
           ("win", 22, 30, 41, "normal"),             # 2 -> platform 1 (50 coins)
           ("loss", 22, 40, 42, None),                # fell from 2: the fall page
           ("win", 22, 50, 42, "hard"),               # 1
           ("win", 22, 60, 43, "normal"),             # 2 again: already paid, nothing
           ("win", 22, 70, 44, "normal"),             # 3
           ("continue", 22, 80, 45, None),            # a paid continue: nothing changes
           ("win", 22, 90, 45, "normal"),             # 4
           ("win", 22, 100, 46, "hard"),              # 5 -> platform 2 (inf 15m)
           ("loss", 22, 110, 47, None),               # fell from 5
           ("win", 22, 120, 47, "normal"),            # 1
           ("loss", 22, 130, 48, None)]               # fell from 1: no fall page
    lv, m = 48, 140
    tags = ["normal", "hard", "normal", "superHard", "normal"]
    for i in range(122):                           # 1 .. 122: platforms 2 (already paid), 3 .. 10, then past the top
        ops.append(("win", 22, m, lv, tags[i % len(tags)]))
        lv += 1; m += 10
    ops += [("loss", 22, m, lv, None),                          # fell from 122
            ("refresh", 23, 10, lv, None),                      # Treasure Climb week: rolled, not live
            ("win", 23, 20, lv, "hard"), ("loss", 23, 30, lv + 1, None),
            ("win", 24, 10, lv + 1, "normal"),                  # joins by the counted win, 1
            ("win", 24, 20, lv + 2, "normal"),                  # 2 -> platform 1 pays again (a new event)
            ("refresh", 25, 10, lv + 3, None),                  # the second Up & Away week in a row restarts
            ("win", 25, 20, lv + 3, "superHard")]
    return ops


def gate_script():
    """A player reaching the unlock during an Up & Away week: the L32 win counts nothing, the L33 home joins."""
    return [("refresh", 22, 10, 32, None), ("win", 22, 20, 32, "hard"), ("loss", 22, 30, 33, None),
            ("refresh", 22, 40, 33, None), ("win", 22, 50, 33, "normal"), ("win", 22, 60, 34, "normal")]


def kill_switch_script():
    """rotation.enabled == false (the compiled default, and the v552 plan under -pc.uitest / -pc.capture): never live."""
    return [("refresh", 22, 10, 60, None), ("win", 22, 20, 60, "normal"), ("win", 22, 30, 61, "normal"),
            ("loss", 22, 40, 62, None)]


def _apply(p, op, level_box):
    kind, w, minute, level, tag = op
    if kind == "refresh":
        level_box[0] = max(level_box[0], level)
        return p.refresh(w, level_box[0])
    if kind == "win":
        level_box[0] = max(level_box[0], level + 1)
        return p.win(w, level, level_box[0], tag)
    if kind == "loss":
        level_box[0] = max(level_box[0], level)
        return p.loss(w)
    if kind == "continue":             # a paid continue never reaches onLoss: nothing changes
        return []
    raise ValueError(kind)


def run(ops, rules=RULES, cfg=rot.CONFIG):
    p = Player(rules, rot.Rotation(cfg))
    rows = []
    lv = [0]
    for op in ops:
        kind, w, minute, level, tag = op
        out = _apply(p, op, lv)
        row = {"op": kind, "w": w, "t": _t(w, minute), "level": level, "reached": lv[0], "out": out,
               "state": dict(p.s), "bar": p.bar(w), "claims": len(p.claims), "wins": p.wins,
               "live": p.is_live(w, lv[0])}
        if kind == "loss":
            row["fallPage"] = p.fall_page(out)
        if tag is not None:
            row["tag"] = tag
        rows.append(row)
    return rows, p


# ------------------------------------------------------------------------------------------------ fixture
def _dump(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fixture_text(rules=RULES):
    off = dict(copy.deepcopy(rot.CONFIG), enabled=False)
    traces = [("main", rules, rot.CONFIG, main_script()), ("gate", rules, rot.CONFIG, gate_script()),
              ("killSwitch", rules, off, kill_switch_script())]
    out = ["{"]
    out.append('"_about":%s,' % _dump(
        "Arrow Out Up & Away (balloonRise) golden traces (events.md §8.4 A6, re-derived from the v582 phone rules). Generated "
        "by design/publish/tools/balloon_ref.py --fixture; never edit by hand. Each row = the hook, its outcomes "
        "(EventOutcome's Codable shape), the state after it, the home bar, the claim/win counts, liveness and, for a loss, "
        "whether the fail flow inserts the fall page."))
    out.append('"rulesSource":%s,' % _dump(RULES_SOURCE))
    out.append('"rules":%s,' % _dump(rules))
    out.append('"unlock":%d,' % UNLOCK)
    out.append('"rotationFixtureWeeks":%s,' % _dump({str(w): {"ladder": rot.Rotation().plan(w)[0],
                                                           "race": rot.race_ids(rot.Rotation().plan(w)[1])}
                                                       for w in (22, 23, 24, 25)}))
    for i, (name, r, cfg, ops) in enumerate(traces):
        rows, p = run(ops, r, cfg)
        out.append('%s:{"enabled":%s,"claims":%s,"rows":[' % (_dump(name), _dump(bool(cfg["enabled"])), _dump(p.claims)))
        out.append(",\n".join(_dump(x) for x in rows))
        out.append("]}" + ("," if i < len(traces) - 1 else ""))
    out.append("}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------------------------------------ self-test
def selftest():
    fails, notes = [], []

    def ok(c, m):
        if not c:
            fails.append(m)

    plat = RULES["platforms"]
    ok([p["at"] for p in plat] == [2, 5, 8, 13, 20, 28, 36, 46, 77, 120], "platform counts != balloon.md §4")
    phone = [None, (0, 900, 0), (0, 0, 1), (100, 0, 0), (0, 900, 1), (150, 900, 0), (0, 1800, 1), (500, 3600, 0),
             (0, 3600, 1), (1200, 3600, 2)]
    ok(all(ph is None or grant_value(p["grant"]) == ph for p, ph in zip(plat, phone)), "rewards != balloon.md §4")
    ok(plat[2]["grant"]["boosters"] == {"hint": 1} and plat[4]["grant"]["boosters"] == {"freeze": 1}
       and plat[9]["grant"]["boosters"] == {"freeze": 1, "hint": 1}, "bulb = hint, hourglass = freeze")
    coins = sum(p["grant"].get("coins", 0) for p in plat)
    lives = sum(p["grant"].get("unlimitedLives", 0) for p in plat)
    boosters = sum(sum(p["grant"].get("boosters", {}).values()) for p in plat)
    notes.append("week value: %d coins, inf %.2f h, %d boosters (platform 1 = 50 coins, DECISION)" % (coins, lives / 3600, boosters))
    ok((coins, lives, boosters) == (2000, 15300, 6), "week value moved")
    R = rot.Rotation()
    ok([R.plan(w)[0] for w in (22, 23, 24, 25)] == [EVENT, "clawChallenge", EVENT, EVENT], "trace weeks no longer fit the calendar")

    rows, p = run(main_script())
    # the phone's rows (balloon.md §5): win 0 -> 1, win 1 -> 2 (platform 1: nothing if already paid), win 2 -> 3, fail 3 -> 0
    ok(rows[1]["out"] == [{"balloonStreak": {"added": 1, "total": 1, "goal": 2}}], "a Super Hard win adds exactly 1")
    ok(rows[2]["out"][1] == {"balloonStep": {"step": 1, "reward": {"coins": 50}}}, "platform 1 at 2")
    ok(rows[3]["out"] == [{"balloonFell": {"from": 2}}] and rows[3]["fallPage"] and rows[3]["state"]["streak"] == 0,
       "a fail resets to 0 (and shows the fall page from 2)")
    ok(rows[5]["out"] == [{"balloonStreak": {"added": 1, "total": 2, "goal": 5}}], "2 again pays nothing (once per event)")
    ok(rows[7]["op"] == "continue" and rows[7]["state"] == rows[6]["state"], "a paid continue changed the state")
    ok(rows[9]["out"][1]["balloonStep"]["step"] == 2 and rows[10]["out"] == [{"balloonFell": {"from": 5}}], "platform 2, fall from 5")
    ok(rows[12]["out"] == [{"balloonFell": {"from": 1}}] and rows[12]["fallPage"] is False, "no fall page from 1 (VERIFIED)")
    w22 = [c for c in p.claims if c["week"] == 22]
    ok([c["step"] for c in w22] == list(range(1, 11)), "each platform paid exactly once in week 22")
    ok(sum(1 for r in rows if r["w"] == 22 and r["wins"] > 0 and rows[rows.index(r) - 1]["wins"] == 0) == 1, "one completion")
    top = [r for r in rows if r["w"] == 22 and r["state"]["streak"] == 120][0]
    ok(top["out"][0] == {"balloonStreak": {"added": 1, "total": 120}} and top["out"][1]["balloonStep"]["step"] == 10,
       "120: the last platform, goal nil")
    past = [r for r in rows if r["w"] == 22 and r["state"]["streak"] == 122][0]
    ok(past["out"] == [{"balloonStreak": {"added": 1, "total": 122}}] and past["bar"]["complete"], "past the top: counted, nothing paid")
    w23 = [r for r in rows if r["w"] == 23]
    ok(all(r["out"] == [] and r["bar"] is None and not r["live"] for r in w23), "Up & Away acted in a Treasure Climb week")
    ok(w23[0]["state"] == {"week": None, "streak": 0, "paid": 0, "best": 122}, "the roll keeps only the best streak")
    w24 = [r for r in rows if r["w"] == 24]
    ok(w24[1]["out"][1] == {"balloonStep": {"step": 1, "reward": {"coins": 50}}}, "a new event pays platform 1 again")
    w25 = [r for r in rows if r["w"] == 25]
    ok(w25[0]["bar"] == {"streak": 0, "goal": 2, "paid": 0, "complete": False, "nextReward": {"coins": 50}}
       and w25[1]["state"]["streak"] == 1, "week 25 restarts")
    for r in rows:
        st = r["state"]
        ok(st["best"] >= st["streak"] >= 0 and 0 <= st["paid"] <= len(plat), "state out of range at %s" % r)
        if st["week"] is not None:
            ok(st["paid"] == 10 or st["streak"] < plat[st["paid"]]["at"], "an unpaid platform below the streak at %s" % r)
    g, _ = run(gate_script())
    ok(g[0]["state"]["week"] is None and g[1]["out"] == [] and g[1]["state"]["week"] is None and g[2]["out"] == []
       and g[3]["state"]["week"] == 22 and g[4]["out"][0]["balloonStreak"]["total"] == 1, "unlock gate")
    k, _ = run(kill_switch_script(), RULES, dict(rot.CONFIG, enabled=False))
    ok(all(r["out"] == [] and r["state"]["week"] is None for r in k), "the kill switch lets Up & Away act")
    notes.append("main/gate/killSwitch traces: the v582 rows, once-per-event pay, continue, fall page >= 2, completion, roll, restart")

    # negative controls: each broken rule must change the golden text
    golden = fixture_text()
    muts = {}

    def mutate(name, cls_attr, fn):
        muts[name] = (cls_attr, fn)

    def bad_loss_checkpoint(self, w):                  # "a fail falls back to the last passed platform" (the §5 genre idea)
        self.roll(w)
        s = self.s
        if s["week"] != w or s["streak"] <= 0:
            return []
        frm = s["streak"]
        s["streak"] = max([p["at"] for p in self.r["platforms"] if p["at"] <= frm] or [0])
        return [{"balloonFell": {"from": frm}}] if s["streak"] != frm else []
    mutate("fail keeps the last checkpoint", "loss", bad_loss_checkpoint)

    def bad_loss_repays(self, w):                      # "a fail also resets the paid platforms" (pays again)
        out = Player.__dict__["_orig_loss"](self, w)
        if out:
            self.s["paid"] = 0
        return out
    mutate("fall resets the paid platforms", "loss", bad_loss_repays)

    def bad_win_tag(self, w, won, lvl, tag):           # "Hard levels give more" (the genre's puffs)
        out = Player.__dict__["_orig_win"](self, w, won, lvl, tag)
        if out and tag != "normal":
            self.s["streak"] += 1
        return out
    mutate("hard wins add 2", "win", bad_win_tag)

    def bad_roll_best(self, w):                        # "the best streak resets with the week"
        if self.s["week"] is not None and self.s["week"] != w:
            self.s = empty(0)
    mutate("roll resets best", "roll", bad_roll_best)

    rmuts = {
        "platform 1 at 3": dict(RULES, platforms=[dict(RULES["platforms"][0], at=3)] + RULES["platforms"][1:]),
        "fall page from 1": dict(RULES, fallPageMinStreak=1),
    }
    Player._orig_loss = Player.loss
    Player._orig_win = Player.win
    caught = 0
    total = len(muts) + len(rmuts)
    for name, (attr, fn) in muts.items():
        saved = getattr(Player, attr)
        setattr(Player, attr, fn)
        try:
            hit = fixture_text() != golden
        finally:
            setattr(Player, attr, saved)
        ok(hit, "negative control NOT caught: %s" % name)
        caught += hit
    for name, r in rmuts.items():
        hit = fixture_text(r) != golden
        ok(hit, "negative control NOT caught: %s" % name)
        caught += hit
    del Player._orig_loss, Player._orig_win
    notes.append("negative controls %d/%d CAUGHT" % (caught, total))
    ok(fixture_text() == fixture_text(), "two in-process runs differ")

    for n_ in notes:
        print("  ok  " + n_)
    for f_ in fails:
        print("  FAIL " + f_)
    print("selftest: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
    return not fails


def main(argv):
    if not os.path.exists(PH0B):
        sys.stderr.write("WARNING: %s is missing: RULES cite it as their source\n" % PH0B)
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
        have = open(path, "rb").read()
        want = fixture_text().encode("ascii")
        print("balloon fixture sha256 %s: %s" % (hashlib.sha256(have).hexdigest(), "OK" if have == want else "DIFFERS"))
        return 0 if have == want else 1
    if len(argv) >= 2 and argv[1] == "--selftest":
        return 0 if selftest() else 1
    rows, p = run(main_script())
    for r in rows:
        print("w%-3d %-8s L%-3d %-9s -> %-64s bar %s" % (
            r["w"], r["op"], r["level"], r.get("tag", ""), _dump(r["out"])[:64], _dump(r["bar"])))
    print("claims %d, wins %d, best %d" % (len(p.claims), p.wins, p.s["best"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
