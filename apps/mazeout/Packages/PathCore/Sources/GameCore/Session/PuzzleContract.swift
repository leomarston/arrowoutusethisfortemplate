import Foundation

// Template phase 2 (docs/architecture/PUZZLE-MODULE.md, contract v1-candidate). The genre-agnostic contract between a
// puzzle module and everything around it (the app's Game layer: fan-out, HUD, fail chain, win, boosters, tutorials,
// unlock cards, events, the simulated world). Nothing here names a mechanic: a module's own vocabulary (arrows, tiles,
// tubes, cells …) travels as opaque `PuzzleEvent` / `PuzzleBeat` values that only the module's own board reads, plus
// `PuzzleTarget`s (an opaque integer id of "something the player can act on").
//
// Design (why an existential and not a generic associated type): the Game layer holds ONE session and ONE board of the
// active module and never looks inside the puzzle's events, it only forwards them to the board. `SessionOutput.puzzle`
// therefore carries `any PuzzleEvent`; the module's board casts it back to its own type (one metadata compare per event,
// a handful of events per tap) and the shell reads the few generic facts it needs through the `PuzzleEvent` requirements
// (a resolved move, a hint's targets, targets leaving play). A generic `SessionOutput<E>` would force the whole Game layer
// (controller, every director, the entry points and their tests) to be generic over the module for no shell benefit.

// MARK: - Targets and inputs

/// Something on the board the player can act on (an arrow, a tube, a tile, a cell …). Opaque to the shell: only the module
/// gives the number a meaning. Used by inputs, hints, tutorials (hand + allowed targets), bots and UI tests.
public struct PuzzleTarget: Hashable, Comparable, Codable, Sendable, CustomStringConvertible {
    public let raw: Int
    public init(_ raw: Int) { self.raw = raw }
    public static func < (a: PuzzleTarget, b: PuzzleTarget) -> Bool { a.raw < b.raw }
    public var description: String { "t\(raw)" }
}

/// The input styles a module can declare (`PuzzleCapabilities.inputs`).
public enum InputKind: String, Codable, Sendable, CaseIterable {
    case tap, drag, swap, select2, paint, multiTouch
}

/// One player input, already hit-tested by the module's board (the shell never hit-tests).
public enum PuzzleInput: Hashable, Sendable {
    /// A tap on a target; nil = on nothing (it may still start the clock, depending on the rules).
    case tap(PuzzleTarget?)
    case drag(from: PuzzleTarget, to: PuzzleTarget?)
    case swap(PuzzleTarget, PuzzleTarget)
    /// select-then-target puzzles: the first pick (the second is another `.select`).
    case select(PuzzleTarget)
    case custom(id: String, targets: [PuzzleTarget])

    public var kind: InputKind {
        switch self {
        case .tap: return .tap
        case .drag: return .drag
        case .swap: return .swap
        case .select: return .select2
        case .custom: return .multiTouch
        }
    }

    /// The input's primary target (logs, the same-frame proof).
    public var target: PuzzleTarget? {
        switch self {
        case .tap(let t): return t
        case .drag(let from, _): return from
        case .swap(let a, _): return a
        case .select(let t): return t
        case .custom(_, let ts): return ts.first
        }
    }
}

/// A player's move as the rules resolved it (reported by a `PuzzleEvent`).
public struct PuzzleMove: Hashable, Sendable {
    public var target: PuzzleTarget
    /// The rules refused the move on the board (it bounced, it was an illegal swap …): still a move (the tap haptic, a
    /// tutorial's "any tap"), counted as a mistake by bots and logs.
    public var failed: Bool
    public init(target: PuzzleTarget, failed: Bool) { self.target = target; self.failed = failed }
}

// MARK: - Opaque puzzle vocabulary

/// A module's own session event (exits, swaps, pours, cascades …). Only the module's board interprets it; the shell reads
/// the three generic projections below (all optional: the defaults say "nothing of the kind").
public protocol PuzzleEvent: Sendable {
    /// The player's resolved move this event reports (the tap haptic and sound, tutorials, bots); nil = not a move.
    var move: PuzzleMove? { get }
    /// Targets a hint highlights (the hint booster's result); nil = not a hint.
    var hintTargets: [PuzzleTarget]? { get }
    /// Targets this event takes out of play (a hinted target leaving ends its hint).
    var removedTargets: [PuzzleTarget] { get }
}

extension PuzzleEvent {
    public var move: PuzzleMove? { nil }
    public var hintTargets: [PuzzleTarget]? { nil }
    public var removedTargets: [PuzzleTarget] { [] }
}

/// A presentation-timed fact of the module's board that its rules wait for (an impact frame, a burst …).
public protocol PuzzleBeat: Sendable {}

