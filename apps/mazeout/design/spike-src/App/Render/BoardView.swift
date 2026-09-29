import UIKit

/// The board: UIScrollView zoom/pan over a content view whose bounds are board space at fit (zoomScale 1).
/// Everything that moves runs on the render server; the main thread only resolves taps and adds animations.
final class BoardView: UIView, UIScrollViewDelegate, UIGestureRecognizerDelegate {
    let tun = Tunables.shared
    let scroll = UIScrollView()
    let content = UIView()
    /// All board layers; pausing it (speed 0) freezes every board animation for screenshots.
    let stage = CALayer()
    let dotsLayer = CALayer()
    let arrowsLayer = CALayer()
    let tapeLayer = CALayer()
    let movingLayer = CALayer()
    let fxLayer = CALayer()

    private(set) var level: LevelSpec!
    private(set) var state: BoardState!
    private(set) var layout: BoardLayout!
    private(set) var nodes: [ArrowNode?] = []
    private(set) var movers: [Int: Mover] = [:]
    private(set) var hearts = 3
    var onChange: (() -> Void)?
    var onReady: (() -> Void)?
    private(set) var buildMs: Double = 0
    private var built = false

    /// Play area on the 393x852 reference (shot 003): HUD bottom 122 pt, booster bar top 755 pt.
    static let hudBottom: CGFloat = 122
    static let boosterTop: CGFloat = 755

