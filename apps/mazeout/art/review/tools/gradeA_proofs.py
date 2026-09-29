"""Grader A composed proofs (proof images only; nothing here ships). Run from apps/mazeout with the mf3d python.

    PY=~/.venvs/mf3d/bin/python
    $PY art/review/tools/gradeA_proofs.py [hud home loading popups settings events board all]  -> art/ui/sheets/gA_<name>.png

The board BOX proof renders gen_board.curtain_crate(10, 3) once into build/ui-art/draft/gradeA_boxW10H3.png (WebKit,
scratch only; no manifest entry, nothing in art/ is written besides the gA_ sheets).

Every panel is at the capture's scale (3 px per pt) and the sheets are saved at 2 px per pt (a phone-sized view).
"Ours in place": our asset scaled so its INK bbox matches the measured element (ui-measure / lane ref) and centred on it,
after the original element is erased (column-wise interpolation between the rows above and below the box; proof only).
Board sprites use the manifest anchor + pitch scale (fit pitch / 32).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

APP = os.getcwd()
sys.path.insert(0, os.path.join(APP, "art", "ui", "recipes"))
sys.path.insert(0, os.path.join(APP, "art", "ui", "tools"))
OUT = os.path.join(APP, "art", "ui", "out")
AOUT = os.path.join(APP, "art", "out")
SHEETS = os.path.join(APP, "art", "ui", "sheets")
SHOTS = os.path.join(APP, "research", "shots")
K = 3
FONT = os.path.join(APP, "design", "fonts", "PCDisplay-Black.ttf")
LOG = []


def font(pt):
    return ImageFont.truetype(FONT, int(pt * K))


def lab(pt):
    return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", int(pt))


def shot(name):
    p = name if os.path.exists(name) else os.path.join(SHOTS, name)
    im = Image.open(p).convert("RGBA")
    return im.resize((393 * K, 852 * K), Image.LANCZOS) if im.size != (393 * K, 852 * K) else im


def asset(i, d=OUT):
    p = i if os.path.exists(i) else os.path.join(d, f"{i}@3x.png")
    return Image.open(p).convert("RGBA")


def ink(im, thr=128):
    a = np.asarray(im)[:, :, 3]
    ys, xs = np.where(a > thr)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def erase(cv, box, pad=1.5):
    """fill box (pt) by interpolating, per column, between the rows just above and below it (proof only)."""
    x0, y0, x1, y1 = [int(round(v * K)) for v in (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)]
    a = np.asarray(cv).astype(np.float32).copy()
    top, bot = a[max(y0 - 2, 0), x0:x1], a[min(y1 + 1, a.shape[0] - 1), x0:x1]
    t = np.linspace(0, 1, y1 - y0)[:, None, None]
    a[y0:y1, x0:x1] = top[None] * (1 - t) + bot[None] * t
    cv.paste(Image.fromarray(a.astype(np.uint8)))


def put(cv, im, cx, cy, scale=1.0, anchor=None, rot=0.0, tag=None):
    """paste im (3 px/pt) scaled; its anchor (px of the unscaled image; default the ink centre) lands on (cx, cy) pt."""
    if anchor is None:
        b = ink(im)
        anchor = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    w, h = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    s = im.resize((w, h), Image.LANCZOS)
    ax, ay = anchor[0] * scale, anchor[1] * scale
    if rot:
        big = Image.new("RGBA", (w * 2, h * 2))
        big.alpha_composite(s, (w - int(ax), h - int(ay)))
        s = big.rotate(rot, resample=Image.BICUBIC, center=(w, h))
        ax, ay = w, h
    cv.alpha_composite(s, (int(round(cx * K - ax)), int(round(cy * K - ay))))
    if tag:
        LOG.append(f"{tag}: scale {scale:.2f}")


def fit(im, w_pt=None, h_pt=None):
    b = ink(im)
    sw = (w_pt * K) / (b[2] - b[0]) if w_pt else None
    sh = (h_pt * K) / (b[3] - b[1]) if h_pt else None
    return min(v for v in (sw, sh) if v)


def place_box(cv, i, box, by="w", er=True, d=OUT, rot=0.0, scale=None, pad=1.5):
    x0, y0, w, h = box
    im = asset(i, d)
    if er:
        erase(cv, (x0, y0, x0 + w, y0 + h), pad)
    s = scale if scale else (fit(im, w_pt=w) if by == "w" else fit(im, h_pt=h) if by == "h" else fit(im, w, h))
    put(cv, im, x0 + w / 2, y0 + h / 2, s, rot=rot, tag=i)
    return s


def rrect(cv, box, r, fill, outline=None, width=0):
    d = ImageDraw.Draw(cv)
    x0, y0, w, h = box
    d.rounded_rectangle([x0 * K, y0 * K, (x0 + w) * K, (y0 + h) * K], radius=r * K, fill=fill, outline=outline,
                        width=int(width * K))


def text(cv, xy, s, pt, fill, outline=None, ow=1.0, anchor="mm"):
    d = ImageDraw.Draw(cv)
    d.text((xy[0] * K, xy[1] * K), s, font=font(pt), fill=fill, anchor=anchor,
           stroke_width=int(ow * K) if outline else 0, stroke_fill=outline)


def sheet(name, panels, crop=None, title="", scale=2 / 3):
    """panels: [(label, RGBA canvas 1179 x 2556)]; crop in pt (x0, y0, x1, y1)."""
    ims = []
    for label, cv in panels:
        c = cv if crop is None else cv.crop(tuple(int(v * K) for v in crop))
        c = c.convert("RGB")
        c = c.resize((max(1, int(c.width * scale)), max(1, int(c.height * scale))), Image.LANCZOS)
        ims.append((label, c))
    gap, top = 16, 60
    vertical = ims[0][1].width > 1.5 * ims[0][1].height
    if vertical:
        W = max(c.width for _, c in ims) + 2 * gap
        H = sum(c.height + 26 for _, c in ims) + top + gap * len(ims)
    else:
        W = sum(c.width for _, c in ims) + gap * (len(ims) + 1)
        H = max(c.height for _, c in ims) + top + gap
    out = Image.new("RGB", (W, H), (236, 236, 240))
    d = ImageDraw.Draw(out)
    d.text((gap, 6), title, fill=(20, 20, 30), font=lab(20))
    x, y = gap, 34
    for label, c in ims:
        if vertical:
            d.text((x, y), label, fill=(40, 40, 60), font=lab(16))
            out.paste(c, (x, y + 24))
            y += c.height + 26 + gap
        else:
            d.text((x, 34), label, fill=(40, 40, 60), font=lab(16))
            out.paste(c, (x, top))
            x += c.width + gap
    os.makedirs(SHEETS, exist_ok=True)
    p = os.path.join(SHEETS, f"gA_{name}.png")
    out.save(p, optimize=True)
    print(p, out.size, "|", "; ".join(LOG))
    LOG.clear()
    return p


# --------------------------------------------------------------------------------------------- HUD
def hud():
    ref = shot("003-L32-start.png")
    cv = ref.copy()
    place_box(cv, "iconCoin", (19.7, 30.4, 23.7, 24.4))
    place_box(cv, "iconStopwatch", (92.7, 77.7, 29, 33), by="h")
    for x in (201.5, 237.5, 273.6):
        place_box(cv, "heartHUD", (x, 82.1, 28.7, 24.4))
    pb = asset(os.path.join(APP, "build", "ui-art", "swiftui", "pauseButton.png"))
    erase(cv, (334.3, 68.1, 334.3 + 40.4, 68.1 + 40), 2.5)
    put(cv, pb, 334.3 + 20.2, 68.1 + 20, 1.0, anchor=(pb.width / 2, pb.height / 2), tag="pauseButton(swiftui)")
    ref2 = shot("110-L047-after-bump.png")
    cv2 = ref2.copy()
    place_box(cv2, "heartHUDLost", (272.1, 80.6, 31, 27), by="both")
    sheet("hud", [("reference 003 (looked at only)", ref), ("ours in place: coin, stopwatch, 3 hearts, pause (SwiftUI)", cv),
                  ("reference 110 (after a bump)", ref2), ("ours: heartHUDLost in place", cv2)],
          crop=(0, 22, 393, 122), title="HUD row at game size (L32 start / L47 after bump)", scale=1.0)


# --------------------------------------------------------------------------------------------- HOME
def home():
    import scene_proofs as P
    cv = P.home_stack()
    ref = shot("026-home-after-L32.png")
    # --- mocked SwiftUI chrome (flat stand-ins, only so the icons sit on a plausible ground)
    rrect(cv, (18.7, 36.7, 45, 45), 13, (0, 152, 253, 255), (0, 70, 190, 255), 1.2)          # avatar button (approx)
    av = asset("avatarDefault")
    put(cv, av, 18.7 + 22.5, 36.7 + 22.5, 36 / 64)
    rrect(cv, (126.8, 55.7, 73.7, 27.4), 11.3, (222, 238, 255, 255), (80, 125, 200, 255), 1)  # coin pill
    text(cv, (170, 69.5), "2260", 18.8, (9, 56, 150, 255))
    rrect(cv, (242.2, 56, 76.7, 27.4), 11.5, (222, 238, 255, 255), (80, 125, 200, 255), 1)    # lives pill
    text(cv, (285, 70), "Full", 19.1, (9, 56, 150, 255))
    rrect(cv, (334.3, 49, 40, 39.7), 12.5, (2, 146, 255, 255), (0, 60, 200, 255), 2)         # gear button
    rrect(cv, (19.3, 107.8, 354.6, 43.7), 12, (1, 156, 251, 255), (0, 63, 206, 255), 1.5)    # claw bar frame
    rrect(cv, (60, 114, 262, 30), 8, (8, 40, 148, 255))                                       # claw track
    text(cv, (190, 129), "0/1", 21.7, (255, 255, 255, 255), (6, 30, 121, 255), 1)
    rrect(cv, (174.5, 149.8, 54.7, 16.3), 4.8, (0, 149, 253, 255), (15, 44, 128, 255), 1)    # claw timer chip
    text(cv, (206, 158), "3d 9h", 13, (255, 255, 255, 255), (15, 44, 128, 255), 0.8)
    rrect(cv, (147.5, 536.8, 98.4, 32.4), 14.8, (5, 208, 1, 255), (6, 106, 1, 255), 1.5)     # level plate
    text(cv, (196.7, 527), "LEVEL", 14.1, (255, 255, 255, 255), (9, 49, 152, 255), 0.8)
    text(cv, (196.7, 553), "33", 30.6, (255, 255, 255, 255), (6, 106, 1, 255), 1.5)
    rrect(cv, (82.7, 622.2, 228.2, 103.8), 40, (0, 167, 251, 255), (0, 80, 200, 255), 2)     # play frame
    bg = asset(os.path.join(APP, "build", "ui-art", "swiftui", "buttonGreen.png"))
    cv.alpha_composite(bg.resize((int(215 * K), int(91 * K)), Image.LANCZOS), (int(89 * K), int(626 * K)))
    text(cv, (196.7, 668), "Play", 48.8, (241, 255, 242, 255), (6, 106, 1, 255), 2)
    nav = Image.new("RGBA", (393 * K, int(81.1 * K)))
    a = np.zeros((nav.height, nav.width, 4), np.uint8)
    for y in range(nav.height):
        t = y / nav.height
        c = np.array([0, 160, 255]) * (1 - t) + np.array([19, 75, 239]) * t
        a[y, :, :3] = c
        a[y, :, 3] = 255
    a[:3, :, :3] = (0, 59, 203)
    cv.alpha_composite(Image.fromarray(a), (0, int(771.7 * K)))
    rrect(cv, (126.8, 753.6, 140.1, 99.1), 16, (13, 207, 255, 255), (0, 92, 218, 255), 1.5)  # raised home tab
    text(cv, (196.9, 830), "Home", 15.1, (255, 255, 255, 255), (22, 56, 140, 255), 1)
    for i, box in (("navShop", (40, 779, 56.7, 56.7)), ("navTrophy", (293.6, 779, 61.7, 60.1)),
                   ("navHome", (159.5, 743.6, 74.4, 71.4))):
        if os.path.exists(os.path.join(OUT, f"{i}@3x.png")):
            place_box(cv, i, box, by="both", er=False)
    if os.path.exists(os.path.join(OUT, "eventBadgeStreak@3x.png")):
        place_box(cv, "eventBadgeStreak", (11.7, 190.8, 75.7, 80.1), by="both", er=False)
    # --- OUR svg icons (graded here) at the ui-measure frames
    place_box(cv, "iconCoin", (95.7, 53, 34, 34), er=False)
    place_box(cv, "iconPlusGreen", (118.8, 73.7, 18.7, 18.7), er=False)
    place_box(cv, "heartLives", (212.5, 53, 39, 33), by="both", er=False)
    text(cv, (236.9, 72.4), "5", 22.8, (255, 255, 255, 255), (135, 4, 0, 255), 0.9)
    place_box(cv, "glyphGear", (341.3, 55.4, 26, 26), by="both", er=False, scale=1.0)
    place_box(cv, "iconHexArrow", (30.7, 110.8, 36.7, 34), by="both", er=False)
    place_box(cv, "heartInfiniteSmall", (323.6, 108.4, 46, 48.4), by="w", er=False)
    text(cv, (346.6, 146), "30m", 15, (255, 255, 255, 255), (130, 0, 0, 255), 1)
    place_box(cv, "iconStopwatchSmall", (162, 146, 18, 26), by="h", er=False, scale=1.0)
    # --- 1:1 in-place on the capture (erase + ours) for the same icons
    ip = ref.copy()
    place_box(ip, "iconCoin", (95.7, 53, 34, 34))
    place_box(ip, "iconPlusGreen", (118.8, 73.7, 18.7, 18.7))
    place_box(ip, "heartLives", (212.5, 53, 39, 33), by="both")
    text(ip, (236.9, 72.4), "5", 22.8, (255, 255, 255, 255), (135, 4, 0, 255), 0.9)
    erase(ip, (343, 57, 366, 80), 0)
    place_box(ip, "glyphGear", (341.3, 55.4, 26, 26), er=False, scale=1.0)
    place_box(ip, "iconHexArrow", (30.7, 110.8, 36.7, 34), by="both", er=False)
    place_box(ip, "heartInfiniteSmall", (323.6, 108.4, 46, 42), by="w", er=False)
    place_box(ip, "iconStopwatchSmall", (162, 146, 18, 26), by="h", er=False, scale=1.0)
    sheet("home", [("ours: scene + rigs + mocked chrome + our icons", cv), ("reference 026 (looked at only)", ref),
                   ("our icons pasted in place on 026 (no erase for hex/claw/watch)", ip)],
          title="Home at game size (026 layout; chrome = flat mocks, icons = ours)", scale=0.5)
    sheet("home_top", [("ours", cv), ("reference 026", ref), ("ours in place on 026", ip)], crop=(0, 30, 393, 200),
          title="Home top bar + Claw bar", scale=1.0)


# --------------------------------------------------------------------------------------------- LOADING
def loading():
    import scene_proofs as P
    cv = P.loading_stack()
    ref = shot(os.path.join(APP, "research", "kickoff", "state.png"))
    lg = asset("logoArrowOut")
    b = ink(lg)
    s = (206.8 * K) / (b[2] - b[0])
    put(cv, lg, 20 + 206.8 / 2, 66.7 + 160.1 / 2, s, rot=4.0, tag="logoArrowOut")
    text(cv, (187.7, 785.6), "Loading", 26.8, (204, 204, 204, 255), (104, 30, 26, 255), 0.9)
    ip = ref.copy()
    erase(ip, (14, 60, 232, 232), 0)
    put(ip, lg, 20 + 206.8 / 2, 66.7 + 160.1 / 2, s, rot=4.0)
    sheet("loading", [("ours: loadingBackdrop + characters + logoArrowOut (206.8 pt wide, +4 deg)", cv),
                      ("reference: kickoff/state.png (looked at only)", ref), ("our logo in place on the capture", ip)],
          title="Loading at game size", scale=0.5)
    sheet("loading_logo", [("ours", cv), ("reference", ref), ("ours in place", ip)], crop=(0, 40, 260, 250),
          title="Loading logo", scale=1.0)


# --------------------------------------------------------------------------------------------- POPUPS
def popups():
    ref = shot("007-L32-pause.png")
    cv = ref.copy()
    place_box(cv, "glyphSound", (73.4, 331.6, 31.4, 28.7), by="both", pad=1)
    place_box(cv, "glyphHaptic", (72.4, 403.3, 33, 31.7), by="both", pad=1)
    cv_1 = ref.copy()
    place_box(cv_1, "glyphSound", (73.4, 331.6, 31.4, 28.7), scale=1.0, pad=1)
    place_box(cv_1, "glyphHaptic", (72.4, 403.3, 33, 31.7), scale=1.0, pad=1)
    for n, box in (("buttonGreen", (60.4, 486.1, 125.1, 89.1)), ("buttonRed", (206.5, 486.1, 125.1, 89.1))):
        im = asset(os.path.join(APP, "build", "ui-art", "swiftui", f"{n}.png"))
        erase(cv, (box[0], box[1], box[0] + box[2], box[1] + box[3]), 2)
        put(cv, im, box[0] + box[2] / 2, box[1] + box[3] / 2 + 0.7, 1.0, anchor=(im.width / 2, im.height / 2))
    text(cv, (123, 530.6), "Resume", 27.2, (253, 249, 232, 255), (6, 106, 1, 255), 1.4)
    text(cv, (269, 530.6), "Quit", 30.5, (253, 248, 230, 255), (101, 0, 0, 255), 1.5)
    sheet("popup_pause", [("reference 007", ref), ("ours: glyphs fitted to the measured ink + buttons (SwiftUI render, PC Display label)", cv),
                          ("ours: glyphs at their shipped 1:1 frame", cv_1)],
          crop=(0, 180, 393, 640), title="Paused popup at game size", scale=1.0)
    # unlock cards
    r1 = shot("040-L35-pipe-unlocked.png")
    c1 = r1.copy()
    erase(c1, (112, 336, 280, 470), 0)
    put(c1, asset("unlockIconPipe"), 117.8 + 78, 340.4 + 62, 1.0, anchor=(156 * 1.5, 124 * 1.5))
    text(c1, (117.8 + 74.6, 340.4 + 28.0), "3", 26, (255, 255, 255, 255), (130, 37, 33, 255), 1.2)
    r2 = shot("134-L050-box-unlock.png")
    c2 = r2.copy()
    erase(c2, (120, 345, 274, 478), 0)
    put(c2, asset("unlockIconCurtain"), 197, 411, 1.0, anchor=(180, 165))
    text(c2, (197, 411), "5", 30, (255, 255, 255, 255), (20, 30, 90, 255), 1.5)
    c3 = r2.copy()
    erase(c3, (120, 345, 274, 478), 0)
    put(c3, asset("unlockIconCurtain"), 197, 411, 1.09, anchor=(180, 165))
    text(c3, (197, 411), "5", 32, (255, 255, 255, 255), (20, 30, 90, 255), 1.5)
    sheet("popup_unlock", [("reference 040 Pipe!", r1), ("ours unlockIconPipe 1:1 (+live '3')", c1),
                           ("reference 134 Box!", r2), ("ours unlockIconCurtain 1:1", c2), ("ours at 1.09", c3)],
          crop=(30, 150, 363, 640), title="Unlock cards at game size", scale=0.75)


def settings():
    ref = shot("meta-029-settings.png")
    cv = ref.copy()
    for i, (cx, cy) in (("glyphSound", (91.7, 343.3)), ("glyphMusic", (191.7, 343.3)), ("glyphHaptic", (300, 343.3))):
        erase(cv, (cx - 23, cy - 20, cx + 23, cy + 20), 0)
        put(cv, asset(i), cx, cy, 1.0)
    erase(cv, (38, 160, 80, 204), 0)
    put(cv, asset("glyphBell"), 58.3, 181.7, 1.0)
    r2 = shot("meta-003-profile-edit.png")
    c2 = r2.copy()
    erase(c2, (289, 235, 324, 270), 0)
    put(c2, asset("iconPencil"), 306, 252.3, 1.0)
    r3 = shot("meta-002-avatar-tap.png")
    c3 = r3.copy()
    for i, (cx, cy), box in (("statFirstTryIcon", (53.3, 366.7), (29, 342, 80, 392)),
                             ("statWeeklyWinsIcon", (240.7, 366.7), (219, 340, 263, 394)),
                             ("iconPencil", (111.7, 231.7), (97, 217, 127, 247))):
        erase(c3, box, 0)
        put(c3, asset(i), cx, cy, 1.0)
    r4 = shot("016-L32-after-decline-life.png")
    c4 = r4.copy()
    put(c4, asset("iconCheckeredFlag"), 98, 719, 1.0)
    sheet("profile", [("reference meta-002 Profile (phone v552)", r3),
                      ("ours 1:1 in place: statFirstTryIcon, statWeeklyWinsIcon, iconPencil", c3)],
          crop=(0, 150, 393, 420), title="Profile stats at game size", scale=1.0)
    sheet("streak_flag", [("reference 016 Streak Race strip", r4), ("ours: iconCheckeredFlag 1:1 over the left flag (no erase)", c4)],
          crop=(60, 680, 330, 760), title="Streak Race logo flag at game size", scale=1.5)
    sheet("settings", [("reference meta-029 Settings (phone v552)", ref), ("ours (Paused-panel style glyphs 1:1 + bell) in place", cv),
                       ("reference meta-003 Edit Profile", r2), ("ours: iconPencil 1:1 in place", c2)],
          crop=(0, 100, 393, 420), title="Settings + Edit Profile at game size", scale=0.9)


# --------------------------------------------------------------------------------------------- EVENTS
def events():
    r = shot("203-streak-race-leaderboard.png")
    c = r.copy()
    erase(c, (16, 495, 57, 534), 0)
    put(c, asset("rankBadgeSilver"), 36.7, 514.7, 1.0)
    text(c, (36.7, 514.7), "2", 20, (255, 255, 255, 255), (38, 58, 112, 255), 1.2)
    erase(c, (16, 568, 57, 607), 0)
    put(c, asset("rankBadgeBronze"), 36.7, 587.3, 1.0)
    text(c, (36.7, 587.3), "3", 20, (255, 255, 255, 255), (110, 20, 10, 255), 1.2)
    for cy, s in ((515.7, "3423"), (588.3, "2950"), (660.8, "2065")):
        erase(c, (303, cy - 22, 386, cy + 22), 0)
        put(c, asset("scoreChip"), 345, cy, 1.0)
        text(c, (345 + 12, cy + 0.5), s, 15, (255, 255, 255, 255), (60, 30, 10, 255), 1)
    r2 = shot("069-skyjump-screen.png")
    c2 = r2.copy()
    put(c2, asset("prizeSign"), 124, 397, 1.0)
    r3 = shot("023-claw-challenge-c.png")
    c3 = r3.copy()
    erase(c3, (182, 460, 308, 538), 0)
    put(c3, asset("sunburstRays"), 245, 499, 1.0, anchor=(180, 120))
    r4 = shot("025-claw-info.png")
    c4 = r4.copy()
    erase(c4, (60, 128, 178, 246), 0)
    put(c4, asset("infoPathIcon"), 119, 187, 1.0, anchor=(177, 177))
    erase(c4, (226, 218, 272, 268), 0)
    put(c4, asset("pointerArrowYellow"), 249, 243, 1.0, anchor=(69, 75))
    # rays on the reward card: card field flattened to the cream fill, our rays, the 3d-events coin bowl on top
    c5 = r3.copy()
    ImageDraw.Draw(c5).rectangle([186 * K, 462 * K, 305 * K, 537 * K], fill=(248, 231, 210, 255))
    put(c5, asset("sunburstRays"), 245, 499, 1.0, anchor=(180, 120))
    if os.path.exists(os.path.join(OUT, "coinBowl@3x.png")):
        put(c5, asset("coinBowl"), 245, 499, 0.95)
        text(c5, (245, 512), "10000", 15, (255, 255, 255, 255), (120, 0, 20, 255), 1)
    sheet("claw_rays", [("reference 023 reward card", r3), ("ours: sunburstRays on the cream field (+ coinBowl)", c5)],
          crop=(150, 440, 340, 560), title="Claw reward card rays", scale=1.0)
    sheet("streak", [("reference 203 Streak Race", r), ("ours: rank badges 2/3 + scoreChip x3 in place (live text stand-in)", c)],
          crop=(0, 440, 393, 700), title="Streak Race rows at game size", scale=1.0)
    sheet("skyjump", [("reference 069 Sky Jump", r2), ("ours: prizeSign 1:1 at the lane's ref box (no erase)", c2)],
          crop=(0, 250, 393, 560), title="Sky Jump prize sign at game size", scale=1.0)
    sheet("claw", [("reference 023 Claw", r3), ("ours: sunburstRays (erase + 1:1; coin bowl erased too)", c3),
                   ("reference 025 Claw info", r4), ("ours: infoPathIcon + pointerArrowYellow 1:1", c4)],
          crop=(0, 100, 393, 560), title="Claw screens at game size", scale=0.75)


# --------------------------------------------------------------------------------------------- BOARD
def board():
    M = {e["id"]: e for e in json.load(open(os.path.join(APP, "art", "MANIFEST.json")))["entries"]}

    def sprite(cv, i, ax, ay, pitch):
        e = M[i]
        im = asset(i)
        s = pitch / e.get("pitch_pt", 32)
        anc = e.get("anchor_pt") or (im.width / 6, im.height / 6)
        put(cv, im, ax, ay, s, anchor=(anc[0] * 3, anc[1] * 3))

    r = shot("027-L33-start.png")
    c = r.copy()
    p = 17.857
    for h in (4, 8, 12, 16, 20):
        i = f"doorW4H{h}"
        ax, ay = M[i]["ref"]["anchor_pt"]
        sprite(c, i, ax, ay, p)
        put(c, asset("lockHex"), ax + 2 * p, ay + h * p / 2 + 0.18 * p, p / 32,
            anchor=tuple(v * 3 for v in M["lockHex"]["anchor_pt"]))
    sprite(c, "keyOnArrow", *M["keyOnArrow"]["ref"]["anchor_pt"], p)
    r2 = shot("042-L035-start.png")
    c2 = r2.copy()
    sprite(c2, "pipeMouth", *M["pipeMouth"]["ref"]["anchor_pt"], 28.092)
    sprite(c2, "pipeCounter", *M["pipeCounter"]["ref"]["anchor_pt"], 28.092)
    text(c2, M["pipeCounter"]["ref"]["anchor_pt"], "2", 22, (255, 255, 255, 255), (130, 37, 33, 255), 1.0)
    r3 = shot("003-L32-start.png")
    c3 = r3.copy()
    L = json.load(open(os.path.join(APP, "research", "levels", "L032.json")))
    ox, oy = L["origin_pt"]
    p3 = L["pitch_pt"]
    for o in L["obstacles"]:
        xs = [q[0] for q in o["cells"]]
        ys = [q[1] for q in o["cells"]]
        n = max(len(set(xs)), len(set(ys)))
        i = f"tape{'V' if len(set(xs)) == 1 else 'H'}{n}"
        sprite(c3, i, ox + (min(xs) + max(xs)) / 2 * p3, oy + (min(ys) + max(ys)) / 2 * p3, p3)
    bxp = os.path.join(APP, "build", "ui-art", "draft", "gradeA_boxW10H3.png")
    if not os.path.exists(bxp):
        import subprocess
        sys.path.insert(0, os.path.join(APP, "art", "ui", "src"))
        import gen_board as G
        r = G.curtain_crate(G.P0, 10, 3)
        os.makedirs(os.path.join(APP, "build", "ui-art", "svgsrc"), exist_ok=True)
        open(os.path.join(APP, "build", "ui-art", "svgsrc", "gradeA_boxW10H3.svg"), "w").write(r[0] if isinstance(r, tuple) else r)
        subprocess.run([sys.executable, os.path.join(APP, "art", "ui", "tools", "svg.py"), "--draft", "gradeA_boxW10H3"], check=True)
    r4 = shot("135-L050-start.png")
    c4 = r4.copy()
    L5 = json.load(open(os.path.join(APP, "research", "levels", "L050.json")))
    ox5, oy5 = L5["origin_pt"]
    p5 = L5["pitch_pt"]
    bx = asset(os.path.join(APP, "build", "ui-art", "draft", "gradeA_boxW10H3.png"))
    put(c4, bx, ox5 - p5 / 2, oy5 + 14.5 * p5, p5 / 32, anchor=(12, 12))
    text(c4, (ox5 + 4.5 * p5, oy5 + 16 * p5), "10", 24, (255, 255, 255, 255), (40, 20, 90, 255), 1.3)
    sheet("board_L33", [("reference 027 L33", r), ("ours: 5 doors + 5 locks + key 1 in place", c)],
          crop=(0, 240, 393, 640), title="Board L33 (doors, locks, key) at game size", scale=1.0)
    sheet("board_L35_L32", [("reference 042 L35", r2), ("ours: pipeMouth + pipeCounter (tube = original, engine code)", c2),
                            ("reference 003 L32", r3), ("ours: 4 tapes in place", c3)],
          crop=(0, 180, 393, 640), title="Board L35 pipe + L32 tapes at game size", scale=0.75)
    sheet("board_box", [("reference 135 L050 (the phone's BOX, 10 x 3 cells)", r4),
                        ("ours: gen_board.curtain_crate(10, 3) scratch render (no manifest entry) in place", c4)],
          crop=(0, 560, 393, 720), title="Board BOX obstacle at game size", scale=1.0)


# --------------------------------------------------------------------------------------------- APP RENDERS
def app():
    """the shell lane's simulator renders (build/s1, 06:36-07:13) and the device grab (build/device) next to the phone."""
    pairs = {"app_home": ("026-home-after-L32.png", "build/s1/home-L33-normal.png"),
             "app_pause": ("007-L32-pause.png", "build/s1/popup-pause.png"),
             "app_settings": ("meta-029-settings.png", "build/s1/popup-settings.png"),
             "app_board_L32": ("003-L32-start.png", "build/device/grab-L032-fit.png")}
    for name, (ref, ours) in pairs.items():
        if os.path.exists(os.path.join(APP, ours)):
            sheet(name, [("reference " + ref[:-4], shot(ref)), ("app render " + ours, shot(os.path.join(APP, ours)))],
                  title=name.replace("_", " "), scale=0.5)
    h = [(n, os.path.join(APP, p)) for n, p in (("035", "research/shots/035-home-L34.png"),
                                              ("app L34", "build/s1/home-L34-hard.png"),
                                              ("060", "research/shots/060-home-coins-2500-claw-reward.png"),
                                              ("app L39", "build/s1/home-L39-superHard.png"))]
    if all(os.path.exists(p) for _, p in h):
        sheet("app_hard_play", [(n, shot(p)) for n, p in h], crop=(0, 480, 393, 760), title="Hard / Super Hard Play", scale=0.75)


if __name__ == "__main__":
    todo = sys.argv[1:] or ["all"]
    for n in ("hud", "home", "loading", "popups", "settings", "events", "board", "app"):
        if "all" in todo or n in todo:
            globals()[n]()
