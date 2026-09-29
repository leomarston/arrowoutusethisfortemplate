"""missing-3d lane: the Out of Lives heart and the frost overlay of the hourglass (freeze) booster.

    heartBig3d        (ROUTE CANDIDATE, not shipped: the missing-svg lane owns and ships heartBig as SVG)
                      meta-088 "Out of Lives!": one whole glossy red heart, 186 x 157 pt, with its dark-red glow on the
                      dimmed screen. The same heart family as the 3d-hud lane's heartInfinite / heartBroken (its
                      heart_body + painted "red" scheme), rendered big and plump.
    fxFrostVignette   meta-065 (L62 right after the hourglass): the whole-screen frost frame -- saturated cyan at the
                      screen edges (deepest along the top and bottom and in the corners), melting into a white haze,
                      with thin white ice cracks, soft snow sparkles and tiny snowflakes; transparent in the middle.
                      SPEC-ui 4.2 proposed a code vignette + a 120 pt crack tile; one full-screen raster (393 x 852,
                      drawn between the board and the HUD) reproduces the capture more closely and costs one texture.

References (LOOKED AT only; measured in pt on gridded crops): research/shots/meta-088-L062-hearts-out-1.png,
meta-065-L062-after-hourglass.png (+ meta-066..068). Everything here is ours: an SDF heart rendered by mfrender, the
frost painted in code from value noise and random walks.
"""
from __future__ import annotations

import math
import sys

import numpy as np
from PIL import Image

import m3d_kit as MK
import scene_kit as K
from scene_kit import Canvas, aa, rgb, stops_interp, F

_M = sys.modules[__name__]
HP = MK.HP


# ====================================================================== heartBig (meta-088)
# meta-088 (pt): the heart spans x 104-290, y 319-476 (186 x 157: h / w 0.845), centre (197, 397.5); round full lobes,
# a soft rounded tip; face #F01A10, lit #FF5A40 upper left, a big soft pink-white specular on the left lobe, a crisp
# streak on the right lobe's upper-right edge, deep red #B00808 toward the lower right; a dark-red glow ~10-14 pt round
# it. Frame 205 x 177 at (94.5, 309): the heart in the middle 186 x 157, the glow in the margin.
HB_VIEW = (0, -4, 0)


HB_RED = dict(top="#FF4C34", mid="#F21C12", bot="#E2140C", etop="#C00C08", ebot="#8A0606")


def heart_mask(px=900):
    """meta-088's outline (width 1): two round lobes (r 0.275 at +-0.225, 0.13), a shallow notch, CONVEX lower sides
    (an ellipse rx 0.43 / ry 0.30 under the lobes) running into a soft round tip at y -0.43 (height 0.835 = 157 / 186)."""
    from PIL import ImageDraw, ImageFilter
    ext = (-0.62, -0.60, 0.62, 0.60)
    W = px
    Hh = int(round(px * 1.2 / 1.24))
    im = Image.new("L", (W, Hh), 0)
    dr = ImageDraw.Draw(im)

    def P(x, y):
        return ((x - ext[0]) / (ext[2] - ext[0]) * W, (ext[3] - y) / (ext[3] - ext[1]) * Hh)
    lob_r, lob_y, tip = 0.275, 0.13, (0.0, -0.40, 0.045)
    for cx in (-0.225, 0.225):
        (x0, y0), (x1, y1) = P(cx - lob_r, lob_y + lob_r), P(cx + lob_r, lob_y - lob_r)
        dr.ellipse([x0, y0, x1, y1], fill=255)
    # the lower body = the convex hull of the lobes' lower halves and the tip disc (straight-to-convex sides)
    pts = []
    for cx in (-0.225, 0.225):
        for a in np.linspace(math.pi, 2 * math.pi, 40):
            pts.append((cx + lob_r * math.cos(a), lob_y + lob_r * math.sin(a)))
    for a in np.linspace(0, 2 * math.pi, 40):
        pts.append((tip[0] + tip[2] * math.cos(a), tip[1] + tip[2] * math.sin(a)))
    for a in np.linspace(math.pi, 2 * math.pi, 60):     # the full lower flanks (meta-088: ~0.40 out at y -0.12)
        pts.append((0.455 * math.cos(a), -0.02 + 0.325 * math.sin(a)))
    from scipy.spatial import ConvexHull
    pts = np.array(pts)
    hull = pts[ConvexHull(pts).vertices]
    # a slight outward bulge of the sides (meta-088's flanks are a touch convex)
    c = np.array([0.0, -0.05])
    v = hull - c
    lowmask = hull[:, 1] < lob_y
    bul = 1 + 0.02 * np.sin(np.clip((lob_y - hull[:, 1]) / (lob_y - tip[1]), 0, 1) * math.pi)
    hull = np.where(lowmask[:, None], c + v * bul[:, None], hull)
    dr.polygon([P(x, y) for x, y in hull], fill=255)
    im = im.filter(ImageFilter.GaussianBlur(px * 0.012))
    return np.asarray(im) > 127, ext


