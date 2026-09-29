import UIKit
import PathCore

// SHELL S2 (SPEC-architecture §6.7, D13) — the win celebration, Core Animation on the FX host (never per-frame SwiftUI).
// LOGO-IMPL (OWNER P0 19:40 (b), SPEC.md rulings 35/36): the logo follows build/logo/LOGO-SPEC.md, measured frame by frame on
// v552 (REFERENCE.md). GAME's WinDirector plays `.celebration(tag)` at W = the clear wave's first frame (`WinDirector.atW`) and
// awaits `fx.finished(handle)`, which returns at W + 4.034 (`win.panelAt`, the win panel's frame). Beats (W +, ui.json `win.*`):
//   0.457  the blue "ARROW" sign enters from the bottom-left (a rim corner first), swings on its pivot (+20.6° at 0.773), settles
//   0.690  the five letters fade in as a lagging chain (flat sprites while they fade), all five swap to their Ext/Face pairs at
//          0.807 (`win.logo.containers.arrowSwap.flatUntil`)
//   0.703  the purple arrow sign turns −146° → 0° growing 0.64 → 1 (sx ≠ sy, bent −8…−10° by 4 contents variants)
//   1.022  "OUT!" (4 glyph pairs in ONE group-opacity container, + its echo 2 frames behind) grows crowded and spreads apart to
//          ≈ 3× at W + 1.305…1.42, then slams back onto its sign
//   1.190  the pegs slide out from behind the blue sign (1.190 → 1.590)
//   1.355  the full-screen dim over the board and the HUD, 0 → 0.894 linear in 0.349 s (under the logo)
//   1.655  confetti (the burst from the bottom, then the rain until the panel) + the first rocket (six, bursts to 3.595)
//   1.688  impact: OUT! is back on its sign → ◉ win on this frame (`win.impactAt`); the whole logo bounces 1 → 0.854 → 1.039 → 1
//          about (196, 425.5) and rests at `celebrate.logo` (no settle scale, no squash)
//   4.018  logo + fireworks removed (the confetti keeps falling)      4.034  finished → the win panel (it takes over the dim)
// Every part is a layer from its OWN art file (UIArt logo* ids; no colour-key split, no in-painting), sized and placed from
// `win.logo.layers` (never UIArt.sizePt), driven by CAKeyframeAnimations baked ONCE behind Loading from the `win.logo` tracks
// (LogoParts.prepare: decode + bake off the main thread, then one invisible render so the first celebration pays nothing).
// Files are never shown above their own pixels (LOGO-SPEC §6: ≤ 0.963 screen px per file px); every layer is trilinear.
// Tap to skip (`CelebrationSkip`, placed by HUDView over the board) = v582 exactly (ruling 40, motion-catalog §11.4, A2 FEEL-P):
// every tap is IGNORED until the logo has landed (`win.skipFrom` W + 1.70: no ripple, no click, no skip); from then a tap cuts
// to the complete win panel on that frame → ♪ uiClick + ◉ button (+ ◉ win if not yet), logo + fireworks gone, dim at 0.894.
// (`win.skipFrom` ≥ `win.panelAt` = no skip at all, ruling 37c literal: one constant.) Silent otherwise (VERIFIED sounds §1).
// Haptic beats (item 7, motion-catalog §5.1 rows 10-14, ruling 39 OD4): ui.json `win.haptics` [[W + t, case, intensity?]] —
// five rising ARROW letter clicks, OUT!'s swell, the slam (◉ win at `impactAt`), the bounce, one soft pop per firework burst;
// each fires once, on the first tick at or after its time, through the arbiter (one per frame); none after a skip.
// `-pc.freezeAt win@t` pins the host layer at exactly W + t; with `-pc.capture 1` the frozen frame logs every part's
// on-screen pose (`[PC][logo] probe …`, LOGO-SPEC §7 A1/A4); `-pc.logoTrace 1` logs the real-time beats (A3).

// MARK: - the logo data (ui.json `win.logo`, LOGO-SPEC §2 / §4)

/// One keyframe track `{kf: [t0, v0, t1, v1, …], ease: […]}` (LOGO-SPEC §2 "easing names"): held before the first key and
/// after the last; `ease[i]` shapes the segment from key i to key i + 1 (build/logo/spec/tools/logo_spec.py `ev`).
struct LogoTrack: Sendable {
    enum Ease: String, Sendable {
        case linear, sineIn, sineOut, sineInOut, quadIn, quadOut, quadInOut, cubicIn, cubicOut, cubicInOut

        func callAsFunction(_ u: Double) -> Double {
            switch self {
            case .linear: return u
            case .sineIn: return 1 - cos(u * .pi / 2)
            case .sineOut: return sin(u * .pi / 2)
            case .sineInOut: return (1 - cos(.pi * u)) / 2
            case .quadIn: return u * u
            case .quadOut: return 1 - (1 - u) * (1 - u)
            case .quadInOut: return u < 0.5 ? 2 * u * u : 1 - 2 * (1 - u) * (1 - u)
            case .cubicIn: return u * u * u
            case .cubicOut: return 1 - (1 - u) * (1 - u) * (1 - u)
            case .cubicInOut: return u < 0.5 ? 4 * u * u * u : 1 - (2 - 2 * u) * (2 - 2 * u) * (2 - 2 * u) / 2
            }
        }
    }

    let times: [Double]
    let values: [Double]
    let eases: [Ease]

    init(times: [Double], values: [Double], eases: [Ease]) {
        self.times = times; self.values = values; self.eases = eases
    }

    static func constant(_ v: Double) -> LogoTrack { LogoTrack(times: [0], values: [v], eases: []) }

    /// Parses `{kf, ease}`; nil when malformed (an odd count, times not increasing, an unknown easing, a wrong ease count).
    init?(_ any: Any?) {
        guard let d = any as? [String: Any], let kf = d["kf"] as? [Any] else { return nil }
        let n = kf.compactMap { ($0 as? NSNumber)?.doubleValue }
        guard n.count == kf.count, n.count >= 2, n.count % 2 == 0 else { return nil }
        let t = stride(from: 0, to: n.count, by: 2).map { n[$0] }
        let v = stride(from: 1, to: n.count, by: 2).map { n[$0] }
        let raw = (d["ease"] as? [Any]) ?? []
        let e = raw.compactMap { ($0 as? String).flatMap(Ease.init(rawValue:)) }
        guard e.count == raw.count, e.count == t.count - 1, zip(t, t.dropFirst()).allSatisfy({ $0 < $1 }) else { return nil }
        self.init(times: t, values: v, eases: e)
    }

    var start: Double { times[0] }
    var end: Double { times[times.count - 1] }

    func callAsFunction(_ t: Double) -> Double {
        let last = times.count - 1
        if t <= times[0] { return values[0] }
        if t >= times[last] { return values[last] }
        var lo = 0, hi = last                                  // the largest i with times[i] <= t
        while hi - lo > 1 {
            let m = (lo + hi) / 2
            if times[m] <= t { lo = m } else { hi = m }
        }
        let u = (t - times[lo]) / (times[lo + 1] - times[lo])
        return values[lo] + (values[lo + 1] - values[lo]) * eases[lo](u)
    }
}

/// `ui.json win.logo` (LOGO-SPEC §2 tables P / L, §4; the block is build/logo/spec/ui_json_win.json's, generated).
struct LogoSpec: Sendable {
    struct Layer: Sendable {
        let id: String
        let part: String
        let container: String         // group | logoSignBlue | outGroup
        let slot: String              // the paint slot: sign | pegs | ext | face (a letter's flat is in its face slot) | fallback
        let role: String              // ext | face | flat for a letter / glyph (its part's `layers`); else the slot
        let z: Double
        let logoRect: CGRect          // fractions of the logoArrowOut canvas
        let bounds: CGSize            // pt
        let anchor: CGPoint           // anchorPoint (fractions of the bounds)
        let position: CGPoint         // rest position in its container (pt)
        let contents: [String]        // the arrow sign's five images (the rest drawing first); else [id]
        let filePx: CGSize?           // the file's pixels (the spec's; tests check the bundle against it)
    }
    struct Part: Sendable {
        let id: String
        let parent: String
        let z: Double
        let visibleFrom: Double
        let anchorPt: CGPoint
        let tracks: [String: LogoTrack]
        let layers: [String: String]  // ext / face / flat
        let flatUntil: Double?
    }
    struct Container: Sendable {
        let id: String
        let z: Double
        let visibleFrom: Double
        let a: LogoTrack?
        let children: [String]
        let delay: Double
        let until: Double
    }

