import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// SPEC-architecture §4.17 "EconomyTests" (C3): start 1000; rewards 20/60/100/80 banked at the win; the FTUE payout
/// 1000 → 1120 banked and flown; continues 900; the attempt bookkeeping; purchases once; every value from the tuning data
/// (SPEC-gameplay §15 decodes to exactly the compiled defaults).
final class EconomyTests: XCTestCase {
    let r = C3.rules
    let t0 = C3.trt("12:00:00")

    // MARK: install

    func testAFreshInstallComesFromTheRules() {
        let s = C3.fresh()
        XCTAssertEqual(s.coins, 1000)                                   // VERIFIED vflows §8
        XCTAssertEqual(s.boosters, ["freeze": 3, "hint": 3])            // VERIFIED badges "3"
        XCTAssertEqual(s.lives, LivesState(count: 5, anchor: nil))
        XCTAssertEqual(s.level, 1)
        XCTAssertEqual(s.pendingCoinFly, 0)
        var other = r
        other.economy.startCoins = 250
        other.economy.startBoosters = ["freeze": 1]
        other.lives.max = 3
        let o = Economy.freshState(installSeed: 7, installDate: t0, rules: other)
        XCTAssertEqual([o.coins, o.boosters["freeze"] ?? -1, o.boosters["hint"] ?? 0, o.lives.count], [250, 1, 0, 3])
        XCTAssertEqual(o.installSeed, 7)
        XCTAssertEqual(o.installDate, t0)
    }

    // MARK: rewards, banked at the win

    /// Plays a session on tiny one-arrow boards through the REAL `LevelSession` and returns its WinResult.
    func play(_ levels: [Int], tag: LevelTag = .normal, reward: Int? = nil, attempt: Int = 1) throws -> WinResult {
        let stages = levels.map { C2Fixtures.level(6, 3, [C2Fixtures.arrow(0, [(0, 1), (1, 1)], .right)], n: $0, tag: tag) }
        let s = LevelSession(plan: SessionPlan(id: Economy.sessionID(levels), levels: levels, reward: reward),
                             stages: stages, setup: AttemptSetup(levels: levels, attemptIndex: attempt))
        _ = s.start()
        for step in 0..<40 {
            switch s.phase {
            case .won(let w): return w
            case .intro: _ = s.ack(.introFinished)
            case .ready, .playing: _ = s.tap(s.board.live.first, at: Double(step))
            case .stageClear: _ = s.ack(.stageTransitionDone)
            default: XCTFail("unexpected \(s.phase)"); return C3.win(levels)
            }
        }
        XCTFail("not won")
        return C3.win(levels)
    }

    func testRewardsTwentySixtyHundredAndEightyAreBankedAtTheWin() throws {
        for (tag, coins) in [(LevelTag.normal, 20), (.hard, 60), (.superHard, 100)] {
            var s = C3.fresh()
            s.level = 34
            let w = try play([34], tag: tag)
            XCTAssertEqual(w.reward, coins)
            guard case .success = Economy.startAttempt(&s, levels: [34], now: t0, rules: r) else { return XCTFail() }
            XCTAssertEqual(Economy.finishAttempt(&s, outcome: .won(w), now: t0, rules: r), [.coins(coins)])
            XCTAssertEqual(s.coins, 1000 + coins, "\(tag)")
            XCTAssertEqual(s.pendingCoinFly, coins)
            XCTAssertEqual(s.level, 35)
        }
        // "Levels 1-4": one session of four boards, one panel, 80 (sessions.json reward)
        let w = try play([1, 2, 3, 4], reward: 80)
        XCTAssertEqual(w.reward, 80)
        XCTAssertEqual(w.levels, [1, 2, 3, 4])
    }

