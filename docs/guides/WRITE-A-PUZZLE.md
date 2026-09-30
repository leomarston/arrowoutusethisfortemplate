# Write a puzzle module

A game made from this template = the shared system + **a puzzle module** + a skin + `game.yml` (map: `docs/TEMPLATE.md`).
This guide is the "how" of the module. The contract itself (every type, every rule) is
`docs/architecture/PUZZLE-MODULE.md`; read its §2-§5 once, then follow the steps here. The worked example is
**SortPuzzle** (colour sorting: pick a tube, then a target; no timer, no hearts; the one fail is "stuck"), the second
module, written only against the contract. Arrow Out's own module (ArrowEscape) is the first one; it is older, bigger and
wraps a session that existed before the contract, so copy SortPuzzle's shape, not ArrowEscape's.

All paths below are relative to the game folder (`apps/<slug>/`; the reference is `apps/mazeout/`) unless they start with
`docs/` or `tools/`.

**Status:** SortPuzzle's Swift (core target, app half, its tests) builds and passes on CI (core `swift test` + app
unit tests, run 19 onward); its Python reference and goldens are checked on Linux in the same CI. Device feel and UI tests
still need the Mac.

## 0. What a module is

| Half | Where | Depends on | SortPuzzle |
|---|---|---|---|
| **Core** (pure Swift: rules, levels, session, bot) | `Packages/PathCore/Sources/<Module>/` | `Foundation` + `GameCore` only | `Sources/SortPuzzle/SortLevel.swift` (`SortLevel`, `SortRules`), `SortMechanics.swift` (`SortMove`, `SortMechanics`, `SortSolver`, `SortGenerator`), `SortPuzzleSession.swift` (`SortEvent`, `SortPuzzleSession`, `SortPuzzleModule`, `SortBot`) |
| **App** (plugin, board view, entry) | `App/Puzzles/<Module>/` | UIKit/SwiftUI, `PathCore`, the core product | `App/Puzzles/SortPuzzle/SortPuzzlePlugin.swift` (`SortPuzzlePlugin`, `SortPuzzleEntry`), `SortPuzzleBoard.swift` (`SortBoardTuning`, `SortBoardLayout`, `SortBoardView`, `SortPuzzleBoard`) |
| **Data** | `App/Resources/Tuning/<module>.json`; colours in `skin/colors.json` `puzzle.<board>.*` | — | `Tuning/sort.json` (`levels`, `play`, `failChain.stuck`, `board.*`); 17 `puzzle.sortBoard.*` tokens |
| **Determinism proof** | `tools/<module>/ref.py` + `Packages/PathCore/Tests/Fixtures/<module>_goldens.json` | Python 3 stdlib | `tools/sortpuzzle/ref.py`, `sortpuzzle_goldens.json` |
| **Tests** | `Packages/PathCore/Tests/<Module>Tests/`, `Tests/<Module>AppTests.swift` | — | `SortPuzzleTests` (16 tests), `Tests/SortPuzzleAppTests.swift` (6 tests) |

