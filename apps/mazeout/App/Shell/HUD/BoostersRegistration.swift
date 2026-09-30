import SwiftUI
import PathCore

// Kit component `boosters` (kit/economy/boosters): the booster buy popup in the popup host, its `-pc.popup boosterBuy[:id]`
// id and Loading warm-up (S3Popups in S3Hooks.swift until the kit decoupling step), and the Time Freeze on the FX host
// (`FreezeFX`, was S2FX in HUD/S2Hooks.swift). GameComponents.swift lists it. The HUD corners are placed by the HUD and the
// director is installed by the game loop (GameDirectors+G2.swift).

@MainActor enum BoostersRegistration {
    static func register() {
        FXEffects.register(FreezeFX.shared)
        PopupPanels.register(PopupPanelProvider("boosters", handles: { r in
            if case .boosterBuy = r { return true }
            return false
        }, make: { r, answer in
            guard case .boosterBuy(let b) = r else { return AnyView(EmptyView()) }
            return AnyView(BoosterBuyPopup(booster: b, answer: answer))
        }))
        DebugPopups.register { p, app in
            guard p.id == PopupID.boosterBuy.rawValue else { return false }
            let request = PopupRequest.boosterBuy(BoosterID(p.variant ?? "freeze"))
            if await DebugPopups.loopIfRequested(p, app: app, request: request, style: .standard) { return true }
            let r = await app.popups.present(Popup<PopupResult>.boosterBuy(BoosterID(p.variant ?? "freeze")))
            Log.mark("popup", "boosterBuy → \(r)")
            return true
        }
        ShellPrewarmItems.register(order: 110) { _, host in
            [ShellPrewarmItem("boosterBuy", ReferenceCanvas { BoosterBuyPopup(booster: .freeze, answer: PopupAnswer(id: -32, host: host)) })]
        }
    }
}
