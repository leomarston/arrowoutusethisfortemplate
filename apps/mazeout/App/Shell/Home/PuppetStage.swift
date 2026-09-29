import SwiftUI
import UIKit

// SHELL S1 (SPEC-architecture §6.4 item 2, D14; SPEC-motion-audio §8.2 + MA12). The home characters as cut-out puppets: one
// CALayer per rig layer at its `rect_pt`; each rig loops ONE set of repeating CAKeyframeAnimations whose duration is the rig's
// measured cycle (scientist 3.16 s, right worker 10.2 s, left worker 17.3 s). The motion is DATA: `ui.json puppet.<rig>` =
// {cycle, tracks[{layer, prop, t[], v[], curve, pivot?}]} (generated from the §8.2 tables). Targets:
//   whole        every layer of a worker as one sublayer tree about the `feet` pivot (sway, look-up, think)
//   head         the scientist's head group + its lid overlays about `neck`
//   <group>      prop `member`: the group's members swap by discrete opacity keyframes (eyes, body)
//   lids         prop `overlay`: the named overlay shows ("" = none)
//   <layer>      rotation about its own `shoulder` pivot (arms), or about the track's `pivot` (the torso breathe)
// Rotations are additive (the sway and the nod add up), in degrees, positive = clockwise on screen. Everything runs on the
// render server: zero main-thread work at rest (the S1 report's sample). Capture mode (-pc.capture) holds the rest pose
// (the full render); `-pc.freezeAt puppets@<t>` freezes the loops at t. Stages of one rig share the absolute cycle grid
// (beginTime aligned to a multiple of the cycle), so a rig split around the console (the scientist's arms, SPEC-ui §2.2.1)
// stays in step. The MotionClock's time scale (slow motion) mirrors onto the layers.

struct PuppetMotion {
    struct Track {
        let layer: String
        let prop: String
        let times: [Double]
        let values: [Any]
        let curves: [String]
        let pivot: CGPoint?
    }

    var cycle: Double = 0
    var tracks: [Track] = []
    var phase: Double = 0

    static let none = PuppetMotion()

    init() {}

    init(_ file: TuningFile, rig: String) {
        let base = "puppet." + rig
        cycle = file.double(base + ".cycle", 0)
        phase = file.double(base + ".phase", 0)
        guard let raw = file.value(base + ".tracks") as? [[String: Any]] else {
            if cycle == 0 { Log.mark("tokens", "ui.json has no \(base): \(rig) holds its rest pose") }
            return
        }
        tracks = raw.compactMap { item -> Track? in
            guard let layer = item["layer"] as? String, let prop = item["prop"] as? String,
                  let t = item["t"] as? [Any], let v = item["v"] as? [Any], t.count == v.count, !t.isEmpty else { return nil }
            let times = t.compactMap { ($0 as? NSNumber)?.doubleValue }
            guard times.count == t.count else { return nil }
            let segs = max(0, v.count - 1)
            let curves: [String]
            if let list = item["curve"] as? [String], list.count == segs { curves = list } else {
                curves = Array(repeating: (item["curve"] as? String) ?? "sine", count: segs)
            }
            var pivot: CGPoint?
            if let p = item["pivot"] as? [Any], p.count == 2, let x = (p[0] as? NSNumber)?.doubleValue,
               let y = (p[1] as? NSNumber)?.doubleValue { pivot = CGPoint(x: x, y: y) }
            return Track(layer: layer, prop: prop, times: times, values: v, curves: curves, pivot: pivot)
        }
    }
}

/// Which layers one stage draws (the scientist is split around the console: torso + head behind it, arms in front).
enum PuppetPart: Equatable {
    case all
    case only(Set<String>)
    case excluding(Set<String>)

    func includes(_ name: String) -> Bool {
        switch self {
        case .all: return true
        case .only(let s): return s.contains(name)
        case .excluding(let s): return !s.contains(name)
        }
    }

    static let scientistArms: Set<String> = ["armL", "armR", "armR_point"]
}

/// One character, framed at the rig's placement on the 393 x 852 scene canvas (put it inside `SceneLayer`).
struct PuppetStage: UIViewRepresentable {
    let rig: PuppetRig
    let motion: PuppetMotion
    let clock: MotionClock
    let animate: Bool
    let freezeAt: Double?
    var part: PuppetPart = .all

    func makeUIView(context: Context) -> PuppetView {
        let v = PuppetView(rig: rig, motion: motion, animate: animate, freezeAt: freezeAt, part: part)
        clock.observeTimeScale { [weak v] k in v?.setTimeScale(k) }
        return v
    }

    func updateUIView(_ uiView: PuppetView, context: Context) {}
}

extension PuppetStage {
    /// The rig's frame on the reference canvas.
    var frame: CGRect { CGRect(origin: rig.placement, size: rig.frame) }
}

