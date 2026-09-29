> **ORCHESTRATOR RULING 08:35 (binding; also SPEC.md §5.19-20):** ship video L1-L31 in video order with video timers/tags; phone L32-L61 in phone order with v552 timers/tags; the 4 duplicate PHONE slots (L35, L45, L51, L52) are substituted in order by V2-L032..V2-L035; V2-L036..038 open the designed range at L62-L64; unlock cards only at first appearance in our order (Linked L7, Box L11, Pipe L21, Elevator L31, Door+Key L33 with our card text); incomplete phone door/counter/pipe data must be completed from the shots or the level substituted and logged.

# Video levels 1-38: consolidated table and verifier's verdicts

Verifier (adversarial), 2026-09-25. The owner calls the game **Arrow Out**; the videos show the original "Maze Out!". Frames were
measured and looked at, never shipped or traced. This file consolidates the four batch reports, which stay as the detailed sources:
`video-levels-A.md` (L1-10), `-B.md` (L11-20), `-C.md` (L21-30), `-D.md` (L31-38). My scripts, results and notes are in
`research/levels/video/verify/`; my images are in `research/video-frames/work/verify/` (gitignored). Nothing is committed.

## 1. Verdicts

### 1.1 The extracted boards are right: 38 of 38
Each check below is my own work and does not reuse the batch agents' tools, except the replay re-run, which uses vextract as
instructed.

- **A third, independent reader** (`verify/myread2.py`, written from scratch) read every start frame of both videos. That is 48
  frames: V1 L1-20 and V2 L11-38. It agrees with the batch files **arrow for arrow: 1,527 of 1,527 arrows**.
  - **Obstacles: 84 of 84.** Box rectangles, pipe cells including both mouths and their out directions, and Linked ties all match.
    This confirms batch C's and batch D's pipe-mouth fixes.
  - **Hidden layers: 74 of 74.** Every hidden-layer arrow of the 5 elevators appears on its reveal frame, and no extra arrow appears.
  - **Elevator platforms.** My colour mask finds exactly the batch's rectangles on L31 and L32. On L33 (Jaccard 0.92) and L35 (0.55)
    it finds only part of each platform, because arrows cover most of it. I drew the batch's rectangles on those frames and looked
    at them: they match the lavender platforms (`video-frames/work/verify/elev-both.png`).
- **Blind re-extraction of random levels.** I picked the levels before opening their files (seed 1790312444, one per range):
  L1, L11 and L29, plus a bonus L3 because L1 has only 3 arrows. All four are identical to the batch files:
  - L1: 3/3 arrows. L3: 8/8.
  - L11: 14/14 arrows plus both boxes, with counters 8 and 13, from **both** videos.
  - L29: 68/68, including batch C's hand-added arrow 67 and all three pipes with their corrected mouths.
- **Replay re-run** (`vextract.py replay` on the final files), 48 level-video pairs: **0 inconsistent events**. The only oddities are
  the artefacts the batches already explained, and I checked the L7 one on frames:
  - L1: the tutorial hand covers arrow 1;
  - L7: at +0.4 s the win logo covers arrow 14, but the board is already empty at 91.16 s;
  - L33: arrow 7's real exit is misjudged.
- **Validator and solver** (`verify/validate.py`, my own rule model) on L001-L031 plus the video L32-38:
  - schema and invariants: **0 errors on 38 files**. That covers every phone-schema key, ids, adjacency, no shared cells, dir equal
    to the last step, tight bounds, full box rectangles with counters, pipe ends at the degree-1 cells pointing out, and ties on the
    cell behind the head of straight, parallel, equal arrows;
  - **all 38 solvable**;
  - **0 dead ends in 100 random move orders per level**;
  - dependency depth (rounds) equals the batch reports on 37 levels. L32 reads 17 against batch D's 16, because the hidden layer
    joins mid-round.
- **Negative controls.** These cases prove the checks can fail:
  - a box counter +1 on L13 → unsolvable;
  - reversing L29's arrow 67 → unsolvable;
  - a wrong `taped_arrow_ids` → flagged.
  - A *deleted* arrow still solves. That is why the ink comparison (the third reader) is needed next to the solver.
