"""The CORNER obstacle (v552, first on L70: "Corner! / Unlocked! / Arrows turn when they hit the CORNER!"): a red plate on a
blue coil spring, one cell, the plate facing a board diagonal. Lane "corner" (art/lanes/corner.md has every measurement).

Measured on the phone's lossless shots (457 L70, 470 L71, 498 L76, 521 L79, 526 L80, 533 L82: 21 corners at pitch 14.7-20.6
pt, all four facings) in PITCH units, in the corner's own frame: +Y = the plate's facing diagonal s (the "front"), X along
the plate, origin = the corner cell's centre. The sprite scales with the zoom (every number is constant in pitch units
across the six levels, 0.01-0.02 p scatter):
  plate  (red)    X -0.618..+0.650, Y +0.085 (front face) .. -0.289 (back); corners rounded; front bevel highlight, dark back edge
  spring (blue)   3 fat coils of a helix whose lobes slant ~13 deg (groove slope 0.22 across the axis), period 0.226 along
                  -Y, grooves at -0.43 / -0.65 / -0.88, lateral extent +-0.315 (grooves +-0.26); a darker domed base cap
                  -0.88..-1.00 (+-0.20 wide)
  shadow          a thin grey drop shadow, black 12-14 %, offset (0.015, 0.040) p in SCREEN space (down), almost no blur
The game draws the SAME sprite rotated for three facings (the (-1,-1) and (1,1) captures are the (1,-1) capture rotated by
90 deg, lighting and shadow included: RMSE 12-26 vs >= 60 for every other dihedral transform), while the (-1,1) facing is
the model turned 180 deg but lit from the screen top again (its plate highlight and shadow stay on the screen-top/down side).
So: two renders (canonical s = (1,-1) and s = (-1,1)), the other two facings are exact 90-deg pixel rotations of the
canonical render. Each facing ships as TWO registered layers (spring under, plate over) because the game animates the plate
along s (a spring bounce, art/lanes/corner.md "Hit animation") while the spring base stays put.

Frames: every board case is 64 x 64 pt = 2 x 2 pitch at the design pitch 32 pt, centred on the cell centre (anchor (32, 32);
the engine scales by pitch / 32 and may rotate nothing). The unlock-card icon is the same model at 73.4 pt per pitch (the
card's plate is 92.5 pt long vs 26.0 pt on the L70 board at pitch 20.63).

Ids: `cornerWedge` is the one sprite the board code loads today (CornerLayer.swift rotates it per turn; the level bundle's
sprite check wants it): the UpRight layers composited. The 1:1 route is the eight per-turn layers + the hit animation
(corner_anim.py); the code requests that switch the board to them are in art/lanes/corner.md.
"""
import math

import numpy as np

from uikit import Part, box, ellipsoid, gloss, satin, union  # noqa: F401
from sdf import SDF, F

VOXEL = 0.005

# colours: tuned against 457 / 498 in place (see the lane log); the render lands on the sampled tones
PLATE_RED = "#D40A04"
COIL_BLUE = "#6A809E"
CORE_NAVY = "#26337A"
BASE_BLUE = "#4C5C9E"

