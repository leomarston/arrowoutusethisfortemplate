# Lane "missing-svg" (route B2) — Arrow Out

2026-09-25, art round 3. Scope: the SVG ids of SPEC-ui §4.2's unbuilt list, plus the Settings art REVIEW.md "For other
owners" asks for. 15 entries, all built, all `ok` in `manifest_check.py --lanes art/lanes/missing-svg.entries.json`, all
verified by `art_batch.py` (RGBA, exact frame x 3, cut-out, not clipped). Nothing in `App/` or `art/MANIFEST.json` was
edited. No commit.

Copying line: every shape is a primitive (ellipses, circles, rounded polygons, round-capped strokes, the two-ellipse
heart of `shapes.py`) whose numbers were MEASURED on the captures: ink extents, colour profiles, and shape parameters
FITTED to masks (the hearts, the checks). The fitted numbers are in the comment above each case. Nothing is traced and
no capture pixel goes into an asset. Numbers and words stay live text.

## Files

| file | what |
|---|---|
| `art/ui/src/svg/gen_missing.py` | the generator, `CASES[<id>]()` for all 15. It imports `gen_icons.py` read-only (`Doc`, primitives, the stopwatch drawing), because that file belongs to the svg lane. |
| `art/lanes/missing-svg.entries.json` | the 15 full manifest entries, status `done`. Each entry's notes hold its placement, its live-text anchors and its self-grade. |
| `art/ui/out/<id>@3x.png` + `art/ui/src/<id>.svg` | outputs + the intermediate SVGs that `art_batch` writes |

Rebuild and sheets:
```sh
PY=~/.venvs/mf3d/bin/python     # from apps/mazeout
$PY art/tools/art_batch.py --manifest art/lanes/missing-svg.entries.json --svg          # ~12 s, one WebKit run
$PY art/tools/manifest_sheets.py --manifest art/lanes/missing-svg.entries.json <ids>    # art/ui/sheets/m_<id>.png
python3 art/tools/manifest.py merge art/lanes/missing-svg.entries.json                  # director: 15 new ids
```

## Entries (self-grade at game size; every one looked at on its sheet AND composed into its screen)

