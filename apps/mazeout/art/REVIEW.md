# Arrow Out — art review, round 3 (art director)

2026-09-25 (afternoon). These are the grades that count after round 3. Round 2's grades are the "was" column and are kept
in `art/review/grades-director-r2.json`. Machine-readable twin of this file: `art/review/grades-director.json` (grade,
was, grader, what changed, remaining gap, sheet per id). The grades are also written into `art/MANIFEST.json` (`grade`
on every graded entry; A/B entries with an output have status `graded`).

**Scale** (unchanged): **A** = ship — a player takes it for the same art at game size. **B** = the same art, and the
differences show only on inspection or side by side. **C** = redo. **n/a** = not shipped, so it isn't counted. "near A"
in a note = one small pass away.

## Grade distribution

| | A | B | C | n/a | share A |
|---|---|---|---|---|---|
| round 1 (graders A + B, 155 ids) | 44 | 69 | 34 | 8 | 30 % |
| round 2 (director, 160 ids) | 50 | 95 | 1 | 14 | 34 % |
| **round 3 (director, 189 ids = 160 + 29 new)** | **72** | **101** | **1** | **15** | **41 %** |

Round 3 by lane (the ids each lane touched; the director's re-grades):

| lane | ids | A | B | n/a | the lane's self-grade vs mine |
|---|---|---|---|---|---|
| polish | 15 | 14 | 1 | 0 | agreed on all 14 A. `logoArrowOut` B+ → still B after my fix (below). |
| missing-svg | 15 | 9 | 5 | 1 | +6 A: `heartBig` (after my fix), `iconSkull` (after my fix), `heartGlossySmall`, `heartLivesBig`, `shopSeal`, `pageBgPattern` read the same at game size. `frostCracks` not shipped (ruling 2). |
| missing-3d | 13 | 0 | 13 | 0 | the B- ids (`bundleChest`, `bundleCart`, planets) are B after my fixes. `weeklyContestLogo` is not graded as art: it is now a SwiftUI entry (ruling 3). |
| characters | 6 | 0 | 6 | 0 | the lane's two A- (`scientistLoading`, `workerCarrier`) stay **B**: side by side with store 8 at 1x the mouths are still bigger and deeper than store 8's grins. Visibly closer than round 2. |

Composed screens: **home A** (unchanged), **loading B** (closer: the cast re-posed, a new left group, a cleaner logo),
**popup chrome prototype A** (the polish lane's SwiftUI proposal over 007 — the app does not draw it yet).

- **P0 C count: one, and it is still not art.** `settingsRoundToggle` stays C only because the app's Settings screen is
  still a Paused-style popup. Every glyph the phone's full-screen Settings page needs now exists, including the OFF rod
  (`glyphOffSlash`, new). Rebuilding the screen is the shell's job. No art id the P0 game shows is C.
- **Target ≥ 50 % A: missed (41 %).** +22 A this round: 13 B → A (the polish lane's HUD, unlock icons, rays, rank badges)
  and 9 new ids at A. The 101 B are real B: I did not raise a grade I could not see on a sheet. 15 more A reach 50 %;
  the cheapest are listed under "Round 4".

## Rulings (the lanes asked for them)

1. **`heartBig` ships as the SVG** (missing-svg), not the 3D candidate (`build/ui-art/route3d/heartBig.png`, which stays
   a compare-only file). Next to meta-088 the 3D heart's silhouette is fatter and its notch shallow; the SVG's silhouette
   is IoU 0.986. The overwrite race between the two lanes is closed: `m3d_fx.py` sends its heart only to route3d, and the
   file in `art/ui/out` is the SVG (rebuilt by me, see fix 3). **Shell:** `OutOfTimePopup` still draws a code heart
   (`OutOfTimePopup.swift` ~l.103); use `UIArt.heartBig` at (99.5, 316) 194 × 164 pt; the red glow stays code.
2. **Frost = `fxFrostVignette` alone.** One full-screen overlay (`.resizable`, fill, between the board and the HUD) that
   already paints the cracks. `frostCracks` is marked not shipped (`confirmed: false`, n/a): drawing both doubles the
   cracks. SPEC-ui 2.3.3 / 4.2 said code gradient + crack tile; the raster reads closer to 065.
3. **The Weekly Contest lettering is the SwiftUI `EventLogo` with live text** (route B1), as SPEC-ui 2.15.3 / 4.2 say,
   like the other four event logos (`streakRaceLogo`, `clawLogo`, `skyJumpLogo`, `rocketRaceLogo`), and because PIPELINE's
   rule is never to bake translatable text. The lane's two renders are good (I'd grade them B+ as art) and are kept as the
   **look target** the component must match: `art/ui/code/targets/weeklyContestLogo@3x.png` and `…TR@3x.png` (committed,
   never bundled: `tools/sync_art.sh` copies only `art/ui/out` and `art/out`). `m3d_make.py` now builds them there
   (`DEST "target"`). In the manifest, `weeklyContestLogo` and `weeklyContestLogoTR` are `swiftui / B1 / todo / shell`
   with `preview` = their render; the layer recipe to port is `m3d_events.build_weekly_logo`. Frame 277 × 54 at
   (60.1, 193.5) (54, not 50: the "y" descender + outline + extrusion).
4. **Bundle ids = what the phone draws:** Mini `bundleBag`, Epic `bundleBarrel`, Elite `bundleChest`, Mega `bundleSafe`,
   Legendary `bundleCart`, Special Offer `bundleSpecial`. SPEC-ui 4.2's `bundleChestRed` / `bundleChestPurple` do not
   exist. One 176 × 102 frame for every card at (16, card top + 7.7); Special at (16, 200). Amounts stay live text.

## The director's fixes, worst first

1. **Shop bundle heaps read as noodles** (`bundleChest`, `bundleCart` B- → B; `bundleSafe`, `bundleBarrel` B). The
   heaps packed unit coins at 0.47 of a diameter, so every coin hid half of its neighbours and showed only a crescent: at
   game size the Elite / Mega / Legendary heaps were a tangle of gold rings next to meta-008 … meta-010's big star-faced
   coins. New `m3d_shop.big_heap / big_stack / big_upright`: the same mounds with the coin 1.4-1.6× bigger at 0.64
   spacing, brighter heap cores (#F4A812), stacks re-spaced; the cart's load is one taller pyramid plus its spill; the
   safe renders without cast shadows (its wall threw a hard diagonal wedge across the coins). Coins in the barrel's hole
   stay at scale 1 (bigger ones cut through the staves). Evidence: `director3/shop_bundles.png`.
2. **Stage planets were thin lines on flat colour** (`planetStage1..3` B- → B). New `m3d_events._lat_planet`: colour by
   latitude bands read off 163 (Stage 1 magenta streaks + a broad white-mint belt, Stage 2 cream / pink-red, Stage 3 sky
   blue with navy streaks), warped by noise; the glass haze halved (it washed them pastel); Stage 3's ring fatter and
   brighter. Evidence: `director3/planets_163.png`.
3. **`heartBig` (B → A).** The speculars' radial gradients were rotated twice (the ellipse's transform already rotates
   its user space), so the left lobe had hard ellipse edges and the right lobe a white parallelogram. Fixed, plus: the
   dark lip ellipses at the notch (a smudge, and the notch read ~10 pt deep) removed, the top band 0.75 → 0.35, 088's soft
   right-lobe streak and shoulder crescent. Evidence: `director3/heart_088.png`.
4. **`logoArrowOut` letters melted together** (stays B, near A). At `sx` 0.80 the five inked letters were 63 design px
   wider than their span *before* the 34 px inflation, so neighbours overlapped ~95 px: ARROW read as one blob next to
   049's four separate blocks. Now a compression per letter (0.75 0.77 0.77 0.73 0.60 — the wide W most), span
   222–1828, inflation 32, baseline 25 px higher and extrusion 50 (the undersides stay on the blue face), OUT! at cap 312
   with a purple margin. `_word` accepts a per-letter `sx`; nothing else calls it. Evidence: `director3/logo_049.png`.
   **Shell:** `WinLogoSequence` letter cuts are now `[0, 0.2470, 0.3950, 0.5545, 0.7370, 1] × W` (measured on this
   render's letter gaps; they supersede polish.md §A.8's).
5. **Skulls** (`iconSkull` B+ → A, `iconSkullBones` stays B): the cranium is a dome (an ellipse), not a rounded box — at
   6× next to 037 / 063 it read square; the crossbones are fatter (shaft 4.0 pt, knobs 2.85 pt). Evidence:
   `director3/skulls.png`.

After these fixes the full `art_batch.py --svg` run reproduced every svg output byte-identical to the files on disk
(checksums over `art/ui/out` + `art/out`), so my generator edits changed only the ids above.

## How it was judged

At **game size** first (3 px per pt, the capture's scale), side by side and in place over the capture at the frame the
shell draws; 2× only to name a difference already visible at 1×. Proofs regenerate into `art/ui/sheets/` (gitignored):

```sh
PY=~/.venvs/mf3d/bin/python                                   # from apps/mazeout
$PY art/tools/manifest_sheets.py <ids>                        # m_<id>.png: ref | ours | in place | alpha (every id)
$PY art/ui/recipes/m3d_proofs.py <ids>                        # m3d_<id>.png (missing-3d ids, in the composed card)
$PY art/review/tools/polish_proofs.py all                     # polish/*.png (HUD at the shell's rects, unlock, logo …)
$PY art/review/tools/director_proofs_r3.py                    # director3/: heart_088, skulls, logo_049, planets_163, shop_bundles
python3 art/review/tools/director_grades_r3.py                # -> art/review/grades-director.json (round 3)
python3 art/review/tools/director_merge.py                    # every lane -> MANIFEST.json + ID-MAP.md (re-runnable)
python3 art/review/tools/director_review.py                   # the per-entry table below
$PY art/tools/manifest_check.py --quiet --strict              # 239 entries, 0 failing, no strays
$PY art/tools/art_batch.py --svg                              # all svg entries rebuilt + verified
$PY art/ui/recipes/m3d_make.py build <ids>                    # the missing-3d ids (art_batch --3d cannot: BUILDS, not ASSETS)
```

The characters were judged on the characters lane's sheets (`characters/p_loading_r2_r3_s8_1x.png` at game size,
`final_sci.png`, `carrier8.png`, `crowd4.png`, `crowdL1.png`, `idle_*.png`); nothing there was re-rendered by me.

## Merge

`director_merge.py` merges into `art/MANIFEST.json` in this order (later wins), then regenerates `art/ID-MAP.md`:

| step | lane file | entries differing | new ids |
|---|---|---|---|
| 1 | `characters.entries.json` (round 3 content) | 28 | 1: workerCrowdLeft (+ the 4 round-2 ones) |
| 2-5 | `3d-hud`, `3d-events`, `scene`, `svg` (round 1-2, unchanged) | 21 / 16 / 16 / 38 | 0 |
| 6 | `director.entries.json` (round 2; grades from `grades-director-r2.json`) | 161 | 5 (round 2's) |
| 7 | **`missing-svg.entries.json`** | 15 | 15 |
| 8 | **`missing-3d.entries.json`** | 15 | 15 |
| 9 | **`polish.entries.json`** (after director: director still holds the round-2 sizes of the ids polish resized) | 16 | 0 |
| 10 | **`director-r3.entries.json`** (new: rulings, fix notes, every round-3 grade + status) | 46 | 0 |

- Result: **239 entries; `manifest_check.py --quiet --strict`: 0 failing, no stray files.** `art_batch.py --svg`: every
  svg entry rebuilt and verified. The 15 missing-3d outputs were rebuilt / verified by `m3d_make.py` + the checker (the
  7 I changed) or verified by the checker as the lane left them.
- `manifest_check.py --lanes` now merges the lane files in the director's order, not alphabetically. Alphabetical order
  put round 1's `svg` lane after `polish` and reverted polish's sizes, which is where the lanes' "other lanes' failures"
  came from. With the order fixed, `--lanes` is also 0 failing.
- `art/ui/CASES.txt` was regenerated.

## For other owners (not art; nothing in App/ was edited)

**Shell**
- `tools/uiart_gen.py --check` is stale: run `python3 tools/uiart_gen.py` (29 new raster ids, 15 resized). The
  `weeklyContestLogo*` ids are SwiftUI now, so they have no UIArt case.
- Rulings 1-4 above: `UIArt.heartBig` on Out of Lives; `fxFrostVignette` alone for the freeze; the Weekly `EventLogo`
  (live text, match `art/ui/code/targets/`); the bundle ids.
- Polish lane handoffs, all still open: `S2Chrome.swift ArtInk.boxes` (15 rows), the HUD / Claw / unlock rects and text
  anchors, and the popup chrome numbers (`art/lanes/polish.md` §A-§B). Re-grade `buttonGreen` / `buttonRed` /
  `panelFrame` / `panelRibbon` / `panelClose` once the app draws §B (the prototype is A at game size; the manifest keeps
  B until the app renders it).
- The logo cuts in fix 4.
- Placements and live-text anchors of the new ids: `art/lanes/missing-svg.md` ("Entries", "Live text anchors") and
  `art/lanes/missing-3d.md` ("The ids vs SPEC-ui §4.2").
- Loading: bundle `char_workerCrowdLeft@3x.png` and the left worker's two new rig layers (`eyes_wink`, `armL_wave`);
  `char_loading_layout.json` has the new frames. The §8.2 wave track fix (use `armL_wave`) is in
  `art/lanes/characters.md` round 3.

**Scene lane**
- `loadingBackdrop`: re-bake the contact shadows from the new `char_loading_layout.json`, and build the conveyor + press
  that `workerCrowdLeft`'s two back-view workers should stand on.

**Pipeline keeper**
- `art_batch.py --3d` cannot rebuild BUILDS-style modules (`m3d_*`, the scene lane): use `m3d_make.py` until it can.
- `scene_kit`'s mesh cache does not see edits to `m3d_kit.py` (delete `build/ui-art/scene/usdz/m3d_*/*.hash`).
- The toon material in `3d-hud_props.tpart` has the uv-wrap dark spot the missing-3d lane fixed only in `m3d_kit.painted`.

## Per entry (grade after round 3)

"Was" is round 2's grade (`new` = first graded now). "What changed" is round 3's change (blank = not touched this
round); "remaining gap" is what still differs.

<!-- BEGIN TABLE -->

### board

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `boardArrow` | **A** | A | - | Device grab of L32 (build/device/grab-L032-fit.png) next to 003: stroke 11-12 px vs 12 px, round caps and joins, head size and position all identical at game size. |
| `boardTrailStar` | **A** | A | - | White 5-point star tinted at runtime. Tinted with the trail hues next to store 1's trail stars, it reads the same. |
| `boardVacatedDot` | **B** | B | - | Only seen in the 1x JPEG soak frames (build/device/frames/waves-mid). The pale-blue dots sit on the lattice, and their colour (206, 224, 245) is within JPEG error of #C5E1FF. There is no lossless in-app frame to confirm the size. |
| `boxRing` | **B** | B | - | The lugs are a touch longer and whiter than 135's. |
| `boxSlab` | **A** | A | - | none visible at game size |
| `curtainCrate` | **n/a** | n/a | - | not shipped |
| `doorShards` | **B** | B | - | Six shards in the door palette (orange / blue / purple). Fine as FX particles; not compared frame by frame with the L33 burst clip. |
| `doorW11H10` | **A** | A | - | In place on L37 (052) it covers the original door exactly (frame, rivets, slat count per row). The 22-wide door's top chamfer reads the same. |
| `doorW13H4` | **A** | A | - | In place on L34 (036) it covers the original door exactly (frame, rivets, slat count per row). The 22-wide door's top chamfer reads the same. |
| `doorW22H10` | **A** | A | - | In place on L37 (052) it covers the original door exactly (frame, rivets, slat count per row). The 22-wide door's top chamfer reads the same. |
| `doorW4H12` | **A** | A | - | The L33 staircase recomposed from our 5 doors + 5 hex locks + the key covers 027 exactly: orange frame, gold rivets, purple inner frame, one slat per row, shadow. Identical at game size. |
| `doorW4H16` | **A** | A | - | The L33 staircase recomposed from our 5 doors + 5 hex locks + the key covers 027 exactly: orange frame, gold rivets, purple inner frame, one slat per row, shadow. Identical at game size. |
| `doorW4H20` | **A** | A | - | The L33 staircase recomposed from our 5 doors + 5 hex locks + the key covers 027 exactly: orange frame, gold rivets, purple inner frame, one slat per row, shadow. Identical at game size. |
| `doorW4H4` | **A** | A | - | The L33 staircase recomposed from our 5 doors + 5 hex locks + the key covers 027 exactly: orange frame, gold rivets, purple inner frame, one slat per row, shadow. Identical at game size. |
| `doorW4H8` | **A** | A | - | The L33 staircase recomposed from our 5 doors + 5 hex locks + the key covers 027 exactly: orange frame, gold rivets, purple inner frame, one slat per row, shadow. Identical at game size. |
| `doorW5H17` | **A** | A | - | Same generator as the L33 doors, checked in place on L34 (036). Identical at game size. |
| `keyOnArrow` | **A** | A | - | In place on L33 (027) the key covers the original: purple ribbon loop, gold ring and bit, at the right anchor on the arrow. |
| `lockHex` | **A** | A | - | 5 locks placed by the rule (door centre + 0.18 pitch) land on the capture's locks on L33; bevel facets, keyhole and blue socket read identical. |
| `pipeCounter` | **A** | A | - | In place on L35 (042): gold collars, orange counter box and the live digit read identical at game size. |
| `pipeMouth` | **A** | A | - | In place on L35 (042) the gold collar at the tube's end covers the original exactly. |
| `pipeShards` | **B** | B | - | Cyan glass shards in the tube palette. At game size they are specks, as in the break clip; no frame-by-frame check. |
| `tapeH2` | **A** | A | - | In place on L38 (056) it covers the 2-lane tape exactly; straps at the steeper angle as in the capture. |
| `tapeH3` | **A** | A | - | Same recipe as the verified tapes (no 3-lane horizontal band on the phone yet, so judged next to L32's 4-lane look, not in place). Reads as the same tape. |
| `tapeH4` | **A** | A | - | Pasted over L32 (003) at the lattice anchor it covers the original tape exactly: same band, the two crossing straps, pink tones and shadow. Identical at game size. |
| `tapeV2` | **A** | A | - | Same recipe; the ref is the older video skin (blue arrows), so there is no in-place phone check. Reads as the phone tape at game size. |
| `tapeV3` | **A** | A | - | In place on L44 (090) it covers the 3-lane tape exactly. |
| `tapeV4` | **A** | A | - | Pasted over L32 (003) at the lattice anchor it covers the original tape exactly: same band, the two crossing straps, pink tones and shadow. Identical at game size. |

### hud

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `heartHUD` | **A** | A | - | Three hearts in place on 003 at the measured slots read identical (lobes, tip, specular, dark rim). |
| `heartHUDLost` | **A** | A | - | In place on 110 (after a bump), the flat #6C94DC slot heart with a darker edge is indistinguishable from the capture. |
| `hudPauseButton` | **A** | A | - | SwiftUI render (build/ui-art/swiftui/pauseButton.png) in place on 003: IoU 0.927, dE00 3.9. The glossy squircle, rim and glyph read identical in the HUD row. |
| `iconCoin` | **A** | B | Re-measured on 002's home coin: darker thick outline, a 6 pt thickness band, the recess's shaded top wall, a chubby star with an extruded side, no white glints; frame 39 pt (home draws it 1:1). | Judged on home (002) and 003's HUD crop, not yet in an app render of the HUD (~0.68x). |
| `iconPlusGreen` | **A** | A | Frame 24 pt (the 23.5 pt rect draws it 1:1), vivid flat green, top light ring, short chunky cream plus. | none visible at game size |
| `iconStopwatch` | **A** | A | - | In place on 003 at 1.02x it reads the same. Ring tones match (sampled 252,187,7 / 233,136,4 vs the capture's 253,174,6 / 233,132,0). |
| `iconStopwatchFrozen` | **B** | new | iconStopwatch's drawing at 1.02x under a snow cap with icicles, frame 34 x 50 (the icicles hang to y 120). | near A: the capture's cap is lumpier and a touch smaller, its icicle clump longer. |
| `iconStopwatchSmall` | **A** | B | Frame 26 x 28 (204's chip watch is 22.7 x 26 pt of ink; the old 18 pt frame drew it at 0.7x): dome crown, warmer ring, long tick pills, fat wedge hand. | The hand angle is fixed (the original's turns). |

### boosters

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `boosterDome` | **n/a** | n/a | - | not shipped |
| `boosterFreeze` | **B** | B | - | Fatter snow caps (optional). |
| `boosterHint` | **B** | B | - | Pale-blue glass tint + a filament inside. |
| `boosterPointer` | **n/a** | n/a | - | not shipped |

### popups

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `buttonGreen` | **B** | B | - | SwiftUI PanelButton in the Paused panel: same glossy green pill and size. Next to 007 the top glare line is heavier, the dark outline runs all round, and the face is a little more saturated. In the app render ... |
| `buttonPurple` | **A** | A | - | The Super Hard Play face matches 060's purple. |
| `buttonRed` | **B** | B | - | Same notes as buttonGreen (in-place dE00 5.1); reads as the same Quit button at game size. |
| `coinStackReward` | **B** | B | - | Coins ~1.1x. |
| `glyphHaptic` | **B** | B | - | Zig-zags still a little short. |
| `glyphSound` | **A** | A | - | In the Paused panel (007) at its 1:1 frame, the cream speaker with the dark-brown outline and two waves is indistinguishable at game size. |
| `heartBig` | **A** | new | missing-svg: the fitted two-ellipse heart (IoU 0.986 on 088). director: the speculars' gradients were rotated twice (hard ellipse edges, a white parallelogram on the right lobe); the dark lip smudges at the notch are gone; the top band is lighter; the ... | The notch reads a hair sharper than 088's (2x only). |
| `heartBroken` | **B** | B | - | Taller, rounder lobes (~+6 %). |
| `heartGlossySmall` | **A** | new | The More Lives '+1 Live' button heart (had no id), the heartLivesBig style at 46 x 40. | The capture's specular is a touch larger (2x only). |
| `heartInfinite` | **A** | A | - | Same at game size; the tip is marginally sharper. |
| `heartInfiniteSmall` | **A** | B | Heart 42 x 36.4 (was 45 x 39); a rounder, thinner-edged cream infinity. | none visible at game size |
| `heartLivesBig` | **A** | new | The popup lives heart (meta-095), fitted box 92.5 x 79.4 in 100 x 90, orange specular. | The specular is a touch small (2x only). |
| `iconVideoAd` | **A** | new | The clapper with the play triangle punched as a HOLE. | none visible at game size |
| `infoPathIcon` | **B** | B | - | Same white tile, blue border, 3D lower edge and arrow grammar as 025's info icon; the path layout is ours by design. |
| `panelClose` | **B** | B | - | The red X disc is the same size as 007's (37.7 vs 39 pt). Its navy/blue outer ring is thinner than 007's. |
| `panelCream` | **A** | A | - | The cream inset card with its warm border matches 007. |
| `panelFrame` | **B** | B | - | The Paused panel in the app render matches 007's size and rivets. The outer bumper is a uniform light-cyan ring, where 007 has lighter cyan corner bumpers with darker straight bars between them. |
| `panelRibbon` | **B** | B | - | The 'Paused' yellow plate is the same size (x 61.7-332.3 vs 64.7-329.0 pt). Its lower edge is less arched and its bottom rim lighter than 007's. |
| `pointerArrowDown` | **A** | new | The Weekly tutorial's straight block arrow (130), a new drawing. | none visible at game size |
| `pointerArrowYellow` | **B** | B | - | The curved yellow pointer with an orange outline reads as 025's. The head is slightly narrower. (The dark edge beside it in the proof is the erase, not the asset.) |
| `stopwatchBig` | **A** | A | - | Same prop at 225 pt. The ticks are rounder pills than the capture's flat bars; that shows only at 2x. |
| `toggleOnOff` | **B** | B | - | The green ON pill with the blue knob reads the same. 007's track has a light border ring; ours is darker/greyer, and the knob is a bit taller. |
| `tutorialHand` | **B** | B | - | The fist is still ~14 % wider. |
| `unlockIconBox` | **A** | B | Its own card illustration (no longer the board sprites): pillow slab, sphere in a dark crease, four stubby lugs in front of the rim, tube-like purple ring, 41 pt navy well. | The lug caps are a touch flatter than 134's (2x only). |
| `unlockIconCurtain` | **n/a** | n/a | - | not shipped |
| `unlockIconDoor` | **A** | B | V1 t 185 s: a SQUARE 5 x 5-cell card door, lock at the door's pitch; frame 128 x 128. | Unconfirmed on the phone (no v552 door card). |
| `unlockIconElevator` | **A** | B | V2 t 1182.5 s at 1:1 in 164 x 112: icy blue-grey panels, soft outline, faint wide stripes, flat windows. | Unconfirmed on the phone (video-only obstacle). |
| `unlockIconLinked` | **A** | B | V1 t 78 s at 1:1 in a 150 x 106 frame (round 2 was 0.8x): 15.4 pt shafts, rounded heads, the board tape. | The V1 skin is the older build's (no phone card). |
| `unlockIconPipe` | **A** | A | - | In the Pipe! card (040) at 1:1 with a live '3': the gold collars, orange counter and U tube read identical. The tube's light band is a hair stripier. |

### fx

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `frostCracks` | **n/a** | new | A 120 pt corner crack tile for SPEC-ui's code-vignette route. | not shipped: fxFrostVignette ships alone (it already paints the cracks) |
| `fxFrostVignette` | **B** | new | One full-screen frost overlay (streaky cyan edge ice, translucent white haze, cracks, sparkles), clear middle; between the board and the HUD. | near A: 065's side ice is a little more saturated and its corner cracks denser. |
| `heartHUDHalves` | **B** | B | - | The HUD heart with a zig-zag crack, halves 2.4 px apart. Same heart family as heartHUD; one sprite for both halves (FX must mask by gen_icons.CRACK). |
| `sparkleTwinkle` | **B** | B | - | 4-point white star with a warm glow. The unlock-card sparkles on 040/134 are warmer (cream-yellow) and slightly bigger. Tint it warm at runtime. |

### home

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `eventBadgeRocket` | **B** | B | - | Narrower, taller body; fins down onto the drum. |
| `eventBadgeSkyJump` | **B** | B | - | Pad ~1.25x; wider, lower clouds. |
| `eventBadgeStreak` | **B** | B | - | Flags ~1.3x with bigger checks and folds. |
| `glyphGear` | **A** | A | - | In place on 026 at 1:1, the white gear with the light-blue side reads the same; the teeth are marginally narrower. |
| `heartLives` | **A** | B | Frame 42 x 40 = the shell's rect at 1:1; HEART2 at 002's 39.7 x 33.7; deeper crimson, dark top band, softer darker outline. | none visible at game size |
| `homeArrowPileFull` | **A** | A | - | none visible at game size |
| `homeArrowPileHalf` | **B** | B | - | 168's heap is a taller centre column. |
| `homeArrowPileLow` | **B** | B | - | 070's arrows cluster more. |
| `homeBackdrop` | **B** | B | - | Lift the tank glow; add 2-3 soft vertical highlight bands. |
| `homeCapsuleMachine` | **B** | B | - | The glass sheen is still painted. |
| `homeConsole` | **B** | B | - | Sits ~4 pt higher than 002; the belly's warm yellow is paler. |
| `homeLevelPlate` | **A** | A | - | The green 'LEVEL / 33' plate in the machine recess matches 026, and the red (L34) and purple (L39) plates match 035/060. |
| `homePlatform` | **B** | B | - | Right size and placement. Our dais rim is a crisp bright ring; 002's is glassier, with a soft reflection of the wall. |
| `homePlayButton` | **A** | A | - | Green Play, red 'Hard Level' and purple 'Super Hard' variants in the blue frame match 026/035/060 at game size: glare, ribbon tab and label. |
| `homeTopBar` | **A** | A | - | App render (build/s1/home-L33-normal.png) next to 002/026: the avatar frame, coin pill + icon + plus, lives pill + heart + 'Full', and gear button read identical in size, position and colour. |
| `iconHexArrow` | **A** | B | Frame 40 x 40, ink 37.3 x 35 at 1:1 (was ~1.15x); thick pale 3D side, sky-blue arrow with a dark-purple edge. | The chain hook belongs to the bar (shell). |
| `navBar` | **A** | A | - | The bar gradient and the raised cyan Home tab match 026 (the Home icon's size is grader B's navHome). |
| `navHome` | **B** | B | - | The eaves sit a little low. |
| `navShop` | **B** | B | - | Dark rounded-rect slot cut-outs. |
| `navTrophy` | **B** | B | - | Fuller handles, single foot slab. |

### characters

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `scientist` | **A** | A | - | Composed on 002 at game size, it reads as the same character recoloured pink: same pose, size, eye line, coat, badge and pen. Minor: the crown tuft is a thin side wisp (002: a centred spiky tuft). The hands are big fur mitts on ... |
| `scientistLoading` | **B** | B | New 'load' pose: squat wide torso, the fist a clenched BALL beside the mouth, arrows held at his side, fuller dome, raised brows, crescent smile, lighter fur, camera from a little above. | near A: the mouth opens rounder and deeper than store 8's grin (visible at game size side by side); no lapel; the held arrows are thinner than store 8's chunky ones. |
| `workerCarrier` | **B** | B | Full bean turned left, arms near-vertical to the box, short chunky legs with shoe feet, tall laughing D, box seen from a little above; eye whites within ~2 pt of store 8. | near A: the mouth fills more of the face than store 8's; the legs are the body colour and blobby (store 8: separate legs with shoes under purple pants). |
| `workerClawPair` | **B** | B | - | Both workers read on 023 at the right size and placement. The arms are thin and both wear the same buck-tooth grin (023: a laughing left worker with a big fist). Not yet composited into clawHeaderArt. |
| `workerClipboard` | **B** | B | - | Clipboard still shows the paper side. |
| `workerCrowdLeft` | **B** | new | The loading screen's left group (P1): a clipboard worker at the edge + two back-view workers, defocused. | The two back-view workers stand on nothing: store 8's conveyor platform (scene lane, loadingBackdrop) is unbuilt. |
| `workerFist` | **B** | B | ~20 % bigger, rounder bean, bigger glasses, fist on a thick arm, spiral notebook, wide grin, chunky legs. | The flexed arm is smaller; the fist sits partly behind the carrier's box; no cap tabs. |
| `workerFlyer` | **B** | B | - | Block-arrow red (the arrowGlossy family). |
| `workerRacers` | **B** | B | - | The chute is still a flat ribbon and the checkered banner is missing. |
| `workerRunners` | **B** | B | The right crowd at store 8's sizes and spots (top-hat worker, waver, burger eater), chunky running legs, lighter haze (1.1 px / 12 %). | The burger eater's mouth is hidden behind the burger (store 8: gaping around it). |
| `workerWalkie` | **B** | B | Rig gained eyes_wink + armL_wave (existing layers re-exported pixel-identical). | Arms still thinner than theirs; the wave/wink need ui.json tracks (shell). |

### loading-win

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `arrowGlossyBlue` | **B** | B | - | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. |
| `arrowGlossyCyan` | **B** | B | - | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. The manifest ref points at store 8's red-orange loading arrow; judged against 026's cyan. |
| `arrowGlossyGreen` | **B** | B | - | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. The green leans lime. |
| `arrowGlossyOrange` | **B** | B | - | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. |
| `arrowGlossyPurple` | **B** | B | - | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. The purple leans magenta against 026's lilac. |
| `arrowGlossyRed` | **B** | B | - | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. The loading screen's red arrow is more orange-red. |
| `arrowGlossyYellow` | **B** | B | - | A chunky block arrow in the capsule-pile family (soft bevel, visible lower wall, saturated face); reads right at 40-60 pt. |
| `iconSkull` | **A** | new | Hard win-tag skull (037), eye sockets are holes; director: the cranium is a dome (an ellipse), not a rounded box. | none visible at game size |
| `iconSkullBones` | **B** | new | Super Hard skull over crossbones (063); director: dome cranium, fatter bones and knobs. | The bone shafts show a little longer between knob and skull than 063's. |
| `loadingBackdrop` | **B** | B | - | The left press is still flat panels (no conveyor). |
| `logoArrowOut` | **B** | B | polish: solid graded extrusion + inner-bevel filter, fatter letters. director: the five letters were 63 design px wider than their span BEFORE the 34 px inflation, so they melted into one blob; now a compression per letter (W most), a wider span, inflation ... | near A: MAZE's letters are wider blocks with a crisper 3D side; ours are rounder (our OFL font, five letters in the same plate). |

### avatars

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `avatarBlue` | **n/a** | n/a | - | not shipped |
| `avatarBoxHead` | **B** | B | - | The phone's leans are stronger. |
| `avatarBurger` | **B** | B | - | The phone's leans are stronger. |
| `avatarCap` | **n/a** | n/a | - | not shipped |
| `avatarCapGlasses` | **B** | B | - | The phone's leans are stronger. |
| `avatarDefault` | **A** | A | - | Flat grey-blue tile with the lighter silhouette, the same as the phone's placeholder (meta-003, 026) at game size. |
| `avatarDetective` | **B** | B | - | The phone's leans are stronger. |
| `avatarGreen` | **n/a** | n/a | - | not shipped |
| `avatarNotebook` | **B** | B | - | The phone's leans are stronger. |
| `avatarParty` | **B** | B | - | The phone's leans are stronger. |
| `avatarPink` | **n/a** | n/a | - | not shipped |
| `avatarPoint` | **n/a** | n/a | - | not shipped |
| `avatarRed` | **n/a** | n/a | - | not shipped |
| `avatarScientist` | **B** | B | - | Still ~0.85x of the phone's head in its tile. |
| `avatarShades` | **n/a** | n/a | - | not shipped |
| `avatarSpecs` | **n/a** | n/a | - | not shipped |
| `avatarWalkie` | **B** | B | - | The phone's leans are stronger. |

### events-streak

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `coinBowl` | **B** | B | - | The bowl is pinker than 023's crimson; the coin heap is 2-3 pt lower and lacks the tall coin on edge at the upper left. |
| `iconCheckeredFlag` | **B** | B | - | Redrawn from 016: grey pole + silver knob, a waving cloth with big glossy cream/slate 3 x 2 checks. |
| `rankBadgeBronze` | **A** | B | As gold (203 row 3 at 1:1). | none visible at game size |
| `rankBadgeGold` | **A** | B | 203 at 1:1: 37.3 x 36.3 pt badge in a 40 frame, thin dark outline, 1.7 pt side, rim band, window ring; gold from store 6. | Gold is not captured on the phone. |
| `rankBadgePlain` | **n/a** | n/a | - | not shipped |
| `rankBadgeSilver` | **A** | B | As gold (203 row 2 at 1:1). | none visible at game size |
| `scoreChip` | **B** | B | - | Caps slightly paler gold. |

### events-claw

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `clawHeaderArt` | **B** | B | - | 023's workers are bigger/closer, the box bluer. |
| `coinPileSmall` | **B** | B | - | The same glowing mound of stacks. Ours is flatter with paler coins and less orange in the crevices. |
| `iconCheck` | **B** | new | The glossy extruded Claw / Sky Jump check, 60 x 54. | The capture's extruded side is deeper and its short arm rounder. |
| `padlockGold` | **B** | B | - | Reads the same at 44 pt. Ours is more lemon than 023's orange-edged gold; the keyhole is reddish. |
| `sunburstRays` | **A** | B | Frame 190 x 86 = 023's cream reward field clipped to its r 22 corners; rays reach the edges, centred on the prize. | none visible at game size |

### events-skyjump

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `prizeSign` | **n/a** | n/a | - | not shipped |
| `skyJumpBackdrop` | **A** | A | - | Composed with our islands and pad, it reads as 069 (sky over a pink cloud sea). Cloud sculpting is softer, which is fine at game size. |
| `skyJumpIsland` | **B** | B | - | The sign stands left of the chest (069: overlapping it). |
| `skyJumpIslandFar` | **B** | B | - | Same fixes (~139 pt, stacks, haze inside the frame). |
| `skyJumpIslandFar2` | **B** | new | 069's upper-right purple-chest island, 144 x 132 at (213, 214). | Paler and seen from higher; fewer coin stacks round the chest; the pad is pinker than 069's magenta. |
| `skyJumpPad` | **A** | A | - | Matches 069's '4' pad in size, bands and glow. |
| `skyJumpPopupScene` | **B** | B | - | 065's lid is open wider over the coins. |
| `stageChestBlue` | **A** | A | - | Matches 065's stage tile at 56 x 42 pt (colour, lid, lock plate). |
| `stageChestGreen` | **A** | A | - | Matches 065's stage tile at 56 x 42 pt (colour, lid, lock plate). |
| `stageChestPink` | **A** | A | - | Matches 065's stage tile at 56 x 42 pt (colour, lid, lock plate). |

### events-rocket

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `planetStage1` | **B** | new | director: coloured by LATITUDE bands read off 163 (magenta streaks, a broad white-mint belt, purple below) instead of thin sine lines; less glass haze. | Paler and less contrasted than 163's marble. |
| `planetStage2` | **B** | new | director: latitude bands (cream / pink-red), darker below. | 163's red bands are deeper and more streaked. |
| `planetStage3` | **B** | new | director: latitude bands with navy streaks; a fatter, brighter cyan ring. | 163's ring glows at its ends; the planet is a little more cyan. |
| `rankWings1` | **B** | new | Gold diamond badge with wings (167/171), the '1' live. | near A: the wings are flatter and less notched than 167's. |
| `rocketMine` | **B** | B | - | Reads as the player's rocket. The nose is pointier, the body narrower at the band, and the flame smaller than 178's. |
| `rocketOfferScene` | **B** | new | Stars, banded planet, lilac moon, the gold/teal chest on a coin mound with a heart, pink cloud bank (330 x 504 full bleed). | The chest is seen straight on (163: turned, from above); the hoard lacks 163's rock slab; paler coins. |
| `rocketOther` | **B** | B | - | White body to the fins. |
| `rocketRaceBackdrop` | **B** | B | - | The chest is still an upright blue barrel; 167's is a gold-banded chest seen from above. |

### leaderboard

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `leaderboardPodium` | **A** | A | - | Blocks, colours, caps and hex sockets match meta-013 at game size. |
| `trophyCup` | **B** | B | - | The handles are thinner loops than meta-017's full ears, and the stand is shorter. |

### profile-shop-settings

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `bundleBag` | **B** | new | Crimson sack with a twisted rope and knot on a lavender base, stacks either side. | The rope ends hang straighter and longer; the rolled rim is thinner. |
| `bundleBarrel` | **B** | new | Crimson stave barrel, lavender hoop, broken hole, spill; director: the spill coins 1.4x at 0.64 spacing and the top heap 1.2x (the scale-1 heaps read as rings). | The phone's barrel is squatter with fatter staves; its hole shows coins pouring out. |
| `bundleCart` | **B** | new | Crimson cart, lavender posts and wheels; director: heap coins 1.6x at 0.64 spacing (the scale-1 heap was a tangle of crescents), one taller load + a spill, stacks re-spaced. | The phone's cart is bigger in the card and its heap one continuous pyramid. |
| `bundleChest` | **B** | new | Red chest, lavender frame, pink gem; director: heap coins 1.45x at 0.64 spacing (they read as noodles), stacks re-spaced, a brighter core. | The phone's chest is turned to show its left end, fills more of the card, and its lid is thrown back. |
| `bundleSafe` | **B** | new | Lavender safe, open door, coins pouring out; director: no cast shadows (a hard diagonal shadow wedge crossed the coins), coins 1.45x at 0.64 spacing. | The phone shows the door's wheel face-on at the far left; ours shows the door edge-on. |
| `bundleSpecial` | **B** | new | The 1 000 pile at the Special card's size + glints, frame 176 x 102. | The left coin on edge faces further right; the phone's glints are warmer and bigger. |
| `coinPackBig` | **B** | B | - | Shadow fixed. |
| `coinPackGiant` | **B** | B | - | Shadow fixed. |
| `coinPackMedium` | **B** | B | - | Shadow fixed. |
| `coinPackSmall` | **B** | B | - | Shadow fixed. |
| `coinPackSuper` | **B** | B | - | Shadow fixed. |
| `coinPackTiny` | **B** | B | - | Shadow fades before the frame edge (no hard line). |
| `glyphBell` | **B** | B | - | The lip band is narrower than the phone's. |
| `glyphHapticWhite` | **B** | B | - | meta-029's white vibrating phone; ~0.85x of the phone's glyph width. |
| `glyphMusic` | **A** | A | - | none visible at game size |
| `glyphOffSlash` | **A** | new | The Settings OFF rod as art (optional; the shell may keep its SwiftUI rod). | none visible at game size |
| `glyphSoundWhite` | **A** | A | - | none visible at game size |
| `iconCheckBadge` | **B** | new | The flatter Edit Profile badge (thick outline + inner light contour), 40 x 34. | The capture's dark outline is thicker and its green brighter. |
| `iconPencil` | **A** | A | - | none visible at game size |
| `iconSkyDrum` | **B** | new | The Profile drum: pink cushion, cream rings, gold belt + plate, purple foot, cyan glow. | near A: our body is taller and the plate smaller than meta-002's. |
| `pageBgPattern` | **A** | new | meta-029's page pattern: 2 chunky arrows per 145 x 79.3 pt repeat at alpha 0.10. | none visible at game size |
| `settingsRoundToggle` | **C** | C | - | Owner: shell. |
| `shopSeal` | **A** | new | Red 8-lobe scalloped seal with a gold rim, text live, -12 deg. | none visible at game size |
| `statFirstTryIcon` | **B** | B | - | The target face is slightly smaller than meta-002's. |
| `statWeeklyWinsIcon` | **B** | B | - | 1.33x bigger (48 x 51), ribbon as wide as the medal, wider gold bar. |

### app-icon

| id | grade | was (r2) | what changed (round 3) | remaining gap |
|---|---|---|---|---|
| `appIcon` | **B** | B | - | Heads and shafts ~1.25x, rounder pillow bevel, keep the composition. |

<!-- END TABLE -->

## Still missing vs SPEC-ui's UI ART PLAN (§4.2)

Every art id §4.2 proposed now exists or is covered:

| §4.2 proposed | now |
|---|---|
| `unlockIconBox`, `boxSlab`, `boxRing` | built (round 2); `unlockIconBox` A |
| `iconStopwatchFrozen` | built, B (34 × 50: the icicles) |
| `fxFrostVignette` + `frostCracks` | `fxFrostVignette` ships alone, B; `frostCracks` built, not shipped |
| `heartBig` | built as SVG (B3 → B2), A |
| `heartLivesBig` | built, A (+ new `heartGlossySmall` for the ad button, A) |
| `iconVideoAd` | built, A |
| `iconCheck` | split: `iconCheck` (Claw / Sky Jump) B + `iconCheckBadge` (Edit Profile) B |
| `iconSkull` | split: `iconSkull` (Hard) A + `iconSkullBones` (Super Hard) B |
| `rankWings1` | built, B |
| `rocketOfferScene` | built, B (+ `planetStage1..3`, B, which SPEC-ui draws but had no id) |
| `weeklyContestLogo` | **SwiftUI EventLogo, todo (shell)**; its look target is built (ruling 3) |
| `iconFlagRoll` | covered by `scoreChip` (round 2) |
| `iconSkyDrum` | built, B |
| `bundleBag`, `bundleChestRed`, `bundleChestPurple`, `bundleSafe`, `bundleCart` | built as `bundleBag`, `bundleBarrel`, `bundleChest`, `bundleSafe`, `bundleCart` (+ `bundleSpecial`), all B |
| `shopSeal` | built, A |
| `pageBgPattern` | built, A (a 145 × 79 tile of 2 arrows, measured; SPEC-ui guessed 64 pt / 3) |
| `pointerArrowYellow` @ 72 × 97 | a new drawing: `pointerArrowDown` (78 × 104), A |
| `skyJumpIslandFar2` | built, B |

Still open, not art: the 46 SwiftUI entries (now incl. the Weekly EventLogo) and 15 code entries have no app render
to grade yet. The only raster `todo` ids left are the not-shipped V2 avatars, `curtainCyan` and `cornerWedge`
(`confirmed: false`). **New since SPEC-ui was written:** SPEC.md §5.26 (15:55) adds a Corner unlock card at L70 and
corner obstacles on the phone's recorded boards; `cornerWedge` is still the V2 skin and there is no corner card icon —
round 4 should measure the phone's corner skin once the level lane has its L062-L083 shots.

## Round 4: the cheapest A candidates (one pass each)

- `iconStopwatchFrozen`: a lumpier, smaller snow cap and a longer icicle clump.
- `rankWings1`: notched, less flat wings.
- `iconSkyDrum`: a shorter body and a bigger plate.
- `fxFrostVignette`: more saturated side ice, denser corner cracks.
- `logoArrowOut`: wider block letters with a crisper 3D side.
- `scientistLoading` / `workerCarrier`: store 8's smaller grin (both), separate legs + shoes under purple pants (carrier).
- `iconCheck` / `iconCheckBadge`: a deeper extruded side / thicker outline + brighter green.
- `bundleChest`: yaw so the left end shows and throw the lid back; `bundleSafe`: the door's wheel face-on at the left.
- `rocketOfferScene`: 163's turned chest on a rock slab, brighter coins.
- The popup chrome: 5 ids go B → A as soon as the shell applies polish.md §B (re-grade in the app render).
- Round 2's list still stands for the ids no lane touched this round (homeConsole, homeCapsuleMachine, navHome, the
  home workers, avatars, rocketRaceBackdrop, workerRacers, skyJumpPopupScene, boxRing, coin packs, glossy arrows).
