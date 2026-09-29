"""3d-hud lane: the chunky glossy 3D arrows (STYLE.md route C2) of the capsule machine / loading screen, and the app icon.

References (LOOKED at only, nothing traced or sampled into a texture): the capsule-machine pile on 026 (box 112,410 ->
282,520 pt) and the loading art (store 8) for the block arrows; research/store/icon-1024.png for the icon STYLE (glossy
long-shaft arrows, painted hue-shifted bevel, white ground) -- the icon composition here is our own (three arrows
entering from three edges: blue <- at the top, yellow ^ at the right, red -> at the bottom), not the original's
three horizontal lanes (yellow ->, red <-, blue ->).

Block arrow (pile / loading), measured on 026 at 3x zoom, head width = 1: head length 0.58, shaft width 0.54, shaft length
0.62, thickness 0.30, tip radius ~0.13, head back corners ~0.10, a soft 0.08 bevel. Colours per family = (face, shade,
rim, highlight); pile families measured as value quantiles of each hue family on 026 (the face = the median of the
bright half, the shade = the walls); red/blue = the icon's k-means set (STYLE.md §D).
Icon arrow: head height 1, shaft 0.37, head length 0.79 (STYLE.md §C.3 / arrows3d.py spike), thickness 0.20.

Painting (per vertex, `uv=("fn", ...)`): u = which way the outline faces (0 up-left -> 1 down-right), v = the zone (0..0.5
the top face from its middle to the bevel, 0.5..1 the wall from the bevel down to the back). The texture paints the
hue-shifted bevel/wall; the rig only adds form and the speculars.
"""
import math

import numpy as np

from uikit import F, Part, extrude, polygon2
from sdf import fillet_points
from mesher import Material

VOXEL = 0.004

SHADES = {  # face, shade (walls / lower bevel), rim (deep lower wall), highlight (upper-left bevel)
    "yellow": ("#FEC307", "#FB9A08", "#E8700C", "#FFDB52"),
    "orange": ("#FD8A0C", "#F06A06", "#CC4E08", "#FFB456"),
    "green": ("#86E532", "#4DBA12", "#349A06", "#BAF472"),
    "cyan": ("#3EC6F9", "#1C9ADA", "#0A74BC", "#94E0FD"),
    "purple": ("#D06EEA", "#AE42D4", "#8A2EB0", "#EAB0F8"),
    "red": ("#FA3633", "#D4090B", "#A80508", "#FC6E68"),
    "blue": ("#0292FE", "#005FF1", "#0647CC", "#4ABBFD"),
}
ICON_SHADES = {  # the icon arrows (research/store/icon-1024.png k-means, STYLE.md §D): lower side orange for yellow
    "yellow": ("#FEBF0E", "#FB8A03", "#E46011", "#FED23B"),
    "red": ("#FA3633", "#D4090B", "#A80508", "#FC635F"),
    "blue": ("#0292FE", "#005FF1", "#0647CC", "#42B7FC"),
}


def block2d(hl=0.58, t=0.27, shaft=0.54):
    """The pile arrow outline, tip at the origin pointing +X, head width 1."""
    pts = [(0.0, 0.0), (-hl, 0.5), (-hl, t), (-hl - shaft, t), (-hl - shaft, -t), (-hl, -t), (-hl, -0.5)]
    radii = [0.16, 0.14, 0.05, 0.13, 0.13, 0.05, 0.14]
    return polygon2(fillet_points(pts, radii, n_arc=10))


def icon2d(shaft=2.6, t=0.185, hl=0.79):
    """The icon arrow outline (long shaft), tip at the origin pointing +X, head height 1."""
    pts = [(0.0, 0.0), (-hl, 0.5), (-hl, t), (-hl - shaft, t), (-hl - shaft, -t), (-hl, -t), (-hl, -0.5)]
    radii = [0.085, 0.085, 0.035, 0.05, 0.05, 0.035, 0.085]
    return polygon2(fillet_points(pts, radii, n_arc=10))


