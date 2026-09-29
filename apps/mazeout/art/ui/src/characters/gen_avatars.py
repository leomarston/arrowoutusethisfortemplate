"""Characters lane: the flat SVG avatar pieces (route B2).

avatarDefault -- the player's avatar until they pick one: a grey-blue head-and-shoulders silhouette on a grey-blue
tile (phone v552: meta-003 Edit Profile cell 1, the home top bar 002, Sky Jump 066; looked at only). Measured on
meta-003 (phone px, the tile interior ~165 px = 55 pt inside the frame): tile #86A3AE (top) .. #809FA6 (bottom),
silhouette flat #637F93; head circle d 110 px (0.667 of the interior) centred at 0.394 of its height, neck 67 px
wide at 0.667 (the circle / shoulder-ellipse pinch gives ~19 pt), shoulders ~150 px wide at the bottom edge. The frame (green = the player, blue = others) is UI chrome
(avatarFrame), not part of this art: the 64 pt square is full bleed and the frame covers ~4.5 pt of each edge, so the
interior numbers are mapped onto the 64 pt square about its centre (x 55/64).

    ~/.venvs/mf3d/bin/python art/tools/art_batch.py --manifest art/lanes/characters.entries.json --svg --ids avatarDefault
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shapes import svg_doc  # noqa: E402

S = 64.0                      # pt, full bleed
K_ = 55.0 / 64.0              # the frame's visible interior -> the square


def _m(u):
    """interior fraction (0..1 across the 55 pt interior) -> @3x px on the 64 pt square."""
    return (0.5 + (u - 0.5) * K_) * S * 3


def avatar_default():
    # A5 CODEMOD (2026-09-29): tile + silhouette on R9's chrome-blue -> D1 teal ladder (same L*); was #8AA7B2/#86A3AE/#7F9DA7/#637F93
    W = S * 3
    head_c = (_m(0.5), _m(0.394))
    head_r = 0.333 * 55.0 * 3                          # 110 of 165 interior px = 0.667 diameter -> r 18.3 pt, @3x px
    # shoulders: an ellipse whose top sits at 0.68 of the interior and which is ~0.91 of it wide at the bottom edge
    sh_top = _m(0.68)
    rx, ry = 27.0 * 3, 24.0 * 3
    defs = ('<linearGradient id="tile" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#93A7A0"/><stop offset="0.55" stop-color="#8FA39C"/>'
            '<stop offset="1" stop-color="#8A9C95"/></linearGradient>')
    body = (f'<rect x="0" y="0" width="{W:.1f}" height="{W:.1f}" fill="url(#tile)"/>\n'
            f'<g fill="#6B807A">'
            f'<circle cx="{head_c[0]:.2f}" cy="{head_c[1]:.2f}" r="{head_r:.2f}"/>'
            f'<ellipse cx="{W / 2:.2f}" cy="{sh_top + ry:.2f}" rx="{rx:.2f}" ry="{ry:.2f}"/>'
            f'</g>')
    return svg_doc(S, S, body, defs)


CASES = {"avatarDefault": avatar_default}

if __name__ == "__main__":
    for c in sys.argv[1:] or CASES:
        out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), f"{c}.svg")
        open(out, "w").write(CASES[c]())
        print(out)
