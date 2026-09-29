# Video levels — batch D (levels 31-38, V2)

Author: level extractor batch D, 2026-09-25 (second run; the first run left only `levels/video/dcheck.py`, which this run extended
and kept). Owner-facing name **Arrow Out**; the video shows the original "Maze Out!". Content only: frames were measured, never
shipped or traced.

**Result.**
- **L31-L38 are extracted from V2 and verified.** That is 315 arrows at the start plus 74 hidden-layer arrows, with 6 boxes, 3 pipes, 4 Linked ties and 5 elevator platforms.
- **Ink IoU.** Every start frame scores 0.982-0.993 (1-px tolerance, registered). Every hidden layer scores 0.977-0.991 at its reveal frame. 0 arrows are flagged for a wrong head.
- **Replay.** Every level replays against V2 with **0 contradictions**: 387 consistent events, including L32's two heart losses, both on blocked arrows. The one "no-effect" tap (L33) is a real exit that the check misjudged (frames).
- **Solvers.** Both solvers clear all eight boards.
- **Two recognition errors, fixed by hand.** Both are pipe mouths that the reader placed one row too low (L35, L38). Batch C found and fixed the same error in its L21-L30 (see "Reader error found").
- **The build verdict.** Video L32-L38 are **not** the phone's L32-L38. They are not anywhere in the phone's L32-L61 either, under any rotation, reflection or shift: the best overlap is 2-5 of 29-57 arrows, which is chance.

Files:
- `research/levels/L031.json`: final, phone schema, `source:"video"`, `video:"V2"`, `t`, plus a `checks` block (IoU, replay, events, solver, play facts) and `batchD` notes.
- `research/levels/video/V2-L031.json` … `V2-L038.json`: the V2 extractions, same fields. L32-L38 are NOT promoted to `levels/L0NN.json`, where the phone's recorded files live and are untouched.
- `research/levels/video/diff-L032.md` … `diff-L038.md`: cell-by-cell diff vs the phone file (ASCII boards side by side + diff map), plus the search over every phone level with 8 symmetries.
- `research/levels/video/dcheck.py`: the batch-D tool, built on vextract and bcheck:
  - `rebuild`: robust refit.
  - `verify1`: start-frame IoU.
  - `verify2`: hidden layers at their reveal frames.
  - `replay`.
  - `events`: pipe passes, box breaks, activations and platform crossings in video order.
  - `track`: whole-level ink audit.
  - `solveall`: bot.plan greedy with the video rules and an elevator heuristic, plus the rule-model DFS, box/pipe counterfactuals and random-order dead-ends.
  - `diff`, `final`.
- Gitignored, in `research/video-frames/work/D/`:
  - overlays (`V2-L0NN-overlay.png`, `-verifyB.png`, `-layer2-eK-verifyB.png`);
  - verify, replay, track and solve JSONs;
  - side-by-side crops (`sbs-L0NN*.png`);
  - sheets: `L035-pipe-break.png`, `L038-pipe0.png`, `L038-pipe1.png`, `L032-elevator.png`, `L032-doors-fine.png`, `L033-arrow7.png`, `L035-cross32.png`, `L035-pan*.png`, `L038-move.png`, `L038-last.png`, `L031-popup.png`, `L035-pipe-grid.png`, `L038-pipes-grid.png`, `L021-pipe-grid.png`, `L023-pipe-grid.png`.

## How each level was checked
1. **Start frame.** The index's clean start frame is the frame 0.10 s before the first tap; for L31 the board was already built under the popup. I read it at full resolution side by side with the overlay, in halves, bands or quadrants at 1-1.6x (`sbs-*.png`). Every arrow of all 8 boards was compared by eye; the elevator platforms of L31/L32/L33 were zoomed separately.
2. **Read.** `vextract.read_board` plus bcheck's robust grid refit. The residual falls from 0.63-1.20 px to 0.27-0.37 px. No cell changed. All 8 boards equal the index agent's extraction arrow for arrow, with the same ids (8/8). Hidden layers are carried from the index's `reveal()` only when the cell frame and ids are unchanged, which they were for all 5 elevators.
3. **Overlay read by eye** → two errors found (both pipes). No arrow error.
4. **Ink IoU, three ways** (bcheck.verify: vextract / registered / model), with residual classes and a per-arrow head/tail check. The negative control is batch B's: a reversed head is flagged even when the board IoU stays above 0.97.
   - Start frames: 0.9838-0.9931 registered. Body clusters of 25 px or more: only 1-px slivers along strokes on the platform shading (L31, L33) and one 1-px offset segment of L32 arrow 8. None is a missing or extra segment.
   - **Hidden layers**: the board of every arrow alive at the reveal frame, as rebuilt from the replay log (platform arrows removed), is scored on the reveal frame: 0.9772-0.9909, 0 hidden heads flagged. L32's only cluster (501 px) is arrow 16 drawn black after its bump.
5. **Replay** (`vextract.replay`) with these JSONs, then `events`, which walks the log through the model. Every miss, stay and move was looked at on frames (notes per level).
6. **Whole-level ink audit** (`track`): before every tap, the frame is compared with the model's live set.
   - Nothing persistent is unexplained. The persistent spots are 30-58 px at arrow heads (L31 arrow 15, L32 arrow 10, L38 arrow 20 and between the heads of 23/26): the game's head is drawn a little larger than our render (checked on a crop).
   - L32 also shows the black bumped arrow.
   - **Nothing appears under any box, pipe or platform after it goes.**
