#!/usr/bin/env python3
"""Scene lane driver: build the scene illustrations listed in the recipes' BUILDS tables.

    PY=~/.venvs/mf3d/bin/python
    $PY art/ui/recipes/scene_make.py list
    $PY art/ui/recipes/scene_make.py build homeConsole homePlatform      # -> art/out/<id>@3x.png
    $PY art/ui/recipes/scene_make.py build homeConsole --draft           # 0.4x render -> build/ui-art/scene/draft/
    $PY art/ui/recipes/scene_make.py proof home                          # composed home screen next to 002

Each recipe module (scene_home.py, scene_events.py, scene_loading.py) defines BUILDS = {manifest id: fn(ctx) -> PIL
RGBA image at exactly frame x 3}. Renders go through scene_kit (per-model mesh cache, one mfrender job per batch).
Before every render batch the machine rule is checked (free swap >= 400 MB, memory pressure normal); the command
refuses to start otherwise (re-run later) instead of sleeping past the 4-minute command budget.
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
from PIL import Image  # noqa: E402

RECIPES = ["scene_home", "scene_events", "scene_loading", "scene_home_d1", "scene_events_d1", "scene_loading_d1"]   # R3 HOME: + scene_home_d1; R8: + scene_events_d1; R4: + scene_loading_d1 (after scene_loading: its loadingBackdrop wins)
DRAFT = os.path.join(K.BUILD, "draft")


class Ctx:
    def __init__(self, draft=False):
        self.draft = draft
        self.q = 0.4 if draft else 1.0

    def px(self, n):
        return int(n * self.q)

    def render(self, specs, tag="scene"):
        if not K.memory_ok(wait=False):
            raise SystemExit("memory rule: not enough free swap / pressure not normal -- retry in 2 minutes")
        for s in specs.values():
            s["px"] = self.px(s.get("px", 1600))
        return K.render_sprites(specs, tag=tag)


def builds():
    table = {}
    for r in RECIPES:
        if not os.path.exists(os.path.join(HERE, r + ".py")):
            continue
        m = importlib.import_module(r)
        for k, fn in getattr(m, "BUILDS", {}).items():
            table[k] = (m, fn)
    return table


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
            dst = os.path.join(K.OUT, f"{i}@3x.png")
        K.save_png(im, dst)
        print(f"{i}: {im.size[0]}x{im.size[1]} -> {os.path.relpath(dst, K.APP)} ({time.time() - t0:.1f}s)")
        done.append(dst)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "build", "proof"])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    if a.cmd == "list":
        for k, (m, _) in sorted(builds().items()):
            print(f"{k:22s} {m.__name__}")
    elif a.cmd == "build":
        build(a.ids, a.draft)
    elif a.cmd == "proof":
        for n in a.ids or ["home"]:
            m = importlib.import_module("scene_proofs")
            print(getattr(m, f"proof_{n}")(draft=a.draft))


if __name__ == "__main__":
    main()
