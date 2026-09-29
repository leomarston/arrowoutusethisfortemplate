# Video levels — batch A (levels 1-10, V1)

Author: level extractor batch A, 2026-09-25. Owner-facing name **Arrow Out**; the video shows the original "Maze Out!". Content only:
video frames were measured and looked at, never shipped or traced.

**Result: L1-L10 are final in `research/levels/L001.json` … `L010.json` (phone schema, `source:"video"`, `video:"V1"`).**
- 10 boards, 182 arrows, 9 Linked ties. No other obstacles appear in L1-L10.
- The index agent's reading was right everywhere: **no arrow, cell, direction or tie needed a hand edit.** Every board was checked by
  eye (zoomed side by side with the model) and by an ink diff.
- What changed is geometry and metadata only:
  - a sub-pixel grid re-fit of every board (cells unchanged);
  - `occlusion_inferred` moved into the level's own cell frame;
  - the video facts added: label and session, tutorial, unlock popup, timer, reward, play times, and a `checks` block.
- **Replay check: 0 contradictions in 10 of 10 levels.** Every arrow the video removes is free in our model when it leaves. There are
  no bumps in V1, so no bump could be tested.
- **Both solvers** (bot.py rules and the replay model's rules) clear every board.
- **Ink IoU with 1-px tolerance: at least 0.984 on every board** with the shading-aware render. With vextract's standard renderer on
  the final fit it is at least 0.978 on L2-L6 and L8-L10. It is 0.963 on L7 and 0.953 on L1; both are explained below by how the
  video skin draws strokes and heads, not by the model.
- V1 L1-L10 match none of the phone's recorded levels (L32-L61) and no V2 board (vmatch best score 0.06). They exist only in V1.

## Files
- `research/levels/L001.json` … `L010.json`: final.
  - Extra keys beyond the phone schema:
    - `label`; `session` (L1-L4 only); `reward_coins`;
    - `tutorial` (L1) and `intro_popup` (L7);
    - `checks` (IoU, replay, solvers);
    - `video_play` (times, timer, taps);
    - `verify.index_fit` / `verify.shading_aware`, and `fit_px.refined` / `fit_px.note`.
  - Arrow ids are the index agent's ids, so they match the replay reports.
- Gitignored, in `research/video-frames/work/levels-A/`:
  - `L0NN-look.png`: frame crop | model with ids, tails circled, row and column numbers.
  - `L0NN-look-diff.png` and `L0NN-shade-diff.png`: red = frame ink the model does not draw, orange = model ink the frame lacks.
  - Evidence sheets: `L001-fit-compare.png`, `L001-hand-shadow-1.64.png`, `L001-hand-ripple-vs-tap.png`, `L007-bundle-exit.png`,
    `L007-miss-84.92.png`.
  - `tools/`:
    - scripts: `atool.py` (look sheets, bot-rule solver), `refine.py`, `shade.py` (shading-aware IoU), `build.py` (writes the final
      JSON), `validate.py`, `replayA.py`, `tick.py` (first timer tick);
    - data: `shadeNN.json`, `refNN.json` and `replay-L0NN.json` (my replay reports against the final JSONs).
  - The tools live in the gitignored cache so that I touch no shared folder. Move them into `research/video-tools/` if they should be
    committed.

## How each level was checked
1. **Start frame.** I used the index's clean start frame (`video-frames/V1/L0NN-start.png`, full res), which is taken just before the
   first tap.
   - L1 is taken at 0.72 s. The arrows are fully grown at 0.68 s (heads are still small at 0.60 s), and the hint hand appears at
     0.80 s.
   - L7's frame is 0.12 s before the first tap. The unlock overlay has fully faded by then (checked by eye).
2. **Read by eye.** I traced every arrow of L1-L5, L7 and L8 on a zoomed side-by-side against the frame (path, tail, head,
   direction), and checked L6, L9 and L10 on 1.3× zoomed diffs.
   - Each arrow in the model is one connected path with its head on one end. Wrong splitting, merging, or a reversed head would
     therefore show up in the diff: a stroke across a gap, a missing stroke, or a head at the wrong end.
   - No such mark appears anywhere. The only diff pixels are 1-2 px fringes on stroke edges and head tips.
3. **Integrity** (`validate.py`):
   - every step is 4-adjacent, no cell is used twice, every cell is inside the grid;
   - each head points along the last segment, and no ray crosses its own body.
   - All 10 boards: 0 problems.
4. **Grid re-fit.** The pitch and origin were re-fitted sub-pixel to the start-frame ink (`shade.py`, 4× supersampled render). On
   L2-L10 the grid moved by at most 1.2 px at any corner cell (L7 row 0) and the pitch by at most 0.15 px. The cells were never
   changed.
   - **L1 is the exception.** Three vertical arrows cannot fix their own vertical origin: the free fit traded it against the head
     shading (pitch 43.05 px, row 0 at 596.6 px). L1 uses the layout rule below instead: pitch 28.071 pt, cell-centre box centred
     at (196.25, 437.3) pt, so col 0 is at 253.3 px and row 0 at 595.3 px.
   - Direct measurement agrees within 1.3 px: column centres 253.0 / 295.5 / 337.5 px, and row 0 at 594.0 ± 1.5 px from the tail
     caps.
   - This fit scores the best raw IoU of the three candidates (rule 0.933, measured 0.919, free fit 0.854);
     `L001-fit-compare.png` shows the free fit misplacing tails and heads.
5. **Ink IoU**, three ways (`checks.ink_iou_tol1`):
   - vextract.verify at the index fit;
   - vextract.verify at the final fit;
   - **shading-aware**: the same cells drawn with separate widths for vertical and horizontal strokes and a head size per direction.

   **Why the standard renderer tops out at about 0.96-0.99 here.** The video skin shades every stroke:
   - a cyan glow on top and a dark navy rim below, which the ink mask leaves out;
   - so horizontal strokes read 1-1.5 px thinner than vertical ones (L7: 8.25 vs 6.75 px; histogram on L2: vertical 8-9 px,
     horizontal 7-8 px);
   - and down and right heads read longer than up heads (tip 0.46-0.50 vs 0.34 pitch).

   The centres are unbiased: a horizontal stroke's ink is lost equally at the top and bottom edges (L2 profile: glow 547-548, core
   550-556, rim 557).
