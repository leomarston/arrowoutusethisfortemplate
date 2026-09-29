import XCTest
import Foundation
@testable import PathCore

/// SPEC-architecture §4.17 "PersistenceTests" (C3; §4.12): round trip; atomic write + backup; corrupt → backup (kept once
/// aside, never rotated into the backup); the frozen v1 fixture decodes forever; additive fields decode from old JSON;
/// migrations; the rewind-safe clock's high-water mark survives a relaunch.
final class PersistenceTests: XCTestCase {
    var dir: URL!

    override func setUpWithError() throws {
        dir = FileManager.default.temporaryDirectory.appendingPathComponent("c3-store-\(UUID().uuidString)", isDirectory: true)
    }

    override func tearDownWithError() throws { try? FileManager.default.removeItem(at: dir) }

    var store: StateStore { StateStore(url: dir.appendingPathComponent("Save/player.json")) }

    /// A state with every part filled (economy, attempt, events, social, settings).
    func rich() -> PlayerState {
        var s = C3.fresh()
        let t = Date(timeIntervalSince1970: 1_790_328_600.125)
        s.level = 57
        s.homeSeen = true
        s.coins = 4014
        s.pendingCoinFly = 20
        s.lives = LivesState(count: 3, anchor: t.addingTimeInterval(-600.5))
        s.unlimitedLivesUntil = t.addingTimeInterval(4200)
        s.unlocksSeen = ["linked", "box", "pipe", "elevator", "door"]
        s.tutorialsDone = ["tapToMove"]
        s.attempts = [1: 1, 47: 2, 52: 2, 57: 1]
        s.activeAttempt = ActiveAttempt(session: "L57", levels: [57], attemptIndex: 1, startedAt: t, stage: 0)
        s.stats = PlayerState.Stats(wins: 56, losses: 4, firstTryWins: 52, weeklyContestWins: 1, playSeconds: 12_345.25)
        s.settings = PlayerState.Settings(sound: true, music: false, haptic: true, notifications: false, trail: "rainbow")
        s.flags.seen = ["clawIntro", "bought:offer.special"]
        s.social.username = "Hsheh"
        s.social.highWater = 1_790_328_600
        s.social.ledger = [LedgerEntry(at: SocialTime(seconds: 1_790_328_000), level: 56, score: 100)]
        s.processedTransactions = ["2000000000000001"]
        s.events.streakStep = 4
        s.events.claw = ClawState(week: 21, points: 222, step: 6)
        s.events.streakRace = ContestState(index: 150, joinedAt: SocialTime(seconds: 1_790_300_000), score: 1824,
                                           lastScoreAt: SocialTime(seconds: 1_790_328_000))
        s.events.weekly = ContestState(index: 21, joinedAt: SocialTime(seconds: 1_790_310_000), score: 8, lastScoreAt: nil)
        let inst = EventInstance(event: .rocketRace, index: 3, start: SocialTime(seconds: 1_790_320_000),
                                 end: SocialTime(seconds: 1_790_319_600 + 86_400))
        s.events.rocket.active = RocketRun(instance: inst, joinedAt: inst.start, stage: 1, progress: 3)
        s.events.rocket.raceCounter = 3
        s.events.rocket.joinGrantDay = 150
        s.events.sky.lastResult = .won
        s.events.sky.nextStage = 2
        s.events.claims = [EventClaim(id: 7, event: .clawChallenge, kind: .clawStep, grant: .booster(.hint, 1), value: 6,
                                      index: 21, at: SocialTime(seconds: 1_790_328_000))]
        s.events.nextClaimID = 8
        s.events.toSettle = [ContestResult(event: .streakRace, index: 149, score: 900, joinedAt: nil, lastScoreAt: nil)]
        s.events.wins = ["skyJump": 1]
        s.events.attemptFree = true
        return s
    }

    // MARK: round trip, sorted keys, exact dates

