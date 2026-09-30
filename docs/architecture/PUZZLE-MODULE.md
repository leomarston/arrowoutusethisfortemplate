# The puzzle-module contract (v1.1-candidate: implemented by Arrow Out and SortPuzzle; awaiting CI + review before freezing)

**Goal:** the shell and the meta systems never learn how a puzzle works. A puzzle module provides its levels, its rules
and its board view; everything around it (home, HUD, popups, fail/continue chain, win celebration, economy, boosters
shop, events, the simulated leaderboards, store, tooling) is shared. **Genre-agnostic** by rule (docs/ROADMAP.md D1):
nothing here may assume arrows, tiles, coins, swaps or any other mechanic.

This file describes what is **built**: template phase 2 (v1, the reference module) and phase 5 (v1.1, the second module,
SortPuzzle, §6b). The earlier draft (v0) is in git history; the differences are listed in §8, the v1.1 changes in §8b.

## 1. What the shell really needs from a level (measured on Arrow Out)
The meta systems consume very little. Economy, events, streaks, races and the social world read only *"a level was won or
lost, which level, its difficulty tag, first try or not"* (`EventTypes.WinContext` / `LossContext`). The HUD needs a few
widgets; the fail flow needs an offer. Everything else is the puzzle's own business.

Generic session types (GameCore, `Session/SessionTypes.swift`, frozen, extended **additively** in phase 2 — the
original cases/fields are unchanged and first; APISurfaceTests pins both):