6. **Replay check** (`vextract.py replay V1 N --json research/levels/L0NN.json`) against the video's own play-through. The checks:
   every exit free, every bump blocked, every vanished arrow free, nothing left at the end.
7. **Solvers.** Greedy with bot.py's `ray` and tie groups (`atool.py solve`), and greedy with `vextract.Model` (the replay's rules).
   Both report the same result for every board, and none leaves an arrow. "Waves" = dependency depth, counted as rounds of
   simultaneously free units.

## Summary

| lvl | in-level label | grid | arrows (cells) | ties | pitch pt | IoU idx / final / shading | replay (taps, consistent, contradictions) | free at start / waves | video: board → clear, left |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Levels 1-4 (stage 1) | 3×4 | 3 (12) | – | 28.071 | 0.868 / 0.953 / 0.984 | 4, 3, 0 | 3 / 1 | 0.72 → 5.20, 2:59 |
| 2 | Levels 1-4 (stage 2) | 6×6 | 6 (36) | – | 28.049 | 0.966 / 0.978 / 0.990 | 6, 6, 0 | 1 / 4 | 7.92 → 10.36, 2:58 |
| 3 | Levels 1-4 (stage 3) | 10×9 | 8 (90) | – | 28.124 | 0.980 / 0.986 / 0.992 | 6, 8, 0 | 2 / 3 | 12.32 → 17.44, 2:56 |
| 4 | Levels 1-4 (stage 4) | 9×14 | 8 (126) | – | 28.067 | 0.982 / 0.988 / 0.995 | 5, 8, 0 | 1 / 4 | 19.36 → 24.12, 2:56 |
| 5 | Level 5 | 12×14 | 17 (167) | – | 28.105 | 0.976 / 0.979 / 0.992 | 15, 17, 0 | 6 / 8 | 30.12 → 41.64, 2:50 |
| 6 | Level 6 | 27×22 | 29 (394) | – | 13.559 | 0.987 / 0.990 / 0.999 | 27, 29, 0 | 11 / 10 | 46.60 → 69.08, 2:38 |
| 7 | Level 7 | 10×15 | 18 (134) | 4 pairs | 28.074 | 0.969 / 0.963 / 0.992 | 13, 15, 0 | 3 / 9 | 81.04 → 91.32, 2:50 |
| 8 | Level 8 | 12×17 | 19 (202) | 2 pairs | 28.070 | 0.971 / 0.978 / 0.993 | 15, 17, 0 | 3 / 7 | 99.00 → 109.52, 2:50 |
| 9 | Level 9 | 14×19 | 27 (261) | – | 24.550 | 0.975 / 0.978 / 0.994 | 27, 27, 0 | 7 / 10 | 120.12 → 135.68, 2:44 |
| 10 | Level 10 | 20×22 | 47 (391) | 3 quads | 17.857 | 0.982 / 0.988 / 0.997 | 35, 38, 0 | 9 / 14 | 143.44 → 176.24, 2:27 |

