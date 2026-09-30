import UIKit
import PathCore

// SHELL S2 (SPEC-architecture §6.7, D13; SPEC-motion-audio §5 rows 11, 19, §10 "confetti"). Core Animation confetti: every piece
// is a small rounded quad whose whole flight is precomputed into keyframes (position with a sway, a tumbling flip on scale-Y, an
// in-plane spin) and handed to the render server, so the main thread does nothing while it falls.
//   burst  `fx.confetti.burst` 420 pieces from the bottom (y 862, x uniform 0 … W) within ±12° of vertical. FIX-2 A (L27, MEASURED
//          on v552's S1-L50 / S3-L089 win clips, build/p/FIX2/A/confetti): a cannon, not a ballistic arc — each piece rises a
//          height R (`riseMin` … `riseMax`) with drag, R·(1 − e^(−t/τ)), τ `riseTau`, then flutters down at a terminal 140-220 pt/s
//          with a ±20 pt sway (period 1.2-2 s). Was 900-1500 pt/s under g 900: a low band at W+1.7-1.9 that later hung ABOVE the
//          screen for over a second.
//          FIX-2 A-R (review-A): fitted on the DRAWN pixels (the simulator's frozen frames measured like v552's, lane A's
//          conf_measure: saturated pixels outside the HUD and the logo box — how many, the share above y 426), no longer on
//          modelled piece positions: R uniform 80-780 pt, τ 0.135 s, 420 pieces (was 200-800 skewed low, 280 pieces: every piece
//          rose ≥ 200 pt, so v552's densest part, the bottom 150 pt, stayed empty — 5069 px at W+1.90 vs ≈ 8100, share above
//          0.33 vs 0.20). Now W+1.90 / 1.95 / 2.00 / 2.10 / 2.20: share 0.20 / 0.24 / 0.34 / 0.38 / 0.28 (v552 0.20 / 0.29 /
//          0.33 / 0.35 / 0.27), pixels 0.88-1.25× v552's (build/p/FIX2/A-R/conf). Left: at W+1.72 (the burst's first 65 ms) the
//          cloud is 2.3× v552's pixels — every piece launches at once.
//   rain   `fx.confetti.rainPerS` 45 pieces/s from y −10 (x uniform), falling 140-220 pt/s with the same sway, until the panel
//   look   7 colours, equal weights except blue ×1.4 (#1F77F3 #EB4FB0 #6A11EF #D30A20 #FFB807 #F8F2DA #65DD2B), 5-11 pt (median 6.5),
//          aspect 1:1 … 1:1.6, corner 1.5 pt; flip 2-5 rev/s; spin ±180°/s
// Deterministic per seed (PathRandom), so a `-pc.freezeAt win@t` capture repeats. Times are the FX host layer's local time
// (the MotionClock's slow motion and freezes act on it).

struct ConfettiSpec {
    var burst = 140
    var rainPerS = 45.0
    var colors: [UIColor] = [Skin.fxConfettiConfettiSpecColors0, Skin.fxConfettiConfettiSpecColors1, Skin.fxConfettiConfettiSpecColors2, Skin.fxConfettiConfettiSpecColors3, Skin.fxConfettiConfettiSpecColors4, Skin.fxConfettiConfettiSpecColors5, Skin.fxConfettiConfettiSpecColors6].map { UIColor(rgb: $0) }
    var sizeMin = 5.0
    var sizeMax = 11.0
    var flipMin = 2.0
    var flipMax = 5.0
    var gravity = 900.0
    var fallMin = 140.0
    var fallMax = 220.0
    var sway = 20.0
    /// FIX-2 A (L27): the burst's rise with drag (the fit to v552, see the header).
    var riseMin = 80.0
    var riseMax = 780.0
    var risePower = 1.0
    var riseTau = 0.135

    init() {}

    init(_ t: Tokens) {
        burst = Int(t.number("fx.confetti.burst", Double(burst)))
        rainPerS = t.number("fx.confetti.rainPerS", rainPerS)
        let c = t.file.strings("fx.confetti.colors", []).compactMap { UIColor(hexString: $0) }
        if !c.isEmpty { colors = c }
        sizeMin = t.number("fx.confetti.sizeMin", sizeMin)
        sizeMax = t.number("fx.confetti.sizeMax", sizeMax)
        flipMin = t.number("fx.confetti.flipMin", flipMin)
        flipMax = t.number("fx.confetti.flipMax", flipMax)
        riseMin = t.number("fx.confetti.riseMin", riseMin)
        riseMax = max(riseMin, t.number("fx.confetti.riseMax", riseMax))
        risePower = t.number("fx.confetti.risePower", risePower)
        riseTau = max(0.01, t.number("fx.confetti.riseTau", riseTau))
    }
}

enum Confetti {
    /// One piece launched from the bottom at host time `begin`; `bounds` = the screen in pt.
    static func burstPiece(_ rng: inout PathRandom, spec: ConfettiSpec, bounds: CGRect, begin: CFTimeInterval) -> CALayer {
        let (points, times) = burstPath(&rng, spec: spec, bounds: bounds)
        return piece(&rng, spec: spec, points: points, times: times, begin: begin)
    }

