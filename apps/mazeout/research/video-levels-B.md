# Video levels — batch B (levels 11-20, V1 + V2)

Author: level extractor batch B, 2026-09-25. Owner-facing name **Arrow Out**; the videos show the original "Maze Out!". Content only:
video frames were measured, never shipped or traced.

**Result: L11-L20 are extracted from both videos and they agree cell by cell.** All 316 arrows, all 12 boxes (with counters) and all 5
Linked ties are identical in V1 and V2. Every board passes the replay check in both videos with 0 contradictions, and both solvers
clear every board. Ink IoU (1-px tolerance) is at least 0.9808 once the render is sub-pixel registered, and at least 0.9829 for the
model. Two boards also match the phone (v552) exactly: L12 is phone L51 and L14 is phone L52.

Files:
- `research/levels/L011.json` … `L020.json`: final, phone schema, `source:"video"`, from **V2**, with `video_alt` = V1 and a `checks` block
  (V1/V2 diff, IoU, replay, solver, play facts).
- `research/levels/video/V1-L0NN.json`, `V2-L0NN.json`: per-video extractions.
- `research/levels/video/bcheck.py`: the batch-B tool: robust refit, three-way IoU with per-arrow head/tail check, two solvers, diff,
  and `final`.
- Gitignored, in `research/video-frames/work/B/`: overlays (`V?-L0NN-overlay.png`, `V?-L0NN-verifyB.png`), replay reports
  (`replay/`), verify, solve and diff JSONs, and sheets (`breaks-V1.png`, `breaks-V2.png`, `v2l13-tape.png`, `v2l11-*.png`, `v1l11-*.png`).

## How each level was checked
1. **Start frame.** The index's clean start frame (`video-frames/V?/L0NN-start.png`, full res) is the frame just before the first
   tap. For V2 L11, frames at 89.5, 90.2, 90.9 and 91.5 s read the same board as the 92.012 s start frame.
2. **Read.** `vextract read_board` plus a **robust grid refit** (bcheck `rebuild`), which does not change any cell.
   - vextract's least-squares grid fit included a few segments that are not strokes: the dark outline of V2's cyan box and the
     bases of wide arrow heads. On V2 L11 the residual was 3.56 px and the grid drifted about 1 px across the board.
   - The refit drops off-grid segments and re-solves. Residual falls to 0.19-0.48 px on all 20 boards.
   - Every rebuilt board equals the index agent's extraction arrow for arrow (20/20 boards). Counters are kept from the index OCR.
     Every counter was also read by eye on the frames, and 8/16/23 on the phone shot of L51.
3. **Overlays read by eye**: both videos for L11, V1 for L12, V2 for L13-L20, plus both start frames of every level side by side.
   - No recognition error was found and **no hand edit was needed**.
   - The only non-arrow ink the reader reports is the dark outline of V2's L11 box A: two short edges, 42 px and 87 px, at x 85
     and y 362. It is not an arrow; see `work/B/v2l11-box.png`.
4. **Ink IoU**, three ways (bcheck `verify`):
   - **vx**: vextract.verify on the JSON's own transform.
   - **reg**: the same render moved by a sub-pixel registration. vextract draws on integer pixel centres, but it measures stroke
     centres as (start+stop-1)/2, which leaves about a 0.5 px bias.
   - **model**: `reg` plus a wider search over head size (tip 0.40-0.58 pitch, half-width 0.26-0.42). Cells never vary, so this
     scores the model.

   Residual pixels are then sorted by position:
   - **Body:** 0 clusters of 25 px or more on all 20 boards (except the V2 L11 box outline above). A missing or extra segment would
     show up as a cluster of 100 px or more.
   - **Heads and tails:** 94-100 % of the missed ink is at heads and tails on every board except V2 L11 (59 %, the box outline)
     and V2 L14 (91 %, with only 11 px on bodies). The video's heads are a little larger than the render's.
   - **Extra model ink** is scattered 1-px slivers along bodies, where the render's stroke is a hair wider.
   - **Per arrow:** the ink at each head and tail is checked. A reversed head would leave about one head triangle extra at the model
     head and one missing at the model tail. **0 arrows flagged on all 20 boards.**
   - **Negative control** (V1 L14, arrows 3 and 10 reversed): both are flagged, while the board IoU only falls from 0.9845 to 0.9711.
     A whole-board IoU of 0.97 alone would NOT catch a reversed arrow.
5. **Replay check**: `vextract.py replay` against each video, with that video's JSON; the final files are replayed against V2 again.
6. **Solver**, two ways (bcheck `solve`):
   - research/bot's greedy `plan()`, re-planned after every tap. Unbroken boxes are passed in as door cells, and every removed arrow
     lowers every counter.
   - The replay's rule model, `vextract.Model`.

   Both clear every board. Two more checks run on each board:
   - **Box slack:** the largest counter that still leaves the level solvable.
   - **Control:** with boxes that never break, every box level is unsolvable, so the counter rule is always needed.
7. **Grid size check**: the measured pitch equals the phone's fit rule, pitch = clamp(393/(cols+2), 14.04, 28.07) pt, within 0.03 pt on
   every level. That also confirms each `cols`, obstacle cells included.
8. **JSON invariants** hold on all 10 final files:
   - it has every key of the phone schema;
   - ids run 0..n-1;
   - every cell is in bounds;
   - no two arrows share a cell;
   - consecutive cells are 4-adjacent and no arrow crosses itself;
   - `dir` = the last step;
   - every box is a full rectangle with an integer counter and covers no arrow;
   - each Linked tie crosses exactly one cell of each bound arrow;
   - `cols`/`rows` fit the bounding box tightly.

## Summary

