"""Shared materials + procedural textures. Colours are sRGB hex measured from the
reference captures (lit side of each surface), see art/STYLE.md."""
from __future__ import annotations

import numpy as np

from mesher import Material, hex_to_rgb


def _rgb(h):
    return np.array(hex_to_rgb(h))


def streaks(base, dark, light=None, n_lines=40, strength=0.35, seed=0, axis="u"):
    """Painted-wood grain: thin lines running along v (so they vary with u).
    Returns fn(u, v) -> (H, W, 3) sRGB."""
    b = _rgb(base); d = _rgb(dark); li = _rgb(light) if light else b
    rng = np.random.default_rng(seed)
    pos = np.sort(rng.uniform(0, 1, n_lines))
    width = rng.uniform(0.002, 0.008, n_lines)
    amp = rng.uniform(0.3, 1.0, n_lines)
    phase = rng.uniform(0, 6.28, n_lines)

    def fn(u, v):
        t = u if axis == "u" else v
        s = v if axis == "u" else u
        g = np.zeros_like(t)
        for p, w, a, ph in zip(pos, width, amp, phase):
            # lines wobble slightly along their length
            c = p + 0.004 * np.sin(s * 6.28 * 2 + ph)
            dd = np.abs(((t - c + 0.5) % 1.0) - 0.5)
            g = np.maximum(g, a * np.clip(1 - dd / w, 0, 1))
        # broad low-frequency variation
        lo = 0.5 + 0.5 * np.sin(t * 6.28 * 3 + 1.3) * np.sin(t * 6.28 * 7 + 0.4)
        col = b[None, None, :] * (1 - g[..., None] * strength) + d[None, None, :] * (g[..., None] * strength)
        col = col * (1 - 0.06 * lo[..., None]) + li[None, None, :] * (0.06 * lo[..., None])
        return col
    return fn


def decal(base, shapes, world_lo, world_hi, edge_dark=0.0, edge_width=0.004, aa=1.0):
    """Planar decal texture. `shapes` = [(SDF2, hex), ...] drawn in order over `base`.
    UV (0,0)-(1,1) maps to world rectangle world_lo..world_hi (2D, in the projection plane)."""
    b = _rgb(base)
    lo = np.asarray(world_lo, float); hi = np.asarray(world_hi, float)

    def fn(u, v):
        H, W = u.shape
        texel = (hi[0] - lo[0]) / W
        p = np.stack([lo[0] + u * (hi[0] - lo[0]), lo[1] + v * (hi[1] - lo[1])], -1).reshape(-1, 2).astype(np.float32)
        col = np.broadcast_to(b, (H * W, 3)).copy()
        for s2, hexc in shapes:
            c = _rgb(hexc)
            d = np.asarray(s2(p), float)
            a = np.clip(0.5 - d / (aa * texel), 0, 1)[:, None]
            cc = np.broadcast_to(c, col.shape).copy()
            if edge_dark > 0:
                e = np.clip(1 - np.abs(d + edge_width * 0.5) / (edge_width * 0.5), 0, 1) * (d < 0)
                cc = cc * (1 - edge_dark * e[:, None])
            col = col * (1 - a) + cc * a
        return col.reshape(H, W, 3)
    return fn


# ---- toy hammer
HAMMER_CREAM = Material("hammer_cream", "#F3E3AE", roughness=0.55, clearcoat=0.0)
HAMMER_BLUE = Material("hammer_blue", "#1D82CF", roughness=0.5, clearcoat=0.0,
                       texture=streaks("#1D82CF", "#15609F", "#3A9BE0", n_lines=34, strength=0.22, seed=3), texture_size=256)
HAMMER_RED = Material("hammer_red", "#E2290C", roughness=0.5, clearcoat=0.0)
HAMMER_HANDLE = Material("hammer_handle", "#EC4C24", roughness=0.55, clearcoat=0.0,
                         texture=streaks("#EC4C24", "#B5371A", "#F46A40", n_lines=46, strength=0.6, seed=7), texture_size=256)
HAMMER_STAR = Material("hammer_star", "#F4461F", roughness=0.55)

