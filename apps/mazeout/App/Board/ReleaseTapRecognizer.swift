import UIKit

// B1 (SPEC-architecture §5.3, P5; the spike's recogniser). One finger down and up within `slop` points: recognised on
// TOUCH-UP however long the hold (the original fires on release even after a 5 s press, VERIFIED levels "Input model";
// UITapGestureRecognizer gives up on long holds). A second finger (pinch) or a move beyond the slop (a pan) fails it.
// `touchTimestamp` is the release's UITouch.timestamp (the LatencyProbe's first mark).
//
// R1 (the first-day check): with `require(toFail:)` on the scroll view's pan and pinch, `.ended` is delivered only when
// those fail. The lab-private launch argument `-pc.r1 fallback` switches to the fallback (no failure requirements; the
// recogniser vetoes itself in touchesEnded from the pan state, isZooming and isDecelerating) so BoardLab `latency` can
// measure both; `touchesEndedAt` → the action is the recogniser's own delay.

final class ReleaseTapRecognizer: UIGestureRecognizer {
    var slop: CGFloat = 10
    private(set) var touchTimestamp: TimeInterval = 0
    /// CACurrentMediaTime() when UIKit delivered the touch-up to this recogniser (R1: the handler must follow in the same
    /// event dispatch; `touchTimestamp → touchesEndedAt` is the system's own delivery time).
    private(set) var touchesEndedAt: CFTimeInterval = 0
    private(set) var releaseLocation: CGPoint = .zero
    /// Fallback mode (no failure requirements): the scroll view whose gestures veto the tap.
    weak var vetoScroll: UIScrollView?
    private var start: CGPoint = .zero

    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
        if (event.allTouches?.count ?? touches.count) > 1 || touches.count > 1 { state = .failed; return }
        guard let t = touches.first else { return }
        start = t.location(in: view)
    }

    override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent) {
        if (event.allTouches?.count ?? touches.count) > 1 { state = .failed; return }
        guard let t = touches.first else { return }
        let p = t.location(in: view)
        if hypot(p.x - start.x, p.y - start.y) > slop { state = .failed }
    }

    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent) {
        touchesEndedAt = CACurrentMediaTime()
        guard state == .possible, let t = touches.first else { state = .failed; return }
        if let s = vetoScroll {
            let pan = s.panGestureRecognizer.state
            if pan == .began || pan == .changed || s.isZooming || s.isDecelerating && s.isDragging {
                state = .failed
                return
            }
        }
        touchTimestamp = t.timestamp
        releaseLocation = t.location(in: view)
        state = .ended
    }

    override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent) { state = .cancelled }

    override func reset() {
        super.reset()
        start = .zero
    }
}
