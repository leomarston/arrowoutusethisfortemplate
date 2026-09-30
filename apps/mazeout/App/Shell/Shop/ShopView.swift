import SwiftUI
import UIKit
import PathCore

// SHELL S3 (SPEC-architecture §6.8; SPEC-ui §2.12 (VERIFIED meta-007..012, text frames tok2 `text2.shop.*`), §2.12.3 the test-store
// note; SPEC-gameplay §9.4-§9.5; CONSISTENCY X-17..X-24, S-18; art rulings 4 (bundle ids) in art/REVIEW.md). The Shop page:
//   header    the page header with the coin pill at the left (no plus) and "Shop"; X at the right only as a closable page
//   scroll    DEBUG builds on the FakeStore only: the honest test-store chip first (the sections move down 30 pt, DECISION D18;
//             A1: never in a Release build — the chip is compiled into DEBUG only and is not a catalogue string),
//             "Special Offers" (purple rail + plate on #370660) with the Special Offer card (gold top, "STARTER" ribbon, 1 000 coins,
//             x1 of each booster, ∞ 1h, the purple name strip, the green price), "Bundles" (blue rail on #0B2176) with Mini / Epic /
//             Elite "Popular" / Mega / Legendary "Best Value" (cream top with the art + amount, items and ∞ tiles, the blue name
//             strip, the price), "Coins" (yellow rail on #460A24) with six coin tiles in a 3 × 2 grid
//   nav       the bottom nav (HomeView draws it) with the Shop tab raised; the closable page has none
// Prices: ONLY the store's `displayPrice` (StoreKit 2: the storefront's currency; the DEBUG FakeStore: its reference TL / US $
// list). A product StoreKit has not priced yet (no network at the first open, a slow store) shows a disabled "…" well and the
// page asks the store again on every open (A1, release-plan §2.5 S-3: never a hard-coded price). A price tap → the
// button presses (0.95) → the store (0.3 s) → the claim overlay per part (coins, then the boosters, then ∞; S2's
// ClaimRewardPopup) → the coins fly to the header pill (segment C from the claim's centre). `.pending` → "Purchase pending";
// cancel → nothing; a failure → nothing (logged). The once-only Special Offer disappears after its purchase (C3 flag).
// Layout: every block is drawn on the 393-wide reference canvas at its measured y (content y = screen y − 115 at scroll 0),
// scaled by s; the scroll view spans the header bottom … the nav top (the screen bottom for the closable page).

enum ShopSection: String { case top, bundles, coins }

struct ShopView: View {
    var closable = false
    var initialSection: ShopSection = .top
    var onClose: (() -> Void)? = nil
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m
    @State private var buying: String?
    @State private var scroll = ScrollPosition(edge: .top)

    var body: some View {
        let t = app.tuning.ui.tokens
        let rules = ShellEconomy.rules(app)
        // FIX-2 A: the Shop TAB is part of home, so it reads home's state proxy — parked under a level it keeps its copy and
        // re-renders nothing on the level's store writes (the attempt at Play, the win banked at the clearing tap: before,
        // this body + its ScrollView re-ran inside those frames, build/p/FIX2/A/tp/base-tp1). The closable page (over a level
        // or a popup) reads the live store.
        let state = closable ? app.store.state : ShellScreens.homeState(app)
        let visible = rules.shop.visible(state)
        let layout = ShopLayout(products: visible, testStore: app.shop.isTestStore)
        let top = m.y(115, .top)
        let bottom = closable ? m.size.height : m.y(771.7, .bottom)
        ZStack(alignment: .topLeading) {
            t.color("shop.groundBottom", Skin.shopShopViewShopGroundBottom).frame(width: m.size.width, height: m.size.height)
            ScrollView(.vertical, showsIndicators: false) {
                ShopContent(layout: layout, prices: prices(rules), buying: buying, scale: m.s) { p in buy(p, rules: rules) }
            }
            .scrollPosition($scroll)
            .scrollBounceBehavior(.basedOnSize)
            .frame(width: m.size.width, height: max(0, bottom - top))
            .offset(y: top)
            .task {
                guard initialSection != .top else { return }
                await FrameWaiter.frames(1)                         // laid out: jump (no animation)
                scroll.scrollTo(id: initialSection == .coins ? "coinsPlate" : "bundlesPlate", anchor: .top)
                Log.mark("shop", "opened at \(initialSection.rawValue)")
            }
            .task { await ShopProbe.soak(app, scroll: $scroll) }
            .task { await (app.shop as? ShopStore)?.refresh() }
            .accessibilityIdentifier("shop.scroll")
            ShellPageHeader(t: t)
            ShopHeaderCoins(live: closable)
            PageTitle(title: "Shop", t: t)
            if closable {
                PopupCloseButton(id: "shop.close", t: t, halo: true) { onClose?() }
                    .placed(m.rect(CGRect(333.0, 51.2, 45, 45), .top))
            }
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .clipped()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.shop")
        .onAppear {
            ShopProbe.open(app, closable ? "shop page open" : "shop tab open")
            ArtStore.preload(ShopView.art)
            Log.mark("shop", "open (\(closable ? "page" : "tab")): \(visible.count) products, store \((app.shop as? ShopStore)?.kind ?? "?"), "
                     + "test note \(app.shop.isTestStore)")
        }
    }

    /// Behind Loading: the whole scroll content once (every card / plate image is made there, not on the first tab switch).
    static func prewarm(_ app: AppModel) -> some View {
        let rules = ShellEconomy.rules(app)
        let layout = ShopLayout(products: rules.shop.products, testStore: app.shop.isTestStore)
        var prices: [String: String] = [:]
        for p in app.shop.products { prices[p.id] = p.displayPrice }
        return ShopContent(layout: layout, prices: prices, buying: nil, lazy: false) { _ in }
    }

    static let art: [UIArt] = [.shopBundleSpecial, .shopBundleMini, .shopBundleEpic, .shopBundleElite, .shopBundleMega, .shopBundleLegendary, .shopCoins1,
                               .shopCoins2, .shopCoins3, .shopCoins4, .shopCoins5, .shopCoins6, .shopSeal, .boosterHintIcon,
                               .boosterFreezeIcon, .livesUnlimitedSmall, .currencyCoinIcon, .fxSunburst]

    private func prices(_ rules: EconomyRules) -> [String: String] {
        var out: [String: String] = [:]
        for p in app.shop.products { out[p.id] = p.displayPrice }
        return out
    }

    private func buy(_ p: ShopProduct, rules: EconomyRules) {
        guard buying == nil else { return }
        let id = rules.shop.storeID(p)
        buying = id
        let before = app.store.state.coins
        Log.mark("shop", "buy \(id)")
        Task { @MainActor in
            let outcome = await app.shop.purchase(id)
            buying = nil
            Log.mark("shop", "buy \(id) → \(outcome)")
            switch outcome {
            case .granted:
                let gained = max(0, app.store.state.coins - before)
                if !closable { ShellScreens.home?.syncState() }            // FIX-2 A: the tab's header counts the coins and the fly together
                if gained > 0 { CoinPillDisplay.shared.flying += gained }
                await ShopPurchaseFlow.claim(p.grant, coins: gained, app: app, metrics: m)
            case .pending:
                app.toasts.show("Purchase pending")
            case .cancelled, .failed:
                break
            }
        }
    }
}

/// SHELL-private perf hooks (`-pc.probeOpen 1`: the frames of the first second after the page appears; `-pc.shopSoak 1`: an
/// animated scroll to Coins and back, 2.5 s each way), logged as "[PC][perf] shop … frames n max x ms over20 k".
@MainActor enum ShopProbe {
    static func open(_ app: AppModel, _ label: String) {
        guard app.args.raw["pc.probeOpen"] == "1" else { return }
        let p = FrameProbe(label)
        p.start()
        Task { @MainActor in try? await Task.sleep(nanoseconds: 1_000_000_000); p.stop() }
    }

