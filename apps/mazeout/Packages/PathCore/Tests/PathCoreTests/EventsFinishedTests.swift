import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// B1b EVENTS FINISHED STATE (owner item 14; events.md "PH-0a", VERIFIED v582 across the Monday 07:00 UTC roll): the ended
/// events' badges stay and read "Finished" and the trophy tab gets a red "!" until the player opens the result; then the new
/// week's featured events show. The boundary, on the real calendar (EventRotationTests pins it): week 23 = Treasure Climb +
/// Cloud Hop, week 24 = Up & Away + Cloud Hop, week 25 = Up & Away + Double. Before / at the roll, the open, the claim, the win,
/// one instance deep, the daily roll, the kill switch, the save, a clock set back.
final class EventsFinishedTests: XCTestCase {
    let me = PlayerStanding(name: "Hsheh", avatar: 0, country: "TR", level: 60, ledger: [])
    static func week(_ w: Int) -> Date { EventsRotationHookTests.week(w) }
    static func secs(_ d: Date) -> Int64 { Int64(d.timeIntervalSince1970) }

    func rules(enabled: Bool = true) throws -> EconomyRules { try BalloonRiseTests.rules(enabled: enabled) }

    /// A player at L60 on Sunday evening of week 23 (the Treasure Climb week), as v582's shot had them: the ladder bar at step 12
    /// with 537 points toward its threshold, today's Hot Streak joined with 12 flags, the Weekly Cup joined with 5 wins.
    func sundayOfWeek23(_ r: EconomyRules) -> PlayerState {
        var s = C3.fresh(r)
        s.level = 60
        let sunday = Self.week(24) - 11 * 3600
        s.social.highWater = Self.secs(sunday)
        s.events.claw = ClawState(week: 23, points: 537, step: 11)
        s.events.streakRace = ContestState(index: 24 * 7 - 1, joinedAt: SocialTime(seconds: Self.secs(sunday) - 3600), score: 12,
                                           lastScoreAt: SocialTime(seconds: Self.secs(sunday)))
        s.events.weekly = ContestState(index: 23, joinedAt: SocialTime(seconds: Self.secs(Self.week(23)) + 3600), score: 5,
                                       lastScoreAt: SocialTime(seconds: Self.secs(sunday)))
        return s
    }

    // MARK: before / at the roll

    func testBeforeTheRollTheBadgesCountDownAndNothingIsFinished() throws {
        let r = try rules()
        let s = sundayOfWeek23(r)
        let before = Self.week(24) - 1
        let st = Events.status(s, now: before, rules: r)
        XCTAssertTrue(st.finished.isEmpty, "\(st.finished)")
        XCTAssertEqual(st.claw?.points, 537)
        XCTAssertEqual(st.claw?.target, r.claw.ladder[11].threshold)
        XCTAssertEqual(st.claw?.endsAt.seconds, Self.secs(Self.week(24)), "the bar's countdown ends at the roll")
        XCTAssertEqual(st.streakRace?.endsAt.seconds, Self.secs(Self.week(24)))
        XCTAssertEqual(st.streakRace?.score, 12)
        XCTAssertEqual(st.weekly?.score, 5)
        XCTAssertNil(st.balloon, "week 23 runs Treasure Climb")
        XCTAssertEqual(Events.finished(s, at: SocialTime(seconds: Self.secs(before)), rules: r), [])
    }

