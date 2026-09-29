import UIKit
import PathCore

// B2 (SPEC-architecture §5.5, §10.2 "Tap handler ≤ 2 ms p99 solid"; D1a finding F4: the L032 tap-handler p99 was 4.06 ms,
// a 4-arrow tape bundle = 4 movers from one tap). A STRAIGHT exit (a straight body leaving along its own ray, no tube or
// corner: most exits, and every tape bundle member) is a RIGID TRANSLATION of the resting shapes along the direction:
//  - one additive `position` keyframe track (the same ExitKinematics samples at every display frame, exact linear) on a
//    mover root that holds the body + head shapes with the resting node's own paths (nothing is re-built, and the render
//    server moves a small layer instead of re-stroking a trimmed path every frame);
//  - the samples, the track and the star emitter's tracks depend only on (direction, travel to the far edge), so every
//    member of a bundle and every same-length exit of one tap SHARES them (built once per tap: `ExitShare`);
//  - solid: the colour ramp animates the body/head colours themselves (B1's mechanism); violet / rainbow: ONE axial
//    gradient covering the straight path (the field fixed on the path, MA5) masked by the moving body + head, and the
//    resting colour on top fading out over the ramp;
//  - stars: one emitter per member (absolute tail track built from the shared samples; its birth-rate track shared) —
//    stars stay where they are born (the emitter layer itself never moves).
// Bent exits (snakes, tubes, corners) keep B1's trimmed-stroke mover.

@MainActor final class ExitShare {
    let times: [Double]
    let travel: [CGFloat]
    let duration: Double
    let move: CAKeyframeAnimation          // additive position offsets (dir × travel)
    let stars: CAKeyframeAnimation?       // additive emitterPosition offsets, up to the stop
    let birth: CAKeyframeAnimation?
    let tStop: Double

    init(times: [Double], travel: [CGFloat], duration: Double, move: CAKeyframeAnimation, stars: CAKeyframeAnimation?,
         birth: CAKeyframeAnimation?, tStop: Double) {
        self.times = times; self.travel = travel; self.duration = duration; self.move = move; self.stars = stars
        self.birth = birth; self.tStop = tStop
    }
}

extension BoardEngine {
    /// Whether an exit along `plan` is a rigid translation (straight body, straight ray, no tube / corner).
    func isStraightExit(_ node: ArrowNode, plan: ExitPath?) -> Bool {
        guard node.rest.vertices.count == 2 else { return false }
        guard let plan else { return true }
        for s in plan.segments {
            switch s {
            case .tube, .corner: return false
            default: break
            }
        }
        let h = headCell(node.spec)
        let d = node.spec.dir
        let own = node.spec.cells.count
        for (i, c) in plan.cells.dropFirst(own).enumerated() where c != h.moved(d, by: i + 1) { return false }
        return true
    }