# ---- rubber duck
DUCK_YELLOW = Material("duck_yellow", "#FFAE00", roughness=0.42, ior=1.12)
DUCK_BEAK = Material("duck_beak", "#F25A06", roughness=0.45, clearcoat=0.0)
DUCK_MOUTH = Material("duck_mouth", "#B8360A", roughness=0.5)
DUCK_EYE = Material("duck_eye", "#120D0A", roughness=0.18, ior=1.5)

# ---- strawberry
STRAW_RED = Material("straw_red", "#F5233B", roughness=0.45, clearcoat=0.0)
STRAW_SEED = Material("straw_seed", "#F09A26", roughness=0.45, clearcoat=0.1)
STRAW_GREEN = Material("straw_green", "#4A9A0C", roughness=0.5, clearcoat=0.0)
STRAW_STEM = Material("straw_stem", "#56A812", roughness=0.5, clearcoat=0.0)


# =====================================================================================
# Shared material FAMILIES for the modelling lanes (do not edit per item: call a preset).
#
#   from palette import preset, glossy_plastic, satin_rubber, matte_food, ...
#   BALL = glossy_plastic("bowling_blue", "#1F4FC8", texture=marble("#1F4FC8", "#5E8CF0"))
#   M    = preset("paper", "cup_white", "#F4F1EA", roughness=0.7)   # any field can be overridden
#
# Values follow STYLE.md: low specular (USD ior -> RealityKit specular: 1.1 -> 0.03, 1.2 -> 0.1,
# 1.3 -> 0.2, 1.5 -> 0.5), no clearcoat (it veils the colours), albedo = the capture's LIT colour.
# The "metals" are NOT mirror metals: the original's gold and silver are satin coloured plastics
# with a soft highlight (a metallic-1 surface under the dim item IBL renders nearly black), so they
# stay (almost) dielectric: a bright diffuse base + a broad soft highlight (metallic 0.3 went olive/grey).
# Calibrated on spheres with the game rig: art/previews/material_presets.png (items/_materials.py).
# =====================================================================================

FAMILIES = {
    # family:          (roughness, ior, metallic, opacity, typical use)
    "glossy_plastic": dict(roughness=0.4, ior=1.3, metallic=0.0, note="toy plastic with a visible highlight: bowling balls, balloons, gamepad"),
    "satin_plastic": dict(roughness=0.5, ior=1.2, metallic=0.0, note="default toy plastic: hammer, drum, keyboard, robot"),
    "satin_rubber": dict(roughness=0.44, ior=1.12, metallic=0.0, note="rubber duck, squeaky toys, tyres (dark)"),
    "fruit_skin": dict(roughness=0.4, ior=1.28, metallic=0.0, note="glossy fruit/veg: apple, cherry, tomato, chili, pepper"),
    "matte_food": dict(roughness=0.62, ior=1.12, metallic=0.0, note="banana, pear, carrot, egg, avocado flesh, cheese, patty"),
    "glaze": dict(roughness=0.34, ior=1.32, metallic=0.0, note="icing, chocolate spread, yolk, jam, candy"),
    "bread": dict(roughness=0.72, ior=1.08, metallic=0.0, note="bun, crust, croissant, cookie, waffle, cone (use speckle())"),
    "fabric": dict(roughness=0.9, ior=1.04, metallic=0.0, note="cushions, knit, felt, tennis-ball fuzz (use knit()/speckle())"),
    "paper": dict(roughness=0.74, ior=1.1, metallic=0.0, note="cups, cartons, liners, labels, book pages"),
    "leather": dict(roughness=0.58, ior=1.15, metallic=0.0, note="books, footballs, bags"),
    "wood": dict(roughness=0.6, ior=1.12, metallic=0.0, note="painted or bare wood (use streaks())"),
    "metal_gold": dict(roughness=0.42, ior=1.35, metallic=0.05, note="the 'gold' instruments: warm satin yellow-orange, soft broad highlight"),
    "chrome": dict(roughness=0.4, ior=1.4, metallic=0.05, note="silver/chrome parts: light cool grey, soft highlight (mic mesh, ferrules, blades)"),
    "glass_ice": dict(roughness=0.3, ior=1.33, metallic=0.0, opacity=0.9, note="ice cube, glass: pale, mostly opaque (use frost())"),
}

