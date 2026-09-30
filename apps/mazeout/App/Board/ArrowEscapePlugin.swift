import UIKit
import QuartzCore
import PathCore

// Template phase 2 (docs/architecture/PUZZLE-MODULE.md §6): ArrowEscape's puzzle module, app half. Everything the Game layer
// used to know about arrows lives here now, next to the board:
//  - `ArrowPuzzleBoard`: the app-lifetime BoardEngine (still `BoardControlling`, the board's own arrow-typed API that
//    BoardLab and the board tests drive) behind the generic `PuzzleBoard`. It is the engine's `BoardDelegate` while a Play
//    runs and translates both ways: released arrow → `.tap(target)`, board beats → `PuzzleAck`s (+ the burst haptic),
//    `[SessionOutput]` → the engine's `[SessionEvent]` (the `.puzzle` items, in order), the probe's session half;
//  - `ArrowEscapePlugin`: the session factory over the level library (with `-pc.timer` / `-pc.hearts`), tutorials and unlock
//    cards in generic form, the bot's blocked-arrow picks, the headless warm-up win;
//  - `ArrowEscapeEntry`: what `ActivePuzzle.entry` names.
// Same-frame path (§8.2, D8): engine release handler → `boardReleased` → `boardInput` → session → `present` → the engine's
// present, all in the release handler's run-loop turn and its Core Animation transaction, exactly as before (one more
// synchronous call on the way in, one array filter on the way out).

@MainActor final class ArrowPuzzleBoard: PuzzleBoard, BoardDelegate, BoardProbeSupplying {
    let engine: any BoardControlling
    private let tuning: BoardTuning
    private var cachedConfig: BoardConfig?

    init(engine: any BoardControlling, tuning: BoardTuning) {
        self.engine = engine
        self.tuning = tuning
    }

    // MARK: PuzzleBoard

    /// Setting a Play's delegate (re)claims the engine (BoardLab may have taken it); clearing it releases the engine.
    weak var delegate: PuzzleBoardDelegate? {
        didSet {
            if delegate != nil {
                engine.delegate = self
            } else if engine.delegate === self {
                engine.delegate = nil
            }
        }
    }

    var view: UIView { engine.view }

    var inputEnabled: Bool {
        get { engine.inputEnabled }
        set { engine.inputEnabled = newValue }
    }

    var allowedTargets: Set<PuzzleTarget>? {
        get { engine.allowedArrows.map { Set($0.map(\.target)) } }
        set { engine.allowedArrows = newValue.map { Set($0.map(ArrowID.init(target:))) } }
    }

    func prepare() async { await engine.prepare() }

    func load(_ stage: StageContext) {
        guard let setup = setup(stage) else { return }
        engine.load(setup)
    }

    func playIntro(_ style: IntroStyle) { engine.playIntro(style) }

    func present(_ outputs: [SessionOutput]) {
        engine.present(SessionOutput.arrowEvents(outputs))
    }

    func playStageTransition(to next: StageContext) {
        guard let setup = setup(next) else { return }
        engine.playStageTransition(to: setup)
    }

    func playClearWave() { engine.playClearWave() }

    /// The fingertip: `at` (lattice coordinates of the level, integer = a cell centre) relative to the arrow's middle cell
    /// (the engine's `screenPoint(of:)` anchor), scaled by the on-screen pitch; nil `at` = the anchor itself.
    func handPoint(for target: PuzzleTarget, at: [Double]?) -> CGPoint? {
        let id = ArrowID(target: target)
        guard let level = currentLevel, let arrow = level.arrows.first(where: { $0.id == id }),
              let mid = engine.screenPoint(of: id) else { return nil }
        guard let at, at.count == 2, !arrow.cells.isEmpty else { return mid }
        let c = arrow.cells[arrow.cells.count / 2]                          // the engine's own anchor cell (screenPoint)
        let p = engine.pitchOnScreen
        return CGPoint(x: mid.x + (CGFloat(at[0]) - CGFloat(c.c)) * p, y: mid.y + (CGFloat(at[1]) - CGFloat(c.r)) * p)
    }

    /// Through the engine's real release handler (hit test, ripple, the session, the movers) at the arrow's safe tap point.
    func performTap(on target: PuzzleTarget) -> Bool {
        guard let e = engine as? BoardEngine, let p = e.tapPoint(of: ArrowID(target: target)) else { return false }
        e.handleRelease(screenPoint: p, touchTimestamp: CACurrentMediaTime())
        return true
    }

    func publishProbe() { (engine as? BoardEngine)?.publishProbe() }

    /// The engine meters its own frames (its display link feeds PerfMonitor / LatencyProbe and logs hitches and tap
    /// latency), exactly as before the contract: the Play adds no second meter.
    var metersFrames: Bool { true }

