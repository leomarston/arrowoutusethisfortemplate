"""Art director (round 2) proofs: composed screens next to their references at GAME size, reusing grader B's composer
(gradeB_compose.home / loading) so the same stand-in chrome is used. Outputs art/ui/sheets/director/*.png (gitignored).
    cd apps/mazeout; ~/.venvs/mf3d/bin/python art/review/tools/director_proofs.py [home|window|loading|all]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gradeB_compose as G  # noqa: E402

SH = "art/ui/sheets/director"


def window():
    r = G.img("research/shots/002-home-L32.png")
    for p, ref in (("homeArrowPileFull", r), ("homeArrowPileHalf", G.img("research/shots/168-home-L055.png")),
                   ("homeArrowPileLow", G.img("research/shots/070-home-L40-skyjump-joined.png"))):
        h = G.home(ui=True, pile=p)
        G.crop_pair(h, ref, (90, 360, 305, 590), f"{SH}/win_{p}.png", k=3)


def home():
    r = G.img("research/shots/002-home-L32.png")
    h = G.home()
    h.save(f"{SH}/home_composed.png")
    G.pair(h, r, f"{SH}/p_home.png", labels=("ours (round 2)", "002 (looked at only)"))
    G.pair(h, r, f"{SH}/p_home_1x.png", k=1, labels=("ours", "002"))
    G.crop_pair(G.home(ui=False), r, (0, 150, 393, 620), f"{SH}/p_home_mid.png", k=2)
    G.crop_pair(h, r, (0, 480, 393, 852), f"{SH}/p_home_low.png", k=2)


def loading():
    rl = G.img("build/ui-art/refcrops/loadingBackdrop.png")
    lo = G.loading()
    lo.save(f"{SH}/loading_composed.png")
    G.pair(lo, rl, f"{SH}/p_loading.png", labels=("ours (round 2)", "V1 t=0 (looked at only)"))
    G.pair(lo, rl, f"{SH}/p_loading_1x.png", k=1, labels=("ours", "V1 t=0"))
    G.pair(lo, G.img("research/store/iphone-8.png"), f"{SH}/p_loading_s8.png", labels=("ours", "store 8"))


if __name__ == "__main__":
    os.makedirs(SH, exist_ok=True)
    what = sys.argv[1:] or ["all"]
    for w in ("window", "home", "loading"):
        if w in what or "all" in what:
            globals()[w]()


def loading_with(over, dst, box=(40, 250, 300, 560), k=3):
    """The loading proof with some cast renders replaced (e.g. drafts): over = {layout case: image path}."""
    import json
    lo = G.img("art/out/loadingBackdrop@3x.png").copy()
    lay = json.load(open("art/out/char_loading_layout.json"))["characters"]
    for name, c in sorted(lay.items(), key=lambda kv: kv[1]["z"]):
        G.put(lo, G.img(over.get(name, f"art/out/{c['file']}")), c["x"], c["y"])
    lg = G.img("art/ui/out/logoArrowOut@3x.png")
    s = 197.0 / (299.33 - 8.67)
    G.put(lo, lg, 21 - 8.67 * s, 65 - 1.67 * s, 306 * s, 236 * s)
    G.crop_pair(lo, G.img("build/ui-art/refcrops/loadingBackdrop.png"), box, dst, k=k)
    return lo


def box_proof(slab="build/ui-art/svgroute/boxW10H3.png", ring="build/ui-art/svgroute/boxRing.png",
              dst=f"{SH}/box_135.png"):
    """The phone BOX on 135 (L50, 10 x 3 cells, pitch 28.07): ours pasted over the capture at the cell block (ref | ours in
    place), 3 px/pt and a 1x view."""
    from PIL import Image
    r = G.img("research/shots/135-L050-start.png")
    s = 28.07 / 32.0
    x0, y0, x1, y1 = 56.7, 607.3, 336.0, 690.0
    ours = r.copy()
    sl = Image.open(slab).convert("RGBA")
    sl = sl.resize((round(sl.width * s), round(sl.height * s)), Image.LANCZOS)
    ours.alpha_composite(sl, (round((x0 - 4 * s) * 3), round((y0 - 4 * s) * 3)))
    rg = Image.open(ring).convert("RGBA")
    rg = rg.resize((round(rg.width * s), round(rg.height * s)), Image.LANCZOS)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ours.alpha_composite(rg, (round(cx * 3 - rg.width / 2), round(cy * 3 - rg.height / 2)))
    G.crop_pair(ours, r, (40, 590, 353, 705), dst, k=3)
    G.crop_pair(ours, r, (0, 150, 393, 852), dst.replace(".png", "_1x.png"), k=1)


def _paste_center(base, im, cx, cy, s=1.0):
    from PIL import Image
    im = Image.open(im).convert("RGBA") if isinstance(im, str) else im
    if s != 1.0:
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    base.alpha_composite(im, (round(cx * 3 - im.width / 2), round(cy * 3 - im.height / 2)))


def settings_proof(src="build/ui-art/svgroute", dst=f"{SH}/settings_meta029.png"):
    """meta-029 (Settings): the glyphs erased with a flat patch of their button face (proof only) and ours pasted at the
    glyph centres; the bell over the card colour."""
    from PIL import ImageDraw
    r = G.img("research/shots/meta-029-settings.png")
    ours = r.copy()
    dr = ImageDraw.Draw(ours)
    for cx, cy in ((91.7, 345.0), (196.7, 343.3), (300.0, 345.0)):
        dr.rounded_rectangle([round((cx - 23) * 3), round((cy - 21) * 3), round((cx + 23) * 3), round((cy + 21) * 3)], 30,
                             fill=(19, 205, 19, 255))
    dr.rounded_rectangle([round(40 * 3), round(160 * 3), round(78 * 3), round(203 * 3)], 10, fill=(38, 118, 244, 255))
    _paste_center(ours, f"{src}/glyphSoundWhite.png", 91.7, 345.0)
    _paste_center(ours, f"{src}/glyphMusic.png", 196.7, 343.3)
    _paste_center(ours, f"{src}/glyphHapticWhite.png", 300.0, 345.0)
    _paste_center(ours, f"{src}/glyphBell.png", 59.3, 181.7)
    G.crop_pair(ours, r, (30, 150, 363, 390), dst, k=3)
    G.crop_pair(ours, r, (0, 100, 393, 420), dst.replace(".png", "_1x.png"), k=1)


def profile_proof(src="build/ui-art/svgroute", dst=f"{SH}/profile_meta002.png"):
    from PIL import ImageDraw
    r = G.img("research/shots/meta-002-avatar-tap.png")
    ours = r.copy()
    dr = ImageDraw.Draw(ours)
    bg = (7, 38, 150, 255)
    dr.rectangle([round(28 * 3), round(335 * 3), round(86 * 3), round(395 * 3)], fill=bg)          # target
    dr.rectangle([round(218 * 3), round(335 * 3), round(262 * 3), round(398 * 3)], fill=bg)         # medal
    dr.ellipse([round(94 * 3), round(208 * 3), round(131 * 3), round(245 * 3)], fill=(30, 90, 220, 255))   # pencil
    _paste_center(ours, f"{src}/statFirstTryIcon.png", 57.0, 364.5)
    _paste_center(ours, f"{src}/statWeeklyWinsIcon.png", 241.0, 367.0)
    _paste_center(ours, f"{src}/iconPencil.png", 112.0, 227.0)
    G.crop_pair(ours, r, (20, 190, 380, 400), dst, k=3)


def sky_proof(dst=f"{SH}/sky_069.png"):
    from PIL import Image
    r = G.img("research/shots/069-skyjump-screen.png")
    bg = G.img("art/out/skyJumpBackdrop@3x.png").copy()
    for f, xy in (("art/out/skyJumpIslandFar@3x.png", (6, 222)), ("art/out/skyJumpIsland@3x.png", (66, 306)),
                  ("art/out/skyJumpPad@3x.png", (51, 503))):
        G.put(bg, G.img(f), *xy)
    G.crop_pair(bg, r, (0, 200, 393, 620), dst, k=2)
    p = G.img("art/out/skyJumpPopupScene@3x.png")
    r5 = G.img("research/shots/065-join-event.png")
    base = r5.copy().resize((393 * 3, 852 * 3))
    base.alpha_composite(p, (30 * 3, 270 * 3))
    G.crop_pair(base, r5, (20, 250, 373, 470), dst.replace("069", "065"), k=2)
