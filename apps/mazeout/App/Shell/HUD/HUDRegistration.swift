import SwiftUI
import PathCore

// Kit component `hud` (kit/hud/hud): the level HUD's Loading warm-up renders (every tier and booster state: its chrome rasters
// are made behind Loading, not on the first level's cut). Moved as they were from S2Popups.prewarm (HUD/S2Hooks.swift) in the
// kit decoupling step; GameComponents.swift lists it. The HUD itself is placed by the game loop's GameScreen.

@MainActor enum HUDRegistration {
    static func register() {
        ShellPrewarmItems.register(order: 460) { _, _ in
            var items: [ShellPrewarmItem] = []
            for (i, model) in prewarmHUDs.enumerated() { items.append(ShellPrewarmItem("hud.\(i)", HUDView(model: model))) }
            return items
        }
    }

    /// Three HUD models (normal / Hard / Super Hard; stock, empty and a lost heart) for the warm-up render.
    private static let prewarmHUDs: [HUDModel] = LevelTag.allCases.map { tag in
        let m = HUDModel()
        HUDSample.fill(m, tag: tag, hearts: tag == .normal ? 3 : 2)
        if tag == .superHard { m.boosters = [BoosterSlotVM(id: .freeze, state: .empty), BoosterSlotVM(id: .hint, state: .stock(12))] }
        return m
    }
}