| level | grid | arrows | cells | obstacles | tag | V1 start (s) | V2 start (s) | V1 = V2 | IoU tol1 V1 vx / reg / model | IoU tol1 V2 vx / reg / model | replay V1 | replay V2 | solver (taps) | waves |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 11 | 10x20 | 14 | 128 | box 8, box 13 | - | 187.76 | 92.01 | 14/14 + obstacles | 0.9888 / 0.9896 / 0.9896 | 0.9839 / 0.9848 / 0.9855 | 16 taps; 14 ok, **0 bad**, 1 miss | 20 taps; 14 ok, **0 bad**, 5 miss | solved (14) | 5 |
| 12 | 15x21 | 24 | 224 | box 8, box 16, box 23 | - | 203.08 | 112.14 | 24/24 + obstacles | 0.9780 / 0.9825 / 0.9832 | 0.9813 / 0.9853 / 0.9853 | 23 taps; 24 ok, **0 bad**, 2 miss | 23 taps; 24 ok, **0 bad**, 0 miss | solved (24) | 10 |
| 13 | 14x18 | 33 | 216 | box 4, box 28, 2 Linked ties | - | 228.68 | 147.80 | 33/33 + obstacles | 0.9770 / 0.9833 / 0.9846 | 0.9784 / 0.9860 / 0.9875 | 26 taps; 31 ok, **0 bad**, 2 miss | 32 taps; 29 ok, **0 bad**, 3 miss | solved (29) | 12 |
| 14 | 13x16 | 15 | 180 | - | - | 262.44 | 194.94 | 15/15 | 0.9781 / 0.9841 / 0.9845 | 0.9815 / 0.9854 / 0.9859 | 15 taps; 15 ok, **0 bad**, 0 miss | 15 taps; 15 ok, **0 bad**, 0 miss | solved (15) | 5 |
| 15 | 20x25 | 48 | 465 | box 26, box 41 | - | 279.72 | 221.37 | 48/48 + obstacles | 0.9827 / 0.9896 / 0.9902 | 0.9816 / 0.9908 / 0.9908 | 44 taps; 48 ok, **0 bad**, 1 miss | 47 taps; 48 ok, **0 bad**, 2 miss | solved (48) | 11 |
| 16 | 13x15 | 24 | 195 | - | - | 320.16 | 284.65 | 24/24 | 0.9672 / 0.9824 / 0.9830 | 0.9736 / 0.9808 / 0.9829 | 21 taps; 24 ok, **0 bad**, 0 miss | 24 taps; 24 ok, **0 bad**, 0 miss | solved (24) | 10 |
| 17 | 19x24 | 54 | 453 | 3 Linked ties | - | 340.72 | 317.81 | 54/54 | 0.9701 / 0.9851 / 0.9873 | 0.9725 / 0.9867 / 0.9883 | 46 taps; 50 ok, **0 bad**, 4 miss, 1 late | 46 taps; 50 ok, **0 bad**, 3 miss | solved (48) | 14 |
| 18 | 14x17 | 22 | 226 | - | - | 391.00 | 389.94 | 22/22 | 0.9769 / 0.9878 / 0.9888 | 0.9864 / 0.9896 / 0.9897 | 21 taps; 22 ok, **0 bad**, 1 miss | 20 taps; 22 ok, **0 bad**, 1 miss | solved (22) | 10 |
| 19 | 20x31 | 62 | 575 | box 13, box 20, box 25 | Hard Level | 415.56 | 420.91 | 62/62 + obstacles | 0.9807 / 0.9920 / 0.9920 | 0.9825 / 0.9931 / 0.9931 | 58 taps; 62 ok, **0 bad**, 5 miss | 61 taps; 62 ok, **0 bad**, 2 miss | solved (62) | 25 |
| 20 | 14x20 | 20 | 279 | - | - | 475.32 | 500.20 | 20/20 | 0.9779 / 0.9836 / 0.9848 | 0.9803 / 0.9862 / 0.9869 | 19 taps; 20 ok, **0 bad**, 1 miss | 20 taps; 20 ok, **0 bad**, 0 miss | solved (20) | 9 |

Column notes:
- **ok**: replay events consistent with the model. That counts every exit on a free arrow, plus every arrow the sync found gone
  without a detected tap, which must also be free. So "ok" can exceed "taps".
- **bad**: an exit on a blocked arrow, a heart loss on a free arrow, or an arrow gone while blocked.
- **waves**: the number of rounds needed if every free unit leaves at once, a depth measure.
- **Solver taps**: one tap per unit. A Linked bundle is one unit, so L13 has 29 taps and L17 has 48.

- **Timer, hearts, result:** every level starts at 3:00 with 3 hearts. No heart was lost and no bump happened in either video. The
  clock does not run before the first tap: V2 L13 sat 6.5 s and V2 L19 4.8 s between the board appearing and the first tap, and both
  still read 3:00 at the start frame.
- **Rewards:** 20 coins, and 60 for L19 (Hard).
- **Tutorials:** no tutorial hand and no in-board caption on any of L11-L20. The only first-time moment is the **unlock popup before
  L11** (tutorials.md §6: V1 "Curtain! / Unlocked! / Clear required amount of arrows to open the CURTAIN!", 3:03.5-3:05.84; V2
  "Box! / Unlocked! / Clear required amount of arrows to break the BOX!" with a "5" box icon, 1:16.0-1:19.0), and the **first Hard
  level at L19**, with no popup (tutorials.md §7).
- **Misses in the replay** are not model problems. There are two kinds:
  - **Box-break debris.** The shards fly and fall over the board and look like touch discs. Checked on frames for V1 L11 193.48
    (`work/B/v1l11-weak.png`) and V2 L11 97.1-97.4 (`work/B/v2l11-debris.png`). The others (V1 L11 196.36, V1 L12 207.72, V2 L13
    155.54/155.88/182.94) come within 0.6 s of a break, next to or below the box.
  - **Touches just outside the replay's 0.75-cell radius.** They land 0.75-0.90 cell from an arrow, and that arrow is then found
    gone and free. So the game accepts touches at least about 0.8-0.9 cell from the stroke. This is only a hint: disc centroids are
    biased.

## Obstacle behaviour measured in these levels
### Box (V2 "Box", V1 "Curtain"): same cells, same counters, same rule
Frames: `work/B/breaks-V1.png`, `work/B/breaks-V2.png` (all 12 breaks), `v2l11-count1.png`, `v1l11-count1.png`, `v2l11-break.png`,
`v1l11-break.png`.
- **What it is:** a rectangle of cells showing its counter. In L11-L20 the sizes are 3x3, 5x3, 3x4 and 3x5, always 9-15 cells. It
  blocks rays like an arrow until it breaks. Boxes sit at the edge of the arrow block (or inside it on L15), and arrows point into
  them.
- **Counting:** the counter shows how many more arrows must be cleared. It drops by 1 for each arrow launched ANYWHERE, on the
  frame the tapped arrow starts to move, not when it finishes leaving. Examples:
  - V2 L11 92.10: the disc appears, and at 92.12 the counter already reads 7 and the arrow has moved.
  - V1 L11 187.88: both counters change 8→7 and 13→12 on the disc frame.
  - A Linked bundle lowers it by its size (V2 L13: 22 → 19 in one frame).
