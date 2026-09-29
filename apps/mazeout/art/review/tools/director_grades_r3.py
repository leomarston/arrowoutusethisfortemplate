#!/usr/bin/env python3
"""Art director round 3: the grades that count now, written to art/review/grades-director.json.

Starts from round 2 (art/review/grades-director-r2.json, the 'before' column) and applies the round-3 grades of every
entry the four round-3 lanes touched (missing-svg, missing-3d, polish, characters) plus the director's own fixes. Every
grade was judged at GAME size, next to its reference and in its composed screen, on the sheets named per entry
(art/ui/sheets/, gitignored; director_proofs_r3.py rebuilds the director3/ ones, manifest_sheets.py the m_<id> ones).

    cd apps/mazeout; python3 art/review/tools/director_grades_r3.py

Scale (unchanged): A = ship (a player takes it for the same art at game size), B = the same art, differences show on
inspection or side by side, C = redo; n/a = not shipped (not counted). "near A" in a note = the B is one small pass away.
"""
import json
import os

APP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
R2 = json.load(open(os.path.join(APP, "art/review/grades-director-r2.json")))
A1 = {e["id"]: e for e in json.load(open(os.path.join(APP, "art/review/grades-A.json")))["entries"]}
B1 = {e["id"]: e for e in json.load(open(os.path.join(APP, "art/review/grades-B.json")))["entries"]}
NS = "n/a"

# id: (grade, grader, what changed in round 3, remaining gap, sheet)
R3 = {
    # ------------------------------------------------------------------ polish lane (B -> A on their proofs; re-judged)
    "iconCoin": ("A", "polish", "Re-measured on 002's home coin: darker thick outline, a 6 pt thickness band, the recess's shaded "
                 "top wall, a chubby star with an extruded side, no white glints; frame 39 pt (home draws it 1:1).",
                 "Judged on home (002) and 003's HUD crop, not yet in an app render of the HUD (~0.68x).", "polish/hud_002.png"),
    "iconPlusGreen": ("A", "polish", "Frame 24 pt (the 23.5 pt rect draws it 1:1), vivid flat green, top light ring, short "
                      "chunky cream plus.", "none visible at game size", "polish/hud_002.png"),
    "iconStopwatchSmall": ("A", "polish", "Frame 26 x 28 (204's chip watch is 22.7 x 26 pt of ink; the old 18 pt frame drew it "
                           "at 0.7x): dome crown, warmer ring, long tick pills, fat wedge hand.",
                           "The hand angle is fixed (the original's turns).", "polish/hud_watch.png"),
    "heartLives": ("A", "polish", "Frame 42 x 40 = the shell's rect at 1:1; HEART2 at 002's 39.7 x 33.7; deeper crimson, dark top "
                   "band, softer darker outline.", "none visible at game size", "polish/hud_002.png"),
    "heartInfiniteSmall": ("A", "polish", "Heart 42 x 36.4 (was 45 x 39); a rounder, thinner-edged cream infinity.",
                           "none visible at game size", "polish/hud_168.png"),
    "iconHexArrow": ("A", "polish", "Frame 40 x 40, ink 37.3 x 35 at 1:1 (was ~1.15x); thick pale 3D side, sky-blue arrow with a "
                     "dark-purple edge.", "The chain hook belongs to the bar (shell).", "polish/hud_168.png"),
    "unlockIconBox": ("A", "polish", "Its own card illustration (no longer the board sprites): pillow slab, sphere in a dark "
                      "crease, four stubby lugs in front of the rim, tube-like purple ring, 41 pt navy well.",
                      "The lug caps are a touch flatter than 134's (2x only).", "polish/unlock.png"),
    "unlockIconLinked": ("A", "polish", "V1 t 78 s at 1:1 in a 150 x 106 frame (round 2 was 0.8x): 15.4 pt shafts, rounded heads, "
                         "the board tape.", "The V1 skin is the older build's (no phone card).", "polish/unlock.png"),
    "unlockIconElevator": ("A", "polish", "V2 t 1182.5 s at 1:1 in 164 x 112: icy blue-grey panels, soft outline, faint wide "
                           "stripes, flat windows.", "Unconfirmed on the phone (video-only obstacle).", "polish/unlock.png"),
    "unlockIconDoor": ("A", "polish", "V1 t 185 s: a SQUARE 5 x 5-cell card door, lock at the door's pitch; frame 128 x 128.",
                       "Unconfirmed on the phone (no v552 door card).", "polish/unlock.png"),
    "sunburstRays": ("A", "polish", "Frame 190 x 86 = 023's cream reward field clipped to its r 22 corners; rays reach the edges, "
                     "centred on the prize.", "none visible at game size", "polish/rays.png"),
    "rankBadgeGold": ("A", "polish", "203 at 1:1: 37.3 x 36.3 pt badge in a 40 frame, thin dark outline, 1.7 pt side, rim band, "
                      "window ring; gold from store 6.", "Gold is not captured on the phone.", "polish/streak_badges.png"),
    "rankBadgeSilver": ("A", "polish", "As gold (203 row 2 at 1:1).", "none visible at game size", "polish/streak_badges.png"),
    "rankBadgeBronze": ("A", "polish", "As gold (203 row 3 at 1:1).", "none visible at game size", "polish/streak_badges.png"),
    "logoArrowOut": ("B", "polish + director", "polish: solid graded extrusion + inner-bevel filter, fatter letters. director: the "
                     "five letters were 63 design px wider than their span BEFORE the 34 px inflation, so they melted into one "
                     "blob; now a compression per letter (W most), a wider span, inflation 32, baseline 25 px higher, extrusion "
                     "50 (the undersides stay on the blue face), OUT! at cap 312 with a purple margin.",
                     "near A: MAZE's letters are wider blocks with a crisper 3D side; ours are rounder (our OFL font, five "
                     "letters in the same plate).", "director3/logo_049.png"),
    # ------------------------------------------------------------------ characters lane (loading cast r3)
    "scientistLoading": ("B", "characters", "New 'load' pose: squat wide torso, the fist a clenched BALL beside the mouth, arrows "
                         "held at his side, fuller dome, raised brows, crescent smile, lighter fur, camera from a little above.",
                         "near A: the mouth opens rounder and deeper than store 8's grin (visible at game size side by side); "
                         "no lapel; the held arrows are thinner than store 8's chunky ones.",
                         "characters/p_loading_r2_r3_s8_1x.png, characters/final_sci.png"),
    "workerCarrier": ("B", "characters", "Full bean turned left, arms near-vertical to the box, short chunky legs with shoe feet, "
                      "tall laughing D, box seen from a little above; eye whites within ~2 pt of store 8.",
                      "near A: the mouth fills more of the face than store 8's; the legs are the body colour and blobby (store 8: "
                      "separate legs with shoes under purple pants).", "characters/carrier8.png"),
    "workerFist": ("B", "characters", "~20 % bigger, rounder bean, bigger glasses, fist on a thick arm, spiral notebook, wide grin, "
                   "chunky legs.", "The flexed arm is smaller; the fist sits partly behind the carrier's box; no cap tabs.",
                   "characters/fist7.png"),
    "workerRunners": ("B", "characters", "The right crowd at store 8's sizes and spots (top-hat worker, waver, burger eater), "
                      "chunky running legs, lighter haze (1.1 px / 12 %).",
                      "The burger eater's mouth is hidden behind the burger (store 8: gaping around it).",
                      "characters/crowd4.png"),
    "workerWalkie": ("B", "characters", "Rig gained eyes_wink + armL_wave (existing layers re-exported pixel-identical).",
                     "Arms still thinner than theirs; the wave/wink need ui.json tracks (shell).",
                     "characters/idle_wk_homeL_blue.png"),
}

