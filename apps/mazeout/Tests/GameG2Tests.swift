import XCTest
import UIKit
@testable import ArrowOut
import PathCore

/// GAME G2 (SPEC-architecture §8.4, §12.2 G2 acceptance) with G1's fakes (GameControllerTests: a fake board, popups, FX,
/// router, audio, haptics) and a real PlayerStore on a temp directory. G2's real directors run (`GameDirectors.make`):
///  - the tutorial step shows at the stage's ready beat, is dismissed by the first accepted tap and is never shown again;
///  - the unlock overlay shows once per feature, before the timer can start, and not on a retry;
///  - the hourglass freezes the level clock for flight + 10 s of running time (the HUD freeze effect at B; used before the
///    first tap it flies at once and its tray holds "10" until that tap, SPEC.md ruling 30), the bulb hints C2's unit, each is
///    inert while its effect runs, 0 stock → the popup;
///  - a scripted sequence of wins and a loss leaves exactly C3's event state (multiplier, Claw points, Sky Jump, Rocket Race);
///  - the local-notification plan (lives full, the Weekly Contest ending).
@MainActor final class GameG2Tests: XCTestCase {
    typealias G = GameControllerTests

    struct Rig {
        let game: GameController
        let log: G.Recorder
        let board: G.FakeBoard
        let popups: G.FakePopups
        let router: G.FakeRouter
        let store: PlayerStore
        let hud: HUDModel
    }

    private var t = 1000.0
    private var scriptsBackup: ((GameController) -> [TutorialScript])?
    private var unlocksBackup: ((GameController) -> [FeatureUnlock])?

    override func setUp() {
        continueAfterFailure = false
        scriptsBackup = TutorialDirector.source
        unlocksBackup = UnlockDirector.source
    }

    override func tearDown() {
        if let s = scriptsBackup { TutorialDirector.source = s }
        if let u = unlocksBackup { UnlockDirector.source = u }
    }

    static func level(_ n: Int, timer: Int = 180) -> LevelSpec { G.tinyLevel(n, timer: timer) }

    /// A store shared by several Plays (the events sequence).
    func makeStore(_ pairs: [String: String]) -> (PlayerStore, LaunchArgs, Tuning, RulesTuning, EconomyRules) {
        let args = LaunchArgs(pairs: pairs)
        let tuning = Tuning.load(bundle: .main, tune: [:])
        let rules = RulesTuning.load(json: tuning.rules.data, overrides: tuning.rules.overrides).rules
        let economy = EconomyRules.load(rules: tuning.rules.data, social: tuning.social.file.data, overrides: tuning.rules.overrides).rules
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("g2-\(UUID().uuidString)")
        let store = PlayerStore(args: args, now: MotionClock(args: args).wallClock(), bundle: .main, directory: dir, rules: economy,
                                debounce: 0.05)
        return (store, args, tuning, rules, economy)
    }

    func makeRig(_ pairs: [String: String] = [:], levels: [LevelSpec] = [G.tinyLevel()], launchLevel: Int? = nil,
                 isRetry: Bool = false, plan: SessionPlan? = nil,
                 shared: (PlayerStore, LaunchArgs, Tuning, RulesTuning, EconomyRules)? = nil,
                 fx: (any FXPlaying)? = nil) -> Rig {
        var p = ["pc.seed": "7"]
        for (k, v) in pairs { p[k] = v }
        let (store, args, tuning, rules, economy) = shared ?? makeStore(p)
        let log = G.Recorder()
        let board = G.FakeBoard(log), popups = G.FakePopups(log), router = G.FakeRouter()
        let hud = HUDModel()
        let byNumber = Dictionary(uniqueKeysWithValues: levels.map { ($0.level, $0) })
        let first = launchLevel ?? levels[0].level
        let thePlan = plan ?? SessionPlan(id: "L\(first)", levels: [first])
        let services = GameServices(
            args: args, tuning: tuning, rules: rules, economy: economy, clock: MotionClock(args: args), store: store, hud: hud,
            board: board, audio: G.FakeAudio(log), haptics: G.FakeHaptics(log), popups: popups, fx: fx ?? G.FakeFX(log), router: router,
            latency: LatencyProbe(), perf: PerfMonitor(),
            level: { byNumber[$0] }, plan: { _ in thePlan },
            rivals: { SocialWorld(installSeed: 7, config: .default, names: NameBank()) },
            screenSize: { CGSize(width: 393, height: 852) },
            screenAfterWin: { .home(.afterWin($0), tab: .home) },
            screenAfterLoss: { GameServices.defaultAfterLoss($0, tryAgain: $1, homeSeen: true) },
            levelStarted: { _ in }, app: nil)
        let launch = LevelLaunch(session: thePlan.id, levels: thePlan.levels, isRetry: isRetry)
        let game = GameController(launch, services: services)             // G2's directors through GameDirectors.make
        return Rig(game: game, log: log, board: board, popups: popups, router: router, store: store, hud: hud)
    }

