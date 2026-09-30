import Foundation
import GameCore

// C1 (SPEC-architecture §4.16, D5). How far an exiting arrow's head has travelled along its own path, in CELLS (the motion
// scales with zoom: a fit in pt fails, motion.md §3.3), as a function of τ = seconds since the release:
//     s(τ) = vmax·τ − (vmax − v0)·T·(1 − e^(−τ/T)),   v(τ) = vmax − (vmax − v0)·e^(−τ/T)
// `measured` = research/motion.md §3.3 pass 2 (VERIFIED 11 exits, 203 samples, 4 pitches 14.0–28.1 pt, RMS 0.082 cells):
// v0 7.67, vmax 73.86 c/s, T 0.353 s. The architecture quotes pass 1 (5 exits: s = 71.4τ − 21.29(1 − e^(−τ/0.323))), kept as
// `pass1`; motion.md says the law is stable (T(d) differs ≤ 7 ms) and SPEC.md §4 makes motion.md the interim authority
// for timings, so pass 2 is the default. Both tables are pinned by KinematicsTests. Data: board.json may override it.
// The exit ends when the TAIL passes the SCREEN edge: time(toTravel: headToScreenEdge + bodyLength (+ tail cap)).

public struct ExitKinematics: Codable, Sendable, Equatable, TunableParameters {
    /// Speed at the release, cells/s.
    public var v0: Double
    /// Cruise speed, cells/s.
    public var vmax: Double
    /// Time constant of the approach to cruise, s.
    public var tau: Double

    public init(v0: Double, vmax: Double, tau: Double) {
        self.v0 = v0; self.vmax = vmax; self.tau = tau
    }

    /// motion.md §3.3 pass 2 (the default).
    public static let measured = ExitKinematics(v0: 7.67, vmax: 73.86, tau: 0.353)
    /// SPEC-architecture §4.16 / D5 (motion pass 1, 5 exits): s = 71.4τ − 21.29(1 − e^(−τ/0.323)).
    public static let pass1 = ExitKinematics(v0: 71.4 - 21.29 / 0.323, vmax: 71.4, tau: 0.323)

    /// Head travel (cells) τ seconds after the release; 0 before it.
    public func s(_ t: Double) -> Double {
        guard t > 0 else { return 0 }
        return vmax * t - (vmax - v0) * tau * (1 - exp(-t / tau))
    }

    /// Speed (cells/s) τ seconds after the release (v0 before it).
    public func v(_ t: Double) -> Double {
        guard t > 0 else { return v0 }
        return vmax - (vmax - v0) * exp(-t / tau)
    }

    /// The inverse: seconds after the release until the head has travelled `d` cells (0 for d ≤ 0).
    /// Safeguarded Newton between the bounds d/vmax ≤ τ ≤ (d + (vmax − v0)·T)/vmax; |s(τ) − d| < 1e-10 cells.
    public func time(toTravel d: Double) -> Double {
        guard d > 0 else { return 0 }
        var lo = d / vmax, hi = (d + (vmax - v0) * tau) / vmax
        if v0 > 0 { hi = min(hi, d / v0) }
        var t = min(max((lo + hi) / 2, lo), hi)
        for _ in 0..<60 {
            let f = s(t) - d
            if abs(f) < 1e-10 { break }
            if f > 0 { hi = t } else { lo = t }
            let next = t - f / v(t)
            t = (next > lo && next < hi) ? next : (lo + hi) / 2
        }
        return t
    }

    /// Sample times for keyframes: every `step` s from 0 to the time the head reaches `d` cells (that time included),
    /// with the travel at each. B1 turns them into `CAKeyframeAnimation` keys (exact linear between samples, §5.5).
    public func samples(toTravel d: Double, step: Double = 1.0 / 60.0) -> [(t: Double, s: Double)] {
        let end = time(toTravel: d)
        guard end > 0, step > 0 else { return [(0, 0)] }
        var out: [(t: Double, s: Double)] = []
        var t = 0.0
        while t < end - 1e-9 { out.append((t, s(t))); t += step }
        out.append((end, d))
        return out
    }

    // Static conveniences on the measured law (the §4.16 call shape `ExitKinematics.s(τ)`).
    public static func s(_ t: Double) -> Double { measured.s(t) }
    public static func v(_ t: Double) -> Double { measured.v(t) }
    public static func time(toTravel d: Double) -> Double { measured.time(toTravel: d) }
}