# measured geometry (pitch units, corner frame)
PLATE_X = (-0.620, 0.664)
PLATE_Y = (-0.270, 0.100)
PLATE_ROUND = 0.08         # the plate's corners (top view) and bevels
PLATE_HZ = 0.34            # half height: the plate stands taller than the spring (top 0.68 > coil top 0.63)
AXIS_X = -0.01             # the spring sits 0.01-0.03 p left of the plate centre (measured)
LOBE_Y = (-0.091, -0.317, -0.543, -0.769)   # lobe centres on the axis: grooves at -0.43 / -0.656 / -0.882 (457: -0.430 /
#                                             -0.651 / -0.882); the first lobe is hidden under the plate (it fills the gap
#                                             when the plate bounces out)
LOBE_A = 0.110             # lobe half-thickness along the axis (period 0.226: a thin dark groove between lobes)
LOBE_B = 0.150             # lobe tube half-width across (radial)
LOBE_R = 0.165             # ring radius: R + b = 0.315 = the lobes' lateral extent
LOBE_TILT = -12.4          # deg: the top half of a helix turn seen from above; groove slope 0.22 measured across the axis
BASE = dict(rx=0.21, ry=0.12, rz=0.20, y=-0.860)   # the domed base cap: +-0.20 at -0.90, +-0.12..0.17 at -0.95, ends -0.98
CORE_R = 0.22              # the dark inside of the coil, seen in the grooves between lobes (0.04-0.06 p wide on 457)
PLATE_CURVE = (0.90, 1.20)  # the top's curvature radius along the plate / across it ...
PLATE_BULGE_DY = 0.06      # ... its crest 0.06 p in front of the plate centre (the capture's sheen peaks toward the front)
PLATE_RIM = 0.09           # the plate top rim rounding (vertical profile): the bevel band seen from above


def lobe(yc, R=LOBE_R, a=LOBE_A, b=LOBE_B, tilt=LOBE_TILT):
    """One coil lobe: a ring around the Y axis with an elliptical tube (a along Y, b radial), tilted about Z so its top
    half slants like a helix turn's (the bottom half is hidden from the top-down camera, so a ring = a helix here)."""
    af, bf, Rf = F(a), F(b), F(R)
    m = F(min(a, b) * 0.9)

    def fn(p):
        q = np.sqrt(p[:, 0] ** 2 + p[:, 2] ** 2) - Rf
        return (np.sqrt((q / bf) ** 2 + (p[:, 1] / af) ** 2) - F(1.0)) * m
    e = R + b
    ring = SDF(fn, np.array([-e, -a, -e]), np.array([e, a, e]))
    return ring.rotate_z(tilt).translate(AXIS_X, yc, R + b)


def spring():
    return union(*[lobe(y) for y in LOBE_Y])


def core():
    from sdf import cylinder
    y0, y1 = -0.10, -0.86
    return cylinder(CORE_R, (y0 - y1) / 2, center=(AXIS_X, (y0 + y1) / 2, LOBE_R + LOBE_B))


def plate():
    """A slab standing on the board: its top-view outline is a rounded rectangle (corner r 0.08, measured) and its top rim
    is rounded wider (PLATE_RIM) so the front bevel carries the capture's highlight band ~0.04 p inside the edge."""
    from sdf import extrude, rect2
    cx = (PLATE_X[0] + PLATE_X[1]) / 2; cy = (PLATE_Y[0] + PLATE_Y[1]) / 2
    s2 = rect2((PLATE_X[1] - PLATE_X[0]) / 2, (PLATE_Y[1] - PLATE_Y[0]) / 2, round=PLATE_ROUND)
    slab = extrude(s2, PLATE_HZ, round=PLATE_RIM).translate(cx, cy, PLATE_HZ)
    # the top is a smooth paraboloid cap, curved ALONG the plate (radius PLATE_CURVE[0]) more than across it
    # (PLATE_CURVE[1]): the card render (456, 73 pt / pitch) shows the sheen as a band across the whole depth centred
    # at mid-length and both ends deep red (G 11 at u -0.56, 10 at +0.56 vs 126 at u 0); the board captures agree
    # (7 corners: G 158 at u 0 -> 91 at u -0.4, 70 at u +0.4)
    top = 2 * PLATE_HZ
    ra, rc = PLATE_CURVE
    y0 = cy + PLATE_BULGE_DY
    lo, hi = slab.lo.copy(), slab.hi.copy()

    def cap(p):
        zt = F(top) - (p[:, 0] - F(cx)) ** 2 / F(2 * ra) - (p[:, 1] - F(y0)) ** 2 / F(2 * rc)
        return (p[:, 2] - zt) * F(0.8)
    return slab.intersect(SDF(cap, lo, hi), k=0.02)