    func frames(_ r: Rig, _ n: Int) {
        for _ in 0..<n {
            t += 1.0 / 60
            r.game.boardFrame(timestamp: t, targetTimestamp: t + 1.0 / 60)
        }
    }

    func settle(_ r: Rig, frames n: Int = 3) async {
        for _ in 0..<8 {
            for _ in 0..<10 { await Task.yield() }
            frames(r, n)
        }
    }

    func tap(_ r: Rig, _ a: Int) {
        r.game.boardReleased(arrow: ArrowID(a), contentPoint: .zero, touchTimestamp: CACurrentMediaTime())
    }

    /// Wins the tiny board (2 then 1) and runs W → the panel → the route.
    func win(_ r: Rig) async {
        tap(r, 2); tap(r, 1)
        r.game.boardBeat(.lastExitLeftBoard)
        await settle(r)
    }

    func directors<T>(_ r: Rig, _ type: T.Type) -> T? { r.game.extra.compactMap { $0 as? T }.first }

    /// Display-link frames with the main actor's queued work (the directors' frame waits, popups) run in between.
    func pump(_ r: Rig, frames n: Int) async {
        for _ in 0..<n {
            frames(r, 1)
            for _ in 0..<4 { await Task.yield() }
        }
    }

    /// FIX-A2: every FX call with its custom id and params (the freeze's hold / resume edges).
    @MainActor final class FXCalls: FXPlaying {
        struct Call: CustomStringConvertible {
            let id: String
            let params: [String: Double]
            let handle: FXHandle
            var description: String { "\(id)\(params.isEmpty ? "" : "\(params)")" }
        }
        private(set) var calls: [Call] = []
        private var n = 0
        func play(_ effect: FXEffect) -> FXHandle {
            n += 1
            let h = FXHandle(id: n)
            if case .custom(let id, let params) = effect { calls.append(Call(id: id, params: params, handle: h)) }
            else { calls.append(Call(id: "other", params: [:], handle: h)) }
            return h
        }
        func finished(_ handle: FXHandle) async {}
        func skip(_ handle: FXHandle) {}
        func stop(_ handle: FXHandle) { calls.append(Call(id: "stop", params: ["handle": Double(handle.id)], handle: handle)) }
        func stopAll() {}
        var isPlaying: Bool { false }
        func handle(_ id: String) -> FXHandle? { calls.first { $0.id == id }?.handle }
        /// The `on` values of every freezeHold, in order.
        var holds: [Double] { calls.filter { $0.id == "freezeHold" }.map { $0.params["on"] ?? -1 } }
    }

    // MARK: the tutorial

    func testTapToMoveShowsAtTheReadyBeatAndGoesAtTheFirstTap() {
        TutorialDirector.source = { _ in
            [TutorialScript(id: "tapToMove", level: 900, stage: 0, trigger: .stageReady, caption: "Tap to move!",
                            hand: TutorialHand(arrow: ArrowID(2), at: [3.0, 1.5]), dismiss: .anyTap, holdTimer: false)]
        }
        let r = makeRig()
        XCTAssertTrue(r.game.start())
        XCTAssertNotNil(directors(r, TutorialDirector.self))
        XCTAssertFalse(r.game.hint.isShown, "nothing before the board's ready beat")
        r.game.boardBeat(.introFinished)
        XCTAssertTrue(r.game.hint.isShown, "shown on the ready beat (not from Loading: K + ack)")
        XCTAssertEqual(r.game.session?.clock.started, false, "holdTimer false: the timer still waits for the first tap")
        XCTAssertNil(r.board.allowedArrows, "anyTap: no input restriction")
        tap(r, 2)
        XCTAssertNotNil(r.game.hint.dismissedAt, "the first accepted tap dismisses it")
        XCTAssertEqual(r.game.session?.clock.started, true, "…and starts the timer as always")
        XCTAssertTrue(r.store.state.tutorialsDone.contains("tapToMove"))

        // never again: a new Play of the same level shows nothing
        let r2 = makeRig(shared: nil)
        r2.store.mutateAndSave { $0.tutorialsDone.insert("tapToMove") }
        XCTAssertTrue(r2.game.start())
        r2.game.boardBeat(.introFinished)
        XCTAssertFalse(r2.game.hint.isShown)
    }

