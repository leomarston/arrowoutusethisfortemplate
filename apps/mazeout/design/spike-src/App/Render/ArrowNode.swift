import UIKit

/// Path + its local frame: every shape layer's frame hugs its own path, so off-screen arrows are culled at
/// high zoom (a board-sized frame would keep all 300 layers "visible" to the render server).
struct LocalPath {
    let frame: CGRect
    let path: CGPath
    init(_ path: CGPath, pad: CGFloat) {
        let box = path.boundingBoxOfPath.insetBy(dx: -pad, dy: -pad).integral
        frame = box
        var t = CGAffineTransform(translationX: -box.minX, y: -box.minY)
        self.path = path.copy(using: &t) ?? path
    }
    func local(_ p: CGPoint) -> CGPoint { CGPoint(x: p.x - frame.minX, y: p.y - frame.minY) }
}

/// One arrow at rest: a black round-capped/round-joined stroke (body) + a separate head triangle.
/// While it moves, `Mover` owns its motion layers; the node's own layers are hidden.
final class ArrowNode {
    let index: Int
    let geo: ArrowGeometry
    let body = CAShapeLayer()
    let head = CAShapeLayer()
    static let black = UIColor.black.cgColor

    init(index: Int, geo: ArrowGeometry, scale: CGFloat) {
        self.index = index
        self.geo = geo
        let lp = LocalPath(geo.restPath, pad: geo.width)
        body.frame = lp.frame
        body.path = lp.path
        body.fillColor = nil
        body.strokeColor = Self.black
        body.lineWidth = geo.width
        body.lineCap = .round
        body.lineJoin = .round
        body.contentsScale = scale
        let hp = ArrowGeometry.headPath(pitch: geo.pitch)
        let e = geo.pitch
        head.bounds = CGRect(x: -e, y: -e, width: 2 * e, height: 2 * e)
        head.path = hp
        head.fillColor = Self.black
        head.position = geo.headCentre
        head.setAffineTransform(CGAffineTransform(rotationAngle: geo.dirAngle))
        head.contentsScale = scale
    }

    func add(to parent: CALayer) {
        parent.addSublayer(body)
        parent.addSublayer(head)
    }

    func removeFromSuperlayer() {
        body.removeFromSuperlayer()
        head.removeFromSuperlayer()
    }
}

/// Everything that moves during one exit or bump. Built at tap time, removed when the motion ends.
final class Mover {
    let node: ArrowNode
    let root = CALayer()          // holds the motion layers, above the resting arrows
    private(set) var extraLayers: [CALayer] = []
    var onFinish: (() -> Void)?

    init(node: ArrowNode) { self.node = node }

    // MARK: exit

