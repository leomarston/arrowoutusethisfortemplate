import UIKit
import PathCore

// B2 (SPEC-architecture §4.4 "corner", §5.6; SPEC-motion-audio §3.5.6; CONSISTENCY O-28) + FIX-2 lane A (L02, art/lanes/corner.md
// code requests 1-3; v552 first on L70, 32 shipped levels carry corners). A corner turns a ray 90° (its turn accepts `in` and
// `out.opposite`). The look, MEASURED on the phone (L70/L71/L76/L79/L80/L82, 21 corners): a blue coil spring on a domed foot
// UNDER a red plate, drawn from the art lane's per-facing layers `corner{Turn}Spring` / `corner{Turn}Plate` — each a 64 × 64 pt
// frame at the 32 pt design pitch (2 × 2 pitch, centred on the corner cell's centre; the art overflows the cell exactly as the
// original's does), NOT rotated: the original lights three facings as rotations of one render and draws UpLeft as its own render
// (the plate's lit end and the shadow stay up-left / below), so every facing uses its own pair. If a pair is missing the
// `cornerWedge` sprite (= UpRight's pair composited) is rotated per turn, else a code-drawn teal wedge fills the cell.
// The hit (corner_anim.py, the three 60 Hz clips give one curve in pitch units, fit rms 0.0035 p): on the `.corner` beat (the head
// at the cell centre) the plate is pushed IN along the facing s (−0.093 p within one frame, starting 0.012 s before the beat),
// sinks linearly to −0.105 p while the arrow's body slides over it, and 0.010 s after the TAIL passes the cell centre springs out
// (+0.079 p at +0.063 s, −0.030 p at +0.124 s, rest at +0.229 s; ease-in-out segments). The spring stretches / compresses along s
// about its fixed foot (k = 1 + x / 0.694). The exiting arrow draws over the corner (the corner stays in `roots.obstacle`, below
// the movers). board.json `corner.*` holds the measured numbers (replaces the 1.0 → 1.15 → 1.0 pop, a DECISION from older builds).

/// The measured corner hit (board.json `corner`): the plate's offset along the facing, in pitch units, at a time after the beat.
struct CornerHitSpec: Equatable {
    var pressLead = 0.012            // the push starts this long BEFORE the beat (the head tip reaches the plate first) …
    var pressDur = 0.016             // … and is complete one 60 Hz frame later
    var push = -0.093                // reached at the end of the press
    var holdEnd = -0.105             // a linear sink while the body slides over the plate
    var releaseAfterTail = 0.010     // the release: this long after the tail passes the cell centre
    var peak = (t: 0.063, x: 0.079)  // after the release
    var trough = (t: 0.124, x: -0.030)
    var restAt = 0.229
    var pivot = -0.98                // the spring's foot on the axis (cell centre + pivot · s), pitch
    var springLen = 0.694            // the foot pivot → the plate's back face, pitch
    var sampleHz = 60.0

    static func == (a: CornerHitSpec, b: CornerHitSpec) -> Bool {
        a.pressLead == b.pressLead && a.pressDur == b.pressDur && a.push == b.push && a.holdEnd == b.holdEnd
            && a.releaseAfterTail == b.releaseAfterTail && a.peak == b.peak && a.trough == b.trough && a.restAt == b.restAt
            && a.pivot == b.pivot && a.springLen == b.springLen && a.sampleHz == b.sampleHz
    }

    private static func easeInOut(_ f: Double) -> Double { (1 - cos(Double.pi * min(1, max(0, f)))) / 2 }

    /// The plate offset (pitch, + = out of the spring) at `t` s after the beat; `hold` = beat → the tail at the cell centre.
    /// The same function as art/ui/recipes/corner_anim.py `offset(t, hold)`.
    func offset(_ t: Double, hold: Double) -> Double {
        let t0 = -pressLead
        if t < t0 { return 0 }
        let t1 = t0 + pressDur
        if t < t1 { return push * sin(Double.pi / 2 * (t - t0) / max(1e-6, pressDur)) }
        let r = hold + releaseAfterTail
        if t < r { return push + (holdEnd - push) * (t - t1) / max(1e-6, r - t1) }
        let b = t - r
        if b < peak.t { return holdEnd + (peak.x - holdEnd) * Self.easeInOut(b / peak.t) }
        if b < trough.t { return peak.x + (trough.x - peak.x) * Self.easeInOut((b - peak.t) / (trough.t - peak.t)) }
        if b < restAt { return trough.x * (1 - Self.easeInOut((b - trough.t) / (restAt - trough.t))) }
        return 0
    }

    /// The last sampled time after the beat (the plate at rest).
    func end(hold: Double) -> Double { hold + releaseAfterTail + restAt }

