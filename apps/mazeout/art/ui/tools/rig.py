#!/usr/bin/env python3
"""Cut-out puppet rigs for characters (pipeline feature; characters lane request 2 in art/lanes/requests.md).

    PY=~/.venvs/mf3d/bin/python
    $PY art/ui/tools/rig.py --recipes art/pipeline/items --list
    $PY art/ui/tools/rig.py --recipes art/pipeline/items doc                 # render layers + export + proof
    $PY art/ui/tools/rig.py --recipes art/pipeline/items doc --skip-render   # re-export from the last renders
    $PY art/ui/tools/ui3d.py --recipes art/pipeline/items --rig doc          # same, through ui3d

A recipe declares RIGS = {name: spec}; the output shape is the characters lane's (char_make.py), adopted as-is:
  art/out/<dir>/<layer>@3x.png  every layer trimmed to its alpha bbox (1 px pad)
  art/out/<dir>/rig.json        {character, frame_pt, full, placement_pt, note,
                                 layers: [{name, file, z, rect_pt [x, y, w, h], pivots_pt {k: [x, y]}, group?, default?,
                                           overlay?, parent?, note?}],
                                 groups: {group: {members: [...], default: name}}, proof: {mean_abs, pct_gt40}}
  art/ui/sheets/char_<name>_puppet.png   full | painter's composite | |diff| x4
  art/ui/sheets/rig_<name>_layers.png    every layer on a checker, labelled, with its pivots
<dir> = spec["dir"] or "char_<name>_rig". Points are pt inside the frame (origin top-left), layers back -> front.

Two ways to declare the layers
  explicit (char_doc.py):  spec = dict(full=<ASSETS case>, layers=[(layer, <ASSETS case>), ...], layer_notes={...})
      every layer case uses the FULL case's view: scene entries with center=False, the same explicit `bounds`,
      `no_fit=True`, the same light/fov, dest="parts"; pivots = the case's `anchors` (3D points, projected).
  auto (new recipes):      spec = dict(auto=dict(factory=f, kw={}, pose=dict(yaw, pitch), frame=(w, h) pt,
                                                 margin=1.08, fov=18, light={...}, layers=[...]))
      factory(**kw) -> parts or (parts, voxel); each layer = dict(name, parts={names} | callable(Part) -> bool,
      kw={overrides, e.g. eyes="half"}, group, default, overlay, parent, pivots={k: [x, y, z]}, note).
      The tool injects the models and the full + layer cases (shared bounds from the full model's posed mesh bbox).
Layer flags: overlay = not in the proof composite (blink lids, an alternative arm); group + default = a swap set
(eyes open / half / closed, mouth shapes): only the default member joins the proof; parent = the layer it rides on;
holdout (auto mode, default "below") = the parts of the layers behind it are rendered as a MATTE (mfrender item
holdout: occludes, draws nothing), so eyes/mouths buried in the head carry only their visible pixels; False = off,
or a set of part names. Explicit cases get the same by adding (model, dict(pose, holdout=True)) to their scene.

BAKE (characters lane request 5; spec `bake=True`, or rig.py --bake / --no-bake to override): each layer is rendered
alone, so it misses its neighbours' cast shadows. Baking copies the full render's colour into every default layer where
that layer is top-most and (nearly) opaque; alpha is untouched, overlays and non-default group members are left as
rendered. The proof then compares the BAKED composite (sci_home: 1.39/255, 1.6 % px > 40 -> 0.12/255, 0.004 %) and
rig.json gains a `baked` note. Same maths as the lane's char_make.bake: do not bake twice (a spec with bake=True does
not need char_make's own bake step).

PREMESHED parts (request 4): a Part with a `premesh` callable -> (v, f, n, uv) (char_fur.fur_part) is meshed natively by
ui3d.mesh_parts, so rigs with fur render through rig.py / art_batch.py --rigs without the char_make driver.

Every render goes through ui3d (mfrender, the calibrated rig); USDZs are cached by recipe hash (local imports included).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ui3d  # noqa: E402
from uikit import APP, ART  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT_ART = os.path.join(ART, "out")
SHEETS = os.path.join(ART, "ui", "sheets")
PARTS = os.path.join(APP, "build", "ui-art", "parts")


def _font(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def rigs():
    out = {}
    for r in ui3d.recipe_names():
        m = ui3d._load(r)
        for name, spec in getattr(m, "RIGS", {}).items():
            out[name] = (r, spec)
    return out


# ------------------------------------------------------------------ auto mode: inject models + cases

def _inject_auto(mod, name, spec):
    """Turn spec['auto'] into explicit models / ASSETS cases on the loaded module; returns an explicit spec."""
    A = spec["auto"]
    fac = A["factory"]
    base_kw = A.get("kw", {})
    voxel0 = getattr(mod, "VOXEL", 0.006)

    def model_for(sel, kw):
        def fn():
            res = fac(**dict(base_kw, **kw))
            parts, vox = res if isinstance(res, tuple) else (res, voxel0)
            if sel is None:
                return parts, vox
            keep = [p for p in parts if (sel(p) if callable(sel) else p.name in sel)]
            if not keep:
                raise SystemExit(f"rig {name}: a layer selects no parts ({sel})")
            return keep, vox
        return fn
    full_model = f"rig_{name}_full"
    mod.MODELS[full_model] = model_for(None, {})
    pose = dict(A.get("pose", {}), center=False)
    # bounds: the posed full mesh bbox (meshed once, cached), grown by margin, matched to the frame aspect
    recipe = mod.__name__.replace("uirecipe_", "")
    u, meta = ui3d.model_usdz(recipe, mod, full_model)
    R = ui3d._look(pose.get("yaw", 0), pose.get("pitch", 0), pose.get("roll", 0))
    lo, hi = ui3d.posed_bounds([(meta, ui3d.mat4(R))])
    fw, fh = A["frame"]
    c = (lo + hi) / 2
    ext = (hi - lo) * A.get("margin", 1.08)
    asp = fw / fh
    if ext[0] / ext[1] > asp:
        ext[1] = ext[0] / asp
    else:
        ext[0] = ext[1] * asp
    bounds = (tuple((c - ext / 2).tolist()), tuple((c + ext / 2).tolist()))
    common = dict(bounds=bounds, frame=(fw, fh), fov=A.get("fov", 18), light=A.get("light"), no_fit=True)
    full_case = f"rig_{name}_full"
    mod.ASSETS[full_case] = dict(scene=[(full_model, pose)], **common)
    layers, notes = [], {}
    defaults = {}
    for L in A["layers"]:
        if L.get("group") and (L.get("default") or L["group"] not in defaults):
            defaults[L["group"]] = L["name"] if L.get("default") or L["group"] not in defaults else defaults[L["group"]]
    for i, L in enumerate(A["layers"]):
        mn = f"rig_{name}_{L['name']}"
        mod.MODELS[mn] = model_for(L["parts"], L.get("kw", {}))
        case = f"rig_{name}_L_{L['name']}"
        scene = [(mn, pose)]
        # holdout (default "below"): the parts of the layers BEHIND this one occlude it but render transparent, so a
        # layer carries only what the full render shows of it (no rims of eyes buried in the head)
        ho = L.get("holdout", "below")
        if ho:
            if ho == "below":
                sels = [M["parts"] for M in A["layers"][:i] if not M.get("overlay") and
                        (not M.get("group") or (M["group"] != L.get("group") and defaults.get(M["group"]) == M["name"]))]
            else:
                sels = [set(ho)]
            if sels:
                hm = f"rig_{name}_{L['name']}_holdout"
                mod.MODELS[hm] = model_for(lambda p, sels=sels: any((q(p) if callable(q) else p.name in q) for q in sels), {})
                scene.append((hm, dict(pose, holdout=True)))
        mod.ASSETS[case] = dict(scene=scene, dest="parts", **common)
        if L.get("pivots"):
            mod.ASSETS[case]["anchors"] = {k: [v] for k, v in L["pivots"].items()}
        layers.append((L["name"], case))
        notes[L["name"]] = {k: L[k] for k in ("group", "default", "overlay", "parent", "note") if k in L}
    out = dict(spec)
    out.update(full=full_case, layers=layers, layer_notes=dict(notes, **spec.get("layer_notes", {})))
    return out


# ------------------------------------------------------------------ export

def _alpha_bbox(im, thr=2):
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a > thr)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _sidecar(case):
    for p in (os.path.join(PARTS, f"{case}.json"), os.path.join(OUT_ART, f"{case}.json"), os.path.join(ui3d.OUT, f"{case}.json")):
        if os.path.exists(p):
            return json.load(open(p))
    return None


def _full_image(full_case, draft, full_dir, size=None):
    """The full render the layers must recompose (the draft render when draft), resized to `size` px if given."""
    fp = os.path.join(APP, "build", "ui-art", "draft", f"{full_case}.png") if draft else os.path.join(full_dir, f"{full_case}@3x.png")
    full = Image.open(fp).convert("RGBA")
    if size is not None and full.size != tuple(size):
        full = full.resize(tuple(size), Image.LANCZOS)
    return full


def _proof_stack(rj):
    """The layers the default pose shows, back -> front: no overlays, only the default member of each swap group."""
    defaults = {g["default"] for g in rj.get("groups", {}).values()}
    return [L for L in rj["layers"] if not L.get("overlay") and (not L.get("group") or L["name"] in defaults)]


def bake(d, rj, full):
    """Colour BAKE (characters lane request 5; the lane's char_make.bake adopted verbatim): every layer is rendered
    alone, so it lacks the cast shadows / bounce of its neighbours. Wherever a default layer is the TOP-MOST one in the
    default composite, its colour becomes the full render's (so the default pose recomposes the full render exactly,
    neighbours' shadows included); under a front layer the solo render is kept (seen only when the puppet moves).
    Alpha is untouched; only where the layer is (nearly) opaque (alpha > 0.6, ramped to 1.0) is the full colour taken,
    because a partly transparent edge pixel of the full render blends this layer with what lies behind it.
    Overlay layers and non-default group members are never touched. Rewrites the layer PNGs in `d` in place.
    full: PIL RGBA, exactly frame x 3 px."""
    fw, fh = rj["frame_pt"]
    W, H = round(fw * 3), round(fh * 3)
    full = np.asarray(full.convert("RGBA")).astype(np.float32) / 255
    if full.shape[:2] != (H, W):
        raise SystemExit(f"bake: full render is {full.shape[1]}x{full.shape[0]} px, frame is {W}x{H}")
    stack = _proof_stack(rj)
    imgs = {}
    for L in stack:
        cv = np.zeros((H, W, 4), np.float32)
        im = np.asarray(Image.open(os.path.join(d, L["file"])).convert("RGBA")).astype(np.float32) / 255
        x0, y0 = round(L["rect_pt"][0] * 3), round(L["rect_pt"][1] * 3)
        cv[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im[:H - y0, :W - x0]
        imgs[L["name"]] = (cv, x0, y0, im.shape)
    for i, L in enumerate(stack):
        cv, x0, y0, shp = imgs[L["name"]]
        front = np.ones((H, W), np.float32)
        for M in stack[i + 1:]:
            front *= 1 - imgs[M["name"]][0][..., 3]
        wgt = (front * (full[..., 3] > 0.02))[..., None]
        wgt = wgt * np.clip((cv[..., 3:4] - 0.6) / 0.4, 0, 1)
        cv[..., :3] = cv[..., :3] * (1 - wgt) + full[..., :3] * wgt
        out = cv[y0:y0 + shp[0], x0:x0 + shp[1]]
        Image.fromarray(np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(d, L["file"]), optimize=True)
    return len(stack)


def export(name, draft=False, force=False, skip_render=False, bake_layers=None):
    """Render (unless skip_render) + export one RIGS entry. bake_layers: None = the spec's `bake` (default False),
    True/False = force (rig.py --bake / --no-bake)."""
    recipe, spec = rigs()[name]
    mod = ui3d._load(recipe)
    if "auto" in spec:
        spec = _inject_auto(mod, name, spec)
    do_bake = bool(spec.get("bake", False)) if bake_layers is None else bool(bake_layers)
    full_case = spec["full"]
    cases = [full_case] + [c for _, c in spec["layers"]]
    for c in cases:  # registration contract: one shared view
        s = mod.ASSETS[c]
        if not s.get("no_fit") or "bounds" not in s or any(p.get("center", True) for _, p in s.get("scene", [("", {})])):
            raise SystemExit(f"rig {name}: case {c} must use scene entries with center=False, explicit bounds and no_fit=True")
    scratch_root = os.path.join(APP, "build", "ui-art", "rigs")
    full_dir = scratch_root if spec.get("scratch") else OUT_ART   # the full render ships next to the rig (art/out)
    os.makedirs(full_dir, exist_ok=True)
    old_out = ui3d.OUT
    ui3d.OUT = full_dir
    try:
        if not skip_render:
            for c in cases:
                t0 = time.time()
                ui3d.render_case(c, recipe, draft=draft, force=force, mod=mod)
                print(f"  ({time.time() - t0:.1f}s)")
    finally:
        ui3d.OUT = old_out
    fw, fh = mod.ASSETS[full_case]["frame"]
    # drafts and scratch rigs (examples, self-tests) never land in art/out
    root = scratch_root if (draft or spec.get("scratch")) else OUT_ART
    d = os.path.join(root, spec.get("dir", f"char_{name}_rig") + ("_draft" if draft else ""))
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        if f.endswith(".png"):
            os.remove(os.path.join(d, f))
    notes = spec.get("layer_notes", {})
    layers, groups = [], {}
    part_dir = os.path.join(APP, "build", "ui-art", "draft") if draft else PARTS
    for z, (lname, case) in enumerate(spec["layers"]):
        src = os.path.join(part_dir, f"{case}.png")
        im = Image.open(src).convert("RGBA")
        if draft:
            im = im.resize((round(fw * 3), round(fh * 3)), Image.LANCZOS)
        bb = _alpha_bbox(im)
        if bb is None:
            raise SystemExit(f"rig {name}: layer {lname} rendered empty ({src})")
        x0, y0, x1, y1 = bb
        x0, y0 = max(0, x0 - 1), max(0, y0 - 1)
        x1, y1 = min(im.width, x1 + 1), min(im.height, y1 + 1)
        fn = f"{lname}@3x.png"
        im.crop((x0, y0, x1, y1)).save(os.path.join(d, fn), optimize=True)
        e = dict(name=lname, file=fn, z=z, rect_pt=[round(x0 / 3, 3), round(y0 / 3, 3), round((x1 - x0) / 3, 3), round((y1 - y0) / 3, 3)])
        sj = _sidecar(case)
        if sj:
            e["pivots_pt"] = {k: v[0] for k, v in sj.items() if k not in ("case", "frame_pt", "note")}
            legacy = os.path.join(ui3d.OUT, f"{case}.json")   # ui3d also drops the sidecar in its OUT: keep OUT clean
            for p in (legacy, os.path.join(OUT_ART, f"{case}.json"), os.path.join(full_dir, f"{case}.json")):
                if os.path.exists(p) and os.path.dirname(p) != PARTS:
                    os.remove(p)
        e.update(notes.get(lname, {}))
        if e.get("group"):
            g = groups.setdefault(e["group"], dict(members=[], default=None))
            g["members"].append(lname)
            if e.get("default"):
                g["default"] = lname
        layers.append(e)
    for g in groups.values():   # a group without an explicit default shows its first member
        g["default"] = g["default"] or g["members"][0]
    placement = spec.get("placement")
    fs = _sidecar(full_case) or (json.load(open(os.path.join(OUT_ART, f"{full_case}.json")))
                                 if os.path.exists(os.path.join(OUT_ART, f"{full_case}.json")) else None)
    if spec.get("place") and fs:
        ax, ay = fs[spec["place"]["anchor"]][0]
        placement = dict(x=round(spec["place"]["at"][0] - ax, 2), y=round(spec["place"]["at"][1] - ay, 2),
                         how=f"frame top-left on the 393x852 pt screen: anchor {spec['place']['anchor']} at "
                             f"{list(spec['place']['at'])} pt")
    rj = dict(character=name, frame_pt=[fw, fh],
              note="rect_pt / pivots_pt: pt inside the frame, origin top-left; layers back -> front (z); every layer "
                   "shares the full render's camera, so drawing each at rect_pt recomposes the full render; overlay "
                   "layers and non-default group members are swapped in by the animation",
              full=os.path.relpath(os.path.join(full_dir, f"{full_case}@3x.png"), d), placement_pt=placement, layers=layers,
              groups=groups)
    nb = 0
    if do_bake:
        nb = bake(d, rj, _full_image(full_case, draft, full_dir, (round(fw * 3), round(fh * 3))))
    rj["proof"] = proof(name, full_case, d, rj, draft, full_dir, label="baked layers composited" if do_bake else None)
    if do_bake:
        rj["baked"] = "default layers carry the full render's colour where they are top-most (cast shadows included)"
    json.dump(rj, open(os.path.join(d, "rig.json"), "w"), indent=1)
    layer_sheet(name, d, rj)
    print(f"  rig {name}: {len(layers)} layers -> {os.path.relpath(d, APP)}; {f'baked {nb} layers; ' if do_bake else ''}"
          f"proof mean |d| {rj['proof']['mean_abs']}, {rj['proof']['pct_gt40']} % px > 40")
    return d


def compose(rig_dir, rj):
    fw, fh = rj["frame_pt"]
    cv = Image.new("RGBA", (round(fw * 3), round(fh * 3)), (0, 0, 0, 0))
    for L in _proof_stack(rj):
        im = Image.open(os.path.join(rig_dir, L["file"])).convert("RGBA")
        cv.alpha_composite(im, (round(L["rect_pt"][0] * 3), round(L["rect_pt"][1] * 3)))
    return cv


def proof(name, full_case, d, rj, draft=False, full_dir=OUT_ART, label=None):
    comp = compose(d, rj)
    full = _full_image(full_case, draft, full_dir, comp.size)
    bg = Image.new("RGBA", full.size, (98, 132, 214, 255))
    a = np.asarray(Image.alpha_composite(bg, full).convert("RGB")).astype(float)
    b = np.asarray(Image.alpha_composite(bg, comp).convert("RGB")).astype(float)
    diff = np.abs(a - b).max(2)
    res = dict(mean_abs=round(float(diff.mean()), 3), pct_gt40=round(float((diff > 40).mean() * 100), 3))
    W, H = full.size
    strip = Image.new("RGB", (W * 3 + 40, H + 40), (236, 236, 240))
    strip.paste(Image.fromarray(a.astype(np.uint8)), (10, 30))
    strip.paste(Image.fromarray(b.astype(np.uint8)), (W + 20, 30))
    strip.paste(Image.fromarray(np.clip(diff * 4, 0, 255).astype(np.uint8)).convert("RGB"), (2 * W + 30, 30))
    ImageDraw.Draw(strip).text((10, 8), f"{name}: full | {label or 'layers composited'} | |diff| x4   mean {res['mean_abs']}/255, "
                                         f"{res['pct_gt40']} % px > 40", fill=(20, 20, 30), font=_font(16))
    os.makedirs(SHEETS, exist_ok=True)
    strip.save(os.path.join(SHEETS, f"char_{name}_puppet.png"), optimize=True)
    return res


def layer_sheet(name, d, rj):
    """Every layer on a checker at its rect inside the frame (so offsets read), labelled, pivots as red crosses."""
    fw, fh = rj["frame_pt"]
    W, H = round(fw * 3), round(fh * 3)
    s = min(1.0, 360 / max(W, H))
    tiles = []
    for L in rj["layers"]:
        ck = Image.new("RGB", (W, H), (255, 255, 255))
        dr = ImageDraw.Draw(ck)
        for y in range(0, H, 24):
            for x in range(0, W, 24):
                if (x // 24 + y // 24) % 2:
                    dr.rectangle([x, y, x + 23, y + 23], fill=(222, 222, 226))
        im = Image.open(os.path.join(d, L["file"])).convert("RGBA")
        ck.paste(im, (round(L["rect_pt"][0] * 3), round(L["rect_pt"][1] * 3)), im)
        for k, (px, py) in (L.get("pivots_pt") or {}).items():
            X, Y = px * 3, py * 3
            dr.line([X - 14, Y, X + 14, Y], fill=(230, 0, 0), width=3)
            dr.line([X, Y - 14, X, Y + 14], fill=(230, 0, 0), width=3)
            dr.text((X + 8, Y + 6), k, fill=(200, 0, 0), font=_font(16))
        ck = ck.resize((round(W * s), round(H * s)), Image.LANCZOS)
        lab = f"{L['z']}: {L['name']}" + (f" [{L['group']}]" if L.get("group") else "") + (" overlay" if L.get("overlay") else "")
        tiles.append((lab, ck))
    cols = min(4, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    tw, th = tiles[0][1].size
    out = Image.new("RGB", (cols * (tw + 20) + 20, rows * (th + 40) + 20), (236, 236, 240))
    dr = ImageDraw.Draw(out)
    for i, (lab, t) in enumerate(tiles):
        x, y = 20 + (i % cols) * (tw + 20), 20 + (i // cols) * (th + 40)
        dr.text((x, y), lab, fill=(20, 20, 30), font=_font(16))
        out.paste(t, (x, y + 22))
    os.makedirs(SHEETS, exist_ok=True)
    out.save(os.path.join(SHEETS, f"rig_{name}_layers.png"), optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--recipes", help="recipe directory (default art/ui/recipes)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-render", action="store_true")
    bk = ap.add_mutually_exclusive_group()
    bk.add_argument("--bake", dest="bake", action="store_true", default=None,
                    help="bake the full render's colour into the default layers (overrides the spec's `bake`)")
    bk.add_argument("--no-bake", dest="bake", action="store_false", help="never bake (overrides the spec's `bake`)")
    a = ap.parse_args()
    if a.recipes:
        ui3d.set_recipes(a.recipes)
    if a.list:
        for n, (r, s) in sorted(rigs().items()):
            n_l = len(s["layers"]) if "layers" in s else len(s.get("auto", {}).get("layers", []))
            print(f"{n}: recipe {r}, {n_l} layers, {'auto' if 'auto' in s else 'explicit'}{', bake' if s.get('bake') else ''}")
        return
    for n in a.names:
        export(n, draft=a.draft, force=a.force, skip_render=a.skip_render, bake_layers=a.bake)


if __name__ == "__main__":
    main()
