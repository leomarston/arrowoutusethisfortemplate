"""D1 "Burrow Works" board skin (PLAN-P R7 BOARD-UI; SPEC.md rulings 38, 44, 46).

Ruling 46 (owner, "minimum sufficient distance"): the board obstacles keep their SHAPES, sizes, anchors, shading structure
and readability; only materials / colours / small details change, just enough to be our own. So every board sprite is
still drawn by its measured generator (gen_board.py, gen_icons.py, gen_missing.py, corner.py) and this module recolours
its output per MATERIAL: each source colour keeps its CIELAB L* (optionally re-graded) and its chroma relative to its
family, and takes the D1 material's hue. Geometry (and so the hit areas, anchors and alpha bboxes) cannot change.

Materials (art-direction.md §3.1 palette; the owner approved the D1 palette on 2026-09-28 06:17, ruling 44):
  tape   pink canvas            -> TEAL webbing        (D1 chrome #17B3A3 family)
  door   orange frame           -> HONEY TIMBER        (timber #E0A862 / #B97A3E / #7E4E27)
         purple inner frame     -> IRON                (rock #4E7F86 / #2E5961, darkened)
         blue slatted shutter   -> TEAL-PAINTED PLANKS (the boss coat teal #2E8C8A family)
         gold rivets            -> IRON BOLTS
  lock   purple hex, blue socket-> BRASS hex in an IRON socket
  key    gold key               -> gold (generic, kept: DoorLayer.withoutRibbon keeps only r>=g>=b+25 pixels)
         purple ribbon          -> TEAL tag ribbon (fails the gold test by construction, so the flying key drops it)
  pipe   cyan glass tube        -> COPPER (art-direction §3.1: copper #D9824A / highlight #FFC39A)
         gold collars           -> IRON collars;  orange counter -> TEAL plate (live white number)
  box    violet slab            -> SLATE STONE         (rock #6E9FA5 / #4E7F86 / #2E5961 / #1B3A40)
         purple ring, navy well -> BRASS ring, deep teal well; the steel sphere stays steel (generic)
  corner red plate, blue spring -> MINT bumper on a BRASS coil (corner.py, 3-D)
  elevator lavender platform    -> SAND planks (pale timber)
  exit colour / vacated dots    -> tangerine #FF8F1F / #FFDDB0 (board.json color.exit / color.dot)

API:
  remap(hex, fam)                 one colour through a Material
  recolour(svg, rules)            every #RRGGBB in an SVG text through `rules(hex) -> hex`
  rules_for(kind)                 the per-sprite rule (source hue windows -> materials, plus exact overrides)
"""
from __future__ import annotations

import math
import re

# ------------------------------------------------------------------------------------------------ colour maths (D65)


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    v = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return v * 255.0


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, int(round(v)))):02X}" for v in rgb)


_XN, _YN, _ZN = 0.95047, 1.0, 1.08883


def _f(t):
    return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116


def _finv(t):
    return t ** 3 if t ** 3 > 216 / 24389 else (116 * t - 16) / (24389 / 27)


def rgb_lab(rgb):
    r, g, b = (_lin(v) for v in rgb)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    fx, fy, fz = _f(x / _XN), _f(y / _YN), _f(z / _ZN)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def lab_rgb(L, a, b):
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200
    x, y, z = _finv(fx) * _XN, _finv(fy) * _YN, _finv(fz) * _ZN
    r = 3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    g = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    bb = 0.0556434 * x - 0.2040259 * y + 1.0572252 * z
    return tuple(_gam(v) if v > 0 else 12.92 * v * 255 for v in (r, g, bb))


def lch(hex_):
    L, a, b = rgb_lab(hex_rgb(hex_))
    return L, math.hypot(a, b), (math.degrees(math.atan2(b, a)) + 360) % 360


def _in_gamut(rgb):
    return all(-0.5 <= v <= 255.5 for v in rgb)


def from_lch(L, C, h):
    """LCh -> hex; chroma is reduced (hue and L* kept) until the colour is inside sRGB."""
    L = max(0.0, min(100.0, L))
    for _ in range(60):
        rgb = lab_rgb(L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h)))
        if _in_gamut(rgb):
            return rgb_hex(rgb)
        C *= 0.95
    return rgb_hex(lab_rgb(L, 0, 0))