# suggested base colours per family (sRGB, measured lit colours where a capture exists)
FAMILY_COLOURS = {
    "metal_gold": "#F7B928",  # gold-trumpet/bell lit side
    "chrome": "#D5D8E2",      # disco-ball tiles / headphone sliders lit side
    "glass_ice": "#8FD8EE",   # ice-cube lit face
    "bread": "#D98A3A",       # bun/crust
    "paper": "#F2EFE8",
}


def preset(family, name, color=None, **overrides):
    """Material from a family preset; any Material field can be overridden."""
    f = dict(FAMILIES[family]); f.pop("note", None)
    f.update(overrides)
    return Material(name, color or FAMILY_COLOURS.get(family, "#808080"), **f)


def glossy_plastic(name, color, **kw): return preset("glossy_plastic", name, color, **kw)
def satin_plastic(name, color, **kw): return preset("satin_plastic", name, color, **kw)
def satin_rubber(name, color, **kw): return preset("satin_rubber", name, color, **kw)
def fruit_skin(name, color, **kw): return preset("fruit_skin", name, color, **kw)
def matte_food(name, color, **kw): return preset("matte_food", name, color, **kw)
def glaze(name, color, **kw): return preset("glaze", name, color, **kw)
def bread(name, color=None, **kw): return preset("bread", name, color, **kw)
def fabric(name, color, **kw): return preset("fabric", name, color, **kw)
def paper(name, color=None, **kw): return preset("paper", name, color, **kw)
def leather(name, color, **kw): return preset("leather", name, color, **kw)
def wood(name, color, **kw): return preset("wood", name, color, **kw)
def metal_gold(name="gold", color=None, **kw): return preset("metal_gold", name, color, **kw)
def chrome(name="chrome", color=None, **kw): return preset("chrome", name, color, **kw)
def glass_ice(name="ice", color=None, **kw): return preset("glass_ice", name, color, **kw)


# the engine's hint/tap outline colour (research/motion.md 13.4); used by <item>.outline.usdz
OUTLINE_LIME = Material("outline_lime", "#E0F800", roughness=1.0, ior=1.0, emissive="#E0F800")


# ---- more procedural textures: all return fn(u, v) -> (H, W, 3) sRGB in [0, 1]

def _noise2(u, v, freq, seed):
    """Tileable smooth value noise on the unit square (periodic in u and v)."""
    rng = np.random.default_rng(seed)
    n = int(freq)
    g = rng.uniform(0, 1, (n, n))
    x = u * n; y = v * n
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = x - x0; fy = y - y0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = g[y0 % n, x0 % n]; b = g[y0 % n, (x0 + 1) % n]; c = g[(y0 + 1) % n, x0 % n]; d = g[(y0 + 1) % n, (x0 + 1) % n]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm2(u, v, freq=4, octaves=4, seed=0):
    s, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + amp * _noise2(u, v, freq * 2 ** o, seed + o)
        tot += amp; amp *= 0.5
    return s / tot


def marble(base, vein, dark=None, scale=2, warp=2.6, width=0.32, seed=0):
    """Swirled marble (bowling balls): soft light veins over the base colour."""
    b = _rgb(base); c = _rgb(vein); dk = _rgb(dark) if dark else b * 0.8

    def fn(u, v):
        w = fbm2(u, v, freq=scale, octaves=4, seed=seed)
        t = np.sin((u * 2 + v + warp * w) * 2 * np.pi * scale / 2)
        vein_a = np.clip(1 - np.abs(t) / width, 0, 1) ** 1.5
        shade = fbm2(u, v, freq=scale * 2, octaves=2, seed=seed + 7)
        col = b[None, None] * (1 - 0.25 * shade[..., None]) + dk[None, None] * (0.25 * shade[..., None])
        return col * (1 - vein_a[..., None]) + c[None, None] * vein_a[..., None]
    return fn


