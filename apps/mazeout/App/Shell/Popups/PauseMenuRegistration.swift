import SwiftUI
import PathCore

// Kit component `pause-menu` (kit/popups/pause-menu): the Pause popup in the popup host and its Loading warm-ups (the popup;
// its toggle's OFF track). The panel was named by PopupHost's `PopupContent`, the warm-ups by RootView's `ShellPrewarm` and
// S2Popups.prewarm, until the kit decoupling step; GameComponents.swift lists it. `-pc.popup pause` stays the router's (it
// presents the request, not the panel).

@MainActor enum PauseMenuRegistration {
    static func register() {
        PopupPanels.register(PopupPanelProvider("pause-menu", handles: { r in
            if case .pause = r { return true }
            return false
        }, make: { _, answer in AnyView(PausePopup(answer: answer)) }))
        ShellPrewarmItems.register(order: 320) { _, host in
            [ShellPrewarmItem("pause", ReferenceCanvas { PausePopup(answer: PopupAnswer(id: -1, host: host)) })]
        }
        // A2: the Pause toggle's OFF track (the track and the knob are separate rasters now; ON is made with the Pause popup)
        ShellPrewarmItems.register(order: 440) { app, _ in
            let tk = app.tuning.ui.tokens
            return [ShellPrewarmItem("toggle.off", ReferenceCanvas {
                PopupToggle(id: "prewarm.toggle", isOn: false, t: tk) {}.placed(tk.frame("pause.toggleSound", CGRect(206.5, 328.6, 116.1, 37.4)))
            })]
        }
    }
}