def inflate(mask, ext, depth, iters=900):
    """Harmonic inflation of a 2D outline (the Teddy trick): solve  laplace(h) = -1  inside the mask (h = 0 outside) by
    Jacobi iterations, then the surface is z = +-depth * sqrt(h / max h) -- one smooth dome, no medial-axis crease
    (an extruded pillow creases where two rims meet). Returns an SDF (a Lipschitz-damped bound)."""
    from scipy import ndimage
    from scipy.ndimage import map_coordinates
    from uikit import raster_sdf2
    from scene_kit import SDF
    small = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).resize((mask.shape[1] // 3, mask.shape[0] // 3),
                                                                             Image.BILINEAR)) > 127
    # solve laplace(h) = -1 inside, h = 0 outside, DIRECTLY (sparse): Jacobi sweeps never converge on a 300 px grid
    # (round 1 left a flat plateau with a rim -- a visible ring on the heart's face)
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla
    m = small
    idx = -np.ones(m.shape, np.int64)
    ys, xs = np.nonzero(m)
    idx[ys, xs] = np.arange(len(ys))
    rows, cols, vals = [np.arange(len(ys))], [np.arange(len(ys))], [np.full(len(ys), 4.0)]
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        yy, xx = ys + dy, xs + dx
        ok = (yy >= 0) & (yy < m.shape[0]) & (xx >= 0) & (xx < m.shape[1])
        j = np.full(len(ys), -1)
        j[ok] = idx[yy[ok], xx[ok]]
        good = j >= 0
        rows.append(np.nonzero(good)[0]); cols.append(j[good]); vals.append(np.full(good.sum(), -1.0))
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(len(ys), len(ys)))
    sol = spla.spsolve(A.tocsc(), np.ones(len(ys)))
    h = np.zeros(m.shape)
    h[ys, xs] = sol
    m = m.astype(np.float64)
    h = ndimage.gaussian_filter(h, 1.0) * m
    zmap = ndimage.gaussian_filter(np.clip(h / h.max(), 0, 1) ** 0.5, 1.5) * depth
    Hs, Ws = zmap.shape
    xmin, ymin, xmax, ymax = ext
    sx = (xmax - xmin) / Ws
    s2 = raster_sdf2(mask, ext)

    def fn(p):
        x = (p[:, 0] - xmin) / sx - 0.5
        y = (ymax - p[:, 1]) / sx - 0.5
        zs = map_coordinates(zmap, [y, x], order=1, mode="constant", cval=0.0)
        d2 = s2(p[:, :2])
        dz = np.abs(p[:, 2]) - zs
        return (np.maximum(d2, dz * 0.55)).astype(F)
    return SDF(fn, np.array([xmin, ymin, -depth - 0.02]), np.array([xmax, ymax, depth + 0.02]))


def heart_big():
    """A full, round heart inflated as one smooth dome."""
    mask, ext = heart_mask()
    body = inflate(mask, ext, 0.34)
    # nearly no specular from the rig (a broad env reflection washed the face pink); the highlights are painted
    return [MK.painted("heart", body, HB_RED, -0.45, 0.41, HB_VIEW, rough=0.55, ior=1.04, e0=0.55, e1=1.0)], 0.004