7. **Solvers**:
   - research/bot's `plan()`, re-planned after every tap. Rules added around it: unbroken boxes are door cells; every removed arrow lowers every box counter; a pipe teleports rays mouth to mouth, counts its passes and frees its cells when it breaks; a hidden layer joins the board when its platform's last arrow leaves.
   - An elevator heuristic: if plan() picks a platform's last arrow, re-plan with that platform frozen.
   - The replay's rule model (greedy, then DFS).
   - Counterfactuals: boxes/pipes that never break, the largest solvable box counter, and 300 random orders.
8. **Diff vs the phone** (L32-L38): `dcheck.diff` at the best integer shift, then an exhaustive search over the phone's L032-L061 (open variants included) × 8 symmetries. It votes on the shift between identically shaped arrows.

## Summary

| level | grid | arrows (+hidden) | obstacles | tag | start (s) | IoU tol1 vx / reg / model | hidden-layer IoU reg | replay: taps, ok, **bad**, miss | solver (taps) | waves | vs phone |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 31 | 16x17 | 28 (+7) | elevator (84 cells) | - | 1184.04 | 0.9829 / 0.9885 / 0.9887 | 0.9909 | 31, 35, **0**, 3 | solved (35) | 12 | (L31 is not recorded on the phone) |
| 32 | 17x21 | 29 (+11) | elevator (104) | - | 1216.38 | 0.9684 / 0.9820 / 0.9896 | 0.9772 | 41, 42, **0**, 2 (2 bumps, both blocked) | solved (40) | 16 | different (1/53) |
| 33 | 17x23 | 36 (+17) | box 41, 28, 18, 13; 2 elevators (78 + 78) | - | 1259.17 | 0.9663 / 0.9838 / 0.9840 | 0.9773, 0.9815 | 47, 53, **0**, 1 | solved (53) | 22 | different (1/20) |
| 34 | 18x23 | 40 | 4 Linked ties of 3 | - | 1330.78 | 0.9766 / 0.9899 / 0.9899 | - | 30, 36, **0**, 0 | solved (32 units) | 13 | different (1/76) |
| 35 | 20x32 | 57 (+39) | pipe 3 (U, 26 cells); elevator (320) | Hard Level | 1379.07 | 0.9854 / 0.9931 / 0.9931 | 0.9892 | 89, 96, **0**, 4 | solved (96) | 44 | different (1/20) |
| 36 | 20x23 | 36 | - | - | 1506.21 | 0.9795 / 0.9907 / 0.9907 | - | 36, 36, **0**, 3 | solved (36) | 14 | different (1/31) |
| 37 | 20x33 | 55 | box 52, box 35 | - | 1549.25 | 0.9793 / 0.9906 / 0.9917 | - | 54, 55, **0**, 1 | solved (55) | 23 | different (1/14) |
| 38 | 16x20 | 34 | pipe 3 (∩, 14 cells), pipe 3 (U, 14 cells) | - | 1631.10 | 0.9674 / 0.9893 / 0.9893 | - | 33, 34, **0**, 1 | solved (34) | 12 | different (1/42) |

Column notes:
- "ok" counts exits on free arrows, bumps on blocked arrows, and arrows gone without a detected tap (each checked free), so it can exceed the number of taps.
- Solver taps are units: a Linked bundle is one. "waves" = rounds if every free unit leaves at once.
- The vextract IoU (first number) is below 0.97 on L32, L33 and L38 only because vextract draws on integer pixel centres, a ~0.5-px bias batch B measured. The registered render (second number) is ≥ 0.982 on all eight. That meets the 0.97 target.

**Timer, hearts, rewards.** Every level starts at **3:00** with **3 hearts**; L35 (Hard) is 3:00 too.
- The clock starts at the first tap. L32: 3:00 was still showing 1 s after the first tap at 1216.50, and 2:59 at 1218.38.
- Time left at clear: L31 2:36, L32 2:26, L33 2:02, L34 2:27, L35 1:03, L36 2:28, L37 1:49, L38 2:20.
- Rewards: 20, and 60 for L35 (Hard).
- The only heart losses in the whole of V2 are L32's two (3 → 1). Both are taps on blocked arrows; the win title is still "Perfect!" (index).

## The build verdict: video L32-L38 vs the phone's L32-L38

| level | video V2 | phone v552 (research/levels) | identical arrows at best shift | best over all phone L32-61 × 8 symmetries |
|---|---|---|---|---|
| 32 | 17x21, 29 (+11 hidden), elevator | 20x20, 53, 4 tapes | 1 | 2/29 (L044) |
| 33 | 17x23, 36 (+17), 4 boxes + 2 elevators | 20x20, 20, doors + keys | 1 | 2/36 (L060) |
| 34 | 18x23, 40, 4 tapes | 25x35, 76, doors + keys, **Hard 3:30** | 1 | 5/40 (L057: parallel straight triples) |
| 35 | 20x32, 57 (+39), pipe + elevator, **Hard** | 12x18, 20, pipe (= video L21) | 1 | 2/57 |
| 36 | 20x23, 36 | 16x23, 31, 2 pipes | 1 | 2/36 |
| 37 | 20x33, 55, 2 boxes | 22x30, 14, doors + keys | 1 | 2/55 |
| 38 | 16x20, 34, 2 pipes | 20x22, 42, pipe + tapes | 1 | 2/34 |

