import XCTest
import CoreGraphics
import PathCore   // NOT @testable (WP0 acceptance 1): the smoke test uses the public surface only

/// WP0 (LEAD) smoke tests: the package builds and the pieces of REAL WP0 code work — Cell/Dir, the IDs' coding, the
/// tolerant PlayerState v1 decoding (incl. the frozen fixture Tests/Fixtures/wp0_player_v1.json), PathRandom against
/// tools/rng_ref.py, and the owners' WP0 defaults (bundle v1 coding, the fit rule, the rewind-safe social clock, the
/// social clock). CORE owns this file after WP0; each owner's own suite supersedes the matching test here.
final class WP0SmokeTests: XCTestCase {

    // MARK: helpers

    /// Packages/PathCore/Tests, from this file's path.
    private var testsDir: URL { URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent() }

    /// The save format of §4.12 (StateStore): ISO-8601 dates with fractional seconds.
    private static func iso(_ s: String) -> Date {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f.date(from: s)!
    }

    private static func saveDecoder() -> JSONDecoder {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .custom { dec in
            let s = try dec.singleValueContainer().decode(String.self)
            let f = ISO8601DateFormatter()
            f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = f.date(from: s) { return date }
            f.formatOptions = [.withInternetDateTime]
            if let date = f.date(from: s) { return date }
            throw DecodingError.dataCorrupted(.init(codingPath: dec.codingPath, debugDescription: "bad date \(s)"))
        }
        return d
    }

    private static func saveEncoder() -> JSONEncoder {
        let e = JSONEncoder()
        e.outputFormatting = [.sortedKeys, .prettyPrinted]
        e.dateEncodingStrategy = .custom { date, enc in
            let f = ISO8601DateFormatter()
            f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            var c = enc.singleValueContainer()
            try c.encode(f.string(from: date))
        }
        return e
    }

    // MARK: Cell / Dir (◆, real code)

    func testCellAndDir() throws {
        let a = Cell(3, 4)
        XCTAssertEqual(a + .right, Cell(4, 4))
        XCTAssertEqual(a + .up, Cell(3, 3))                 // rows grow DOWN
        XCTAssertEqual(a.moved(.left, by: 3), Cell(0, 4))
        XCTAssertEqual(Dir(from: a, to: Cell(3, 5)), .down)
        XCTAssertNil(Dir(from: a, to: Cell(4, 5)))
        for d in Dir.allCases {
            XCTAssertEqual(d.opposite.opposite, d)
            XCTAssertEqual(d.dc + d.opposite.dc, 0)
            XCTAssertEqual(d.dr + d.opposite.dr, 0)
        }
        XCTAssertEqual(Dir.down.angle, Double.pi / 2, accuracy: 1e-12)
        XCTAssertEqual(Dir.up.angle, -Double.pi / 2, accuracy: 1e-12)
        let json = try JSONEncoder().encode([Cell(1, 2)])
        XCTAssertEqual(String(decoding: json, as: UTF8.self), "[[1,2]]")
        XCTAssertEqual(try JSONDecoder().decode(Cell.self, from: Data("[7,0]".utf8)), Cell(7, 0))
        XCTAssertEqual(try JSONDecoder().decode(Dir.self, from: Data("\"left\"".utf8)), .left)
    }

    // MARK: IDs (◆)

    func testIDsCoding() throws {
        XCTAssertEqual(try JSONDecoder().decode(ArrowID.self, from: Data("13".utf8)), ArrowID(13))
        XCTAssertEqual(try JSONDecoder().decode(ObstacleID.self, from: Data("\"p0\"".utf8)), "p0")
        let counters: [ObstacleID: Int] = ["p0": 2]
        XCTAssertEqual(String(decoding: try JSONEncoder().encode(counters), as: UTF8.self), "{\"p0\":2}")
        let stock: [BoosterID: Int] = [.freeze: 3]
        XCTAssertEqual(String(decoding: try JSONEncoder().encode(stock), as: UTF8.self), "{\"freeze\":3}")
        XCTAssertEqual(try JSONDecoder().decode([BoosterID: Int].self, from: Data("{\"hint\":1}".utf8)), [.hint: 1])
        XCTAssertTrue(ArrowID(2) < ArrowID(10))
    }

    func testLevelTagSpellings() throws {
        let tags = try JSONDecoder().decode([LevelTag].self,
            from: Data("[null, \"normal\", \"Hard Level\", \"hard\", \"Super Hard\", \"superHard\"]".utf8))
        XCTAssertEqual(tags, [.normal, .normal, .hard, .hard, .superHard, .superHard])
        XCTAssertThrowsError(try JSONDecoder().decode(LevelTag.self, from: Data("\"Mega Hard\"".utf8)))
        XCTAssertEqual(String(decoding: try JSONEncoder().encode([LevelTag.superHard]), as: UTF8.self), "[\"superHard\"]")
    }

    // MARK: LevelSpec family (◆ model, C1's WP0 default coding: bundle v1)

