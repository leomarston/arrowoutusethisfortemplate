"""R2 CAST helper (no ASSETS: not a recipe): the D1 "Burrow Works" room + light, palettes, material helpers and the
BANDED FUR BLEND shared by char_boss.py, char_crew_d1.py and char_cast_d1.py (design/publish/art-direction.md §1.3, §3.1).

Forked from R1's art/pipeline/items/char_concepts_d1.py (the draft file stays as R1 left it); the room map writes the
same build/ui-art/char_env_d1.png, so drafts and production share one ambient.

Banded fur blend (R2 fix for R1's "muzzle edge grainy at 2x" / the orchestrator's 04:32 "speckled / blotchy muzzle"):
R1 grew the muzzle as a SECOND strand set whose roots were dithered against the body fur's, so in the transition every
strand was either full pink or full blush -> salt-and-pepper. Here ONE strand set is grown with one continuous groom
(the patch's comb and length blend in smoothly), then split into N material bands whose LUTs step from the body ladder
to the patch ladder; each strand goes to the band nearest its patch weight (stochastic rounding between the two
neighbours). Neighbouring strands then differ by at most 1/(N-1) of the colour step (N = 7: 17 %), which reads as a
soft gradient at 2x, not as speckle.
"""
from __future__ import annotations

import math
import os

import numpy as np

import char_fur as FUR
import char_kit as K
from mesher import Material
from uikit import Part, box, capsule, cylinder, ellipsoid, extrude, metal, polygon2, round_cone, satin, sphere, torus, union  # noqa: F401
from sdf import fillet_points

HERE = os.path.dirname(os.path.abspath(__file__))


# ================================================================== the D1 room + light (R6)

def env_d1(path=None):
    """Equirect room of the Burrow Works: warm timber + lantern light on one side, cool teal rock on the other, a cream
    daylight shaft from above, a packed-earth floor. Identical to R1's (same file)."""
    from PIL import Image
    path = path or os.path.join(K.APP, "build", "ui-art", "char_env_d1.png")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    phi = (u - 0.5) * 2 * math.pi
    theta = v * math.pi
    d = np.stack([np.sin(theta) * np.sin(phi), np.cos(theta), -np.sin(theta) * np.cos(phi)], -1)
    t = d[..., 1]
    ceil = np.array([0.93, 0.85, 0.68])
    timber = np.array([0.70, 0.50, 0.29])
    rock = np.array([0.28, 0.46, 0.48])
    floor = np.array([0.50, 0.39, 0.28])
    wmix = np.clip(0.5 + 0.55 * (-d[..., 0]), 0, 1)[..., None]
    wall = rock + (timber - rock) * wmix
    col = np.where(t[..., None] > 0, wall + (ceil - wall) * np.clip(t, 0, 1)[..., None] ** 0.8,
                   wall + (floor - wall) * np.clip(-t * 2.2, 0, 1)[..., None])
    for k, amp, width in (((-0.55, 0.62, 0.56), np.array([0.64, 0.52, 0.32]), 0.78),
                          ((0.70, 0.55, -0.45), np.array([0.36, 0.44, 0.42]), 0.86)):
        kk = K.unit(k)
        col = col + np.clip((d @ kk - width) / (1 - width), 0, 1)[..., None] ** 1.3 * amp
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(path)
    return path


# R6: the CHAR_LIGHT family (key 1730 lx warm; warm fill = fake SSS); the rim is a cool teal-white at 1150 lx
# (<= 1400 lx; never the old workers' 4200-lx hot orange rim); the D1 room as the ambient dome
LIGHT_D1 = dict(K.CHAR_LIGHT, env=env_d1(), rim_color=(0.80, 0.96, 0.92), rim_lux=1150.0,
                fill_color=(1.0, 0.80, 0.60), fill_lux=375.0)
# portraits / props: a touch more fill so small reads stay open
LIGHT_D1_SOFT = dict(LIGHT_D1, fill_lux=520.0, ibl_exp=-0.95)


