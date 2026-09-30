import SwiftUI
import PathCore

// The home's event-bar chrome (kit decoupling step, docs/ROADMAP.md): the ladder bar's frame, fill, value text and reward end,
// the Treasure Climb token and multiplier flame, the home-return count-up state, and the NEW / ×2 badge marks. The Treasure
// Climb bar (ClawBar.swift, claw-challenge), Up & Away's bar (BalloonBar.swift, balloon-rise), the event badges and the home's
// payout sequence all draw them, so they live with the home (they were in ClawBar.swift / BalloonBar.swift). Moved as they
// were; the bar's reference frame is `ClawBarFrame.bar` (was `ClawBar.frame`).

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

/// The bar's capsule: a dark outline, the light-blue rim (#0060EB top → #00A9FA → #1D79E8 bottom), a socket ≈ 3 pt taller around
/// the hex token at the left end, and the navy track 117.1 → 141.8 starting under the hex (VERIFIED 202 columns x 45 / 280).
struct ClawBarFrame: View {                                    // B1: shared with BalloonBar
    /// The bar's reference frame (ui.json `home.clawBar`'s default): the Treasure Climb and Up & Away bars sit there.
    static let bar = CGRect(19.3, 107.8, 354.6, 43.7)
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
                    ArtImage(art: .rewardCoinBowl).placed(CGRect(x: box.minX - 4.5, y: box.minY - 1.5, width: 55, height: 43))
                    amount(ShopFormat.amount(g.coins), outline: Skin.homeClawBarClawRewardIconOutline, x: box.midX, baseline: box.minY + 35.3, size: 12.2)
                } else if g.unlimitedLives > 0 {
                    ArtImage(art: .livesUnlimitedSmall).placed(CGRect(x: box.minX - 1, y: box.minY - 0.5, width: 48, height: 44))
                    amount(ShopFormat.duration(g.unlimitedLives), outline: Skin.homeClawBarClawRewardIconOutlineV2, x: box.midX + 1, baseline: box.minY + 37.8, size: 15.6)
                } else if let (id, n) = g.boosters.first(where: { $0.value > 0 }) {
                    ArtImage(art: id == "freeze" ? .boosterFreezeIcon : .boosterHintIcon)
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
            ArtImage(art: .eventClawChallengeToken)
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

/// A four-point twinkle star filling its frame (the Sparkles shape).
struct TwinkleStar: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path(Sparkles.starPath(size: min(r.width, r.height)))
        p = p.offsetBy(dx: r.midX, dy: r.midY)
        return p
    }
}

/// "NEW" (T1 event.new): a red capsule, bold 11 pt white, wiggling 6° every 6 s (events.md §6.1).
struct NewRibbon: View {
    enum Phase: CaseIterable { case rest, left, right, back }
    var body: some View {
        let st = GameTextStyle.s2(11, -0.2, [Skin.homeBalloonBarNewRibbonSt0], outline: Skin.homeBalloonBarNewRibbonStOutline, 1.0, drop: 0.6)
        ZStack {
            Capsule().fill(Color(hex: Skin.homeBalloonBarNewRibbonFill)).offset(y: 1.2)
            Capsule().fill(LinearGradient(colors: [Color(hex: Skin.homeBalloonBarNewRibbonColors0), Color(hex: Skin.homeBalloonBarNewRibbonColors1)], startPoint: .top, endPoint: .bottom))
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
        let st = GameTextStyle.s2(13, -0.4, [Skin.homeBalloonBarDoubleGemSt0], outline: Skin.homeBalloonBarDoubleGemStOutline, 1.1, drop: 0.7)
        ZStack {
            DiamondShape().fill(Color(hex: Skin.homeBalloonBarDoubleGemFill)).offset(y: 1.2)
            DiamondShape().fill(LinearGradient(colors: [Color(hex: Skin.homeBalloonBarDoubleGemColors0), Color(hex: Skin.homeBalloonBarDoubleGemColors1)], startPoint: .top, endPoint: .bottom))
            DiamondShape().stroke(Color(hex: Skin.homeBalloonBarDoubleGemStroke), lineWidth: 0.8).padding(0.4)
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
