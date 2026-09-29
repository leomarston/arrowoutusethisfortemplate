#!/usr/bin/env python3
"""Build item USDZs from recipes.

    PY=~/.venvs/mf3d/bin/python
    MF_WORKERS=2 $PY art/pipeline/build.py toy_hammer rubber_duck      # recipes or item ids (variants), any subset
    $PY art/pipeline/build.py star_mallet                              # one variant: meshes its shared geometry once
    $PY art/pipeline/build.py --all
    $PY art/pipeline/build.py --list                                   # recipes -> item ids
    $PY art/pipeline/build.py --catalog                                # only regenerate art/out/catalog.json
    $PY art/pipeline/build.py --repose corn_can toy_drum               # recompute stable_poses from the shipped usdz (--all ok)

Outputs (art/out/), per item id (every colour variant gets its own set):
    <id>.usdz          one Mesh per part + UsdPreviewSurface materials
    <id>.outline.usdz  closed, manifold, low-poly union shell for the outline shader (same frame)
    <id>.json          metadata: dims, volume, inertia, triangle stats per part, stable resting poses,
                       convex hulls (physics compound), icon view, tray pose/scale, outline stats, catalogue
    catalog.json       every built id -> files, length, tris, variant_of, first level, role (rebuilt each run)
Icons (<id>_icon.png, <id>_icon_sticker.png) come from preview.py.
"""
from __future__ import annotations

import argparse
import datetime
import importlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ART = os.path.dirname(HERE)
APP = os.path.dirname(ART)
OUT = os.path.join(ART, "out")

from mesher import (PartMesh, build_item, convex_hulls, geometry_key, load_items, stable_poses,  # noqa: E402
                    tray_info)
from usdwriter import check_usdz, write_outline_usdz, write_usdz  # noqa: E402


# ------------------------------------------------------------------ recipes and ids

def recipes():
    """Board-ITEM recipes: items/*.py that define a top-level build(). Skipped: '_' helpers, and the character /
    UI recipes that live next to them (char_*.py: MODELS / ASSETS / RIGS for art/ui/tools/ui3d.py + rig.py, no
    build()) -- characters lane request 1, art/lanes/requests.md."""
    d = os.path.join(HERE, "items")
    out = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".py") or f.startswith("_") or f.startswith("char_"):
            continue
        with open(os.path.join(d, f), encoding="utf-8") as fh:
            if re.search(r"^def build\(", fh.read(), re.M):
                out.append(f[:-3])
    return out


def recipe_ids(recipe):
    """Item ids a recipe emits, WITHOUT meshing: module-level VARIANTS (list or dict keys) if present,
    else the recipe name (build() may still return more; then select them by the recipe name)."""
    mod = importlib.import_module(f"items.{recipe}")
    v = getattr(mod, "VARIANTS", None)
    return list(v) if v else [recipe]


def resolve(names):
    """CLI names (recipe names or item ids) -> {recipe: set of ids or None for all}."""
    all_r = recipes()
    idx = {}
    for r in all_r:
        try:
            for i in recipe_ids(r):
                idx.setdefault(i, r)
        except Exception as e:  # a broken recipe must not block the others
            print(f"  (skipping {r} in the id index: {e})")
    want = {}
    for n in names:
        if n in all_r or (n.startswith("_") and os.path.exists(os.path.join(HERE, "items", n + ".py"))):
            want[n] = None
        elif n in idx:
            r = idx[n]
            if want.get(r, set()) is not None:
                want.setdefault(r, set()).add(n)
        else:
            raise SystemExit(f"unknown recipe or item id: {n} (see build.py --list)")
    return want


# ------------------------------------------------------------------ research/items.md: first level + role

def research_index():
    """slug -> (first_level, role) from the research catalogue table."""
    p = os.path.join(APP, "research", "items.md")
    res = {}
    if not os.path.exists(p):
        return res
    for line in open(p):
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 3 or not re.match(r"L\d+", cols[1]):
            continue
        m = re.search(r"L(\d+)", cols[1])
        level = int(m.group(1))
        role = "goal" if re.search(r"\bgoals?\b", cols[1]) else "filler"
        names = re.sub(r"\(.*?\)", "", cols[0]).split("/")
        base = None
        for nm in (x.strip() for x in names):
            if not nm:
                continue
            if nm.startswith("-") and base:
                nm = base.rsplit("-", 1)[0] + nm
            base = nm
            res.setdefault(nm, (level, role))
    return res


# ------------------------------------------------------------------ build

def _jsonable(x):
    if isinstance(x, (list, tuple)):
        return [_jsonable(y) for y in x]
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if hasattr(x, "item") and not isinstance(x, (str, bytes)):
        try:
            return x.item()
        except Exception:
            pass
    return x


