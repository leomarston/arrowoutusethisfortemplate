import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// SPEC-architecture §4.17 "EventsTests" (C3; §4.10, SPEC-gameplay §11, SPEC-social §4): the multiplier ladder and its
/// reset; Claw points = the multiplier and untouched by a loss (replayed against every bar reading of the phone session
/// L32–L61); Streak Race flags; the Weekly score; Sky Jump; Rocket Race; settlement from the world; rewind safety.
final class EventsTests: XCTestCase {
    let r = C3.rules
    let me = PlayerStanding(name: "Hsheh", avatar: 0, country: "TR", level: 62, ledger: [])

    func state(level: Int, step: Int = 0) -> PlayerState {
        var s = C3.fresh()
        s.level = level
        s.events.streakStep = step
        return s
    }

    func win(_ s: inout PlayerState, _ level: Int, at t: Date, firstTry: Bool = true, tag: LevelTag = .normal,
             rivals: RivalProvider = StubRivals()) -> [EventOutcome] {
        guard case .success = Economy.startAttempt(&s, levels: [level], now: t, rules: r) else { XCTFail("start L\(level)"); return [] }
        Economy.finishAttempt(&s, outcome: .won(C3.win([level], tag: tag, firstTry: firstTry)), now: t, rules: r)
        return Events.onWin(&s, WinContext(levels: [level], tag: tag, firstTry: firstTry, now: t), rivals: rivals, rules: r)
    }

    func lose(_ s: inout PlayerState, _ level: Int, at t: Date, _ reason: LossReason = .timeUp) -> [EventOutcome] {
        guard case .success = Economy.startAttempt(&s, levels: [level], now: t, rules: r) else { XCTFail("start L\(level)"); return [] }
        Economy.finishAttempt(&s, outcome: .lost(reason), now: t, rules: r)
        return Events.onLoss(&s, LossContext(levels: [level], reason: reason, now: t), rules: r)
    }

    // MARK: the multiplier

    func testTheMultiplierLadderAndItsReset() {
        var s = state(level: 30)
        var t = C3.trt("08:00:00")
        Economy.grant(&s, .unlimited(86_400), now: t)                   // 9 failed attempts below: no lives gate
        var scored: [Int] = []
        for n in 30..<37 {
            let out = win(&s, n, at: t)
            scored.append(s.events.streakRace.score)
            if n == 30 { XCTAssertEqual(out.first, .multiplier(from: 1, to: 5)) }
            t += 60
        }
        // the multiplier lit BEFORE each win: 1, 5, 10, 25, 100, 100, 100 (x100 stays)
        XCTAssertEqual(scored, [1, 6, 16, 41, 141, 241, 341])
        XCTAssertEqual(Events.multiplier(s, rules: r), 100)
        // a paid continue never reaches onLoss (the streak is kept); a failed attempt of any kind → x1
        for reason in [LossReason.timeUp, .hearts, .quit, .killed] {
            s.events.streakStep = 3
            XCTAssertEqual(lose(&s, 40, at: t, reason), [.multiplier(from: 25, to: 1)], "\(reason)")
            XCTAssertEqual(lose(&s, 40, at: t, reason), [], "already x1")
        }
        // the retry's win scores x1 and steps to x5 (VERIFIED L47/L52)
        let before = s.events.streakRace.score
        XCTAssertEqual(win(&s, 40, at: t, firstTry: false).first, .multiplier(from: 1, to: 5))
        XCTAssertEqual(s.events.streakRace.score, before + 1)
        // before the Streak Race unlock (L30) the multiplier does not move and nothing scores
        var early = state(level: 12)
        XCTAssertEqual(win(&early, 12, at: t), [])
        XCTAssertEqual(early.events.streakStep, 0)
        XCTAssertEqual([early.events.streakStep, early.events.streakRace.score, early.events.weekly.score, early.events.claw.points,
                        early.events.claims.count], [0, 0, 0, 0, 0])
        XCTAssertNil(early.events.streakRace.index)
        XCTAssertNil(early.events.claw.week)
    }

    // MARK: the phone session L32–L61 (research/levels.md, phone-session1-progress.md, meta.md, fail.md)

