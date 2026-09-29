"""icon_v2 -- the app-icon OPTIONS after the owner rejected IC-1 (SPEC.md ruling 45, 2026-09-28 06:21):
"The app icon is unaccaptable, I dont want this, change it to something simpler like mazeout".

Rules (ruling 45 + art-direction.md §5): SIMPLE -- a few bold GLOSSY 3-D arrows with our in-game arrow quality (the
`arrowGlossy*` pipeline: `3d-hud_arrows.arrow_part` = extruded outline + painted hue-shifted bevel/walls, the same
material and ARROW_LIGHT rig), a clean ground (flat / soft gradient, painted in post_fit), no character, no scene, no
text, readable at 40 pt, and NOT Maze Out's composition (theirs: three horizontal glossy arrows yellow -> / red <- /
blue -> stacked on white; ours before: blue <- / red -> / yellow ^ on white, also too close). research/store/icon-1024.png
was only LOOKED at; nothing traced or sampled.

Four options (1024 px, opaque RGB, full bleed):
  iconOptA  "Round the Bend"  one fat tangerine PATH arrow (our board arrow's shape: round-capped tail, round outer join,
                              triangle head) turning a corner, on a D1 teal ground
  iconOptB  "Loop"            two bent path arrows, tangerine + cyan, interlocked round a square loop (each head passes
                              OVER the other's tail in depth), on a deep boss-pink berry ground
  iconOptC  "Breakout"        one big diagonal sunflower arrow lifting off a small cream board tile with a 4 x 4 dot
                              lattice, on a green ground
  iconOptD  "Burst"           three short in-game BLOCK arrows (the arrowGlossy outline) fanning out of one point like
                              an exit burst, teal / sunflower / cream, on a warm burnt-tangerine ground

Everything is authored in ICON coordinates: the icon square is S = 2.5 world units, centred on the origin, +Y up,
+Z toward the viewer; outlines are drawn already in screen orientation (roll 0), so the painted light (upper left) and
shade (lower right) follow the screen. Render: `ui3d.render_case` (build/p/ICON2/render_icons.py drives it with OUT
pointed at build/p/ICON2/, never art/ui/out or Assets.xcassets).

PICKED: option B "Loop" is the app icon -- the OWNER's choice 2026-09-28 11:07 ("pick the icon B-loop its better",
build/p/ICON2/PICK), superseding ruling 47's A. R5B ICON finishing (2026-09-28, evidence build/p/R5B/):
  * iconOptB is posed with the in-game arrows' view tilt (arrowGlossy*: pitch -28; here VIEW_B = -27) so the thick
    glossy lower walls read like our toy arrows; the outlines are pre-stretched in y by B_STRETCH = cos 16 / cos 27 so
    the PROJECTED loop keeps the owner-sheet proportions, and the ramp shear follows the new tilt (VIEWS).
  * the over/under reads at 60 / 40 pt (at the owner sheet's size it read as the flat 'repeat' glyph): each tail starts a
    stub beyond the loop corner, so the under-strand comes out on BOTH sides of the head that crosses it; a steeper
    ramp (0.55) lifts each head higher over the other's tail; B_LIGHT lets the frontal fill cast a shadow too (a tight
    contact shadow where a head overlies a tail) and the ground shadow is deeper / more lifted (GROUNDS["B"]).
    Same composition and colours (B_GEOM vs B_SHEET = the owner-sheet parameters); the ground is WHITE since the owner's
    2026-09-28 13:15 call (GROUNDS["B"], ruling 50; the owner sheet showed a berry ground).
  * iconOptBDark / iconOptBTinted = the iOS 18+/26 home-screen variants from the SAME models and camera: dark = the
    arrows + their soft shadow on a transparent ground (the system paints its dark ground), tinted = an opaque
    grayscale on black (the system applies the tint) with a red-leaning grey mix (TINT_B_WEIGHTS) so tangerine and cyan
    stay apart. Manifest: appIcon / appIconDark / appIconTinted -> App/Resources/Assets.xcassets/AppIcon.appiconset.
  Option A (finished by R5 before the owner's pick; iconOptA / ADark / ATinted) is kept as a record, no longer shipped.
  Options C/D are unchanged (VIEW, grounds and layouts as the owner sheet showed them).
"""
import importlib.util
import math
import os