    static func soak(_ app: AppModel, scroll: Binding<ScrollPosition>) async {
        guard app.args.raw["pc.shopSoak"] == "1" else { return }
        try? await Task.sleep(nanoseconds: 1_200_000_000)
        let p = FrameProbe("shop scroll")
        p.start()
        withAnimation(.linear(duration: 2.5)) { scroll.wrappedValue.scrollTo(id: "coins.1", anchor: .bottom) }
        try? await Task.sleep(nanoseconds: 2_800_000_000)
        withAnimation(.linear(duration: 2.5)) { scroll.wrappedValue.scrollTo(id: "note", anchor: .top) }
        try? await Task.sleep(nanoseconds: 2_800_000_000)
        p.stop()
    }
}

/// After a granted purchase: one claim overlay per part (coins, boosters, ∞), then the coins fly to the header pill.
@MainActor enum ShopPurchaseFlow {
    static func claim(_ g: Grant, coins: Int, app: AppModel, metrics m: ShellMetrics) async {
        var parts: [Grant] = []
        if g.coins > 0 { parts.append(.coins(g.coins)) }
        let boosters = g.boosters.filter { $0.value > 0 }
        if !boosters.isEmpty { parts.append(Grant(boosters: boosters)) }
        if g.unlimitedLives > 0 { parts.append(.unlimited(g.unlimitedLives)) }
        for (i, part) in parts.enumerated() {
            _ = await app.popups.present(Popup<PopupResult>.claimReward(part))
            if i == 0, coins > 0 { fly(coins, app: app, metrics: m) }
        }
        if parts.isEmpty { CoinPillDisplay.shared.flying = 0 }
    }

    /// Segment C from the claim's reward centre (197, 411) to the Shop header's coin icon (23.5, 76.4).
    static func fly(_ amount: Int, app: AppModel, metrics m: ShellMetrics) {
        guard let host = (app.fx as? FXOverlay)?.hostView.layer else { CoinPillDisplay.shared.flying = 0; return }
        var spec = CoinFlySpec(app.tuning.ui.tokens)
        spec.liftAt = 0.05
        let from = m.point(CGPoint(x: 197, y: 411), .centre)
        let to = m.point(CGPoint(x: 23.5, y: 76.4), .top)
        let control = CGPoint(x: (from.x + to.x) / 2 + 60 * m.s, y: min(from.y, to.y) + 40 * m.s)
        let t0 = host.convertTime(CACurrentMediaTime(), from: nil)
        CATransaction.begin(); CATransaction.setDisableActions(true)
        let layers = CoinFly.layers(amount: amount, spec: spec, from: from, to: to, control: control, labelCentre: from, scale: m.s,
                                    t0: t0, showLabel: false)
        for l in layers { host.addSublayer(l) }
        CATransaction.commit()
        let shares = spec.shares(amount)
        for (k, share) in shares.enumerated() {
            DispatchQueue.main.asyncAfter(deadline: .now() + spec.landing(k)) {
                MainActor.assumeIsolated {
                    CoinPillDisplay.shared.flying = max(0, CoinPillDisplay.shared.flying - share)
                    app.haptics.play(.coinLand)
                    app.fx.play(.sparkles(at: to))
                    if k == shares.count - 1 {
                        CoinPillDisplay.shared.flying = 0
                        for l in layers { l.removeFromSuperlayer() }
                    }
                }
            }
        }
        if let s = app.tuning.audio.cue("homePayout") { app.audio.play(s, gain: Float(app.tuning.audio.gain(s))) }
    }
}

// MARK: - layout (reference pt, content y = screen y − 115 at scroll 0)

struct ShopLayout {
    struct Card { let product: ShopProduct; let top: CGFloat }
    let testStore: Bool
    let noteY: CGFloat = 4                       // 119 − 115
    var shift: CGFloat { testStore ? 30 : 0 }
    let offer: Card?
    let bundles: [Card]
    let coins: [Card]
    let bundlesPlate: CGFloat
    let coinsPlate: CGFloat
    let height: CGFloat

    init(products: [ShopProduct], testStore: Bool) {
        self.testStore = testStore
        let shift: CGFloat = testStore ? 30 : 0
        let offerP = products.first { $0.section == "offer" }
        let bundleP = products.filter { $0.section == "bundle" }
        let coinP = products.filter { $0.section == "coins" }
        // VERIFIED meta-012: offer card 190.2, Bundles plate 403.7, first bundle 472.7 (pitch 203.5); meta-011: the Coins plate
        // 115.6 pt under the last bundle card's bottom, tiles 60 pt under the plate (row pitch 171.8), 16.7 pt of ground after.
        let offerH: CGFloat = offerP == nil ? 0 : 213.5          // 403.7 − 190.2: the Special section collapses once bought
        offer = offerP.map { Card(product: $0, top: 190.2 - 115 + shift) }
        let bundlesPlateY = 403.7 - 115 + shift - (213.5 - offerH)
        bundlesPlate = bundlesPlateY
        bundles = bundleP.enumerated().map { Card(product: $1, top: bundlesPlateY + 69.0 + CGFloat($0) * 203.5) }
        let lastBundleBottom = (bundles.last?.top ?? bundlesPlateY) + (bundles.isEmpty ? 58.4 : 194.5)
        let coinsPlateY = lastBundleBottom + 16.0
        coinsPlate = coinsPlateY
        coins = coinP.enumerated().map { Card(product: $1, top: coinsPlateY + 60.0 + CGFloat($0 / 3) * 171.8) }
        let lastTile = (coins.last?.top ?? coinsPlateY + 43) + (coins.isEmpty ? 0 : 163.5)
        height = lastTile + 16.7
    }

    /// Section grounds switch at the rails' top edges (VERIFIED meta-012 / meta-009).
    var purpleEnd: CGFloat { bundlesPlate + 12.6 }
    var navyEnd: CGFloat { coinsPlate + 8.0 }

    /// The content cut into rows (a lazy stack builds only the visible ones): each element belongs to the row its top is in.
    struct Row: Identifiable, Equatable { let id: String; let top: CGFloat; let height: CGFloat }
    var rows: [Row] {
        var cuts: [(String, CGFloat)] = [("note", 0)]
        if let offer { cuts += [("offersPlate", offer.top - 69.4), ("offerCard", offer.top)] }
        cuts.append(("bundlesPlate", bundlesPlate))
        for (i, b) in bundles.enumerated() { cuts.append(("bundle.\(i)", b.top - 1.0)) }
        cuts.append(("coinsPlate", coinsPlate - 8.5))
        for r in stride(from: 0, to: coins.count, by: 3) { cuts.append(("coins.\(r / 3)", coins[r].top)) }
        return cuts.enumerated().map { i, c in
            let next = i + 1 < cuts.count ? cuts[i + 1].1 : height
            return Row(id: c.0, top: c.1, height: max(0, next - c.1))
        }
    }
}

private struct ShopContent: View {
    let layout: ShopLayout
    let prices: [String: String]
    let buying: String?
    var lazy = true
    var scale: CGFloat = 1
    let buy: (ShopProduct) -> Void