/// A4: a raster that rides a rig layer (`PuppetView.setRider`): drawn with its centre at `centre` (pt on the rig's frame).
struct PuppetRider {
    let layer: String
    let image: CGImage
    let size: CGSize
    let centre: CGPoint
    let scale: CGFloat
    /// What the raster shows (a new key redraws it).
    let key: String
}

/// A4 (R3 HOME "badges" / R8's Up & Away token; OD5 / ruling 39, motion-catalog §6.4): a small rig drawn in its own frame
/// (put a `.frame(rig.frame)` on it) with its idle loop from ui.json `puppet.<rig>` on the render server, and an optional live
/// number riding its moving part. At rest (capture mode, reduce motion) the default layers recompose the full render.
struct BadgePuppet: UIViewRepresentable {
    let rig: PuppetRig
    let motion: PuppetMotion
    let clock: MotionClock
    let animate: Bool
    let freezeAt: Double?
    var rider: PuppetRider? = nil

    func makeUIView(context: Context) -> PuppetFrameView {
        let v = PuppetFrameView(PuppetView(rig: rig, motion: motion, animate: animate, freezeAt: freezeAt))
        clock.observeTimeScale { [weak v] k in v?.puppet.setTimeScale(k) }
        v.puppet.setRider(rider)
        return v
    }

    func updateUIView(_ uiView: PuppetFrameView, context: Context) { uiView.puppet.setRider(rider) }
}

/// A4: a puppet fitted to whatever rect SwiftUI gives it (its layers are laid out on the rig's own frame; this scales that frame
/// to the view's bounds — identity when the rect is the rig's frame, as on the reference canvas).
class PuppetFrameView: UIView {
    let puppet: PuppetView

    init(_ puppet: PuppetView) {
        self.puppet = puppet
        super.init(frame: CGRect(origin: .zero, size: puppet.rig.frame))
        isUserInteractionEnabled = false
        backgroundColor = .clear
        isAccessibilityElement = false
        addSubview(puppet)
    }

    required init?(coder: NSCoder) { fatalError("built in code") }

    override func layoutSubviews() {
        super.layoutSubviews()
        let f = puppet.rig.frame
        let t = CGAffineTransform(scaleX: bounds.width / max(f.width, 1), y: bounds.height / max(f.height, 1))
        if puppet.transform != t { puppet.transform = t }
        puppet.center = CGPoint(x: bounds.midX, y: bounds.midY)
    }
}

final class PuppetView: UIView {
    let rig: PuppetRig
    let motion: PuppetMotion
    let animate: Bool
    let freezeAt: Double?
    let part: PuppetPart
    /// "whole": every layer (workers sway about `feet`).
    private(set) var whole = CALayer()
    /// The scientist's head group + lids, about `neck`.
    private(set) var head: CALayer?
    private(set) var layerByName: [String: CALayer] = [:]
    private var installed = false
    /// Number of animations installed (tests, the S1 report).
    private(set) var installedCount = 0
    /// A4: the live number riding a moving layer (`BadgePuppet`), and the key it was drawn for.
    private(set) var riderLayer: CALayer?
    private var riderKey: String?

    init(rig: PuppetRig, motion: PuppetMotion, animate: Bool, freezeAt: Double? = nil, part: PuppetPart = .all) {
        self.rig = rig; self.motion = motion; self.animate = animate; self.freezeAt = freezeAt; self.part = part
        super.init(frame: CGRect(origin: .zero, size: rig.frame))
        isUserInteractionEnabled = false
        backgroundColor = .clear
        isAccessibilityElement = false
        build()
    }

    required init?(coder: NSCoder) { fatalError("PuppetView is built in code") }

    var isWorker: Bool { rig.pivot("feet") != nil }

    /// The layer tree at rest (every animation is added on top of it; the rest pose is the full render).
    private func build() {
        let f = CGRect(origin: .zero, size: rig.frame)
        let feet = rig.pivot("feet") ?? CGPoint(x: f.midX, y: f.maxY)
        Self.anchor(whole, bounds: f, at: feet)
        layer.addSublayer(whole)
        let neck = rig.pivot("neck")
        // A track's explicit pivot re-anchors that layer (the scientist's torso breathes about its bottom centre).
        var pivots: [String: CGPoint] = [:]
        for t in motion.tracks { if let p = t.pivot { pivots[t.layer] = p } }
        for l in rig.layers where part.includes(l.name) {
            let cl = CALayer()
            cl.contentsScale = 3
            if let img = ArtStore.image(path: rig.path(l))?.cgImage { cl.contents = img }
            cl.opacity = rig.isVisibleAtRest(l) ? 1 : 0
            let pivot = pivots[l.name] ?? (l.name.hasPrefix("arm") ? l.pivots["shoulder"] : nil)
            Self.anchor(cl, bounds: CGRect(origin: .zero, size: l.rect.size), at: pivot.map {
                CGPoint(x: $0.x - l.rect.minX, y: $0.y - l.rect.minY)
            } ?? .zero, position: pivot ?? l.rect.origin)
            layerByName[l.name] = cl
            let inHead = !isWorker && (l.group == "head" || l.parent == "head")
            if inHead, let neck {
                if head == nil {
                    let h = CALayer()
                    Self.anchor(h, bounds: f, at: neck)
                    whole.addSublayer(h)
                    head = h
                }
                head?.addSublayer(cl)
            } else {
                whole.addSublayer(cl)
            }
        }
    }

