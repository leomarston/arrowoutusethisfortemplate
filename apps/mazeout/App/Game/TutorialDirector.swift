import SwiftUI
import UIKit
import PathCore

// GAME G2 (SPEC-architecture §8.4 TutorialDirector; SPEC-gameplay §10.2; SPEC-motion-audio §6.4; research/tutorials.md §3;
// CONSISTENCY L-14, T-29). Plays Levels/tutorials.json steps on the level screen through S2's TutorialLayer (the caption + our
// hand; `GameController.hint`). v552 ships ONE step: "Tap to move!" on stage 1 of "Levels 1-4":
//   trigger    `stageReady`: the stage's board is built and its intro acked (`.timerArmed`); the step shows at the stage-1
//              board's FIRST VISIBLE FRAME + `tutorial.showAfter` (0.36 s, VERIFIED V1 0.44 → 0.80). On the FTUE board that
//              frame is the start of the Loading cross-fade (the router's level layer turning opaque), which is ≈ 2 frames
//              after the board's draw-in begins (K); anywhere else the step shows on the intro ack (K + 1.015).
//              Input is closed for those ≤ 2 frames only (`allowedTargets = []`), so no tap can beat the hint.
//   hand       the fingertip at `hand.at` in the level's lattice (integer = a cell centre): [0.89, 1.06] on arrow 1 = its
//              left stroke edge, 38 % down its drawn length (T-29), converted to screen points through the board's own
//              `screenPoint(of:)` (the arrow's middle cell) and `pitchOnScreen`;
//   dismiss    `anyTap`: the first accepted tap of ANY arrow (an exit or a bump) — the caption scales out 0.16 s, the hand fades
//              0.12 s (S2); `targetTap`: only the hand's arrow, input restricted to it while the step is up;
//   holdTimer  false for "Tap to move!" (the timer starts at that first tap as always, VERIFIED tutorials §3/§8);
//   done       `PlayerState.tutorialsDone` gets the id at the dismissal (saved): never shown again. Quitting before any tap
//              keeps it pending (the retry shows it).
// Tests and captures (`-pc.uitest` / `-pc.capture`) show no hint unless `-pc.tutorials force` (SPEC-architecture §9.1).
// Log: `[PC][tutorial] show <id> …` with the offsets from K and from the first visible frame, `[PC][tutorial] dismiss <id> …`.
// Template phase 2: genre-agnostic — the steps are the module's in generic form (`TutorialStep`: the hand points at a
// `PuzzleTarget`, the board turns it into the fingertip, `PuzzleBoard.handPoint`); "a tap" is any output whose puzzle event
// reports a resolved move; the input restriction is the board's `allowedTargets`.

@MainActor final class TutorialDirector: GameDirector {
    unowned let game: GameController
    /// Where the steps come from (the bundle's Levels/tutorials.json through C1's LevelLibrary); tests inject theirs.
    static var source: (GameController) -> [TutorialStep] = { $0.services.puzzle.tutorials }

    private var pending: [TutorialStep] = []
    private(set) var active: TutorialStep?
    private var activeStage: Int?
    private var tappedStages: Set<Int> = []
    private var gated = false
    private var shownAt: Double?

    init(_ game: GameController) { self.game = game }

    private var services: GameServices { game.services }

    /// Tests / captures: off unless forced.
    static func allowed(_ args: LaunchArgs) -> Bool { !args.quietUI || args.tutorials == .force }

    // MARK: GameDirector

    func levelStarted(_ game: GameController) {
        guard Self.allowed(services.args) else { return }
        let done = services.store.state.tutorialsDone
        let levels = Set(game.stages.map(\.level))
        pending = Self.source(game).filter { levels.contains($0.level) && !done.contains($0.id.rawValue) }
        fromLoading = services.router.screen == .loading
        if !pending.isEmpty, fromLoading { watchCrossFade() }
        if !pending.isEmpty {
            Log.mark("tutorial", "pending in \(game.levelName): " + pending.map { "\($0.id.rawValue)@L\($0.level)s\($0.stage + 1)" }
                .joined(separator: ","))
        }
    }

    func handle(_ outputs: [SessionOutput], game: GameController) {
        for o in outputs {
            switch o {
            case .meta(.timerArmed(let k, _)):
                trigger(.stageReady, stage: k)
            case .meta(.timerStarted(let k)):
                trigger(.firstTap, stage: k)
            case .meta(.stageCleared(_)), .meta(.won(_)), .meta(.lost(_)):
                clear(reason: "the stage ended")
            case .puzzle(let p):
                if let move = p.move { tapped(move.target) }             // an exit or a bump: an accepted move
            default:
                break
            }
        }
    }

    func teardown(_ game: GameController) {
        if gated { game.board.allowedTargets = nil; gated = false }
        if active != nil { clear(reason: "the Play ended") }
    }

    // MARK: show

    private func trigger(_ t: TutorialTrigger, stage k: Int) {
        guard k < game.stages.count, !pending.isEmpty else { return }
        let level = game.stages[k].level
        guard let i = pending.firstIndex(where: { $0.trigger == t && $0.level == level && $0.stage == k }) else { return }
        let script = pending.remove(at: i)
        if t == .firstTap {
            show(script, stage: k, anchor: nil)
        } else {
            schedule(script, stage: k)
        }
    }