A real match scores every arrow; the known ones score 15/15-26/26. So **the video build's L32-L38 are different content from v552's L32-L38**, and none of them appears elsewhere in v552's L32-L61. This confirms the index agent's finding with an exhaustive search.
- The obstacles differ as well. v552 has doors and keys and no elevator at all in L32-L61; the videos have elevators from L31 and no doors.
- v552 has Hard on L34, the videos on L35.
- The numbering question (video order vs v552 order) is the orchestrator's; nothing here was promoted for L32-L38.

## Obstacle behaviour measured in these levels

### Elevator (L31, L32, L33 ×2, L35)
- **What it is.** A rounded lavender platform with a hatched rim and a vertical divider: two closed **doors**. Sizes: 84, 104, 78, 78 and 320 cells. The unlock icon is the same grey double door. The platform's arrows are ordinary arrows standing on the doors.
- **Rays.** **Empty platform cells do not block rays.**
  - Five exits of outside arrows crossed a platform that still had 1-8 arrows on it (L33: arrows 20, 49, 51, 0; L35: arrow 32).
  - Seen on frames (`L035-cross32.png`): arrow 32 slides straight down over the closed doors and off the board.
  - Arrows on the platform block like any arrow.
- **Opening.** When the last platform arrow has left, the doors part from the centre divider outward. The hidden layer shows under a dark tint, then at full colour, and the platform frame fades.
  - L32 (`L032-doors-fine.png`): the last arrow (14, 52 cells) is tapped at 1234.50 and its tail clears the platform at 1235.05. The doors start opening at 1235.07. The layer is fully visible by ~1235.4 and the frame is gone by 1235.5.
  - L33 elevator 0 (`L033-arrow7.png`): the last arrow (7, 3 cells) is tapped at 1311.55. The doors are opening at 1311.70, the tinted layer is full at 1311.85, and the plain board shows at 1312.15.
  - So the doors open **when the last platform arrow has cleared the platform** (0.15-0.55 s after its tap, depending on its length), and the reveal takes ~0.45 s.
- **When the hidden layer blocks.** L32 1235.10: a tap on arrow 16, 0.03 s after the doors began to part. Its ray runs left under the LEFT door, which was still closed. It bumped (heart lost, red vignette at 1235.19) against hidden arrows 29/30/32/36. So **the hidden layer blocks from the start of the door animation, before it is visible.**
  - Not observed: a tap during the last platform arrow's exit slide. The model (and the index) make the layer live at that arrow's tap. Using "live when the last arrow has cleared the platform" is equally consistent with all 5 elevators.
- **What comes up.** The platform is packed: its arrows cover 97-100 % of its cells (84/84, 104/104, 76/78, 78/78, 320/320). The hidden layer (7, 11, 9 + 8, 39 arrows) lies entirely inside the platform and covers the same cells again (84/84, 103/104, 76/78, 77/78, 304/320): a true second layer. Once up, they are ordinary arrows, and no third layer appeared (whole-level audit).
- **Solver facts.** 300 random play orders never dead-ended on any elevator level, and bot.plan solves them without the elevator heuristic too. So emptying a platform early does not trap these boards, although the rule could in principle.

### Pipe (L35 one U, L38 an inverted U and a U; all counter 3)
- **What it is.** A thick light-blue tube along cells, with a mouth cap at each end and a dark-blue counter badge on one leg.
- **Pass rule.** An arrow whose head points INTO a mouth, against the mouth's outward direction, enters, travels through the tube (drawn inside it) and leaves by the other mouth in that mouth's outward direction. Any other ray that meets a tube cell or a cap cell is blocked. This is the model's rule; the replay found 0 contradictions with it.
  - L35: 14 arrows are held by the pipe at the start: 12, 16, 17, 26, 27, 32, 35, 39 inside or beside the U, and platform arrows 7, 36, 42, 44, 46, 54 pointing up into its bottom row. Every one left after the break; the first at 1413.81, 2.1 s after the third pass.
  - L38: arrows 0, 1, 29 are held by the top pipe and 9 by the bottom one; each left after its own pipe broke. Each pipe is needed: the level is unsolvable if either one never breaks.
- **Counting and breaking** (`L035-pipe-break.png`, `L038-pipe0.png`, `L038-pipe1.png`):
  - The badge counts down by 1 **when the passing arrow comes out of the far mouth**, about 0.6 s after its tap on these long U tubes (batch C: ~0.42 s for an arrow next to the mouth on shorter pipes).
  - When it would reach 0, the pipe **shatters** into cyan chunks; the badge and caps fly out and fall with gravity, gone by ~0.6 s. A "0" is never shown.
  - L35: taps 1409.90 / 1411.21 / 1411.68 → badge 2 at ~1410.5, 1 at ~1411.9, shattered at ~1412.3.
  - L38 top pipe: taps 1651.94 / 1654.88 / 1655.18 → 1 at ~1655.4, shattered at 1655.80.
  - L38 bottom pipe: taps 1665.14 / 1666.38 / 1666.71 → 1 at ~1666.9, shattered at 1667.30.
