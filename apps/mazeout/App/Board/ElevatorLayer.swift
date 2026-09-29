import UIKit
import PathCore

// B2 (SPEC-architecture §5.6 "elevator"; SPEC.md §5.11/§5.20: the videos' mechanics in the phone palette; MANIFEST
// elevatorPlatform (code route): a translucent lavender slab with a hatched rim and a vertical centre divider (two closed
// doors), the board's dots showing through; SPEC-motion-audio §3.5.5).
// Z order (roots): dots → `under` (the elevator's hidden layer-2 arrows) → `platform` (this) → rest (the layer-1 arrows
// standing ON the platform) → obstacles … so the platform covers what is below it and never the arrows on it.
// Activation (anchor O = the frame the LAST platform arrow's tail clears the platform cells, 0.15–0.55 s after its tap):
//   #1 O + 0.02, 0.30 s: the two door halves part from the centre divider outward (easeInOut), clipped by the frame;
//   #2 O + 0.02, 0.30 s: the hidden layer (its arrows) shows under a black tint 0.55 → 0 (linear);
//   #3 O + 0.30, 0.15 s: the frame + hatched rim fade out.
// The layer-2 arrows are live from the TAP (rules `elevator.activateAt "tap"`); only their look waits for O.

@MainActor final class ElevatorNode {
    let id: ObstacleID
    let spec: ObstacleSpec
    let block: CGRect
    let root = CALayer()          // in the `platform` root
    let tint = CALayer()
    let doors = CALayer()         // clips the halves
    let left = CAShapeLayer()
    let right = CAShapeLayer()
    let frameLayer = CALayer()
    var active = false

    init(spec: ObstacleSpec, geo: BoardGeometry, scale: CGFloat) {
        id = spec.id
        self.spec = spec
        let p = geo.pitch
        let cs = spec.cells.isEmpty ? [Cell(0, 0)] : spec.cells
        let minC = cs.map(\.c).min()!, maxC = cs.map(\.c).max()!
        let minR = cs.map(\.r).min()!, maxR = cs.map(\.r).max()!
        let tl = geo.centre(Cell(minC, minR))
        block = CGRect(x: tl.x - p / 2, y: tl.y - p / 2, width: CGFloat(maxC - minC + 1) * p, height: CGFloat(maxR - minR + 1) * p)
        root.frame = block
        let local = CGRect(origin: .zero, size: block.size)
        let rimW = 0.22 * p
        let inner = local.insetBy(dx: rimW, dy: rimW)
        // the hidden layer's tint (under the doors; shown only while the doors part)
        tint.frame = inner
        tint.backgroundColor = UIColor.black.cgColor
        tint.opacity = 0
        root.addSublayer(tint)
        // two closed door halves (translucent lavender: the dots show through), clipped by the frame opening
        doors.frame = inner
        doors.masksToBounds = true
        let half = CGRect(x: 0, y: 0, width: inner.width / 2, height: inner.height)
        for (l, x) in [(left, CGFloat(0)), (right, inner.width / 2)] {
            l.frame = CGRect(x: x, y: 0, width: half.width, height: half.height)
            l.path = CGPath(rect: CGRect(origin: .zero, size: half.size), transform: nil)
            // PUBLISH R7 (D1 skin): sand planks (d1_skin.py "sand") instead of the measured lavender
            l.fillColor = BoardConfig.color("#DFC393").copy(alpha: 0.62)
            l.strokeColor = BoardConfig.color("#BE8A49").copy(alpha: 0.9)
            l.lineWidth = 0.06 * p
            l.contentsScale = scale
            doors.addSublayer(l)
        }
        root.addSublayer(doors)
        // the frame: a rounded rim with a diagonal hatch
        frameLayer.frame = local
        let rim = CAShapeLayer()
        let r = 0.3 * p
        rim.path = CGPath(roundedRect: local.insetBy(dx: rimW / 2, dy: rimW / 2), cornerWidth: r, cornerHeight: r, transform: nil)
        rim.fillColor = nil
        rim.strokeColor = BoardConfig.color("#D3AC73").copy(alpha: 0.95)
        rim.lineWidth = rimW
        rim.contentsScale = scale
        frameLayer.addSublayer(rim)
        let hatch = CAShapeLayer()
        let hp = CGMutablePath()
        let step = 0.3 * p
        var t: CGFloat = 0
        let perimeterBoxes: [CGRect] = [CGRect(x: 0, y: 0, width: local.width, height: rimW),
                                        CGRect(x: 0, y: local.height - rimW, width: local.width, height: rimW),
                                        CGRect(x: 0, y: rimW, width: rimW, height: local.height - 2 * rimW),
                                        CGRect(x: local.width - rimW, y: rimW, width: rimW, height: local.height - 2 * rimW)]
        for b in perimeterBoxes {
            t = b.minX - b.height
            while t < b.maxX {
                // short diagonals inside the rim band (clipped by construction to the band)
                if b.width >= b.height {
                    let x0 = max(b.minX, t), x1 = min(b.maxX, t + b.height)
                    hp.move(to: CGPoint(x: x0, y: b.maxY - (x0 - t))); hp.addLine(to: CGPoint(x: x1, y: b.maxY - (x1 - t)))
                    t += step
                } else {
                    break
                }
            }
            if b.width < b.height {
                var y = b.minY
                while y < b.maxY {
                    let y1 = min(b.maxY, y + b.width)
                    hp.move(to: CGPoint(x: b.minX, y: y1)); hp.addLine(to: CGPoint(x: b.minX + (y1 - y), y: y))
                    y += step
                }
            }
        }
        hatch.path = hp
        hatch.strokeColor = BoardConfig.color("#B07B3C").copy(alpha: 0.8)
        hatch.lineWidth = 0.05 * p
        hatch.contentsScale = scale
        frameLayer.addSublayer(hatch)
        let divider = CAShapeLayer()
        let dp = CGMutablePath()
        dp.move(to: CGPoint(x: local.midX, y: inner.minY)); dp.addLine(to: CGPoint(x: local.midX, y: inner.maxY))
        divider.path = dp
        divider.strokeColor = BoardConfig.color("#B07B3C")
        divider.lineWidth = 0.08 * p
        divider.contentsScale = scale
        frameLayer.addSublayer(divider)
        root.addSublayer(frameLayer)
    }

