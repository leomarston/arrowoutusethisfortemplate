import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// B1 EVENTS-P — events.md §8.4 A5 (the hooks under the rotation) and the event notifications' planner (§6.4; A11's
/// "outside 10-21 local" mutation target): a Join outside a live week → `.notLive(next:)`; a Sky Jump run crossing the roll
/// finishes and pays; the status hides non-live featured events; the kill switch keeps the v552 hooks; ≤ 1 event
/// notification per 24 h, inside the local window, in every zone.
final class EventsRotationHookTests: XCTestCase {
    let me = PlayerStanding(name: "Hsheh", avatar: 0, country: "TR", level: 62, ledger: [])
    static let w22 = Date(timeIntervalSince1970: 1_790_578_800)                  // Mon 2026-09-28 07:00 UTC: Up & Away + Double
    static func week(_ w: Int) -> Date { w22 + Double((w - 22) * 604_800) }

    func rules() throws -> EconomyRules { try BalloonRiseTests.rules() }

    // MARK: A5 joins

    func testAJoinOutsideALiveWeekIsNotLive() throws {
        let r = try rules()
        var s = C3.fresh(r)
        s.level = 60
        // week 23 = Treasure Climb + Cloud Hop: no Rocket Rally; its next week is 25
        let t = Self.week(23) + 3600
        XCTAssertEqual(Events.joinRocketRace(&s, now: t, rules: r).failure, .notLive(next: EventRotation.weekStart(25, r.events)))
        XCTAssertNil(s.events.rocket.active)
        XCTAssertTrue(s.events.claims.isEmpty, "no join claim for a refused join")
        guard case .success = Events.joinSkyJump(&s, now: t, rules: r) else { return XCTFail("Cloud Hop is live in week 23") }
        // week 26 = Treasure Climb + Rocket: Sky refuses (after the running run ends)
        var u = C3.fresh(r)
        u.level = 60
        XCTAssertEqual(Events.joinSkyJump(&u, now: Self.week(26) + 60, rules: r).failure,
                       .notLive(next: EventRotation.weekStart(27, r.events)))
        // a locked event is still `.locked` (the unlock comes first)
        var low = C3.fresh(r)
        low.level = 20
        XCTAssertEqual(Events.joinSkyJump(&low, now: t, rules: r).failure, .locked)
        // the status hides the non-live events and keeps the always-on ones
        let st = Events.status(u, now: Self.week(26) + 60, rules: r)
        XCTAssertNil(st.skyJump)
        XCTAssertNotNil(st.rocketRace)
        XCTAssertNotNil(st.claw)
        XCTAssertNil(st.balloon)
        XCTAssertNotNil(st.streakRace)
        XCTAssertNotNil(st.weekly)
        XCTAssertEqual(st.live, LiveEvents(always: [.streakRace, .weeklyContest], ladder: .clawChallenge, race: [.rocketRace]))
        XCTAssertEqual(st.week?.week, 26)
        XCTAssertTrue(st.rotating)
        XCTAssertEqual(st.nextLive.featured, [.balloonRise, .skyJump], "week 27 = Up & Away + Cloud Hop")
    }

    func testASkyJumpRunCrossingTheRollFinishesAndPays() throws {
        let r = try rules()
        var s = C3.fresh(r)
        s.level = 60
        Economy.grant(&s, .unlimited(86_400 * 3), now: Self.week(23))
        // joined on Sunday evening of week 23 (Cloud Hop), the Monday roll to week 24 (Up & Away + Cloud Hop) … and 26 (Rocket)
        let sun = Self.week(26) - 5 * 3600                                          // week 25 (Double): Sunday 02:00 UTC
        guard case .success(let run) = Events.joinSkyJump(&s, now: sun, rules: r) else { return XCTFail("join in a Double week") }
        XCTAssertEqual(run.instance.end.seconds, Int64(sun.timeIntervalSince1970) + 86_400)
        // the roll into week 26 (no Cloud Hop): the run keeps its own 24 h; the badge still shows it
        let after = Self.week(26) + 3600
        _ = Events.refresh(&s, now: after, rivals: StubRivals(), me: me, rules: r)
        XCTAssertNotNil(s.events.sky.active, "the run survives the roll")
        let st = Events.status(s, now: after, rules: r)
        XCTAssertEqual(st.skyJump?.progress, 0)
        XCTAssertEqual(st.skyJump?.why, .alreadyActive)
        XCTAssertFalse(st.live.contains(.skyJump))
        var out: [EventOutcome] = []
        for k in 0..<5 {
            s.level += 1
            out = Events.onWin(&s, WinContext(levels: [60 + k], tag: .normal, firstTry: true, now: after + Double(60 * (k + 1))),
                               rivals: StubRivals(), rules: r)
        }
        XCTAssertTrue(out.contains(.skyJumpWon(share: 5000 / 7, winners: 7)), "\(out)")
        XCTAssertEqual(s.events.claims.last?.kind, .skyJumpShare, "its win pays")
        // and no new run starts in week 26
        XCTAssertEqual(Events.joinSkyJump(&s, now: after + 3600, rules: r).failure, .notLive(next: EventRotation.weekStart(27, r.events)))
        XCTAssertNil(Events.status(s, now: after + 3600, rules: r).skyJump, "the badge is gone once the run ended")
    }