def build_recipe(recipe, only=None, out_dir=OUT, research=None):
    """Mesh each distinct geometry of the recipe once, write every selected id."""
    t0 = time.time()
    items = load_items(recipe)
    sel = [(k, it) for k, it in enumerate(items) if only is None or it.name in only]
    if only and len(sel) < len(only):
        missing = set(only) - {it.name for _, it in sel}
        raise SystemExit(f"{recipe}: build() does not return {sorted(missing)}")
    groups = {}
    for k, it in sel:
        groups.setdefault(geometry_key(it), []).append((k, it))
    research = research if research is not None else research_index()
    metas = []
    for members in groups.values():
        k0, rep = members[0]
        shared = f" (shared by {', '.join(m.name for _, m in members)})" if len(members) > 1 else ""
        print(f"[{rep.name}] building ({len(rep.parts)} parts, budget {rep.budget}){shared}")
        meshes, meta, (uv_, uf_), outline = build_item(rep, recipe=recipe, item_index=k0)
        poses = stable_poses(uv_, uf_)
        hulls = convex_hulls(meshes)
        geo_s = time.time() - t0
        for k, it in members:
            metas.append(write_member(recipe, it, rep, meshes, meta, outline, poses, hulls, out_dir, research, geo_s))
    return metas


def write_member(recipe, it, rep, meshes, meta0, outline, poses, hulls, out_dir, research, geo_s):
    t1 = time.time()
    name = it.name
    pms = [PartMesh(p, pm.v, pm.f, pm.n, pm.uv, pm.stats) for p, pm in zip(it.parts, meshes)]
    os.makedirs(out_dir, exist_ok=True)
    usdz = os.path.join(out_dir, f"{name}.usdz")
    write_usdz(name, pms, usdz)
    errs, warns = check_usdz(usdz)
    from palette import OUTLINE_LIME
    ousdz = os.path.join(out_dir, f"{name}.outline.usdz")
    write_outline_usdz(name, outline, OUTLINE_LIME, ousdz)
    oerrs, _ = check_usdz(ousdz)

    meta = json.loads(json.dumps(_jsonable(meta0)))
    meta["name"] = name
    meta["display_name"] = it.display_name or name
    for p, pm in zip(it.parts, meshes):
        meta["parts"][p.name]["material"] = p.material.name
    meta["icon_view"] = list(it.icon_view)
    slug = it.slug or name.replace("_", "-")
    lv, role = research.get(slug, (None, None))
    meta.update(
        recipe=recipe,
        slug=slug,
        variant_of=it.variant_of or (rep.name if it is not rep else None),
        first_level=it.first_level if it.first_level is not None else lv,
        role=it.role or role,
        materials=sorted({p.material.name for p in it.parts}),
    )
    allv = __import__("numpy").vstack([pm.v for pm in meshes])
    meta.update(tray_info(it, allv))
    meta["outline"] = dict(file=os.path.basename(ousdz), usd_errors=len(oerrs), **outline["stats"])
    meta["usd_check"] = dict(errors=errs, warnings=warns)
    meta["stable_poses"] = poses
    meta["collision_hulls"] = hulls
    meta["ref_poses"] = _jsonable(list(it.ref_poses))
    meta["icon_ref"] = _jsonable(it.icon_ref)
    meta["tray_ref"] = it.tray_ref
    meta["files"] = dict(usdz=os.path.basename(usdz), outline=os.path.basename(ousdz), json=f"{name}.json",
                         icon=f"{name}_icon.png", icon_sticker=f"{name}_icon_sticker.png")
    meta["build_seconds"] = round(geo_s + time.time() - t1, 2)
    meta["file_bytes"] = os.path.getsize(usdz)
    meta["built_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    _atomic_json(os.path.join(out_dir, f"{name}.json"), meta, indent=1)
    o = meta["outline"]
    print(f"[{name}] {meta['triangles']} tris / {meta['vertices']} verts, "
          f"bbox {[round(b - a, 3) for a, b in zip(meta['bbox_min'], meta['bbox_max'])]}, "
          f"{meta['file_bytes'] // 1024} KB, usdchecker errors: {len(errs)} | outline {o['tris']} tris "
          f"closed {o['closed']} manifold {o['manifold']} | tray x{meta['tray_scale']} "
          f"{meta['tray_fit']['size_pt']} pt ({meta['tray_fit']['limited_by']}) | L{meta['first_level']} {meta['role']}"
          + (f" | variant of {meta['variant_of']}" if meta["variant_of"] else ""))
    for e in errs + oerrs:
        print("   USD ERROR:", e)
    return meta


def _atomic_json(path, obj, **kw):
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w") as fh:
        json.dump(obj, fh, **kw)
    os.replace(tmp, path)


# ------------------------------------------------------------------ catalogue

def write_catalog(out_dir=OUT):
    """art/out/catalog.json from every <id>.json in out_dir (safe to run from parallel lanes)."""
    items = {}
    for fn in sorted(os.listdir(out_dir)):
        if not fn.endswith(".json") or fn == "catalog.json" or fn.startswith("_") or ".tmp" in fn:
            continue
        try:
            m = json.load(open(os.path.join(out_dir, fn)))
        except Exception:
            continue
        if "triangles" not in m or "name" not in m:
            continue
        name = m["name"]
        files = m.get("files") or dict(usdz=f"{name}.usdz", json=fn, icon=f"{name}_icon.png", icon_sticker=f"{name}_icon_sticker.png")
        present = {k: v for k, v in files.items() if os.path.exists(os.path.join(out_dir, v))}
        o = m.get("outline") or {}
        items[name] = dict(
            display_name=m.get("display_name", name), recipe=m.get("recipe"), variant_of=m.get("variant_of"),
            first_level=m.get("first_level"), role=m.get("role"),
            length=m.get("length"), tris=m.get("triangles"), outline_tris=o.get("tris"),
            outline_ok=bool(o.get("closed") and o.get("manifold")) if o else False,
            tray_scale=m.get("tray_scale"), tray_size_pt=(m.get("tray_fit") or {}).get("size_pt"),
            board_scale=m.get("board_scale", 1.0),
            files=present, missing=sorted(set(files) - set(present)),
            usd_errors=len((m.get("usd_check") or {}).get("errors", [])), built_at=m.get("built_at"),
        )
    by_level = {}
    for k, v in items.items():
        by_level.setdefault(str(v["first_level"]), []).append(k)
    cat = dict(generated=datetime.datetime.now().isoformat(timespec="seconds"), count=len(items),
               note="files are relative to art/out/; regenerated by build.py (and preview.py after icons)",
               items=items, by_level={k: sorted(v) for k, v in sorted(by_level.items(), key=lambda kv: (len(kv[0]), kv[0]))})
    _atomic_json(os.path.join(out_dir, "catalog.json"), cat, indent=1)
    return cat


# ------------------------------------------------------------------ re-pose (no remesh)

def usdz_points(path):
    """Every Mesh prim's points of a shipped usdz, in the item frame (COM origin, final scale)."""
    import numpy as np
    from pxr import Usd, UsdGeom
    st = Usd.Stage.Open(path)
    pts = []
    for prim in st.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            v = np.array(UsdGeom.Mesh(prim).GetPointsAttr().Get(), float)
            M = np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()), float)
            pts.append((np.c_[v, np.ones(len(v))] @ M)[:, :3])
    return np.vstack(pts)


