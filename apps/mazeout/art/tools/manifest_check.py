#!/usr/bin/env python3
"""Check art/MANIFEST.json against the tree: every entry well-formed, every built raster present and right.

    ~/.venvs/mf3d/bin/python art/tools/manifest_check.py              # table + summary; exit 1 on any failure
    ~/.venvs/mf3d/bin/python art/tools/manifest_check.py --strict     # stray files in art/ui/out, art/out also fail
    ~/.venvs/mf3d/bin/python art/tools/manifest_check.py --write-cases   # regenerate art/ui/CASES.txt (check.py)
    ~/.venvs/mf3d/bin/python art/tools/manifest_check.py --quiet      # failures + summary only
    ~/.venvs/mf3d/bin/python art/tools/manifest_check.py --lanes      # + every art/lanes/*.entries.json merged IN MEMORY
                                                                      # (lane scratch manifests; nothing is written)

Per entry
  schema   id unique, lowerCamelCase, neutral (no brand words); family / route / status valid; owner set;
           rasters (svg, 3d) have `file` = <dir>/<id>@3x.png (or a rig dir for puppets, or exact_px files such as the icon)
           and whole-pt size_pt
  ref      shot / video exists; box_pt (or box_px) inside the image; box non-empty
  source   svg: the generator file has the case in CASES; 3d: the recipe file mentions the case in ASSETS (or RIGS);
           swiftui: `struct <Symbol>` exists in the Swift file; code: free text (engine owner).
           A todo entry may name a PLANNED generator / symbol (a note, not a failure); wip/done/graded must resolve.
  output   status done/graded (and any existing file): RGBA, exactly size_pt x 3 px, not empty, some transparency and
           nothing touching the frame edge (unless full_bleed) -- the art_batch verifier
  status   done/graded without an output = FAIL; todo with an output = note ("built but not marked")
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import manifest as MF  # noqa: E402
from art_batch import split_source, verify  # noqa: E402

APP, ART = MF.APP, MF.ART
RASTER = ("svg", "3d")
REQUIRED = ("id", "family", "route", "purpose", "screen", "status", "owner")


def check_entry(e, seen):
    from PIL import Image
    probs, notes = [], []
    for k in REQUIRED:
        if not e.get(k):
            probs.append(f"missing '{k}'")
    i = e.get("id", "?")
    if i in seen:
        probs.append("duplicate id")
    seen.add(i)
    probs += [f"id: {p}" for p in MF.id_problems(i)]
    if e.get("family") not in MF.FAMILIES:
        probs.append(f"family {e.get('family')!r}")
    if e.get("route") not in MF.ROUTES:
        probs.append(f"route {e.get('route')!r}")
    if e.get("status") not in MF.STATUSES:
        probs.append(f"status {e.get('status')!r}")
    fam = e.get("family")
    sz = e.get("size_pt")
    todo = e.get("status") == "todo"
    if fam in RASTER:
        if not e.get("file"):
            probs.append("raster entry without 'file'")
        elif e.get("exact_px"):
            pass
        elif not e.get("rig") and not (e["file"].endswith(f"/{i}@3x.png") or e["file"].endswith(f"/char_{i}@3x.png")):
            probs.append(f"file {e['file']} is not <dir>/{i}@3x.png (characters lane: <dir>/char_{i}@3x.png)")
        if e.get("exact_px"):
            pass
        elif not sz or len(sz) != 2:
            probs.append("raster entry without size_pt [w, h]")
        elif any(abs(v - round(v)) > 1e-6 for v in sz) and not e.get("render_scale"):
            probs.append(f"size_pt {sz} not whole pt")     # render_scale entries: size_pt = a settled on-screen size
        if e.get("render_scale") is not None and not (isinstance(e["render_scale"], (int, float)) and e["render_scale"] >= 1):
            probs.append(f"render_scale {e['render_scale']!r} (a number >= 1: the file is size_pt x 3 x render_scale px)")
    if sz and (len(sz) != 2 or min(sz) <= 0):
        probs.append(f"bad size_pt {sz}")
    if e.get("size_px") and sz and [round(v * 3) for v in sz] != list(e["size_px"]):
        probs.append(f"size_px {e['size_px']} != size_pt x 3")
    # reference
    r = e.get("ref") or {}
    if r.get("video"):
        if not os.path.exists(MF.app_path(r["video"])):
            probs.append(f"ref video missing: {r['video']}")
    elif r.get("shot"):
        p = MF.app_path(r["shot"])
        if not os.path.exists(p):
            probs.append(f"ref shot missing: {r['shot']}")
        else:
            W, H = Image.open(p).size
            k = r.get("px_per_pt") or MF.shot_scale(p)
            if r.get("box_px"):
                x0, y0, x1, y1 = r["box_px"]
                if not (0 <= x0 < x1 <= W + 1 and 0 <= y0 < y1 <= H + 1):
                    probs.append(f"ref box_px {r['box_px']} outside {r['shot']} ({W} x {H} px)")
            elif r.get("box_pt"):
                x0, y0, x1, y1 = r["box_pt"]
                if not (-0.5 <= x0 < x1 <= W / k + 0.5 and -0.5 <= y0 < y1 <= H / k + 0.5):
                    probs.append(f"ref box_pt {r['box_pt']} outside {r['shot']} ({W / k:.0f} x {H / k:.0f} pt)")
    elif e.get("status") in ("done", "graded") and not e.get("no_ref"):
        notes.append("no reference crop (side-by-side impossible)")
    # source
    src = e.get("source") or ""
    def bad(msg):
        (notes if todo else probs).append(("planned: " if todo else "") + msg)
    if fam == "svg" and src:
        gp, case = split_source(e)
        if not gp or not os.path.exists(gp):
            bad(f"generator missing: {src}")
        else:
            txt = open(gp, encoding="utf-8").read()
            dyn = (case.startswith("doorW") and "def door_case" in txt) or (case.startswith("curtainW") and "def curtain_case" in txt)
            if not dyn and not re.search(rf'["\']{re.escape(case)}["\']|CASES\[f"', txt):
                bad(f"case {case} not found in {os.path.relpath(gp, APP)}")
    elif fam == "3d" and src:
        rp, case = split_source(e)
        if not rp or not os.path.exists(rp):
            bad(f"recipe missing: {src}")
        elif case not in open(rp, encoding="utf-8").read():
            bad(f"case {case} not mentioned in {os.path.relpath(rp, APP)}")
    elif fam == "swiftui" and src and ":" in src:
        p, sym = src.rsplit(":", 1)
        if not os.path.exists(MF.app_path(p)):
            bad(f"swift file missing: {p}")
        elif not re.search(rf"\b(struct|enum|class|func)\s+{re.escape(sym)}\b", open(MF.app_path(p), encoding="utf-8").read()):
            bad(f"symbol {sym} not in {p}")
    # output
    if fam in RASTER and e.get("file"):
        path = MF.app_path(e["file"])
        exists = os.path.exists(path)
        if e.get("rig"):
            if e.get("status") in ("done", "graded") and not os.path.exists(os.path.join(path, "rig.json")):
                probs.append(f"rig.json missing in {e['file']}")
        elif exists and e.get("exact_px"):
            probs += verify(e, path)   # exact size; full_bleed -> RGB without alpha (the app icon)
        elif exists:
            probs += verify(e, path)
            if e.get("status") == "todo":
                notes.append("built but status todo")
        elif e.get("status") in ("done", "graded"):
            probs.append(f"status {e['status']} but {e['file']} is missing")
    return probs, notes


def strays(m):
    used = {os.path.abspath(MF.app_path(x["file"])) for x in m.get("superseded", [])}
    for e in m["entries"]:   # a rig ships its full render + sidecar next to the rig dir (rig.json "full")
        if e.get("rig") and e.get("file"):
            d = os.path.abspath(MF.app_path(e["file"]))
            base = d[:-4] if d.endswith("_rig") else d
            for ext in ("@3x.png", ".json", "_t.json"):
                used.add(base + ext)
            rj = os.path.join(d, "rig.json")
            if os.path.exists(rj):
                import json
                full = json.load(open(rj)).get("full")
                if full.endswith(".png"):
                    used.add(os.path.normpath(os.path.join(d, full)))
                elif full:
                    for ext in ("@3x.png", ".json"):
                        used.add(os.path.join(os.path.dirname(d), full + ext))
    for e in m["entries"]:
        if e.get("file"):
            f = os.path.abspath(MF.app_path(e["file"]))
            used.add(f)
            if f.endswith("@3x.png"):      # a 3D render's anchor sidecar (ui3d `anchors`): <case>.json next to it
                used.add(f[:-len("@3x.png")] + ".json")
    for x in m.get("support_files", []):   # non-graphic files the app reads next to the renders (director r2)
        used.add(os.path.abspath(MF.app_path(x["file"])))
    out = []
    for d in (os.path.join(ART, "ui", "out"), os.path.join(ART, "out")):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            p = os.path.abspath(os.path.join(d, f))
            if p in used or f.startswith("."):
                continue
            out.append(os.path.relpath(p, APP))
    return out


def write_cases(m):
    rows = ["# UI raster cases (art/ui/out/<case>@3x.png) -- GENERATED from art/MANIFEST.json by",
            "# `art/tools/manifest_check.py --write-cases`; edit the manifest, not this file. check.py reads it."]
    for e in m["entries"]:
        f = e.get("file") or ""
        if e["family"] in RASTER and f.startswith("art/ui/out/"):
            if "NOT SHIPPED" in (e.get("notes") or "") and not os.path.exists(MF.app_path(f)):
                continue            # provenance-only entries (older video skins), as tools/uiart_gen.py skips them
            sz = "x".join(str(v) for v in e["size_pt"])
            rows.append(f"{e['id']:22s} # {sz:>9s} pt  {e['family']:3s} {e['status']:6s} {e.get('purpose', '')[:60]}")
    p = os.path.join(ART, "ui", "CASES.txt")
    open(p, "w", encoding="utf-8").write("\n".join(rows) + "\n")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--write-cases", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--manifest", help="another manifest file (tests)")
    ap.add_argument("--lanes", nargs="*", metavar="ENTRIES_JSON",
                    help="merge lane scratch manifests in memory before checking (default: art/lanes/*.entries.json)")
    a = ap.parse_args()
    if a.manifest:
        MF.use_manifest(a.manifest)
    m = MF.load()
    if a.lanes is not None:
        import glob
        # director r3: the default merges in the art director's order (art/review/tools/director_merge.py LANE_ORDER;
        # later wins), not alphabetically -- alphabetical put the round-1 svg lane after polish and reverted its sizes
        order = ["characters", "3d-hud", "3d-events", "scene", "svg", "director", "missing-svg", "missing-3d", "polish",
                 "director-r3"]
        rank = lambda f: (order.index(os.path.basename(f)[:-len(".entries.json")])
                          if os.path.basename(f)[:-len(".entries.json")] in order else len(order), os.path.basename(f))
        files = a.lanes or sorted(glob.glob(os.path.join(ART, "lanes", "*.entries.json")), key=rank)
        touched = {}
        for f in files:
            d = MF.merge_diff(m, MF.load(f))
            for i, _, _ in d:
                if i in touched:
                    print(f"lanes: {i} is in both {touched[i]} and {os.path.basename(f)} (the later wins)")
                touched[i] = os.path.basename(f)
            MF.merge_apply(m, d, validate=False)
            print(f"lanes: merged {os.path.relpath(f, APP)}: {len(d)} entries differ "
                  f"({sum(1 for x in d if x[1] == 'new')} new)")
    for k in ("version", "entries", "board_design_pitch_pt"):
        if k not in m:
            print(f"manifest: missing top-level '{k}'")
            sys.exit(1)
    seen = set()
    fails = 0
    counts = {}
    for e in m["entries"]:
        probs, notes = check_entry(e, seen)
        key = (e.get("family"), e.get("status"))
        counts[key] = counts.get(key, 0) + 1
        if probs:
            fails += 1
        if probs or (notes and not a.quiet) or not a.quiet:
            if not probs and a.quiet:
                continue
            sz = "x".join(str(v) for v in e["size_pt"]) if e.get("size_pt") else "-"
            flag = "FAIL" if probs else "ok  "
            print(f"{flag} {e.get('id', '?'):26s} {e.get('family', '?'):7s} {e.get('route', '?'):3s} {sz:>9s} {e.get('status', '?'):6s} "
                  + "; ".join(probs + [f"({n})" for n in notes]))
    st = strays(m)
    print(f"\n{len(m['entries'])} entries, {fails} failing")
    for fam in MF.FAMILIES:
        row = [f"{s} {counts.get((fam, s), 0)}" for s in MF.STATUSES]
        print(f"  {fam:8s} " + ", ".join(row))
    print("stray files (not in the manifest):", ", ".join(st) if st else "none")
    sup = [x["file"] for x in m.get("superseded", []) if os.path.exists(MF.app_path(x["file"]))]
    if sup:
        print("superseded files still on disk (their lane deletes them):", ", ".join(sup))
    if a.write_cases:
        print("wrote", os.path.relpath(write_cases(m), APP))
    if fails or (a.strict and st):
        sys.exit(1)


if __name__ == "__main__":
    main()