    let groupPivot: CGPoint
    let groupScale: LogoTrack
    let canvas: CGRect
    let parts: [String: Part]
    let layers: [String: Layer]
    let outGroup: Container?
    let outEcho: Container?
    let flatUntil: Double
    let arrowLetters: [String]

    static let arrowOrder = ["logoLetterA", "logoLetterR1", "logoLetterR2", "logoLetterO", "logoLetterW"]
    static let outOrder = ["logoOutO", "logoOutU", "logoOutT", "logoOutBang"]

    init?(_ f: TuningFile) {
        guard let logo = f.value("win.logo") as? [String: Any] else { return nil }
        func num(_ a: Any?) -> Double? { (a as? NSNumber)?.doubleValue }
        func nums(_ a: Any?) -> [Double]? {
            guard let arr = a as? [Any] else { return nil }
            let n = arr.compactMap { ($0 as? NSNumber)?.doubleValue }
            return n.count == arr.count ? n : nil
        }
        guard let gp = nums(logo["groupPivot"]), gp.count == 2,
              let gs = LogoTrack((logo["group"] as? [String: Any])?["s"]),
              let cv = nums((logo["canvas"] as? [String: Any])?["rectPt"]), cv.count == 4,
              let pd = logo["parts"] as? [String: Any], let ld = logo["layers"] as? [String: Any] else { return nil }
        groupPivot = CGPoint(x: gp[0], y: gp[1])
        groupScale = gs
        canvas = CGRect(x: cv[0], y: cv[1], width: cv[2], height: cv[3])
        var parts: [String: Part] = [:]
        for (id, any) in pd {
            guard let p = any as? [String: Any], let parent = p["parent"] as? String, let z = num(p["z"]),
                  let vf = num(p["visibleFrom"]), let ap = nums(p["anchorPt"]), ap.count == 2,
                  let td = p["tracks"] as? [String: Any] else { return nil }
            var tracks: [String: LogoTrack] = [:]
            for (k, v) in td {
                if let tr = LogoTrack(v) {
                    tracks[k] = tr
                } else if let d = v as? [String: Any], let kf = nums(d["kf"]), kf.count == 2 {
                    tracks[k] = .constant(kf[1])                // a single key (logoPegs.a)
                } else {
                    return nil
                }
            }
            parts[id] = Part(id: id, parent: parent, z: z, visibleFrom: vf, anchorPt: CGPoint(x: ap[0], y: ap[1]), tracks: tracks,
                             layers: (p["layers"] as? [String: String]) ?? [:], flatUntil: num(p["flatUntil"]))
        }
        var layers: [String: Layer] = [:]
        for (id, any) in ld {
            guard let l = any as? [String: Any], let part = l["part"] as? String, let container = l["container"] as? String,
                  let z = num(l["z"]), let r = nums(l["logoRect"]), r.count == 4, let b = nums(l["boundsPt"]), b.count == 2,
                  let a = nums(l["anchor"]), a.count == 2, let p = nums(l["positionPt"]), p.count == 2 else { return nil }
            let slot = (l["slot"] as? String) ?? ""
            let roles = ((pd[part] as? [String: Any])?["layers"] as? [String: String]) ?? [:]
            layers[id] = Layer(id: id, part: part, container: container, slot: slot, role: roles.first { $0.value == id }?.key ?? slot, z: z,
                               logoRect: CGRect(x: r[0], y: r[1], width: r[2], height: r[3]), bounds: CGSize(width: b[0], height: b[1]),
                               anchor: CGPoint(x: a[0], y: a[1]), position: CGPoint(x: p[0], y: p[1]),
                               contents: (l["contents"] as? [String]) ?? [id],
                               filePx: nums(l["filePx"]).flatMap { $0.count == 2 ? CGSize(width: $0[0], height: $0[1]) : nil })
        }
        self.parts = parts
        self.layers = layers
        let cd = (logo["containers"] as? [String: Any]) ?? [:]
        func container(_ id: String) -> Container? {
            guard let c = cd[id] as? [String: Any] else { return nil }
            let tracks = c["tracks"] as? [String: Any]
            return Container(id: id, z: num(c["z"]) ?? 7, visibleFrom: num(c["visibleFrom"]) ?? 0, a: LogoTrack(tracks?["a"]),
                             children: (c["children"] as? [String]) ?? [], delay: num(c["delay"]) ?? 0, until: num(c["until"]) ?? .infinity)
        }
        outGroup = container("outGroup")
        outEcho = container("outEcho")
        let swap = cd["arrowSwap"] as? [String: Any]
        arrowLetters = (swap?["letters"] as? [String]) ?? Self.arrowOrder
        flatUntil = num(swap?["flatUntil"]) ?? arrowLetters.compactMap { parts[$0]?.flatUntil }.max() ?? 0.807
    }

    // MARK: the pose (LOGO-SPEC §2 "Composition") — what the baked animations draw, in closed form

    /// A part's own pose at t (before its parent and the group): the anchor's displacement, its axis scales, its rotation (°).
    func local(_ id: String, _ t: Double) -> (dx: Double, dy: Double, sx: Double, sy: Double, rot: Double) {
        guard let p = parts[id] else { return (0, 0, 1, 1, 0) }
        func v(_ k: String, _ d: Double) -> Double { p.tracks[k].map { $0(t) } ?? d }
        let s = v("s", 1)
        return (v("dx", 0), v("dy", 0), v("sx", s), v("sy", s), v("rot", 0))
    }

    /// The part's anchor on the reference canvas (pt), its total scale ((sx + sy) / 2 × the group) and total rotation (°) at t —
    /// the quantities of build/logo/spec/beats.json.
    func screenPose(_ id: String, _ t: Double) -> (x: Double, y: Double, s: Double, rot: Double) {
        guard let p = parts[id] else { return (0, 0, 0, 0) }
        let o = local(id, t)
        var x = p.anchorPt.x + o.dx, y = p.anchorPt.y + o.dy
        var rot = o.rot
        if p.parent == "logoSignBlue", let b = parts["logoSignBlue"] {
            let ob = local(b.id, t)
            let th = ob.rot * .pi / 180
            let qx = x - b.anchorPt.x, qy = y - b.anchorPt.y
            x = b.anchorPt.x + ob.dx + cos(th) * qx - sin(th) * qy
            y = b.anchorPt.y + ob.dy + sin(th) * qx + cos(th) * qy
            rot += ob.rot
        }
        let g = groupScale(t)
        return (groupPivot.x + g * (x - groupPivot.x), groupPivot.y + g * (y - groupPivot.y), g * (o.sx + o.sy) / 2, rot)
    }

    /// The part's EFFECTIVE on-screen opacity at t (beats.json `about_a`): OUT!'s glyphs = outGroup's; a letter = its flat's
    /// before flatUntil, its pair's (1) from it; else its own a from visibleFrom.
    func opacity(_ id: String, _ t: Double) -> Double {
        guard let p = parts[id] else { return 0 }
        if Self.outOrder.contains(id), let g = outGroup {
            return t < g.visibleFrom - 1e-9 ? 0 : (g.a.map { $0(t) } ?? 1)
        }
        if t < p.visibleFrom - 1e-9 { return 0 }
        if arrowLetters.contains(id), t >= flatUntil - 1e-9 { return 1 }
        return p.tracks["a"].map { $0(t) } ?? 1
    }
}

// MARK: - the logo parts: files decoded + tracks baked ONCE, off the main thread

final class LogoParts: @unchecked Sendable {       // immutable after `make`; the templates are only touched on the main actor
    /// One layer of the logo tree, built into a CALayer at every celebration (cheap: the images and the animations are made).
    final class Node {
        var name: String
        var part: String?
        var slot: String?
        var image: CGImage?
        var size: CGSize
        var anchor: CGPoint
        var position: CGPoint
        var transform = CATransform3DIdentity
        /// Table L's per-LAYER z (the only z, orchestrator note 19:56): the layer's zPosition among its siblings.
        var z: Double = 0
        var opacity: Float = 1
        var groupOpacity = false
        /// Animation templates; `begin` = seconds after W (beginTime = t0 + begin is set when the tree is built).
        var anims: [(key: String, anim: CAAnimation, begin: Double)] = []
        var children: [Node] = []