    func testThePhoneSessionL32ToL61() {
        var s = state(level: 32, step: 4)
        s.coins = 2240
        s.stats.firstTryWins = 31                                          // L1–L31 all first try (V1/V2)
        let join = C3.trt("03:47:00")                                     // the Rocket Race joined after the L54 win
        let rivals = StubRivals(
            rocket: { _, _, at in
                let m = Double(at.seconds - Int64(join.timeIntervalSince1970)) / 60
                return [StubRivals.lane(1, m < 13 ? 4 : 5), StubRivals.lane(2, m < 12 ? 3 : 4), StubRivals.lane(3, 3),
                        StubRivals.lane(4, 0)]
            },
            sky: { _, _ in SkyJumpField(total: 100, left: 7, winners: 7) })
        let hard: Set = [34, 44, 54], superHard: Set = [39, 49, 59]
        let failsFirst: Set = [32, 33, 47, 52]
        // the Claw bar after each win (points/target), as the phone showed them; nil = not read on the phone
        let bar: [Int: (Int, Int)] = [33: (0, 200), 34: (5, 200), 36: (40, 200), 37: (140, 200), 38: (40, 300), 39: (140, 300),
                                      40: (240, 300), 41: (40, 400), 43: (240, 400), 44: (340, 400), 45: (40, 300), 46: (140, 300),
                                      47: (141, 300), 48: (146, 300), 49: (156, 300), 50: (181, 300), 51: (281, 300), 52: (282, 300),
                                      53: (287, 300), 54: (297, 300), 55: (22, 500), 56: (122, 500), 57: (222, 500), 58: (322, 500),
                                      59: (422, 500), 60: (22, 500), 61: (122, 500)]
        var t = C3.trt("00:17:00")
        var claimed: [EventClaim] = []
        var clawSteps: [Int] = []
        var rocketLanes: [Int: [EventOutcome]] = [:]
        var tokenWarnings: [Int: Events.StreakWarning] = [:]
        for level in 32...61 {
            if failsFirst.contains(level) {
                tokenWarnings[level] = Events.continueWarning(s, now: t, rules: r)
                _ = lose(&s, level, at: t)
                t += 300
            }
            if level == 55 { t = join.addingTimeInterval(5 * 60) }
            if level == 56 { t = join.addingTimeInterval(10 * 60) }
            if level == 57 { t = join.addingTimeInterval(15 * 60) }
            let tag: LevelTag = hard.contains(level) ? .hard : superHard.contains(level) ? .superHard : .normal
            let out = win(&s, level, at: t, firstTry: !failsFirst.contains(level), tag: tag, rivals: rivals)
            for o in out { if case .clawStep(let n, _) = o { clawSteps.append(n) } }
            if (55...57).contains(level) { rocketLanes[level] = rocket(out) }
            if let (p, target) = bar[level] {
                let c = s.events.claw
                XCTAssertEqual([c.points, Events.clawTarget(c, rules: r) ?? -1], [p, target], "Claw bar after L\(level)")
            }
            // home: the claims ("Tap to Claim") and the offers
            _ = Events.refresh(&s, now: t + 60, rivals: rivals, me: me, rules: r)
            for c in s.events.claims { claimed.append(c); Events.claim(&s, id: c.id, now: t + 60) }
            if level == 32 {
                XCTAssertEqual(s.events.claw, ClawState(week: EventSchedule.week(EconomyClock.social(&s, wall: t)), points: 0, step: 0),
                               "the Claw intro after the L32 win: 0/1")
            }
            if level == 39, case .failure(let e) = Events.joinSkyJump(&s, now: t + 90, rules: r) { XCTFail("sky \(e)") }
            if level == 54, case .failure(let e) = Events.joinRocketRace(&s, now: join, rules: r) { XCTFail("rocket \(e)") }
            t += 300
        }
        // Claw: steps 1–6 with the phone's rewards; points untouched by the fails (140 → 141 at L47)
        XCTAssertEqual(clawSteps, [1, 2, 3, 4, 5, 6])
        let clawRewards = claimed.filter { $0.kind == .clawStep }.map(\.grant)
        XCTAssertEqual(clawRewards, [.unlimited(1800), .coins(100), .unlimited(1800), .coins(200), .unlimited(3600), .booster(.hint, 1)])
        XCTAssertEqual(Events.status(s, now: t, rules: r).claw?.accessibilityValue, "122/500 x100")
        XCTAssertEqual(Events.clawNextReward(s.events.claw, rules: r), .coins(300), "next: 300 coins (step 7)")
        // Streak Race: the flags of the session = 1824 (the player's 2065 − the 241 scored before the session, SPEC-social §1.1)
        XCTAssertEqual(s.events.streakRace.score, 1824)
        // Weekly Contest: L50–L61 = 12 (meta §7: "Hsheh 12")
        XCTAssertEqual(s.events.weekly.score, 12)
        // Sky Jump stage 1: L40–L44 first try → 5000 / 7 winners = 714; the stage-2 offer (7 levels) follows
        XCTAssertEqual(claimed.filter { $0.kind == .skyJumpShare }.map(\.grant), [.coins(714)])
        XCTAssertEqual(claimed.first { $0.kind == .skyJumpShare }?.value, 7)
        XCTAssertEqual(Events.status(s, now: t, rules: r).skyJump?.levels, 7)
        XCTAssertEqual(s.events.wins["skyJump"], 1)                     // Profile: "Sky Jump Wins 1"
        // Rocket Race: join ∞ 30m; L55 1/5, L56 2/5, L57 3/5 while a rival had 5/5 → lost, rank 4
        XCTAssertEqual(claimed.filter { $0.kind == .rocketJoin }.map(\.grant), [.unlimited(1800)])
        XCTAssertEqual(rocketLanes[55], [.rocketProgress(mine: 1)])
        XCTAssertEqual(rocketLanes[56], [.rocketProgress(mine: 2)])
        XCTAssertEqual(rocketLanes[57], [.rocketProgress(mine: 3), .rocketFinished(rank: 4, reward: nil)])
        XCTAssertEqual(s.events.rocket.lastResult, .lost)
        XCTAssertEqual(Events.status(s, now: t, rules: r).rocketRace?.joinable, true, "'Join' again at once")
        // the fail flow's step B: "You will lose your streak!" before the Claw (L32), "… 100 token …" at x100 with it (L47)
        XCTAssertEqual(tokenWarnings[32], Events.StreakWarning(streakActive: true, tokens: nil, multiplier: 100))
        XCTAssertEqual(tokenWarnings[33], Events.StreakWarning(streakActive: true, tokens: 5, multiplier: 5))
        XCTAssertEqual(tokenWarnings[47], Events.StreakWarning(streakActive: true, tokens: 100, multiplier: 100))
        // coins: 2240 + 30 wins (24 × 20 + 3 × 60 + 3 × 100 = 960) + Claw 100 + 200 + Sky Jump 714 = 4214 (economy.md §1)
        XCTAssertEqual(s.coins, 4214)
        XCTAssertEqual(s.pendingCoinFly, 960)
        XCTAssertEqual(s.boosters, ["freeze": 3, "hint": 4])            // bulb x1 from Claw step 6
        XCTAssertEqual(s.stats.firstTryWins, 57)                        // Profile at LEVEL 62: "First Try Wins 57"
        XCTAssertEqual(s.level, 62)
        let ledgerWins = s.social.ledger.filter { $0.kind == .win }
        XCTAssertEqual(ledgerWins.count, 30)
        XCTAssertEqual(ledgerWins.map(\.score).reduce(0, +), 1824)
        XCTAssertEqual(s.social.ledger.filter { $0.kind == .fail }.map(\.level), [32, 33, 47, 52])
        XCTAssertEqual(s.social.ledger.filter { $0.kind == .streakJoin }.count, 1)
        XCTAssertEqual(s.social.ledger.filter { $0.kind == .weeklyJoin }.count, 1)
        C3.evidence("phone-session-replay.txt", "L32–L61: Claw steps \(clawSteps), bar \(s.events.claw.points)/"
                    + "\(Events.clawTarget(s.events.claw, rules: r) ?? 0); Streak Race \(s.events.streakRace.score); Weekly "
                    + "\(s.events.weekly.score); claims \(claimed.map { "\($0.kind.rawValue)=\($0.grant)" }); coins \(s.coins); "
                    + "First Try Wins \(s.stats.firstTryWins)\n")
    }

