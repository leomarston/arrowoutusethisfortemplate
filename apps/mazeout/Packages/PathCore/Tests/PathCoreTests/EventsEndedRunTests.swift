import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// INTEG (SOC2's C3 request, build-3): an ended Rocket Race / Sky Jump run is kept in `EventsState` — its window, join time,
/// stage, the player's final lane and when C3 judged it over (`lastRun`, `lastEndedAt`) — so SOC2's result pages rebuild the
/// same final lanes after a relaunch instead of reading an in-memory memo. The fields are additive: a save written before
/// them decodes with both nil, and a state without an ended run encodes byte-identically to before (no new keys).
final class EventsEndedRunTests: XCTestCase {
    let r = C3.rules
    let me = PlayerStanding(name: "Hsheh", avatar: 0, country: "TR", level: 62, ledger: [])

    func win(_ s: inout PlayerState, _ level: Int, at t: Date, firstTry: Bool = true, rivals: RivalProvider) -> [EventOutcome] {
        guard case .success = Economy.startAttempt(&s, levels: [level], now: t, rules: r) else { XCTFail("start L\(level)"); return [] }
        Economy.finishAttempt(&s, outcome: .won(C3.win([level], firstTry: firstTry)), now: t, rules: r)
        return Events.onWin(&s, WinContext(levels: [level], tag: .normal, firstTry: firstTry, now: t), rivals: rivals, rules: r)
    }

    func lose(_ s: inout PlayerState, _ level: Int, at t: Date) -> [EventOutcome] {
        guard case .success = Economy.startAttempt(&s, levels: [level], now: t, rules: r) else { XCTFail("start L\(level)"); return [] }
        Economy.finishAttempt(&s, outcome: .lost(.timeUp), now: t, rules: r)
        return Events.onLoss(&s, LossContext(levels: [level], reason: .timeUp, now: t), rules: r)
    }

    /// The save round trip of the app (StateStore's encoder: sorted keys, exact dates).
    func relaunch(_ s: PlayerState) throws -> PlayerState { try StateStore.decode(StateStore.encode(s)) }

    func social(_ d: Date) -> SocialTime { SocialTime(seconds: Int64(d.timeIntervalSince1970.rounded(.down))) }

    /// A deterministic world like SOC1's: every rival's lane is a pure function of (race, join time, moment); capped at 4 so
    /// the player (5 levels at stage 1) wins.
    static let slowRivals = StubRivals(rocket: { inst, joined, at in
        let minutes = Int((at.seconds - joined.seconds) / 60)
        return (1...4).map { StubRivals.lane(UInt64(inst.index * 10 + $0), min(4, minutes / ($0 + 1))) }
    })

    /// The result page's final lanes rebuilt from the saved facts alone: the world's rivals at the end moment + the
    /// player's final lane (what SOC2's `SocCompute.rocket` draws for an ended race).
    func finalLanes(_ s: PlayerState, _ world: RivalProvider) throws -> [RaceStanding] {
        let run = try XCTUnwrap(s.events.rocket.lastRun)
        let at = try XCTUnwrap(s.events.rocket.lastEndedAt)
        let mine = RaceStanding(rank: 0, player: SimPlayer(id: .max, name: me.name, country: me.country, avatar: me.avatar),
                                score: run.progress, isMe: true)
        return [mine] + world.rocketRace(run.instance, joinedAt: run.joinedAt, at: at).filter { !$0.isMe }
    }

    // MARK: Rocket Race

