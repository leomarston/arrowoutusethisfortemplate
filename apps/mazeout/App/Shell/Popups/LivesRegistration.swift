import SwiftUI
import PathCore

// Kit component `lives` (kit/economy/lives): the More Lives popup in the popup host, its `-pc.popup noLives` id and its Loading
// warm-up (S3Popups in S3Hooks.swift until the kit decoupling step). GameComponents.swift lists it.

@MainActor enum LivesRegistration {
    static func register() {
        PopupPanels.register(PopupPanelProvider("lives", handles: { r in
            if case .noLives = r { return true }
            return false
        }, make: { _, answer in AnyView(NoLivesPopup(answer: answer)) }))
        DebugPopups.register { p, app in
            guard p.id == PopupID.noLives.rawValue else { return false }
            if await DebugPopups.loopIfRequested(p, app: app, request: .noLives, style: .standard) { return true }
            let r = await app.popups.present(Popup<PopupResult>.noLives)
            Log.mark("popup", "noLives → \(r)")
            return true
        }
        ShellPrewarmItems.register(order: 100) { _, host in
            [ShellPrewarmItem("noLives", ReferenceCanvas { NoLivesPopup(answer: PopupAnswer(id: -31, host: host)) })]
        }
    }
}