    /// The rigid-translation exit (see the file header). Call inside the tap's no-actions transaction.
    func startStraightExit(_ node: ArrowNode, path plan: ExitPath?, combo: Int, begin t0: CFTimeInterval) -> Mover? {
        guard let st = stage else { return nil }
        let prof = ExitProfile.on
        var pt = prof ? CACurrentMediaTime() : 0
        func mark(_ k: Int) { if prof { let n = CACurrentMediaTime(); ExitProfile.add(k, n - pt); pt = n } }
        let geo = st.geo
        let p = geo.pitch
        let spec = node.spec
        let own = spec.cells.count
        let beyondCount = plan.map { max(0, $0.cells.count - own) } ?? 0
        let d = dirVector(spec.dir)
        let restLen = node.rest.length
        let travelEnd = straightTravelEnd(node, beyondCount: beyondCount, far: farRect())
        let share = exitShare(dir: spec.dir, travelEnd: travelEnd, pitch: p)
        mark(0)

        let m = Mover(id: spec.id, kind: .exit, begin: t0)
        m.duration = share.duration
        m.times = share.times
        m.travel = share.travel
        m.pitch = p
        m.dirVec = d
        m.straight = true
        m.fastPath = true
        let leftTravel = config.leftBoardAtLastCell ? restLen + p * 0.5 : restLen + CGFloat(beyondCount) * p + p * 0.5
        m.leftBoardAt = kinematics.time(toTravel: Double(min(leftTravel, travelEnd) / p))
        // the moving root: the resting body + head, moved rigidly
        let bodyFrame = node.body.frame
        let headFrame = node.head.frame
        let box = bodyFrame.union(headFrame)
        m.root.frame = box
        // A3: the model sits at the final place (off the board); the additive track runs −travelEnd → 0 (see `exitShare`)
        let finalShift = CGPoint(x: d.dx * travelEnd, y: d.dy * travelEnd)
        m.headStartLocal = m.root.position
        m.root.position = CGPoint(x: m.root.position.x + finalShift.x, y: m.root.position.y + finalShift.y)
        let move = share.move
        move.beginTime = t0
        m.root.add(move, forKey: "move")
        let color = node.color
        let painter = painterFor(combo: combo)
        let body = CAShapeLayer()
        body.frame = bodyFrame.offsetBy(dx: -box.minX, dy: -box.minY)
        body.path = node.body.path
        body.fillColor = nil
        body.lineWidth = node.body.lineWidth
        body.lineCap = .round
        body.lineJoin = .round
        body.contentsScale = screenScale
        let headL = CAShapeLayer()
        headL.bounds = node.head.bounds
        headL.path = node.head.path
        headL.position = CGPoint(x: node.head.position.x - box.minX, y: node.head.position.y - box.minY)
        headL.setAffineTransform(node.head.affineTransform())
        headL.contentsScale = screenScale
        let ramp = config.colourRamp
        let field = (painter as? FieldPainter).map { ColourField(palette: $0.palette, period: $0.period, phase: fxRng.unit()) }
        mark(1)
        if let field {
            // the field: one axial gradient along the straight path (tail start → far edge), masked by the moving shapes
            let tail = node.rest.vertices[0]
            let endPt = CGPoint(x: tail.x + d.dx * travelEnd, y: tail.y + d.dy * travelEnd)
            let halfW = p * 0.33 + 1
            let pathBox = CGRect(x: min(tail.x, endPt.x), y: min(tail.y, endPt.y), width: abs(endPt.x - tail.x), height: abs(endPt.y - tail.y))
                .insetBy(dx: -(abs(d.dy) * halfW + abs(d.dx) * p), dy: -(abs(d.dx) * halfW + abs(d.dy) * p))
            let content = CALayer()
            content.frame = pathBox
            let gl = Self.fieldGradient(field: field, from: tail, dir: d, length: travelEnd + restLen + p, pitch: p,
                                        frame: CGRect(origin: .zero, size: pathBox.size), origin: pathBox.origin)
            content.addSublayer(gl)
            let mask = CALayer()
            mask.frame = content.bounds
            let mover = CALayer()
            mover.frame = box.offsetBy(dx: -pathBox.minX, dy: -pathBox.minY)
            mover.position = CGPoint(x: mover.position.x + finalShift.x, y: mover.position.y + finalShift.y)   // A3: final model
            body.strokeColor = UIColor.black.cgColor
            headL.fillColor = UIColor.black.cgColor
            mover.addSublayer(body)
            mover.addSublayer(headL)
            mover.add(move, forKey: "move")
            mask.addSublayer(mover)
            content.mask = mask
            roots.mover.addSublayer(content)
            m.extras.append(content)
            // the resting colour on top, fading out (in the moving root)
            if ramp > 0 {
                let rb = CAShapeLayer(), rh = CAShapeLayer()
                for (l, src) in [(rb, body), (rh, headL)] {
                    l.frame = src.frame
                    l.bounds = src.bounds
                    l.position = src.position
                    l.path = src.path
                    l.lineWidth = src.lineWidth
                    l.lineCap = .round
                    l.lineJoin = .round
                    l.setAffineTransform(src.affineTransform())
                    l.contentsScale = screenScale
                    l.opacity = 0
                    l.add(Anim.basic("opacity", from: 1, to: 0, duration: ramp, begin: t0), forKey: "ramp")
                }
                rb.fillColor = nil
                rb.strokeColor = color
                rh.fillColor = color
                m.root.addSublayer(rb)
                m.root.addSublayer(rh)
            }
            m.headLayer = m.root
        } else {
            let c = config.exitColor
            body.strokeColor = c
            headL.fillColor = c
            if ramp > 0 {
                body.add(Anim.basic("strokeColor", from: color, to: c, duration: ramp, begin: t0), forKey: "ramp")
                headL.add(Anim.basic("fillColor", from: color, to: c, duration: ramp, begin: t0), forKey: "ramp")
            }
            m.root.addSublayer(body)
            m.root.addSublayer(headL)
            m.headLayer = m.root
        }
        roots.mover.addSublayer(m.root)
        node.setVisible(false)
        mark(2)
        addStraightStars(node: node, share: share, field: field, begin: t0)
        mark(3)
        let id = spec.id
        Anim.beat(on: m.root, key: "leftBoard", begin: t0, delay: m.leftBoardAt) { [weak self, weak m] finished in
            guard finished, let self, let m, self.movers[id] === m else { return }
            self.moverLeftBoard(id)
        }
        Anim.beat(on: m.root, key: "end", begin: t0, delay: share.duration) { [weak self, weak m] finished in
            guard finished, let self, let m, self.movers[id] === m else { return }
            self.finishMover(id)
        }
        mark(4)
        return m
    }