    /// Exit: body snakes along its path and out along the head ray. `style` paints it (black, dash hue
    /// steps, or gradient runs under a trimmed-stroke mask); stars are shed at the tail; dots appear as the
    /// tail uncovers each cell.
    func playExit(ray: CGFloat, track: Track, profile: TravelProfile, tun: Tunables, into parent: CALayer,
                  dotsParent: CALayer, fxParent: CALayer, scale: CGFloat) {
        let g = node.geo
        let exit = LocalPath(g.exitPath(ray: ray), pad: g.pitch)
        let startFns = track.travel.map { g.strokeStart($0, ray: ray) }
        let endFns = track.travel.map { g.strokeEnd($0, ray: ray) }
        let headLocal = track.travel.map { NSValue(cgPoint: exit.local(g.headPosition($0))) }
        let period = tun.trailPeriodCells * g.pitch
        let palette = Tunables.rainbow

        func trimmedStroke(color: CGColor?, width: CGFloat) -> CAShapeLayer {
            let l = CAShapeLayer()
            l.frame = root.bounds
            l.path = exit.path
            l.fillColor = nil
            l.strokeColor = color
            l.lineWidth = width
            l.lineCap = .round
            l.lineJoin = .round
            l.contentsScale = scale
            l.strokeStart = startFns.last!
            l.strokeEnd = endFns.last!
            l.add(keyframes("strokeStart", startFns, track), forKey: "s0")
            l.add(keyframes("strokeEnd", endFns, track), forKey: "s1")
            return l
        }
        func movingHead(color: CGColor?) -> CAShapeLayer {
            let h = CAShapeLayer()
            h.bounds = node.head.bounds
            h.path = node.head.path
            h.fillColor = color
            h.setAffineTransform(CGAffineTransform(rotationAngle: g.dirAngle))
            h.contentsScale = scale
            h.position = (headLocal.last!).cgPointValue
            h.add(keyframes("position", headLocal, track), forKey: "p")
            return h
        }

        // addSublayer must sit inside the no-actions transaction too: adding a layer runs the implicit
        // "onOrderIn" fade (0.25 s), which made the first frames of every exit/bump translucent
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        root.frame = exit.frame
        parent.addSublayer(root)
        node.body.isHidden = true
        node.head.isHidden = true

        let headLayer: CAShapeLayer
        switch tun.trail {
        case .none, .solid:
            let c = tun.trail == .solid ? tun.exitColor.cgColor : ArrowNode.black
            root.addSublayer(trimmedStroke(color: c, width: g.width))
            headLayer = movingHead(color: c)
            root.addSublayer(headLayer)

        case .gradient:
            // gradient runs (one axial CAGradientLayer per straight run, stops every palette step along the
            // arc length) masked by the trimmed stroke + moving head: smooth hue along the path, bands fixed
            let content = CALayer()
            content.frame = root.bounds
            let runs = g.runs(ray: ray)
            let headHalf = Metrics.headHalfWidthRatio * g.pitch + 1
            for (k, run) in runs.enumerated() {
                let (a, b, u0) = run
                let len = hypot(b.x - a.x, b.y - a.y)
                let wide = k >= runs.count - 2       // last body run + ray carry the head's width
                let half = wide ? headHalf : g.width / 2 + 1
                let pad = wide ? Metrics.headApexRatio * g.pitch + 1 : g.width / 2 + 1
                let ua = u0 - pad, ub = u0 + len + pad
                let horizontal = abs(b.y - a.y) < 0.5
                let pa = exit.local(a), pb = exit.local(b)
                let rect: CGRect = horizontal
                    ? CGRect(x: min(pa.x, pb.x) - pad, y: pa.y - half, width: len + 2 * pad, height: 2 * half)
                    : CGRect(x: pa.x - half, y: min(pa.y, pb.y) - pad, width: 2 * half, height: len + 2 * pad)
                let gl = CAGradientLayer()
                gl.frame = rect
                var colors: [CGColor] = [], locs: [NSNumber] = []
                func stop(_ u: CGFloat) {
                    colors.append(paletteColor(palette, u / period).cgColor)
                    locs.append(NSNumber(value: Double((u - ua) / (ub - ua))))
                }
                stop(ua)
                let step = period / CGFloat(palette.count)
                var u = (floor(ua / step) + 1) * step
                while u < ub { stop(u); u += step }
                stop(ub)
                gl.colors = colors
                gl.locations = locs
                let fwd = horizontal ? (b.x > a.x) : (b.y > a.y)
                gl.startPoint = horizontal ? CGPoint(x: fwd ? 0 : 1, y: 0.5) : CGPoint(x: 0.5, y: fwd ? 0 : 1)
                gl.endPoint = horizontal ? CGPoint(x: fwd ? 1 : 0, y: 0.5) : CGPoint(x: 0.5, y: fwd ? 1 : 0)
                content.addSublayer(gl)
            }
            let mask = CALayer()
            mask.frame = root.bounds
            mask.addSublayer(trimmedStroke(color: ArrowNode.black, width: g.width))
            headLayer = movingHead(color: ArrowNode.black)
            mask.addSublayer(headLayer)
            content.mask = mask
            root.addSublayer(content)

        case .dash:
            // N solid hue steps as dashed strokes (butt caps) + a round tail cap + head, colours sampled in time
            let n = max(2, tun.dashSteps)
            let band = period / CGFloat(n)
            let big = period * CGFloat(Int(ray / period) + 4)
            for k in 0..<n {
                let l = trimmedStroke(color: paletteColor(palette, (CGFloat(k) + 0.5) / CGFloat(n)).cgColor, width: g.width)
                l.lineCap = .butt
                l.lineDashPattern = [NSNumber(value: Double(band + 0.35)), NSNumber(value: Double(period - band - 0.35))]
                let phase0 = (period - CGFloat(k) * band).truncatingRemainder(dividingBy: period) + big
                l.lineDashPhase = tun.trailMoves ? phase0 - track.final : phase0
                if tun.trailMoves {
                    l.add(keyframes("lineDashPhase", track.travel.map { phase0 - $0 }, track), forKey: "ph")
                }
                root.addSublayer(l)
            }
            let samples = track.samples(every: 1.0 / 30, profile: profile)
            let cap = CAShapeLayer()
            cap.frame = root.bounds
            cap.path = exit.path
            cap.lineWidth = g.width
            cap.lineCap = .round
            cap.fillColor = nil
            cap.contentsScale = scale
            let total = g.bodyLength + ray
            cap.strokeStart = startFns.last!
            cap.strokeEnd = (track.final + 0.01) / total
            cap.add(keyframes("strokeStart", startFns, track), forKey: "s0")
            cap.add(keyframes("strokeEnd", track.travel.map { ($0 + 0.01) / total }, track), forKey: "s1")
            let tailColor: (CGFloat) -> CGColor = { s in paletteColor(palette, tun.trailMoves ? 0 : s / period).cgColor }
            cap.strokeColor = tailColor(track.final)
            cap.add(sampledKeyframes("strokeColor", samples.map { ($0.0, tailColor($0.1)) }, duration: track.duration), forKey: "c")
            root.addSublayer(cap)
            let headColor: (CGFloat) -> CGColor = { s in
                paletteColor(palette, tun.trailMoves ? g.bodyLength / period : (s + g.bodyLength) / period).cgColor
            }
            headLayer = movingHead(color: headColor(track.final))
            headLayer.add(sampledKeyframes("fillColor", samples.map { ($0.0, headColor($0.1)) }, duration: track.duration), forKey: "c")
            root.addSublayer(headLayer)
        }

        // dots: one dashed [0, pitch] round-capped stroke along the resting centreline, revealed with the tail
        // +1 pt past the head: a zero-length dash exactly at the path's end is dropped about half the time
        // (27 of 53 head dots were missing on L32 before this)
        let dotsPath = CGMutablePath()
        dotsPath.addLines(between: g.corners + [g.headPosition(1)])
        let rest = LocalPath(dotsPath, pad: g.pitch)
        let dots = CAShapeLayer()
        dots.frame = rest.frame
        dots.path = rest.path
        dots.fillColor = nil
        dots.strokeColor = tun.dotColor.cgColor
        dots.lineWidth = Metrics.dotDiameterRatio * g.pitch
        dots.lineCap = .round
        dots.lineDashPattern = [0.01, NSNumber(value: Double(g.pitch - 0.01))]
        dots.contentsScale = scale
        dots.strokeEnd = 1
        if g.bodyLength > 0 {
            let dTrack = track.clamped(to: g.bodyLength, profile: profile)
            dots.add(keyframes("strokeEnd", dTrack.travel.map { min(1, ($0 + 0.02) / (g.bodyLength + 1)) }, dTrack), forKey: "reveal")
        }
        dotsParent.addSublayer(dots)
        extraLayers.append(dots)

        // stars: one emitter following the tail, colour = the band under the tail at that moment
        if tun.stars && (tun.trail == .gradient || tun.trail == .dash) {
            let em = StarTrail.make(pitch: g.pitch, tun: tun, scale: scale)
            em.frame = fxParent.bounds
            // without this the render server "catches up" the emitter from time 0: a burst of stars at the start
            em.beginTime = fxParent.convertTime(CACurrentMediaTime(), from: nil)
            let corners = (1..<g.corners.count).map { i -> Double in
                var u: CGFloat = 0
                for j in 1...i { u += hypot(g.corners[j].x - g.corners[j - 1].x, g.corners[j].y - g.corners[j - 1].y) }
                return profile.time(toReach: u)
            }
            let samples = track.samples(every: 1.0 / 60, profile: profile, extra: corners)
            let tailStop = g.bodyLength + ray * 0.5
            em.emitterPosition = g.point(along: track.final)
            em.add(sampledKeyframes("emitterPosition", samples.map { ($0.0, NSValue(cgPoint: g.point(along: $0.1))) },
                                    duration: track.duration), forKey: "pos")
            let colorSamples = track.samples(every: 1.0 / 20, profile: profile)
            em.add(sampledKeyframes("emitterCells.star.color",
                                    colorSamples.map { ($0.0, paletteColor(palette, tun.trailMoves ? 0 : $0.1 / period).cgColor) },
                                    duration: track.duration), forKey: "col")
            em.birthRate = 0
            let off = min(track.duration, profile.time(toReach: tailStop))
            let br = CAKeyframeAnimation(keyPath: "birthRate")
            br.values = [1, 1, 0]
            br.keyTimes = [0, NSNumber(value: off / max(track.duration, 1e-3)), 1]
            br.duration = track.duration
            em.add(br.hi(), forKey: "br")
            fxParent.addSublayer(em)
            extraLayers.append(em)
        }

        let end = CABasicAnimation(keyPath: "opacity")      // carrier for the completion callback
        end.fromValue = 1
        end.toValue = 1
        end.duration = track.duration
        end.delegate = AnimationEnd { [weak self] _ in self?.finishExit(lifetime: Double(tun.starLifetime)) }
        root.add(end, forKey: "end")
        CATransaction.commit()
    }

