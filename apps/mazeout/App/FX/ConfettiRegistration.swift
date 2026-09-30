import SwiftUI
import UIKit
import PathCore

// Kit component `confetti` (kit/fx/confetti): `.confetti(rect)` on the FX host, a burst of Core Animation pieces removed after
// 5 s of game time. Moved as it was from S2FX (HUD/S2Hooks.swift) in the kit decoupling step; GameComponents.swift lists it.

@MainActor enum ConfettiRegistration {
    static func register() {
        FXEffects.register(LooseLayerFX(lifetime: 5) { effect, handle, fx in
            guard case .confetti(let rect) = effect else { return nil }
            let root = CALayer()
            let host = fx.hostView.layer
            root.frame = host.bounds
            let t0 = host.convertTime(CACurrentMediaTime(), from: nil)
            var rng = PathRandom(seed: 0xF1 &+ UInt64(handle.id))
            let area = rect.isEmpty ? host.bounds : rect
            CATransaction.begin(); CATransaction.setDisableActions(true)
            let spec = ConfettiSpec(fx.ui.tokens)
            for _ in 0..<spec.burst { root.addSublayer(Confetti.burstPiece(&rng, spec: spec, bounds: area, begin: t0)) }
            host.addSublayer(root)
            CATransaction.commit()
            return root
        })
    }
}
