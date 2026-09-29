#!/usr/bin/env python3
"""Proof sheets for the corner lane (art/lanes/corner.md): our corner layers composed IN PLACE over the phone's lossless
shots at each corner's lattice anchor, at game size and zoomed, plus the unlock-card icon over shot 456.

    PY=~/.venvs/mf3d/bin/python                         # from apps/mazeout
    $PY art/ui/recipes/corner_proofs.py board           # art/ui/sheets/corner/board_<level>.png + board_all.png (every corner)
    $PY art/ui/recipes/corner_proofs.py facings         # art/ui/sheets/corner/facings.png: capture | ours | in place | diff, x4
    $PY art/ui/recipes/corner_proofs.py card            # art/ui/sheets/corner/card_456.png
    $PY art/ui/recipes/corner_proofs.py bounce          # art/ui/sheets/corner/bounce.png: the hit animation spec applied
    $PY art/ui/recipes/corner_proofs.py clip            # art/ui/sheets/corner/clip.png: S2-L070 clip frames | ours posed by
                                                        #   corner_anim.py at the same times (the hit animation, in place)
    $PY art/ui/recipes/corner_proofs.py wedge           # art/ui/sheets/corner/wedge_<level>.png: `cornerWedge` drawn the way
                                                        #   CornerLayer.swift draws it today (rotated per turn) vs the capture
    $PY art/ui/recipes/corner_proofs.py stats           # in-place mean / p90 CIEDE2000 + silhouette IoU per facing

Captures are LOOKED AT only (the sheets live in art/ui/sheets, gitignored); nothing here writes an asset.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(APP, "art", "ui", "out")
SHEETS = os.path.join(APP, "art", "ui", "sheets", "corner")
PXPT = 1178 / 393.0
LEVELS = ["L070", "L071", "L076", "L079", "L080", "L082"]
TURN = {(1, -1): "DownRight", (-1, -1): "DownLeft", (1, 1): "UpRight", (-1, 1): "UpLeft"}


def layers(turn, plate_off=0.0, spring_k=1.0):
    """Our two layers for a turn, composited (spring under plate); plate_off = plate offset along s in pitch units,
    spring_k = the spring's stretch along its axis about its far-end pivot (the hit animation)."""
    sp = Image.open(os.path.join(OUT, f"corner{turn}Spring@3x.png")).convert("RGBA")
    pl = Image.open(os.path.join(OUT, f"corner{turn}Plate@3x.png")).convert("RGBA")
    s = {v: k for k, v in TURN.items()}[turn]
    ppx = 96.0  # px per pitch in the layer
    W = sp.width
    if spring_k != 1.0:
        # pivot: the spring's foot end on the axis (corner_anim.PIVOT = -0.98 p along s from the cell centre)
        sys.path.insert(0, HERE)
        import corner_anim as A
        n = np.array(s, float) / np.sqrt(2)
        piv = np.array([W / 2, W / 2]) + n * A.PIVOT * ppx
        # affine: scale by k along n about piv (PIL wants the inverse map)
        A = np.eye(2) + (1.0 / spring_k - 1.0) * np.outer(n, n)
        off = piv - A @ piv
        sp = sp.transform(sp.size, Image.AFFINE, (A[0, 0], A[0, 1], off[0], A[1, 0], A[1, 1], off[1]), resample=Image.BICUBIC)
    if plate_off:
        n = np.array(s, float) / np.sqrt(2)
        dx, dy = n * plate_off * ppx
        pl = pl.transform(pl.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.BICUBIC)
    out = Image.new("RGBA", sp.size, (0, 0, 0, 0))
    out.alpha_composite(sp)
    out.alpha_composite(pl)
    return out


def corners():
    for L in LEVELS:
        d = json.load(open(os.path.join(APP, "research", "levels", f"{L}.json")))
        p = d["pitch_pt"]; ox, oy = d["origin_pt"]
        for o in d["obstacles"]:
            if o["kind"] != "corner":
                continue
            c, r = o["cells"][0]
            yield dict(L=L, shot=d["shot"], p=p, cx=ox + c * p, cy=oy + r * p, s=tuple(o["facing"]), cell=(c, r))