- **Breaking:**
  - The box shatters on the launch frame of the arrow that brings the count to 0 (V2 L11: "1" at 96.92, shattered at 96.94; V1 L11
    192.88 "1", 192.92 shattered). A "0" is never shown.
  - V2's art bursts into cyan chunks and bomb pieces. V1's art bursts into purple shards and grey lock parts. The pieces fly
    outward, then fall off the bottom with gravity. A few pieces are left at +0.5 s, and none by +1.5 s.
  - The cells then show ordinary empty grid dots. **Nothing was under any of the 12 boxes**: at +0.5 s and +1.5 s every box
    area shows only grid dots, falling debris or arrows passing through. On V1 L11 B and V1 L12 C the level had already cleared by
    +1.5 s.
  - The replay's model treats the box as gone from that launch on, and none of the 24 breaks (12 per video) disagreed with the
    video. The players always tapped an arrow behind a box at least 0.52 s after the break, so the earliest moment such an arrow
    may leave was not observed. The model's answer is "at once".
- **Skin (answers the index agent's open question 3):**
  - The phone's in-board box on L51, which is this batch's L12 (`shots/140-L051-start.png`), is the **purple slab with a silver
    ring lock, four rivets and a white counter**. That is exactly V1's in-board "Curtain" art, not V2's cyan bomb block.
  - The phone names it "Box" (unlock card at L50: "Box! … break the BOX!").
  - So the current build = V1's purple art + V2's name and caption. The V1 *popup icon* for "Curtain!" (a door-like shutter) is a
    different picture from its in-board art (tutorials.md §6).
  - L0NN.json uses `kind:"box"`. V1's JSONs keep `curtain`.

### Linked ties (L13, L17)
- The pink X tie binds three parallel arrows. One tap on any member (middle or end, both seen) launches the whole bundle, and the tie
  travels with it (rainbow/star trail in V2, `work/B/v2l13-tape.png`).
- In the model, the bundle leaves only when every member's ray is clear. All 5 bundle exits in each video were free for every
  member. No tap on a partly blocked bundle was seen, so what happens then is not in these videos.
- Each member counts toward box counters.

## Per level

### L11
- **Source frames**: V1 3:07.76 (187.76 s, `video-frames/V1/L011-start.png`); V2 1:32.01 (92.012 s, `video-frames/V2/L011-start.png`). Final JSON from V2.
- **Board**: 10x20 cells, 14 arrows, 128 arrow cells (density 0.64), arrow length 4-25 cells (median 8), heads up/down/left/right 4/1/4/5; pitch 28.046 pt (fit rule 28.070).
- **Obstacles**: box 8 (3x3), box 13 (3x3).
- **Timer / hearts / tag**: 3:00 / 3 / none. **Tutorial**: unlock popup before the level (V1 Curtain / V2 Box, see above); no hand, no caption.
- **Play in the videos**: V1 first tap 3:07.88, cleared 3:16.96 (9.1 s of video; timer 2:51 left; 16 taps); V2 first tap 1:32.13, cleared 1:41.77 (9.6 s; 2:50 left; 20 taps). Hearts 3 → 3. Reward 20.
- **V1 vs V2**: 14/14 arrows identical, obstacles identical (counters and cells), Linked ties identical; disagreements: none.
- **Ink IoU (1 px tol)**: V1 0.9888 / 0.9896 / 0.9896, V2 0.9839 / 0.9848 / 0.9855 (vx / registered / model); heads flagged 0.
- **Replay**: V1 16 taps, 14 consistent, 0 inconsistent, 1 miss, left at end none; V2 20 taps, 14 consistent, 0 inconsistent, 5 miss, left at end none. Box breaks confirmed: 2.
- **Solver**: bot plan solved (14 taps), rule model solved (14 taps); 6 units free at start; 5 waves; box slack (counter → largest solvable) 8→10, 13→13; unsolvable if boxes never break.
- **Fixes**: none to cells or arrows. The robust grid refit changed only the transform: residual 3.56 → 0.48 px.
- **Notes**: First obstacle level. Two 3x3 boxes sit OUTSIDE the arrow block: box A (8) at the top-left with arrows 0 (↑, col 0) and 7 (←, row 1) aimed at it; box B (13) at the bottom-right with arrow 9 (→, row 18) aimed at it. Box B's 13 = every other arrow, so arrow 9 is always the last one (tight: counter 14 would be unsolvable); box A has slack 2 (the level stays solvable up to counter 10). In the video: V1 box A shattered on the 8th launch (192.92), B on the 13th (≈196.16-196.20); V2 at 96.944 and 100.834. Arrows 0/7 and 9 left only after their box was gone (V1 7 @193.92, 0 @194.52, 9 @196.80; V2 0 @99.644, 7 @100.331, 9 @101.806).

```
    0         5         
  0 AAAAA . . . . . . .
  1 AAAAA <-----o . . .
  2 AAAAA . . . . . . .
  3 . . . . . . . . . .
  4 ^ +-----+ o-------+
  5 | | o-+ | ^ o ^ ^ |
  6 | +---+ +-+ | | | |
  7 +-----------+ | | |
  8 +-------------+ | |
  9 | +---------o o | |
 10 | | o o-----> +-+ |
 11 | v | o +---------+
 12 +---+ | | o o +---o
 13 <-----+ | | | +--->
 14 <-----o | | +----->
 15 <-------+ +------->
 16 . . . . . . . . . .
 17 . . . . . . . BBBBB
 18 . . . o-----> BBBBB
 19 . . . . . . . BBBBB
A = box, counter 8, cols 0-2 rows 0-2
B = box, counter 13, cols 7-9 rows 17-19
```
Legend: `o` tail, `^ v < >` head, `-` `|` straight body, `+` turn; `A`-`C` box cells; `.` empty cell. Cells are [col,row] as in the JSON.

### L12
- **Source frames**: V1 3:23.08 (203.08 s, `video-frames/V1/L012-start.png`); V2 1:52.14 (112.135 s, `video-frames/V2/L012-start.png`). Final JSON from V2.
- **Board**: 15x21 cells, 24 arrows, 224 arrow cells (density 0.71), arrow length 2-29 cells (median 9), heads up/down/left/right 6/4/1/13; pitch 23.107 pt (fit rule 23.118).
- **Obstacles**: box 8 (5x3), box 16 (5x3), box 23 (5x3).
- **Timer / hearts / tag**: 3:00 / 3 / none. **Tutorial**: none (no popup, no hand, no caption).
- **Play in the videos**: V1 first tap 3:23.20, cleared 3:38.20 (15.0 s of video; timer 2:45 left; 23 taps); V2 first tap 1:52.23, cleared 2:12.67 (20.4 s; 2:39 left; 23 taps). Hearts 3 → 3. Reward 20.
- **V1 vs V2**: 24/24 arrows identical, obstacles identical (counters and cells), Linked ties identical; disagreements: none.
- **Ink IoU (1 px tol)**: V1 0.9780 / 0.9825 / 0.9832, V2 0.9813 / 0.9853 / 0.9853 (vx / registered / model); heads flagged 0.
- **Replay**: V1 23 taps, 24 consistent, 0 inconsistent, 2 miss, left at end none; V2 23 taps, 24 consistent, 0 inconsistent, 0 miss, left at end none. Box breaks confirmed: 3.
- **Solver**: bot plan solved (24 taps), rule model solved (24 taps); 4 units free at start; 10 waves; box slack (counter → largest solvable) 8→9, 16→17, 23→23; unsolvable if boxes never break.
- **Fixes**: none to cells or arrows. The robust grid refit changed only the transform: residual 0.96 → 0.27 px.
- **Notes**: Three 5x3 boxes in a staircase along the bottom (A 8 right, B 16 middle, C 23 left). Rays into them: A ← arrows 5 and 15 (directly) + 0, 11 further back; B ← 7 (+12, 14); C ← 6 only. C = 23 = every other arrow, so arrow 6 (↓ in the bottom-left pocket) is always last. SAME BOARD AS THE PHONE'S L51 (research/levels/L051.json, read by bot.py from a black-on-white phone shot): all 24 arrows and the three box rectangles identical; the phone shot shows the counters 8 / 16 / 23 on purple slabs (V1's curtain art) and a 3:00 timer.

