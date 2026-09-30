#!/usr/bin/env python3
"""R4 LOADING proofs (PLAN-P §4.2; ruling 46). The D1 Loading composed EXACTLY as LoadingScreen draws it (the backdrop
full-bleed on the 393 x 852 reference, the cast from art/out/char_loading_layout.json in z order, logoArrowOut at
ui.json frames.loading.logo, "Loading.." at text.loading.label), gated with tools/copygate.py (kind 'screen') against
the original's Loading (research/store/iphone-8.png, the calibrated pair) and LOOKED at at real size.
Research frames are references to LOOK at and to measure distance from; nothing is traced or sampled from them.

    PY=~/.venvs/mf3d/bin/python        # from apps/mazeout
    $PY art/review/tools/r4_loading.py proof [--draft]   # compose + gates -> art/review/loading/, proofs.json
    $PY art/review/tools/r4_loading.py layout            # write art/out/char_loading_layout.json from scene_loading_d1.LAYOUT
    $PY art/review/tools/r4_loading.py arrows            # the 7 recoloured arrowGlossy* sprites: sheet + hue check
    $PY art/review/tools/r4_loading.py manifest          # art/lanes/loading-d1.entries.json
"""
from __future__ import annotations

import json
import os
import sys

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
os.chdir(APP)
for p in ("tools", "tools/skin", "art/ui/recipes", "art/ui/tools", "art/pipeline"):
    sys.path.insert(0, os.path.join(APP, p))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

S = 3
DST = "art/review/loading"
PROOFS = os.path.join(DST, "proofs.json")
THEIRS = "research/store/iphone-8.png"
UI = "App/Resources/Tuning/ui.json"
os.makedirs(DST, exist_ok=True)


def ui_tokens():
    import skinlib                      # ui.json's colours are "@<ui id>" references into the skin (docs/SKIN.md)
    u = skinlib.resolve_ui_json(json.load(open(UI)))
    return u["frames"]["loading"], u["text"]["loading"]["label"]


def paste_pt(cv, im, x, y, w=None, h=None):
    if w is not None:
        im = im.resize((round(w * S), round(h * S)), Image.LANCZOS)
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    lay.paste(im, (round(x * S), round(y * S)))
    cv.alpha_composite(lay)


def draw_label(cv, text="Loading..", outline=None):
    """GameText's look, approximated with PIL: PCDisplay-Black, white face, the ui.json outline + a small drop; the word's
    left edge fixed so 'Loading' is centred on centreX (LoadingScreen)."""
    _, st = ui_tokens()
    oc = outline or st["outline"]
    oc = tuple(int(oc[i:i + 2], 16) for i in (1, 3, 5))
    f = ImageFont.truetype("App/Resources/Fonts/PCDisplay-Black.ttf", round(st["size"] * S))
    d = ImageDraw.Draw(cv)
    adv = d.textlength("Loading", font=f)
    left = st["centreX"] * S - adv / 2
    base = st["baseline"] * S
    sw = round(2.2 * S)
    d.text((left, base + st["drop"] * S * 2), text, font=f, fill=oc + (255,), anchor="ls", stroke_width=sw, stroke_fill=oc + (255,))
    d.text((left, base), text, font=f, fill=(255, 255, 255, 255), anchor="ls", stroke_width=sw, stroke_fill=oc + (255,))


def compose(backdrop, chars, logo=True, label=True):
    cv = Image.open(backdrop).convert("RGBA")
    assert cv.size == (393 * S, 852 * S), cv.size
    for c in sorted(chars, key=lambda c: c["z"]):
        im = Image.open(c["path"]).convert("RGBA")
        paste_pt(cv, im, c["x"], c["y"], c["w"], c["h"])
    if logo:
        fr, _ = ui_tokens()
        x, y, w, h = fr["logo"]
        paste_pt(cv, Image.open("art/ui/out/logoArrowOut@3x.png").convert("RGBA"), x, y, w, h)
    if label:
        draw_label(cv)
    return cv.convert("RGB")


def chars_from_layout(path, out_dir="art/out"):
    lay = json.load(open(path))["characters"]
    return [dict(path=os.path.join(out_dir, v["file"]), x=v["x"], y=v["y"], w=v["frame_pt"][0], h=v["frame_pt"][1],
                 z=v.get("z", 0), name=k) for k, v in lay.items()]


def chars_from_recipe():
    import scene_loading_d1 as LD
    return [dict(path=os.path.join("art/out", c["file"]), x=c["x"], y=c["y"], w=c["w"], h=c["h"], z=c["z"], name=n)
            for n, c in LD.layout_frames().items()]


def gate(ours, theirs=THEIRS, kind="screen", crop=None):
    import copygate as CG
    cfg = CG.load_config()
    m = CG.measure(ours, theirs, crop=crop, cmin=CG.kind_cmin(cfg, kind))
    j = CG.judge(m, kind, cfg)
    return dict(ours=ours, theirs=theirs, kind=kind, crop=crop, ssim=round(m["ssim"], 3), overlap=round(m["overlap"], 3),
                pass_=bool(j["pass"]))


