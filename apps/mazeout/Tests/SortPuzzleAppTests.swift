import XCTest
import UIKit
@testable import ArrowOut
import PathCore
import SortPuzzle

/// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §6b): the second puzzle module's app half, compiled into the app while
/// ArrowEscape stays the active module. Proves, headless (no window, the board's clock advanced by hand):
///  - the plugin + the real `SortPuzzleBoard` play a two-board session through the board's own release handler
///    (`performTap` → hit test → `.select` → the session → `present`), the board mirroring the session's tubes, its beats
///    (`introFinished`, `boardCleared`, `stageTransitionDone`) never synchronous;
///  - the unchanged, genre-agnostic `GameController` runs a sort Play end to end with the real board: the win banked at the
///    last pour, W at the board's `boardCleared`, the win panel and the route; a stuck board's offer paid through the shell's
///    fail flow grants the extra tube;
///  - layout and hit testing, the bundle's sort.json, `ActivePuzzle` still naming ArrowEscape.
@MainActor final class SortPuzzleAppTests: XCTestCase {

    static let screen = CGSize(width: 393, height: 852)

    /// A stand-in for the Play: forwards the board's input and acks to the session and the session's answers to the board.
    @MainActor final class Relay: PuzzleBoardDelegate {
        weak var board: SortPuzzleBoard?
        let session: any PuzzleSession
        private(set) var outputs: [SessionOutput] = []
        private(set) var acks: [String] = []
        private(set) var inputs: [PuzzleInput] = []

        init(_ session: any PuzzleSession) { self.session = session }

        func deliver(_ o: [SessionOutput]) {
            outputs += o
            board?.present(o)
        }

