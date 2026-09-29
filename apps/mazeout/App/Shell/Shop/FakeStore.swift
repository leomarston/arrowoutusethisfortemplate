#if DEBUG
import Foundation
import PathCore

// SHELL S3 (SPEC-architecture §6.8, D18; SPEC-gameplay §9.4; CONSISTENCY X-18, §21.14). The store DEBUG builds use for tests, UI
// tests, captures and `-pc.fakeStore 1`: the same 12-product catalogue as the App Store sells (rules.json `shop`), prices in the
// device region's REFERENCE list (TL on a TR device, else US $; ShopCatalog's priceTRY / priceUSD, reference data only), a
// purchase that succeeds after 0.3 s and grants through `Economy.applyPurchase` (once per transaction id), and `isTestStore =
// true` so the Shop shows its DEBUG-only chip. No money path exists: nothing here talks to StoreKit or the network.
// A1 STORE-APP (release-plan §2.5 S-1…S-3): this whole file — and the hard-coded price formatter below — is compiled into
// DEBUG builds only. A Release build sells through StoreKit 2 and shows StoreKit's `displayPrice`, or a disabled "…" well.

@MainActor final class FakeStore: StoreServicing {
    let rules: EconomyRules
    let priceList: ShopFormat.PriceList
    private let playerStore: PlayerStore
    private let clock: MotionClock
    /// The purchase latency (SPEC-architecture §6.8: 0.3 s).
    var latency: Double = 0.3
    private var counter = 0

    init(rules: EconomyRules, region: String?, store: PlayerStore, clock: MotionClock) {
        self.rules = rules
        self.priceList = ShopFormat.list(region: region)
        self.playerStore = store
        self.clock = clock
    }

    var isTestStore: Bool { true }

    var products: [StoreProductInfo] {
        rules.shop.products.map {
            StoreProductInfo(id: rules.shop.storeID($0), displayName: ShopTitles.english($0),
                             displayPrice: ShopFormat.price($0, list: priceList))
        }
    }

    func start() async {
        Log.mark("shop", "FakeStore ready: \(rules.shop.products.count) products, prices \(priceList.rawValue) (nothing is charged)")
    }

    func purchase(_ productID: String) async -> PurchaseOutcome {
        guard rules.shop.product(productID) != nil else {
            Log.error("shop", "FakeStore: unknown product \(productID)")
            return .failed("unknown product")
        }
        try? await Task.sleep(nanoseconds: UInt64(latency * 1_000_000_000))
        counter += 1
        let tx = "fake-\(Int(clock.wallClock().timeIntervalSince1970))-\(counter)-\(UUID().uuidString.prefix(8))"
        guard ShellEconomy.applyPurchase(store: playerStore, rules: rules, productID: productID, transactionID: tx,
                                         now: clock.wallClock()) != nil else {
            return .failed("not granted")
        }
        return .granted
    }
}

/// The FakeStore's reference price lists (SPEC-gameplay §9.4 / CONSISTENCY X-18: the device region's list, TL for region TR,
/// else US $). DEBUG only: the real Shop never formats a price itself (release-plan §3.2).
extension ShopFormat {
    enum PriceList: String, Sendable { case tl, usd }

    /// The price list for a region code (ISO 3166 alpha-2): "TR" → TL, anything else → US $.
    static func list(region: String?) -> PriceList { (region ?? "").uppercased() == "TR" ? .tl : .usd }

    /// "49,99 TL" / "2.499,99 TL" (VERIFIED meta-012 on the TR device) or "$0.99" / "$99.99".
    static func price(_ p: ShopProduct, list: PriceList) -> String {
        switch list {
        case .tl:
            guard let v = p.priceTRY else { return price(p, list: .usd) }
            return decimal(v, grouping: ".", decimal: ",") + " TL"
        case .usd:
            guard let v = p.priceUSD else { return "" }
            return "$" + decimal(v, grouping: ",", decimal: ".")
        }
    }

    private static func decimal(_ v: Double, grouping: String, decimal: String) -> String {
        let cents = Int((v * 100).rounded())
        let whole = cents / 100, frac = cents % 100
        let digits = String(whole)
        var out = ""
        for (i, ch) in digits.enumerated() {
            if i > 0 && (digits.count - i) % 3 == 0 { out += grouping }
            out.append(ch)
        }
        return out + decimal + String(format: "%02d", frac)
    }

    /// The device region the FakeStore's prices follow (`-pc.storeRegion XX`, SHELL-private, overrides it for tests / captures).
    static func deviceRegion(args: LaunchArgs) -> String? {
        if let r = args.raw["pc.storeRegion"], r.count == 2 { return r.uppercased() }
        return Locale.current.region?.identifier
    }
}
#endif