| Type | Phase 2 addition |
|---|---|
| `Phase`, `HoldReason`, `AttemptSetup`, `LevelTag`, `LevelClock`, `TimeCause` | unchanged (already generic) |
| `ContinueOffer.Kind` | + `outOfMoves`, `stuck`; `Kind.lossReason` (outOfTime→timeUp, outOfHearts→hearts, outOfMoves→outOfMoves, stuck→stuck). The failChain keys stay the raw values |
| `ContinueOffer.Grant` | + `addMoves(n)`, `puzzleAction(id:amount:)` (a module's own rescue: "shuffle", "undo 3", "extra tube") |
| `LossReason` | + `outOfMoves`, `stuck` |
| `WinResult` | + `stars: Int?` (nil), `stats: [String: Double]` ([:]); old JSON decodes, an empty `stats` / nil `stars` encodes exactly as before |

Still arrow-shaped and therefore module-private: `SessionEvent`, `SessionAck`, `SessionSnapshot`, `LevelSession`, `RulesTuning`
(ArrowEscape). `MetaRules.StepGrant` (the rules.json fail-chain grants) still has only `addTime` / `refillHearts` / `none`
(pinned; a module with a move limit adds `addMoves` there when it ships). v1.1: a step's `action` grants a module's own
rescue instead (`FailStep.action` → `.puzzleAction(id:amount:)`, §8b).

## 2. The module
Split in two halves because the core packages must not depend on UIKit and `SessionPlan` still lives in ArrowEscape:

**Pure half — GameCore `Session/PuzzleContract.swift`:**
```swift
public protocol PuzzleModule {
    static var id: String { get }                 // "arrow-escape" = game.yml puzzle.module
    static var contractVersion: Int { get }       // PuzzleContract.version (1)
    static var capabilities: PuzzleCapabilities { get }
}

public struct PuzzleCapabilities: Sendable {
    public var failRules: [FailRule]              // .timer, .moves, .hearts(n), .none, .custom(id)
    public var inputs: Set<InputKind>             // .tap, .drag, .swap, .select2, .paint, .multiTouch
    public var boosters: [BoosterSpec]            // HUD order; BoosterSpec(id, effect: BoosterKind, icon: art slot?)
    public var hud: [HUDWidget]                   // .timer, .moves, .hearts, .goals, .progress, .score
    public var zoomable: Bool
    public var multiStageSessions: Bool
    public func booster(_ id: BoosterID) -> BoosterSpec?
}
public enum BoosterKind { case freezeTimer, addTime(Int), addMoves(Int), puzzleAction(String) }
public struct PuzzleStage: Sendable {             // one stage as the shell sees it
    level: Int, tag: LevelTag, timerSeconds: Int?, hearts: Int?, summary: String /* logs */, content: any Sendable /* the module's level */
}
```
(`BoosterKind`, not `BoosterEffect`: that name is C3's economy booster table in `Economy/Boosters.swift`.)

**App half — `App/Contracts/PuzzleBoardContract.swift`:**
```swift
@MainActor protocol PuzzlePlugin: AnyObject {
    var id: String { get }
    var capabilities: PuzzleCapabilities { get }
    func stages(for plan: SessionPlan, args: LaunchArgs) -> [PuzzleStage]?     // nil = a level is missing (no life taken)
    func makeSession(plan: SessionPlan, stages: [PuzzleStage], setup: AttemptSetup, streakActive: Bool) -> any PuzzleSession
    var tutorials: [TutorialStep] { get }                                      // generic steps (GameCore)
    var unlocks: [FeatureUnlock] { get }                                       // "X unlocked!" cards
    func mistakeTargets(_ session: any PuzzleSession, board: any PuzzleBoard) -> [PuzzleTarget]   // bots, -pc.lose hearts
    func warmUpWin() -> @Sendable () -> WinResult?                            // first-win warm-up, run off-main
}
@MainActor protocol PuzzleEntryPoint {
    static func makePlugin(_ app: AppModel) -> any PuzzlePlugin
    static func makeBoard(_ app: AppModel) -> any PuzzleBoard
}
@MainActor enum ActivePuzzle {
    static let entry: any PuzzleEntryPoint.Type = ArrowEscapeEntry.self       // THE ONE LINE A NEW GAME CHANGES
}
```
AppModel builds `puzzle` and `puzzleBoard` from `ActivePuzzle.entry` once at boot and logs
`[PC][boot] puzzle module <id> (contract v1): boosters …, HUD …`. `GameServices` carries `puzzle`, `board: any PuzzleBoard`
and `rules: MetaRules` (the meta half; the puzzle's own rules are the plugin's).

## 3. The session and its outputs
```swift
public protocol PuzzleSession: AnyObject {
    var phase: Phase { get }
    var stage: Int { get }; var stageCount: Int { get }
    var clock: LevelClock { get }     // no timer rule: an idle clock (limit 0, never started, never expires)
    var hearts: Int? { get }          // nil = no hearts rule
    var isFinished: Bool { get }
    func start() -> [SessionOutput]
    func input(_ e: PuzzleInput, at gameTime: Double) -> [SessionOutput]
    func ack(_ a: PuzzleAck) -> [SessionOutput]
    func tick(_ dt: Double) -> [SessionOutput]
    func hold(_ r: HoldReason); func release(_ r: HoldReason)
    func canUseBooster(_ id: BoosterID) -> Bool          // false = nothing to do now (no stock is taken)
    func useBooster(_ id: BoosterID) -> [SessionOutput]  // the caller took the stock
    func acceptContinue() -> [SessionOutput]; func declineContinue() -> [SessionOutput]; func quit() -> [SessionOutput]
    func hint() -> PuzzleTarget?                         // bots, debug jumps
}

public enum SessionOutput: Sendable {
    case meta(MetaEvent)              // the shell acts on these
    case puzzle(any PuzzleEvent)      // opaque: only the module's board reads them
    var metaEvent / puzzleEvent / move   // helpers
}

public enum MetaEvent: Equatable, Sendable {
    case stageLoaded(stage:of:level:), timerArmed(stage:seconds:), timerStarted(stage:), timerAlert(seconds:)
    case timeAdded(seconds:cause:), freezeStarted(seconds:), freezeEnded
    case heartsChanged(left:), movesChanged(left:), mistake, goalProgress([GoalState])
    case boosterUsed(BoosterID), stageCleared(stage:), stageAdvanced(to:)
    case offer(ContinueOffer), continued(ContinueOffer), won(WinResult), lost(LossReason)
}

public protocol PuzzleEvent: Sendable {           // the three generic facts the shell may read (defaults: none)
    var move: PuzzleMove? { get }                   // a resolved player move (target, failed): tap haptic + cue, tutorials, bots
    var hintTargets: [PuzzleTarget]? { get }        // a hint's targets (the hint booster stays inert while they are in play)
    var removedTargets: [PuzzleTarget] { get }      // targets leaving play
}
public protocol PuzzleBeat: Sendable {}           // a board beat the module's rules wait for
public enum PuzzleAck { case introFinished, stageTransitionDone, boardCleared, contact(any PuzzleBeat), beat(any PuzzleBeat) }
public struct PuzzleTarget: Hashable, Comparable, Codable, Sendable { public let raw: Int }   // opaque id of "something to act on"
public enum PuzzleInput: Hashable, Sendable { case tap(PuzzleTarget?), drag(from:to:), swap(_,_), select(_), custom(id:targets:) }
```
**Why `any PuzzleEvent` and not a generic `SessionOutput<E>`:** the Game layer holds one session and one board of the
active module and never inspects puzzle events, it only forwards them. A generic output type would make the controller,
every director, the entry points and their tests generic over the module for no shell benefit. The cost is one
existential box per puzzle event and one `as?` per event in the module's board (a handful per tap, sub-microsecond);
dispatch in the shell stays static (`switch` on `SessionOutput` / `MetaEvent`).

Rules for every module: deterministic from `AttemptSetup.seed` + inputs; no wall clock; rules resolve at the input (the
board animates what already happened); outputs in causal order; a `won`/`lost` is emitted exactly once.

**Shell semantics that depend on outputs** (all generic):
- haptic `.tap` + the tap cue when a batch holds a `move`; `.contact` ack → `heartLost` haptic if the batch holds
  `heartsChanged`, else `bumpContact` (also when the ack returns nothing);
- HUD: `timerArmed/Started`, `heartsChanged`, `continued` (refill → `session.hearts`), `timeAdded`, `stageLoaded` (shows
  `session.hearts`), `offer/won/lost/stageCleared` (timer frozen);
- fail flow: `offer` (first step after `fail.zeroHoldSeconds` for `outOfTime`, `fail.heartsOutDelay` for every other kind),
  `lost`; win: `won` (banked at once), W = `.boardCleared` ack;
- boosters: `timerStarted`, `freezeEnded`, `stageCleared/won/lost`, `stageAdvanced`, a puzzle event's `removedTargets`;
- tutorials: `timerArmed` (stageReady), `timerStarted` (firstTap), a `move` (dismiss), `stageCleared/won/lost`.

## 4. The board (`App/Contracts/PuzzleBoardContract.swift`)
```swift
@MainActor protocol PuzzleBoard: AnyObject {
    var delegate: PuzzleBoardDelegate? { get set }
    var view: UIView { get }
    var inputEnabled: Bool { get set }
    var allowedTargets: Set<PuzzleTarget>? { get set }        // tutorial restriction
    func prepare() async
    func load(_ stage: StageContext)                          // stage, stages, seed, screen, info: PuzzleStage
    func playIntro(_ style: IntroStyle)                       // → .introFinished
    func present(_ outputs: [SessionOutput])                  // the whole batch; the board picks its .puzzle events
    func playStageTransition(to: StageContext)                // → .stageTransitionDone
    func playClearWave()
    func handPoint(for: PuzzleTarget, at: [Double]?) -> CGPoint?   // tutorial fingertip in screen points
    func performTap(on: PuzzleTarget) -> Bool                 // through the real release handler (bots, debug jumps)
    func publishProbe()
    var diagnostics: BoardDiagnostics? { get }                // ripple / present timings, hitches (bench, same-frame proof)
}
@MainActor protocol PuzzleBoardDelegate: AnyObject {          // GameController
    func boardFrame(timestamp:targetTimestamp:)               // the master clock
    func boardInput(_ input: PuzzleInput, touchTimestamp:)    // inside the board's release handler: answer synchronously
    func boardAck(_ ack: PuzzleAck)
    func boardFeedback(_ haptic: Haptic)                      // a visual-only beat's haptic (a burst)
    func boardZoomChanged(scale:)
    var activeSession: (any PuzzleSession)? { get }           // the probe's session half is the board's
}
```
`PuzzleBoardHost` hosts `board.view` edge to edge. The feel budget stays binding for every module: input → session →
`present` synchronously in the board's release handler, one Core Animation transaction; no hitch > 20 ms.

## 5. Boosters, continues and HUD without genre knowledge
- The module **declares** its boosters (`capabilities.boosters`, in HUD order); the HUD corners, the buy popup, stock and
  prices come from the config (rules.json economy). The shell runs `.freezeTimer` itself (the HUD freeze FX + the session's
  clock freeze through `useBooster`); every other kind (`addTime`, `addMoves`, `puzzleAction`) asks `canUseBooster`, takes
  the stock, then `useBooster`. A booster whose outputs carry `hintTargets` stays inert until one of them leaves play.
- The fail chain comes from rules.json `failChain` per `ContinueOffer.Kind` raw value (v1.1: a module may ship a default
  chain for its own kinds, merged under rules.json — rules.json wins for a kind it lists — and a step may grant a module
  action, `FailStep.action`, §8b). The popups (Shell) choose texts by
  kind; today only `outOfTime` / `outOfHearts` have texts — **a module that uses `outOfMoves` / `stuck` must first get their
  strings (13 languages) and the Shell popups' variants**; no new user-visible string was added in phase 2.
- HUD widgets are declared (`capabilities.hud`); today's HUD shows timer + hearts (a module without hearts gets an empty
  hearts row: `HUDWriter.begin(hearts: nil)`). Goal counters (`goalProgress`) have no HUD view yet.

## 6. How Arrow Out maps onto it (the first module)
- **Core (ArrowEscape `Session/ArrowPuzzleSession.swift`):** `ArrowPuzzleSession` wraps `LevelSession` unchanged (every call is
  the same core call as before: `useBooster` = `useBooster(id, hintPolicy: rules.boosters.hintPolicy, freezeFlightFromUse:
  true)`, exactly what the app's BoosterDirector passed). `SessionEvent` → `SessionOutput` 1:1 in order:
  `stageLoaded/timerArmed/timerStarted/timerAlert/timeAdded/freezeStarted/freezeEnded/boosterUsed/stageCleared/stageAdvanced/
  offer/continued/won/lost` → `.meta`, `heartLost(n)` → `.meta(.heartsChanged(left: n))`; `exited, bumped, tapIgnored,
  arrowMarked, keyDispatched, doorOpened, pipeUsed, pipeBroken, counterChanged, counterBroken, elevatorActivated, hintShown`
  stay `SessionEvent`s carried as `.puzzle` (`SessionEvent: PuzzleEvent`: exit = move, bump = failed move, `hintShown` =
  hint targets, an exit removes its unit). `SessionAck: PuzzleBeat` (bumpContact → `.contact`, bumpFinished / doorBurst →
  `.beat`); `lastExitLeftBoard` = `.boardCleared`. `ArrowID` ↔ `PuzzleTarget` (`ArrowID.target`, `ArrowID(target:)`).
  `ArrowEscapeModule: PuzzleModule`: id `arrow-escape`, fail rules `[.timer, .hearts(3)]`, inputs `[.tap]`, boosters
  `freeze` (`.freezeTimer`, 1.6 s flight + 10 s from rules.json) and `hint` (`.puzzleAction("hint")`), HUD `[.timer,
  .hearts]`, zoomable, multi-stage; `makeSession`, `stage(_:)` (a `PuzzleStage` from a `LevelSpec`), `warmUpWin(rules:)`.
  `TutorialScript.step` converts to the generic `TutorialStep`; `TutorialTrigger` / `TutorialDismiss` moved to GameCore.
- **App (`App/Board/ArrowEscapePlugin.swift`):** `ArrowPuzzleBoard` wraps the app-lifetime `BoardEngine` (which keeps its
  arrow-typed `BoardControlling` API for BoardLab and the board tests): it is the engine's `BoardDelegate` while a Play runs
  (`delegate` set = engine claimed, cleared = released), maps released arrow → `.tap(target)`, beats → acks (+ the burst
  haptic for door / pipe / box), outputs → the engine's `[SessionEvent]`, the tutorial fingertip (lattice `at` → screen),
  and supplies the probe's session half (keys unchanged). `ArrowEscapePlugin`: stages from the level library/provider with
  `-pc.timer` / `-pc.hearts`, the session, tutorials/unlocks from the library, mistakes = blocked arrows not red yet.
- **Game layer (`App/Game/*`):** knows no arrow type. Remaining Arrow-flavoured names are data/labels: the audio cue key
  `cues.arrowTap` (the move cue; renaming it is an audio.json key change, phase 3), the `a<n>` prefix of the same-frame log
  line (bench.py parses it), and comments describing the reference game.


## 6b. SortPuzzle: the second module (template phase 5)
A colour-sorting puzzle built only against this contract, to find its gaps: tubes of coloured units, pick a source tube then
a target; the source's top run pours onto an empty tube or onto its own colour, as many units as fit; won when every tube is
empty or full of one colour. **No timer, no hearts:** the one fail is `stuck` (no legal pour left). Original design: the
levels are generated from a seed, the colours are skin tokens, no art files.

| Part | Where | What |
|---|---|---|
| Core (GameCore only) | `Packages/PathCore/Sources/SortPuzzle/` (own product, **not** in the PathCore umbrella) | `SortLevel` (Codable), `SortRules` (sort.json: curve, generator, play, the `stuck` chain), `SortMechanics` (pour rules, stuck = no legal pour), `SortSolver` (bounded iterative DFS over multisets of tubes), `SortGenerator` (seeded deal + solver check; last resort one empty tube per colour: always solvable), `SortPuzzleSession: PuzzleSession`, `SortPuzzleModule: PuzzleModule`, `SortBot` (plays any `PuzzleSession` through the contract only) |
| Independent reference | `apps/mazeout/tools/sortpuzzle/ref.py` | the generator + solver in Python; `--write` makes `Tests/Fixtures/sortpuzzle_goldens.json` from the shipped sort.json (+ a "stress" set pinning the rejection and last-resort paths), `--check` in CI's Linux job |
| Tests | `Packages/PathCore/Tests/SortPuzzleTests`, `Tests/SortPuzzleAppTests.swift` | goldens, solvability, the bot through the contract, stuck/continue/lost exactly once, boosters; app: plugin + real board headless, the unchanged GameController playing a sort level to the win panel and a stuck offer paid through the shell |
| App half | `App/Puzzles/SortPuzzle/` (globbed by project.yml's `App` source; the app links the `SortPuzzle` product) | `SortPuzzlePlugin`, `SortPuzzleBoard` (UIKit + Core Animation, sizes/durations from sort.json `board.*`, colours from skin/colors.json `puzzle.sortBoard.*`), `SortPuzzleEntry` |
| Data | `App/Resources/Tuning/sort.json` | levels (salt, curve, tags), play (hint budget, extra tubes), `failChain.stuck`, `board.*` |

Mapping onto the contract:
- **capabilities:** fail rules `[.custom("stuck")]`, inputs `[.select2, .drag]`, boosters `undo` (`.puzzleAction("undo")`) and
  `extraTube` (`.puzzleAction("extraTube")`, `play.maxExtraTubes` per stage), HUD `[.progress]`, not zoomable, multi-stage.
- **input:** the board sends `.select(tube)`; the session keeps the pick (`selected` / `deselected` events), the second pick
  pours (`poured`, a move) or is refused (`refused`, a failed move: the tap haptic, the autoplayer's mistake). `.tap(t)` is
  the same pick (LevelFlow's fallback when `performTap` returns false), `.drag(from:to:)` both picks.
- **untimed:** an idle `LevelClock(limit: 0)`; `timerArmed(stage, seconds: 0)` at ready, `timerStarted(stage)` at the
  stage's first real pick (tutorials' "first tap"); `tick` returns nothing. `hearts` is nil.
- **progress:** `goalProgress([GoalState(id: "sorted", current: complete tubes, target: colours)])` at ready and on change.
- **fail:** a pour that leaves no legal pour opens `offer(stuck)`; the default chain (sort.json) grants
  `.puzzleAction(id: "extraTube", amount: 1)`; still stuck after a grant → the next step; declined → `lost(.stuck)`.
- **win:** decided at the pour (`won` / `stageCleared`); the board acks `.boardCleared` once the pour has landed (W).
- **hint():** the solver's plan from the current tubes (`play.hintBudget`), as the next pick: its source, then its target;
  a different lifted tube → that tube (picking it again drops it). The plan is kept while the player follows it.

What the second module found (the v1.1 changes are in §8b; these are **shell work before a sort game can ship**, not
contract changes — the contract already carries the information):
- HUD: `HUDView` always shows the timer pill (a frozen "0:00" for an untimed module) and has no view for `.progress` /
  `goalProgress` (nor `.moves` / `.goals`). It must honour `capabilities.hud`.
- Popups: a `stuck` offer gets the Out of Time! layout and texts (`OutOfTimePopup` / `ContinuePopup` pick "time" for every
  kind but `outOfHearts`). `stuck` / `outOfMoves` need their strings (13 languages) and variants.
- Boosters: `undo` / `extraTube` need rules.json economy entries (stock, price), BoosterBuyPopup texts and corner art
  (`BoosterSpec.icon` slots).
- The Play's frame-driven services (PerfMonitor, LatencyProbe) are fed by the arrow engine's display link only; AppModel
  still builds the arrow engine and level library for every game. A non-arrow game's boot should not.
- No tutorials / unlock cards for the module yet (content: strings + a tutorials file).

## 7. Checks the contract must pass before v1 is frozen
1. ArrowEscape implements it with no behaviour change: core tests (incl. `PuzzleContractTests`: the wrapped session emits the
   same events in the same order as `LevelSession`), app unit tests (GameControllerTests / GameG2Tests drive the generic
   controller through ArrowPuzzleBoard's real translation), UI tests, benches and captures unchanged. **Status: written
   without a Swift toolchain; CI (core + app build + unit tests) is the first compile.** UI tests / bench / captures need
   the Mac.
2. Paper designs of three unlike genres fit without new shell code: a **select-then-target** puzzle with no timer and a
   "stuck" fail (sorting), a **swap + cascade** puzzle with a move limit and goals (match-3), a **no-fail progress** puzzle
   (colouring). Known gaps found while building: the HUD has no moves / goals widgets; `outOfMoves` / `stuck` popups have no
   texts; `MetaRules.StepGrant` has no `addMoves`; `SessionPlan` (and its `hearts: reset|carry`) still lives in ArrowEscape.
3. A second real module ships through the whole pipeline (phase 5); its lessons produce contract v1.1. **Status:**
   SortPuzzle (§6b) is built through the contract with one additive contract change (§8b); it is compiled into the app and
   tested (core + app unit tests, CI) while ArrowEscape stays active; the shell gaps listed in §6b stand between it and a
   shipped game. The known gaps of item 2 that the sort module needed are resolved (`stuck` grants) or listed there.

## 8. Differences from the v0 draft
- `PuzzleModule` is split: pure `PuzzleModule` (id, version, capabilities) in GameCore + the app's `PuzzlePlugin` /
  `PuzzleEntryPoint` (content, sessions, board). v0's `levels(_:)`, `SessionPlan<Level>`, `makeBot`, `mechanicUnlocks`,
  `tutorials` statics became plugin members or stayed in the module (`mistakeTargets` + `session.hint()` are the bot).
- The generic ack is `PuzzleAck` (v0 reused the name `SessionAck`, which is ArrowEscape's frozen type); `contact` is its
  own case (the shell's contact haptic).
- `hold(_:)` / `release(_:)` instead of `hold(_, on)`; `ack` takes no game time (Arrow Out's rules never needed it);
  `canUseBooster` added; `useBooster` returns `[SessionOutput]` (not optional); `snapshot` is module-private (the probe's
  session half is the board's, through `activeSession`).
- `clock` is non-optional (an idle clock for untimed modules); `timerArmed` / `timerStarted` keep their `stage`.
- `StageContext` carries the stage's `PuzzleStage` (with the module's level) instead of a module-typed context.

## 8b. Contract v1.1 (template phase 5, from SortPuzzle; all additive, ArrowEscape's behaviour unchanged)
`PuzzleContract.version` stays 1: it names the breaking version, and nothing here breaks a v1 module.
1. **`MetaRules.FailStep.action: String?`** (+ `init(price:grant:amount:warning:onlyWithStreak:action:)`): a fail-chain step
   may grant a module's own rescue. With an action, `offerGrant` is `.puzzleAction(id: action, amount: amount)` (the v1
   `ContinueOffer.Grant` case); without one (every step of rules.json today) nothing changes: decoding, grants and encoding
   (no `action` key) are as before. Why: `StepGrant` (addTime / refillHearts / none) is pinned by APISurfaceTests, and a
   select-then-target puzzle's continue is "one more tube", not time or hearts. Tests: `ContractV11Tests`.
2. **Module default chains:** a module may carry default `failChain` entries for the kinds only it uses (SortPuzzle:
   `SortRules.failChain["stuck"]`, sort.json); `SortRules.meta(over:)` adds them to rules.json's `MetaRules` only for a kind
   rules.json does not list. A game tunes them in its own data; rules.json wins.
3. **Modules are packages, selected at compile time:** every module's app half is compiled in (`App/Puzzles/<Module>/`),
   its core is its own package product (not re-exported by the PathCore umbrella, so its names never collide with the
   reference module's); `ActivePuzzle.entry` is still the one line, now `#if PC_PUZZLE_SORT … #else ArrowEscapeEntry #endif`
   so a build setting (SWIFT_ACTIVE_COMPILATION_CONDITIONS) picks the module without editing the file.
4. **Semantics made explicit** (no code change; both modules follow them):
   - a board acks `.introFinished`, `.boardCleared`, `.stageTransitionDone` **later than the call that caused them**, never
     synchronously inside `playIntro` / `present` / `playStageTransition` (LevelFlow calls `playIntro` before
     `session.start()`: a synchronous intro ack would reach a session that has not started);
   - a board that is not the arrow engine drives the Play's master clock itself (`boardFrame` on every display-link frame
     while it is on screen); SortPuzzleBoard keeps its own beat clock so tests can advance it headless;
   - `performTap(on:)` returns false while input is closed; the caller then sends `.tap(target)` to the session, so every
     module accepts `.tap` for its primary pick;
   - an untimed module: an idle clock, `timerArmed(seconds: 0)` at ready, `timerStarted` at the stage's first real input
     (tutorials' "first tap"), nothing from `tick`, `hearts` nil, `WinResult.timeLeft` / `heartsLeft` 0 and its own numbers
     in `WinResult.stats`;
   - select-then-target input: the pick is the session's state; `hint()` returns the next pick (so bots and debug jumps
     that only tap `hint()` work unchanged).
