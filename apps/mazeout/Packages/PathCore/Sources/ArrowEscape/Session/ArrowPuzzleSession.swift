import Foundation
import GameCore

// Template phase 2 (docs/architecture/PUZZLE-MODULE.md §6): ArrowEscape behind the generic puzzle contract. `LevelSession`
// (and its frozen `SessionEvent` / `SessionAck`, pinned by APISurfaceTests and every core test) stays exactly as it is; this
// file wraps it:
//  - `SessionEvent` → `SessionOutput`, 1:1 and in order: the generic events become `.meta(MetaEvent)`, the arrow ones
//    (exits, bumps, marks, keys, doors, pipes, counters, elevators, ignored taps, the hint) stay `SessionEvent` values
//    carried as `.puzzle` for the board. `heartLost(n)` → `.meta(.heartsChanged(left: n))`.
//  - `SessionAck` doubles as the module's `PuzzleBeat` (bump contact / finished, door burst); the generic acks map to
//    `introFinished`, `stageTransitionDone` and `lastExitLeftBoard` (= `.boardCleared`).
//  - `ArrowID` ↔ `PuzzleTarget` (the same integer).
//  - boosters: the app's BoosterDirector always used the rules' hint policy and `freezeFlightFromUse: true` (SPEC.md rulings
//    30 + 31); the wrapper does the same, so a booster use is the same core call as before.

// MARK: - ids

extension ArrowID {
    /// The generic target of this arrow (the same integer).
    public var target: PuzzleTarget { PuzzleTarget(raw) }
    public init(target: PuzzleTarget) { self.init(target.raw) }
}

// MARK: - events

extension SessionEvent: PuzzleEvent {
    /// Exits and bumps are the player's resolved moves (a bump is a failed one).
    public var move: PuzzleMove? {
        switch self {
        case .exited(let plan): return PuzzleMove(target: plan.tapped.target, failed: false)
        case .bumped(let plan): return PuzzleMove(target: plan.arrow.target, failed: true)
        default: return nil
        }
    }

    public var hintTargets: [PuzzleTarget]? {
        if case .hintShown(let ids) = self { return ids.map(\.target) }
        return nil
    }

    /// An exit takes its whole unit (a tape bundle) off the board.
    public var removedTargets: [PuzzleTarget] {
        if case .exited(let plan) = self { return plan.unit.map(\.target) }
        return []
    }

    /// This event as the generic contract carries it.
    public var output: SessionOutput {
        switch self {
        case .stageLoaded(let stage, let of, let level): return .meta(.stageLoaded(stage: stage, of: of, level: level))
        case .timerArmed(let stage, let seconds): return .meta(.timerArmed(stage: stage, seconds: seconds))
        case .timerStarted(let stage): return .meta(.timerStarted(stage: stage))
        case .heartLost(let remaining): return .meta(.heartsChanged(left: remaining))
        case .timerAlert(.threshold(let n)): return .meta(.timerAlert(seconds: n))
        case .timeAdded(let seconds, let cause): return .meta(.timeAdded(seconds: seconds, cause: cause))
        case .freezeStarted(let seconds): return .meta(.freezeStarted(seconds: seconds))
        case .freezeEnded: return .meta(.freezeEnded)
        case .boosterUsed(let b): return .meta(.boosterUsed(b))
        case .stageCleared(let stage): return .meta(.stageCleared(stage: stage))
        case .stageAdvanced(let to): return .meta(.stageAdvanced(to: to))
        case .offer(let o): return .meta(.offer(o))
        case .continued(let o): return .meta(.continued(o))
        case .won(let r): return .meta(.won(r))
        case .lost(let r): return .meta(.lost(r))
        case .exited, .bumped, .tapIgnored, .arrowMarked, .keyDispatched, .doorOpened, .pipeUsed, .pipeBroken,
             .counterChanged, .counterBroken, .elevatorActivated, .hintShown:
            return .puzzle(self)
        }
    }

    /// A batch, in order.
    public static func outputs(_ events: [SessionEvent]) -> [SessionOutput] { events.map(\.output) }
}

extension SessionAck: PuzzleBeat {}

extension SessionOutput {
    /// The arrow board's events of a batch (the `.puzzle` items that are `SessionEvent`s), in order.
    public static func arrowEvents(_ outputs: [SessionOutput]) -> [SessionEvent] {
        outputs.compactMap { o -> SessionEvent? in
            if case .puzzle(let p) = o { return p as? SessionEvent }
            return nil
        }
    }
}

// MARK: - the session

/// `LevelSession` as a `PuzzleSession` (a thin wrapper: every call is the same core call as before).
public final class ArrowPuzzleSession: PuzzleSession {
    public let core: LevelSession

    public init(_ core: LevelSession) { self.core = core }

    public var phase: Phase { core.phase }
    public var stage: Int { core.stage }
    public var stageCount: Int { core.stages.count }
    public var clock: LevelClock { core.clock }
    public var hearts: Int? { core.hearts }
    public var isFinished: Bool { core.isFinished }

    public func start() -> [SessionOutput] { SessionEvent.outputs(core.start()) }