def de00(h1, h2):
    """CIEDE2000 between two hex colours."""
    L1, a1, b1 = rgb_lab(hex_rgb(h1))
    L2, a2, b2 = rgb_lab(hex_rgb(h2))
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2p - h1p if abs(h2p - h1p) <= 180 else h2p - h1p - 360 * math.copysign(1, h2p - h1p))
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lb, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hb = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hb = (h1p + h2p) / 2
    else:
        hb = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hb - 30)) + 0.24 * math.cos(math.radians(2 * hb))
         + 0.32 * math.cos(math.radians(3 * hb + 6)) - 0.20 * math.cos(math.radians(4 * hb - 63)))
    Sl = 1 + 0.015 * (Lb - 50) ** 2 / math.sqrt(20 + (Lb - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hb - 275) / 25) ** 2)))
    return math.sqrt((dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh))


# ------------------------------------------------------------------------------------------------ materials


class Material:
    """A D1 material ladder: hue(L*) and chroma(L*) interpolated from anchor colours (light -> dark), so a source
    gradient (same hue, L* 90 -> 30) becomes the material's own gradient (e.g. honey -> walnut) at the same L*.
    `ck` scales the source chroma relative to the source family's reference chroma `c_ref` (keeps a gradient's
    saturation structure); `l_gain`/`l_off` re-grade L* (L' = l_off + l_gain * L) when a material must sit lighter or
    darker than the source (e.g. iron is darker than the purple it replaces)."""

    def __init__(self, name, anchors, c_ref=None, ck=1.0, l_gain=1.0, l_off=0.0, c_max=None):
        self.name = name
        pts = sorted((lch(h) for h in anchors), key=lambda t: t[0])
        self.pts = pts
        self.c_ref = c_ref
        self.ck = ck
        self.l_gain, self.l_off = l_gain, l_off
        self.c_max = c_max

    def at(self, L):
        p = self.pts
        if L <= p[0][0]:
            return p[0][1], p[0][2]
        if L >= p[-1][0]:
            return p[-1][1], p[-1][2]
        for (L0, C0, h0), (L1, C1, h1) in zip(p, p[1:]):
            if L0 <= L <= L1:
                t = (L - L0) / max(1e-9, L1 - L0)
                dh = ((h1 - h0 + 180) % 360) - 180
                return C0 + t * (C1 - C0), (h0 + t * dh) % 360
        return p[-1][1], p[-1][2]

    def map(self, hex_):
        L, C, h = lch(hex_)
        L2 = max(0.0, min(100.0, self.l_off + self.l_gain * L))
        Ct, ht = self.at(L2)
        if self.c_ref:                                   # keep the colour's saturation relative to its family
            Ct = Ct * (C / self.c_ref) ** 0.5 * self.ck
        else:
            Ct *= self.ck
        if self.c_max is not None:
            Ct = min(Ct, self.c_max)
        return from_lch(L2, Ct, ht)


