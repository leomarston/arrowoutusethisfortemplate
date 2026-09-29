import SwiftUI
import PathCore

// SHELL S2 (SPEC-ui §2.6.1 Out of Time!, §2.6.2 Out of Lives!; uim `outOfTime.*`, tok2 `outOfLives.*`; VERIFIED 013 / 030 /
// meta-069 / meta-088). The first step of the fail chain, the one popup with no panel: dim 0.94 (`dim.outOfTime`) with a coloured
// radial glow behind the prop, the title (52 pt, white → pink face, a double outline #580008 1.5 + #E42831 3, a #5F111A drop),
// the prop (the big stopwatch / a big glossy heart), the grant ("+30 sec" outlined #004DFB / "+3 Lives" outlined #580008), a
// framed green "Add Time" / "Add Lives" + coin + price button, the red X at the top right, the coin group at the top left
// (above the dim). Appears complete in one frame (SPEC-motion-audio §6.2; GAME plays the `fail` haptic on it).
// Answers: the button → `pay()` (GAME's PayAction; it may put the Shop over the offer and re-check) → .primary when paid, else
// the popup stays; X → .close (GAME continues the chain). The same view serves `PopupRequest.continueOffer` with an
// `.outOfHearts` offer and no warning (CONSISTENCY ID-11: `-pc.popup continue:hearts`).

struct OutOfTimePopup: View {
    let offer: ContinueOffer
    let pay: PayAction
    let answer: PopupAnswer
    /// The container id's suffix: "outOfTime" (PopupRequest.outOfTime) or "continue" (the hearts-out continueOffer).
    var popupID = "outOfTime"
    @Environment(AppModel.self) private var app
    @State private var paying = false

    private var hearts: Bool { offer.kind == .outOfHearts }

    var body: some View {
        let t = app.tuning.ui.tokens
        let key = hearts ? "outOfLives" : "outOfTime"
        ZStack(alignment: .topLeading) {
            OfferGlow(hearts: hearts, t: t)
                .placed(hearts ? t.frame("outOfLives.glow", CGRect(16, 218, 360, 360)) : t.frame("outOfTime.glow", CGRect(26, 214, 340, 340)))
                .allowsHitTesting(false)
            TokenText(id: key + ".title", source: .copy(hearts ? "Out of Lives!" : "Out of Time!"),
                      style: .s2(hearts ? 52.1 : 51.6, hearts ? -1.21 : -1.04, [0xFFFFFF, 0xFFFAFA, 0xF7E8DC], outline: 0x540900, 1.5,
                                 drop: 5.2, dropColor: 0x5A1812),
                      baseline: hearts ? 215.5 : 215.2, centreX: hearts ? 196.5 : 196.7, maxWidth: 345, rings: [(0xD34434, 5.8)],
                      ringDY: 1.4, innerDY: 2.4)
            if hearts {
                BigGlossyHeart(t: t).placed(t.frame("outOfLives.heart", CGRect(103.8, 320.6, 184.8, 155.1)))
            } else {
                InkImage(art: .stopwatchBig, ink: t.frame("outOfTime.stopwatch", CGRect(91.7, 273.6, 208.2, 220.9)))
            }
            TokenText(id: key + ".grant", source: .copy(hearts ? "+3 Lives" : "+30 sec"),
                      style: .s2(hearts ? 60.4 : 61.0, hearts ? -1.1 : -0.75, [0xF9F1E6], outline: hearts ? 0x540900 : 0x006E6C,
                                 2.1, drop: 2.62),
                      baseline: 554.7, centreX: hearts ? 196.5 : 197.5, maxWidth: 345)
            PriceButton(id: "popup.\(popupID).primary", label: hearts ? "Add Lives" : "Add Time",
                        price: offer.price,
                        face: hearts ? t.frame("outOfLives.addLives", CGRect(80.7, 633.5, 231.9, 86.7))
                                     : t.frame("outOfTime.addTimeFace", CGRect(79.7, 632.9, 233.9, 88.1)),
                        well: hearts ? t.frame("outOfLives.addFrame", CGRect(71.4, 627.5, 250.9, 105.4))
                                     : t.frame("outOfTime.addTime", CGRect(71.7, 627.5, 249.9, 104.1)),
                        n: t.superellipseN(key + ".button", hearts ? 4.8 : 5.1),
                        labelID: key + ".button.label",
                        labelStyle: .s2(23.1, hearts ? 0.09 : 0.22, [0xFFFBF3, 0xFFF7E7, 0xFDF3DF], outline: 0x924500, 1.17, drop: 1.05),
                        labelAt: (156.0, hearts ? 684.6 : 684.3),
                        priceID: key + ".button.price",
                        priceStyle: .s2(26.2, 0.52, [0xFFFBF3, 0xFFF7E6, 0xFDF3DF], outline: 0x924500, 1.62, drop: 0.86),
                        priceAt: (267.6, 685.9),
                        coin: t.frame(key + ".button.coin", CGRect(216.2, 666.3, 25.8, 25.8)),
                        wellInset: OfferWell.tightInset) { buy() }
            OfferCoinGroup(frame: t.frame(key + ".coinGroup", CGRect(12.7, 62.4, 108.4, 44.4)), coins: app.store.state.coins,
                           textID: key + ".coinGroup.digits")
            PopupCloseButton(id: "popup.\(popupID).close", t: t) { answer(PopupResult.close) }
                .placed(t.frame(key + ".closeDisc", hearts ? CGRect(327.1, 54.4, 45, 45) : CGRect(327.5, 53.0, 45, 45)))
        }
    }