def env_d1hk(path=None):
    """LOOK-L: the HIGH-KEY sunlit room of the Loading (owner 09-28 13:56: "not as smooth and good as the original"):
    a bright soft studio dome in the D1 warm family -- a near-white warm sky, a pale cream-mint horizon, a warm cream
    floor bounce (the sandstone flags), a BIG warm soft box upper-left-front (the broad window reflection a vinyl toy
    shows), a cool sky strip right-back (the rim's reflection) and a soft top box. LDR, made once."""
    from PIL import Image
    path = path or os.path.join(K.APP, "build", "ui-art", "char_env_d1hk.png")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    phi = (u - 0.5) * 2 * math.pi
    th = v * math.pi
    d = np.stack([np.sin(th) * np.sin(phi), np.cos(th), -np.sin(th) * np.cos(phi)], -1)
    t = d[..., 1]
    sky = np.array([0.97, 0.97, 0.96])
    hor = np.array([0.86, 0.90, 0.86])
    flo = np.array([0.95, 0.88, 0.76])
    col = np.where(t[..., None] > 0, hor + (sky - hor) * np.clip(t, 0, 1)[..., None] ** 0.7,
                   hor + (flo - hor) * np.clip(-t * 2.0, 0, 1)[..., None])
    for k, amp, width in (((-0.55, 0.62, 0.56), np.array([0.60, 0.56, 0.48]), 0.64),
                          ((0.78, 0.30, -0.55), np.array([0.36, 0.44, 0.52]), 0.80),
                          ((0.0, 1.0, 0.1), np.array([0.26, 0.26, 0.24]), 0.74)):
        kk = K.unit(k)
        col = col + np.clip((d @ kk - width) / (1 - width), 0, 1)[..., None] ** 1.2 * amp
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(path)
    return path


# LOOK-L: the Loading figures' rig -- high-key, soft gradients: a warm key from the upper left (1700 lx), a strong warm
# fill (520 lx: the shadow side stays light and coloured, the sunlit floor's bounce), a cool sky rim from the right-back
# (1000 lx <= 1400, A-bar R6: separation from value planning + a restrained rim), the bright room as the ambient dome
LIGHT_D1_HK = dict(K.CHAR_LIGHT, env=env_d1hk(), key_lux=1800.0, key_color=(1.0, 0.965, 0.92),
                   rim_lux=1000.0, rim_color=(0.90, 0.96, 1.0), fill_lux=420.0, fill_color=(1.0, 0.88, 0.76),
                   ibl_exp=-0.68)      # r3: a touch more key vs fill + ambient (the vinyl read a little flat at 1:1)


def env_d1hk2(path=None):
    """LOOK-L fix round 1 (the judges: "one dusty warm peach family ... warm characters must sit on a COOL ground"):
    the Loading's new room is a cool cerulean works with ONE warm-white daylight pool behind the boss, so the figures'
    dome turns COOL -- a pale cool sky, a cool blue-grey horizon, a pale cool floor bounce (the new flags) -- while the
    two things that give the vinyl its crisp speculars stay WARM: the big soft box upper-left-front (the key's window)
    and a warm-white strip BEHIND (the daylight pool: the rim's reflection). Warm light on cool shadows = the
    figure / ground separation, the way a studio shot does it. LDR, made once."""
    from PIL import Image
    path = path or os.path.join(K.APP, "build", "ui-art", "char_env_d1hk2b.png")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    phi = (u - 0.5) * 2 * math.pi
    th = v * math.pi
    d = np.stack([np.sin(th) * np.sin(phi), np.cos(th), -np.sin(th) * np.cos(phi)], -1)
    t = d[..., 1]
    sky = np.array([0.94, 0.955, 0.965])
    hor = np.array([0.80, 0.85, 0.86])
    flo = np.array([0.88, 0.90, 0.90])
    col = np.where(t[..., None] > 0, hor + (sky - hor) * np.clip(t, 0, 1)[..., None] ** 0.7,
                   hor + (flo - hor) * np.clip(-t * 2.0, 0, 1)[..., None])
    for k, amp, width in (((-0.55, 0.62, 0.56), np.array([0.62, 0.56, 0.46]), 0.66),     # the key's warm window
                          ((0.05, 0.28, -1.0), np.array([0.50, 0.47, 0.40]), 0.80),       # the daylight pool behind
                          ((0.0, 1.0, 0.1), np.array([0.20, 0.22, 0.24]), 0.76)):         # a soft top box
        kk = K.unit(k)
        col = col + np.clip((d @ kk - width) / (1 - width), 0, 1)[..., None] ** 1.2 * amp
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(path)
    return path


# LOOK-L fix round 1: the Loading figures' rig on the COOL ground -- a warm key upper-left (1800 lx), a COOL fill (the
# sky / pale floor bounce: shadows stay coloured but cool, never grey), a WARM-WHITE rim from BEHIND (the daylight pool
# the whole cast stands in front of; <= 1400 lx, A-bar R6) whose direction each case aims at the pool (LOAD_RIM below),
# the cool dome above as the ambient
LIGHT_D1_HK2 = dict(K.CHAR_LIGHT, env=env_d1hk2(), key_lux=1900.0, key_color=(1.0, 0.955, 0.89),
                    rim_lux=1200.0, rim_color=(1.0, 0.95, 0.86), fill_lux=420.0, fill_color=(0.95, 0.97, 1.0),
                    ibl_exp=-0.70)     # r2: a near-neutral dome + fill (r1's blue one greyed the mint ~10 C*)