import numpy as np

from uikit import F, SDF2, Part, box, ellipsoid, gloss, polygon2, rect2, satin, union
from sdf import fillet_points

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("icon_v2_hud_arrows", os.path.join(_HERE, "3d-hud_arrows.py"))
HUD = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(HUD)

arrow_part = HUD.arrow_part          # the in-game glossy arrow: extrude + painted bevel/walls, gloss material
ARROW_LIGHT = HUD.ARROW_LIGHT        # the in-game arrow light rig (arrowGlossy*)

VOXEL = 0.004
S = 2.5                              # the icon square (world units)

# face, shade (walls / lower bevel), rim (deep lower wall), highlight (upper-left bevel)
SH = dict(HUD.SHADES)                # yellow orange green cyan purple red blue = the in-game arrowGlossy sets
SH.update({
    "tangerine": ("#FF9A12", "#F06A06", "#C24A04", "#FFC266"),      # D1 CTA / board exit colour
    "teal": ("#19B8A8", "#0C8C84", "#06605E", "#86EEDF"),           # D1 chrome #17B3A3 family
    "sunflower": ("#FFC526", "#F79A0C", "#D9730C", "#FFE27A"),      # D1 OUT! sunflower
    "cream": ("#FFF5DE", "#F1CF9C", "#D6A472", "#FFFFFF"),          # D1 panel cream
})

# thickness / bevel like the in-game block arrow (head width 1: half-depth 0.15, bevel 0.085, band 0.11)
HALF, BEVEL, BAND = 0.15, 0.085, 0.11


# ------------------------------------------------------------------ 2D outlines

def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _fillet_open(pts, R, n_arc=14):
    """An OPEN polyline with every interior corner replaced by a circular arc of centreline radius R."""
    P = [np.asarray(p, float) for p in pts]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, p, b = P[i - 1], P[i], P[i + 1]
        u, w = _unit(a - p), _unit(b - p)
        th = math.acos(float(np.clip(u @ w, -1, 1)))
        if R <= 0 or th > math.pi - 1e-3:
            out.append(p)
            continue
        t = min(R / math.tan(th / 2), 0.49 * np.linalg.norm(a - p), 0.49 * np.linalg.norm(b - p))
        rr = t * math.tan(th / 2)
        c = p + _unit(u + w) * rr / math.sin(th / 2)
        t1, t2 = p + u * t, p + w * t
        a1 = math.atan2(*(t1 - c)[::-1])
        a2 = math.atan2(*(t2 - c)[::-1])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n_arc + 1):
            ang = a1 + da * k / n_arc
            out.append(c + rr * np.array([math.cos(ang), math.sin(ang)]))
    out.append(P[-1])
    return np.array(out)


def stroke2(pts, w):
    """Distance to an open polyline minus w/2: round caps, round outer joins (the board arrow's lineCap/lineJoin)."""
    P = np.asarray(pts, F)
    A, B = P[:-1], P[1:]
    AB = B - A
    L2 = np.maximum((AB * AB).sum(1), 1e-12)

    def fn(p):
        d = np.full(len(p), 1e9, F)
        for a, ab, l2 in zip(A, AB, L2):
            ap = p - a
            t = np.clip((ap @ ab) / l2, 0, 1)
            q = ap - t[:, None] * ab
            d = np.minimum(d, np.sqrt((q * q).sum(1)))
        return d - F(w / 2)
    return SDF2(fn, P.min(0) - w / 2, P.max(0) + w / 2)


