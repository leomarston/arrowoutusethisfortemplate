import Foundation

// C3 (SPEC-architecture §4.8, §8.4–§8.6; SPEC-gameplay §7–§9). Pure transforms of `PlayerState`: the attempt bookkeeping
// (the lives gate, the life taken at the start and given back on a win, a killed app = a failed attempt), coins, grants,
// boosters, purchases. Adapted from MF Economy (e10a076): MF's stars / pre-boosters / pieces are gone; ours are the tag
// rewards (C2's `RulesTuning.rewards` → `WinResult.reward`), the session reward (`SessionPlan.reward`, 80 for "Levels 1-4")
// and the 900-coin sinks. The event hooks (streak multiplier, Claw, races) are `Events.onWin` / `Events.onLoss`.
//
// Order for GAME (one `store.mutate`, then an immediate save — kill-safe, arch §8.4):
//   Play / Try Again  → `startAttempt` (the lives gate; `.noLives` → the More Lives popup, SPEC-gameplay §8.2)
//   win (at the tap)  → `finishAttempt(.won(result))` + `Events.onWin(...)`
//   Level Failed / Quit → `finishAttempt(.lost(reason))` + `Events.onLoss(...)`
//   launch            → `reconcileOnLaunch` (refills, ∞ end, the kill rule incl. its event hook)
// Every `now:` is the device wall clock; C3 turns it into the rewind-safe effective time itself (`EconomyClock`).

public enum Economy {}

public enum AttemptOutcome: Equatable, Sendable {
    case won(WinResult)
    case lost(LossReason)
}

public enum StartError: Error, Equatable, Sendable {
    /// 0 lives and no ∞: show More Lives instead of the level (SPEC-gameplay §8.2).
    case noLives
    /// `finishAttempt` was not called for the previous attempt (a GAME bug; the store keeps the running attempt).
    case attemptInProgress
    case noLevels
}

public enum LaunchNotice: Equatable, Sendable {
    /// The device clock is behind the saved high-water mark by this many seconds: lives and events wait for it.
    case clockBehind(seconds: Int64)
    case livesRefilled(from: Int, to: Int)
    case unlimitedEnded
    /// The app was killed during this attempt. `countedAsLoss` = the kill rule applied (`lives.killIsLoss`); `outcomes` are
    /// the event consequences (the streak reset, a Sky Jump run failed).
    case killedAttempt(levels: [Int], countedAsLoss: Bool, outcomes: [EventOutcome])
}

extension Economy {

    // MARK: install

    /// A fresh install: start coins and booster stock from the rules, full lives, the install seed and date.
    public static func freshState(installSeed: UInt64, installDate: Date, rules: EconomyRules) -> PlayerState {
        var s = PlayerState(installSeed: installSeed, installDate: installDate)
        s.coins = rules.economy.startCoins
        s.boosters = rules.economy.startBoosters
        s.lives = LivesState(count: rules.lives.max, anchor: nil)
        return s
    }

    // MARK: the attempt

    /// The session id an attempt is saved under: "L32", or "L1-4" for a multi-board session (= sessions.json ids).
    public static func sessionID(_ levels: [Int]) -> String {
        guard let f = levels.first else { return "" }
        guard levels.count > 1, let l = levels.last else { return "L\(f)" }
        return "L\(f)-\(l)"
    }

