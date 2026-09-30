import SwiftUI

// SHELL S2 (SPEC-ui §2.3.1 `hud.coinGroup`; uim `hud.coinIcon`, `hud.coinPill`, VERIFIED 003). The level's coin group beside the
// Dynamic Island: the coin 19.7 · 30.4 · 23.7 · 24.4 over the left end of a recessed light-blue pill 42.7 · 30.4 · 64.4 · 22 (rr 6.8,
// #BDDCFF, a dark top inner edge #527DC8 → #BBDAFE, a light lower rim) with the digits 18.5 / +0.25 #3861AC plain (box 52).
// Not tappable in a level (DECISION: v552 never showed a reaction). Top-anchored; it rides the HUD drop.

struct HUDCoinGroup: View, Equatable {
    let coins: Int
    let t: Tokens
    let m: ShellMetrics

    static func == (a: HUDCoinGroup, b: HUDCoinGroup) -> Bool { a.coins == b.coins && a.m == b.m }

    var body: some View {
        let pill = t.rect("hud.coinPill", CGRect(42.7, 30.4, 64.4, 22), .top, m)
        let coin = t.rect("hud.coinIcon", CGRect(19.7, 30.4, 23.7, 24.4), .top, m)
        let style = t.text("hud.coinPill.digits", .s2(18.5, 0.25, [Skin.hudCoinPillHUDHudCoinPillDigits0])).sized(18.5 * m.s)
        let p = t.textPoint("hud.coinPill.digits", baseline: 48.4, centreX: 74.7)
        let at = m.point(CGPoint(x: p.x, y: p.baseline), .top)
        ZStack(alignment: .topLeading) {
            Rasterized("hudCoinPill", overflow: 1.5) { _ in HUDRecessedPill(radius: t.radius("hud.coinPill", 6.76) * m.s, t: t) }
                .placed(pill)
            GameText(verbatim: "\(coins)", style: style, maxWidth: CGFloat(t.textMaxWidth("hud.coinPill.digits", 52) ?? 52) * m.s)
                .at(at.x, style.capCentre(baseline: at.y))
            InkImage(art: .iconCoin, ink: coin.insetBy(dx: -0.6, dy: -0.6))
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("hud.coins")
        .accessibilityLabel(Text("Coins"))
        .accessibilityValue(Text(verbatim: "\(coins)"))
    }
}

/// The recessed light-blue pill of the HUD coin group (xsec.hud.coinPill: a white outer rim, a dark top inner edge, face #BDDCFF).
struct HUDRecessedPill: View {
    let radius: CGFloat
    let t: Tokens

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: radius, style: .continuous)
        ZStack {
            shape.fill(Color.white).padding(-1.2)
            shape.fill(t.color("hud.coinPillEdge", Skin.hudCoinPillHUDHudCoinPillEdge))
            shape.fill(LinearGradient(stops: [.init(color: t.color("hud.coinPillTop", Skin.hudCoinPillHUDHudCoinPillTop), location: 0),
                                              .init(color: Color(hex: Skin.hudCoinPillHUDHudRecessedPillStops1), location: 0.06),
                                              .init(color: t.color("hud.coinPill", Skin.hudCoinPillHUDHudCoinPill), location: 0.14),
                                              .init(color: t.color("hud.coinPill", Skin.hudCoinPillHUDHudCoinPill), location: 0.82),
                                              .init(color: Color(hex: Skin.hudCoinPillHUDHudRecessedPillStops4), location: 0.9),
                                              .init(color: Color(hex: Skin.hudCoinPillHUDHudRecessedPillStops5), location: 1)],
                                      startPoint: .top, endPoint: .bottom))
                .padding(EdgeInsets(top: 0.6, leading: 0.6, bottom: 0.4, trailing: 0.6))
        }
    }
}
