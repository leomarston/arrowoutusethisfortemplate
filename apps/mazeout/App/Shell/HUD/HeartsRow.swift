import SwiftUI

// SHELL S2 (SPEC-ui §2.3.1 `hud.heart1..3`, VERIFIED 003 / meta-077; SPEC-motion-audio §3.4.5, §3.6 row 10, §4; CONSISTENCY B-6).
// Three slots 28.7 × 24.4 at x 201.5 / 237.5 / 273.6, y 82.1 (pitch 36.1). `.full` = `heartHUD`; `.lost` / `.empty` = the recessed
// slot `heartHUDLost`. Hearts are lost right → left: on the bump-contact frame the rightmost full heart BREAKS — it is hidden
// and the two halves of `heartHUDHalves` (split along its crack) fly apart: y = −115τ + 480τ², x = ±37.5τ, tilt ±25° by τ 0.12
// then ±40° by 0.40, fading 0.30 → 0.40 s, over the empty recess. The break is a one-shot TimelineView on the MotionClock,
// started by the model's full → lost change (GAME's HUDWriter writes it on the `.heartLost` event), outside the ≤ 10 Hz
// throttle. During the intro a slot shows the recess until its pop (`hudIntro.heartsAt`, `heartKf`); after Add Lives (+3) the
// refilled hearts re-pop left → right (`hud.refillStagger`, DECISION MA §4). No pop, no shake on a loss. Silent.

struct HUDHeartsRow: View {
    let hearts: [HeartSlotVM]
    /// Seconds since the level-start cut while the intro runs (nil = at rest).
    let introT: Double?
    let motion: HUDMotion
    let t: Tokens
    let m: ShellMetrics
    @Environment(AppModel.self) private var app
    @State private var breaks: [Int: Double] = [:]          // slot → game time of the contact frame
    @State private var refillAt: Double?                     // game time of the Add Lives refill

    var body: some View {
        let k = CGFloat(t.number("hud.heartInkScale", 1.07))
        let slots = Self.frames(t, m).map { $0.insetBy(dx: -$0.width * (k - 1) / 2, dy: -$0.height * (k - 1) / 2) }
        let live = !breaks.isEmpty || refillAt != nil
        TimelineView(.animation(minimumInterval: nil, paused: !live)) { ctx in
            let now = live ? app.clock.gameTime(ctx.date) : 0
            ZStack(alignment: .topLeading) {
                ForEach(0..<max(3, hearts.count), id: \.self) { i in
                    slot(i, frame: i < slots.count ? slots[i] : slots[slots.count - 1].offsetBy(dx: CGFloat(i - 2) * 36.1 * m.s, dy: 0),
                         now: now)
                }
            }
        }
        .overlay(alignment: .topLeading) {
            // `hud.hearts` (value = full hearts) as its own leaf: a value on a container would leak into every heart
            Color.clear.frame(width: 1, height: 1)
                .accessibilityElement()
                .accessibilityIdentifier("hud.hearts")
                .accessibilityValue(Text(verbatim: "\(hearts.filter { $0 == .full }.count)"))
                .allowsHitTesting(false)
                .position(x: slots.first?.midX ?? 0, y: slots.first?.midY ?? 0)
        }
        .onChange(of: hearts) { old, new in noteChange(old, new) }
    }

