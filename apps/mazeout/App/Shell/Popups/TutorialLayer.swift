import SwiftUI
import PathCore

// SHELL S2 (SPEC-architecture §6.5 z 2; SPEC-ui §2.3.6; SPEC-motion-audio §6.4; tutorials §3; Levels/tutorials.json). The
// "Tap to move!" hint on stage 1 of "Levels 1-4": the caption (≈ 40 pt, tracking 0, solid navy #121B51, no outline, no plate, box
// 353) centred at (196.5, 289.1) and our hand (`tutorialHand`, 70 × 99 with its shadow) whose FINGERTIP is the anchor, placed by
// GAME's TutorialDirector on the hinted arrow (board.screenPoint(of:)). No dim, no spotlight, input not restricted.
// Motion (from `show`, which G2 calls at the stage-1 board's first frame + `tutorial.showAfter` 0.36 s):
//   caption  kf 0.7 → 0.98 → 1.10 → 1.05 → 1.0 over 0.16 s (`tutorial.captionKf`)
//   hand     0.24 → 1.0 about the fingertip, 0.28 s easeOutCubic; then the press loop: hold 0.28 (first) / 1.26, press → 0.53 in
//            0.48 s easeInOut, release → 1.0 in 0.36 s easeOutQuad (period 2.10 s)
//   dismiss  (the first accepted tap, `dismiss`) the caption 1 → 0 in 0.16 s easeInQuad, the hand fades in 0.12 s; then gone
// A TimelineView on the MotionClock runs only while the hint is up.

@MainActor @Observable final class TutorialHint {
    private(set) var caption: LocalizedStringResource?
    private(set) var fingertip: CGPoint = .zero                 // screen pt
    private(set) var shownAt: Double?                           // MotionClock game time
    private(set) var dismissedAt: Double?

    init() {}

    var isShown: Bool { shownAt != nil }

    /// Shows the hint now (caption key from tutorials.json, e.g. "Tap to move!").
    func show(caption: LocalizedStringResource, fingertip: CGPoint, clock: MotionClock) {
        self.caption = caption
        self.fingertip = fingertip
        shownAt = clock.gameTime()
        dismissedAt = nil
        Log.mark("tutorial", "show caption at (\(Int(fingertip.x)), \(Int(fingertip.y)))")
    }

    /// Moves the fingertip (the board zoomed or the arrow moved).
    func move(to fingertip: CGPoint) { self.fingertip = fingertip }

    /// The first accepted tap: the caption shrinks away and the hand fades; the layer clears itself afterwards.
    func dismiss(clock: MotionClock) {
        guard shownAt != nil, dismissedAt == nil else { return }
        dismissedAt = clock.gameTime()
        Log.mark("tutorial", "dismiss")
        let wait = 0.2 / max(clock.baseTimeScale, 0.01)
        Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(wait * 1_000_000_000))
            self?.clear()
        }
    }

    func clear() {
        caption = nil
        shownAt = nil
        dismissedAt = nil
    }
}

struct TutorialLayer: View {
    let hint: TutorialHint
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        ZStack(alignment: .topLeading) {
            if let start = hint.shownAt, let caption = hint.caption {
                TimelineView(.animation) { ctx in
                    let now = app.clock.gameTime(ctx.date)
                    let u = app.clock.sequenceTime("caption", now - start)
                    let out = hint.dismissedAt.map { now - $0 }
                    TutorialFrame(caption: caption, fingertip: hint.fingertip, u: u, out: out, motion: TutorialMotion(app.tuning.ui),
                                  t: app.tuning.ui.tokens, m: m)
                }
            }
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .allowsHitTesting(false)
    }
}

/// The tutorial's curves (ui.json `tutorial.*`, SPEC-motion-audio §6.4).
struct TutorialMotion {
    var captionKf: [Double] = [0, 0.7, 0.04, 0.98, 0.08, 1.10, 0.12, 1.05, 0.16, 1.0]
    var handIn: [Double] = [0.24, 0.28]
    var handLoop: [Double] = [1.26, 0.48, 0.36]
    var press = 0.53
    var firstHold = 0.28
    var captionOut = 0.16
    var handOut = 0.12

