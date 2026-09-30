import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// B1 EVENTS-P — events.md §8.4 A6, re-stated for the v582 rules (build/p/PH0/balloon.md; SPEC.md ruling 42c): Up & Away
/// (EventID "balloonRise") replayed through the REAL C3 hooks (Events.refresh / onWin / onLoss) against the golden traces of
/// `design/publish/tools/balloon_ref.py` (fixtures/balloon_trace.json, read in place): +1 per counted win whatever the tag;
/// every failed attempt resets to 0; each platform pays once per event; a paid continue keeps the counter; the fall page from 2;
/// completion; the roll (best kept); the kill switch; save round trip + old-save decode.
final class BalloonRiseTests: XCTestCase {
    static let fixtureURL = C3.appRoot.appendingPathComponent("design/publish/tools/fixtures/balloon_trace.json")
    let me = PlayerStanding(name: "Hsheh", avatar: 0, country: "TR", level: 62, ledger: [])

    static func rules(enabled: Bool = true) throws -> EconomyRules {
        var r = EconomyRules.default
        let f = try EventRotationTests.loadFixture()
        r.events.rotation = f.rules.rotation
        r.events.rotation.enabled = enabled
        r.events.unlocks = f.rules.unlocks
        return r
    }

    static func balloonOutcomes(_ out: [EventOutcome]) -> [EventOutcome] {
        out.filter { o in
            switch o {
            case .balloonStreak, .balloonStep, .balloonFell: return true
            default: return false
            }
        }
    }

    func testTheFixtureIsWhatTheReferenceWritesToday() throws {
        guard let out = C3.python("design/publish/tools/balloon_ref.py", ["--check"]) else {
            throw XCTSkip("python3 / balloon_ref.py not runnable here")
        }
        XCTAssertTrue(out.hasSuffix(": OK\n"), out)
        guard let st = C3.python("design/publish/tools/balloon_ref.py", ["--selftest"]) else { return XCTFail("selftest failed") }
        XCTAssertTrue(st.contains("negative controls 6/6 CAUGHT") && st.contains("selftest: PASS"), st)
    }