    /// The travel at which a straight exit's TAIL (cap included) has left the far rect.
    func straightTravelEnd(_ node: ArrowNode, beyondCount: Int, far: CGRect) -> CGFloat {
        guard let st = stage else { return 0 }
        let p = st.geo.pitch
        let d = dirVector(node.spec.dir)
        let head = node.headCentre
        let lastPt = CGPoint(x: head.x + d.dx * CGFloat(beyondCount) * p, y: head.y + d.dy * CGFloat(beyondCount) * p)
        let dEdge = BoardGeometry.distanceToEdge(from: lastPt, dir: d, in: far)
        return node.rest.length + CGFloat(beyondCount) * p + dEdge + st.geo.lineWidth
    }

    /// The samples and shared tracks for (direction, travel) in this tap (built once, reused by every same-length exit).
    func exitShare(dir: Dir, travelEnd: CGFloat, pitch p: CGFloat) -> ExitShare {
        let key = "\(dir.rawValue):\(Int((travelEnd * 8).rounded())):\(Int((p * 100).rounded()))"
        if let s = exitShares[key] { return s }
        let kin = kinematics
        let tEnd = kin.time(toTravel: Double(travelEnd / p))
        var times: [Double] = []
        var t = 0.0
        let dt = max(config.keyframeStep, 1.0 / 240)
        while t < tEnd { times.append(t); t += dt }
        times.append(tEnd)
        let travel: [CGFloat] = times.map { min(travelEnd, CGFloat(kin.s($0)) * p) }
        let d = dirVector(dir)
        // A3 GLITCH (owner item 5, "a gone error for a millisecond" after an arrow tap): the offsets are relative to the
        // FINAL place (travelEnd along the direction, off the board: −travelEnd … 0) and the moving layers' MODEL position
        // is that final place (`startStraightExit`). Before, the model was the resting place and the track went 0 → travelEnd:
        // when the track ended at tEnd the render server drew the model — the resting arrow in the exit colour, or the
        // rainbow / violet field behind its mask — for the frame(s) before the main thread's "end" beat removed the layer
        // (blipscan, build/p/A3: a whole arrow back on its rest cells for one frame after straight exits). Holding the track
        // (isRemovedOnCompletion = false) fixed the solid root but not the field's MASK mover, so the model itself moves.
        let offsets = travel.map { NSValue(cgPoint: CGPoint(x: d.dx * ($0 - travelEnd), y: d.dy * ($0 - travelEnd))) }
        let move = Anim.keyframes("position", offsets, times: times, duration: tEnd, begin: 0)
        move.isAdditive = true
        move.isRemovedOnCompletion = false                  // and it holds its last offset (0) until the layer goes
        // stars: while the tail is inside the content rect (grid + 1-cell margin) — decided per exit below; the shared
        // tracks run to the end (the emitter's birthRate model is 0 after them)
        let stars: CAKeyframeAnimation? = nil
        var birth: CAKeyframeAnimation?
        if fx.starsOn {
            var rt: [Double] = []
            var rv: [NSNumber] = []
            var k = 0.0
            while k < tEnd { rt.append(k); rv.append(NSNumber(value: kin.v(k))); k += 1.0 / 30 }
            rt.append(tEnd); rv.append(NSNumber(value: kin.v(tEnd)))
            let b = Anim.keyframes("birthRate", rv, times: rt, duration: tEnd, begin: 1e-6)
            b.fillMode = .backwards
            birth = b
        }
        let s = ExitShare(times: times, travel: travel, duration: tEnd, move: move, stars: stars, birth: birth, tStop: tEnd)
        if exitShares.count >= 256 { exitShares.removeAll(keepingCapacity: true) }
        exitShares[key] = s
        return s
    }