    func testTutorialIsOffUnderUITestUnlessForced() {
        TutorialDirector.source = { _ in [TutorialScript(id: "tapToMove", level: 900, caption: "Tap to move!", hand: TutorialHand(arrow: ArrowID(2)))] }
        let quiet = makeRig(["pc.uitest": "1"])
        XCTAssertTrue(quiet.game.start()); quiet.game.boardBeat(.introFinished)
        XCTAssertFalse(quiet.game.hint.isShown, "-pc.uitest: hints off")
        let forced = makeRig(["pc.uitest": "1", "pc.tutorials": "force"])
        XCTAssertTrue(forced.game.start()); forced.game.boardBeat(.introFinished)
        XCTAssertTrue(forced.game.hint.isShown, "-pc.tutorials force shows it")
    }

    func testABumpAlsoDismissesAndATargetTapStepRestrictsInput() {
        TutorialDirector.source = { _ in [TutorialScript(id: "any", level: 900, caption: "Tap to move!", hand: TutorialHand(arrow: ArrowID(2)))] }
        let b = makeRig()
        XCTAssertTrue(b.game.start()); b.game.boardBeat(.introFinished)
        XCTAssertTrue(b.game.hint.isShown)
        tap(b, 1)                                                            // arrow 1 is blocked by 2: a bump
        XCTAssertNotNil(b.game.hint.dismissedAt, "a bump is an accepted tap too (anyTap)")

        TutorialDirector.source = { _ in [TutorialScript(id: "only1", level: 900, caption: "Tap to move!",
                                                          hand: TutorialHand(arrow: ArrowID(2)), dismiss: .targetTap)] }
        let r = makeRig()
        XCTAssertTrue(r.game.start()); r.game.boardBeat(.introFinished)
        XCTAssertEqual(r.board.allowedArrows, [ArrowID(2)], "targetTap: only the hand's arrow takes input")
        tap(r, 2)
        XCTAssertNil(r.board.allowedArrows)
        XCTAssertTrue(r.store.state.tutorialsDone.contains("only1"))
    }

    // MARK: the unlock overlay

    func testUnlockOverlayOnceBeforeTheTimerAndNotOnARetry() async {
        UnlockDirector.source = { _ in [FeatureUnlock(feature: "linked", level: 900, title: "Linked Arrows!", card: "LINKED ARROWS move together!")] }
        let shared = makeStore(["pc.seed": "7"])
        let r = makeRig(shared: shared)
        r.popups.hold = [.unlockOverlay]
        XCTAssertTrue(r.game.start())
        await settle(r)
        XCTAssertEqual(r.popups.presented, [.unlockOverlay], "the overlay comes up with the level's cut")
        XCTAssertTrue(r.store.state.unlocksSeen.contains("linked"), "marked (and saved) when shown")
        r.game.boardBeat(.introFinished)
        frames(r, 2)
        XCTAssertFalse(r.board.inputEnabled, "input stays closed while the overlay is up")
        let t0 = r.game.session?.clock.remaining
        frames(r, 120)
        XCTAssertEqual(r.game.session?.clock.remaining, t0, "the timer is frozen under the overlay")
        r.popups.release(.unlockOverlay, .close)
        await settle(r)
        XCTAssertTrue(r.board.inputEnabled, "the board is playable after the dismissal")
        XCTAssertEqual(r.game.session?.clock.started, false, "the timer waits for the first tap")

        // a second Play of the same level (the feature seen) and a retry: no overlay
        let again = makeRig(shared: shared)
        XCTAssertTrue(again.game.start()); await settle(again)
        XCTAssertFalse(again.popups.presented.contains(.unlockOverlay))
    }

    // MARK: boosters

    func testHourglassFreezesFlightPlusTenSecondsOfRunningTime() async {
        let r = makeRig(["pc.boosters": "freeze=3,hint=3"])
        XCTAssertTrue(r.game.start()); r.game.boardBeat(.introFinished)
        tap(r, 2)                                                            // the timer runs
        frames(r, 60)
        let before = r.game.session!.clock.remaining
        r.game.boosterTapped(BoosterID("freeze"))
        XCTAssertEqual(r.store.state.boosters["freeze"], 2, "one taken from the stock")
        XCTAssertEqual(r.hud.boosters.first { $0.id.rawValue == "freeze" }?.state, .stock(2), "the badge shows n − 1 at once")
        XCTAssertNotNil(r.log.index("fx.other"), "S2's HUD freeze starts at B: \(r.log.lines)")
        XCTAssertNotNil(r.log.index("haptic.booster"))
        let total = r.game.services.rules.boosters.freezeTotal
        XCTAssertEqual(total, 11.6, accuracy: 1e-9, "flight 1.6 + 10 s (K-3)")
        r.game.boosterTapped(BoosterID("freeze"))
        XCTAssertEqual(r.store.state.boosters["freeze"], 2, "inert while its own freeze runs (K-7)")
        frames(r, Int(total * 60) - 6)
        XCTAssertEqual(r.game.session!.clock.remaining, before, accuracy: 1e-9, "frozen through flight + countdown")
        frames(r, 12)
        XCTAssertLessThan(r.game.session!.clock.remaining, before, "the timer resumes after the freeze")
        XCTAssertEqual(directors(r, BoosterDirector.self)?.freeze, .idle)
        r.game.boosterTapped(BoosterID("freeze"))
        XCTAssertEqual(r.store.state.boosters["freeze"], 1, "usable again")
    }

