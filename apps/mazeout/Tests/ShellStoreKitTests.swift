import XCTest
import StoreKit
import StoreKitTest
import UIKit
import PathCore
@testable import ArrowOut

/// SHELL S3 (SPEC-architecture §6.8, §12.2 S3 acceptance "ShellStoreKitTests (SKTestSession) grant once and a replay grants
/// nothing"). The StoreKit 2 service against App/Resources/StoreKit/ArrowOut.storekit (the 12-product catalogue, local testing:
/// nothing is charged): every product loads with the catalogue's id, a verified purchase grants exactly the catalogue's Grant
/// once (coins, each booster, unlimited lives), the same transaction delivered again grants nothing, and the once-only Special
/// Offer is marked bought.
@MainActor final class ShellStoreKitTests: XCTestCase {
    private var session: SKTestSession!
    private var state = PlayerState(installSeed: 7, installDate: Date(timeIntervalSince1970: 1_790_000_000))
    private let rules = ShellEconomy.rules(Tuning.load(bundle: .main))

    override func setUp() async throws {
        let url = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("App/Resources/StoreKit/ArrowOut.storekit")
        session = try SKTestSession(contentsOf: url)
        session.disableDialogs = true
        session.resetToDefaultState()
        session.clearTransactions()
        state = PlayerState(installSeed: 7, installDate: Date(timeIntervalSince1970: 1_790_000_000))
    }

    override func tearDown() async throws {
        session.clearTransactions()
        session = nil
    }

    private func makeService() -> StoreService {
        StoreService(catalogue: rules.shop) { [unowned self] pid, tid in
            Economy.applyPurchase(&self.state, productID: pid, transactionID: tid, now: Date(), rules: self.rules)
        }
    }

    func testCatalogueLoadsCompletely() async {
        let svc = makeService()
        let ok = await svc.loadProducts()
        XCTAssertTrue(ok, "the local configuration answers with every catalogue id")
        XCTAssertEqual(svc.products.map(\.id), rules.shop.storeIDs)
        XCTAssertEqual(svc.products.first?.displayPrice.contains("0.99"), true, svc.products.first?.displayPrice ?? "-")
    }

    /// Waits (≤ `timeout` s) until `cond` holds.
    private func eventually(_ timeout: Double = 10, _ cond: () -> Bool) async -> Bool {
        let end = Date().addingTimeInterval(timeout)
        while Date() < end { if cond() { return true }; try? await Task.sleep(nanoseconds: 50_000_000) }
        return cond()
    }

    /// A purchase made by the session (no UI) reaches the service through `Transaction.updates`: granted once; the same
    /// transaction delivered again grants nothing.
    func testTransactionGrantsOnceAndReplayGrantsNothing() async throws {
        let svc = makeService()
        await svc.start()
        let coins0 = state.coins
        let tx = try await session.buyProduct(identifier: "com.manycode.arrowout.coins.1000")
        let arrived = await eventually { self.state.coins == coins0 + 1000 }
        XCTAssertTrue(arrived, "the update granted the catalogue's coins")
        XCTAssertEqual(state.processedTransactions, [String(tx.id)])
        let replay = try XCTUnwrap(svc.lastVerification)
        let again = await svc.handle(replay)
        XCTAssertNil(again, "a replay grants nothing")
        XCTAssertEqual(state.coins, coins0 + 1000)
        XCTAssertEqual(state.processedTransactions.count, 1)
    }

    func testBundleGrantsEachBoosterAndUnlimitedLives() async throws {
        let svc = makeService()
        await svc.start()
        let coins0 = state.coins
        _ = try await session.buyProduct(identifier: "com.manycode.arrowout.bundle.epic")
        let arrived = await eventually { self.state.coins == coins0 + 4000 }
        XCTAssertTrue(arrived)
        XCTAssertEqual(state.boosters["freeze"], 3)
        XCTAssertEqual(state.boosters["hint"], 3)
        let until = try XCTUnwrap(state.unlimitedLivesUntil)
        XCTAssertGreaterThan(until.timeIntervalSinceNow, 6 * 3600 - 120, "∞ 6h")
    }

    func testSpecialOfferIsOnceOnly() async throws {
        let svc = makeService()
        await svc.start()
        XCTAssertTrue(rules.shop.visible(state).contains { $0.id == "offer.special" })
        _ = try await session.buyProduct(identifier: "com.manycode.arrowout.offer.special")
        let arrived = await eventually { !self.rules.shop.visible(self.state).contains { $0.id == "offer.special" } }
        XCTAssertTrue(arrived, "the card disappears once bought")
    }

    // `Product.purchase()` itself is not exercised here: in the hosted unit-test process on the iOS 26 simulator the host scene
    // stays `foregroundInactive` and the call never returns (probed 2026-09-25, build/s3/test-unit-5.log: no answer in 15-20 s,
    // with and without `confirmIn:`). The purchase-result mapping is covered by the FakeStore path (ShellS3Tests, ShellS3UITests);
    // the grant-once / replay logic by the session-made transactions above.

    // MARK: VERIFY (2026-09-29, META): the StoreKit half of the Meta purchase event

    /// Records what the pipeline reports to Meta (MetaAds in the app).
    private final class MetaReportRecorder: PurchaseReporting {
        var values: [PurchaseValue] = []
        func purchaseCompleted(_ value: PurchaseValue) { values.append(value) }
    }