    func testAtTheRollTheJoinedEventsReadFinishedWithTheirFinalNumbers() throws {
        let r = try rules()
        let s = sundayOfWeek23(r)
        let roll = Self.week(24)
        let st = Events.status(s, now: roll, rules: r)
        // the ladder bar keeps its final numbers and ends at the roll (v582: "537/800" + "Finished")
        let claw = try XCTUnwrap(st.finished.claw, "\(st.finished)")
        XCTAssertEqual(claw.points, 537)
        XCTAssertEqual(claw.step, 12)
        XCTAssertEqual(claw.target, r.claw.ladder[11].threshold)
        XCTAssertEqual(claw.endsAt.seconds, Self.secs(roll))
        XCTAssertFalse(claw.complete)
        XCTAssertEqual(st.finished.ladder, .clawChallenge)
        XCTAssertEqual(st.finished.streakRace?.score, 12)
        XCTAssertEqual(st.finished.streakRace?.index, 24 * 7 - 1)
        XCTAssertEqual(st.finished.weekly?.score, 5, "the trophy tab's red '!'")
        XCTAssertEqual(st.finished.weekly?.index, 23)
        // the rules rolled as always: the new week's calendar is computed (the home shows it once the result is opened)
        XCTAssertNil(st.claw, "week 24 has no Treasure Climb")
        XCTAssertEqual(st.balloon?.streak, 0, "week 24 = Up & Away")
        XCTAssertEqual(st.live.featured, [.balloonRise, .skyJump])
        XCTAssertEqual(st.streakRace?.index, 24 * 7, "the new day's Hot Streak")
        XCTAssertEqual(st.streakRace?.joined, false)
        // status is read-only: nothing stored in `s`
        XCTAssertTrue(s.events.finished.isEmpty)
        // the refresh at the next home stores the holds, joins the new instances, and keeps the holds
        var h = s
        _ = Events.refresh(&h, now: roll + 60, rivals: StubRivals(), me: me, rules: r)
        XCTAssertEqual(Set(h.events.finished.map(\.event)), [.streakRace, .weeklyContest, .clawChallenge])
        XCTAssertEqual(h.events.claw, ClawState(), "the ladder state restarted (the roll)")
        XCTAssertEqual(h.events.balloon.week, 24, "Up & Away joined at home")
        XCTAssertEqual(h.events.streakRace.index, 24 * 7, "today's Hot Streak joined at home")
        XCTAssertEqual(Events.status(h, now: roll + 60, rules: r).finished, st.finished, "the same holds from the stored state")
    }

    // MARK: open → the new week

    func testOpeningTheResultShowsTheNewWeekInItsSlot() throws {
        let r = try rules()
        var s = sundayOfWeek23(r)
        let t = Self.week(24) + 120
        _ = Events.refresh(&s, now: Self.week(24) + 60, rivals: StubRivals(), me: me, rules: r)
        XCTAssertTrue(Events.openFinished(&s, .clawChallenge, now: t, rules: r))
        var st = Events.status(s, now: t, rules: r)
        XCTAssertNil(st.finished.claw)
        XCTAssertNil(st.finished.ladder, "the ladder slot shows this week's event now")
        XCTAssertNotNil(st.balloon)
        XCTAssertNotNil(st.finished.streakRace, "each hold is opened on its own")
        XCTAssertNotNil(st.finished.weekly)
        XCTAssertFalse(Events.openFinished(&s, .clawChallenge, now: t, rules: r), "opening twice drops nothing")
        XCTAssertTrue(Events.openFinished(&s, .streakRace, now: t, rules: r))
        XCTAssertTrue(Events.openFinished(&s, .weeklyContest, now: t, rules: r))
        st = Events.status(s, now: t, rules: r)
        XCTAssertTrue(st.finished.isEmpty)
        XCTAssertEqual(st.streakRace?.joined, true, "the new day's Hot Streak (joined by the refresh) counts down")
        // opening before any refresh (the idle home crossed the roll): the open itself rolls the calendar and drops only its hold
        var idle = sundayOfWeek23(r)
        XCTAssertTrue(Events.openFinished(&idle, .clawChallenge, now: Self.week(24) + 30, rules: r))
        XCTAssertEqual(Set(idle.events.finished.map(\.event)), [.streakRace, .weeklyContest])
        XCTAssertEqual(idle.events.claw, ClawState())
        XCTAssertNil(Events.status(idle, now: Self.week(24) + 30, rules: r).finished.claw, "never re-held after the open")
    }

    // MARK: the claim, then the new week