- Every level has timer 3:00 (`timer_s` 180, frozen until the first tap), 3 hearts, no tag and no heart lost.
- Rewards: 20 per level for L5-L10; the "Levels 1-4" session pays 80 once, on its win panel.
- "consistent" = legal exits of tapped units (a bundle tap counts once) + arrows seen gone at a later sync, each counted.

## Findings that apply beyond L1-L10 (for the spec lanes)

### 1. Board layout rule: `pitch = 393 pt / max(14, cols + 2)`, cell box centred
The pitch depends only on the column count: the board spans the screen width with one empty cell of margin on each side, and never
grows beyond 14 columns' worth (28.071 pt). Checked on 50 boards:
- video L1-L20: all 20 within ±0.19 %;
- phone L32-L61 (30 files): all within ±0.10 %.
- Examples: 27 cols → 13.552 (L6 reads 13.559); 20 cols → 17.864 (L10 17.857, phone L33 17.857); 14 cols → 24.562 (L9 24.550);
  36-row phone boards → 15.115 (L49 15.127).
- **Rows never limit the pitch** in any level seen, including 20×31 and 24×36 boards.

The centre of the box through the cell centres is **(196.2, 437.3) pt** in both videos (L2-L20: x 196.0-196.3, y 437.2-437.7) and
**(196.5, 439.2) pt** on the phone (v552: x 196.3-196.6, y 439.1-439.4; its HUD differs). Our layout: `pitch = W / max(14, cols + 2)` (W = 393 on this phone; scale with the width), and
the cell box centred at x = W/2, y = the phone's 439.2 pt (on an 852-pt screen).

### 2. Linked Arrows (the phone's `tape_pink`): geometry and behaviour seen in L7, L8, L10
- **Tie placement.** A bundle is straight, parallel, equal-length arrows in adjacent rows or columns, all pointing the same way:
  2 or 4 of them in V1, and 2, 3 or 4 on the phone. The tie covers exactly one cell of each: the cell right behind the head, index
  `len-2`.
  - Seen on all 9 V1 bundles (arrow lengths 3, 4, 5 and 6).
  - Seen on all 19 bundles recorded on the phone: L32 4×4, L38 3×2, L44 4×3, L57 4×2, L61 4×2; always 4-cell arrows with the tie
    on cell index 2.
  - A level generator should keep this rule.
- **One tap moves the bundle.** The whole bundle leaves together and the tie travels with it (`L007-bundle-exit.png`: V1 81.08-81.36,
  both arrows plus the tie slide up and out in about 0.2 s).
