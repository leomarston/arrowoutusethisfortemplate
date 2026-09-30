import SwiftUI
import PathCore

// SHELL S2 (SPEC-architecture §6.7; SPEC-ui §2.7.2; uim `win*`, VERIFIED 020 / 037 / 063 / 171 / 196; SPEC-motion-audio §5 rows
// 15-18, §6.1). The win panel, complete on its first frame over the 0.90 dim at W + 3.94:
//   panel   blue 10 · 176.8 · 373.3 · 465.1 (n 5.9); Hard red (field #CC0410, frame #9E0014); Super Hard purple (#8F01DE / #7306BA)
//   tag     Hard / Super Hard only: the "Hard Level" / "Super Hard" tag ribbon 76.7 · 100.1 · 240.2 · 56.7 behind the ribbon, a skull
//           each side (drawn in code: `iconSkull` is not in the MANIFEST and ☠ is not in PCDisplay, CONSISTENCY W-10)
//   ribbon  the level label ("Level 32"; "Level 1-4") at 60.1 · 149.8
//   content "Perfect!" (45.2 / −1.6, cream face, navy outline + a cyan ring, 4.2 drop) — always, hearts lost or not; "Rewards:";
//           the coin stack 141.1 · 366.6 · 120.1 · 99.1 on a radial glow with its twinkles and the amount "20" / "60" / "100" (56.5 /
//           −3.7) at its lower right; the framed green "Continue" 90.4 · 497.4 · 212.5 · 88.1; the X (361.3, 207.7)
//   under   the Streak Race strip (from L30) or, while a Rocket Race runs, the race bar — both slide up at P + 0.01;
//           B1: while Up & Away runs its strip takes the Streak Race strip's place (BalloonViews.swift)
// The coins are NOT counted up on the panel (they fly on home). Continue is silent: its release plays the button haptic only
// (SPEC-motion-audio §6.1); X = Continue (DECISION W-11). On its first frame the panel takes over the celebration's dim.

struct WinPanel: View {
    let summary: WinSummary
    let answer: PopupAnswer
    /// The invisible render behind Loading: no dim hand-over, no log.
    var prewarm = false
    /// FIX-2 A-R: the hidden copy drawn ahead of the real panel (RootView `PopupWarm`, W+2.6) is a warm copy too — its
    /// appearance handed the dim over 1.4 s early (the board full-bright until the real panel) and logged a second panel.
    @Environment(\.shellWarmCopy) private var warmCopy
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?

