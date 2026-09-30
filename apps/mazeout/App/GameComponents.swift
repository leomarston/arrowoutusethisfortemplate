import SwiftUI
import PathCore

// The components this game ships, registered once (kit decoupling step; docs/guides/KIT.md §3). Each line calls the component's
// own registration (`<Name>Registration.register()`, next to its code): its popup panels and `-pc.popup` ids, its screens and
// tab pages, its Loading warm-ups and boot work, its FX effects, the strips and slots it fills in other panels
// (ShellRegistry.swift). Removing a component from a game = deleting its files and its line here (`python3 tools/kit.py rdeps
// <id>` prints the other lines that name it). The order only matters where noted; every ordered list (the warm-up items, the
// strips) carries its own `order:`, so this list reproduces the reference game's routing exactly.
// Components that plug in at compile time instead (the entry-point pattern of ShellContract.swift / PuzzleBoardContract.swift:
// the puzzle module, the level host, the leaderboard body, the audio engine) and the game loop's directors
// (GameDirectors+G2.swift) are not listed here.

@MainActor enum GameComponents {
    static func registerAll() {
        // screens
        LoadingRegistration.register()
        HomeRegistration.register()
        ProfileRegistration.register()
        ToastsRegistration.register()
        // popups and the level HUD
        PauseMenuRegistration.register()
        QuitLevelRegistration.register()
        SettingsRegistration.register()
        FailFlowRegistration.register()
        WinFlowRegistration.register()
        UnlockCardsRegistration.register()
        ClaimRewardRegistration.register()
        HUDRegistration.register()
        // economy (the boosters' Time Freeze first among the FX: `stopAll` cancels its frost first, as S2FX did)
        LivesRegistration.register()
        BoostersRegistration.register()
        ShopRegistration.register()
        // effects
        WinCelebrationRegistration.register()
        ConfettiRegistration.register()
        FireworksRegistration.register()
        SparklesRegistration.register()
        // social pages and events
        SocialUIRegistration.register()
        EventsEngineRegistration.register()
        StreakRaceRegistration.register()
        RocketRaceRegistration.register()
        BalloonRiseRegistration.register()
    }
}
