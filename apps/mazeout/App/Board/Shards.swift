import UIKit
import PathCore

// B2 (SPEC-architecture §5.6 "Shards", §5.11 rule 12; SPEC-motion-audio §10, MA6). Door / pipe / box shatter debris: a
// POOL of pre-built layers (never allocated on the tap path) animated with keyframes from the `fx` stream (deterministic,
// freezable for captures), not emitters (arch DECISION).
// Physics in SCREEN pt (gravity is the same at every zoom, MA6): each piece is a holder at the spawn point (content space,
// scaled by 1/zoom so its children move in screen pt) → a mover (additive position, exact parabola) → the shard (spin,
// fade). The parabola is exact: up to the apex easeOutQuad, then easeInQuad (y = vy·t + g·t²/2 has exactly those shapes).
// The animation templates are built once per kind (the velocities are fixed draws of the fx stream) and re-added with a
// new beginTime (CA copies an animation when it is added), so a 140-piece box break costs ≈ 1 ms of main thread.

enum ShardKind: Int, CaseIterable { case door, pipe, box, ring, pipeHalf, pipeRim }

@MainActor final class ShardPool {
    final class Piece {
        let holder = CALayer()
        let mover = CALayer()
        /// FIX-V2 F-05: the piece's grey drop shadow on the white board (a sibling under the shard: it spins with the shard
        /// about its own centre but stays offset straight DOWN, like the phone's).
        let shadow = CALayer()
        let shard = CALayer()
        var busy = false
        init() {
            holder.addSublayer(mover)
            mover.addSublayer(shadow)
            mover.addSublayer(shard)
            shadow.isHidden = true
        }
    }

    struct Template {
        let move: CAAnimationGroup           // additive position (screen pt, relative)
        let spin: CAAnimationGroup           // rotation + opacity
        let vx: Double
    }

    private var pieces: [Piece] = []
    private var next = 0
    private var templates: [ShardKind: [Template]] = [:]
    private let fx: EffectsConfig
    private(set) var busyCount = 0
    private var images: [String: CGImage] = [:]