def _smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def union2(shapes, k=0.0):
    fns = [s.fn for s in shapes]

    def fn(p):
        d = fns[0](p)
        for f in fns[1:]:
            d = _smin(d, f(p), k)
        return d
    lo = np.min([s.lo for s in shapes], 0) - k
    hi = np.max([s.hi for s in shapes], 0) + k
    return SDF2(fn, lo, hi)


def head2(base, direction, hb, hl, r_tip=0.07, r_back=0.07):
    """The rounded isosceles triangle head: base centre `base`, pointing along `direction`, base width hb, length hl."""
    d = _unit(direction)
    nrm = np.array([-d[1], d[0]])
    base = np.asarray(base, float)
    tip = base + d * hl
    pts = [tip, base + nrm * hb / 2, base - nrm * hb / 2]
    return polygon2(fillet_points(pts, [r_tip, r_back, r_back], n_arc=12))


def path_arrow2(pts, w, hb, hl, R=None, k=0.035):
    """Our path arrow: the polyline `pts` (tail cap centre ... head base centre) stroked w wide with round caps and
    round outer joins (centreline fillet R, default 0.55 w: outer radius ~1.05 w, inner ~0.05 w), and a rounded
    triangle head (base hb, length hl) on the last point along the last segment. k = a small fillet at the
    head/shaft junction."""
    R = 0.55 * w if R is None else R
    P = [np.asarray(p, float) for p in pts]
    d = _unit(P[-1] - P[-2])
    line = _fillet_open(P[:-1] + [P[-1] + d * 0.22 * hl], R)
    return union2([stroke2(line, w), head2(P[-1], d, hb, hl)], k=k)


def block2(tip, direction, s=1.0, hl=0.58, t=0.27, shaft=0.54):
    """The in-game BLOCK arrow outline (3d-hud_arrows.block2d: head width 1, head length 0.58, shaft 0.54 x 0.54),
    scaled by s, tip at `tip`, pointing along `direction`."""
    pts = np.array([(0.0, 0.0), (-hl, 0.5), (-hl, t), (-hl - shaft, t), (-hl - shaft, -t), (-hl, -t), (-hl, -0.5)])
    radii = np.array([0.16, 0.14, 0.05, 0.13, 0.13, 0.05, 0.14])
    loop = fillet_points(pts, radii, n_arc=10) * s
    a = math.atan2(direction[1], direction[0])
    Rm = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    return polygon2(loop @ Rm.T + np.asarray(tip, float))


# ------------------------------------------------------------------ the four layouts (2D, icon coordinates)
# Each layout: {model name: (outline SDF2, shade key, ramp)}; ramp = None or ((dx, dy), slope): the arrow's height rises
# along that screen direction (z += slope * (x dx + y dy)), which lets two flat arrows pass over each other (option B).

def stretch_y2(s2, k):
    """The outline stretched by k (> 1) along y about y = 0. f(x, y / k) keeps |grad| <= 1 (a valid bound for meshing)
    and its gradient (fx, fy / k) is the stretched outline's true normal, so the painted bevel side (`u`) stays right."""
    f = s2.fn
    kk = F(k)
    return SDF2(lambda p: f(np.stack([p[:, 0], p[:, 1] / kk], 1)), [s2.lo[0], s2.lo[1] * k], [s2.hi[0], s2.hi[1] * k])


# R5 finishing (ruling 47): the picked option A takes the in-game arrow's view tilt (arrowGlossy*: pitch -28); its outline
# is pre-stretched so the projected silhouette keeps the -16 proportions of the picked render (y' ~ y cos(pitch))
VIEW_A = (0, -27)
A_STRETCH = math.cos(math.radians(16)) / math.cos(math.radians(27))


