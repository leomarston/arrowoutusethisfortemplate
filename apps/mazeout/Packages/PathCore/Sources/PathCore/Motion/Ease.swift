import Foundation
import CoreGraphics   // CGPoint helpers; Foundation alone lacks the CG overlay on macOS

// SPEC-architecture §4.16. COPIED in WP0 from apps/matchfactory Packages/MFCore/Sources/MFCore/Motion/Ease.swift
// (05424db, identical in the working tree): Ease, EaseToken, SpringCurve, KeyTrack and the helpers, as-is. The only
// change: MF's two SIMD3 helpers (mix3, bezier2: 3-D, RealityKit-specific) and `import simd` were dropped (PathCore is
// Foundation + CoreGraphics only, D1). The token table comments cite MF's motion spec; SPEC-motion-audio replaces the
// values in C1 if ours differ. C1 OWNS the file from now on.
// C1 changes: KeyTrack stores `endSlopesZero` (so a track round-trips as data, Tunable.swift); the Double `Easing` family added.

/// Easing functions (proven in the MF spike). t in 0...1.
public enum Ease {
    public static func outCubic(_ t: Float) -> Float { let u = 1 - t; return 1 - u * u * u }
    public static func inCubic(_ t: Float) -> Float { t * t * t }
    public static func inOutCubic(_ t: Float) -> Float {
        t < 0.5 ? 4 * t * t * t : 1 - pow(-2 * t + 2, 3) / 2
    }
    public static func outQuad(_ t: Float) -> Float { 1 - (1 - t) * (1 - t) }
    public static func inQuad(_ t: Float) -> Float { t * t }
    public static func outBack(_ t: Float, _ s: Float = 1.70158) -> Float {
        let u = t - 1; return 1 + (s + 1) * u * u * u + s * u * u
    }
    public static func outSine(_ t: Float) -> Float { sin(t * .pi / 2) }
}

/// Analytic Double easings (C1; the Float `Ease` functions above are MF's and stay as they are). t is clamped to 0...1.
public enum Easing {
    public static func outQuad(_ t: Double) -> Double { let u = 1 - clamp01(t); return 1 - u * u }
    public static func inQuad(_ t: Double) -> Double { let u = clamp01(t); return u * u }
    public static func outCubic(_ t: Double) -> Double { let u = 1 - clamp01(t); return 1 - u * u * u }
    public static func inOutQuad(_ t: Double) -> Double {
        let u = clamp01(t); return u < 0.5 ? 2 * u * u : 1 - 2 * (1 - u) * (1 - u)
    }
    public static func inOutSine(_ t: Double) -> Double { let u = clamp01(t); return 0.5 - 0.5 * cos(u * .pi) }
    /// Robert Penner's easeOutBack with overshoot `s` (1.70158 = the classic 10 % overshoot; the HUD drop measures 3.42).
    public static func outBack(_ t: Double, s: Double = 1.70158) -> Double {
        let x = clamp01(t) - 1; return 1 + (s + 1) * x * x * x + s * x * x
    }
    /// 1 − (1 − t)^n: the ease-out power family (n = 2 outQuad, 3 outCubic).
    public static func power(_ t: Double, _ n: Double) -> Double { 1 - pow(1 - clamp01(t), n) }
}

// MARK: - SPEC-motion-audio §0.3 easing tokens (C1)

/// The named easing curves of SPEC-motion-audio §0.3. Each is a CSS / CoreAnimation cubic Bézier, so a SwiftUI
/// `.timingCurve(x1, y1, x2, y2)` and `Curves` evaluate exactly the same curve ("Use these names in code").
public enum EaseToken: String, CaseIterable, Sendable, Codable {
    case linear, outQuad, inQuad, outCubic, inCubic, inOutCubic, inOutSine, outBack, outQuint

    /// (x1, y1, x2, y2), verbatim from the §0.3 table.
    public var controlPoints: (x1: Double, y1: Double, x2: Double, y2: Double) {
        switch self {
        case .linear:     return (0, 0, 1, 1)
        case .outQuad:    return (0.5, 1, 0.89, 1)
        case .inQuad:     return (0.11, 0, 0.5, 0)
        case .outCubic:   return (0.33, 1, 0.68, 1)
        case .inCubic:    return (0.32, 0, 0.67, 0)
        case .inOutCubic: return (0.65, 0, 0.35, 1)
        case .inOutSine:  return (0.37, 0, 0.63, 1)
        case .outBack:    return (0.34, 1.56, 0.64, 1)
        case .outQuint:   return (0.22, 1, 0.36, 1)
        }
    }

