import XCTest
import UIKit
@testable import ArrowOut
import PathCore

/// GAME G1 (SPEC-architecture §8.1–§8.4, §12.2 G1 acceptance): the GameController with a FAKE board, fake audio / haptics /
/// popups / FX / router and a real PlayerStore on a temp directory, driven by hand (taps, board beats, display-link frames).
/// Proves: the §8.1 fan-out order (board → haptics → audio → HUD → FX → directors) for a tap, a contact and a win; nothing
/// written to the HUD on a tap frame; the win banked (and saved) at the tap, before the celebration starts at W; the
/// time-out and hearts-out chains through C3; holds keep the timer constant; the HUD's write rate.
/// Template phase 2: the controller is genre-agnostic (a `PuzzleSession` + a `PuzzleBoard`); the fake board implements
/// `PuzzleBoard`, the Play runs Arrow Out's module (`ArrowEscapePlugin`), and the tests drive it with the reference game's taps
/// and beats through ArrowPuzzleBoard's real translation (the `GameController` helpers at the end of this file).
@MainActor final class GameControllerTests: XCTestCase {

    // MARK: fakes

    final class Recorder {
        private(set) var lines: [String] = []
        func add(_ s: String) { lines.append(s) }
        func clear() { lines = [] }
        /// The first index of a line starting with `prefix`.
        func index(_ prefix: String) -> Int? { lines.firstIndex { $0.hasPrefix(prefix) } }
    }

    @MainActor final class FakeBoard: PuzzleBoard {
        weak var delegate: PuzzleBoardDelegate?
        let view = UIView()
        var inputEnabled = false
        var allowedTargets: Set<PuzzleTarget>?
        let log: Recorder
        init(_ log: Recorder) { self.log = log }
        func prepare() async {}
        func load(_ stage: StageContext) { log.add("board.load L\(stage.info.level) stage \(stage.stage)") }
        func playIntro(_ style: IntroStyle) { log.add("board.intro \(style)") }
        func present(_ outputs: [SessionOutput]) {
            log.add("board.present " + outputs.map { GameControllerTests.name($0) }.joined(separator: ","))
        }
        func playStageTransition(to next: StageContext) { log.add("board.stageTransition L\(next.info.level)") }
        func playClearWave() { log.add("board.clearWave") }
        func handPoint(for target: PuzzleTarget, at: [Double]?) -> CGPoint? { nil }
        func performTap(on target: PuzzleTarget) -> Bool { false }
        func publishProbe() {}
        var diagnostics: BoardDiagnostics? { nil }
    }

    @MainActor final class FakeAudio: AudioPlaying {
        let log: Recorder
        init(_ log: Recorder) { self.log = log }
        func warmUp() async {}
        func play(_ s: SoundID, gain: Float) { log.add("audio.\(s.rawValue)") }
        func playMusic(_ m: MusicID, fade: Double) {}
        func stopMusic(fade: Double) {}
        func apply(settings: PlayerState.Settings) {}
        var outputLatency: TimeInterval { 0 }
    }

    @MainActor final class FakeHaptics: HapticPlaying {
        let log: Recorder
        var enabled = true
        init(_ log: Recorder) { self.log = log }
        func prepare() {}
        func play(_ h: Haptic) { log.add("haptic.\(h.rawValue)") }
    }

