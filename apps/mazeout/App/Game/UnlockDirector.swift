import SwiftUI
import PathCore

// GAME G2 (SPEC-architecture §8.4 UnlockDirector, §8.5 level start step 2; SPEC-gameplay §10.4; SPEC-motion-audio §6.3;
// research/tutorials.md §6; SPEC.md §5.19/§5.26: Linked L7 · Box L11 · Pipe L21 · Elevator L31 · Door L33 · Corner L70).
// On the Play of a level whose Levels/unlocks.json feature is not in `PlayerState.unlocksSeen`, the level opens UNDER S2's
// unlock overlay ("<Title>! / Unlocked! / icon / card", the 0.90 dim, staggered pops, ♪ unlockChime on its first frame —
// S2's panel), presented in the same run-loop turn as the level's cut (S + 0.02 ≈ K): the intro (zoom, draw-in, HUD drop)
// runs underneath; the popup host holds the level timer and keeps board input closed (G1's `updateInput`), so input opens at
// max(dismiss, K + 1.015) and the timer stays frozen until the first tap. Tap anywhere dismisses (accepted from S + 0.94, S2).
// Shown once: the feature joins `unlocksSeen` when the overlay shows (saved at once), so a retry or a kill never repeats it.
// No in-board hint follows any card (VERIFIED). `-pc.unlocks skip|force` (PlayerStore) and `-pc.go level` (the first Play of
// the run skips the overlay unless `-pc.unlocks force`, SPEC-architecture §9.1).
// Log: `[PC][unlock] show <feature> L<n>` (the §9.3 mark) and `[PC][unlock] dismissed <feature> after <s> s`.

@MainActor final class UnlockDirector: GameDirector {
    unowned let game: GameController
    /// Where the rows come from (the bundle's Levels/unlocks.json through C1's LevelLibrary); tests inject theirs.
    static var source: (GameController) -> [FeatureUnlock] = { $0.services.app?.library?.unlocks ?? [] }
    /// `-pc.go level` skips the overlay on the run's first Play only.
    private static var firstPlayOfRun = true

    private(set) var shown: FeatureUnlock?

    init(_ game: GameController) { self.game = game }

    func levelStarted(_ game: GameController) {
        let s = game.services
        let firstPlay = Self.firstPlayOfRun
        Self.firstPlayOfRun = false
        guard !game.launch.isRetry else { return }
        let level = game.stages.indices.contains(game.setup?.firstStage ?? 0) ? game.stages[game.setup?.firstStage ?? 0].level
            : (game.plan.levels.first ?? 0)
        guard let u = Self.source(game).first(where: { $0.level == level }) else { return }
        guard !s.store.state.unlocksSeen.contains(u.feature.rawValue) else { return }
        if firstPlay, s.args.go == .level, s.args.unlocks != .force {
            Log.mark("unlock", "\(u.feature.rawValue) L\(level) skipped (-pc.go level without -pc.unlocks force)")
            return
        }
        shown = u
        s.store.mutateAndSave { $0.unlocksSeen.insert(u.feature.rawValue) }
        Log.mark("unlock", "show \(u.feature.rawValue) L\(level)")
        let popups = s.popups, clock = s.clock
        let t0 = clock.gameTime()
        Task { @MainActor [game] in
            let r = await popups.present(Popup<PopupResult>.unlockOverlay(u.feature))
            Log.mark("unlock", String(format: "dismissed %@ after %.2f s (%@)", u.feature.rawValue, clock.gameTime() - t0, "\(r)"))
            withExtendedLifetime(game) {}
        }
    }
}