    var body: some View {
        let t = app.tuning.ui.tokens
        let tier = WinTier(summary.tag)
        let panel = summary.tag == .normal ? t.frame("win.panel", CGRect(10.0, 176.8, 373.3, 465.1))
                                           : t.frame("winHard.panel", CGRect(9.7, 177.2, 374.0, 464.7))
        let face = t.frame("win.continue", CGRect(90.4, 497.4, 212.5, 88.1))
        ZStack(alignment: .topLeading) {
            if summary.tag != .normal {
                TierTagRibbon(tag: summary.tag, frame: t.frame("winHard.tagRibbon", CGRect(76.7, 100.1, 240.2, 56.7)), t: t)
            }
            if summary.tag == .normal {
                PopupPanelFrame(n: t.superellipseN("win.panel", 5.92), t: t).placed(panel)
            } else {
                TierPanelFrame(tier: tier, t: t).placed(panel)
            }
            CoinGlow(tier: tier).placed(t.frame("win.glow", CGRect(40, 250, 313, 250))).allowsHitTesting(false)
            TokenText(id: "win.perfect.title", source: .copy("Perfect!"),
                      style: .s2(45.2, -1.62, [Skin.popupsWinPanelWinPanelStyle0, Skin.popupsWinPanelWinPanelStyle1, Skin.popupsWinPanelWinPanelStyle2], outline: tier.textOutline, 2.43, drop: 4.21),
                      baseline: 290.4, centreX: 196.8, maxWidth: 300, rings: [(tier.perfectEdge, 5.7), (tier.perfectRing, 5.0)])
            TokenText(id: "win.rewardsLabel.label", source: .copy("Rewards:"),
                      style: .s2(25.9, -1.52, [Skin.popupsWinPanelWinPanelStyle0V2], outline: tier.textOutline, 1.35, drop: 1.25),
                      baseline: 332.8, centreX: 199.5, maxWidth: 240)
            InkImage(art: .rewardCoins, ink: t.frame("win.coinsInk", CGRect(136.4, 363.3, 132.6, 105.2)))
            WinTwinkles(t: t)
            TokenText(id: "win.amountDigits.amt", source: .number("\(summary.reward)"),
                      style: .s2(56.5, -3.73, [Skin.popupsWinPanelWinPanelStyle0V2], outline: tier.textOutline, 2.6, drop: 1.8),
                      baseline: 471.1, centreX: 256.4)
                .accessibilityIdentifier("win.reward")
                .accessibilityValue(Text(verbatim: "\(summary.reward)"))
            ZStack(alignment: .topLeading) {
                OfferWell(n: 4.6, palette: tier.offerWell, t: t)
                    .placed(t.frame("win.continueFrame", face.insetBy(dx: -11.3, dy: -8.7)))
                GameButton(id: "win.continue", label: "Continue", clicks: false, action: { cont(PopupResult.primary) }) {
                    ZStack(alignment: .topLeading) {
                        ChromeButtonFace(colors: .green, n: t.superellipseN("win.continue", 5.0))
                        let ls = t.text("win.continue.label", .s2(38.9, 0.05, [Skin.popupsWinPanelWinContinueLabel0, Skin.popupsWinPanelWinContinueLabel1, Skin.popupsWinPanelWinContinueLabel2], outline: Skin.popupsWinPanelWinContinueLabelOutline, 1.74, drop: 1.8))
                        let lp = t.textPoint("win.continue.label", baseline: 551.2, centreX: 197.2)
                        GameText("Continue", style: ls, maxWidth: t.textMaxWidth("win.continue.label", 176))
                            .at(lp.x - face.minX, ls.capCentre(baseline: lp.baseline) - face.minY)
                    }
                    .frame(width: face.width, height: face.height, alignment: .topLeading)
                }
                .placed(face)
            }
            PopupTitle(title: PanelLabel.resource(summary.levels), frame: t.frame("win.ribbon", CGRect(60.1, 149.8, 274.2, 90.4)), t: t,
                       baselineFromTop: CGFloat(t.number("text.win.ribbon.title.baseline", 208.6)) - 149.8)
            PopupCloseButton(id: "win.close", t: t) { cont(PopupResult.close) }
                .overlay {
                    if summary.tag != .normal {
                        // Hard / Super Hard: the X's ring takes the panel's colour and covers the blue ring (VERIFIED 037 / 063:
                        // ring 55.8 across the 46.7 face). An overlay, so it never changes the button's layout size.
                        ZStack {
                            Circle().fill(Color(hex: tier.closeRing[2])).frame(width: 55.8, height: 55.8)
                            Circle().fill(LinearGradient(colors: tier.closeRing.map { Color(hex: $0) }, startPoint: .top, endPoint: .bottom))
                                .frame(width: 54.4, height: 54.4)
                        }
                        .mask(Circle().strokeBorder(lineWidth: 5.6).frame(width: 55.8, height: 55.8))
                        .allowsHitTesting(false)
                    }
                }
                .placed(t.frame("win.closeDisc", CGRect(338.8, 185.2, 45, 45)))
            under
        }
        .onAppear {
            guard !prewarm, !warmCopy else { return }
            shownAt = app.clock.gameTime()
            (app.fx as? FXOverlay)?.handOverCelebrationDim()
            Log.mark("win", "panel \(summary.tag.rawValue) \(summary.levels.map(String.init).joined(separator: "-")) reward \(summary.reward)")
        }
    }

