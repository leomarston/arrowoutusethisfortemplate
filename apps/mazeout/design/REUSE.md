# Maze Out — REUSE (GAMEPROMPT §8.0)

REUSE agent, 2026-09-25 (~01:55–02:25 +03). **Status: done.** The build/test tooling is copied into `apps/mazeout/tools/` and
adapted (§2). Every script passed a syntax check, and most passed a smoke test in the scratchpad (§6). The Swift and content
inventory in §3 is a proposal: the architecture spec confirms the target files, and WP0 creates `App/` and `Packages/`.
Nothing here needed a simulator or xcodebuild, and nothing was committed.

**Column conventions**
- **Commit** = `git log -1 --format=%h -- <path>`.
  - Exemplars were read on `build/matchfactory` (HEAD `e10a076`).
  - `apps/arrows` → `8e77f85` (2026-09-24, "Arrows puzzle copy … (WIP, parked)").
  - Match Factory → `05424db` (2026-09-24 WIP snapshot) or `e10a076` (2026-09-24 build complete).
  - Our own files → `git log -1 build/mazeout -- <path>` (`dbf4543` desk research, `9a25a95` kickoff).
  - Every copied tool is identical to its commit. `git diff --quiet HEAD` passed on all of them. The only MF tools file with
    uncommitted edits is `tools/levels/build.py`, and it was NOT copied.
- **Verdict** is one of four values:
  - **copy** = as-is (a header line may change);
  - **adapt** = copied with the listed changes;
  - **ref** = read it, don't copy it (the path + commit is how to find it);
  - **NO** = must not carry over (§4).

---

## 1. Global renames (applied in `tools/`; WP0 applies the same ones to Swift)

| From (exemplar) | To (Maze Out) | Where it matters |
|---|---|---|
| `MatchFactory` / `Arrows` (project, scheme, target, `.app`, executable) | `ArrowOut` | project.yml, `tools/slot.sh` `SCHEME`/`PROJECT`/`APP`, bench `APP_NAME`, crash-report prefix |
| `MFCore` (package) | `PathCore` (`Packages/PathCore`) | `tools/core.sh`, project.yml `packages:` |
| `com.manycode.matchfactory`, `com.manycode.arrows` | `com.manycode.arrowout` (+ `.tests`, `.uitests`) | slot.sh, capture.py, bench.py, play-watch.sh, the `Log` subsystem |
| Launch args `-mf.<name>` | `-pc.<name>` | run/capture/bench/lab args, the `LaunchArgs` contract, `raw["pc.x"]` |
| Log tag `[MF][cat]` | `[PC][cat]` (format `"<uptime> [PC][cat] msg"`, errors `[PC][cat][ERROR]`) | bench.py `LOGLINE`/`MARKS`, capture.py `LOG_TAG` |
| Console log `data/tmp/mf-run-<slot>.log` | `data/tmp/pc-run-<slot>.log` (linked as `build/run-<slot>.log`) | slot.sh `SIMLOG`, capture.py, bench.py |
| Temp prefixes `mf-audio-repro-`, `mf-mut-` | `pc-audio-repro-`, `pc-mut-` | audio/check.py, check_selftest.py |
| Simulators "MF Spike" `FFE58FD1-0DC6-4010-895D-AA12D0327736` / "MF Main" `B8F323DC-F338-4918-B370-5F6D9F48FB11` | slot A = "Maze A" `177520B6-4889-46C2-BDD9-155813D2B175`, slot B = "Maze B" `B80EDB24-6280-4C52-A63F-E8AADD245017` | slot.sh (the single source); capture.py and bench.py repeat it with a `= tools/slot.sh` comment |
| Arrows "Arrows Play" sim `A9DA09AD-…`, a stale scratchpad path | `PLAY_UDID` env (required; a slot UDID is refused), `build/play-stage` | play-watch.sh |
| Brand constant `"Match Factory"` (strings check) | `BRANDS = ("Maze Out", "MazeOut", "Arrow Jam", "Grand Games")` | strings/build.py |
| `MF_BRAND_NAME` build setting → `MFBrandName` Info key → `Brand.name` | proposal: `PC_BRAND_NAME` → `PCBrandName` → `Brand.name` | WP0 (project.yml + `App/Brand.swift`) |
| Type prefixes `MFRandom`, `MFTiming`, `MFButton`, `MFDisplay-Regular.ttf` | `PathRandom`, `Timing`, `GameButton`; the font is already `PCDisplay-Black.ttf` (design/fonts.md) | Swift (WP0/C1/S1). File names stay neutral: never "maze", "mo", "grand", "arrowjam" (the app entry file is `App/GameApp.swift`, not `ArrowOutApp.swift`) |
| `Application Support/MatchFactory/player.json` | proposal: `Application Support/Save/player.json` | PathCore `StateStore` (C3) |
| The original's ids (`net.peakgames.*`, `ecffri`) | none found | grep over every copied file: 0 hits (§6) |

---

## 2. Copied into `apps/mazeout/tools/` (step 2 deliverable)

Every script derives `ROOT` (= `apps/mazeout`) from its own location, so it runs from any cwd.
`tools/watchdog.sh` (kickoff, `9a25a95`) was left untouched.

### 2.1 Build, run, test