```
    0         5         10        
  0 +-----------+ o +-+ o o---+ ^
  1 | +-------+ o +-+ v +---+ +-+
  2 +-+ +-+ ^ +---------+ o | +->
  3 <---+ | | +-------+ | | | +-+
  4 o-----+ o +-----+ v | | +-> o
  5 +-o +-> +-----o | o | +-+ +->
  6 +---+ o | +---o o | | ^ | +-+
  7 +-----+ | | +-+ +-+ | o | . |
  8 | +---> | | | | +-> | +-+ +-+
  9 +-+ ^ ^ | | | +---> v | o-+ ^
 10 +-+ | | | +-+ +-----> +---> |
 11 | | | | +-----+ +-----------+
 12 o | o | +---> o +-o AAAAAAAAA
 13 o +---+ o +-+ +---> AAAAAAAAA
 14 +---------+ +-----> AAAAAAAAA
 15 +-+ +---> BBBBBBBBB . . . . .
 16 v o +---+ BBBBBBBBB . . . . .
 17 o-------+ BBBBBBBBB . . . . .
 18 CCCCCCCCC . . . . . . . . . .
 19 CCCCCCCCC . . . . . . . . . .
 20 CCCCCCCCC . . . . . . . . . .
A = box, counter 8, cols 10-14 rows 12-14
B = box, counter 16, cols 5-9 rows 15-17
C = box, counter 23, cols 0-4 rows 18-20
```
Legend: `o` tail, `^ v < >` head, `-` `|` straight body, `+` turn; `A`-`C` box cells; `.` empty cell. Cells are [col,row] as in the JSON.

### L13
- **Source frames**: V1 3:48.68 (228.68 s, `video-frames/V1/L013-start.png`); V2 2:27.80 (147.797 s, `video-frames/V2/L013-start.png`). Final JSON from V2.
- **Board**: 14x18 cells, 33 arrows, 216 arrow cells (density 0.86), arrow length 3-25 cells (median 5), heads up/down/left/right 9/5/5/14; pitch 24.563 pt (fit rule 24.562).
- **Obstacles**: box 4 (3x4), box 28 (3x4), 2 Linked ties x3 arrows.
- **Timer / hearts / tag**: 3:00 / 3 / none. **Tutorial**: none (no popup, no hand, no caption).
- **Play in the videos**: V1 first tap 3:48.80, cleared 4:10.04 (21.2 s of video; timer 2:39 left; 26 taps); V2 first tap 2:27.90, cleared 3:04.30 (36.4 s; 2:24 left; 32 taps). Hearts 3 → 3. Reward 20.
- **V1 vs V2**: 33/33 arrows identical, obstacles identical (counters and cells), Linked ties identical; disagreements: none.
- **Ink IoU (1 px tol)**: V1 0.9770 / 0.9833 / 0.9846, V2 0.9784 / 0.9860 / 0.9875 (vx / registered / model); heads flagged 0.
- **Replay**: V1 26 taps, 31 consistent, 0 inconsistent, 2 miss, left at end none; V2 32 taps, 29 consistent, 0 inconsistent, 3 miss, left at end none. Box breaks confirmed: 2.
- **Solver**: bot plan solved (29 taps), rule model solved (29 taps); 4 units free at start; 12 waves; box slack (counter → largest solvable) 4→4, 28→28; unsolvable if boxes never break.
- **Fixes**: none to cells or arrows. The robust grid refit changed only the transform: residual 1.36 → 0.33 px.
- **Notes**: Two 3x4 boxes on the right edge (A 4 top, B 28 bottom) and two Linked ties (pink X), each binding three → arrows that point straight into a box (22-24 into A, 27-29 into B). A is aimed at by 8 arrows (22-25, 31 directly), B by 27-29 and 32. Both counters are tight (4 and 28 are the largest solvable values). A bundle launch lowers every counter by its size: V2 158.40 box B went 22 → 19 in one frame when the 22-24 bundle left (sheet work/B/v2l13-tape.png). Bundles were launched by tapping a middle member (23, 28, V1 28) or an end member.

```
    0         5         10      
  0 +---> +-> ^ o ^ o---> AAAAA
  1 | o---+ o | | | o---> AAAAA
  2 o <-----+ +-+ | o---> AAAAA
  3 <---o o-----> o o---> AAAAA
  4 o-------------------> +-+ ^
  5 <---o o---> ^ o---> ^ | o |
  6 +---------> | +-----+ +---+
  7 | +-----+ ^ | | ^ o o . . .
  8 | +-o o | | | | | | | . . .
  9 | +---+ | | | o +-+ v . . .
 10 | | o ^ | o | +-----+ . . .
 11 | | | | v ^ | | +-+ | +---+
 12 | | | | o | | | o | | | o |
 13 | | +-+ | | | +---+ | +-+ v
 14 | | +---+ o | +-----+ BBBBB
 15 | | v o---+ | | o---> BBBBB
 16 | v <-----+ o | o---> BBBBB
 17 +-------o <---+ o---> BBBBB
A = box, counter 4, cols 11-13 rows 0-3
B = box, counter 28, cols 11-13 rows 14-17
Linked tie over cells (9,0) (9,1) (9,2) binds arrows [22, 23, 24]
Linked tie over cells (9,15) (9,16) (9,17) binds arrows [27, 28, 29]
```
Legend: `o` tail, `^ v < >` head, `-` `|` straight body, `+` turn; `A`-`C` box cells; `.` empty cell. Cells are [col,row] as in the JSON.