    /// Eased progress for t in 0...1 (t is clamped; outBack overshoots above 1 inside the interval).
    public func callAsFunction(_ t: Double) -> Double {
        if self == .linear { return min(max(t, 0), 1) }
        let c = controlPoints
        return Ease.cubicBezier(c.x1, c.y1, c.x2, c.y2, t)
    }
}

extension Ease {
    /// A CSS `cubic-bezier(x1, y1, x2, y2)` timing function: solves x(s) = t for the curve parameter (Newton, then
    /// bisection), returns y(s). x1 and x2 must be in 0...1 (true for every token), so x(s) is monotonic.
    public static func cubicBezier(_ x1: Double, _ y1: Double, _ x2: Double, _ y2: Double, _ t: Double) -> Double {
        let x = min(max(t, 0), 1)
        if x == 0 || x == 1 { return x }
        // Polynomial coefficients: B(s) = ((a·s + b)·s + c)·s
        let cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx
        let cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by
        func sampleX(_ s: Double) -> Double { ((ax * s + bx) * s + cx) * s }
        func sampleY(_ s: Double) -> Double { ((ay * s + by) * s + cy) * s }
        func slopeX(_ s: Double) -> Double { (3 * ax * s + 2 * bx) * s + cx }
        var s = x
        for _ in 0..<8 {
            let err = sampleX(s) - x
            if abs(err) < 1e-9 { return sampleY(s) }
            let d = slopeX(s)
            if abs(d) < 1e-9 { break }
            s -= err / d
        }
        // Bisection fallback (flat slopes near the ends).
        var lo = 0.0, hi = 1.0
        s = x
        for _ in 0..<60 {
            let v = sampleX(s)
            if abs(v - x) < 1e-10 { break }
            if v < x { lo = s } else { hi = s }
            s = (lo + hi) / 2
        }
        return sampleY(s)
    }

    /// `expFade(τ)` of §0.3: v = v0·e^(−t/τ).
    public static func expFade(_ t: Double, tau: Double, from v0: Double = 1) -> Double {
        t <= 0 ? v0 : v0 * exp(-t / tau)
    }
}

// MARK: - Springs (SPEC-motion-audio §0.4)

/// `spring(response, dampingFraction)` exactly as SwiftUI names it, in the closed form of §0.4. (Named `SpringCurve`
/// so it never shadows SwiftUI's own `Spring` type in files that import both.)
/// ω0 = 2π / response, ζ = dampingFraction, mass 1,
/// x(t) = e^(−ζω0 t)·(x0·cos(ωd t) + ((v0 + ζω0 x0)/ωd)·sin(ωd t)), ωd = ω0·√(1 − ζ²).
/// `x` is the displacement from rest: a value that springs from `a` to `b` is `b + (a − b)·x(t)` with x0 = 1.
public struct SpringCurve: Equatable, Sendable {
    public var response: Double
    public var dampingFraction: Double
    public init(response: Double, dampingFraction: Double) {
        self.response = response; self.dampingFraction = dampingFraction
    }

    public var omega0: Double { 2 * .pi / response }

    /// Displacement at t (t < 0 returns x0). Underdamped (ζ < 1) as every spec spring; ζ ≥ 1 uses the critically
    /// damped form.
    public func displacement(_ t: Double, x0: Double = 1, v0: Double = 0) -> Double {
        guard t > 0 else { return x0 }
        let w0 = omega0, z = dampingFraction
        if z < 1 {
            let wd = w0 * (1 - z * z).squareRoot()
            return exp(-z * w0 * t) * (x0 * cos(wd * t) + ((v0 + z * w0 * x0) / wd) * sin(wd * t))
        }
        return exp(-w0 * t) * (x0 + (v0 + w0 * x0) * t)
    }

    /// A value springing from `from` to `to` (released at t = 0 with no velocity).
    public func value(_ t: Double, from: Double, to: Double) -> Double { to + (from - to) * displacement(t) }

    /// "Done" per §0.4: |x| < 0.5 % of the travel and the envelope has decayed below it too.
    public func settleTime(threshold: Double = 0.005) -> Double {
        let z = min(dampingFraction, 0.999), w0 = omega0
        // Envelope e^(−ζω0 t)·√(1 + (ζ/√(1−ζ²))²) < threshold
        let k = (1 + (z * z) / (1 - z * z)).squareRoot()
        return log(k / threshold) / (z * w0)
    }
}