def place(shot_im, cor, sprite):
    """Paste the sprite (64 pt frame at 32 pt / pitch, anchor = frame centre) at the corner's cell centre, at the level's pitch."""
    side = 2 * cor["p"] * PXPT
    sp = sprite.resize((int(round(side)), int(round(side))), Image.LANCZOS)
    x = cor["cx"] * PXPT - sp.width / 2; y = cor["cy"] * PXPT - sp.height / 2
    im = shot_im.copy()
    im.alpha_composite(sp, (int(round(x)), int(round(y))))
    return im, (x, y, sp.width)


def crop_around(im, cor, k=1.25):
    h = k * cor["p"] * PXPT
    x, y = cor["cx"] * PXPT, cor["cy"] * PXPT
    return im.crop((int(x - h), int(y - h), int(x + h), int(y + h)))


def _label(im, t):
    d = ImageDraw.Draw(im); d.rectangle((0, 0, 8 * len(t) + 4, 12), fill=(255, 255, 255)); d.text((2, 0), t, fill=(200, 0, 0))
    return im


def facings():
    os.makedirs(SHEETS, exist_ok=True)
    seen = {}
    for cor in corners():
        if cor["L"] in ("L076",) and cor["s"] not in seen:
            seen[cor["s"]] = cor
    rows = []
    for s, cor in seen.items():
        shot = Image.open(os.path.join(APP, cor["shot"])).convert("RGBA")
        ours = layers(TURN[s])
        placed, _ = place(shot, cor, ours)
        white = Image.new("RGBA", shot.size, (255, 255, 255, 255))
        alone, _ = place(white, cor, ours)
        a = crop_around(shot, cor); b = crop_around(alone, cor); c = crop_around(placed, cor)
        diff = Image.fromarray(np.clip(np.abs(np.asarray(a).astype(int) - np.asarray(b).astype(int))[..., :3] * 2, 0, 255).astype(np.uint8)).convert("RGBA")
        tiles = [a, b, c, diff]
        S = 4
        tiles = [t.resize((t.width * S, t.height * S), Image.NEAREST) for t in tiles]
        row = Image.new("RGBA", (sum(t.width for t in tiles) + 30, tiles[0].height), (255, 255, 255, 255))
        x = 0
        for t, nm in zip(tiles, ["capture", "ours", "ours in place", "|diff| x2"]):
            row.paste(t, (x, 0)); _label(row.crop((x, 0, x + t.width, 14)), ""); ImageDraw.Draw(row).text((x + 3, 2), f"{cor['L']} {s} {TURN[s]}: {nm}", fill=(200, 0, 0)); x += t.width + 10
        rows.append(row)
    H = sum(r.height for r in rows) + 10 * len(rows)
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, H), "white")
    y = 0
    for r in rows:
        sheet.paste(r.convert("RGB"), (0, y)); y += r.height + 10
    out = os.path.join(SHEETS, "facings.png"); sheet.save(out); print(out)


