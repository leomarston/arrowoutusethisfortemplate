#!/usr/bin/env python3
"""missing-3d lane driver: build the lane's ids from the BUILDS tables of m3d_shop.py / m3d_events.py / m3d_fx.py.

    PY=~/.venvs/mf3d/bin/python                                 # from apps/mazeout
    $PY art/ui/recipes/m3d_make.py list
    $PY art/ui/recipes/m3d_make.py build bundleBag bundleSafe   # -> art/ui/out/<id>@3x.png (UI props) or art/out (scenes)
    $PY art/ui/recipes/m3d_make.py build bundleBag --draft      # 0.4x render -> build/ui-art/m3d/draft/<id>.png

Each module defines BUILDS = {id: fn(ctx) -> PIL RGBA at exactly frame x 3} and DEST = {id: "ui" | "art"}. Renders go
through scene_kit (per-model mesh cache, one mfrender job per batch); ctx.render() checks the machine rule first (free
swap >= 400 MB, memory pressure normal) and refuses to start rather than sleeping past the 4-minute command budget.
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
os.environ.setdefault("MF_WORKERS", "2")

import scene_kit as K  # noqa: E402
from scene_make import Ctx  # noqa: E402
import m3d_kit as MK  # noqa: E402

RECIPES = ["m3d_shop", "m3d_events", "m3d_fx"]
DRAFT = os.path.join(K.APP, "build", "ui-art", "m3d", "draft")


def builds():
    table = {}
    for r in RECIPES:
        if not os.path.exists(os.path.join(HERE, r + ".py")):
            continue
        m = importlib.import_module(r)
        for k, fn in getattr(m, "BUILDS", {}).items():
            table[k] = (m, fn)
    return table


ROUTE3D = os.path.join(K.APP, "build", "ui-art", "route3d")
TARGETS = os.path.join(K.UI, "code", "targets")   # director r3: look targets for SwiftUI entries (committed, never shipped)


def dest(m, i):
    """ui -> art/ui/out, art -> art/out, route3d -> build/ui-art/route3d (a losing-route candidate: compare only, never
    shipped; e.g. the 3D heartBig next to the missing-svg lane's shipped SVG heartBig), target -> art/ui/code/targets
    (the look a SwiftUI component must match, e.g. the Weekly Contest lettering: tools/sync_art.sh never copies it)."""
    d = getattr(m, "DEST", {}).get(i, "ui")
    return {"ui": MK.UI_OUT, "art": MK.ART_OUT, "route3d": ROUTE3D, "target": TARGETS}[d]


def build(ids, draft=False):
    table = builds()
    ctx = Ctx(draft)
    done = []
    for i in ids:
        if i not in table:
            raise SystemExit(f"unknown id {i}; known: {', '.join(sorted(table))}")
        t0 = time.time()
        m, fn = table[i]
        im = fn(ctx)
        if draft:
            os.makedirs(DRAFT, exist_ok=True)
            dst = os.path.join(DRAFT, f"{i}.png")
        else:
            dd = dest(m, i)
            os.makedirs(dd, exist_ok=True)
            dst = os.path.join(dd, f"{i[:-2] if i.endswith('3d') else i}.png" if dd == ROUTE3D else f"{i}@3x.png")
        K.save_png(im, dst)
        print(f"{i}: {im.size[0]}x{im.size[1]} -> {os.path.relpath(dst, K.APP)} ({time.time() - t0:.1f}s)")
        done.append(dst)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "build"])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    if a.cmd == "list":
        for k, (m, _) in sorted(builds().items()):
            print(f"{k:22s} {m.__name__:12s} -> {os.path.relpath(dest(m, k), K.APP)}")
    else:
        build(a.ids, a.draft)


if __name__ == "__main__":
    main()
