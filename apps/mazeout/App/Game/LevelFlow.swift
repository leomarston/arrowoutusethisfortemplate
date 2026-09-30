import SwiftUI
import UIKit
import PathCore

// GAME G1 (SPEC-architecture §8.4 LevelFlow, §8.5 level start, §8.6; SPEC-gameplay §5, §7.2, §7.3, §8.2; SPEC-motion-audio
// §3.6, §3.7; CONSISTENCY T-7, T-10, T-14, T-32). The level's start sequence and its lifecycle:
//  - start: C3's lives gate (`Economy.startAttempt`: a life is taken at the start, refunded on a win; 0 lives → the More
//    Lives popup instead of the level), the C2 session over the session's boards, `board.load` (≤ 5 ms, no await, no
//    spinner: the original hard-cuts), the intro (`growFromTails` with the HUD drop from home / a win panel / Try Again;
//    `growFromTailsNoHUD` when Loading cross-fades straight into the level), the HUD's first state, one level ahead
//    (C4's provider + the next session's decode and sprites);
//  - stage transitions ("Levels 1-4"): at the stage's W the board plays the clear wave + the swap at W + stage gap (the
//    session's `stage_gap_s`, board.json the default: T-7), the HUD timer re-arms at the swap, the session re-arms at the
//    board's `stageTransitionDone`;
//  - Pause (HUD pause) and "Quit Level?" (HUD back, Pause → Quit): the timer holds while they are up; Quit → the session's
//    `.lost(.quit)` → Level Failed directly (FailFlowDirector);
//  - background: the timer holds (`.background`) and the Pause popup is up on the return (§8.6);
//  - the debug outcome jumps `-pc.win <tag>` / `-pc.lose timeUp|hearts|quit` (§9.1).
// Template phase 2: genre-agnostic — the stages and the session come from the active module (`services.puzzle`), the board
// is a `PuzzleBoard`, the booster corners are the module's `BoosterSpec`s.

@MainActor final class LevelFlow: GameDirector {
    unowned let game: GameController
    private var debugJumpDone = false

    init(_ game: GameController) { self.game = game }

    private var services: GameServices { game.services }
    private var session: (any PuzzleSession)? { game.session }

    // MARK: start (§8.5)

    /// Builds the Play. false = refused (a missing level, no lives: the More Lives popup is up instead).
    func start() -> Bool {
        let t0 = CACurrentMediaTime()
        let s = services
        let plan = game.plan
        // the boards first: a level that cannot load never costs a life (the module logs which one is missing)
        guard let stages = s.puzzle.stages(for: plan, args: s.args), !stages.isEmpty else { return false }

        // the lives gate (C3): a life is taken now and given back on a win
        let now = s.clock.wallClock()
        var result = s.store.mutateAndSave { Economy.startAttempt(&$0, levels: plan.levels, now: now, rules: s.economy) }
        if case .failure(.attemptInProgress) = result {
            let stale = s.store.state.activeAttempt
            Log.error("game", "an attempt was still open (\(stale?.session ?? "?")): finished as a loss, then this Play starts")
            s.store.mutateAndSave { st in
                Economy.finishAttempt(&st, outcome: .lost(.killed), now: now, rules: s.economy)
                _ = Events.onLoss(&st, LossContext(levels: stale?.levels ?? plan.levels, reason: .killed, now: now), rules: s.economy)
            }
            result = s.store.mutateAndSave { Economy.startAttempt(&$0, levels: plan.levels, now: now, rules: s.economy) }
        }
        var setup: AttemptSetup
        switch result {
        case .success(let a):
            setup = a
        case .failure(.noLives):
            Log.mark("game", "\(game.levelName): 0 lives → More Lives (SPEC-gameplay §8.2)")
            let launch = game.launch
            let popups = s.popups, store = s.store, router = s.router, economy = s.economy, clock = s.clock
            Task { @MainActor in
                _ = await popups.present(Popup<PopupResult>.noLives)
                if Economy.livesCount(store.state, now: clock.wallClock(), rules: economy) > 0
                    || Economy.hasUnlimitedLives(store.state, now: clock.wallClock()) {
                    Log.mark("game", "lives are back: the level starts at once")
                    router.go(.level(launch))
                }
            }
            return false
        case .failure(let e):
            Log.error("game", "\(game.levelName): the attempt did not start (\(e))")
            return false
        }
        setup.firstStage = game.launch.isRetry ? 0 : min(max(game.launch.firstStage, 0), stages.count - 1)
        let streakActive = Events.continueWarning(s.store.state, now: now, rules: s.economy).streakActive
        let session = s.puzzle.makeSession(plan: plan, stages: stages, setup: setup, streakActive: streakActive)
        game.install(session: session, stages: stages, setup: setup)

        // the board: load (synchronously), then the intro
        let board = s.board
        board.delegate = game
        board.inputEnabled = false
        board.allowedTargets = nil
        let k = session.stage
        board.load(stageContext(k))
        let fromLoading = s.router.screen == .loading
        let style: IntroStyle = fromLoading ? .growFromTailsNoHUD : .growFromTails
        game.markCut()
        board.playIntro(style)
        s.haptics.prepare()

        // the HUD's first state (the cut): the HUD is already in place when Loading cross-fades into the level (T-14)
        let level = stages[k]
        game.hudWriter.begin(label: label(for: level), tag: level.tag, seconds: level.timerSeconds ?? 0, hearts: session.hearts,
                             maxHearts: level.hearts ?? 0, coins: s.store.state.coins, boosters: boosterSlots(),
                             intro: fromLoading ? .shown : .playing(start: game.cutAt))
        game.fanOut(session.start(), origin: .start)
        s.levelStarted(plan.levels.last ?? level.level)
        let timerText: String = level.timerSeconds.map { "\($0) s" } ?? "none"
        let heartsText: String = session.hearts.map { "\($0)" } ?? "none"
        Log.mark("game", "start \(game.levelName) attempt \(setup.attemptIndex) stage \(k + 1)/\(stages.count): L\(level.level) "
                 + "\(level.summary), timer \(timerText), hearts \(heartsText), tag \(level.tag.rawValue), "
                 + "intro \(style), lives \(s.store.state.lives.count), coins \(s.store.state.coins)"
                 + (streakActive ? ", streak x\(Events.continueWarning(s.store.state, now: now, rules: s.economy).multiplier)" : "")
                 + String(format: " (main %.2f ms)", (CACurrentMediaTime() - t0) * 1000))
        return true
    }

