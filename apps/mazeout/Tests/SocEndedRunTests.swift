import XCTest
import PathCore
@testable import ArrowOut

/// FIX-A2 (the INTEG review's low: "EventsEndedRunTests use their own finalLanes, not SocCompute"). The app's own result-page
/// data path — `SocCompute.rocket` / `SocCompute.sky`, what the Rocket Race and Sky Jump pages draw — for an ENDED run, on the
/// real SocialWorld and the bundled rules:
///  - it is drawn from C3's persisted `EventsState.lastRun` at `lastEndedAt`: the page shows the same final lanes whenever it is
///    opened later (hours later, the next day) as at the end moment itself, and the rivals' lanes are the world's at
///    `lastEndedAt` (independently recomputed here);
///  - after a relaunch (the app's real save path: PlayerStore writes player.json, a new PlayerStore reads it) it is the same;
///  - after a clock rebase (a device clock far in the future, then repaired: C3 ends the runs `.expired` and keeps them with
///    `lastEndedAt` = the abandoned clock's last moment) the page draws that moment — not the repaired clock's `now`, which lies
///    BEFORE the race's join (CORE-2's request; SocCompute now uses `lastEndedAt` alone for an ended run). This is also the
///    expired case: a race left to its window's end is always lost first on the real world (its rivals finish within minutes;
///    measured while writing this suite), so C3's window-end expiry is covered by PathCore's EventsEndedRunTests.
@MainActor final class SocEndedRunTests: XCTestCase {
    private let tuning = Tuning.load(bundle: .main)
    private lazy var rules = ShellEconomy.rules(tuning)
    private lazy var names: NameBank = {
        (try? NameBank.load(folder: Bundle.main.resourceURL!.appendingPathComponent("Social"))) ?? NameBank()
    }()
    /// 25 Sep 2026 12:00 UTC (the capture clock).
    private let t0 = Date(timeIntervalSince1970: 1_790_337_600)

    private func world() -> SocialWorld { SocialWorld(installSeed: 1, config: tuning.social.config, names: names) }

    private func state(level: Int) -> PlayerState {
        var s = PlayerState()
        s.installSeed = 1
        s.level = level
        s.homeSeen = true
        s.social.country = "TR"
        return s
    }

    /// What SocialModel hands SocCompute when a page opens at wall time `date` (the rewind-safe world clock).
    private func inputs(_ w: SocialWorld, _ s: PlayerState, at date: Date) -> SocInputs {
        inputs(w, s, now: EconomyClock.peekSocial(s, wall: date))
    }

    private func inputs(_ w: SocialWorld, _ s: PlayerState, now: SocialTime) -> SocInputs {
        SocInputs(world: w, state: s, now: now, me: s.social.standing(installSeed: s.installSeed, level: s.level),
                  config: tuning.social.config, rules: rules, scale: 3, captionLevel: "Level", captionScore: "Score")
    }

    private func date(_ t: SocialTime) -> Date { Date(timeIntervalSince1970: Double(t.seconds)) }

    /// The app's relaunch: the state saved by one PlayerStore (player.json) and read back by a new one.
    private func relaunch(_ s: PlayerState) throws -> PlayerState {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("socended-\(UUID().uuidString)")
        defer { try? FileManager.default.removeItem(at: dir) }
        let args = LaunchArgs(pairs: [:])
        let first = PlayerStore(args: args, now: t0, bundle: .main, directory: dir, rules: rules, debounce: 0.05)
        first.mutateAndSave { $0 = s }
        first.flush()
        let second = PlayerStore(args: args, now: t0, bundle: .main, directory: dir, rules: rules, debounce: 0.05)
        XCTAssertEqual(second.loadSource, .primary, "read back from player.json")
        return second.state
    }

    private func lanes(_ snap: SocRocketSnap?) -> [String] {
        (snap?.lanes ?? []).map { "\($0.isMe ? "me" : "\($0.player.id)")|\($0.progress)|#\($0.rank)" }
    }

