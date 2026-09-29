import UIKit
import PathCore

// B2 (SPEC-architecture §5.6 "pipe"; STYLE §A.2 "Pipe" (L35 shot 042); MANIFEST pipeTube (code), pipeMouth, pipeCounter;
// SPEC-motion-audio §3.5.3). In tubeRoot, ABOVE the movers (an arrow passes inside the translucent tube: it reads lighter
// blue, VERIFIED motion §2.2).
//  - tube (CODE route): strokes along the tube centreline, 1.00 p wide, round joins; the measured cross-section (lit from
//    the upper right) as parallel bands: each band is the centreline translated by (o, −o)·p, so on a vertical run it sits
//    at x = o and on a horizontal run at y = −o (the "same profile rotated" of STYLE): dark #28A0DD −0.45…−0.26, the ramp
//    #31B1E7 → #7DDAFA to the centre, the hard highlight #9DE2FB +0.07…+0.15, #4CC8F6 → #3DC4F6 to +0.41, bright rim
//    #32CFF9 +0.42…+0.51; a grey shadow translated (−0.05, +0.15) p. Each band has its own alpha (no group opacity:
//    no offscreen pass) so a passing arrow shows through.
//  - mouths: `pipeMouth` at each end cell centre (anchor 23.04, 9.6 of 47 × 30 pt; drawn opening DOWN, rotated per `out`).
//  - counter: `pipeCounter` centred on `counter_at` (cells), rotated 90° on a vertical run; the number is live glyphs
//    (DigitGlyphs, white face, #822521 outline, upright).
//  - the count swaps (no pop) when the passing head comes out of the far mouth (`pipe.countAt leave`, the plan's
//    `.pipeCount` beat); the last pass shatters everything 0.05 s after the head leaves (`.pipeBreak` + breakAfterLeave):
//    ≈ 40 cyan shards, the counter box in two tumbling halves, both gold rims dropping; `.pipeBroken(id)` from that beat.

@MainActor final class CounterDigits {
    let root = CALayer()
    let outline = CAShapeLayer()
    let face = CAShapeLayer()
    let height: CGFloat
    private(set) var shown: Int
    private var pending: [(t: CFTimeInterval, v: Int)] = []

    init(value: Int, height: CGFloat, faceColor: CGColor, outlineColor: CGColor, outlineWidth: CGFloat, scale: CGFloat) {
        self.height = height
        shown = value
        outline.fillColor = nil
        outline.strokeColor = outlineColor
        outline.lineWidth = outlineWidth
        outline.lineJoin = .round
        face.fillColor = faceColor
        face.strokeColor = nil
        for l in [outline, face] {
            l.contentsScale = scale
            root.addSublayer(l)
        }
        setPaths(value)
    }

    func path(_ v: Int) -> CGPath {
        let g = DigitGlyphs.shared.path(String(max(0, v)))
        let box = g.boundingBoxOfPath
        let k = box.height > 0 ? height / box.height : 1
        var t = CGAffineTransform(scaleX: k, y: k)
        return g.copy(using: &t) ?? g
    }

    private func setPaths(_ v: Int) {
        let p = path(v)
        outline.path = p
        face.path = p
    }

    /// Shows `v` from `at` (parent-local time) on; several pending swaps are merged into one discrete keyframe track.
    func schedule(_ v: Int, at: CFTimeInterval, now: CFTimeInterval) {
        pending.removeAll { $0.t <= now }
        pending.append((at, v))
        pending.sort { $0.t < $1.t }
        // the value showing now: the base (`shown` before the first pending swap)
        let startV = shown
        guard let last = pending.last else { return }
        if last.t <= now + 0.0001 && pending.count == 1 {
            shown = v
            setPaths(v)
            pending = []
            return
        }
        var values: [CGPath] = [path(startV)]
        var times: [Double] = [0]
        let dur = max(0.001, last.t - now)
        for s in pending {
            values.append(path(s.v))
            times.append(max(0, min(1, (s.t - now) / dur)))
        }
        shown = last.v
        setPaths(last.v)
        for l in [outline, face] {
            let a = CAKeyframeAnimation(keyPath: "path")
            a.values = values
            a.keyTimes = times.map { NSNumber(value: $0) }
            a.calculationMode = .discrete
            a.duration = dur
            a.beginTime = now
            a.fillMode = .backwards
            l.add(a.hi(), forKey: "count")
        }
    }

