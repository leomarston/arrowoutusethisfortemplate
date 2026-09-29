#!/usr/bin/env python3
"""Checks art/ui/out against the case list art/ui/CASES.txt (one UIArt case per line, '#' comments; SPEC-ui §7 will
generate it): every case has <case>@3x.png, RGBA, sizes are whole pt at 3x, the art is not empty and does not touch the
frame edge by accident (transparent-margin check for sprite art), no stray files.

    python3 art/ui/tools/check.py            # prints a table; exit 1 on any failure
"""
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.dirname(HERE)
APP = os.path.dirname(os.path.dirname(UI))
OUT = os.path.join(UI, "out")
OPAQUE = set()      # full-bleed cases (backgrounds) go here
EXTRA = set()       # proposed extra cases (reported, not failed)
SIDECARS = set()    # json sidecars allowed next to the PNGs


def spec_cases():
    p = os.path.join(UI, "CASES.txt")
    if not os.path.exists(p):
        return set()
    out = set()
    for line in open(p, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line.split()[0])
    return out


def main():
    want = spec_cases()
    files = sorted(os.listdir(OUT))
    have = {f[:-7] for f in files if f.endswith("@3x.png")}
    stray = [f for f in files if not f.endswith("@3x.png") and f not in SIDECARS]
    bad = []
    rows = []
    for c in sorted(have):
        im = Image.open(os.path.join(OUT, f"{c}@3x.png"))
        a = np.asarray(im.convert("RGBA"))[..., 3]
        cov = float((a > 8).mean())
        w, h = im.size
        edge = max(a[0].max(), a[-1].max(), a[:, 0].max(), a[:, -1].max())
        fading = False
        ok = im.mode == "RGBA" and w % 3 == 0 and h % 3 == 0 and (cov > 0.02 or (fading and a.max() > 0))
        note = ""
        if im.mode != "RGBA":
            note += " not RGBA;"
        if w % 3 or h % 3:
            note += " size not whole pt;"
        if cov <= 0.02:
            note += " fade-out tail;" if fading else " empty;"
        if c not in OPAQUE and edge > 250:
            note += " touches edge;"
        if not ok:
            bad.append(c)
        rows.append(f"{c:22s} {w:5d} x {h:<5d} px  {w / 3:6.1f} x {h / 3:<6.1f} pt  alpha {cov:5.2f} {'OK' if ok else 'FAIL'}{note}")
    print("\n".join(rows))
    missing = sorted(want - have)
    extra = sorted(have - want - EXTRA)
    print(f"\nspec cases {len(want)}, produced {len(have & want)}, extra (proposed) {sorted(have & EXTRA)}")
    print("missing:", missing or "none")
    print("unexpected:", extra or "none")
    print("stray files:", stray or "none")
    print("total size MB:", round(sum(os.path.getsize(os.path.join(OUT, f)) for f in files) / 1e6, 2))
    if missing or bad or stray or extra:
        sys.exit(1)


if __name__ == "__main__":
    main()