- **After the break**, the cells are empty grid dots, and nothing was under either pipe (whole-level audit).
- **Gap in the replay tool.** It does NOT check pipe breaks against the video: the model drops the pipe on the 3rd pass, and the video-side check only logs a break the video shows first. The five breaks above were checked on frames instead.

### Box (L33: 41 / 28 / 18 / 13; L37: 52 / 35)
- Same rule as batch B, confirmed here: a box breaks on the exit that makes arrows-removed == its counter.
  - The replay's two-sided check logs the model break and requires the video's to follow within ~1 s: 6 of 6 agree.
  - The boxes break in counter order: L33 13 → 18 → 28 → 41, L37 35 → 52.
- **The counters are tight.** Raising any counter by 1 makes the level unsolvable, except L33's 13, which can go to 14. With boxes that never break, both levels are unsolvable. This is the designer's pattern: the box opens exactly when the arrows behind it are the only ones left that can move.
- L33 combines boxes and elevators: 53 arrows in all, with the hidden layers counting toward the boxes (box 41 broke on hidden arrow 51).
- Skin: the video's cyan "bomb" box. Batch B found the phone's in-board box = V1's purple slab, and the name "Box".

### Linked ties (L34)
- 4 ties, each binding 3 parallel straight arrows. Every bundle left as one unit on a single tap, and all members were free every time (as in batch B). Each member counts toward boxes; L34 has none.

