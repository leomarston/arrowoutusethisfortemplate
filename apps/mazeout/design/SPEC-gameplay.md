# Arrow Out: gameplay, content, economy and copy (SPEC-gameplay)

Gameplay spec writer, 2026-09-25 (+03). The rules half of the V1 spec for **Arrow Out**, our 1:1 copy of "Maze Out! - Tap
Puzzle" (Grand Games, v552). SPEC.md §4 makes this file and `design/levels.json` the winners for **rules, levels, economy,
boosters, event rules, tutorial content and strings**. SPEC-architecture wins for code structure; SPEC-ui for geometry and
looks; SPEC-motion-audio for curves, timings of animations and sounds; SPEC-social for the simulated world.

The owner's sentence (verbatim, PLAN.md): *"Read GAMEPROMPT.md and make Maze Out on my phone. ultracode ultrathink"*.

Companion files, all written with this spec:
- `design/levels.json`: the content, L1–L150 in the bundle schema, plus sessions, unlock cards, tutorials and the generator
  curve (§14).
- `design/LEVELS.md`: the level list, the provenance of every level, the curve fit, the door reconstruction, the validator.
- `design/tools/`: `arrowcore.py` (these rules as code), `reveal_backfill.py`, `import_research.py`, `gen_levels.py`,
  `build_levels.py`, `validate_levels.py`, `validator_selftest.py`, `render_levels.py`, `levels_report.py`, `pathrandom.py`.

---

## 0 Read this first

### 0.1 Tags, sources, precedence
- **VERIFIED** (source): seen on the owner's phone (v552), in the owner's videos V1/V2, or in the measured research files.
- **INFERRED**: reasoned from indirect evidence; the reasoning is given.
- **DECISION**: ours (never observed, or an engineering choice). A DECISION can be flipped by changing the named key.
- **ORCH n**: an orchestrator ruling, SPEC.md §5 item n (binding).
- Evidence precedence (SPEC.md §4): phone v552 > owner videos (content, FTUE, tutorials) > store/help > web videos > reviews.

Source shorthands: `levels` `flows` `fail` `boosters` `economy` `meta` `obstacles` `tutorials` `motion` `sounds` `web` =
`research/<name>.md`; `vflows` = `research/video-flows.md`; `vlev` = `research/video-levels.md` (the verifier) and `-A`..`-D` its
batch reports; `social` = `design/SPEC-social.md`; `arch` = `design/SPEC-architecture.md`; `uim` = `design/ui-measure.md`.

### 0.2 Where every value lands
Every number below names the key that carries it. Files (SPEC-architecture §3.2 owners):
- `rules.json` = `App/Resources/Tuning/rules.json`, decoded into PathCore `RulesTuning` (C2) — board rules, hearts, clock, fail
  chain, rewards, boosters. The **economy** keys (lives, continue/refill prices, shop, booster purchase, Claw ladder, streak
  ladder) are new sections of the same file (`economy.*`, `lives.*`, `shop.*`, `claw.*`, `streak.*`): C3's `EconomyRules`
  decodes them (arch §4.4: RulesTuning holds the §4.5–§4.9 knobs). The current file already carries `lives.refillSeconds`.
- `game.json` (G1): FTUE chain, rating, notifications, hint policy.
- `social.json` (SOC1): event unlock levels (identical to `social` D11, repeated in §11.3 for G2).
- `levels.json` → `Levels/*.json` (CONTENT via `pclevels bundle`): levels, sessions, unlock cards, tutorials, curve.
- `board.json` (B1): hit radius and tie break (the input the board owns).
§15 lists every key with its value in one table.

### 0.3 What this spec settles (SPEC-architecture §14, PENDING-gameplay)

| PENDING item | value | key | § |
|---|---|---|---|
| tape some-clear policy | the whole bundle bumps, one heart, every member marked red | `rules.json:tape.blockedPolicy = "bundleBumps"` | 3.4 |
| tapping a bumping arrow | ignored until its bump has returned (≤ 0.35 s) | `IgnoreReason.bumping` (C2) | 2.4 |
| pipe consumption on a blocked exit | none: a bump consumes no passage | `rules.json:pipe.bumpConsumes = false` | 3.6 |
| elevator empty-cell blocking | empty platform cells never block | `rules.json:elevator.emptyCellsBlock = false` | 3.8 |
| hearts per stage in multi-board sessions | carried across the 4 boards of "Levels 1-4" | `sessions.json hearts = "carry"` | 4 |
| the fail chain's later steps and grants | every step 900 coins; "Play On" grants what the first step grants (+30 s / 3 hearts); no escalation | `rules.json:failChain` | 7 |
| life refill seconds | **1800** (one life per 30:00, one continuous clock) — VERIFIED | `rules.json:lives.refillSeconds = 1800` | 8 |
| kill mid-level | a loss at the next launch (streak reset, the life stays spent) | `rules.json:lives.killIsLoss = true` | 8.5 |
| booster effects | hourglass: clock frozen 1.5 s flight + 10 s; bulb: one free arrow, zoom + green blink | `rules.json:boosters.*`, `game.json:hint.*` | 6 |
| booster prices, buy flow | a "×3 for 900 coins" popup at 0 stock (DECISION); none sold alone in the shop (VERIFIED) | `rules.json:economy.boosterPack` | 6.4 |
| shop catalogue | the v552 list (6 bundles + 6 coin packs), US $ and TL | `rules.json:shop.products` | 9.4 |
| Claw ladder and duration | 20 steps, weekly, thresholds 1/200/300/400/300/500/500 (VERIFIED) then 600…1500 (DECISION) | `rules.json:claw.ladder` | 11.2 |
| the event schedule (unlock levels) | Streak Race L30, Claw L33, Sky Jump L40, Weekly L50, Rocket Race L55 (= `social` D11) | `social.json:unlocks` | 11.3 |
| the authored level count | **150** (L1–L150 in levels.json); endless generation beyond | `curve.authoredEnd` | 14 |
| unlock levels in our build | Linked L7, Box L11, Pipe L21, Elevator L31, Door L33 (ORCH 19) | `unlocks.json` | 10.4 |
| hit radius and tie break | nearest stroke within **22 pt**; within 1 pt: the right-hand, then the lower one | `board.json:input.hitRadiusPt = 22`, `rules.json:hit.radiusPt = 22` | 2.2 |
| timer alerts near 0 | **none** — no colour, pulse or scale (VERIFIED) | `rules.json:clock.alerts = []` | 5 |
| local notifications | two, both offline: "lives full" and "Weekly Contest ends in 2 hours" (ORCH 5) | `game.json:notifications.*` | 12.5 |

---

## 1 The game in one page
A white board holds black snake arrows on a hidden square grid. Tapping an arrow (fired on **release**) sends it out along its
own body and off the screen if the straight line from its head to the grid edge is clear; otherwise it slides to the first
thing in its way and back (**bump**), turns red for the rest of the level and costs a heart. A level is won when its last arrow
is tapped. Every level has **3 hearts** and a **timer** (3:00, 2:30, 2:00 or 3:30 per level) that starts at the **first tap**.
0 hearts or 0:00 opens a chain of 900-coin continue offers, then "Level Failed!". Obstacles: taped bundles leave together
(Linked Arrows), doors open with keys carried by arrows, pipes carry arrows through and break after N passes, boxes break after
N arrows are cleared, elevators hold a second layer of arrows. Two boosters (hourglass freezes the timer, bulb shows a free
arrow). A life is spent when a level starts and refunded on a win; 5 lives, one back every 30:00. Wins pay 20 coins (Hard 60,
Super Hard 100). Levels 1–4 are one session of four boards; the first home appears after Level 6. From L30 on, simulated
events (Streak Race, Claw Challenge, Sky Jump, Weekly Contest, Rocket Race) ride on the win streak multiplier x1–x100.

---

## 2 Input

### 2.1 Gestures (VERIFIED `levels` "Input model", `boosters` §4)

| gesture | effect |
|---|---|
| tap on or near an arrow | fires on **release** (touch-up), even after a 5 s hold; the press itself does nothing |
| tap on an empty point | the grey tap ripple only; the timer does NOT start (`rules.json:clock.emptyTapStartsTimer = false`, DECISION) |
| one-finger drag | pans the board; never fires an arrow (a 52 pt swipe that starts on a free arrow only panned) |
| pinch | zooms; the pitch stays within 14.04…28.07 pt (absolute, arch D6); never starts the timer |
| double tap | nothing (no zoom reset) |
| any gesture during popups, the intro, a stage transition, the win sequence or the 0:00 hold | ignored (`IgnoreReason.inputLocked`) |

A touch that moves more than the slop before lift-off is a pan, not a tap (slop: SPEC-motion-audio / `board.json:input.slopPt`).

### 2.2 Which arrow a tap hits (`board.json:input.*`, `rules.json:hit.*`)
- The tapped arrow is the one whose **centre line** (body polyline from tail centre to the head apex) is **nearest** to the
  touch point, if that distance is **≤ 22 pt** in screen space at the current zoom. DECISION from: phone taps 10 pt and 15 pt
  off a stroke fired it (VERIFIED L47); video touches 12–22 pt from a stroke took the nearest arrow (VERIFIED `vlev-A` §3, a lower
  bound). 22 pt is the largest observed and keeps every observed tap working.
- **Tie**: when two centre lines are within 1 pt of the same distance, the arrow to the **right** wins, then the **lower** one
  (VERIFIED once: the exact midpoint between two parallel strokes sent the right-hand one, L52). `hit.tieBreak = "rightThenDown"`.
- **Tape tie**: a touch on a Linked tie (the pink band) counts as a touch on its bundle (VERIFIED `vlev-A` §2: 6 of 9 bundle taps
  landed on the tie). The tie's cells are part of every member's hit shape.
- **Hidden arrows** (under a locked door, on an inactive elevator layer) cannot be hit; a touch there hits the nearest visible
  arrow within 22 pt, or nothing.
- Nothing within 22 pt: ripple only.

### 2.3 Queued taps (VERIFIED `levels` input model, motion §2.1)
An arrow leaves the blocking grid **at its tap**, not when it leaves the screen. Tapping A (free) and then B (blocked only by A)
770 ms later — while A is still moving — sends B out with no heart lost. Obstacle counters step at the tap (§3.6, §3.7).

### 2.4 What a tap does, by state

| state of the touched arrow | result |
|---|---|
| free (every cell of its ray empty) | **exit** (§3.2) |
| blocked | **bump** (§4) |
| member of a tape bundle | the bundle decides as one unit (§3.4) |
| still moving out (tapped before) | ignored (`IgnoreReason.moving`) |
| in its bump (out and back, ≤ 0.35 s) | ignored (`IgnoreReason.bumping`, DECISION) |
| red (bumped before) and still blocked | bumps again, **no heart** (`rules.json:bump.repeatOnMarkedCostsHeart = false`, VERIFIED once, `fail` §3) |
| red and now free | exits normally (VERIFIED L47: "still a normal arrow") |
| hidden | not hittable (§2.2) |