    func testAWonRocketRaceKeepsItsRunAndFinalLanesAcrossARelaunch() throws {
        var s = C3.fresh()
        s.level = 55
        let t = C3.utc("2026-09-25T08:00:00Z")
        guard case .success(let race) = Events.joinRocketRace(&s, now: t, rules: r) else { return XCTFail("join") }
        XCTAssertNil(s.events.rocket.lastRun, "a running race is `active`, not ended")
        XCTAssertNil(s.events.rocket.lastEndedAt)
        for k in 0..<5 { _ = win(&s, 55 + k, at: t + Double(60 * (k + 1)), rivals: Self.slowRivals) }
        XCTAssertEqual(s.events.rocket.lastResult, .won)
        XCTAssertNil(s.events.rocket.active)
        XCTAssertEqual(s.events.rocket.lastRun, RocketRun(instance: race.instance, joinedAt: race.joinedAt, stage: 1, progress: 5),
                       "the join time, window, stage and the player's final lane (5/5)")
        XCTAssertEqual(s.events.rocket.lastEndedAt, social(t + 300), "the 5th win")

        let text = String(decoding: try StateStore.encode(s), as: UTF8.self)
        XCTAssertTrue(text.contains("\"lastRun\"") && text.contains("\"lastEndedAt\""), "saved to disk")
        let back = try relaunch(s)
        XCTAssertEqual(back, s)
        XCTAssertEqual(back.events.rocket.lastRun, s.events.rocket.lastRun)
        XCTAssertEqual(back.events.rocket.lastEndedAt, s.events.rocket.lastEndedAt)
        let before = try finalLanes(s, Self.slowRivals)
        XCTAssertEqual(try finalLanes(back, Self.slowRivals), before, "a relaunch rebuilds the same final lanes")
        XCTAssertEqual(before.map(\.score), [5, 2, 1, 1, 1], "the lanes as they stood at the win (5 min after joining)")
        // the next join starts clean: the page shows the new race, not the old result
        guard case .success = Events.joinRocketRace(&s, now: t + 400, rules: r) else { return XCTFail("join 2") }
        XCTAssertNil(s.events.rocket.lastRun)
        XCTAssertNil(s.events.rocket.lastEndedAt)
        XCTAssertNil(s.events.rocket.lastResult)
    }

    func testALostAndAnExpiredRocketRaceKeepTheirRuns() throws {
        var s = C3.fresh()
        s.level = 55
        let t = C3.utc("2026-09-25T08:00:00Z")
        guard case .success(let race) = Events.joinRocketRace(&s, now: t, rules: r) else { return XCTFail("join") }
        _ = win(&s, 55, at: t + 60, rivals: Self.slowRivals)
        _ = win(&s, 56, at: t + 120, rivals: Self.slowRivals)
        // a rival reaches 5 while the player is away: lost at the home refresh
        let fast = StubRivals(rocket: { _, _, _ in [StubRivals.lane(1, 5), StubRivals.lane(2, 3), StubRivals.lane(3, 1), StubRivals.lane(4, 0)] })
        let out = Events.refresh(&s, now: t + 900, rivals: fast, me: me, rules: r)
        XCTAssertEqual(out.filter { if case .rocketFinished = $0 { return true } else { return false } }, [.rocketFinished(rank: 3, reward: nil)])
        XCTAssertEqual(s.events.rocket.lastResult, .lost)
        XCTAssertEqual(s.events.rocket.lastRun, RocketRun(instance: race.instance, joinedAt: race.joinedAt, stage: 1, progress: 2))
        XCTAssertEqual(s.events.rocket.lastEndedAt, social(t + 900))
        var back = try relaunch(s)
        XCTAssertEqual(back, s)
        XCTAssertEqual(try finalLanes(back, fast).map(\.score), [2, 5, 3, 1, 0])

        // re-join; the race is still running when the event day ends → expired, judged at most at the window's end
        guard case .success(let r2) = Events.joinRocketRace(&back, now: t + 1000, rules: r) else { return XCTFail("join 2") }
        XCTAssertNil(back.events.rocket.lastRun)
        let late = Date(timeIntervalSince1970: Double(r2.instance.end.seconds) + 7200)
        _ = Events.refresh(&back, now: late, rivals: Self.slowRivals, me: me, rules: r)
        XCTAssertEqual(back.events.rocket.lastResult, .expired)
        XCTAssertEqual(back.events.rocket.lastRun?.instance, r2.instance)
        XCTAssertEqual(back.events.rocket.lastRun?.progress, 0)
        XCTAssertEqual(back.events.rocket.lastEndedAt, r2.instance.end, "capped at the window's end, not the late refresh")
        XCTAssertEqual(try relaunch(back), back)
    }