MODELS = {"heartBig": heart_big}


def build_heart_big(ctx):
    light = dict(HP.PROP_LIGHT)
    light.update(key_lux=1450.0, fill_lux=420.0, rim_lux=900.0,
                 extra=[dict(type="directional", direction=[0.05, -0.12, -1.0], intensity=260.0, color=[1.0, 1.0, 1.0],
                             shadow=False)])
    env = K.scene_env("heartdark", sky=(1.0, 0.92, 0.9), hor=(0.42, 0.10, 0.09), gnd=(0.16, 0.02, 0.02),
                      boxes=(((-0.45, 0.62, 0.62), (0.95, 0.85, 0.82), 0.80), ((0.75, 0.35, -0.55), (0.45, 0.30, 0.30), 0.86)))
    ims = ctx.render({"heartBig": dict(scene=[(_M, "heartBig", dict(yaw=HB_VIEW[0], pitch=HB_VIEW[1]))], fov=18, px=1400,
                                       light=K.rig(base=dict(ui3d_rig(), **light), env=env))}, tag="heartBig")
    cv = Canvas(205, 177)
    # the dark-red glow round the heart (meta-088: a warm halo on the dimmed board)
    X, Y = cv.X, cv.Y
    g = np.exp(-(((X - 102.5) / 104.0) ** 2 + ((Y - 90.0) / 88.0) ** 2) * 2.6)
    cv.fill(np.clip(g * 1.25, 0, 1), "#A0100C", 0.55)
    MK.fit_into(cv, ims["heartBig"], (9.5, 10.0, 195.5, 167.0), mode="stretch", align=(0.5, 0.5))
    # painted highlights (ours, measured on meta-088): a big soft pink-white bloom on the left lobe, a soft spot on the
    # right lobe's top and a crisp arc glint along its upper-right edge
    heart_a = cv.a[..., 3].copy()

    def blob(cx, cy, rx, ry, ang, col, alpha, power=1.6):
        a = math.radians(ang)
        u = (X - cx) * math.cos(a) + (Y - cy) * math.sin(a)
        v = -(X - cx) * math.sin(a) + (Y - cy) * math.cos(a)
        g = np.clip(1 - np.sqrt((u / rx) ** 2 + (v / ry) ** 2), 0, 1) ** power
        cv.screen(g * np.clip(heart_a * 1.2 - 0.2, 0, 1), col, alpha)
    blob(58, 44, 25, 15, -32, "#FFB8A8", 0.70)
    blob(58, 42, 10, 6, -32, "#FFE6DE", 0.55)
    blob(146, 26, 14, 8, 20, "#FFB0A0", 0.45)
    blob(176, 34, 11, 3.0, 58, "#FFF2EE", 0.85, power=1.0)
    # meta-088's heart has a crisp dark-red rim line just outside the body, inside the glow
    rim = np.clip(K.blur(heart_a, 2.0) - heart_a, 0, 1)
    cv.fill(np.clip(rim * 3.0, 0, 1), "#9A0606", 0.9)
    MK.edge_fade(cv, 3.0)
    return cv.image()


def ui3d_rig():
    return dict(MK.ui3d.RIG)