    func testRoundTripIsExact() throws {
        let s = rich()
        let st = store
        try st.save(s)
        let back = st.load()
        XCTAssertEqual(back.source, .primary)
        XCTAssertNil(back.problem)
        XCTAssertEqual(back.state, s)
        XCTAssertEqual(back.state.lives.anchor, s.lives.anchor, "fractional seconds survive (no refill drift per relaunch)")
        let text = String(decoding: try Data(contentsOf: st.url), as: UTF8.self)
        XCTAssertTrue(text.contains("\"anchor\" : \"2026-09-25T09:19:59.625Z\""), text)
        XCTAssertEqual(try StateStore.decode(StateStore.encode(StateStore.decode(StateStore.encode(s)))), s)
        let keys = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: st.url)) as? [String: Any]).keys.sorted()
        let firstKeys = text.split(separator: "\n").filter { $0.hasPrefix("  \"") }.map { $0.split(separator: "\"")[1] }.map(String.init)
        XCTAssertEqual(firstKeys, keys, "sorted keys")
        for d in [Date(timeIntervalSince1970: 0), Date(timeIntervalSince1970: 1_790_328_600.000_001),
                  Date(timeIntervalSinceReferenceDate: 812_000_000.123_456_789)] {
            XCTAssertEqual(ISODate.date(ISODate.string(d)), d)
        }
        XCTAssertEqual(Array(StateStore.defaultURL().pathComponents.suffix(3)), ["Application Support", "Save", "player.json"])
    }

    // MARK: atomic write + backup

    func testEverySaveKeepsThePreviousGoodFileAsTheBackup() throws {
        let st = store
        var a = C3.fresh(); a.coins = 1
        var b = a; b.coins = 2
        var c = a; c.coins = 3
        try st.save(a)
        XCTAssertFalse(FileManager.default.fileExists(atPath: st.backupURL.path), "nothing to back up on the first save")
        try st.save(b)
        XCTAssertEqual(try StateStore.decode(Data(contentsOf: st.backupURL)).coins, 1)
        try st.save(c)
        XCTAssertEqual(try StateStore.decode(Data(contentsOf: st.backupURL)).coins, 2)
        XCTAssertEqual(try StateStore.decode(Data(contentsOf: st.url)).coins, 3)
        let leftovers = try FileManager.default.contentsOfDirectory(atPath: st.url.deletingLastPathComponent().path)
        XCTAssertEqual(leftovers.sorted(), ["player.json", "player.prev.json"], "no temp files left behind")
        // a second store on the same folder (a relaunch) rotates the same way
        let again = StateStore(url: st.url)
        var d = a; d.coins = 4
        try again.save(d)
        XCTAssertEqual(try StateStore.decode(Data(contentsOf: again.backupURL)).coins, 3)
    }

    // MARK: corrupt → backup

    func testACorruptSaveLoadsTheBackupAndIsKeptAside() throws {
        let st = store
        var a = C3.fresh(); a.coins = 111
        var b = a; b.coins = 222
        try st.save(a)
        try st.save(b)                                                  // prev = 111, primary = 222
        let junk = Data("{\"coins\": \"lots\", \"version\": 1".utf8)
        try junk.write(to: st.url)
        let fresh = StateStore(url: st.url)
        let r = fresh.load()
        XCTAssertEqual(r.source, .backup)
        XCTAssertEqual(r.state.coins, 111)
        XCTAssertNotNil(r.problem)
        XCTAssertEqual(try Data(contentsOf: fresh.corruptURL), junk, "kept once aside for diagnosis")
        // the next save must NOT rotate the corrupt primary into the backup
        var c = r.state; c.coins = 333
        try fresh.save(c)
        XCTAssertEqual(try StateStore.decode(Data(contentsOf: fresh.backupURL)).coins, 111)
        XCTAssertEqual(fresh.load().state.coins, 333)
        // a wrong TYPE is corrupt too (never silently reset to a default)
        try Data("{\"version\":1,\"lives\":{\"count\":\"five\"}}".utf8).write(to: st.url)
        XCTAssertEqual(StateStore(url: st.url).load().source, .backup)
    }

    func testCorruptWithoutABackupStartsFreshAndNeverCrashes() throws {
        let st = store
        try FileManager.default.createDirectory(at: st.url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data([0xFF, 0x00, 0x7B]).write(to: st.url)
        let r = st.load()
        XCTAssertEqual(r.source, .fresh)
        XCTAssertEqual(r.state, PlayerState())
        XCTAssertNotNil(r.problem)
        try Data("[]".utf8).write(to: st.backupURL)
        XCTAssertEqual(StateStore(url: st.url).load().source, .fresh)
        XCTAssertEqual(StateStore(url: dir.appendingPathComponent("nothing/player.json")).load().source, .fresh)
        st.wipe()
        for u in [st.url, st.backupURL, st.corruptURL] { XCTAssertFalse(FileManager.default.fileExists(atPath: u.path)) }
    }

    // MARK: schema evolution

    func testTheFrozenV1FixtureDecodesForever() throws {
        let data = try Data(contentsOf: C3.fixture("wp0_player_v1.json"))
        let s = try StateStore.decode(data)
        XCTAssertEqual(s.version, 1)
        XCTAssertEqual(s.installSeed, 42)
        XCTAssertEqual(s.level, 32)
        XCTAssertEqual(s.coins, 1340)
        XCTAssertEqual(s.lives, LivesState(count: 4, anchor: C3.utc("2026-09-25T09:20:00.000Z")))
        XCTAssertEqual(s.unlimitedLivesUntil, C3.utc("2026-09-25T10:00:00.000Z"))
        XCTAssertEqual(s.activeAttempt?.startedAt, C3.utc("2026-09-25T09:31:00.000Z"))
        XCTAssertEqual(s.social.highWater, 1_790_328_600)
        XCTAssertEqual(s.events, EventsState(), "\"events\": {} → every C3 field at its default")
        XCTAssertEqual(try StateStore.decode(StateStore.encode(s)), s)
        // the economy runs on it: a relaunch applies the kill rule to the saved attempt
        var t = s
        let n = Economy.reconcileOnLaunch(&t, now: C3.utc("2026-09-25T09:40:00Z"), rules: C3.rules)
        XCTAssertEqual(n.last, .killedAttempt(levels: [32], countedAsLoss: true, outcomes: []))
        XCTAssertEqual(t.lives.count, 4)
    }

    func testAdditiveFieldsDecodeFromOldJSON() throws {
        // an old save that knows only part of the events (and nothing of later fields) decodes with defaults
        let old = #"{"version":1,"coins":5,"events":{"streakStep":3,"claw":{"points":40}},"social":{"highWater":7}}"#
        let s = try StateStore.decode(Data(old.utf8))
        XCTAssertEqual(s.coins, 5)
        XCTAssertEqual(s.events.streakStep, 3)
        XCTAssertEqual(s.events.claw, ClawState(week: nil, points: 40, step: 0))
        XCTAssertEqual(s.events.rocket, RocketState())
        XCTAssertEqual(s.events.sky.nextStage, 1)
        XCTAssertEqual(s.events.claims, [])
        XCTAssertEqual(s.lives, LivesState())
        XCTAssertEqual(s.social.highWater, 7)
        // a NEWER build's file (unknown keys, higher version) is read for what this build knows
        let newer = #"{"version":2,"coins":9,"futureThing":{"a":1},"events":{"streakStep":1,"futureEvent":{"x":2}}}"#
        let n = try StateStore.decode(Data(newer.utf8))
        XCTAssertEqual([n.version, n.coins, n.events.streakStep], [2, 9, 1])
        // every sub-state decodes from {}
        let empty = Data("{}".utf8)
        let d = StateStore.decoder()
        XCTAssertEqual(try d.decode(EventsState.self, from: empty), EventsState())
        XCTAssertEqual(try d.decode(ClawState.self, from: empty), ClawState())
        XCTAssertEqual(try d.decode(ContestState.self, from: empty), ContestState())
        XCTAssertEqual(try d.decode(RocketState.self, from: empty), RocketState())
        XCTAssertEqual(try d.decode(SkyJumpState.self, from: empty), SkyJumpState())
        XCTAssertEqual(try d.decode(EconomyRules.self, from: empty), EconomyRules())
        XCTAssertEqual(try d.decode(Grant.self, from: empty), Grant())
    }

    func testMigrationsStampAndStepVersions() throws {
        let v0 = try StateStore.decode(Data(#"{"coins":77}"#.utf8))           // no version: 0 → 1
        XCTAssertEqual([v0.version, v0.coins], [1, 77])
        XCTAssertEqual(PlayerState.schemaVersion, 1)
        let steps: [Int: Migrations.Step] = [0: { $0 }, 1: { var o = $0; o["renamed"] = o["old"]; o.removeValue(forKey: "old"); o["version"] = 2; return o }]
        let up = Migrations.upgrade(["old": 5], steps: steps, to: 2)
        XCTAssertEqual(Migrations.version(of: up), 2)
        XCTAssertEqual(up["renamed"] as? Int, 5)
        XCTAssertNil(up["old"])
        XCTAssertEqual(Migrations.version(of: Migrations.upgrade(["version": 1], steps: [:], to: 3)), 1, "a missing step stops")
    }

    // MARK: rewind safety survives a relaunch

    func testTheHighWaterMarkSurvivesARelaunch() throws {
        var s = C3.fresh()
        let t0 = C3.trt("12:00:00")
        _ = Economy.startAttempt(&s, levels: [40], now: t0, rules: C3.rules)
        Economy.finishAttempt(&s, outcome: .lost(.quit), now: t0.addingTimeInterval(1000), rules: C3.rules)
        let st = store
        try st.save(s)
        var back = StateStore(url: st.url).load().state
        XCTAssertEqual(back.social.highWater, Int64(t0.timeIntervalSince1970) + 1000)
        // relaunched with the device clock two days behind: still the latest time ever shown
        let behind = t0.addingTimeInterval(-2 * 86_400)
        XCTAssertEqual(Economy.reconcileOnLaunch(&back, now: behind, rules: C3.rules),
                       [.clockBehind(seconds: Int64(2 * 86_400 + 1000))])
        XCTAssertEqual(Economy.lives(back, now: behind, rules: C3.rules), .counting(count: 4, nextAt: t0.addingTimeInterval(1800)))
        XCTAssertEqual(EconomyClock.peek(back, wall: behind), t0.addingTimeInterval(1000))
    }
}