### L14
- **Source frames**: V1 4:22.44 (262.44 s, `video-frames/V1/L014-start.png`); V2 3:14.94 (194.945 s, `video-frames/V2/L014-start.png`). Final JSON from V2.
- **Board**: 13x16 cells, 15 arrows, 180 arrow cells (density 0.86), arrow length 2-42 cells (median 7), heads up/down/left/right 3/4/6/2; pitch 26.186 pt (fit rule 26.200).
- **Obstacles**: none.
- **Timer / hearts / tag**: 3:00 / 3 / none. **Tutorial**: none (no popup, no hand, no caption).
- **Play in the videos**: V1 first tap 4:22.56, cleared 4:32.24 (9.7 s of video; timer 2:51 left; 15 taps); V2 first tap 3:15.04, cleared 3:31.07 (16.0 s; 2:44 left; 15 taps). Hearts 3 → 3. Reward 20.
- **V1 vs V2**: 15/15 arrows identical, obstacles identical (counters and cells), Linked ties identical; disagreements: none.
- **Ink IoU (1 px tol)**: V1 0.9781 / 0.9841 / 0.9845, V2 0.9815 / 0.9854 / 0.9859 (vx / registered / model); heads flagged 0.
- **Replay**: V1 15 taps, 15 consistent, 0 inconsistent, 0 miss, left at end none; V2 15 taps, 15 consistent, 0 inconsistent, 0 miss, left at end none. Box breaks confirmed: 0.
- **Solver**: bot plan solved (15 taps), rule model solved (15 taps); 5 units free at start; 5 waves.
- **Fixes**: none to cells or arrows. The robust grid refit changed only the transform: residual 1.46 → 0.46 px.
- **Notes**: No obstacles. 15 arrows on a 13x16 block, including a 42-cell zig-zag frame arrow (0). SAME BOARD AS THE PHONE'S L52 (research/levels/L052.json): all 15 arrows identical, timer 3:00.

```
    0         5         10    
  0 . . . o <---------o . . .
  1 . . +-+ +---+ . +---+ . .
  2 . <-+ +-+ ^ +-+ | o +-+ .
  3 o-+ . | . +-+ +-+ +-+ +-+
  4 ^ +---+ +---+ <-----+ +-+
  5 | +---o +---+ +---+ o +-+
  6 +-+ <-----+ | +-+ | v +-+
  7 +-+ +-+ o | | +-+ +-> +-+
  8 | +-+ +-+ | | o +-+ +-o |
  9 +---------+ | +-+ o | +-+
 10 <-o o---+ +-+ +-> +-+ +-+
 11 ^ <-+ +-+ +-+ +-+ +-+ . |
 12 +-+ | | +-+ +-+ +---+ +-+
 13 . o +-+ | | +-----+ +-+ .
 14 . . o-+ | | | o-+ | v . .
 15 . . . +-+ v +---+ v . . .
```
Legend: `o` tail, `^ v < >` head, `-` `|` straight body, `+` turn; `A`-`C` box cells; `.` empty cell. Cells are [col,row] as in the JSON.

### L15
- **Source frames**: V1 4:39.72 (279.72 s, `video-frames/V1/L015-start.png`); V2 3:41.37 (221.369 s, `video-frames/V2/L015-start.png`). Final JSON from V2.
- **Board**: 20x25 cells, 48 arrows, 465 arrow cells (density 0.93), arrow length 2-40 cells (median 7), heads up/down/left/right 13/9/9/17; pitch 17.850 pt (fit rule 17.864).
- **Obstacles**: box 26 (3x3), box 41 (3x3).
- **Timer / hearts / tag**: 3:00 / 3 / none. **Tutorial**: none (no popup, no hand, no caption).
- **Play in the videos**: V1 first tap 4:39.84, cleared 5:13.80 (34.0 s of video; timer 2:27 left; 44 taps); V2 first tap 3:41.47, cleared 4:33.60 (52.1 s; 2:08 left; 47 taps). Hearts 3 → 3. Reward 20.
- **V1 vs V2**: 48/48 arrows identical, obstacles identical (counters and cells), Linked ties identical; disagreements: none.
- **Ink IoU (1 px tol)**: V1 0.9827 / 0.9896 / 0.9902, V2 0.9816 / 0.9908 / 0.9908 (vx / registered / model); heads flagged 0.
- **Replay**: V1 44 taps, 48 consistent, 0 inconsistent, 1 miss, left at end none; V2 47 taps, 48 consistent, 0 inconsistent, 2 miss, left at end none. Box breaks confirmed: 2.
- **Solver**: bot plan solved (48 taps), rule model solved (48 taps); 8 units free at start; 11 waves; box slack (counter → largest solvable) 26→31, 41→43; unsolvable if boxes never break.
- **Fixes**: none to cells or arrows. The robust grid refit changed only the transform: residual 0.67 → 0.34 px.
- **Notes**: 48 arrows on 20x25 with two 3x3 boxes inside the maze: A (26) mid-right, rays from 30/32 (↑, directly) and 11/12/18; B (41) lower-left with only arrow 9 (↑ from below) aimed at it. Slack: A up to 31, B up to 43.

```
    0         5         10        15        
  0 +-------------------------------+ ^ o ^
  1 | ^ . o o---+ +---------------o | | | |
  2 | +---+ o-> | | +-------------o | | | o
  3 +-----------+ | +---------> +-> | | | ^
  4 +-+ o---+ . . +-----------> +-+ | | | |
  5 | | +-o | o---+ o---+ ^ AAAAA | | | +-+
  6 | | +-> | +---+ +---+ | AAAAA | | +---o
  7 | | <---+ +---> +-----+ AAAAA o | +--->
  8 | +---------o <-o o---+ ^ ^ o ^ | +---o
  9 | +-------------------+ | o | | +-> +->
 10 | | +-----------------+ +-+ +-+ o---+ ^
 11 | | | o-> o---+ . +-+ | ^ | +---------+
 12 | | +---------+ . | | | | | +---------o
 13 | +-------> o-> . v o | | | o---------+
 14 | +---> +---------+ . | | +-------o . |
 15 | | . . | +---o o-+ . +-+ o---------> |
 16 +-+ o . | +-----+ +-------------------+
 17 +-+ v . | BBBBB | | +-+ o +-+ o o-+ +->
 18 v +-o . | BBBBB | | | | | | | +-+ | | .
 19 o <-----+ BBBBB v | | o +-+ v ^ | v +-o
 20 | <-----------+ o | +---------+ | +---+
 21 +-+ +-------+ o | | +-----+ <-+ | | ^ |
 22 <-+ | +---+ | ^ | | +---o +-+ o +-+ | v
 23 . o-+ o . v +-+ | | <-----o +-------+ o
 24 <-o <-----------+ +---------> o-----> v
A = box, counter 26, cols 12-14 rows 5-7
B = box, counter 41, cols 5-7 rows 17-19
```
Legend: `o` tail, `^ v < >` head, `-` `|` straight body, `+` turn; `A`-`C` box cells; `.` empty cell. Cells are [col,row] as in the JSON.