    var body: some View {
        if lazy {
            LazyVStack(spacing: 0) { rows }.scrollTargetLayout()
        } else {
            VStack(spacing: 0) { rows }
        }
    }

    @ViewBuilder private var rows: some View {
        ForEach(layout.rows) { row in
            ShopRow(row: row, layout: layout, prices: prices, buying: buying, buy: buy)
                .frame(width: 393, height: row.height, alignment: .topLeading)
                .scaleEffect(scale, anchor: .topLeading)
                .frame(width: 393 * scale, height: row.height * scale, alignment: .topLeading)
                .id(row.id)
        }
    }
}

/// One row: its piece of the section grounds and the elements that start in it (drawn in the row's local coordinates; the
/// Special Offer's seal overhangs the row above and is drawn after it).
private struct ShopRow: View {
    let row: ShopLayout.Row
    let layout: ShopLayout
    let prices: [String: String]
    let buying: String?
    let buy: (ShopProduct) -> Void
    @Environment(AppModel.self) private var app

    var body: some View {
        let rules = ShellEconomy.rules(app)
        ZStack(alignment: .topLeading) {
            ground(Skin.shopShopViewShopRowGround, from: 0, to: layout.purpleEnd)
            ground(Skin.shopShopViewShopRowGroundV2, from: layout.purpleEnd, to: layout.navyEnd)
            ground(Skin.shopShopViewShopRowGroundV3, from: layout.navyEnd, to: layout.height)
            content(rules)
        }
    }

    /// The part of a section ground inside this row.
    @ViewBuilder private func ground(_ hex: UInt32, from a: CGFloat, to b: CGFloat) -> some View {
        let lo = max(a, row.top), hi = min(b, row.top + row.height)
        if hi > lo { Color(hex: hex).frame(width: 393, height: hi - lo).offset(y: lo - row.top) }
    }

    @ViewBuilder private func content(_ rules: EconomyRules) -> some View {
        let id = row.id
        if id == "note" {
            #if DEBUG
            if layout.testStore { TestStoreNote().placed(CGRect(31.5, layout.noteY, 330, 26)) }
            #endif
        } else if id == "offersPlate" {
            ShopStatic(key: "plate|offers") { SectionPlate(kind: .purple, title: "Special Offers") }.placed(CGRect(0, 0, 393, 60))
        } else if id == "offerCard", let o = layout.offer?.product {
            ShopStatic(key: "card|\(o.id)", overflow: 16) { OfferCard(product: o, price: "", buying: false, showPrice: false) {} }
                .placed(CGRect(4.0, 0, 381.7, 199.8))
            tag(o, rules, size: 24.4, CGRect(232.9, 317.9 - 190.2, 130.1, 48.4))
        } else if id == "bundlesPlate" {
            ShopStatic(key: "plate|bundles") { SectionPlate(kind: .blue, title: "Bundles") }.placed(CGRect(0, 0, 393, 60))
        } else if id.hasPrefix("bundle."), let i = Int(id.dropFirst(7)), layout.bundles.indices.contains(i) {
            let b = layout.bundles[i].product
            ShopStatic(key: "card|\(b.id)", overflow: 10) { BundleCard(product: b, price: "", buying: false, showPrice: false) {} }
                .placed(CGRect(4.7, 0, 384.3, 199.5))
            tag(b, rules, size: 24.8, CGRect(232.9, 123.0, 130.1, 48.7))
        } else if id == "coinsPlate" {
            ShopStatic(key: "plate|coins") { SectionPlate(kind: .yellow, title: "Coins") }.placed(CGRect(0, 0, 393, 60))
        } else if id.hasPrefix("coins."), let r = Int(id.dropFirst(6)) {
            let x: [CGFloat] = [9.7, 137.8, 266.0]
            ForEach(Array(layout.coins.indices.filter { $0 / 3 == r }), id: \.self) { i in
                let p = layout.coins[i].product
                ShopStatic(key: "card|\(p.id)", overflow: 4) { CoinTile(product: p, index: i, price: "", buying: false, showPrice: false) {} }
                    .placed(CGRect(x[i % 3], 0, 117.4, 163.5))
                tag(p, rules, size: 19.9, CGRect(x[i % 3] + 14.0, 108.0, 90.4, 44.0))
            }
        }
    }

    private func tag(_ p: ShopProduct, _ rules: EconomyRules, size: CGFloat, _ r: CGRect) -> some View {
        // the store's displayPrice or nothing: nil draws the disabled "…" well (A1: no hard-coded fallback price)
        PriceTag(id: "shop.product.\(p.id)", price: ShopPrices.label(for: rules.shop.storeID(p), in: prices), size: size,
                 buying: buying == rules.shop.storeID(p)) { buy(p) }
            .placed(r)
    }
}

/// A static card / plate composition rendered ONCE into one image (RasterCache, keyed by the language: the titles are copy) —
/// the Shop's content is ~150 views; as ~20 images + the live price buttons a tab switch builds in one frame.
private struct ShopStatic<Content: View>: View {
    let key: String
    var overflow: CGFloat = 0
    @ViewBuilder var content: () -> Content
    var body: some View {
        let lang = Bundle.main.preferredLocalizations.first ?? "en"
        let scale = UIScreen.main.scale
        Rasterized("shopStatic|\(key)|\(lang)", overflow: overflow) { _ in
            content().environment(\.displayScale, scale)
        }
    }
}

#if DEBUG
/// The DEBUG FakeStore's honest chip (15 pt white, outline #022880, on a #0B2176 α 0.92 chip rr 12, 330 × 26; SPEC-ui §2.12.3).
/// A1 (T1-changes: dropped from the catalogue): verbatim English, compiled into DEBUG builds only — a Release build has no
/// test store, so neither the chip nor its text exists there (release gate G8).
private struct TestStoreNote: View {
    static let text = "Test store: nothing is charged"
    var body: some View {
        let st = GameTextStyle.s2(15, 0, [Skin.shopShopViewTestStoreNoteSt0], outline: Skin.shopShopViewTestStoreNoteStOutline, 1.0, drop: 0.8)
        ZStack {
            RoundedRectangle(cornerRadius: 12).fill(Color(hex: Skin.shopShopViewTestStoreNoteFill, 0.92))
            RoundedRectangle(cornerRadius: 12).stroke(Color(hex: Skin.shopShopViewTestStoreNoteStroke, 0.6), lineWidth: 1)
            GameText(verbatim: Self.text, style: st, maxWidth: 310)
        }
        .accessibilityElement()
        .accessibilityIdentifier("shop.testStoreNote")
        .accessibilityLabel(Text(verbatim: Self.text))
    }
}
#endif

// MARK: - section plates

private struct SectionPlate: View {
    enum Kind { case purple, blue, yellow }
    let kind: Kind
    let title: LocalizedStringResource

