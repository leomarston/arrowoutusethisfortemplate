import SwiftUI
import PathCore

// Kit component `shop` (kit/economy/shop): the Shop tab page, the closable Shop page in the popup host (`.custom("shop")`), its
// `-pc.popup shop[:bundles|coins]` id and Loading warm-up, the boot warm-up (the offers' coin groups open the closable Shop:
// S2's `S2Hooks.shopOpener`; the store starts) and the Shop's art (kept, and decoded off the main thread before home). Named
// by RootView, S3Hooks.swift (S3Popups, S3Hooks.warmUp) and HomeView until the kit decoupling step; GameComponents.swift
// lists it.

@MainActor enum ShopRegistration {
    static func register() {
        ShellScreens.registerTabPage(.shop) { AnyView(ShopView()) }
        ShellArt.registerKept { ShopView.art }
        ShellArt.registerPreload(order: 10) { ShopView.art }
        ShellWarmUps.register(order: 20) { app in
            S2Hooks.shopOpener = { app in ShopPage.openOver(app, section: .coins) }
            if let store = app.shop as? ShopStore { Task { @MainActor in await store.start() } }
        }
        PopupPanels.register(PopupPanelProvider("shop", handles: isShopPage, isPage: isShopPage, make: { r, answer in
            guard case .custom(_, let params) = r else { return AnyView(EmptyView()) }
            return AnyView(ShopView(closable: true, initialSection: ShopSection(rawValue: params["section"] ?? "") ?? .top,
                                    onClose: { answer(PopupResult.close) }))
        }))
        DebugPopups.register { p, app in
            guard p.id == ShopPage.popupID else { return false }
            let request = PopupRequest.custom(id: ShopPage.popupID, params: ["section": p.variant ?? "top"])
            if await DebugPopups.loopIfRequested(p, app: app, request: request, style: PopupStyle(dim: .none)) { return true }
            let r = await app.popups.present(Popup<PopupResult>(.custom(id: ShopPage.popupID, params: ["section": p.variant ?? "top"]),
                                                                style: PopupStyle(dim: .none), fallback: .close))
            Log.mark("popup", "shop page → \(r)")
            return true
        }
        ShellPrewarmItems.register(order: 140) { app, _ in [ShellPrewarmItem("shop", ShopView.prewarm(app))] }
    }

    /// The closable Shop (a full page: no dim, live-screen layout).
    private static func isShopPage(_ r: PopupRequest) -> Bool {
        if case .custom(let id, _) = r { return id == ShopPage.popupID }
        return false
    }
}
