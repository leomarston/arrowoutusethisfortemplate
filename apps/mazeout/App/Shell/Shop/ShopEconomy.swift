import Foundation
import PathCore

// SHELL S3 (SPEC-architecture §4.8, §6.8; SPEC-gameplay §8.4, §9.4, §6.4). The C3 economy table the shell's own actions use:
// store purchases, the More Lives Refill, the booster pack ("Buy ×3 [coin] 900"). It is decoded ONCE per tuning set from the
// bundled rules.json (economy / lives / streak / claw / shop sections, WP0b's GP §15 copy) + social.json (the event table),
// with the `-pc.tune rules.<key>=v` overrides — the same `EconomyRules.load` GAME uses, so the shell and the level agree on
// every price. Every change goes through the pure `Economy` functions and `PlayerStore.mutateAndSave` (written at once: a
// purchase must survive a kill).

@MainActor enum ShellEconomy {
    private static var cache: [String: EconomyRules] = [:]
    private struct QuickKey: Equatable { let rules: Int; let social: Int; let overrides: Int }
    private static var last: (QuickKey, EconomyRules)?

    static func rules(_ app: AppModel) -> EconomyRules { rules(app.tuning) }

    static func rules(_ tuning: Tuning) -> EconomyRules {
        // called from view bodies (the lives pill ticks every second): the identity check must cost nothing — the files'
        // sizes + the override count; the full key (contents hash) is computed only when that identity changes
        let quick = QuickKey(rules: tuning.rules.data?.count ?? -1, social: tuning.social.file.data?.count ?? -1,
                             overrides: tuning.rules.overrides.count)
        if let last, last.0 == quick { return last.1 }
        let key = "\(tuning.rules.data?.hashValue ?? 0)|\(tuning.social.file.data?.hashValue ?? 0)|"
            + tuning.rules.overrides.sorted { $0.key < $1.key }.map { "\($0.key)=\($0.value)" }.joined(separator: ",")
        if let hit = cache[key] { last = (quick, hit); return hit }
        var (r, problems) = EconomyRules.load(rules: tuning.rules.data, social: tuning.social.file.data,
                                              overrides: tuning.rules.overrides)
        EventRotationPolicy.apply(&r)                                   // B1: the same rotation table as AppModel.economy
        // template phase 5: the active module's own boosters (their stock and packs), as AppModel.economy (none for ArrowEscape)
        r.addModuleBoosters(ActivePuzzle.entry.moduleBoosters(bundle: .main, tune: LaunchArgs.current.tune))
        for p in problems { Log.error("shop", "economy table: \(p)") }
        cache[key] = r
        last = (quick, r)
        return r
    }

    /// A completed purchase: grants the product once per transaction id and writes the save at once. nil = a replay (the id
    /// was processed before) or a product the catalogue does not know.
    @discardableResult
    static func applyPurchase(store: PlayerStore, rules: EconomyRules, productID: String, transactionID: String,
                              now: Date) -> Grant? {
        let g = store.mutateAndSave {
            Economy.applyPurchase(&$0, productID: productID, transactionID: transactionID, now: now, rules: rules)
        }
        if let g {
            Log.mark("shop", "granted \(productID) tx \(transactionID): coins +\(g.coins) boosters \(g.boosters.sorted { $0.key < $1.key }) "
                     + "∞ \(Int(g.unlimitedLives)) s → coins \(store.state.coins)")
        } else {
            Log.mark("shop", "no grant for \(productID) tx \(transactionID) (already processed or unknown)")
        }
        return g
    }

    /// The live lives count and the next-life countdown (refills applied at the effective time).
    static func lives(_ app: AppModel) -> LivesStatus {
        Economy.lives(app.store.state, now: app.clock.wallClock(), rules: rules(app))
    }
}

/// The catalogue's titles and the section a product sits in (SPEC-gameplay §9.4, §16.8; strings keys = these literals).
enum ShopTitles {
    static func title(_ p: ShopProduct) -> LocalizedStringResource {
        switch p.id {
        case "offer.special": return "Special Offer"
        case "bundle.mini": return "Mini Bundle"
        case "bundle.epic": return "Epic Bundle"
        case "bundle.elite": return "Elite Bundle"
        case "bundle.mega": return "Mega Bundle"
        case "bundle.legendary": return "Legendary Bundle"
        default: return "Coins"
        }
    }

    /// The English title (StoreProductInfo.displayName and the logs; the page draws `title`).
    static func english(_ p: ShopProduct) -> String {
        switch p.id {
        case "offer.special": return "Special Offer"
        case "bundle.mini": return "Mini Bundle"
        case "bundle.epic": return "Epic Bundle"
        case "bundle.elite": return "Elite Bundle"
        case "bundle.mega": return "Mega Bundle"
        case "bundle.legendary": return "Legendary Bundle"
        default: return "\(ShopFormat.amount(p.grant.coins)) Coins"
        }
    }
}

/// Number formats of the shop (SPEC-ui §2.12.2: a thin space groups thousands, "1 000", in both languages). Money is never
/// formatted here: the Shop shows StoreKit's `displayPrice` (A1, release-plan §3.2); the DEBUG FakeStore's reference price
/// lists live in FakeStore.swift (DEBUG only).
enum ShopFormat {
    /// "1 000", "60 000", "100 000" (U+2009 THIN SPACE, VERIFIED EN on a TR phone).
    static func amount(_ n: Int) -> String {
        let digits = String(abs(n))
        var out = ""
        for (i, ch) in digits.enumerated() {
            if i > 0 && (digits.count - i) % 3 == 0 { out.append("\u{2009}") }
            out.append(ch)
        }
        return (n < 0 ? "-" : "") + out
    }

    /// "1h", "3h", "72h" for an unlimited-lives duration; "30m" below an hour.
    static func duration(_ seconds: Double) -> String {
        let m = Int((seconds / 60).rounded())
        return m >= 60 && m % 60 == 0 ? "\(m / 60)h" : (m >= 60 ? "\(m / 60)h \(m % 60)m" : "\(m)m")
    }
}