def layout_A():
    """One fat tangerine path arrow: up from a round-capped tail at the lower left, round a tight (board-like) bend,
    out to the right edge."""
    w = 0.54
    s2 = path_arrow2([(-0.70, -0.72), (-0.70, 0.34), (0.12, 0.34)], w=w, hb=1.16, hl=0.84, R=0.16 * w)
    return {"arrowA": (stretch_y2(s2, A_STRETCH), "tangerine", None)}


# R5B finishing (the OWNER's pick, 2026-09-28 11:07 "pick the icon B-loop its better"; build/p/ICON2/PICK): option B takes
# the in-game arrows' view tilt (arrowGlossy*: pitch -28; VIEW_B = -27) with the outline pre-stretched by cos16/cos27
# (the projected loop keeps the owner-sheet proportions), and the over/under is made legible at 60/40 pt: each TAIL now
# starts a stub (0.42) BEYOND the loop corner, so the under-strand visibly comes out on the far side of the head that
# crosses it (a woven crossing, not a head butting a tail = the flat 'repeat' glyph; shorter stubs of 0.24 / 0.36 still
# read as bumps at 40 pt, build/p/R5B/look-B*.png); a steeper height ramp (0.45 -> 0.55) lifts each head higher over the
# other's tail, which throws a real cast shadow on it. The loop is a little smaller (s 0.62 -> 0.55, heads 0.88 x 0.62
# -> 0.80 x 0.56) to make room for the stubs; `lift` = a vertical re-centring knob (0: the art's box sits 71 px from the
# top and the bottom of the 1024 px icon). B_SHEET = the owner-sheet render's parameters.
VIEW_B = (0, -27)
B_STRETCH = math.cos(math.radians(16)) / math.cos(math.radians(27))
B_SHEET = dict(s=0.62, w=0.40, hb=0.88, hl=0.62, hbo=0.22, stub=0.0, ramp=0.45, lift=0.0, stretch=1.0)
B_GEOM = dict(s=0.55, w=0.40, hb=0.80, hl=0.56, hbo=0.20, stub=0.42, ramp=0.55, lift=0.0, stretch=B_STRETCH)
B_RAMP = B_GEOM["ramp"]


def layout_B(g=None):
    """Two bent path arrows interlocked round a square loop: tangerine up the left side and along the top, cyan down
    the right side and along the bottom. Each HEAD passes over the other's TAIL: tangerine rises toward +x, cyan toward
    -x (a height ramp along x), so the loop links in depth instead of chasing round a flat ring; each tail starts
    `stub` beyond the loop corner so it shows on BOTH sides of the head that crosses it (hbo = the head's base sits
    that far before the crossed strand's centreline)."""
    g = g or B_GEOM
    s, w, hb, hl, hbo, e, up = g["s"], g["w"], g["hb"], g["hl"], g["hbo"], g["stub"], g["lift"]
    R = 0.16 * w
    a = path_arrow2([(-s, -s - e + up), (-s, s + up), (s - hbo, s + up)], w=w, hb=hb, hl=hl, R=R)
    b = path_arrow2([(s, s + e + up), (s, -s + up), (-(s - hbo), -s + up)], w=w, hb=hb, hl=hl, R=R)
    if g["stretch"] != 1.0:
        a, b = stretch_y2(a, g["stretch"]), stretch_y2(b, g["stretch"])
    k = g["ramp"]
    return {"arrowB1": (a, "tangerine", ((1.0, 0.0), k)), "arrowB2": (b, "cyan", ((-1.0, 0.0), k))}


C_TILE = dict(center=(-0.40, -0.40), half=0.58, round=0.16, angle=-10.0, pitch=0.25, n=4, dot=0.05)
C_ARROW = dict(tail=(0.16, 0.14), dir=(1.0, 0.86), run=0.94, w=0.44, hb=1.0, hl=0.72)