    private func sky(_ snap: SocSkySnap?) -> String {
        guard let s = snap else { return "nil" }
        return "\(s.attemptId) st\(s.stage) \(s.progress)/\(s.goal) alive \(s.alive) pool \(s.pool) share \(s.share) \(s.result) "
            + s.shown.map { "\($0.id)" }.joined(separator: ",")
    }

    /// The result page of an ended race, opened at the end moment, hours later, the next day and after a relaunch: one set
    /// of final lanes, C3's result; returns the lanes.
    @discardableResult
    private func assertRocketDrawnAtItsEnd(_ s: PlayerState, _ w: SocialWorld, _ what: String,
                                           file: StaticString = #filePath, line: UInt = #line) throws -> [String] {
        let rs = s.events.rocket
        let run = try XCTUnwrap(rs.lastRun, "\(what): C3 kept the ended race", file: file, line: line)
        let ended = try XCTUnwrap(rs.lastEndedAt, file: file, line: line)
        let result = try XCTUnwrap(rs.lastResult, file: file, line: line)
        XCTAssertNil(rs.active, file: file, line: line)
        let atEnd = SocCompute.rocket(inputs(w, s, now: ended)).0
        let snap = try XCTUnwrap(atEnd, "\(what): the page has data at the end moment", file: file, line: line)
        XCTAssertEqual(snap.result, result.rawValue, "\(what): C3's result", file: file, line: line)
        XCTAssertEqual(snap.raceId, run.instance.index, file: file, line: line)
        XCTAssertEqual(snap.lanes.count, 5, "the player + 4 rivals", file: file, line: line)
        let goal = rules.events.rocketRace.levels(stage: run.stage)
        XCTAssertEqual(snap.lanes.first?.isMe, true, file: file, line: line)
        XCTAssertEqual(snap.lanes.first?.progress, result == .won ? goal : min(run.progress, goal),
                       "\(what): the player's final lane from lastRun", file: file, line: line)
        let reference = lanes(atEnd)
        for later in [date(ended) + 3 * 3600, date(ended) + 20 * 3600] {
            XCTAssertEqual(lanes(SocCompute.rocket(inputs(w, s, at: later)).0), reference,
                           "\(what): opened \(Int(later.timeIntervalSince(date(ended)) / 3600)) h later", file: file, line: line)
        }
        let back = try relaunch(s)
        XCTAssertEqual(back.events.rocket, s.events.rocket, "\(what): the ended race survives the save", file: file, line: line)
        XCTAssertEqual(lanes(SocCompute.rocket(inputs(w, back, at: date(ended) + 5 * 3600)).0), reference,
                       "\(what): after a relaunch", file: file, line: line)
        return reference
    }

    // MARK: Rocket Race

    func testAWonRocketRaceIsDrawnAtItsWinAndAfterARelaunch() throws {
        let w = world()
        var s = state(level: 55)
        let join = t0.addingTimeInterval(-3 * 3600)
        guard case .success(let race) = Events.joinRocketRace(&s, now: join, rules: rules) else { return XCTFail("join") }
        let goal = rules.events.rocketRace.levels(stage: race.stage)
        for k in 0..<goal {                                                   // a win a minute: faster than any rival
            let lv = s.level
            _ = Events.onWin(&s, WinContext(levels: [lv], tag: .normal, firstTry: true, now: join.addingTimeInterval(Double(60 * (k + 1)))),
                             rivals: w, rules: rules)
            s.level = lv + 1
        }
        XCTAssertEqual(s.events.rocket.lastResult, .won)
        let ended = try XCTUnwrap(s.events.rocket.lastEndedAt)
        XCTAssertEqual(ended.seconds, Int64(join.addingTimeInterval(Double(60 * goal)).timeIntervalSince1970), "the last win")
        _ = Events.refresh(&s, now: t0, rivals: w, me: s.social.standing(installSeed: 1, level: s.level), rules: rules)
        try assertRocketDrawnAtItsEnd(s, w, "won")
        // the rivals are the world's lanes AT the win (independently recomputed), not at the page's `now`
        let snap = try XCTUnwrap(SocCompute.rocket(inputs(w, s, at: t0)).0)
        let atWin = w.rocketRace(race.instance, joinedAt: race.joinedAt, at: ended).filter { !$0.isMe }
        XCTAssertEqual(snap.lanes.dropFirst().map { "\($0.player.id)|\($0.progress)" },
                       atWin.map { "\($0.player.id)|\(min($0.score, goal))" })
        let now = w.rocketRace(race.instance, joinedAt: race.joinedAt, at: SocialTime(seconds: Int64(t0.timeIntervalSince1970)))
        XCTAssertNotEqual(now.filter { !$0.isMe }.map(\.score), atWin.map(\.score),
                          "precondition: the world's lanes moved on after the win (else this test could not tell the moments apart)")
    }

