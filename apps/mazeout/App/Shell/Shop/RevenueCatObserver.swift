import Foundation
import StoreKit
import RevenueCat

// A1 STORE-APP (PLAN-P §4.3; release-plan §2.4 "SDK mode. DECISION: observer mode"; SPEC.md §5 item 42 (d)). RevenueCat
// (purchases-ios-spm, pinned 5.89.0) OBSERVES the purchases our StoreKit 2 StoreService completes: it never buys, never
// finishes a transaction and never decides a grant, so a kill between the App Store's charge and our grant is recovered
// offline by StoreKit (Transaction.unfinished) whatever RevenueCat's state. Configured once, on a utility-priority task
// (off the main thread and off the launch path: the FEEL budget), with the `appl_` key from StoreConfig.swift — an empty key
// (until T5) or any other key leaves it unconfigured, and the game sells and grants the same. After OUR verified grant the
// pipeline calls `record` → `Purchases.shared.recordPurchase(_:)` (StoreKit's own Product.PurchaseResult) → then finishes.
// Transactions that arrive through Transaction.updates / .unfinished are seen by RevenueCat's own StoreKit 2 listener and its
// unobserved-transaction detector (didBecomeActive), so they are not recorded here a second time.

@MainActor final class RevenueCatObserver: PurchaseRecording {
    static let shared = RevenueCatObserver()
    private static var configuring = false

    /// "configured", "no key" or "not an appl_ key" (the boot log; never the key itself).
    static var keyState: String {
        if Purchases.isConfigured { return "configured" }
        return StoreConfig.rcAPIKey.isEmpty ? "(no key yet: not configured)" : (StoreConfig.isUsableRevenueCatKey(StoreConfig.rcAPIKey)
            ? "(configuring)" : "(not an appl_ key: not configured)")
    }

    /// Configures RevenueCat in observer mode, once, off the main thread. Does nothing without a usable `appl_` key.
    static func configureIfPossible(key: String = StoreConfig.rcAPIKey) {
        guard StoreConfig.isUsableRevenueCatKey(key), !configuring, !Purchases.isConfigured else { return }
        configuring = true
        Task.detached(priority: .utility) {
            Purchases.logLevel = .warn
            Purchases.configure(with: Configuration.Builder(withAPIKey: key)
                .with(purchasesAreCompletedBy: .myApp, storeKitVersion: .storeKit2)
                .build())
            await MainActor.run { Log.mark("shop", "RevenueCat configured (observer mode, StoreKit 2)") }
        }
    }

    func record(_ purchase: RecordablePurchase) async {
        guard let result = purchase.result else { return }
        guard Purchases.isConfigured else {
            // FIX-3 B (ruling 55): the log texts say "reported" (the store binary carries no standalone "recorded")
            Log.mark("shop", "RevenueCat not configured: \(purchase.productID) tx \(purchase.transactionID) not reported here")
            return
        }
        do {
            let t = try await Purchases.shared.recordPurchase(result)
            Log.mark("shop", "RevenueCat reported \(purchase.productID) tx \(t?.transactionIdentifier ?? purchase.transactionID)")
        } catch {
            // the grant is already saved; RevenueCat's own listener / detector retries the report later
            Log.error("shop", "RevenueCat recordPurchase \(purchase.productID) failed: \(error.localizedDescription)")
        }
    }
}