## Reader error found (same as batch C's): pipe legs cut short
- The reader stops a vertical pipe leg one cell short of its mouth cap. It drops the cap cell, or takes the badge cell as the mouth.
- The convention is set by video L21, which is phone L35: both readers agree there, the cap is drawn INSIDE the end cell and the badge sits in the next cell (`L021-pipe-grid.png`).
- Fixed here on **L35** (both legs) and **L38** (the bottom pipe's left leg).
- Batch C found the same error independently and fixed it in its final `levels/L021-L030` (video-levels-C.md: "the reader cut pipe legs short"; e.g. L23 ends (9,17)/(15,17), L25 (18,5)/(5,29), L29). Only the index agent's raw `work/extract/V2-L0NN.json` files still carry the short legs (`L023-pipe-grid.png` shows one): **anyone reading pipes from work/extract must use the batch files instead.**
- **Why it matters:** a ray crossing the cap cell sideways is blocked in the game but free in the unfixed model. On L35 that is arrow 16 (row 12, pointing left at the left cap cell). It left only after the break, so no replay could catch it.
- Timing agrees with batch C. The badge steps when the passing arrow comes out of the far mouth, and the pipe shatters as the last arrow does. That is ~0.42 s after the tap for an arrow next to the mouth (C) and ~0.6 s here, where the paths through the U are longer: 26-cell tube on L35, 14-cell tubes on L38.

## Tutorial: L31 "Elevator!" unlock (V2 1180.6-1184.1; `L031-popup.png`)
Complementing tutorials.md §6 (row 18); tutorials.md was not edited.

| time | event |
|---|---|
| 1178.0-1180.6 | Home at LEVEL 31 (coins 1760, lives 5 "Full"); Play tapped between 1180.6 and 1180.8 |
| 1180.8 | Black transition; the L31 board is already built underneath a near-black overlay |
| 1181.0 | The icon pops in at screen centre: a grey rounded square with two door panels (the elevator doors) |
| 1181.2 | Title **"Elevator!"** (white, blue outline) |
| 1181.4 | **"Unlocked!"**; the caption box starts scaling up from a point |
| 1181.6 | The caption box is at full size: cream box with a blue border, **"Clear all arrows on the"** / **"ELEVATOR"** (blue caps) **"to activate it!"** |
| 1181.8-1182.8 | Twinkle sparkles around the icon |
| 1182.8-1183.0 | Tap anywhere dismisses it (the card is still full at 1182.80 and fading at 1183.00, 1.2-1.4 s after it completed); the overlay fades |
| 1183.2 | Board at full brightness, HUD 3:00 and 3 hearts, timer not running |
| 1184.14 | First tap; the clock starts |

- There is no hand, no spotlight and no in-board caption on L31 or on any later elevator level.
- The first Hard level of this batch, L35, has no popup either; the HUD shows the red "Hard Level" tab and red buttons (`L035-pan2.png`).

## Board moves without a touch (answers the index agent's open question 4 as far as video allows)
- **L35 1479.3-1480.9.** The board wobbles: up and right, back, right and down, back. It settles +44.8 px right and +3 px down with the pitch unchanged. No touch disc is drawn.
- **L38 1669.4-1671.0.** With one arrow left, the board is dragged so the arrow goes to the left edge and back, again with no disc.
- Both look like **manual pans** (rubber-band motion, back and forth), not an automatic re-centre, which would be one smooth move. The screen recorder evidently does not draw its touch disc during drags.
- The replay re-registers the grid on L35. On L38 its sync counts the last arrow as "gone" from its old cells, which is harmless because it is free.
- Not settled: whether the game re-centres by itself at all. That still needs the phone.

## Per level

### L31

- **Source frames**: V2 19:44.04 (1184.037 s, `video-frames/V2/L031-start.png`, the frame 0.10 s before the first tap); elevator 0 hidden layer read at 20:03.04 (`video-frames/V2/L031-elevator0-reveal.png`).
- **Board**: 16x17 cells, 28 arrows at start + 7 hidden-layer arrows, 272 arrow cells, arrow length 4-34 (median 8.0), heads up/down/left/right 11/4/8/5; pitch 21.828 pt.
- **Obstacles**: elevator 0: 84-cell platform (2 doors), 9 platform arrows, 7 hidden arrows (ids 28-34).
- **Timer / hearts / tag**: 3:00 / 3 -> 3 / none. Reward 20.
- **Play in V2**: first tap 19:44.14, cleared 20:07.51 (23.4 s of play), 2:36 left on the clock, 31 taps; win panel 20:08.16.
- **Tutorial**: the Elevator unlock popup before the level (timeline in "Tutorial" above); no hand, no in-board caption.
- **Ink IoU (1 px tol)**: start frame 0.9829 / 0.9885 / 0.9887 (vextract / registered / model), heads flagged 0; hidden layer 0 at its reveal frame 0.9836 / 0.9909 / 0.9909, hidden heads flagged 0.
- **Replay**: 31 taps; 35 consistent (28 exits on free arrows, 0 bumps on blocked arrows, 7 untapped exits all free), **0 inconsistent**, 3 miss, left at end none.
- **Obstacle events (model, in video order)**: elevator 0 live at 20:01.81 (7 arrows).
- **Solver**: bot plan solved (35 taps, elevator heuristic deferred the last platform arrow 1 x; also solved without it), rule model solved (35 taps, greedy); 8 units free at start; 12 waves; random order dead-ends 0/300.
- **Fixes**: none to cells, arrows or obstacles. Robust grid refit changed only the transform (resid 0.85 -> 0.36 px).
- **Notes**: Replay misses (3): touches 0.75-0.79 cell from arrows 8, 18, 28, each found gone at the next sync = the real tap, just outside the replay radius.

### L32

- **Source frames**: V2 20:16.38 (1216.379 s, `video-frames/V2/L032-start.png`, the frame 0.10 s before the first tap); elevator 0 hidden layer read at 20:35.88 (`video-frames/V2/L032-elevator0-reveal.png`).
- **Board**: 17x21 cells, 29 arrows at start + 11 hidden-layer arrows, 355 arrow cells, arrow length 2-52 (median 7), heads up/down/left/right 13/2/12/2; pitch 20.667 pt.
- **Obstacles**: elevator 0: 104-cell platform (2 doors), 8 platform arrows, 11 hidden arrows (ids 29-39).
- **Timer / hearts / tag**: 3:00 / 3 -> 1 (heart drops at 20:35.28, 20:49.44) / none. Reward 20.
- **Play in V2**: first tap 20:16.50, cleared 20:51.34 (34.8 s of play), 2:26 left on the clock, 41 taps; win panel 20:51.67.
- **Tutorial**: none (no popup; first elevator repeat).
- **Ink IoU (1 px tol)**: start frame 0.9684 / 0.9820 / 0.9896 (vextract / registered / model), heads flagged 0; hidden layer 0 at its reveal frame 0.9506 / 0.9772 / 0.9772, hidden heads flagged 0.
- **Replay**: 41 taps; 42 consistent (37 exits on free arrows, 2 bumps on blocked arrows, 3 untapped exits all free), **0 inconsistent**, 2 miss, left at end none.
- **Obstacle events (model, in video order)**: elevator 0 live at 20:34.50 (11 arrows).
- **Solver**: bot plan solved (40 taps, elevator heuristic deferred the last platform arrow 12 x; also solved without it), rule model solved (40 taps, greedy); 4 units free at start; 16 waves; random order dead-ends 0/300.
- **vs the phone (v552)**: `levels/video/diff-L032.md`: DIFFERENT LEVELS (1 identical arrow at the best shift). Over every phone level L032-L061 x 8 symmetries the best is 2 of 29 arrows (`L044.json`).
- **Fixes**: none (resid 0.82 -> 0.31 px).
- **Notes**: Hidden layer check at 1235.879: the 501-px residual at (346,491) is arrow 16 drawn BLACK after its bump at 1235.107 (V2 redraws a bumped arrow black until it leaves, 1241.345); the ink mask counts blue only. Elevator timing (work/D/L032-elevator.png, L032-doors-fine.png): last platform arrow 14 tapped 1234.504, its tail leaves the platform 1235.05, the doors start parting from the centre 1235.07, the bump touch on arrow 16 lands 1235.10 (red vignette 1235.19). Arrow 16 is blocked by hidden arrows 29/30/32/36 lying under the LEFT door, still closed at that moment: the hidden layer blocks from the start of the door animation, before it is visible. Replay misses (2): touches 0.79 and 0.95 cell from arrows 3 and 22 (found gone at the next sync).

### L33

- **Source frames**: V2 20:59.17 (1259.167 s, `video-frames/V2/L033-start.png`, the frame 0.10 s before the first tap); elevator 0 hidden layer read at 21:52.67 (`video-frames/V2/L033-elevator0-reveal.png`); elevator 1 hidden layer read at 21:33.17 (`video-frames/V2/L033-elevator1-reveal.png`).
- **Board**: 17x23 cells, 36 arrows at start + 17 hidden-layer arrows, 315 arrow cells, arrow length 2-29 (median 5.0), heads up/down/left/right 7/15/5/9; pitch 20.666 pt.
- **Obstacles**: box 41 (18 cells); box 28 (18 cells); box 18 (18 cells); box 13 (18 cells); elevator 0: 78-cell platform (2 doors), 9 platform arrows, 8 hidden arrows (ids 36-43); elevator 1: 78-cell platform (2 doors), 8 platform arrows, 9 hidden arrows (ids 44-52).
- **Timer / hearts / tag**: 3:00 / 3 -> 3 / none. Reward 20.
- **Play in V2**: first tap 21:00.24, cleared 21:58.57 (58.3 s of play), 2:02 left on the clock, 47 taps; win panel 21:59.21.
- **Tutorial**: none.
- **Ink IoU (1 px tol)**: start frame 0.9663 / 0.9838 / 0.9840 (vextract / registered / model), heads flagged 0; hidden layer 0 at its reveal frame 0.9505 / 0.9773 / 0.9850, hidden heads flagged 0; hidden layer 1 at its reveal frame 0.9424 / 0.9815 / 0.9838, hidden heads flagged 0.
- **Replay**: 47 taps; 53 consistent (45 exits on free arrows, 0 bumps on blocked arrows, 8 untapped exits all free), **0 inconsistent**, 1 miss, left at end none, box breaks confirmed 4.
- **Obstacle events (model, in video order)**: box 13 breaks at 21:11.64 on the exit of arrow 34; box 18 breaks at 21:17.44 on the exit of arrow 1; box 28 breaks at 21:28.07 on the exit of arrow 23; box 41 breaks at 21:46.40 on the exit of arrow 51; elevator 1 live at 21:32.03 (9 arrows); elevator 0 live at 21:53.09 in the replay walk (8 arrows; the log removes platform arrow 7 only at the drop; on frames it left at 21:51.55 and the doors opened at ~21:51.70); 4 exits of OUTSIDE arrows crossed an unopened platform (arrows 20, 49, 51, 0).
- **Solver**: bot plan solved (53 taps), rule model solved (53 taps, greedy); 8 units free at start; 22 waves; random order dead-ends 0/300; box slack (counter -> largest solvable) 41->41, 28->28, 18->18, 13->14; unsolvable if boxes never break.
- **vs the phone (v552)**: `levels/video/diff-L033.md`: DIFFERENT LEVELS (1 identical arrow at the best shift). Over every phone level L032-L061 x 8 symmetries the best is 2 of 36 arrows (`L060.json`).
- **Fixes**: none (resid 0.89 -> 0.37 px).
- **Notes**: The one replay "stay" (arrow 7, tap 1311.546) is a real exit: frames (work/D/L033-arrow7.png) show it rainbow and leaving at 1311.55; it is elevator 0's last platform arrow, the doors part at ~1311.70 and the new layer is drawn over its cells by 1311.85, so the +0.3 s presence read 0.33 (threshold 0.30). No unexplained tap remains. Replay miss (1): touch 0.85 cell from arrow 32 (found gone at the next sync).

### L34

- **Source frames**: V2 22:10.78 (1330.777 s, `video-frames/V2/L034-start.png`, the frame 0.10 s before the first tap).
- **Board**: 18x23 cells, 40 arrows at start, 408 arrow cells, arrow length 4-46 (median 6.5), heads up/down/left/right 23/7/5/5; pitch 19.635 pt.
- **Obstacles**: 4 Linked ties of 3 (12 taped arrows).
- **Timer / hearts / tag**: 3:00 / 3 -> 3 / none. Reward 20.
- **Play in V2**: first tap 22:10.88, cleared 22:43.87 (33.0 s of play), 2:27 left on the clock, 30 taps; win panel 22:44.55.
- **Tutorial**: none (Linked ties, introduced in V1 at L7).
- **Ink IoU (1 px tol)**: start frame 0.9766 / 0.9899 / 0.9899 (vextract / registered / model), heads flagged 0.
- **Replay**: 30 taps; 36 consistent (30 exits on free arrows, 0 bumps on blocked arrows, 6 untapped exits all free), **0 inconsistent**, 0 miss, left at end none.
- **Solver**: bot plan solved (32 taps), rule model solved (32 taps, greedy); 5 units free at start; 13 waves; random order dead-ends 0/300.
- **vs the phone (v552)**: `levels/video/diff-L034.md`: DIFFERENT LEVELS (1 identical arrow at the best shift). Over every phone level L032-L061 x 8 symmetries the best is 5 of 40 arrows (`L057.json`).
- **Fixes**: none (resid 0.89 -> 0.27 px).
- **Notes**: No misses; 4 Linked ties of 3 arrows each (bundles 1/3/5, 12/16/19, 29/31/34, 36/37/39).

### L35

- **Source frames**: V2 22:59.07 (1379.065 s, `video-frames/V2/L035-start.png`, the frame 0.10 s before the first tap); elevator 0 hidden layer read at 24:03.82 (`video-frames/V2/L035-elevator0-reveal.png`).
- **Board**: 20x32 cells, 57 arrows at start + 39 hidden-layer arrows, 613 arrow cells, arrow length 3-43 (median 7), heads up/down/left/right 12/11/8/26; pitch 17.845 pt.
- **Obstacles**: elevator 0: 320-cell platform (2 doors), 29 platform arrows, 39 hidden arrows (ids 57-95); pipe 0: counter 3, 26 cells, mouths (0,12) out up + (19,12) out up.
- **Timer / hearts / tag**: 3:00 / 3 -> 3 / Hard Level. Reward 60.
- **Play in V2**: first tap 22:59.17, cleared 24:56.46 (117.3 s of play), 1:03 left on the clock, 89 taps; win panel 24:57.13.
- **Tutorial**: none; first V2 "Hard Level" of this batch (red tab + red HUD buttons, reward 60), no popup.
- **Ink IoU (1 px tol)**: start frame 0.9854 / 0.9931 / 0.9931 (vextract / registered / model), heads flagged 0; hidden layer 0 at its reveal frame 0.9760 / 0.9892 / 0.9892, hidden heads flagged 0.
- **Replay**: 89 taps; 96 consistent (85 exits on free arrows, 0 bumps on blocked arrows, 11 untapped exits all free), **0 inconsistent**, 4 miss, left at end none, board re-registered 1 x.
- **Obstacle events (model, in video order)**: pipe 0 breaks on its 3rd pass (arrow 1, tap 23:31.68); elevator 0 live at 24:07.22 (39 arrows); 1 exits of OUTSIDE arrows crossed an unopened platform (arrows 32).
- **Solver**: bot plan solved (96 taps, elevator heuristic deferred the last platform arrow 2 x; also solved without it), rule model solved (96 taps, greedy); 8 units free at start; 44 waves; random order dead-ends 0/300; unsolvable if the pipes never break.
- **vs the phone (v552)**: `levels/video/diff-L035.md`: DIFFERENT LEVELS (1 identical arrow at the best shift). Over every phone level L032-L061 x 8 symmetries the best is 2 of 57 arrows (`L061.json`).
- **Fixes**: **pipe mouths moved up one row**: cells (0,12) and (19,12) added, ends (0,13)/(19,13) up -> (0,12)/(19,12) up (the reader dropped the cap cells of both vertical legs; see "Reader error found"). Behaviour-relevant: arrow 16 (row 12, head (2,12) left) points into the left cap cell from the side and is blocked by it while the pipe lives. Resid 0.86 -> 0.32 px.
- **Notes**: Board pan 1479.3-1480.9 (work/D/L035-pan.png, L035-pan2.png): the board wobbles up/right, back, right/down, back, then settles +44.8 px right / +3 px down, pitch unchanged (26.88 -> 26.91 px). No touch disc is drawn. It looks like a manual drag with rubber-band limits, not an automatic re-centre; the replay re-registers the grid at 1486.318 (first tap after it). Replay misses (4): touches 0.76-0.95 cell from arrows 38, 8, 57, 16 (each found gone at the next sync). Pipe: passes by arrows 5 (tap 1409.899), 3 (1411.206), 1 (1411.676); the badge counts 3 -> 2 at ~1410.5 and 2 -> 1 at ~1411.9, each when the arrow comes out of the far mouth; the pipe shatters ~1412.3 (work/D/L035-pipe-break.png). The replay does not check pipe breaks (the model drops the pipe first); checked on frames. An outside arrow (32, tap 1436.675) slid straight over the platform (closed doors, 8 platform arrows still on it) and off the board (work/D/L035-cross32.png): empty platform cells do not block rays.

### L36

- **Source frames**: V2 25:06.21 (1506.206 s, `video-frames/V2/L036-start.png`, the frame 0.10 s before the first tap).
- **Board**: 20x23 cells, 36 arrows at start, 458 arrow cells, arrow length 2-52 (median 7.5), heads up/down/left/right 15/14/1/6; pitch 17.852 pt.
- **Obstacles**: none.
- **Timer / hearts / tag**: 3:00 / 3 -> 3 / none. Reward 20.
- **Play in V2**: first tap 25:06.31, cleared 25:39.13 (32.8 s of play), 2:28 left on the clock, 36 taps; win panel 25:39.81.
- **Tutorial**: none.
- **Ink IoU (1 px tol)**: start frame 0.9795 / 0.9907 / 0.9907 (vextract / registered / model), heads flagged 0.
- **Replay**: 36 taps; 36 consistent (33 exits on free arrows, 0 bumps on blocked arrows, 3 untapped exits all free), **0 inconsistent**, 3 miss, left at end none.
- **Solver**: bot plan solved (36 taps), rule model solved (36 taps, greedy); 3 units free at start; 14 waves; random order dead-ends 0/300.
- **vs the phone (v552)**: `levels/video/diff-L036.md`: DIFFERENT LEVELS (1 identical arrow at the best shift). Over every phone level L032-L061 x 8 symmetries the best is 2 of 36 arrows (`L057.json`).
- **Fixes**: none (resid 0.63 -> 0.34 px).
- **Notes**: Replay misses (3): touches 0.88-0.96 cell from arrows 18, 25, 0 (each found gone at the next sync).

### L37

- **Source frames**: V2 25:49.24 (1549.245 s, `video-frames/V2/L037-start.png`, the frame 0.10 s before the first tap).
- **Board**: 20x33 cells, 55 arrows at start, 602 arrow cells, arrow length 2-48 (median 7), heads up/down/left/right 14/14/9/18; pitch 17.853 pt.
- **Obstacles**: box 52 (28 cells); box 35 (28 cells).
- **Timer / hearts / tag**: 3:00 / 3 -> 3 / none. Reward 20.
- **Play in V2**: first tap 25:49.35, cleared 26:59.66 (70.3 s of play), 1:49 left on the clock, 54 taps; win panel 27:00.30.
- **Tutorial**: none.
- **Ink IoU (1 px tol)**: start frame 0.9793 / 0.9906 / 0.9917 (vextract / registered / model), heads flagged 0.
- **Replay**: 54 taps; 55 consistent (53 exits on free arrows, 0 bumps on blocked arrows, 2 untapped exits all free), **0 inconsistent**, 1 miss, left at end none, box breaks confirmed 2.
- **Obstacle events (model, in video order)**: box 35 breaks at 26:36.34 on the exit of arrow 6; box 52 breaks at 26:57.77 on the exit of arrow 8.
- **Solver**: bot plan solved (55 taps), rule model solved (55 taps, greedy); 7 units free at start; 23 waves; random order dead-ends 0/300; box slack (counter -> largest solvable) 52->52, 35->35; unsolvable if boxes never break.
- **vs the phone (v552)**: `levels/video/diff-L037.md`: DIFFERENT LEVELS (1 identical arrow at the best shift). Over every phone level L032-L061 x 8 symmetries the best is 2 of 55 arrows (`L060.json`).
- **Fixes**: none (resid 0.64 -> 0.32 px).
- **Notes**: Replay miss (1): touch 0.76 cell from arrow 39 (found gone at the next sync).

### L38

- **Source frames**: V2 27:11.10 (1631.100 s, `video-frames/V2/L038-start.png`, the frame 0.10 s before the first tap).
- **Board**: 16x20 cells, 34 arrows at start, 290 arrow cells, arrow length 2-33 (median 6.0), heads up/down/left/right 6/12/5/11; pitch 21.826 pt.
- **Obstacles**: pipe 0: counter 3, 14 cells, mouths (15,4) out down + (10,4) out down; pipe 1: counter 3, 14 cells, mouths (0,15) out up + (5,15) out up.
- **Timer / hearts / tag**: 3:00 / 3 -> 3 / none. Reward 20.
- **Play in V2**: first tap 27:11.20, cleared 27:51.34 (40.1 s of play), 2:20 left on the clock, 33 taps; win panel 27:51.57.
- **Tutorial**: none.
- **Ink IoU (1 px tol)**: start frame 0.9674 / 0.9893 / 0.9893 (vextract / registered / model), heads flagged 0.
- **Replay**: 33 taps; 34 consistent (32 exits on free arrows, 0 bumps on blocked arrows, 2 untapped exits all free), **0 inconsistent**, 1 miss, left at end none.
- **Obstacle events (model, in video order)**: pipe 0 breaks on its 3rd pass (arrow 25, tap 27:35.18); pipe 1 breaks on its 3rd pass (arrow 2, tap 27:46.71).
- **Solver**: bot plan solved (34 taps), rule model solved (34 taps, greedy); 6 units free at start; 12 waves; random order dead-ends 0/300; unsolvable if the pipes never break.
- **vs the phone (v552)**: `levels/video/diff-L038.md`: DIFFERENT LEVELS (1 identical arrow at the best shift). Over every phone level L032-L061 x 8 symmetries the best is 2 of 34 arrows (`L054.json`).
- **Fixes**: **bottom pipe: left mouth moved up one row**: cell (0,15) added, end (0,16) up -> (0,15) up (the badge cell had been read as the mouth). Behaviour unchanged in this level (no ray crosses (0,15) sideways), geometry now as drawn. Resid 1.20 -> 0.35 px.
- **Notes**: Pipe 0 (top, inverted U): passes by 23 (1651.94), 24 (1654.875), 25 (1655.176); badge 2 -> 1 at ~1655.4 when 24 comes out of the right mouth; shatters at 1655.8 as 25 comes out (work/D/L038-pipe0.png). Pipe 1 (bottom U): passes by 6 (1665.136), 4 (1666.376), 2 (1666.712); badge 2 -> 1 at ~1666.9; shatters 1667.3 (work/D/L038-pipe1.png). Arrows are drawn travelling THROUGH the tube. The last replay "miss" (1670.937) is the real tap on the last arrow 8: the player dragged the board around at 1669.4-1671.0 (work/D/L038-move.png, L038-last.png; no zoom, no touch disc), so the sync saw arrow 8 "gone" from its old cells; the frames show the touch on arrow 8 and it leaving at 1671.00-1671.10.