    var body: some View {
        // the plate frame, relative to this 393 × 60 block (VERIFIED meta-012 / meta-011): purple 60.1 · 120.8 − 69.4 …
        let plate: CGRect = {
            switch kind {
            case .purple: return CGRect(60.1, 0.0, 273.6, 57.0)
            case .blue: return CGRect(60.1, 0.0, 273.6, 58.4)
            case .yellow: return CGRect(69.4, 8.5, 254.5, 43.0)
            }
        }()
        let rail: CGRect = kind == .yellow ? CGRect(0, 16.7, 393, 26.7) : CGRect(0, 12.6, 393, 26.7)
        let style: GameTextStyle = {
            switch kind {
            case .purple: return .s2(27.6, -0.24, [Skin.shopShopViewSectionPlateStylePurple0], outline: Skin.shopShopViewSectionPlateStylePurpleOutline, 1.91, drop: 1.01)
            case .blue: return .s2(28.1, -0.72, [Skin.shopShopViewSectionPlateStyleBlue0], outline: Skin.shopShopViewSectionPlateStyleBlueOutline, 1.09, drop: 1.02)
            case .yellow: return .s2(27.6, 0.18, [Skin.shopShopViewSectionPlateStyleYellow0, Skin.shopShopViewSectionPlateStyleYellow1, Skin.shopShopViewSectionPlateStyleYellow2], outline: Skin.shopShopViewSectionPlateStyleYellowOutline, 1.86, drop: 1.03)
            }
        }()
        let baseline: CGFloat = kind == .purple ? 157.1 - 120.8 : (kind == .blue ? 442.7 - 403.7 : 386.7 - 355.3 + 8.5)
        ZStack(alignment: .topLeading) {
            SectionRail(kind: kind).placed(rail)
            SectionPlateFace(kind: kind).placed(plate)
            GameText(title, style: style, maxWidth: plate.width - 40).at(196.8, style.capCentre(baseline: baseline))
                .accessibilityAddTraits(.isHeader)
        }
        .frame(width: 393, height: 60, alignment: .topLeading)
    }
}

private struct SectionRail: View {
    let kind: SectionPlate.Kind
    var body: some View {
        let c: [UInt32] = {
            switch kind {
            case .purple: return [Skin.shopShopViewSectionRailCPurple0, Skin.shopShopViewSectionRailCPurple1, Skin.shopShopViewSectionRailCPurple2, Skin.shopShopViewSectionRailCPurple3, Skin.shopShopViewSectionRailCPurple4]
            case .blue: return [Skin.shopShopViewSectionRailCBlue0, Skin.shopShopViewSectionRailCBlue1, Skin.shopShopViewSectionRailCBlue2, Skin.shopShopViewSectionRailCBlue3, Skin.shopShopViewSectionRailCBlue4]
            case .yellow: return [Skin.shopShopViewSectionRailCYellow0, Skin.shopShopViewSectionRailCYellow1, Skin.shopShopViewSectionRailCYellow2, Skin.shopShopViewSectionRailCYellow3, Skin.shopShopViewSectionRailCYellow4]
            }
        }()
        Rasterized("shopRail|\(c[2])") { size in
            ZStack(alignment: .topLeading) {
                Color(hex: c[0])
                Color(hex: c[1]).frame(height: 3).offset(y: 1)
                Color(hex: c[2]).frame(height: size.height - 7).offset(y: 3.5)
                Color(hex: c[3]).frame(height: 2).offset(y: size.height - 2)
                ForEach([31.0, 362.0], id: \.self) { x in
                    Circle().fill(Color(hex: c[3])).frame(width: 14.5, height: 14.5).position(x: x, y: size.height / 2)
                    Circle().fill(RadialGradient(colors: [Color.white.opacity(0.7), Color(hex: c[4])], center: UnitPoint(x: 0.4, y: 0.35),
                                                 startRadius: 0, endRadius: 7))
                        .frame(width: 13, height: 13).position(x: x, y: size.height / 2)
                }
            }
        }
    }
}

private struct SectionPlateFace: View {
    let kind: SectionPlate.Kind
    var body: some View {
        let r: CGFloat = kind == .purple ? 19.8 : (kind == .blue ? 15.4 : 8.8)
        let c: [UInt32] = {
            switch kind {
            case .purple: return [Skin.shopShopViewSectionPlateFaceCPurple0, Skin.shopShopViewSectionPlateFaceCPurple1, Skin.shopShopViewSectionPlateFaceCPurple2, Skin.shopShopViewSectionPlateFaceCPurple3, Skin.shopShopViewSectionPlateFaceCPurple4]
            case .blue: return [Skin.shopShopViewSectionPlateFaceCBlue0, Skin.shopShopViewSectionPlateFaceCBlue1, Skin.shopShopViewSectionPlateFaceCBlue2, Skin.shopShopViewSectionPlateFaceCBlue3, Skin.shopShopViewSectionPlateFaceCBlue4]
            case .yellow: return [Skin.shopShopViewSectionPlateFaceCYellow0, Skin.shopShopViewSectionPlateFaceCYellow1, Skin.shopShopViewSectionPlateFaceCYellow2, Skin.shopShopViewSectionPlateFaceCYellow3, Skin.shopShopViewSectionPlateFaceCYellow4]
            }
        }()
        Rasterized("shopPlate|\(c[3])|\(r)", overflow: 2) { size in
            ZStack {
                RoundedRectangle(cornerRadius: r).fill(Color(hex: c[0])).offset(y: 2)
                RoundedRectangle(cornerRadius: r).fill(Color(hex: c[0]))
                RoundedRectangle(cornerRadius: r - 1).fill(Color(hex: c[1])).padding(1)
                RoundedRectangle(cornerRadius: r - 2)
                    .fill(LinearGradient(colors: [Color(hex: c[2]), Color(hex: c[3]), Color(hex: c[4])], startPoint: .top, endPoint: .bottom))
                    .padding(EdgeInsets(top: 2.5, leading: 2, bottom: 3, trailing: 2))
            }
        }
    }
}

// MARK: - cards

/// The price button (green, se n 4.9; `role.shopPrice` 24.4 / −0.2 white outlined #066A01; box 110). `price` nil = StoreKit has
/// not priced this product yet: a disabled button showing "…" (A1, release-plan §2.5 S-3).
private struct PriceTag: View {
    let id: String
    let price: String?
    let size: CGFloat
    let buying: Bool
    let action: () -> Void
    var body: some View {
        let st = GameTextStyle.s2(size, -0.2, [Skin.shopShopViewPriceTagSt0], outline: Skin.shopShopViewPriceTagStOutline, 1.08 * size / 24.4, drop: 1.2 * size / 24.4)
        GameButton(id: id, label: "Shop", value: price ?? ShopPrices.pending, enabled: !buying && price != nil, action: action) {
            ZStack {
                ChromeButtonFace(colors: .green, n: 4.9)
                GameText(verbatim: price ?? ShopPrices.pending, style: st, maxWidth: size > 21 ? 112 : 80).offset(y: -1)
            }
            .opacity(buying || price == nil ? 0.7 : 1)
        }
    }
}

/// The Shop's price labels: the store's `displayPrice` for a product id, or nil (drawn as the disabled `pending` well). There is
/// deliberately no other source of a price in the app (A1; StoreReleaseTests pins it).
enum ShopPrices {
    static let pending = "\u{2026}"
    static func label(for storeID: String, in prices: [String: String]) -> String? {
        guard let p = prices[storeID], !p.isEmpty else { return nil }
        return p
    }
}

private struct OfferCard: View {
    let product: ShopProduct
    let price: String
    let buying: Bool
    var showPrice = true
    let action: () -> Void

    /// The card's frame origin on meta-012; every part below is measured there.
    static let origin = CGPoint(x: 4.0, y: 190.2)
    private func r(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat) -> CGRect {
        CGRect(x - Self.origin.x, y - Self.origin.y, w, h)
    }

