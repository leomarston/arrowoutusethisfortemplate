#!/usr/bin/env python3
"""CONTENT (L2): contact sheets of bundled and served levels, to LOOK at (SPEC-architecture §12.2 L2).

    python3 -B tools/levels/sheets.py --out build/l2/sheets [--bundle App/Resources/Levels] [--served build/l2/endless-levels.jsonl]

Uses design/tools/render_levels.py's drawing (imported read-only, no bytecode): black arrows with heads, hidden arrows faint,
doors blue with their order, boxes purple with the counter, pipes cyan with the counter, tapes pink, keys gold, elevators
grey. Writes 20 levels per sheet (4 x 5):
  designed-L062-L081.png … designed-L142-L150.png   the bundled L62-L150 (spares + designed)
  endless-L151-L170.png, endless-L171-L190.png        the first served endless levels
  endless-sample-*.png                                every 23rd served level (all ten cycle positions) up to the end of the served range
  endless-flagged.png                                 the served levels lvtool endless failed (from --report, if given)
"""
import json
import os
import sys

sys.dont_write_bytecode = True
APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(APP, "design", "tools"))
import render_levels as rl  # noqa: E402


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def save(levels, path, title=None):
    if not levels:
        return
    rl.sheet(levels, cols=4, cell=12).save(path)
    print(path, "(%s)" % (title or ", ".join("L%d" % l["level"] for l in levels[:3]) + " …"))


def main():
    out = os.path.join(APP, arg("--out", "build/l2/sheets"))
    bundle = os.path.join(APP, arg("--bundle", "App/Resources/Levels"))
    served_path = os.path.join(APP, arg("--served", "build/l2/endless-levels.jsonl"))
    report = arg("--report", None)
    os.makedirs(out, exist_ok=True)
    designed = [json.load(open(os.path.join(bundle, "level_%04d.json" % n))) for n in range(62, 151)]
    for i in range(0, len(designed), 20):
        chunk = designed[i:i + 20]
        save(chunk, os.path.join(out, "designed-L%03d-L%03d.png" % (chunk[0]["level"], chunk[-1]["level"])))
    if os.path.exists(served_path):
        served = [json.loads(x) for x in open(served_path, encoding="utf-8").read().split("\n") if x.strip()]
        for i in (0, 20):
            chunk = served[i:i + 20]
            if chunk:
                save(chunk, os.path.join(out, "endless-L%d-L%d.png" % (chunk[0]["level"], chunk[-1]["level"])))
        sample = [l for l in served if l["level"] % 23 == 0]      # every 23rd: all ten cycle positions
        for i in range(0, len(sample), 20):
            chunk = sample[i:i + 20]
            save(chunk, os.path.join(out, "endless-sample-L%d-L%d.png" % (chunk[0]["level"], chunk[-1]["level"])))
        if report and os.path.exists(os.path.join(APP, report)):
            rep = json.load(open(os.path.join(APP, report)))
            bad = sorted({int(f.split(":")[0][1:]) for f in rep.get("failures", []) if f.startswith("L") and f.split(":")[0][1:].isdigit()})
            flagged = [l for l in served if l["level"] in bad]
            save(flagged, os.path.join(out, "endless-flagged.png"), "flagged: " + ", ".join("L%d" % n for n in bad))


if __name__ == "__main__":
    main()