    /// SPEC.md ruling 30 (K-4, 21:12): before the first tap the stock is taken at B and the hourglass flies AT ONCE; the tray holds
    /// "10" until the first board tap, which starts the timer and the 10 s countdown (the flight already flown is not frozen again).
    func testHourglassBeforeTheFirstTapFliesAtOnceAndCountsFromTheFirstTap() {
        let r = makeRig(["pc.boosters": "freeze=3"])
        XCTAssertTrue(r.game.start()); r.game.boardBeat(.introFinished)
        r.game.boosterTapped(BoosterID("freeze"))
        XCTAssertEqual(r.store.state.boosters["freeze"], 2)
        XCTAssertEqual(r.log.lines.filter { $0 == "fx.other" }.count, 1, "the flight + the held tray start at B: \(r.log.lines)")
        XCTAssertEqual(directors(r, BoosterDirector.self)?.freeze, .pendingFirstTap)
        frames(r, 600)
        // FIX-A2, changed pin (was 11.6; SPEC.md ruling 30 through CORE-2's `clock.freeze(_:lead:)`): the core counts the 1.6 s
        // flight from B itself now (the app no longer takes it off at the first tap), so after 10 s of pre-tap frames 10 s
        // remain — and they wait: the countdown is never wasted before the start. Equally strong: the exact value + the
        // clock's own "waits for the first tap" state + the level timer untouched.
        XCTAssertEqual(r.game.session!.clock.freezeRemaining, 10, accuracy: 1e-9, "the flight counted from B; the 10 s wait for the tap")
        XCTAssertTrue(r.game.session!.clock.freezeWaitsForFirstTap, "the tray holds \"10\" (ruling 30)")
        XCTAssertEqual(r.game.session!.clock.freezeLead, 0, "the flight is over")
        XCTAssertEqual(r.game.session!.clock.remaining, 180, accuracy: 1e-9, "the level timer never moved")
        let limit = r.game.session!.clock.remaining
        tap(r, 2)
        XCTAssertEqual(r.log.lines.filter { $0 == "fx.other" }.count, 2, "the first tap starts the held countdown: \(r.log.lines)")
        XCTAssertEqual(directors(r, BoosterDirector.self)?.freeze, .running)
        XCTAssertEqual(r.game.session!.clock.freezeRemaining, 10, accuracy: 1e-9, "the flight was flown at B: 10 s of countdown left")
        XCTAssertEqual(r.game.session!.clock.remaining, limit, accuracy: 1e-9, "the flown flight never moves the level timer")
        frames(r, 600 - 6)
        XCTAssertEqual(r.game.session!.clock.remaining, limit, accuracy: 1e-9, "frozen through the 10 s countdown")
        frames(r, 12)
        XCTAssertLessThan(r.game.session!.clock.remaining, limit, "the timer runs when the tray's countdown ends")
        XCTAssertEqual(directors(r, BoosterDirector.self)?.freeze, .idle)
    }

    /// Ruling 30 with the first tap DURING the flight: the rest of the flight + 10 s, i.e. the countdown ends at B + 1.60 + 10.
    func testHourglassBeforeTheFirstTapTappedDuringTheFlight() {
        let r = makeRig(["pc.boosters": "freeze=3"])
        XCTAssertTrue(r.game.start()); r.game.boardBeat(.introFinished)
        r.game.boosterTapped(BoosterID("freeze"))
        frames(r, 30)                                                         // 0.5 s into the 1.6 s flight
        tap(r, 2)
        XCTAssertEqual(r.game.session!.clock.freezeRemaining, 11.1, accuracy: 0.02, "1.1 s of flight left + 10 s")
    }

