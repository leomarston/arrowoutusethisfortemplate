import SwiftUI
import PathCore

// Kit component `unlock-cards` (kit/popups/unlock-cards): the unlock overlay in the popup host, its `-pc.popup unlock[:id]` id
// and its parts' Loading warm-up. Moved as they were from S2Popups (HUD/S2Hooks.swift) in the kit decoupling step;
// GameComponents.swift lists it.

@MainActor enum UnlockCardsRegistration {
    static func register() {
        PopupPanels.register(PopupPanelProvider("unlock-cards", handles: { r in
            if case .unlockOverlay = r { return true }
            return false
        }, variant: { r, _ in
            if case .unlockOverlay(let f) = r { return f.rawValue }
            return ""
        }, make: { r, answer in
            guard case .unlockOverlay(let feature) = r else { return AnyView(EmptyView().popupVariantMarker(r)) }
            return AnyView(UnlockOverlay(feature: feature, answer: answer).popupVariantMarker(r))
        }))
        DebugPopups.register { p, app in
            guard p.id == PopupID.unlockOverlay.rawValue else { return false }
            let f = FeatureID(p.variant ?? "pipe")
            let r = await app.popups.present(Popup<PopupResult>.unlockOverlay(f))
            Log.mark("popup", "unlock → \(r)")
            return true
        }
        ShellPrewarmItems.register(order: 420) { _, _ in [ShellPrewarmItem("unlockParts", ReferenceCanvas { UnlockParts_Prewarm() })] }
    }
}