    init(fx: EffectsConfig, size: Int) {
        self.fx = fx
        for _ in 0..<max(1, size) { pieces.append(Piece()) }
        var r = FXRandom(seed: 0x5A4D_5348_4152_4453, label: "shards")
        templates[.door] = Self.makeTemplates(fx.doorShards, count: 64, symmetric: true, rng: &r)
        templates[.pipe] = Self.makeTemplates(fx.pipeShards, count: 44, symmetric: true, rng: &r)
        templates[.box] = Self.makeTemplates(fx.boxShards, count: 150, symmetric: false, rng: &r)
        var ring = fx.boxShards
        ring.spinDeg = 180
        templates[.ring] = Self.makeTemplates(ring, count: 4, symmetric: false, rng: &r)
        var half = fx.pipeShards
        half.vyMin = -150; half.vyMax = -150; half.vxMin = 60; half.vxMax = 60; half.spinDeg = 180
        templates[.pipeHalf] = Self.makeTemplates(half, count: 2, symmetric: false, rng: &r)
        var rim = fx.pipeShards
        rim.vyMin = -100; rim.vyMax = -100; rim.vxMin = 0; rim.vxMax = 30; rim.spinDeg = 180
        templates[.pipeRim] = Self.makeTemplates(rim, count: 2, symmetric: true, rng: &r)
        // FIX-V2 F-05: the chunky 3-D debris atlases, code-drawn once OFF the main thread (≈ 9 ms of CoreGraphics in Debug:
        // never inside a Loading / launch frame); a level's first break comes seconds later
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let t0 = CACurrentMediaTime()
            let built = ShardArt.buildAll()
            let ms = (CACurrentMediaTime() - t0) * 1000
            DispatchQueue.main.async {
                MainActor.assumeIsolated {
                    guard let self else { return }
                    for (n, img) in built.images where self.images[n] == nil { self.images[n] = img }
                    Log.mark("fx", String(format: "shard atlases %d built off-main in %.1f ms", built.images.count, ms))
                }
            }
        }
    }

    var capacity: Int { pieces.count }

    func setImage(_ name: String, _ img: CGImage?) { if let img { images[name] = img } }

    /// Velocities and spins drawn once (screen pt/s). `symmetric`: vx sign random; else the caller picks the sign.
    private static func makeTemplates(_ s: ShardSpec, count: Int, symmetric: Bool, rng: inout FXRandom) -> [Template] {
        var out: [Template] = []
        for _ in 0..<count {
            let vy = rng.range(s.vyMin, s.vyMax)
            let vxMag = rng.range(s.vxMin, s.vxMax)
            let vx = symmetric ? vxMag * rng.sign() : vxMag
            let spin = rng.range(0.4, 1.0) * s.spinDeg * .pi / 180 * rng.sign()
            out.append(makeTemplate(vx: vx, vy: vy, g: s.g, life: s.life, fadeFrom: s.fadeFrom, spin: spin))
        }
        return out
    }

    static func makeTemplate(vx: Double, vy: Double, g: Double, life: Double, fadeFrom: Double, spin: Double) -> Template {
        let T = max(0.05, life)
        let x = CABasicAnimation(keyPath: "position.x")
        x.fromValue = 0
        x.toValue = vx * T
        x.duration = T
        x.isAdditive = true
        x.timingFunction = Ease2.linear
        let y = CAKeyframeAnimation(keyPath: "position.y")
        y.isAdditive = true
        y.calculationMode = .linear
        let tApex = vy < 0 ? min(T, -vy / max(g, 1)) : 0
        func yAt(_ t: Double) -> Double { vy * t + 0.5 * g * t * t }
        if tApex > 0.005 && tApex < T - 0.005 {
            y.values = [0, yAt(tApex), yAt(T)]
            y.keyTimes = [0, NSNumber(value: tApex / T), 1]
            y.timingFunctions = [Ease2.outQuad, Ease2.inQuad]
        } else if tApex >= T - 0.005 {
            y.values = [0, yAt(T)]
            y.keyTimes = [0, 1]
            y.timingFunctions = [Ease2.outQuad]
        } else {
            y.values = [0, yAt(T)]
            y.keyTimes = [0, 1]
            y.timingFunctions = [Ease2.inQuad]
        }
        y.duration = T
        let move = CAAnimationGroup()
        move.animations = [x, y]
        move.duration = T
        move.fillMode = .both
        let rot = CABasicAnimation(keyPath: "transform.rotation.z")
        rot.fromValue = 0
        rot.toValue = spin * T
        rot.duration = T
        rot.isAdditive = true
        rot.timingFunction = Ease2.linear
        let op = CAKeyframeAnimation(keyPath: "opacity")
        op.values = [1, 1, 0]
        op.keyTimes = [0, NSNumber(value: min(0.999, max(0, fadeFrom / T))), 1]
        op.duration = T
        let spinG = CAAnimationGroup()
        spinG.animations = [rot, op]
        spinG.duration = T
        spinG.fillMode = .both
        return Template(move: move.hi(), spin: spinG.hi(), vx: vx)
    }

    /// What one shard looks like.
    struct Look {
        var image: String? = nil        // atlas name (images[]) with `rect` as contentsRect
        var rect = CGRect(x: 0, y: 0, width: 1, height: 1)
        var color: CGColor? = nil       // a solid rounded quad when there is no image
        var size: CGSize
        var corner: CGFloat = 0
        var angle: CGFloat = 0
        /// FIX-V2 F-05: an atlas of the same layout drawn as the grey shadow, `shadowDY` content pt below the piece.
        var shadow: String? = nil
        var shadowDY: CGFloat = 0
    }

    /// Spawns pieces at `points` (content space) into `parent` beginning at `begin` (parent-local time), zoom `z`.
    /// `vxSign` (per piece, box shards: away from the centre line) overrides the template's sign when non-nil.
    /// Returns the pieces (the caller's end beat returns them with `release`).
    @discardableResult
    func spawn(kind: ShardKind, points: [CGPoint], looks: [Look], vxSign: [Double]? = nil, zoom z: CGFloat,
               parent: CALayer, begin: CFTimeInterval, hiddenUntilBegin: Bool = false) -> [Piece] {
        let parentNow = parent.convertTime(CACurrentMediaTime(), from: nil)
        guard let tpl = templates[kind], !tpl.isEmpty else { return [] }
        let zc = max(z, 0.05)
        var used: [Piece] = []
        used.reserveCapacity(points.count)
        for (i, p) in points.enumerated() {
            let piece = pieces[next]
            next = (next + 1) % pieces.count
            if piece.busy { piece.holder.removeFromSuperlayer(); busyCount -= 1 }
            piece.busy = true
            busyCount += 1
            var t = tpl[i % tpl.count]
            if let s = vxSign?[i], (s < 0) != (t.vx < 0) {
                // mirror x: rebuild the x half of the move group lazily from the template (cheap, rare path)
                t = mirrored(t)
            }
            let look = looks[i % looks.count]
            piece.holder.position = p
            piece.holder.transform = CATransform3DMakeScale(1 / zc, 1 / zc, 1)
            piece.mover.position = .zero
            let s = CGSize(width: look.size.width * zc, height: look.size.height * zc)
            piece.shard.bounds = CGRect(origin: .zero, size: s)
            piece.shard.position = .zero
            piece.shard.transform = CATransform3DMakeRotation(look.angle, 0, 0, 1)
            if let name = look.image, let img = images[name] {
                piece.shard.contents = img
                piece.shard.contentsRect = look.rect
                piece.shard.contentsGravity = .resize
                piece.shard.backgroundColor = nil
                piece.shard.cornerRadius = 0
            } else {
                piece.shard.contents = nil
                piece.shard.backgroundColor = look.color
                piece.shard.cornerRadius = look.corner * zc
            }
            piece.shard.opacity = 0                                   // model: gone after the animation
            piece.shadow.removeAllAnimations()
            if let sname = look.shadow, let simg = images[sname] {
                piece.shadow.isHidden = false
                piece.shadow.contents = simg
                piece.shadow.contentsRect = look.rect
                piece.shadow.contentsGravity = .resize
                piece.shadow.bounds = piece.shard.bounds
                piece.shadow.position = CGPoint(x: 0, y: look.shadowDY * zc)
                piece.shadow.transform = piece.shard.transform
                piece.shadow.opacity = 0
            } else {
                piece.shadow.isHidden = true
                piece.shadow.contents = nil
            }
            piece.holder.removeAllAnimations()
            piece.holder.opacity = 1
            if hiddenUntilBegin, begin > parentNow + 0.001 {
                Anim.switchOpacity(piece.holder, from: 0, to: 1, begin: parentNow, at: begin - parentNow, key: "wait")
            }
            t.move.beginTime = begin
            t.spin.beginTime = begin
            piece.mover.add(t.move, forKey: "m")
            piece.shard.add(t.spin, forKey: "s")
            if !piece.shadow.isHidden { piece.shadow.add(t.spin, forKey: "s") }
            parent.addSublayer(piece.holder)
            used.append(piece)
        }
        return used
    }

    private var mirrorCache: [ObjectIdentifier: Template] = [:]
    private func mirrored(_ t: Template) -> Template {
        let key = ObjectIdentifier(t.move)
        if let m = mirrorCache[key] { return m }
        let move = t.move.copy() as! CAAnimationGroup
        if let x = move.animations?.first as? CABasicAnimation, let v = x.toValue as? Double {
            let nx = x.copy() as! CABasicAnimation
            nx.toValue = -v
            move.animations = [nx] + (move.animations?.dropFirst() ?? [])
        }
        let m = Template(move: move, spin: t.spin, vx: -t.vx)
        mirrorCache[key] = m
        return m
    }

    /// Returns pieces to the pool (their holders leave the tree). Call inside a no-actions transaction.
    func release(_ used: [Piece]) {
        for p in used where p.busy {
            p.holder.removeFromSuperlayer()
            p.mover.removeAllAnimations()
            p.shard.removeAllAnimations()
            p.shadow.removeAllAnimations()
            p.busy = false
            busyCount -= 1
        }
    }

    /// Every piece back (a board clear).
    func releaseAll() { release(pieces) }
}