    /// FIX-A2 (G2's request "freeze HUD effect pausable"): the HUD freeze follows the session's clock holds — Pause holds it
    /// (the core's freeze stands still with it), Resume lets both run again, a popup does the same, and the core's
    /// `.freezeEnded` comes exactly the held spans later (the effect ends on its own clock at that moment).
    func testTheFreezeEffectHoldsAndResumesWithTheSessionClock() async {
        let fx = FXCalls()
        let r = makeRig(["pc.boosters": "freeze=3"], fx: fx)
        XCTAssertTrue(r.game.start()); r.game.boardBeat(.introFinished)
        tap(r, 2)                                                            // the timer runs
        frames(r, 30)
        r.game.boosterTapped(BoosterID("freeze"))
        let h = fx.handle("freeze")
        XCTAssertNotNil(h, "S2's HUD freeze at B: \(fx.calls)")
        await pump(r, frames: 60)                                            // 1 s of the freeze
        XCTAssertEqual(fx.holds, [], "nothing holds the clock: the effect runs")
        let left = r.game.session!.clock.freezeRemaining
        XCTAssertEqual(left, 11.6 - 1, accuracy: 0.02)

        // Pause: the session holds (.pause + .popup) → the effect holds on the next frame
        r.popups.hold = [.pause]
        r.game.flow.pause()
        await pump(r, frames: 2)
        XCTAssertEqual(fx.holds, [1], "held with the session's clock: \(fx.calls)")
        XCTAssertEqual(fx.calls.last { $0.id == "freezeHold" }?.params["handle"], h.map { Double($0.id) }, "the running freeze's handle")
        await pump(r, frames: 300)                                           // 5 s paused
        XCTAssertEqual(r.game.session!.clock.freezeRemaining, left, accuracy: 1e-9, "the core's freeze stood still too")
        XCTAssertEqual(fx.holds, [1], "one edge, no chatter")

        // Resume → both run again
        r.popups.release(.pause, .primary)
        await pump(r, frames: 3)
        XCTAssertEqual(fx.holds, [1, 0], "resumed: \(fx.calls)")
        XCTAssertFalse(r.game.paused)

        // a popup over the level (the booster popup's kind of hold) does the same
        r.popups.hold = [.boosterBuy]
        let popup = Task { @MainActor in _ = await r.popups.present(Popup<PopupResult>.boosterBuy(BoosterID("hint"))) }
        await pump(r, frames: 3)
        XCTAssertEqual(fx.holds, [1, 0, 1], "a popup holds it")
        let atPopup = r.game.session!.clock.freezeRemaining
        await pump(r, frames: 120)
        XCTAssertEqual(r.game.session!.clock.freezeRemaining, atPopup, accuracy: 1e-9)
        r.popups.release(.boosterBuy, .close)
        _ = await popup.value
        await pump(r, frames: 3)
        XCTAssertEqual(fx.holds, [1, 0, 1, 0])

        // the rest of the freeze runs, then the timer: the stop edges above changed nothing else
        let rest = r.game.session!.clock.freezeRemaining
        XCTAssertGreaterThan(rest, 9)
        let limit = r.game.session!.clock.remaining
        await pump(r, frames: Int(rest * 60) - 6)
        XCTAssertEqual(r.game.session!.clock.remaining, limit, accuracy: 1e-9, "frozen until the freeze's own end")
        XCTAssertEqual(directors(r, BoosterDirector.self)?.freeze, .running)
        await pump(r, frames: 12)
        XCTAssertLessThan(r.game.session!.clock.remaining, limit, "the timer runs after the freeze")
        XCTAssertEqual(directors(r, BoosterDirector.self)?.freeze, .idle)
        let n = fx.holds.count
        r.popups.hold = [.pause]
        r.game.flow.pause()
        await pump(r, frames: 3)
        XCTAssertEqual(fx.holds.count, n, "no freeze running: nothing to hold")
        r.popups.release(.pause, .primary)
    }

    /// FIX-A2: the HUD freeze's layers stand still while held and continue from the same instant — on a slow-motion host too
    /// (the FX host mirrors `-pc.slowmo`), which is where a naive `speed = 1` resume would jump.
    func testTheFreezeLayersStopAndContinueTheirOwnTime() async throws {
        let ui = Tuning.load(bundle: .main).ui
        for hostSpeed in [1.0, 0.25] as [Float] {
            let host = CALayer()
            host.bounds = CGRect(x: 0, y: 0, width: 393, height: 852)
            host.speed = hostSpeed
            let t0 = host.convertTime(CACurrentMediaTime(), from: nil)
            let parts = HUDFreezeFX.build(host: host, t0: t0, seconds: 10, ui: ui, safeTop: 59, hold: false)
            host.addSublayer(parts.root)
            try await Task.sleep(nanoseconds: 100_000_000)
            let a = HUDFreezeFX.localTime(parts)
            XCTAssertGreaterThan(a - t0, 0.05 * Double(hostSpeed), "running before the hold")
            HUDFreezeFX.hold(parts, true)
            let held = HUDFreezeFX.localTime(parts)
            try await Task.sleep(nanoseconds: 300_000_000)
            XCTAssertEqual(HUDFreezeFX.localTime(parts), held, accuracy: 1e-9, "held: the parts' time stands still (host speed \(hostSpeed))")
            HUDFreezeFX.hold(parts, true)                                       // a second hold changes nothing
            XCTAssertEqual(HUDFreezeFX.localTime(parts), held, accuracy: 1e-9)
            HUDFreezeFX.hold(parts, false)
            XCTAssertEqual(HUDFreezeFX.localTime(parts), held, accuracy: 0.004, "resumed at the instant it was held")
            let r0 = CACurrentMediaTime(), l0 = HUDFreezeFX.localTime(parts)
            try await Task.sleep(nanoseconds: 200_000_000)
            let ran = HUDFreezeFX.localTime(parts) - l0, wall = CACurrentMediaTime() - r0
            XCTAssertEqual(ran, wall * Double(hostSpeed), accuracy: 0.004, "runs again at the host's rate (host speed \(hostSpeed))")
            parts.root.removeFromSuperlayer()
        }
        FreezeHUDState.shared.cancel()
    }