def layout_C():
    """One big diagonal sunflower arrow lifting off a small cream board tile (tile + dots are their own model): its
    round tail sits on the tile's upper-right lattice, so most of the board's dots stay in view."""
    cx, cy = C_TILE["center"]
    a = C_ARROW
    d = _unit(a["dir"])
    tail = np.array([cx + a["tail"][0], cy + a["tail"][1]])
    base = tail + d * a["run"]
    return {"arrowC": (path_arrow2([tail, base], w=a["w"], hb=a["hb"], hl=a["hl"]), "sunflower", None)}


D_FAN = dict(origin=(0.0, -0.72), angles=(152.0, 90.0, 28.0), reach=(1.20, 1.56, 1.20), shaft=(0.54, 0.68, 0.54),
             s=0.90)


def layout_D():
    """Three short in-game block arrows fanning out of one point low in the icon, like an exit burst (left-up, up,
    right-up); the middle one has a longer shaft so all three tails start at the fan point."""
    out = {}
    o = np.array(D_FAN["origin"])
    for i, (ang, reach, sh, col) in enumerate(zip(D_FAN["angles"], D_FAN["reach"], D_FAN["shaft"],
                                                  ("teal", "sunflower", "cream"))):
        d = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
        out[f"arrowD{i + 1}"] = (block2(o + d * reach, d, s=D_FAN["s"], shaft=sh), col, None)
    return out


LAYOUTS = {"A": layout_A, "B": layout_B, "C": layout_C, "D": layout_D}


def ramp_z(ramp, xy):
    """The height offset of a ramped arrow at screen points xy (N,2); 0 without a ramp."""
    if ramp is None:
        return np.zeros(len(xy))
    (dx, dy), k = ramp
    return k * (xy[:, 0] * dx + xy[:, 1] * dy)


# ------------------------------------------------------------------ grounds (painted in post_fit, opaque RGB)

GROUNDS = {  # centre colour, edge colour, radial centre (x, y in 0..1, y down), shadow tint (multiplied), shadow strength
    # deep grounds on purpose: the copy gate's SSIM is ~ (luminance term) x (structure term), and a light flat ground
    # scores like their white one (mock v1: cream 0.40, mid teal 0.30); the D1 page teal / moss / timber / boss-pink
    # families at low value keep the arrows the brightest thing in the icon
    "A": dict(c0="#1F8F88", c1="#083638", at=(0.42, 0.42), shadow="#021E20", k=0.60),
    # B = the OWNER's white ground (2026-09-28 13:15: "the background color of it should be white just like mazeout has ...
    # the purplish background is bad"; SPEC ruling 50): white with an all-but-invisible cool edge (#FAFBFD) and a soft
    # slate contact shadow; the berry ground it replaced was c0 #A3306F, c1 #480C32, shadow #240418, k 0.68
    "B": dict(c0="#FFFFFF", c1="#FAFBFD", at=(0.50, 0.45), shadow="#6B7488", k=0.40, blur=0.020, off=(0.013, 0.032)),
    "C": dict(c0="#2F9656", c1="#0B4022", at=(0.62, 0.34), shadow="#032010", k=0.60),
    "D": dict(c0="#A84A1A", c1="#3C1004", at=(0.50, 0.40), shadow="#2A0A02", k=0.60),
}


def _hex(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def paint_ground(key, W, H):
    g = GROUNDS[key]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx + 0.5) / W - g["at"][0]) ** 2 + ((yy + 0.5) / H - g["at"][1]) ** 2) / 0.78
    t = np.clip(r, 0, 1) ** 1.6
    return _hex(g["c0"]) * (1 - t[..., None]) + _hex(g["c1"]) * t[..., None]


def ground_post(key):
    """post_fit: the painted ground + a soft contact shadow (the ground's own deep tint, down-right) under the art."""
    def post(im):
        from PIL import Image, ImageFilter
        W, H = im.size
        g = GROUNDS[key]
        base = paint_ground(key, W, H)
        a = np.asarray(im.getchannel("A")).astype(np.float32) / 255
        sh = _contact_shadow(a, W, H, key)
        tint = _hex(g["shadow"])      # a multiply toward the ground's own deep tint (never a grey smudge)
        base = base * (1 - g["k"] * sh[..., None]) + (base * tint / 255.0) * (g["k"] * sh[..., None])
        out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        out.alpha_composite(im)
        return out.convert("RGB")
    return post