def board():
    """Game size (1 px = 1 capture px): each level's corners, capture | ours in place, plus 2x crops."""
    os.makedirs(SHEETS, exist_ok=True)
    allrows = []
    for L in LEVELS:
        cs = [c for c in corners() if c["L"] == L]
        if not cs:
            continue
        shot = Image.open(os.path.join(APP, cs[0]["shot"])).convert("RGBA")
        placed = shot.copy()
        for cor in cs:
            placed, _ = place(placed, cor, layers(TURN[cor["s"]]))
        # the region holding the corners
        xs = [c["cx"] * PXPT for c in cs]; ys = [c["cy"] * PXPT for c in cs]; p = cs[0]["p"] * PXPT
        box = (int(max(0, min(xs) - 2.5 * p)), int(max(0, min(ys) - 2.5 * p)), int(min(1178, max(xs) + 2.5 * p)), int(min(2556, max(ys) + 2.5 * p)))
        a = shot.crop(box).convert("RGB"); b = placed.crop(box).convert("RGB")
        row = Image.new("RGB", (a.width * 2 + 20, a.height + 16), "white")
        row.paste(a, (0, 16)); row.paste(b, (a.width + 20, 16))
        ImageDraw.Draw(row).text((2, 2), f"{L} capture (1:1 capture px)", fill=(200, 0, 0))
        ImageDraw.Draw(row).text((a.width + 22, 2), f"{L} ours pasted in place at the lattice anchor", fill=(200, 0, 0))
        row.save(os.path.join(SHEETS, f"board_{L}.png"))
        allrows.append(row)
        # per-corner 2x strip
        strip = []
        for cor in cs:
            a2 = crop_around(shot, cor, 1.1); b2 = crop_around(placed, cor, 1.1)
            t = Image.new("RGB", (a2.width * 2 * 2 + 6, a2.height * 2), "white")
            t.paste(a2.convert("RGB").resize((a2.width * 2, a2.height * 2), Image.LANCZOS), (0, 0))
            t.paste(b2.convert("RGB").resize((a2.width * 2, a2.height * 2), Image.LANCZOS), (a2.width * 2 + 6, 0))
            strip.append(t)
        if strip:
            Wd = sum(t.width for t in strip) + 12 * len(strip); Hd = max(t.height for t in strip)
            st = Image.new("RGB", (Wd, Hd), "white"); x = 0
            for t in strip:
                st.paste(t, (x, 0)); x += t.width + 12
            st.save(os.path.join(SHEETS, f"board_{L}_2x.png"))
    print(SHEETS)


def _lab(rgb):
    from skimage.color import rgb2lab
    return rgb2lab(rgb / 255.0)


def stats(shift=3):
    """Per corner: silhouette IoU and CIEDE2000 inside the object, at the lattice anchor AND at the best integer shift
    within +-`shift` capture px (the capture's lattice fit carries ~0.02 p of error per level). The best shift is also
    reported in the corner's own frame (along the plate u, along the facing n; pitch units): its mean over all corners is
    our anchor's bias."""
    from skimage.color import deltaE_ciede2000
    offs = []
    for cor in corners():
        shot = Image.open(os.path.join(APP, cor["shot"])).convert("RGBA")
        white = Image.new("RGBA", shot.size, (255, 255, 255, 255))
        alone, _ = place(white, cor, layers(TURN[cor["s"]]))
        A = np.asarray(crop_around(shot, cor, 1.3).convert("RGB")).astype(float)
        Bf = np.asarray(crop_around(alone, cor, 1.3).convert("RGB")).astype(float)
        la = _lab(A); lb_full = _lab(Bf)
        best = None
        n = A.shape[0]; M = shift + 1
        for dy in range(-shift, shift + 1):
            for dx in range(-shift, shift + 1):
                a = A[M:n - M, M:n - M]; b = Bf[M - dy:n - M - dy, M - dx:n - M - dx]
                ma = (a.max(axis=2) - a.min(axis=2) > 30); mb = (b.max(axis=2) - b.min(axis=2) > 30)
                m = ma | mb
                de = deltaE_ciede2000(la[M:n - M, M:n - M], lb_full[M - dy:n - M - dy, M - dx:n - M - dx])[m]
                r = (de.mean(), (ma & mb).sum() / max(1, m.sum()), np.percentile(de, 90), dx, dy)
                if dx == 0 and dy == 0:
                    r0 = r
                if best is None or r[0] < best[0]:
                    best = r
        sx, sy = cor["s"]; nn = np.array([sx, sy]) / np.sqrt(2); uu = np.array([-sy, sx]) / np.sqrt(2)
        d = np.array([best[3], best[4]]) / (cor["p"] * PXPT)
        offs.append((d @ uu, d @ nn))
        print(f"{cor['L']} {str(cor['cell']):9s} {TURN[cor['s']]:9s} anchor: IoU {r0[1]:.3f} dE {r0[0]:5.2f} p90 {r0[2]:5.2f} | "
              f"best shift ({best[3]:+d},{best[4]:+d}) px: IoU {best[1]:.3f} dE {best[0]:5.2f} p90 {best[2]:5.2f} | "
              f"shift u {d @ uu:+.3f} n {d @ nn:+.3f} p")
    o = np.array(offs)
    print("mean best shift in the corner frame: u %+.3f  n %+.3f p (sd %.3f %.3f)" % (o[:, 0].mean(), o[:, 1].mean(), o[:, 0].std(), o[:, 1].std()))


