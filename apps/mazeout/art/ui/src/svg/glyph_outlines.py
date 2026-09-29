#!/usr/bin/env python3
"""Dump glyph outlines of OUR OFL display font (design/fonts/PCDisplay-Black.ttf = Nunito wght 1000, SIL OFL 1.1) as SVG
path data (font units, y UP, origin on the baseline) into art/ui/src/svg/pcdisplay_glyphs.json, for lettering that is
baked into brand art (logoArrowOut only: the brand name is never translated). Needs fontTools (system python3 has it;
the mf3d venv does not), so the generator reads the JSON instead of the font.

    python3 art/ui/src/svg/glyph_outlines.py            # default character set "ARROWOUT!0123456789PRIZE"
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
FONTS = {"black": os.path.join(APP, "design", "fonts", "PCDisplay-Black.ttf"),
         "blackItalic": os.path.join(APP, "design", "fonts", "PCDisplay-BlackItalic.ttf")}
OUT = os.path.join(HERE, "pcdisplay_glyphs.json")


def dump(chars):
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont
    res = {}
    for key, path in FONTS.items():
        f = TTFont(path)
        gs = f.getGlyphSet()
        cmap = f.getBestCmap()
        hhea = f["hhea"]
        d = {"unitsPerEm": f["head"].unitsPerEm, "ascender": hhea.ascent, "descender": hhea.descent,
             "capHeight": getattr(f["OS/2"], "sCapHeight", 0), "glyphs": {}}
        for ch in chars:
            gn = cmap.get(ord(ch))
            if gn is None:
                continue
            pen = SVGPathPen(gs)
            gs[gn].draw(pen)
            bp = BoundsPen(gs)
            gs[gn].draw(bp)
            d["glyphs"][ch] = {"d": pen.getCommands(), "adv": gs[gn].width, "bounds": bp.bounds}
        res[key] = d
    json.dump(res, open(OUT, "w"), indent=0)
    print("wrote", OUT, {k: len(v["glyphs"]) for k, v in res.items()})


if __name__ == "__main__":
    dump(sys.argv[1] if len(sys.argv) > 1 else "ARROWOUT!0123456789PRIZE")