    func testBundleV1RoundTrip() throws {
        let level = LevelSpec(
            level: 33, source: .authored, capture: "shot 013", cols: 6, rows: 5, mask: nil, timerSeconds: 180, hearts: 3,
            tag: .hard,
            arrows: [ArrowSpec(id: ArrowID(0), cells: [Cell(0, 0), Cell(1, 0)], dir: .right),
                     ArrowSpec(id: ArrowID(1), cells: [Cell(3, 3), Cell(3, 2)], dir: .up, layer: 1, hiddenBy: "d0")],
            obstacles: [ObstacleSpec(id: "d0", kind: .door, cells: [Cell(3, 2), Cell(3, 3)], order: 0, reveals: [ArrowID(1)]),
                        ObstacleSpec(id: "p0", kind: .pipe, cells: [Cell(5, 0), Cell(5, 1)],
                                     ends: [PipeEnd(cell: Cell(5, 0), out: .up), PipeEnd(cell: Cell(5, 1), out: .down)],
                                     counter: 2, counterAt: [5.5, 0])],
            unlock: .door, seed: nil,
            metrics: LevelMetrics(rounds: 2, freeAtStart: 1, arrows: 2, cells: 4, meanLength: 2))
        // Key names are C1's to choose (SPEC-gameplay may rename them); only the round trip is invariant.
        let data = try JSONEncoder().encode(level)
        XCTAssertEqual(try JSONDecoder().decode(LevelSpec.self, from: data), level)

        let plan = SessionPlan(id: "L1-4", levels: [1, 2, 3, 4], hudLabel: "Levels 1-4", panelLabel: "Level 1-4",
                               reward: 80, stageGap: 0.7, hearts: .carry)
        XCTAssertEqual(try JSONDecoder().decode(SessionPlan.self, from: JSONEncoder().encode(plan)), plan)
    }

    // MARK: Grid / fit (C1's WP0 defaults; C1 pins all 30 recorded levels)

    func testGridMaskAndFitRule() {
        let g = Grid(cols: 3, rows: 2, maskRows: ["#.#", "###"])
        XCTAssertTrue(g.contains(Cell(0, 0)))
        XCTAssertFalse(g.contains(Cell(1, 0)))
        XCTAssertFalse(g.contains(Cell(3, 0)))
        XCTAssertEqual(LevelSpec(level: 1, source: .designed, cols: 3, rows: 2, mask: ["#.#", "###"], timerSeconds: 180,
                                 arrows: []).grid, g)
        let play = Metrics.playRect
        // §4.2 table: L32 20×20 → 17.864, L34 25×35 → 14.556, L35 12×18 → the 28.07 cap, L54 26×34 → 14.036.
        XCTAssertEqual(BoardLayout.fit(grid: Grid(cols: 20, rows: 20), play: play).pitch, 17.864, accuracy: 0.001)
        XCTAssertEqual(BoardLayout.fit(grid: Grid(cols: 25, rows: 35), play: play).pitch, 14.556, accuracy: 0.001)
        XCTAssertEqual(BoardLayout.fit(grid: Grid(cols: 12, rows: 18), play: play).pitch, 28.07, accuracy: 1e-9)
        XCTAssertEqual(BoardLayout.fit(grid: Grid(cols: 26, rows: 34), play: play).pitch, 14.036, accuracy: 0.001)
        let l = BoardLayout.fit(grid: Grid(cols: 20, rows: 20), play: play)
        XCTAssertEqual(l.cell(at: l.centre(Cell(7, 11))), Cell(7, 11))
        XCTAssertEqual(l.maxZoom, 28.07 / l.pitch, accuracy: 1e-9)
        XCTAssertEqual(BoardLayout.fit(grid: Grid(cols: 12, rows: 18), play: play).maxZoom, 1)
    }

    // MARK: PlayerState (◆): tolerant v1 decoding + the frozen fixture

    func testPlayerStateDecodesEmptyObjectToDefaults() throws {
        let s = try Self.saveDecoder().decode(PlayerState.self, from: Data("{}".utf8))
        XCTAssertEqual(s, PlayerState())
        XCTAssertEqual(s.coins, 1000)
        XCTAssertEqual(s.lives.count, 5)
        XCTAssertEqual(s.level, 1)
        XCTAssertTrue(s.settings.sound && s.settings.music && s.settings.haptic)
    }

    func testPlayerStateWrongTypeThrows() {
        XCTAssertThrowsError(try Self.saveDecoder().decode(PlayerState.self, from: Data("{\"coins\":\"lots\"}".utf8)))
    }