    var diagnostics: BoardDiagnostics? {
        guard let e = engine as? BoardEngine else { return nil }
        return BoardDiagnostics(lastRippleAt: e.lastRippleAt, lastPresentMs: e.lastPresentMs, presentNotes: e.presentNotes,
                                hitchesLoad: e.hitchesLoad, hitchesPlay: e.hitchesPlay)
    }

    /// Arrows marked red by a bump (the engine's probe), as targets.
    func markedTargets() -> Set<PuzzleTarget> {
        Set(engine.probe().arrows.filter(\.red).map { PuzzleTarget($0.id) })
    }

    // MARK: stage setup

    private var arrowSession: LevelSession? { (delegate?.activeSession as? ArrowPuzzleSession)?.core }
    private var currentLevel: LevelSpec? { arrowSession?.level }

    /// The engine's config (its play rect and caps), else the tuning's (a board that is not the engine).
    private var config: BoardConfig {
        if let c = cachedConfig { return c }
        let c = (engine as? BoardEngine)?.config ?? BoardConfig(tuning)
        cachedConfig = c
        return c
    }

    private func setup(_ s: StageContext) -> StageSetup? {
        guard let level = s.info.content as? LevelSpec else {
            Log.error("board", "stage \(s.stage + 1) of L\(s.info.level) carries no LevelSpec: not loaded")
            return nil
        }
        return StageSetup(level: level, stage: s.stage, stages: s.stages, seed: s.seed, screen: s.screen, config: config)
    }

    // MARK: BoardDelegate (the engine → the Play)

    func boardFrame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval) {
        delegate?.boardFrame(timestamp: timestamp, targetTimestamp: targetTimestamp)
    }

    func boardReleased(arrow: ArrowID?, contentPoint: CGPoint, touchTimestamp: TimeInterval) {
        Self.forward(release: arrow, touchTimestamp: touchTimestamp, to: delegate)
    }

    func boardBeat(_ beat: BoardBeat) { Self.forward(beat, to: delegate) }

    func boardZoomChanged(scale: CGFloat) { delegate?.boardZoomChanged(scale: scale) }

    /// A released arrow (nil = empty point) as the generic tap.
    static func forward(release arrow: ArrowID?, touchTimestamp: TimeInterval, to d: PuzzleBoardDelegate?) {
        d?.boardInput(.tap(arrow?.target), touchTimestamp: touchTimestamp)
    }

    /// The engine's beats as the contract's acks. Only the beats the rules wait for reach the session: intro, bump contact
    /// (`.contact`: the contact haptic), bump finished, door burst (+ the burst haptic), the last exit (W = `.boardCleared`)
    /// and the stage transition; a pipe / box break is only its burst haptic; the rest is the board's own business.
    static func forward(_ beat: BoardBeat, to d: PuzzleBoardDelegate?) {
        switch beat {
        case .introFinished: d?.boardAck(.introFinished)
        case .bumpContact(let a): d?.boardAck(.contact(SessionAck.bumpContact(a)))
        case .bumpFinished(let a): d?.boardAck(.beat(SessionAck.bumpFinished(a)))
        case .doorBurst(let o):
            d?.boardAck(.beat(SessionAck.doorBurst(o)))
            d?.boardFeedback(.burst)                                   // MA §12.1: the burst frame (B2's beat)
        case .pipeBroken, .counterBroken: d?.boardFeedback(.burst)
        case .lastExitLeftBoard: d?.boardAck(.boardCleared)
        case .stageTransitionDone: d?.boardAck(.stageTransitionDone)
        case .exitLeftBoard, .exitFinished, .clearWaveFinished: break
        }
    }

    // MARK: BoardProbeSupplying (the §9.4 probe's session half; keys EXACT, VERIFY parses them)

    func supplementProbe(_ p: inout BoardProbeData) {
        guard let session = arrowSession else { return }
        let snap = session.snapshot()
        p.lvl = session.level.level
        p.stage = snap.stage
        p.stages = session.stages.count
        p.phase = snap.phase
        p.t = (snap.remaining * 1000).rounded() / 1000
        p.timerStarted = snap.timerStarted
        p.hearts = snap.hearts
        p.combo = snap.combo
        var unitOf: [Int: [Int]] = [:]
        var free: Set<Int> = []
        for u in snap.free {
            let ids = u.map(\.raw)
            for a in ids { unitOf[a] = ids; free.insert(a) }
        }
        let tapes = session.level.obstacles.filter { $0.kind == .tape }
        for i in p.arrows.indices {
            let id = p.arrows[i].id
            p.arrows[i].free = free.contains(id)
            if let u = unitOf[id] {
                p.arrows[i].unit = u
            } else if let t = tapes.first(where: { $0.arrows.contains(ArrowID(id)) }) {
                p.arrows[i].unit = t.arrows.map(\.raw).filter { m in p.arrows.contains { $0.id == m } }
            }
        }
        for (oid, n) in snap.counters {
            if let i = p.obstacles.firstIndex(where: { $0.id == oid.raw }) {
                if p.obstacles[i].n == nil { p.obstacles[i].n = n }
            } else if let o = session.level.obstacle(oid) {
                p.obstacles.append(BoardProbeData.Obstacle(id: oid.raw, k: o.kind.rawValue, n: n))
            }
        }
    }
}