        init(_ name: String, size: CGSize, anchor: CGPoint, position: CGPoint) {
            self.name = name; self.size = size; self.anchor = anchor; self.position = position
        }

        func forEach(_ body: (Node) -> Void) {
            body(self)
            for c in children { c.forEach(body) }
        }
    }

    enum Mode: String { case pairs, oneLayerOut, onePiece }

    let spec: LogoSpec?
    let mode: Mode
    let group: Node
    /// Image id → the decoded file (every file the tree shows, the arrow sign's contents variants included).
    let images: [String: CGImage]

    private init(spec: LogoSpec?, mode: Mode, group: Node, images: [String: CGImage]) {
        self.spec = spec; self.mode = mode; self.group = group; self.images = images
    }

    private static let lock = NSLock()
    nonisolated(unsafe) private static var cached: LogoParts?
    nonisolated(unsafe) private static var started = false

    static var ready: LogoParts? { lock.lock(); defer { lock.unlock() }; return cached }

    /// Decodes every part file (in parallel, off the main thread; S2Hooks.warmUp calls this behind Loading), commits each one once
    /// invisibly while Loading is still up (LogoWarmRender: the image copies and textures are paid there, not at W), then bakes
    /// the tracks into keyframe animations off the main thread and publishes the parts.
    @MainActor static func prepare() {
        lock.lock()
        if started { lock.unlock(); return }
        started = true
        lock.unlock()
        let file = S2Hooks.app?.tuning.ui.file ?? Tuning.load(bundle: .main).ui.file
        Task.detached(priority: .userInitiated) {
            let t0 = ProcessInfo.processInfo.systemUptime
            let spec = LogoSpec(file)
            let (images, mode) = LogoParts.loadImages(spec)
            let t1 = ProcessInfo.processInfo.systemUptime
            await MainActor.run { LogoWarmRender.run(images: images, echo: spec?.outEcho?.children ?? []) }
            // the bake is needed only by the first win: at utility priority, it never competes with Loading's own work
            let baked = await Task.detached(priority: .utility) { LogoParts.assemble(spec, mode: mode, images: images) }.value
            guard let parts = baked else {
                Log.error("fx", "logo parts failed (the logo art is missing): the celebration shows no logo")
                return
            }
            LogoParts.publish(parts)
            Log.mark("warmup", String(format: "logo parts: %d files decoded in %.3f s, %d animations baked in %.3f s (%@)", images.count,
                                      t1 - t0, parts.animationCount, ProcessInfo.processInfo.systemUptime - t1, mode.rawValue))
        }
    }

    private static func publish(_ parts: LogoParts) { lock.lock(); cached = parts; lock.unlock() }

    var animationCount: Int { var n = 0; group.forEach { n += $0.anims.count }; return n }

    /// Loads the files and bakes the animations (any thread; the tests). nil only when not even the one-piece logo exists.
    static func make(_ file: TuningFile, bundle: Bundle = .main) -> LogoParts? {
        let spec = LogoSpec(file)
        let (images, mode) = loadImages(spec, bundle: bundle)
        return assemble(spec, mode: mode, images: images)
    }

    /// Decodes the files the tree shows (the pairs, the flats, the signs, the pegs and the arrow sign's variants; never the
    /// composed round-1/2 ids), 4 at a time. Missing files → the fallbacks (logged): OUT! as ONE layer, or the one-piece logo.
    static func loadImages(_ spec: LogoSpec?, bundle: Bundle = .main) -> ([String: CGImage], Mode) {
        if spec == nil { Log.error("fx", "ui.json win.logo missing or malformed: the one-piece logo at rest") }
        func decode(_ ids: [String]) -> [String: CGImage] {
            let lock = NSLock()
            var out: [String: CGImage] = [:]
            DispatchQueue.concurrentPerform(iterations: ids.count) { i in
                guard let art = UIArt(rawValue: ids[i]), let cg = ArtStore.image(path: art.path, bundle: bundle)?.cgImage else { return }
                lock.lock(); out[ids[i]] = cg; lock.unlock()
            }
            return out
        }
        if let spec {
            let needed = Array(Set(spec.layers.values.filter { $0.part != "logoOut" }.flatMap(\.contents))).sorted()
            var images = decode(needed)
            let missing = needed.filter { images[$0] == nil }
            if missing.isEmpty { return (images, .pairs) }
            Log.error("fx", "logo files missing: \(missing.joined(separator: ", "))")
            let outGlyphs = Set(spec.layers.values.filter { $0.container == "outGroup" }.map(\.id))
            if missing.allSatisfy({ outGlyphs.contains($0) }), let out = decode(["logoOut"])["logoOut"] {
                Log.error("fx", "logo: OUT! falls back to ONE layer (logoOut; LOGO-SPEC table F)")
                images["logoOut"] = out
                return (images, .oneLayerOut)
            }
        }
        Log.error("fx", "logo: the one-piece logoArrowOut at rest (the group bounce only)")
        return (decode(["logoArrowOut"]), .onePiece)
    }

    /// The tree with its baked animations (any thread).
    static func assemble(_ spec: LogoSpec?, mode: Mode, images: [String: CGImage]) -> LogoParts? {
        if let spec, mode != .onePiece {
            return LogoParts(spec: spec, mode: mode, group: tree(spec, mode: mode, images: images), images: images)
        }
        guard let whole = images["logoArrowOut"] else { return nil }
        return LogoParts(spec: spec, mode: .onePiece, group: onePieceTree(spec, whole: whole), images: images)
    }

    // MARK: the tree (LOGO-SPEC §2 "Core Animation recipe")

    static let refSize = CGSize(width: 393, height: 852)

    private static func groupNode(_ spec: LogoSpec?) -> Node {
        let pivot = spec?.groupPivot ?? CGPoint(x: 196, y: 425.5)
        let g = Node("group", size: refSize, anchor: CGPoint(x: pivot.x / refSize.width, y: pivot.y / refSize.height), position: pivot)
        if let s = spec?.groupScale, s.times.count > 1 {
            let (t, v) = bake(s.start, s.end, keys: s.times, tol: [0.0001]) { [s($0)] }
            g.anims.append(keyframes("transform.scale", t, v.map { NSNumber(value: $0[0]) }, fill: .both))
        }
        return g
    }

    private static func tree(_ spec: LogoSpec, mode: Mode, images: [String: CGImage]) -> Node {
        let g = groupNode(spec)
        var motion = MotionCache()                           // one bake per part (+ delay), shared by its Ext / Face / Flat / echo
        var top: [(Double, Node)] = []
        let blueID = "logoSignBlue"
        for p in spec.parts.values where p.parent == "group" {
            switch p.id {
            case "logoOut":
                if mode == .oneLayerOut, let l = spec.layers["logoOut"], let n = layerNode(l, spec: spec, images: images) {
                    animate(n, part: p, spec: spec, opacity: .own, cache: &motion)
                    top.append((l.z, n))
                }
            case let id where LogoSpec.outOrder.contains(id):
                continue                                     // inside outGroup / outEcho (below)
            default:
                guard let l = spec.layers.values.first(where: { $0.part == p.id }), let n = layerNode(l, spec: spec, images: images) else { continue }
                animate(n, part: p, spec: spec, opacity: .own, cache: &motion)
                if p.id == "logoSignPurple" { bendContents(n, part: p, layer: l, images: images) }
                if p.id == blueID {
                    // the letters: every Ext under every Face (the one-piece's paint order), the flat in its Face slot
                    let letterLayers = spec.layers.values.filter { $0.container == blueID }.sorted { ($0.z, $0.role) < ($1.z, $1.role) }
                    for ll in letterLayers {
                        guard let lp = spec.parts[ll.part], let ln = layerNode(ll, spec: spec, images: images) else { continue }
                        animate(ln, part: lp, spec: spec, opacity: ll.role == "flat" ? .flat(spec.flatUntil) : .pair(spec.flatUntil),
                                cache: &motion)
                        n.children.append(ln)
                    }
                }
                top.append((l.z, n))
            }
        }
        if mode == .pairs {
            let glyphLayers = spec.layers.values.filter { $0.container == "outGroup" }.sorted { $0.z < $1.z }
            if let c = spec.outEcho {
                // the echo: ONE group-opacity container of delayed copies (LOGO-SPEC-FIX L2: its own opacity track)
                let e = containerNode(c)
                for gl in glyphLayers {
                    guard let gp = spec.parts[gl.part], let n = layerNode(gl, spec: spec, images: images) else { continue }
                    n.name = "echo:" + gl.id
                    animate(n, part: gp, spec: spec, opacity: .none, delay: c.delay, cache: &motion)
                    e.children.append(n)
                }
                top.append((c.z, e))
            }
            let o = containerNode(spec.outGroup ?? LogoSpec.Container(id: "outGroup", z: 7, visibleFrom: 1.022, a: nil, children: [],
                                                                      delay: 0, until: .infinity))
            for gl in glyphLayers {
                guard let gp = spec.parts[gl.part], let n = layerNode(gl, spec: spec, images: images) else { continue }
                animate(n, part: gp, spec: spec, opacity: .none, cache: &motion)
                o.children.append(n)
            }
            top.append((spec.outGroup?.z ?? 7, o))
        }
        g.children = top.sorted { $0.0 < $1.0 }.map(\.1)
        return g
    }

