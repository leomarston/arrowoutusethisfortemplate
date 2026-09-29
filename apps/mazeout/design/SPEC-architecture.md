# Arrow Out: architecture, engine and build plan (V1)

Architecture writer, 2026-09-25 (+03). The engineering half of the V1 spec for **Arrow Out**, our 1:1 copy of "Maze Out! - Tap
Puzzle" (Grand Games, `com.grandgames.arrowjam` v552). It turns the research, the art pipeline and the tech spike into:
- one Xcode project and one pure-Swift core package,
- a module layout where every file has exactly one owning work package,
- exact public APIs (the frozen ◆ contracts),
- engine numbers and engine rules,
- test hooks, performance budgets (the owner's FEEL acceptance),
- an ordered build plan over two simulator slots.

The owner's sentence (verbatim, PLAN.md): *"Read GAMEPROMPT.md and make Maze Out on my phone. ultracode ultrathink"*.

**PRECEDENCE (repeat of PLAN.md).** The repo's app-factory rules are SUSPENDED for this job: no app-factory skill, no
paywall/Restore gates, no RevenueCat, ASO, App Store Connect or submission; do not read PROJECT_LOG.md, docs/DESIGN.md or
docs/ASO.md (one line is appended to PROJECT_LOG.md in the final commit). EN (base) + TR only. iPhone only. Still binding:
one-app-per-task, commit-when-work-is-done (orchestrator only), verify-real-not-mock, never-ship-stand-in-content, offline game, honest
reports, never weaken a failing test, never spend money.

**Copying line.** Rules, systems, timings, layouts and flows are copied 1:1. Every asset is ours (code, our SVG, our 3D renders,
our synthesised audio, OFL fonts). Captures and videos are references to LOOK at only. The product name is **"Arrow Out"** (OWNER
02:33) and lives behind one `Brand` constant; code prefixes are neutral (`PathCore`, `-pc.`, `[PC]`, `PCDisplay`); no file name
contains "maze", "mo", "grand" or "arrowjam". The folder `apps/mazeout` and the branch `build/mazeout` stay (internal only).

---

## 0 Read this first

### 0.1 What this document decides
| This document decides | The content specs decide (`design/SPEC-gameplay.md`, `SPEC-ui.md`, `SPEC-motion-audio.md`, `SPEC-social.md`) |
|---|---|
| Project, targets, folders, **file ownership**, build commands | Screen layouts, colours, text styles, copy (EN + TR) of every screen (SPEC-ui + `design/ui-tokens.json`) |
| PathCore public API: models, level JSON decoding, rules engine, session state machine, the one event stream, clock, economy/boosters/events/social **module boundaries**, persistence format, RNG, solver/validator/generator | Rule VALUES: timers, prices, rewards, refill interval, booster effects, fail-chain wording, event ladders, unlock levels (SPEC-gameplay + `design/levels.json`) |
| The Core Animation board engine: layers, input, hit test, zoom, movers, obstacle layers, warm-up | Motion and sound values: every curve's numbers, cue list, synthesis recipes, haptic intensities (SPEC-motion-audio) |
| Audio/haptic engine structure; the same-frame feedback pipeline | The social world's model: population, name generation, score dynamics, race bots (SPEC-social) |
| Test hooks, capture mode, probe, labs, accessibility ids, log contract, performance budgets, work packages | Per-level content (the level files are generated from `design/levels.json`) |

If a number appears both here and in a content spec, **the content spec wins for looks, values and content; this document wins
for code structure and engine behaviour.** Numbers that are not known yet are written as data-driven knobs and marked
`PENDING-<spec>`; §14 indexes them. Whoever notices a conflict flags it to the orchestrator; nobody edits another spec.

### 0.2 Evidence tags and source shorthands
- **VERIFIED** (source): seen in the phone captures, the owner's videos, measured in the spike, or produced by the art pipeline.
- **INFERRED**: reasoned from indirect observations; the reasoning is given.
- **DECISION**: our choice (unobservable, or an engineering matter).
- **PENDING-gameplay / PENDING-ui / PENDING-motion-audio / PENDING-social**: the value belongs to that spec (written after this
  one); the API here already carries the knob, and the default shown is a placeholder the spec replaces.

Shorthands: `levels` `flows` `obstacles` `items` `motion` `sounds` `tutorials` `web` = `research/<name>.md`; `vflows` =
`research/video-flows.md`; `spike` = `design/tech-spike.md`; `REUSE` = `design/REUSE.md`; `fonts` = `design/fonts.md`; `uim` =
`design/ui-measure.md`; `tokens` = `design/ui-tokens.json`; `STYLE` `PIPE` `ID-MAP` = `art/STYLE.md`, `art/PIPELINE.md`,
`art/ID-MAP.md`; `MANIFEST` = `art/MANIFEST.json`; `GP` = `GAMEPROMPT.md`; `PLAN` = `apps/mazeout/PLAN.md`; `shot NNN` =
`research/shots/NNN-*.png`; `V1`/`V2` = the owner's videos (`research/video/owner/`); `Lnnn.json` = `research/levels/Lnnn.json`.

### 0.3 Reference device and units
- Reference screen **393 × 852 pt** = the owner's iPhone 15 (60 Hz, A16), where every phone capture was made; captures are
  1178 × 2556 px (pt = px × 393 / 1178). The simulators "Maze A"/"Maze B" are iPhone 16s (iOS 26.0) of the same point size
  (VERIFIED PLAN). The owner's videos are 592 × 1280 px (pt = px × 393 / 592, VERIFIED tutorials §0).
- Screen positions are **pt**, times **seconds**, board lengths **cells** (1 cell = the lattice pitch). The board's own
  coordinate space ("content space") is pt at fit zoom; the scroll view zooms it.
- The original hides the iOS status bar on every screen and draws into the full 852 pt (VERIFIED uim "How to read").

### 0.4 What the game is (one paragraph for engineers)
A timed escape puzzle. A white board holds black snake arrows on a hidden square grid. Tapping an arrow (fired on **release**)
sends it out along its own path if the ray from its head to the grid edge is clear; otherwise it **bumps** the first thing in
its way, turns red for the rest of the level, and a heart is lost. The timer (3:00, 2:30, 2:00, 3:30 … per level) starts at the
**first tap**; 0 hearts or 0 time opens a chain of 900-coin continue offers, then "Level Failed". Obstacles: taped bundles move
together, keys open doors that hide arrows, pipes carry arrows through (a counter per pipe), boxes/curtains break after N clears,
elevators reveal a second layer, corners deflect. Levels 1-4 are one four-board session. The meta is offline coins, lives,
2 boosters, Hard/Super Hard levels, and online-looking events and leaderboards that we SIMULATE offline (OWNER 02:33 point 3).

---

## 1 Decisions at a glance

| # | Decision | Tag / why |
|---|---|---|
| D1 | The game core is a local SwiftPM package **`PathCore`**: pure Swift, Foundation + CoreGraphics only (the spike's core is CG-based), no UIKit/SwiftUI/QuartzCore. It is tested with `swift test` **on macOS**, with no simulator. | DECISION (GP §8.1; two simulator slots only on this 16 GB Mac). |
| D2 | The board is **UIKit + Core Animation**: one `CAShapeLayer` body + one head layer per resting arrow inside a `UIScrollView`, every motion a `CAAnimation` on the render server, hosted in the SwiftUI shell by a `UIViewRepresentable`. | VERIFIED spike verdict "GO" (304 arrows, 0 frames > 20 ms at 3× with 5 exits, 22–26 MB). |
| D3 | **Input fires on RELEASE** through the spike's `ReleaseTapRecognizer` (never `UITapGestureRecognizer`), with grid-maths hit testing. | VERIFIED levels "Input model" (5 s press, fires at lift-off), spike P5. |
| D4 | **The core resolves a tap into a plan; the board plays the plan.** Logical state changes at the tap (an arrow leaves the blocking grid when tapped, VERIFIED motion §2.1 P02 queued tap); visual beats (dots, pipe passes, key flight) carry an arc position `s` in cells that the board converts to time with the measured exit kinematics. Presentation-timed facts (bump contact → heart, door burst → door opens, last exit left the board → celebration) come back to the core as **acks**. | DECISION (MF pattern "the core never guesses visual timing"). |
| D5 | **Exit kinematics are in board space (cells):** `s(τ) = 71.4·τ − 21.29·(1 − e^(−τ/0.323))` cells; the exit ends when the tail leaves the **screen**, passing under the HUD. | VERIFIED motion §1, §2.3 (5 exits, 3 zooms, RMS 0.079 cells). |
| D6 | **Fit rule:** `pitch = min(W/(cols+2), H/(rows+2), 28.07)` pt with the play rect 122…755 pt; zoom min **0.786× fit**, max = **absolute 28.07 pt per cell** (`maxZoom = max(1, 28.07/pitch)`). | VERIFIED levels L47 probe + L50 (small board opens at the cap); the fit reproduces every measured L32–L61 pitch (§4.2). |
| D7 | **One session state machine, one ordered event stream** (`SessionEvent`) consumed by board, HUD, FX, audio, haptics and directors, in a fixed fan-out order on the same frame. Multi-board sessions ("Levels 1-4") are stages inside one session. | DECISION (GP §8.1); VERIFIED tutorials §2 (one session, four boards, one win panel, 80 coins). |
| D8 | **Same-frame feedback:** the release handler resolves the tap, adds the ripple and mover layers, calls the haptic and schedules the sound, all before the run-loop's CA commit, so all four land on the first presented frame. | OWNER 03:00 (binding); VERIFIED original: ripple and first arrow change on the same frame (motion §2.1). |
| D9 | **Levels:** authored levels are bundled per file (`Levels/level_NNNN.json`, generated from `design/levels.json`); levels beyond the authored set are **generated at runtime** by the same solver-gated generator, deterministic per level number. | DECISION; INFERRED need for unlimited levels (vflows §9.1: World board players at level 8k–11k). |
| D10 | **Social = an offline, deterministic world** in `PathCore/Social`: stateless keyed hashes of (install seed, labels, time) with IEEE-exact arithmetic, Python reference `design/social/tools/socialsim/`, bit-exact goldens, a rewind-safe clock. | OWNER 02:33 point 3; DECISION on the method (the social designer's reference already fixes the arithmetic rules). |
| D11 | Persistence: one versioned Codable `PlayerState` JSON (atomic write + backup), module sub-states owned by their modules. **No `@AppStorage` for any state**, settings included. | DECISION (GP §13; memory appstorage-in-observableobject). |
| D12 | RNG: `PathRandom` (xoshiro256**, SplitMix64 seeding, named forks) pinned against `tools/rng_ref.py`. Social uses the stateless hash of the socialsim reference, not `PathRandom`. | DECISION (REUSE §3.4). |
| D13 | Shell: SwiftUI + Observation; HUD writes ≤ 10 Hz; a stackable async popup host; heavy particle FX (confetti, fireworks, coin fly, shards) are **Core Animation layers**, not per-frame SwiftUI `Canvas`, so the main thread stays idle during celebrations. | DECISION (FEEL requirement; GP §8.1 HUD rule). |
| D14 | Home characters are **cut-out puppets** from the art rigs (`art/out/char_*_rig/rig.json`), animated by looping `CAAnimation`s on the render server (0 main-thread cost at rest). | DECISION (art route C1, PIPE §3). |
| D15 | Glossy chrome = `art/ui/code/GlossyChrome.swift` (UI-ART's file) **compiled into the app as-is**; text effects = one cross-platform `GameText` (CoreText glyph paths: gradient face, outside outline with round joins, solid drop). | DECISION (STYLE decision summary B1; fonts §6). |
| D16 | Board obstacle sprites are the art pipeline's @3x PNGs drawn at the **design pitch 32 pt**, scaled by `pitch/32`; pipe tubes, arrows, dots, ripple, trails are vector code. Counter digits are CoreText glyph paths in `CAShapeLayer`s (crisp at every zoom; no `CATextLayer`). | VERIFIED PIPE §0.3, STYLE §A.2; DECISION for digits. |
| D17 | Audio: `AVAudioEngine` started at boot and never stopped in play, `.ambient` session, 5 ms IO buffer, pre-decoded buffers on pre-started player nodes. The cue list is data (PENDING-motion-audio); v552's in-level play is **silent** except UI clicks, the coin collect and the unlock chime (VERIFIED sounds §1). | VERIFIED + DECISION; the owner's "tap sound" wish is an open question (§7.2). |
| D18 | Shop: `FakeStore` everywhere (tests, captures, the phone install); StoreKit 2 + a local `.storekit` file only on the scheme's Run action; "Test store: nothing is charged". | GP §6.3; owner's order to reject purchases. |
| D19 | Swift 5 language mode, `SWIFT_STRICT_CONCURRENCY: minimal`, iOS 18.0, **iPhone only, portrait**, no third-party dependencies, no network, no analytics, no ads, no ATT. | DECISION (GP §6.3; MF D16; spike P6 strictness). |
| D20 | Localisation: EN base + TR in `Localizable.xcstrings`, generated from TSVs by `tools/strings/build.py`; the original's UI is **English**, so EN copies the captures exactly and TR is ours. | VERIFIED flows header ("Game UI is ENGLISH"); REUSE §5.2. |
| D21 | Launch arguments `-pc.*` exist in every configuration (dev build; no submission); the Release build with no arguments boots to the real first-run state. | DECISION (MF D-precedent; GP §9.4). |
| D22 | No publisher splash: our launch goes straight to the Loading screen (the original's "grand" splash is Grand Games' brand). | DECISION (tutorials §1 row 1: "ours: our own studio splash, or none"). |
| D23 | Exit colour is chosen per exit by the **combo ladder** (blue, blue, violet, rainbow…, window ≈ 1.25 s); a debug override forces solid or rainbow. | INFERRED motion §2.4 (84 % agreement over 1630 taps); supersedes PLAN DECISION 02:05 "solid default, rainbow behind a setting" (the phone shows both). |
| D24 | The iOS rating sheet is requested once, on home after the L34 win (StoreKit `AppStore.requestReview(in:)`, the iOS 16+ form of `SKStoreReviewController.requestReview(in:)`, which is deprecated on iOS 18). | VERIFIED flows (phone, after L34) + tutorials §9 (V2, after L34). |

---

## 2 Project

### 2.1 Identity
| Key | Value |
|---|---|
| Project / scheme | `ArrowOut` (xcodegen; `ArrowOut.xcodeproj` is gitignored and never edited by hand) |
| Targets | `ArrowOut` (app), `ArrowOutTests` (unit, hosted), `ArrowOutUITests` (UI) |
| Bundle ids | `com.manycode.arrowout`, `.tests`, `.uitests` (OWNER 02:33; PLAN's older `com.manycode.mazeout` is superseded) |
| Team / signing | `GDU77F3MXL`, automatic signing |
| Deployment | iOS 18.0; `TARGETED_DEVICE_FAMILY = 1` (iPhone); portrait only; status bar hidden |
| Version | `MARKETING_VERSION 0.1.0`, `CURRENT_PROJECT_VERSION 1` |
| Display name | `$(PC_BRAND_NAME)` = **"Arrow Out"** |
| Local package | `Packages/PathCore` (library `PathCore`, executable `pclevels`) |
| App entry file | `App/GameApp.swift` (neutral name, REUSE §1) |

### 2.2 `project.yml` (the LEAD writes it in WP0; nobody else edits it)
```yaml
# The one Xcode project (SPEC-architecture §2.2). LEAD-owned. Regenerate with tools/gen.sh (mutex) after adding,
# removing or renaming any file. ArrowOut.xcodeproj is gitignored.
name: ArrowOut
options:
  bundleIdPrefix: com.manycode
  deploymentTarget: { iOS: "18.0" }
  createIntermediateGroups: true
packages:
  PathCore: { path: Packages/PathCore }
settings:
  base:
    SWIFT_VERSION: "5.0"
    SWIFT_STRICT_CONCURRENCY: minimal
    DEVELOPMENT_TEAM: GDU77F3MXL
    CODE_SIGN_STYLE: Automatic
    ENABLE_USER_SCRIPT_SANDBOXING: NO          # tools/sync_art.sh writes into the product bundle
    PC_BRAND_NAME: "Arrow Out"                  # the owner's product name (OWNER 02:33); the ONLY place it is spelled
  configs:
    Release: { SWIFT_OPTIMIZATION_LEVEL: "-O", SWIFT_COMPILATION_MODE: wholemodule }
targets:
  ArrowOut:
    type: application
    platform: iOS
    sources:
      - path: App
        excludes: ["Info.plist", "Resources/StoreKit/**", "Resources/Levels/**", "Resources/Sounds/**",
                   "Resources/Music/**", "Resources/Tuning/**", "Resources/Fonts/**", "Resources/Social/**",
                   "Resources/Strings/**"]
      - path: art/ui/code                        # GlossyChrome.swift (UI-ART owns it; compiled in as-is, D15)
        includes: ["*.swift"]
      - { path: App/Resources/Levels, type: folder, buildPhase: resources }   # -> bundle/Levels/
      - { path: App/Resources/Sounds, type: folder, buildPhase: resources }   # -> bundle/Sounds/
      - { path: App/Resources/Music,  type: folder, buildPhase: resources }   # -> bundle/Music/
      - { path: App/Resources/Tuning, type: folder, buildPhase: resources }   # -> bundle/Tuning/
      - { path: App/Resources/Fonts,  type: folder, buildPhase: resources }   # -> bundle/Fonts/
      - { path: App/Resources/Social, type: folder, buildPhase: resources }   # -> bundle/Social/ (name lists)
      - { path: App/Resources/StoreKit/ArrowOut.storekit, buildPhase: none }
    dependencies:
      - package: PathCore
        product: PathCore
    postCompileScripts:
      - name: Sync art (art/ui/out -> UI/, art/out -> Art/)
        script: '"$SRCROOT/tools/sync_art.sh"'
        basedOnDependencyAnalysis: false
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.manycode.arrowout
        GENERATE_INFOPLIST_FILE: YES
        INFOPLIST_FILE: App/Info.plist           # base plist: array keys (UIAppFonts) + ProMotion opt-in (§2.3)
        INFOPLIST_KEY_CFBundleDisplayName: "$(PC_BRAND_NAME)"
        INFOPLIST_KEY_UISupportedInterfaceOrientations: UIInterfaceOrientationPortrait
        INFOPLIST_KEY_UIStatusBarHidden: YES
        INFOPLIST_KEY_ITSAppUsesNonExemptEncryption: NO
        TARGETED_DEVICE_FAMILY: "1"
        MARKETING_VERSION: 0.1.0
        CURRENT_PROJECT_VERSION: 1
        ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon
  ArrowOutTests:
    type: bundle.unit-test
    platform: iOS
    sources: [Tests]
    dependencies: [{ target: ArrowOut }, { package: PathCore, product: PathCore }]
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.manycode.arrowout.tests
        GENERATE_INFOPLIST_FILE: YES
        TEST_HOST: "$(BUILT_PRODUCTS_DIR)/ArrowOut.app/ArrowOut"
        BUNDLE_LOADER: "$(TEST_HOST)"
  ArrowOutUITests:
    type: bundle.ui-testing
    platform: iOS
    sources: [UITests]
    dependencies: [{ target: ArrowOut }]
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.manycode.arrowout.uitests
        GENERATE_INFOPLIST_FILE: YES
        TEST_TARGET_NAME: ArrowOut
schemes:
  ArrowOut:
    build: { targets: { ArrowOut: all, ArrowOutTests: [test], ArrowOutUITests: [test] } }
    run:  { config: Debug, storeKitConfiguration: App/Resources/StoreKit/ArrowOut.storekit }
    test: { config: Debug, targets: [ArrowOutTests, ArrowOutUITests] }
    profile: { config: Release }
```
- The `art/ui/code` source path compiles UI-ART's `GlossyChrome.swift` into the app (D15). The file must stay compilable for
  **iOS 18 and macOS 14** (the art renderer `art/ui/tools/swiftui_render.swift` compiles it too). Its top-level names are
  reserved (§6.11).
- Pitfall (GP §13): a new `.swift` or resource file is invisible until `tools/gen.sh` runs. xcodegen needs the mutex.

### 2.3 `App/Info.plist` (base plist; LEAD)
Array keys have no `INFOPLIST_KEY_` form and are dropped silently without a base plist (memory
infoplist-array-keys-need-a-base-plist):
- `UIAppFonts` = `Fonts/PCDisplay-Black.ttf`, `Fonts/PCDisplay-BlackItalic.ttf` (VERIFIED `design/fonts/`; fonts §7).
- `CADisableMinimumFrameDurationOnPhone` = YES (ProMotion opt-in; the owner's iPhone 15 is 60 Hz, so 120 Hz stays
  unverified, GP §13).
- `UIViewControllerBasedStatusBarAppearance` = NO, `UIRequiresFullScreen` = YES.
- `UILaunchScreen` = { `UIColorName` = `LaunchBackground` } (the Loading screen's base colour, PENDING-ui; the SwiftUI Loading
  screen takes over on the first frame, §6.3).
- `PCBrandName` = `$(PC_BRAND_NAME)`: `Brand.name` reads this key, so the product name has a single source (REUSE §1).
- No usage-description keys: no camera, microphone, location or tracking, and the notification permission prompt needs none.

### 2.4 `Packages/PathCore/Package.swift` (LEAD writes it in WP0; CORE owns it afterwards)
- `// swift-tools-version:5.10`; platforms `.iOS(.v18), .macOS(.v15)`; `swiftLanguageVersions: [.v5]`.
- Products: library `PathCore`; executable `pclevels`.
- Targets: `PathCore` (Sources/PathCore), `pclevels` (Sources/pclevels, depends on PathCore), `PathCoreTests`
  (Tests/PathCoreTests, depends on PathCore). No resources in the package: tests read fixtures from disk relative to
  `#filePath` (research JSON, `design/social/fixtures/`, `tools/rng_ref.py` outputs) — DECISION (SwiftPM resources must live
  inside the target folder).
- Imports allowed in `PathCore`: `Foundation`, `CoreGraphics`. Nothing else (`tools/core.sh` greps for `import UIKit|SwiftUI|
  QuartzCore|AVFoundation` and fails).

### 2.5 `tools/` (as copied by REUSE; every script derives `ROOT` = `apps/mazeout` from its own path)
| Script | What it does (read from the file) | Owner |
|---|---|---|
| `tools/slot.sh <A\|B>` | **Sourced** by the others. The single place that maps slot → simulator (A = "Maze A" `177520B6-4889-46C2-BDD9-155813D2B175`, B = "Maze B" `B80EDB24-6280-4C52-A63F-E8AADD245017`) and sets `DD=build/dd-<slot>`, `BUNDLE_ID`, `SCHEME=ArrowOut`, `PROJECT`, `APP`, `SIMLOG` (the console log inside the simulator's own `data/tmp`). Helpers: `sim_state`, `sim_boot` (boots only this slot, then `chmod 000` its nsurlsessiond cache), `sim_unblock_assets`, `swap_free_mb`, `wait_for_memory` (refuses < 3 GB disk; waits in 120 s steps while free swap < 400 MB, max 600 s, then exit 75). | LEAD |
| `tools/gen.sh` | `xcodegen generate` under the `build/.gen.lock` mkdir mutex (60 s). Finds xcodegen in `$XCODEGEN`, PATH, `~/.local/bin`. | LEAD |
| `tools/build.sh <A\|B> [args]` | Debug build for that slot into `build/dd-<slot>`, `-jobs 4 -quiet`, after `wait_for_memory`; runs gen.sh if the project is missing. | LEAD |
| `tools/run.sh <A\|B> [-pc.* args]` | `sim_boot` → terminate → install → `simctl launch --terminate-running-process` with stdout/stderr into the simulator's `data/tmp/pc-run-<slot>.log`, linked from `build/run-<slot>.log` (writing under ~/Downloads is denied by the sandbox). | LEAD |
| `tools/test.sh <A\|B> [-only-testing:…]` | `xcodebuild test` with the slot's destination and DerivedData, after `wait_for_memory`. | LEAD |
| `tools/core.sh [args]` | `swift build -j 2 && swift test -j 2` in `Packages/PathCore` (macOS, no simulator). | LEAD |
| `tools/sync_art.sh` | postCompile build phase: `art/ui/out/*.png` → bundle `UI/`, `art/out/*.png` → bundle `Art/`; skips `_*`; PNG only; missing folders skipped. | LEAD |
| `tools/iso-build-copy.sh <role> <A\|B> [action]` | Builds a snapshot copy (`build/iso-<role>/tree`: App rsynced, project.yml copied, Packages/art/design/Tests/UITests/tools symlinked, own DerivedData) while others are mid-edit; optional copy-only `patch.py`. | LEAD |
| `tools/wait-build.sh <role> <A\|B>` | Waits until App/ + PathCore sources were quiet 90 s and swap ≥ 400 MB, then runs iso-build-copy (5 attempts). May exceed 4 min: run in the background. | LEAD |
| `tools/play-watch.sh` | Keeps the latest slot build running on a separate "Play" simulator (`PLAY_UDID`, never a slot UDID). | LEAD |
| `tools/capture-shot.sh <A\|B> <name> [args]` + `tools/flat_check.py` | One capture that waits for `Documents/<READY>` (`capture-ready.json` or `lab-ready.json`), shoots with `simctl io … --mask=ignored`, converts to sRGB, rejects frames > `FLAT_MAX` 0.97 one tone (REUSE §5.1). | VERIFY |
| `tools/bench.sh` + `tools/bench/{bench.py,hudocr.swift}` | Host bench: `lab`, `launch`, `level`, `soak`, `report`, `heapdiff`; parses the `[PC]` log MARKS (§9.3) and OCRs the debug overlay (§9.6). | VERIFY |
| `tools/capture/{capture.py,manifest.json}` | V2 capture driver (ready file / log / probe conditions, EN + TR, bursts). | VERIFY |
| `tools/compare/*` | CIEDE2000 per region, side-by-side sheets, summary (V2). | VERIFY |
| `tools/strings/{build.py,coverage.py,sources.json}` | TSV → `Localizable.xcstrings` (argument ORDER check, brand check), coverage against spec sources + Swift literals. | CONTENT |
| `tools/audio/*.py` | Synthesis toolkit (dsp, instruments, sfx, music), `specs.py` (parses `AudioContract.swift`), `check.py`, `check_selftest.py`, `spectro.py`. Cue tables EMPTY until A1. | AUDIO |
| `tools/rng_ref.py` | Independent Python reference of `PathRandom` (SplitMix64 + xoshiro256**, forks, attempt seed). | CORE (read-only reference) |
| `tools/watchdog.sh` | The orchestrator's health watchdog (disk, caffeinate, phone runner, stall). | orchestrator (untouched) |

**WP0 amendments (LEAD, in the same change as project.yml):**
1. `slot.sh`: `CONFIG="${CONFIG:-Debug}"` and `APP="$DD/Build/Products/${CONFIG}-iphonesimulator/ArrowOut.app"`; `build.sh`
   and `test.sh` pass `-configuration "$CONFIG"`. Release is needed for every performance number (`CONFIG=Release tools/build.sh A`).
2. `sync_art.sh`: also copy `*_rig/rig.json` and the `char_*.json` placement sidecars from `art/out` (the puppets need them,
   §6.4); still nothing but PNG + JSON, still skipping `_*`.
3. `core.sh`: add the import grep of §2.4.
4. Write `build/wp0/frozen-contracts.sha256` (§3.5).

### 2.6 Machine and simulator rules for every build agent
VERIFIED: memory max-two-parallel-builds, parallel-agents-and-simulators, disk-fills-fast; GP §3.4; PLAN "Machine".
- At most **two** agents compile for iOS or run simulators at once: slot **A** = "Maze A", slot **B** = "Maze B". A device
  build for the phone (D1) counts as a compiling agent and runs inside slot A's window. No-simulator lanes (`swift test`,
  Python, art) run alongside: at most 3 at once, `swift build -j 2`, and each checks `sysctl vm.swapusage` first.
- One xcodebuild per agent, `-jobs 4 -quiet`; each shell command < ~4 min (longer ones in the background, polled).
- Boot only your slot's simulator; `xcrun simctl shutdown <your udid>` when your WP ends. Never `shutdown all`, never create or
  erase simulators other than ours, never touch another session's simulator (app-factory-0b uses "MF Main"/"MF Spike").
- `df -h /` before a build; `build/dd-*` and `build/iso-*` are always safe to delete. A full disk shows up as a codesign or
  linker error that never mentions space.
- `design/`, `research/` and `art/` are **read-only** for build agents (UI-ART and the art lanes own `art/`).
- Never `git clean -x/-X`, `git stash -u`, `checkout main`; never commit (the orchestrator commits with the GIT_INDEX_FILE recipe).
- Before starting a WP, re-read the research files it names: the phone and video lanes keep appending.

---

## 3 Folder layout and FILE OWNERSHIP

### 3.1 Roles and work packages
| Role | Work packages | Owns (summary) |
|---|---|---|
| **LEAD** | WP0 | project.yml, App/Info.plist, GameApp, Brand, AppModel (until G1), every ◆ contract, Support (frozen parts), tools/*.sh |
| **CORE** | C1 → C2 → C3 → C4 | `Packages/PathCore` except `Social/` |
| **SOCIAL** | SOC1, SOC2 | `PathCore/Social/**`, `App/Shell/Social/**`, `Resources/Social`, `Tuning/social.json` |
| **CONTENT** | L1 → L2 | `Resources/Levels/**`, `Resources/Strings/strings.tsv`, the generated `Localizable.xcstrings`, `tools/strings/**`, `tools/levels/**` |
| **AUDIO** | A1 → A2 → A3 | `App/Audio/**`, `Resources/Sounds|Music`, `Tuning/audio.json`, `tools/audio/**` |
| **UI-ART** | UI-ART (with the art lanes) | `art/**` (incl. `art/ui/code/GlossyChrome.swift`), the AppIcon image |
| **BOARD** | B1 → B2 (+ D1a) | `App/Board/**`, `Tuning/board.json`, board tests and labs |
| **SHELL** | S1 → S2 → S3 | `App/Shell/**` (except `Shell/Social`), `App/FX/**`, fonts, `Tuning/ui.json`, the `.storekit` (from S3) |
| **GAME** | G1 → G2 | `App/Game/**`, `App/AppModel.swift` (from G1), `App/Support/PlayerStore.swift` (from G1), `Tuning/game.json` |
| **VERIFY** | V1, V2, V3 (+ D1b) | `Tests/AppTests/**`, the V suites in `UITests/`, `tools/{capture,compare,bench}/**`, `tools/capture-shot.sh`, `tools/bench.sh` |

A file may be edited only by its owner. The ◆ files are written by the LEAD in WP0 and are **frozen** (§3.5). "→" in the tree
below means the file changes owner at that WP (the earlier owner never touches it again). `design/arch/ownership.tsv` is the
machine-readable twin of this tree (glob → WP → role); if the two disagree, this section wins and the orchestrator fixes the TSV.

### 3.2 The tree
```
apps/mazeout/
├─ project.yml                                                                   WP0 (LEAD; frozen after WP0)
├─ tools/{slot,gen,build,run,test,core,sync_art,iso-build-copy,wait-build,play-watch}.sh   WP0 (LEAD; §2.5 amendments)
├─ tools/{capture-shot.sh,flat_check.py,bench.sh}, tools/{bench,capture,compare}/**        V1 / V2 / V3 (VERIFY; §3.3)
├─ tools/strings/**, tools/levels/** (render.py overlay proof, pathlib_rules.py mirror)    L1 (CONTENT)
├─ tools/audio/**                                                                         A1 (AUDIO)
├─ tools/uiart_gen.py (MANIFEST.json -> App/Shell/Components/UIArt.swift)                 S1 (SHELL)
├─ tools/rng_ref.py, tools/watchdog.sh                                                    read-only / orchestrator
├─ Packages/PathCore/
│  ├─ Package.swift                                                              WP0 → C1
│  ├─ Sources/PathCore/
│  │  ├─ Grid/      Cell.swift ◆, Dir.swift ◆                                     WP0
│  │  │             Grid.swift, Metrics.swift, BoardLayout.swift, ArrowGeometry.swift, ExitPath.swift, HitGeometry.swift   C1
│  │  ├─ Model/     IDs.swift ◆, LevelSpec.swift ◆                               WP0
│  │  │             LevelJSON.swift, LevelLibrary.swift, FeatureUnlock.swift, TutorialScript.swift                       C1
│  │  ├─ Rules/     Plans.swift ◆                                                WP0
│  │  │             BoardState.swift, RayWalk.swift, TapResolver.swift, Obstacles.swift, RulesTuning.swift              C2
│  │  ├─ Session/   SessionEvent.swift ◆, SessionTypes.swift ◆                   WP0
│  │  │             LevelSession.swift, LevelClock.swift, Combo.swift, HeadlessDriver.swift                             C2
│  │  ├─ Solver/    Greedy.swift, Hint.swift                                      C2
│  │  │             Search.swift, Difficulty.swift                                C4
│  │  ├─ Content/   Validator.swift, Generator.swift, Silhouettes.swift, CurveSpec.swift, LevelProvider.swift          C4
│  │  ├─ Economy/   PlayerState.swift ◆                                          WP0
│  │  │             Economy.swift, EconomyRules.swift, Lives.swift, Boosters.swift, Grant.swift, ShopCatalog.swift     C3
│  │  ├─ Events/    EventTypes.swift ◆                                           WP0
│  │  │             EventsState.swift, Streak.swift, ClawChallenge.swift, StreakRace.swift, RocketRace.swift,
│  │  │             SkyJump.swift, WeeklyContest.swift, EventSchedule.swift       C3
│  │  ├─ Social/    SocialAPI.swift ◆                                            WP0
│  │  │             SocialClock.swift, SocialHash.swift, SocialCalendar.swift, Population.swift, Names.swift,
│  │  │             Leaderboards.swift, RaceBots.swift, SocialState.swift          SOC1
│  │  ├─ Persistence/ StateStore.swift, Migrations.swift                          C3
│  │  ├─ Random/    PathRandom.swift                                              WP0 (copied from MF, renamed) → C1
│  │  └─ Motion/    Ease.swift                                                    WP0 (copied from MF) → C1
│  │                ExitKinematics.swift, Timing.swift, Curves.swift              C1
│  ├─ Sources/pclevels/main.swift                                                WP0 (stub) → C4
│  └─ Tests/
│     ├─ PathCoreTests/APISurfaceTests.swift                                     WP0 (skeleton) → C2 (completes; never @testable)
│     ├─ PathCoreTests/{Grid,Geometry,LevelJSON,Kinematics,Curves,Random}Tests.swift                          C1
│     ├─ PathCoreTests/{Rules,Session,Clock,Combo,GoldenRounds,Headless}Tests.swift                           C2
│     ├─ PathCoreTests/{Economy,Lives,Boosters,Events,Persistence}Tests.swift                                 C3
│     ├─ PathCoreTests/{Solver,Validator,Generator,LevelLibrary}Tests.swift                                   C4
│     ├─ PathCoreTests/Social*Tests.swift                                                                     SOC1
│     ├─ tools/golden_rounds.py (research/bot/log.jsonl -> Fixtures/golden_rounds.json)                         C2
│     ├─ tools/lives_ref.py (independent lives-chain reference)                                               C3
│     └─ Fixtures/<prefix>_*.json  (prefix = owner: c1_, c2_, c3_, c4_, soc_)                                 per prefix
├─ App/
│  ├─ GameApp.swift, Brand.swift, Info.plist                                     WP0 (frozen)
│  ├─ AppModel.swift (composition root + BootSequence)                           WP0 → G1
│  ├─ Contracts/ BoardContract.swift ◆, PresentationContract.swift ◆, ShellContract.swift ◆, AudioContract.swift ◆   WP0
│  ├─ Support/  LaunchArgs.swift ◆, Tuning.swift ◆, MotionClock.swift ◆, Log.swift ◆                                 WP0
│  │            PlayerStore.swift                                                WP0 → G1
│  │            PerfMonitor.swift, LatencyProbe.swift                            WP0 → B1
│  ├─ Board/    BoardHost, BoardContainerView, BoardScrollView, BoardEngine (command queue), ReleaseTapRecognizer,
│  │            HitTester, ArrowNode, LocalPath, ExitMover, BumpMover, Painters (solid), DotsPainter, RippleLayer,
│  │            ScreenFX, TapeLayer, IntroBuildIn, SpriteCache, DigitGlyphs, WarmUp, BoardProbe, BoardLab        B1
│  │            Track.swift                                                       WP0 (seeded from the spike) → B1
│  │            PaintersCombo (violet, rainbow gradient runs), StarTrail, DoorLayer, KeyFlight, PipeLayer,
│  │            CounterLayer, ElevatorLayer, CornerLayer, Shards, ClearWave, StageTransition, BoardLab+Obstacles  B2
│  ├─ FX/       FXOverlayView, Sparkles                                           S1
│  │            Confetti, Fireworks, WinLogoSequence                              S2
│  │            CoinFly                                                           S3
│  ├─ Game/     GameController, GameScreen, HUDWriter, LevelFlow, FailFlowDirector, WinDirector, AutoPlayer      G1
│  │            TutorialDirector, FTUEDirector, UnlockDirector, BoosterDirector, EventsDirector, RatingDirector,
│  │            NotificationPrompt                                               G2
│  ├─ Shell/    RootView, Router, Transitions, LoadingScreen, ShellLab (host + registry)                           S1
│  │  ├─ Components/ GameText, GameButton, Toast, UIArt (generated by tools/uiart_gen.py), Tokens, ShellLayout,
│  │  │              DebugPlaceholder (Debug builds only)                         S1
│  │  ├─ Home/  HomeView, HomeTopBar, PlayButton, LevelPlate, NavBar, PuppetStage, PuppetRig                     S1
│  │  │         HomeScene, ClawBar, EventBadges, PayoutSequence, ShellLab+Home                                  S3
│  │  ├─ HUD/   HUDView, CoinPillHUD, TimerPill, HeartsRow, BoosterCorner, HUDIntro, ShellLab+HUD                S2
│  │  ├─ Popups/ PopupHost, PopupChrome, PausePopup, QuitLevelPopup, SettingsPopup                              S1
│  │  │         OutOfTimePopup, ContinuePopup, LevelFailedPopup, WinPanel, StreakBanner, RaceBar,
│  │  │         UnlockOverlay, ClaimRewardPopup, TutorialLayer, ShellLab+Popups                                 S2
│  │  │         UsernamePopup, EditProfilePopup, NoLivesPopup, BoosterBuyPopup, ShellLab+Meta                  S3
│  │  ├─ Shop/  ShopView, StoreService, FakeStore                                 S3
│  │  ├─ Profile/ ProfileView                                                     S3
│  │  └─ Social/ SocialModel, LeaderboardView, LeaderboardRow, WeeklyContestIntro, WeeklyContestTutorial,
│  │             ClawScreen, ClawInfoOverlay, StreakRaceView, RocketRaceView, SkyJumpViews, SocialLab             SOC2
│  ├─ Audio/    AudioEngine, SoundBank, MusicPlayer, AudioCues, Haptics          A2
│  │            SoundBoard                                                        A3
│  └─ Resources/
│     ├─ Assets.xcassets (AppIcon set, LaunchBackground colour)                  WP0; AppIcon.appiconset/icon-1024.png: UI-ART
│     ├─ Fonts/PCDisplay-Black.ttf, PCDisplay-BlackItalic.ttf (copied from design/fonts)   WP0 → S1
│     ├─ Tuning/board.json B1 · game.json G1 · ui.json S1 · audio.json A2 · rules.json C2 · social.json SOC1
│     │         (WP0 writes each with {} or its defaults, then the listed owner takes it)
│     ├─ Levels/level_NNNN.json, sessions.json, tutorials.json, unlocks.json, curve.json          L1 / L2 (CONTENT)
│     ├─ Social/*.txt (copied from design/social/data; checksum-tested)          SOC1
│     ├─ Strings/strings.tsv                                                      L1 (CONTENT)
│     ├─ Strings/requests/<role>.tsv (board, shell, game, social, audio)          that role (append-only)
│     ├─ Localizable.xcstrings  (GENERATED by tools/strings/build.py; never edited by hand)   L1/L2 (CONTENT)
│     ├─ Sounds/*.wav, Music/*.wav                                                A1 (AUDIO)
│     └─ StoreKit/ArrowOut.storekit                                               WP0 → S3
├─ art/ui/code/GlossyChrome.swift (compiled into the app, §2.2)                  UI-ART
├─ art/** (everything else: pipeline, out/, ui/out/, MANIFEST.json, …)           UI-ART and the art lanes (never build agents)
├─ Tests/  AppTests/{StringsCoverage,FontCoverage,UIArtBundle,LevelsBundle,Tuning,Brand}Tests.swift    V1
│          Board*Tests.swift B1/B2 · Shell*Tests.swift S1–S3 · Game*Tests.swift G1/G2 · Audio*Tests.swift A3 · Social*Tests.swift SOC2
├─ UITests/ UITestSupport.swift                                                  WP0 → V1
│           {Flow,FailFlow,Booster,Meta,Capture}Tests.swift                        V1 / V2
│           BoardInputTests.swift, BoardLabTests.swift B1/B2 · Shell*UITests.swift S1–S3 · GameFlowTests.swift G1/G2 ·
│           SocialUITests.swift SOC2
├─ design/**, research/**                                                        read-only for build agents
└─ build/  (gitignored) dd-A, dd-B, iso-<role>/, <wp>/ evidence, bench/, compare/, shots/, blocked.md (append-only, anyone),
           wp0/frozen-contracts.sha256 (WP0)
```

### 3.3 Shared files and their single owner
| File | Single owner | How the others contribute |
|---|---|---|
| `project.yml` | LEAD (WP0); frozen afterwards | Agents only add files under their folders and run `tools/gen.sh`. A needed project change (new resource folder, build setting) goes to the orchestrator as a request, who applies it and re-hashes nothing (project.yml is not ◆ but is LEAD-only). |
| `Localizable.xcstrings` | CONTENT (generated) | Every role writes English literals in code and appends `en<TAB>tr<TAB>context` rows to **its own** `Resources/Strings/requests/<role>.tsv`; `tools/strings/build.py` (CONTENT adapts it in L1 to merge `strings.tsv` + `requests/*.tsv`, duplicates must agree) regenerates the catalogue. `StringsCoverageTests` fails on any literal without a TR row. |
| `strings.tsv` | CONTENT | as above. A request row carries the requester's TR draft; CONTENT reviews it and, to change it, adds the same key to `strings.tsv` (a `strings.tsv` row wins over a request row; two request rows with the same key must agree). CONTENT never edits a requester's file. |
| `tools/bench/bench.py` `MARKS` table | VERIFY | BOARD, SHELL and GAME print the log lines of §9.3 exactly; a change to a mark's text changes bench.py in the same WP (the producer requests it). |
| `Tuning/*.json` | one file per owner (tree above) | defaults compiled into `Tuning.swift` ◆; owners add keys to their own JSON and read them through extensions in their own files (MF pattern). |
| `art/ui/code/GlossyChrome.swift` | UI-ART | SHELL uses its components and never redefines its top-level names (§6.11); a missing component is a request to UI-ART. |
| `App/Resources/Assets.xcassets` | LEAD (WP0) | the single image file `AppIcon.appiconset/icon-1024.png` is written by UI-ART (from `art/out/appIcon1024.png`). |
| `App/AppModel.swift` | LEAD → GAME at G1 | before G1 nobody edits it; boot tasks are reached through the contracts' `warmUp()`/`prepare()` that WP0 already calls. |
| `UITests/UITestSupport.swift` | LEAD → VERIFY at V1 | owners add helpers in their own test files (extensions). |
| `build/blocked.md` | append-only, anyone | one line per block: `file:line error — owner` (GP §8.2 rule 4). |
| `design/levels.json` | the gameplay spec writer (not a build agent) | CONTENT generates `Resources/Levels/*` from it; a content bug found in the build is a request to the orchestrator. |

### 3.4 Rules that keep parallel work mergeable (GP §8.2)
1. Add files only under your own folders; run `tools/gen.sh` after adding, removing or renaming any file.
2. Never leave your files non-compiling past one edit-build cycle. Develop big rewrites in a new file and wire it in when it
   compiles. To build while others edit, use `tools/wait-build.sh <role> <slot>` (the iso copy).
3. Blocked by someone else's file: append `file:line error — owner` to `build/blocked.md`, work around it (the iso copy's
   `patch.py`), report it. Never patch another owner's file in the real tree.
4. Tuning is one JSON per owner; a missing key never crashes (compiled defaults).
5. Nobody edits `Localizable.xcstrings` by hand. Custom text components take `LocalizedStringKey` or
   `LocalizedStringResource`, **never `String`** for user-visible copy (memory localizedstringkey-not-string); their names are
   listed in `tools/strings/sources.json` `callees`.
6. Every WP ends with `shasum -a 256 -c build/wp0/frozen-contracts.sha256` green and its slot's build green.

### 3.5 Frozen contracts (◆): what each holds
The LEAD writes every ◆ file in WP0 with its full public surface: types and protocols complete, function bodies stubbed
(`fatalError("C2")`, no-ops or trivial defaults), so every agent compiles from day one. After WP0 the owner implements the
bodies but may not change a public signature without the orchestrator; a changed signature fails `APISurfaceTests` (compiled
WITHOUT `@testable`, it calls every public member of every ◆ PathCore type) and the sha256 list.

| ◆ file | Holds (sections) | Written by → implemented by → read by |
|---|---|---|
| `PathCore/Grid/{Cell,Dir}.swift` | `Cell`, `Dir` (real code in WP0: tiny) | WP0 → everyone |
| `PathCore/Model/IDs.swift` | `ArrowID`, `ObstacleID`, `BoosterID`, `FeatureID`, `TutorialID`, `EventID`, `LevelTag`, `LevelSource` (§4.3) | WP0 → everyone |
| `PathCore/Model/LevelSpec.swift` | `ArrowSpec`, `ObstacleSpec`, `ObstacleKind`, `PipeEnd`, `CornerTurn`, `LevelSpec`, `SessionPlan`, `LevelMetrics` (§4.3) | WP0 → C1 (decoding) → BOARD, GAME, CONTENT |
| `PathCore/Rules/Plans.swift` | `TapResolution`, `ExitPlan`, `ExitPath`, `PathSegment`, `PlanBeat`, `BumpPlan`, `Blocker`, `IgnoreReason` (§4.4) | WP0 → C2 → BOARD |
| `PathCore/Session/SessionEvent.swift`, `SessionTypes.swift` | `SessionEvent`, `SessionAck`, `Phase`, `HoldReason`, `AttemptSetup`, `ContinueOffer`, `WinResult`, `LossReason`, `TimerAlert`, `TimeCause`, `SessionSnapshot` (§4.5) | WP0 → C2 → everyone |
| `PathCore/Economy/PlayerState.swift` | `PlayerState` v1 aggregate + `LivesState`, `ActiveAttempt`, `Stats`, `Settings`, `Flags` (§4.8). Sub-states `EventsState`, `SocialState` are declared in their modules (not frozen; additive-only, §4.12). | WP0 → C3 → LEAD store, SHELL, GAME |
| `PathCore/Events/EventTypes.swift` | `EventOutcome`, `WinContext`, `LossContext`, `RivalProvider` protocol, `RaceStanding`, `SkyJumpField` (§4.10) | WP0 → C3 / SOC1 → GAME, SOC2 |
| `PathCore/Social/SocialAPI.swift` | `SocialWorld` public API, `SocialTime`, `LeaderboardKind`, `LeaderboardPage`, `LeaderboardRow`, `SimPlayer` (§4.11) | WP0 → SOC1 → SOC2, GAME |
| `App/Contracts/BoardContract.swift` | `BoardControlling`, `BoardDelegate`, `BoardBeat`, `StageSetup`, `IntroStyle`, `BoardProbeData` (§5.10) | WP0 → BOARD → GAME |
| `App/Contracts/PresentationContract.swift` | `HUDModel`, `HeartSlotVM`, `BoosterSlotVM`, `AnchorID`, `AnchorRegistry` + `.anchor(_:)`, `FXPlaying` + `FXEffect` (§6.5, §6.7) | WP0 → GAME writes the models, SHELL renders them |
| `App/Contracts/ShellContract.swift` | `Screen`, `HomeTab`, `HomeEntry`, `LevelLaunch`, `WinSummary`, `PopupHost` API, `Popup<R>`, `PopupStyle`, `PopupID` + each popup's result enum, `ToastCenter` (§6.1, §6.6) | WP0 → SHELL → GAME, SOC2 |
| `App/Contracts/AudioContract.swift` | `AudioPlaying`, `HapticPlaying`, `enum SoundID`, `enum MusicID`, `var bus: AudioBus`, `enum Haptic` (§7.4) — the shape `tools/audio/specs.py` parses | WP0 → AUDIO → GAME, SHELL |
| `App/Support/LaunchArgs.swift` | every `-pc.*` argument of §9.1, parsed once; `raw` for private flags | WP0 → everyone |
| `App/Support/Tuning.swift` | `TuningFile` loader (MF copy) + typed `BoardTuning`, `GameTuning`, `UITuning`, `AudioTuning`, `SocialTuning` shells with compiled defaults; `-pc.tune file.key=v` | WP0 → owners add extensions |
| `App/Support/MotionClock.swift` | the one game clock for SwiftUI sequences: `timeScale`, `freezeAt`, `gameTime(date)`; mirrors onto the board's stage layer speed (§5.12) | WP0 → everyone |
| `App/Support/Log.swift` | `Log.mark(_ cat:, _ msg:)` printing `"<uptime> [PC][<cat>] <msg>"`, errors `[PC][<cat>][ERROR]`, plus os.Logger subsystem `com.manycode.arrowout` (the bench/capture grammar, §9.3) | WP0 → everyone |

`build/wp0/frozen-contracts.sha256` lists exactly these files. Every WP ends with `shasum -a 256 -c` on it; a mismatch is a
P0 for the orchestrator (who alone may approve a contract change and re-hash).

---

## 4 Core package PathCore

### 4.1 Package rules
- Pure Swift, `Foundation` + `CoreGraphics` (§2.4). Value types by default; `BoardState` and `LevelSession` are `final class`es
  with no actor isolation, used on the main actor by the app and freely by tests, the solver and the generator (on copies).
- **Deterministic:** no `Date()`, no `Double.random`, no `SystemRandomNumberGenerator`. Wall time enters only as arguments
  (`tick(dt)`, `tap(at:)`, `now:`), randomness only through `PathRandom` / the social hash.
- Every public API in this section is **exact** (the ◆ parts are frozen at WP0). CORE may add internals and new public
  helpers; changing a public signature of a ◆ type needs the orchestrator.
- Cost targets (macOS `-O`, checked by tests with generous margins): tap resolve + commit ≤ 50 µs on a 304-arrow board; a
  greedy solve of that board ≤ 20 ms; generation of a 40 × 40 board ≤ 30 ms p95.

### 4.2 Grid and geometry (C1)
```swift
public struct Cell: Hashable, Codable, Sendable { public var c: Int; public var r: Int }   // JSON [c, r]; row 0 = top (◆)
public enum Dir: String, Codable, Sendable, CaseIterable {                                  // (◆)
    case up, down, left, right
    public var dc: Int { get }; public var dr: Int { get }; public var opposite: Dir { get }
    public var angle: Double { get }                 // screen space, y down: right 0, down π/2, left π, up −π/2
}
public struct Grid: Sendable, Equatable {
    public let cols: Int, rows: Int
    public let mask: [Bool]?                         // nil = all playable; from the JSON "mask" rows ('#' = playable)
    public func contains(_ c: Cell) -> Bool; public func index(_ c: Cell) -> Int
}
public enum Metrics {                                 // ratios of the pitch
    public static let stroke = 0.22                  // VERIFIED STYLE §A (0.215 at fit, 0.226 at 1.57×, 0.233 at 0.79×)
    public static let headBase = 0.616, headLength = 0.61, headCornerRadius = 0.047        // VERIFIED STYLE §A (37 heads)
    public static func headApexPast(_ d: Dir) -> Double  // ← → 0.36, ↑ 0.30, ↓ 0.435 (VERIFIED STYLE §A; copy per direction)
    public static let dotDiameter = 0.192            // VERIFIED spike + STYLE (#C5E1FF discs)
    public static let maxPitch = 28.07               // pt: zoom cap = fit cap (VERIFIED levels L47 probe, L50 opens at the cap)
    public static let minZoomOfFit = 0.786           // VERIFIED levels L47 (0.783–0.786)
    public static let playRect = CGRect(x: 0, y: 122, width: 393, height: 633)   // HUD bottom … booster top (VERIFIED spike)
}
public struct BoardLayout: Sendable, Equatable {
    public static func fit(grid: Grid, play: CGRect, maxPitch: Double = Metrics.maxPitch) -> BoardLayout
    public let pitch: Double                          // = min(play.w/(cols+2), play.h/(rows+2), maxPitch)
    public let contentSize: CGSize                    // (cols+2, rows+2) × pitch: one empty margin cell all round
    public let origin: CGPoint                        // centre of cell (0,0) in content space = (1.5 p, 1.5 p)
    public func centre(_ c: Cell) -> CGPoint; public func cell(at p: CGPoint) -> Cell
    public var minZoom: Double { get }                // Metrics.minZoomOfFit
    public var maxZoom: Double { get }                // max(1, maxPitch / pitch)
}
public struct ArrowGeometry: Sendable {               // the spike's Geometry.swift, generalised to ExitPath
    public init(cells: [Cell], dir: Dir, layout: BoardLayout)
    public let polyline: [CGPoint]                    // cell centres tail → head, collapsed to corners (sharp polyline)
    public let bodyLength: Double                     // (cells − 1) × pitch: arc length is exact (tail passes cell i at travel i·p)
    public let headCentre: CGPoint
    public func headPath() -> CGPath                   // rounded triangle, head-local, apex at +headApexPast(dir)
    public func point(along u: Double, on path: ExitPath) -> CGPoint
    public func tangent(along u: Double, on path: ExitPath) -> Dir
}
public struct HitGeometry: Sendable {                 // centrelines incl. the head apex; the spike's 5 × 5-cell neighbour search
    public init(arrows: [ArrowSpec], layout: BoardLayout)
    public func nearest(to p: CGPoint, within r: Double, among live: (ArrowID) -> Bool, tieBreak: TieBreak) -> ArrowID?
}
public enum TieBreak: String, Codable, Sendable { case rightThenDown, leftThenUp }  // VERIFIED once: midpoint → right (levels L52)
```
**The fit rule reproduces every recorded pitch** (VERIFIED levels, pitch at fit): L32 20×20 → 17.864 (17.865); L34 25×35 →
14.556 (14.562); L35 12×18 → 28.07 cap (28.092); L36 16×23 → 21.83 (21.836); L37 22×30 → 16.375 (16.381); L39 24×34 → 15.115
(15.126); L45 15×19 → 23.118 (23.115); L50 10×18 → 28.07 cap (28.07); L52 13×16 → 26.2 (26.199); L54 26×34 → 14.036 (14.044).
`GeometryTests` pins all 30 recorded levels within ±0.03 pt. The board is centred in the play rect (L32 centre y 439.1 pt vs
(122 + 755)/2 = 438.5, VERIFIED spike).

The **vertical head nudge** (↑ and ↓ heads sit ≈1.2 pt lower than the horizontal rule predicts, STYLE §A: "copy the
per-direction values") is carried by `headApexPast(_:)` per direction (INFERRED sprite pivot in the original).

### 4.3 Level model and JSON (C1)
```swift
// IDs.swift (◆)
public struct ArrowID: Hashable, Comparable, Codable, Sendable { public let raw: Int }          // JSON "id"
public struct ObstacleID: Hashable, Comparable, Codable, Sendable { public let raw: String }     // "t0" "d0" "k0" "p0" "b0" "c0" "e0" "x0"
public struct BoosterID: RawRepresentable, Hashable, Codable, Sendable { public let rawValue: String }   // "freeze", "hint"
public struct FeatureID: RawRepresentable, Hashable, Codable, Sendable { public let rawValue: String }   // "linked", "door", "pipe", "box", …
public struct TutorialID: RawRepresentable, Hashable, Codable, Sendable { public let rawValue: String }
public struct EventID: RawRepresentable, Hashable, Codable, Sendable { public let rawValue: String }     // "streakRace", "clawChallenge", …
public enum LevelTag: String, Codable, Sendable { case normal, hard, superHard }   // JSON null | "Hard Level" | "Super Hard"
public enum LevelSource: String, Codable, Sendable { case recorded, video, designed, generated }

// LevelSpec.swift (◆)
public struct ArrowSpec: Codable, Sendable, Equatable {
    public var id: ArrowID
    public var cells: [Cell]                      // tail → head, orthogonally adjacent, ≥ 2 cells (VERIFIED min 2)
    public var dir: Dir                           // head direction = the last segment's direction (validator)
    public var layer: Int                         // 1; 2 = under an elevator platform (video V2 L31+)
    public var hiddenBy: ObstacleID?              // door / box / curtain / elevator that hides it until it opens
}
public enum ObstacleKind: String, Codable, Sendable { case tape, door, key, pipe, box, curtain, elevator, corner }
public struct PipeEnd: Codable, Sendable, Equatable { public var cell: Cell; public var out: Dir }
public enum CornerTurn: String, Codable, Sendable { case upRight, upLeft, downRight, downLeft }  // incoming → outgoing pairs (§4.4)
public struct ObstacleSpec: Codable, Sendable, Equatable {
    public var id: ObstacleID
    public var kind: ObstacleKind
    public var cells: [Cell]                      // covered cells; pipe: ordered mouth → mouth; key: the 2 cells it hangs on
    public var arrows: [ArrowID]                  // tape members · the key's arrow · the elevator's platform arrows
    public var ends: [PipeEnd]                    // pipe only: 2 mouths
    public var counter: Int?                      // pipe passes left · box/curtain clears left
    public var counterAt: [Double]?               // pipe counter box centre in cells (e.g. [7.5, 0], STYLE §A.2)
    public var order: Int?                        // door opening order (keys go to the lowest-order locked door)
    public var opens: ObstacleID?                 // key → explicit door (nil = next by order)
    public var turn: CornerTurn?
    public var reveals: [ArrowID]                 // arrows hidden under it (door / box / curtain / elevator layer 2)
    public var sprite: String?                    // art id override; nil = derived (tapeV4, doorW4H8, …)
}
public struct LevelMetrics: Codable, Sendable, Equatable {
    public var rounds: Int; public var freeAtStart: Int; public var arrows: Int; public var cells: Int
    public var meanLength: Double; public var botTimeLeft: Double?        // validator/generator output (§4.14)
}
public struct LevelSpec: Codable, Sendable, Equatable {
    public var level: Int
    public var source: LevelSource
    public var capture: String?                   // research shot / video frame the level was read from
    public var cols: Int, rows: Int
    public var mask: [String]?
    public var timerSeconds: Int                  // JSON "timer_s" (3:00, 2:30, 2:00, 3:30 seen; VERIFIED levels)
    public var hearts: Int                        // 3 everywhere (VERIFIED)
    public var tag: LevelTag
    public var arrows: [ArrowSpec]
    public var obstacles: [ObstacleSpec]
    public var unlock: FeatureID?                 // the first Play of this level shows this feature's unlock overlay
    public var seed: UInt64?                      // generated levels
    public var metrics: LevelMetrics?
    public var grid: Grid { get }
}
public enum HeartsCarry: String, Codable, Sendable { case reset, carry }
public struct SessionPlan: Codable, Sendable, Equatable {   // one Play = one session = 1…n stages
    public var id: String
    public var levels: [Int]                      // [1, 2, 3, 4] (VERIFIED tutorials §2) or [n]
    public var hudLabel: String?                  // "Levels 1-4" (else "Level %lld")
    public var panelLabel: String?                // "Level 1-4" (singular on the win panel, VERIFIED)
    public var reward: Int?                       // 80 (VERIFIED); nil = by tag
    public var stageGap: Double?                  // last exit → next board built: 0.7 s (VERIFIED tutorials §2)
    public var hearts: HeartsCarry                // PENDING-gameplay (unknown: no heart was lost in V1); default .carry
}
```

**Level JSON.** Three readers, one model (C1, `LevelJSON.swift`):
| schema | used by | keys (snake_case; `Cell` = `[c, r]`) |
|---|---|---|
| **phone** (research/levels/Lnnn.json, `research/bot/bot.py`) | `pclevels import` | `level, source:"recorded", shot, zoom, pitch_pt, stroke_pt, origin_pt, cols, rows, mask, arrows[{id,cells,dir}], obstacles[{kind: tape_pink\|door\|key\|pipe\|box\|box_part, cells, bbox_px, mean_rgb}], taped_arrow_ids, timer_s, hearts, tag, pipes[{cells, ends[{cell,out}]}], door_cells, reveals ["Lnnn-open1.json"], anomalies, occlusion_inferred, reader` (VERIFIED L032/L033/L035/L049/L050) |
| **video** (`research/video-frames/work/extract/V?-Lnnn.json`, `research/video-tools/vextract.py`) | `pclevels import` | the phone schema + `source:"video", video, t, frame, obstacles[].counter, obstacles[kind: curtain\|box\|pipe\|elevator\|tape_pink], elevators[{cells, arrow_ids, t_active, hidden_arrow_ids}], arrows[].layer, arrows[].under_elevator, blocker_cells, fit_px, verify` (VERIFIED V1-L011, V2-L021, V2-L031) |
| **bundle v1** (`App/Resources/Levels/level_NNNN.json`, written by `pclevels bundle` from `design/levels.json`) | the app, tests | `schema:1, level, source, capture, cols, rows, mask, timer_s, hearts, tag, arrows[{id,cells,dir,layer?,hidden_by?}], obstacles[{id,kind,cells,arrows?,ends?,counter?,counter_at?,order?,opens?,turn?,reveals?,sprite?}], unlock?, seed?, metrics?` |

- `tag` accepts `null`/`"Hard Level"`/`"Super Hard"`/`"hard"`/`"superHard"`. `box_part` blobs (the counter ring/bolts) and every
  research-only key (`bbox_px`, `mean_rgb`, `anomalies`, `reader`, `fit_px`, `verify`, …) are dropped; the import report lists
  every unknown key so nothing is lost silently.
- The phone schema carries **no counters** for pipes/boxes (L035: counter 2 is in levels.md, not the JSON) and **no arrows under
  doors** (the `Lnnn-openK.json` reveal files hold them; PLAN TODO ledger). `design/levels.json` (SPEC-gameplay) is where the
  counters and the merged reveals live; the exact obstacle field names are **PENDING-gameplay** (the bundle keys above are the
  default the decoder implements; C1 follows whatever SPEC-gameplay freezes).
- `sessions.json`: `{"schema":1,"sessions":[{"id":"L1-4","levels":[1,2,3,4],"hud_label":"Levels 1-4","panel_label":"Level 1-4",
  "reward":80,"stage_gap_s":0.7,"hearts":"carry"}]}` (VERIFIED tutorials §2). A level in no session is a one-stage session.
- `unlocks.json`: `[{"feature":"linked","level":7,"title":"Linked Arrows!","card":"LINKED ARROWS move together!",
  "caps":"LINKED ARROWS","icon":"unlockIconLinked"}, …]` — VERIFIED texts tutorials §6 (Linked Arrows L7, Curtain/Box L11,
  Pipe L21, Elevator L31 from the videos; Pipe L35, Box L50 on the phone). Which levels ship: **PENDING-gameplay**.
- `tutorials.json`: MF-style steps (`id, level, stage, trigger, caption, hand {arrow, at}, dismiss, holdTimer`), e.g. the
  VERIFIED "Tap to move!" hand on the middle arrow of stage 1 (tutorials §3). Timings come from SPEC-motion-audio.

```swift
public struct LevelLibrary: Sendable {
    public static func load(folder: URL) throws -> LevelLibrary      // level_*.json + sessions/unlocks/tutorials/curve
    public let authoredCount: Int
    public func session(containing level: Int) -> SessionPlan        // next level after a session = its last + 1
    public func authored(_ level: Int) -> LevelSpec?
    public let unlocks: [FeatureUnlock]; public let tutorials: [TutorialScript]; public let curve: CurveSpec
}
```

### 4.4 Rules (C2): occupancy, the ray walk, obstacles, tap resolution
`BoardState` keeps one flat occupancy array per layer (`[Int32]`, −1 empty; the spike's layout), an alive/visible/moving bit
per arrow, tape units, and obstacle state (door locked/opening/open, pipe counter, box counter, elevator active).

**The blocking rule** (VERIFIED spike + levels): walk from the head's next cell in `dir` to the grid edge; the first live
occupant blocks. Vacated cells (dots) never block. The walk also reads obstacles:

| obstacle | ray behaviour | tap/lifecycle rule | tag |
|---|---|---|---|
| **tape** (Linked Arrows) | members are ordinary arrows | one tap on ANY member sends the whole bundle, each along its own path, iff every member's ray is clear; the tape leaves with them | VERIFIED levels L32 (4/4), motion §4.1; some-clear case **PENDING-gameplay** (default: the tapped member bumps alone) |
| **door** | door cells block while locked or opening | a key arrow's exit sends its key to its `opens` door, else the lowest-`order` locked door not yet targeted; the door stays blocking until the board acks `doorBurst` (≈1.14 s after the tap); then its cells empty and `reveals` arrows become live and visible | VERIFIED levels L33 (order left → right, blocked until the break), motion §4.2 |
| **key** | none (it hangs on its arrow) | leaves with its arrow's exit; the plan carries `keyReleased(key, door, s)` | VERIFIED |
| **pipe** | a ray entering a **mouth** against that mouth's `out` direction travels the tube and continues from the other mouth in its `out` direction; a ray meeting a tube cell or a mouth from another side is blocked | each passage −1 at the tap (logical); at 0 the pipe breaks and its cells empty. A ray blocked after leaving the far mouth is a bump and consumes nothing (DECISION, PENDING-gameplay). Chained pipes allowed (loop guard) | VERIFIED levels L35/L36/L42 (U-turns), motion §4.3 |
| **box** (phone) / **curtain** (video V1) | covered cells block while `counter > 0` | every arrow cleared ANYWHERE (tape members count one each) lowers every box/curtain counter by 1; at 0 it breaks, its cells empty, `reveals` become live | VERIFIED levels L50/L51 (all boxes together), tutorials §6 (V1 curtain); blocking INFERRED (bot assumption) |
| **elevator** (video V2) | platform arrows are layer 1 on the platform cells; layer-2 arrows are inert until activation; empty platform cells do not block (INFERRED) | when the last platform arrow is tapped the elevator activates at once: layer-2 arrows become live | VERIFIED vflows/vextract (V2 L32: layer 2 live 0.3 s before the platform visibly drops); empty-cell rule PENDING-gameplay |
| **corner** (May/Jul builds) | a wedge turns the ray 90° per `turn`; a ray arriving from a non-accepting side is blocked | exit paths bend at the corner | INFERRED web §3 (not in v552 L32–L61 nor the videos' L1–38); supported so content can use it |

- **Queued taps:** an arrow leaves the blocking grid **at its tap**, not when it leaves the screen (VERIFIED motion §2.1, P02).
- A tapped arrow that is moving, bumping, hidden, or on an inactive layer is ignored (DECISION for "bumping": the ≤ 0.35 s
  bump cannot be re-tapped; PENDING-gameplay).
- A bumped arrow is **marked** (red for the rest of the level) but stays an ordinary arrow (VERIFIED levels L47/L48).
- The ray of an arrow never meets its own body (validator rule).

```swift
// Plans.swift (◆): what the core hands the board
public enum TapResolution: Equatable, Sendable { case exit(ExitPlan), bump(BumpPlan), ignored(IgnoreReason) }
public enum IgnoreReason: String, Codable, Sendable { case noArrow, hidden, moving, bumping, inputLocked, notPlaying }
public enum PathSegment: Equatable, Sendable {
    case body(Range<Double>)                              // arc range in cells of the HEAD's travel
    case ray(Range<Double>)
    case tube(ObstacleID, Range<Double>)
    case corner(ObstacleID, at: Double)
}
public struct ExitPath: Equatable, Sendable {
    public var cells: [Cell]                              // body tail → head, then every cell the head passes to the grid edge
    public var segments: [PathSegment]
    public var toGridEdge: Double                         // head travel (cells) until the head leaves the grid;
                                                          // the board extends the last direction to the SCREEN edge (D5)
}
public enum PlanBeat: Equatable, Sendable {               // s = the leading head's travel in cells when it happens
    case keyReleased(key: ObstacleID, door: ObstacleID, s: Double)
    case enterTube(ObstacleID, ArrowID, s: Double), leaveTube(ObstacleID, ArrowID, s: Double)
    case pipeCount(ObstacleID, remaining: Int, s: Double) // visible counter change (PENDING-motion-audio: at enter or leave)
    case pipeBreak(ObstacleID, s: Double)                 // the board adds the measured +0.05 s (motion §4.3)
    case corner(ObstacleID, ArrowID, s: Double)
    case counterTick(ObstacleID, remaining: Int, s: Double)   // box/curtain (PENDING-motion-audio: at the tap or at the leave)
    case counterBreak(ObstacleID, s: Double)
    case elevatorEmptied(ObstacleID, s: Double)
}
public struct ExitPlan: Equatable, Sendable {
    public var tapped: ArrowID
    public var unit: [ArrowID]                            // [tapped] or the whole tape bundle
    public var tape: ObstacleID?
    public var paths: [ArrowID: ExitPath]
    public var beats: [PlanBeat]                          // sorted by s
    public var combo: Int                                 // 1-based combo index (§4.7)
}
public enum Blocker: Equatable, Sendable { case arrow(ArrowID), obstacle(ObstacleID) }
public struct BumpPlan: Equatable, Sendable {
    public var arrow: ArrowID
    public var blocker: Blocker
    public var gapCells: Int                              // empty cells between head and blocker (0 is common: spike P9)
    public var path: ExitPath                             // the travelled part (may pass through a tube)
    public var contactCells: Double                       // head travel to contact: apex touches the blocker's stroke edge
    public var contactPoint: Cell                         // where the ✖ badge sits (VERIFIED obstacles "BUMP")
}

public final class BoardState {
    public init(level: LevelSpec, rules: RulesTuning)
    public var live: [ArrowID] { get }                    // tappable now
    public var hidden: [ArrowID] { get }
    public var isCleared: Bool { get }                    // no live and no hidden arrows left
    public func owner(of cell: Cell) -> ArrowID?
    public func resolve(tap arrow: ArrowID) -> TapResolution           // pure
    public func commit(_ r: TapResolution) -> [RuleEvent]              // the logical change, at tap time
    public func ack(_ a: RuleAck) -> [RuleEvent]                        // .doorBurst(ObstacleID), .bumpFinished(ArrowID)
    public func freeUnits() -> [[ArrowID]]
    public func copy() -> BoardState
}
```
`RuleEvent`/`RuleAck` are internal to PathCore; the session maps them onto `SessionEvent`/`SessionAck` (§4.5).
`RulesTuning` (C2, Codable, compiled defaults, overridable by `Tuning/rules.json`) holds every rule knob of this section and
§4.5–§4.9 (tape some-clear policy, bump-on-bump policy, hit radius, tie break, fail chain, combo window, clock display).

### 4.5 Session state machine and the event stream (C2)
```
            start()                introFinished()         first tap                 last arrow of the stage tapped
 (none) ───────────▶ .intro(k) ───────────────────▶ .ready(k) ─────────▶ .playing(k) ───────────────────────────────┐
                        ▲  timer frozen at limit      (tutorial caption,   │  taps / bumps / obstacles / boosters      │
                        │  (unlock overlay before     unlock overlay)      │                                           ▼
                        │   this, §8.5)                                    ├─ time 0 ──▶ .offer(outOfTime, step 0)    .stageClear(k)
                        │                                                  ├─ hearts 0 (at the contact ack) ──▶        │ more stages:
                        │                                                  │      .offer(outOfHearts, step 0)          │ ack(.stageTransitionDone)
                        └──────────────── stage k+1 ◀──────────────────────┼──────────────────────────────────────────┘
                                                                           │                       last stage: .won(result)
   .offer(kind, i) ── acceptContinue ──▶ .playing(k) (+time or hearts)     └─ quit() ──▶ .lost(.quit)
                   ── declineContinue ─▶ .offer(kind, i+1) … last step ─▶ .lost(.timeUp | .hearts)
```
- `.ready`: the board is built and the timer shows its limit, frozen until the **first tap** (VERIFIED levels L33/L35, tutorials
  §8). A pinch/zoom/pan never starts it (VERIFIED levels L47).
- **Win at the tap:** when the last arrow (live + hidden = 0) is tapped, the timer stops, input locks and `.won` is emitted at
  once (the win is banked, §8.4). The presentation waits for the board's `lastExitLeftBoard` beat before the celebration
  (VERIFIED tutorials §8: "the timer stops on the last arrow"; motion §5.6 beat table).
- **Hearts at contact:** a bump is decided at the tap (`.bumped(plan)`), but the heart is taken, the arrow marked and a
  possible `.offer(outOfHearts)` emitted when the board acks `.bumpContact` (the HUD heart dims on that frame, VERIFIED motion §3).
  The timer keeps running through a bump (no time penalty, VERIFIED vflows §7).
- A **win beats a fail**: time running out between the last tap and `lastExitLeftBoard` cannot fail a won level (DECISION).
- The fail chain is data: `RulesTuning.failChain[kind] = [ContinueStep]` with price, grant and warning per step. VERIFIED
  phone (flows "Fail by time", L47): Out of Time! (+30 sec, 900) → Continue? "You will lose your streak!" / "You will lose 100
  token and your streak!" (Play On 900) → Continue? "You will lose a life!" (Play On 900) → Level Failed / Try Again.
  Out of hearts: "Continue? Get 3 lives to keep playing! Play On 900" (VERIFIED web §2, Jul build); its later steps and what
  "Play On" grants on the later time-out steps are **PENDING-gameplay**.

```swift
// SessionTypes.swift (◆)
public enum Phase: Equatable, Sendable {
    case intro(stage: Int), ready(stage: Int), playing(stage: Int), stageClear(stage: Int)
    case offer(ContinueOffer), won(WinResult), lost(LossReason)
}
public enum HoldReason: String, Hashable, Codable, Sendable {
    case intro, stageTransition, tutorial, unlockOverlay, popup, pause, offer, background, winSequence
}
public struct AttemptSetup: Codable, Sendable, Equatable {
    public var levels: [Int]                     // the session's levels
    public var attemptIndex: Int                 // 1-based count of starts of this session (first try = 1 with no loss)
    public var seed: UInt64                      // combo/hint tie-breaks only (the boards are fixed data)
    public var boosters: [BoosterID: Int]        // stock snapshot (the caller owns stock)
    public var firstStage: Int                   // 0, or -pc.stage
}
public struct ContinueOffer: Codable, Sendable, Equatable {
    public enum Kind: String, Codable, Sendable { case outOfTime, outOfHearts }
    public enum Grant: Codable, Sendable, Equatable { case addTime(Int), refillHearts(Int), none }
    public enum Warning: String, Codable, Sendable { case none, streak, token, life }
    public var kind: Kind; public var step: Int; public var price: Int; public var grant: Grant; public var warning: Warning
    public var isLast: Bool
}
public struct WinResult: Codable, Sendable, Equatable {
    public var levels: [Int]; public var tag: LevelTag; public var timeLeft: Int; public var heartsLeft: Int
    public var firstTry: Bool; public var reward: Int; public var bumps: Int
}
public enum LossReason: String, Codable, Sendable { case timeUp, hearts, quit, killed }
public enum TimerAlert: Codable, Sendable, Equatable { case threshold(Int) }   // thresholds PENDING-gameplay (clips-needed #3)
public enum TimeCause: String, Codable, Sendable { case continueOffer, booster }
public enum SessionAck: Equatable, Sendable {
    case introFinished, bumpContact(ArrowID), bumpFinished(ArrowID), doorBurst(ObstacleID),
         lastExitLeftBoard, stageTransitionDone
}
public struct SessionSnapshot: Codable, Sendable, Equatable {   // the probe's source (§9.4)
    public var levels: [Int]; public var stage: Int; public var phase: String; public var remaining: Double
    public var timerStarted: Bool; public var hearts: Int; public var live: [ArrowID]; public var free: [[ArrowID]]
    public var counters: [ObstacleID: Int]; public var combo: Int
}

// SessionEvent.swift (◆): the one stream
public enum SessionEvent: Equatable, Sendable {
    case stageLoaded(stage: Int, of: Int, level: Int)
    case timerArmed(stage: Int, seconds: Int)                  // .ready: HUD shows the limit, frozen
    case timerStarted(stage: Int)                              // the first tap of the stage
    case exited(ExitPlan)
    case bumped(BumpPlan)
    case tapIgnored(ArrowID?, IgnoreReason)
    case heartLost(remaining: Int)                             // at .bumpContact
    case arrowMarked(ArrowID)                                  // at .bumpContact (turns red on the return, §5.5)
    case keyDispatched(key: ObstacleID, door: ObstacleID)
    case doorOpened(ObstacleID, revealed: [ArrowID])           // at .doorBurst
    case pipeUsed(ObstacleID, remaining: Int), pipeBroken(ObstacleID)
    case counterChanged(ObstacleID, remaining: Int), counterBroken(ObstacleID, revealed: [ArrowID])
    case elevatorActivated(ObstacleID, revealed: [ArrowID])
    case timerAlert(TimerAlert)
    case timeAdded(seconds: Int, cause: TimeCause)
    case freezeStarted(seconds: Double), freezeEnded
    case boosterUsed(BoosterID), hintShown([ArrowID])
    case stageCleared(stage: Int)
    case stageAdvanced(to: Int)
    case offer(ContinueOffer), continued(ContinueOffer)
    case won(WinResult), lost(LossReason)
}

public final class LevelSession {
    public init(plan: SessionPlan, stages: [LevelSpec], setup: AttemptSetup, rules: RulesTuning = .default)
    public private(set) var phase: Phase
    public var stage: Int { get }; public var board: BoardState { get }; public var clock: LevelClock { get }
    public var hearts: Int { get }
    public func start() -> [SessionEvent]                                 // → .intro(firstStage)
    public func tap(_ arrow: ArrowID?, at t: TimeInterval) -> [SessionEvent]   // nil = empty board point (ripple only)
    public func tick(_ dt: Double) -> [SessionEvent]
    public func ack(_ a: SessionAck) -> [SessionEvent]
    public func hold(_ r: HoldReason); public func release(_ r: HoldReason)
    public func useBooster(_ b: BoosterID) -> [SessionEvent]              // stock is the caller's (§4.9)
    public func acceptContinue() -> [SessionEvent]                        // caller already charged the coins
    public func declineContinue() -> [SessionEvent]
    public func quit() -> [SessionEvent]
    public func hint() -> [ArrowID]?                                      // Solver.hintUnit on the live board
    public func snapshot() -> SessionSnapshot
}
```
Events are returned **in causal order**; GAME forwards them unchanged to every presenter in the §8.1 order. The core never
sleeps or schedules; the headless driver and tests call `ack` themselves.

### 4.6 LevelClock (C2)
```swift
public struct LevelClock: Equatable, Sendable {
    public private(set) var limit: Int                  // the stage's timer_s (+ time added at start, none known)
    public private(set) var remaining: Double
    public private(set) var started: Bool               // false until the first tap
    public private(set) var holds: Set<HoldReason>
    public private(set) var freezeRemaining: Double     // the freeze booster (PENDING-gameplay: seconds)
    public var isRunning: Bool { started && holds.isEmpty && freezeRemaining <= 0 && remaining > 0 }
    public var displayedSeconds: Int { get }            // ceil(remaining) (DECISION; tutorials §8: first tick 0.1–1.0 s after the tap)
    public mutating func startOnFirstTap(); public mutating func tick(_ dt: Double) -> [ClockEvent]
    public mutating func hold(_ r: HoldReason); public mutating func release(_ r: HoldReason)
    public mutating func freeze(_ s: Double); public mutating func add(_ s: Int)
}
```
- Holds: pause (VERIFIED flows), popups and offers, unlock overlays/tutorials (the timer has not started yet anyway, VERIFIED
  tutorials §8), stage transitions (the timer resets per stage, VERIFIED tutorials §2), win sequence, background (DECISION).
- Alerts near 0 (colour, pulse): **PENDING-gameplay/motion-audio** (never observed; clips-needed #3). The clock emits
  `threshold(n)` for the configured list (default empty).
- Every stage of a multi-board session re-arms at its own `timer_s` (VERIFIED 3:00 each for Levels 1-4).

### 4.7 Combo ladder (C2)
```swift
public struct ComboTracker: Codable, Sendable, Equatable {
    public var window: Double = 1.25                    // INFERRED motion §2.4 (best fit 1.20–1.25 s)
    public mutating func register(tapAt t: TimeInterval, isBump: Bool) -> Int   // 1-based index of this exit in its streak
}
```
The index goes into `ExitPlan.combo`; the board maps it to a painter via `board.json` `combo.ladder` (default `[solid, solid,
violet, rainbow]`, the last entry repeats; VERIFIED colours for blue #10A2EF and the 12-hue rainbow, violet INFERRED ≈ #9A50F5).
Whether a bump or an obstacle tap breaks the streak: **PENDING-motion-audio** (`RulesTuning.combo.bumpBreaks`, default true).

### 4.8 Economy (C3)
```swift
// PlayerState.swift (◆, schema v1). Every field has a default; decoding tolerates missing keys (additive-only evolution).
public struct PlayerState: Codable, Sendable, Equatable {
    public var version = 1
    public var installSeed: UInt64                   // random at first launch (or -pc.seed); feeds the social world
    public var installDate: Date
    public var level = 1                             // next level to play (1 = the "Levels 1-4" session; then 5, 6, …)
    public var homeSeen = false                      // first home after the L6 win (VERIFIED tutorials §1)
    public var coins = 1000                          // VERIFIED start (vflows §8: 1000 + 80 + 6 × 20 = 1200 at L11 in both videos)
    public var pendingCoinFly = 0                    // won and banked, not yet flown on home (+120 on the first home)
    public var lives = LivesState()                  // count 5, anchor nil
    public var unlimitedLivesUntil: Date?
    public var boosters: [String: Int] = [:]         // BoosterID.rawValue → stock
    public var unlocksSeen: Set<String> = []
    public var tutorialsDone: Set<String> = []
    public var attempts: [Int: Int] = [:]            // session's first level → starts
    public var activeAttempt: ActiveAttempt?         // non-nil at launch = the app was killed mid-level
    public var stats = Stats()                       // wins, losses, firstTryWins (Profile), weeklyContestWins, playSeconds
    public var events = EventsState()                // PathCore/Events (additive-only)
    public var social = SocialState()                // PathCore/Social: username, avatar, country, clock high-water, ledger
    public var settings = Settings()                 // sound, music, haptic, notifications (+ debug trail override)
    public var flags = Flags()                       // ratingPromptShown, notificationPromptShown, weeklyIntroSeen, …
    public var processedTransactions: Set<String> = []
}
public enum Economy {
    public static func lives(_ s: PlayerState, now: Date, rules: EconomyRules) -> LivesStatus   // .full | .counting(n, nextAt) | .unlimited(until)
    public static func startAttempt(_ s: inout PlayerState, levels: [Int], now: Date, rules: EconomyRules) -> Result<AttemptSetup, StartError>  // .noLives
    public static func finishAttempt(_ s: inout PlayerState, outcome: AttemptOutcome, now: Date, rules: EconomyRules) -> [Grant]
    public static func reconcileOnLaunch(_ s: inout PlayerState, now: Date, rules: EconomyRules) -> [LaunchNotice]
    public static func spend(_ s: inout PlayerState, _ coins: Int) -> Bool
    public static func grant(_ s: inout PlayerState, _ g: Grant, now: Date)       // coins, boosters, unlimited lives (stacking)
    public static func useBooster(_ s: inout PlayerState, _ b: BoosterID) -> Bool
    public static func buyBooster(_ s: inout PlayerState, _ b: BoosterID, rules: EconomyRules) -> Bool
    public static func takeCoinFly(_ s: inout PlayerState) -> Int                  // home consumes pendingCoinFly
}
```
| rule | value | tag |
|---|---|---|
| start coins | 1000 | VERIFIED vflows §8 |
| reward per win | normal 20 · Hard 60 · Super Hard 100 · "Levels 1-4" 80 | VERIFIED flows, tutorials §4 |
| payout timing | coins are **banked at the win**; the home plays the fly (FTUE: L1-4 + L5 + L6 = +120 on the first home) | VERIFIED vflows §6; banking = DECISION (kill-safe) |
| continue price | 900 (every step seen) · Add Time +30 s | VERIFIED flows; escalation PENDING-gameplay |
| lives | max 5 | VERIFIED |
| life cost | a life is lost when the level is LOST (the "You will lose a life!" step declined, or Quit); a win refunds nothing | VERIFIED levels L33/L47/L52 (5 → 4) |
| refill | one life per `lifeRefillSeconds`, chained from the anchor; clock set back never punishes (MF Lives) | **PENDING-gameplay** (INFERRED ≈ 1200 s: "~20 min per life", levels L47/L52) |
| kill mid-level | counts as a loss at the next launch | DECISION default (MF precedent); **PENDING-gameplay** |
| unlimited lives | grants stack: `until = max(until, now) + duration` | VERIFIED levels L55 ("∞ 1h 20m" = 1 h on top of the 30 m) |
| boosters | freeze 3, hint 3 at install | VERIFIED items (badges "3") |
| booster prices, shop products | — | **PENDING-gameplay / PENDING-ui** (V2 shop table in vflows §8 is an older skin) |

`ShopCatalog` maps a product id (`com.manycode.arrowout.<id>`) to a `Grant` and a display price. `Grant` = coins, boosters,
unlimited-lives duration (MF `Grant.swift` copy).

### 4.9 Boosters (C3 rules, C2 session hook)
```swift
public enum BoosterEffect: Codable, Sendable, Equatable { case freezeTimer(seconds: Double), hint(units: Int), custom(String) }
public struct BoosterRule: Codable, Sendable, Equatable {
    public var id: BoosterID; public var effect: BoosterEffect; public var startStock: Int; public var price: Int?; public var unlockLevel: Int?
}
```
- Phone v552 has two: left **frozen hourglass** (id `freeze`), right **light bulb** (id `hint`) (VERIFIED items, PLAN DECISION
  02:50). Their effects were never used on the phone: **PENDING-gameplay** (defaults: `freezeTimer(10)` — INFERRED from the
  icon and MF's freezer; `hint(units: 1)` — the first unit of the solver's order from the live board, highlighted).
- The videos' extra two (yellow pointer, blue dome) are documented only (PLAN DECISION 02:50); the API admits them as
  `custom` so a later request costs data, not code.
- `session.useBooster` never touches stock: GAME checks and decrements `PlayerState.boosters` (MF rule).

### 4.10 Events (C3; opponents from Social)
Pure state machines stored in `PlayerState.events`, advanced by win/loss hooks and wall time. The opponents live in the
social world (§4.11) behind the ◆ `RivalProvider` protocol, so C3 is testable with a stub.
```swift
// EventTypes.swift (◆)
public struct WinContext: Sendable { public var levels: [Int]; public var tag: LevelTag; public var firstTry: Bool; public var now: Date }
public struct LossContext: Sendable { public var levels: [Int]; public var reason: LossReason; public var now: Date }
public enum EventOutcome: Codable, Sendable, Equatable {
    case multiplier(from: Int, to: Int)                 // x1 x5 x10 x25 x100
    case clawPoints(added: Int, total: Int, target: Int), clawStep(step: Int, reward: Grant)
    case streakRaceScore(Int)
    case skyJumpProgress(levels: Int, of: Int), skyJumpWon(share: Int, winners: Int), skyJumpFailed
    case rocketProgress(mine: Int), rocketFinished(rank: Int, reward: Grant?)
    case weeklyScore(Int)
    case grant(Grant)
}
public protocol RivalProvider: Sendable {
    func streakRace(_ instance: EventInstance, player: PlayerStanding, at: SocialTime) -> [RaceStanding]   // 5 rows
    func rocketRace(_ instance: EventInstance, joinedAt: SocialTime, at: SocialTime) -> [RaceStanding]     // 4 rivals
    func skyJump(_ run: SkyJumpRun, at: SocialTime) -> SkyJumpField                                          // players left, winners
}
```
| event | rule seeds (VERIFIED unless marked) | values |
|---|---|---|
| **streak multiplier** | a first-try win moves x1 → x5 → x10 → x25 → x100 (cap); any loss resets to x1 (flows, levels L32–L52) | ladder `[1,5,10,25,100]` |
| **Streak Race** | a timed race shown under every win/fail panel; a 5-row ranking with coin prize plates 1000/500/100/100/100 and token scores (shots/203) | score formula INFERRED (levels × multiplier); duration, reset time: **PENDING-social** |
| **Claw Challenge** | points per win = the current multiplier; a failed level removes no points; a 20-step ladder of rewards (∞ 30m, 100 coins, … bulb ×1 at 17, 600 coins, ∞ 6h, 10000 coins at 20) with thresholds 1, 200, 300, 400, 500 … (flows, levels L32–L61) | the full ladder, duration: **PENDING-gameplay** |
| **Sky Jump** | stage n: pass k levels in a row on the first try (5, then 7); 100 players drop per round; the prize splits among the winners (5000 / 7 = 714); a fail ends the run; join is free (flows) | the player curve: **PENDING-social** |
| **Rocket Race** | beat 5 levels before 4 rivals; joining grants ∞ 30m; stage-1 prize 500 coins + ∞ 45m; rivals advance on their own clock (flows L54–L58) | rival pace: **PENDING-social** |
| **Weekly Contest** | unlocks at L50 (forced tutorial on the first Play of L50); weekly score = levels won this week (INFERRED "Score : 4" 3 days in); podium prizes 2000/1000/500 (flows) | week boundary: PENDING-social (socialsim: Monday 07:00 UTC) |
| **event schedule** | which events exist at which level/time (phone: Streak Race + Claw live by L32, Sky Jump "Join" after L39, Rocket Race after L54; videos: none through L39) | **PENDING-social/gameplay** (`EventSchedule` data in `Tuning/social.json`) |

### 4.11 Social: the offline world simulation (SOC1)
SPEC-social (`design/SPEC-social.md`, in progress) owns the MODEL; this section owns the module boundary, the API and the
invariants. The social designer's Python reference is `design/social/tools/socialsim/core.py`; name data is
`design/social/data/*.txt` (given names per culture, word lists, blocklists).

**What it must do** (OWNER 02:33 point 3, verbatim intent): Weekly Contest leaderboards (Weekly / World / the player's
Country), Streak Race, Rocket Race, Sky Jump and Claw opponents are many simulated players with plausible nicknames,
countries, avatars and points that move over real time, self-sustaining for years with no updates.

**Invariants (DECISION, binding for SOC1):**
1. **Deterministic** from `(installSeed, SocialTime, the player's own ledger)`; two launches at the same time show the same world.
2. **Stateless O(1) evaluation:** every quantity is `h64(seed, "label", a, b, …)` (SplitMix64 finaliser + FNV-1a-64 of the
   label, the `tools/rng_ref.py` primitives used statelessly), permutations are a keyed 4-round Feistel with cycle walking, and
   curves are piecewise-linear tables. There is no time-stepping loop: any player at any time is computed directly.
3. **Bit-exact with the Python reference:** UInt64 wrap-around (`&*`, `&+`), only correctly-rounded IEEE operations (+ − × ÷,
   comparisons, `floor`), **no** `exp/log/pow/sin/cos/sqrt`, no fused multiply-add (`addingProduct`/`fma` are banned, and the
   goldens run under both Debug and `-O` so a compiler contraction would be caught), rounding by `floor(x)` or `floor(x + 0.5)`
   written out, `floordiv`/`posmod` helpers for negative operands (Swift `/` and `%` truncate).
4. **Calendar** (from the reference): `EPOCH = 1777273200` (2026-04-27 07:00 UTC, the original's release day); event days
   start 07:00 UTC; weeks start Monday 07:00 UTC.
5. **Rewind-safe clock:** `SocialClock.now(wall:)` returns `max(wall, highWater)` and raises `highWater`
   (`PlayerState.social.highWater`); setting the device clock back freezes the world until wall time catches up (DECISION;
   forward jumps advance it, as the original's server time would; **PENDING-social** may refine).
6. **Names** pass the blocklists (`blocklist_substring.txt`, `blocklist_token.txt`, `block_names.txt`) after leet
   normalisation; the default name format is `player_` + 7 lowercase letters/digits (VERIFIED vflows §9.1).
7. **Budget:** a 50-row page ≤ 2 ms on the iPhone 15 (≤ 1 ms on macOS `-O`); larger pages are computed off the main thread.

```swift
// SocialAPI.swift (◆)
public struct SocialTime: Hashable, Comparable, Codable, Sendable { public let seconds: Int64 }   // effective epoch seconds
public enum LeaderboardKind: Hashable, Codable, Sendable { case weekly(week: Int), world, country(String) }  // ISO 3166 alpha-2
public struct SimPlayer: Hashable, Codable, Sendable {
    public var id: UInt64; public var name: String; public var country: String; public var avatar: Int  // 0 = default silhouette
}
public struct LeaderboardRow: Hashable, Codable, Sendable {
    public var rank: Int; public var player: SimPlayer; public var value: Int; public var isMe: Bool   // value = level or score
}
public struct LeaderboardPage: Codable, Sendable { public var rows: [LeaderboardRow]; public var myRank: Int; public var total: Int }
public struct PlayerStanding: Codable, Sendable { public var name: String; public var avatar: Int; public var country: String
                                                  public var level: Int; public var ledger: [LedgerEntry] }
public final class SocialWorld: RivalProvider, @unchecked Sendable {     // immutable after init
    public init(installSeed: UInt64, config: SocialConfig, names: NameBank)
    public func page(_ kind: LeaderboardKind, me: PlayerStanding, at: SocialTime, ranks: ClosedRange<Int>) -> LeaderboardPage
    public func page(_ kind: LeaderboardKind, me: PlayerStanding, at: SocialTime, around: Int, radius: Int) -> LeaderboardPage
    public func weeklyPodium(week: Int, at: SocialTime) -> [LeaderboardRow]           // 3 rows + prizes (2000/1000/500)
    public func player(_ id: UInt64) -> SimPlayer
    // RivalProvider (§4.10)
}
public enum SocialClock { public static func now(wall: Date, highWater: inout Int64) -> SocialTime }
```
- `SocialConfig` = `Tuning/social.json` (population sizes, curves, event calendar) with compiled defaults; `NameBank` loads
  `bundle/Social/*.txt` (copied from `design/social/data/` by SOC1; a test asserts the copies are byte-identical).
- Rank semantics seeds: World = by level reached (VERIFIED vflows §9.1: 8k–11.6k at the top three months after launch);
  Country opens scrolled to the player's row, ties share a level and the player sits first among equals (VERIFIED); Weekly =
  score this week (VERIFIED phone podium "Score : 4"). Everything else **PENDING-social**.

### 4.12 Persistence (C3)
- `StateStore` (MF copy, renamed): `Application Support/Save/player.json` (REUSE §1 proposal, confirmed); JSON with sorted keys
  and ISO-8601 dates with fractions; atomic write after copying the previous file to `player.prev.json`; a corrupt file is
  kept once as `player.corrupt.json` and the backup (or a fresh state) is loaded; never crashes; `Migrations` step `version`.
- **Additive-only evolution:** sub-states (`EventsState`, `SocialState`, `Stats`, `Settings`, `Flags`) may gain fields with
  defaults (`decodeIfPresent`) without a version bump; `PersistenceTests` decodes a frozen v1 fixture written at WP0 and must
  keep decoding it forever. Renames or removals need a migration.
- The social ledger (the player's timestamped wins/scores) is capped (DECISION: last 400 entries + weekly aggregates) so the
  file stays < 64 KB.
- The app wraps the state in `@MainActor @Observable final class PlayerStore` (App/Support, §6.1): mutations go through
  `store.mutate { … }`; saves are debounced 0.3 s and immediate on attempt start, finish, purchase and
  `scenePhase == .background`; encoding and the write run on a utility queue (≤ 1 ms main-thread cost, §10).
- **No `@AppStorage`/`UserDefaults` for any state**, settings included (they live in `PlayerState.settings`). Launch args are
  read from the argument domain only.

### 4.13 RNG (C1)
```swift
public struct PathRandom: RandomNumberGenerator, Sendable {      // MF's MFRandom, renamed (REUSE §3.4)
    public init(seed: UInt64); public mutating func next() -> UInt64
    public func fork(_ label: String) -> PathRandom               // seed' = splitmix(state ^ fnv1a64(label)); does not advance self
    public static func attemptSeed(install: UInt64, level: Int, attempt: Int) -> UInt64
    public static func levelSeed(level: Int, salt: UInt64) -> UInt64      // generated levels: the same board for every player
    public mutating func unit() -> Double; public mutating func below(_ n: Int) -> Int   // own maths: stable across Swift versions
}
```
Streams: `"generator"`, `"hint"`, `"autoplay"`, `"fx"` (star jitter), `"combo"`. A new consumer never shifts another's
numbers. `RandomTests` pins the first 8 outputs for seeds 0, 1, 42 and the forks against `python3 tools/rng_ref.py`.

### 4.14 Solver, validator, generator (C2 greedy + hint; C4 the rest)
- **`Solver.greedy(_ level:) -> GreedyResult`** (C2): each round removes every unit free at its start (the spike). Exact for
  monotone boards (removals only free cells). Returns rounds (the dependency depth), the order, and the stuck set.
- **`Solver.solve(_ level:, budget:) -> SolveResult`** (C4): greedy first; when the board has non-monotone obstacles (an
  elevator or a door that REVEALS arrows, pipe counters that change a ray's destination) a bounded DFS with memo over the
  branch points; `.solved(order) | .unsolvable | .undecided(nodes)`.
- **`Solver.hintUnit(_ board:) -> [ArrowID]?`** (C2): the first unit of a solvable order from the live state (the hint booster
  and the autoplayer). Policy PENDING-gameplay.
- **`Validator.check(_ level:, sprites: SpriteCatalog?) -> [Finding]`** (C4): structure (orthogonal adjacency, no two arrows in
  one cell per layer, `dir` = last segment, the ray never meets its own body, ≥ 2 cells), obstacles (tape members parallel,
  straight, covered by one band of 2–4 lanes; pipe ends are the tube's extremities and the tube is 4-connected; doors/boxes are
  rectangles or unions the art can draw; counters ≥ 1; keys ride on existing arrows; every key has a door), values
  (`timer_s` 60…600, hearts 3, tag), provenance (`source`, `capture` for recorded/video), sprites resolvable (every door size,
  box size, tape lanes/orientation exists in the bundle's `UI/`), and **solvable** (`solve` = `.solved`).
- **Recorded levels must equal their research source** cell for cell (after the reveal merge): `pclevels import` + a diff test.
- **Generator** (C4, the spike's reverse construction, centre outwards, 304 arrows in 9 ms): silhouettes (masks), length and
  turn distributions fitted to the recorded levels, obstacle injection (tapes, doors + keys, pipes with counters, boxes with
  counters; only sizes the art has), Hard/Super Hard cadence and timers from `Levels/curve.json` (CONTENT, fitted to L1–L61;
  VERIFIED cadence seeds: Hard 34, 44, 54, Super Hard 39, 49, 59 on the phone), difficulty target per level (rounds,
  arrows, freeAtStart). Every generated level passes the validator and a HeadlessDriver win at human speed; a failure retries
  with `seed + 1` (≤ 8 tries, then the nearest authored level of the same tag — never a crash).
- **`LevelProvider`** (C4): `level(n)` = authored if `n ≤ authoredCount`, else generated with
  `PathRandom.levelSeed(level: n, salt: curve.salt)` (the same board for every player, like authored content); results are
  cached and the next level is generated on a background queue when a level starts (≤ 60 ms on device, never on the tap path).
- **`pclevels`** CLI (C4): `import <research json> [--reveal …]`, `bundle <design/levels.json> <out dir>`, `validate <dir>
  [--sprites art/ui/out]`, `solve <file>`, `bot <dir> [--rate 0.6] [--mistakes p]`, `gen <from> <to>`, `stats <dir>` (the curve
  table), `needs <dir>` (door/box sizes the art must produce).

### 4.15 HeadlessDriver (C2)
Plays a `LevelSession` with no UI: strategy (solver order, or free-first with a random pick), a human-like tap interval, a
mistake probability, and **modelled acks** (bump contact from `Timing.bump`, door burst 1.14 s after the key tap, exits from
`ExitKinematics`). Returns `DriverResult { won, timeLeft, heartsLeft, bumps, taps, events }`. Users: `LevelLibraryTests` (every
authored level), the generator gate, `pclevels bot`, difficulty bands. The app's `AutoPlayer` (§8.4) instead drives the REAL
board through the probe's tap points.

### 4.16 Motion curves and timing constants (C1)
`Ease`, `EaseToken`, `SpringCurve` are MF's files copied as-is (REUSE §3.4). New, from motion.md (every function unit-tested
against the motion.md sample points; values may be replaced by SPEC-motion-audio in the same commit as the test):
| function | measured shape | source |
|---|---|---|
| `ExitKinematics.s(τ)`, `v(τ)`, `time(toTravel:)` | `s = 71.4τ − 21.29(1 − e^(−τ/0.323))` cells; T(1)=0.078, T(5)=0.215, T(10)=0.331, T(20)=0.518, T(40)=0.836 s | VERIFIED motion §2.3 (the table is the test) |
| `Timing.exitColourRamp` | black → exit colour in 0.08 s from release | VERIFIED motion §2.2 |
| `Curves.ripple(t)` | radius 11 → 22.5 pt, luminance 180 → 250 on white, 0.25 s | VERIFIED motion §1 |
| `Curves.bump(t)` | forward to contact, hold, back, red on the return; PHONE (obstacles "BUMP"): ≈400 pt/s out, back ≈0.13 s; YT-B: out ≈0.09 s accelerating, hold 0.10 s, back 0.10 s ease-out | the two sources disagree → **PENDING-motion-audio** (phone wins, owner 02:55) |
| `Curves.vignette(t)` | red screen-edge glow ≈50 pt deep, full 0.05 s, fade 0.28 s (0.33 s total) | VERIFIED motion §3 (YT-B) |
| `Curves.hudDrop`, `boosterSlide` | springs: response 0.429 s / damping 0.47; response 0.245 s / damping 0.43 | VERIFIED motion §5.1 |
| `Curves.bigTimer(t)`, `heartPop(t)` | 3.5× → 2.65 → 2.2 → 1.6 → 1.12 → 0.8 → 1.0 (0.50–0.749 s); hearts 1.58 → 0.89 → 1.0, stagger 0.10–0.12 s | VERIFIED motion §5.1 |
| `Curves.buildIn(t)` | every arrow draws tail → head at once, ink 93 % at 0.25 s, 100 % at 0.33 s (ease-out); heads appear when reached | VERIFIED motion §5.1 (YT-B); phone PENDING (clips-needed #12) |
| `Curves.unlockOverlay` | icon +0.24 (overshoot, settle +0.40), title +0.52, "Unlocked!" +0.60, card +0.76, sparkles from +1.1; dismiss fade 0.25 s | VERIFIED motion §5.3, tutorials §6 |
| `Curves.captionPop`, `handIn`, `handLoop` | caption 0.7 → 1.10 → 1.0 (ease-out-back 0.20 s); hand 0.24 → 1.0 (0.28 s ease-out); press 1.0 → 0.53 (0.48 s) → 1.0 (0.36 s), loop period 2.1 s | VERIFIED tutorials §3 (loop INFERRED) |
| `Curves.keyFlight(t, from, to)` | sag 8.6 pt (0.749–0.832) → float up 41 pt (0.22 s) → dive g ≈ 7650 pt/s² → insert 0.15 s → turn 0.1 s → burst at tap + 1.14 s | VERIFIED motion §4.2 (one key; far doors clips-needed #14) |
| `Curves.debris(t)` | pop ≈14 pt up, fall g ≈ 1000 pt/s², lifetime ≈ 0.9 s | VERIFIED timing, INFERRED g |
| `Curves.clearWave(t)` | rainbow ring from the board centre through the dots ≈ 0.45 s, then the dots fade | VERIFIED motion §5.6 |
| `Curves.win(t)` | the beat table: sign in −0.16 → 0, letters +0.08, arrow sign +0.08 → +0.32, OUT! slam +0.40 → +0.96, dim +0.68 → +1.04, confetti/fireworks, panel **+3.36 s**; a tap skips to the panel | VERIFIED motion §5.6 (YT-A ×2) |
| `Curves.coinFly(t)` | +0.25 "+N" appears; 5 coins lift +0.80 → +1.36, each arrival adds N/5 and sparkles the pill; done ≈ +1.6 s | VERIFIED vflows §6 |
| `Timing.stageGap` | 0.7 s from the last exit to the next board | VERIFIED tutorials §2 |

### 4.17 Core tests (`swift test`; CORE and SOCIAL own them)
| suite | must cover |
|---|---|
| `GridTests`, `GeometryTests` (C1) | fit rule on all 30 recorded levels (±0.03 pt); zoom limits; `centre`/`cell(at:)` round trip; head geometry per direction; arc length exactness; hit geometry: 873 + 399 jittered points 0 wrong (spike), head-apex taps, 15 pt radius, the right-hand tie |
| `LevelJSONTests` (C1) | every `research/levels/*.json` (41 files) and every video extract (58) decodes; unknown keys reported; bundle round trip |
| `KinematicsTests`, `CurvesTests` (C1) | the motion §2.3 T(d) table ±0.003 s; each §4.16 curve at its sample points |
| `RandomTests` (C1) | golden values vs `tools/rng_ref.py`; fork independence; level seeds stable |
| `RulesTests` (C2) | each §4.4 row with a fixture: L32 tapes, L33 door order + blocking until the ack, L35 pipe 2 → 1 → 0 break, L42 U-pipes, L50 box ×10, L51 three boxes together, V2-L031 elevator, a corner fixture, queued taps (P02), bump gap/contact, marked arrows stay tappable |
| `SessionTests`, `ClockTests`, `ComboTests` (C2) | the §4.5 diagram path by path; timer starts at the first tap, never at intro/zoom; holds keep `remaining` constant; Levels 1-4 as one session with 4 stages and one win (reward 80); win beats fail; the fail chain; combo indices at 1.25 s |
| `GoldenRoundsTests` (C2) | **golden test from real play:** every arrow the phone bot tapped in round k (`research/bot/log.jsonl`, `result == "tapped"`, L32–L61, mapped by cell set with the best integer shift) is FREE in our rules at the start of that round; 0 mismatches (`Tests/tools/golden_rounds.py` builds the fixture) |
| `HeadlessTests` (C2) | the driver wins every recorded level at 0.6 s per tap with ≥ 20 % time left; mistakes cost hearts as the rules say |
| `EconomyTests`, `LivesTests`, `BoostersTests`, `EventsTests` (C3) | §4.8–§4.10 rows; lives chain against `Tests/tools/lives_ref.py` (independent Python reference, exact); clock set back never punishes; unlimited stacking; kill = loss; FTUE payout 1000 → 1120 |
| `PersistenceTests` (C3) | round trip; atomic + backup; corrupt → backup; the frozen v1 fixture decodes; additive fields decode from old JSON |
| `SolverTests`, `ValidatorTests`, `GeneratorTests`, `LevelLibraryTests` (C4) | greedy = DFS on monotone boards; DFS solves the non-monotone fixtures greedy cannot; the validator's findings on broken fixtures; 500 generated levels deterministic (same bytes twice), valid, solvable, in their curve bands; every authored level valid + won by the driver |
| `Social*Tests` (SOC1) | bit-exact goldens vs `design/social/fixtures/` (hashes, perms, interp, calendar, names, pages at ≥ 20 times over 3 years); rewind; blocklists on 100 k names; page cost |
| `APISurfaceTests` (C2) | calls every public member of every ◆ PathCore type WITHOUT `@testable` |

**Mutation checks** (GP §8.3; each C/SOC WP reports CAUGHT/MISSED per mutation; one MISSED = a weak test to fix): at least
C1: 4 (fit cap, a head offset, a kinematics constant, a cell-index off-by-one); C2: 6 (ray stops one cell early, tape
all-clear → any-clear, door opens at the tap, pipe consumes on a bump, timer starts at intro, win not beating fail);
C3: 5 (refill interval, anchor on a win, stacking, a Claw point on a loss, backup skipped); C4: 3; SOC1: 4 (banker's
rounding, truncating division, a hash label typo, rewind allowed).

---

## 5 Engine / board

The spike's Core Animation engine (VERIFIED spike, `build/spike/App/Render/*`) goes to production. The spike source is the
reference implementation for B1; the orchestrator commits it to `design/spike-src/` before WP0 (REUSE §7 item 1, §11 R12).

### 5.1 Host and view tree (B1)
One `BoardEngine` (`@MainActor final class`, implements `BoardControlling`) and one `BoardContainerView` live for the whole app
run: they are created at boot, warmed up behind Loading (§5.9) and re-loaded per stage (304 arrows build in 1.6 ms, VERIFIED
spike). `BoardHost` (`UIViewRepresentable`) hosts the container edge to edge, ignoring the safe area; it never re-creates it.
```
BoardContainerView (full screen)
 ├─ BoardScrollView: UIScrollView (full screen; zoom + pan; clipsToBounds = true at the SCREEN edge)
 │   └─ BoardContentView (bounds = layout.contentSize at zoom 1; clipsToBounds = false so exits run to the screen edge)
 │       └─ stage: CALayer            (speed / timeOffset: capture freeze and slow motion, §5.12)
 │           ├─ dotsRoot              1 dashed CAShapeLayer per departed arrow (#C5E1FF)
 │           ├─ restRoot              per resting arrow: body CAShapeLayer + head CAShapeLayer (frames hug their paths, P4)
 │           ├─ obstacleRoot          doors + locks, boxes/curtains + counters, elevator platforms, corner wedges
 │           ├─ tapeRoot              tapes (OVER their arrows, STYLE §A.2) and keys (on their arrows)
 │           ├─ moverRoot             exits and bumps: built at tap time, removed by animation delegates
 │           ├─ tubeRoot              pipe tubes (translucent: an arrow passes UNDER/inside), mouths, counter boxes + digits
 │           └─ fxRoot                stars, shards, key flight, clear wave, hint highlight, bump ✖ badge
 └─ ScreenFXView (screen space, not zoomed, no touches): tap ripples, red bump vignette
```
Layering is VERIFIED: an exiting arrow is **above** idle arrows and obstacles and **below** the HUD and boosters (motion §2.2,
runner shots L038-r07, L048-r17); a pipe arrow is drawn inside the translucent tube (motion §2.2). The SwiftUI HUD sits above
the host, so "under the HUD" needs no work.

The board owns the app's single `CADisplayLink` (`preferredFrameRateRange` 60…120) and calls `delegate.boardFrame` every
frame: this is the master clock that ticks the session and the HUD throttle (§8.1). No other per-frame timer exists in play.

### 5.2 Layout, zoom and pan (B1)
- `BoardLayout.fit` (§4.2): pitch = min(W/(cols+2), H/(rows+2), 28.07 pt), content centred in the play rect 122…755 pt.
- `minimumZoomScale = 0.786`, `maximumZoomScale = layout.maxZoom` (= absolute 28.07 pt per cell; a board whose fit pitch is
  already 28.07 cannot zoom in) — VERIFIED levels L47/L50. Zoom limits and the cap live in `board.json` (`zoom.min`,
  `zoom.maxPitch`) and `-pc.zoom Z` sets the start zoom for labs/captures.
- Centring: while the zoomed content is smaller than the play rect it stays centred (VERIFIED "at min zoom the board is
  centred"); `contentInset` is recomputed in `scrollViewDidZoom`.
- **Pan** works at every zoom, fit included: a 52 pt swipe on an arrow panned the board ~30 pt and the pan persisted (VERIFIED
  levels L47e). Pan limits and snap-back are unmeasured (clips-needed #13): `board.json pan.slackPt` (default 120 pt beyond each
  content edge, DECISION) and `pan.bounces` (default true) — **PENDING-motion-audio**.
- No double-tap zoom (VERIFIED shot 008). A pinch, pan or zoom never starts the level timer (VERIFIED L47a): the board does not
  report them as taps.
- Strokes stay vector-crisp at every zoom with no `contentsScale` work (VERIFIED spike: 2 partial px per stroke at 3×); sprites
  are drawn at the 32 pt design pitch @3x, crisp up to 32 pt/cell ≥ the 28.07 cap (VERIFIED PIPE §0.3).

### 5.3 Input: fire-on-release and the hit test (B1)
- `ReleaseTapRecognizer` (spike code, P5) on the scroll view: fails on a second touch (pinch) or a move beyond `slop` (10 pt,
  VERIFIED spike; the phone's value PENDING-motion-audio); ends on `touchesEnded`; `require(toFail:)` the scroll view's pan and
  pinch recognisers (spike). It passes `touch.timestamp` to the delegate for the latency probe.
  **First-day check R1:** the recogniser's `.ended` must arrive in the SAME event dispatch as `touchesEnded` (no deferred
  failure wait). Fallback: drop `require(toFail:)` and test `panGestureRecognizer.state`, `isZooming`, `isDecelerating`
  inside `touchesEnded`.
- Hit test in content space (`HitGeometry`, §4.2): the owner of the touched cell; else the nearest centreline (the head apex
  segment included: head taps work, VERIFIED L47b) within `max(0.5·pitch, hitRadiusPt / zoom)`, `hitRadiusPt = 15` (VERIFIED ≥
  15 pt, L47c; the true limit PENDING-gameplay, clips-needed #16); ties → `rightThenDown` (VERIFIED once, L52a). Hidden,
  inactive-layer and moving arrows are excluded; obstacles are never hit.
- A **tap ripple** is drawn on every release inside the board area, hit or miss (VERIFIED on hits; the miss case is a
  DECISION).
- `inputEnabled` is false during the build-in and every popup/overlay; `allowedArrows` restricts taps for tutorials that need
  it (the "Tap to move!" hint does not: tutorials §3).
- Swipes and holds never fire (VERIFIED: a swipe pans, a 5 s hold fires on release).

### 5.4 Resting arrows: `ArrowNode` (B1)
| part | recipe | source |
|---|---|---|
| body | `CAShapeLayer`, path = the sharp polyline through the cell centres (tail → head centre), `lineWidth = 0.22·p`, `lineCap = .round`, `lineJoin = .round` (outer corner radius = half the stroke, inner corner sharp), `strokeColor` #000000, no fill | VERIFIED STYLE §A, spike |
| head | `CAShapeLayer` filled #000000: rounded triangle (base 0.616 p, length 0.61 p, corner r 0.047 p), apex `headApexPast(dir)` past the head cell centre, rotated to `dir` | VERIFIED STYLE §A (per-direction apex) |
| marked (bumped) | stroke + fill `#EE0A13` (238, 10, 19) for the rest of the level | VERIFIED items, obstacles |
| key | sprite `keyOnArrow` registered on the key's 2 cells (STYLE §A.2), in `tapeRoot` | VERIFIED art |
| frames | `LocalPath`: each layer's frame hugs its path (+ head pad) so off-screen arrows are culled at max zoom | VERIFIED spike P4 |
| hidden arrows | not in the tree until revealed | DECISION |

Paths are in content space at fit; the scroll view's zoom scales strokes with the board (VERIFIED STYLE: "the stroke scales
with the zoom"). A resting arrow is exactly 2 layers and has no animations.

### 5.5 Movers: exit and bump (B1 solid; B2 the combo painters)
**Exit mover** — everything in ONE `CATransaction` with actions disabled, `addSublayer` included (P1):
1. **Path:** the plan's `ExitPath` cells → content points; the last direction extended past the grid edge to the far rect
   (the visible screen rect ∪ the content, outset by 25 % of the screen, so a zoom-out mid-exit still ends off-screen; spike)
   plus the arrow's length and a stroke width. The exit ends when the TAIL leaves the screen (VERIFIED motion §2.2).
2. **Timing:** `ExitKinematics` (§4.16) in cells → keyframes at every display frame (1/60 s) plus one at every corner/tube
   turn, `calculationMode = .linear`, `timingFunctions = nil` (exact linear between samples, GP §13), `beginTime = 0` (= now),
   `preferredFrameRateRange` 60…120.
3. **Layers:** the trimmed body (`strokeStart`/`strokeEnd` keyframes over the whole path), the head (`position` + `transform`
   rotation keyframes; the rotation steps at corners and tube turns), the resting layers hidden in the same transaction.
4. **Colour:** the painter's layers carry the exit colour as the model value; a black copy of the trimmed stroke + head sits on
   top and fades 1 → 0 over **0.08 s** (VERIFIED motion §2.2 ramp; one mechanism for every painter).
5. **Dots:** one dashed `CAShapeLayer` per departed arrow on the body polyline extended 1 pt past the head (P3),
   `lineDashPattern = [0.01, p − 0.01]`, round caps, `lineWidth = 0.192·p`, #C5E1FF; `strokeEnd` keyframes reveal each dot on
   the frame the tail leaves its cell (VERIFIED instant, motion §2.5). The layer stays in `dotsRoot`.
6. **Stars:** one `CAEmitterLayer` per exit following the tail (`emitterPosition` keyframes), `beginTime = convertTime(now)`
   (P2); star cells in the painter's colours, jittered ±½ cell, fading in ≈ 0.4–0.6 s (VERIFIED look motion §2.2; counts and
   sizes PENDING-motion-audio).
7. **Tape carry:** the tape sprite moves with its bundle (the members are parallel straight arrows: one common translation).
8. **Beats:** each `PlanBeat` becomes an animation on the relevant layer with `beginTime = start + t(s)`; the beats that the
   core needs back (`exitLeftBoard`, `lastExitLeftBoard`, `pipeBroken`, `counterBroken`) are reported from that animation's
   `animationDidStart`. **Never timers** (spike rule).
9. **End:** a 1 → 1 opacity "end" animation whose delegate removes the mover's layers and reports `exitFinished`.

**Painters** (`board.json combo.ladder`, §4.7):
| painter | look | source |
|---|---|---|
| `solid` | #10A2EF body + head | VERIFIED motion §2.2 (runner shot, 17 samples) |
| `violet` | ≈ #9A50F5 (video) | INFERRED; lossless sample PENDING-motion-audio (clips-needed #10) |
| `rainbow` | spike painter A: one `CAGradientLayer` per straight run with a stop at every palette step along the arc length, masked by the trimmed stroke + moving head; the 12-hue palette #FF6500 · #FFCE01 · #9DE600 · #37E500 · #00E100 · #00D3AF · #00C1FF · #4079FF · #8D5FFF · #BC4BF3 · #FF2FC6 · #FF5A85; bands fixed on the path | VERIFIED palette motion §2.4, technique spike 3e; period PENDING-motion-audio (5.6 cells spike vs 3.8 STYLE) |
`-pc.trail solid|rainbow|ladder` overrides the ladder (debug). Gradient runs cost 2.9–6.3 ms per 5 exits on the simulator
(VERIFIED spike): if the phone's tap cost exceeds §10's 4 ms, B2 prebuilds each arrow's runs lazily in idle frames (≤ 2 ms per
frame) after the level loads (R2).

**Bump mover** (B1):
- The arrow snakes **along its own path** toward the blocker (VERIFIED phone, obstacles "BUMP": "the tail follows the body"),
  stops when the apex touches the blocker's stroke edge (`contactCells`), holds, and slides back. Profile numbers:
  `Curves.bump` (PENDING-motion-audio: phone ≈ 400 pt/s out / ≈ 0.13 s back vs YT-B 0.09 s / 0.10 s hold / 0.10 s back; the
  phone wins).
- It turns **red on the return** and stays red (VERIFIED phone ≈ 516 ms into the clip; model value = red).
- At contact: the blocker flashes red and a red ✖ badge with a dark outline sits at `contactPoint` (fade ≈ 0.3 s, VERIFIED
  obstacles); the screen-edge red vignette starts (ScreenFX, 0.33 s, VERIFIED motion §3); the board reports
  `.bumpContact(arrow)` from the contact keyframe's `animationDidStart` → the session takes the heart on that frame (§8.3).
- No shake, no sound (VERIFIED motion §3, sounds §1). `.bumpFinished` when it is back at rest.

### 5.6 Obstacle layers (B2; sprites from `art/ui/out`, drawn at 32 pt per cell and scaled by `pitch/32`)
| obstacle | resting look | motion / events | source |
|---|---|---|---|
| **tape** | sprite `tape{V,H}{2,3,4}` centred on the bundle's cell block, over its arrows | carried with the bundle | VERIFIED art (done), STYLE §A.2 |
| **door + lock** | sprite `doorW{w}H{h}` anchored at the block's top-left + `lockHex` on the door's centre line, 0.18 p below its bbox centre | key flight (`Curves.keyFlight`: sag, float, dive into the target lock, insert, turn), white flash on the lock, **burst** at tap + 1.14 s: the door sprite goes, ≈ 60 shards (purple/orange/blue) pop and fall (g ≈ 1000 pt/s², ≈ 0.9 s), the revealed arrows' layers appear on the burst frame; reports `.doorBurst(id)` | VERIFIED motion §4.2, levels L33, STYLE §A.2 |
| **pipe** | tube = vector (`CAShapeLayer` strokes along the tube centreline, 1.00 p wide, outer corner r 0.43 p, inner 0.07 p, layered strokes approximating the measured cross-section: dark base, light ramp, hard-edged highlight toward the upper right, bright rims; a grey shadow stroke offset down-left), translucent so a passing arrow reads lighter blue; mouths `pipeMouth` (gold collars 0.10 p outward); counter box `pipeCounter` + digits (white fill, #822521 outline) | the arrow passes under the tube; the counter changes at its beat; on the last pass the tube, box and rims **shatter** (cyan/orange shards, gravity) 0.05 s after the head leaves the far mouth; the tube's cells then show vacated dots | VERIFIED STYLE §A.2, motion §4.3, levels L35 |
| **box** (phone) | the purple slab with 4 corner bolts and a silver 4-lobed counter ring + digits | counter ticks at its beat; at 0 it breaks (shards) and its cells show vacated dots | VERIFIED levels L50/L51, items |
| **curtain** (video V1) | sprite `curtainCrate` (3 × 3) + ring + digits | as box; reveals what it covered | VERIFIED STYLE §A.2 (video) |
| **elevator** (video V2) | code: a translucent hatched lavender platform under its layer-1 arrows | on activation the platform darkens and merges, layer-2 arrows fade in ≈ 0.25 s | VERIFIED motion §4.4 (V2) |
| **corner** | sprite `cornerWedge`, rotated per `turn` | the exit path bends at it | INFERRED web §3; not in v552 levels |

- **Sprite sizes:** doors are per-size sprites (`doorW4H4` … `doorW22H10` exist, ID-MAP "board"); `pclevels needs` lists the
  sizes every bundled level requires, and the generator only uses sizes present in the bundle (§4.14). Boxes of arbitrary size
  need either per-size sprites (`boxW{w}H{h}`, the door route) or a stretchable slice set (`boxSlice` + `boxRing`): **request to
  UI-ART** (ID-MAP has no box entries yet); B2 implements whichever UI-ART ships, and the validator checks it resolves.
- **Digits** (`DigitGlyphs`): CoreText glyph paths of `PCDisplay-Black` in a `CAShapeLayer` (fill + outside stroke), cached
  per string, crisp at every zoom (D16). The counter-change animation is unmeasured (clips-needed #17): PENDING-motion-audio.
- **Shards** are a pool of pre-built layers animated with keyframes from the `fx` RNG stream (deterministic, freezable for
  captures) rather than emitters (DECISION).
- **Silhouette border** (a magenta/blue outline seen only in store shot 5): not drawn unless SPEC-ui finds it on a v552 level
  (`boardSilhouetteBorder`, PENDING-ui).

### 5.7 Level intro, stage transitions and the board-clear wave (B1 intro; B2 the rest)
- **Build-in** (`playIntro`): every arrow's body `strokeEnd` 0 → 1 at once with `Curves.buildIn` (≈ 0.33 s ease-out), each head
  appearing when its stroke reaches it; obstacle sprites fade in (PENDING-motion-audio); one transaction; `.introFinished` at
  the end. The HUD drop runs in SwiftUI at the same time (§6.5). The FTUE's first board uses `.growFromTailsNoHUD` (the HUD is
  already in place after the Loading cross-fade; VERIFIED tutorials §3/§5).
- **Stage transition** (Levels 1-4, `playStageTransition`): the clear wave, then the dots fade, then the next board builds in;
  ≈ 0.7 s from the last exit leaving to the new board (VERIFIED tutorials §2). The phone skin shows no dot lattice before
  cells are vacated (VERIFIED motion §2.5), so the V1 video's "dot grid first" is not copied (phone wins).
  `.stageTransitionDone` at the end.
- **Board-clear wave** (`playClearWave`, before the win celebration): a radial rainbow ring expands from the board centre
  through the vacated dots in ≈ 0.45 s, then the dots fade (VERIFIED motion §5.6). One `CAGradientLayer` (type `.radial`, the
  palette as a ring, `locations` animated outward) masked by ONE `CAShapeLayer` holding every dot position (built once at the
  clear, ≤ 1 ms). `.clearWaveFinished`.

### 5.8 Screen-space feedback (B1)
- **Tap ripple:** a grey disc at the release point, radius 11 → 22.5 pt, luminance 180 → 250 on white (fading), 0.25 s
  (`Curves.ripple`, VERIFIED motion §1, 3 clips), from a pool of 6 pre-built layers (never allocated on the tap path), added in
  the tap's transaction.
- **Bump vignette:** 4 edge gradient layers (red, ≈ 50 pt deep), opacity keyframes of `Curves.vignette` (VERIFIED motion §3,
  YT-B; the phone's "faint red tint over the screen" agrees, obstacles).

### 5.9 Warm-up, caching, memory (B1, B2 extends)
**Warm-up** (`prepare()`, awaited by the boot sequence behind the Loading screen, budget ≤ 0.5 s on the iPhone 15; §10):
1. Load a built-in warm-up board (every obstacle kind, ~40 arrows) into the REAL view tree under the opaque Loading view and let
   it render for 2 frames.
2. Run, at `stage.speed = 20`, one exit per painter (solid, violet, rainbow + stars), a bump with the vignette, a key flight and
   door burst, a pipe pass and break, a box break, a clear wave and a ripple, so every layer class, gradient, mask, emitter and
   shape path is compiled once before the player's first tap.
3. Decode the sprites of the next levels (`preload`) with ImageIO at the pixel size they need at max zoom, into `SpriteCache`
   (LRU, cap 48 MB).
4. Build `DigitGlyphs` for "0"…"99".
5. Log `[PC][warmup] board <s> s` (§9.3). **First-day check R3** proves on the phone that the first real exit/bump/burst after
   install has no frame > 20 ms.

**Memory** (DECISION, §10): the board ≤ 40 MB at the densest level (spike: 22–26 MB for 304 arrows), `SpriteCache` ≤ 48 MB.

### 5.10 Board contract (`App/Contracts/BoardContract.swift` ◆)
```swift
@MainActor protocol BoardControlling: AnyObject {
    var delegate: BoardDelegate? { get set }
    var view: UIView { get }                                    // the BoardContainerView
    var inputEnabled: Bool { get set }
    var allowedArrows: Set<ArrowID>? { get set }                // tutorial restriction; nil = all
    var zoomScale: CGFloat { get }
    var pitchOnScreen: CGFloat { get }
    var isSettled: Bool { get }                                  // no mover, no transition, intro done (capture readiness)
    func prepare() async                                         // §5.9 warm-up, idempotent
    func preload(_ levels: [LevelSpec])                          // background sprite decode for the next levels
    func load(_ stage: StageSetup)                               // build the rest layers (hidden until playIntro)
    func playIntro(_ style: IntroStyle)
    func present(_ events: [SessionEvent])                       // exits, bumps, marks, reveals, counters, hint, freeze
    func playStageTransition(to next: StageSetup)
    func playClearWave()
    func clear()
    func setHint(_ arrows: [ArrowID])                            // [] clears
    func screenPoint(of arrow: ArrowID) -> CGPoint?              // the arrow's hand anchor (tutorial) in screen pt
    func tapPoint(of arrow: ArrowID) -> CGPoint?                 // a safe on-screen tap point (not under HUD/boosters)
    func setFrozen(_ frozen: Bool)                               // capture freeze (§5.12)
    func setTimeScale(_ k: Double)                               // slow motion
    func probe() -> BoardProbeData                               // §9.4
}
@MainActor protocol BoardDelegate: AnyObject {
    func boardFrame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval)      // the master clock (every frame)
    func boardReleased(arrow: ArrowID?, contentPoint: CGPoint, touchTimestamp: TimeInterval)
    func boardBeat(_ beat: BoardBeat)
    func boardZoomChanged(scale: CGFloat)
}
enum BoardBeat: Equatable {
    case introFinished, bumpContact(ArrowID), bumpFinished(ArrowID), doorBurst(ObstacleID), pipeBroken(ObstacleID),
         counterBroken(ObstacleID), exitLeftBoard(ArrowID), exitFinished(ArrowID), lastExitLeftBoard,
         stageTransitionDone, clearWaveFinished
}
struct StageSetup { let level: LevelSpec; let layout: BoardLayout; let stage: Int; let stages: Int; let seed: UInt64 }
enum IntroStyle { case growFromTails, growFromTailsNoHUD, none }
struct BoardProbeData: Codable { /* §9.4 fields */ }
```
The engine **queues** commands that arrive before its first layout and replays them after (the Arrows/MF rule), and never
awaits the layout of a view that is not in a window (GP §13 boot hang).

### 5.11 Engine rules (the spike pitfalls, binding)
1. **P1** Every model write and every `addSublayer` happens inside `CATransaction.begin(); setDisableActions(true)`.
   (Otherwise the implicit 0.25 s fade makes the first frames of every exit translucent: 64 % / 83 % ink measured.)
2. **P2** Every `CAEmitterLayer.beginTime = parent.convertTime(CACurrentMediaTime(), from: nil)`.
3. **P3** Dots paths extend 1 pt past the head (a zero-length dash at the path end is dropped half the time).
4. **P4** Frames hug their paths; the long exit path exists only while moving.
5. **P5** Taps fire on release through `ReleaseTapRecognizer`; never `UITapGestureRecognizer` (gives up on long holds).
6. **P6** Nested funcs inside `@MainActor` methods are `@MainActor`; no exclusivity conflicts (`getRed(&a[0], …)`).
7. **P7** Long numeric expressions are split into typed `let`s (type-checker timeouts under swap).
8. **P8** Test hooks (the probe) refresh continuously (≤ 4 Hz), never once.
9. **P9** Dense boards bump at gap 0: the bump's timing comes from the measured profile, not from geometry.
10. `beginTime = 0` means now; exact linear = `timingFunction = nil`; a finished animation is removed by its delegate.
11. No `shouldRasterize`, no runtime `shadowPath`-less shadows (sprites carry baked shadows), no `CATextLayer`, no
    `drawsAsynchronously`, no `UIView` per arrow.
12. No allocation on the tap path beyond the mover's layers: ripples and shards come from pools; paths and sprites are cached.
13. Offscreen passes: only rainbow masks and the clear-wave mask; the soak (§10.4) proves 5 concurrent masked movers.

### 5.12 Freeze, slow motion and BoardLab (B1 host, B2 scenarios)
- **Freeze:** `stage.speed = 0; stage.timeOffset = stage.convertTime(CACurrentMediaTime(), from: nil)` (VERIFIED spike);
  ScreenFXView likewise; `MotionClock` mirrors it for SwiftUI. `-pc.freezeAt <sequence>@<t>` shows the frame at t s into a
  sequence: `intro, exit, bump, keyFlight, doorBurst, pipeBreak, boxBreak, clearWave, stageGap` (board) plus the shell's
  `hudIntro, win, unlock, coinFly, caption` (§9.2).
- **Slow motion:** `-pc.slowmo N` → `stage.speed = 1/N` and `MotionClock.timeScale = 1/N`.
- **BoardLab** (`-pc.go boardlab -pc.lab <scenario> [-pc.labBoard synth40|L032|L039|…] [-pc.zoom Z]`): scenarios `idle,
  exit5, exitWaves, rainbow5, bump, hittest, latency, zoomramp, intro, tape, door, pipe, box, curtain, elevator, corner,
  clearwave, stageGap, soak, autoplay`. Each writes `Documents/lab-ready.json` and `Documents/lab-perf.json` (§9.5) and prints
  the §9.3 marks. It drives the REAL engine with scripted taps through `boardReleased`.

---

## 6 Shell

SwiftUI + Observation. SHELL owns the views (`App/Shell/**`, `App/FX/**`), SOCIAL owns `App/Shell/Social/**` (SOC2), GAME owns
the glue that drives them (§8). Looks, copy and exact frames come from SPEC-ui + `design/ui-tokens.json` (component ids such as
`hud.timerPill`, `pause.resume`); this section fixes structure, timing mechanisms and ownership.

### 6.1 App structure and navigation (S1; composition root WP0 → G1)
`GameApp` (@main, LEAD) builds one `AppModel` (App/AppModel.swift) injected with `.environment`:
`PlayerStore`, `Router`, `PopupHost`, `ToastCenter`, `StoreService` (or `FakeStore`), `AudioEngine`, `Haptics`, `BoardEngine`
(created at boot, never destroyed), `MotionClock`, `Tuning`, `LaunchArgs`, `LevelLibrary` + `LevelProvider`, `SocialModel`
(wrapping `SocialWorld` + the rewind-safe clock), `HUDModel`, `AnchorRegistry`, `FXPlaying`.

No `NavigationStack`: the game is a set of full-screen states. The root applies `.preferredColorScheme(.light)` (the game has a
fixed palette; no dark mode, REUSE §4) and hides the status bar.
```swift
// ShellContract.swift (◆)
enum Screen: Equatable {
    case loading                                   // cold launch; the iOS notification prompt may sit over it (first launch)
    case home(HomeEntry, tab: HomeTab)             // the 3-tab bottom nav: shop · home · leaderboard (VERIFIED flows, tutorials §5)
    case level(LevelLaunch)                        // the board + HUD
    case event(EventScreen)                        // full-screen event pages (Claw, Streak Race, Rocket Race, Sky Jump map)
    case profile
    case lab(LabID)                                // boardlab | shelllab | soundboard | sociallab (debug hooks)
}
enum HomeTab: String { case shop, home, leaderboard }
enum HomeEntry: Equatable { case normal, afterWin(WinSummary), afterLoss, firstHome(WinSummary) }
struct LevelLaunch: Equatable { let session: String; let levels: [Int]; let isRetry: Bool; let firstStage: Int }
struct WinSummary: Equatable { let levels: [Int]; let reward: Int; let tag: LevelTag; let outcomes: [EventOutcome] }
```
| transition | how | source |
|---|---|---|
| launch → Loading | the launch screen colour, then the SwiftUI Loading screen on the first frame; stays ≥ `ui.loading.minSeconds` (PENDING-ui) and until the boot sequence (§8.5) finishes (cap 4 s) | VERIFIED tutorials §1 rows 2–3 |
| Loading → first board (fresh install) | ≈ 0.1–0.16 s cross-fade into "Levels 1-4" with the HUD already in place (no HUD intro) | VERIFIED tutorials §1, motion §5.4 |
| Loading → home (returning player) | cross-fade (PENDING-ui) | INFERRED |
| home → level | **hard cut**, then the board build-in + HUD drop | VERIFIED motion §5.1 |
| win panel Continue → home | hard cut, then the coin payout on home | VERIFIED vflows §6, sounds cue 2 |
| home tabs | the nav swaps pages (animation PENDING-ui) | — |
| popups | appear and disappear **instantly**; the dim reaches its alpha in 0–0.1 s | VERIFIED motion §5.3 (60 fps YT-B) |

### 6.2 First-run routing and the level loop (S1 router; G2 FTUE director)
- Fresh install: Loading → **"Levels 1-4"** (4 stages, one session) → win panel "Level 1-4 / 80" → Continue → **Level 5**
  directly → win → **Level 6** directly → win → Continue → the **first home**, which pays out +120 on the 1000 start
  (1000 → 1120) (VERIFIED tutorials §1/§4). Rule in `Router`: while `homeSeen == false`, the next screen after a win is the
  next level; the chain length is data (`game.json ftue.chainUntilLevel = 7`).
- From L7 on (VERIFIED vflows §3): home → Play → [unlock overlay, the first time only] → level intro → play → last arrow →
  clear wave → celebration → win panel → Continue → home (+N coin fly; a new Hard/Super Hard look if the next level has one) →
  Play. No level-start dialog, no "Level N" card, no ads.
- A loss: Level Failed → **Try Again** (same board, VERIFIED levels L32) or X → home. A loss before the first home retries.
- Play at 0 lives: the no-lives popup (the original's copy and offers are unrecorded: PENDING-ui/gameplay). Try Again passes
  the same lives gate (DECISION).

### 6.3 Loading screen (S1)
`LoadingScreen`: full-bleed `loadingBackdrop` art + our "ARROW OUT!" logo (`logoArrowOut`) at `loading.logo` + characters +
"Loading" with dots cycling "." → ".." → "..." (VERIFIED tutorials §1; frames `uim` `loading`). It is the cover for the boot
sequence and the board warm-up (§5.9, §8.5): its own animation is a SwiftUI `TimelineView` limited to the dots (cheap) so the
warm-up's frames are not starved.

### 6.4 Home (S1 skeleton; S3 complete)
Z-order and frames: `uim` "Home" (shots 026, 035, 060, 064, 070). Layers back → front:
1. **Scene:** `homeBackdrop` (full bleed), `homePlatform`, `homeConsole`, `homeCapsuleMachine` + the arrow pile
   (`homeArrowPile{Full,Half,Low}`, meaning PENDING-ui).
2. **Characters** (`PuppetStage`, D14): the pink scientist (`char_sci_home_rig`) and the two BLUE workers
   (`char_wk_home{L,R}_blue_rig`), OWNER 02:33/02:55. A rig = layers with `rect_pt`, `z`, `pivots_pt`, groups with one default
   member (VERIFIED `art/out/*_rig/rig.json`). `PuppetRig` loads it; `PuppetStage` (a `UIViewRepresentable` of `CALayer`s)
   places each layer at `placement_pt + rect_pt` and plays idle loops as repeating `CAAnimation`s about the named pivots
   (sway/breathe on `feet`, head nods on `neck`), blinks by swapping the `eyes` group's layers on a pseudo-random schedule baked
   into one long repeating keyframe animation, mouth swaps likewise. Zero main-thread work at rest. Loop periods and motions:
   PENDING-motion-audio (clips-needed #11; motion §5.5: workers sway continuously, the scientist ≈ 3 s cycle). The proof: the
   rig's default layers recompose `full` within ≤ 1/255 mean (the art lane's proof method, PIPE §3.1).
3. **LEVEL** caption + `LevelPlate` (green normal, red Hard, purple Super Hard) + the **Play** button (`homePlayButton`,
   Hard: red + "Hard Level" ribbon; Super Hard: purple + "Super Hard" ribbon) — VERIFIED flows "Hard / Super Hard".
   Play is static (no pulse, VERIFIED motion §5.5).
4. **Top bar:** avatar tile (→ Profile), coin pill with green + (→ Shop tab), lives pill ("5 Full" / count + mm:ss / ∞ + time),
   settings gear (→ Settings popup).
5. **Claw bar** (hex icon, progress `n/target`, multiplier badge x1…x100 with its chevron tray, reward icon, timer chip) and
   the **event badges column** (Streak Race, Sky Jump, Rocket Race; "Join" badges; timers) — shown per the event schedule.
6. **Bottom nav** (`NavBar`): shop basket · raised Home · trophy (a red "!" badge when the leaderboard has news, VERIFIED L61).
7. **Payout** (`PayoutSequence` + `FX/CoinFly`, S3): "+N" over the LEVEL plate at +0.25 s, 5 coins fly to the coin pill
   (+0.80 → +1.36 s), each arrival adds N/5 and sparkles the pill (VERIFIED vflows §6); the coin collect cue (§7.2).
Home auto-sequences after a win (event claims, Sky Jump progress, Rocket Race offer, rating prompt) are GAME's `EventsDirector`
queue (§8.4), presented through the popup host.

### 6.5 Level screen and HUD (S2)
Layer stack (GAME owns `GameScreen.swift`):
| z | layer |
|---|---|
| 0 | `BoardHost` (edge to edge; opaque white board) |
| 1 | `HUDView` (coin pill, back, panel + level tab + timer pill + hearts, pause; the two booster corners) |
| 2 | `TutorialLayer` (the "Tap to move!" caption and our hand, anchored to `board.screenPoint(of:)`) |
| 3 | `FXOverlay` (celebration: logo, confetti, fireworks; CA layers, D13) |
| 4 | `PopupHost` (dims + panels + the unlock overlay) |
| 5 | toasts; debug overlay (`-pc.hud debug`), probe element (`-pc.uitest 1`) |

- **HUDModel** (◆ `PresentationContract.swift`, written ONLY by GAME's `HUDWriter`; HUD views never touch the session):
  `levelLabel` ("Level 32" / "Levels 1-4"), `tag`, `timerText`, `timerFrozen`, `hearts: [HeartSlotVM]` (`.full/.lost/.empty`),
  `coins`, `boosters: [BoosterSlotVM]` (`.stock(n)`, `.empty`, `.locked`, `.active`), `introPhase`.
- **Sync ≤ 10 Hz** (GP §8.1): the timer text is written only when the displayed second changes; hearts, boosters and coins are
  written on their events. The tap frame writes nothing to SwiftUI (§8.2) so the exit's first frame has no SwiftUI layout cost.
- **Tag colours:** the level tab, back and pause buttons are blue / red / purple for normal / Hard / Super Hard; the timer pill
  stays blue (VERIFIED flows, uim `hud`).
- **HUD intro** (`HUDIntro`): the top row drops with `Curves.hudDrop` (spring response 0.429 s, damping 0.47), the boosters
  slide in from the sides (0.245 s, 0.43), the big "3:00" pops 3.5× → 1 with an undershoot, the hearts pop 1.58× → 1 staggered
  ≈ 0.10–0.12 s (VERIFIED motion §5.1). Driven by `TimelineView` + `Curves` (pure functions of t, freezable via `MotionClock`).
- The hearts dim one by one from the right on a bump contact (≈ 0.07–0.10 s cross-fade, no pop, VERIFIED motion §3).

### 6.6 Popup host and the popup list (S1 host; S2/S3/SOC2 popups)
```swift
@MainActor @Observable final class PopupHost {
    private(set) var stack: [PresentedPopup] = []
    func present<R>(_ popup: Popup<R>) async -> R      // pushes, awaits the answer, pops; stackable
    func dismissAll()
}
struct PopupStyle {
    var dim: DimToken                 // dim.popup 0.90 · dim.unlock 0.90 · dim.outOfTime 0.94 · dim.skyMatch 0.96 (VERIFIED uim)
    var dimFadeIn: Double = 0.0       // 0–0.1 s (VERIFIED motion §5.3)
    var entrance: Entrance = .instant // .instant | .staggered(UnlockBeats) (unlock overlay)
    var closesOnTapAnywhere = false   // unlock overlay, claim screens, "Tap to Continue" pages
    var holdsLevelTimer = true        // GAME adds HoldReason.popup while any popup is up in a level
    var inputLock = false             // forced tutorials (Weekly Contest arrow at the trophy tab)
}
```
Popups (one file each; ids are `PopupID` cases; copy and layout from SPEC-ui):
| group | popups | owner |
|---|---|---|
| level | `pause` (Sound, Haptic toggles, Resume, Quit, X), `quitLevel` ("Quit Level?" / "You will lose a life!" / Quit / X) | S1 |
| meta | `settings` (Sound, Music, Haptic, Notifications; Support/Terms/Privacy as honest offline states, PENDING-ui) | S1 |
| fail | `outOfTime` (+30 sec, Add Time 900), `continue` (variants: streak / token / life / hearts-out), `levelFailed` (Try Again) + `StreakBanner` | S2 |
| win | `winPanel` (normal / Hard / Super Hard; Rewards; Continue; X) + `StreakBanner` or `RaceBar` (Rocket Race joined) | S2 |
| first times | `unlockOverlay` (title, "Unlocked!", icon, card; staggered pops, tap anywhere, sparkles), `claimReward` ("Congratulations!" … "Tap to Claim") | S2 |
| meta | `username` ("Create your username:"), `editProfile` (3 × 3 avatars + Save), `noLives`, `boosterBuy` | S3 |
| social | `weeklyContestTutorial` (the arrow pointing at the trophy tab, input locked), `weeklyContestIntro`, `clawInfo`, `skyJumpJoin/Offer/Matching/Tutorial/Progress/Win`, `rocketRaceOffer/Tutorial/Result`, `streakRaceBoard` | SOC2 |
Each popup's result is a small enum (`.primary | .close | .secondary`), so the flows read as straight-line async code (§8.4).
`ToastCenter.show(_ text: LocalizedStringResource)`: one at a time, newest replaces.

### 6.7 Win and fail presentation (S2)
- **Celebration** (`FX/WinLogoSequence` + `Confetti` + `Fireworks`, CA layers): after the board's clear wave, the blue sign
  swoops in with "ARROW" (ours; the plate widened for the longer word), the purple arrow sign swings in, the white 3-D "OUT!"
  balloons and slams, the dim reaches ≈ 90 % in 0.36 s, confetti rains, two rockets rise and burst; the panel at **+3.36 s**; a
  tap anywhere skips to the panel (VERIFIED motion §5.6, vflows §4; our logo art `logoArrowOut`). Silent (VERIFIED sounds §1).
- **Win panel:** instant; the Rewards coin pile + amount; Continue; X; under it the Streak Race banner (chips x1…x100 with the
  current one lit, timer) or the Rocket Race bar (5 tiles, ranks, n/5) (VERIFIED flows, levels L55). The coins are NOT counted
  up on the panel (VERIFIED tutorials §4).
- **Fail chain:** the popups of §4.5 in order, each instant, the offer's coin pill with its + at the top right.

### 6.8 Shop (S3)
- `StoreService` (StoreKit 2, only when `Product.products` returns the catalogue, i.e. the scheme's Run action with
  `ArrowOut.storekit`): `.success(.verified)` → grant + record the transaction id + finish; `.unverified` → nothing;
  `.userCancelled` RETURNS (memory revenuecat-cancel-does-not-throw); `.pending` → toast; listens to `Transaction.updates`.
- `FakeStore` everywhere else (tests, captures, the phone install): the same interface, static products with the catalogue's
  prices, purchase succeeds after 0.3 s, and the shop shows **"Test store: nothing is charged"**. The shop is never empty and no
  real purchase path is reachable (GP §6.3).
- Catalogue and layout: PENDING-ui/gameplay (v552's shop is not captured yet; the V2 shop in vflows §8 is an older skin).

### 6.9 Settings, Profile, Leaderboards, event screens (S1, S3, SOC2)
- **Settings** (S1): toggles write `PlayerState.settings` (never UserDefaults); Sound → SFX bus, Music → music bus, Haptic →
  `Haptics.enabled`, Notifications → local-notification scheduling (none planned unless SPEC-gameplay adds one).
- **Profile** (S3): avatar (9 of ours + the default silhouette), username (`player_` + 7 chars by default, editable), the
  "Level" pennant, General Stats "First Try Wins" and "Weekly Contest Wins" (VERIFIED vflows §9.2). The username popup appears
  when Profile opens without a name (not forced).
- **Leaderboards** (SOC2, the trophy tab): tabs Weekly | World | the player's country name (from `Locale.current.region`,
  localised); before L50 the Weekly tab shows "Reach level 50 to compete in Weekly Contest!"; after the L50 tutorial the Weekly
  podium (2000/1000/500) + list; World from the top; Country opens scrolled to the player's green row with a "Top" button
  (VERIFIED vflows §9.1, flows). Rows come from `SocialWorld.page(…)` computed off the main thread for > 50 rows.
- **Event screens** (SOC2): Claw Challenge (ladder auto-scroll on first open, (i) overlay), Streak Race board, Rocket Race lanes
  and results, Sky Jump join/matching ("Finding players on your level." 29/100 → 100/100)/tutorial/map/win (VERIFIED flows).

### 6.10 Rating and notification prompts (G2 drives, S3/S1 host)
- **Rating:** once per install, on home right after the **L34** win (VERIFIED phone + V2), `AppStore.requestReview(in:
  windowScene)` (D24). Suppressed under `-pc.uitest`/`-pc.capture` unless `-pc.rating 1`; `PlayerState.flags.ratingPromptShown`.
- **Notifications:** the original asks over the Loading screen on the first launch (VERIFIED F00, V2). We do the same
  (`UNUserNotificationCenter.requestAuthorization`), once; suppressed under `-pc.uitest`/`-pc.capture` unless `-pc.notif 1`.

### 6.11 Components, text, fonts, UI art, strings, Brand (S1)
- **GlossyChrome** (`art/ui/code/GlossyChrome.swift`, UI-ART, compiled in, D15): `Superellipse`, `GlossyHeartShape`,
  `Color(hex:_:)`, `BlueSquareButton`, `PauseGlyph`, `HeartHUD`, `PanelButton`, `OutlinedLabel` today, plus the manifest's
  planned symbols (`CoinPill`, `HudPanel`, `LevelTab`, `TimerPill`, `PanelFrame`, `TitlePlate`, `CreamCard`, `CloseButton`,
  `PillToggle`, `StreakChips`, `UnlockCard`, `BoosterButton`, `CountBadge`, `LevelPlate`, `NavBar`, `EventProgressBar`,
  `RankRow`, `SegmentTabs`, `RaceLane`, `RaceBar`, …; ID-MAP). **These names are reserved:** SHELL never redefines them.
- **GameText** (`Shell/Components/GameText.swift`, S1): the one outlined casual-game text: CoreText glyph paths of
  `PCDisplay-Black` (or `-BlackItalic` for event logos), a vertical-gradient face, an outline drawn OUTSIDE the glyph with round
  joins, a solid unblurred drop in the outline colour (VERIFIED fonts §6), size/tracking per `tokens.textStyles`; paths cached
  per (string, style); takes `LocalizedStringResource`, never `String`. It compiles for iOS 18 **and macOS 14** so UI-ART's
  renderer compiles it next to GlossyChrome; UI-ART then routes `OutlinedLabel`'s look through it (a request, §12.2 UI-ART).
- **Fonts:** `Fonts/PCDisplay-Black.ttf` + `PCDisplay-BlackItalic.ttf` (Nunito wght 1000, OFL, renamed; VERIFIED fonts);
  `FontCoverageTests` renders "ıİşŞğĞüÜöÖçÇ" without fallback.
- **UIArt** (`Shell/Components/UIArt.swift`, generated by `tools/uiart_gen.py` from `art/MANIFEST.json`): one case per shipped
  raster id; `UIArt.image(_:)` loads `bundle/UI/<id>@3x.png` or `bundle/Art/…`, decoded with ImageIO at the needed pixel size
  and cached. A missing file shows a hatched placeholder in **Debug only**; `UIArtBundleTests` (V1) requires 0 missing in the
  bundle (never ship stand-in content).
- **Tokens / ShellLayout:** `Tokens` loads `design/ui-tokens.json`'s numbers compiled into `Tuning/ui.json` (SHELL copies the
  values it uses; the app never reads `design/`); `ShellLayout` maps the 393 × 852 canvas to the device (§6.12).
- **Strings:** English literals in code (`Text("Paused")`), TR from the TSVs (§3.3); positional `%1$@` when TR reorders
  arguments; `StringsCoverageTests` scans `App/**/*.swift` + `art/ui/code/*.swift`.
- **Brand:** `enum Brand { static let name: String /* Info.plist PCBrandName */ }`; the logo is art (`logoArrowOut`). Copy that
  names the game interpolates `Brand.name`. `BrandTests` (V1) greps the built app: "Arrow Out" only via Brand/Info.plist/string
  interpolation; "Maze", "MazeOut", "Arrow Jam", "Grand Games", "grandgames", "arrowjam" appear nowhere (file names included).

### 6.12 Layout adaptation (S1)
Frames are measured on 393 × 852 with the iPhone 15 safe area (top 59, bottom 34; VERIFIED uim). The anchoring rule is
INFERRED per component from `uim` "anchor" (top: offset from the top safe inset; bottom: from the bottom inset); x scales with
`W/393`. `ShellLayout` implements it and publishes the play rect (HUD bottom … booster top) to `BoardLayout.fit` so the board
and the HUD agree on every device. iPhone only; iPad is out of scope (PLAN PRECEDENCE).

---

## 7 Audio and haptics

AUDIO owns `App/Audio/**`, `Resources/Sounds|Music`, `Tuning/audio.json`, `tools/audio/**`. The engine is MF's (REUSE §3.4:
`AudioCore`, `AudioGraph`, `MusicPlayer`, `SoundBank`, `AudioRamps` adapted), the cue list is ours.

### 7.1 Engine (A2)
```
AVAudioSession  .ambient (mixes with other audio, obeys the silent switch; DECISION), preferredIOBufferDuration 0.005 s,
                activated at boot BEFORE the Loading screen's warm-up finishes
AVAudioEngine   started at boot and NEVER stopped during play (a stopped engine costs 50–150 ms to restart)
 ├─ sfxBus   (AVAudioMixerNode) ── mainMixer     8 voices: AVAudioPlayerNode → AVAudioUnitVarispeed → sfxBus,
 │                                               all attached, connected and play()-ed at boot (idle nodes, zero latency to schedule)
 └─ musicBus (AVAudioMixerNode) ── mainMixer     2 decks, 0.3 s crossfade, looping buffers (only if SPEC-motion-audio finds music)
```
- Every `Sounds/<id>.wav` (mono, 44.1 kHz, 16-bit) is decoded at boot into Float32 buffers (a few hundred KB total).
- `play(id)` = `voice.scheduleBuffer(buffer, at: nil)` on the next free voice (round robin, oldest stolen): no allocation,
  no file I/O, no engine start on the call path. Callers fire it **on the frame of the visual event** (§8.2).
- Latency is logged at boot: `[PC][audio] latency io <ms> out <ms>` (`ioBufferDuration` + `outputLatency`); §10 budget.
- Settings: Sound off → `sfxBus.outputVolume = 0`; Music off → `musicBus.outputVolume = 0` and the decks stop. Applied at boot
  from `PlayerState.settings`.
- Robustness: on `AVAudioSession.interruptionNotification` and `.AVAudioEngineConfigurationChange` restart the engine, re-play
  the idle voices, resume music.

### 7.2 Cue list (PENDING-motion-audio) and the silent-play question
VERIFIED sounds §1: v552's look (YT-A) is a **near-silent game in play** — no sound on taps, exits, bumps, obstacles, the
intro, the timer or the win celebration. Only three cues exist: the **UI click** (every UI button on release, and the tap that
skips the celebration), the **coin collect** (the home payout; clinks when the coins land), the **unlock chime** (with every
unlock overlay). Music: none heard (clips-needed #4 decides).

Default map (DECISION from sounds §5; the table lives in `Tuning/audio.json` so SPEC-motion-audio replaces it as data):
| event | cue | bus |
|---|---|---|
| any UI button released; celebration skip | `uiClick` (380 → 300 Hz glide + a 3 ms noise burst, 30 ms, −6 dBFS) | sfx |
| home payout coin fly | `coinCollect` (glitter swell + one clink per landing coin, 2.9 s) | sfx |
| unlock overlay appears | `unlockChime` (C2 thump + Cmaj7 FM bell, 2.2 s) | sfx |
| arrow tap (exit/bump), exit, bump, obstacles, win | — (silent, VERIFIED) | — |

**Open question for the orchestrator/owner:** OWNER 03:00 asks that "the tap sound + tap ripple + haptic land on the SAME frame
as the motion start", but the original has no tap sound (VERIFIED on ≈ 1630 taps). The architecture supports both: a
`tapTick` `SoundID` exists in the contract and the same-frame pipeline schedules it when `audio.json` maps it; whether it is
mapped (a deviation from 1:1, by the owner's feel wish) is decided in SPEC-motion-audio / by the orchestrator. The haptic and
the ripple land on the motion frame either way.

### 7.3 Haptics (A2; the map is data, every row a DECISION — video cannot record vibration)
`Haptics` (`@MainActor`) keeps one prepared generator per style, re-`prepare()`s after each fire and at level start (the Taptic
Engine idles after a few seconds), and is gated by `PlayerState.settings.haptic` (the Pause and Settings toggles, VERIFIED).
| event | generator (default; `audio.json haptics`) | frame |
|---|---|---|
| arrow tap accepted (exit or bump) | `UIImpactFeedbackGenerator(.light)`, intensity 0.7 | the release frame (= the first motion frame) |
| bump contact | `.rigid`, 1.0 (also stands for the heart loss: one impulse, not two within 0.1 s) | the contact frame |
| out of hearts / out of time | `UINotificationFeedbackGenerator.warning` | the offer popup's frame |
| board cleared (clear wave start) | `.medium`, 0.8 | wave start |
| win (OUT! slam) | `UINotificationFeedbackGenerator.success` | the slam keyframe |
| door burst, pipe/box break | `.soft`, 0.6 | the burst frame |
| UI buttons | none (DECISION; the original's taps on UI have only the click) | — |
OWNER 03:00 names "light tap, rigid/heavy bump, heart loss, win": the table covers them; intensities are PENDING-motion-audio.

### 7.4 Audio contract (`App/Contracts/AudioContract.swift` ◆)
```swift
enum AudioBus { case sfx, music }
enum SoundID: String, CaseIterable { case uiClick, coinCollect, unlockChime, tapTick
    var bus: AudioBus { return .sfx } }                               // tools/audio/specs.py parses these enums
enum MusicID: String, CaseIterable { case home, level
    var bus: AudioBus { return .music } }
@MainActor protocol AudioPlaying: AnyObject {
    func warmUp() async                                                // session, engine, decode, idle voices
    func play(_ s: SoundID, gain: Float)
    func playMusic(_ m: MusicID, fade: Double); func stopMusic(fade: Double)
    func apply(settings: PlayerState.Settings)
    var outputLatency: TimeInterval { get }                            // io buffer + route latency (probe, §10)
}
enum Haptic { case tap, bumpContact, fail, clear, win, burst }
@MainActor protocol HapticPlaying: AnyObject { func prepare(); func play(_ h: Haptic); var enabled: Bool { get set } }
```
The `SoundID`/`MusicID` case lists are written in WP0 from SPEC-motion-audio's cue list (the cases above are the default set:
sounds §5 + the `tapTick` slot). A1 renders exactly these files; `tools/audio/check.py` fails on a missing or extra file.

---

## 8 Game glue

GAME owns `App/Game/**` (and `AppModel.swift`, `PlayerStore.swift` from G1).

### 8.1 `GameController` (G1)
One per session (a Play). It owns the `LevelSession`, writes `HUDModel` through `HUDWriter`, runs the directors, and is the
board's delegate.

**Event fan-out order** for every batch the session returns (all on the main thread, in the same run-loop turn):
1. `board.present(events)` (layers + animations, one transaction)
2. `haptics` (§7.3 map)
3. `audio` (§7.2 map)
4. `hud.apply(events)` (HUDWriter; throttled fields only when they change)
5. `fx` (shell overlays)
6. the directors (tutorial, fail flow, win, events), which may call back into the session; the events those calls return are
   fanned out the same way.
Steps 1–3 happen before the run loop's Core Animation commit, so the board frame, the haptic and the scheduled sound share the
first presented frame (D8). HUD writes that could trigger SwiftUI layout are deferred to the next display-link tick when they
are not needed on the tap frame (nothing on a normal exit changes the HUD).

Board callbacks → session:
| board callback | session call |
|---|---|
| `boardReleased(arrow?, point, touchTimestamp)` | `session.tap(arrow, at: now)` (+ the latency probe) |
| `boardBeat(.bumpContact(a))` / `.bumpFinished(a)` | `session.ack(.bumpContact(a))` / `.bumpFinished(a)` |
| `boardBeat(.doorBurst(d))` | `session.ack(.doorBurst(d))` |
| `boardBeat(.lastExitLeftBoard)` | `session.ack(.lastExitLeftBoard)` → the win or stage-transition presentation |
| `boardBeat(.introFinished)` / `.stageTransitionDone` | `session.ack(…)` |
| `boardFrame(timestamp, target)` | `session.tick(dt)` + the HUD throttle + the perf monitor |

### 8.2 A tap, end to end (the same-frame pipeline; G1 + B1)
```
finger lifts ─▶ UIKit touchesEnded (event dispatch) ─▶ ReleaseTapRecognizer .ended ─▶ BoardEngine.hitTest (µs)
  ─▶ delegate.boardReleased(arrow 13, point, touchTimestamp)            LatencyProbe.mark(.handler)
       GameController: events = session.tap(13, at: now)                 ~50 µs: [.timerStarted?, .exited(plan)]
         1 board.present   → ripple (pooled) + exit mover + dots + stars, ONE CATransaction (P1)
         2 haptics.play(.tap)                                             (prepared generator)
         3 audio.play(.tapTick) if mapped                                 (idle voice, scheduleBuffer at: nil)
         4 hud.apply       → .timerStarted only flips `timerFrozen` (first tap): written on the next tick
  ─▶ end of the run-loop turn: CA commit                                   LatencyProbe.mark(.commit)
  ─▶ next vsync: the render server shows ripple + the first exit frame     LatencyProbe (next display link targetTimestamp)
```
Budget (§10): `touchTimestamp → handler` ≤ 4 ms, handler → commit ≤ 4 ms (5 rainbow exits in flight, densest board, device),
first motion on the next vsync. The original shows the ripple and the first arrow change on the same frame (VERIFIED motion
§2.1); ours must too.

### 8.3 A bump, end to end
`session.tap` → `.bumped(plan)` → the board's bump mover + ripple + `.tap` haptic on the release frame → at the contact
keyframe the board reports `.bumpContact` → `session.ack(.bumpContact)` → `[.heartLost(2), .arrowMarked(a)]` (+ `.offer(
outOfHearts)` at 0) → the HUD heart dims, the `.bumpContact` haptic fires, the vignette is already running (board) — all on the
contact frame. The timer never pauses for a bump (VERIFIED).

### 8.4 Directors
- **`LevelFlow`** (G1): the start sequence (§8.5), stage transitions (`.stageCleared` → wait `lastExitLeftBoard` →
  `board.playStageTransition` → `ack(.stageTransitionDone)`), background/foreground (§8.6).
- **`FailFlowDirector`** (G1, async): on `.offer(o)`: hold the timer, present the offer popup for `o` (with its warning variant);
  "Play On"/"Add Time" → `Economy.spend(price)` (too few coins → the Shop over the popup, re-check on close, DECISION) →
  `session.acceptContinue()`; X → `session.declineContinue()` → the next offer or `.lost` → `Economy.finishAttempt(.lost)`
  (the life, the streak) → `levelFailed` (Try Again | X). Quit from Pause/back → `quitLevel` confirm → `.lost(.quit)`.
- **`WinDirector`** (G1): on `.won`: lock input, **bank at once** (`Economy.finishAttempt(.won)` + the event hooks + an
  immediate save — kill-safe, DECISION), wait `lastExitLeftBoard` → `board.playClearWave()` → the celebration (skippable) →
  the win panel (+ banner/race bar) → Continue → the FTUE chain's next level or home `.afterWin`.
- **`AutoPlayer`** (G1, `-pc.autoplay 1`): every `autoplayRate` s (default 0.45) picks the first unit of `session.hint()` (the
  solver order; `-pc.autoplayMistakes p` taps a blocked arrow with probability p), taps it through `board.tapPoint(of:)` →
  `boardReleased` (the real pipeline), dismisses tutorials/unlocks/panels, and stops at `-pc.autoplayStop N`; logs
  `[PC][autoplay] done: …`.
- **`TutorialDirector`** (G2): plays `tutorials.json` steps: trigger (`stageReady(level, stage)`, …), caption + hand anchored
  to `board.screenPoint(of:)`, dismiss (`anyTap`: caption scale-out 0.16 s, hand fade 0.12 s), `holdTimer` (false for "Tap to
  move!", VERIFIED tutorials §3/§8); marks `tutorialsDone`.
- **`FTUEDirector`** (G2): the first-launch chain (§6.2), the notification prompt over Loading, the first-home payout.
- **`UnlockDirector`** (G2): on Play of a level whose `unlock` feature is not in `unlocksSeen`: open the level under the unlock
  overlay (staggered pops, the chime), tap anywhere → the board (timer still frozen). VERIFIED tutorials §6.
- **`BoosterDirector`** (G2): a booster tap: stock > 0 → `Economy.useBooster` + `session.useBooster`; stock 0 → the buy popup
  (PENDING-gameplay/ui); the timer holds while it is up.
- **`EventsDirector`** (G2): after every finished attempt, applies the C3 event hooks and queues the post-level screens in the
  original's order (VERIFIED flows: win panel with banner → Claw first-open screen/claims → Sky Jump progress → home; Rocket
  Race offer on home; the Streak Race board auto-opening on an idle home), each through the popup host; the exact queue rules
  are PENDING-gameplay/social.
- **`RatingDirector`** (G2): §6.10. **`NotificationPrompt`** (G2): §6.10.

### 8.5 Boot and level start sequences
**Boot** (`AppModel.boot()`, behind the Loading screen, log marks per step):
1. `PlayerStore` load (+ `Economy.reconcileOnLaunch`: a killed attempt → loss per the rules).
2. `LevelLibrary.load`, `SocialWorld` init, tuning files.
3. In parallel: `audio.warmUp()`, `haptics.prepare()`, `board.prepare()` (§5.9), fonts + `GameText` glyph caches for the HUD
   strings, decode the first screen's UI art (home or the FTUE board), pre-render each popup type once off-screen at alpha 0
   inside the window (SwiftUI first-presentation cost), `LevelProvider` warms the next level.
4. The notification prompt (first launch only).
5. `[PC][launch] <screen> fully visible` → cross-fade.

**Level start** (Play tapped):
1. `Economy.startAttempt` (lives gate) → `LevelSession.start()` → `board.load(stage)` (≤ 5 ms) — no await, no spinner: the
   original hard-cuts (VERIFIED).
2. [unlock overlay first time] → `board.playIntro` + the HUD intro → `ack(.introFinished)` → `.ready` (timer frozen).
3. [tutorial caption] → the first tap starts the timer.

### 8.6 App lifecycle
- Background during play: `hold(.background)` and the Pause popup on return (DECISION); an immediate save.
- Killed mid-level: at the next launch `reconcileOnLaunch` applies the kill rule (default: a loss, PENDING-gameplay) and lands
  on home.
- Every `PlayerState` mutation goes through `PlayerStore.mutate` (§4.12); nothing writes UserDefaults.

---

## 9 Test hooks

### 9.1 Launch arguments (`App/Support/LaunchArgs.swift` ◆)
Read once from the `UserDefaults` argument domain as `-pc.<name> <value>` (never persisted; negative numbers are values —
Arrows' `value(after:)` rule). They exist in every configuration (D21). Always launch with `--terminate-running-process`
(simctl drops arguments for a running app, GP §13).
| argument | effect |
|---|---|
| `-pc.reset 1` | fresh install: wipe `PlayerState` (+ backup) before boot |
| `-pc.state <path \| base64>` | load this `PlayerState` JSON |
| `-pc.level N` | next level = N (marks home seen when N ≥ 7) |
| `-pc.stage K` | start a multi-board session at stage K (e.g. Levels 1-4 stage 3) |
| `-pc.go home \| level \| shop \| leaderboard[:weekly\|world\|country] \| profile \| settings \| event:<claw\|streakRace\|rocketRace\|skyJump> \| boardlab \| shelllab \| soundboard \| sociallab` | open that screen after boot (`level` skips unlock overlays unless `-pc.unlocks force`) |
| `-pc.popup <id>[:variant]` | present one popup over the target screen: `pause`, `quitLevel`, `settings`, `outOfTime`, `continue:streak\|token\|life\|hearts`, `levelFailed`, `win:normal\|hard\|superHard`, `unlock:<feature>`, `claim:<grant>`, `username`, `editProfile`, `noLives`, `boosterBuy:<id>`, `weeklyTutorial`, `weeklyIntro`, `clawInfo`, `skyJump:<page>`, `rocketRace:<page>`, `streakRace` |
| `-pc.seed N` | fixed install seed (social world, combo/hint tie-breaks, fx) |
| `-pc.coins N`, `-pc.lives N`, `-pc.livesNextIn S`, `-pc.unlimitedLives S`, `-pc.boosters freeze=3,hint=0` | economy state |
| `-pc.tutorials skip \| force`, `-pc.unlocks skip \| force` | mark all done / not done |
| `-pc.now <ISO-8601>`, `-pc.clockOffset ±S`, `-pc.clockRate K` | wall-clock override for lives, events and the social world; `clockRate` runs the social/event clock K× faster (SocialLab, event tests) |
| `-pc.timer S`, `-pc.freezeTimer 1`, `-pc.timerRuns 1` | remaining seconds at the first tap; keep the timer frozen; let it run in capture mode |
| `-pc.hearts N` | hearts at stage start |
| `-pc.win normal\|hard\|superHard`, `-pc.lose timeUp\|hearts\|quit` | jump to that outcome's flow |
| `-pc.autoplay 1`, `-pc.autoplayRate S`, `-pc.autoplayStop N`, `-pc.autoplayMistakes p` | bot play through the real board (§8.4) |
| `-pc.trail solid\|rainbow\|ladder`, `-pc.zoom Z`, `-pc.tune file.key=v,…` | engine switches |
| `-pc.lab <scenario>`, `-pc.labBoard <id>` | BoardLab / ShellLab / SocialLab page (§9.5) |
| `-pc.slowmo N`, `-pc.freezeAt <sequence>@<t>` | slow motion; freeze a sequence at t (§5.12) |
| `-pc.capture 1`, `-pc.probeFile 1` | capture mode (§9.2); also write the probe to `Documents/probe.json` |
| `-pc.uitest 1` | exposes `board.probe`; hints/auto-popups/rating/notification prompts off unless forced |
| `-pc.hud debug` | the fps/latency overlay (§9.6) |
| `-pc.bench 1` | write `Documents/bench-L<n>-<ts>.json` at each level end |
| `-pc.fakeStore 1` | force FakeStore (it is already the fallback whenever StoreKit returns no products) |
| `-pc.rating 1`, `-pc.notif 1` | allow the system prompts under uitest/capture |
| `-AppleLanguages "(tr)" -AppleLocale tr_TR` | Turkish; set BOTH (the simulators inherit the Mac's en_TR region) |

### 9.2 Capture mode (`-pc.capture 1`)
- Seed 1 unless `-pc.seed`; clock fixed at `2026-09-25T12:00:00Z` unless `-pc.now` (lives, events, the social world);
  audio muted; no random pitch; hints, auto-popups, rating and notification prompts off; the debug overlay hidden.
- The level timer is held unless `-pc.timerRuns 1`.
- **Ready file:** when the screen is ready the app writes `Documents/capture-ready.json` =
  `{"screen":"<Screen or popup id>","t":<uptime>,"lang":"en","frozen":<bool>}` and exposes the `capture.ready` element. Ready
  means: fonts registered, the screen's UI art decoded, the board `isSettled` (in a level), the requested `freezeAt` reached,
  and 2 frames presented since. Captures wait for this file, never a fixed sleep (`tools/capture-shot.sh`, `capture.py`,
  GP §8.3), then convert to sRGB and reject flat frames (> 0.97 one tone); every frame is LOOKED at.

### 9.3 Log contract (`App/Support/Log.swift` ◆; parsed by `tools/bench/bench.py` and `capture.py`)
Every line: `"<systemUptime> [PC][<category>] <message>"`, errors `"[PC][<category>][ERROR] <message>"`, to stdout (captured by
`tools/run.sh`) and os.Logger (`com.manycode.arrowout`). The bench `MARKS` (REUSE §5.4 proposal, **confirmed**) are printed
exactly:
| key | category | message | printed by |
|---|---|---|---|
| first_screen | `launch` | `<screen> fully visible` | SHELL (Router) |
| launch_done | `launch` | `cold launch summary …` (boot step times) | LEAD/GAME (AppModel) |
| level_go | `router` | `go level(L<n>)` | SHELL (Router) |
| level_visible | `router` | `level(L<n>) visible` | SHELL |
| board_ready | `board` | `ready L<n>: <k> arrows` | BOARD |
| play | `game` | `play L<n>` (the first tap: the timer starts) | GAME |
| won | `win` | `L<n> won: <s> s left, <h> hearts` | GAME |
| lost | `fail` | `L<n> lost: timeUp\|hearts\|quit\|killed` | GAME |
| teardown | `game` | `teardown L<n>` | GAME |
| home_visible | `router` | `home visible` | SHELL |
| hitch | `board` | `hitch <ms> ms <context>` (any frame > 20 ms in play) | BOARD (PerfMonitor) |
| autoplay_done | `autoplay` | `done: L<a>-L<b> won <w>/<n> bumps <b>` | GAME |
Additional marks (same grammar; bench.py gains them in V3): `[PC][perf] tap L<n> a<id> touch→handler <ms> handler→commit <ms>
commit→vsync <ms>` (every tap under `-pc.hud debug`/`-pc.bench`), `[PC][warmup] <part> <s> s`, `[PC][audio] latency io <ms>
out <ms>`, `[PC][tutorial] show <id>`, `[PC][unlock] show <feature>`, `[PC][event] <id> <outcome>`, `[PC][capture] ready
<screen>`, `[PC][lab] <scenario> done`.

### 9.4 Board probe (`-pc.uitest 1`; B1)
An invisible element with identifier `board.probe` whose `accessibilityValue` is compact JSON, refreshed at ≤ 4 Hz from a
display-link tick (P8); `-pc.probeFile 1` also writes `Documents/probe.json`:
```json
{"lvl":32,"stage":0,"stages":1,"phase":"playing","t":178.0,"timerStarted":true,"hearts":3,"zoom":1.0,"pitch":17.87,
 "settled":true,"moving":0,"combo":0,"fps":60,
 "arrows":[{"id":13,"x":133.2,"y":443.4,"free":true,"unit":[13],"red":false}],
 "hidden":[21,22],"obstacles":[{"id":"p0","k":"pipe","n":2},{"id":"d0","k":"door","state":"locked"}]}
```
`x, y` = `board.tapPoint(of:)` in screen pt (visible, not under the HUD or boosters); `free` from the session's rules.
XCUITest taps `app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(dx: x, dy: y))` (the spike's proven method).

### 9.5 Lab screens (each writes `Documents/lab-ready.json` + its perf/snapshot JSON)
| lab | argument | owner | what it proves |
|---|---|---|---|
| **BoardLab** | `-pc.go boardlab -pc.lab <scenario>` | B1/B2 | every board scenario of §5.12 on the real engine, with `lab-perf.json` = `{frames, over20, max_ms, p95_ms, p99_ms, footprint_mb, layers, movers_peak, tap_handler_ms_p99, touch_to_commit_ms_p99, commit_to_vsync_ms_p50}` |
| **ShellLab** | `-pc.go shelllab -pc.lab <page>` | S1 (+ S2/S3 pages) | every screen and popup state with fixed data (EN/TR), the HUD states (normal/Hard/Super Hard, hearts 3/2/1, frozen), the win panels, the unlock overlays, GameText samples, puppets |
| **SoundBoard** | `-pc.go soundboard` | A3 | every `SoundID`/`MusicID` and every `Haptic`; a latency button that logs handler → schedule; the interruption test hook |
| **SocialLab** | `-pc.go sociallab [-pc.now …] [-pc.clockRate K]` | SOC2 | the world at a chosen time: boards, races, Sky Jump fields, name samples; scrubbing time; writes `social-snapshot.json` |

### 9.6 Debug overlay (`-pc.hud debug`; B1)
Drawn at (0, 95)–(260, 155) pt (bench.py `HUD_CROP`, confirmed), three lines of monospaced digits:
`"<fps> fps p95 <ms> p99 <ms> ms"` (last 600 frames), `"<MB> MB <n> layers <n> movers"` (phys_footprint, live layers,
arrows in motion), `"tap <ms>/<ms> vsync <ms>"` (last tap: touch→handler / handler→commit, commit→vsync). Hidden in captures.

### 9.7 XCUITest strategy (V1 owns the suites; owners own their lab tests)
- Every test launches with `-pc.uitest 1 -pc.seed 1 -pc.fakeStore 1` + a state (`-pc.reset 1` or `-pc.state`) + a target
  (`-pc.go`, `-pc.popup`), terminating the app first. Tests never sleep for animations: they wait on anchored predicates
  (`label == …`, `BEGINSWITH`, never a loose `CONTAINS`) over identifiers or on probe values. On failure:
  `print(app.debugDescription)` before guessing. Containers with identifiers use `.accessibilityElement(children: .contain)`.
- Permission prompts are one-shot (memory): uninstall before re-running any test that expects the notification alert.
- Suites: `FlowTests` (fresh install → Levels 1-4 with the "Tap to move!" hint → 80 → L5 → L6 → first home 1000 → 1120 → L7
  unlock overlay), `FailFlowTests` (`-pc.timer 3`: the whole time-out chain declined → a life lost with a countdown;
  `-pc.hearts 1` + a forced bump: the hearts-out offer; Try Again = the same board), `BoosterTests`, `MetaTests` (settings
  persist across a relaunch, shop purchase via FakeStore, profile, lives refill with `-pc.now`), `SocialUITests` (tabs, the
  L50 Weekly tutorial, events via `-pc.clockRate`), `CaptureTests` (the V2 list), `BoardInputTests` (B1: real touches — fire on
  release after a 2 s hold, swipe pans without firing, pinch clamps at 0.786× and the 28.07 pt cap, head tap, a 15 pt off-stroke
  tap, the midpoint tie).

### 9.8 Accessibility identifiers (the owners add them; VERIFY relies on them)
- **Home:** `home.play` (value = level), `home.level`, `home.coins` (value), `home.coins.plus`, `home.lives` (value
  `"n|mm:ss|full|inf:mm:ss"`), `home.settings`, `home.avatar`, `home.claw` (value `"n/target xM"`), `home.event.<id>`,
  `nav.shop`, `nav.home`, `nav.leaderboard` (value `"badge"` when "!").
- **HUD:** `hud.level` (value label), `hud.timer` (value seconds), `hud.hearts` (value n), `hud.coins`, `hud.back`,
  `hud.pause`, `hud.booster.freeze|hint` (value `"stock:n|empty|locked|active"`).
- **Board:** `board` (container), `board.probe`, `tutorial.caption`, `tutorial.hand`.
- **Popups:** `popup.<id>` (a `.contain` container), `popup.<id>.close`, `.primary`, `.secondary`; `unlock.overlay`;
  `win.continue`, `win.close`, `win.reward` (value); `claim.tap`.
- **Other:** `toast` (label), `shop.product.<id>`, `shop.testStoreNote`, `settings.toggle.sound|music|haptic|notifications`
  (value on/off), `pause.toggle.sound|haptic`, `leaderboard.tab.weekly|world|country`, `leaderboard.row.<rank>`,
  `leaderboard.me`, `event.<id>.close`, `capture.ready`, `debug.hud`.

---

## 10 Performance budgets

### 10.1 The owner's acceptance (verbatim, PLAN.md OWNER 03:00; binding for §10, V3 and D1)
> - OWNER 03:00 — FEEL IS A TOP REQUIREMENT: "the flawless gaming experience … no computer lag … very well optimized … flawless perfectly,
>   and that click feeling". Acceptance (binding for SPEC-architecture §10 + V3 + D1):
>   * on the iPhone 15 (60 Hz): 0 dropped frames (> 20 ms) in a scripted soak of the densest recorded/generated boards at max zoom with 5
>     simultaneous exits + trail; no first-launch or level-start stall (warm-up behind loading); memory bounded;
>   * input: fire on RELEASE like the original; tap → first motion frame ≤ 1 frame; the original's input→motion latency measured from phone
>     clips (tap marks) and ours measured the same way on the phone: ours ≤ theirs;
>   * click feel: the tap sound + tap ripple (measured by the analyst) + haptic land on the SAME frame as the motion start; haptic map per event
>     (light tap, rigid/heavy bump, heart loss, win) behind the Haptic toggle; audio latency minimised (pre-warmed AVAudioEngine, short buffers);
>   * judged side by side: our clip vs the original's clip of the same moment.

### 10.2 Budgets (DECISION unless tagged; the verdict is taken on the iPhone 15 in D1, the simulator numbers gate the WPs)
| metric | budget | measured by (§10.3) |
|---|---|---|
| **Frames in play** (iPhone 15, 60 Hz) | **0 frames > 20 ms** through the scripted soak (§10.4); p99 ≤ 16.7 ms | in-app `PerfMonitor` + render-server hitches (xctrace) + phone recording gaps |
| Frames in the shell (home, popups, event screens, 200-row leaderboard scroll, celebration, transitions) | 0 frames > 20 ms after warm-up | same |
| Frames on the simulator (M2, loaded Mac) | ≥ 59.5 fps avg, p99 ≤ 20 ms, with an idle baseline recorded (GP §8.3) | `tools/bench.sh` |
| **Tap → first motion** | the ripple and the first exit frame are the first frame presented after the release: `touch→handler` ≤ 4 ms p99, `handler→commit` ≤ 4 ms p99 (5 rainbow exits in flight, densest board at max zoom), presented at the next vsync; on phone recordings ripple onset = first arrow change (0 frames apart) and ours ≤ the original's input→motion latency (frames from the runner's tap mark) | `LatencyProbe`, phone `rec` |
| **Feedback sync** | ripple, mover, haptic call and the sound's `scheduleBuffer` are all issued inside the release handler before the commit (Δ ≤ 1 ms between them, logged); audio route latency (`ioBufferDuration + outputLatency`) ≤ 16.7 ms target (reported honestly if the hardware route exceeds it) | log marks, `[PC][audio] latency` |
| Tap handler main-thread cost | ≤ 2 ms p99 solid, ≤ 4 ms p99 with the rainbow painter (device) | `LatencyProbe` |
| **Level start** | Play → first board frame ≤ 50 ms (hard cut); board build ≤ 5 ms main thread (spike: 1.6 ms for 304 arrows); 0 frames > 20 ms from Play to the end of the intro | log marks + PerfMonitor |
| **First launch** | the Loading screen on screen ≤ 0.5 s after launch; boot + warm-up ≤ 2.5 s on the device (≤ 4 s cap); 0 frames > 20 ms on the first board and on the FIRST exit, bump, key burst, pipe break, box break, clear wave, celebration and popup of each kind after install | log marks, PerfMonitor, `bench.sh launch` |
| **Memory** | ≤ 160 MB resident in play, ≤ 220 MB peak anywhere (full-bleed home/event art), growth ≤ 10 MB across a 30-level soak; the board alone ≤ 40 MB at 304 arrows; `SpriteCache` ≤ 48 MB | `phys_footprint` (in-app), `bench.sh soak` |
| Layers | ≤ 2 per resting arrow + 1 per departed arrow + ≤ 16 per mover; ≤ 1,500 live layers at the soak's peak | debug overlay, `lab-perf.json` |
| HUD | ≤ 10 Hz writes; ≤ 1 ms per write | os_signpost |
| Autosave | encode + write off the main thread; ≤ 1 ms main-thread cost | os_signpost |
| Social | a 50-row page ≤ 2 ms (device); pages > 50 rows off the main thread | `SocialLab` timings |
| Thermal soak | 10 min of autoplay on the phone: 0 frames > 20 ms, average ≥ 59.5 fps | `bench.sh soak` on device (D1) |
| 120 Hz | shell and board opt in (`CADisableMinimumFrameDurationOnPhone`, animation frame-rate ranges 60…120); unverified until a ProMotion device (GP §13) | — |

### 10.3 How each is measured
1. **In-app frame histogram (`PerfMonitor`, B1):** a main-thread `CADisplayLink` records every presented frame's interval
   (`timestamp` deltas; a missed vsync shows as ≥ 33 ms), keeps the last 600, and writes p50/p95/p99/max/over-20 counts to
   `lab-perf.json`, `bench-L<n>.json` and the debug overlay; any frame > 20 ms in play prints the `hitch` mark with its context
   (the last event batch). This sees main-thread stalls.
2. **Render-server hitches (device):** `xcrun xctrace record --device <UDID> --template 'Animation Hitches' --attach ArrowOut
   --time-limit 60s` around the soak; the trace's hitch count must be 0. Fallback if xctrace cannot record on this setup:
   the phone runner's 60 Hz `rec` of the soak — the recording has a variable frame rate where a timestamp gap means nothing
   changed, so **during continuous motion any inter-frame PTS gap > 20 ms is a dropped frame** (motion §0 capture note);
   chained ≤ 3 s recordings (the runner's limit).
3. **Latency (`LatencyProbe`, B1):** `touch.timestamp` (the release) → the handler's `CACurrentMediaTime()` → the commit
   (a `CATransaction` completion block + the run-loop observer before `kCFRunLoopBeforeWaiting`) → the first display link
   whose `targetTimestamp` follows the commit. Logged per tap under `-pc.hud debug`/`-pc.bench`.
4. **Phone side by side (D1b, V2):** the same recorded level (L32: same board in both apps) and the same tap sequence recorded
   on the owner's phone with the runner (`phone rec`, 60 Hz), ours and the original's: frames from the tap mark to the ripple
   and to the first arrow change, the exit colour ramp, the arc length per frame vs `ExitKinematics`, the bump beats; sheets
   side by side (`research/motion-tools` `mfx` + `tools/compare`). The original's numbers already measured: ripple and first
   motion on the same frame; black → #10A2EF in 0.08 s; T(d) table (motion §2).
5. **Memory:** `task_vm_info.phys_footprint` in-app every second into the bench JSON; `bench.sh soak` + `heapdiff` for growth.
6. **Warm-up proof:** a fresh install (`devicectl uninstall` + install) → the Loading screen → the FTUE board; the first
   occurrence of every effect is tagged in the hitch log (`first:<effect>`), and none may exceed 20 ms.

### 10.4 The scripted soak (`-pc.go boardlab -pc.lab soak`; B1/B2 build it, V3 and D1 run it)
- Boards, each at **max zoom** (28.07 pt per cell) and again at fit: the synthetic 40 × 40 heart (304 arrows, spike), L039
  (Super Hard, 102 visible arrows), L044 (Hard, pipes + tapes), L049 (door + 5 pipes), L054 (Hard, 72 arrows + a door), the
  densest generated level of `curve.json`.
- Per board, 90 s: waves of **5 simultaneous exits** every 0.7 s with the combo ladder forced to the rainbow painter + stars
  (`-pc.trail rainbow`), 2 bumps with the vignette, a key flight + door burst, a pipe break, a box break when present, a zoom
  ramp 1 → max → min → 1 over 6 s in the middle of the waves, then the clear wave.
- Then the full-game soak: `-pc.reset 1 -pc.autoplay 1 -pc.autoplayStop 30 -pc.hud debug` (fresh install → L30 through the
  real UI: FTUE, unlock overlays, celebrations, home payouts, event screens).
- Pass = §10.2's frame, latency and memory rows. The soak's `lab-perf.json` and bench JSONs are archived under
  `build/bench/` (simulator, V3) and `build/device/` (phone, D1).

---

## 11 Risks and first-day checks
B1 runs R1–R6 before building on them; the orchestrator schedules the phone for R2/R3 (D1a) as soon as B1's lab exists.
| # | risk | first-day check | fallback |
|---|---|---|---|
| R1 | `require(toFail:)` on the scroll view's pan/pinch delays the release recogniser's `.ended` past the touch-up event | BoardLab `latency`: `touch→handler` ≤ 4 ms p99 over 50 real XCUITest taps; handler inside the same event dispatch | drop `require(toFail:)`; decide in `touchesEnded` from the pan state, `isZooming`, `isDecelerating` and the slop |
| R2 | The rainbow painter's masked gradient runs cost the A16's render server more than the M2 simulator showed (2.3–6.3 ms main thread per wave, offscreen masks) | D1a: the §10.4 soak on the phone in Release, xctrace hitches + PerfMonitor | prebuild gradient runs per arrow in idle frames; cap concurrent masked movers and draw the rest with the dash-step painter (spike 3e B: no mask); report the numbers to the owner |
| R3 | First-use stalls (shader/mask/emitter compilation, glyph rasterisation, image decode, AVAudioEngine start, Taptic prepare, SwiftUI first presentation) on the first launch after install | D1a: fresh install → FTUE board → the first of each effect; the `first:<effect>` hitch tags | extend the warm-up list (§5.9 step 2, §8.5 step 3); render warm-up effects on screen under the opaque Loading view longer |
| R4 | Audio route latency on the iPhone 15 speaker exceeds one frame even with a 5 ms buffer | SoundBoard latency log + `outputLatency` on the device | none available in software beyond a pre-running engine and idle voices; report the measured value honestly (the original is silent on taps anyway, §7.2) |
| R5 | `UIScrollView` zoom re-tessellates 300 shape layers every frame of a pinch (the costliest spike run: backboardd 31–34 %) | D1a: zoom ramp on the 304-arrow board at max zoom | rasterise the rest layers during an active pinch (`shouldRasterize` only while zooming, off at rest) — measured before adoption |
| R6 | The fire-on-release recogniser, a pinch that starts on an arrow, and the pan-on-swipe interact badly on a real finger (spike: synthetic touches only) | `BoardInputTests` + D1a by hand on the phone runner (`taps`, `pinch`, `drag`) | tune `slop`, the two-finger rule and `delaysContentTouches` |
| R7 | The door/box/elevator reveals were never extracted fully (arrows under doors missing from the start JSON, PLAN TODO) | L1: every door level has its `Lnnn-openK` reveals merged and the solver says `.solved` | reconstruct from the bot's round shots (`research/bot/tmp/L0NN-*-rNN.png`); a level that cannot be completed stays out of the bundle and is replaced by a designed one (reported) |
| R8 | Pan limits and snap-back were never measured (clips-needed #13) | — | `board.json pan.*` knobs; V2 compares a pan clip when recorded |
| R9 | The social world's Swift and Python drift (floating point, integer division) | SOC1 goldens under Debug and `-O` | fix the Swift, never the fixture (the Python reference is the model's owner) |
| R10 | The device clock is moved (lives, events, the social world) | C3/SOC1 tests: back = never punished, world frozen; forward = advances | the high-water mark (§4.11) |
| R11 | The spike source lives only in the gitignored `build/spike/` (REUSE §3.1) | the orchestrator commits it to `design/spike-src/` before WP0 | — (a lost spike costs B1 a day) |
| R12 | Values still moving: the meta explorer and the analyst are still writing, clips-needed has 19 open rows | every WP re-reads the research files it names at start | the knobs are data (`Tuning/*.json`, `design/levels.json`); a late number is a data change, not a code change |
| R13 | The notification and rating prompts appear over tests and captures | `-pc.uitest`/`-pc.capture` suppress them | uninstall before a test that expects the one-shot alert |
| R14 | Simulator slots are shared with app-factory-0b (Match Factory) on this Mac | `xcrun simctl list devices booted` before each WP | wait; never boot a third simulator |
| R15 | The owner's "tap sound" wish vs the original's silent taps (§7.2) | — | the `tapTick` slot exists; the orchestrator decides the mapping |
| R16 | Full-bleed @3x art (1179 × 2556 px ≈ 12 MB decoded each) on home and event screens pushes memory | V3 memory rows | downsample on decode to the screen's pixel size; release event art when leaving the screen |

---

## 12 Build plan

### 12.1 Slots and stages
At most **two** agents compile for iOS or run a simulator at once (§2.6): slot **A** = "Maze A"
`177520B6-4889-46C2-BDD9-155813D2B175`, slot **B** = "Maze B" `B80EDB24-6280-4C52-A63F-E8AADD245017` (iPhone 16, iOS 26.0).
No-simulator lanes (`swift test`, Python, art) run alongside, at most 3 at once. A device build for the phone runs inside slot
A's window (it compiles) and needs the phone lock (`/tmp/phonedriver.lock`) from the orchestrator.

| stage | slot A: "Maze A" | slot B: "Maze B" | no-simulator lanes | gate to the next stage |
|---|---|---|---|---|
| 0 | — | **WP0** LEAD | (orchestrator: `design/spike-src/` committed) | WP0 acceptance; contracts hashed |
| 1 | **B1** BOARD (+ **D1a** phone bench at its end) | **S1** SHELL, then **A3** AUDIO (≤ 45 min window) | **C1 → C2** CORE · **L1** CONTENT (starts when C1's decoder is green) · **A1 → A2** AUDIO · **SOC1** SOCIAL · **UI-ART** | B1 + S1 + C2 + L1 green |
| 2 | **B2** BOARD | **S2** SHELL | **C3 → C4** CORE · **L2** CONTENT · SOC1 (cont.) · UI-ART | B2 + S2 + C3 green |
| 3 | **G1** GAME (slot A handed over from BOARD) | **S3** SHELL | C4 · L2 · UI-ART rounds | G1 + S3 green |
| 4 | **G2** GAME | **V1** VERIFY | — | G2 + V1 green |
| 5 | **SOC2** SOCIAL (screens) | **V2** VERIFY (captures; owners' fix loops one at a time on slot B) | — | SOC2 green; V2 round 1 findings filed |
| 6 | **V3** VERIFY (sim perf + soak) → **D1b** device | V2 rounds 2–3 (≤ 3 rounds, GP §9.2) | — | §14-of-GP definition of done |

Dependencies (a WP starts when its inputs are green):
| WP | needs |
|---|---|
| C1 | WP0 |
| C2 | C1 |
| C3 | C2 (session types) |
| C4 | C2 |
| SOC1 | WP0 (+ `design/social/fixtures/` from the social designer) |
| L1 | C1 (decoder, `pclevels import`), `design/levels.json` (SPEC-gameplay) |
| L2 | L1, C4 (generator, validator) |
| A1 | WP0 (the `SoundID` list), SPEC-motion-audio |
| A2 | A1 |
| A3 | A2, S1 |
| UI-ART | art lanes (running already); MANIFEST |
| B1 | WP0, `design/spike-src/`; switches to PathCore's geometry as soon as C1 is green |
| B2 | B1, C2 (plans), UI-ART board sprites |
| S1 | WP0, UI-ART's GlossyChrome |
| S2 | S1, A3 |
| S3 | S2, C3 |
| G1 | B2, S2, C2, C3, L1, A3 |
| G2 | G1, S3, C4, L2 |
| SOC2 | SOC1, S3, G2 (events glue) |
| V1 | G1, S3 (re-runs after G2/SOC2) |
| V2 | G2, SOC2 |
| V3 | G2, SOC2 |
| D1 | D1a after B1; D1b after V3 |

Handoff rules (every WP): the slot's build green; `shasum -a 256 -c build/wp0/frozen-contracts.sha256` green; the simulator
shut down; a structured report (status, acceptance items with evidence paths under `build/<wp>/` or the scratchpad — never
`design/`, files, requests for others, open issues). Nobody weakens a failing test. No WP commits.

### 12.2 Work packages

#### WP0 — Scaffold and contracts (LEAD, slot B)
- **Files:** everything WP0 owns in §3.2: `project.yml`, `App/Info.plist`, `App/GameApp.swift`, `App/Brand.swift`,
  `App/AppModel.swift` (services created, boot sequence calling the contracts' `warmUp()`/`prepare()`), every ◆ file with its
  full public surface and stub bodies, `App/Support/{PlayerStore,PerfMonitor,LatencyProbe}.swift` (working basics),
  `Packages/PathCore/Package.swift` + every ◆ PathCore type + `pclevels` stub + a smoke test + the `APISurfaceTests` skeleton +
  a frozen v1 `PlayerState` fixture; real code copied, not stubbed: `PathRandom` (MF `MFRandom`, renamed), `Ease` (MF), and
  `App/Board/Track.swift` (from `design/spike-src/`); `Resources/Tuning/{board,game,ui,audio,rules,social}.json` (defaults or
  `{}`); `Resources/Fonts/` (the 2 TTFs from `design/fonts/`); `Assets.xcassets` (placeholder AppIcon, `LaunchBackground`);
  `StoreKit/ArrowOut.storekit` (the catalogue's products if SPEC-ui/gameplay has them, else one test product); `.gitkeep` in the
  empty resource folders (`Levels`, `Sounds`, `Music`, `Social`, `Strings/requests`); `UITests/UITestSupport.swift` (launch
  helper, probe reader); the §2.5 tool amendments; `build/wp0/frozen-contracts.sha256`.
- **Inputs:** §2–§5.10, §6.1, §6.5–§6.6, §7.4, §9.1–§9.3; SPEC.md reconciliations; the other specs' enums (SoundID cue list,
  booster ids, feature ids, popup ids); `apps/matchfactory/{project.yml, App/Support/*, App/Contracts/*}` (patterns);
  `design/spike-src/`.
- **Acceptance:**
  1. `tools/gen.sh` and `tools/core.sh` succeed on macOS (PathCore builds; the smoke test and the `APISurfaceTests` skeleton
     compile without `@testable`; the import grep passes).
  2. `tools/build.sh B` and `CONFIG=Release tools/build.sh B` succeed.
  3. `tools/run.sh B -pc.reset 1` shows the Loading placeholder then the boot placeholder; `build/run-B.log` contains
     `[PC][launch] … fully visible`; the screenshot is LOOKED at.
  4. The built `.app` contains `UI/` (the tape/door/lock/key/pipe PNGs), `Art/` (character PNGs + `*_rig/rig.json`), `Tuning/`
     (6 files), `Fonts/` (2 TTFs), `Levels/`, `Social/`.
  5. `plutil -p` on the BUILT Info.plist shows `CADisableMinimumFrameDurationOnPhone`, `UIAppFonts` (2 entries),
     `PCBrandName = Arrow Out`, `CFBundleDisplayName = Arrow Out`, portrait only, `UIDeviceFamily = [1]`.
  6. `shasum -a 256 -c build/wp0/frozen-contracts.sha256` passes and lists exactly the §3.5 files.
  7. A grep of `App/`, `Packages/`, `project.yml` finds no "Maze", "MazeOut", "Arrow Jam", "Grand", "arrowjam" (and "Arrow
     Out" only in `project.yml`); no file name contains them.
  8. "Maze B" is shut down.

#### C1 — Grid, geometry, level model and JSON, RNG, motion (CORE, no simulator; first)
- **Files:** `PathCore/{Grid,Model,Random,Motion}/*` (non-◆ files), their tests (`c1_` fixtures), `Package.swift` from now on.
- **Inputs:** §4.2, §4.3, §4.13, §4.16; spike "Measured reference geometry" + `design/spike-src/App/Core/*`; STYLE §A;
  motion §2–§5; `research/levels/*.json`; `research/video-frames/work/extract/*.json`; `tools/rng_ref.py`.
- **Acceptance:** `swift test` green; the fit rule on all 30 recorded levels within ±0.03 pt; all 41 phone JSONs and all 58
  video extracts decode with an unknown-key report and 0 errors; the bundle schema round-trips; the hit geometry passes the
  spike's 873 + 399-point test with 0 wrong; `ExitKinematics` reproduces the motion §2.3 table within ±0.003 s; every §4.16
  curve hits its sample points; `RandomTests` equal `python3 tools/rng_ref.py` output; 4 mutations (§4.17) all CAUGHT.

#### C2 — Rules, session, clock, combo, greedy solver, headless driver (CORE, no simulator)
- **Files:** `PathCore/{Rules,Session}/*` (non-◆), `Solver/{Greedy,Hint}.swift`, `RulesTuning.swift`, `Resources/Tuning/
  rules.json`, `Tests/tools/golden_rounds.py`, tests incl. completing `APISurfaceTests`.
- **Inputs:** §4.4–§4.7, §4.14 (greedy, hint), §4.15; levels, obstacles, tutorials §2/§8, motion §2.1/§3/§4; SPEC-gameplay
  (rules, fail chain); `research/bot/log.jsonl`.
- **Acceptance:** the `RulesTests`, `SessionTests`, `ClockTests`, `ComboTests`, `HeadlessTests` suites (§4.17) green; the
  **golden rounds** test: every arrow the phone bot tapped in round k (L32–L61) is FREE in our rules at that round's start, 0
  mismatches, with the mismatch list printed if any; the HeadlessDriver wins every recorded level (reveals merged) at 0.6 s per
  tap; `APISurfaceTests` calls every public member of every ◆ PathCore type without `@testable`; 6 mutations all CAUGHT.

#### C3 — Economy, lives, boosters, events, persistence (CORE, no simulator)
- **Files:** `PathCore/{Economy,Events,Persistence}/*` (non-◆), `Tests/tools/lives_ref.py`, tests.
- **Inputs:** §4.8–§4.10, §4.12; flows, levels (economy notes), vflows §8, web §7; SPEC-gameplay (values).
- **Acceptance:** `EconomyTests`, `LivesTests`, `BoostersTests`, `EventsTests`, `PersistenceTests` green: start 1000; rewards
  20/60/100/80; FTUE payout banked and flown (1000 → 1120); continue 900; a loss costs a life, a win refunds none; the lives
  chain equals `lives_ref.py` on 200 random scripts; the clock set back never punishes; unlimited stacking (30 m + 1 h =
  the L55 observation); Claw points = multiplier and untouched by a loss; the multiplier ladder and reset; the frozen v1 fixture
  decodes; additive fields decode from old JSON; corrupt → backup; 5 mutations all CAUGHT.

#### C4 — Search solver, validator, generator, level provider, pclevels (CORE, no simulator)
- **Files:** `PathCore/Solver/{Search,Difficulty}.swift`, `PathCore/Content/*`, `Sources/pclevels/main.swift`, tests.
- **Inputs:** §4.14; spike "Core rule, solver and generator" + `design/spike-src/App/Core/Generator.swift`; `Levels/curve.json`
  (L2 fits it; C4 ships a default); art sprite list (`art/ui/out`).
- **Acceptance:** `SolverTests`, `ValidatorTests`, `GeneratorTests`, `LevelLibraryTests` green; DFS = greedy on every monotone
  board and solves the non-monotone fixtures; 500 generated levels past the authored end are byte-identical across two runs,
  valid, solvable, won by the driver, and inside their curve bands; generation ≤ 30 ms p95 (macOS `-O`) for 40 × 40;
  `pclevels validate App/Resources/Levels --sprites art/ui/out` passes; 3 mutations all CAUGHT.

#### SOC1 — The social world simulation (SOCIAL, no simulator)
- **Files:** `PathCore/Social/*` (non-◆), `Resources/Social/*.txt`, `Resources/Tuning/social.json`, `Social*Tests.swift`
  (`soc_` fixtures).
- **Inputs:** §4.10–§4.11; `design/SPEC-social.md` (the model); `design/social/tools/socialsim/` (the Python reference) +
  `design/social/fixtures/` + `design/social/data/`; vflows §9; flows (Weekly Contest, Streak Race, Rocket Race, Sky Jump).
- **Acceptance:** bit-exact agreement with the Python reference on the whole fixture set (≥ 10 k values: hashes,
  permutations, tables, calendar, names, leaderboard pages at ≥ 20 times across 3 years, race fields, Sky Jump fields), in
  Debug and `-O`; the rewind test (world frozen while the clock is behind the high-water mark); 100 k generated names pass the
  blocklists; `Resources/Social` byte-identical to `design/social/data`; a 50-row page ≤ 1 ms on macOS `-O`; 4 mutations all
  CAUGHT.

#### SOC2 — Social and event screens (SOCIAL, slot A after G2)
- **Files:** `App/Shell/Social/*`, `Strings/requests/social.tsv`, `Tests/Social*Tests.swift`, `UITests/SocialUITests.swift`.
- **Inputs:** §6.6, §6.9, §9.5; SPEC-ui (leaderboard, Claw, Streak Race, Rocket Race, Sky Jump, Weekly Contest frames and
  copy); SPEC-social; flows, vflows §9; `uim` screens `claw`, `clawInfo`, `claim*`, `sky*`, `race`.
- **Acceptance:** every screen opened with `-pc.go event:<id>`/`-pc.popup …` at a fixed `-pc.now` matches its reference (layout
  ±2 pt, copy exact EN/TR) in ready-file captures that are LOOKED at; `SocialLab` shows boards and races moving with
  `-pc.clockRate 600`; two launches with the same seed and time render identical rows; setting `-pc.now` earlier never shows
  less progress; the L50 Weekly Contest tutorial locks input to the trophy tab; a 200-row leaderboard scroll has 0 frames > 20 ms
  (simulator, Release).

#### L1 — Levels 1–61, sessions, tutorials, unlocks, strings base (CONTENT, no simulator)
- **Files:** `Resources/Levels/level_0001…0061.json`, `sessions.json`, `tutorials.json`, `unlocks.json`,
  `Resources/Strings/strings.tsv`, `Localizable.xcstrings` (generated), `tools/strings/*` (sources.json pointed at the real spec
  headings; `build.py` merges `requests/*.tsv`), `tools/levels/{render.py, pathlib_rules.py}`.
- **Inputs:** `design/levels.json` (SPEC-gameplay: the source of truth), SPEC-ui/SPEC-gameplay string sections; levels.md,
  tutorials.md, vflows; `research/levels/*` + reveals; the video extracts; the owner's orders (L1–31 from the videos, the phone
  wins from L32).
- **Acceptance:** `pclevels bundle` reproduces the folder from `design/levels.json` byte for byte; `pclevels validate` green
  with sprites; `pclevels bot` wins every level; **overlay proof:** every recorded level rendered by `tools/levels/render.py`
  over its capture reaches IoU ≥ 0.99 with 1-px tolerance, every video level ≥ 0.97 (video compression) and its `vextract replay`
  has 0 inconsistent taps; recorded levels equal their research JSON cell for cell after the reveal merge; the Python mirror
  (`pathlib_rules.py`) agrees with PathCore on the free set of every level's start state; `build.py` output parses, every row
  has EN + TR, argument ORDER checked; `coverage.py` passes against the spec sources; the `pclevels needs` list goes to UI-ART.

#### L2 — Designed levels to the authored end, curve, strings complete (CONTENT, no simulator)
- **Files:** `Resources/Levels/level_0062…NNNN.json` (the authored count: PENDING-gameplay, ≥ 100 per PLAN V1 scope),
  `Levels/curve.json`, the final `strings.tsv`/`Localizable.xcstrings`, level contact sheets under `build/l2/`.
- **Inputs:** SPEC-gameplay (curve, cadence, obstacle schedule), L1, C4 (generator, validator), `design/levels.json` designed
  entries.
- **Acceptance:** validator + bot green on every authored level; `pclevels stats` shows the designed levels inside the bands
  fitted to L1–61 (arrows, rounds, timer, tag cadence) with the table in the report; the contact sheets are LOOKED at; strings
  coverage 100 % EN/TR including every `requests/*.tsv` row and argument order.

#### A1 — Sounds (AUDIO, no simulator)
- **Files:** `tools/audio/{specs,sfx,music}.py` tables and recipes, `Resources/Sounds/*.wav` (+ `Music/*.wav` only if
  SPEC-motion-audio finds music).
- **Inputs:** SPEC-motion-audio (cue list, recipes), sounds.md §2 recipes, §7.2 here.
- **Acceptance:** `tools/audio/check.py --reproduce` passes (every `SoundID` has its file, lengths and peaks within ±1.5 dB of
  the spec, no edge clicks, byte-identical re-render); `check_selftest.py` catches every applicable mutation; spectrograms in
  the report; **no file derives from `research/sound-refs/`**.

#### A2 — Audio engine and haptics code (AUDIO, no simulator)
- **Files:** `App/Audio/{AudioEngine,SoundBank,MusicPlayer,AudioCues,Haptics}.swift`, `Tuning/audio.json`.
- **Inputs:** §7; MF `App/Audio/*` (05424db); REUSE §3.4.
- **Acceptance:** compiles against `AudioContract.swift` (checked in A3); an offline AVAudioEngine test on macOS (MF's
  `enginetest` pattern) renders each cue through the graph and asserts the scheduled-to-output sample offset ≤ one IO buffer.

#### A3 — Audio integration (AUDIO, slot B window after S1, ≤ 45 min)
- **Files:** `App/Audio/SoundBoard.swift`, `Tests/Audio*Tests.swift`, `Strings/requests/audio.tsv`.
- **Acceptance:** build green; `-pc.go soundboard` plays every id and every haptic with no engine error in the log; the
  latency line is logged; Sound/Music toggles mute their buses; a debug interruption restarts the engine and the idle voices.

#### UI-ART — Our rasters and chrome for every shipped screen (art lanes, no simulator)
- **Files:** `art/**` (their lanes): every MANIFEST entry routed B2/B3/C1/C2/C3 → `art/ui/out/<id>@3x.png` / `art/out/…`;
  `art/ui/code/GlossyChrome.swift` (route B1 components, iOS 18 + macOS 14, labels through `GameText` once S1 ships it); the
  box sprites or slice set (§5.6 request); the per-size door sprites from `pclevels needs`; `appIcon1024` → the AppIcon image.
- **Acceptance:** `manifest_check.py --strict` green with 0 `todo` among the entries the shipped screens use; side-by-side
  sheets LOOKED at and graded A/B by the director (0 C, GP §14); `GlossyChrome.swift` type-checks for iOS 18
  (`xcrun swiftc -typecheck -target arm64-apple-ios18.0-simulator …`) after every edit.

#### B1 — Board foundation and risk checks (BOARD, slot A)
- **Files:** the B1 files of §3.2 (`App/Board/*` foundation, `PerfMonitor`, `LatencyProbe`), `Tuning/board.json`,
  `Tests/BoardTests*.swift`, `UITests/{BoardInputTests,BoardLabTests}.swift`, `Strings/requests/board.tsv`.
- **Inputs:** §5 (all), §9.4–§9.6, §10, §11 R1–R6; `design/spike-src/`; STYLE §A; motion §1–§3, §5.1.
- **Order:** needs WP0; starts from the spike's code while C1 runs, switches to PathCore's geometry when C1 is green.
- **Acceptance:**
  1. **L32 against shot 003** (same 393 × 852 screen, ready-file capture): best shift ≤ 1 px, stroke 12.0 ± 0.3 px, dot Ø
     10.3 ± 0.3 px and #C5E1FF, black-ink IoU ≥ 0.90 with the tapes masked (the spike reached 0.909), ink coverage within 1 %;
     the sheet is LOOKED at.
  2. Zoom clamps at 0.786× fit and at 28.07 pt per cell (L50 opens at the cap); a pinch never starts the timer; a swipe pans.
  3. Exit timing: 20 logged exits' keyframes match `ExitKinematics` within ±1 frame; the first presented exit frame shows full
     ink (P1: no fade-in), and 100 % of the dots appear after an autoplay (P3).
  4. `BoardInputTests` (real touches): a 2 s hold fires on release; a swipe pans without firing; head tap; a 15 pt off-stroke
     tap; the midpoint tie goes right.
  5. Latency (simulator, Release): `touch→handler` ≤ 4 ms p99 and the exit on the next vsync (R1 closed).
  6. Performance (simulator, Release): the 304-arrow board at max zoom, 5 simultaneous solid exits × 4 waves → 0 frames > 20 ms,
     footprint ≤ 40 MB; the bump with its contact beat, vignette and red return, in a freeze capture.
  7. The warm-up runs behind Loading; the first exit and bump after a fresh install show no frame > 20 ms (simulator).
  8. **D1a** (when the orchestrator grants the phone): the same lab in Release on the iPhone 15 — the §10.4 soak boards at max
     zoom, xctrace hitches (or recording gaps), latency, first-use stalls, memory; R2, R3, R5, R6 closed with numbers.

#### B2 — Obstacles, combo painters, transitions (BOARD, slot A)
- **Files:** the B2 files of §3.2, BoardLab obstacle scenarios, `Tests/BoardObstacleTests.swift`.
- **Inputs:** §5.5 painters, §5.6, §5.7, §5.12; motion §2.4, §4, §5.6; STYLE §A.2; the art sprites.
- **Acceptance:** each obstacle scenario runs in BoardLab and its `-pc.freezeAt` captures are compared with the research shots
  and motion beats: the key flight bursts the door at tap + 1.14 s ± 1 frame (log), the pipe breaks 0.05 s after the head leaves
  (log), box counters count down together and break with dots underneath, tape carry, elevator reveal, the corner bend; the
  rainbow painter + stars on 5 simultaneous exits at max zoom on the 304-arrow board → 0 frames > 20 ms (simulator, Release);
  the clear wave and the Levels 1-4 stage transition (0.7 s ± 1 frame) captured; the warm-up covers every new effect (first
  use ≤ 20 ms); sprites resolve for every bundled level.

#### S1 — Shell foundation (SHELL, slot B)
- **Files:** the S1 files of §3.2 (Root/Router/Loading/Transitions, Components incl. `GameText` and the generated `UIArt`,
  the Home skeleton with `PuppetStage`, `PopupHost` + Pause/Quit/Settings, FX host, ShellLab), `Fonts/`, `Tuning/ui.json`,
  `tools/uiart_gen.py`, `Tests/ShellTests*.swift`, `Strings/requests/shell.tsv`.
- **Inputs:** SPEC-ui (home, pause, settings, loading, text styles), `uim` `loading`/`home`/`pause`, fonts §5–§6, §6 here,
  the art rigs.
- **Acceptance:** home at L32/L34/L39 states (`-pc.level`) against shots 026/035/060: frames within ±2 pt (LOOKED at); the
  puppets' default layers recompose each rig's full render (mean ≤ 1/255) and idle loops run with 0 main-thread work (Time
  Profiler sample in the report); Pause/Quit/Settings popups appear instantly with the 0.90 dim; toggles persist across a
  relaunch in `PlayerState` (not UserDefaults); `GameText` matches fonts §6 on the Paused title and the Play label; `FontCoverageTests`
  green; ShellLab pages captured with ready files.

#### S2 — HUD, level popups, win, unlock, tutorial layer (SHELL, slot B)
- **Files:** the S2 files of §3.2 (HUD, fail/win popups, banners, unlock overlay, claim popup, TutorialLayer, Confetti,
  Fireworks, WinLogoSequence).
- **Inputs:** SPEC-ui (hud, booster, outOfTime, continue*, failed, win*, celebrate, unlock, streakRace, claim), SPEC-motion-audio
  (HUD intro, celebration, unlock, caption/hand), motion §5, tutorials §3/§6.
- **Acceptance:** every S2 popup via `-pc.popup` matches its reference shot (layout ±2 pt, copy exact EN + TR); the HUD in
  normal/Hard/Super Hard against shots 003/036/061; the HUD intro timings from the log within ±1 frame of motion §5.1; the
  celebration at `-pc.freezeAt win@…` against the motion §5.6 beats, the panel at +3.36 s, tap-to-skip; the unlock overlay's
  staggered beats; HUD writes ≤ 10 Hz (counted over 60 s of play).

#### S3 — Home complete, shop, profile, meta popups (SHELL, slot B)
- **Files:** the S3 files of §3.2 (HomeScene, ClawBar, EventBadges, PayoutSequence, CoinFly, Shop, Profile, username/edit
  profile/no lives/booster buy popups), the `.storekit` from now on, `Tests/ShellStoreKitTests.swift`.
- **Inputs:** SPEC-ui (home complete, shop, profile), vflows §6/§8/§9.2, flows (home, Claw bar), C3.
- **Acceptance:** home captures with the Claw bar, badges and the "!" tab against shots 035/064/070/202; the payout sequence
  (+120 on the first home, +20 later) against vflows §6 beats (log ±1 frame); FakeStore purchase grants and shows "Test store:
  nothing is charged"; `ShellStoreKitTests` (`SKTestSession`) grant once and a replay grants nothing; the username/avatar round trip
  persists.

#### G1 — Game integration (GAME, slot A)
- **Files:** the G1 files of §3.2, `AppModel.swift`, `PlayerStore.swift`, `Tuning/game.json`, `Tests/GameControllerTests.swift`,
  `UITests/GameFlowTests.swift`, `Strings/requests/game.tsv`.
- **Inputs:** §8; C2, C3; B2, S2, A3; L1.
- **Acceptance:** from a fresh install `-pc.autoplay 1 -pc.autoplayStop 20` completes L1 → L20 (Levels 1-4 as one session, the
  FTUE chain to L6, the first home payout) with no error; a `GameController` unit test with a fake board proves the §8.1 fan-out
  order; the **same-frame proof**: over 50 taps the log shows ripple, mover, haptic and sound calls within 1 ms and before the
  commit, and the exit on the next vsync; the probe's `t` stays constant for 3 s during pause, popups, offers, the unlock
  overlay and before the first tap; the time-out and hearts-out chains via `-pc.timer 3`/`-pc.hearts 1`; win banked
  before the celebration (kill during the celebration → still won at relaunch).

#### G2 — Tutorials, FTUE, unlocks, boosters, events glue, prompts (GAME, slot A)
- **Files:** the G2 files of §3.2.
- **Inputs:** §8.4; `tutorials.json`, `unlocks.json`; SPEC-gameplay (events, boosters, queue order); S3; C4; L2.
- **Acceptance:** fresh-install autoplay to the authored end completes, and the logged tutorial + unlock ids equal the
  expected list from `tutorials.json`/`unlocks.json`; the "Tap to move!" beats against tutorials §3 (log ±1 frame); the
  rating prompt requested exactly once, after the L34 win (log); both boosters' flows; the event outcomes after a scripted
  sequence of wins and a loss equal C3's rules (multiplier, Claw points, Sky Jump, Rocket Race); the notification prompt once
  on the first launch only.

#### V1 — Test suites (VERIFY, slot B)
- **Files:** `Tests/AppTests/*`, the V suites of §9.7, `UITests/UITestSupport.swift`.
- **Acceptance:** every §9.7 suite passes **twice in a row**; `StringsCoverageTests`, `FontCoverageTests`, `UIArtBundleTests`
  (0 missing art in the bundle), `LevelsBundleTests` (every bundled level decodes, validates, sprites resolve), `TuningTests`,
  `BrandTests` (§6.11 grep on the built app, file names included) pass; the Release binary contains no dev placeholder string
  (`strings ArrowOut | grep -c` of the `DebugPlaceholder` marker string = 0, with a control string > 0, GP §14).

#### V2 — Side-by-side fidelity (VERIFY, slot B; owners fix in turns)
- **Files:** `tools/capture/manifest.json`, `tools/compare/{regions.py,regions.json,annotations.json}`; output
  `build/compare/`.
- **Acceptance:** ≥ 30 screens and states in EN and TR (home normal/Hard/Super Hard, HUD ×3, every popup, the win freezes,
  the unlock overlay, the FTUE hint, event screens, leaderboards) captured by ready file and LOOKED at; each region within
  ΔE ≤ 6 and ±2 pt or an explained annotation; `FINDINGS.md` with an owner per finding; ≤ 3 fix rounds (GP §9.2).

#### V3 — Performance and soak (VERIFY, slot A)
- **Files:** `tools/bench/*` updates (the new marks), `build/bench/`.
- **Acceptance:** the §10.2 simulator rows with an idle baseline; the §10.4 soak on the simulator: 0 frames > 20 ms in the
  board soak, the 30-level autoplay soak with no crash, memory growth ≤ 10 MB; `bench.sh launch` numbers; the report lists
  every row with its measured value.

#### D1 — Device verification on the owner's iPhone 15 (BOARD for D1a, VERIFY for D1b; the orchestrator holds the phone lock)
- **Steps:** a Release build for `id=00008120-000964E426440032` (GP §9.4 recipe, Bash timeout ≥ 300 s; a "provisioning profile
  … cannot be found" error is a race: retry once); `devicectl` uninstall → install → launch; the phone runner by its absolute
  path (`/Users/yago/Downloads/app-factory/tools/phonedriver/phone`).
  - **D1a** (after B1): BoardLab in Release: the §10.4 board soak at max zoom, latency, first-use stalls after a fresh install,
    memory; R2/R3/R5/R6 closed with numbers.
  - **D1b** (after V3): the full app, fresh install, **no launch arguments**: boots to the real first run (Loading → notification
    prompt → Levels 1-4); the full-game soak (autoplay 30 levels) and 10 min thermal soak; xctrace hitches; the **side-by-side**
    clips: the same L32 taps in our app and in the original (`phone rec`, 60 Hz): tap mark → ripple → first motion frames, the
    exit ramp and arc length, a bump; the shop works through FakeStore; `phone shot` LOOKED at.
- **Acceptance:** the §10.2 device rows met (0 frames > 20 ms in the soaks, tap → first motion on the next frame with ripple +
  haptic on it, ours ≤ theirs on the same clips, no first-launch or level-start stall, memory within caps); the numbers and the
  side-by-side sheets archived under `build/device/`; one optimisation round if a budget misses, then honest numbers to the
  owner (GP §9.4).

---

## 13 Evidence map (where each module's numbers come from)
| module | primary evidence |
|---|---|
| Grid, fit, zoom, head/stroke metrics | STYLE §A; spike "Measured reference geometry"; levels (every level's fit pitch; L47 zoom probe; L50 cap) |
| Exit motion, colour, dots, stars, layering | motion §1–§2; spike 3c–3e; runner shots L038-r07, L048-r17 |
| Bump | obstacles "BUMP" (phone clips L47/L48); motion §3 (YT-B) |
| Obstacles | levels L32–L61; obstacles.md; motion §4; STYLE §A.2; tutorials §6; vextract (video) |
| Input, hit test | levels "Input model", L47 probes, L52 tie; motion §2.1; spike 3a/3b |
| Session, timer, FTUE | tutorials §1–§8; levels (timer at the first tap); vflows §1–§5 |
| Economy, fail chain | flows; levels (lives, rewards); vflows §8; web §2, §7 |
| Events, social | flows (Claw, Streak Race, Sky Jump, Rocket Race, Weekly Contest); vflows §9; web §8–§9; SPEC-social; `design/social/` |
| Shell geometry, text | `design/ui-measure.md`, `ui-tokens.json`; fonts §5–§6; art manifest |
| Audio, haptics | sounds §1–§5 |
| Performance | spike frame-time table; OWNER 03:00 |

---

## 14 PENDING index (values this spec leaves to the content specs; each is already a knob)
- **PENDING-gameplay:** tape some-clear policy; tapping a bumping arrow; pipe consumption on a blocked exit; elevator empty-cell
  blocking; hearts per stage in multi-board sessions; the fail chain's later steps and grants (hearts-out chain, escalation);
  life refill seconds (INFERRED ≈ 1200); kill mid-level; booster effects (`freeze` seconds, `hint` policy), prices, buy flow;
  shop catalogue; Claw ladder and duration; the event schedule (unlock levels); the authored level count; unlock levels in our
  build; hit radius and tie break beyond the observations; timer alerts near 0; local notifications (none by default).
- **PENDING-ui:** Loading minimum time; home tab and Loading → home transitions; the arrow-pile states; the no-lives, booster-buy
  and settings layouts; the Support/Terms/Privacy offline states; the silhouette border; box sprites/slices (with UI-ART);
  the shop layout.
- **PENDING-motion-audio:** bump profile (phone vs YT-B); the violet colour; the rainbow period; star counts/sizes; build-in of
  obstacles; pipe/box counter-change timing and animation; pan limits and snap-back; slop; combo window refinements and
  whether bumps break it; puppet idle loops; the cue list and music (and the owner's tap-sound question, §7.2); haptic
  intensities.
- **PENDING-social:** the whole world model (population, names, curves, race bots, Sky Jump field, Weekly/World/Country
  dynamics), event durations and calendar, the clock-forward policy.