    private func finishExit(lifetime: Double) {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        root.removeFromSuperlayer()
        node.removeFromSuperlayer()
        CATransaction.commit()
        // dots stay (the board keeps them); the emitter lives until its last star fades
        let fx = extraLayers.filter { $0 is CAEmitterLayer }
        DispatchQueue.main.asyncAfter(deadline: .now() + lifetime + 0.1) {
            CATransaction.begin(); CATransaction.setDisableActions(true)
            fx.forEach { $0.removeFromSuperlayer() }
            CATransaction.commit()
        }
        onFinish?()
    }

    // MARK: bump

    /// Forward to the blocker's ink, back to rest; red from the contact frame, then (optionally) fading back.
    func playBump(contact: CGFloat, profile: TravelProfile, tun: Tunables, into parent: CALayer, scale: CGFloat,
                  onContact: @escaping () -> Void) {
        let g = node.geo
        let ray = contact + g.pitch
        let exit = LocalPath(g.exitPath(ray: ray), pad: g.pitch)
        let track = Track.bump(profile, contact: contact, back: tun.bumpBackDuration)
        let tc = profile.time(toReach: contact)
        let body = CAShapeLayer()
        body.frame = root.bounds
        body.path = exit.path
        body.fillColor = nil
        body.lineWidth = g.width
        body.lineCap = .round
        body.lineJoin = .round
        body.contentsScale = scale
        body.strokeStart = 0
        body.strokeEnd = g.strokeEnd(0, ray: ray)
        let head = CAShapeLayer()
        head.bounds = node.head.bounds
        head.path = node.head.path
        head.setAffineTransform(CGAffineTransform(rotationAngle: g.dirAngle))
        head.contentsScale = scale
        head.position = exit.local(g.headCentre)

        let red = tun.bumpRed.cgColor, black = ArrowNode.black
        let total = track.duration + (tun.bumpTintPersists ? 0 : tun.bumpTintFade)
        let kt: [NSNumber] = [0, NSNumber(value: max(0, tc - 0.001) / total), NSNumber(value: tc / total),
                              NSNumber(value: track.duration / total), 1]
        let colours: [CGColor] = [black, black, red, red, tun.bumpTintPersists ? red : black]
        func colourAnim(_ key: String) -> CAKeyframeAnimation {
            let a = CAKeyframeAnimation(keyPath: key)
            a.values = colours
            a.keyTimes = kt
            a.duration = total
            return a.hi()
        }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        root.frame = exit.frame
        parent.addSublayer(root)
        node.body.isHidden = true
        node.head.isHidden = true
        body.strokeColor = colours.last
        head.fillColor = colours.last
        body.add(keyframes("strokeStart", track.travel.map { g.strokeStart($0, ray: ray) }, track), forKey: "s0")
        body.add(keyframes("strokeEnd", track.travel.map { g.strokeEnd($0, ray: ray) }, track), forKey: "s1")
        head.add(keyframes("position", track.travel.map { NSValue(cgPoint: exit.local(g.headPosition($0))) }, track), forKey: "p")
        body.add(colourAnim("strokeColor"), forKey: "c")
        head.add(colourAnim("fillColor"), forKey: "c")
        root.addSublayer(body)
        root.addSublayer(head)
        let contactMark = CABasicAnimation(keyPath: "opacity")
        contactMark.fromValue = 1
        contactMark.toValue = 1
        contactMark.duration = tc
        contactMark.delegate = AnimationEnd { _ in onContact() }
        root.add(contactMark, forKey: "contact")
        let end = CABasicAnimation(keyPath: "opacity")
        end.fromValue = 1
        end.toValue = 1
        end.duration = total
        end.delegate = AnimationEnd { [weak self] _ in
            guard let self else { return }
            CATransaction.begin(); CATransaction.setDisableActions(true)
            if tun.bumpTintPersists {
                self.node.body.strokeColor = red
                self.node.head.fillColor = red
            }
            self.node.body.isHidden = false
            self.node.head.isHidden = false
            self.root.removeFromSuperlayer()
            CATransaction.commit()
            self.onFinish?()
        }
        root.add(end, forKey: "end")
        CATransaction.commit()
    }
}