    /// SPEC.md ruling 31 (FIX-A2): the bulb shows the rules' `unblocksMost` unit through CORE-2's `hint(policy:)`, not the
    /// greedy first free unit (`session.hint()`, which BoardLab and the HeadlessDriver keep). The board is PathCore
    /// HintPolicyTests' `differing` (worked out by hand there): a0 (0,3)(1,3) → free, nobody's ray crosses it; a1 (4,1)(4,0) ↑
    /// free, and a2 (0,1)(1,1) → / a3 (0,0)(1,0) → both run into it — greedy picks a0, unblocksMost a1.
    func testBulbHintsTheUnblocksMostUnitNotTheGreedyOne() {
        let level = LevelSpec(level: 901, source: .designed, cols: 6, rows: 4, timerSeconds: 180, hearts: 3, tag: .normal, arrows: [
            ArrowSpec(id: ArrowID(0), cells: [Cell(0, 3), Cell(1, 3)], dir: .right),
            ArrowSpec(id: ArrowID(1), cells: [Cell(4, 1), Cell(4, 0)], dir: .up),
            ArrowSpec(id: ArrowID(2), cells: [Cell(0, 1), Cell(1, 1)], dir: .right),
            ArrowSpec(id: ArrowID(3), cells: [Cell(0, 0), Cell(1, 0)], dir: .right)])
        let r = makeRig(["pc.boosters": "hint=2"], levels: [level])
        XCTAssertTrue(r.game.start()); r.game.boardBeat(.introFinished)
        let session = r.game.session!
        XCTAssertEqual(r.game.services.rules.boosters.hintPolicy, .unblocksMost, "rules.json boosters.hintPolicy")
        XCTAssertEqual(session.hint(), [ArrowID(0)], "greedy (BoardLab, the HeadlessDriver): a0")
        XCTAssertEqual(Solver.hintUnit(session.board, policy: .unblocksMost), [ArrowID(1)], "the policy's unit: a1")
        r.log.clear()
        r.game.boosterTapped(BoosterID("hint"))
        XCTAssertEqual(r.store.state.boosters["hint"], 1, "one bulb taken")
        XCTAssertTrue(r.log.lines.contains { $0.hasPrefix("board.present") && $0.contains("other") }, "hintShown reaches the board: \(r.log.lines)")
        XCTAssertEqual(directors(r, BoosterDirector.self)?.hinted, [ArrowID(1)], "the bulb's .hintShown carries the policy's unit")
        XCTAssertEqual(session.clock.started, false, "the bulb never starts the timer")
        XCTAssertEqual(session.clock.freezeRemaining, 0, "a bulb freezes nothing")
        tap(r, 1)                                                            // the hinted arrow leaves → usable again
        XCTAssertNil(directors(r, BoosterDirector.self)?.hinted)
        // a0, a2, a3 are free now and none crosses another: the tie goes to the lowest id (both policies agree)
        r.game.boosterTapped(BoosterID("hint"))
        XCTAssertEqual(directors(r, BoosterDirector.self)?.hinted, [ArrowID(0)])
        XCTAssertEqual(r.store.state.boosters["hint"], 0)
    }

    func testBulbHintsTheSolverUnitAndIsInertUntilItLeaves() {
        let r = makeRig(["pc.boosters": "hint=1"])
        XCTAssertTrue(r.game.start()); r.game.boardBeat(.introFinished)
        r.log.clear()
        r.game.boosterTapped(BoosterID("hint"))
        XCTAssertEqual(r.store.state.boosters["hint"], 0)
        XCTAssertTrue(r.log.lines.contains { $0.hasPrefix("board.present") && $0.contains("other") }, "hintShown reaches the board: \(r.log.lines)")
        XCTAssertEqual(directors(r, BoosterDirector.self)?.hinted, [ArrowID(2)], "C2's unit: arrow 2 (the only free one)")
        XCTAssertEqual(r.game.session?.clock.started, false, "the bulb never starts the timer")
        XCTAssertEqual(r.hud.boosters.first { $0.id.rawValue == "hint" }?.state, .empty, "0 left → the + badge")
        tap(r, 2)
        XCTAssertNil(directors(r, BoosterDirector.self)?.hinted, "the hinted unit left: usable again")
    }