- **Counterfactuals** equal the batches wherever a batch reported one (the L25 and L27 slack values are new). Every box is needed: with a box that never breaks, the level is unsolvable.
  - Tight counters, where +1 makes the level unsolvable: L11 13, L12 23, L13 4 and 28, L19 13/20/25, L25 24, L27 32 and 18, L28 10
    and 38, L33 41/28/18, L37 52/35.
  - Slack, where the counter can rise and the level stays solvable: L11 8→10, L12 8→9 and 16→17, L15 26→31 and 41→43, L25 57→59 and
    36→46, L27 25→26, L33 13→14.
  - Every pipe except L22's first one (counter 1) is needed.
- **Overlays looked at: 31 of 31.** I drew each final L001-L031 on its own start frame, with the model's centre lines, heads,
  tails, obstacles and counters, and looked at every sheet. For L31 I also drew the hidden layer on its reveal frame. Every red
  centre line sits inside its blue stroke; every head, tail, tie, box counter and pipe mouth matches.
  - Sheets: `video-frames/work/verify/final/sheet-00..14.png`.

### 1.2 V1 vs V2 on L11-20: identical, cell for cell
- `verify/lvldiff.py` on `levels/video/V1-L0NN.json` vs `V2-L0NN.json` finds identical content, all at shift (0,0) and with the
  same grid sizes:
  - **316/316 arrows** (same cells, same direction);
  - **12/12 boxes**, with the same cells and the same counters;
  - **5/5 Linked ties**.
- The V2 files equal the final `levels/L011-L020.json`.
- The third reader, reading the V1 frames and the V2 frames separately, gets the same boards again (see the table's "3rd reader"
  column).
- The only difference is the skin: V1 draws the boxes as purple "Curtain" slabs and V2 as cyan "Box" bomb blocks. There is no A/B
  content difference and no extraction disagreement, so nothing needed re-extracting.

### 1.3 The videos are not v552. Video L1-31 is the older build's L1-31, not the phone's
**V2 vs the phone, L32-38: 0 of 7 identical.**
- My exhaustive search (`verify/xmatch.py`) compares every video board with every phone board L032-L061, open variants included,
  under all 8 rotations and reflections and any shift.
- No video L32-38 board appears anywhere in v552's L32-61. The best overlap is 2-5 identical arrows out of 29-96. Real matches
  score every arrow.
- The obstacles differ too:
  - v552's L32-38 has doors and keys (L33, L34, L37);
  - the video's has elevators (L32, L33, L35);
  - v552 has no elevator anywhere in L32-61.

**The two builds share 4 boards, at other numbers.** Over all 38 video boards against all 30 phone boards, exactly four are the
same. Each matches in every arrow and every obstacle cell, at shift (0,0), with the board centre within 2 pt:

| video | = phone v552 | arrows | obstacles | timer video → phone |
|---|---|---|---|---|
| L12 | **L51** | 24/24 | 3 boxes, counters 8/16/23 both | 3:00 → 3:00 |
| L14 | **L52** | 15/15 | – | 3:00 → 3:00 |
| L21 | **L35** | 20/20 | pipe, same 15 cells and mouths, counter 2 both | 3:00 → 3:00 |
| L26 | **L45** | 26/26 | – | 3:00 → **2:30** |

Every other video board shares at most 5 arrows with any phone board. The one exception is L1, whose three parallel 4-cell arrows
also occur inside phone L32's 53 arrows; that is not a match.

**The unlock order shows v552 reordered the levels.** v552's own unlock cards on the phone:

| obstacle | video build: first level (card) | v552 phone: first level (card) |
|---|---|---|
| Linked Arrows (tie) | L7 "Linked Arrows!" | before L32 (no card at L32; the phone never saw L1-31) |
| Box ("Curtain" in V1) | L11 "Box!" (V1 "Curtain!") | **L50** "Box!" (same text) |
| Pipe | L21 "Pipe!" | **L35** "Pipe!" (same text); L35 *is* video L21 |
| Elevator | L31 "Elevator!" | none in L32-61 |
| Door + key | never | L33, with no card, so it was introduced before L32 (inferred) |
| Hard / Super Hard | Hard L19, L25, L35; Super Hard L29 | Hard L34, L44, L54; Super Hard L39, L49, L59 |

