import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// C3's shared test helpers (fixtures, phone times, a stub world).
enum C3 {
    /// Packages/PathCore/Tests.
    static var testsDir: URL { URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent() }
    /// apps/mazeout.
    static var appRoot: URL { testsDir.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent() }
    static func fixture(_ name: String) -> URL { testsDir.appendingPathComponent("Fixtures/\(name)") }

    static let rules = EconomyRules.default

    /// 2026-09-<day> hh:mm:ss on the owner's phone (Turkey, UTC+3) — the research ledgers' clock.
    static func trt(_ hms: String, day: Int = 25) -> Date {
        let p = hms.split(separator: ":").map { Int($0)! }
        var c = DateComponents()
        c.year = 2026; c.month = 9; c.day = day; c.hour = p[0]; c.minute = p[1]; c.second = p.count > 2 ? p[2] : 0
        c.timeZone = TimeZone(secondsFromGMT: 3 * 3600)
        return Calendar(identifier: .gregorian).date(from: c)!
    }

    static func utc(_ iso: String) -> Date { ISODate.date(iso)! }

    static func win(_ levels: [Int], tag: LevelTag = .normal, firstTry: Bool = true, reward: Int? = nil) -> WinResult {
        WinResult(levels: levels, tag: tag, timeLeft: 60, heartsLeft: 3, firstTry: firstTry,
                  reward: reward ?? RulesTuning.default.rewards.reward(for: tag), bumps: 0)
    }

    /// A fresh install from the rules (1000 coins, 3 + 3 boosters, 5 lives).
    static func fresh(_ r: EconomyRules = rules) -> PlayerState {
        Economy.freshState(installSeed: 42, installDate: utc("2026-09-25T00:00:00Z"), rules: r)
    }

    /// Runs `python3 <apps/mazeout/relative> args…`; nil when python3 is missing or the run fails.
    static func python(_ relative: String, _ args: [String]) -> String? {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        p.arguments = ["python3", appRoot.appendingPathComponent(relative).path] + args
        let out = Pipe()
        p.standardOutput = out
        p.standardError = Pipe()
        do { try p.run() } catch { return nil }
        let d = out.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        return p.terminationStatus == 0 ? String(decoding: d, as: UTF8.self) : nil
    }

    /// Writes a text report into $PC_EVIDENCE_DIR (build/c3/ in the C3 runs); a no-op otherwise.
    static func evidence(_ name: String, _ text: String) {
        guard let dir = ProcessInfo.processInfo.environment["PC_EVIDENCE_DIR"], !dir.isEmpty else { return }
        let url = URL(fileURLWithPath: dir).appendingPathComponent(name)
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? Data(text.utf8).write(to: url)
    }
}

/// A scripted world for the events (SOC1's `SocialWorld` in the app).
struct StubRivals: RivalProvider {
    var streak: @Sendable (EventInstance, PlayerStanding, SocialTime) -> [RaceStanding] = { _, _, _ in [] }
    var rocket: @Sendable (EventInstance, SocialTime, SocialTime) -> [RaceStanding] = { _, _, _ in [] }
    var sky: @Sendable (SkyJumpRun, SocialTime) -> SkyJumpField = { _, _ in SkyJumpField(total: 100, left: 100, winners: 7) }

    func streakRace(_ instance: EventInstance, player: PlayerStanding, at: SocialTime) -> [RaceStanding] { streak(instance, player, at) }
    func rocketRace(_ instance: EventInstance, joinedAt: SocialTime, at: SocialTime) -> [RaceStanding] { rocket(instance, joinedAt, at) }
    func skyJump(_ run: SkyJumpRun, at: SocialTime) -> SkyJumpField { sky(run, at) }

    static func lane(_ id: UInt64, _ score: Int, me: Bool = false, rank: Int = 0) -> RaceStanding {
        RaceStanding(rank: rank, player: SimPlayer(id: id, name: "p\(id)", country: "TR", avatar: 0), score: score, isMe: me)
    }
}