    // MARK: the Claw ladder

    func testClawOverflowCarriesAndTheLadderEndsFullUntilTheWeekEnds() {
        var s = state(level: 40, step: 4)
        let t = C3.trt("08:00:00")
        var total = 0
        for _ in 0..<200 { _ = win(&s, 40, at: t); total += 100 }
        XCTAssertEqual(s.events.claw.step, 20)
        XCTAssertEqual(s.events.claims.filter { $0.kind == .clawStep }.count, 20)
        XCTAssertEqual(s.events.claims.last?.grant, .coins(10000))
        XCTAssertEqual(s.events.wins["clawChallenge"], 1, "Profile: Claw Challenge Wins")
        let st = Events.status(s, now: t, rules: r).claw
        XCTAssertEqual(st?.complete, true)
        XCTAssertEqual(st?.points, 1500)
        XCTAssertEqual(st?.target, 1500)
        XCTAssertNil(Events.clawTarget(s.events.claw, rules: r))
        XCTAssertEqual(Events.continueWarning(s, now: t, rules: r).tokens, nil, "no Claw tokens left to lose")
        // Monday 07:00 UTC: a new week restarts at step 1 with 0 points; unclaimed rewards stay
        let monday = C3.utc("2026-09-28T07:00:00Z")
        _ = Events.refresh(&s, now: monday, rivals: StubRivals(), me: me, rules: r)
        XCTAssertEqual(s.events.claw, ClawState(week: EventSchedule.week(SocialTime(seconds: Int64(monday.timeIntervalSince1970))), points: 0, step: 0))
        XCTAssertEqual(s.events.claims.count, 20)
        XCTAssertEqual(total, 20_000)
    }

