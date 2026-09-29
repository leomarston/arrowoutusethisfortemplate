import Foundation
import XCTest
import PathCore
@testable import ArrowOut

/// A1 STORE-APP (PLAN-P §4.3 acceptance; release-plan §2.5 "Tests to add"; SPEC.md §5 items 37a/42). The real store, without
/// StoreKit test sessions (ShellStoreKitTests is never run in this lane):
///  1. Release store selection: a Release build always sells through StoreKit 2 — no launch argument can make it fake — and a
///     Release-plan ShopStore has no FakeStore, no test chip and no price until StoreKit gives one.
///  2. No dollar fallback: the Shop's only price source is the store's `displayPrice`; a product without one is the disabled
///     "…" well, and no non-DEBUG source file formats a price from the catalogue's reference USD / TRY numbers.
///  3. RevenueCat observer: `record` is called exactly once per verified purchase, after our grant and before `finish`; never
///     for a StoreKit redelivery, a replay or an unverified transaction.
///  4. A grant survives a kill: `finish` runs only after the grant is on disk; an unfinished transaction redelivered to a NEW
///     process grants once (a kill before the grant) or nothing (a kill after it), and the coins are right either way.
@MainActor final class StoreReleaseTests: XCTestCase {
    private let tuning = Tuning.load(bundle: .main)
    private var rules: EconomyRules { ShellEconomy.rules(tuning) }

    // MARK: mocks

    /// A delivered transaction that logs what the pipeline does to it.
    private final class MockTx: DeliveredTransaction {
        let productID: String
        let transactionID: String
        let isVerified: Bool
        let log: EventLog
        private(set) var finished = 0
        init(_ pid: String, _ tid: String, verified: Bool = true, log: EventLog) {
            productID = pid; transactionID = tid; isVerified = verified; self.log = log
        }
        func finish() async { finished += 1; log.events.append("finish \(transactionID)") }
    }

    private final class EventLog { var events: [String] = [] }

    /// Counts RevenueCat observer calls (the protocol RevenueCatObserver implements in the app).
    private final class MockRecorder: PurchaseRecording {
        let log: EventLog
        private(set) var recorded: [String] = []
        init(log: EventLog) { self.log = log }
        func record(_ purchase: RecordablePurchase) async {
            recorded.append(purchase.transactionID)
            log.events.append("record \(purchase.transactionID)")
        }
    }

    private func tempDir(_ name: String) -> URL {
        FileManager.default.temporaryDirectory.appendingPathComponent("a1-\(name)-\(UUID().uuidString)")
    }

    private func makeContext(_ dir: URL, args: [String] = []) -> AppContext {
        let a = LaunchArgs(arguments: args)
        return AppContext(args: a, tuning: tuning, clock: MotionClock(args: a),
                          store: PlayerStore(args: a, now: Date(), bundle: .main, directory: dir), hud: HUDModel(),
                          anchors: AnchorRegistry(), perf: PerfMonitor(), latency: LatencyProbe(), bundle: .main)
    }

    // MARK: 1. Release store selection

    func testReleaseAlwaysSellsThroughStoreKit() {
        for fake in [false, true] {
            for quiet in [false, true] {
                for xctest in [false, true] {
                    XCTAssertEqual(StorePlan.choose(release: true, fakeStoreArg: fake, quietUI: quiet, underXCTest: xctest), .storeKit,
                                   "Release (fakeStore \(fake), quietUI \(quiet), XCTest \(xctest)) must sell through StoreKit")
                    let debug = StorePlan.choose(release: false, fakeStoreArg: fake, quietUI: quiet, underXCTest: xctest)
                    XCTAssertEqual(debug, fake || quiet || xctest ? .fake : .storeKitIfLocalCatalogue, "DEBUG plan")
                }
            }
        }
        XCTAssertFalse(StorePlan.isReleaseBuild, "the unit-test host is a Debug build")
        XCTAssertTrue(StorePlan.underXCTest)
        XCTAssertEqual(StorePlan.current(LaunchArgs(arguments: [])), .fake, "tests stay on the FakeStore")
    }

    func testReleasePlanShopHasNoFakeStoreNoChipAndNoPriceUntilStoreKitAnswers() {
        let dir = tempDir("plan")
        defer { try? FileManager.default.removeItem(at: dir) }
        let shop = ShopStore(makeContext(dir, args: ["-pc.fakeStore", "1"]), plan: .storeKit, autoStart: false)
        XCTAssertEqual(shop.kind, "storekit")
        XCTAssertFalse(shop.isTestStore, "no test-store chip in the Release plan")
        XCTAssertTrue(shop.active is StoreService, "the active store is StoreKit 2, not \(type(of: shop.active))")
        XCTAssertEqual(shop.products, [], "no price before StoreKit answers (never the FakeStore's list)")
        XCTAssertEqual(ShopLayout(products: rules.shop.products, testStore: shop.isTestStore).shift, 0, "no chip row")
        // the same context on the DEBUG plan keeps the FakeStore and its chip (tests / captures)
        let dir2 = tempDir("plan-debug")
        defer { try? FileManager.default.removeItem(at: dir2) }
        let debug = ShopStore(makeContext(dir2), plan: .fake, autoStart: false)
        XCTAssertEqual(debug.kind, "fake")
        XCTAssertTrue(debug.isTestStore)
        XCTAssertEqual(debug.products.count, 12)
    }

