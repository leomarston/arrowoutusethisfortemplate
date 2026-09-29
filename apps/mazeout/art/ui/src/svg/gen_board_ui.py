#!/usr/bin/env python3
"""PUBLISH R7 BOARD-UI: the D1 "Burrow Works" skin of the board-related UI art that lives in gen_icons.py / gen_missing.py
(unlock-card icons, door / pipe shards, the tutorial hand, the two pointers, the page-ground pattern).

SPEC.md ruling 46 (owner, "minimum sufficient distance"): same shapes, sizes, anchors and layout; only materials, colours and
small details change. So every case here CALLS the measured generator (gen_icons / gen_missing, never edited by this lane)
and recolours its SVG per material with art/ui/src/d1_skin.py -- the same material maps as the board sprites
(gen_board.py `skinned`), so a card icon and the board obstacle it introduces always match. The board sprites embedded
by the card icons (pipe mouth + counter, tape, door, lock) already come out of gen_board in D1; only the parts a card
draws itself (the pipe tube, the linked arrows, the box / elevator illustrations) are mapped here, by EXACT colour sets
so nothing is recoloured twice.

    PY=~/.venvs/mf3d/bin/python
    $PY art/tools/art_batch.py --manifest art/lanes/board-ui.entries.json --svg --ids unlockIconPipe ...
    $PY art/ui/src/svg/gen_board_ui.py                 # writes art/ui/src/<case>.svg for every case (no raster)

Units and frames: exactly the wrapped generator's (the case returns its SVG text / (svg, meta) unchanged in geometry).
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
for _p in (HERE, SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import d1_skin as S  # noqa: E402
import gen_icons as GI  # noqa: E402
import gen_missing as GM  # noqa: E402


def _apply(res, rule):
    svg, meta = res if isinstance(res, tuple) else (res, None)
    svg = S.recolour(svg, rule)
    return (svg, meta) if meta is not None else svg


# the card's own pipe tube (gen_icons.unlock_pipe): cyan glass -> copper, like the board's tube (PipeLayer.swift)
PIPE_TUBE = ["#2291D6", "#2EA8E4", "#39BCEF", "#45CCF7", "#6ED3F8", "#A6E4FA", "#5FE0FB"]
# the card's two arrows (gen_icons.unlock_linked): the exit-colour blue -> the D1 exit colour (tangerine)
LINKED_ARROWS = ["#0D3DF5", "#10298F", "#122FC0", "#127AFE", "#1459FC", "#1468D8", "#1487F5", "#1776FF", "#1B61BF",
                 "#1C96F3", "#30AEFF"]
# the page-ground pattern (gen_missing.PATTERN fill #0B4A97 at 10 % over the navy page): over the D1 page ground
# (#003135 -> #002A2D, R9's map of page.bgNavy) the same faint lift (+1, +4.9, +4.9 per channel at 10 %)
PAGE_PATTERN = {"#0B4A97": "#0A6266"}


def unlock_icon_pipe():
    return _apply(GI.unlock_pipe(), S.set_rule(PIPE_TUBE, "copper"))


def unlock_icon_linked():
    return _apply(GI.unlock_linked(), S.set_rule(LINKED_ARROWS, "tangerine_arrow"))


def unlock_icon_box():
    return _apply(GI.unlock_box(), S.rules_for("boxIcon"))


def unlock_icon_elevator():
    return _apply(GI.unlock_elevator(), S.rules_for("elevator"))


def door_shards():
    return _apply(GI.door_shards(), S.rules_for("doorShards"))


def pipe_shards():
    return _apply(GI.pipe_shards(), S.rules_for("glass"))


# The tutorial hand: the yellow emoji hand becomes a mint Digger GLOVE with a hard-hat-yellow cuff (a detail inside the same
# silhouette: the wrist's last 12 of the hand's 104 units), so the fingertip anchor and the alpha bbox are unchanged.
CUFF = dict(y0=91.5, y1=106.0, face=("#FFD84A", "#FFCB2F", "#E0A416"), lite="#FFF1B0", seam="#9E6A10")


def tutorial_hand():
    svg, meta = _apply(GI.tutorial_hand(102, 136), S.rules_for("hand"))
    # the hand's own group is the second `rotate(-16 46 52)` group; its clip path (the union of the hand's parts) is
    # the first clip-path it uses
    heads = [m.start() for m in re.finditer(r'<g transform="translate\([^"]*\) scale\([^"]*\) rotate\(-16 46 52\)">', svg)]
    assert heads, "tutorial_hand layout changed"
    clip = re.search(r'clip-path="url\(#([^)]+)\)"', svg[heads[-1]:]).group(1)
    c = CUFF
    cuff = (f'<linearGradient id="cuffg" gradientUnits="userSpaceOnUse" x1="0" y1="{c["y0"]}" x2="0" y2="{c["y1"]}">'
            f'<stop offset="0" stop-color="{c["face"][0]}"/><stop offset="0.45" stop-color="{c["face"][1]}"/>'
            f'<stop offset="1" stop-color="{c["face"][2]}"/></linearGradient>')
    svg = svg.replace("</defs>", cuff + "</defs>", 1)
    band = (f'<g clip-path="url(#{clip})">'
            f'<rect x="20" y="{c["y0"]}" width="70" height="{c["y1"] - c["y0"]}" fill="url(#cuffg)"/>'
            f'<path d="M20 {c["y0"] + 1.6} L90 {c["y0"] + 1.6}" stroke="{c["lite"]}" stroke-opacity="0.85" stroke-width="2"/>'
            f'<path d="M20 {c["y0"]} L90 {c["y0"]}" stroke="{c["seam"]}" stroke-opacity="0.9" stroke-width="1.4"/></g>')
    end = svg.rindex("</g>")                       # the hand group's closing tag (the document's last group)
    svg = svg[:end] + band + svg[end:]
    return svg, meta


def pointer_arrow_yellow():
    return _apply(GI.pointer_arrow_yellow(), S.rules_for("tangerine"))


def pointer_arrow_down():
    return _apply(GM.pointer_arrow_down(), S.rules_for("tangerine"))


def page_bg_pattern():
    return _apply(GM.page_bg_pattern(), S.exact_rule(PAGE_PATTERN))


CASES = {
    "unlockIconPipe": unlock_icon_pipe,
    "unlockIconLinked": unlock_icon_linked,
    "unlockIconBox": unlock_icon_box,
    "unlockIconElevator": unlock_icon_elevator,
    "doorShards": door_shards,
    "pipeShards": pipe_shards,
    "tutorialHand": tutorial_hand,
    "pointerArrowYellow": pointer_arrow_yellow,
    "pointerArrowDown": pointer_arrow_down,
    "pageBgPattern": page_bg_pattern,
}


if __name__ == "__main__":
    for name in sys.argv[1:] or list(CASES):
        res = CASES[name]()
        svg = res[0] if isinstance(res, tuple) else res
        open(os.path.join(SRC, f"{name}.svg"), "w", encoding="utf-8").write(svg)
        print("wrote", name)
