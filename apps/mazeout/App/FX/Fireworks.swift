import UIKit
import PathCore

// SHELL S2 (SPEC-architecture §6.7, D13; SPEC-motion-audio §5 rows 12-13, §10 "firework rocket" / "firework burst"; CONSISTENCY
// W-4: six rockets). Core Animation fireworks, precomputed keyframes on the render server:
//   rocket  a white head (⌀6 with a soft glow) and a tapered white trail (60-110 pt), rising from y 862 at x ∈ {150, 240, 120, 270,
//           200, 170} to its burst point (x ± 40, y 190-330) with a decelerating cb(0.25, 0.6, 0.4, 1); launches at W + 1.60, 1.78,
//           1.95, 2.15, 2.40, 2.75, bursts at W + 2.24, 2.44, 2.64, 2.84, 3.07, 3.47 (`win.rockets` / `win.bursts`)
//   burst   48 sparks (40 % white, 15 % each #8D5FFF #4079FF #FF2FC6 #FFCE01), streaks 10-18 × 1.5 pt aligned with their velocity,
//           radial 260-420 pt/s with drag e^(−6.3t) and a 180 pt/s² droop, 0.70-0.90 s, fading over their last 0.4 s; a white flash
//           disc r 0 → 22 pt in 0.18 s; the whole screen flashes white 0 → 0.08 → 0 in 0.15 s (row 13)
// `-pc.freezeAt win@t` freezes the host layer, so every spark holds its place.

struct FireworkSpec {
    var sparks = 48
    var speedMin = 260.0
    var speedMax = 420.0
    var life = 0.8
    var colors: [UIColor] = [Skin.fxFireworksFireworkSpecColors0, Skin.fxFireworksFireworkSpecColors1, Skin.fxFireworksFireworkSpecColors2, Skin.fxFireworksFireworkSpecColors3, Skin.fxFireworksFireworkSpecColors4, Skin.fxFireworksFireworkSpecColors5].map { UIColor(rgb: $0) }
    var launchX: [Double] = [150, 240, 120, 270, 200, 170]
    var flash = 0.08

    init(_ t: Tokens) {
        sparks = Int(t.number("fx.firework.sparks", Double(sparks)))
        speedMin = t.number("fx.firework.speedMin", speedMin)
        speedMax = t.number("fx.firework.speedMax", speedMax)
        life = t.number("fx.firework.life", life)
        let c = t.file.strings("fx.firework.colors", []).compactMap { UIColor(hexString: $0) }
        if !c.isEmpty { colors = c }
        let xs = t.file.doubles("fx.firework.launchX", [])
        if xs.count >= 1 { launchX = xs }
        flash = t.number("win.burstFlash", flash)
    }
}

enum Fireworks {
    /// The rocket layers (head + trail) rising from `from` to `to` between host times `launch` and `burst`.
    static func rocket(from: CGPoint, to: CGPoint, launch: CFTimeInterval, burst: CFTimeInterval, trail: CGFloat) -> [CALayer] {
        let dur = max(0.05, burst - launch)
        let timing = CAMediaTimingFunction(controlPoints: 0.25, 0.6, 0.4, 1)
        let angle = atan2(to.y - from.y, to.x - from.x) + .pi / 2
        // trail: a vertical gradient strip (clear top → white bottom? the head leads, the trail follows below it)
        let tr = CAGradientLayer()
        tr.colors = [UIColor.white.withAlphaComponent(0.95).cgColor, UIColor.white.withAlphaComponent(0.0).cgColor]
        tr.startPoint = CGPoint(x: 0.5, y: 0)
        tr.endPoint = CGPoint(x: 0.5, y: 1)
        tr.bounds = CGRect(x: 0, y: 0, width: 3, height: trail)
        tr.anchorPoint = CGPoint(x: 0.5, y: 0)
        tr.cornerRadius = 1.5
        tr.position = from
        tr.opacity = 0
        tr.setAffineTransform(CGAffineTransform(rotationAngle: angle))
        let head = CALayer()
        head.bounds = CGRect(x: 0, y: 0, width: 6, height: 6)
        head.cornerRadius = 3
        head.backgroundColor = UIColor.white.cgColor
        head.shadowColor = UIColor.white.cgColor
        head.shadowRadius = 4
        head.shadowOpacity = 1
        head.shadowOffset = .zero
        head.shadowPath = CGPath(ellipseIn: head.bounds, transform: nil)   // FEEL: no offscreen shadow pass (§5.11 rule 11)
        head.position = from
        head.opacity = 0
        for l in [tr, head] {
            let move = CABasicAnimation(keyPath: "position")
            move.fromValue = NSValue(cgPoint: from)
            move.toValue = NSValue(cgPoint: to)
            move.timingFunction = timing
            let vis = CAKeyframeAnimation(keyPath: "opacity")
            vis.values = [1, 1]
            vis.keyTimes = [0, 1]
            let g = CAAnimationGroup()
            g.animations = [move, vis]
            g.duration = dur
            g.beginTime = launch
            g.fillMode = .forwards
            g.isRemovedOnCompletion = false
            l.add(g, forKey: "rise")
        }
        // the trail shrinks as the rocket slows
        let shrink = CABasicAnimation(keyPath: "bounds.size.height")
        shrink.fromValue = trail
        shrink.toValue = trail * 0.35
        shrink.beginTime = launch
        shrink.duration = dur
        shrink.timingFunction = timing
        shrink.fillMode = .forwards
        shrink.isRemovedOnCompletion = false
        tr.add(shrink, forKey: "shrink")
        // gone at the burst
        for l in [tr, head] {
            let off = CABasicAnimation(keyPath: "hidden")
            off.fromValue = true
            off.toValue = true
            off.beginTime = burst
            off.duration = 100
            off.fillMode = .forwards
            off.isRemovedOnCompletion = false
            l.add(off, forKey: "gone")
        }
        return [tr, head]
    }