    // MARK: 2. no dollar fallback

    func testThePriceIsOnlyTheStoresDisplayPrice() {
        let ids = rules.shop.storeIDs
        XCTAssertEqual(ids.count, 12)
        for id in ids {
            XCTAssertNil(ShopPrices.label(for: id, in: [:]), "\(id): no StoreKit price → the disabled well, never a fallback")
            XCTAssertNil(ShopPrices.label(for: id, in: [id: ""]), "\(id): an empty displayPrice is no price")
        }
        let storefront = ["com.manycode.arrowout.offer.special": "₺49,99", "com.manycode.arrowout.coins.1000": "1,99 €",
                          "com.manycode.arrowout.bundle.mega": "¥8,000"]
        for (id, p) in storefront { XCTAssertEqual(ShopPrices.label(for: id, in: storefront), p, "passed through untouched") }
        XCTAssertEqual(ShopPrices.pending, "\u{2026}")
        // a Release-plan store with no StoreKit answer yet shows no price for any product
        let dir = tempDir("prices")
        defer { try? FileManager.default.removeItem(at: dir) }
        let shop = ShopStore(makeContext(dir), plan: .storeKit, autoStart: false)
        var prices: [String: String] = [:]
        for p in shop.products { prices[p.id] = p.displayPrice }
        XCTAssertTrue(ids.allSatisfy { ShopPrices.label(for: $0, in: prices) == nil })
    }

    /// The grep half of "no dollar fallback anywhere": outside the DEBUG-only FakeStore.swift, no app source formats a price
    /// from the catalogue's reference numbers or spells a currency sign in a string literal.
    func testNoSourceFormatsAPriceOutsideTheDebugFakeStore() throws {
        let files = V1Repo.files("App", extensions: ["swift"])
        XCTAssertGreaterThan(files.count, 50)
        let fake = try V1Repo.text("App/Shell/Shop/FakeStore.swift")
        XCTAssertTrue(fake.hasPrefix("#if DEBUG\n") && fake.hasSuffix("#endif\n"), "FakeStore.swift is DEBUG-only as a whole")
        let banned = ["ShopFormat.price(", "priceUSD", "priceTRY", "PriceList", "\"$\"", "\"$\" +", " TL\""]
        for url in files where url.lastPathComponent != "FakeStore.swift" {
            let code = try String(contentsOf: url, encoding: .utf8).split(separator: "\n")
                .filter { !$0.trimmingCharacters(in: .whitespaces).hasPrefix("//") }.joined(separator: "\n")
            for b in banned {
                XCTAssertFalse(code.contains(b), "\(url.lastPathComponent) contains \(b)")
            }
        }
        let shop = try V1Repo.text("App/Shell/Shop/ShopView.swift")
        XCTAssertTrue(shop.contains("ShopPrices.label(for:"), "the Shop's price tags read ShopPrices")
        XCTAssertFalse(shop.contains("?? ShopFormat"), "the old ShopView:328 fallback is gone")
    }

    // MARK: 3. RevenueCat observer: exactly once per verified purchase

