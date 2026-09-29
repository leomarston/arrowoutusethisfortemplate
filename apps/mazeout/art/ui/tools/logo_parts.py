#!/usr/bin/env python3
"""The win logo's animation parts: measure their frames, build, prove they re-assemble, check edges, write the manifest.

Round 1 (UI-ART, OWNER P0 19:40 (b)): logoSignPurple, logoSignBlue, logoLetterA R1 R2 O W, logoOut (evidence build/logo/art/,
kept as the record). Round 2 (LOGO-ART-2, 2026-09-27, build/logo/LOGO-SPEC.md §9.1-9.4; evidence build/logo/art2/):
  P0  "OUT!" as four layers logoOutO, logoOutU, logoOutT, logoOutBang (split like ARROW's letters; logoOut kept),
  P1  the two grey pegs as their own layer logoPegs; logoSignPurple re-exported without them (continuous top rim),
  P2  four bent variants of logoSignPurple (LOGO-SPEC §2's warp): logoSignPurpleBend25 / 50 / 75 / 100 (-2.5 ... -10 deg),
  P3  the first 8 parts' manifest notes moved to the new rest (the logo rests at celebrate.logo's k 1.00665, no 0.94 settle).

    PY=~/.venvs/mf3d/bin/python
    $PY art/ui/tools/logo_parts.py measure     # the round-2 frames (pegs, glyphs), the bend pad and x_a -> paste the printed
                                               #   values into gen_icons (LOGO_PART_FRAMES.update, LOGO_BEND)
    $PY art/tools/art_batch.py --svg --ids logoSignPurple logoPegs logoOutO logoOutU logoOutT logoOutBang \
        logoSignPurpleBend25 logoSignPurpleBend50 logoSignPurpleBend75 logoSignPurpleBend100
                                               # the shipped files (manifest svg route; svg.py composes passes / warps)
    $PY art/ui/tools/logo_parts.py manifest    # (re)write the logo group's MANIFEST entries (new parts + the first 8's notes)
    $PY art/ui/tools/logo_parts.py verify      # every shipped part == a fresh render of its SVG (bit-exact), sizes
    $PY art/ui/tools/logo_parts.py proof       # re-assembly proofs (+ sheets) -> build/logo/art2/
    $PY art/ui/tools/logo_parts.py fringe      # premultiplied-edge check (black + white, 400 %) -> build/logo/art2/
    $PY art/ui/tools/logo_parts.py upscale     # LOGO-SPEC table U with the real files -> build/logo/art2/upscale.json
    $PY art/ui/tools/logo_parts.py bendcal     # L_body so LOGO-SPEC's bend.py reads each variant at its nominal bend
    $PY art/ui/tools/logo_parts.py geometry    # the OLD on-screen sizes (today's WinLogoSequence.swift: settle 0.94)
    $PY art/ui/tools/logo_parts.py clean       # remove the scratch renders
Round 3 (LOGO-ART-3, 2026-09-27; the owner: "the OUT! has weird lines when it grows on the screen"; evidence build/logo/art3/):
  every independently moving letter / glyph as a PAIR <id>Ext + <id>Face (gen_icons.LOGO_PAIRS: its extrusion alone, trimmed
  under its own opaque face, and its face alone; one shared transform; every Ext of a word under every Face of it) -- the
  composed round-1/2 files bake the earlier letter's face into the later one, which LOGO-SPEC's motion spreads apart.
    $PY art/tools/art_batch.py --svg --ids logoLetterAExt logoLetterAFace ... logoOutBangExt logoOutBangFace
    $PY art/ui/tools/logo_parts.py manifest    # + the 18 pair entries; verify (+ "only its own glyph" per pair)
    $PY art/ui/tools/logo_parts.py proof3      # at rest: 23-layer stack vs the one-piece (2x, 1x grid, settled), joins
    $PY art/ui/tools/logo_parts.py motion      # THE KEY TEST: LOGO-SPEC's tracks every 1/60 s W+0.60-1.95 on screen: stray
                                               #   pixels per frame (round 3 = 0; the round-2 files as the negative control)
    $PY art/ui/tools/logo_parts.py fringe3     # the pairs' edges over black / white;  upscale (table U incl. the pairs)
    $PY art/ui/tools/logo_parts.py pegsfix2    # round 2's pegs labels corrected (the PEGS over the sign) in build/logo/art2/

Round 4 (LOGO-ART-4, 2026-09-27, SPEC.md ruling 36; evidence build/logo/art4/): the pairs are never drawn translucent --
  OUT!'s 8 layers in ONE group-opacity container outGroup (the echo one container outEcho), each ARROW letter's FLAT sprite
  logoLetter<X>Flat (own face over own UNtrimmed extrusion; gen_icons.LOGO_FLATS, 2 passes) while its opacity < 1, the Ext
  trim ring 4 -> 1 logo px (gen_icons.LOGO_TRIM; build/logo/art4/trim_experiment*.py / .json).
    $PY art/tools/art_batch.py --svg --ids logoLetterAFlat ... logoLetterWFlat (+ the 9 Ext after a LOGO_TRIM change)
    $PY art/ui/tools/logo_parts.py manifest    # + the 5 flats; pair / flat size_pt = the replaced ids' (ruling 36 (e))
    $PY art/ui/tools/logo_parts.py look        # THE COLOUR TEST: the stack as LOGO-SPEC §2 composes it (outGroup, echo group,
                                               #   flats, trilinear) vs one sprite per glyph, every 1/60 s W+0.60-1.95
    $PY art/ui/tools/logo_parts.py swap        # ruling 36 (b): pair vs flat at opacity 1 (swap frame, later frames, at rest)
    $PY art/ui/tools/logo_parts.py fringe4     # pairs + flats over black / white;  verify / upscale as before (-> art4)
    build/logo/art4/tools/reassemble_cg        # LOGO-SPEC §5.3's unit-test bound, measured with CoreGraphics
LOGO-SPEC-FIX (2026-09-27; evidence build/logo/art4/specfix/): logoSignPurple re-exported on its bend variants' padded frame
  (gen_icons.LOGO_PAD, root data-pad: rendered on its own frame, transparent rows appended; `manifest logoSignPurple` rewrites
  just that entry); `look` / `swap` follow the spec's ONE anchor per layer (the MANIFEST's, winlogo_keyframes.json anchorPt),
  its ONE flatUntil for all five letters and the echo container's own opacity track (containers.outEcho.tracks.a).
    $PY art/ui/tools/logo_parts.py manifest [ids...]   # (re)write the logo entries (all, or just these ids)
Every part comes from the SVG drawing (art/ui/src/svg/gen_icons.py _logo_layers), never from a PNG. A part's frame is an
integer rect of logoArrowOut@3x's pixel grid (918 x 708) and its file is that rect x `factor` px, so shrinking a file by
1/factor puts it back on logoArrowOut's grid exactly (factor-1.5 parts sit on even logo px, so they share logoSignPurple's
file grid). The letters R1 R2 O W and OUT!'s U T ! are MULTI-PASS (gen_icons.logo_part_passes): WebKit draws three plain
passes on the part's frame -- the glyph's extrusion, the faces of the glyphs before it, its own face -- and `compose`
makes face OVER (earlier faces ATOP extrusion) in premultiplied float, then an exact 2:1 area filter (svg.py calls it for
any SVG root carrying data-passes). A bend variant's root carries data-warp: its 2x render is warped (`warp`) before the
filter. Scratch renders go to build/logo/art2/scratch (deleted by `clean`).
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as NDI

HERE = os.path.dirname(os.path.abspath(__file__))
UI = os.path.dirname(HERE)
APP = os.path.dirname(os.path.dirname(UI))
OUT = os.path.join(UI, "out")
EVID2 = os.path.join(APP, "build", "logo", "art2")          # round 2's evidence (the record)
EVID3 = os.path.join(APP, "build", "logo", "art3")          # round 3's evidence (the record)
EVID = os.path.join(APP, "build", "logo", "art4")           # the current round's evidence (LOGO-ART-4)
SCR = os.path.join(EVID, "scratch")
BACKUP = os.path.join(EVID2, "backup")         # round 2's copy of the files it replaced (the peg-carrying logoSignPurple)
SPEC = os.path.join(APP, "build", "logo", "spec")
SVGR = os.path.join(APP, "build", "ui-art", "svgr")
CW, CH = 918, 708                     # logoArrowOut@3x.png
IDS_R1 = ["logoSignPurple", "logoSignBlue", "logoLetterA", "logoLetterR1", "logoLetterR2", "logoLetterO", "logoLetterW", "logoOut"]
IDS = IDS_R1                          # (the old name)
LETTERS = ["logoLetterA", "logoLetterR1", "logoLetterR2", "logoLetterO", "logoLetterW"]
PEGS = "logoPegs"
GLYPHS = ["logoOutO", "logoOutU", "logoOutT", "logoOutBang"]
BENDS = ["logoSignPurpleBend25", "logoSignPurpleBend50", "logoSignPurpleBend75", "logoSignPurpleBend100"]
NEW = [PEGS] + GLYPHS + BENDS
# the logo at rest, bottom to top (LOGO-SPEC §2: z 0, 0.5, 1, 2-6, 7-10); FALLBACK = the same with OUT! as one layer
LAYERS = ["logoSignPurple", PEGS, "logoSignBlue"] + LETTERS + GLYPHS
FALLBACK = ["logoSignPurple", PEGS, "logoSignBlue"] + LETTERS + ["logoOut"]
Z = {"logoSignPurple": 0, PEGS: 0.5, "logoSignBlue": 1, **{p: 2 + i for i, p in enumerate(LETTERS)},
     **{p: 7 + i for i, p in enumerate(GLYPHS)}, "logoOut": 7, **{p: 0 for p in BENDS}}
# x logoArrowOut @3x. Integer WebKit mappings only (svgr snapshots at 2x: 1.5 -> 3, 2.0 -> 4, 3.0 -> 6, 4.0 -> 8 device px per
# logo px): a 1.25 part (2.5 px per logo px) measured 2495-3683 edge px > 16/255 off a supersampled render, 1.5 measured like 1x.
FACTOR = {"logoSignPurple": 1.5, "logoSignBlue": 1.5, "logoOut": 3.0, PEGS: 1.5, **{p: 4.0 for p in GLYPHS},
          **{p: 1.5 for p in BENDS}}                                                  # letters 2.0
MULT = {1.5: 2, 2.0: 3, 3.0: 1, 4.0: 3}   # frame sizes that make (size x factor) whole px AND whole pt (check.py: px % 3 == 0)
PAD = 3
BEND_MIN_PAD_PT = 8.0                 # LOGO-SPEC §2 / §9.3: the variants' frame padded >= 8 pt at the bottom
NAMES = {"logoOutO": "O", "logoOutU": "U", "logoOutT": "T", "logoOutBang": "!"}
# ---- round 3 (LOGO-ART-3): every independently moving letter / glyph as a PAIR <base>Ext + <base>Face (gen_icons.LOGO_PAIRS)
BASES = LETTERS + GLYPHS
WORD_OF = {**{b: "ARROW" for b in LETTERS}, **{b: "OUT!" for b in GLYPHS}}
EXT = {b: b + "Ext" for b in BASES}
FACE = {b: b + "Face" for b in BASES}
BASE_OF = {**{v: k for k, v in EXT.items()}, **{v: k for k, v in FACE.items()}}
ARROW_PAIRS = [EXT[b] for b in LETTERS] + [FACE[b] for b in LETTERS]      # inside logoSignBlue: every Ext under every Face
OUT_PAIRS = [EXT[b] for b in GLYPHS] + [FACE[b] for b in GLYPHS]         # z 7-10 Ext, 11-14 Face
PAIRS = ARROW_PAIRS + OUT_PAIRS
LAYERS3 = ["logoSignPurple", PEGS, "logoSignBlue"] + ARROW_PAIRS + OUT_PAIRS   # the round-3 stack, bottom to top
FALLBACK3 = ["logoSignPurple", PEGS, "logoSignBlue"] + ARROW_PAIRS + ["logoOut"]
Z.update({**{EXT[b]: round(2.0 + 0.1 * i, 1) for i, b in enumerate(LETTERS)},
          **{FACE[b]: round(3.0 + 0.1 * i, 1) for i, b in enumerate(LETTERS)},
          **{EXT[b]: 7 + i for i, b in enumerate(GLYPHS)}, **{FACE[b]: 11 + i for i, b in enumerate(GLYPHS)}})
LTR = {"logoLetterA": "A", "logoLetterR1": "R1", "logoLetterR2": "R2", "logoLetterO": "O", "logoLetterW": "W", **NAMES}
# ---- round 4 (LOGO-ART-4, SPEC.md ruling 36): each ARROW letter's FLAT sprite (own face over own UNTRIMMED extrusion),
# shown while the letter's opacity < 1 in its Face slot; OUT!'s 8 layers inside ONE group-opacity container (outGroup)
FLAT = {b: b + "Flat" for b in LETTERS}
FLATS = [FLAT[b] for b in LETTERS]
BASE_OF.update({v: k for k, v in FLAT.items()})
Z.update({FLAT[b]: round(3.0 + 0.1 * i, 1) for i, b in enumerate(LETTERS)})     # the letter's Face slot
ALL = IDS_R1 + NEW + PAIRS + FLATS


def gen():
    sys.path.insert(0, os.path.join(UI, "src"))
    sys.path.insert(0, os.path.join(UI, "src", "svg"))
    spec = importlib.util.spec_from_file_location("gen_icons_lp", os.path.join(UI, "src", "svg", "gen_icons.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_GEN = None


def _g():
    global _GEN
    if _GEN is None:
        _GEN = gen()
    return _GEN


def svgr(jobs):
    sys.path.insert(0, HERE)
    import svg as SVG
    SVG.ensure_tool()
    os.makedirs(SCR, exist_ok=True)
    p = os.path.join(SCR, f"job_{os.getpid()}.json")
    json.dump(jobs, open(p, "w"))
    subprocess.run([SVGR, p], check=True, timeout=220, stdout=subprocess.DEVNULL)
    os.remove(p)


# ---------------------------------------------------------------------------------------------- the passes (svg.py hook)
def pass_svgs(pid, frame=None, factor=None):
    """{pass: SVG text} of a multi-pass part ({} for a one-pass part); same root, viewBox and clamped regions as the part."""
    m = _g()
    return {p: m.logo_part_svg(pid, frame=frame, factor=factor, pass_=p) for p in m.logo_part_passes(pid)}


def pm(im):
    a = np.asarray(im.convert("RGBA")).astype(np.float64) / 255.0
    a[..., :3] *= a[..., 3:4]
    return a


def over(dst, src):
    return src + dst * (1.0 - src[..., 3:4])


def compose(raws):
    """{"ext", "before", "face": RGBA images (or premultiplied arrays) of one size} -> premultiplied float of
    face OVER (before ATOP ext): the earlier faces only where this glyph's extrusion is, E x (1 - a_F) + F x b_E.
    LOGO-ART-4: a flat sprite has no "before" pass -> face OVER its own (untrimmed) extrusion."""
    if "before" not in raws:
        a, c = (x if isinstance(x, np.ndarray) else pm(x) for x in (raws["ext"], raws["face"]))
        return over(a, c)
    a, b, c = (x if isinstance(x, np.ndarray) else pm(x) for x in (raws["ext"], raws["before"], raws["face"]))
    t = b * a[..., 3:4] + a * (1.0 - b[..., 3:4])
    return over(t, c)


def trim_ext(E, F, r):
    """LOGO-ART-3: a pair's extrusion E trimmed under its OWN face F (premultiplied rasters of one frame, r = gen_icons.
    LOGO_TRIM in raster px): removed only where that face is OPAQUE (a_F >= 0.998) AND farther than r from where the
    extrusion shows (E x (1 - a_F) >= 0.5: the 3-D side outside the face); kept everywhere else. Face OVER trimmed
    extrusion == face OVER extrusion at this resolution (the removed part is always under the opaque face: same
    transform), but the extrusion's sides no longer run exactly under the face's sides, which two separately filtered
    layers conflate into an extra lilac / orange rim along every side edge (build/logo/art3/reassembly.json)."""
    aE, aF = E[..., 3], F[..., 3]
    band = aE * (1.0 - aF) >= 0.5
    k = (NDI.distance_transform_edt(~band) <= r) if band.any() else np.zeros(aE.shape, bool)
    return E * (1.0 - ((aF >= 0.998) & ~k))[..., None]


def pad_logo(svg_text):
    """LOGO-SPEC-FIX M3: a root's data-pad (logo px of transparent rows appended below the render), 0 when absent."""
    m_ = re.search(r'<svg\b[^>]*\bdata-pad="([\d.]+)"', svg_text[:4000])
    return float(m_.group(1)) if m_ else 0.0


def trim_px(svg_text, W):
    """(trim radius in raster px) from a root's data-trim (logo px) and viewBox, for a raw render W raster px wide."""
    m_ = re.search(r'<svg\b[^>]*\bdata-trim="([\d.]+)"', svg_text[:4000])
    return float(m_.group(1)) * W / viewbox(svg_text)[2] if m_ else None


def box2(p):
    """Exact 2:1 area average of a premultiplied float image (both sides even)."""
    h, w = p.shape[0] // 2, p.shape[1] // 2
    return p[:2 * h, :2 * w].reshape(h, 2, w, 2, p.shape[2]).mean(axis=(1, 3))


def to_img(p):
    a = np.array(p, dtype=np.float64)
    al = a[..., 3:4]
    a[..., :3] = np.where(al > 0, a[..., :3] / np.maximum(al, 1e-9), 0)
    return Image.fromarray(np.clip(np.round(a * 255), 0, 255).astype(np.uint8), "RGBA")


def _sized(svg, w, h):
    return re.sub(r'width="[\d.]+" height="[\d.]+"', f'width="{w}" height="{h}"', svg, count=1)


# --------------------------------------------------------------------------------------------- the bend (svg.py hook)
def warp_spec(svg_text):
    """(bend deg, x_a, L_body, clip) in logo @3x px from a root's data-warp, or None."""
    m_ = re.search(r'<svg\b[^>]*\bdata-warp="([^"]+)"', svg_text[:4000])
    return tuple(float(v) for v in m_.group(1).split()) if m_ else None


def viewbox(svg_text):
    m_ = re.search(r'<svg\b[^>]*\bviewBox="([^"]+)"', svg_text[:4000])
    return tuple(float(v) for v in m_.group(1).split())


def warp(p, spec, frame):
    """LOGO-SPEC §2's bend on a premultiplied raster `p` of the logo-px rect `frame` (x0, y0, w, h): rows below `clip` (the
    rest file's own bottom edge, the canvas edge: the rest drawing is warped exactly as the rest file has it) are cleared,
    then out(x, y) = in(x, y - k (x - x_a)^2), k = -rad(bend) / (2 L_body) (bend < 0: k > 0, the ends move DOWN, x_a stays
    put). x is unchanged, so each column is a 1-D shift, linear in y (exact at bend 0). Deterministic (bit-exact re-render)."""
    bend, xa, body, clip = spec
    x0, y0, w, h = frame
    H, W = p.shape[:2]
    r = W / w                                         # raster px per logo px
    assert abs(H / h - r) < 1e-9, (p.shape, frame)
    q = np.array(p, dtype=np.float64, copy=True)
    cy = (clip - y0) * r
    ci = int(round(cy))
    assert abs(cy - ci) < 1e-6, ("the clip must fall on a whole raster row", cy)
    if ci < H:
        q[max(ci, 0):] = 0.0
    k = -math.radians(bend) / (2.0 * body)            # per logo px
    xs = x0 + (np.arange(W) + 0.5) / r                # column centres, logo px
    dpx = k * (xs - xa) ** 2 * r                      # the downward shift of each column, raster px
    rows = np.arange(H, dtype=np.float64)
    out = np.zeros_like(q)
    for c in range(W):
        if dpx[c] == 0.0:
            out[:, c] = q[:, c]
            continue
        src = rows - dpx[c]
        for ch in range(4):
            out[:, c, ch] = np.interp(src, rows, q[:, c, ch], left=0.0, right=0.0)
    return out


def bend_spec(pid):
    m = _g()
    spec = warp_spec(m.logo_part_svg(pid))          # exactly what the SVG's root says (svg.py reads the same attribute)
    b = m.LOGO_BEND
    assert spec == (float(m.LOGO_BENDS[pid]), float(b["xa"]), float(b["body"]), float(b["clip"])), spec
    return spec


def render_part(pid, frame, factor, tag, force=False, trim=True):
    """One part on `frame` (logo @3x px) at `factor`, raw WebKit 2x snapshot -> premultiplied float (passes composed, a
    bend variant warped, a pair's extrusion trimmed under its face unless trim=False). Cached in SCR as
    <pid>_<tag>[_<pass>]_raw.png."""
    m = _g()
    W, H = round(frame[2] * factor), round(frame[3] * factor)
    passes = m.logo_part_passes(pid)
    svgs = pass_svgs(pid, frame=frame, factor=factor) if passes else {"": m.logo_part_svg(pid, frame=frame, factor=factor)}
    padl = pad_logo(next(iter(svgs.values())))          # LOGO-SPEC-FIX M3: data-pad (logo px) -> drawn unpadded, rows added
    Hp, H = H, H - int(round(padl * factor))
    raws, jobs = {}, []
    os.makedirs(SCR, exist_ok=True)
    for p, s in svgs.items():
        stem = f"{pid}_{tag}" + (f"_{p}" if p else "")
        raw = os.path.join(SCR, f"{stem}_raw.png")
        raws[p] = raw
        if force or not os.path.exists(raw):
            sp = os.path.join(SCR, f"{stem}.svg")
            open(sp, "w", encoding="utf-8").write(_sized(s, W, H))
            jobs.append(dict(svg=sp, out=raw, w=W, h=H))
    if jobs:
        svgr(jobs)
    ims = {p: Image.open(r).convert("RGBA") for p, r in raws.items()}
    for p, im in ims.items():
        assert im.size == (2 * W, 2 * H), (pid, p, im.size, "WebKit did not snapshot at 2x (display backing scale?)")
    out = compose(ims) if passes else pm(ims[""])
    if Hp != H:                                          # the transparent pad rows (raw 2x)
        out = np.concatenate([out, np.zeros((2 * (Hp - H),) + out.shape[1:], out.dtype)], 0)
    if pid in m.LOGO_BENDS:
        out = warp(out, bend_spec(pid), frame)
    if trim and pid in getattr(m, "LOGO_PAIRS", {}) and m.LOGO_PAIRS[pid][1] == "ext":
        face = render_part(FACE[BASE_OF[pid]], frame, factor, tag, force)
        out = trim_ext(out, face, trim_px(svgs[""], out.shape[1]))
    return out


def render_svg_file(path, w, h, tag, force=False):
    """Any SVG file (e.g. round 1's logoSignPurple.svg from BACKUP) at w x h CSS px, raw 2x -> premultiplied float."""
    raw = os.path.join(SCR, f"{tag}_raw.png")
    if force or not os.path.exists(raw):
        sp = os.path.join(SCR, f"{tag}.svg")
        open(sp, "w", encoding="utf-8").write(_sized(open(path, encoding="utf-8").read(), w, h))
        svgr([dict(svg=sp, out=raw, w=w, h=h)])
    return pm(Image.open(raw))


def fc(pid, force=False):
    """A part on logoArrowOut's full canvas, raw WebKit 2x (1836 x 1416, 2 px per logo px), premultiplied float32."""
    return render_part(pid, (0, 0, CW, CH), 1.0, "full", force).astype(np.float32)


def fc_whole(name, force=False):
    """'whole' = logoArrowOut.svg exactly as it ships (canvas-wide filter regions); 'whole_same' = the one-piece body with the
    regions clamped like a part's (the fair reference for the split), both raw 2x on the full canvas, float32."""
    m = _g()
    raw = os.path.join(SCR, f"{name}_full_raw.png")
    if force or not os.path.exists(raw):
        svg = m.CASES["logoArrowOut"]() if name == "whole" else _whole_same_regions(m, 3.0)
        sp = os.path.join(SCR, f"{name}_full.svg")
        open(sp, "w", encoding="utf-8").write(_sized(svg, CW, CH))
        svgr([dict(svg=sp, out=raw, w=CW, h=CH)])
    return pm(Image.open(raw)).astype(np.float32)


def _whole_same_regions(m, factor):
    svg = m.logo_part_svg("logoSignBlue", frame=(0, 0, CW, CH), factor=factor)      # its clamped <defs> + root
    whole = m.CASES["logoArrowOut"]()
    body = whole[whole.index("</defs>") + len("</defs>"):]
    return svg[:svg.index("</defs>") + len("</defs>")] + body


def hires_one_piece(k=2, force=False):
    """The one-piece logo (part-clamped regions) at k x the full-canvas render: 4 px per logo @3x px for k = 2 (float32)."""
    raw = os.path.join(SCR, f"whole_same_x{k}_raw.png")
    if force or not os.path.exists(raw):
        sp = os.path.join(SCR, f"whole_same_x{k}.svg")
        open(sp, "w", encoding="utf-8").write(_sized(_whole_same_regions(_g(), 3.0 * k), CW * k, CH * k))
        svgr([dict(svg=sp, out=raw, w=CW * k, h=CH * k)])
    return pm(Image.open(raw)).astype(np.float32)


# ------------------------------------------------------------------------------------------------ geometry (from the code)
def geometry():
    """The logo's on-screen geometry in TODAY's code + data (round 1: WinLogoSequence.swift still settles at win.settleScale),
    on the 393 x 852 pt reference canvas (WinLogoSequence.layoutRect is the identity there and on every larger iPhone):
      group = ArtInk.canvas(.logoArrowOut, ink: ui.json frames.celebrate.logo) at scale 1 (k x the logo's own pt) -- the
      NEW rest (LOGO-SPEC D4: the logo rests at k, no settle); OLD settle s = k x settleScale about its centre."""
    seq = open(os.path.join(APP, "App", "FX", "WinLogoSequence.swift"), encoding="utf-8").read()
    chrome = open(os.path.join(APP, "App", "Shell", "HUD", "S2Chrome.swift"), encoding="utf-8").read()
    ui = json.load(open(os.path.join(APP, "App", "Resources", "Tuning", "ui.json")))
    b = [float(v) for v in re.search(r"\.logoArrowOut: \(([^)]*)\)", chrome).group(1).split(",")]
    ink = ui["frames"]["celebrate"]["logo"]
    win = ui["win"]
    W0, H0 = 306.0, 236.0                                          # UIArt.logoArrowOut.sizePt (MANIFEST)
    vw, vh = (b[2] - b[0]) * W0, (b[3] - b[1]) * H0
    k = min(ink[2] / vw, ink[3] / vh)
    cw, ch = W0 * k, H0 * k
    x0 = ink[0] + ink[2] / 2 - (b[0] + b[2]) / 2 * cw
    y0 = ink[1] + ink[3] / 2 - (b[1] + b[3]) / 2 * ch
    out = dict(k=k, group_pt=[x0, y0, cw, ch])
    settle = win.get("settleScale", 0.94)                          # round 1's rest (LOGO-SPEC removes the key)
    out["old"] = dict(settle=settle, s=k * settle, settled_origin_pt=[x0 + cw / 2 - cw * settle / 2, y0 + ch / 2 - ch * settle / 2])
    need = ['ArtInk.canvas(.logoArrowOut, ink: layoutRect(ui.tokens.frame("celebrate.logo"', "settle.toValue = beats.settleScale",
            "sc.toValue = 1", "signA.addSublayer(l)", "signB.addSublayer(o)"]
    if all(n in seq for n in need):                                # round 1's largest scales (the old sequence)
        big = win["outBig"]

        def vals(name):
            txt = re.search(name + r"\.values = \[([^\]]*)\]", seq).group(1)
            return [float(eval(v.replace("beats.outBig", str(big)).replace("beats.squash", str(win["squash"])), {}))
                    for v in txt.split(",")]
        pop, grow, squash = max(vals("pop")), max(vals("grow")), max(vals("sq"))
        fly = {n: max(1.0, float(s0)) for n, s0 in re.findall(r"fly\((signA|signB), .*?s0: ([\d.]+)", seq, re.S)}
        out["old"].update(outBig=big, pop=pop, grow=grow, fly=fly,
                          largest={"sign": k * max(fly["signA"], fly["signB"], squash), "letter": k * fly["signA"] * pop,
                                   "out": k * fly["signB"] * grow})
    return out


