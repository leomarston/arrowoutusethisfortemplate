import Foundation

// A1 STORE-APP (PLAN-P §4.3; release-plan §2.4 "The public appl_… key goes into a new App/Shell/Shop/StoreConfig.swift";
// SPEC.md §5 item 42). The one place the app's RevenueCat public key lives. scripts/rc_consumables.py (T5) writes the
// production `appl_…` key into the string below with a regex after it has created this app's entry in the shared RevenueCat
// project (that needs the owner's Apple 2FA session first). Until then the key is EMPTY and the app runs without RevenueCat:
// StoreKit 2 still sells and grants (our StoreService is the purchase engine), RevenueCat only observes and reports.
// Only an `appl_` key is ever used: an empty key, a `test_` (RevenueCat's simulated "Test Store") key or any other string
// leaves RevenueCat unconfigured (RevenueCatObserver.configureIfPossible), so no build can talk to a fake store by accident.

enum StoreConfig {
    /// RevenueCat public app-specific API key (App Store, "appl_" prefix). Written by T5 (rc_consumables.py --config-file).
    static let rcAPIKey = "appl_gXsKxCACkPIqRyKEkwJgqdSuOXg"

    /// The key is a production App Store public key (G8 asserts this on the Release build that is submitted).
    static func isUsableRevenueCatKey(_ key: String) -> Bool {
        key.hasPrefix("appl_") && key.count > "appl_".count
            && key.allSatisfy { $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "_") }
    }
}
