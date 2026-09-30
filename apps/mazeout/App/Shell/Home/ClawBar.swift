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

/// The count-up the home-return queue drives (nil = show the live status).
@MainActor @Observable final class ClawBarDisplay {
    static let shared = ClawBarDisplay()
    var points: Int?
    var multiplier: Int?
    /// Game time of the last flash on the hex icon (A9) / the multiplier badge (B6).
    var iconFlash = 0
    var badgeFlash = 0
    func reset() { points = nil; multiplier = nil }
}

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

    static let frame = CGRect(19.3, 107.8, 354.6, 43.7)

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

/// The bar's capsule: a dark outline, the light-blue rim (#0060EB top → #00A9FA → #1D79E8 bottom), a socket ≈ 3 pt taller around
/// the hex token at the left end, and the navy track 117.1 → 141.8 starting under the hex (VERIFIED 202 columns x 45 / 280).
struct ClawBarFrame: View {                                    // B1: shared with BalloonBar
    let t: Tokens
    var body: some View {
        Rasterized("clawBarFrame4", overflow: 4) { size in
            let r = size.height / 2
            let rim = LinearGradient(stops: [.init(color: t.color("clawBar.rimTop", Skin.homeClawBarClawBarRimTop), location: 0),
                                             .init(color: t.color("clawBar.rimMid", Skin.homeClawBarClawBarRimMid), location: 0.14),
                                             .init(color: Color(hex: Skin.homeClawBarClawBarFrameRimStops2), location: 0.6),
                                             .init(color: t.color("clawBar.rimLow", Skin.homeClawBarClawBarRimLow), location: 1)],
                                     startPoint: .top, endPoint: .bottom)
            ZStack(alignment: .topLeading) {
                // the socket around the hex (x 21 → 76, from 2.8 pt above the bar)
                RoundedRectangle(cornerRadius: 19).fill(t.color("clawBar.outline", Skin.homeClawBarClawBarOutline))
                    .frame(width: 56, height: size.height + 3.4).offset(x: 1.7, y: -2.8)
                RoundedRectangle(cornerRadius: 18).fill(rim)
                    .frame(width: 54, height: size.height + 1.4).offset(x: 2.7, y: -1.8)
                RoundedRectangle(cornerRadius: r).fill(Color(hex: Skin.homeClawBarClawBarFrameFill))                 // the dark lower lip (to 152.8)
                    .frame(width: size.width, height: size.height).offset(y: 1.4)
                RoundedRectangle(cornerRadius: r).fill(t.color("clawBar.outline", Skin.homeClawBarClawBarOutline))
                    .frame(width: size.width, height: size.height)
                RoundedRectangle(cornerRadius: r - 1).fill(rim).padding(1)
                    .frame(width: size.width, height: size.height)
                RoundedRectangle(cornerRadius: 12.3)
                    .fill(LinearGradient(colors: t.colors("clawBar.track", [Skin.homeClawBarClawBarTrack0, Skin.homeClawBarClawBarTrack1]), startPoint: .top, endPoint: .bottom))
                    .frame(width: size.width - 38 - 6.3, height: 24.7)
                    .offset(x: 38, y: 9.3)
            }
            .frame(width: size.width, height: size.height, alignment: .topLeading)   // the taller socket must not re-centre it
        }
    }
}

/// The green progress fill (#2C9A0A edge, #9BF24C upper band, #4FE401 body; VERIFIED 202 column).
struct ClawBarFill: View {                                     // B1: shared with BalloonBar
    let t: Tokens
    var body: some View {
        Rasterized("clawBarFill") { _ in
            ZStack {
                RoundedRectangle(cornerRadius: 6.8).fill(t.color("clawBar.fillEdge", Skin.homeClawBarClawBarFillEdge))
                RoundedRectangle(cornerRadius: 6)
                    .fill(LinearGradient(stops: [.init(color: t.color("clawBar.fillHi", Skin.homeClawBarClawBarFillHi), location: 0),
                                                 .init(color: t.color("clawBar.fill", Skin.homeClawBarClawBarFill), location: 0.45),
                                                 .init(color: t.color("clawBar.fillLow", Skin.homeClawBarClawBarFillLow), location: 1)],
                                         startPoint: .top, endPoint: .bottom))
                    .padding(1.2)
            }
        }
    }
}

