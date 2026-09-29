import SwiftUI
import PathCore

// GAME G1 (SPEC-architecture §8.4 WinDirector, §4.5 "win at the tap"; SPEC-gameplay §9.1–§9.3, §10.3; SPEC-motion-audio §5,
// §3.8, §15.3; CONSISTENCY W-1, W-2, W-11, X-16). The win:
//  - at the TAP of the last arrow (`.won`): input locks and the win is BANKED at once — `Economy.finishAttempt(.won)` (the
//    life back, the reward to coins AND to the pending home coin fly, the stats, `level` past the session) + the event hooks
//    (`Events.onWin`: multiplier, Claw, races, the social ledger) + an immediate save — so a kill during the celebration
//    is still a win at the next launch;
//  - at W (the board's `lastExitLeftBoard`, on that frame): the clear wave (the board) and the celebration clock
//    (`fx.play(.celebration)`, S2), concurrently — `clearWaveFinished` is not a gate (W-1). The win haptic is the
//    celebration's (the OUT! slam or the skip-tap), never fired here;
//  - `fx.finished` returns at W + 3.94 (`ui.json win.panelAt`) or at the skip-tap → the win panel (S2) → Continue or X (X =
//    Continue, W-11) → the post-level hooks (G2) → the next screen (SHELL's §6.2 rule: the FTUE chain's next level while
//    home was never seen, the first home after L6 with its +120, else home with the payout).

@MainActor final class WinDirector: GameDirector {
    unowned let game: GameController
    private(set) var result: WinResult?
    private(set) var outcomes: [EventOutcome] = []
    private(set) var celebration: FXHandle?
    private var atWDone = false
    private var wContinuation: CheckedContinuation<Bool, Never>?
    private var wReached = false
    /// FIX-2 A: the panel was presented (its hidden warm-up is then moot).
    private var panelUp = false
    /// FIX-2 A (V3-01): the headless clear + bank ran once in this process.
    private static var clearWarmed = false

    init(_ game: GameController) { self.game = game }

    private var services: GameServices { game.services }

    func handle(_ events: [SessionEvent], game: GameController) {
        for case .won(let r) in events { won(r, synthetic: false) }
    }

    func teardown(_ game: GameController) {
        wContinuation?.resume(returning: false)
        wContinuation = nil
    }

    // MARK: at the tap

    private func won(_ r: WinResult, synthetic: Bool) {
        guard result == nil else { return }
        result = r
        services.board.inputEnabled = false
        bank(r)
        // the task holds its Play until it ends (teardown resumes every wait, so it ends promptly)
        Task { @MainActor [self, game] in
            await present(r, synthetic: synthetic)
            withExtendedLifetime(game) {}
        }
    }

    /// C3's bookkeeping + the event hooks, one mutation, an immediate save (kill-safe, §8.4).
    private func bank(_ r: WinResult) {
        let s = services
        let now = s.clock.wallClock()
        let rivals = s.rivals()
        let before = s.store.state
        outcomes = s.store.mutateAndSave { st -> [EventOutcome] in
            Economy.finishAttempt(&st, outcome: .won(r), now: now, rules: s.economy)
            return Events.onWin(&st, WinContext(levels: r.levels, tag: r.tag, firstTry: r.firstTry, now: now), rivals: rivals,
                                rules: s.economy)
        }
        let st = s.store.state
        Log.mark("win", "\(game.levelName) won: \(r.timeLeft) s left, \(r.heartsLeft) hearts")
        Log.mark("win", "\(game.levelName) banked: +\(r.reward) coins \(before.coins) → \(st.coins), pending fly \(st.pendingCoinFly), "
                 + "next level \(st.level), lives \(st.lives.count), first try \(r.firstTry), bumps \(r.bumps)"
                 + (outcomes.isEmpty ? "" : ", events " + outcomes.map(EventsDirector.describe).joined(separator: "; ")))
        // FIX-2 A (V3-02): the outcomes are described by EventsDirector's switch, not "\($0)": Swift's reflection-based
        // description cost the FIRST event-counted win of a process ~14 ms between `won` and `banked` (build/p/FIX2/A/perf/v8-ev3)
        services.app?.autoplayer?.noteWin(r)
        game.writeBench(outcome: "won", result: r)
    }

