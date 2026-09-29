import UIKit
import PathCore

// B2 (SPEC-architecture §5.6 "box" / "curtain"; SPEC.md §5.11: the videos' Curtain/Box levels use the phone's BOX skin;
// SPEC-ui §4.3 + CONSISTENCY O-21: a CODE-DRAWN slab + the `boxRing` counter ring; SPEC-motion-audio §3.5.4).
// Slab (fractions of the pitch): covers its cell block exactly; corner radius 0.40; face #BC5BF6; a light top bevel line
// (#ECB2F3); left/right edges darkening toward #5935A2 over 0.26; bottom lip 0.28 (#AB50EB → #582D96 → #4F2F83); a soft grey
// shadow 0.1 below; four rivets ⌀ 0.30 inset 0.35 from the corners. Ring ⌀ 2.2 p centred (0.85 × the short side for a
// block < 2.5 cells): the `boxRing` sprite when the art ships it, else drawn here (silver sphere lit top-left #E5F2FB →
// #48498C with four diagonal stub cylinders, a purple ring #5D46AE → #C698FF around a navy well #142C6A → #1F3C80 holding
// the live count: white face, #4B1F86 outline, 0.8 p). Every accepted exit lowers EVERY box by its member count on the tap
// frame (instant glyph swap, all boxes together, "0" never drawn); at 0 the box and ring vanish on that frame with
// ≈ 140 purple shards + 4 silver ring chunks (g 1275 pt/s², 0.67 s), and the board reports `.counterBroken(id)`.

@MainActor final class BoxNode {
    let id: ObstacleID
    let spec: ObstacleSpec
    let block: CGRect
    let root = CALayer()
    var digits: CounterDigits?
    let ringCentre: CGPoint
    let ringDiameter: CGFloat
    var broken = false
    var remaining: Int?

    init(spec: ObstacleSpec, geo: BoardGeometry, art: BoardArt, scale: CGFloat) {
        id = spec.id
        self.spec = spec
        remaining = spec.counter
        let p = geo.pitch
        let cs = spec.cells.isEmpty ? [Cell(0, 0)] : spec.cells
        let minC = cs.map(\.c).min()!, maxC = cs.map(\.c).max()!
        let minR = cs.map(\.r).min()!, maxR = cs.map(\.r).max()!
        let tl = geo.centre(Cell(minC, minR))
        block = CGRect(x: tl.x - p / 2, y: tl.y - p / 2, width: CGFloat(maxC - minC + 1) * p, height: CGFloat(maxR - minR + 1) * p)
        let short = min(block.width, block.height)
        let dia = short < 2.5 * p ? 0.85 * short : 2.2 * p
        ringDiameter = dia
        ringCentre = CGPoint(x: block.midX, y: block.midY - 0.14 * p)
        let root = self.root
        root.frame = block.insetBy(dx: -0.05 * p, dy: -0.05 * p).union(block.offsetBy(dx: 0, dy: 0.12 * p))
        let o = CGPoint(x: block.minX - root.frame.minX, y: block.minY - root.frame.minY)
        let r = 0.40 * p
        let local = CGRect(origin: o, size: block.size)
        @discardableResult
        func shape(_ path: CGPath, fill: String?, alpha: CGFloat = 1, stroke: String? = nil, width: CGFloat = 0) -> CAShapeLayer {
            let l = CAShapeLayer()
            l.path = path
            l.fillColor = fill.map { BoardConfig.color($0).copy(alpha: alpha)! }
            l.strokeColor = stroke.map { BoardConfig.color($0) }
            l.lineWidth = width
            l.contentsScale = scale
            root.addSublayer(l)
            return l
        }
        func rrect(_ rc: CGRect, _ rad: CGFloat) -> CGPath {
            let rr = min(rad, rc.width / 2, rc.height / 2)
            return CGPath(roundedRect: rc, cornerWidth: rr, cornerHeight: rr, transform: nil)
        }
        // PUBLISH R7 (D1 skin, SPEC.md ruling 46): same slab recipe, MOSS stone (d1_skin.py "moss"); ring fallback = steel +
        // brass + deep teal well; the counter outline deep teal.
        shape(rrect(local.offsetBy(dx: 0, dy: 0.1 * p), r), fill: "#000000", alpha: 0.16)              // soft shadow
        shape(rrect(local, r), fill: "#314721")                                                          // lip, darkest
        shape(rrect(CGRect(x: local.minX, y: local.minY, width: local.width, height: local.height - 0.09 * p), r), fill: "#334D1F")
        shape(rrect(CGRect(x: local.minX, y: local.minY, width: local.width, height: local.height - 0.19 * p), r), fill: "#5A8A2D")
        let faceRect = CGRect(x: local.minX, y: local.minY, width: local.width, height: local.height - 0.28 * p)
        shape(rrect(faceRect, r), fill: "#375421")                                                       // edge shade
        shape(rrect(faceRect.insetBy(dx: 0.13 * p, dy: 0), max(0, r - 0.1 * p)), fill: "#537F2A")
        shape(rrect(faceRect.insetBy(dx: 0.26 * p, dy: 0.02 * p), max(0, r - 0.2 * p)), fill: "#649634")  // face
        let bevel = CGMutablePath()
        bevel.move(to: CGPoint(x: faceRect.minX + r, y: faceRect.minY + 0.05 * p))
        bevel.addLine(to: CGPoint(x: faceRect.maxX - r, y: faceRect.minY + 0.05 * p))
        let bl = shape(bevel, fill: nil, stroke: "#B3CF8A", width: 0.045 * p)
        bl.lineCap = .round
        // rivets
        let rv = CGMutablePath(), rh = CGMutablePath()
        let inset = 0.35 * p, rd = 0.15 * p
        for (x, y) in [(faceRect.minX + inset, faceRect.minY + inset), (faceRect.maxX - inset, faceRect.minY + inset),
                       (faceRect.minX + inset, faceRect.maxY - inset), (faceRect.maxX - inset, faceRect.maxY - inset)] {
            rv.addEllipse(in: CGRect(x: x - rd, y: y - rd, width: 2 * rd, height: 2 * rd))
            rh.addEllipse(in: CGRect(x: x - rd * 0.75, y: y - rd * 0.8, width: rd * 0.9, height: rd * 0.8))
        }
        shape(rv, fill: "#406521")
        shape(rh, fill: "#BED699", alpha: 0.9)
        // the ring
        let rc = CGPoint(x: ringCentre.x - root.frame.minX, y: ringCentre.y - root.frame.minY)
        if let img = art.image("boxRing") {
            let l = CALayer()
            l.contents = img
            l.contentsGravity = .resize
            l.bounds = CGRect(x: 0, y: 0, width: dia, height: dia)
            l.position = rc
            root.addSublayer(l)
        } else {
            Self.drawRing(into: root, centre: rc, diameter: dia, scale: scale)
        }
        if let n = spec.counter {
            let d = CounterDigits(value: n, height: 0.8 * p * dia / (2.2 * p) * 0.72, faceColor: UIColor.white.cgColor,
                                  outlineColor: BoardConfig.color("#054145"), outlineWidth: 0.12 * p * dia / (2.2 * p),
                                  scale: scale)
            d.root.position = rc
            root.addSublayer(d.root)
            digits = d
        }
    }

