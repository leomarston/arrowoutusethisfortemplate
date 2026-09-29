#!/usr/bin/env python3
"""CONTENT (L2): the designed levels against the bands fitted to the recorded levels (SPEC-architecture §12.2 L2:
"`pclevels stats` shows the designed levels inside the bands fitted to L1-61 (arrows, rounds, timer, tag cadence)").

    python3 -B tools/levels/curvefit.py build/l2/pclevels-stats.txt [--out build/l2/curvefit.txt]

Input: `pclevels stats App/Resources/Levels` (C4's table: tag, timer, grid, arrows, units, waves, free, bot_left, kinds).
Bands (fixed here, before looking at the designed levels): per tag, the range the curve was fitted to — the phone's L32-L61
(SPEC-gameplay §14.3: templates L30-L59, the substitutes in the phone slots included) — widened by the curve's own growth
allowance: upper x 1.25 (growth cap, `curve.growth.cap`), lower x 0.75 (the generator's `goodEnough` 0.25 relative
distance). Tag cadence: from L34 every level ending in 4 is Hard and in 9 Super Hard, all others normal. Timers:
`curve.timers` (normal 3:00 or 2:30, Hard 3:00, Super Hard 2:00) for the designed L65-L150; the spares L62-L64 keep the
video's 3:00. Prints the per-tag band table, every designed level outside a band, and the per-level rows; exit 0 always
(the verdict is in the text: this documents content owned by design/levels.json, the orchestrator decides on outliers).
"""
import json
import os
import re
import sys

APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def parse(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"L(\d+)\s+(\w+)\s+(\d+)\s+(\d+)x(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s*(.*)$", line.rstrip())
        if m:
            g = m.groups()
            rows.append(dict(level=int(g[0]), tag=g[1], timer=int(g[2]), cols=int(g[3]), rows=int(g[4]), arrows=int(g[5]),
                             units=int(g[6]), waves=int(g[7]), free=int(g[8]), kinds=g[12].strip()))
    return rows


def main(argv):
    rows = parse(argv[0])
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    curve = json.load(open(os.path.join(APP, "App", "Resources", "Levels", "curve.json"), encoding="utf-8"))
    cap, low = curve["growth"]["cap"], 1 - curve["goodEnough"]
    by = {r["level"]: r for r in rows}
    fit_set = [by[n] for n in range(32, 62)]
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    bands = {}
    say("Bands fitted to the phone's L32-L61 (the curve's fit set), widened x%.2f below / x%.2f above:" % (low, cap))
    say("| tag | fit levels | arrows band | units band | waves band | free band |")
    say("|---|---|---|---|---|---|")
    for tag in ("normal", "hard", "superHard"):
        fs = [r for r in fit_set if r["tag"] == tag]
        b = {}
        for k in ("arrows", "units", "waves"):
            b[k] = (int(min(r[k] for r in fs) * low), int(max(r[k] for r in fs) * cap + 0.999))
        b["free"] = (max(0, min(r["free"] for r in fs) - 4), max(r["free"] for r in fs) + 4)
        bands[tag] = b
        say("| %s | %d | %d-%d | %d-%d | %d-%d | %d-%d |" % (tag, len(fs), *b["arrows"], *b["units"], *b["waves"], *b["free"]))
    timers = curve["timers"]
    outliers, cadence_bad, timer_bad = [], [], []
    designed = [r for r in rows if r["level"] >= 62]
    for r in designed:
        n = r["level"]
        want = "hard" if n % 10 == 4 else "superHard" if n % 10 == 9 else "normal"
        if r["tag"] != want:
            cadence_bad.append("L%d %s (cadence %s)" % (n, r["tag"], want))
        allowed = {"hard": {timers["hard"]}, "superHard": {timers["superHard"]}, "normal": {timers["normal"], timers["short"]}}[r["tag"]]
        if n >= 65 and r["timer"] not in allowed:
            timer_bad.append("L%d %s %d s" % (n, r["tag"], r["timer"]))
        b = bands[r["tag"]]
        out_k = [k for k in ("arrows", "units", "waves", "free") if not (b[k][0] <= r[k] <= b[k][1])]
        if out_k:
            outliers.append("L%d %s: %s" % (n, r["tag"], ", ".join("%s %d not in %d-%d" % (k, r[k], *b[k]) for k in out_k)))
    say()
    say("Designed L62-L150 (%d levels): tag cadence %s; timers %s; inside every band: %d/%d" % (
        len(designed), "OK" if not cadence_bad else "OFF " + ", ".join(cadence_bad),
        "OK (curve.timers)" if not timer_bad else "OFF " + ", ".join(timer_bad), len(designed) - len(outliers), len(designed)))
    for o in outliers:
        say("  outside: " + o)
    say()
    say("Per tag, designed vs fit set (median arrows / units / waves / free; timers):")
    for tag in ("normal", "hard", "superHard"):
        for name, grp in (("fit L32-L61", [r for r in fit_set if r["tag"] == tag]), ("designed L62-L150", [r for r in designed if r["tag"] == tag])):
            def med(k):
                v = sorted(r[k] for r in grp)
                return v[len(v) // 2] if v else 0
            tm = {}
            for r in grp:
                tm[r["timer"]] = tm.get(r["timer"], 0) + 1
            say("  %-9s %-18s n=%2d  arrows %3d  units %3d  waves %2d  free %2d  timers %s" % (
                tag, name, len(grp), med("arrows"), med("units"), med("waves"), med("free"),
                ", ".join("%d:%02d x%d" % (t // 60, t % 60, c) for t, c in sorted(tm.items(), reverse=True))))
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