/// What the board reports back to the session (the core never sleeps: the board says when a visual beat landed).
public enum PuzzleAck: Sendable {
    /// The stage's build-in finished: the stage is ready (input may open).
    case introFinished
    /// A multi-stage session's transition to the next stage finished.
    case stageTransitionDone
    /// The stage's last piece left the board (W: the clear wave, the celebration or the stage transition start here).
    case boardCleared
    /// A move's impact frame (a mistake may cost here): the shell plays the contact haptic.
    case contact(any PuzzleBeat)
    /// Any other beat the module's rules wait for.
    case beat(any PuzzleBeat)
}

// MARK: - Generic meta events

/// A goal counter for the HUD ("12/20 red", "3/5 boxes", "72 % painted").
public struct GoalState: Hashable, Codable, Sendable {
    public var id: String
    public var current: Int
    public var target: Int
    public init(id: String, current: Int, target: Int) { self.id = id; self.current = current; self.target = target }
}

/// Everything the shared systems need from a session, nothing more (PUZZLE-MODULE.md §3).
public enum MetaEvent: Equatable, Sendable {
    case stageLoaded(stage: Int, of: Int, level: Int)
    /// The stage is ready: the HUD shows the timer's limit, frozen (seconds 0 without a timer rule).
    case timerArmed(stage: Int, seconds: Int)
    /// The stage's first move started the level clock.
    case timerStarted(stage: Int)
    case timerAlert(seconds: Int)
    case timeAdded(seconds: Int, cause: TimeCause)
    case freezeStarted(seconds: Double)
    case freezeEnded
    /// A mistake cost a heart (the contact frame): `left` hearts remain.
    case heartsChanged(left: Int)
    case movesChanged(left: Int)
    /// A mistake that costs nothing countable (no hearts / moves rule).
    case mistake
    case goalProgress([GoalState])
    case boosterUsed(BoosterID)
    case stageCleared(stage: Int)
    case stageAdvanced(to: Int)
    case offer(ContinueOffer)
    case continued(ContinueOffer)
    case won(WinResult)
    case lost(LossReason)
}

/// One item of the session's ordered output: a meta event the shell acts on, or the module's own event for its board.
public enum SessionOutput: Sendable {
    case meta(MetaEvent)
    case puzzle(any PuzzleEvent)

    public var metaEvent: MetaEvent? {
        if case .meta(let m) = self { return m }
        return nil
    }

    public var puzzleEvent: (any PuzzleEvent)? {
        if case .puzzle(let p) = self { return p }
        return nil
    }

    /// The resolved move this output reports (only puzzle events report moves).
    public var move: PuzzleMove? {
        if case .puzzle(let p) = self { return p.move }
        return nil
    }
}

// MARK: - Capabilities

/// How a level can be lost (the fail chain per rule comes from the config: rules.json `failChain`).
public enum FailRule: Hashable, Sendable {
    /// A level clock (the seconds come from each level).
    case timer
    case moves
    case hearts(Int)
    case none
    case custom(String)
}

/// The HUD widgets a module shows (their art and tokens come from the skin).
public enum HUDWidget: String, Codable, Sendable, CaseIterable {
    case timer, moves, hearts, goals, progress, score
}

/// What a booster does. The shell runs `freezeTimer` itself (the HUD freeze + the session's clock freeze); every other
/// effect is handed to `PuzzleSession.useBooster`.
public enum BoosterKind: Hashable, Sendable {
    case freezeTimer
    case addTime(Int)
    case addMoves(Int)
    case puzzleAction(String)
}

/// A booster the module declares (its shop price, starting stock and buy popup come from the config).
public struct BoosterSpec: Hashable, Sendable {
    public var id: BoosterID
    public var effect: BoosterKind
    /// The skin's art slot of the HUD corner / shop icon (nil = the skin's default for `id`).
    public var icon: String?
    public init(id: BoosterID, effect: BoosterKind, icon: String? = nil) { self.id = id; self.effect = effect; self.icon = icon }
}

public struct PuzzleCapabilities: Sendable {
    public var failRules: [FailRule]
    public var inputs: Set<InputKind>
    /// In HUD order (left corner first).
    public var boosters: [BoosterSpec]
    public var hud: [HUDWidget]
    /// The board zooms and pans (the module's board owns the gesture container).
    public var zoomable: Bool
    /// "Levels 1-4"-style sessions of several boards.
    public var multiStageSessions: Bool

    public init(failRules: [FailRule], inputs: Set<InputKind>, boosters: [BoosterSpec], hud: [HUDWidget], zoomable: Bool,
                multiStageSessions: Bool) {
        self.failRules = failRules; self.inputs = inputs; self.boosters = boosters; self.hud = hud; self.zoomable = zoomable
        self.multiStageSessions = multiStageSessions
    }

    public func booster(_ id: BoosterID) -> BoosterSpec? { boosters.first { $0.id == id } }
}