def base_cap(card=False):
    b = dict(BASE, **(CARD_BASE_GEOM if card else {}))
    return ellipsoid(b["rx"], b["ry"], b["rz"], center=(AXIS_X, b["y"], LOBE_R + LOBE_B))


REGISTER = (-0.017, -0.024)   # measured bias of the whole model vs 21 captured corners (best in-place shift, corner
#                               frame u / n, pitch; corner_proofs.py stats): applied to every part

# The unlock card (456, 73.4 pt per pitch) is the same model with a softer spring (round 3 lane, corner.md "Card"):
CARD_COIL = dict(rough=0.40, ior=1.55)    # its lobes carry a soft broad sheen, not the board's sharp glint
CARD_BASE = "#6A7CBC"                     # its domed foot reads mid-blue (456 mean #5D6F99; ours was #455583)
CARD_BASE_GEOM = dict(ry=0.13, y=-0.878)  # and reaches 0.03 p further (n -1.00 .. -1.02 on 456 vs -0.98)


def parts(which=("spring", "base", "plate"), card=False):
    ps = []
    if "spring" in which:
        cm = CARD_COIL if card else dict(rough=0.28, ior=1.80)
        ps.append(Part("coil", spring(), gloss("corner_coil" + ("_card" if card else ""), COIL_BLUE, **cm), voxel=0.004))
        ps.append(Part("core", core(), satin("corner_core", CORE_NAVY, rough=0.55), voxel=0.005))
    if "base" in which:
        ps.append(Part("base", base_cap(card), gloss("corner_base" + ("_card" if card else ""),
                                                  CARD_BASE if card else BASE_BLUE, rough=0.30, ior=1.40), voxel=0.004))
    if "plate" in which:
        ps.append(Part("plate", plate(), gloss("corner_plate", PLATE_RED, rough=0.52, ior=1.60), voxel=0.004))
    for q in ps:
        q.sdf = q.sdf.translate(REGISTER[0], REGISTER[1], 0.0)
    return ps, VOXEL


MODELS = {
    "corner": lambda: parts(),
    "cornerPlateOnly": lambda: parts(("plate",)),
    "cornerSpringOnly": lambda: parts(("spring", "base")),
    "cornerSpringOnlyCard": lambda: parts(("spring", "base"), card=True),
}

# ------------------------------------------------------------------ rendering

# Lit from the screen TOP (the canonical plate's up-left end is lighter and its back edge dark; the (-1, 1) capture keeps
# that screen-space lighting) plus a low grazing light from the upper right (the front-bevel highlight band 0.04 p inside
# the plate's edge, the lobes' sheen on their plate side). Each layer has its own light colour: the plate's sheen is warm
# (254,166,133 on 457), the coils' is cool (211,221,238) with blue shadows.
_KEY = dict(shadow=False, key_dir=(0.12, -0.72, -0.68), key_lux=2400.0, rim_lux=500.0, fill_lux=250.0, ibl_exp=-0.9)
def _fan(n=13, spread=42.0, tilt=42.0, lux=720.0, color=(1.0, 1.0, 1.0)):
    """A fan of near-frontal lights spread ALONG the corner's u axis (the plate's length = the lobes' direction), tilted
    `tilt` deg toward the plate side. One small light draws a dot on a torus or a pill; the captures show a long streak
    mid-lobe on the coils and a sheen band across the plate: a fan draws those. Directions are in camera space for the
    canonical pose (u = screen down-right, the plate toward screen up-right); the (-1, 1) render lies on the same diagonal,
    so it shares the fan (its plate side is then the other way, like the capture's)."""
    import math as _m
    w = (0.7071, -0.7071, 0.0); nrm = (0.7071, 0.7071, 0.0)
    out = []
    for i in range(n):
        t = _m.radians(-spread + 2 * spread * i / (n - 1)); tl = _m.radians(tilt)
        d = [-(_m.sin(t) * w[k] + _m.cos(t) * _m.sin(tl) * nrm[k]) for k in range(3)]
        d[2] = -_m.cos(t) * _m.cos(tl)
        L = _m.sqrt(sum(v * v for v in d))
        out.append(dict(type="directional", direction=[round(v / L, 4) for v in d], intensity=lux,
                        color=list(color), shadow=False))
    return out