    func testALostRocketRaceIsDrawnAtItsEndAndAfterARelaunch() throws {
        let w = world()
        var s = try XCTUnwrap(SocScenario.build("rocketLost", from: state(level: 62), wall: t0, world: w, rules: rules))
        XCTAssertNotNil(s.events.rocket.active)
        _ = Events.refresh(&s, now: t0, rivals: w, me: s.social.standing(installSeed: 1, level: s.level), rules: rules)
        XCTAssertEqual(s.events.rocket.lastResult, .lost, "the scenario's rivals finished: lost at the refresh")
        let reference = try assertRocketDrawnAtItsEnd(s, w, "lost")
        XCTAssertTrue(reference.contains { $0.hasSuffix("|#1") && !$0.hasPrefix("me") }, "a rival leads: \(reference)")
    }

    // MARK: Sky Jump

    func testAWonAndAFailedSkyJumpRunAreDrawnFromTheirSavedRun() throws {
        let w = world()
        for (name, result) in [("skyWin", EventRunResult.won), ("skyFail", .failed)] {
            var s = try XCTUnwrap(SocScenario.build(name, from: state(level: 45), wall: t0, world: w, rules: rules), name)
            XCTAssertEqual(s.events.sky.lastResult, result, name)
            let run = try XCTUnwrap(s.events.sky.lastRun, name)
            let ended = try XCTUnwrap(s.events.sky.lastEndedAt, name)
            let atEnd = try XCTUnwrap(SocCompute.sky(inputs(w, s, now: ended)).0, name)
            XCTAssertEqual(atEnd.result, result.rawValue, name)
            XCTAssertEqual(atEnd.attemptId, run.instance.index, name)
            XCTAssertEqual(atEnd.progress, result == .won ? atEnd.goal : run.progress, "\(name): the final progress from lastRun")
            let field = w.skyJump(SkyJumpRun(instance: run.instance, joinedAt: run.joinedAt, stage: run.stage,
                                             progress: min(atEnd.progress, atEnd.goal)), at: ended)
            XCTAssertEqual(atEnd.shown.map(\.id), field.shown.map(\.id), "\(name): the world's field of that attempt")
            let reference = sky(atEnd)
            _ = Events.refresh(&s, now: t0.addingTimeInterval(3 * 3600), rivals: w, me: s.social.standing(installSeed: 1, level: s.level),
                               rules: rules)
            XCTAssertEqual(s.events.sky.lastRun, run, "\(name): a later refresh keeps the ended run")
            for later in [date(ended) + 3 * 3600, date(ended) + 20 * 3600] {
                XCTAssertEqual(sky(SocCompute.sky(inputs(w, s, at: later)).0), reference, "\(name): opened later")
            }
            let back = try relaunch(s)
            XCTAssertEqual(back.events.sky, s.events.sky, "\(name): survives the save")
            XCTAssertEqual(sky(SocCompute.sky(inputs(w, back, at: date(ended) + 5 * 3600)).0), reference, "\(name): after a relaunch")
        }
    }

    // MARK: a clock rebase (CORE-2's request)