    func testTheFTUEPayoutIsBankedAndFlownOnTheFirstHome() throws {
        var s = C3.fresh()
        for (levels, reward) in [([1, 2, 3, 4], 80), ([5], nil), ([6], nil)] as [([Int], Int?)] {
            let w = try play(levels, reward: reward)
            guard case .success(let setup) = Economy.startAttempt(&s, levels: levels, now: t0, rules: r) else { return XCTFail() }
            XCTAssertEqual(setup.attemptIndex, 1)
            Economy.finishAttempt(&s, outcome: .won(w), now: t0.addingTimeInterval(60), rules: r)
            XCTAssertNil(s.activeAttempt, "banked at once (kill-safe)")
        }
        XCTAssertEqual(s.coins, 1120)                                   // banked
        XCTAssertEqual(s.pendingCoinFly, 120)                           // not flown yet
        XCTAssertEqual(s.level, 7)
        XCTAssertEqual(s.stats.firstTryWins, 6, "Levels 1-4 counts four wins (VERIFIED 10 at L11)")
        XCTAssertEqual(s.lives.count, 5)
        // the first home: the pill starts at coins − pending and the fly adds the rest
        XCTAssertEqual(s.coins - s.pendingCoinFly, 1000)
        XCTAssertEqual(Economy.takeCoinFly(&s), 120)
        XCTAssertEqual(s.pendingCoinFly, 0)
        XCTAssertEqual(s.coins, 1120)
        XCTAssertEqual(Economy.takeCoinFly(&s), 0)
    }

    func testFinishingTwiceBanksOnce() {
        var s = C3.fresh()
        _ = Economy.startAttempt(&s, levels: [8], now: t0, rules: r)
        XCTAssertEqual(Economy.finishAttempt(&s, outcome: .won(C3.win([8])), now: t0, rules: r), [.coins(20)])
        XCTAssertEqual(Economy.finishAttempt(&s, outcome: .won(C3.win([8])), now: t0, rules: r), [])
        XCTAssertEqual(Economy.finishAttempt(&s, outcome: .lost(.quit), now: t0, rules: r), [])
        XCTAssertEqual(s.coins, 1020)
        XCTAssertEqual(s.stats, PlayerState.Stats(wins: 1, losses: 0, firstTryWins: 1, weeklyContestWins: 0, playSeconds: 0))
    }

    // MARK: continues, the 900-coin sinks

    func testContinuesCostNineHundred() {
        for kind in [ContinueOffer.Kind.outOfTime, .outOfHearts] {
            let chain = RulesTuning.default.chain(kind, streakActive: true)
            XCTAssertEqual(chain.map(\.price), [900, 900, 900], "\(kind)")
        }
        var s = C3.fresh()
        let price = RulesTuning.default.chain(.outOfTime, streakActive: false)[0].price
        XCTAssertTrue(Economy.canAfford(s, price))
        XCTAssertTrue(Economy.spend(&s, price))
        XCTAssertEqual(s.coins, 100)
        XCTAssertFalse(Economy.canAfford(s, price))
        XCTAssertFalse(Economy.spend(&s, price), "short: nothing changes (the Shop opens over the popup)")
        XCTAssertFalse(Economy.spend(&s, -5))
        XCTAssertEqual(s.coins, 100)
        XCTAssertEqual(r.lives.refillPrice, 900)
        XCTAssertEqual(r.economy.boosterPack, EconomyRules.BoosterPack(count: 3, price: 900))
    }

    // MARK: the attempt

    func testTheAttemptBookkeeping() {
        var s = C3.fresh()
        s.boosters = ["freeze": 2, "hint": 0]
        guard case .success(let a) = Economy.startAttempt(&s, levels: [1, 2, 3, 4], now: t0, rules: r) else { return XCTFail() }
        XCTAssertEqual(a.levels, [1, 2, 3, 4])
        XCTAssertEqual(a.attemptIndex, 1)
        XCTAssertEqual(a.seed, PathRandom.attemptSeed(install: 42, level: 1, attempt: 1))
        XCTAssertEqual(a.boosters, [.freeze: 2, .hint: 0])
        XCTAssertEqual(a.firstStage, 0)
        XCTAssertEqual(s.activeAttempt, ActiveAttempt(session: "L1-4", levels: [1, 2, 3, 4], attemptIndex: 1, startedAt: t0))
        XCTAssertEqual(Economy.startAttempt(&s, levels: [5], now: t0, rules: r).failure, .attemptInProgress)
        XCTAssertEqual(Economy.startAttempt(&s, levels: [], now: t0, rules: r).failure, .noLevels)
        Economy.finishAttempt(&s, outcome: .lost(.timeUp), now: t0.addingTimeInterval(95.5), rules: r)
        XCTAssertEqual(s.stats.losses, 1)
        XCTAssertEqual(s.stats.playSeconds, 95, "whole seconds of the rewind-safe clock")
        guard case .success(let b) = Economy.startAttempt(&s, levels: [1, 2, 3, 4], now: t0, rules: r) else { return XCTFail() }
        XCTAssertEqual(b.attemptIndex, 2, "Try Again is a new attempt: not a first try")
        XCTAssertEqual(s.attempts, [1: 2])
        XCTAssertEqual(Economy.sessionID([32]), "L32")
    }

