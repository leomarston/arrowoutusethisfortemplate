import SwiftUI
import PathCore

// Kit component `loading` (kit/screens/loading): the Loading screen for the router's `.loading` layer and its art's lifetime
// (decoded off the main thread by the router's first act, released once the first screen is up). Named by RootView.swift and
// Router.swift until the kit decoupling step; GameComponents.swift lists it.

@MainActor enum LoadingRegistration {
    static func register() {
        ShellScreens.registerLoading(LoadingScreenHooks(makeView: { AnyView(LoadingScreen()) },
                                                        startArt: { LoadingArt.shared.start() },
                                                        releaseArt: { LoadingArt.shared.release() }))
    }
}