struct ClawValueText: View {                                   // B1: shared with BalloonBar
    let text: String
    let t: Tokens
    let origin: CGPoint
    var body: some View {
        let st = t.text("home.clawBar.value", .s2(21.7, 0.6, [Skin.homeClawBarHomeClawBarValue0], outline: Skin.homeClawBarHomeClawBarValueOutline, 1.0, drop: 1.0))
        let p = t.textPoint("home.clawBar.value", baseline: 136.7, centreX: 196.3)
        GameText(verbatim: text, style: st, maxWidth: 200)
            .at(p.x - origin.x, st.capCentre(baseline: p.baseline) - origin.y)
            .accessibilityHidden(true)
    }
}

/// The next reward at the bar's right end (VERIFIED 101 / 168 / 173 / 202 / 204): coin bowl + amount, ∞-heart + duration,
/// or a booster + "x1"; a green check when the ladder is complete.
struct ClawRewardIcon: View {                                  // B1: shared with BalloonBar
    let reward: Grant?
    let complete: Bool
    let t: Tokens
    let origin: CGPoint

    var body: some View {
        let box = t.frame("home.clawReward", CGRect(323.6, 108.4, 46.0, 48.4)).offsetBy(dx: -origin.x, dy: -origin.y)
        ZStack(alignment: .topLeading) {
            if complete {
                ArtImage(art: .iconCheck).placed(box.insetBy(dx: 4, dy: 6))
            } else if let g = reward {
                if g.coins > 0 {
                    ArtImage(art: .coinBowl).placed(CGRect(x: box.minX - 4.5, y: box.minY - 1.5, width: 55, height: 43))
                    amount(ShopFormat.amount(g.coins), outline: Skin.homeClawBarClawRewardIconOutline, x: box.midX, baseline: box.minY + 35.3, size: 12.2)
                } else if g.unlimitedLives > 0 {
                    ArtImage(art: .heartInfiniteSmall).placed(CGRect(x: box.minX - 1, y: box.minY - 0.5, width: 48, height: 44))
                    amount(ShopFormat.duration(g.unlimitedLives), outline: Skin.homeClawBarClawRewardIconOutlineV2, x: box.midX + 1, baseline: box.minY + 37.8, size: 15.6)
                } else if let (id, n) = g.boosters.first(where: { $0.value > 0 }) {
                    ArtImage(art: id == "freeze" ? .boosterFreeze : .boosterHint)
                        .placed(CGRect(x: box.midX - 16, y: box.minY + 1, width: 32, height: 36))
                    amount("x\(n)", outline: Skin.homeClawBarClawRewardIconOutlineV3, x: box.midX + 1, baseline: box.minY + 41, size: 13.5)
                }
            }
        }
        .accessibilityElement()
        .accessibilityIdentifier("home.claw.reward")
        .accessibilityValue(Text(verbatim: value))
    }

    private var value: String {
        guard !complete, let g = reward else { return complete ? "complete" : "none" }
        if g.coins > 0 { return "coins:\(g.coins)" }
        if g.unlimitedLives > 0 { return "lives:\(ShopFormat.duration(g.unlimitedLives))" }
        if let b = g.boosters.first(where: { $0.value > 0 }) { return "\(b.key):\(b.value)" }
        return "none"
    }

    private func amount(_ s: String, outline: UInt32, x: CGFloat, baseline: CGFloat, size: CGFloat) -> some View {
        let st = GameTextStyle.s2(size, 0, [Skin.homeClawBarClawRewardIconAmountSt0], outline: outline, max(1, size * 0.09), drop: size * 0.06)
        return GameText(verbatim: s, style: st, maxWidth: 46).at(x, st.capCentre(baseline: baseline))
    }
}