**Plain verdict, with numbers.**
- v552 shows its Pipe card at L35 and its Box card at L50, so **v552 has no pipe level before L35 and no box level before L50**.
- Every one of the **12 video levels in L11-L31 that has a box or a pipe** (L11, 12, 13, 15, 19, 21, 22, 23, 25, 27, 28, 29) is
  therefore **not** v552's level at that number.
- Two more, **L14 and L26**, sit in v552 at L52 and L45, unless v552 plays the same board twice.
- **L31**'s elevator never appears in 30 recorded v552 levels.
- So **at least 12, and most likely 15, of the 21 video levels L11-31 are not v552's content at those numbers.**
- The other 16 (L1-L10, L16, L17, L18, L20, L24, L30) cannot be checked, because the phone is past L31 and its progress survives a
  reinstall. Nothing in the data shows they are v552's.
- v552 also retunes difficulty:
  - timers vary from 2:00 to 3:30 (19 of 30 recorded levels at 3:00, 9 at 2:30, L34 at 3:30, L59 at 2:00). Every one of the 38 video
    levels is 3:00, and the shared board L26/L45 went from 3:00 to 2:30;
  - v552 places Hard and Super Hard every 5 levels (x4, x9), while the video build has them at 19, 25, 29 and 35.

**How far to trust L1-31.**
- As **extractions of the video build**: fully. Every check above passed on every board.
- As **v552's L1-31**: low. They are the older build's level list, and they are provably wrong for v552 at every obstacle level from
  L11 on.
- What the two builds do share holds up. The unlock card texts for Box and Pipe are word for word the same on the phone. The rules
  measured in the videos (tie, box counter, pipe pass, bump) match the phone's. The owner stated that the FTUE and tutorial flow is
  the same (OWNER 02:50).

**Decision needed from the orchestrator** (my recommendation follows). The owner said both "levels 1-38 from the videos"
(OWNER 02:33) and "where the videos and the phone differ, the PHONE wins" (02:55).
- **L32-38: the phone wins.** Its L32-38 differ from the video's and are recorded exactly. The video L32-38 files stay in
  `levels/video/` as unused extras.
- **L1-31 from the videos** is the only source there is, but mixing it with phone L32+ creates three conflicts:
  1. **Duplicate boards:** video L12, L14, L21 and L26 are phone L51, L52, L35 and L45.
  2. **Doubled unlock cards:** Box would unlock at L11 and again at L50, and Pipe at L21 and again at L35. The phone's L35 is the
     video's own Pipe-intro board.
  3. **A dead-end obstacle:** the elevator would unlock at L31 and never appear again, while doors and keys would arrive at L33 with
     no card.
- A consistent option: keep the video L1-31 boards, show each unlock card only on an obstacle's first appearance, add a Door/Key card
  at L33 (its text is unknown and must be designed), and replace the four duplicated boards on one side with generated levels.
  Whoever freezes `levels.json` decides this.

## 2. The 38 levels

- **file:**
  - L1-31: `research/levels/L0NN.json`, source "video";
  - L32-38 video: `research/levels/video/V2-L0NN.json`;
  - `research/levels/L032-L038.json` are the **phone's** recordings, a different level list.
- **t:** the start-frame time in seconds.
- **rounds:** dependency depth (every free unit removed per round).
- **left:** timer at clear, for this video's player.
- **3rd reader:** my independent read vs the file, both videos for L11-20.
- **replay:** inconsistent events in my re-run, V2 then V1.