    func testZeroStockOpensTheBoosterPopupAndTakesNothing() async {
        let r = makeRig(["pc.boosters": "freeze=0,hint=0"])
        XCTAssertTrue(r.game.start()); r.game.boardBeat(.introFinished)
        let coins = r.store.state.coins
        r.game.boosterTapped(BoosterID("freeze"))
        await settle(r)
        XCTAssertEqual(r.popups.presented, [.boosterBuy])
        XCTAssertEqual(r.store.state.coins, coins, "X: nothing bought")
        XCTAssertNil(r.log.index("fx.other"))
        r.game.boosterTapped(BoosterID("hint"))
        await settle(r)
        XCTAssertEqual(r.popups.presented, [.boosterBuy, .boosterBuy])
    }

    // MARK: events (C3 rules through the real attempt glue)

    func testScriptedWinsAndALossLeaveExactlyC3sEventState() async throws {
        // a player at L55 (every event unlocked) on a fixed clock, in a Sky Jump run and a Rocket Race.
        // B1 re-pin (requirement change, SPEC.md ruling 38 / PUBLISH item 14: the featured events rotate weekly; the same
        // assertions): the clock moves from 2026-09-28 (week 22 = Up & Away + Double) to 2026-11-11 (week 28 = Treasure
        // Climb + Double Event Week), the week in which the Claw, Rocket Rally and Cloud Hop all run, as every week did in
        // the v552 plan this test was written against (EventRotationTests pins the calendar)
        let pairs = ["pc.seed": "7", "pc.level": "55", "pc.now": "2026-11-11T12:00:00Z", "pc.clockRate": "0"]
        let shared = makeStore(pairs)
        let (store, args, _, _, rules) = shared
        let now = MotionClock(args: args).wallClock()
        let rivals = SocialWorld(installSeed: 7, config: .default, names: NameBank())
        store.mutateAndSave { s in
            _ = Events.refresh(&s, now: now, rivals: rivals, me: s.social.standing(installSeed: s.installSeed, level: s.level),
                               rules: rules, home: true)
            _ = Events.joinSkyJump(&s, now: now, rules: rules)
            _ = Events.joinRocketRace(&s, now: now, rules: rules)
        }
        XCTAssertNotNil(store.state.events.sky.active, "joined a Sky Jump run")
        XCTAssertNotNil(store.state.events.rocket.active, "joined a Rocket Race")
        var ref = store.state                                                // C3 alone, the same inputs
        let levels = (55...59).map { Self.level($0) }
        var outcomes: [[EventOutcome]] = []
        var refOutcomes: [[EventOutcome]] = []

        func play(_ n: Int, win: Bool, retry: Bool = false) async {
            let r = makeRig(levels: levels, launchLevel: n, isRetry: retry, shared: shared)
            XCTAssertTrue(r.game.start())
            _ = Economy.startAttempt(&ref, levels: [n], now: now, rules: rules)
            r.game.boardBeat(.introFinished)
            if win {
                await self.win(r)
                let res = try! XCTUnwrap(r.game.win.result)
                outcomes.append(r.game.win.outcomes)
                Economy.finishAttempt(&ref, outcome: .won(res), now: now, rules: rules)
                refOutcomes.append(Events.onWin(&ref, WinContext(levels: [n], tag: res.tag, firstTry: res.firstTry, now: now),
                                                rivals: rivals, rules: rules))
            } else {
                tap(r, 2)
                r.game.fanOut(r.game.session!.quit(), origin: .director)       // Quit → Level Failed
                await settle(r)
                Economy.finishAttempt(&ref, outcome: .lost(.quit), now: now, rules: rules)
                refOutcomes.append(Events.onLoss(&ref, LossContext(levels: [n], reason: .quit, now: now), rules: rules))
                outcomes.append(refOutcomes.last!)
            }
            r.game.teardown()
        }

        await play(55, win: true)
        await play(56, win: true)
        await play(57, win: false)
        await play(57, win: true, retry: true)
        await play(58, win: true)

        XCTAssertEqual(store.state.events, ref.events, "the glue leaves exactly C3's event state")
        XCTAssertEqual(outcomes, refOutcomes, "and reports exactly C3's outcomes")
        // the rules, spelled out (SPEC-gameplay §11.1-§11.4)
        let mult = outcomes.map { $0.compactMap { o -> String? in if case .multiplier(let a, let b) = o { return "\(a)>\(b)" }; return nil } }
        XCTAssertEqual(mult[0], ["1>5"]); XCTAssertEqual(mult[1], ["5>10"]); XCTAssertEqual(mult[3], ["1>5"]); XCTAssertEqual(mult[4], ["5>10"])
        XCTAssertEqual(store.state.events.streakStep, 2, "x10 after win, win, LOSS (→ x1), win, win")
        let claw = outcomes.flatMap { $0 }.compactMap { o -> Int? in if case .clawPoints(let a, _, _) = o { return a }; return nil }
        XCTAssertEqual(claw, [1, 5, 1, 5], "Claw points = the multiplier before each win; the loss removes none")
        XCTAssertNil(store.state.events.sky.active, "the loss failed the Sky Jump run")
        XCTAssertTrue(outcomes[2].contains(.skyJumpFailed) || store.state.events.sky.lastResult == .failed)
        XCTAssertEqual(store.state.events.rocket.active?.progress, 4, "every win +1 (first try or not); the loss changes nothing")
        XCTAssertEqual(store.state.stats.firstTryWins, ref.stats.firstTryWins)
    }