    /// No usable parts: the one-piece logo at the canvas, fading in with the blue sign's beat, with the group bounce only.
    private static func onePieceTree(_ spec: LogoSpec?, whole: CGImage) -> Node {
        let g = groupNode(spec)
        let c = spec?.canvas ?? CGRect(x: 45.1011, y: 293.2133, width: 308.0345, height: 237.5691)
        let n = Node("logoArrowOut", size: c.size, anchor: CGPoint(x: 0.5, y: 0.5), position: CGPoint(x: c.midX, y: c.midY))
        n.image = whole
        n.part = "logoArrowOut"
        n.opacity = 0
        n.anims.append(keyframes("opacity", [0.457, 0.6], [NSNumber(value: 0), NSNumber(value: 1)], fill: .forwards))
        g.children = [n]
        return g
    }

    private static func layerNode(_ l: LogoSpec.Layer, spec: LogoSpec, images: [String: CGImage]) -> Node? {
        guard let img = images[l.contents.first ?? l.id] else { return nil }
        let n = Node(l.id, size: l.bounds, anchor: l.anchor, position: l.position)
        n.image = img
        n.z = l.z
        n.part = l.part
        n.slot = l.role
        return n
    }

    private static func containerNode(_ c: LogoSpec.Container) -> Node {
        let n = Node(c.id, size: refSize, anchor: CGPoint(x: 0.5, y: 0.5), position: CGPoint(x: refSize.width / 2, y: refSize.height / 2))
        n.groupOpacity = true                        // ruling 36 (a): the 8 layers composite first, then fade as one
        n.part = c.id
        n.z = c.z
        if let a = c.a {
            n.opacity = 0
            let from = max(a.start, c.visibleFrom)
            let (t, v) = bake(from, a.end, keys: a.times, tol: [0.003]) { [a($0)] }
            // outEcho ends at 0 on `until` (fill: none → 0 after); outGroup holds its last value (1)
            n.anims.append(keyframes("opacity", t, v.map { NSNumber(value: $0[0]) }, fill: c.until.isFinite ? .removed : .forwards))
        }
        return n
    }

    private enum OpacityRule { case own, flat(Double), pair(Double), none }

    /// A part's baked position / transform animations and their model values, keyed by part + delay + rest position.
    private struct Motion {
        var anims: [(key: String, anim: CAAnimation, begin: Double)] = []
        var position: CGPoint?
        var transform: CATransform3D?
    }
    private typealias MotionCache = [String: Motion]

    /// The part's tracks as keyframe animations on one of its layers (a pair's two layers and its flat get the same ones: the
    /// motion is baked once per part and the templates are shared; `add` copies them).
    private static func animate(_ n: Node, part p: LogoSpec.Part, spec: LogoSpec, opacity rule: OpacityRule, delay: Double = 0,
                                cache: inout MotionCache) {
        let tr = p.tracks
        let key = "\(p.id)|\(delay)|\(n.position.x),\(n.position.y)"
        if cache[key] == nil {
            var m = Motion()
            let posKeys = ["dx", "dy"].compactMap { tr[$0] }
            if !posKeys.isEmpty {
                let a = posKeys.map(\.start).min()!, b = posKeys.map(\.end).max()!
                let dx = tr["dx"], dy = tr["dy"]
                let rest = n.position
                let (t, v) = bake(a, b, keys: posKeys.flatMap(\.times), tol: [0.04, 0.04]) { x in [dx.map { $0(x) } ?? 0, dy.map { $0(x) } ?? 0] }
                m.anims.append(keyframes("position", t, v.map { NSValue(cgPoint: CGPoint(x: rest.x + $0[0], y: rest.y + $0[1])) }, fill: .both, delay: delay))
                m.position = CGPoint(x: rest.x + (dx.map { $0(b) } ?? 0), y: rest.y + (dy.map { $0(b) } ?? 0))
            }
            let tfKeys = ["s", "sx", "sy", "rot"].compactMap { tr[$0] }
            if !tfKeys.isEmpty {
                let a = tfKeys.map(\.start).min()!, b = tfKeys.map(\.end).max()!
                let s = tr["s"], sx = tr["sx"] ?? s, sy = tr["sy"] ?? s, rot = tr["rot"]    // resolved once, not per sample
                let f: (Double) -> [Double] = { t in [sx.map { $0(t) } ?? 1, sy.map { $0(t) } ?? 1, rot.map { $0(t) } ?? 0] }
                let (t, v) = bake(a, b, keys: tfKeys.flatMap(\.times), tol: [0.0004, 0.0004, 0.04], maxStep: [.infinity, .infinity, 45], f)
                m.anims.append(keyframes("transform", t, v.map { NSValue(caTransform3D: transform($0)) }, fill: .both, delay: delay))
                m.transform = transform(f(b))
            }
            cache[key] = m
        }
        let m = cache[key]!
        n.anims += m.anims
        if let pos = m.position { n.position = pos }
        if let tf = m.transform { n.transform = tf }
        switch rule {
        case .none:
            n.opacity = 1                               // inside a group-opacity container: always 1
        case .own:
            n.opacity = 0
            let a = tr["a"] ?? .constant(1)
            let from = p.visibleFrom, to = max(a.end, from + 1.0 / 120)
            let (t, v) = bake(from, to, keys: a.times, tol: [0.003]) { [a($0)] }
            n.anims.append(keyframes("opacity", t, v.map { NSNumber(value: $0[0]) }, fill: .forwards, delay: delay))
        case .flat(let until):
            // the letter's a on its flat until the ONE swap (LOGO-SPEC-FIX L1), then 0 (fill: none → the model's 0)
            n.opacity = 0
            let a = tr["a"] ?? .constant(1)
            let from = p.visibleFrom
            guard until > from else { break }
            let (t, v) = bake(from, until, keys: a.times.filter { $0 < until }, tol: [0.003]) { [a($0)] }
            n.anims.append(keyframes("opacity", t, v.map { NSNumber(value: $0[0]) }, fill: .removed, delay: delay))
        case .pair(let until):
            // hidden until the swap, then exactly 1 (never translucent: ruling 36)
            n.opacity = 0
            n.anims.append(keyframes("opacity", [until, until + 1.0 / 120], [NSNumber(value: 1), NSNumber(value: 1)], fill: .forwards, delay: delay))
        }
    }

    /// The arrow sign's bend (LOGO-SPEC-FIX M3): ONLY `contents` changes — the nearest of the rest drawing and the four variants
    /// (−2.5 … −10°), discrete; bounds, anchorPoint and position never move.
    private static func bendContents(_ n: Node, part p: LogoSpec.Part, layer l: LogoSpec.Layer, images: [String: CGImage]) {
        guard let bend = p.tracks["bend"], bend.times.count > 1, l.contents.count > 1 else { return }
        let imgs = l.contents.compactMap { images[$0] }
        guard imgs.count == l.contents.count else { return }
        func index(_ t: Double) -> Int { max(0, min(imgs.count - 1, Int((-bend(t) / 2.5).rounded()))) }
        let a = max(bend.start, p.visibleFrom), b = bend.end
        var times = [a], idx = [index(a)]
        var t = a
        while t < b {                                   // 1 ms steps: the switch times to the millisecond
            t = min(b, t + 0.001)
            let i = index(t)
            if i != idx.last! { times.append(t); idx.append(i) }
        }
        guard idx.count > 1 || idx[0] != 0 else { return }
        let end = max(b, times.last! + 0.001)
        let anim = CAKeyframeAnimation(keyPath: "contents")
        anim.values = idx.map { imgs[$0] }
        anim.keyTimes = (times + [end]).map { NSNumber(value: ($0 - a) / (end - a)) }
        anim.calculationMode = .discrete
        anim.duration = end - a
        anim.fillMode = .both
        anim.isRemovedOnCompletion = false
        n.anims.append((key: "bend", anim: anim, begin: a))
    }