| L | video, t | grid | arrows (+hidden) | obstacles (counters) | tag | timer | reward | left | rounds | first-time popup | v552 | 3rd reader | replay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | V1 0.72 | 3x4 | 3 | - | - | 3:00 | (80 for L1-4) | 2:59 | 1 | "Tap to move!" + hand | ? | 3/3 | 0 |
| 2 | V1 7.92 | 6x6 | 6 | - | - | 3:00 | (session) | 2:58 | 4 | - | ? | 6/6 | 0 |
| 3 | V1 12.32 | 10x9 | 8 | - | - | 3:00 | (session) | 2:56 | 3 | - | ? | 8/8 | 0 |
| 4 | V1 19.36 | 9x14 | 8 | - | - | 3:00 | 80 (L1-4) | 2:56 | 4 | - | ? | 8/8 | 0 |
| 5 | V1 30.12 | 12x14 | 17 | - | - | 3:00 | 20 | 2:50 | 8 | - | ? | 17/17 | 0 |
| 6 | V1 46.60 | 27x22 | 29 | - (heart shape) | - | 3:00 | 20 | 2:38 | 10 | first home after it | ? | 29/29 | 0 |
| 7 | V1 81.04 | 10x15 | 18 | 4 ties x2 | - | 3:00 | 20 | 2:50 | 9 | **Linked Arrows!** | ? | 18/18 | 0 |
| 8 | V1 99.00 | 12x17 | 19 | 2 ties x2 | - | 3:00 | 20 | 2:50 | 7 | - | ? | 19/19 | 0 |
| 9 | V1 120.12 | 14x19 | 27 | - | - | 3:00 | 20 | 2:44 | 10 | - | ? | 27/27 | 0 |
| 10 | V1 143.44 | 20x22 | 47 | 3 ties x4 | - | 3:00 | 20 | 2:27 | 14 | - | ? | 47/47 | 0 |
| 11 | V2 92.01 | 10x20 | 14 | box 8/13 | - | 3:00 | 20 | 2:50 | 5 | **Box!** (V1 Curtain!) | not v552 L11 | 14/14 (V1 14/14) | 0/0 |
| 12 | V2 112.14 | 15x21 | 24 | box 8/16/23 | - | 3:00 | 20 | 2:39 | 10 | - | **= phone L51** | 24/24 (24/24) | 0/0 |
| 13 | V2 147.80 | 14x18 | 33 | box 4/28, 2 ties x3 | - | 3:00 | 20 | 2:24 | 12 | - | not v552 L13 | 33/33 (33/33) | 0/0 |
| 14 | V2 194.95 | 13x16 | 15 | - | - | 3:00 | 20 | 2:44 | 5 | - | **= phone L52** | 15/15 (15/15) | 0/0 |
| 15 | V2 221.37 | 20x25 | 48 | box 26/41 | - | 3:00 | 20 | 2:08 | 11 | - | not v552 L15 | 48/48 (48/48) | 0/0 |
| 16 | V2 284.65 | 13x15 | 24 | - | - | 3:00 | 20 | 2:44 | 10 | - | ? | 24/24 (24/24) | 0/0 |
| 17 | V2 317.81 | 19x24 | 54 | 3 ties x3 | - | 3:00 | 20 | 1:57 | 14 | - | ? | 54/54 (54/54) | 0/0 |
| 18 | V2 389.94 | 14x17 | 22 | - | - | 3:00 | 20 | 2:41 | 10 | - | ? | 22/22 (22/22) | 0/0 |
| 19 | V2 420.91 | 20x31 | 62 | box 13/20/25 | Hard Level | 3:00 | 60 | 1:52 | 25 | first Hard (no popup) | not v552 L19 | 62/62 (62/62) | 0/0 |
| 20 | V2 500.20 | 14x20 | 20 | - | - | 3:00 | 20 | 2:42 | 9 | - | ? | 20/20 (20/20) | 0/0 |
| 21 | V2 530.64 | 12x18 | 20 | pipe 2 | - | 3:00 | 20 | 2:44 | 10 | **Pipe!** | **= phone L35** | 20/20 | 0 |
| 22 | V2 555.88 | 14x23 | 29 | pipe 1/1 | - | 3:00 | 20 | 2:28 | 10 | - | not v552 L22 | 29/29 | 0 |
| 23 | V2 599.47 | 16x22 | 41 | 2 ties x3, pipe 3/3 | - | 3:00 | 20 | 2:17 | 18 | - | not v552 L23 | 41/41 | 0 |
| 24 | V2 654.01 | 17x27 | 37 | 4 ties x3 | - | 3:00 | 20 | 2:11 | 10 | - | ? | 37/37 | 0 |
| 25 | V2 712.75 | 19x30 | 61 | box 24/57/36, pipe 3/3 | Hard Level | 3:00 | 60 | 1:40 | 24 | - | not v552 L25 | 61/61 | 0 |
| 26 | V2 801.21 | 15x19 | 26 | - | - | 3:00 | 20 | 2:30 | 12 | - | **= phone L45 (2:30)** | 26/26 | 0 |
| 27 | V2 840.00 | 16x26 | 40 | box 32/25/18 | - | 3:00 | 20 | 2:06 | 16 | - | not v552 L27 | 40/40 | 0 |
| 28 | V2 902.61 | 19x24 | 51 | box 10/38, 4 ties x3 | - | 3:00 | 20 | 1:51 | 14 | - | not v552 L28 | 51/51 | 0 |
| 29 | V2 982.47 | 20x32 | 68 | pipe 3/3/3 | Super Hard | 3:00 | 100 | 0:20 | 29 | first Super Hard (no popup) | not v552 L29 | 68/68 | 0 |
| 30 | V2 1152.94 | 16x16 | 25 | - | - | 3:00 | 20 | 2:40 | 7 | - | ? | 25/25 | 0 |
| 31 | V2 1184.04 | 16x17 | 28 (+7) | elevator 84 cells, 7 hidden | - | 3:00 | 20 | 2:36 | 12 | **Elevator!** | likely not | 28/28, hidden 7/7 | 0 |
| 32 | V2 1216.38 | 17x21 | 29 (+11) | elevator 104 cells, 11 hidden | - | 3:00 | 20 | 2:26 | 17 | - | **≠ phone L32** | 29/29, 11/11 | 0 |
| 33 | V2 1259.17 | 17x23 | 36 (+17) | box 41/28/18/13, 2 elevators 78+78 cells, 8+9 hidden | - | 3:00 | 20 | 2:02 | 22 | - | **≠ phone L33** | 36/36, 17/17 | 0 |
| 34 | V2 1330.78 | 18x23 | 40 | 4 ties x3 | - | 3:00 | 20 | 2:27 | 13 | - (rating prompt on the home after its win) | **≠ phone L34** | 40/40 | 0 |
| 35 | V2 1379.07 | 20x32 | 57 (+39) | pipe 3, elevator 320 cells, 39 hidden | Hard Level | 3:00 | 60 | 1:03 | 44 | - | **≠ phone L35** | 57/57, 39/39 | 0 |
| 36 | V2 1506.21 | 20x23 | 36 | - | - | 3:00 | 20 | 2:28 | 14 | - | **≠ phone L36** | 36/36 | 0 |
| 37 | V2 1549.25 | 20x33 | 55 | box 52/35 | - | 3:00 | 20 | 1:49 | 23 | - | **≠ phone L37** | 55/55 | 0 |
| 38 | V2 1631.10 | 16x20 | 34 | pipe 3/3 | - | 3:00 | 20 | 2:20 | 12 | - | **≠ phone L38** | 34/34 | 0 |