    func testTheKillSwitchKeepsTheV552Hooks() throws {
        // the compiled default (the existing C3 tests' rules): every event every week, whatever the calendar says
        let r = EconomyRules.default
        var s = C3.fresh(r)
        s.level = 60
        let t = Self.week(22) + 3600                                                // an Up & Away week in the calendar
        let out = Events.onWin(&s, WinContext(levels: [60], tag: .normal, firstTry: true, now: t), rivals: StubRivals(), rules: r)
        XCTAssertTrue(out.contains { if case .clawPoints = $0 { return true }; return false })
        XCTAssertTrue(BalloonRiseTests.balloonOutcomes(out).isEmpty)
        guard case .success = Events.joinRocketRace(&s, now: t, rules: r) else { return XCTFail("rocket") }
        guard case .success = Events.joinSkyJump(&s, now: t, rules: r) else { return XCTFail("sky") }
        let st = Events.status(s, now: t, rules: r)
        XCTAssertNotNil(st.claw)
        XCTAssertNil(st.balloon)
        XCTAssertFalse(st.rotating)
    }

    // MARK: event notifications (events.md §6.4)

    static let zones = ["Europe/Istanbul", "America/New_York", "America/Los_Angeles", "Pacific/Honolulu", "Asia/Tokyo",
                        "Australia/Sydney", "Pacific/Kiritimati", "Pacific/Pago_Pago", "Europe/London", "Asia/Kolkata",
                        "America/Sao_Paulo", "Asia/Kathmandu"].map { TimeZone(identifier: $0)! }

    func testEveryEventNotificationIsInsideTheLocalWindowAndOnePer24Hours() throws {
        let r = try rules()
        var plans = 0, items = 0, starts = 0, endings = 0
        for zone in Self.zones {
            for w in 22..<74 {                                                     // one year of weeks
                for (level, progress) in [(35, true), (45, false), (60, true), (60, false)] {
                    var s = C3.fresh(r)
                    s.level = level
                    let t = Self.week(w) + Double((w * 7919) % 500_000)            // somewhere inside the week
                    _ = Events.refresh(&s, now: t, rivals: StubRivals(), me: me, rules: r)
                    if progress {
                        s.level += 1
                        _ = Events.onWin(&s, WinContext(levels: [level], tag: .normal, firstTry: true, now: t), rivals: StubRivals(), rules: r)
                    }
                    let p = EventNotifications.plan(s, now: t, rules: r, zone: zone)
                    plans += 1
                    for it in p where it.kind != .weeklyEnding {
                        XCTAssertTrue(EventNotifications.inWindow(it.at, zone: zone, window: [10, 21]),
                                      "\(zone.identifier) w\(w) L\(level): \(it)")
                        if it.kind == .eventStart { starts += 1 } else { endings += 1 }
                    }
                    for (a, b) in zip(p, p.dropFirst()) { XCTAssertGreaterThanOrEqual(b.at - a.at, 86_400, "\(zone.identifier) w\(w): \(p)") }
                    XCTAssertTrue(p.allSatisfy { $0.at > Int64(t.timeIntervalSince1970) }, "never in the past")
                    items += p.count
                }
            }
        }
        XCTAssertGreaterThan(starts, 500, "the start notifications exist")
        XCTAssertGreaterThan(endings, 200, "the ending reminders exist")
        XCTAssertGreaterThan(items, plans / 2)
    }