M = {
    # teal webbing: D1 chrome ladder (#7FEADB light edge, #17B3A3 face, #0B8A83 rim, #075E5E, #053F43)
    "teal": Material("teal", ["#C9FBF2", "#7FEADB", "#2CC4B2", "#17B3A3", "#0B8A83", "#075E5E", "#053F43"], c_ref=62),
    # honey timber (frame): D1 timber #E0A862 / #B97A3E / #7E4E27 + a light plank edge and a dark walnut
    "timber": Material("timber", ["#FFF1CF", "#F6CF8C", "#E0A862", "#C98A48", "#B97A3E", "#7E4E27", "#4A2A12", "#2A160A"],
                       c_ref=75),
    # iron trim (the door's inner frame, collars, bolts): a cool teal-grey from D1 rock, darkened and desaturated
    "iron": Material("iron", ["#E4ECEC", "#A9BBBE", "#6E8286", "#4F6166", "#39484C", "#252F32", "#141A1C"], c_ref=60,
                     l_gain=0.80, l_off=4.0, c_max=12),
    # teal-painted planks (the shutter): boss-coat teal #2E8C8A / #1F6B6B / #144C4E, lighter paint on the lit edge
    "plank": Material("plank", ["#CDEDE6", "#86CFC4", "#4FAFA6", "#2E8C8A", "#1F6B6B", "#144C4E", "#0B2F31"], c_ref=48,
                      l_gain=0.86),
    # brass (lock, box ring): D1 buttons #E3B04B, lantern #FFCF6B, dark #7A4E14
    "brass": Material("brass", ["#FFF4CF", "#FFE08A", "#F2C45A", "#E3B04B", "#C98E3E", "#9E6A24", "#6A420F", "#3A2408"],
                      c_ref=55),
    # copper glass tube (pipe): #FFC39A highlight, #D9824A base, darker oxide browns
    "copper": Material("copper", ["#FFE3CC", "#FFC39A", "#F0A06A", "#D9824A", "#B8622E", "#8E4520", "#5E2A12"], c_ref=45),
    # slate stone (box): D1 rock ladder #A8CFD2 / #6E9FA5 / #4E7F86 / #2E5961 / #1B3A40
    "slate": Material("slate", ["#E1F0F0", "#A8CFD2", "#7FAAB0", "#6E9FA5", "#4E7F86", "#2E5961", "#1B3A40", "#0F2226"],
                      c_ref=70),
    # deep teal well / digit outline
    "well": Material("well", ["#2E6E70", "#17474A", "#0B2E33", "#061C20"], c_ref=40),
    # sand planks (elevator platform)
    "sand": Material("sand", ["#FFF6E4", "#F3E0BC", "#E6C996", "#D9B67E", "#B98A52", "#8A6034"], c_ref=35),
    # tangerine (exit colour arrows in card art, pointers): D1 CTA #FFE08A / #FFB422 / #FF9A12 / #D06A06 / #9E4A00 / #6B2E00
    "tangerine": Material("tangerine", ["#FFF0C8", "#FFE08A", "#FFB422", "#FF9A12", "#FF8F1F", "#D06A06", "#9E4A00", "#6B2E00"],
                          c_ref=70),
    # mint (corner bumper): crew mint fur ladder
    "mint": Material("mint", ["#E2FFF5", "#B6F5E2", "#7FE3C3", "#4CCBA5", "#2FA888", "#1C8068", "#115C4C", "#0A3A30"], c_ref=70),
    # cream glove (the tutorial hand)
    "cream": Material("cream", ["#FFFFFF", "#FFFBF0", "#FFF3DF", "#F3E3C6", "#E2CCA6", "#C7A87C", "#8C6A44"], c_ref=70,
                      c_max=26),
}


def remap(hex_, fam):
    return (M[fam] if isinstance(fam, str) else fam).map(hex_)


# ------------------------------------------------------------------------------------------------ SVG recolouring

HEX = re.compile(r"#([0-9A-Fa-f]{6})\b")


def recolour(svg, rule):
    """Every #RRGGBB token through rule(hex) -> hex (None = unchanged). Memoised per call."""
    memo = {}

    def sub(m):
        h = "#" + m.group(1).upper()
        if h not in memo:
            r = rule(h)
            memo[h] = r or h
        return memo[h]
    return HEX.sub(sub, svg)


# Source hue windows (CIELAB hue of the measured generator colours):
#   pink/magenta 340-20 · orange/gold 45-100 · purple/violet 285-345 · blue/cyan 215-285 · red-orange 20-45
KEEP = "keep"
# tuned after the round-1 sheet (build/p/R7/sheets/d1_r1_*.png): the tape a touch lighter than the pink it replaces,
# the lock a richer brass, the box a MOSS stone (slate read dull and sat too close to the teal tape it shares 5 levels
# with), copper deeper, the card arrows / pointers a vivid tangerine, the tutorial hand a mint Digger glove (a cream
# glove vanished on the white board)
M["teal_tape"] = Material("teal_tape", ["#C9FBF2", "#7FEADB", "#2CC4B2", "#17B3A3", "#0B8A83", "#075E5E", "#053F43"],
                          c_ref=62, l_off=7.0, l_gain=1.0, ck=1.08)
M["moss"] = Material("moss", ["#EEF8D8", "#CDEA9C", "#A8D56C", "#86C04E", "#6A9E38", "#4E7A26", "#34561A", "#1E3410"],
                     c_ref=80, ck=0.95)