def paint_texture(shades, hi_amt=0.55):
    from palette import _rgb
    face, shade, rim, hi = (np.asarray(_rgb(c), float) for c in shades)

    def fn(u, v):
        u3, v3 = u[..., None], v[..., None]
        hi_soft = face + (hi - face) * hi_amt
        edge = hi_soft + (shade - hi_soft) * np.clip(u3 * 1.25 - 0.1, 0, 1)   # up-left light -> down-right shade
        tb = np.clip(v3 / 0.5, 0, 1)
        tb = tb * tb * (3 - 2 * tb)
        top = face * (1 - tb) + edge * tb
        wall_base = hi * 0.25 + shade * 0.75
        wall = wall_base + (shade - wall_base) * np.clip(u3 * 1.4 - 0.2, 0, 1)
        tw = np.clip((v3 - 0.5) / 0.5, 0, 1)
        wall = wall * (1 - tw * 0.8) + rim * (tw * 0.8)
        return np.where(v3 < 0.5, top, wall)
    return fn


def arrow_part(name, s2, half, bevel, shades, band, roll=0.0, hi_amt=0.55):
    """Extrude the outline, paint it (see the module docstring). `roll` = the in-plane rotation the arrow will be
    posed with (deg, CCW), so the painted light/shade follow the SCREEN's lower right, not the model's."""
    from dataclasses import replace
    body = extrude(s2, half, round=bevel)
    down = np.array([0.30, -1.0]); down /= np.linalg.norm(down)
    a = math.radians(-roll)
    down = np.array([math.cos(a) * down[0] - math.sin(a) * down[1], math.sin(a) * down[0] + math.cos(a) * down[1]])
    zt = half - bevel

    def uvf(v):
        p = v[:, :2].astype(F)
        d = s2.fn(p).astype(np.float64)
        e = 1e-3
        gx = (s2.fn(p + np.array([e, 0], F)) - s2.fn(p - np.array([e, 0], F))) / (2 * e)
        gy = (s2.fn(p + np.array([0, e], F)) - s2.fn(p - np.array([0, e], F))) / (2 * e)
        g = np.stack([gx, gy], 1).astype(np.float64)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-6)
        u = np.clip((g @ down + 1) / 2, 0, 1)
        z = v[:, 2]
        on_top = z > zt
        vt = 0.5 * np.clip((d + band) / band, 0, 1) * 0.98
        vw = 0.5 + 0.5 * np.clip((zt - z) / (2 * half), 0, 1)
        vv = np.where(on_top, vt, np.maximum(vw, 0.5))
        return np.stack([u, vv], 1)
    m = Material(name, shades[0], roughness=0.28, ior=1.42)
    m = replace(m, texture=paint_texture(shades, hi_amt), texture_size=256)
    return Part(name, body, m, uv=("fn", uvf), min_tris=10 ** 9)   # no decimation: the painted band stays clean


def block_arrow(color):
    return [arrow_part(f"block_{color}", block2d(), 0.15, 0.085, SHADES[color], band=0.11)], VOXEL


def icon_arrow(color, roll):
    return [arrow_part(f"icon_{color}", icon2d(), 0.10, 0.055, ICON_SHADES[color], band=0.075, roll=roll, hi_amt=0.08)], VOXEL


# R4 LOADING (PLAN-P §4.2; ruling 46): the seven arrowGlossy* ids recoloured to D1 enamel -- same ids, shape, frame, light
# and painting; only the (face, shade, rim, highlight) quadruples move onto the D1 ladder (3d-home_d1.py families; purple ->
# the berry ladder of design/publish/palette R9, blue -> the chrome teal). The v552-measured SHADES above stay for reference.
D1_SHADES = {
    "yellow": ("#FFCB2F", "#EDA80E", "#B77C04", "#FFE88A"),     # sunflower
    "orange": ("#FF9A12", "#E27608", "#A84E00", "#FFC46A"),     # tangerine
    "red": ("#F2553F", "#D23A26", "#9A2414", "#FF9C86"),        # coral
    "green": ("#6CCB8F", "#3F9E68", "#256F48", "#B4EDC8"),      # mint (the OUT! sign family)
    "cyan": ("#5CDCCF", "#2DBFB1", "#138F84", "#B0F4EC"),       # aqua
    "purple": ("#E8488A", "#B22470", "#7A1448", "#FFB3CF"),     # berry
    "blue": ("#139A90", "#0B7A72", "#05504C", "#46C2B6"),       # deep teal
}


def block_arrow_d1(color):
    return [arrow_part(f"block_d1_{color}", block2d(), 0.15, 0.085, D1_SHADES[color], band=0.11)], VOXEL