    /// Answers each popup from a script (by popup id), or holds it until `release` is called.
    @MainActor final class FakePopups: PopupPresenting {
        let log: Recorder
        var script: [PopupID: [PopupResult]] = [:]
        /// Popups whose answer waits for `release(_:)`.
        var hold: Set<PopupID> = []
        /// For offers: call the PayAction first (a "Play On" press).
        var payFirst: Set<PopupID> = []
        private var pending: [(PopupID, CheckedContinuation<Any?, Never>)] = []
        private(set) var presented: [PopupID] = []
        init(_ log: Recorder) { self.log = log }
        var isPresenting: Bool { !pending.isEmpty }
        var topID: PopupID? { pending.last?.0 }
        func present<R>(_ popup: Popup<R>) async -> R {
            let id = popup.request.id
            presented.append(id)
            log.add("popup.\(id.rawValue)")
            if payFirst.contains(id) {
                switch popup.request {
                case .outOfTime(_, let pay), .continueOffer(_, let pay): _ = await pay()
                default: break
                }
            }
            if hold.contains(id) {
                let v = await withCheckedContinuation { (c: CheckedContinuation<Any?, Never>) in pending.append((id, c)) }
                return (v as? R) ?? popup.fallback
            }
            if var q = script[id], !q.isEmpty {
                let r = q.removeFirst()
                script[id] = q
                return (r as? R) ?? popup.fallback
            }
            return popup.fallback
        }
        func release(_ id: PopupID, _ answer: PopupResult) {
            guard let i = pending.firstIndex(where: { $0.0 == id }) else { return }
            let p = pending.remove(at: i)
            p.1.resume(returning: answer)
        }
        func dismissAll() { for p in pending { p.1.resume(returning: nil) }; pending = [] }
    }

    @MainActor final class FakeFX: FXPlaying {
        let log: Recorder
        private var n = 0
        init(_ log: Recorder) { self.log = log }
        func play(_ effect: FXEffect) -> FXHandle {
            n += 1
            if case .celebration(let t) = effect { log.add("fx.celebration \(t.rawValue)") } else { log.add("fx.other") }
            return FXHandle(id: n)
        }
        func finished(_ handle: FXHandle) async {}
        func skip(_ handle: FXHandle) {}
        func stop(_ handle: FXHandle) {}
        func stopAll() {}
        var isPlaying: Bool { false }
    }

    @MainActor final class FakeRouter: Routing {
        var screen: Screen = .home(.normal, tab: .home)
        private(set) var went: [Screen] = []
        func go(_ screen: Screen) { went.append(screen); self.screen = screen }
    }

    @MainActor final class RecordingDirector: GameDirector {
        let log: Recorder
        init(_ log: Recorder) { self.log = log }
        func handle(_ outputs: [SessionOutput], game: GameController) { log.add("director " + outputs.map { GameControllerTests.name($0) }.joined(separator: ",")) }
    }

    /// One output's name in the log. The names are the reference game's event names (the arrow events the board gets, the
    /// meta events under their SessionEvent name: `heartsChanged(n)` is the `heartLost(remaining: n)` of the contact frame).
    nonisolated static func name(_ out: SessionOutput) -> String {
        switch out {
        case .puzzle(let p):
            guard let e = p as? SessionEvent else { return "other" }
            switch e {
            case .exited: return "exited"
            case .bumped: return "bumped"
            case .arrowMarked: return "marked"
            case .tapIgnored: return "ignored"
            default: return "other"
            }
        case .meta(let m):
            switch m {
            case .heartsChanged(let n): return "heartLost(\(n))"
            case .timerStarted: return "timerStarted"
            case .timerArmed: return "timerArmed"
            case .stageLoaded: return "stageLoaded"
            case .won: return "won"
            case .lost(let r): return "lost(\(r.rawValue))"
            case .offer(let o): return "offer(\(o.kind.rawValue),\(o.step))"
            case .continued: return "continued"
            case .stageCleared: return "stageCleared"
            default: return "other"
            }
        }
    }

    // MARK: the rig

    struct Rig {
        let game: GameController
        let log: Recorder
        let board: FakeBoard
        let popups: FakePopups
        let router: FakeRouter
        let store: PlayerStore
        let hud: HUDModel
    }

    /// A 4 × 4 board: arrow 1 (the tail at (0,1) → the head at (1,1), right) is blocked by arrow 2 ((3,2) → (3,1), up), which
    /// is free. Tapping 2 then 1 wins; tapping 1 first bumps.
    nonisolated static func tinyLevel(_ n: Int = 900, timer: Int = 180) -> LevelSpec {
        let a1 = ArrowSpec(id: ArrowID(1), cells: [Cell(0, 1), Cell(1, 1)], dir: .right)
        let a2 = ArrowSpec(id: ArrowID(2), cells: [Cell(3, 2), Cell(3, 1)], dir: .up)
        return LevelSpec(level: n, source: .designed, cols: 4, rows: 4, timerSeconds: timer, hearts: 3, tag: .normal, arrows: [a1, a2])
    }