def card():
    os.makedirs(SHEETS, exist_ok=True)
    shot = Image.open(os.path.join(APP, "research", "shots", "456-L070-start.png")).convert("RGBA")
    icon = Image.open(os.path.join(OUT, "unlockIconCorner@3x.png")).convert("RGBA")
    # frame top-left (pt) = ink centre (196.55, 413.25) - 50
    x, y = (196.55 - 50) * PXPT, (413.25 - 50) * PXPT
    ic = icon.resize((int(round(100 * PXPT)), int(round(100 * PXPT))), Image.LANCZOS)
    placed = shot.copy(); placed.alpha_composite(ic, (int(round(x)), int(round(y))))
    dark = Image.new("RGBA", shot.size, (28, 28, 28, 255)); dark.alpha_composite(ic, (int(round(x)), int(round(y))))
    box = (int(x - 40), int(y - 40), int(x + 100 * PXPT + 40), int(y + 100 * PXPT + 40))
    tiles = [shot.crop(box), dark.crop(box), placed.crop(box)]
    W = sum(t.width for t in tiles) + 20
    sh = Image.new("RGB", (W, tiles[0].height + 16), "white"); xx = 0
    for t, nm in zip(tiles, ["capture 456", "ours on the scrim colour", "ours in place"]):
        sh.paste(t.convert("RGB"), (xx, 16)); ImageDraw.Draw(sh).text((xx + 2, 2), nm, fill=(200, 0, 0)); xx += t.width + 10
    sh.save(os.path.join(SHEETS, "card_456.png"))
    # context: the whole card screen, ours pasted, at game size (1/1 capture px) - top half
    placed.crop((0, 300, 1178, 1500)).convert("RGB").save(os.path.join(SHEETS, "card_456_context.png"))
    print(SHEETS)