---

## 3 Board rules

### 3.1 Grid, arrows and the blocking rule (VERIFIED spike + `levels`; executable: `design/tools/arrowcore.py`)
- A level is a `cols × rows` grid (the bounding box of every arrow and obstacle cell). Cells are `[c, r]`, row 0 at the top.
- An arrow is a path of ≥ 2 orthogonally adjacent cells, **tail first, head last**; its direction `dir` is its last step.
  No arrow's straight ray passes over its own body (validator).
- **Ray**: from the head's next cell in `dir` to the grid edge. The arrow is **free** when no cell of its ray is blocked.
  A cell blocks when it holds: a live arrow (visible, not yet tapped); a **locked door** cell; an **unbroken box** cell; a
  **pipe tube** cell entered any way other than through a mouth (§3.6); a **corner** side that does not deflect (§3.9).
  Cells an arrow has vacated (the light-blue dots) never block. Empty cells outside the silhouette never block.
- **Units**: a plain arrow is a unit; a tape bundle is one unit (§3.4).
- **Monotone levels** (no pipes, no elevators, no corners): removing an arrow only ever frees cells, so the order of free taps
  never matters and no dead end exists. Pipes and elevators are non-monotone (§3.11).

### 3.2 Exit
The arrow slides along its own body, then along its ray, off the **screen** (it passes under the HUD). Logically it is gone at
the tap (§2.3). Exit look and kinematics: SPEC-motion-audio (`motion` §3; exit colour #10A2EF, combo ladder). Every exit
(each tape member counts one) lowers every unbroken box counter by 1 **at the tap** (§3.7). A key carried by the arrow is
dispatched **at the tap** (§3.5). A pipe passage is counted **at the tap** (§3.6).

### 3.3 The level ends
- **Win at the tap**: when the tapped unit was the last arrow (visible + hidden = 0), the timer stops at once, input locks and
  the win is banked (arch §4.5). The celebration waits until the last exit has left the board.
- **A win beats a fail**: if the timer reaches 0:00 between the last tap and the end of the last exit, the level is still won
  (DECISION, arch §4.5).
- **Multi-board session** ("Levels 1-4"): the last arrow of stage k (k < 4) → the board-clear wave → the next board builds in
  0.7 s after the last exit left (VERIFIED `tutorials` §2) → a new timer at that board's `timer_s`, frozen until its first tap.

### 3.4 Linked Arrows (the pink tape) — first appearance L7
VERIFIED `levels` L32 (4/4), `vlev-A` §2, `vlev-B`, `vlev-C`, `fail` §3; tie geometry `vlev-A` §2 (28 bundles):
- A bundle is 2, 3 or 4 **straight, parallel, equal-length** arrows in adjacent lanes, all pointing the same way. The tie covers
  exactly **one cell of each member: the cell right behind its head** (`cells[len − 2]`).
- **One tap on any member or on the tie** sends the **whole bundle** out together, each member along its own path, and the tape
  leaves with it — **iff every member's ray is clear** (a member's ray ignores the other members).