    @ViewBuilder private func slot(_ i: Int, frame: CGRect, now: Double) -> some View {
        let state = i < hearts.count ? hearts[i] : .empty
        ZStack(alignment: .topLeading) {
            if let scale = shownScale(i, state: state, now: now) {
                let c = ArtInk.canvas(.heartHUD, ink: frame)
                ArtImage(art: .heartHUD)
                    .frame(width: c.width, height: c.height)
                    .scaleEffect(CGFloat(scale), anchor: .center)          // about the heart's own centre (then placed)
                    .position(x: c.midX, y: c.midY)
            } else {
                InkImage(art: .heartHUDLost, ink: frame)
            }
            if let c = breaks[i] {
                let tau = app.clock.sequenceTime("heartBreak", now - c)
                if tau >= 0 && tau < motion.heartBreakEnd {
                    HeartHalf(left: true, frame: frame, tau: tau, motion: motion, s: m.s)
                    HeartHalf(left: false, frame: frame, tau: tau, motion: motion, s: m.s)
                }
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("hud.heart.\(i + 1)")
        .accessibilityValue(Text(verbatim: state == .full ? "full" : "lost"))
    }

    /// The full heart's scale, or nil when the slot shows the recess.
    private func shownScale(_ i: Int, state: HeartSlotVM, now: Double) -> Double? {
        guard state == .full else { return nil }
        if breaks[i] != nil { return nil }
        if let introT { return motion.heartScale(i, introT) }
        if let r = refillAt { return motion.refillScale(i, now - r) }
        return 1
    }

    private func noteChange(_ old: [HeartSlotVM], _ new: [HeartSlotVM]) {
        guard introT == nil else { return }
        let now = app.clock.gameTime()
        var broke = false
        for i in 0..<min(old.count, new.count) where old[i] == .full && new[i] != .full {
            breaks[i] = now
            broke = true
            Log.mark("hud", "heart \(i + 1) breaks")
        }
        let gained = zip(old, new).filter { $0.0 != .full && $0.1 == .full }.count
        if gained >= 2 {
            refillAt = now
            Log.mark("hud", "hearts refill pop (\(gained))")
            let end = motion.refillEnd
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: UInt64((end + 0.05) / max(app.clock.baseTimeScale, 0.01) * 1_000_000_000))
                refillAt = nil
            }
        }
        if broke {
            let end = motion.heartBreakEnd
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: UInt64((end + 0.05) / max(app.clock.baseTimeScale, 0.01) * 1_000_000_000))
                while app.clock.isFrozen { try? await Task.sleep(nanoseconds: 100_000_000) }
                breaks = breaks.filter { app.clock.gameTime() - $0.value < end }
            }
        }
    }

    /// The three slots' measured frames on the live screen (top-anchored).
    static func frames(_ t: Tokens, _ m: ShellMetrics) -> [CGRect] {
        [t.rect("hud.heart1", CGRect(201.5, 82.1, 28.7, 24.4), .top, m),
         t.rect("hud.heart2", CGRect(237.5, 82.1, 28.7, 24.4), .top, m),
         t.rect("hud.heart3", CGRect(273.6, 82.1, 28.4, 24.4), .top, m)]
    }
}

/// One half of the breaking heart (`heartHUDHalves` masked by its crack line), moved by the break curve.
private struct HeartHalf: View {
    let left: Bool
    let frame: CGRect
    let tau: Double
    let motion: HUDMotion
    let s: CGFloat

    var body: some View {
        let h = motion.heartHalf(tau, side: left ? -1 : 1)
        let canvas = ArtInk.canvas(.heartHUDHalves, ink: frame)
        ArtImage(art: .heartHUDHalves)
            .frame(width: canvas.width, height: canvas.height)
            .mask(HeartCrackMask(left: left))
            .rotationEffect(.degrees(h.degrees), anchor: left ? .bottomTrailing : .bottomLeading)
            .offset(x: CGFloat(h.dx) * s, y: CGFloat(h.dy) * s)
            .opacity(h.opacity)
            .position(x: canvas.midX, y: canvas.midY)
    }
}

/// The left or right part of the heart along the crack of `heartHUDHalves` (the gap's centre line, measured on the @3x file:
/// x fractions of the 93 px canvas per y fraction of its 81 px).
struct HeartCrackMask: Shape {
    let left: Bool
    static let crack: [(Double, Double)] = [(0.495, 0.0), (0.495, 0.074), (0.478, 0.111), (0.468, 0.148), (0.457, 0.185),
                                            (0.441, 0.222), (0.446, 0.259), (0.468, 0.296), (0.495, 0.333), (0.511, 0.370),
                                            (0.532, 0.407), (0.511, 0.444), (0.489, 0.481), (0.473, 0.519), (0.452, 0.556),
                                            (0.452, 0.593), (0.478, 0.630), (0.500, 0.667), (0.516, 0.704), (0.532, 0.741),
                                            (0.527, 0.778), (0.516, 0.815), (0.516, 0.852), (0.505, 0.889), (0.505, 0.926),
                                            (0.500, 1.0)]

    func path(in r: CGRect) -> Path {
        var p = Path()
        let pts = Self.crack.map { CGPoint(x: r.minX + CGFloat($0.0) * r.width, y: r.minY + CGFloat($0.1) * r.height) }
        let edge = left ? r.minX : r.maxX
        p.move(to: CGPoint(x: edge, y: r.minY))
        for q in pts { p.addLine(to: q) }
        p.addLine(to: CGPoint(x: edge, y: r.maxY))
        p.closeSubpath()
        return p
    }
}
