import SwiftUI
import PathCore

// SHELL S2: the fixed HUD states (Level 32 · 3:00 / Level 34 · 3:30 / Level 39 · 3:00, coins 2240, boosters 3 / 3) that the
// shell's warm-up renders behind Loading (S2Hooks `prewarmHUDs`) and the HUD lab pages show (HUD/ShellLab+HUD.swift, Debug /
// Measure only). Shipping code: it was `HUDLab.fill` / `HUDLab.text` in the lab file until the labs left the Release build.

@MainActor enum HUDSample {
    static func fill(_ hud: HUDModel, tag: LevelTag, hearts: Int) {
        let level = tag == .normal ? 32 : (tag == .hard ? 34 : 39)
        let secs = tag == .hard ? 210 : 180
        hud.levelLabel = "Level \(level)"
        hud.tag = tag
        hud.timerSeconds = secs
        hud.timerText = HUDSample.text(secs)
        hud.timerFrozen = true
        hud.hearts = (0..<3).map { $0 < hearts ? .full : .lost }
        hud.coins = 2240
        hud.boosters = [BoosterSlotVM(id: .freeze, state: .stock(3)), BoosterSlotVM(id: .hint, state: .stock(3))]
        hud.introPhase = .shown
        hud.isVisible = true
    }

    /// "m:ss" with no leading zero on the minutes (SPEC-motion-audio §4).
    static func text(_ s: Int) -> String { "\(s / 60):" + String(format: "%02d", s % 60) }
}
