import SwiftUI
import UIKit
import QuartzCore
import PathCore

// GAME G1 (SPEC-architecture §8.1–§8.3, §8.5, §9.3–§9.4, §10; SPEC-motion-audio §3, §12; CONSISTENCY T-4, T-10, W-1, B-11).
// One GameController per Play (a session of 1…n stages). It owns the module's `PuzzleSession`, is the board's delegate, and fans
// every output batch the session returns out in the FIXED order of §8.1, on the main thread, in the same run-loop turn:
//   1 board.present(outputs)   layers + animations, one transaction (the board's own)
//   2 haptics                  the §12.1 map (tap / heartLost / bumpContact; the one-per-frame arbiter is A2's)
//   3 audio                    the cue map (in play only `cues.arrowTap`, unmapped by default: v552 is silent, MA3)
//   4 hud                      HUDWriter (≤ 10 Hz; nothing on a tap frame: `.timerStarted` is written on the next tick)
//   5 fx                       shell overlays (none for in-play events; the celebration starts at W, WinDirector)
//   6 directors                LevelFlow, FailFlowDirector, WinDirector, then G2's (GameDirectors.make); they may call
//                              back into the session, and the events those calls return are fanned out the same way.
// Steps 1–3 run inside the board's release handler before its Core Animation commit, so the ripple (added by the board
// just before it calls `boardReleased`), the mover, the haptic request and the sound's scheduleBuffer share the first
// presented frame (D8). The frame-exact beats (W: the clear wave + the celebration; the stage transition) are handled
// synchronously in `boardBeat`; waits for later moments run on the board's display link (`wait(gameSeconds:)`), never
// on timers.
// Template phase 2 (docs/architecture/PUZZLE-MODULE.md): genre-agnostic. The Play holds the active module's
// `PuzzleSession` and `PuzzleBoard` (services.puzzle / services.board); batches are `[SessionOutput]` — the shell acts on
// `.meta(MetaEvent)` items and hands the whole batch to the board, whose module reads its own `.puzzle` items. Input arrives
// hit-tested (`boardInput`), beats as `PuzzleAck`s (`boardAck`); a "move" (the tap haptic / sound) is any output whose
// puzzle event reports `move`.

/// A director's hooks into a Play (G1's LevelFlow / FailFlowDirector / WinDirector and G2's TutorialDirector,
/// UnlockDirector, BoosterDirector, EventsDirector … through `GameDirectors.make`). Every hook has a no-op default.
@MainActor protocol GameDirector: AnyObject {
    /// The session started and the board is loading (before the intro; the level screen is not visible yet).
    func levelStarted(_ game: GameController)
    /// Step 6 of every fanned-out batch.
    func handle(_ outputs: [SessionOutput], game: GameController)
    /// A board ack, after the controller acked it to the session.
    func ack(_ ack: PuzzleAck, game: GameController)
    /// A booster corner was tapped; true = handled (G2's BoosterDirector).
    func boosterTapped(_ id: BoosterID, game: GameController) -> Bool
    /// After the win panel's Continue / X, before the next screen (G2: the post-level queue).
    func afterWin(_ summary: WinSummary, game: GameController) async
    /// After Level Failed's answer, before the next screen.
    func afterLoss(_ reason: LossReason, game: GameController) async
    /// The Play is going away.
    func teardown(_ game: GameController)
}

extension GameDirector {
    func levelStarted(_ game: GameController) {}
    func handle(_ outputs: [SessionOutput], game: GameController) {}
    func ack(_ ack: PuzzleAck, game: GameController) {}
    func boosterTapped(_ id: BoosterID, game: GameController) -> Bool { false }
    func afterWin(_ summary: WinSummary, game: GameController) async {}
    func afterLoss(_ reason: LossReason, game: GameController) async {}
    func teardown(_ game: GameController) {}
}

/// G2 installs its directors by declaring, in its OWN file (the WP0 entry-point pattern):
///     extension GameDirectors { static func make(_ game: GameController) -> [any GameDirector] { [TutorialDirector(game), …] } }
@MainActor protocol GameDirectorsEntryPoint {
    static func make(_ game: GameController) -> [any GameDirector]
}

