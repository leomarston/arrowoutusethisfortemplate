# Video levels, batch C (levels 21-30, V2)

Author: level extractor, batch C, 2026-09-25. The owner calls the game **Arrow Out**; the videos show the original "Maze Out!". I used the
videos only as content: I looked at the frames and measured them. No frame is shipped or traced.

**Result: all ten boards are extracted, and every check passes.**
- **Ink:** 1-px-tolerance ink IoU is 0.9875-0.9952 with a renderer that matches the video's look.
- **Replay:** every arrow's exit on all ten boards was checked, 380 events in all, with 0 contradictions.
- **Solver:** every board clears. None of 30 random move orders per board gets stuck.
- **Grid:** pitch follows clamp(393/(cols+2)) within 0.05 pt, which confirms each `cols`.
- **Phone:** L21 = phone L35 and L26 = phone L45, cell for cell.

**Hand fixes on three boards (the reader's errors):**
- **L29 was missing a whole 10-cell arrow.** It sits inside a pipe's L corner. vextract's IoU excludes the pipe's whole bounding box,
  so the arrow never showed up there. It appeared only as a "0 heads" anomaly.
- **The reader cut pipe legs short.** It ended legs at the badge cell or one cell before the mouth ring. That cost 10 pipe cells:
  3 in L23 (both pipes), 2 in L25 (both pipes) and 5 in L29 (all three pipes). L21 and L22 were right.

Levels L21, L22, L24, L26, L27, L28 and L30 needed no edit.

Files:
- `research/levels/L021.json` … `L030.json`: final files in the phone schema, with `source:"video"`, `video:"V2"`, `t` and `frame`, and
  a `batchC` block.
  - `batchC` holds the start frame, fixes, both IoUs, the replay stats, the solver, the grid rule, play facts (timer, hearts,
    reward, popups) and the obstacle timelines.
  - `tag` uses the phone's strings: `"Hard Level"` for L25, `"Super Hard"` for L29. `timer_s` is 180 and `hearts` is 3 everywhere.
- `research/levels/video/ccheck/`: the batch-C tools.
  - `chk.py`: `verify` / `verify2` / `solve` / `rounds`.
  - `obst.py`: obstacle presence plus a counter-OCR timeline.
  - `corr.py`: model passes and counters against the video.
  - `fix.py`: the hand edits, replayable from `*.orig.json`.
  - `build.py`: writes the final files.
  - `grid.py`, `sbs.py`: frame + cell-grid and frame | overlay pictures.
- `research/video-frames/work/levelsC/` (gitignored):
  - per level: `V2-L0NN.json` (working copy), `.orig.json` (the index extraction, for L23/L25/L29), `-overlay.png` / `-overlay2.png`,
    `-verify2.json`, `-replay.json`, `-obst.json`, `-events.json`;
  - counter-crop sheets `V2-L0NN-obst*-counter-sheet.png`: obst.py writes them here when it is re-run. This session's sheets were
    kept in scratch only.

## How each level was checked
1. **Start frame.** I used the index's clean start frame, the last frame at least 0.1 s before the first tap, full resolution. I
   looked at all ten on one sheet: HUD 3:00, 3 hearts, no popup, no hand, no touch disc. L25 shows the red "Hard Level" tab and
   L29 the purple "Super Hard" tab. The board is fully built on every frame, the build-in animation long finished.
2. **Overlay read by eye.**
   - Frame | overlay side by side, both halves of every board at 1:1.
   - Zooms (2-5x) on every pipe, box, tie, spiral and residual blob.
   - Every pipe checked on the raw frame with the cell grid drawn over it (`grid.py`).
3. **Ink IoU, two ways.**
   - **vextract.verify** (the index tool, target >= 0.97 at 1-px tolerance). Four boards come in just under: L21 0.9678, L23
     0.9657, L27 0.9642, L30 0.9690.
   - **Why they fall short:** the residual is geometry. Heads are drawn as sharp triangles (the video's are rounded), corners are
     unrounded (the video's outer radius is about 1 stroke), and the render sits at a fixed 0.5-1 px offset.
   - **video-skin render** (`chk.py verify2`) fixes that geometry: 3x supersampling, corner arcs, rounded heads, and a fitted
     sub-px offset, pitch scale and stroke.
   - It also excludes obstacles **per cell** (±0.7 pitch) instead of per bounding box, so arrows inside an L/U pipe or next to a
     box are scored.
   - All ten land at 0.9875-0.9952.
   - **Residual blobs:** every missed or extra blob of 10 px or more is listed with its "thickness" (px / longest side). Slivers
     score about 1-2.
   - **Negative control** on L25 and L29: reversing 2 arrows each leaves 77-114 px compact blobs (thickness about 5), while the
     board IoU only drops 0.004.
   - On the final boards, the largest compact blob is 22 px (L21, at arrow 18's head tip: the fitted tip is a little long for that
     head) and 0 on the other nine.
   - The largest blob of any kind is 153 px: L21, a 1-px sliver along a 150-px stroke edge.
4. **Replay** (`vextract.py replay V2 N --json levelsC/V2-L0NN.json`) on the final JSONs: 0 contradictions on all ten, 0 arrows left
   at the end.
5. **Solver** (`chk.py solve`):
   - It uses research/bot/bot.py `ray()` for rays and pipe teleports, plus Linked bundles (a bundle moves when every member's ray is
     clear), box counters (every removed arrow counts, bundle members each) and pipe counters (one per pass).
   - Greedy clears all ten.
   - Move order cannot dead-end the pipe-free boards: removing an arrow or lowering a counter never blocks anything. On the pipe
     boards, 30 random free-move orders each never got stuck. Only the clock or hearts can fail a level.
   - `rounds` = dependency depth: remove every free unit per round. The results: L21 10, L22 10, L23 18, L24 10, L25 24 (Hard),
     L26 12, L27 16, L28 14, L29 29 (Super Hard), L30 7.
6. **Obstacles against the video** (`obst.py` + `corr.py`):
   - Every box and pipe was sampled at 3-10 fps. For each: presence (the break time) and the badge read by Vision OCR whenever the
     crop changed.
   - The readings were matched to the model's removal and pass timeline. **All 234 box-badge and 23 pipe-badge readings agree.**
   - Every break falls on the model's removal or pass that takes the counter to 0.
   - Allowances: Vision swaps this font's 9 and 6; the replay stamps an exit whose touch was not detected at the next tap's sync
     frame; and one reading (L28 928.06) is explained by hand.
   - "Replay time" in the per-level lists is the tap time. For an exit whose touch the index did not map, it is the later sync
     frame; the real taps are given in the Notes where it matters.
7. **Grid rule:** measured pitch against clamp(393/(cols+2), 14.04, 28.07) pt. The difference is -0.001 to -0.048 pt on all ten.

## Rules and timings measured here (for SPEC / the motion lane)
- **Box** (V2 skin: cyan block with a bomb and a white counter; L25, L27, L28):
  - every removed arrow lowers **every** box's counter by 1, and all boxes step on the same frame;
  - a Linked bundle lowers it by its member count (L28: 10 -> 7 and 38 -> 35 on one tap);
  - the step happens **at the tap** (L27: touch-down disc at 840.104, the badge reads 31 at 840.121);
  - the box breaks on the removal that makes it 0 and is gone within about 0.2-0.6 s (4-fps sampling);
  - its cells are then empty board cells (dots), and nothing is hidden under a box (checked after all 8 breaks).
- **Pipe** (L21, L22, L23, L25, L29):
  - a ray that enters a mouth against its outward direction leaves by the other mouth in that mouth's direction (bot.py rule);
  - a ray that hits the tube anywhere else is blocked;
  - each arrow that passes lowers the counter by 1, about **0.42 s after the tap** for an arrow that starts next to the mouth
    (L23: 616.673 -> 617.089 and 636.072 -> 636.489, 30-fps crops);
  - the pass that would take it to 0 does not show "0". The pipe **shatters** about 0.35-0.46 s after that tap, as the arrow leaves
    the far mouth (L21 532.137 -> shards at 532.59, L22 555.979 -> 556.43):
    - light-cyan glass shards scatter and fall under gravity;
    - the badge disc and the mouth rings tumble down as bigger pieces;
    - it lasts about 0.7 s;
  - the cells then show empty-cell dots, with no arrows under any pipe (checked after all 10 breaks);
  - counters seen: 2 (L21), 1 and 1 (L22), 3 (L23, L25, L29).
- **Pipe geometry:**
  - the **mouth ring is a pipe cell**: the leg's end cell, where the ray enters;
  - the round counter **badge** sits on the tube cell next to a mouth (L21 and L22 on the horizontal mouth, L23 top on the right
    leg, L23 bottom and L25 both on a vertical leg, L29 on the lower leg of every L);
  - the phone's L35 (= V2 L21) agrees.
- **Linked ties** (L23, L24, L28): 3-arrow bundles under a pink X tie, perpendicular to the arrows.
  - In the model, a bundle can go only when every member's ray is clear.
  - In the video, bundles leave together (e.g. L24 32/34/36).
  - No blocked bundle was tapped in L21-L30, so a bundle's bump was never seen here.
- **Hard / Super Hard** (L25 / L29): no popup, no timer change (3:00), rewards 60 and 100 (normal 20). The HUD adds a red "Hard
  Level" or purple "Super Hard" tab over the timer pill, with back and pause in the same colour.
- **No idle hint:** in L28 (19.6 s without a tap) and L29 (28.9 s), nothing appears on the board: no hand, no pulse, no highlight.
- **Tutorials in 21-30:** only the unlock popup before L21: "Pipe! / Unlocked! / Pass arrows through the PIPE to break it!", icon a U
  pipe with a "3" badge.
  - The board is built dimmed under it. tutorials.md §6 already covers the layout and dismissal.
  - New timing: board revealed at 528.83 s; the player's first board tap came at 530.75 s, 1.9 s after the dismiss.
  - No hand or caption on any of L21-L30.


## Notes for other lanes
- **Other extractions (L31-L38 video, and any tool reuse):**
  - vextract's pipe `ends` can stop at the badge cell or one cell before the mouth ring. Check every pipe against the frame with
    the grid drawn (`ccheck/grid.py`).
  - Its IoU excludes whole obstacle bounding boxes, so an arrow inside an L/U pipe or beside an elevator/box can be missing
    unnoticed. Use `CELL_EXCL=0.7 ccheck/chk.py verify2` and look at any blob of 100 px or more.
  - Relevant boards: V2 L35 and L38 have pipes; L33 and L37 have boxes.
- **Index:**
  - The 30-fps touch detector missed the tap on L29 arrow 67 at about 1080.95 s: the disc landed on the cyan pipe mouth.
  - The falling mouth ring after a pipe shatter is detected as touch discs (L21 532.81-533.14, 4 fake taps).
  - The replay's `counter_mismatch` flags on L25 are sync-order artifacts; see L25 Notes.
- **Numbering (open, the orchestrator's call):**
  - These files follow the video's order (L21-L30), as instructed.
  - v552 moved video L21 to phone L35 and video L26 to phone L45. If phone L32+ is shipped as recorded, those two boards appear
    twice.
  - Timers differ for the same board: video L26 3:00, phone L45 2:30.

## L21

- **Source:** V2, start frame t=530.644 s (8:50.64), `research/video-frames/V2/L021-start.png`; first tap 8:50.75, board cleared 9:07.04, win 9:07.68. Board 12 x 18 cells, pitch 28.030 pt (rule clamp(393/(cols+2)) = 28.070 pt, diff -0.040), stroke 5.97 pt, origin (41.66, 198.84) pt.
- **Arrows:** 20 (down 4, right 11, up 5); length min/median/max 2/6/41 cells, 165 cells in all. Dependency depth 10 rounds (all free units removed per round: [1, 1, 3, 2, 4, 2, 1, 2, 3, 1]).
- **Obstacles:** pipe counter 2, 15 cells, mouths (6,0) out left, (11,9) out down.
- **Timer / hearts / tag / reward:** 3:00 at start (clock starts at the first tap), 3 hearts start and end (no heart lost), tag null, timer at clear 2:44, reward 20 coins; 24 taps, 0 booster taps.
- **Tutorial / popup:** before the level, the unlock popup "Pipe! / Unlocked! / Pass arrows through the PIPE to break it!".
  - Its icon is a U pipe with a "3" badge.
  - Timeline: shown 525.99-528.80 s, over a dark frame from 525.50; board revealed 528.83; first board tap 530.75.
  - The board is built dimmed under the popup. There is no hand, no caption and no in-board hint afterwards.
- **Ink IoU:** vextract 0.7908 raw / **0.9678** with 1-px tolerance; video-skin render 0.9035 / **0.9879**; largest residual blob 153 px, largest compact blob 22 px (a reversed head leaves 77-114 px).
- **Replay:** 24 taps, 20 mapped, 20 exits on FREE arrows, 0 exits without a detected tap (all FREE), 4 misses; **20 consistent, 0 contradictions**, 0 arrows left at the end.
- **Solver:** greedy clears it in 20 moves (20 units); 0 of 30 random free-move orders get stuck (0/30 stuck).
- **Phone (v552):** = phone L035: 20/20 arrows and the pipe (cells, ends) identical, shift (0,0); pitch 28.03 vs 28.09 pt; phone timer 3:00, pipe counter 2 (phone clip S1-L35-pipe-first: 2->1).
- **Fixes:** none. The overlay was read by eye and the index extraction was right, cell for cell.
  - pipe (obstacle 0, counter 2): passes (replay time, arrows) 530.745 [7]; 532.137 [0]; video badge 2@530.59, 1@531.19; shattered by 532.89.
- **Notes:** the 4 replay "misses" (532.81-533.14 s, x 529 px, y 744 -> 1101 px) are not touches. They are the pipe's bottom mouth ring falling after the shatter: the grey ring reads as a touch disc (frames 532.60-533.30 checked).

## L22

- **Source:** V2, start frame t=555.878 s (9:15.88), `research/video-frames/V2/L022-start.png`; first tap 9:15.98, board cleared 9:48.00, win 9:48.64. Board 14 x 23 cells, pitch 24.559 pt (rule clamp(393/(cols+2)) = 24.562 pt, diff -0.003), stroke 4.65 pt, origin (36.56, 166.98) pt.
- **Arrows:** 29 (down 5, left 7, right 10, up 7); length min/median/max 2/6/23 cells, 245 cells in all. Dependency depth 10 rounds (all free units removed per round: [6, 5, 4, 3, 2, 3, 2, 2, 1, 1]).
- **Obstacles:** pipe counter 1, 12 cells, mouths (0,4) out up, (5,10) out right; pipe counter 1, 12 cells, mouths (5,12) out right, (0,18) out down.
- **Timer / hearts / tag / reward:** 3:00 at start (clock starts at the first tap), 3 hearts start and end (no heart lost), tag null, timer at clear 2:28, reward 20 coins; 29 taps, 0 booster taps.
- **Tutorial / popup:** none (no popup, no hand, no caption)
- **Ink IoU:** vextract 0.8451 raw / **0.9724** with 1-px tolerance; video-skin render 0.9090 / **0.9908**; largest residual blob 24 px, largest compact blob 0 px (a reversed head leaves 77-114 px).
- **Replay:** 29 taps, 29 mapped, 29 exits on FREE arrows, 0 exits without a detected tap (all FREE), 0 misses; **29 consistent, 0 contradictions**, 0 arrows left at the end.
- **Solver:** greedy clears it in 29 moves (29 units); 0 of 30 random free-move orders get stuck (0/30 stuck).
- **Fixes:** none. The overlay was read by eye and the index extraction was right, cell for cell.
  - pipe (obstacle 0, counter 1): passes (replay time, arrows) 562.635 [15]; video badge 1@555.83; shattered by 563.13.
  - pipe (obstacle 1, counter 1): passes (replay time, arrows) 555.979 [16]; video badge 1@555.83; shattered by 556.73.
- **Notes:** both pipes are single-use (counter 1). The level's first tap sent arrow 16 into the lower pipe's right mouth (obstacle 1), and that pipe shattered 0.35-0.45 s later. Arrow 16 left through the bottom mouth (0,18), straight down.

## L23

- **Source:** V2, start frame t=599.471 s (9:59.47), `research/video-frames/V2/L023-start.png`; first tap 9:59.57, board cleared 10:42.17, win 10:42.81. Board 16 x 22 cells, pitch 21.785 pt (rule clamp(393/(cols+2)) = 21.833 pt, diff -0.048), stroke 3.98 pt, origin (32.74, 208.52) pt.
- **Arrows:** 41 (down 16, left 6, right 5, up 14); length min/median/max 2/6/28 cells, 317 cells in all. Dependency depth 18 rounds (all free units removed per round: [7, 5, 1, 1, 1, 1, 2, 4, 4, 1, 2, 1, 1, 2, 1, 1, 2, 4]).
- **Obstacles:** Linked tie (tape_pink) on cells [[2, 4], [3, 4], [4, 4]] -> bundle [7, 9, 12]; Linked tie (tape_pink) on cells [[11, 17], [12, 17], [13, 17]] -> bundle [32, 34, 35]; pipe counter 3, 15 cells, mouths (0,4) out down, (6,4) out down; pipe counter 3, 15 cells, mouths (9,17) out up, (15,17) out up.
- **Timer / hearts / tag / reward:** 3:00 at start (clock starts at the first tap), 3 hearts start and end (no heart lost), tag null, timer at clear 2:17, reward 20 coins; 37 taps, 0 booster taps.
- **Tutorial / popup:** none (no popup, no hand, no caption)
- **Ink IoU:** vextract 0.8168 raw / **0.9657** with 1-px tolerance; video-skin render 0.8923 / **0.9875**; largest residual blob 15 px, largest compact blob 0 px (a reversed head leaves 77-114 px).
- **Replay:** 37 taps, 36 mapped, 36 exits on FREE arrows, 1 exits without a detected tap (all FREE), 1 misses; **37 consistent, 0 contradictions**, 0 arrows left at the end.
- **Solver:** greedy clears it in 37 moves (37 units); 0 of 30 random free-move orders get stuck (0/30 stuck).
- **Fixes (pipe geometry, 3 cells added):** top U pipe: the right leg's mouth ring is on (6,4), the badge on (6,3); the reader had ended the leg at the badge, so (6,4) was added and the end moved (6,3) -> (6,4). Bottom U pipe: both mouth rings are on row 17 (badge on (15,18)); the reader had started both legs at row 18, so (9,17) and (15,17) were added and the ends moved there. Evidence: `research/video-frames/V2/L023-start.png` with the cell grid drawn over it (`ccheck/grid.py`); the rings sit centred on those cells. Replay and solver unchanged (no arrow's ray crosses those cells before the pipes break).
  - pipe (obstacle 2, counter 3): passes (replay time, arrows) 616.673 [14]; 618.367 [15]; 618.836 [16]; video badge 3@599.42, 2@617.22, 1@619.02; shattered by 619.82.
  - pipe (obstacle 3, counter 3): passes (replay time, arrows) 636.072 [40]; 636.777 [39]; 637.246 [38]; video badge 3@599.42, 2@636.62, 1@637.42; shattered by 638.02.

## L24

- **Source:** V2, start frame t=654.013 s (10:54.01), `research/video-frames/V2/L024-start.png`; first tap 10:54.13, board cleared 11:43.61, win 11:44.28. Board 17 x 27 cells, pitch 20.667 pt (rule clamp(393/(cols+2)) = 20.684 pt, diff -0.017), stroke 3.98 pt, origin (30.80, 168.64) pt.
- **Arrows:** 37 (down 6, left 15, right 8, up 8); length min/median/max 2/6/41 cells, 365 cells in all. Dependency depth 10 rounds (all free units removed per round: [9, 5, 2, 2, 3, 3, 3, 4, 3, 3]).
- **Obstacles:** Linked tie (tape_pink) on cells [[1, 1], [1, 2], [1, 3]] -> bundle [0, 1, 2]; Linked tie (tape_pink) on cells [[14, 2], [15, 2], [16, 2]] -> bundle [32, 34, 36]; Linked tie (tape_pink) on cells [[14, 23], [14, 24], [14, 25]] -> bundle [29, 30, 31]; Linked tie (tape_pink) on cells [[0, 24], [1, 24], [2, 24]] -> bundle [10, 11, 15].
- **Timer / hearts / tag / reward:** 3:00 at start (clock starts at the first tap), 3 hearts start and end (no heart lost), tag null, timer at clear 2:11, reward 20 coins; 28 taps, 0 booster taps.
- **Tutorial / popup:** none (no popup, no hand, no caption)
- **Ink IoU:** vextract 0.8131 raw / **0.9717** with 1-px tolerance; video-skin render 0.9006 / **0.9952**; largest residual blob 14 px, largest compact blob 0 px (a reversed head leaves 77-114 px).
- **Replay:** 28 taps, 28 mapped, 28 exits on FREE arrows, 3 exits without a detected tap (all FREE), 0 misses; **31 consistent, 0 contradictions**, 0 arrows left at the end.
- **Solver:** greedy clears it in 29 moves (29 units); 0 of 30 random free-move orders get stuck (0/30 stuck).
- **Fixes:** none. The overlay was read by eye and the index extraction was right, cell for cell.

## L25

- **Source:** V2, start frame t=712.746 s (11:52.75), `research/video-frames/V2/L025-start.png`; first tap 11:52.86, board cleared 13:12.30, win 13:12.94. Board 19 x 30 cells, pitch 18.687 pt (rule clamp(393/(cols+2)) = 18.714 pt, diff -0.027), stroke 3.98 pt, origin (27.97, 166.45) pt.
- **Arrows:** 61 (down 20, left 11, right 15, up 15); length min/median/max 2/6/32 cells, 511 cells in all. Dependency depth 24 rounds (all free units removed per round: [10, 6, 4, 2, 1, 1, 2, 1, 2, 2, 3, 3, 3, 2, 2, 3, 1, 2, 1, 3, 2, 2, 2, 1]).
- **Obstacles:** box counter 24 on cols 8-10 rows 0-3; box counter 57 on cols 8-10 rows 13-16; box counter 36 on cols 8-10 rows 26-29; pipe counter 3, 11 cells, mouths (13,0) out left, (18,5) out down; pipe counter 3, 11 cells, mouths (5,29) out right, (0,24) out up.
- **Timer / hearts / tag / reward:** 3:00 at start (clock starts at the first tap), 3 hearts start and end (no heart lost), tag "Hard Level", timer at clear 1:40, reward 60 coins; 60 taps, 0 booster taps.
- **Tutorial / popup:** none (no popup, no hand, no caption)
- **Ink IoU:** vextract 0.8142 raw / **0.9747** with 1-px tolerance; video-skin render 0.9057 / **0.9925**; largest residual blob 12 px, largest compact blob 0 px (a reversed head leaves 77-114 px).
- **Replay:** 60 taps, 55 mapped, 55 exits on FREE arrows, 6 exits without a detected tap (all FREE), 5 misses; **61 consistent, 0 contradictions**, 0 arrows left at the end; 4 box/pipe breaks seen.
- **Solver:** greedy clears it in 61 moves (61 units); 0 of 30 random free-move orders get stuck (0/30 stuck).
- **Fixes (pipe geometry, 2 cells added):** top-right pipe: the bottom mouth ring is on (18,5), the badge on (18,4), so (18,5) was added and the end moved (18,4) -> (18,5). Bottom-left pipe: the right mouth ring is on (5,29), so (5,29) was added and the end moved (4,29) -> (5,29).
  - box (obstacle 0, counter 24): model reaches 0 on removal #24 (arrows [57], replay time 757.512); video: box gone by 757.95; 25 badge readings, 0 unexplained.
  - box (obstacle 1, counter 57): model reaches 0 on removal #57 (arrows [15], replay time 789.838); video: box gone by 790.20; 58 badge readings, 0 unexplained.
  - box (obstacle 2, counter 36): model reaches 0 on removal #36 (arrows [25], replay time 769.381); video: box gone by 768.95; 37 badge readings, 0 unexplained.
  - pipe (obstacle 3, counter 3): passes (replay time, arrows) 761.235 [56]; 763.076 [59]; 764.317 [60]; video badge 2@761.70, 1@763.45; shattered by 764.20.
  - pipe (obstacle 4, counter 3): passes (replay time, arrows) 778.202 [7]; 778.772 [6]; 780.868 [1]; video badge 3@712.70, 2@778.70, 1@779.45; shattered by 781.95.
- **Notes:** the replay flags 2 "counter_mismatch" events (box 36 "broke at 35", pipe "broke after 2 passes"). Both come from the replay's sync order: it checks obstacles before it removes the arrows that left without a mapped tap in the same frame. The taps that did it are the "misses" 762.777 / 763.196 (arrows 59 / 60, whose touch discs sit 0.75 cell right of column 18) and 767.874 / 768.344 (arrows 21 / 25). With those taps the badge readings are exact: pipe 3 -> 2 at 761.70, 1 at 763.45, shatter by 763.95; box 36 -> 2 at 767.70, 1 at 767.95, break at 768.45 on removal #36. The three boxes count down together, one step per removed arrow (all 117 box-badge readings agree; Vision reads this font's 9 as 6 and back).

## L26

- **Source:** V2, start frame t=801.206 s (13:21.21), `research/video-frames/V2/L026-start.png`; first tap 13:21.31, board cleared 13:51.03, win 13:51.67. Board 15 x 19 cells, pitch 23.075 pt (rule clamp(393/(cols+2)) = 23.118 pt, diff -0.043), stroke 4.65 pt, origin (34.62, 229.76) pt.
- **Arrows:** 26 (down 7, left 6, right 2, up 11); length min/median/max 4/7/47 cells, 283 cells in all. Dependency depth 12 rounds (all free units removed per round: [4, 2, 3, 2, 1, 1, 3, 2, 3, 2, 2, 1]).
- **Obstacles:** none.
- **Timer / hearts / tag / reward:** 3:00 at start (clock starts at the first tap), 3 hearts start and end (no heart lost), tag null, timer at clear 2:30, reward 20 coins; 26 taps, 0 booster taps.
- **Tutorial / popup:** none (no popup, no hand, no caption)
- **Ink IoU:** vextract 0.8479 raw / **0.9824** with 1-px tolerance; video-skin render 0.9171 / **0.9903**; largest residual blob 23 px, largest compact blob 0 px (a reversed head leaves 77-114 px).
- **Replay:** 26 taps, 26 mapped, 26 exits on FREE arrows, 0 exits without a detected tap (all FREE), 0 misses; **26 consistent, 0 contradictions**, 0 arrows left at the end.
- **Solver:** greedy clears it in 26 moves (26 units); 0 of 30 random free-move orders get stuck (0/30 stuck).
- **Phone (v552):** = phone L045: 26/26 arrows identical, shift (0,0); pitch 23.075 vs 23.115 pt; phone timer 2:30 (video 3:00).
- **Fixes:** none. The overlay was read by eye and the index extraction was right, cell for cell.

## L27

- **Source:** V2, start frame t=840.004 s (14:00.00), `research/video-frames/V2/L027-start.png`; first tap 14:00.10, board cleared 14:53.98, win 14:54.61. Board 16 x 26 cells, pitch 21.819 pt (rule clamp(393/(cols+2)) = 21.833 pt, diff -0.014), stroke 3.98 pt, origin (32.44, 164.61) pt.
- **Arrows:** 40 (down 7, left 8, right 13, up 12); length min/median/max 2/9/21 cells, 375 cells in all. Dependency depth 16 rounds (all free units removed per round: [7, 4, 3, 3, 1, 3, 3, 2, 2, 2, 1, 1, 2, 2, 2, 2]).
- **Obstacles:** box counter 32 on cols 6-9 rows 0-2; box counter 25 on cols 0-2 rows 11-14; box counter 18 on cols 13-15 rows 11-14.
- **Timer / hearts / tag / reward:** 3:00 at start (clock starts at the first tap), 3 hearts start and end (no heart lost), tag null, timer at clear 2:06, reward 20 coins; 41 taps, 0 booster taps.
- **Tutorial / popup:** none (no popup, no hand, no caption)
- **Ink IoU:** vextract 0.8039 raw / **0.9642** with 1-px tolerance; video-skin render 0.8936 / **0.9911**; largest residual blob 20 px, largest compact blob 0 px (a reversed head leaves 77-114 px).
- **Replay:** 41 taps, 40 mapped, 40 exits on FREE arrows, 0 exits without a detected tap (all FREE), 1 misses; **40 consistent, 0 contradictions**, 0 arrows left at the end; 3 box/pipe breaks seen.
- **Solver:** greedy clears it in 40 moves (40 units); 0 of 30 random free-move orders get stuck (0/30 stuck).
- **Fixes:** none. The overlay was read by eye and the index extraction was right, cell for cell.
  - box (obstacle 0, counter 32): model reaches 0 on removal #32 (arrows [19], replay time 888.476); video: box gone by 888.95; 33 badge readings, 0 unexplained.
  - box (obstacle 1, counter 25): model reaches 0 on removal #25 (arrows [13], replay time 874.141); video: box gone by 874.45; 27 badge readings, 0 unexplained.
  - box (obstacle 2, counter 18): model reaches 0 on removal #18 (arrows [3], replay time 861.566); video: box gone by 861.95; 20 badge readings, 0 unexplained.
- **Notes:** box badges step down at the tap itself: tap 840.104 s, and 32 reads 31 at 840.121 (30-fps crops, `work/levelsC` sheets). All three boxes step together.

## L28

- **Source:** V2, start frame t=902.610 s (15:02.61), `research/video-frames/V2/L028-start.png`; first tap 15:02.71, board cleared 16:11.13, win 16:11.81. Board 19 x 24 cells, pitch 18.697 pt (rule clamp(393/(cols+2)) = 18.714 pt, diff -0.017), stroke 3.98 pt, origin (27.82, 222.42) pt.
- **Arrows:** 51 (down 12, left 13, right 15, up 11); length min/median/max 2/5/46 cells, 438 cells in all. Dependency depth 14 rounds (all free units removed per round: [9, 1, 1, 4, 3, 5, 7, 2, 3, 3, 2, 4, 4, 3]).
- **Obstacles:** box counter 10 on cols 16-18 rows 0-2; Linked tie (tape_pink) on cells [[1, 0], [1, 1], [1, 2]] -> bundle [0, 1, 2]; Linked tie (tape_pink) on cells [[8, 1], [9, 1], [10, 1]] -> bundle [19, 23, 27]; box counter 38 on cols 0-2 rows 21-23; Linked tie (tape_pink) on cells [[17, 21], [17, 22], [17, 23]] -> bundle [48, 49, 50]; Linked tie (tape_pink) on cells [[8, 22], [9, 22], [10, 22]] -> bundle [22, 26, 30].
- **Timer / hearts / tag / reward:** 3:00 at start (clock starts at the first tap), 3 hearts start and end (no heart lost), tag null, timer at clear 1:51, reward 20 coins; 42 taps, 0 booster taps.
- **Tutorial / popup:** none (no popup, no hand, no caption)
- **Ink IoU:** vextract 0.8203 raw / **0.9842** with 1-px tolerance; video-skin render 0.8947 / **0.9929**; largest residual blob 10 px, largest compact blob 0 px (a reversed head leaves 77-114 px).
- **Replay:** 42 taps, 39 mapped, 39 exits on FREE arrows, 4 exits without a detected tap (all FREE), 3 misses; **43 consistent, 0 contradictions**, 0 arrows left at the end; 2 box/pipe breaks seen.
- **Solver:** greedy clears it in 43 moves (43 units); 0 of 30 random free-move orders get stuck (0/30 stuck).
- **Fixes:** none. The overlay was read by eye and the index extraction was right, cell for cell.
  - box (obstacle 0, counter 10): model reaches 0 on removal #10 (arrows [29], replay time 914.330); video: box gone by 914.56; 8 badge readings, 0 unexplained.
  - box (obstacle 3, counter 38): model reaches 0 on removal #38 (arrows [0, 1, 2], replay time 962.634); video: box gone by 962.81; 33 badge readings, 0 unexplained, 1 explained by hand.
- **Notes:** the first move is a Linked bundle (22, 26, 30), and both badges drop by 3 at once (10 -> 7, 38 -> 35): every member counts. Box 38's last 6 steps are two bundles (19, 23, 27 at 960.04 s -> 3; 0, 1, 2 at 962.63 s -> 0 -> break). The player idled 19.6 s (940.4-960.0 s) and no hint, hand or pulse appeared.

## L29

- **Source:** V2, start frame t=982.469 s (16:22.47), `research/video-frames/V2/L029-start.png`; first tap 16:22.60, board cleared 19:03.18, win 19:03.76. Board 20 x 32 cells, pitch 17.844 pt (rule clamp(393/(cols+2)) = 17.864 pt, diff -0.020), stroke 3.32 pt, origin (26.55, 160.84) pt.
- **Arrows:** 68 (down 13, left 12, right 19, up 24); length min/median/max 3/6/45 cells, 608 cells in all. Dependency depth 29 rounds (all free units removed per round: [13, 4, 1, 1, 2, 1, 1, 3, 2, 2, 1, 1, 1, 2, 3, 6, 2, 2, 1, 1, 2, 1, 1, 2, 2, 4, 2, 2, 2]).
- **Obstacles:** pipe counter 3, 9 cells, mouths (0,4) out down, (4,0) out right; pipe counter 3, 9 cells, mouths (6,10) out down, (10,6) out right; pipe counter 3, 9 cells, mouths (16,12) out right, (12,16) out down.
- **Timer / hearts / tag / reward:** 3:00 at start (clock starts at the first tap), 3 hearts start and end (no heart lost), tag "Super Hard", timer at clear 0:20, reward 100 coins; 67 taps, 0 booster taps.
- **Tutorial / popup:** none (no popup, no hand, no caption)
- **Ink IoU:** vextract 0.8099 raw / **0.9812** with 1-px tolerance; video-skin render 0.8941 / **0.9945**; largest residual blob 12 px, largest compact blob 0 px (a reversed head leaves 77-114 px).
- **Replay:** 67 taps, 66 mapped, 66 exits on FREE arrows, 2 exits without a detected tap (all FREE), 1 misses; **68 consistent, 0 contradictions**, 0 arrows left at the end.
- **Solver:** greedy clears it in 68 moves (68 units); 0 of 30 random free-move orders get stuck (0/30 stuck).
- **Fixes (1 missing arrow + 5 pipe cells):**
  - **Arrow 67 added:** a 10-cell arrow inside the top-left pipe's L corner, cells (4,2) (3,2) (3,3) (3,4) (2,4) (2,3) (2,2) (2,1) (3,1) (4,1), head (4,1) pointing RIGHT. The reader had logged it only as the anomaly "arrow (2,1)-(2,4): 0 heads" and dropped it. vextract's IoU could not see it because it excludes the whole pipe bounding box, and the arrow lies inside that box. Evidence: the start frame at 5x; the video shows it leaving at 1080.95 s (a touch the index missed, next to its head), and it blocks arrow 24 (head (5,2) pointing left), which left later. The replay stays at 0 contradictions with 68 arrows (it was 67).
  - **Pipe mouths:** all three L pipes carry their badge on the cell next to the lower mouth, and the reader ended the legs at the badge or one cell short. Mouth rings sit on (0,4) and (4,0), (6,10) and (10,6), and (12,16), so those cells were added and the ends moved.
  - pipe (obstacle 0, counter 3): passes (replay time, arrows) 1133.703 [1]; 1134.173 [5]; 1134.475 [7]; video badge 2@1134.42, 1@1134.75; shattered by 1135.09.
  - pipe (obstacle 1, counter 3): passes (replay time, arrows) 1073.344 [21]; 1108.537 [29]; 1108.973 [31]; video badge 3@982.42, 2@1073.75, 1@1109.09; shattered by 1110.09.
  - pipe (obstacle 2, counter 3): passes (replay time, arrows) 1051.665 [48]; 1052.570 [49]; 1060.367 [51]; video badge 3@982.42, 2@1052.09, 1@1053.09; shattered by 1061.09.
- **Notes:** 2:40 of the 3:00 was used (0:20 left). The player idled 28.9 s (1077.2-1106.1 s, only arrow 67's unlisted tap at 1080.95 in between) and no hint appeared. The "Super Hard" tab sits on the timer pill, and back and pause are purple.

## L30

- **Source:** V2, start frame t=1152.935 s (19:12.93), `research/video-frames/V2/L030-start.png`; first tap 19:13.04, board cleared 19:32.60, win 19:33.27. Board 16 x 16 cells, pitch 21.832 pt (rule clamp(393/(cols+2)) = 21.833 pt, diff -0.001), stroke 3.98 pt, origin (32.39, 273.62) pt.
- **Arrows:** 25 (down 5, left 7, right 5, up 8); length min/median/max 2/7/25 cells, 232 cells in all. Dependency depth 7 rounds (all free units removed per round: [9, 4, 2, 4, 3, 2, 1]).
- **Obstacles:** none.
- **Timer / hearts / tag / reward:** 3:00 at start (clock starts at the first tap), 3 hearts start and end (no heart lost), tag null, timer at clear 2:40, reward 20 coins; 25 taps, 0 booster taps.
- **Tutorial / popup:** none (no popup, no hand, no caption)
- **Ink IoU:** vextract 0.8192 raw / **0.9690** with 1-px tolerance; video-skin render 0.9094 / **0.9913**; largest residual blob 14 px, largest compact blob 0 px (a reversed head leaves 77-114 px).
- **Replay:** 25 taps, 25 mapped, 25 exits on FREE arrows, 0 exits without a detected tap (all FREE), 0 misses; **25 consistent, 0 contradictions**, 0 arrows left at the end.
- **Solver:** greedy clears it in 25 moves (25 units); 0 of 30 random free-move orders get stuck (0/30 stuck).
- **Fixes:** none. The overlay was read by eye and the index extraction was right, cell for cell.