/// The Treasure Climb token `treasureToken` (A4: R8's D1 token, was the purple hex `iconHexArrow`); a white flash over it when the queue's token lands (A9, 0.12 s).
struct HexToken: View {
    var flash: Int = 0
    @State private var flashOpacity = 0.0
    var body: some View {
        ZStack {
            ArtImage(art: .treasureToken)
            Circle().fill(Color.white).opacity(flashOpacity).padding(6).blendMode(.screen)
        }
        .onChange(of: flash) { _, _ in
            flashOpacity = 1
            withAnimation(.linear(duration: 0.12)) { flashOpacity = 0 }
        }
    }
}

/// The multiplier "flame" hanging from the hex by a two-link chain (VERIFIED 202 x100 gold, 035 x5 orange, 026 x1): a teardrop
/// whose tip points up-right, a lighter core, the label "x100" (11.9 pt white, outline #800100).
struct MultiplierFlame: View {
    let multiplier: Int
    let t: Tokens

    var body: some View {
        let palette: [UInt32] = multiplier >= 100 ? [Skin.homeClawBarMultiplierFlamePalette0, Skin.homeClawBarMultiplierFlamePalette1, Skin.homeClawBarMultiplierFlamePalette2, Skin.homeClawBarMultiplierFlamePalette3]
            : multiplier > 1 ? [Skin.homeClawBarMultiplierFlame0, Skin.homeClawBarMultiplierFlame1, Skin.homeClawBarMultiplierFlame2, Skin.homeClawBarMultiplierFlame3] : [Skin.homeClawBarMultiplierFlame0V2, Skin.homeClawBarMultiplierFlame1V2, Skin.homeClawBarMultiplierFlame2V2, Skin.homeClawBarMultiplierFlame3V2]
        let key = palette.map { String(format: "%06X", $0) }.joined()
        ZStack(alignment: .topLeading) {
            Rasterized("flame|\(key)", overflow: 2) { size in
                FlameArt(palette: palette, gold: multiplier >= 100).frame(width: size.width, height: size.height)
            }
            let st = t.text("home.clawMultBadge.mult", .s2(multiplier >= 100 ? 11.9 : 15.0, -0.2, [Skin.homeClawBarHomeClawMultBadgeMult0], outline: Skin.homeClawBarHomeClawMultBadgeMultOutline,
                                                            1.3, drop: 0.8))
            GameText(verbatim: "x\(multiplier)", style: st, maxWidth: 34)
                .at(24.8, st.capCentre(baseline: 34.4))
        }
        .frame(width: 50, height: 52, alignment: .topLeading)
    }
}

private struct FlameArt: View {
    let palette: [UInt32]
    let gold: Bool
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            // the teardrop (centre (24.8, 31.5), r 17.5) with its flame tip at the upper right
            let drop = Path { p in
                let c = CGPoint(x: w * 0.496, y: h * 0.606), r = w * 0.35
                p.addArc(center: c, radius: r, startAngle: .degrees(-60), endAngle: .degrees(200), clockwise: false)
                p.addQuadCurve(to: CGPoint(x: w * 0.60, y: h * 0.13), control: CGPoint(x: w * 0.30, y: h * 0.26))
                p.addQuadCurve(to: CGPoint(x: c.x + r * 0.5, y: c.y - r * 0.866), control: CGPoint(x: w * 0.74, y: h * 0.33))
                p.closeSubpath()
            }
            ZStack {
                // the chain from the hex: two grey links
                Ellipse().stroke(Color(hex: Skin.homeClawBarFlameArtStroke), lineWidth: 2.2).frame(width: 7, height: 11).rotationEffect(.degrees(-35))
                    .position(x: w * 0.40, y: h * 0.10)
                Ellipse().stroke(Color(hex: Skin.homeClawBarFlameArtStrokeV2), lineWidth: 2.0).frame(width: 7, height: 10).rotationEffect(.degrees(25))
                    .position(x: w * 0.50, y: h * 0.22)
                drop.fill(Color(hex: palette[3])).offset(y: 1.2)
                drop.fill(RadialGradient(colors: [Color(hex: palette[0]), Color(hex: palette[1]), Color(hex: palette[2])],
                                         center: UnitPoint(x: 0.5, y: 0.62), startRadius: 0, endRadius: w * 0.42))
                drop.stroke(Color(hex: palette[3]).opacity(0.8), lineWidth: 1)
                if gold {
                    ForEach(0..<3, id: \.self) { i in
                        TwinkleStar().fill(Color(hex: Skin.homeClawBarFlameArtFill))
                            .frame(width: [8.0, 6.0, 7.0][i], height: [8.0, 6.0, 7.0][i])
                            .position(x: w * [0.9, 0.12, 0.84][i], y: h * [0.30, 0.55, 0.92][i])
                    }
                }
            }
        }
    }
}

