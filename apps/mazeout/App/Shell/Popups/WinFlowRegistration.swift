import SwiftUI
import PathCore

// Kit component `win-flow` (kit/popups/win-flow): the win panel in the popup host, its `-pc.popup win[:tag]` id and the
// Loading warm-up of every tier. Moved as they were from S2Popups (HUD/S2Hooks.swift) in the kit decoupling step;
// GameComponents.swift lists it. The strip under the panel is a slot (`PanelStrips`) the event components fill.

@MainActor enum WinFlowRegistration {
    static func register() {
        PopupPanels.register(PopupPanelProvider("win-flow", handles: { r in
            if case .winPanel = r { return true }
            return false
        }, variant: { r, _ in
            if case .winPanel(let s) = r { return s.tag.rawValue }                  // SPEC-ui §6: win = the tier
            return ""
        }, make: { r, answer in
            guard case .winPanel(let summary) = r else { return AnyView(EmptyView().popupVariantMarker(r)) }
            return AnyView(WinPanel(summary: summary, answer: answer).popupVariantMarker(r))
        }))
        DebugPopups.register { p, app in await debugPresent(p, app: app) }
        ShellPrewarmItems.register(order: 410) { app, host in prewarm(app, host: host) }
    }

    /// `-pc.popup win[:normal|hard|superHard]`. False for an id this component does not own.
    private static func debugPresent(_ p: LaunchArgs.PopupArg, app: AppModel) async -> Bool {
        guard p.id == PopupID.winPanel.rawValue else { return false }
        let tag = LevelTag(label: p.variant) ?? .normal
        let reward = Int(app.tuning.rules.double("rewards.\(tag.rawValue)", tag == .normal ? 20 : (tag == .hard ? 60 : 100)))
        let lv = app.levelLaunch(for: app.store.state.level).levels
        let summary = WinSummary(levels: lv, reward: lv.count > 1 ? 80 : reward, tag: tag)
        let r = await app.popups.present(Popup<PopupResult>.winPanel(summary))
        Log.mark("popup", "win → \(r)")
        return true
    }

    /// Every win tier, not only Normal (FEEL item 1: the Hard / Super Hard rasters — tierPanel, coinGlow, the red / purple
    /// offer wells, the tag ribbon, the skulls — and their first draw were paid on the first Hard win, 1.95 s at L19, G1).
    /// `-pc.feelPrewarm normalOnly` keeps B1's Normal-only list (the before/after measurement).
    private static func prewarm(_ app: AppModel, host: PopupHost) -> [ShellPrewarmItem] {
        let tiers: [LevelTag] = app.args.raw["pc.feelPrewarm"] == "normalOnly" ? [.normal] : LevelTag.allCases
        var items: [ShellPrewarmItem] = []
        for (i, tag) in tiers.enumerated() {
            items.append(ShellPrewarmItem("win.\(tag.rawValue)", ReferenceCanvas {
                WinPanel(summary: WinSummary(levels: [32], reward: tag == .normal ? 20 : (tag == .hard ? 60 : 100), tag: tag),
                         answer: PopupAnswer(id: -15 - i, host: host), prewarm: true)
            }))
        }
        return items
    }
}
