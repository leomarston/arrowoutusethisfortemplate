import UIKit
import PathCore

// B2 (SPEC-architecture §5.5 "Painters"; SPEC-motion-audio §3.2.2, MA4/MA5; CONSISTENCY E-10/E-12). The combo ladder's
// colour-field painters: `violet` (6 stops #01ACFD · #3972FF · #7B3CFC · #B908FE · #7B3CFC · #3972FF, period 3.75 cells) and
// `rainbow` (the 12-hue palette, period 4.2 cells). The colour is a FIELD fixed on the exit path's arc coordinate σ (the
// body slides through it; a screen point on the path keeps its hue), with a random phase per exit (fx stream).
//
// Technique: the spike's painter A (design/spike-src/App/Render/ArrowNode.swift `.gradient`, VERIFIED spike 3e): one
// axial CAGradientLayer per straight run of the moving path with a stop at every palette step along the arc length,
// masked by the trimmed stroke + the moving head (so the head takes the colour at its σ) — B2: one masked box per run
// (small offscreen passes); straight exits use StraightExit's single gradient under a moving mask. The colour ramp from the
// resting colour (black / red / hint green) runs as a copy of the trimmed stroke + head ON TOP, fading 1 → 0 over
// `exit.colourRamp` (0.09 s) — the one mechanism of arch §5.5 step 4.
// Layers per bent mover: root + per run (box, gradient, mask, shift, stroke, + head on the runs the head crosses) + ramp
// (stroke + head): 14 for 2 runs, 26 for 4 (above §10.2's DECISION of 16 per mover, reported: it trades layers for
// offscreen area).

@MainActor final class FieldPainter: ExitPainter {
    let name: String
    let palette: [CGColor]
    let period: Double

    init(name: String, palette: [CGColor], period: Double) {
        self.name = name
        self.palette = palette
        self.period = period
    }

    func field(_ ctx: ExitPaintContext) -> ColourField { ColourField(palette: palette, period: period, phase: ctx.phase) }

    /// Bent exits (the straight ones take StraightExit's one-gradient route). Each straight run gets its OWN masked box
    /// (the run's thin rect), so the offscreen mask passes cover the path's strips instead of the path's whole bounding
    /// box (a snake's bbox can be most of the screen: one full-screen offscreen pass per mover, R2).
    func paint(_ ctx: ExitPaintContext) -> CALayer {
        let field = field(ctx)
        var head: CALayer?
        let black = UIColor.black.cgColor
        for (gl, wide) in Self.runs(ctx, field: field) {
            let rect = gl.frame
            let box = CALayer()
            box.frame = rect
            gl.frame = box.bounds
            box.addSublayer(gl)
            let mask = CALayer()
            mask.frame = box.bounds
            let shift = CALayer()                                  // the root's coordinates inside the box
            shift.frame = CGRect(x: -rect.minX, y: -rect.minY, width: ctx.root.bounds.width, height: ctx.root.bounds.height)
            shift.addSublayer(ctx.trimmedStroke(color: black))
            if wide {
                let h = ctx.movingHead(color: black)
                shift.addSublayer(h)
                if head == nil { head = h }
            }
            mask.addSublayer(shift)
            box.mask = mask
            ctx.root.addSublayer(box)
        }
        Self.addRamp(ctx)
        return head ?? ctx.root
    }

    /// The resting colour on top, fading out over the colour ramp (model opacity 0: nothing is drawn after it).
    static func addRamp(_ ctx: ExitPaintContext) {
        let ramp = ctx.config.colourRamp
        guard ramp > 0 else { return }
        let body = ctx.trimmedStroke(color: ctx.fromColor)
        let head = ctx.movingHead(color: ctx.fromColor)
        for l in [body, head] {
            l.opacity = 0
            l.add(Anim.basic("opacity", from: 1, to: 0, duration: ramp, begin: ctx.begin), forKey: "ramp")
            ctx.root.addSublayer(l)
        }
    }

    /// One axial gradient per straight run (root-local), stops at every palette step of σ (cells from the path start).
    static func runs(_ ctx: ExitPaintContext, field: ColourField) -> [(CAGradientLayer, Bool)] {
        let p = ctx.pitch
        let lw = ctx.lineWidth
        let headHalf = p * 0.33 + 1                       // the head's half width (0.305 p) + AA
        let thinHalf = lw / 2 + 1
        let fillet = CGFloat(ctx.config.cornerFillet) * p
        let padAlong = fillet + lw / 2 + 1
        let stepPt = CGFloat(field.period) * p / CGFloat(field.palette.count)
        var out: [(CAGradientLayer, Bool)] = []
        var u: CGFloat = 0
        for piece in ctx.path.pieces {
            defer { u += piece.length }
            guard case let .line(a, b, len) = piece, len > 0.01 else { continue }
            // the head passes over this run (it travels the path beyond the resting body)
            let wide = u + len > ctx.restLength - p
            let half = wide ? headHalf : thinHalf
            let pad = wide ? max(padAlong, p * 0.5) : padAlong
            let ua = u - pad, ub = u + len + pad
            let horizontal = abs(b.y - a.y) < 0.5
            let pa = ctx.local.local(a), pb = ctx.local.local(b)
            let rect: CGRect = horizontal
                ? CGRect(x: min(pa.x, pb.x) - pad, y: pa.y - half, width: len + 2 * pad, height: 2 * half)
                : CGRect(x: pa.x - half, y: min(pa.y, pb.y) - pad, width: 2 * half, height: len + 2 * pad)
            var colors: [CGColor] = []
            var locs: [NSNumber] = []
            let span = ub - ua
            colors.append(field.colour(Double(ua / p)))
            locs.append(0)
            // the first palette step after ua: σ/period + phase crosses k/N
            let pos0 = CGFloat(field.position(Double(ua / p)))          // palette units at ua
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
            let gl = CAGradientLayer()
            gl.frame = rect
            gl.colors = colors
            gl.locations = locs
            let fwd = horizontal ? (b.x > a.x) : (b.y > a.y)
            gl.startPoint = horizontal ? CGPoint(x: fwd ? 0 : 1, y: 0.5) : CGPoint(x: 0.5, y: fwd ? 0 : 1)
            gl.endPoint = horizontal ? CGPoint(x: fwd ? 1 : 0, y: 0.5) : CGPoint(x: 0.5, y: fwd ? 1 : 0)
            out.append((gl, wide))
        }
        return out
    }
}

extension BoardEngine {
    /// Registers the B2 painters (idempotent): the ladder's `violet` and `rainbow` (board.json `violet.*`, `rainbow.*`).
    func installComboPainters() {
        guard painters["rainbow"] == nil else { return }
        painters["violet"] = FieldPainter(name: "violet", palette: fx.violetPalette, period: fx.violetPeriod)
        painters["rainbow"] = FieldPainter(name: "rainbow", palette: fx.rainbowPalette, period: fx.rainbowPeriod)
        missingPainters = []
    }
}
