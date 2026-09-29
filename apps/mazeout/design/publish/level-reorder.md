# Arrow Out — level re-order plan (PUBLISH item 12, SPEC.md ruling 37e)

Author: level re-order planner, 2026-09-28. This phase only investigates and plans: no App/Packages/Tests/UITests edits, no
simulator, no xcodebuild, no phone, and nothing under design/ except this document and its reference prototype
(`design/publish/tools/level_reorder/`). design/levels.json, the bundle and every pin are untouched.
Tags: **VERIFIED** = seen in a file / measured by running the existing Python tools on this Mac (command given).
**INFERRED** = reasoned from several signals. **DECISION** = ours, tunable, listed in §11 for the owner/orchestrator.

---

## 0. TL;DR

- **Freeze L1–L33** (the FTUE, the "Levels 1-4" session, the tutorial and FIVE of the six unlock cards: Linked L7, Box L11,
  Pipe L21, Elevator L31, Door L33) and the **Corner card L70**. **Re-order L34–L105** (the range recorded from the original on
  the phone, where 61 of our boards sit at the original's own level number today). **Keep L106–L150** (our own generated
  boards) and the endless generator (L151+) untouched.
- **Rules**: an obstacle never before its teaching level; the level after a card practises it (L34 door, L71 corner); every
  slot keeps its tag (Hard at x4 / Super Hard at x9 exactly as today) and a board moves only inside its tag class; timers
  travel with their board and no ≤ 2:00 timer comes earlier than in the original; no board at its original number; no two
  boards that were consecutive in the original stay consecutive; look-alike boards ≥ 10 levels apart; ≤ 3 same-obstacle
  levels in a row; the curve inside a tolerance measured from the original curve's own level-to-level jitter.
- **Algorithm** (deterministic, §5): per tag class a min-cost *difficulty-matched derangement* (linear assignment: each slot
  gets a board similar to the one it holds today, never the same one), then a seeded swap search that flattens the curve
  deviation; 64 seeded attempts (PathRandom, salt `arrow-out/reorder/v1`), the in-tolerance attempt with the lowest curve
  error wins. Reference prototype: `design/publish/tools/level_reorder/reorder_ref.py` (~25 s, one core, no solver runs).
- **Candidate computed (VERIFIED)**: 67 boards move (|move| median 7, max 20). Boards at the original's own number:
  **61 → 3** (L32, L33, L70, all frozen on purpose). Consecutive pairs of the original kept consecutive: **49 → 1**
  (L32→L33, frozen). Curve: rolling-9 units max 10.2 % / mean 3.7 %, waves 10.4 % / 3.3 %, time pressure max 0.027 —
  all inside tolerance; decade means within 6.1 %. On a scratch copy the EXISTING validator says **0 errors, the same single
  L6 warning, the same first appearances**; `repeats.py` 0 repeats / 0 near repeats; the 20 negative controls re-targeted
  through the order are **20/20 CAUGHT**; two runs of the search give byte-identical output.
- **Re-pins**: 3 fixtures (content/levels.json + MANIFEST, c4b_bot_replay.json, c4_negative_controls.json), 4 Swift test call
  sites that name a moved board by number (BotReplayTests, RulesTests ×2, ValidatorTests.testSpriteCheck), sample lists that
  should follow their boards (coverage), 6 Python/CONTENT tools that look research files up by level number, the 67 bundle
  files. **Unchanged**: CurveSpec, DifficultyBands, designed.json, the endless references, EndlessFixtures, every UI test, all
  App/ and PathCore Sources code. Nothing is loosened (§9).
- **Blocking caveat for the purpose of item 12 (VERIFIED)**: the SHIPPED level files carry their provenance — 72 files name
  a research shot `research/shots/NNN-L0xx-start.png` whose `L0xx` IS the original's level number, 38 name video frames, 13
  say "phone", and `CurveSpec.swift` compiles the string "v552" into the binary. After a re-order, `level_0044.json` would
  literally say `L034`. Strip provenance from what ships (§11 D3) or the re-order hides nothing from anyone who unzips the IPA.

---

## 1. What the owner asked (verbatim, binding)

> 12- you may want to change the order of changeable levels, like after a certaion point we dont want to be called
> copycatters, so you can change some orders maybe, not breaking the logic, like if there are no pipes still in the game,
> dont change a pipe before the pipe teaching level, you get what i mean

SPEC.md ruling 37(e): "Levels after a point are re-ordered (never before their obstacle's teaching level)." Ruling 37(b): what
stays 1:1 includes "rules, level logic, systems, timings" — so the re-order must keep the difficulty *logic* (cadence,
teaching order, the curve), only the sequence changes.

## 2. What is "copied order" today (VERIFIED from design/levels.json, sha256 `63e41001…`, = the pinned fixture: `pin_fixtures.py --check` → current)

| range | source | at the SAME number as in the source game? |
|---|---|---|
| L1–L31 | the owner's videos = an OLDER build (ruling 19) | yes, as the older build numbered them (31 boards) |
| L32–L105 | the phone, v552 (the current store version) | **61 of 74 slots hold v552's board at v552's number** (capture paths); the other 13 are V2 substitutes (L35, L45, L51, L52, L72, L75, L77) and our generated stand-ins (L81, L83, L86, L100, L101, L103) |
| L106–L150 | `gen_levels.py` (ours) | no (our boards) |
| L151+ | runtime generator (ours) | no |

v552 itself already renumbered the older build: phone L35/L45/L51/L52 = video L21/L26/L12/L14, and v552 L100/L101/L103 =
older build L31/V2-L032/V2-L033 (LEVELS.md §2.3, §2.6, VERIFIED there). So at least 5 of our L1–L31 boards are NOT at their
v552 number. v552's own L1–L31 were never recorded (PLAN DECISION 02:01), so how many of the other 26 still match v552 is
UNKNOWN; the FTUE boards L1–L6 probably do (INFERRED: owner 02:50 "the tutorial and designs are the same").
The number-for-number copy is therefore concentrated in L32–L105 — exactly the range this plan re-orders.

## 3. From which level the order may change: L34 (freeze L1–L33 and the anchor L70)

**DECISION: the zone is L34–L105 minus L70; 71 movable slots.** Justification:

1. **Teaching density.** L1–L33 hold the whole FTUE (session "Levels 1-4" = L1–L4 with the "Tap to move!" tutorial,
   `game.json ftue.chainUntilLevel` 7, first home after L6) and five of the six unlock cards (L7, L11, L21, L31, L33), each
   followed by practice levels (L8 tape, L12–L13 box, L22–L23 pipe, L34/L37 door). Permuting there breaks
   teach-then-practice for new players — the retention-critical first session. The owner called the start "very
   important" (02:50) and ruling 19 fixed L1–L31 in video order for exactly this reason.
