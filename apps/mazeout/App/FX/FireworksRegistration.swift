import SwiftUI
import UIKit
import PathCore

// Kit component `fireworks` (kit/fx/fireworks): `.fireworks(rect)` on the FX host, two rockets and their bursts as Core
// Animation layers removed after 5 s of game time. Moved as it was from S2FX (HUD/S2Hooks.swift) in the kit decoupling step;
// GameComponents.swift lists it.

@MainActor enum FireworksRegistration {
    static func register() {
        FXEffects.register(LooseLayerFX(lifetime: 5) { effect, handle, fx in
            guard case .fireworks(let rect) = effect else { return nil }
            let root = CALayer()
            let host = fx.hostView.layer
            root.frame = host.bounds
            let t0 = host.convertTime(CACurrentMediaTime(), from: nil)
            var rng = PathRandom(seed: 0xF1 &+ UInt64(handle.id))
            let area = rect.isEmpty ? host.bounds : rect
            CATransaction.begin(); CATransaction.setDisableActions(true)
            let spec = FireworkSpec(fx.ui.tokens)
            for i in 0..<2 {
                let from = CGPoint(x: area.minX + area.width * (0.35 + 0.3 * CGFloat(i)), y: area.maxY)
                let to = CGPoint(x: from.x + CGFloat((rng.unit() - 0.5) * 60), y: area.minY + area.height * 0.3)
                for l in Fireworks.rocket(from: from, to: to, launch: t0 + 0.2 * Double(i), burst: t0 + 0.2 * Double(i) + 0.65, trail: 200) {
                    root.addSublayer(l)
                }
                for l in Fireworks.burst(at: to, begin: t0 + 0.2 * Double(i) + 0.65, spec: spec, rng: &rng) { root.addSublayer(l) }
            }
            host.addSublayer(root)
            CATransaction.commit()
            return root
        })
    }
}