NEW = {
    # ------------------------------------------------------------------ missing-svg lane (all new)
    "iconStopwatchFrozen": ("B", "missing-svg", "iconStopwatch's drawing at 1.02x under a snow cap with icicles, frame 34 x 50 "
                            "(the icicles hang to y 120).", "near A: the capture's cap is lumpier and a touch smaller, its icicle "
                            "clump longer.", "m_iconStopwatchFrozen.png"),
    "frostCracks": (NS, "missing-svg", "A 120 pt corner crack tile for SPEC-ui's code-vignette route.",
                    "not shipped: fxFrostVignette ships alone (it already paints the cracks)", "m_frostCracks.png"),
    "heartBig": ("A", "missing-svg + director", "missing-svg: the fitted two-ellipse heart (IoU 0.986 on 088). director: the "
                 "speculars' gradients were rotated twice (hard ellipse edges, a white parallelogram on the right lobe); the "
                 "dark lip smudges at the notch are gone; the top band is lighter; the right-lobe streak and shoulder crescent "
                 "are 088's soft ones.", "The notch reads a hair sharper than 088's (2x only).", "director3/heart_088.png"),
    "heartGlossySmall": ("A", "missing-svg", "The More Lives '+1 Live' button heart (had no id), the heartLivesBig style at 46 x 40.",
                         "The capture's specular is a touch larger (2x only).", "m_heartGlossySmall.png"),
    "heartLivesBig": ("A", "missing-svg", "The popup lives heart (meta-095), fitted box 92.5 x 79.4 in 100 x 90, orange specular.",
                      "The specular is a touch small (2x only).", "m_heartLivesBig.png"),
    "iconVideoAd": ("A", "missing-svg", "The clapper with the play triangle punched as a HOLE.", "none visible at game size",
                    "m_iconVideoAd.png"),
    "iconCheck": ("B", "missing-svg", "The glossy extruded Claw / Sky Jump check, 60 x 54.",
                  "The capture's extruded side is deeper and its short arm rounder.", "m_iconCheck.png"),
    "iconCheckBadge": ("B", "missing-svg", "The flatter Edit Profile badge (thick outline + inner light contour), 40 x 34.",
                       "The capture's dark outline is thicker and its green brighter.", "m_iconCheckBadge.png"),
    "iconSkull": ("A", "missing-svg + director", "Hard win-tag skull (037), eye sockets are holes; director: the cranium is a dome "
                  "(an ellipse), not a rounded box.", "none visible at game size", "director3/skulls.png"),
    "iconSkullBones": ("B", "missing-svg + director", "Super Hard skull over crossbones (063); director: dome cranium, fatter bones "
                       "and knobs.", "The bone shafts show a little longer between knob and skull than 063's.",
                       "director3/skulls.png"),
    "rankWings1": ("B", "missing-svg", "Gold diamond badge with wings (167/171), the '1' live.",
                   "near A: the wings are flatter and less notched than 167's.", "m_rankWings1.png"),
    "shopSeal": ("A", "missing-svg", "Red 8-lobe scalloped seal with a gold rim, text live, -12 deg.", "none visible at game size",
                 "m_shopSeal.png"),
    "pageBgPattern": ("A", "missing-svg", "meta-029's page pattern: 2 chunky arrows per 145 x 79.3 pt repeat at alpha 0.10.",
                      "none visible at game size", "m_pageBgPattern.png"),
    "pointerArrowDown": ("A", "missing-svg", "The Weekly tutorial's straight block arrow (130), a new drawing.",
                         "none visible at game size", "m_pointerArrowDown.png"),
    "glyphOffSlash": ("A", "missing-svg", "The Settings OFF rod as art (optional; the shell may keep its SwiftUI rod).",
                      "none visible at game size", "m_glyphOffSlash.png"),
    # ------------------------------------------------------------------ missing-3d lane (all new)
    "bundleSpecial": ("B", "missing-3d", "The 1 000 pile at the Special card's size + glints, frame 176 x 102.",
                      "The left coin on edge faces further right; the phone's glints are warmer and bigger.",
                      "m3d_bundleSpecial.png"),
    "bundleBag": ("B", "missing-3d", "Crimson sack with a twisted rope and knot on a lavender base, stacks either side.",
                  "The rope ends hang straighter and longer; the rolled rim is thinner.", "m3d_bundleBag.png"),
    "bundleBarrel": ("B", "missing-3d + director", "Crimson stave barrel, lavender hoop, broken hole, spill; director: the spill "
                     "coins 1.4x at 0.64 spacing and the top heap 1.2x (the scale-1 heaps read as rings).",
                     "The phone's barrel is squatter with fatter staves; its hole shows coins pouring out.",
                     "director3/shop_bundles.png"),
    "bundleChest": ("B", "missing-3d + director", "Red chest, lavender frame, pink gem; director: heap coins 1.45x at 0.64 spacing "
                    "(they read as noodles), stacks re-spaced, a brighter core.",
                    "The phone's chest is turned to show its left end, fills more of the card, and its lid is thrown back.",
                    "director3/shop_bundles.png"),
    "bundleSafe": ("B", "missing-3d + director", "Lavender safe, open door, coins pouring out; director: no cast shadows (a hard "
                   "diagonal shadow wedge crossed the coins), coins 1.45x at 0.64 spacing.",
                   "The phone shows the door's wheel face-on at the far left; ours shows the door edge-on.",
                   "director3/shop_bundles.png"),
    "bundleCart": ("B", "missing-3d + director", "Crimson cart, lavender posts and wheels; director: heap coins 1.6x at 0.64 spacing "
                   "(the scale-1 heap was a tangle of crescents), one taller load + a spill, stacks re-spaced.",
                   "The phone's cart is bigger in the card and its heap one continuous pyramid.",
                   "director3/shop_bundles.png"),
    "rocketOfferScene": ("B", "missing-3d", "Stars, banded planet, lilac moon, the gold/teal chest on a coin mound with a heart, "
                         "pink cloud bank (330 x 504 full bleed).",
                         "The chest is seen straight on (163: turned, from above); the hoard lacks 163's rock slab; paler coins.",
                         "m3d_rocketOfferScene.png"),
    "skyJumpIslandFar2": ("B", "missing-3d", "069's upper-right purple-chest island, 144 x 132 at (213, 214).",
                          "Paler and seen from higher; fewer coin stacks round the chest; the pad is pinker than 069's magenta.",
                          "m3d_skyJumpIslandFar2.png"),
    "iconSkyDrum": ("B", "missing-3d", "The Profile drum: pink cushion, cream rings, gold belt + plate, purple foot, cyan glow.",
                    "near A: our body is taller and the plate smaller than meta-002's.", "m3d_iconSkyDrum.png"),
    "planetStage1": ("B", "missing-3d + director", "director: coloured by LATITUDE bands read off 163 (magenta streaks, a broad "
                     "white-mint belt, purple below) instead of thin sine lines; less glass haze.",
                     "Paler and less contrasted than 163's marble.", "director3/planets_163.png"),
    "planetStage2": ("B", "missing-3d + director", "director: latitude bands (cream / pink-red), darker below.",
                     "163's red bands are deeper and more streaked.", "director3/planets_163.png"),
    "planetStage3": ("B", "missing-3d + director", "director: latitude bands with navy streaks; a fatter, brighter cyan ring.",
                     "163's ring glows at its ends; the planet is a little more cyan.", "director3/planets_163.png"),
    "fxFrostVignette": ("B", "missing-3d", "One full-screen frost overlay (streaky cyan edge ice, translucent white haze, cracks, "
                        "sparkles), clear middle; between the board and the HUD.",
                        "near A: 065's side ice is a little more saturated and its corner cracks denser.",
                        "m3d_fxFrostVignette.png"),
    # ------------------------------------------------------------------ characters lane (new)
    "workerCrowdLeft": ("B", "characters", "The loading screen's left group (P1): a clipboard worker at the edge + two back-view "
                        "workers, defocused.", "The two back-view workers stand on nothing: store 8's conveyor platform "
                        "(scene lane, loadingBackdrop) is unbuilt.", "characters/crowdL1.png"),
}