What a module must never do (CLAUDE.md, contract §3): read the wall clock or an unseeded random; import UIKit in the core
half; name a colour, a size or a duration as a Swift literal (data and skin tokens only); name an art FILE (art slots
only, `puzzle.<sprite>`); change anything in `App/Game`, `App/Shell` or GameCore to make itself fit. If the module needs
the shell to do something new, that is a contract change: write it into PUZZLE-MODULE.md §8b the way v1.1 did, additive
only, and pin it with a test (SortPuzzle's one change: `MetaRules.FailStep.action`, `ContractV11Tests`).

## 1. Decide the capabilities first

`PuzzleCapabilities` (GameCore `Session/PuzzleContract.swift`) is what the shell reads to set up the HUD, the booster
corners, the fail flow and the input. Write it before any rule:

| Field | Values | SortPuzzle | What the shell does with it **today** |
|---|---|---|---|
| `failRules` | `.timer`, `.moves`, `.hearts(n)`, `.none`, `.custom(id)` | `[.custom("stuck")]` | the fail flow runs on `offer` / `lost` outputs, any kind; popups have texts only for `outOfTime` / `outOfHearts` (gap) |
| `inputs` | `.tap`, `.drag`, `.swap`, `.select2`, `.paint`, `.multiTouch` | `[.select2, .drag]` | informational; the board owns its gestures |
| `boosters` | `BoosterSpec(id, effect: .freezeTimer / .addTime(n) / .addMoves(n) / .puzzleAction(id), icon: art slot?)` | `undo`, `extraTube` (both `.puzzleAction`) | slots in HUD order; stock and prices come from rules.json `economy` (gap: none for these ids yet) |
| `hud` | `.timer`, `.moves`, `.hearts`, `.goals`, `.progress`, `.score` | `[.progress]` | **not honoured yet**: the HUD always shows the timer pill + hearts row (gap) |
| `zoomable`, `multiStageSessions` | Bool | `false`, `true` | zoom is the board's; multi-stage sessions run through LevelFlow |

The known gaps are listed in `docs/guides/NEW-GAME.md` ("Known gaps") and docs/ROADMAP.md phase 5. A module may declare a
widget the shell cannot draw yet; the game cannot ship until the shell can.

## 2. The core half

### 2.1 The package target
In `Packages/PathCore/Package.swift` (SortPuzzle's lines are the pattern):
```swift
products: [ …, .library(name: "<Module>", targets: ["<Module>"]) ],
targets:  [ …, .target(name: "<Module>", dependencies: ["GameCore"]),
               .testTarget(name: "<Module>Tests", dependencies: ["<Module>", "GameCore"]) ]
```
Its own product, **not** re-exported by the `PathCore` umbrella target (so its type names never collide with ArrowEscape's).
Then add it to `tools/core.sh`: the directory loop (`for d in Sources/GameCore … Sources/SortPuzzle`) and the import check
(`check_imports Sources/<Module> 'Foundation|GameCore'`), so a stray `import UIKit` fails the core run.

### 2.2 Level model and rules
- A `Codable` level type (`SortLevel`: level number, tag, capacity, tubes) and a `Codable` rules type decoded from the
  module's tuning file (`SortRules`: `levels.curve`, `play`, `failChain`; its defaults equal the shipped sort.json, pinned by
  `testRulesDefaultsAreTheShippedSortJSON`).
- Levels are authored (a bundle of JSON files, like ArrowEscape's `App/Resources/Levels/`) or generated from a seed (like
  SortPuzzle: `SortGenerator.level(n, rules:)`, seed = `PathRandom.levelSeed(level, salt)`, rejected deals re-dealt, a
  last-resort deal that is always solvable). Seeded randomness only through GameCore's `PathRandom`.
- A solver or validator that proves every level is solvable (`SortSolver`: bounded iterative DFS). A generated module
  proves it at generation time; an authored one in a content check (ArrowEscape: `design/tools/validate_levels.py`).

### 2.3 The session (`PuzzleSession`)
One class per attempt (`SortPuzzleSession`). The contract's rules (PUZZLE-MODULE.md §3, §8b.4), as SortPuzzle applies them:
- **Deterministic** from `AttemptSetup.seed` + inputs; no wall clock; outputs in causal order; `won` / `lost` exactly once.
- **Rules resolve at the input**: `input(.select(tube), at:)` returns the whole answer (`selected`, then `poured` or
  `refused` as `.puzzle` events; `goalProgress`, `stageCleared` / `won`, or `offer(stuck)` as `.meta`); the board only
  animates what already happened.
- **Puzzle events** are your own enum conforming to `PuzzleEvent` (`SortEvent`); expose the three generic facts the shell
  may read: `move` (a resolved move: haptic, tap cue, tutorial dismiss, bot mistakes), `hintTargets`, `removedTargets`.
- **Untimed**: an idle `LevelClock(limit: 0)`, `timerArmed(stage, seconds: 0)` at ready, `timerStarted(stage)` at the
  stage's first real input (tutorials' "first tap"), `tick` returns nothing, `hearts` is nil, `WinResult.timeLeft` /
  `heartsLeft` 0 and the module's own numbers in `WinResult.stats`.
- **Progress** for the HUD: `goalProgress([GoalState(id:current:target:)])` at ready and on every change.
- **Fail**: emit `offer(ContinueOffer)` of your kind (`stuck`); `acceptContinue()` applies the chain step's grant
  (`.puzzleAction(id: "extraTube", amount: 1)`); still failing → the next step; `declineContinue()` → `lost(.stuck)`.
- **Boosters**: `canUseBooster(id)` false = nothing to do now (the shell takes no stock); `useBooster(id)` after the shell
  took the stock (`undo` pops the last pour; `extraTube` adds a tube, capped by `play.maxExtraTubes` per stage).
- **`hint()`** returns the next target to act on (for select-then-target: the next pick), so the autoplayer, the debug
  jumps and the bot work unchanged.
- `hold` / `release` pause whatever the module counts; `quit()` loses once.

### 2.4 The module type (`PuzzleModule`)
The protocol has three members (`id`, `contractVersion`, `capabilities`); SortPuzzle's enum adds the statics its plugin
and tests call: `level(_:rules:)`, `stage(_:) -> PuzzleStage` (the shell's view of one board: level, tag,
`timerSeconds: nil`, `hearts: nil`, a log summary, the level as `content`), `makeSession(…)` (merges the module's default
fail chain under rules.json's: `rules.meta(over: meta)`; rules.json wins for a kind it lists) and `warmUpWin(…)` (level 1
won headless by the bot: the shell's first-win warm-up). `id` is the kebab-case string `game.yml puzzle.module` names
(`sort-puzzle`).

### 2.5 The bot
A headless player that uses **only** `PuzzleSession` (`SortBot.play(_:)`: start, ack the intro, feed `hint()` as inputs,
ack stage transitions, accept offers). It proves the contract is enough to play, it is the warm-up, and tests use it.

## 3. Data: tuning, fail chain, colours, sprites
- `App/Resources/Tuning/<module>.json` holds every number: levels (salt, curve, tags), play rules, the module's default
  `failChain.<kind>` (steps with `price`, `grant`, `action`, `amount`, `warning`, `onlyWithStreak`), `board.*` sizes and
  durations. project.yml bundles the whole `Tuning` folder; load it with `TuningFile.load("<module>", bundle:, tune:)` so
  `-pc.tune` overrides work.
- **Colours** are skin tokens: add them to `skin/colors.json` `tokens` as `puzzle.<board>.<role>` pointing at palette names,
  run `python3 tools/skin/build.py`, draw `Skin.puzzle<Board><Role>`. Add them by hand: `tools/skin/codemod.py` files
  literals outside `App/Shell` / `App/FX` under the `art.*` area. `build.py --check-literals` scans `App/Puzzles`, so a
  leftover literal fails.
- **Sprites** (if the board draws raster art): register them in `art/MANIFEST.json` and map them as `puzzle.<sprite id>`
  slots in `skin/art.json`; the board draws them by slot (docs/guides/RESKIN.md §4). SortPuzzle draws shapes only.
- Strings (tutorial captions, the fail popup's texts) go in `App/Resources/Strings/strings.tsv`, 13 languages.

## 4. The app half (`App/Puzzles/<Module>/`)
project.yml's app target globs `App/`, so new files need no project edit, only `sh tools/gen.sh` on the Mac. The core
product goes into BOTH the app and the unit-test target's `dependencies` (`{ package: PathCore, product: <Module> }`,
as SortPuzzle's two lines in project.yml).

**Plugin** (`PuzzlePlugin`, `@MainActor`): `id`, `capabilities`, `stages(for:args:)` (nil = a level is missing, no life
taken), `makeSession(plan:stages:setup:streakActive:)`, `tutorials: [TutorialStep]`, `unlocks: [FeatureUnlock]`,
`mistakeTargets(_:board:)` (what the autoplayer taps to lose on purpose), `warmUpWin()` (a `@Sendable` closure run off
main). SortPuzzle's plugin takes an injectable level source so tests can hand it fixed boards.

**Board** (`PuzzleBoard`, any rendering tech; SortPuzzle is UIKit + Core Animation layers):
- `view`, `delegate`, `inputEnabled`, `allowedTargets` (tutorial restriction), `prepare()`, `load(_ StageContext)`,
  `playIntro`, `present([SessionOutput])` (pick your `.puzzle` events with `as?`), `playStageTransition`, `playClearWave`,
  `handPoint(for:at:)`, `performTap(on:)`, `publishProbe()`, `diagnostics` (may be nil).
- Input: hit-test the release, call `delegate.boardInput(.select(t), touchTimestamp:)` inside the touch handler; the session
  answers synchronously and `present` animates it in the same run-loop turn (the feel budget: one Core Animation
  transaction, no hitch > 20 ms).
- Acks (`.introFinished`, `.boardCleared`, `.stageTransitionDone`, `.contact` / `.beat`) come **later** than the call that
  caused them, never synchronously (LevelFlow calls `playIntro` before `session.start()`).
- The board drives the Play's master clock: `delegate.boardFrame(timestamp:targetTimestamp:)` on every display-link frame
  while it is in a window. SortPuzzleBoard keeps its own beat clock with `advance(_:)` so tests run it headless.
- `performTap(on:)` returns false while input is closed; the caller then sends `.tap(target)` to the session, so the
  session must accept `.tap` for its primary pick.

**Entry** (`PuzzleEntryPoint`): `makePlugin(_ app:)` and `makeBoard(_ app:)` (SortPuzzle: `SortPuzzleEntry`, loading
`sort.json` once for each).

## 5. The Python reference and goldens (anything seeded)
Swift and Python must agree exactly; the Swift is never edited to match itself.
- `tools/<module>/ref.py`: an independent implementation of the generator and solver (and of `PathRandom` via
  `tools/rng_ref.py`), reading the shipped tuning file.
- `--write` writes `Packages/PathCore/Tests/Fixtures/<module>_goldens.json` (SortPuzzle: levels 1-40 with tag, capacity,
  tubes, an FNV-1a hash and the solver's solution length; the first 3 with full move lists; a "stress" set with tight
  rules that pins the rejection and last-resort paths). `--check` exits 1 when the fixture is stale and self-checks every
  golden level.
- The core test (`testGoldensMatchThePythonReference`) decodes the same rules with the Swift type, generates the same
  levels and compares every field.
- Run it: `python3 apps/mazeout/tools/sortpuzzle/ref.py --check` → `ref.py: goldens up to date (40 levels, every one
  solvable by its recorded solution)` (verified on Linux, 2026-09-30).
- CI: the Linux job has one step per module (`.github/workflows/ci.yml`, "SortPuzzle goldens"); a new module's `--check`
  needs its own step (a CI edit).

## 6. Tests
**Core** (`Packages/PathCore/Tests/<Module>Tests/`; SortPuzzle's 16 as the list to copy): goldens == reference; rules
defaults == the shipped JSON; generator deterministic and salt-dependent; the first levels solvable, well formed, on the
curve; the move rules; the bot wins through the contract; a multi-stage session wins once; the fail offer opens the
chain and a grant continues; declined → lost exactly once; a rules.json chain beats the module default; quit loses once;
refusal + each booster (and its cap); every input form (`drag` = both picks); contract conformance (capabilities, idle
clock, `hearts` nil); the warm-up win.

**App** (`Tests/<Module>AppTests.swift`, hosted in the app; SortPuzzle's 6): plugin + real board headless through the
release handler (two boards); a release on nothing + the tutorial restriction; layout fits the screen and hits every
target; the bundled tuning file and which module `ActivePuzzle` names; the **unchanged `GameController`** playing a level
to the win panel; a fail offer paid through the shell. They reuse GameControllerTests' fakes.

Run them on the Mac: `apps/<slug>/tools/core.sh` (core) and `apps/<slug>/tools/test.sh A -only-testing:<Product>Tests`
(app), or on CI (README §3). Mutation-check the core tests (GAMEPROMPT.md §8.3): break a rule on purpose, the suite must
fail.

## 7. Select the module (the ActivePuzzle switch)
- `App/Contracts/PuzzleBoardContract.swift`, `enum ActivePuzzle`, is the ONE place a game picks its module:
  ```swift
  #if PC_PUZZLE_SORT
  static let entry: any PuzzleEntryPoint.Type = SortPuzzleEntry.self
  #else
  static let entry: any PuzzleEntryPoint.Type = ArrowEscapeEntry.self
  #endif
  ```
  A third module adds its own `#elseif PC_PUZZLE_<X>` branch. Every module's app half stays compiled in.
- Turn the condition on in the game's `project.yml`: `SWIFT_ACTIVE_COMPILATION_CONDITIONS: "$(inherited) PC_PUZZLE_SORT"`
  in `settings.base` of the app target AND of the `<Product>Tests` target (`SortPuzzleAppTests` checks the flag too).
  Target level with `$(inherited)` keeps the project's `DEBUG` / `PC_MEASURE`; do not put it in the project-level `base`,
  which the Measure config overrides. `tools/game.py new --puzzle sort-puzzle` does **not** set it (verified on a scratch
  copy); nothing has been built with it set yet.
- `game.yml`: `puzzle.module: <id>` and the module's checks, run from the game folder by doctor:
  `puzzle.checks: ["tools/sortpuzzle/ref.py --check"]`. Write the path WITHOUT `python3`: doctor splits the string, needs
  the first word to be a file in the game folder and runs a `.py` with its own interpreter (`tools/game.py` `run_cmd`);
  `"python3 tools/…"` fails as "python3 missing". Doctor runs these checks only once level files exist (see NEW-GAME.md
  "Known gaps": a generated-level module does not reach them yet).
- AppModel logs the choice at boot: `[PC][boot] puzzle module <id> (contract v1): boosters …, HUD …`.

## 8. Checklist
- [ ] Capabilities written; every shell gap they hit is on the list in NEW-GAME.md "Known gaps" (or fixed).
- [ ] Core target + product + test target in Package.swift; `tools/core.sh` knows the directory and its import rule.
- [ ] Session follows §2.3; bot plays through the contract only; solver/validator proves every level.
- [ ] Tuning file holds every number; colours are `puzzle.<board>.*` tokens; sprites are `puzzle.<sprite>` slots;
      `python3 tools/skin/build.py --check` and `--check-literals` pass.
- [ ] `ref.py --check` passes and a CI step runs it; the core test compares the Swift against the goldens.
- [ ] App half: plugin, board (async acks, `boardFrame` from its display link), entry; product in app + test deps.
- [ ] `ActivePuzzle` branch + `SWIFT_ACTIVE_COMPILATION_CONDITIONS` on app and test target; `game.yml puzzle.*`
      (`checks` entries start with the script's path, not `python3`).
- [ ] Core and app tests green (Mac or CI), mutation checks CAUGHT.
- [ ] Tutorials (`TutorialStep`s + their strings) and unlock cards, or a written decision that the game has none.