    var body: some View {
        let o = OfferCard.origin
        let amount = GameTextStyle.s2(30.7, -0.34, [Skin.shopShopViewOfferCardAmount0, Skin.shopShopViewOfferCardAmount1, Skin.shopShopViewOfferCardAmount2], outline: Skin.shopShopViewOfferCardAmountOutline, 2.24, drop: 0.97)
        let name = GameTextStyle.s2(28.0, -0.25, [Skin.shopShopViewOfferCardName0], outline: Skin.shopShopViewOfferCardNameOutline, 1.9, drop: 1.4)
        ZStack(alignment: .topLeading) {
            OfferCardFrame()
            ArtImage(art: .shopBundleSpecial).placed(r(16, 200, 176, 102))
            GameText(verbatim: ShopFormat.amount(product.grant.coins), style: amount).at(135.8 - o.x, amount.capCentre(baseline: 299.2) - o.y)
            ItemsTile(boosters: product.grant.boosters, gold: true).placed(r(196.2, 211.8, 105.8, 91.1))
            HeartTile(seconds: product.grant.unlimitedLives, gold: true).placed(r(307.9, 211.8, 59.4, 91.1))
            LeftText(text: String(localized: ShopTitles.title(product)), style: name, left: 26.7 - o.x, baseline: 350.9 - o.y, box: 200)
            if showPrice {
                PriceTag(id: "shop.product.\(product.id)", price: price, size: 24.4, buying: buying, action: action)
                    .placed(r(232.9, 317.9, 130.1, 48.4))
            }
            // A1: the STARTER ribbon over the card's top-left corner (the old 66 pt seal sat at 1.4 · 183.3)
            StarterRibbon().placed(r(3.0, 190.0, StarterRibbon.size.width, StarterRibbon.size.height))
        }
        .frame(width: 381.7, height: 199.8, alignment: .topLeading)
    }
}

/// The Special Offer card's frame (FIX-V2 F-06, re-measured on meta-012; local = meta-012 − (4.0, 190.2)): the card is
/// x 8.5 → 384.8, y 195.4 → 388.8 (the seal overhangs it); a gold bevel rim, light inside → dark outside (sides 7 pt, top
/// 5 pt, bottom 10.5 pt) inside a soft dark halo; a 0.5 pt dark line; the gold field (#FEC006 → #FDA504, an orange top
/// bevel + a #FEE409 highlight line) to 304.5; a 4 pt orange ledge #CF6902 → #A03401; the purple strip 308.8 → 373
/// (#6C0AB1 line, #C67DFD highlight, #B55FF5 → #8300CD) with a dark foot #7100B6 → #390065 to 377.6; and the price
/// button's recessed well (#5A009C, 1.7 pt round the button, a 0.8 pt #B050F4 lip). Was: a 199.8 pt card whose strip ran
/// 336 → 384 (SPEC-ui's number), a brown #B95503 rim band and no well.
private struct OfferCardFrame: View {
    private static let o = CGPoint(x: 4.0, y: 190.2)
    private func r(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat) -> CGRect { CGRect(x - Self.o.x, y - Self.o.y, w, h) }

    var body: some View {
        Rasterized("offerCardFrame.v2", overflow: 4) { _ in
            let card = r(8.5, 195.4, 376.3, 193.4)
            // the bevel rim as 8 rounded rings: outer dark → inner light (top 5/7, bottom 10.5/7 of the side step)
            let rim: [UInt32] = [Skin.shopShopViewOfferCardFrameRim0, Skin.shopShopViewOfferCardFrameRim1, Skin.shopShopViewOfferCardFrameRim2, Skin.shopShopViewOfferCardFrameRim3, Skin.shopShopViewOfferCardFrameRim4, Skin.shopShopViewOfferCardFrameRim5, Skin.shopShopViewOfferCardFrameRim6, Skin.shopShopViewOfferCardFrameRim7]
            let field = r(16.4, 200.9, 360.8, 176.9)        // inside the 0.5 pt dark line
            let fieldShape = RoundedRectangle(cornerRadius: 16.5, style: .continuous)
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 27, style: .continuous).fill(Color(hex: Skin.shopShopViewOfferCardFrameFill))
                    .frame(width: card.width + 5, height: card.height + 5).blur(radius: 2)
                    .offset(x: card.minX - 2.5, y: card.minY - 1.5)
                ForEach(Array(rim.enumerated()), id: \.offset) { i, hex in
                    let k = CGFloat(i) * 7.0 / 8.0
                    RoundedRectangle(cornerRadius: max(17, 24 - k), style: .continuous).fill(Color(hex: hex))
                        .frame(width: card.width - 2 * k, height: card.height - k * (5.0 + 10.5) / 7)
                        .offset(x: card.minX + k, y: card.minY + k * 5.0 / 7)
                }
                RoundedRectangle(cornerRadius: 17, style: .continuous).fill(Color(hex: Skin.shopShopViewOfferCardFrameFillV2))
                    .frame(width: field.width + 1, height: field.height + 1).offset(x: field.minX - 0.5, y: field.minY - 0.5)
                ZStack(alignment: .topLeading) {
                    // gold field with its sunburst, the orange top bevel and the highlight line
                    ZStack {
                        LinearGradient(stops: [.init(color: Color(hex: Skin.shopShopViewOfferCardFrameStops0), location: 0), .init(color: Color(hex: Skin.shopShopViewOfferCardFrameStops1), location: 0.35),
                                               .init(color: Color(hex: Skin.shopShopViewOfferCardFrameStops2), location: 0.8), .init(color: Color(hex: Skin.shopShopViewOfferCardFrameStops3), location: 1)],
                                       startPoint: .top, endPoint: .bottom)
                        SunburstRays(centre: CGPoint(x: 100, y: 55), rays: 20, colour: Color(hex: Skin.shopShopViewOfferCardFrameColour)).opacity(0.55)
                    }
                    .frame(width: field.width, height: 304.5 - 200.9)
                    LinearGradient(colors: [Color(hex: Skin.shopShopViewOfferCardFrameColors0), Color(hex: Skin.shopShopViewOfferCardFrameColors1), Color(hex: Skin.shopShopViewOfferCardFrameColors2)], startPoint: .top, endPoint: .bottom)
                        .frame(width: field.width, height: 1.5)
                    Color(hex: Skin.shopShopViewOfferCardFrame).frame(width: field.width, height: 0.8).offset(y: 1.6)
                    // the ledge
                    LinearGradient(colors: [Color(hex: Skin.shopShopViewOfferCardFrameColors0V2), Color(hex: Skin.shopShopViewOfferCardFrameColors1V2), Color(hex: Skin.shopShopViewOfferCardFrameColors2V2), Color(hex: Skin.shopShopViewOfferCardFrameColors3)],
                                   startPoint: .top, endPoint: .bottom)
                        .frame(width: field.width, height: 308.8 - 304.5).offset(y: 304.5 - 200.9)
                    // the purple strip + its dark foot
                    LinearGradient(stops: [.init(color: Color(hex: Skin.shopShopViewOfferCardFrameStops0V2), location: 0), .init(color: Color(hex: Skin.shopShopViewOfferCardFrameStops1V2), location: 0.17),
                                           .init(color: Color(hex: Skin.shopShopViewOfferCardFrameStops2V2), location: 0.39), .init(color: Color(hex: Skin.shopShopViewOfferCardFrameStops3V2), location: 0.59),
                                           .init(color: Color(hex: Skin.shopShopViewOfferCardFrameStops4), location: 0.78), .init(color: Color(hex: Skin.shopShopViewOfferCardFrameStops5), location: 1)],
                                   startPoint: .top, endPoint: .bottom)
                        .frame(width: field.width, height: 373.0 - 308.8).offset(y: 308.8 - 200.9)
                    Color(hex: Skin.shopShopViewOfferCardFrameV2).frame(width: field.width, height: 0.7).offset(y: 308.8 - 200.9)
                    Color(hex: Skin.shopShopViewOfferCardFrameV3).frame(width: field.width, height: 1.1).offset(y: 309.5 - 200.9)
                    LinearGradient(colors: [Color(hex: Skin.shopShopViewOfferCardFrameColors0V3), Color(hex: Skin.shopShopViewOfferCardFrameColors1V3), Color(hex: Skin.shopShopViewOfferCardFrameColors2V3), Color(hex: Skin.shopShopViewOfferCardFrameColors3V2)],
                                   startPoint: .top, endPoint: .bottom)
                        .frame(width: field.width, height: 377.6 - 373.0).offset(y: 373.0 - 200.9)
                }
                .frame(width: field.width, height: field.height, alignment: .topLeading)
                .clipShape(fieldShape)
                .offset(x: field.minX, y: field.minY)
                // the price button's recessed well (the live PriceTag sits in it at 232.9 · 317.9 · 130.1 · 48.4)
                let lip = r(230.0, 314.6, 135.9, 55.5), well = r(230.8, 315.4, 134.3, 53.9)
                Superellipse(n: 4.9).fill(Color(hex: Skin.shopShopViewOfferCardFrameFillV3)).frame(width: lip.width, height: lip.height).offset(x: lip.minX, y: lip.minY)
                Superellipse(n: 4.9).fill(Color(hex: Skin.shopShopViewOfferCardFrameFillV4)).frame(width: well.width, height: well.height).offset(x: well.minX, y: well.minY)
            }
        }
    }
}