def env_d1hk3(path=None):
    """LOOK-L fix round 2 (the finish judge on v3: "character light is flat -- even front / ambient light, a weak
    terminator, one flat tone per part"): a DIRECTIONAL dome for the modelling rig below -- the upper-left front is a
    big warm window (the key's side: the vinyl's broad soft reflection), the right side and the floor are the saturated
    azure room (a cool, coloured fill -- the ground's own blue bouncing back), the back a warm-white strip (the doorway
    behind the cast: the rim's reflection). Darker overall than hk2 so the key, not the dome, shapes the forms. LDR."""
    from PIL import Image
    path = path or os.path.join(K.APP, "build", "ui-art", "char_env_d1hk3b.png")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    phi = (u - 0.5) * 2 * math.pi
    th = v * math.pi
    d = np.stack([np.sin(th) * np.sin(phi), np.cos(th), -np.sin(th) * np.cos(phi)], -1)
    t = d[..., 1]
    sky = np.array([0.86, 0.90, 0.96])
    hor = np.array([0.66, 0.74, 0.84])
    flo = np.array([0.60, 0.72, 0.86])            # the azure floor's bounce (coloured, not grey)
    col = np.where(t[..., None] > 0, hor + (sky - hor) * np.clip(t, 0, 1)[..., None] ** 0.7,
                   hor + (flo - hor) * np.clip(-t * 2.0, 0, 1)[..., None])
    # the key's side is lighter and warmer, the far side (camera-right, away from the key) a deeper azure
    side = np.clip(-d[..., 0] * 0.8 + d[..., 1] * 0.3, -1, 1)[..., None]
    col = col * (0.82 + 0.16 * side) + np.array([0.08, 0.05, 0.0]) * np.clip(side, 0, 1)
    for k, amp, width in (((-0.60, 0.58, 0.55), np.array([1.00, 0.90, 0.74]), 0.72),     # the key's warm window
                          ((0.10, 0.25, -1.0), np.array([0.62, 0.56, 0.46]), 0.82),       # the doorway behind (rim)
                          ((0.0, 1.0, 0.15), np.array([0.14, 0.16, 0.18]), 0.80)):        # a soft top box
        kk = K.unit(k)
        col = col + np.clip((d @ kk - width) / (1 - width), 0, 1)[..., None] ** 1.3 * amp
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(path)
    return path


# LOOK-L fix round 2: the MODELLING rig -- a warm key from the upper left, more from the side (a visible terminator
# across heads and bellies), ~2:1 over a COOL coloured fill from camera-right (the azure room), a warm-white rim from
# the doorway behind (<= 1400 lx, A-bar R6; aimed per figure with rim_from), the directional dome above at a lower
# exposure so the lights, not an even ambient, shape the vinyl
# (tuned on cached drafts, build/p/LOOK/F2/review/lg_*: the first try -- a blue fill at 520 lx, dome at -1.05 -- dropped the
# mint to L* 54 / C* 32 with grey-blue shadows; this one keeps L* ~69, C* ~40 with a visible terminator)
LIGHT_D1_HK3 = dict(K.CHAR_LIGHT, env=env_d1hk3(), key_dir=(0.72, -0.52, -0.46), key_lux=3100.0, key_color=(1.0, 0.95, 0.86),
                    rim_lux=1250.0, rim_color=(1.0, 0.94, 0.84), fill_dir=(-0.55, -0.25, -0.80), fill_lux=1050.0,
                    fill_color=(1.0, 0.965, 0.92), ibl_exp=-0.90)


def env_d1hk4(path=None):
    """LOOK-2 (the finish judge on v4: "the specular is a hard, tiny, near-white clearcoat hotspot ... over teal-grey
    shadows ... the original has broad soft highlights and warm, saturated shadows. FIX: ... warm and saturate the
    shadow side by shifting the fill toward yellow-green, not blue"): hk3's directional dome with (a) a BIGGER, softer
    key window (a broad soft reflection on the satin vinyl, not a pin-point) and (b) the far side and the floor bounce
    WARM -- a pale honey / peach bounce instead of the azure room -- so the shadow side of mint skin lands on a warm
    yellow-green; the sky stays a light cool blue (the goggle lenses reflect it). LDR."""
    from PIL import Image
    path = path or os.path.join(K.APP, "build", "ui-art", "char_env_d1hk4.png")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    phi = (u - 0.5) * 2 * math.pi
    th = v * math.pi
    d = np.stack([np.sin(th) * np.sin(phi), np.cos(th), -np.sin(th) * np.cos(phi)], -1)
    t = d[..., 1]
    sky = np.array([0.80, 0.88, 0.97])
    hor = np.array([0.74, 0.72, 0.66])
    flo = np.array([0.78, 0.70, 0.54])            # a warm honey floor bounce
    col = np.where(t[..., None] > 0, hor + (sky - hor) * np.clip(t, 0, 1)[..., None] ** 0.7,
                   hor + (flo - hor) * np.clip(-t * 2.0, 0, 1)[..., None])
    side = np.clip(-d[..., 0] * 0.8 + d[..., 1] * 0.3, -1, 1)[..., None]
    far = np.array([0.80, 0.70, 0.56])            # the far side: a warm peach (not the azure room)
    col = col * (0.84 + 0.14 * side) + (far - col) * np.clip(-side, 0, 1) * 0.55
    for k, amp, width in (((-0.60, 0.58, 0.55), np.array([0.92, 0.82, 0.64]), 0.55),     # a BIG soft warm key window
                          ((0.10, 0.25, -1.0), np.array([0.62, 0.54, 0.40]), 0.80),       # the warm doorway behind (rim)
                          ((0.0, 1.0, 0.15), np.array([0.10, 0.12, 0.14]), 0.80)):        # a soft top box
        kk = K.unit(k)
        col = col + np.clip((d @ kk - width) / (1 - width), 0, 1)[..., None] ** 1.6 * amp
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(path)
    return path