M["copper"] = Material("copper", ["#FFE3CC", "#FFC39A", "#F0A06A", "#D9824A", "#B8622E", "#8E4520", "#5E2A12"], c_ref=40,
                       l_gain=0.86, l_off=2.0, ck=1.15)
M["tangerine_arrow"] = Material("tangerine_arrow", ["#FFF0C8", "#FFE08A", "#FFB422", "#FF9A12", "#FF8F1F", "#D06A06", "#9E4A00",
                                                    "#6B2E00"], c_ref=70, l_off=18.0, l_gain=0.84, ck=1.1)
M["tangerine_ptr"] = Material("tangerine_ptr", ["#FFF0C8", "#FFE08A", "#FFB422", "#FF9A12", "#FF8F1F", "#D06A06", "#9E4A00",
                                                "#6B2E00"], c_ref=70, l_gain=0.84, ck=1.3)
M["mint_glove"] = Material("mint_glove", ["#E2FFF5", "#B6F5E2", "#7FE3C3", "#4CCBA5", "#2FA888", "#1C8068", "#115C4C"],
                           c_ref=70, l_gain=0.92, ck=1.0)
M["brass_lock"] = Material("brass_lock", ["#FFF4CF", "#FFE08A", "#F6C84E", "#E9B23C", "#CF9230", "#A56E1C", "#6A420F",
                                          "#3A2408"], c_ref=70, l_gain=1.10, l_off=6.0, ck=1.2)
M["mint_plate"] = Material("mint_plate", ["#E2FFF5", "#B6F5E2", "#7FE3C3", "#4CCBA5", "#2FA888", "#1C8068", "#115C4C"],
                           c_ref=80, l_gain=0.78, l_off=22.0)
M["brass_coil"] = Material("brass_coil", ["#FFF4CF", "#FFE08A", "#F2C45A", "#E3B04B", "#C98E3E", "#9E6A24", "#6A420F",
                                          "#3A2408"], c_ref=30, ck=1.0)


def hue_rule(windows, overrides=None, neutral_c=8.0):
    """windows: [(h0, h1, material), ...] in CIELAB hue degrees (h0 > h1 wraps through 0); colours with C* below
    `neutral_c` (shadows, whites, greys) are kept; `overrides` = {hex: hex | material | KEEP} win over the windows."""
    ov = {k.upper(): v for k, v in (overrides or {}).items()}

    def rule(h):
        if h in ov:
            v = ov[h]
            if v == KEEP:
                return None
            return v if v.startswith("#") else remap(h, v)
        L, C, hh = lch(h)
        if C < neutral_c:
            return None
        for h0, h1, fam in windows:
            inside = (h0 <= hh < h1) if h0 <= h1 else (hh >= h0 or hh < h1)
            if inside:
                return remap(h, fam)
        return None
    return rule


def exact_rule(table):
    """{hex: material | hex | KEEP}: only these colours change (composites whose other parts are already D1)."""
    return hue_rule([], table, neutral_c=1e9)


def set_rule(hexes, fam):
    return exact_rule({h: fam for h in hexes})


# ---- the steel sphere of the box ring (a blue-grey in the measured art): cool neutral steel, L* kept
def steel(h, c_max=5.0):
    L, C, hh = lch(h)
    return from_lch(L, min(C, c_max), 205.0)


def _box_family(h, ring=(), well=(), slate=()):
    """Box / crate / box icon: ring purples -> brass, navy -> deep teal well, blue-grey sphere + lugs -> steel,
    violet slab -> slate stone. `ring`/`well`/`slate` = exact hex sets for the colours the windows cannot tell apart."""
    if h in ring:
        return remap(h, "brass_lock")
    if h in well:
        return remap(h, "well")
    if h in slate:
        return remap(h, "moss")
    L, C, hh = lch(h)
    if C < 8:
        return None
    if 268 <= hh < 300 and L < 36:
        return remap(h, "well")
    if 255 <= hh < 310 and C < 47:
        return steel(h)
    if 285 <= hh < 345:
        return remap(h, "moss")
    return None