### L16
- **Source frames**: V1 5:20.16 (320.16 s, `video-frames/V1/L016-start.png`); V2 4:44.65 (284.646 s, `video-frames/V2/L016-start.png`). Final JSON from V2.
- **Board**: 13x15 cells, 24 arrows, 195 arrow cells (density 1.00), arrow length 2-38 cells (median 6), heads up/down/left/right 6/8/2/8; pitch 26.188 pt (fit rule 26.200).
- **Obstacles**: none.
- **Timer / hearts / tag**: 3:00 / 3 / none. **Tutorial**: none (no popup, no hand, no caption).
- **Play in the videos**: V1 first tap 5:20.28, cleared 5:32.88 (12.6 s of video; timer 2:47 left; 21 taps); V2 first tap 4:44.76, cleared 5:00.74 (16.0 s; 2:44 left; 24 taps). Hearts 3 → 3. Reward 20.
- **V1 vs V2**: 24/24 arrows identical, obstacles identical (counters and cells), Linked ties identical; disagreements: none.
- **Ink IoU (1 px tol)**: V1 0.9672 / 0.9824 / 0.9830, V2 0.9736 / 0.9808 / 0.9829 (vx / registered / model); heads flagged 0.
- **Replay**: V1 21 taps, 24 consistent, 0 inconsistent, 0 miss, left at end none; V2 24 taps, 24 consistent, 0 inconsistent, 0 miss, left at end none. Box breaks confirmed: 0.
- **Solver**: bot plan solved (24 taps), rule model solved (24 taps); 4 units free at start; 10 waves.
- **Fixes**: none to cells or arrows. The robust grid refit changed only the transform: residual 1.46 → 0.38 px.
- **Notes**: No obstacles. 24 arrows filling every cell of a 13x15 block (density 1.00), a nested-spiral left half.

```
    0         5         10    
  0 +-------> o-+ +-> ^ +---o
  1 | +-------> +-+ o +-+ +->
  2 | | +-----+ +---+ o o-+ ^
  3 | | | +-+ o | o o +-----+
  4 | | v | | o | | | ^ o---+
  5 | | o-+ v | | v | | o-+ |
  6 | +-------+ +-+ | o ^ | |
  7 | +---------+ | | o-+ | |
  8 | | o---> o | | | +-+ | |
  9 | +-------+ | | | | | | v
 10 | <---o <-+ | | | o | +->
 11 | o-------+ | | | ^ | o-+
 12 | o +-------+ | | | | ^ v
 13 | v +-> o---> v | | | | o
 14 +---------------+ o +-+ v
```
Legend: `o` tail, `^ v < >` head, `-` `|` straight body, `+` turn; `A`-`C` box cells; `.` empty cell. Cells are [col,row] as in the JSON.

