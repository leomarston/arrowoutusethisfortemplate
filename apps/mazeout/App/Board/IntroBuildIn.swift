import UIKit
import PathCore

// B1 → B2 (SPEC-architecture §5.7 "Build-in"; SPEC-motion-audio §3.6 (S1-L48-play-intro 60 Hz), MA9; CONSISTENCY T-9,
// T-10). Anchor K = the level screen's first frame:
//  - growFromTails: the board (the active set's container) scales 1.49 → 1.0 about the board centre, easeOutCubic,
//    1.35 s; the dots and the obstacles are complete from the first frame (they only zoom, MA §3.5.7);
//  - every arrow draws tail → head at once: strokeEnd f0 = 0.10 + 0.30/n on the first frame (n = its cells), linear to 1.0
//    at D(n) = 0.32 + 0.0216·n s; the head appears when the stroke reaches it;
//  - `.introFinished` at K + `intro.ackAt` (1.015 s, when the HUD starts to drop): the board is legible and input opens
//    (MA9; the original's gate is unobservable, the FEEL goal is no dead input) while the zoom still runs — the hit test
//    converts touches through the container's presentation transform (BoardEngine.introAdjusted);
//  - growFromTailsNoHUD (the FTUE's first board after the Loading cross-fade): the draw-in only, no zoom;
//    `.introFinished` at + `intro.ftueAckAt` (0.36 s, when "Tap to move!" appears);
//  - none: shown at once, `.introFinished` on the next run-loop turn.
// Arrows attached in later frames (F1 split loads) get the same draw with the same begin time: they join in phase.
// `introRunning` (isSettled) stays true until the zoom and the longest draw are over.

extension BoardEngine {
    func runIntro(_ style: IntroStyle) {
        guard let st = stage else { return }
        introRunning = true
        let c = config
        let t0 = roots.stage.convertTime(CACurrentMediaTime(), from: nil)
        var longest = 0.0
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        // F3-B: + the door stubs (door-hidden arrows poking out of their door, attached at load as preAttached: StageTransition)
        for a in st.level.arrows where (a.hiddenBy == nil || preAttached.contains(a.id)) && a.layer <= 1 {
            longest = max(longest, drawDuration(a.cells.count))
            guard let n = nodes[a.id], n.attached else { continue }
            n.setVisible(true)
            guard style != .none else { continue }
            addDraw(n, begin: t0)
        }
        if style == .growFromTails {
            let zoom = Anim.basic("transform.scale", from: c.introZoomFrom, to: 1, duration: c.introZoomDuration, begin: t0,
                                  function: Ease2.outCubic)
            roots.intro.add(zoom, forKey: "intro")
            longest = max(longest, c.introZoomDuration)
        }
        CATransaction.commit()
        introShown = true
        drawIn = style == .none ? nil : (t0, style != .growFromTails)
        introStartLocal = t0
        noteFirst("intro")
        if style == .none {
            DispatchQueue.main.async { [weak self] in
                self?.introRunning = false
                self?.delegate?.boardBeat(.introFinished)
            }
            return
        }
        let ack = style == .growFromTails ? fx.introAckAt : fx.ftueAckAt
        let token = stageToken
        Anim.beat(on: beatCarrier, key: "introAck\(beatSeq())", begin: t0, delay: min(ack, longest)) { [weak self] _ in
            guard let self, self.stageToken == token else { return }
            self.delegate?.boardBeat(.introFinished)
        }
        Anim.beat(on: beatCarrier, key: "introEnd\(beatSeq())", begin: t0, delay: longest) { [weak self] _ in
            guard let self, self.stageToken == token else { return }
            self.introRunning = false
            self.drawIn = nil
        }
    }

    /// B1 compatibility (tests / labs): the intro's end without waiting for the beats.
    func introDidFinish() {
        guard introRunning else { return }
        introRunning = false
        delegate?.boardBeat(.introFinished)
    }
}
