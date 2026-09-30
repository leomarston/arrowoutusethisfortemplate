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

    /// The streak multiplier steps (`rules.json streak.steps`): the Continue? chips and token count, the Streak Race strip.
    /// Moved from the Streak Race's StreakStripSource in the kit decoupling step (the fail flow reads it without the event).
    static func streakSteps(_ app: AppModel) -> [Int] {
        let v = app.tuning.rules.doubles("streak.steps", [1, 5, 10, 25, 100]).map { Int($0) }
        return v.isEmpty ? [1, 5, 10, 25, 100] : v
    }

    /// The live lives count and the next-life countdown (refills applied at the effective time).
    static func lives(_ app: AppModel) -> LivesStatus {
        Economy.lives(app.store.state, now: app.clock.wallClock(), rules: rules(app))
    }
}
