#!/usr/bin/env python3
"""Art-director review tools (only uses preview.py's public helpers; changes no shared file).

    PY=~/.venvs/mf3d/bin/python
    MF_WORKERS=2 $PY art/pipeline/review.py --stale            # re-render <id>_sheet rows older than their usdz
    $PY art/pipeline/review.py --level 4 --contact              # previews/review/L04_contact.png (every row of the level)
    $PY art/pipeline/review.py --level 4 --board                # previews/review/L04_board_vs_ref.png
    $PY art/pipeline/review.py --level 4 --board --seed 3       # another pile
    $PY art/pipeline/review.py --level 14 --contact --board --cast capture   # L14-L19: the CAPTURED cast, not levels.json

The board mock piles the level's items (counts from design/levels.json) on the floor rig at game scale
(200 px/unit, the capture's scale) with a crude "drop onto a heightfield" packer: each item takes a random
stable pose (by probability) and yaw, and is dropped where the pile is lowest among a few candidates.
It is a look/size/recognisability check, not physics. Left: the level's start capture, right: ours.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import preview as P  # noqa: E402

REVIEW = os.path.join(P.PREV, "review")
LEVELS = os.path.join(P.APP, "design", "levels.json")

# the level's board capture (undimmed, as full as possible) and the board crop in capture px
LEVEL_SHOTS = {
    1: "007-L01-after-continue", 2: "019-L02-board-start", 3: "046-L03-vacuum-a", 4: "062-L04-board-start",
    5: "072-L05-start", 6: "093-L06-board-start", 7: "112-L07-tray-scissors-table-table", 8: "119-L08-board-start",
    9: "131-L09-tray-5-mac-mac-muffin-coffee-coffee", 10: "141-L10-board-start", 11: "154-L11-near-fail-6-of-7-pink-slot", 12: "160-L12-board-start",
    13: "174-L13-board-start",
    14: "203-L14-board-start", 15: "217-L15-board-start", 16: "237-L16-board-start", 17: "270-L17-firework-item-a",
    18: "283-L18-sandglass-a", 19: "312-L19-att4-board-red-paddles",
}
# Round 2: design/levels.json still re-casts L14-L19 with round-1 stand-ins. `--cast capture` piles what the captures
# show instead (research/levels.md + items.md session 2 + the lane logs; filler counts are read off the boards, rounded
# to multiples of 3). Goals are exact (goal cards); specials and keys as recorded.
CAPTURE_CASTS = {
    14: {"corn_can": 6, "tomato_can": 6, "broccoli_can": 12, "tomato": 12, "sandwich_sub": 12, "corn_cob": 12,
         "watermelon_slice": 12},
    15: {"fashion_doll_yellow": 18, "fashion_doll_blue": 18, "gift_pink_hearts": 15, "notebook_pink_dots": 6,
         "roller_skate": 6, "swirl_lollipop": 6, "ice_lolly_pink": 9, "milkshake_pink": 9, "special_key": 2},
    16: {"backpack_blue": 12, "skateboard": 12, "rope_ring_green": 15, "stacking_rings": 12, "play_dough_tub": 9,
         "ruler_orange": 9, "special_key": 5},
    17: {"hot_air_balloon_red_hearts": 15, "hot_air_balloon_yellow_stars": 15, "hot_air_balloon_green_clovers": 15,
         "hot_air_balloon_blue_dots": 15, "balloon_purple_dots": 12, "balloon_smiley": 9, "special_firework": 3,
         "special_key": 2},
    18: {"apple_red": 9, "chili_red": 6, "watermelon_slice": 9, "strawberry": 6, "cherries": 9, "grapes_green": 15,
         "apple_green": 9, "kiwi": 9, "chili_green": 9, "special_sandglass": 4, "special_key": 4},
    19: {"tennis_racket_red": 9, "table_tennis_paddle": 9, "cricket_bat": 9, "baseball_bat": 9, "pool_cue": 9,
         "tennis_ball": 12, "baseball": 12, "cricket_ball": 12, "pool_ball_8": 9, "pool_ball_green_stripe_14": 9,
         "small_white_ball_match": 9, "special_firework": 2, "special_sandglass": 1, "special_key": 3},
}
CAST = "levels"   # or "capture" (main: --cast)
CROP = (0, 590, 1178, 1960)  # board area between the goal cards and the tray
ALIASES = {"blue_case": "blue_radio", "boombox": "blue_radio"}  # requests-music-sports.md R1


def level_counts(level):
    if CAST == "capture" and level in CAPTURE_CASTS:
        return dict(CAPTURE_CASTS[level]), 1.0
    d = json.load(open(LEVELS))
    lv = next(l for l in d["levels"] if l["id"] == level)
    counts = {}
    for g in lv["goals"] + lv["fillers"]:
        k = ALIASES.get(g["item"], g["item"])
        counts[k] = counts.get(k, 0) + int(g["count"])
    return counts, lv.get("itemScale", 1.0)


def catalog():
    return json.load(open(os.path.join(P.OUT, "catalog.json")))


def level_ids(level):
    c = catalog()
    ids = [] if CAST == "capture" and level in CAPTURE_CASTS else list(c["by_level"].get(str(level), []))
    try:
        counts, _ = level_counts(level)
        ids += [k for k in counts if k not in ids and k in c["items"]]
    except StopIteration:
        pass
    return ids


# ------------------------------------------------------------------ stale rows

def stale_ids():
    out = []
    for i in sorted(catalog()["items"]):
        u = os.path.join(P.OUT, f"{i}.usdz")
        s = os.path.join(P.PREV, f"{i}_sheet.png")
        if not os.path.exists(s) or os.path.getmtime(s) < os.path.getmtime(u):
            out.append(i)
    return out


# ------------------------------------------------------------------ contact sheet per level

def level_contact(level, max_w=None):
    ids = level_ids(level)
    rows = [Image.open(os.path.join(P.PREV, f"{i}_sheet.png")).convert("RGB") for i in ids
            if os.path.exists(os.path.join(P.PREV, f"{i}_sheet.png"))]
    W = max(r.width for r in rows)
    head = 40
    sh = Image.new("RGB", (W, head + sum(r.height + 6 for r in rows)), (12, 13, 15))
    ImageDraw.Draw(sh).text((8, 8), f"Level {level}: {len(rows)} items   (refs and ours at 200 px/unit, tray at 3 px/pt)",
                            fill=(255, 255, 255), font=P._font(22))
    y = head
    for r in rows:
        sh.paste(r, (0, y)); y += r.height + 6
    os.makedirs(REVIEW, exist_ok=True)
    tag = "_capture_cast" if CAST == "capture" and level in CAPTURE_CASTS else ""
    p = os.path.join(REVIEW, f"L{level:02d}_contact{tag}.png")
    sh.save(p)
    print("contact:", p, sh.size)
    return p


# ------------------------------------------------------------------ board mock per level

def _random_rot(rng):
    """Uniform random rotation (Shoemake quaternion)."""
    u1, u2, u3 = rng.random(), rng.random(), rng.random()
    a, b = math.sqrt(1 - u1), math.sqrt(u1)
    x, y, z, w = a * math.sin(2 * math.pi * u2), a * math.cos(2 * math.pi * u2), b * math.sin(2 * math.pi * u3), b * math.cos(2 * math.pi * u3)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _posed(meta, pose_i, yaw, R0=None):
    """Rotation of stable pose pose_i (or R0) then yaw; returns (R 3x3, hull points posed)."""
    M = np.array(meta["stable_poses"][pose_i]["matrix"]) if meta.get("stable_poses") else np.eye(4)
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    Ry = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    R = Ry @ (M[:3, :3] if R0 is None else R0)
    pts = np.vstack([np.array(h["points"]) for h in meta["collision_hulls"]]) @ R.T
    return R, pts


def board_mock(level, seed=1, scale=None, cell=0.04, density=1.0, jam=0.45):
    counts, lvl_scale = level_counts(level)
    scale = scale or lvl_scale
    rng = random.Random(seed)
    L, T, Rr, B = CROP
    W_px, H_px = Rr - L, B - T
    Wu, Hu = W_px / P.PX_PER_UNIT, H_px / P.PX_PER_UNIT
    margin = 0.25
    nx, nz = int(Wu / cell) + 1, int(Hu / cell) + 1
    hf = np.zeros((nz, nx))
    gx = (np.arange(nx) * cell) - Wu / 2
    gz = (np.arange(nz) * cell) - Hu / 2
    GX, GZ = np.meshgrid(gx, gz)
    inst = []
    for k, n in counts.items():
        mp = os.path.join(P.OUT, f"{k}.json")
        if not os.path.exists(mp):
            print("  (not built:", k, ")")
            continue
        meta = json.load(open(mp))
        inst += [(k, meta)] * max(1, int(round(n * density)))
    rng.shuffle(inst)
    items = []
    for k, meta in inst:
        probs = [p.get("probability") or 0.25 for p in meta.get("stable_poses") or [{}]]
        pi = rng.choices(range(len(probs)), weights=probs)[0]
        yaw = rng.uniform(0, 360)
        # the captures' piles hold many items jammed on a tilt or on their side (burgers, drums, coconuts), not only
        # in the quasi-static stable poses trimesh ranks first: a share of the items takes a random orientation
        R0 = _random_rot(rng) if rng.random() < jam else None
        R, pts = _posed(meta, pi, yaw, R0)
        pts = pts * scale
        lo, hi = pts.min(0), pts.max(0)
        ext = hi - lo
        best = None
        for _ in range(28):
            cx = rng.uniform(-Wu / 2 + margin + ext[0] / 2 * 0.6, Wu / 2 - margin - ext[0] / 2 * 0.6)
            cz = rng.uniform(-Hu / 2 + margin + ext[2] / 2 * 0.6, Hu / 2 - margin - ext[2] / 2 * 0.6)
            # footprint: ellipse of the posed XZ extent
            m = (((GX - cx) / (ext[0] / 2 + 1e-6)) ** 2 + ((GZ - cz) / (ext[2] / 2 + 1e-6)) ** 2) <= 1.0
            if not m.any():
                continue
            base = float(np.percentile(hf[m], 80))
            score = base + rng.uniform(0, 0.05)
            if best is None or score < best[0]:
                best = (score, cx, cz, m, base)
        if best is None:
            continue
        _, cx, cz, m, base = best
        y0 = base * 0.8  # nest a little into the pile
        # heightfield update: dome over the footprint up to the posed height
        d = np.sqrt(((GX - cx) / (ext[0] / 2 + 1e-6)) ** 2 + ((GZ - cz) / (ext[2] / 2 + 1e-6)) ** 2)
        dome = y0 + ext[1] * np.sqrt(np.clip(1 - d ** 2, 0, 1))
        hf = np.where(m, np.maximum(hf, dome), hf)
        Mx = np.eye(4)
        Mx[:3, :3] = R * scale
        Mx[0, 3] = cx - (lo[0] + hi[0]) / 2
        Mx[2, 3] = cz - (lo[2] + hi[2]) / 2
        Mx[1, 3] = y0 - lo[1]
        items.append(dict(usdz=os.path.join(P.OUT, f"{k}.usdz"), matrix=Mx.reshape(-1).tolist()))
    os.makedirs(REVIEW, exist_ok=True)
    o = os.path.join(REVIEW, f"L{level:02d}_board_raw.png")
    s = P.base_scene(o, W_px * P.SS, H_px * P.SS, P.top_camera(Wu, W_px / H_px), shadow_half=max(Wu, Hu) / 2 + 0.3)
    s["items"] = items
    P.run_job([s], f"review_L{level}")
    ours = P.downsample(o).convert("RGB")
    shot = os.path.join(P.RESEARCH, "shots", LEVEL_SHOTS.get(level, "") + ".png")
    sheet = Image.new("RGB", (W_px * 2 + 12, H_px + 40), (12, 13, 15))
    dr = ImageDraw.Draw(sheet)
    if os.path.exists(shot):
        sheet.paste(Image.open(shot).convert("RGB").crop(CROP), (0, 40))
        dr.text((8, 8), f"capture {os.path.basename(shot)}", fill=(255, 255, 255), font=P._font(22))
    sheet.paste(ours, (W_px + 12, 40))
    dr.text((W_px + 20, 8), f"ours: L{level} pile, {len(items)} items, scale {scale}, seed {seed}, jammed {jam:.0%}", fill=(255, 255, 255), font=P._font(22))
    tag = "_capture_cast" if CAST == "capture" and level in CAPTURE_CASTS else ""
    p = os.path.join(REVIEW, f"L{level:02d}_board_vs_ref{tag}.png")
    sheet.save(p)
    os.remove(o)
    print("board:", p, sheet.size, len(items), "items")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, nargs="*", default=[])
    ap.add_argument("--contact", action="store_true")
    ap.add_argument("--board", action="store_true")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--density", type=float, default=1.0)
    ap.add_argument("--jam", type=float, default=0.45, help="share of items in a random (jammed) orientation")
    ap.add_argument("--stale", action="store_true", help="list (and with --render re-render) stale rows")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--max", type=int, default=6, help="max rows to re-render per run (keep runs < 4 min)")
    ap.add_argument("--cast", choices=["levels", "capture"], default="levels",
                    help="item mix: design/levels.json, or the captured cast (CAPTURE_CASTS, L14-L19)")
    a = ap.parse_args()
    global CAST
    CAST = a.cast
    if a.stale:
        ids = stale_ids()
        print("stale:", ids)
        if a.render:
            for i in ids[: a.max]:
                P.item_previews(i)
    for lv in a.level:
        if a.contact:
            level_contact(lv)
        if a.board:
            board_mock(lv, seed=a.seed, density=a.density, jam=a.jam)


if __name__ == "__main__":
    main()
