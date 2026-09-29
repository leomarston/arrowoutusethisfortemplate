#!/usr/bin/env python3
"""CONTENT (L2): the independent Python verdict on the served endless levels.

    python3 -B tools/levels/endless_py.py build/l2/endless-levels.jsonl [--jobs 3] [--report build/l2/endless-python.json]

`lvtool endless --out` writes every level exactly as LevelProvider serves it (canonical bundle lines). This runs the design
validator's per-level list on each one — design/tools/validate_levels.check_level on design/tools/arrowcore.py, the Python
rules the spec's levels were proved with (SPEC-gameplay §14.4), an implementation independent of PathCore: structure,
obstacles, the greedy solver, every obstacle used, no dead end in 40 seeded random orders on pipe / elevator levels, the
0.6 s/tap bot keeps >= 20 %, metrics = recomputed — plus the validator's own board key across design/levels.json L1-L150 and
the served levels (no repeat). The design tools are imported read-only (no bytecode, `main()` never called: it writes
design/tools/work/). Exit 1 on any error.
"""
import json
import os
import sys
import time
from multiprocessing import Pool

sys.dont_write_bytecode = True
APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(APP, "design", "tools"))
import validate_levels as vl  # noqa: E402


def one(line):
    lvl = json.loads(line)
    errs, warns = [], []
    t = time.time()
    m = vl.check_level(lvl, errs, warns)
    return lvl["level"], errs, warns, (m or {}).get("rounds"), round(time.time() - t, 3)


def main(argv):
    path = argv[0]
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 3
    report = argv[argv.index("--report") + 1] if "--report" in argv else None
    lines = [x for x in open(path, encoding="utf-8").read().split("\n") if x.strip()]
    t0 = time.time()
    with Pool(jobs) as p:
        res = p.map(one, lines, chunksize=4)
    errs = [e for _n, es, _w, _r, _t in res for e in es]
    warns = [w for _n, _e, ws, _r, _t in res for w in ws]
    design = json.load(open(os.path.join(APP, "design", "levels.json"), encoding="utf-8"))["levels"]
    seen, repeats = {}, []
    for lvl in design + [json.loads(x) for x in lines]:
        k = vl.board_key(lvl)
        if k in seen:
            repeats.append("L%d repeats L%d" % (lvl["level"], seen[k]))
        seen[k] = lvl["level"]
    errs += repeats
    secs = [t for *_x, t in res]
    out = dict(file=path, levels=len(res), errors=errs, warnings=warns, repeats=repeats,
               seconds=round(time.time() - t0, 1), per_level_seconds_max=max(secs) if secs else 0,
               table=[dict(level=n, ok=not es, rounds=r) for n, es, _w, r, _t in res])
    if report:
        with open(report, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
    print("endless_py: %d served levels through design/tools/validate_levels.check_level (arrowcore, Python): %d error(s), "
          "%d warning(s); board-key repeats across L1-L150 + these: %d; %.0f s on %d processes" % (
              len(res), len(errs), len(warns), len(repeats), time.time() - t0, jobs))
    for e in errs[:40]:
        print("ERROR", e)
    for w in warns[:10]:
        print("WARN", w)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
