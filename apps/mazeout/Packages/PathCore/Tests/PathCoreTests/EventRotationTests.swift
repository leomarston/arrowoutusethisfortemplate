import XCTest
import Foundation
@testable import PathCore

/// B1 EVENTS-P — events.md §8.4 A1-A4 (+ the rotation half of A5): the weekly rotation of the featured events
/// (`EventRotation`) against T7's reference `design/publish/tools/rotation_ref.py` and its 1,044-week fixture, read in place.
///   A1  the calendar == the fixture, bit for bit (every week's picks and start second; the hash KATs; the clock KATs; the
///       clamp of weeks before the anchor; the kill switch's v552 plan)
///   A2  its properties over 1,043 and 1,044 weeks (max run ≤ 2, Double gap ≥ 3, each ladder event 40-60 %, each race event
///       absent ≤ 2 weeks, ≤ 8 % unchanged weeks) — measured on OUR plan, with the SPEC's thresholds (never the config's)
///   A3  constant inside a week; the roll at Monday 07:00:00 UTC exactly; a clock set back across a Monday never shows last
///       week's events (SocialTime); the one-time 30-day rebase follows the repaired clock
///   A4  segmentation (the fixture's 84 rows + the four named cases)
final class EventRotationTests: XCTestCase {
    static let fixtureURL = C3.appRoot.appendingPathComponent("design/publish/tools/fixtures/rotation_1044.json")

    struct Fixture {
        let doc: [String: Any]
        let rules: EventRules                // rotation = the fixture's config (enabled), unlocks = the fixture's
        var weeks: [[String: Any]] { doc["weeks"] as! [[String: Any]] }
    }

    static func loadFixture() throws -> Fixture {
        let data = try Data(contentsOf: fixtureURL)
        let doc = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        var rules = EventRules()
        rules.rotation = try JSONDecoder().decode(EventRules.Rotation.self,
                                                  from: JSONSerialization.data(withJSONObject: try XCTUnwrap(doc["config"])))
        rules.unlocks = try XCTUnwrap(doc["unlocks"] as? [String: Int])
        return Fixture(doc: doc, rules: rules)
    }

    static func ids(_ a: Any?) -> [String] { (a as? [String]) ?? [] }
    static func names(_ e: [EventID]) -> [String] { e.map(\.rawValue) }

    // MARK: A1

    func testTheFixtureIsWhatTheReferenceWritesToday() throws {
        // the committed fixture == a fresh regeneration (skipped where python3 is missing; the fixture itself stays pinned)
        guard let out = C3.python("design/publish/tools/rotation_ref.py", ["--check"]) else {
            throw XCTSkip("python3 / rotation_ref.py not runnable here")
        }
        XCTAssertTrue(out.contains("fixture sha256 f48c5f4f28f12b70f3325d8bab90f718535f9ea31678ba8a93d209ee13c89e14: OK"), out)
        XCTAssertTrue(out.contains("A2 over 1043 weeks: PASS"), out)
    }

    func testTheCalendarEqualsTheReferenceBitForBit() throws {
        let f = try Self.loadFixture()
        XCTAssertTrue(f.rules.rotation.enabled)
        XCTAssertEqual(f.doc["weekCount"] as? Int, 1044)
        XCTAssertEqual(f.doc["weekSeconds"] as? Int, 604_800)
        let plans = EventRotation.plans(count: 1044, rules: f.rules)
        XCTAssertEqual(plans.count, 1044)
        var diffs: [String] = []
        for (i, row) in f.weeks.enumerated() {
            let p = plans[i]
            XCTAssertEqual(row["w"] as? Int, i)
            let want = (row["ladder"] as! String, Self.ids(row["race"]), (row["start"] as! NSNumber).int64Value)
            if p.ladder.rawValue != want.0 || Self.names(p.race) != want.1 || p.start.seconds != want.2 || p.week != i {
                diffs.append("w\(i): \(p.ladder.rawValue) \(Self.names(p.race)) \(p.start.seconds) != \(want)")
            }
            // the one-week path (what the hooks use) equals the one-pass path
            if i % 97 == 0 || i < 40 || i > 1030 { XCTAssertEqual(EventRotation.plan(week: i, rules: f.rules), p, "w\(i)") }
        }
        XCTAssertEqual(diffs, [], "the calendar differs from rotation_ref.py")
        // the published table (events.md §4.3, weeks 22-35)
        let table: [(String, [String])] = [("balloonRise", ["rocketRace", "skyJump"]), ("clawChallenge", ["skyJump"]),
            ("balloonRise", ["skyJump"]), ("balloonRise", ["rocketRace", "skyJump"]), ("clawChallenge", ["rocketRace"]),
            ("balloonRise", ["skyJump"]), ("clawChallenge", ["rocketRace", "skyJump"]), ("balloonRise", ["rocketRace"]),
            ("clawChallenge", ["skyJump"]), ("balloonRise", ["rocketRace", "skyJump"]), ("clawChallenge", ["skyJump"]),
            ("balloonRise", ["rocketRace"]), ("clawChallenge", ["rocketRace"]), ("balloonRise", ["skyJump"])]
        for (k, row) in table.enumerated() {
            XCTAssertEqual(plans[22 + k].ladder.rawValue, row.0, "w\(22 + k)")
            XCTAssertEqual(Self.names(plans[22 + k].race), row.1, "w\(22 + k)")
        }
        XCTAssertEqual(plans[22].start.seconds, 1_790_578_800, "week 22 starts Mon 2026-09-28 07:00 UTC")
    }