    func testTheRulesEqualTheReferenceAndThePhone() throws {
        let doc = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: Self.fixtureURL)) as? [String: Any])
        let fixtureRules = try JSONDecoder().decode(EventRules.BalloonRise.self,
                                                    from: JSONSerialization.data(withJSONObject: try XCTUnwrap(doc["rules"])))
        XCTAssertEqual(fixtureRules, EventRules.BalloonRise(), "the compiled table == balloon_ref.py RULES")
        let r = EventRules.BalloonRise()
        XCTAssertEqual(r.platforms.map(\.at), [2, 5, 8, 13, 20, 28, 36, 46, 77, 120], "VERIFIED balloon.md §4")
        XCTAssertEqual(r.platforms[1].grant, Grant(unlimitedLives: 900), "platform 2: ∞ 15m")
        XCTAssertEqual(r.platforms[9].grant, Grant(coins: 1200, boosters: ["freeze": 1, "hint": 1], unlimitedLives: 3600))
        XCTAssertEqual(r.fallPageMinStreak, 2)
        XCTAssertEqual(doc["unlock"] as? Int, 33)
        XCTAssertEqual(r.goal(after: 0), 2)
        XCTAssertEqual(r.goal(after: 2), 5)
        XCTAssertEqual(r.goal(after: 119), 120)
        XCTAssertNil(r.goal(after: 120))
        // a broken table falls back to the phone's (never pays twice or never)
        let bad = try JSONDecoder().decode(EventRules.BalloonRise.self, from: Data(#"{"platforms":[{"at":5,"grant":{}},{"at":5,"grant":{}}]}"#.utf8))
        XCTAssertEqual(bad.platforms, EventRules.BalloonRise().platforms)
    }

    // MARK: A6 — the golden traces through the real hooks

    func testTheGoldenTracesReplayThroughTheRealHooks() throws {
        let doc = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: Self.fixtureURL)) as? [String: Any])
        var checked = 0
        for name in ["main", "gate", "killSwitch"] {
            let trace = try XCTUnwrap(doc[name] as? [String: Any], name)
            let rules = try Self.rules(enabled: trace["enabled"] as! Bool)
            var s = C3.fresh(rules)
            Economy.grant(&s, .unlimited(86_400 * 30), now: C3.utc("2026-09-25T00:00:00Z"))
            s.level = 1
            var claims: [EventClaim] = []
            for (i, row) in (trace["rows"] as! [[String: Any]]).enumerated() {
                let op = row["op"] as! String
                let level = row["level"] as! Int
                let now = Date(timeIntervalSince1970: (row["t"] as! NSNumber).doubleValue)
                let tag = LevelTag(label: row["tag"] as? String) ?? .normal
                var out: [EventOutcome] = []
                switch op {
                case "refresh":
                    s.level = max(s.level, level)
                    out = Events.refresh(&s, now: now, rivals: StubRivals(), me: me, rules: rules, home: true)
                case "win":
                    s.level = max(s.level, level + 1)                     // finishAttempt(.won) advances the level first
                    out = Events.onWin(&s, WinContext(levels: [level], tag: tag, firstTry: true, now: now), rivals: StubRivals(), rules: rules)
                case "loss":
                    s.level = max(s.level, level)
                    out = Events.onLoss(&s, LossContext(levels: [level], reason: .timeUp, now: now), rules: rules)
                case "continue":
                    break                                                    // a paid continue never reaches onLoss
                default:
                    XCTFail(op)
                }
                let at = "\(name) row \(i) (\(op) w\(row["w"]!) L\(level))"
                let want = try JSONDecoder().decode([EventOutcome].self, from: JSONSerialization.data(withJSONObject: row["out"]!))
                XCTAssertEqual(Self.balloonOutcomes(out), want, at)
                let st = row["state"] as! [String: Any]
                let b = s.events.balloon
                XCTAssertEqual(b.week, st["week"] as? Int, at)
                XCTAssertEqual([b.streak, b.paid, b.best], [st["streak"] as! Int, st["paid"] as! Int, st["best"] as! Int], at)
                XCTAssertEqual(s.events.claims.filter { $0.kind == .balloonStep }.count, row["claims"] as? Int, at)
                XCTAssertEqual(s.events.wins["balloonRise"] ?? 0, row["wins"] as? Int, at)
                let status = Events.status(s, now: now, rules: rules)
                XCTAssertEqual(status.live.ladder == .balloonRise, row["live"] as? Bool, at)
                if let bar = row["bar"] as? [String: Any] {
                    let sb = try XCTUnwrap(status.balloon, at)
                    XCTAssertEqual(sb.streak, bar["streak"] as? Int, at)
                    XCTAssertEqual(sb.goal, bar["goal"] as? Int, at)
                    XCTAssertEqual(sb.paid, bar["paid"] as? Int, at)
                    XCTAssertEqual(sb.complete, bar["complete"] as? Bool, at)
                    let next = try (bar["nextReward"] as? [String: Any]).map {
                        try JSONDecoder().decode(Grant.self, from: JSONSerialization.data(withJSONObject: $0))
                    }
                    XCTAssertEqual(sb.nextReward, next, at)
                    XCTAssertEqual(sb.best, b.best, at)
                    XCTAssertEqual(sb.accessibilityValue, sb.goal.map { "\(sb.streak)/\($0)" } ?? "\(sb.streak)", at)
                } else if let sb = status.balloon {
                    // live but not joined yet: the empty event
                    XCTAssertEqual([sb.streak, sb.paid], [0, 0], at)
                }
                if let fall = row["fallPage"] as? Bool {
                    XCTAssertEqual(Events.balloonFallPage(out, rules: rules) != nil, fall, at)
                }
                checked += 1
            }
            // the claims, in order, with their grants
            claims = s.events.claims.filter { $0.kind == .balloonStep }
            let wantClaims = trace["claims"] as! [[String: Any]]
            XCTAssertEqual(claims.count, wantClaims.count, name)
            for (c, w) in zip(claims, wantClaims) {
                XCTAssertEqual(c.value, w["step"] as? Int)
                XCTAssertEqual(c.index, w["week"] as? Int)
                XCTAssertEqual(c.event, .balloonRise)
                XCTAssertEqual(c.grant, try JSONDecoder().decode(Grant.self, from: JSONSerialization.data(withJSONObject: w["grant"]!)))
            }
        }
        XCTAssertGreaterThan(checked, 150, "every row replayed")
    }

    // MARK: the rules, spelled out

    func testEveryLossKindResetsAndAPaidContinueKeeps() throws {
        let rules = try Self.rules()
        let mon = Date(timeIntervalSince1970: 1_790_578_800)                    // week 22: Up & Away
        for reason in [LossReason.timeUp, .hearts, .quit, .killed] {
            var s = C3.fresh(rules)
            s.level = 40
            Economy.grant(&s, .unlimited(86_400), now: mon)
            for k in 0..<3 {
                s.level += 1
                _ = Events.onWin(&s, WinContext(levels: [40 + k], tag: .hard, firstTry: k == 0, now: mon + Double(60 * k)), rivals: StubRivals(), rules: rules)
            }
            XCTAssertEqual(s.events.balloon.streak, 3, "any tag +1, first try or not")
            // a paid continue never reaches onLoss: nothing to call, the counter stays
            let out = Events.onLoss(&s, LossContext(levels: [43], reason: reason, now: mon + 600), rules: rules)
            XCTAssertTrue(out.contains(.balloonFell(from: 3)), "\(reason)")
            XCTAssertEqual(Events.balloonFallPage(out, rules: rules), 3, "the fall page from 3 (VERIFIED)")
            XCTAssertEqual(s.events.balloon.streak, 0)
            XCTAssertEqual(s.events.balloon.best, 3)
            XCTAssertEqual(Self.balloonOutcomes(Events.onLoss(&s, LossContext(levels: [43], reason: reason, now: mon + 700), rules: rules)), [],
                           "already 0: nothing")
        }
        // a kill found at launch is a loss too (lives.killIsLoss): the counter resets through reconcileOnLaunch
        var s = C3.fresh(rules)
        s.level = 40
        Economy.grant(&s, .unlimited(86_400), now: mon)
        for k in 0..<2 {
            guard case .success = Economy.startAttempt(&s, levels: [40 + k], now: mon + Double(k * 60), rules: rules) else { return XCTFail("start") }
            Economy.finishAttempt(&s, outcome: .won(C3.win([40 + k])), now: mon + Double(k * 60), rules: rules)
            _ = Events.onWin(&s, WinContext(levels: [40 + k], tag: .normal, firstTry: true, now: mon + Double(k * 60)), rivals: StubRivals(), rules: rules)
        }
        XCTAssertEqual(s.events.balloon.streak, 2)
        guard case .success = Economy.startAttempt(&s, levels: [42], now: mon + 300, rules: rules) else { return XCTFail("start") }
        let notices = Economy.reconcileOnLaunch(&s, now: mon + 900, rules: rules)
        XCTAssertEqual(s.events.balloon.streak, 0, "\(notices)")
    }

    func testTheLadderSlotIsExclusiveAndTheClawKeepsItsWeeks() throws {
        let rules = try Self.rules()
        let w22 = Date(timeIntervalSince1970: 1_790_578_800 + 3600)             // Up & Away
        let w23 = w22 + 7 * 86_400                                              // Treasure Climb
        var s = C3.fresh(rules)
        s.level = 40
        s.events.streakStep = 3                                                 // x25
        let a = Events.onWin(&s, WinContext(levels: [40], tag: .normal, firstTry: true, now: w22), rivals: StubRivals(), rules: rules)
        XCTAssertFalse(a.contains { if case .clawPoints = $0 { return true }; return false }, "no Claw points in an Up & Away week")
        XCTAssertTrue(a.contains(.balloonStreak(added: 1, total: 1, goal: 2)))
        XCTAssertNil(s.events.claw.week, "the Claw is not joined in an Up & Away week")
        XCTAssertNil(Events.status(s, now: w22, rules: rules).claw)
        XCTAssertNil(Events.continueWarning(s, now: w22, rules: rules).tokens, "no token line in an Up & Away week")
        s.level = 41
        let b = Events.onWin(&s, WinContext(levels: [41], tag: .normal, firstTry: true, now: w23), rivals: StubRivals(), rules: rules)
        XCTAssertTrue(b.contains { if case .clawPoints(let p, _, _) = $0 { return p == 100 }; return false }, "x100 Claw points: \(b)")
        XCTAssertTrue(Self.balloonOutcomes(b).isEmpty, "no Up & Away in a Treasure Climb week")
        XCTAssertNil(Events.status(s, now: w23, rules: rules).balloon)
        XCTAssertEqual(s.events.balloon, BalloonState(best: 1), "the roll kept only the best streak")
        XCTAssertEqual(Events.continueWarning(s, now: w23, rules: rules).tokens, 100, "the token line is back with the Claw")
    }

    // MARK: A5 — claims survive the roll

    func testPlatformClaimsSurviveTheRollAndPayOnce() throws {
        let rules = try Self.rules()
        let w22 = Date(timeIntervalSince1970: 1_790_578_800 + 3600)
        var s = C3.fresh(rules)
        s.level = 40
        for k in 0..<5 {
            s.level += 1
            _ = Events.onWin(&s, WinContext(levels: [40 + k], tag: .normal, firstTry: true, now: w22 + Double(60 * k)), rivals: StubRivals(), rules: rules)
        }
        let claims = s.events.claims.filter { $0.kind == .balloonStep }
        XCTAssertEqual(claims.map(\.value), [1, 2])
        XCTAssertEqual(claims.map(\.grant), [.coins(50), Grant(unlimitedLives: 900)])
        // the next Monday (Treasure Climb): the event state resets, the earned chests wait on home
        let w23 = w22 + 7 * 86_400
        _ = Events.refresh(&s, now: w23, rivals: StubRivals(), me: me, rules: rules)
        XCTAssertEqual(s.events.claims.filter { $0.kind == .balloonStep }.count, 2, "claims survive the roll")
        let coins = s.coins
        XCTAssertEqual(Events.claim(&s, id: claims[0].id, now: w23), .coins(50))
        XCTAssertEqual(s.coins, coins + 50)
        XCTAssertNil(Events.claim(&s, id: claims[0].id, now: w23), "a claim pays once")
    }

    // MARK: save

    func testTheSaveRoundTripsAndOldSavesDecode() throws {
        let rules = try Self.rules()
        var s = C3.fresh(rules)
        s.level = 40
        let t = Date(timeIntervalSince1970: 1_790_578_800 + 3600)
        for k in 0..<6 {
            s.level += 1
            _ = Events.onWin(&s, WinContext(levels: [40 + k], tag: .normal, firstTry: true, now: t + Double(60 * k)), rivals: StubRivals(), rules: rules)
        }
        XCTAssertEqual(s.events.balloon, BalloonState(week: 22, streak: 6, paid: 2, best: 6))
        let data = try StateStore.encode(s)
        XCTAssertEqual(try StateStore.decode(data), s, "round trip")
        // a save from before B1 (no "balloon" key) decodes to the empty event
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        var events = try XCTUnwrap(json["events"] as? [String: Any])
        XCTAssertNotNil(events.removeValue(forKey: "balloon"))
        json["events"] = events
        let old = try StateStore.decode(JSONSerialization.data(withJSONObject: json))
        XCTAssertEqual(old.events.balloon, BalloonState())
        var expected = s
        expected.events.balloon = BalloonState()
        XCTAssertEqual(old, expected, "every other field decodes as saved")
        // partial keys, and the frozen v1 fixture
        let partial = try StateStore.decoder().decode(BalloonState.self, from: Data(#"{"streak":4}"#.utf8))
        XCTAssertEqual(partial, BalloonState(week: nil, streak: 4, paid: 0, best: 0))
        let v1 = try StateStore.decode(Data(contentsOf: C3.fixture("wp0_player_v1.json")))
        XCTAssertEqual(v1.events.balloon, BalloonState())
        XCTAssertEqual(v1.events.notify, EventNotifyState())
        // a state that never met B1's blocks re-encodes without them (existing saves stay byte-identical)
        let fresh = String(decoding: try StateStore.encode(C3.fresh()), as: UTF8.self)
        XCTAssertFalse(fresh.contains("\"balloon\""), fresh)
        XCTAssertFalse(fresh.contains("\"notify\""), fresh)
        // the new claim kind decodes (and an old build's kinds still do)
        let kinds = try JSONDecoder().decode([EventClaim.Kind].self, from: Data(#"["balloonStep","clawStep","rocketJoin"]"#.utf8))
        XCTAssertEqual(kinds, [.balloonStep, .clawStep, .rocketJoin])
    }
}