extension GameDirectorsEntryPoint {
    static func make(_ game: GameController) -> [any GameDirector] { [] }
}

@MainActor enum GameDirectors: GameDirectorsEntryPoint {}

/// Everything a Play needs: the app's services, or fakes in GameControllerTests.
@MainActor struct GameServices {
    var args: LaunchArgs
    var tuning: Tuning
    /// The meta rules (fail chain, rewards, boosters); the puzzle's own rules are its plugin's.
    var rules: MetaRules
    var economy: EconomyRules
    var clock: MotionClock
    var store: PlayerStore
    var hud: HUDModel
    var board: any PuzzleBoard
    /// The active puzzle module's app half (sessions, capabilities, tutorials, unlock cards).
    var puzzle: any PuzzlePlugin
    var audio: any AudioPlaying
    var haptics: any HapticPlaying
    var popups: any PopupPresenting
    var fx: any FXPlaying
    var router: any Routing
    var latency: LatencyProbe
    var perf: PerfMonitor
    /// The session plan of a launch (sessions.json).
    var plan: @MainActor (LevelLaunch) -> SessionPlan
    /// The events' opponents (the social world).
    var rivals: @MainActor () -> RivalProvider
    /// The screen the board lays out on (pt).
    var screenSize: @MainActor () -> CGSize
    /// Where a won / lost Play goes (SHELL's Router rules, §6.2).
    var screenAfterWin: @MainActor (WinSummary) -> Screen
    var screenAfterLoss: @MainActor (LevelLaunch, _ tryAgain: Bool) -> Screen
    /// A level started (one level ahead: C4's provider + the next session's decode and sprites).
    var levelStarted: @MainActor (Int) -> Void
    /// The app (nil in unit tests): the Shop opener, the autoplayer.
    weak var app: AppModel?

    @MainActor static func of(_ app: AppModel) -> GameServices {
        let router = app.router
        return GameServices(
            args: app.args, tuning: app.tuning, rules: app.rules.meta, economy: app.economy, clock: app.clock, store: app.store,
            hud: app.hud, board: app.puzzleBoard, puzzle: app.puzzle, audio: app.audio, haptics: app.haptics, popups: app.popups,
            fx: app.fx, router: router, latency: app.latency, perf: app.perf,
            plan: { [weak app] l in app?.sessionPlan(for: l) ?? SessionPlan(id: l.session, levels: l.levels) },
            rivals: { [weak app] in app?.rivals ?? SocialWorld(installSeed: 1, config: .default, names: NameBank()) },
            screenSize: { GameServices.keyWindow()?.bounds.size ?? CGSize(width: 393, height: 852) },
            screenAfterWin: { [weak app] summary in
                if let r = router as? Router { return r.screenAfterWin(summary) }
                return GameServices.defaultAfterWin(summary, store: app?.store, app: app)
            },
            screenAfterLoss: { [weak app] launch, again in
                if let r = router as? Router { return r.screenAfterLoss(launch, tryAgain: again) }
                return GameServices.defaultAfterLoss(launch, tryAgain: again, homeSeen: app?.store.state.homeSeen ?? true)
            },
            levelStarted: { [weak app] n in
                app?.provider?.levelStarted(n)
                app?.prefetchLevels(around: n)
            },
            app: app)
    }

    /// The app's key window (the screen the board lays out on).
    static func keyWindow() -> UIWindow? {
        let windows = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.flatMap(\.windows)
        return windows.first(where: \.isKeyWindow) ?? windows.first
    }

    /// §6.2 without SHELL's Router: the FTUE chain's next level while home was never seen, else home.
    static func defaultAfterWin(_ summary: WinSummary, store: PlayerStore?, app: AppModel?, chainUntil: Int = 7) -> Screen {
        guard let s = store?.state else { return .home(.afterWin(summary), tab: .home) }
        if !s.homeSeen {
            if s.level < chainUntil, let app { return .level(app.levelLaunch(for: s.level)) }
            return .home(.firstHome(summary), tab: .home)
        }
        return .home(.afterWin(summary), tab: .home)
    }