Notes on the table:
- **Hearts:** 3 on every level. The only heart losses are V2 L32's two, both on taps of blocked arrows.
- **Clock:** it starts at the first tap, and is frozen under hints and unlock cards.
- **Sessions:** L1-L4 are one session, "Levels 1-4": four boards, one win panel, 80 coins.
- **Totals:**
  - L1-31: 924 start-layer arrows plus 7 hidden;
  - video L32-38: 287 plus 67 hidden.
- **"?"** means the level cannot be checked against v552: no v552 recording exists below L32.
- **"not v552 LNN"** is proven by v552's unlock cards (§1.3), or by the board sitting at another v552 number.

## 3. Completeness and gaps
**Every level from 1 to 38 has a file and a source.**
- L1-10 come from V1.
- L11-20 come from V2 with V1 as `video_alt`; the per-video files are `levels/video/V1-*` and `V2-*`.
- L21-31 come from V2.
- L32-38 exist twice:
  - the video build's, in `levels/video/V2-L0NN.json`, with no promotion to `levels/`;
  - v552's, in `levels/L032-L038.json`, source "recorded".

Gaps, most important first:
1. **The level list itself (§1.3).** v552's L1-31 is unknown. The video L1-31 is a different build's list, so the numbering, the
   duplicates and the unlock placement need an orchestrator decision before `levels.json` is frozen.