    /// The strip under the panel: a slot the event components fill (`PanelStrips`; the first that draws wins — the Rocket Race
    /// bar while a race runs, else Up & Away's strip while it runs (B1: it replaces the Hot Streak strip, VERIFIED v582,
    /// balloon.md §5), else the Streak Race strip).
    @ViewBuilder private var under: some View {
        if let strip = PanelStrips.view(PanelStripContext(app: app, place: .win, level: summary.levels.last ?? 0,
                                                          outcomes: summary.outcomes, shownAt: shownAt)) {
            strip
        }
    }

    /// Continue / X: the button haptic only (no click, VERIFIED silent), then the answer.
    private func cont(_ r: PopupResult) {
        if let h = GameButtonFeedback.haptic(app) { app.haptics.play(h) }
        answer(r)
    }
}

/// The panel colours of a tier (VERIFIED 020 / 037 / 063).
struct WinTier: Equatable {
    let tag: LevelTag
    init(_ tag: LevelTag) { self.tag = tag }
    var key: String { tag.rawValue }
    var textOutline: UInt32 { tag == .normal ? Skin.popupsWinPanelWinTierTextOutlineNormal : (tag == .hard ? Skin.popupsWinPanelWinTierTextOutlineHard : Skin.popupsWinPanelWinTierTextOutlineNotHard) }
    var perfectRing: UInt32 { tag == .normal ? Skin.popupsWinPanelWinTierPerfectRingNormal : (tag == .hard ? Skin.popupsWinPanelWinTierPerfectRingHard : Skin.popupsWinPanelWinTierPerfectRingNotHard) }
    var perfectEdge: UInt32 { tag == .normal ? Skin.popupsWinPanelWinTierPerfectEdgeNormal : (tag == .hard ? Skin.popupsWinPanelWinTierPerfectEdgeHard : Skin.popupsWinPanelWinTierPerfectEdgeNotHard) }
    /// outline, bar (top, bottom), bumper, groove, field, rivet
    var frame: (outline: UInt32, bar: [UInt32], bumper: [UInt32], groove: UInt32, field: UInt32, rivet: UInt32) {
        switch tag {
        case .normal: return (Skin.popupsWinPanelWinTierFrameNormal, [Skin.popupsWinPanelWinTierFrameNormal0, Skin.popupsWinPanelWinTierFrameNormal1], [Skin.popupsWinPanelWinTierFrameNormal0V2, Skin.popupsWinPanelWinTierFrameNormal1V2, Skin.popupsWinPanelWinTierFrameNormal2], Skin.popupsWinPanelWinTierFrameNormalV2, Skin.popupsWinPanelWinTierFrameNormalV3, Skin.popupsWinPanelWinTierFrameNormalV4)
        case .hard: return (Skin.popupsWinPanelWinTierFrameHard, [Skin.popupsWinPanelWinTierFrameHard0, Skin.popupsWinPanelWinTierFrameHard1], [Skin.popupsWinPanelWinTierFrameHard0V2, Skin.popupsWinPanelWinTierFrameHard1V2, Skin.popupsWinPanelWinTierFrameHard2], Skin.popupsWinPanelWinTierFrameHardV2, Skin.popupsWinPanelWinTierFrameHardV3, Skin.popupsWinPanelWinTierFrameHardV4)
        case .superHard: return (Skin.popupsWinPanelWinTierFrameSuperHard, [Skin.popupsWinPanelWinTierFrameSuperHard0, Skin.popupsWinPanelWinTierFrameSuperHard1], [Skin.popupsWinPanelWinTierFrameSuperHard0V2, Skin.popupsWinPanelWinTierFrameSuperHard1V2, Skin.popupsWinPanelWinTierFrameSuperHard2], Skin.popupsWinPanelWinTierFrameSuperHardV2, Skin.popupsWinPanelWinTierFrameSuperHardV3, Skin.popupsWinPanelWinTierFrameSuperHardV4)
        }
    }
    var closeRing: [UInt32] { tag == .hard ? [Skin.popupsWinPanelWinTierCloseRing0, Skin.popupsWinPanelWinTierCloseRing1, Skin.popupsWinPanelWinTierCloseRing2] : [Skin.popupsWinPanelWinTierCloseRing0V2, Skin.popupsWinPanelWinTierCloseRing1V2, Skin.popupsWinPanelWinTierCloseRing2V2] }
    /// the popup well recipe in the tier colour (VERIFIED 020 / 037 / 063 at y 541)
    var offerWell: OfferWell.Palette { tag == .normal ? .blue : (tag == .hard ? .red : .purple) }
    var glow: [UInt32] { tag == .normal ? [Skin.popupsWinPanelWinTierGlow0, Skin.popupsWinPanelWinTierGlow1] : (tag == .hard ? [Skin.popupsWinPanelWinTierGlowHard0, Skin.popupsWinPanelWinTierGlowHard1] : [Skin.popupsWinPanelWinTierGlowNotHard0, Skin.popupsWinPanelWinTierGlowNotHard1]) }
}