    /// One axial gradient along a straight run (content coords): a stop at every palette step of σ = travel / p.
    static func fieldGradient(field: ColourField, from tail: CGPoint, dir d: CGVector, length: CGFloat, pitch p: CGFloat,
                              frame: CGRect, origin: CGPoint) -> CAGradientLayer {
        let gl = CAGradientLayer()
        gl.frame = frame
        // σ along the direction from the tail start; the layer's axis spans its full extent along d
        let horizontal = abs(d.dx) > 0.5
        let span = horizontal ? frame.width : frame.height
        let startCoord = horizontal ? (d.dx > 0 ? origin.x : origin.x + frame.width) : (d.dy > 0 ? origin.y : origin.y + frame.height)
        let tailCoord = horizontal ? tail.x : tail.y
        let sign: CGFloat = horizontal ? (d.dx > 0 ? 1 : -1) : (d.dy > 0 ? 1 : -1)
        let ua = (startCoord - tailCoord) * sign                      // σ·p at the gradient start
        let ub = ua + span
        let stepPt = CGFloat(field.period) * p / CGFloat(field.palette.count)
        var colors: [CGColor] = [field.colour(Double(ua / p))]
        var locs: [NSNumber] = [0]
        let pos0 = CGFloat(field.position(Double(ua / p)))
        var next = ua + (floor(pos0) + 1 - pos0) * stepPt
        var idx = (Int(floor(pos0)) + 1) % field.palette.count
        while next < ub - 0.01 {
            colors.append(field.palette[idx])
            locs.append(NSNumber(value: Double((next - ua) / span)))
            next += stepPt
            idx = (idx + 1) % field.palette.count
        }
        colors.append(field.colour(Double(ub / p)))
        locs.append(1)
        gl.colors = colors
        gl.locations = locs
        if horizontal {
            gl.startPoint = CGPoint(x: d.dx > 0 ? 0 : 1, y: 0.5)
            gl.endPoint = CGPoint(x: d.dx > 0 ? 1 : 0, y: 0.5)
        } else {
            gl.startPoint = CGPoint(x: 0.5, y: d.dy > 0 ? 0 : 1)
            gl.endPoint = CGPoint(x: 0.5, y: d.dy > 0 ? 1 : 0)
        }
        _ = length
        return gl
    }