    /// The spring's scale along s for a plate offset x (pitch).
    func springScale(_ x: Double) -> Double { 1 + x / max(0.01, springLen) }
}

@MainActor final class CornerNode {
    let id: ObstacleID
    /// The sprite frame: 2 × 2 pitch, centred on the corner cell's centre (art/lanes/corner.md code request 1).
    let layer = CALayer()
    /// Spring (under) and plate (over), the facing's own renders; nil when the pair is missing (the rotated fallback draws).
    let spring: CALayer?
    let plate: CALayer?
    let turn: CornerTurn
    /// The facing's unit vector on screen (y down): + = out of the spring, toward the arrows the plate turns.
    let facing: CGVector
    let pitch: CGFloat
    /// The sprite's frame side in points (64 pt at the 32 pt design pitch).
    let side: CGFloat
    /// The last hit's curve (stage-local begin of t = 0 = its beat, hold) — a second hit starts from its value.
    private(set) var lastHit: (beat: CFTimeInterval, hold: Double)?
    private(set) var hits = 0

    /// The sprite ids of one facing (spring, plate).
    static func layerIDs(_ t: CornerTurn) -> (spring: String, plate: String) {
        let s = suffix(t)
        return ("corner\(s)Spring", "corner\(s)Plate")
    }

    /// Every corner sprite the engine may draw (the 8 facing layers + the fallback wedge).
    static let spriteIDs: [String] = CornerTurn.allCases.flatMap { [layerIDs($0).spring, layerIDs($0).plate] } + ["cornerWedge"]

    static func suffix(_ t: CornerTurn) -> String {
        switch t {
        case .upRight: return "UpRight"
        case .upLeft: return "UpLeft"
        case .downLeft: return "DownLeft"
        case .downRight: return "DownRight"
        }
    }

    static func facing(_ t: CornerTurn) -> CGVector {
        let h = CGFloat(0.5.squareRoot())
        switch t {
        case .upRight: return CGVector(dx: h, dy: h)
        case .upLeft: return CGVector(dx: -h, dy: h)
        case .downLeft: return CGVector(dx: -h, dy: -h)
        case .downRight: return CGVector(dx: h, dy: -h)
        }
    }

    init(spec: ObstacleSpec, geo: BoardGeometry, art: BoardArt, scale: CGFloat, hit: CornerHitSpec = CornerHitSpec()) {
        id = spec.id
        let p = geo.pitch
        pitch = p
        let c = geo.centre(spec.cells.first ?? Cell(0, 0))
        let t = spec.turn ?? .upRight
        turn = t
        facing = Self.facing(t)
        side = 64.0 * p / 32.0                                   // sprite size_pt × pitch / design pitch
        layer.bounds = CGRect(x: 0, y: 0, width: side, height: side)
        layer.position = c
        let ids = Self.layerIDs(t)
        if let springImage = art.image(ids.spring), let plateImage = art.image(ids.plate) {
            let s = CALayer(), pl = CALayer()
            // the spring scales about its foot: the anchor = the pivot (cell centre + pivot · s) in the frame's unit coords
            let a = CGPoint(x: 0.5 + CGFloat(hit.pivot) * facing.dx / 2, y: 0.5 + CGFloat(hit.pivot) * facing.dy / 2)
            s.bounds = layer.bounds
            s.anchorPoint = a
            s.position = CGPoint(x: a.x * side, y: a.y * side)
            s.contents = springImage
            s.contentsGravity = .resize
            pl.frame = layer.bounds
            pl.contents = plateImage
            pl.contentsGravity = .resize
            layer.addSublayer(s)
            layer.addSublayer(pl)
            spring = s
            plate = pl
        } else {
            spring = nil
            plate = nil
            let angle: CGFloat
            switch t {                                           // the wedge = UpRight; the others are its quarter-turns
            case .upRight: angle = 0
            case .upLeft: angle = .pi / 2
            case .downLeft: angle = .pi
            case .downRight: angle = -.pi / 2
            }
            let inner = CALayer()
            inner.frame = layer.bounds
            layer.addSublayer(inner)
            if let img = art.image("cornerWedge") {
                inner.contents = img
                inner.contentsGravity = .resize
            } else {
                // last resort: a teal wedge filling the cell (the middle pitch of the 2-pitch frame)
                let sh = CAShapeLayer()
                let path = CGMutablePath()
                let m = 0.08 * p, o = (side - p) / 2
                path.move(to: CGPoint(x: o + m, y: o + m))
                path.addLine(to: CGPoint(x: o + p - m, y: o + m))
                path.addLine(to: CGPoint(x: o + m, y: o + p - m))
                path.closeSubpath()
                sh.path = path
                sh.fillColor = BoardConfig.color("#4CCBA5")
                sh.strokeColor = BoardConfig.color("#1C8068")
                sh.lineWidth = 0.06 * p
                sh.lineJoin = .round
                sh.frame = inner.bounds
                sh.contentsScale = scale
                inner.addSublayer(sh)
            }
            inner.setAffineTransform(CGAffineTransform(rotationAngle: angle))
        }
    }