/// S1's PopupPanelFrame recipe with a tier palette (red / purple win panels).
struct TierPanelFrame: View {
    let tier: WinTier
    let t: Tokens
    var n: CGFloat = 5.92

    var body: some View { Rasterized("tierPanel|\(tier.key)|\(n)") { _ in art } }

    @ViewBuilder private var art: some View {
        GeometryReader { geo in
            let r = CGRect(origin: .zero, size: geo.size)
            let c = tier.frame
            let outer = Superellipse(n: n)
            let bar: CGFloat = 18.6
            ZStack(alignment: .topLeading) {
                outer.fill(Color(hex: c.outline))
                outer.fill(LinearGradient(colors: c.bar.map { Color(hex: $0) }, startPoint: .top, endPoint: .bottom)).padding(0.8)
                outer.fill(LinearGradient(colors: c.bumper.map { Color(hex: $0) }, startPoint: .topLeading, endPoint: .bottomTrailing))
                    .padding(0.8)
                    .mask(TierCornerArms(arm: CGSize(width: 80, height: 87)))
                Superellipse(n: n).fill(Color(hex: c.groove)).padding(bar)
                ZStack {
                    Superellipse(n: n).fill(Color(hex: c.field))
                    Superellipse(n: n).stroke(Color(hex: c.groove), lineWidth: 16).blur(radius: 4.5).clipShape(Superellipse(n: n))
                }
                .padding(bar + 1.3)
                ForEach(Array(Self.rivets(in: r).enumerated()), id: \.offset) { _, p in
                    ZStack {
                        Circle().fill(Color(hex: c.outline))
                        Circle().fill(RadialGradient(colors: [Color.white.opacity(0.8), Color(hex: c.rivet)], center: UnitPoint(x: 0.4, y: 0.35),
                                                     startRadius: 0, endRadius: 6)).padding(1.2)
                    }
                    .frame(width: 13, height: 13).position(p)
                }
            }
        }
        .accessibilityHidden(true)
    }

    static func rivets(in r: CGRect) -> [CGPoint] {
        let ix: CGFloat = 12.2, iy: CGFloat = 80.2, along: CGFloat = 73
        return [CGPoint(x: r.minX + ix, y: r.minY + iy), CGPoint(x: r.maxX - ix, y: r.minY + iy),
                CGPoint(x: r.minX + ix, y: r.maxY - iy), CGPoint(x: r.maxX - ix, y: r.maxY - iy),
                CGPoint(x: r.minX + along, y: r.maxY - ix), CGPoint(x: r.maxX - along, y: r.maxY - ix)]
    }
}

private struct TierCornerArms: Shape {
    var arm: CGSize
    func path(in r: CGRect) -> Path {
        var p = Path()
        for (x, y) in [(r.minX, r.minY), (r.maxX - arm.width, r.minY), (r.minX, r.maxY - arm.height), (r.maxX - arm.width, r.maxY - arm.height)] {
            p.addRect(CGRect(x: x, y: y, width: arm.width, height: arm.height))
        }
        return p
    }
}

/// The light radial glow behind the coin stack (VERIFIED 020: the field brightens towards the coins).
private struct CoinGlow: View {
    let tier: WinTier
    var body: some View {
        Rasterized("coinGlow|\(tier.key)") { size in
            RadialGradient(stops: [.init(color: Color(hex: tier.glow[0], 0.95), location: 0),
                                   .init(color: Color(hex: tier.glow[0], 0.55), location: 0.35),
                                   .init(color: Color(hex: tier.glow[1], 0.25), location: 0.7),
                                   .init(color: .clear, location: 1)],
                           center: UnitPoint(x: 0.5, y: 0.62), startRadius: 0, endRadius: max(size.width, size.height) * 0.55)
        }
    }
}