        func boardFrame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval) {}
        func boardInput(_ input: PuzzleInput, touchTimestamp: TimeInterval) {
            inputs.append(input)
            deliver(session.input(input, at: touchTimestamp))
        }
        func boardAck(_ ack: PuzzleAck) {
            acks.append(SortPuzzleAppTests.name(ack))
            deliver(session.ack(ack))
        }
        func boardFeedback(_ haptic: Haptic) {}
        func boardZoomChanged(scale: CGFloat) {}
        var activeSession: (any PuzzleSession)? { session }
    }

    nonisolated static func name(_ a: PuzzleAck) -> String {
        switch a {
        case .introFinished: return "introFinished"
        case .stageTransitionDone: return "stageTransitionDone"
        case .boardCleared: return "boardCleared"
        case .contact: return "contact"
        case .beat: return "beat"
        }
    }

    static func wins(_ outputs: [SessionOutput]) -> Int {
        outputs.filter { if case .meta(.won) = $0 { return true }; return false }.count
    }

    func makeBoard(tune: [String: String] = [:]) -> SortPuzzleBoard {
        SortPuzzleBoard(tuning: SortBoardTuning(file: TuningFile.load(SortPuzzleEntry.tuningFile, bundle: .main, tune: tune)))
    }

    func bundleRules() -> SortRules {
        SortPuzzlePlugin.loadRules(TuningFile.load(SortPuzzleEntry.tuningFile, bundle: .main, tune: [:]))
    }

    // MARK: the plugin + the board, headless

    func testPluginAndBoardPlayATwoBoardSessionThroughTheReleaseHandler() throws {
        let plugin = SortPuzzlePlugin(rules: bundleRules(), meta: MetaRules())
        XCTAssertEqual(plugin.id, "sort-puzzle")
        XCTAssertEqual(plugin.capabilities.hud, [.progress])
        let plan = SessionPlan(id: "S3-4", levels: [3, 4])
        let stages = try XCTUnwrap(plugin.stages(for: plan, args: LaunchArgs()))
        XCTAssertEqual(stages.map(\.level), [3, 4])
        XCTAssertNil(plugin.stages(for: SessionPlan(id: "S0", levels: [0]), args: LaunchArgs()), "no level 0: refused")
        let session = plugin.makeSession(plan: plan, stages: stages, setup: AttemptSetup(levels: plan.levels), streakActive: false)
        let sort = try XCTUnwrap(session as? SortPuzzleSession)
        let board = makeBoard()
        let relay = Relay(session)
        relay.board = board
        board.delegate = relay

        func context(_ k: Int) -> StageContext {
            StageContext(stage: k, stages: stages.count, seed: 1, screen: Self.screen, info: stages[k])
        }
        board.load(context(0))
        XCTAssertEqual(board.tubes, sort.tubes)
        XCTAssertEqual(board.layout.tubes.count, sort.tubes.count)
        board.playIntro(.growFromTails)
        relay.deliver(session.start())
        XCTAssertEqual(session.phase, .intro(stage: 0), "the intro's ack comes later, never inside playIntro")
        board.advance(1)
        XCTAssertEqual(relay.acks, ["introFinished"])
        XCTAssertEqual(session.phase, .ready(stage: 0))

        XCTAssertFalse(board.performTap(on: PuzzleTarget(0)), "input closed: the caller feeds the session itself")
        board.inputEnabled = true
        var taps = 0
        while !session.isFinished && taps < 400 {
            if case .stageClear(let k) = session.phase {
                XCTAssertEqual(relay.acks.last, "introFinished", "W waits for the last pour to land")
                board.advance(1)
                XCTAssertEqual(relay.acks.last, "boardCleared")
                board.playStageTransition(to: context(k + 1))
                XCTAssertEqual(session.phase, .stageClear(stage: k))
                board.advance(1)
                XCTAssertEqual(relay.acks.last, "stageTransitionDone")
                XCTAssertEqual(session.phase, .ready(stage: k + 1))
                XCTAssertEqual(board.tubes, sort.tubes, "the next board")
                continue
            }
            let t = try XCTUnwrap(session.hint())
            taps += 1
            XCTAssertTrue(board.performTap(on: t))
            XCTAssertEqual(relay.inputs.last, PuzzleInput.select(t), "the release hit-tests to the hinted tube")
            XCTAssertEqual(board.tubes, sort.tubes, "the board mirrors the session")
        }
        XCTAssertEqual(Self.wins(relay.outputs), 1)
        XCTAssertEqual(relay.acks.filter { $0 == "boardCleared" }.count, 1, "stage 1's W so far")
        board.advance(1)
        XCTAssertEqual(relay.acks.filter { $0 == "boardCleared" }.count, 2, "…and the last stage's")
        XCTAssertEqual(board.pendingBeats, 0)
        guard case .won(let r) = session.phase else { return XCTFail("won: \(session.phase)") }
        XCTAssertEqual(r.levels, [3, 4])
        board.playClearWave()
        board.publishProbe()
        XCTAssertNotNil(board.view.accessibilityValue)
        board.delegate = nil
    }

    func testReleaseOnNothingDropsTheLiftAndTutorialRestrictionHolds() throws {
        let plugin = SortPuzzlePlugin(rules: bundleRules(), meta: MetaRules())
        let plan = SessionPlan(id: "S1", levels: [1])
        let stages = try XCTUnwrap(plugin.stages(for: plan, args: LaunchArgs()))
        let session = plugin.makeSession(plan: plan, stages: stages, setup: AttemptSetup(levels: [1]), streakActive: false)
        let board = makeBoard()
        let relay = Relay(session)
        relay.board = board
        board.delegate = relay
        board.load(StageContext(stage: 0, stages: 1, seed: 1, screen: Self.screen, info: stages[0]))
        board.playIntro(.none)
        relay.deliver(session.start())
        board.advance(0)
        XCTAssertEqual(session.phase, .ready(stage: 0), "IntroStyle.none: the ack on the next board tick")
        board.inputEnabled = true
        board.allowedTargets = [PuzzleTarget(1)]
        XCTAssertTrue(board.performTap(on: PuzzleTarget(0)))
        XCTAssertTrue(relay.inputs.isEmpty, "a tutorial allows only its targets")
        board.allowedTargets = nil
        XCTAssertTrue(board.performTap(on: PuzzleTarget(0)))
        XCTAssertEqual(board.lifted?.tube, 0)
        board.handleRelease(at: CGPoint(x: 1, y: 1), touchTimestamp: 0)          // above the grid (the HUD's inset)
        XCTAssertEqual(relay.inputs, [PuzzleInput.select(PuzzleTarget(0)), .select(PuzzleTarget(0))], "the same pick again drops it")
        XCTAssertNil(board.lifted)
        XCTAssertNil((session as? SortPuzzleSession)?.selection)
        XCTAssertEqual(plugin.mistakeTargets(session, board: board), [], "nothing lifted: no refusable pick")
        XCTAssertTrue(board.performTap(on: PuzzleTarget(0)))
        let refusable = plugin.mistakeTargets(session, board: board)
        XCTAssertFalse(refusable.contains(PuzzleTarget(0)))
        for t in refusable {
            let s = try XCTUnwrap(session as? SortPuzzleSession)
            XCTAssertFalse(SortMechanics.canPour(s.tubes, from: 0, to: t.raw, capacity: s.capacity))
        }
        let f2 = board.layout.tubes[2]
        XCTAssertEqual(board.handPoint(for: PuzzleTarget(2), at: nil), CGPoint(x: f2.midX, y: f2.midY))
    }

    func testLayoutFitsTheScreenAndHitsEveryTube() throws {
        let board = makeBoard()
        let t = board.tuning
        for count in [3, 5, 6, 7, 12, 14, 17] {
            for capacity in [3, 4, 6] {
                let l = SortBoardLayout.make(count: count, capacity: capacity, size: Self.screen, tuning: t)
                XCTAssertEqual(l.tubes.count, count)
                XCTAssertLessThanOrEqual(l.scale, 1)
                for (i, f) in l.tubes.enumerated() {
                    XCTAssertGreaterThanOrEqual(f.minX, t.insetSide - 0.5, "\(count)×\(capacity) #\(i)")
                    XCTAssertLessThanOrEqual(f.maxX, Self.screen.width - t.insetSide + 0.5)
                    XCTAssertGreaterThanOrEqual(f.minY - t.liftHeight * l.scale, t.insetTop - 0.5, "room to lift, below the HUD")
                    XCTAssertLessThanOrEqual(f.maxY, Self.screen.height - t.insetBottom + 0.5)
                    for g in l.tubes[(i + 1)...] { XCTAssertFalse(f.intersects(g), "\(count)×\(capacity): tubes overlap") }
                }
            }
        }
        // a 10-colour level (+ 2 empty tubes): every tube's middle hits that tube
        let level = SortPuzzleModule.level(85, rules: bundleRules())
        XCTAssertEqual(level.tubes.count, 12)
        board.load(StageContext(stage: 0, stages: 1, seed: 1, screen: Self.screen, info: SortPuzzleModule.stage(level)))
        for (i, f) in board.layout.tubes.enumerated() {
            XCTAssertEqual(board.tube(at: CGPoint(x: f.midX, y: f.midY)), i)
            XCTAssertEqual(board.tube(at: CGPoint(x: f.midX, y: f.minY - 2)), i, "the lifted run's room counts")
        }
        XCTAssertNil(board.tube(at: CGPoint(x: 1, y: 1)))
        XCTAssertLessThanOrEqual(level.colors, SortPuzzleBoard.unitColors.count, "a skin colour per colour")
    }

    func testBundleSortJSONAndTheActiveModule() {
        let file = TuningFile.load(SortPuzzleEntry.tuningFile, bundle: .main, tune: [:])
        XCTAssertNotNil(file.data, "Tuning/sort.json ships in the bundle")
        let (rules, problems) = SortRules.load(json: file.data)
        XCTAssertEqual(problems, [])
        XCTAssertEqual(rules, SortRules(), "the bundle's sort.json is the module's defaults")
        for key in ["insetTop", "unitSize", "pourSeconds", "introSeconds", "transitionSeconds", "completeSeconds"] {
            XCTAssertTrue(file.has("board." + key), "board.\(key) is data")
        }
        XCTAssertEqual(makeBoard(tune: ["sort.board.pourSeconds": "0.5"]).tuning.pourSeconds, 0.5, "-pc.tune sort.*")
        let highest = rules.levels.curve.map(\.colors).max() ?? 0
        XCTAssertLessThanOrEqual(highest, SortPuzzleBoard.unitColors.count, "the curve never outruns the skin's colours")
        #if PC_PUZZLE_SORT
        XCTAssertEqual(ObjectIdentifier(ActivePuzzle.entry), ObjectIdentifier(SortPuzzleEntry.self))
        #else
        XCTAssertEqual(ObjectIdentifier(ActivePuzzle.entry), ObjectIdentifier(ArrowEscapeEntry.self),
                       "ArrowEscape stays the active module unless PC_PUZZLE_SORT is set")
        #endif
        let win = SortPuzzlePlugin(rules: rules, meta: MetaRules()).warmUpWin()()
        XCTAssertEqual(win?.levels, [1])
    }

    // MARK: the unchanged GameController with the sort module

    struct Rig {
        let game: GameController
        let board: SortPuzzleBoard
        let popups: GameControllerTests.FakePopups
        let router: GameControllerTests.FakeRouter
        let store: PlayerStore
        let log: GameControllerTests.Recorder
        let hud: HUDModel
    }

    func makeRig(levels: [Int], level: (@MainActor (Int) -> SortLevel?)? = nil, tune: [String: String] = [:]) -> Rig {
        let args = LaunchArgs(pairs: ["pc.seed": "7", "pc.coins": "5000"])
        let tuning = Tuning.load(bundle: .main, tune: tune)
        let rules = RulesTuning.load(json: tuning.rules.data, overrides: tuning.rules.overrides).rules
        let economy = EconomyRules.load(rules: tuning.rules.data, social: tuning.social.file.data,
                                        overrides: tuning.rules.overrides).rules
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("sort-\(UUID().uuidString)")
        let store = PlayerStore(args: args, now: Date(), bundle: .main, directory: dir, rules: economy, debounce: 0.05)
        let log = GameControllerTests.Recorder()
        let board = makeBoard()
        let popups = GameControllerTests.FakePopups(log), router = GameControllerTests.FakeRouter()
        let hud = HUDModel()
        let plugin = SortPuzzlePlugin(rules: bundleRules(), meta: rules.meta, level: level)
        let plan = SessionPlan(id: "S\(levels[0])", levels: levels)
        let services = GameServices(
            args: args, tuning: tuning, rules: rules.meta, economy: economy, clock: MotionClock(args: args), store: store, hud: hud,
            board: board, puzzle: plugin,
            audio: GameControllerTests.FakeAudio(log), haptics: GameControllerTests.FakeHaptics(log), popups: popups,
            fx: GameControllerTests.FakeFX(log), router: router, latency: LatencyProbe(), perf: PerfMonitor(),
            plan: { _ in plan },
            rivals: { SocialWorld(installSeed: 7, config: .default, names: NameBank()) },
            screenSize: { SortPuzzleAppTests.screen },
            screenAfterWin: { .home(.afterWin($0), tab: .home) },
            screenAfterLoss: { GameServices.defaultAfterLoss($0, tryAgain: $1, homeSeen: true) },
            levelStarted: { _ in }, app: nil)
        let game = GameController(LevelLaunch(session: plan.id, levels: plan.levels), services: services, directors: { _ in [] })
        return Rig(game: game, board: board, popups: popups, router: router, store: store, log: log, hud: hud)
    }

    private var frameTime = 5_000.0
    /// n display-link frames at 60 Hz (the board's clock is advanced with them, as its display link would).
    func frames(_ r: Rig, _ n: Int) {
        for _ in 0..<n {
            frameTime += 1.0 / 60
            r.board.advance(1.0 / 60)
            r.game.boardFrame(timestamp: frameTime, targetTimestamp: frameTime + 1.0 / 60)
        }
    }

    func settle(_ r: Rig, frames n: Int = 3) async {
        for _ in 0..<8 {
            for _ in 0..<10 { await Task.yield() }
            frames(r, n)
        }
    }

    /// Plays the session's own hint through the board until the Play is finished or an offer is up.
    func play(_ r: Rig, maxTaps: Int = 400) throws {
        var taps = 0
        while let s = r.game.session, !s.isFinished, taps < maxTaps {
            if case .offer = s.phase { return }
            frames(r, 1)                                                    // the controller re-opens input on its frames
            let t = try XCTUnwrap(s.hint())
            taps += 1
            XCTAssertTrue(r.board.performTap(on: t), "input open on a live stage")
        }
    }

    func testGameControllerPlaysASortLevelToTheWinPanel() async throws {
        let r = makeRig(levels: [2])
        XCTAssertTrue(r.game.start())
        XCTAssertEqual(r.game.session?.phase, .intro(stage: 0))
        XCTAssertFalse(r.board.inputEnabled)
        frames(r, 60)                                                        // the intro (0.45 s) → introFinished
        XCTAssertEqual(r.game.session?.phase, .ready(stage: 0))
        XCTAssertTrue(r.board.inputEnabled, "the controller opens input at introFinished")
        XCTAssertNil(r.game.session?.hearts)
        XCTAssertTrue(r.hud.hearts.isEmpty, "no hearts rule: no hearts on the HUD")
        let coins0 = r.store.state.coins
        try play(r)
        guard case .won(let result)? = r.game.session?.phase else { return XCTFail("won: \(String(describing: r.game.session?.phase))") }
        // banked at the last pour, before W
        XCTAssertEqual(r.store.state.coins, coins0 + result.reward)
        XCTAssertEqual(r.store.state.level, 3)
        XCTAssertNil(r.store.state.activeAttempt)
        XCTAssertNil(r.log.index("fx.celebration"), "no celebration before W")
        XCTAssertNotNil(r.log.index("haptic.tap"), "a pour is a move: the tap haptic")
        frames(r, 60)                                                        // the pour lands → boardCleared → W
        XCTAssertNotNil(r.log.index("haptic.clear"))
        XCTAssertNotNil(r.log.index("fx.celebration normal"))
        await settle(r)
        XCTAssertEqual(r.popups.presented.last, .winPanel)
        if case .home(.afterWin(let s), _)? = r.router.went.last { XCTAssertEqual(s.reward, result.reward) } else {
            XCTFail("routed to \(String(describing: r.router.went.last))")
        }
    }

    func testStuckOfferPaidThroughTheShellAddsATube() async throws {
        let stuck = SortLevel(level: 5, tag: .normal, capacity: 3, colors: 3, tubes: [[2, 1, 0], [0, 1, 2], [1, 0, 2], []])
        let r = makeRig(levels: [5], level: { $0 == 5 ? stuck : nil }, tune: ["game.fail.heartsOutDelay": "0"])
        r.popups.payFirst = [.outOfTime]
        r.popups.script[.outOfTime] = [.primary]
        XCTAssertTrue(r.game.start())
        frames(r, 60)
        let coins0 = r.store.state.coins
        XCTAssertTrue(r.board.performTap(on: PuzzleTarget(0)))
        XCTAssertTrue(r.board.performTap(on: PuzzleTarget(3)))
        guard case .offer(let o)? = r.game.session?.phase else { return XCTFail("stuck → an offer") }
        XCTAssertEqual(o.kind, .stuck)
        XCTAssertEqual(o.grant, .puzzleAction(id: SortPuzzleModule.extraTubeAction, amount: 1))
        await settle(r)
        XCTAssertEqual(r.popups.presented.first, .outOfTime, "step 0 (no warning) uses the first offer popup")
        XCTAssertEqual(r.store.state.coins, coins0 - o.price)
        XCTAssertEqual(r.game.session?.phase, .playing(stage: 0))
        XCTAssertEqual((r.game.session as? SortPuzzleSession)?.tubes.count, 5)
        XCTAssertEqual(r.board.tubes.count, 5, "the board added the granted tube")
        try play(r)
        guard case .won? = r.game.session?.phase else { return XCTFail("won after the extra tube") }
        XCTAssertEqual(r.log.lines.filter { $0 == "haptic.fail" }.count, 1)
    }
}