/// SPEC-architecture §4.17 "LivesTests" (C3): the lives chain against the independent Python reference, the phone's
/// ledgers, a clock set back never granting or punishing, unlimited stacking, the start/refund rule, the kill rule.
final class LivesTests: XCTestCase {
    let r = C3.rules

    // MARK: the chain equals lives_ref.py on 200 random scripts

    func testChainEqualsThePythonReferenceOn200RandomScripts() throws {
        let fixture = C3.fixture("c3_lives_scripts.json")
        // The committed fixture is what the reference emits today (python3 present on the build Macs).
        let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("c3_lives_\(UUID().uuidString).json")
        if C3.python("Packages/PathCore/Tests/tools/lives_ref.py", ["--emit", tmp.path]) != nil {
            XCTAssertEqual(try Data(contentsOf: tmp), try Data(contentsOf: fixture),
                           "Tests/Fixtures/c3_lives_scripts.json is stale: re-run lives_ref.py --emit")
            try? FileManager.default.removeItem(at: tmp)
        }
        let doc = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: fixture)) as? [String: Any])
        XCTAssertEqual(doc["refillSeconds"] as? Double, r.lives.refillSeconds)
        XCTAssertEqual(doc["max"] as? Int, r.lives.max)
        XCTAssertEqual(doc["refillPrice"] as? Int, r.lives.refillPrice)
        let scripts = try XCTUnwrap(doc["scripts"] as? [[String: Any]])
        XCTAssertEqual(scripts.count, 200)

        func num(_ v: Any?) -> Double? { (v as? NSNumber)?.doubleValue }
        func secs(_ d: Date?) -> Double? { d?.timeIntervalSince1970 }
        var mismatches: [String] = []
        var ops = 0
        var kinds: [String: Int] = [:]
        for sc in scripts {
            let seed = sc["seed"] as? Int ?? -1
            let ini = try XCTUnwrap(sc["init"] as? [String: Any])
            var s = C3.fresh()
            s.lives = LivesState(count: ini["count"] as! Int, anchor: num(ini["anchor"]).map { Date(timeIntervalSince1970: $0) })
            s.unlimitedLivesUntil = num(ini["until"]).map { Date(timeIntervalSince1970: $0) }
            s.social.highWater = Int64(ini["hw"] as! Int)
            s.coins = ini["coins"] as! Int
            for (i, rowAny) in (sc["ops"] as! [[Any]]).enumerated() {
                let row = rowAny
                let op = row[0] as! String
                let wall = Date(timeIntervalSince1970: Double((row[1] as! NSNumber).int64Value) / 1000)
                let arg = (row[2] as! NSNumber).doubleValue
                ops += 1
                kinds[op, default: 0] += 1
                var result = "ok"
                switch op {
                case "start":
                    switch Economy.startAttempt(&s, levels: [100], now: wall, rules: r) {
                    case .success: result = "ok"
                    case .failure(let e): result = "\(e)"
                    }
                case "win", "loss":
                    let had = s.activeAttempt != nil
                    let outcome: AttemptOutcome = op == "win" ? .won(C3.win([100], reward: 0)) : .lost(.timeUp)
                    Economy.finishAttempt(&s, outcome: outcome, now: wall, rules: r)
                    result = had ? "ok" : "none"
                case "launch":
                    let n = Economy.reconcileOnLaunch(&s, now: wall, rules: r)
                    result = n.contains { if case .killedAttempt = $0 { return true }; return false } ? "killed" : "ok"
                case "grant":
                    Economy.grant(&s, Grant(unlimitedLives: arg), now: wall)
                case "refill":
                    result = Economy.refillLives(&s, now: wall, rules: r) ? "ok" : "no"
                default:
                    break
                }
                var status: [Any?] = []
                switch Economy.lives(s, now: wall, rules: r) {
                case .full: status = ["full", nil, nil]
                case .counting(let n, let next): status = ["counting", Double(n), next.timeIntervalSince1970]
                case .unlimited(let u): status = ["unlimited", u.timeIntervalSince1970, nil]
                }
                let want: [Any?] = [row[3], num(row[4]), num(row[5]), num(row[6]), num(row[7]), num(row[8]), num(row[9]),
                                    num(row[10]), row[11], num(row[12]), num(row[13])]
                let got: [Any?] = [result, Double(s.lives.count), secs(s.lives.anchor), secs(s.unlimitedLivesUntil),
                                   Double(s.social.highWater), Double(s.coins), s.activeAttempt != nil ? 1.0 : 0.0,
                                   s.events.attemptFree ? 1.0 : 0.0, status[0], status[1] as? Double, status[2] as? Double]
                let names = ["result", "count", "anchor", "until", "hw", "coins", "active", "free", "status", "statusA", "statusB"]
                for k in 0..<names.count {
                    let a = want[k].map { "\($0)" } ?? "nil", b = got[k].map { "\($0)" } ?? "nil"
                    let same: Bool
                    if let x = want[k] as? Double, let y = got[k] as? Double { same = x == y } else { same = a == b }
                    if !same && !(want[k] == nil && got[k] == nil) {
                        mismatches.append("seed \(seed) op \(i) \(op) @\(wall.timeIntervalSince1970): \(names[k]) want \(a) got \(b)")
                    }
                }
            }
        }
        C3.evidence("lives-ref-replay.txt", "200 scripts, \(ops) operations \(kinds.sorted { $0.key < $1.key }), "
                    + "\(mismatches.count) mismatches\n" + mismatches.prefix(50).joined(separator: "\n") + "\n")
        XCTAssertEqual(mismatches.count, 0, mismatches.prefix(10).joined(separator: "\n"))
        XCTAssertGreaterThan(ops, 8000)
    }

    // MARK: the phone's ledgers (research/fail.md §6, economy.md §2b)

    func testThePhoneLedgerOfL62() {
        var s = C3.fresh()
        // #2: started 05:18:07 from 5 Full, lost on time; at 05:28:22 the home read "4, 19:45" → next life 05:48:07
        guard case .success = Economy.startAttempt(&s, levels: [62], now: C3.trt("05:18:07"), rules: r) else { return XCTFail() }
        Economy.finishAttempt(&s, outcome: .lost(.timeUp), now: C3.trt("05:25:40"), rules: r)
        XCTAssertEqual(Economy.lives(s, now: C3.trt("05:28:22"), rules: r), .counting(count: 4, nextAt: C3.trt("05:48:07")))
        XCTAssertEqual(Economy.countdown(s, now: C3.trt("05:28:22"), rules: r), 19 * 60 + 45)
        // #3 05:30:44 (hearts), #4 Try Again 05:46:37, quit → 05:49:25 "3, 28:42" → next 06:18:07
        _ = Economy.startAttempt(&s, levels: [62], now: C3.trt("05:30:44"), rules: r)
        Economy.finishAttempt(&s, outcome: .lost(.hearts), now: C3.trt("05:46:17"), rules: r)
        _ = Economy.startAttempt(&s, levels: [62], now: C3.trt("05:46:37"), rules: r)
        Economy.finishAttempt(&s, outcome: .lost(.quit), now: C3.trt("05:49:00"), rules: r)
        XCTAssertEqual(Economy.lives(s, now: C3.trt("05:49:25"), rules: r), .counting(count: 3, nextAt: C3.trt("06:18:07")))
        XCTAssertEqual(Economy.countdown(s, now: C3.trt("05:49:25"), rules: r), 28 * 60 + 42)
        // economy.md §2b: the tick landed on 06:18:07 and the next countdown started at once (continuous clock)
        XCTAssertEqual(Economy.lives(s, now: C3.trt("06:18:06"), rules: r), .counting(count: 3, nextAt: C3.trt("06:18:07")))
        XCTAssertEqual(Economy.lives(s, now: C3.trt("06:18:07"), rules: r), .counting(count: 4, nextAt: C3.trt("06:48:07")))
        XCTAssertEqual(Economy.countdown(s, now: C3.trt("06:18:08"), rules: r), 29 * 60 + 59)
        // the "lives full" notification: 4 at 06:18:07 → 5 at 06:48:07
        XCTAssertEqual(Economy.livesFullAt(s, now: C3.trt("06:20:00"), rules: r), C3.trt("06:48:07"))
        XCTAssertEqual(Economy.livesFullAt(s, now: C3.trt("05:49:25"), rules: r), C3.trt("06:48:07"))
        XCTAssertNil(Economy.livesFullAt(s, now: C3.trt("06:48:07"), rules: r))
    }

    func testAFailedStartFromFullGivesItsLifeBackThirtyMinutesLater() {
        // fail.md §6 direct confirmation: started 06:54:20 from 5 Full, failed 07:20:35, closed 07:28:47 → "5 Full"
        var s = C3.fresh()
        _ = Economy.startAttempt(&s, levels: [62], now: C3.trt("06:54:20"), rules: r)
        XCTAssertEqual(s.lives, LivesState(count: 4, anchor: C3.trt("06:54:20")))      // taken at the START
        Economy.finishAttempt(&s, outcome: .lost(.timeUp), now: C3.trt("07:28:47"), rules: r)
        XCTAssertEqual(Economy.lives(s, now: C3.trt("07:28:47"), rules: r), .full)
        XCTAssertEqual(Economy.refreshLives(&s, now: C3.trt("07:28:47"), rules: r), 1, "it came back at 07:24:20")
        XCTAssertEqual(s.lives, LivesState(count: 5, anchor: nil))
    }

    // MARK: a life is taken at the start and refunded on a win (the net: a loss costs one, a win none)

    func testALossCostsALifeAndAWinRefundsTheStartsLife() {
        var s = C3.fresh()
        let t0 = C3.trt("10:00:00")
        _ = Economy.startAttempt(&s, levels: [40], now: t0, rules: r)
        XCTAssertEqual(s.lives.count, 4)
        Economy.finishAttempt(&s, outcome: .won(C3.win([40])), now: t0.addingTimeInterval(120), rules: r)
        XCTAssertEqual(s.lives, LivesState(count: 5, anchor: nil), "a won attempt costs no life")
        for reason in [LossReason.timeUp, .hearts, .quit] {
            let before = s.lives.count
            _ = Economy.startAttempt(&s, levels: [41], now: t0.addingTimeInterval(200), rules: r)
            Economy.finishAttempt(&s, outcome: .lost(reason), now: t0.addingTimeInterval(260), rules: r)
            XCTAssertEqual(s.lives.count, before - 1, "a \(reason) attempt costs exactly one life")
        }
        // a refund keeps the running countdown (one continuous clock): the phase is the first drop below 5
        XCTAssertEqual(s.lives.anchor, t0.addingTimeInterval(200))
        _ = Economy.startAttempt(&s, levels: [41], now: t0.addingTimeInterval(400), rules: r)
        Economy.finishAttempt(&s, outcome: .won(C3.win([41], firstTry: false)), now: t0.addingTimeInterval(500), rules: r)
        XCTAssertEqual(s.lives, LivesState(count: 2, anchor: t0.addingTimeInterval(200)))
    }

    func testTheLivesGateAndUnlimitedCheckedAtTheStartOnly() {
        var s = C3.fresh()
        let t0 = C3.trt("04:57:00")
        s.lives = LivesState(count: 0, anchor: t0.addingTimeInterval(-60))
        XCTAssertEqual(Economy.startAttempt(&s, levels: [62], now: t0, rules: r).failure, .noLives)
        XCTAssertNil(s.activeAttempt)
        // ∞ running at the start: the level takes nothing, even with 0 lives, and a fail after ∞ ended costs nothing
        Economy.grant(&s, .unlimited(900), now: t0)
        guard case .success = Economy.startAttempt(&s, levels: [62], now: t0, rules: r) else { return XCTFail() }
        XCTAssertEqual(s.lives.count, 0)
        XCTAssertTrue(s.events.attemptFree)
        Economy.finishAttempt(&s, outcome: .lost(.timeUp), now: t0.addingTimeInterval(1500), rules: r)   // ∞ ended at +900
        XCTAssertEqual(s.lives.count, 0, "a level started under ∞ costs nothing")
        // … and a win refunds nothing either
        s.lives = LivesState(count: 3, anchor: t0.addingTimeInterval(1600))
        Economy.grant(&s, .unlimited(600), now: t0.addingTimeInterval(1600))
        _ = Economy.startAttempt(&s, levels: [63], now: t0.addingTimeInterval(1601), rules: r)
        Economy.finishAttempt(&s, outcome: .won(C3.win([63])), now: t0.addingTimeInterval(1700), rules: r)
        XCTAssertEqual(s.lives.count, 3)
        // just after ∞ ended, a start takes a life again
        _ = Economy.startAttempt(&s, levels: [64], now: t0.addingTimeInterval(1600 + 600), rules: r)
        XCTAssertEqual(s.lives.count, 2)
    }

    // MARK: unlimited lives stack (VERIFIED L55: ∞ 30m + 1h = "1h 20m")

    func testUnlimitedGrantsStack() {
        var s = C3.fresh()
        Economy.grant(&s, .unlimited(1800), now: C3.trt("03:47:00"))            // Rocket Race join
        Economy.grant(&s, .unlimited(3600), now: C3.trt("03:52:00"))            // Claw step 5 (∞ 1h)
        XCTAssertEqual(Economy.countdown(s, now: C3.trt("03:57:00"), rules: r), 80 * 60)
        XCTAssertEqual(Economy.lives(s, now: C3.trt("03:57:00"), rules: r), .unlimited(until: C3.trt("05:17:00")))
        // an expired ∞ does not carry: max(until, now) + d
        Economy.grant(&s, .unlimited(600), now: C3.trt("06:00:00"))
        XCTAssertEqual(s.unlimitedLivesUntil, C3.trt("06:10:00"))
        XCTAssertTrue(Economy.hasUnlimitedLives(s, now: C3.trt("06:09:59")))
        XCTAssertFalse(Economy.hasUnlimitedLives(s, now: C3.trt("06:10:00")))
    }

    // MARK: the device clock set back never grants, never rewinds, never punishes

    func testAClockSetBackNeverGrantsALife() {
        var s = C3.fresh()
        let t0 = C3.trt("12:00:00")
        _ = Economy.startAttempt(&s, levels: [40], now: t0, rules: r)
        Economy.finishAttempt(&s, outcome: .lost(.quit), now: t0.addingTimeInterval(60), rules: r)
        XCTAssertEqual(s.lives, LivesState(count: 4, anchor: t0))
        _ = Economy.reconcileOnLaunch(&s, now: t0.addingTimeInterval(1000), rules: r)
        // set back two hours, then relaunch: frozen at the latest time ever seen (t0 + 1000), no life, no shorter wait
        let back = t0.addingTimeInterval(-7200)
        XCTAssertEqual(Economy.reconcileOnLaunch(&s, now: back, rules: r), [.clockBehind(seconds: 8200)])
        XCTAssertEqual(Economy.lives(s, now: back, rules: r), .counting(count: 4, nextAt: t0.addingTimeInterval(1800)))
        XCTAssertEqual(Economy.countdown(s, now: back, rules: r), 800)
        XCTAssertTrue(EconomyClock.isBehind(s, wall: back))
        // the classic exploit: set back, open the app, set the clock right again → still exactly one life at t0 + 1800
        _ = Economy.startAttempt(&s, levels: [40], now: back, rules: r)
        Economy.finishAttempt(&s, outcome: .won(C3.win([40])), now: back.addingTimeInterval(30), rules: r)
        XCTAssertEqual(Economy.livesCount(s, now: t0.addingTimeInterval(1799), rules: r), 4)
        XCTAssertEqual(Economy.livesCount(s, now: t0.addingTimeInterval(1800), rules: r), 5)
        XCTAssertEqual(s.lives.anchor, t0, "the refill phase never moved")
    }

    func testAClockSetBackNeverTakesALifeOrExtendsUnlimited() {
        var s = C3.fresh()
        let t0 = C3.trt("12:00:00")
        s.lives = LivesState(count: 2, anchor: t0)
        Economy.grant(&s, .unlimited(3600), now: t0.addingTimeInterval(100))
        XCTAssertEqual(Economy.countdown(s, now: t0.addingTimeInterval(100), rules: r), 3600)
        for back in [60.0, 3600, 86_400 * 3] as [Double] {
            let w = t0.addingTimeInterval(100 - back)
            XCTAssertEqual(Economy.livesCount(s, now: w, rules: r), 2, "never punished (set back \(back) s)")
            XCTAssertEqual(Economy.countdown(s, now: w, rules: r), 3600, "∞ neither extended nor shortened")
        }
        // the world keeps its latest time: a start while the clock is behind happens at the high-water mark
        _ = Economy.startAttempt(&s, levels: [60], now: t0.addingTimeInterval(-500), rules: r)
        XCTAssertEqual(s.activeAttempt?.startedAt, t0.addingTimeInterval(100))
    }

    func testAMonthLongRepairedClockRebasesAndKeepsRemainingDurations() {
        // SPEC-social §5 (SOC1's clock): > 30 days behind the mark rebases; the stored economy times move with it
        var s = C3.fresh()
        let future = C3.trt("12:00:00").addingTimeInterval(45 * 86_400)
        s.lives = LivesState(count: 3, anchor: future.addingTimeInterval(-600))
        Economy.grant(&s, .unlimited(3600), now: future)
        XCTAssertEqual(Economy.countdown(s, now: future, rules: r), 3600)
        let repaired = C3.trt("12:00:00")
        _ = Economy.reconcileOnLaunch(&s, now: repaired, rules: r)
        XCTAssertEqual(s.social.highWater, Int64(repaired.timeIntervalSince1970))
        XCTAssertEqual(s.unlimitedLivesUntil, repaired.addingTimeInterval(3600), "∞ keeps its remaining hour")
        XCTAssertEqual(s.lives, LivesState(count: 3, anchor: repaired.addingTimeInterval(-600)), "no life granted by the step")
        XCTAssertEqual(Economy.livesCount(s, now: repaired.addingTimeInterval(1199), rules: r), 3)
        XCTAssertEqual(Economy.livesCount(s, now: repaired.addingTimeInterval(1200), rules: r), 4)
    }

    // MARK: the kill rule, Refill, the interval is data

    func testAKilledAttemptIsALossAtTheNextLaunch() {
        var s = C3.fresh()
        let t0 = C3.trt("12:00:00")
        s.level = 40
        s.events.streakStep = 3
        _ = Economy.startAttempt(&s, levels: [40], now: t0, rules: r)
        let n = Economy.reconcileOnLaunch(&s, now: t0.addingTimeInterval(300), rules: r)
        XCTAssertEqual(n, [.killedAttempt(levels: [40], countedAsLoss: true, outcomes: [.multiplier(from: 25, to: 1)])])
        XCTAssertNil(s.activeAttempt)
        XCTAssertEqual(s.lives.count, 4, "the life stays spent")
        XCTAssertEqual(s.stats.losses, 1)
        XCTAssertEqual(s.events.streakStep, 0)
        // lives.killIsLoss = false: the attempt is forgotten and its life given back
        var soft = r
        soft.lives.killIsLoss = false
        _ = Economy.startAttempt(&s, levels: [40], now: t0.addingTimeInterval(400), rules: soft)
        XCTAssertEqual(s.attempts[40], 2)
        let m = Economy.reconcileOnLaunch(&s, now: t0.addingTimeInterval(500), rules: soft)
        XCTAssertEqual(m, [.killedAttempt(levels: [40], countedAsLoss: false, outcomes: [])])
        XCTAssertEqual(s.lives.count, 4)
        XCTAssertEqual(s.attempts[40], 1)
        XCTAssertEqual(s.stats.losses, 1)
    }

    func testRefillCostsNineHundredAndFillsToMax() {
        var s = C3.fresh()
        let t0 = C3.trt("12:00:00")
        XCTAssertFalse(Economy.refillLives(&s, now: t0, rules: r), "not when full")
        s.lives = LivesState(count: 1, anchor: t0)
        s.coins = 899
        XCTAssertFalse(Economy.refillLives(&s, now: t0, rules: r), "not when short")
        XCTAssertEqual(s.coins, 899)
        s.coins = 1000
        XCTAssertTrue(Economy.refillLives(&s, now: t0, rules: r))
        XCTAssertEqual(s.coins, 100)
        XCTAssertEqual(s.lives, LivesState(count: 5, anchor: nil))
    }

    func testTheRefillIntervalIsData() {
        var fast = r
        fast.lives.refillSeconds = 60
        fast.lives.max = 3
        var s = Economy.freshState(installSeed: 1, installDate: C3.trt("12:00:00"), rules: fast)
        XCTAssertEqual(s.lives.count, 3)
        let t0 = C3.trt("12:00:00")
        _ = Economy.startAttempt(&s, levels: [9], now: t0, rules: fast)
        Economy.finishAttempt(&s, outcome: .lost(.quit), now: t0, rules: fast)
        XCTAssertEqual(Economy.lives(s, now: t0.addingTimeInterval(59), rules: fast), .counting(count: 2, nextAt: t0.addingTimeInterval(60)))
        XCTAssertEqual(Economy.lives(s, now: t0.addingTimeInterval(60), rules: fast), .full)
        // lives.cost = atLoss (the architecture's first placeholder): nothing at the start, one at the loss, none on a win
        var late = r
        late.lives.cost = .atLoss
        var u = C3.fresh()
        _ = Economy.startAttempt(&u, levels: [9], now: t0, rules: late)
        XCTAssertEqual(u.lives.count, 5)
        Economy.finishAttempt(&u, outcome: .lost(.timeUp), now: t0.addingTimeInterval(10), rules: late)
        XCTAssertEqual(u.lives, LivesState(count: 4, anchor: t0.addingTimeInterval(10)))
        _ = Economy.startAttempt(&u, levels: [9], now: t0.addingTimeInterval(20), rules: late)
        Economy.finishAttempt(&u, outcome: .won(C3.win([9], firstTry: false)), now: t0.addingTimeInterval(30), rules: late)
        XCTAssertEqual(u.lives.count, 4)
    }

    func testSetLivesForLaunchArguments() {
        var s = C3.fresh()
        let t0 = C3.trt("12:00:00")
        Economy.setLives(&s, count: 2, nextIn: 90, now: t0, rules: r)
        XCTAssertEqual(Economy.lives(s, now: t0, rules: r), .counting(count: 2, nextAt: t0.addingTimeInterval(90)))
        Economy.setLives(&s, count: 5, now: t0, rules: r)
        XCTAssertEqual(Economy.lives(s, now: t0, rules: r), .full)
    }
}

extension Result {
    var failure: Failure? { if case .failure(let e) = self { return e }; return nil }
}
