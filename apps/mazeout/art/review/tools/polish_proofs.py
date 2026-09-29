"""Polish lane (round 3) proofs: the raised entries next to their references, at GAME size and in place.

    PY=~/.venvs/mf3d/bin/python                      # from apps/mazeout
    $PY art/review/tools/polish_proofs.py [hud unlock events logo popup all]   -> art/ui/sheets/polish/*.png (gitignored)
    sh art/review/tools/polish/build.sh              # first, for `popup`: renders the shell chrome + the polish proposal

Every panel is the capture at 3 px per pt; "ours in place" pastes the shipped @3x file (art/ui/out) at the rect the shell
draws it in (ui.json / UnlockOverlay / SPEC-ui frames), after erasing the original element where noted. Live text is a
PC Display stand-in (the shell draws the real label). Nothing here ships.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gradeA_proofs as A  # noqa: E402  (shot / erase / text / sheet helpers)

APP = A.APP
OUT = os.path.join(APP, "art", "ui", "out")
SHEETS = os.path.join(APP, "art", "ui", "sheets", "polish")
K = 3


def frame(name):
    p = os.path.join(APP, "build", "ui-art", "refframes", name)
    im = Image.open(p).convert("RGBA")
    return im.resize((393 * K, 852 * K), Image.LANCZOS)


def at(cv, i, rect, d=OUT):
    """paste asset i with its FRAME scaled to rect (x, y, w, h pt), as the shell's placed(rect) does."""
    im = Image.open(os.path.join(d, f"{i}@3x.png")).convert("RGBA")
    im = im.resize((round(rect[2] * K), round(rect[3] * K)), Image.LANCZOS)
    cv.alpha_composite(im, (round(rect[0] * K), round(rect[1] * K)))


def save(name, panels, crop, title, scale):
    os.makedirs(SHEETS, exist_ok=True)
    p = A.sheet(name, panels, crop=crop, title=title, scale=scale)
    dst = os.path.join(SHEETS, os.path.basename(p).replace("gA_", "", 1))
    os.replace(p, dst)
    print(dst)


def hud():
    for shot, extra in (("002-home-L32.png", False), ("168-home-L055.png", True)):
        ref = A.shot(shot)
        cv = ref.copy()
        A.erase(cv, (93, 50, 134, 90), 0)
        at(cv, "iconCoin", (93.45, 51.15, 38.5, 38.5))
        at(cv, "iconPlusGreen", (116.6, 71.1, 23.5, 23.5))
        if not extra:
            at(cv, "heartLives", (210.5, 50.9, 42.3, 39.8))
            A.text(cv, (231.8, 70.3), "5", 22.8, (255, 255, 255, 255), (135, 4, 0, 255), 0.9)
        else:
            A.erase(cv, (26, 108, 70, 148), 0)
            at(cv, "iconHexArrow", (29.0, 109.2, 40, 40))
            A.erase(cv, (322, 110, 369, 150), 0)
            at(cv, "heartInfiniteSmall", (323.6, 108.4, 46, 42))
            A.text(cv, (346.2, 141.3), "1h", 13.5, (252, 233, 221, 255), (138, 10, 16, 255), 1.1)
        save(f"hud_{shot[:3]}", [(f"reference {shot[:3]} (looked at only)", ref), ("ours in place at the shell's rects", cv)],
             (0, 30, 393, 200), f"Home top bar + Claw bar at game size ({shot[:3]})", 1.0)
    ref = A.shot("204-final-home-L062.png")
    cv = ref.copy()
    A.erase(cv, (154, 142, 180, 172), 0)
    at(cv, "iconStopwatchSmall", (154.0, 142.6, 26, 28))
    save("hud_watch", [("reference 204", ref), ("ours: iconStopwatchSmall 1:1 (erased + pasted)", cv)], (120, 130, 260, 180),
         "Claw timer chip watch", 2.0)