    /// FIX-2 A (L27): one burst piece's path (points at times after its launch): the drag rise, then the flutter down.
    static func burstPath(_ rng: inout PathRandom, spec: ConfettiSpec, bounds: CGRect) -> ([CGPoint], [Double]) {
        let x0 = bounds.minX + CGFloat(rng.unit()) * bounds.width
        let rise = spec.riseMin + (spec.riseMax - spec.riseMin) * pow(rng.unit(), spec.risePower)
        let angle = (rng.unit() * 2 - 1) * 12 * Double.pi / 180
        let tau = spec.riseTau
        let tRise = 3 * tau                                  // 95 % of the rise; the flutter takes over from there
        var times: [Double] = []
        var points: [CGPoint] = []
        // the rise: R·(1 − e^(−t/τ)) along the launch angle, 12 samples (dense at the start, where it is fast)
        for i in 0...12 {
            let t = tRise * pow(Double(i) / 12, 1.6)
            let k = 1 - exp(-t / tau)
            points.append(CGPoint(x: x0 + CGFloat(rise * k * tan(angle)), y: bounds.maxY + 10 - CGFloat(rise * k)))
            times.append(t)
        }
        // the flutter down at a terminal speed with a sway
        let apex = points.last ?? CGPoint(x: x0, y: 0)
        let fall = rng.double(in: spec.fallMin...spec.fallMax)
        let period = rng.double(in: 1.2...2.0), phase = rng.unit() * 2 * .pi
        let fallTime = Double(bounds.maxY + 30 - apex.y) / fall
        let steps = max(4, Int(fallTime / 0.2))
        for i in 1...steps {
            let t = fallTime * Double(i) / Double(steps)
            let dx = CGFloat(spec.sway * sin(2 * .pi * t / period + phase) - spec.sway * sin(phase))
            points.append(CGPoint(x: apex.x + dx, y: apex.y + CGFloat(fall * t)))
            times.append(tRise + t)
        }
        return (points, times)
    }

    /// One rain piece entering at the top at host time `begin`.
    static func rainPiece(_ rng: inout PathRandom, spec: ConfettiSpec, bounds: CGRect, begin: CFTimeInterval) -> CALayer {
        let x0 = bounds.minX + CGFloat(rng.unit()) * bounds.width
        let fall = rng.double(in: spec.fallMin...spec.fallMax)
        let period = rng.double(in: 1.2...2.0), phase = rng.unit() * 2 * .pi
        let total = Double(bounds.height + 40) / fall
        let steps = max(4, Int(total / 0.2))
        var times: [Double] = [], points: [CGPoint] = []
        for i in 0...steps {
            let t = total * Double(i) / Double(steps)
            let dx = CGFloat(spec.sway * sin(2 * .pi * t / period + phase) - spec.sway * sin(phase))
            points.append(CGPoint(x: x0 + dx, y: bounds.minY - 10 + CGFloat(fall * t)))
            times.append(t)
        }
        return piece(&rng, spec: spec, points: points, times: times, begin: begin)
    }

    private static func piece(_ rng: inout PathRandom, spec: ConfettiSpec, points: [CGPoint], times: [Double],
                              begin: CFTimeInterval) -> CALayer {
        let l = CALayer()
        // colour: equal weights, blue ×1.4
        let weights = spec.colors.enumerated().map { $0.offset == 0 ? 1.4 : 1.0 }
        var pick = rng.unit() * weights.reduce(0, +), ci = 0
        for (i, w) in weights.enumerated() { if pick < w { ci = i; break }; pick -= w; ci = i }
        let side = CGFloat(spec.sizeMin + (spec.sizeMax - spec.sizeMin) * pow(rng.unit(), 1.6))
        let aspect = CGFloat(rng.double(in: 1.0...1.6))
        l.bounds = CGRect(x: 0, y: 0, width: side, height: side * aspect)
        l.cornerRadius = 1.5
        l.backgroundColor = spec.colors[ci].cgColor
        l.position = points[0]
        l.opacity = 0
        let total = times.last ?? 1
        let pos = CAKeyframeAnimation(keyPath: "position")
        pos.values = points.map { NSValue(cgPoint: $0) }
        pos.keyTimes = times.map { NSNumber(value: $0 / total) }
        pos.calculationMode = .cubic
        let flipRate = rng.double(in: spec.flipMin...spec.flipMax)
        let flip = CAKeyframeAnimation(keyPath: "transform.scale.y")
        flip.values = [1, 0.15, -1, -0.15, 1]
        flip.keyTimes = [0, 0.25, 0.5, 0.75, 1]
        flip.duration = 1 / flipRate
        flip.repeatCount = .greatestFiniteMagnitude
        flip.timeOffset = rng.unit() / flipRate
        let spin = CABasicAnimation(keyPath: "transform.rotation.z")
        let dir = rng.sign()
        spin.fromValue = rng.unit() * 2 * .pi
        spin.toValue = (spin.fromValue as? Double ?? 0) + dir * .pi * total
        spin.duration = total
        let show = CAKeyframeAnimation(keyPath: "opacity")
        show.values = [1, 1]
        show.keyTimes = [0, 1]
        let group = CAAnimationGroup()
        group.animations = [pos, flip, spin, show]
        group.duration = total
        group.beginTime = begin
        group.fillMode = .forwards
        group.isRemovedOnCompletion = false
        l.add(group, forKey: "fall")
        return l
    }
}

extension UIColor {
    convenience init(rgb: UInt32, alpha: CGFloat = 1) {
        self.init(red: CGFloat((rgb >> 16) & 0xFF) / 255, green: CGFloat((rgb >> 8) & 0xFF) / 255, blue: CGFloat(rgb & 0xFF) / 255, alpha: alpha)
    }
}