extension BoardEngine {
    /// Spawns a burst and schedules its return to the pool (a beat on the parent: never a timer).
    func burstShards(kind: ShardKind, points: [CGPoint], looks: [ShardPool.Look], vxSign: [Double]? = nil,
                     begin: CFTimeInterval, life: Double, hiddenUntilBegin: Bool = false, allowDefer: Bool = true) {
        guard !points.isEmpty else { return }
        // F4: a burst that starts later (a key's door at + 1.14 s, a pipe at leave + 0.05 s) is built in a later
        // display-link frame, off the tap's handler; its begin time is absolute, so it stays render-exact
        if allowDefer, hiddenUntilBegin, begin > Anim.now(sharedFX) + 0.1 {
            let token = stageToken
            deferred.append { [weak self] in
                guard let self, self.stageToken == token else { return }
                self.burstShards(kind: kind, points: points, looks: looks, vxSign: vxSign, begin: begin, life: life,
                                 hiddenUntilBegin: true, allowDefer: false)
            }
            return
        }
        let parent = sharedFX
        let used = shards.spawn(kind: kind, points: points, looks: looks, vxSign: vxSign, zoom: zoomScale, parent: parent,
                                begin: begin, hiddenUntilBegin: hiddenUntilBegin)
        let carrier = CALayer()
        parent.addSublayer(carrier)
        activeBursts += 1
        Anim.beat(on: carrier, key: "shardsEnd", begin: begin, delay: life + 0.02) { [weak self, weak carrier] _ in
            self?.activeBursts -= 1
            CATransaction.begin(); CATransaction.setDisableActions(true)
            self?.shards.release(used)
            carrier?.removeFromSuperlayer()
            CATransaction.commit()
        }
        noteFirst("shards:\(kind)")
    }
}

