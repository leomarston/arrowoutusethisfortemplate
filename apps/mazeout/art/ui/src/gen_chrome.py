#!/usr/bin/env python3
"""SVG sources for the glossy UI chrome (route B, SVG variant): writes art/ui/src/<case>.svg, rasterised by
art/ui/tools/svg.py to art/ui/out/<case>@3x.png.

    ~/.venvs/mf3d/bin/python art/ui/src/gen_chrome.py            # all cases below
    python3 art/ui/tools/svg.py pauseButton heartHUD buttonGreen

Every layer and colour is measured on the untinted runner shots (003 HUD, 007 Paused panel); see art/STYLE.md §B.
Units: @3x px (1 = 1/3 pt), y down. Shapes are primitives (superellipse, heart from circles), never traced.
Text is NEVER baked in (buttonGreen is blank: the label is live text in the app).
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from shapes import fmt, heart2_path, superellipse_path, svg_doc  # noqa: E402


def _stops(stops):
    out = []
    for st in stops:
        o, c = st[0], st[1]
        a = st[2] if len(st) > 2 else 1
        op = "" if a == 1 else f' stop-opacity="{a}"'
        out.append(f'<stop offset="{o}" stop-color="{c}"{op}/>')
    return "".join(out)


def lin(id_, stops, x1=0, y1=0, x2=0, y2=1):
    return f'<linearGradient id="{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{_stops(stops)}</linearGradient>'


def rad(id_, stops, cx=0.5, cy=0.5, r=0.5, fx=None, fy=None, extra=""):
    f = f' fx="{fx}" fy="{fy}"' if fx is not None else ""
    return f'<radialGradient id="{id_}" cx="{cx}" cy="{cy}" r="{r}"{f} {extra}>{_stops(stops)}</radialGradient>'


def blur(id_, std):
    return (f'<filter id="{id_}" x="-30%" y="-30%" width="160%" height="160%">'
            f'<feGaussianBlur stdDeviation="{std}"/></filter>')


# ------------------------------------------------------------------ the square blue HUD button (pause, back, settings)
# Shot 003 (centre column / row profiles): body 120 x 120 px superellipse n 3.5. Rim: top 5 px #0047DB, sides 9 px
# #0040CF (outer) -> #0252E9 (inner), bottom lip 12 px #0465EF -> #004FE9 -> #0047DA -> #0038C2. Face inset
# (12, 6, 12, 12), flat #0192FF -> #008BFE, a 5 px bright top edge #48C1FF and 2 px light sides #1F8BFA. A dark soft
# shadow all round, mostly below: #5D6B83 right under the body, ~8 px deep. Glyph bars 18 x 61 px, navy outline
# #0B2B86 3 px, face #EAFFFD, bottom shade #A9D5EB / #7BB7DC.

def blue_square(glyph: str, W=44, H=44):
    bx, by, bw, bh = 6, 4, 120, 120
    body = superellipse_path(bx, by, bw, bh, 3.5)
    fx, fy, fw, fh = bx + 12, by + 6, bw - 24, bh - 6 - 12
    face = superellipse_path(fx, fy, fw, fh, 3.5)
    defs = (lin("rim", [(0, "#0047DB"), (0.1, "#004CE4"), (0.86, "#0050EA"), (0.9, "#0465EF"), (0.94, "#004CE4"),
                        (0.97, "#0044D6"), (1, "#0036BE")]) +
            lin("rimside", [(0, "#002E9A", 0.6), (0.09, "#002E9A", 0), (0.91, "#002E9A", 0), (1, "#002E9A", 0.6)], 0, 0, 1, 0) +
            lin("face", [(0, "#0192FF"), (1, "#008BFE")]) +
            lin("facegl", [(0, "#50C8FF"), (0.07, "#3FBCFF"), (0.14, "#1B8EF8"), (0.6, "#1488F8"), (1, "#008BFE")]) +
            blur("sh", 2.8) + blur("soft", 0.7) +
            f'<clipPath id="facec"><path d="{face}"/></clipPath>')
    g = [f'<path d="{body}" fill="#1E2940" fill-opacity="0.8" filter="url(#sh)" transform="translate(0 3)"/>',
         f'<path d="{body}" fill="url(#rim)"/>',
         f'<path d="{body}" fill="url(#rimside)"/>',
         f'<path d="{face}" fill="url(#face)"/>',
         f'<g clip-path="url(#facec)"><path d="{face}" fill="none" stroke="url(#facegl)" stroke-width="7" filter="url(#soft)"/></g>']
    if glyph == "pause":
        for x in (bx + 36, bx + 66):
            y, w, h = by + 31, 18, 61
            g.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#0B2B86"/>')
            g.append(f'<clipPath id="bar{x}"><rect x="{x + 3}" y="{y + 3}" width="{w - 6}" height="{h - 6}" rx="4.5"/></clipPath>')
            g.append(f'<g clip-path="url(#bar{x})"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#EAFFFD"/>'
                     f'<rect x="{x}" y="{y + h - 13}" width="{w}" height="10" fill="#A9D5EB"/>'
                     f'<rect x="{x}" y="{y + h - 6}" width="{w}" height="6" fill="#7BB7DC"/></g>')
    return svg_doc(W, H, "\n".join(g), defs)


# ------------------------------------------------------------------ the glossy red heart (HUD lives, 3 per level)
# Shot 003: 88 x 76 px incl. a thin dark outline #711925; body radial #FC3A2A centre -> #E0120A -> #B30400 edges,
# darker just under the top edge (#B20103); a warm specular blob #FD9160 on the left lobe (centre ~(27, 25) px),
# a thin light streak on the right lobe's upper-right edge; a dark-blue soft halo (#7D99D5 on the #BDDCFF panel).
# Outline = shapes.HEART2 (two ellipses leaning +-48 deg, IoU 0.977).

def heart_hud(W=31, H=27):
    hx, hy, hw, hh = 2.5, 1.5, 88, 76
    p = heart2_path(hx, hy, hw, hh)
    defs = (rad("hb", [(0, "#FD6A48"), (0.25, "#FB3E2C"), (0.55, "#F02416"), (0.8, "#DC0C05"), (1, "#B80400")],
                cx=0.42, cy=0.40, r=0.62, fx=0.36, fy=0.33) +
            lin("htop", [(0, "#8A0006", 0.8), (0.14, "#A00003", 0), (0.78, "#A00003", 0), (1, "#8A0006", 0.45)]) +
            rad("spec", [(0, "#FFB189", 0.95), (0.45, "#FD9160", 0.55), (1, "#FC6A48", 0)]) +
            blur("hh", 2.0) + blur("s1", 0.9) + blur("ol", 0.7) +
            f'<clipPath id="hc"><path d="{p}"/></clipPath>')
    g = [f'<path d="{p}" fill="#1D3D40" fill-opacity="0.6" filter="url(#hh)" transform="translate(0 1)"/>',
         f'<path d="{p}" fill="url(#hb)"/>',
         f'<path d="{p}" fill="url(#htop)"/>',
         f'<g clip-path="url(#hc)">'
         f'<ellipse cx="{hx + 27}" cy="{hy + 25}" rx="10" ry="7" transform="rotate(-38 {hx + 27} {hy + 25})" fill="url(#spec)" filter="url(#s1)"/>'
         f'<path d="M{hx + 63} {hy + 8} Q{hx + 79} {hy + 9} {hx + 82} {hy + 26}" fill="none" stroke="#FF9A7C" stroke-opacity="0.7" '
         f'stroke-width="2.4" stroke-linecap="round" filter="url(#s1)"/>'
         f'<path d="{p}" fill="none" stroke="#7A0610" stroke-width="5" filter="url(#ol)"/></g>',
         f'<path d="{p}" fill="none" stroke="#6E0E16" stroke-width="1.6"/>']
    return svg_doc(W, H, "\n".join(g), defs)


# ------------------------------------------------------------------ the big glossy panel button (Resume green, Quit red)
# Shot 007 (centre profiles): body 375 x 267 px superellipse n 4 with a 3 px dark outline #0A3C00. The FACE reaches the
# top edge (a 3-D pill seen from a little above): face inset (23, 3, 23, 33) n 4.5, #02E10F top -> #00E900 -> #00E400
# -> #00CC00 bottom. Sides: a 15 px band #005700 (outer) -> #007C00 (inner) + a 6 px light edge #61D761 on the face
# side; bottom lip 28 px #018301 -> #007300 -> #005D00 -> #004F00. A glare line #91FC92 (6 px) 16 px under the top
# edge, following the top contour and fading down the sides. Blank: the label is live text.

PANEL_BUTTONS = {
    "green": dict(outline="#0A3C00", edge_dark="#003A00",
                  rim=[(0, "#006400"), (0.55, "#007600"), (0.84, "#008401"), (0.9, "#007600"), (0.96, "#005A00"), (1, "#004A00")],
                  face=[(0, "#02E10F"), (0.07, "#02E10F"), (0.1, "#00E900"), (0.3, "#00E400"), (0.65, "#00D600"), (1, "#00CA00")],
                  edge="#66EC66", glare="#91FC92"),
    "red": dict(outline="#5A0006", edge_dark="#5A0006",
                rim=[(0, "#A0000C"), (0.55, "#B0000E"), (0.84, "#BC020F"), (0.9, "#A8000D"), (0.96, "#86000A"), (1, "#6A0006")],
                face=[(0, "#FF3838"), (0.07, "#FF3838"), (0.1, "#FF2A2A"), (0.3, "#FB1E1E"), (0.65, "#F01010"), (1, "#E20808")],
                edge="#FF6A6A", glare="#FFA6A6"),
}


def panel_button(color="green", W=127, H=91):
    c = PANEL_BUTTONS[color]
    bx, by, bw, bh = 3, 3, 375, 267
    body = superellipse_path(bx, by, bw, bh, 4.0)
    inner = superellipse_path(bx + 3, by + 3, bw - 6, bh - 6, 4.0)
    fx, fy, fw, fh = bx + 23, by + 3, bw - 46, bh - 3 - 33
    face = superellipse_path(fx, fy, fw, fh, 4.5)
    gl = superellipse_path(fx + 4, fy + 16, fw - 8, fh - 30, 4.5)
    defs = (lin("rim", c["rim"]) + lin("face", c["face"]) +
            lin("glm", [(0, "#FFFFFF", 1), (0.22, "#FFFFFF", 0.55), (0.55, "#FFFFFF", 0)]) +
            lin("edm", [(0, "#FFFFFF", 0.9), (0.5, "#FFFFFF", 0.6), (1, "#FFFFFF", 0.2)]) +
            blur("s", 1.2) + blur("e", 4.0) +
            f'<clipPath id="fc"><path d="{face}"/></clipPath><clipPath id="ic"><path d="{inner}"/></clipPath>'
            f'<mask id="gm" maskUnits="userSpaceOnUse" x="0" y="0" width="{W * 3}" height="{H * 3}">'
            f'<rect x="0" y="{fy}" width="{W * 3}" height="{fh}" fill="url(#glm)"/></mask>'
            f'<mask id="em" maskUnits="userSpaceOnUse" x="0" y="0" width="{W * 3}" height="{H * 3}">'
            f'<rect x="0" y="{fy}" width="{W * 3}" height="{fh}" fill="url(#edm)"/></mask>')
    g = [f'<path d="{body}" fill="{c["outline"]}"/>',
         f'<path d="{inner}" fill="url(#rim)"/>',
         # the side band darkens toward the outer edge (a cylinder side seen at a grazing angle)
         f'<g clip-path="url(#ic)"><path d="{inner}" fill="none" stroke="{c["edge_dark"]}" stroke-opacity="0.75" stroke-width="12" filter="url(#e)"/></g>',
         f'<path d="{face}" fill="url(#face)"/>',
         f'<g clip-path="url(#fc)"><path d="{face}" fill="none" stroke="{c["edge"]}" stroke-width="11" filter="url(#s)" mask="url(#em)"/></g>',
         f'<path d="{gl}" fill="none" stroke="{c["glare"]}" stroke-opacity="0.85" stroke-width="4.5" mask="url(#gm)"/>']
    return svg_doc(W, H, "\n".join(g), defs)


CASES = {
    "pauseButton": lambda: blue_square("pause"),
    "heartHUD": heart_hud,
    "buttonGreen": lambda: panel_button("green"),
    "buttonRed": lambda: panel_button("red"),
}

if __name__ == "__main__":
    names = sys.argv[1:] or list(CASES)
    for n in names:
        open(os.path.join(HERE, f"{n}.svg"), "w", encoding="utf-8").write(CASES[n]())
        print("wrote", n)