# LOOK-2: the modelling rig with a warm fill (a honey-peach bounce from the camera-right / below) and a slightly softer key
LIGHT_D1_HK4 = dict(K.CHAR_LIGHT, env=env_d1hk4(), key_dir=(0.70, -0.52, -0.48), key_lux=2700.0, key_color=(1.0, 0.94, 0.84),
                    rim_lux=1300.0, rim_color=(1.0, 0.92, 0.78), fill_dir=(-0.55, -0.20, -0.80), fill_lux=1150.0,
                    fill_color=(1.0, 0.90, 0.72), ibl_exp=-0.85)


def lantern_lit(scale=1.0):
    """LOOK-2 (the finish judge: "the lantern: unlit cream plastic ... FIX: a brass frame and a warm emissive flame with a
    small glow halo"): the lantern() with a warm AMBER glass globe (a low-opacity-looking tinted shell: dark amber at the
    rim, hot at the core) and a bright FLAME inside, a saturated brass frame. The halo is added in 2-D (the sprite's
    post_fit). -> [(name, sdf, material, voxel)]"""
    s = scale
    out = []
    for n, sdf_, m, vx in lantern(scale):
        if n == "lanternBrass":
            m = K.skin("lan_brass4", BRASS4_LUT, None, rough=0.28, ior=1.5, clearcoat=0.3, cc_rough=0.10)
            out.append((n, sdf_, m, vx))
        else:
            out.append((n, sdf_, Material("lan_glow4", "#FFC45A", roughness=0.08, ior=1.45, emissive="#E07A12",
                                          clearcoat=0.8, clearcoat_roughness=0.04, opacity=0.62), vx))
    flame = union(ellipsoid(0.036 * s, 0.072 * s, 0.036 * s).translate(0, -0.29 * s, 0.0),
                  sphere(0.034 * s).translate(0, -0.32 * s, 0.0), k=0.02 * s)
    out.append(("lanternFlame", flame, Material("lan_flame4", "#FFF6D8", roughness=0.4, emissive="#FFF2C8"), 0.0015 * max(s, 0.5)))
    return out


BRASS4_LUT = [(0.0, "#F4C458"), (0.35, "#D29830"), (0.70, "#9C6414"), (1.0, "#5A3404")]    # a saturated brass (not cream)
# LOOK-2 round 2 (the finish judge on v5: "the frame is lemon-yellow plastic, not brass, the flame is a white egg ...
# FIX: desaturated brass with dark tarnish in the crevices; warm amber glass; an orange flame with a white-hot core"):
# (r2 render: the thin cage parts sit at obscurance u ~ 0 -- a pale #EAD49A end read cream-lemon; a darker old gold)
BRASS5_LUT = [(0.0, "#AC915E"), (0.25, "#8E7446"), (0.50, "#6E5830"), (0.75, "#4A3A1C"), (0.90, "#2C220E"), (1.0, "#1A1206")]


