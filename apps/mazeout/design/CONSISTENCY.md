# Arrow Out: consistency pass (GAMEPROMPT §6.2)

Consistency writer, 2026-09-25 (+03). This pass compares every named constant that two or more design documents state, flags every
disagreement and every PENDING left open, and recommends a ruling for each. No spec was edited. The orchestrator rules on this file,
then rewrites SPEC.md.

**Read in full:** SPEC.md (§1-§6); design/SPEC-architecture.md (2,317 lines); design/SPEC-gameplay.md (1,049); design/SPEC-ui.md
(1,461); design/SPEC-motion-audio.md (1,125); design/SPEC-social.md (675); design/levels.json (header, `sessions`, `unlocks`,
`tutorials`, `curve`, plus a field census of all 150 levels); design/ui-tokens.json (meta, dims, palette, the components other specs
cite); design/ui-tokens-2.json (every section, all 164 strings).

**Checked for the BUILD column** (information only, so owners know which shipped data still carries a superseded value):
`App/Resources/Tuning/{rules,board,ui,audio,game,social}.json`, the ◆ contracts `AudioContract.swift`, `ShellContract.swift`,
`PlayerState.swift`, `LaunchArgs.swift`, and C3/SOC1 sources where a spec value is compiled in (`EconomyRules.swift`, `Lives.swift`,
`Population.swift`, `SocialModel.swift`, `ExitKinematics.swift`), plus `art/MANIFEST.json` for art ids.

**Measured in this pass:** the fit of every conflicting TR string. Method: SPEC-ui's `strings_fit.py` (the shipped `PCDisplay-Black.ttf`,
CoreText through the `ctmeasure` helper), each string at its style size, tracking and box from SPEC-ui §3. The 2-line rule is the same:
width / lines × 1.12. Floor 0.70 (SPEC.md §5.14). The script is `fit.py` in this session's scratchpad (`consistency/`). Results are
in §16.

---

## 0 How to read

### 0.1 File codes
| code | file |
|---|---|
| SPEC | SPEC.md (§5 n = orchestrator reconciliation n) |
| ARCH | design/SPEC-architecture.md |
| GP | design/SPEC-gameplay.md (LV = design/LEVELS.md) |
| UI | design/SPEC-ui.md |
| TOK / TOK2 | design/ui-tokens.json / design/ui-tokens-2.json |
| MA | design/SPEC-motion-audio.md |
| SOC | design/SPEC-social.md |
| LJ | design/levels.json |
| BUILD | the running build's data or code today (informational, not a spec) |

Evidence tags are the specs' own: **V** VERIFIED, **I** INFERRED, **D** DECISION (the source is given in the spec cited).

### 0.2 Status column
| status | meaning |
|---|---|
| **OK** | every file that states it agrees (small wording differences noted) |
| **FLAG-W** | disagreement with a clear winner under §0.3. Apply the ruling and update the loser (spec text, key or data). |
| **FLAG-S** | stale: SPEC-architecture seeded a value that the owning content spec has now replaced. ARCH §0.1 already says the content spec wins. No decision is needed, but code or tests that quote the ARCH value must change. |
| **FLAG-R** | needs an orchestrator or owner ruling, or a ◆ contract change. A recommendation is given; §21 collects them. |
| **PENDING** | still unfilled after all six specs |

### 0.3 Ruling rules (applied in this order)
1. **Ownership** (SPEC.md §4): the owning spec wins in its domain.
   - ARCH: code structure, files, persistence, contracts, engine behaviour, performance budgets.
   - GP + LJ: rules, levels, economy, boosters, event rules, tutorial content, strings.
   - UI: geometry, colours, text styles, screen flows.
   - MA: timings, curves, particles, sounds, music, haptics.
   - SOC: the simulated world.
2. **Binding rulings**: SPEC.md §5 items and the OWNER blocks in PLAN.md.
3. **Evidence**, when two sources compete for the same value:
   - a measurement beats an estimate;
   - a newer capture beats an older one;
   - the phone (v552) beats the videos, and the videos beat web footage;
   - a DECISION never beats a VERIFIED value.
4. **Strings.**
   - GP's EN and TR win, unless GP's TR fails the 0.70 fit floor. Then the variant that fits wins (measured here, §16).
   - For event and social copy, SOC's TR proposal wins unless UI lists a deliberate, measured difference (UI §3).
   - Every integer argument is `%lld`.

---

## 1 Summary

- **335 constants** are compared in §3-§18:
  - **181 OK**;
  - **106 FLAG-W** (the winner is clear; 32 of them are TR/EN strings);
  - **26 FLAG-S** (ARCH seeds replaced by a content spec);
  - **19 FLAG-R** (18 distinct decisions; M-3 repeats O-23; §21 lists them);
  - **2 PENDING** (small motion details nobody specified: T-33, W-23); K-4 RESOLVED by SPEC.md ruling 30 (21:12).
  - A few rows in §16-§18 point back to an earlier row (e.g. M-2 → O-21, S-25 → W-10) and repeat its flag.
- **Every PENDING item in ARCH §14 is filled.** All 18 PENDING-gameplay, 8 PENDING-ui, 12 PENDING-motion-audio and 3 PENDING-social
  items are covered (§2). Where a filler conflicts with another spec's filler, §2 names the flag.
- **One data bug waiting in the build.** `App/Resources/Tuning/rules.json` still has `lives.refillSeconds 1200`. C3's
  `EconomyRules.load` decodes the file's `lives` section over its compiled 1800 default. So once GAME wires it up, a life refills every
  20 min instead of the VERIFIED 30 min (X-7).
- **One content-versus-art gap blocks endless levels:**
  - L1–L150 need 48 door sizes; the MANIFEST has 9;
  - the runtime generator for L151+ can ask for any size;
  - ARCH requires "only sizes present in the bundle";
  - see O-23.
- **Simulated players can reference avatars 9–14, which do not exist.**
  - SOC1's shipped world model picks a portrait from 14, the V2 set;
  - SPEC.md §5.12 ships the phone's 8 portraits plus the default;
  - see V-24.
- **Contract changes the content specs imply** (§19). Four are additive ◆ edits: SoundID, Haptic, the Tuning.swift haptic rows and
  DimToken. The other four can be avoided with data or with code in the owner's own files.

---

## 2 SPEC-architecture §14 PENDING index: closure

### 2.1 PENDING-gameplay
| # | item | filled by | value | status |
|---|---|---|---|---|
| 1 | tape some-clear policy | GP §3.4 | the whole bundle bumps, one heart, every member red; `rules.json tape.blockedPolicy "bundleBumps"` (D) | filled (B-10) |
| 2 | tapping a bumping arrow | GP §2.4 | ignored until back (`IgnoreReason.bumping`, ≤ 0.35 s) (D) | filled |
| 3 | pipe consumption on a blocked exit | GP §3.6 | none; `pipe.bumpConsumes false` (D) | filled |
| 4 | elevator empty-cell blocking | GP §3.8 | never block; `elevator.emptyCellsBlock false` (V vlev-D) | filled (O-12 asks for one extra key) |
| 5 | hearts per stage in multi-board sessions | GP §4, LJ sessions | `carry` (D) | filled |
| 6 | fail chain later steps, grants, escalation | GP §7.1 | every step costs 900; Play On grants the chain's first grant (+30 s / 3 hearts) (D); no escalation (V: 900 on every step seen) | filled |
| 7 | life refill seconds | GP §8.1 | **1800** (V economy ledgers) | filled; FLAG-W against ARCH's 1200 and BUILD (X-7) |
| 8 | kill mid-level | GP §8.5 | a failed attempt; `lives.killIsLoss true` (D) | filled |
| 9 | booster effects | GP §6.2-6.3 | freeze 10 s (V); flight 1.5 s against MA's 1.6 (K-3); hint = the free unit that unblocks the most arrows (D) | filled, with FLAG K-3 |
| 10 | booster prices, buy flow | GP §6.4 | a "Buy ×3 for 900" popup at 0 stock (D) | filled; FLAG-W against UI §2.10 (K-6) |
| 11 | shop catalogue | GP §9.4 | 12 products; US $ and TL | filled; FLAG-R on the currency shown (X-18) |
| 12 | Claw ladder and duration | GP §11.2 | 20 steps, weekly; thresholds 1–7 V, 8–20 D | filled; FLAG-W against SOC D16 (V-9) |
| 13 | event schedule (unlock levels) | GP §11.3 = SOC D11 | L30 / L33 / L40 / L50 / L55 | filled, OK |
| 14 | authored level count | GP §14, LJ `authoredEnd` | 150 | filled |
| 15 | unlock levels in our build | GP §10.4, LJ unlocks, SPEC §5.19 | L7 / L11 / L21 / L31 / L33 | filled, OK |
| 16 | hit radius and tie break | GP §2.2 | 22 pt on screen; a tie within 1 pt → the right-hand arrow, then the lower one | filled; BUILD stale (G-6) |
| 17 | timer alerts near 0 | GP §5, MA §4 | none (V) | filled, OK |
| 18 | local notifications | GP §12.5 | `livesFull` and `weeklyEnding` (2 h before Monday 07:00 UTC) | filled |
| — | inline: ObstacleSpec field names (ARCH §4.3) | GP §14.1 | the bundle keys exactly; no decoder change | filled, OK (O-3) |
| — | inline: `Solver.hintUnit` policy (ARCH §4.14) | GP §6.3 | `unblocksMost` | filled; key placement FLAG-W (K-8) |
| — | inline: no-lives popup copy (ARCH §6.2) | GP §8.4 + UI §2.9 | the v552 More Lives popup | filled, OK |
| — | inline: EventsDirector queue rules (ARCH §8.4) | SOC §4.8, GP §9.3, MA §8.3, UI §2.2.7 | Sky Jump progress → home → segments A/B/C → claims → offers → Streak list | filled; ARCH's own order is stale (W-15) |

### 2.2 PENDING-ui
| # | item | filled by | value | status |
|---|---|---|---|---|
| 1 | Loading minimum time | UI §2.1 | 1.5 s + boot done + the first-launch alert answered; cap 4 s (alert time excluded) | filled |
| 2 | home tab and Loading → home transitions | UI §1.8 (MA §7 agrees) | tabs: hard cut (0 s); Loading → home: 0.16 s cross-fade | filled; BUILD `loadingToHome 0.3` is stale |
| 3 | arrow-pile states | UI §2.2.8 | full at rest + a refill animation on home re-entry (1.2 s, D) | filled; the timing has no MA row or key (W-23) |
| 4 | no-lives, booster-buy, settings layouts | UI §2.9, §2.10, §2.13 | More Lives; a booster info popup; Settings as a full page | More Lives OK; booster-buy FLAG-W (K-6); Settings FLAG-R (U-5) |
| 5 | Support / Terms / Privacy offline states | UI §2.13.1 | offline pages | filled; FLAG-R against GP §12.2-12.4 (U-6) |
| 6 | silhouette border | UI C6 | absent on v552 (V) | filled |
| 7 | box sprites / slices | UI §4.3 | a code-drawn slab + a `boxRing` sprite | filled; FLAG-W against GP's request and the ARCH validator wording (O-22) |
| 8 | shop layout | UI §2.12 | the full v552 page | filled |
| — | inline: `LaunchBackground` colour | UI §1.8, §5 | `#ABA0D8` | filled |