    // MARK: Streak Race settlement

    func testTheStreakRaceSettlesFromTheWorldsFinalStandings() {
        var s = state(level: 40, step: 4)
        let day = C3.utc("2026-09-25T06:00:00Z")                        // an hour before the day ends
        _ = win(&s, 40, at: day)
        XCTAssertEqual(s.events.streakRace.score, 100)
        let index = EventSchedule.day(SocialTime(seconds: Int64(day.timeIntervalSince1970)))
        var asked: [SocialTime] = []
        let rows: [RaceStanding] = [StubRivals.lane(1, 3530), StubRivals.lane(2, 3423), StubRivals.lane(3, 2950),
                                    StubRivals.lane(4, 1882)]
        let box = Box()
        let rivals = StubRivals(streak: { inst, _, at in box.asked.append((inst, at)); return rows })
        let next = C3.utc("2026-09-25T07:00:05Z")
        let out = Events.refresh(&s, now: next, rivals: rivals, me: me, rules: r)
        asked = box.asked.map(\.1)
        XCTAssertEqual(asked, [EventSchedule.dayStart(index + 1)], "the final standings, at the race end")
        XCTAssertEqual(box.asked.first?.0.index, index)
        XCTAssertEqual(out, [.grant(.coins(100))], "rank 5 of the rows → 100 coins")
        XCTAssertEqual(s.events.claims.last?.kind, .streakRacePrize)
        XCTAssertEqual(s.events.claims.last?.value, 5)
        XCTAssertEqual(s.events.streakRace.index, index + 1, "the home joined the new day's race")
        XCTAssertEqual(s.events.streakRace.score, 0)
        XCTAssertTrue(s.events.toSettle.isEmpty)
        // rank 1 = 2000 coins + a Streak Race Win; the world's own row for the player wins over our count
        var w = state(level: 40, step: 4)
        _ = win(&w, 40, at: day)
        let top = StubRivals(streak: { _, _, _ in [StubRivals.lane(0, 100, me: true, rank: 1), StubRivals.lane(2, 99, rank: 2)] })
        XCTAssertEqual(Events.refresh(&w, now: next, rivals: top, me: me, rules: r), [.grant(.coins(2000))])
        XCTAssertEqual(w.events.wins["streakRace"], 1)
        // no standings from the world: no prize (a rank is never invented)
        var n = state(level: 40, step: 4)
        _ = win(&n, 40, at: day)
        XCTAssertEqual(Events.refresh(&n, now: next, rivals: StubRivals(), me: me, rules: r), [])
        XCTAssertFalse(n.events.claims.contains { $0.kind == .streakRacePrize })
        XCTAssertTrue(n.events.toSettle.isEmpty)
    }

    final class Box: @unchecked Sendable { var asked: [(EventInstance, SocialTime)] = [] }

    // MARK: Weekly Contest

    func testTheWeeklyContest() {
        var s = state(level: 49)
        let t = C3.utc("2026-09-25T12:00:00Z")
        XCTAssertFalse(Events.joinWeekly(&s, now: t, rules: r), "locked before L50")
        s.level = 50
        XCTAssertTrue(Events.joinWeekly(&s, now: t, rules: r))
        XCTAssertFalse(Events.joinWeekly(&s, now: t, rules: r))
        XCTAssertEqual(s.events.weekly.score, 0)
        XCTAssertEqual(win(&s, 50, at: t + 60).last, .weeklyScore(1))
        _ = lose(&s, 51, at: t + 120)
        _ = win(&s, 51, at: t + 180, firstTry: false)
        XCTAssertEqual(s.events.weekly.score, 2, "wins only")
        let week = EventSchedule.week(SocialTime(seconds: Int64(t.timeIntervalSince1970)))
        let monday = C3.utc("2026-09-28T07:00:00Z")
        _ = Events.refresh(&s, now: monday, rivals: StubRivals(), me: me, rules: r)
        XCTAssertEqual(Events.weeksToSettle(s).map(\.index), [week])
        XCTAssertEqual(Events.weeksToSettle(s).first?.score, 2)
        XCTAssertEqual(Events.settleWeekly(&s, week: week, rank: 1, rules: r), [.grant(.coins(2000))])
        XCTAssertEqual(s.stats.weeklyContestWins, 1)
        XCTAssertEqual(Events.settleWeekly(&s, week: week, rank: 1, rules: r), [], "settled once")
        XCTAssertEqual(s.stats.weeklyContestWins, 1)
        // prizes 2000 / 1000 / 500, nothing from rank 4
        for (rank, prize) in [(2, 1000), (3, 500), (4, 0)] {
            var p = state(level: 50)
            _ = win(&p, 50, at: t)
            _ = Events.refresh(&p, now: monday, rivals: StubRivals(), me: me, rules: r)
            XCTAssertEqual(Events.settleWeekly(&p, week: week, rank: rank, rules: r), prize > 0 ? [.grant(.coins(prize))] : [])
            XCTAssertEqual(p.stats.weeklyContestWins, 0)
        }
    }