/// The four-point twinkles around the coins (VERIFIED 020 / 037 / 171 positions), our `sparkleTwinkle`.
private struct WinTwinkles: View {
    let t: Tokens
    var body: some View {
        let spots: [(CGFloat, CGFloat, CGFloat)] = [(147, 397, 16), (243, 386, 19), (281, 386, 21), (115, 448, 19)]
        ZStack(alignment: .topLeading) {
            ForEach(Array(spots.enumerated()), id: \.offset) { _, s in
                ArtImage(art: .fxSparkle).placed(CGRect(s.0 - s.2 / 2, s.1 - s.2 / 2, s.2, s.2))
            }
        }
        .allowsHitTesting(false)
    }
}

/// The Hard / Super Hard tag ribbon above the level ribbon with a skull each side (VERIFIED 037 / 063).
struct TierTagRibbon: View {
    let tag: LevelTag
    let frame: CGRect
    let t: Tokens

    var body: some View {
        let hard = tag == .hard
        let style = hard ? t.text("winHard.tagRibbon.tag", .s2(23.4, -0.96, [Skin.popupsWinPanelWinHardTagRibbonTag0], outline: Skin.popupsWinPanelWinHardTagRibbonTagOutline, 1.56, drop: 1.04))
                         : t.text("winSuperHard.tagRibbon.tag", .s2(23.2, -0.65, [Skin.popupsWinPanelWinSuperHardTagRibbonTag0], outline: Skin.popupsWinPanelWinSuperHardTagRibbonTagOutline, 1.87, drop: 0.71))
        let base = CGFloat(hard ? t.number("text.winHard.tagRibbon.tag.baseline", 137.5) : t.number("text.winSuperHard.tagRibbon.tag.baseline", 138.7))
        let label: LocalizedStringResource = hard ? "Hard Level" : "Super Hard"
        let layout = GameTextLayout.make(String(localized: label), postScriptName: style.postScriptName, size: style.size,
                                         tracking: style.tracking, maxWidth: 150, minScale: style.minScale)
        let skullGap: CGFloat = 8
        ZStack(alignment: .topLeading) {
            Rasterized("tagRibbon|\(tag.rawValue)", overflow: 3) { _ in TagPlate(hard: hard) }.placed(frame)
            GameText(label, style: style, maxWidth: 150).at(frame.midX, style.capCentre(baseline: base))
            Skull(hard: hard).frame(width: 25, height: 25).position(x: frame.midX - layout.advance / 2 - skullGap - 12.5, y: base - 8.5)
            Skull(hard: hard).frame(width: 25, height: 25).position(x: frame.midX + layout.advance / 2 + skullGap + 12.5, y: base - 8.5)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("win.tagRibbon")
        .accessibilityLabel(Text(label))
    }
}

/// The tag plate (VERIFIED 037 / 063 at x 150 and y 118 / 135): a dark outline ~2 pt, a bright hairline inside it, and a flat
/// tier face (#CD000D → #C5000E; #7300D8).
private struct TagPlate: View {
    let hard: Bool
    var body: some View {
        ZStack {
            TagShape().fill(Color(hex: hard ? Skin.popupsWinPanelTagPlateFillHard : Skin.popupsWinPanelTagPlateFillNotHard))
            TagShape().fill(Color(hex: hard ? Skin.popupsWinPanelTagPlateFillHardV2 : Skin.popupsWinPanelTagPlateFillNotHardV2))
                .padding(EdgeInsets(top: 2.2, leading: 2.4, bottom: 0, trailing: 2.4))
            TagShape().fill(LinearGradient(colors: hard ? [Color(hex: Skin.popupsWinPanelTagPlateColorsHard0), Color(hex: Skin.popupsWinPanelTagPlateColorsHard1)]
                                                        : [Color(hex: Skin.popupsWinPanelTagPlateColorsNotHard0), Color(hex: Skin.popupsWinPanelTagPlateColorsNotHard1)],
                                           startPoint: .top, endPoint: .bottom))
                .padding(EdgeInsets(top: 3.4, leading: 3.6, bottom: 0, trailing: 3.6))
                .blur(radius: 0.6)
        }
    }
}

private struct TagShape: Shape {
    /// VERIFIED 037 in the 240.2 x 56.7 token frame: the top edge 4 pt down, the widest point 12.7 in at 18 pt down, the sides
    /// narrowing to 18 in at the bottom (under the level plate), and a long chamfer-like curve into the top edge.
    func path(in r: CGRect) -> Path {
        let kx = r.width / 240.2, ky = r.height / 56.7
        func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: r.minX + x * kx, y: r.minY + y * ky) }
        func q(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: r.maxX - x * kx, y: r.minY + y * ky) }
        var path = Path()
        path.move(to: p(18.0, 56.7))
        path.addLine(to: p(12.7, 19))
        path.addQuadCurve(to: p(40, 4), control: p(24, 9))
        path.addLine(to: q(40, 4))
        path.addQuadCurve(to: q(12.7, 19), control: q(24, 9))
        path.addLine(to: q(18.0, 56.7))
        path.closeSubpath()
        return path
    }
}