    func testRunsEndedByAClockRebaseAreDrawnAtTheOldClocksLastMoment() throws {
        let w = world()
        var s = state(level: 60)
        // B1 re-pin (requirement change, SPEC.md ruling 38: the featured events rotate weekly; the same assertions): 20 Nov
        // (week 29 = Up & Away + Rocket Rally, no Cloud Hop) → 12 Nov (week 28 = Treasure Climb + Double Event Week), where
        // both runs this test joins are live — still > 30 days ahead of t0 (the rebase below)
        let future = Date(timeIntervalSince1970: 1_794_484_800)             // 12 Nov 2026 12:00 UTC: the device clock ~7 weeks ahead
        guard case .success(let race) = Events.joinRocketRace(&s, now: future, rules: rules) else { return XCTFail("rocket join") }
        guard case .success(let run) = Events.joinSkyJump(&s, now: future, rules: rules) else { return XCTFail("sky join") }
        for k in 0..<2 {
            let lv = s.level
            _ = Events.onWin(&s, WinContext(levels: [lv], tag: .normal, firstTry: true, now: future.addingTimeInterval(Double(20 * (k + 1)))),
                             rivals: w, rules: rules)
            s.level = lv + 1
        }
        // the old clock's last visit: the first whole minute at which the world's rivals have moved but none has finished
        // (so the race still runs then, and its lanes differ from the lanes before the join)
        let goal = rules.events.rocketRace.levels(stage: race.stage)
        let minute = try XCTUnwrap((1...30).first { m in
            let scores = w.rocketRace(race.instance, joinedAt: race.joinedAt,
                                      at: SocialTime(seconds: race.joinedAt.seconds + Int64(60 * m))).map(\.score)
            return scores.reduce(0, +) > 0 && (scores.max() ?? 0) < goal
        }, "a moment with the rivals under way")
        let lastVisit = future.addingTimeInterval(Double(60 * minute))
        _ = Events.refresh(&s, now: lastVisit, rivals: w, me: s.social.standing(installSeed: 1, level: s.level), rules: rules)
        XCTAssertEqual(s.events.rocket.active?.progress, 2, "precondition: the race still runs at the old clock's last visit")
        XCTAssertEqual(s.events.sky.active?.progress, 2)

        _ = Economy.reconcileOnLaunch(&s, now: t0, rules: rules)            // the repaired clock (> 30 days behind): a rebase
        XCTAssertEqual(s.events.rocket.lastResult, .expired)
        XCTAssertEqual(s.events.sky.lastResult, .expired)
        let ended = try XCTUnwrap(s.events.rocket.lastEndedAt)
        XCTAssertEqual(ended.seconds, Int64(lastVisit.timeIntervalSince1970), "C3: the abandoned clock's last moment")
        XCTAssertGreaterThan(ended, race.joinedAt)
        let now = EconomyClock.peekSocial(s, wall: t0)
        XCTAssertLessThan(now, race.joinedAt, "the repaired clock's now lies before the join")

        // Rocket Race: the lanes as they stood at the old clock's last moment
        let snap = try XCTUnwrap(SocCompute.rocket(inputs(w, s, at: t0)).0)
        XCTAssertEqual(snap.result, "expired")
        XCTAssertEqual(snap.lanes.first?.progress, 2, "the player's lane from lastRun")
        let atEnd = w.rocketRace(race.instance, joinedAt: race.joinedAt, at: ended).filter { !$0.isMe }
        XCTAssertEqual(snap.lanes.dropFirst().map { "\($0.player.id)|\($0.progress)" }, atEnd.map { "\($0.player.id)|\(min($0.score, goal))" },
                       "the world's rivals at lastEndedAt")
        XCTAssertGreaterThan(atEnd.map(\.score).reduce(0, +), 0,
                             "precondition: the rivals had moved by then (at the repaired `now`, before the join, they had not)")
        let back = try relaunch(s)
        XCTAssertEqual(lanes(SocCompute.rocket(inputs(w, back, at: t0.addingTimeInterval(600))).0), lanes(snap), "after a relaunch")

        // Sky Jump: the kept run
        let skySnap = try XCTUnwrap(SocCompute.sky(inputs(w, s, at: t0)).0)
        XCTAssertEqual(skySnap.result, "expired")
        XCTAssertEqual(skySnap.attemptId, run.instance.index)
        XCTAssertEqual(skySnap.progress, 2)
        XCTAssertEqual(sky(SocCompute.sky(inputs(w, back, at: t0)).0), sky(skySnap), "after a relaunch")
    }
}