    /// Sets `anchorPoint` to `pivot` (in the layer's own pt) and puts the layer where it rests (`position` in the parent's pt,
    /// default = the pivot in the frame, i.e. a full-frame layer).
    private static func anchor(_ l: CALayer, bounds: CGRect, at pivot: CGPoint, position: CGPoint? = nil) {
        l.bounds = bounds
        l.anchorPoint = CGPoint(x: pivot.x / max(bounds.width, 1), y: pivot.y / max(bounds.height, 1))
        l.position = position ?? pivot
    }

    override func didMoveToWindow() {
        super.didMoveToWindow()
        guard window != nil, animate, !installed else { return }
        installed = true
        install()
    }

    func setTimeScale(_ k: Double) {
        guard freezeAt == nil else { return }
        let now = layer.convertTime(CACurrentMediaTime(), from: nil)
        layer.timeOffset = now
        layer.beginTime = CACurrentMediaTime()
        layer.speed = Float(k)
    }

    /// The target layers of a track.
    private func targets(_ t: PuppetMotion.Track) -> [CALayer] {
        switch t.layer {
        case "whole": return [whole]
        case "head": return head.map { [$0] } ?? []
        default: return layerByName[t.layer].map { [$0] } ?? []
        }
    }

    private func install() {
        let cycle = motion.cycle
        guard cycle > 0, !motion.tracks.isEmpty else { return }
        // One absolute grid per rig: every stage of the rig (and every relaunch of home) starts on a multiple of the cycle.
        let now = CACurrentMediaTime()
        let begin = (now / cycle).rounded(.down) * cycle - motion.phase * cycle
        for (i, t) in motion.tracks.enumerated() {
            switch t.prop {
            case "member", "overlay":
                for (layer, anim) in discrete(t, cycle: cycle) {
                    anim.beginTime = begin
                    layer.add(anim, forKey: "puppet.\(i)")
                    installedCount += 1
                }
            default:
                guard let key = Self.keyPath(t.prop) else { continue }
                for target in targets(t) {
                    let a = CAKeyframeAnimation(keyPath: key)
                    a.values = t.values.map { Self.number($0, prop: t.prop) }
                    a.keyTimes = t.times.map { NSNumber(value: $0 / cycle) }
                    a.timingFunctions = t.curves.map(Self.timing)
                    a.calculationMode = .linear
                    a.isAdditive = !t.prop.hasPrefix("scale")                  // an additive scale would ADD to 1 (A4)
                    a.duration = cycle
                    a.repeatCount = .infinity
                    a.beginTime = begin
                    a.isRemovedOnCompletion = false
                    target.add(a, forKey: "puppet.\(i)")
                    installedCount += 1
                }
            }
        }
        if let t = freezeAt {
            // convert BEFORE stopping the clock: with speed 0 the layer's local time is its timeOffset alone
            let base = layer.convertTime(begin, from: nil)
            layer.speed = 0
            layer.timeOffset = base + t
        }
    }

    /// Group swaps and overlays: one discrete opacity track per member over the cycle.
    private func discrete(_ t: PuppetMotion.Track, cycle: Double) -> [(CALayer, CAKeyframeAnimation)] {
        let names = t.values.map { ($0 as? String) ?? "" }
        let members: [String]
        if t.prop == "member" {
            members = rig.groups[t.layer]?.members ?? Array(Set(names))
        } else {
            members = rig.layers.filter(\.overlay).map(\.name)
        }
        var out: [(CALayer, CAKeyframeAnimation)] = []
        for m in members {
            guard let cl = layerByName[m] else { continue }
            let a = CAKeyframeAnimation(keyPath: "opacity")
            a.values = names.map { $0 == m ? Float(1) : Float(0) }
            a.keyTimes = t.times.map { NSNumber(value: $0 / cycle) } + [1]        // discrete: one more key time than values
            a.calculationMode = .discrete
            a.duration = cycle
            a.repeatCount = .infinity
            a.isRemovedOnCompletion = false
            out.append((cl, a))
        }
        return out
    }

