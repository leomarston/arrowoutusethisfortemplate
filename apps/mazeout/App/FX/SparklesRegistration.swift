import SwiftUI
import UIKit
import PathCore

// Kit component `sparkles` (kit/fx/sparkles): `.sparkles(at)` on the FX host, built by the host inside one transaction that
// ends the effect when every animation is done (was the FX host's own case until the kit decoupling step).
// GameComponents.swift lists it.

@MainActor enum SparklesRegistration {
    static func register() {
        FXEffects.registerLayers { effect, fx, seed in
            guard case .sparkles(let at) = effect else { return nil }
            let tokens = fx.ui.tokens
            return { Sparkles.make(at: at, tokens: tokens, seed: seed) }
        }
    }
}