def speckle(base, dark, light=None, density=0.05, size=3.0, variation=0.12, seed=0):
    """Baked/fuzzy surfaces: low-frequency tone variation + sparse dark (and light) specks
    (bread crust, cookie, tennis-ball fuzz, basketball pebbling with size ~1)."""
    b = _rgb(base); d = _rgb(dark); li = _rgb(light) if light else b

    def fn(u, v):
        H, W = u.shape
        tone = fbm2(u, v, freq=4, octaves=3, seed=seed) - 0.5
        rng = np.random.default_rng(seed + 1)
        spk = (rng.uniform(0, 1, (H, W)) < density).astype(float)
        from scipy.ndimage import gaussian_filter
        spk = np.clip(gaussian_filter(spk, size / 3, mode="wrap") * (size ** 1.2), 0, 1)
        lit = (rng.uniform(0, 1, (H, W)) < density * 0.5).astype(float)
        lit = np.clip(gaussian_filter(lit, size / 3, mode="wrap") * (size ** 1.2), 0, 1)
        col = b[None, None] * (1 + variation * 2 * tone[..., None])
        col = col * (1 - 0.6 * spk[..., None]) + d[None, None] * (0.6 * spk[..., None])
        return col * (1 - 0.4 * lit[..., None]) + li[None, None] * (0.4 * lit[..., None])
    return fn


def stripes(colors, n=6, axis="u", slant=0.0, soft=0.004):
    """Repeating bands of `colors` (hex list), n repeats across [0,1) of `axis` (candy stripes with slant != 0)."""
    cs = [_rgb(c) for c in colors]

    def fn(u, v):
        t = (u if axis == "u" else v) + slant * (v if axis == "u" else u)
        x = (t * n) % 1.0 * len(cs)
        col = np.zeros(u.shape + (3,))
        for i, c in enumerate(cs):
            d = np.minimum(np.abs(x - i - 0.5), len(cs) - np.abs(x - i - 0.5))  # circular distance to band centre
            a = np.clip((0.5 - d) / (soft * n * len(cs)) + 0.5, 0, 1)
            col = col + a[..., None] * c[None, None]
        return col
    return fn


def tiled_motif(base, motif, color, cells=(4, 4), stagger=True, scale=0.36, rotation_jitter=0.0, seed=0):
    """A printed pattern (gift wraps: stars, dots, trees, snowflakes): `motif` = SDF2 authored in a unit
    cell (-0.5..0.5), drawn in `color` on `base`, `cells` repeats in (u, v), rows staggered by half a cell."""
    b = _rgb(base); c = _rgb(color)
    rng = np.random.default_rng(seed)

    def fn(u, v):
        H, W = u.shape
        cu, cv = cells
        y = v * cv
        row = np.floor(y)
        x = u * cu + (0.5 * (row % 2) if stagger else 0)
        px = (x % 1.0) - 0.5; py = (y % 1.0) - 0.5
        p = np.stack([px.reshape(-1) / scale, py.reshape(-1) / scale], 1).astype(np.float32)
        d = np.asarray(motif(p), float).reshape(H, W) * scale
        texel = 1.0 / (W / cu)
        a = np.clip(0.5 - d / texel, 0, 1)
        return b[None, None] * (1 - a[..., None]) + c[None, None] * a[..., None]
    return fn


def knit(base, dark, rows=24, cols=16):
    """Knitted/fabric cushion (stool seat): V-shaped stitches."""
    b = _rgb(base); d = _rgb(dark)

    def fn(u, v):
        x = (u * cols) % 1.0; y = (v * rows) % 1.0
        vshape = np.abs(np.abs(x - 0.5) * 2 - (y * 0.9 + 0.05))
        g = np.clip(1 - vshape / 0.35, 0, 1)[..., None]
        return b[None, None] * (0.8 + 0.2 * g) * (1 - 0.3 * (1 - g)) + d[None, None] * (0.3 * (1 - g))
    return fn


def frost(base, white="#F4FBFF", amount=0.8, seed=0):
    """Ice: pale base with white frosty streaks and cloudy patches."""
    b = _rgb(base); w = _rgb(white)

    def fn(u, v):
        cloud = fbm2(u, v, freq=3, octaves=4, seed=seed)
        streak = np.clip(1 - np.abs(np.sin((u * 3 + v * 1.3 + 0.8 * cloud) * 2 * np.pi * 3)) / 0.08, 0, 1)
        a = np.clip((cloud - 0.45) * 1.6, 0, 1) * amount + streak * 0.35
        return b[None, None] * (1 - a[..., None]) + w[None, None] * a[..., None]
    return fn