    private func buy() {
        guard !paying else { return }
        paying = true
        Task { @MainActor in
            let paid = await pay()
            paying = false
            Log.mark("popup", "\(hearts ? "outOfLives" : "outOfTime") pay → \(paid ? "paid" : "not paid")")
            if paid { answer(PopupResult.primary) }
        }
    }
}

/// The coloured radial glow behind the prop, over the 0.94 dim (VERIFIED 013: #0C1840 at the stopwatch's edge → #0F0F0F by
/// 190 pt out; meta-088: #FF2F20 at the heart's edge, #480F0D at 100 pt, black by 150 pt).
struct OfferGlow: View {
    let hearts: Bool
    let t: Tokens
    var body: some View {
        let stops: [Gradient.Stop] = hearts
            ? [.init(color: t.color("outOfLives.glowCore", 0xF04830).opacity(0.95), location: 0),
               .init(color: t.color("outOfLives.glowCore", 0xF04830).opacity(0.62), location: 0.28),
               .init(color: t.color("outOfLives.glowMid", 0x761B0F).opacity(0.45), location: 0.46),
               .init(color: Color(hex: 0x1D0B00, 0.25), location: 0.62),
               .init(color: .clear, location: 0.8)]
            : [.init(color: t.color("outOfTime.glowCore", 0x00716E).opacity(0.75), location: 0),
               .init(color: t.color("outOfTime.glowCore", 0x00716E).opacity(0.55), location: 0.3),
               .init(color: t.color("outOfTime.glowMid", 0x0A4B4E).opacity(0.28), location: 0.5),
               .init(color: Color(hex: 0x0A1E20, 0.12), location: 0.7),
               .init(color: .clear, location: 0.95)]
        Rasterized("offerGlow|\(hearts)") { size in
            RadialGradient(stops: stops, center: .center, startRadius: 0, endRadius: min(size.width, size.height) / 2)
        }
    }
}

/// A whole glossy red heart drawn in code (SPEC-ui §2.6.2 `heartBig`: the MANIFEST has no whole big heart; GlossyChrome's heart
/// outline + the HUD heart's shading recipe at 185 pt, VERIFIED look meta-088).
struct BigGlossyHeart: View {
    let t: Tokens
    var body: some View {
        Rasterized("bigHeart2", overflow: 4) { size in
            let s = ClassicHeart()
            ZStack {
                s.fill(Color(hex: 0x3A0205, 0.55)).offset(y: size.height * 0.012).blur(radius: 2)
                s.fill(EllipticalGradient(stops: [.init(color: t.color("heartBig.hi", 0xFF7A66), location: 0),
                                                  .init(color: t.color("heartBig.face", 0xF8392B), location: 0.28),
                                                  .init(color: Color(hex: 0xEE2418), location: 0.55),
                                                  .init(color: Color(hex: 0xD20F08), location: 0.8),
                                                  .init(color: Color(hex: 0xA80400), location: 1)],
                                          center: UnitPoint(x: 0.4, y: 0.36), startRadiusFraction: 0, endRadiusFraction: 0.66))
                s.fill(LinearGradient(stops: [.init(color: Color(hex: 0x8A0006, 0.0), location: 0.6),
                                              .init(color: Color(hex: 0x8A0006, 0.45), location: 1)], startPoint: .top, endPoint: .bottom))
                Ellipse().fill(RadialGradient(colors: [Color.white.opacity(0.75), Color(hex: 0xFFB8A8, 0.35), .clear], center: .center,
                                              startRadius: 0, endRadius: size.width * 0.13))
                    .frame(width: size.width * 0.26, height: size.height * 0.16).rotationEffect(.degrees(-35))
                    .position(x: size.width * 0.3, y: size.height * 0.24)
                s.stroke(Color(hex: 0x6E0E16), lineWidth: 1.6)
            }
            .frame(width: size.width, height: size.height)
        }
    }
}

/// A classic heart (round lobes, a deep notch, a pointed tip) filling its rect (VERIFIED meta-088 silhouette).
struct ClassicHeart: Shape {
    func path(in r: CGRect) -> Path {
        func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: r.minX + x * r.width, y: r.minY + y * r.height) }
        var path = Path()
        path.move(to: p(0.5, 1.0))
        // the lower sides fitted to meta-088's silhouette (rows 394-474, max error ≈ 1 pt; the old 0.30/0.82 · 0/0.62 curve
        // was 12 pt too thin at y 450)
        path.addCurve(to: p(0.0, 0.32), control1: p(0.33, 0.99), control2: p(-0.04, 0.57))
        path.addCurve(to: p(0.27, 0.0), control1: p(0.0, 0.12), control2: p(0.13, 0.0))
        path.addCurve(to: p(0.5, 0.17), control1: p(0.40, 0.0), control2: p(0.47, 0.08))
        path.addCurve(to: p(0.73, 0.0), control1: p(0.53, 0.08), control2: p(0.60, 0.0))
        path.addCurve(to: p(1.0, 0.32), control1: p(0.87, 0.0), control2: p(1.0, 0.12))
        path.addCurve(to: p(0.5, 1.0), control1: p(1.04, 0.57), control2: p(0.67, 0.99))
        path.closeSubpath()
        return path
    }
}