    func testClaimingTheRankPrizeIsOpeningTheResult() throws {
        let r = try rules()
        var s = sundayOfWeek23(r)
        // the world ranks the player 1st in yesterday's Hot Streak
        var rivals = StubRivals()
        rivals.streak = { _, _, _ in [StubRivals.lane(1, 12, me: true, rank: 1), StubRivals.lane(2, 11, rank: 2)] }
        // a Treasure Climb step claim earned before the roll (still waiting)
        Events.addClaim(&s, .clawChallenge, .clawStep, grant: .coins(300), value: 11, index: 23,
                        at: SocialTime(seconds: Self.secs(Self.week(24)) - 7200))
        let t = Self.week(24) + 60
        _ = Events.refresh(&s, now: t, rivals: rivals, me: me, rules: r)
        let prize = try XCTUnwrap(s.events.claims.first { $0.kind == .streakRacePrize }, "\(s.events.claims)")
        XCTAssertEqual(prize.index, 24 * 7 - 1)
        XCTAssertNotNil(Events.status(s, now: t, rules: r).finished.streakRace, "held until the result is claimed / opened")
        let coins = s.coins
        XCTAssertEqual(Events.claim(&s, id: prize.id, now: t), .coins(r.events.streakRace.prizes[0]))
        XCTAssertEqual(s.coins, coins + r.events.streakRace.prizes[0])
        var st = Events.status(s, now: t, rules: r)
        XCTAssertNil(st.finished.streakRace, "the claim, then the new day's Hot Streak")
        XCTAssertNotNil(st.finished.claw)
        // a step claim of the ended ladder is a reward, not its result: the bar stays Finished
        let step = try XCTUnwrap(s.events.claims.first { $0.kind == .clawStep })
        Events.claim(&s, id: step.id, now: t)
        XCTAssertNotNil(Events.status(s, now: t, rules: r).finished.claw)
        // the Weekly Cup podium (SOC2 settles the rank from the world): its claim clears the trophy's "!"
        XCTAssertEqual(Events.weeksToSettle(s).map(\.index), [23])
        _ = Events.settleWeekly(&s, week: 23, rank: 2, rules: r)
        XCTAssertNotNil(Events.status(s, now: t, rules: r).finished.weekly)
        let podium = try XCTUnwrap(s.events.claims.first { $0.kind == .weeklyPrize })
        Events.claim(&s, id: podium.id, now: t)
        st = Events.status(s, now: t, rules: r)
        XCTAssertNil(st.finished.weekly)
        XCTAssertEqual(st.finished.ladder, .clawChallenge, "only opening the bar's page ends its hold")
        // a prize of ANOTHER instance never clears a hold
        var other = sundayOfWeek23(r)
        _ = Events.refresh(&other, now: t, rivals: StubRivals(), me: me, rules: r)
        Events.addClaim(&other, .streakRace, .streakRacePrize, grant: .coins(100), value: 9, index: 24 * 7 - 2, at: SocialTime(seconds: 0))
        Events.claim(&other, id: other.events.claims.last!.id, now: t)
        XCTAssertNotNil(Events.status(other, now: t, rules: r).finished.streakRace)
    }

    // MARK: a win moves on; a loss does not

    func testACountedWinMovesThePlayerIntoTheNewInstanceALossDoesNot() throws {
        let r = try rules()
        var s = sundayOfWeek23(r)
        let t = Self.week(24) + 600
        _ = Events.refresh(&s, now: Self.week(24) + 60, rivals: StubRivals(), me: me, rules: r)
        _ = Events.onLoss(&s, LossContext(levels: [60], reason: .timeUp, now: t), rules: r)
        XCTAssertEqual(Set(s.events.finished.map(\.event)), [.streakRace, .weeklyContest, .clawChallenge], "a loss moves nothing")
        let out = Events.onWin(&s, WinContext(levels: [60], tag: .normal, firstTry: true, now: t + 60), rivals: StubRivals(), rules: r)
        s.level = 61
        XCTAssertTrue(out.contains(.balloonStreak(added: 1, total: 1, goal: 2)), "\(out)")
        let st = Events.status(s, now: t + 60, rules: r)
        XCTAssertNil(st.finished.ladder, "the win scored this week's Up & Away: its bar shows")
        XCTAssertNil(st.finished.streakRace, "the win scored today's Hot Streak")
        XCTAssertNotNil(st.finished.weekly, "the Weekly Cup's '!' is news: only opening / claiming clears it")
        XCTAssertEqual(st.balloon?.streak, 1)
        XCTAssertEqual(st.streakRace?.score, 1)
        // a win right AT the roll (a level started before 07:00): the win's own roll holds and it moves on in one step
        var edge = sundayOfWeek23(r)
        _ = Events.onWin(&edge, WinContext(levels: [60], tag: .normal, firstTry: true, now: Self.week(24) + 1), rivals: StubRivals(), rules: r)
        XCTAssertEqual(edge.events.finished.map(\.event), [.weeklyContest], "no Finished bar over points the win just earned")
        // below the Hot Streak's unlock nothing is scored and nothing moves
        var low = sundayOfWeek23(r)
        low.level = 29
        _ = Events.onWin(&low, WinContext(levels: [29], tag: .normal, firstTry: true, now: Self.week(24) + 1), rivals: StubRivals(), rules: r)
        XCTAssertEqual(Set(low.events.finished.map(\.event)), [.streakRace, .weeklyContest, .clawChallenge])
    }