def lantern_lit5(scale=1.0):
    """lantern_lit with an aged BRASS frame (a desaturated old-gold, dark tarnish where the obscurance is deep: the
    cage roots, under the cap), a warm AMBER glass globe (tinted, semi-clear), and a FLAME = an orange tongue with a
    small white-hot core at its base (the core shows through the tongue's lower half). -> [(name, sdf, mat, voxel)]"""
    s = scale
    out = []
    for n, sdf_, m, vx in lantern(scale):
        if n == "lanternBrass":
            out.append((n, sdf_, K.skin("lan_brass5", BRASS5_LUT, None, rough=0.36, ior=1.5, clearcoat=0.18, cc_rough=0.14), vx))
        else:
            out.append((n, sdf_, Material("lan_glass5", "#E8963A", roughness=0.06, ior=1.45, emissive="#9A4A0A",
                                          clearcoat=0.9, clearcoat_roughness=0.03, opacity=0.50), vx))
    tongue = union(ellipsoid(0.030 * s, 0.050 * s, 0.030 * s).translate(0, -0.315 * s, 0.0),
                   round_cone((0, -0.30 * s, 0), (0.004 * s, -0.235 * s, 0), 0.024 * s, 0.004 * s), k=0.018 * s)
    core = ellipsoid(0.010 * s, 0.017 * s, 0.010 * s).translate(0, -0.326 * s, 0.022 * s)
    out.append(("lanternFlame", tongue, Material("lan_flame5", "#FF8420", roughness=0.5, emissive="#FF6400", opacity=0.94),
                0.0012 * max(s, 0.5)))
    out.append(("lanternCore", core, Material("lan_core5", "#FFFBEA", roughness=0.5, emissive="#FFF6D8"), 0.0010 * max(s, 0.5)))
    return out


def rim_from(dx, dy=-0.30):
    """The rim's direction (camera space, the direction the light TRAVELS) for a figure whose daylight pool sits at
    screen offset dx (-1 = far to its left, +1 = far to its right) behind it: the light comes from behind (-Z) and the
    pool's side, travelling toward the camera and away from the pool."""
    return tuple(float(c) for c in K.unit([-dx * 0.75, dy, 0.80]))


# the in-game glossy arrow enamel (the board's arrows / the flying block arrows): ONE saturated flat colour with a
# gentle obscurance ramp (the convex bevel lighter, the creases deeper) -- no wood rim, no edge wear, no noise: the
# "iced gingerbread" boards the judges flagged were the painted wood + worn rim of arrow_board
GLOSS_ARROW = {
    "tangerine": [(0.0, "#FFB14A"), (0.30, "#FF8E1C"), (0.62, "#F57500"), (0.86, "#D05C00"), (1.0, "#9A4200")],
    "coral": [(0.0, "#FF8D74"), (0.30, "#FA5A40"), (0.62, "#E63D26"), (0.86, "#C22A16"), (1.0, "#8A1A0C")],
    "sunflower": [(0.0, "#FFE77E"), (0.30, "#FFCF22"), (0.62, "#F7B500"), (0.86, "#D99500"), (1.0, "#9C6600")],
    "teal": [(0.0, "#78F2DF"), (0.30, "#1CCBB5"), (0.62, "#0CA897"), (0.86, "#078777"), (1.0, "#045A50")],
    "sky": [(0.0, "#A6E8FF"), (0.30, "#3CBDF4"), (0.62, "#1A99D6"), (0.86, "#107AB2"), (1.0, "#0A527A")],
    "berry": [(0.0, "#FF8FC2"), (0.30, "#F2549E"), (0.62, "#DC3582"), (0.86, "#B82368"), (1.0, "#7E1446")],
}


def glossy_arrow(paint="tangerine", length=1.0, width=0.70, shaft=0.38, head_len=0.44, depth=0.17, bevel=0.07, tag="",
                 R=None, t=None):
    """LOOK-L fix round 1: a chunky GLOSSY enamel arrow (the game's own arrow material: a clean clearcoat over one
    saturated colour, a fat rounded bevel that catches the soft boxes as a crisp highlight line) instead of the painted
    wooden arrow board. Placed like arrow_board (frame R: columns = x, y (the point), z (the face)) at t.
    -> [(name, sdf, mat, voxel)]"""
    R = np.eye(3) if R is None else np.asarray(R, float)
    t = np.zeros(3) if t is None else np.asarray(t, float)
    s2 = arrow2d(length, width, shaft, head_len)
    body = extrude(s2, depth / 2, round=min(bevel, depth / 2 * 0.92))
    m = K.skin(f"garr_{paint}{tag}", GLOSS_ARROW[paint], None, vfn=None, rough=0.26, ior=1.46, clearcoat=0.85, cc_rough=0.05)
    return [(f"arrow{tag}", body.transform(R).translate(*t), m, 0.0032)]


# ================================================================== palettes (art-direction.md §3.1)

