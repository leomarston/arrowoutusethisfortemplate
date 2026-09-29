import SwiftUI
import PathCore

// GAME G2 (SPEC-architecture §8.4 FTUEDirector, §6.2, §8.5; SPEC-gameplay §10.1–§10.3, §12.1; research/tutorials.md §1, §12;
// CONSISTENCY T-14, T-31, U-7). The first-time user experience from a fresh install with NO launch arguments:
//   Loading (+ the notification prompt over it, NotificationPrompt) → a 0.13 s cross-fade into "Levels 1-4" stage 1 with the
//   HUD in place ("Tap to move!", TutorialDirector) → the four boards → "Level 1-4" / 80 → Continue → Level 5 (hard cut + the
//   HUD intro) → 20 → Level 6 → 20 → Continue → the FIRST HOME, which flies the banked +120 onto the 1000 start (1000 → 1120,
//   S3's PayoutSequence). Nothing pops up on that home. From L7 on every win returns home.
// Who does what: the chain's routing is SHELL's Router (`screenAfterWin`: while `homeSeen` is false and the next level is below
// game.json `ftue.chainUntilLevel` 7, the next screen is that level; a loss before the first home retries, T-31); the coins are
// C3's (banked at each win into `pendingCoinFly`); G1's WinDirector hands each Continue to the router. This director:
//   - the first launch's own writes (boot, once per install, `flags.seen "firstLaunch"`): Settings' Music = OFF (U-7: v552's
//     Music button is inert and reads OFF; the ◆ default is true, so G2 writes false at the first launch, GP §17.1 #2);
//   - the FTUE log that proves the chain: `[PC][ftue] …` at every Play and Continue while home was never seen.

@MainActor final class FTUEDirector: GameDirector {
    unowned let game: GameController

    init(_ game: GameController) { self.game = game }

    // MARK: first launch (boot)

    static func firstLaunchWrites(_ app: AppModel) {
        guard !app.store.state.flags.seen.contains("firstLaunch") else { return }
        app.store.mutateAndSave {
            $0.flags.seen.insert("firstLaunch")
            $0.settings.music = false
        }
        app.audio.apply(settings: app.store.state.settings)
        let s = app.store.state
        Log.mark("ftue", "first launch: Music OFF written (U-7); level \(s.level), coins \(s.coins), boosters "
                 + s.boosters.sorted { $0.key < $1.key }.map { "\($0.key)=\($0.value)" }.joined(separator: ",")
                 + ", home seen \(s.homeSeen)")
    }

    // MARK: the chain's log

    func levelStarted(_ game: GameController) {
        let s = game.services.store.state
        guard !s.homeSeen else { return }
        Log.mark("ftue", "chain: \(game.levelName) (\(game.plan.levels.count) board\(game.plan.levels.count == 1 ? "" : "s"))"
                 + (game.launch.isRetry ? " retry" : "") + ", coins \(s.coins), pending fly \(s.pendingCoinFly)")
    }

    func afterWin(_ summary: WinSummary, game: GameController) async {
        let s = game.services.store.state
        guard !s.homeSeen else { return }
        let until = game.services.tuning.game.ftueChainUntilLevel
        if s.level < until {
            Log.mark("ftue", "chain: \(game.levelName) won +\(summary.reward) → L\(s.level) directly (no home), pending fly \(s.pendingCoinFly)")
        } else {
            Log.mark("ftue", "chain: \(game.levelName) won +\(summary.reward) → the first home: +\(s.pendingCoinFly) flies onto "
                     + "\(s.coins - s.pendingCoinFly) → \(s.coins)")
        }
    }

    func afterLoss(_ reason: LossReason, game: GameController) async {
        guard !game.services.store.state.homeSeen else { return }
        Log.mark("ftue", "chain: \(game.levelName) lost (\(reason.rawValue)) before the first home: X or Try Again retries (T-31)")
    }
}