    func makeRig(args extra: [String: String] = [:], tune: [String: String] = [:], levels: [LevelSpec] = [tinyLevel()],
                 plan: SessionPlan? = nil) -> Rig {
        var pairs = ["pc.seed": "7"]
        for (k, v) in extra { pairs[k] = v }
        let args = LaunchArgs(pairs: pairs)
        let tuning = Tuning.load(bundle: .main, tune: tune)
        let rules = RulesTuning.load(json: tuning.rules.data, overrides: tuning.rules.overrides).rules
        let economy = EconomyRules.load(rules: tuning.rules.data, social: tuning.social.file.data, overrides: tuning.rules.overrides).rules
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("g1-\(UUID().uuidString)")
        let store = PlayerStore(args: args, now: Date(), bundle: .main, directory: dir, rules: economy, debounce: 0.05)
        let log = Recorder()
        let board = FakeBoard(log), popups = FakePopups(log), router = FakeRouter()
        let hud = HUDModel()
        let byNumber = Dictionary(uniqueKeysWithValues: levels.map { ($0.level, $0) })
        let thePlan = plan ?? SessionPlan(id: "L\(levels[0].level)", levels: levels.map(\.level))
        let services = GameServices(
            args: args, tuning: tuning, rules: rules.meta, economy: economy, clock: MotionClock(args: args), store: store, hud: hud,
            board: board, puzzle: ArrowEscapePlugin(rules: rules, level: { byNumber[$0] }),
            audio: FakeAudio(log), haptics: FakeHaptics(log), popups: popups, fx: FakeFX(log), router: router,
            latency: LatencyProbe(), perf: PerfMonitor(),
            plan: { _ in thePlan },
            rivals: { SocialWorld(installSeed: 7, config: .default, names: NameBank()) },
            screenSize: { CGSize(width: 393, height: 852) },
            screenAfterWin: { .home(.afterWin($0), tab: .home) },
            screenAfterLoss: { GameServices.defaultAfterLoss($0, tryAgain: $1, homeSeen: true) },
            levelStarted: { _ in }, app: nil)
        let launch = LevelLaunch(session: thePlan.id, levels: thePlan.levels)
        let game = GameController(launch, services: services, directors: { _ in [RecordingDirector(log)] })
        game.hudWriter.onWrite = { log.add("hud.\($0)") }
        return Rig(game: game, log: log, board: board, popups: popups, router: router, store: store, hud: hud)
    }

    /// Start + the intro ack: the session is `.ready`.
    func ready(_ r: Rig) {
        XCTAssertTrue(r.game.start())
        r.game.boardBeat(.introFinished)
        XCTAssertEqual(r.game.session?.phase, .ready(stage: 0))
    }

    private var t = 1000.0
    /// n display-link frames at 60 Hz.
    func frames(_ r: Rig, _ n: Int) {
        for _ in 0..<n {
            t += 1.0 / 60
            r.game.boardFrame(timestamp: t, targetTimestamp: t + 1.0 / 60)
        }
    }

    /// Lets the directors' tasks run (they await popups, frames and each other on the main actor).
    func settle(_ r: Rig, frames n: Int = 3) async {
        for _ in 0..<8 {
            for _ in 0..<10 { await Task.yield() }
            frames(r, n)
        }
    }

    func assertOrder(_ log: Recorder, _ prefixes: [String], file: StaticString = #filePath, line: UInt = #line) {
        var last = -1
        for p in prefixes {
            guard let i = log.index(p) else { XCTFail("no '\(p)' in \(log.lines)", file: file, line: line); return }
            XCTAssertGreaterThan(i, last, "'\(p)' out of order in \(log.lines)", file: file, line: line)
            last = i
        }
    }

    // MARK: the §8.1 fan-out order

