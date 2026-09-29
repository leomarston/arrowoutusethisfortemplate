import Foundation
import StoreKit
import UIKit
import PathCore

// SHELL S3 (SPEC-architecture §6.8, D18; memory revenuecat-cancel-does-not-throw), made the real store by A1 STORE-APP
// (PLAN-P §4.3; release-plan §2.4-§2.5 S-1…S-3; SPEC.md §5 items 37a, 42). The StoreKit 2 service is THE purchase engine of
// every Release build (the App Store sells, prices come only from StoreKit's `displayPrice`) and of a DEBUG build started from
// the scheme's Run action with App/Resources/StoreKit/ArrowOut.storekit; `ShellStoreKitTests` drives it with SKTestSession.
// RevenueCat runs in OBSERVER mode next to it (RevenueCatObserver): it never buys or finishes anything, it only records.
//   .success(.verified)   → PurchasePipeline: grant once (Economy.applyPurchase keyed by the transaction id, saved at once)
//                            → RevenueCat records the purchase (exactly once, a purchase made in the app) → finish → .granted
//                            META: a GRANTED transaction (any path: a purchase, Transaction.updates, .unfinished) is reported
//                            once to MetaAds (fb_mobile_purchase, the transaction's own price + currency); a replay grants
//                            nothing and reports nothing
//   .success(.unverified) → nothing granted or recorded, finished → .failed
//   .userCancelled        → RETURNS .cancelled (StoreKit 2 does not throw on cancel)
//   .pending              → .pending (the Shop toasts "Purchase pending"; the grant arrives later through Transaction.updates)
// `Transaction.updates` (Ask to Buy, interrupted purchases) and `Transaction.unfinished` at start go through the same pipeline
// without the RevenueCat step (RevenueCat's own StoreKit 2 listener and its unobserved-transaction detector see those), so a
// kill anywhere before `finish` is recovered at the next launch and a transaction delivered twice grants once.
// The FakeStore (FakeStore.swift) exists only in DEBUG builds (tests, UI tests, captures, `-pc.fakeStore 1`): a Release build
// has no free-coin path and no "test store" text at all.

// MARK: - the purchase pipeline (StoreKit-free, unit-tested: Tests/AppTests/StoreReleaseTests.swift)

/// One delivered StoreKit transaction, abstracted so the grant → record → finish order is testable without StoreKit.
@MainActor protocol DeliveredTransaction {
    var productID: String { get }
    var transactionID: String { get }
    var isVerified: Bool { get }
    /// META: the price and currency StoreKit recorded (nil = unknown: nothing is reported to Meta).
    var value: PurchaseValue? { get }
    func finish() async
}

extension DeliveredTransaction {
    var value: PurchaseValue? { nil }
}

/// What RevenueCat needs to record a purchase our code completed. `result` is StoreKit's own `Product.PurchaseResult` in the
/// app (RevenueCat's `recordPurchase(_:)` takes exactly that); tests pass nil.
struct RecordablePurchase {
    let productID: String
    let transactionID: String
    let result: Product.PurchaseResult?
}

/// Observer-mode reporting of a purchase the app completed itself (RevenueCatObserver in the app, a counting mock in tests).
@MainActor protocol PurchaseRecording: AnyObject {
    func record(_ purchase: RecordablePurchase) async
}

@MainActor enum PurchasePipeline {
    /// A verified transaction → our grant (once per transaction id) → `persist` (the save is ON DISK) → `record` for a
    /// purchase made in the app (RevenueCat observer mode: exactly once per verified purchase) → finish. An unverified one is
    /// finished with no grant and no record. Returns the grant (nil = a replay, an unknown product or an unverified
    /// transaction). A kill before `finish` leaves the transaction unfinished: StoreKit delivers it again at the next launch
    /// and this same function grants it once, or — when the grant reached the disk before the kill — grants nothing and
    /// finishes it. `finish` never runs before the grant is durable, so no kill can lose a finished purchase's coins.
    /// META: `report` receives the transaction's `value` once, when THIS delivery granted it (g != nil) and the grant is on
    /// disk; a replay (already granted), an unknown product or an unverified transaction reports nothing.
    @discardableResult
    static func complete(_ tx: some DeliveredTransaction, apply: (_ productID: String, _ transactionID: String) -> Grant?,
                         persist: (@MainActor () async -> Void)? = nil,
                         record: RecordablePurchase? = nil, recorder: PurchaseRecording? = nil,
                         report: PurchaseReporting? = nil) async -> Grant? {
        guard tx.isVerified else {
            Log.error("shop", "StoreKit: unverified transaction \(tx.productID) tx \(tx.transactionID): finished, nothing granted")
            await tx.finish()
            return nil
        }
        let g = apply(tx.productID, tx.transactionID)
        if let persist { await persist() }
        if let record, let recorder { await recorder.record(record) }
        if g != nil, let report {
            if let v = tx.value { report.purchaseCompleted(v) } else {
                Log.error("shop", "StoreKit: \(tx.productID) tx \(tx.transactionID) has no StoreKit price: not reported to Meta")
            }
        }
        await tx.finish()
        return g
    }
}