/// The Special Offer's "STARTER" ribbon (A1; ruling 38: an honest label instead of the original's "90% OFF" seal, release-plan
/// §10.5). ONE catalogue key drawn in ONE run (the old seal split its key at the first space into two runs in a 46 pt box);
/// T1: the widest of the 13 languages needs a text box of at least 95 pt at about 15 pt, so the round 66 pt seal became a red
/// swallowtail ribbon with a gold rim (text box 98 pt at 15.5 pt), pinned across the card's top-left corner at −9°.
struct StarterRibbon: View {
    static let size = CGSize(width: 136, height: 40)
    static let textBox: CGFloat = 98
    static let textSize: CGFloat = 15.5
    static let angle: Double = -9
    var body: some View {
        let st = GameTextStyle.s2(Self.textSize, 0.4, [Skin.shopShopViewStarterRibbonSt0, Skin.shopShopViewStarterRibbonSt1, Skin.shopShopViewStarterRibbonSt2], outline: Skin.shopShopViewStarterRibbonStOutline, 0.95, drop: 0.6)
        ZStack {
            Rasterized("starterRibbon.v1", overflow: 3) { size in StarterRibbonShape(size: size) }
            GameText("STARTER", style: st, maxWidth: Self.textBox).offset(y: -1.5)
        }
        .frame(width: Self.size.width, height: Self.size.height)
        .rotationEffect(.degrees(Self.angle))
        .accessibilityElement()
        .accessibilityIdentifier("shop.offer.starter")
        .accessibilityLabel(Text("STARTER"))
    }
}

/// The ribbon: two folded swallowtail ends (dark red, behind, 6 pt lower) and the band (a red gradient, a 2 pt gold rim, a
/// soft top highlight), drawn once into an image.
private struct StarterRibbonShape: View {
    let size: CGSize
    var body: some View {
        let w = size.width, h = size.height
        let band = CGRect(x: 14, y: 3, width: w - 28, height: h - 12)
        let tailW: CGFloat = 22, tailH = band.height - 6, notch: CGFloat = 7
        func tail(_ left: Bool) -> Path {
            Path { p in
                let x0 = left ? 0 : w, x1 = left ? tailW : w - tailW, y0 = band.minY + 9, y1 = y0 + tailH
                p.move(to: CGPoint(x: x1, y: y0)); p.addLine(to: CGPoint(x: x0, y: y0))
                p.addLine(to: CGPoint(x: x0 + (left ? notch : -notch), y: (y0 + y1) / 2)); p.addLine(to: CGPoint(x: x0, y: y1))
                p.addLine(to: CGPoint(x: x1, y: y1)); p.closeSubpath()
            }
        }
        return ZStack(alignment: .topLeading) {
            ForEach([true, false], id: \.self) { left in
                tail(left).fill(LinearGradient(colors: [Color(hex: Skin.shopShopViewStarterRibbonShapeColors0), Color(hex: Skin.shopShopViewStarterRibbonShapeColors1)], startPoint: .top, endPoint: .bottom))
                tail(left).stroke(Color(hex: Skin.shopShopViewStarterRibbonShapeStroke), lineWidth: 1.4)
                // the fold: a dark wedge where the band turns under
                Path { p in
                    let x = left ? band.minX : band.maxX, d: CGFloat = left ? 1 : -1
                    p.move(to: CGPoint(x: x, y: band.maxY)); p.addLine(to: CGPoint(x: x + d * 8, y: band.maxY))
                    p.addLine(to: CGPoint(x: x + d * 8, y: band.maxY + 6)); p.closeSubpath()
                }.fill(Color(hex: Skin.shopShopViewStarterRibbonShapeFill))
            }
            RoundedRectangle(cornerRadius: 5).fill(Color(hex: Skin.shopShopViewStarterRibbonShapeFill, 0.35)).frame(width: band.width, height: band.height)
                .offset(x: band.minX, y: band.minY + 1.5).blur(radius: 1.2)
            RoundedRectangle(cornerRadius: 5)
                .fill(LinearGradient(stops: [.init(color: Color(hex: Skin.shopShopViewStarterRibbonShapeStops0), location: 0), .init(color: Color(hex: Skin.shopShopViewStarterRibbonShapeStops1), location: 0.45),
                                             .init(color: Color(hex: Skin.shopShopViewStarterRibbonShapeStops2), location: 1)], startPoint: .top, endPoint: .bottom))
                .frame(width: band.width, height: band.height).offset(x: band.minX, y: band.minY)
            RoundedRectangle(cornerRadius: 5)
                .stroke(LinearGradient(colors: [Color(hex: Skin.shopShopViewStarterRibbonShapeColors0V2), Color(hex: Skin.shopShopViewStarterRibbonShapeColors1V2), Color(hex: Skin.shopShopViewStarterRibbonShapeColors2)], startPoint: .top,
                                       endPoint: .bottom), lineWidth: 2)
                .frame(width: band.width - 2, height: band.height - 2).offset(x: band.minX + 1, y: band.minY + 1)
            Capsule().fill(Color.white.opacity(0.28)).frame(width: band.width - 16, height: 3).offset(x: band.minX + 8, y: band.minY + 4)
        }
        .frame(width: w, height: h, alignment: .topLeading)
    }
}

private struct BundleCard: View {
    let product: ShopProduct
    let price: String
    let buying: Bool
    var showPrice = true
    let action: () -> Void