### 2.3 PENDING-motion-audio
| # | item | filled by | value | status |
|---|---|---|---|---|
| 1 | bump profile | MA §3.4 | constant speed, T_out = 0.075 + 0.025·c, no hold, back 0.14 s easeOutQuad (V v552) | filled |
| 2 | violet colour | MA §3.2.2 | a 6-stop field, period 3.75 cells | filled (a lossless sample is still open, clips-needed #10) |
| 3 | rainbow period | MA §3.2.2 | 4.2 cells ([P3] 3.66 / 4.74) | filled; BUILD 5.6 stale |
| 4 | star counts / sizes | MA §3.2.3 | 2.4 per cell, 0.30 p, life 0.40 s | filled |
| 5 | build-in of obstacles | MA §3.5.7 | drawn complete, no fade (V) | filled |
| 6 | pipe / box counter-change timing and animation | MA §3.5.3-4 | pipe when the arrow leaves the far mouth (V), box at the tap (V), instant glyph swap (I) | filled |
| 7 | pan limits and snap-back | MA §3.9 | `pan.limit centreInGrid` (V); native bounce (D) | filled |
| 8 | slop | MA §3.9 | 10 pt (D) | filled |
| 9 | combo window, whether bumps break it | MA §3.3 | 1.25 s (I); a bump breaks the streak (D) | filled |
| 10 | puppet idle loops | MA §8.2 | 3.16 / 10.2 / 17.3 s with keyframe tracks | filled; BUILD shared knobs superseded |
| 11 | cue list, music, tap-sound question | MA §11 | 9 SoundIDs (5 need a ◆ change), no music, `tapTick` unmapped | filled; FLAG-R contract (A-2) |
| 12 | haptic intensities | MA §12 | 10 cases, one per frame | filled; FLAG-R contract (A-8) |
| — | referenced but not specified | UI §2.6.3 → MA | the Continue? token popup's "orange x1 chip slides over the current one" (a reset preview) | **PENDING** (T-33) |
| — | referenced but not specified | GP §6.2 `freezeRunsBeforeStart false` → MA | what the freeze tray shows when the hourglass is used before the first tap | **RESOLVED** (K-4, SPEC.md ruling 30) |

### 2.4 PENDING-social
| # | item | filled by | value | status |
|---|---|---|---|---|
| 1 | the whole world model | SOC §2-§5 | cohorts, archetypes, names, rivals, Sky Jump field | filled (group sizes FLAG-W, V-5 and V-6) |
| 2 | event durations and calendar | SOC §4.1 | days start 07:00 UTC; weeks start Monday 07:00 UTC; every event every day or week, forever | filled, OK |
| 3 | clock-forward policy | SOC §5 | forward jumps accepted; set-back freezes; a one-time rebase after 30 days | filled |

---

## 3 Identity, files, paths, fonts, launch arguments

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| ID-1 | Product name | SPEC §2, §5.1: "Arrow Out" from `PC_BRAND_NAME` · ARCH §2.1-2.3: `Brand.name` reads `PCBrandName` · GP §12.2, §16.10: `%@` = `Brand.name` · UI §0: `Brand` only | OK | — |
| ID-2 | Bundle and product ids | ARCH §2.1: `com.manycode.arrowout`; ARCH §4.8: `com.manycode.arrowout.<id>` · GP §9.4: same prefix; ids `offer.special`, `bundle.*`, `coins.N` | OK | — |
| ID-3 | Font | SPEC §2: Nunito wght 1000 · ARCH §2.3, §6.11: `PCDisplay-Black` / `-BlackItalic` · UI §0.3, §1.4 · TOK meta.font · MA §6.4 | OK | — |
| ID-4 | Canvas and units | ARCH §0.3: 393 × 852 pt; pt = px × 393/1178 · UI §0.3: safe area 59/34 · TOK meta, TOK2 meta: same | OK | — |
| ID-5 | Save file | ARCH §4.12: `Application Support/Save/player.json`; social state in `PlayerState.social` · SOC §6: a separate `Application Support/Save/social.json` with its own StateStore · BUILD `StateStore`: player.json | FLAG-W | ARCH owns persistence. SOC §6's schema becomes the content of `SocialState` inside player.json (additive-only). There is no second file. |
| ID-6 | Where the streak multiplier and Claw state live | ARCH §4.10: `PlayerState.events` (C3) · GP §11.1: `PlayerState.events` · SOC §6: `streakStep` and `claw{…}` in social.json | FLAG-W | ARCH/GP: one copy in `PlayerState.events`. Social reads it (via the event hooks); it never stores its own copy. |
| ID-7 | Social ledger cap | ARCH §4.12: the last 400 entries + weekly aggregates, file < 64 KB (D) · SOC §6: the last 200 wins + the last 10 play windows | FLAG-W | SOC decides what the model needs (200 + 10). ARCH's < 64 KB budget still binds. |
| ID-8 | Name data shipped | ARCH §4.11: `design/social/data/*.txt` → `bundle/Social/*.txt`, byte-identical · SOC header: `social_names.json` is "the ONE shipped name resource" · BUILD `Resources/Social`: both the .txt files and the JSON | OK | Ship what SOC1 reads. ARCH's byte-identity test covers every copied file. |
| ID-9 | Install-seed launch arg | ARCH §9.1 (◆ LaunchArgs): `-pc.seed N` · SOC §7: `-pc.socialSeed <u64>`, `-pc.socialCountry`, `-pc.socialScenario` | FLAG-W | ARCH: use `-pc.seed` for the install seed. `socialCountry` and `socialScenario` are private flags read from `LaunchArgs.raw` (ARCH §3.5). No ◆ change. |
| ID-10 | `-pc.now` | ARCH §9.1: overrides the wall clock for lives, events and social · SOC §5, §7: overrides `deviceNow` | OK | — |
| ID-11 | `-pc.popup continue:hearts` | ARCH §9.1 · UI §2.6.2: a separate "Out of Lives!" popup (a11y `popup.outOfLives`) · ◆ ShellContract comment: continueOffer variants include "hearts-out" | FLAG-W | Keep the argument. It shows the Out of Lives! layout (the Out of Time family). No new PopupID. |
| ID-12 | `-pc.stage K` base | ARCH §9.1: "e.g. Levels 1-4 stage 3" (ambiguous) · ARCH §4.5 `AttemptSetup.firstStage` "0, or -pc.stage" · LJ tutorials `stage: 0` = the first board | FLAG-W | 0-based everywhere (LJ already uses 0 for stage 1). Fix the ARCH example. |
| ID-13 | Social EPOCH | ARCH §4.11 inv. 4: `1777273200` · SOC §2.1, D4: 2026-04-27 07:00 UTC | OK | Checked: 1777273200 = 2026-04-27T07:00:00Z. |
| ID-14 | Capture defaults | ARCH §9.2: seed 1, clock 2026-09-25T12:00:00Z · SOC §7: `-pc.socialScenario` presets | OK | — |

---

## 4 Board geometry and input

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| G-1 | Zoom cap | ARCH D6, §4.2: 28.07 pt per cell, absolute (V L47/L50) · GP §2.1 · MA §3.9 `zoom.maxPitch 28.07` · BUILD board.json | OK | — |
| G-2 | Minimum zoom | ARCH D6, §4.2, §5.2: **0.786 × fit** (V L47); B1 acceptance and BoardInputTests "clamps at 0.786×" · GP §2.1: "14.04…28.07 absolute (arch D6)" · MA §3.9: `zoom.minPitch 14.036` absolute (V motion §6.7, boosters §4: L62 opens at 14.05 and cannot zoom out) · BUILD board.json has both (minPitch wins; 0.786 is a fallback) | FLAG-S | MA: absolute 14.036 pt. The two rules agree only when the fit pitch is ≈ 17.9. Rewrite B1's test to "clamps at 14.036 pt". GP's value is right but its citation of ARCH D6 is wrong. |
| G-3 | Fit rule and play rect | ARCH D6, §4.2: pitch = min(W/(cols+2), H/(rows+2), 28.07); play rect 122…755 pt (V: every recorded pitch within ±0.03) · UI §1.1: `ShellLayout` publishes the play rect "from the adapted HUD/booster frames" (UI booster tray top = 753.3) · GP §14.4: L6 (27 cols) fits at 13.55, below the 14.04 floor (V) | FLAG-W | ARCH: publish 122…755 on the 393 × 852 reference, adapted by UI §1.1 on other devices. Do not use the raw tray top (753.3); it is 1.7 pt off the measured fit. A board that opens below the floor (L6) cannot zoom out, which matches ARCH (no clamp on the fit). |
| G-4 | Arrow corner shape | ARCH §4.2, §5.4: a sharp polyline, `lineJoin .round` (outer radius = half the stroke, inner corner sharp) · MA §3.2.1: "the path is a polyline with corner fillet 0.125 p" (V motion §2.2) · BUILD board.json `arrow.cornerFillet 0.125` | FLAG-W | MA (look, newer V). The kinematics stay on the centre-line polyline. C1's "bodyLength = (cells − 1)·p, exact" applies to that centre line, not to the drawn path. |
| G-5 | Hit radius | ARCH §5.3: `hitRadiusPt 15` (V ≥ 15, L47c; PENDING) and tests "a 15 pt off-stroke tap" · GP §2.2: **22 pt** on screen (D from V: 10/15 pt phone taps, 12–22 pt video taps); `board.json input.hitRadiusPt 22` **and** `rules.json hit.radiusPt 22` · BUILD board.json 16, rules.json 15 | FLAG-W | GP (the owner of this PENDING item). Update both BUILD files. One value lives in two files: add a TuningTests equality check. |
| G-6 | What the hit radius measures | ARCH §5.3: content space, `max(0.5·pitch, hitRadiusPt/zoom)` · GP §2.2: ≤ 22 pt in screen space at the current zoom | OK | Same rule. 0.5·pitch·zoom is at most 14.04 pt on screen, so the `max` never binds at 22. |
| G-7 | Tie break | ARCH §4.2, §5.3: `rightThenDown` (V once, L52) · GP §2.2: within 1 pt, right then lower (`tieTolerancePt 1.0`) · BUILD board.json `tieTolerancePt 1.0` + `tieTolerancePitch 0.03` (B1 D) | OK | B1's pitch cap is a refinement inside GP's 1 pt. |
| G-8 | Slop | ARCH §5.3: 10 pt (V spike) · GP §2.1: → MA · MA §3.9: 10 pt (D) · BUILD 10 | OK | — |
| G-9 | A tap whose nearest arrow is still moving out | ARCH §5.3: moving arrows are excluded from the hit test (the touch falls through to the next nearest arrow) · ARCH §4.4 and GP §2.4: a tap on a moving arrow is ignored (`IgnoreReason.moving`) | FLAG-R (small) | GP. If the nearest centre line within 22 pt belongs to a moving arrow, emit `tapIgnored(id, .moving)`. Never re-target the tap to a neighbour: a quick double tap must not fire a second arrow. |
| G-10 | A tap on the pink tape tie | GP §2.2: the tie's cells are part of every member's hit shape · ARCH §5.3: "obstacles are never hit" | OK | The tie sits on member cells (`cells[len−2]`), so both rules resolve to the bundle. |
| G-11 | Pan limit | ARCH §5.2: `pan.slackPt 120` beyond each content edge (D, PENDING) · MA §3.9: `pan.limit "centreInGrid"` (V meta-116…123) · BUILD board.json slackPt 120 | FLAG-S | MA. B1 adds the key; `slackPt` is ignored when `limit` is set. |
| G-12 | Bounce and deceleration | ARCH: `pan.bounces true` (D) · MA: `pan.bounces`, `zoom.bounces` true; `deceleration "normal"` (D) | OK | — |
| G-13 | Double tap | ARCH §5.2, GP §2.1, MA §3.9: does nothing | OK | — |
| G-14 | Gestures never start the timer | ARCH §5.2, GP §5, MA §3.9 (V boosters §4): pinch, pan and zoom | OK | — |

---

## 5 Exit, colours, painters, dots, combo

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| E-1 | Exit law | ARCH D5, §4.16: s = 71.4τ − 21.29(1 − e^(−τ/0.323)) (V, pass 1, 5 exits) · MA §2: v0 7.67, vmax 73.86, T 0.353 (V, 11 exits) · BUILD `ExitKinematics.measured` = MA; board.json `exit.*` = MA | FLAG-S | MA. The build already uses it; ARCH §4.16's table is the old one. |
| E-2 | T(d) test table | ARCH: T(1) 0.078, T(5) 0.215, T(10) 0.331, T(20) 0.518, T(40) 0.836 · MA: 0.072, 0.209, 0.326, 0.513, 0.828 | FLAG-S | MA (±0.003 s). |
| E-3 | Where an exit ends | ARCH D5, §5.5; GP §3.2; MA §3.2.1: the tail leaves the SCREEN, passing under the HUD | OK | — |
| E-4 | W / `lastExitLeftBoard` | ARCH §4.5: "the last exit left the board" · MA §0.2: the tail leaves its last grid cell (`exit.leftBoardAt "lastCell"`, I) · BUILD `lastCell` | OK | MA defines it. |
| E-5 | Colour ramp (black → exit colour) | ARCH §4.16: 0.08 s · MA §2: 0.09 s linear (V) · BUILD 0.09 | FLAG-S | MA. |
| E-6 | Solid exit colour | ARCH §5.5, GP §3.2, MA §3.2.2, BUILD: `#10A2EF` | OK | — |
| E-7 | Combo ladder | ARCH §4.7, D23; MA §3.2.2, MA4; BUILD: solid, solid, violet, rainbow (the last repeats) | OK | — |
| E-8 | Combo window | ARCH §4.7 (I); MA §3.3 (I); BUILD rules.json: 1.25 s | OK | — |
| E-9 | A bump breaks the combo | ARCH: PENDING (default true) · MA §3.3: true (D) · BUILD true | OK | filled |
| E-10 | Violet painter | ARCH §4.7, §5.5: solid ≈ `#9A50F5` (I) · MA §3.2.2: a field `#01ACFD · #3972FF · #7B3CFC · #B908FE · #7B3CFC · #3972FF`, period 3.75 cells · BUILD board.json `color.violet "#9A50F5"` | FLAG-S | MA (`board.json violet.*`). Drop `color.violet`. |
| E-11 | Rainbow palette | ARCH §5.5 (V), MA §3.2.2 (V lossless), BUILD: 12 stops `#FF6500` … `#FF5A85` | OK | — |
| E-12 | Rainbow period | ARCH §5.5: PENDING (5.6 spike vs 3.8 STYLE) · MA: 4.2 cells ([P3] 3.66 and 4.74 on lossless phone shots) · BUILD 5.6 | FLAG-W | MA (a phone measurement beats the spike and the store shot). Update BUILD. |
| E-13 | Colour field fixed on the path | ARCH §5.5: "bands fixed on the path" · MA MA5 | OK | — |
| E-14 | Trail stars | ARCH §5.5: PENDING (look V, fade ≈ 0.4–0.6 s) · MA §3.2.3: 2.4 per cell, 0.30 p ± 0.08, jitter 0.25 p, life 0.40 s | OK | filled |
| E-15 | Vacated dots | ARCH §5.5 item 5: a dash layer per departed arrow; `strokeEnd` reveals each dot as the tail leaves; §5.7: "no dot lattice before cells are vacated" · MA §3.2.4: ONE static layer at stage load, a dot under every arrow cell; the arrows cover them (V shot 003: a bluish fringe at outer corners) | FLAG-W | MA (newer V). It also fits ARCH's "no lattice": cells no arrow ever used get no dot. B1's `DotsPainter` changes (`board.json dots.mode "static"`). |
| E-16 | Dot look | ARCH §4.2, §5.5; MA §3.2.4; TOK `board.vacatedDot`: `#C5E1FF`, ⌀ 0.192 p | OK | — |
| E-17 | Tap ripple | ARCH §4.16, §5.8: radius 11 → 22.5 pt, luminance 180 → 250, **0.25 s**, pool 6 · MA §3.1: keyframes over **0.233 s**, pool 6 · BUILD 0.233 | FLAG-S | MA. |
| E-18 | Ripple on a miss | ARCH §5.3 (D); MA §3.1 (D); GP §2.1: an empty point shows the ripple only | OK | — |
| E-19 | Layer order of an exit | ARCH §5.1, MA §3.2.1: above idle arrows and obstacles, under the HUD and boosters; inside a pipe's tube | OK | — |

---

## 6 Bump and hearts

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| B-1 | Bump motion | ARCH §4.16, §5.5: forward, **hold**, back; PENDING (phone ≈ 400 pt/s out, ≈ 0.13 s back; YT-B 0.09 / 0.10 hold / 0.10 back) · MA §3.4.1: constant speed, T_out = 0.075 + 0.025·c, no hold, back 0.14 s easeOutQuad (V 2 v552 clips) · BUILD board.json = MA | FLAG-S | MA ("hold" is gone). |
| B-2 | Marked (bumped) red | ARCH §5.4, UI §2.3.5, MA §3.4.1, BUILD: `#EE0A13` (238, 10, 19) (V) · GP §4: `#EE0912` | FLAG-W | `#EE0A13` (GP has a typo). |
| B-3 | When the arrow turns red | ARCH §5.5: on the return (≈ 516 ms into the clip) · MA: from C + 0.017 over 0.103 s, S-curve | OK | There is no hold, so the return starts at C. MA gives the numbers. |
| B-4 | ✖ badge and blocker flash | ARCH §5.5: badge fades in ≈ 0.3 s · MA §3.4.2-3: badge 1.0 p, `#F62631` / `#7A0A10`, gone by C + 0.43; blocker red 0.10 s, back by 0.33 · UI §2.3.5: ≈ 1 pitch, `#F62631` | OK | MA timing, UI look; they agree. |
| B-5 | Red screen-edge vignette | ARCH §4.16, §5.8: ≈ 50 pt deep, full for 0.05 s, fade 0.28 s (0.33 total) · MA §3.4.4: alpha 0.42·e^(−d/27 pt) to 90 pt, hold 0.035 s, gone at 0.333 s · UI §2.3.5: "≈ 50 pt deep, `#FE9B9B` at the edge" · BUILD = MA | FLAG-S | MA. UI's `#FE9B9B` is alpha 0.39 over white, inside MA's measured 0.39–0.42. |
| B-6 | Heart loss animation | ARCH §6.5: the hearts dim from the right, ≈ 0.07–0.10 s cross-fade · UI §2.3.5: the heart turns `heartHUDLost`, cross-fade 0.07–0.10 s · MA §3.4.5: the heart **breaks into two halves** (y = −115τ + 480τ², x ±37.5τ, fade 0.30–0.40 s) over the empty recess (V v552) · GP §4: "the rightmost full heart breaks" | FLAG-W | MA (v552 V). The empty-slot look stays UI's `heartHUDLost`. Update the text in ARCH §6.5 and UI §2.3.5. |
| B-7 | Heart taken at contact, rightmost first, no time penalty | ARCH §4.5, §8.3; GP §4; MA §3.4; UI §2.3.1 | OK | — |
| B-8 | The first bump starts the timer | GP §4 (V fail §3); MA §3.4.6; BUILD `bump.startsTimer true`; ARCH §4.5: "first tap" (a bump is a tap) | OK | — |
| B-9 | A red arrow's re-bump costs no heart | GP §2.4, §4 (V once); MA §12.1 (`bumpContact` haptic for a no-heart re-bump); BUILD | OK | — |
| B-10 | Tape bundle bump | ARCH §4.4: default "the tapped member bumps alone" (PENDING) · GP §3.4: the whole bundle, one heart, every member red, one ✖ · MA §3.4.6: the same + a rigid move by the smallest member's contact travel (V META-L062-tape-blocked-bump) · BUILD `bundleBumps` | FLAG-S | GP + MA. |
| B-11 | Out of Lives! after the 3rd heart | ARCH §4.5: `.offer(outOfHearts)` at the contact ack · GP §4, §7.1: "at that contact frame" · MA §4: the popup at **C + 0.60** (I, after the 0.40 s heart break); `ui.json hud.heartsOutDelay 0.60` | FLAG-W | Both hold. The session emits the offer at contact (input locks, timer held: ARCH, GP). The popup is shown 0.60 s later (MA owns the timing). Key: `game.json fail.heartsOutDelay` (GAME reads it; T-4). |
| B-12 | Hearts per level | ARCH §4.3; GP §4; LJ: 3 on all 150 levels; UI | OK | — |
| B-13 | Heart geometry | UI §2.3.1: 201.5 / 237.5 / 273.6 · 82.1, 28.7 × 24.4 = TOK `hud.heart1..3` · MA §10: halves of 28.7 × 24.4 | OK | — |
| B-14 | Heart pop in the intro | ARCH §4.16, §6.5: 1.58 → 0.89 → 1.0, stagger 0.10–0.12 s · MA §3.6: keyframes 1.58 … 1.0 at K + 1.406 / 1.505 / 1.622 | OK | MA refines it. |

---

## 7 Obstacles

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| O-1 | Obstacle kinds | ARCH §4.3 `ObstacleKind`: tape, door, key, pipe, box, curtain, elevator, corner · LJ uses tape, door, key, box, pipe, elevator (videos' curtain → box, SPEC §5.11; corner unused, GP §3.9) | OK | — |
| O-2 | Obstacle id prefixes | ARCH §4.3: t0 d0 k0 p0 b0 c0 e0 x0 · GP §14.1: t, d, k, p, b, e + index · LJ: t, d, k, p, b, e | OK | — |
| O-3 | Obstacle JSON fields | ARCH §4.3 bundle v1: `id, kind, cells, arrows?, ends?, counter?, counter_at?, order?, opens?, turn?, reveals?, sprite?` · GP §14.1: the same ("no field name differs") · LJ census: id, kind, cells, arrows 168, counter 128, reveals 77, order 67, counter_at 63, ends 63 | OK | — |
| O-4 | Arrow JSON fields | ARCH: `id, cells, dir, layer?, hidden_by?` · GP §14.1 · LJ: 7,998 arrows (hidden_by 1,097; layer 94) | OK | — |
| O-5 | Level JSON fields | ARCH §4.3: `schema, level, source, capture, cols, rows, mask, timer_s, hearts, tag, arrows, obstacles, unlock?, seed?, metrics?` · GP §14.1: the same + `_from` (a comment) · LJ: the same; `_from` on 7 levels | OK | Codable ignores `_from`. `pclevels bundle` copies it, which keeps the byte-for-byte check. |
| O-6 | `tag` values | ARCH `LevelTag`: normal, hard, superHard (also accepts null, "Hard Level", "Super Hard") · GP: "normal", "hard", "superHard" · LJ: normal 123, hard 14, superHard 13 | OK | — |
| O-7 | `source` values | ARCH: recorded, video, designed, generated · LJ: video 38, recorded 26, designed 86 | OK | — |
| O-8 | `mask` | ARCH `Grid.mask`: nil = all playable · GP §14.1, LJ: null = "the silhouette is the arrow cells" | OK | The behaviour is the same: empty cells never block. |
| O-9 | Metrics keys | ARCH `LevelMetrics`: rounds, freeAtStart, arrows, cells, meanLength, botTimeLeft · LJ: rounds, free_at_start, arrows, cells, mean_length, bot_time_left | OK | snake_case in JSON |
| O-10 | Door order | ARCH §4.4; GP §3.5: `order` 0-based; a key flies to the lowest-order locked door not yet targeted; `opens` is explicit (unused) | OK | — |
| O-11 | Door burst | ARCH §4.4, §4.15, §5.6; GP §3.5; MA §3.5.2: at tap + 1.14 s; the door blocks until the burst ack (V) | OK | — |
| O-12 | Elevator activation moment | ARCH §4.4: when the last platform arrow is tapped, at once (V) · GP §3.8: at the tap (V: a tap 0.03 s after the doors began to part bumped) · MA §3.5.5: asks for `rules.json elevator.activateAt` ("tap" today, or "clear") — the key is missing from GP §15 | FLAG-W | GP/ARCH: "tap". If C2 adds the key, its value is "tap". |
| O-13 | Empty elevator cells | ARCH (I), GP (V vlev-D), MA (V), BUILD: never block | OK | — |
| O-14 | Elevator reveal motion | ARCH §5.6: the platform darkens and merges; layer 2 fades in ≈ 0.25 s · MA §3.5.5: the doors part in 0.30 s at O + 0.02; tint 0.55 → 0; the frame fades 0.15 s (V vlev-D) | FLAG-S | MA. |
| O-15 | Pipe counter | logical decrement at the tap: ARCH §4.4, GP §3.6, MA · visible change: ARCH `PlanBeat.pipeCount` PENDING (enter or leave) · GP `pipe.countAt "leave"` (V vlev-C/D) · MA "leave" · BUILD rules.json **"enter"** | FLAG-W | "leave". Update BUILD rules.json. |
| O-16 | Pipe break | ARCH §4.4, §5.6 (V); GP §3.6; MA §3.5.3: 0.05 s after the head leaves the far mouth | OK | — |
| O-17 | A bump through a pipe consumes nothing | ARCH (D, PENDING); GP `pipe.bumpConsumes false`; BUILD | OK | — |
| O-18 | Pipe loop guard | ARCH §4.4: "loop guard" · GP §3.6, §15, BUILD: `pipe.maxHops 16` | OK | — |
| O-19 | Box rule | SPEC §5.11; ARCH §4.4; GP §3.7; MA §3.5.4 (V); BUILD `box.countAt "tap"`: every arrow cleared anywhere (each tape member counts one) lowers every box by 1 at the tap; the box breaks on that first-motion frame; "0" is never drawn | OK | — |
| O-20 | Curtain versus box | SPEC §5.11: the video "Curtain"/"Box" levels use the Box skin and card · ARCH keeps a `curtain` kind + `curtainCrate` sprite · LJ uses `box` only · UI §4.4: curtain art not shipped | OK | The curtain kind is unused; the importer maps curtain → box. |
| O-21 | Box obstacle look | ARCH §5.6: purple slab, 4 bolts, silver 4-lobed ring; asks UI-ART for per-size sprites (`boxW{w}H{h}`) or `boxSlice` + `boxRing`; §4.14 the validator checks box sizes resolve · UI §4.3, TOK2 `boxObstacle`: a **code-drawn slab** (r 0.40 p, face `#BC5BF6`, bevels, rivets) + a `boxRing` sprite ⌀ 2.2 p · GP §17.1 #1: "box sprites at every size the content uses" (LV §2.5: 23 sizes) | FLAG-W | UI (looks; draws any size). GP's per-size request is withdrawn except `boxRing` and `unlockIconBox`. For boxes, the validator's sprite check becomes "`boxRing` is present". |
| O-22 | Tape sprites | ARCH §5.6; UI §4.1 (done); LV §2.5: `tape{V,H}{2,3,4}`, all 6 used | OK | — |
| O-23 | Door sprites per size | ARCH §4.14, §5.6: "the generator only uses sizes present in the bundle"; MANIFEST has 9 (`doorW4H4` … `doorW22H10`) · LV §2.5: **48 door sizes** are needed by L1–150; `gen_levels.py` makes any size ("`manifest.py add-door W H`") · UI §4.1: the 9 | FLAG-R | 39 sizes are missing today, and L151+ runtime levels can ask for sizes no bundle has. **Recommended:** draw the door shutter in code as a 9-slice like the box slab (+ the `lockHex` sprite), so any size renders and the generator stays unchanged. **Otherwise:** UI-ART renders all 48, and C4 limits runtime door sizes to the bundled set (L1–150 unaffected). |
| O-24 | Tape geometry | ARCH §4.14: validator "one band of 2–4 lanes" · GP §3.4: 2, 3 or 4 straight, parallel, equal-length arrows; the tie covers `cells[len−2]` | OK | — |
| O-25 | Door shards | ARCH §4.16, §5.6; MA §10: ≈ 60 shards, g ≈ 1000 pt/s², 0.9 s | OK | — |
| O-26 | Obstacle build-in | ARCH §5.7: sprites fade in (PENDING) · MA §3.5.7: drawn complete on the first frame, no fade (V) | OK | filled |
| O-27 | Counter digits | ARCH D16: CoreText glyph paths; pipe digits white with `#822521` outline · UI §4.3: box digits white, purple `#4B1F86` outline, 0.8 p · MA: instant swap, no pop | OK | — |
| O-28 | Corner | ARCH §4.4 (I, supported) · GP §3.9: in no level, not in the endless curve · UI §2.8: a card only if content uses corners · MA §3.5.6: wedge pop (D) | OK | not shipped |
| O-29 | Key sprite | ARCH §5.4, GP §3.5: `keyOnArrow` on 2 cells | OK | — |

---

## 8 Level content and the generator

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| L-1 | Level order | SPEC §5.19; GP §14.2; LJ `_from`: L1–31 from the videos (video order); L32–61 phone; the duplicate slots L35/45/51/52 ← V2-L032..035 with the slot's v552 timer and tag | OK | — |
| L-2 | The three spares at L62–L64 | SPEC §5.19: "Spare V2-L036..V2-L038 open the designed range at L62-L64" (in that order) · GP §14.2, LJ: L62 V2-L036, **L63 V2-L038, L64 V2-L037** (the biggest board takes the Hard slot, D) | FLAG-R | **Accept GP's swap.** The spares' order carries no evidence, and the cadence puts a Hard level at L64. |
| L-3 | Level timers | SPEC §5.19: the videos' 3:00; Hard L19, L25; Super Hard L29 · ARCH §4.3: 3:00, 2:30, 2:00, 3:30 seen · GP §5 · LJ: normal 180 ×90, 150 ×33; hard 180 ×13, 210 ×1 (L34); superHard 120 ×10, 180 ×2, 150 ×1 (L49) | OK | — |
| L-4 | Hard / Super Hard cadence | ARCH §4.14: V Hard 34/44/54, Super Hard 39/49/59 · GP §10.5: from L34 every level ending in 4 is Hard and every one ending in 9 is Super Hard · LJ `curve.tagByPosition` {4: hard, 9: superHard} and the tags | OK | — |
| L-5 | Timers of designed levels | GP §14.3: Hard 3:00, Super Hard 2:00, normal 3:00 — or 2:30 with p 0.45 when the bot's work is ≤ 40 % · LJ `curve.timers` {normal 180, short 150, pShort 0.45, maxWorkShareShort 0.4, hard 180, superHard 120} | OK | — |
| L-6 | Authored count | ARCH L2: PENDING, "≥ 100" · GP §14 · LJ `authoredEnd` 150 (top level and inside `curve`) | OK | — |
| L-7 | Runtime levels beyond the authored set | ARCH D9, §4.14: `PathRandom.levelSeed(level: n, salt: curve.salt)` · GP §14.3 · LJ `curve.salt` = 15177990143040770677 | OK | — |
| L-8 | Generator retry policy | ARCH §4.14: on failure retry with `seed + 1` (≤ 8 tries), then the nearest authored level of the same tag · GP §14.3: the best of `attempts` = 10 forks; drop the last obstacle kind if infeasible; never serve an unvalidated level · LJ `curve.attempts 10` | FLAG-W | GP (the content algorithm; C4 ports `gen_levels.py` bit-exact). Keep ARCH's fallback only as the never-crash net. |
| L-9 | Generator cost | ARCH §4.1: 40 × 40 ≤ 30 ms p95 (macOS `-O`); §4.14: ≤ 60 ms on device, never on the tap path; C4 acceptance: ≤ 30 ms p95 · GP §14.3: Python worst case 3.2 s (26 × 36 Hard); Swift "~50× faster" ≈ 64 ms (an estimate); on a background queue | FLAG-R | ARCH owns budgets. **Binding now:** generate off the main thread, one level ahead, never on the tap path. C4 measures p95 and the maximum before the ms numbers are relaxed. |
| L-10 | Grid size cap | ARCH: a 40 × 40 synthetic board (soak, spike) · GP §14.3, LJ: `maxCols 26`, `maxRows 36` | OK | 40 × 40 stays the soak's synthetic board. |
| L-11 | Curve fitted to | ARCH §4.14: L1–L61 · GP, LJ: the recorded L30–L61 (templates L30–L59) | OK | — |
| L-12 | `sessions.json` | ARCH §4.3 example = GP §10.2 = LJ: `L1-4`, levels [1,2,3,4], `hud_label` "Levels 1-4", `panel_label` "Level 1-4", reward 80, `stage_gap_s` 0.7, hearts carry | OK | — |
| L-13 | `unlocks.json` fields | ARCH §4.3; LJ: feature, level, title, card, caps, icon | OK | — |
| L-14 | `tutorials.json` | ARCH §4.3: `id, level, stage, trigger, caption, hand {arrow, at}, dismiss, holdTimer` · LJ `tapToMove`: level 1, stage 0, `stageReady`, hand arrow 1 at [0.89, 1.06], `anyTap`, holdTimer false · GP §10.2 | OK | — |
| L-15 | Feature ids and first appearance | ARCH `FeatureID` examples · GP §10.4 · LJ unlocks and `curve.obstacles.firstLevel`: tape 7 (feature `linked`), box 11, pipe 21, elevator 31, door 33 | OK | The feature `linked` is the obstacle kind `tape` (SPEC §5.11). |
| L-16 | Overlay IoU gates | SPEC §5.7; ARCH L1: video levels ≥ 0.97, recorded levels ≥ 0.99 | OK | — |
| L-17 | Door levels reconstructed | ARCH R7: the fallback is to replace a level that cannot be completed · GP §14.2, LV §3: 11 of 11 reconstructed | OK | The fallback is not needed. |
| L-18 | Level file name | ARCH §3.2, §4.3; GP §14.1: `level_NNNN.json` (4 digits) | OK | — |

---

## 9 Session, timer, intro, transitions

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| T-1 | The timer starts at the first tap on an arrow (an exit or a bump) | ARCH §4.5 (V); GP §5; MA §3.6; UI §2.3.1 | OK | — |
| T-2 | Timer display | ARCH §4.6 (D); GP §5; MA §4; UI §2.3.1: `ceil(remaining)`, "m:ss" with no leading zero on the minutes | OK | — |
| T-3 | Alerts near 0 | ARCH: PENDING · GP (V), MA (V), UI (V): none · BUILD `clock.alerts []` | OK | filled |
| T-4 | The 0:00 hold | GP §5: 1.61 s with input locked, key `game.json fail.zeroHoldSeconds` · MA §4: 1.61 s, key `ui.json hud.outOfTimeHold` (+ `Timing.outOfTimeHold`) · UI §2.3.1: 1.61 s | FLAG-W (key) | The value agrees. Use **one** key: `game.json fail.zeroHoldSeconds` (GAME's FailFlowDirector reads it; ARCH §3.2: GAME owns game.json). Drop `ui.json hud.outOfTimeHold`. Do the same for B-11's delay (`fail.heartsOutDelay`). |
| T-5 | Holds | ARCH §4.6 `HoldReason`; GP §5; BUILD `session.inputLockingHolds`: pause, popups, offers, unlock, tutorial, stage transition, win sequence, background, freeze | OK | — |
| T-6 | Win at the tap; a win beats a fail | ARCH §4.5 (D); GP §3.3 | OK | — |
| T-7 | Stage gap | ARCH §4.16 `Timing.stageGap`, §5.7 · GP §3.3 · MA §3.7 · LJ `stage_gap_s 0.7` · BUILD `board.json stageGap 0.7`: all 0.7 s | FLAG-W (keys) | The value agrees but lives in three places. The session's `stage_gap_s` wins for its session; board.json is the default. A test keeps them equal. |
| T-8 | Stage transition look | ARCH §5.7: wave → dots fade → build-in · MA §3.7: wave at W for 0.50 s; dots fade W + 0.12 for 0.56 s; new board at W + 0.70 with the draw-in; no zoom, no HUD intro | OK | MA gives the numbers. |
| T-9 | Level intro | ARCH §4.16, §5.7: build-in ≈ 0.33 s ease-out (YT-B) + the HUD spring · MA §3.6: zoom 1.49 → 1.0 easeOutCubic 1.35 s + draw-in 0.32 + 0.0216·n s (f0 = 0.10 + 0.30/n) · UI §2.3.7: zoom 1.49 → fit; HUD from 118 pt above · BUILD board.json `intro` = MA | FLAG-S | MA. |
| T-10 | Input during the intro | ARCH §5.3: `inputEnabled` false during the build-in; §8.5 intro → `ack(.introFinished)` → `.ready` · GP §2.1: input locked during the intro · MA MA9: `introFinished` at **K + 1.015** (when the HUD starts to drop). The zoom still runs to K + 1.35 and long arrows are still drawing; hit tests go through the presentation transform. | FLAG-R | **Accept MA9.** The original's input gate is not observable, and the FEEL goal is no dead input. B1 must hit-test through `stage.presentation()`. GP's "locked during the intro" then means until K + 1.015. |
| T-11 | HUD drop | ARCH §4.16, §6.5: spring, response 0.429 / damping 0.47 · MA §3.6: easeOutBack(3.42) = cb(0.333, 2.14, 0.667, 1), 0.334 s, from −118.4 pt at K + 1.015 (V 60 Hz) · UI §2.3.7: 118 pt | FLAG-S | MA. |
| T-12 | Booster slide-in | ARCH: spring 0.245 / 0.43 · MA: easeOutBack(2.57), 0.209 s, ∓88.8 pt at K + 1.092 | FLAG-S | MA. |
| T-13 | Big timer pop | ARCH: 3.5× → 2.65 → 2.2 → 1.6 → 1.12 → 0.8 → 1.0 over 0.50–0.749 s · MA: keyframes 3.5 → 1.42 (0.067 s) … 1.0 at 0.25 s, starting at K + 1.339 | FLAG-S | MA (60 Hz v552). |
| T-14 | FTUE first board | ARCH §5.7 `growFromTailsNoHUD`; GP §10.1; UI §2.1, §2.3.7; MA §3.6 (`introFinished` at +0.36 s): no HUD intro | OK | — |
| T-15 | Loading minimum and cap | ARCH: PENDING · UI §2.1, §5; BUILD: 1.5 s, cap 4 s (alert time excluded) | OK | filled |
| T-16 | Loading dots | ARCH §6.3 (V tutorials §1): "." → ".." → "..." · UI §2.1: the same, 0.4 s · MA §7: "Loading" → "Loading." → "Loading.." → "Loading..." (4 states), 0.40 s · BUILD `dotsPeriod 0.4` | FLAG-W | ARCH/UI: 3 states (V). The 0.4 s period agrees. |
| T-17 | Loading → first board | ARCH §6.1: ≈ 0.1–0.16 s (V) · GP §10.1: ≈ 0.1 s · UI §1.8 text: "0.16 s (… 0.13 → keep 0.13-0.16)"; §2.1 text: 0.16 s; §5 key: **0.13** · MA §7: 0.13 · BUILD 0.13 | FLAG-W | **0.13 s** (MA owns timing; also UI's own key value). UI's "0.16" in the text is a slip. |
| T-18 | Loading → home | UI §1.8; MA §7: 0.16 s · ARCH: PENDING · BUILD **0.3** | FLAG-W | 0.16. Update BUILD. |
| T-19 | Home tabs; home ↔ pages | UI §1.8 (I); MA §7 (D); BUILD: hard cut (0 s) | OK | — |
| T-20 | Home → level cut | ARCH §10.2: Play → first board frame ≤ 50 ms · MA MA10: ≤ 0.05 s after the release · UI §2.2.5: "hard cut to the level +0.06 s (motion §6.1)" — the original's latency | FLAG-W | MA (≤ 0.05 s). UI quotes the original's number. |
| T-21 | Popups appear instantly | ARCH `PopupStyle.dimFadeIn 0.0` (V: 0–0.1 s) · UI §1.3, §1.8 · MA §6.2 `popup.dimFadeIn 0` · BUILD 0 | OK | — |
| T-22 | Button press | UI §1.6.2, §1.7; MA §6.1; BUILD: scale 0.95 on touch-down, action on release | OK | — |
| T-23 | Toggle knob motion | UI §1.6.13: "DECISION: the knob slides 0.12 s ease-out" · MA §6.1: the look swaps on the release frame, no slide (D) | FLAG-W | MA (timing owner). Both are DECISIONs; the 1 fps phone shots show no slide. |
| T-24 | Toasts | UI §2.20, §5; MA §6.6; BUILD: hold 2.0 s, in 0.08 s, out 0.27 s; y 390 on home and pages, 110 pt below the top safe inset in a level | OK | — |
| T-25 | Unlock overlay beats | ARCH §4.16: icon +0.24 (settles +0.40), title +0.52, "Unlocked!" +0.60, card +0.76, sparkles +1.1, dismiss fade 0.25 s · UI §2.8: "fade 0.25 s" · MA §6.3: icon 0.26, settle 0.54, title 0.50, unlocked 0.62, card 0.78, sparkles 1.14, dismiss fade **0.16**, `acceptFrom 0.94` (V tutorials §6) · BUILD ui.json = ARCH | FLAG-W | MA. UI §2.8 and BUILD are stale. |
| T-26 | Unlock overlay behaviour | ARCH §8.4; GP §10.4; UI §2.8; MA §6.3: 0.90 dim, tap anywhere, the timer stays frozen | OK | — |
| T-27 | "Tap to move!" timings | ARCH §4.16, §8.4; GP §10.2; MA §6.4: shown 0.36 s after the board; caption 0.7 → 1.10 → 1.0 in 0.20 s; hand 0.24 → 1.0 in 0.28 s; loop 2.10 s; on dismiss the caption goes in 0.16 s and the hand in 0.12 s | OK | — |
| T-28 | Caption geometry | UI §2.3.6: centre (196.5, 289.1), ≈ 40 pt, `#121B51`, box 353 · MA §6.4: centre (195.5, 289) | FLAG-W | UI (geometry owner; 1 pt). |
| T-29 | Hand anchor | LJ `hand.at` [0.89, 1.06] on arrow 1 (pointing up; cells (1,3) → (1,0)) · GP §10.2 · UI §2.3.6: "38 % of its length from its tail end nearest the caption" · MA §6.4: "38 % down" · research tutorials §3: (193, 424), on the left edge, ≈ 38 % down | FLAG-W | The data (`hand.at`) wins. UI's wording is wrong: arrow 1 points up, so the end nearest the caption is its HEAD. 0.89 = the left stroke edge (1 − 0.11); 1.06 cells ≈ 38 % of the drawn length from the top. |
| T-30 | Overlay stagger (Weekly (i), Claw (i), Streak (i), Rocket and Sky tutorials) | MA §6.5 (V Weekly; the rest D); UI refers to MA | OK | — |
| T-31 | FTUE loss, X on Level Failed | ARCH §6.2: "A loss before the first home retries" · GP §7.1: "X on D → home" (no FTUE exception) | FLAG-R (small) | ARCH. Before the L6 win there is no home yet, so X returns to the same level. |
| T-32 | Background during play | ARCH §8.6; GP §8.5: hold + the Pause popup on return | OK | — |
| T-33 | Continue? token popup: an orange x1 chip slides over the current one | UI §2.6.3: "the reset preview, SPEC-motion-audio" · GP §11.1 (V L47: "look: SPEC-ui/motion") · MA: no row | PENDING | MA owner: add a row. Suggested: slide 0.25 s easeInOut at S + 0.30, mirroring §5 row 17. |

---

## 10 Win, celebration, home return

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| W-1 | Win sequencing | ARCH §4.16: beats from "the sign"; §6.7 and §8.4 WinDirector: wait for `lastExitLeftBoard` → clear wave → celebration · MA §5: every beat from **W**; the celebration runs **alongside** the clear wave (the sign enters at W + 0.41, before the wave ends at W + 0.50); `clearWaveFinished` is not a gate · UI §2.7.1: dim 0.90 reached +1.58 s after the wave starts | FLAG-S | MA. The WinDirector starts the celebration clock at `lastExitLeftBoard` (MA §15.3). |
| W-2 | Win panel time | ARCH §4.16, §6.7 and S2 acceptance: +3.36 s from the sign · MA: **W + 3.94** (the same beat, re-anchored on W) · BUILD `ui.json win.panelAt 3.36` | FLAG-S | MA. The key `win.panelAt` keeps its name but its anchor becomes W. The code and the value change together. |
| W-3 | Clear wave | ARCH §4.16, §5.7: ≈ 0.45 s, then the dots fade · MA §3.8: the front takes 0.45 s, 0.50 s in total, colour by radius | OK | MA details |
| W-4 | Firework rockets | ARCH §6.7: "two rockets rise and burst" · UI §2.7.1: "two firework rockets" · TOK `celebrate.logo` note: "2 rocket trails" (one frame, shot 049) · MA §5 row 12: **6** rockets launched at W + 1.60…2.75, bursts at W + 2.24…3.47 ([P3] win clip) | FLAG-W | MA (a clip beats a single frame). |
| W-5 | Celebration dim | ARCH §6.7: ≈ 90 % in 0.36 s · UI: 0.90, reached at W + 1.58 · MA: from W + 1.24, 0.34 s linear, to 0.90 | OK | — |
| W-6 | Logo frame | ARCH §6.7; UI §2.7.1; TOK `celebrate.logo`; MA §5: 46 · 294.9 · 307.9 · 232.2, centre (200, 411); the plate is widened for "ARROW" | OK | — |
| W-7 | Logo art | UI §2.1, §2.7.1: `logoArrowOut` as one image (306 × 236 master) · MA §15.4: split into parts (blue sign, 5 letters, arrow sign, "OUT!") for the slam | FLAG-W | MA (the slam animates the parts). UI-ART request. |
| W-8 | Tap to skip | ARCH §6.7; UI §2.7.1: any tap skips · MA §5: accepted from W + 0.41 to W + 3.94, with a click + the win haptic | OK | — |
| W-9 | Win panel content | ARCH §6.7; GP §9.2; UI §2.7.2: blue / red / purple panel; "Perfect!" always; Rewards; Continue; X | OK | — |
| W-10 | Hard / Super Hard tag ribbon | GP §9.2: text "☠ Hard Level ☠" / "☠ Super Hard ☠" · UI §2.7.2: text "Hard Level" / "Super Hard" + `iconSkull` art on each side | FLAG-W | UI. The skulls are art: ☠ is not in PCDisplay, so FontCoverageTests would fail. The strings are "Hard Level" and "Super Hard". |
| W-11 | X on the win panel = Continue | GP §9.2 (D); UI §2.7.2 (D) | OK | — |
| W-12 | Coins are not counted up on the panel | ARCH §6.7; GP §9.1; UI §2.7.2; MA §5 | OK | — |
| W-13 | Streak strip slide under the panels | UI §2.7.3: "slides up 0.13 s after the panel" · MA §5 row 16: starts W + 3.95 (panel + 0.01), 0.13 s easeOutCubic; the lit chip then moves in 0.31 s | FLAG-W | MA. UI's 0.13 s is the duration, not a delay. |
| W-14 | The win is silent | SPEC §5.13; ARCH §6.7, §7.2; MA §5, §11 | OK | — |
| W-15 | Post-win queue order | ARCH §8.4: win panel → Claw first-open screen and claims → Sky Jump progress → home; Rocket offer on home · SOC §4.8: (1) Sky Jump progress, (2) home, then claims, the Rocket lost screen, offers, the Streak list · GP §9.3: as SOC, + the rating prompt after L34 · MA §8.3: the home return A → B → C, then SOC §4.8 and the rating prompt · UI §2.2.7: the same | FLAG-S | SOC/GP/MA/UI. |
| W-16 | Home-return segments | MA §8.3 (V clip); UI §2.2.7 steps 1–5: Claw token → Streak strip → coin payout | OK | — |
| W-17 | Home dim during the return | UI §2.2.7 step 1: ≈ 50 % (D) · TOK2 `dim.homeReturn 0.50` (I) · MA A1/A7: 0.50, but only during segment A, the Claw token (V) | FLAG-W | MA. There is no dim on a plain payout (before L33, or with the Claw inactive). |
| W-18 | Claw token on home | UI §2.2.7: `iconHexArrow` at 64 pt, ≈ (198, 450) · MA A2: 56 pt at (198, 440) | FLAG-W | UI (geometry owner). |
| W-19 | Claw "+N" label | UI: white, outline `#505878` 2 pt, 25 pt (I) · MA A6: "+1" → "+m" at H + 0.88 | OK | UI look, MA timing |
| W-20 | Coin payout | ARCH §4.16, §6.4: "+N" at +0.25 s; 5 coins lift +0.80 → +1.36 (V vflows §6) · GP §9.1: "+N" over the LEVEL plate; 5 coins, N/5 each · UI §2.2.7: "+N" ≈ 36 pt, white, brown `#6B3A1E` 2 pt, centre ≈ (229, 484) (I, phone shots); `iconCoin` 34 pt to (112.7, 70) · MA segment C: label 30 pt, white, `#0B2A7A` outline at (196, 490); alone at H + 0.35; lift at C0 + 0.55; 0.22 s flights 0.085 s apart; `iconCoin` 30 pt to (112.7, 70) | FLAG-W | Timing: MA (≤ 0.1 s later than the video, so the coin cue's baked clinks line up). Look and position: UI (a phone inference beats the older video). The target point agrees. |
| W-21 | First home +120 (1000 → 1120) | ARCH §6.2; GP §10.3; UI §2.2.7; MA §8.3 | OK | — |
| W-22 | Claw bar count-up | MA §8.5 (V: ticks 0.057 s, n = min(7, m)); UI refers to MA | OK | — |
| W-23 | Arrow-pile refill when home returns from an event page | UI §2.2.8: Low → Half → Full + falling arrows, 1.2 s (D) · MA §8.1: the pile is static on an idle home (V; consistent) — but MA has no row or key for the refill | PENDING | MA owner: key it (e.g. `ui.json home.pileRefill 1.2`) or accept UI's 1.2 s as is. |
| W-24 | Rating prompt | ARCH D24, §6.10; GP §10.6; UI §2.21; MA §8.3: once, on home right after the L34 win | OK | — |

---

## 11 Fail chain, lives, economy, shop

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| X-1 | Fail chain order | GP §7.1 (V fail) and UI §2.6: Out of Time! (+30 sec, Add Time 900) or Out of Lives! (+3 Lives, Add Lives 900) → Continue? (streak or token; only when the multiplier is above x1) → Continue? (a life) → Level Failed! · ARCH §4.5: the time chain as V L47; for hearts-out, "Continue? Get 3 lives to keep playing!" (the July web build) · BUILD `failChain` = GP | FLAG-S | GP/UI: on v552, "Out of Lives!" replaced the web build's hearts-out Continue? (UI §2.6.4). |
| X-2 | Continue prices | ARCH (V; escalation PENDING); GP; UI; BUILD: 900 on every step, no escalation | OK | — |
| X-3 | Grants | ARCH `ContinueOffer.Grant`; GP (D); BUILD: Add Time +30 s; Add Lives → 3 hearts; later steps grant the same | OK | — |
| X-4 | Step B wording | GP §7.1; UI §2.6.3; SOC §4.7: "You will lose your streak!" while the Claw is not running; "You will lose %lld token and your streak!" while it runs (the number = the current multiplier) | OK | — |
| X-5 | Step B only when the multiplier is above x1 | GP; UI (V fail §1); BUILD `onlyWithStreak` | OK | — |
| X-6 | When the multiplier starts counting | GP §11.1: from the Streak Race unlock (L30); x1 before (D) · SOC §4.2: no unlock gate stated | OK | GP rule; SOC does not contradict it. |
| X-7 | Life refill interval | ARCH §4.8: ≈ 1200 s (I, PENDING) · GP §8.1: **1800 s**, one continuous clock (V economy ledgers) · UI §2.13.1 Support text: "every 30 minutes" · SOC §9 bench: "5, 20 min refill" · BUILD rules.json **1200** (EconomyRules' compiled default is 1800, and the file overrides it) | FLAG-W | **GP 1800. Fix `rules.json` now.** `EconomyRules.load` decodes the file's `lives` section, so the shipped file would give 20 min. The SOC bench text is stale; a rerun is optional. |
| X-8 | When a life is spent | ARCH §4.8: lost when the level is LOST, a win refunds nothing (V 5 → 4); C3 acceptance and mutations ("anchor on a win") · GP §8.1: taken when a level STARTS, refunded on a WIN (V ledgers; meta: 30:00 exactly from the level start) · UI §2.13.1: "Starting a level uses a life; winning gives it back" · BUILD Lives.swift = GP | FLAG-S | GP. The net count is the same, but the refill phase and the pill during play differ. The build already follows GP; ARCH's text and mutation names are stale. |
| X-9 | App killed mid-level | ARCH: a loss (D, PENDING) · GP: `lives.killIsLoss true` | OK | — |
| X-10 | Lives max; unlimited lives | ARCH §4.8; GP §8.1: max 5; unlimited grants stack `until = max(until, now) + d`; checked only at the level start | OK | — |
| X-11 | Lives pill states | GP §8.3; UI §2.2.2: Full · mm:ss · "Finished" for ≈ 1 s · ∞ mm:ss under an hour, "%lldh %lldm" above | OK | — |
| X-12 | 0 lives at Play or Try Again | ARCH §6.2 (Try Again uses the same gate, D); GP §8.2; UI §2.9: the More Lives popup (count "0") | OK | — |
| X-13 | More Lives offers | SPEC §5.18; GP §8.4; UI §2.9: Refill 900 (lives to 5); "+1 Live" → AdSlot; never granted in Release — **SUPERSEDED by SPEC.md 37(d): Refill is the only offer (A1)** | OK | — |
| X-14 | Start coins; rewards | ARCH §4.8; GP §9.1; BUILD: 1000; wins 20 / 60 / 100; the "Levels 1-4" session 80 | OK | — |
| X-15 | Session reward stored twice | LJ `sessions.json reward 80` · GP §15 `rules.json rewards.session["L1-4"] 80` (GP §17.1 #4: the session value wins) | FLAG-W (key) | Keep `sessions.json`. Drop `rewards.session`, or test that they are equal. |
| X-16 | Coins banked at the win, flown on home | ARCH §4.8 (D); GP §9.1 | OK | — |
| X-17 | Shop catalogue | GP §9.4; UI §2.12.2, §5 `shop.fakePrices`; TOK2 tuning: 1 special offer + 5 bundles + 6 coin packs; the same contents and US $ prices (0.99 … 99.99; coins 1.99 … 99.99); ids `com.manycode.arrowout.<id>` (ARCH); a11y `shop.product.<id>` (ARCH, UI) | OK | — |
| X-18 | Currency FakeStore shows | GP §9.4: the device region's price list (TL for region TR, else US $) (D) · UI §2.12.3: always US $ with "$" (D, for honesty; an open owner question) · UI `role.shopPrice`: "49,99 TL" measured on the phone (V) | FLAG-R | **GP.** The phone shows TL, and the "Test store: nothing is charged" chip already carries the honesty. The owner may choose UI's US $. |
| X-19 | Thousands separator | UI §2.12.2: a thin space, "1 000" (V EN on a TR phone) · GP §9.4 table titles: "1,000" | FLAG-W | UI (display format). GP's commas are table notation. |
| X-20 | Special Offer once per install | GP §9.4 (D); UI silent | OK | — |
| X-21 | What a purchase shows | UI §2.12.4: after 0.3 s the claim overlay ("Congratulations!", the coins, then boosters, then ∞), then coins fly to the header pill · MA §8.4: the pill number swaps at once + one sparkle (D) · GP §16.8: a "Purchase complete!" string (no place given) · ARCH §6.8: succeeds after 0.3 s | FLAG-W | UI (the screen-flow owner). MA reuses segment C for the fly. GP's "Purchase complete!" goes unused. |
| X-22 | Test-store chip | ARCH D18; GP §9.4; UI §2.12.3 (the first row of the scroll, 330 × 26 pt) | OK | TR text: S-11 |
| X-23 | Not enough coins | ARCH §8.4 (D); GP §7.1, §9.5; UI §2.6.6: the Shop opens over the popup (scrolled to Coins) and re-checks on return | OK | — |
| X-24 | No Restore row, no "Remove Ads" | GP §9.4 (V); UI §2.12.4 (V) | OK | — |

---

## 12 Boosters

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| K-1 | The two boosters | SPEC §5.10; ARCH §4.9; GP §6; UI §2.3.2: left `freeze` (hourglass), right `hint` (bulb) | OK | — |
| K-2 | Start stock | ARCH §4.8; GP §6 `economy.startBoosters`: 3 each | OK | — |
| K-3 | Freeze flight | ARCH `freezeTimer(10)` (I) · GP §6.2: `freezeSeconds 10`, `freezeFlight 1.5` (V boosters §2: ≈ 1.5) · MA §3.10.2: **1.6** (the frost and the countdown start at B + 1.60) · BUILD 1.5 | FLAG-W | MA 1.6 (timing owner). Update GP §15 and BUILD. The 10 s agrees. |
| K-4 | Freeze used before the first tap | GP §6.2: `freezeRunsBeforeStart false`; the 10 s wait for the first tap · MA §3.10.2: a timeline from B with no before-start case | RESOLVED (SPEC.md §5 ruling 30) | Suggested (MA owner): the tray and frost appear at B + 1.60 as usual, the countdown holds "10", and it starts with the first tap. |
| K-5 | Hint camera | GP §6.3: to **max zoom**, centred on one free arrow, ≈ 0.65 s ease-in-out (boosters §1) · MA §3.10.1: starts at B + 0.05, 0.80 s, `ease` cb(0.25, 0.1, 0.25, 1), to max zoom (the clip starts mid-move) · UI §2.3.4: "The board pans (at the current zoom)" | FLAG-W | Zoom to max (V boosters §1: 14.05 → ≈ 28 pt); UI §2.3.4 is wrong. Duration: MA's 0.80 s (the 0.65 s measurement started mid-move). |
| K-6 | Booster at 0 stock | GP §6.4: the badge shows "+"; a booster popup with the title, one line and a green "Buy ×3 [coin] 900" (`economy.boosterPack` {3, 900}) (D) · UI §2.10: a green "+" badge; a booster info popup + "Get more in the Shop!" + a "Shop" button → Shop (Bundles) (D) · ARCH §8.4: "the buy popup (PENDING)" · BUILD `EconomyRules.boosterPack` (C3 follows GP) | FLAG-W | GP (booster and economy rule owner; C3 already built it). UI supplies the panel geometry (the More Lives frame, §2.10) with GP's title, line and Buy button. The owner may switch to UI's variant by removing `boosterPack`. |
| K-7 | A booster is inert while its own effect runs | GP §6.1 (D); UI §2.3.2 (a freeze tap during a freeze is ignored) | OK | — |
| K-8 | Where the hint policy key lives | GP §6.3: `game.json hint.policy "unblocksMost"` (D) · ARCH §4.9, §4.14: `Solver.hintUnit` is C2 code in PathCore, which reads only `RulesTuning` (rules.json) | FLAG-W | ARCH (structure). Move the key to `rules.json boosters.hintPolicy`; the value is GP's. |
| K-9 | Hint look | GP §6.3; UI §1.5, §2.3.4; MA §3.10.1; TOK2: `#00DE00` (anti-aliased rim `#009100`); blinks twice, then stays green until tapped | OK | — |
| K-10 | Return to fit after the hinted arrow leaves | GP §6.3 (I); MA §3.10.1: 0.50 s easeInOut | OK | — |
| K-11 | Freeze tray frame | UI §2.3.3: 92.7 · 118.4 · 92.7 · 25.0 · MA §13.2: [93, 118, 92, 25] | OK | — |
| K-12 | Freeze countdown digit | UI §2.3.3: ≈ 14 pt, white face, navy outline ≈ `#0D2C9E` (I) · MA §3.10.2: "navy `#0C2A6B`-class GameText 16 pt" | FLAG-W | UI (look). |
| K-13 | Frost vignette | UI §2.3.3: edges `#6BD4F8` (sides) and `#60EFFB` (top, bottom); ≈ 27 pt deep at the sides, 53 pt at the top, 83 pt at the bottom; crack lines within 40 pt of the corners (V meta-065) · MA §3.10.3: `#6BD4F8` → white; ≈ 30 pt at the sides, 88 pt at top and bottom; a static full-screen PNG `fxFrostEdge` ([P3] meta-065) | FLAG-W | UI (colours and geometry; both measured the same shot). MA keeps the timing (in 0.20 s at B + 1.60, out in 0.30 s). |
| K-14 | Frost and ice art ids | UI §4.2: `iconStopwatchFrozen`, `fxFrostVignette` (code) + `frostCracks` (a 120 × 120 corner tile) · MA §15.4: `iconStopwatchIced`, `fxFrostEdge` (393 × 852 @3x PNG) | FLAG-W | UI's ids (art-plan owner). This also avoids a full-screen @3x PNG (≈ 12 MB decoded; ARCH R16). |
| K-15 | Flying hourglass | UI §2.3.3: ≈ 90 × 100 pt, starting at ≈ (190, 617) · MA §3.10.2: 94 × 100 pt at (192, 612) (`ui.json freeze.spawn`) | FLAG-W | UI geometry (≤ 5 pt). |
| K-16 | Using a booster never starts the timer | GP §6.1; UI §2.3.2 (V boosters §1-2) | OK | — |

---

## 13 Events and the social world

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| V-1 | Unlock levels | GP §11.3; SOC §1.3, D11; ARCH §4.10 (phone first appearances); UI (Claw L33, Weekly L50); BUILD social.json: Streak Race L30 · Claw L33 (its screen after the L32 win) · Sky Jump L40 · Weekly L50 · Rocket Race L55 | OK | — |
| V-2 | Multiplier steps | ARCH §4.10; GP §11.1; SOC §4.2; BUILD: x1 x5 x10 x25 x100 (cap); any failed attempt → x1; a paid continue keeps it | OK | — |
| V-3 | What steps the multiplier | ARCH §4.10: "a first-try win moves x1 → x5 …" · GP §11.1: any won attempt (V L47/L52: the retry's win at x1 stepped to x5) · SOC §4.2: "a won level" | FLAG-S | GP/SOC. |
| V-4 | Points per win (Streak Race, Claw) | GP §11.1; SOC §4.2 (I strong); ARCH: "levels × multiplier" (I): the multiplier lit before the win | OK | filled |
| V-5 | Streak Race group size | ARCH ◆ `RivalProvider.streakRace` comment: "5 rows" · SOC §4.4, D13: 20 players (D) · UI C7: the phone lists **50** rows (V meta-045..052) · BUILD social.json: 49 bands + the player = 50 ("phone v552: a 50-row ranking") | FLAG-W | Phone: 50 (already in the build). The SOC §4.4 text and the ◆ comment are stale. |
| V-6 | Weekly group | SOC §4.3, D12: 50 ("group size UNKNOWN, ≥ 10"); front-loaded arrivals · UI C7: a **10**-row group (V meta-013..015) · BUILD social.json: a 10-player group, "complete when the player joins" | FLAG-W | Phone: 10 (build). The SOC text is stale. Follow the build's arrival model. |
| V-7 | Streak Race prizes | SOC §4.4: 2000 (I) / 1000 / 500 / 100 for ranks 4–10 (7–10 D) · UI C7: the same · ARCH §4.10: plates 1000/500/100/100/100 (ranks 2–6 on shot 203) | OK | ARCH lists the ranks visible on one shot. |
| V-8 | Weekly podium prizes | ARCH, GP, SOC, UI: 2000 / 1000 / 500 | OK | — |
| V-9 | Claw thresholds | ARCH §4.10: "1, 200, 300, 400, 500 …" · GP §11.2: 1/200/300/400/300/500/**500** (V 1–7), then 600, 600, 700, 700, 800, 800, 1000, 900, 1000, 1000, 1100, 1200, 1500 (D) · SOC §4.7, D16: 1/200/300/400/300/500 (V), then **400**, 500, 400, 600, 500, 700, 600, 800, 700, 900, 800, 1000, 900, 1200 (D) · BUILD EconomyRules = GP | FLAG-W | GP. Step 7 = 500 is VERIFIED and contradicts SOC's 400; GP owns the ladder (GP §17.1 #6 asks SOC to point here). ARCH's 5th step "500" is stale (V 300). |
| V-10 | Claw rewards | GP §11.2 (1–7 V phone; 8–20 from the ladder art) · SOC §1.1 (1 ∞30m, 2 100, 3 ∞30m, 4 200, 5 ∞1h, 6 bulb ×1, 17 bulb ×1, 18 600, 19 ∞6h, 20 10000) · ARCH §4.10 (the same known points) | OK | — |
| V-11 | Claw period | GP §11.2; SOC §4.7; ARCH: weekly, ending Monday 07:00 UTC; overflow carries; claims on the next home | OK | — |
| V-12 | Event day and week | ARCH §4.11 inv. 4; SOC §1.2, D2: days start 07:00 UTC; weeks start Monday 07:00 UTC · GP §12.5: `weeklyEnding` fires Monday 05:00 UTC | OK | — |
| V-13 | Countdown format | SOC §4.1; GP §16.6; UI §3: "Xd Yh" at a day or more, else "Xh Ym", floored | OK | TR: S-32 |
| V-14 | Rocket Race | ARCH §4.10; SOC §4.5; UI §2.17: 5 lanes; 4 rivals; stage 1 = beat 5 levels; joining grants ∞30m; stage-1 prize 500 + ∞45m (V); stages 7 / 9 and prizes 1000 + ∞90m / 2000 + ∞3h (SOC D14) | OK | — |
| V-15 | Rocket text depends on N | SOC §10: "Beat %d Levels before others …" / "Beat %d levels …" · UI §3: the literal "Beat 5 Levels …" / "Beat 5 levels …" | FLAG-W | SOC: use `%lld`. Stages 2 and 3 need 7 and 9. |
| V-16 | Sky Jump | ARCH (5, 7; 714) · SOC §4.6 · UI §2.18 ("5/7/9 from SPEC-social"): 5/7/9 first-try wins; pools 5000 / 7000 / 10000; 100 players; share = floor(pool/W) (5000/7 = 714); a run lasts 24 h; a fail ends it; a new run after 30 min, at most 2 stage-1 runs a day | OK | — |
| V-17 | "Finding players on your level." | SOC §4.6; UI §2.18; MA §9: 29 → 100 over ≈ 1.5 s; a fan of 14 portraits | OK | — |
| V-18 | Board metrics | ARCH §4.11; SOC §3.1; UI §2.15: World ranks by level; Country opens at the player's row; Weekly = levels won since joining | OK | — |
| V-19 | World list | SOC §3.3, D9; UI §2.15.4; BUILD `lists.worldTop 100`, `window 10`: ranks 1–100 + "• • •" + R−10…R+10 | OK | — |
| V-20 | Country list shown continuously up to rank | SOC §3.3, D9: R ≤ 300 · BUILD social.json `countryContinuousUpTo 600` | FLAG-W | SOC (model owner), unless SOC1 had evidence (the phone's Turkey #455, PLAN 07:45). The orchestrator confirms with SOC1; the spec and the file must agree. |
| V-21 | Pinned player row | SOC §3.3: "A pinned mini-row of the user at the bottom is NOT in the original — don't add one" (World; V2) · UI §2.15.3, §2.15.5: a pinned row on Weekly (V meta-014, meta-111) and Country (V meta-027); World has the "Bottom" JumpPill (V meta-019..024) | FLAG-W | UI (phone). SOC's rule holds for World only. |
| V-22 | Country "Top" pill | SOC (V2); UI (D: kept on the v552 skin) | OK | — |
| V-23 | Country tab label | ARCH §6.9: `Locale.current.region`, localised · SOC §2.3, D5: `homeCountry`, frozen at the first launch · UI §2.15.1: the frozen home country + a short-name table | FLAG-W | SOC/UI (frozen). |
| V-24 | Avatar range | SPEC §5.12: the phone's portrait set; the older arrow-character set is not shipped · UI §2.14.2, TOK2: 0 default + 8 portraits (an index table) · GP §13: default + 8 · ARCH §6.9: "9 of ours + the default silhouette" · SOC §2.8: "1…14 = `avatarGreen … avatarWalkie`", uniform over 14 · BUILD `Population.swift`: `1 + below(…, 14)` | FLAG-W | SPEC §5.12: **range 0…8** (UI's table). SOC1 must draw from 1…8 in the shipped v552 model. Today simulated players can carry avatars 9–14, which have no art. ARCH's "9 + default" is stale. |
| V-25 | Default names | ARCH inv. 6; GP §13; SOC §2.8; UI: `player_` + 7 lowercase letters/digits; blocklists | OK | — |
| V-26 | Username rules | GP §13: 3–15 characters after trimming; letters of any script, digits, "_", "." and single inner spaces; errors "Name must be 3-15 characters" / "This name is not allowed" · UI §2.14.3: 3–16; letters, digits, "_"; the field shakes + toast "This name is not available." · SOC §2.8: 3–16; letters of any script, digits, "_"; shake + red outline | FLAG-R | **SOC** (names and blocklist owner; world names go up to 16): 3–16 characters, letters of any script, digits, "_"; shake + red outline + GP's message strings (edited to "3-16"). |
| V-27 | Social clock | ARCH inv. 5 (PENDING refinement); SOC §5: `max(wall, highWater)`; setting the clock back freezes the world; forward jumps accepted; a one-time rebase after 30 days | OK | filled |
| V-28 | What drives the world | ARCH §4.11 inv. 1: "Deterministic from (installSeed, SocialTime, ledger)"; D10: "(install seed, labels, time)" · SOC §0 rule 1: ONE shared world from `WORLD_SEED`; the install seed only picks the player's groups and rivals · BUILD `SocialModel.worldSeed` = SOC | FLAG-S | SOC (model owner). It is still deterministic. |
| V-29 | Social query budgets | ARCH §4.11, §10.2: a 50-row page ≤ 2 ms on the device, ≤ 1 ms macOS `-O` · SOC §3.2: world rank ≤ 8 ms, top-100 ≤ 10 ms, country ≤ 2 ms, neighbours ≤ 3 ms (device, 3-year world), all off the main thread | FLAG-R | ARCH owns budgets. **Recommended binding rule:** 0 ms on the main thread (every query off-main, snapshots published). SOC's per-query numbers become the SOC1 bench gate. ARCH's "≤ 1 ms on macOS" for a World page is unlikely at a 3-year world. |
| V-30 | Social file layout | ARCH §3.2: `PathCore/Social` (SocialClock, SocialHash, SocialCalendar, Population, Names, Leaderboards, RaceBots, SocialState) + `PathCore/Events` (C3: StreakRace, RocketRace, SkyJump, ClawChallenge, WeeklyContest) · SOC §7: World, WorldQueries, Matchmaking, GroupContest, RocketRace, SkyJump, ClawChallenge, WinStreak and an actor `SocialService`, all under Social/ · BUILD follows ARCH | FLAG-W | ARCH (file ownership). |
| V-31 | Live updates | SOC §3.4; MA §9; BUILD `refreshSeconds 5`: every 5 s; values count up in 0.30 s; rows slide in 0.35 s | OK | — |
| V-32 | Trophy "!" badge | SOC §3.4 (the trigger, D); UI §2.2.6 (the look); MA §9 (the pop) | OK | — |
| V-33 | Streak Race list auto-shows | ARCH §8.4; SOC §4.4: on an idle home (the first home of the day; after a rank drop, at most once per 30 min) | OK | — |
| V-34 | Streak strip under the panels | GP §7.1, §11.3; UI §2.7.3; SOC: from L30 | OK | — |
| V-35 | Profile stats | ARCH §6.9; SOC §1.1: two stats (First Try Wins, Weekly Contest Wins; V2) · GP §13; UI §2.14.1: **six** (V meta-002, v552) | FLAG-S | GP/UI (phone). |

---

## 14 UI chrome, dims, pages, popups

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| U-1 | Popup dims | ARCH §6.6 (V uim); UI §1.3; MA §6.2; TOK and TOK2 `dims`; BUILD: popup 0.90 · unlock 0.90 · outOfTime 0.94 (also Out of Lives!) · skyMatch 0.96 | OK | — |
| U-2 | New dims | UI §1.3, §5; TOK2: info 0.95, weeklyTutorial 0.92, overPage 0.63, homeReturn 0.50 · ◆ ShellContract `DimToken` = popup, unlock, outOfTime, skyMatch, none | FLAG-R (contract) | Three popup dims need new `DimToken` cases (`info`, `weeklyTutorial`, `overPage`); an additive change. `homeReturn` is not a popup (S3 draws it). |
| U-3 | Continue? / Quit band | TOK `continueStreak.band`: 0 · 213.5 · 393 · 424.7 (rail `#FFC400`, field `#FFB600`) · UI §1.6.7 and TOK2 `corrections.band`: 0 · **233.2** · 393 · 404.8 (Quit 234.2); rails `#00B4FF`, field `#226DF5`, a cream strip | FLAG-W | UI/TOK2 (newer; TOK's frame included the X's ring). |
| U-4 | Where the X sits on Continue? | UI §1.6.3: "Continue/Quit band (362.3, 241.0)" · UI §2.6.3 and TOK `continueStreak.close`: (362.5, 237.4) on shot 014 · UI §2.5 Quit: (362.3, 241.2) on meta-075 | FLAG-W | Use each popup's own measurement: Continue? 237.4 (shot 014), Quit 241.2 (meta-075). §1.6.3's shared value is a slip. |
| U-5 | Settings: page or popup | ARCH §6.4 (gear → Settings popup), §6.6 `PopupID.settings` (S1 `SettingsPopup`) · GP §12.1: "Settings popup" (its contents match the page) · MA §6.2: listed among the instant popups · UI C1: a full-screen page (V meta-029..037) · ◆ ShellContract: `Screen` has no settings case | FLAG-R (contract) | **Recommended:** UI's page look, delivered through the existing `PopupID.settings`, rendered full-screen with `DimToken.none`. No contract change; `-pc.go settings` keeps working. The alternative is a new `Screen.settings` (a ◆ change). |
| U-6 | Support, Terms, Privacy | GP §12.2: "Support" opens the Mail composer to anycodeapps@gmail.com (subject "%@ Support"; body "Please describe…", "Version : %@", "Level : %lld" — the original's shape, V meta §4); Terms and Privacy are offline pages with GP §16.10's texts · UI §2.13.1: Support is an offline Help page, with "Contact Us" only if `Brand.supportEmail` is set (nil by default); "Terms of Use" and "Privacy Policy" pages with different texts · ARCH §6.6: "honest offline states (PENDING-ui)" | FLAG-R | **Recommended:** GP's behaviour (1:1 with the VERIFIED original: Support opens Mail) and GP's texts (strings owner), shown in UI's page layout (the §2.13.1 card, 17 pt body). The owner confirms the address: the support-mail-button rule is suspended for this job (PLAN PRECEDENCE). `Brand.supportEmail` would touch the frozen, LEAD-owned `Brand.swift`, so use a `game.json support.email` key instead. |
| U-7 | Music button | GP §12.1: default OFF; "stores its state only" · UI §2.13: "ours toggles `settings.music` (default OFF)" · MA MA2: inert — shows OFF; press + click; no state change (V meta §4: inert on 4 attempts) · ◆ `PlayerState.Settings.music` defaults to true · BUILD `music.enabled false` | FLAG-R | **Recommended:** MA2 (VERIFIED 1:1). The PlayerState default then no longer matters, but it should still read false: G2 writes false at the first launch (GP §17.1 #2), with no contract change. Its a11y value is always "off". The owner may prefer to hide the button. |
| U-8 | Settings defaults | GP §12.1; MA §11.4; meta (the owner's state): Sound ON, Music OFF, Haptic ON, Notifications ON · ◆ PlayerState: music = true | FLAG-W | see U-7 |
| U-9 | Pause panel toggles | ARCH §6.6; GP §12.1; UI §2.4: Sound + Haptic only (no Music) | OK | — |
| U-10 | Quit Level? container | ARCH §6.6 `quitLevel` (content only) · UI C2: the full-width band popup (V meta-075/092) · BUILD `ui.json frames.quit` = the Level Failed panel | FLAG-W | UI. BUILD is stale; UI §5 gives the frames. |
| U-11 | Quit → Level Failed directly (no offers) | ARCH §8.4; GP §7.2 (V fail §5); UI §2.5 | OK | — |
| U-12 | Out of Lives! popup | UI §2.6.2 (V meta-088); GP §7.1 step A′ | OK | ARCH stale per X-1 |
| U-13 | Home z-order | ARCH §6.4: scene → characters → LEVEL / plate / Play → top bar → Claw → nav → payout · UI §2.2.1: backdrop → scientist → console → arms → platform → capsule → pile → LEVEL / Play → **workers** → top bar … (V scene proof) | FLAG-W | UI: the workers sit above the Play frame; the scientist sits behind the console. |
| U-14 | Event badge column | UI §2.2.4 (V), TOK2 layout: Streak, Rocket, Sky Jump from the top; slot tops 190.8 / 293.6 / 390.3 · ARCH §6.4: the same three, no order given | OK | — |
| U-15 | Nav tabs | ARCH §6.1, §6.4: shop · home · leaderboard; Home raised · UI C8: the raised tab moves with the selection (V meta-012/013) · BUILD: `home.navHomeTab` only | FLAG-W | UI (C8). |
| U-16 | Arrow pile | ARCH §6.4: `homeArrowPile{Full,Half,Low}`, meaning PENDING · UI C4: full at rest + a refill animation · MANIFEST note: "by progress" | OK | filled (UI) |
| U-17 | Silhouette border | ARCH §5.6: not drawn unless SPEC-ui finds it · UI C6: absent on v552 | OK | filled |
| U-18 | Loading label colours | TOK `text.loading.label`: `#CCCCCC` face, `#681E1A` outline (measured under the iOS alert) · UI C3, TOK2: `#FFFFFF`, `#82251F` | FLAG-W | UI (C3; the dim ratio is exact). |
| U-19 | Launch colour | ARCH `LaunchBackground` (PENDING-ui) · UI §1.8: `#ABA0D8` (D) | OK | filled |
| U-20 | Close button red | TOK palette `close.red` `#FF2D2E` (`continueStreak` `#FF2E2F`, `outOfTime` `#FF2A2A`) · UI §1.6.3: face `#FF3B3C` + the rim and ring recipe | FLAG-W | UI (the newer full recipe; TOK's values are single 7 × 7 medians). |
| U-21 | Ribbon titles | SPEC §5.14 (≈ 1100 pt radius, min scale 0.7); UI §1.4, §1.6.5; TOK2 layout: max 49 pt, box 228 pt, floor 0.70 | OK | — |
| U-22 | Device adaptation | SPEC §5.14 (scale popups with width below 393); ARCH §6.12; UI §1.1; TOK2 layout: `s = min(1, W/393)`, no upscale; top, bottom and centre anchors | OK | — |
| U-23 | HUD tier colours | SPEC §5.10; ARCH §6.5; GP §10.5; UI §2.3.1; TOK: the Level tab, back and pause are blue / red / purple; the timer pill is always blue; no "Hard Level" tag in the HUD | OK | — |
| U-24 | Home Hard / Super Hard look | ARCH §6.4; GP §10.5; UI §2.2.5: red / purple Play and LEVEL plate + a "Hard Level" / "Super Hard" ribbon | OK | — |
| U-25 | Toast | UI §2.20 (look, D); ARCH §6.6 `ToastCenter`: one at a time, the newest replaces | OK | — |
| U-26 | AdSlot | SPEC §5.18; GP §8.4; UI §2.20: "video not available" → a toast; no reward in Release — **SUPERSEDED by SPEC.md 37(d): no AdSlot (A1)** | OK | copy: S-20 |
| U-27 | Weekly L50 tutorial | GP §10.7; SOC §1.1; UI §2.15.7; ARCH `PopupStyle.inputLock`: dim 0.92 with a hole over the trophy tab; only the tab takes input | OK | DimToken: U-2 |
| U-28 | Edit Profile save | ARCH ◆ `EditProfileResult.saved(avatar: Int)` · UI §2.14.2: "Save writes name + avatar" | FLAG-R (small) | The result type has no name. **Recommended:** the popup writes the name itself through `PlayerStore` (no ◆ change). |
| U-29 | Username popup trigger | ARCH §6.9; GP §13; SOC §1.1; UI §2.14.3: opening Profile with the default name shows it; not forced | OK | — |
| U-30 | Reserved GlossyChrome names versus new SHELL components | ARCH §6.11: `SegmentTabs`, `RankRow`, `RaceBar`, `PillToggle`, … are reserved for UI-ART's GlossyChrome · UI §4.2: "Not art (SwiftUI/code, SHELL): PageHeader, SegmentTabs, JumpPill, SquareToggle…" | FLAG-W | ARCH: `SegmentTabs` stays a GlossyChrome name (UI-ART); SHELL must not define it. Give each new name one owner before S2/S3 (UI §1.6: BandPopup, PageHeader, PageBackground, SquareToggle, JumpPill, TimerChip, ChevronChips, AvatarFrame, PlusBadge, NewsBadge, InfoButton). Suggested: chrome pieces to UI-ART, screen containers to SHELL. |
| U-31 | More Lives a11y id | ARCH §9.8: `popup.<PopupID>` → `popup.noLives` · UI §6: `popup.moreLives` | FLAG-W | ARCH: `popup.noLives`. |

---

## 15 Audio and haptics

| ID | constant | values by file | status | ruling |
|---|---|---|---|---|
| A-1 | Engine | ARCH §7.1; MA §11.4; BUILD audio.json and AudioContract: buses `sfx` and `music`; `.ambient` session; 0.005 s IO buffer; 8 voices; started at boot, never stopped in play | OK | — |
| A-2 | SoundID list | ARCH §7.4 and ◆ AudioContract: uiClick, coinCollect, unlockChime, tapTick · MA §11.2, §15.1: + clawToken, clawMerge, clawTick, clawComplete, streakPop (V v552 home-return cues) | FLAG-R (contract) | **Accept the additive change.** Fallback if refused (MA §15.1): the home Claw/Streak cues stay silent. |
| A-3 | MusicID | ARCH, ◆, MA §11.5: `home`, `level` stay; nothing is rendered; A1's tools skip them while `music.enabled` is false | FLAG-R (small) | **Accept MA's route:** A1 changes its own tools; no contract change. |
| A-4 | Music | SPEC §5.13: unknown, a gap-filler clip decides · MA MA2, §11.5: none (V: the button is inert; no loop was ever heard) · BUILD `music.enabled false` | OK | filled (MA) |
| A-5 | Tap sound | SPEC §5.4; ARCH §7.2 (open); MA MA3; BUILD `cues.arrowTap ""`: none by default; `tapTick` is rendered but unmapped | OK | The owner question stays open. |
| A-6 | uiClick recipe | ARCH §7.2: a 380 → 300 Hz glide + a 3 ms noise burst, 30 ms, −6 dBFS · MA §11.3: 35 ms, peak −7.5 dBFS, 390 → 300 Hz (V v552: −7.6 dBFS, 20 ms above −20 dB) | FLAG-S | MA. |
| A-7 | Which releases click | ARCH §7.2: "any UI button released; celebration skip" · UI §1.7 and MA §6.1, §11.2: every button except the win panel's Continue (V: it is silent) | FLAG-S | MA/UI. |
| A-8 | Haptic enum | ARCH §7.4 and ◆: tap, bumpContact, fail, clear, win, burst · MA §15.1: + heartLost, button, booster, coinLand | FLAG-R (contract) | **Accept the additive change**, with the default rows in ◆ `Tuning.swift` (MA §15.1). |
| A-9 | Haptic map | ARCH §7.3: tap `.light` 0.7; bump contact `.rigid` 1.0 (it also stands for the heart loss); fail `.warning`; clear `.medium` 0.8; win `.success`; burst `.soft` 0.6; UI buttons none · MA §12.1: tap `.rigid` 0.70; heartLost `.error`; bumpContact (no heart lost) `.heavy` 0.85; fail `.warning`; clear `.medium` 0.80; win `.success`; burst `.medium` 0.65; button `.light` 0.50; booster `.medium` 0.60; coinLand `.soft` 0.45; one per frame, by priority · BUILD audio.json = ARCH | FLAG-S | MA (the intensity owner). The 4 new rows need A-8; the fallback is MA §15.1. |
| A-10 | coinCollect and unlockChime | ARCH §7.2; MA §11.2-11.3: coinCollect 2.9 s with 5 baked clinks; unlockChime 2.2 s at the overlay's first frame | OK | — |
| A-11 | Cue keys | BUILD audio.json (ARCH): uiButton, celebrationSkip, homePayout, unlockOverlay, arrowTap · MA §13.3: + dismissTap, clawToken, clawMerge, clawTick, clawComplete, streakPop | OK | additive |
| A-12 | tapTick gain | BUILD 1.0 · MA §11.4: 0.6 | FLAG-W | MA (it is unmapped anyway). |
| A-13 | Sound on the visual's frame | ARCH §7.1, §8.2; MA §11.2: `scheduleBuffer(at: nil)` inside the same handler, before the CA commit | OK | — |

---

## 16 Strings

Measured fit (§0; shipped font, UI §3 boxes). "LOW" = below the 0.70 floor.

| ID | string (EN) | values by file | fit | status | ruling |
|---|---|---|---|---|---|
| S-1 | Tap to move! (TR) | GP "Dokun ve oynat!" · UI "Dokun ve çıkar!" · MA "Hareket ettirmek için dokun!" | 1.00 · 1.00 · **0.62 LOW** | FLAG-W | GP (strings owner; it fits). |
| S-2 | Quit Level? (TR) | GP "Seviyeden Çık?" · UI "Çıkılsın mı?" | **0.65 LOW** · 0.85 | FLAG-W | UI (GP's fails the floor). |
| S-3 | More Lives (TR) | GP "Daha Fazla Can" · UI "Ekstra Can" | **0.63 LOW** · 0.90 | FLAG-W | UI |
| S-4 | Edit Profile (TR) | GP and SOC "Profili Düzenle" · UI "Düzenle" | **0.65 LOW** · 1.00 | FLAG-W | UI |
| S-5 | Time Freeze (TR, 228 pt ribbon) | GP "Zaman Dondurucu" · UI "Dondurucu" | **0.53 LOW** · 0.88 | FLAG-W | UI |
| S-6 | Username popup title (EN) | GP and SOC "Enter Username" (the V2 original) · UI "Username"; TR "Kullanıcı Adı" in all three | **0.60 LOW** · 0.97; TR 0.76 | FLAG-R | **Recommended: UI's "Username".** The v552 look of this popup was never captured (UI draws it as a ribbon), and the V2 wording cannot fit that ribbon at 0.70 or more. |
| S-7 | Out of Time! (TR) | GP "Süre Doldu!" · UI "Süre Bitti!" | 1.00 · 1.00 | FLAG-W | GP |
| S-8 | Continue? (TR) | GP "Devam?" · UI "Devam mı?" | 1.00 · 0.89 | FLAG-W | GP (both fit). |
| S-9 | Time to next live: (TR) | GP "Sonraki cana kalan süre:" · UI "Sonraki cana kalan:" | 0.93 · 1.00 | FLAG-W | GP |
| S-10 | Finished (lives pill, TR) | GP "Bitti" · UI "Doldu" | 1.00 · 0.99 | FLAG-W | GP. The EN "Finished" itself needs 0.72 in the 52 pt box. |
| S-11 | Test store: nothing is charged (TR) | GP "Test mağazası: hiçbir ücret alınmaz" · UI "Test mağazası: ücret alınmaz" | 1.00 · 1.00 | FLAG-W | GP |
| S-12 | Terms (button, TR) | GP "Koşullar" · UI "Şartlar" | 1.00 · 1.00 | FLAG-W | GP |
| S-13 | Terms / Privacy page titles | GP "Terms" / "Privacy" · UI "Terms of Use" / "Kullanım Şartları" (0.74), "Privacy Policy" / "Gizlilik Politikası" (0.76) | — | FLAG-W | GP (strings owner; goes with U-6). |
| S-14 | Rocket Race Wins (TR) | GP "Roket Yarışı Zaferleri" · UI "Roket Yarışı Birincilikleri" | 1.00 · 0.99 | FLAG-W | GP |
| S-15 | Sky Jump (TR name) | SOC "Gökyüzü Zıplayışı" (title) · GP "Gökyüzü Zıplayışı Zaferleri" (stat) · UI "Gökyüzü Atlayışı" / "… Atlayışı Zaferleri" | title: **0.68 LOW** (SOC) · 0.70 (UI); stat: 0.92 · 0.94 | FLAG-W | UI's "Atlayışı" everywhere. The event name must fit its title box and read the same across the title, the stat and the copy. |
| S-16 | Pipe card (TR) | GP "BORUYU kırmak için okları içinden geçir!" · UI "Kırmak için okları BORUDAN geçir!" | 1.00 · 1.00 (2 lines) | FLAG-W | GP |
| S-17 | Elevator card (TR) | GP "ASANSÖRÜ çalıştırmak için üstündeki tüm okları temizle!" · UI "Çalıştırmak için ASANSÖRDEKİ tüm okları temizle!" | 0.80 · 0.90 | FLAG-W | GP (it fits). |
| S-18 | "OFF" key collision | the toggle's "OFF" = "KAPALI" (GP §16.3, UI `toggle.off`) · UI's shop seal splits into "90%"/"%90" + "OFF"/"İNDİRİM" · GP: one string "90% OFF" / "%90 İNDİRİM" | — | FLAG-W | A catalogue keyed by the English literal (ARCH §6.11; `build.py` rejects duplicates that disagree) cannot hold "OFF" twice. Give the seal keyed strings (e.g. `shop.seal.off`), or use GP's single "90% OFF" drawn in two runs. **SUPERSEDED (ruling 38 / T1 / A1): the seal is the one-run key "STARTER" on a ribbon; "90% OFF" is gone.** |
| S-19 | +1 Live | GP: one string "+1 Live" / "+1 Can" · UI: "+1" drawn inside the heart art + the label "Live" / "Can" | — | FLAG-W | UI layout: the string is "Live" / "Can"; GP's key goes unused. **SUPERSEDED by SPEC.md 37(d): no "+1 Live" button (A1).** |
| S-20 | AdSlot toast | GP "Video not available" / "Video şu anda kullanılamıyor" · UI "Video not available right now." / "Video şu an kullanılamıyor." | — | FLAG-W | GP (strings owner; SPEC §5.18 wording). **SUPERSEDED by SPEC.md 37(d): no AdSlot toast (A1).** |
| S-21 | Not enough coins | GP "Not enough coins" / "Yeterli altın yok" · UI "Not enough coins!" / "Yeterli altın yok!" | — | FLAG-W | GP |
| S-22 | Purchase pending | GP "Purchase pending" / "Satın alma bekliyor" · UI "Purchase pending." / "Satın alma beklemede." | — | FLAG-W | GP |
| S-23 | Rejected username | GP "This name is not allowed" / "Bu isim kullanılamaz"; "Name must be 3-15 characters" · UI toast "This name is not available." / "Bu isim kullanılamıyor." | — | FLAG-W | GP's strings, with "3-16" (V-26). |
| S-24 | Booster popup copy | GP "Freeze the timer for 10 seconds!" / "Süreyi 10 saniye dondur!"; "Find an arrow that can move!" / "Çıkabilen bir oku bul!"; "Buy" · UI "Stops the timer for 10 seconds!" / "Süreyi 10 saniye durdurur!"; "Shows you an arrow that can move!" / "Çıkabilecek bir oku gösterir!"; "Get more in the Shop!"; "Shop" | GP lines 1.00 (270 pt × 2 lines) | FLAG-W | Follows K-6 (GP). |
| S-25 | Hard ribbon | GP "☠ Hard Level ☠" · UI "Hard Level" + art | — | FLAG-W | UI (W-10) |
| S-26 | Top pill (TR) | SOC "Başa" · UI "Yukarı" (pairs with "Aşağı" for "Bottom") | 1.00 · 1.00 | FLAG-W | UI (a listed, deliberate difference; SOC defers to the strings lane). |
| S-27 | Sky Jump share (TR) | SOC "Ödülü %d diğer kazananla paylaşıyorsun!" · UI "Ödülü %lld kazananla daha paylaşıyorsun!" | 1.00 · 1.00 | FLAG-W | SOC's wording (with `%lld`). UI does not list this as a deliberate difference. |
| S-28 | Sky Jump offer (TR) | SOC "%d seviyeyi ilk denemede art arda geç, sonraki aşamalara ilerle!" · UI "%lld seviyeyi art arda ilk denemede geç ve sonraki aşamalara ilerle!" | — | FLAG-W | SOC's wording (`%lld`). |
| S-29 | "Advance to next stages for greater prizes!" (TR) | SOC "Daha büyük ödüller için sonraki aşamalara ilerle!" · UI (`rocket.tut4`, `sky.tut4`) "… sonraki aşamalara geç!" | — | FLAG-W | SOC |
| S-30 | Rocket offer (TR) | SOC "Kazanmak için %d seviyeyi herkesten önce geç ve daha büyük ödüller için ilerle!" · UI "5 seviyeyi herkesten önce geç, kazan ve daha büyük ödüller için ilerle!" (a listed rewording) | 0.92 · 1.00 | FLAG-W | UI's wording (listed), but with `%lld` in place of the literal 5 (V-15). |
| S-31 | Rocket race won (both NEW) | SOC "You won the race!" / "Yarışı kazandın!" · UI "You won the race! Claim your amazing rewards!" / "Yarışı kazandın! Harika ödüllerini al!" | 1.00 | FLAG-W | UI (the owner of that new screen; mirrors the lost-race sentence). |
| S-32 | Countdown units in TR | GP "%lldg %lldsa", "%lldsa %llddk", "%lldsa", "%llddk" · UI §3: keep "d/h/m" in TR (D: "would not fit") | measured: "1sa 20dk" in the lives pill (18.9 pt, 52 pt box) **0.66 LOW**; "6g 23sa" in the Claw chip 0.82; "23sa 59dk" on a badge 0.78 | FLAG-W | UI: the measurement shows GP's TR fails the lives pill. Use one format everywhere. |
| S-33 | Format specifiers | SOC §10: `%d` everywhere · GP, UI: `%lld` (Swift `Int`) | — | FLAG-W | `%lld` |
| S-34 | Token line argument | GP, UI, SOC: "You will lose %lld token and your streak!"; UI mentions a positional `%1$lld` for TR | — | OK | There is one argument, so the positional form is optional. |
| S-35 | Door card | SPEC §5.19; GP §16.2; UI §2.8; LJ (EN): "Door!" / "Unlocked!" / "Collect the KEY to open the DOOR!" — TR "Kapı! / Açıldı! / KAPIYI açmak için ANAHTARI topla!" | 1.00 | OK | — |
| S-36 | Every other string shared by two or more files | Loading, Level %lld, Levels 1-4, Level 1-4, Unlocked!, the Linked / Box cards and titles, Pipe!, Elevator!, Paused, Sound, Haptic, ON, OFF (toggle), Resume, Quit, You will lose a life!, +30 sec, Add Time, Out of Lives!, +3 Lives, Add Lives, You will lose your streak!, Play On, Level Failed!, Try Again, Perfect!, Rewards:, Continue, Hard Level, Super Hard, Play, LEVEL, Full, Refill, Congratulations!, Tap to Claim, Tap to Continue, Hint, Shop, the shop sections and bundle names, Popular, Best Value, Settings, Notifications, Music, Support, Privacy, Profile, General Stats, First Try Wins, Weekly Contest Wins, Streak Race Wins, Claw Challenge Wins, Create your username:, Save, and the leaderboard / Weekly / Streak / Claw / Rocket / Sky strings not listed above (UI §3 = SOC §10) | — | OK | the same EN and TR in every file |

---

## 17 Art and MANIFEST ids

| ID | id | values by file | status | ruling |
|---|---|---|---|---|
| M-1 | `unlockIconBox` | GP §10.4, §17.1; UI §2.8, §4.2; LJ unlocks `icon` · MANIFEST: missing | OK | All agree: a UI-ART request. |
| M-2 | Box art | O-21 | FLAG-W | UI (the slab in code + `boxRing`) |
| M-3 | Door sizes | O-23 | FLAG-R | — |
| M-4 | Frozen stopwatch and frost | K-14 | FLAG-W | UI's ids |
| M-5 | `heartHUDHalves`, `heartHUDLost` | MA §3.4.5; UI §4.1 · MANIFEST: present | OK | — |
| M-6 | Avatars | UI §2.14.2 and TOK2 `avatars`: index 0–8 = avatarDefault, Walkie, CapGlasses, Detective, Burger, Scientist, Party, BoxHead, Notebook (MANIFEST lacks `avatarBurger` and `avatarNotebook`; the files exist) · SOC §2.8: "avatarGreen … avatarWalkie" (14) | FLAG-W | UI (see V-24). Add the 2 ids to the MANIFEST. |
| M-7 | `logoArrowOut` parts | W-7 | FLAG-W | split it |
| M-8 | Green flag roll | UI §4.2: `iconFlagRoll` (missing; B3, 36 × 41) · MA §15.4: "the green flag-roll icon … (if `iconCheckeredFlag` is not it)" | FLAG-W | UI's id `iconFlagRoll`: one asset for the Streak score chip, the Profile stat and the home-return flight. |
| M-9 | Curtain art | ARCH §5.6: `curtainCrate` for the curtain kind · UI §4.4: not shipped | OK | The curtain kind is unused (O-20). |
| M-10 | Board sprites at the 32 pt design pitch, scaled by pitch/32 | ARCH D16, §5.6; UI §4.3 | OK | — |

---

## 18 Accessibility identifiers

| ID | identifier | values by file | status | ruling |
|---|---|---|---|---|
| Y-1 | `hud.booster.freeze` / `hint` value | ARCH §9.8: stock:n, empty, locked, active · UI §6: stock:n, empty, active | OK | v552 has no booster lock, so "locked" is never used. |
| Y-2 | `popup.<id>` | ARCH: `popup.<PopupID raw>` · UI: `popup.moreLives`, `popup.outOfLives` | FLAG-W | `popup.noLives` (U-31). The Out of Lives! layout is `popup.continue`, value `hearts` (ID-11). |
| Y-3 | `settings.toggle.*` value | ARCH, UI: on / off | OK | Music is always "off" (U-7). |
| Y-4 | `home.lives` value | ARCH: n, mm:ss, full, inf:mm:ss · GP and UI: ∞ at an hour or more reads "1h 20m" | FLAG-W | Use `inf:<the displayed text>`. |
| Y-5 | Leaderboard and event ids | ARCH §9.8 + UI §6 additions | OK | additive |

---

## 19 Contract (◆) and frozen-file changes the content specs imply

| # | file | change | needed by | recommendation |
|---|---|---|---|---|
| C-1 | `App/Contracts/AudioContract.swift` ◆ | `SoundID` + clawToken, clawMerge, clawTick, clawComplete, streakPop | A-2 | approve (additive) |
| C-2 | `AudioContract.swift` ◆ + `App/Support/Tuning.swift` ◆ | `Haptic` + heartLost, button, booster, coinLand; the default rows | A-8 | approve (additive) |
| C-3 | `App/Contracts/ShellContract.swift` ◆ | `DimToken` + info, weeklyTutorial, overPage | U-2 | approve (additive) |
| C-4 | `ShellContract.swift` ◆ | Settings as a page | U-5 | none: use `PopupID.settings` full-screen |
| C-5 | `Packages/PathCore/.../PlayerState.swift` ◆ | `Settings.music` default true → false | U-7 | none: G2 writes false at the first launch |
| C-6 | `ShellContract.swift` ◆ | `EditProfileResult` carries the name | U-28 | none: the popup writes the name through `PlayerStore` |
| C-7 | `App/Brand.swift` (frozen, LEAD) | `Brand.supportEmail` | U-6 | none: use a `game.json support.email` key |
| C-8 | `Packages/PathCore/.../EventTypes.swift` ◆ | the `RivalProvider.streakRace` comment "5 rows" | V-5 | comment only (50 rows); fix at the next approved contract edit |
| C-9 | `App/Support/LaunchArgs.swift` ◆ | the social flags | ID-9 | none: `-pc.seed` + `LaunchArgs.raw` |
| C-10 | `PlayerState.swift` ◆ `social` sub-state | SOC §6's schema | ID-5 | none: `SocialState` is additive-only by design (ARCH §4.12) |

---

## 20 Build data still carrying superseded values (information for the data owners)

| file (owner) | key: now → should be | ref |
|---|---|---|
| `Tuning/rules.json` (C2) | `lives.refillSeconds` 1200 → **1800** (C3's `EconomyRules.load` reads this section over its 1800 default); `pipe.countAt` "enter" → "leave"; `hit.radiusPt` 15 → 22; `boosters.freezeFlight` 1.5 → 1.6; add the GP §15 sections the file still lacks (economy, lives.*, streak, claw, shop); the hint policy key (K-8) | X-7, O-15, G-5, K-3 |
| `Tuning/board.json` (B1) | `input.hitRadiusPt` 16 → 22; `rainbow.periodCells` 5.6 → 4.2; `color.violet` → `violet.palette` / `violet.periodCells`; `pan.slackPt` → `pan.limit "centreInGrid"`; the MA §13.1 blocks (`dots.mode`, `stars`, `hint`, `shards`, `key`, `elevator`, `intro.drawStartFraction`, `intro.ackAt`) | G-5, E-12, E-10, G-11 |
| `Tuning/ui.json` (S1) | `transition.loadingToHome` 0.3 → 0.16; `unlock.*` → MA §6.3; `win.panelAt` 3.36 → 3.94 (anchored on W); `frames.settings` and `frames.quit` → UI §5; the shared `puppet.*` knobs → per rig (MA §8.2); the MA §13.2 blocks; drop `hud.outOfTimeHold` (T-4) | T-18, T-25, W-2, U-10 |
| `Tuning/audio.json` (A2) | `haptics` → MA §13.3 (after C-2); `gain.tapTick` 1.0 → 0.6; the new cue keys | A-9, A-12 |
| `Tuning/social.json` (SOC1) | already the phone's group sizes (Weekly 10, Streak 50); SPEC-social's text lags behind; `countryContinuousUpTo` 600 against SOC's 300 | V-5, V-6, V-20 |
| `PathCore/Social/Population.swift` (SOC1) | avatar `1 + below(…, 14)` → 8 in the shipped v552 model | V-24 |

---

## 21 Orchestrator decisions (every FLAG-R), with the recommendation

1. **T-10**: open input at K + 1.015 during the intro (MA9) → **accept**; B1 hit-tests through the presentation transform.
2. **U-5**: Settings as a full page → **deliver it through `PopupID.settings`** rendered full-screen; no contract change.
3. **U-6**: Support, Terms, Privacy → **GP's behaviour and texts in UI's page layout**; the owner confirms anycodeapps@gmail.com; the
   address goes in `game.json`, not `Brand.swift`.
4. **U-7**: Music → **the inert button (MA2)**; G2 writes `music = false` at the first launch; the owner may ask to hide it.
5. **A-2, A-8**: the AudioContract + Tuning.swift additive change → **approve** (MA §15.1 is the fallback).
6. **A-3**: MusicID → **approve MA's route** (A1 changes its tools; no contract change).
7. **U-2**: `DimToken` + 3 cases → **approve** (additive).
8. **U-28**: the Edit Profile name → **the popup writes it**; no contract change.
9. **L-2**: the spare swap (V2-L038 at L63, V2-L037 at the Hard slot L64) → **accept**.
10. **L-9**: the generator cost → **binding: off-main, one level ahead**; C4 measures before the ms budget is relaxed.
11. **O-23**: door sizes → **a code-drawn door shutter (9-slice) + `lockHex`**, so L1–150 (48 sizes) and every runtime size render; the
    fallback is to render all 48 and restrict runtime sizes.
12. **V-26**: username rules → **3–16 characters, letters of any script, digits, "_"**; GP's messages edited to "3-16".
13. **V-29**: social budgets → **0 ms on the main thread + SOC's per-query numbers as SOC1's bench gate**.
14. **X-18**: the FakeStore currency → **the region list (TL on a TR device)** with the test-store chip; the owner may prefer US $.
15. **S-6**: the username popup title → **"Username"**.
16. **G-9**: a tap on a moving arrow → **ignored** (never re-targeted).
17. **T-31**: X on Level Failed before the first home → **retry the level**.
18. **GP OPEN**: the honest Terms line "the other players … are simulated" → **keep it** (GP §12.3: the owner can remove it).
19. **SPEC-social's text** (V-5, V-6, V-9, V-24): ask SOC1 to align SPEC-social with the rulings above. The shipped world model already
    follows the phone except for the avatar range.

**Passed through (not consistency conflicts; for the orchestrator's own list):**
- GP: designed Hard/Super Hard levels shallower than their templates (L79: 15 waves against 30).
- GP: `design/tools/work/` intermediates, commit or ignore.
- UI: the clips that would settle its DECISIONs.
- MA: the phone gap-filler clip list (§16) and the haptic feel check on the phone (D1b).
- MA: the logo parts and `eyes_wink` art requests.