2. **Copy risk there is lower** (§2): L1–L31 follow the older build, which v552 itself re-numbered. L32/L33 are the only
   v552 boards left at their number by the freeze (2 of 61).
3. **Tests.** L32 is the UI-test workhorse (GameFlowTests, GameG2UITests ×6, FailFlowTests, BoosterTests, UITestSupport,
   ShellUITests, AccessibilityIDTests: a Normal 3:00 board with blocked arrows); freezing through L33 keeps every UI test
   untouched (§9.4).
4. **Why not later.** Every level frozen past L33 leaves one more board at v552's number. Measured with the same algorithm
   (VERIFIED, `FREEZE_TO=50`): 18 boards stay at their v552 number instead of 3.
5. **Why L70 stays.** The Corner card; `curve.obstacles.firstLevel.corner = 70` is compiled into `CurveSpec.default` and
   drives the designed and endless generator — moving it changes the curve and every endless pin. Same for the other
   `firstLevel` values (7/11/21/31/33), all inside the frozen prefix.
6. **Why not L106–L150 (option B, not recommended).** Those boards are ours, so moving them buys no copy distance, and the
   pins say "designed L_n = Generator(n) byte for byte" (GeneratorTests sample + every-designed-level, LevelLibraryTests
   L106/L151, `DifficultyBands.designed` = the designed range's envelope against the targets of THEIR number,
   `testProviderNeverCrashes` "L144 = the last authored Hard"). Option B needs those tests to read designed.json by
   generation number instead — possible, but a bigger re-pin for no benefit.

## 4. The constraints (all enforced by the prototype; H10 by the existing validators)

| # | rule | why | how checked |
|---|---|---|---|
| H1 | **Teaching order**: a board with obstacle k only after k's teaching level (tape 7, box 11, pipe 21, elevator 31, door 33, corner 70) | owner item 12's own example | forbidden cell in the assignment; the validator's first-appearance check (`first appearances` unchanged) |
| H2 | **Practice after a card**: L34 holds a door board, L71 a corner board (as today) | the level after a card uses it | forbidden cell |
| H3 | **Tag cadence**: every slot keeps today's tag; a board moves only within its class (Normal↔Normal, Hard↔Hard, Super Hard↔Super Hard) | Hard at x4 / Super Hard at x9 from L34 (v552's cadence, `curve.tagByPosition`); rewards per slot (Hard 60, SH 100) and the rating ask after the L34 win stay on a Hard | per-class assignment; lvtool `consistency` checks `cadence[n % 10]` |
| H4 | **Timers travel with their board** (calibrated to it: bot keeps ≥ 20 %); **short-timer floor**: a ≤ 2:00 board never earlier than the original's first timer that short (2:00 at L59, 1:40 at L64); short timers ≥ 5 levels apart | no early time-pressure spike | forbidden cell + pairwise rule |
| H5 | **Anti-copy**: no board at its number in the original game (v552) or the older build; a v552 Normal board moves ≥ 3; no two boards consecutive in the original stay consecutive in the same order (seams 33\|34 and 105\|106 included) | item 12's purpose; ≥ 3 and the adjacency rule stop a "shift by one" that keeps the original sequence | forbidden cell + pairwise rule |
| H6 | **Bounded move**: Normal ≤ 10 levels; Hard/Super Hard ≤ 20 (two cadence steps), penalised past 10 | curve locality | forbidden cell + cost |
| H7 | **No near-identical neighbours**: look-alike = same grid W×H, same obstacle-kind set, units within 20 %; plus each generated stand-in and the board it was built to imitate ("twins"); gap ≥ 10 levels. Exact and near repeats (same cells, other heads, 8 symmetries): `repeats.py` = 0 | the player must not feel a board twice | pairwise rule; today's minimum gap is 15 (L40/L55) |
| H8 | **Variety**: no obstacle kind (and not "plain") on more than 3 consecutive zone levels | today's max is 2 (elevator 4 at L100–L103) | pairwise rule (3 = the tightest that is feasible, §8) |
| H9 | **Curve tolerance** (acceptance, table §7.1): the new rolling-9 curve may not deviate from the old by more than the OLD curve changes from one level to the next | "within tolerance" measured, not guessed | `within()` |
| H10 | **Content invariants**: same multiset of boards (every key but `level`), frozen slots byte-identical, sessions/unlocks/tutorials/curve unchanged; validator 0 errors + the L6 warning; repeats 0; negative controls 20/20 | a re-order must not edit a board | §8 checks |

## 5. The algorithm (deterministic, documented)

Input: design/levels.json after `build_levels.py assemble` (our research order with the dedup substitutes). Output: a
permutation `order[slot] = original slot`, committed as data (`design/level-order.json` in the build phase; the prototype
writes `design/publish/tools/level_reorder/level_order_candidate.json`, sha256 `b3690abc…`).

```
FREEZE_TO 33, ZONE_END 105, ANCHORS {70}, PRACTICE {34: door, 71: corner}
DMAX normal 10 / tagged 20, DMIN_V552 3, LOOKALIKE_GAP 10, TWIN_GAP 10, RUN_MAX 3, short timer <= 120 s gap 5
salt = fnv1a64('arrow-out/reorder/v1'); NOISE 0.30; ATTEMPTS 64; ROUNDS 12; MAX_PASSES 20
features per board (no solver run): units (tapes count once), waves = metrics.rounds, free = metrics.free_at_start,
  time pressure p = 1 - bot_time_left / timer, grid area, timer, obstacle-kind set, origin (capture path / _from)
dist(b, o) = |ln u_b/u_o| + |ln w_b/w_o| + 4|p_b - p_o| + 0.5|ln area_b/area_o| + 0.15|t_b - t_o|/30
           + 0.6 * (1 - Jaccard(kinds_b, kinds_o)) + 0.025|free_b - free_o| + (0.4 if tagged and moved > 10)
for k in 0 .. ATTEMPTS-1:
  rng = PathRandom(salt).fork('a' + k); noise[b][s] = rng.unit() for every zone cell (fixed order)
  stage 1: repeat up to ROUNDS:
     per tag class: C[b][s] = BIG if forbidden(b, s) else dist(b, board today at s) + NOISE*noise[b][s] + penalty[b][s]
                    order |= linear_sum_assignment(C)            (scipy; optimal, deterministic)
     v = pairwise violations (H4 gap, H5 adjacency, H7 gaps, H8 runs); if none: break
     penalty[order[s]][s] += 2 for each violating slot s
  stage 2: pairs = every same-class slot pair; for up to MAX_PASSES passes: shuffle(pairs, rng.fork('swaps'));
     for (s1, s2): swap if both cells allowed, J decreases and no pairwise violation (first improvement); stop when a pass
     improves nothing
  keep the attempt if within(TOL); winner = lowest J (ties: lowest k)
J = sum over L30-L109 of the squared relative rolling-9 deviations of units and waves + ((dp)/0.2)^2
    + 0.05 * ((dfree)/3)^2 + 20 * (max(0, maxdev_units - 0.08)^2 + max(0, maxdev_waves - 0.08)^2)
    + 5 * decade_dev^2 + 0.02 * sum(kind-count change per decade)^2
```