| Our file | Source | Commit | Verdict | Changes |
|---|---|---|---|---|
| `tools/slot.sh` | `apps/matchfactory/tools/slot.sh` | 05424db | adapt | Holds our UDIDs, names, `BUNDLE_ID`, `SCHEME`, `PROJECT`, `APP` and `SIMLOG` (the one place they are defined). A caller in a subfolder may pre-set `ROOT`. New helpers: `sim_state`; `sim_boot` (boots ONLY this slot, then `chmod 000` its `nsurlsessiond` cache, §3.3); `sim_unblock_assets` (755 before an erase); `swap_free_mb`; `wait_for_memory` (refuses < 3 GB disk; waits in 120 s steps while free swap < `SWAP_MIN_MB`=400, at most `SWAP_WAIT_MAX`=600 s, then exits 75). |
| `tools/gen.sh` | `…/tools/gen.sh` | 05424db | adapt | `build/.gen.lock` mkdir mutex (60 s, then a hint to rmdir). Finds xcodegen via `$XCODEGEN`, then PATH, then `~/.local/bin/xcodegen` (where it lives on this Mac). Fails clearly if `project.yml` is missing. |
| `tools/build.sh` | `…/tools/build.sh` | 05424db | adapt | Debug, `-jobs 4 -quiet`, into `build/dd-<slot>`. Calls `wait_for_memory` first and prints slot, free swap and the booted count. |
| `tools/test.sh` | `…/tools/test.sh` | 05424db | adapt | Same destination and DerivedData as build.sh, plus `wait_for_memory`. |
| `tools/run.sh` | `…/tools/run.sh` | 05424db | adapt | `sim_boot`, terminate, install, then `simctl launch --terminate-running-process` with stdout/stderr to the simulator's own `data/tmp/pc-run-<slot>.log`, symlinked from `build/run-<slot>.log`. Writing under ~/Downloads is denied by the sandbox (§3.3). |
| `tools/core.sh` | `…/tools/core.sh` | 05424db | adapt | `Packages/PathCore`: `swift build -j 2` + `swift test -j 2`. Clear error until WP0 creates the package. |
| `tools/bench.sh` | `…/tools/bench.sh` | 05424db | adapt | Wrapper for `bench/bench.py`. |
| `tools/sync_art.sh` | `…/tools/sync_art.sh` | 05424db | adapt | Copies `art/ui/out/*.png` → bundle `UI/` and `art/out/*.png` → bundle `Art/`; skips `_*`, copies PNG only. MF's USDZ items, sidecars and lighting rig are gone. **WP0 decides** whether project.yml runs it as a postCompile script (MF needed `ENABLE_USER_SCRIPT_SANDBOXING: NO`) or uses an asset catalog. |
| `tools/iso-build-copy.sh` | `tools/gameprompt/snippets/iso-build-copy.sh` | 05424db | adapt | Generalised to `<role> <A\|B> [action] [xcodebuild args]`. `build/iso-<role>/tree` = App/ rsynced, project.yml copied, Packages/art/design/Tests/UITests/tools symlinked; DerivedData in `build/iso-<role>/dd`. MF G1's baked-in BoardEngine patch became an optional `build/iso-<role>/patch.py`, which touches the copy only. |
| `tools/wait-build.sh` | `…/snippets/wait-build.sh` | 05424db | adapt | `<role> <A\|B> [action]`. Waits until `App/` + `Packages/PathCore/Sources` have been quiet for `QUIET`=90 s and free swap ≥ 400 MB, then runs iso-build-copy (5 attempts). Log: `build/iso-<role>/build.log`. Can exceed 4 min: run it in the background. |
| `tools/play-watch.sh` | `…/snippets/play-watch.sh` (Arrows' copy) | 05424db | adapt | The Arrows UDID, bundle and paths became `PLAY_UDID` (required), slot A/B `ArrowOut.app`, `com.manycode.arrowout` and `build/play-stage`. Refuses a slot UDID: never share a simulator. |
| `tools/capture-shot.sh` + `tools/flat_check.py` | `…/snippets/capture-shot.sh` (MF BoardLab, slot A only) | 05424db | adapt | `<A\|B> <name> [args]`. Env: `OUT`, `READY` (`capture-ready.json` \| `lab-ready.json`), `TIMEOUT`, `SHOT_DELAY`, `CAPTURE_ARGS` (default `-pc.capture 1`). Waits for the ready file, then `simctl io … --mask=ignored`, then sips sRGB. **New:** the §8.3 step-4 flat-frame rejection (flat_check.py) at `FLAT_MAX` = 0.97 (DECISION §5.1). Always prints the measured fraction. |
| `tools/rng_ref.py` | `…/snippets/rng_ref.py` | 05424db | copy | Header only. The independent Python reference that PathCore's `RandomTests` must pin: SplitMix64 + xoshiro256**, `fork`, `attemptSeed`. |

### 2.2 Strings (EN + TR)

| Our file | Source | Commit | Verdict | Changes |
|---|---|---|---|---|
| `tools/strings/build.py` | `apps/matchfactory/tools/strings/build.py` | 05424db | adapt | TSV `App/Resources/Strings/strings.tsv` (en, tr, context) → `App/Resources/Localizable.xcstrings`. Kept: 3 columns, no duplicates, no stray whitespace, balanced `**`, argument types compared in ORDER after positional resolution (memory reordered-args-need-positional), and TR written positionally when there are ≥ 2 args. Changed: `BRANDS` (4 names) instead of one; `--tsv` / `--out` for tests. |
| `tools/strings/coverage.py` | `…/strings/coverage.py` | 05424db | adapt (rewritten around MF's functions) | MF hard-coded its spec sections and compared TURKISH (its phone was Turkish). Our original's UI is ENGLISH (research/flows.md). Sources therefore moved to `sources.json`, each with its `lang` column; kinds are json / json-map / md-table / md-quoted. A missing source FAILS unless it is marked `"optional": true`. Tutorial keys walk any JSON; `callees` (custom text components) are configurable. MF's `SUPERSEDED` table became `sources.json` `superseded` (empty). |
| `tools/strings/sources.json` | new | — | new | Proposal: ui-tokens.json `strings`, SPEC-ui `## Strings`, SPEC-gameplay `## Strings`, levels.json `tutorials`, tutorials file `App/Resources/Levels/tutorials.json`. **The spec writers point these at their real headings.** Until then coverage fails, on purpose. |

### 2.3 Audio (synthesis + checker + self-test; nothing may derive from research/sound-refs)

| Our file | Source | Commit | Verdict | Changes |
|---|---|---|---|---|
| `tools/audio/dsp.py` | `apps/matchfactory/tools/audio/dsp.py` | 05424db | copy | Docstring only. |
| `tools/audio/instruments.py` | `…/instruments.py` | 05424db | copy | Docstring only. The generic patches: pluck bass, marimba, kalimba, glock, toy EP, whistle, brass stab, saw pad, woodblock, shaker, kick, clap, hat, tambourine, snare, crash, firework pop. |
| `tools/audio/spectro.py` | `…/spectro.py` | 05424db | copy | Docstring only. |
| `tools/audio/specs.py` | `…/specs.py` | 05424db | adapt | Paths and the contract parser kept; all cue tables are **EMPTY** (`SFX`, `LOOPS`, `CHAINS`, `VARIANTS`, `SIZED`, `MUSIC`). A1 fills them from our SPEC-motion-audio. MF's `TIME_TICK_SIZES` became the generic `SIZED` + `SIZED_LENGTH`. Contract path: `App/Contracts/AudioContract.swift` (proposal; env `PC_AUDIO_CONTRACT` overrides it). A clear error if it is missing. New helper `loop_samples()`. |
| `tools/audio/sfx.py` | `…/sfx.py` | 05424db | adapt | Kept: the helpers, `render_all` (variants + SIZED renders via `SIZED_KEYWORD`) and `write_manifest`. MF's ~50 cue recipes are NOT copied (they are its cues). `RECIPES` is empty. MF recipes are a technique reference only: `git show 05424db:apps/matchfactory/tools/audio/sfx.py` (buttonClick, coins, key, timeTick count-up, winFanfare, sting→pad chains). |
| `tools/audio/music.py` | `…/music.py` | 05424db | adapt | The `Song` circular-loop engine and `parse_line` are verbatim (diff-checked). MF's two compositions are NOT copied. `RENDER` is empty, and a missing composition fails. |
| `tools/audio/check.py` | `…/check.py` | 05424db | adapt | Checks: length, peak / true peak ±1.5 dB, format, edge clicks, DC, loop seams, chains, music RMS / TP / bars, strays, provenance, `--reproduce`. Changed: SIZED is generic, and **an empty contract now FAILS** (MF's passed vacuously). |
| `tools/audio/check_selftest.py` | `…/check_selftest.py` | 05424db | adapt (generalised) | MF's mutations named MF files. Ours pick targets from specs.py (one-shot, loop, chain, music). All 11 MF mutations are kept, and 4 were added: start click, DC offset, 10 % too long, 3 dB too quiet. A mutation with no target in our specs prints `n/a` and is not counted. Every applicable one must be CAUGHT. Exit 2 = nothing shipped yet. |

Reference only (A2 decides when App/Audio lands):
- `tools/audio/engine_test.sh` + `enginetest/main.swift` (offline AVAudioEngine tests of MF's AudioCore; its cases name MF cues).
- `typecheck_ios.sh`.
- `demo.py` (MF scenes).
- `manifest.json` (MF's output).

All of them are in `05424db`.

### 2.4 Fidelity (V2) and performance (V3)

| Our file | Source | Commit | Verdict | Changes |
|---|---|---|---|---|
| `tools/compare/side_by_side.py` | `apps/matchfactory/tools/compare/side_by_side.py` | e10a076 | copy | Docstring only. CIEDE2000 per region on the 393×852 pt canvas (ours too). |
| `tools/compare/compare_all.py` | `…/compare_all.py` | e10a076 | copy | Docstring only. Reads `tools/capture/manifest.json` + `tools/compare/regions.json`, writes `build/compare/`. |
| `tools/compare/summarize.py` | `…/summarize.py` | e10a076 | copy | Docstring only. Exits 1 when an over-6 region has no annotation. |
| `tools/compare/regions.py` | `…/regions.py` | e10a076 | adapt | `reg`/`inset`/`add` helpers and region kinds kept; MF's ~60 capture lists EMPTIED. |
| `tools/compare/regions.json` | `…/regions.json` | e10a076 | adapt | **Emptied**: `{"shots": []}`, regenerated by regions.py. |
| `tools/compare/annotations.json` | `…/annotations.json` | e10a076 | adapt | Emptied: `rules: []`. |
| `tools/capture/capture.py` | `apps/matchfactory/tools/capture/capture.py` | e10a076 | adapt | `-mf.` → `-pc.`, `[MF]` → `[PC]`, our slots and bundle. Probe conditions made generic (`true` = truthy, `{"min": n}`, equality); MF's `trayLanded` is gone. The blank-frame test now uses flat_check (MF looked for its placeholder colour `#28303A`). The boot-cap retry keys on `BOOT_CAP_MARK`. The whole probe is saved. |
| `tools/capture/manifest.json` | `…/capture/manifest.json` | e10a076 | adapt | Emptied: `captures: []`. |
| `tools/bench/bench.py` | `apps/matchfactory/tools/bench/bench.py` | e10a076 | adapt | Kept: Slot plumbing, footprint, host state, HUD OCR, lab / launch / level / soak / report / heapdiff. Removed: `stats` (RealityKit `.showStatistics`). Every parsed log line now lives in one `MARKS` table (proposal; §7). The report is generic: per attempt, outcome, time left, hearts, loss reason, go→visible, board-ready, frames, memory. MF's items/kinds/proxies/oyna are gone. Budgets are MF's until SPEC-architecture sets ours. |
| `tools/bench/hudocr.swift` | `…/bench/hudocr.swift` | 05424db | adapt | New `--crop x,y,w,h` (pt); bench passes `HUD_CROP`. Default band unchanged. |

MF's `tools/capture/shot.sh` is not copied: `tools/capture-shot.sh` covers single shots.

---

## 3. Inventory: what transfers into App/ and Packages/ (proposals; the architecture spec confirms)

### 3.1 Our own tech spike — `apps/mazeout/build/spike/` (≈2,240 lines)

**⚠ It is UNCOMMITTED and gitignored (`build/`).** It is the most direct source of the board, and a cleanup of `build/` would
lose it. Request (§7): commit it to a tracked path such as `design/spike-src/` (MF precedent: `design/spike-src/Tween.swift`)
before any cleanup.

| Source (build/spike/…) | What it is | Verdict | Target (proposal) |
|---|---|---|---|
| `App/Core/Level.swift` (136) | `Cell`, `Dir`, `ArrowSpec` (tail→head), `TapeSpec`, `LevelSpec` (decodes both the phone player's schema and the spike's), `SplitMix64` | adapt | `Packages/PathCore/Sources/PathCore/Model/{Cell,Dir,ArrowSpec,LevelSpec}.swift`. `TapeSpec` → an `Obstacle` enum (tape, door+key, pipe, …). The RNG → `PathRandom` (§3.4). |
| `App/Core/Board.swift` (138) | `BoardState` (flat `[Int32]` occupancy, alive bits, tape units); `tap → .exits / .exitsGroup / .blocked(gap) / .ignored`, with rays running to the GRID EDGE; `greedy` solver; `validate` | adapt | `PathCore/Rules/BoardState.swift` + `Solver/Greedy.swift` + `Content/Validator.swift`. Add doors (door cells block rays; keys unlock) per research/obstacles.md. The some-clear tape case is still UNKNOWN. |
| `App/Core/Geometry.swift` (177) | `Metrics` (ratios of the measured pitch), `BoardLayout` (fit rule, play rect 122…755 pt), `ArrowGeometry` (strokeStart/End, headPosition, runs, exitTravel, contactTravel), `TravelProfile` | adapt | `PathCore/Geometry/*.swift` (CoreGraphics only). Unit-test it against motion.md once the analyst writes it. |
| `App/Core/Generator.swift` (96) | Reverse construction from the centre outwards; silhouette mask; solvable by construction (304 arrows in 9 ms) | adapt | `PathCore/Generator/Generator.swift` + difficulty target, obstacle injection, `PathRandom` streams |
| `App/Render/ArrowNode.swift` (430) | `LocalPath` (frames hug their paths), `ArrowNode` (rest: body + head), `Mover` (exit / bump / tape carry, one no-actions transaction), `StarTrail` | adapt | `App/Board/{ArrowNode,Mover,StarTrail}.swift` |
| `App/Render/BoardView.swift` (337) | `UIScrollView` zoom 0.75–3, stage layers, grid-maths hit test, ripple, `freeze()`, `ReleaseTapRecognizer` | adapt | `App/Board/BoardView.swift` + `App/Board/ReleaseTapRecognizer.swift` |
| `App/Render/Track.swift` (107) | Shared keyframe track, `AnimationEnd` delegate, `keyframes` / `sampledKeyframes` | copy | `App/Board/Track.swift` |
| `App/Tunables.swift` (113) | Placeholder motion values as `-pc.*` UserDefaults args; `paletteColor` | adapt | Values → `App/Resources/Tuning/board.json` read through MF's `Tuning` pattern (§3.4); `paletteColor` → `App/Board/Palette.swift` |
| `App/Bench.swift` (350) | `CADisplayLink` histogram, footprint, scenarios (idle, exit5, trail, bump, crisp, zoomramp, hittest, autoplay), results in `tmp/` | adapt | `App/Board/BoardLab.swift` (scenarios, reached with `-pc.go boardlab -pc.lab <scenario>`, writes `Documents/lab-ready.json` + `lab-perf.json` for tools/bench.py). Frame stats → `App/Support/PerfMonitor.swift`. |
| `App/SpikeApp.swift` (85) | `BoardHost` (UIViewRepresentable) + `HostView` + `LevelLoader` | ref | Pattern for `App/Board/BoardHost.swift` |
| `UITests/PinchTapTests.swift` (98) | Real-touch XCUITest: tap on release, hold 2 s then release, pinch clamps | adapt | `UITests/BoardInputTests.swift` (bundle `com.manycode.arrowout`; the refreshed `-pc.uitest` hook, pitfall P8) |
| `tools/run.sh`, `tools/extract_l32.py`, `tools/coretest_main.swift` | Spike harness, an independent L32 extractor (identical 53 arrows), a swiftc core check | ref | Superseded by tools/capture-shot.sh, research/bot/bot.py and `tools/core.sh` |
| `project.yml` | iOS 18, `CADisableMinimumFrameDurationOnPhone`, portrait, UITests target | ref | WP0's project.yml (§3.6) |

Pitfalls P1–P9 of design/tech-spike.md travel with this code:
- P1: `addSublayer` inside the no-actions transaction.
- P2: emitter `beginTime`.
- P3: extend the dots path 1 pt.
- P4: frames hug their paths.
- P5: release-tap.
- P6: nested funcs `@MainActor`, and no exclusivity conflicts.
- P7: typed `let`s.
- P8: a refreshing UI-test hook.
- P9: take the bump timing from the analyst.

### 3.2 `apps/mazeout/art/ui/code/GlossyChrome.swift` (dbf4543, 199 lines)

What it is: the art spike's route-B chrome in pure SwiftUI, with numbers measured on runner shots 003/007. It contains:
- `Superellipse`;
- `GlossyHeartShape` (IoU 0.981);
- `BlueSquareButton` + `PauseGlyph` (HUD 40×40);
- `HeartHUD`;
- `PanelButton` (Resume / Quit 125×89);
- `OutlinedLabel`.

**Verdict: copy** → `App/Shell/Components/GlossyChrome.swift`. Then:
- swap `OutlinedLabel`'s placeholder font for `PCDisplay-Black`;
- make its text a `LocalizedStringKey`, or keep it in `sources.json` `callees`;
- keep it compiling on macOS 14 for `art/ui/tools/swiftui_render.swift`.

### 3.3 `apps/arrows` (8e77f85) — same genre, Core Animation board

| Source | What it is | Verdict | Notes / target |
|---|---|---|---|
| `App/Board/BoardView.swift` (719) | Zoomable board, tap + long-press + accessibility, render-server motion | ref | The spike's BoardView replaces it. Take its accessibility container pattern (`accessibilityIdentifier "board"`, per-arrow elements) → `App/Board/BoardView.swift`. **NO** to its tap/long-press model (§4). |
| `App/Board/ArrowNode.swift` (204) | Body / tail disc / head driven by identical keyframes | ref | The spike's `ArrowNode` + `Mover` supersede it. |
| `App/Board/BoardGeometry.swift` (400) | Layout centred on occupied bounds, arrow paths with a 0.10p corner radius | ref | Our geometry is measured differently (sharp polyline + round join, fit to `cols+2`). Use the spike's `Geometry.swift`. |
| `App/Board/BoardMotion.swift` (90) | `TravelTrack` | ref | = the spike's `Track.swift` |
| `App/Board/BoardController.swift` (141) | Command queue between the shell and the board; replays commands when SwiftUI re-creates the view | **adapt** | → `App/Board/BoardController.swift`. Events: `tapped`, `contact`, `exitFinished`, `boardCleared` (tech-spike.md). |
| `App/Board/BoardContainer.swift` (34) | Edge-to-edge host ignoring the safe area | adapt | Fold into `App/Board/BoardHost.swift` |
| `App/Board/DotsLayer.swift` (120) | One shape layer PER CELL for vacated dots | **NO** | The spike's one dashed stroke per departed arrow is proven: 399/399 dots, 1 layer per arrow. |
| `App/Board/GameFeel.swift` (87) | All board tunables, tuned by eye in the simulator | ref | Ours come from the analyst's motion.md via `Tuning/board.json` |
| `App/Board/TutorialHandLayer.swift` (193) | Pointing glove in board space; loops a tap | adapt (if the FTUE shows a hand) | → `App/Board/TutorialHandLayer.swift`. The art must be ours in the original's style, and the FTUE is not recorded yet. |
| `App/Engine/GameEngine.swift` (163) | Tap rules; the ray runs to the edge of the OCCUPIED BOUNDS | **NO** | Maze Out rays run to the grid edge, with doors and tapes (spike `Board.swift`) |
| `App/Engine/Level.swift` (130) | `GridPoint`, `LevelSpec` for Arrows' Levels.json | ref | The spike's `Level.swift` reads our research schema |
| `App/Services/Haptics.swift` (74) | Main-thread-safe generators, re-prepared after firing; gated by the Vibrations setting | **adapt** | → `App/Audio/Haptics.swift` (MF put it there as well). Events: exit, bump, heart lost, win, fail, selection. Gate on our Haptic toggle (the Pause panel). Every row is a DECISION (vibration can't be recorded). |
| `App/Services/SoundManager.swift` (310) | Small AVAudioEngine SFX player, mono → stereo buffers, interruption recovery | ref | MF's App/Audio is the fuller engine (buses, music decks, chains, offline tests). A2 picks one; MF's is recommended because tools/audio/manifest.json targets it. |
| `App/Services/Store.swift` (98) | Real StoreKit 2, non-consumable "Remove ads" | **NO** | The shop runs on FakeStore (GAMEPROMPT §9); purchases are rejected by the owner's rule. |
| `App/Services/GameCenter.swift` (124) | Game Center account link | **NO** | §4 |
| `App/Core/LaunchArgs.swift` (46) | 9 flags (`-resetState`, `-level`, `-openGame`, `-dark`, `-lang`, `-tab`, `-holdPraise`, `-mistake`, `-hintNow`); the "negative numbers are values" parsing rule | ref | MF's `-mf.*` struct is the model (§3.4). Keep Arrows' `value(after:)` rule for negative numbers. |
| `App/Core/AppSettings.swift` (82) | `@Observable` over UserDefaults (no `@AppStorage`); `SavedLevelProgress` | adapt (settings only) | Sound/Haptic toggles → `App/Support/Settings.swift`. **Game state** (level, coins, lives, streak, mid-level progress if the original keeps it) goes into PathCore's JSON `StateStore`, never UserDefaults (§8.1). |
| `App/Core/Theme.swift` (170) | Measured light tokens + invented dark values | ref | Our tokens = `design/ui-tokens.json`. **NO** to dark mode (not seen in the original). |
| `App/Game/GameModel.swift` (420) | Level session: hearts, saved progress, hint, tutorial, win / out-of-hearts flow | ref | Our session is a PathCore state machine with one event stream (§3.4). Its rules differ (§4). |
| `App/Game/HUD.swift`, `HintPill.swift`, `DifficultyTag.swift`, `TutorialLabel.swift`, `OutOfHeartsDialog.swift`, `PraiseOverlay.swift`, `GameScreen.swift` | Arrows' HUD and flows | ref | Layout techniques only (safe-area maths). Our HUD: coin pill, back, Level tab + stopwatch + timer + 3 hearts, pause, 2 boosters (research/flows.md). Hard / Super Hard recolours instead of a tag word. |
| `App/Game/Confetti.swift` (198) | Closed-form confetti over a preallocated array, `holdAt` freeze | adapt (technique) | → `App/FX/Confetti.swift` for the win celebration ("MAZE OUT!" sign + confetti + rockets). Shapes, colours and timings come from motion.md. |
| `App/Shell/*` (13 files) | Home, RootView + **TabBar**, Settings, LanguageSheet, RatingPrompt, SafariSheet, Toast, Logo, ComingSoon, ArrowsToggle | ref / **NO** | Only `Toast.swift`'s `LocalizedStringKey` pattern transfers (MF's Toast is closer, §3.4). Everything else is **NO** (§4). |
| `Tests/*`, `UITests/*` (EngineTests 319, BoardTests 159, SoundTests 314, SmokeTests 243, ShellTests 156) | Arrows' suites | ref | Patterns for PathCore tests and UI smoke tests |
| `project.yml` (85) | Arrows' project | ref | MF's is the closer model (§3.6) |
| `design/tools/extract_levels.py` (548) + `extract_outputs.py` (287) | Auto-trace → least-squares grid fit → head-sprite fit → render-and-XOR proof, with green overlays | ref | Research already extracts with `research/bot/bot.py` (+ `research/bot/overlay/`), and the spike's extractor matched it exactly on L32. Use this pair for the **IoU ≥ 0.99 overlay proof** (§8.3) if bot.py lacks one. Content owner → `tools/levels/`. |
| `design/tools/solve_levels.py` (115) | Greedy solver; the ray runs to the bounding box | ref | PathCore's `Greedy` (from spike `Board.swift`) is the solver of record; a Python mirror is optional. The ray end must be the grid edge. |
| `tools/levels/arrowlib.py` (242) | Python mirror of the rules | adapt (content owner) | → `tools/levels/pathlib_rules.py` (neutral name). Ray to the grid edge; tape units; doors/keys. |
| `tools/levels/generate.py` (338) | Partition + orientation search for style targets; exact greedy layering | ref | PathCore's generator (spike) is the shipping path. Its orientation search (free-at-start count, dependency depth, traps) is worth reading for the difficulty curve. |
| `tools/levels/render.py` (367) | SDF renderer of boards on the reference canvas (+ solution sheets) | adapt (content owner) | → `tools/levels/render.py`, re-measured for our geometry (tech-spike table); feeds the overlay proof and the level sheets. |
| `tools/levels/trace_storyboard.py` (156) | Traces levels from YouTube storyboard frames | ref | Useful for L1–31 from videos (research/web-research.md: videos A/B'd content) |
| `tools/sounds/gen_sounds.py` + `README.md` | numpy SFX set | ref | Superseded by MF's audio toolkit (§2.3) |
| `tools/play-watch.sh` | = the snippet | adapt | → `tools/play-watch.sh` (§2.1) |

### 3.4 `apps/matchfactory` Swift (05424db unless noted)

MF's working tree is ahead of `05424db` for:
- `App/Shell/Components/{Badge,ItemIcon,Panel,Tokens,UIArt}.swift`;
- `App/Shell/Popups/{ContinueOfferPopup,LevelFailedPopup,LevelStartPopup,NoLivesPopup,PopupHost}.swift`;
- `MFCore/Content/LevelDefinition.swift`.

These are another session's uncommitted edits: copy from the working tree and say so, or pin `05424db`.

| Source (apps/matchfactory/…) | What it is | Verdict | Target (proposal) |
|---|---|---|---|
| `Packages/MFCore/Package.swift` | swift-tools 5.10, Foundation + simd, tests on macOS | adapt | `Packages/PathCore/Package.swift` (Foundation + CoreGraphics; the spike's core is CG-based) |
| `Sources/MFCore/Random/MFRandom.swift` (143) | xoshiro256** seeded by SplitMix64; named `fork` streams that don't advance the parent; its own `unit/below/int/double/chance` (stable across Swift versions) | **copy** + rename | `PathCore/Random/PathRandom.swift`. Streams: `generator`, `hint`, `autoplay`, `fx`. Pin `RandomTests` to `tools/rng_ref.py`. Replaces the spike's `SplitMix64`. |
| `Tests/MFCoreTests/RandomTests.swift` | Pins the first 8 outputs for seeds 0/1/42 + forks against rng_ref.py | copy + rename | `Packages/PathCore/Tests/PathCoreTests/RandomTests.swift` |
| `Sources/MFCore/Persistence/StateStore.swift` (193) + `Migrations.swift` (42) | Atomic JSON, `.prev` backup, `.corrupt` kept once, ISO-8601 with fractions, step migrations | **copy** + rename | `PathCore/Persistence/{StateStore,Migrations}.swift`; folder `Application Support/Save/` |
| `Tests/…/PersistenceTests.swift` (399) | Corrupt / backup / migration fixtures | adapt | `PathCoreTests/PersistenceTests.swift` |
| `Sources/MFCore/Economy/Lives.swift` (112) | Lives chain: max 5, refill anchored at the start of a running period; take / tick / give back; a clock set back never punishes | **adapt** | `PathCore/Economy/Lives.swift`. Maze Out shows 5 lives "Full". The refill interval and unlimited-lives rewards (∞ 30m / 6h Claw rewards) come from OUR research; MF's 30:00 is not ours until measured. |
| `Sources/MFCore/Economy/Economy.swift` (294) | Pure transforms of PlayerState: attempt bookkeeping (life taken at start, given back on a win, a killed app = a loss), coins, grants | adapt | `PathCore/Economy/Economy.swift`. Keep the attempt bookkeeping. Drop MF boosters / pre-boosters / stars. Add the win streak ×1/×5/×10/×25/×100 (Streak Race, Claw points), coin rewards 20/60/100 (normal / Hard / Super Hard) and continue prices (Add Time 900, Play On 900) from research. |
| `…/Economy/PlayerState.swift` (184), `Grant.swift` (48), `ShopCatalog.swift` (44) | The frozen save schema (every field defaults), grants, TL shop table | adapt / ref | `PathCore/Economy/PlayerState.swift` (our fields), `Grant.swift` (copy), `ShopCatalog.swift` (our products and prices from research; FakeStore) |
| `…/Rules/LevelClock.swift` (73) | Timer with hold reasons (intro, popups, pause, tutorials, background), a freezer that counts instead of the timer, alerts at 0:30 / 0:20 / every second ≤ 0:10 | **adapt** | `PathCore/Rules/LevelClock.swift`. Maze Out's timer starts at the FIRST TAP (research L32/L33): the initial `.intro` hold lifts on the first tap. Pause freezes it. The frozen-hourglass booster (art/STYLE.md B3) may map onto the freezer. The alert thresholds come from our research. |
| `…/Rules/{HintPlanner,ContinueRules,RulesTuning}.swift` | Hint choice, continue rules, the rules tuning struct | ref | The hint (bulb) = a free unit from the greedy solver. Continue = Add Time +30 s / Play On (research). |
| `…/Session/LevelSession.swift` (566) + `LevelEvent.swift` (67) + `SessionTypes.swift` (98) | ◆ One state machine and one causal event stream consumed by board / HUD / FX / audio / haptics | adapt (pattern) | `PathCore/Session/{LevelSession,LevelEvent,SessionTypes}.swift`. Our events: `exited`, `exitedGroup`, `bumped(gap)`, `contact`, `heartLost`, `doorUnlocked`, `timerAlert`, `timeUp`, `outOfHearts`, `won`, `continued`. |
| `…/Session/HeadlessDriver.swift` (132) | A bot over the real core, deterministic per seed | adapt (pattern) | `PathCore/Session/HeadlessDriver.swift`: taps free units (greedy order) at a human-like rhythm; plus the bump / time-out variants for the fail flows |
| `…/Motion/Curves.swift` (336), `Ease.swift` (218), `MFTiming.swift` (148) | Pure motion functions of t tested against motion.md; the Bézier tokens SwiftUI uses; closed-form springs; timing constants | **adapt** | `PathCore/Motion/{Curves,Ease,Timing}.swift`. `Ease` + `EaseToken` + `SpringCurve` copy as-is. `Curves` and `Timing` are rewritten from OUR motion.md (exit v, bump, dots, ripple, popups). Drop `Curves+Cards/Crate/Merge/Win`. |
| `…/Content/{LevelLibrary,LevelsJSON,LevelDefinition,FeatureGate,TutorialID}.swift` | Level loading + validator findings, feature unlock gates | adapt (pattern) | `PathCore/Content/{LevelLibrary,Validator,FeatureGate}.swift` (our schema = research/levels + tech-spike "Level JSON"). The feature gate covers the "Pipe! Unlocked!" style unlocks (research/flows.md). |
| `…/Content/{ItemCatalog,ItemKind}.swift`, `Geometry/*` (camera, lanes, projector, tray, visibility), `Meta/{ChiefsTool,DailyBonus,KeyChallenge}.swift`, `Rules/{TrayModel,GoalBoard,StarRule,BoosterRules}.swift` | MF's 3D tray / items / goals / meta | **NO** | MF-specific. `KeyChallenge` (a 30-step reward ladder filled by keys banked on wins) is only a pattern reference for the Claw Challenge (a 20-step ladder filled by per-win streak points). |
| `Sources/mflevels/main.swift` (169) | CLI over the core (validate / bot) | adapt (pattern) | `Packages/PathCore/Sources/pclevels/main.swift` (neutral name) for the content owner |
| `Tests/MFCoreTests/APISurfaceTests.swift` (196) | Imports the core WITHOUT `@testable`: the frozen-contract check (§8.2) | adapt | `PathCoreTests/APISurfaceTests.swift` |
| `App/Support/LaunchArgs.swift` (190) | ◆ One struct for every `-mf.*` hook, `raw` for private flags | **adapt** | `App/Support/LaunchArgs.swift` with `-pc.*`. Keep: `reset, state, level, go (home/level/shop/settings/boardlab/soundboard), popup, seed, coins, lives, livesNextIn, unlimitedLives, tutorials, now, timer, freezeTimer, timerRuns, win, lose (timeUp/hearts/quit), autoplay, autoplayRate, autoplayStop, bench, hud, slowmo, freezeAt, capture, probeFile, tune`. Drop: `tray, goals, stock (→ boosters), camera, shadows, fx rk, items, pinAttempt`. |
| `App/Support/Log.swift` (38) | os.Logger + stdout line `"<uptime> [MF][cat] msg"` | copy + rename | `App/Support/Log.swift`: subsystem `com.manycode.arrowout`, tag `[PC]`. tools/bench.py and capture.py parse this format. |
| `App/Support/Tuning.swift` (209) | ◆ One JSON per owner (`Tuning/{board,game,ui}.json`), compiled-in defaults, `-mf.tune file.key=v` | **copy** + rename | `App/Support/Tuning.swift` (`-pc.tune`). The spike's Tunables values move into `board.json`. |
| `App/Support/MotionClock.swift` (75) | ◆ The one game clock: slow motion + capture freezes act here | copy + rename | `App/Support/MotionClock.swift`. The board's CA layers use `layer.speed` / `timeOffset` on the stage (spike `freeze()`), driven by it. |
| `App/Support/PerfMonitor.swift` (55) | 600-frame window, fps / p95 / p99, phys_footprint | copy | `App/Support/PerfMonitor.swift` (feeds `-pc.hud debug` and bench) |
| `App/Support/PlayerStore.swift` (103) | The app's single PlayerState; debounced saves; `saveNow` on start / finish / background | copy + rename | `App/Support/PlayerStore.swift` |
| `App/Brand.swift` (26) | ◆ The only place the product name comes from (build setting → Info.plist → `Brand.name`) | copy + rename | `App/Brand.swift` (`PC_BRAND_NAME` = "Arrow Out" (the owner's product name, 02:33)) |
| `App/Contracts/{Audio,Board,Presentation,Shell}Contract.swift` | ◆ Frozen protocols between owners (+ sha256) | adapt (pattern) | `App/Contracts/*` written by WP0. `AudioContract.swift` must keep `enum SoundID`, `enum MusicID` and `var bus: AudioBus { … return .music }`, because tools/audio/specs.py parses them. |
| `App/Audio/{AudioCore,AudioGraph,MusicPlayer,SoundBank,AudioRamps}.swift` (platform-neutral) + `AudioEngine.swift`, `AudioPlayingExtras.swift`, `SoundBoard.swift`, `Haptics.swift` | The full engine: 12 SFX voices → varispeed → buses → limiter; music decks with seamless loops; sting → pad chains; `.ambient` session; offline tests; debug SoundBoard | **adapt** | `App/Audio/*` (A2). Cue rules (voice caps, retrigger, ducks) come from our SPEC-motion-audio. `SoundBoard` → `-pc.go soundboard`. The engine reads tools/audio/manifest.json relations (variants, sized, chains). |
| `App/Shell/Components/GlyphText.swift` (255) | Outlined casual-game text from CoreText glyph paths (stroke, fill or gradient, extrusion); takes `LocalizedStringResource` | **adapt** | `App/Shell/Components/GlyphText.swift` in `PCDisplay-Black` ("Perfect!", "Out of Time!", "Level 32", the LEVEL plate). Pick it or GlossyChrome's `OutlinedLabel` by side-by-side. |
| `App/Shell/Components/{MFButton,Toast,ShellLayout,Tokens,UIArt,Panel,ToggleButton,TutorialBubble,LivesPill,Badge}.swift` | Press 0.95× + click + spring; text-only toast; 393×852 → live-screen mapping; token loader; raster-with-placeholder; popup chrome; toggles; tutorial bubble + glove; top pills; badges | adapt | `ShellLayout` → copy (same canvas). `MFButton` → `GameButton.swift`. `Toast`, `UIArt` (our cases; a placeholder must never ship, §14), `Tokens` (loads OUR ui-tokens.json) → adapt. `Panel` / `ToggleButton` / `TutorialBubble` / `LivesPill` / `Badge` → ref (our looks are GlossyChrome + art). |
| `App/Shell/Popups/PopupHost.swift` (307) + `PopupChrome.swift` (41) | A stack of async popups (`present` awaits the answer), dim per style, spring-in panel, on the 393×852 canvas | **adapt** | `App/Shell/Popups/PopupHost.swift`. Our popups: Paused, Out of Time!, Continue? (streak), Continue? (life), Level Failed, Perfect!, feature unlock, Claw info, Sky Jump. Timings come from our motion.md. |
| `App/Shell/Popups/*` (the other 16 files) | MF popups | ref | Structure only |
| `project.yml` | One app + unit + UI targets, local package, folder resources, postCompile sync, base Info.plist, brand setting | **adapt** (WP0) | `apps/mazeout/project.yml`: name `ArrowOut`, package `PathCore`, `com.manycode.arrowout`, `PC_BRAND_NAME`, base `App/Info.plist` for `UIAppFonts` (`PCDisplay-Black.ttf`) + `CADisableMinimumFrameDurationOnPhone` (§3.3). iPhone only, portrait. No StoreKit config (FakeStore). |

### 3.5 Other tools (reference; owners copy when they need them)

- **Motion and sound analysis:** `apps/matchfactory/research/motion-tools/` (05424db).
  - Contents: `mfx.swift`, `mf.py`, `taps.py`, `evavg.py`, `spec.py`, `excess.py`, `ov.py`, `README.md`.
  - Owner: the motion analyst. Target: `research/motion-tools/` (already gitignored for `w/` and the `mfx` binary). Set `V`/`MFX` in `mf.py`.
  - Research also has its own `research/tools/frames2` (decodes every sample of the short phone clips).
- **3D + UI art pipeline:** already copied by the art spike into `art/pipeline/` and `art/ui/tools/` (dbf4543; art/PIPELINE.md). Not REUSE's.
- **MF content:** `design/tools/gen_levels.py` (c4ebdbc) and `tools/levels/{build,fit_l1}.py` (working tree ahead of 05424db) are **ref**: MF level JSON.
- **Workflow templates:** `tools/gameprompt/workflows/{1-research,2-spec,3-art-round1,3b-art-round2,4-build}.js` (05424db) are for the orchestrator (GAMEPROMPT §11), not app code.

### 3.6 Proposed layout (for the architecture spec to confirm)

```
App/GameApp.swift  App/Brand.swift  App/Info.plist (base: UIAppFonts, CADisableMinimumFrameDurationOnPhone)
App/Contracts/     Audio, Board, Presentation, Shell contracts (◆ frozen, sha256)
App/Board/         BoardHost, BoardView, ReleaseTapRecognizer, ArrowNode, Mover, Track, StarTrail, Palette,
                   BoardController, TutorialHandLayer, BoardLab            (spike + Arrows controller)
App/FX/            Confetti, win sign, rockets
App/Game/          GameScreen, HUD, boosters, directors (tutorial, fail flow)
App/Shell/         Components (GlossyChrome, GlyphText, GameButton, Toast, ShellLayout, Tokens, UIArt), Popups (PopupHost ...),
                   Home, Shop (FakeStore), Events (Streak Race, Claw, Sky Jump: offline or honestly locked)
App/Audio/         MF engine (A2) + Haptics
App/Support/       LaunchArgs, Log, Tuning, MotionClock, PerfMonitor, PlayerStore, Settings
App/Resources/     Levels/, Tuning/{board,game,ui}.json, Sounds/, Music/, Fonts/PCDisplay-Black.ttf, Strings/strings.tsv,
                   Localizable.xcstrings
Packages/PathCore/ Sources/PathCore/{Model,Rules,Solver,Generator,Geometry,Content,Session,Economy,Persistence,Random,Motion}
                   Sources/pclevels (CLI)   Tests/PathCoreTests
Tests/ UITests/ tools/ project.yml
```

---

## 4. Must NOT carry over (Arrows- and MF-specific)

**Arrows' game rules.**
- Arrows is **hearts-only**: no timer, 3 hearts, an out-of-hearts dialog with Play On / Restart, a free Hint pill after 10 s, a ↻ restart.
- Maze Out is **timed + hearts**:
  - 3:00 on L32, starting at the FIRST tap;
  - 3 hearts shown in the timer pill; a bump costs one;
  - fail on time-out or on hearts;
  - the fail flow is Out of Time! (Add Time +30 s, 900 coins) → Continue? (lose your streak, Play On 900) → Continue? (lose a life) → Level Failed / Try Again;
  - boosters (crystal/magnet, bulb) with stock badges.
- `GameModel` / `GameEngine` / `OutOfHeartsDialog` / `HintPill` rules stay out.

**Arrows' ray rule.** The ray is scanned to the edge of the occupied BOUNDS. Ours runs to the GRID edge, door cells block,
and tape bundles are one unit.

**Arrows' input.** `UITapGestureRecognizer` plus a long-press "preview". The original fires on RELEASE even after a 5 s hold
(research/levels.md), so use `ReleaseTapRecognizer`.

**Arrows' Game Center** (`GameCenter.swift`, "Account link"). No Game Center, no network. Maze Out's leaderboards and
"players" (Streak Race, Sky Jump's 100 players) are offline simulations or honest locked states, per PLAN.md.

**Arrows' tab bar** (`TabBar.swift`: Material-3, 4 tabs, Daily/Collection locked, `ComingSoon`). Maze Out has a different
bottom nav: shop basket · raised Home · trophy.

**Arrows' shell.**
- Settings (Account link, Remove ads, Rate, Write to us, Privacy/Terms in Safari), `LanguageSheet` (10 languages), dark mode.
- Instead: EN + TR following the device, and a Pause panel with Sound/Haptic toggles; the home gear panel is taken from
  research.
- The support-mail rule is suspended for this job.

**Arrows' `RatingPrompt`** (a custom card after L5). The original shows the iOS system sheet after L34 (research/flows.md);
the specs decide whether to call `SKStoreReviewController`.

**Arrows' `Store.swift`** (real StoreKit, Remove ads). Use FakeStore; the owner rejects all purchases.

**Arrows' `DotsLayer`** (a layer per cell) and **`BoardGeometry`** (0.10p corner radius, a different head). Superseded by the
spike's measured geometry.

**Arrows' look.** Albert Sans, praise words, logo and the Arrows palette. Ours: PCDisplay-Black (Nunito), the "Perfect!"
popup, the "MAZE OUT!" sign as our own art.

**MF-specific.**
- The RealityKit engine (ARView, CustomMaterial outline, inverse-LUT, tray, items, goals, merges).
- `ItemCatalog`, the item icons and `sync_art`'s USDZ.
- ChiefsTool, DailyBonus and KeyChallenge content.
- The TL shop table, MF popups' copy, MF's strings `SUPERSEDED` rows.
- MF regions / annotations / manifest.
- MF's cue recipes and compositions.
- The bench's RealityKit stats and MF log regexes.

---

## 5. DECISIONs taken in this package

1. **`FLAT_MAX` = 0.97, not 0.88** (tools/capture-shot.sh, capture.py).
   - Reason: a white Maze Out board late in a level (≈ 5 arrows, no popup) is ≈ 92 % white. Arithmetic: 334,836 pt² screen;
     arrows ≈ 2,900 pt², dots ≈ 3,600, HUD + boosters ≈ 20,000 → 92 %. So 0.88 would reject real frames.
   - Measured on synthetic frames: a blank frame = 1.000 → rejected; a white board with a HUD pill and 3 strokes = 0.965 →
     kept.
   - The fraction is always printed, and every frame must still be LOOKED at.
2. **Strings coverage checks the EN column** for measured copy: the original's UI is English. TR is ours, and build.py
   requires it on every row.
3. **The audio checker fails on an empty contract.** Its self-test adds 4 mutations and counts only applicable ones; none are
   skipped silently.
4. **Proposals the architecture spec must confirm or change in the same commit as the tools:**
   - `Log` line format + the bench `MARKS` table;
   - `Documents/{lab-ready,lab-perf,capture-ready,probe}.json`;
   - the `-pc.*` list (§3.4);
   - `App/Contracts/AudioContract.swift`;
   - `App/Resources/Levels/` (bench `LEVELS_DIR`);
   - the debug-HUD text (`"<fps> fps p95 <ms> p99 <ms> ms"`, `"<MB> MB <n> layers <n> movers"`) and its position (`HUD_CROP`);
   - `Application Support/Save/`;
   - `PC_BRAND_NAME`.

---

## 6. Verification (what ran; what did NOT)

**Syntax.**
- 13 shell scripts: `bash -n` and `sh -n`.
- 18 Python files: `python3 -m py_compile`.
- 4 JSON files: `json.load`.
- 1 Swift CLI: `swiftc -O tools/bench/hudocr.swift` (1.6 s).

All green.

**Smoke tests (scratchpad; nothing written into the app tree except the deliverables).**
- **strings/build.py:**
  - a good TSV → the catalogue, and `--check` is up to date; TR reorder `%2$lld … %1$@` is written positionally.
  - a bad TSV → 5 errors, nothing written: wrong argument ORDER, the brand in both columns, a trailing space, unbalanced `**`.
- **strings/coverage.py:** exact / instance (`+30 sec` for `+%lld sec`, `Level 32` for `Level %lld`) / superseded / MISSING,
  a missing non-optional source = FAIL (optional = skipped), tutorial keys, and the Swift literal regex
  (`Text("Level \(level)")` → `Level %?`; `verbatim:` ignored).
- **audio:** a fixture contract with 6 SoundIDs (one-shots, variant, loop, sting → pad chain, sized tick) + 1 MusicID and
  scratch recipes.
  - `sfx.py` wrote 9 files and the manifest; `music.py` wrote the loop; `check.py --reproduce` was **all green**, 10/10
    byte-identical.
  - `check_selftest.py`: **caught 15/15**.
  - In the real tree: check.py fails with a clear missing-contract message; an empty contract FAILS; the self-test exits 2
    (nothing shipped).
- **compare:** synthetic ref + EN/TR captures.
  - compare_all → EN 0 over 6 (worst ΔE 1.5); TR 1 over 6 (ΔE 45.6).
  - summarize exits 1 on the unannotated region.
  - sbs PNGs written.
- **flat_check:** a blank frame is rejected (exit 3, renamed `.rejected.png`); a sparse board is kept.
- **bench:**
  - `report` on a synthetic soak log in our `[PC]` grammar: 3 attempts (a timeUp loss then a win), homes after L1/L2,
    growth fit, frame windows;
  - `--help`;
  - hudocr on research shot 003 read `"Level 32", "3:00"` (a read-only OCR test, not an asset).
- **gen.sh:** two concurrent runs on a scratch project serialised through the mutex; both generated, and the lock was removed.
- **build.sh / test.sh / iso-build-copy.sh / wait-build.sh:** run with a STUB `xcodebuild` on PATH (no compile):
  - correct `-project`/`-scheme`/`-destination id=<slot UDID>`/`-derivedDataPath`/`-jobs 4 -quiet`/action;
  - the iso copy's `patch.py` changed the copy only;
  - the swap guard exited 75 when forced.
- **play-watch.sh:** refuses a missing or slot `PLAY_UDID`.
- **sync_art.sh:** against the real `art/out` + `art/ui/out` → 5 Art + 2 UI PNGs in a scratch bundle.
- **grep:** no `-mf.`, `[MF]`, MF / Arrows UDIDs, `com.manycode.matchfactory|arrows`, `peakgames`, `ecffri`, `arrowjam` or
  `grandgames` outside provenance comments.

**NOT run (machine rules: no simulators, no xcodebuild in this workflow):**
- `run.sh`, `capture-shot.sh`, `capture.py`;
- bench `lab`/`launch`/`level`/`soak`;
- real `build.sh`/`test.sh`/`core.sh` (no project or package yet), and the `sim_boot` / nsurlsessiond chmod path.

WP0 is the first real user of all of these: run `tools/gen.sh && tools/build.sh B && tools/run.sh B` once and fix anything
found here.

---

## 7. Open items for others

1. **Orchestrator:** commit `build/spike/{App,UITests,tools,project.yml,Support}` to a tracked path (e.g. `design/spike-src/`)
   before anything cleans `build/`. It is the board's source (§3.1) and exists only in the working tree.
2. **Architecture spec / WP0:**
   - confirm or replace every proposal in §5.4 and the §3.6 layout;
   - wire `tools/sync_art.sh` (with `ENABLE_USER_SCRIPT_SANDBOXING: NO`) or use an asset catalog;
   - write `App/Contracts/AudioContract.swift` in the shape specs.py parses.
3. **Spec writers:** point `tools/strings/sources.json` at the real string sections of SPEC-ui / SPEC-gameplay / ui-tokens /
   levels.json. Coverage fails until then, by design.
4. **A1 audio:**
   - fill `tools/audio/specs.py` + `sfx.py` `RECIPES` + `music.py` `RENDER` from SPEC-motion-audio;
   - run `check.py --reproduce` and `check_selftest.py` (all applicable mutations must be caught).
5. **V2:** fill `tools/capture/manifest.json` (≥ 30 EN + TR), `tools/compare/regions.py` (from SPEC-ui boxes) and
   `annotations.json`.
6. **V3 / BOARD:** print the `MARKS` lines and the debug HUD in the proposed format (or update bench.py in the same change),
   and set `HUD_CROP`.
7. **Content owner:** port Arrows' `arrowlib.py` / `render.py` / `extract_levels.py` into `tools/levels/` (ray to the grid
   edge; tapes / doors / keys) for the IoU ≥ 0.99 overlay proof, unless research/bot already provides it.
