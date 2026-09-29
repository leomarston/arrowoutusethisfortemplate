#!/usr/bin/env python3
"""Characters lane driver: mesh + render the char_* recipes with the pipeline's ui3d.py / rig.py (imported, pointed
at art/pipeline/items at runtime), export cut-out puppet rigs, and build comparison sheets.

    PY=~/.venvs/mf3d/bin/python
    $PY art/pipeline/items/char_make.py list
    $PY art/pipeline/items/char_make.py render <case> [<case> ...] [--draft] [--force]
    $PY art/pipeline/items/char_make.py rig <name> [--draft] [--force] [--skip-render]
    $PY art/pipeline/items/char_make.py sheet <sheet name>          # SHEETS table of a recipe

Runtime patch (no shared file edited; art/lanes/requests.md): ui3d.mesh_parts learns PREMESHED parts (a Part with a
`premesh` callable -> (v, f, n, uv)), used by the fur strands (char_fur.py). Everything else goes through the
pipeline as-is: ui3d.set_recipes(items/), ui3d.OUT = art/out, rig.py's export (auto or explicit layers).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))           # art/pipeline/items
PIPE = os.path.dirname(HERE)
ART = os.path.dirname(PIPE)
APP = os.path.dirname(ART)
TOOLS = os.path.join(ART, "ui", "tools")
for _p in (TOOLS, PIPE, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import ui3d  # noqa: E402
from mesher import PartMesh  # noqa: E402

OUT = os.path.join(ART, "out")
SHEETS = os.path.join(ART, "ui", "sheets")

ui3d.set_recipes(HERE)
ui3d.OUT = OUT
_orig_mesh_parts = ui3d.mesh_parts


def _mesh_parts(parts, voxel, log=print, **kw):
    pre = [p for p in parts if p.__dict__.get("premesh") is not None]
    rest = [p for p in parts if p.__dict__.get("premesh") is None]
    out = _orig_mesh_parts(rest, voxel, log=log, **kw) if rest else []
    for p in pre:
        t0 = time.time()
        v, f, n, uv = p.premesh()
        out.append(PartMesh(p, np.asarray(v, np.float64), np.asarray(f, np.int64), np.asarray(n, np.float64),
                            None if uv is None else np.asarray(uv, np.float64), dict(tris=int(len(f)))))
        log(f"    {p.name:16s} {len(f):7d} tris  premeshed ({time.time() - t0:.1f}s)")
    return out


ui3d.mesh_parts = _mesh_parts


def _recipe_names():
    return sorted(f[:-3] for f in os.listdir(HERE)
                  if f.startswith("char_") and f.endswith(".py") and ui3d._is_recipe(os.path.join(HERE, f)))


ui3d.recipe_names = _recipe_names

import rig as RIG  # noqa: E402  (after the patches: rig.py shares this ui3d module)


def render(cases, draft=False, force=False):
    idx = ui3d.index()
    for c in cases:
        t0 = time.time()
        ui3d.render_case(c, idx[c], draft=draft, force=force)
        print(f"  ({time.time() - t0:.1f}s)")


def bake(d):
    """BAKE the full render into the default layers: wherever a layer is the top-most one in the default composite,
    its colour becomes the full render's (so the default pose recomposes the full render exactly, cast shadows of the
    other layers included -- rig.py renders each layer alone, without its neighbours' shadows); under a front layer
    the solo render is kept (seen only when the puppet moves). Alpha is untouched. Re-runs the proof."""
    rj = json.load(open(os.path.join(d, "rig.json")))
    fw, fh = rj["frame_pt"]
    W, H = round(fw * 3), round(fh * 3)
    full = np.asarray(Image.open(os.path.normpath(os.path.join(d, rj["full"]))).convert("RGBA")).astype(np.float32) / 255
    defaults = {g["default"] for g in rj.get("groups", {}).values()}
    stack = [L for L in rj["layers"] if not L.get("overlay") and (not L.get("group") or L["name"] in defaults)]
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
        # un-premultiplied colours: where the layer is partly transparent the full render's edge colour is a blend of
        # this layer and what lies behind it; only take the full colour where this layer is (nearly) opaque
        wgt = wgt * np.clip((cv[..., 3:4] - 0.6) / 0.4, 0, 1)
        cv[..., :3] = cv[..., :3] * (1 - wgt) + full[..., :3] * wgt
        out = cv[y0:y0 + shp[0], x0:x0 + shp[1]]
        Image.fromarray(np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(d, L["file"]), optimize=True)
    rj["baked"] = "default layers carry the full render's colour where they are top-most (cast shadows included)"
    name = rj["character"]
    rj["proof"] = _proof(name, d, rj)
    json.dump(rj, open(os.path.join(d, "rig.json"), "w"), indent=1)
    print(f"  baked {len(stack)} layers; proof mean |d| {rj['proof']['mean_abs']}, {rj['proof']['pct_gt40']} % px > 40")


def _proof(name, d, rj):
    full = Image.open(os.path.normpath(os.path.join(d, rj["full"]))).convert("RGBA")
    comp = RIG.compose(d, rj)
    bg = Image.new("RGBA", full.size, (98, 132, 214, 255))
    a = np.asarray(Image.alpha_composite(bg, full).convert("RGB")).astype(float)
    b = np.asarray(Image.alpha_composite(bg, comp).convert("RGB")).astype(float)
    diff = np.abs(a - b).max(2)
    res = dict(mean_abs=round(float(diff.mean()), 3), pct_gt40=round(float((diff > 40).mean() * 100), 3))
    Wd, Hd = full.size
    strip = Image.new("RGB", (Wd * 3 + 40, Hd + 40), (236, 236, 240))
    strip.paste(Image.fromarray(a.astype(np.uint8)), (10, 30))
    strip.paste(Image.fromarray(b.astype(np.uint8)), (Wd + 20, 30))
    strip.paste(Image.fromarray(np.clip(diff * 4, 0, 255).astype(np.uint8)).convert("RGB"), (2 * Wd + 30, 30))
    ImageDraw.Draw(strip).text((10, 8), f"{name}: full | baked layers composited | |diff| x4   mean {res['mean_abs']}/255, "
                                         f"{res['pct_gt40']} % px > 40", fill=(20, 20, 30), font=font(16))
    strip.save(os.path.join(SHEETS, f"char_{name}_puppet.png"), optimize=True)
    return res


def rig(name, draft=False, force=False, skip_render=False):
    d = RIG.export(name, draft=draft, force=force, skip_render=skip_render)
    if not draft:
        bake(d)
    # the lane's sheets are char_* (the pipeline writes rig_<name>_layers.png)
    src = os.path.join(SHEETS, f"rig_{name}_layers.png")
    if os.path.exists(src):
        os.replace(src, os.path.join(SHEETS, f"char_{name}_layers.png"))
    return d


# ------------------------------------------------------------------ sheets

def font(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def stats(im_rgba, thr=128, mask=None):
    """Median hue (deg), saturation, value and a 'spec' share (near-white low-sat pixels) over opaque pixels."""
    a = np.asarray(im_rgba.convert("RGBA")).astype(float) / 255
    m = a[..., 3] > thr / 255
    if mask is not None:
        m &= mask
    rgb = a[..., :3][m]
    if not len(rgb):
        return {}
    mx, mn = rgb.max(1), rgb.min(1)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    return dict(sat=round(float(np.median(s)), 3), val=round(float(np.median(mx)), 3),
                spec=round(float(((mx > 0.94) & (s < 0.25)).mean() * 100), 2))


def load_ref(ref):
    """ref = dict(shot=path rel to APP, box_px=(x0, y0, x1, y1), scale=px per pt of the shot (default 1178/393))."""
    return Image.open(os.path.join(APP, ref["shot"])).convert("RGBA")


def paste_pt(canvas, im3x, x_pt, y_pt, s_pt):
    """Paste an @3x image at (x_pt, y_pt) on a shot whose scale is s_pt px per pt."""
    sm = im3x.resize((max(1, round(im3x.width * s_pt / 3)), max(1, round(im3x.height * s_pt / 3))), Image.LANCZOS)
    canvas.alpha_composite(sm, (round(x_pt * s_pt), round(y_pt * s_pt)))
    return canvas


def sheet_rows(rows, title, dst, third=True):
    """rows: [(label, [(caption, PIL image), ...])] -> one PNG: each row's tiles at full size (+ a 1/3-size strip)."""
    tiles_h = []
    W = 0
    for lab, tiles in rows:
        h = max(t.height for _, t in tiles)
        w = 20 + sum(t.width + 20 for _, t in tiles)
        tiles_h.append(h)
        W = max(W, w)
    H = 50 + sum(h + 60 + (h // 3 + 20 if third else 0) for h in tiles_h)
    out = Image.new("RGB", (max(W, 900), H), (236, 236, 240))
    dr = ImageDraw.Draw(out)
    dr.text((20, 14), title, fill=(20, 20, 30), font=font(20))
    y = 50
    for (lab, tiles), h in zip(rows, tiles_h):
        dr.text((20, y), lab, fill=(20, 20, 30), font=font(17))
        x = 20
        for cap, t in tiles:
            dr.text((x, y + 22), cap, fill=(60, 60, 70), font=font(14))
            out.paste(t.convert("RGB"), (x, y + 40))
            if third:
                sm = t.resize((max(1, t.width // 3), max(1, t.height // 3)), Image.LANCZOS)
                out.paste(sm.convert("RGB"), (x, y + 50 + h))
            x += t.width + 20
        y += h + 60 + (h // 3 + 20 if third else 0)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    out.save(dst, optimize=True)
    print(dst)
    return dst


def _sheet_wk_home():
    """Both home workers vs store 7 (the standing pose ours copies; 002 is an animation frame) at game size, on the
    same backdrop, in context on the 002 clean plate, + the face swap groups."""
    import char_kit as CK
    import char_worker as CW
    s7 = CK.shot("research/store/iphone-7.png")
    plate, _ = CW.home_plate()
    rows = []
    for side, box in (("L", (0, 1380, 440, 1880)), ("R", (700, 1380, 1178, 1880))):
        d = os.path.join(OUT, f"char_wk_home{side}_blue_rig")
        rj = json.load(open(os.path.join(d, "rig.json")))
        defaults = {g["default"] for g in rj["groups"].values()}
        names = {L["name"] for L in rj["layers"] if not L.get("overlay") and (not L.get("group") or L["name"] in defaults)}
        comp, _ = CK.layer_composite(d, names)
        pl = rj["placement_pt"]
        flat = CK.on_shot(CK.flat_like(s7, box), comp, pl["x"], pl["y"])
        ctx = CK.on_shot(plate, comp, pl["x"], pl["y"])
        rows.append((f"home worker {side} ({'navy cap + walkie' if side == 'L' else 'green cap + glasses + clipboard'})",
                     [("reference store 7 at phone scale (looked at only)", s7.crop(box)),
                      ("ours (BLUE), same game size, their wall colour", flat.crop(box)),
                      ("ours on the 002 clean plate", ctx.crop(box))]))
        tiles = []
        base_layers = {L["name"] for L in rj["layers"] if not L.get("group") and not L.get("overlay")}
        for body in [m for m in rj["groups"]["body"]["members"]]:
            for eyes in rj["groups"]["eyes"]["members"]:
                comp, _ = CK.layer_composite(d, base_layers | {body, eyes})
                t = CK.on_shot(CK.flat_like(s7, box), comp, pl["x"], pl["y"]).crop(box)
                tiles.append((f"{body} + {eyes}", t.resize((t.width // 2, t.height // 2), Image.LANCZOS)))
        rows.append((f"worker {side}: swap groups (mouth x eyes), half size", tiles))
    return rows, "HOME WORKERS (blue) vs the original at game size -- 1 phone px = 1 px; 1/3-size reads under each row"


def _sheet_sci_fur():
    """The fur decision at game size: the reference head | A smooth skin + ripples | B strand cards (spike v1) | B as
    shipped (the home rig's head layers composited at the rig placement), all on the reference's backdrop."""
    import char_kit as CK
    base = CK.shot("research/shots/002-home-L32.png")
    box = (420, 480, 820, 830)
    ev = os.path.join(APP, "build", "ui-art", "char_evidence")
    tiles = [("reference 002 (looked at only)", base.crop(box))]
    wall = CK.flat_like(base, box)
    for fn, cap in (("fur_A_smooth_v1.png", "A: smooth SDF skin + noise ripples + tuft cones (rejected)"),
                    ("fur_B_strands_v1.png", "B: strand cards, spike v1")):
        im = Image.open(os.path.join(ev, fn)).convert("RGBA")
        # the spike frames were aligned by their silhouette bottom-centre on the reference's jowl bottom (620, 784)
        a = np.asarray(im)[..., 3] > 128
        ys, xs = np.nonzero(a)
        yb = ys.max(); xb = xs[ys > yb - 6].mean()
        t = wall.copy(); t.alpha_composite(im, (int(round(620 - xb)), int(round(784 - yb))))
        tiles.append((cap, t.crop(box)))
    d = os.path.join(OUT, "char_sci_home_rig")
    comp, rj = CK.layer_composite(d, {"torso", "armL", "armR", "headSmile"})
    pl = rj["placement_pt"]
    tiles.append(("B as shipped (home rig, v5)", CK.on_shot(wall, comp, pl["x"], pl["y"]).crop(box)))
    return [("fur technique at game size (1 phone px = 1 px)", tiles)], \
        "FUR: A (smooth + ripples) vs B (geometric strand cards) -- B chosen"


def _sheet_avatars():
    """The phone's Edit Profile set (meta-003 3 x 3 grid, cells 2-9; looked at only) | ours at game size (64 pt = 192 px,
    the manifest size), in the same order, + ours at the 44 pt top-bar size; the default silhouette (SVG) first."""
    import char_kit as CK
    import char_avatars as AV
    base = CK.shot("research/shots/meta-003-profile-edit.png")
    ox, oy = 180, 980
    cells = []
    for cy in (150, 415, 680):
        for cx in (135, 410, 680):
            cells.append(base.crop((ox + cx - 96, oy + cy - 96, ox + cx + 96, oy + cy + 96)))
    ids = AV.PROFILE_ORDER
    rows = [("reference: meta-003 Edit Profile cells (phone px, frame included; looked at only)",
             [(f"cell {i + 1}", c) for i, c in enumerate(cells)])]
    ours = []
    for i in ids:
        pth = os.path.join(ART, "ui", "out", f"{i}@3x.png") if i == "avatarDefault" else os.path.join(OUT, f"char_{i}@3x.png")
        ours.append((i, Image.open(pth).convert("RGBA") if os.path.exists(pth) else Image.new("RGBA", (192, 192), (255, 0, 0, 255))))
    rows.append(("ours at game size (64 pt = 192 px @3x), same order", ours))
    rows.append(("ours at the 44 pt top-bar / fan size", [(n, im.resize((132, 132), Image.LANCZOS)) for n, im in ours]))
    return rows, "AVATARS: the phone v552 Edit Profile set (workers BLUE, scientist PINK on a violet plate) vs theirs"


def _sheet_home_detail():
    """The COMPOSED home (the scene lane's layers via scene_proofs.home_stack, read-only, + our rigs) next to 002 at
    1 phone px = 1 px: scientist, left worker, right worker (ours | 002 | 50 % blend) -- the placement / scale check."""
    rec = os.path.join(ART, "ui", "recipes")
    if rec not in sys.path:
        sys.path.insert(0, rec)
    import scene_proofs as SP
    ours = SP.home_stack(False).convert("RGB")
    ref = Image.open(os.path.join(APP, "research", "shots", "002-home-L32.png")).convert("RGB").resize(ours.size)
    rows = []
    for lab, box in (("scientist (ours | 002 | blend)", (300, 470, 960, 960)), ("left worker", (0, 1340, 560, 1900)),
                     ("right worker", (620, 1340, 1179, 1900))):
        a, b = ours.crop(box), ref.crop(box)
        rows.append((lab, [("ours", a), ("002 (looked at only)", b), ("50 % blend", Image.blend(a, b, 0.5))]))
    return rows, "HOME composed (scene layers + characters rigs) vs 002 -- 1 phone px = 1 px"


BUILTIN_SHEETS = {"home_detail": _sheet_home_detail, "wk_home": _sheet_wk_home, "sci_fur": _sheet_sci_fur, "avatars": _sheet_avatars}


def sheet(name):
    """A recipe's SHEETS[name]() builds its rows (it knows its references); this saves art/ui/sheets/char_<name>.png."""
    if name in BUILTIN_SHEETS:
        rows, title = BUILTIN_SHEETS[name]()
        return sheet_rows(rows, title, os.path.join(SHEETS, f"char_{name}.png"))
    for r in _recipe_names():
        m = ui3d._load(r)
        if name in getattr(m, "SHEETS", {}):
            rows, title = m.SHEETS[name]()
            return sheet_rows(rows, title, os.path.join(SHEETS, f"char_{name}.png"))
    raise SystemExit(f"no sheet {name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["render", "rig", "sheet", "list"])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-render", action="store_true")
    a = ap.parse_args()
    if a.cmd == "list":
        by = {}
        for c, r in ui3d.index().items():
            by.setdefault(r, []).append(c)
        for r, cs in sorted(by.items()):
            print(f"{r}: {', '.join(cs)}")
        print("rigs:", ", ".join(RIG.rigs()))
        return
    if a.cmd == "render":
        render(a.names, draft=a.draft, force=a.force)
    elif a.cmd == "rig":
        for n in a.names:
            rig(n, draft=a.draft, force=a.force, skip_render=a.skip_render)
    elif a.cmd == "sheet":
        for n in a.names:
            sheet(n)


if __name__ == "__main__":
    main()
