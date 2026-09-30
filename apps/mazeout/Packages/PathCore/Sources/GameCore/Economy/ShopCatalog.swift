import Foundation

// C3 (SPEC-architecture §4.8 "ShopCatalog"; SPEC-gameplay §9.4, §15 `rules.json:shop`). The v552 shop: 1 special offer,
// 5 bundles, 6 coin packs (VERIFIED meta §3 + economy §4 TL prices; US $ from the V2 shop and the US store list). A
// product id is the bundle id + "." + the catalogue id; its Grant is coins + N of EACH booster + unlimited lives.
// The shell's StoreKit layer shows the price (StoreKit's displayPrice only; A1, release-plan §3.2); `Economy.applyPurchase`
// grants each transaction once. `priceUSD` / `priceTRY` are REFERENCE data: the App Store's US base price (Apple derives every
// other storefront's price from it) for the DEBUG FakeStore and the iap.json self-check — the app never shows them.

public struct ShopProduct: Codable, Sendable, Equatable, Identifiable {
    /// Catalogue id ("offer.special", "bundle.mini", "coins.1000", …).
    public var id: String
    public var priceUSD: Double?
    public var priceTRY: Double?
    /// The card's badge / ribbon ("STARTER", "Popular", "Best Value"; ruling 38: STARTER replaced "90% OFF").
    public var badge: String?
    public var grant: Grant

    public init(id: String, usd: Double?, try tl: Double?, badge: String? = nil, grant: Grant) {
        self.id = id; self.priceUSD = usd; self.priceTRY = tl; self.badge = badge; self.grant = grant
    }

    enum CodingKeys: String, CodingKey { case id, priceUSD = "usd", priceTRY = "try", badge, grant }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.v(.id, "")
        priceUSD = try c.decodeIfPresent(Double.self, forKey: .priceUSD)
        priceTRY = try c.decodeIfPresent(Double.self, forKey: .priceTRY)
        badge = try c.decodeIfPresent(String.self, forKey: .badge)
        grant = try c.v(.grant, Grant())
    }

    /// The shop section the card sits in (the id's prefix: "offer" → Special Offers, "bundle" → Bundles, "coins" → Coins).
    public var section: String { String(id.split(separator: ".").first ?? "") }
}

public struct ShopCatalog: Codable, Sendable, Equatable {
    /// The App Store product id prefix (the bundle id + "."): rules.json `shop.productPrefix`, else game.yml's via the
    /// generated GameConfig.
    public var productPrefix: String = GameConfig.productPrefix
    /// The Special Offer can be bought once per install, then its card disappears (DECISION SPEC-gameplay §9.4).
    public var specialOfferOnce: Bool = true
    public var products: [ShopProduct] = ShopCatalog.defaultProducts

    public init() {}

    enum CodingKeys: String, CodingKey { case productPrefix, specialOfferOnce, products }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); let d = ShopCatalog()
        productPrefix = try c.v(.productPrefix, d.productPrefix)
        specialOfferOnce = try c.v(.specialOfferOnce, d.specialOfferOnce)
        products = try c.v(.products, d.products)
    }

    /// SPEC-gameplay §9.4 (order = the shop's order: Special Offers, Bundles, Coins).
    public static let defaultProducts: [ShopProduct] = {
        func each(_ n: Int) -> [String: Int] { ["freeze": n, "hint": n] }
        let h = 3600.0
        return [
            ShopProduct(id: "offer.special", usd: 0.99, try: 49.99, badge: "STARTER",
                        grant: Grant(coins: 1_000, boosters: each(1), unlimitedLives: 1 * h)),
            ShopProduct(id: "bundle.mini", usd: 4.99, try: 249.99, grant: Grant(coins: 2_000, boosters: each(1), unlimitedLives: 3 * h)),
            ShopProduct(id: "bundle.epic", usd: 9.99, try: 499.99, grant: Grant(coins: 4_000, boosters: each(3), unlimitedLives: 6 * h)),
            ShopProduct(id: "bundle.elite", usd: 19.99, try: 999.99, badge: "Popular",
                        grant: Grant(coins: 8_000, boosters: each(8), unlimitedLives: 12 * h)),
            ShopProduct(id: "bundle.mega", usd: 49.99, try: 2_499.99, grant: Grant(coins: 20_000, boosters: each(18), unlimitedLives: 36 * h)),
            ShopProduct(id: "bundle.legendary", usd: 99.99, try: 4_999.99, badge: "Best Value",
                        grant: Grant(coins: 60_000, boosters: each(36), unlimitedLives: 72 * h)),
            ShopProduct(id: "coins.1000", usd: 1.99, try: 99.99, grant: .coins(1_000)),
            ShopProduct(id: "coins.5000", usd: 7.99, try: 399.99, grant: .coins(5_000)),
            ShopProduct(id: "coins.10000", usd: 14.99, try: 799.99, grant: .coins(10_000)),
            ShopProduct(id: "coins.25000", usd: 29.99, try: 1_499.99, grant: .coins(25_000)),
            ShopProduct(id: "coins.50000", usd: 54.99, try: 2_999.99, grant: .coins(50_000)),
            ShopProduct(id: "coins.100000", usd: 99.99, try: 4_999.99, grant: .coins(100_000)),
        ]
    }()

    /// The catalogue entry for a catalogue id or a full App Store product id.
    public func product(_ id: String) -> ShopProduct? {
        let short = id.hasPrefix(productPrefix) ? String(id.dropFirst(productPrefix.count)) : id
        return products.first { $0.id == short }
    }

    /// The App Store product id of a catalogue entry.
    public func storeID(_ p: ShopProduct) -> String { productPrefix + p.id }

    /// Every App Store product id (StoreKit's `Product.products(for:)`).
    public var storeIDs: [String] { products.map(storeID) }

    /// The products the shop shows to this player (the once-only Special Offer disappears after its purchase).
    public func visible(_ s: PlayerState) -> [ShopProduct] {
        products.filter { p in !(specialOfferOnce && p.section == "offer" && s.flags.seen.contains(Self.boughtFlag(p.id))) }
    }

    /// The `flags.seen` marker written when a once-only offer is bought.
    public static func boughtFlag(_ id: String) -> String { "bought:" + id }
}