def bounce():
    """The hit animation as specced (art/lanes/corner.md): frames of plate offset + spring stretch at 60 fps."""
    os.makedirs(SHEETS, exist_ok=True)
    sys.path.insert(0, HERE)
    import corner_anim as A
    frames = []
    for t in np.arange(0, A.total_after_release() + A.HOLD_EXAMPLE + 0.02, 1 / 60):
        x = A.offset(t, hold=A.HOLD_EXAMPLE)
        im = layers("DownRight", plate_off=x, spring_k=A.spring_scale(x))
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
        bg = _label(bg.convert("RGB"), f"{t:.3f} {x:+.3f}")
        frames.append(bg)
    cols = 10
    W = frames[0].width; Hh = frames[0].height
    sheet = Image.new("RGB", (cols * W, ((len(frames) + cols - 1) // cols) * Hh), "white")
    for i, f in enumerate(frames):
        sheet.paste(f, ((i % cols) * W, (i // cols) * Hh))
    sheet.save(os.path.join(SHEETS, "bounce.png")); print(os.path.join(SHEETS, "bounce.png"))


def clip():
    """The hit animation in place: frames of S2-L070-corner-first-use (L70 corner (8, 14), 60 Hz, full-res crops) next to our
    two layers posed by corner_anim.offset / spring_scale at the same time after the beat (the head at the corner cell
    centre, 1.2795 s in the clip), pasted on the clip's own rest frame (so only the corner differs)."""
    os.makedirs(SHEETS, exist_ok=True)
    sys.path.insert(0, HERE)
    sys.path.insert(0, os.path.join(APP, "research", "motion-tools"))
    import corner_anim as A
    import mf
    cor = [c for c in corners() if c["L"] == "L070" and c["cell"] == (8, 14)][0]
    Hh = 40.0
    t, px = mf.raw("S2-L070-corner-first-use.mov", 1.10, 1.70, width=240, fps=240,
                   crop=(cor["cx"] - Hh, cor["cy"] - Hh, 2 * Hh, 2 * Hh))
    beat = 1.2795
    rest = Image.fromarray(px[np.argmin(np.abs(t - 1.65))]).convert("RGBA")
    side = int(round(2 * cor["p"] * 3))
    tiles = []
    for tt in (1.20, 1.281, 1.315, 1.348, 1.381, 1.414, 1.448, 1.481, 1.531, 1.60):
        i = int(np.argmin(np.abs(t - tt)))
        x = A.offset(t[i] - beat)
        ours = layers("DownRight", plate_off=x, spring_k=A.spring_scale(x)).resize((side, side), Image.LANCZOS)
        # erase the capture's corner from the rest frame (white disc over the corner's box), then paste ours
        base = rest.copy()
        ImageDraw.Draw(base).rectangle((120 - side * 0.45, 120 - side * 0.45, 120 + side * 0.45, 120 + side * 0.45), fill=(255, 255, 255, 255))
        base.alpha_composite(ours, (int(round(120 - side / 2)), int(round(120 - side / 2))))
        cap = Image.fromarray(px[i]).convert("RGB")
        pair = Image.new("RGB", (160 * 2 + 6, 160 + 14), "white")
        pair.paste(cap.crop((40, 40, 200, 200)), (0, 14)); pair.paste(base.convert("RGB").crop((40, 40, 200, 200)), (166, 14))
        ImageDraw.Draw(pair).text((2, 1), f"t-beat {t[i] - beat:+.3f}  model {x:+.3f} p", fill=(200, 0, 0))
        tiles.append(pair.resize((pair.width * 2, pair.height * 2), Image.LANCZOS))
    cols = 2
    W, Ht = tiles[0].size
    sheet = Image.new("RGB", (cols * (W + 12), ((len(tiles) + cols - 1) // cols) * (Ht + 12)), "white")
    for k, tile in enumerate(tiles):
        sheet.paste(tile, ((k % cols) * (W + 12), (k // cols) * (Ht + 12)))
    out = os.path.join(SHEETS, "clip.png"); sheet.save(out); print(out)


def wedge():
    """`cornerWedge` (the one sprite the code loads today) drawn as CornerLayer.swift draws it once its frame is the
    sprite's 2 x 2 pitch (code request 1 in corner.md): rotated by the turn (upRight 0, upLeft +90 cw, downLeft 180,
    downRight -90), pasted over each captured corner of L70/L71/L76 next to the capture and to the per-turn layers."""
    os.makedirs(SHEETS, exist_ok=True)
    wd = Image.open(os.path.join(OUT, "cornerWedge@3x.png")).convert("RGBA")
    rot = {"UpRight": 0, "UpLeft": 90, "DownLeft": 180, "DownRight": -90}   # CALayer angle, + = clockwise on screen
    for L in ("L070", "L071", "L076"):
        cs = [c for c in corners() if c["L"] == L]
        shot = Image.open(os.path.join(APP, cs[0]["shot"])).convert("RGBA")
        rows = []
        for cor in cs:
            turn = TURN[cor["s"]]
            w = wd.rotate(-rot[turn], resample=Image.BICUBIC)       # PIL rotates counter-clockwise
            pw, _ = place(shot, cor, w)
            pl, _ = place(shot, cor, layers(turn))
            tiles = [crop_around(x, cor, 1.1).convert("RGB") for x in (shot, pw, pl)]
            tiles = [x.resize((x.width * 3, x.height * 3), Image.LANCZOS) for x in tiles]
            row = Image.new("RGB", (sum(x.width for x in tiles) + 20, tiles[0].height + 14), "white")
            xx = 0
            for x, nm in zip(tiles, ["capture", "cornerWedge rotated (code today)", "per-turn layers (1:1)"]):
                row.paste(x, (xx, 14)); ImageDraw.Draw(row).text((xx + 2, 1), f"{L} {cor['cell']} {turn}: {nm}", fill=(200, 0, 0))
                xx += x.width + 10
            rows.append(row)
        Hs = sum(r.height for r in rows); Ws = max(r.width for r in rows)
        sheet = Image.new("RGB", (Ws, Hs), "white"); y = 0
        for r in rows:
            sheet.paste(r, (0, y)); y += r.height
        sheet.save(os.path.join(SHEETS, f"wedge_{L}.png"))
    print(SHEETS)


if __name__ == "__main__":
    what = sys.argv[1:] or ["facings"]
    for w in what:
        dict(facings=facings, board=board, stats=stats, card=card, bounce=bounce, clip=clip, wedge=wedge)[w]()