Everything draws from `pathrandom.PathRandom` (the bit-exact mirror of PathCore's), sorted inputs, scipy's exact
assignment: the same levels.json gives the same bytes (VERIFIED: two runs, identical order). The runtime never runs it —
the order is data, applied at content-build time, so no Swift port is needed.

**Search statistics (VERIFIED)**: 64 attempts → 7 inside tolerance, 48 outside, 9 whose pairwise rules stayed unresolved;
winner attempt a32, J = 1.281.

**Where it goes in the pipeline (build phase):** a new `design/tools/reorder_levels.py` = this prototype with three commands:
`plan` (search → `design/level-order.json`, which also records the sha256 of the level list it was computed on and all
parameters), `apply` (called by `build_levels.py assemble` right after `plan_slots`, before the unlock cards and metrics),
`check` (re-computes the plan and demands byte equality, and asserts H1–H10). A content change that alters any zone board
makes `check` fail until the plan is recomputed — the same discipline as `EXPECTED_REPEATS`.

## 6. The candidate permutation (VERIFIED output of `reorder_ref.py`; "from" = original slot − new slot)

Frozen and identical: L1–L33, L70, L106–L150. Zone slots whose board did not move: L35 (V2-L032), L72 (V2-L036), L83 and
L100 (our stand-ins) — none is a v552 board, so H5 does not force them.

| L | tag | board (origin) | timer | obstacles | units/waves | from |
|---|---|---|---|---|---|---|
| 34 | H | v552 L54 | 3:00 | door | 102/44 | +20 |
| 35 |  | V2-L032 | 3:00 | elevator | 40/17 | 0 |
| 36 |  | v552 L40 | 2:30 | - | 42/13 | +4 |
| 37 |  | v552 L47 | 3:00 | door+tape | 55/18 | +10 |
| 38 |  | v552 L42 | 3:00 | pipe | 45/23 | +4 |
| 39 | SH | v552 L49 | 2:30 | door+pipe | 69/30 | +10 |
| 40 |  | v552 L43 | 3:00 | door | 59/19 | +3 |
| 41 |  | v552 L38 | 3:00 | pipe+tape | 39/15 | -3 |
| 42 |  | v552 L48 | 2:30 | pipe | 47/20 | +6 |
| 43 |  | v552 L36 | 3:00 | pipe | 31/14 | -7 |
| 44 | H | v552 L34 | 3:30 | door | 116/42 | -10 |
| 45 |  | v552 L41 | 2:30 | door+pipe | 48/19 | -4 |
| 46 |  | V2-L035 | 3:00 | elevator+pipe | 96/44 | +6 |
| 47 |  | v552 L37 | 3:00 | door | 49/23 | -10 |
| 48 |  | V2-L034 | 3:00 | tape | 32/13 | +3 |
| 49 | SH | v552 L39 | 3:00 | - | 102/38 | -10 |
| 50 |  | v552 L60 | 3:00 | - | 34/7 | +10 |
| 51 |  | v552 L55 | 2:30 | - | 48/22 | +4 |
| 52 |  | V2-L033 | 2:30 | box+elevator | 53/22 | -7 |
| 53 |  | v552 L56 | 3:00 | box+pipe | 60/23 | +3 |
| 54 | H | v552 L44 | 3:00 | pipe+tape | 83/33 | -10 |
| 55 |  | v552 L46 | 3:00 | door | 102/37 | -9 |
| 56 |  | v552 L63 | 2:30 | door+pipe | 60/25 | +7 |
| 57 |  | v552 L50 | 3:00 | box | 16/9 | -7 |
| 58 |  | v552 L62 | 3:00 | box+door+tape | 72/30 | +4 |
| 59 | SH | v552 L69 | 2:00 | door+pipe | 99/36 | +10 |
| 60 |  | v552 L57 | 3:00 | box+tape | 38/13 | -3 |
| 61 |  | v552 L66 | 2:30 | door | 25/12 | +5 |
| 62 |  | v552 L65 | 3:00 | box+door | 65/21 | +3 |
| 63 |  | v552 L53 | 2:30 | box+door | 61/24 | -10 |
| 64 | H | v552 L84 | 2:00 | - | 87/44 | +20 |
| 65 |  | v552 L68 | 3:00 | pipe+tape | 50/19 | +3 |
| 66 |  | v552 L61 | 2:30 | tape | 35/9 | -5 |
| 67 |  | v552 L58 | 2:30 | door | 61/26 | -9 |
| 68 |  | V2-L038 | 2:30 | pipe | 34/12 | +7 |
| 69 | SH | v552 L59 | 2:00 | - | 85/34 | -10 |
| 70 |  | v552 L70 (Corner card, anchor) | 3:00 | corner | 22/6 | 0 |
| 71 |  | v552 L80 | 3:00 | corner | 42/18 | +9 |
| 72 |  | V2-L036 | 3:00 | - | 36/14 | 0 |
| 73 |  | v552 L76 | 3:00 | corner | 56/18 | +3 |
| 74 | H | v552 L64 | 1:40 | - | 75/33 | -10 |
| 75 |  | v552 L78 | 3:00 | - | 37/15 | +3 |
| 76 |  | v552 L82 | 2:30 | corner+pipe | 60/27 | +6 |
| 77 |  | v552 L67 | 2:30 | box | 37/16 | -10 |
| 78 |  | V2-L037 | 3:00 | box | 55/23 | -1 |
| 79 | SH | v552 L99 | 3:00 | - | 85/25 | +20 |
| 80 |  | v552 L71 | 3:00 | corner | 25/11 | -9 |
| 81 |  | stand-in (was L86; twin of v552 L66) | 2:30 | door | 33/13 | +5 |
| 82 |  | v552 L73 | 2:30 | box+corner | 61/19 | -9 |
| 83 |  | stand-in (L83; twin of v552 L63) | 2:30 | door+pipe | 71/25 | 0 |
| 84 | H | v552 L74 | 3:00 | - | 113/43 | -10 |
| 85 |  | v552 L91 | 2:30 | corner | 38/18 | +6 |
| 86 |  | stand-in (was L81; twin of v552 L61) | 2:30 | tape | 34/9 | -5 |
| 87 |  | v552 L92 | 2:30 | box+pipe | 40/19 | +5 |
| 88 |  | v552 L98 | 2:30 | door+tape | 74/31 | +10 |
| 89 | SH | v552 L79 | 3:00 | corner | 74/28 | -10 |
| 90 |  | v552 L95 | 2:30 | - | 41/14 | +5 |
| 91 |  | v552 L88 | 2:30 | pipe+tape | 68/21 | -3 |
| 92 |  | v552 L87 | 3:00 | box | 43/23 | -5 |
| 93 |  | v552 L85 | 2:30 | corner+tape | 45/14 | -8 |
| 94 | H | v552 L104 | 3:00 | - | 83/34 | +10 |
| 95 |  | v552 L90 | 2:30 | - | 33/14 | -5 |
| 96 |  | v552 L93 | 2:30 | corner+door | 64/19 | -3 |
| 97 |  | v552 L102 | 2:30 | corner+elevator | 80/31 | +5 |
| 98 |  | v552 L105 | 3:00 | pipe | 34/16 | +7 |
| 99 | SH | v552 L89 | 2:30 | corner+door | 99/36 | -10 |
| 100 |  | stand-in (L100; twin of video L31) | 3:00 | elevator | 39/12 | 0 |
| 101 |  | stand-in (was L103; twin of V2-L033) | 3:00 | box+elevator | 49/18 | +2 |
| 102 |  | v552 L97 | 2:30 | box+corner | 48/25 | -5 |
| 103 |  | v552 L96 | 2:30 | pipe | 32/12 | -7 |
| 104 | H | v552 L94 | 2:30 | - | 104/38 | -10 |
| 105 |  | stand-in (was L101; twin of V2-L032) | 3:00 | elevator | 35/14 | -4 |

Move histogram (VERIFIED): 1:1, 2:1, 3:11, 4:6, 5:10, 6:4, 7:7, 8:1, 9:5, 10:18, 20:3 (the 1- and 2-level moves are
non-v552 boards). Tagged boards: Hard 34←54←44←34 (3-cycle), 64←84←74←64 (3-cycle), 94↔104; Super Hard 39↔49, 59↔69,
79←99←89←79 (3-cycle).

## 7. Its curve against the old one (VERIFIED, `analyse.py`)

### 7.1 Tolerance and result (rolling mean over 9 levels, L30–L109; decades L30–L105)

The tolerance is the ORIGINAL curve's own jitter: on today's rolling-9 curve over L34–L105 the change from one level to the
next is at most 18.1 % (mean 5.6 %) in units, 18.8 % (6.3 %) in waves, 0.047 (0.013) in time pressure; decade means move by 7 %
on average between consecutive decades (max 14 %). A re-order inside these limits changes the curve less than the original
changes itself from one level to the next.

| measure | tolerance | candidate |
|---|---|---|
| units, max relative deviation | 0.12 | **0.102** |
| units, mean relative deviation | 0.056 | **0.037** |
| waves, max / mean | 0.12 / 0.063 | **0.104 / 0.033** |
| time pressure (1 − bot time left / timer), max / mean absolute | 0.035 / 0.013 | **0.027 / 0.009** |
| timer, max relative | 0.10 | **0.072** |
| free at start, max absolute | 3.5 arrows | **1.78** |
| decade means (units, waves), max relative | 0.08 | **0.061** |
| obstacle-kind level count per decade, max change | ±2 | **2** |
| correlation old vs new rolling-9 (L30–L110) | reported | units 0.875, waves 0.927, pressure 0.884, timer 0.762 |

### 7.2 Per decade (old → new)

| slots | units | waves | pressure | mean timer s | obstacle levels door/pipe/box/tape/elevator/corner |
|---|---|---|---|---|---|
| L30–L39 | 52.8 → 50.4 | 20.3 → 19.9 | 0.178 → 0.181 | 183 → 174 | 3/2/0/2/2/0 → 4/2/0/2/2/0 |
| L40–L49 | 60.3 → 61.9 | 23.4 → 24.7 | 0.225 → 0.213 | 165 → 177 | 5/5/1/2/1/0 → 4/5/0/2/1/0 |
| L50–L59 | 59.9 → 62.7 | 25.2 → 24.4 | 0.228 → 0.245 | 165 → 165 | 3/2/4/2/1/0 → 4/4/4/2/1/0 |
| L60–L69 | 55.2 → 54.1 | 20.8 → 21.4 | 0.239 → 0.228 | 154 → 153 | 5/3/3/3/0/0 → 4/2/3/3/0/0 |
| L70–L79 | 51.3 → 50.5 | 18.9 → 19.5 | 0.177 → 0.195 | 174 → 166 | 0/1/2/0/0/5 → 0/1/2/0/0/4 |
| L80–L89 | 58.2 → 56.3 | 23.0 → 21.6 | 0.239 → 0.214 | 153 → 159 | 3/3/1/3/0/4 → 3/2/2/2/0/4 |
| L90–L99 | 55.9 → 59.0 | 21.5 → 22.2 | 0.222 → 0.229 | 153 → 159 | 2/2/2/1/0/3 → 2/2/1/2/1/4 |
| L100–L109 | 53.6 → 52.3 | 20.3 → 19.7 | 0.205 → 0.207 | 165 → 159 | 0/2/3/0/5/1 → 0/2/4/0/4/1 |
| L110–L150 | unchanged | | | | |

### 7.3 Rolling-9 samples (units / waves / pressure, old → new)

| L | units | waves | pressure |
|---|---|---|---|
| 35 | 55.9 → 53.2 | 21.8 → 21.3 | 0.188 → 0.192 |
| 40 | 55.3 → 55.9 | 21.9 → 21.6 | 0.195 → 0.198 |
| 45 | 62.3 → 62.2 | 24.6 → 25.3 | 0.231 → 0.214 |
| 50 | 64.4 → 61.9 | 26.6 → 25.0 | 0.235 → 0.216 |
| 55 | 64.8 → 65.9 | 27.0 → 26.3 | 0.247 → 0.259 |
| 60 | 57.8 → 58.1 | 22.2 → 23.8 | 0.245 → 0.249 |
| 65 | 57.6 → 55.9 | 22.3 → 22.3 | 0.253 → 0.239 |
| 70 | 52.0 → 49.6 | 19.6 → 18.9 | 0.206 → 0.214 |
| 75 | 54.6 → 53.7 | 20.3 → 21.0 | 0.189 → 0.208 |
| 80 | 57.3 → 60.0 | 23.0 → 22.4 | 0.220 → 0.221 |
| 85 | 60.0 → 59.8 | 23.6 → 22.8 | 0.250 → 0.229 |
| 90 | 58.0 → 55.8 | 22.3 → 21.4 | 0.234 → 0.210 |
| 95 | 58.4 → 61.0 | 22.3 → 23.1 | 0.232 → 0.236 |
| 100 | 58.3 → 61.0 | 22.4 → 23.0 | 0.213 → 0.239 |
| 105 | 55.2 → 53.8 | 21.2 → 20.6 | 0.213 → 0.216 |

Worst units spots: L73 (55.7 → 50.0), L72 (55.1 → 49.7), L59 (54.8 → 59.8) — all under the 12 % limit.

### 7.4 Hard / Super Hard slots and timers

| slot | tag | today | candidate |
|---|---|---|---|
| L34 | Hard | v552 L34 (3:30, 116/42) | v552 L54 (3:00, 102/44) |
| L39 | Super Hard | v552 L39 (3:00, 102/38) | v552 L49 (2:30, 69/30) |
| L44 | Hard | v552 L44 (3:00, 83/33) | v552 L34 (3:30, 116/42) |
| L49 | Super Hard | v552 L49 (2:30, 69/30) | v552 L39 (3:00, 102/38) |
| L54 | Hard | v552 L54 (3:00, 102/44) | v552 L44 (3:00, 83/33) |
| L59 | Super Hard | v552 L59 (2:00, 85/34) | v552 L69 (2:00, 99/36) |
| L64 | Hard | v552 L64 (1:40, 75/33) | v552 L84 (2:00, 87/44) |
| L69 | Super Hard | v552 L69 (2:00, 99/36) | v552 L59 (2:00, 85/34) |
| L74 | Hard | v552 L74 (3:00, 113/43) | v552 L64 (1:40, 75/33) |
| L79 | Super Hard | v552 L79 (3:00, 74/28) | v552 L99 (3:00, 85/25) |
| L84 | Hard | v552 L84 (2:00, 87/44) | v552 L74 (3:00, 113/43) |
| L89 | Super Hard | v552 L89 (2:30, 99/36) | v552 L79 (3:00, 74/28) |
| L94 | Hard | v552 L94 (2:30, 104/38) | v552 L104 (3:00, 83/34) |
| L99 | Super Hard | v552 L99 (3:00, 85/25) | v552 L89 (2:30, 99/36) |
| L104 | Hard | v552 L104 (3:00, 83/34) | v552 L94 (2:30, 104/38) |

Tags per slot: identical (VERIFIED). Timers ≤ 2:00: today L59, L64, L69, L84 (+ designed L109, L124) → candidate L59, L64,
L69, **L74** (+ L109, L124): the first 2:00 stays at L59 and the first 1:40 moves LATER (L64 → L74). The first 2:30 timer moves
from L40 to **L36** (the floor protects only ≤ 2:00; §11 D5).

## 8. Validation of the candidate (VERIFIED on a scratch copy; design/ untouched)

`python3 design/publish/tools/level_reorder/candidate.py <scratch>/candidate_levels.json` writes today's boards in the
candidate order (only `level` differs; sha256 `8ace3d3a…`, same size as today's file, 957,459 bytes). Then, with copies of the
existing tools (so `design/tools/work/validate_report.json` was not overwritten):

| check | result |
|---|---|
| `validate_levels.py` (every rule, incl. the 40 seeded random play orders per pipe/elevator/corner level, which are seeded by the level NUMBER `1000 + L`, so every moved level was re-checked on new seeds) | **150 levels, 0 errors, 1 warning (L6 cols 27, as today); first appearances linked 7, box 11, pipe 21, elevator 31, door 33, corner 70**; 11.3 s |
| `repeats.py` | **0 repeats, 0 near repeats** |
| same boards | the multiset of level objects without `level` is identical; L1–L33, L70, L106–L150 byte-identical; `curve`, `unlocks`, `sessions`, `tutorials` identical; tags per slot identical |
| `validator_selftest.py` with its targets resolved through the order (3-line change: `lv(doc, n)` → `doc['levels'][slot_of[n] - 1]`) | **20/20 CAUGHT**; the messages name the boards' new slots, e.g. "L37: 1 keys for 2 doors" (v552 L47), "L59: pipe p0 covers visible arrow 13" (v552 L69), "L81 repeats L61", "L134 repeats L104" (the mirrored v552 L94), "L105 repeats L35", "L97: elevator e0 platform …" (v552 L102) |
| look-alike/twin pairs (24) | minimum gap 15 today, 15 in the candidate |
| runs (L34–L105) | door 3 (L61–63), pipe 3 (L41–43), plain 3 (L49–51), others ≤ 2; today: 2, 2, 2 (elevator 4 → 2). `RUN_MAX=2` was tried: no attempt satisfies every other rule (VERIFIED: 0 of 64) |
| determinism | two runs → byte-identical order |

NOT run in this phase (the machine is being timed; no swift/xcodebuild): the Swift `Validator` (randomOrders 8, game rules)
and `HeadlessDriver` on the moved levels (PathCore C4Full + app LevelsBundleTests), lvtool's `check`/`consistency`/
self-tests, the bundle regeneration. The overlay proofs and bot replays need NOT be re-run: every board is byte-identical
(H10), only its number changes — but the tools that locate research files must learn the new numbers (§9.3).

## 9. Exactly what must be re-pinned (build phase) and why that is not weakening

Principle: a re-pin is allowed when the source of truth changed and the assertion keeps its meaning and strength. Here the
content change is a pure renumbering, so every assertion either (a) is untouched, (b) is a data pin of the source of truth
that is refreshed, or (c) names a board by NUMBER and must follow the SAME board to its new number. No expected value is
relaxed, no tolerance widened, no test removed. Board lookup: a test helper `C4Fixtures.board(v552: n)` = the level whose
`capture` names `L0nn` (LevelSpec has `capture`), or the `slot` written into the fixture by its generator.

Board → new slot (candidate): L34→44, L35→35, L39→49, L42→38, L44→54, L47→37, L48→42, L51→48, L54→34, L59→69, L62→58,
L63→56, L64→74, L69→59, L73→82, L74→84, L75→68, L76→73, L79→89, L80→71, L82→76, L86→81, L89→99, L93→96, L98→88, L100→100,
L102→97, L103→101.

### 9.1 PathCore fixtures (Packages/PathCore/Tests/Fixtures)

| fixture | change | why not weakening |
|---|---|---|
| `content/levels.json` + `MANIFEST.txt` | `design/tools/pin_fixtures.py` | the hermetic copy of design/levels.json; `--check` enforces it |
| `c4b_bot_replay.json` | `content_sha256` changes; each row gains `slot` (v552 69, 73, 76, 79, 80, 82 → 59, 82, 73, 89, 71, 76) found through `capture` by `Tests/tools/c4b_bot_replay.py` | same log, same taps, same boards, same verdicts; only the lookup key changes |
| `c4_negative_controls.json` | regenerated by `Tests/tools/c4_reference.py negatives` after `validator_selftest.py` resolves its targets through the order | the same 20 mutations on the same boards; the Python messages now carry the new numbers; still 20/20 caught (§8) |
| **unchanged** | `content/designed.json`, `c4_runtime_reference.json` (curve sha only), `c4_reference_extras.json`, `c4b_corner_layouts.json`, `c2_*`, `research/`, `soc_*` | the curve, the designed range and the research inputs do not change |

### 9.2 Swift tests

| test | today | change | category |
|---|---|---|---|
| BotReplayTests.testPhoneBotWinningTapsExitUnderTheGameRules | `C4Fixtures.level(n)` with n = the log's v552 number | `C4Fixtures.level(lv["slot"])`; keep `[69, 73, 76, 79, 80, 82]` as the LOG's levels | MUST (would replay taps on the wrong board) |
| RulesTests.testLockedDoorBlocksBeforeThePipeUnderIt_L069, testL069IsTheSameWithThePipesListedFirst | `C4Fixtures.level(69)` | the v552-L69 board (candidate slot 59) | MUST (new L69 has no door/pipe: `XCTUnwrap` fails) |
| ValidatorTests.testSpriteCheck | `C4Fixtures.level(47)` "doors, keys, tapes" | the v552-L47 board (slot 37) | MUST (new L47 has no tape) |
| ValidatorTests.testNegativeControlsAreCaughtWithThePythonMessages | reads the fixture (swaps each mutated level in at `n - 1`; the fixture's `levels` then carry the new slots) | nothing (fixture regenerated) | data |
| ValidatorTests.testSampleOfShippedLevelsIsValidUnderBothRuleBooks | `[…, 34, 47, 62, 63, 69, 75, 76, 86, 89, 93, 98, 100, 102, …]` with a comment naming each board's feature | map through the order (44, 37, 58, 56, 59, 68, 73, 81, 99, 96, 88, 100, 97) | coverage (passes either way; the mapping keeps the SAME features covered) |
| SolverTests.testSearchEqualsGreedyOnMonotoneBoards, testBothRuleBooksAgreeOnTheSample | sample numbers | map through the order | coverage |
| LevelLibraryTests.testSampleOfAuthoredLevelsIsWonByTheDriver | `[…, 44, 59, 63, 64, 69, 70, 79, 100, 150]` | map through the order | coverage |
| **unchanged** | GeneratorTests (designed range + curve), EndlessGateTests / EndlessFixtures (curve), LevelLibraryTests byte-for-byte / `unlocks [7, 11, 21, 31, 33, 70]` / `authored(65) == level(65)` / L106, L144, L150, L151, ValidatorTests first appearances + the L6 warning + C4FullValidatorTests, HeadlessTests (C2 research fixtures), HintPolicyTests (whole set), app LevelsBundleTests (first appearances, L19/L25/L29 tags, bundle == design/levels.json), BoardGeometryTests (synthetic sizes), every UITest | — | — |

UI tests (VERIFIED by grep): the zone numbers they use — 34, 35, 40, 45, 50, 55, 60, 62 — are the PLAYER's level for meta
screens (home, shop, leaderboards, events, the Weekly gate at L50, popups forced by `-pc.popup`). The only content they need is
"L34 is Hard" (win:hard ribbon, reward 60), kept by H3. The only autoplay/tap-through tests use L1–L7 and L32 (frozen).
Lab boards (`App/Board/LabBoards/lab_L0xx.json`) are separate copies and are not affected.

### 9.3 Tools that find research files or boards by level number (build phase)

| tool | today | change |
|---|---|---|
| `design/tools/validator_selftest.py` | `lv(doc, n)` by number | through the order (prototype: 3 lines, §8) |
| `Packages/PathCore/Tests/tools/c4b_bot_replay.py` | `lv[L]` | find by capture; write `slot` |
| `tools/levels/render.py` (`SUBST` by slot, research by `b['level']`), `replay_bundle.py`, `design/tools/overlay_recast.py` (`L%03d-open1.json % b['level']`) | by our number | research number from `capture` / `_from` |
| `tools/levels/lvtool` `main.swift` + `SelftestL2.swift` (mutations on idx 40, 45, 47, 50, 58, 59, 64, 74, 100) and `Diff.swift` (research lookup; substitute slots 35/45/51/52) | by our number | through the order / by capture; re-run until every mutation is CAUGHT (note: some targets are already stale since the recast — e.g. the L64 "box counter" mutation targets a plain board — INFERRED from source, check when re-targeting) |
| `design/tools/levels_report.py` | origin inferred per slot range | group by origin; add an "order" table to LEVELS.md |
| `design/LEVELS.md` | prose names boards by number (L62 poking key, L69 pipes under doors, L89 corner under a door, …) | say "v552 L69 (ships at L59)" |

### 9.4 The app bundle

`tools/levels/lv.sh bundle design/levels.json App/Resources/Levels`: the 67 moved `level_00NN.json` files change;
`sessions.json`, `unlocks.json`, `tutorials.json`, `curve.json` are byte-identical. No App/ or PathCore Sources code changes.

## 10. Player-facing effects

- No store players exist yet. The owner's phone build: `PlayerState` stores the next level NUMBER, counters
  (`attempts[level]`, stats) and `activeAttempt {session, levels, attemptIndex, startedAt, stage}` — no board snapshot
  (VERIFIED, PlayerState.swift). After installing over, the owner simply meets a different board at the same number; no
  migration is needed.
- Event/meta unlocks (Streak Race 30, Claw 33, Sky Jump 40, Weekly 50, Rocket Race 55, rating after L34, FTUE chain to L7)
  are level NUMBERS and do not move.

## 11. Decisions for the owner / orchestrator

- **D1 (recommended)**: zone L34–L105, freeze L1–L33 + L70, keep L106+. Alternative: start later (every frozen level leaves one
  more board at the original's number: 18 at `FREEZE_TO=50`).
- **D2**: corner practice at L71. The only gentle corner board (v552 L71, 25 units) may not stay at L71 (H5), so the candidate
  uses v552 L80 (42 units, 18 waves; today's L71 has 25/11). Accept, or anchor L71 as well (+1 copied number), or take our
  designed L112 (16 units, one corner) — which requires option B.
- **D3 (strongly recommended, separate change)**: strip provenance from what ships. VERIFIED today: 72 bundled level files
  carry `research/shots/NNN-L0xx-start.png` (the original's level number), 38 carry `research/video-frames/...`, 13 mention
  "phone", 4 files (curve.json, level_0072/0075/0077.json) mention "v552", and `CurveSpec.swift` compiles the curve `_about`
  ("…obstacle mix of v552 L40-L105…") into the binary. Proposal: the bundle writer drops `_*` keys and `capture` in a
  publish form (the Python/Swift validators then must not demand `capture` in the bundle), and the curve `_about` is
  neutralised — this last one changes the curve's sha, i.e. `EndlessFixtures.pinnedCurveSHA` and
  `c4_runtime_reference.json`'s `curve_sha256` (a text-only re-pin; the curve numbers are unchanged).
- **D4**: the boards themselves remain the original's recorded boards; re-ordering removes the number-for-number identity,
  not the boards. If more distance is wanted (beyond item 12): mirror/rotate recorded boards (the rules are symmetric; the
  validator re-proves them; `repeats.py` would still call them the same board because it is symmetry-aware — by design) or
  replace some with generated boards. Owner call.
- **D5**: the timer floor protects only ≤ 2:00; the first 2:30 moves from L40 to L36. Tighten to all timers only by
  accepting fewer valid orders (a full timer floor was infeasible for the Super Hard class: slot 39 would need a 3:00 SH board
  from ≥ 40 levels away).
- **D6**: variety allows runs of 3 (three places); 2 was infeasible with the other rules.
- **D7**: option B (also permute L106–L150): not recommended (§3.6).

## 12. What needs the phone

Nothing for the plan or the build of the re-order. After the build: a feel check by the owner on the iPhone — play the new
L34–L45 (first Hard/Super Hard after the Door card) and L70–L75 (Corner card + practice) — optional, D1-style. Tell the owner
that the level they are on will show a different board after the update.

## 13. Reproduce

```
python3 design/publish/tools/level_reorder/reorder_ref.py            # the search -> level_order_candidate.json (~25 s)
python3 design/publish/tools/level_reorder/analyse.py                # the numbers of §6-§8
python3 design/publish/tools/level_reorder/candidate.py /tmp/x/c.json  # the candidate levels.json (then validate_levels.py /
                                                                      # repeats.py on it; validate_levels.py writes its report
                                                                      # into design/tools/work/, so run a copy of the tools)
```
Inputs: design/levels.json (sha256 `63e41001…`), design/tools/pathrandom.py; Python 3 + numpy + scipy (`linear_sum_assignment`).
The order is only valid for that levels.json: the build-phase tool records the input sha and refuses a stale plan.

---

## 14. Build-phase tools (PLAN-P T8 LV-TOOLS, 2026-09-28): built, proven on scratch, NOT applied

Wave 0 fence: nothing under App/, Packages/, Tests/, UITests/ or project.yml was written; the real design/levels.json, bundle,
fixtures and pins are untouched (design/level-order.json does not exist in the real tree). B0 applies. Proof harness:
`design/publish/tools/level_reorder/t8_prove.py {setup,fast,slow,samples}` on three scratch trees under build/p/T8/scratch
(`orig` = today's content + today's tools, `cur` = today's content + T8 tools, `new` = re-ordered + re-pinned + re-bundled +
stripped); evidence and logs in build/p/T8/evidence/ (results-*.json).

### 14.1 The tools

| file | state | what |
|---|---|---|
| `design/tools/level_order.py` | new | board identity: `rslot` (research slot) from the board's own capture / `_from`, `slot_map` (bijection, asserted), `resolver`, `with_provenance` (a bundled board joined to its design/levels.json record; gameplay must match), `plan_state` |
| `design/tools/reorder_levels.py` | new | `plan` (§5's algorithm verbatim; writes design/level-order.json with the input AND output sha256), `apply` (**sha guard**: input -> permuted and re-hashed to the plan's output; output -> "already applied"; anything else -> exit 2, nothing written), `check` (re-search byte-equal + H1-H10) |
| `design/tools/build_levels.py` | edited | `doc_text()` split out of `write_doc`; `assemble` calls `reorder_levels.apply_planned()` — no plan: today's bytes; stale plan: refused before writing |
| `design/tools/strip_provenance.py` | new | `scan` (hit classes with JSON paths; text + binary + file names; works on a built .app), `publish` (the shipped set, stripped), `strip-levels` / `strip-json` (in place), `bundle` / `check-bundle` (Python mirror of lvtool's bundle writer, byte-exact on today's 154 files) |
| `design/tools/validator_selftest.py`, `overlay_recast.py`, `levels_report.py` | re-pointed in place | targets / research files by research slot; output byte-identical on today's content |
| `tools/levels/render.py`, `replay_bundle.py`, `Packages/PathCore/Tests/tools/c4b_bot_replay.py`, `c4_reference.py` | **staged** (fenced paths) | `design/publish/tools/level_reorder/staged/` + `patches/` + README (install after checking the base sha). `c4_reference.py negatives` is a 7th number-lookup tool (its own copy of the 20 mutations) |

A number no longer names a board after the re-order, so every tool names boards by their RESEARCH SLOT (v552's number for a
phone board, the video number for L1-L31, the phone slot a V2 board / stand-in substitutes), read from provenance — never
from position. VERIFIED: on today's file every rslot = its level (identity); on the re-ordered file the provenance lookup
equals the plan's order for all 150 slots and reproduces the board -> slot list of §9.

### 14.2 Proof (VERIFIED on scratch; build/p/T8/evidence)

| check | result |
|---|---|
| plan twice | byte-identical (5,312 bytes, sha256 `2eba197b…`); order == `level_order_candidate.json` (a32, J 1.2809; 7 inside tolerance, 48 outside, 9 unresolved) |
| apply | design/levels.json -> sha256 `8ace3d3a…` (= §8); again -> no-op; a copy with one timer changed -> exit 2, nothing written |
| assemble hook | no plan -> `63e41001…` (today, byte for byte); plan -> `8ace3d3a…` (= apply); a plan with a wrong input sha -> refused, file untouched |
| check | the search reproduces the plan byte for byte; H1-H10 hold (units 0.102, waves 0.104, pressure 0.027 …) |
| rule negative controls on `verify()` | 9/9 caught (H1 corner before L70, H2 L34 without a door, H3 tag, H4 the 1:40 board early, H5 own number, H6 move > 10, H10 frozen slot, H10 not a permutation, the copied order itself). H9 (curve) is non-vacuous by the search itself: 48 of 64 attempts rejected |
| validator on the re-ordered file | 150 levels, 0 errors, 1 warning (`WARN L6: cols 27 > 26 …`), first appearances 7/11/21/31/33/70 (= today) |
| repeats.py | 0 repeats, 0 near repeats |
| negative controls (validator_selftest.py, re-pointed) | re-ordered: **20/20 CAUGHT**, the messages name the new slots exactly as §8 said ("L37: 1 keys for 2 doors", "L59: pipe p0 covers visible arrow 13", "L81 repeats L61", "L134 repeats L104", "L105 repeats L35", "L97: elevator e0 …"); today: stdout byte-identical to the old tool (20/20) |
| samples on moved boards (staged render.py on the STRIPPED bundle vs today's tools) | v552 L69 at L59 and v552 L80 at L71: IoU / tol1 / registration identical (0.9994, 0.9915); door reveals of v552 L47 at L37 identical (2 doors); elevator of v552 L102 at L97 identical (0.9989); video replay of V2-L035 at L46 = at L52 (89 taps, 96 consistent, 0 inconsistent). In-place overlay_recast.py + TODAY's render.py (the real tree until B0) = before (L102, L62) and its research-file lookup equals the old slot map for every recorded/video board. No video-board overlay could run: every research/video-frames capture is absent from disk (38 files; pre-existing, both tools fail alike) |
| c4_reference negatives (staged) | 20/20 caught; `levels` = slots (L47->37, L62->58, L69->59, L86->81, L101->105, L93->96, L102->97); today: fixture byte-identical to the pinned one with old AND new tool |
| c4b_bot_replay (staged) | same taps and verdicts as the pinned fixture; `slot` 69->59, 73->82, 76->73, 79->89, 80->71, 82->76 (= §9.1); today: pinned + `slot` = level |
| levels_report | today: LEVELS.md byte-identical (old vs new tool); re-ordered: range tables unchanged (grouped by origin), order section 67 rows (= §6) |
| bundle | Python mirror == today's App/Resources/Levels (154/154 files, byte); re-ordered bundle: exactly the 67 moved level files change |
| strip | stripped bundle == publish form of the mirror (byte); every stripped level joins back to design/levels.json (gameplay equal); Tuning: parsed files differ only by "_" keys + worldModel |
| scan of the stripped shipped set | **0 provenance hits**; the literal regex `research/\|phone\|v552\|L0\d\d` finds 2 = "iphone" in the username brand blocklists (Social/block_names.txt, social_names.json: functional, not provenance); scanner negative controls 5/5 caught |

### 14.3 Provenance hit classes (VERIFIED: sources today, and the compiled Release-sim app build/v3/app/ArrowOut.app 2026-09-27)

| class | where | today | action (tool) | after |
|---|---|---|---|---|
| research path + level name in `capture` | Levels/level_NNNN.json | 99 files (94 match L0nn; L32, L33, L102, L104, L105 are named "L32"/"L102", which only the wider `level-ref` class `L\d{2,3}` sees) | drop `capture` | 0 (both classes, text files) |
| recast notes `_from` (research/, "the phone's", v552, L0nn) | 13 level files (substitutes, spares, stand-ins) | 13 | drop `_` keys | 0 |
| curve `_about` ("v552 L40-L105") | Levels/curve.json | 1 | drop `_` keys | 0 |
| tuning comments (`_about`, `_doc`, `_sources`, `_pending`, `_corrections`, `_owner`, `_s3`: research/, phone, v552) | Tuning/{audio,board,game,rules,social,ui}.json | 20 hits | drop `_` keys (every reader skips them) | 0 |
| `"worldModel": "v552"` | Tuning/social.json | 1 | rewrite "shipped" (`SocialWorldModel.named` maps every name but "reference" to the shipped model) | 0 |
| xcstrings `comment` (phone, v552, L70 notes) | Localizable.xcstrings | 4 | none: compiled away (the .app's .lproj: 0 hits) | 0 |
| lab boards (file names lab_L0nn / labb_L0nn, `capture`, `shot`, `reveals`) | App/Board/LabBoards -> .app ROOT, Release too | 24 files | exclude from Release (project.yml, B0) | excluded |
| brand stems (grandgames, mazeout, arrowjam) + "iphone" | Social/block_names.txt, social_names.json | 6 + 2 | none (functional); G4c: ship hashed (B0) | reported |
| absolute paths `…/apps/mazeout/…` (object files + `#filePath` literals) | ArrowOut binary | 986 | B0/G4c: build settings / `#fileID` / a neutral checkout path; check the DEVICE archive | — |
| Swift symbols + literals: `v552Weekly`, `v552Streak`, `SocialSkySpec.v552`, `SocialNameStyle.v552`, `SocialWorldModel(name: "v552")`, `LabBoards.PhoneLevel`, Log text "v552 plays nothing", the CurveSpec.default `_about`, lab names "L039,L044…" | ArrowOut binary | v552 146, phone-word 454, L0nn 63 | B0/B2 source renames | — |
| CodeResources lists lab_L0nn.json | _CodeSignature | 48 | goes with the lab-board exclusion | — |
| iphonesimulator / "OnPhone" | Info.plist, binary | — | not provenance (platform strings; a sim build) | — |

Not in the regex and left as is: `"source": "recorded" / "video"` in the shipped level files (read only by the validators).

### 14.4 What B0 still has to do (fenced or Swift; T8 did not)

1. Install the 4 staged files (base sha check, staged/README.md); `reorder_levels.py plan` + `apply` + `check`; `pin_fixtures.py`;
   `c4_reference.py negatives`; `c4b_bot_replay.py`.
2. `lv.sh bundle`, then `strip_provenance.py check-bundle` (mirror == lvtool, else stop) -> `strip-levels` -> `check-bundle --publish`.
3. Swift tests that name a board by number (§9.2): BotReplayTests (`C4Fixtures.level(lv["slot"])`), RulesTests L069 x2 (slot 59),
   ValidatorTests.testSpriteCheck L47 (slot 37), sample lists mapped (§9.2).
4. Publish-form requirement changes (ruling 39 OD8, log in PLAN.md): LevelLibraryTests.testTheAppBundleFolderIsABundleOfLevelsJSON
   (the folder is now publish(encoded): a Swift publish form or a comparison without `capture`/`_` keys), `lvtool bundle --check`,
   `pclevels validate App/Resources/Levels` ("no capture for a recorded level" belongs to design/levels.json, not the bundle),
   tools/levels/bundle_check.py (`capture`/`_from` "only in source").
5. Curve `_about`: neutralise it in CurveSpec.default too (a compiled literal), re-pin EndlessFixtures.pinnedCurveSHA and
   c4_runtime_reference.json `curve_sha256` (text only). LevelLibraryTests `lib.curve == .default` compares the pinned doc's
   curve, so it moves with the same change.
6. Tuning: strip in source (`strip-json`) or in a Release build phase; the worldModel rewrite needs SocialConfig's default,
   SocialNamesTests:170 and the model name changed with it (B2 if the name feeds anything).
7. lvtool (Swift): main.swift + SelftestL2.swift mutation targets and Diff.swift's research lookup / substitute slots still go by
   number (§9.3) — not re-pointed (a Swift compile is heavy and fenced).
8. LabBoards out of the Release bundle; blocklist brand stems hashed; binary strings of §14.3 (G4c on the device archive).
9. design/LEVELS.md: add `<!-- BEGIN:order -->` / `<!-- END:order -->` for the generated order table; prose names boards by
   research number ("v552 L69 (ships at L59)").

Pre-existing bug fixed on the way: render.py and replay_bundle.py still carried the pre-recast slot map {62: 36, 63: 38, 64: 37}
(the spares moved to L72/L75/L77 in the recast), so standalone they looked up the wrong research file for those levels; the
provenance lookup removes the map.