// MARK: - Stages

/// One stage of a session as the shell sees it: the numbers the HUD, the logs and the directors need, and the module's own
/// level (`content`, read back only by the module's session and board).
public struct PuzzleStage: Sendable {
    public var level: Int
    public var tag: LevelTag
    /// The timer rule's limit; nil = no timer.
    public var timerSeconds: Int?
    /// The hearts rule's count; nil = no hearts.
    public var hearts: Int?
    /// A short description for the logs ("12 arrows").
    public var summary: String
    public var content: any Sendable

    public init(level: Int, tag: LevelTag, timerSeconds: Int?, hearts: Int?, summary: String, content: any Sendable) {
        self.level = level; self.tag = tag; self.timerSeconds = timerSeconds; self.hearts = hearts; self.summary = summary
        self.content = content
    }
}

// MARK: - The session

/// A Play's rules: pure, deterministic from `AttemptSetup.seed` + inputs, no wall clock, no timers (time enters only through
/// `tick`). Outputs come back in causal order and the shell forwards every batch unchanged (board first). A `won` / `lost`
/// is emitted exactly once. Class-bound: the shell holds one per Play on the main thread.
public protocol PuzzleSession: AnyObject {
    var phase: Phase { get }
    /// 0-based current stage and the session's stage count.
    var stage: Int { get }
    var stageCount: Int { get }
    /// The level clock. A module without a timer rule returns an idle clock (limit 0, never started: it never expires)
    /// and leaves `.timer` out of its HUD widgets.
    var clock: LevelClock { get }
    /// Hearts left (nil = no hearts rule).
    var hearts: Int? { get }
    var isFinished: Bool { get }

    func start() -> [SessionOutput]
    func input(_ e: PuzzleInput, at gameTime: Double) -> [SessionOutput]
    func ack(_ a: PuzzleAck) -> [SessionOutput]
    func tick(_ dt: Double) -> [SessionOutput]
    /// Clock holds (they stack; the clock runs only with none).
    func hold(_ r: HoldReason)
    func release(_ r: HoldReason)
    /// The booster would do something now (no stock is taken when it would not).
    func canUseBooster(_ id: BoosterID) -> Bool
    /// The caller has already taken the stock.
    func useBooster(_ id: BoosterID) -> [SessionOutput]
    /// The caller has already charged `offer.price`.
    func acceptContinue() -> [SessionOutput]
    func declineContinue() -> [SessionOutput]
    func quit() -> [SessionOutput]
    /// A good next target (bots, debug jumps); nil = none right now.
    func hint() -> PuzzleTarget?
}

// MARK: - The module

/// The contract version this file describes (PUZZLE-MODULE.md).
public enum PuzzleContract {
    public static let version = 1
}

/// The pure half of a puzzle module (its id, contract version and capabilities). The app half — the session factory over
/// the module's content, the board, tutorials, unlock cards, bot helpers — is the app's `PuzzlePlugin`.
public protocol PuzzleModule {
    /// Stable id ("arrow-escape"), the `puzzle.module` of game.yml.
    static var id: String { get }
    static var contractVersion: Int { get }
    static var capabilities: PuzzleCapabilities { get }
}

// MARK: - Tutorials (generic form)

/// One tutorial step as the shell plays it (caption + hand + dismissal + optional input restriction). Modules convert their
/// own tutorial data into this form (their hand points at a `PuzzleTarget`; the board turns it into a screen point).
public struct TutorialStep: Sendable, Equatable {
    public struct Hand: Sendable, Equatable {
        public var target: PuzzleTarget
        /// The fingertip in the module's own board coordinates (the board converts it), nil = the target's anchor.
        public var at: [Double]?
        public init(target: PuzzleTarget, at: [Double]? = nil) { self.target = target; self.at = at }
    }

    public var id: TutorialID
    /// The stage's level number.
    public var level: Int
    /// 0-based stage within the session.
    public var stage: Int
    public var trigger: TutorialTrigger
    /// Strings-table key of the caption, nil = hand only.
    public var caption: String?
    public var hand: Hand?
    public var dismiss: TutorialDismiss
    public var holdTimer: Bool
    /// Input restriction while the step is up; nil = every target.
    public var allowedTargets: [PuzzleTarget]?

    public init(id: TutorialID, level: Int, stage: Int = 0, trigger: TutorialTrigger = .stageReady, caption: String? = nil,
                hand: Hand? = nil, dismiss: TutorialDismiss = .anyTap, holdTimer: Bool = false,
                allowedTargets: [PuzzleTarget]? = nil) {
        self.id = id; self.level = level; self.stage = stage; self.trigger = trigger; self.caption = caption
        self.hand = hand; self.dismiss = dismiss; self.holdTimer = holdTimer; self.allowedTargets = allowedTargets
    }
}
