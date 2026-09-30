import XCTest
import Foundation
import PathCore   // not @testable: public API

/// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §8b, contract v1.1): the additive change the second module needed.
/// A fail-chain step may name a module's puzzle action (`FailStep.action`): its offer then grants
/// `.puzzleAction(id:amount:)`. Steps without it decode, grant and encode exactly as before (rules.json is unchanged).
final class ContractV11Tests: XCTestCase {

    func testFailStepActionIsAPuzzleActionGrant() throws {
        let json = Data("""
        {"failChain": {"stuck": [{"price": 500, "grant": "none", "action": "extraTube", "amount": 1},
                                 {"price": 900, "grant": "none", "amount": 0, "warning": "life"}]}}
        """.utf8)
        let meta = try JSONDecoder().decode(MetaRules.self, from: json)
        let chain = meta.chain(.stuck, streakActive: false)
        XCTAssertEqual(chain.map(\.grant), [.puzzleAction(id: "extraTube", amount: 1), ContinueOffer.Grant.none])
        XCTAssertEqual(chain.map(\.price), [500, 900])
        XCTAssertEqual(chain.last?.isLast, true)
        XCTAssertEqual(meta.failChain["stuck"]?.first?.action, "extraTube")
        XCTAssertNil(meta.failChain["stuck"]?.last?.action)
        let step = MetaRules.FailStep(price: 1, grant: .none, amount: 3, action: "undo")
        XCTAssertEqual(step.offerGrant, .puzzleAction(id: "undo", amount: 3))
        XCTAssertEqual(MetaRules.FailStep(price: 1, grant: .addTime, amount: 3, action: "").offerGrant, .addTime(3),
                       "an empty action is no action")
    }

    func testStepsWithoutAnActionAreUnchanged() throws {
        let rules = MetaRules()
        XCTAssertTrue(rules.failChain.values.joined().allSatisfy { $0.action == nil })
        XCTAssertEqual(rules.chain(.outOfTime, streakActive: false).map(\.grant), [.addTime(30), .addTime(30)])
        XCTAssertEqual(rules.chain(.outOfHearts, streakActive: false).first?.grant, .refillHearts(3))
        XCTAssertTrue(rules.chain(.stuck, streakActive: true).isEmpty, "the reference game ships no stuck chain")
        // encoding: no "action" key when there is none (rules.json round-trips unchanged)
        let data = try JSONEncoder().encode(MetaRules.FailStep(price: 900, grant: .addTime, amount: 30))
        let obj = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        XCTAssertNil(obj["action"])
        XCTAssertEqual(Set(obj.keys), ["price", "grant", "amount", "warning", "onlyWithStreak"])
        let back = try JSONDecoder().decode(MetaRules.FailStep.self, from: data)
        XCTAssertEqual(back, MetaRules.FailStep(price: 900, grant: .addTime, amount: 30))
    }
}