LIGHTS = {
    # plate: a weak key from the top, a low warm light from the upper right and a warm near-frontal sheen light (the
    # sheen band across the plate's middle, both ends deep red); the front-bevel highlight is painted (rim_light below)
    "plate": dict(_KEY, key_lux=600.0, ibl_exp=-1.8,
                  extra=[dict(type="directional", direction=[-0.66, -0.66, -0.36], intensity=1300.0,
                              color=[1.0, 0.86, 0.72], shadow=False),
                         dict(type="directional", direction=[-0.15, -0.15, -0.977], intensity=2900.0,
                              color=[1.0, 0.80, 0.62], shadow=False)]),
    "spring": dict(_KEY, key_lux=1700.0, ibl_exp=-0.7, fill_color=(0.50, 0.66, 1.0), fill_lux=650.0,
                   extra=_fan()),
}


def _scaled(rig, k):
    r = dict(rig, key_lux=rig["key_lux"] * k, rim_lux=rig["rim_lux"] * k, fill_lux=rig["fill_lux"] * k)
    r["extra"] = [dict(e, intensity=e["intensity"] * k) for e in rig.get("extra", [])]
    return r


# the board sprite of the original is darker than its card render (board plate body 240,85,66 and ends 196-210 red;
# card 254,126,110 and ends 206-235): the board layers use the same rig scaled down
PLATE_BOARD_EXPOSURE = 0.72
LIGHTS["plate_board"] = _scaled(LIGHTS["plate"], PLATE_BOARD_EXPOSURE)
LIGHT = LIGHTS["plate"]
H = 1.0                      # board frame half-size in pitch: 2 x 2 pitch = 64 x 64 pt at 32 pt / pitch
ZB = (-0.05, 1.0)            # z range of the bounds (the camera fits the XY window at the top plane; fov 2 ~ orthographic)
FOV = 2.0
SHADOW = dict(dx=0.015, dy=0.040, sigma=0.010, alpha=0.13)   # pitch units, SCREEN space (y down)


OUTLINE = {"plate": ((0xA8, 0x10, 0x10), 0.016, 0.60), "spring": ((0x28, 0x33, 0x7A), 0.016, 0.60)}
# the card is the same art 2.3x bigger: its rims are thinner in pitch units and softer (456: edge 197,43,40 then 254,167,157)
OUTLINE_CARD = {"plate": ((0xC0, 0x1C, 0x1A), 0.010, 0.45), "spring": ((0x2C, 0x3A, 0x80), 0.010, 0.45)}   # colour, width p, mix


def outline(px_per_pitch, color, width, mix):
    """The capture's thin dark rim (1 capture px = 0.016 p on L70): pixels within `width` of the alpha edge are pulled
    toward `color` by `mix` (inside the silhouette only; the soft AA edge keeps its alpha)."""
    def post(im):
        import numpy as np
        from PIL import Image
        from scipy import ndimage
        a = np.asarray(im).astype(np.float32)
        al = a[..., 3] / 255.0
        inside = al > 0.5
        dist = ndimage.distance_transform_edt(inside) / px_per_pitch        # pitch units to the silhouette edge
        w = np.clip(1.0 - (dist - width) / (0.6 * width), 0, 1) * mix * (al > 0)
        c = np.array(color, np.float32)
        a[..., :3] = a[..., :3] * (1 - w[..., None]) + c * w[..., None]
        return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    return post