    /// Play / Try Again: the lives gate, then the attempt is recorded (`activeAttempt`, `attempts[first] += 1`) and — under
    /// `lives.cost == .atStart` without ∞ — one life is taken. ∞ lives are checked HERE only (VERIFIED fail.md §2 #1).
    public static func startAttempt(_ s: inout PlayerState, levels: [Int], now: Date,
                                    rules: EconomyRules) -> Result<AttemptSetup, StartError> {
        guard let first = levels.first else { return .failure(.noLevels) }
        guard s.activeAttempt == nil else { return .failure(.attemptInProgress) }
        let t = EconomyClock.now(&s, wall: now)
        normalizeLives(&s, at: t, rules.lives)
        let free = unlimited(s, at: t)
        if !free && s.lives.count <= 0 { return .failure(.noLives) }
        if !free && rules.lives.cost == .atStart { takeLife(&s, at: t, rules.lives) }
        s.events.attemptFree = free
        let index = (s.attempts[first] ?? 0) + 1
        s.attempts[first] = index
        s.activeAttempt = ActiveAttempt(session: sessionID(levels), levels: levels, attemptIndex: index, startedAt: t, stage: 0)
        var stock: [BoosterID: Int] = [:]
        for (k, v) in s.boosters { stock[BoosterID(k)] = max(0, v) }
        return .success(AttemptSetup(levels: levels, attemptIndex: index,
                                     seed: PathRandom.attemptSeed(install: s.installSeed, level: first, attempt: index),
                                     boosters: stock, firstStage: 0))
    }

    /// The end of the running attempt. A win gives the life back (`.atStart`), banks the reward (coins AND the pending home
    /// coin fly, SPEC-gameplay §9.1), counts the win(s) (First Try Wins when `result.firstTry`; a multi-board session counts
    /// each of its levels) and moves `level` past the
    /// session. A loss costs nothing more under `.atStart` (the start took the life) and one life under `.atLoss`. Returns
    /// the grants banked. Finishing twice banks once (no running attempt → nothing happens).
    @discardableResult
    public static func finishAttempt(_ s: inout PlayerState, outcome: AttemptOutcome, now: Date, rules: EconomyRules) -> [Grant] {
        guard let attempt = s.activeAttempt else { return [] }
        let t = EconomyClock.now(&s, wall: now)
        let free = s.events.attemptFree
        var grants: [Grant] = []
        switch outcome {
        case .won(let r):
            if !free && rules.lives.cost == .atStart { giveLifeBack(&s, at: t, rules.lives) }
            if r.reward > 0 {
                s.coins += r.reward
                s.pendingCoinFly += r.reward
                grants.append(.coins(r.reward))
            }
            // "Levels 1-4" counts as four wins (VERIFIED First Try Wins 10 at L11 = L1–4 + L5–L10, SPEC-gameplay §10.2)
            let n = max(1, r.levels.count)
            s.stats.wins += n
            if r.firstTry { s.stats.firstTryWins += n }
            let last = (r.levels.isEmpty ? attempt.levels : r.levels).max() ?? s.level
            s.level = max(s.level, last + 1)
        case .lost:
            if !free && rules.lives.cost == .atLoss { takeLife(&s, at: t, rules.lives) }
            s.stats.losses += 1
        }
        if outcome != .lost(.killed) {                          // a kill's time until the relaunch is not play time
            s.stats.playSeconds += max(0, t.timeIntervalSince(attempt.startedAt))
        }
        s.activeAttempt = nil
        s.events.attemptFree = false
        return grants
    }