### L17
- **Source frames**: V1 5:40.72 (340.72 s, `video-frames/V1/L017-start.png`); V2 5:17.81 (317.810 s, `video-frames/V2/L017-start.png`). Final JSON from V2.
- **Board**: 19x24 cells, 54 arrows, 453 arrow cells (density 0.99), arrow length 2-44 cells (median 6), heads up/down/left/right 18/19/5/12; pitch 18.704 pt (fit rule 18.714).
- **Obstacles**: 3 Linked ties x3 arrows.
- **Timer / hearts / tag**: 3:00 / 3 / none. **Tutorial**: none (no popup, no hand, no caption).
- **Play in the videos**: V1 first tap 5:40.84, cleared 6:20.76 (39.9 s of video; timer 2:08 left; 46 taps); V2 first tap 5:17.91, cleared 6:20.60 (62.7 s; 1:57 left; 46 taps). Hearts 3 → 3. Reward 20.
- **V1 vs V2**: 54/54 arrows identical, obstacles identical (counters and cells), Linked ties identical; disagreements: none.
- **Ink IoU (1 px tol)**: V1 0.9701 / 0.9851 / 0.9873, V2 0.9725 / 0.9867 / 0.9883 (vx / registered / model); heads flagged 0.
- **Replay**: V1 46 taps, 50 consistent, 0 inconsistent, 4 miss, 1 late, left at end none, 1 board re-fit after the edit cut; V2 46 taps, 50 consistent, 0 inconsistent, 3 miss, left at end none. Box breaks confirmed: 0.
- **Solver**: bot plan solved (48 taps), rule model solved (48 taps); 7 units free at start; 14 waves.
- **Fixes**: none to cells or arrows. The robust grid refit changed only the transform: residual 0.84 → 0.29 px.
- **Notes**: 54 arrows on 19x24 (almost every cell filled) with three Linked ties, each binding three parallel ↓ arrows (top-left 5/8/12, top-right 43/46/51, centre 23/25/27). V1 is CUT at 6:00.7 (timer 2:41 → 2:28, board re-fitted after the cut: the replay's board_moved event); V2 shows the whole level, so L017 is from V2.

```
    0         5         10        15      
  0 ^ o o o o-+ +-> ^ ^ +-----+ ^ o o o ^
  1 o | | | ^ +-+ o | o | +-+ o o | | | |
  2 ^ | | | +-+ +-+ | ^ | o | ^ o | | | o
  3 | v v v +-+ +---+ | | +-+ o | v v v ^
  4 | +-+ o +---+ +-+ | | v +-+ | +---> |
  5 | | o +-----+ | | | | <-+ | | | +-+ |
  6 | | <-o o <---+ | | | o---+ | | o +-+
  7 +-+ o-> | +-> . | | | +-----+ +-----+
  8 +---> . | | +---+ | | +-> +---+ +-> |
  9 | o---+ | | | +---+ +-----+ ^ | +-+ o
 10 | <---+ | o | | o o o +---+ | +-+ | ^
 11 +-----+ | ^ | | | | | | o v +-+ | | |
 12 +-+ o-+ | | | | | | | | v +---+ | o |
 13 v | o +-+ o | | v v v +-o +---o +---+
 14 o +-+ | +---+ +---+ +-----+ ^ +-+ +->
 15 | +-+ | | +-----+ | | o o-+ | o +-+ ^
 16 | | | | | +---+ | | | | +-+ +-+ +-> o
 17 | | | | +-o o-+ | | v | o +-> | +---+
 18 | | | | <---+ ^ | | +-+ +-----+ +-+ o
 19 | | +-+ o ^ | | v | | . | o +-+ | | ^
 20 | | o +-+ | | o o | +-> | +-+ v | | |
 21 | | v +---+ +---+ | +-+ +-----+ | +-+
 22 | +-------------> | v +-o +-+ | o o-+
 23 +-----------------+ o-----+ v +-----+
Linked tie over cells (1,2) (2,2) (3,2) binds arrows [5, 8, 12]
Linked tie over cells (15,2) (16,2) (17,2) binds arrows [43, 46, 51]
Linked tie over cells (8,12) (9,12) (10,12) binds arrows [23, 25, 27]
```
Legend: `o` tail, `^ v < >` head, `-` `|` straight body, `+` turn; `A`-`C` box cells; `.` empty cell. Cells are [col,row] as in the JSON.

### L18
- **Source frames**: V1 6:31.00 (391.00 s, `video-frames/V1/L018-start.png`); V2 6:29.94 (389.940 s, `video-frames/V2/L018-start.png`). Final JSON from V2.
- **Board**: 14x17 cells, 22 arrows, 226 arrow cells (density 0.95), arrow length 3-45 cells (median 7), heads up/down/left/right 2/4/13/3; pitch 24.542 pt (fit rule 24.562).
- **Obstacles**: none.
- **Timer / hearts / tag**: 3:00 / 3 / none. **Tutorial**: none (no popup, no hand, no caption).
- **Play in the videos**: V1 first tap 6:31.12, cleared 6:44.16 (13.0 s of video; timer 2:47 left; 21 taps); V2 first tap 6:30.04, cleared 6:49.27 (19.2 s; 2:41 left; 20 taps). Hearts 3 → 3. Reward 20.
- **V1 vs V2**: 22/22 arrows identical, obstacles identical (counters and cells), Linked ties identical; disagreements: none.
- **Ink IoU (1 px tol)**: V1 0.9769 / 0.9878 / 0.9888, V2 0.9864 / 0.9896 / 0.9897 (vx / registered / model); heads flagged 0.
- **Replay**: V1 21 taps, 22 consistent, 0 inconsistent, 1 miss, left at end none; V2 20 taps, 22 consistent, 0 inconsistent, 1 miss, left at end none. Box breaks confirmed: 0.
- **Solver**: bot plan solved (22 taps), rule model solved (22 taps); 4 units free at start; 10 waves.
- **Fixes**: none to cells or arrows. The robust grid refit changed only the transform: residual 1.16 → 0.40 px.
- **Notes**: No obstacles. 22 arrows on 14x17; 13 of the 22 heads point left (a left-draining board), one 45-cell border arrow (3).

```
    0         5         10      
  0 +---+ o-----------+ o-----+
  1 | o | <-----------+ <---+ |
  2 | | | +---------+ o-----+ |
  3 | +-+ +-------o v <-------+
  4 | ^ o---------------------+
  5 v +---------+ ^ +-o <---o |
  6 o-----+ +-+ | | | +-------+
  7 . . <-+ | | | o | | +-+ . .
  8 . . +-+ o v +---+ | | o . .
  9 . . | o <---o <---+ +-> . .
 10 +-+ | +-> +---------------+
 11 o | | | o | <---o o +---+ |
 12 o | | +-+ +-----+ | | o | |
 13 | v +---------> | | | | | |
 14 +---------------+ | +-+ | |
 15 <---o <-----o <---+ <---+ |
 16 <-------------------------+
```
Legend: `o` tail, `^ v < >` head, `-` `|` straight body, `+` turn; `A`-`C` box cells; `.` empty cell. Cells are [col,row] as in the JSON.

### L19 — Hard Level
- **Source frames**: V1 6:55.56 (415.56 s, `video-frames/V1/L019-start.png`); V2 7:00.91 (420.907 s, `video-frames/V2/L019-start.png`). Final JSON from V2.
- **Board**: 20x31 cells, 62 arrows, 575 arrow cells (density 0.93), arrow length 2-35 cells (median 7), heads up/down/left/right 24/7/18/13; pitch 17.853 pt (fit rule 17.864).
- **Obstacles**: box 13 (3x5), box 20 (3x5), box 25 (3x5).
- **Timer / hearts / tag**: 3:00 / 3 / Hard Level. **Tutorial**: no popup (first Hard: red HUD + "Hard Level" tab, tutorials.md §7); no hand, no caption.
- **Play in the videos**: V1 first tap 6:55.68, cleared 7:43.20 (47.5 s of video; timer 2:13 left; 58 taps); V2 first tap 7:01.01, cleared 8:09.33 (68.3 s; 1:52 left; 61 taps). Hearts 3 → 3. Reward 60.
- **V1 vs V2**: 62/62 arrows identical, obstacles identical (counters and cells), Linked ties identical; disagreements: none.
- **Ink IoU (1 px tol)**: V1 0.9807 / 0.9920 / 0.9920, V2 0.9825 / 0.9931 / 0.9931 (vx / registered / model); heads flagged 0.
- **Replay**: V1 58 taps, 62 consistent, 0 inconsistent, 5 miss, left at end none; V2 61 taps, 62 consistent, 0 inconsistent, 2 miss, left at end none. Box breaks confirmed: 3.
- **Solver**: bot plan solved (62 taps), rule model solved (62 taps); 11 units free at start; 25 waves; box slack (counter → largest solvable) 13→13, 20→20, 25→25; unsolvable if boxes never break.
- **Fixes**: none to cells or arrows. The robust grid refit changed only the transform: residual 0.73 → 0.28 px.
- **Notes**: FIRST HARD LEVEL ("Hard Level" tab, red HUD; win reward 60, no popup). 62 arrows on 20x31 (the tallest board of the batch) with three 3x5 boxes in three corners: A 13 top-left, B 20 top-right (59/60 ↑ directly under it), C 25 bottom-left. All three counters are tight (13 / 20 / 25 are the largest solvable values). Rays into them: A 1, 12, 22, 44, 49, 53; B 28, 54, 58-61; C 2, 3, 17, 25, 31, 37, 38, 42, 43. The greedy clear needs 25 waves (the deepest board of the batch).

```
    0         5         10        15        
  0 AAAAA o ^ ^ <-o ^ ^ o ^ <-o <---+ BBBBB
  1 AAAAA | | | ^ +-+ +-+ | o <-o ^ | BBBBB
  2 AAAAA | | | | | o ^ ^ | +---+ | | BBBBB
  3 AAAAA | | | | | +-+ | +---o | | | BBBBB
  4 AAAAA | | | | | o-> +-------+ | | BBBBB
  5 +-----+ o | | | +-----------o | | o ^ ^
  6 | o-------+ | | | <---------+ | | | | |
  7 | o---------+ | | o---------+ | | | | |
  8 +-------------+ +-----> o---> | | | o |
  9 ^ o o +---------> +-----> o---+ o | +-+
 10 | | | | ^ o <---o +-o +-----------+ o ^
 11 | | | | | | +-------+ | <-+ +---------+
 12 +-+ | | +-+ | <---+ | | ^ | | +---> ^ o
 13 o-+ | +-----+ o---+ | | | | | | ^ o | |
 14 o v +---------------+ | | | | | | | | |
 15 | o-----+ <-o ^ +---+ | | | o | | | | |
 16 | o ^ ^ | o o | | o | | | | ^ | | | | |
 17 | | o | | | | | | | | | | o o | | | | |
 18 | +---+ | | +-+ | | | | | o---+ o +-+ |
 19 | <-----+ | ^ ^ | | | | +-------------+
 20 +---+ +-+ | | | | | | | +------------->
 21 <-+ | | | | | | | | | | | +---------> ^
 22 o o v v o +-+ | | | o | | | o-------+ o
 23 +-------------+ v +-> v o +-------o +->
 24 +------------------------------------->
 25 +-----+ +-------> o---> o-------------+
 26 CCCCC | +-------------------------o o |
 27 CCCCC | <-----o <---o <-----------+ | |
 28 CCCCC | +-----------------o o-----+ | |
 29 CCCCC | | +-----+ <-----------------+ |
 30 CCCCC o v o <-o v <-o <---------------+
A = box, counter 13, cols 0-2 rows 0-4
B = box, counter 20, cols 17-19 rows 0-4
C = box, counter 25, cols 0-2 rows 26-30
```
Legend: `o` tail, `^ v < >` head, `-` `|` straight body, `+` turn; `A`-`C` box cells; `.` empty cell. Cells are [col,row] as in the JSON.

### L20
- **Source frames**: V1 7:55.32 (475.32 s, `video-frames/V1/L020-start.png`); V2 8:20.20 (500.196 s, `video-frames/V2/L020-start.png`). Final JSON from V2.
- **Board**: 14x20 cells, 20 arrows, 279 arrow cells (density 1.00), arrow length 2-39 cells (median 13), heads up/down/left/right 4/7/2/7; pitch 24.558 pt (fit rule 24.562).
- **Obstacles**: none.
- **Timer / hearts / tag**: 3:00 / 3 / none. **Tutorial**: none (no popup, no hand, no caption).
- **Play in the videos**: V1 first tap 7:55.44, cleared 8:10.72 (15.3 s of video; timer 2:45 left; 19 taps); V2 first tap 8:20.33, cleared 8:37.90 (17.6 s; 2:42 left; 20 taps). Hearts 3 → 3. Reward 20.
- **V1 vs V2**: 20/20 arrows identical, obstacles identical (counters and cells), Linked ties identical; disagreements: none.
- **Ink IoU (1 px tol)**: V1 0.9779 / 0.9836 / 0.9848, V2 0.9803 / 0.9862 / 0.9869 (vx / registered / model); heads flagged 0.
- **Replay**: V1 19 taps, 20 consistent, 0 inconsistent, 1 miss, left at end none; V2 20 taps, 20 consistent, 0 inconsistent, 0 miss, left at end none. Box breaks confirmed: 0.
- **Solver**: bot plan solved (20 taps), rule model solved (20 taps); 5 units free at start; 9 waves.
- **Fixes**: none to cells or arrows. The robust grid refit changed only the transform: residual 1.33 → 0.38 px.
- **Notes**: No obstacles. 20 long arrows (median 13 cells) filling a 14x20 block (density 0.996): nested spirals and a comb-shaped border arrow (0).

```
    0         5         10      
  0 +-------------> o-----+ +-+
  1 | +---+ +-+ ^ <-----+ +-+ |
  2 | | o +-+ +-+ o-> ^ +-+ +-+
  3 | | | +-----------+ +-+ +->
  4 | o | | +---------+ +-----+
  5 +-+ | | | +-----+ | +-+ +-+
  6 +-+ | | | | o-+ | | | +-+ o
  7 +-+ | | | +---+ | | +---o v
  8 +-+ | | +-----o v | ^ o---+
  9 +-o | +---------+ | | +---+
 10 +-o +-----+ +-+ +-+ o +---+
 11 | +-o o-+ +-+ | +-+ +-----+
 12 | +---+ +---+ +-+ v +-----+
 13 | +---+ +-+ +-----+ +-+ +-+
 14 | | +-+ v o ^ +---+ | | +-+
 15 | +-+ +-> +-+ +---+ | +---+
 16 +---+ +-+ | . +-+ | +-> +-+
 17 +---+ | | +-+ o | +-+ +-+ |
 18 +-----+ +-> +-+ | +-+ +-o v
 19 <-------o o---+ v v o----->
```
Legend: `o` tail, `^ v < >` head, `-` `|` straight body, `+` turn; `A`-`C` box cells; `.` empty cell. Cells are [col,row] as in the JSON.

## New for tutorials.md (tutor lane; I did not edit it)
- **Box counter timing:**
  - The counter drops on the frame the tapped arrow starts to move.
  - The box shatters on the launch frame of the arrow that brings it to 0; "0" is never drawn.
  - The pieces fall away within 1.5 s and leave plain grid dots.
  - A Linked bundle lowers it by 3 in one frame.
  - Measured in both skins, frame by frame (V2 at 59.64 fps).
- **The phone's in-board box art** (L51 = video L12) is V1's in-board "Curtain" slab: purple, silver ring lock, rivets. It is not
  V2's cyan bomb block. The unlock card name and caption are the phone's and V2's "Box!".
- **L11-L20 have no hand, caption or spotlight.** Only L11's unlock popup and L19's first Hard (no popup). That matches §6-7.

## Open questions (for the orchestrator)
1. **Numbering (from the index agent):**
   - v552 moved two of this batch's boards: video L12 is phone L51, and video L14 is phone L52.
   - If L1-31 follow the videos and L32+ follow the phone, the game ships these two boards twice (L12 and L51, L14 and L52).
   - The phone also has the counters (8/16/23) on its L51.
   - Decide whether to keep both copies or replace phone L51/L52 with other phone levels.
2. **Box art:** I recommend the phone's look, which is V1's purple slab, with the phone's "Box!" name and caption. The index agent
   had assumed V2's cyan bomb block. The phone shot `shots/140-L051-start.png` settles it.
3. **Touch radius:** touches 0.75-0.90 cell from a stroke still launched the arrow in the video. The phone lane can measure the real
   hit area; the disc centroids here are biased.