    /// The burst at `at`, host time `begin`: sparks + a flash disc.
    static func burst(at p: CGPoint, begin: CFTimeInterval, spec: FireworkSpec, rng: inout PathRandom) -> [CALayer] {
        var out: [CALayer] = []
        let drag = 6.3, droop = 180.0
        for i in 0..<spec.sparks {
            let a = Double(i) / Double(spec.sparks) * 2 * .pi + rng.unit() * 0.12
            let v0 = rng.double(in: spec.speedMin...spec.speedMax)
            let life = spec.life + (rng.unit() - 0.5) * 0.2
            let color = rng.unit() < 0.4 ? UIColor.white : spec.colors[2 + rng.below(max(1, spec.colors.count - 2))]
            let s = CALayer()
            let len = CGFloat(rng.double(in: 10...18))
            s.bounds = CGRect(x: 0, y: 0, width: len, height: 1.5)
            s.cornerRadius = 0.75
            s.backgroundColor = color.cgColor
            s.position = p
            s.opacity = 0
            s.setAffineTransform(CGAffineTransform(rotationAngle: CGFloat(a)))
            var pts: [NSValue] = []
            var keys: [NSNumber] = []
            let n = 10
            for k in 0...n {
                let t = life * Double(k) / Double(n)
                let r = v0 * (1 - exp(-drag * t)) / drag
                pts.append(NSValue(cgPoint: CGPoint(x: p.x + CGFloat(cos(a) * r), y: p.y + CGFloat(sin(a) * r + 0.5 * droop * t * t))))
                keys.append(NSNumber(value: Double(k) / Double(n)))
            }
            let move = CAKeyframeAnimation(keyPath: "position")
            move.values = pts
            move.keyTimes = keys
            move.calculationMode = .cubic
            let fade = CAKeyframeAnimation(keyPath: "opacity")
            let fadeFrom = max(0, (life - 0.4) / life)
            fade.values = [1, 1, 0]
            fade.keyTimes = [0, NSNumber(value: fadeFrom), 1]
            let g = CAAnimationGroup()
            g.animations = [move, fade]
            g.duration = life
            g.beginTime = begin
            g.fillMode = .forwards
            g.isRemovedOnCompletion = false
            s.add(g, forKey: "spark")
            out.append(s)
        }
        // the flash disc
        let disc = CALayer()
        disc.bounds = CGRect(x: 0, y: 0, width: 44, height: 44)
        disc.cornerRadius = 22
        disc.backgroundColor = UIColor.white.cgColor
        disc.position = p
        disc.opacity = 0
        let grow = CABasicAnimation(keyPath: "transform.scale")
        grow.fromValue = 0.05
        grow.toValue = 1
        let fade = CAKeyframeAnimation(keyPath: "opacity")
        fade.values = [0.95, 0.7, 0]
        fade.keyTimes = [0, 0.5, 1]
        let g = CAAnimationGroup()
        g.animations = [grow, fade]
        g.duration = 0.18
        g.beginTime = begin
        g.fillMode = .forwards
        g.isRemovedOnCompletion = false
        disc.add(g, forKey: "flash")
        out.append(disc)
        return out
    }

    /// The full-screen white flash of a burst (0 → `peak` → 0 in 0.15 s).
    static func screenFlash(bounds: CGRect, begin: CFTimeInterval, peak: Double) -> CALayer {
        let l = CALayer()
        l.frame = bounds
        l.backgroundColor = UIColor.white.cgColor
        l.opacity = 0
        let a = CAKeyframeAnimation(keyPath: "opacity")
        a.values = [0, peak, 0]
        a.keyTimes = [0, 0.4, 1]
        a.duration = 0.15
        a.beginTime = begin
        a.fillMode = .forwards
        a.isRemovedOnCompletion = false
        l.add(a, forKey: "flash")
        return l
    }
}
