import SwiftUI
import PathCore

// Kit component `social-ui` (kit/social-events/social-ui): the Leaderboard tab page (the page shell; its body is the
// leaderboard component's `SocialEntry.makeLeaderboard`) and its Loading warm-up. HomeView and S3Hooks.swift (S3Popups.prewarm)
// named LeaderboardPageShell until the kit decoupling step; GameComponents.swift lists it.

@MainActor enum SocialUIRegistration {
    static func register() {
        ShellScreens.registerTabPage(.leaderboard) { AnyView(LeaderboardPageShell()) }
        ShellPrewarmItems.register(order: 160) { _, _ in [ShellPrewarmItem("leaderboardShell", LeaderboardPageShell())] }
    }
}
