# Polish lane (art round 3): the most visible B entries raised toward A

2026-09-25. Scope (orchestrator): HUD (iconCoin, iconPlusGreen, iconStopwatchSmall, heartLives, heartInfiniteSmall,
iconHexArrow), the popup chrome (buttonGreen / buttonRed, panelFrame, panelRibbon, panelClose: SwiftUI route, so
instructions for the shell), the unlock card icons (Box, Linked, Elevator, Door), logoArrowOut, sunburstRays and the
rank badges. Every change was built, put next to its reference at game size and in place at the rect the shell draws
it in, looked at, and iterated. Nothing in `App/` was edited. `art/MANIFEST.json` was not edited either: this lane's
entries are in `art/lanes/polish.entries.json`.

Copying line: every shape is still a primitive or our own OFL glyph, with its parameters measured on the captures. The
measurements are written in each function's docstring. Nothing is traced, and no capture pixels go into an asset.

## Files

| file | what changed |
|---|---|
| `art/ui/src/svg/gen_icons.py` | These functions were rewritten from new profiles: `icon_coin` (now `_coin`), `icon_plus_green`, `icon_stopwatch(small=True)` (the `small=False` path is unchanged), `heart_lives`, `heart_infinite_small`, `icon_hex_arrow`, `unlock_box`, `unlock_linked`, `unlock_door`, `unlock_elevator`, `sunburst_rays`, `rank_badge` (new `RANK3` table) and the logo's letter rendering (`LOGO`, solid extrusion + inner-bevel filter). The round-2 drawings are kept as `*_r2` for comparison and are not in `CASES`. `prizeSign` and `statWeeklyWinsIcon` embed a coin, so they now call `icon_coin_r2` and stay pixel-identical. |
| `art/ui/out/*.png` | 16 rebuilt: the 15 ids below + `rankBadgePlain`, which is not shipped but shares the badge generator. |
| `art/lanes/polish.entries.json` | 16 full entries with the new `size_pt` / `size_px`, `status: done` and notes. |
| `art/review/tools/polish_proofs.py` | The proofs: `hud`, `unlock`, `events`, `logo`, `popup`, written to `art/ui/sheets/polish/` (gitignored). |
| `art/review/tools/polish/{build.sh, chrome_polish.swift, stubs.swift, main.swift}` | The SwiftUI prototypes. `build.sh` copies the shell's `PopupChrome.swift` read-only, compiles it with the proposal (swiftc only, ~15 s) and renders both at 007's `ui.json` frames to `build/ui-art/polish/pause_{shell,polish}.png`. |

Checks:
- `art_batch.py --manifest art/lanes/polish.entries.json --svg` reports 16 OK and "all built entries verified". The edge alpha is ≤ 14 on every side for every file.
- Every `gen_icons.CASES` output was re-rendered and compared with `art/ui/out`: 41 cases, 0 differing. Nothing else moved.
- `manifest_check.py --quiet --lanes art/lanes/polish.entries.json` gives 208 entries and 2 failing. Both failures (`workerRunners`, `workerFist`) are the characters lane's current work, not this lane's.
- The plain `manifest_check` fails on this lane's 14 resized ids until the merge. That is expected (PIPELINE §0).

**For the director's merge:** `director.entries.json` still holds the round-2 `size_pt` of these ids. Merge
`polish.entries.json` after it, or the sizes revert. `director_merge.py` has a fixed lane order, so `polish` must be
appended after `director` there.

## Entries (self-grade at game size; A = reads the same as the original's art at game size)