def rim_light(px_per_pitch, color, d0, d1, mix, facing=(0.7071, -0.7071), sharp=2.0):
    """A PAINTED bevel highlight (the PBR rim cannot be both this bright and this thin while the top keeps a broad sheen):
    pixels between d0 and d1 (pitch) inside the silhouette whose outward normal faces `facing` (screen, y down) are
    pulled toward `color`. Applied before any quarter-turn, so it stays on the side facing the screen-space light."""
    def post(im):
        import numpy as np
        from PIL import Image
        from scipy import ndimage
        a = np.asarray(im).astype(np.float32)
        inside = a[..., 3] > 127
        dist = ndimage.distance_transform_edt(inside) / px_per_pitch
        sm = ndimage.gaussian_filter(dist, 1.5)
        gy, gx = np.gradient(sm)
        nrm = np.stack([-gx, -gy], -1)
        nrm /= np.maximum(np.linalg.norm(nrm, axis=-1, keepdims=True), 1e-6)
        f = np.clip(nrm @ np.asarray(facing, np.float32), 0, 1) ** sharp
        mid, half = (d0 + d1) / 2, (d1 - d0) / 2
        band = np.clip(1 - np.abs(dist - mid) / half, 0, 1)
        w = (band * f * mix * inside)[..., None]
        a[..., :3] = a[..., :3] * (1 - w) + np.asarray(color, np.float32) * w
        return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    return post


RIM = dict(color=(0xFF, 0xB4, 0x96), d0=0.008, d1=0.055, mix=0.88)   # 457: 254,166,133 at 0.03 p inside the lit edge


# ---- the card's painted corrections (round 3 lane, corner.md "Card": measured on 456 along/across the plate and on the
# spring's tone bands; the board layers do not use them -- their region colours already sit within dE00 0.7-3.2)

def along_u(px_per_pitch, centre_px, fn):
    """A per-pixel weight from the plate coordinate u (pitch; +u = screen down-right for the canonical s = (1, -1)):
    fn(u) -> array. centre_px = the cell centre in the rendered frame (px)."""
    def w(shape):
        import numpy as np
        yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
        return fn(((xx + 0.5 - centre_px[0]) + (yy + 0.5 - centre_px[1])) / np.sqrt(2) / px_per_pitch)
    return w


def rim_light_u(px_per_pitch, centre_px, sigma, floor, **rim):
    """rim_light whose mix fades along the plate: the card's front-edge line is brightest mid-plate (456: G 165 at u 0,
    40-58 at u +-0.4) where our uniform rim was G 155-166 everywhere."""
    import numpy as np
    base = rim_light(px_per_pitch, **dict(rim, mix=1.0))
    weight = along_u(px_per_pitch, centre_px, lambda u: floor + (1 - floor) * np.exp(-(u / sigma) ** 2))

    def post(im):
        from PIL import Image
        a0 = np.asarray(im).astype(np.float32)
        a1 = np.asarray(base(im)).astype(np.float32)
        k = (weight(a0.shape[:2]) * rim["mix"])[..., None]
        out = a0.copy()
        out[..., :3] = a0[..., :3] + (a1[..., :3] - a0[..., :3]) * k
        return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")
    return post


