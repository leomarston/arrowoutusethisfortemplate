import UIKit
import PathCore

// B2 (SPEC-architecture §5.5 step 6, P2; SPEC-motion-audio §3.2.3, §10 "trail stars"). One CAEmitterLayer per exit in
// fxRoot (board content space: the stars zoom with the board): spawned at the arrow's TAIL as it moves (they line the path
// the tail vacated, corners included), 2.4 stars per cell of tail travel (the layer's birthRate is keyframed with the tail
// speed v(τ) c/s, the cell's rate is 2.4), jitter in a disc of 0.25 p, size 0.30 p ± 0.08 p, life 0.40 s (alpha 1 → 0 and
// scale 1 → 0.4 over life), spin ±90°/s, no velocity. Emission stops when the tail leaves the content rect (grid + 1-cell
// margin). Colours: solid → 50 % #1E88F5 + 50 % #7FD8FF (two cells); violet / rainbow → the palette stop at the spawn σ of
// the same field as the body (keyframed cell colour). `seed` from the fx stream (deterministic captures).
// Timing: emitterLayer.beginTime = the tap's parent-local time (P2: otherwise the render server "catches up" from 0); its
// keyframes run on the emitter's own clock from local 0, so the stage's freeze / slow motion hold them with the mover.

@MainActor enum StarTrail {
    /// The white 5-point star (MANIFEST `boardTrailStar`, 36 px); a code-drawn star when the sprite is missing.
    static func image(_ cache: SpriteCache) -> CGImage? {
        if let s = cachedImage { return s }
        let img = cache.image("boardTrailStar") ?? drawnStar()
        cachedImage = img
        return img
    }
    private static var cachedImage: CGImage?

    private static func drawnStar() -> CGImage? {
        let px = 36
        let r = UIGraphicsImageRenderer(size: CGSize(width: px, height: px), format: {
            let f = UIGraphicsImageRendererFormat(); f.scale = 1; return f
        }())
        return r.image { ctx in
            let c = ctx.cgContext
            let path = CGMutablePath()
            for i in 0..<10 {
                let a = -CGFloat.pi / 2 + CGFloat(i) * .pi / 5
                let rad: CGFloat = i % 2 == 0 ? 16 : 7
                let p = CGPoint(x: 18 + rad * cos(a), y: 18 + rad * sin(a))
                if i == 0 { path.move(to: p) } else { path.addLine(to: p) }
            }
            path.closeSubpath()
            c.addPath(path)
            c.setLineJoin(.round)
            c.setLineWidth(3)
            c.setStrokeColor(UIColor.white.cgColor)
            c.setFillColor(UIColor.white.cgColor)
            c.drawPath(using: .fillStroke)
        }.cgImage
    }

    enum Colours {
        case solid([CGColor])
        case field(ColourField)
    }