    func testHashAndClockKATs() throws {
        let f = try Self.loadFixture()
        let seed = f.rules.rotation.seedValue
        XCTAssertEqual(seed, 0x524F_5441_5449_4F4E)
        for k in f.doc["hashKAT"] as! [[String: Any]] {
            let label = k["label"] as! String, w = k["w"] as! Int
            let h = SocialHash.h64(seed, Label(label), w)
            XCTAssertEqual(String(h), k["h64"] as? String, "\(label) \(w)")
            XCTAssertEqual(SocialHash.unit(h), Double(k["unit"] as! String)!, "\(label) \(w)")
        }
        for k in f.doc["clockKAT"] as! [[String: Any]] {
            let t = (k["t"] as! NSNumber).int64Value
            XCTAssertEqual(EventRotation.week(SocialTime(seconds: t), f.rules), k["week"] as? Int, "t \(t)")
        }
        // weeks before the anchor take week 0's picks (a clock set before 2026-04-27)
        let clamp = f.doc["clamp"] as! [String: Any]
        let plan0 = clamp["plan"] as! [String: Any]
        for w in clamp["weeks"] as! [Int] {
            let p = EventRotation.plan(week: w, rules: f.rules)
            XCTAssertEqual(p.ladder.rawValue, plan0["ladder"] as? String)
            XCTAssertEqual(Self.names(p.race), Self.ids(plan0["race"]))
            XCTAssertEqual(p.week, w)
            XCTAssertEqual(p.start, EventRotation.weekStart(w, f.rules))
        }
        // T7's B1 rule: the rotation's anchor is the event calendar's (same instant mod a week), so its w = the Claw's week
        let r = EventRules()
        XCTAssertEqual((r.rotation.epoch - r.calendar.epoch) % r.calendar.week, 0)
        XCTAssertEqual(f.rules.rotation.epoch, r.calendar.epoch)
    }

    func testTheKillSwitchIsTheV552Plan() throws {
        var f = try Self.loadFixture().rules
        f.rotation.enabled = false
        let fx = try Self.loadFixture()
        for row in fx.doc["allOn"] as! [[String: Any]] {
            let level = row["level"] as! Int
            let want = row["live"] as! [String: Any]
            for w in [0, 22, 23, 500] {
                let live = EventRotation.live(week: w, level: level, rules: f)
                XCTAssertEqual(Self.names(live.always), Self.ids(want["always"]), "L\(level) w\(w)")
                XCTAssertEqual(live.ladder?.rawValue, want["ladder"] as? String, "L\(level) w\(w)")
                XCTAssertEqual(Self.names(live.race), Self.ids(want["race"]), "L\(level) w\(w)")
                XCTAssertFalse(live.contains(.balloonRise), "Up & Away never runs in the v552 plan")
            }
        }
        // and the COMPILED default is that plan (every existing C3 rule keeps its v552 meaning)
        XCTAssertFalse(EventRules.default.rotation.enabled)
        XCTAssertEqual(EventRotation.live(week: 22, level: 60, rules: .default),
                       LiveEvents(always: [.streakRace, .weeklyContest], ladder: .clawChallenge, race: [.rocketRace, .skyJump]))
    }

    // MARK: A2

