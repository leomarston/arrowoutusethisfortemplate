import SwiftUI
import UIKit
import StoreKit
import PathCore

// GAME G2 (SPEC-architecture §6.10, D24; SPEC-gameplay §10.6; CONSISTENCY W-24; VERIFIED phone 01:27 + V2 1372: the iOS
// "rate this app" sheet on the home right after the L34 win, before L35). Once per install (`flags.ratingPromptShown`, saved
// before asking): `AppStore.requestReview(in:)` (the iOS 16+ form; `SKStoreReviewController.requestReview(in:)` is deprecated
// on iOS 18) on the active window scene, at the end of that home's queue (after the home-return sequence and the claims,
// MA §8.3). iOS decides whether the sheet really shows (at most 3 times a year; in development builds always).
// Suppressed under `-pc.uitest` / `-pc.capture` unless `-pc.rating 1` (§9.1) — then nothing is marked, so a real run still
// asks. Log: `[PC][rating] requestReview after the L34 win (once per install)`.

@MainActor enum RatingDirector {
    /// true = asked (or already asked before): the caller clears its due flag.
    @discardableResult
    static func requestIfDue(_ app: AppModel, due: Bool) -> Bool {
        let s = app.store.state
        let after = app.tuning.game.ratingAfterLevel
        guard !s.flags.ratingPromptShown else { return true }
        // due = the L34 win's Continue landed here; or the next home after it (the queue was left early)
        guard due || s.level == after + 1 else { return false }
        guard app.args.ratingPromptAllowed, !NotificationPrompt.isUnitTestHost else {
            Log.mark("rating", "due after the L\(after) win but suppressed (-pc.uitest / -pc.capture without -pc.rating 1)")
            return true
        }
        guard let scene = UIApplication.shared.connectedScenes
            .compactMap({ $0 as? UIWindowScene })
            .first(where: { $0.activationState == .foregroundActive }) else {
            Log.mark("rating", "due after the L\(after) win, but no active window scene: retried at the next home")
            return false
        }
        app.store.mutateAndSave { $0.flags.ratingPromptShown = true }
        Log.mark("rating", "requestReview after the L\(after) win (once per install), level \(s.level)")
        AppStore.requestReview(in: scene)
        return true
    }
}