WOOD0 = [(0.0, "#F2C586"), (0.45, "#E0A862"), (0.8, "#B97A3E"), (1.0, "#7E4E27")]
WOOD1 = [(0.0, "#D9A462"), (0.45, "#B97A3E"), (0.8, "#8E5A2F"), (1.0, "#5E3718")]
LEATHER = [(0.0, "#B8824F"), (0.45, "#8E5A2F"), (0.8, "#6A3F1E"), (1.0, "#43260F")]
BRASS = "#E3B04B"
BRASS_LUT = [(0.0, "#FFE39A"), (0.40, "#E8B85A"), (0.75, "#C08A2E"), (1.0, "#7E5510")]
IRON = "#4B4F55"
HAT = [(0.0, "#FFE27A"), (0.4, "#FFCB2F"), (0.75, "#EDA80E"), (1.0, "#B77C04")]
VEST = [(0.0, "#FFB36A"), (0.45, "#FF8A2A"), (0.75, "#E26A12"), (1.0, "#A64806")]
STRIPE = [(0.0, "#FFFCF0"), (0.5, "#FFF4DA"), (1.0, "#D8C8A4")]
ROCK = [(0.0, "#8FB7B8"), (0.35, "#6A979B"), (0.7, "#4E7F86"), (1.0, "#1B3A40")]
ROCK1 = [(0.0, "#7FA5A4"), (0.35, "#5B8589"), (0.7, "#3F6B72"), (1.0, "#16323A")]
EARTH = [(0.0, "#C79A6A"), (0.4, "#A77A4E"), (0.75, "#7E5634"), (1.0, "#4A3018")]
EARTH1 = [(0.0, "#B8895A"), (0.4, "#946A42"), (0.75, "#6C4A2C"), (1.0, "#3E2812")]
PARCHMENT = [(0.0, "#FFF6E0"), (0.4, "#F6E6C2"), (0.75, "#E3CC9C"), (1.0, "#B89A66")]
PARCHMENT1 = [(0.0, "#F4E4C0"), (0.4, "#E8D2A4"), (0.75, "#D2B680"), (1.0, "#A8884E")]
INK = "#3E2A1C"
# the arrow boards' painted faces (the D1 accents: tangerine CTA, the teal chrome, sunflower, coral, crystal sky)
BOARD_PAINT = {
    "tangerine": [(0.0, "#FFC46A"), (0.35, "#FF9A12"), (0.7, "#E27608"), (1.0, "#A84E00")],
    "teal": [(0.0, "#7FEADB"), (0.35, "#17B3A3"), (0.7, "#0B8A83"), (1.0, "#075E5E")],
    "sunflower": [(0.0, "#FFE88A"), (0.35, "#FFCB2F"), (0.7, "#EDA80E"), (1.0, "#B77C04")],
    "coral": [(0.0, "#FF9C86"), (0.35, "#F2553F"), (0.7, "#D23A26"), (1.0, "#9A2414")],
    "sky": [(0.0, "#C8F4FF"), (0.35, "#7FE6FF"), (0.7, "#3FBCE0"), (1.0, "#1A7FA6")],
    "mint": [(0.0, "#D6FFF0"), (0.35, "#86E8C6"), (0.7, "#4CCBA5"), (1.0, "#1C8068")],
}


# ================================================================== small helpers

def slab_y(y0, y1, big=3.0):
    return box(big, (y1 - y0) / 2, big).translate(0, (y0 + y1) / 2, 0)


def sdf_fn(sdf):
    return lambda p: sdf(np.asarray(p, np.float32))


def grain_vfn(freq=26.0, axis=0, seed=1):
    """Wood grain for the v term of a 2-ramp LUT: streaks along `axis`, warped by value noise."""
    from sdf import value_noise3

    def fn(v):
        p = np.asarray(v, np.float32)
        other = [i for i in range(3) if i != axis]
        n = value_noise3(p * np.float32(1.0), freq=3.0, seed=seed)
        s = np.sin(freq * (p[:, other[0]] * 1.0 + p[:, other[1]] * 0.6) + 5.0 * n)
        return np.clip(0.5 + 0.5 * s, 0, 1) ** 2.2
    return fn


def canvas_vfn(freq=34.0, seed=9):
    """Heathered canvas: two octaves of value noise for the v term of a 2-ramp LUT."""
    from sdf import value_noise3

    def fn(v):
        p = np.asarray(v, np.float32)
        n = 0.65 * value_noise3(p, freq=freq, seed=seed) + 0.35 * value_noise3(p, freq=freq * 2.7, seed=seed + 1)
        return np.clip(0.5 + 0.9 * n, 0, 1)
    return fn


def rock_vfn(freq=7.0, seed=3):
    """Mottled rock / earth: a low + a high octave."""
    from sdf import value_noise3

    def fn(v):
        p = np.asarray(v, np.float32)
        n = 0.7 * value_noise3(p, freq=freq, seed=seed) + 0.3 * value_noise3(p, freq=freq * 3.1, seed=seed + 7)
        return np.clip(0.5 + 1.1 * n, 0, 1)
    return fn