    /// The value on screen right now is `shown` once every pending swap has passed.
    func committed(now: CFTimeInterval) {
        pending.removeAll { $0.t <= now }
    }
}

@MainActor final class PipeNode {
    let id: ObstacleID
    let spec: ObstacleSpec
    let tube: [Cell]
    let root = CALayer()
    var digits: CounterDigits?
    var counterRect: CGRect = .null
    var mouthLayers: [CALayer] = []
    var counterLayer: CALayer?
    var broken = false
    var remaining: Int?

    init(spec: ObstacleSpec, geo: BoardGeometry, art: BoardArt, scale: CGFloat) {
        id = spec.id
        self.spec = spec
        remaining = spec.counter
        let p = geo.pitch
        let ordered = Self.ordered(spec)
        tube = ordered
        let bounds = CGRect(origin: .zero, size: geo.layout.contentSize)
        let root = self.root
        root.frame = bounds
        // the centreline, extended 0.2 p under each mouth collar
        var pts = ordered.map(geo.centre)
        if pts.count == 1 { pts.append(pts[0]) }
        if let e0 = spec.ends.first(where: { $0.cell == ordered.first }) ?? spec.ends.first, pts.count >= 2 {
            pts[0] = CGPoint(x: pts[0].x + CGFloat(e0.out.dc) * 0.2 * p, y: pts[0].y + CGFloat(e0.out.dr) * 0.2 * p)
        }
        if let e1 = spec.ends.first(where: { $0.cell == ordered.last }) ?? spec.ends.last, pts.count >= 2 {
            let n = pts.count - 1
            pts[n] = CGPoint(x: pts[n].x + CGFloat(e1.out.dc) * 0.2 * p, y: pts[n].y + CGFloat(e1.out.dr) * 0.2 * p)
        }
        let line = CGMutablePath()
        line.addLines(between: pts)
        func band(_ o: CGFloat, _ w: CGFloat, _ hex: String, _ alpha: CGFloat, dx: CGFloat? = nil, dy: CGFloat? = nil) {
            var t = CGAffineTransform(translationX: (dx ?? o) * p, y: (dy ?? -o) * p)
            let l = CAShapeLayer()
            l.path = line.copy(using: &t)
            l.fillColor = nil
            l.strokeColor = BoardConfig.color(hex).copy(alpha: alpha)
            l.lineWidth = w * p
            l.lineJoin = .round
            l.lineCap = .butt
            l.contentsScale = scale
            l.frame = bounds
            root.addSublayer(l)
        }
        // PUBLISH R7 (D1 skin, SPEC.md ruling 46): the bands keep the measured profile + alphas, recoloured to COPPER
        // (art/ui/src/d1_skin.py material "copper", the same map as the pipe card icon and shards).
        // translucent glass: the base carries ~half the ink, each band ~0.6, so a passing arrow shows through (lighter blue)
        band(0, 1.0, "#A6A6A6", 0.35, dx: -0.05, dy: 0.15)          // shadow, down-left
        band(0, 1.02, "#C66222", 0.52)                               // base
        band(-0.355, 0.19, "#BF5C1D", 0.62)                          // dark band −0.45…−0.26
        band(-0.18, 0.16, "#D26F2F", 0.55)                           // ramp
        band(-0.015, 0.17, "#EE985F", 0.58)                          // light centre
        band(0.11, 0.08, "#F1AD80", 0.9)                             // hard highlight +0.07…+0.15
        band(0.24, 0.18, "#E48443", 0.55)                            // +0.15…+0.33
        band(0.37, 0.08, "#E3813F", 0.55)                            // to +0.41
        band(0.465, 0.09, "#EE9050", 0.9)                            // bright rim
        band(-0.48, 0.05, "#EB8D4D", 0.85)                           // left rim
        // mouths
        var mouths: [CALayer] = []
        if let img = art.image("pipeMouth") {
            for e in spec.ends {
                let m = CALayer()
                m.contents = img
                m.contentsGravity = .resize
                let w = CGFloat(img.width) * p / 96, h = CGFloat(img.height) * p / 96
                m.bounds = CGRect(x: 0, y: 0, width: w, height: h)
                m.anchorPoint = CGPoint(x: 23.04 / 47.0, y: 9.6 / 30.0)
                m.position = geo.centre(e.cell)
                let a: CGFloat
                switch e.out {
                case .down: a = 0
                case .up: a = .pi
                case .left: a = .pi / 2
                case .right: a = -.pi / 2
                }
                m.setAffineTransform(CGAffineTransform(rotationAngle: a))
                root.addSublayer(m)
                mouths.append(m)
            }
        }
        mouthLayers = mouths
        // the counter box + live number
        if let at = spec.counterAt, at.count == 2, let img = art.image("pipeCounter"), let n = spec.counter {
            let o = geo.centre(Cell(0, 0))
            let c = CGPoint(x: o.x + CGFloat(at[0]) * p, y: o.y + CGFloat(at[1]) * p)
            let box = CALayer()
            box.contents = img
            box.contentsGravity = .resize
            let w = CGFloat(img.width) * p / 96, h = CGFloat(img.height) * p / 96
            box.bounds = CGRect(x: 0, y: 0, width: w, height: h)
            box.anchorPoint = CGPoint(x: 34.0 / 68.0, y: 24.9 / 53.0)
            box.position = c
            let vertical = Self.isVertical(at: at, tube: ordered)
            if vertical { box.setAffineTransform(CGAffineTransform(rotationAngle: .pi / 2)) }
            root.addSublayer(box)
            counterLayer = box
            counterRect = CGRect(x: c.x - w / 2, y: c.y - h / 2, width: w, height: h)
            let d = CounterDigits(value: n, height: 0.56 * p, faceColor: UIColor.white.cgColor,
                                  outlineColor: BoardConfig.color("#124346"), outlineWidth: 0.13 * p, scale: scale)
            d.root.position = CGPoint(x: c.x, y: c.y + (vertical ? 0 : 0.02 * p))
            root.addSublayer(d.root)
            digits = d
        }
    }