    /// What the board needs for stage k (the module's level, the screen, the fx seed per stage).
    func stageContext(_ k: Int) -> StageContext {
        let seed = (game.setup?.seed ?? 1) &+ UInt64(k)
        return StageContext(stage: k, stages: game.stages.count, seed: seed, screen: services.screenSize(), info: game.stages[k])
    }

    /// "Level 32", or the session's HUD label key ("Levels 1-4", sessions.json `hud_label`: a strings-table key).
    func label(for level: PuzzleStage) -> LocalizedStringResource {
        if game.plan.levels.count > 1, let key = game.plan.hudLabel { return LocalizedStringResource(String.LocalizationValue(key)) }
        return "Level \(level.level)"
    }

    /// The module's booster corners in its order (ArrowEscape: freeze left, hint right) from the player's stock (0 → the "+"
    /// badge).
    func boosterSlots() -> [BoosterSlotVM] {
        let b = services.store.state.boosters
        return game.capabilities.boosters.map { spec in
            let n = b[spec.id.rawValue] ?? 0
            return BoosterSlotVM(id: spec.id, state: n > 0 ? .stock(n) : .empty)
        }
    }

    // MARK: GameDirector

    func handle(_ outputs: [SessionOutput], game: GameController) {
        for o in outputs {
            guard case .meta(let e) = o else { continue }
            switch e {
            case .timerStarted(let stage):
                if stage < game.stages.count { Log.mark("game", "play L\(game.stages[stage].level)") }
            case .stageLoaded(let stage, _, _) where stage < game.stages.count && game.started:
                let l = game.stages[stage]
                game.hudWriter.setTag(l.tag)
                if game.plan.levels.count > 1 && game.plan.hudLabel == nil { game.hudWriter.setLabel(label(for: l)) }
            default:
                break
            }
        }
    }

    /// Every display-link frame: a pending debug jump. (The HUD stays `.playing(start: K)` after its intro: S2's HUDView
    /// pauses that timeline at rest, while a `.shown` write would swap the HUD's view branch — a measured 37–40 ms hitch at
    /// K + 1.96 s on every level, build/g1.)
    func frame(gameTime: Double) {
        #if DEBUG || PC_MEASURE
        if !debugJumpDone, game.introDone, let s = session, case .ready = s.phase, !services.popups.isPresenting {
            if services.args.win != nil || services.args.lose != nil {
                debugJumpDone = true
                runDebugJump()
            }
        }
        #else
        // the debug outcome jumps are Debug / Measure only: the store build plays the level (and says so once)
        if !debugJumpDone, services.args.win != nil || services.args.lose != nil {
            debugJumpDone = true
            Log.error("game", "-pc.win / -pc.lose: no debug outcome jump in this build (Release); they run in Debug / Measure")
        }
        #endif
    }

    // MARK: stage transitions (§5.7, MA §3.7)