    private static func keyPath(_ prop: String) -> String? {
        switch prop {
        case "rotation": return "transform.rotation.z"
        case "scaleY": return "transform.scale.y"
        case "scaleX": return "transform.scale.x"                              // A4: the signpost's board flip (R3)
        case "translateY": return "transform.translation.y"
        case "translateX": return "transform.translation.x"                    // A4: for data tracks (no shipped track uses it yet)
        default: return nil
        }
    }

    /// A4 (R3's signpost refill): ONE keyframe run on a named layer (or `whole`), on the render server, ADDITIVE over the
    /// looping tracks (the board keeps swaying about its hinge while it flips).
    /// `holdBefore`: the first value holds from now until `begin` (a board stays hidden until its flip).
    func oneShot(layer name: String, prop: String, values: [Double], keyTimes: [Double], curve: String, begin: CFTimeInterval,
                 duration: Double, holdBefore: Bool, key: String) {
        guard let path = Self.keyPath(prop), let target = name == "whole" ? whole : layerByName[name] else { return }
        let a = CAKeyframeAnimation(keyPath: path)
        // an ADDITIVE scale adds to the model's 1 (measured on the sim: 1.0 drew the board twice as wide), so a scale value
        // v is sent as v − 1 (0 → folded, 1 → at rest); rotations and translations add as they are
        let scale = prop.hasPrefix("scale")
        a.values = values.map { Self.number(scale ? $0 - 1 : $0, prop: prop) }
        a.keyTimes = keyTimes.map { NSNumber(value: $0) }
        a.timingFunctions = Array(repeating: Self.timing(curve), count: max(0, values.count - 1))
        a.calculationMode = .linear
        a.isAdditive = true
        a.duration = duration
        a.beginTime = begin
        a.fillMode = holdBefore ? .backwards : .removed
        a.isRemovedOnCompletion = true
        target.add(a, forKey: "\(key).\(name).\(prop)")
    }

    private static func number(_ v: Any, prop: String) -> NSNumber {
        let x = (v as? NSNumber)?.doubleValue ?? 0
        return NSNumber(value: prop == "rotation" ? x * .pi / 180 : x)
    }

    /// sine = easeInOutSine; sineOut / sineIn the quarter-wave halves; easeInOut; linear.
    private static func timing(_ name: String) -> CAMediaTimingFunction {
        switch name {
        case "sine": return CAMediaTimingFunction(controlPoints: 0.37, 0, 0.63, 1)
        case "sineOut": return CAMediaTimingFunction(controlPoints: 0.61, 1, 0.88, 1)
        case "sineIn": return CAMediaTimingFunction(controlPoints: 0.12, 0, 0.39, 0)
        case "easeInOut": return CAMediaTimingFunction(name: .easeInEaseOut)
        case "easeOut": return CAMediaTimingFunction(name: .easeOut)
        case "easeIn": return CAMediaTimingFunction(name: .easeIn)
        default: return CAMediaTimingFunction(name: .linear)
        }
    }

    /// A4 (R3's badge rigs): a raster riding one of the rig's layers — a sublayer of it, so it moves with that layer's
    /// render-server loop (the Rocket Rally rank on the rocket's porthole, the Cloud Hop count on the drum's tag). nil removes it.
    func setRider(_ r: PuppetRider?) {
        guard r?.key != riderKey else { return }
        riderKey = r?.key
        CATransaction.begin(); CATransaction.setDisableActions(true)
        defer { CATransaction.commit() }
        guard let r, let host = layerByName[r.layer], let rect = rig.layer(r.layer)?.rect else {
            riderLayer?.removeFromSuperlayer()
            riderLayer = nil
            return
        }
        let l = riderLayer ?? CALayer()
        l.contents = r.image
        l.contentsScale = r.scale
        l.contentsGravity = .resize
        l.bounds = CGRect(origin: .zero, size: r.size)
        // the host's own coordinates: (0, 0) is its rect's top-left on the frame, whatever its anchor (see `anchor`)
        l.position = CGPoint(x: r.centre.x - rect.minX, y: r.centre.y - rect.minY)
        if l.superlayer !== host { l.removeFromSuperlayer(); host.addSublayer(l) }
        riderLayer = l
    }

    /// Renders the rest pose (no animations) at `scale` — the recompose proof (ShellTests) and ShellLab.
    static func renderRest(_ rig: PuppetRig, scale: CGFloat = 3) -> CGImage? {
        let v = PuppetView(rig: rig, motion: .none, animate: false)
        let size = CGSize(width: rig.frame.width * scale, height: rig.frame.height * scale)
        let fmt = UIGraphicsImageRendererFormat()
        fmt.scale = 1
        fmt.opaque = false
        let img = UIGraphicsImageRenderer(size: size, format: fmt).image { ctx in
            ctx.cgContext.scaleBy(x: scale, y: scale)
            v.layer.render(in: ctx.cgContext)
        }
        return img.cgImage
    }
}