    /// Stars for a straight exit: model position = the resting tail; the shared additive track moves the spawn point.
    func addStraightStars(node: ArrowNode, share: ExitShare, field: ColourField?, begin t0: CFTimeInterval) {
        guard fx.starsOn, let birth = share.birth, let image = StarTrail.image(sprites),
              let st = stage else { return }
        let p = st.geo.pitch
        let tail = node.rest.vertices[0]
        let tailExt = CGFloat(config.tailExtend) * p
        let d = dirVector(node.spec.dir)
        let tail0 = CGPoint(x: tail.x + d.dx * tailExt, y: tail.y + d.dy * tailExt)
        // emission stops when the tail leaves the content rect
        let rect = CGRect(origin: .zero, size: contentBounds.size)
        let toEdge = BoardGeometry.distanceToEdge(from: tail0, dir: d, in: rect)
        let tStop = min(share.duration, kinematics.time(toTravel: Double(toEdge / p)))
        guard tStop > 0.001 else { return }
        let em = CAEmitterLayer()
        em.frame = rect
        em.emitterShape = .circle
        em.emitterMode = .volume
        let jitter = CGFloat(fx.starJitter) * p
        em.emitterSize = CGSize(width: jitter, height: jitter)
        em.renderMode = .unordered
        em.seed = fxRng.u32()
        let fxRoot = roots.fx
        em.beginTime = fxRoot.convertTime(CACurrentMediaTime(), from: nil) - motionLead   // FEEL F3: the tap's motion lead
        em.emitterPosition = tail0
        let imgPx = CGFloat(image.width)
        func cell(_ name: String, rate: Double, color: CGColor) -> CAEmitterCell {
            let c = CAEmitterCell()
            c.name = name
            c.contents = image
            c.birthRate = Float(rate)
            c.lifetime = Float(fx.starLife)
            c.velocity = 0
            c.emissionRange = .pi * 2
            let s = CGFloat(fx.starSize) * p / imgPx
            c.scale = s
            c.scaleRange = CGFloat(fx.starSizeRange) * p / imgPx
            c.scaleSpeed = -(1 - CGFloat(fx.starEndScale)) * s / CGFloat(fx.starLife)
            c.alphaSpeed = Float(-1 / fx.starLife)
            c.spinRange = CGFloat(fx.starSpinDeg * .pi / 180)
            c.color = color
            return c
        }
        if let f = field {
            em.emitterCells = [cell("star", rate: fx.starsPerCell, color: f.stop(0))]
            var cTimes: [Double] = []
            var cVals: [CGColor] = []
            var k = 0.0
            while k <= tStop {
                let s = (kinematics.s(k) * Double(p) + Double(tailExt)) / Double(p)
                cTimes.append(k); cVals.append(f.stop(s))
                k += 1.0 / 30
            }
            if cTimes.count >= 2 {
                let ca = CAKeyframeAnimation(keyPath: "emitterCells.star.color")
                ca.values = cVals
                ca.keyTimes = cTimes.map { NSNumber(value: $0 / max(cTimes[cTimes.count - 1], 1e-6)) }
                ca.calculationMode = .discrete
                ca.duration = cTimes[cTimes.count - 1]
                ca.beginTime = 1e-6
                em.add(ca, forKey: "col")
            }
        } else {
            let list = fx.starSolidColors.isEmpty ? [UIColor.white.cgColor] : fx.starSolidColors
            em.emitterCells = list.enumerated().map { cell("s\($0.offset)", rate: fx.starsPerCell / Double(list.count), color: $0.element) }
        }
        // absolute positions (an additive emitterPosition track is NOT added to the model on the render server: the
        // stars spawned from the layer origin): the shared travel samples offset from this tail
        let pts = share.travel.map { NSValue(cgPoint: CGPoint(x: tail0.x + d.dx * $0, y: tail0.y + d.dy * $0)) }
        em.add(Anim.keyframes("emitterPosition", pts, times: share.times, duration: share.duration, begin: 1e-6), forKey: "pos")
        em.birthRate = 0
        em.add(birth, forKey: "br")
        // the stop: a zero-rate override from tStop (a second track on the layer multiplier)
        if tStop < share.duration - 0.001 {
            let off = CABasicAnimation(keyPath: "birthRate")
            off.fromValue = 0
            off.toValue = 0
            off.duration = max(0.001, share.duration - tStop) + 0.4
            off.beginTime = tStop
            off.fillMode = .forwards
            em.add(off, forKey: "stop")
        }
        fxRoot.addSublayer(em)
        Anim.beat(on: em, key: "starsEnd", begin: 1e-6, delay: share.duration + fx.starLife + 0.05) { [weak em] _ in
            CATransaction.begin(); CATransaction.setDisableActions(true)
            em?.removeFromSuperlayer()
            CATransaction.commit()
        }
        noteFirst("stars")
    }
}