    // MARK: Sky Jump

    func testSkyJumpRuns() {
        var s = state(level: 39)
        let t = C3.utc("2026-09-25T08:00:00Z")
        XCTAssertEqual(Events.joinSkyJump(&s, now: t, rules: r).failure, .locked)
        s.level = 40
        guard case .success(let run) = Events.joinSkyJump(&s, now: t, rules: r) else { return XCTFail() }
        XCTAssertEqual(run.stage, 1)
        XCTAssertEqual(run.instance.end.seconds - run.instance.start.seconds, 86_400, "24 h from joining")
        XCTAssertEqual(Events.joinSkyJump(&s, now: t, rules: r).failure, .alreadyActive)
        XCTAssertEqual(sky(win(&s, 40, at: t + 60)), [.skyJumpProgress(levels: 1, of: 5)])
        XCTAssertEqual(sky(win(&s, 41, at: t + 120, firstTry: false)), [], "not on the first try: no progress, no fail")
        XCTAssertEqual(s.events.sky.active?.progress, 1)
        // a failed attempt fails the run; re-join after 30 min
        XCTAssertEqual(sky(lose(&s, 42, at: t + 180)), [.skyJumpFailed])
        XCTAssertEqual(s.events.sky.lastResult, .failed)
        XCTAssertEqual(Events.joinSkyJump(&s, now: t + 180 + 1799, rules: r).failure,
                       .coolingDown(until: SocialTime(seconds: Int64(t.timeIntervalSince1970) + 180 + 1800)))
        guard case .success = Events.joinSkyJump(&s, now: t + 180 + 1800, rules: r) else { return XCTFail() }
        // two stage-1 runs a day
        _ = lose(&s, 42, at: t + 4000)
        XCTAssertEqual(Events.joinSkyJump(&s, now: t + 6000, rules: r).failure, .limitReached)
        // the next event day: runs again; 5 first-try wins → the share; stage 2 needs 7
        let d2 = C3.utc("2026-09-26T08:00:00Z")
        let rivals = StubRivals(sky: { run, _ in SkyJumpField(total: 100, left: 12, winners: run.stage == 1 ? 7 : 3) })
        guard case .success = Events.joinSkyJump(&s, now: d2, rules: r) else { return XCTFail() }
        var out: [EventOutcome] = []
        for k in 0..<5 { out = sky(win(&s, 43 + k, at: d2 + Double(60 * (k + 1)), rivals: rivals)) }
        XCTAssertEqual(out, [.skyJumpProgress(levels: 5, of: 5), .skyJumpWon(share: 714, winners: 7)])
        XCTAssertEqual(s.events.claims.last.map { [$0.grant.coins, $0.value] }, [714, 7])
        guard case .success(let st2) = Events.joinSkyJump(&s, now: d2 + 600, rules: r) else { return XCTFail() }
        XCTAssertEqual(st2.stage, 2)
        for k in 0..<7 { out = sky(win(&s, 48 + k, at: d2 + 600 + Double(60 * (k + 1)), rivals: rivals)) }
        XCTAssertEqual(out.last, .skyJumpWon(share: 7000 / 3, winners: 3))
        // the 24 h window runs out: the run fails at the next refresh
        guard case .success(let st3) = Events.joinSkyJump(&s, now: d2 + 2000, rules: r) else { return XCTFail() }
        XCTAssertEqual(st3.stage, 3)
        _ = win(&s, 60, at: d2 + 2100, rivals: rivals)
        XCTAssertEqual(Events.refresh(&s, now: d2 + 2000 + 86_400, rivals: rivals, me: me, rules: r).first, .skyJumpFailed)
        XCTAssertEqual(s.events.sky.lastResult, .expired)
        XCTAssertEqual(s.events.wins["skyJump"], 2)
    }