    /// The tube cells mouth → mouth (the ◆ model orders them; imports may not: walk from end 0, BFS fallback).
    static func ordered(_ o: ObstacleSpec) -> [Cell] {
        guard o.ends.count == 2 else { return o.cells }
        let set = Set(o.cells)
        let a = o.ends[0].cell, b = o.ends[1].cell
        if o.cells.first == a, o.cells.last == b { return o.cells }
        if o.cells.first == b, o.cells.last == a { return Array(o.cells.reversed()) }
        var prev: [Cell: Cell] = [:]
        var queue = [a]
        var seen: Set<Cell> = [a]
        var k = 0
        while k < queue.count {
            let c = queue[k]; k += 1
            if c == b { break }
            for d in Dir.allCases {
                let n = c + d
                if set.contains(n), !seen.contains(n) { seen.insert(n); prev[n] = c; queue.append(n) }
            }
        }
        guard seen.contains(b) else { return o.cells }
        var path = [b]
        while let p = prev[path[path.count - 1]] { path.append(p) }
        return path.reversed()
    }

    static func isVertical(at: [Double], tube: [Cell]) -> Bool {
        if at[1] != at[1].rounded() { return true }
        if at[0] != at[0].rounded() { return false }
        let c = Cell(Int(at[0]), Int(at[1]))
        if let i = tube.firstIndex(of: c) {
            let n = i + 1 < tube.count ? tube[i + 1] : (i > 0 ? tube[i - 1] : c)
            return n.c == c.c
        }
        return false
    }

