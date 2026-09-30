import XCTest
import Foundation
@testable import GameCore

/// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §8c): a puzzle module's boosters carry their OWN pack
/// (`EconomyRules.economy.boosterPacks`, by booster id), added at boot from the module's data for the ids rules.json does not
/// list. rules.json lists none, so the reference game's table, prices and decoding are unchanged.
final class ModuleBoosterPackTests: XCTestCase {

    func testTheReferenceTableIsUnchangedWithoutModulePacks() throws {
        let r = EconomyRules.default
        XCTAssertEqual(r.economy.boosterPacks, [:], "rules.json lists no per-booster pack")
        XCTAssertEqual(r.boosterRules().map(\.id), [.freeze, .hint])
        XCTAssertEqual(r.boosterPack(for: .freeze), r.economy.boosterPack)
        XCTAssertEqual(r.boosterPack(for: BoosterID("undo")), r.economy.boosterPack, "an unknown id falls back to the shared pack")
        // the shipped rules.json decodes to the same table and names no unknown key
        let rules = try Data(contentsOf: C3.appRoot.appendingPathComponent("App/Resources/Tuning/rules.json"))
        XCTAssertEqual(EconomyRules.load(rules: rules).rules.economy.boosterPacks, [:])
        XCTAssertEqual(EconomyRules.unknownKeys(in: rules), [])
    }

    func testAModuleBoosterIsSoldInItsOwnPack() {
        var r = EconomyRules.default
        r.economy.startBoosters["undo"] = 2
        r.economy.boosterPacks["undo"] = .init(count: 5, price: 300)
        let table = r.boosterRules()
        XCTAssertEqual(table.map(\.id), [.freeze, .hint, BoosterID("undo")])
        XCTAssertEqual(table[2], BoosterRule(id: BoosterID("undo"), effect: .custom("undo"), startStock: 2, price: 300, packCount: 5))
        XCTAssertEqual(table[0].price, 900, "the reference boosters keep the shared pack")

        var s = Economy.freshState(installSeed: 1, installDate: Date(timeIntervalSince1970: 0), rules: r)
        XCTAssertEqual(Economy.stock(s, BoosterID("undo")), 2, "the module booster's start stock at install")
        s.coins = 1000
        XCTAssertTrue(Economy.buyBooster(&s, BoosterID("undo"), rules: r))
        XCTAssertEqual(Economy.stock(s, BoosterID("undo")), 7)
        XCTAssertEqual(s.coins, 700)
        XCTAssertFalse(Economy.buyBooster(&s, .hint, rules: r), "the shared pack still costs 900: short of coins")
        XCTAssertEqual(s.coins, 700)
        // decoding: a per-booster pack in the economy section is read (a game may also list it in its own rules.json)
        let json = Data(#"{"economy":{"boosterPacks":{"undo":{"count":4,"price":250}}}}"#.utf8)
        let (loaded, problems) = EconomyRules.load(rules: json)
        XCTAssertEqual(problems, [])
        XCTAssertEqual(loaded.boosterPack(for: BoosterID("undo")), .init(count: 4, price: 250))
        XCTAssertEqual(EconomyRules.unknownKeys(in: json), [], "booster ids under boosterPacks are data, not unknown keys")
    }
}