def _contact_shadow(a, W, H, key=None):
    """The soft contact shadow of ground_post as a 0..1 field: blur 1.6 %, offset 1.0 % / 2.4 % down-right, or the
    ground's own blur / off (B: 2.0 %, 1.3 % / 3.2 % -- the linked arrows float higher, R5B)."""
    from PIL import Image, ImageFilter
    g = GROUNDS.get(key, {})
    sh = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(W * g.get("blur", 0.016)))
    sh = np.asarray(sh).astype(np.float32) / 255
    ox, oy = g.get("off", (0.010, 0.024))
    dx, dy = int(W * ox), int(W * oy)
    return np.pad(sh, ((dy, 0), (dx, 0)))[:H, :W]


def dark_post(key, shadow_alpha=0.55):
    """post_fit for the iOS DARK icon: no ground (Apple: a transparent background, the system paints its dark one), the
    same arrow, and its contact shadow as translucent black so the arrow still sits on something. RGBA out."""
    def post(im):
        from PIL import Image
        W, H = im.size
        a = np.asarray(im.getchannel("A")).astype(np.float32) / 255
        sh = _contact_shadow(a, W, H, key) * shadow_alpha
        base = np.zeros((H, W, 4), np.uint8)
        base[..., 3] = np.clip(sh * 255, 0, 255).astype(np.uint8)
        out = Image.fromarray(base, "RGBA")
        out.alpha_composite(im)
        return out
    return post