def r2_gap(i, g):
    """The remaining gap round 2's table showed for an entry round 3 did not touch."""
    if g["grade"] == NS:
        return "not shipped"
    if g.get("changed"):
        return "none visible at game size" if g["grade"] == "A" else g["changed"].split(". ")[-1]
    if i in B1:
        return B1[i].get("fix") or B1[i].get("note", "")
    if i in A1:
        return A1[i].get("note", "")
    return ""


def main():
    out = {"grader": "art director round 3", "date": "2026-09-25", "scale": R2["scale"],
           "before": "art/review/grades-director-r2.json (round 2)", "entries": {}}
    for i, g in R2["entries"].items():
        if i in R3:
            gr, who, what, gap, sheet = R3[i]
            out["entries"][i] = dict(grade=gr, before=g["grade"], grader=who, changed=what, gap=gap, sheet=sheet)
        else:
            out["entries"][i] = dict(grade=g["grade"], before=g["grade"], grader=g.get("grader", ""), changed="",
                                     gap=r2_gap(i, g), sheet=g.get("sheet", ""))
    for i, (gr, who, what, gap, sheet) in NEW.items():
        out["entries"][i] = dict(grade=gr, before="new", grader=who, changed=what, gap=gap, sheet=sheet)
    missing = sorted(set(R3) - set(R2["entries"]))
    if missing:
        raise SystemExit(f"R3 names ids round 2 did not grade: {missing}")
    out["composed"] = dict(R2.get("composed", {}))
    out["composed"]["loadingProof"] = dict(
        grade="B", before="B", sheet="characters/p_loading_r2_r3_s8_1x.png, director3/logo_049.png",
        changed="Round 3: the cast re-posed against store 8 (scientist's ball fist and side-held arrows, the carrier turned "
                "with chunky legs, the right crowd at store 8's spots, a new left group) and a cleaner logo. Visibly closer "
                "at game size.",
        gap="The loadingBackdrop's conveyor + press are still unbuilt (the left group stands on nothing) and its contact "
            "shadows were baked for the old layout (scene lane).")
    out["composed"]["popupChromePrototype"] = dict(
        grade="A", before="B", sheet="polish/popup_pause_gamesize.png, polish/popup.png",
        changed="The polish lane's SwiftUI prototype of the popup chrome (panel frame, ribbon, close X, Resume/Quit) rendered "
                "next to the shell's chrome over 007: at game size it reads as 007.",
        gap="A PROPOSAL: the app still draws the old chrome, so buttonGreen / buttonRed / panelFrame / panelRibbon / "
            "panelClose stay B in the manifest until the shell applies art/lanes/polish.md section B.")
    E = out["entries"]
    counted = [e["grade"] for e in E.values() if e["grade"] in ("A", "B", "C")]
    out["counts"] = {g: counted.count(g) for g in ("A", "B", "C")}
    out["counts"]["n/a"] = sum(1 for e in E.values() if e["grade"] == NS)
    out["counts"]["share_A"] = round(counted.count("A") / len(counted), 3)
    json.dump(out, open(os.path.join(APP, "art/review/grades-director.json"), "w"), indent=1)
    print(out["counts"], len(E), "entries")


if __name__ == "__main__":
    main()