    func testStartEndingAndWeeklyEndingInTurkey() throws {
        let r = try rules()
        let trt = TimeZone(identifier: "Europe/Istanbul")!
        // week 22 (Up & Away + Double), Thursday noon; an L60 player with an Up & Away streak and the Weekly Cup joined
        var s = C3.fresh(r)
        s.level = 60
        let t = Self.week(22) + 3 * 86_400 + 5 * 3600
        s.level = 61
        _ = Events.onWin(&s, WinContext(levels: [60], tag: .normal, firstTry: true, now: t), rivals: StubRivals(), rules: r)
        XCTAssertNotNil(s.events.weekly.index)
        let p = EventNotifications.plan(s, now: t, rules: r, zone: trt)
        let end = EventRotation.weekStart(23, r.events).seconds                   // Mon 10:00 TRT
        // weeklyEnding (existing) at end − 2 h wins the cap: the Up & Away reminder falls inside its 24 h and is dropped
        XCTAssertEqual(p.first, .init(kind: .weeklyEnding, at: end - 7200, events: [.weeklyContest]))
        XCTAssertFalse(p.contains { $0.kind == .eventEnding })
        // week 23 brings Treasure Climb + Cloud Hop: new vs week 22's Up & Away + Double → Treasure Climb; 24 h after the
        // weekly reminder, inside the window: Tuesday 08:00 TRT → 10:00 TRT
        let start = try XCTUnwrap(p.first { $0.kind == .eventStart })
        XCTAssertEqual(start.events, [.clawChallenge])
        XCTAssertFalse(start.double)
        XCTAssertEqual(start.at, end - 7200 + 86_400 + 2 * 3600, "Tue 10:00 TRT")
        // without the Weekly Cup (L45): the ending reminder is at the window's last moment before end − 3 h (Sun 21:00 TRT)
        var u = C3.fresh(r)
        u.level = 46
        _ = Events.onWin(&u, WinContext(levels: [45], tag: .normal, firstTry: true, now: t), rivals: StubRivals(), rules: r)
        let q = EventNotifications.plan(u, now: t, rules: r, zone: trt)
        let ending = try XCTUnwrap(q.first { $0.kind == .eventEnding })
        XCTAssertEqual(ending.events, [.balloonRise])
        XCTAssertEqual(ending.at, end - 13 * 3600, "Sunday 21:00 TRT")
        XCTAssertFalse(ending.threeHours)
        // the start (Mon 10:00 TRT) would be 13 h after that reminder: it moves to 24 h later, still inside the window
        let qs = try XCTUnwrap(q.first { $0.kind == .eventStart })
        XCTAssertEqual(qs.events, [.clawChallenge])
        XCTAssertEqual(qs.at, end + 11 * 3600, "Monday 21:00 TRT")
    }

    func testTheCapRemembersWhatWasDelivered() throws {
        let r = try rules()
        let tokyo = TimeZone(identifier: "Asia/Tokyo")!
        var s = C3.fresh(r)
        s.level = 46
        let t = Self.week(22) + 4 * 86_400
        s.level = 47
        _ = Events.onWin(&s, WinContext(levels: [46], tag: .normal, firstTry: true, now: t), rivals: StubRivals(), rules: r)
        let p = EventNotifications.plan(s, now: t, rules: r, zone: tokyo)
        let ending = try XCTUnwrap(p.first { $0.kind == .eventEnding })
        XCTAssertTrue(ending.threeHours, "Tokyo: end − 3 h = Monday 13:00 local, inside the window")
        EventNotifications.record(&s, p)
        // the player comes back after it fired: it counts; a new plan keeps 24 h away from it
        let back = Date(timeIntervalSince1970: Double(ending.at + 600))
        EventNotifications.foreground(&s, now: back)
        XCTAssertEqual(s.events.notify.lastAt, ending.at)
        XCTAssertEqual(s.events.notify.pending, [:])
        let q = EventNotifications.plan(s, now: back, rules: r, zone: tokyo)
        XCTAssertTrue(q.allSatisfy { $0.at - ending.at >= 86_400 }, "\(q)")
        // a notification cancelled before its time (the game came back first) does not count
        var u = s
        EventNotifications.record(&u, [.init(kind: .eventStart, at: Int64(back.timeIntervalSince1970) + 7200, events: [.skyJump])])
        EventNotifications.foreground(&u, now: back + 60)
        XCTAssertEqual(u.events.notify.lastAt, ending.at)
    }

    func testTheWindowHelpers() {
        let trt = TimeZone(identifier: "Europe/Istanbul")!
        let mon0700utc: Int64 = 1_790_578_800                                         // 10:00 TRT
        XCTAssertTrue(EventNotifications.inWindow(mon0700utc, zone: trt, window: [10, 21]))
        XCTAssertFalse(EventNotifications.inWindow(mon0700utc - 1, zone: trt, window: [10, 21]))
        XCTAssertEqual(EventNotifications.firstInWindow(atOrAfter: mon0700utc - 3 * 3600, zone: trt, window: [10, 21]), mon0700utc)
        XCTAssertEqual(EventNotifications.firstInWindow(atOrAfter: mon0700utc + 11 * 3600 + 1, zone: trt, window: [10, 21]),
                       mon0700utc + 86_400)
        XCTAssertEqual(EventNotifications.lastInWindow(atOrBefore: mon0700utc - 1, zone: trt, window: [10, 21]), mon0700utc - 13 * 3600)
        // New York across the DST change (2026-11-01): the window follows the local clock
        let ny = TimeZone(identifier: "America/New_York")!
        let after = EventNotifications.firstInWindow(atOrAfter: 1_793_602_800, zone: ny, window: [10, 21])   // Mon 2026-11-02 07:00 UTC
        XCTAssertTrue(EventNotifications.inWindow(after, zone: ny, window: [10, 21]))
        XCTAssertEqual(after, 1_793_602_800 + 8 * 3600, "02:00 EST → 10:00 EST")
        let before = EventNotifications.firstInWindow(atOrAfter: 1_793_602_800 - 7 * 86_400, zone: ny, window: [10, 21])
        XCTAssertEqual(before, 1_793_602_800 - 7 * 86_400 + 7 * 3600, "a week earlier, 03:00 EDT → 10:00 EDT")
    }
}