/// A StoreKit 2 `VerificationResult<Transaction>` as a `DeliveredTransaction`.
struct StoreKitDelivery: DeliveredTransaction {
    let result: VerificationResult<Transaction>
    private var transaction: Transaction {
        switch result {
        case .verified(let t): return t
        case .unverified(let t, _): return t
        }
    }
    var productID: String { transaction.productID }
    var transactionID: String { String(transaction.id) }
    var isVerified: Bool { if case .verified = result { return true } else { return false } }
    /// META: StoreKit's recorded price (`Transaction.price`), currency (`Transaction.currency`, ISO 4217) and environment
    /// (`Transaction.environment`, RFIX 2026-09-29: MetaAds reports only `.production` money as revenue).
    var value: PurchaseValue? {
        let t = transaction
        guard let price = t.price, let currency = t.currency?.identifier else { return nil }
        return PurchaseValue(productID: t.productID, transactionID: String(t.id), amount: price, currency: currency,
                             quantity: t.purchasedQuantity, environment: Self.environment(t.environment))
    }
    static func environment(_ e: AppStore.Environment) -> StoreEnvironment {
        switch e {
        case .production: return .production
        case .sandbox: return .sandbox
        case .xcode: return .xcode
        default: return .unknown
        }
    }
    func finish() async { await transaction.finish() }
}

// MARK: - which store a process runs

/// release-plan §2.5 S-1: Release = StoreKit 2 always; DEBUG = the FakeStore, except the scheme's Run action where StoreKit
/// answers with the whole local catalogue. A build-configuration-agnostic function, so the Release rule is unit-tested in the
/// Debug test host (StoreReleaseTests).
enum StorePlan: String, Equatable {
    case storeKit                   // Release: the App Store (real money) + RevenueCat observing
    case storeKitIfLocalCatalogue   // DEBUG, scheme Run action: StoreKit if the local .storekit answers completely, else fake
    case fake                       // DEBUG under tests / captures / `-pc.fakeStore 1`

    static func choose(release: Bool, fakeStoreArg: Bool, quietUI: Bool, underXCTest: Bool) -> StorePlan {
        if release { return .storeKit }                        // nothing a launch argument says can turn a Release build fake
        if fakeStoreArg || quietUI || underXCTest { return .fake }
        return .storeKitIfLocalCatalogue
    }

    static var isReleaseBuild: Bool {
        #if DEBUG
        return false
        #else
        return true
        #endif
    }

    static var underXCTest: Bool { ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil }

    static func current(_ args: LaunchArgs) -> StorePlan {
        choose(release: isReleaseBuild, fakeStoreArg: args.fakeStore, quietUI: args.quietUI, underXCTest: underXCTest)
    }
}

// MARK: - StoreKit 2

@MainActor final class StoreService: StoreServicing {
    let catalogue: ShopCatalog
    private let apply: @MainActor (_ productID: String, _ transactionID: String) -> Grant?
    private let recorder: PurchaseRecording?
    /// META: where a granted purchase is reported (MetaAds; nil = not reported).
    private let reporter: PurchaseReporting?
    private let persist: (@MainActor () async -> Void)?
    private(set) var products: [StoreProductInfo] = []
    private var storeProducts: [String: Product] = [:]
    private var updates: Task<Void, Never>?
    private var started = false
    private var loading = false
    /// The last verification result the service saw (tests replay it: a second delivery must grant nothing).
    private(set) var lastVerification: VerificationResult<Transaction>?
    /// The catalogue came back complete from StoreKit.
    private(set) var isComplete = false
    /// Called after the products changed or a transaction was delivered (ShopStore mirrors the products for the Shop).
    var onChange: (() -> Void)?
    /// DEBUG's local StoreKit configuration charges nothing (the DEBUG-only chip may say so); the App Store store is real.
    let isTestStore: Bool