2. **Phone L32-38, if they ship:**
   - The door levels **L33, L34 and L37 lack the arrows hidden under their doors.** There are no `-open` files below L47, so the
     start-state JSONs are incomplete. This is the PLAN TODO.
   - **No phone file carries its pipe or box counters.** Every phone `counter` is null; the numbers are only in levels.md's text
     (L35 2, L36 1/1, L38 4, and L41-57 further on).
   - L048, L049 and L056 have pipe obstacles but an **empty `pipes` list**, so they have no ends.
3. **Fields differ from batch to batch in L001-L031.** Whoever builds `levels.json` should normalise them:
   - `label`, `session` and `reward_coins` exist only on L1-10 (batch A);
   - the rewards of L11-31 sit inside `checks`, `batchC` or `batchD` blocks (the table above has them all);
   - the unlock card is a top-level `intro_popup` only on L7. L11 (Box!) has no popup record at all, and L21 and L31 carry it only
     inside the `batchC` or `batchD` notes;
   - suggestion: one `unlock` key on L7, L11, L21 and L31, with the card texts from §4.
4. **Behaviour the videos never show** (the batch OPEN items, still open):
   - a tap on a Linked bundle with one member blocked;
   - the true tap radius (it is at least about 22 pt from a stroke);
   - the earliest moment an arrow behind a just-broken box may leave;
   - whether the elevator layer goes live at the last platform arrow's tap or at the door start;
   - whether input is locked under the L1 hint;
   - the layout rule's height cap.
5. **Art unknown for v552:** the elevator exists only in the video build, so its v552 look is unknown. The box art on v552 is V1's
   purple slab, as batch B found.

## 4. Obstacles, captions and unlocks in the video build
| level | what the player sees | exact text | notes |
|---|---|---|---|
| L1 (board 1 of "Levels 1-4") | caption and pointing hand on the middle arrow; no dim | **"Tap to move!"** | first launch goes straight from Loading into play; the hand's press draws its own ripple (batch A §4); tutorials.md §3 |
| after L4 | win panel | "Level 1-4 / Perfect! / Rewards: 80" | Continue leads straight into L5 |
| after L6 | first home screen | – | +120 coins paid out |
| L7 | unlock card over the dimmed board | **"Linked Arrows! / Unlocked! / LINKED ARROWS move together!"** | tie = pink X over the cell behind the heads of 2-4 straight, parallel, equal arrows; one tap, including on the tie, moves the bundle |
| L11 | unlock card | V2 **"Box! / Unlocked! / Clear required amount of arrows to break the BOX!"** (V1 "Curtain! … to open the CURTAIN!") | every removed arrow lowers every box by 1, bundle members each; breaks on the removal that reaches 0, never shows "0"; nothing underneath. v552: the same card at L50 |
| L19 | first Hard: red "Hard Level" tab, red buttons, no card | – | reward 60 |
| L21 | unlock card | **"Pipe! / Unlocked! / Pass arrows through the PIPE to break it!"** | an arrow entering a mouth against the mouth's out direction exits the other mouth; the counter steps when the arrow leaves the far mouth (0.42-0.6 s); shatters on the last pass. v552: the same card at L35 on the same board |
| L29 | first Super Hard: purple tab, no card | – | reward 100 |
| L31 | unlock card | **"Elevator! / Unlocked! / Clear all arrows on the ELEVATOR to activate it!"** | a hidden second layer under the platform comes up when the last platform arrow has left; empty platform cells do not block rays; not seen in v552 L32-61 |
| after L34 | iOS rating sheet on the home | system text | same moment on the phone (tutorials.md) |