    // MARK: one instance deep, the daily roll, the same ladder twice

    func testTheHoldIsOneInstanceDeep() throws {
        let r = try rules()
        var s = sundayOfWeek23(r)
        _ = Events.refresh(&s, now: Self.week(24) + 60, rivals: StubRivals(), me: me, rules: r)
        // never opened: the next week's roll drops week 23's holds; week 24's Up & Away (joined at home) is held in turn
        let st = Events.status(s, now: Self.week(25) + 60, rules: r)
        XCTAssertNil(st.finished.claw)
        XCTAssertNil(st.finished.weekly, "week 23's '!' went with week 24's end (the week-24 Weekly Cup was never joined)")
        XCTAssertEqual(st.finished.balloon?.streak, 0)
        XCTAssertEqual(st.finished.balloon?.endsAt.seconds, Self.secs(Self.week(25)))
        XCTAssertNil(st.finished.streakRace, "the Hot Streak joined on Monday of week 24 is six days past its end")
        // a player away three weeks sees no stale Finished
        let away = sundayOfWeek23(r)
        XCTAssertTrue(Events.status(away, now: Self.week(26) + 60, rules: r).finished.isEmpty)
        XCTAssertEqual(Events.finished(away, at: SocialTime(seconds: Self.secs(Self.week(26))), rules: r), [])
    }

    func testTheDailyRollHoldsTheHotStreakAlone() throws {
        let r = try rules()
        var s = sundayOfWeek23(r)
        _ = Events.refresh(&s, now: Self.week(24) + 60, rivals: StubRivals(), me: me, rules: r)
        XCTAssertTrue(Events.openFinished(&s, .clawChallenge, now: Self.week(24) + 90, rules: r))
        XCTAssertTrue(Events.openFinished(&s, .streakRace, now: Self.week(24) + 90, rules: r))
        XCTAssertTrue(Events.openFinished(&s, .weeklyContest, now: Self.week(24) + 90, rules: r))
        _ = Events.refresh(&s, now: Self.week(24) + 3600, rivals: StubRivals(), me: me, rules: r)
        // Tuesday 07:00 UTC: only the day's Hot Streak ended
        let tue = Self.week(24) + 86_400
        let before = Events.status(s, now: tue - 1, rules: r)
        XCTAssertTrue(before.finished.isEmpty)
        let st = Events.status(s, now: tue, rules: r)
        XCTAssertEqual(st.finished.streakRace?.index, 24 * 7)
        XCTAssertNil(st.finished.ladder, "Up & Away runs all week")
        XCTAssertNil(st.finished.weekly)
        XCTAssertEqual(st.streakRace?.index, 24 * 7 + 1)
    }