    /// SOC1's real world as the rivals: whatever the race's outcome, the lanes rebuilt from the saved run after a relaunch
    /// equal the lanes before it.
    func testTheRealWorldRebuildsTheSameFinalLanesAfterARelaunch() throws {
        let world = SocialWorld(installSeed: 42, config: .default, names: SocFix.bankV2)   // PUBLISH B2: the shipped (v2) world + its names
        var s = C3.fresh()
        s.level = 55
        let t = C3.utc("2026-09-25T08:00:00Z")
        guard case .success = Events.joinRocketRace(&s, now: t, rules: r) else { return XCTFail("join") }
        var k = 0
        while s.events.rocket.active != nil, k < 10 {
            k += 1
            _ = win(&s, 54 + k, at: t + Double(900 * k), rivals: world)
        }
        let result = try XCTUnwrap(s.events.rocket.lastResult, "the race ended (won or lost) within 10 wins")
        XCTAssertTrue([.won, .lost].contains(result))
        let back = try relaunch(s)
        XCTAssertEqual(back.events.rocket, s.events.rocket)
        let lanes = try finalLanes(back, world)
        XCTAssertEqual(lanes, try finalLanes(s, world))
        XCTAssertEqual(lanes.count, 5)
        XCTAssertEqual(lanes.first?.score, back.events.rocket.lastRun?.progress)
    }

    // MARK: Sky Jump

    func testAWonAndAFailedSkyJumpRunKeepTheirRuns() throws {
        var s = C3.fresh()
        s.level = 40
        let t = C3.utc("2026-09-25T08:00:00Z")
        let rivals = StubRivals(sky: { run, _ in SkyJumpField(total: 100, left: 12, winners: run.stage == 1 ? 7 : 3) })
        guard case .success(let run) = Events.joinSkyJump(&s, now: t, rules: r) else { return XCTFail("join") }
        XCTAssertNil(s.events.sky.lastRun)
        for k in 0..<5 { _ = win(&s, 40 + k, at: t + Double(60 * (k + 1)), rivals: rivals) }
        XCTAssertEqual(s.events.sky.lastResult, .won)
        XCTAssertEqual(s.events.sky.lastRun, SkyJumpRun(instance: run.instance, joinedAt: run.joinedAt, stage: 1, progress: 5))
        XCTAssertEqual(s.events.sky.lastEndedAt, social(t + 300))
        var back = try relaunch(s)
        XCTAssertEqual(back, s)
        XCTAssertEqual(back.events.sky.lastRun, s.events.sky.lastRun)

        // stage 2: one first-try win, then a failed attempt fails the run (its progress is kept as it stood)
        guard case .success(let run2) = Events.joinSkyJump(&back, now: t + 600, rules: r) else { return XCTFail("join 2") }
        XCTAssertEqual(run2.stage, 2)
        XCTAssertNil(back.events.sky.lastRun, "a new run clears the old result")
        _ = win(&back, 45, at: t + 660, rivals: rivals)
        _ = lose(&back, 46, at: t + 720)
        XCTAssertEqual(back.events.sky.lastResult, .failed)
        XCTAssertEqual(back.events.sky.lastRun, SkyJumpRun(instance: run2.instance, joinedAt: run2.joinedAt, stage: 2, progress: 1))
        XCTAssertEqual(back.events.sky.lastEndedAt, social(t + 720))
        XCTAssertEqual(try relaunch(back), back)
    }

    func testAnExpiredSkyJumpRunIsJudgedAtItsWindowsEnd() throws {
        var s = C3.fresh()
        s.level = 40
        let t = C3.utc("2026-09-25T08:00:00Z")
        let rivals = StubRivals()
        guard case .success(let run) = Events.joinSkyJump(&s, now: t, rules: r) else { return XCTFail("join") }
        _ = win(&s, 40, at: t + 60, rivals: rivals)
        _ = Events.refresh(&s, now: t + 86_400 + 5000, rivals: rivals, me: me, rules: r)
        XCTAssertEqual(s.events.sky.lastResult, .expired)
        XCTAssertEqual(s.events.sky.lastRun?.progress, 1)
        XCTAssertEqual(s.events.sky.lastEndedAt, run.instance.end)
        XCTAssertEqual(try relaunch(s), s)
    }