    /// §6.2: Try Again = the same board; X = home, except before the first home (CONSISTENCY T-31: a retry).
    static func defaultAfterLoss(_ launch: LevelLaunch, tryAgain: Bool, homeSeen: Bool) -> Screen {
        let retry = LevelLaunch(session: launch.session, levels: launch.levels, isRetry: true, firstStage: launch.firstStage)
        if tryAgain || !homeSeen { return .level(retry) }
        return .home(.afterLoss, tab: .home)
    }
}

@MainActor final class GameController: LevelHosting, PuzzleBoardDelegate {
    /// Where a batch came from (the haptic of step 2 depends on it).
    enum Origin: Equatable { case start, tap, contact, beat, tick, director }

    let launch: LevelLaunch
    let services: GameServices
    let plan: SessionPlan
    /// The session's stages as the module described them (its launch-argument overrides applied).
    private(set) var stages: [PuzzleStage] = []
    private(set) var session: (any PuzzleSession)?
    private(set) var setup: AttemptSetup?
    /// The "Tap to move!" layer's model (S2's TutorialLayer; G2's TutorialDirector drives it).
    let hint = TutorialHint()
    let hudWriter: HUDWriter
    private(set) var flow: LevelFlow!
    private(set) var fail: FailFlowDirector!
    private(set) var win: WinDirector!
    /// G2's directors (and test directors).
    private(set) var extra: [any GameDirector] = []
    private let extraFactory: ((GameController) -> [any GameDirector])?

    private(set) var isTornDown = false
    private(set) var started = false
    /// `introFinished` acked (input may open; MA9: K + 1.015, or + 0.36 on the FTUE's first board).
    private(set) var introDone = false
    /// Game-time of the level screen's cut (K).
    private(set) var cutAt: Double = 0
    var paused = false
    /// The whole Play is settled by a debug jump (`-pc.win`): no board play.
    var synthetic = false
    /// The level's start (wall seconds) and the last result (bench JSON).
    private(set) var startedAtUptime: Double = 0
    /// A2's play() count at the start (SPEC-motion-audio §11.6: a scripted level, its intro and its celebration are silent).
    private var audioPlaysAtStart: Int?

    // audio: the tap cue (resolved once, never on the tap path)
    private let tapSound: (id: SoundID, gain: Float)?

    // frame clock
    private var lastFrameTimestamp: CFTimeInterval = 0
    /// Game seconds of this Play on the display link's scaled deltas (the same time base the session's tick uses; directors
    /// measure short spans with it, e.g. the pre-start hourglass flight, ruling 30).
    private(set) var frameClock: Double = 0
    private var holdingPopup = false
    /// The level timer ran on the last frame (the probe's start/stop edges, FIX-B).
    private var clockWasRunning = false
    private struct TimeWait { let until: Double; let cont: CheckedContinuation<Bool, Never> }
    private var timeWaits: [TimeWait] = []
    private var frameWaits: [(Int, CheckedContinuation<Bool, Never>)] = []

    // same-frame proof (§8.2, §10.2 "Feedback sync")
    private let logTaps: Bool
    private var tapProbe: TapTiming?
    private var commitObserver: CFRunLoopObserver?
    private var hapticObserver: CFRunLoopObserver?
    private(set) var tapTimings: [TapTiming] = []

    /// A test hook: every fan-out step as "<step>" (GameControllerTests; nil in the app).
    var trace: ((String) -> Void)?

    init(_ launch: LevelLaunch, services: GameServices, directors: ((GameController) -> [any GameDirector])? = nil) {
        self.launch = launch
        self.services = services
        plan = services.plan(launch)
        hudWriter = HUDWriter(hud: services.hud, publishHz: services.tuning.game.hudPublishHz)
        extraFactory = directors
        let cues = AudioCueMap(lookup: { services.tuning.audio.file.value($0) })
        tapSound = cues.sound(for: .arrowTap)
        let a = services.args
        logTaps = a.bench || a.showsDebugHUD || a.raw["pc.logTaps"] != nil || a.raw["pc.sameFrame"] != nil
        flow = LevelFlow(self)
        fail = FailFlowDirector(self)
        win = WinDirector(self)
    }

    convenience init(_ launch: LevelLaunch, app: AppModel) {
        self.init(launch, services: .of(app))
    }

    // MARK: convenience accessors