- No level has an idle hint. There was none during a 19.6 s idle on L28 or a 28.9 s idle on L29.
- No tutorial hand appears after L1.
- The booster bar in the videos has 4 boosters from the first board. v552 has 2. The videos' extra two are documented only.

## 5. Difficulty curve in the video build
| range | arrows, min-max (mean) | occupied cells, mean | grid area, mean (max) | depth in rounds, min-max (mean) | time used by the video's player, s |
|---|---|---|---|---|---|
| L1-4 (tutorial session) | 3-8 (6.2) | 66 | 66 (126) | 1-4 (3.0) | 1-4 |
| L5-10 | 17-47 (26.2) | 258 | 304 (594) | 7-14 (9.7) | 10-33 (mean 17) |
| L11-20 | 14-62 (31.6) | 294 | 326 (620) | 5-25 (11.1) | 10-68 (mean 32) |
| L21-31 | 20-68 (39.4) | 346 | 386 (640) | 7-29 (14.7) | 16-160 (mean 52) |
| L32-38 (video) | 34-96 incl. hidden (50.6) | 434 | 463 (660) | 12-44 (20.7) | 32-117 (mean 55) |

- **The curve is a saw-tooth, not a ramp.** Spikes sit at the tagged levels:
  - L19 Hard: 62 arrows, depth 25;
  - L25 Hard: 61, depth 24;
  - L29 Super Hard: 68, depth 29, only 0:20 left;
  - L35 Hard: 96 with hidden arrows, depth 44.
- Each spike is followed by an easy board: L20 20 arrows, depth 9; L26 26, depth 12; L30 25, depth 7; L36 36, depth 14.
- New obstacles arrive on easy boards: L7 18 arrows, L11 14, L21 20, L31 28.
- **Timer:** 3:00 on all 38 video levels, Hard and Super Hard included. v552 retimes (§1.3), so timers are per-level data.
- **Board size:**
  - pitch = 393 pt / max(14, cols + 2), confirmed by the batches on 50 boards;
  - widths run from 3 to 27 columns, heights up to 33 rows;
  - L6 (the heart) is the widest board at 27 columns, 13.6 pt pitch.
- **Rewards:** 20 per level; Hard 60; Super Hard 100; the "Levels 1-4" session 80.

## 6. Verifier's files (`research/levels/video/verify/`)
- **Readers and comparison:**
  - `myread.py`: the independent reader used for the blind picks;
  - `myread2.py`: the same reader plus ties, both box skins, pipes with their badge gap, and elevator platforms;
  - `runall.py`: runs the reader on all 48 start frames and 5 reveal frames → `thirdreader.json`, per-frame reads in `third/`;
  - `lvldiff.py`: cell-by-cell diff with best shift and optional 8 symmetries; obstacles, counters and elevators;
  - `xmatch.py`: every video board against every phone board → `xmatch.json`.
- **Validation:**
  - `validate.py`: schema, invariants, rule-model solver, random orders, counterfactuals → `validate.json`;
  - `replay-rerun.json`: my vextract replay re-run, 48 runs.
- **Consolidation:** `consolidate.py` → `consolidated.json`, the data behind §2.
- **Blind picks and cross-checks:**
  - `indep/`: the blind picks (`V?-L0NN.json`) and their diffs against the batch files;
  - `v1v2/`: the V1-vs-V2 diffs;
  - `phone-L0NN-vs-L0MM.json`: the four shared boards.
- **Images** (gitignored): `research/video-frames/work/verify/`
  - `final/sheet-*.png`: the looked-at overlays;
  - `third/`: the third reader's overlays;
  - `indep-*.png`, `zoom-*.png`, `l7end/sheet.png`.
