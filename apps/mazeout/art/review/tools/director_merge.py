#!/usr/bin/env python3
"""Art director, round 2: merge every lane's entries into art/MANIFEST.json and apply the director's own changes.

    cd apps/mazeout; python3 art/review/tools/director_merge.py [--dry]

Re-runnable: it always starts from the pre-merge manifest (build/ui-art/MANIFEST.pre_director.json, a copy of the
committed round-1 MANIFEST.json) so running it twice gives the same result.

1. writes the two lane files that only existed as gitignored scratch copies, so the merge survives a clean checkout:
   art/lanes/scene.entries.json  (from build/ui-art/scene/scene_manifest.json, the scene lane's 16 entries)
   art/lanes/svg.entries.json    (the svg lane's 38 entries from build/ui-art/lane_svg/MANIFEST.json + art/lanes/svg.md:
                                  status done, corrected refs, text_live / anchor)
2. writes art/lanes/director.entries.json: the director's round-2 changes (frames that changed with the fixes, new ids,
   not-shipped markings, grades); sizes are read from the rendered files so the manifest cannot drift from the disk
3. merges characters, 3d-hud, 3d-events, scene, svg, director (in that order; later wins) with art/tools/manifest.py's
   merge_diff / merge_apply, then regenerates art/ID-MAP.md

Round 3 (art director, 2026-09-25 afternoon) appends, after `director`:
4. the round-3 lanes missing-svg, missing-3d, polish (polish AFTER director: director.entries.json still carries the
   round-2 frame sizes of the ids polish resized)
5. art/lanes/director-r3.entries.json: the round-3 rulings (Weekly Contest lettering = SwiftUI EventLogo with live text,
   its renders a look target; frostCracks not shipped, fxFrostVignette alone; heartBig = the SVG) + the director's fixes'
   notes, with every round-3 grade from art/review/grades-director.json applied; sizes read from the rendered files
   (weeklyContestLogoTR stays as the TR look target of the same SwiftUI EventLogo: a lane merge never deletes an id)
The round-2 step reads its grades from art/review/grades-director-r2.json, so director.entries.json stays round 2's.

Round 4 (2026-09-25 evening) appends, after `director-r3`:
6. the round-4 lanes in ROUND4_LANES that have an art/lanes/<lane>.entries.json (plain lane files, merged as written):
   `corner` (the CORNER obstacle: cornerWedge + the eight per-turn layers + unlockIconCorner; art/lanes/corner.md)
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(APP, "art", "tools"))
import manifest as MF  # noqa: E402

LANES = os.path.join(APP, "art", "lanes")
PRE = os.path.join(APP, "build", "ui-art", "MANIFEST.pre_director.json")
GRADES = os.path.join(APP, "art", "review", "grades-director-r2.json")      # round 2's grades (the director r2 step)
GRADES_R3 = os.path.join(APP, "art", "review", "grades-director.json")      # the grades that count now (round 3)
ROUND4_LANES = ["corner"]
LANE_ORDER = ["characters", "3d-hud", "3d-events", "scene", "svg", "director", "missing-svg", "missing-3d", "polish",
              "director-r3"] + ROUND4_LANES   # manifest_check.py --lanes merges in this order too (later wins)


def jload(p):
    return json.load(open(p))


def jsave(p, d):
    with open(p, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")


def px_size(rel):
    from PIL import Image
    im = Image.open(os.path.join(APP, rel))
    return [round(im.width / 3), round(im.height / 3)]


# ------------------------------------------------------------------ 1. scene + svg lane files
def scene_entries():
    src = jload(os.path.join(APP, "build", "ui-art", "scene", "scene_manifest.json"))["entries"]
    out = []
    for e in src:
        e = dict(e)
        if e.get("file") and os.path.exists(os.path.join(APP, e["file"])):
            e["size_pt"] = px_size(e["file"])
            e["size_px"] = [v * 3 for v in e["size_pt"]]
        out.append(e)
    return {"version": 1, "title": "scene lane entries (committed copy of build/ui-art/scene/scene_manifest.json, written by "
                                   "the art director round 2; sizes read from the rendered files)", "entries": out}


SVG_REFS = {   # art/lanes/svg.md "Corrected refs for the manifest merge"
    "unlockIconLinked": {"video": "research/video/owner/V1-levels-01-20.mp4", "t": 78.0, "box_pt": [118, 348, 274, 470], "scale": 1.25},
    "unlockIconDoor": {"video": "research/video/owner/V1-levels-01-20.mp4", "t": 185.0, "box_pt": [92.9, 262.3, 305.4, 481.2], "scale": 1.45},
    "unlockIconPipe": {"shot": "research/shots/040-L35-pipe-unlocked.png", "box_pt": [117.8, 340.4, 273.8, 464.4]},
    "unlockIconElevator": {"video": "research/video/owner/V2-levels-11-38.mp4", "t": 1182.5, "box_pt": [110, 348, 282, 470], "scale": 1.37},
    "iconCoin": {"shot": "research/shots/003-L32-start.png", "box_pt": [15, 27, 45, 57], "scale": 0.89},
    "iconStopwatch": {"shot": "research/shots/003-L32-start.png", "box_pt": [90.7, 76.5, 123.7, 109.5]},
    "iconStopwatchSmall": {"shot": "research/shots/026-home-after-L32.png", "box_pt": [162, 146, 180, 172]},
    "heartHUDLost": {"shot": "research/shots/110-L047-after-bump.png", "box_pt": [272.1, 80.6, 303.1, 107.6]},
    "heartLives": {"shot": "research/shots/026-home-after-L32.png", "box_pt": [212.5, 53, 251.5, 86], "scale": 1.1},
    "glyphSound": {"shot": "research/shots/007-L32-pause.png", "box_pt": [74, 331, 104, 361]},
    "glyphGear": {"shot": "research/shots/026-home-after-L32.png", "box_pt": [341.3, 55.4, 367.3, 81.4]},
    "rankBadgeGold": {"shot": "research/store/iphone-6.png", "box_pt": [14, 581, 56, 621], "scale": 1.19},
    "rankBadgeSilver": {"shot": "research/store/iphone-6.png", "box_pt": [14, 661, 56, 701], "scale": 1.19},
    "rankBadgeBronze": {"shot": "research/store/iphone-6.png", "box_pt": [14, 740, 56, 780], "scale": 1.19},
    "rankBadgePlain": {"shot": "research/store/iphone-6.png", "box_pt": [14, 740, 56, 780], "scale": 1.19},
    "iconHexArrow": {"shot": "research/shots/026-home-after-L32.png", "box_pt": [30, 106, 78, 150]},
}


def svg_entries():
    src = jload(os.path.join(APP, "build", "ui-art", "lane_svg", "MANIFEST.json"))["entries"]
    out = []
    for e in src:
        if not str(e.get("source", "")).startswith("art/ui/src/svg/gen_icons.py"):
            continue
        e = dict(e)
        e["status"] = "done"
        e["owner"] = "ui-art"
        if e["id"] in SVG_REFS:
            e["ref"] = SVG_REFS[e["id"]]
        out.append(e)
    return {"version": 1, "title": "svg lane entries (the lane's scratch copy build/ui-art/lane_svg/MANIFEST.json, statuses from "
                                   "art/lanes/svg.md; written by the art director round 2)", "entries": out}


# ------------------------------------------------------------------ 2. the director's changes
NOT_SHIPPED = ("NOT SHIPPED (SPEC-ui 4.4; director r2): kept for provenance, confirmed false; no build agent references it.")


def director_entries(base):
    have = MF.by_id(base)
    E = {}

    def upd(i, **kw):
        e = copy.deepcopy(have[i]) if i in have and i not in E else E.get(i, {"id": i})
        e.update(kw)
        if kw.get("file") or e.get("file"):
            f = e["file"]
            if f and f.endswith(".png") and os.path.exists(os.path.join(APP, f)) and not e.get("exact_px") and not e.get("rig"):
                e["size_pt"] = px_size(f)
                e["size_px"] = [v * 3 for v in e["size_pt"]]
        E[i] = e

    # -- frames that changed with the round-2 fixes (sizes read from the rendered files)
    upd("navHome", ref={"shot": "research/shots/026-home-after-L32.png", "box_pt": [157, 730, 237, 816]},
        notes="3d-hud; director r2: 66x66 -> 80x86 (026's raised Home icon is 74 x 82 pt: round 1 was 0.7x), wider body, "
              "thicker arch / eaves / door frame / corner blocks, deeper orange (orangeHouse). Frame top-left (157, 730) pt.")
    upd("tutorialHand", anchor_pt=[20.3, 5.8],
        ref={"video": "research/video/owner/V1-levels-01-20.mp4", "t": 1.2, "box_pt": [176, 410, 286, 555], "anchor_pt": [193, 424]},
        purpose="yellow emoji-style pointing hand with its big soft grey shadow (tap tutorial)",
        notes="director r2: frame 102 x 136 (hand ~80 x 99 pt as V1 t 1.2 shows it, + V1's big soft shadow down-right); "
              "anchor_pt = the fingertip in frame pt (the app places it on the target cell); slimmer, rounder palm.")
    upd("glyphHaptic", notes="007 Paused panel (cream face, brown outline); director r2: frame 34 x 33 (the measured ink "
                             "32.4 x 31.1 pt no longer shrinks to 0.9). Settings uses glyphHapticWhite.")
    upd("iconPlusGreen", notes="director r2: frame 20 pt (the home slot is 18.7 pt; 16 pt read small)")
    upd("glyphMusic", ref={"shot": "research/shots/meta-029-settings.png", "box_pt": [172, 320, 221, 367]},
        purpose="music-note glyph, WHITE on the green Settings button (the red off-slash is live UI)",
        notes="director r2: redrawn from the phone's Settings page meta-029 (white face, thin dark-green outline, on a green "
              "square button), frame 38 x 36; round 1 was the Paused panel's cream/brown style from the V2 build (muddy on green).")
    upd("glyphBell", ref={"shot": "research/shots/meta-029-settings.png", "box_pt": [43, 163, 76, 201]},
        purpose="notification bell (Settings, Notifications row): white-to-ice-blue face, navy outline, clapper",
        notes="director r2: redrawn from meta-029 (round 1 followed the V2 build: a 17 pt cream bell without an outline); "
              "frame 30 x 36.")
    upd("iconPencil", ref={"shot": "research/shots/meta-002-avatar-tap.png", "box_pt": [95, 209, 130, 244]},
        notes="director r2: the same drawing at the phone size (meta-002 disc ~33 pt; round 1 was 0.6x): frame 32 pt.")
    upd("statFirstTryIcon", ref={"shot": "research/shots/meta-002-avatar-tap.png", "box_pt": [29, 339, 85, 391]},
        notes="director r2: meta-002 size (~51 x 50 pt; round 1 0.6x) and a thick glossy red side; frame 56 x 54.")
    upd("statWeeklyWinsIcon", ref={"shot": "research/shots/meta-002-avatar-tap.png", "box_pt": [219, 340, 263, 394]},
        notes="director r2: meta-002 size (~38 x 51 pt, coin ~36 pt; round 1 0.62x), ribbon as wide as the medal, a wider "
              "gold bar; frame 48 x 51. The '1' is baked (a fixed part of the medal).")
    upd("iconCheckeredFlag", notes="director r2: redrawn from 016's Streak Race logo flags (grader A: a different flag): "
                                   "grey-lilac pole + silver knob leaning left, a thick waving cloth with BIG glossy 3 x 2 "
                                   "checks (cream #F5EEDD / slate #4A6696), navy outline.")
    upd("scoreChip", purpose="the green capsule (flag roll) at the left of a Streak Race score (the number plate behind it is "
                             "a row-tinted SwiftUI shape; the score is live text on it)",
        text_live=False,
        notes="director r2: CAPSULE ONLY at store 6's size (~36 x 40 pt; round 1 0.75x in a 64 x 36 frame with one brown "
              "plate for every row). SHELL: draw the plate as a SwiftUI capsule tinted per row (gold row #A0500A, silver row "
              "#4A5AA8, bronze row #9A3A1A at ~0.9) with the capsule's centre on its left end. The same sprite is SPEC-ui's "
              "proposed iconFlagRoll.")
    upd("logoArrowOut", notes="OUR 'ARROW OUT!' lettering; director r2: chunkier bubble letters (compression 0.70 -> 0.78, "
                              "inflation 14 -> 22, extrusion 66 -> 90) inside the plate, OUT! fatter; placed on the loading "
                              "screen at the original logo's box (x 21-218, y 65-217 pt; frame scaled 197/290.7).")
    upd("homeConsole", notes="scene; director r2: rebuilt against 002: rim x 99..294 pt (193 wide; round 1 ~0.9x), a THICK "
                             "glossy blue rim band (RIM_H 1.45 u), a deeper bulging belly with a warm cream-to-yellow gradient, "
                             "a short base; fitted by width, bottom at 373 pt; frame 214 x 109 at (95, 266).")
    upd("homeCapsuleMachine", notes="scene; director r2: slanted light-cyan inner walls (002's ~24 pt bevel) taper the cavity; "
                                    "the arrow piles hold this machine out (machine_hold) so they stay inside the window.")
    for p in ("Full", "Half", "Low"):
        upd(f"homeArrowPile{p}", notes="scene; director r2: re-laid from 002 / 168 / 070 at 6 px/pt: chunky block arrows "
                                       "(head 0.58, shaft 0.54 x 0.54), a wide low mound in four depth rows (Full), face-on "
                                       "(pitch -14..-34), weighted colour mix (lilac/sky most, lime least); the machine is a "
                                       "holdout so nothing crosses the bezel (round 1 spilled ~20 pt out of the window).")
    upd("skyJumpIsland", ref={"shot": "research/shots/069-skyjump-screen.png", "box_pt": [66, 306, 326, 562]},
        notes="scene; director r2: fitted by the island's width (069: ~220 pt; round 1 ~172), thicker cream/gold layers, "
              "the 069 chest (lavender body, green quilt lid open 36 deg with the green shield on it), tall coin stacks, "
              "deeper gold; the haze fades out inside the frame (round 1 drew a rectangle). Frame 260 x 256 at (66, 306). "
              "The PRIZE sign is baked blank (live text: face box as art/lanes/scene.md, scaled).")
    upd("skyJumpIslandFar", ref={"shot": "research/shots/069-skyjump-screen.png", "box_pt": [6, 222, 172, 380]},
        notes="scene; director r2: as skyJumpIsland (width fit ~139 pt, dense stacks, haze inside the frame). Frame 166 x 158 "
              "at (6, 222). The upper-right purple-chest island of 069 has no id yet (round 2: skyJumpIslandFar2).")
    upd("skyJumpPopupScene", notes="scene; director r2: deeper orange-gold coins, a warm glow behind the heap, the 065 chest "
                                   "(lavender, quilt lid + shield). Remaining: 065's lid is opened wider over a heap of coins.")
    upd("rocketRaceBackdrop", confirmed=True,
        notes="scene; director r2: the moon ground ends under the banner and the lane area is deep indigo (#16105C -> #420FAC) "
              "with faint stars (round 1: flat lavender); the hoard is seen from higher with the chest turned 18 deg.")
    upd("clawHeaderArt", notes="scene; director r2: rebuilt with char_workerClawPair composited behind the prizes (round 1 was "
                               "built before the pair existed).")
    upd("loadingBackdrop", notes="scene; director r2: the floor's far-tile speckle band is gone (seams + per-tile jitter fade "
                                 "where a tile is < ~16 pt), tiles 1.6x bigger, the room behind the cast defocused (4.5 px) and "
                                 "hazed toward the backlit opening, soft contact shadows baked under the grounded cast (from "
                                 "char_loading_layout.json). Remaining: the left press is still flat panels, no conveyor.")
    for i in ("coinPackTiny", "coinPackSmall", "coinPackMedium", "coinPackBig", "coinPackSuper", "coinPackGiant"):
        upd(i, notes="3d-events: pile fitted to its meta-011 bbox; shared 102 x 66 frame, bottom-aligned; director r2: the "
                     "base shadow fades to 0 before the frame's bottom edge (round 1 cut it: a faint hard line on the card).")
    # -- the phone BOX (SPEC 5.11 / SPEC-ui 4.3): boxSlab (9-slice) + boxRing; curtainCrate not shipped
    upd("boxSlab", family="svg", route="C3", group="board", purpose="the phone's BOX obstacle slab (violet, four rivets, bottom "
        "lip): authored at 3 x 3 cells, 9-sliced by the engine to any W x H block (cap insets 0.5 pitch + the 4 pt margin)",
        screen="level board (counter levels)", source="art/ui/src/gen_board.py:boxSlab", file="art/ui/out/boxSlab@3x.png",
        ref={"shot": "research/shots/135-L050-start.png", "box_pt": [50, 600, 345, 700], "pitch_pt": 28.07},
        status="done", owner="pipeline", pitch_pt=32, anchor_pt=[4.0, 4.0],
        notes="director r2 (grader A graded the curtain crate C as the BOX skin): measured on 135 (L50, 10 x 3 cells) -- "
              "corner r 0.40 pitch, face #BC5BF6, light top line, side darkening 0.26, bottom lip 0.28, rivets d 0.31 at 0.50 "
              "pitch from both edges, soft shadow 0.1 pitch. anchor = top-left of the cell block. The counter ring is a "
              "separate fixed-size sprite (boxRing). gen_board.box_case(w, h) renders any size for proofs (boxW10H3).")
    upd("boxRing", family="svg", route="C3", group="board", purpose="the Box's counter ring: silver sphere with four stubby "
        "lugs, purple ring, navy well (the counter is live text in the well); a FIXED size (2.2 pitch across the sphere + lugs)",
        screen="level board (counter levels)", source="art/ui/src/gen_board.py:boxRing", file="art/ui/out/boxRing@3x.png",
        ref={"shot": "research/shots/135-L050-start.png", "box_pt": [165, 615, 228, 680], "pitch_pt": 28.07},
        status="done", owner="pipeline", pitch_pt=32, text_live=True,
        notes="director r2: centred on the block (anchor = frame centre = block centre); the engine scales it by pitch/32 "
              "like the slab (round 1's crate grew the sphere with the block: a 10 x 9 box got a huge sphere). Every box in "
              "levels.json is >= 3 cells on each side, so the fixed size always fits. Counter text: white, purple outline "
              "#4B1F86, ~0.8 pitch.")
    upd("unlockIconBox", family="svg", route="B2", group="popups", purpose="the Box unlock card icon: the board's Box slab "
        "(rounder, no rivets) + the counter ring nearly filling it; the digit is live text in the well",
        screen="Box! Unlocked!", source="art/ui/src/svg/gen_icons.py:unlockIconBox", file="art/ui/out/unlockIconBox@3x.png",
        ref={"shot": "research/shots/134-L050-box-unlock.png", "box_pt": [130, 337, 262, 471]},
        status="done", owner="ui-art", text_live=True,
        notes="director r2: the id design/levels.json uses (grader A: unlockIconCurtain vs unlockIconBox disagreed). Drawn "
              "with gen_board.box_slab / box_ring at P = 40 pt so the slab is 134's 120 pt; the counter well is centred 2 pt "
              "above the frame centre. SHELL: UIArt.swift still says unlockIconCurtain -> rename to unlockIconBox.")
    upd("glyphSoundWhite", family="svg", route="B2", group="profile-shop-settings", purpose="speaker glyph, WHITE on the green "
        "Settings button (Sound)", screen="Settings", source="art/ui/src/svg/gen_icons.py:glyphSoundWhite",
        file="art/ui/out/glyphSoundWhite@3x.png", ref={"shot": "research/shots/meta-029-settings.png", "box_pt": [68, 322, 116, 368]},
        status="done", owner="ui-art", notes="director r2: the Settings variant of glyphSound (meta-029: white face, dark-green "
                                              "outline; grader A asked for white Settings variants of sound and haptic).")
    upd("glyphHapticWhite", family="svg", route="B2", group="profile-shop-settings", purpose="vibrating-phone glyph, WHITE on "
        "the green Settings button (Haptic)", screen="Settings", source="art/ui/src/svg/gen_icons.py:glyphHapticWhite",
        file="art/ui/out/glyphHapticWhite@3x.png", ref={"shot": "research/shots/meta-029-settings.png", "box_pt": [276, 322, 324, 368]},
        status="done", owner="ui-art", notes="director r2: the Settings variant of glyphHaptic (meta-029).")
    # -- not shipped (SPEC-ui 4.4) -- kept, confirmed false
    for i in ("curtainCrate", "unlockIconCurtain", "rankBadgePlain", "boosterPointer", "boosterDome", "curtainCyan",
              "avatarGreen", "avatarRed", "avatarCap", "avatarBlue", "avatarPoint", "avatarSpecs", "avatarShades", "avatarPink"):
        if i in have:
            upd(i, confirmed=False, notes=NOT_SHIPPED + " " + str(have[i].get("notes", ""))[:400])
    upd("prizeSign", confirmed=False,
        notes=NOT_SHIPPED + " Director r2 (grader A: two PRIZE signs on Sky Jump): the scene lane's islands and popup scene "
              "bake the 3D sign (blank face, live text), so this flat sprite is not used.")
    upd("unlockIconCurtain", notes=NOT_SHIPPED + " Replaced by unlockIconBox (the phone Box card, the id levels.json uses).")
    upd("curtainCrate", notes=NOT_SHIPPED + " The videos' Curtain/Box levels use the phone BOX skin: boxSlab + boxRing.")
    upd("rankBadgePlain", notes=NOT_SHIPPED + " Ranks 4+ are plain outlined digits on the phone (203, meta-013): live text.")
    return E


# ------------------------------------------------------------------ round 3: rulings + fixes (merged after every lane)
R3_NOT_SHIPPED = "NOT SHIPPED (director r3): kept for provenance, confirmed false; no build agent references it."
WEEKLY_TARGETS = ["art/ui/code/targets/weeklyContestLogo@3x.png", "art/ui/code/targets/weeklyContestLogoTR@3x.png"]
LOGO_CUTS = [0.2470, 0.3950, 0.5545, 0.7370]   # ARROW's letter gaps in the r3 logo (fraction of W; measured on the render)


def director_r3_entries(m):
    have = MF.by_id(m)
    E = {}

    def upd(i, **kw):
        e = copy.deepcopy(have[i])
        e.update(kw)
        f = e.get("file")
        if f and f.endswith(".png") and os.path.exists(os.path.join(APP, f)) and not e.get("exact_px") and not e.get("rig"):
            e["size_pt"] = px_size(f)
            e["size_px"] = [v * 3 for v in e["size_pt"]]
        E[i] = e

    def note(i, text):
        upd(i, notes=(str(have[i].get("notes", "")) + " " + text).strip())

    # -- rulings the lanes asked for
    upd("weeklyContestLogo", family="swiftui", route="B1", source="art/ui/code/GlossyChrome.swift:EventLogo", file=None,
        status="todo", owner="shell", text_live=True, preview=WEEKLY_TARGETS[0], targets=WEEKLY_TARGETS,
        variants=["weeklyContestLogoTR"],
        purpose="'Weekly Contest' / 'Haftalik Yarisma' lettering on the Weekly page rail: the SwiftUI EventLogo with LIVE text",
        notes="DIRECTOR R3 RULING (the missing-3d lane asked): SwiftUI EventLogo with live text, as SPEC-ui 2.15.3 / 4.2 route "
              "B1 says and like the other four event logos (streakRaceLogo, clawLogo, skyJumpLogo, rocketRaceLogo); "
              "PIPELINE's rule is never to bake translatable text. The lane's per-language renders are the LOOK TARGET the "
              "EventLogo must match (graded B+ as art: bevels, blue outline, cyan rim, extrusion) -- `targets` (EN, TR; "
              "committed, never bundled). Layer recipe to port: art/ui/recipes/m3d_events.py build_weekly_logo (face "
              "#FFED40 -> #FAB910 'Weekly' + white 'Contest', 2.5 pt #034AC8 outline, #14C4F9 rim, 3 pt extrusion). "
              "Frame 277 x 54 at (60.1, 193.5) (SPEC-ui said 50: the 'y' descender + outline + extrusion reach 54).")
    upd("weeklyContestLogoTR", family="swiftui", route="B1", source="art/ui/code/GlossyChrome.swift:EventLogo", file=None,
        status="todo", owner="shell", text_live=True, preview=WEEKLY_TARGETS[1],
        purpose="the TR look of the Weekly Contest EventLogo ('Haftalik Yarisma', live text) -- the same SwiftUI component as "
                "weeklyContestLogo",
        notes="DIRECTOR R3 RULING: see weeklyContestLogo (SwiftUI EventLogo, live text). This id only keeps the TR render as "
              "the look target (`preview`); it is not a separate component or file.")
    upd("frostCracks", confirmed=False,
        notes=R3_NOT_SHIPPED + " Ruling: fxFrostVignette ships ALONE (one full-screen overlay that already paints the cracks); "
              "this 120 pt corner tile served SPEC-ui's other route (code gradient + tile) and would double the cracks. "
              + str(have["frostCracks"].get("notes", ""))[:300])
    note("fxFrostVignette", "DIRECTOR R3 RULING: this overlay ships alone (frostCracks is not shipped). Draw it full-screen "
                            "(.resizable, fill) between the board and the HUD while the freeze runs.")
    note("heartBig", "DIRECTOR R3: the SVG ships (the 3D candidate at build/ui-art/route3d/heartBig.png has a fatter "
                     "silhouette and a shallow notch next to 088). Fixed: the speculars' gradients were rotated twice "
                     "(hard edges), the notch smudges removed, a lighter top band, 088's soft right-lobe streak + shoulder "
                     "crescent. SHELL: OutOfTimePopup draws a code heart today -- use UIArt.heartBig at (99.5, 316) 194 x 164.")
    for i in ("bundleBarrel", "bundleChest", "bundleSafe", "bundleCart"):
        note(i, "DIRECTOR R3: heap coins drawn bigger at 0.64 diameter spacing (m3d_shop big_heap / big_stack): the scale-1 "
                "heaps packed coins at 0.47 of a diameter, so each showed only a crescent and the heaps read as noodles."
                + (" No cast shadows (a hard diagonal shadow wedge crossed the coins)." if i == "bundleSafe" else ""))
    note("bundleBarrel", "Ids: SPEC-ui 4.2's bundleChestRed / bundleChestPurple do not exist -- Epic = bundleBarrel, "
                         "Elite = bundleChest (what the phone draws).")
    for i in ("planetStage1", "planetStage2", "planetStage3"):
        note(i, "DIRECTOR R3: coloured by latitude bands read off 163 (m3d_events._lat_planet) instead of thin sine lines; "
                "less glass haze" + ("; a fatter, brighter ring." if i == "planetStage3" else "."))
    note("iconSkull", "DIRECTOR R3: the cranium is a dome (ellipse), not a rounded box (shared with iconSkullBones).")
    note("iconSkullBones", "DIRECTOR R3: dome cranium; fatter bones (shaft 4.0 pt) and knobs (2.85 pt).")
    note("logoArrowOut", "DIRECTOR R3: the letters no longer melt together -- a compression per letter (0.75 0.77 0.77 0.73 "
                         "0.60), span 222-1828 design px, inflation 32, baseline 635, extrusion 50, OUT! at cap 312. SHELL: "
                         "WinLogoSequence LogoParts.split cuts = [0, %s, W] (fractions of W, the letter gaps measured on "
                         "this render; they supersede art/lanes/polish.md section A.8's)." % ", ".join(
                             "Int(%.4f * Double(W))" % c for c in LOGO_CUTS))
    # -- every round-3 grade (the grades that count now)
    G = jload(GRADES_R3)
    for i, g in G["entries"].items():
        if i not in have and i not in E:
            continue
        if i not in E:
            E[i] = copy.deepcopy(have[i])
        e = E[i]
        e["grade"] = g["grade"]
        if g["grade"] in ("A", "B") and e.get("status") in ("done", "graded"):
            e["status"] = "graded"
    return {"version": 1, "title": "art director round 3 (2026-09-25): rulings, fixes and grades, merged after every lane "
                                   "(sizes read from the files)", "entries": list(E.values())}


# ------------------------------------------------------------------ 3. merge
def main():
    dry = "--dry" in sys.argv
    if not os.path.exists(PRE):
        shutil.copy(MF.PATH, PRE)
    m = jload(PRE)
    jsave(os.path.join(LANES, "scene.entries.json"), scene_entries())
    jsave(os.path.join(LANES, "svg.entries.json"), svg_entries())
    order = ["characters", "3d-hud", "3d-events", "scene", "svg"]
    for lane in order:
        d = jload(os.path.join(LANES, f"{lane}.entries.json"))
        diffs = MF.merge_diff(m, d)
        MF.merge_apply(m, diffs)
        print(f"merged {lane}: {len(diffs)} entries differ ({sum(1 for _, k, _ in diffs if k == 'new')} new)")
    E = director_entries(m)
    # grades (art/review/grades-director.json): grade + a short note on every graded entry; statuses follow them
    G = jload(GRADES) if os.path.exists(GRADES) else {}
    for i, g in G.get("entries", {}).items():
        e = E.get(i) or copy.deepcopy(MF.by_id(m).get(i))
        if e is None:
            continue
        e["grade"] = g["grade"]
        if g["grade"] in ("A", "B") and e.get("status") in ("done", "graded"):
            e["status"] = "graded"
        E[i] = e
    director = {"version": 1, "title": "art director round 2 (2026-09-25): changes merged after the round-2 lanes (sizes read from the files)",
                "entries": list(E.values())}
    jsave(os.path.join(LANES, "director.entries.json"), director)
    diffs = MF.merge_diff(m, director)
    MF.merge_apply(m, diffs)
    print(f"merged director: {len(diffs)} entries differ ({sum(1 for _, k, _ in diffs if k == 'new')} new)")
    # round 3: the new lanes after director (polish last: it resized ids director.entries.json still has at r2 sizes)
    for lane in ("missing-svg", "missing-3d", "polish"):
        d = jload(os.path.join(LANES, f"{lane}.entries.json"))
        diffs = MF.merge_diff(m, d)
        MF.merge_apply(m, diffs)
        print(f"merged {lane}: {len(diffs)} entries differ ({sum(1 for _, k, _ in diffs if k == 'new')} new)")
    r3 = director_r3_entries(m)
    jsave(os.path.join(LANES, "director-r3.entries.json"), r3)
    diffs = MF.merge_diff(m, r3)
    MF.merge_apply(m, diffs)
    print(f"merged director-r3: {len(diffs)} entries differ")
    # round 4: finished lanes after the round-3 rulings
    for lane in ROUND4_LANES:
        path = os.path.join(LANES, f"{lane}.entries.json")
        if not os.path.exists(path):
            continue
        diffs = MF.merge_diff(m, jload(path))
        MF.merge_apply(m, diffs)
        print(f"merged {lane} (round 4): {len(diffs)} entries differ ({sum(1 for _, k, _ in diffs if k == 'new')} new)")

    # support files the app reads next to the renders (not graphics): the loading layout
    m["support_files"] = [{"file": "art/out/char_loading_layout.json",
                           "why": "loading-screen cast placement (frame top-left pt, z) -- LoadingScreen reads it"}]
    m["notes"] = [n for n in m.get("notes", []) if not n.startswith(("Round 2", "Round 3", "Round 4"))] + [
        "Round 2 (art director, 2026-09-25): every lane merged (art/lanes/*.entries.json) + director changes "
        "(art/lanes/director.entries.json); grades in art/review/grades-director-r2.json.",
        "Round 3 (art director, 2026-09-25): lanes missing-svg, missing-3d, polish, characters merged + the round-3 "
        "rulings / fixes (art/lanes/director-r3.entries.json); the grades that count are art/review/grades-director.json "
        "and art/REVIEW.md. weeklyContestLogo / weeklyContestLogoTR are now ONE SwiftUI EventLogo (live text); their "
        "renders in art/ui/code/targets are look targets, never bundled."] + (
        ["Round 4 (2026-09-25): lane corner merged after director-r3 (art/lanes/corner.entries.json; art/lanes/corner.md): "
         "cornerWedge (the id the board code and the level bundle's sprite check load), the eight per-turn corner layers "
         "and unlockIconCorner."] if os.path.exists(os.path.join(LANES, "corner.entries.json")) else [])
    if dry:
        print("dry run: MANIFEST.json not written")
        return
    MF.save(m)
    MF.write_idmap(m)
    print("wrote", os.path.relpath(MF.PATH, APP), "and art/ID-MAP.md;", len(m["entries"]), "entries")


if __name__ == "__main__":
    main()