def tinted_post(key, black=0.28, gamma=0.9, white=0.98, weights=(0.2126, 0.7152, 0.0722)):
    """post_fit for the iOS TINTED icon: Apple asks for an opaque grayscale image on black; the system maps its luminance
    to the user's tint. The arrow's own luminance (Rec. 709 on the sRGB values) is levelled: its 98th percentile (the
    bevel highlight) -> near white, and a black point pulls the side walls well below the face (R5 look: without it
    the walls sat at 140 against a 208 face and the tinted arrow read flat); then laid on black. RGB out.
    `weights` = the grey mix of R, G, B (default Rec. 709). Option B passes TINT_B_WEIGHTS: tangerine (L709 ~168) and
    cyan (~150) have nearly the same luminance, so a plain luminance map fuses the two linked arrows into one grey
    ring; a red-leaning mix keeps tangerine bright and cyan mid-grey, so the crossings still read when tinted."""
    def post(im):
        from PIL import Image
        arr = np.asarray(im.convert("RGBA")).astype(np.float32) / 255
        a = arr[..., 3]
        L = arr[..., 0] * weights[0] + arr[..., 1] * weights[1] + arr[..., 2] * weights[2]
        solid = a > 0.9
        hi = float(np.percentile(L[solid], 98.0)) if solid.any() else 1.0
        g = np.clip((L / max(hi, 1e-3) - black) / (1 - black), 0, 1) ** gamma * white
        v = np.clip(g * a * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(np.stack([v, v, v], -1), "RGB")
    return post


# ------------------------------------------------------------------ 3D models

def _calm_uv(part, s2):
    """arrow_part's per-vertex u (which way the outline faces) flips across the shape's medial axis INSIDE the flat
    face, where the paint does not use it; the triangles spanning that flip cover the whole texture, the renderer picks
    a coarse mip there and faint bevel-coloured lines + stair-steps show on the face (seen on option D at 1024 px).
    Hold u at 0.5 deeper than 1.6 bands inside the outline; the bevel band itself (d > -BAND) keeps its u."""
    from dataclasses import replace
    uvf = part.uv[1]

    def uv(v):
        out = np.array(uvf(v), float, copy=True)
        d = s2.fn(np.asarray(v)[:, :2].astype(F)).astype(float)
        w = np.clip((d + 1.6 * BAND) / (0.6 * BAND), 0, 1)
        out[:, 0] = 0.5 + (out[:, 0] - 0.5) * w
        return out
    return replace(part, uv=("fn", uv))


def _arrow_model(key, name):
    s2, col, ramp = LAYOUTS[key]()[name]
    part = _calm_uv(arrow_part(name, s2, HALF, BEVEL, SH[col], band=BAND, roll=0.0), s2)
    if ramp is None:
        return [part], VOXEL
    # ramp: shear the SDF in z along the screen direction; the painted zones are looked up on the un-sheared point
    from dataclasses import replace
    from uikit import SDF
    (dx, dy), k = ramp
    assert dy == 0, "ramps run along x only (the view-tilt compensation below assumes it)"
    # the scene's view tilt maps y' = cos(p) (y + tan|p| z): a height that grows with x would slant every bar on
    # screen, so the outline is pre-sheared by -tan|p| k dx x and the PROJECTED loop stays square
    t = math.tan(math.radians(-VIEWS.get(key, VIEW)[1]))
    f2 = s2.fn
    a = F(t * k * dx)
    xm = float(max(abs(s2.lo[0]), abs(s2.hi[0])))
    s2 = SDF2(lambda p: f2(np.stack([p[:, 0], p[:, 1] + a * p[:, 0]], 1)),
              [s2.lo[0], s2.lo[1] - abs(float(a)) * xm], [s2.hi[0], s2.hi[1] + abs(float(a)) * xm])
    part = _calm_uv(arrow_part(name, s2, HALF, BEVEL, SH[col], band=BAND, roll=0.0), s2)
    f, uvf = part.sdf.fn, part.uv[1]
    lip = math.sqrt(1 + k * k)

    def fn(p):
        q = p.copy()
        q[:, 2] = p[:, 2] - F(k) * (p[:, 0] * F(dx) + p[:, 1] * F(dy))
        return f(q) / F(lip)

    def uv(v):
        q = np.array(v, float, copy=True)
        q[:, 2] = v[:, 2] - k * (v[:, 0] * dx + v[:, 1] * dy)
        return uvf(q)
    lo, hi = part.sdf.lo.copy(), part.sdf.hi.copy()
    corners = np.array([[x, y] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])])
    zs = ramp_z(ramp, corners)
    lo[2] += zs.min(); hi[2] += zs.max()
    return [replace(part, sdf=SDF(fn, lo, hi), uv=("fn", uv))], VOXEL


def _tile_xy(i, j):
    cx, cy = C_TILE["center"]
    a = math.radians(C_TILE["angle"])
    x, y = i * C_TILE["pitch"], j * C_TILE["pitch"]
    return cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)


def tile_dots():
    """The lattice points left visible: dots under (or within 0.06 of) the arrow's outline are dropped, so none sits
    half-hidden at its edge."""
    n = C_TILE["n"]
    k = [i - (n - 1) / 2 for i in range(n)]
    pts = [_tile_xy(i, j) for i in k for j in k]
    arrow = layout_C()["arrowC"][0]
    d = arrow.fn(np.asarray(pts, np.float32))
    return [p for p, dd in zip(pts, d) if dd > C_TILE["dot"] + 0.06]


def tile2():
    """The board tile's outline (2D, for the mocks / clearance checks)."""
    cx, cy = C_TILE["center"]
    return rect2(C_TILE["half"], C_TILE["half"], round=C_TILE["round"]).rotate(C_TILE["angle"]).translate(cx, cy)