    var board: any PuzzleBoard { services.board }
    /// The active module's fail rules, inputs, boosters, HUD widgets.
    var capabilities: PuzzleCapabilities { services.puzzle.capabilities }
    var store: PlayerStore { services.store }
    var clock: MotionClock { services.clock }
    var args: LaunchArgs { services.args }
    var popups: any PopupPresenting { services.popups }
    var haptics: any HapticPlaying { services.haptics }
    var directors: [any GameDirector] {
        var d: [any GameDirector] = [flow!, fail!, win!]
        d += extra
        return d
    }
    /// The level the logs name: the session's first level ("L1" for "Levels 1-4").
    var levelName: String { "L\(plan.levels.first ?? launch.levels.first ?? 0)" }
    /// The stage on the board now.
    var currentStage: PuzzleStage? {
        guard let s = session, stages.indices.contains(s.stage) else { return nil }
        return stages[s.stage]
    }

    // MARK: LevelHosting

    func start() -> Bool {
        guard !started else { return true }
        started = true
        startedAtUptime = ProcessInfo.processInfo.systemUptime
        guard flow.start() else {
            isTornDown = true
            return false
        }
        services.app?.game = self
        services.app?.autoplayer?.noteStart(plan.levels)
        audioPlaysAtStart = (services.audio as? AudioEngine)?.status.plays
        extra = (extraFactory ?? { GameDirectors.make($0) })(self)
        for d in extra { d.levelStarted(self) }
        if !synthetic { win.warmEventHooks() }                                  // FIX-2 A (V3-02): off-main, a copy
        return true
    }

    func makeView() -> AnyView { AnyView(GameScreen(game: self)) }

    func teardown() {
        guard !isTornDown else { return }
        let plays = ((services.audio as? AudioEngine)?.status.plays ?? 0) - (audioPlaysAtStart ?? 0)
        Log.mark("game", "teardown \(levelName)" + (audioPlaysAtStart == nil ? "" : " (audio play() calls during the Play: \(plays))"))
        // A Play left without a finished attempt (never through the normal flows): a quit, so the next Play can start.
        if session?.isFinished == false, store.state.activeAttempt != nil, !synthetic {
            Log.error("game", "\(levelName) torn down mid-play: the attempt is finished as a quit")
            fail.bankLoss(.quit)
        }
        isTornDown = true
        for d in directors { d.teardown(self) }
        if board.delegate === self { board.delegate = nil }
        board.inputEnabled = false
        board.allowedTargets = nil
        services.fx.stopAll()
        hint.clear()
        hudWriter.end()
        for w in timeWaits { w.cont.resume(returning: false) }
        timeWaits = []
        for w in frameWaits { w.1.resume(returning: false) }
        frameWaits = []
        removeObservers()
        if services.app?.game === self { services.app?.game = nil }
    }

    // MARK: the session (LevelFlow builds it)

    func install(session s: any PuzzleSession, stages: [PuzzleStage], setup: AttemptSetup) {
        session = s
        self.stages = stages
        self.setup = setup
    }

    func markCut() { cutAt = clock.gameTime() }

    // MARK: fan-out (§8.1)

    /// Forwards one batch to every presenter in the fixed order.
    func fanOut(_ outputs: [SessionOutput], origin: Origin) {
        guard !outputs.isEmpty, !isTornDown else { return }
        trace?("board")
        board.present(outputs)                                                 // 1
        playHaptics(outputs, origin: origin)                                   // 2
        playAudio(outputs, origin: origin)                                     // 3
        trace?("hud")
        if let s = session { hudWriter.apply(outputs, session: s, onTapFrame: origin == .tap) }   // 4
        trace?("fx")                                                           // 5: nothing in play (celebration at W)
        trace?("directors")
        for d in directors { d.handle(outputs, game: self) }                   // 6
    }

    /// A batch holds a resolved player move (an exit, a bump, a swap …): the tap haptic and the tap cue.
    private static func hasMove(_ outputs: [SessionOutput]) -> Bool { outputs.contains { $0.move != nil } }

    private func playHaptics(_ outputs: [SessionOutput], origin: Origin) {
        switch origin {
        case .tap:
            if Self.hasMove(outputs) {
                trace?("haptic.tap")
                haptics.play(.tap)
            }
        case .contact:
            let lost = outputs.contains { if case .meta(.heartsChanged(left: _)) = $0 { return true }; return false }
            trace?(lost ? "haptic.heartLost" : "haptic.bumpContact")
            haptics.play(lost ? .heartLost : .bumpContact)
        default:
            break
        }
    }