    // MARK: Rocket Race

    func testRocketRaces() {
        var s = state(level: 54)
        let t = C3.utc("2026-09-25T08:00:00Z")
        XCTAssertEqual(Events.joinRocketRace(&s, now: t, rules: r).failure, .locked)
        s.level = 55
        guard case .success(let race) = Events.joinRocketRace(&s, now: t, rules: r) else { return XCTFail() }
        XCTAssertEqual(race.stage, 1)
        XCTAssertEqual(race.instance.end, EventSchedule.dayStart(EventSchedule.day(race.joinedAt) + 1), "ends with the event day")
        XCTAssertEqual(race.instance.event, .rocketRace)
        XCTAssertEqual(s.events.claims.map(\.kind), [.rocketJoin])
        // stage 1: the player's 5th win first → 500 coins + ∞ 45m; stage 2 offered at once (7 levels)
        let slow = StubRivals(rocket: { _, _, _ in [StubRivals.lane(1, 4), StubRivals.lane(2, 2), StubRivals.lane(3, 1), StubRivals.lane(4, 0)] })
        var out: [EventOutcome] = []
        for k in 0..<5 { out = rocket(win(&s, 55 + k, at: t + Double(60 * (k + 1)), firstTry: k != 2, rivals: slow)) }
        XCTAssertEqual(out, [.rocketProgress(mine: 5), .rocketFinished(rank: 1, reward: Grant(coins: 500, unlimitedLives: 2700))])
        XCTAssertEqual(s.events.rocket.lastResult, .won)
        XCTAssertEqual(Events.status(s, now: t + 400, rules: r).rocketRace?.levels, 7)
        guard case .success(let r2) = Events.joinRocketRace(&s, now: t + 400, rules: r) else { return XCTFail() }
        XCTAssertEqual(r2.stage, 2)
        XCTAssertEqual(r2.instance.event.rawValue, "rocketRace.2")
        XCTAssertEqual(s.events.claims.filter { $0.kind == .rocketJoin }.count, 1, "the join ∞ once per event day")
        // a rival finishes while the player is away → lost at the home refresh (rank by lanes, a tie behind the rival)
        let fast = StubRivals(rocket: { _, _, _ in [StubRivals.lane(1, 7), StubRivals.lane(2, 2), StubRivals.lane(3, 1), StubRivals.lane(4, 0)] })
        _ = win(&s, 60, at: t + 500, rivals: slow)
        _ = win(&s, 61, at: t + 560, rivals: slow)
        XCTAssertEqual(Events.refresh(&s, now: t + 900, rivals: fast, me: me, rules: r), [.rocketFinished(rank: 3, reward: nil)])
        XCTAssertEqual(s.events.rocket.lastResult, .lost)
        // re-join at once (no cooldown): stage 2 again; a race still running when the day ends expires
        guard case .success(let r3) = Events.joinRocketRace(&s, now: t + 1000, rules: r) else { return XCTFail() }
        XCTAssertEqual(r3.stage, 2)
        let dayEnd = Date(timeIntervalSince1970: Double(r3.instance.end.seconds))
        XCTAssertEqual(Events.refresh(&s, now: dayEnd, rivals: slow, me: me, rules: r), [.rocketFinished(rank: 5, reward: nil)],
                       "no win yet: behind all four lanes")
        XCTAssertEqual(s.events.rocket.lastResult, .expired)
        // the next day starts at stage 1 with a fresh join ∞
        guard case .success(let r4) = Events.joinRocketRace(&s, now: dayEnd + 60, rules: r) else { return XCTFail() }
        XCTAssertEqual(r4.stage, 1)
        XCTAssertEqual(s.events.claims.filter { $0.kind == .rocketJoin }.count, 2)
    }

    // MARK: rewind safety