| id | was | now | what changed | remaining gap | sheet |
|---|---|---|---|---|---|
| `iconCoin` | B | **A** | Re-measured on 002's home coin (34.0 × 34.3 pt of ink):<br>• darker, thicker outline (#85430F / #9A4A10)<br>• a 6 pt thickness band (#E69014 → #C15B00)<br>• the recess's top wall in shadow (#B23C00)<br>• a chubby star with an extruded orange side<br>• no white glints<br>Frame **39 pt**: home's 38.5 pt rect draws it at 0.99× (it was 1.28×). | The HUD draws it at ~0.68×: judged on 003's crop only, not in an app render. | `polish/hud_002.png` |
| `iconPlusGreen` | A | **A** | Frame **24 pt**, which the shell's 23.5 pt rect draws 1:1.<br>• vivid flat green (#00DB00)<br>• a top-only light ring and a dark lower rim<br>• a short chunky cream plus with a 4 px dark drop (002) | none at game size | `polish/hud_002.png` |
| `iconStopwatchSmall` | B | **A** | 204's chip watch is 22.7 × 26 pt of ink, so the frame is **26 × 28**. The old 18 pt frame drew it at ~0.7×.<br>• dome crown<br>• warmer ring<br>• long tick pills<br>• a fat wedge hand at 40° | The hand angle is fixed; the original's turns. | `polish/hud_watch.png` |
| `heartLives` | B | **A** | Frame **42 × 40**, the shell's 42.3 × 39.8 rect at 1:1. HEART2 at 002's 39.7 × 33.7: round 2 was 11 % too tall once scaled.<br>• deeper crimson<br>• a dark top band<br>• a softer, darker outline | none at game size | `polish/hud_002.png` |
| `heartInfiniteSmall` | B | **A** | Same frame. The heart is 42 × 36.4 (was 45 × 39), and the infinity is rounder, thinner-edged cream. | none at game size | `polish/hud_168.png` |
| `iconHexArrow` | B | **A** | Frame **40 × 40**; the ink is 37.3 × 35 at 1:1 (it was ~1.15× too big).<br>• a thick pale 3D side at the lower left<br>• a sky-blue arrow with a dark-**purple** edge and its own slab side | The chain hook belongs to the bar. | `polish/hud_168.png` |
| `unlockIconBox` | B | **A** | Drawn as its own card illustration, no longer the board sprites:<br>• a pillow slab 121.5 × 127<br>• the sphere in a dark crease<br>• four stubby cylinder lugs in front of the rim<br>• a tube-like purple ring<br>• a 41 pt navy well | The lug caps are a touch flatter than 134's. | `polish/unlock.png` |
| `unlockIconLinked` | B | **A** | V1 t 78 s at 1:1: 141.7 × 97 pt of art in a **150 × 106** frame (round 2 was 0.8×).<br>• 15.4 pt shafts<br>• 45.5 × 47 rounded heads<br>• the board tape at P 54 | The V1 skin itself is older (SPEC 5.10). | `polish/unlock.png` |
| `unlockIconElevator` | B | **A** | V2 t 1182.5 s at 1:1: 159.5 × 105 in a **164 × 112** frame.<br>• icy blue-grey<br>• a soft outline<br>• wide faint stripes in V2's direction<br>• flat #A1B1CB windows with a light bevel | Unconfirmed on the phone. | `polish/unlock.png` |
| `unlockIconDoor` | B | **A** | V1 t 185 s: the card door is **square, 5 × 5 cells**, with the lock at the door's own pitch. Frame **128 × 128**, drawn at the phone cards' size (~121 pt). | Unconfirmed on the phone (no v552 door card). | `polish/unlock.png` |
| `logoArrowOut` | B | **B+** | Fatter bubble letters (sx 0.80, inflation 34; OUT! 26 at cap 335). A solid graded extrusion replaces the shifted dark copy, which read as a double image. An SVG inner-bevel filter per letter adds a dark lower rim and a light upper-left rim. The extrusion is shallower (58 / 44) and the tilts bouncier. | MAZE's letters are chunky blocks with crisp rounded corners; our five inflated letters touch and read softer at the bottoms. Stopped here (see the 25-minute rule); a round-4 idea is per-letter kerning + a smaller inflation with a real bevel. | `polish/logo.png` |
| `sunburstRays` | B | **A** | Frame **190 × 86** = 023's whole cream reward field, clipped to its r 22 corners. The rays reach the edges and are centred on the prize (0.5 W, 0.34 H), with a softer falloff and a centre glow. | none at game size | `polish/rays.png` |
| `rankBadgeGold` / `Silver` / `Bronze` | B | **A** | 203 at 1:1: the badge is 37.3 × 36.3 pt (round 2 drew 33 × 32), so the frame is **40**.<br>• a thin dark outline<br>• a 1.7 pt 3D side<br>• a rim band and a light upper bevel<br>• a window ring 0.65 of the width (a dark line + band + light line)<br>Gold is from store 6's profile. | Gold is not captured on the phone. | `polish/streak_badges.png` |
| `buttonGreen` / `buttonRed` | B | **A−** (proposal) | SwiftUI. See "Shell instructions" §B. | Grade it again once the shell renders it. | `polish/popup.png`, `popup_buttons_zoom.png` |
| `panelFrame` | B | **A−** (proposal) | SwiftUI (§B): a 21 pt bar with its own outlines, separate corner bumpers with square ends and royal-blue + light edge bands, n 5.8, measured rivets. | — | `polish/popup.png` |
| `panelRibbon` | B | **A−** (proposal) | SwiftUI (§B): a true polar arch (the ends lean in ~7°), top r 16 / bottom r 20, and a darker 7.7 pt bottom rim. | The bottom rim is still a hair lighter at mid-depth. | `polish/popup_top_zoom.png` |
| `panelClose` | B | **A−** (proposal) | SwiftUI (§B):<br>• a thicker **radial** blue ring (outer ⌀ 56.3 at d 45)<br>• a 3.3 pt dark-red rim<br>• a flat vertical face with a light top band<br>• the X at 0.60 d | — | `polish/popup_top_zoom.png` |

## Shell instructions (numbers; the shell owns every file named here)

### A. Rasters: frames, rects, ink boxes, live-text anchors

1. **UIArt.swift** is generated from the manifest. After the director merges `polish.entries.json`, re-run `tools/uiart_gen.py`. The new sizes (pt):
   - iconCoin 39 × 39
   - iconPlusGreen 24 × 24
   - iconStopwatchSmall 26 × 28
   - heartLives 42 × 40
   - iconHexArrow 40 × 40
   - unlockIconLinked 150 × 106
   - unlockIconElevator 164 × 112
   - unlockIconDoor 128 × 128
   - sunburstRays 190 × 86
   - rankBadgeGold / Silver / Bronze / Plain 40 × 40

   These keep their size: heartInfiniteSmall 46 × 42, unlockIconBox 132 × 134, logoArrowOut 306 × 236.
2. **S2Chrome.swift `ArtInk.boxes`**: replace these 15 rows. Every `InkImage` user (the HUD coin pill, the streak banner watch, the Continue token hex, RaceBar's badge, the unlock overlay) depends on them.
   ```swift
        .iconCoin: (0.0769, 0.0427, 0.9231, 0.9573),
        .iconPlusGreen: (0.0972, 0.0972, 0.9028, 0.9167),
        .iconStopwatchSmall: (0.0513, 0.0238, 0.9487, 0.9524),
        .heartLives: (0.0397, 0.0500, 0.9683, 0.8833),
        .heartInfiniteSmall: (0.0290, 0.0873, 0.9420, 0.9524),
        .iconHexArrow: (0.0167, 0.0250, 0.9750, 0.9750),
        .unlockIconBox: (0.0379, 0.0224, 0.9621, 0.9851),
        .unlockIconLinked: (0.0178, 0.0472, 0.9644, 0.9686),
        .unlockIconElevator: (0.0061, 0.0179, 0.9939, 0.9881),
        .unlockIconDoor: (0.0286, 0.0391, 0.9792, 0.9844),
        .logoArrowOut: (0.0283, 0.0071, 0.9771, 0.9845),
        .sunburstRays: (0.0018, 0.0039, 0.9982, 0.9961),
        .rankBadgeGold: (0.0333, 0.0667, 0.9667, 0.9750),
        .rankBadgeSilver: (0.0333, 0.0667, 0.9667, 0.9750),
        .rankBadgeBronze: (0.0333, 0.0667, 0.9667, 0.9750),
   ```
3. **Home top bar.** The `home.coinIconArt` rect (93.45, 51.15, 38.5, 38.5) and `home.plusBadgeArt` (116.6, 71.1, 23.5, 23.5) stay; they now draw 1:1. `home.livesHeartArt` (210.5, 50.9, 42.3, 39.8) stays too. The heart's centre moved by < 0.2 pt, so the lives count needs no move; it sits at frame (21.3, 19.4).
4. **Claw bar** (SPEC-ui §2.2.3):
   - `iconHexArrow`: place the frame at (29.0, 109.2, 40, 40), or `InkImage` with ink (30.3, 110.7, 37.3, 35.0).
   - `heartInfiniteSmall`: the frame at (323.6, 108.4, 46, 42). The duration text is centred at frame (22.6, 32.9), i.e. screen (346.2, 141.3).
   - Timer chip watch `iconStopwatchSmall`: the frame at (154.0, 142.6, 26, 28).
5. **UnlockOverlay `UnlockContent.of`:**
   - `.unlockIconBox`: keep the ink (136.5, 351.0, 121.5, 127.5), but set `at = CGPoint(x: 0.497, y: 0.487)`. The well's centre is now frame (65.55, 65.25) of 132 × 134.
   - Give the icons that use the `default:` branch their own ink rects:
     - `.unlockIconLinked` (123.7, 365.7, 142.0, 97.7) (V1's placement)
     - `.unlockIconElevator` (115.75, 363.5, 162.0, 108.7)
     - `.unlockIconDoor` (135.65, 349.5, 121.7, 121.0)
   - The twinkle ellipse centre follows `iconCentre`, so it needs no change.
6. **Rank badges:** the rank digit is centred at frame (20, 19.3). On 203 the frame goes at (16.7, 494.7, 40, 40) for row 2 (the badge centre at (36.7, 514.7)). RaceBar's `InkImage(ink: 32 × 32)` needs no change.
7. **sunburstRays:** draw the frame 1:1 over the Claw reward card's cream field (023: (147.5, 455, 190, 86)). The rays are clipped to the field's r 22 corners. For a field of another size, scale the frame to the field's width.
8. **WinLogoSequence `LogoParts.split`:** the colour keys still hold on the new logo. The yellow key covers the new extrusion (#EE8A06 → #B45000) and rims. The white key covers OUT!'s #CBC4DC → #877FA6 side. Both stay inside fy 0.05-0.52 / 0.575-0.897. The letters sit a little differently, so move the cuts to the measured gaps:
   `let cuts = [0, Int(0.2440 * Double(W)), Int(0.3540 * Double(W)), Int(0.4978 * Double(W)), Int(0.6732 * Double(W)), W]`.
   The inflated letters touch, as round 2's did, so a sliver of each neighbour stays in a letter part at the cut. The fix for that is still MA §15.4's separate part files (a UI-ART request, not in this lane's scope).

### B. Popup chrome (`App/Shell/Popups/PopupChrome.swift`)

The rendered proposal is `art/review/tools/polish/chrome_polish.swift` (`PolishPanelFrame`, `PolishRibbon`,
`PolishCloseButton`, `PolishButtonFace`). Copy the bodies, or apply the numbers below. All values are pt at 007's
`ui.json` `frames.pause.*`. Evidence: `polish/popup.png` shows the shell's chrome today and the proposal over 007.

**PopupPanelFrame** (the panel is 370.6 × 399)
- `n` 6.3 → **5.8**. On 007 the outer corner is ~6 pt rounder than n 6.3 at 10-20 pt from the corner.
- **Bar** (outer edge → groove = **21.0**; was 18.6), from outside in:
  - a #152C74 hairline 0.35
  - the #13349E outline to 1.6
  - a light line #0169EE from 1.6 to 2.2
  - the face `LinearGradient(#0060EE, #005EEE, #006AFD)` top → bottom from 2.2
  - a light line #0169EE at 18.7–19.3
  - the bar's own inner outline #13349E from 19.3 to 21.0

  007: `row y=400` 11.3 #152C74, 12-13 #13349E, 14 #0169EE, 15-29 #005EEE, 30 #0169EB, 31-32 #13349E, 33 #0C2897.
- **Corner bumpers** are separate raised pieces with square ends, not a uniform ring:
  - The shape is the ring between the outer superellipse and the one inset by 21.0, intersected with four corner rects: top **83.4 × 90.4**, bottom **83.4 × 93.5**, corner rounding 1.2.
  - Fill `#00A7EE` (the top 5 %) → `#00B4FF`.
  - Edge bands, stroked and **clipped inside the bumper shape**: #4AC8FF width 6.0 (3 pt visible), #1D53FF 3.2, #13349E 0.9.
  - 007 `row y=290`: 13 #1C3175, 13.3-14 #1C53FD, 15 #4CA9FF, 16 #10B9FF, 17-30 #00B4FF, 32 #4AC9FF, 33.7 #1D52FF, 35 #0D2792.
- **Groove**, 21.0 → 30.8: fill #1A53DF plus a #0C2794 stroke of 13 blurred 3.4, clipped, so it is dark at the bar and lighter toward the field. Then the field's bright rim line **#257DF7 1.0 pt**, then the field #226DF5 (from 31.8). 007: `row y=400` 33 #0D2A9A … 41.7 #1D5DE7, 42.3 #257DF7, 44 #216DF6.
- **Rivets** ⌀ **11.6** (was 13): edge #1A46C0 1.0; dome `RadialGradient(#4CA8EE, #3B8AE4, #2256C8)`, centre (0.5, 0.45), r 5.4. Centres, measured as 007 blob centres, panel-relative:
  - (12.0, 79.8) and (W − 12.0, 79.8)
  - (12.0, H − 83.7) and (W − 12.0, H − 83.7)
  - (72.5, H − 15.7) and (W − 72.5, H − 15.7)

  (The shell's current `rivetInset` (12.2, 80.2) / `along` 73 is close. The low side pair is the one that moves: 83.7 from the bottom, where 80.2 is used today.)

**PopupRibbon** (frame (60.1, 190.5, 274.2, 90.4))
- **Shape:** a *polar* arch instead of `y += dx²/2R`. A flat body point (x, y) maps to θ = (x − cx)/R, r = R − (y − top), (cx + r·sinθ, top + R − r·cosθ), with R = 1100, so the ends lean in ~7° as on 007.
- The flat body is **2.2 pt wider each side than the frame**, so its widest row spans the frame after the lean. Thickness **84.5**, top corners r **16**, bottom corners r **20** (was 27 all round). Measured left edge per row: y 200 → 69.3 (ours 67.0), 215 → 60.3 (60.0), 245 → 64.7 (64.0), 272 → 70.3 (69.7).
- **Layers** (insets top / sides / bottom from the body; blur in pt):
  - #642806 (0/0/0)
  - #6A2400 (0.3/0.3/0)
  - #8D3403 (0.3/0.5/1.4, blur 0.5)
  - #B04405 (0.3/0.8/3.2, 0.7)
  - #D35001 (0.3/1.1/5.0, 0.7)
  - #EF8C00 (0.3/1.3/6.6, 0.6)
  - the top band `#963804 → #B94907` over the first 3 % (0.3/1.4/7.6)
  - the highlight #FFFA4A (2.0/1.9/7.7, 0.5)
  - the face `#FFD500 → #FFC800 → #FFB600` (4.4/2.4/7.7, 0.4)

  007 `col x=100`: 194.3 #542308, 195-196 #A23C05..#B94A07, 197-200 #ECD83E..#FFF034, 201.7 #FFD400 … 270.3 #FFB600, then 7.7 pt #EF8F00 → #D95800 → #BB4906 → #943703 → #672200.

**PopupCloseButton** (frame d = 45)
- Ring outer ⌀ **d × 56.3 / 45** (was 52.4):
  - a #081B66 outer line
  - then a **radial** ring gradient from the disc edge outward: #1A98DD 0, #127ECA 0.35, #0B5EB3 0.7, #0848A3 1. It is light next to the disc and dark outside; the current gradient is vertical.
  - a 0.4 pt #2A3550 line between the ring and the disc
- Disc ⌀ **d × 46.2 / 45**: a dark-red rim `RadialGradient(#BA0000, #9E0000, #4D0000)` over its outer 3.3 pt.
- Face inset 3.3 (sides) / 2.7 (top, bottom), offset y −0.6: a **vertical** gradient #FF7A7F 0, #FF5A5E 0.08, #FF5155 0.16, #FF4447 0.5, #FF3C3D 1. Drop the radial face and the white gloss ellipse.
- X glyph frame **0.60 d** (was 0.56), outline #730606, drop #670202 at +0.06 w.
- 007 centre row: 334 #0848A3 → 337 #1897DD (ring), 338 #4D0000 → 341 #B90000 (rim), 342.7 #FF3D3E (face).

**ChromeButtonFace for the popup buttons** (Resume, Quit and every popup PanelButton; keep the home Play as it is: it is graded A)
- Add a style or palette: `PolishButtonColors.green / .red` in `chrome_polish.swift`. The values:
  - Outline 0.8 pt: green #0B3A00, red #4E0103.
  - Rim, green: (#029A0A 0, #02A80A .45, #02A00A .7, #01980A .8, #018C01 .88, #007D00 .92, #006600 .955, #004900 1).
  - Rim, red: (#E02628 0, #F22E30 .4, #E8202A .7, #D0101A .8, #B00203 .88, #A00000 .92, #8D0000 .96, #6A0001 1). On 007 the side rim is the face darkened, not a dark green or red.
  - Face, green: (#02E110 0, .06; #00E900 .12, #00E700 .18, #00E300 .3, #00DF00 .42, #00D500 .75, #00CF00 .9, #00CB00 1).
  - Face, red: (#FF5357 0, #FD4D51 .14, #FA3E41 .3, #F83133 .43, #F4161C .62, #F10A16 .73, #EE0A13 .85, #EA060F 1).
- Rim darkening stroke: 2.4, blur 0.8, at 0.55 of the outline colour (was 4 / 1.33 / 0.75).
- Face shape n **3.9** (was n + 0.5 = 5.1): the face corners are rounder on 007. Face inset at the 89 pt height: sides **6.0** (was 7.67), top **1.6**, bottom **10.8**.
- **Edge light:** a stroke of 2.6, blur 0.7, clipped to the face and masked to the **sides only** (clear 0 → white 0.14 … white 0.7 → clear 0.95). Green #8CF88C, red #FD6F74.
- **Glare:** a 0.9 pt core line (green #91FC92, red #FF7378) 4.7 pt under the face top along the contour, inset 1.6 at the sides, masked to the top 8-17 %. Add a soft 2.2 pt line, blur 0.9, at 0.55, 5.6 pt under it. The current glare is 1.5 pt at 0.85 fading over 55 %, which is the "heavier glare" grader A saw. 007 `col x=123`: face top 486.3, glare core 492.0 #91FC92, gone by 495.
- **The well** (popups only): a dark ring 2.3 pt `#1036AE → #1848CE` outside the body and a 1.2 pt light rim #2A8BF9 beyond it, blur 0.5. Draw it as a `.background` with negative padding; the `Rasterized` overflow must be ≥ 4. 007 `row y=500`: 59.3 #2885F8, 60.3 #1B51D9 … 62.3 #1038B3, 63 the button's outline.

### C. Not art (FYI)

The repo's working tree is on `build/matchfactory`, with `apps/mazeout/` untracked. Another session switched
branches; `build/mazeout` still points at 4a06449. The files in the tree matched 4a06449 when this lane started. This
lane did not touch git.

## Regenerate

```sh
PY=~/.venvs/mf3d/bin/python                                   # from apps/mazeout
$PY art/tools/art_batch.py --manifest art/lanes/polish.entries.json --svg
sh art/review/tools/polish/build.sh                           # SwiftUI: shell today vs the proposal (swiftc, ~15 s)
$PY art/review/tools/polish_proofs.py all                     # -> art/ui/sheets/polish/*.png
$PY art/tools/manifest_check.py --quiet --lanes art/lanes/polish.entries.json
```
