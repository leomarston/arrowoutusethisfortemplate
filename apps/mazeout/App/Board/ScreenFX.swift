import UIKit

// B1 (SPEC-architecture §5.1 "ScreenFXView", §5.8). Screen-space feedback over the board (not zoomed, no touches): tap
// ripples and the red bump vignette. It has its own freeze (layer speed / timeOffset), mirrored with the stage's (§5.12).
//
// Vignette (research/motion.md §4, pass 2, identical on both v552 clips): all four screen edges tint red, an overlay
// ≈ #FF0000 at alpha 0.42·e^(−d/27 pt) (d = distance from the edge), full on the contact frame, holds ≈ 0.035 s, fades
// ≈ linearly to 0 at 0.33 s. Four axial gradients (built once) under one container whose opacity is animated.

@MainActor final class ScreenFXView: UIView {
    let fxLayer = CALayer()
    private let vignette = CALayer()
    private var edges: [CAGradientLayer] = []
    private(set) var ripples: RipplePool?
    private var vignetteDepth: CGFloat = 81

    override init(frame: CGRect) {
        super.init(frame: frame)
        isUserInteractionEnabled = false
        backgroundColor = .clear
        layer.addSublayer(fxLayer)
        vignette.opacity = 0
        fxLayer.addSublayer(vignette)
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }

    func configure(_ c: BoardConfig, scale: CGFloat) {
        guard ripples == nil else { return }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        ripples = RipplePool(config: c, parent: fxLayer, scale: scale)
        let decay = CGFloat(max(1, c.vignetteDecayPt))
        vignetteDepth = decay * 3
        let steps = 8
        var colors: [CGColor] = []
        var locs: [NSNumber] = []
        for i in 0...steps {
            let f = CGFloat(i) / CGFloat(steps)
            let d = f * vignetteDepth
            let a = c.vignetteAlpha * exp(-Double(d / decay))
            colors.append(UIColor(red: 1, green: 0, blue: 0, alpha: CGFloat(a)).cgColor)
            locs.append(NSNumber(value: Double(f)))
        }
        colors[colors.count - 1] = UIColor(red: 1, green: 0, blue: 0, alpha: 0).cgColor
        edges = (0..<4).map { _ in
            let g = CAGradientLayer()
            g.colors = colors
            g.locations = locs
            vignette.addSublayer(g)
            return g
        }
        CATransaction.commit()
        setNeedsLayout()
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        fxLayer.frame = bounds
        vignette.frame = bounds
        let d = min(vignetteDepth, bounds.width / 2, bounds.height / 2)
        let w = bounds.width, h = bounds.height
        if edges.count == 4 {
            // top, bottom, left, right: each gradient runs from its edge inward
            edges[0].frame = CGRect(x: 0, y: 0, width: w, height: d)
            edges[0].startPoint = CGPoint(x: 0.5, y: 0); edges[0].endPoint = CGPoint(x: 0.5, y: 1)
            edges[1].frame = CGRect(x: 0, y: h - d, width: w, height: d)
            edges[1].startPoint = CGPoint(x: 0.5, y: 1); edges[1].endPoint = CGPoint(x: 0.5, y: 0)
            edges[2].frame = CGRect(x: 0, y: 0, width: d, height: h)
            edges[2].startPoint = CGPoint(x: 0, y: 0.5); edges[2].endPoint = CGPoint(x: 1, y: 0.5)
            edges[3].frame = CGRect(x: w - d, y: 0, width: d, height: h)
            edges[3].startPoint = CGPoint(x: 1, y: 0.5); edges[3].endPoint = CGPoint(x: 0, y: 0.5)
        }
        CATransaction.commit()
    }

    /// The fx layer's local time now (the begin time of anything added this run-loop turn).
    var localNow: CFTimeInterval { fxLayer.convertTime(CACurrentMediaTime(), from: nil) }

    /// A ripple at a screen point (this view's coordinates). Call inside the tap's no-actions transaction.
    func ripple(at p: CGPoint) {
        ripples?.play(at: p, begin: localNow)
    }

    /// The bump vignette, starting `delay` seconds from now (the contact frame).
    func playVignette(delay: Double, config c: BoardConfig) {
        let total = max(c.vignetteTotal, c.vignetteHold + 0.01)
        let a = Anim.keyframes("opacity", [1, 1, 0], times: [0, c.vignetteHold, total], duration: total,
                               begin: localNow + delay)
        a.fillMode = .forwards
        a.isRemovedOnCompletion = true
        vignette.removeAnimation(forKey: "v")
        vignette.add(a, forKey: "v")
    }

    /// Freeze / slow motion, mirrored with the stage (§5.12).
    func applyTiming(speed: Float, freezeAt local: CFTimeInterval?) {
        BoardEngine.setLayerTiming(fxLayer, speed: speed, freezeAt: local)
    }
}