def plate_ends(px_per_pitch, centre_px):
    """PAINTED end + back shading of the card plate (456 vs our render along the plate at n -0.1): both ends go deep pure
    red (G 27 at u -0.4, 15 at +0.4, 5 at +0.58; ours 50 / 29 / 16), the lower-right end darkens (R 236 at +0.4, 193 at
    +0.58; ours 255 / 242) and the back band is darker (L 46 vs 52 at n < -0.2). PBR shading of the rounded top cannot
    reach that red without going brown (PIPELINE "painted bevels")."""
    import numpy as np

    def gk(u):
        return np.interp(np.abs(u), [0.0, 0.24, 0.40, 0.58, 0.8], [1.0, 1.0, 0.55, 0.32, 0.32])

    def rk(u):
        return np.interp(u, [-0.8, -0.3, 0.30, 0.40, 0.58, 0.8], [0.97, 1.0, 1.0, 0.93, 0.80, 0.80])
    wg = along_u(px_per_pitch, centre_px, gk)
    wr = along_u(px_per_pitch, centre_px, rk)

    def back(shape):
        yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
        n = ((xx + 0.5 - centre_px[0]) - (yy + 0.5 - centre_px[1])) / np.sqrt(2) / px_per_pitch
        return np.interp(n, [-0.4, -0.24, -0.14, 0.5], [0.86, 0.86, 1.0, 1.0])

    def post(im):
        from PIL import Image
        a = np.asarray(im).astype(np.float32)
        g = wg(a.shape[:2]); r = wr(a.shape[:2]); b = back(a.shape[:2])
        a[..., 0] *= r * b
        a[..., 1] *= g * b
        a[..., 2] *= g * b
        return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    return post


# the card spring's tone ramp measured on 456 (its spring pixels in six luminance bands, dark -> light: mean luminance,
# mean colour); our render's light bands were sky blue (#9EB8DD, #BAD5F7) where 456's lobes are lavender grey
CARD_SPRING_RAMP = [(59, (0x2E, 0x38, 0x6A)), (79, (0x41, 0x4D, 0x7D)), (107, (0x59, 0x6C, 0x97)), (132, (0x6F, 0x86, 0xAD)),
                    (166, (0x93, 0xA8, 0xCA)), (205, (0xC0, 0xCF, 0xE5))]


def tone_ramp(ramp, mix):
    """Grade a layer onto a measured tone ramp by luminance: keeps the render's shading, takes the capture's hues."""
    import numpy as np
    ys = np.array([r[0] for r in ramp], np.float32)
    cs = np.array([r[1] for r in ramp], np.float32)

    def post(im):
        from PIL import Image
        a = np.asarray(im).astype(np.float32)
        Y = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
        t = np.stack([np.interp(Y, ys, cs[:, k]) for k in range(3)], -1)
        a[..., :3] = a[..., :3] * (1 - mix) + t * mix
        return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    return post


def chain(*fns):
    def post(im):
        for f in fns:
            im = f(im)
        return im
    return post


def drop_shadow(px_per_pitch, s=SHADOW):
    def post(im):
        from PIL import Image, ImageFilter
        a = im.getchannel("A")
        sig = max(0.3, s["sigma"] * px_per_pitch)
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sa = a.filter(ImageFilter.GaussianBlur(sig)).point(lambda v: int(round(v * s["alpha"])))
        blk = Image.new("RGBA", im.size, (0, 0, 0, 255)); blk.putalpha(sa)
        dx, dy = s["dx"] * px_per_pitch, s["dy"] * px_per_pitch
        blk = blk.transform(im.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.BILINEAR)
        out = Image.new("RGBA", im.size, (0, 0, 0, 0))
        out.alpha_composite(blk)
        out.alpha_composite(im)
        return out
    return post


def rotated(post, k):
    """post, then an exact k x 90-deg CCW pixel rotation about the frame centre (the frame is square, centred on the cell)."""
    def fn(im):
        from PIL import Image
        im = post(im)
        return im.transpose({1: Image.ROTATE_90, 2: Image.ROTATE_180, 3: Image.ROTATE_270}[k]) if k else im
    return fn


# facing s (screen, y down) -> the model's roll: +Y (front) must point along s; screen up = world +Y
ROLL = {(1, -1): -45.0, (-1, 1): 135.0}
PX_BOARD = 96.0              # px per pitch at @3x on the 32 pt design pitch
# turn name (SPEC-gameplay 3.9 / CornerTurn) -> (facing s, which render, extra CCW quarter turns)
FACINGS = {
    "DownRight": ((1, -1), (1, -1), 0),     # plate faces up-right: left->up, down->right
    "DownLeft": ((-1, -1), (1, -1), 1),     # plate faces up-left: the canonical render rotated 90 CCW
    "UpRight": ((1, 1), (1, -1), 3),        # plate faces down-right: the canonical render rotated 90 CW
    "UpLeft": ((-1, 1), (-1, 1), 0),        # plate faces down-left: its own render (turned 180, lit from the top again)
}