    private func playAudio(_ outputs: [SessionOutput], origin: Origin) {
        guard origin == .tap, let s = tapSound else { return }
        if Self.hasMove(outputs) {
            trace?("audio.\(s.id.rawValue)")
            services.audio.play(s.id, gain: s.gain)
        }
    }

    // MARK: PuzzleBoardDelegate

    var activeSession: (any PuzzleSession)? { session }

    /// The board's release handler, synchronously (§8.2): the session resolves the input and the board presents the result in
    /// this same run-loop turn, before the board's Core Animation commit.
    func boardInput(_ input: PuzzleInput, touchTimestamp: TimeInterval) {
        guard let session, !isTornDown else { return }
        let t0 = CACurrentMediaTime()
        let outputs = session.input(input, at: clock.gameTime())
        let tCore = CACurrentMediaTime()
        if !Self.hasMove(outputs) {
            fanOut(outputs, origin: .tap)
            return
        }
        // 1–3 with timestamps (the same-frame proof). FEEL item 4: the board adds the release's ripple at the END of its
        // present, right after the movers, so ripple, mover, haptic and sound are issued back to back (the ripple used to go in
        // before the session and the mover build, 0.2–6 ms earlier)
        trace?("board")
        board.present(outputs)
        let t1 = CACurrentMediaTime()
        playHaptics(outputs, origin: .tap)
        let t2 = CACurrentMediaTime()
        playAudio(outputs, origin: .tap)
        let t3 = CACurrentMediaTime()
        trace?("hud")
        hudWriter.apply(outputs, session: session, onTapFrame: true)
        trace?("fx")
        trace?("directors")
        for d in directors { d.handle(outputs, game: self) }
        if logTaps {
            let diag = board.diagnostics
            let ripple = diag.map { $0.lastRippleAt >= t0 ? $0.lastRippleAt : t0 } ?? t0
            beginTapTiming(target: input.target, entry: t0, core: tCore, mover: t1, ripple: ripple, haptic: t2, sound: t3,
                           touch: touchTimestamp, build: diag.map { ($0.lastPresentMs, $0.presentNotes.joined(separator: ",")) })
        }
        services.app?.autoplayer?.noteTap(outputs)
    }

    func boardAck(_ ack: PuzzleAck) {
        guard let session, !isTornDown else { return }
        switch ack {
        case .introFinished:
            introDone = true
            fanOut(session.ack(ack), origin: .beat)
            updateInput()
        case .contact:
            let outputs = session.ack(ack)
            if outputs.isEmpty {
                // a contact that costs nothing and changes nothing (Arrow Out: a red arrow's re-bump): only its contact haptic
                // (MA §12.1 bumpContact)
                trace?("haptic.bumpContact")
                haptics.play(.bumpContact)
            } else {
                fanOut(outputs, origin: .contact)
            }
        case .beat:
            fanOut(session.ack(ack), origin: .beat)
        case .boardCleared:
            fanOut(session.ack(ack), origin: .beat)
            // W: every stage's clear (MA §12.1 `clear`), then the stage transition or the celebration on THIS frame
            haptics.play(.clear)
            switch session.phase {
            case .stageClear(let k): flow.stageLeftBoard(k)
            case .won: win.atW()
            default: break
            }
        case .stageTransitionDone:
            fanOut(session.ack(ack), origin: .beat)
            updateInput()
        }
        for d in directors { d.ack(ack, game: self) }
    }

    /// A purely visual beat's haptic (a burst frame).
    func boardFeedback(_ haptic: Haptic) {
        guard session != nil, !isTornDown else { return }
        haptics.play(haptic)
    }

