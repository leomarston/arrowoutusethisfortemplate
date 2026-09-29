import QuartzCore

/// Travel keyframes shared by every layer of a moving arrow (body trim, head position, trail mask, dots,
/// tail emitter): `travel[i]` at `times[i]` seconds; `fns[i]` shapes the segment after keyframe i.
struct Track {
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
    static func forward(_ p: TravelProfile, to distance: CGFloat) -> Track {
        if p.accel > 0, distance > p.accelDistance {
            return Track(times: [0, p.accel, p.time(toReach: distance)], travel: [0, p.accelDistance, distance],
                         fns: [accelerate, cruise])
        }
        if p.accel > 0 {
            return Track(times: [0, p.time(toReach: distance)], travel: [0, distance], fns: [accelerate])
        }
        return Track(times: [0, p.time(toReach: distance)], travel: [0, distance], fns: nil)
    }

    /// Forward to the contact point, then eased back to rest.
    static func bump(_ p: TravelProfile, contact: CGFloat, back: Double) -> Track {
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
    func clamped(to limit: CGFloat, profile: TravelProfile) -> Track {
        guard final > limit else { return self }
        let tc = profile.time(toReach: limit)
        var times: [Double] = [], travel: [CGFloat] = []
        for (t, s) in zip(self.times, self.travel) where t < tc { times.append(t); travel.append(s) }
        times.append(tc); travel.append(limit)
        times.append(duration); travel.append(limit)
        return Track(times: times, travel: travel, fns: nil)
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

func keyframes(_ keyPath: String, _ values: [Any], _ track: Track) -> CAKeyframeAnimation {
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