def board_case(model, render_facing, k, layer):
    return dict(scene=[(model, dict(roll=ROLL[render_facing], center=False, pos=(0, 0, 0)))],
                bounds=((-H, -H, ZB[0]), (H, H, ZB[1])), no_fit=True, margin=1.0, fov=FOV, frame=(64, 64),
                light=LIGHTS[layer + "_board" if layer == "plate" else layer],
                post_fit=rotated(chain(*([rim_light(PX_BOARD, **RIM)] if layer == "plate" else []),
                                       outline(PX_BOARD, *OUTLINE[layer]), drop_shadow(PX_BOARD)), k))


def _part(case):
    """Render a dest="parts" case of THIS recipe (build/ui-art/parts/<case>.png) and return it. `import ui3d` is a fresh
    module when ui3d.py runs as a script, so it is pointed at this recipe's directory first."""
    import os
    import sys as _sys
    from PIL import Image
    here = os.path.dirname(os.path.abspath(__file__))
    tools = os.path.join(os.path.dirname(here), "tools")
    if tools not in _sys.path:
        _sys.path.insert(0, tools)
    import ui3d
    ui3d.set_recipes(here)
    return Image.open(ui3d.render_case(case, "corner")).convert("RGBA")


def _over_part(post, case):
    """post (the spring layer's own steps), then the plate part laid on top: spring under plate, as the board draws them."""
    def fn(im):
        out = post(im).copy()
        out.alpha_composite(_part(case))
        return out
    return fn


# the per-turn layers (spring UNDER, plate OVER; the ids are spelled out so manifest_check finds every case in this file)
LAYERS = {"cornerDownRightSpring": ("DownRight", "spring"), "cornerDownRightPlate": ("DownRight", "plate"),
          "cornerDownLeftSpring": ("DownLeft", "spring"), "cornerDownLeftPlate": ("DownLeft", "plate"),
          "cornerUpRightSpring": ("UpRight", "spring"), "cornerUpRightPlate": ("UpRight", "plate"),
          "cornerUpLeftSpring": ("UpLeft", "spring"), "cornerUpLeftPlate": ("UpLeft", "plate")}

ASSETS = {}
for _case, (_turn, _layer) in LAYERS.items():
    _s, _rf, _k = FACINGS[_turn]
    ASSETS[_case] = board_case("cornerPlateOnly" if _layer == "plate" else "cornerSpringOnly", _rf, _k, _layer)
# the full model (proofs: layer composite vs one render)
ASSETS["cornerFull_draft"] = dict(board_case("corner", (1, -1), 0, "spring"), dest="route3d")

# `cornerWedge`: the id the board code loads (App/Board/CornerLayer.swift, ObstacleSet.spriteIDs, BoardArt.names) and the
# level bundle's sprite check expects (PathCore Validator.spriteIDs). ONE sprite = the UpRight corner (plate facing
# down-right), the orientation CornerNode draws at angle 0 and rotates for the other turns: the composite of
# cornerUpRightSpring + cornerUpRightPlate, pixel for pixel. Rotating it reproduces the original's DownRight / DownLeft
# lighting exactly; UpLeft is its own render in the original (corner.md "Facings"): the per-turn layers are the 1:1 route.
_wedge = board_case("cornerSpringOnly", (1, -1), FACINGS["UpRight"][2], "spring")
ASSETS["cornerWedgePlatePart"] = dict(board_case("cornerPlateOnly", (1, -1), FACINGS["UpRight"][2], "plate"), dest="parts")
ASSETS["cornerWedge"] = dict(_wedge, post_fit=_over_part(_wedge["post_fit"], "cornerWedgePlatePart"))