ICON_ROLLS = {"blue": 180, "yellow": 90, "red": 0}
MODELS = {f"block_{c}": (lambda c=c: block_arrow(c)) for c in SHADES}
MODELS.update({f"block_d1_{c}": (lambda c=c: block_arrow_d1(c)) for c in D1_SHADES})
MODELS.update({f"icon_{c}": (lambda c=c: icon_arrow(c, ICON_ROLLS[c])) for c in ICON_SHADES})

# bright, even toy light (the pile/icon look): a strong neutral fill from below keeps the painted walls saturated
ARROW_LIGHT = dict(key_lux=2000.0, key_dir=(0.45, -0.60, -0.66), fill_lux=950.0, fill_color=(1.0, 0.97, 0.94),
                   fill_dir=(0.1, 0.8, -0.6), rim_lux=1000.0, ibl_exp=-0.82,
                   extra=[dict(type="directional", direction=[0.05, -0.1, -1.0], intensity=600.0, color=[1.0, 1.0, 1.0], shadow=False)])


# the icon: a stronger frontal fill so the flat faces stay the brightest part (as on the store icon), key a little lower
ICON_LIGHT = dict(ARROW_LIGHT, key_lux=1700.0,
                  extra=[dict(type="directional", direction=[0.05, -0.1, -1.0], intensity=1150.0, color=[1.0, 1.0, 1.0], shadow=False)])

# ------------------------------------------------------------------ the app icon (ours): three arrows entering from three edges

S_ICON = 2.5            # the icon square in world units; icon arrow head height 1 = 0.40 of the icon


def _icon_pos(xn, yn):
    """Normalised icon coords (x right, y DOWN, 0..1) -> world."""
    return ((xn - 0.5) * S_ICON, (0.5 - yn) * S_ICON, 0.0)


def _icon_post(im):
    """Our icon ground: white with a soft cool-grey vignette, a soft grey contact shadow under each arrow; opaque RGB."""
    from PIL import Image, ImageFilter
    W, H = im.size
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx + 0.5) / W - 0.5) ** 2 + ((yy + 0.5) / H - 0.46) ** 2) / 0.70
    ground = np.clip(1 - 0.045 * np.clip(r, 0, 1.2) ** 2.4, 0, 1)
    g = np.stack([ground * 255, ground * 255 * 0.995 + 0.0, ground * 255 * 0.985 + 3.0], -1)
    a = np.asarray(im.getchannel("A")).astype(np.float32) / 255
    sh = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(W * 0.012))
    sh = np.asarray(sh).astype(np.float32) / 255
    dy = int(W * 0.018)
    sh = np.concatenate([np.zeros((dy, W), np.float32), sh[:-dy]], 0)
    base = g * (1 - 0.22 * sh[..., None]) + np.array([60, 70, 95]) * 0.0
    base = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    base.alpha_composite(im)
    return base.convert("RGB")


ICON_SCENE = [
    ("icon_blue", dict(pos=_icon_pos(0.255, 0.240), roll=ICON_ROLLS["blue"], center=False)),      # from the right edge, pointing left
    ("icon_yellow", dict(pos=_icon_pos(0.720, 0.485), roll=ICON_ROLLS["yellow"], center=False)),  # from the bottom edge, pointing up
    ("icon_red", dict(pos=_icon_pos(0.460, 0.720), roll=ICON_ROLLS["red"], center=False)),        # from the left edge, pointing right
]

def _block(c, d1=True):
    return dict(model=f"block_d1_{c}" if d1 else f"block_{c}", yaw=0, pitch=-28, roll=0, frame=(200, 100), fill=0.94, fov=12,
                light=ARROW_LIGHT)


# the cases are spelled out (manifest_check greps the recipe for each case name)
ASSETS = {
    "arrowGlossyYellow": _block("yellow"),
    "arrowGlossyRed": _block("red"),
    "arrowGlossyBlue": _block("blue"),
    "arrowGlossyGreen": _block("green"),
    "arrowGlossyPurple": _block("purple"),
    "arrowGlossyOrange": _block("orange"),
    "arrowGlossyCyan": _block("cyan"),
}
ASSETS["appIcon"] = dict(scene=ICON_SCENE, view=(0, -14), frame=(1024 / 3, 1024 / 3), fov=10, light=ICON_LIGHT,
                         bounds=((-S_ICON / 2, -S_ICON / 2, -0.3), (S_ICON / 2, S_ICON / 2, 0.3)), no_fit=True, margin=1.0,
                         post_fit=_icon_post, ss=2)
