import UIKit
import PathCore

// B1 (SPEC-architecture §5.5 "Bump mover", §8.3; the numbers are research/motion.md §4, pass 2, two v552 clips, as
// board.json data, PENDING-motion-audio):
//  - the arrow slides ALONG ITS OWN PATH at constant speed until the apex touches the blocker's stroke edge,
//    T_out = outBase + outPerCell · contact cells (0.075 + 0.025·gap), no hold, then eases back (easeOutQuad 0.14 s);
//  - it turns red (#EE0A13) from contact + 0.017 to + 0.12 (S-shaped) and stays red (the rest node is marked);
//  - the blocking arrow flashes red (contact + 0.02 → + 0.12) and fades back to black by + 0.33;
//  - a red ✖ badge at the contact point: in large and transparent at + 0.017, 1.0 and opaque by + 0.12, holds to + 0.33,
//    shrinks and fades out by + 0.43;
//  - the red screen-edge vignette (ScreenFX) starts on the contact frame;
//  - `.bumpContact` from the contact beat (the session takes the heart on that frame), `.bumpFinished` at rest.
// No shake, no sound (VERIFIED).

extension BoardEngine {
    @discardableResult
    func startBump(_ node: ArrowNode, plan: BumpPlan, begin t0: CFTimeInterval) -> Mover? {
        guard let st = stage else { return nil }
        let geo = st.geo
        let p = geo.pitch
        let spec = node.spec
        let own = spec.cells.count
        let beyond: [Cell] = plan.path.cells.count > own ? Array(plan.path.cells[own...]) : []
        let contactCells = max(0.05, plan.contactCells)
        let contact = CGFloat(contactCells) * p
        let path = geo.movingPath(spec, beyond: beyond, extend: contact + p)
        let restLen = node.rest.length
        let total = path.length
        let c = config
        let tOut = max(0.02, c.bumpOutBase + c.bumpOutPerCell * contactCells)
        let hold = max(0, c.bumpHold)
        let back = max(0.02, c.bumpBack)
        let tTotal = tOut + hold + back
        // samples: constant speed out, hold, easeOutQuad back (1 − (1 − u)² of the way home)
        var times: [Double] = []
        var travel: [CGFloat] = []
        let dt = max(c.keyframeStep, 1.0 / 240)
        var t = 0.0
        while t < tTotal {
            times.append(t)
            travel.append(Self.bumpTravel(t, contact: contact, tOut: tOut, hold: hold, back: back))
            t += dt
        }
        for extra in [tOut, tOut + hold, tTotal] where !times.contains(where: { abs($0 - extra) < 1e-6 }) {
            times.append(extra)
            travel.append(Self.bumpTravel(extra, contact: contact, tOut: tOut, hold: hold, back: back))
        }
        let order = times.indices.sorted { times[$0] < times[$1] }
        times = order.map { times[$0] }
        travel = order.map { travel[$0] }

        let local = LocalPath(path.cgPath, pad: max(p, geo.headExtent))
        let m = Mover(id: spec.id, kind: .bump, begin: t0)
        m.duration = tTotal
        m.times = times
        m.travel = travel
        m.pitch = p
        m.dirVec = dirVector(spec.dir)
        m.contactAt = tOut
        m.root.frame = local.frame

        let from = node.color
        let red = c.markedColor
        let body = CAShapeLayer()
        body.frame = m.root.bounds
        body.path = local.path
        body.fillColor = nil
        body.lineWidth = geo.lineWidth
        body.lineCap = .round
        body.lineJoin = .round
        body.contentsScale = screenScale
        body.strokeColor = red
        body.strokeStart = 0
        body.strokeEnd = restLen / total
        let head = CAShapeLayer()
        head.bounds = node.head.bounds
        head.path = geo.headPath(spec.dir)
        head.contentsScale = screenScale
        head.fillColor = red
        head.position = local.local(node.headCentre)
        head.setAffineTransform(CGAffineTransform(rotationAngle: CGFloat(spec.dir.angle)))
        body.add(Anim.keyframes("strokeStart", travel.map { NSNumber(value: Double($0 / total)) }, times: times,
                                duration: tTotal, begin: t0), forKey: "s0")
        body.add(Anim.keyframes("strokeEnd", travel.map { NSNumber(value: Double((restLen + $0) / total)) }, times: times,
                                duration: tTotal, begin: t0), forKey: "s1")
        head.add(Anim.keyframes("position", travel.map { NSValue(cgPoint: local.local(path.point(at: restLen + $0))) },
                                times: times, duration: tTotal, begin: t0), forKey: "p")
        // red on the return (S-shaped), then red for the rest of the level
        let r0 = min(tTotal, tOut + c.bumpRedFrom), r1 = min(tTotal, max(r0 + 0.001, tOut + c.bumpRedTo))
        let colourTimes = [0, r0, r1, tTotal]
        let fns = [CAMediaTimingFunction(name: .linear), Anim.easeInOut, CAMediaTimingFunction(name: .linear)]
        body.add(Anim.keyframes("strokeColor", [from, from, red, red], times: colourTimes, duration: tTotal, begin: t0,
                                functions: fns), forKey: "c")
        head.add(Anim.keyframes("fillColor", [from, from, red, red], times: colourTimes, duration: tTotal, begin: t0,
                                functions: fns), forKey: "c")
        m.root.addSublayer(body)
        m.root.addSublayer(head)
        m.headLayer = head
        m.headStartLocal = local.local(node.headCentre)
        roots.mover.addSublayer(m.root)
        node.setVisible(false)

        // the blocker flashes red and fades back (VERIFIED motion §4 "blocker")
        if case .arrow(let b) = plan.blocker, let bn = nodes[b], bn.attached, movers[b] == nil {
            flashBlocker(bn, begin: t0 + tOut)
        }
        // the ✖ badge at the contact point: the blocker's near edge on the ray
        let cp = geo.centre(plan.contactPoint)
        let rayDir: CGVector = beyond.isEmpty ? dirVector(spec.dir)
            : ArrowPath.unit(geo.centre(beyond.count >= 2 ? beyond[beyond.count - 2] : headCell(spec)), geo.centre(beyond[beyond.count - 1]))
        let badgeAt = CGPoint(x: cp.x - rayDir.dx * geo.lineWidth / 2, y: cp.y - rayDir.dy * geo.lineWidth / 2)
        let badge = makeBadge(at: badgeAt, pitch: p, begin: t0 + tOut)
        roots.fx.addSublayer(badge)
        // the badge outlives the return (+0.43 vs +0.14): it removes itself, so `.bumpFinished` comes at rest
        Anim.beat(on: badge, key: "badgeEnd", begin: t0, delay: tOut + c.badgeOutTo) { [weak badge] _ in
            CATransaction.begin(); CATransaction.setDisableActions(true)
            badge?.removeFromSuperlayer()
            CATransaction.commit()
        }
        // the vignette starts on the contact frame (screen space)
        container.screenFX.playVignette(delay: max(0, tOut - motionLead), config: c)   // FEEL F3: the contact frame

        let id = spec.id
        Anim.beat(on: m.root, key: "contact", begin: t0, delay: tOut) { [weak self, weak m] finished in
            guard finished, let self, let m, self.movers[id] === m else { return }
            self.noteFirst("bumpContact")
            self.delegate?.boardBeat(.bumpContact(id))
        }
        Anim.beat(on: m.root, key: "end", begin: t0, delay: tTotal) { [weak self, weak m] finished in
            guard finished, let self, let m, self.movers[id] === m else { return }
            self.finishMover(id)
        }
        return m
    }