/// Our skull, drawn in code (white cranium, dark eye sockets and nose, a jaw with teeth lines, a dark outline).
struct Skull: View {
    let hard: Bool
    var body: some View {
        Rasterized("skull|\(hard)", overflow: 2) { size in
            let w = size.width, h = size.height
            let ink = Color(hex: hard ? Skin.popupsWinPanelSkullInkHard : Skin.popupsWinPanelSkullInkNotHard)
            ZStack {
                if !hard {
                    // Super Hard: skull and crossbones (VERIFIED 063)
                    ForEach([45.0, -45.0], id: \.self) { a in
                        Capsule().fill(ink).frame(width: w * 1.12, height: h * 0.2).rotationEffect(.degrees(a)).offset(y: h * 0.12)
                        Capsule().fill(Color.white).frame(width: w * 1.02, height: h * 0.11).rotationEffect(.degrees(a)).offset(y: h * 0.12)
                    }
                }
                ZStack {
                    Ellipse().frame(width: w * 0.92, height: h * 0.74).offset(y: -h * 0.1)
                    RoundedRectangle(cornerRadius: w * 0.12).frame(width: w * 0.56, height: h * 0.36).offset(y: h * 0.28)
                }
                .foregroundStyle(ink)
                ZStack {
                    Ellipse().frame(width: w * 0.8, height: h * 0.62).offset(y: -h * 0.1)
                    RoundedRectangle(cornerRadius: w * 0.09).frame(width: w * 0.44, height: h * 0.27).offset(y: h * 0.27)
                }
                .foregroundStyle(LinearGradient(colors: [Color.white, Color(hex: Skin.popupsWinPanelSkullColors1)], startPoint: .top, endPoint: .bottom))
                HStack(spacing: w * 0.1) {
                    Ellipse().fill(ink).frame(width: w * 0.24, height: h * 0.22)
                    Ellipse().fill(ink).frame(width: w * 0.24, height: h * 0.22)
                }
                .offset(y: -h * 0.06)
                Triangle().fill(ink).frame(width: w * 0.12, height: h * 0.1).offset(y: h * 0.1)
                HStack(spacing: w * 0.07) {
                    ForEach(0..<3, id: \.self) { _ in Capsule().fill(ink).frame(width: w * 0.045, height: h * 0.13) }
                }
                .offset(y: h * 0.31)
            }
            .frame(width: w, height: h)
        }
    }
}

private struct Triangle: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path()
        p.move(to: CGPoint(x: r.midX, y: r.minY)); p.addLine(to: CGPoint(x: r.maxX, y: r.maxY)); p.addLine(to: CGPoint(x: r.minX, y: r.maxY))
        p.closeSubpath()
        return p
    }
}