    /// The counter ring in code (our drawing of STYLE §A.2's crate ring at ⌀ 2.2 p).
    static func drawRing(into parent: CALayer, centre c: CGPoint, diameter dia: CGFloat, scale: CGFloat) {
        let u = dia / 2.72                                            // crate units: stubs reach r 1.36
        func circle(_ r: CGFloat) -> CGPath { CGPath(ellipseIn: CGRect(x: c.x - r, y: c.y - r, width: 2 * r, height: 2 * r), transform: nil) }
        func add(_ path: CGPath, _ fill: String, _ stroke: String? = nil, _ w: CGFloat = 0) {
            let l = CAShapeLayer()
            l.path = path
            l.fillColor = BoardConfig.color(fill)
            l.strokeColor = stroke.map(BoardConfig.color)
            l.lineWidth = w
            l.contentsScale = scale
            parent.addSublayer(l)
        }
        // four stub cylinders on the diagonals
        let stubs = CGMutablePath(), caps = CGMutablePath()
        for k in 0..<4 {
            let a = CGFloat.pi / 4 + CGFloat(k) * .pi / 2
            var t = CGAffineTransform(translationX: c.x, y: c.y).rotated(by: a)
            stubs.addPath(CGPath(roundedRect: CGRect(x: 0.7 * u, y: -0.29 * u, width: 0.66 * u, height: 0.58 * u),
                                 cornerWidth: 0.1 * u, cornerHeight: 0.1 * u, transform: &t))
            caps.addPath(CGPath(ellipseIn: CGRect(x: 1.22 * u, y: -0.29 * u, width: 0.16 * u, height: 0.58 * u), transform: &t))
        }
        add(stubs, "#ABB9BA", "#5A6667", 0.05 * u)
        add(caps, "#E4F3F4")
        // the sphere: base, shade and a top-left light
        add(circle(1.07 * u), "#6E7B7C")
        let lit = CAGradientLayer()
        lit.type = .radial
        let r = 1.07 * u
        lit.frame = CGRect(x: c.x - r, y: c.y - r, width: 2 * r, height: 2 * r)
        lit.startPoint = CGPoint(x: 0.36, y: 0.33)
        lit.endPoint = CGPoint(x: 1.02, y: 1.02)
        lit.colors = [BoardConfig.color("#E5F3F4"), BoardConfig.color("#AEBCBD"), BoardConfig.color("#465253").copy(alpha: 0)!]
        lit.locations = [0, 0.55, 1]
        lit.contentsScale = scale
        lit.cornerRadius = r                                          // clipped to the sphere (one layer, no sublayers)
        lit.masksToBounds = true
        parent.addSublayer(lit)
        add(circle(0.68 * u), "#D48F0B", "#9D6301", 0.1 * u)          // the purple ring
        add(circle(0.53 * u), "#0D363A")                               // the navy well
        add(circle(0.44 * u), "#13474A")
    }