def unlock():
    r1 = A.shot("134-L050-box-unlock.png")
    c1 = r1.copy()
    A.erase(c1, (128, 340, 266, 486), 0)
    at(c1, "unlockIconBox", (131.25, 347.75, 132, 134))
    A.text(c1, (196.8, 413), "5", 34, (255, 255, 255, 255), (20, 48, 110, 255), 1.9)
    r2 = frame("V1_levels_01_20_mp4/t_00078.0.jpg")
    c2 = r2.copy()
    A.erase(c2, (110, 355, 280, 475), 0)
    at(c2, "unlockIconLinked", (121.0, 360.7, 150, 106))
    r3 = frame("V2_levels_11_38_mp4/t_01182.5.jpg")
    c3 = r3.copy()
    A.erase(c3, (110, 358, 284, 476), 0)
    at(c3, "unlockIconElevator", (114.75, 361.5, 164, 112))
    r4 = frame("V1_levels_01_20_mp4/t_00185.0.jpg")
    c4 = r4.copy()
    A.erase(c4, (115, 330, 280, 495), 0)
    s = 154 / 120.0                                     # V1's card door is 154 pt; ours is drawn at the phone cards' 120
    at(c4, "unlockIconDoor", (196.4 - 64 * s, 412.4 - 64 * s, 128 * s, 128 * s))
    save("unlock", [("134 Box (phone)", r1), ("ours unlockIconBox 1:1", c1), ("V1 78 s Linked", r2), ("ours 1:1", c2),
                       ("V2 1182.5 s Elevator", r3), ("ours 1:1", c3), ("V1 185 s door card", r4), ("ours at V1's size", c4)],
         (100, 320, 295, 500), "Unlock card icons at game size", 1.0)


def events():
    r = A.shot("203-streak-race-leaderboard.png")
    c = r.copy()
    for y, n, ol in ((494.7, "2", (38, 58, 112, 255)), (567.3, "3", (110, 20, 10, 255))):
        A.erase(c, (14, y, 60, y + 41), 0)
        at(c, "rankBadgeSilver" if n == "2" else "rankBadgeBronze", (16.7, y, 40, 40))
        A.text(c, (36.7, y + 19.6), n, 20, (255, 255, 255, 255), ol, 1.2)
    save("streak_badges", [("reference 203", r), ("ours: rank badges 1:1", c)], (0, 470, 200, 620), "Streak Race rank badges", 1.5)
    r3 = A.shot("023-claw-challenge-c.png")
    c3 = r3.copy()
    ImageDraw.Draw(c3).rounded_rectangle([int(149 * K), int(456.5 * K), int(336 * K), int(538.5 * K)], radius=60, fill=(248, 231, 210, 255))
    at(c3, "sunburstRays", (147.5, 455, 190, 86))
    bowl = Image.open(os.path.join(OUT, "coinBowl@3x.png")).convert("RGBA")
    c3.alpha_composite(bowl, (int(242.5 * K - bowl.width / 2), int(485 * K - bowl.height / 2)))
    save("rays", [("reference 023", r3), ("ours: sunburstRays on the field (+ coinBowl)", c3)], (140, 445, 345, 550),
         "Claw reward card rays", 1.5)


def logo():
    ref = A.shot("049-L036-end.png")
    cv = ref.copy()
    lg = Image.open(os.path.join(OUT, "logoArrowOut@3x.png")).convert("RGBA")
    A.erase(cv, (30, 280, 365, 540), 0)
    A.put(cv, lg, 197, 410, 1.0)
    save("logo", [("reference 049 (the original's logo, looked at only)", ref), ("ours: logoArrowOut 1:1", cv)],
         (20, 270, 375, 550), "Logo at game size", 1.0)


def popup():
    shell = os.path.join(APP, "build", "ui-art", "polish", "pause_shell.png")
    pol = os.path.join(APP, "build", "ui-art", "polish", "pause_polish.png")
    if not (os.path.exists(shell) and os.path.exists(pol)):
        print("run art/review/tools/polish/build.sh first")
        return
    ref = A.shot("007-L32-pause.png")
    panels = [("reference 007", ref)]
    for label, p in (("the shell's chrome today (PopupChrome.swift copy)", shell), ("the polish proposal (chrome_polish.swift)", pol)):
        cv = ref.copy()
        cv.alpha_composite(Image.open(p).convert("RGBA"))
        A.text(cv, (197.2, 234.0), "Paused", 49.2, (255, 255, 255, 255), (123, 29, 1, 255), 1.87)
        A.text(cv, (123.0, 530.6), "Resume", 27.2, (253, 249, 232, 255), (6, 106, 1, 255), 1.4)
        A.text(cv, (269.0, 530.6), "Quit", 30.5, (253, 248, 230, 255), (101, 0, 0, 255), 1.5)
        panels.append((label, cv))
    save("popup", panels, (0, 180, 393, 640), "Paused popup chrome at game size (labels = stand-in)", 0.667)


if __name__ == "__main__":
    todo = sys.argv[1:] or ["all"]
    for n in ("hud", "unlock", "events", "logo", "popup"):
        if "all" in todo or n in todo:
            globals()[n]()
