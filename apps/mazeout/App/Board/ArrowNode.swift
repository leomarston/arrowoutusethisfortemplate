import UIKit
import PathCore

// B1 (SPEC-architecture §5.4). One resting arrow = exactly 2 layers (body stroke + head triangle), no animations; frames
// hug their paths (P4). While it moves, a mover owns its motion layers and these are hidden.

@MainActor final class ArrowNode {
    let spec: ArrowSpec
    let rest: ArrowPath
    let body = CAShapeLayer()
    let head = CAShapeLayer()
    private let local: LocalPath
    private let ink: CGColor
    private let red: CGColor
    /// Marked by a bump: red (#EE0A13) for the rest of the level (VERIFIED items, obstacles).
    private(set) var marked = false
    /// In the tree (false for hidden arrows until revealed, and after the exit).
    private(set) var attached = false

    var id: ArrowID { spec.id }
    var dir: Dir { spec.dir }
    var headCentre: CGPoint { rest.vertices[rest.vertices.count - 1] }
    /// The hint colour while this arrow is the bulb's hint (MA §3.10.1: stays green until tapped).
    private(set) var hintColor: CGColor?
    var color: CGColor { hintColor ?? (marked ? red : ink) }

    init(spec: ArrowSpec, geo: BoardGeometry, ink: CGColor, red: CGColor, scale: CGFloat) {
        self.spec = spec
        self.ink = ink
        self.red = red
        rest = geo.restPath(spec)
        local = LocalPath(rest.cgPath, pad: geo.lineWidth)
        body.frame = local.frame
        body.path = local.path
        body.fillColor = nil
        body.strokeColor = ink
        body.lineWidth = geo.lineWidth
        body.lineCap = .round
        body.lineJoin = .round
        body.contentsScale = scale
        let e = geo.headExtent
        head.bounds = CGRect(x: -e, y: -e, width: 2 * e, height: 2 * e)
        head.path = geo.headPath(spec.dir)
        head.fillColor = ink
        head.position = headCentre
        head.setAffineTransform(CGAffineTransform(rotationAngle: CGFloat(spec.dir.angle)))
        head.contentsScale = scale
    }

    /// Call inside a no-actions transaction (P1).
    func attach(to parent: CALayer) {
        guard !attached else { return }
        parent.addSublayer(body)
        parent.addSublayer(head)
        attached = true
    }

    func detach() {
        body.removeFromSuperlayer()
        head.removeFromSuperlayer()
        attached = false
    }

    /// Hides / shows both rest layers (a mover takes over while the arrow moves).
    func setVisible(_ v: Bool) {
        body.isHidden = !v
        head.isHidden = !v
    }

    /// Red for the rest of the level. Call inside a no-actions transaction.
    func mark(_ on: Bool = true) {
        marked = on
        body.strokeColor = color
        head.fillColor = color
    }

    /// The hint highlight on (a colour) or off (nil). Call inside a no-actions transaction.
    func setHinted(_ c: CGColor?) {
        hintColor = c
        if c == nil {
            body.removeAnimation(forKey: "hint")
            head.removeAnimation(forKey: "hint")
        }
        body.strokeColor = color
        head.fillColor = color
    }
}