/// FIX-V2 F-05 (V2 finding: our door / pipe / box breaks were ~40-80 flat flecks where the phone throws chunky 3-D shards with
/// grey drop shadows; S1-L33-key-first, S1-L35-pipe-break, S1-L50-box-break). Our own debris, drawn in code: 8 irregular
/// convex chunks per palette (5-7 corners), each a dark lower side (the chunk's thickness, 0.13 R below), the face in a
/// top-light → bottom gradient, a lighter top facet and a small specular spot; glass (pipe) adds a pale rim. The phone's
/// colours (histograms of the break frames): box face #B858F8 with #C868F8 / #D888F8 lights and #9848D8 / #8848C8 sides; pipe
/// #68C8E8 / #88D8F8 with #18A8F8 / #38A8D8 depths; shadows #E4E4E4 / #DCDCDC on the white board (black α 0.11-0.14).
/// The shadow atlas has the same layout: each chunk's silhouette (face ∪ side) in black α 0.13.
enum ShardArt {
    struct Palette {
        let dark: UInt32, top: UInt32, bottom: UInt32, facet: UInt32, spec: UInt32
        var glass = false
        var shadowAlpha: CGFloat = 0.13
    }
    // PUBLISH R7 (D1 skin): box = moss stone, pipe = copper glass, door = iron trim (P) / teal-painted frame (O) /
    // honey planks (B) -- the d1_skin.py materials of the board sprites they break from.
    static let palettes: [(String, Palette)] = [
        ("sh3d.box", Palette(dark: 0x4B7129, top: 0x78A848, bottom: 0x5C8E2E, facet: 0x89B75B, spec: 0xC6DBA4)),
        ("sh3d.pipe", Palette(dark: 0xCB692B, top: 0xEFA877, bottom: 0xE48C52, facet: 0xF1B993, spec: 0xFFF4EA, glass: true,
                              shadowAlpha: 0.14)),
        ("sh3d.doorP", Palette(dark: 0x3A4C51, top: 0x677E83, bottom: 0x4D656B, facet: 0x7B9093, spec: 0xA5B2B4)),
        ("sh3d.doorO", Palette(dark: 0x0C6B6C, top: 0x47B8AD, bottom: 0x129D98, facet: 0x6AC1B7, spec: 0xA5D1C9)),
        ("sh3d.doorB", Palette(dark: 0x7F512D, top: 0xD6AA78, bottom: 0xBA814C, facet: 0xE3C69C, spec: 0xF4EDE0)),
    ]
    static let cols = 4, rows = 2, cellPx = 72
    static var cells: Int { cols * rows }

    /// The normalised contentsRect of cell `i`.
    static func rect(_ i: Int) -> CGRect {
        let k = ((i % cells) + cells) % cells
        return CGRect(x: CGFloat(k % cols) / CGFloat(cols), y: CGFloat(k / cols) / CGFloat(rows),
                      width: 1 / CGFloat(cols), height: 1 / CGFloat(rows))
    }

    /// Ink share of a cell (a look of size s shows a chunk ≈ 0.86 s across).
    static let inkFraction: CGFloat = 0.86

    /// Every palette's atlas + shadow atlas (any thread: private bitmap contexts only).
    struct Built: @unchecked Sendable { var images: [String: CGImage] = [:] }
    static func buildAll() -> Built {
        var b = Built()
        for (name, pal) in palettes {
            let (a, sh) = atlas(pal, name: name)
            if let a { b.images[name] = a }
            if let sh { b.images[name + ".shadow"] = sh }
        }
        return b
    }