/// ArrowEscape's module, app half.
@MainActor final class ArrowEscapePlugin: PuzzlePlugin {
    let rules: RulesTuning
    private let level: @MainActor (Int) -> LevelSpec?
    let tutorials: [TutorialStep]
    let unlocks: [FeatureUnlock]

    init(rules: RulesTuning, level: @escaping @MainActor (Int) -> LevelSpec?, tutorials: [TutorialScript] = [],
         unlocks: [FeatureUnlock] = []) {
        self.rules = rules
        self.level = level
        self.tutorials = tutorials.map(\.step)
        self.unlocks = unlocks
    }

    var id: String { ArrowEscapeModule.id }
    var capabilities: PuzzleCapabilities { ArrowEscapeModule.capabilities }

    /// The session's boards first (a level that cannot load never costs a life), with `-pc.timer` / `-pc.hearts` applied.
    func stages(for plan: SessionPlan, args: LaunchArgs) -> [PuzzleStage]? {
        var stages: [LevelSpec] = []
        for n in plan.levels {
            guard let l = level(n) else {
                Log.error("game", "L\(n) is not available (library / provider): the Play is refused")
                return nil
            }
            stages.append(l)
        }
        if let t = args.timer { for i in stages.indices { stages[i].timerSeconds = max(1, Int(t.rounded(.up))) } }
        if let h = args.hearts { for i in stages.indices { stages[i].hearts = max(1, h) } }
        return stages.map(ArrowEscapeModule.stage)
    }

    func makeSession(plan: SessionPlan, stages: [PuzzleStage], setup: AttemptSetup, streakActive: Bool) -> any PuzzleSession {
        let specs = stages.compactMap { $0.content as? LevelSpec }
        precondition(specs.count == stages.count && !specs.isEmpty, "ArrowEscape stages carry LevelSpecs (stages(for:args:))")
        return ArrowEscapeModule.makeSession(plan: plan, stages: specs, setup: setup, rules: rules, streakActive: streakActive)
    }

    /// Blocked arrows that are not red yet (a bump that costs a heart), in board order.
    func mistakeTargets(_ session: any PuzzleSession, board: any PuzzleBoard) -> [PuzzleTarget] {
        guard let s = session as? ArrowPuzzleSession else { return [] }
        let red = (board as? ArrowPuzzleBoard)?.markedTargets() ?? []
        return s.blockedTargets().filter { !red.contains($0) }
    }

    func warmUpWin() -> @Sendable () -> WinResult? {
        let rules = rules
        return { ArrowEscapeModule.warmUpWin(rules: rules) }
    }
}

/// `ActivePuzzle.entry` for ArrowEscape.
@MainActor enum ArrowEscapeEntry: PuzzleEntryPoint {
    static func makePlugin(_ app: AppModel) -> any PuzzlePlugin {
        ArrowEscapePlugin(rules: app.rules, level: { [weak app] n in app?.level(n) },
                          tutorials: app.library?.tutorials ?? [], unlocks: app.library?.unlocks ?? [])
    }

    /// The engine AppModel built at boot (`makeEngine`); a fresh one only if it is missing (never on the boot path).
    static func makeBoard(_ app: AppModel) -> any PuzzleBoard {
        ArrowPuzzleBoard(engine: app.board ?? BoardEntry.makeBoard(app.context), tuning: app.tuning.board)
    }

    /// Template phase 5: the arrow content is built only while ArrowEscape is the active module. The level library (index +
    /// small files; levels decode lazily) and C4's provider, with the same logs as AppModel wrote them before.
    static func loadContent(bundle: Bundle) -> PuzzleBootContent {
        var library: LevelLibrary?
        if let folder = bundle.resourceURL?.appendingPathComponent("Levels") {
            do {
                let lib = try LevelLibrary.load(folder: folder)
                for p in lib.problems { Log.error("levels", p) }
                library = lib
            } catch {
                Log.error("levels", "\(error)")
            }
        }
        let provider = library.map { LevelProvider(library: $0) }
        provider?.onProduced = { r in
            Log.mark("level", String(format: "generated L%d in %.1f ms (%@, seeds %d, validate %.1f ms)", r.level, r.totalMs,
                                     r.route.rawValue, r.seedsTried, r.validateMs))
        }
        return PuzzleBootContent(library: library, provider: provider,
                                 sessions: library?.sessions ?? AppModel.loadSessions(bundle: bundle))
    }

    /// The app-lifetime Core Animation engine (BOARD's `BoardEntry`), created at boot and never destroyed (§5.1).
    static func makeEngine(_ ctx: AppContext) -> (any BoardControlling)? { BoardEntry.makeBoard(ctx) }
}