    func testFrozenV1FixtureDecodesAndRoundTrips() throws {
        let url = testsDir.appendingPathComponent("Fixtures/wp0_player_v1.json")
        let s = try Self.saveDecoder().decode(PlayerState.self, from: Data(contentsOf: url))
        XCTAssertEqual(s.version, 1)
        XCTAssertEqual(s.installSeed, 42)
        XCTAssertEqual(s.installDate, Self.iso("2026-09-25T09:00:00.000Z"))
        XCTAssertEqual(s.level, 32)
        XCTAssertTrue(s.homeSeen)
        XCTAssertEqual(s.coins, 1340)
        XCTAssertEqual(s.pendingCoinFly, 20)
        XCTAssertEqual(s.lives, LivesState(count: 4, anchor: Self.iso("2026-09-25T09:20:00.000Z")))
        XCTAssertEqual(s.unlimitedLivesUntil, Self.iso("2026-09-25T10:00:00.000Z"))
        XCTAssertEqual(s.boosters, ["freeze": 3, "hint": 2])
        XCTAssertEqual(s.unlocksSeen, ["linked", "pipe"])
        XCTAssertEqual(s.tutorialsDone, ["tapToMove"])
        XCTAssertEqual(s.attempts, [1: 1, 32: 2])
        XCTAssertEqual(s.activeAttempt, ActiveAttempt(session: "L32", levels: [32], attemptIndex: 2,
                                                      startedAt: Self.iso("2026-09-25T09:31:00.000Z"), stage: 0))
        XCTAssertEqual(s.stats, PlayerState.Stats(wins: 31, losses: 3, firstTryWins: 20, weeklyContestWins: 0, playSeconds: 3600.5))
        XCTAssertEqual(s.settings, PlayerState.Settings(sound: true, music: false, haptic: true, notifications: true, trail: nil))
        XCTAssertEqual(s.flags, PlayerState.Flags(ratingPromptShown: false, notificationPromptShown: true, weeklyIntroSeen: false,
                                                  seen: ["clawIntro"]))
        XCTAssertEqual(s.social.username, "player_k3x9q2a")
        XCTAssertEqual(s.social.avatar, 3)
        XCTAssertEqual(s.social.country, "TR")
        XCTAssertEqual(s.social.highWater, 1_790_328_600)
        XCTAssertEqual(s.processedTransactions, ["2000000000000001"])
        let again = try Self.saveDecoder().decode(PlayerState.self, from: Self.saveEncoder().encode(s))
        XCTAssertEqual(again, s)
    }

    // MARK: PathRandom (copied from MF; values from `python3 tools/rng_ref.py`)

    func testPathRandomMatchesTheReference() {
        var r = PathRandom(seed: 42)
        let first: [UInt64] = (0..<8).map { _ in r.next() }
        XCTAssertEqual(first, [0x15780B2E0C2EC716, 0x6104D9866D113A7E, 0xAE17533239E499A1, 0xECB8AD4703B360A1,
                               0xFDE6DC7FE2EC5E64, 0xC50DA53101795238, 0xB82154855A65DDB2, 0xD99A2743EBE60087])
        var f = PathRandom(seed: 42).fork("hint")
        XCTAssertEqual((0..<4).map { _ in f.next() },
                       [0x7E2CD01BAB3605D1, 0xE572465D3E420439, 0x132171D6A148A154, 0xAA9BB41BFDC800C3])
        XCTAssertEqual(PathRandom.attemptSeed(install: 42, level: 1, attempt: 1), 0x2AA7E46C18DBC455)
        XCTAssertEqual(PathRandom.attemptSeed(install: 42, level: 2, attempt: 1), 0xB9BA5C379319B214)
        var u = PathRandom(seed: 42)
        XCTAssertEqual((0..<4).map { _ in u.unit() },
                       [0.08386297105988216, 0.3789802506626686, 0.6800434110281394, 0.9246929453253876])
        var b = PathRandom(seed: 7)
        for _ in 0..<1000 { let v = b.below(6); XCTAssertTrue((0..<6).contains(v)) }
        XCTAssertEqual(PathRandom.levelSeed(level: 100, salt: 1), PathRandom.levelSeed(level: 100, salt: 1))
        XCTAssertNotEqual(PathRandom.levelSeed(level: 100, salt: 1), PathRandom.levelSeed(level: 101, salt: 1))
    }

    // MARK: Ease (copied from MF)

    func testEaseEndpoints() {
        for token in EaseToken.allCases {
            XCTAssertEqual(token(0), 0, accuracy: 1e-9, "\(token)")
            XCTAssertEqual(token(1), 1, accuracy: 1e-9, "\(token)")
        }
        XCTAssertEqual(Ease.outCubic(1), 1, accuracy: 1e-6)
        XCTAssertEqual(SpringCurve(response: 0.429, dampingFraction: 0.47).value(10, from: 0, to: 1), 1, accuracy: 1e-6)
    }

    // MARK: Social clock (SOC1's WP0 default; the rewind rule is binding, §4.11 item 5)

    func testSocialClockIsRewindSafe() {
        var high: Int64 = 0
        let t1 = SocialClock.now(wall: Date(timeIntervalSince1970: 2_000_000_000.9), highWater: &high)
        XCTAssertEqual(t1.seconds, 2_000_000_000)
        XCTAssertEqual(high, 2_000_000_000)
        let back = SocialClock.now(wall: Date(timeIntervalSince1970: 1_999_000_000), highWater: &high)
        XCTAssertEqual(back, t1, "a clock set back must freeze the world (§4.11 item 5)")
        XCTAssertEqual(high, 2_000_000_000)
    }
}