    /// Builds the emitter for one exit (added by the caller to fxRoot inside the tap's transaction) or nil when stars are
    /// off or the tail never moves inside the content rect.
    /// `track`: the tail points and the stop index prepared ahead (ExitPrep, FEEL item 4); computed here when nil.
    static func make(ctx: ExitPaintContext, colours: Colours, fx: EffectsConfig, kin: ExitKinematics, contentRect: CGRect,
                     tailExtend: CGFloat, image: CGImage?, seed: UInt32, parentNow: CFTimeInterval,
                     track: ([NSValue], Int)? = nil) -> CAEmitterLayer? {
        guard fx.starsOn, let image, ctx.times.count >= 2 else { return nil }
        let p = ctx.pitch
        // the tail point at every sample, and the moment it leaves the content rect (emission stops)
        var pts: [NSValue] = []
        var stopIndex = ctx.times.count - 1
        if let track, track.0.count == ctx.times.count {
            pts = track.0
            stopIndex = min(track.1, ctx.times.count - 1)
        } else {
            pts.reserveCapacity(ctx.times.count)
            var stopped = false
            for (i, s) in ctx.travel.enumerated() {
                let q = ctx.path.point(at: s + tailExtend)
                pts.append(NSValue(cgPoint: q))
                if !stopped && !contentRect.contains(q) { stopIndex = max(0, i); stopped = true }
            }
        }
        let tStop = ctx.times[stopIndex]
        guard tStop > 0.001 else { return nil }
        let dur = ctx.times[ctx.times.count - 1]
        let em = CAEmitterLayer()
        em.frame = CGRect(origin: .zero, size: contentRect.size)
        em.emitterShape = .circle
        em.emitterMode = .volume
        let jitter = CGFloat(fx.starJitter) * p
        em.emitterSize = CGSize(width: jitter, height: jitter)
        em.renderMode = .unordered
        em.seed = seed
        em.beginTime = parentNow
        em.emitterPosition = pts[min(stopIndex, pts.count - 1)].cgPointValue
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
            c.spin = 0
            c.spinRange = CGFloat(fx.starSpinDeg * .pi / 180)
            c.color = color
            return c
        }
        switch colours {
        case .solid(let cs):
            let list = cs.isEmpty ? [UIColor.white.cgColor] : cs
            em.emitterCells = list.enumerated().map { cell("s\($0.offset)", rate: fx.starsPerCell / Double(list.count), color: $0.element) }
        case .field(let f):
            em.emitterCells = [cell("star", rate: fx.starsPerCell, color: f.stop(0))]
        }
        // local keyframes (the emitter's own clock starts at the tap): a tiny positive begin keeps CA from re-stamping 0
        let b: CFTimeInterval = 1e-6
        let posTimes = Array(ctx.times.prefix(stopIndex + 1))
        let posVals = Array(pts.prefix(stopIndex + 1))
        if posTimes.count >= 2 {
            em.add(Anim.keyframes("emitterPosition", posVals, times: posTimes, duration: tStop, begin: b), forKey: "pos")
        }
        // birth rate = v_tail (cells/s): the layer multiplier; 0 from the stop on (model value 0)
        var rTimes: [Double] = []
        var rVals: [NSNumber] = []
        var t = 0.0
        while t < tStop { rTimes.append(t); rVals.append(NSNumber(value: kin.v(t))); t += 1.0 / 30 }
        rTimes.append(tStop); rVals.append(NSNumber(value: kin.v(tStop)))
        rTimes.append(min(dur, tStop + 0.001) + 0.0001); rVals.append(0)
        em.birthRate = 0
        let br = Anim.keyframes("birthRate", rVals, times: rTimes, duration: rTimes[rTimes.count - 1], begin: b)
        br.fillMode = .forwards
        em.add(br, forKey: "br")
        if case .field(let f) = colours {
            var cTimes: [Double] = []
            var cVals: [CGColor] = []
            var k = 0.0
            var cursor = 1                                     // FEEL: one forward pass over the samples (was a search per step)
            while k <= tStop {
                // the tail's σ (cells from the path start) at time k
                let s = Double(interp(ctx.times, ctx.travel, k, from: &cursor) + tailExtend) / Double(p)
                cTimes.append(k); cVals.append(f.stop(s))
                k += 1.0 / 60
            }
            if cTimes.count >= 2 {
                let ca = Anim.keyframes("emitterCells.star.color", cVals, times: cTimes, duration: cTimes[cTimes.count - 1], begin: b)
                ca.calculationMode = .discrete
                ca.keyTimes = cTimes.map { NSNumber(value: $0 / max(cTimes[cTimes.count - 1], 1e-6)) }
                em.add(ca, forKey: "col")
            }
        }
        return em
    }

    /// Linear interpolation of the travel samples.
    static func interp(_ times: [Double], _ travel: [CGFloat], _ t: Double) -> CGFloat {
        var c = 1
        return interp(times, travel, t, from: &c)
    }

    /// … continuing the search from `cursor` (non-decreasing `t` across calls).
    static func interp(_ times: [Double], _ travel: [CGFloat], _ t: Double, from cursor: inout Int) -> CGFloat {
        guard let last = times.last, t < last else { return travel.last ?? 0 }
        var i = max(1, cursor)
        while i < times.count && times[i] < t { i += 1 }
        cursor = i
        let t0 = times[i - 1], t1 = times[i]
        let f = CGFloat(t1 > t0 ? (t - t0) / (t1 - t0) : 0)
        return travel[i - 1] + (travel[i] - travel[i - 1]) * f
    }
}

extension BoardEngine {
    /// Adds the trail stars of one exit (inside the tap's no-actions transaction); the emitter removes itself when its last
    /// star has faded.
    func addStars(_ ctx: ExitPaintContext, painter: ExitPainter, moverRoot: CALayer, fxRoot: CALayer,
                  track: ([NSValue], Int)? = nil) {
        guard fx.starsOn else { return }
        let colours: StarTrail.Colours
        if let fp = painter as? FieldPainter { colours = .field(fp.field(ctx)) } else { colours = .solid(fx.starSolidColors) }
        let parentNow = fxRoot.convertTime(CACurrentMediaTime(), from: nil) - motionLead   // FEEL F3: the tap's motion lead
        let rect = CGRect(origin: .zero, size: contentBounds.size)
        guard let em = StarTrail.make(ctx: ctx, colours: colours, fx: fx, kin: kinematics, contentRect: rect,
                                      tailExtend: CGFloat(config.tailExtend) * ctx.pitch,
                                      image: StarTrail.image(sprites), seed: fxRng.u32(), parentNow: parentNow,
                                      track: track) else { return }
        fxRoot.addSublayer(em)
        Anim.beat(on: em, key: "starsEnd", begin: 1e-6, delay: ctx.duration + fx.starLife + 0.05) { [weak em] _ in
            CATransaction.begin(); CATransaction.setDisableActions(true)
            em?.removeFromSuperlayer()
            CATransaction.commit()
        }
        noteFirst("stars")
    }
}
