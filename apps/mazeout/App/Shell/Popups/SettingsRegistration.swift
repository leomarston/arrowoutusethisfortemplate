import SwiftUI
import PathCore

// Kit component `settings` (kit/meta/settings): the Settings page and the offline pages (`.custom("page.support" |
// "page.terms" | "page.privacy")`, full pages) in the popup host, their `-pc.popup page.*` ids (over Settings) and the
// Settings warm-up. Named by PopupHost's `PopupContent`, the router's `DebugPopupLauncher` and RootView's `ShellPrewarm`
// until the kit decoupling step; GameComponents.swift lists it. `-pc.popup settings` / `-pc.go settings` stay the router's.

@MainActor enum SettingsRegistration {
    static func register() {
        PopupPanels.register(PopupPanelProvider("settings", handles: isOwn, isPage: isOwn, make: { r, answer in
            if case .custom(let id, _) = r, let kind = InfoPage.Kind(popupID: id) { return AnyView(InfoPage(kind: kind, answer: answer)) }
            return AnyView(SettingsPopup(answer: answer))
        }))
        DebugPopups.register { p, app in
            // S1-private ids for the offline pages (`-pc.popup page.support|page.terms|page.privacy`), over Settings
            guard InfoPage.Kind(popupID: p.id) != nil else { return false }
            let popups = app.popups
            let id = p.id
            Task { @MainActor in _ = await popups.present(Popup<PopupResult>.settings) }
            for _ in 0..<60 where popups.topID != .settings { try? await Task.sleep(nanoseconds: 16_000_000) }
            let r = await popups.present(Popup<PopupResult>(.custom(id: id, params: [:]), style: PopupStyle(dim: .none), fallback: .close))
            Log.mark("popup", "\(id) → \(r)")
            return true
        }
        ShellPrewarmItems.register(order: 300) { _, host in
            [ShellPrewarmItem("settings", ReferenceCanvas { SettingsPopup(answer: PopupAnswer(id: -2, host: host)) })]
        }
    }

    /// Settings, and the offline pages (both full pages on the live screen).
    private static func isOwn(_ r: PopupRequest) -> Bool {
        switch r {
        case .settings: return true
        case .custom(let id, _): return InfoPage.Kind(popupID: id) != nil
        default: return false
        }
    }
}