    // MARK: a clock rebase (CORE-2, INTEG review: Events.rebase ends runs like every other end)

    /// SPEC-social §5: a device clock > 30 days in the future, once repaired, rebases the world clock; the Rocket Race and
    /// the Sky Jump run joined in the abandoned future end `.expired` and are KEPT like every other end — `lastRun` as it
    /// stood, `lastEndedAt` = the abandoned clock's last moment (the run's own timeline: after its join, within its window)
    /// — so the result pages still draw the final lanes, also after a relaunch.
    func testARebaseKeepsTheRunsItEnds() throws {
        var s = C3.fresh()
        s.level = 60
        let future = C3.utc("2026-11-20T12:00:00Z")                        // the device clock ~8 weeks ahead
        guard case .success(let race) = Events.joinRocketRace(&s, now: future, rules: r) else { return XCTFail("rocket join") }
        guard case .success(let run) = Events.joinSkyJump(&s, now: future, rules: r) else { return XCTFail("sky join") }
        _ = win(&s, 60, at: future + 60, rivals: Self.slowRivals)
        _ = win(&s, 61, at: future + 120, rivals: Self.slowRivals)
        _ = Events.refresh(&s, now: future + 600, rivals: Self.slowRivals, me: me, rules: r)   // the old clock's last visit
        XCTAssertEqual(s.events.rocket.active?.progress, 2)
        XCTAssertEqual(s.events.sky.active?.progress, 2)
        let last = social(future + 600)
        XCTAssertEqual(s.social.highWater, last.seconds)
        XCTAssertLessThan(last, race.instance.end, "the race was still running at the old clock's last moment")
        XCTAssertLessThan(last, run.instance.end)

        let repaired = C3.utc("2026-09-25T12:00:00Z")
        _ = Economy.reconcileOnLaunch(&s, now: repaired, rules: r)            // SOC1's clock rebases (> 30 days behind)
        XCTAssertEqual(s.social.highWater, social(repaired).seconds, "rebased")

        XCTAssertNil(s.events.rocket.active, "a race stamped in the abandoned future ends")
        XCTAssertEqual(s.events.rocket.lastResult, .expired)
        XCTAssertEqual(s.events.rocket.lastRun, RocketRun(instance: race.instance, joinedAt: race.joinedAt, stage: 1, progress: 2),
                       "kept as it stood: its window, join time and the player's lane")
        XCTAssertEqual(s.events.rocket.lastEndedAt, last, "judged at the abandoned clock's last moment, not the rebased now")
        XCTAssertNil(s.events.sky.active)
        XCTAssertEqual(s.events.sky.lastResult, .expired)
        XCTAssertEqual(s.events.sky.lastRun, SkyJumpRun(instance: run.instance, joinedAt: run.joinedAt, stage: 1, progress: 2))
        XCTAssertEqual(s.events.sky.lastEndedAt, last)
        for (ended, joined, end) in [(s.events.rocket.lastEndedAt, race.joinedAt, race.instance.end),
                                     (s.events.sky.lastEndedAt, run.joinedAt, run.instance.end)] {
            let e = try XCTUnwrap(ended)
            XCTAssertTrue(joined <= e && e <= end, "within the run's own window: \(e)")
        }
        XCTAssertEqual(s.events.rocket.raceCounter, race.instance.index, "the result page's run (SOC2 matches on the counter)")
        XCTAssertEqual(s.events.sky.attemptCounter, run.instance.index)

        let back = try relaunch(s)
        XCTAssertEqual(back, s)
        XCTAssertEqual(try finalLanes(back, Self.slowRivals).map(\.score), [2, 4, 3, 2, 2],
                       "the lanes as they stood 10 min after the join (slowRivals: min(4, minutes / (k + 1)))")
        XCTAssertEqual(try finalLanes(back, Self.slowRivals), try finalLanes(s, Self.slowRivals))
        // the next race, joined on the repaired clock, starts clean
        var again = back
        guard case .success = Events.joinRocketRace(&again, now: repaired + 60, rules: r) else { return XCTFail("re-join") }
        XCTAssertNil(again.events.rocket.lastRun)
        XCTAssertNil(again.events.rocket.lastEndedAt)
    }