    /// R(rot) · diag(sx, sy): scale along the part's own axes, then rotate (+ = clockwise on screen).
    static func transform(_ v: [Double]) -> CATransform3D {
        CATransform3DScale(CATransform3DMakeRotation(CGFloat(v[2] * .pi / 180), 0, 0, 1), CGFloat(v[0]), CGFloat(v[1]), 1)
    }

    /// Samples `f` over [a, b] (every 1/2400 s + the track keys: some fitted segments turn hard, e.g. R2's cubicInOut 27 pt in
    /// 17 ms, so a 480 Hz grid would miss up to 1.2 pt between its samples; 2400 Hz ≤ 0.05) and keeps the points linear
    /// interpolation needs to stay within `tol` per dimension (Ramer–Douglas–Peucker). Returns the kept times and values.
    static func bake(_ a: Double, _ b: Double, keys: [Double], tol: [Double], maxStep: [Double]? = nil,
                     _ f: (Double) -> [Double]) -> ([Double], [[Double]]) {
        guard b > a else { return ([a], [f(a)]) }
        var ts = Set(keys.filter { $0 > a && $0 < b })
        let n = Int(((b - a) * 2400).rounded(.up))
        for i in 0...n { ts.insert(min(b, a + Double(i) / 2400)) }
        ts.insert(a); ts.insert(b)
        let t = ts.sorted()
        let v = t.map(f)
        var keep = [Bool](repeating: false, count: t.count)
        keep[0] = true; keep[t.count - 1] = true
        var stack = [(0, t.count - 1)]
        while let (i, j) = stack.popLast() {
            guard j - i > 1 else { continue }
            var worst = 0.0, at = -1
            for k in (i + 1)..<j {
                let u = (t[k] - t[i]) / (t[j] - t[i])
                var e = 0.0
                for d in 0..<tol.count { e = max(e, abs(v[i][d] + (v[j][d] - v[i][d]) * u - v[k][d]) / tol[d]) }
                if e > worst { worst = e; at = k }
            }
            // a transform key may not turn more than `maxStep` from the one before: CA interpolates a rotation along the
            // shorter arc, so a longer step (the blue sign turns 180° in 0.3 s) would spin the wrong way
            if let maxStep, worst <= 1, (0..<maxStep.count).contains(where: { abs(v[j][$0] - v[i][$0]) > maxStep[$0] }) {
                worst = 2; at = (i + j) / 2
            }
            if worst > 1, at > 0 {
                keep[at] = true
                stack.append((i, at)); stack.append((at, j))
            }
        }
        var kt: [Double] = [], kv: [[Double]] = []
        for k in 0..<t.count where keep[k] { kt.append(t[k]); kv.append(v[k]) }
        return (kt, kv)
    }

    static func keyframes(_ key: String, _ t: [Double], _ values: [Any], fill: CAMediaTimingFillMode,
                          delay: Double = 0) -> (key: String, anim: CAAnimation, begin: Double) {
        let anim = CAKeyframeAnimation(keyPath: key)
        let a = t[0], span = max(t[t.count - 1] - a, 1e-4)
        anim.values = values
        anim.keyTimes = t.map { NSNumber(value: ($0 - a) / span) }
        anim.calculationMode = .linear
        anim.duration = span
        anim.fillMode = fill
        anim.isRemovedOnCompletion = false
        return (key: key, anim: anim, begin: a + delay)
    }

    // MARK: building

    /// A fresh CALayer tree from the nodes; animations begin at `t0` (the host's local time of W) + their offsets.
    @MainActor func build(t0: CFTimeInterval, into registry: inout [(node: Node, layer: CALayer)]) -> CALayer {
        func make(_ n: Node) -> CALayer {
            let l = CALayer()
            l.name = n.name
            l.bounds = CGRect(origin: .zero, size: n.size)
            l.anchorPoint = n.anchor
            l.position = n.position
            l.transform = n.transform
            l.zPosition = CGFloat(n.z)
            l.opacity = n.opacity
            l.allowsGroupOpacity = n.groupOpacity
            if let img = n.image {
                l.contents = img
                l.contentsGravity = .resize
                l.contentsScale = 3
                l.minificationFilter = .trilinear
                l.magnificationFilter = .linear
            }
            for a in n.anims {
                a.anim.beginTime = t0 + a.begin
                l.add(a.anim, forKey: a.key)
            }
            registry.append((n, l))
            for c in n.children { l.addSublayer(make(c)) }
            return l
        }
        return make(group)
    }
}

/// The first-celebration warm-up (SPEC-architecture §10.2 "no first-presentation stall", LOGO-SPEC §2 "warm-up"; orchestrator
/// note 19:56 (4)): every part file — each contents image of the arrow sign, every flat, pair and sign — is drawn once at a
/// non-zero opacity (1 %, a quarter of its size so its trilinear mipmaps are made), plus one echo copy (the 8 OUT! files in a
/// group-opacity container), in the FX host while the opaque Loading screen is still up. Staged, 6 files a frame, so no
/// Loading frame carries every image copy; all of it leaves 2 frames after the last. Skipped when Loading is already gone
/// (never during play): the first celebration then commits the files itself (logged).
@MainActor enum LogoWarmRender {
    private(set) static var done = false

    static func run(images: [String: CGImage], echo: [String]) {
        guard !done, let app = S2Hooks.app, app.router.screen == .loading, let fx = app.fx as? FXOverlay else {
            if !done { Log.mark("warmup", "logo warm render skipped (Loading is gone: the first celebration commits the files)") }
            return
        }
        done = true
        let host = fx.hostView.layer
        let root = CALayer()
        root.allowsGroupOpacity = false
        func sprite(_ img: CGImage, _ x: CGFloat, opacity: Float) -> CALayer {
            let l = CALayer()
            l.contents = img
            l.contentsGravity = .resize
            l.minificationFilter = .trilinear
            l.magnificationFilter = .linear
            l.opacity = opacity
            l.frame = CGRect(x: x, y: 0, width: CGFloat(img.width) / 12, height: CGFloat(img.height) / 12)
            return l
        }
        let files = images.sorted { $0.key < $1.key }
        Task { @MainActor in
            var cost = 0.0, x: CGFloat = 0
            for start in stride(from: 0, to: files.count, by: 6) {
                let t = ProcessInfo.processInfo.systemUptime
                CATransaction.begin(); CATransaction.setDisableActions(true)
                if root.superlayer == nil { root.frame = host.bounds; host.addSublayer(root) }
                for (_, img) in files[start..<min(files.count, start + 6)] {
                    root.addSublayer(sprite(img, x, opacity: 0.01))
                    x += 4
                }
                CATransaction.commit()
                cost = max(cost, ProcessInfo.processInfo.systemUptime - t)
                await FrameWaiter.frames(1)
            }
            let t = ProcessInfo.processInfo.systemUptime
            CATransaction.begin(); CATransaction.setDisableActions(true)
            let group = CALayer()
            group.frame = host.bounds
            group.allowsGroupOpacity = true
            group.opacity = 0.01
            for id in echo { if let img = images[id] { group.addSublayer(sprite(img, x, opacity: 1)); x += 4 } }
            root.addSublayer(group)
            CATransaction.commit()
            cost = max(cost, ProcessInfo.processInfo.systemUptime - t)
            await FrameWaiter.frames(2)
            CATransaction.begin(); CATransaction.setDisableActions(true)
            root.removeFromSuperlayer()
            CATransaction.commit()
            Log.mark("warmup", String(format: "logo warm render: %d files + one echo copy drawn under Loading (worst commit %.1f ms)",
                                      files.count, cost * 1000))
        }
    }
}

// MARK: - one celebration

