# The puzzle-module contract (DRAFT v0, for review before phase 2)

**Goal:** the shell and the meta systems never learn how a puzzle works. A puzzle module is a Swift package that provides
its levels, its rules and its board view; everything around it (home, HUD, popups, fail/continue chain, win celebration,
economy, boosters shop, events, the simulated leaderboards, store, tooling) is shared. **Genre-agnostic** by rule
(docs/ROADMAP.md D1): nothing here may assume arrows, tiles, coins, swaps or any other mechanic.

## 1. What the shell really needs from a level (measured on Arrow Out)
The meta systems consume very little. Economy, events, streaks, races and the social world read only *"a level was won or
lost, which level, its difficulty tag, first try or not"* (`EventTypes.WinContext` / `LossContext`). The HUD needs a few
widgets; the fail flow needs an offer. Everything else is the puzzle's own business.

Today's frozen types (`Packages/PathCore/Sources/PathCore/Session/SessionTypes.swift`) are **already mostly generic**:
`Phase` (intro → ready → playing → stageClear → offer → won/lost), `HoldReason`, `AttemptSetup`, `LevelTag`
(normal/hard/superHard). The arrow leaks are small and precise:

| Type | Arrow-specific part | Generic replacement |
|---|---|---|
| `SessionAck` | `bumpContact(ArrowID)`, `doorBurst(ObstacleID)`, `lastExitLeftBoard` | `introFinished`, `stageTransitionDone`, `boardCleared` (was lastExitLeftBoard) + `puzzle(PuzzleBeat)` (opaque to the shell) |
| `ContinueOffer.Kind` / `.Grant` | `outOfTime`, `outOfHearts` / `addTime`, `refillHearts` | `outOfTime`, `outOfHearts`, `outOfMoves`, `stuck`, `custom(id)` / `addTime(s)`, `refillHearts(n)`, `addMoves(n)`, `puzzleAction(id, amount)` (e.g. "shuffle", "undo 3", "extra tube") |
| `LossReason` | `timeUp`, `hearts` | + `outOfMoves`, `stuck` |
| `WinResult` | `timeLeft`, `heartsLeft`, `bumps` | keep `levels`, `tag`, `firstTry`, `reward`; + `stars: Int?`, `stats: [String: Double]` (timeLeft, movesLeft, mistakes, …) |
| `SessionEvent` | `exited`, `bumped`, `keyDispatched`, `pipeUsed`, … | split: generic `MetaEvent` + opaque `PuzzleEvent` (§3) |
| `BoardControlling` (App) | `Set<ArrowID>`, `tapPoint(of: ArrowID)`, arrow beats | `PuzzleBoard` (§4) |
| `BoosterID` "freeze"/"hint" hard-coded in LevelFlow | — | boosters declared by the module (§5) |

## 2. The module
```swift
public protocol PuzzleModule {
    associatedtype Level: Codable & Sendable
    static var id: String { get }                          // "arrow-escape", stable, used in game.yml
    static var contractVersion: Int { get }                // this document's version the module implements
    static var capabilities: PuzzleCapabilities { get }

    // content: authored levels from the bundle, generated ones after them (both deterministic)
    static func levels(_ ctx: ContentContext) -> any LevelProviding<Level>

    // rules: pure, deterministic, no timers, headless-testable (a bot can play it in simulated time)
    static func makeSession(_ plan: SessionPlan<Level>, setup: AttemptSetup, tuning: PuzzleTuning) -> any PuzzleSession

    // presentation: the module's own board (UIKit / Core Animation / SpriteKit / Metal — its choice)
    @MainActor static func makeBoard(_ ctx: BoardContext) -> any PuzzleBoard

    // optional
    static var tutorials: [TutorialScript] { get }         // steps keyed by level/stage, with allowed targets
    static var mechanicUnlocks: [MechanicUnlock] { get }   // "X unlocked!" cards at a mechanic's first level
    static func makeBot(_ session: any PuzzleSession) -> (any PuzzleBot)?   // tests, soak, screenshots
}

public struct PuzzleCapabilities: Sendable {
    public var failRules: [FailRule]        // .timer(seconds per level from the level file), .moves, .hearts(n), .none, .custom(id)
    public var inputs: Set<InputKind>       // .tap, .drag, .swap, .select2 (source → target), .paint, .multiTouch
    public var boosters: [BoosterSpec]      // id, icon art slot, effect kind (.freezeTimer, .hint, .puzzleAction(id))
    public var hud: [HUDWidget]             // .timer, .moves, .hearts, .goals, .progress, .score
    public var zoomable: Bool               // the shell's pinch/pan container, or the board handles its own
    public var multiStageSessions: Bool     // "Levels 1-4"-style sessions of several boards
}
```

