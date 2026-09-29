import SwiftUI
import PathCore

// SHELL S3 — B1 EVENTS-P (events.md §4.2, §6.1; ruling 38: "Claw / Balloon alternate weekly on the top bar"). The ladder slot's
// bar in an Up & Away week: the Treasure Climb bar's frame, fill, value text, reward end and countdown chip (ClawBar.swift),
// with Up & Away's token (R8's `eventBadgeBalloon` rig, A4: its balloon bobs) at the left end and its numbers — "streak/goal" (wins in a row
// toward the next platform), the goal platform's reward while it is unpaid (a check once paid), the week's countdown. The
// multiplier flame keeps hanging from the token: the win-streak multiplier (Hot Streak) runs in every week. Tap → the Up &
// Away page. The NEW ribbon (until the page is opened this week) is the rotation's (EventAnnounce); the chip stays blue to the
// end and reads mm:ss in the last hour (FIX-2 B, v582).
// Also here: the NEW ribbon and the ×2 gem (Double Event Week) — code-drawn chrome, no bitmaps (events.md §7.1 "rotation").

struct BalloonBar: View {
    let balloon: Events.BalloonStatus
    let multiplier: Int
    let now: SocialTime
    var isNew = false
    /// B1b (v582 PH-0a): the ENDED week's bar, held until its page is opened (final numbers, the chip reads "Finished").
    var finished = false
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let bar = t.frame("home.clawBar", ClawBar.frame)
        let fillFrom = CGFloat(t.number("home.clawBar.fillFromX", 66.7))
        let fillTo = CGFloat(t.number("home.clawBar.fillToX", 330.0))
        let goal = balloon.goal
        let k = goal.map { min(1, max(0, CGFloat(balloon.streak) / CGFloat(max(1, $0)))) } ?? 1
        let value = goal.map { "\(balloon.streak)/\($0)" } ?? "\(balloon.streak)"
        ZStack(alignment: .topLeading) {
            GameButton(id: "home.balloon", label: "Up & Away", value: "\(value) x\(multiplier)",
                       action: { app.router.go(.event(.balloonRise)) }) {
                ZStack(alignment: .topLeading) {
                    ClawBarFrame(t: t).placed(CGRect(x: 0, y: 0, width: bar.width, height: bar.height))
                    if k > 0 {
                        // the home-return beat of a counted win: the fill grows to the new count (0.45 s) — v582 moves the
                        // balloon on its page and on the win strip; the bar only follows (no token flight, DECISION)
                        ClawBarFill(t: t)
                            .frame(width: max(14, (fillTo - fillFrom) * k), height: 24.7)
                            .position(x: fillFrom - bar.minX + max(14, (fillTo - fillFrom) * k) / 2, y: 129.45 - bar.minY)
                            .animation(.easeOut(duration: 0.45), value: k)
                    }
                    ClawValueText(text: value, t: t, origin: bar.origin)
                    ClawRewardIcon(reward: balloon.nextReward, complete: balloon.nextReward == nil, t: t, origin: bar.origin)
                }
                .frame(width: bar.width, height: bar.height + 4, alignment: .topLeading)
                .scaleEffect(m.s, anchor: .topLeading)
                .frame(width: bar.width * m.s, height: (bar.height + 4) * m.s, alignment: .topLeading)
            }
            .placed(m.rect(CGRect(x: bar.minX, y: bar.minY, width: bar.width, height: bar.height + 4), .top))
            .anchor(.custom("home.balloonBar"))
            UpAwayToken()
                .placed(m.rect(t.frame("home.clawHexArt", CGRect(29.0, 107.8, 40, 40)).insetBy(dx: -3, dy: -3), .top))
                .allowsHitTesting(false)
            MultiplierFlame(multiplier: multiplier, t: t)
                .placed(m.rect(t.frame("home.clawMultBadgeArt", CGRect(46.0, 136.0, 50.0, 52.0)), .top))
                .allowsHitTesting(false)
                .accessibilityElement()
                .accessibilityIdentifier("home.balloon.multiplier")
                .accessibilityValue(Text(verbatim: "x\(multiplier)"))
            CountdownChip(seconds: Double(balloon.endsAt.seconds - now.seconds), t: t, id: "home.balloon.timer",
                          finished: finished, live: (balloon.endsAt, now))
                .placed(m.rect(t.frame("home.clawTimerChipBox", CGRect(155.0, 145.4, 80.0, 25.7)), .top))
                .allowsHitTesting(false)
            if isNew { NewRibbon().placed(m.rect(CGRect(47, 98, 40, 18), .top)).allowsHitTesting(false) }
        }
    }
}