def screen_scales():            # (the old name, kept for callers)
    return geometry()


# ------------------------------------------------------------------------------------------------------- measure / files
def measure():
    """Round 2: the frames of logoPegs and the four OUT! glyphs (alpha box on logoArrowOut's grid of a 2x render, + PAD, sized
    by MULT; factor-1.5 frames on EVEN logo px = logoSignPurple's file grid), the purple face centroid x_a (LOGO-SPEC §2's
    anchor rule, logo_spec.our_geometry, on the shipped rest file) and the bend variants' bottom pad."""
    m = _g()
    frames = {}
    for pid in [PEGS] + GLYPHS:
        a = box2(fc(pid))[..., 3]
        ys, xs = np.nonzero(a > 0)
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
        f = FACTOR[pid]
        k = MULT[f]
        even = f == 1.5

        def span(lo, hi, lim):
            w = int(math.ceil((hi - lo + 2 * PAD) / k) * k)
            c = (lo + hi) / 2
            s = int(round(c - w / 2))
            if even:
                s -= s % 2
                if s + w < hi + PAD:
                    w += 2
            return max(0, min(lim - w, s)), w
        x, w = span(x0, x1, CW)
        y, h = span(y0, y1, CH)
        frames[pid] = (x, y, w, h, f)
        print(f"{pid:12s} ink x {x0}..{x1} y {y0}..{y1}  frame ({x}, {y}, {w}, {h}) x {f} -> {round(w * f)} x {round(h * f)} px")
    # x_a: the purple face centroid of the shipped rest sign (straight RGBA, the colour mask of logo_spec.our_geometry)
    _, sx, sy, sw, sh, sf = m.LOGO_PART_FRAMES["logoSignPurple"]
    ax, ay = purple_face_centroid(Image.open(os.path.join(OUT, "logoSignPurple@3x.png")))
    xa = sx + ax * sw
    print(f"logoSignPurple purple-face centroid: frac ({ax:.5f}, {ay:.5f}) -> x_a {xa:.3f} logo px, y_a {sy + ay * sh:.3f}")
    # the pad: the rest drawing's lowest ink per column (clipped at the canvas bottom), moved by the -10 deg warp, + PAD
    a = box2(fc("logoSignPurple"))[..., 3]
    kk = math.radians(10.0) / (2.0 * m.LOGO_BEND["body"])
    low = -1.0
    for c in range(CW):
        ys_ = np.nonzero(a[:, c] > 0)[0]
        if len(ys_):
            low = max(low, ys_.max() + 1 + kk * (c + 0.5 - xa) ** 2)
    k_ = geometry()["k"]
    need_geo = low + PAD - CH
    need_pt = BEND_MIN_PAD_PT * 3 / k_
    pad = int(math.ceil(max(need_geo, need_pt)))
    pad += pad % 2
    print(f"bend -10 deg: lowest ink {low:.1f} logo px (canvas {CH}) -> {need_geo:.1f} px needed; 8 pt = {need_pt:.2f} logo px "
          f"-> pad {pad} logo px = {pad * k_ / 3:.2f} pt")
    print("\nLOGO_PART_FRAMES.update({")
    layer = {PEGS: "pegs"}
    for pid, (x, y, w, h, f) in frames.items():
        print(f'    "{pid}": ("{layer.get(pid, "OUT!")}", {x}, {y}, {w}, {h}, {f}),')
    print("})")
    print(f'LOGO_BEND = dict(xa={xa:.3f}, body={m.LOGO_BEND["body"]:g}, clip={CH}, pad={pad})   # body: from `bendcal`')


def purple_face_centroid(im):
    """LOGO-SPEC's anchor of logoSignPurple (build/logo/spec/tools/logo_spec.py our_geometry): the centroid of the purple
    face pixels (a > 0.5, r > 0.45, b > 0.6, g < 0.35) as a fraction of the file (pixel centres)."""
    a = np.asarray(im.convert("RGBA")).astype(float) / 255
    H, W = a.shape[:2]
    w = ((a[..., 3] > 0.5) & (a[..., 0] > 0.45) & (a[..., 2] > 0.6) & (a[..., 1] < 0.35)).astype(float)
    yy, xx = np.mgrid[0:H, 0:W]
    return (float((xx * w).sum() / w.sum()) + 0.5) / W, (float((yy * w).sum() / w.sum()) + 0.5) / H


def frame_of(pid):
    _, x, y, w, h, f = _g().LOGO_PART_FRAMES[pid]
    return x, y, w, h, f


def shipped(pid):
    x, y, w, h, f = frame_of(pid)
    im = Image.open(os.path.join(OUT, f"{pid}@3x.png")).convert("RGBA")
    assert im.size == (round(w * f), round(h * f)), (pid, im.size, w, h, f)
    return im


def verify():
    """Every shipped part (round 1 + round 2) == a fresh WebKit render of its SVG through svg.py's own path (bit-exact); the
    SVG source file == the generator's output; no raster inside any SVG; each file is frame x factor px."""
    sys.path.insert(0, HERE)
    import svg as SVG
    m = _g()
    rep, bad = {}, []
    tmp = os.path.join(SCR, "verify")
    os.makedirs(tmp, exist_ok=True)
    for pid in ALL:
        src = open(os.path.join(UI, "src", f"{pid}.svg"), encoding="utf-8").read()
        gen_txt = m.CASES[pid]()
        x, y, w, h, f = frame_of(pid)
        r = dict(svg_matches_generator=src == gen_txt, raster_refs=src.count("<image") + src.count(".png") + src.count("data:image"),
                 passes=list(m.logo_part_passes(pid)), warp=list(warp_spec(src)) if warp_spec(src) else None,
                 file_px=list(Image.open(os.path.join(OUT, f"{pid}@3x.png")).size), frame_x_factor=[round(w * f), round(h * f)])
        if pid in PAIRS or pid in BASES or pid in FLATS:   # LOGO-ART-3/4: which glyphs does the drawing reference?
            gids = glyph_ids()
            used = sorted(set(re.findall(r'href="#([^"]+)"', src[src.index("</defs>"):])) & set(gids.values()))
            r["glyphs_drawn"] = [k for k, v in gids.items() if v in used]
            if pid in PAIRS or pid in FLATS:
                r["only_its_own_glyph"] = r["glyphs_drawn"] == [BASE_OF[pid]]
                if not r["only_its_own_glyph"]:
                    bad.append(pid)
            if pid in FLATS:                      # LOGO-ART-4: the flat's passes = its OWN extrusion (untrimmed) + face
                pv = {p: m.logo_part_svg(pid, pass_=p) for p in m.logo_part_passes(pid)}
                ep = {p: m.logo_part_svg(EXT[BASE_OF[pid]] if p == "ext" else FACE[BASE_OF[pid]]) for p in pv}
                body = lambda s: s[s.index("</defs>"):]                                          # noqa: E731
                r["passes_equal_its_pair_bodies"] = all(body(pv[p]) == body(ep[p]) for p in pv)
                r["untrimmed"] = "data-trim" not in src[:4000] and all("data-trim" not in v[:4000] for v in pv.values())
                if not (r["passes_equal_its_pair_bodies"] and r["untrimmed"]):
                    bad.append(pid)
        rep[pid] = r
        if not r["svg_matches_generator"] or r["raster_refs"] or r["file_px"] != r["frame_x_factor"]:
            bad.append(pid)
    SVG.render(ALL, out_dir=tmp)
    for pid in ALL:
        a = np.asarray(Image.open(os.path.join(tmp, f"{pid}@3x.png")).convert("RGBA")).astype(int)
        b = np.asarray(Image.open(os.path.join(OUT, f"{pid}@3x.png")).convert("RGBA")).astype(int)
        d = np.abs(a - b)
        rep[pid]["rerender_max_abs"] = int(d.max())
        rep[pid]["rerender_px_differing"] = int((d.max(-1) > 0).sum())
        if d.max() > 0:
            bad.append(pid)
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(EVID, exist_ok=True)
    json.dump(rep, open(os.path.join(EVID, "verify.json"), "w"), indent=1)
    for pid, r in rep.items():
        print(f"  {pid:22s} {r}")
    print("verify:", "OK" if not bad else f"FAIL {sorted(set(bad))}")
    if bad:
        sys.exit(1)


def glyph_ids():
    """{letter / glyph base id: its <symbol> id in the drawing} (gen_icons._logo_layers, the glyph each <use> draws)."""
    _, _, L = _g()._logo_layers()
    return {b: L[WORD_OF[b]][(LETTERS if WORD_OF[b] == "ARROW" else GLYPHS).index(b)][2] for b in BASES}


# ------------------------------------------------------------------------------------------------------ resampling helpers
def weights(n_in, n_out, off, r):
    """(n_out x n_in) exact area weights: input pixel j covers [off + j r, off + (j + 1) r) in output pixels."""
    Wm = np.zeros((n_out, n_in))
    for j in range(n_in):
        a, b = off + j * r, off + (j + 1) * r
        for i in range(max(0, int(math.floor(a))), min(n_out, int(math.ceil(b)))):
            Wm[i, j] = max(0.0, min(b, i + 1) - max(a, i))
    return Wm


def place(p, out_hw, x0, y0, r):
    """Premultiplied image `p` with its top-left at output pixel (x0, y0) (fractional), r output px per input px."""
    Wy, Wx = weights(p.shape[0], out_hw[0], y0, r), weights(p.shape[1], out_hw[1], x0, r)
    return np.einsum("yi,ijc,xj->yxc", Wy, p, Wx, optimize=True)


def area_resize(p, w, h):
    return place(p, (h, w), 0.0, 0.0, w / p.shape[1])


def stats(a, b):
    d = np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64)) * 255.0
    dm = d.max(-1)
    return dict(max=round(float(d.max()), 2), mean=round(float(d.mean()), 4), p99_9=round(float(np.percentile(dm, 99.9)), 2),
                px_gt_2=int((dm > 2).sum()), px_gt_8=int((dm > 8).sum()), px_gt_16=int((dm > 16).sum()), px=int(dm.size))


def on_bg(p, rgb):
    bg = np.ones(p.shape[:2] + (3,)) * np.array(rgb, dtype=np.float64) / 255.0
    return p[..., :3] + bg * (1.0 - p[..., 3:4])


def worst(a, b, alphas, n=6, scale=1.0, origin=(0.0, 0.0)):
    """The n largest |diff| pixels, each with the alpha of every part there (to name what the difference is)."""
    d = (np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64)) * 255.0).max(-1)
    dd, out = d.copy(), []
    for _ in range(n):
        y, x = np.unravel_index(dd.argmax(), dd.shape)
        if dd[y, x] <= 0:
            break
        lx, ly = (x + 0.5 - origin[0]) / scale, (y + 0.5 - origin[1]) / scale      # logo @3x px
        out.append(dict(at=[int(x), int(y)], logo_px=[round(lx, 1), round(ly, 1)], diff=round(float(d[y, x]), 1),
                        alpha={pid[4:]: round(float(al[y, x]), 2) for pid, al in alphas.items() if al[y, x] > 0.004}))
        dd[max(0, y - 6):y + 7, max(0, x - 6):x + 7] = 0
    return out


def settled_grid():
    """The NEW rest on the device grid (iPhone 15 @3x, reference canvas): s = k device px per logo px, the canvas's top-left
    at (45.101, 293.213) pt -> its fractional device offset, and the grid size."""
    geo = geometry()
    s = geo["k"]
    ox, oy = geo["group_pt"][0] * 3, geo["group_pt"][1] * 3
    fx, fy = ox - math.floor(ox), oy - math.floor(oy)
    hw = (int(math.ceil(CH * s + fy)) + 2, int(math.ceil(CW * s + fx)) + 2)
    return s, fx, fy, hw


# -------------------------------------------------------------------------------------------------------------- the proof
def proof():
    """Re-assembly at rest (LOGO-ART-2). Writes build/logo/art2/reassembly.json + the sheets.
      A  layering only: every part drawn by the same renderer at the same resolution on the full canvas (2x), composited in
         z order (the 13 layers; the fallback with logoOut), vs the one-piece with the same part-clamped filter regions.
      G  the glyphs: O U T ! vs logoOut -- (G1) their renders on the full canvas (2x); (G2) the SHIPPED glyph files at their
         own resolution (factor 4.0) composited on logoOut's frame vs a fresh factor-4.0 render of logoOut on that frame;
         (G3) the files on logoArrowOut's 1x grid vs the shipped logoOut shrunk the same way; (G4) at the settled on-screen
         scale, each file resampled on its own (as Core Animation does) vs logoOut's file resampled once.
      P  the pegs: (P1) the logoPegs file OVER the new logoSignPurple file (z 0.5 over z 0) on the sign's own 1.5x grid vs round 1's
         logoSignPurple file (BACKUP); (P2) the same from the renders; (P3) at the settled scale.
      C  all shipped files at their frames on the 1x grid (13 layers) vs the one-piece; per-file registration.
      D  the shipped files at the settled scale (13 layers) vs the one-piece supersampled x2 at the settled scale.
      S  seams: the largest |diff| in windows around every glyph join and around the pegs, at the settled scale."""
    m = _g()
    os.makedirs(EVID, exist_ok=True)
    rep = {"frames_logo_px": {pid: dict(zip(("x", "y", "w", "h", "factor"), frame_of(pid)), passes=list(m.logo_part_passes(pid)),
                                        z=Z[pid]) for pid in LAYERS + ["logoOut"] + BENDS}}
    s, fx, fy, hw = settled_grid()
    rep["settled"] = dict(s=s, device_offset=[fx, fy], grid=list(hw))
    ref2 = fc_whole("whole_same")
    # ---- (A) layering at 2x, 13 layers and the fallback
    acc, alph = None, {}
    for pid in LAYERS:
        p = fc(pid)
        alph[pid] = p[..., 3].copy()
        acc = p if acc is None else over(acc, p)
    rep["A_layers13_2x_vs_one_piece_same_regions"] = stats(acc, ref2)
    rep["A_layers13_2x_worst"] = worst(acc, ref2, alph, scale=2.0)
    del acc
    accF = None
    for pid in FALLBACK:
        p = fc(pid)
        accF = p if accF is None else over(accF, p)
    rep["A_fallback10_2x_vs_one_piece_same_regions"] = stats(accF, ref2)
    del accF
    # ---- (G1) the glyphs vs logoOut, renders at 2x on the full canvas
    out2 = fc("logoOut")
    g2 = None
    for pid in GLYPHS:
        p = fc(pid)
        g2 = p if g2 is None else over(g2, p)
    rep["G1_glyph_renders_2x_vs_logoOut_render_2x"] = stats(g2, out2)
    rep["G1_worst"] = worst(g2, out2, {p_: alph[p_] for p_ in GLYPHS}, scale=2.0)
    joins = glyph_joins({p_: alph[p_] for p_ in GLYPHS})
    rep["glyph_joins_logo_px"] = joins
    del out2, g2
    # ---- (G2) the shipped glyph files at factor 4.0 vs a fresh factor-4.0 render of logoOut, on the union of their frames
    fr_ = [frame_of(p_) for p_ in GLYPHS + ["logoOut"]]
    ux0, uy0 = min(f_[0] for f_ in fr_), min(f_[1] for f_ in fr_)
    ux1, uy1 = max(f_[0] + f_[2] for f_ in fr_), max(f_[1] + f_[3] for f_ in fr_)
    uw, uh = ux1 - ux0, uy1 - uy0
    rep["G2_union_frame_logo_px"] = [ux0, uy0, uw, uh]
    F4 = 4.0
    # (logoOut on one frame this wide at 8 device px per logo px would need a > 5000 px filter buffer, past WebKit's limit:
    # rendered in 3 tiles, each with its own clamped regions -- the pixels inside a viewBox are unchanged)
    cuts = [ux0, ux0 + uw // 3, ux0 + 2 * (uw // 3), ux1]
    tiles = [box2(render_part("logoOut", (a_, uy0, b_ - a_, uh), F4, f"native4_{a_}_{b_ - a_}")) for a_, b_ in zip(cuts[:-1], cuts[1:])]
    ref4 = np.concatenate(tiles, axis=1)
    del tiles
    acc4 = np.zeros_like(ref4)
    rnd4 = np.zeros_like(ref4)
    for pid in GLYPHS:
        x, y, w, h, f = frame_of(pid)
        assert f == F4
        X, Y = round((x - ux0) * F4), round((y - uy0) * F4)
        lay = np.zeros_like(ref4)
        lay[Y:Y + round(h * F4), X:X + round(w * F4)] = pm(shipped(pid))
        acc4 = over(acc4, lay)
        lay[:] = 0
        lay[Y:Y + round(h * F4), X:X + round(w * F4)] = box2(render_part(pid, (x, y, w, h), F4, "part"))
        rnd4 = over(rnd4, lay)
        del lay
    rep["G2_worst"] = worst(acc4, ref4, {}, scale=F4, origin=(-ux0 * F4, -uy0 * F4))
    ref4q = pm(to_img(ref4))                                       # the reference quantised like a file (8-bit straight)
    rep["G2_glyph_files_4x_vs_logoOut_render_4x"] = stats(acc4, ref4)
    rep["G2_glyph_files_4x_vs_logoOut_render_4x_quantised"] = stats(acc4, ref4q)
    rep["G2_glyph_renders_4x_vs_logoOut_render_4x (layering only)"] = stats(rnd4, ref4)
    g4_img, r4_img = acc4, ref4
    del rnd4, ref4q
    # ---- (G3) 1x logo grid: glyph files (1/4) vs the shipped logoOut (1/3)
    one = {pid: file_on_grid(pid) for pid in GLYPHS + ["logoOut"]}
    accg1 = np.zeros((CH, CW, 4))
    for pid in GLYPHS:
        accg1 = over(accg1, one[pid])
    rep["G3_glyph_files_1x_vs_logoOut_file_1x"] = stats(accg1, one["logoOut"])
    # ---- (G4) settled scale: each file resampled on its own, composited, vs logoOut's file resampled once
    setg = np.zeros(hw + (4,))
    for pid in GLYPHS:
        setg = over(setg, file_settled(pid, s, fx, fy, hw))
    set_out = file_settled("logoOut", s, fx, fy, hw)
    rep["G4_glyph_files_settled_vs_logoOut_file_settled"] = stats(setg, set_out)
    # (G5) against the TRUTH at the settled scale: logoOut's drawing rendered at factor 4.0 and resampled ONCE; in OUT!'s box,
    # the glyph files (each resampled on its own, then composited) vs the one-layer logoOut file (resampled once)
    truth = place(ref4, hw, fx + ux0 * s, fy + uy0 * s, s / F4)
    bx = (slice(int(uy0 * s + fy) - 2, int(uy1 * s + fy) + 3), slice(int(ux0 * s + fx) - 2, int(ux1 * s + fx) + 3))
    rep["G5_glyph_files_settled_vs_truth (OUT! box)"] = stats(setg[bx], truth[bx])
    rep["G5_logoOut_file_settled_vs_truth (OUT! box)"] = stats(set_out[bx], truth[bx])
    # ---- (P) the pegs
    px_, py_, pw, ph, pf = frame_of(PEGS)
    sx_, sy_, sw, sh, sf = frame_of("logoSignPurple")
    assert pf == sf == 1.5 and (px_ - sx_) % 2 == 0 and (py_ - sy_) % 2 == 0, "pegs off the sign's file grid"
    old_file = pm(Image.open(os.path.join(BACKUP, "out", "logoSignPurple@3x.png")))
    new_sign = pm(shipped("logoSignPurple"))
    peg_lay = np.zeros_like(new_sign)
    X, Y = round((px_ - sx_) * sf), round((py_ - sy_) * sf)
    peg_lay[Y:Y + round(ph * sf), X:X + round(pw * sf)] = pm(shipped(PEGS))
    comp = over(new_sign, peg_lay)                                 # over(dst, src): the PEGS over the sign
    rep["P1_pegs_file_over_sign_file_vs_round1_sign_file"] = stats(comp, old_file)
    rep["P1_worst"] = worst(comp, old_file, {"new_sign": new_sign[..., 3], "pegs": peg_lay[..., 3]}, scale=1.5,
                            origin=(-sx_ * 1.5, -sy_ * 1.5))
    old_render = box2(render_svg_file(os.path.join(BACKUP, "src", "logoSignPurple.svg"), round(sw * sf), round(sh * sf), "r1_sign"))
    new_render = box2(render_part("logoSignPurple", (sx_, sy_, sw, sh), sf, "part"))
    peg_r = np.zeros_like(new_render)
    peg_r[Y:Y + round(ph * sf), X:X + round(pw * sf)] = box2(render_part(PEGS, (px_, py_, pw, ph), pf, "part"))
    rep["P2_pegs_render_over_sign_render_vs_round1_sign_render (layering only)"] = stats(over(new_render, peg_r), old_render)
    rep["P1_inside_the_pegs_frame"] = stats(comp[Y:Y + round(ph * sf), X:X + round(pw * sf)],
                                            old_file[Y:Y + round(ph * sf), X:X + round(pw * sf)])
    rep["pegs_frame_file_px_in_sign"] = [X, Y, round(pw * sf), round(ph * sf)]
    set_p = over(file_settled("logoSignPurple", s, fx, fy, hw), file_settled(PEGS, s, fx, fy, hw))
    set_old = place(old_file, hw, fx + sx_ * s, fy + sy_ * s, s / sf)
    rep["P3_pegs_over_sign_files_settled_vs_round1_sign_file_settled"] = stats(set_p, set_old)
    # ---- (C) the shipped files on the 1x grid, 13 layers vs the one-piece
    for pid in LAYERS:
        if pid not in one:
            one[pid] = file_on_grid(pid)
    acc1 = np.zeros((CH, CW, 4))
    for pid in LAYERS:
        acc1 = over(acc1, one[pid])
    ref1 = box2(ref2.astype(np.float64))
    rep["C_shipped_layers13_1x_vs_one_piece_same_regions"] = stats(acc1, ref1)
    rep["C_shipped_layers13_1x_worst"] = worst(acc1, ref1, {p_: one[p_][..., 3] for p_ in LAYERS})
    reg = {}
    yy, xx = np.mgrid[0:CH, 0:CW]
    for pid in [PEGS] + GLYPHS + ["logoSignPurple"]:
        a_f, a_r = one[pid][..., 3], box2(fc(pid).astype(np.float64))[..., 3]
        c_f = (float((a_f * xx).sum() / a_f.sum()), float((a_f * yy).sum() / a_f.sum()))
        c_r = (float((a_r * xx).sum() / a_r.sum()), float((a_r * yy).sum() / a_r.sum()))
        reg[pid] = dict(centroid_shift_px=[round(c_f[0] - c_r[0], 4), round(c_f[1] - c_r[1], 4)],
                        alpha_sum_ratio=round(float(a_f.sum() / a_r.sum()), 5))
    rep["C_file_registration_vs_own_render_1x"] = reg
    # ---- (D) the shipped files at the settled scale (13 layers) vs the one-piece x2 at the settled scale
    accS = np.zeros(hw + (4,))
    setF = {}
    for pid in LAYERS:
        setF[pid] = file_settled(pid, s, fx, fy, hw)
        accS = over(accS, setF[pid])
    hi = hires_one_piece(2)
    refHi = place(hi, hw, fx, fy, s / 4)
    del hi
    rep["D_shipped_layers13_settled_vs_one_piece_x2_settled"] = stats(accS, refHi)
    # the same with the 13 parts' own renders resampled one by one (isolates the file stage)
    accR = np.zeros(hw + (4,))
    for pid in LAYERS:
        accR = over(accR, place(fc(pid), hw, fx, fy, s / 2))
    rep["D_part_renders13_settled_vs_one_piece_x2_settled"] = stats(accR, refHi)
    rep["D_shipped_vs_renders13_settled"] = stats(accS, accR)
    # ---- (S) seams: windows at the glyph joins and the pegs, settled scale
    seams = {}
    for name, j in joins.items():
        x0j, y0j, x1j, y1j = j["bbox"]
        win = (slice(int(y0j * s + fy) - 8, int(y1j * s + fy) + 9), slice(int(x0j * s + fx) - 8, int(x1j * s + fx) + 9))
        seams["glyph " + name] = dict(window_device_px=[win[1].start, win[0].start, win[1].stop, win[0].stop],
                                      vs_logoOut_file=stats(setg[win], set_out[win]),
                                      glyph_files_vs_truth=stats(setg[win], truth[win]),
                                      logoOut_file_vs_truth=stats(set_out[win], truth[win]),
                                      layers13_vs_one_piece_x2=stats(accS[win], refHi[win]))
    for i, (x0p, x1p) in enumerate(peg_x_ranges()):
        cx = int((x0p + x1p) / 2 * s + fx)
        y0d, y1d = int(py_ * s + fy), int((py_ + ph) * s + fy) + 1
        win = (slice(y0d, y1d), slice(cx - 30, cx + 30))
        seams[f"peg {i + 1}"] = dict(vs_round1_sign=stats(set_p[win], set_old[win]), vs_one_piece_x2=stats(accS[win], refHi[win]))
    rep["S_seams_settled"] = seams
    # ---- (B0) the bend variants' pipeline at 0 deg (the rest drawing on the padded frame, clipped, float 2:1 filter) vs the
    # shipped rest file: the variants warp exactly the rest drawing; the pad stays empty
    x, y, w, h, f = frame_of(BENDS[-1])
    b0 = to_img(box2(warp(pm(Image.open(_bend_src_raw())), (0.0,) + bend_spec(BENDS[-1])[1:], (x, y, w, h))))
    b0a = pm(b0)
    rH = round(sh * sf)
    rep["B0_bend0_vs_rest_file"] = stats(b0a[:rH], pm(shipped("logoSignPurple")))
    rep["B0_pad_rows_max_alpha"] = round(float(b0a[rH:, :, 3].max() * 255), 3)
    for pid in BENDS:
        a_ = np.asarray(shipped(pid))[..., 3]
        rows_ = np.nonzero(a_.max(1) > 0)[0]
        rep.setdefault("B_bottom_clearance_file_px", {})[pid] = int(a_.shape[0] - 1 - rows_[-1])
    json.dump(rep, open(os.path.join(EVID, "reassembly.json"), "w"), indent=1)
    for k_, v in rep.items():
        if k_[:2] in ("A_", "G1", "G2", "G3", "G4", "G5", "P1", "P2", "P3", "C_", "D_") and "worst" not in k_:
            print(f"{k_:70s} {v}")
    for k_, v in seams.items():
        print(f"  seam {k_:14s} {v}")
    _sheet_whole(acc1, ref1, accS, refHi, rep)
    _sheet_glyphs(g4_img, r4_img, setg, set_out, truth, joins, s, fx, fy, rep)
    _sheet_pegs(new_sign, peg_lay, comp, old_file, set_p, set_old, s, fx, fy, rep)
    _sheet_bends()


def file_on_grid(pid):
    """A shipped file shrunk by 1/factor onto logoArrowOut's 1x grid at its frame (exact area), premultiplied."""
    x, y, w, h, f = frame_of(pid)
    layer = np.zeros((CH, CW, 4))
    layer[y:y + h, x:x + w] = area_resize(pm(shipped(pid)), w, h)
    return layer


def file_settled(pid, s, fx, fy, hw):
    x, y, w, h, f = frame_of(pid)
    return place(pm(shipped(pid)), hw, fx + x * s, fy + y * s, s / f)


def glyph_joins(alphas2):
    """Where neighbouring glyphs meet (logo @3x px), from their 2x renders: the pixels where both have alpha > 0.02 -> their
    centroid ("c"), their bbox, and the top / bottom ends ("top", "bottom": the V-notches where the two outlines cross); when
    two glyphs do not overlap, the midpoint of their closest pixels (all four the same point)."""
    out = {}
    for a, b in zip(GLYPHS, GLYPHS[1:]):
        A, B = alphas2[a] > 0.02, alphas2[b] > 0.02
        both = A & B
        name = f"{NAMES[a]}|{NAMES[b]}"
        if both.any():
            ys, xs = np.nonzero(both)
            c = (round(float(xs.mean() + 0.5) / 2, 1), round(float(ys.mean() + 0.5) / 2, 1))
            it, ib = int(np.argmin(ys)), int(np.argmax(ys))
            out[name] = dict(c=c, top=(round(float(xs[it] + 0.5) / 2, 1), round(float(ys[it] + 0.5) / 2, 1)),
                             bottom=(round(float(xs[ib] + 0.5) / 2, 1), round(float(ys[ib] + 0.5) / 2, 1)),
                             bbox=[round(float(xs.min()) / 2, 1), round(float(ys.min()) / 2, 1), round(float(xs.max() + 1) / 2, 1),
                                   round(float(ys.max() + 1) / 2, 1)], overlap_px_2x=int(both.sum()))
        else:
            ya, xa = np.nonzero(A)
            yb, xb = np.nonzero(B)
            ia, ib = np.argmax(xa), np.argmin(xb)
            c = (round(float(xa[ia] + xb[ib] + 1) / 4, 1), round(float(ya[ia] + yb[ib] + 1) / 4, 1))
            out[name] = dict(c=c, top=c, bottom=c, bbox=[c[0] - 4, c[1] - 10, c[0] + 4, c[1] + 10], overlap_px_2x=0)
    return out


def peg_x_ranges():
    """The two pegs' x spans in logo @3x px (gen_icons: rr(x0, 800, x0 + 110, 935) design units, + the 3-unit stroke)."""
    sc, ox = 0.47, 306 * 1.5 - 1025 * 0.47
    return [(ox + (x0 - 1.5) * sc, ox + (x0 + 111.5) * sc) for x0 in (640, 1225)]


# ------------------------------------------------------------------------------------------------------------- the sheets
def _checker(w, h, cell=24):
    c = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    d = ImageDraw.Draw(c)
    for yy in range(0, h, cell):
        for xx in range(0, w, cell):
            if (xx // cell + yy // cell) % 2:
                d.rectangle([xx, yy, xx + cell - 1, yy + cell - 1], fill=(222, 226, 234, 255))
    return c


def _heat(a, b, gain=8):
    d = (np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64)) * 255.0).max(-1)
    return Image.fromarray(np.clip(d * gain, 0, 255).astype(np.uint8), "L").convert("RGBA")