    func testAClockSetBackNeverRewindsAnEvent() {
        var s = state(level: 60, step: 4)
        let monday = C3.utc("2026-09-28T07:00:10Z")                     // a new week and a new day
        _ = win(&s, 60, at: monday)
        let week = s.events.weekly.index, day = s.events.streakRace.index
        let claw = s.events.claw
        // the device clock set back into the previous week / day: every hook still happens at the latest time shown
        let back = monday.addingTimeInterval(-3 * 86_400)
        _ = win(&s, 61, at: back)
        XCTAssertEqual(s.events.weekly.index, week)
        XCTAssertEqual(s.events.streakRace.index, day)
        XCTAssertEqual(s.events.weekly.score, 2)
        XCTAssertEqual(s.events.claw.week, claw.week)
        XCTAssertEqual(s.events.claw.points, claw.points + 100)
        XCTAssertTrue(s.events.toSettle.isEmpty, "the previous week / day are not re-opened")
        // a Sky Jump run's 24 h cannot be stretched by setting the clock back and forth
        s.level = 60
        guard case .success(let run) = Events.joinSkyJump(&s, now: monday, rules: r) else { return XCTFail() }
        _ = Events.refresh(&s, now: monday.addingTimeInterval(86_400), rivals: StubRivals(), me: me, rules: r)
        XCTAssertNil(s.events.sky.active)
        XCTAssertEqual(s.events.sky.lastResult, .expired)
        XCTAssertEqual(run.instance.end.seconds, Int64(monday.timeIntervalSince1970) + 86_400)
        _ = Events.refresh(&s, now: back, rivals: StubRivals(), me: me, rules: r)
        XCTAssertNil(s.events.sky.active, "setting the clock back does not revive it")
        // a second join ∞ in the same day cannot be farmed by setting the clock back to "yesterday"
        s.level = 60
        guard case .success = Events.joinRocketRace(&s, now: monday, rules: r) else { return XCTFail() }
        _ = Events.refresh(&s, now: monday.addingTimeInterval(90_000), rivals: StubRivals(rocket: { _, _, _ in [StubRivals.lane(1, 9)] }),
                           me: me, rules: r)
        let joins = s.events.claims.filter { $0.kind == .rocketJoin }.count
        _ = Events.joinRocketRace(&s, now: back, rules: r)
        XCTAssertEqual(s.events.claims.filter { $0.kind == .rocketJoin }.count, joins, "same effective day: no second ∞")
    }

    func testAMonthLongRepairedClockEndsTheEventsOfTheAbandonedFuture() {
        var s = state(level: 60, step: 4)
        let future = C3.utc("2026-11-20T12:00:00Z")                     // the device clock was ~8 weeks ahead
        _ = win(&s, 60, at: future)
        guard case .success = Events.joinSkyJump(&s, now: future, rules: r) else { return XCTFail() }
        XCTAssertNotNil(s.events.streakRace.index)
        let repaired = C3.utc("2026-09-25T12:00:00Z")
        _ = Economy.reconcileOnLaunch(&s, now: repaired, rules: r)      // SOC1's clock rebases (> 30 days behind)
        XCTAssertEqual(s.social.highWater, Int64(repaired.timeIntervalSince1970))
        XCTAssertNil(s.events.sky.active, "a run stamped in the abandoned future ends")
        XCTAssertEqual(s.events.sky.lastResult, .expired)
        let out = Events.refresh(&s, now: repaired, rivals: StubRivals(streak: { _, _, _ in [StubRivals.lane(1, 1)] }), me: me, rules: r)
        XCTAssertEqual(out, [], "the future day's race is dropped, never settled")
        XCTAssertTrue(s.events.toSettle.isEmpty)
        XCTAssertEqual(s.events.streakRace.index, EventSchedule.day(SocialTime(seconds: Int64(repaired.timeIntervalSince1970))))
        XCTAssertEqual(s.events.streakRace.score, 0)
    }

    // MARK: the ledger, claims, status