    /// At launch: the refills due, the end of ∞, and an attempt the app was killed in (`lives.killIsLoss`: a failed
    /// attempt — its life stays spent, the streak resets, a Sky Jump run fails; else the attempt is forgotten and its life
    /// given back).
    @discardableResult
    public static func reconcileOnLaunch(_ s: inout PlayerState, now: Date, rules: EconomyRules) -> [LaunchNotice] {
        var notices: [LaunchNotice] = []
        let wallSeconds = Int64(now.timeIntervalSince1970.rounded(.down))
        if s.social.highWater > wallSeconds { notices.append(.clockBehind(seconds: s.social.highWater - wallSeconds)) }
        let t = EconomyClock.now(&s, wall: now)
        let before = s.lives.count
        let gained = normalizeLives(&s, at: t, rules.lives)
        if gained > 0 { notices.append(.livesRefilled(from: before, to: s.lives.count)) }
        if let u = s.unlimitedLivesUntil, u <= t { s.unlimitedLivesUntil = nil; notices.append(.unlimitedEnded) }
        if let a = s.activeAttempt {
            if rules.lives.killIsLoss {
                finishAttempt(&s, outcome: .lost(.killed), now: now, rules: rules)
                let out = Events.onLoss(&s, LossContext(levels: a.levels, reason: .killed, now: now), rules: rules)
                notices.append(.killedAttempt(levels: a.levels, countedAsLoss: true, outcomes: out))
            } else {
                if !s.events.attemptFree && rules.lives.cost == .atStart { giveLifeBack(&s, at: t, rules.lives) }
                if let first = a.levels.first, let n = s.attempts[first] { s.attempts[first] = n > 1 ? n - 1 : nil }
                s.activeAttempt = nil
                s.events.attemptFree = false
                notices.append(.killedAttempt(levels: a.levels, countedAsLoss: false, outcomes: []))
            }
        }
        return notices
    }

    // MARK: coins

    /// Pays `coins` (a continue, Refill, a booster pack). False (nothing changes) when short or negative.
    public static func spend(_ s: inout PlayerState, _ coins: Int) -> Bool {
        guard coins >= 0, s.coins >= coins else { return false }
        s.coins -= coins
        return true
    }

    public static func canAfford(_ s: PlayerState, _ coins: Int) -> Bool { coins >= 0 && s.coins >= coins }

    /// The home's coin fly: returns the banked amount not yet flown and clears it (1000 → 1120 on the first home).
    public static func takeCoinFly(_ s: inout PlayerState) -> Int {
        let n = max(0, s.pendingCoinFly)
        s.pendingCoinFly = 0
        return n
    }

    // MARK: grants

    /// Coins, boosters and unlimited lives (stacking at the effective time: `until = max(until, now) + duration`).
    public static func grant(_ s: inout PlayerState, _ g: Grant, now: Date) {
        let t = EconomyClock.now(&s, wall: now)
        s.coins = max(0, s.coins + g.coins)
        for (k, n) in g.boosters where n != 0 { s.boosters[k] = max(0, (s.boosters[k] ?? 0) + n) }
        addUnlimited(&s, seconds: g.unlimitedLives, at: t)
    }

    // MARK: boosters

    /// Takes one from stock. False (nothing changes) at 0 stock: then the booster popup (SPEC-gameplay §6.4).
    public static func useBooster(_ s: inout PlayerState, _ b: BoosterID) -> Bool {
        let n = stock(s, b)
        guard n > 0 else { return false }
        s.boosters[b.rawValue] = n - 1
        return true
    }

    /// "Buy ×3 [coin] 900": coins − pack price, stock + pack count. False (nothing changes) when short or not for sale.
    public static func buyBooster(_ s: inout PlayerState, _ b: BoosterID, rules: EconomyRules) -> Bool {
        guard let rule = rules.boosterRules().first(where: { $0.id == b }), let price = rule.price, rule.packCount > 0 else {
            return false
        }
        guard spend(&s, price) else { return false }
        s.boosters[b.rawValue] = stock(s, b) + rule.packCount
        return true
    }

    // MARK: purchases

    /// A completed store transaction: grants the product once per transaction id (`processedTransactions`), marks a
    /// once-only offer as bought. Returns the grant, or nil for a replay / an unknown product.
    public static func applyPurchase(_ s: inout PlayerState, productID: String, transactionID: String, now: Date,
                                     rules: EconomyRules) -> Grant? {
        guard !s.processedTransactions.contains(transactionID), let p = rules.shop.product(productID) else { return nil }
        s.processedTransactions.insert(transactionID)
        grant(&s, p.grant, now: now)
        if rules.shop.specialOfferOnce && p.section == "offer" { s.flags.seen.insert(ShopCatalog.boughtFlag(p.id)) }
        return p.grant
    }
}