| id | frame pt | where (frame top-left in the ref shot, pt) | grade | remaining gap |
|---|---|---|---|---|
| `iconStopwatchFrozen` | 34 x 50 | meta-065 (90.45, 72.4) = hud.stopwatch origin + (-2.25, -5.3). The iced watch sits ~1 pt higher than on 003. | B+ | The capture's snow cap is lumpier. |
| `frostCracks` | 120 x 120 | top-left corner tile, corner at (0, 0); mirror it for the other corners | B | Optional (see note 1). |
| `heartBig` | 194 x 164 | meta-088 (99.5, 316.0); body box at frame (4.5, 5.0), 185 x 155 | B | Silhouette IoU 0.986 on the red body, and the notch profile matches within 1-2 pt. At game size the lobes read a little flatter and less sculpted than meta-088's. The red glow is code (SPEC-ui 2.6.2). Stopped at the 25-min cap. |
| `heartGlossySmall` | 46 x 40 | meta-095 (140.0, 592.0), the heart on the "+1 Live" ad button (it had no id) | B+ | The capture's specular is a touch larger. |
| `heartLivesBig` | 100 x 90 | meta-095 (146.9, 250.5); fitted heart box (150.4, 254.3), 92.5 x 79.4 | B+ | The specular is a touch small. |
| `iconVideoAd` | 40 x 41 | meta-095 (97.0, 589.7). The play triangle is a HOLE, so the button face shows through. | A | none at game size |
| `iconCheck` | 60 x 54 | meta-039 Claw card (211.8, 738.2). Sky Jump won stage (096): the same art at 0.755, frame at (72.0, 460.1). | B+ | The capture's extruded side is a little deeper. |
| `iconCheckBadge` | 40 x 34 | meta-003 (115.0, 392.6) = selected tile (67.4, 339.6) + (47.6, 53.0) | B+ | The capture's dark outline is a hair thicker. |
| `iconSkull` | 30 x 32 | 037 left skull (101.0, 117.5). The right skull is the same drawing, not mirrored. The eye sockets are holes. | B+ | The capture's sockets slant more. |
| `iconSkullBones` | 38 x 38 | 063 left (95.5, 114.0), Super Hard (outline #3A007C) | B | The bones are a little long. |
| `rankWings1` | 52 x 38 | 167 (13.5, 338.5); on 171's race bar, (308.3, 713.8) | B+ | The wings are a little lower at the outer end. |
| `shopSeal` | 66 x 66 | meta-012 (1.4, 183.3); 8 lobes (the radius profile's harmonic 8) | B+ | none beyond the live text |
| `pageBgPattern` | 145 x 79 tile | Screen tile origins at x = 145 i, y = -7 + 79 j | B+ | The arrow outlines are our block arrows at the measured size, tilt and lattice. |
| `pointerArrowDown` | 78 x 104 | 130 (285.0, 635.2); tip at frame (39.2, 101) | A | none at game size |
| `glyphOffSlash` | 56 x 52 | meta-029; anchor = the button FACE centre = frame (28.6, 28.4) | A | none (covers the capture's rod in place) |

Composed proofs, regenerated from the scratchpad scripts and then looked at:
- More Lives (meta-095): heartLivesBig, iconVideoAd and heartGlossySmall with stand-in live text.
- Out of Lives (meta-088), Win Hard (037), Rocket Race (167), Shop (meta-012), Freeze HUD (meta-065), Sky Jump stage row (096).
- The Settings page (meta-029): our pattern tiled over the de-patterned ground, plus the OFF rod on Music.
All of them read the same as the captures at game size.

## Decisions against SPEC-ui §4.2 (please carry into the manifest / SPEC)

- **iconStopwatchFrozen**: the frame is 34 x 50, not 31 x 33, because the icicles hang to y 120. It embeds iconStopwatch's own drawing at 1.02x.
- **heartBig** ships as SVG (§4.2 said B3).
  - The missing-3d lane agreed: its `m3d_fx.py` DEST now sends its 3D heart to `build/ui-art/route3d/heartBig.png`
    as a route candidate, never to `art/ui/out`.
  - Race window: before that change (14:27), both lanes wrote `art/ui/out/heartBig@3x.png`. My batch at 14:20:59 overwrote
    the 3D lane's shipped render. Their render is reproducible with `m3d_make.py build heartBig3d`, which now goes to route3d.
  - The file in `art/ui/out` is mine (582 x 492 px).
- **iconCheck** is split in two: `iconCheck` (the glossy extruded Claw / Sky Jump check) and `iconCheckBadge` (the
  flatter Edit Profile badge: a thick outline plus an inner light contour, no extrusion). They are different drawings,
  not two sizes of one.
- **iconSkull** is split in two: `iconSkull` (Hard, 037) and `iconSkullBones` (Super Hard, 063 shows crossbones).
- **pointerArrowYellow @ 72 x 97** became **`pointerArrowDown`**. The Weekly tutorial's arrow (130) is a straight block
  arrow, not the curved Claw pointer, so it is a new drawing and not a size variant.
- **pageBgPattern**: SPEC-ui 1.6.9 guessed a 64 pt tile of 3 arrows. Measured on meta-029, it is 2 chunky arrows per
  145 x 79.3 pt repeat, lighter than the ground by (0, +4, +3.5) RGB. The tile is transparent: the arrows are #0B4A97 at
  alpha 0.10, drawn over `page.bg.navy`.
- **heartGlossySmall** is new: SPEC-ui 2.9's ad-button heart had no id.
- **glyphOffSlash** is new and optional: the art version of SPEC-ui 1.6.14's SwiftUI rod. It is identical on all three
  toggles, and the shell may use it or keep drawing the rod in SwiftUI.

## Live text anchors (frame pt, origin top-left)

| id | text | where |
|---|---|---|
| heartLivesBig | count "3" | centre (49.3, 42.5), 50.3 pt, face #FFFBE6, outline #870400 1.7 |
| heartLivesBig | "+" | centre (80.8, 78.2), ~28 pt, same style. It overhangs the frame, so do not clip it. |
| heartGlossySmall | "+1" | centre (36.5, 31.9), ~22 pt, face #FFFBE6, outline #0B5A18 |
| rankWings1 | "1" | centre (26.35, 18.5), ~20 pt, white, outline #800100 |
| shopSeal | "90%" / "OFF" | centred at (33, 33), rotated -12 deg. EN: 18.5 / 15.2 pt. TR: "%90" / "İNDİRİM". Outline #69000C. |

## Notes for the other owners

1. **frostCracks vs fxFrostVignette.** The missing-3d lane ships `fxFrostVignette` as one full-screen raster, and that
   raster already paints cracks. If it ships, do not also draw `frostCracks`, or the cracks double. `frostCracks` only
   serves SPEC-ui's original route (a code gradient plus a corner crack tile). The director should pick one.
2. **Settings (REVIEW "For other owners").** The white-on-green glyph set is complete: `glyphSoundWhite`, `glyphMusic`,
   `glyphHapticWhite`, `glyphBell`, plus `glyphOffSlash` for OFF. No toggle art is needed beyond that. SquareToggle and
   PillToggle stay SwiftUI.
3. **Out of Lives.** The red radial glow is code: #FF2F20 at the heart edge, #480F0D at 100 pt, black by 150 pt.
   `heartBig` has only its own dark rim.
4. **Not in this lane.** These are other routes: `rocketOfferScene` (C1), `weeklyContestLogo` (B1), `iconSkyDrum`,
   `bundle*`, `skyJumpIslandFar2`. SPEC-ui's `iconFlagRoll` is covered by `scoreChip`, as REVIEW says.
5. **Other lanes' failures.** The `manifest_check --lanes` failures on `iconCoin`, `iconPlusGreen`,
   `iconStopwatchSmall`, `unlockIcon*`, `heartLives`, `iconHexArrow`, `workerRunners` and `workerFist` belong to lanes
   that were running at the same time and resized those files around 14:30. They are not this lane's.
