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

    // MARK: the purchase-report hook (Support/Attribution.swift): what a game's attribution SDK would receive

    /// Records what the pipeline reports (a game's attribution adapter in an app that has one).
    private final class ReportRecorder: PurchaseReporting {
        var values: [PurchaseValue] = []
        func purchaseCompleted(_ value: PurchaseValue) { values.append(value) }
    }

    private func makeReportingService(_ reporter: ReportRecorder) -> StoreService {
        StoreService(catalogue: rules.shop, reporter: reporter) { [unowned self] pid, tid in
            Economy.applyPurchase(&self.state, productID: pid, transactionID: tid, now: Date(), rules: self.rules)
        }
    }

    /// A REAL StoreKit transaction (the session buys, `Transaction.updates` delivers it to the service) reaches the
    /// reporter exactly once with StoreKit's own price, currency and quantity (`StoreKitDelivery.value`, the proof of the
    /// Transaction → PurchaseValue mapping). The replay of the same transaction reports nothing.
    func testASessionPurchaseReachesTheReporterWithTheTransactionsPriceAndCurrency() async throws {
        let reporter = ReportRecorder()
        let svc = makeReportingService(reporter)
        await svc.start()
        let pid = "com.manycode.arrowout.coins.1000"
        let priced = try await Product.products(for: [pid])
        let product = try XCTUnwrap(priced.first, "the local catalogue prices \(pid)")
        let tx = try await session.buyProduct(identifier: pid)
        let arrived = await eventually { reporter.values.count == 1 }
        XCTAssertTrue(arrived, "the granted transaction was reported")
        let v = try XCTUnwrap(reporter.values.first)
        XCTAssertEqual(v.productID, pid)
        XCTAssertEqual(v.transactionID, String(tx.id), "the transaction that was granted")
        XCTAssertEqual(v.amount, try XCTUnwrap(tx.price), "StoreKit's recorded price")
        XCTAssertEqual(v.amount, product.price, "= the product's price in this storefront (\(product.displayPrice))")
        XCTAssertGreaterThan(v.amount, 0)
        XCTAssertEqual(v.currency, try XCTUnwrap(tx.currency?.identifier), "StoreKit's recorded currency")
        XCTAssertEqual(v.currency, "USD", "the configuration's storefront is USA")
        XCTAssertEqual(v.quantity, 1)
        // StoreKit's own environment rides along: this SKTestSession transaction (like a TestFlight / App Review sandbox
        // purchase) is test money, which a reporter must not count as revenue
        XCTAssertEqual(v.environment, .xcode, "Transaction.environment of an SKTestSession purchase")
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
        let reporter = ReportRecorder()
        let svc = makeReportingService(reporter)
        await svc.start()
        let tx = try await session.buyProduct(identifier: "com.manycode.arrowout.coins.1000")
        let arrived = await eventually { reporter.values.count == 1 }
        XCTAssertTrue(arrived, "the granted transaction was reported")
        let v = try XCTUnwrap(reporter.values.first)
        XCTAssertEqual(v.currency, try XCTUnwrap(tx.currency?.identifier), "the transaction's own currency")
        XCTAssertEqual(v.amount, try XCTUnwrap(tx.price), "the transaction's own price")
        XCTAssertEqual(tx.storefront.countryCode, "TUR")
        XCTAssertEqual(v.environment, .xcode, "RFIX: the transaction's own environment (never revenue in a StoreKit test)")
        print("[VERIFY][report] TUR storefront purchase: reported \(v.amount) \(v.currency) (transaction currency \(tx.currency?.identifier ?? "nil"))")
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
