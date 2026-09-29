#!/usr/bin/env python3
"""Rasterise the SVG-method UI art: art/ui/src/<UIArt case>.svg -> art/ui/out/<case>@3x.png (exactly 3 px per pt).

    python3 art/ui/tools/svg.py hourglassGold tabHome ...     # cases (their .svg must exist in art/ui/src/)
    python3 art/ui/tools/svg.py --all
    python3 art/ui/tools/svg.py --draft tabHome               # -> build/ui-art/draft/<case>.png
    python3 art/ui/tools/svg.py --route pauseButton           # -> build/ui-art/svgroute/<case>.png (an SVG candidate
                                                              #    of a class that ships another route; compare only)

The root <svg> carries width/height in pt (and a viewBox); WebKit lays it out at 3x that in CSS px and snapshots at
the screen's backing scale (2x), and the result is downsampled to the exact size (supersampled edges).
The WebKit tool (svgr.swift) is compiled once to build/ui-art/svgr.
Opt-ins on the root (the win logo's parts, art/ui/tools/logo_parts.py): data-resample="box" = premultiplied area filter
instead of Lanczos (and the snapshot must be the full 2x); data-passes="ext,before,face" = the case is rendered as those
passes (logo_parts.pass_svgs) and composed exactly (logo_parts.compose: face OVER (before ATOP ext)) before the filter;
data-warp="bend x_a L_body clip" (the arrow sign's bend variants, LOGO-ART-2) = the premultiplied 2x render is warped by
logo_parts.warp (LOGO-SPEC §2's y' = y + k (x - x_a)^2) and then area-filtered 2:1 in float;
data-pass="ext" / "face" (LOGO-ART-3: a letter / glyph as a PAIR of single-pass layers) = the premultiplied 2x render is
area-filtered 2:1 in float exactly like the passes (logo_parts.box2), one rounding at the end;
data-pad="<logo px>" (LOGO-SPEC-FIX M3: logoSignPurple on its bend variants' padded frame) = the finished raster gets that
many logo px (x the file's px per logo px) of transparent rows appended at the bottom -- its pixels are unchanged.
LOGO-ART-4: a letter's flat sprite (logoLetter<X>Flat) carries data-passes="ext,face": its own extrusion (UNtrimmed) and its
own face rendered as two passes and composed face OVER extrusion (logo_parts.compose without a "before" pass).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.dirname(HERE)
APP = os.path.dirname(os.path.dirname(UI))
SRC = os.path.join(UI, "src")
OUT = os.path.join(UI, "out")
BUILD = os.path.join(APP, "build", "ui-art")
SVGR = os.path.join(BUILD, "svgr")


def ensure_tool():
    src = os.path.join(HERE, "svgr.swift")
    if os.path.exists(SVGR) and os.path.getmtime(SVGR) > os.path.getmtime(src):
        return
    os.makedirs(BUILD, exist_ok=True)
    subprocess.run(["swiftc", "-O", "-o", SVGR, src], check=True)


def svg_size(path):
    head = open(path, encoding="utf-8").read(4000)
    m = re.search(r"<svg[^>]*>", head, re.S)
    tag = m.group(0)
    w = float(re.search(r'\bwidth="([\d.]+)', tag).group(1))
    h = float(re.search(r'\bheight="([\d.]+)', tag).group(1))
    return w, h


def render(cases, draft=False, route=False, out_dir=None):
    ensure_tool()
    jobs, finals = [], []
    for c in cases:
        svg = os.path.join(SRC, f"{c}.svg")
        if not os.path.exists(svg):  # comparison-only sources (gen_props.COMPARE_ONLY) are generated into build/
            svg = os.path.join(BUILD, "svgsrc", f"{c}.svg")
        w, h = svg_size(svg)
        W, H = round(w * 3), round(h * 3)
        # lay the page out at the target pixel size with the svg scaled to fill it
        txt = open(svg, encoding="utf-8").read()
        txt = re.sub(r'(<svg[^>]*?)\bwidth="[\d.]+"', rf'\1width="{W}"', txt, count=1)
        txt = re.sub(r'(<svg[^>]*?)\bheight="[\d.]+"', rf'\1height="{H}"', txt, count=1)
        tmp_svg = os.path.join(BUILD, "svgtmp", f"{c}.svg")
        os.makedirs(os.path.dirname(tmp_svg), exist_ok=True)
        open(tmp_svg, "w", encoding="utf-8").write(txt)
        raw = os.path.join(BUILD, "svgtmp", f"{c}_raw.png")
        passes = re.search(r'<svg\b[^>]*\bdata-passes="([^"]+)"', txt[:4000])
        if passes:                       # multi-pass (logo letters): render each pass, compose after the snapshot
            sys.path.insert(0, HERE)
            import logo_parts as LPT
            psvgs = LPT.pass_svgs(c)
            assert sorted(psvgs) == sorted(passes.group(1).split(",")), (c, sorted(psvgs), passes.group(1))
            raw = {}
            for p_, ptxt in psvgs.items():
                ptxt = re.sub(r'(<svg[^>]*?)\bwidth="[\d.]+"', rf'\1width="{W}"', ptxt, count=1)
                ptxt = re.sub(r'(<svg[^>]*?)\bheight="[\d.]+"', rf'\1height="{H}"', ptxt, count=1)
                ps = os.path.join(BUILD, "svgtmp", f"{c}__{p_}.svg")
                open(ps, "w", encoding="utf-8").write(ptxt)
                raw[p_] = os.path.join(BUILD, "svgtmp", f"{c}__{p_}_raw.png")
                jobs.append(dict(svg=ps, out=raw[p_], w=W, h=H))
        else:
            jobs.append(dict(svg=tmp_svg, out=raw, w=W, h=H))
        dst = (os.path.join(out_dir, f"{c}@3x.png") if out_dir else os.path.join(BUILD, "draft", f"{c}.png") if draft else
               os.path.join(BUILD, "svgroute", f"{c}.png") if route else os.path.join(OUT, f"{c}@3x.png"))
        box = 'data-resample="box"' in txt[:4000]
        wsp = None
        if re.search(r'<svg\b[^>]*\bdata-pass="(ext|face)"', txt[:4000]):
            wsp = "pass"                 # LOGO-ART-3 pair layer: float premultiplied 2:1 area filter
            sys.path.insert(0, HERE)
            if 'data-trim="' in txt[:4000]:  # its extrusion is trimmed under its own face: render that face too
                import logo_parts as LPT
                ftxt = LPT._g().logo_part_svg(c[:-3] + "Face")
                ftxt = re.sub(r'(<svg[^>]*?)\bwidth="[\d.]+"', rf'\1width="{W}"', ftxt, count=1)
                ftxt = re.sub(r'(<svg[^>]*?)\bheight="[\d.]+"', rf'\1height="{H}"', ftxt, count=1)
                fs = os.path.join(BUILD, "svgtmp", f"{c}__face.svg")
                open(fs, "w", encoding="utf-8").write(ftxt)
                fraw = os.path.join(BUILD, "svgtmp", f"{c}__face_raw.png")
                jobs.append(dict(svg=fs, out=fraw, w=W, h=H))
                wsp = ("pass", fraw, LPT.trim_px(txt, 2 * W))
        if 'data-warp="' in txt[:4000]:
            sys.path.insert(0, HERE)
            import logo_parts as LPT
            wsp = (LPT.warp_spec(txt), LPT.viewbox(txt))
        padpx = 0
        mp = re.search(r'<svg\b[^>]*\bdata-pad="([\d.]+)"', txt[:4000])
        if mp:                           # LOGO-SPEC-FIX M3: + transparent rows at the bottom (logo px -> file px)
            vb = [float(v) for v in re.search(r'<svg\b[^>]*\bviewBox="([^"]+)"', txt[:4000]).group(1).split()]
            padpx = float(mp.group(1)) * W / vb[2]
            assert abs(padpx - round(padpx)) < 1e-6, (c, "data-pad must be whole file px", padpx)
            padpx = int(round(padpx))
        finals.append((raw, dst, W, H, box, wsp, padpx))
    job = os.path.join(BUILD, "svgtmp", f"job_{os.getpid()}.json")
    json.dump(jobs, open(job, "w"))
    subprocess.run([SVGR, job], check=True, timeout=220, stdout=subprocess.DEVNULL)
    os.remove(job)
    for raw, dst, W, H, box, wsp, padpx in finals:
        if isinstance(raw, dict):
            import logo_parts as LPT
            ims = {k: Image.open(v).convert("RGBA") for k, v in raw.items()}
            for k, im_ in ims.items():
                if im_.size != (2 * W, 2 * H):
                    raise SystemExit(f"svg.py: {os.path.basename(dst)} pass {k}: snapshot {im_.size}, not 2x {W}x{H} "
                                     f"(the display's backing scale?)")
            im = LPT.to_img(LPT.box2(LPT.compose(ims)))
            for v in raw.values():
                os.remove(v)
        elif wsp == "pass" or (isinstance(wsp, tuple) and wsp[0] == "pass"):
            # a pair layer (LOGO-ART-3): the exact 2:1 area filter in premultiplied float; an extrusion trimmed first
            import logo_parts as LPT
            im_ = Image.open(raw).convert("RGBA")
            if im_.size != (2 * W, 2 * H):
                raise SystemExit(f"svg.py: {os.path.basename(dst)}: snapshot {im_.size}, not 2x {W}x{H} (the display's backing scale?)")
            p_ = LPT.pm(im_)
            if isinstance(wsp, tuple):
                p_ = LPT.trim_ext(p_, LPT.pm(Image.open(wsp[1]).convert("RGBA")), wsp[2])
                os.remove(wsp[1])
            im = LPT.to_img(LPT.box2(p_))
            os.remove(raw)
        elif wsp:                        # a bend variant: warp the premultiplied 2x render, then the exact 2:1 area filter
            import logo_parts as LPT
            im_ = Image.open(raw).convert("RGBA")
            if im_.size != (2 * W, 2 * H):
                raise SystemExit(f"svg.py: {os.path.basename(dst)}: snapshot {im_.size}, not 2x {W}x{H} (the display's backing scale?)")
            im = LPT.to_img(LPT.box2(LPT.warp(LPT.pm(im_), wsp[0], wsp[1])))
            os.remove(raw)
        else:
            im = Image.open(raw).convert("RGBA")
            if box and im.size != (2 * W, 2 * H):
                raise SystemExit(f"svg.py: {os.path.basename(dst)}: snapshot {im.size}, not 2x {W}x{H} (the display's backing scale?)")
            if im.size != (W, H):
                # opt-in (logo parts, UI-ART): an SVG whose root says data-resample="box" is area-averaged (premultiplied, no
                # negative lobes: no ringing halo on a layer's alpha edge, so separately animated layers re-assemble cleanly)
                im = im.resize((W, H), Image.BOX if box else Image.LANCZOS)
            os.remove(raw)
        if padpx:                        # data-pad (LOGO-SPEC-FIX M3): the render unchanged, transparent rows appended
            padded = Image.new("RGBA", (im.size[0], im.size[1] + padpx), (0, 0, 0, 0))
            padded.paste(im.convert("RGBA"), (0, 0))
            im = padded
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im.save(dst, optimize=True)
        print(f"  {os.path.basename(dst)} {im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    a = sys.argv[1:]
    draft = "--draft" in a
    route = "--route" in a
    a = [x for x in a if x not in ("--draft", "--route")]
    if "--all" in a:
        a = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".svg"))
    render(a, draft, route)