    var body: some View {
        // local frame = the card (7.7 · top · 378.3 · 194.5) offset by (−3, −1) to leave room for the shadow
        let dx: CGFloat = 3.0, dy: CGFloat = 1.0
        let amount = GameTextStyle.s2(30.7, -0.34, [Skin.shopShopViewBundleCardAmount0, Skin.shopShopViewBundleCardAmount1, Skin.shopShopViewBundleCardAmount2], outline: Skin.shopShopViewBundleCardAmountOutline, 2.24, drop: 0.97)
        let name = GameTextStyle.s2(27.8, 0, [Skin.shopShopViewBundleCardName0], outline: Skin.shopShopViewBundleCardNameOutline, 1.8, drop: 1.8)
        let amountText = ShopFormat.amount(product.grant.coins)
        let al = GameTextLayout.make(amountText, postScriptName: amount.postScriptName, size: amount.size, tracking: amount.tracking)
        ZStack(alignment: .topLeading) {
            BundleCardFrame().placed(CGRect(dx, dy, 378.3, 194.5))
            ArtImage(art: BundleCard.art(product.id)).placed(CGRect(16 - 7.7 + dx, 7.7 + dy, 176, 102))
            GameText(verbatim: amountText, style: amount)
                .at(177 - 7.7 + dx - al.advance / 2, amount.capCentre(baseline: 105) + dy)
            ItemsTile(boosters: product.grant.boosters, gold: false).placed(CGRect(196.2 - 7.7 + dx, 16 + dy, 105.8, 91.1))
            HeartTile(seconds: product.grant.unlimitedLives, gold: false).placed(CGRect(307.9 - 7.7 + dx, 16 + dy, 59.4, 91.1))
            LeftText(text: String(localized: ShopTitles.title(product)), style: name, left: 26.7 - 7.7 + dx, baseline: 155.0 + dy, box: 200)
            if showPrice {
                PriceTag(id: "shop.product.\(product.id)", price: price, size: 24.8, buying: buying, action: action)
                    .placed(CGRect(232.9 - 7.7 + dx, 122 + dy, 130.1, 48.7))
            }
            if let badge = product.badge, badge == "Popular" || badge == "Best Value" {
                CornerSash(text: badge == "Popular" ? "Popular" : "Best Value").placed(CGRect(5.0 - 7.7 + dx, -1 + dy, 87.4, 85.7))
            }
        }
        .frame(width: 384.3, height: 199.5, alignment: .topLeading)
    }

    /// Art ruling 4 (art/REVIEW.md): Mini bag · Epic barrel · Elite chest · Mega safe · Legendary cart.
    static func art(_ id: String) -> UIArt {
        switch id {
        case "bundle.mini": return .shopBundleMini
        case "bundle.epic": return .shopBundleEpic
        case "bundle.elite": return .shopBundleElite
        case "bundle.mega": return .shopBundleMega
        default: return .shopBundleLegendary
        }
    }
}

/// The bundle card: frame #0241B3 (outer highlight #008EE3), cream top 17 → 109.9 (#F8E9DD → #F8E1CE, faint sunburst), a
/// #AA5D44 seam, the blue name strip 115.8 → 175.3 (#00B1FF, top highlight #7AD1FF); rr 29.6 (VERIFIED meta-012).
private struct BundleCardFrame: View {
    var body: some View {
        Rasterized("bundleCardFrame", overflow: 3) { size in
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 29.6).fill(Color(hex: Skin.shopShopViewBundleCardFrameFill)).offset(y: 3)
                RoundedRectangle(cornerRadius: 29.6).fill(LinearGradient(colors: [Color(hex: Skin.shopShopViewBundleCardFrameColors0), Color(hex: Skin.shopShopViewBundleCardFrameColors1)],
                                                                          startPoint: .top, endPoint: .bottom))
                RoundedRectangle(cornerRadius: 26).fill(Color(hex: Skin.shopShopViewBundleCardFrameFillV2)).padding(3)
                ZStack {
                    LinearGradient(colors: [Color(hex: Skin.shopShopViewBundleCardFrameColors0V2), Color(hex: Skin.shopShopViewBundleCardFrameColors1V2)], startPoint: .top, endPoint: .bottom)
                    SunburstRays(centre: CGPoint(x: 90, y: 45), rays: 20).opacity(0.5)
                }
                .frame(width: size.width - 18, height: 92.9)
                .clipShape(UnevenRoundedRectangle(topLeadingRadius: 18, bottomLeadingRadius: 0, bottomTrailingRadius: 0, topTrailingRadius: 18))
                .offset(x: 9, y: 17)
                Color(hex: Skin.shopShopViewBundleCardFrame).frame(width: size.width - 18, height: 1).offset(x: 9, y: 109.9)
                Color(hex: Skin.shopShopViewBundleCardFrameV2).frame(width: size.width - 18, height: 4.5).offset(x: 9, y: 110.9)
                ZStack(alignment: .top) {
                    Color(hex: Skin.shopShopViewBundleCardFrameV3)
                    Color(hex: Skin.shopShopViewBundleCardFrameV4).frame(height: 2.5)
                }
                .frame(width: size.width - 18, height: 59.5)
                .clipShape(UnevenRoundedRectangle(topLeadingRadius: 0, bottomLeadingRadius: 18, bottomTrailingRadius: 18, topTrailingRadius: 0))
                .offset(x: 9, y: 115.8)
            }
        }
    }
}

/// The boosters tile: the bulb + the hourglass at 30 pt over "xN" (gold tile #FCA800 / #FC8800 strip on the Special Offer; cream
/// #F5DECC / #E8C2AA strip on the bundles).
private struct ItemsTile: View {
    let boosters: [String: Int]
    let gold: Bool
    var body: some View {
        let n = boosters.values.max() ?? 0
        let st = gold ? GameTextStyle.s2(20.5, -1.0, [Skin.shopShopViewItemsTileSt0, Skin.shopShopViewItemsTileSt1, Skin.shopShopViewItemsTileSt2], outline: Skin.shopShopViewItemsTileStOutline, 1.4, drop: 0.71)
                      : GameTextStyle.s2(18.5, 0.03, [Skin.shopShopViewItemsTile0, Skin.shopShopViewItemsTile1, Skin.shopShopViewItemsTile2], outline: Skin.shopShopViewItemsTileOutline, 1.59, drop: 0.97)
        ZStack(alignment: .topLeading) {
            ShopTileFace(gold: gold, radius: gold ? 12.8 : 11.2)
            ArtImage(art: .boosterHintIcon).placed(CGRect(18.0, 13.0, 34, 34))
            ArtImage(art: .boosterFreezeIcon).placed(CGRect(56.5, 13.0, 34, 34))
            GameText(verbatim: "x\(n)", style: st).at(53.2, st.capCentre(baseline: 83.0))
        }
        .frame(width: 105.8, height: 91.1, alignment: .topLeading)
    }
}

private struct HeartTile: View {
    let seconds: Double
    let gold: Bool
    var body: some View {
        let st = gold ? GameTextStyle.s2(20.1, 0.5, [Skin.shopShopViewHeartTileSt0, Skin.shopShopViewHeartTileSt1, Skin.shopShopViewHeartTileSt2], outline: Skin.shopShopViewHeartTileStOutline, 1.4, drop: 0.71)
                      : GameTextStyle.s2(18.5, 0.03, [Skin.shopShopViewHeartTile0, Skin.shopShopViewHeartTile1, Skin.shopShopViewHeartTile2], outline: Skin.shopShopViewHeartTileOutline, 1.59, drop: 0.97)
        ZStack(alignment: .topLeading) {
            ShopTileFace(gold: gold, radius: gold ? 12.8 : 11.2)
            ArtImage(art: .livesUnlimitedSmall).placed(CGRect(7.7, 9.0, 44, 40))
            GameText(verbatim: ShopFormat.duration(seconds), style: st, maxWidth: 52).at(29.7, st.capCentre(baseline: 83.3))
        }
        .frame(width: 59.4, height: 91.1, alignment: .topLeading)
    }
}