    func testTheSameLadderEventTwiceHoldsTheEndedOneBesideTheNewOne() throws {
        let r = try rules()
        var s = C3.fresh(r)
        s.level = 60
        s.social.highWater = Self.secs(Self.week(25)) - 3600
        s.events.balloon = BalloonState(week: 24, streak: 7, paid: 2, best: 9)          // weeks 24 and 25 both run Up & Away
        let st = Events.status(s, now: Self.week(25) + 5, rules: r)
        XCTAssertEqual(st.finished.balloon?.streak, 7)
        XCTAssertEqual(st.finished.balloon?.paid, 2)
        XCTAssertEqual(st.finished.balloon?.best, 9)
        XCTAssertEqual(st.finished.balloon?.endsAt.seconds, Self.secs(Self.week(25)))
        XCTAssertEqual(st.finished.ladder, .balloonRise)
        XCTAssertEqual(st.balloon?.streak, 0, "the new week's Up & Away starts at 0")
        XCTAssertEqual(st.balloon?.best, 9)
    }

    // MARK: the kill switch, the save, a clock set back

    func testTheKillSwitchHoldsNothing() throws {
        let r = try rules(enabled: false)
        var s = sundayOfWeek23(r)
        let st = Events.status(s, now: Self.week(24), rules: r)
        XCTAssertTrue(st.finished.isEmpty, "the v552 plan: the ended events go at the roll, as before")
        XCTAssertEqual(st.claw?.points, 0, "the new week's Treasure Climb (every week in the v552 plan)")
        _ = Events.refresh(&s, now: Self.week(24) + 60, rivals: StubRivals(), me: me, rules: r)
        XCTAssertTrue(s.events.finished.isEmpty)
        let json = String(decoding: try JSONEncoder().encode(s.events), as: UTF8.self)
        XCTAssertFalse(json.contains("\"finished\""), "a save under the kill switch re-encodes as before")
        XCTAssertFalse(Events.openFinished(&s, .clawChallenge, now: Self.week(24) + 90, rules: r))
    }

    func testTheSaveRoundTripsAndAnOldSaveDecodes() throws {
        let r = try rules()
        var s = sundayOfWeek23(r)
        _ = Events.refresh(&s, now: Self.week(24) + 60, rivals: StubRivals(), me: me, rules: r)
        XCTAssertEqual(s.events.finished.count, 3)
        let data = try JSONEncoder().encode(s)
        let back = try JSONDecoder().decode(PlayerState.self, from: data)
        XCTAssertEqual(back.events.finished, s.events.finished)
        XCTAssertEqual(back, s)
        // an old save (no key) decodes to no holds; a state without holds encodes without the key
        let old = try JSONDecoder().decode(EventsState.self, from: Data(#"{"streakStep":1}"#.utf8))
        XCTAssertEqual(old.finished, [])
        XCTAssertFalse(String(decoding: try JSONEncoder().encode(old), as: UTF8.self).contains("finished"))
        // a hold decodes with only its required keys
        let f = try JSONDecoder().decode(FinishedEvent.self, from: Data(#"{"event":"streakRace","index":7}"#.utf8))
        XCTAssertEqual(f, FinishedEvent(event: .streakRace, index: 7))
    }

    func testAClockSetBackNeverRevivesOrDuplicatesAHold() throws {
        let r = try rules()
        var s = sundayOfWeek23(r)
        _ = Events.refresh(&s, now: Self.week(24) + 60, rivals: StubRivals(), me: me, rules: r)
        XCTAssertTrue(Events.openFinished(&s, .clawChallenge, now: Self.week(24) + 90, rules: r))
        // the device clock set back to Sunday: the world clock holds at its high-water mark (no week 23 again, no new hold)
        let back = Self.week(24) - 5 * 3600
        let st = Events.status(s, now: back, rules: r)
        XCTAssertNil(st.finished.claw)
        XCTAssertNil(st.claw, "last week's Treasure Climb never comes back")
        _ = Events.refresh(&s, now: back, rivals: StubRivals(), me: me, rules: r)
        XCTAssertEqual(s.events.finished.map(\.event).sorted { $0.rawValue < $1.rawValue }, [.streakRace, .weeklyContest])
        // the one-time rebase (a clock repaired > 30 days back) drops the holds of the abandoned future
        Events.rebase(&s, to: SocialTime(seconds: Self.secs(Self.week(23)) + 3600), from: SocialTime(seconds: Self.secs(Self.week(24)) + 90))
        XCTAssertTrue(s.events.finished.isEmpty, "\(s.events.finished)")
    }
}
