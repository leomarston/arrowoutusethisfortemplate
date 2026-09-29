#!/usr/bin/env python3
"""Batch-build the art listed in art/MANIFEST.json.

    PY=~/.venvs/mf3d/bin/python
    $PY art/tools/art_batch.py --svg                  # every svg entry with a generator -> its file, exact frame x 3
    $PY art/tools/art_batch.py --3d                   # every 3d entry with a recipe case -> its file, alpha checked
    $PY art/tools/art_batch.py --ids tapeV4 doorW4H8  # just these (any family that has a builder)
    $PY art/tools/art_batch.py --svg --status todo,wip,done   # filter by status (default: every status)
    $PY art/tools/art_batch.py --svg --sync           # write the generator's frame/anchor back into the manifest
    $PY art/tools/art_batch.py --3d --draft           # quick low-res 3D renders to build/ui-art/draft/ (no ship)
    $PY art/tools/art_batch.py --svg --dry            # list what would be built
    $PY art/tools/art_batch.py --rigs                 # every rig entry (characters): layers + rig.json + proof (rig.py)
    $PY art/tools/art_batch.py --manifest x.json --3d # another manifest (tests / scratch batches)

SVG entries: source "art/ui/src/<gen>.py:<case>". The generator module's CASES[case]() returns the SVG text (or
(svg, meta) with meta["anchor"] in pt); it is written to art/ui/src/<case>.svg and rasterised by art/ui/tools/svg.py
(WebKit, 2x supersampled) in ONE WebKit process for the whole batch, then moved to the entry's `file`.
3D entries: source "<recipe dir>/<recipe>.py:<case>" (art/ui/recipes or art/pipeline/items). Rendered by ui3d.render_case
with the calibrated rig (ui3d.RIG + the case's light), written to the entry's `file` (art/out/<id>@3x.png for
characters/scenes/3D arrows and props, art/ui/out for UI props). `exact_px` entries (the 1024 px app icon; the case's frame
is exact_px / 3 pt) are resized to exactly exact_px if needed and, when `full_bleed` and fully opaque, saved as RGB
(no alpha); verified on exact size (+ RGB for full_bleed) instead of the @3x cut-out rules.

Every output is verified: RGBA, exactly size_pt x 3 px, some transparency (unless full_bleed), not empty, not touching
the frame edge (unless full_bleed). A failure exits 1 and names the entry. 3D batches check `sysctl vm.swapusage` first
and wait in 2-minute steps while less than 400 MB of swap is free (machine limit).
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import manifest as MF  # noqa: E402

APP, ART = MF.APP, MF.ART
UI_TOOLS = os.path.join(ART, "ui", "tools")
SRC = os.path.join(ART, "ui", "src")


def swap_free_mb():
    try:
        out = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True, timeout=10).stdout
        m = re.search(r"free = ([\d.]+)M", out)
        return float(m.group(1)) if m else 1e9
    except Exception:
        return 1e9


def wait_swap(min_mb=400, step_s=120, max_wait_s=1800):
    t0 = time.time()
    while True:
        f = swap_free_mb()
        if f >= min_mb:
            return f
        if time.time() - t0 > max_wait_s:
            raise SystemExit(f"swap still below {min_mb} MB after {max_wait_s} s ({f:.0f} MB free); try again later")
        print(f"  swap free {f:.0f} MB < {min_mb} MB: waiting {step_s} s")
        time.sleep(step_s)


def verify(e, path, draft=False):
    """-> list of problems (empty = OK)."""
    import numpy as np
    from PIL import Image
    probs = []
    if not os.path.exists(path):
        return [f"missing {os.path.relpath(path, APP)}"]
    im = Image.open(path)
    if e.get("exact_px"):   # a raster that is not @3x (the 1024 px app icon): exact size; full_bleed = opaque RGB, no alpha
        if not draft and list(im.size) != list(e["exact_px"]):
            probs.append(f"size {im.size[0]}x{im.size[1]} px, exact_px {e['exact_px']}")
        if e.get("full_bleed") and im.mode != "RGB":
            probs.append(f"mode {im.mode}: an opaque full-bleed exact_px raster (app icon) must be RGB without alpha")
        return probs
    if im.mode != "RGBA":
        probs.append(f"mode {im.mode}, not RGBA")
    w, h = im.size
    if not draft and e.get("size_pt") and e.get("render_scale"):
        # render_scale entries (the win logo's parts): size_pt is the part's SETTLED on-screen size and the file is
        # render_scale x that at @3x (it is animated up to that size and only ever scaled down); file_px is exact
        want = (round(e["size_pt"][0] * 3 * e["render_scale"]), round(e["size_pt"][1] * 3 * e["render_scale"]))
        if abs(w - want[0]) > 1 or abs(h - want[1]) > 1:
            probs.append(f"size {w}x{h} px, manifest {e['size_pt']} pt x 3 x render_scale {e['render_scale']} -> {want[0]}x{want[1]}")
        if e.get("file_px") and [w, h] != list(e["file_px"]):
            probs.append(f"size {w}x{h} px, file_px {e['file_px']}")
    elif not draft and e.get("size_pt"):
        want = (round(e["size_pt"][0] * 3), round(e["size_pt"][1] * 3))
        if (w, h) != want:
            probs.append(f"size {w}x{h} px, manifest {e['size_pt']} pt -> {want[0]}x{want[1]}")
    if w % 3 or h % 3:
        probs.append("size not whole pt")
    a = np.asarray(im.convert("RGBA"))[..., 3]
    cov = float((a > 8).mean())
    if cov < 0.02:
        probs.append(f"nearly empty (alpha coverage {cov:.3f})")
    if not e.get("full_bleed"):
        if a.min() > 8:
            probs.append("no transparent pixel (not a cut-out)")
        edge = max(int(a[0].max()), int(a[-1].max()), int(a[:, 0].max()), int(a[:, -1].max()))
        if edge > 250:
            probs.append(f"art touches the frame edge (alpha {edge}): clipped?")
    return probs


def _load_gen(path):
    name = "gen_" + re.sub(r"\W", "_", os.path.relpath(path, APP))
    if name in sys.modules:
        return sys.modules[name]
    if os.path.dirname(path) not in sys.path:
        sys.path.insert(0, os.path.dirname(path))
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def split_source(e):
    src = e.get("source") or ""
    if ":" not in src:
        return None, None
    p, case = src.rsplit(":", 1)
    return MF.app_path(p), case


def build_svg(es, draft=False, sync=False, m=None):
    sys.path.insert(0, UI_TOOLS)
    import svg as SVG
    todo = []
    metas = {}
    for e in es:
        gp, case = split_source(e)
        if not gp or not gp.endswith(".py") or not os.path.exists(gp):
            print(f"  skip {e['id']}: no generator ({e.get('source')})")
            continue
        mod = _load_gen(gp)
        cases = getattr(mod, "CASES", {})
        if case not in cases and hasattr(mod, "door_case") and case.startswith("doorW"):
            w, h = case[5:].split("H")
            mod.door_case(int(w), int(h))
        if case not in cases and hasattr(mod, "curtain_case") and case.startswith("curtainW"):
            w, h = case[8:].split("H")
            mod.curtain_case(int(w), int(h))
        if case not in cases:
            print(f"  FAIL {e['id']}: {os.path.relpath(gp, APP)} has no case {case}")
            continue
        res = cases[case]()
        svg_txt, meta = (res if isinstance(res, tuple) else (res, {}))
        open(os.path.join(SRC, f"{case}.svg"), "w", encoding="utf-8").write(svg_txt)
        metas[e["id"]] = (case, meta, svg_txt)
        todo.append(e)
    if not todo:
        return []
    cases = sorted({metas[e["id"]][0] for e in todo})
    SVG.render(cases, draft=draft)
    fails = []
    for e in todo:
        case, meta, svg_txt = metas[e["id"]]
        w, h = SVG.svg_size(os.path.join(SRC, f"{case}.svg"))
        if sync and m is not None and e.get("render_scale"):
            print(f"  sync skips {e['id']}: render_scale entry (size_pt is its SETTLED on-screen size, written by "
                  f"art/ui/tools/logo_parts.py manifest; its SVG root is the file size)")
        elif sync and m is not None:
            e["size_pt"] = [int(round(w)), int(round(h))]
            e["size_px"] = [v * 3 for v in e["size_pt"]]
            if meta.get("anchor"):
                e["anchor_pt"] = [round(meta["anchor"][0], 2), round(meta["anchor"][1], 2)]
        built = os.path.join(APP, "build", "ui-art", "draft", f"{case}.png") if draft else os.path.join(SVG.OUT, f"{case}@3x.png")
        dst = built if draft else MF.app_path(e["file"])
        if not draft and os.path.abspath(built) != os.path.abspath(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(built, dst)
        p = verify(e, dst, draft)
        tag = "OK " if not p else "FAIL"
        print(f"  {tag} {e['id']:24s} {os.path.relpath(dst, APP)}  {'; '.join(p)}")
        if p:
            fails.append((e["id"], p))
    return fails


def finish_exact(e, path):
    """exact_px entries (the app icon): resize to exactly exact_px if the case's frame x 3 differs, and save a full_bleed
    one as RGB (App Store icons carry no alpha) -- only when it is fully opaque; otherwise verify() reports it."""
    from PIL import Image
    im = Image.open(path)
    im.load()
    want = tuple(e["exact_px"])
    changed = False
    if im.size != want:
        im = im.convert("RGBA").resize(want, Image.LANCZOS)
        changed = True
    if e.get("full_bleed") and im.mode != "RGB":
        a = im.convert("RGBA").getchannel("A")
        if a.getextrema()[0] == 255:
            im = im.convert("RGB")
            changed = True
    if changed:
        tmp = path + f".tmp{os.getpid()}.png"
        im.save(tmp, optimize=True)
        os.replace(tmp, path)
    return path


def build_3d(es, draft=False, force=False):
    sys.path.insert(0, UI_TOOLS)
    import ui3d
    fails = []
    for e in es:
        rp, case = split_source(e)
        if not rp or not os.path.exists(rp):
            print(f"  skip {e['id']}: no recipe ({e.get('source')})")
            continue
        wait_swap()
        ui3d.set_recipes(os.path.dirname(rp))
        recipe = os.path.basename(rp)[:-3]
        dst = MF.app_path(e["file"])
        old = ui3d.OUT
        ui3d.OUT = os.path.dirname(dst)
        t0 = time.time()
        try:
            out = ui3d.render_case(case, recipe, draft=draft, force=force, log=lambda *a: None)
        finally:
            ui3d.OUT = old
        if not draft and os.path.abspath(out) != os.path.abspath(dst):
            shutil.move(out, dst)
            out = dst
        if e.get("exact_px") and not draft:
            out = finish_exact(e, out)
        p = verify(e, out, draft)
        print(f"  {'OK ' if not p else 'FAIL'} {e['id']:24s} {os.path.relpath(out, APP)} ({time.time() - t0:.1f}s)  {'; '.join(p)}")
        if p:
            fails.append((e["id"], p))
    return fails


def build_rigs(es, draft=False, force=False):
    """Rig entries (rig: true; source '<recipe dir>/<recipe>.py:<RIGS name>') -> art/ui/tools/rig.py export: per-layer
    PNGs + rig.json (pivots, groups, z) in the entry's `file` dir, plus the proof sheets. Checks rig.json afterwards."""
    sys.path.insert(0, UI_TOOLS)
    import json
    import ui3d
    import rig as RIG
    fails = []
    for e in es:
        rp, name = split_source(e)
        if not rp or not os.path.exists(rp):
            print(f"  skip {e['id']}: no rig recipe ({e.get('source')})")
            continue
        wait_swap()
        ui3d.set_recipes(os.path.dirname(rp))
        t0 = time.time()
        RIG.export(name, draft=draft, force=force)
        d = MF.app_path(e["file"])
        rj = os.path.join(d, "rig.json")
        probs = []
        if draft:
            print(f"  draft rig {name} ({time.time() - t0:.1f}s): build/ui-art/rigs/")
            continue
        if not os.path.exists(rj):
            probs.append(f"no rig.json in {e['file']} (RIGS dir name must match the manifest file)")
        else:
            r = json.load(open(rj))
            for L in r.get("layers", []):
                lp = os.path.join(d, L["file"])
                if not os.path.exists(lp):
                    probs.append(f"layer file missing {L['file']}")
            pr = r.get("proof") or {}
            if pr.get("mean_abs", 0) > 2.0 or pr.get("pct_gt40", 0) > 1.0:
                probs.append(f"proof off: {pr}")
        print(f"  {'OK ' if not probs else 'FAIL'} {e['id']:24s} {e['file']} ({time.time() - t0:.1f}s)  {'; '.join(probs)}")
        if probs:
            fails.append((e["id"], probs))
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", action="store_true")
    ap.add_argument("--3d", dest="three", action="store_true")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--status", default="todo,wip,done,graded")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--force", action="store_true", help="3d: re-mesh even if cached")
    ap.add_argument("--sync", action="store_true", help="svg: write frame size / anchor from the generator into the manifest")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--rigs", action="store_true", help="rig entries (rig: true, source <recipes>/<recipe>.py:<RIG>) -> rig.py export")
    ap.add_argument("--manifest", help="another manifest file (tests, scratch batches)")
    a = ap.parse_args()
    if a.manifest:
        MF.use_manifest(a.manifest)
    m = MF.load()
    st = set(a.status.split(","))
    es = [e for e in m["entries"] if e["status"] in st and (not a.ids or e["id"] in a.ids)]
    buildable = lambda e: bool(split_source(e)[0]) and e.get("file")
    svg_es = [e for e in es if e["family"] == "svg" and buildable(e) and (a.svg or a.ids)]
    d3_es = [e for e in es if e["family"] == "3d" and buildable(e) and not e.get("rig") and (a.three or a.ids)]
    rig_es = [e for e in es if e.get("rig") and buildable(e) and (a.rigs or a.ids)]
    if a.dry:
        for e in svg_es + d3_es + rig_es:
            print(f"  {e['family']:4s} {e['id']:24s} {e['source']} -> {e['file']}")
        return
    fails = []
    if svg_es:
        print(f"svg: {len(svg_es)} entries")
        fails += build_svg(svg_es, draft=a.draft, sync=a.sync, m=m)
        if a.sync:
            MF.save(m)
            print("  manifest synced (size_pt / anchor_pt from the generators)")
    if d3_es:
        print(f"3d: {len(d3_es)} entries (swap free {swap_free_mb():.0f} MB)")
        fails += build_3d(d3_es, draft=a.draft, force=a.force)
    if rig_es:
        print(f"rigs: {len(rig_es)} entries (swap free {swap_free_mb():.0f} MB)")
        fails += build_rigs(rig_es, draft=a.draft, force=a.force)
    if fails:
        print(f"\n{len(fails)} FAILED: " + ", ".join(i for i, _ in fails))
        sys.exit(1)
    print("\nall built entries verified")


if __name__ == "__main__":
    main()