- **Any member blocked → the whole bundle bumps** (`tape.blockedPolicy = "bundleBumps"`): it slides as one toward the first
  contact and back, **every member turns red**, one ✖ at the contact point, **one heart** for the bundle (VERIFIED for "every
  ray blocked", `fail` §3; the some-clear case follows the same unit rule, DECISION). A bundle whose members are all red bumps
  for free (§4).
- Each member counts one toward box counters (VERIFIED `vlev-B`/`-C`: a 3-bundle lowers boxes by 3).

### 3.5 Door + Key — first appearance L33 (card: ORCH 19)
VERIFIED `levels` L33/L34/L37/L41/L43/L46/L47/L49/L53/L54/L58, `obstacles`, `motion` §5.2; reconstruction `design/LEVELS.md` §3:
- A **door** is a rectangle of cells (the blue slatted shutter with the purple hexagon lock). Its cells **block** rays while it
  is locked or opening. Doors hide arrows ("hidden arrows") and sometimes keys and tapes on them.
- A **key** hangs on an arrow's body (2 cells). When that arrow **exits**, its key is dispatched **at the tap** to the
  **lowest-`order` locked door not yet targeted** (`order` = the door's position in the level's opening order; `opens` may name
  a door explicitly; no shipped level uses it). The recorded levels opened their doors strictly in data order; every key on a
  door level ends in exactly one door (keys = doors).
- The key flies to the lock (tap → door burst **1.14 s**, `motion` §5.2); **at the burst** the door breaks, its cells become
  empty and every arrow hidden under it becomes **live and visible** at once. Until the burst, the door still blocks (arch
  §4.4: the board acks `doorBurst`). Keys under a door ride hidden arrows; they fly when those arrows exit later ("each door hid
  the key arrow for the next door", L33).
- A hidden arrow is inert: not hittable, never blocks (its cells are door cells, which block anyway). VERIFIED v552 L62: a
  hidden arrow may poke out of its door (its two humps show above the door frame at the start); the validator allows it
  only where no ray can reach the poking cells while the door is shut, so whether they block never matters.
- VERIFIED v552 L69 (Super Hard): other obstacles can lie UNDER a door (three pipes, one under each of three doors). An
  obstacle whose cells all lie inside a door is under it: the locked door blocks first, the obstacle acts (and is drawn)
  only from the burst on (`arrowcore.walk` checks a locked door before a pipe/corner/box).
- A bump never dispatches a key.

### 3.6 Pipe — first appearance L21
VERIFIED `levels` L35/L36/L42, `vlev-C` "Pipe", `vlev-D` "Pipe", `motion` §5.3:
- A pipe is a 1-cell-wide tube along a 4-connected path of cells with a **mouth at each end**; each mouth has an `out` direction
  (the way an arrow leaves through it = the tube's continuation outward). The mouth ring sits **on** the end cell.
- **Passage**: a ray that enters a mouth cell moving **against** that mouth's `out` travels the tube and continues from the other
  mouth, in that mouth's `out` direction (the ray then goes on normally and may enter further pipes; loop guard 16 hops,
  `pipe.maxHops`). A ray that meets any tube cell, or a mouth from the side or the wrong way, is **blocked by the pipe**.
- **Counter**: each passage lowers the counter by 1, **logically at the tap** (§2.3). The visible number changes when the
  passing arrow's head leaves the far mouth (`rules.json:pipe.countAt = "leave"`, VERIFIED `vlev-C`/`-D`: 0.42–0.6 s after the tap;
  the "0" is never shown). At 0 the pipe **breaks** (logically at the tap that used its last pass; it shatters ≈ 0.05 s after
  that arrow's head leaves the far mouth, `motion` §5.3); its cells become empty (nothing is ever under a pipe).
- A **bump through a pipe** (the ray passes the tube and is blocked after the far mouth) consumes nothing
  (`pipe.bumpConsumes = false`, DECISION).
- A tape member passing a pipe counts one passage per member.
- Counters seen: 1…8 (L44's left pipe 8). The badge sits at `counter_at` (cell units; half-cells allowed), measured per level.

### 3.7 Box — first appearance L11 (ORCH 11: the video "Curtain"/"Box" levels use the phone's Box skin and card)
VERIFIED `levels` L50/L51, `vlev-B` (12 breaks), `vlev-C`, `vlev-D`, `motion` §5.4:
- A box is a rectangle of cells with a counter. Its cells **block** while the counter is above 0.
- **Every arrow cleared anywhere** (each tape member one) lowers **every** unbroken box by 1, **at the tap**
  (`rules.json:box.countAt = "tap"`). All boxes count down together.
- On the tap that brings a counter to 0 the box **breaks** on that arrow's first-motion frame ("0" is never shown); its cells
  become ordinary empty cells. Nothing was ever found under a box (24 breaks in the videos, 5 levels on the phone); the schema's
  `reveals` allows it, no shipped level uses it.
- Designer pattern (VERIFIED `vlev-D`): counters are **tight** — the box opens exactly when the arrows behind it are the only
  ones left that can move. The validator requires every box to break before the level ends (counter < arrows).

### 3.8 Elevator — first appearance L31 (video build only; ORCH 11, ORCH 20: video mechanics, phone palette)
VERIFIED `vlev-D` "Elevator" (5 platforms), `web` §3:
- A rectangular **platform** carries layer-1 arrows (the **platform arrows**: every layer-1 arrow whose cells all lie inside it).
  Under it lies a **second layer** of arrows covering the same cells (layer 2, `hidden_by` = the elevator).
- Layer-2 arrows are **inert** while any platform arrow remains: not hittable, never blocking. **Empty platform cells never block**
  (`elevator.emptyCellsBlock = false`, VERIFIED "Empty platform cells do not block rays").
- **Activation at the tap** of the last platform arrow: from that tap the layer-2 arrows are **live** (they block and can be
  tapped), before the doors visibly part (VERIFIED L32: a tap 0.03 s after the doors began to part bumped against them).
- The platform itself never blocks and never counts toward boxes; each layer-2 arrow counts one when it exits.

### 3.9 Corner — first appearance L70 (card: "Corner! / Unlocked! / Arrows turn when they hit the CORNER!")
VERIFIED on the phone (v552, recast 2026-09-25): unlock card shots/456; the rule in clips S2-L070-corner-first-use,
S2-L070-corner-lower-turn-up, S2-L071-corner-right-moving-turns-up; the phone bot's 291 winning taps on the corner levels
L73/L76/L79/L80/L82 (18 corners) replay under this rule with 0 bumps (`design/tools/replay_log.py`, build/recast). The phone
confirms the web-frame reading; what it adds: corners ship (L70, L71, L73, L76, L79, L80, L82 = half the levels since L70),
they sit on the board's edges or in an empty margin line beside the arrow block, and a level has 1–6 of them.
- A corner is one cell: a red diagonal **plate** on a blue **spring**. `turn` = one incoming → outgoing pair, the reverse pair
  implied: opp(out) → opp(in) (`upRight`: up→right and left→down; `upLeft`: up→left, right→down; `downRight`: down→right,
  left→up; `downLeft`: down→left, right→up). The research files store the plate's facing diagonal s = (sx, sy) (y down):
  a ray moving d with d·s < 0 hits the plate and leaves along d − (d·s)s; so s (1,−1) (plate up-right) = `downRight`,
  (−1,−1) = `downLeft`, (1,1) = `upRight`, (−1,1) = `upLeft` (`import_research.FACING_TURN`, checked for all 16 pairs).
- A ray entering the corner cell from the plate side turns there and goes on from that cell (it may meet more corners,
  pipes, the grid edge). A ray arriving any other way hits the spring and is **blocked by the corner** (INFERRED: the bot's
  model, research/bot/corners.py; no recorded tap tested the spring side). No heart is lost on a turn; a blocked ray bumps
  like any other. The corner never moves, breaks or counts.
- Turns share the pipe loop guard (16 hops, `pipe.maxHops`); the validator refuses any ray that meets its own body or
  loops through corners/pipes, so no shipped ray can cycle.
- Corners are static, so they keep a board monotone (only pipes and elevators are non-monotone); the validator still runs
  its 40 random play orders on corner levels.

### 3.10 Board-level invariants (the validator enforces them, §14.4)
Every level: parses; structurally sound; obstacles well-formed (tape tie on the cell behind each head; doors, boxes and platforms
rectangles; pipe cells an ordered path whose ends are the mouths; counters ≥ 1; keys = doors; `reveals` = the arrows hidden by
it); **solved by the greedy solver** under these rules; every pipe passed, every box broken, every door opened, every elevator
activated in that solution; the 0.6 s-per-tap bot keeps ≥ 20 % of the timer; no dead end in 40 seeded random play orders
(non-monotone levels); unlock card exactly at each feature's first appearance; no two boards identical.

### 3.11 Dead ends
Non-monotone rules (a pipe that breaks early changes where later rays go; an activated elevator adds blockers) could in principle
trap a player. No shipped level can be trapped: the videos' levels had 0 dead ends in 100 random orders (VERIFIED `vlev` §1.1),
and the validator checks 40 random orders on every pipe/elevator level of L1–150 (all clean, `LEVELS.md` §5). The generator's
endless levels pass the same check before they are served (§14.3).

---

## 4 Hearts, bumps and red arrows
VERIFIED `levels` L47/L48, `fail` §3, `obstacles` "BUMP", `motion` §4, `tutorials` §8:
- **3 hearts** per level (`LevelSpec.hearts = 3` on every level). Shown in the timer pill.
- A **bump**: the tapped arrow (or bundle) slides along its own path to the first blocker and back; it turns **red #EE0912**
  and **stays red** for the rest of the level; the blocker flashes red; a ✖ badge at the contact point; a red screen-edge
  vignette. Timings and looks: SPEC-motion-audio (`motion` §4).
- The heart is taken **at contact** (arch §8.3), the **rightmost** full heart breaks. **No time penalty**; the timer keeps
  running through a bump.
- **The first bump starts the timer** like a first successful tap (`rules.json:bump.startsTimer = true`, VERIFIED `fail` §3).
- A **red** arrow that bumps again costs **no heart** (VERIFIED once, `fail` §3; `bump.repeatOnMarkedCostsHeart = false`). A
  bundle bump costs a heart unless every member is already red (DECISION).
- The **3rd heart lost** → "Out of Lives!" (§7) at that contact frame.
- A heart lost does **not** change the win: the title is still "Perfect!" and the reward is the same (VERIFIED L48, V2 L32).
- "Levels 1-4": hearts **carry** across the four boards (`sessions.json hearts = "carry"`, DECISION: it is one level to the
  player; no heart was ever lost in V1, so the original's rule is unobserved).
- Hearts return to 3 at every level start and on "Add Lives" (§7).
- **No stars.** v552 shows no star rating anywhere; the win title is always "Perfect!" (VERIFIED every win panel, phone and both
  videos, including with hearts lost).

---

## 5 The level timer
VERIFIED `levels` L32/L33/L35/L47, `fail` §2, `tutorials` §8, `vlev-A` §5, `boosters` §4:
- Per-level `timer_s` (levels.json). Seen: 3:00 (most), 2:30, 2:00 (Super Hard L59), 3:30 (Hard L34). Video levels L1–31: 3:00
  everywhere (VERIFIED), shipped as the videos show them (ORCH 19).
- Display `m:ss` in the pill ("3:00", "2:30", "0:59", "0:00"; no leading zero on the minutes). The displayed value is
  `ceil(remaining)` (arch §4.6); the first tick shows 1.0 s after the first tap (VERIFIED range 0.0–1.0 s; DECISION within it).
- **The timer starts at the FIRST TAP on an arrow** (an exit or a bump). It does not start at the level load, the intro, an
  unlock card, the "Tap to move!" hint, a pinch, a drag, a tap on empty board, or a booster (VERIFIED: bulb and pinch).
- **Holds** (the timer does not run): the Pause popup, every popup of the level (fail chain, Quit Level?, booster buy), the
  unlock card (before the start anyway), a tutorial step with `holdTimer: true` (none ships: "Tap to move!" has `false` and goes
  away at the first tap, which starts the timer), app background, stage transitions, the win sequence, the hourglass freeze (§6.2).
  `rules.json:session.inputLockingHolds` lists the holds that also lock input.
- **Near 0: nothing** — no colour change, no pulse, no scale, no sound in the last 18 s (VERIFIED `fail` §2 #3,
  `rules.json:clock.alerts = []`).
- **0:00**: the pill shows "0:00" for **1.61 s** with input locked (`game.json:fail.zeroHoldSeconds = 1.61`, VERIFIED), then
  "Out of Time!" appears in one frame (§7). The timer reads 0:00 behind the popups.
- "Levels 1-4": each board re-arms its own timer (3:00), frozen until its own first tap (VERIFIED `tutorials` §2).
- Try Again: a fresh `timer_s`, frozen until the first tap.

---

## 6 Boosters
Two boosters on v552, in the bottom corners: left **hourglass** (id `freeze`), right **bulb** (id `hint`) (VERIFIED `boosters`,
ORCH 10). Both are there from the first board with **3 each** (VERIFIED badges "3" from L1-4 in both videos, phone kickoff 3/3;
`rules.json:economy.startBoosters = {"freeze": 3, "hint": 3}`). No booster unlock, no booster tutorial (VERIFIED). The videos'
extra two (yellow pointer, blue dome) are not built (PLAN DECISION 02:50).

### 6.1 Common rules
- A tap on a booster with stock > 0 uses one at once (badge count −1). Using a booster never starts the timer.
- Stock is the player's (`PlayerState.boosters`), GAME decrements it (arch §4.9).
- A booster is **inert while its own effect is running** (a freeze counting down, a hint arrow still green): no stock is taken
  (DECISION). The other booster stays usable.
- Boosters work in every level including the FTUE and the tutorial board.

### 6.2 Hourglass = time freeze (VERIFIED `boosters` §2, `motion` §7.2)
- The timer freezes at once. An icy hourglass flies to the HUD stopwatch (≈ 1.5 s, the clock frozen during the flight), then a
  frost vignette and a countdown bar under the timer pill ("10" → "1") run for **10 s**; the timer resumes when it ends.
  `rules.json:boosters.freezeSeconds = 10`, `boosters.freezeFlight = 1.5`.
- The freeze counts down only while the level clock would otherwise run: popups and pause hold it too.
- Used **before the first tap**: allowed; the 10 s wait for the first tap and start with it
  (`boosters.freezeRunsBeforeStart = false`, DECISION: never wasted).

### 6.3 Bulb = hint (VERIFIED `boosters` §1, `motion` §7.1; the choice rule is ours)
- The view animates to **max zoom** (28.07 pt per cell; only a pan when the board already opens at max) **centred on one free
  arrow** (≈ 0.65 s ease-in-out), which then blinks **green #00DE00** twice and stays green until it is tapped. The timer does not
  start. When that arrow exits the view returns to fit (INFERRED from the next shot). Timings: SPEC-motion-audio.
- **Which arrow** (DECISION, `game.json:hint.policy = "unblocksMost"`): among the units free right now, the one whose exit
  unblocks the most other arrows (the number of live arrows whose ray passes over its cells); ties → the longer arrow → the lower
  id. A tape bundle is hinted as a whole (all members green). This is `Solver.hintUnit` (C2).
- `rules.json:boosters.hintUnits = 1`. No free unit at that moment (only possible while a door is opening): the tap does nothing
  and no stock is taken.
- The hinted arrow is an ordinary arrow; tapping any other arrow is allowed and the hint stays until the green one exits.

### 6.4 Booster at 0 stock (DECISION; v552 never observed at 0)
The badge shows "+" instead of a number. A tap opens the **booster popup** (timer held): title "Time Freeze" / "Hint", the
booster icon, one line ("Freeze the timer for 10 seconds!" / "Find an arrow that can move!"), a green **"Buy ×3 [coin] 900"**
button and the red X. Buy: coins −900, stock +3, the popup closes and the player taps the booster again to use it. Not enough
coins: the Shop opens over the popup (§9.5), and on return the popup re-checks. `rules.json:economy.boosterPack = {"count": 3,
"price": 900}` — priced like the original's single coin sink (900 = one continue). Boosters are otherwise earned from Claw steps
and shop bundles (VERIFIED: never sold alone in the v552 shop).

---

## 7 Fail chain, Quit, Try Again
VERIFIED `fail` §1–§5, `flows`, `uim` popups (texts exact); every popup appears and disappears in one frame (VERIFIED `motion` §6.3).
While any of them is up the timer is held and reads its last value (0:00 for a time-out).

### 7.1 The chain (`rules.json:failChain`)

| step | when | title | body | green button | grant on accept | key |
|---|---|---|---|---|---|---|
| A | the timer reached 0:00 (+1.61 s hold) | **Out of Time!** | big stopwatch, **"+30 sec"** | **Add Time [coin] 900** | +30 s | `failChain.outOfTime[0]` |
| A′ | the 3rd heart lost (at contact) | **Out of Lives!** | big red heart, **"+3 Lives"** | **Add Lives [coin] 900** | hearts back to 3 | `failChain.outOfHearts[0]` |
| B | next, **only if the streak multiplier is above x1** | **Continue?** | token icon + **"You will lose %lld token and your streak!"** when the Claw Challenge is running (the number = the current multiplier: the Claw points the next win would add); **"You will lose your streak!"** before the Claw unlocks; + the x1 x5 x10 x25 x100 chips, the current one lit | **Play On [coin] 900** | the same grant as the chain's step A/A′ (DECISION) | `[1]`, `onlyWithStreak: true`, `warning: token` |
| C | next | **Continue?** | **"You will lose a life!"** + broken heart | **Play On [coin] 900** | the same grant (DECISION) | `[2]`, `warning: life` |
| D | next | ribbon **"Level %lld"** | broken heart, **"Level Failed!"** | **Try Again** | — (a new attempt) | the end of the chain |

- X on A/A′/B/C → the next step. X on D → **home**. Try Again → the same level at once (§7.3).
- Every step costs **900**, every time, with no escalation within an attempt or across attempts (VERIFIED 900 on every step seen;
  repeats DECISION).
- Accept: coins −900 (`Economy.spend`), the grant, the popup closes and play resumes; the streak multiplier is **kept** (paying is
  what "You will lose your streak!" sells, `social` §4.2).
- Not enough coins: the green button opens the **Shop** over the popup; on return the popup re-checks (DECISION, arch §8.4).
- Step C is shown even when the level was started under unlimited lives (VERIFIED fail #1); it is the copy the original shows.
- "Levels 1-4": the ribbon of step D reads "Level 1-4".
- Under D: the Streak Race strip with **x1** lit (VERIFIED) once the Streak Race is unlocked (L30, §11.3).

### 7.2 Quit
- The in-level **back button**, at any time (also before the first tap) → **"Quit Level?"** / broken heart / **"You will lose a
  life!"** / red **"Quit"** / X. X → back to the level (the timer, if started, resumes; it was held).
- Pause → **Quit** → the same "Quit Level?" popup.
- **Quit** → step **D** ("Level Failed!" / Try Again) directly, no offers (VERIFIED `fail` §5).
- A quit is a **failed attempt**: streak → x1, the life taken at the start is not refunded (§8).

### 7.3 Try Again and the attempt
- Try Again starts the **same board** (levels are fully deterministic: four starts of L62 were pixel-identical, VERIFIED
  `fail` §4), a fresh timer and 3 hearts, boosters keep their stock. It is a new **attempt**: the lives gate applies (§8.2).
- **Failed attempt** (D reached by any path): `stats.losses += 1`; streak multiplier → x1; Claw points unchanged; a Sky Jump run
  fails; Weekly Contest and Streak Race scores unchanged (they only add on wins); the next win of this level is not a first-try win.
- "Levels 1-4": Try Again restarts the session at **stage 1** (DECISION: one level to the player).

---

## 8 Lives
VERIFIED `economy` §2 / §2b and `fail` §6 (ledgers with exact times); `meta` §6.

### 8.1 The model (`rules.json:lives.*`)
- **Max 5** (`lives.max = 5`).
- A life is **taken when a level STARTS** (Play or Try Again) and **given back when that attempt is WON**. A failed or quit
  attempt therefore keeps it spent; nothing else costs a life.
- **Regeneration**: while lives < 5, one life every **30:00** (`lives.refillSeconds = 1800`) on **one continuous clock** whose
  phase is set when the count first drops below 5 (= the level start that took it). The clock is not restarted by a tick.
  When the count is back at 5 the clock stops.
- **Unlimited lives** (`unlimitedLivesUntil`): while active, a level start takes nothing and a win refunds nothing. It is checked
  **at the level start only**: a level started under ∞ costs nothing even if ∞ expires before it ends (VERIFIED). Grants stack:
  `until = max(until, now) + duration` (VERIFIED 30 m + 1 h = "1h 20m", L55).
- The wall clock set back never takes lives away (arch §4.8, MF Lives).

### 8.2 The lives gate
Play or Try Again with **0 lives** (and no ∞) → the **More Lives** popup instead of the level (DECISION; not reached on the phone).
If lives come back (Refill) the level starts at once.

### 8.3 Home lives pill (VERIFIED `economy` §2b, `meta` §6)

| state | pill text |
|---|---|
| 5 | "5" in the heart + **"Full"** |
| 1–4 | count + countdown to the next life **"mm:ss"** ("28:42"); under a minute still "00:12"; at zero **"Finished"** for ≈ 1 s, then the next countdown starts ("29:59") |
| 0 | "0" + countdown |
| ∞ | "∞" in the heart + the time left: **"mm:ss"** under an hour, **"%lldh %lldm"** above ("1h 20m") |

A green "+" badge sits on the heart while lives < 5. Tapping the pill: Full or ∞ → nothing (VERIFIED); otherwise **More Lives**.

### 8.4 More Lives popup (VERIFIED `meta` §6, `economy` §2)
Ribbon **"More Lives"**, the heart with the count and a "+", **"Time to next live:"** + stopwatch "mm:ss", green **"Refill [coin]
900"** (lives to 5; `lives.refillPrice = 900`), green **"[video][heart] +1 Live"** (a rewarded ad), X.
- **SUPERSEDED by SPEC.md ruling 37(d) (owner item 9; A1 2026-09-28): the "+1 Live" rewarded-ad button is NOT built — Refill is
  the only offer and the panel ends under it.** Was: **"+1 Live" (ORCH 18)**: the button is copied where the original has it and
  routed to the offline `AdSlot`, which answers **"Video not available"** (a toast). The reward is **never** granted in Release.
- Not enough coins for Refill → the Shop (§9.5).

### 8.5 App killed mid-level
The attempt counts as **failed** at the next launch (`lives.killIsLoss = true`, DECISION, arch §8.6): streak → x1, the life stays
spent, the player lands on home. Background (not killed) → hold + the Pause popup on return (arch §8.6).

---

## 9 Coins, rewards, shop

### 9.1 Coins (`rules.json:economy.*`, `rewards.*`)

| item | value | tag |
|---|---|---|
| start | **1000** | VERIFIED `vflows` §8 (1000 + 80 + 6 × 20 = 1200 at L11 in both videos) |
| win, normal | **20** | VERIFIED |
| win, Hard | **60** | VERIFIED |
| win, Super Hard | **100** | VERIFIED |
| win, "Levels 1-4" session | **80** (one panel) | VERIFIED `tutorials` §4 |
| continue / Add Time / Add Lives / Play On | 900 | VERIFIED |
| lives Refill | 900 | VERIFIED |
| booster ×3 (at 0 stock) | 900 | DECISION §6.4 |
| event prizes | Claw steps (§11.2); Streak Race, Weekly, Sky Jump, Rocket Race prizes: `social` §4 | VERIFIED/`social` |

- Coins are **banked at the win** (kill-safe) and **flown on home**: "+N" over the LEVEL plate, 5 coins fly to the pill, each
  arrival adds N/5 (VERIFIED `vflows` §6; motion in SPEC-motion-audio). The win panel does not count them up.
- The FTUE banks 80 + 20 + 20 and flies **+120** on the first home (1000 → 1120, VERIFIED).
- Nothing else costs coins (VERIFIED `economy` §1).

### 9.2 Win panel (VERIFIED `flows`, `tutorials` §4, `uim` win)
Yellow ribbon **"Level %lld"** ("Level 1-4" for the session), **"Perfect!"**, **"Rewards:"**, coin pile + amount, green
**"Continue"**, red X. Hard: red panel + ribbon **"☠ Hard Level ☠"**; Super Hard: purple panel + **"☠ Super Hard ☠"**. Under it the
Streak Race strip, or the Rocket Race bar while a race runs (`social` §4.8). **X = Continue** (DECISION: never observed apart).

### 9.3 Where Continue goes
FTUE (`homeSeen == false`, `game.json:ftue.chainUntilLevel = 7`): the next level directly (L1-4 → L5 → L6); after L6 → the first
home. From L7 on: [the Sky Jump progress page while a run is active] → home (coin fly, then the queued claims/offers, `social`
§4.8; the rating prompt after L34, §10.6).

### 9.4 Shop catalogue (VERIFIED `meta` §3 + `economy` §4 TL prices; US $ from the V2 shop and the US store list, `vflows` §8, `web` §7)
Sections in this order: **Special Offers**, **Bundles**, **Coins**. "×N" = N of **each** booster (hourglass + bulb). No "Remove
Ads", no Restore row, no free item (VERIFIED).

| product id (`com.manycode.arrowout.` +) | title | badge | content | US $ | TL |
|---|---|---|---|---|---|
| `offer.special` | Special Offer | **90% OFF** | 1,000 coins + ×1 + ∞ 1h | 0.99 | 49,99 |
| `bundle.mini` | Mini Bundle | — | 2,000 + ×1 + ∞ 3h | 4.99 | 249,99 |
| `bundle.epic` | Epic Bundle | — | 4,000 + ×3 + ∞ 6h | 9.99 | 499,99 |
| `bundle.elite` | Elite Bundle | **Popular** | 8,000 + ×8 + ∞ 12h | 19.99 | 999,99 |
| `bundle.mega` | Mega Bundle | — | 20,000 + ×18 + ∞ 36h | 49.99 | 2.499,99 |
| `bundle.legendary` | Legendary Bundle | **Best Value** | 60,000 + ×36 + ∞ 72h | 99.99 | 4.999,99 |
| `coins.1000` | 1,000 | — | 1,000 coins | 1.99 | 99,99 |
| `coins.5000` | 5,000 | — | 5,000 | 7.99 | 399,99 |
| `coins.10000` | 10,000 | — | 10,000 | 14.99 | 799,99 |
| `coins.25000` | 25,000 | — | 25,000 | 29.99 | 1.499,99 |
| `coins.50000` | 50,000 | — | 50,000 | 54.99 | 2.999,99 |
| `coins.100000` | 100,000 | — | 100,000 | 99.99 | 4.999,99 |

- All consumable. The Special Offer can be bought **once** per install, then its card disappears (DECISION: a "90% OFF" first-buyer
  offer).
- `rules.json:shop.products` = this table (`Grant` = coins, boosters `{"freeze": N, "hint": N}`, `unlimitedLives` seconds).
- **FakeStore** (arch D18) everywhere outside the scheme's StoreKit run: the same catalogue, the price shown in the device region's
  list (TL for region TR, else US $, DECISION), purchase succeeds after 0.3 s, and the shop shows **"Test store: nothing is
  charged"**. The owner's order: never a real charge.

### 9.5 Shop entry points
The Shop tab (nav basket), the home coin pill (the whole pill), and "not enough coins" on any coin button (continues, Refill,
booster ×3): then the Shop opens **over** the popup; closing it returns to the popup, which re-checks the balance.

---

## 10 First launch, FTUE and first-time moments
VERIFIED `tutorials` §1–§12, `vflows` §1–§6, phone F00/flows; ORCH 19 for the unlock cards.

### 10.1 First launch
1. Launch screen → **Loading** (our logo + characters + "Loading" with cycling dots). No publisher splash (arch D22).
2. The **iOS notification prompt** appears over Loading on the first launch (VERIFIED V2 3.0–6.0 s, phone F00). Either answer
   continues. Asked once (`flags.notificationPromptShown`); used by §12.5.
3. Loading cross-fades (≈ 0.1 s) straight into **"Levels 1-4"**, stage 1, with the HUD already in place (no HUD intro, no home).

### 10.2 "Levels 1-4" (sessions.json `L1-4`)
`{"id":"L1-4","levels":[1,2,3,4],"hud_label":"Levels 1-4","panel_label":"Level 1-4","reward":80,"stage_gap_s":0.7,"hearts":"carry"}`
- Four boards played back to back; the HUD tab reads **"Levels 1-4"** on all four; each board has its own 3:00 timer, frozen until
  its first tap; between boards: the clear wave and the next board 0.7 s after the last exit; one celebration and one win panel
  at the end: **"Level 1-4" / "Perfect!" / "Rewards:" 80 / Continue**.
- Stage 1 hint (tutorials.json `tapToMove`): **"Tap to move!"** + the pointing hand on the middle arrow (arrow 1; fingertip at
  cell (0.89, 1.06)); no dim, no spotlight, no input restriction (all 3 arrows are free, so no wrong tap is possible); both appear
  0.36 s after the board; on the first tap of any arrow the caption scales out (0.16 s) and the hand fades (0.12 s); never shown
  again. `holdTimer: false` (the timer starts at that first tap like everywhere). The hand's press loop and looks:
  SPEC-motion-audio / `tutorials` §3.
- First Try Wins counts the session as **four** wins (VERIFIED: 10 at L11 = L1–4 + L5–L10).

### 10.3 The FTUE chain
L1-4 win → Continue → **Level 5** at once (with the HUD intro) → win (20) → Continue → **Level 6** (the heart) → win (20) →
Continue → the **first home**: **+120** flies onto 1000 → 1120. Nothing pops up on the first home (VERIFIED). From L7 on, every
win returns home. `game.json:ftue.chainUntilLevel = 7`. `PlayerState.homeSeen` becomes true on the first home.

### 10.4 Unlock cards (unlocks.json; the first Play of the level)
The level opens **under** a ≈ 90 % dim overlay: the icon pops, the title, "Unlocked!", the card; sparkles; **tap anywhere**
dismisses it; the board is playable with the timer frozen (VERIFIED `tutorials` §6; timings SPEC-motion-audio). Shown once
(`unlocksSeen`); a retry does not show it again. No in-board hint follows any card (VERIFIED).

| level | feature | title | card (the upper-case words are drawn in the blue caps colour) | icon | tag |
|---|---|---|---|---|---|
| 7 | `linked` | **Linked Arrows!** | **LINKED ARROWS move together!** | `unlockIconLinked` | VERIFIED V1 |
| 11 | `box` | **Box!** | **Clear required amount of arrows to break the BOX!** | `unlockIconBox` (purple slab, silver ring "5": phone shots/134) | VERIFIED V2 + phone L50 (ORCH 11) |
| 21 | `pipe` | **Pipe!** | **Pass arrows through the PIPE to break it!** | `unlockIconPipe` | VERIFIED V2 + phone L35 |
| 31 | `elevator` | **Elevator!** | **Clear all arrows on the ELEVATOR to activate it!** | `unlockIconElevator` | VERIFIED V2 |
| 33 | `door` | **Door!** | **Collect the KEY to open the DOOR!** | `unlockIconDoor` | ORCH 19 (our wording; v552 showed none) |

"Unlocked!" is the same line on every card. The validator requires each card exactly at the feature's first appearance.

### 10.5 Hard and Super Hard (VERIFIED `flows`, `tutorials` §7)
No popup. On the home before the level: the Play button and the LEVEL plate turn **red** with a **"Hard Level"** ribbon (Super
Hard: **purple**, **"Super Hard"**). In the level: the Level tab, back and pause buttons red / purple; the timer pill stays blue
(ORCH 10). Rewards 60 / 100. Positions: L19, L25 Hard and L29 Super Hard (videos); from L34 every level ending in **4 is Hard and
every level ending in 9 is Super Hard** (VERIFIED phone 34/44/54, 39/49/59; the Aug-13 web video's L79 is Super Hard too); the
designed and endless levels keep that cadence (`curve.tagByPosition`).

### 10.6 Rating prompt (VERIFIED phone + V2)
Once per install, on the home **right after the L34 win**: `AppStore.requestReview(in:)` (arch D24). `game.json:rating.afterLevel =
34`, `flags.ratingPromptShown`.

### 10.7 Weekly Contest tutorial (VERIFIED phone shots/130–133; `social` §4.3)
The first Play tap on the LEVEL 50 home is intercepted: dim, the cream card **"Tap to compete in Weekly Contest!"**, a yellow arrow
at the trophy tab (the only live target) → the "Weekly Contest" intro page → the Weekly board; the Home tab returns, Play works.
SOC2 builds it; copy in `social` §10.

### 10.8 Level labels
HUD tab: "Level %lld" (or "Levels 1-4"). Win and fail ribbons: "Level %lld" ("Level 1-4"). Home: "LEVEL" over the number plate.

---

## 11 Streak multiplier, Claw Challenge, event hooks
The world (opponents, calendars, group sizes, prizes of the races) is SPEC-social's. This section owns the rules every event
shares and the Claw ladder.

### 11.1 The win-streak multiplier (VERIFIED `flows`, `levels` L32–L61, `economy` §5; `social` §4.2)
- Steps **x1 → x5 → x10 → x25 → x100** (`rules.json:streak.steps = [1, 5, 10, 25, 100]`); x100 stays.
- A **won attempt** scores the multiplier **lit before the win** (Claw points, Streak Race flags), then steps up one. A paid
  continue keeps the streak.
- A **failed attempt** (Level Failed by any path: time, hearts, quit, kill) → **x1**. The retry's win then scores x1 and steps to x5
  (VERIFIED L47/L52: 140 → 141 after the x1 win).
- One global value, persisted (`PlayerState.events`). It starts counting when the **Streak Race unlocks (L30)**; before that it
  stays x1, so the fail chain's step B never appears in L1–L29 (DECISION: the videos' build had no events and no step B; the phone
  showed step B from L32).
- The chips on step B and under the fail panel show x1 lit after the reset; an orange x1 chip slides over the lost one (VERIFIED
  L47, look: SPEC-ui/motion).
- **First-try win**: a win on the level's first attempt (no failed attempt of that level before; paid continues do not count as a
  failure). `stats.firstTryWins` (Profile), Sky Jump progress.

### 11.2 Claw Challenge (VERIFIED `flows`, `levels` bar readings L32–L61, `meta` §5.2; duration `social` §4.1)
- Weekly (ends Monday 07:00 UTC, `social` D2); unlocks at **L33** — its first-open screen appears right after the **L32** win
  (VERIFIED), then the home bar.
- Points per win = the multiplier before the win (§11.1). A failed attempt removes no points (VERIFIED 122/500 before and after).
- The bar fills toward the current step's threshold; on reaching it the step completes, the **overflow carries** (240 − 200 = 40,
  VERIFIED L38: "37/300"–"40/300" readings), and the reward is claimed on the next home: **"Congratulations!"** + the reward +
  **"Tap to Claim"** (VERIFIED shots/033, 100, 172, 197).
- After step 20 the bar stays full until the week ends (DECISION). A new week restarts at step 1 with 0 points.
- `rules.json:claw.ladder` (threshold, reward):

| step | threshold | reward | tag |
|---|---|---|---|
| 1 | 1 | ∞ 30m | VERIFIED |
| 2 | 200 | 100 coins | VERIFIED |
| 3 | 300 | ∞ 30m | VERIFIED |
| 4 | 400 | 200 coins | VERIFIED |
| 5 | 300 | ∞ 1h | VERIFIED |
| 6 | 500 | bulb ×1 | VERIFIED |
| 7 | 500 | 300 coins | VERIFIED (22/500 after step 6, "next 300") |
| 8 | 600 | ∞ 2h | reward VERIFIED ladder art, threshold DECISION |
| 9 | 600 | 400 coins | " |
| 10 | 700 | ∞ 3h | " |
| 11 | 700 | hourglass ×2 | " |
| 12 | 800 | ∞ 4h | " |
| 13 | 800 | bulb ×2 | " |
| 14 | 1000 | 2000 coins | " |
| 15 | 900 | ∞ 5h | " |
| 16 | 1000 | 500 coins | " |
| 17 | 1000 | bulb ×1 | " |
| 18 | 1100 | 600 coins | " |
| 19 | 1200 | ∞ 6h | " |
| 20 | 1500 | 10000 coins | " |

The DECISION thresholds keep the recorded shape (a slow rise, the coin steps a little dearer); a player winning every level at x100
completes the ladder in ≈ 141 wins a week. **Conflict to reconcile**: `social` D16 proposes 400, 500, 400, … from step 7, but the phone
shows step 7 = 500 (`levels` L60, `fail` §0 "122/500"); this table wins for the values (SPEC.md §4), SPEC-social should point here.

### 11.3 Event unlock levels (`social.json:unlocks`; = `social` §1.3 / D11)

| event | appears | evidence |
|---|---|---|
| Streak Race | reaching **L30** (the strip under win/fail panels, the home badge, the daily list) | DECISION inside the evidence (> L21 in the Aug build, live at L32 on v552) |
| Claw Challenge | after the **L32** win (first-open screen), bar from L33 | VERIFIED |
| Sky Jump | "Join" badge after the **L39** win (L40 home) | VERIFIED |
| Weekly Contest | the **L50** tutorial (§10.7); before it the Weekly tab reads "Reach level 50 to compete in Weekly Contest!" | VERIFIED |
| Rocket Race | offer after the **L54** win (L55 home) | VERIFIED |

### 11.4 What each attempt reports to the events (G2's hooks; rules in `social` §4)

| hook | Streak Race | Claw | Sky Jump | Weekly Contest | Rocket Race |
|---|---|---|---|---|---|
| won | + multiplier before the win | + multiplier before the win | +1 if first-try (a run) | +1 (from L50) | +1 (a race) |
| failed | — (multiplier → x1) | — | the run fails | — | — |

---

## 12 Settings, Support, Terms, Privacy, notifications

### 12.1 Settings popup (VERIFIED `meta` §4, V2 settings)
Title **"Settings"**, red X. Rows: **"Notifications"** ON/OFF slider; three square toggles **"Sound"**, **"Music"**, **"Haptic"**
(OFF = a red slash over the icon); green **"Support"**; blue **"Terms"** and **"Privacy"**. Every toggle writes
`PlayerState.settings` at once (never UserDefaults), no toast, no system prompt (VERIFIED).

| setting | default | effect |
|---|---|---|
| Notifications | ON | our two local notifications (§12.5) are scheduled only when ON and iOS allows them |
| Sound | ON | the SFX bus |
| Music | **OFF** | stores its state only: v552 has no music (the phone's Music button is inert, VERIFIED `meta` §4; V2 shows Music OFF). DECISION. Request: `PlayerState.Settings.music` defaults to `true` in the ◆ file — first launch writes `false` (G2) or the orchestrator changes the default |
| Haptic | ON | `Haptics.enabled` |

The in-level Pause panel shows **Sound** and **Haptic** only (VERIFIED).

### 12.2 Support (the app-factory Contact rule, adapted)
**"Support"** opens a mail to **anycodeapps@gmail.com** (the in-app composer, MFMailComposeViewController, when the device can send
mail; else a `mailto:` URL; composing needs no network),
subject **"%@ Support"** (Brand.name → "Arrow Out Support"), body **"Please describe your issue above. We will get back to you as
soon as possible."** + an empty line + **"Version : %@"** + **"Level : %lld"** (the original's body shape, without a device id).
No mail account: a small popup **"Write to us at"** + the address + **"Copy"** (→ toast **"Copied"**). Never claims a message was sent.

### 12.3 Terms (offline in-app page, DECISION; text §16.10)
A scrolling page with the title **"Terms"** and our text: what the game is, virtual items have no money value, purchases through
Apple, updates, contact. OWNER 10:35: the page says NOTHING about the other players (neither simulated nor online) — see SPEC.md §5.24.

### 12.4 Privacy (offline in-app page, DECISION; text §16.10)
Title **"Privacy"**: no personal data collected, no accounts, no ads, no analytics, no tracking; progress stays on the device;
purchases by Apple; local notifications; support e-mails used only to answer. True for this build (arch D19).

### 12.5 Local notifications (ORCH 5; `game.json:notifications.*`)
Asked at first launch over Loading (§10.1). Scheduled on the device, only when Notifications is ON and authorised; all pending ones
are recomputed on every background/foreground and cancelled while the app is open.

| id | fires | title | body |
|---|---|---|---|
| `livesFull` | the moment lives regenerate to 5, if the app is in the background and lives were < 5 | Brand.name | **"Your lives are full! Time to play!"** |
| `weeklyEnding` | 2 h before the Weekly Contest ends (Monday 05:00 UTC), if the player joined this week's contest (L50+) | Brand.name | **"The Weekly Contest ends in 2 hours!"** |

No other notification, no badge number, no sound beyond the system default.

---

## 13 Profile (VERIFIED `meta` §2, V2 50–70 s; the world data: `social`)
- Home avatar → **Profile** page: title **"Profile"**, red X; card with the avatar (pencil badge), the name, a **"Level %lld"**
  tile; **"General Stats"** 2 × 3 tiles: **First Try Wins**, **Weekly Contest Wins**, **Streak Race Wins**, **Rocket Race Wins**,
  **Sky Jump Wins**, **Claw Challenge Wins**; a zero shows **"-"** (VERIFIED).
  Counting: First Try Wins §11.1; Weekly Contest Wins = weeks finished 1st; Streak Race Wins = days finished 1st; Rocket Race Wins =
  races won (any stage); Sky Jump Wins = stages won; Claw Challenge Wins = weeks in which step 20 was reached (DECISION for the last
  four; the phone showed Sky Jump Wins 1 after one stage won, VERIFIED).
- **Name**: default **"player_"** + 7 lowercase letters/digits from the install seed (VERIFIED format, `social` §2.8). Opening Profile
  while the name is still the default shows **"Enter Username"** / **"Create your username:"** / a text field / **"Continue"** / X
  (VERIFIED V2; not forced). Rules (DECISION): 3–15 characters after trimming; letters of any script, digits, "_", "." and single
  inner spaces; must pass the social blocklists (`design/social/data`); errors: **"Name must be 3-15 characters"**, **"This name is
  not allowed"**.
- Pencil → **"Edit Profile"**: the avatar + the name field with a pencil, a **3 × 3 avatar grid** (the default grey silhouette +
  8 recoloured worker/scientist portraits, ORCH 12; the selected one framed green with a ✓), green **"Save"**, X (nothing saved).

---

## 14 Level content (design/levels.json; detail and provenance: design/LEVELS.md)

### 14.1 The file
One JSON object (keys starting with "_" are comments): `schema: 1`, `authoredEnd: 150`, `sessions`, `unlocks`, `tutorials`,
`curve`, `levels` (150 levels, one per line). CONTENT runs `pclevels bundle design/levels.json App/Resources/Levels` to write
`level_NNNN.json` (each level object as it is), `sessions.json` (`{"schema":1,"sessions":[…]}`), `unlocks.json`, `tutorials.json`,
`curve.json`. Every level is the **bundle schema v1** of `LevelJSON.swift` exactly:
- level: `schema, level, source ("video" | "recorded" | "designed"), capture (the research frame/shot; null for designed), cols, rows,
  mask (null: the silhouette is the arrow cells, VERIFIED `vlev-A` §6), timer_s, hearts, tag ("normal" | "hard" | "superHard"),
  arrows, obstacles, unlock?, seed? (designed), metrics (rounds, free_at_start, arrows, cells, mean_length, bot_time_left)`;
- arrow: `id, cells [[c,r]…] tail → head, dir, layer? (2 = elevator layer), hidden_by? (a door or elevator id)`;
- obstacle: `id (t/d/k/p/b/e/x + index), kind, cells, arrows? (tape members · the key's rider · platform arrows), turn? (corner,
  §3.9), ends? (pipe: 2 ×
  {cell, out}, cells ordered mouth → mouth), counter? (pipe passes · box clears), counter_at? (pipe badge centre, cell units),
  order? (door opening order, 0-based), reveals? (arrows hidden by a door / an elevator's layer 2)`.
- `_from` (comment) on the substituted and spare levels (§14.2).
No field name differs from the architecture's default, so C1's decoder needs no change.

### 14.2 The list (ORCH 19; full table in LEVELS.md §1)

| range | source | notes |
|---|---|---|
| L1–L31 | **video** (V1 L1–10, V2 L11–31), video order, the videos' timers (3:00) and tags (Hard L19, L25; Super Hard L29) | "Levels 1-4" = L1–L4; verified 31/31 by the video verifier (`vlev` §1.1) |
| L32–L61 | **recorded** on the phone (v552), phone order, v552 timers/tags; the door levels include the arrows (and keys, tapes) hidden under their doors, reconstructed from the bot's round shots (LEVELS.md §3; 11/11 door levels complete, 0 left unreconstructed) | counters and pipe mouths the phone JSON lacked are completed from levels.md and the shots (LEVELS.md §2.2) |
| L35, L45, L51, L52 | **video** V2-L032, V2-L033, V2-L034, V2-L035 in the phone slots (the phone's own boards there are the video's L21, L26, L12, L14) | ORCH 19; each keeps the slot's v552 timer and tag |
| L62–L83 | **recorded** on the phone (v552, session 2), phone order, v552 timers/tags (Hard L64 1:40, L74 3:00; Super Hard L69 2:00, L79 3:00); doors reconstructed like L32–L61 (6 levels, incl. L69's pipes under doors); Corner card at L70 | LEVELS.md §2.5 |
| L72, L75, L77 | **video** V2-L036, V2-L038, V2-L037 (the video build's boards v552 does not have) in the phone slots whose boards REPEAT earlier ones (v552 L72 = L52 = video L14, L75 = L55, L77 = L57) | ORCH 19's duplicate rule; each keeps the slot's v552 timer and tag (RECAST DECISION, LEVELS.md §2.4) |
| L81, L83, L86, L100, L101, L103 | **designed** stand-ins for the repeats L81 = L61, L83 = L63, L86 = L66, L100 = L31 (v552's L100 is the older build's V2-L031), L101 = L35 (V2-L032), L103 = L45 (V2-L033), each generated to the repeated board's size, units, waves, free arrows, timer, tag and obstacle kinds | ORCH 26 + 28 (DEDUP: the first occurrence in our order wins; LEVELS.md §2.4) |
| L84–L105 | **recorded** on the phone (v552, session 3), phone order, v552 timers/tags (Hard L84 2:00, L94 2:30, L104 3:00; Super Hard L89 2:30, L99 3:00; normals 2:30 / 3:00 as recorded); doors reconstructed like L62–L83 (L89, L93, L98); L102 = v552's new elevator board (22 layer-2 arrows from the bot's -open1 dump); v552's Elevator card at L100 is NOT copied (ours stays at L31, video order) | LEVELS.md §2.6 |
| L106–L150 | **designed** by `gen_levels.py`, seeded by the level number, fitted to the recorded curve L30–L105 (templates L30–L99) | every one solver-proved and validator-gated |
| L151+ | **generated at runtime** by C4's port of the same algorithm and `curve`, seeded by the level number (arch D9) | the original repeats a small pool after ≈ 150, which reviews hate (`web` §5); ours never repeats (DECISION) |

### 14.3 The generator (reference: `design/tools/gen_levels.py`; C4 ports it)
Deterministic from `PathRandom(levelSeed(n, curve.salt))` (bit-exact with PathCore's PathRandom, `design/tools/pathrandom.py`); no
transcendental maths. For level n:
1. **Target**: position p = n mod 10 (p 4 → Hard, p 9 → Super Hard); template = the recorded level at the same position of decade
   slot (n div 10) mod `curve.slots` (7) among L3p … L9p (`curve.templates`: its units, waves, free-at-start, cols × rows, timer);
   growth `min(cap, 1 + perDecade · ⌊(n − 100)/10⌋)` (`growth.from` 100; the 25 % cap is reached at L230) scales units (×g), waves (×(1 + (g−1)/2)) and the grid (×(1 + (g−1)/2),
   ≤ 26 × 36).
2. **Obstacle plan** (fork "plan"): 0, 1 or 2 kinds with weights `curve.obstacles.countWeights = [26, 36, 38]`, kinds drawn by
   `kindWeights = {door 27, pipe 23, box 21, tape 17, elevator 6, corner 36}` among the unlocked ones (`firstLevel`, corner 70).
   Each kind's weight = its share of v552's L40–L105 levels since its unlock (corner: 13 of the 36 levels L70–L105); the
   elevator is fitted like the others on v552's L100–L103 and gives 6 % again (LEVELS.md §4).
3. **Regions**: doors (after the recorded layouts: bands, stacked halves, quadrants, a ring of 4, a staircase, two-below-one-above),
   an elevator platform, boxes (corner, bottom bar, corner pair, staircase, side), pipes (∩ caps at the top, ⊏/⊐ on a side, ∪ at the
   bottom, ┐ along two edges) with **feeders** — 2–5 straight arrows (2–4 cells each) lined up in front of one mouth, pointing
   into it, the other mouth's lane left free for the arrows leaving (the recorded pattern: L35's two arrows aimed at its mouth,
   L48's columns under their caps), so a pipe is passed 2–5 times like the recorded counters (median 3–4) — and tape bundles
   (2–4 lanes of 3–4 cells) — and **corners** (laid out last): one side, or two ADJACENT sides, of the board keep an empty margin
   line holding 1–3 corners each, facing the board (v552 L76/L79/L80/L82: corners beside the arrow block, where rays leave;
   adjacent sides only, so no ray can come round a corner loop). A silhouette (oval, octagon, notch, blocks, cross, heart,
   diamond, arch) with probability 0.25 on obstacle-free or tape-only levels.
4. **Tiling**: snakes grown with lengths from the recorded histogram (`curve.lengths`), straightness 0.82 (reproduces the recorded
   0.36 turns per interior cell), merged end to end toward the unit target × 0.80; door rectangles and both elevator layers tiled
   separately.
5. **Heads**: a plain peel (forward removal, split-repair when stuck) + a head-flip local search on the dependency DAG toward the
   target waves and free-at-start (`flipSteps` 3000), giving each snake a preferred head.
6. **Peel with the full rules**: a forward removal simulation takes preferred-head moves first; picks the key riders (a door opens
   right after its rider leaves; the first rider after 5 % of the visible arrows, the next after +18 % or when ≤ 2 moves remain;
   half the time a rider comes from under the previous door); breaks a box or a pipe exactly when nothing else can move (its counter
   = the removals / passages so far; boxes never needed break at 55–95 % of the level); splits a snake when stuck. The removal
   order is a **witness**: the level is solvable by construction.
7. **Checks** (the same validator as §3.10): structure, the greedy solver, bot ≥ 20 % of the timer; the best of `attempts` = 10
   candidates (score = relative distance to units, waves, free-at-start); if the plan is infeasible on every attempt the last kind
   is dropped (never a crash, never an unsolvable level).
8. **Timer** (`curve.timers.fromTemplate`): the template's own v552 timer, every tag (so Hard levels run 1:40 … 3:30 and Super Hard
   2:00 … 3:00 exactly as recorded, e.g. L124 ← L84's 2:00 (Hard), L109 ← L69's 2:00 (Super Hard)); the older keys (hard/superHard/normal/short/pShort) stay in the curve,
   refitted, for a reader without `fromTemplate`.
9. **Gate** (authored levels, and C4's runtime `LevelProvider`): a candidate that would become the best is validated first
   (§14.4); a refused one is dropped ("gate: <reason>") and the attempts go on (`gen_levels.generate(gate=)` = C4's
   `Generator.generate(gate:)`). In L106–L150 only L136 needed it.
Runtime (endless, C4): the next level is generated on a background queue when a level starts and cached (Python worst case 3.2 s
for a 26 × 36 Hard board; Swift -O is ~50× faster); a candidate failing the validator retries with the next attempt fork; the
level is never served unvalidated.

### 14.4 The validator (`design/tools/validate_levels.py`; C4's `Validator` implements the same list)
§3.10's list, plus: level numbers 1…150 contiguous; `metrics` equal to the recomputed values; sessions and tutorials point at real
levels and arrows; no board repeats another (design/tools/repeats.py: offset-free,
under the 8 rotations/mirrors of the square, on the start-visible arrows or on every layer; SPEC.md §5 item 28); no ray meets its own body or loops (pipes/corners); an
obstacle may lie wholly inside a door (under it, §3.5) and a door-hidden arrow may poke out of its door only where no ray can
reach it. Result on the shipped file: **150 levels, 0 errors**, 1 warning (L6 is 27 columns wide: its fit pitch 13.55 pt is
below the 14.04 pt zoom floor — VERIFIED as the video shows it). `design/tools/validator_selftest.py` applies 20 mutations
(the 15 + recast 2: L86 given back its phone board (= L66), L134 = L94 mirrored left-right, L101 given back its phone board
(= V2-L032 at L35), L93's key under its first door removed, L102's platform list one short; the 15: a tight box counter +1, a reversed arrow, a removed unlock card, a pipe counter 0, a door reveals list short, a missing key, a tape
tie off its cell, a repeated board, a never-breaking box, a short platform list; corners turned away, a pipe moved half out of its
door, a door-hidden arrow made visible, the repeated L72 board, the Corner card removed): **20/20 caught** (build/recast2/selftest.txt).

---

## 15 Tuning keys (every value of this spec)
`rules.json` (C2; the `economy`/`lives`/`shop`/`claw`/`streak` sections decoded by C3):
```json
{
  "tape": { "blockedPolicy": "bundleBumps" },
  "bump": { "repeatOnMarkedCostsHeart": false, "startsTimer": true },
  "pipe": { "countAt": "leave", "bumpConsumes": false, "maxHops": 16, "missingCounterIsUnlimited": true },
  "box": { "countAt": "tap" },
  "elevator": { "emptyCellsBlock": false },
  "hit": { "radiusPt": 22, "tieBreak": "rightThenDown" },
  "clock": { "alerts": [], "emptyTapStartsTimer": false },
  "failChain": {
    "outOfTime":   [ {"price": 900, "grant": "addTime", "amount": 30, "warning": "none"},
                     {"price": 900, "grant": "addTime", "amount": 30, "warning": "token", "onlyWithStreak": true},
                     {"price": 900, "grant": "addTime", "amount": 30, "warning": "life"} ],
    "outOfHearts": [ {"price": 900, "grant": "refillHearts", "amount": 3, "warning": "none"},
                     {"price": 900, "grant": "refillHearts", "amount": 3, "warning": "token", "onlyWithStreak": true},
                     {"price": 900, "grant": "refillHearts", "amount": 3, "warning": "life"} ] },
  "rewards": { "normal": 20, "hard": 60, "superHard": 100, "session": { "L1-4": 80 } },
  "boosters": { "actions": { "freeze": "freezeTimer", "hint": "hint" }, "freezeSeconds": 10, "freezeFlight": 1.5,
                "freezeRunsBeforeStart": false, "hintUnits": 1 },
  "economy": { "startCoins": 1000, "startBoosters": { "freeze": 3, "hint": 3 }, "boosterPack": { "count": 3, "price": 900 } },
  "lives": { "max": 5, "refillSeconds": 1800, "refillPrice": 900, "killIsLoss": true },
  "streak": { "steps": [1, 5, 10, 25, 100] },
  "claw": { "period": "week", "ladder": [
    {"threshold": 1, "grant": {"unlimitedLives": 1800}}, {"threshold": 200, "grant": {"coins": 100}},
    {"threshold": 300, "grant": {"unlimitedLives": 1800}}, {"threshold": 400, "grant": {"coins": 200}},
    {"threshold": 300, "grant": {"unlimitedLives": 3600}}, {"threshold": 500, "grant": {"boosters": {"hint": 1}}},
    {"threshold": 500, "grant": {"coins": 300}}, {"threshold": 600, "grant": {"unlimitedLives": 7200}},
    {"threshold": 600, "grant": {"coins": 400}}, {"threshold": 700, "grant": {"unlimitedLives": 10800}},
    {"threshold": 700, "grant": {"boosters": {"freeze": 2}}}, {"threshold": 800, "grant": {"unlimitedLives": 14400}},
    {"threshold": 800, "grant": {"boosters": {"hint": 2}}}, {"threshold": 1000, "grant": {"coins": 2000}},
    {"threshold": 900, "grant": {"unlimitedLives": 18000}}, {"threshold": 1000, "grant": {"coins": 500}},
    {"threshold": 1000, "grant": {"boosters": {"hint": 1}}}, {"threshold": 1100, "grant": {"coins": 600}},
    {"threshold": 1200, "grant": {"unlimitedLives": 21600}}, {"threshold": 1500, "grant": {"coins": 10000}} ] },
  "shop": { "specialOfferOnce": true, "products": [
    {"id": "offer.special", "usd": 0.99, "try": 49.99, "badge": "90% OFF", "grant": {"coins": 1000, "boosters": {"freeze": 1, "hint": 1}, "unlimitedLives": 3600}},
    {"id": "bundle.mini", "usd": 4.99, "try": 249.99, "grant": {"coins": 2000, "boosters": {"freeze": 1, "hint": 1}, "unlimitedLives": 10800}},
    {"id": "bundle.epic", "usd": 9.99, "try": 499.99, "grant": {"coins": 4000, "boosters": {"freeze": 3, "hint": 3}, "unlimitedLives": 21600}},
    {"id": "bundle.elite", "usd": 19.99, "try": 999.99, "badge": "Popular", "grant": {"coins": 8000, "boosters": {"freeze": 8, "hint": 8}, "unlimitedLives": 43200}},
    {"id": "bundle.mega", "usd": 49.99, "try": 2499.99, "grant": {"coins": 20000, "boosters": {"freeze": 18, "hint": 18}, "unlimitedLives": 129600}},
    {"id": "bundle.legendary", "usd": 99.99, "try": 4999.99, "badge": "Best Value", "grant": {"coins": 60000, "boosters": {"freeze": 36, "hint": 36}, "unlimitedLives": 259200}},
    {"id": "coins.1000", "usd": 1.99, "try": 99.99, "grant": {"coins": 1000}},
    {"id": "coins.5000", "usd": 7.99, "try": 399.99, "grant": {"coins": 5000}},
    {"id": "coins.10000", "usd": 14.99, "try": 799.99, "grant": {"coins": 10000}},
    {"id": "coins.25000", "usd": 29.99, "try": 1499.99, "grant": {"coins": 25000}},
    {"id": "coins.50000", "usd": 54.99, "try": 2999.99, "grant": {"coins": 50000}},
    {"id": "coins.100000", "usd": 99.99, "try": 4999.99, "grant": {"coins": 100000}} ] }
}
```
`board.json` (B1): `"input": { "hitRadiusPt": 22, "tieBreak": "rightThenDown", "tieTolerancePt": 1.0 }`.
`game.json` (G1/G2): `"ftue": { "chainUntilLevel": 7 }`, `"rating": { "afterLevel": 34 }`, `"fail": { "zeroHoldSeconds": 1.61 }`,
`"hint": { "policy": "unblocksMost" }`, `"notifications": { "askOnFirstLaunch": true, "livesFull": true, "weeklyEndingHours": 2 }`.
`social.json` (SOC1): `"unlocks": { "streakRace": 30, "clawChallenge": 33, "skyJump": 40, "weeklyContest": 50, "rocketRace": 55 }`.
Changed from the files as they stand today: `hit.radiusPt` 15 → 22, `input.hitRadiusPt` 16 → 22, `pipe.countAt` "enter" →
"leave", `lives.refillSeconds` 1200 → 1800; new: `economy`, `lives.*` (rest), `streak`, `claw`, `shop`, `rewards.session`, the game.json
`fail`/`hint`/`notifications.*` keys.

---

## 16 Strings (EN = the original's copy where it exists; TR = ours)
The original's UI is English only (VERIFIED `flows` header). TR is natural casual-game Turkish; a positional form (`%1$@`, `%2$lld`)
is used wherever TR reorders arguments. Integers are `%lld` (Swift `Int`). Social/event screens: SPEC-social §10 (same keys, its TR
wins there); the rows repeated here are the ones gameplay popups use. CONTENT copies these into `strings.tsv`.

### 16.1 Board, HUD, tutorial

| EN | TR | where |
|---|---|---|
| Level %lld | Seviye %lld | HUD tab, win/fail ribbons |
| Levels 1-4 | Seviye 1-4 | HUD tab of the first session |
| Level 1-4 | Seviye 1-4 | its win/fail ribbon |
| Tap to move! | Dokun ve oynat! | the L1 stage-1 caption (VERIFIED EN) |
| Loading | Yükleniyor | Loading |

### 16.2 Unlock cards

| EN | TR |
|---|---|
| Unlocked! | Açıldı! |
| Linked Arrows! | Bağlı Oklar! |
| LINKED ARROWS move together! | BAĞLI OKLAR birlikte hareket eder! |
| Box! | Kutu! |
| Clear required amount of arrows to break the BOX! | KUTUYU kırmak için gereken sayıda oku temizle! |
| Pipe! | Boru! |
| Pass arrows through the PIPE to break it! | BORUYU kırmak için okları içinden geçir! |
| Elevator! | Asansör! |
| Clear all arrows on the ELEVATOR to activate it! | ASANSÖRÜ çalıştırmak için üstündeki tüm okları temizle! |
| Door! | Kapı! |
| Collect the KEY to open the DOOR! | KAPIYI açmak için ANAHTARI topla! |

### 16.3 Pause, Quit

| EN | TR |
|---|---|
| Paused | Duraklatıldı |
| Sound | Ses |
| Haptic | Titreşim |
| ON | AÇIK |
| OFF | KAPALI |
| Resume | Devam |
| Quit | Çık |
| Quit Level? | Seviyeden Çık? |
| You will lose a life! | Bir can kaybedeceksin! |

### 16.4 Fail chain

| EN | TR |
|---|---|
| Out of Time! | Süre Doldu! |
| +30 sec | +30 sn |
| Add Time | Süre Ekle |
| Out of Lives! | Canların Bitti! |
| +3 Lives | +3 Can |
| Add Lives | Can Ekle |
| Continue? | Devam? |
| You will lose your streak! | Serini kaybedeceksin! |
| You will lose %lld token and your streak! | %lld jetonu ve serini kaybedeceksin! |
| Play On | Devam Et |
| Level Failed! | Seviye Başarısız! |
| Try Again | Tekrar Dene |

### 16.5 Win

| EN | TR |
|---|---|
| Perfect! | Mükemmel! |
| Rewards: | Ödüller: |
| Continue | Devam |
| Hard Level | Zor Seviye |
| Super Hard | Süper Zor |
| +%lld | +%lld |

### 16.6 Home, lives

| EN | TR |
|---|---|
| Play | Oyna |
| LEVEL | SEVİYE |
| Full | Dolu |
| Finished | Bitti |
| More Lives | Daha Fazla Can |
| Time to next live: | Sonraki cana kalan süre: |
| Refill | Doldur |
| +1 Live | +1 Can |
| Video not available | Video şu anda kullanılamıyor |
| Not enough coins | Yeterli altın yok |
| Congratulations! | Tebrikler! |
| Tap to Claim | Almak için dokun |
| %lldd %lldh | %lldg %lldsa |
| %lldh %lldm | %lldsa %llddk |
| %lldh | %lldsa |
| %lldm | %llddk |

### 16.7 Boosters

| EN | TR |
|---|---|
| Time Freeze | Zaman Dondurucu |
| Freeze the timer for 10 seconds! | Süreyi 10 saniye dondur! |
| Hint | İpucu |
| Find an arrow that can move! | Çıkabilen bir oku bul! |
| Buy | Satın Al |
| x%lld | x%lld |

### 16.8 Shop

| EN | TR |
|---|---|
| Shop | Mağaza |
| Special Offers | Özel Teklifler |
| Special Offer | Özel Teklif |
| 90% OFF | %90 İNDİRİM |
| Bundles | Paketler |
| Mini Bundle | Mini Paket |
| Epic Bundle | Epik Paket |
| Elite Bundle | Elit Paket |
| Mega Bundle | Mega Paket |
| Legendary Bundle | Efsanevi Paket |
| Popular | Popüler |
| Best Value | En Avantajlı |
| Coins | Altınlar |
| Test store: nothing is charged | Test mağazası: hiçbir ücret alınmaz |
| Purchase complete! | Satın alma tamamlandı! |
| Purchase pending | Satın alma bekliyor |

### 16.9 Settings, Support, Profile, notifications

| EN | TR |
|---|---|
| Settings | Ayarlar |
| Notifications | Bildirimler |
| Music | Müzik |
| Support | Destek |
| Terms | Koşullar |
| Privacy | Gizlilik |
| %@ Support | %@ Destek |
| Please describe your issue above. We will get back to you as soon as possible. | Lütfen sorununu yukarıya yaz. En kısa sürede sana dönüş yapacağız. |
| Version : %@ | Sürüm : %@ |
| Level : %lld | Seviye : %lld |
| Write to us at | Bize şu adresten yazabilirsin: |
| Copy | Kopyala |
| Copied | Kopyalandı |
| Profile | Profil |
| General Stats | Genel İstatistikler |
| First Try Wins | İlk Denemede Kazanılan |
| Weekly Contest Wins | Haftalık Yarışma Birincilikleri |
| Streak Race Wins | Seri Yarışı Birincilikleri |
| Rocket Race Wins | Roket Yarışı Zaferleri |
| Sky Jump Wins | Gökyüzü Zıplayışı Zaferleri |
| Claw Challenge Wins | Pençe Mücadelesi Zaferleri |
| - | - |
| Enter Username | Kullanıcı Adı |
| Create your username: | Kullanıcı adını oluştur: |
| Edit Profile | Profili Düzenle |
| Save | Kaydet |
| Name must be 3-15 characters | İsim 3-15 karakter olmalı |
| This name is not allowed | Bu isim kullanılamaz |
| Your lives are full! Time to play! | Canların doldu! Oynama zamanı! |
| The Weekly Contest ends in 2 hours! | Haftalık Yarışma 2 saat içinde bitiyor! |

### 16.10 Terms and Privacy pages (DECISION; one string each, paragraphs separated by blank lines)
**Terms, EN:**
> Arrow Out is a puzzle game.
>
> Coins, lives, boosters and other items in the game have no money value and cannot be exchanged or refunded outside the game.
>
> Purchases are made through Apple and follow the App Store terms. We never see your payment details.
>
> The game is provided as is. We may update the game and these terms.
>
> Questions? Write to anycodeapps@gmail.com

**Terms, TR:**
> Arrow Out bir bulmaca oyunudur.
>
> Oyundaki altınların, canların, güçlendiricilerin ve diğer öğelerin parasal değeri yoktur; oyun dışında değiştirilemez veya iade edilemez.
>
> Satın almalar Apple üzerinden yapılır ve App Store koşullarına tabidir. Ödeme bilgilerini asla görmeyiz.
>
> Oyun olduğu gibi sunulur. Oyunu ve bu koşulları güncelleyebiliriz.
>
> Sorun mu var? anycodeapps@gmail.com adresine yaz.

**Privacy, EN:**
> Arrow Out collects no personal data. There are no accounts, no ads, no analytics and no tracking.
>
> Your progress, settings and profile name are stored only on this device.
>
> The game works offline. Purchases are handled by Apple.
>
> Notifications are scheduled on your device and can be turned off in Settings.
>
> If you write to support, we use your message only to answer you.
>
> Contact: anycodeapps@gmail.com

**Privacy, TR:**
> Arrow Out hiçbir kişisel veri toplamaz. Hesap, reklam, analiz ve takip yoktur.
>
> İlerlemen, ayarların ve profil adın yalnızca bu cihazda saklanır.
>
> Oyun çevrimdışı çalışır. Satın almalar Apple tarafından yürütülür.
>
> Bildirimler cihazında planlanır ve Ayarlar'dan kapatılabilir.
>
> Desteğe yazarsan mesajını yalnızca sana yanıt vermek için kullanırız.
>
> İletişim: anycodeapps@gmail.com

"Arrow Out" in these texts comes from `Brand.name` (`%@`); the TR sentence keeps the name first, so no reordering is needed.

---

## 17 Requests, conflicts and open questions

### 17.1 Requests (to the orchestrator / owners)
1. **UI-ART**: an unlock icon **`unlockIconBox`** (the phone's purple slab with a silver ring "5", shots/134) is missing from
   `art/MANIFEST.json` (there are `unlockIconCurtain`/`unlockIconDoor`, which show the door shutter). Box sprites at every size the
   content uses (LEVELS.md §2.5 lists them) and door sizes beyond the manifest's nine (the generator makes any; `manifest.py add-door`).
2. **◆ PlayerState**: `Settings.music` defaults to `true`; this spec's default is **false** (§12.1). Either the orchestrator changes
   the default or G2 writes `false` at first launch.
3. **C2** `rules.json`: `hit.radiusPt` 22, `pipe.countAt` "leave", `lives.refillSeconds` 1800, and the new sections of §15.
   **B1** `board.json`: `input.hitRadiusPt` 22.
4. **C3**: decode `economy`, `lives`, `streak`, `claw`, `shop` from rules.json (§15); `rewards.session["L1-4"] = 80` duplicates
   `sessions.json reward` (the session value wins).
5. **C4**: port `gen_levels.py` + `curve` for L151+ and test that the port reproduces `design/levels.json` L65–L150 byte for byte (a
   strong check that the port is exact); run the §14.4 validator on every generated level before serving it.
6. **SPEC-social**: point D16 (Claw thresholds) at §11.2 (the phone's step 7 is 500).

### 17.2 Open questions (each has a DECISION above; a phone session could confirm)
- A tape bundle with **some** members blocked (only "all blocked" was seen): our rule = the whole bundle bumps.
- What a booster does at 0 stock (never reached): our buy popup, ×3 for 900.
- Fail-chain repeats inside one attempt (a second time-out after Add Time): our rule = the same chain, 900 each.
- Try Again at 0 lives: our rule = the More Lives popup.
- The hit radius beyond 22 pt and the tie rule beyond the one midpoint tap.
- Which arrow the original's bulb picks (one observation): ours = the free arrow that unblocks the most.
- Claw steps 8–20 thresholds (the rewards are from the ladder art; the thresholds are ours).
- The Door card text (v552 introduced doors before L32; ORCH 19 wording).
- Music: v552 has none switchable; ours stores the toggle.
- Corner: the look is the phone's (plate + spring, shots/456); the rule is VERIFIED (§3.9).