    func testTapFanOutOrderAndNoHUDWriteOnTheTapFrame() {
        let r = makeRig(tune: ["audio.cues.arrowTap": "tapTick"])           // map the optional tap sound so step 3 runs
        ready(r)
        r.log.clear()
        r.game.boardReleased(arrow: ArrowID(2), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        assertOrder(r.log, ["board.present timerStarted,exited", "haptic.tap", "audio.tapTick", "director timerStarted,exited"])
        XCTAssertNil(r.log.index("hud."), "nothing is written to the HUD on the tap frame (§8.2): \(r.log.lines)")
        XCTAssertTrue(r.hud.timerFrozen, "the first tap's timerFrozen waits for the next tick")
        frames(r, 1)
        XCTAssertFalse(r.hud.timerFrozen, "…and is written on the next display-link tick")
    }

    func testDefaultTapIsSilentButTheHapticFires() {
        let r = makeRig()                                                  // audio.json cues.arrowTap = "" (MA3)
        ready(r)
        r.log.clear()
        r.game.boardReleased(arrow: ArrowID(2), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        XCTAssertNotNil(r.log.index("haptic.tap"))
        XCTAssertNil(r.log.index("audio."), "v552 plays no tap sound (MA3): \(r.log.lines)")
    }

    func testContactFanOutOrder() {
        let r = makeRig()
        ready(r)
        r.game.boardReleased(arrow: ArrowID(1), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())   // bumps into 2
        XCTAssertNotNil(r.log.index("board.present timerStarted,bumped"))
        r.log.clear()
        r.game.boardBeat(.bumpContact(ArrowID(1)))
        assertOrder(r.log, ["board.present heartLost(2)", "haptic.heartLost", "hud.hearts", "director heartLost(2)"])
        XCTAssertEqual(r.hud.hearts, [.full, .full, .lost], "the rightmost heart breaks on the contact frame")
        // a re-bump of the red arrow costs no heart: the heavy bump haptic instead (MA §12.1)
        r.game.boardBeat(.bumpFinished(ArrowID(1)))
        r.game.boardReleased(arrow: ArrowID(1), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        r.log.clear()
        r.game.boardBeat(.bumpContact(ArrowID(1)))
        XCTAssertNotNil(r.log.index("haptic.bumpContact"), "\(r.log.lines)")
        XCTAssertNil(r.log.index("haptic.heartLost"))
        XCTAssertEqual(r.game.session?.hearts, 2)
    }

    // MARK: the win: banked at the tap, the celebration at W

    func testWinIsBankedAndSavedAtTheTapBeforeTheCelebration() async throws {
        let r = makeRig()
        ready(r)
        let coins0 = r.store.state.coins
        let lives0 = r.store.state.lives.count
        XCTAssertEqual(lives0, 4, "a life is taken at the start (C3 atStart)")
        r.game.boardReleased(arrow: ArrowID(2), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        r.log.clear()
        r.game.boardReleased(arrow: ArrowID(1), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        // banked at the tap: coins, the pending home fly, the life back, the next level, no running attempt — and on disk
        XCTAssertEqual(r.store.state.coins, coins0 + 20)
        XCTAssertEqual(r.store.state.pendingCoinFly, 20)
        XCTAssertEqual(r.store.state.lives.count, 5, "a win gives the life back")
        XCTAssertEqual(r.store.state.level, 901)
        XCTAssertNil(r.store.state.activeAttempt)
        r.store.flush()
        let saved = try PlayerStore.decode(Data(contentsOf: r.store.fileURL))
        XCTAssertEqual(saved.coins, coins0 + 20, "a kill during the celebration still finds the win on disk")
        XCTAssertNil(saved.activeAttempt, "…so the next launch does not count it as a killed attempt")
        XCTAssertNil(r.log.index("fx."), "no celebration before W: \(r.log.lines)")
        XCTAssertFalse(r.board.inputEnabled, "input locks at the win")
        // W: the clear wave + the celebration on the same beat; then the panel, then the route
        r.game.boardBeat(.lastExitLeftBoard)
        assertOrder(r.log, ["haptic.clear", "board.clearWave", "fx.celebration normal"])
        await settle(r)
        XCTAssertEqual(r.popups.presented.last, .winPanel)
        XCTAssertEqual(r.router.went.count, 1)
        if case .home(.afterWin(let s), _)? = r.router.went.last { XCTAssertEqual(s.reward, 20) } else {
            XCTFail("routed to \(String(describing: r.router.went.last))")
        }
        XCTAssertNil(r.log.index("haptic.win"), "the win haptic is the celebration's (S2), never GAME's")
    }

    // MARK: the fail chains (C3 + S2 popups)

    func testTimeOutChainDeclinedEndsInLevelFailedAndCostsTheLife() async {
        let r = makeRig(args: ["pc.timer": "2"], tune: ["game.fail.zeroHoldSeconds": "0"])
        ready(r)
        XCTAssertEqual(r.hud.timerText, "0:02")
        r.game.boardReleased(arrow: ArrowID(2), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        frames(r, 60 * 3)                                                   // 3 s of play: the clock runs out
        await settle(r)
        // no streak (x1): Out of Time! → Continue? (a life) → Level Failed
        XCTAssertEqual(Array(r.popups.presented.prefix(3)), [.outOfTime, .continueOffer, .levelFailed], "\(r.popups.presented)")
        XCTAssertEqual(r.log.lines.filter { $0 == "haptic.fail" }.count, 1, "one warning, on the first offer's frame")
        XCTAssertEqual(r.store.state.lives.count, 4, "the life taken at the start stays spent")
        XCTAssertEqual(r.store.state.stats.losses, 1)
        XCTAssertNil(r.store.state.activeAttempt)
        XCTAssertEqual(r.router.went.last, .home(.afterLoss, tab: .home), "X on Level Failed → home (home seen)")
    }

    func testHeartsOutOfferPaidRefillsTheHearts() async {
        let r = makeRig(args: ["pc.hearts": "1"], tune: ["game.fail.heartsOutDelay": "0"])
        r.popups.payFirst = [.outOfTime]
        r.popups.script[.outOfTime] = [.primary]
        ready(r)
        let coins0 = r.store.state.coins
        r.game.boardReleased(arrow: ArrowID(1), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        r.game.boardBeat(.bumpContact(ArrowID(1)))
        if case .offer(let o)? = r.game.session?.phase { XCTAssertEqual(o.kind, .outOfHearts) } else { XCTFail("no offer") }
        await settle(r)
        XCTAssertEqual(r.popups.presented.first, .outOfTime, "Out of Lives! uses the Out of Time! layout (variant hearts)")
        XCTAssertEqual(r.store.state.coins, coins0 - 900, "Add Lives costs 900 (Economy.spend)")
        XCTAssertEqual(r.game.session?.hearts, 3)
        XCTAssertEqual(r.game.session?.phase, .playing(stage: 0))
        XCTAssertEqual(r.hud.hearts, [.full, .full, .full])
    }

    // MARK: holds keep the timer constant

    func testPauseAndPopupsHoldTheTimer() async {
        let r = makeRig()
        ready(r)
        frames(r, 60)
        XCTAssertEqual(r.game.session?.clock.remaining, 180, "frozen until the first tap")
        r.game.boardReleased(arrow: ArrowID(2), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        frames(r, 30)
        let running = r.game.session!.clock.remaining
        XCTAssertLessThan(running, 180)
        r.popups.hold = [.pause]
        r.game.flow.pause()
        await settle(r, frames: 0)
        frames(r, 180)
        XCTAssertEqual(r.game.session!.clock.remaining, running, accuracy: 1e-9, "Pause holds the timer")
        XCTAssertFalse(r.board.inputEnabled)
        r.popups.release(.pause, .primary)
        await settle(r, frames: 0)
        frames(r, 30)
        XCTAssertLessThan(r.game.session!.clock.remaining, running, "Resume releases it")
        XCTAssertTrue(r.board.inputEnabled)
    }

    func testBackgroundHoldsAndReturnsToPause() async {
        let r = makeRig()
        ready(r)
        r.game.boardReleased(arrow: ArrowID(2), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        frames(r, 10)
        let before = r.game.session!.clock.remaining
        r.game.appDidEnterBackground()
        frames(r, 120)
        XCTAssertEqual(r.game.session!.clock.remaining, before, accuracy: 1e-9)
        r.popups.hold = [.pause]
        r.game.appDidBecomeActive()
        await settle(r, frames: 1)
        XCTAssertEqual(r.popups.presented.last, .pause, "the Pause popup on the return (§8.6)")
    }

    // MARK: quit

    func testQuitGoesStraightToLevelFailed() async {
        let r = makeRig()
        r.popups.script[.quitLevel] = [.primary]
        r.popups.script[.levelFailed] = [.primary]
        ready(r)
        r.game.flow.back()
        await settle(r)
        XCTAssertEqual(r.popups.presented, [.quitLevel, .levelFailed], "Quit → Level Failed, no offers (SPEC-gameplay §7.2)")
        XCTAssertEqual(r.router.went.last.map { if case .level(let l) = $0 { return l.isRetry } else { return false } }, true,
                       "Try Again = the same board")
        XCTAssertEqual(r.store.state.stats.losses, 1)
    }

    // MARK: multi-board sessions

    func testLevels1to4StageTransitionOneWin() async {
        let plan = SessionPlan(id: "L1-4", levels: [901, 902], hudLabel: "Levels 1-4", panelLabel: "Level 1-4", reward: 80,
                               stageGap: 0.7, hearts: .carry)
        let r = makeRig(levels: [Self.tinyLevel(901), Self.tinyLevel(902)], plan: plan)
        ready(r)
        r.game.boardReleased(arrow: ArrowID(2), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        r.game.boardReleased(arrow: ArrowID(1), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        XCTAssertEqual(r.game.session?.phase, .stageClear(stage: 0))
        r.game.boardBeat(.lastExitLeftBoard)
        XCTAssertNotNil(r.log.index("board.stageTransition L902"))
        r.game.boardBeat(.stageTransitionDone)
        XCTAssertEqual(r.game.session?.phase, .ready(stage: 1))
        r.game.boardReleased(arrow: ArrowID(2), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        r.game.boardReleased(arrow: ArrowID(1), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        XCTAssertEqual(r.store.state.pendingCoinFly, 80, "one session, one reward (80)")
        XCTAssertEqual(r.store.state.stats.wins, 2, "a multi-board session counts each of its levels")
    }

    /// CONSISTENCY T-7: the session's stage gap and board.json's default agree.
    func testStageGapKeysAgree() throws {
        let folder = try XCTUnwrap(Bundle.main.resourceURL?.appendingPathComponent("Levels"))
        let lib = try LevelLibrary.load(folder: folder)
        let gap = try XCTUnwrap(lib.session(containing: 1).stageGap)
        XCTAssertEqual(gap, Tuning.load(bundle: .main).board.stageGap, accuracy: 1e-9)
    }

    // MARK: HUD rate

    func testHUDWritesStayUnderTenPerSecond() {
        let r = makeRig(args: ["pc.timer": "120"])
        ready(r)
        r.game.boardReleased(arrow: ArrowID(2), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
        r.log.clear()
        frames(r, 60 * 60)                                                  // 60 s of play at 60 Hz
        let writes = r.log.lines.filter { $0.hasPrefix("hud.") }.count
        XCTAssertLessThanOrEqual(Double(writes) / 60, 10, "\(writes) writes in 60 s")
        XCTAssertGreaterThanOrEqual(r.log.lines.filter { $0 == "hud.timerText" }.count, 59, "the timer text still ticks each second")
    }
}

// MARK: - the reference game's input on the generic controller

extension GameController {
    /// A released arrow (nil = an empty point), as ArrowPuzzleBoard forwards the engine's release to the Play.
    func boardReleased(arrow: ArrowID?, contentPoint: CGPoint, touchTimestamp: TimeInterval) {
        ArrowPuzzleBoard.forward(release: arrow, touchTimestamp: touchTimestamp, to: self)
    }

    /// An engine beat, as ArrowPuzzleBoard forwards it (acks + the burst haptic).
    func boardBeat(_ beat: BoardBeat) { ArrowPuzzleBoard.forward(beat, to: self) }

    /// Arrow Out's `LevelSession` behind the generic session (for arrow-specific assertions).
    var levelSession: LevelSession? { (session as? ArrowPuzzleSession)?.core }
}
