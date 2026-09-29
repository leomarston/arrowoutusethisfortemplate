import SwiftUI
import QuartzCore
import PathCore

// GAME G1 (SPEC-architecture §8.4 AutoPlayer, §9.1, §10.4 full-game soak). `-pc.autoplay 1`: a bot that plays through the
// REAL app — the real board's release handler (hit test, ripple, the session, the movers: `BoardEngine.handleRelease` at the
// arrow's `tapPoint`), the real popups (answered through the popup host like a finger would), the real router (home's Play
// action). Every `autoplayRate` s (game.json `autoplay.rate` 0.45, `-pc.autoplayRate`) it taps the first unit of
// `session.hint()` (C2's solver order); with `-pc.autoplayMistakes p` it taps a blocked arrow instead with probability p
// (the "autoplay" stream of the install seed). It dismisses tutorials / unlocks / panels, presses Play on home, and stops
// after the win that takes the player past `-pc.autoplayStop N`:
//   [PC][autoplay] done: L<a>-L<b> won <w>/<n> bumps <b>
// Test driver only: it never runs without the launch argument.

@MainActor final class AutoPlayer {
    let rate: Double
    let stopLevel: Int?
    let mistakes: Double
    /// Popups are answered after they have been up this long (s); the unlock overlay accepts taps from S + 0.94.
    let popupDelay: Double
    let unlockDelay: Double
    /// Home: Play is pressed after this long (the payout plays first).
    let homeDelay: Double

    private weak var app: AppModel?
    private var rng: PathRandom
    private var task: Task<Void, Never>?
    private(set) var attempts = 0
    private(set) var wins = 0
    private(set) var bumps = 0
    private(set) var taps = 0
    private var levelTaps = 0
    private var levelBumps = 0
    private var firstLevel: Int?
    private var lastWon: Int?
    private(set) var done = false
    private var stopScreen: String?
    private var lastTap: Double = 0
    private var popupSeen: (id: Int, at: Double)?
    private var homeSince: Double?
    private var levelSince: Double?

    init(args: LaunchArgs, tuning: Tuning) {
        rate = max(0.05, args.autoplayRate ?? tuning.game.autoplayRate)
        stopLevel = args.autoplayStop
        mistakes = min(max(args.autoplayMistakes ?? 0, 0), 1)
        popupDelay = tuning.game.file.double("autoplay.popupDelay", 0.6)
        unlockDelay = tuning.game.file.double("autoplay.unlockDelay", 1.2)
        homeDelay = tuning.game.file.double("autoplay.homeDelay", 2.0)
        rng = PathRandom(seed: args.effectiveSeed ?? 1).fork("autoplay")
        Log.mark("autoplay", "on: rate \(rate) s, stop \(stopLevel.map(String.init) ?? "none"), mistakes \(mistakes)")
    }

    func start(_ app: AppModel) {
        self.app = app
        guard task == nil else { return }
        task = Task { @MainActor [weak self] in
            while let self, !Task.isCancelled {
                self.step()
                try? await Task.sleep(nanoseconds: 50_000_000)
            }
        }
    }

    func stop() {
        task?.cancel()
        task = nil
    }

    // MARK: notes from the game

    func noteStart(_ levels: [Int]) {
        attempts += 1
        if firstLevel == nil { firstLevel = levels.first }
        levelTaps = 0
        levelBumps = 0
    }

    func noteTap(_ events: [SessionEvent]) {
        for e in events { if case .bumped = e { bumps += 1; levelBumps += 1 } }
    }

    func noteWin(_ r: WinResult) {
        wins += 1
        lastWon = r.levels.max()
        Log.mark("autoplay", "L\(r.levels.first ?? 0)\(r.levels.count > 1 ? "-\(r.levels.last ?? 0)" : "") won "
                 + "(\(levelTaps) taps, \(levelBumps) bumps, \(r.timeLeft) s left)")
        if let stop = stopLevel, let last = r.levels.max(), last >= stop, !done {
            done = true
            Log.mark("autoplay", "done: L\(firstLevel ?? 1)-L\(last) won \(wins)/\(attempts) bumps \(bumps)")
        }
    }

