import SwiftUI
import PathCore

// SHELL S3 (SPEC-architecture §6.4 item 5; SPEC-ui §2.2.3; uim `home.clawBar*`; VERIFIED 026 / 035 / 051 / 101 / 168 / 173 / 202 /
// meta-001). The Claw Challenge bar under the top bar, shown from the Claw unlock (L33) while the week's ladder runs:
//   the frame (19.3 · 107.8 · 354.6 · 43.7: a light-blue capsule rim #0060EB → #00A9FA → #1D79E8 around a navy track #0F2C80 →
//   #041A75), the green fill (#77EE28 family, rr 6.8) growing from x 66.7, "n/target" centred on the track (21.7 pt white,
//   outline #061E79 1.0), the token `treasureToken` (R8 D1; was the purple hex `iconHexArrow`) on the left end, the next reward at the right end (coin bowl +
//   amount / ∞-heart + duration / booster + "x1"), the multiplier flame hanging from the hex on a chain (x1 red-orange, x5-x25
//   orange, x100 gold), and the blue countdown chip under the bar ("3d 5h", with the small stopwatch overlapping its left end).
// The numbers come from C3's `Events.status` (read-only). During the home-return queue (PayoutSequence segment A) the bar shows
// `ClawBarDisplay`'s count-up value instead, with the fill animating 0.057 s per step (SPEC-motion-audio §8.5). Tap → the Claw
// Challenge page (SOC2's `.event(.claw)`).
// Kit decoupling step: this file is the claw-challenge component's (the bar only). The bar chrome it shares with Up & Away's bar,
// the payout and the badges is the home's (EventBarChrome.swift); the countdowns are social-ui's (Social/Countdown.swift).

struct ClawBar: View {
    let claw: Events.ClawStatus
    let multiplier: Int
    let now: SocialTime
    /// B1: the NEW ribbon on the token until the Treasure Climb page is opened this week.
    var isNew = false
    /// B1b (v582 PH-0a): the ENDED week's bar, held until its page is opened — its final numbers stay, the chip reads
    /// "Finished" (no count-up of the home-return queue lands on it: a counted win moves the player on first).
    var finished = false
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    static let frame = ClawBarFrame.bar

    var body: some View {
        let t = app.tuning.ui.tokens
        let display = ClawBarDisplay.shared
        let points = finished ? claw.points : (display.points ?? claw.points)
        let mult = display.multiplier ?? multiplier
        let bar = t.frame("home.clawBar", Self.frame)
        let fillFrom = CGFloat(t.number("home.clawBar.fillFromX", 66.7))
        let fillTo = CGFloat(t.number("home.clawBar.fillToX", 330.0))
        let k = claw.target > 0 ? min(1, max(0, CGFloat(points) / CGFloat(claw.target))) : 0
        ZStack(alignment: .topLeading) {
            GameButton(id: "home.claw", label: "Treasure Climb", value: "\(points)/\(claw.target) x\(mult)",
                       action: { app.router.go(.event(.claw)) }) {
                ZStack(alignment: .topLeading) {
                    ClawBarFrame(t: t).placed(local(bar, bar))
                    // the green fill: a rounded bar from the hex to the reward, its width = the progress
                    if k > 0 {
                        ClawBarFill(t: t)
                            .frame(width: max(14, (fillTo - fillFrom) * k), height: 24.7)
                            .animation(display.points == nil ? nil : .linear(duration: 0.057), value: k)
                            .position(x: fillFrom - bar.minX + max(14, (fillTo - fillFrom) * k) / 2, y: 129.45 - bar.minY)
                    }
                    ClawValueText(text: "\(points)/\(claw.target)", t: t, origin: bar.origin)
                    ClawRewardIcon(reward: claw.nextReward, complete: claw.complete, t: t, origin: bar.origin)
                }
                .frame(width: bar.width, height: bar.height + 4, alignment: .topLeading)
                .scaleEffect(m.s, anchor: .topLeading)
                .frame(width: bar.width * m.s, height: (bar.height + 4) * m.s, alignment: .topLeading)
            }
            .placed(m.rect(CGRect(x: bar.minX, y: bar.minY, width: bar.width, height: bar.height + 4), .top))
            .anchor(.custom("home.clawBar"))
            // the hex token (it overhangs the frame) + the chain and the multiplier flame
            HexToken(flash: display.iconFlash).placed(m.rect(t.frame("home.clawHexArt", CGRect(29.0, 107.8, 40, 40)), .top))
                .allowsHitTesting(false)
                .anchor(.custom("home.clawHex"))
            if isNew { NewRibbon().placed(m.rect(CGRect(47, 98, 40, 18), .top)).allowsHitTesting(false) }   // B1
            MultiplierFlame(multiplier: mult, t: t)
                .placed(m.rect(t.frame("home.clawMultBadgeArt", CGRect(46.0, 136.0, 50.0, 52.0)), .top))
                .allowsHitTesting(false)
                .accessibilityElement()
                .accessibilityIdentifier("home.claw.multiplier")
                .accessibilityValue(Text(verbatim: "x\(mult)"))
                .anchor(.custom("home.clawMultiplier"))
            CountdownChip(seconds: Double(claw.endsAt.seconds - now.seconds), t: t, id: "home.claw.timer", finished: finished,
                          live: (claw.endsAt, now))
                .placed(m.rect(t.frame("home.clawTimerChipBox", CGRect(155.0, 145.4, 80.0, 25.7)), .top))
                .allowsHitTesting(false)
        }
    }

    private func local(_ r: CGRect, _ bar: CGRect) -> CGRect { r.offsetBy(dx: -bar.minX, dy: -bar.minY) }
}