# unlock card icon (shot 456): ink bbox 150.5..242.6 x 367.4..459.1 pt, centre (196.55, 413.25); 73.4 pt per pitch (the card
# plate is 92.5 pt long vs 26.0 pt on L70's board at pitch 20.63: the same model, 3.56x). The frame (100 x 100 pt) is centred
# on the ink centre = corner-frame point (-0.180, +0.180) screen = world (-0.18, -0.18). The spring and the plate are
# rendered separately with their own light rigs (as on the board) and composited here: the case renders the spring, its
# post step renders the plate part with the same camera and lays it on top.
CARD_PT = 73.4
_c = (-0.180, -0.180)
_h = 50.0 / CARD_PT


def _card_case(model, layer, **kw):
    return dict(scene=[(model, dict(roll=-45.0, center=False, pos=(0, 0, 0)))],
                bounds=((_c[0] - _h, _c[1] - _h, ZB[0]), (_c[0] + _h, _c[1] + _h, ZB[1])), no_fit=True, margin=1.0,
                fov=FOV, frame=(100, 100), light=LIGHTS[layer], **kw)


def _card_post(im):
    """spring render (graded onto 456's tone ramp, outlined) + the plate part (outlined) + the drop shadow."""
    im = outline(CARD_PT * 3, *OUTLINE_CARD["spring"])(tone_ramp(CARD_SPRING_RAMP, 0.7)(im))
    out = im.copy()
    out.alpha_composite(_part("unlockIconCornerPlatePart"))
    return drop_shadow(CARD_PT * 3)(out)


_CARD_CELL_PX = ((50.0 - _c[0] * CARD_PT) * 3, (50.0 + _c[1] * CARD_PT) * 3)   # the cell centre in the 300 px frame
ASSETS["unlockIconCornerPlatePart"] = _card_case("cornerPlateOnly", "plate", dest="parts",
                                                 post_fit=chain(plate_ends(CARD_PT * 3, _CARD_CELL_PX),
                                                                rim_light_u(CARD_PT * 3, _CARD_CELL_PX, 0.22, 0.25, **RIM),
                                                                outline(CARD_PT * 3, *OUTLINE_CARD["plate"])))
ASSETS["unlockIconCorner"] = _card_case("cornerSpringOnlyCard", "spring", post_fit=_card_post)

# ------------------------------------------------------------------ PUBLISH R7 BOARD-UI: the D1 skin
# SPEC.md rulings 38 / 44 / 46 (same shape, same animation, new materials): the red plate becomes a MINT rubber bumper and
# the blue coil + base a BRASS coil. The model, camera, lights and every painted step above are unchanged (they carry the
# measured shape and shading); the final image goes through d1_skin.corner_post, a per-pixel material map that keeps each
# pixel's L* (the render's shading) and alpha (so frames, anchors and silhouettes are identical) and replaces its hue /
# chroma with the D1 material ladder (art/ui/src/d1_skin.py CORNER_WINDOWS). Applied ONCE, to the final composites only
# (the dest="parts" plate renders are composited into cornerWedge / unlockIconCorner first). CORNER_SKIN = "measured"
# renders the measured reference look (proofs).
import os as _os
import sys as _sys2

CORNER_SKIN = _os.environ.get("BOARD_SKIN", "d1")
if CORNER_SKIN == "d1":
    _src = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src")
    if _src not in _sys2.path:
        _sys2.path.insert(0, _src)
    import d1_skin as _d1

    for _case in list(LAYERS) + ["cornerWedge", "unlockIconCorner"]:
        ASSETS[_case] = dict(ASSETS[_case], post_fit=chain(ASSETS[_case]["post_fit"], _d1.corner_post))
