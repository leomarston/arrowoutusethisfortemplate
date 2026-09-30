import SwiftUI
import PathCore

// SOCIAL SOC2 (SPEC-architecture §3.5 item 17, SPEC.md §5.17: owners plug in through `extension <X>Entry { static func make… }`
// with the EXACT signatures of ShellContract.swift `SocialEntryPoint`). SOCIAL provides:
//   makeEventScreen   `Screen.event(.claw | .streakRace | .rocketRace | .skyJump)` → the full-screen event pages
//   makeLeaderboard   the Leaderboard tab body: the leaderboard component's own (LeaderboardViews.swift; kit decoupling step)
//   makeDebugScreen   `-pc.go sociallab` → SocialLab (the world at a chosen time, scrubbing, the scroll bench)
// Each entry installs the SocialModel (idempotent) — S3 pre-renders the Leaderboard page behind Loading, so the model, its
// hooks and the first background snapshots are ready before the first screen.

extension SocialEntry {
    static func makeEventScreen(_ screen: EventScreen, app: AppModel) -> AnyView {
        SocialModel.install(app)
        switch screen {
        case .claw: return AnyView(SocClawPage())
        case .streakRace: return AnyView(SocStreakPage())
        case .rocketRace: return AnyView(SocRocketPage())
        case .skyJump: return AnyView(SocSkyMap())
        // B1 (contract amend 4, SPEC.md §5 item 42): Up & Away's page (BalloonViews.swift; the v582 Balloon Rise rules)
        case .balloonRise: return AnyView(SocBalloonPage())
        }
    }

    #if DEBUG || PC_MEASURE
    // SocialLab is Debug / Measure only; the Release build keeps SocialEntryPoint's default (no debug screen)
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? {
        guard name == LabID.sociallab.rawValue else { return nil }
        SocialModel.install(app)
        return AnyView(SocialLab())
    }
    #endif
}