def _on(p, rgb):
    """premultiplied -> an RGB image over a flat colour."""
    return Image.fromarray(np.clip(np.round(on_bg(np.asarray(p, np.float64), rgb) * 255), 0, 255).astype(np.uint8), "RGB")


DIM = (27, 27, 27)          # the win dim (0.894 black) over the white board


def _grid_sheet(rows, title, path, pad=16, lab=26):
    """rows = [[(PIL image, caption), ...], ...] -> one sheet."""
    W = max(sum(im.size[0] for im, _ in r) + pad * (len(r) + 1) for r in rows)
    H = 40 + sum(max(im.size[1] for im, _ in r) + lab + pad for r in rows)
    sheet = Image.new("RGB", (W, H), (236, 240, 247))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 12), title, fill=(20, 30, 60))
    y = 40
    for r in rows:
        x = pad
        for im, cap in r:
            dr.text((x, y + 6), cap, fill=(20, 30, 60))
            sheet.paste(im.convert("RGB"), (x, y + lab))
            x += im.size[0] + pad
        y += max(im.size[1] for im, _ in r) + lab + pad
    sheet.save(path, optimize=True)
    print("wrote", os.path.relpath(path, APP))


def _sheet_whole(acc1, ref1, accS, refS, rep):
    t1, tS = rep["C_shipped_layers13_1x_vs_one_piece_same_regions"], rep["D_shipped_layers13_settled_vs_one_piece_x2_settled"]

    def ck(p):
        im = to_img(p)
        base = _checker(*im.size)
        base.alpha_composite(im)
        return base
    rows = [[(ck(ref1), "one-piece (part-clamped regions), logo grid 1x"), (ck(acc1), "13 SHIPPED layers at their frames (1/factor)"),
             (_heat(acc1, ref1), f"|diff| x8  max {t1['max']} p99.9 {t1['p99_9']} >16: {t1['px_gt_16']}")],
            [(ck(refS), "one-piece x2 at the SETTLED scale (k 1.00665)"), (ck(accS), "13 files resampled ONE BY ONE, then composited"),
             (_heat(accS, refS), f"|diff| x8  max {tS['max']} p99.9 {tS['p99_9']} >16: {tS['px_gt_16']}")]]
    _grid_sheet(rows, "LOGO-ART-2 re-assembly at rest: logoSignPurple (no pegs), logoPegs, logoSignBlue, A R R O W, O U T ! "
                "(z order) vs the one-piece drawing", os.path.join(EVID, "reassembly_sheet.png"))