private struct ShopTileFace: View {
    let gold: Bool
    let radius: CGFloat
    var body: some View {
        Rasterized("shopTile|\(gold)|\(radius)", overflow: 1) { size in
            let face: UInt32 = gold ? Skin.shopShopViewShopTileFaceFaceGold : Skin.shopShopViewShopTileFaceFaceNotGold, strip: UInt32 = gold ? Skin.shopShopViewShopTileFaceXFCA800Gold : Skin.shopShopViewShopTileFaceXFCA800NotGold
            let rim: UInt32 = gold ? Skin.shopShopViewShopTileFaceRimGold : Skin.shopShopViewShopTileFaceRimNotGold
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: radius).fill(Color(hex: rim))
                RoundedRectangle(cornerRadius: radius - 1).fill(Color(hex: face)).padding(1.2)
                Color(hex: strip).frame(width: size.width - 2.4, height: 30)
                    .clipShape(UnevenRoundedRectangle(topLeadingRadius: 0, bottomLeadingRadius: radius - 1, bottomTrailingRadius: radius - 1,
                                                      topTrailingRadius: 0))
                    .offset(x: 1.2, y: size.height - 31.2)
                Color(hex: rim).frame(width: size.width - 2.4, height: 1).offset(x: 1.2, y: size.height - 31.2)
            }
        }
    }
}

/// The purple diagonal sash across a card's top-left corner ("Popular" / "Best Value": 15 pt white outlined #5F1896, −45°).
private struct CornerSash: View {
    let text: LocalizedStringResource
    var body: some View {
        let st = GameTextStyle.s2(15, -0.2, [Skin.shopShopViewCornerSashSt0], outline: Skin.shopShopViewCornerSashStOutline, 1.1, drop: 0.6)
        ZStack {
            Rasterized("cornerSash", overflow: 1) { size in
                Path { p in
                    p.move(to: CGPoint(x: 0, y: size.height * 0.62)); p.addLine(to: CGPoint(x: size.width * 0.62, y: 0))
                    p.addLine(to: CGPoint(x: size.width, y: 0)); p.addLine(to: CGPoint(x: 0, y: size.height)); p.closeSubpath()
                }
                .fill(LinearGradient(colors: [Color(hex: Skin.shopShopViewCornerSashColors0), Color(hex: Skin.shopShopViewCornerSashColors1), Color(hex: Skin.shopShopViewCornerSashColors2)], startPoint: .topLeading,
                                     endPoint: .bottomTrailing))
                .overlay(Path { p in
                    p.move(to: CGPoint(x: 0, y: size.height)); p.addLine(to: CGPoint(x: size.width, y: 0))
                }.stroke(Color(hex: Skin.shopShopViewCornerSashStroke), lineWidth: 2.4))
            }
            GameText(text, style: st, maxWidth: 88).rotationEffect(.degrees(-45)).offset(x: -8, y: -8)
        }
    }
}

private struct CoinTile: View {
    let product: ShopProduct
    let index: Int
    let price: String
    let buying: Bool
    var showPrice = true
    let action: () -> Void

    var body: some View {
        let arts: [UIArt] = [.shopCoins1, .shopCoins2, .shopCoins3, .shopCoins4, .shopCoins5, .shopCoins6]
        let amount = GameTextStyle.s2(27.6, -0.42, [Skin.shopShopViewCoinTileAmount0], outline: Skin.shopShopViewCoinTileAmountOutline, 2.4, drop: 1.2)
        ZStack(alignment: .topLeading) {
            CoinTileFace()
            ArtImage(art: arts[min(index, arts.count - 1)]).placed(CGRect(7.7, 12.0, 102, 66))
            GameText(verbatim: ShopFormat.amount(product.grant.coins), style: amount, maxWidth: 108)
                .at(58.7, amount.capCentre(baseline: 92.8))
            if showPrice {
                PriceTag(id: "shop.product.\(product.id)", price: price, size: 19.9, buying: buying, action: action)
                    .placed(CGRect(14.0, 108.0, 90.4, 44.0))
            }
        }
        .frame(width: 117.4, height: 163.5, alignment: .topLeading)
    }
}

/// Cream top 93 pt with a white sunburst, the yellow bottom #FDC306 (rim #FCF201, a dark lip line).
private struct CoinTileFace: View {
    var body: some View {
        Rasterized("coinTileFace", overflow: 2) { size in
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 16).fill(Color(hex: Skin.shopShopViewCoinTileFaceFill)).offset(y: 2)
                RoundedRectangle(cornerRadius: 16).fill(Color(hex: Skin.shopShopViewCoinTileFaceFillV2))
                ZStack {
                    Color(hex: Skin.shopShopViewCoinTileFace)
                    SunburstRays(centre: CGPoint(x: size.width / 2, y: 40), rays: 18).opacity(0.7)
                }
                .frame(width: size.width - 3, height: 93)
                .clipShape(UnevenRoundedRectangle(topLeadingRadius: 15, bottomLeadingRadius: 0, bottomTrailingRadius: 0, topTrailingRadius: 15))
                .offset(x: 1.5, y: 1.5)
                ZStack(alignment: .top) {
                    Color(hex: Skin.shopShopViewCoinTileFaceV2)
                    Color(hex: Skin.shopShopViewCoinTileFaceV3).frame(height: 2.5)
                }
                .frame(width: size.width - 3, height: size.height - 96)
                .clipShape(UnevenRoundedRectangle(topLeadingRadius: 0, bottomLeadingRadius: 15, bottomTrailingRadius: 15, topTrailingRadius: 0))
                .offset(x: 1.5, y: 94.5)
            }
        }
    }
}

/// The header's coin pill (5.0 · 57.7 · 110.4 · 38.0, #DEEEFF, no plus) with the coin icon at its left and the digits.
private struct ShopHeaderCoins: View {
    /// The closable page reads the store; the home tab reads home's parked-aware proxy (FIX-2 A).
    let live: Bool
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m
    var body: some View {
        let t = app.tuning.ui.tokens
        let coins = CoinPillDisplay.shared.shown(live ? app.store.state : ShellScreens.homeState(app))
        let st = GameTextStyle.s2(18.7, -0.17, [Skin.shopShopViewShopHeaderCoinsSt0]).sized(18.7 * m.s)
        let digits = m.point(CGPoint(x: 76.4, y: 82.6), .top)
        ZStack(alignment: .topLeading) {
            Rasterized("shopHeaderPill") { _ in TopPill(t: t, n: 5.3) }.placed(m.rect(CGRect(5.0, 57.7, 110.4, 38.0), .top))
            GameText(verbatim: "\(coins)", style: st, maxWidth: 62 * m.s).at(digits.x, st.capCentre(baseline: digits.y))
            ArtImage(art: .currencyCoinIcon).placed(m.rect(CGRect(4.2, 57.3, 38.5, 38.5), .top))
        }
        .accessibilityElement()
        .accessibilityIdentifier("shop.coins")
        .accessibilityValue(Text(verbatim: "\(coins)"))
        .anchor(.custom("shop.coins"))
    }
}

// MARK: - the Shop as a closable page over a popup (SPEC-ui §2.12.5, SPEC-gameplay §9.5)

@MainActor enum ShopPage {
    static let popupID = "shop"

    /// Opens the Shop over the current screen / popup; returns when it is closed.
    static func openOver(_ app: AppModel, section: ShopSection = .top) {
        Task { @MainActor in
            let r = await app.popups.present(Popup<PopupResult>(.custom(id: popupID, params: ["section": section.rawValue]),
                                                                style: PopupStyle(dim: .none), fallback: .close))
            Log.mark("shop", "closable page closed (\(r))")
        }
    }
}