- **The tie itself is tappable.** 6 of the 9 bundle taps in V1 landed on the tie, not on an arrow: L7 81.16 and 82.68, L8 102.24 and
  108.36, L10 143.56, 167.32 and 173.4. One more (L7 86.88) landed 7 px above the tie, between the two arrows. The tie must be part
  of the bundle's hit area.
- Every bundle exit in V1 was free in the model. **A bundle with one member blocked was never tapped**, so "bump if any member is
  blocked" is still unverified in the videos (obstacles.md says the same for the phone).

### 3. Hit tolerance: touches 12-22 pt from a stroke still take the arrow
The replay maps a touch to an arrow only within 0.75 cell. Some touches landed farther away, and the nearest free arrow then left
before the next tap anyway. Evidence (touch → arrow that left, distance to that arrow's stroke):

| level | touch t | distance | arrow gone within |
|---|---|---|---|
| L4 | 22.20 | 17.1 pt | 0.76 s |
| L6 | 46.88 | 13.2 pt | 0.72 s |
| L6 | 48.84 | 11.9 pt | 0.32 s |
| L6 | 64.00 | 14.1 pt | 0.96 s |
| L6 | 65.08 | 17.0 pt | 0.80 s |
| L7 | 84.92 | 21.6 pt | 0.76 s |
| L8 | 108.80 | 17.1 pt | 0.52 s |
| L9 | 120.24 | 16.4 pt | 0.32 s |
| L10 | 155.32 | 15.0 pt | 1.24 s |
| L10 | 158.48 | 13.2 pt | 0.28 s |
| L10 | 163.40 | 13.7 pt | 0.56 s |
| L10 | 174.52 | 17.0 pt | 0.60 s |

The clearest case is L7 84.92, shown in `L007-miss-84.92.png`:
- the touch disc lands on column 0, which is already empty (its arrow left earlier);
- arrow 3, 21.6 pt to the right, starts to leave on the same frame;
- no heart is lost and no other arrow moves.

So the original picks the nearest arrow within at least ~22 pt of the touch point. This assumes the recorder's disc sits on the
touch point. It is a lower bound on the radius, not a measured radius. The phone lane can pin it with deliberate off-stroke taps.

### 4. Tutorial hand (L1): two corrections to the index
- The index's first L1 "tap" (1.64 s at 329,750 px) is **the hand's drop shadow**, not a touch (`L001-hand-shadow-1.64.png`). The first
  real tap is at 3.48-3.52 s, on the hinted middle arrow.
- **The hand's press emits a tap ripple.** At the bottom of the press (1.84 s), a grey disc appears at the fingertip at 1.88 s. It grows
  and fades by 2.04-2.08 s: a dark core with a lighter halo, lasting about 0.16-0.2 s. That is the same look and duration as the real
  tap ripple at 3.52-3.68 s (`L001-hand-ripple-vs-tap.png`, top row hand, bottom row real tap).
  - The ripple appears exactly at the fingertip at the exact bottom of the press, and the arrow does not move. It is therefore part
    of the hint animation, not a player touch.
  - So the video says nothing about whether input is locked during the hint.
  - Build the press loop as: shrink 0.48 s → ripple at the fingertip → release 0.36 s (with tutorials.md §3's timings).
- Fingertip: the up-left extreme of the index finger at full size is (193.2, 424.9) pt = cell (0.89, 1.06) in L001's frame. The finger
  pad lies on the middle arrow (col 1) one cell below its head. This agrees with tutorials.md's (193, 424).

### 5. Timer: the first 3:00 → 2:59 tick after the first tap
Measured by frame difference on the timer digits at 25 fps (`tick.py`). The first real board tap → the first tick:

| level | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 |
|---|---|---|---|---|---|---|---|---|---|---|
| delay s | 0.60 | 0.04 | 0.68 | 0.68 | 0.96 | 0.32 | 0.20 | 0.36 | 0.32 | 0.12 |

- L11-L20 (same method, for the timer rule only; batch B owns those boards): 0.08, 0.80, 0.56, 1.00, 0.72, 0.48, 0.08, 0.04, 0.60,
  0.00.
- After the first tick, ticks come every 1.00 s. The delay takes values from 0.00 to 1.00 s and is not tied to the tap.
- Across L1-L10 the tick phase (tick time mod 1 s) drifts slowly and steadily: 0.08, 0.08, 0.12, 0.16, 0.20, 0.20, 0.36, 0.48, 0.56,
  0.68. That fits **a free-running 1 Hz clock that the countdown joins at the first tap**. Later levels no longer follow a smooth
  drift, probably because of edit cuts (V1 is a YouTube edit, with a cut inside L17).
- Build it as: after the first tap, decrement on the next tick of a 1 Hz clock that is not re-phased per level. A uniform random
  0-1 s first delay looks the same.

### 6. The dot grid
Vacated cells show faint dots. The dots are exactly the level's arrow cells: on L6 (the heart), the dots fill the heart, and the only
two interior cells no arrow covers, (6,13) and (10,17), show no dot. No separate `mask` is needed; the silhouette is the union of the
start arrows' cells (`mask: null` stays correct).

## Level by level

### L1: "Levels 1-4", stage 1 (the first thing a new player sees)
- **Source:**
  - V1: board fades in from Loading at 0.44 s, built by 0.68, start frame 0.72 (`video-frames/V1/L001-start.png`);
  - first real tap 3.48-3.52; cleared ≈5.08-5.20.
- **Board:** 3×4, 3 arrows of 4 cells in adjacent columns: col 0 ↓ (id 0), col 1 ↑ (id 1, the hinted one), col 2 ↓ (id 2). All three
  are free (1 wave), so no wrong tap is possible.
- **Timer / hearts / tag:** 3:00 frozen until the tap at 3.48, first tick 4.08 (0.60 s), 2:59 at clear; 3 hearts; no tag.
- **Tutorial:** caption **"Tap to move!"** plus the pointing hand on arrow 1, both at 0.80 s (0.36 s after the board). There is no dim
  and no spotlight. On the first tap the caption scales out and the hand fades.
  - Animation, font and art: tutorials.md §3. New here: the press ripple and the shadow "tap" (§4 above).
  - `tutorial` block in L001.json.
- **Session:**
  - one session, "Levels 1-4": four boards back to back with no panel between them;
  - the HUD label reads "Levels 1-4" on all four;
  - each board restarts the timer at 3:00 and freezes it until its first tap;
  - `session` block in L001-L004.
- **IoU:** index fit 0.868 → final 0.953 (vextract) / 0.984 (shading-aware).
  - Three arrows are only 4415 ink px, and the heads are about a quarter of that, so the symmetric-head renderer loses the most here.
  - The fit is the layout-rule fit (see How each level was checked, item 4).
- **Replay:** 4 disc events. The 1.64 shadow did nothing (`stay_weak`); 3.52 took arrow 1 ↑, 4.24 arrow 0 ↓, 4.84 arrow 2 ↓, all free.
  0 contradictions.
  - This replay samples pixels with the index fit (same cells). With the final fit, the hand covering arrow 1 from 0.80 to 3.64 s
    makes its presence test read "gone" at 1.52 s; that is a tool artefact.
- **Solver:** both solvers, 1 wave.
- **Fixes:** none to the cells. Grid fit replaced (item 4 of How each level was checked).

### L2: "Levels 1-4", stage 2
- **Source:** V1 board appears 5.80 s (dots, then arrows grow tail→head, done ≈6.12-6.24); start frame 7.92; first tap 8.04; clear
  10.36.
- **Board:** 6×6, 6 arrows of 2-11 cells:
  - three nested Γ shapes (up the left side, then along the top) pointing → (ids 0, 1, 3; 11, 7 and 5 cells);
  - a ┘ shape (down the right side, then along the bottom) pointing ← (id 2, 9 cells);
  - two 2-cell ↑ in the middle.
  - Only the outer Γ (id 0) is free at start; 4 waves.
- **Timer:** 3:00 → first tick 8.08 (0.04 s after the tap) → 2:58 at clear. 3 hearts, no tag.
- **Tutorial:** none (no caption, no hand).
- **IoU:** 0.966 → 0.978 / 0.990. The re-fit (pitch +0.10 px, grid moved by at most 0.75 px) removes most of the fringe the index
  fit left on the stroke edges.
- **Replay:** 6 taps, 6 exits, all free. 0 contradictions.
- **Solver:** 4 waves, both solvers.
- **Fixes:** none to the cells.

### L3: "Levels 1-4", stage 3
- **Source:** V1 board appears 11.00 s, start frame 12.32, first tap 12.44, clear 17.44.
- **Board:** 10×9, 8 arrows of 6-21 cells drawn like the glyphs "2 5 / 2 5" (4 ←, 4 →):
  - the outline of the left "2/2" is one 21-cell arrow ending ← (id 0), the outline of the right "5/5" one 21-cell arrow ending → (id 4);
  - the inner strokes are two 12-cell arrows (ids 1 →, 6 ←) and four 6-cell ones.
  - 2 free at start (ids 0 and 4); 3 waves.
- **Timer:** first tick 13.12 (0.68 s); 2:56 at clear. 3 hearts, no tag. No tutorial.
- **IoU:** 0.980 → 0.986 / 0.992.
- **Replay:** 6 taps, all free exits, plus 2 arrows gone between taps (ids 3 and 6, both free then). 0 contradictions.
- **Solver:** 3 waves.
- **Fixes:** none.

### L4: "Levels 1-4", stage 4 (the session's last board)
- **Source:** V1 board appears 17.88 s, start frame 19.36, first tap 19.48, clear 24.12, win 24.20.
- **Board:** 9×14 maze, 8 arrows of 6-44 cells. The 44-cell green arrow (id 1) winds around the whole board and ends →. Only id 1 is
  free at start; 4 waves.
- **Timer:** first tick 20.16 (0.68 s); 2:56 at clear. 3 hearts, no tag. No tutorial.
- **After the clear:** the win celebration, then panel **"Level 1-4 / Perfect! / Rewards: 80 / Continue"** (27.4). Continue (28.34)
  goes straight into Level 5 (tutorials.md §4).
- **IoU:** 0.982 → 0.988 / 0.995.
- **Replay:** 5 taps: 4 mapped exits (all free) and 1 touch at 22.20 that mapped to no arrow (17 pt from arrow 4; see finding §3).
  Arrows 4, 5, 6 and then 0 were gone by the next frames, all free. 0 contradictions.
- **Solver:** 4 waves.
- **Fixes:** none.

### L5: Level 5
- **Source:** V1 level intro 28.32 s (HUD drop-in, board built by 28.64), start frame 30.12, first tap 30.24, clear 41.64, win 41.72.
- **Board:** 12×14 maze, 17 arrows of 3-17 cells (8 ↑, 4 →, 3 ←, 2 ↓). 6 free at start; 8 waves.
- **Timer:** first tick 31.20 (0.96 s); 2:50 at clear. 3 hearts, no tag. Reward 20. No tutorial.
- **IoU:** 0.976 → 0.979 / 0.992.
- **Replay:** 15 taps, all mapped exits on free arrows; 2 more gone between taps (ids 9 and 1, both free). 0 contradictions.
- **Solver:** 8 waves.
- **Fixes:** none. I traced all 17 arrows by hand against the frame.

### L6: Level 6 (the heart)
- **Source:** V1 level intro 44.96 s (the dot grid draws the heart first, then the arrows grow), start frame 46.60, first touch 46.88,
  clear 69.08, win 69.84.
  - After this win, Continue goes to **home for the first time**: +120 coins paid out (tutorials.md §4-5).
- **Board:** a heart silhouette, 27×22 at 13.559 pt (the smallest pitch in batch A).
  - 29 arrows of 2-53 cells. The two longest (ids 1 and 3, 53 and 52 cells) loop around the heart's middle band.
  - 11 free at start; 10 waves.
  - Two interior cells, (6,13) and (10,17), are empty, with no dot.
- **Timer:** first tick 47.20 (0.32 s); 2:38 at clear. 3 hearts, no tag. Reward 20. No tutorial.
- **IoU:** 0.987 → 0.990 / 0.999.
- **Replay:** 27 disc events.
  - 23 mapped exits, all free.
  - 4 touches at 12-17 pt from a stroke, beyond the 0.75-cell mapping radius at this small pitch. Each was followed by a free arrow
    leaving within 0.3-1.0 s (finding §3).
  - 6 arrows gone between taps, all free.
  - 0 contradictions.
- **Solver:** 10 waves.
- **Fixes:** none.

### L7: Level 7 (first Linked Arrows)
- **Source:**
  - V1 home "LEVEL 7" → Play at 76.42 s → the unlock popup over the dimmed board, 76.4-80.0 (tutorials.md §6).
  - Popup dismissed ≈80.0, board live 80.12, start frame 81.04 (overlay fully faded), first tap 81.16, clear 91.32, win 91.40.
- **Unlock popup** (`intro_popup` in L007.json): **"Linked Arrows!" / "Unlocked!" / card "LINKED ARROWS move together!"**. Tap anywhere
  to dismiss. There is no in-board hint afterwards.
- **Board:** 10×15, 18 arrows of 3-19 cells with **4 tie pairs**:
  - ids 9+11: ↑ at the top, tie on row 1;
  - ids 14+17: ↓ at the upper right, tie on row 3;
  - ids 4+5: ↑ at the lower left, tie on row 11;
  - ids 10+12: ↓ at the bottom, tie on row 13.
  - Each pair is two 3-cell straight arrows with the tie on the middle cell. 14 units; 3 free at start (both top/bottom pairs and
    arrow 1); 9 waves.
- **Timer:** first tick 81.36 (0.20 s); 2:50 at clear. 3 hearts, no tag. Reward 20.
- **Tie behaviour seen:**
  - 81.16: a tap on the top tie itself sends arrows 9+11 and the tie up and out together, in about 0.2 s.
  - 82.68: the bottom tie is tapped the same way.
  - 86.88: a touch just above the lower-left tie takes 4+5.
  - Pair 14+17 left between frames at the end (both free).
- **IoU:** 0.969 → 0.963 (vextract) / 0.992 (shading-aware).
  - Of the ten, this board has the most horizontal stroke length combined with down heads. The standard renderer's single stroke
    width over-draws the bottom edge of every horizontal stroke (orange fringe in `L007-look-diff.png`), and the re-fit that raises
    the raw IoU (0.839 → 0.884) lowers the 1-px-tolerant score slightly.
  - The shading-aware render (vertical strokes 8.25 px, horizontal 6.75 px, down heads 0.46 vs up heads 0.34 pitch) scores 0.992
    with the same cells.
- **Replay:** 13 taps: 12 mapped exits (all free, 3 of them bundles), plus the 84.92 touch 21.6 pt from arrow 3 (finding §3). 3
  arrows vanished between frames (arrow 3, then 14 and 17 together), all free. 0 contradictions.
  - The final sync frame was moved from t_clear + 0.4 to t_clear + 0.1 (`replayA.py`). At 91.72 the win logo's blue MAZE sign
    already covers one cell of arrow 14 and reads as ink ("left_at_end [14]" at +0.4; the frame at 91.40 shows the board empty).
- **Solver:** 9 waves, ties as units.
- **Fixes:** none to the cells or ties. `occlusion_inferred` (the tie-bridged edges) was moved into the level's cell frame (the index
  file had it in the fit frame, like the phone files).

### L8: Level 8
- **Source:** V1 home → Play 97.12 s, start frame 99.00, first tap 99.12, clear 109.52, win 110.08.
- **Board:** 12×17, 19 arrows of 2-34 cells (10 →, 7 ←) with **2 tie pairs**:
  - ids 14+15: 4-cell ← at the top right, tie on column 9;
  - ids 5+6: 4-cell → at the bottom left, tie on column 2.
  - In both pairs the tie sits on the cell behind the head. 17 units; 3 free at start; 7 waves.
- **Timer:** first tick 99.48 (0.36 s); 2:50 at clear. 3 hearts, no tag. Reward 20. No popup.
- **Ties:** both bundles were tapped on the tie (102.24 and 108.36) and left whole.
- **IoU:** 0.971 → 0.978 / 0.993.
- **Replay:** 15 taps: 14 mapped exits (all free); the 108.80 touch is 0.75 cell from arrow 9's nearest cell centre (17 pt from its stroke), and
  arrow 9 left by 109.32 (free); 3
  arrows vanished between frames, all free. 0 contradictions.
  - With the index fit this touch mapped at exactly the 0.75-cell limit. Moving the grid by 0.25 px pushed it just past.
- **Solver:** 7 waves.
- **Fixes:** none to the cells. `occlusion_inferred` normalised.

### L9: Level 9
- **Source:** V1 home → Play 118.28 s, start frame 120.12, first touch 120.24, clear 135.68, win 136.44.
- **Board:** 14×19 at 24.55 pt, 27 arrows of 2-34 cells (11 ↓, 8 →, 7 ←, 1 ↑), including a square spiral at the right. 7 free at
  start; 10 waves.
- **Timer:** first tick 120.56 (0.32 s); 2:44 at clear. 3 hearts, no tag. Reward 20. No tutorial.
- **IoU:** 0.975 → 0.978 / 0.994.
- **Replay:** 27 taps: 26 mapped exits (all free); the first touch (120.24) was 16 pt above arrow 0, which left by 120.56. 0
  contradictions.
- **Solver:** 10 waves.
- **Fixes:** none.

### L10: Level 10
- **Source:** V1 home → Play 142.16 s, start frame 143.44, first tap 143.56, clear 176.24, win 177.00. After it, home "LEVEL 11" →
  the Curtain unlock (batch B).
- **Board:** 20×22 at 17.857 pt, 47 arrows of 2-29 cells, with **3 tie quads**:
  - ids 2-5: four 5-cell → at the left, vertical tie on column 3;
  - ids 36-39: four 5-cell → at the right, tie on column 18;
  - ids 21, 23, 28, 29: four 6-cell ↓ in the middle, horizontal tie on row 12.
  - Each tie sits on the cell behind the heads. 38 units; 9 free at start; 14 waves (the deepest in batch A).
- **Timer:** first tick 143.68 (0.12 s); 2:27 at clear. 3 hearts, no tag. Reward 20. No popup.
- **Ties:** all three quads were tapped on the tie (143.56, 167.32, 173.4) and left as one.
- **IoU:** 0.982 → 0.988 / 0.997.
- **Replay:** 35 taps: 31 mapped exits (all free, 3 of them quads); 4 touches 13-17 pt off a stroke, each followed by that free arrow
  leaving; 7 arrows vanished between frames, all free. 0 contradictions.
- **Solver:** 14 waves.
- **Fixes:** none to the cells. `occlusion_inferred` normalised.

## Open questions (not answerable from V1)
- Hit radius: at least ~22 pt from a stroke (§3), but the true radius and the tie-breaking rule between two nearby arrows are unknown.
  Needs deliberate off-stroke taps on the phone.
- Linked bundle with one member blocked: bump or not? Never tapped in V1 (and not tested on the phone either).
- Whether input is locked while the L1 hint shows (the only candidate "touch" was the hand's own ripple).
- The height limit of the layout rule: no board in 50 is height-limited. The deepest seen is 36 rows at 15.1 pt, a cell box of
  about 545 pt.