    func testRecordIsCalledOncePerVerifiedPurchaseBetweenGrantAndFinish() async {
        let log = EventLog()
        let rec = MockRecorder(log: log)
        var granted: Set<String> = []
        let apply: (String, String) -> Grant? = { pid, tid in
            guard !granted.contains(tid) else { log.events.append("replay \(tid)"); return nil }
            granted.insert(tid); log.events.append("grant \(tid)")
            return .coins(1000)
        }
        // a verified purchase made in the app
        let tx = MockTx("com.manycode.arrowout.coins.1000", "t1", log: log)
        let g = await PurchasePipeline.complete(tx, apply: apply,
                                                persist: { log.events.append("saved") },
                                                record: RecordablePurchase(productID: tx.productID, transactionID: "t1", result: nil),
                                                recorder: rec)
        XCTAssertEqual(g?.coins, 1000)
        XCTAssertEqual(rec.recorded, ["t1"], "recorded exactly once")
        XCTAssertEqual(tx.finished, 1)
        XCTAssertEqual(log.events, ["grant t1", "saved", "record t1", "finish t1"], "grant → on disk → record → finish")
        // the same transaction delivered again (Transaction.updates / .unfinished): no grant, no second record, finished
        let again = MockTx("com.manycode.arrowout.coins.1000", "t1", log: log)
        let g2 = await PurchasePipeline.complete(again, apply: apply, persist: { log.events.append("saved") })
        XCTAssertNil(g2, "a replay grants nothing")
        XCTAssertEqual(rec.recorded, ["t1"], "a redelivery is not recorded again")
        XCTAssertEqual(again.finished, 1)
        // an unverified transaction: finished, never granted or recorded
        let bad = MockTx("com.manycode.arrowout.coins.1000", "t2", verified: false, log: log)
        let g3 = await PurchasePipeline.complete(bad, apply: apply, persist: { log.events.append("saved") },
                                                 record: RecordablePurchase(productID: bad.productID, transactionID: "t2", result: nil),
                                                 recorder: rec)
        XCTAssertNil(g3)
        XCTAssertEqual(bad.finished, 1)
        XCTAssertEqual(rec.recorded, ["t1"], "an unverified purchase is never recorded")
        XCTAssertFalse(granted.contains("t2"))
        // the app's recorder is RevenueCat's observer, and without an appl_ key it is never configured
        let appRecorder: PurchaseRecording = RevenueCatObserver.shared
        XCTAssertTrue(appRecorder === RevenueCatObserver.shared)
        XCTAssertFalse(StoreConfig.isUsableRevenueCatKey(""))
        XCTAssertFalse(StoreConfig.isUsableRevenueCatKey("test_abcdef"), "RevenueCat's simulated Test Store key is refused")
        XCTAssertFalse(StoreConfig.isUsableRevenueCatKey("appl_"))
        XCTAssertTrue(StoreConfig.isUsableRevenueCatKey("appl_AbCdEf123"))
        XCTAssertTrue(StoreConfig.rcAPIKey.isEmpty || StoreConfig.isUsableRevenueCatKey(StoreConfig.rcAPIKey),
                      "StoreConfig holds nothing or a production appl_ key")
    }

    // MARK: 4. a grant survives a kill

    func testAGrantSurvivesAKillBetweenPurchaseAndFinish() async throws {
        let dir = tempDir("kill")
        defer { try? FileManager.default.removeItem(at: dir) }
        let pid = "com.manycode.arrowout.coins.1000"
        let r = rules
        func process() -> PlayerStore { PlayerStore(args: LaunchArgs(), now: Date(), directory: dir, debounce: 0.05) }
        func apply(_ store: PlayerStore) -> (String, String) -> Grant? {
            { p, t in ShellEconomy.applyPurchase(store: store, rules: r, productID: p, transactionID: t, now: Date()) }
        }
        let log = EventLog()

        // (a) killed after the App Store charged, before our grant ran: the next process gets the unfinished transaction
        let p1 = process()
        let coins0 = p1.state.coins
        p1.flush()
        let p2 = process()                                            // "relaunch": the save on disk, no grant yet
        XCTAssertEqual(p2.state.coins, coins0)
        let unfinishedA = MockTx(pid, "kill-a", log: log)
        let gA = await PurchasePipeline.complete(unfinishedA, apply: apply(p2), persist: { await p2.flushed() })
        XCTAssertEqual(gA?.coins, 1000, "the redelivered purchase is granted")
        XCTAssertEqual(unfinishedA.finished, 1)
        XCTAssertEqual(process().state.coins, coins0 + 1000, "on disk once finished")

        // (b) killed after our grant, before finish (the transaction stays unfinished): the grant is already on disk, the
        // redelivery grants nothing and finishes it — the coins are counted once
        let p3 = process()
        XCTAssertEqual(p3.state.coins, coins0 + 1000)
        _ = apply(p3)(pid, "kill-b")                                  // the grant ran …
        await p3.flushed()                                            // … and reached the disk; then the process died
        let p4 = process()
        XCTAssertEqual(p4.state.coins, coins0 + 2000, "the grant survived the kill")
        let unfinishedB = MockTx(pid, "kill-b", log: log)
        let gB = await PurchasePipeline.complete(unfinishedB, apply: apply(p4), persist: { await p4.flushed() })
        XCTAssertNil(gB, "no double grant")
        XCTAssertEqual(unfinishedB.finished, 1, "finished now")
        XCTAssertEqual(process().state.coins, coins0 + 2000)
        XCTAssertEqual(process().state.processedTransactions.filter { $0.hasPrefix("kill-") }.sorted(), ["kill-a", "kill-b"])

        // (c) the pipeline never finishes before the grant is durable: at `finish` the file already holds the coins
        let p5 = process()
        final class DiskCheckTx: DeliveredTransaction {
            let productID: String, transactionID = "kill-c", isVerified = true
            let dir: URL
            var coinsOnDiskAtFinish: Int?
            init(_ pid: String, _ dir: URL) { productID = pid; self.dir = dir }
            func finish() async {
                coinsOnDiskAtFinish = PlayerStore(args: LaunchArgs(), now: Date(), directory: dir, debounce: 0.05).state.coins
            }
        }
        let c = DiskCheckTx(pid, dir)
        await PurchasePipeline.complete(c, apply: apply(p5), persist: { await p5.flushed() })
        XCTAssertEqual(c.coinsOnDiskAtFinish, coins0 + 3000, "finish saw the granted coins on disk")
    }
}