def save_proof(key, val):
    d = json.load(open(PROOFS)) if os.path.exists(PROOFS) else {}
    d[key] = val
    json.dump(d, open(PROOFS, "w"), indent=1)


def registered_theirs():
    """Store 8 on the phone frame (scene_loading.py: scaled 0.8925, shifted (-6.5, -0.5) pt) at 1179 x 2556, to LOOK at."""
    st = Image.open(THEIRS).convert("RGB")
    s = 0.8925 * S / 3
    im = st.resize((round(st.width * s), round(st.height * s)), Image.LANCZOS)
    out = Image.new("RGB", (393 * S, 852 * S), (0, 0, 0))
    out.paste(im, (round(-6.5 * S), round(-0.5 * S)))
    return out


def today():
    """Today's Loading (the 09-27 backdrop + layout in build/p/R4/prev) with the CURRENT logo (green OUT!, ruling 48)."""
    prev = "build/p/R4/prev"
    return compose(f"{prev}/loadingBackdrop@3x.png", chars_from_layout(f"{prev}/char_loading_layout.json"))


def sheet(ims, labels, dst, h=1100):
    tiles = []
    for im in ims:
        tiles.append(im.resize((round(im.width * h / im.height), h), Image.LANCZOS))
    W = sum(t.width for t in tiles) + 24 * (len(tiles) + 1)
    sh = Image.new("RGB", (W, h + 70), (236, 236, 240))
    d = ImageDraw.Draw(sh)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26)
    x = 24
    for t, lb in zip(tiles, labels):
        sh.paste(t, (x, 56))
        d.text((x, 16), lb, font=f, fill=(30, 30, 40))
        x += t.width + 24
    sh.save(dst, optimize=True)
    return dst


def cmd_proof(draft=False):
    bd = "build/ui-art/scene/draft/loadingBackdrop.png" if draft else "art/out/loadingBackdrop@3x.png"
    chars = chars_from_recipe()
    if draft and os.path.exists("build/ui-art/scene/draft/char_digDockL.png"):
        for c in chars:
            if c["name"] == "char_digDockL":
                c["path"] = "build/ui-art/scene/draft/char_digDockL.png"
    tag = "draft" if draft else "final"
    ours = compose(bd, chars)
    dst = f"{DST}/loading-d1-{tag}.png"
    ours.save(dst, optimize=True)
    art_only = compose(bd, chars, logo=False, label=False)
    dst_art = f"build/p/R4/loading-d1-{tag}-artonly.png"
    art_only.save(dst_art)
    bd_only = f"build/p/R4/loading-d1-{tag}-backdrop.png"
    Image.open(bd).convert("RGB").save(bd_only)
    td = today()
    td_p = "build/p/R4/loading-today-greenlogo.png"
    td.save(td_p)
    res = [dict(state="D1 Loading as the app draws it", **gate(dst)),
           dict(state="D1 art only (no logo / label)", **gate(dst_art)),
           dict(state="D1 backdrop alone", **gate(bd_only)),
           dict(state="scene band y 230..760 (the cast + floor)", **gate(dst, crop=[0, 230, 393, 530])),
           dict(state="CONTROL today's Loading (green logo)", **gate(td_p))]
    for r in res:
        print(f"{r['state']:48s} SSIM {r['ssim']:.3f}  overlap {r['overlap']:.3f}  {'PASS' if r['pass_'] else 'FAIL'}")
    sheet([registered_theirs(), td, ours], ["original (store 8, registered)", "today (09-27 art, green logo)",
                                            f"D1 Loading ({tag})"], f"{DST}/sheet-{tag}.png")
    save_proof(tag, dict(note="LoadingScreen's composition (backdrop full-bleed, cast from scene_loading_d1.LAYOUT, logoArrowOut "
                              "at frames.loading.logo, 'Loading..' at text.loading.label) vs the original's Loading, kind "
                              "screen: SSIM < 0.30 and chroma overlap < 0.55 (tools/copygate.json)", gates=res,
                         sheet=f"{DST}/sheet-{tag}.png", composed=dst))
    return res


def cmd_layout():
    import scene_loading_d1 as LD
    fr = LD.layout_frames()
    chars = {}
    for n, c in fr.items():
        chars[n] = dict(file=c["file"], frame_pt=[c["w"], c["h"]], x=c["x"], y=c["y"], z=c["z"],
                        replaces=LD.LAYOUT[n][5])
    doc = dict(note="loading screen (R4 LOADING, D1; ruling 46: the same composition as the 09-27 Loading): frame top-left "
                    "x/y and frame_pt in pt on the 393 x 852 screen, z back -> front; each D1 figure takes the slot of the "
                    "figure it replaces (placed by its eye midpoint, art/ui/recipes/scene_loading_d1.py LAYOUT)",
               characters=chars)
    for n, c in chars.items():
        p = os.path.join("art/out", c["file"])
        assert os.path.exists(p), p
        w, h = Image.open(p).size
        ar_file, ar_frame = w / h, c["frame_pt"][0] / c["frame_pt"][1]
        assert abs(ar_file / ar_frame - 1) < 0.01, (n, ar_file, ar_frame)       # LoadingScreen stretches to the frame
    tmp = "art/out/char_loading_layout.json.tmp"
    json.dump(doc, open(tmp, "w"), indent=1)
    os.replace(tmp, "art/out/char_loading_layout.json")
    print(len(chars), "characters -> art/out/char_loading_layout.json")


