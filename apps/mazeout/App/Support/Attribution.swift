import Foundation

// The template ships NO ad or attribution SDK (docs/ROADMAP.md D2). A game that wants install attribution (Meta, AppsFlyer,
// …) adds its SDK itself and plugs in here: the store pipeline reports every GRANTED purchase to a `PurchaseReporting`
// (StoreService's `reporter`, nil by default), exactly once, with StoreKit's own price and currency. Recipe and pitfalls:
// docs/recipes/ad-attribution.md.

/// A completed purchase as an attribution event needs it: StoreKit's recorded price and currency, never a hard-coded price
/// (the same coin pack is a different number in every storefront).
struct PurchaseValue: Equatable, Sendable {
    let productID: String
    let transactionID: String
    let amount: Decimal
    let currency: String                  // ISO 4217, from the transaction
    let quantity: Int
    /// Where StoreKit says the money came from (`Transaction.environment`). Only `.production` is revenue.
    let environment: StoreEnvironment
}

/// `AppStore.Environment` as a reporter needs it: production = real money; sandbox = TestFlight and App Review's test
/// purchases; xcode = a local StoreKit configuration / SKTestSession.
enum StoreEnvironment: String, Equatable, Sendable {
    case production, sandbox, xcode, unknown
}

/// Where the purchase pipeline reports a GRANTED purchase (a game's attribution SDK adapter; a recorder in the tests).
@MainActor protocol PurchaseReporting: AnyObject {
    func purchaseCompleted(_ value: PurchaseValue)
}