    func testThePropertiesOverTwentyYears() throws {
        let f = try Self.loadFixture()
        for n in [1043, 1044] {
            let plans = EventRotation.plans(count: n, rules: f.rules)
            let L = plans.map(\.ladder.rawValue)
            let R = plans.map { $0.isDouble ? "double" : $0.race[0].rawValue }
            func maxRun<T: Equatable>(_ a: [T]) -> Int {
                var m = 0, c = 0; var prev: T?
                for x in a { c = x == prev ? c + 1 : 1; prev = x; m = max(m, c) }
                return m
            }
            func maxAbsence(_ a: [String], _ pred: (String) -> Bool) -> Int {
                var m = 0, c = 0
                for x in a { c = pred(x) ? c + 1 : 0; m = max(m, c) }
                return m
            }
            XCTAssertLessThanOrEqual(maxRun(L), 2, "ladder max run (n \(n))")
            XCTAssertLessThanOrEqual(maxRun(R), 2, "race pick max run")
            XCTAssertLessThanOrEqual(maxRun(R.filter { $0 != "double" }), 2, "race single run, Double weeks skipped")
            let dbl = R.indices.filter { R[$0] == "double" }
            XCTAssertGreaterThanOrEqual(zip(dbl, dbl.dropFirst()).map { $1 - $0 }.min() ?? 99, 3, "Double gap")
            for e in ["clawChallenge", "balloonRise"] {
                let share = Double(L.filter { $0 == e }.count) / Double(n)
                XCTAssertTrue((0.40...0.60).contains(share), "\(e) share \(share)")
            }
            XCTAssertLessThanOrEqual(maxAbsence(R) { $0 == "skyJump" }, 2, "Rocket absent")
            XCTAssertLessThanOrEqual(maxAbsence(R) { $0 == "rocketRace" }, 2, "Sky absent")
            var unchanged = 0
            for i in 1..<n where L[i] == L[i - 1] && R[i] == R[i - 1] { unchanged += 1 }
            XCTAssertLessThanOrEqual(Double(unchanged) / Double(n - 1), 0.08, "unchanged weeks")
            // measured (T7): Double 14.7 %, Claw 49.2 %, unchanged 4.9 %
            XCTAssertEqual(dbl.count, 153)
            XCTAssertEqual(unchanged, 51)
        }
    }

    // MARK: A3

    func testThePlanIsConstantInsideAWeekAndRollsAtMonday0700UTC() throws {
        let r = try Self.loadFixture().rules
        for w in [0, 1, 22, 23, 100, 1043] {
            let start = EventRotation.weekStart(w, r).seconds
            let a = EventRotation.live(at: SocialTime(seconds: start), level: 60, rules: r)
            let offsets: [Int64] = [1, 3600, 86_400 * 3, 604_799]
            for dt in offsets {
                XCTAssertEqual(EventRotation.live(at: SocialTime(seconds: start + dt), level: 60, rules: r), a, "w\(w) +\(dt)")
            }
            XCTAssertEqual(EventRotation.week(SocialTime(seconds: start - 1), r), w - 1, "the second before the roll")
            XCTAssertEqual(EventRotation.week(SocialTime(seconds: start), r), w, "the roll")
            let d = Date(timeIntervalSince1970: Double(start))
            var cal = Calendar(identifier: .gregorian); cal.timeZone = TimeZone(identifier: "UTC")!
            XCTAssertEqual(cal.component(.weekday, from: d), 2, "a Monday")
            XCTAssertEqual(cal.component(.hour, from: d), 7)
            XCTAssertEqual(cal.component(.minute, from: d), 0)
        }
    }