def cmd_arrows():
    names = ["Yellow", "Orange", "Red", "Green", "Cyan", "Blue", "Purple"]
    rows = []
    for tag, d in (("before (build/p/R4/prev)", "build/p/R4/prev"), ("D1 (art/out)", "art/out")):
        tiles = []
        for n in names:
            im = Image.open(f"{d}/arrowGlossy{n}@3x.png").convert("RGBA")
            bg = Image.new("RGBA", im.size, (246, 240, 228, 255))
            bg.alpha_composite(im)
            tiles.append(bg.convert("RGB"))
        rows.append((tag, tiles))
    W = 24 + sum(t.width // 2 + 12 for t in rows[0][1])
    sh = Image.new("RGB", (W, 2 * (150 + 50) + 20), (236, 236, 240))
    d = ImageDraw.Draw(sh)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
    y = 12
    for tag, tiles in rows:
        d.text((24, y), tag, font=f, fill=(30, 30, 40))
        x = 24
        for t in tiles:
            sh.paste(t.resize((t.width // 2, t.height // 2), Image.LANCZOS), (x, y + 36))
            x += t.width // 2 + 12
        y += 200
    sh.save(f"{DST}/arrows-d1.png", optimize=True)
    print(f"{DST}/arrows-d1.png")


def cmd_manifest():
    import scene_loading_d1 as LD
    ents = []
    w, h = Image.open("art/out/loadingBackdrop@3x.png").size
    ents.append(dict(id="loadingBackdrop", family="3d", route="C1", group="loading-win",
                     purpose="loading screen (D1 'Burrow Works'): a boarded teal vault under timber arch beams, copper pipes, "
                             "the yard doorway in warm daylight, the sorting machine (teal iron / brass / copper / timber), the "
                             "timber dock, sandstone flags, a hemp rope, D1 enamel flying block arrows",
                     screen="loading", size_pt=[393, 852], size_px=[w, h],
                     source="art/ui/recipes/scene_loading_d1.py:loadingBackdrop", file="art/out/loadingBackdrop@3x.png",
                     status="done", owner="scene", full_bleed=True,
                     notes="R4 LOADING (D1; ruling 46): same composition and object types as the 09-27 backdrop "
                           "(scene_loading.py stays the geometry source), materials/colours changed. Proofs "
                           "art/review/loading/ (copygate vs store 8 in proofs.json)."))
    x, y, fw, fh = LD.DOCK_FRAME
    ents.append(dict(id="digDockL", family="3d", route="C1", group="characters",
                     purpose="two small Diggers on the dock at the back left of the Loading screen (the map Digger and the "
                             "shovel Digger, R2's home-rig renders at ~0.4x, a touch of room haze)",
                     screen="loading", size_pt=[fw, fh], size_px=[round(fw * 3), round(fh * 3)],
                     source="art/ui/recipes/scene_loading_d1.py:char_digDockL", file="art/out/char_digDockL@3x.png",
                     status="done", owner="characters",
                     notes="R4 LOADING. Replaces char_workerCrowdLeft's slot in char_loading_layout.json."))
    cur = {e["id"]: e for e in json.load(open("art/MANIFEST.json"))["entries"] if "id" in e}
    fam = dict(yellow="sunflower", orange="tangerine", red="coral", green="mint", cyan="aqua", blue="deep teal",
               purple="berry")
    for n in ["Yellow", "Orange", "Red", "Green", "Cyan", "Blue", "Purple"]:
        i = f"arrowGlossy{n}"
        old = cur.get(i, {}).get("notes", "")
        add = (f" | R4 LOADING (D1): recoloured to D1 {fam[n.lower()]} enamel (3d-hud_arrows.py D1_SHADES['{n.lower()}']); "
               f"same id, shape, frame and light (the id keeps its old colour word)")
        ents.append(dict(id=i, purpose=f"glossy 3D arrow, D1 {fam[n.lower()]} (the id's colour word is the pre-D1 name)",
                         notes=old if add in old else old + add))
    json.dump(dict(version=1, title="R4 LOADING lane entries (the art director merges them into art/MANIFEST.json by id; "
                                    "arrowGlossy* rows only append a note)", entries=ents),
              open("art/lanes/loading-d1.entries.json", "w"), indent=1)
    print(len(ents), "entries -> art/lanes/loading-d1.entries.json")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "proof":
        cmd_proof(draft="--draft" in args)
    elif cmd == "layout":
        cmd_layout()
    elif cmd == "arrows":
        cmd_arrows()
    elif cmd == "manifest":
        cmd_manifest()
    else:
        raise SystemExit(__doc__)