    // MARK: old saves

    func testASaveFromBeforeTheFieldsDecodesThemAsNil() throws {
        // a state with an ended race and run, as this build saves it …
        var s = C3.fresh()
        s.level = 55
        let t = C3.utc("2026-09-25T08:00:00Z")
        guard case .success = Events.joinRocketRace(&s, now: t, rules: r) else { return XCTFail("join") }
        for k in 0..<5 { _ = win(&s, 55 + k, at: t + Double(60 * (k + 1)), rivals: Self.slowRivals) }
        guard case .success = Events.joinSkyJump(&s, now: t + 600, rules: r) else { return XCTFail("sky join") }
        _ = lose(&s, 60, at: t + 700)
        XCTAssertNotNil(s.events.rocket.lastRun)
        XCTAssertNotNil(s.events.sky.lastRun)
        // … written by the previous build: the same JSON without the two keys
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: StateStore.encode(s)) as? [String: Any])
        var events = try XCTUnwrap(json["events"] as? [String: Any])
        for key in ["rocket", "sky"] {
            var sub = try XCTUnwrap(events[key] as? [String: Any])
            XCTAssertNotNil(sub.removeValue(forKey: "lastRun"))
            XCTAssertNotNil(sub.removeValue(forKey: "lastEndedAt"))
            events[key] = sub
        }
        json["events"] = events
        let old = try StateStore.decode(JSONSerialization.data(withJSONObject: json))
        XCTAssertNil(old.events.rocket.lastRun)
        XCTAssertNil(old.events.rocket.lastEndedAt)
        XCTAssertNil(old.events.sky.lastRun)
        XCTAssertNil(old.events.sky.lastEndedAt)
        var expected = s
        expected.events.rocket.lastRun = nil
        expected.events.rocket.lastEndedAt = nil
        expected.events.sky.lastRun = nil
        expected.events.sky.lastEndedAt = nil
        XCTAssertEqual(old, expected, "every other field decodes as saved")
        XCTAssertEqual(old.events.rocket.lastResult, .won)
        XCTAssertEqual(old.events.sky.lastResult, .failed)

        // the sub-states from the previous build's literal keys
        let d = StateStore.decoder()
        let rocket = try d.decode(RocketState.self, from: Data(#"{"raceCounter":4,"nextStage":2,"lastResult":"lost","day":150}"#.utf8))
        XCTAssertEqual([rocket.raceCounter, rocket.nextStage, rocket.day], [4, 2, 150])
        XCTAssertEqual(rocket.lastResult, .lost)
        XCTAssertNil(rocket.lastRun)
        XCTAssertNil(rocket.lastEndedAt)
        let sky = try d.decode(SkyJumpState.self, from: Data(#"{"attemptCounter":3,"runsToday":1,"lastResult":"won"}"#.utf8))
        XCTAssertEqual([sky.attemptCounter, sky.runsToday], [3, 1])
        XCTAssertNil(sky.lastRun)
        XCTAssertNil(sky.lastEndedAt)
        // the frozen v1 fixture ("events": {})
        let v1 = try StateStore.decode(Data(contentsOf: C3.fixture("wp0_player_v1.json")))
        XCTAssertNil(v1.events.rocket.lastRun)
        XCTAssertNil(v1.events.sky.lastRun)
    }

    func testAStateWithoutAnEndedRunSavesNoNewKeys() throws {
        // existing saves re-encode byte-identically: nil optionals are left out, like every other optional field
        var s = C3.fresh()
        s.level = 55
        guard case .success = Events.joinRocketRace(&s, now: C3.utc("2026-09-25T08:00:00Z"), rules: r) else { return XCTFail("join") }
        let text = String(decoding: try StateStore.encode(s), as: UTF8.self)
        XCTAssertFalse(text.contains("lastRun"), text)
        XCTAssertFalse(text.contains("lastEndedAt"), text)
    }
}
