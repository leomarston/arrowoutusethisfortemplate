# SVG lane (route B2) — Arrow Out

Scope: every MANIFEST entry with owner `ui-art` + family `svg`, plus the `fx` svg entries (boardTrailStar, doorShards,
pipeShards, heartHUDHalves, sparkleTwinkle). 39 entries: 38 built by this lane, `heartHUD` was already done by the art
spike (gen_chrome.py, not touched).

Copying line kept: every shape is a primitive (circles, rounded rects, superellipses, stars, hexagons, arcs, lemniscate)
or a glyph of OUR OFL font (PC Display = Nunito wght 1000, design/fonts), with measured sizes/positions. Colours come
from STYLE.md §D tokens or from profiles sampled on the captures, written into the generator comments. Nothing is
traced, and no capture pixels go into an asset. The four unlock icons reuse the pipeline lane's own board sprites
(gen_board: pipe mouth + counter, door + hex lock, curtain/box block, tape). They are imported read-only and drawn at a
larger pitch, so the popup art matches the board exactly. No shared pipeline file was edited.

## Files (this lane only)

| file | what |
|---|---|
| `art/ui/src/svg/gen_icons.py` | the generator: `CASES[<id>]()` for all 38 entries (+ the `Doc` helper, `toon` / `toon3d` outlined-glyph helpers, `embed` for the board sprites) |
| `art/ui/src/svg/glyph_outlines.py` | dumps PC Display glyph outlines to JSON (needs fontTools: run with the system `python3`, the mf3d venv lacks it) |
| `art/ui/src/svg/pcdisplay_glyphs.json` | the dumped outlines (`ARROWOUT!0123456789PRIZE`, black + black italic); only the logo and the medal "1" use them |
| `art/ui/out/<id>@3x.png` | the 38 shipped rasters (all pass `art_batch.verify` and `manifest_check`: RGBA, exact frame x 3, not clipped) |
| `art/ui/src/<id>.svg` | the intermediate SVG that `art_batch.py` writes next to the other generators' SVGs (pipeline convention) |

**Manifest merge.** For each entry below, set `source` = `art/ui/src/svg/gen_icons.py:<id>`. The manifest currently
says `art/ui/src/gen_icons.py`, which does not exist. After that, `art_batch.py --svg --ids <ids>` rebuilds everything
in one WebKit run (about 20 s for all 38). The `ref` column is the reference the sheets were judged on. Several of the
manifest's boxes pointed at the wrong spot (glyphMusic, glyphBell, iconPlusGreen, heartHUDLost, unlockIconLinked,
tutorialHand, the rank badges). The corrected refs are in the JSON block at the end, ready to paste.
While this lane ran it used a scratch copy of the manifest (`build/ui-art/lane_svg/MANIFEST.json`, gitignored) with those
sources and refs. Sheets: `art/ui/sheets/m_<id>.png` (gitignored). Regenerate them with
`manifest_sheets.py --manifest build/ui-art/lane_svg/MANIFEST.json <ids>`, or with the real manifest after the merge.

## Entries

Self-grade: A = reads identical at game size, B = same thing, same style, small visible differences, C = acceptable
stand-in with known gaps.