RING_SETS = dict(
    boxRing=dict(ring={"#C698FF", "#A270E8", "#6A52BC", "#4C3AA0", "#433595"}, well={"#6C9AD6"}),
    crate=dict(ring={"#C698FF", "#A270E8", "#6A52BC", "#4C3AA0", "#433595"}, well={"#6C86D6", "#24468A"},
               slate={"#3A2466", "#3E2C68", "#2A1A48"}),
    boxIcon=dict(ring={"#9A5AF0", "#7A3CCB", "#D3A8FC"},
                 well={"#2A5FA2", "#245595", "#18427A", "#0D3363", "#082650"},
                 slate={"#3C196D", "#4E2E87", "#5A2A92", "#5A3196", "#5E3399"}),
)


def box_rule(which):
    sets = {k: {x.upper() for x in v} for k, v in RING_SETS.get(which, {}).items()}
    return lambda h: _box_family(h, **sets)


DOOR_RIVETS = {"#FFFFF1": "#FFFFFF", "#FFF48A": "iron", "#FFD23A": "iron", "#FFAE14": "iron", "#EF8E0B": "iron",
               "#983A00": "#2A3336"}

RULES = {
    # the tape: pink -> teal webbing (its grey drop shadow stays)
    "tape": lambda: hue_rule([(330, 30, "teal_tape"), (285, 330, "teal_tape")], {"#2A2A3A": KEEP}),
    # the door: orange frame -> teal-painted wood, purple inner frame -> iron, blue shutter -> honey timber planks,
    # gold rivets -> iron bolts, the dark outline -> a teal-black
    "door": lambda: hue_rule([(35, 100, "plank"), (285, 345, "iron"), (215, 285, "timber")],
                             dict(DOOR_RIVETS, **{"#3A0E06": "#0E2426"})),
    # door shards: the same three materials
    "doorShards": lambda: hue_rule([(35, 100, "plank"), (285, 345, "iron"), (215, 285, "timber")]),
    # the hex lock: purple -> brass, its blue socket -> iron
    "lock": lambda: hue_rule([(285, 345, "brass_lock"), (215, 285, "iron")]),
    # the key: gold kept (generic; DoorLayer.withoutRibbon keeps only r>=g>=b+25 pixels); the purple ribbon -> teal
    "key": lambda: hue_rule([(285, 345, "teal")]),
    # pipe mouth: gold collar -> iron; the orange opening -> a dark copper interior
    "pipeMouth": lambda: hue_rule([(60, 105, "iron")],
                                  {"#6E2D01": "#2B1A10", "#A94E01": "#5E2A12", "#E98001": "#8E4520", "#C06A06": "iron"}),
    # pipe counter: gold frame + collars -> iron; the red-orange face -> a teal plate (white live digits)
    "pipeCounter": lambda: hue_rule([(40, 60, "plank"), (60, 105, "iron")]),
    # the cyan glass (pipe tube in card art, pipe shards) -> copper
    "glass": lambda: hue_rule([(215, 285, "copper")]),
    "boxSlab": lambda: hue_rule([(285, 345, "moss")]),
    "boxRing": lambda: box_rule("boxRing"),
    "crate": lambda: box_rule("crate"),
    "boxIcon": lambda: box_rule("boxIcon"),
    "elevator": lambda: hue_rule([(215, 345, "sand")], neutral_c=4.0),
    "tangerine": lambda: hue_rule([(40, 110, "tangerine_ptr")]),
    # the tutorial hand: the yellow emoji hand -> a mint Digger glove (the grey shadow stays)
    "hand": lambda: hue_rule([(40, 110, "mint_glove")]),
}


def rules_for(kind):
    return RULES[kind]()


def chain(*rules):
    """First rule that changes a colour wins."""
    def rule(h):
        for r in rules:
            v = r(h)
            if v and v != h:
                return v
        return None
    return rule


def palette_table(svg, rule):
    """[(old, new, ΔE00)] for every distinct colour an SVG uses (review CSV / sheets)."""
    seen = []
    for m in HEX.finditer(svg):
        h = "#" + m.group(1).upper()
        if h not in [s[0] for s in seen]:
            n = rule(h) or h
            seen.append((h, n, round(de00(h, n), 1)))
    return seen


# ------------------------------------------------------------------------------------------------ raster recolouring
# For RENDERED sprites (the 3-D corner, corner.py): the same material maps per pixel, vectorised. Alpha is untouched,
# so the silhouette (and every anchor / bbox) is identical by construction; L* (the render's shading) is kept.