@MainActor final class CelebrationRun: NSObject {
    let handle: FXHandle
    let tag: LevelTag
    private weak var host: CALayer?
    private let clock: MotionClock
    private let app: AppModel?
    private let ui: UITuning
    private let root = CALayer()
    fileprivate let dim = CALayer()
    fileprivate let fireworkRoot = CALayer()
    fileprivate let confettiRoot = CALayer()
    fileprivate let logoRoot = CALayer()
    private let flashRoot = CALayer()
    private var link: CADisplayLink?
    private var waiters: [CheckedContinuation<Void, Never>] = []
    private let startGame: Double
    private let t0: CFTimeInterval                    // host local time of W
    private var rng: PathRandom
    private let confetti: ConfettiSpec
    private let fireworks: FireworkSpec
    private let beats: Beats
    private var burstDone = false
    private var burstBuilt = 0
    private var rainEmitted = 0
    private var rocketsBuilt = 0
    private var winHaptic = false
    private var nextBeat = 0                        // A2: the next `win.haptics` beat
    private var logoBuilt = false
    private var logoCleared = false
    private(set) var panelDue = false
    private var skipped = false
    private var endAt: Double = .infinity
    private var logoParts: LogoParts?
    private var logoLayers: [(node: LogoParts.Node, layer: CALayer)] = []
    private var frozenTicks = 0
    private var trace: LogoTrace?
    var onEnd: (() -> Void)?

    /// The celebration's beats (ui.json `win.*`; LOGO-SPEC §1 / §5.2 — REFERENCE §2 / §8, W = the clear wave's first frame).
    /// The logo's own motion is `win.logo` (LogoSpec).
    struct Beats {
        var impactAt = 1.688, dimAt = 1.355, dimDur = 0.349, dim = 0.894, confettiAt = 1.655
        var rockets: [Double] = [1.655, 1.905, 2.075, 2.275, 2.525, 2.875], bursts: [Double] = [2.365, 2.565, 2.765, 2.965, 3.195, 3.595]
        /// `skipFrom` 1.70 = ruling 40 (v582: taps ignored until the logo has landed; was 0.41).
        var clearAt = 4.018, panelAt = 4.034, skipFrom = 1.70
        /// FEEL item 2: the confetti burst and the rockets are built ahead from here, `burstPerFrame` pieces a frame.
        var prebuildFrom = 0.10, burstPerFrame = 10
        /// A2 (motion-catalog §5.2): the haptic beats, W + t, sorted; nil intensity = the case's audio.json row.
        struct HapticBeat: Equatable { var t: Double; var haptic: Haptic; var intensity: Double? }
        var haptics: [HapticBeat] = Beats.specHaptics
        static let specHaptics: [HapticBeat] = [
            HapticBeat(t: 0.815, haptic: .logoLetter, intensity: 0.55), HapticBeat(t: 0.848, haptic: .logoLetter, intensity: 0.58),
            HapticBeat(t: 0.881, haptic: .logoLetter, intensity: 0.62), HapticBeat(t: 0.914, haptic: .logoLetter, intensity: 0.66),
            HapticBeat(t: 0.947, haptic: .logoLetter, intensity: 0.70), HapticBeat(t: 1.139, haptic: .logoSwell, intensity: nil),
            HapticBeat(t: 1.688, haptic: .win, intensity: nil), HapticBeat(t: 1.828, haptic: .logoBounce, intensity: nil),
            HapticBeat(t: 2.365, haptic: .firework, intensity: nil), HapticBeat(t: 2.565, haptic: .firework, intensity: nil),
            HapticBeat(t: 2.765, haptic: .firework, intensity: nil), HapticBeat(t: 2.965, haptic: .firework, intensity: nil),
            HapticBeat(t: 3.195, haptic: .firework, intensity: nil), HapticBeat(t: 3.595, haptic: .firework, intensity: nil),
        ]

        init(_ f: TuningFile) {
            impactAt = f.double("win.impactAt", impactAt)
            dimAt = f.double("win.dimAt", dimAt); dimDur = f.double("win.dimDur", dimDur); dim = f.double("win.dim", dim)
            confettiAt = f.double("win.confettiAt", confettiAt)
            let r = f.doubles("win.rockets", rockets), b = f.doubles("win.bursts", bursts)
            if r.count == b.count, !r.isEmpty { rockets = r; bursts = b }
            clearAt = f.double("win.clearAt", clearAt); panelAt = f.double("win.panelAt", panelAt); skipFrom = f.double("win.skipFrom", skipFrom)
            prebuildFrom = f.double("win.prebuildFrom", prebuildFrom)
            burstPerFrame = max(1, Int(f.double("win.burstPerFrame", Double(burstPerFrame))))
            if let rows = f.value("win.haptics") as? [[Any]] {
                haptics = rows.compactMap { r -> HapticBeat? in
                    guard r.count >= 2, let t = (r[0] as? NSNumber)?.doubleValue, let name = r[1] as? String,
                          let h = Haptic(rawValue: name) else { return nil }
                    return HapticBeat(t: t, haptic: h, intensity: r.count > 2 ? (r[2] as? NSNumber)?.doubleValue : nil)
                }.sorted { $0.t < $1.t }
            }
        }
    }

    init(handle: FXHandle, tag: LevelTag, host: CALayer, clock: MotionClock, ui: UITuning, app: AppModel?, seed: UInt64) {
        self.handle = handle
        self.tag = tag
        self.host = host
        self.clock = clock
        self.ui = ui
        self.app = app
        self.startGame = clock.gameTime()
        self.t0 = host.convertTime(CACurrentMediaTime(), from: nil)
        self.rng = PathRandom(seed: seed)
        self.confetti = ConfettiSpec(ui.tokens)
        self.fireworks = FireworkSpec(ui.tokens)
        self.beats = Beats(ui.file)
        super.init()
        build()
    }

    var bounds: CGRect { host?.bounds ?? CGRect(x: 0, y: 0, width: 393, height: 852) }

    /// Game seconds since W (the win sequence's local time; `-pc.freezeAt win@t` holds it at t).
    var elapsed: Double { clock.sequenceTime("win", clock.gameTime() - startGame) }