    /// Shatter: everything vanishes at `at` after `begin` (render-exact); shards, the counter halves and the rims.
    func shatter(engine e: BoardEngine, begin: CFTimeInterval, at: Double, pitch p: CGFloat) {
        broken = true
        Anim.switchOpacity(root, from: 1, to: 0, begin: begin, at: at, key: "break")
        var rng = FXRandom(seed: e.stage?.setup.seed ?? 1, label: "pipe:\(id.raw)")
        let geo = e.stage?.geo
        var pts: [CGPoint] = []
        var looks: [ShardPool.Look] = []
        // FIX-V2 F-05 (S1-L35-pipe-break): chunky cyan glass shards laid ALONG the tube (≈ 4.5 per tube cell, in tube order, so
        // the break holds the tube's footprint on its first frames) with their grey drop shadows; was 40 small flat flecks
        // at random tube cells
        let n = max(e.fx.pipeShards.count, min(130, Int((Double(tube.count) * 4.5).rounded())))
        for i in 0..<n {
            let c = tube.isEmpty ? Cell(0, 0) : tube[(i * max(1, tube.count)) / n % max(1, tube.count)]
            let o = geo?.centre(c) ?? .zero
            pts.append(CGPoint(x: o.x + CGFloat(rng.range(-0.36, 0.36)) * p, y: o.y + CGFloat(rng.range(-0.36, 0.36)) * p))
            let sz = CGFloat(rng.range(0.60, 0.90)) * p
            looks.append(ShardPool.Look(image: "sh3d.pipe", rect: ShardArt.rect(Int(rng.unit() * Double(ShardArt.cells))),
                                        size: CGSize(width: sz, height: sz), angle: CGFloat(rng.range(-0.6, 0.6)),
                                        shadow: "sh3d.pipe.shadow", shadowDY: 0.17 * p))
        }
        e.burstShards(kind: .pipe, points: pts, looks: looks, begin: begin + at, life: e.fx.pipeShards.life, hiddenUntilBegin: true)
        if let box = counterLayer, !counterRect.isNull {
            let w = counterRect.width, h = counterRect.height
            // the counter box CRACKS in two: the halves start 0.05 w apart and tilted ±7° (the phone's split box on the first
            // frame after the break), then tumble as before
            let halves = [CGPoint(x: counterRect.midX - w / 4 - 0.05 * w, y: counterRect.midY),
                          CGPoint(x: counterRect.midX + w / 4 + 0.05 * w, y: counterRect.midY)]
            let looksH = [ShardPool.Look(image: "pipeCounter", rect: CGRect(x: 0, y: 0, width: 0.5, height: 1), size: CGSize(width: w / 2, height: h),
                                         angle: -0.12),
                          ShardPool.Look(image: "pipeCounter", rect: CGRect(x: 0.5, y: 0, width: 0.5, height: 1), size: CGSize(width: w / 2, height: h),
                                         angle: 0.12)]
            _ = box
            e.burstShards(kind: .pipeHalf, points: halves, looks: looksH, vxSign: [-1, 1], begin: begin + at,
                          life: e.fx.pipeShards.life, hiddenUntilBegin: true)
        }
        if !mouthLayers.isEmpty {
            let rims = mouthLayers.map(\.position)
            let size = mouthLayers[0].bounds.size
            let looksR = rims.map { _ in ShardPool.Look(image: "pipeMouth", size: size) }
            e.burstShards(kind: .pipeRim, points: rims, looks: looksR, begin: begin + at, life: e.fx.pipeShards.life,
                          hiddenUntilBegin: true)
        }
    }
}