def wear_vfn(sdf, width=0.012, seed=5, gain=1.0):
    """Worn edges for a painted / hard part: ~1 on the part's convex edges, 0 on flat faces, broken up by fine noise ->
    the v term picks the 'worn' ramp there. Convexity = the SDF's discrete Laplacian at scale `width` (the mean of the
    six axis samples at +-width: 0 on a plane, > 0 on a convex edge)."""
    from sdf import value_noise3
    h = np.float32(width)
    offs = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], np.float32) * h

    def fn(v):
        p = np.asarray(v, np.float32)
        lap = np.zeros(len(p), np.float32)
        for o in offs:
            lap += sdf(p + o)
        lap /= 6.0
        e = np.clip(lap / (0.18 * h) * gain, 0, 1)
        n = value_noise3(p, freq=60.0, seed=seed)
        return np.clip(e * (0.75 + 0.5 * n), 0, 1)
    return fn


def painted_metal(name, paint, worn, sdf, rough=0.34, width=0.010):
    """A painted / blued steel part with bright worn edges: LUT v = 0 paint, 1 worn metal."""
    return K.skin(name, paint, worn, vfn=wear_vfn(sdf, width), rough=rough, ior=1.45)


def lut_rgb(stops, u, v):
    return FUR.lut_v(stops)(np.asarray(u, float), np.asarray(v, float))


def blend_stops(a, b, t, nu=9):
    """Fur LUT stops [(v, [(u, hex)])] mixed a -> b at t (sRGB), resampled on the union of the v rows, nu u stops."""
    vs = sorted({s[0] for s in a} | {s[0] for s in b})
    us = np.linspace(0, 1, nu)
    out = []
    for vv in vs:
        U = us[None, :]
        V = np.full_like(U, vv)
        ca = lut_rgb(a, U, V)[0]
        cb = lut_rgb(b, U, V)[0]
        c = ca * (1 - t) + cb * t
        out.append((vv, [(float(u), "#%02X%02X%02X" % tuple(int(round(x * 255)) for x in np.clip(ci, 0, 1)))
                         for u, ci in zip(us, c)]))
    return out


# ------------------------------------------------------------------ strand-set cache + banded parts

_STRANDS = {}


def cached(key, build):
    """One strand set per key per process (the band parts of one set share it)."""
    if key not in _STRANDS:
        _STRANDS[key] = build()
    return _STRANDS[key]


def subset(V, Fc, NR, uv, nv, keep):
    """The strands `keep` (bool per strand) of a strands() result: vertices [i*nv, (i+1)*nv) per strand."""
    keep = np.asarray(keep, bool)
    vmask = np.repeat(keep, nv)
    newidx = np.cumsum(vmask) - 1
    fk = vmask[Fc[:, 0]]
    F2 = newidx[Fc[fk]]
    return V[vmask], F2, NR[vmask], uv[vmask]


def band_of(w, bands, rng):
    """Stochastic rounding of w in [0, 1] onto 0 .. bands-1."""
    x = np.clip(np.asarray(w, float), 0, 1) * (bands - 1)
    lo = np.floor(x)
    return (lo + (rng.random(len(x)) < (x - lo))).astype(int).clip(0, bands - 1)


def banded_fur_parts(prefix, key, build, stops_a, stops_b, bands=7, rough=0.60, mat_prefix=None):
    """build() -> dict(V, F, NR, uv, nv, w) with w = the patch weight per STRAND (0 = body, 1 = patch).
    Returns `bands` premeshed fur Parts named <prefix>0..<prefix>{bands-1}; empty bands are dropped at mesh time
    (they return a degenerate single triangle, filtered by the caller's `only`)."""
    mat_prefix = mat_prefix or prefix
    parts = []

    def get():
        return cached(key, build)
    for b in range(bands):
        t = b / (bands - 1)
        m = FUR.fur_material(f"{mat_prefix}_b{b}", None, stops=blend_stops(stops_a, stops_b, t), rough=rough)

        def fn(b=b):
            S = get()
            keep = S["band"] == b
            if not keep.any():
                # an empty band: one invisible sliver far inside the body (mesh writers need >= 1 triangle)
                c = np.asarray(S["V"][0], float)
                v = np.stack([c, c + [1e-5, 0, 0], c + [0, 1e-5, 0]])
                return v, np.array([[0, 1, 2]]), np.tile([[0, 0, 1.0]], (3, 1)), np.full((3, 2), 0.5)
            return subset(S["V"], S["F"], S["NR"], S["uv"], S["nv"], keep)
        parts.append(FUR.fur_part(f"{prefix}{b}", m, fn))
    return parts


def band_names(prefix, bands=7):
    return {f"{prefix}{b}" for b in range(bands)}


# ================================================================== props shared by the cast