| id | status | output | reference used (see JSON) | self-grade | remaining differences / notes |
|---|---|---|---|---|---|
| iconCoin | done | art/ui/out/iconCoin@3x.png | 003 HUD coin (sheet scale 0.89) | B+ | Face slightly less orange than 003. Frame 30 pt, while the HUD coin is 23.7 pt and home 34 pt: the app scales it. |
| iconPlusGreen | done | art/ui/out/iconPlusGreen@3x.png | 013 badge (scale 1.17) | B+ | Frame 16 pt vs the 18.7 pt slot (ui-measure home.plusBadge). |
| iconStopwatch | done | art/ui/out/iconStopwatch@3x.png | 003 hud.stopwatch | B+ | Ring a touch more yellow than 003's orange rim. Spade hand is ours. |
| iconStopwatchSmall | done | art/ui/out/iconStopwatchSmall@3x.png | 026 Claw-bar chip | B | Same drawing with heavier outlines. The 026 watch shows at ~20 pt. |
| heartHUDLost | done | art/ui/out/heartHUDLost@3x.png | 110 hud.heart3 after a bump | A- | Flat #6C94DC slot with a darker edge band. Could also be done in code (tinted heartHUD). |
| heartHUDHalves | done (fx) | art/ui/out/heartHUDHalves@3x.png | 003 heart | B | Both halves in ONE sprite, 2.4 px apart and tilted ±3°. The crack polyline is `gen_icons.CRACK` (px) for masking. If FX needs two sprites, ask for `heartHUDHalfL` / `heartHUDHalfR`. |
| heartLives | done | art/ui/out/heartLives@3x.png | 026 home.livesHeart (scale 1.1) | B+ | The count is LIVE text, centred at (17, 15.5) pt of the frame. |
| glyphSound | done | art/ui/out/glyphSound@3x.png | 007 Paused panel | B+ | Ink 28.5 pt wide vs 30.7 pt measured: the 30 pt frame is the limit. |
| glyphHaptic | done | art/ui/out/glyphHaptic@3x.png | 007 Paused panel (scale 1.12) | B | Measured ink is 32.4 x 31.1 pt, wider than the 30 pt frame, so it ships at 0.9. Suggest frame 34 x 33 (then `glyph_haptic(34, 33)`). Zig-zags are a little shorter than 007's. |
| glyphMusic | done | art/ui/out/glyphMusic@3x.png | V2 t 48 s Settings | B | Seen only in V2 Settings, as a white glyph on a green button. Drawn in the phone's Paused-panel style (cream face + brown outline + drop) so all three glyphs match. The "off" red slash is not baked. |
| glyphGear | done | art/ui/out/glyphGear@3x.png | 026 gear button | B+ | Extruded light-blue side (toon3d). Teeth a little narrower than 026's. |
| glyphBell | done | art/ui/out/glyphBell@3x.png | V2 t 48 s Notifications row | B | Plain cream bell, no outline (as in V2). The reference bell is ~23 pt, the frame 20 pt. |
| unlockIconPipe | done | art/ui/out/unlockIconPipe@3x.png | 040 "Pipe! Unlocked!" | B+ | Board sprites at P = 35.5 pt (the popup uses the board's proportions exactly) plus our tube. The tube's light band is a bit stripier than 040's. The counter digit is LIVE text at (74.6, 28.0) pt. Sparkles are not baked (see note 1). |
| unlockIconLinked | done | art/ui/out/unlockIconLinked@3x.png | V1 t 78 s (scale 1.25) | B | gen_board.tape(2, "V") at P = 44 plus our glossy arrows. Drawn at 0.8 of the card size to fit the 120 x 110 frame. Arrow shafts a bit thinner than V1's. |
| unlockIconCurtain | done | art/ui/out/unlockIconCurtain@3x.png | **134 phone "Box! Unlocked!"** (scale 1.09) | B+ | SPEC §5.11: this is the **BOX** card icon (purple slab, silver sphere with 4 lugs, navy well). It is gen_board.curtain_crate at P = 34 with a larger sphere (in-process parameter override, file untouched). **The digit is LIVE text**, centred on the frame centre: please set `text_live: true`. The slab is 0.92 of 134's size; a frame of 132 x 132 would show it 1:1. Update the manifest `purpose`/`ref` (it still describes the door). |
| unlockIconElevator | done (unconfirmed) | art/ui/out/unlockIconElevator@3x.png | V2 t 1182.5 s "Elevator! Unlocked!" (scale 1.37) | B | Not on the phone. Two lavender sliding panels, drawn at 0.73 of the card size to fit the frame. Stripes a little stronger than V2's. |
| unlockIconDoor | done (unconfirmed) | art/ui/out/unlockIconDoor@3x.png | V1 t 185 s (scale 1.45) | B | gen_board.door(4, 4) + hex_lock at P = 25.5. V1's door is a little taller (about 4 x 4.5 cells). Same art family as the board door. |
| tutorialHand | done | art/ui/out/tutorialHand@3x.png | V1 t 1.2 s (scale 1.52; fingertip (193, 424) pt) | B- | Yellow emoji-style hand, as V1 shows it (the manifest said "white"). Fingertip = **(15.4, 3.6) pt of the frame** (the app scales the hand about it). Measured hand is **70 x 100 pt without the shadow**, and the manifest frame is 60 x 70. Please set the frame to **78 x 110** and the case to `tutorial_hand(78, 110)`; the generator fits any frame. Remaining: the silhouette is chunkier and more boxy than the reference, and the knuckle bumps show more. |
| rankBadgeGold | done | art/ui/out/rankBadgeGold@3x.png | store 6 row 1 (scale 1.19) | B+ | Rank number is LIVE text at the frame centre (cream #FCE6D7, outline #76001B). |
| rankBadgeSilver | done | art/ui/out/rankBadgeSilver@3x.png | store 6 row 2 | B+ | Number outline navy #263A70. |
| rankBadgeBronze | done | art/ui/out/rankBadgeBronze@3x.png | store 6 row 3 | B+ | |
| rankBadgePlain | done | art/ui/out/rankBadgePlain@3x.png | store 6 (no plain badge captured) | B | Colours derived from the HUD blue family; not seen in a capture. |
| logoArrowOut | done | art/ui/out/logoArrowOut@3x.png | 049 L36 win splash | B | **OUR lettering**: "ARROW" / "OUT!" in PC Display glyphs placed along the arch, inflated, extruded, glossed, in the original's layout (arched blue plate + white rim, pegs, purple arrow plate). Five letters need 0.70 horizontal compression. Extrusion shallower and letters a bit less chunky than the original. The original logo on 049 is ~312 x 250 pt and spills past the manifest box. Brand art, not translated. |
| heartInfiniteSmall | done | art/ui/out/heartInfiniteSmall@3x.png | 026 Claw bar | B+ | The duration ("30m") is LIVE text centred at (23, 29) pt. |
| iconHexArrow | done | art/ui/out/iconHexArrow@3x.png | 026 Claw bar | B+ | The key-ring hook seen on 026 is part of the bar, not this icon. |
| iconCheckeredFlag | done | art/ui/out/iconCheckeredFlag@3x.png | 016 Streak Race strip | B | 016's flag has larger checks (3 x 2) and a paler pole. |
| scoreChip | done | art/ui/out/scoreChip@3x.png | store 6 rows | C+ | Capsule leaner/smaller than store 6's. The plate is one warm-dark tint (#7A2E00 at 0.55) that suits the gold/bronze rows only; the silver row's plate is blue. Recommend the plate as SwiftUI (row-tinted) with a capsule-only asset, or a variant `scoreChipBlue`. The score is LIVE text at (45, 18) pt. |
| sunburstRays | done | art/ui/out/sunburstRays@3x.png | 023 Claw reward card | B | White rays, alpha only (the card colour shows through). |
| prizeSign | done | art/ui/out/prizeSign@3x.png | 069 Sky Jump | B | "PRIZE" + amount are LIVE text centred at (54, 25) pt (turned -17°). The arrow head is smaller than 069's. |
| iconPencil | done | art/ui/out/iconPencil@3x.png | V2 t 70 s Profile edit disc | B | The manifest's web-frame ref is unreadable (blurred), so V2's orange disc was used. |
| pointerArrowYellow | done | art/ui/out/pointerArrowYellow@3x.png | 025 Claw info | B+ | |
| infoPathIcon | done | art/ui/out/infoPathIcon@3x.png | 025 Claw info | B | Same tile, colours and arrow grammar as 025. The path layout is ours, not 025's. |
| statFirstTryIcon | done | art/ui/out/statFirstTryIcon@3x.png | V2 t 70 s General Stats | B | |
| statWeeklyWinsIcon | done | art/ui/out/statWeeklyWinsIcon@3x.png | V2 t 70 s General Stats | B | The "1" is baked (our font's glyph): a fixed part of the medal, not translatable. |
| boardTrailStar | done (fx) | art/ui/out/boardTrailStar@3x.png | store 1 trail stars | A- | Pure white, tinted at runtime. |
| sparkleTwinkle | done (fx) | art/ui/out/sparkleTwinkle@3x.png | 020 / unlock cards | B+ | 4-point white star with a warm glow. |
| doorShards | done (fx) | art/ui/out/doorShards@3x.png | 028 (door colours, STYLE §A.2) | B | 6 shards in a 3 x 2 grid of 16 pt cells; shard i centre = (8 + 16 (i % 3), 16 + 16 (i // 3)) pt. Not compared frame by frame with the break clip. |
| pipeShards | done (fx) | art/ui/out/pipeShards@3x.png | V2 t 560 s (tube colours) | B | Same layout as doorShards; cyan glass. |
| heartHUD | done (spike, untouched) | art/ui/out/heartHUD@3x.png | 003 | — | Not rebuilt by this lane. |

### Notes for the other lanes
1. **Unlock-card sparkles are not baked.** In the original they twinkle in a loop (research/motion.md "Feature unlock").
   The FX / shell lane places `sparkleTwinkle` sprites around the icon.
2. **Live-text anchor points** (frame pt, origin top-left): heartLives (17, 15.5); heartInfiniteSmall (23, 29);
   unlockIconPipe counter (74.6, 28.0); unlockIconCurtain/Box well = frame centre (60, 55); rank badges = frame centre;
   scoreChip (45, 18); prizeSign (54, 25) at -17°.
3. **Frame-size requests** (the generators are parametric, so each is a one-line change in `CASES`):
   tutorialHand 78 x 110 (measured 70 x 100 without the shadow); glyphHaptic 34 x 33; unlockIconCurtain (Box) 132 x 132.
   Until then the app scales those assets up, which softens them slightly.
4. The glyph style (cream face, dark-brown outline, solid drop) is the house label style (fonts.md §6). If the Settings
   screen puts these glyphs on green buttons, they still read.

## Verification
- `art_batch.py --manifest build/ui-art/lane_svg/MANIFEST.json --ids <38 ids>` → 38 OK, "all built entries verified"
  (last full run 07:02).
- `manifest_check.py --manifest build/ui-art/lane_svg/MANIFEST.json` → all 38 `ok` (status still `todo` in the manifest
  until merged). The 14 failures in that run belong to 3d entries of other lanes.
- Every entry was looked at on its side-by-side sheet at game size, and on the in-place overlay where the reference box
  allows it.

## Corrected refs for the manifest merge (JSON; `_entry` = entry-level fields)
```json
{"unlockIconCurtain":{"shot":"research/shots/134-L050-box-unlock.png","box_pt":[127,351,267,471],"scale":1.09},
 "unlockIconLinked":{"video":"research/video/owner/V1-levels-01-20.mp4","t":78.0,"box_pt":[118,348,274,470],"scale":1.25},
 "unlockIconDoor":{"video":"research/video/owner/V1-levels-01-20.mp4","t":185.0,"box_pt":[92.9,262.3,305.4,481.2],"scale":1.45},
 "unlockIconPipe":{"shot":"research/shots/040-L35-pipe-unlocked.png","box_pt":[117.8,340.4,273.8,464.4]},
 "unlockIconElevator":{"video":"research/video/owner/V2-levels-11-38.mp4","t":1182.5,"box_pt":[110,348,282,470],"scale":1.37},
 "iconCoin":{"shot":"research/shots/003-L32-start.png","box_pt":[15,27,45,57],"scale":0.89},
 "iconPlusGreen":{"shot":"research/shots/013-L32-popup.png","box_pt":[38,84,58,104],"scale":1.17},
 "iconStopwatch":{"shot":"research/shots/003-L32-start.png","box_pt":[90.7,76.5,123.7,109.5]},
 "iconStopwatchSmall":{"shot":"research/shots/026-home-after-L32.png","box_pt":[162,146,180,172]},
 "heartHUDLost":{"shot":"research/shots/110-L047-after-bump.png","box_pt":[272.1,80.6,303.1,107.6]},
 "heartLives":{"shot":"research/shots/026-home-after-L32.png","box_pt":[212.5,53,251.5,86],"scale":1.1},
 "glyphSound":{"shot":"research/shots/007-L32-pause.png","box_pt":[74,331,104,361]},
 "glyphHaptic":{"shot":"research/shots/007-L32-pause.png","box_pt":[74,403,105,435],"scale":1.12},
 "glyphMusic":{"video":"research/video/owner/V2-levels-11-38.mp4","t":48.0,"box_pt":[168,300,238,360]},
 "glyphBell":{"video":"research/video/owner/V2-levels-11-38.mp4","t":48.0,"box_pt":[52,170,82,200]},
 "glyphGear":{"shot":"research/shots/026-home-after-L32.png","box_pt":[341.3,55.4,367.3,81.4]},
 "tutorialHand":{"video":"research/video/owner/V1-levels-01-20.mp4","t":1.2,"box_pt":[176,410,276,535],"scale":1.52,"anchor_pt":[193,424]},
 "rankBadgeGold":{"shot":"research/store/iphone-6.png","box_pt":[14,581,56,621],"scale":1.19},
 "rankBadgeSilver":{"shot":"research/store/iphone-6.png","box_pt":[14,661,56,701],"scale":1.19},
 "rankBadgeBronze":{"shot":"research/store/iphone-6.png","box_pt":[14,740,56,780],"scale":1.19},
 "rankBadgePlain":{"shot":"research/store/iphone-6.png","box_pt":[14,740,56,780],"scale":1.19},
 "iconPencil":{"video":"research/video/owner/V2-levels-11-38.mp4","t":70.0,"box_pt":[130,225,160,255]},
 "iconHexArrow":{"shot":"research/shots/026-home-after-L32.png","box_pt":[30,106,78,150]},
 "statFirstTryIcon":{"video":"research/video/owner/V2-levels-11-38.mp4","t":70.0,"box_pt":[110,368,144,402]},
 "statWeeklyWinsIcon":{"video":"research/video/owner/V2-levels-11-38.mp4","t":70.0,"box_pt":[248,368,278,406]},
 "_entry":{"tutorialHand":{"anchor_pt":[15.4,3.6]},"unlockIconCurtain":{"text_live":true}}}
```
