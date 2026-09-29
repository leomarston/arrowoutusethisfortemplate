import SwiftUI
import UIKit
import PathCore

// GAME G2 (SPEC-architecture §8.4, §8.5 step 4, §8.6, §6.10; §12.2 G2). Where G2 plugs into the app:
//  - per Play: the directors below, installed through G1's `GameDirectors.make` entry point (the WP0 pattern: a static member
//    declared on the concrete enum wins over the protocol-extension default). Order = the order their hooks run in step 6 of
//    the §8.1 fan-out: the unlock overlay first (it covers the level's first frame), then the tutorial, the boosters, the
//    events and the FTUE log;
//  - per app run: `G2App` — the boot step 4 (first-launch writes + the notification prompt over Loading), the home queue
//    (claims, offers, the rating prompt after L34) and the scene-phase hooks (local notifications, the events' refresh on
//    foreground). AppModel (GAME's composition root) calls these three one-liners.

extension GameDirectors {
    static func make(_ game: GameController) -> [any GameDirector] {
        // META: MetaDirector last (it only reports the banked win to MetaAds)
        [UnlockDirector(game), TutorialDirector(game), BoosterDirector(game), EventsDirector(game), FTUEDirector(game), MetaDirector(game)]
    }
}

/// The app-run half of G2 (AppModel calls these).
@MainActor enum G2App {
    /// Boot step 4 begins (behind Loading, in parallel with the warm-ups): the first launch's writes and the notification
    /// prompt over Loading. The returned task ends when the prompt was answered (or at once when there is none).
    static func bootBegan(_ app: AppModel) -> Task<Void, Never> {
        FTUEDirector.firstLaunchWrites(app)
        HomeQueue.shared.start(app)
        EventsGlue.install(app)
        MetaAds.shared.boot(app)                        // META: the mode; a live run starts the SDK a few frames later
        return Task { @MainActor in await NotificationPrompt.askIfNeeded(app) }
    }

    /// Boot step 4 ends: Loading stays up while the iOS alert is (VERIFIED F00 / V2 3.0–6.0 s: the prompt sits over Loading).
    static func bootEnding(_ app: AppModel, prompt: Task<Void, Never>) async {
        let t0 = ProcessInfo.processInfo.systemUptime
        await prompt.value
        let waited = ProcessInfo.processInfo.systemUptime - t0
        if waited > 0.05 { Log.mark("notif", String(format: "Loading held %.2f s for the notification prompt's answer", waited)) }
    }

    /// §8.6: background → schedule the local notifications (lives full, the Weekly Contest ending); active → cancel them
    /// (they are only for a closed game) and refresh the events on the wall clock.
    static func sceneChanged(_ app: AppModel, _ phase: ScenePhase) {
        switch phase {
        case .background: LocalNotifications.reschedule(app)
        case .active:
            LocalNotifications.cancelAll(app)
            HomeQueue.shared.foreground()
            MetaAds.shared.activate()                   // META: a Meta session (live mode only)
        default: break
        }
    }
}