/// An event countdown. FIX-2 lane B (L28 / F-10 — the phone wins, v582 PH-0a build/p/PH0a/before-reset.png): ONE formatter for
/// every event countdown (the home chip and badges, the event pages, the win strips, the race bars): ≥ 1 day "3d 5h", ≥ 1 hour
/// "5h 13m" — always with its minutes ("19h 0m", as the win strip always read; was "19h" here), under an hour "mm:ss"
/// ("09:34", two-digit minutes like the lives pill; was "9m"). Floored. The "mm:ss" is digits and a colon in every language.
enum Countdown {
    /// The last hour: the text reads mm:ss and home ticks it every second (`LiveCountdown`).
    static let lastHour: Double = 3600

    static func text(_ seconds: Double) -> String {
        let s = max(0, Int(seconds.rounded(.down)))
        let d = s / 86_400, h = (s % 86_400) / 3600, m = (s % 3600) / 60
        if d > 0 { return String(localized: "\(d)d \(h)h") }
        if h > 0 { return String(localized: "\(h)h \(m)m") }
        return String(format: "%02d:%02d", m, s % 60)
    }
}

/// FIX-2 lane B (L28): an event countdown, live. The social clock counts whole seconds, so a countdown's text can only change
/// at a whole second of the wall clock: the view re-reads the clock on its own small TimelineView exactly there
/// (`CountdownSchedule`: once a second, on the second — not 4 polls a second landing up to 250 ms late), and its content is
/// equatable, so it re-renders only when the TEXT changes and nothing around it (bars, badges, rigs, the page) re-renders.
/// Where it runs (`CountdownClock`):
///  - `.home` (the home bars and badges): at or above an hour the event layer's 20 s tick is enough (the text has minute
///    resolution); in the LAST HOUR (+ one layer tick before it, so "1h 0m" → "59:59" lands on its second) it ticks. Parked
///    under a level (`HomeLive.active` false) the timeline pauses and reads the date home last drew (it never records one:
///    the layer's own parked-date logic is untouched).
///  - `.homeTab(tab)` (a chip on a home tab page, the Leaderboard's Weekly Cup): as `.home`, and paused while that tab page
///    is not drawn (`HomeTabStrip.shown`), so a hidden tab never re-renders.
///  - `.page` (the event pages, their offers and the win panel's strips — FIX-2 B review: they drew the time their page
///    last rendered, so "09:32" stood still, or moved in 5 s steps with the social refresh): always ticks, from the store's
///    clock (the minute values above an hour turn on time as well); a hidden warm-up copy (`socPrewarm`) draws once, static.
struct LiveCountdown<Content: View>: View {
    let ends: SocialTime
    /// The caller's clock reading (home: the event layer's tick; a page: its body time) — the static draw.
    let now: SocialTime
    var clock: CountdownClock = .home
    @ViewBuilder let content: (Double) -> Content
    @Environment(AppModel.self) private var app
    @Environment(\.socPrewarm) private var prewarm

    static func ticks(_ seconds: Double) -> Bool { seconds > -1 && seconds < Countdown.lastHour + 20 }