    private func build() {
        let b = bounds
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for l in [root, dim, fireworkRoot, confettiRoot, logoRoot, flashRoot] { l.frame = b }
        root.addSublayer(dim)
        root.addSublayer(fireworkRoot)
        root.addSublayer(confettiRoot)
        root.addSublayer(logoRoot)
        root.addSublayer(flashRoot)
        dim.backgroundColor = UIColor.black.cgColor
        dim.opacity = 0
        let d = CABasicAnimation(keyPath: "opacity")
        d.fromValue = 0
        d.toValue = beats.dim
        d.beginTime = t0 + beats.dimAt
        d.duration = beats.dimDur
        d.fillMode = .both
        d.isRemovedOnCompletion = false
        dim.add(d, forKey: "dim")
        // the logo + fireworks removal on the render timeline at exactly W + 4.018 (LOGO-SPEC §1; the tick's clearLogo() is
        // up to a frame later and only keeps the state — a skip still clears at once)
        for l in [logoRoot, fireworkRoot, flashRoot] {
            let hide = CABasicAnimation(keyPath: "hidden")
            hide.fromValue = true
            hide.toValue = true
            hide.beginTime = t0 + beats.clearAt
            hide.duration = 3600
            hide.fillMode = .forwards
            hide.isRemovedOnCompletion = false
            l.add(hide, forKey: "clear")
        }
        host?.addSublayer(root)
        CATransaction.commit()
        logoParts = LogoParts.ready
        if logoParts == nil { LogoParts.prepare() }       // normally made behind Loading; built as soon as they are ready
        if app?.args.raw["pc.logoTrace"] != nil { trace = LogoTrace() }
        let l = CADisplayLink(target: self, selector: #selector(tick))
        l.add(to: .main, forMode: .common)
        link = l
        Log.mark("fx", "celebration \(tag.rawValue) start (logo parts \(logoParts.map { "ready: \($0.mode.rawValue)" } ?? "not ready: no logo"))")
    }

    // MARK: logo

    /// The logo tree (LOGO-SPEC §2): refCanvas (the reference 393 × 852 pt, scaled like the popups) ⊃ group ⊃ the parts.
    /// Built on the first frame after W (the logo is invisible until W + 0.457), from the parts made behind Loading.
    private func buildLogo() {
        guard let parts = logoParts else { return }
        logoBuilt = true
        let b = bounds
        let k = min(1, b.width / 393, b.height / 852)
        let t = ProcessInfo.processInfo.systemUptime
        CATransaction.begin(); CATransaction.setDisableActions(true)
        let canvas = CALayer()
        canvas.bounds = CGRect(origin: .zero, size: LogoParts.refSize)
        canvas.position = CGPoint(x: b.midX, y: b.midY)
        canvas.transform = CATransform3DMakeScale(k, k, 1)
        canvas.addSublayer(parts.build(t0: t0, into: &logoLayers))
        logoRoot.addSublayer(canvas)
        CATransaction.commit()
        Log.mark("fx", String(format: "celebration logo built W+%.3f (%d layers, %.2f ms)", elapsed, logoLayers.count,
                              (ProcessInfo.processInfo.systemUptime - t) * 1000))
    }

    // MARK: the clock

    @objc private func tick() {
        let e = elapsed
        if !logoBuilt && !logoCleared {
            if logoParts == nil { logoParts = LogoParts.ready }
            if logoParts != nil { buildLogo() }
        }
        if !armedNoted && e >= beats.skipFrom { armedNoted = true; CelebrationState.shared.update() }
        if clock.isFrozen, let f = clock.frozenAt, f.sequence == "win", let host {
            host.timeOffset = t0 + f.t          // pin the render server exactly at W + t
            frozenTicks += 1
            if frozenTicks == 2, app?.args.capture == true { logoProbe(f.t) }
        }
        if let trace, !clock.isFrozen, let host { trace.tick(self, time: host.convertTime(CACurrentMediaTime(), from: nil) - t0) }
        // A2: the haptic beats due now (one per frame through the arbiter; none after a skip or once the logo is gone)
        while nextBeat < beats.haptics.count && e >= beats.haptics[nextBeat].t {
            let b = beats.haptics[nextBeat]
            nextBeat += 1
            guard !skipped, !logoCleared, !clock.isFrozen else { continue }
            if b.haptic == .win {
                if !winHaptic { fireWinHaptic() }
                continue
            }
            if let i = b.intensity { app?.haptics.play(b.haptic, intensity: i) } else { app?.haptics.play(b.haptic) }
            Log.mark("fx", "celebration haptic \(b.haptic.rawValue)\(b.intensity.map { String(format: " %.2f", $0) } ?? "") planned W+"
                     + String(format: "%.3f at W+%.3f", b.t, e))
        }
        if !winHaptic && e >= beats.impactAt { fireWinHaptic() }
        // FEEL item 2: the 140-piece burst was built in ONE frame (a 33 ms frame on every win, G1) and each rocket's 48 sparks in
        // the frame 0.12 s before its launch. Every piece is invisible until its own begin time (model opacity 0, fill
        // forwards), so they are built ahead, a few per frame, from W + 0.10: nothing is built in the dim / confetti / impact
        // frames.
        if !burstDone && e >= min(beats.prebuildFrom, beats.confettiAt - 0.12) { buildBurst(upTo: beats.burstPerFrame) }
        if e >= beats.confettiAt - 0.1 && !panelDue && !skipped {
            let due = Int((min(e, beats.panelAt) + 0.1 - beats.confettiAt) * confetti.rainPerS)
            while rainEmitted < due { emitRain() }
        }
        if burstDone && rocketsBuilt < beats.rockets.count && !logoCleared
            && (e >= beats.prebuildFrom || e >= beats.rockets[rocketsBuilt] - 0.12) {
            buildRocket(rocketsBuilt)                                   // one rocket per frame once the burst is built
        }
        while rocketsBuilt < beats.rockets.count && e >= beats.rockets[rocketsBuilt] - 0.12 && !logoCleared { buildRocket(rocketsBuilt) }
        if !logoCleared && e >= beats.clearAt { clearLogo() }
        if !panelDue && e >= beats.panelAt { reachPanel() }
        if e >= endAt { end() }
    }

    private func fireWinHaptic() {
        winHaptic = true
        app?.haptics.play(.win)
        Log.mark("fx", "celebration slam (◉ win) W+\(String(format: "%.3f", elapsed))")
    }

    /// Builds up to `n` more burst pieces (all of them when the confetti is due: a skip or a slow start never loses any).
    private func buildBurst(upTo n: Int) {
        let e = elapsed
        let count = e >= beats.confettiAt - 0.12 ? confetti.burst - burstBuilt : min(n, confetti.burst - burstBuilt)
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for _ in 0..<max(0, count) {
            confettiRoot.addSublayer(Confetti.burstPiece(&rng, spec: confetti, bounds: bounds, begin: t0 + beats.confettiAt))
        }
        CATransaction.commit()
        burstBuilt += max(0, count)
        if burstBuilt >= confetti.burst { burstDone = true }
    }

    private func emitRain() {
        let at = t0 + beats.confettiAt + Double(rainEmitted) / max(1, confetti.rainPerS)
        rainEmitted += 1
        CATransaction.begin(); CATransaction.setDisableActions(true)
        confettiRoot.addSublayer(Confetti.rainPiece(&rng, spec: confetti, bounds: bounds, begin: at))
        CATransaction.commit()
    }

    private func buildRocket(_ i: Int) {
        rocketsBuilt += 1
        let b = bounds
        let k = min(1, b.width / 393)
        let x = fireworks.launchX[i % fireworks.launchX.count]
        let from = CGPoint(x: b.midX + CGFloat(x - 196.5) * k, y: b.maxY + 10)
        let to = CGPoint(x: from.x + CGFloat((rng.unit() * 2 - 1) * 40) * k, y: layoutRect(CGRect(0, rng.double(in: 190...330), 1, 1)).minY)
        let launch = t0 + beats.rockets[i], burst = t0 + beats.bursts[i]
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for l in Fireworks.rocket(from: from, to: to, launch: launch, burst: burst, trail: CGFloat(rng.double(in: 200...260))) {
            fireworkRoot.addSublayer(l)
        }
        for l in Fireworks.burst(at: to, begin: burst, spec: fireworks, rng: &rng) { fireworkRoot.addSublayer(l) }
        flashRoot.addSublayer(Fireworks.screenFlash(bounds: b, begin: burst, peak: fireworks.flash))
        CATransaction.commit()
    }

    /// A reference-canvas rect mapped like the popups (centre-anchored, SPEC-ui §1.1).
    private func layoutRect(_ r: CGRect) -> CGRect {
        let b = bounds
        let k = min(1, b.width / 393, b.height / 852)
        return CGRect(x: (b.width - 393 * k) / 2 + r.minX * k, y: (b.height - 852 * k) / 2 + r.minY * k, width: r.width * k, height: r.height * k)
    }

    private func clearLogo() {
        logoCleared = true
        CATransaction.begin(); CATransaction.setDisableActions(true)
        logoRoot.isHidden = true
        fireworkRoot.isHidden = true
        flashRoot.isHidden = true
        CATransaction.commit()
    }

    private func reachPanel() {
        panelDue = true
        Log.mark("fx", "celebration panel due W+\(String(format: "%.3f", elapsed))\(skipped ? " (skipped)" : "")")
        let w = waiters
        waiters.removeAll()
        for c in w { c.resume() }
        endAt = elapsed + 2.6                 // the live confetti finishes falling behind the panel
    }

    /// Returns at the panel's beat (W + 4.034, or the skip).
    func finished() async {
        if panelDue { return }
        await withCheckedContinuation { (c: CheckedContinuation<Void, Never>) in
            if panelDue { c.resume() } else { waiters.append(c) }
        }
    }

    /// Tap to skip (ruling 40): from W + 1.70 (the logo has landed), the logo and the fireworks go, the dim jumps to 0.894, the
    /// panel is due now, with the UI click and the button haptic; an earlier tap does nothing at all.
    @discardableResult
    func skip(fromTap: Bool) -> Bool {
        guard !panelDue else { return false }
        let e = elapsed
        if fromTap && (e < beats.skipFrom || beats.skipFrom >= beats.panelAt) {
            Log.mark("fx", "celebration tap ignored at W+\(String(format: "%.3f", e)) (skip from W+\(String(format: "%.2f", beats.skipFrom)))")
            return false
        }
        skipped = true
        if fromTap, let app, let cue = app.tuning.audio.cue("celebrationSkip") ?? app.tuning.audio.cue("uiButton") {
            app.audio.play(cue, gain: Float(app.tuning.audio.gain(cue)))
        }
        if fromTap { app?.haptics.play(.button) }                            // A2: the click's haptic (§5.1 row 16)
        if !winHaptic { fireWinHaptic() }
        clearLogo()
        CATransaction.begin(); CATransaction.setDisableActions(true)
        dim.removeAnimation(forKey: "dim")
        dim.opacity = Float(beats.dim)
        CATransaction.commit()
        Log.mark("fx", "celebration skipped at W+\(String(format: "%.3f", e))")
        reachPanel()
        return true
    }

    /// The win panel is on screen with its own 0.90 dim: drop ours on the same frame.
    /// FIX-2 A-R (UI tests only, `shell.warmProbe`): the dim's opacity as drawn now.
    var dimOpacity: Float { dim.presentation()?.opacity ?? dim.opacity }

    func handOverDim() {
        CATransaction.begin(); CATransaction.setDisableActions(true)
        dim.removeAllAnimations()
        dim.opacity = 0
        CATransaction.commit()
    }

    var isSkippable: Bool { !panelDue }
    /// A tap now skips (W + 1.70 … the panel; ruling 40).
    var isArmed: Bool { !panelDue && armedNoted }
    private var armedNoted = false

    func end() {
        link?.invalidate(); link = nil
        let w = waiters
        waiters.removeAll()
        for c in w { c.resume() }
        CATransaction.begin(); CATransaction.setDisableActions(true)
        root.removeFromSuperlayer()
        CATransaction.commit()
        logoLayers.removeAll()
        onEnd?()
    }

    // MARK: probes (capture / trace only; LOGO-SPEC §7)

    /// A layer's map to the host (its own bounds space → host pt, from the presentation tree) and its effective opacity.
    fileprivate func screenMap(_ layer: CALayer) -> (CGAffineTransform, Double) {
        var m = CGAffineTransform.identity
        var op = 1.0
        var cur: CALayer? = layer
        while let l = cur, l !== host {
            let p = l.presentation() ?? l
            let b = p.bounds
            let ap = CGPoint(x: b.minX + p.anchorPoint.x * b.width, y: b.minY + p.anchorPoint.y * b.height)
            let t = CATransform3DGetAffineTransform(p.transform)      // the 2-D part (transform.scale also scales z)
            m = m.concatenating(CGAffineTransform(translationX: -ap.x, y: -ap.y)).concatenating(t)
                .concatenating(CGAffineTransform(translationX: p.position.x, y: p.position.y))
            op *= p.isHidden ? 0 : Double(p.opacity)
            cur = l.superlayer
        }
        return (m, op)
    }

    /// Every part's anchor on screen, total scale, total rotation and effective opacity (the quantities of beats.json), plus
    /// each layer's opacity / filter / contents: `[PC][logo] probe …` / `[PC][logo] layer …`.
    fileprivate func partPoses() -> [(part: String, x: Double, y: Double, s: Double, rot: Double, a: Double)] {
        var byPart: [String: [(LogoParts.Node, CALayer)]] = [:]
        for (n, l) in logoLayers where !(n.name.hasPrefix("echo:")) { if let p = n.part, n.image != nil { byPart[p, default: []].append((n, l)) } }
        var out: [(part: String, x: Double, y: Double, s: Double, rot: Double, a: Double)] = []
        for (part, list) in byPart.sorted(by: { $0.key < $1.key }) {
            // the pose from the Face (or the only) layer; the opacity = the most opaque of the part's layers
            let rep = list.first { $0.0.slot == "face" } ?? list[0]
            let (m, _) = screenMap(rep.1)
            let b = rep.1.bounds, ap = rep.1.anchorPoint
            let p = CGPoint(x: ap.x * b.width, y: ap.y * b.height).applying(m)
            let s = (hypot(m.a, m.b) + hypot(m.c, m.d)) / 2
            let rot = atan2(Double(m.b), Double(m.a)) * 180 / .pi
            let a = list.map { screenMap($0.1).1 }.max() ?? 0
            out.append((part: part, x: Double(p.x), y: Double(p.y), s: Double(s), rot: rot, a: a))
        }
        return out
    }

    private func logoProbe(_ t: Double) {
        guard let parts = logoParts else { Log.mark("logo", "probe t=\(t) none"); return }
        Log.mark("logo", String(format: "probe t=%.4f mode=%@ group=%@", t, parts.mode.rawValue, groupScaleText()))
        for p in partPoses() {
            Log.mark("logo", String(format: "probe t=%.4f %@ x=%.2f y=%.2f s=%.4f rot=%.2f a=%.3f", t, p.part, p.x, p.y, p.s, p.rot, p.a))
        }
        for (n, l) in logoLayers {
            let pl = l.presentation() ?? l
            let a = screenMap(l).1
            var contents = ""
            if n.image != nil, let c = pl.contents {
                let cg = c as! CGImage          // swiftlint:disable:this force_cast
                contents = parts.images.first { $0.value === cg }?.key ?? "?"
            }
            Log.mark("logo", String(format: "layer t=%.4f %@ own=%.3f eff=%.3f group=%d filt=%@ contents=%@ bounds=%.4fx%.4f anchor=%.5f,%.5f pos=%.4f,%.4f",
                                    t, n.name, pl.opacity, a, l.allowsGroupOpacity ? 1 : 0, l.minificationFilter.rawValue, contents,
                                    Double(l.bounds.width), Double(l.bounds.height), Double(l.anchorPoint.x), Double(l.anchorPoint.y),
                                    Double(l.position.x), Double(l.position.y)))
        }
        let dimNow = (dim.presentation() ?? dim).opacity
        Log.mark("logo", String(format: "probe t=%.4f dim=%.3f haptic=%d cleared=%d", t, dimNow, winHaptic ? 1 : 0, logoCleared ? 1 : 0))
    }

    fileprivate func groupScaleText() -> String {
        guard let g = logoLayers.first(where: { $0.node.name == "group" })?.layer else { return "-" }
        let p = g.presentation() ?? g
        return String(format: "%.4f", Double(CATransform3DGetAffineTransform(p.transform).a))
    }
}

/// `-pc.logoTrace 1` (LOGO-SPEC §7 A3): on the real-time run, logs the first frame each part is on screen and the frames of
/// the named extremes (blue sign's overshoot, OUT!'s largest glyph, the group's low / high), in host time since W.
@MainActor private final class LogoTrace {
    private var seen: Set<String> = []
    private var blueMax = (-Double.infinity, 0.0)
    private var uMax = (-Double.infinity, 0.0)
    private var gMin = (Double.infinity, 0.0), gMax = (-Double.infinity, 0.0)
    private var reported = false

