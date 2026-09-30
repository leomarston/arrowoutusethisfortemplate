import SwiftUI
import PathCore

// Kit component `quit-level` (kit/popups/quit-level): the "Quit Level?" band in the popup host and its Loading warm-up (named
// by PopupHost's `PopupContent` and RootView's `ShellPrewarm` until the kit decoupling step). GameComponents.swift lists it.

@MainActor enum QuitLevelRegistration {
    static func register() {
        PopupPanels.register(PopupPanelProvider("quit-level", handles: { r in
            if case .quitLevel = r { return true }
            return false
        }, make: { _, answer in AnyView(QuitLevelPopup(answer: answer)) }))
        ShellPrewarmItems.register(order: 310) { _, host in
            [ShellPrewarmItem("quitLevel", ReferenceCanvas { QuitLevelPopup(answer: PopupAnswer(id: -3, host: host)) })]
        }
    }
}