    /// Plays the activation with O = `o` seconds after `begin` (stage-local).
    func activate(begin: CFTimeInterval, o: Double, fx: EffectsConfig) {
        guard !active else { return }
        active = true
        let t1 = begin + o + fx.elevatorDoorsAt
        let d = max(0.05, fx.elevatorDoorsDur)
        let w = doors.bounds.width / 2
        for (l, dir) in [(left, CGFloat(-1)), (right, CGFloat(1))] {
            let a = Anim.basic("position.x", from: l.position.x, to: l.position.x + dir * w, duration: d, begin: t1,
                               function: Ease2.inOut)
            l.position.x += dir * w
            l.add(a, forKey: "part")
        }
        tint.opacity = 0
        let ta = Anim.keyframes("opacity", [0, fx.elevatorTintFrom, 0].map { NSNumber(value: $0) },
                                times: [0, 0.0001, d], duration: d, begin: t1)
        ta.fillMode = .forwards
        tint.add(ta, forKey: "tint")
        let f0 = begin + o + fx.elevatorFrameFadeAt
        let fd = max(0.02, fx.elevatorFrameFadeDur)
        frameLayer.opacity = 0
        frameLayer.add(Anim.basic("opacity", from: 1, to: 0, duration: fd, begin: f0), forKey: "fade")
        Anim.switchOpacity(doors, from: 1, to: 0, begin: begin, at: o + fx.elevatorDoorsAt + d, key: "doorsGone")
    }
}

extension BoardEngine {
    /// O: seconds after the release until the last of `unit`'s tails has cleared the platform (tail = the moving path's
    /// start point at the head's travel).
    func elevatorClearTime(_ plan: ExitPlan, platform: CGRect) -> Double {
        guard let st = stage else { return 0.3 }
        let p = st.geo.pitch
        var worst = 0.15
        for id in plan.unit {
            guard let a = st.level.arrows.first(where: { $0.id == id }) else { continue }
            let beyond: [Cell] = plan.paths[id].map { $0.cells.count > a.cells.count ? Array($0.cells[a.cells.count...]) : [] } ?? []
            let path = st.geo.movingPath(a, beyond: beyond, extend: p * 2)
            let zone = platform.insetBy(dx: -p * 0.5, dy: -p * 0.5)
            var u: CGFloat = 0
            var lastInside: CGFloat = 0
            let restLen = st.geo.restPath(a).length
            while u < restLen + CGFloat(beyond.count + 2) * p {
                if zone.contains(path.point(at: u)) { lastInside = u }
                u += p * 0.25
            }
            worst = max(worst, kinematics.time(toTravel: Double((lastInside + p * 0.25) / p)))
        }
        return min(worst, 0.8)
    }
}
