import UIKit
import PathCore

// B2 (SPEC-architecture §5.1 "hint highlight"; SPEC-motion-audio §3.10.1; CONSISTENCY K-5/K-9/K-10). The bulb booster's
// board part (anchor B = the booster release; `hintShown(ids)` or `setHint(ids)` reaches the board on that frame):
//   #1 B + 0.05, 0.80 s: the camera zooms to MAX (28.07 pt/cell) centred on the hinted unit (clamped by the pan limit),
//      `ease` cb(0.25, 0.1, 0.25, 1);
//   #2–#6 the hinted arrow(s) blink: → #00DE00 at B + 1.03 (0.20 s), hold 0.13, → own colour 0.17, off 0.38, → green 0.19,
//      then stay green until tapped (the exit ramps from green, §3.2.1 #2);
//   #7 when the hinted unit's exit leaves the board: back to fit, centred, 0.50 s easeInOut.
// A pinch / pan during #1 or #7 cancels the camera (never fight the finger). `setHint([])` clears the highlight.

@MainActor final class HintState {
    let arrows: [ArrowID]
    var animator: UIViewPropertyAnimator?
    init(arrows: [ArrowID]) { self.arrows = arrows }
}

extension BoardEngine {
    func showHint(_ ids: [ArrowID]) {
        // clear the previous highlight
        if let old = hintState {
            for id in old.arrows { nodes[id]?.setHinted(nil) }
            cancelHintCamera()
        }
        hint = ids
        guard !ids.isEmpty, let st = stage else { hintState = nil; return }
        let state = HintState(arrows: ids)
        hintState = state
        let b = fx.hintBlink
        let t0 = Anim.now(roots.rest)
        let green = fx.hintColor
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for id in ids {
            guard let n = nodes[id], n.attached else { continue }
            let own = n.color
            n.setHinted(green)
            if b.count >= 6 {
                let t1 = b[0], t2 = t1 + b[1], t3 = t2 + b[2], t4 = t3 + b[3], t5 = t4 + b[4], t6 = t5 + b[5]
                let times = [0, t1, t2, t3, t4, t5, t6]
                let vals: [CGColor] = [own, own, green, green, own, own, green]
                n.body.add(Anim.keyframes("strokeColor", vals, times: times, duration: t6, begin: t0), forKey: "hint")
                n.head.add(Anim.keyframes("fillColor", vals, times: times, duration: t6, begin: t0), forKey: "hint")
            }
        }
        CATransaction.commit()
        // the camera: max zoom centred on the unit
        var pts: [CGPoint] = []
        for id in ids { if let a = st.level.arrows.first(where: { $0.id == id }) { pts.append(contentsOf: a.cells.map(st.geo.centre)) } }
        guard !pts.isEmpty else { return }
        let c = CGPoint(x: pts.map(\.x).reduce(0, +) / CGFloat(pts.count), y: pts.map(\.y).reduce(0, +) / CGFloat(pts.count))
        let s = container.scroll
        let zTarget = s.maximumZoomScale
        let curve = fx.hintCurve.count == 4 ? fx.hintCurve : [0.25, 0.1, 0.25, 1]
        let anim = UIViewPropertyAnimator(duration: fx.hintCameraDur,
                                          controlPoint1: CGPoint(x: curve[0], y: curve[1]),
                                          controlPoint2: CGPoint(x: curve[2], y: curve[3])) { [weak self] in
            guard let self else { return }
            let off = self.offset(zoom: zTarget, centredOn: c)
            s.zoomScale = zTarget
            s.updateInsets()
            s.contentOffset = off
        }
        anim.addCompletion { [weak self] _ in
            guard let self else { return }
            self.container.scroll.updateInsets()
            self.delegate?.boardZoomChanged(scale: self.zoomScale)
        }
        state.animator = anim
        anim.startAnimation(afterDelay: fx.hintCameraDelay)
        noteFirst("hint")
    }

    func cancelHintCamera() {
        guard let a = hintState?.animator else { return }
        if a.state == .active { a.stopAnimation(false); a.finishAnimation(at: .current) }
        hintState?.animator = nil
    }

    /// The hinted unit's exit left the board: back to fit, centred (0.50 s easeInOut).
    func hintUnitLeft(_ id: ArrowID) {
        guard let st = hintState, st.arrows.contains(id) else { return }
        hintState = nil
        hint = []
        let s = container.scroll
        let fit: CGFloat = 1
        let anim = UIViewPropertyAnimator(duration: fx.hintReturnDur, curve: .easeInOut) { [weak self] in
            guard let self else { return }
            let off = self.offset(zoom: fit, centredOn: nil)
            s.zoomScale = fit
            s.updateInsets()
            s.contentOffset = off
        }
        anim.addCompletion { [weak self] _ in
            guard let self else { return }
            self.container.scroll.updateInsets()
            self.delegate?.boardZoomChanged(scale: self.zoomScale)
        }
        anim.startAnimation()
    }
}