/// A4 (R8 "upaway.badge"): the bar's token as its rig (body + balloon), the balloon bobbing ±1 pt on a 4 s sine (v582 PH-0b
/// R7; ui.json puppet.badge_upaway_rig, render server). Without the rig: the flat file (or DEBUG's placeholder).
private struct UpAwayToken: View {
    static let rig = "badge_upaway_rig"
    @Environment(AppModel.self) private var app

    var body: some View {
        if let rig = PuppetCache.rig(Self.rig) {
            let freeze = app.clock.freezeAt.flatMap { $0.sequence == "puppets" ? $0.t : nil }
            BadgePuppet(rig: rig, motion: PuppetMotion(app.tuning.ui.file, rig: Self.rig), clock: app.clock,
                        animate: !app.args.capture || freeze != nil, freezeAt: freeze)
                .accessibilityHidden(true)
        } else {
            UpAwayArtImage(id: UpAwayArt.badge)
        }
    }
}

/// "NEW" (T1 event.new): a red capsule, bold 11 pt white, wiggling 6° every 6 s (events.md §6.1).
struct NewRibbon: View {
    enum Phase: CaseIterable { case rest, left, right, back }
    var body: some View {
        let st = GameTextStyle.s2(11, -0.2, [0xFFFFFF], outline: 0x7A0A00, 1.0, drop: 0.6)
        ZStack {
            Capsule().fill(Color(hex: 0x7A0A00)).offset(y: 1.2)
            Capsule().fill(LinearGradient(colors: [Color(hex: 0xF37357), Color(hex: 0xD93E2A)], startPoint: .top, endPoint: .bottom))
            GameText("NEW", style: st, maxWidth: 34)
        }
        .frame(width: 40, height: 18)
        .phaseAnimator(Phase.allCases) { v, p in
            v.rotationEffect(.degrees(p == .left ? -6 : (p == .right ? 6 : 0)))
        } animation: { p in
            switch p {
            case .left, .right: return .easeInOut(duration: 0.12)
            case .back: return .easeOut(duration: 0.12)
            case .rest: return .linear(duration: 5.6)                  // the hold: one wiggle every 6 s
            }
        }
        .accessibilityElement()
        .accessibilityIdentifier("home.event.new")
    }
}

/// "×2" on both race badges in a Double Event Week (a gem, code-drawn). A5: R8's D1 CTA tokens — face #FFE08A → #FFB422,
/// outline #8A3F00, a thin brass rim #E3B04B (art/lanes/events-d1.handoff.json rotation_chrome).
struct DoubleGem: View {
    var body: some View {
        let st = GameTextStyle.s2(13, -0.4, [0xFFFFFF], outline: 0x8A3F00, 1.1, drop: 0.7)
        ZStack {
            DiamondShape().fill(Color(hex: 0x8A3F00)).offset(y: 1.2)
            DiamondShape().fill(LinearGradient(colors: [Color(hex: 0xFFE08A), Color(hex: 0xFFB422)], startPoint: .top, endPoint: .bottom))
            DiamondShape().stroke(Color(hex: 0xE3B04B), lineWidth: 0.8).padding(0.4)
            GameText(verbatim: "×2", style: st, maxWidth: 24)
        }
        .frame(width: 30, height: 26)
        .accessibilityElement()
        .accessibilityIdentifier("home.event.double")
    }
}

private struct DiamondShape: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: r.midX, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX, y: r.midY))
        p.addLine(to: CGPoint(x: r.midX, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX, y: r.midY))
        p.closeSubpath()
        return p
    }
}