def repose(ids, out_dir=OUT):
    """Recompute <id>.json stable_poses from the shipped usdz (stable poses depend only on the convex hull and the COM,
    which is the usdz origin), without remeshing. Used after the art-director round-2 change to stable_poses."""
    import trimesh
    for i in ids:
        jp = os.path.join(out_dir, f"{i}.json")
        up = os.path.join(out_dir, f"{i}.usdz")
        if not (os.path.exists(jp) and os.path.exists(up)):
            print(f"[{i}] skipped (not built)")
            continue
        h = trimesh.convex.convex_hull(usdz_points(up))
        poses = stable_poses(h.vertices, h.faces)
        if not poses:
            print(f"[{i}] no poses computed, kept")
            continue
        meta = json.load(open(jp))
        old = [p["probability"] for p in meta.get("stable_poses", [])]
        meta["stable_poses"] = poses
        _atomic_json(jp, meta, indent=1)
        print(f"[{i}] poses {old} -> {[p['probability'] for p in poses]}")


# ------------------------------------------------------------------ CLI

def main():
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="*", help="recipe names or item ids")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true", help="print recipes and the ids they emit")
    ap.add_argument("--catalog", action="store_true", help="only regenerate art/out/catalog.json")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--repose", action="store_true", help="only recompute stable_poses of built ids from their usdz")
    a = ap.parse_args()
    if a.repose:
        ids = sorted(json.load(open(os.path.join(a.out, "catalog.json")))["items"]) if a.all else \
            [i for r, only in resolve(a.items).items() for i in (only or recipe_ids(r))]
        repose(ids, a.out)
        return
    if a.list:
        for r in recipes():
            try:
                print(f"{r}: {', '.join(recipe_ids(r))}")
            except Exception as e:
                print(f"{r}: ERROR {e}")
        return
    if a.catalog:
        c = write_catalog(a.out)
        print(f"catalog: {c['count']} items -> {os.path.join(a.out, 'catalog.json')}")
        return
    want = {r: None for r in recipes()} if a.all else resolve(a.items)
    if not want:
        print("recipes:", ", ".join(recipes()))
        return
    research = research_index()
    failed = []
    for r, only in want.items():
        try:
            build_recipe(r, only, a.out, research)
        except SystemExit:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            failed.append(r)
    c = write_catalog(a.out)
    print(f"catalog: {c['count']} items -> {os.path.join(a.out, 'catalog.json')}")
    if failed:
        raise SystemExit(f"FAILED: {', '.join(failed)}")


if __name__ == "__main__":
    main()