    // MARK: purchases

    func testAPurchaseGrantsOncePerTransaction() {
        var s = C3.fresh()
        let id = r.shop.storeID(r.shop.product("bundle.elite")!)
        XCTAssertEqual(id, "com.manycode.arrowout.bundle.elite")
        let g = Economy.applyPurchase(&s, productID: id, transactionID: "2000000000000001", now: t0, rules: r)
        XCTAssertEqual(g, Grant(coins: 8000, boosters: ["freeze": 8, "hint": 8], unlimitedLives: 12 * 3600))
        XCTAssertEqual(s.coins, 9000)
        XCTAssertEqual(s.boosters, ["freeze": 11, "hint": 11])
        XCTAssertEqual(s.unlimitedLivesUntil, t0.addingTimeInterval(12 * 3600))
        XCTAssertNil(Economy.applyPurchase(&s, productID: id, transactionID: "2000000000000001", now: t0, rules: r), "a replay grants nothing")
        XCTAssertNil(Economy.applyPurchase(&s, productID: "com.manycode.arrowout.nope", transactionID: "x", now: t0, rules: r))
        XCTAssertEqual(s.coins, 9000)
        // the Special Offer: once per install, then its card disappears
        XCTAssertEqual(r.shop.visible(s).count, 12)
        XCTAssertNotNil(Economy.applyPurchase(&s, productID: "offer.special", transactionID: "t2", now: t0, rules: r))
        XCTAssertEqual(r.shop.visible(s).map(\.id).first, "bundle.mini")
        XCTAssertEqual(r.shop.visible(s).count, 11)
    }

    func testTheShopIsTheSpecTable() {
        let p = r.shop.products
        XCTAssertEqual(p.map(\.id), ["offer.special", "bundle.mini", "bundle.epic", "bundle.elite", "bundle.mega", "bundle.legendary",
                                     "coins.1000", "coins.5000", "coins.10000", "coins.25000", "coins.50000", "coins.100000"])
        XCTAssertEqual(p.map(\.section), ["offer"] + Array(repeating: "bundle", count: 5) + Array(repeating: "coins", count: 6))
        XCTAssertEqual(p.compactMap(\.priceUSD), [0.99, 4.99, 9.99, 19.99, 49.99, 99.99, 1.99, 7.99, 14.99, 29.99, 54.99, 99.99])
        XCTAssertEqual(p.compactMap(\.priceTRY), [49.99, 249.99, 499.99, 999.99, 2499.99, 4999.99, 99.99, 399.99, 799.99, 1499.99,
                                                   2999.99, 4999.99])
        // A1 (ruling 38, requirement change): the Special Offer's badge is the honest "STARTER", no longer v552's "90% OFF"
        XCTAssertEqual(p.compactMap(\.badge), ["STARTER", "Popular", "Best Value"])
        XCTAssertEqual(p.map(\.grant.coins), [1000, 2000, 4000, 8000, 20000, 60000, 1000, 5000, 10000, 25000, 50000, 100000])
        XCTAssertEqual(p.map { $0.grant.boosters["hint"] ?? 0 }, [1, 1, 3, 8, 18, 36, 0, 0, 0, 0, 0, 0])
        XCTAssertEqual(p.map { $0.grant.unlimitedLives / 3600 }, [1, 3, 6, 12, 36, 72, 0, 0, 0, 0, 0, 0])
        XCTAssertEqual(r.shop.storeIDs.count, 12)
        XCTAssertTrue(r.shop.storeIDs.allSatisfy { $0.hasPrefix("com.manycode.arrowout.") })
    }

    // MARK: every value is tuning data

    func testTheSpecSection15DecodesToExactlyTheCompiledDefaults() throws {
        let spec = try Data(contentsOf: C3.fixture("c3_rules_spec15.json"))
        let social = try Data(contentsOf: C3.fixture("c3_social_spec15.json"))
        let (loaded, problems) = EconomyRules.load(rules: spec, social: social)
        XCTAssertEqual(problems, [])
        XCTAssertEqual(EconomyRules.unknownKeys(in: spec), [], "every §15 key of the C3 sections is decoded")
        XCTAssertEqual(loaded.lives.refillSeconds, 1800)
        XCTAssertEqual(loaded.claw.ladder.map(\.threshold),
                       [1, 200, 300, 400, 300, 500, 500, 600, 600, 700, 700, 800, 800, 1000, 900, 1000, 1000, 1100, 1200, 1500])
        XCTAssertEqual(loaded, EconomyRules.default, "the compiled defaults ARE SPEC-gameplay §15")
        // the C3 sections round-trip through JSON (the tuning file can be written from the defaults)
        let again = try JSONDecoder().decode(EconomyRules.self, from: JSONEncoder().encode(loaded))
        XCTAssertEqual(again, loaded)
    }

