import XCTest
import UIKit
import PathCore
@testable import ArrowOut

/// LOGO-IMPL (OWNER P0 19:40 (b); build/logo/LOGO-SPEC.md §5.3, §6, §7 A7; SPEC.md rulings 35/36). The win logo's data and the
/// animations the app actually adds:
/// - testWinLogoTracksMatchTheSpec: ui.json `win.logo` parses and every part's pose at the 45 acceptance beats equals
///   build/logo/spec/beats.json (Tests/WinLogoBeatsFixture.swift, generated) within 0.01 (pt, ×, °, α);
/// - testWinLogoLayersAreConsistent: every `win.logo.layers` entry sits at its logo_rect on the canvas, a part's layers share one
///   frame / anchor / rest position = the part's anchorPt (LOGO-SPEC-FIX M1), the arrow sign is ONE layer with 5 contents (M3),
///   one flatUntil for all five letters (L1), and every bundled file has the spec's pixel size;
/// - testWinLogoNeverUpscales (§6, A7 in closed form): no layer is ever drawn above its file's pixels on the iPhone 15 (@3x, k 1),
///   checked every 1 ms from the layer's first visible frame to the removal;
/// - testTheBakedAnimationsFollowTheTracks: the CAKeyframeAnimations LogoParts bakes (simplified keyframes, what CA interpolates)
///   reproduce the closed-form tracks every 1 ms within 0.06 pt / 0.06° / 0.0006 × / 0.005 α, and the tree is the spec's (paint
///   order, group opacity, the flat / pair / echo opacity rules, the discrete bend contents);
/// - testTheWinBeatsAreTheSpecs: the non-logo beats (LOGO-SPEC §1 / §5.2) in ui.json and as compiled defaults; the old logo keys
///   are gone.
@MainActor final class WinLogoTests: XCTestCase {
    private let file = Tuning.load(bundle: .main).ui.file

    private func spec() throws -> LogoSpec { try XCTUnwrap(LogoSpec(file), "ui.json win.logo parses") }

    private static let partIDs: Set<String> = ["logoSignPurple", "logoPegs", "logoSignBlue", "logoLetterA", "logoLetterR1", "logoLetterR2",
                                               "logoLetterO", "logoLetterW", "logoOutO", "logoOutU", "logoOutT", "logoOutBang", "logoOut"]

    // MARK: the data