# ====================================================================== fxFrostVignette (meta-065)
# meta-065 (pt): cyan (#3ED6F2 at the very edge -> #7FE6F8 -> #C4F4FC) along the top ~0-30 fading to white haze by
# ~70-100; along the sides only ~0-14 cyan fading by ~35; the bottom ~800-852 cyan fading up to ~720 at the corners;
# the corners hold the most frost (top-left down to y ~200, bottom-left up to ~680). White crack lines ~0.8-1.2 pt,
# a few soft sparkles 2-6 pt, tiny 6-arm snowflakes 3-6 pt in the cyan.
def build_frost(ctx=None):
    """to-A r4: re-fitted on 065 against 058 (the same L62 board unfrozen). The frost is ONE translucent colour layer,
    no white haze: over the board it stays thin (065 x 20 pt over a black arrow = 0c1525 vs 000000, alpha ~0.16; over
    white E1ECFD), so the arrows at the board's edge stay black (round 3's 0.8 white haze greyed them). Alpha profiles
    read off the R channel (C0 R 70-90), pt from each edge:
      sides  (y 450) 0.9 @0-3, 0.62 @10, 0.38 @15, 0.18 @20, 0 @28; deeper toward the top / bottom (y 180, 700: 0.34-0.5
             @20, ~0.1 @30-40);
      top    (x 330) 0.64 @2 (a light rim), 0.93 @20-40, 0.70 @60, 0.47 @70, 0.30 @80, 0.11 @100, ~0.03 @130;
      bottom (x 130) 0.82 @2, 1.0 @18, 0.83 @34, 0.64 @42, 0.41 @52, 0.25 @62, 0.14 @72, 0.06 @82, 0 @92.
    Colour: a saturated CYAN core at the top / bottom (5DE3F9 / 46DCF9 over white) and a bluer azure along the middle of
    the sides (83CBF7 @6), turning azure-blue as it fades (the layer colour ~(110, 160, 245) at low alpha); a light
    greener rim in the outer ~2 pt (A4EEFD). Cracks are sparse and faint (065: a few thin lines in the corners)."""
    W, H = 393, 852
    cv = Canvas(W, H)
    X, Y = cv.X, cv.Y
    n1 = K.noise2(cv.h, cv.w, 150, seed=3, octaves=4)
    n2 = K.noise2(cv.h, cv.w, 40, seed=7, octaves=3)
    streak = K.noise2(cv.h, cv.w, 12, seed=19, octaves=2)
    s3 = lambda t: K.smooth(t, 0.0, 1.0)
    n3 = K.noise2(cv.h, cv.w, 60, seed=23, octaves=3)
    dx = np.minimum(X, W - X) * (1 + 0.22 * n3 + 0.08 * n1)   # ragged edges (noise), as 065's ice is uneven
    dt = Y * (1 + 0.08 * n1)
    db = (H - Y) * (1 + 0.08 * n1)
    g = np.clip(np.abs(Y - 450.0) / 250.0, 0, 1) ** 1.5  # the side band deepens toward the top and bottom
    d0, d1 = 2.0 + 4.0 * g, 27.0 + 9.0 * g
    a_s = 0.88 * (1 - s3((dx - d0) / (d1 - d0)))
    a_t = np.maximum(0.94 * (1 - s3((dt - 45.0) / 55.0)), 0.25 * np.exp(-np.maximum(dt - 70.0, 0) / 28.0) * (dt > 70))
    a_b = np.maximum(0.97 * (1 - s3((db - 22.0) / 50.0)), 0.30 * np.exp(-np.maximum(db - 52.0, 0) / 18.0) * (db > 52))
    A = 1 - (1 - a_s) * (1 - a_t) * (1 - a_b)
    fine = K.noise2(cv.h, cv.w, 5, seed=29, octaves=2)      # 065's powdery grain inside the ice
    A = np.clip(A * (1 + 0.06 * streak + 0.04 * n2 + 0.05 * fine), 0, 0.97)
    w_cy = (a_t + a_b) / (a_s + a_t + a_b + 1e-6)
    core = rgb("#5AB8F4")[None, None, :] * (1 - w_cy[..., None]) + rgb("#4CDCF9")[None, None, :] * w_cy[..., None]
    fade = rgb("#6EA0F5")[None, None, :]
    k = np.clip(A / 0.85, 0, 1)[..., None] ** 1.2
    col = fade * (1 - k) + core * k
    # the light rim in the outer ~2 pt of every edge
    rim = np.maximum(np.maximum(np.exp(-(dx / 2.2) ** 2), np.exp(-(dt / 2.6) ** 2)), np.exp(-(db / 2.6) ** 2))
    col = col * (1 - 0.55 * rim[..., None]) + rgb("#A6F2FE")[None, None, :] * 0.55 * rim[..., None]
    A = A * (1 - 0.25 * rim)
    col = np.clip(col + 0.025 * streak[..., None], 0, 1)
    cv.a[..., :3] = col
    cv.a[..., 3] = A
    t = np.clip(A / 0.9, 0, 1)      # "in the ice" weight for the cracks and flakes below
    rng = np.random.default_rng(11)
    # ice cracks: branching random walks started in the frost band, drawn as thin white lines
    lines = np.zeros((cv.h, cv.w), np.float64)
    from PIL import ImageDraw
    lim = Image.new("L", (cv.w, cv.h), 0)
    dr = ImageDraw.Draw(lim)
    seeds = []
    for _ in range(26):             # to-A r4: 60 -> 26 seeds, fainter (065's cracks are few and thin)
        edge = rng.choice(["t", "b", "l", "r"], p=[0.3, 0.3, 0.2, 0.2])
        if edge == "t":
            p = (rng.uniform(0, W), rng.uniform(0, 30))
        elif edge == "b":
            p = (rng.uniform(0, W), H - rng.uniform(0, 30))
        elif edge == "l":
            p = (rng.uniform(0, 10), rng.uniform(0, H))
        else:
            p = (W - rng.uniform(0, 10), rng.uniform(0, H))
        seeds.append(p)
    for (x, y) in seeds:
        stack = [(x, y, rng.uniform(0, 2 * math.pi), 3)]
        while stack:
            x, y, ang, depth = stack.pop()
            n = int(rng.integers(3, 7))
            for _ in range(n):
                seg = rng.uniform(6, 16)
                ang += rng.uniform(-0.6, 0.6)
                nx, ny = x + seg * math.cos(ang), y + seg * math.sin(ang)
                ix, iy = int(np.clip(nx * 3, 0, cv.w - 1)), int(np.clip(ny * 3, 0, cv.h - 1))
                if t[iy, ix] < 0.45:
                    break
                dr.line([(x * 3, y * 3), (nx * 3, ny * 3)], fill=int(150 + 105 * t[iy, ix]), width=2)
                x, y = nx, ny
                if depth > 0 and rng.random() < 0.35:
                    stack.append((x, y, ang + rng.choice([-1, 1]) * rng.uniform(0.6, 1.2), depth - 1))
    lines = K.blur(np.asarray(lim).astype(np.float64) / 255, 0.6)
    cv.a[..., :3] = cv.a[..., :3] * (1 - lines[..., None] * 0.5) + lines[..., None] * 0.5
    cv.a[..., 3] = np.maximum(cv.a[..., 3], lines * 0.45 * np.clip(t * 2 - 0.6, 0, 1))
    # soft sparkles and tiny snowflakes in the cyan
    for _ in range(70):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        ix, iy = int(np.clip(x * 3, 0, cv.w - 1)), int(np.clip(y * 3, 0, cv.h - 1))
        if t[iy, ix] < 0.45:
            continue
        m = (np.abs(X - x) < 8) & (np.abs(Y - y) < 8)
        if not m.any():
            continue
        r = rng.uniform(0.8, 2.6)
        d = np.sqrt((X - x) ** 2 + (Y - y) ** 2)
        if rng.random() < 0.45:     # a tiny six-arm snowflake (3-6 pt)
            a = np.arctan2(Y - y, X - x)
            arm = np.exp(-((np.sin(3 * a) * d) / 0.30) ** 2) * np.clip(1 - d / (r * 1.6 + 1.2), 0, 1)
            g = np.clip(arm + np.exp(-(d / 0.6) ** 2), 0, 1) * 0.8
        else:                       # a soft bokeh sparkle
            g = np.exp(-(d / r) ** 2) * rng.uniform(0.35, 0.8)
        cv.a[..., :3] = cv.a[..., :3] * (1 - g[..., None]) + g[..., None]
        cv.a[..., 3] = np.maximum(cv.a[..., 3], g)
    return cv.image()


# heartBig is the missing-svg lane's (an SVG, shipped at art/ui/out/heartBig@3x.png); this 3D heart is a ROUTE CANDIDATE
# only: build/ui-art/route3d/heartBig.png, for the art director to compare (never written to art/ui/out)
BUILDS = {"heartBig3d": build_heart_big, "fxFrostVignette": lambda ctx: build_frost(ctx)}
DEST = {"heartBig3d": "route3d", "fxFrostVignette": "ui"}