    /// `persist`: waits until the grant's save is on disk (the app: PlayerStore.flushed); nil in the StoreKit tests.
    init(catalogue: ShopCatalog, isTestStore: Bool = false, recorder: PurchaseRecording? = nil,
         reporter: PurchaseReporting? = nil,
         persist: (@MainActor () async -> Void)? = nil,
         apply: @escaping @MainActor (_ productID: String, _ transactionID: String) -> Grant?) {
        self.catalogue = catalogue
        self.isTestStore = isTestStore
        self.recorder = recorder
        self.reporter = reporter
        self.persist = persist
        self.apply = apply
    }

    deinit { updates?.cancel() }

    func start() async {
        guard !started else { return }
        started = true
        updates = Task { @MainActor [weak self] in
            for await result in Transaction.updates {
                guard let self else { return }
                _ = await self.handle(result)
                if !self.isComplete { await self.loadProducts() }   // a store that answered again: retry the prices
                self.onChange?()
            }
        }
        await loadProducts()
        for await result in Transaction.unfinished { _ = await handle(result) }
        onChange?()
    }

    /// Loads the catalogue's products; true when every id came back. Never overlaps itself.
    @discardableResult
    func loadProducts() async -> Bool {
        guard !loading else { return isComplete }
        loading = true
        defer { loading = false }
        do {
            let list = try await Product.products(for: catalogue.storeIDs)
            storeProducts = Dictionary(list.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
            products = catalogue.products.compactMap { p in
                storeProducts[catalogue.storeID(p)].map { StoreProductInfo(id: $0.id, displayName: $0.displayName, displayPrice: $0.displayPrice) }
            }
            isComplete = products.count == catalogue.products.count
            Log.mark("shop", "StoreKit: \(products.count)/\(catalogue.products.count) products")
        } catch {
            Log.mark("shop", "StoreKit: products unavailable (\(error.localizedDescription))")
            isComplete = false
        }
        onChange?()
        return isComplete
    }

    func purchase(_ productID: String) async -> PurchaseOutcome {
        if storeProducts.isEmpty { await loadProducts() }
        guard let product = storeProducts[productID] else { return .failed("unknown product") }
        do {
            let result: Product.PurchaseResult
            if let scene = UIApplication.shared.connectedScenes.first(where: { $0.activationState == .foregroundActive }) {
                result = try await product.purchase(confirmIn: scene)
            } else {
                result = try await product.purchase()
            }
            switch result {
            case .success(let verification):
                lastVerification = verification
                let delivery = StoreKitDelivery(result: verification)
                guard delivery.isVerified else {
                    await PurchasePipeline.complete(delivery, apply: apply)     // finishes it, grants nothing
                    return .failed("unverified")
                }
                await PurchasePipeline.complete(delivery, apply: apply, persist: persist,
                                                record: RecordablePurchase(productID: productID, transactionID: delivery.transactionID,
                                                                           result: result),
                                                recorder: recorder, report: reporter)
                onChange?()
                return .granted
            case .userCancelled:
                Log.mark("shop", "StoreKit: \(productID) cancelled")
                return .cancelled
            case .pending:
                Log.mark("shop", "StoreKit: \(productID) pending")
                return .pending
            @unknown default:
                return .failed("unknown result")
            }
        } catch {
            Log.error("shop", "StoreKit: purchase \(productID) failed: \(error)")
            return .failed(error.localizedDescription)
        }
    }

    /// One transaction delivered by `Transaction.updates` / `.unfinished` (or replayed by a test): verified → grant once +
    /// finish; unverified → finish without a grant. Returns the grant (nil for a replay, an unknown product or an unverified
    /// transaction). RevenueCat is not called here: its own StoreKit 2 listener observes these deliveries.
    @discardableResult
    func handle(_ result: VerificationResult<Transaction>) async -> Grant? {
        lastVerification = result
        return await PurchasePipeline.complete(StoreKitDelivery(result: result), apply: apply, persist: persist, report: reporter)
    }
}

// MARK: - the app's store

/// The app's store (`AppModel.shop`), per `StorePlan`: StoreKit 2 (+ RevenueCat observing) in every Release build; in DEBUG the
/// FakeStore, or the StoreKit service when the scheme's Run action's local configuration answers with the whole catalogue.
/// The Shop reads `products` (mirrored here, so the page redraws when StoreKit answers) and asks `refresh()` on every open:
/// a product StoreKit has not priced yet shows a disabled "…" well — never a hard-coded price (release-plan §2.5 S-3).
@MainActor @Observable final class ShopStore: StoreServicing {
    @ObservationIgnored let plan: StorePlan
    #if DEBUG
    @ObservationIgnored let fake: FakeStore
    #endif
    @ObservationIgnored private let args: LaunchArgs
    @ObservationIgnored private let makeKit: (_ testStore: Bool) -> StoreService
    private(set) var kit: StoreService?
    /// The active store's products (StoreKit's `displayPrice`, or the DEBUG FakeStore's list).
    private(set) var products: [StoreProductInfo] = []
    /// "fake" or "storekit" (logged by the Shop).
    var kind: String { kit == nil ? "fake" : "storekit" }