/// Star confetti shed at the tail (store shots 1 + 5). Our own star shape, drawn in code.
enum StarTrail {
    static let image: CGImage = {
        let px = 96
        let fmt = UIGraphicsImageRendererFormat()
        fmt.scale = 1
        let img = UIGraphicsImageRenderer(size: CGSize(width: px, height: px), format: fmt).image { ctx in
            let c = ctx.cgContext
            let centre = CGPoint(x: Double(px) / 2, y: Double(px) / 2 + 3)
            let outer = Double(px) * 0.46, inner = outer * 0.5
            let p = CGMutablePath()
            for i in 0..<10 {
                let r = i % 2 == 0 ? outer : inner
                let a = -Double.pi / 2 + Double(i) * Double.pi / 5
                let q = CGPoint(x: centre.x + r * cos(a), y: centre.y + r * sin(a))
                if i == 0 { p.move(to: q) } else { p.addLine(to: q) }
            }
            p.closeSubpath()
            c.addPath(p)
            c.setLineJoin(.round)
            c.setLineWidth(8)
            c.setStrokeColor(UIColor.white.cgColor)
            c.setFillColor(UIColor.white.cgColor)
            c.drawPath(using: .fillStroke)
        }
        return img.cgImage!
    }()

    static func make(pitch: CGFloat, tun: Tunables, scale: CGFloat) -> CAEmitterLayer {
        let em = CAEmitterLayer()
        em.emitterShape = .point
        em.renderMode = .unordered
        em.contentsScale = scale
        let cell = CAEmitterCell()
        cell.name = "star"
        cell.contents = image
        cell.birthRate = tun.starBirthRate
        cell.lifetime = tun.starLifetime
        cell.lifetimeRange = tun.starLifetime * 0.4
        cell.velocity = pitch * 0.9
        cell.velocityRange = pitch * 0.7
        cell.emissionRange = .pi * 2
        cell.spin = 0
        cell.spinRange = 2.5
        // image is 96 px; a particle's size = 96 px * scale in points (emitter contentsScale does not apply)
        let startSize = 0.55 * pitch
        cell.scale = startSize / 96
        cell.scaleRange = cell.scale * 0.35
        cell.scaleSpeed = -cell.scale * 0.8
        cell.alphaSpeed = -1 / tun.starLifetime
        cell.color = Tunables.rainbow[0].cgColor
        em.emitterCells = [cell]
        return em
    }
}