    /// The stage's last exit left the board (W): the clear wave, the swap at W + gap and the next draw-in (the board's);
    /// the HUD timer re-arms at the swap.
    func stageLeftBoard(_ k: Int) {
        guard k + 1 < game.stages.count else { return }
        let next = stageContext(k + 1)
        services.board.playStageTransition(to: next)
        let gap = game.plan.stageGap ?? services.tuning.board.stageGap
        game.hudWriter.scheduleRearm(atGameTime: services.clock.gameTime() + gap, seconds: game.stages[k + 1].timerSeconds ?? 0)
        Log.mark("game", "\(game.levelName) stage \(k + 1) cleared → stage \(k + 2)/\(game.stages.count) "
                 + "L\(game.stages[k + 1].level) at W+\(gap) s")
    }

    // MARK: Pause, Quit Level? (SPEC-gameplay §7.2)

    private var isLive: Bool {
        guard let s = session, !game.isTornDown else { return false }
        switch s.phase { case .intro, .ready, .playing: return true; default: return false }
    }

    /// HUD pause: the Pause popup (Resume / Quit / X); the timer holds while it is up.
    func pause() {
        guard isLive, !services.popups.isPresenting, !game.paused else { return }
        hold()
        Log.mark("game", "\(game.levelName) paused")
        Task { @MainActor [self, game] in
            defer { withExtendedLifetime(game) {} }
            let r = await services.popups.present(Popup<PopupResult>.pause)
            guard !game.isTornDown else { return }
            if r == .secondary { await confirmQuit() }
            release()
        }
    }

    /// HUD back (any time, also before the first tap): "Quit Level?" directly.
    func back() {
        guard isLive, !services.popups.isPresenting, !game.paused else { return }
        hold()
        Task { @MainActor [self, game] in
            defer { withExtendedLifetime(game) {} }
            await confirmQuit()
            release()
        }
    }

    /// "Quit Level?" / "You will lose a life!" / Quit / X. Quit → `.lost(.quit)` → Level Failed (no offers).
    private func confirmQuit() async {
        let r = await services.popups.present(Popup<PopupResult>.quitLevel)
        guard r == .primary, let s = session, !game.isTornDown else { return }
        Log.mark("game", "\(game.levelName) quit")
        game.fanOut(s.quit(), origin: .director)
    }

    private func hold() {
        game.paused = true
        session?.hold(.pause)
        game.updateInput()
    }

    private func release() {
        game.paused = false
        session?.release(.pause)
        game.updateInput()
    }

    /// §8.6: back from the background during play → the Pause popup (unless something is already up).
    func returnedFromBackground() {
        guard isLive, !services.popups.isPresenting else { return }
        Log.mark("game", "\(game.levelName) back from the background: Pause")
        pause()
    }

    // MARK: debug outcome jumps (§9.1 `-pc.win`, `-pc.lose`; Debug / Measure only)

    #if DEBUG || PC_MEASURE
    private func runDebugJump() {
        guard let s = session else { return }
        if let tag = services.args.win {
            Log.mark("game", "-pc.win \(tag.rawValue): a synthetic win (no board play)")
            game.win.startSynthetic(tag: tag)
            return
        }
        guard let reason = services.args.lose else { return }
        Log.mark("game", "-pc.lose \(reason.rawValue)")
        switch reason {
        case .quit:
            game.fanOut(s.quit(), origin: .director)
        case .timeUp:
            Task { @MainActor [self, game] in
                defer { withExtendedLifetime(game) {} }
                // the first move starts the clock (the real pipeline), then the clock runs out
                guard let a = s.hint() else { return }
                tap(a)
                guard await game.wait(frames: 2), case .playing = s.phase else { return }
                game.fanOut(s.tick(s.clock.remaining + 0.01), origin: .tick)
            }
        case .hearts:
            Task { @MainActor [self, game] in
                defer { withExtendedLifetime(game) {} }
                var tries = 0
                while (s.hearts ?? 0) > 0, tries < 12, !game.isTornDown {
                    tries += 1
                    switch s.phase { case .ready, .playing: break; default: return }
                    // the module's deliberate mistake (ArrowEscape: a blocked arrow that is not red yet → a bump)
                    guard let a = services.puzzle.mistakeTargets(s, board: services.board).first else {
                        Log.error("game", "-pc.lose hearts: no mistake to make on L\(game.currentStage?.level ?? 0)")
                        return
                    }
                    tap(a)
                    guard await game.wait(gameSeconds: 0.6) else { return }
                }
            }
        case .killed, .outOfMoves, .stuck:
            break
        }
    }
    #endif

    /// A tap through the board's real release handler when it can (ripple, hit test), else straight to the session.
    func tap(_ target: PuzzleTarget) {
        if services.board.performTap(on: target) { return }
        game.boardInput(.tap(target), touchTimestamp: CACurrentMediaTime())
    }
}