    static func bumpTravel(_ t: Double, contact: CGFloat, tOut: Double, hold: Double, back: Double) -> CGFloat {
        if t <= tOut { return contact * CGFloat(t / tOut) }
        if t <= tOut + hold { return contact }
        let u = min(1, (t - tOut - hold) / back)
        let remain = (1 - u) * (1 - u)
        return contact * CGFloat(remain)
    }

    private func flashBlocker(_ n: ArrowNode, begin: CFTimeInterval) {
        let c = config
        let base = n.color
        let red = c.markedColor
        let times = [0, c.blockerRedFrom, c.blockerRedTo, c.blockerBlackAt]
        let dur = c.blockerBlackAt
        let fns = [Anim.easeInOut, CAMediaTimingFunction(name: .linear), CAMediaTimingFunction(name: .linear)]
        n.body.add(Anim.keyframes("strokeColor", [base, base, red, base], times: times, duration: dur, begin: begin,
                                  functions: fns), forKey: "flash")
        n.head.add(Anim.keyframes("fillColor", [base, base, red, base], times: times, duration: dur, begin: begin,
                                  functions: fns), forKey: "flash")
    }

    /// The red ✖ with a dark outline (our vector drawing; ≈ 1 pitch across, VERIFIED motion §4 look and timing).
    private func makeBadge(at p: CGPoint, pitch: CGFloat, begin: CFTimeInterval) -> CALayer {
        let c = config
        let size = pitch * CGFloat(c.badgePitch)
        let root = CALayer()
        root.bounds = CGRect(x: -size, y: -size, width: 2 * size, height: 2 * size)
        root.position = p
        root.opacity = 0
        let bars = CGMutablePath()
        let len = size * 0.82, thick = size * 0.3
        for angle in [CGFloat.pi / 4, -CGFloat.pi / 4] {
            var tr = CGAffineTransform(rotationAngle: angle)
            let rect = CGRect(x: -len / 2, y: -thick / 2, width: len, height: thick)
            bars.addPath(CGPath(roundedRect: rect, cornerWidth: thick * 0.45, cornerHeight: thick * 0.45, transform: &tr))
        }
        let outline = CAShapeLayer()
        outline.path = bars
        outline.fillColor = nil
        outline.strokeColor = c.badgeOutline
        outline.lineWidth = size * 0.16
        outline.lineJoin = .round
        outline.contentsScale = screenScale
        let fill = CAShapeLayer()
        fill.path = bars
        fill.fillColor = c.badgeFill
        fill.contentsScale = screenScale
        root.addSublayer(outline)
        root.addSublayer(fill)
        let dur = c.badgeOutTo
        let times = [0, c.badgeInFrom, c.badgeInTo, c.badgeHoldTo, c.badgeOutTo]
        let op = Anim.keyframes("opacity", [0, 0, 1, 1, 0], times: times, duration: dur, begin: begin)
        let sc = Anim.keyframes("transform.scale", [c.badgeScaleIn, c.badgeScaleIn, 1, 1, c.badgeScaleOut].map { NSNumber(value: $0) },
                                times: times, duration: dur, begin: begin)
        op.fillMode = .both
        root.add(op, forKey: "o")
        root.add(sc, forKey: "s")
        return root
    }
}
