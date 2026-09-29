"""The chunky glossy 3D arrow (app icon, home capsule-machine pile, loading/win art), 3D route (art spike).

Measured on the store icon (research/store/icon-1024.png, looked at only): head height H = 403 px (1.0 unit), shaft
thickness 0.37 H, head length 0.79 H (back corners to tip), corner rounding ~0.09 H (tip, head back corners),
~0.035 H at the shaft-head junction; a thick soft bevel. Colours (k-means, share): yellow face #FEBF0E (69 %),
bevel shade #FB8A03 (15 %), dark rim #E46011 (7 %), highlights #FEC920 / #FED23B / #FDD561; red #FA3633 face,
#D4090B shade, #FC524E / #FC635F highlights; blue #0292FE face, #005FF1 shade, #0647CC rim, #1DA6FD / #42B7FC
highlights. Authored with the tip at the origin pointing +X, head height 1, +Z toward the viewer.
"""
from uikit import Part, extrude, gloss, polygon2, rounded_polygon2  # noqa: F401
from sdf import fillet_points, polygon2 as _poly2  # noqa: F401

VOXEL = 0.004
COLORS = {"yellow": "#FEBF0E", "red": "#FA3633", "blue": "#0292FE", "green": "#3CCB2A", "purple": "#B45CF0",
          "orange": "#FF8A1C", "cyan": "#2ED3F0"}


def arrow2d(shaft=1.2, t=0.185, hl=0.79):
    pts = [(0.0, 0.0), (-hl, 0.5), (-hl, t), (-hl - shaft, t), (-hl - shaft, -t), (-hl, -t), (-hl, -0.5)]
    radii = [0.085, 0.085, 0.035, 0.05, 0.05, 0.035, 0.085]
    return polygon2(fillet_points(pts, radii, n_arc=10))


# per colour: face, lower-bevel shade, lower rim, upper-bevel highlight (measured, see the docstring)
SHADES = {"yellow": ("#FEBF0E", "#FB8A03", "#E46011", "#FED23B"),
          "red": ("#FA3633", "#D4090B", "#A80508", "#FC635F"),
          "blue": ("#0292FE", "#005FF1", "#0647CC", "#42B7FC"),
          "green": ("#3CCB2A", "#1E9A12", "#157A0C", "#7CE36A"),
          "purple": ("#B45CF0", "#8A2FD6", "#6A1FB0", "#D19BFA"),
          "orange": ("#FF8A1C", "#F05A05", "#C84403", "#FFB45A"),
          "cyan": ("#2ED3F0", "#0FA2D8", "#0A7DB0", "#8AEBFA")}


def bevel_texture(s2, lo, size, color, band):
    """PAINTED bevel (the capture's shading shifts HUE toward a deeper saturated shade, which a grey-ish PBR falloff
    cannot do): texels within `band` of the 2D outline whose outward normal faces down-right take the measured shade
    and rim colours; those facing up-left take the highlight. Planar UV over the square world rect lo..lo+size."""
    import numpy as np
    from palette import _rgb
    face, shade, rim, hi = (np.asarray(_rgb(c)) for c in SHADES[color])
    down = np.array([0.30, -1.0]); down /= np.linalg.norm(down)

    def fn(u, v):
        H, W = u.shape
        p = np.stack([lo[0] + u * size, lo[1] + v * size], -1).reshape(-1, 2).astype(np.float32)
        d = s2.fn(p).astype(np.float64)
        e = size / W
        gx = (s2.fn(p + np.array([e, 0], np.float32)) - s2.fn(p - np.array([e, 0], np.float32))) / (2 * e)
        gy = (s2.fn(p + np.array([0, e], np.float32)) - s2.fn(p - np.array([0, e], np.float32))) / (2 * e)
        g = np.stack([gx, gy], 1); g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-6)
        facing = g @ down                                  # +1 lower-right edge, -1 upper-left edge
        t = np.clip((d + band) / band, 0, 1)               # 0 inside the flat face, 1 at the outline
        t = t * t * (3 - 2 * t)
        w_sh = t * np.clip(facing * 1.6 + 0.35, 0, 1)
        w_rim = np.clip((d + 0.25 * band) / (0.25 * band), 0, 1) * np.clip(facing * 1.6, 0, 1)
        w_hi = t * np.clip(-facing * 1.4 - 0.2, 0, 1) * 0.8
        col = face[None] * (1 - w_sh[:, None]) + shade[None] * w_sh[:, None]
        col = col * (1 - w_rim[:, None]) + rim[None] * w_rim[:, None]
        col = col * (1 - w_hi[:, None]) + hi[None] * w_hi[:, None]
        return col.reshape(H, W, 3)
    return fn


def arrow(color="yellow", shaft=1.2, depth=0.1, bevel=0.08):
    from dataclasses import replace
    s2 = arrow2d(shaft)
    body = extrude(s2, depth, round=bevel)
    lo = (-0.79 - shaft - 0.05, -0.55)
    size = 0.79 + shaft + 0.1
    m = gloss(f"arrow_{color}", SHADES[color][0], rough=0.30, ior=1.40)
    m = replace(m, texture=bevel_texture(s2, lo, size, color, band=0.11), texture_size=1024)
    uv = ("planar", (lo[0], lo[1], 0.0), (1, 0, 0), (0, 1, 0), 1.0 / size)
    return [Part("arrow", body, m, uv=uv)], VOXEL


MODELS = {f"arrow_{c}": (lambda c=c: arrow(c)) for c in COLORS}
MODELS.update({f"arrowShort_{c}": (lambda c=c: arrow(c, shaft=0.55)) for c in COLORS})

# the icon look is bright and evenly lit: a strong neutral fill from below keeps the painted lower bevel saturated
# (under the default UI rig it went olive-brown), ambient up a little
ARROW_LIGHT = dict(fill_lux=900.0, fill_color=(1.0, 0.97, 0.94), fill_dir=(0.1, 0.8, -0.6), ibl_exp=-0.85, key_lux=2100.0)

ASSETS = {
    # the icon's yellow arrow, long shaft (cropped by the comparison to the icon window)
    "arrowIconYellow_3d": dict(model="arrow_yellow", yaw=0, pitch=-14, frame=(200, 100), fill=0.98, fov=12, light=ARROW_LIGHT, dest="route3d"),
    "arrowIconRed_3d": dict(model="arrow_red", yaw=180, pitch=-14, frame=(200, 100), fill=0.98, fov=12, light=ARROW_LIGHT, dest="route3d"),
    "arrowIconBlue_3d": dict(model="arrow_blue", yaw=0, pitch=-14, frame=(200, 100), fill=0.98, fov=12, light=ARROW_LIGHT, dest="route3d"),
}