def arrow2d(length=1.0, width=0.66, shaft=0.36, head_len=0.44):
    """A chunky arrow outline pointing +Y, centred on its bbox (2-D SDF)."""
    L, W, S, H = length, width, shaft, head_len
    y0, y1 = -L / 2, L / 2
    pts = [(-S / 2, y0), (S / 2, y0), (S / 2, y1 - H), (W / 2, y1 - H), (0.0, y1), (-W / 2, y1 - H), (-S / 2, y1 - H)]
    return polygon2(fillet_points(pts, [0.03, 0.03, 0.025, 0.04, 0.05, 0.04, 0.025], n_arc=5))


def arrow_board(paint="tangerine", length=1.0, width=0.66, shaft=0.36, head_len=0.44, depth=0.11, seed=1, R=None, t=None):
    """A hand-painted wooden ARROW BOARD (the D1 arrow motif: the Signpost's boards, the loading cart's load): a timber
    core with rounded edges and wood grain on the sides, a painted front + back face (a thin raised coat) worn back
    to the wood ONLY along a narrow band at the outline (2-D edge distance; R2 v1's 3-D curvature wear on the thin
    face read as muddy all over). Placed with frame R (columns = board x, y (the arrow's point), z (the face)) at t.
    -> [(name, sdf, material, voxel)] in world space."""
    from sdf import value_noise3
    R = np.eye(3) if R is None else np.asarray(R, float)
    t = np.zeros(3) if t is None else np.asarray(t, float)
    s2 = arrow2d(length, width, shaft, head_len)
    core = extrude(s2, depth / 2, round=min(0.035, depth / 2 * 0.9))
    face = extrude(s2.offset(-0.035), 0.012, round=0.010).translate(0, 0, depth / 2 + 0.002)
    back = extrude(s2.offset(-0.035), 0.012, round=0.010).translate(0, 0, -depth / 2 - 0.002)

    def edge_wear(v):
        q = (np.asarray(v, float) - t) @ R               # world -> board space
        d = -np.asarray(s2(q[:, :2].astype(np.float32)), float) - 0.035   # distance inside the painted face's outline
        n = value_noise3(q.astype(np.float32), freq=40.0, seed=seed)
        return np.clip(1.0 - d / (0.030 + 0.012 * n), 0, 1) ** 2
    wood = K.skin(f"brd_wood{seed}", WOOD0, WOOD1, vfn=grain_vfn(40, 1, seed), rough=0.62, ior=1.25)
    pm = K.skin(f"brd_{paint}{seed}", BOARD_PAINT[paint], WOOD0, vfn=edge_wear, rough=0.40, ior=1.35)

    def xf(q):
        return q.transform(R).translate(*t)
    return [("board", xf(core), wood, 0.004), ("boardFace", xf(union(face, back)), pm, 0.003)]


def place_parts(parts, R=np.eye(3), t=(0, 0, 0), s=1.0):
    """Transform [(name, sdf, mat, voxel)] rigidly (+ uniform scale)."""
    out = []
    for n, sdf_, m, vx in parts:
        q = sdf_.scale(s) if s != 1.0 else sdf_
        out.append((n, q.transform(np.asarray(R, float)).translate(*np.asarray(t, float)), m, vx * (s if s < 1 else 1.0)))
    return out


def lantern(scale=1.0):
    """A brass miner's lantern with a glowing glass globe, a wire cage and a bail handle (origin = the handle top,
    hanging down -Y). -> [(name, sdf, material, voxel)]"""
    s = scale
    base = cylinder(0.11 * s, 0.03 * s, round=0.012 * s).translate(0, -0.44 * s, 0)
    cap = union(cylinder(0.095 * s, 0.025 * s, round=0.01 * s).translate(0, -0.13 * s, 0),
                cylinder(0.05 * s, 0.03 * s, round=0.01 * s).translate(0, -0.09 * s, 0))
    glob = union(capsule((0, -0.36 * s, 0), (0, -0.22 * s, 0), 0.085 * s))
    cage = []
    for a in range(4):
        ang = a * math.pi / 2 + math.pi / 4
        x, z = math.cos(ang) * 0.095 * s, math.sin(ang) * 0.095 * s
        cage.append(capsule((x, -0.42 * s, z), (x, -0.15 * s, z), 0.009 * s))
    cage.append(torus(0.098 * s, 0.009 * s).translate(0, -0.29 * s, 0))
    bail = torus(0.10 * s, 0.010 * s).transform(K.rotate_matrix((1, 0, 0), 90)).intersect(
        box(1, 0.2 * s, 1).translate(0, 0.2 * s, 0)).translate(0, -0.08 * s, 0)
    brass = K.skin("lan_brass", BRASS_LUT, None, rough=0.30, ior=1.5)
    return [("lanternBrass", union(base, cap, *cage, bail), brass, 0.002 * max(s, 0.5)),
            ("lanternGlass", glob, Material("lan_glow", "#FFE7A0", roughness=0.15, ior=1.45, emissive="#FFC860"),
             0.002 * max(s, 0.5))]