    func boardFrame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval) {
        guard let session, !isTornDown else { return }
        let real = lastFrameTimestamp > 0 ? timestamp - lastFrameTimestamp : 0
        lastFrameTimestamp = timestamp
        if real > 0 { frameClock += clock.scaled(real) }
        finishTapTiming(targetTimestamp: targetTimestamp)
        // holds that follow the shell: any popup up in a level holds the timer (§6.6 `holdsLevelTimer`)
        let presenting = popups.isPresenting
        if presenting != holdingPopup {
            holdingPopup = presenting
            if presenting { session.hold(.popup) } else { session.release(.popup) }
        }
        updateInput()
        if real > 0, !args.freezeTimer, !args.holdsTimerForCapture {
            let events = session.tick(clock.scaled(real))
            if !events.isEmpty { fanOut(events, origin: .tick) }
        }
        // FIX-B (V1 GameFlowTests.testUnlockOverlayHoldsTheTimer): the §9.4 probe refreshes at <= 4 Hz, so a `t` read just
        // after a popup appeared could be up to 250 ms older than the hold (V1 run 4: 174.861 -> 174.728 under the overlay,
        // the hold itself on the first frame of the popup). On the frame the timer starts or stops it publishes at once.
        let running = session.clock.isRunning
        if running != clockWasRunning {
            clockWasRunning = running
            if args.exposesProbe { board.publishProbe() }
        }
        let now = clock.gameTime()
        hudWriter.tick(session: session, now: timestamp, gameTime: now)
        flow.frame(gameTime: now)
        if !timeWaits.isEmpty {
            let due = timeWaits.filter { $0.until <= now }
            timeWaits.removeAll { $0.until <= now }
            for w in due { w.cont.resume(returning: true) }
        }
        if !frameWaits.isEmpty {
            var keep: [(Int, CheckedContinuation<Bool, Never>)] = []
            for (n, c) in frameWaits { if n <= 1 { c.resume(returning: true) } else { keep.append((n - 1, c)) } }
            frameWaits = keep
        }
    }

    func boardZoomChanged(scale: CGFloat) {}

    /// Opens board input exactly while a live stage is on screen with nothing over it (T-10: from `introFinished`).
    func updateInput() {
        guard let session, !isTornDown else { return }
        let live: Bool
        switch session.phase { case .ready, .playing: live = true; default: live = false }
        let want = live && introDone && !popups.isPresenting && !paused && !synthetic
        if board.inputEnabled != want { board.inputEnabled = want }
    }

    // MARK: waits (display-link driven; false = the Play went away)

    /// Resumes on the first display-link frame at or after `s` seconds of GAME time (slow motion and freezes apply).
    func wait(gameSeconds s: Double) async -> Bool {
        guard !isTornDown else { return false }
        let until = clock.gameTime() + max(0, s)
        return await withCheckedContinuation { c in timeWaits.append(TimeWait(until: until, cont: c)) }
    }

    /// Resumes after `n` display-link frames.
    func wait(frames n: Int) async -> Bool {
        guard !isTornDown else { return false }
        return await withCheckedContinuation { c in frameWaits.append((max(1, n), c)) }
    }

    // MARK: HUD buttons

    func boosterTapped(_ id: BoosterID) {
        guard !isTornDown else { return }
        for d in extra where d.boosterTapped(id, game: self) { return }
        Log.mark("game", "booster \(id.rawValue): G2's BoosterDirector is not installed (no effect)")
    }

    // MARK: lifecycle (§8.6)

    func appDidEnterBackground() {
        guard let session, !isTornDown else { return }
        session.hold(.background)
        Log.mark("game", "\(levelName) background: timer held")
    }

    func appDidBecomeActive() {
        guard let session, !isTornDown else { return }
        session.release(.background)
        flow.returnedFromBackground()
    }

    // The probe's session half (§9.4) is the module board's (it reads `activeSession`): Arrow Out's is ArrowPuzzleBoard's.

    // MARK: the same-frame proof (§8.2; logged under -pc.bench / -pc.hud debug / -pc.logTaps / -pc.sameFrame)

    struct TapTiming {
        var level: Int
        var target: Int
        var touch: CFTimeInterval
        var entry: CFTimeInterval            // boardReleased entry (the board's hit test is done)
        var core: CFTimeInterval             // session.tap returned (C2: resolve + commit); board.present starts here
        var mover: CFTimeInterval            // board.present returned (mover layers + animations in the transaction)
        var ripple: CFTimeInterval           // the release ripple added (FEEL: at the end of the present, after the movers)
        var build: (ms: Double, notes: String)?   // the board's present: main-thread ms and what it built
        var haptic: CFTimeInterval           // haptics.play(.tap) returned (the arbiter's request)
        var sound: CFTimeInterval            // the tap cue scheduled (or its silent decision)
        var hapticFired: CFTimeInterval?     // the arbiter flushed it (run-loop order 1 999 000, before CA's 2 000 000)
        var commit: CFTimeInterval?          // after Core Animation's commit (order 2 000 002)
        var vsync: CFTimeInterval?           // the first display-link target after the commit
        var firedCount: Int                  // Haptics.fired[.tap] before the tap
        var hapticConfirmed = false
    }

    private func beginTapTiming(target: PuzzleTarget?, entry: CFTimeInterval, core: CFTimeInterval, mover: CFTimeInterval,
                                ripple: CFTimeInterval, haptic: CFTimeInterval, sound: CFTimeInterval, touch: TimeInterval,
                                build: (Double, String)?) {
        installObservers()
        let fired = (haptics as? Haptics)?.fired[.tap] ?? 0
        tapProbe = TapTiming(level: currentStage?.level ?? 0, target: target?.raw ?? -1, touch: touch, entry: entry,
                             core: core, mover: mover, ripple: ripple, build: build.map { (ms: $0.0, notes: $0.1) }, haptic: haptic, sound: sound, firedCount: fired)
    }

    private func installObservers() {
        guard commitObserver == nil else { return }
        // after A2's haptic flush (1 999 000), before Core Animation's commit (2 000 000)
        let h = CFRunLoopObserverCreateWithHandler(kCFAllocatorDefault, CFRunLoopActivity.beforeWaiting.rawValue | CFRunLoopActivity.exit.rawValue,
                                                   true, 1_999_500) { [weak self] _, _ in
            MainActor.assumeIsolated {
                guard let self, var p = self.tapProbe, p.hapticFired == nil else { return }
                p.hapticFired = CACurrentMediaTime()
                let now = (self.haptics as? Haptics)?.fired[.tap] ?? p.firedCount
                p.hapticConfirmed = now > p.firedCount || !(self.haptics is Haptics)
                self.tapProbe = p
            }
        }
        let c = CFRunLoopObserverCreateWithHandler(kCFAllocatorDefault, CFRunLoopActivity.beforeWaiting.rawValue | CFRunLoopActivity.exit.rawValue,
                                                   true, 2_000_002) { [weak self] _, _ in
            MainActor.assumeIsolated {
                guard let self, var p = self.tapProbe, p.commit == nil else { return }
                p.commit = CACurrentMediaTime()
                self.tapProbe = p
            }
        }
        CFRunLoopAddObserver(CFRunLoopGetMain(), h, .commonModes)
        CFRunLoopAddObserver(CFRunLoopGetMain(), c, .commonModes)
        hapticObserver = h
        commitObserver = c
    }

    private func removeObservers() {
        for o in [hapticObserver, commitObserver].compactMap({ $0 }) { CFRunLoopRemoveObserver(CFRunLoopGetMain(), o, .commonModes) }
        hapticObserver = nil
        commitObserver = nil
    }

    private func finishTapTiming(targetTimestamp: CFTimeInterval) {
        guard var p = tapProbe, let commit = p.commit else { return }
        p.vsync = targetTimestamp
        tapProbe = nil
        tapTimings.append(p)
        if tapTimings.count > 400 { tapTimings.removeFirst() }
        func ms(_ a: CFTimeInterval, _ b: CFTimeInterval?) -> String { b.map { String(format: "%.3f", ($0 - a) * 1000) } ?? "-" }
        // the four feedback calls: the ripple (added after the movers), the mover (present returned), haptic, sound
        let calls = [p.ripple, p.mover, p.haptic, p.sound]
        let spread = (calls.max() ?? 0) - (calls.min() ?? 0)
        let onTime = p.sound <= commit && (p.hapticFired ?? .infinity) <= commit
        let build = p.build.map { String(format: " · build %.3f ms [%@]", $0.ms, $0.notes) } ?? ""
        // G1's field order (build/g1/sameframe_stats.py parses it); FEEL adds `ripple` before `mover` and the build detail last
        let line = "L\(p.level) a\(p.target) core \(ms(p.entry, p.core)) ripple \(ms(p.entry, p.ripple)) mover \(ms(p.entry, p.mover)) "
            + "haptic \(ms(p.entry, p.haptic)) "
            + "sound \(ms(p.entry, p.sound))\(tapSound == nil ? " (unmapped: silent)" : " (\(tapSound!.id.rawValue))") "
            + "hapticFired \(ms(p.entry, p.hapticFired))\(p.hapticConfirmed ? "" : " (not fired)") commit \(ms(p.entry, commit)) "
            + "vsync +\(String(format: "%.2f", (targetTimestamp - commit) * 1000)) ms · touch→entry \(ms(p.touch, p.entry)) · "
            + String(format: "spread %.3f ms %@", spread * 1000, onTime && spread <= 0.001 ? "OK" : "LATE") + build
        Log.mark("sameframe", line)
        if args.raw["pc.sameFrame"] != nil { SameFrameFile.append(line) }
    }

    // MARK: bench (-pc.bench 1: Documents/bench-L<n>-<ts>.json at each level end)

    func writeBench(outcome: String, result: WinResult? = nil) {
        guard args.bench else { return }
        let snap = services.perf.snapshot()
        let lat = services.latency
        var obj: [String: Any] = [
            "level": plan.levels.first ?? 0, "levels": plan.levels, "outcome": outcome,
            "seconds": ProcessInfo.processInfo.systemUptime - startedAtUptime,
            "frames": snap.frames, "fps": snap.fps, "p50_ms": snap.p50_ms, "p95_ms": snap.p95_ms, "p99_ms": snap.p99_ms,
            "max_ms": snap.max_ms, "over20": snap.over20, "footprint_mb": snap.footprint_mb,
            "footprint_peak_mb": snap.footprint_peak_mb, "thermal_state": snap.thermal,
            "touch_to_handler_ms_p99": lat.percentile(0.99) { $0.touchToHandlerMs },
            "handler_to_commit_ms_p99": lat.percentile(0.99) { $0.handlerToCommitMs },
            "commit_to_vsync_ms_p50": lat.percentile(0.5) { $0.commitToVsyncMs },
            "taps": tapTimings.count,
        ]
        if let d = board.diagnostics {
            obj["hitches_load"] = d.hitchesLoad
            obj["hitches_play"] = d.hitchesPlay
        }
        if let r = result { obj["timeLeft"] = r.timeLeft; obj["heartsLeft"] = r.heartsLeft; obj["bumps"] = r.bumps }
        let name = "bench-L\(plan.levels.first ?? 0)-\(Int(Date().timeIntervalSince1970)).json"
        guard let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first,
              let data = try? JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys, .prettyPrinted]) else { return }
        DispatchQueue.global(qos: .utility).async { try? data.write(to: docs.appendingPathComponent(name), options: .atomic) }
        Log.mark("game", "bench \(name)")
    }
}

