import SwiftUI
import PathCore

// Kit component `toasts` (kit/meta/toasts): the toast plate over everything (RootView's top layer; named there until the kit
// decoupling step). The presenter itself is AppModel's `toasts` (ShellEntry.makeToasts, Toast.swift). GameComponents.swift
// lists it.

@MainActor enum ToastsRegistration {
    static func register() {
        ShellScreens.registerToastLayer { app, inLevel in
            guard let center = app.toasts as? ToastCenter else { return nil }
            return AnyView(ToastLayer(center: center, tokens: app.tuning.ui.tokens, inLevel: inLevel))
        }
    }
}
