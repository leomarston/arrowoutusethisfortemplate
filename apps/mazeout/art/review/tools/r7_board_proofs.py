#!/usr/bin/env python3
"""R7 BOARD-UI proofs and checks (PUBLISH, PLAN-P §4.2). Proof images and JSON only; nothing here ships.

    PY=~/.venvs/mf3d/bin/python                       # from apps/mazeout
    $PY art/review/tools/r7_board_proofs.py geometry  # per id: frame px, anchor, alpha bbox + alpha diff, before vs after
    $PY art/review/tools/r7_board_proofs.py key       # DoorLayer.withoutRibbon on the new key: the ribbon goes, the key stays
    $PY art/review/tools/r7_board_proofs.py boards    # 6 levels drawn the way the engine draws them, measured skin | D1 skin
    $PY art/review/tools/r7_board_proofs.py distance  # colour distance per sprite + per board (copygate chroma overlap)
    $PY art/review/tools/r7_board_proofs.py all

"before" = the measured-skin files snapshotted in build/p/R7/before (the committed art + the App/Board colour literals as
they were); "after" = art/ui/out + the D1 literals now in App/Board / board.json. The board renderer follows the App/Board
code: tapes (TapeLayer: centred on the bundle's block, pitch/32), doors (DoorLayer: doorW4H8 9-sliced, lock at the block
centre + 0.18 p), keys (KeyNode: anchorFrac, orientation per direction), pipes (PipeLayer: the banded tube, mouths,
counter + live digits), boxes (CounterLayer: the code slab + boxRing + digits), elevators (ElevatorLayer: doors, rim,
hatch, divider), corners (CornerNode: cornerWedge in the p x p cell, rotated per turn), dots (DotsPainter) and the arrows
(board.json arrow metrics, approximately: round-capped 0.22 p strokes + the measured head). Output: build/p/R7/.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

APP = os.getcwd()
OUT = os.path.join(APP, "art", "ui", "out")
BEFORE = os.path.join(APP, "build", "p", "R7", "before")
EV = os.path.join(APP, "build", "p", "R7")
LEVELS = os.path.join(APP, "App", "Resources", "Levels")
FONT = os.path.join(APP, "design", "fonts", "PCDisplay-Black.ttf")
sys.path.insert(0, os.path.join(APP, "art", "ui", "src"))
sys.path.insert(0, os.path.join(APP, "art", "ui", "src", "svg"))
sys.path.insert(0, os.path.join(APP, "tools"))

IDS_SVG = ["tapeV2", "tapeV3", "tapeV4", "tapeH2", "tapeH3", "tapeH4", "doorW4H4", "doorW4H8", "doorW4H12", "doorW4H16",
           "doorW4H20", "doorW5H17", "doorW13H4", "doorW11H10", "doorW22H10", "lockHex", "keyOnArrow", "pipeMouth",
           "pipeCounter", "curtainCrate", "boxSlab", "boxRing", "unlockIconPipe", "unlockIconLinked", "unlockIconBox",
           "unlockIconElevator", "doorShards", "pipeShards", "tutorialHand", "pointerArrowYellow", "pointerArrowDown",
           "pageBgPattern", "unlockIconDoor", "unlockIconCurtain"]
IDS_3D = ["cornerWedge", "cornerDownRightSpring", "cornerDownRightPlate", "cornerDownLeftSpring", "cornerDownLeftPlate",
          "cornerUpRightSpring", "cornerUpRightPlate", "cornerUpLeftSpring", "cornerUpLeftPlate", "unlockIconCorner"]
ALL = IDS_SVG + IDS_3D
PROOF_LEVELS = [13, 39, 52, 58, 76, 93]     # box+tape · door+key+pipe · box+elevator · box+door+key+tape · corner+pipe · corner+tape


def img(path):
    return Image.open(path).convert("RGBA")


def before(i):
    return img(os.path.join(BEFORE, "out", f"{i}@3x.png"))


def after(i):
    return img(os.path.join(OUT, f"{i}@3x.png"))


def abbox(a, thr):
    ys, xs = np.nonzero(a >= thr)
    return None if len(xs) == 0 else [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


# ----------------------------------------------------------------------------------------------------------- geometry

def generator_anchors():
    """Anchor (pt) each generator reports, measured skin vs D1 skin (SVG ids)."""
    import gen_board as GB
    import gen_board_ui as GU
    import gen_icons as GI
    import gen_missing as GM
    out = {}
    for i in IDS_SVG:
        if i.startswith("doorW") and i not in GB.CASES:
            w, h = i[5:].split("H")
            GB.door_case(int(w), int(h))
        if i in GU.CASES:                       # D1 = the wrapper; measured = the wrapped generator
            d1_fn = GU.CASES[i]
            ms_fn = GI.CASES[i] if i in GI.CASES else GM.CASES[i]
        else:                                   # gen_board (and the two card icons that only embed gen_board parts)
            d1_fn = ms_fn = GB.CASES[i] if i in GB.CASES else GI.CASES[i]
        res = d1_fn()
        GB.SKIN = "measured"
        try:
            res0 = ms_fn()
        finally:
            GB.SKIN = "d1"
        anc = lambda r: list(r[1]["anchor"]) if isinstance(r, tuple) and r[1] and r[1].get("anchor") else None  # noqa: E731
        out[i] = (anc(res0), anc(res))
    return out


def cmd_geometry():
    lane = {e["id"]: e for e in json.load(open(os.path.join(APP, "art", "lanes", "board-ui.entries.json")))["entries"]}
    man = {e["id"]: e for e in json.load(open(os.path.join(APP, "art", "MANIFEST.json")))["entries"]}
    anchors = generator_anchors()
    rows, fails = [], []
    for i in ALL:
        b, a = before(i), after(i)
        ab, aa = np.asarray(b)[..., 3].astype(int), np.asarray(a)[..., 3].astype(int)
        same_size = b.size == a.size
        d = np.abs(ab - aa) if same_size else None
        r = dict(id=i, size_px_before=list(b.size), size_px_after=list(a.size), size_equal=same_size,
                 bbox_a1_before=abbox(ab, 1), bbox_a1_after=abbox(aa, 1),
                 bbox_a128_before=abbox(ab, 128), bbox_a128_after=abbox(aa, 128),
                 alpha_max_diff=int(d.max()) if d is not None else None,
                 alpha_px_diff_gt8=int((d > 8).sum()) if d is not None else None,
                 manifest_anchor_pt=man[i].get("anchor_pt"), lane_anchor_pt=lane[i].get("anchor_pt"),
                 manifest_size_pt=man[i].get("size_pt"), lane_size_pt=lane[i].get("size_pt"))
        if i in anchors:
            r["generator_anchor_measured"], r["generator_anchor_d1"] = anchors[i]
        r["anchor_equal"] = (r["manifest_anchor_pt"] == r["lane_anchor_pt"]
                             and (i not in anchors or anchors[i][0] == anchors[i][1]))
        r["bbox_equal"] = r["bbox_a1_before"] == r["bbox_a1_after"] and r["bbox_a128_before"] == r["bbox_a128_after"]
        ok = same_size and r["anchor_equal"] and r["bbox_equal"] and r["manifest_size_pt"] == r["lane_size_pt"]
        r["pass"] = bool(ok)
        rows.append(r)
        if not ok:
            fails.append(i)
        print(f"{'PASS' if ok else 'FAIL'} {i:22s} {b.size} bbox {r['bbox_a1_after']} anchor {r['lane_anchor_pt']} "
              f"alpha maxdiff {r['alpha_max_diff']} (>8: {r['alpha_px_diff_gt8']} px)")
    json.dump(dict(rows=rows, fails=fails), open(os.path.join(EV, "geometry.json"), "w"), indent=1)
    print(f"geometry: {len(ALL) - len(fails)}/{len(ALL)} ids identical frame + anchor + alpha bbox; fails {fails}")
    return not fails


# ----------------------------------------------------------------------------------------------------------- key filter

def without_ribbon(im):
    """DoorLayer.withoutRibbon: keep only r > 70 && r >= g && g >= b + 25 (straight colours; alpha > 0)."""
    a = np.asarray(im).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    return (al > 0) & (r > 70) & (r >= g) & (g >= b + 25), al > 0


def cmd_key():
    kb, lb = without_ribbon(before("keyOnArrow"))
    ka, la = without_ribbon(after("keyOnArrow"))
    # the ribbon region: the loop above the ring (y < ~0.3 of the frame top part), i.e. the pixels the measured filter
    # drops that are opaque
    ribbon_b = lb & ~kb
    ribbon_a = la & ~ka
    iou_keep = float((kb & ka).sum() / max(1, (kb | ka).sum()))
    res = dict(kept_before=int(kb.sum()), kept_after=int(ka.sum()), dropped_before=int(ribbon_b.sum()),
               dropped_after=int(ribbon_a.sum()), kept_iou=round(iou_keep, 4),
               teal_ribbon_pixels_surviving=int((ka & ribbon_b).sum()))
    ok = iou_keep > 0.97 and res["teal_ribbon_pixels_surviving"] < 0.01 * ribbon_b.sum()
    res["pass"] = bool(ok)
    json.dump(res, open(os.path.join(EV, "key_filter.json"), "w"), indent=1)
    print("key filter:", res)
    # a proof: before | after | after filtered, on white
    tiles = [before("keyOnArrow"), after("keyOnArrow")]
    f = np.asarray(after("keyOnArrow")).copy()
    f[~ka] = 0
    tiles.append(Image.fromarray(f, "RGBA"))
    W = sum(t.width for t in tiles) + 40
    S = Image.new("RGBA", (W, tiles[0].height + 20), (255, 255, 255, 255))
    x = 10
    for t in tiles:
        S.alpha_composite(t, (x, 10))
        x += t.width + 10
    S.convert("RGB").save(os.path.join(EV, "sheets", "key_filter.png"))
    return ok


# ----------------------------------------------------------------------------------------------------------- board render

MEASURED = dict(
    exit="#10A2EF", dot="#C5E1FF",
    pipe=[(0, 1.0, "#A6A6A6", 0.35, -0.05, 0.15), (0, 1.02, "#1597D6", 0.52), (-0.355, 0.19, "#1E8FCF", 0.62),
          (-0.18, 0.16, "#27A6E0", 0.55), (-0.015, 0.17, "#6ED2F8", 0.58), (0.11, 0.08, "#9DE2FB", 0.9),
          (0.24, 0.18, "#3DBFF2", 0.55), (0.37, 0.08, "#33BCF1", 0.55), (0.465, 0.09, "#32CFF9", 0.9),
          (-0.48, 0.05, "#2BCCF2", 0.85)],
    pipe_digit="#822521",
    box=dict(lip="#4F2F83", lip2="#582D96", lip3="#AB50EB", edge="#5935A2", mid="#9A4BE0", face="#BC5BF6", bevel="#ECB2F3",
             rivet="#7A34C4", rivet_hi="#E3C0FF", digit="#4B1F86"),
    elev=dict(fill="#CDBFF3", stroke="#9A88D8", rim="#B9A9EC", hatch="#8C79CF"),
    sprites=os.path.join(BEFORE, "out"))


def d1_palette():
    cc = json.load(open(os.path.join(EV, "code_colours.json")))["plan"]
    m = {}
    for t in cc.values():
        m.update(t)
    P = json.loads(json.dumps(MEASURED))
    P["exit"], P["dot"] = "#FF8F1F", "#FFDDB0"
    P["pipe"] = [tuple([b[0], b[1], m.get(b[2], b[2])] + list(b[3:])) for b in MEASURED["pipe"]]
    P["pipe_digit"] = m[MEASURED["pipe_digit"]]
    P["box"] = {k: m.get(v, v) for k, v in MEASURED["box"].items()}
    P["elev"] = {k: m.get(v, v) for k, v in MEASURED["elev"].items()}
    P["sprites"] = OUT
    return P


def rgba(hx, a=1.0):
    hx = hx.lstrip("#")
    return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4)) + (int(round(a * 255)),)


class Board:
    """Content drawn at K px per pt with pitch p pt; SS supersampling for the vector parts."""

    def __init__(self, lvl, pal, width_pt=393.0, K=3):
        self.l, self.pal, self.K = lvl, pal, K
        cols, rows = lvl["cols"], lvl["rows"]
        self.p = min((width_pt - 16) / cols, 600.0 / rows, 28.07)
        self.pp = self.p * K
        self.m = 8 * K
        W = int(cols * self.pp + 2 * self.m)
        H = int(rows * self.pp + 2 * self.m)
        self.im = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        self.obs = {o["id"]: o for o in lvl.get("obstacles", [])}

    def c(self, cell):
        return (self.m + (cell[0] + 0.5) * self.pp, self.m + (cell[1] + 0.5) * self.pp)

    def sprite(self, i):
        return img(os.path.join(self.pal["sprites"], f"{i}@3x.png"))

    def put(self, sp, x, y, anchor_frac=(0.5, 0.5), scale=None, rot_cw_deg=0.0, transform=None):
        """Place a sprite (drawn at 96 px per cell) so that its anchor lands on (x, y) px; rot about the anchor."""
        k = self.pp / 96.0 if scale is None else scale
        w, h = max(1, round(sp.width * k)), max(1, round(sp.height * k))
        s = sp.resize((w, h), Image.LANCZOS)
        ax, ay = anchor_frac[0] * w, anchor_frac[1] * h
        if transform == "transpose":
            s = s.transpose(Image.TRANSPOSE)
            ax, ay = ay, ax
        elif transform == "antitranspose":
            s = s.transpose(Image.TRANSVERSE)
            ax, ay = s.width - ay, s.height - ax
        if rot_cw_deg:
            big = Image.new("RGBA", (s.width * 3, s.height * 3), (0, 0, 0, 0))
            big.alpha_composite(s, (s.width, s.height))
            cx, cy = s.width + ax, s.height + ay
            big = big.rotate(-rot_cw_deg, resample=Image.BICUBIC, center=(cx, cy))
            s, ax, ay = big, cx, cy
        self.im.alpha_composite(s, (int(round(x - ax)), int(round(y - ay))))

    def layer(self):
        return Image.new("RGBA", self.im.size, (0, 0, 0, 0))

    # ---- parts
    def dots(self, arrows):
        L = self.layer()
        d = ImageDraw.Draw(L)
        r = 0.192 * self.pp / 2
        for a in arrows:
            for cell in a["cells"]:
                x, y = self.c(cell)
                d.ellipse([x - r, y - r, x + r, y + r], fill=rgba(self.pal["dot"]))
        self.im.alpha_composite(L)

    def arrows(self, arrows, colour="#000000"):
        SS = 2
        L = Image.new("RGBA", (self.im.width * SS, self.im.height * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        w = 0.22 * self.pp * SS
        col = rgba(colour)
        for a in arrows:
            pts = [(x * SS, y * SS) for x, y in (self.c(c) for c in a["cells"])]
            if len(pts) == 1:
                pts = pts * 2
            # tail extension 0.14 p past the tail centre (board.json arrow.tailExtend + half width)
            (x0, y0), (x1, y1) = pts[0], pts[1]
            L0 = math.hypot(x1 - x0, y1 - y0) or 1
            pts[0] = (x0 - (x1 - x0) / L0 * 0.03 * self.pp * SS, y0 - (y1 - y0) / L0 * 0.03 * self.pp * SS)
            d.line(pts, fill=col, width=int(w), joint="curve")
            x0, y0 = pts[0]
            d.ellipse([x0 - w / 2, y0 - w / 2, x0 + w / 2, y0 + w / 2], fill=col)
            hx, hy = pts[-1]
            dx, dy = {"right": (1, 0), "left": (-1, 0), "up": (0, -1), "down": (0, 1)}[a["dir"]]
            base, tip, hw = -0.22 * self.pp * SS, 0.375 * self.pp * SS, 0.61 / 2 * self.pp * SS
            bx, by = hx + dx * base, hy + dy * base
            tri = [(hx + dx * tip, hy + dy * tip), (bx - dy * hw, by + dx * hw), (bx + dy * hw, by - dx * hw)]
            d.polygon(tri, fill=col)
        self.im.alpha_composite(L.resize(self.im.size, Image.LANCZOS))

    def block(self, cells):
        xs, ys = [c[0] for c in cells], [c[1] for c in cells]
        x0, y0 = self.m + min(xs) * self.pp, self.m + min(ys) * self.pp
        return x0, y0, x0 + (max(xs) - min(xs) + 1) * self.pp, y0 + (max(ys) - min(ys) + 1) * self.pp

    def tape(self, o):
        cols, rows = len({c[0] for c in o["cells"]}), len({c[1] for c in o["cells"]})
        lanes = max(len(o["cells"]), len(o.get("arrows", [])))
        sid = o.get("sprite") or (f"tapeV{lanes}" if rows >= cols else f"tapeH{lanes}")
        pts = [self.c(c) for c in o["cells"]]
        cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
        cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
        self.put(self.sprite(sid), cx, cy)

    def door(self, o):
        x0, y0, x1, y1 = self.block(o["cells"])
        d = self.sprite("doorW4H8")
        w, h = d.width, d.height
        cell = (h - w) / 4
        margin = (w - 4 * cell) / 2
        post = margin + 0.72 * cell
        k = self.pp / cell
        rows = round((y1 - y0) / self.pp)
        topH = round(margin + 2 * cell)
        top = d.crop((0, 0, w, topH))
        mid = d.crop((0, topH, w, topH + round(cell)))
        by = round(margin + 7 * cell)
        bot = d.crop((0, by, w, h))
        outer_w = (x1 - x0) + 2 * margin * k

        def slice_(s, target_h):
            # 9-slice horizontally: fixed posts (scaled by k), stretched centre
            pl = s.crop((0, 0, round(post), s.height)).resize((max(1, round(post * k)), max(1, round(target_h))), Image.LANCZOS)
            pr = s.crop((s.width - round(post), 0, s.width, s.height)).resize(pl.size, Image.LANCZOS)
            cw = max(1, round(outer_w - 2 * pl.width))
            pc = s.crop((round(post), 0, s.width - round(post), s.height)).resize((cw, pl.height), Image.LANCZOS)
            out = Image.new("RGBA", (pl.width * 2 + cw, pl.height), (0, 0, 0, 0))
            out.alpha_composite(pl, (0, 0)); out.alpha_composite(pc, (pl.width, 0)); out.alpha_composite(pr, (pl.width + cw, 0))
            return out
        ox, oy = x0 - margin * k, y0 - margin * k
        t = slice_(top, top.height * k)
        self.im.alpha_composite(t, (round(ox), round(oy)))
        yy = oy + t.height
        for _ in range(max(0, rows - 3)):
            mm = slice_(mid, self.pp)
            self.im.alpha_composite(mm, (round(ox), round(yy)))
            yy += self.pp
        b = slice_(bot, bot.height * k)
        self.im.alpha_composite(b, (round(ox), round(oy + (y1 - y0) + 2 * margin * k - b.height)))
        self.put(self.sprite("lockHex"), (x0 + x1) / 2, (y0 + y1) / 2 + 0.18 * self.pp)

    def key(self, o, arrows):
        cells = [tuple(c) for c in o["cells"]]
        a = next((x for x in arrows if x["id"] in o.get("arrows", [])), None)
        if a and len(cells) >= 2:
            ac = [tuple(c) for c in a["cells"]]
            if ac.index(cells[1]) < ac.index(cells[0]):
                cells = [cells[1], cells[0]]
        first = cells[0]
        second = cells[1] if len(cells) > 1 else first
        d = (second[0] - first[0], second[1] - first[1])
        x, y = self.c(first)
        af = (19.84 / 43.0, 27.52 / 78.0)
        sp = self.sprite("keyOnArrow")
        if d == (0, 1):
            self.put(sp, x, y, af)
        elif d == (0, -1):
            self.put(sp, x, y, af, rot_cw_deg=180)
        elif d == (1, 0):
            self.put(sp, x, y, af, transform="transpose")
        else:
            self.put(sp, x, y, af, transform="antitranspose")

    def digits(self, n, x, y, h, outline, ow):
        f = ImageFont.truetype(FONT, max(6, int(h * 1.35)))
        L = self.layer()
        d = ImageDraw.Draw(L)
        d.text((x, y), str(n), font=f, fill=(255, 255, 255, 255), anchor="mm", stroke_width=max(1, int(ow)),
               stroke_fill=rgba(outline))
        self.im.alpha_composite(L)

    def pipe(self, o):
        cells = [tuple(c) for c in o["cells"]]
        ends = o.get("ends", [])
        pts = [self.c(c) for c in cells]
        if len(pts) == 1:
            pts = pts * 2
        dirs = {"down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0)}
        for e, idx in ((ends[0], 0), (ends[-1], -1)) if len(ends) == 2 else ():
            if tuple(e["cell"]) == cells[idx]:
                dx, dy = dirs[e["out"]]
                x, y = pts[idx]
                pts[idx] = (x + dx * 0.2 * self.pp, y + dy * 0.2 * self.pp)
        SS = 2
        for band in self.pal["pipe"]:
            o_, w, hx, al = band[:4]
            dx = band[4] if len(band) > 4 else o_
            dy = band[5] if len(band) > 5 else -o_
            L = Image.new("RGBA", (self.im.width * SS, self.im.height * SS), (0, 0, 0, 0))
            ImageDraw.Draw(L).line([((x + dx * self.pp) * SS, (y + dy * self.pp) * SS) for x, y in pts],
                                   fill=rgba(hx), width=max(1, int(w * self.pp * SS)), joint="curve")
            L = L.resize(self.im.size, Image.LANCZOS)
            a = np.asarray(L).copy()
            a[..., 3] = (a[..., 3].astype(float) * al).astype(np.uint8)
            self.im.alpha_composite(Image.fromarray(a, "RGBA"))
        rot = {"down": 0, "up": 180, "left": 90, "right": -90}
        for e in ends:
            x, y = self.c(e["cell"])
            self.put(self.sprite("pipeMouth"), x, y, (23.04 / 47.0, 9.6 / 30.0), rot_cw_deg=rot[e["out"]])
        at = o.get("counter_at")
        if at and o.get("counter") is not None:
            x = self.m + (at[0] + 0.5) * self.pp
            y = self.m + (at[1] + 0.5) * self.pp
            vertical = at[1] != round(at[1])
            if not vertical and at[0] == round(at[0]):
                c0 = (int(at[0]), int(at[1]))
                if c0 in cells:
                    i = cells.index(c0)
                    n = cells[i + 1] if i + 1 < len(cells) else cells[i - 1]
                    vertical = n[0] == c0[0]
            self.put(self.sprite("pipeCounter"), x, y, (34.0 / 68.0, 24.9 / 53.0), rot_cw_deg=90 if vertical else 0)
            self.digits(o["counter"], x, y + (0 if vertical else 0.02 * self.pp), 0.56 * self.pp, self.pal["pipe_digit"],
                        0.13 * self.pp * 0.5)

    def box(self, o):
        x0, y0, x1, y1 = self.block(o["cells"])
        P = self.pal["box"]
        p = self.pp
        SS = 2
        L = Image.new("RGBA", (self.im.width * SS, self.im.height * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        r = 0.40 * p

        def rr(rc, rad, fill, alpha=1.0):
            a, b, c, e = rc
            rad = min(rad, (c - a) / 2, (e - b) / 2)
            d.rounded_rectangle([a * SS, b * SS, c * SS, e * SS], radius=max(0, rad * SS), fill=rgba(fill, alpha))
        H = y1 - y0
        rr((x0, y0 + 0.1 * p, x1, y1 + 0.1 * p), r, "#000000", 0.16)
        rr((x0, y0, x1, y1), r, P["lip"])
        rr((x0, y0, x1, y1 - 0.09 * p), r, P["lip2"])
        rr((x0, y0, x1, y1 - 0.19 * p), r, P["lip3"])
        fy1 = y1 - 0.28 * p
        rr((x0, y0, x1, fy1), r, P["edge"])
        rr((x0 + 0.13 * p, y0, x1 - 0.13 * p, fy1), max(0, r - 0.1 * p), P["mid"])
        rr((x0 + 0.26 * p, y0 + 0.02 * p, x1 - 0.26 * p, fy1 - 0.02 * p), max(0, r - 0.2 * p), P["face"])
        d.line([((x0 + r) * SS, (y0 + 0.05 * p) * SS), ((x1 - r) * SS, (y0 + 0.05 * p) * SS)], fill=rgba(P["bevel"]),
               width=max(1, int(0.045 * p * SS)))
        ins, rd = 0.35 * p, 0.15 * p
        for x, y in ((x0 + ins, y0 + ins), (x1 - ins, y0 + ins), (x0 + ins, fy1 - ins), (x1 - ins, fy1 - ins)):
            d.ellipse([(x - rd) * SS, (y - rd) * SS, (x + rd) * SS, (y + rd) * SS], fill=rgba(P["rivet"]))
            d.ellipse([(x - rd * 0.75) * SS, (y - rd * 0.8) * SS, (x - rd * 0.75 + rd * 0.9) * SS, (y - rd * 0.8 + rd * 0.8) * SS],
                      fill=rgba(P["rivet_hi"], 0.9))
        self.im.alpha_composite(L.resize(self.im.size, Image.LANCZOS))
        short = min(x1 - x0, H)
        dia = 0.85 * short if short < 2.5 * p else 2.2 * p
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - 0.14 * p
        ring = self.sprite("boxRing")
        self.put(ring, cx, cy, scale=dia / ring.width)
        if o.get("counter") is not None:
            self.digits(o["counter"], cx, cy, 0.8 * p * dia / (2.2 * p) * 0.72, P["digit"], 0.12 * p * dia / (2.2 * p) * 0.5)

    def elevator(self, o):
        x0, y0, x1, y1 = self.block(o["cells"])
        P = self.pal["elev"]
        p = self.pp
        rim = 0.22 * p
        SS = 2
        L = Image.new("RGBA", (self.im.width * SS, self.im.height * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        ix0, iy0, ix1, iy1 = x0 + rim, y0 + rim, x1 - rim, y1 - rim
        mx = (x0 + x1) / 2
        for a, b in ((ix0, mx), (mx, ix1)):
            d.rectangle([a * SS, iy0 * SS, b * SS, iy1 * SS], fill=rgba(P["fill"], 0.62), outline=rgba(P["stroke"], 0.9),
                        width=max(1, int(0.06 * p * SS)))
        d.rounded_rectangle([(x0 + rim / 2) * SS, (y0 + rim / 2) * SS, (x1 - rim / 2) * SS, (y1 - rim / 2) * SS],
                            radius=0.3 * p * SS, outline=rgba(P["rim"], 0.95), width=max(1, int(rim * SS)))
        step = 0.3 * p
        t = x0 - rim
        while t < x1:
            for yb in (y0, y1 - rim):
                a0, a1 = max(x0, t), min(x1, t + rim)
                d.line([(a0 * SS, (yb + rim - (a0 - t)) * SS), (a1 * SS, (yb + rim - (a1 - t)) * SS)],
                       fill=rgba(P["hatch"], 0.8), width=max(1, int(0.05 * p * SS)))
            t += step
        y = y0 + rim
        while y < y1 - rim:
            yy = min(y1 - rim, y + rim)
            for xb in (x0, x1 - rim):
                d.line([(xb * SS, yy * SS), ((xb + (yy - y)) * SS, y * SS)], fill=rgba(P["hatch"], 0.8),
                       width=max(1, int(0.05 * p * SS)))
            y += step
        d.line([(mx * SS, iy0 * SS), (mx * SS, iy1 * SS)], fill=rgba(P["hatch"]), width=max(1, int(0.08 * p * SS)))
        self.im.alpha_composite(L.resize(self.im.size, Image.LANCZOS))

    def corner(self, o):
        x, y = self.c(o["cells"][0])
        ang = {"upRight": 0, "upLeft": 90, "downLeft": 180, "downRight": -90}[o.get("turn", "upRight")]
        sp = self.sprite("cornerWedge")
        # CornerNode today: the 64 pt (2 x 2 pitch) sprite in a p x p layer, rotated about the cell centre; a positive
        # CA angle turns clockwise on screen
        self.put(sp, x, y, scale=self.pp / sp.width, rot_cw_deg=ang)

    def draw(self):
        arrows = self.l["arrows"]
        shown = [a for a in arrows if a.get("hidden_by") is None and a.get("layer", 1) == 1]
        self.dots(shown)
        kinds = {}
        for o in self.obs.values():
            kinds.setdefault(o["kind"], []).append(o)
        for o in kinds.get("elevator", []):
            self.elevator(o)
        self.arrows(shown)
        for o in kinds.get("tape", []):
            self.tape(o)
        for o in kinds.get("key", []):
            self.key(o, arrows)
        for o in kinds.get("pipe", []):
            self.pipe(o)
        for o in kinds.get("box", []) + kinds.get("curtain", []):
            self.box(o)
        for o in kinds.get("door", []):
            self.door(o)
        for o in kinds.get("corner", []):
            self.corner(o)
        return self.im


def level(n):
    return json.load(open(os.path.join(LEVELS, f"level_{n:04d}.json")))


def cmd_boards():
    os.makedirs(os.path.join(EV, "boards"), exist_ok=True)
    P1 = d1_palette()
    lab = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 28)
    for n in PROOF_LEVELS:
        lv = level(n)
        a = Board(lv, MEASURED).draw()
        b = Board(lv, P1).draw()
        a.convert("RGB").save(os.path.join(EV, "boards", f"L{n:03d}-measured.png"))
        b.convert("RGB").save(os.path.join(EV, "boards", f"L{n:03d}-d1.png"))
        S = Image.new("RGB", (a.width * 2 + 30, a.height + 50), (220, 220, 220))
        S.paste(a.convert("RGB"), (10, 40))
        S.paste(b.convert("RGB"), (a.width + 20, 40))
        d = ImageDraw.Draw(S)
        kinds = sorted({o["kind"] for o in lv.get("obstacles", [])})
        d.text((10, 6), f"L{n}  measured skin (before)", font=lab, fill=(0, 0, 0))
        d.text((a.width + 20, 6), f"L{n}  D1 skin (after)   {'+'.join(kinds)}", font=lab, fill=(0, 0, 0))
        S = S.resize((S.width // 2, S.height // 2), Image.LANCZOS)
        S.save(os.path.join(EV, "sheets", f"board_L{n:03d}.png"))
        print("board", n, a.size, kinds)
    return True


# ----------------------------------------------------------------------------------------------------------- distance

def cmd_distance():
    import copygate as CG
    import d1_skin as S
    rows = []
    tmp = os.path.join(EV, "tmp")
    os.makedirs(tmp, exist_ok=True)
    for i in ALL:
        b, a = before(i), after(i)
        bg = (0, 49, 53, 255) if i == "pageBgPattern" else (255, 255, 255, 255)
        pb, pa = os.path.join(tmp, f"{i}_b.png"), os.path.join(tmp, f"{i}_a.png")
        for im, p in ((b, pb), (a, pa)):
            c = Image.new("RGBA", im.size, (11, 33, 118, 255) if (i == "pageBgPattern" and p == pb) else bg)
            c.alpha_composite(im)
            c.convert("RGB").save(p)
        m = CG.measure(pa, pb, cmin=8.0)
        # mean colour of the opaque, chromatic pixels (what the eye reads as "the obstacle's colour")
        def mean_col(im):
            x = np.asarray(im).astype(float)
            al = x[..., 3] > 200
            px = x[al][:, :3]
            return S.rgb_hex(px.mean(0)) if len(px) else None
        mb, ma = mean_col(b), mean_col(a)
        rows.append(dict(id=i, chroma_overlap=round(m["overlap"], 3), ssim=round(m["ssim"], 3),
                         mean_before=mb, mean_after=ma, mean_de00=round(S.de00(mb, ma), 1) if mb and ma else None))
    boards = []
    for n in PROOF_LEVELS:
        pm = os.path.join(EV, "boards", f"L{n:03d}-measured.png")
        pd = os.path.join(EV, "boards", f"L{n:03d}-d1.png")
        if os.path.exists(pm):
            m = CG.measure(pd, pm, cmin=8.0)
            boards.append(dict(level=n, chroma_overlap_cmin8=round(m["overlap"], 3), ssim=round(m["ssim"], 3)))
    json.dump(dict(sprites=rows, boards=boards, note="copygate.measure(ours=D1, theirs=measured skin, chroma_min 8): "
                   "informative (no 'sprite'/'board' kind in tools/copygate.json); SSIM stays high by design (ruling 46: "
                   "same shapes)"), open(os.path.join(EV, "distance.json"), "w"), indent=1)
    for r in rows:
        print(f"{r['id']:22s} overlap {r['chroma_overlap']:.3f}  mean {r['mean_before']} -> {r['mean_after']}  ΔE00 {r['mean_de00']}")
    for r in boards:
        print("board", r)
    return True


if __name__ == "__main__":
    os.makedirs(os.path.join(EV, "sheets"), exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    ok = True
    for name, fn in (("geometry", cmd_geometry), ("key", cmd_key), ("boards", cmd_boards), ("distance", cmd_distance)):
        if what in (name, "all"):
            ok = fn() and ok
    sys.exit(0 if ok else 1)