    var body: some View {
        let left = Double(ends.seconds - now.seconds)
        switch clock {
        case .home, .homeTab:
            if Self.ticks(left) {
                let active = HomeLive.shared.active
                let shown: Bool = {
                    if case .homeTab(let tab) = clock { return HomeTabStrip.shared.shown.contains(tab) }
                    return true
                }()
                TimelineView(CountdownSchedule(clock: app.clock, paused: !(active && shown))) { ctx in
                    let date = active ? ctx.date : (HomeLive.shared.eventsDrawnAt ?? ctx.date)
                    let t = EconomyClock.peekSocial(HomeLive.read(app), wall: app.clock.wallClock(date))
                    LiveCountdownFrame(seconds: Double(ends.seconds - t.seconds), content: content).equatable()
                }
            } else {
                content(left)
            }
        case .page:
            if prewarm || left <= -1 {
                content(left)
            } else {
                TimelineView(CountdownSchedule(clock: app.clock, paused: false)) { ctx in
                    let t = EconomyClock.peekSocial(app.store.state, wall: app.clock.wallClock(ctx.date))
                    LiveCountdownFrame(seconds: Double(ends.seconds - t.seconds), content: content).equatable()
                }
            }
        }
    }
}

/// FIX-2 lane B (review of L28): where a `LiveCountdown` lives (its clock and when it pauses).
enum CountdownClock: Equatable { case home, homeTab(HomeTab), page }

/// FIX-2 lane B (review of L28): the moments a countdown's text can change — the wall clock's whole seconds (the social clock
/// is `max(⌊wall⌋, highWater)` and every event end is a whole second). `MotionClock.wallClock` maps a real date linearly (the
/// real time, or `-pc.now` running at `-pc.clockRate`, + `-pc.clockOffset`): `anchor` is a real date 3 ms after the wall
/// clock's next whole second (so ⌊wall⌋ there is already the new second) and `period` the real length of one wall second.
/// A stopped clock (capture mode, `-pc.clockRate 0`) or a paused countdown gives its start only: one draw, no ticks.
struct CountdownSchedule: TimelineSchedule {
    let anchor: Date
    /// Real seconds per wall second; 0 = the clock stands.
    let period: TimeInterval
    let paused: Bool

    @MainActor init(clock: MotionClock, paused: Bool) {
        let real = Date()
        let w0 = clock.wallClock(real).timeIntervalSince1970
        let rate = clock.wallClock(real.addingTimeInterval(1)).timeIntervalSince1970 - w0
        self.init(real: real, wall: w0, rate: rate, paused: paused)
    }

    /// `wall` = the wall clock at the real date `real` (seconds since 1970), `rate` = wall seconds per real second.
    init(real: Date, wall: Double, rate: Double, paused: Bool) {
        self.paused = paused
        guard rate > 1e-6 else { period = 0; anchor = real; return }
        period = 1 / rate
        anchor = real.addingTimeInterval((wall.rounded(.down) + 1 - wall) * period + 0.003)
    }

    func entries(from start: Date, mode: TimelineScheduleMode) -> AnyIterator<Date> {
        var first: Date? = start
        guard !paused, period > 0 else { return AnyIterator { defer { first = nil }; return first } }
        var next = anchor.addingTimeInterval(((start.timeIntervalSince(anchor) / period).rounded(.down) + 1) * period)
        return AnyIterator {
            if let f = first { first = nil; return f }
            defer { next = next.addingTimeInterval(period) }
            return next
        }
    }
}

/// Re-renders only when the countdown's TEXT changes (the timeline checks once a second, on the second).
private struct LiveCountdownFrame<Content: View>: View, Equatable {
    let seconds: Double
    let content: (Double) -> Content
    static func == (a: Self, b: Self) -> Bool { Countdown.text(a.seconds) == Countdown.text(b.seconds) }
    var body: some View { content(seconds) }
}