def tile_model():
    """Option C's board: a cream tile (satin) with a 4 x 4 lattice of small teal dot domes (the board's lattice
    points; 3 x 3 big pips read as a die), turned a little so it reads as a game piece, not a UI 'open in' box."""
    cx, cy = C_TILE["center"]
    h = C_TILE["half"]
    tile = box(h, h, 0.07, round=0.06).rotate_z(C_TILE["angle"]).translate(cx, cy, -0.12)
    parts = [Part("tile", tile, satin("icon_tile", "#FCEBC8", rough=0.42), voxel=0.006)]
    r = C_TILE["dot"]
    dots = [ellipsoid(r, r, 0.03, center=(x, y, -0.05)) for x, y in tile_dots()]
    parts.append(Part("dots", union(*dots), gloss("icon_dots", "#1F6B66", rough=0.35), voxel=0.004))
    return parts, VOXEL


MODELS = {}
for _k, _fn in LAYOUTS.items():
    for _name in _fn():
        MODELS[_name] = (lambda k=_k, n=_name: _arrow_model(k, n))
MODELS["tileC"] = tile_model

VIEW = (0, -16)                      # the whole scene tilts a little so the arrows' lower walls show (in-game look)
VIEWS = {"A": VIEW_A, "B": VIEW_B}    # the finished options take the in-game arrowGlossy tilt (the ramp shear follows it)
BOUNDS = ((-S / 2, -S / 2, -0.35), (S / 2, S / 2, 0.35))


# B's rig = the in-game ARROW_LIGHT with its frontal fill casting a shadow too (R5B): lit almost along the view, a head
# that passes over the other arrow's tail throws a TIGHT dark contact line on it just below-right of its edge (the
# key's shadow lands far off to the lower right), which is what keeps the over/under readable at 60/40 pt
B_LIGHT = dict(ARROW_LIGHT, extra=[dict(type="directional", direction=[0.15, -0.32, -1.0], intensity=600.0,
                                        color=[1.0, 1.0, 1.0], shadow=True, shadowFixed=2.1, shadowBias=0.6)])
LIGHTS = {"B": B_LIGHT}
TINT_B_WEIGHTS = (0.45, 0.50, 0.05)  # tinted B: tangerine face ~195 vs cyan face ~122 before levelling (see tinted_post)


def _case(key, entries, view=VIEW, post=None):
    return dict(scene=entries, view=view, frame=(1024 / 3, 1024 / 3), fov=10, light=LIGHTS.get(key, ARROW_LIGHT), bounds=BOUNDS,
                no_fit=True, margin=1.0, post_fit=post or ground_post(key), ss=2)


def _flat(names, z=0.0):
    return [(n, dict(pos=(0.0, 0.0, z), center=False)) for n in names]


# the cases are spelled out (manifest_check greps recipes for case names). The OWNER's pick (2026-09-28 11:07, superseding
# ruling 47's A) = option B: iconOptB = the app icon (manifest appIcon), iconOptBDark / iconOptBTinted = its iOS dark /
# tinted variants (appIconDark / appIconTinted). iconOptA* = R5's finished A, kept as a record (not shipped).
ASSETS = {
    "iconOptA": _case("A", _flat(["arrowA"]), view=VIEW_A),
    "iconOptADark": _case("A", _flat(["arrowA"]), view=VIEW_A, post=dark_post("A")),
    "iconOptATinted": _case("A", _flat(["arrowA"]), view=VIEW_A, post=tinted_post("A")),
    "iconOptB": _case("B", _flat(["arrowB1", "arrowB2"]), view=VIEW_B),
    "iconOptBDark": _case("B", _flat(["arrowB1", "arrowB2"]), view=VIEW_B, post=dark_post("B")),
    "iconOptBTinted": _case("B", _flat(["arrowB1", "arrowB2"]), view=VIEW_B, post=tinted_post("B", weights=TINT_B_WEIGHTS)),
    "iconOptC": _case("C", [("tileC", dict(pos=(0.0, 0.0, 0.0), center=False))] + _flat(["arrowC"], z=0.14)),
    "iconOptD": _case("D", _flat(["arrowD1", "arrowD2", "arrowD3"])),
}
