import UIKit

// B1 (SPEC-architecture §5.8; research/motion.md §3.1 + research/motion-tools/out/ripple_{L33,L35,P02A}.txt, 3 phone clips);
// FEEL (build/phone2/latency.md F2, the owner's "click feeling"). The tap ripple is the original's crisp FLAT grey disc, not a
// soft glow: on the release frame a mid-grey disc (luminance 180 on white) with a hard anti-aliased edge sits at the touch
// point, out to r 11 pt; the disc grows to 22.5 pt while it fades to 250 and is gone at ≈ 0.25 s. The 60 Hz clips show it as
// two flat tones — a core (180 → 250, r ≈ 8 pt) inside a lighter disc whose edge grows 11 → 22.5 pt (232 → 250): on the
// first frame the 180 core fills the disc to 9.5 pt (the original's first frame changes 215–347 px in a 14 pt test disc, a
// flat r 9.5 disc changes 283; B1's soft gradients changed only 115–135, F2), then settles to r 8 as the outer disc grows.
// Both parts are plain circle layers (cornerRadius: a crisp edge at every scale, no gradient, no offscreen pass) of black at
// the alpha that gives that luminance on white. A pool of `ripple.pool` (6) pre-built pairs: nothing is allocated on the
// tap path (§5.11 rule 12).

@MainActor final class RipplePool {
    private struct Item {
        let root: CALayer
        let ring: CALayer
        let core: CALayer
    }

    private var items: [Item] = []
    private var next = 0
    private let config: BoardConfig
    private let coreMax: CGFloat

    init(config: BoardConfig, parent: CALayer, scale: CGFloat) {
        self.config = config
        let rMax = CGFloat(config.rippleRadius.max() ?? 22.5)
        coreMax = CGFloat(max(config.rippleCoreFirstRadius, config.rippleCoreRadius))
        for _ in 0..<config.ripplePool {
            let root = CALayer()
            root.bounds = CGRect(x: -rMax, y: -rMax, width: 2 * rMax, height: 2 * rMax)
            root.isHidden = true
            let ring = Self.disc(radius: rMax, scale: scale)
            let core = Self.disc(radius: coreMax, scale: scale)
            ring.position = .zero
            core.position = .zero
            ring.opacity = 0
            core.opacity = 0
            root.addSublayer(ring)
            root.addSublayer(core)
            parent.addSublayer(root)
            items.append(Item(root: root, ring: ring, core: core))
        }
    }

    /// A flat black circle (its opacity sets the luminance on white); the edge is the render server's anti-aliased corner.
    private static func disc(radius r: CGFloat, scale: CGFloat) -> CALayer {
        let l = CALayer()
        l.bounds = CGRect(x: 0, y: 0, width: 2 * r, height: 2 * r)
        l.cornerRadius = r
        l.backgroundColor = UIColor.black.cgColor
        l.contentsScale = scale
        l.allowsEdgeAntialiasing = true
        return l
    }

    /// The ripple's keyframes (times, ring scale / alpha, core scale / alpha) for the pool's layer sizes.
    struct Track {
        var times: [Double]
        var duration: Double
        var ringScale: [Double]
        var ringAlpha: [Double]
        var coreScale: [Double]
        var coreAlpha: [Double]
    }

    static func track(_ c: BoardConfig, ringMax: Double, coreMax: Double) -> Track? {
        let times = c.rippleTimes
        let n = min(times.count, c.rippleRadius.count, c.rippleCoreLum.count, c.rippleRingLum.count)
        guard n >= 2 else { return nil }
        let dur = times[n - 1] + 0.017                              // one more frame at the last value, then gone
        let ringA = (0..<n).map { BoardConfig.alphaForLuminance(c.rippleRingLum[$0]) }
        // the centre shows core over ring: 1 − (1 − a_core)(1 − a_ring) = a(centre lum)
        let coreA = (0..<n).map { i -> Double in
            let ac = BoardConfig.alphaForLuminance(c.rippleCoreLum[i])
            return max(0, 1 - (1 - ac) / max(0.001, 1 - ringA[i]))
        }
        let ringS = (0..<n).map { c.rippleRadius[$0] / max(ringMax, 0.1) }
        // the core: the first frame's flat disc, then the settled core (never wider than the outer disc)
        let coreS = (0..<n).map { i -> Double in
            let r = i == 0 ? c.rippleCoreFirstRadius : c.rippleCoreRadius
            return min(r, c.rippleRadius[i]) / max(coreMax, 0.1)
        }
        let t = Array(times.prefix(n)) + [dur]
        return Track(times: t, duration: dur, ringScale: ringS + [ringS[n - 1]], ringAlpha: ringA + [0],
                     coreScale: coreS + [coreS[n - 1]], coreAlpha: coreA + [0])
    }

    /// Plays one ripple at `point` (parent coordinates). Call inside the tap's no-actions transaction. `begin` is the
    /// parent layer's local time of the release.
    func play(at point: CGPoint, begin: CFTimeInterval) {
        guard !items.isEmpty else { return }
        let it = items[next]
        next = (next + 1) % items.count
        let rMax = Double(it.ring.bounds.width / 2)
        guard let tr = Self.track(config, ringMax: rMax, coreMax: Double(coreMax)) else { return }
        let num: ([Double]) -> [NSNumber] = { $0.map { NSNumber(value: $0) } }
        it.root.removeAllAnimations()
        it.ring.removeAllAnimations()
        it.core.removeAllAnimations()
        it.root.position = point
        it.root.isHidden = false
        it.ring.add(Anim.keyframes("opacity", num(tr.ringAlpha), times: tr.times, duration: tr.duration, begin: begin), forKey: "o")
        it.ring.add(Anim.keyframes("transform.scale", num(tr.ringScale), times: tr.times, duration: tr.duration, begin: begin),
                    forKey: "s")
        it.core.add(Anim.keyframes("opacity", num(tr.coreAlpha), times: tr.times, duration: tr.duration, begin: begin), forKey: "o")
        it.core.add(Anim.keyframes("transform.scale", num(tr.coreScale), times: tr.times, duration: tr.duration, begin: begin),
                    forKey: "s")
    }
}