    /// The spring's transform for a plate offset x (pitch): a scale k along s about the anchor (the foot).
    func springTransform(_ x: Double, hit: CornerHitSpec) -> CGAffineTransform {
        let k = CGFloat(hit.springScale(x))
        let sg: CGFloat = facing.dx * facing.dy > 0 ? 1 : -1
        return CGAffineTransform(a: (1 + k) / 2, b: (k - 1) / 2 * sg, c: (k - 1) / 2 * sg, d: (1 + k) / 2, tx: 0, ty: 0)
    }

    /// The plate's centre for a plate offset x (pitch).
    func platePosition(_ x: Double) -> CGPoint {
        CGPoint(x: side / 2 + CGFloat(x) * pitch * facing.dx, y: side / 2 + CGFloat(x) * pitch * facing.dy)
    }

    /// The hit: `beat` = the stage-local time the head reaches the cell centre, `hold` = beat → the tail at the cell centre.
    /// Two keyframe tracks sampled at 60 Hz (linear between samples, like the exits). A hit while the previous one still runs
    /// continues from that curve's value (its samples up to the new press, then the new press from there).
    func hit(beat: CFTimeInterval, hold: Double, spec: CornerHitSpec, now: CFTimeInterval) {
        hits += 1
        guard let plate, let spring else {
            // the rotated fallback has no parts: the whole frame follows the plate's offset
            let (times, xs, begin, dur) = samples(beat: beat, hold: hold, spec: spec, now: now)
            let vals = xs.map { NSValue(cgPoint: CGPoint(x: layer.position.x + CGFloat($0) * pitch * facing.dx,
                                                         y: layer.position.y + CGFloat($0) * pitch * facing.dy)) }
            layer.add(Anim.keyframes("position", vals, times: times, duration: dur, begin: begin), forKey: "cornerHit")
            lastHit = (beat, hold)
            return
        }
        let (times, xs, begin, dur) = samples(beat: beat, hold: hold, spec: spec, now: now)
        let pos = xs.map { NSValue(cgPoint: platePosition($0)) }
        let tr = xs.map { NSValue(caTransform3D: CATransform3DMakeAffineTransform(springTransform($0, hit: spec))) }
        plate.add(Anim.keyframes("position", pos, times: times, duration: dur, begin: begin), forKey: "cornerHit")
        spring.add(Anim.keyframes("transform", tr, times: times, duration: dur, begin: begin), forKey: "cornerHit")
        lastHit = (beat, hold)
    }

    /// The 60 Hz samples (times relative to `begin`, offsets in pitch) of a hit. When the previous hit's curve is still moving at
    /// this press, the new tracks (which replace the old ones) start NOW with the old curve's values and the press blends from
    /// the old curve's value at its start (no jump).
    func samples(beat: CFTimeInterval, hold: Double, spec: CornerHitSpec, now: CFTimeInterval)
        -> (times: [Double], xs: [Double], begin: CFTimeInterval, duration: Double) {
        let step = 1 / max(1, spec.sampleHz)
        let pressAt = beat - spec.pressLead
        let end = beat + spec.end(hold: hold)
        var prev: ((CFTimeInterval) -> Double)?
        if let last = lastHit, pressAt < last.beat + spec.end(hold: last.hold) {
            let b = last.beat, h = last.hold
            prev = { spec.offset($0 - b, hold: h) }
        }
        let begin = prev != nil ? min(max(now, pressAt - 10), pressAt) : pressAt
        let from = prev.map { $0(pressAt) } ?? 0
        func value(_ at: CFTimeInterval) -> Double {
            if at < pressAt { return prev?(at) ?? 0 }
            let x = spec.offset(at - beat, hold: hold)
            let f = min(1, max(0, (at - pressAt) / max(1e-6, spec.pressDur)))
            return from * (1 - f) + x                          // the press starts from the previous curve's value
        }
        var times: [Double] = [], xs: [Double] = []
        var at = begin
        while at < end - 1e-9 {
            times.append(at - begin)
            xs.append(value(at))
            at += step
        }
        times.append(end - begin)                              // at rest
        xs.append(0)
        return (times, xs, begin, end - begin)
    }
}