    /// FIX-2 A (V3-02): the FIRST event-counted win of a process spent 9-23 ms in `Events.onWin` (the world's race / contest
    /// tables of this week built on first use) inside the clearing tap's frame; later wins took 0-1 ms. At level start the
    /// same hook runs once OFF the main thread on a COPY of the state (its result dropped; the world is immutable and safe to
    /// query from any thread, its caches lock): the real bank at the tap then finds them warm. Nothing is written.
    func warmEventHooks() {
        let s = services
        let state = s.store.state
        // V3-01: the level-clearing tap's FIRST run in a process paid Swift's one-time metadata instantiation in
        // `LevelSession.cleared` (a generic dictionary literal: 4 of the tap's 7 ms, build/p/FIX2/A/tp/v2-tp1) and in the bank
        // (`Economy.finishAttempt`). Once per process a headless 2-arrow session is cleared and banked on a copy, off the main
        // thread (nothing shown, nothing written).
        if !Self.clearWarmed {
            Self.clearWarmed = true
            let rules = s.rules, economy = s.economy, now = s.clock.wallClock()
            Task.detached(priority: .utility) {
                let a1 = ArrowSpec(id: ArrowID(1), cells: [Cell(0, 1), Cell(1, 1)], dir: .right)
                let a2 = ArrowSpec(id: ArrowID(2), cells: [Cell(3, 2), Cell(3, 1)], dir: .up)
                let level = LevelSpec(level: 9_990, source: .designed, cols: 4, rows: 4, timerSeconds: 180, hearts: 3, tag: .normal,
                                      arrows: [a1, a2])
                let session = LevelSession(plan: SessionPlan(id: "warm-clear", levels: [level.level]), stages: [level],
                                           setup: AttemptSetup(levels: [level.level]), rules: rules)
                _ = session.start()
                _ = session.ack(.introFinished)
                _ = session.tap(ArrowID(2), at: 0.1)
                for case .won(let r) in session.tap(ArrowID(1), at: 0.2) {
                    var copy = state
                    _ = Economy.finishAttempt(&copy, outcome: .won(r), now: now, rules: economy)
                }
            }
        }
        guard state.homeSeen else { return }                        // the FTUE chain counts no event
        let rivals = s.rivals()
        let rules = s.economy
        let ctx = WinContext(levels: game.plan.levels, tag: .normal, firstTry: true, now: s.clock.wallClock())
        let name = game.levelName
        let t0 = ProcessInfo.processInfo.systemUptime
        Task.detached(priority: .utility) {
            var copy = state
            let outcomes = Events.onWin(&copy, ctx, rivals: rivals, rules: rules)
            let ms = (ProcessInfo.processInfo.systemUptime - t0) * 1000
            await MainActor.run {
                Log.mark("win", String(format: "%@ event hooks warmed off-main in %.1f ms (%d outcomes on a copy)", name, ms, outcomes.count))
            }
        }
    }

    // MARK: at W (the board's lastExitLeftBoard, called synchronously on its frame)

    func atW() {
        guard result != nil, !atWDone, !game.isTornDown else { return }
        atWDone = true
        services.board.playClearWave()
        celebration = services.fx.play(.celebration(result?.tag ?? .normal))
        Log.mark("win", "\(game.levelName) W: clear wave + celebration")
        wReached = true
        wContinuation?.resume(returning: true)
        wContinuation = nil
    }

    private func waitForW() async -> Bool {
        if wReached { return true }
        if game.isTornDown { return false }
        return await withCheckedContinuation { c in wContinuation = c }
    }

    // MARK: the presentation

    private func present(_ r: WinResult, synthetic: Bool) async {
        if synthetic {
            celebration = services.fx.play(.celebration(r.tag))
            wReached = true
        } else {
            guard await waitForW() else { return }
        }
        let summary = WinSummary(levels: r.levels, reward: r.reward, tag: r.tag, outcomes: outcomes)
        // FIX-2 A (V3-14): the panel drawn once, hidden, at W + `win.panelWarmAt` (after the logo has landed), so its first frame
        // composites cached rasters (Shell/RootView.swift PopupWarm)
        if !synthetic, services.app != nil {
            let at = services.tuning.ui.file.double("win.panelWarmAt", 2.6)
            Task { @MainActor [weak self] in
                try? await Task.sleep(nanoseconds: UInt64(max(0, at) * 1_000_000_000))
                guard let self, !self.game.isTornDown, !self.panelUp else { return }
                let p = Popup<PopupResult>.winPanel(summary)
                PopupWarm.shared.warm(p.request, style: p.style)
            }
        }
        if let h = celebration { await services.fx.finished(h) }
        guard !game.isTornDown else { return }
        panelUp = true
        PopupWarm.shared.cancel()
        let answer = await services.popups.present(Popup<PopupResult>.winPanel(summary))
        guard !game.isTornDown else { return }
        Log.mark("win", "\(game.levelName) panel → \(answer == .close ? "X" : "Continue")")
        for d in game.directors { await d.afterWin(summary, game: game) }
        guard !game.isTornDown else { return }
        let next = services.screenAfterWin(summary)
        if case .home(.firstHome, _) = next {
            Log.mark("game", "first home: pending coin fly \(services.store.state.pendingCoinFly), coins \(services.store.state.coins)")
        }
        services.router.go(next)
    }

    // MARK: -pc.win <tag>

    /// A synthetic win for captures and flow tests: the session's current values, the given tier's reward.
    func startSynthetic(tag: LevelTag) {
        guard let s = game.session, let setup = game.setup else { return }
        game.synthetic = true
        game.updateInput()
        let reward = game.plan.levels.count > 1 ? (game.plan.reward ?? services.rules.rewards.reward(for: tag))
            : services.rules.rewards.reward(for: tag)
        let r = WinResult(levels: game.plan.levels, tag: tag, timeLeft: s.clock.displayedSeconds, heartsLeft: s.hearts,
                          firstTry: setup.attemptIndex <= 1, reward: reward, bumps: 0)
        won(r, synthetic: true)
    }
}