    static func atlas(_ pal: Palette, name: String) -> (CGImage?, CGImage?) {
        let W = cols * cellPx, H = rows * cellPx
        func ctx() -> CGContext? {
            guard let c = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: W * 4,
                                    space: CGColorSpace(name: CGColorSpace.sRGB)!,
                                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
            c.translateBy(x: 0, y: CGFloat(H)); c.scaleBy(x: 1, y: -1)           // y down, like the layers
            c.setShouldAntialias(true); c.interpolationQuality = .high
            return c
        }
        guard let a = ctx(), let sh = ctx() else { return (nil, nil) }
        func col(_ hex: UInt32, _ alpha: CGFloat = 1) -> CGColor {
            CGColor(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
                    blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
        }
        // a stable seed per palette name (String.hashValue is randomised per launch: captures must be deterministic)
        var h: UInt64 = 1469598103934665603
        for b in name.utf8 { h = (h ^ UInt64(b)) &* 1099511628211 }
        var rng = FXRandom(seed: h, label: "shardArt")
        for i in 0..<cells {
            let cx = (CGFloat(i % cols) + 0.5) * CGFloat(cellPx)
            let cy = (CGFloat(i / cols) + 0.46) * CGFloat(cellPx)
            let R = CGFloat(cellPx) * 0.40
            // irregular rock-like chunks (the phone's: 4-6 corners, elongated, uneven), not regular gems
            let n = 4 + Int(rng.unit() * 3)
            let rot = CGFloat(rng.range(0, 2 * .pi))
            let squash = CGFloat(rng.range(0.58, 0.95))
            var raw: [CGPoint] = []
            for k in 0..<n {
                let a0 = CGFloat(k) / CGFloat(n) * 2 * .pi + CGFloat(rng.range(-0.32, 0.32)) * 2 * .pi / CGFloat(n)
                let r = R * CGFloat(rng.range(0.66, 1.0))
                raw.append(CGPoint(x: r * cos(a0), y: r * sin(a0) * squash))
            }
            let pts = raw.map { CGPoint(x: cx + $0.x * cos(rot) - $0.y * sin(rot), y: cy + $0.x * sin(rot) + $0.y * cos(rot)) }
            func poly(_ q: [CGPoint]) -> CGPath {
                let pth = CGMutablePath(); pth.addLines(between: q); pth.closeSubpath(); return pth
            }
            let face = poly(pts)
            let side = poly(pts.map { CGPoint(x: $0.x + 0.04 * R, y: $0.y + 0.2 * R) })
            // shadow: the silhouette (face ∪ side)
            sh.setFillColor(col(0x000000, pal.shadowAlpha))
            sh.beginTransparencyLayer(auxiliaryInfo: nil)
            sh.setFillColor(col(0x000000, 1))
            sh.addPath(face); sh.addPath(side); sh.fillPath()
            sh.endTransparencyLayer()
            // the chunk
            a.addPath(side); a.setFillColor(col(pal.dark)); a.fillPath()
            a.saveGState()
            a.addPath(face); a.clip()
            let g = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB)!, colors: [col(pal.top), col(pal.bottom)] as CFArray,
                               locations: [0, 1])!
            a.drawLinearGradient(g, start: CGPoint(x: cx, y: cy - R), end: CGPoint(x: cx, y: cy + R), options: [])
            // the top facet: the chunk shrunk toward its upper left
            let fc = CGPoint(x: cx - 0.14 * R, y: cy - 0.22 * R)
            a.addPath(poly(pts.map { CGPoint(x: fc.x + ($0.x - cx) * 0.58, y: fc.y + ($0.y - cy) * 0.52) }))
            a.setFillColor(col(pal.facet, 0.5)); a.fillPath()
            a.addEllipse(in: CGRect(x: cx - 0.46 * R, y: cy - 0.58 * R, width: 0.30 * R, height: 0.16 * R))
            a.setFillColor(col(pal.spec, 0.45)); a.fillPath()
            a.restoreGState()
            if pal.glass {
                a.addPath(face); a.setStrokeColor(col(0xFFF7F0, 0.55)); a.setLineWidth(1.6); a.strokePath()
            } else {
                a.addPath(face); a.setStrokeColor(col(pal.dark, 0.35)); a.setLineWidth(1.0); a.strokePath()
            }
        }
        // the shadow pass drew each silhouette opaque inside a transparency layer: fade it to the shadow alpha
        guard let shImg = sh.makeImage() else { return (a.makeImage(), nil) }
        guard let fade = ctx() else { return (a.makeImage(), shImg) }
        fade.setAlpha(pal.shadowAlpha)
        fade.translateBy(x: 0, y: CGFloat(H)); fade.scaleBy(x: 1, y: -1)
        fade.draw(shImg, in: CGRect(x: 0, y: 0, width: W, height: H))
        return (a.makeImage(), fade.makeImage())
    }
}