    init(_ ctx: AppContext, plan: StorePlan? = nil, autoStart: Bool = true) {
        let rules = ShellEconomy.rules(ctx.tuning)
        let store = ctx.store, clock = ctx.clock
        let plan = plan ?? StorePlan.current(ctx.args)
        self.plan = plan
        #if DEBUG
        fake = FakeStore(rules: rules, region: ShopFormat.deviceRegion(args: ctx.args), store: store, clock: clock)
        #endif
        args = ctx.args
        let recorder: PurchaseRecording? = plan == .fake ? nil : RevenueCatObserver.shared
        let reporter: PurchaseReporting? = plan == .fake ? nil : MetaAds.shared     // META: live only in a real Release run
        makeKit = { testStore in
            StoreService(catalogue: rules.shop, isTestStore: testStore, recorder: recorder, reporter: reporter,
                         persist: { await store.flushed() }) { pid, tid in
                ShellEconomy.applyPurchase(store: store, rules: rules, productID: pid, transactionID: tid, now: clock.wallClock())
            }
        }
        if plan == .storeKit { attach(makeKit(false)) }           // Release: the App Store from the first frame (prices "…")
        syncProducts()
        // start behind the Loading screen, off the launch path (SPEC-architecture §6.8 "listens to Transaction.updates")
        if autoStart { Task { @MainActor [weak self] in await self?.start() } }
    }

    var isTestStore: Bool {
        if let kit { return kit.isTestStore }
        #if DEBUG
        return fake.isTestStore
        #else
        return false
        #endif
    }

    var active: any StoreServicing {
        if let kit { return kit }
        #if DEBUG
        return fake
        #else
        return UnavailableStore()                                // unreachable: a Release ShopStore always has its kit
        #endif
    }

    @ObservationIgnored private var didStart = false

    func start() async {
        guard !didStart else { return }
        didStart = true
        switch plan {
        case .storeKit:
            // RevenueCat off the main thread and off the launch path; never under tests / captures (they buy nothing)
            if !args.quietUI && !StorePlan.underXCTest { RevenueCatObserver.configureIfPossible() }
            Log.mark("shop", "store: StoreKit 2 (App Store) + RevenueCat observer \(RevenueCatObserver.keyState)")
            await kit?.start()
        case .storeKitIfLocalCatalogue:
            #if DEBUG
            await fake.start()
            let service = makeKit(true)
            if await service.loadProducts() {
                attach(service)
                await service.start()
                Log.mark("shop", "store: StoreKit (the local configuration answered with the whole catalogue)")
            } else {
                Log.mark("shop", "store: FakeStore (StoreKit has no local catalogue)")
            }
            #endif
        case .fake:
            #if DEBUG
            await fake.start()
            #endif
        }
        syncProducts()
    }

    /// The Shop opened: a StoreKit catalogue that is still incomplete (no network at launch, a slow store) is asked again.
    func refresh() async {
        guard let kit, !kit.isComplete else { return }
        await kit.loadProducts()
        syncProducts()
    }

    func purchase(_ productID: String) async -> PurchaseOutcome {
        let outcome = await active.purchase(productID)
        syncProducts()
        return outcome
    }

    private func attach(_ service: StoreService) {
        service.onChange = { [weak self] in self?.syncProducts() }
        kit = service
    }

    private func syncProducts() {
        let now = active.products
        if now != products { products = now }
    }
}

extension ShellEntry {
    static func makeStore(_ ctx: AppContext) -> any StoreServicing { ShopStore(ctx) }
}