    // MARK: local notifications

    func testNotificationPlanLivesFullAndWeeklyEnding() throws {
        let (store, args, tuning, _, rules) = makeStore(["pc.seed": "7", "pc.level": "60", "pc.lives": "3", "pc.livesNextIn": "600",
                                                       "pc.now": "2026-09-28T12:00:00Z", "pc.clockRate": "0"])
        let now = MotionClock(args: args).wallClock()
        var p = LocalNotifications.plan(store.state, now: now, rules: rules, tuning: tuning.game)
        XCTAssertEqual(try XCTUnwrap(p.livesFullIn), 600 + rules.lives.refillSeconds, accuracy: 1, "3 → 5 lives: the next one + one interval")
        XCTAssertNil(p.weeklyEndingIn, "not in this week's contest yet")
        store.mutateAndSave { s in
            _ = Events.onWin(&s, WinContext(levels: [60], tag: .normal, firstTry: true, now: now),
                             rivals: SocialWorld(installSeed: 7, config: .default, names: NameBank()), rules: rules)
        }
        p = LocalNotifications.plan(store.state, now: now, rules: rules, tuning: tuning.game)
        let ends = try XCTUnwrap(Events.status(store.state, now: now, rules: rules).weekly?.endsAt)
        XCTAssertEqual(try XCTUnwrap(p.weeklyEndingIn), Double(ends.seconds) - now.timeIntervalSince1970 - 7200, accuracy: 1,
                       "2 h before Monday 07:00 UTC")
        store.mutateAndSave { $0.settings.notifications = false }
        XCTAssertEqual(LocalNotifications.plan(store.state, now: now, rules: rules, tuning: tuning.game), .init(), "Settings OFF: nothing")
    }
    // MARK: B1 — Up & Away's fall page (VERIFIED v582, build/p/PH0/balloon.md §5)

    func testUpAndAwayFallPageComesBeforeLevelFailedOnlyForAStreakOfTwoOrMore() async throws {
        // week 22 (Up & Away + Double) at L45, the shipped rotation: win, win (streak 2), Quit → the fall page, then Level
        // Failed; win (streak 1), Quit → Level Failed alone (v582 showed the page from 3 and not from 1; DECISION: from 2)
        let shared = makeStore(["pc.seed": "7", "pc.level": "45", "pc.now": "2026-09-30T12:00:00Z", "pc.clockRate": "0",
                                "pc.unlimitedLives": "86400"])
        let (store, _, _, _, rules) = shared
        XCTAssertTrue(rules.events.rotation.enabled, "precondition: the shipped social.json runs the calendar")
        let levels = (45...50).map { Self.level($0) }
        func play(_ n: Int, win: Bool) async -> [String] {
            let r = makeRig(levels: levels, launchLevel: n, shared: shared)
            XCTAssertTrue(r.game.start())
            r.game.boardBeat(.introFinished)
            if win {
                await self.win(r)
            } else {
                tap(r, 2)
                r.game.fanOut(r.game.session!.quit(), origin: .director)     // Quit → the chain's end
                await settle(r)
            }
            r.game.teardown()
            return r.log.lines.filter { $0.hasPrefix("popup.") }
        }
        _ = await play(45, win: true)
        _ = await play(46, win: true)
        XCTAssertEqual(store.state.events.balloon.streak, 2)
        let lostTwo = await play(47, win: false)
        let fall = try XCTUnwrap(lostTwo.firstIndex(of: "popup.custom"), "the fall page: \(lostTwo)")
        let failed = try XCTUnwrap(lostTwo.firstIndex(of: "popup.levelFailed"), "\(lostTwo)")
        XCTAssertLessThan(fall, failed, "the fall page first, its X leads to Level Failed")
        XCTAssertEqual(store.state.events.balloon.streak, 0, "the loss reset the counter")
        XCTAssertEqual(store.state.events.balloon.best, 2)
        _ = await play(47, win: true)
        let lostOne = await play(48, win: false)
        XCTAssertFalse(lostOne.contains("popup.custom"), "a lost 1 shows no fall page: \(lostOne)")
        XCTAssertTrue(lostOne.contains("popup.levelFailed"))
    }
}
