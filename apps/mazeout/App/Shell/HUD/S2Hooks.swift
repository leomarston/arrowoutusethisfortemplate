import SwiftUI
import UIKit
import PathCore

// SHELL S2: the app reference the Core Animation effects need (the win haptic, the skip click, the freeze's clock) and the
// Shop route of the offers' coin groups. Nothing here changes a ◆ contract.
// Kit decoupling step (docs/ROADMAP.md): the S2 panels, their `-pc.popup` launchers and warm-up items, and the S2 effects no
// longer live here — each component registers its own (ShellRegistry.swift, FXOverlayView.swift `FXEffects`):
//   fail-flow        outOfTime / continue / levelFailed      Popups/FailFlowRegistration.swift
//   win-flow         the win panel                           Popups/WinFlowRegistration.swift
//   unlock-cards     the unlock overlay                      Popups/UnlockCardsRegistration.swift
//   claim-reward     the claim screen                        Popups/ClaimRewardRegistration.swift
//   hud              the HUD warm-up renders                 HUD/HUDRegistration.swift
//   win-celebration  `.celebration` (+ its skip)             FX/WinCelebrationRegistration.swift
//   boosters         the Time Freeze (`.custom("freeze")`)   HUD/BoostersRegistration.swift
//   confetti         `.confetti`                             FX/ConfettiRegistration.swift
//   fireworks        `.fireworks`                            FX/FireworksRegistration.swift

@MainActor enum S2Hooks {
    /// The running app (set by the shell's first render); the CA effects use it for the win haptic and the skip click.
    static weak var app: AppModel?

    /// The offers' coin group → the Shop as a closable page over the offer (SPEC-ui §2.6.6). The Shop is S3's; until it lands
    /// the tap is logged and nothing opens (never a dead-end: the offer stays up and answers normally).
    static var shopOpener: ((AppModel) -> Void)?
    static func openShop(_ app: AppModel) {
        if let shopOpener { shopOpener(app) } else { Log.mark("popup", "coin group → Shop: S3's Shop page is not installed yet") }
    }

    /// Behind Loading: the app reference (the components' own warm-ups follow: `ShellWarmUps`, e.g. the celebration's logo
    /// split off the main thread).
    static func warmUp(_ app: AppModel) {
        self.app = app
    }
}
