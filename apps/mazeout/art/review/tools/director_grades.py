#!/usr/bin/env python3
"""Art director round 2: the grades after the round-2 fixes, written to art/review/grades-director-r2.json (the
round-3 grades that count now are art/review/grades-director.json, written by director_grades_r3.py from this file). Starts from graders A and B (art/review/grades-{A,B}.json, the 'before' column) and
applies the director's re-grades, judged at game size on art/ui/sheets/director/*.png (composed screens next to their
references at the same scale; director_proofs.py rebuilds them).
    cd apps/mazeout; python3 art/review/tools/director_grades.py"""
import json
import os

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
A = json.load(open(os.path.join(APP, "art/review/grades-A.json")))
B = json.load(open(os.path.join(APP, "art/review/grades-B.json")))

NS = "n/a"   # not shipped (SPEC-ui 4.4) -- not counted
REGRADE = {
    # id: (after, what changed / why, sheet)
    # ---- (a) the capsule-machine pile + the window
    "homeArrowPileFull": ("A", "Re-laid from 002: chunky block arrows, wide low mound in 4 depth rows, face-on, weighted colours; the "
                               "machine is a holdout, so the heap stays inside the glass. At game size it reads as 002's pile.",
                          "director/win_homeArrowPileFull.png, director/p_home.png"),
    "homeArrowPileHalf": ("B", "Inside the window now; lower heap + a 2-arrow falling column (168). 168's heap is a taller centre "
                               "column.", "director/win_homeArrowPileHalf.png"),
    "homeArrowPileLow": ("B", "Arrows stand on the floor, the emerging arrow shows its shaft (070). 070's arrows cluster more.",
                         "director/win_homeArrowPileLow.png"),
    "homeCapsuleMachine": ("B", "Slanted light-cyan inner walls added (002's thick bevel). The glass sheen is still painted.",
                           "director/win_homeArrowPileFull.png"),
    # ---- home
    "homeConsole": ("B", "Rim now 193 pt (x 99-294 like 002), thick glossy blue rim, deeper bulging belly with a warm gradient, "
                         "short base. Sits ~4 pt higher than 002; the belly's warm yellow is paler.", "director/console_after.png"),
    "navHome": ("B", "80 x 86 frame (026's icon is 74 x 82), wider body, thick arch, deeper orange. The eaves sit a little low.",
                "director/navhome_after.png"),
    "workerWalkie": ("B", "Default layer = closed smile (the rest frames); stronger warm rim + key for the separation from the "
                          "blue lab. Arms still thinner than theirs.", "director/p_home.png"),
    "workerClipboard": ("B", "Stronger warm rim + key (separation). Clipboard still shows the paper side.", "director/p_home.png"),
    # ---- (b) loading
    "scientistLoading": ("B", "Big open smile (one tooth band) instead of the buck-tooth D; taller, rounder head; SHORT rolled sleeves "
                              "with fur forearms; fist at chin level; white shirt. The fist reads as a fur cylinder, not a clenched "
                              "ball.", "director/sci_loading_draft.png, director/p_loading.png"),
    "workerCarrier": ("B", "Taller, narrower bean at 92 pt/u, chunky running legs reaching ~y 750, box without the 'eye' holes and "
                           "tipped so its underside shows, a laughing mouth, a contact shadow. V1's near foot is lifted higher.",
                      "director/p_loading.png"),
    "workerFist": ("B", "Laughing mouth (one tooth band), chunky legs + feet, contact shadow.", "director/p_loading.png"),
    "workerRunners": ("B", "Hazed and defocused (2.2 px + 36 % room tint), 12 % bigger, soft floor shadow. The left conveyor pair is "
                           "still missing (P1).", "director/p_loading.png"),
    "loadingBackdrop": ("B", "Speckle band gone, bigger tiles with visible near seams, the room defocused and hazed, contact shadows "
                             "under the cast. The left press is still flat panels (no conveyor).", "director/p_loading.png"),
    "logoArrowOut": ("B", "Chunkier letters (0.78 compression, fatter inflation, deeper extrusion), placed at the original logo's "
                          "box. MAZE's four letters are still rounder than our five.", "director/logo.png, director/p_loading.png"),
    # ---- (c) svg C's + requests
    "tutorialHand": ("B", "Frame 102 x 136: the hand is ~80 x 99 pt (V1: 70 x 99) with V1's big soft shadow straight down; slimmer, "
                          "rounder palm. The fist is still ~14 % wider.", "director/svg_misc2.png"),
    "scoreChip": ("B", "Capsule only at store 6's size (the row-tinted plate is SwiftUI, shell). Caps slightly paler gold.",
                  "director/svg_misc.png"),
    "glyphMusic": ("A", "White on green from meta-029 (was the Paused panel's cream/brown).", "director/settings_meta029.png"),
    "glyphBell": ("B", "meta-029's white/ice bell with a navy outline, 30 x 36. The lip band is narrower than the phone's.",
                  "director/settings_meta029.png"),
    "iconPencil": ("A", "Same drawing at the phone's 32 pt.", "director/profile_meta002.png"),
    "statFirstTryIcon": ("B", "1.6x bigger (56 x 54) with a thick glossy side. The target face is slightly smaller than meta-002's.",
                         "director/profile_meta002.png"),
    "statWeeklyWinsIcon": ("B", "1.33x bigger (48 x 51), ribbon as wide as the medal, wider gold bar.", "director/profile_meta002.png"),
    "iconCheckeredFlag": ("B", "Redrawn from 016: grey pole + silver knob, a waving cloth with big glossy cream/slate 3 x 2 checks.",
                          "director/svg_misc.png"),
    "iconPlusGreen": ("A", "20 pt frame for the 18.7 pt slot.", "-"),
    "glyphHaptic": ("B", "34 x 33 frame (the measured ink no longer shrinks). Zig-zags still a little short.", "-"),
    "unlockIconCurtain": (NS, "Replaced by unlockIconBox (the phone Box card).", "-"),
    "curtainCrate": (NS, "The phone BOX skin ships instead: boxSlab + boxRing.", "director/box_135.png"),
    "rankBadgePlain": (NS, "Ranks 4+ are live outlined digits on the phone.", "-"),
    "prizeSign": (NS, "The islands / popup scene bake the 3D PRIZE sign (blank face, live text); one sign ships.", "-"),
    "settingsRoundToggle": ("C", "NOT ART: the app's Settings screen is still a Paused-style popup; the phone's is a full-screen page "
                                 "with three SQUARE glyph buttons (SPEC-ui 1.6.14 / 2.13). The glyph art for it now exists "
                                 "(glyphSoundWhite, glyphMusic, glyphHapticWhite, glyphBell). Owner: shell.", "director/settings_meta029.png"),
    # ---- events
    "clawHeaderArt": ("B", "Rebuilt with the two workers behind the prizes. 023's workers are bigger/closer, the box bluer.",
                      "director/claw.png"),
    "skyJumpIsland": ("B", "Width-fitted to 069's ~220 pt, thicker layers, the 069 chest (lavender, quilt + shield), tall coin "
                           "stacks, deeper gold, haze inside the frame. The sign stands left of the chest (069: overlapping it).",
                      "director/sky_069.png"),
    "skyJumpIslandFar": ("B", "Same fixes (~139 pt, stacks, haze inside the frame).", "director/sky_069.png"),
    "skyJumpPopupScene": ("B", "Orange-gold coins, a warm glow, the lavender chest with quilt + shield. 065's lid is open wider over "
                               "the coins.", "director/sky_065.png"),
    "rocketRaceBackdrop": ("B", "Deep indigo lane area with stars (the banner hides the seam). The chest is still an upright blue "
                                "barrel; 167's is a gold-banded chest seen from above.", "director/rocket_after.png"),
    "workerRacers": ("B", "Riders sit in their sleds (sunk in), laughing mouths. The chute is still a flat ribbon and the checkered "
                          "banner is missing.", "director/racers.png"),
    "coinPackTiny": ("B", "Shadow fades before the frame edge (no hard line).", "-"),
    "coinPackSmall": ("B", "Shadow fixed.", "-"), "coinPackMedium": ("B", "Shadow fixed.", "-"),
    "coinPackBig": ("B", "Shadow fixed.", "-"), "coinPackSuper": ("B", "Shadow fixed.", "-"), "coinPackGiant": ("B", "Shadow fixed.", "-"),
    "boosterDome": (NS, "Video-only 4-booster bar (SPEC 5.10 / SPEC-ui 4.4).", "-"),
    "boosterPointer": (NS, "Video-only 4-booster bar.", "-"),
}
for i in ("avatarWalkie", "avatarCapGlasses", "avatarDetective", "avatarBurger", "avatarParty", "avatarNotebook", "avatarBoxHead"):
    REGRADE[i] = ("B", "Re-framed as the phone's close-ups (40 pt/u: the bean fills the tile width, the belt at the bottom edge, the "
                       "cap inside), 3/4 turns, a laughing mouth with one tooth band. The phone's leans are stronger.",
                  "director/avatars.png")