    private func first(_ what: String, _ e: Double, _ extra: String = "") {
        guard !seen.contains(what) else { return }
        seen.insert(what)
        Log.mark("logo", String(format: "trace first-visible %@ W+%.4f", what, e) + extra)
    }

    func tick(_ run: CelebrationRun, time e: Double) {
        let poses = run.partPoses()
        for p in poses where p.a > 0.001 { first(p.part, e, String(format: " a=%.3f", p.a)) }
        // the background beats on screen (presentation values): the dim's start / full, the first confetti piece and rocket
        let d = Double((run.dim.presentation() ?? run.dim).opacity)
        if d > 0.001 { first("dim", e, String(format: " %.3f", d)) }
        if d >= 0.894 * 0.995 { first("dimFull", e, String(format: " %.3f", d)) }
        let screen = run.bounds
        func onScreen(_ root: CALayer) -> Bool {
            for l in root.sublayers ?? [] {
                let p = l.presentation() ?? l
                if p.opacity > 0.01 && !p.isHidden && p.frame.intersects(screen) && p.frame.minY < screen.maxY - 0.5 { return true }
            }
            return false
        }
        if !seen.contains("confetti") && onScreen(run.confettiRoot) { first("confetti", e) }
        if !seen.contains("firework") && onScreen(run.fireworkRoot) { first("firework", e) }
        if (run.logoRoot.presentation() ?? run.logoRoot).isHidden { first("logoRemoved", e) }
        if let b = poses.first(where: { $0.part == "logoSignBlue" }), b.a > 0, b.rot > blueMax.0 { blueMax = (b.rot, e) }
        if let u = poses.first(where: { $0.part == "logoOutU" }), u.a > 0, u.s > uMax.0 { uMax = (u.s, e) }
        let g = Double(run.groupScaleText()) ?? 1
        if e > 1.6 { if g < gMin.0 { gMin = (g, e) }; if g > gMax.0 { gMax = (g, e) } }
        if e > 2.4 && !reported {
            reported = true
            Log.mark("logo", String(format: "trace blue-peak rot=%.2f W+%.4f; U-peak s=%.4f W+%.4f; group low %.4f W+%.4f high %.4f W+%.4f",
                                    blueMax.0, blueMax.1, uMax.0, uMax.1, gMin.0, gMin.1, gMax.0, gMax.1))
        }
    }
}
