// WP0 → B1 (SPEC-architecture §3.2, §12.2 WP0): COPIED as-is from design/spike-src/App/Render/Track.swift (the tech
// spike, committed by the orchestrator), plus the `TravelProfile` it needs, copied as-is from
// design/spike-src/App/Core/Geometry.swift. BOARD owns this file from B1 on (the production exit timing is
// ExitKinematics, §4.16/D5; the spike's accelerate-then-cruise profile stays here only as the proven reference).
// Kit decoupling step: the spike's `Track` is `TravelTrack` now (a rename inside this file only: nothing else names it), so the
// puppets' own nested `PuppetMotion.Track` no longer reads as a use of this board file; the file is the arrow board's
// (`CAAnimation.hi()` and `AnimationEnd` are what its movers use), no longer core's.

import QuartzCore

/// Travel keyframes shared by every layer of a moving arrow (body trim, head position, trail mask, dots,
/// tail emitter): `travel[i]` at `times[i]` seconds; `fns[i]` shapes the segment after keyframe i.
struct TravelTrack {
    var times: [Double]
    var travel: [CGFloat]
    var fns: [CAMediaTimingFunction]?

    var duration: Double { times[times.count - 1] }
    var final: CGFloat { travel[travel.count - 1] }
    var keyTimes: [NSNumber] { times.map { NSNumber(value: duration > 0 ? $0 / duration : 0) } }

    /// y = x^2 as a cubic Bezier: constant acceleration from rest (ends at twice the mean speed).
    static let accelerate = CAMediaTimingFunction(controlPoints: 1.0 / 3, 0, 2.0 / 3, 1.0 / 3)
    /// Exact y = x (the named .linear function is solved numerically and drifts; arrows tech spike).
    static let cruise = CAMediaTimingFunction(controlPoints: 1.0 / 3, 1.0 / 3, 2.0 / 3, 2.0 / 3)
    static let easeOutCubic = CAMediaTimingFunction(controlPoints: 0.215, 0.61, 0.355, 1)

    /// 0 -> distance at the profile's speed (constant, or accelerate-then-cruise).
    static func forward(_ p: TravelProfile, to distance: CGFloat) -> TravelTrack {
        if p.accel > 0, distance > p.accelDistance {
            return TravelTrack(times: [0, p.accel, p.time(toReach: distance)], travel: [0, p.accelDistance, distance],
                         fns: [accelerate, cruise])
        }
        if p.accel > 0 {
            return TravelTrack(times: [0, p.time(toReach: distance)], travel: [0, distance], fns: [accelerate])
        }
        return TravelTrack(times: [0, p.time(toReach: distance)], travel: [0, distance], fns: nil)
    }

    /// Forward to the contact point, then eased back to rest.
    static func bump(_ p: TravelProfile, contact: CGFloat, back: Double) -> TravelTrack {
        var t = forward(p, to: contact)
        let n = t.times.count - 1
        t.times.append(t.duration + back)
        t.travel.append(0)
        var f = t.fns ?? [CAMediaTimingFunction](repeating: cruise, count: n)
        f.append(easeOutCubic)
        t.fns = f
        return t
    }

    /// Travel at time `t` (exact for the linear/accelerate curves used here; bump return approximated).
    func value(at t: Double, profile: TravelProfile) -> CGFloat {
        if t <= 0 { return travel[0] }
        if t >= duration { return final }
        return min(profile.travel(at: t), final)
    }

    /// Same timing, travel clamped to `limit` (inserts the keyframe where the clamp starts).
    func clamped(to limit: CGFloat, profile: TravelProfile) -> TravelTrack {
        guard final > limit else { return self }
        let tc = profile.time(toReach: limit)
        var times: [Double] = [], travel: [CGFloat] = []
        for (t, s) in zip(self.times, self.travel) where t < tc { times.append(t); travel.append(s) }
        times.append(tc); travel.append(limit)
        times.append(duration); travel.append(limit)
        return TravelTrack(times: times, travel: travel, fns: nil)
    }

    /// Uniform samples (plus every keyframe) for properties that are not linear in travel.
    func samples(every dt: Double, profile: TravelProfile, extra: [Double] = []) -> [(Double, CGFloat)] {
        var ts = Set(times)
        var t = 0.0
        while t < duration { ts.insert(t); t += dt }
        for e in extra where e > 0 && e < duration { ts.insert(e) }
        return ts.sorted().map { ($0, value(at: $0, profile: profile)) }
    }
}

extension CAAnimation {
    func hi() -> Self {
        preferredFrameRateRange = CAFrameRateRange(minimum: 60, maximum: 120, preferred: 120)
        return self
    }
}

final class AnimationEnd: NSObject, CAAnimationDelegate {
    private var action: ((Bool) -> Void)?
    init(_ action: @escaping (Bool) -> Void) { self.action = action }
    func animationDidStop(_ anim: CAAnimation, finished flag: Bool) {
        let a = action
        action = nil
        a?(flag)
    }
}

func keyframes(_ keyPath: String, _ values: [Any], _ track: TravelTrack) -> CAKeyframeAnimation {
    let a = CAKeyframeAnimation(keyPath: keyPath)
    a.values = values
    a.keyTimes = track.keyTimes
    a.timingFunctions = track.fns
    a.duration = track.duration
    return a.hi()
}

func sampledKeyframes(_ keyPath: String, _ samples: [(Double, Any)], duration: Double,
                      discrete: Bool = false) -> CAKeyframeAnimation {
    let a = CAKeyframeAnimation(keyPath: keyPath)
    a.values = samples.map { $0.1 }
    a.keyTimes = samples.map { NSNumber(value: duration > 0 ? $0.0 / duration : 0) }
    a.calculationMode = discrete ? .discrete : .linear
    if discrete { a.keyTimes = (a.keyTimes ?? []) + [1] }
    a.duration = duration
    return a.hi()
}

// MARK: - From design/spike-src/App/Core/Geometry.swift

struct TravelProfile {
    let v: CGFloat
    let accel: Double     // seconds to reach v (0 = constant speed from the first frame)

    var accelDistance: CGFloat { v * CGFloat(accel) / 2 }

    func time(toReach s: CGFloat) -> Double {
        guard s > 0 else { return 0 }
        if accel > 0, s <= accelDistance { return accel * Double((s / accelDistance).squareRoot()) }
        return (accel > 0 ? accel : 0) + Double((s - (accel > 0 ? accelDistance : 0)) / v)
    }

    func travel(at t: Double) -> CGFloat {
        guard t > 0 else { return 0 }
        if accel > 0, t <= accel { let k = CGFloat(t / accel); return accelDistance * k * k }
        return (accel > 0 ? accelDistance : 0) + v * CGFloat(t - max(accel, 0))
    }
}