    func testTheShippedTuningFilesDecode() throws {
        let dir = C3.appRoot.appendingPathComponent("App/Resources/Tuning")
        let rules = try Data(contentsOf: dir.appendingPathComponent("rules.json"))
        let social = try Data(contentsOf: dir.appendingPathComponent("social.json"))
        let (loaded, problems) = EconomyRules.load(rules: rules, social: social)
        XCTAssertEqual(problems, [])
        XCTAssertEqual(EconomyRules.unknownKeys(in: rules), [])
        // whatever the shipped file says wins over the compiled default (today's file may still carry the old 1200 s:
        // a request to CORE/C2 per SPEC-gameplay §17.1 item 3; the compiled default is the VERIFIED 1800)
        let raw = try XCTUnwrap(JSONSerialization.jsonObject(with: rules) as? [String: Any])
        let fileRefill = (raw["lives"] as? [String: Any])?["refillSeconds"] as? Double
        XCTAssertEqual(loaded.lives.refillSeconds, fileRefill ?? 1800)
        C3.evidence("shipped-tuning.txt", "rules.json lives.refillSeconds = \(fileRefill.map { "\($0)" } ?? "absent") → "
                    + "EconomyRules.lives.refillSeconds = \(loaded.lives.refillSeconds); C3 sections present: "
                    + "\(EconomyRules.rulesSections.filter { raw[$0] != nil }); social.json keys: "
                    + "\(((try? JSONSerialization.jsonObject(with: social)) as? [String: Any])?.keys.sorted() ?? [])\n")
    }

    func testOverridesAndBrokenFilesNeverCrash() {
        let (o, p) = EconomyRules.load(rules: Data(#"{"lives":{"refillSeconds":1200},"combo":{"window":9}}"#.utf8),
                                       overrides: ["lives.refillSeconds": "60", "economy.startCoins": "5",
                                                   "events.unlocks.skyJump": "41", "combo.window": "3"])
        XCTAssertEqual(p, [])
        XCTAssertEqual(o.lives.refillSeconds, 60)
        XCTAssertEqual(o.economy.startCoins, 5)
        XCTAssertEqual(o.events.unlocks["skyJump"], 41)
        XCTAssertEqual(o.events.unlocks["rocketRace"], 55)
        let (bad, problems) = EconomyRules.load(rules: Data("[1,2]".utf8), social: Data("nope".utf8))
        XCTAssertEqual(bad, .default)
        XCTAssertEqual(problems.count, 2)
        let (wrongType, pt) = EconomyRules.load(rules: Data(#"{"lives":{"max":"five"}}"#.utf8))
        XCTAssertEqual(wrongType, .default)
        XCTAssertEqual(pt.count, 1)
        XCTAssertEqual(EconomyRules.unknownKeys(in: Data(#"{"lives":{"maxx":1},"economy":{"startCoins":1},"tape":{}}"#.utf8)),
                       ["lives.maxx"])
    }

    func testEventValuesComeFromSocialJSON() {
        let (e, p) = EventRules.load(social: Data(#"{"unlocks":{"skyJump":45},"events":{"skyJump":{"pools":[1,2,3]},"weekly":{"prizes":[9]}}}"#.utf8))
        XCTAssertEqual(p, [])
        XCTAssertEqual(e.unlocks, ["streakRace": 30, "clawChallenge": 33, "skyJump": 45, "weeklyContest": 50, "rocketRace": 55])
        XCTAssertEqual(e.skyJump.pools, [1, 2, 3])
        XCTAssertEqual(e.skyJump.levels, [5, 7, 10])
        XCTAssertEqual(e.weekly.prizes, [9])
        XCTAssertEqual(EventRules.load(social: Data("{}".utf8)).rules, .default)
        XCTAssertEqual(EventRules.load(social: nil).rules, .default)
    }
}