def _sheet_glyphs(g4, r4, setg, set_out, truth, joins, s, fx, fy, rep):
    m = _g()
    rows = []
    # the four files, each on a checker with its anchor (cream-face centroid) marked
    anchors = glyph_anchors()
    tiles = []
    for pid in GLYPHS:
        im = shipped(pid)
        base = _checker(*im.size)
        base.alpha_composite(im)
        d = ImageDraw.Draw(base)
        ax, ay = anchors[pid]["frac"]
        cx, cy = ax * im.size[0], ay * im.size[1]
        d.line([cx - 14, cy, cx + 14, cy], fill=(255, 0, 0, 255), width=2)
        d.line([cx, cy - 14, cx, cy + 14], fill=(255, 0, 0, 255), width=2)
        tiles.append((base.resize((im.size[0] // 2, im.size[1] // 2), Image.LANCZOS),
                      f"{pid} {im.size[0]}x{im.size[1]} (1/2)  + anchor"))
    rows.append(tiles)
    t = rep["G2_glyph_files_4x_vs_logoOut_render_4x"]

    def half(p):
        im = to_img(p)
        base = _checker(*im.size)
        base.alpha_composite(im)
        return base.resize((im.size[0] // 2, im.size[1] // 2), Image.LANCZOS)
    rows.append([(half(r4), "logoOut rendered at factor 4.0 (1/2)"), (half(g4), "O U T ! files composited at factor 4.0 (1/2)"),
                 (_heat(g4, r4).resize((g4.shape[1] // 2, g4.shape[0] // 2), Image.BOX),
                  f"|diff| x8  max {t['max']} p99.9 {t['p99_9']} mean {t['mean']}")])
    # the joins at 400 % (nearest), settled scale: the V-notch at the top, the middle, the V-notch at the bottom of every
    # overlap; truth (logoOut's drawing at factor 4.0, resampled once) | the 4 glyph files | the one-layer logoOut file | diff
    for bg, bname in ((DIM, "dim 0.894"), ((255, 255, 255), "white")):
        for where in ("top", "c", "bottom"):
            r = []
            for name, j in joins.items():
                jx, jy = j[where]
                cx, cy = int(jx * s + fx), int(jy * s + fy)
                box = (slice(cy - 14, cy + 14), slice(cx - 20, cx + 20))
                r += [(_on(truth[box], bg).resize((160, 112), Image.NEAREST), f"{name} {where}: truth ({bname})"),
                      (_on(setg[box], bg).resize((160, 112), Image.NEAREST), "O U T ! files"),
                      (_on(set_out[box], bg).resize((160, 112), Image.NEAREST), "logoOut file"),
                      (_heat(setg[box], truth[box]).resize((160, 112), Image.NEAREST), "|files - truth| x8")]
            rows.append(r)
    t = rep["G4_glyph_files_settled_vs_logoOut_file_settled"]
    rows.append([(_on(set_out, DIM), "logoOut file at the settled scale, over the dim"),
                 (_on(setg, DIM), "O U T ! files, each resampled on its own"),
                 (_heat(setg, set_out), f"|diff| x8  max {t['max']} p99.9 {t['p99_9']}")])
    # crop the last row to OUT!'s area
    x, y, w, h, _ = frame_of("logoOut")
    y0, y1, x0, x1 = int(y * s + fy) - 6, int((y + h) * s + fy) + 6, int(x * s + fx) - 6, int((x + w) * s + fx) + 6
    rows[-1] = [(im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.NEAREST), cap) for im, cap in rows[-1]]
    _grid_sheet(rows, "P0: OUT! as four layers (paint order O < U < T < !, earlier faces ATOP each extrusion) re-assembling "
                "logoOut; joins at 400 % (nearest) at the settled scale", os.path.join(EVID, "glyphs_sheet.png"))


def _sheet_pegs(new_sign, peg_lay, comp, old_file, set_p, set_old, s, fx, fy, rep):
    t = rep["P1_pegs_file_over_sign_file_vs_round1_sign_file"]

    def ck(p, k=2):
        im = to_img(p)
        base = _checker(*im.size)
        base.alpha_composite(im)
        return base.resize((im.size[0] // k, im.size[1] // k), Image.LANCZOS)
    rows = [[(ck(new_sign), "logoSignPurple NEW (no pegs), 1/2"), (ck(peg_lay), "logoPegs on the sign's grid, 1/2"),
             (ck(comp), "logoPegs OVER the sign (z 0.5 over z 0), 1/2"), (ck(old_file), "round 1's logoSignPurple (BACKUP), 1/2"),
             (_heat(comp, old_file).resize((comp.shape[1] // 2, comp.shape[0] // 2), Image.BOX),
              f"|diff| x8 max {t['max']} p99.9 {t['p99_9']}")]]
    # the rim where the pegs were: the new sign alone, file px, 400 % nearest, over the dim / white, next to round 1's
    sx_, sy_, sw, sh, sf = frame_of("logoSignPurple")
    for bg, bname in ((DIM, "dim"), ((255, 255, 255), "white")):
        r = []
        for i, (x0p, x1p) in enumerate(peg_x_ranges()):
            cx = int(((x0p + x1p) / 2 - sx_) * sf)
            box = (slice(40, 170), slice(cx - 70, cx + 70))
            r.append((_on(new_sign[box], bg).resize((560, 520), Image.NEAREST), f"peg {i + 1}: NEW sign rim alone ({bname}), 400 %"))
            r.append((_on(old_file[box], bg).resize((560, 520), Image.NEAREST), f"peg {i + 1}: round 1 (pegs on the sign)"))
        rows.append(r)
    # settled scale, the pegs area: sign+pegs files vs round 1 file
    x0, x1 = int(peg_x_ranges()[0][0] * s + fx) - 20, int(peg_x_ranges()[1][1] * s + fx) + 20
    _, py_, _, ph, _ = frame_of(PEGS)
    y0, y1 = int(py_ * s + fy) - 10, int((py_ + ph) * s + fy) + 40
    t3 = rep["P3_pegs_over_sign_files_settled_vs_round1_sign_file_settled"]
    rows.append([(_on(set_old[y0:y1, x0:x1], DIM).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.NEAREST), "round 1 sign, settled, 200 %"),
                 (_on(set_p[y0:y1, x0:x1], DIM).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.NEAREST), "logoPegs OVER the NEW sign, settled"),
                 (_heat(set_p[y0:y1, x0:x1], set_old[y0:y1, x0:x1]).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.NEAREST),
                  f"|diff| x8 max {t3['max']} p99.9 {t3['p99_9']}")])
    _grid_sheet(rows, "P1: logoPegs split out of logoSignPurple (the pegs were painted over the plate: the rim under them is "
                "drawn whole)", os.path.join(EVID, "pegs_sheet.png"))


def _sheet_bends():
    """The rest sign and the 4 variants: each on a checker (1/2), their silhouettes overlaid, the anchor and the pad line."""
    m = _g()
    rest = shipped("logoSignPurple")
    sx_, sy_, sw, sh, sf = frame_of("logoSignPurple")
    ax, ay = purple_face_centroid(rest)
    tiles = []
    ims = [("logoSignPurple", rest)] + [(pid, shipped(pid)) for pid in BENDS]
    Hmax = max(im.size[1] for _, im in ims)
    over_img = Image.new("RGBA", (rest.size[0], Hmax), (255, 255, 255, 255))
    cols = [(0, 0, 0), (0, 160, 255), (0, 170, 60), (255, 140, 0), (230, 0, 60)]
    ov = np.asarray(over_img).copy()
    for (pid, im), col in zip(ims, cols):
        base = _checker(im.size[0], Hmax)
        base.alpha_composite(im)
        d = ImageDraw.Draw(base)
        cx, cy = ax * sw * sf, ay * sh * sf                    # the anchor: same file px in every variant (same top-left)
        d.line([cx - 16, cy, cx + 16, cy], fill=(255, 0, 0, 255), width=2)
        d.line([cx, cy - 16, cx, cy + 16], fill=(255, 0, 0, 255), width=2)
        d.line([0, sh * sf, im.size[0], sh * sf], fill=(0, 120, 255, 255), width=1)
        cap = pid + (f" {m.LOGO_BENDS[pid]:+.1f} deg" if pid in m.LOGO_BENDS else " (rest)") + f" {im.size[0]}x{im.size[1]}"
        tiles.append((base.resize((base.size[0] // 2, base.size[1] // 2), Image.LANCZOS), cap))
        a = np.asarray(im)[..., 3]
        edge = (a > 128) & ~((np.roll(a, 1, 0) > 128) & (np.roll(a, -1, 0) > 128) & (np.roll(a, 1, 1) > 128) & (np.roll(a, -1, 1) > 128))
        ov[:a.shape[0]][edge] = col + (255,)
    rows = [tiles[:3], tiles[3:] + [(Image.fromarray(ov).resize((rest.size[0] // 2, Hmax // 2), Image.LANCZOS),
                                     "outlines (alpha 0.5): rest black, -2.5 blue, -5 green, -7.5 orange, -10 red")]]
    _grid_sheet(rows, "P2: logoSignPurple bent (LOGO-SPEC §2 warp y' = y + k (x - x_a)^2, ends down), frame padded at the bottom "
                "(blue line = the rest frame's bottom); red cross = the anchor (a fixed point of the warp)",
                os.path.join(EVID, "bend_sheet.png"))


# ------------------------------------------------------------------------------------------------------ the bend's scale
def _bend_measure(im):
    """LOGO-SPEC's own bend measurement (build/logo/spec/tools/bend.py measure: the purple face's midline turning over its
    body, the tool that measured v552's -8...-11 deg, table K) on a straight-RGBA file composited over white."""
    sys.path.insert(0, os.path.join(SPEC, "tools"))
    import bend as BM
    bg = Image.new("RGBA", (im.width, im.height + 40), (255, 255, 255, 255))
    bg.alpha_composite(im)
    return BM.measure(np.asarray(bg.convert("RGB")), y_min_pt=0)


def _bend_src_raw():
    """The raw WebKit 2x render of the rest drawing on the variants' padded frame (what every variant warps)."""
    m = _g()
    pid = BENDS[-1]
    x, y, w, h, f = frame_of(pid)
    W, H = round(w * f), round(h * f)
    raw = os.path.join(SCR, "bendcal_raw.png")
    if not os.path.exists(raw):
        sp = os.path.join(SCR, "bendcal.svg")
        open(sp, "w", encoding="utf-8").write(_sized(m.logo_part_svg(pid), W, H))
        svgr([dict(svg=sp, out=raw, w=W, h=H)])
    return raw


def bend_calibrate(target=-10.0):
    """L_body such that bend.py reads each variant at its nominal bend. §2's literal L_body = 0.70 x the frame width (698
    logo px, as build/logo/spec/tools/render_ours.py warps) reads 83 %; 0.70 x the purple face's length as bend.py measures
    it (624 logo px, body/length 0.708 as on v552) still reads ~93 % (the tool's parabola fit over the trimmed face). The
    variants are named by the metric the bend track is in, so L_body is solved on the -10 deg variant (secant, the reading is
    ~ 1 / L_body) and all four are checked. Uses the raw render of the rest drawing on the padded frame; writes nothing."""
    m = _g()
    x, y, w, h, f = frame_of(BENDS[-1])
    p0 = pm(Image.open(_bend_src_raw()))
    rest = _bend_measure(shipped("logoSignPurple"))["bend"]
    xa, clip = float(m.LOGO_BEND["xa"]), float(m.LOGO_BEND["clip"])

    def reading(b, L):
        return _bend_measure(to_img(box2(warp(p0, (b, xa, L, clip), (x, y, w, h)))))["bend"] - rest
    L0, r0 = 0.70 * 698, reading(target, 0.70 * 698)
    L1 = L0 * r0 / target
    r1 = reading(target, L1)
    L2 = L1 + (target - r1) * (L1 - L0) / (r1 - r0)
    L2 = round(L2, 1)
    rows = {"rest_turning": round(rest, 3), "L_body_literal_0.70x698": {"L": L0, "reading_at_-10": round(r0, 3)},
            "L_body": L2, "readings": {}}
    for b in (-2.5, -5.0, -7.5, -10.0):
        rows["readings"][b] = round(reading(b, L2), 3)
    print(json.dumps(rows, indent=1))
    json.dump(rows, open(os.path.join(EVID, "bend_calibration.json"), "w"), indent=1)
    return rows


# ------------------------------------------------------------------------------------------------------------- the fringe
def fringe(ids=None, neg="logoOutO", title="LOGO-ART-2 parts"):
    """Premultiplied-edge check of every round-2 file (+ the re-exported logoSignPurple; `ids` = another list, e.g. the
    round-3 pairs, command fringe3). For a constant background,
    filter-then-composite must equal composite-then-filter: the shipped (straight-alpha, 8-bit) part composited over
    black / white vs the SAME part's raw 2x render (passes composed, bend warped) composited first and area-filtered after.
    A straight-alpha resize (the fringe bug) is run as the negative control."""
    os.makedirs(EVID, exist_ok=True)
    rep, tiles = {}, []
    for pid in (ids or ["logoSignPurple"] + NEW):
        x, y, w, h, f = frame_of(pid)
        rawp = render_part(pid, (x, y, w, h), f, "part")
        ship = shipped(pid)
        assert rawp.shape[:2] == (ship.size[1] * 2, ship.size[0] * 2), (pid, rawp.shape, ship.size)
        straight = Image.merge("RGBA", [c.resize(ship.size, Image.BOX) for c in to_img(rawp).split()])   # negative control
        r = {}
        edge = (np.asarray(ship)[..., 3] > 0) & (np.asarray(ship)[..., 3] < 255)
        for bgname, rgb in (("black", (0, 0, 0)), ("white", (255, 255, 255))):
            truth = box2(np.concatenate([on_bg(rawp, rgb), np.ones(rawp.shape[:2] + (1,))], -1))[..., :3] * 255
            got = on_bg(pm(ship), rgb) * 255
            bad = on_bg(pm(straight), rgb) * 255
            r[bgname] = dict(edge_px=int(edge.sum()), max=round(float(np.abs(got - truth).max()), 2),
                             mean_edge=round(float(np.abs(got - truth)[edge].mean()), 3),
                             negative_control_max=round(float(np.abs(bad - truth).max()), 2),
                             negative_control_mean_edge=round(float(np.abs(bad - truth)[edge].mean()), 3))
        rep[pid] = r
        del rawp
        a = np.asarray(ship)[..., 3]
        H_, W_ = a.shape
        rows_ = [H_ // 2] if BASE_OF.get(pid, pid) not in BASES else [H_ // 3, 2 * H_ // 3]
        spots = []
        for yy in rows_:
            xs = np.nonzero(a[yy] > 0)[0]
            if len(xs):
                spots += [(int(xs[0]), yy), (int(xs[-1]), yy)]
        xs = np.nonzero(a.max(0) > 0)[0]
        cx = int(xs.mean()) if len(xs) else W_ // 2
        ys = np.nonzero(a[:, cx] > 0)[0]
        if len(ys):
            spots.append((cx, int(ys[0])))
        if pid in BENDS:
            ys = np.nonzero(a[:, int(0.9 * W_)] > 0)[0]
            if len(ys):
                spots.append((int(0.9 * W_), int(ys[-1])))
        for (sx, sy) in spots[:4]:
            box = (max(0, sx - 24), max(0, sy - 16), max(0, sx - 24) + 48, max(0, sy - 16) + 32)
            for rgb in ((0, 0, 0), (255, 255, 255)):
                t = Image.new("RGBA", (48, 32), rgb + (255,))
                t.alpha_composite(ship.crop(box))
                tiles.append((pid, rgb, t.resize((192, 128), Image.NEAREST)))
        if pid == neg:
            sx, sy = spots[0]
            box = (max(0, sx - 24), max(0, sy - 16), max(0, sx - 24) + 48, max(0, sy - 16) + 32)
            for rgb in ((0, 0, 0), (255, 255, 255)):
                t = Image.new("RGBA", (48, 32), rgb + (255,))
                t.alpha_composite(straight.crop(box))
                tiles.append(("NEGATIVE CONTROL (straight-alpha resize)", rgb, t.resize((192, 128), Image.NEAREST)))
    json.dump(rep, open(os.path.join(EVID, "fringe.json"), "w"), indent=1)
    for pid, r in rep.items():
        print(f"  {pid:22s} {r}")
    cols = 6
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * 212 + 20, rows * 158 + 40), (236, 240, 247))
    dr = ImageDraw.Draw(sheet)
    dr.text((10, 8), f"{title}: silhouette edges at 400 % (nearest), over black and over white", fill=(20, 30, 60))
    for i, (pid, rgb, t) in enumerate(tiles):
        cx, cy = 10 + (i % cols) * 212, 30 + (i // cols) * 158
        sheet.paste(t.convert("RGB"), (cx, cy + 14))
        dr.text((cx, cy), f"{pid} / {'black' if rgb == (0, 0, 0) else 'white'}", fill=(20, 30, 60))
    sheet.save(os.path.join(EVID, "fringe_sheet.png"), optimize=True)
    print("wrote", os.path.relpath(os.path.join(EVID, "fringe_sheet.png"), APP))


# ------------------------------------------------------------------------------------------------ anchors / never upscale
def glyph_anchors():
    """Each OUT! glyph's anchor = its CREAM FACE's centroid, by LOGO-SPEC's own colour rule (logo_spec.our_geometry: the face
    pixels with alpha > 0.6, max channel > 0.93 and max - min < 0.06 -- the cream face without its lilac-shaded lower bevel,
    as v552's glyph centroids were measured on its cream faces, REFERENCE §0) applied to the glyph's OWN face pass (the face
    element alone through its inflation filter; no neighbour's pixels, no cut), on the part's frame at its factor.
    -> {pid: {frac, logo_px, ref_pt, alpha_frac (the face pass's plain alpha centroid, for the record)}}
    (+ `logo_spec_mask_ref_pt` = LOGO-SPEC's approximation on the one-piece logoOut cut at x 478 / 905 / 1262, for comparison)."""
    m = _g()
    geo = geometry()
    gx, gy, gw, gh = geo["group_pt"]
    out = {}
    for pid in GLYPHS:
        x, y, w, h, f = frame_of(pid)
        W, H = round(w * f), round(h * f)
        s = m.logo_part_svg(pid, frame=(x, y, w, h), factor=f, pass_="face") if m.logo_part_passes(pid) else None
        if s is None:                         # O is one pass: draw its face element alone the same way
            d, head, L = m._logo_layers()
            exts, face, gid, sw = L["OUT!"][0]
            full = m.logo_part_svg(pid, frame=(x, y, w, h), factor=f)
            body_at = full.index("</defs>") + len("</defs>")
            s = full[:body_at] + "\n" + "\n".join([head, face, "</g>"]) + "\n</svg>\n"
        raw = os.path.join(SCR, f"{pid}_faceonly_raw.png")
        if not os.path.exists(raw):
            sp = os.path.join(SCR, f"{pid}_faceonly.svg")
            open(sp, "w", encoding="utf-8").write(_sized(s, W, H))
            svgr([dict(svg=sp, out=raw, w=W, h=H)])
        p = box2(pm(Image.open(raw)))
        im = np.asarray(to_img(p)).astype(float) / 255
        a = p[..., 3]
        mx, mn = im[..., :3].max(2), im[..., :3].min(2)
        cream = (im[..., 3] > 0.6) & (mx > 0.93) & (mx - mn < 0.06)
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        fr = (float(xx[cream].mean() + 0.5) / a.shape[1], float(yy[cream].mean() + 0.5) / a.shape[0])
        fa = (float((a * (xx + 0.5)).sum() / a.sum()) / a.shape[1], float((a * (yy + 0.5)).sum() / a.sum()) / a.shape[0])
        lx, ly = x + fr[0] * w, y + fr[1] * h
        out[pid] = dict(frac=[round(fr[0], 5), round(fr[1], 5)], logo_px=[round(lx, 3), round(ly, 3)],
                        ref_pt=[round(gx + lx / CW * gw, 3), round(gy + ly / CH * gh, 3)],
                        alpha_frac=[round(fa[0], 5), round(fa[1], 5)],
                        alpha_ref_pt=[round(gx + (x + fa[0] * w) / CW * gw, 3), round(gy + (y + fa[1] * h) / CH * gh, 3)],
                        cream_px=int(cream.sum()))
    # LOGO-SPEC's approximation (colour mask on the one-piece logoOut, cut at x 478 / 905 / 1262 file px), for comparison
    im = np.asarray(shipped("logoOut")).astype(float) / 255
    ox, oy, ow, oh, of = frame_of("logoOut")
    mx, mn = im[..., :3].max(2), im[..., :3].min(2)
    face = (im[..., 3] > 0.6) & (mx > 0.93) & (mx - mn < 0.06)
    yy, xx = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    cuts = [0, 478, 905, 1262, im.shape[1]]
    for pid, (c0, c1) in zip(GLYPHS, zip(cuts[:-1], cuts[1:])):
        m_ = face & (xx >= c0) & (xx < c1)
        lx, ly = ox + (xx[m_].mean() + 0.5) / of, oy + (yy[m_].mean() + 0.5) / of
        out[pid]["logo_spec_mask_ref_pt"] = [round(gx + lx / CW * gw, 3), round(gy + ly / CH * gh, 3)]
    return out


def pegs_anchor():
    a = np.asarray(shipped(PEGS))[..., 3].astype(float)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    return (float((a * (xx + 0.5)).sum() / a.sum()) / a.shape[1], float((a * (yy + 0.5)).sum() / a.sum()) / a.shape[0])


FAM = {
    'linear': lambda u: u,
    'sineIn': lambda u: 1 - np.cos(u * np.pi / 2),
    'sineOut': lambda u: np.sin(u * np.pi / 2),
    'sineInOut': lambda u: (1 - np.cos(np.pi * u)) / 2,
    'quadIn': lambda u: u * u,
    'quadOut': lambda u: 1 - (1 - u) ** 2,
    'quadInOut': lambda u: np.where(u < 0.5, 2 * u * u, 1 - 2 * (1 - u) ** 2),
    'cubicIn': lambda u: u ** 3,
    'cubicOut': lambda u: 1 - (1 - u) ** 3,
    'cubicInOut': lambda u: np.where(u < 0.5, 4 * u ** 3, 1 - (2 - 2 * u) ** 3 / 2),
}


def ev(track, t):
    """A LOGO-SPEC track {kf: [t0, v0, ...], ease: [...]} at times t (build/logo/spec/tools/logo_spec.ev)."""
    kt, kv = np.array(track["kf"][0::2], float), np.array(track["kf"][1::2], float)
    t = np.atleast_1d(np.asarray(t, float))
    out = np.empty_like(t)
    for n, x in enumerate(t):
        if x <= kt[0]:
            out[n] = kv[0]
        elif x >= kt[-1]:
            out[n] = kv[-1]
        else:
            i = int(np.searchsorted(kt, x, side="right") - 1)
            u = (x - kt[i]) / (kt[i + 1] - kt[i])
            out[n] = kv[i] + (kv[i + 1] - kv[i]) * float(FAM[track["ease"][i]](u))
    return out


def largest_scales(dt=1 / 1200):
    """Every part's largest on-screen scale relative to its settled size over the LOGO-SPEC sequence (winlogo_keyframes.json):
    group.s x its own (s, or sx and sy per axis) x its parent's (the blue sign has no scale), while visible. The bend variants
    show only while bend <= -1.25 deg: the nearest of the 5 images rest / -2.5 / -5 / -7.5 / -10 (LOGO-ART-3 fix: round 2
    counted |bend| >= 1.25, i.e. also the POSITIVE +1.5 deg overshoot at W+0.986...1.03, which has no variant -- the rest
    drawing is the nearest there). The echo copies reuse the glyph files at t - delay."""
    kf = json.load(open(os.path.join(SPEC, "winlogo_keyframes.json")))
    tt = np.round(np.arange(0.0, 2.40 + 1e-9, dt), 6)
    g = ev(kf["group"]["s"], tt)
    out = {}
    for pid, p in kf["parts"].items():
        tr = p["tracks"]
        one = np.ones_like(tt)
        sx = ev(tr["sx"], tt) if "sx" in tr else ev(tr["s"], tt) if "s" in tr else one
        sy = ev(tr["sy"], tt) if "sy" in tr else ev(tr["s"], tt) if "s" in tr else one
        if p["parent"] != "group":
            par = kf["parts"][p["parent"]]["tracks"]
            ps = ev(par["s"], tt) if "s" in par else one
            sx, sy = sx * ps, sy * ps
        vis = tt >= p["visibleFrom"] - 1e-9
        ax, ay = (g * sx)[vis], (g * sy)[vis]
        i, j = int(np.argmax(ax)), int(np.argmax(ay))
        out[pid] = dict(x=round(float(ax[i]), 4), x_at=round(float(tt[vis][i]), 4), y=round(float(ay[j]), 4),
                        y_at=round(float(tt[vis][j]), 4))
        if pid == "logoSignPurple":
            b = ev(tr["bend"], tt)
            vb = vis & (b <= -1.25)
            bx, by = (g * sx)[vb], (g * sy)[vb]
            i, j = int(np.argmax(bx)), int(np.argmax(by))
            out["bend variants"] = dict(x=round(float(bx[i]), 4), x_at=round(float(tt[vb][i]), 4), y=round(float(by[j]), 4),
                                        y_at=round(float(tt[vb][j]), 4), shown=[round(float(tt[vb][0]), 4), round(float(tt[vb][-1]), 4)])
    return out


def upscale():
    """LOGO-SPEC table U re-computed with the real files: at each part's largest on-screen scale (iPhone 15 @3x, layoutRect
    k = 1), screen px / file px per axis = settled pt x 3 x scale / file px must be <= 1.0."""
    geo = geometry()
    k = geo["k"]
    gw, gh = geo["group_pt"][2], geo["group_pt"][3]
    L = largest_scales()
    rows, bad = {}, []
    for pid in LAYERS + ["logoOut"] + BENDS + PAIRS + FLATS:
        x, y, w, h, f = frame_of(pid)
        im = shipped(pid)
        set_w, set_h = w / CW * gw, h / CH * gh                     # settled size, pt (the new rest)
        sc = L["bend variants"] if pid in BENDS else L[BASE_OF.get(pid, pid)]
        rx, ry = set_w * 3 * sc["x"] / im.size[0], set_h * 3 * sc["y"] / im.size[1]
        need = [int(math.ceil(set_w * 3 * sc["x"])), int(math.ceil(set_h * 3 * sc["y"]))]
        rows[pid] = dict(settled_pt=[round(set_w, 2), round(set_h, 2)], file_px=list(im.size),
                         file_over_settled=round(im.size[0] / (set_w * 3), 3), largest_scale=[sc["x"], sc["y"]],
                         at=[sc["x_at"], sc["y_at"]], min_file_px_for_1to1=need,
                         screen_px_per_file_px=[round(rx, 3), round(ry, 3)], ok=max(rx, ry) <= 1.0)
        if BASE_OF.get(pid, pid) in GLYPHS:
            rows[pid]["table_U_minimum_px"] = {"logoOutO": [485, 563], "logoOutU": [424, 537], "logoOutT": [348, 530],
                                               "logoOutBang": [192, 558]}[BASE_OF.get(pid, pid)]
            rows[pid]["meets_table_U_minimum"] = im.size[0] >= rows[pid]["table_U_minimum_px"][0] and \
                im.size[1] >= rows[pid]["table_U_minimum_px"][1]
            if not rows[pid]["meets_table_U_minimum"]:
                bad.append(pid)
        if pid in BENDS:
            rows[pid]["shown"] = L["bend variants"]["shown"]
        if not rows[pid]["ok"]:
            bad.append(pid)
    rows["_k"] = k
    json.dump(rows, open(os.path.join(EVID, "upscale.json"), "w"), indent=1)
    print(f"{'part':22s} {'settled pt':>16s} {'file px':>11s} {'file/settled':>12s} {'largest (x, y) @W+':>30s} {'screen/file':>14s}")
    for pid, r in rows.items():
        if pid.startswith("_"):
            continue
        print(f"{pid:22s} {r['settled_pt'][0]:7.2f} x {r['settled_pt'][1]:6.2f} {r['file_px'][0]:5d} x {r['file_px'][1]:4d} "
              f"{r['file_over_settled']:12.3f}   {r['largest_scale'][0]:.3f} @{r['at'][0]:.3f}, {r['largest_scale'][1]:.3f} "
              f"@{r['at'][1]:.3f}   {r['screen_px_per_file_px'][0]:.3f} {r['screen_px_per_file_px'][1]:.3f}"
              + ("" if r["ok"] else "  UPSCALED") + (f"  table-U min {r['table_U_minimum_px']} "
                                                      f"{'met' if r['meets_table_U_minimum'] else 'NOT MET'}"
                                                      if "table_U_minimum_px" in r else ""))
    print("upscale:", "OK" if not bad else f"FAIL {bad}")
    if bad:
        sys.exit(1)
    return rows


# ------------------------------------------------------------------------------------------------------------ the manifest
PURPOSE = {
    "logoSignPurple": "win logo part: the purple ARROW-shaped sign (white rim, grey underside), WITHOUT the pegs (logoPegs) and "
                      "WITHOUT the 'OUT!' word",
    "logoSignBlue": "win logo part: the arched blue top sign (white rim, grey underside, its drop shadow), WITHOUT the ARROW letters",
    "logoLetterA": "win logo part: the letter A of ARROW (yellow bubble face + orange extrusion), pops on its own",
    "logoLetterR1": "win logo part: the first R of ARROW (yellow bubble face + orange extrusion), pops on its own",
    "logoLetterR2": "win logo part: the second R of ARROW (yellow bubble face + orange extrusion), pops on its own",
    "logoLetterO": "win logo part: the letter O of ARROW (yellow bubble face + orange extrusion), pops on its own",
    "logoLetterW": "win logo part: the letter W of ARROW (yellow bubble face + orange extrusion), pops on its own",
    "logoOut": "win logo part: the white 'OUT!' word in ONE layer (cream faces + lilac extrusion) -- Loading and the fallback; "
               "the celebration animates OUT! as 4 pairs logoOutOExt/Face, U, T, Bang (LOGO-ART-3)",
    PEGS: "win logo part: the two grey pegs that hang the blue sign over the purple arrow sign (between the two signs); they "
          "slide down from behind the blue sign",
    "logoOutO": "win logo part: the O of 'OUT!' (cream bubble face + lilac extrusion), animated on its own",
    "logoOutU": "win logo part: the U of 'OUT!' (cream bubble face + lilac extrusion), animated on its own",
    "logoOutT": "win logo part: the T of 'OUT!' (cream bubble face + lilac extrusion), animated on its own",
    "logoOutBang": "win logo part: the ! of 'OUT!' (cream bubble face + lilac extrusion), animated on its own",
    **{pid: f"win logo part: logoSignPurple bent {_b:+.1f} deg (a stronger arch, both ends down) for the rising arrow sign"
       for pid, _b in zip(BENDS, (-2.5, -5.0, -7.5, -10.0))},
}
_WHAT = {"logoLetterA": "the letter A of ARROW", "logoLetterR1": "the first R of ARROW", "logoLetterR2": "the second R of ARROW",
         "logoLetterO": "the letter O of ARROW", "logoLetterW": "the letter W of ARROW", "logoOutO": "the O of 'OUT!'",
         "logoOutU": "the U of 'OUT!'", "logoOutT": "the T of 'OUT!'", "logoOutBang": "the ! of 'OUT!'"}
for _b in BASES:
    PURPOSE[_b] += f" -- SUPERSEDED in the animation by the pair {EXT[_b]} + {FACE[_b]} (LOGO-ART-3; kept, not animated)"
    _col = ("orange", "yellow") if WORD_OF[_b] == "ARROW" else ("lilac", "cream")
    PURPOSE[EXT[_b]] = (f"win logo part: {_WHAT[_b]} -- its {_col[0]} 3-D EXTRUSION alone (the side + its outline), the lower "
                        f"layer of a pair with {FACE[_b]} (one shared transform)")
    PURPOSE[FACE[_b]] = (f"win logo part: {_WHAT[_b]} -- its {_col[1]} bubble FACE alone (the face + its outline and bevel), the "
                         f"upper layer of a pair with {EXT[_b]} (one shared transform)")
    if _b in LETTERS:
        PURPOSE[FLAT[_b]] = (f"win logo part: {_WHAT[_b]} as ONE flat sprite (its yellow face over its own whole orange "
                             f"extrusion), shown instead of the pair {EXT[_b]} + {FACE[_b]} while the letter fades in "
                             f"(opacity < 1)")
Z_ORDER_TXT = ("z = LOGO-SPEC §2 paint order (0 bottom; LOGO-ART-3/4): logoSignPurple 0, logoPegs 0.5 (the pegs OVER the "
               "purple sign), logoSignBlue 1; inside the blue sign ARROW's 5 extrusions logoLetterAExt R1Ext R2Ext OExt WExt "
               "2.0-2.4 UNDER its 5 faces logoLetterAFace ... WFace 3.0-3.4 (while a letter's opacity < 1 its flat sprite "
               "logoLetter<X>Flat stands in its Face slot and its pair is hidden: ruling 36 (b)); OUT!'s 4 extrusions "
               "logoOutOExt UExt TExt BangExt 7-10 UNDER its 4 faces logoOutOFace ... BangFace 11-14, all 8 at opacity 1 "
               "inside ONE container outGroup that carries OUT!'s opacity with GROUP opacity (ruling 36 (a)); the echo = "
               "one group-opacity container outEcho of the same 8 files under outGroup; the two layers of a pair share ONE "
               "transform (same anchor, same values; the echo copies too); logoOut 7 when it stands in for the 8 OUT! "
               "layers (fallback). Rounds 1-2's composed letters / glyphs (logoLetterA ... W z 2-6, logoOutO ... Bang z "
               "7-10) are kept but no longer animated")


def manifest_entries(only=None):
    """(Re)writes the logo group's entries in art/MANIFEST.json (in place when present): the round-2 parts and the round-3
    pairs (LOGO-ART-3) from gen_icons.LOGO_PART_FRAMES + the anchors + LOGO-SPEC's largest scales (winlogo_keyframes.json),
    and the first 8 parts' notes (and logoSignPurple's purpose) moved to the new rest; the first 8's size_pt / render_scale /
    anchor_pt / file stay (UIArt.sizePt must not change) -- EXCEPT logoSignPurple (LOGO-SPEC-FIX M3, 2026-09-27): it ships
    on its bend variants' padded frame and takes their size / anchor fields (the settled size at the new rest, anchor_frac,
    anchor_ref_pt): the arrow-sign layer's 5 contents share one frame. only = an iterable of ids: rewrite just those."""
    sys.path.insert(0, os.path.join(APP, "art", "tools"))
    import manifest as MF
    g = _g()
    geo = geometry()
    k = geo["k"]
    old = geo["old"]
    s_old = old["s"]
    grow = k / s_old                                          # 1.0638: the new settled size / the old
    L = largest_scales()
    gw, gh = geo["group_pt"][2], geo["group_pt"][3]
    anchors = glyph_anchors() if only is None or set(only) & set(GLYPHS + OUT_PAIRS) else None
    pa = pegs_anchor()
    sa = purple_face_centroid(shipped("logoSignPurple"))
    m = MF.load()
    byid = {e["id"]: e for e in m["entries"]}
    ref = dict(byid["logoArrowOut"]["ref"])
    print(f"logoArrowOut at rest: x{k:.6f} (new rest), old settle x{s_old:.6f}; new / old = {grow:.4f}")
    common_tail = (" Area-filtered 2:1 from the WebKit 2x render, premultiplied (no ringing halo, no dark fringe; "
                   "build/logo/art2/fringe.json, pairs + flats build/logo/art4/fringe.json). Shrunk on screen: the layer "
                   "wants minificationFilter .trilinear.")
    kf = json.load(open(os.path.join(SPEC, "winlogo_keyframes.json")))

    def upscale_txt(pid, f):
        sc = L["bend variants"] if pid in BENDS else L[BASE_OF.get(pid, pid)]
        big = max(sc["x"], sc["y"])
        at = sc["x_at"] if sc["x"] >= sc["y"] else sc["y_at"]
        return big, at, k * big / f
    # ---- the first 8: notes (+ logoSignPurple's purpose / variants); the fields that feed UIArt stay
    for pid in IDS_R1:
        if only is not None and pid not in only:
            continue
        e = byid[pid]
        x, y, w, h, f = frame_of(pid)
        big, at, r = upscale_txt(pid, f)
        set_w, set_h = w / CW * gw, h / CH * gh
        extra = ""
        if pid in LETTERS or pid == "logoOut":
            e["purpose"] = PURPOSE[pid]
            if pid in LETTERS:
                e["pair"] = [EXT[pid], FACE[pid]]
        if pid == "logoSignPurple":
            e["purpose"] = PURPOSE[pid]
            e["variants"] = list(BENDS)
            pad = g.LOGO_PAD[pid]
            extra = (" LOGO-ART-2 P1 (2026-09-27): RE-EXPORTED WITHOUT THE TWO PEGS (now logoPegs, z 0.5); the pegs were "
                     "painted over the plate, so the plate's rim under them is drawn whole (no gap / seam; logoPegs OVER this "
                     "file (pegs z 0.5 above this sign's z 0) = round 1's file within 8-bit rounding, build/logo/art2/"
                     "reassembly.json P1). Its 4 bend variants (-2.5 / -5 / -7.5 / -10 deg) are logoSignPurpleBend25 / 50 / "
                     f"75 / 100 (LOGO-SPEC §2 'the bend'). LOGO-SPEC-FIX M3 (2026-09-27): RE-EXPORTED ON THE BEND VARIANTS' "
                     f"PADDED FRAME ({x}, {y}, {w}, {h}) = the drawing's own frame + {pad} logo px of TRANSPARENT rows at the "
                     f"bottom (gen_icons.LOGO_PAD, svg.py data-pad: the render is unchanged, its pixels identical to round 2's "
                     f"1047 x 564 file inside; build/logo/art4/specfix/signswap.json), so the arrow-sign layer's 5 contents "
                     f"(rest + 4 bends) share ONE frame, ONE anchor and ONE bounds: a contents-only discrete swap is exact "
                     f"(round 2's rest frame was 36 px shorter: a contents-only swap squashed the sign and jumped ~7.9 pt). "
                     f"Its size_pt / anchor_pt / render_scale / size_px / anchor_frac / anchor_ref_pt now follow the variants' "
                     f"convention (the SETTLED size at the new rest; anchor = the purple face's centroid "
                     f"({sa[0]:.5f}, {sa[1]:.5f}) of this frame, the variants' anchor point).")
            rs = round(f / k, 4)
            e["size_pt"] = [round(set_w, 4), round(set_h, 4)]
            e["render_scale"] = rs
            e["file_px"] = [round(w * f), round(h * f)]
            e["anchor_pt"] = [round(x / CW * gw, 4), round(y / CH * gh, 4)]
            e["logo_rect"] = [round(x / CW, 6), round(y / CH, 6), round(w / CW, 6), round(h / CH, 6)]
            e["anchor_frac"] = [round(sa[0], 5), round(sa[1], 5)]
            e["anchor_ref_pt"] = [round((x + sa[0] * w) / CW * gw + geo["group_pt"][0], 3),
                                  round((y + sa[1] * h) / CH * gh + geo["group_pt"][1], 3)]
            e["size_px"] = [round(v * 3) for v in e["size_pt"]]
        if pid == "logoOut":
            extra = (" LOGO-ART-3 (2026-09-27): the celebration animates OUT! as four PAIRS logoOutOExt / logoOutOFace, U, T, "
                     "Bang (extrusions z 7-10 under faces z 11-14; they re-assemble this file at rest, build/logo/art3/"
                     "reassembly.json); this one-layer file stays for Loading and as the fallback.")
        if pid in LETTERS[1:]:
            extra = (" Rendered in 3 passes (its extrusion, the faces of the letters before it, its own face) and composed "
                     "as face OVER (earlier faces ATOP extrusion) -- where letters touch, this extrusion lies under the "
                     "earlier face (the one-piece paints every extrusion before every face); the earlier face's pixels "
                     "over this extrusion ride with this letter.")
        if pid in LETTERS:
            extra += (f" LOGO-ART-3 (2026-09-27): SUPERSEDED IN THE ANIMATION by the pair {EXT[pid]} + {FACE[pid]} (the "
                      "letters overshoot and tilt apart at W+0.69-1.27, so any neighbour-face pixels baked into a composed "
                      "letter travel with the wrong letter; and every ARROW extrusion must lie under every ARROW face, A "
                      "included). Kept (not animated); build/logo/art3/motion.json.")
        e["notes"] = (
            f"OWNER P0 19:40 (b): exported STRAIGHT FROM THE SVG drawing of logoArrowOut (gen_icons._logo_layers, never cut "
            f"from the PNG) so the win animation only ever scales it DOWN. NEW REST (LOGO-SPEC 2026-09-27, D4; LOGO-ART-2 "
            f"§9.4): the logo now rests at celebrate.logo's k {k:.5f} (ArtInk box of logoArrowOut on ui.json celebrate.logo; "
            f"no win.settleScale 0.94 any more), so this part's SETTLED on-screen size is {set_w:.2f} x {set_h:.2f} pt on the "
            + (f"393 x 852 reference canvas = size_pt (LOGO-SPEC-FIX M3: this part's size fields follow its bend variants, "
               f"the settled size at the new rest): render_scale " if pid == "logoSignPurple" else
               f"393 x 852 reference canvas = {grow:.4f} x size_pt. size_pt / anchor_pt / render_scale are kept at the OLD "
               f"settle (x{s_old:.5f} of the logo's pt; they feed UIArt.sizePt, which must not move): render_scale ") +
            f"{e.get('render_scale')} x size_pt = the file ({f}x logoArrowOut@3x) = {f / k:.3f}x the new settled size. Its "
            f"largest on-screen size in LOGO-SPEC is x{big:.3f} of the settled size (W+{at:.3f}; table U, "
            f"build/logo/art4/upscale.json): {r:.3f} screen px per file px, never upscaled. PLACE BY logo_rect (exact): the "
            f"frame as fractions of the logoArrowOut canvas (x, y, w, h), the same space as LogoParts.Part.rect; frame in "
            f"logoArrowOut @3x px = ({x}, {y}, {w}, {h}); at rest the canvas is (45.101, 293.213, 308.034 x 237.569) pt. "
            f"{Z_ORDER_TXT}; composited in that order at their frames the parts re-assemble the one-piece drawing "
            f"(art/ui/tools/logo_parts.py proof3 -> build/logo/art3/reassembly.json; round 2: build/logo/art2/, round 1: "
            f"build/logo/art/)."
            + extra + common_tail)
    # ---- the round-2 parts
    order_after = "logoOut"
    for pid in NEW:
        if only is not None and pid not in only:
            continue
        x, y, w, h, f = frame_of(pid)
        big, at, r = upscale_txt(pid, f)
        set_w, set_h = w / CW * gw, h / CH * gh
        rs = round(f / k, 4)
        e = {"id": pid, "family": "svg", "route": "B2", "group": "logo", "purpose": PURPOSE[pid],
             "screen": "win celebration (WinLogoSequence), above the dim",
             "size_pt": [round(set_w, 4), round(set_h, 4)], "render_scale": rs, "file_px": [round(w * f), round(h * f)],
             "anchor_pt": [round(x / CW * gw, 4), round(y / CH * gh, 4)],
             "logo_rect": [round(x / CW, 6), round(y / CH, 6), round(w / CW, 6), round(h / CH, 6)], "z": Z[pid]}
        if pid in GLYPHS:
            a = anchors[pid]
            e["anchor_frac"], e["anchor_ref_pt"] = a["frac"], a["ref_pt"]
            i = GLYPHS.index(pid)
            detail = (f"LOGO-ART-2 P0 (LOGO-SPEC §9.1, 2026-09-27): the {NAMES[pid]} of 'OUT!' split out of logoOut, exported "
                      f"STRAIGHT FROM THE SVG drawing (gen_icons._logo_layers; never cut from a PNG). " +
                      ("One pass (extrusion + face), as logoLetterA. " if i == 0 else
                       f"Rendered in 3 passes (its extrusion, the faces of the glyphs before it ({', '.join(NAMES[p] for p in GLYPHS[:i])}), "
                       f"its own face) composed as face OVER (earlier faces ATOP extrusion), as ARROW's R1-W: where glyphs "
                       f"touch, this extrusion lies under the earlier face; that face's pixels over this extrusion ride with this "
                       f"glyph. ") +
                      f"Paint order O < U < T < ! (z {Z[pid]}): composited at their frames the four re-assemble logoOut "
                      f"(build/logo/art2/reassembly.json G1-G4, glyphs_sheet.png). anchor_frac = the CREAM FACE's centroid "
                      f"as a fraction of this frame = the layer's anchorPoint: LOGO-SPEC's own colour rule (alpha > 0.6, max "
                      f"channel > 0.93, max - min < 0.06: the cream face without its lilac-shaded lower bevel, as v552's glyph "
                      f"centroids were measured on its cream faces) on this glyph's OWN face pass (no neighbour, no cut); "
                      f"anchor_ref_pt = that point at rest on the 393 x 852 reference canvas (LOGO-SPEC §2 'anchor at rest'; "
                      f"LOGO-SPEC's approximation, cut from the one-piece, was {[round(float(v), 3) for v in a['logo_spec_mask_ref_pt']]}; "
                      f"the face's plain alpha centroid is {a['alpha_ref_pt']}). LOGO-ART-3 (2026-09-27): SUPERSEDED IN THE "
                      f"ANIMATION by the pair {EXT[pid]} + {FACE[pid]} (same frame, same anchor): "
                      + ("a composed glyph i > 0 bakes the earlier glyphs' face pixels into its file, and LOGO-SPEC spreads "
                         "the glyphs apart (O|U +4...+14 pt, U|T +4...+20 pt at W+1.30-1.60): those pixels then show as a "
                         "cream block and a light line (the owner's 'weird lines'); " if i > 0 else
                         "every OUT! extrusion must lie under every OUT! face, O included; ")
                      + "kept (not animated); build/logo/art3/motion.json.")
        elif pid == PEGS:
            e["anchor_frac"] = [round(pa[0], 5), round(pa[1], 5)]
            e["anchor_ref_pt"] = [round((x + pa[0] * w) / CW * gw + geo["group_pt"][0], 3),
                                  round((y + pa[1] * h) / CH * gh + geo["group_pt"][1], 3)]
            detail = ("LOGO-ART-2 P1 (LOGO-SPEC §9.2): the two grey pegs (gen_icons layer 'pegs'), their own layer between the "
                      "two signs (z 0.5), cut out of logoSignPurple IN THE DRAWING (never from a PNG); THIS FILE OVER "
                      "logoSignPurple (pegs z 0.5 above the sign's z 0) = round 1's logoSignPurple (reassembly.json P1-P3, "
                      "pegs_sheet.png; LOGO-ART-3 corrected the order in these labels, the composite was always pegs over sign). Frame on EVEN logo px, factor "
                      "1.5 like the signs: its file pixels coincide with logoSignPurple's. Only dy moves it (LOGO-SPEC T3: "
                      "-15 -> 0 pt, W+1.19 -> 1.59): any anchor works; anchor_frac = its alpha centroid.")
        else:
            b = g.LOGO_BENDS[pid]
            sx_, sy_, sw, sh, sf = frame_of("logoSignPurple")
            pad = g.LOGO_BEND["pad"]
            ay_ref = (sy_ + sa[1] * sh)
            e["anchor_frac"] = [round(sa[0], 5), round((ay_ref - y) / h, 5)]
            e["anchor_ref_pt"] = [round((sx_ + sa[0] * sw) / CW * gw + geo["group_pt"][0], 3),
                                  round(ay_ref / CH * gh + geo["group_pt"][1], 3)]
            e["variant_of"] = "logoSignPurple"
            e["bend_deg"] = b
            kk = math.radians(-b) / (2 * g.LOGO_BEND["body"])
            cal = _bend_measure(shipped(pid))["bend"] - _bend_measure(shipped("logoSignPurple"))["bend"]
            e["bend_measured_deg"] = round(cal, 3)
            detail = (f"LOGO-ART-2 P2 (LOGO-SPEC §9.3 / §2 'the bend'): logoSignPurple (no pegs) bent {b:+.1f} deg: the rest "
                      f"drawing warped y' = y + k (x - x_a)^2 in the part's own axes (its frame = the layer's axes, as sx / sy), "
                      f"k = |bend| rad / (2 L_body) = {kk:.4e} per logo px, x_a = {g.LOGO_BEND['xa']} logo px = the purple "
                      f"face's centroid: both ends move DOWN (a stronger arch), the anchor is a fixed point. L_body = "
                      f"{g.LOGO_BEND['body']} logo px is set so that LOGO-SPEC's own bend measurement (spec/tools/bend.py, the "
                      f"metric of table K and of the bend track) reads this file at {cal:+.2f} deg (build/logo/art2/"
                      f"bend_calibration.json); §2's literal 0.70 x the frame width (488.6 logo px, spec/tools/render_ours.py) "
                      f"read only 83 % of the nominal bend. The warp runs on the premultiplied WebKit 2x render of the "
                      f"rest drawing (clipped at the canvas bottom as the rest file is), before the 2:1 area filter (svg.py "
                      f"data-warp -> logo_parts.warp). Frame = logoSignPurple's frame + {pad} logo px ({pad * k / 3:.2f} pt) at "
                      f"the bottom (same x, y, width, factor 1.5): the anchor POINT is logoSignPurple's (anchor_ref_pt), only "
                      f"its y fraction differs. ONE LAYER, 5 contents (rest + 4, calculationMode .discrete, nearest of rest / "
                      f"-2.5 / -5 / -7.5 / -10): bounds = this padded frame ({w / CW * gw:.3f} x {h / CH * gh:.3f} pt), "
                      f"anchorPoint = anchor_frac, contentsGravity .top and contentsScale = {f * CW / gw:.4f} file px per "
                      f"reference pt -- the rest file then draws exactly on its own frame and the pad stays empty (or swap "
                      f"bounds / anchorPoint with the contents). The variants are shown W+{L['bend variants']['shown'][0]:.3f}"
                      f"...{L['bend variants']['shown'][1]:.3f} only (bend <= -1.25 deg: the nearest of rest / -2.5 / -5 / "
                      f"-7.5 / -10); before and after that, the REST drawing (logoSignPurple) -- including the positive "
                      f"overshoot from W+0.986 (up to +1.5 deg at W+0.989), which has no variant (LOGO-ART-3 corrected round "
                      f"2's 'W+0.703...0.993 (|bend| >= 1.25 deg)').")
        e.update({"source": f"art/ui/src/svg/gen_icons.py:{pid}", "file": f"art/ui/out/{pid}@3x.png", "ref": ref,
                  "status": "done", "owner": "ui-art"})
        e["notes"] = (detail + f" size_pt = its SETTLED on-screen size at the NEW rest (logoArrowOut at celebrate.logo's k "
                      f"{k:.5f}, LOGO-SPEC D4; layoutRect only shrinks it below 393 x 852) -- unlike the first 8 parts' size_pt "
                      f"(old 0.94 settle); anchor_pt = this frame's top-left inside the logo canvas at rest. render_scale {rs} = "
                      f"the file is size_pt x 3 x {rs} px ({f}x logoArrowOut@3x); its largest on-screen size in LOGO-SPEC is "
                      f"x{big:.3f} of the settled size (W+{at:.3f}; build/logo/art4/upscale.json): {r:.3f} screen px per file "
                      f"px, never upscaled. PLACE BY logo_rect (exact): the frame as fractions of the logoArrowOut canvas "
                      f"(x, y, w, h), the same space as the other logo parts; frame in logoArrowOut @3x px = ({x}, {y}, {w}, "
                      f"{h}). {Z_ORDER_TXT}." + common_tail)
        e["size_px"] = [round(v * 3) for v in e["size_pt"]]
        idx = next((i for i, o in enumerate(m["entries"]) if o["id"] == pid), None)
        if idx is None:
            at_ = next(i for i, o in enumerate(m["entries"]) if o["id"] == order_after) + 1
            m["entries"].insert(at_, e)
        else:
            m["entries"][idx] = e
        order_after = pid
        print(f"  {pid:22s} size_pt {e['size_pt']} render_scale {rs} file_px {e['file_px']} logo_rect {e['logo_rect']} "
              f"z {e['z']} anchor_frac {e.get('anchor_frac')} anchor_ref_pt {e.get('anchor_ref_pt')}")
        if pid in GLYPHS:
            m["entries"][next(i for i, o in enumerate(m["entries"]) if o["id"] == pid)]["pair"] = [EXT[pid], FACE[pid]]
    # ---- the round-3 pairs (LOGO-ART-3) + the round-4 flats (LOGO-ART-4): every letter / glyph as <base>Ext + <base>Face on
    # the base's frame; each ARROW letter also as <base>Flat. SPEC.md ruling 36 (e): size_pt / anchor_pt / render_scale /
    # size_px FOLLOW THE ID THEY REPLACE (<base>: ARROW = the round-1 letters' OLD 0.94-settle numbers, OUT! = round 2's
    # new-rest numbers); the implementer sizes every layer from logo_rect (LOGO-SPEC §2), never from size_pt.
    def base_entry(b_):
        return next(o for o in m["entries"] if o["id"] == b_)
    for pid in PAIRS + FLATS:
        if only is not None and pid not in only:
            continue
        base = BASE_OF[pid]
        kind = "flat" if pid in FLATS else "ext" if pid == EXT[base] else "face"
        word = WORD_OF[base]
        x, y, w, h, f = frame_of(pid)
        assert (x, y, w, h, f) == frame_of(base), (pid, "a pair / flat must keep its base's frame")
        big, at, r = upscale_txt(pid, f)
        set_w, set_h = w / CW * gw, h / CH * gh
        be = base_entry(base)
        rs = be["render_scale"]
        assert [round(v) for v in (be["size_pt"][0] * 3 * rs, be["size_pt"][1] * 3 * rs)] == [round(w * f), round(h * f)], pid
        if word == "OUT!":
            a = anchors[base]
            af, ar = a["frac"], a["ref_pt"]
            anchor_txt = ("anchor_frac = the glyph's CREAM FACE centroid (LOGO-SPEC's colour rule on the glyph's own face "
                          "pass, as round 2's logoOut" + NAMES[base].replace("!", "Bang") + "; the same frame, so the same "
                          "fraction)")
            parent = "outGroup"
            size_txt = (f"size_pt / anchor_pt / render_scale = {base}'s (the id it replaces, SPEC.md ruling 36 (e)) = its "
                        f"SETTLED on-screen size at the NEW rest (logoArrowOut at celebrate.logo's k {k:.5f}); anchor_pt = "
                        f"this frame's top-left inside the logo canvas at rest.")
        else:
            p_ = kf["parts"][base]
            af, ar = [round(v, 5) for v in p_["anchorFrac"]], [round(v, 3) for v in p_["anchorPt"]]
            anchor_txt = ("anchor_frac / anchor_ref_pt = LOGO-SPEC §2's anchor of " + base + " (winlogo_keyframes.json "
                          "anchorFrac / anchorPt; the same frame, so the same fraction)")
            parent = "logoSignBlue"
            size_txt = (f"size_pt / anchor_pt / render_scale = {base}'s (the id it replaces, SPEC.md ruling 36 (e)): the "
                        f"round-1 numbers at the OLD 0.94 settle (x{s_old:.5f} of the logo's pt), kept so UIArt.sizePt "
                        f"agrees with {base}; the SETTLED on-screen size at the new rest is {grow:.4f} x size_pt = "
                        f"{set_w:.2f} x {set_h:.2f} pt. The implementer sizes the layer from logo_rect (LOGO-SPEC §2: bounds "
                        f"= logo_rect x the logoArrowOut canvas at rest), never from size_pt.")
        e = {"id": pid, "family": "svg", "route": "B2", "group": "logo", "purpose": PURPOSE[pid],
             "screen": "win celebration (WinLogoSequence), above the dim",
             "size_pt": list(be["size_pt"]), "render_scale": rs, "file_px": [round(w * f), round(h * f)],
             "anchor_pt": list(be["anchor_pt"]),
             "logo_rect": [round(x / CW, 6), round(y / CH, 6), round(w / CW, 6), round(h / CH, 6)], "z": Z[pid],
             "anchor_frac": af, "anchor_ref_pt": ar, "pair_of": base, "layer": kind, "pair": [EXT[base], FACE[base]],
             "parent": parent}
        if word == "ARROW":
            e["flat"] = FLAT[base]
        zs = ("inside logoSignBlue: the 5 ARROW extrusions (z 2.0-2.4) UNDER the 5 ARROW faces (z 3.0-3.4)" if word == "ARROW"
              else "inside outGroup (in the group, z 7): the 4 OUT! extrusions (z 7-10) UNDER the 4 OUT! faces (z 11-14)")
        if kind == "flat":
            detail = (f"LOGO-ART-4 (2026-09-27, SPEC.md ruling 36 (b)): {_WHAT[base]} as ONE FLAT SPRITE exported STRAIGHT "
                      f"FROM THE SVG drawing: its own face OVER its own WHOLE (untrimmed) extrusion, nothing of any other "
                      f"letter (two plain passes = exactly {EXT[base]}'s and {FACE[base]}'s elements on the same frame and "
                      f"clamped regions, composed in premultiplied float at the raw WebKit 2x render, then the exact 2:1 "
                      f"area filter; verify: build/logo/art4/verify.json). SHOWN WHILE THE LETTER'S OPACITY < 1 (W+"
                      f"{kf['parts'][base]['visibleFrom']:.3f} until its flatUntil), in the letter's Face slot (z "
                      f"{Z[pid]}), with the letter's transform (the same frame, anchorPoint and animations as the pair) and "
                      f"opacity = the letter's a; the pair {EXT[base]} + {FACE[base]} is hidden then and takes over, at "
                      f"opacity 1, on the first frame at opacity 1 (a discrete step; the pair is never drawn translucent: "
                      f"a translucent pair shows its trimmed extrusion through the face as an orange outline, the second "
                      f"adversarial check of round 3). Swap proof (pair vs flat at opacity 1): build/logo/art4/swap.json. "
                      f"{anchor_txt}.")
        else:
            op = ("Opacity (LOGO-ART-4, SPEC.md ruling 36 (a)): this layer stays at opacity 1 inside the ONE container "
                  "outGroup, which carries OUT!'s opacity track with GROUP opacity (allowsGroupOpacity = true; the 8 "
                  "layers composite first, then fade as one: a translucent pair would show its trimmed extrusion through "
                  "the face); the echo copies likewise inside the one container outEcho." if word == "OUT!" else
                  f"Opacity (LOGO-ART-4, SPEC.md ruling 36 (b)): shown only from the letter's flatUntil (its first frame "
                  f"at opacity 1), always at opacity 1 (a discrete step, never translucent); before that the flat sprite "
                  f"{FLAT[base]} stands in its Face slot.")
            detail = (f"LOGO-ART-3 (2026-09-27; the owner: 'the OUT! has weird lines when it grows on the screen'): "
                      f"{_WHAT[base]} as a PAIR of layers exported STRAIGHT FROM THE SVG drawing (gen_icons._logo_layers, never "
                      f"from a PNG): this is its {'EXTRUSION' if kind == 'ext' else 'FACE'} ALONE (one plain pass, the "
                      + ("18-step 3-D side and its stroke; TRIMMED where its own face is opaque and it is farther than "
                         f"LOGO_TRIM {g.LOGO_TRIM} logo px from where it shows (logo_parts.trim_ext: that part is always "
                         "hidden by its own face at opacity 1, same transform; without the trim the two separately filtered "
                         "layers conflate along the side edges; LOGO-ART-4 cut the ring from 4 to 1 logo px -- the longer "
                         "ring made the extrusion's edge coincide with the face's along the side edges near the bottom "
                         "corners: build/logo/art4/trim_experiment*.json)" if kind == 'ext' else
                         "face through the word inflation filter: outline + bevel") +
                      f"), NO element of any other letter / glyph (verify: the SVG references only this glyph; build/logo/art4/"
                      f"verify.json). Its partner is {FACE[base] if kind == 'ext' else EXT[base]}: the two share ONE transform "
                      f"-- the same frame (logo_rect, as {base}), the same anchorPoint (anchor_frac) and the same animation "
                      f"values ({base}'s LOGO-SPEC tracks); the echo copies (LOGO-SPEC §2) are pairs too. Stacking: {zs}, "
                      f"exactly the one-piece's paint order, so at rest the stack re-assembles logoArrowOut (build/logo/art3/"
                      f"reassembly.json). {op} Colour test of the whole stack vs one sprite per glyph at every 1/60 s frame "
                      f"W+0.60-1.95: build/logo/art4/look.json. {anchor_txt}. Replaces {base} (rounds 1-2) in the animation.")
        e.update({"source": f"art/ui/src/svg/gen_icons.py:{pid}", "file": f"art/ui/out/{pid}@3x.png", "ref": ref,
                  "status": "done", "owner": "ui-art"})
        e["notes"] = (detail + f" {size_txt} render_scale {rs}: the file is size_pt x 3 x {rs} px ({f}x logoArrowOut@3x); "
                      f"its largest on-screen size in LOGO-SPEC is x{big:.3f} of the settled size (W+{at:.3f}; "
                      f"build/logo/art4/upscale.json): {r:.3f} screen px per file px, never upscaled. PLACE BY logo_rect "
                      f"(exact): frame in logoArrowOut @3x px = ({x}, {y}, {w}, {h}). {Z_ORDER_TXT}." + common_tail)
        e["size_px"] = [round(v * 3) for v in e["size_pt"]]
        idx = next((i for i, o in enumerate(m["entries"]) if o["id"] == pid), None)
        if idx is None:
            at_ = next(i for i, o in enumerate(m["entries"]) if o["id"] == order_after) + 1
            m["entries"].insert(at_, e)
        else:
            m["entries"][idx] = e
        order_after = pid
        print(f"  {pid:22s} size_pt {e['size_pt']} render_scale {rs} file_px {e['file_px']} z {e['z']} "
              f"anchor_frac {e['anchor_frac']} anchor_ref_pt {e['anchor_ref_pt']}")
    for b_ in LETTERS if only is None else ():         # the replaced round-1 letters point at their flat too
        base_entry(b_)["flat"] = FLAT[b_]
    MF.save(m)
    MF.write_idmap(m)
    print("wrote art/MANIFEST.json + art/ID-MAP.md")


def show_geometry():
    geo = geometry()
    print(json.dumps(geo, indent=1))
    old = geo["old"]
    kind = {"logoSignPurple": "sign", "logoSignBlue": "sign", "logoOut": "out"}
    for pid in IDS_R1:
        x, y, w, h, f = frame_of(pid)
        kd = kind.get(pid, "letter")
        if "largest" in old:
            print(f"  {pid:15s} old settled {w / 3 * old['s']:.2f} x {h / 3 * old['s']:.2f} pt; old largest "
                  f"{w / 3 * old['largest'][kd]:.2f} x {h / 3 * old['largest'][kd]:.2f} pt; new rest {w / 3 * geo['k']:.2f} x "
                  f"{h / 3 * geo['k']:.2f} pt; file {round(w * f)} x {round(h * f)} px")


def clean():
    shutil.rmtree(SCR, ignore_errors=True)
    print("removed", os.path.relpath(SCR, APP))


# ====================================================================================== round 3 (LOGO-ART-3): the pairs
# The owner: "the OUT! has weird lines when it grows on the screen". Rounds 1-2 composed a letter / glyph i > 0 as ONE
# layer = its face OVER (the earlier faces ATOP its extrusion): exact at rest, but the earlier faces' pixels are BAKED into
# the file and travel with it when LOGO-SPEC moves the glyphs apart. Round 3: every letter / glyph is a PAIR <base>Ext +
# <base>Face (gen_icons.LOGO_PAIRS), one shared transform, every extrusion of a word under every face of that word.
#   proof3   at rest: the 23-layer stack vs the one-piece (2x renders, the 1x grid, the settled scale), per word, the joins
#   motion   THE KEY TEST: LOGO-SPEC's tracks (winlogo_keyframes.json) at every 1/60 s frame W+0.60...1.95 (+ table G's
#            rows and the frames of the largest relative displacement at every join), composited at on-screen size (iPhone
#            15 @3x, 3 device px per pt): no pixel of a letter / glyph appears outside its own silhouette (stray = 0 per
#            frame), with rounds 1-2's composed files as the negative control; the 6 worst frames at 400 %.
#   fringe3  the pairs' premultiplied edges over black / white.
PXPT = 3.0                                     # iPhone 15 @3x, layoutRect k = 1: 3 device px per reference pt
SCREEN = (int(852 * PXPT), int(393 * PXPT))    # (H, W) device px of the 393 x 852 pt reference canvas
TAU = (1 / 255, 16 / 255)                      # stray thresholds on a layer's on-screen alpha: any ink / visible ink
SIL_DILATE = 2                                 # device px of tolerance around the independent silhouette (two renders' AA)
BEND_STEPS = [(0.0, "logoSignPurple"), (-2.5, BENDS[0]), (-5.0, BENDS[1]), (-7.5, BENDS[2]), (-10.0, BENDS[3])]
_KF = _GEO = _ANCH = None


def kf():
    global _KF
    if _KF is None:
        _KF = json.load(open(os.path.join(SPEC, "winlogo_keyframes.json")))
    return _KF


def geo_():
    global _GEO
    if _GEO is None:
        _GEO = geometry()
    return _GEO


def rest_frame_pt(pid):
    """A part's frame at rest on the 393 x 852 reference canvas (pt): logo_rect x the logoArrowOut canvas at celebrate.logo."""
    x, y, w, h, f = frame_of(pid)
    gx, gy, gw, gh = geo_()["group_pt"]
    return (gx + x / CW * gw, gy + y / CH * gh, w / CW * gw, h / CH * gh)


def anchor_pt(part):
    """The anchor at rest (reference pt) of a LOGO-SPEC part = winlogo_keyframes.json's anchorPt. LOGO-SPEC-FIX M1: the
    spec's anchors ARE the MANIFEST's (anchor_frac on logo_rect; its tracks re-expressed about them), so the tracks and the
    anchor always come from ONE place (round 4 mixed the manifest's glyph anchors with tracks fitted about LOGO-SPEC's
    pre-split guesses: T sat 1.73 pt off at rest); checked here against the MANIFEST's anchor_ref_pt."""
    global _ANCH
    if _ANCH is None:
        sys.path.insert(0, os.path.join(APP, "art", "tools"))
        import manifest as MF
        by = MF.by_id()
        _ANCH = {}
        for pid, p in kf()["parts"].items():
            lids = [l_ for l_, d in kf().get("layers", {}).items() if d["part"] == pid]
            for l_ in lids:
                ar = by[l_].get("anchor_ref_pt")
                assert ar is None or max(abs(ar[0] - p["anchorPt"][0]), abs(ar[1] - p["anchorPt"][1])) < 0.006, (l_, ar, p["anchorPt"])
            _ANCH[pid] = np.array(p["anchorPt"], float)
    return _ANCH[part]


def tval(tr, key, t, d):
    return float(ev(tr[key], t)[0]) if key in tr else d


def local_pose(part, t):
    p = kf()["parts"][part]
    tr = p["tracks"]
    a = anchor_pt(part)
    s_ = tval(tr, "s", t, 1.0)
    sx, sy = tval(tr, "sx", t, s_), tval(tr, "sy", t, s_)
    th = math.radians(tval(tr, "rot", t, 0.0))
    R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    A = R @ np.diag([sx, sy])
    b = a + np.array([tval(tr, "dx", t, 0.0), tval(tr, "dy", t, 0.0)]) - A @ a
    if p["parent"] != "group":
        A2, b2 = local_pose(p["parent"], t)
        A, b = A2 @ A, A2 @ b + b2
    return A, b


def pose(part, t):
    """(A, b, alpha): a point p of `part` at rest (reference pt) is on screen at A p + b at t - W -- LOGO-SPEC §2's
    composition: displacement about the part's own anchor, a letter through the blue sign's map, the group scale about
    groupPivot; alpha = its opacity x its parent's (0 before visibleFrom)."""
    K = kf()
    A, b = local_pose(part, t)
    g = float(ev(K["group"]["s"], t)[0])
    P = np.array(K["groupPivot"], float)
    p = K["parts"][part]
    tr_a = a_track(part)                                   # (the OUT! glyphs: outGroup's track, LOGO-ART-4)
    alpha = (float(ev(tr_a, t)[0]) if tr_a else 1.0) if t >= p["visibleFrom"] - 1e-9 else 0.0
    if p["parent"] != "group":
        alpha *= pose(p["parent"], t)[2]
    return g * A, g * b + P - g * P, alpha


def sign_image(t):
    """The purple sign's contents at t: the nearest of rest / -2.5 / -5 / -7.5 / -10 deg (LOGO-SPEC §2 'the bend')."""
    b = tval(kf()["parts"]["logoSignPurple"]["tracks"], "bend", t, 0.0)
    return min(BEND_STEPS, key=lambda v: abs(v[0] - b))[1]


class Lay:
    """A layer's premultiplied float32 pixels on its rest frame, with integer box mip levels."""

    def __init__(self, arr, frame):
        self.a = np.ascontiguousarray(arr, dtype=np.float32)
        if self.a.ndim == 2:
            self.a = self.a[..., None]
        self.frame = frame
        self.mips = {1: self.a}

    def mip(self, d):
        if d not in self.mips:
            a = self.a
            H, W, C = a.shape
            Hp, Wp = -(-H // d) * d, -(-W // d) * d
            q = np.zeros((Hp, Wp, C), np.float32)
            q[:H, :W] = a
            self.mips[d] = q.reshape(Hp // d, d, Wp // d, d, C).mean(axis=(1, 3))
        return self.mips[d]


_LAY = {}


def lay_file(pid, alpha_only=False):
    """A SHIPPED file as a layer on its rest frame (cached)."""
    key = (pid, alpha_only)
    if key not in _LAY:
        p = pm(shipped(pid)).astype(np.float32)
        _LAY[key] = Lay(p[..., 3] if alpha_only else p, rest_frame_pt(pid))
    return _LAY[key]


def screen_box(frame, A, b, margin=3):
    x0, y0, w, h = frame
    c = np.array([[x0, y0], [x0 + w, y0], [x0, y0 + h], [x0 + w, y0 + h]]) @ A.T + b
    c = c * PXPT
    X0, Y0 = int(math.floor(c[:, 0].min())) - margin, int(math.floor(c[:, 1].min())) - margin
    X1, Y1 = int(math.ceil(c[:, 0].max())) + margin, int(math.ceil(c[:, 1].max())) + margin
    X0, Y0, X1, Y1 = max(0, X0), max(0, Y0), min(SCREEN[1], X1), min(SCREEN[0], Y1)
    return (Y0, X0, max(0, Y1 - Y0), max(0, X1 - X0))


def place_lay(L, A, b, win):
    """Layer L drawn with the map A p + b (rest pt -> screen pt) into the device-px window win = (Y0, X0, h, w): an integer
    box pre-filter (the mip level; then screen px per level px is in (0.5, 1]) and bilinear, premultiplied -- roughly Core
    Animation's trilinear minification. -> float32 (h, w, C)."""
    Y0, X0, hh, ww = win
    C = L.a.shape[2]
    if hh <= 0 or ww <= 0:
        return np.zeros((max(hh, 0), max(ww, 0), C), np.float32)
    H, W = L.a.shape[:2]
    x0, y0, fw, fh = L.frame
    Lm = PXPT * A @ np.diag([fw / W, fh / H])                   # device px per file px
    d = max(1, int(math.floor(1.0 / np.linalg.svd(Lm, compute_uv=False)[0] + 1e-9)))
    src = L.mip(d)
    F = Lm * d
    f = PXPT * (A @ (np.array([x0, y0]) + 0.5 * d * np.array([fw / W, fh / H])) + b) - 0.5 - np.array([X0, Y0])
    G = np.linalg.inv(F)
    g = -G @ f
    M = np.array([[G[1, 1], G[1, 0]], [G[0, 1], G[0, 0]]])
    off = np.array([g[1], g[0]])
    out = np.empty((hh, ww, C), np.float32)
    for c in range(C):
        out[..., c] = NDI.affine_transform(src[..., c], M, offset=off, output_shape=(hh, ww), order=1, mode="constant",
                                           cval=0.0, prefilter=False)
    return out


def _over_into(canvas, patch, win, alpha=1.0):
    Y0, X0, hh, ww = win
    if hh <= 0 or ww <= 0 or alpha <= 0:
        return
    if alpha < 1.0:
        patch = patch * np.float32(alpha)
    dst = canvas[Y0:Y0 + hh, X0:X0 + ww]
    dst *= (1.0 - patch[..., 3:4])
    dst += patch


def dim_at(t):
    w = kf()["win"]
    return min(1.0, max(0.0, (t - w["dimAt"]) / w["dimDur"])) * w["dim"]


def stack(t, rnd):
    """The layer stack at t - W, bottom to top: [(file id, LOGO-SPEC part, pose time, alpha x, echo group?)].
    rnd 3 = the pairs (every extrusion of a word under every face of it; the echo = one group of 8 pair copies under OUT!,
    group opacity); rnd 2 = rounds 1-2's composed letters / glyphs (the echo per glyph under its glyph, as LOGO-SPEC §2 had
    it)."""
    K = kf()
    ec = K["echo"]
    te = t - ec["delay"]
    out = [(sign_image(t), "logoSignPurple", t, 1.0, False), (PEGS, "logoPegs", t, 1.0, False),
           ("logoSignBlue", "logoSignBlue", t, 1.0, False)]
    if rnd == 3:
        out += [(p, BASE_OF[p], t, 1.0, False) for p in ARROW_PAIRS]
        if t < ec["until"]:
            out += [(p, BASE_OF[p], te, ec["alphaFactor"], True) for p in OUT_PAIRS]
        out += [(p, BASE_OF[p], t, 1.0, False) for p in OUT_PAIRS]
    else:
        out += [(b_, b_, t, 1.0, False) for b_ in LETTERS]
        for b_ in GLYPHS:
            if t < ec["until"]:
                out.append((b_, b_, te, ec["alphaFactor"], False))
            out.append((b_, b_, t, 1.0, False))
    return out


def composite(t, rnd, bg=True):
    """The logo on screen at t - W (premultiplied float32 SCREEN x 4): white board + the win dim + the stack."""
    can = np.zeros(SCREEN + (4,), np.float32)
    if bg:
        d = dim_at(t)
        can[..., 3] = 1.0
        can[..., :3] = 1.0 - d
    group, gwin = [], None
    for pid, part, tp, am, grp in stack(t, rnd) + [(None, None, None, None, False)]:
        if group and not grp:                              # flush the echo group (composited, then its opacity)
            Y0 = min(w_[0] for _, w_, _ in group)
            X0 = min(w_[1] for _, w_, _ in group)
            Y1 = max(w_[0] + w_[2] for _, w_, _ in group)
            X1 = max(w_[1] + w_[3] for _, w_, _ in group)
            gwin = (Y0, X0, Y1 - Y0, X1 - X0)
            tmp = np.zeros((Y1 - Y0, X1 - X0, 4), np.float32)
            for patch, w_, _ in group:
                _over_into(tmp, patch, (w_[0] - Y0, w_[1] - X0, w_[2], w_[3]))
            _over_into(can, tmp, gwin, group[0][2])
            group = []
        if pid is None:
            break
        A, b, al = pose(part, tp)
        al *= am
        if al <= 0.002:
            continue
        L = lay_file(pid)
        win = screen_box(L.frame, A, b)
        patch = place_lay(L, A, b, win)
        if grp:
            group.append((patch, win, al))                 # the pairs' copies at full opacity inside the group
        else:
            _over_into(can, patch, win, al)
    return can


# ---- silhouettes and the baked pieces
_SIL = {}


def silhouette(base):
    """The letter / glyph's OWN silhouette, independently of the shipped files: its extrusion pass and its face pass
    rendered on logoArrowOut's FULL canvas (WebKit 2x = 2 px per logo px; another frame, resolution and filter region than
    the files), union alpha, cropped to the base's frame -> a 1-channel layer on the base's rest frame."""
    if base not in _SIL:
        x, y, w, h, f = frame_of(base)
        ae = render_part(EXT[base], (0, 0, CW, CH), 1.0, "full", trim=False)[2 * y:2 * (y + h), 2 * x:2 * (x + w), 3]
        ae = ae.astype(np.float64)                         # (the whole extrusion: the silhouette, untrimmed)
        af = fc(FACE[base])[2 * y:2 * (y + h), 2 * x:2 * (x + w), 3].astype(np.float64)
        _SIL[base] = Lay(ae + af - ae * af, rest_frame_pt(base))
    return _SIL[base]


_BAKED = {}


def baked(g):
    """Rounds 1-2's composed file of letter / glyph g (i > 0): the earlier faces baked into it = compose()'s term
    before x a_E x (1 - a_F) -- where the file shows an EARLIER letter's face instead of g's own extrusion (ATOP keeps the
    alpha: the pixels are inside g's silhouette, the colour is the neighbour's). From the part's own 3 pass renders at its
    frame and factor (the pipeline that made the file) -> {owner h: coverage on the file grid (float32)}, the owner = the
    earlier face on top at that pixel (the full-canvas face renders); + the area in logo px^2."""
    if g in _BAKED:
        return _BAKED[g]
    word = LETTERS if g in LETTERS else GLYPHS
    i = word.index(g)
    if i == 0:
        _BAKED[g] = ({}, 0.0, {})
        return _BAKED[g]
    x, y, w, h, f = frame_of(g)
    render_part(g, (x, y, w, h), f, "part")                # (the cached pass raws)
    E, B, Fc = (pm(Image.open(os.path.join(SCR, f"{g}_part_{p}_raw.png"))) for p in ("ext", "before", "face"))
    cov = box2((B[..., 3] * E[..., 3] * (1.0 - Fc[..., 3]))[..., None])[..., 0]
    rep_ = int(round(f / 2))                              # file px per full-canvas render px
    top = np.full(cov.shape, -1, int)
    for j, hb in enumerate(word[:i]):                     # later faces paint over earlier ones
        a = fc(FACE[hb])[2 * y:2 * (y + h), 2 * x:2 * (x + w), 3]
        a = np.repeat(np.repeat(a, rep_, 0), rep_, 1)[:cov.shape[0], :cov.shape[1]]
        top[a > 0.02] = j
    out = {}
    for j, hb in enumerate(word[:i]):
        c = np.where(top == j, cov, 0.0)
        if c.max() > 1 / 255:
            out[hb] = c.astype(np.float32)
    unowned = float(np.where(top < 0, cov, 0.0).sum())
    assert unowned < 0.05 * max(cov.sum(), 1e-9), (g, "baked pixels without an owner", unowned, cov.sum())
    _BAKED[g] = ({hb: Lay(c, rest_frame_pt(g)) for hb, c in out.items()}, float(cov.sum() / f ** 2),
                 {hb: round(float(c.sum() / f ** 2), 1) for hb, c in out.items()})
    return _BAKED[g]


def strays(t, rnd, echo=True):
    """Pixels of a letter / glyph drawn OUTSIDE its own silhouette at t - W (on screen, device px), per letter / glyph.
    rnd 3: each pair layer's ink (alpha > tau) where the base's own silhouette (placed with the base's pose, dilated
    SIL_DILATE px) is empty; + the echo pairs at t - delay. rnd 2: the earlier faces baked into each composed file (drawn
    with the file's pose) where their OWNER's silhouette (at the owner's pose) is empty."""
    K = kf()
    ec = K["echo"]
    res = {}
    bases = [b_ for b_ in BASES if pose(b_, t)[2] > 0.002]
    if rnd == 3:
        jobs = [(b_, t, "") for b_ in bases]
        if echo and t < ec["until"]:
            jobs += [(b_, t - ec["delay"], " echo") for b_ in GLYPHS if pose(b_, t - ec["delay"])[2] > 0.002]
        for b_, tp, tag in jobs:
            A, b, _ = pose(b_, tp)
            sil = silhouette(b_)
            win = screen_box(sil.frame, A, b, margin=6)
            ok = NDI.maximum_filter(place_lay(sil, A, b, win)[..., 0], size=2 * SIL_DILATE + 1) > 0.5 / 255
            n = [0, 0]
            for pid in (EXT[b_], FACE[b_]):
                a_ = place_lay(lay_file(pid, True), A, b, win)[..., 0]
                for k_, tau in enumerate(TAU):
                    n[k_] += int(((a_ > tau) & ~ok).sum())
            res[LTR[b_] + tag] = n
        return res
    for g in bases:
        pieces = baked(g)[0]
        if not pieces:
            continue
        A, b, _ = pose(g, t)
        win = screen_box(rest_frame_pt(g), A, b, margin=6)
        n = [0, 0]
        for hb, L in pieces.items():
            Ah, bh, alh = pose(hb, t)
            own = place_lay(silhouette(hb), Ah, bh, win)[..., 0] if alh > 0.002 else np.zeros(win[2:], np.float32)
            ok = NDI.maximum_filter(own, size=2 * SIL_DILATE + 1) > 0.5 / 255
            c = place_lay(L, A, b, win)[..., 0]
            for k_, tau in enumerate(TAU):
                n[k_] += int(((c > tau) & ~ok).sum())
        res[LTR[g]] = n
    return res


def join_points():
    """Where neighbouring letters / glyphs meet at rest (reference pt): the pixels where both silhouettes (full-canvas 2x
    renders) have alpha > 0.02, or the two closest pixels when they do not touch."""
    gx, gy, gw, gh = geo_()["group_pt"]
    out = {}
    for word in (LETTERS, GLYPHS):
        for a_, b_ in zip(word, word[1:]):
            A_ = np.zeros((2 * CH, 2 * CW), bool)
            B_ = np.zeros((2 * CH, 2 * CW), bool)
            for base, M_ in ((a_, A_), (b_, B_)):
                x, y, w, h, f = frame_of(base)
                M_[2 * y:2 * (y + h), 2 * x:2 * (x + w)] = silhouette(base).a[..., 0] > 0.02
            ys, xs = np.nonzero(A_ & B_)
            if not len(xs):
                ya, xa = np.nonzero(A_)
                yb, xb = np.nonzero(B_)
                i_, j_ = np.argmax(xa), np.argmin(xb)
                ys, xs = np.array([ya[i_], yb[j_]]), np.array([xa[i_], xb[j_]])
            sel = np.linspace(0, len(xs) - 1, min(len(xs), 400)).astype(int)
            pts = np.stack([gx + (xs[sel] + 0.5) / 2 / CW * gw, gy + (ys[sel] + 0.5) / 2 / CH * gh], 1)
            out[(a_, b_)] = pts
    return out


def join_spread(t, jp):
    """The largest relative displacement (pt) at each join: max over the join's points of |pose_b(p) - pose_a(p)| -- how far a
    piece baked into one glyph at that join lands from where its owner draws it."""
    res = {}
    for (a_, b_), pts in jp.items():
        Aa, ba, ala = pose(a_, t)
        Ab, bb, alb = pose(b_, t)
        if ala <= 0.002 or alb <= 0.002:
            continue
        res[f"{LTR[a_]}|{LTR[b_]}"] = round(float(np.linalg.norm(pts @ (Ab - Aa).T + (bb - ba), axis=1).max()), 2)
    return res


def motion():
    """THE KEY TEST (LOGO-ART-3). Writes build/logo/art3/motion.json + motion_worst_sheet.png + motion_strip.png."""
    os.makedirs(EVID, exist_ok=True)
    K = kf()
    jp = join_points()
    t0, t1 = 0.60, 1.95
    grid = [round(t0 + n / 60, 6) for n in range(int(round((t1 - t0) * 60)) + 1)]
    table_g = [1.155, 1.205, 1.255, 1.305, 1.355, 1.405, 1.455, 1.505, 1.555, 1.605, 1.655, 1.705, 1.805]
    dense = np.round(np.arange(t0, t1 + 1e-9, 1 / 600), 6)
    spread = {tt: join_spread(tt, jp) for tt in dense}
    peaks = {}
    for name in sorted({k_ for v in spread.values() for k_ in v}):
        tt = max(dense, key=lambda x: spread[x].get(name, -1))
        peaks[name] = dict(t=float(tt), pt=spread[tt][name])
    extra = sorted({round(v["t"], 6) for v in peaks.values()} | set(table_g))
    frames = sorted(set(grid) | set(extra))
    beats = [round(0.35 + m / 30, 6) for m in range(44)] + [1.80]
    rows, worst_new = [], 0
    baked_area = {LTR[g]: (round(baked(g)[1], 1), baked(g)[2]) for g in BASES if baked(g)[1] > 0}
    for tt in frames:
        s3, s2 = strays(tt, 3), strays(tt, 2)
        n3 = [sum(v[k_] for v in s3.values()) for k_ in range(2)]
        n2 = [sum(v[k_] for v in s2.values()) for k_ in range(2)]
        worst_new = max(worst_new, n3[0])
        rows.append(dict(t=tt, on_1_60_grid=tt in grid, beat_1_30=any(abs(tt - b_) < 1e-6 for b_ in beats),
                         table_g=tt in table_g, spread_peak=[k_ for k_, v in peaks.items() if abs(v["t"] - tt) < 1e-6],
                         join_spread_pt=join_spread(tt, jp), stray_round3=n3, stray_round3_per_glyph=s3,
                         stray_round2=n2, stray_round2_per_glyph=s2))
        print(f"  W+{tt:.4f}  round 3 strays {n3}  round 2 (composed files) {n2}  spread {rows[-1]['join_spread_pt']}")
    # the full composites of the 6 worst frames (by the round-2 count) + their difference
    order = sorted(rows, key=lambda r: (-r["stray_round2"][1], -r["stray_round2"][0]))
    worst6 = sorted(order[:6], key=lambda r: r["t"])
    rep = dict(about="LOGO-ART-3 key test: LOGO-SPEC's tracks (build/logo/spec/winlogo_keyframes.json; the OUT! anchors = "
                     "the manifest's cream-face centroids) at every 1/60 s frame W+0.60...1.95 (all 1/30 s acceptance beats "
                     "in that range are on this grid) + table G's rows + the frame of the largest relative displacement at "
                     "every join; iPhone 15 @3x (3 device px per pt), each layer resampled on its own (box mip + "
                     "bilinear, premultiplied). stray = device px where a letter / glyph's ink (on-screen alpha > 1/255, "
                     "> 16/255) lies outside its OWN silhouette (its extrusion + face rendered alone on the full canvas, "
                     "placed with its own pose, dilated 2 px). round 3 = the pair files (+ the echo pairs at t - 2/60); "
                     "round 2 = the NEGATIVE CONTROL: the earlier faces baked into rounds 1-2's composed files, drawn with "
                     "the file's pose, outside their owner's silhouette.",
               frames=len(rows), frames_on_1_60_grid=sum(r["on_1_60_grid"] for r in rows),
               beats_1_30_covered=sum(r["beat_1_30"] for r in rows), join_spread_peaks=peaks,
               baked_logo_px2_round1_2=baked_area,
               round3_stray_max_any_frame=[max(r["stray_round3"][k_] for r in rows) for k_ in range(2)],
               round2_stray_max_any_frame=[max(r["stray_round2"][k_] for r in rows) for k_ in range(2)],
               round2_frames_with_visible_strays=sum(1 for r in rows if r["stray_round2"][1] > 0),
               worst6=[r["t"] for r in worst6], rows=rows)
    _motion_sheet(worst6, rep)
    _motion_strip()
    json.dump(rep, open(os.path.join(EVID, "motion.json"), "w"), indent=1)
    print(f"round 3: max strays per frame {rep['round3_stray_max_any_frame']} over {len(rows)} frames; round 2 (negative "
          f"control): max {rep['round2_stray_max_any_frame']}, {rep['round2_frames_with_visible_strays']} frames with "
          f"visible strays; baked areas (logo px^2) {baked_area}; worst frames {rep['worst6']}")
    print("motion:", "OK (0 stray pixels at every frame)" if rep["round3_stray_max_any_frame"] == [0, 0] else "FAIL")
    if rep["round3_stray_max_any_frame"] != [0, 0]:
        sys.exit(1)


def _stray_masks(t, rnd):
    """Full-screen boolean mask of the stray pixels (> 16/255) for the sheet (the same rule as strays())."""
    m_ = np.zeros(SCREEN, bool)
    K = kf()
    for b_ in BASES:
        A, b, al = pose(b_, t)
        if al <= 0.002:
            continue
        if rnd == 3:
            win = screen_box(silhouette(b_).frame, A, b, margin=6)
            ok = NDI.maximum_filter(place_lay(silhouette(b_), A, b, win)[..., 0], size=2 * SIL_DILATE + 1) > 0.5 / 255
            for pid in (EXT[b_], FACE[b_]):
                a_ = place_lay(lay_file(pid, True), A, b, win)[..., 0]
                m_[win[0]:win[0] + win[2], win[1]:win[1] + win[3]] |= (a_ > TAU[1]) & ~ok
        else:
            pieces = baked(b_)[0]
            win = screen_box(rest_frame_pt(b_), A, b, margin=6)
            for hb, L in pieces.items():
                Ah, bh, alh = pose(hb, t)
                own = place_lay(silhouette(hb), Ah, bh, win)[..., 0] if alh > 0.002 else np.zeros(win[2:], np.float32)
                ok = NDI.maximum_filter(own, size=2 * SIL_DILATE + 1) > 0.5 / 255
                m_[win[0]:win[0] + win[2], win[1]:win[1] + win[3]] |= (place_lay(L, A, b, win)[..., 0] > TAU[1]) & ~ok
    return m_


def _rgb(can):
    return Image.fromarray(np.clip(np.round(can[..., :3] * 255), 0, 255).astype(np.uint8), "RGB")


def _motion_sheet(worst6, rep):
    """The 6 worst frames (by round 2's stray count) at 400 % (nearest): round 2 | round 2 with its strays in red | round 3
    | round 3 with its strays in red (none) | |round 2 - round 3| x4, around the strays; + a thumbnail of round 3's frame."""
    rows = []
    for r in worst6:
        t = r["t"]
        c2, c3 = composite(t, 2), composite(t, 3)
        m2, m3 = _stray_masks(t, 2), _stray_masks(t, 3)
        ys, xs = np.nonzero(m2 if m2.any() else m3)
        cy, cx = (int(ys.mean()), int(xs.mean())) if len(xs) else (SCREEN[0] // 2, SCREEN[1] // 2)
        hh, ww = 90, 120
        Y0 = min(max(0, cy - hh // 2), SCREEN[0] - hh)
        X0 = min(max(0, cx - ww // 2), SCREEN[1] - ww)
        crop = (slice(Y0, Y0 + hh), slice(X0, X0 + ww))

        def big(im):
            return im.resize((ww * 4, hh * 4), Image.NEAREST)

        def red(can, m):
            a = np.asarray(_rgb(can[crop])).copy()
            a[m[crop]] = (a[m[crop]] * 0.25 + np.array([255, 0, 0]) * 0.75).astype(np.uint8)
            return Image.fromarray(a)
        d = (np.abs(c2[crop] - c3[crop]) * 255).max(-1)
        thumb = _rgb(c3).resize((SCREEN[1] // 6, SCREEN[0] // 6), Image.BOX)
        ImageDraw.Draw(thumb).rectangle([X0 // 6, Y0 // 6, (X0 + ww) // 6, (Y0 + hh) // 6], outline=(255, 0, 0), width=2)
        rows.append([(big(_rgb(c2[crop])), f"W+{t:.4f} ROUND 2 files (composed glyphs)"),
                     (big(red(c2, m2)), f"round 2 strays in red: {r['stray_round2'][1]} px (>16/255)"),
                     (big(_rgb(c3[crop])), "ROUND 3 pairs (Ext under Face)"),
                     (big(red(c3, m3)), f"round 3 strays in red: {r['stray_round3'][1]} px"),
                     (big(Image.fromarray(np.clip(d * 4, 0, 255).astype(np.uint8), "L")), "|round 2 - round 3| x4"),
                     (thumb, "round 3, whole screen (1/6)")])
    _grid_sheet(rows, "LOGO-ART-3 key test: the 6 worst frames of the ROUND-2 files (by visible strays: a neighbour's face "
                "baked into a composed glyph, moved with the wrong glyph) vs ROUND 3's pairs at the same t; iPhone 15 @3x "
                "device px, 400 % nearest", os.path.join(EVID, "motion_worst_sheet.png"))


def _motion_strip():
    """Round 3 on screen every 1/30 s W+0.683...1.950 (reference pt y 230-640), 1/3 size -- to LOOK at the whole motion."""
    tiles = []
    for t in [round(0.6833 + n / 30, 4) for n in range(39)]:
        c = composite(t, 3)
        im = _rgb(c[int(230 * PXPT):int(640 * PXPT)]).resize((SCREEN[1] // 3, int(410 * PXPT) // 3), Image.BOX)
        ImageDraw.Draw(im).text((6, 4), f"W+{t:.3f}", fill=(255, 0, 0))
        tiles.append(im)
    cols = 8
    w_, h_ = tiles[0].size
    sheet = Image.new("RGB", (cols * (w_ + 6) + 6, math.ceil(len(tiles) / cols) * (h_ + 6) + 30), (236, 240, 247))
    ImageDraw.Draw(sheet).text((6, 8), "LOGO-ART-3: round 3's pairs on screen every 1/30 s (reference pt 230-640, 1/3 size)",
                                fill=(20, 30, 60))
    for i, im in enumerate(tiles):
        sheet.paste(im, (6 + (i % cols) * (w_ + 6), 30 + (i // cols) * (h_ + 6)))
    sheet.save(os.path.join(EVID, "motion_strip.png"), optimize=True)
    print("wrote", os.path.relpath(os.path.join(EVID, "motion_strip.png"), APP))


def pegs_fix2():
    """LOGO-ART-3 finding (2): round 2's evidence named the pegs composite backwards ('sign over pegs'); the composite
    was always the PEGS OVER the sign (over(dst=sign, src=pegs); pegs z 0.5 above the sign's z 0). Recomputes P1-P3
    exactly as round 2's proof did, checks they equal the stored numbers, renames the keys in build/logo/art2/
    reassembly.json and redraws build/logo/art2/pegs_sheet.png with the corrected captions (the files are unchanged)."""
    global EVID
    s, fx, fy, hw = settled_grid()
    px_, py_, pw, ph, pf = frame_of(PEGS)
    sx_, sy_, sw, sh, sf = frame_of("logoSignPurple")
    old_file = pm(Image.open(os.path.join(BACKUP, "out", "logoSignPurple@3x.png")))
    new_sign = pm(shipped("logoSignPurple"))
    peg_lay = np.zeros_like(new_sign)
    X, Y = round((px_ - sx_) * sf), round((py_ - sy_) * sf)
    peg_lay[Y:Y + round(ph * sf), X:X + round(pw * sf)] = pm(shipped(PEGS))
    comp = over(new_sign, peg_lay)                                 # over(dst, src): the PEGS over the sign
    set_p = over(file_settled("logoSignPurple", s, fx, fy, hw), file_settled(PEGS, s, fx, fy, hw))
    set_old = place(old_file, hw, fx + sx_ * s, fy + sy_ * s, s / sf)
    path = os.path.join(EVID2, "reassembly.json")
    r2 = json.load(open(path))
    ren = {"P1_sign_file_over_pegs_file_vs_round1_sign_file": "P1_pegs_file_over_sign_file_vs_round1_sign_file",
           "P2_sign_render_over_pegs_render_vs_round1_sign_render (layering only)":
               "P2_pegs_render_over_sign_render_vs_round1_sign_render (layering only)",
           "P3_sign_and_pegs_files_settled_vs_round1_sign_file_settled":
               "P3_pegs_over_sign_files_settled_vs_round1_sign_file_settled"}
    got = {"P1_pegs_file_over_sign_file_vs_round1_sign_file": stats(comp, old_file),
           "P3_pegs_over_sign_files_settled_vs_round1_sign_file_settled": stats(set_p, set_old)}
    out = {}
    for k_, v in r2.items():
        k2 = ren.get(k_, k_)
        if k2 in got:
            assert got[k2] == v, (k2, got[k2], v)
        out[k2] = v
    out["_labels_corrected"] = ("LOGO-ART-3 (2026-09-27): the P keys said 'sign over pegs'; the composite was always the "
                                "pegs OVER the sign (over(dst=sign, src=pegs); pegs z 0.5 above the sign's z 0). Keys "
                                "renamed, values re-computed and unchanged; pegs_sheet.png redrawn with the corrected captions.")
    json.dump(out, open(path, "w"), indent=1)
    keep = EVID
    try:
        EVID = EVID2
        _sheet_pegs(new_sign, peg_lay, comp, old_file, set_p, set_old, s, fx, fy, out)
    finally:
        EVID = keep
    print("art2 reassembly.json: renamed", [k for k in ren if k in r2], "(values re-computed, equal)")


# ---- at rest
def render_text(svg, w, h, tag):
    """Any SVG text at w x h CSS px -> its raw WebKit 2x render, premultiplied float (cached in SCR as <tag>_raw.png)."""
    raw = os.path.join(SCR, f"{tag}_raw.png")
    if not os.path.exists(raw):
        sp = os.path.join(SCR, f"{tag}.svg")
        open(sp, "w", encoding="utf-8").write(_sized(svg, w, h))
        svgr([dict(svg=sp, out=raw, w=w, h=h)])
    im = Image.open(raw)
    assert im.size == (2 * w, 2 * h), (tag, im.size, "WebKit did not snapshot at 2x")
    return pm(im)


def word_svg(word, frame, factor):
    """One word drawn in ONE piece (every extrusion, then every face: logo_arrow_out's order) on `frame` with the parts'
    clamped filter regions -- the reference for that word's pairs (for OUT! = logoOut's drawing)."""
    m = _g()
    first = EXT[(LETTERS if word == "ARROW" else GLYPHS)[0]]
    svg = m.logo_part_svg(first, frame=frame, factor=factor)
    d, head, L = m._logo_layers()
    body = ([head] + [e for exts, face, gid, sw in L[word] for e in exts] + [face for exts, face, gid, sw in L[word]]
            + ["</g>"])
    return svg[:svg.index("</defs>") + len("</defs>")] + "\n" + "\n".join(body) + "\n</svg>\n"


def _union(bases):
    fr = [frame_of(b_) for b_ in bases]
    x0, y0 = min(f[0] for f in fr), min(f[1] for f in fr)
    x1, y1 = max(f[0] + f[2] for f in fr), max(f[1] + f[3] for f in fr)
    return x0, y0, x1 - x0, y1 - y0


def proof3():
    """Re-assembly at rest of the round-3 stack (LOGO-ART-3) -> build/logo/art3/reassembly.json + reassembly_sheet.png +
    joins_sheet.png. The same measurements as rounds 1-2 (build/logo/art/, build/logo/art2/ reassembly.json):
      A  layering only: the 23 layers' renders on the full canvas (2x) in z order vs the one-piece with the same clamped
         regions (whole logo, each word's window; the fallback with logoOut);
      W  each word: its SHIPPED pair files at their own resolution (OUT! 4.0, ARROW 2.0) composited on the word's union
         frame vs the word drawn in one piece at that resolution (OUT! = logoOut's drawing);
      C  the shipped files on logoArrowOut's 1x grid (23 layers) vs the one-piece; per-file registration;
      D  the shipped files at the SETTLED scale (each resampled on its own, as Core Animation does) vs the one-piece x2
         resampled once (whole, per word, and OUT! vs the one-layer logoOut file);
      S  the joins between neighbouring letters / glyphs at the settled scale."""
    os.makedirs(EVID, exist_ok=True)
    rep = {"stack_bottom_to_top": [[pid, Z[pid]] for pid in LAYERS3],
           "frames_logo_px": {pid: dict(zip(("x", "y", "w", "h", "factor"), frame_of(pid))) for pid in LAYERS3}}
    s, fx, fy, hw = settled_grid()
    rep["settled"] = dict(s=s, device_offset=[fx, fy], grid=list(hw))
    ref2 = fc_whole("whole_same")
    # ---- (A)
    acc, alph = None, {}
    for pid in LAYERS3:
        p = fc(pid)
        alph[pid] = p[..., 3].copy()
        acc = p if acc is None else over(acc, p)
    rep["A_layers23_2x_vs_one_piece_same_regions"] = stats(acc, ref2)
    rep["A_worst"] = worst(acc, ref2, alph, scale=2.0)
    for word, bases in (("ARROW", LETTERS), ("OUT!", GLYPHS)):
        x0, y0, w0, h0 = _union(bases)
        win = (slice(2 * y0, 2 * (y0 + h0)), slice(2 * x0, 2 * (x0 + w0)))
        rep[f"A_{word}_window_2x_vs_one_piece"] = stats(acc[win], ref2[win])
    del acc
    accF = None
    for pid in FALLBACK3:
        p = fc(pid)
        accF = p if accF is None else over(accF, p)
    rep["A_fallback_(logoOut)_2x_vs_one_piece_same_regions"] = stats(accF, ref2)
    del accF
    # ---- (W) the words at the files' own resolution
    truthW = {}
    for word, bases, F, nt in (("OUT!", GLYPHS, 4.0, 3), ("ARROW", LETTERS, 2.0, 2)):
        ux0, uy0, uw, uh = _union(bases)
        cuts = [ux0 + (uw * i) // nt for i in range(nt)] + [ux0 + uw]
        tiles = [box2(render_text(word_svg(word, (a_, uy0, b_ - a_, uh), F), round((b_ - a_) * F), round(uh * F),
                                  f"word_{'OUT' if word == 'OUT!' else word}_x{F:g}_{a_}_{b_ - a_}"))
                 for a_, b_ in zip(cuts[:-1], cuts[1:])]
        ref = np.concatenate(tiles, axis=1)
        del tiles
        acc = np.zeros_like(ref)
        for pid in [EXT[b_] for b_ in bases] + [FACE[b_] for b_ in bases]:
            x, y, w, h, f = frame_of(pid)
            assert f == F
            X, Y = round((x - ux0) * F), round((y - uy0) * F)
            lay = np.zeros_like(ref)
            lay[Y:Y + round(h * F), X:X + round(w * F)] = pm(shipped(pid))
            acc = over(acc, lay)
            del lay
        tag = f"W_{word}_pair_files_x{F:g}_vs_{'logoOut drawing' if word == 'OUT!' else 'ARROW in one piece'}_x{F:g}"
        rep[tag] = stats(acc, ref)
        rep[tag + " (reference quantised like a file)"] = stats(acc, pm(to_img(ref)))
        rep[f"W_{word}_worst"] = worst(acc, ref, {}, scale=F, origin=(-ux0 * F, -uy0 * F))
        rep[f"W_{word}_union_frame_logo_px"] = [ux0, uy0, uw, uh]
        truthW[word] = (ref, F, ux0, uy0, uw, uh)
        del acc
    # ---- (C) the shipped files on the 1x grid
    one = {pid: file_on_grid(pid) for pid in LAYERS3}
    acc1 = np.zeros((CH, CW, 4))
    for pid in LAYERS3:
        acc1 = over(acc1, one[pid])
    ref1 = box2(ref2.astype(np.float64))
    rep["C_shipped_layers23_1x_vs_one_piece_same_regions"] = stats(acc1, ref1)
    rep["C_worst"] = worst(acc1, ref1, {p_: one[p_][..., 3] for p_ in LAYERS3})
    yy, xx = np.mgrid[0:CH, 0:CW]
    reg = {}
    for pid in PAIRS:
        a_f, a_r = one[pid][..., 3], box2(fc(pid).astype(np.float64))[..., 3]
        reg[pid] = dict(centroid_shift_px=[round(float((a_f * xx).sum() / a_f.sum() - (a_r * xx).sum() / a_r.sum()), 4),
                                           round(float((a_f * yy).sum() / a_f.sum() - (a_r * yy).sum() / a_r.sum()), 4)],
                        alpha_sum_ratio=round(float(a_f.sum() / a_r.sum()), 5))
    rep["C_file_registration_vs_own_render_1x"] = reg
    del one
    # ---- (D) the settled scale
    accS = np.zeros(hw + (4,))
    setF = {}
    for pid in LAYERS3:
        setF[pid] = file_settled(pid, s, fx, fy, hw)
        accS = over(accS, setF[pid])
    refHi = place(hires_one_piece(2), hw, fx, fy, s / 4)
    rep["D_shipped_layers23_settled_vs_one_piece_x2_settled"] = stats(accS, refHi)
    for word, bases in (("ARROW", LETTERS), ("OUT!", GLYPHS)):
        x0, y0, w0, h0 = _union(bases)
        win = (slice(int(y0 * s + fy) - 2, int((y0 + h0) * s + fy) + 3), slice(int(x0 * s + fx) - 2, int((x0 + w0) * s + fx) + 3))
        rep[f"D_{word}_window_settled_vs_one_piece_x2"] = stats(accS[win], refHi[win])
        ref, F, ux0, uy0, uw, uh = truthW[word]
        truth = place(ref, hw, fx + ux0 * s, fy + uy0 * s, s / F)
        pairs_ = np.zeros(hw + (4,))
        for pid in [EXT[b_] for b_ in bases] + [FACE[b_] for b_ in bases]:
            pairs_ = over(pairs_, setF[pid])
        rep[f"D_{word}_pair_files_settled_vs_truth (word drawn at x{F:g}, resampled once)"] = stats(pairs_[win], truth[win])
        truthW[word] = truthW[word] + (truth, pairs_, win)
    set_out = file_settled("logoOut", s, fx, fy, hw)
    rep["D_OUT!_pair_files_settled_vs_logoOut_file_settled"] = stats(truthW["OUT!"][7][truthW["OUT!"][8]],
                                                                    set_out[truthW["OUT!"][8]])
    rep["D_OUT!_logoOut_file_settled_vs_truth (the one-layer fallback, for scale)"] = stats(set_out[truthW["OUT!"][8]],
                                                                                          truthW["OUT!"][6][truthW["OUT!"][8]])
    # ---- (S) the joins at the settled scale
    joins = {}
    for word, bases in (("ARROW", LETTERS), ("OUT!", GLYPHS)):
        truth, pairs_ = truthW[word][6], truthW[word][7]
        uni = {b_: 1 - (1 - alph[EXT[b_]]) * (1 - alph[FACE[b_]]) for b_ in bases}
        for a_, b_ in zip(bases, bases[1:]):
            A_, B_ = uni[a_] > 0.02, uni[b_] > 0.02
            ys, xs = np.nonzero(A_ & B_)
            if not len(xs):
                continue
            j = dict(word=word, top=((xs[np.argmin(ys)] + 0.5) / 2, (ys.min() + 0.5) / 2), c=((xs.mean() + 0.5) / 2, (ys.mean() + 0.5) / 2),
                     bottom=((xs[np.argmax(ys)] + 0.5) / 2, (ys.max() + 0.5) / 2),
                     bbox=[xs.min() / 2, ys.min() / 2, (xs.max() + 1) / 2, (ys.max() + 1) / 2])
            x0j, y0j, x1j, y1j = j["bbox"]
            win = (slice(int(y0j * s + fy) - 8, int(y1j * s + fy) + 9), slice(int(x0j * s + fx) - 8, int(x1j * s + fx) + 9))
            j["pair_files_vs_truth"] = stats(pairs_[win], truth[win])
            j["layers23_vs_one_piece_x2"] = stats(accS[win], refHi[win])
            joins[f"{LTR[a_]}|{LTR[b_]}"] = j
    rep["S_joins_settled"] = {k_: {kk: (list(map(lambda v: round(float(v), 1), vv)) if isinstance(vv, (tuple, list)) else vv)
                                   for kk, vv in v.items()} for k_, v in joins.items()}
    # ---- rounds 1-2 for comparison (their own reassembly.json)
    r1 = json.load(open(os.path.join(APP, "build", "logo", "art", "reassembly.json")))
    r2 = json.load(open(os.path.join(EVID2, "reassembly.json")))
    rep["rounds_1_2_for_comparison"] = {
        "round1 A_split_2x_same_regions": r1["A_split_2x_same_regions"],
        "round1 C_shipped_parts_1x_vs_one_piece_same_regions": r1["C_shipped_parts_1x_vs_one_piece_same_regions"],
        "round1 D_shipped_parts_settled_vs_one_piece_x2_settled": r1["D_shipped_parts_settled_vs_one_piece_x2_settled"],
        "round2 A_layers13_2x_vs_one_piece_same_regions": r2["A_layers13_2x_vs_one_piece_same_regions"],
        "round2 G2_glyph_files_4x_vs_logoOut_render_4x": r2["G2_glyph_files_4x_vs_logoOut_render_4x"],
        "round2 G5_glyph_files_settled_vs_truth (OUT! box)": r2["G5_glyph_files_settled_vs_truth (OUT! box)"],
        "round2 C_shipped_layers13_1x_vs_one_piece_same_regions": r2["C_shipped_layers13_1x_vs_one_piece_same_regions"],
        "round2 D_shipped_layers13_settled_vs_one_piece_x2_settled": r2["D_shipped_layers13_settled_vs_one_piece_x2_settled"]}
    json.dump(rep, open(os.path.join(EVID, "reassembly.json"), "w"), indent=1)
    for k_, v in rep.items():
        if k_[:2] in ("A_", "W_", "C_", "D_") and "worst" not in k_ and "frame" not in k_ and "registration" not in k_:
            print(f"{k_:92s} {v}")
    for k_, v in rep["S_joins_settled"].items():
        print(f"  join {k_:6s} pairs vs truth {v['pair_files_vs_truth']}")
    for k_, v in rep["rounds_1_2_for_comparison"].items():
        print(f"  {k_:70s} {v}")
    _sheet3(acc1, ref1, accS, refHi, truthW, joins, s, fx, fy, rep)


def _sheet3(acc1, ref1, accS, refS, truthW, joins, s, fx, fy, rep):
    def ck(p):
        im = to_img(p)
        base = _checker(*im.size)
        base.alpha_composite(im)
        return base
    t1, tS = rep["C_shipped_layers23_1x_vs_one_piece_same_regions"], rep["D_shipped_layers23_settled_vs_one_piece_x2_settled"]
    rows = [[(ck(ref1), "one-piece (part-clamped regions), logo grid 1x"),
             (ck(acc1), "23 SHIPPED layers (pairs) at their frames (1/factor)"),
             (_heat(acc1, ref1), f"|diff| x8  max {t1['max']} p99.9 {t1['p99_9']} >16: {t1['px_gt_16']}")],
            [(ck(refS), "one-piece x2 at the SETTLED scale (k 1.00665)"),
             (ck(accS), "23 files resampled ONE BY ONE, then composited"),
             (_heat(accS, refS), f"|diff| x8  max {tS['max']} p99.9 {tS['p99_9']} >16: {tS['px_gt_16']}")]]
    _grid_sheet(rows, "LOGO-ART-3 re-assembly at rest: logoSignPurple, logoPegs, logoSignBlue, ARROW 5 Ext under 5 Face, OUT! "
                "4 Ext under 4 Face (z order) vs the one-piece drawing", os.path.join(EVID, "reassembly_sheet.png"))
    rows = []
    for bg, bname in ((DIM, "dim 0.894"), ((255, 255, 255), "white")):
        for where in ("top", "c", "bottom"):
            r = []
            for name, j in joins.items():
                truth, pairs_ = truthW[j["word"]][6], truthW[j["word"]][7]
                jx, jy = j[where]
                cx, cy = int(jx * s + fx), int(jy * s + fy)
                box = (slice(cy - 14, cy + 14), slice(cx - 20, cx + 20))
                r += [(_on(truth[box], bg).resize((160, 112), Image.NEAREST), f"{name} {where}: truth ({bname})"),
                      (_on(pairs_[box], bg).resize((160, 112), Image.NEAREST), "pairs (Ext under Face)"),
                      (_heat(pairs_[box], truth[box]).resize((160, 112), Image.NEAREST), "|pairs - truth| x8")]
            rows.append(r)
    _grid_sheet(rows, "LOGO-ART-3 at rest: every join of ARROW and OUT! at the settled scale, 400 % nearest: the word drawn in "
                "one piece (truth) | the pair files each resampled on its own | diff", os.path.join(EVID, "joins_sheet.png"))



# ====================================================================================== round 4 (LOGO-ART-4): colour
# SPEC.md ruling 36 (the second adversarial check of round 3: the Ext trim shows as a light lilac / orange OUTLINE through a
# translucent face while the glyphs fade -- OUT! W+1.033-1.150, ARROW W+0.698-0.757; round 3's '0 stray pixels' test only
# looked at alpha silhouettes). The stack now (LOGO-SPEC §2): OUT!'s 8 Ext / Face layers at opacity 1 inside ONE container
# outGroup carrying OUT!'s opacity with GROUP opacity; the echo one group-opacity container outEcho; each ARROW letter's
# FLAT sprite in its Face slot while its opacity < 1, the pair (at opacity 1) from its first frame at opacity 1.
#   look   THE COLOUR TEST: the full stack exactly as LOGO-SPEC §2 composes it, premultiplied, every layer resampled on its
#          own with TRILINEAR minification (box mip levels 2^L, bilinear in each, blended by the fractional LOD, as Core
#          Animation's .trilinear), iPhone 15 @3x, at every 1/60 s frame W+0.60...1.95 (+ W+0.73, 1.083, 1.133, 1.140,
#          1.455), vs a REFERENCE per frame where each letter / glyph is ONE sprite (its own face over its own UNTRIMMED
#          extrusion, composed at the raw render resolution and area-filtered like a file = the flat recipe), with the same
#          transforms, the same resampler and the same opacities, composited in the one-piece paint order.
#   swap   ruling 36 (b)'s swap proof: each letter as its pair vs as its flat at opacity 1 (the swap frame, every later
#          frame, at rest), alone over the blue sign and in the full frame.
#   fringe4  the pairs' + flats' premultiplied edges over black / white.
LOOK_EXTRA = [0.73, 1.083, 1.133, 1.140, 1.455]
LOOK_T0, LOOK_T1 = 0.60, 1.95
EDGE_CEIL = 41 / 255                             # ruling 36 (b): pair vs flat differ by <= 1-px side-edge columns <= 41/255
VIS = 16 / 255


def a_track(part):
    """A part's opacity track: its own, or (LOGO-ART-4, spec/tools/containers.py) its container's -- the OUT! glyphs'
    opacity lives on outGroup. None = constant 1."""
    p = kf()["parts"][part]
    if "a" in p["tracks"]:
        return p["tracks"]["a"]
    c = p.get("container")
    return kf().get("containers", {}).get(c, {}).get("tracks", {}).get("a") if c else None


def a_own(base, t):
    """The letter / glyph's OWN opacity at t (0 before visibleFrom), without its parent's (the OUT! glyphs: outGroup's)."""
    p = kf()["parts"][base]
    tr = a_track(base)
    return (float(ev(tr, t)[0]) if tr else 1.0) if t >= p["visibleFrom"] - 1e-9 else 0.0


def flat_until(base):
    """LOGO-SPEC's flatUntil of the letter (LOGO-SPEC-FIX L1: ONE time for all five letters); an older spec without it:
    the first key time from which the letter's own opacity track is 1 for good."""
    if "flatUntil" in kf()["parts"][base]:
        return float(kf()["parts"][base]["flatUntil"])
    kt = kf()["parts"][base]["tracks"]["a"]["kf"]
    ts, vs = kt[0::2], kt[1::2]
    i = len(vs)
    while i > 0 and abs(vs[i - 1] - 1.0) < 1e-9:
        i -= 1
    return float(ts[i])


def place_level(L, lev, A, b, win):
    """Layer L's box mip level 2^lev drawn with the map A p + b (rest pt -> screen pt) into win, bilinear, premultiplied."""
    Y0, X0, hh, ww = win
    C = L.a.shape[2]
    H, W = L.a.shape[:2]
    x0, y0, fw, fh = L.frame
    d = 2 ** lev
    src = L.mip(d)
    Lm = PXPT * A @ np.diag([fw / W, fh / H])
    F = Lm * d
    f = PXPT * (A @ (np.array([x0, y0]) + 0.5 * d * np.array([fw / W, fh / H])) + b) - 0.5 - np.array([X0, Y0])
    G = np.linalg.inv(F)
    g = -G @ f
    M = np.array([[G[1, 1], G[1, 0]], [G[0, 1], G[0, 0]]])
    off = np.array([g[1], g[0]])
    out = np.empty((hh, ww, C), np.float32)
    for c in range(C):
        out[..., c] = NDI.affine_transform(src[..., c], M, offset=off, output_shape=(hh, ww), order=1, mode="constant",
                                           cval=0.0, prefilter=False)
    return out


def lod(L, A):
    """Core Animation / Metal trilinear level of detail: log2 of the larger texel-space derivative per screen px."""
    H, W = L.a.shape[:2]
    x0, y0, fw, fh = L.frame
    G = np.linalg.inv(PXPT * A @ np.diag([fw / W, fh / H]))
    return math.log2(max(np.linalg.norm(G[:, 0]), np.linalg.norm(G[:, 1])))


def place_tri(L, A, b, win):
    """TRILINEAR minification (.trilinear): levels floor(lod) and +1, bilinear in each, blended by frac(lod); bilinear on
    the file itself when magnified (.linear)."""
    Y0, X0, hh, ww = win
    if hh <= 0 or ww <= 0:
        return np.zeros((max(hh, 0), max(ww, 0), L.a.shape[2]), np.float32)
    lam = lod(L, A)
    if lam <= 0:
        return place_level(L, 0, A, b, win)
    l0 = int(math.floor(lam))
    fr = lam - l0
    out = place_level(L, l0, A, b, win)
    if fr > 1e-6:
        out = out * np.float32(1 - fr) + place_level(L, l0 + 1, A, b, win) * np.float32(fr)
    return out


_SPR = {}


def sprite(base):
    """The reference sprite of a letter / glyph as a FILE (straight 8-bit, then premultiplied): its own face OVER its own
    UNTRIMMED extrusion composed at the raw WebKit 2x render, then the exact 2:1 area filter (the flat recipe). ARROW: the
    shipped <base>Flat file (asserted equal to this computation); OUT!: computed here (not shipped) and saved as evidence."""
    if base not in _SPR:
        x, y, w, h, f = frame_of(base)
        E = render_part(EXT[base], (x, y, w, h), f, "part", trim=False)
        Fr = render_part(FACE[base], (x, y, w, h), f, "part")
        im = to_img(box2(over(E, Fr)))
        if base in LETTERS:
            sh = shipped(FLAT[base])
            d = np.abs(np.asarray(sh).astype(int) - np.asarray(im).astype(int)).max()
            assert d == 0, (base, "the shipped flat differs from face-over-untrimmed-extrusion", d)
        else:
            os.makedirs(os.path.join(EVID, "ref_sprites"), exist_ok=True)
            im.save(os.path.join(EVID, "ref_sprites", f"{base}Sprite@3x.png"), optimize=True)
        _SPR[base] = Lay(pm(im).astype(np.float32), rest_frame_pt(base))
    return _SPR[base]


R3_BACKUP = os.path.join(EVID, "backup", "out")          # round 3's shipped files (the Ext trimmed at 4 logo px)


def lay_any(pid):
    """'<base>Sprite' = the reference sprite; 'R3:<id>' = round 3's shipped file of <id> (the negative control)."""
    if pid.startswith("R3:"):
        key = (pid, False)
        if key not in _LAY:
            _LAY[key] = Lay(pm(Image.open(os.path.join(R3_BACKUP, f"{pid[3:]}@3x.png")).convert("RGBA")).astype(np.float32),
                            rest_frame_pt(pid[3:]))
        return _LAY[key]
    return sprite(pid[:-len("Sprite")]) if pid.endswith("Sprite") else lay_file(pid)


class Frame:
    """One frame's placements (cached: the stack, the reference and the negative control share them)."""

    def __init__(self, t):
        self.t = t
        self.cache = {}

    def put(self, pid, part, tp):
        key = (pid, part, round(tp, 9))
        if key not in self.cache:
            A, b, _ = pose(part, tp)
            L = lay_any(pid)
            win = screen_box(L.frame, A, b)
            self.cache[key] = (place_tri(L, A, b, win), win)
        return self.cache[key]


def _bg(t):
    can = np.zeros(SCREEN + (4,), np.float32)
    can[..., 3] = 1.0
    can[..., :3] = 1.0 - dim_at(t)
    return can


def _signs(fr, can):
    t = fr.t
    for pid, part in ((sign_image(t), "logoSignPurple"), (PEGS, "logoPegs"), ("logoSignBlue", "logoSignBlue")):
        al = pose(part, t)[2]
        if al > 0.002:
            p, w = fr.put(pid, part, t)
            _over_into(can, p, w, al)


def _union_win(wins):
    Y0 = min(w[0] for w in wins)
    X0 = min(w[1] for w in wins)
    Y1 = max(w[0] + w[2] for w in wins)
    X1 = max(w[1] + w[3] for w in wins)
    return (Y0, X0, Y1 - Y0, X1 - X0)


def _in(win, sub):
    return (sub[0] - win[0], sub[1] - win[1], sub[2], sub[3])


def _group(can, items, alpha):
    """items [(patch, win)] composited in order into a transparent buffer, then OVER the canvas with the group's opacity
    (CALayer allowsGroupOpacity)."""
    if not items or alpha <= 0.002:
        return
    gw = _union_win([w for _, w in items])
    tmp = np.zeros((gw[2], gw[3], 4), np.float32)
    for p, w in items:
        _over_into(tmp, p, _in(gw, w))
    _over_into(can, tmp, gw, alpha)


def a_out(t):
    return a_own("logoOutO", t)


def echo_alpha(t):
    """The echo container's opacity at t: containers.outEcho.tracks.a (LOGO-SPEC-FIX L2: alphaFactor x a_out(t - delay)
    ramped to 0 over the last 3 frames before `until`); an older spec: alphaFactor x a_out(t - delay), cut at `until`."""
    ec = kf()["echo"]
    if t >= ec["until"] - 1e-9:
        return 0.0
    tr = kf().get("containers", {}).get("outEcho", {}).get("tracks", {}).get("a")
    return float(ev(tr, t)[0]) if tr else ec["alphaFactor"] * a_out(t - ec["delay"])


def compose4(fr, variant="round4"):
    """The logo on screen at t - W (premultiplied SCREEN x 4) as LOGO-SPEC §2 composes it.
    variant 'round4'  = ruling 36: ARROW Ext slots (pairs at opacity 1) then Face slots (Face at 1, or the FLAT at the
                        letter's opacity while it is < 1); the echo = one group; OUT! = 4 Ext + 4 Face at 1 in outGroup
                        with group opacity a_out(t).
    variant 'round3'  = the NEGATIVE CONTROL (what round 3's stack does with per-layer opacity): every pair layer at its
                        letter's / glyph's opacity, no flats, no outGroup (the echo was already one group).
    variant ('swap', base, 'pair'|'flat') = round4 but letter `base` forced to its pair or its flat at opacity 1."""
    t = fr.t
    can = _bg(t)
    _signs(fr, can)
    ec = kf()["echo"]
    force = variant if isinstance(variant, tuple) else None
    # ---- ARROW (in the blue sign; pose() carries the sign's map and opacity)
    ext_slot, face_slot = [], []
    for b_ in LETTERS:
        A_, B_, al = pose(b_, t)
        if al <= 0.002:
            continue
        own = a_own(b_, t)
        if variant == "round3":                               # round 3's files (Ext trim 4), per-layer opacity
            ext_slot.append(("R3:" + EXT[b_], b_, al))
            face_slot.append((FACE[b_], b_, al))
            continue
        mode = force[2] if force and force[1] == b_ else ("pair" if t >= flat_until(b_) - 1e-9 else "flat")
        par = al / max(own, 1e-9)                              # the parent's opacity (the blue sign)
        if mode == "pair":
            ext_slot.append((EXT[b_], b_, par))
            face_slot.append((FACE[b_], b_, par))
        else:
            face_slot.append((FLAT[b_], b_, al if not force or force[1] != b_ else par))
    for pid, part, al in ext_slot + face_slot:
        p, w = fr.put(pid, part, t)
        _over_into(can, p, w, al)
    # ---- the echo (one group) and OUT! (outGroup)
    r3 = (lambda pid: "R3:" + pid if pid in EXT.values() else pid) if variant == "round3" else (lambda pid: pid)
    if t < ec["until"]:
        te = t - ec["delay"]
        ae = echo_alpha(t)
        if ae > 0.002:
            items = [fr.put(r3(pid), BASE_OF[pid], te) for pid in OUT_PAIRS]
            _group(can, items, ae)
    ao = a_out(t)
    if ao > 0.002:
        if variant == "round3":
            for pid in OUT_PAIRS:
                p, w = fr.put(r3(pid), BASE_OF[pid], t)
                _over_into(can, p, w, ao)
        else:
            _group(can, [fr.put(pid, BASE_OF[pid], t) for pid in OUT_PAIRS], ao)
    return can


def _word_ref(fr, bases, tp, alphas, can=None):
    """The reference for one word: each letter / glyph ONE sprite S = F + X (F = its face file, X = S - F = the exposed
    part of its untrimmed extrusion; the same resampler), composited in the ONE-PIECE PAINT ORDER (every extrusion under
    every face) -- top down F_n ... F_1, X_n ... X_1, each covering its alpha of what is still visible, where a glyph's X
    only covers the part its OWN face left (coverage aX / (1 - aF): face and exposed extrusion are disjoint inside a
    glyph, so alone S == F + X exactly, like the one sprite; between glyphs 'over'). -> (patch, win) premultiplied, or
    None; over `can` when given (the letters over the signs), else transparent (a group)."""
    items = []
    for b_, a_ in zip(bases, alphas):
        if a_ <= 0.002:
            continue
        Fp, wF = fr.put(FACE[b_], b_, tp)
        Sp, wS = fr.put(b_ + "Sprite", b_, tp)
        assert wF == wS
        X = np.clip(Sp - Fp, 0.0, None)
        X[..., :3] = np.minimum(X[..., :3], X[..., 3:4])
        items.append((Fp, X, wF, np.float32(a_)))
    if not items:
        return None
    gw = _union_win([w for _, _, w, _ in items])
    T = np.ones((gw[2], gw[3], 1), np.float32)
    C = np.zeros((gw[2], gw[3], 3), np.float32)
    for Fp, X, w, a_ in reversed(items):                      # faces, top down
        y, x, hh, ww = _in(gw, w)
        sl = (slice(y, y + hh), slice(x, x + ww))
        C[sl] += T[sl] * a_ * Fp[..., :3]
        T[sl] *= 1.0 - a_ * Fp[..., 3:4]
    for Fp, X, w, a_ in reversed(items):                      # exposed extrusions, top down, disjoint with their own face
        y, x, hh, ww = _in(gw, w)
        sl = (slice(y, y + hh), slice(x, x + ww))
        den = 1.0 - a_ * Fp[..., 3:4]
        ok = den > 1e-4
        cov = np.where(ok, a_ * X[..., 3:4] / np.where(ok, den, 1.0), 0.0).clip(0.0, 1.0)
        col = np.where(ok, a_ * X[..., :3] / np.where(ok, den, 1.0), 0.0)
        C[sl] += T[sl] * col
        T[sl] *= 1.0 - cov
    if can is not None:
        Y0, X0, hh, ww = gw
        dst = can[Y0:Y0 + hh, X0:X0 + ww]
        dst[..., :3] = C + T * dst[..., :3]
        dst[..., 3:4] = 1.0 - T * (1.0 - dst[..., 3:4])
        return None
    return np.concatenate([C, 1.0 - T], -1), gw


def compose_ref(fr, order="onepiece"):
    """The REFERENCE frame: the same signs, pegs, dim, echo and opacities; every letter / glyph ONE sprite (face over its
    own untrimmed extrusion). order 'onepiece' = the one-piece paint order (_word_ref); 'glyph' = the sprites simply
    stacked glyph after glyph (A < R1 < ... ; O < U < T < !) -- differs from the one-piece only where a later glyph's
    extrusion meets an earlier glyph's face."""
    t = fr.t
    can = _bg(t)
    _signs(fr, can)
    ec = kf()["echo"]
    al = [pose(b_, t)[2] for b_ in LETTERS]
    if order == "onepiece":
        _word_ref(fr, LETTERS, t, al, can)
    else:
        for b_, a_ in zip(LETTERS, al):
            if a_ > 0.002:
                p, w = fr.put(b_ + "Sprite", b_, t)
                _over_into(can, p, w, a_)
    for tp, ga, on in ((t - ec["delay"], echo_alpha(t), t < ec["until"]), (t, a_out(t), True)):
        if not on or ga <= 0.002:
            continue
        if order == "onepiece":
            r = _word_ref(fr, GLYPHS, tp, [1.0] * 4)
            if r is not None:
                _over_into(can, r[0], r[1], ga)
        else:
            _group(can, [fr.put(g + "Sprite", g, tp) for g in GLYPHS], ga)
    return can


def glyph_cov(fr):
    """Per letter / glyph its sprite's on-screen alpha (x its opacity) at t (and the echo's at t - delay, labelled '~'):
    {label: (alpha patch, win)} for the masks (ink, overlap, silhouette edges, which glyph a pixel belongs to)."""
    t = fr.t
    ec = kf()["echo"]
    out = {}
    for b_ in LETTERS:
        al = pose(b_, t)[2]
        if al > 0.002:
            p, w = fr.put(b_ + "Sprite", b_, t)
            out[LTR[b_]] = (p[..., 3] * al, w)
    for tp, ga, tag in ((t, a_out(t), ""), (t - ec["delay"], echo_alpha(t), "~")):
        if tag and t >= ec["until"]:
            continue
        if ga > 0.002:
            for g in GLYPHS:                                   # 'OUT O' ... ('~' = its echo copy): the letter O is 'O'
                p, w = fr.put(g + "Sprite", g, tp)
                out["OUT " + LTR[g] + tag] = (p[..., 3] * ga, w)
    return out


def _full(patch, win):
    m_ = np.zeros(SCREEN, np.float32)
    Y0, X0, hh, ww = win
    m_[Y0:Y0 + hh, X0:X0 + ww] = patch
    return m_


def run_lengths(m_):
    """The longest horizontal and vertical run of True in a boolean image."""
    def longest(a):
        best = 0
        for r_ in a:
            if r_.any():
                e = np.diff(np.r_[0, r_.astype(np.int8), 0])
                best = max(best, int((np.nonzero(e == -1)[0] - np.nonzero(e == 1)[0]).max()))
        return best
    return longest(m_), longest(m_.T)


def pieces_of(m_, d, edge):
    """The pixels of mask m_ as connected pieces (8-connectivity): count, the longest (bbox extent, px), px in 2x2 blocks
    (0 = every piece is at most ONE device px thick: a 1-px column / line / dot), the share on a silhouette edge."""
    if not m_.any():
        return dict(n=0)
    lab, n = NDI.label(m_, structure=np.ones((3, 3)))
    ps = []
    for j, sl in enumerate(NDI.find_objects(lab)):
        comp = lab[sl] == j + 1
        ps.append(dict(px=int(comp.sum()), extent=int(max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)),
                       max=round(float(d[sl][comp].max()), 1), at_px=[int(sl[1].start), int(sl[0].start)],
                       on_edge=round(float((edge[sl] & comp).sum() / comp.sum()), 2) if edge is not None else None))
    ps.sort(key=lambda q: (-q["extent"], -q["px"]))
    b2 = m_[:-1, :-1] & m_[1:, :-1] & m_[:-1, 1:] & m_[1:, 1:]
    hr, vr = run_lengths(m_)
    return dict(n=n, longest=ps[0], top3=ps[:3], blocks_2x2=int(b2.sum()), longest_row_run=hr, longest_col_run=vr)


def analyse(stack, ref, cov):
    """|stack - ref| on the device grid (max over R, G, B, in /255) inside the letters' / glyphs' ink (any sprite alpha
    > 0.5/255): max, p99.9, mean, px > 16 and > 41; the > 16 px split by where they are (on a silhouette edge = within 1 px
    of a sprite alpha in (0.02, 0.98); inside an overlap of two letters / glyphs, dilated 2 px) and by owner (the glyph
    with the most coverage there), and as connected pieces (pieces_of)."""
    d = np.abs(stack[..., :3] - ref[..., :3]).max(-1) * 255.0
    ink = np.zeros(SCREEN, bool)
    n_on = np.zeros(SCREEN, np.uint8)
    edge = np.zeros(SCREEN, bool)
    best = np.zeros(SCREEN, np.float32)
    owner = np.full(SCREEN, -1, np.int16)
    labels = list(cov)
    for i, k in enumerate(labels):
        a_, (Y0, X0, hh, ww) = cov[k]
        sl = (slice(Y0, Y0 + hh), slice(X0, X0 + ww))
        ink[sl] |= a_ > 0.5 / 255
        n_on[sl] += (a_ > 1 / 255).astype(np.uint8)
        edge[sl] |= (a_ > 0.02) & (a_ < 0.98)
        up = a_ > best[sl]
        best[sl] = np.where(up, a_, best[sl])
        owner[sl] = np.where(up, i, owner[sl])
    overlap = NDI.binary_dilation(n_on >= 2, iterations=2)
    edge = NDI.binary_dilation(edge, iterations=1)
    di = d[ink]
    m16 = d > 16
    res = dict(ink_px=int(ink.sum()), max=round(float(d.max()), 2),
               p99_9=round(float(np.percentile(di, 99.9)), 2) if di.size else 0.0,
               mean=round(float(di.mean()), 4) if di.size else 0.0, gt16=int(m16.sum()), gt41=int((d > 41).sum()),
               outside_ink_max=round(float(d[~ink].max()), 2) if (~ink).any() else 0.0,
               gt16_on_silhouette_edge=int((m16 & edge).sum()), gt16_in_glyph_overlap=int((m16 & overlap).sum()),
               gt16_per_glyph={k: int((m16 & (owner == i)).sum()) for i, k in enumerate(labels) if (m16 & (owner == i)).any()},
               gt41_outside_glyph_overlap=int(((d > 41) & ~overlap).sum()),
               pieces=pieces_of(m16, d, edge))
    res["max_per_word"], res["gt41_per_word"], res["gt16_per_word"] = {}, {}, {}
    for word, idx in (("ARROW", [i for i, k in enumerate(labels) if not k.startswith("OUT")]),
                      ("OUT!", [i for i, k in enumerate(labels) if k.startswith("OUT")])):
        mw = np.isin(owner, idx) & ink
        res["max_per_word"][word] = round(float(d[mw].max()), 2) if mw.any() else 0.0
        res["gt41_per_word"][word] = int(((d > 41) & mw).sum())
        res["gt16_per_word"][word] = int(((d > 16) & mw).sum())
    return res, d


def look():
    """THE COLOUR TEST (LOGO-ART-4, ruling 36 (c)) -> build/logo/art4/look.json + look_worst_sheet.png +
    look_named_sheet.png + look_strip.png."""
    os.makedirs(EVID, exist_ok=True)
    grid = [round(LOOK_T0 + n / 60, 6) for n in range(int(round((LOOK_T1 - LOOK_T0) * 60)) + 1)]
    frames = sorted(set(grid) | set(LOOK_EXTRA))
    rows = []
    for tt in frames:
        fr = Frame(tt)
        st, rf = compose4(fr), compose_ref(fr)
        cov = glyph_cov(fr)
        r4, d4 = analyse(st, rf, cov)
        del d4
        rs = compose_ref(fr, "glyph")
        rS, _ = analyse(st, rs, cov)
        del rs
        neg = compose4(fr, "round3")
        r3, _ = analyse(neg, rf, cov)
        del st, rf, neg, fr
        row = dict(t=tt, on_1_60_grid=tt in grid, named=tt in LOOK_EXTRA,
                   flats=[LTR[b_] for b_ in LETTERS if 0.002 < pose(b_, tt)[2] and tt < flat_until(b_) - 1e-9],
                   out_opacity=round(a_out(tt), 3), echo_opacity=round(echo_alpha(tt), 4),
                   echo=bool(echo_alpha(tt) > 0.002),
                   round4_vs_ref=r4,
                   round4_vs_ref_glyph_order={k: rS[k] for k in ("max", "p99_9", "gt16", "gt16_in_glyph_overlap")},
                   round3_negative_control_vs_ref={k: r3[k] for k in ("max", "p99_9", "gt16", "gt16_per_glyph", "max_per_word",
                                                                      "gt16_per_word")} |
                   {"longest_piece_px": r3["pieces"].get("longest", {}).get("extent", 0)})
        rows.append(row)
        p4 = r4["pieces"]
        print(f"  W+{tt:.4f}  round4 max {r4['max']:6.2f} p99.9 {r4['p99_9']:5.2f} >16 {r4['gt16']:5d} >41 {r4['gt41']:3d} "
              f"(edge {r4['gt16_on_silhouette_edge']}, overlap {r4['gt16_in_glyph_overlap']}, pieces {p4['n']}"
              + (f", longest {p4['longest']['extent']} px, 2x2 {p4['blocks_2x2']}" if p4['n'] else "") +
              f")  | round3 control >16 {r3['gt16']:5d} max {r3['max']:6.2f}  | glyph-order ref >16 {rS['gt16']}"
              f"  flats {row['flats']} outA {row['out_opacity']}", flush=True)
    worst6 = sorted(sorted(rows, key=lambda r: (-r["round4_vs_ref"]["gt16"], -r["round4_vs_ref"]["max"]))[:6],
                    key=lambda r: r["t"])
    R = [r["round4_vs_ref"] for r in rows]
    summ = dict(frames=len(rows), frames_on_1_60_grid=sum(r["on_1_60_grid"] for r in rows),
                round4_max_any_frame=max(r["max"] for r in R), round4_p99_9_max=max(r["p99_9"] for r in R),
                round4_gt16_max_per_frame=max(r["gt16"] for r in R), round4_gt41_total=sum(r["gt41"] for r in R),
                round4_frames_with_gt16=sum(1 for r in R if r["gt16"]), round4_gt16_total=sum(r["gt16"] for r in R),
                round4_gt16_total_on_edge=sum(r["gt16_on_silhouette_edge"] for r in R),
                round4_gt16_total_in_overlap=sum(r["gt16_in_glyph_overlap"] for r in R),
                round4_gt41_outside_glyph_overlap_total=sum(r["gt41_outside_glyph_overlap"] for r in R),
                round4_gt41_outside_glyph_overlap_max_per_frame=max(r["gt41_outside_glyph_overlap"] for r in R),
                round4_max_per_word={w: max(r["max_per_word"][w] for r in R) for w in ("ARROW", "OUT!")},
                round4_gt41_per_word_total={w: sum(r["gt41_per_word"][w] for r in R) for w in ("ARROW", "OUT!")},
                round4_gt16_per_word_max_per_frame={w: max(r["gt16_per_word"][w] for r in R) for w in ("ARROW", "OUT!")},
                round4_OUT_frames_W1_022_to_1_155_max=max((r["round4_vs_ref"]["max_per_word"]["OUT!"] for r in rows
                                                            if 1.022 <= r["t"] < 1.155), default=0),
                round4_longest_piece_px=max((r["pieces"]["longest"]["extent"] for r in R if r["pieces"]["n"]), default=0),
                round4_blocks_2x2_total=sum(r["pieces"].get("blocks_2x2", 0) for r in R),
                round4_longest_row_run=max((r["pieces"].get("longest_row_run", 0) for r in R), default=0),
                round4_longest_col_run=max((r["pieces"].get("longest_col_run", 0) for r in R), default=0),
                glyph_order_ref_gt16_max_per_frame=max(r["round4_vs_ref_glyph_order"]["gt16"] for r in rows),
                round3_negative_control_gt16_max_per_frame=max(r["round3_negative_control_vs_ref"]["gt16"] for r in rows),
                round3_negative_control_max=max(r["round3_negative_control_vs_ref"]["max"] for r in rows),
                round3_negative_control_frames_with_gt16=sum(1 for r in rows if r["round3_negative_control_vs_ref"]["gt16"]),
                round3_negative_control_gt16_max_per_glyph_per_frame=max((max(r["round3_negative_control_vs_ref"]["gt16_per_glyph"].values(),
                                                                                default=0) for r in rows), default=0),
                worst6=[r["t"] for r in worst6])
    rep = dict(about=("LOGO-ART-4 colour test (SPEC.md ruling 36 (c)): LOGO-SPEC §2's stack (outGroup with group opacity, "
                      "the echo group, each ARROW letter's flat while its opacity < 1, the pairs at opacity 1, the bend "
                      "variants, the pegs, the dim) vs a REFERENCE where each letter / glyph is ONE sprite (its own face "
                      "over its own UNTRIMMED extrusion, composed at the raw render and area-filtered like a file; the ARROW "
                      "flats ARE these sprites) in the one-piece paint order (every extrusion under every face: sprite = "
                      "face + exposed extrusion, disjoint inside a glyph, 'over' between glyphs), with the same "
                      "transforms, opacities (OUT! and the echo as groups, letters per letter) and resampler. iPhone 15 @3x "
                      "(3 device px per pt), premultiplied, every layer resampled on its own with TRILINEAR minification "
                      "(box mips 2^L, bilinear in each, blended by the fractional LOD). Numbers in /255 of the device-px "
                      "colour (max over R, G, B) inside the letters' / glyphs' ink; gt16 = device px > 16/255; pieces = "
                      "the gt16 px as 8-connected pieces (blocks_2x2 = 0: no piece is thicker than one device px). "
                      "round4_vs_ref_glyph_order = the same stack vs the sprites simply stacked glyph after glyph (it "
                      "differs only where a later glyph's extrusion meets an earlier glyph's face). "
                      "round3_negative_control = round 3's stack (per-layer opacity on the pairs, no flats, no outGroup) "
                      "vs the same reference: the adversarial check's outline."),
               summary=summ, flat_until={LTR[b_]: flat_until(b_) for b_ in LETTERS}, rows=rows)
    json.dump(rep, open(os.path.join(EVID, "look.json"), "w"), indent=1)
    print(json.dumps(summ, indent=1))
    _look_sheet([r["t"] for r in worst6], rows, "look_worst_sheet.png",
                "LOGO-ART-4 colour test: the 6 WORST frames of the round-4 stack (by px > 16/255)")
    _look_sheet(LOOK_EXTRA, rows, "look_named_sheet.png",
                "LOGO-ART-4 colour test: the named frames W+0.73, 1.083, 1.133, 1.140, 1.455")
    _look_strip()
    return rep


def _crop_at(d, centre, hh=100, ww=140):
    """A crop of hh x ww device px: on the densest cluster of px > 16/255 of d, else on d's largest pixel (if > 4), else
    on `centre`."""
    if d.max() > 16:
        dens = NDI.uniform_filter((d > 16).astype(np.float32), size=(hh // 2, ww // 2))
        cy, cx = np.unravel_index(int(dens.argmax()), d.shape)
    elif d.max() > 4:
        cy, cx = np.unravel_index(int(d.argmax()), d.shape)
    else:
        cy, cx = centre
    Y0 = int(min(max(0, cy - hh // 2), SCREEN[0] - hh))
    X0 = int(min(max(0, cx - ww // 2), SCREEN[1] - ww))
    return (slice(Y0, Y0 + hh), slice(X0, X0 + ww)), (Y0, X0)


def _red(can, m):
    a = np.asarray(_rgb(can)).copy()
    a[m] = (a[m] * 0.2 + np.array([255, 0, 0]) * 0.8).astype(np.uint8)
    return Image.fromarray(a)


def _look_sheet(ts, rows, name, title):
    """Per frame, a 140 x 100 device-px crop at 400 % (nearest) where the round-4 stack differs most from the reference
    (else where round 3's control does, else the glyphs' centre): round 4 | reference | |diff| x4 | round 4 with px > 16
    red | round 3's stack (control) with its px > 16 red | the whole logo at 1/2 with the crop box."""
    out = []
    byt = {r["t"]: r for r in rows}
    for t in ts:
        fr = Frame(t)
        st, rf, neg = compose4(fr), compose_ref(fr), compose4(fr, "round3")
        d4 = np.abs(st[..., :3] - rf[..., :3]).max(-1) * 255
        d3 = np.abs(neg[..., :3] - rf[..., :3]).max(-1) * 255
        r = byt[t]["round4_vs_ref"]
        cov = glyph_cov(fr)
        ys, xs = [], []
        for a_, w in cov.values():
            yy, xx = np.nonzero(a_ > 0.5)
            ys += list(yy + w[0])
            xs += list(xx + w[1])
        centre = (int(np.median(ys)), int(np.median(xs))) if ys else (SCREEN[0] // 2, SCREEN[1] // 2)
        sl, (Y0, X0) = _crop_at(d4 if d4.max() > 4 else d3, centre)

        def big(im):
            return im.resize((im.size[0] * 4, im.size[1] * 4), Image.NEAREST)
        top, bot = int(200 * PXPT), int(700 * PXPT)
        thumb = _rgb(st[top:bot]).resize((SCREEN[1] // 2, (bot - top) // 2), Image.BOX)
        ImageDraw.Draw(thumb).rectangle([X0 // 2, (Y0 - top) // 2, (X0 + 140) // 2, (Y0 + 100 - top) // 2],
                                        outline=(255, 0, 0), width=2)
        out.append([(big(_rgb(st[sl])), f"W+{t:.4f} ROUND 4 stack (LOGO-SPEC §2)"),
                    (big(_rgb(rf[sl])), "REFERENCE (one sprite per glyph)"),
                    (big(Image.fromarray(np.clip(d4[sl] * 4, 0, 255).astype(np.uint8), "L")),
                     f"|round4 - ref| x4: max {r['max']:.1f} p99.9 {r['p99_9']:.1f} >16: {r['gt16']}"),
                    (big(_red(st[sl], d4[sl] > 16)), "round 4, px > 16/255 in red"),
                    (big(_red(neg[sl], d3[sl] > 16)),
                     f"round-3 stack (control), >16 red: {byt[t]['round3_negative_control_vs_ref']['gt16']} px"),
                    (thumb, "round 4, whole logo (pt 200-700, 1/2 device px), crop box")])
        del st, rf, neg, d4, d3
    _grid_sheet(out, title + "; iPhone 15 @3x device px, crops at 400 % nearest", os.path.join(EVID, name))


def _look_strip():
    """The round-4 stack every 1/30 s W+0.60...1.95 (reference pt y 230-640, 1/3 size) -- to LOOK at the whole motion."""
    tiles = []
    for t in [round(0.60 + n / 30, 4) for n in range(41)]:
        c = compose4(Frame(t))
        im = _rgb(c[int(230 * PXPT):int(640 * PXPT)]).resize((SCREEN[1] // 3, int(410 * PXPT) // 3), Image.BOX)
        ImageDraw.Draw(im).text((6, 4), f"W+{t:.3f}", fill=(255, 0, 0))
        tiles.append(im)
    cols = 8
    w_, h_ = tiles[0].size
    sheet = Image.new("RGB", (cols * (w_ + 6) + 6, math.ceil(len(tiles) / cols) * (h_ + 6) + 30), (236, 240, 247))
    ImageDraw.Draw(sheet).text((6, 8), "LOGO-ART-4: the round-4 stack (LOGO-SPEC §2) every 1/30 s (reference pt 230-640, 1/3 size)",
                                fill=(20, 30, 60))
    for i, im in enumerate(tiles):
        sheet.paste(im, (6 + (i % cols) * (w_ + 6), 30 + (i // cols) * (h_ + 6)))
    sheet.save(os.path.join(EVID, "look_strip.png"), optimize=True)
    print("wrote", os.path.relpath(os.path.join(EVID, "look_strip.png"), APP))


def swap():
    """Ruling 36 (b): each letter as its PAIR (Ext + Face at opacity 1) vs as its FLAT at opacity 1 -- the swap frame (the
    first 1/60 s frame at opacity 1), the exact flatUntil, every later 1/60 s frame to W+1.95 and at rest (W+2.40); alone
    (the letter over the blue sign, nothing else of ARROW) and in the full frame. -> build/logo/art4/swap.json + sheet."""
    os.makedirs(EVID, exist_ok=True)
    grid = [round(LOOK_T0 + n / 60, 6) for n in range(int(round((LOOK_T1 - LOOK_T0) * 60)) + 1)]
    rep, tiles = {}, []
    for b_ in LETTERS:
        fu = flat_until(b_)
        swap_t = min(t for t in grid if t >= fu - 1e-9)
        ts = sorted({fu, 2.40} | {t for t in grid if t >= fu - 1e-9})
        rows = []
        for t in ts:
            fr = Frame(t)
            A, bb, al = pose(b_, t)
            pe, w = fr.put(EXT[b_], b_, t)
            pf, _ = fr.put(FACE[b_], b_, t)
            pF, _ = fr.put(FLAT[b_], b_, t)
            bgp, _ = fr.put("logoSignBlue", "logoSignBlue", t)
            Ab, bb2, _ = pose("logoSignBlue", t)
            base = np.zeros((w[2], w[3], 4), np.float32)
            base[..., 3] = 1.0
            base[..., :3] = 1.0 - dim_at(t)
            wb = fr.cache[("logoSignBlue", "logoSignBlue", round(t, 9))][1]
            # the blue sign under the letter (clipped to the letter's window)
            y0, x0 = max(w[0], wb[0]), max(w[1], wb[1])
            y1, x1 = min(w[0] + w[2], wb[0] + wb[2]), min(w[1] + w[3], wb[1] + wb[3])
            if y1 > y0 and x1 > x0:
                sub = bgp[y0 - wb[0]:y1 - wb[0], x0 - wb[1]:x1 - wb[1]]
                dst = base[y0 - w[0]:y1 - w[0], x0 - w[1]:x1 - w[1]]
                dst *= 1.0 - sub[..., 3:4]
                dst += sub
            alone_pair = base.copy()
            _over_into(alone_pair, pe, (0, 0, w[2], w[3]))
            _over_into(alone_pair, pf, (0, 0, w[2], w[3]))
            alone_flat = base.copy()
            _over_into(alone_flat, pF, (0, 0, w[2], w[3]))
            da = np.abs(alone_pair[..., :3] - alone_flat[..., :3]).max(-1) * 255
            sil = pF[..., 3]
            edge = NDI.binary_dilation((sil > 0.02) & (sil < 0.98), iterations=1)

            def pieces(dd, ed):
                m16 = dd > 16
                q = pieces_of(m16, dd, ed)
                return dict(gt16=int(m16.sum()), gt41=int((dd > 41).sum()),
                            gt16_on_silhouette_edge=int((m16 & ed).sum()), pieces=q["n"],
                            longest_piece_px=q.get("longest", {}).get("extent", 0), blocks_2x2=q.get("blocks_2x2", 0),
                            longest_row_run=q.get("longest_row_run", 0), longest_col_run=q.get("longest_col_run", 0))
            ra = dict(max=round(float(da.max()), 2), **pieces(da, edge))
            rc = None
            if t == swap_t or t == 2.40 or abs(t - fu) < 1e-9:     # the full frame: everything else as it is then
                cp, cf = compose4(fr, ("swap", b_, "pair")), compose4(fr, ("swap", b_, "flat"))
                dc = np.abs(cp[..., :3] - cf[..., :3]).max(-1) * 255
                Y0, X0 = w[0], w[1]
                dcl = dc[Y0:Y0 + w[2], X0:X0 + w[3]]
                out_ = dc.copy()
                out_[Y0:Y0 + w[2], X0:X0 + w[3]] = 0
                rc = dict(max=round(float(dc.max()), 2), outside_letter_window_max=round(float(out_.max()), 2),
                          **pieces(dcl, edge))
                del cp, cf, dc, out_
            rows.append(dict(t=t, swap_frame=t == swap_t, exact_flat_until=abs(t - fu) < 1e-9, at_rest=t == 2.40,
                             scale=round(float(np.sqrt(abs(np.linalg.det(A)))), 4), alone=ra, full_frame=rc))
            if t in (swap_t, 2.40):
                m_ = da > 16
                cy, cx = np.unravel_index(int((NDI.uniform_filter(m_.astype(np.float32), size=15) if m_.any() else da).argmax()),
                                          da.shape)
                sl = (slice(max(0, cy - 30), cy + 30), slice(max(0, cx - 40), cx + 40))

                def big(im):
                    return im.resize((im.size[0] * 4, im.size[1] * 4), Image.NEAREST)
                tiles.append([(big(_rgb(alone_pair[sl])), f"{LTR[b_]} W+{t:.4f} PAIR (Ext + Face at 1)"),
                              (big(_rgb(alone_flat[sl])), "FLAT at 1"),
                              (big(Image.fromarray(np.clip(da[sl] * 4, 0, 255).astype(np.uint8), "L")),
                               f"|pair - flat| x4: max {ra['max']:.1f}, >16: {ra['gt16']}"),
                              (big(_red(alone_pair[sl], m_[sl])), "pair, px > 16/255 red"),
                              (_rgb(alone_pair), "the whole letter (100 %)")])
        worst = max(rows, key=lambda r: r["alone"]["max"])
        rep[LTR[b_]] = dict(flat_until=fu, swap_frame=swap_t,
                            swap=next(r for r in rows if r["swap_frame"]),
                            at_rest=next(r for r in rows if r["at_rest"]),
                            worst_alone_any_frame=dict(t=worst["t"], **worst["alone"]),
                            max_alone_all_frames=max(r["alone"]["max"] for r in rows),
                            gt16_alone_max_per_frame=max(r["alone"]["gt16"] for r in rows),
                            gt41_alone_all_frames=sum(r["alone"]["gt41"] for r in rows),
                            blocks_2x2_alone_all_frames=sum(r["alone"]["blocks_2x2"] for r in rows),
                            longest_piece_alone_all_frames=max(r["alone"]["longest_piece_px"] for r in rows), rows=rows)
        print(f"  {LTR[b_]:2s} flatUntil {fu:.3f} swap frame W+{swap_t:.4f}: alone {rep[LTR[b_]]['swap']['alone']}  "
              f"full {rep[LTR[b_]]['swap']['full_frame']}  | all frames: max alone {rep[LTR[b_]]['max_alone_all_frames']}, "
              f">41 {rep[LTR[b_]]['gt41_alone_all_frames']}, 2x2 {rep[LTR[b_]]['blocks_2x2_alone_all_frames']}, longest "
              f"{rep[LTR[b_]]['longest_piece_alone_all_frames']} px", flush=True)
    json.dump(rep, open(os.path.join(EVID, "swap.json"), "w"), indent=1)
    _grid_sheet(tiles, "LOGO-ART-4 swap proof (ruling 36 (b)): each letter as its pair vs its flat at opacity 1, at the swap "
                "frame and at rest, over the blue sign; device px @3x, 400 % nearest", os.path.join(EVID, "swap_sheet.png"))
    return rep


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "proof"
    {"measure": measure, "manifest": lambda: manifest_entries(sys.argv[2:] or None), "proof": proof, "fringe": fringe, "clean": clean, "verify": verify,
     "geometry": show_geometry, "upscale": upscale, "bendcal": bend_calibrate, "proof3": proof3, "motion": motion,
     "fringe3": lambda: fringe(PAIRS, neg="logoOutTFace", title="LOGO-ART-3 pairs"), "pegsfix2": pegs_fix2,
     "fringe4": lambda: fringe(PAIRS + FLATS, neg="logoLetterR2Flat", title="LOGO-ART-4 pairs + flats"), "look": look,
     "swap": swap}[cmd]()