    func testAClockSetBackAcrossAMondayNeverShowsLastWeeksEvents() throws {
        var rules = EconomyRules.default
        rules.events.rotation = try Self.loadFixture().rules.rotation
        var s = C3.fresh(rules)
        s.level = 60
        let mon22 = Date(timeIntervalSince1970: 1_790_578_800)                  // week 22: Up & Away + Double
        _ = Events.refresh(&s, now: mon22 + 3600, rivals: StubRivals(), me: PlayerStanding(name: "x", avatar: 0, country: "TR", level: 60, ledger: []), rules: rules)
        XCTAssertEqual(Events.status(s, now: mon22 + 3600, rules: rules).live.ladder, .balloonRise)
        // the device clock goes back 2 days (week 21: Treasure Climb + Rocket): the world clock holds at the high-water mark
        let back = mon22 - 2 * 86_400
        let st = Events.status(s, now: back, rules: rules)
        XCTAssertEqual(st.live.ladder, .balloonRise, "a clock set back never shows last week's ladder event")
        XCTAssertEqual(st.week?.week, 22)
        XCTAssertNil(st.claw, "no Treasure Climb from a rewound clock")
        XCTAssertNotNil(st.balloon)
        XCTAssertEqual(Events.joinRocketRace(&s, now: back, rules: rules).failure == nil, true, "Double week 22: Rocket joins")
        // the one-time rebase (SPEC-social §5): a clock that ran > 30 days ahead and was repaired follows the repaired clock
        var f = C3.fresh(rules)
        f.level = 60
        let future = mon22 + 45 * 86_400                                       // week 28 (Claw + Double)
        _ = Events.status(f, now: future, rules: rules)
        _ = EconomyClock.social(&f, wall: future)
        XCTAssertEqual(EventRotation.week(SocialTime(seconds: f.social.highWater), rules.events), 28)
        let repaired = mon22 + 3600
        let t = EconomyClock.social(&f, wall: repaired)
        XCTAssertEqual(t.seconds, Int64(repaired.timeIntervalSince1970), "rebased to the repaired clock")
        XCTAssertEqual(Events.status(f, now: repaired, rules: rules).week?.week, 22)
        XCTAssertEqual(Events.status(f, now: repaired, rules: rules).live.ladder, .balloonRise)
    }

    // MARK: A4

    func testSegmentationRowsOfTheFixture() throws {
        let f = try Self.loadFixture()
        let rows = f.doc["segmentation"] as! [[String: Any]]
        XCTAssertEqual(rows.count, 84)
        for row in rows {
            let lad = row["ladder"] as! String
            let race = Self.ids(row["race"])
            let code = race.count == 2 ? EventRotation.double : f.rules.rotation.race.firstIndex(of: race[0])!
            let level = row["level"] as! Int
            let live = EventRotation.live(picks: (f.rules.rotation.ladder.firstIndex(of: lad)!, code), level: level, f.rules)
            let want = row["live"] as! [String: Any]
            XCTAssertEqual(Self.names(live.always), Self.ids(want["always"]), "\(row)")
            XCTAssertEqual(live.ladder?.rawValue, want["ladder"] as? String, "\(row)")
            XCTAssertEqual(Self.names(live.race), Self.ids(want["race"]), "\(row)")
        }
    }

    func testTheFourNamedSegmentationCases() throws {
        let r = try Self.loadFixture().rules
        // week 26 = Treasure Climb + Rocket, week 22 = Up & Away + Double, week 23 = Treasure Climb + Sky
        XCTAssertEqual(EventRotation.live(week: 26, level: 45, rules: r).race, [.skyJump], "L45 in a Rocket week → Cloud Hop")
        XCTAssertEqual(EventRotation.live(week: 22, level: 45, rules: r).race, [.skyJump], "L45 in a Double week → Cloud Hop only")
        let l35 = EventRotation.live(week: 22, level: 35, rules: r)
        XCTAssertEqual(l35, LiveEvents(always: [.streakRace], ladder: .balloonRise, race: []), "L35 → the ladder only")
        XCTAssertEqual(EventRotation.live(week: 26, level: 60, rules: r),
                       LiveEvents(always: [.streakRace, .weeklyContest], ladder: .clawChallenge, race: [.rocketRace]), "L60 → the calendar")
        XCTAssertEqual(EventRotation.live(week: 22, level: 32, rules: r).ladder, nil, "below the ladder unlock")
        // the ladder unlock: Up & Away takes the Claw's when social.json names none (the compiled table keeps its 5 rows)
        var noEntry = r
        noEntry.unlocks.removeValue(forKey: "balloonRise")
        XCTAssertEqual(noEntry.unlockLevel(.balloonRise), 33)
        XCTAssertEqual(EventRules.default.unlockLevel(.balloonRise), 33)
        XCTAssertNil(EventRules.default.unlocks["balloonRise"])
    }

    func testAnUnavailableMemberHandsItsWeeksToTheOther() throws {
        // the app's Release art gate: while Up & Away's art is not in the build, its weeks run Treasure Climb instead
        var r = try Self.loadFixture().rules
        r.rotation.unavailable = ["balloonRise"]
        for w in 0..<120 {
            let live = EventRotation.live(week: w, level: 60, rules: r)
            XCTAssertEqual(live.ladder, .clawChallenge, "w\(w)")
            XCTAssertEqual(live.race, EventRotation.live(week: w, level: 60, rules: try Self.loadFixture().rules).race, "the race slot is untouched")
        }
        // the calendar itself never changes (one calendar for everyone)
        XCTAssertEqual(EventRotation.plan(week: 22, rules: r).ladder, .balloonRise)
        // and it is runtime-only: never written to social.json
        let text = String(decoding: try JSONEncoder().encode(r.rotation), as: UTF8.self)
        XCTAssertFalse(text.contains("unavailable"), text)
    }