    // MARK: the loop

    private func step() {
        guard let app else { return }
        let now = ProcessInfo.processInfo.systemUptime
        if let host = app.popups as? PopupHost, let top = host.stack.last {
            homeSince = nil
            if popupSeen?.id != top.id { popupSeen = (top.id, now); return }
            let wait = top.request.id == .unlockOverlay ? unlockDelay : popupDelay
            guard let seen = popupSeen, now - seen.at >= wait else { return }
            let answer = Self.answer(for: top.request)
            Log.mark("autoplay", "popup \(top.request.id.rawValue) → \(answer)")
            host.answer(top.id, answer)
            popupSeen = nil
            return
        }
        popupSeen = nil
        let screen = app.router.screen
        if done {
            // the win panel's Continue has been answered: stop on the next screen
            if stopScreen == nil { stopScreen = screen.logName }
            var onHome = false
            if case .home = screen { onHome = true }
            if onHome || screen.logName != stopScreen {
                Log.mark("autoplay", "stopped on \(screen.logName)")
                stop()
            }
            return
        }
        switch screen {
        case .level:
            homeSince = nil
            guard let game = app.game, let s = game.session, !game.isTornDown else { return }
            if levelSince == nil { levelSince = now }
            guard app.board.inputEnabled else { return }
            switch s.phase { case .ready, .playing: break; default: return }
            guard now - lastTap >= rate else { return }
            guard let a = pick(s, board: app.board) else { return }
            lastTap = now
            taps += 1
            levelTaps += 1
            game.flow.tap(a)
        case .home:
            levelSince = nil
            // G2: home's queue (the payout, claims, offers, the rating prompt) plays out first, like a player waiting for it
            if HomeQueue.shared.busy || PayoutSequence.running { homeSince = now; return }
            if homeSince == nil { homeSince = now }
            guard let since = homeSince, now - since >= homeDelay else { return }
            homeSince = nil
            let level = app.store.state.level
            Log.mark("autoplay", "home → Play L\(level)")
            app.router.go(.level(app.levelLaunch(for: level)))
        case .event(let e):
            // FIX-2 A (V3-03): home's queue put an event PAGE up (the Claw first-open page at L151, a week-start ladder page):
            // after the same wait a player gives home, its X — the page's own close (back home, the pile refills) — so the
            // run goes on (V3's L151 run sat on the Claw intro until its timeout)
            levelSince = nil
            if homeSince == nil { homeSince = now }
            guard let since = homeSince, now - since >= homeDelay else { return }
            homeSince = nil
            Log.mark("autoplay", "event page \(e.rawValue) → X")
            EventPageShell<EmptyView>.close(app)
        default:
            break
        }
    }

    /// The next arrow: the first unit of the solver's order, or (with probability `mistakes`) a blocked, not-yet-red arrow.
    private func pick(_ s: LevelSession, board: any BoardControlling) -> ArrowID? {
        if mistakes > 0, rng.unit() < mistakes {
            let snap = s.snapshot()
            let free = Set(snap.free.flatMap { $0 })
            let red = Set(board.probe().arrows.filter(\.red).map { ArrowID($0.id) })
            let blocked = snap.live.filter { !free.contains($0) && !red.contains($0) }
            if !blocked.isEmpty { return blocked[rng.below(blocked.count)] }
        }
        return s.hint()?.first
    }

    /// What a player would press: Continue / Try Again / Claim / Resume; X on offers, unlock cards, quit confirmations.
    static func answer(for request: PopupRequest) -> Any {
        switch request {
        case .winPanel, .levelFailed, .claimReward, .pause: return PopupResult.primary
        case .username: return UsernameResult.close
        case .editProfile: return EditProfileResult.close
        default: return PopupResult.close
        }
    }
}