def _np_lab(rgb):
    import numpy as np
    c = rgb / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    Mx = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ Mx.T / np.array([_XN, _YN, _ZN])
    e = 216 / 24389
    f = np.where(xyz > e, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    L = 116 * f[..., 1] - 16
    return L, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])


def _np_rgb(L, a, b):
    import numpy as np
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200

    def inv(t):
        return np.where(t ** 3 > 216 / 24389, t ** 3, (116 * t - 16) / (24389 / 27))
    xyz = np.stack([inv(fx) * _XN, inv(fy) * _YN, inv(fz) * _ZN], -1)
    Mi = np.array([[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560], [0.0556434, -0.2040259, 1.0572252]])
    lin = xyz @ Mi.T
    return np.where(lin > 0.0031308, 1.055 * np.abs(lin) ** (1 / 2.4) - 0.055, 12.92 * lin) * 255.0


def _np_material(mat, L, C):
    """Vectorised Material.map: (L', C', h') arrays."""
    import numpy as np
    L2 = np.clip(mat.l_off + mat.l_gain * L, 0, 100)
    Lp = np.array([p[0] for p in mat.pts])
    Cp = np.array([p[1] for p in mat.pts])
    hp = np.unwrap(np.radians([p[2] for p in mat.pts]))
    Ct = np.interp(L2, Lp, Cp)
    ht = np.interp(L2, Lp, hp)
    if mat.c_ref:
        Ct = Ct * np.sqrt(np.maximum(C, 0) / mat.c_ref) * mat.ck
    else:
        Ct = Ct * mat.ck
    if mat.c_max is not None:
        Ct = np.minimum(Ct, mat.c_max)
    return L2, Ct, ht


def recolour_image(im, windows, neutral_c=3.0):
    """PIL RGBA -> PIL RGBA: every pixel whose CIELAB hue falls in a window takes that window's material (L* kept,
    chroma relative, gamut-clipped by reducing chroma); pixels below `neutral_c` chroma and alpha stay as they are."""
    import numpy as np
    from PIL import Image
    a = np.asarray(im.convert("RGBA")).astype(np.float64)
    rgb = a[..., :3]
    L, A, B = _np_lab(rgb)
    C = np.hypot(A, B)
    h = (np.degrees(np.arctan2(B, A)) + 360) % 360
    out = rgb.copy()
    live = (a[..., 3] > 0) & (C >= neutral_c)
    for h0, h1, fam in windows:
        m = live & ((h >= h0) & (h < h1) if h0 <= h1 else (h >= h0) | (h < h1))
        if not m.any():
            continue
        mat = M[fam]
        L2, C2, h2 = _np_material(mat, L[m], C[m])
        for _ in range(40):
            new = _np_rgb(L2, C2 * np.cos(h2), C2 * np.sin(h2))
            bad = ((new < -0.5) | (new > 255.5)).any(-1)
            if not bad.any():
                break
            C2 = np.where(bad, C2 * 0.94, C2)
        out[m] = new
        live &= ~m
    a[..., :3] = np.clip(out, 0, 255)
    return Image.fromarray(np.round(a).astype(np.uint8), "RGBA")


# the corner (corner.py renders): the red plate -> a mint rubber bumper, the blue coil + base -> brass
CORNER_WINDOWS = [(330, 80, "mint_plate"), (200, 330, "brass_coil")]


def corner_post(im):
    return recolour_image(im, CORNER_WINDOWS)


if __name__ == "__main__":
    # self-check: L* is kept (within gamut limits) and a known D1 anchor maps near itself
    for fam, hx in (("teal", "#DC236C"), ("timber", "#FFA40D"), ("iron", "#AE3DD3"), ("plank", "#5FA6F2"), ("brass", "#BB51DB"),
                    ("copper", "#1597D6"), ("slate", "#BC5BF6"), ("tangerine", "#10A2EF")):
        n = remap(hx, fam)
        print(f"{fam:10s} {hx} L{lch(hx)[0]:5.1f} -> {n} L{lch(n)[0]:5.1f} C{lch(n)[1]:5.1f} h{lch(n)[2]:5.1f}  ΔE00 {de00(hx, n):.1f}")