    func testWinLogoTracksMatchTheSpec() throws {
        let spec = try spec()
        XCTAssertEqual(Set(spec.parts.keys), Self.partIDs)
        let root = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(WinLogoBeatsFixture.json.utf8)) as? [String: Any])
        let beats = try XCTUnwrap(root["beats"] as? [[String: Any]])
        XCTAssertEqual(beats.count, 45, "every 1/30 s from W+0.35 to W+1.7833, plus W+1.80")
        var checked = 0
        for b in beats {
            let t = try XCTUnwrap(b["t"] as? Double)
            XCTAssertEqual(spec.groupScale(t), try XCTUnwrap(b["group_s"] as? Double), accuracy: 0.01, "group.s @ W+\(t)")
            let parts = try XCTUnwrap(b["parts"] as? [String: [String: Double]])
            XCTAssertEqual(parts.count, 12, "every part but the fallback logoOut")
            for (id, e) in parts {
                let p = spec.screenPose(id, t)
                XCTAssertEqual(p.x, try XCTUnwrap(e["x"]), accuracy: 0.01, "\(id).x @ W+\(t)")
                XCTAssertEqual(p.y, try XCTUnwrap(e["y"]), accuracy: 0.01, "\(id).y @ W+\(t)")
                XCTAssertEqual(p.s, try XCTUnwrap(e["s"]), accuracy: 0.01, "\(id).s @ W+\(t)")
                XCTAssertEqual(p.rot, try XCTUnwrap(e["rot"]), accuracy: 0.01, "\(id).rot @ W+\(t)")
                XCTAssertEqual(spec.opacity(id, t), try XCTUnwrap(e["a"]), accuracy: 0.01, "\(id).a @ W+\(t)")
                checked += 1
            }
        }
        XCTAssertEqual(checked, 45 * 12)
    }

    func testWinLogoLayersAreConsistent() throws {
        let spec = try spec()
        XCTAssertEqual(spec.layers.count, 27, "3 signs/pegs + 5 × (Ext, Face, Flat) + 4 × (Ext, Face) + the fallback logoOut")
        let blue = try XCTUnwrap(spec.layers["logoSignBlue"])
        let blueOrigin = CGPoint(x: blue.position.x - blue.anchor.x * blue.bounds.width, y: blue.position.y - blue.anchor.y * blue.bounds.height)
        let c = spec.canvas
        for l in spec.layers.values {
            var o = CGPoint(x: l.position.x - l.anchor.x * l.bounds.width, y: l.position.y - l.anchor.y * l.bounds.height)
            if l.container == "logoSignBlue" { o.x += blueOrigin.x; o.y += blueOrigin.y }
            XCTAssertEqual(o.x, c.minX + l.logoRect.minX * c.width, accuracy: 0.001, "\(l.id) x")
            XCTAssertEqual(o.y, c.minY + l.logoRect.minY * c.height, accuracy: 0.001, "\(l.id) y")
            XCTAssertEqual(l.bounds.width, l.logoRect.width * c.width, accuracy: 0.001, "\(l.id) w")
            XCTAssertEqual(l.bounds.height, l.logoRect.height * c.height, accuracy: 0.001, "\(l.id) h")
            let part = try XCTUnwrap(spec.parts[l.part], l.id)
            XCTAssertEqual(o.x + l.anchor.x * l.bounds.width, part.anchorPt.x, accuracy: 0.001, "\(l.id): its part's anchorPt x")
            XCTAssertEqual(o.y + l.anchor.y * l.bounds.height, part.anchorPt.y, accuracy: 0.001, "\(l.id): its part's anchorPt y")
            // the bundle's file = the spec's pixels (the layer is sized from the spec, never from the image or UIArt.sizePt)
            for id in l.contents {
                let img = try XCTUnwrap(ArtStore.image(try XCTUnwrap(UIArt(rawValue: id), id))?.cgImage, "\(id) decodes")
                let px = try XCTUnwrap(l.filePx, l.id)
                XCTAssertEqual(CGSize(width: img.width, height: img.height), px, id)
            }
        }
        for (pid, ls) in Dictionary(grouping: spec.layers.values, by: \.part) {
            for l in ls {
                XCTAssertEqual(l.bounds, ls[0].bounds, "\(pid): one frame for every layer")
                XCTAssertEqual(l.anchor, ls[0].anchor, "\(pid): one anchor for every layer (LOGO-SPEC-FIX M1)")
                XCTAssertEqual(l.position, ls[0].position, "\(pid): one rest position")
            }
        }
        let sign = spec.layers.values.filter { $0.part == "logoSignPurple" }
        XCTAssertEqual(sign.count, 1, "the arrow sign is ONE layer (LOGO-SPEC-FIX M3)")
        XCTAssertEqual(sign.first?.contents, ["logoSignPurple", "logoSignPurpleBend25", "logoSignPurpleBend50", "logoSignPurpleBend75",
                                              "logoSignPurpleBend100"])
        XCTAssertEqual(spec.arrowLetters, LogoSpec.arrowOrder)
        XCTAssertEqual(spec.flatUntil, 0.807, accuracy: 1e-12, "LOGO-SPEC-FIX L1: R1's own first key at opacity 1")
        for id in LogoSpec.arrowOrder {
            let p = try XCTUnwrap(spec.parts[id])
            XCTAssertEqual(p.flatUntil, spec.flatUntil, "\(id): ONE swap time for all five letters")
            XCTAssertEqual(Set(p.layers.keys), ["ext", "face", "flat"], id)
            for (role, lid) in p.layers { XCTAssertEqual(spec.layers[lid]?.role, role, lid) }
        }
        for id in LogoSpec.outOrder {
            XCTAssertNil(spec.parts[id]?.tracks["a"], "\(id): OUT!'s opacity lives on outGroup (ruling 36 (a))")
            XCTAssertEqual(spec.layers.values.filter { $0.part == id }.map(\.container), ["outGroup", "outGroup"], id)
        }
        let g = try XCTUnwrap(spec.outGroup), e = try XCTUnwrap(spec.outEcho)
        XCTAssertEqual(g.children, e.children, "the echo copies the 8 OUT! layers")
        XCTAssertEqual(g.children, LogoSpec.outOrder.map { $0 + "Ext" } + LogoSpec.outOrder.map { $0 + "Face" }, "every Ext under every Face")
        XCTAssertEqual(e.delay, 2.0 / 60, accuracy: 1e-9, "the echo 2 frames behind")
        XCTAssertLessThan(e.z, g.z, "the echo under OUT!")
    }

    func testWinLogoNeverUpscales() throws {
        let spec = try spec()
        let clearAt = CelebrationRun.Beats(file).clearAt
        for l in spec.layers.values where l.part != "logoOut" {
            let p = try XCTUnwrap(spec.parts[l.part])
            let px = try XCTUnwrap(l.filePx)
            var worst = 0.0, at = 0.0
            for i in 0...Int((clearAt - p.visibleFrom) * 1000) {
                let t = p.visibleFrom + Double(i) / 1000
                let o = spec.local(l.part, t), g = spec.groupScale(t)
                // screen px per file px on the iPhone 15 (@3x, layoutRect k = 1), along each axis
                let r = max(l.bounds.width * o.sx * g * 3 / px.width, l.bounds.height * o.sy * g * 3 / px.height)
                if r > worst { worst = r; at = t }
            }
            XCTAssertLessThanOrEqual(worst, 1.0, "\(l.id) drawn at \(worst) screen px per file px at W+\(at) (LOGO-SPEC §6)")
        }
    }

    // MARK: the baked animations

    /// A keyframe animation's value `t` s after W (begin = its offset after W), the way CA interpolates it (linear or discrete,
    /// the fill modes; transforms by their decomposition into axis scales + rotation).
    private func value(_ a: CAKeyframeAnimation, begin: Double, at t: Double) -> Any? {
        switch raw(a, begin: begin, at: t) {                     // a single key (held, or before / after) in the same form
        case let n as NSNumber: return n.doubleValue
        case let v as NSValue where String(cString: v.objCType).contains("CGPoint"): return v.cgPointValue
        case let v as NSValue: return Self.decompose(v.caTransform3DValue)
        case let other: return other
        }
    }

    private func raw(_ a: CAKeyframeAnimation, begin: Double, at t: Double) -> Any? {
        let values = a.values ?? [], keys = (a.keyTimes ?? []).map(\.doubleValue)
        let u = (t - begin) / a.duration
        if u < 0 { return a.fillMode == .both || a.fillMode == .backwards ? values.first : nil }
        if u > 1 { return a.fillMode == .both || a.fillMode == .forwards ? values.last : nil }
        if a.calculationMode == .discrete {
            let i = max(0, (keys.lastIndex { $0 <= u } ?? 0))
            return values[min(i, values.count - 1)]
        }
        guard let j = keys.firstIndex(where: { $0 >= u }) else { return values.last }
        if j == 0 { return values[0] }
        let f = (u - keys[j - 1]) / max(keys[j] - keys[j - 1], 1e-12)
        func mix(_ x: Double, _ y: Double) -> Double { x + (y - x) * f }
        switch (values[j - 1], values[j]) {
        case let (p as NSNumber, q as NSNumber):                  // first: NSNumber is an NSValue
            return mix(p.doubleValue, q.doubleValue)
        case let (p as NSValue, q as NSValue) where String(cString: p.objCType).contains("CGPoint"):
            let a = p.cgPointValue, b = q.cgPointValue
            return CGPoint(x: mix(a.x, b.x), y: mix(a.y, b.y))
        case let (p as NSValue, q as NSValue):
            // CA decomposes the two matrices and turns along the shorter arc
            let a = Self.decompose(p.caTransform3DValue), b = Self.decompose(q.caTransform3DValue)
            var dr = (b[2] - a[2]).truncatingRemainder(dividingBy: 360)
            if dr > 180 { dr -= 360 } else if dr < -180 { dr += 360 }
            return [mix(a[0], b[0]), mix(a[1], b[1]), a[2] + dr * f]
        default:
            return nil
        }
    }

    private static func decompose(_ m: CATransform3D) -> [Double] {
        [Double(hypot(m.m11, m.m12)), Double(hypot(m.m21, m.m22)), atan2(Double(m.m12), Double(m.m11)) * 180 / .pi]
    }

    func testTheBakedAnimationsFollowTheTracks() throws {
        let spec = try spec()
        let parts = try XCTUnwrap(LogoParts.make(file))
        XCTAssertEqual(parts.mode, .pairs, "every pair, flat, sign and variant file is in the bundle")
        // the tree (LOGO-SPEC §2): the paint order, the containers
        let g = parts.group
        XCTAssertEqual(g.children.map(\.name), ["logoSignPurple", "logoPegs", "logoSignBlue", "outEcho", "outGroup"])
        let blue = try XCTUnwrap(g.children.first { $0.name == "logoSignBlue" })
        let letters = ["A", "R1", "R2", "O", "W"]
        XCTAssertEqual(blue.children.map(\.name), letters.map { "logoLetter\($0)Ext" } + letters.flatMap { ["logoLetter\($0)Face", "logoLetter\($0)Flat"] },
                       "every ARROW extrusion under every face, the flat in its face's slot")
        let out = try XCTUnwrap(g.children.first { $0.name == "outGroup" }), echo = try XCTUnwrap(g.children.first { $0.name == "outEcho" })
        XCTAssertEqual(out.children.map(\.name), try XCTUnwrap(spec.outGroup).children)
        XCTAssertEqual(echo.children.map(\.name), try XCTUnwrap(spec.outGroup).children.map { "echo:" + $0 })
        XCTAssertTrue(out.groupOpacity && echo.groupOpacity, "ruling 36 (a): OUT! and its echo fade as groups")
        XCTAssertFalse(parts.images.keys.contains("logoOut"), "the fallback file is not decoded when the pairs exist")
        XCTAssertFalse(parts.images.keys.contains { ["logoLetterA", "logoOutT", "logoArrowOut"].contains($0) }, "never the composed ids")

        let dt = 0.001
        let ts = stride(from: 0.30, through: 2.60, by: dt).map { $0 }
        var worst: [String: (Double, Double)] = [:]
        func note(_ k: String, _ err: Double, _ t: Double) { if err > (worst[k]?.0 ?? -1) { worst[k] = (err, t) } }
        let echoDelay = try XCTUnwrap(spec.outEcho).delay
        var nodes: [(LogoParts.Node, Double)] = []                     // (node, delay)
        g.forEach { n in nodes.append((n, n.name.hasPrefix("echo:") ? echoDelay : 0)) }
        // the group
        let gs = try XCTUnwrap(g.anims.first { $0.key == "transform.scale" })
        for t in ts { note("group.s", abs((value(gs.anim as! CAKeyframeAnimation, begin: gs.begin, at: t) as! Double) - spec.groupScale(t)), t) }
        for (n, delay) in nodes where n.image != nil {
            let layer = try XCTUnwrap(spec.layers[n.name.replacingOccurrences(of: "echo:", with: "")])
            let part = try XCTUnwrap(spec.parts[layer.part])
            let anims = Dictionary(uniqueKeysWithValues: n.anims.map { ($0.key, $0) })
            for t in ts {
                let tp = t - delay
                let o = spec.local(part.id, tp)
                if let p = anims["position"] {
                    let v = try XCTUnwrap(value(p.anim as! CAKeyframeAnimation, begin: p.begin, at: t) as? CGPoint)
                    note("position", max(abs(Double(v.x) - (layer.position.x + o.dx)), abs(Double(v.y) - (layer.position.y + o.dy))), t)
                } else {
                    XCTAssertEqual(n.position, layer.position, n.name)
                }
                if let tr = anims["transform"] {
                    if t == ts[0] {
                        // adjacent keys turn < 90° (CA's shorter-arc interpolation stays on the track)
                        let r = ((tr.anim as! CAKeyframeAnimation).values ?? []).map { Self.decompose(($0 as! NSValue).caTransform3DValue)[2] }
                        for (x, y) in zip(r, r.dropFirst()) {
                            var d = abs(y - x).truncatingRemainder(dividingBy: 360); d = min(d, 360 - d)
                            XCTAssertLessThan(d, 90, "\(n.name): a transform step of \(d)°")
                        }
                    }
                    let v = try XCTUnwrap(value(tr.anim as! CAKeyframeAnimation, begin: tr.begin, at: t) as? [Double])
                    note("scale", max(abs(v[0] - o.sx), abs(v[1] - o.sy)), t)
                    var dr = abs(v[2] - o.rot).truncatingRemainder(dividingBy: 360)
                    dr = min(dr, 360 - dr)
                    note("rot", dr, t)
                }
                // the opacity rules (ruling 36; LOGO-SPEC-FIX L1 / L2)
                let model = Double(n.opacity)
                let op = anims["opacity"].map { a in (value(a.anim as! CAKeyframeAnimation, begin: a.begin, at: t) as? Double) ?? model } ?? model
                let own = part.tracks["a"].map { $0(t) } ?? 1
                let expected: Double
                if layer.role == "flat" {
                    expected = t < part.visibleFrom || t >= spec.flatUntil ? 0 : own
                } else if layer.role == "ext" || layer.role == "face" {
                    expected = layer.container == "logoSignBlue" ? (t < spec.flatUntil ? 0 : 1) : 1    // outGroup / outEcho: 1
                } else {
                    expected = t < part.visibleFrom ? 0 : own
                }
                // one ms either side of a discrete step is not a defect of the bake
                if abs(t - spec.flatUntil) > 0.0015 && abs(t - part.visibleFrom) > 0.0015 { note("opacity", abs(op - expected), t) }
            }
            if n.name == "logoSignPurple" {
                // the bend: ONLY contents changes, the nearest of the rest drawing and the 4 variants (discrete)
                let b = try XCTUnwrap(anims["bend"]), bend = try XCTUnwrap(part.tracks["bend"])
                let a = b.anim as! CAKeyframeAnimation
                XCTAssertEqual(a.calculationMode, .discrete)
                XCTAssertEqual(Set(n.anims.map(\.key)), ["position", "transform", "opacity", "bend"], "never bounds / anchorPoint")
                func want(_ t: Double) -> Int { max(0, min(4, Int((-bend(t) / 2.5).rounded()))) }
                var wrong = 0, swaps = Set<Int>()
                for t in ts where t >= part.visibleFrom {
                    let img = value(a, begin: b.begin, at: t) as AnyObject
                    let w = want(t)
                    swaps.insert(w)
                    let near = want(t - 0.002) != want(t + 0.002)            // within 2 ms of a switch
                    if img !== (parts.images[layer.contents[w]]! as AnyObject) && !near { wrong += 1 }
                }
                XCTAssertEqual(swaps, [0, 1, 2, 3, 4], "the rest drawing and all four variants are shown")
                XCTAssertEqual(wrong, 0, "the bend contents follow the nearest-variant rule")
            }
        }
        for c in [out, echo] {
            let a = try XCTUnwrap(c.anims.first { $0.key == "opacity" })
            let track = try XCTUnwrap(c.name == "outGroup" ? spec.outGroup?.a : spec.outEcho?.a)
            let from = c.name == "outGroup" ? try XCTUnwrap(spec.outGroup).visibleFrom : track.start
            for t in ts {
                let v = (value(a.anim as! CAKeyframeAnimation, begin: a.begin, at: t) as? Double) ?? Double(c.opacity)
                let want = t < from ? 0 : (c.name == "outEcho" && t > track.end ? 0 : track(t))
                if abs(t - from) > 0.0015 { note("\(c.name).a", abs(v - want), t) }
            }
        }
        XCTAssertLessThanOrEqual(worst["group.s"]?.0 ?? 0, 0.001, "group.s \(String(describing: worst["group.s"]))")
        XCTAssertLessThanOrEqual(worst["position"]?.0 ?? 0, 0.06, "position (pt) \(String(describing: worst["position"]))")
        XCTAssertLessThanOrEqual(worst["scale"]?.0 ?? 0, 0.0006, "scale \(String(describing: worst["scale"]))")
        XCTAssertLessThanOrEqual(worst["rot"]?.0 ?? 0, 0.06, "rotation (°) \(String(describing: worst["rot"]))")
        XCTAssertLessThanOrEqual(worst["opacity"]?.0 ?? 0, 0.005, "opacity \(String(describing: worst["opacity"]))")
        XCTAssertLessThanOrEqual(worst["outGroup.a"]?.0 ?? 0, 0.005, "outGroup.a \(String(describing: worst["outGroup.a"]))")
        XCTAssertLessThanOrEqual(worst["outEcho.a"]?.0 ?? 0, 0.005, "outEcho.a \(String(describing: worst["outEcho.a"]))")
        XCTAssertEqual(Set(worst.keys), ["group.s", "position", "scale", "rot", "opacity", "outGroup.a", "outEcho.a"], "every quantity was sampled")
        // the data the commit carries stays small (the simplified keyframes, not 480 Hz samples)
        var keys = 0
        g.forEach { n in for a in n.anims { keys += (a.anim as? CAKeyframeAnimation)?.values?.count ?? 0 } }
        print("[logo] baked vs tracks, worst (error, W+t): \(worst.sorted { $0.key < $1.key }.map { "\($0.key) \(String(format: "%.4f @ %.3f", $0.value.0, $0.value.1))" }.joined(separator: ", ")); keyframes \(keys)")
        XCTAssertLessThan(keys, 12_000, "keyframes in the whole tree: \(keys)")
    }

    // MARK: the beats

    func testTheWinBeatsAreTheSpecs() {
        let bundled = CelebrationRun.Beats(file), compiled = CelebrationRun.Beats(TuningFile(name: "ui", json: [:]))
        for b in [bundled, compiled] {
            // LOGO-SPEC §1 / §5.2 (REFERENCE §2 / §8; W = the clear wave's first frame)
            XCTAssertEqual(b.impactAt, 1.688, accuracy: 1e-12)
            XCTAssertEqual(b.dimAt, 1.355, accuracy: 1e-12)
            XCTAssertEqual(b.dimDur, 0.349, accuracy: 1e-12)
            XCTAssertEqual(b.dim, 0.894, accuracy: 1e-12)
            XCTAssertEqual(b.confettiAt, 1.655, accuracy: 1e-12)
            XCTAssertEqual(b.rockets, [1.655, 1.905, 2.075, 2.275, 2.525, 2.875])
            XCTAssertEqual(b.bursts, [2.365, 2.565, 2.765, 2.965, 3.195, 3.595])
            XCTAssertEqual(b.clearAt, 4.018, accuracy: 1e-12)
            XCTAssertEqual(b.panelAt, 4.034, accuracy: 1e-12)
            // requirement change (ruling 40 = v582, motion-catalog §11.4; supersedes LOGO-SPEC D9's 0.41): taps are ignored
            // until the logo has landed, W + 1.70; same exact strength as the old pin
            XCTAssertEqual(b.skipFrom, 1.70, accuracy: 1e-12, "ruling 40: skip only once the logo has landed")
            XCTAssertLessThan(b.skipFrom, b.panelAt, "ruling 40 keeps a skip (≥ panelAt would be 37c's no-skip)")
            // A2 (motion-catalog §5.2, ruling 39 OD4): the 14 haptic beats, ≥ 2 frames apart, the slam on the impact frame
            XCTAssertEqual(b.haptics, CelebrationRun.Beats.specHaptics)
            XCTAssertEqual(b.haptics.map(\.t), [0.815, 0.848, 0.881, 0.914, 0.947, 1.139, 1.688, 1.828, 2.365, 2.565, 2.765, 2.965,
                                                3.195, 3.595])
            XCTAssertEqual(b.haptics.compactMap(\.intensity), [0.55, 0.58, 0.62, 0.66, 0.70], "five RISING letter clicks")
            XCTAssertEqual(b.haptics.first { $0.haptic == .win }?.t ?? -1, b.impactAt, accuracy: 1e-12)
            for (a, c) in zip(b.haptics, b.haptics.dropFirst()) {
                XCTAssertGreaterThanOrEqual(c.t - a.t, 0.033 - 1e-9, "beats \(a.t) → \(c.t) stay ≥ 33 ms (2 frames) apart")
            }
            XCTAssertEqual(b.prebuildFrom, 0.10, accuracy: 1e-12)
            XCTAssertEqual(b.burstPerFrame, 10)
        }
        // the strip / chip / ring keep their offsets from the panel (+0.01 / +0.40 / +0.71)
        XCTAssertEqual(file.double("win.stripAt", 0) - bundled.panelAt, 0.01, accuracy: 1e-9)
        XCTAssertEqual(file.double("win.chipAt", 0) - bundled.panelAt, 0.40, accuracy: 1e-9)
        XCTAssertEqual(file.double("win.ringAt", 0) - bundled.panelAt, 0.71, accuracy: 1e-9)
        for k in ["signAt", "signDur", "lettersAt", "letterStagger", "letterDur", "arrowSignAt", "arrowSignDur", "outAt", "outGrowDur",
                  "outBig", "outHoldTo", "slamDur", "squash", "settleScale"] {
            XCTAssertFalse(file.has("win.\(k)"), "win.\(k) is replaced by win.logo (LOGO-SPEC §5.2)")
        }
    }
}