    private func makeReportingService(_ reporter: MetaReportRecorder) -> StoreService {
        StoreService(catalogue: rules.shop, reporter: reporter) { [unowned self] pid, tid in
            Economy.applyPurchase(&self.state, productID: pid, transactionID: tid, now: Date(), rules: self.rules)
        }
    }

    /// A REAL StoreKit transaction (the session buys, `Transaction.updates` delivers it to the service) reaches the Meta
    /// reporter exactly once with StoreKit's own price, currency and quantity (`StoreKitDelivery.value`: MetaEventsTests
    /// feeds hand-made values, so this is the only proof of the Transaction → PurchaseValue mapping), and the event built
    /// from it is the fb_mobile_purchase Meta receives. The replay of the same transaction reports nothing.
    func testASessionPurchaseReachesMetaWithTheTransactionsPriceAndCurrency() async throws {
        let reporter = MetaReportRecorder()
        let svc = makeReportingService(reporter)
        await svc.start()
        let pid = "com.manycode.arrowout.coins.1000"
        let priced = try await Product.products(for: [pid])
        let product = try XCTUnwrap(priced.first, "the local catalogue prices \(pid)")
        let tx = try await session.buyProduct(identifier: pid)
        let arrived = await eventually { reporter.values.count == 1 }
        XCTAssertTrue(arrived, "the granted transaction was reported to Meta")
        let v = try XCTUnwrap(reporter.values.first)
        XCTAssertEqual(v.productID, pid)
        XCTAssertEqual(v.transactionID, String(tx.id), "the transaction that was granted")
        XCTAssertEqual(v.amount, try XCTUnwrap(tx.price), "StoreKit's recorded price")
        XCTAssertEqual(v.amount, product.price, "= the product's price in this storefront (\(product.displayPrice))")
        XCTAssertGreaterThan(v.amount, 0)
        XCTAssertEqual(v.currency, try XCTUnwrap(tx.currency?.identifier), "StoreKit's recorded currency")
        XCTAssertEqual(v.currency, "USD", "the configuration's storefront is USA")
        XCTAssertEqual(v.quantity, 1)
        let e = try XCTUnwrap(MetaEvents.purchase(v), "a priced purchase is revenue")
        XCTAssertEqual(e.name, "fb_mobile_purchase")
        XCTAssertEqual(try XCTUnwrap(e.valueToSum), NSDecimalNumber(decimal: product.price).doubleValue, accuracy: 0.000_001)
        XCTAssertEqual(e.parameters["fb_currency"], .text("USD"))
        XCTAssertEqual(e.parameters["fb_content_id"], .text(pid))
        print("[VERIFY][meta] session purchase \(pid): reported \(v.amount) \(v.currency) tx \(v.transactionID) (displayPrice \(product.displayPrice))")
        // RFIX 2026-09-29: StoreKit's own environment rides along, and MetaAds sends only production money: this SKTestSession
        // transaction (like a TestFlight / App Review sandbox purchase) is test money and never reaches Meta as revenue
        XCTAssertEqual(v.environment, .xcode, "Transaction.environment of an SKTestSession purchase")
        XCTAssertFalse(MetaEvents.isRevenue(v))
        final class Sink: MetaEventSink {
            var events: [MetaEvent] = []
            func start(idfa: Bool) {}
            func activate() {}
            func log(_ event: MetaEvent) { events.append(event) }
            func setIDFACollection(_ on: Bool) {}
        }
        let sink = Sink()
        MetaAds(mode: .live, sink: sink).purchaseCompleted(v)
        XCTAssertEqual(sink.events, [], "a live reporter logs it and sends nothing")
        // the same transaction delivered again: no grant, so no second report
        let replay = try XCTUnwrap(svc.lastVerification)
        let again = await svc.handle(replay)
        XCTAssertNil(again, "a replay grants nothing")
        XCTAssertEqual(reporter.values.count, 1, "…and reports nothing")
    }

    /// The currency is the transaction's, never a constant: the same purchase in another storefront reports what StoreKit
    /// recorded for THAT transaction.
    func testTheReportedCurrencyFollowsTheTransactionsStorefront() async throws {
        session.storefront = "TUR"
        let reporter = MetaReportRecorder()
        let svc = makeReportingService(reporter)
        await svc.start()
        let tx = try await session.buyProduct(identifier: "com.manycode.arrowout.coins.1000")
        let arrived = await eventually { reporter.values.count == 1 }
        XCTAssertTrue(arrived, "the granted transaction was reported to Meta")
        let v = try XCTUnwrap(reporter.values.first)
        XCTAssertEqual(v.currency, try XCTUnwrap(tx.currency?.identifier), "the transaction's own currency")
        XCTAssertEqual(v.amount, try XCTUnwrap(tx.price), "the transaction's own price")
        XCTAssertEqual(tx.storefront.countryCode, "TUR")
        XCTAssertEqual(v.environment, .xcode, "RFIX: the transaction's own environment (never revenue in a StoreKit test)")
        print("[VERIFY][meta] TUR storefront purchase: reported \(v.amount) \(v.currency) (transaction currency \(tx.currency?.identifier ?? "nil"))")
    }

    func testUnknownProductFailsWithoutGrant() async {
        let svc = makeService()
        _ = await svc.loadProducts()
        let coins0 = state.coins
        let outcome = await svc.purchase("com.manycode.arrowout.nope")
        if case .failed = outcome {} else { XCTFail("expected .failed, got \(outcome)") }
        XCTAssertEqual(state.coins, coins0)
    }
}