    /// The count on screen from `at` (parent-local) on.
    func schedule(_ v: Int, at: CFTimeInterval, now: CFTimeInterval) {
        remaining = v
        guard v > 0 else { return }                                  // "0" is never drawn: the break hides the box
        digits?.schedule(v, at: at, now: now)
    }

    /// The break at `at` after `begin`: everything vanishes, 140 purple shards away from the centre line + 4 ring chunks.
    func shatter(engine e: BoardEngine, begin: CFTimeInterval, at: Double, pitch p: CGFloat) {
        broken = true
        Anim.switchOpacity(root, from: 1, to: 0, begin: begin, at: at, key: "break")
        var rng = FXRandom(seed: e.stage?.setup.seed ?? 1, label: "box:\(id.raw)")
        // FIX-V2 F-05 (S1-L50-box-break): the phone's chunky 3-D purple shards HOLD the slab's footprint on the break frame
        // (a jittered mosaic, each chunk ≈ 0.8 of its tile with a grey drop shadow 0.19 p below), then part away
        // from the centre line and fall; the ring breaks into 4 chunks of its own art. Was 140 small flat quads scattered
        // at random and 4 grey blobs.
        // the phone's chunks tile the slab at ≈ 0.85 p (L50 at p 23.5: ~14-16 × 4-5 chunks of 12-15 pt, S1-L50-box-break 0.465);
        // `shards.box.count` caps the mosaic
        let tile = 0.70 * p
        var cols = max(1, Int((block.width / tile).rounded()))
        var rows = max(1, Int((block.height / tile).rounded()))
        let cap = max(4, e.fx.boxShards.count)
        while cols * rows > cap { if cols >= rows { cols -= 1 } else { rows -= 1 } }
        let tw = block.width / CGFloat(cols), th = block.height / CGFloat(rows)
        var pts: [CGPoint] = []
        var looks: [ShardPool.Look] = []
        var signs: [Double] = []
        for r in 0..<rows {
            for c in 0..<cols {
                let q = CGPoint(x: block.minX + (CGFloat(c) + 0.5 + CGFloat(rng.range(-0.28, 0.28))) * tw,
                                y: block.minY + (CGFloat(r) + 0.5 + CGFloat(rng.range(-0.32, 0.32))) * th)
                pts.append(q)
                signs.append(q.x < block.midX ? -1 : 1)
                let s = max(tw, th) * CGFloat(rng.range(1.1, 1.4))
                looks.append(ShardPool.Look(image: "sh3d.box", rect: ShardArt.rect(Int(rng.unit() * Double(ShardArt.cells))),
                                            size: CGSize(width: s, height: s), angle: CGFloat(rng.range(-0.5, 0.5)),
                                            shadow: "sh3d.box.shadow", shadowDY: 0.19 * p))
            }
        }
        e.burstShards(kind: .box, points: pts, looks: looks, vxSign: signs, begin: begin + at, life: e.fx.boxShards.life,
                      hiddenUntilBegin: true)
        let q = ringDiameter / 4
        let chunks = [CGPoint(x: ringCentre.x - q, y: ringCentre.y - q), CGPoint(x: ringCentre.x + q, y: ringCentre.y - q),
                      CGPoint(x: ringCentre.x - q, y: ringCentre.y + q), CGPoint(x: ringCentre.x + q, y: ringCentre.y + q)]
        let cl: [ShardPool.Look]
        if let ring = e.boardArt.image("boxRing") {
            e.shards.setImage("boxRing", ring)
            let half = CGSize(width: ringDiameter / 2, height: ringDiameter / 2)
            cl = [CGRect(x: 0, y: 0, width: 0.5, height: 0.5), CGRect(x: 0.5, y: 0, width: 0.5, height: 0.5),
                  CGRect(x: 0, y: 0.5, width: 0.5, height: 0.5), CGRect(x: 0.5, y: 0.5, width: 0.5, height: 0.5)]
                .map { ShardPool.Look(image: "boxRing", rect: $0, size: half) }
        } else {
            let silver = BoardConfig.color("#C1CFD0")
            cl = chunks.map { _ in ShardPool.Look(color: silver, size: CGSize(width: q * 1.6, height: q * 1.2), corner: q * 0.5) }
        }
        e.burstShards(kind: .ring, points: chunks, looks: cl, vxSign: [-1, 1, -1, 1], begin: begin + at, life: e.fx.boxShards.life,
                      hiddenUntilBegin: true)
    }
}