REGRADE["avatarScientist"] = ("B", "Closer (34 pt/u), the big open smile. Still ~0.85x of the phone's head in its tile.",
                              "director/avatars.png")
for i in ("avatarGreen", "avatarRed", "avatarCap", "avatarBlue", "avatarPoint", "avatarSpecs", "avatarShades", "avatarPink"):
    REGRADE[i] = (NS, "The older V2 arrow-character set (SPEC 5.12).", "-")

NEW = {
    "boxSlab": ("A", "The phone BOX slab from 135: violet face, light top line, bottom lip, four rivets, 9-sliceable.",
                "director/box_135.png"),
    "boxRing": ("B", "Fixed-size counter ring (2.2 pitch). The lugs are a touch longer and whiter than 135's.", "director/box_135.png"),
    "unlockIconBox": ("B", "The phone Box card icon (134) from the same board sprites. The ring's lugs are whiter, the well a little "
                           "larger.", "director/svg_misc2.png"),
    "glyphSoundWhite": ("A", "meta-029's white speaker on green.", "director/settings_meta029.png"),
    "glyphHapticWhite": ("B", "meta-029's white vibrating phone; ~0.85x of the phone's glyph width.", "director/settings_meta029.png"),
}


def main():
    out = {"grader": "art director round 2", "date": "2026-09-25",
           "scale": "A = ship (a player takes it for the same art at game size), B = ok (differences only on inspection), "
                    "C = redo; n/a = not shipped (SPEC-ui 4.4), not counted",
           "entries": {}}
    before = {}
    for src, g in (("A", A), ("B", B)):
        for e in g["entries"]:
            before[e["id"]] = (e["grade"], src, e.get("note", ""))
    for i, (gb, src, note) in before.items():
        if i in REGRADE:
            g, what, sheet = REGRADE[i]
            out["entries"][i] = dict(grade=g, before=gb, grader=src, changed=what, sheet=sheet)
        else:
            out["entries"][i] = dict(grade=gb, before=gb, grader=src, changed="", sheet="")
    for i, (g, what, sheet) in NEW.items():
        out["entries"][i] = dict(grade=g, before="new", grader="director", changed=what, sheet=sheet)
    out["composed"] = {
        "homeProof": dict(grade="A", before="B", changed="Pile inside the window and shaped like 002's, console at 002's width, the "
                          "Home nav icon at 026's size; at game size the composed home reads as 002 (recoloured characters).",
                          sheet="director/p_home.png"),
        "loadingProof": dict(grade="B", before="C", changed="Scientist on-model (smile, short sleeves, fist), carrier tall with legs and "
                             "no box 'eyes', no speckle band, defocused hazy room, contact shadows, chunkier logo at the original "
                             "logo's box. Remaining: the left press is flat, the left conveyor pair and crowd are missing (P1).",
                             sheet="director/p_loading.png")}
    E = out["entries"]
    counted = [e["grade"] for e in E.values() if e["grade"] in ("A", "B", "C")]
    out["counts"] = {g: counted.count(g) for g in ("A", "B", "C")}
    out["counts"]["n/a"] = sum(1 for e in E.values() if e["grade"] == NS)
    out["counts"]["share_A"] = round(counted.count("A") / len(counted), 3)
    json.dump(out, open(os.path.join(APP, "art/review/grades-director-r2.json"), "w"), indent=1)
    print(out["counts"])


if __name__ == "__main__":
    main()