    /// `stageReady`: at the board's first visible frame + showAfter. From Loading that frame is the cross-fade's start
    /// (watched from `levelStarted`, when the Play is built under the opaque Loading screen).
    private func schedule(_ script: TutorialStep, stage k: Int) {
        let showAfter = services.tuning.ui.file.double("tutorial.showAfter", 0.36)
        let clock = services.clock
        let k0 = game.cutAt
        guard fromLoading, k == game.setup?.firstStage ?? 0 else {
            // on the intro ack: K + 1.015 after a hard cut (home, a win panel, Try Again)
            show(script, stage: k, anchor: (k0, k0))
            return
        }
        // FTUE: close input for the few frames until the hint shows (nothing may beat it)
        game.board.allowedTargets = []
        gated = true
        Task { @MainActor [weak self, game] in
            var frames = 0
            while self?.fadeStart == nil, frames < 240, !game.isTornDown {
                await FrameWaiter.frames(1)
                frames += 1
            }
            guard let self, !game.isTornDown else { return }
            let first = self.fadeStart ?? k0
            let due = first + showAfter
            while clock.gameTime() < due - 0.004, !game.isTornDown { await FrameWaiter.frames(1) }
            guard !game.isTornDown else { return }
            guard !self.tappedStages.contains(k) else {
                self.ungate()
                Log.mark("tutorial", "\(script.id.rawValue) not shown: the stage was already tapped")
                return
            }
            self.show(script, stage: k, anchor: (k0, first))
            self.ungate()
        }
    }

    /// The Play was built under Loading (the FTUE's first board): the router cross-fades it in.
    private var fromLoading = false
    /// MotionClock game time of the first frame the level layer is fading in (the board's first visible frame).
    private var fadeStart: Double?

    private func watchCrossFade() {
        guard let router = services.router as? Router else { return }
        let clock = services.clock
        Task { @MainActor [weak self, game] in
            for _ in 0..<600 {
                await FrameWaiter.frames(1)
                guard let self, !game.isTornDown else { return }
                if router.layers.contains(where: { $0.screen.isLevel && $0.opacity >= 1 }) {
                    self.fadeStart = clock.gameTime()
                    Log.mark("tutorial", String(format: "the board's first visible frame (Loading cross-fade start) at K+%.3f s",
                                                clock.gameTime() - game.cutAt))
                    return
                }
            }
        }
    }

    private func ungate() {
        guard gated else { return }
        gated = false
        if active?.dismiss != .targetTap { game.board.allowedTargets = nil }
    }

    /// `anchor` = (K, the board's first visible frame) in MotionClock game time, for the log.
    private func show(_ script: TutorialStep, stage k: Int, anchor: (Double, Double)?) {
        let clock = services.clock
        let now = clock.gameTime()
        let tip = fingertip(script)
        if let caption = script.caption {
            game.hint.show(caption: LocalizedStringResource(String.LocalizationValue(caption)), fingertip: tip ?? .zero, clock: clock)
        } else {
            Log.error("tutorial", "\(script.id.rawValue) has no caption: S2's TutorialLayer draws caption + hand only")
        }
        active = script
        activeStage = k
        shownAt = now
        if script.holdTimer { game.session?.hold(.tutorial) }
        if script.dismiss == .targetTap, let a = script.hand?.target {
            game.board.allowedTargets = Set(script.allowedTargets ?? [a])
        } else if let only = script.allowedTargets {
            game.board.allowedTargets = Set(only)
        }
        var line = "show \(script.id.rawValue) L\(game.stages[k].level) stage \(k + 1)"
        if let (k0, first) = anchor {
            line += String(format: ": K+%.3f s, first visible frame+%.3f s (spec +%.2f)", now - k0, now - first,
                           services.tuning.ui.file.double("tutorial.showAfter", 0.36))
        }
        if let tip { line += String(format: ", fingertip (%.1f, %.1f)", tip.x, tip.y) }
        line += ", holdTimer \(script.holdTimer), dismiss \(script.dismiss.rawValue)"
        Log.mark("tutorial", line)
    }

    /// The fingertip on screen: the board converts the hand's target + offset (Arrow Out: `hand.at` in lattice coordinates
    /// relative to the arrow's middle cell, scaled by the pitch).
    private func fingertip(_ script: TutorialStep) -> CGPoint? {
        guard let hand = script.hand else { return nil }
        return game.board.handPoint(for: hand.target, at: hand.at)
    }

    // MARK: dismiss

    private func tapped(_ target: PuzzleTarget) {
        if let s = activeStage { tappedStages.insert(s) } else if let k = game.session?.stage { tappedStages.insert(k) }
        guard let script = active else { return }
        if script.dismiss == .targetTap, let a = script.hand?.target, a != target { return }
        guard script.dismiss == .anyTap || script.dismiss == .targetTap else { return }
        let clock = services.clock
        game.hint.dismiss(clock: clock)
        finish(script, how: "the first tap (\(target)) " + String(format: "%.3f s after the show", clock.gameTime() - (shownAt ?? 0)))
    }

    private func finish(_ script: TutorialStep, how: String) {
        if script.holdTimer { game.session?.release(.tutorial) }
        if script.dismiss == .targetTap || script.allowedTargets != nil { game.board.allowedTargets = nil }
        active = nil
        activeStage = nil
        services.store.mutateAndSave { $0.tutorialsDone.insert(script.id.rawValue) }
        Log.mark("tutorial", "dismiss \(script.id.rawValue) on \(how); done (tutorialsDone \(services.store.state.tutorialsDone.sorted()))")
    }

    private func clear(reason: String) {
        guard let script = active else { return }
        if script.holdTimer { game.session?.release(.tutorial) }
        if script.dismiss == .targetTap || script.allowedTargets != nil { game.board.allowedTargets = nil }
        game.hint.clear()
        active = nil
        activeStage = nil
        Log.mark("tutorial", "\(script.id.rawValue) cleared (\(reason)); still pending for the next Play")
    }
}