// MARK: - Keyframe tracks

/// A 1-D keyframe track: (t, value) keys in increasing t. Before the first key the first value holds, after the last
/// key the last value holds. Interpolation is linear, or monotone cubic (Fritsch–Carlson / PCHIP: passes through
/// every key, never overshoots between keys) for measured tracks that must stay smooth.
public struct KeyTrack: Equatable, Sendable {
    public enum Interpolation: String, Sendable { case linear, monotoneCubic }
    public let times: [Double]
    public let values: [Double]
    public let interpolation: Interpolation
    /// Monotone cubic only: the first and last slopes are forced to 0 (ease in/out at the ends). C1: stored so the track
    /// round-trips as data (Tunable.swift).
    public let endSlopesZero: Bool
    private let slopes: [Double]

    public init(_ keys: [(Double, Double)], interpolation: Interpolation = .linear, endSlopesZero: Bool = false) {
        precondition(!keys.isEmpty, "KeyTrack needs at least one key")
        times = keys.map(\.0); values = keys.map(\.1)
        self.interpolation = interpolation
        self.endSlopesZero = endSlopesZero
        precondition(zip(times, times.dropFirst()).allSatisfy { $0 < $1 }, "KeyTrack keys must be strictly increasing")
        slopes = interpolation == .monotoneCubic
            ? KeyTrack.pchipSlopes(times, values, endSlopesZero: endSlopesZero) : []
    }

    public var start: Double { times[0] }
    public var end: Double { times[times.count - 1] }

    public func callAsFunction(_ t: Double) -> Double { value(at: t) }

    public func value(at t: Double) -> Double {
        if t <= times[0] { return values[0] }
        let n = times.count
        if t >= times[n - 1] { return values[n - 1] }
        // Tracks are short (≤ 12 keys): a linear scan beats a binary search here.
        var i = 0
        while i < n - 2 && t >= times[i + 1] { i += 1 }
        let t0 = times[i], t1 = times[i + 1], h = t1 - t0
        let u = (t - t0) / h
        let v0 = values[i], v1 = values[i + 1]
        switch interpolation {
        case .linear:
            return v0 + (v1 - v0) * u
        case .monotoneCubic:
            let m0 = slopes[i] * h, m1 = slopes[i + 1] * h
            let u2 = u * u, u3 = u2 * u
            return (2 * u3 - 3 * u2 + 1) * v0 + (u3 - 2 * u2 + u) * m0 + (-2 * u3 + 3 * u2) * v1 + (u3 - u2) * m1
        }
    }

    private static func pchipSlopes(_ x: [Double], _ y: [Double], endSlopesZero: Bool) -> [Double] {
        let n = x.count
        guard n > 1 else { return [0] }
        var d = [Double](repeating: 0, count: n - 1)
        for i in 0..<(n - 1) { d[i] = (y[i + 1] - y[i]) / (x[i + 1] - x[i]) }
        var m = [Double](repeating: 0, count: n)
        m[0] = d[0]; m[n - 1] = d[n - 2]
        if n > 2 {
            for i in 1..<(n - 1) {
                if d[i - 1] * d[i] <= 0 { m[i] = 0; continue }
                let w1 = 2 * (x[i + 1] - x[i]) + (x[i] - x[i - 1])
                let w2 = (x[i + 1] - x[i]) + 2 * (x[i] - x[i - 1])
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])        // weighted harmonic mean (Fritsch–Butland)
            }
        }
        if endSlopesZero { m[0] = 0; m[n - 1] = 0 }
        return m
    }

    public static func == (a: KeyTrack, b: KeyTrack) -> Bool {
        a.times == b.times && a.values == b.values && a.interpolation == b.interpolation && a.endSlopesZero == b.endSlopesZero
    }
}

// MARK: - Small helpers shared by the curves

@inline(__always) func clamp01(_ x: Double) -> Double { min(max(x, 0), 1) }

/// Progress of t through [start, start + duration], clamped to 0...1.
@inline(__always) func progress(_ t: Double, _ start: Double, _ duration: Double) -> Double {
    duration <= 0 ? (t >= start ? 1 : 0) : clamp01((t - start) / duration)
}

@inline(__always) func lerp(_ a: Double, _ b: Double, _ u: Double) -> Double { a + (b - a) * u }

@inline(__always) func lerp(_ a: CGPoint, _ b: CGPoint, _ u: Double) -> CGPoint {
    CGPoint(x: a.x + (b.x - a.x) * u, y: a.y + (b.y - a.y) * u)
}