    func testTheLedgerRecordsWinsFailsAndJoinsForTheWorld() {
        var s = state(level: 40)
        let t = C3.utc("2026-09-25T08:00:00Z")
        for k in 0..<5 { _ = win(&s, 40 + k, at: t + Double(60 * k)) }
        _ = lose(&s, 45, at: t + 400)
        _ = win(&s, 45, at: t + 500, firstTry: false)
        let wins = s.social.ledger.filter { $0.kind == .win }
        XCTAssertEqual(wins.map(\.level), [40, 41, 42, 43, 44, 45])
        XCTAssertEqual(wins.map(\.score), [1, 5, 10, 25, 100, 1], "the Streak Race points of each win (the chip before it)")
        XCTAssertEqual(wins.map(\.firstTry), [true, true, true, true, true, false])
        XCTAssertEqual(s.social.ledger.filter { $0.kind == .fail }.map(\.level), [45])
        let day = EventSchedule.day(SocialTime(seconds: Int64(t.timeIntervalSince1970)))
        XCTAssertEqual(s.social.ledger.filter { $0.kind == .streakJoin }.map(\.instance), [day], "one join marker per day")
        XCTAssertEqual(s.social.ledger.first { $0.kind == .streakJoin }?.at, s.events.streakRace.joinedAt)
        XCTAssertTrue(s.social.ledger.filter { $0.kind == .weeklyJoin }.isEmpty, "the Weekly starts at L50")
        s.level = 50
        XCTAssertTrue(Events.joinWeekly(&s, now: t + 600, rules: r))
        XCTAssertEqual(s.social.ledger.filter { $0.kind == .weeklyJoin }.map(\.instance),
                       [EventSchedule.week(SocialTime(seconds: Int64(t.timeIntervalSince1970)))])
        // claims: once each
        XCTAssertNil(Events.claim(&s, id: 999, now: t))
        let c = s.events.claims.first!
        let coins = s.coins
        XCTAssertEqual(Events.claim(&s, id: c.id, now: t + 700), c.grant)
        XCTAssertNil(Events.claim(&s, id: c.id, now: t + 700), "claimed once")
        XCTAssertEqual(s.coins, coins + c.grant.coins)
        // the Rocket Race's stage reaches the world through the instance id (SOC1's convention)
        XCTAssertEqual(Events.rocketInstanceID(stage: 1), .rocketRace)
        XCTAssertEqual(Events.rocketInstanceID(stage: 3).rawValue, "rocketRace.3")
    }

    func testStatusIsReadOnlyAndHidesLockedEvents() {
        var s = state(level: 29)
        let t = C3.utc("2026-09-25T08:00:00Z")
        let st = Events.status(s, now: t, rules: r)
        XCTAssertNil(st.streakRace); XCTAssertNil(st.claw); XCTAssertNil(st.weekly); XCTAssertNil(st.rocketRace); XCTAssertNil(st.skyJump)
        XCTAssertEqual(st.multiplier, 1)
        s.level = 62
        let before = s
        let open = Events.status(s, now: t, rules: r)
        XCTAssertEqual(s, before, "status never mutates")
        XCTAssertEqual(open.streakRace?.joined, false)
        XCTAssertEqual(open.streakRace?.endsAt, EventSchedule.dayStart(EventSchedule.day(SocialTime(seconds: Int64(t.timeIntervalSince1970))) + 1))
        XCTAssertEqual(open.claw?.accessibilityValue, "0/1 x1")
        XCTAssertEqual(open.skyJump?.joinable, true)
        XCTAssertEqual(open.rocketRace?.levels, 5)
        XCTAssertEqual(open.weekly?.endsAt, SocialTime(seconds: 1_790_578_800), "Monday 2026-09-28 07:00 UTC")
    }

    func testTheCalendar() {
        let c = EventRules.Calendar()
        XCTAssertEqual(EventSchedule.day(SocialTime(seconds: c.epoch)), 0)
        XCTAssertEqual(EventSchedule.day(SocialTime(seconds: c.epoch - 1)), -1)
        XCTAssertEqual(EventSchedule.week(SocialTime(seconds: c.epoch + 7 * 86_400 - 1)), 0)
        // the phone's countdowns (SPEC-social §1.2): 00:50:44 TRT → the Streak Race ends 10:00 TRT (07:00 UTC)
        let t = EconomyClock.social(copyOf: C3.trt("00:50:44"))
        XCTAssertEqual(EventSchedule.instance(.streakRace, at: t)?.end.seconds, Int64(C3.trt("10:00:00").timeIntervalSince1970))
        XCTAssertEqual(EventSchedule.instance(.clawChallenge, at: t)?.end.seconds,
                       Int64(C3.trt("10:00:00", day: 28).timeIntervalSince1970), "the Claw week ends Monday 10:00 TRT")
        XCTAssertNil(EventSchedule.instance(.rocketRace, at: t))
    }
}

private extension EventOutcome {
    enum Kind { case rocket, other }
    var kind: Kind {
        switch self { case .rocketProgress, .rocketFinished: return .rocket; default: return .other }
    }
}

private extension EconomyClock {
    static func social(copyOf d: Date) -> SocialTime { SocialTime(seconds: Int64(d.timeIntervalSince1970.rounded(.down))) }
}

/// The Sky Jump / Rocket Race outcomes of a hook's list (the other events report alongside).
private func sky(_ o: [EventOutcome]) -> [EventOutcome] {
    o.filter { switch $0 { case .skyJumpProgress, .skyJumpWon, .skyJumpFailed: return true; default: return false } }
}
private func rocket(_ o: [EventOutcome]) -> [EventOutcome] { o.filter { $0.kind == .rocket } }