    func testNextStartFindsTheNextLiveWeek() throws {
        let r = try Self.loadFixture().rules
        // week 22 (Double) → Rocket next live in week 25 (Double); Sky in week 23
        XCTAssertEqual(EventRotation.nextStart(of: .rocketRace, after: 22, level: 60, rules: r), EventRotation.weekStart(25, r))
        XCTAssertEqual(EventRotation.nextStart(of: .skyJump, after: 22, level: 60, rules: r), EventRotation.weekStart(23, r))
        XCTAssertEqual(EventRotation.nextStart(of: .clawChallenge, after: 23, level: 60, rules: r), EventRotation.weekStart(26, r))
        XCTAssertNil(EventRotation.nextStart(of: .rocketRace, after: 22, level: 45, rules: r), "L45 never sees the Rocket")
    }

    func testTheShippedSocialJSONTurnsTheRotationOnWithTheReferenceConfig() throws {
        let url = C3.appRoot.appendingPathComponent("App/Resources/Tuning/social.json")
        let (ev, problems) = EventRules.load(social: try Data(contentsOf: url))
        XCTAssertEqual(problems, [])
        var want = try Self.loadFixture().rules
        want.rotation.unavailable = []
        XCTAssertEqual(ev.rotation, want.rotation, "social.json events.rotation == rotation_ref.py CONFIG")
        XCTAssertTrue(ev.rotation.enabled)
        XCTAssertEqual(ev.unlockLevel(.balloonRise), 33)
        XCTAssertEqual(ev.unlocks["balloonRise"], 33, "the shipped file names the ladder event's unlock")
        XCTAssertEqual(ev.balloonRise, EventRules.BalloonRise(), "social.json events.balloonRise == the compiled table")
    }

    func testSocialConfigRoundTripsTheRotationAndUpAndAwayBlocks() throws {
        // SOC1's SocialConfig encodes the shipped social.json (SocialNamesTests: file == compiled defaults): it must carry
        // C3's two new blocks unchanged, so the file keeps what C3 reads
        let url = C3.appRoot.appendingPathComponent("App/Resources/Tuning/social.json")
        let data = try Data(contentsOf: url)
        let cfg = try JSONDecoder().decode(SocialConfig.self, from: data)
        let (ev, _) = EventRules.load(social: data)
        XCTAssertEqual(cfg.rotation, ev.rotation)
        XCTAssertEqual(cfg.balloonRise, ev.balloonRise)
        XCTAssertEqual(cfg.unlocks.balloonRise, ev.unlocks["balloonRise"])
        XCTAssertEqual(cfg, SocialConfig.default)
        let encoded = try JSONEncoder().encode(SocialConfig.default)
        let (back, problems) = EventRules.load(social: encoded)
        XCTAssertEqual(problems, [])
        XCTAssertEqual(back.rotation, SocialConfig.shippedRotation)
        XCTAssertEqual(back.balloonRise, EventRules.BalloonRise())
        XCTAssertEqual(back.unlockLevel(.balloonRise), 33)
        XCTAssertEqual(back.skyJump.levels, [5, 7, 10], "SOC1c's block is still there")
        // tolerant: a broken rotation block keeps the compiled default (never a crash, never a half-parsed calendar)
        let (broken, _) = EventRules.load(social: Data(#"{"events":{"rotation":{"enabled":true,"ladder":["clawChallenge"],"seed":"zz"}}}"#.utf8))
        XCTAssertTrue(broken.rotation.enabled)
        XCTAssertEqual(broken.rotation.ladder, ["clawChallenge", "balloonRise"])
        XCTAssertEqual(broken.rotation.seed, "0x524F544154494F4E")
    }

    func testPlanCostStaysSmall() {
        // A10's budget is on the phone (status p95 ≤ 0.2 ms); here only a gross guard in a Debug build: 20 years ahead
        var r = EventRules()
        r.rotation.enabled = true
        let t0 = ProcessInfo.processInfo.systemUptime
        for _ in 0..<50 { _ = EventRotation.live(week: 1043, level: 60, rules: r) }
        let per = (ProcessInfo.processInfo.systemUptime - t0) / 50
        XCTAssertLessThan(per, 0.005, "one plan at week 1043 took \(per * 1000) ms")
    }
}