    init(_ ui: UITuning) {
        let f = ui.file
        let kf = f.doubles("tutorial.captionKf", captionKf)
        captionKf = kf.count >= 4 && kf.count % 2 == 0 ? kf : captionKf
        let hi = f.doubles("tutorial.handIn", handIn); handIn = hi.count == 2 ? hi : handIn
        let hl = f.doubles("tutorial.handLoop", handLoop); handLoop = hl.count == 3 ? hl : handLoop
        press = f.double("tutorial.handPressScale", press)
        firstHold = f.double("tutorial.handFirstHold", firstHold)
        captionOut = f.double("tutorial.captionOut", captionOut)
        handOut = f.double("tutorial.handOut", handOut)
    }

    func captionScale(_ u: Double) -> Double {
        let tr = HUDMotion.track(captionKf)
        return u >= tr.end ? 1 : tr(max(0, u))
    }

    func handScale(_ u: Double) -> Double {
        let inDur = handIn[1]
        if u < inDur { return handIn[0] + (1 - handIn[0]) * Easing.outCubic(u / inDur) }
        var x = u - inDur
        if x < firstHold { return 1 }
        x -= firstHold
        let pressDur = handLoop[1], releaseDur = handLoop[2], hold = handLoop[0]
        let period = pressDur + releaseDur + hold
        x = x.truncatingRemainder(dividingBy: period)
        if x < pressDur { return 1 + (press - 1) * Easing.inOutQuad(x / pressDur) }
        if x < pressDur + releaseDur { return press + (1 - press) * Easing.outQuad((x - pressDur) / releaseDur) }
        return 1
    }
}

private struct TutorialFrame: View {
    let caption: LocalizedStringResource
    let fingertip: CGPoint
    let u: Double
    let out: Double?
    let motion: TutorialMotion
    let t: Tokens
    let m: ShellMetrics

    var body: some View {
        let style = t.text("tutorial.caption", .s2(40, 0, [0x072527])).sized(40 * m.s)
        let p = t.textPoint("tutorial.caption", baseline: 303.0, centreX: 196.5)
        let at = m.point(CGPoint(x: p.x, y: p.baseline), .top)
        let captionScale = out.map { max(0, 1 - Easing.inQuad($0 / max(0.01, motion.captionOut))) } ?? motion.captionScale(u)
        let handAlpha = out.map { max(0, 1 - $0 / max(0.01, motion.handOut)) } ?? 1
        // the hand: 70 pt wide with its shadow; the fingertip is at (23.67, 6.0) pt of the 102 × 136 canvas (measured on the @3x file)
        let k = CGFloat(t.number("tutorial.handScale", 0.808)) * m.s
        let tip = CGPoint(x: 23.67, y: 6.0)
        let canvas = CGRect(x: fingertip.x - tip.x * k, y: fingertip.y - tip.y * k, width: 102 * k, height: 136 * k)
        ZStack(alignment: .topLeading) {
            GameText(caption, style: style, maxWidth: CGFloat(t.textMaxWidth("tutorial.caption", 353) ?? 353) * m.s)
                .scaleEffect(CGFloat(captionScale))
                .at(at.x, style.capCentre(baseline: at.y))
                .accessibilityIdentifier("tutorial.caption")
            ArtImage(art: .tutorialHand)
                .frame(width: canvas.width, height: canvas.height)
                .scaleEffect(CGFloat(motion.handScale(u)), anchor: UnitPoint(x: tip.x / 102, y: tip.y / 136))
                .opacity(handAlpha)
                .position(x: canvas.midX, y: canvas.midY)
                .accessibilityElement()
                .accessibilityIdentifier("tutorial.hand")
        }
    }
}
