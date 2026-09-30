import SwiftUI

// SHELL S1 (SPEC-architecture §6.4 item 6; design/ui-measure.md `home.navBar`, `home.navHomeTab`, `home.navShop`,
// `home.navTrophy`; VERIFIED 026). The bottom nav (bottom-anchored, to the screen's bottom edge): a 1 pt dark line, 2 pt dark
// blue, a bright cyan line, then the #00A0FF → #134BEF column (`colors.nav.bar`, pt from the top). The SELECTED tab is raised
// 18 pt (140.1 pt wide, cyan field inside a light rim and a dark-blue groove) with its icon overhanging the tab top and its
// label; the others show their icon only (SPEC-ui §2.2.6 + C8: the raised tile moves with the selection, labels "Shop" /
// "Home" / "Leaderboard", box 118). Tabs: shop basket · Home · trophy (a red "!" badge on the trophy is S3's).

struct HomeNavBar: View {
    let tab: HomeTab
    let select: (HomeTab) -> Void
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let bar = t.rect("home.navBar", CGRect(0, 771.7, 393, 81.1), .bottom, m)
        let barRect = CGRect(x: 0, y: bar.minY, width: m.size.width, height: m.size.height - bar.minY)
        let home = t.frame("home.navHomeTab", CGRect(126.8, 753.6, 140.1, 99.1))
        // SPEC-ui C8: the raised tile moves with the selection — Shop flush left (x 0-141.5), Leaderboard flush right
        // (x 253.5-393); the measured Shop/Leaderboard frames include the overhanging icon, so the tile top stays the Home one.
        let tiles: [HomeTab: CGRect] = [.home: home, .shop: t.frame("home.navShopTab", CGRect(0, 744, 141.5, 108.8)),
                                        .leaderboard: t.frame("home.navLeaderboardTab", CGRect(253.5, 734, 139.5, 118.8))]
        let sel = tiles[tab] ?? home
        let raised = CGRect(x: sel.minX, y: home.minY, width: sel.width, height: 852 - home.minY)
        let centres: [HomeTab: CGFloat] = [.shop: tab == .shop ? sel.midX : 68.4, .home: home.midX,
                                           .leaderboard: tab == .leaderboard ? sel.midX : 324.4]
        ZStack(alignment: .topLeading) {
            Rectangle()
                .fill(LinearGradient(stops: t.stops("nav.bar", span: CGFloat(bar.height / m.s), Self.barStops), startPoint: .top,
                                     endPoint: .bottom))
                .placed(barRect)
            // FIX-V2: the column grooves between the unselected tabs (meta-012 x 259.4, meta-013 x 131.8: a 1 pt light line
            // #0B9CED → #18A7FA, then 1 pt #0042CB); the raised tile covers the one(s) next to it
            ForEach([131.8, 259.4], id: \.self) { x in
                HStack(spacing: 0) {
                    LinearGradient(colors: [Color(hex: Skin.homeNavBarHomeNavBarColors0), Color(hex: Skin.homeNavBarHomeNavBarColors1), Color(hex: Skin.homeNavBarHomeNavBarColors2), Color(hex: Skin.homeNavBarHomeNavBarColors3)],
                                   startPoint: .top, endPoint: .bottom)
                    Color(hex: Skin.homeNavBarHomeNavBar)
                }
                .placed(m.rect(CGRect(x: x, y: 772.2, width: 2.2, height: 852 - 772.2), .bottom))
            }
            RaisedTab(t: t).placed(m.rect(raised, .bottom).insetBy(dx: 0, dy: 0))
            ForEach(HomeTab.allCases, id: \.self) { item in
                tabButton(item, t: t, selected: item == tab, centreX: centres[item] ?? 0)
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("nav")
    }

    static let barStops: [(Double, UInt32)] = [(0, Skin.homeNavBarHomeNavBarBarStops0), (0.3, Skin.homeNavBarHomeNavBarBarStops1), (2.0, Skin.homeNavBarHomeNavBarBarStops2), (3.4, Skin.homeNavBarHomeNavBarBarStops3), (3.7, Skin.homeNavBarHomeNavBarBarStops4),
                                               (4.0, Skin.homeNavBarHomeNavBarBarStops5), (6.0, Skin.homeNavBarHomeNavBarBarStops6), (30.3, Skin.homeNavBarHomeNavBarBarStops7), (53.3, Skin.homeNavBarHomeNavBarBarStops8), (81.1, Skin.homeNavBarHomeNavBarBarStops9)]

    @ViewBuilder private func tabButton(_ item: HomeTab, t: Tokens, selected: Bool, centreX: CGFloat) -> some View {
        let art: UIArt = item == .shop ? .navShopIcon : item == .home ? .navHomeIcon : .navLeaderboardIcon
        // FIX-V2 F-01: the frames are the ART boxes (the 3d renders carry 3-8 pt of transparent margin), placed at the art's
        // native aspect so the INK lands on the phone's measured ink boxes (026 / meta-012 / meta-013 / meta-018): unselected
        // shop 42.4 · 782.4 · 51.4 · 52.4, home 172.4 · 780.0 · 49.0 · 55.7, trophy 297.4 · 782.4 · 55.4 · 52.7 (ink bottoms
        // ≈ 835.2); a SELECTED icon is the same icon × 1.445 with its ink bottom at 814.4 (home 161.4 · 734.0 · 71.1 · 80.4,
        // basket ≈ 31 · 738.5 · 74.3 · 75.7, trophy 284 · 738.2 · 80 · 76.2). Before, all three were squeezed into the old
        // 56.7 / 74.4 pt boxes (ink 17-20 % small, the Home icon 14 pt low).
        let icon: CGRect = {
            switch (item, selected) {
            case (.shop, false): return t.frame("home.navShop", CGRect(37.65, 777.95, 61.19, 61.19))
            case (.shop, true): return t.frame("home.navShopSel", CGRect(24.36, 731.69, 88.41, 88.41))
            case (.home, false): return t.frame("home.navHomeRest", CGRect(169.25, 777.31, 56.0, 60.2))
            case (.home, true): return t.frame("home.navHomeIcon", CGRect(157.0, 730.75, 80.92, 86.99))
            case (.leaderboard, false): return t.frame("home.navTrophy", CGRect(289.92, 778.18, 71.4, 65.1))
            case (.leaderboard, true): return t.frame("home.navTrophySel", CGRect(273.18, 732.03, 103.16, 94.05))
            }
        }()
        let label: LocalizedStringResource = item == .shop ? "Shop" : item == .home ? "Home" : "Leaderboard"
        let labelID = item == .shop ? "home.navLabelShop" : item == .home ? "home.navLabel" : "home.navLabelLeaderboard"
        let base0 = t.text("home.navLabel", GameTextStyle(size: 15.1, tracking: -0.25, fill: [.white], outline: Color(hex: Skin.homeNavBarHomeNavLabelOutline),
                                                          outlineWidth: 0.98, drop: 0.58))
        let st0 = t.text(labelID, base0)
        let style = st0.sized(st0.size * m.s)
        let column = m.rect(CGRect(x: centreX - 65, y: 760, width: 130, height: 92), .bottom)
        let base = m.point(CGPoint(x: centreX, y: 832.7), .bottom)
        GameButton(id: "nav.\(item.rawValue)", label: label, value: selected ? "selected" : nil, action: { select(item) }) {
            ZStack(alignment: .topLeading) {
                let ic = m.rect(icon, .bottom)
                ArtImage(art: art).placed(ic.offsetBy(dx: -column.minX, dy: -column.minY))
                if selected {
                    GameText(label, style: style, maxWidth: 118 * m.s)
                        .at(base.x - column.minX, style.capCentre(baseline: base.y) - column.minY)
                }
            }
            .frame(width: column.width, height: column.height, alignment: .topLeading)
        }
        .placed(column)
        .anchor(.navTab(item))
    }
}

/// The raised selected tab: blue edge, light cyan rim, dark-blue groove, a light line, the cyan field (xsec.home.navHomeTab.*).
private struct RaisedTab: View {
    let t: Tokens
    var body: some View {
        let rim = t.colors("nav.tabRim", [Skin.homeNavBarNavTabRim0, Skin.homeNavBarNavTabRim1, Skin.homeNavBarNavTabRim2])
        let field = t.colors("nav.tabField", [Skin.homeNavBarNavTabField0, Skin.homeNavBarNavTabField1, Skin.homeNavBarNavTabField2])
        let shape = UnevenRoundedRectangle(topLeadingRadius: 18, bottomLeadingRadius: 0, bottomTrailingRadius: 0, topTrailingRadius: 18)
        ZStack {
            shape.fill(t.color("nav.tabEdge", Skin.homeNavBarNavTabEdge))
            shape.fill(LinearGradient(colors: rim, startPoint: .top, endPoint: .bottom)).padding(EdgeInsets(top: 1.5, leading: 1.5, bottom: 0, trailing: 1.5))
            UnevenRoundedRectangle(topLeadingRadius: 12, bottomLeadingRadius: 0, bottomTrailingRadius: 0, topTrailingRadius: 12)
                .fill(t.color("nav.tabGroove", Skin.homeNavBarNavTabGroove)).padding(EdgeInsets(top: 8.3, leading: 8.7, bottom: 0, trailing: 8.7))
            UnevenRoundedRectangle(topLeadingRadius: 9, bottomLeadingRadius: 0, bottomTrailingRadius: 0, topTrailingRadius: 9)
                .fill(t.color("nav.tabLine", Skin.homeNavBarNavTabLine)).padding(EdgeInsets(top: 13, leading: 13, bottom: 0, trailing: 13))
            UnevenRoundedRectangle(topLeadingRadius: 8, bottomLeadingRadius: 0, bottomTrailingRadius: 0, topTrailingRadius: 8)
                .fill(LinearGradient(colors: field, startPoint: .top, endPoint: .bottom)).padding(EdgeInsets(top: 14.5, leading: 14.5, bottom: 0, trailing: 14.5))
        }
        .accessibilityHidden(true)
    }
}
