import XCTest
import Foundation
@testable import PathCore

/// SPEC-architecture §4.17 "BoostersTests" (C3; §4.9, SPEC-gameplay §6): the two v552 boosters, 3 each at install, the
/// hourglass freezes 10 s (+ the 1.6 s flight, K-3), the bulb hints one unit; stock is the player's (use / buy ×3 for 900);
/// the effects are C2's session knobs (one source of truth) and the session hook never touches stock.
final class BoostersTests: XCTestCase {
    let r = C3.rules

    func testTheBoosterTable() {
        let table = r.boosterRules()
        XCTAssertEqual(table.map(\.id), [.freeze, .hint])
        XCTAssertEqual(table[0], BoosterRule(id: .freeze, effect: .freezeTimer(seconds: 10), startStock: 3, price: 900, packCount: 3))
        XCTAssertEqual(table[1], BoosterRule(id: .hint, effect: .hint(units: 1), startStock: 3, price: 900, packCount: 3))
        XCTAssertTrue(table.allSatisfy { $0.unlockLevel == nil }, "both from the first board (VERIFIED: no booster unlock)")
        // the effects are RulesTuning's (C2) values: change them there and the table follows
        var b = RulesTuning.Boosters()
        b.freezeSeconds = 7
        b.hintUnits = 2
        b.actions["dome"] = RulesTuning.BoosterAction.none
        let custom = r.boosterRules(b)
        XCTAssertEqual(custom.map(\.effect), [.custom("dome"), .freezeTimer(seconds: 7), .hint(units: 2)])
        XCTAssertEqual(custom.first?.startStock, 0)
        XCTAssertEqual(RulesTuning.default.boosters.freezeTotal, 11.6, "10 s countdown + the 1.6 s flight (K-3), clock frozen for both")
    }

    func testUsingTakesOneFromStockAndNeverGoesBelowZero() {
        var s = C3.fresh()
        for left in [2, 1, 0] {
            XCTAssertTrue(Economy.useBooster(&s, .freeze))
            XCTAssertEqual(Economy.stock(s, .freeze), left)
        }
        XCTAssertFalse(Economy.useBooster(&s, .freeze), "0 stock: the buy popup instead")
        XCTAssertEqual(s.boosters["freeze"], 0)
        XCTAssertEqual(Economy.stock(s, .hint), 3)
        XCTAssertFalse(Economy.useBooster(&s, BoosterID("dome")))
    }

    func testBuyThreeForNineHundredAtZeroStock() {
        var s = C3.fresh()
        s.boosters["hint"] = 0
        XCTAssertTrue(Economy.buyBooster(&s, .hint, rules: r))
        XCTAssertEqual(Economy.stock(s, .hint), 3)
        XCTAssertEqual(s.coins, 100)
        XCTAssertFalse(Economy.buyBooster(&s, .hint, rules: r), "short of coins: nothing changes (the Shop opens)")
        XCTAssertEqual(Economy.stock(s, .hint), 3)
        XCTAssertEqual(s.coins, 100)
        var dear = r
        dear.economy.boosterPack = .init(count: 5, price: 50)
        XCTAssertTrue(Economy.buyBooster(&s, .freeze, rules: dear))
        XCTAssertEqual(Economy.stock(s, .freeze), 8)
        XCTAssertEqual(s.coins, 50)
        XCTAssertFalse(Economy.buyBooster(&s, BoosterID("dome"), rules: r), "not in the table: not for sale")
    }

    func testRewardsAddStock() {
        var s = C3.fresh()
        Economy.grant(&s, .booster(.hint, 1), now: C3.trt("12:00:00"))                   // Claw step 6
        Economy.grant(&s, .booster(.freeze, 2), now: C3.trt("12:00:00"))                 // Claw step 11
        XCTAssertEqual(s.boosters, ["freeze": 5, "hint": 4])
    }

    func testTheSessionHookNeverTouchesStock() {
        // GAME: stock > 0 → Economy.useBooster + session.useBooster (§8.4 BoosterDirector)
        let level = C2Fixtures.level(6, 3, [C2Fixtures.arrow(0, [(0, 1), (1, 1)], .right)], n: 62)
        let session = LevelSession(plan: SessionPlan(id: "L62", levels: [62]), stages: [level], setup: AttemptSetup(levels: [62]))
        _ = session.start(); _ = session.ack(.introFinished)
        var s = C3.fresh()
        XCTAssertTrue(Economy.useBooster(&s, .freeze))
        let ev = session.useBooster(.freeze)
        XCTAssertEqual(ev.first, .boosterUsed(.freeze))
        XCTAssertTrue(ev.contains(.freezeStarted(seconds: RulesTuning.default.boosters.freezeTotal)))
        XCTAssertEqual(Economy.stock(s, .freeze), 2)
        XCTAssertFalse(session.clock.started, "a booster never starts the timer")
    }
}