    init(level: LevelSpec) {
        self.level = level
        super.init(frame: .zero)
        backgroundColor = .white
        scroll.delegate = self
        scroll.minimumZoomScale = tun.zoomMin
        scroll.maximumZoomScale = tun.zoomMax
        scroll.bouncesZoom = true
        scroll.showsVerticalScrollIndicator = false
        scroll.showsHorizontalScrollIndicator = false
        scroll.contentInsetAdjustmentBehavior = .never
        scroll.delaysContentTouches = false
        scroll.clipsToBounds = false
        addSubview(scroll)
        scroll.addSubview(content)
        content.layer.addSublayer(stage)
        for l in [dotsLayer, arrowsLayer, tapeLayer, movingLayer, fxLayer] { stage.addSublayer(l) }
        // NOT UITapGestureRecognizer: it gives up on a long hold, while the original fires on release even
        // after a 5 s press (research/levels.md). ReleaseTap ends on touch-up whatever the hold time.
        let tap = ReleaseTapRecognizer(target: self, action: #selector(onTap(_:)))
        tap.require(toFail: scroll.panGestureRecognizer)
        if let pinch = scroll.pinchGestureRecognizer { tap.require(toFail: pinch) }
        scroll.addGestureRecognizer(tap)
        accessibilityIdentifier = "board"
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }

    override func layoutSubviews() {
        super.layoutSubviews()
        guard !built, bounds.width > 0, bounds.height > 0 else { return }
        built = true
        build()
        onReady?()
    }

    var scale: CGFloat { max(window?.screen.scale ?? traitCollection.displayScale, 1) }
    var zoom: CGFloat { scroll.zoomScale }
    var visibleBoardRect: CGRect { scroll.convert(scroll.bounds, to: content) }
    var layerCount: Int { countLayers(stage) }

    private func countLayers(_ l: CALayer) -> Int { 1 + (l.sublayers ?? []).reduce(0) { $0 + countLayers($1) } }

    // MARK: build

    private func build() {
        let t0 = CACurrentMediaTime()
        let size = bounds.size
        let play = CGRect(x: 0, y: Self.hudBottom, width: size.width, height: Self.boosterTop - Self.hudBottom)
        layout = BoardLayout(cols: level.cols, rows: level.rows, content: size, play: play)
        state = BoardState(level: level)
        hearts = level.hearts ?? 3
        let sc = scale
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        scroll.frame = bounds
        content.frame = CGRect(origin: .zero, size: size)
        scroll.contentSize = size
        stage.frame = content.bounds
        stage.speed = tun.slowmo
        for l in [dotsLayer, arrowsLayer, tapeLayer, movingLayer, fxLayer] { l.frame = stage.bounds }
        nodes = level.arrows.enumerated().map { i, a in
            let n = ArrowNode(index: i, geo: ArrowGeometry(spec: a, layout: layout), scale: sc)
            n.add(to: arrowsLayer)
            return n
        }
        for (k, t) in (level.tapes ?? []).enumerated() {
            let l = tapeShape(t, scale: sc)
            tapeLayer.addSublayer(l)
            tapeLayers[k] = l
        }
        CATransaction.commit()
        buildMs = (CACurrentMediaTime() - t0) * 1000
    }

    /// OUR placeholder for the tape obstacle (pink band across 4 arrows); the real art is an art-spike item.
    private func tapeShape(_ t: TapeSpec, scale: CGFloat) -> CALayer {
        let cs = t.cells.map(layout.centre)
        let minX = cs.map(\.x).min()!, maxX = cs.map(\.x).max()!, minY = cs.map(\.y).min()!, maxY = cs.map(\.y).max()!
        let p = layout.pitch
        let vertical = t.orientation == "vertical"
        let rect = vertical
            ? CGRect(x: minX - 0.45 * p, y: minY - 0.62 * p, width: 0.9 * p, height: maxY - minY + 1.24 * p)
            : CGRect(x: minX - 0.62 * p, y: minY - 0.45 * p, width: maxX - minX + 1.24 * p, height: 0.9 * p)
        let l = CAShapeLayer()
        l.frame = rect
        let path = CGMutablePath()
        let w = vertical ? rect.width : rect.height
        let len = vertical ? rect.height : rect.width
        for k in 0..<2 {   // two crossing strips
            let off = CGFloat(k) * 0.5 * w
            let strip = CGRect(x: 0, y: 0, width: vertical ? w * 0.5 : len, height: vertical ? len : w * 0.5)
            var tr = vertical ? CGAffineTransform(translationX: off, y: 0) : CGAffineTransform(translationX: 0, y: off)
            path.addPath(CGPath(roundedRect: strip, cornerWidth: w * 0.18, cornerHeight: w * 0.18, transform: &tr))
        }
        l.path = path
        l.fillColor = UIColor(red: 1, green: 98 / 255, blue: 152 / 255, alpha: 1).cgColor
        l.strokeColor = UIColor(red: 0.85, green: 0.25, blue: 0.5, alpha: 1).cgColor
        l.lineWidth = max(1, p * 0.03)
        l.contentsScale = scale
        return l
    }

    // MARK: zoom

    func viewForZooming(in scrollView: UIScrollView) -> UIView? { content }
    func scrollViewDidZoom(_ scrollView: UIScrollView) { centreContent() }
    func scrollViewDidEndZooming(_ scrollView: UIScrollView, with view: UIView?, atScale scale: CGFloat) { onChange?() }
    func scrollViewDidEndDecelerating(_ scrollView: UIScrollView) { onChange?() }

    /// Test hook: window point of a free arrow's middle cell that is on screen (nil if none).
    func freeArrowWindowPoint() -> CGPoint? {
        let vis = visibleBoardRect.insetBy(dx: layout.pitch, dy: layout.pitch)
        let playTop = convert(CGPoint(x: 0, y: Self.hudBottom), to: content).y
        let playBottom = convert(CGPoint(x: 0, y: Self.boosterTop), to: content).y
        for i in 0..<level.arrows.count where state.unitFree(i) && state.unit(of: i).count == 1 && movers[i] == nil && nodes[i] != nil {
            let cells = level.arrows[i].cells
            let p = layout.centre(cells[cells.count / 2])
            if vis.contains(p), p.y > playTop, p.y < playBottom { return content.convert(p, to: nil) }
        }
        return nil
    }

    private func centreContent() {
        let s = scroll.bounds.size, c = scroll.contentSize
        let inset = UIEdgeInsets(top: max(0, (s.height - c.height) / 2), left: max(0, (s.width - c.width) / 2),
                                 bottom: max(0, (s.height - c.height) / 2), right: max(0, (s.width - c.width) / 2))
        if scroll.contentInset != inset { scroll.contentInset = inset }
    }

    /// Zooms to `z` with board point `p` at the centre of the play area.
    func setZoom(_ z: CGFloat, centredOn p: CGPoint) {
        scroll.setZoomScale(z, animated: false)
        centreContent()
        let playMid = CGPoint(x: bounds.midX, y: (Self.hudBottom + Self.boosterTop) / 2)
        var off = CGPoint(x: p.x * z - playMid.x, y: p.y * z - playMid.y)
        if z >= 1 {
            let maxX = scroll.contentSize.width - scroll.bounds.width, maxY = scroll.contentSize.height - scroll.bounds.height
            off.x = min(max(off.x, 0), max(maxX, 0))
            off.y = min(max(off.y, 0), max(maxY, 0))
        } else {
            off = CGPoint(x: -scroll.contentInset.left, y: -scroll.contentInset.top)
        }
        scroll.contentOffset = off
    }

    // MARK: input

    /// Fires on touch-up, like the original (research/levels.md: a 5 s hold does nothing until release).
    @objc private func onTap(_ r: UIGestureRecognizer) {
        guard r.state == .ended else { return }
        let p = r.location(in: content)
        ripple(at: p)
        guard let i = arrow(at: p) else { return }
        tapArrow(i)
    }

    /// Grey tap disc at the touch point (seen on the phone; size/timing PLACEHOLDER until measured).
    private func ripple(at p: CGPoint) {
        let r = 0.9 * layout.pitch
        let l = CAShapeLayer()
        l.bounds = CGRect(x: -r, y: -r, width: 2 * r, height: 2 * r)
        l.position = p
        l.path = CGPath(ellipseIn: l.bounds, transform: nil)
        l.fillColor = UIColor(white: 0.5, alpha: 0.25).cgColor
        l.contentsScale = scale
        l.opacity = 0
        let g = CABasicAnimation(keyPath: "transform.scale")
        g.fromValue = 0.3
        g.toValue = 1
        let f = CABasicAnimation(keyPath: "opacity")
        f.fromValue = 1
        f.toValue = 0
        let grp = CAAnimationGroup()
        grp.animations = [g, f]
        grp.duration = 0.3
        grp.delegate = AnimationEnd { _ in l.removeFromSuperlayer() }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        fxLayer.addSublayer(l)
        l.add(grp.hi(), forKey: "ripple")
        CATransaction.commit()
    }

    /// Grid maths: the touched cell's owner, else the nearest centreline within max(0.5 cell, 14 screen pt)
    /// among the owners of the 5x5 cells around the touch (no scan over all arrows).
    func arrow(at p: CGPoint) -> Int? {
        let c = layout.cell(at: p)
        if let o = state.owner(c) { return o }
        let tol = max(0.5 * layout.pitch, 14 / zoom)
        var best: Int?, bestD = tol * tol
        var seen = Set<Int>()
        let reach = Int((tol / layout.pitch).rounded(.up)) + 1
        for dr in -reach...reach {
            for dc in -reach...reach {
                guard let o = state.owner(Cell(c.c + dc, c.r + dr)), seen.insert(o).inserted, let n = nodes[o] else { continue }
                let pts = n.geo.corners
                for k in 1..<pts.count {
                    let d = dist2(p, pts[k - 1], pts[k])
                    if d < bestD { bestD = d; best = o }
                }
            }
        }
        return best
    }

    private var tapeLayers: [Int: CALayer] = [:]

    @discardableResult
    func tapArrow(_ i: Int) -> TapOutcome {
        guard movers[i] == nil else { return .ignored }
        let out = state.tap(i)
        switch out {
        case .exits: startExit(i)
        case let .exitsGroup(members, tape):
            var longest: Track?
            var dir = CGVector.zero
            for a in members {
                if let n = nodes[a] { dir = n.geo.dir }
                if let t = startExit(a), t.final > (longest?.final ?? -1) { longest = t }
            }
            if let t = longest, let l = tapeLayers.removeValue(forKey: tape) { carryTape(l, dir: dir, track: t) }
        case let .blocked(_, _, gap): startBump(i, gap: gap)
        case .ignored: break
        }
        onChange?()
        return out
    }

    var profile: TravelProfile {
        TravelProfile(v: tun.exitSpeedIsScreenSpace ? tun.exitSpeed / zoom : tun.exitSpeed, accel: tun.exitAccel)
    }

    private func carryTape(_ tape: CALayer, dir: CGVector, track: Track) {
        let p0 = tape.position
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        tape.position = CGPoint(x: p0.x + dir.dx * track.final, y: p0.y + dir.dy * track.final)
        let a = keyframes("position", track.travel.map { NSValue(cgPoint: CGPoint(x: p0.x + dir.dx * $0, y: p0.y + dir.dy * $0)) }, track)
        a.delegate = AnimationEnd { _ in tape.removeFromSuperlayer() }
        tape.add(a, forKey: "carry")
        CATransaction.commit()
    }

    @discardableResult
    private func startExit(_ i: Int) -> Track? {
        guard let node = nodes[i] else { return nil }
        let g = node.geo
        // the tail must clear whatever the player can see during the exit, even after zooming out
        let far = visibleBoardRect.union(content.bounds.insetBy(dx: -bounds.width * 0.25, dy: -bounds.height * 0.25))
        let travel = g.exitTravel(leaving: far)
        let ray = travel - g.bodyLength + g.pitch
        let p = profile
        let track = Track.forward(p, to: travel)
        let m = Mover(node: node)
        movers[i] = m
        m.onFinish = { [weak self] in
            self?.movers[i] = nil
            self?.nodes[i] = nil
            self?.onChange?()
        }
        m.playExit(ray: ray, track: track, profile: p, tun: tun, into: movingLayer, dotsParent: dotsLayer,
                   fxParent: fxLayer, scale: scale)
        return track
    }

    private func startBump(_ i: Int, gap: Int) {
        guard let node = nodes[i] else { return }
        let m = Mover(node: node)
        movers[i] = m
        m.onFinish = { [weak self] in self?.movers[i] = nil }
        m.playBump(contact: node.geo.contactTravel(gap: gap), profile: profile, tun: tun, into: movingLayer,
                   scale: scale) { [weak self] in
            guard let self else { return }
            self.hearts = max(0, self.hearts - 1)
            self.onChange?()
        }
    }

    // MARK: freeze (screenshots)

    func freeze() {
        let t = stage.convertTime(CACurrentMediaTime(), from: nil)
        stage.speed = 0
        stage.timeOffset = t
    }
}

/// One finger down, up within `slop` points: recognised on touch-up, however long the hold.
final class ReleaseTapRecognizer: UIGestureRecognizer {
    var slop: CGFloat = 10
    private var start: CGPoint = .zero

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
        if (event.allTouches?.count ?? touches.count) > 1 { state = .failed; return }
        start = touches.first!.location(in: view)
    }
    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent) {
        let p = touches.first!.location(in: view)
        if hypot(p.x - start.x, p.y - start.y) > slop { state = .failed }
    }
    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent) {
        state = state == .possible ? .ended : .failed
    }
    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent) { state = .cancelled }
}
