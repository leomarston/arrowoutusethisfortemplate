import UIKit
import PathCore

// SHELL S1 (SPEC-architecture §3.2 "FX/Sparkles"; used by the payout coin pill (S3), the unlock icons (S2), rewards). A burst of
// four-point twinkle stars around a point: each pops (scale 0 → 1 → 0) with a slight spin and drift, staggered, then the effect
// ends. Vector CAShapeLayers (the `sparkleTwinkle` raster is still `todo` in the manifest); count / radius / duration / size /
// colours are data (ui.json `fx.sparkles.*`, PENDING-motion-audio). Deterministic per seed (PathRandom), so captures repeat.

enum Sparkles {
    static func make(at p: CGPoint, tokens t: Tokens, seed: UInt64) -> [CALayer] {
        let count = max(1, Int(t.number("fx.sparkles.count", 7)))
        let radius = CGFloat(t.number("fx.sparkles.radius", 22))
        let duration = t.number("fx.sparkles.duration", 0.7)
        let size = CGFloat(t.number("fx.sparkles.size", 9))
        let colors = t.file.strings("fx.sparkles.colors", [Skin.fxSparklesFxSparklesColors0Hex, Skin.fxSparklesFxSparklesColors1Hex, Skin.fxSparklesFxSparklesColors2Hex])
            .compactMap { UIColor(hexString: $0) }
        var rng = PathRandom(seed: seed &+ 0x5EED)
        var out: [CALayer] = []
        let now = CACurrentMediaTime()
        for i in 0..<count {
            let a = Double(i) / Double(count) * 2 * .pi + rng.unit() * 0.6
            let r = radius * CGFloat(0.35 + 0.65 * rng.unit())
            let s = size * CGFloat(0.6 + 0.6 * rng.unit())
            let star = CAShapeLayer()
            star.path = starPath(size: s)
            star.bounds = CGRect(x: -s / 2, y: -s / 2, width: s, height: s)
            star.position = CGPoint(x: p.x + CGFloat(cos(a)) * r, y: p.y + CGFloat(sin(a)) * r)
            star.fillColor = (colors.isEmpty ? UIColor.white : colors[i % colors.count]).cgColor
            star.opacity = 0
            let delay = Double(i) / Double(count) * duration * 0.35
            let life = duration - delay
            let pop = CAKeyframeAnimation(keyPath: "transform.scale")
            pop.values = [0, 1.15, 0.9, 0]
            pop.keyTimes = [0, 0.3, 0.6, 1]
            let spin = CABasicAnimation(keyPath: "transform.rotation.z")
            spin.fromValue = 0; spin.toValue = (rng.unit() < 0.5 ? -1 : 1) * Double.pi / 3
            let fade = CAKeyframeAnimation(keyPath: "opacity")
            fade.values = [1, 1, 0]
            fade.keyTimes = [0, 0.7, 1]
            let drift = CABasicAnimation(keyPath: "position")
            drift.fromValue = NSValue(cgPoint: star.position)
            drift.toValue = NSValue(cgPoint: CGPoint(x: star.position.x + CGFloat(cos(a)) * 6, y: star.position.y + CGFloat(sin(a)) * 6 - 4))
            let group = CAAnimationGroup()
            group.animations = [pop, spin, fade, drift]
            group.duration = life
            group.beginTime = now + delay
            group.fillMode = .both
            group.isRemovedOnCompletion = false
            star.add(group, forKey: "twinkle")
            out.append(star)
        }
        return out
    }

    /// A four-point twinkle star centred on 0.
    static func starPath(size s: CGFloat) -> CGPath {
        let p = CGMutablePath()
        let R = s / 2, r = s * 0.13
        for k in 0..<8 {
            let a = CGFloat(k) * .pi / 4 - .pi / 2
            let rr = k % 2 == 0 ? R : r
            let pt = CGPoint(x: cos(a) * rr, y: sin(a) * rr)
            if k == 0 { p.move(to: pt) } else { p.addLine(to: pt) }
        }
        p.closeSubpath()
        return p
    }
}

extension UIColor {
    convenience init?(hexString: String) {
        var s = hexString.trimmingCharacters(in: .whitespaces)
        if s.hasPrefix("#") { s.removeFirst() }
        guard s.count == 6, let v = UInt32(s, radix: 16) else { return nil }
        self.init(red: CGFloat((v >> 16) & 0xFF) / 255, green: CGFloat((v >> 8) & 0xFF) / 255, blue: CGFloat(v & 0xFF) / 255, alpha: 1)
    }
}