    public func input(_ e: PuzzleInput, at gameTime: Double) -> [SessionOutput] {
        switch e {
        case .tap(let t): return SessionEvent.outputs(core.tap(t.map(ArrowID.init(target:)), at: gameTime))
        case .drag, .swap, .select, .custom: return []                  // ArrowEscape is tap-only
        }
    }

    public func ack(_ a: PuzzleAck) -> [SessionOutput] {
        switch a {
        case .introFinished: return SessionEvent.outputs(core.ack(.introFinished))
        case .stageTransitionDone: return SessionEvent.outputs(core.ack(.stageTransitionDone))
        case .boardCleared: return SessionEvent.outputs(core.ack(.lastExitLeftBoard))
        case .contact(let b), .beat(let b):
            guard let s = b as? SessionAck else { return [] }
            return SessionEvent.outputs(core.ack(s))
        }
    }

    public func tick(_ dt: Double) -> [SessionOutput] { SessionEvent.outputs(core.tick(dt)) }
    public func hold(_ r: HoldReason) { core.hold(r) }
    public func release(_ r: HoldReason) { core.release(r) }

    /// The hourglass always does something in a live phase; the bulb only when a unit is free (a door still opening: none).
    public func canUseBooster(_ id: BoosterID) -> Bool {
        switch core.rules.boosters.action(id) {
        case .freezeTimer: return true
        case .hint: return !(core.hint(policy: core.rules.boosters.hintPolicy) ?? []).isEmpty
        case .none: return false
        }
    }

    public func useBooster(_ id: BoosterID) -> [SessionOutput] {
        SessionEvent.outputs(core.useBooster(id, hintPolicy: core.rules.boosters.hintPolicy, freezeFlightFromUse: true))
    }

    public func acceptContinue() -> [SessionOutput] { SessionEvent.outputs(core.acceptContinue()) }
    public func declineContinue() -> [SessionOutput] { SessionEvent.outputs(core.declineContinue()) }
    public func quit() -> [SessionOutput] { SessionEvent.outputs(core.quit()) }

    /// The first arrow of the solver's greedy unit (the HeadlessDriver's order).
    public func hint() -> PuzzleTarget? { core.hint()?.first?.target }

    /// Live arrows that are not free right now, in board order (a deliberate bump for bots and `-pc.lose hearts`).
    public func blockedTargets() -> [PuzzleTarget] {
        let snap = core.snapshot()
        let free = Set(snap.free.flatMap { $0 })
        return snap.live.filter { !free.contains($0) }.map(\.target)
    }
}

// MARK: - the module

/// ArrowEscape's puzzle (the first module; `puzzle.module: arrow-escape` in game.yml).
public enum ArrowEscapeModule: PuzzleModule {
    public static let id = "arrow-escape"
    public static let contractVersion = PuzzleContract.version

    /// Fail rules timer + hearts (3 per board, from each level), tap input, the hourglass (the shell's freeze) and the bulb
    /// (the session's hint), HUD timer + hearts, a zoomable board, "Levels 1-4"-style multi-board sessions.
    public static var capabilities: PuzzleCapabilities {
        PuzzleCapabilities(failRules: [.timer, .hearts(3)], inputs: [.tap],
                           boosters: [BoosterSpec(id: .freeze, effect: .freezeTimer),
                                      BoosterSpec(id: .hint, effect: .puzzleAction("hint"))],
                           hud: [.timer, .hearts], zoomable: true, multiStageSessions: true)
    }

    /// The session over a plan's boards.
    public static func makeSession(plan: SessionPlan, stages: [LevelSpec], setup: AttemptSetup, rules: RulesTuning,
                                   streakActive: Bool) -> ArrowPuzzleSession {
        let s = LevelSession(plan: plan, stages: stages, setup: setup, rules: rules)
        s.streakActive = streakActive
        return ArrowPuzzleSession(s)
    }

    /// The generic description of one board.
    public static func stage(_ level: LevelSpec) -> PuzzleStage {
        PuzzleStage(level: level.level, tag: level.tag, timerSeconds: level.timerSeconds, hearts: level.hearts,
                    summary: "\(level.arrows.count) arrows", content: level)
    }

    /// FIX-2 A (V3-01) warm-up: a headless 2-arrow board cleared to a win (the first clearing tap of a process paid Swift's
    /// one-time metadata instantiation in `LevelSession.cleared`). Pure; run off the main thread by the app.
    public static func warmUpWin(rules: RulesTuning) -> WinResult? {
        let a1 = ArrowSpec(id: ArrowID(1), cells: [Cell(0, 1), Cell(1, 1)], dir: .right)
        let a2 = ArrowSpec(id: ArrowID(2), cells: [Cell(3, 2), Cell(3, 1)], dir: .up)
        let level = LevelSpec(level: 9_990, source: .designed, cols: 4, rows: 4, timerSeconds: 180, hearts: 3, tag: .normal,
                              arrows: [a1, a2])
        let session = LevelSession(plan: SessionPlan(id: "warm-clear", levels: [level.level]), stages: [level],
                                   setup: AttemptSetup(levels: [level.level]), rules: rules)
        _ = session.start()
        _ = session.ack(.introFinished)
        _ = session.tap(ArrowID(2), at: 0.1)
        for case .won(let r) in session.tap(ArrowID(1), at: 0.2) { return r }
        return nil
    }
}