## 3. The session and its events
```swift
public protocol PuzzleSession: AnyObject {
    var phase: Phase { get }
    func start() -> [SessionOutput]
    func input(_ e: PuzzleInput, at gameTime: Double) -> [SessionOutput]   // .tap(target), .drag(from,to), .swap(a,b), …
    func ack(_ a: SessionAck, at gameTime: Double) -> [SessionOutput]      // the board says a visual beat landed
    func tick(_ dt: Double) -> [SessionOutput]                             // the only time input
    func hold(_ r: HoldReason, _ on: Bool)
    func useBooster(_ id: BoosterID) -> [SessionOutput]?                    // nil = not usable now
    func acceptContinue() -> [SessionOutput]; func declineContinue() -> [SessionOutput]
    func hint() -> PuzzleTarget?                                           // bots, tutorials, the hint booster
    var snapshot: SessionSnapshot { get }                                  // the probe for UI tests
}

public enum SessionOutput {
    case meta(MetaEvent)          // the shell acts on these (below)
    case puzzle(PuzzleEvent)      // opaque: only this module's board reads them (exits, swaps, pours, cascades, …)
}

public enum MetaEvent {           // everything the shared systems need, nothing more
    case stageLoaded(stage: Int, of: Int, level: Int)
    case timerArmed(seconds: Int), timerStarted, timeAdded(Int), timerAlert(Int)
    case movesChanged(left: Int), heartsChanged(left: Int), mistake
    case goalProgress([GoalState])           // e.g. "12/20 red", "3/5 boxes", "72 % painted"
    case boosterUsed(BoosterID), freezeStarted(Double), freezeEnded
    case stageCleared(stage: Int), stageAdvanced(to: Int)
    case offer(ContinueOffer), continued(ContinueOffer)
    case won(WinResult), lost(LossReason)
}
```
Rules for every module: deterministic from `AttemptSetup.seed` + inputs; no wall clock; rules resolve at the input
(the board animates what already happened); a `won`/`lost` is emitted exactly once; the bot can finish every authored
level.

## 4. The board
```swift
@MainActor public protocol PuzzleBoard: AnyObject {
    var view: UIView { get }                                   // the shell hosts it (and the pinch/pan container if zoomable)
    var delegate: PuzzleBoardDelegate? { get set }             // boardFrame(dt) master clock, boardInput(PuzzleInput), boardAck(SessionAck)
    func prepare() async                                       // warm-up behind Loading (shaders, sprites, glyphs)
    func load(_ stage: StageContext)                           // build the stage (hidden), sized to the play rect
    func playIntro(_ style: IntroStyle)                        // → ack(.introFinished)
    func present(_ outputs: [SessionOutput])                   // animate what the session decided, in the same frame
    func playStageTransition(to: StageContext)                 // → ack(.stageTransitionDone)
    func setPaused(_ paused: Bool); func setInputEnabled(_ on: Bool)
    func highlight(_ target: PuzzleTarget?)                    // hint / tutorial hand
    func screenPoint(of target: PuzzleTarget) -> CGPoint?      // for the bot, tutorials and UI tests
    func probe() -> [String: Any]                              // UI-test state
}
```
The feel budget stays binding for every module: input → session → `present` synchronously in one frame; no hitch
> 20 ms (docs/lessons, SPEC-architecture §10). The shell never sits between the finger and the first moving pixel.

## 5. Boosters, continues and HUD without genre knowledge
- The module **declares** its boosters; the shop, buy popup, HUD corner, starting stock and prices come from `game.yml`.
  Effects the shell can run itself: `freezeTimer(seconds)`, `addTime`, `addMoves`; everything else is
  `puzzleAction(id)` handed to `session.useBooster`.
- The fail chain comes from `game.yml` per fail rule (price, grant, how many steps, streak/lives warnings) — the
  popups are generic ("Out of Moves!", "+5 moves for 900") with texts per `ContinueOffer.Kind`.
- HUD widgets are data: which widgets, in which slot, with which art slot and tokens. Goal counters show an art slot +
  "n/m" and animate on `goalProgress`.

## 6. How Arrow Out maps onto it (the first module, `Puzzles/ArrowEscape`)
Level = today's `LevelSpec`; session = `LevelSession` wrapped to emit `SessionOutput`; `exited`/`bumped`/`keyDispatched`/…
become `PuzzleEvent`s; `bumpContact`/`doorBurst` become `PuzzleBeat`s; `lastExitLeftBoard` → `boardCleared`; fail rules
`[.timer, .hearts(3)]`; boosters `freeze` (`freezeTimer(10)` after a 1.6 s flight) and `hint` (`puzzleAction("hint")`,
the board zooms and highlights); HUD `[.timer, .hearts]`; board = today's `BoardEngine` behind `PuzzleBoard`.

## 7. Checks the contract must pass before v1 is frozen
1. ArrowEscape implements it with no behaviour change (all tests, benches and captures unchanged).
2. Paper designs of three unlike genres fit without new shell code: a **select-then-target** puzzle with no timer and a
   "stuck" fail (sorting), a **swap + cascade** puzzle with a move limit and goals (match-3), a **no-fail progress**
   puzzle (colouring). Anything that does not fit changes the contract, not the genre.
3. A second real module ships through the whole pipeline (phase 5); its lessons produce contract v1.1.
