import UIKit
import PathCore

// B1 (SPEC-architecture §5.5 "Painters"): the exit look is a painter chosen per exit by the combo ladder (board.json
// `combo.ladder`, §4.7) or forced by `-pc.trail`. B1 ships `solid` (#10A2EF, VERIFIED motion §3.2); B2 registers `violet`
// and `rainbow` (PaintersCombo) in `BoardEngine.painters`. A ladder entry with no registered painter falls back to solid
// (logged once), so the ladder can already name them.

/// Everything a painter needs for one exit. Coordinates are root-local (`local`); every animation begins at `begin`.
struct ExitPaintContext {
    let root: CALayer
    let local: LocalPath
    let path: ArrowPath                     // content coordinates
    let restLength: CGFloat                 // the body's arc length (tail extension included)
    let lineWidth: CGFloat
    let headPath: CGPath
    let headBounds: CGRect
    let strokeStart: CAKeyframeAnimation    // body trim (fractions of `path.length`)
    let strokeEnd: CAKeyframeAnimation
    let headPosition: CAKeyframeAnimation   // root-local points
    let headRotation: CAKeyframeAnimation?  // only when the path turns beyond the head (tubes, corners: B2)
    let finalStrokeStart: CGFloat
    let finalStrokeEnd: CGFloat
    let finalHeadPosition: CGPoint
    let finalHeadAngle: CGFloat
    let fromColor: CGColor                  // the resting colour (black, or red when marked)
    let config: BoardConfig
    let begin: CFTimeInterval
    let duration: Double
    let times: [Double]                     // the sample times (s) …
    let travel: [CGFloat]                   // … and the head travel (pt) at each
    let pitch: CGFloat
    let scale: CGFloat
    let combo: Int
    /// The colour field's phase (0…1) for this exit, from the fx stream (B2 painters and stars).
    var phase: Double = 0

    /// A body stroke on the moving path, trimmed by the shared keyframes (model = the final trim).
    func trimmedStroke(color: CGColor?) -> CAShapeLayer {
        let l = CAShapeLayer()
        l.frame = root.bounds
        l.path = local.path
        l.fillColor = nil
        l.strokeColor = color
        l.lineWidth = lineWidth
        l.lineCap = .round
        l.lineJoin = .round
        l.contentsScale = scale
        l.strokeStart = finalStrokeStart
        l.strokeEnd = finalStrokeEnd
        l.add(strokeStart, forKey: "s0")
        l.add(strokeEnd, forKey: "s1")
        return l
    }

    /// The moving head (model = the final position / angle).
    func movingHead(color: CGColor?) -> CAShapeLayer {
        let h = CAShapeLayer()
        h.bounds = headBounds
        h.path = headPath
        h.fillColor = color
        h.contentsScale = scale
        h.position = finalHeadPosition
        h.setAffineTransform(CGAffineTransform(rotationAngle: finalHeadAngle))
        h.add(headPosition, forKey: "p")
        if let r = headRotation { h.add(r, forKey: "r") }
        return h
    }
}

@MainActor protocol ExitPainter: AnyObject {
    var name: String { get }
    /// Adds the moving layers to `ctx.root` and returns the head layer (the kinematics probe samples it).
    func paint(_ ctx: ExitPaintContext) -> CALayer
}

/// Solid light blue (#10A2EF, VERIFIED motion §3.2). The colour ramp black → exit colour runs on the body and head
/// themselves (a linear per-channel cross-fade over `exit.colourRamp` = 0.09 s from release, VERIFIED motion §3.2), so the
/// first presented frame is full ink (P1) and nothing extra is composited.
@MainActor final class SolidPainter: ExitPainter {
    let name = "solid"

    func paint(_ ctx: ExitPaintContext) -> CALayer {
        let c = ctx.config.exitColor
        let body = ctx.trimmedStroke(color: c)
        let head = ctx.movingHead(color: c)
        let ramp = ctx.config.colourRamp
        if ramp > 0 {
            body.add(Anim.basic("strokeColor", from: ctx.fromColor, to: c, duration: ramp, begin: ctx.begin), forKey: "ramp")
            head.add(Anim.basic("fillColor", from: ctx.fromColor, to: c, duration: ramp, begin: ctx.begin), forKey: "ramp")
        }
        ctx.root.addSublayer(body)
        ctx.root.addSublayer(head)
        return head
    }
}

extension BoardEngine {
    /// The painter for this exit: `-pc.trail` wins (solid | rainbow | ladder), else the combo ladder (1-based index, the
    /// last entry repeats), else solid.
    func painterFor(combo: Int) -> ExitPainter {
        var name: String
        switch trailOverride {
        case .solid?: name = "solid"
        case .rainbow?: name = "rainbow"
        case .ladder?, nil:
            let ladder = config.ladder
            if ladder.isEmpty { name = "solid" } else { name = ladder[min(max(combo, 1), ladder.count) - 1] }
        }
        if let f = forcedPainter { name = f }
        if let p = painters[name] { return p }
        if !missingPainters.contains(name) {
            missingPainters.insert(name)
            Log.mark("board", "painter \(name) not installed (B2): solid instead")
        }
        return painters["solid"] ?? SolidPainter()
    }
}
