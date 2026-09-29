#!/usr/bin/env python3
"""R8 EVENT-ART driver + proofs (PLAN-P §4.2; owner items 14 + 15; SPEC ruling 46). Research shots are LOOKED AT only
(copygate thumbnails, side-by-side sheets).

    PY=~/.venvs/mf3d/bin/python        # from apps/mazeout
    $PY art/review/tools/r8_events.py build <id> [<id> ...] [--draft]   # scene_events_d1 BUILDS -> art/out | art/ui/out
    $PY art/review/tools/r8_events.py gate                              # the render gate (free swap, pressure, mfrender)

Render gate (PLAN-P §3 lane R): one 3-D render job at a time on the Mac -> refuse while another mfrender runs; free swap
>= 1 GB; memory pressure normal. The command exits (code 3) instead of waiting past the 4-minute command budget.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
os.chdir(APP)
for p in ("tools", "art/ui/recipes", "art/ui/tools", "art/pipeline", "art/pipeline/items", "art/review/tools"):
    sys.path.insert(0, os.path.join(APP, p))
os.environ.setdefault("MF_WORKERS", "2")

EV = "build/p/R8"
DRAFT = f"{EV}/draft"
os.makedirs(DRAFT, exist_ok=True)


def gate(min_free_mb=1024):
    out = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
    free = None
    for tok in out.replace("=", " ").split():
        pass
    try:
        free = float(out.split("free =")[1].split("M")[0])
    except Exception:
        free = 0.0
    pr = subprocess.run(["memory_pressure", "-Q"], capture_output=True, text=True).stdout
    pct = None
    for line in pr.splitlines():
        if "free percentage" in line:
            pct = int(line.strip().split()[-1].rstrip("%"))
    others = subprocess.run(["pgrep", "-fl", "build/art/mfrender"], capture_output=True, text=True).stdout.strip()
    ok = free >= min_free_mb and (pct is None or pct >= 20) and not others
    return ok, dict(free_swap_mb=free, mem_free_pct=pct, other_mfrender=others)


def build(ids, draft=False):
    import scene_events_d1 as E
    import scene_make as SM
    import scene_kit as K
    ctx = SM.Ctx(draft)
    for i in ids:
        if i not in E.BUILDS:
            raise SystemExit(f"unknown id {i}; known: {', '.join(sorted(E.BUILDS))}")
        paint_only = i in getattr(E, "PAINT_ONLY", set())
        ok, info = gate(min_free_mb=0 if paint_only else 1024)
        if not ok:
            print("RENDER GATE CLOSED before", i, info)
            sys.exit(3)
        t0 = time.time()
        im = E.BUILDS[i](ctx)
        if draft:
            dst = f"{DRAFT}/{i}.png"
        else:
            dst = os.path.join("art/out" if E.DEST.get(i, "art") == "art" else "art/ui/out", f"{i}@3x.png")
        K.save_png(im, dst)
        print(f"{i}: {im.size[0]}x{im.size[1]} -> {dst} ({time.time() - t0:.1f}s)", flush=True)


def queue(ids, draft=False):
    """Background runner: for each id wait (2-minute steps) until the render gate opens, then build it in its own process."""
    import scene_events_d1 as E
    for i in ids:
        paint_only = i in getattr(E, "PAINT_ONLY", set())
        while True:
            ok, info = gate(min_free_mb=0 if paint_only else 1024)
            if ok:
                break
            print(time.strftime("%H:%M:%S"), "waiting (gate closed)", i, info, flush=True)
            time.sleep(120)
        cmd = [sys.executable, os.path.abspath(__file__), "build", i] + (["--draft"] if draft else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        lines = [l for l in (r.stdout + r.stderr).splitlines() if "tris" not in l]
        print(time.strftime("%H:%M:%S"), i, "exit", r.returncode, "|", " / ".join(lines[-4:]), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "gate", "queue", "rig", "pages", "ua", "manifest", "handoff", "sheets", "pieces"])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    if a.cmd == "gate":
        print(gate())
    elif a.cmd == "build":
        build(a.ids, a.draft)
    elif a.cmd == "queue":
        queue(a.ids, a.draft)
    elif a.cmd == "rig":
        rig_badge(a.draft)
    elif a.cmd == "pages":
        res = gate_pages(a.ids or ["claw", "streakRace", "rocketRace", "rocketOffer", "skyJump", "skyOffer", "lb-weekly", "upaway"],
                         "draft" if a.draft else "final")
        json.dump(res, open(f"{EV}/copygate-{'draft' if a.draft else 'final'}.json", "w"), indent=1)
    elif a.cmd == "ua":
        print(ua_proof("draft" if a.draft else "final"))
    elif a.cmd == "manifest":
        print(lane_manifest(), "entries -> art/lanes/events-d1.entries.json")
    elif a.cmd == "sheets":
        pr = sheets("draft" if a.draft else "final")
        for r in pr["pages"]:
            print(r["page"], r["ssim"], r["overlap"], r.get("art"))
    elif a.cmd == "pieces":
        print(pieces_sheet())
    elif a.cmd == "handoff":
        handoff()
        print("art/lanes/events-d1.handoff.json")



# ============================================================================ Up & Away page proof (composed, no simulator)
# clouds between the ledge rows, right of the chests (page pt, top-left, 10 platforms)
UA_CLOUDS = {"balloonCloudA": [(250, 520), (240, 1250), (262, 1930), (236, 2620)], "balloonCloudB": [(290, 880), (284, 1600), (296, 2280)]}
UA_SKY_STOPS = [(0.0, "#0B2A33"), (0.40, "#1D5963"), (0.66, "#5FA3A0"), (0.84, "#F2C9A0"), (1.0, "#F8B98A")]   # D1 dusk (replaces B1's violet)
V582_SKY_STOPS = [(0.0, "#0E1450"), (0.45, "#3B2A8C"), (0.75, "#8C4FB8"), (1.0, "#F08BB0")]


def _grad(h, w, stops):
    import numpy as np
    from scene_kit import stops_interp
    t = np.linspace(0, 1, h)[:, None] * np.ones((1, w))
    return stops_interp(t, stops)


def ua_page(src="draft", count=0, scale=3, sky=UA_SKY_STOPS, chrome=True):
    """The whole Up & Away page (393 x 3 734 pt) at `scale` px/pt from the pieces, stacked the way the handoff tells A4 to
    (+ a mock of B1's code-drawn track / milestones / chests / live 'Step N' so the proof reads in place)."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    import scene_events_d1 as E
    d = DRAFT if src == "draft" else None

    def piece(name):
        p = f"{DRAFT}/{name}.png" if src == "draft" else (f"art/out/{name}@3x.png" if os.path.exists(f"art/out/{name}@3x.png") else f"art/ui/out/{name}@3x.png")
        im = Image.open(p).convert("RGBA")
        return im if scale == 3 else im.resize((round(im.width * scale / 3), round(im.height * scale / 3)), Image.LANCZOS)
    W, H = 393, int(E.UA_H)
    S = scale
    sky = (np.clip(_grad(H * S, W * S, sky), 0, 1) * 255).astype(np.uint8)
    cv = Image.fromarray(sky, "RGB").convert("RGBA")
    # clouds (if built)
    for name, spots in (("balloonCloudA", UA_CLOUDS["balloonCloudA"]), ("balloonCloudB", UA_CLOUDS["balloonCloudB"])):
        p = f"{DRAFT}/{name}.png" if src == "draft" else f"art/ui/out/{name}@3x.png"
        if os.path.exists(p):
            c = piece(name)
            for x, y in spots:
                cv.alpha_composite(c, (int(x * S), int(y * S)))
    shaft = piece("balloonTowerShaft")
    y = E.UA_SHAFT_Y0
    while y < H - E.UA_FOOT_H + 1:
        cv.alpha_composite(shaft, (0, int(round(y * S))))
        y += E.UA_PITCH
    cv.alpha_composite(piece("balloonTowerTop"), (0, 0))
    cv.alpha_composite(piece("balloonTowerFoot"), (0, int(round((H - E.UA_FOOT_H) * S))))
    dr = ImageDraw.Draw(cv)
    font = ImageFont.truetype("App/Resources/Fonts/PCDisplay-Black.ttf", int(15 * S))
    font2 = ImageFont.truetype("App/Resources/Fonts/PCDisplay-Black.ttf", int(17 * S))
    ledge = piece("balloonLedge")
    chests = ["stageChestPink", "stageChestBlue", "stageChestGreen", "stageChestPink", "stageChestBlue"]
    plats = [2, 5, 8, 13, 20, 28, 36, 46, 77, 120]
    ground = E.UA_GROUND
    if chrome:
        # B1's track: dark rail + green fill to the count
        top_y = E.ua_ledge_y(9) - 40
        dr.rounded_rectangle((int((34 - 11) * S), int(top_y * S), int((34 + 11) * S), int((ground + 3) * S)), radius=int(11 * S), fill=(26, 18, 66, 255))
    for i in range(10):
        ly = E.ua_ledge_y(i)
        cv.alpha_composite(ledge, (int(60 * S), int((ly - 94) * S)))
        if chrome:
            ch = Image.open(f"art/ui/out/{chests[i % 5]}@3x.png").convert("RGBA")
            ch = ch.resize((int(78 * S), int(78 * S * ch.height / ch.width)), Image.LANCZOS)
            cv.alpha_composite(ch, (int((60 + 146) * S), int((ly - 94 + 92) * S) - ch.height))
            t = f"Step {i + 1}"
            tw = dr.textlength(t, font=font)
            dr.text(((60 + 76) * S - tw / 2, (ly - 94 + 118) * S), t, font=font, fill=(255, 255, 255, 255), stroke_width=int(1.1 * S), stroke_fill=(10, 60, 56, 255))
            # milestone cloud (mock of B1's code shape)
            cx, cy = 34 * S, ly * S
            dr.ellipse((cx - 25 * S, cy - 17 * S, cx + 25 * S, cy + 17 * S), fill=(227, 218, 255, 255))
            n = str(plats[i]); tw = dr.textlength(n, font=font2)
            dr.text((cx - tw / 2, cy - 11 * S), n, font=font2, fill=(255, 255, 255, 255), stroke_width=int(1.2 * S), stroke_fill=(58, 42, 140, 255))
    if chrome:
        cx, cy = 34 * S, ground * S
        dr.ellipse((cx - 25 * S, cy - 17 * S, cx + 25 * S, cy + 17 * S), fill=(156, 245, 90, 255))
        dr.text((cx - 5 * S, cy - 11 * S), "0", font=font2, fill=(255, 255, 255, 255), stroke_width=int(1.2 * S), stroke_fill=(29, 107, 0, 255))
    hero = piece("balloonHero")
    by = ground if count == 0 else E.ua_ledge_y(0) + (ground - E.ua_ledge_y(0)) * (1 - count / 2)
    cv.alpha_composite(hero, (int((285 - 75) * S), int((by - 220) * S)))
    return cv


def ua_proof(src="draft"):
    import numpy as np
    from PIL import Image
    import scene_events_d1 as E
    os.makedirs("art/review/events", exist_ok=True)
    page = ua_page(src, scale=3)
    H = int(E.UA_H)
    bottom = page.crop((0, (H - 852) * 3, 393 * 3, H * 3))
    top = page.crop((0, 0, 393 * 3, 852 * 3))
    mid = page.crop((0, (H - 852 - 700) * 3, 393 * 3, (H - 700) * 3))
    tag = "draft" if src == "draft" else "final"
    for n, im in (("bottom", bottom), ("mid", mid), ("top", top)):
        im.convert("RGB").save(f"{EV}/upaway-{n}-{tag}.png")
    thumb = page.resize((393 // 2, H // 2), Image.LANCZOS)
    thumb.convert("RGB").save(f"{EV}/upaway-page-{tag}.png")
    return [f"{EV}/upaway-{n}-{tag}.png" for n in ("bottom", "mid", "top")]


# ============================================================================ event pages in place (from our 09-27 captures)
# Our pages as the build draws them are not re-captured here (no simulator in R8): the 09-27 captures (build/compare/captures,
# today's art + today's chrome) are split into ART and UI -- the art layers are re-drawn at the rects the Swift views use,
# every pixel that differs from them is UI -- then the UI pixels get R9's palette map (tools/palette_map.recolor_pixels, the
# preview of what A5's codemod does) and the NEW art goes under them. Lettering in these captures still shows the pre-T1
# names ("Claw Challenge" ...): the shipped build draws our names (live text).
def _art_file(name, src):
    for p in ((f"{DRAFT}/{name}.png",) if src == "draft" else ()) + (f"art/out/{name}@3x.png", f"art/ui/out/{name}@3x.png",
                                                                       f"art/out/char_{name}@3x.png"):
        if os.path.exists(p):
            return p
    raise FileNotFoundError(name)


def _place(canvas, path, rect, mode="fit", S=3):
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    x, y, w, h = rect
    iw, ih = im.size[0] / S, im.size[1] / S
    k = max(w / iw, h / ih) if mode == "fill" else min(w / iw, h / ih)
    nw, nh = iw * k, ih * k
    ox, oy = x + (w - nw) / 2, y + (h - nh) / 2
    spr = im.resize((max(1, round(nw * S)), max(1, round(nh * S))), Image.LANCZOS)
    if mode == "fill":       # clipped to the rect
        cx0, cy0 = round((x - ox) * S), round((y - oy) * S)
        spr = spr.crop((cx0, cy0, cx0 + round(w * S), cy0 + round(h * S)))
        ox, oy = x, y
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(spr, (round(ox * S), round(oy * S)))
    canvas.alpha_composite(layer)


SKY_PLATES = [((220.0, 750.0), 1.12), ((297.0, 675.0), 1.04), ((189.0, 615.0), 0.95), ((107.5, 558.0), 0.93)]


def _sky_layers(p):
    L = [(p("backdrop"), (0, 0, 393, 852), "fill"), (p("far"), (6, 222, 166, 158), "fit"), (p("far2"), (213, 214, 144, 132), "fit")]
    for (cx, cy) in ((182, 330), (236, 320), (287, 410)):
        L.append((p("pad"), (cx - 22, cy - 20.5, 44, 41), "fit"))
    L.append((p("island"), (66, 306, 260, 256), "fit"))
    for (cx, cy), k in SKY_PLATES:
        L.append((p("pad"), (cx - 56.5 * k, cy - 62.5 * k, 112 * k, 104 * k), "fit"))
    return L


PAGES = {
    "claw": dict(ref="research/shots/meta-039-claw-screen.png", kind="screen",
                 layers=lambda p: [(p("clawHeaderArt|treasureHeader"), (0, 0, 393, 243.5), "fill")]),
    "streakRace": dict(ref="research/shots/203-streak-race-leaderboard.png", kind="screen",
                       layers=lambda p: [(p("workerRacers|streakHeader"), (-18.2, 0, 429.4, 316.9), "fill")]),
    "rocketRace": dict(ref="research/shots/167-rocket-race-screen.png", kind="screen",
                       layers=lambda p: [(p("rocketRaceBackdrop|rallyBackdrop"), (0, 0, 393, 852), "fill")] +
                       [(p("rocketMine|rallyRocketMine" if i == 0 else "rocketOther|rallyRocketOther"),
                         (cx - 36.5, 630.5 - 44.5 * pr, 73, 103.4), "fit")
                        for i, (cx, pr) in enumerate(zip((39.3, 117.9, 196.5, 275.1, 353.7), (1, 4, 3, 2, 1)))]),
    "rocketOffer": dict(ref="research/shots/163-rocket-race-offer.png", kind="screen",
                        layers=lambda p: [(p("rocketOfferScene|rallyOfferScene"), (32, 188, 330, 504), "fill")]),
    "skyJump": dict(ref="research/shots/080-skyjump-levels1of5-players82.png", kind="screen",
                    layers=lambda p: _sky_layers(lambda k: p({"backdrop": "skyJumpBackdrop|hopBackdrop", "far": "skyJumpIslandFar|hopIslandFar",
                                                              "far2": "skyJumpIslandFar2|hopIslandFar2", "pad": "skyJumpPad|hopPad",
                                                              "island": "skyJumpIsland|hopIsland"}[k]))),
    "skyOffer": dict(ref="research/shots/065-join-event.png", kind="screen",
                     layers=lambda p: [(p("skyJumpPopupScene|hopOfferScene"), (24.3, 248, 344.6, 199), "fill")]),
    "lb-weekly": dict(ref="research/shots/132-weekly-contest-board.png", kind="screen",
                      layers=lambda p: [(p("leaderboardPodium|cupPodium"), (2, 294, 389, 206), "fit")]),
}


def page_proof(page, src="draft", thr=28):
    import numpy as np
    from PIL import Image, ImageFilter
    import palette_map as PM
    spec = PAGES[page]
    cap = Image.open(f"build/compare/captures/{page}-en.png").convert("RGBA")
    S = 3
    old = Image.new("RGBA", cap.size, (0, 0, 0, 0))
    new = Image.new("RGBA", cap.size, (0, 0, 0, 0))
    olds = spec["layers"](lambda pair: _art_file(pair.split("|")[0], "final"))
    def _new(pair):
        try:
            return _art_file(pair.split("|")[1], src)
        except FileNotFoundError:
            print("  (not built yet, old art kept:", pair, ")")
            return _art_file(pair.split("|")[0], "final")
    news = spec["layers"](_new)
    for (pth, rect, mode) in olds:
        _place(old, pth, rect, mode, S)
    for (pth, rect, mode) in news:
        _place(new, pth, rect, mode, S)
    c = np.asarray(cap.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float64)
    o = np.asarray(old.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float64)
    oa = np.asarray(old).astype(np.float64)[..., 3] / 255.0
    diff = np.abs(c[..., :3] - o[..., :3]).max(-1)
    art = (oa > 0.97) & (diff < thr)
    # opening (drop thin 'UI' specks that are resampling differences), then a slight shrink of the art (UI edges keep
    # their anti-aliasing from the capture)
    m = Image.fromarray((art * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    art_k = np.asarray(m).astype(np.float64)[..., None] / 255.0
    ui = np.asarray(PM.recolor_pixels(cap)).astype(np.float64)
    nw = np.asarray(new).astype(np.float64)
    na = nw[..., 3:4] / 255.0
    under = ui * (1 - na) + nw[..., :3] * na                     # new art over the (recoloured) capture
    out = under * art_k + ui * (1 - art_k)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")
    tag = "draft" if src == "draft" else "final"
    os.makedirs(f"{EV}/pages", exist_ok=True)
    dst = f"{EV}/pages/{page}-{tag}.png"
    img.save(dst)
    Image.fromarray((art_k[..., 0] * 255).astype(np.uint8)).save(f"{EV}/pages/{page}-artmask.png")
    return dst


def gate_pages(pages, src="draft"):
    import copygate as CG
    cfg = CG.load_config()
    res = []
    for pg in pages:
        if pg == "upaway":
            ours = ua_proof(src)[0]
            ref, kind = "build/p/PH0/024-balloon-bottom.png", "screen"
        else:
            ours = page_proof(pg, src)
            ref, kind = PAGES[pg]["ref"], PAGES[pg]["kind"]
        m = CG.measure(ours, ref, cmin=CG.kind_cmin(cfg, kind))
        j = CG.judge(m, kind, cfg)
        res.append(dict(page=pg, ours=ours, theirs=ref, kind=kind, ssim=round(m["ssim"], 4), overlap=round(m["overlap"], 4), passed=j["pass"]))
        print(f"{'PASS' if j['pass'] else 'FAIL'} {pg:12s} {kind} ssim {m['ssim']:.3f} overlap {m['overlap']:.3f}", flush=True)
    return res


# ============================================================================ the Up & Away bar token as a rig (body + balloon)
def rig_badge(draft=False):
    """eventBadgeBalloon's layers -> art/out/badge_upaway_rig/ (rig.json + motion.json + layer PNGs), R3's badge-rig format.
    The full image (art/ui/out/eventBadgeBalloon@3x.png) is the two layers composited (built by `build eventBadgeBalloon`)."""
    import numpy as np
    from PIL import Image
    import scene_events_d1 as E
    import scene_make as SM
    ok, info = gate()
    if not ok:
        print("RENDER GATE CLOSED:", info)
        sys.exit(3)
    L = E.badge_layers(SM.Ctx(draft))
    d = f"{DRAFT}/badge_upaway_rig" if draft else "art/out/badge_upaway_rig"
    os.makedirs(d, exist_ok=True)
    W, H = E.BADGE_F
    layers = []
    for z, (name, note) in enumerate((("body", "brass hex plate + teal enamel face (static)"),
                                      ("balloon", "the balloon + basket: the idle bob (translateY)"))):
        im = L[name]
        a = np.asarray(im)[..., 3]
        ys, xs = np.nonzero(a > 0)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        im.crop((x0, y0, x1, y1)).save(f"{d}/{name}@3x.png", optimize=True)
        entry = dict(name=name, file=f"{name}@3x.png", z=z, rect_pt=[round(x0 / 3, 3), round(y0 / 3, 3), round((x1 - x0) / 3, 3),
                                                                        round((y1 - y0) / 3, 3)], note=note)
        if name == "balloon":
            entry["pivots_pt"] = {"basket": [23.0, round(y1 / 3, 3)]}
        layers.append(entry)
    rig = dict(character="badge_upaway", frame_pt=[W, H],
               note="rect_pt / pivots_pt: pt inside the frame, origin top-left; layers back -> front (z); both layers share the "
                    "full render's camera, so drawing each at rect_pt recomposes the full image",
               full="../eventBadgeBalloon@3x.png", placement_pt=None, layers=layers)
    json.dump(rig, open(f"{d}/rig.json", "w"), indent=1)
    motion = dict(cycle=4.0, note="idle: the balloon bobs +-1 pt on a 4.0 s sine loop",
                  tracks=[dict(layer="balloon", prop="translateY", t=[0.0, 1.0, 2.0, 3.0, 4.0], v=[0.0, -1.0, 0.0, 1.0, 0.0],
                               curve="sine")])
    json.dump(motion, open(f"{d}/motion.json", "w"), indent=1)
    full = Image.new("RGBA", (int(W * 3), int(H * 3)), (0, 0, 0, 0))
    for e in layers:
        full.alpha_composite(Image.open(f"{d}/{e['file']}").convert("RGBA"), (round(e["rect_pt"][0] * 3), round(e["rect_pt"][1] * 3)))
    ref = Image.open(f"{DRAFT}/eventBadgeBalloon.png" if draft else "art/out/eventBadgeBalloon@3x.png").convert("RGBA")
    fa, ra = np.asarray(full).astype(float), np.asarray(ref).astype(float)
    pm = lambda x: np.concatenate([x[..., :3] * x[..., 3:4] / 255.0, x[..., 3:4]], -1)
    diff = np.abs(pm(fa) - pm(ra))
    print("rig ->", d, "recompose vs the full image (premultiplied, /255): max", round(float(diff.max()), 2), "p99.9",
          round(float(np.percentile(diff, 99.9)), 2))
    return d



# ============================================================================ lane manifest + handoff
R8_ENTRIES = [
    # id, family, route, group, size_pt, dir, replaces, purpose, full_bleed
    ("treasureHeader", "3d", "C1", "events-claw", [393, 240], "art/out", "clawHeaderArt",
     "Treasure Climb page header: a timber-framed prize cabinet (teal felt back, brass-capped posts, lantern strip), a brass claw, "
     "the prize heap in D1 colours, R2's two cheering Diggers (char_digClawPair)", True),
    ("streakHeader", "3d", "C1", "events-streak", [393, 290], "art/out", "workerRacers",
     "Hot Streak page header: R2's three Diggers in mine carts (char_digRacers) on timber trestle tracks out of a burrow tunnel "
     "portal; teal rock cavern, pit props, string lights, lanterns, crystals", True),
    ("rallyBackdrop", "3d", "C1", "events-rocket", [393, 852], "art/out", "rocketRaceBackdrop",
     "Rocket Rally page backdrop: deep-teal night, copper-banded + ringed mint planets, a sandstone moon, the hoard (iron-strapped "
     "timber chest, coins, hearts) on a teal-grey rock, the lanes' deep teal", True),
    ("rallyOfferScene", "3d", "C1", "events-rocket", [330, 504], "art/out", "rocketOfferScene",
     "Rocket Rally offer popup field: the rally world (teal night, copper planet, sandstone moon, the hoard) over a cream / apricot cloud bank", True),
    ("rallyRocketMine", "3d", "B3", "events-rocket", [68, 98], "art/ui/out", "rocketMine",
     "the player's race rocket: tangerine body, teal nose / band / fins, brass porthole (live count on the glass), painted exhaust", False),
    ("rallyRocketOther", "3d", "B3", "events-rocket", [68, 98], "art/ui/out", "rocketOther",
     "the rivals' race rocket: cream body, teal trim, brass porthole, painted exhaust", False),
    ("hopBackdrop", "3d", "C1", "events-skyjump", [393, 852], "art/out", "skyJumpBackdrop",
     "Cloud Hop page backdrop: a dawn sky (deep teal -> mint -> apricot) over cream / apricot cloud banks with mint shadows", True),
    ("hopIsland", "3d", "C1", "events-skyjump", [260, 256], "art/out", "skyJumpIsland",
     "Cloud Hop prize island: a floating earth islet (moss top, timber rim, copper band, teal-rock underside), a timber/brass chest "
     "quilted teal heaped with coins, a carved timber arrow sign (blank: PRIZE + amount are live text), a tangerine pad", False),
    ("hopIslandFar", "3d", "C1", "events-skyjump", [166, 158], "art/out", "skyJumpIslandFar",
     "Cloud Hop far-left islet with a tangerine-quilted chest", False),
    ("hopIslandFar2", "3d", "C1", "events-skyjump", [144, 132], "art/out", "skyJumpIslandFar2",
     "Cloud Hop far-right islet (hazier) with a sunflower-quilted chest", False),
    ("hopPad", "3d", "C1", "events-skyjump", [112, 104], "art/out", "skyJumpPad",
     "Cloud Hop jump drum: tangerine cushion, cream rings, riveted brass belt, teal foot, blank teal plate (live number)", False),
    ("hopOfferScene", "3d", "C1", "events-skyjump", [330, 190], "art/out", "skyJumpPopupScene",
     "Cloud Hop offer popup art: a moss hill heaped with coins, the teal-quilted timber chest, the carved arrow sign, cream clouds", False),
    ("hopDrum", "3d", "B3", "profile-shop-settings", [57, 52], "art/ui/out", "iconSkyDrum",
     "the Cloud Hop drum on its own (Profile 'Cloud Hop Wins' stat icon)", False),
    ("cupPodium", "3d", "C1", "leaderboard", [389, 206], "art/out", "leaderboardPodium",
     "Weekly Cup podium: three timber-plank blocks under pewter-mint (2nd) / brass (1st) / copper (3rd) caps, blank hex rank badges", False),
    ("treasureToken", "3d", "B3", "home", [40, 40], "art/ui/out", "iconHexArrow",
     "Treasure Climb token (home bar, page bar, Continue?, payout flight, Profile): a riveted brass hex nut, teal enamel, a tangerine up-arrow", False),
    ("eventBadgeBalloon", "3d", "B3", "home", [46, 46], "art/out", None,
     "Up & Away token (the home bar's left end in an Up & Away week; Profile tile): the brass/teal hex plate with our patched "
     "balloon floating in it; rig art/out/badge_upaway_rig (body + balloon, bob +-1 pt / 4.0 s)", False),
    ("balloonHero", "3d", "C1", "events-balloon", [150, 220], "art/out", None,
     "Up & Away balloon: a patched-canvas envelope (tangerine / cream over sunflower / tangerine, a stitched teal belt, teal "
     "crown + skirt, two patches), hemp ropes, a brass burner, R2's wicker basket with the lamp-hat Digger (char_digBalloon)", False),
    ("balloonTowerTop", "3d", "C1", "events-balloon", [393, 470], "art/out", None,
     "Up & Away page top: stars, the tower's gallery (timber deck, posts, rope rail), a teal drum under a riveted copper dome with "
     "brass ribs, a brass telescope, a tangerine pennant; the masonry below (tiles with balloonTowerShaft)", True),
    ("balloonTowerShaft", "3d", "C1", "events-balloon", [112, 340], "art/ui/out", None,
     "Up & Away tower shaft (painted, tiles every 340 pt): teal-grey masonry cylinder, a timber ring at each ledge line, a lit "
     "window slit, a copper downpipe, the recessed track groove at x 19..49", True),
    ("balloonTowerFoot", "3d", "C1", "events-balloon", [393, 700], "art/out", None,
     "Up & Away page foot: the tower plinth with a burrow door + lantern, a plank walkway to the round timber launch pad on its "
     "braced post, a hillside town (half-timbered cottages, teal-slate roofs, lit windows, smoke), moss trees, far hills in haze", True),
    ("balloonLedge", "3d", "C1", "events-balloon", [240, 150], "art/ui/out", None,
     "Up & Away platform: a plank balcony on iron knee braces, a teal plank door in a stone arch with a brass porthole, a lantern "
     "post, a blank timber sign board on chains (live 'Step N')", False),
    ("balloonCloudA", "3d", "C1", "events-balloon", [150, 70], "art/ui/out", None, "Up & Away sky cloud (cream / apricot, mint shade)", False),
    ("balloonCloudB", "3d", "C1", "events-balloon", [100, 56], "art/ui/out", None, "Up & Away sky cloud, small", False),
]


R8_REFS = {   # what each new id is LOOKED AT against (the old art's own references; v582 phone shots for Up & Away)
    "treasureHeader": ("research/shots/meta-039-claw-screen.png", [0, 0, 393, 243]),
    "streakHeader": ("research/shots/203-streak-race-leaderboard.png", [0, 0, 393, 300]),
    "rallyBackdrop": ("research/shots/167-rocket-race-screen.png", [0, 0, 393, 852]),
    "rallyOfferScene": ("research/shots/163-rocket-race-offer.png", [32, 188, 362, 692]),
    "rallyRocketMine": ("research/shots/178-rocket-race-progress.png", None),
    "rallyRocketOther": ("research/shots/178-rocket-race-progress.png", None),
    "hopBackdrop": ("research/shots/069-skyjump-screen.png", [0, 0, 393, 852]),
    "hopIsland": ("research/shots/069-skyjump-screen.png", [66, 306, 326, 562]),
    "hopIslandFar": ("research/shots/069-skyjump-screen.png", [6, 222, 172, 380]),
    "hopIslandFar2": ("research/shots/069-skyjump-screen.png", [213, 214, 357, 346]),
    "hopPad": ("research/shots/080-skyjump-levels1of5-players82.png", None),
    "hopOfferScene": ("research/shots/065-join-event.png", [30, 270, 360, 460]),
    "hopDrum": ("research/shots/meta-002-avatar-tap.png", None),
    "cupPodium": ("research/shots/meta-013-leaderboard-weekly.png", [2, 294, 391, 500]),
    "treasureToken": ("research/shots/026-home-after-L32.png", None),
    "eventBadgeBalloon": ("build/p/PH0/000-status.png", None),
    "balloonHero": ("build/p/PH0/002-balloon-page-settled.png", None),
    "balloonTowerTop": ("build/p/PH0/016-scroll5.png", None),
    "balloonTowerShaft": ("build/p/PH0/008-balloon-scroll1.png", None),
    "balloonTowerFoot": ("build/p/PH0/024-balloon-bottom.png", None),
    "balloonLedge": ("build/p/PH0/008-balloon-scroll1.png", None),
    "balloonCloudA": ("build/p/PH0/008-balloon-scroll1.png", None),
    "balloonCloudB": ("build/p/PH0/008-balloon-scroll1.png", None),
}


def lane_manifest():
    ents = []
    for (i, fam, route, group, size, d, rep, purpose, fb) in R8_ENTRIES:
        e = dict(id=i, family=fam, route=route, group=group, purpose=purpose, screen=group.replace("events-", "event page "),
                 size_pt=size, size_px=[size[0] * 3, size[1] * 3], source=f"art/ui/recipes/scene_events_d1.py:{i}",
                 file=f"{d}/{i}@3x.png", status="done", owner="events-d1",
                 notes=("R8 EVENT-ART (D1, ruling 46: today's composition and object types, restyled). " +
                        (f"Replaces {rep} at A4's mapping step (art/lanes/events-d1.handoff.json)." if rep else
                         "NEW (Up & Away; B1's UpAwayArt ids / A4's page pieces, art/lanes/events-d1.handoff.json).")))
        if fb:
            e["full_bleed"] = True
        if i in R8_REFS:
            shot, box = R8_REFS[i]
            e["ref"] = dict(shot=shot, box_pt=box) if box else dict(shot=shot)
        ents.append(e)
        if i == "eventBadgeBalloon":
            r = dict(e, id="eventBadgeBalloonLayers", file="art/out/badge_upaway_rig", rig=True,
                     purpose="the Up & Away token as layers for the idle loop: body (hex plate) + balloon (bob +-1 pt / 4.0 s, motion.json)")
            r.pop("size_px", None)
            ents.append(r)
    doc = dict(version=1, title="R8 EVENT-ART lane (scene_events_d1.py): D1 event art + Up & Away", entries=ents)
    json.dump(doc, open("art/lanes/events-d1.entries.json", "w"), indent=1)
    return len(ents)


def _ink(path):
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGBA"))[..., 3]
    ys, xs = np.nonzero(a > 8)
    H, W = a.shape
    return [round(xs.min() / W, 4), round(ys.min() / H, 4), round((xs.max() + 1) / W, 4), round((ys.max() + 1) / H, 4)]


def handoff():
    import scene_events_d1 as E
    sites = {}
    for (i, fam, route, group, size, d, rep, purpose, fb) in R8_ENTRIES:
        if rep:
            out = subprocess.run(["grep", "-rn", "--include=*.swift", "--include=*.json", "--exclude-dir=.build", "-E",
                                  rf"\.{rep}\b|\"{rep}\"", "App", "Tests", "UITests", "Packages"],
                                 capture_output=True, text=True).stdout.strip().splitlines()
            sites[rep] = sorted({l.split(":")[0] + ":" + l.split(":")[1] for l in out if "UIArt.swift" not in l})
    H = E.UA_H
    doc = {
        "about": "R8 EVENT-ART (PLAN-P §4.2; owner items 14 + 15; ruling 46) -> A4 ART-INTEG (then A5 for the palette). Today's event "
                 "compositions and object types in D1 materials + the NEW Up & Away page art. Every file is NEW (nothing existing "
                 "was changed); the ids they replace become NOT-SHIPPED at A4's step (grep App/ Tests/ UITests/ Packages/ first: "
                 "the sites are listed per id). Lane manifest: art/lanes/events-d1.entries.json (director merges). Recipes: "
                 "art/ui/recipes/scene_events_d1.py (scene_make.py RECIPES += scene_events_d1); proofs + gate: "
                 "art/review/tools/r8_events.py; sheets art/review/events/.",
        "ids": {rep: dict(new=i, file=f"{d}/{i}@3x.png", size_pt=size, sites=sites.get(rep, []))
                for (i, fam, route, group, size, d, rep, purpose, fb) in R8_ENTRIES if rep},
        "trophyCup": "keep the id, but point its one site (WeeklyViews.swift:108, the Weekly Cup (i)) at R3's navCup art (a gold cup "
                     "with a teal star on a timber plinth): today's trophyCup keeps the original's red-arrow emblem. No new file.",
        "treasureToken_ink": dict(note="S2Chrome.swift:35 ink table: iconHexArrow's alpha-bbox fractions -> the token's (re-measured "
                                       "from the file, same method); ContinuePopup InkImage uses them", value=_ink("art/ui/out/treasureToken@3x.png")
                                  if os.path.exists("art/ui/out/treasureToken@3x.png") else None),
        "upaway": {
            "ungate": "EventRotationPolicy.swift UpAwayArt: ids = [eventBadgeBalloon, balloonHero, balloonTowerTop, balloonTowerShaft, "
                      "balloonTowerFoot, balloonLedge] (drop `backdrop`: the page ships as pieces, see below). With those in the "
                      "generated UIArt table `UpAwayArt.ready` is true and Release runs Up & Away (B1's art gate).",
            "badge": dict(id="eventBadgeBalloon", frame_pt=[46, 46], placed="BalloonBar: home.clawHexArt inset -3 (as today)",
                          rig="art/out/badge_upaway_rig (body + balloon; motion.json = the balloon's +-1 pt bob on a 4.0 s sine "
                              "loop, v582 PH-0b R7)"),
            "hero": dict(id="balloonHero", frame_pt=[150, 220],
                         draw="BalloonTower: UpAwayArtImage(id: balloonHero).frame(width: 150, height: 220).position(x: 285, "
                              "y: balloonY - 110) (today 150 x 190 / -95: the basket bottom stays on the count's height); the win "
                              "strip / (i) keep their own frames (the art is .fit)"),
            "page_pieces": dict(
                note="the page stays B1's geometry (sky 330 + ground gap 94 + 340 per platform + street 250). Draw back -> front "
                     "INSIDE BalloonTower (it scrolls): sky gradient, clouds, shaft tiles, top, foot, ledges, B1's track + milestones "
                     "+ counter, chests, 'Step N' text, the hero, the bubble.",
                sky=dict(replaces="BalloonSky's 4 stops (#0E1450 / #3B2A8C / #8C4FB8 / #F08BB0)", stops=UA_SKY_STOPS),
                top=dict(id="balloonTowerTop", frame_pt=[393, E.UA_TOP_H], at=[0, 0]),
                shaft=dict(id="balloonTowerShaft", frame_pt=[E.SHAFT_W, E.UA_PITCH],
                           at="x 0, y = 470 + 340 k for k = 0, 1, ... while y < height - 700 (10 platforms: 8 tiles); drawn "
                              "BEFORE top + foot (they overlap the first / last tile; the masonry is one periodic paint, so every "
                              "join is seamless)"),
                foot=dict(id="balloonTowerFoot", frame_pt=[393, E.UA_FOOT_H], at="x 0, y = height - 700 (ground line at local 450 "
                          "= groundY)", note="carries the launch pad under the balloon (x 285, top = groundY) and the walkway: "
                          "DELETE B1's two code capsules (the pad) at groundY"),
                ledge=dict(id="balloonLedge", frame_pt=list(E.LEDGE_F), at="(60, y(platform: i) - 94) = BalloonLedge's own frame origin",
                           replaces="BalloonLedge's code-drawn purple bar + blue sign + posts (keep its chest button box "
                                    "(146, 22, 78 x 70) and the live 'Step N' GameText: centre x 76, baseline 131, on the teal board "
                                    "at local (34..118, 112..140)); the frame grows 120 -> 150 tall"),
                clouds=dict(ids=["balloonCloudA", "balloonCloudB"], frames_pt=[[150, 70], [100, 56]],
                            suggested_at={k: [list(p) for p in v] for k, v in UA_CLOUDS.items()},
                            note="optional (v582 has a few clouds on the right); positions in page pt for 10 platforms"),
                track="B1's rail (x 34 +- 11) runs in the tower's recessed groove (x 19..49, brass edge trims) from y(last) - 40 "
                      "down to groundY; the '0' milestone sits on the groove at the ground line",
                memory_decoded_mb=dict(top=round(393 * 3 * E.UA_TOP_H * 3 * 4 / 1e6, 1), shaft=round(E.SHAFT_W * 3 * E.UA_PITCH * 3 * 4 / 1e6, 1),
                                       foot=round(393 * 3 * E.UA_FOOT_H * 3 * 4 / 1e6, 1), ledge=round(240 * 3 * 150 * 3 * 4 / 1e6, 1),
                                       single_backdrop_would_be=round(393 * 3 * H * 3 * 4 / 1e6, 1)),
                prewarm="decode all pieces behind the page's prewarm (SocialModel's page art list, today's 'UpAwayArt.ids' "
                        "entry) so the first open pays no decode; purge on leaving (ArtStore.purge) like the other event pages",
                idle="v582: the balloon drifts slightly while idle (not in B1's code): optional A4 track, +-1.5 pt x on a ~5 s sine"),
        },
        "rotation_chrome": "NEW ribbon + x2 gem stay CODE-DRAWN (B1: NewRibbon / DoubleGem, events.md §7.1 'no bitmaps'); they are "
                           "our own additions (the original has no rotation), so there is no copy distance to buy. D1 tokens for A5: "
                           "NEW keeps the danger-red family (#FF6A4A -> #E8231A, outline #7A0A00); the x2 gem moves to the D1 CTA "
                           "family (#FFE08A -> #FFB422 face, outline #8A3F00) with a brass rim #E3B04B.",
        "home_badges": "the three event home badges as layers (body / moving part / smoke) are R3's (art/lanes/home.handoff.json "
                       "'badges'); R8 adds the Up & Away bar token's rig (above). The Treasure Climb bar keeps its code chrome "
                       "(A5 palette) with treasureToken on its left end.",
        "unchanged_generic": ["stageChestGreen/Blue/Pink (chests; B1's ledges use them)", "planetStage1-3", "coinBowl + coin packs",
                              "rankBadge*", "statWeeklyWinsIcon", "rankWings1"],
        "not_shipped_after_A4": [rep for (i, fam, route, group, size, d, rep, purpose, fb) in R8_ENTRIES if rep] + ["workerClawPair"],
        "evidence": {"pages": "build/p/R8/pages/*-final.png (in place, R9 UI) + art/review/events/*.png sheets",
                     "copygate": "build/p/R8/copygate-final.json + art/review/events/proofs.json"},
    }
    json.dump(doc, open("art/lanes/events-d1.handoff.json", "w"), indent=1)
    return doc


# ============================================================================ sheets + proofs.json
ART_CROPS = {"claw": (0, 0, 393, 243.5), "streakRace": (0, 0, 393, 300), "lb-weekly": (0, 294, 393, 206),
             "rocketOffer": (32, 188, 330, 260), "skyOffer": (24.3, 248, 344.6, 199)}


def sheets(src="final"):
    from PIL import Image, ImageDraw, ImageFont
    import copygate as CG
    os.makedirs("art/review/events", exist_ok=True)
    cfg = CG.load_config()
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 22)
    tag = "draft" if src == "draft" else "final"
    proofs = {"note": "copygate (tools/copygate.py, kind screen: SSIM < 0.30 AND chroma overlap < 0.55) of our pages in place "
                      "(R8 art + R9's palette-map preview of the UI, from the 09-27 captures) vs the v552 page; 'baseline' = the same "
                      "page with TODAY's art + the R9 UI (what the art alone changes); 'art' = the art region only (crop)",
              "pages": []}
    rows = []
    for pg, spec in PAGES.items():
        ours = f"{EV}/pages/{pg}-{tag}.png"
        if not os.path.exists(ours):
            continue
        ref = spec["ref"]
        m = CG.measure(ours, ref)
        base = CG.measure(f"build/p/R9/preview/{pg}-mapped.png", ref) if os.path.exists(f"build/p/R9/preview/{pg}-mapped.png") else None
        today = CG.measure(f"build/compare/captures/{pg}-en.png", ref)
        mp = CG.measure(ours, ref, cmin=CG.kind_cmin(cfg, "page"))
        tp = CG.measure(f"build/compare/captures/{pg}-en.png", ref, cmin=CG.kind_cmin(cfg, "page"))
        rec = dict(page=pg, theirs=ref, ours=ours, ssim=round(m["ssim"], 3), overlap=round(m["overlap"], 3),
                   pass_=CG.judge(m, "screen", cfg)["pass"], today=dict(ssim=round(today["ssim"], 3), overlap=round(today["overlap"], 3)),
                   as_page_kind=dict(overlap_cmin8=round(mp["overlap"], 3), today_overlap_cmin8=round(tp["overlap"], 3),
                                     pass_=CG.judge(mp, "page", cfg)["pass"]))
        if base:
            rec["baseline_R9ui_today_art"] = dict(ssim=round(base["ssim"], 3), overlap=round(base["overlap"], 3))
        if pg in ART_CROPS:
            a = CG.measure(ours, ref, crop=ART_CROPS[pg])
            t = CG.measure(f"build/compare/captures/{pg}-en.png", ref, crop=ART_CROPS[pg])
            rec["art"] = dict(crop=ART_CROPS[pg], ssim=round(a["ssim"], 3), overlap=round(a["overlap"], 3),
                              pass_=CG.judge(a, "screen", cfg)["pass"], today=dict(ssim=round(t["ssim"], 3), overlap=round(t["overlap"], 3)))
        proofs["pages"].append(rec)
        rows.append((pg, [ref, f"build/compare/captures/{pg}-en.png", ours], rec))
    ua = f"{EV}/upaway-bottom-{tag}.png"
    if os.path.exists(ua):
        for view, ref in (("bottom", "build/p/PH0/024-balloon-bottom.png"), ("mid", "build/p/PH0/008-balloon-scroll1.png"),
                          ("top", "build/p/PH0/016-scroll5.png")):
            o = f"{EV}/upaway-{view}-{tag}.png"
            m = CG.measure(o, ref)
            rec = dict(page=f"upaway-{view}", theirs=ref, ours=o, ssim=round(m["ssim"], 3), overlap=round(m["overlap"], 3),
                       pass_=CG.judge(m, "screen", cfg)["pass"], note="v582 page (the original has Balloon Rise since v582)")
            proofs["pages"].append(rec)
            rows.append((f"upaway-{view}", [ref, None, o], rec))
    json.dump(proofs, open("art/review/events/proofs.json", "w"), indent=1)
    # page sheets: v552/v582 | today | ours (R8), one row per page
    W, H = 393, 852
    for pg, files, rec in rows:
        cv = Image.new("RGB", (W * 3 + 40, H + 60), (30, 30, 34))
        d = ImageDraw.Draw(cv)
        for k, (lab, f) in enumerate(zip(("THEIRS (look only)", "TODAY (09-27)", "OURS R8 in place"), files)):
            if f and os.path.exists(f):
                cv.paste(Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS), (k * (W + 20), 60))
            d.text((k * (W + 20) + 6, 8), lab, fill=(230, 230, 230), font=font)
        s = f"ssim {rec['ssim']}  overlap {rec['overlap']}" + (f"  | art {rec['art']['ssim']}/{rec['art']['overlap']}" if rec.get("art") else "")
        d.text((6, 32), s, fill=(255, 210, 120), font=font)
        cv.save(f"art/review/events/page-{pg}.png")
    return proofs


def pieces_sheet():
    """today's art | R8's replacement, per id, at 1x (1 px per pt), on a mid-teal ground; NEW ids alone."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
    cells = []
    for (i, fam, route, group, size, d, rep, purpose, fb) in R8_ENTRIES:
        new = f"{d}/{i}@3x.png"
        old = None
        if rep:
            for p in (f"art/out/{rep}@3x.png", f"art/ui/out/{rep}@3x.png", f"art/out/char_{rep}@3x.png"):
                if os.path.exists(p):
                    old = p
        cells.append((rep or "(new)", old, i, new))
    rows = []
    for rep, old, i, new in cells:
        ims = [Image.open(p).convert("RGBA") for p in (old, new) if p]
        k = min(1.0, 420.0 / max(im.height for im in ims)) if ims else 1
        ims = [im.resize((max(1, round(im.width / 3 * k * 1.5)), max(1, round(im.height / 3 * k * 1.5))), Image.LANCZOS) for im in ims]
        w = sum(im.width for im in ims) + 30 * len(ims) + 10
        h = max(im.height for im in ims) + 30
        cv = Image.new("RGBA", (w, h), (40, 90, 96, 255))
        dr = ImageDraw.Draw(cv)
        x = 10
        labels = ([rep] if old else []) + [i]
        for lab, im in zip(labels, ims):
            cv.alpha_composite(im, (x, 24))
            dr.text((x, 4), lab, fill=(255, 240, 200), font=font)
            x += im.width + 30
        rows.append(cv)
    W = 1800
    lines, cur, cw = [], [], 0
    for r in rows:
        if cw + r.width > W and cur:
            lines.append(cur)
            cur, cw = [], 0
        cur.append(r)
        cw += r.width + 8
    lines.append(cur)
    H = sum(max(r.height for r in ln) + 8 for ln in lines)
    sheet = Image.new("RGBA", (W, H), (24, 24, 28, 255))
    y = 0
    for ln in lines:
        x = 0
        for r in ln:
            sheet.alpha_composite(r, (x, y))
            x += r.width + 8
        y += max(r.height for r in ln) + 8
    sheet.convert("RGB").save("art/review/events/pieces.png")
    return "art/review/events/pieces.png"

if __name__ == "__main__":
    main()