/// The blue HUD-style countdown chip (SPEC-ui §1.6.15 home variant: #0095FD, white text outlined #0F2C80 1.0) with the small
/// stopwatch over its left end. FIX-2 lane B (L28, the phone wins): the chip stays BLUE in the event's last day and hour, with
/// no pulse (v582 PH-0a: "09:34" on the blue chip; B1's red face + "Last day" pulse are gone), and ticks mm:ss in the last hour.
struct CountdownChip: View {
    let seconds: Double
    let t: Tokens
    let id: String
    /// B1b (v582 PH-0a, VERIFIED): the event ended and waits for its result to be opened — the same blue chip reads "Finished".
    var finished = false
    /// FIX-2 B: the event's end and the layer's tick — the last hour then ticks every second (`LiveCountdown`); nil = static.
    var live: (ends: SocialTime, now: SocialTime)?
    /// The chip's text style (B1b: shared with the Finished prewarm, so both hit the same GameText raster).
    static func textStyle(_ t: Tokens) -> GameTextStyle {
        t.text("home.clawTimerChip.timer", .s2(16.3, -0.3, [Skin.homeClawBarHomeClawTimerChipTimer0], outline: Skin.homeClawBarHomeClawTimerChipTimerOutline, 1.0, drop: 0.9))
    }
    /// B1b: the width "Finished" is fitted to (v582's ≈ 47 pt, PH-0a).
    static func finishedMaxWidth(_ t: Tokens) -> CGFloat { CGFloat(t.number("home.clawTimerChip.finishedMaxWidth", 47)) }

    var body: some View {
        if !finished, let live {
            LiveCountdown(ends: live.ends, now: live.now) { s in chip(s) }
        } else {
            chip(seconds)
        }
    }

    private func chip(_ seconds: Double) -> some View {
        let text = finished ? EventWord.finished : Countdown.text(seconds)
        let st = Self.textStyle(t)
        let face: [Color] = [Color(hex: Skin.homeClawBarCountdownChipChipFace0), t.color("clawChip.face", Skin.homeClawBarClawChipFace), Color(hex: Skin.homeClawBarCountdownChipChipFace2)]
        return ZStack(alignment: .topLeading) {
            Rasterized("clawChip|false") { _ in
                ZStack {
                    RoundedRectangle(cornerRadius: 5.5).fill(Color(hex: Skin.homeClawBarCountdownChipChipFill))
                    RoundedRectangle(cornerRadius: 4.8)
                        .fill(LinearGradient(colors: face, startPoint: .top, endPoint: .bottom))
                        .padding(0.9)
                }
            }
            .placed(CGRect(x: 17.4, y: 4.4, width: 61.1, height: 17.8))
            ArtImage(art: .iconStopwatchSmall).placed(CGRect(x: 0, y: 0, width: 24, height: 25.7))
            // B1b: "Finished" fitted inside the chip's face like v582's (≈ 47 pt wide on the 1178 px PH-0a shot)
            GlyphRunText(text: text, style: st, maxWidth: finished ? Self.finishedMaxWidth(t) : 54)
                .at(48.3, st.capCentre(baseline: 18.5))
        }
        .frame(width: 80, height: 25.7, alignment: .topLeading)
        .accessibilityElement()
        .accessibilityIdentifier(id)
        .accessibilityValue(Text(verbatim: finished ? "finished" : text))
    }
}

/// FIX-2 lane B (B1b-r3): the ended-event word. v582 shows "Finished" on an ended event's badge, chip and page; the lives pill's
/// "Finished" (a life arrived) is another key, so a language can say "ended" here and "ready" / "full" there
/// (strings.tsv `event.finished`, English in keys.tsv; ja 終了, ko 종료, zh-Hans 已结束, es Terminó, pt-BR Acabou …).
enum EventWord {
    static var finished: String { String(localized: "event.finished", defaultValue: "Finished") }
}

/// A four-point twinkle star filling its frame (the Sparkles shape).
struct TwinkleStar: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path(Sparkles.starPath(size: min(r.width, r.height)))
        p = p.offsetBy(dx: r.midX, dy: r.midY)
        return p
    }
}