/// `-pc.sameFrame 1`: every tap's timing line also goes to Documents/sameframe.txt (UI tests read it off the simulator).
@MainActor enum SameFrameFile {
    private static var lines: [String] = []
    static func append(_ line: String) {
        lines.append(String(format: "%.3f ", ProcessInfo.processInfo.systemUptime) + line)
        let text = lines.joined(separator: "\n") + "\n"
        guard let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else { return }
        DispatchQueue.global(qos: .utility).async {
            try? Data(text.utf8).write(to: docs.appendingPathComponent("sameframe.txt"), options: .atomic)
        }
    }
}

// MARK: - GAME's entry point (the WP0 pattern: SHELL's router hosts a Play through `GameEntry.makeLevel`)

extension GameEntry {
    static func makeLevel(_ launch: LevelLaunch, app: AppModel) -> any LevelHosting { GameController(launch, app: app) }
}

extension Phase {
    /// The phase's name in logs and the probe ("intro", "ready", "playing", "stageClear", "offer", "won", "lost").
    var logName: String {
        switch self {
        case .intro: return "intro"
        case .ready: return "ready"
        case .playing: return "playing"
        case .stageClear: return "stageClear"
        case .offer: return "offer"
        case .won: return "won"
        case .lost: return "lost"
        }
    }
}
