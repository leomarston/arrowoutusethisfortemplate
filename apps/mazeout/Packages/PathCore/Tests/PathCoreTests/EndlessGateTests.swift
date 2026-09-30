import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// C4c (SPEC.md §5.27, the ENDLESS QUALITY GATE): LevelProvider serves a generated level only inside Difficulty's bands
/// (units, waves, free-at-start, the template's timer, grid, time share) with every Box counter inside the ring art's max
/// (99, build/l2/box-digits-fit.txt); otherwise it re-rolls the seed deterministically (`LevelProvider.rollSeed`, bounded
/// by `LevelProvider.maxRolls`), then serves the roll nearest the band centre. L1-L150 are authored and untouched (their
/// byte-for-byte tests live in GeneratorTests / LevelLibraryTests).
enum EndlessFixtures {
    /// The curve the two lists below were read from (Fixtures/c4_runtime_reference.json `curve_sha256`: content recast 2
    /// of 2026-09-25, templates L30-L99 in 7 slots; was 85b7949b… on recast 1's 15:40 curve). A new curve moves them: re-pin both lists from the evidence line "valid reference outputs
    /// outside the bands" of C4FullTests.testRuntimeLevelsAgainstTheReference (PC_C4_FULL=1) on the new curve and its new
    /// reference fixture; `checkPinnedCurve` fails with that instruction until then.
    /// PUBLISH B0 (2026-09-28, ruling 39 OD8 provenance strip): TEXT-ONLY re-pin d129f94c… → 4a3ce70f… — the curve's
    /// "_about" comment lost "the recorded" / "v552"; every curve number is unchanged, so both lists stay (proven by
    /// PC_C4_FULL=1: the 500 runtime levels still equal the reference fixture, whose curve_sha256 moved with this pin).
    static let pinnedCurveSHA = "4a3ce70f4aa2ed7ad4847ee9d5fe3ba1ca3c1c62d7ce4fa8558f3a4421a02ed7"

    /// The reference boards of L151-L650 that are VALID but outside the bands, with their first (on this curve: only)
    /// violation (build/recast2/c4full-copy/c4-runtime-levels.txt; the reference's two dead ends L416 / L517 are not here:
    /// the validator refuses them before the band check).
    static let bandRerolls: [Int: String] = [162: "waves 9 vs target 5", 210: "units 42 vs target 31", 257: "units 66 vs target 48",
                                             322: "units 26 vs target 19", 363: "free at start 10 vs target 1", 441: "units 43 vs target 30",
                                             442: "units 32 vs target 19", 596: "units 44 vs target 31", 642: "units 76 vs target 56"]
    /// The reference boards of L151-L650 whose Box counter the ring cannot show (found by the C4c gate).
    static let boxRerolls: [Int: String] = [354: "box b0 counter 111 above the ring art's max 99"]

    static func levelSeed(_ n: Int) -> UInt64 { PathRandom.levelSeed(level: n, salt: CurveSpec.default.salt) }

    /// false (and a failure saying what to do) when the compiled curve is no longer the one the level lists were read from.
    static func checkPinnedCurve(file: StaticString = #filePath, line: UInt = #line) -> Bool {
        let sha = C4Fixtures.sha256(ContentJSON.write(CurveSpec.default.json))
        if sha == pinnedCurveSHA { return true }
        XCTFail("CurveSpec.default changed (sha256 \(sha)): re-pin EndlessFixtures.bandRerolls / boxRerolls / pinnedCurveSHA (see their note)",
                file: file, line: line)
        return false
    }

    /// The provider's gate (LevelProvider.produce): the full Validator, content rules + the game's rules.
    static let fullGate: Generator.Gate = { cand in
        var c = cand
        c.source = .generated
        let rep = Validator.checkLevel(c, raw: nil, sprites: nil, options: Validator.Options())
        return rep.isValid ? nil : rep.errors.first.map(\.message) ?? "invalid"
    }

    static func boxCounters(_ l: LevelSpec) -> [Int] {
        l.obstacles.filter { $0.kind == .box || $0.kind == .curtain }.compactMap(\.counter)
    }

    /// The board up to translation and the 8 symmetries of the square grid (rotations, mirrors): the smallest of the 8
    /// sorted lists of arrow paths (tail → head cells, translated to the origin). Directions are left out on purpose, so
    /// two boards with the same arrow bodies collide even if a head were drawn differently (a stricter repeat test).
    static func shapeKey(_ l: LevelSpec) -> String {
        let all = l.arrows.flatMap(\.cells)
        guard !all.isEmpty else { return "" }
        var best: String?
        for t in 0..<8 {
            func f(_ c: Cell) -> (Int, Int) {
                switch t {
                case 0: return (c.c, c.r)
                case 1: return (-c.r, c.c)
                case 2: return (-c.c, -c.r)
                case 3: return (c.r, -c.c)
                case 4: return (-c.c, c.r)
                case 5: return (c.c, -c.r)
                case 6: return (c.r, c.c)
                default: return (-c.r, -c.c)
                }
            }
            let mapped = all.map(f)
            let x0 = mapped.map(\.0).min()!, y0 = mapped.map(\.1).min()!
            let k = l.arrows.map { a in a.cells.map { c -> String in let (x, y) = f(c); return "\(x - x0),\(y - y0)" }.joined(separator: " ") }
                .sorted().joined(separator: "|")
            if best == nil || k < best! { best = k }
        }
        return best!
    }

    static func driver(_ l: LevelSpec) -> DriverResult {
        var c = DriverConfig(tapInterval: 0.6)
        c.recordEvents = false
        return HeadlessDriver.play(level: l, config: c)
    }
}

final class EndlessGateTests: XCTestCase {

    // MARK: the seeds and the ranking

    /// Roll 0 is the level's own seed (the reference board); roll k is the seed salted with "reroll" and k. The pinned
    /// values come from the independent Python mirror tools/rng_ref.py (splitmix(splitmix(seed ^ fnv1a64("reroll")) ^ k)).
    func testRollSeedsAreTheLevelSeedSaltedWithTheRoll() {
        for n in [151, 430, 524, 1150] {
            let base = EndlessFixtures.levelSeed(n)
            XCTAssertEqual(LevelProvider.rollSeed(base, roll: 0), base)
            let seeds = (0..<LevelProvider.maxRolls).map { LevelProvider.rollSeed(base, roll: $0) }
            XCTAssertEqual(Set(seeds).count, LevelProvider.maxRolls, "L\(n): a roll repeats a seed")
            for k in 1..<LevelProvider.maxRolls {
                XCTAssertNotEqual(seeds[k], base &+ UInt64(k), "L\(n): roll \(k) is not salted")
                XCTAssertNotEqual(seeds[k], EndlessFixtures.levelSeed(n + k), "L\(n): roll \(k) is another level's seed")
            }
        }
        XCTAssertEqual(LevelProvider.maxRolls, 16)
        // literal level seeds (L151, L430, L524 of the 15:40 curve), so the pins do not move with the curve's salt
        XCTAssertEqual(LevelProvider.rollSeed(1465048862492141599, roll: 1), 4798671902102785016)
        XCTAssertEqual(LevelProvider.rollSeed(1465048862492141599, roll: 2), 8544773118672167310)
        XCTAssertEqual(LevelProvider.rollSeed(1465048862492141599, roll: 15), 17072175894609185165)
        XCTAssertEqual(LevelProvider.rollSeed(17890430866439464329, roll: 1), 16248548397152386883)
        XCTAssertEqual(LevelProvider.rollSeed(1661011634938315102, roll: 1), 18118248475463716450)
    }

    /// The band centre is distance 0, each band edge 1; hard violations outrank any distance; ties keep the earlier roll.
    /// assess counts the hard violations and computes the distance from the same measurement.
    func testCentreDistanceAndRanking() throws {
        let b = DifficultyBands.designed
        let cu = (b.unitsRatio.lowerBound + b.unitsRatio.upperBound) / 2, cr = (b.roundsRatio.lowerBound + b.roundsRatio.upperBound) / 2
        // recast 2's bands: free −9…+8, centre −0.5 (no integer delta sits on it; recast 1's −12…+10 had −1), half-width 8.5
        XCTAssertEqual(b.freeDelta, -9...8)
        let fc = Double(b.freeDelta.lowerBound + b.freeDelta.upperBound) / 2, fh = Double(b.freeDelta.upperBound - b.freeDelta.lowerBound) / 2
        let t1 = abs(-1 - fc) / fh                                           // free delta −1: 0.5 / 8.5 = 1/17
        XCTAssertEqual(t1, 1.0 / 17, accuracy: 1e-12)
        XCTAssertEqual(b.centreDistance(unitsRatio: cu, roundsRatio: cr, freeDelta: -1), t1, accuracy: 1e-12)
        XCTAssertEqual(b.centreDistance(unitsRatio: b.unitsRatio.upperBound, roundsRatio: cr, freeDelta: -1), (1 + t1 * t1).squareRoot(), accuracy: 1e-12)
        XCTAssertEqual(b.centreDistance(unitsRatio: b.unitsRatio.lowerBound, roundsRatio: cr, freeDelta: -1), (1 + t1 * t1).squareRoot(), accuracy: 1e-12)
        XCTAssertEqual(b.centreDistance(unitsRatio: cu, roundsRatio: b.roundsRatio.lowerBound, freeDelta: -1), (1 + t1 * t1).squareRoot(), accuracy: 1e-12)
        XCTAssertEqual(b.centreDistance(unitsRatio: cu, roundsRatio: cr, freeDelta: 8), 1, accuracy: 1e-12)
        XCTAssertEqual(b.centreDistance(unitsRatio: cu, roundsRatio: cr, freeDelta: -9), 1, accuracy: 1e-12)
        XCTAssertEqual(b.centreDistance(unitsRatio: b.unitsRatio.upperBound, roundsRatio: cr, freeDelta: 8), 2.squareRoot(), accuracy: 1e-12)
        // the exact centre is 0 and every edge 1 (on bands whose free centre is an integer, e.g. recast 1's −12…+10)
        var evenFree = b
        evenFree.freeDelta = -12...10
        XCTAssertEqual(evenFree.centreDistance(unitsRatio: cu, roundsRatio: cr, freeDelta: -1), 0, accuracy: 1e-12)
        XCTAssertEqual(evenFree.centreDistance(unitsRatio: b.unitsRatio.upperBound, roundsRatio: cr, freeDelta: -1), 1, accuracy: 1e-12)
        XCTAssertEqual(evenFree.centreDistance(unitsRatio: cu, roundsRatio: b.roundsRatio.lowerBound, freeDelta: -1), 1, accuracy: 1e-12)
        XCTAssertEqual(evenFree.centreDistance(unitsRatio: cu, roundsRatio: cr, freeDelta: 10), 1, accuracy: 1e-12)
        XCTAssertEqual(evenFree.centreDistance(unitsRatio: b.unitsRatio.upperBound, roundsRatio: cr, freeDelta: 10), 2.squareRoot(), accuracy: 1e-12)
        // (that every designed level sits inside the bands is C4FullTests.testBandsAreTheDesignedEnvelope)
        let x = try Difficulty.assess(C4Fixtures.level(C4Fixtures.designedRange.lowerBound))
        XCTAssertEqual(x.centreDistance, b.centreDistance(unitsRatio: x.unitsRatio, roundsRatio: x.roundsRatio,
                                                          freeDelta: x.measured.freeAtStart - x.target.free), accuracy: 1e-12)
        XCTAssertLessThanOrEqual(x.hardViolations, x.violations.count)
        // ranking: hard violations first, then the distance, strict (the earlier candidate keeps a tie)
        var a = x
        var z = a
        a.hardViolations = 0; a.centreDistance = 5
        z.hardViolations = 1; z.centreDistance = 0.1
        XCTAssertTrue(a.ranksBefore(z))
        XCTAssertFalse(z.ranksBefore(a))
        z.hardViolations = 0
        XCTAssertTrue(z.ranksBefore(a))
        z.centreDistance = 5
        XCTAssertFalse(z.ranksBefore(a))
        XCTAssertFalse(a.ranksBefore(z))
    }

    /// The Box counter limit = the ring art's (build/l2/box-digits-fit.txt: 2 digits fit the well, 3 overflow).
    func testTheBoxCounterLimitIsTheRingArtsMax() throws {
        XCTAssertEqual(Difficulty.boxCounterArtMax, 99)
        XCTAssertEqual(DifficultyBands.designed.maxBoxCounter, 99)
        XCTAssertEqual(DifficultyBands(unitsRatio: 0...9, roundsRatio: 0...9, freeDelta: -99...99, minTimeShare: 0.2).maxBoxCounter, 99)
        var l = try XCTUnwrap(C4Fixtures.allLevels.first { C4Fixtures.designedRange.contains($0.level) && $0.obstacles.contains { $0.kind == .box } },
                              "no designed level with a box")
        let i = try XCTUnwrap(l.obstacles.firstIndex { $0.kind == .box })
        // the Box finding alone (a counter also moves the waves, so the other findings may change with it)
        let mark = "box \(l.obstacles[i].id.raw) counter "
        func boxFindings(_ l: LevelSpec, _ b: DifficultyBands = .designed) throws -> [String] {
            try Difficulty.assess(l, bands: b).violations.filter { $0.hasPrefix(mark) }
        }
        var roomy = DifficultyBands.designed
        roomy.maxBoxCounter = 100
        XCTAssertEqual(try boxFindings(l), [])
        l.obstacles[i].counter = 99
        XCTAssertEqual(try boxFindings(l), [])
        l.obstacles[i].counter = 100
        XCTAssertEqual(try boxFindings(l), [mark + "100 above the ring art's max 99"])
        XCTAssertEqual(try boxFindings(l, roomy), [])
        // it is a hard finding: the same board has one more hard violation under the ring's 99 than under 100
        XCTAssertEqual(try Difficulty.assess(l).hardViolations, try Difficulty.assess(l, bands: roomy).hardViolations + 1)
        l.obstacles[i].kind = .curtain                                      // the curtain is drawn with the same ring
        XCTAssertEqual(try boxFindings(l), [mark + "100 above the ring art's max 99"])
    }

    // MARK: the re-rolls on the real levels

    /// The valid reference boards outside the bands (recast 2's curve: L162 L210 L257 L322 L363 L441 L442 L596 L642) are
    /// re-rolled into band: a salted seed, a valid board the game's solver clears and the 0.6 s/tap driver wins, the same
    /// bytes on a second production (checked here on L162; C4FullEndlessTests reproduces all 1,000 of L151-L1150).
    func testTheValidOutOfBandReferenceLevelsAreRerolledIntoBand() throws {
        try EndlessGateTests.checkRerolls(EndlessFixtures.bandRerolls, reproduce: [162])
    }

    /// A Box counter above the maximum is refused like a band miss and re-rolled. Cheap here: the first small generated
    /// level (target ≤ 30 units) from L151 on, served on its own seed with a box counting c ≥ 2; with a
    /// maximum of c − 1 its roll 0 is refused and a re-roll whose boxes fit is served. The real case (recast 2's curve:
    /// L354, 111 against the ring's 99) is C4FullEndlessTests.testBoxCountersAboveTheRingArtMaxAreRerolled.
    func testABoxCounterAboveTheMaxIsRerolled() throws {
        var found: (n: Int, c: Int, id: String)?
        for n in 151...400 where found == nil {
            guard let t = try? Generator.target(.default, n), t.units <= 30 else { continue }   // small boards: cheap in debug
            let (own, rec) = LevelProvider.produce(n, curve: .default, library: nil, options: Validator.Options())
            guard rec.roll == 0, let b = own.obstacles.filter({ $0.kind == .box && ($0.counter ?? 0) >= 2 })
                .max(by: { ($0.counter ?? 0) < ($1.counter ?? 0) }) else { continue }
            found = (n, b.counter!, b.id.raw)
        }
        let (n, c, id) = try XCTUnwrap(found, "no level of L151-L400 with a box on its own seed")
        var bands = DifficultyBands.designed
        bands.maxBoxCounter = c - 1
        let (l, rec) = LevelProvider.produce(n, curve: .default, library: nil, options: Validator.Options(), bands: bands)
        XCTAssertEqual(rec.route, .retried, "L\(n)")
        XCTAssertTrue(rec.refused.contains { $0.hasPrefix("roll 0: out of band: ") && $0.contains("box \(id) counter \(c) above the ring art's max \(c - 1)") },
                      "L\(n): \(rec.refused)")
        XCTAssertTrue(EndlessFixtures.boxCounters(l).allSatisfy { $0 <= c - 1 }, "L\(n): \(EndlessFixtures.boxCounters(l))")
        XCTAssertTrue(try Difficulty.assess(l, bands: bands).inBand, "L\(n)")
        XCTAssertEqual(l.seed, LevelProvider.rollSeed(EndlessFixtures.levelSeed(n), roll: rec.roll))
        XCTAssertTrue(Validator.checkLevel(l, raw: nil, sprites: nil, options: Validator.Options()).isValid, "L\(n)")
    }

    static func checkRerolls(_ cases: [Int: String], reproduce: Set<Int>) throws {
        guard EndlessFixtures.checkPinnedCurve() else { return }
        let refRows = try XCTUnwrap(C4Fixtures.json("c4_runtime_reference.json")["levels"]?.arrayValue)
        for (n, why) in cases.sorted(by: { $0.key < $1.key }) {
            // the premise: the reference board (= gen_levels.py's, by SHA-256) is valid but out of band
            let ref = try Generator.generate(level: n, curve: .default)
            let row = try XCTUnwrap(refRows.first { $0["level"]?.intValue == n })
            XCTAssertEqual(C4Fixtures.sha256(ContentJSON.line(ref.level, schema: false)), row["sha256"]?.stringValue, "L\(n) reference")
            XCTAssertEqual(row["errors"]?.arrayValue?.count, 0, "L\(n): the reference is valid")
            let ra = try Difficulty.assess(ref.level)
            XCTAssertTrue(ra.violations.first?.hasPrefix(why) == true, "L\(n): \(ra.violations)")
            // served: re-rolled into band
            let (l, rec) = LevelProvider.produce(n, curve: .default, library: nil, options: Validator.Options())
            XCTAssertEqual(rec.route, .retried, "L\(n)")
            XCTAssertGreaterThanOrEqual(rec.roll, 1, "L\(n)")
            XCTAssertEqual(rec.seedsTried, rec.roll + 1, "L\(n)")
            XCTAssertEqual(rec.bandViolations, [], "L\(n)")
            XCTAssertTrue(rec.refused.contains { $0.hasPrefix("roll 0: out of band: " + why) }, "L\(n): \(rec.refused)")
            XCTAssertEqual(l.seed, LevelProvider.rollSeed(EndlessFixtures.levelSeed(n), roll: rec.roll), "L\(n)")
            XCTAssertEqual(l.level, n)
            XCTAssertEqual(l.source, .generated)
            XCTAssertNotEqual(l.arrows, ref.level.arrows, "L\(n)")
            let a = try Difficulty.assess(l)
            XCTAssertTrue(a.inBand, "L\(n) served out of band: \(a.violations)")
            XCTAssertEqual(l.timerSeconds, a.target.templateTimer, "L\(n)")
            XCTAssertTrue(EndlessFixtures.boxCounters(l).allSatisfy { (1...Difficulty.boxCounterArtMax).contains($0) }, "L\(n)")
            let rep = Validator.checkLevel(l, raw: nil, sprites: nil, options: Validator.Options())
            XCTAssertTrue(rep.isValid, "L\(n): \(rep.errors)")
            XCTAssertTrue(Solver.solve(l).isSolved, "L\(n): the game's solver does not clear it")
            let d = EndlessFixtures.driver(l)
            XCTAssertTrue(d.won, "L\(n): not won by the 0.6 s/tap driver")
            XCTAssertGreaterThanOrEqual(d.timeLeftFraction, 0.2, "L\(n)")
            // deterministic: the same board again, bytes included
            if reproduce.contains(n) {
                let again = LevelProvider.produce(n, curve: .default, library: nil, options: Validator.Options())
                XCTAssertEqual(ContentJSON.line(again.0, schema: true), ContentJSON.line(l, schema: true), "L\(n) differs on a second production")
            }
        }
    }

    /// No roll in band (impossible bands): the provider serves the roll that ranks first (fewest hard violations, then
    /// nearest the band centre), deterministically, and says so.
    func testWithNoRollInBandTheNearestToTheBandCentreIsServed() throws {
        var odd = DifficultyBands.designed
        odd.unitsRatio = 5.0...6.0                                          // no board of L151 has 5× its target units
        let n = 151, rolls = 3
        let (l, rec) = LevelProvider.produce(n, curve: .default, library: nil, options: Validator.Options(), bands: odd, maxRolls: rolls)
        XCTAssertEqual(rec.route, .nearest)
        XCTAssertEqual(rec.seedsTried, rolls)
        XCTAssertEqual(rec.refused.filter { $0.contains(": out of band: ") }.count, rolls)
        // recompute every roll independently and rank them
        var best: (k: Int, a: Difficulty.Assessment, l: LevelSpec)?
        for k in 0..<rolls {
            var c = try Generator.generate(level: n, curve: .default, seed: LevelProvider.rollSeed(EndlessFixtures.levelSeed(n), roll: k),
                                           gate: EndlessFixtures.fullGate).level
            c.source = .generated
            let a = try Difficulty.assess(c, bands: odd)
            XCTAssertFalse(a.inBand)
            if best == nil || a.ranksBefore(best!.a) { best = (k, a, c) }
        }
        let b = try XCTUnwrap(best)
        XCTAssertEqual(rec.roll, b.k)
        XCTAssertEqual(l, b.l)
        XCTAssertEqual(rec.bandViolations, b.a.violations)
        XCTAssertEqual(l.seed, LevelProvider.rollSeed(EndlessFixtures.levelSeed(n), roll: b.k))
        XCTAssertTrue(Validator.checkLevel(l, raw: nil, sprites: nil, options: Validator.Options()).isValid)
        let again = LevelProvider.produce(n, curve: .default, library: nil, options: Validator.Options(), bands: odd, maxRolls: rolls)
        XCTAssertEqual(again.0, l)
        XCTAssertEqual(again.1.roll, rec.roll)
        // the designed bands: served on the first roll in band (L151 on its own seed, on recast 1's and recast 2's curves)
        let (l0, rec0) = LevelProvider.produce(n, curve: .default, library: nil, options: Validator.Options())
        XCTAssertEqual(rec0.route, rec0.roll == 0 ? .generated : .retried)
        XCTAssertEqual(rec0.seedsTried, rec0.roll + 1)
        XCTAssertEqual(l0.seed, LevelProvider.rollSeed(EndlessFixtures.levelSeed(n), roll: rec0.roll))
        XCTAssertTrue(try Difficulty.assess(l0).inBand)
    }

    // MARK: the provider protocol

    /// The re-roll happens where generation happens: off the main thread, one level ahead (levelStarted(161) prefetches
    /// L162, a pinned re-roll of recast 2's curve; was L622 on recast 1's), and level(162) then returns the re-rolled board
    /// at once; a second provider (produce on the calling thread) gives the same board.
    func testTheRerollRunsOffTheMainThreadOneLevelAhead() throws {
        guard EndlessFixtures.checkPinnedCurve() else { return }            // L162 is one of the pinned re-rolls
        let doc = C4Fixtures.doc
        let unlocks = (try? FeatureUnlock.decodeList(ContentJSON.data(doc["unlocks"]!))) ?? []
        func library() -> LevelLibrary {
            LevelLibrary(levels: C4Fixtures.allLevels, sessions: [], unlocks: unlocks, curveJSON: ContentJSON.data(doc["curve"]!))
        }
        // the compiled curve the re-roll list was pinned on (the fixture document may already carry a newer curve)
        let p = LevelProvider(library: library(), curve: .default)
        XCTAssertEqual(p.authoredEnd, 150)
        XCTAssertEqual(p.bands, .designed)
        XCTAssertEqual(p.maxRolls, LevelProvider.maxRolls)
        XCTAssertTrue(EndlessFixtures.bandRerolls.keys.contains(162))
        XCTAssertFalse(p.isReady(162))
        let produced = expectation(description: "L162 produced off the main thread")
        let seen = Locked<[(Int, Bool, LevelProvider.Record.Route)]>([])
        p.onProduced = { rec in
            seen.set(seen.get() + [(rec.level, Thread.isMainThread, rec.route)])
            if rec.level == 162 { produced.fulfill() }
        }
        XCTAssertTrue(Thread.isMainThread)
        p.levelStarted(161)
        wait(for: [produced], timeout: 240)
        let s = seen.get()
        XCTAssertEqual(s.map(\.0), [162])
        XCTAssertEqual(s.first?.1, false, "generated on the main thread")
        XCTAssertEqual(s.first?.2, .retried)
        XCTAssertTrue(p.isReady(162))
        let t0 = DispatchTime.now().uptimeNanoseconds
        let l = p.level(162)
        XCTAssertLessThan(Double(DispatchTime.now().uptimeNanoseconds - t0) / 1e6, 50, "level(162) generated again instead of the cache")
        XCTAssertTrue(try Difficulty.assess(l).inBand)
        let other = LevelProvider(library: library(), curve: .default)
        XCTAssertEqual(other.level(162), l)                                  // a cache miss: produced on this thread
        XCTAssertEqual(other.records.first?.route, .retried)
        XCTAssertEqual(p.records.count, 1)
        XCTAssertEqual(p.level(150), C4Fixtures.level(150))                  // authored: untouched
    }
}

/// The full endless acceptance (PC_C4_FULL=1, release build): 1,000 served levels L151-L1150.
final class C4FullEndlessTests: XCTestCase {

    override func setUpWithError() throws {
        guard C4Fixtures.full else { throw XCTSkip("PC_C4_FULL=1 runs the 1,000-level endless acceptance (release build recommended)") }
    }

    /// The reference board whose Box counter the ring cannot show (recast 2's curve: L354, 111; valid and otherwise in
    /// band; its roll 1 counts 135, so roll 2 is served) is re-rolled into band like the ratio misses, deterministically.
    func testBoxCountersAboveTheRingArtMaxAreRerolled() throws {
        try EndlessGateTests.checkRerolls(EndlessFixtures.boxRerolls, reproduce: [354])
    }

    /// L151-L1150 exactly as LevelProvider serves them: every one valid (content + game rules), cleared by the game's
    /// solver (C4's exact search) and won by the 0.6 s/tap driver with ≥ 20 % of the timer, inside the bands with every
    /// Box counter ≤ the ring's 99, never the nearest/fallback route; no exact or translated/rotated/mirrored repeat
    /// among them or against L1-L150; byte-identical on a second production (on two threads, in another order). The
    /// production time (the whole gated generation, re-rolls included) is measured sequentially on this Mac.
    func testThousandServedLevelsAreInBandSolvableUniqueAndDeterministic() throws {
        let range = Array(151...1150)
        struct Served { var n: Int; var level: LevelSpec; var line: String; var rec: LevelProvider.Record; var wallMs: Double }
        var served: [Served] = []
        var out: [String] = []
        var invalid = 0, unsolved = 0, lost = 0, outOfBand = 0, boxOver = 0, badRoute = 0, badSeed = 0
        // run 1: sequential, as the provider's single background queue produces them
        for n in range {
            let t0 = C4Fixtures.wallNow()
            let (l, rec) = LevelProvider.produce(n, curve: .default, library: nil, options: Validator.Options())
            let wall = (C4Fixtures.wallNow() - t0) * 1000
            served.append(Served(n: n, level: l, line: ContentJSON.line(l, schema: true), rec: rec, wallMs: wall))
        }
        for s in served {
            let l = s.level, n = s.n
            XCTAssertEqual(l.level, n)
            XCTAssertEqual(l.source, .generated)
            let okRoute = s.rec.route == .generated || s.rec.route == .retried
            if !okRoute { badRoute += 1 }
            XCTAssertTrue(okRoute, "L\(n) route \(s.rec.route): \(s.rec.bandViolations)")
            if l.seed != LevelProvider.rollSeed(EndlessFixtures.levelSeed(n), roll: s.rec.roll) { badSeed += 1 }
            XCTAssertEqual(l.seed, LevelProvider.rollSeed(EndlessFixtures.levelSeed(n), roll: s.rec.roll), "L\(n) seed")
            let rep = Validator.checkLevel(l, raw: nil, sprites: nil, options: Validator.Options())
            if !rep.isValid { invalid += 1 }
            XCTAssertTrue(rep.isValid, "L\(n): \(rep.errors)")
            let solved = Solver.solve(l).isSolved
            if !solved { unsolved += 1 }
            XCTAssertTrue(solved, "L\(n): the game's solver does not clear it")
            let d = EndlessFixtures.driver(l)
            if !d.won || d.timeLeftFraction < 0.2 { lost += 1 }
            XCTAssertTrue(d.won && d.timeLeftFraction >= 0.2, "L\(n): driver won \(d.won), time left \(d.timeLeftFraction)")
            let a = try Difficulty.assess(l)
            if !a.inBand { outOfBand += 1 }
            XCTAssertTrue(a.inBand, "L\(n) out of band: \(a.violations)")
            let boxes = EndlessFixtures.boxCounters(l)
            if boxes.contains(where: { $0 > 99 }) { boxOver += 1 }
            XCTAssertTrue(boxes.allSatisfy { (1...99).contains($0) }, "L\(n) box counters \(boxes)")
            let rerolled = s.rec.refused.filter { $0.contains(": out of band: ") }
            out.append(String(format: "L%d %@ roll %d  %@ %@ %@  units %d/%d (×%.2f) waves %d/%d (×%.2f) free %d/%d %dx%d t%d%@  %.1f ms%@",
                              n, s.rec.route.rawValue, s.rec.roll, rep.isValid ? "valid" : "INVALID", solved ? "solved" : "UNSOLVED",
                              d.won ? "won" : "LOST", a.measured.units, a.target.units, a.unitsRatio, a.measured.rounds, a.target.rounds,
                              a.roundsRatio, a.measured.freeAtStart, a.target.free, l.cols, l.rows, l.timerSeconds,
                              boxes.isEmpty ? "" : " box \(boxes.map(String.init).joined(separator: ","))", s.rec.totalMs,
                              rerolled.isEmpty ? "" : "  RE-ROLLED: " + rerolled.joined(separator: " | ")))
        }
        // run 2: again, on two threads in another order: byte-identical
        var again = [String](repeating: "", count: range.count)
        let lock = NSLock()
        DispatchQueue.concurrentPerform(iterations: 2) { j in
            var i = range.count - 1 - j
            while i >= 0 {
                let line = ContentJSON.line(LevelProvider.produce(range[i], curve: .default, library: nil, options: Validator.Options()).0, schema: true)
                lock.lock(); again[i] = line; lock.unlock()
                i -= 2
            }
        }
        var rerunDiffs: [Int] = []
        for (i, s) in served.enumerated() where again[i] != s.line { rerunDiffs.append(s.n) }
        XCTAssertEqual(rerunDiffs, [], "a second production differs")
        // repeats: exact (Validator.boardKey, offset-free) and up to translation + the 8 grid symmetries, among the 1,000
        // and against the authored L1-L150
        var exact: [[Int]: Int] = [:], shape: [String: Int] = [:]
        var exactRepeats: [String] = [], shapeRepeats: [String] = []
        let checked = Set(range)
        for l in C4Fixtures.allLevels + served.map(\.level) {
            let k = Validator.boardKey(l), s = EndlessFixtures.shapeKey(l)
            if let o = exact[k], checked.contains(l.level) || checked.contains(o) { exactRepeats.append("L\(l.level) = L\(o)") }
            else if let o = shape[s], checked.contains(l.level) || checked.contains(o) { shapeRepeats.append("L\(l.level) ≅ L\(o)") }
            if exact[k] == nil { exact[k] = l.level }
            if shape[s] == nil { shape[s] = l.level }
        }
        XCTAssertEqual(exactRepeats, [])
        XCTAssertEqual(shapeRepeats, [])
        // timing (release, sequential): the whole production incl. the gate, the band check and any re-roll
        func pct(_ v: [Double], _ p: Double) -> Double { let s = v.sorted(); return s[min(s.count - 1, Int(Double(s.count) * p))] }
        func stats(_ v: [Double]) -> String {
            guard !v.isEmpty else { return "-" }
            return String(format: "n %d  mean %.1f  p50 %.1f  p95 %.1f  p99 %.1f  max %.1f ms", v.count, v.reduce(0, +) / Double(v.count),
                          pct(v, 0.5), pct(v, 0.95), pct(v, 0.99), v.max()!)
        }
        let rerolled = served.filter { $0.rec.roll > 0 }
        let routes = Dictionary(grouping: served, by: { $0.rec.route.rawValue }).mapValues(\.count).sorted { $0.key < $1.key }
        let digest = C4Fixtures.sha256(served.map(\.line).joined(separator: "\n") + "\n")
        out.insert(contentsOf: [
            "L151-L1150 (1,000 levels) as LevelProvider.produce serves them (validator-gated generator + the SPEC.md §5.27 band gate, re-rolls ≤ \(LevelProvider.maxRolls) rolls)", "",
            "invalid \(invalid) · unsolved by the game's solver \(unsolved) · not won by the 0.6 s/tap driver (≥ 20 %) \(lost) · out of band \(outOfBand) · box counter > 99 \(boxOver) · route nearest/fallback \(badRoute) · seed ≠ rollSeed \(badSeed)",
            "routes: " + routes.map { "\($0.key) \($0.value)" }.joined(separator: ", "),
            "re-rolled (\(rerolled.count)): " + rerolled.map { "L\($0.n) (roll \($0.rec.roll))" }.joined(separator: " "),
            "second production (2 threads, reverse order): \(rerunDiffs.isEmpty ? "1000/1000 byte-identical" : "DIFFERS \(rerunDiffs)")",
            "repeats vs each other and L1-L150: exact \(exactRepeats.count) \(exactRepeats), translated/rotated/mirrored \(shapeRepeats.count) \(shapeRepeats)",
            "sha256 of the 1,000 canonical lines (schema 1, newline-joined): \(digest)",
            "production time, all 1,000 (rec.totalMs, release, sequential):      " + stats(served.map(\.rec.totalMs)),
            "production time, wall around produce():                               " + stats(served.map(\.wallMs)),
            "production time, the \(rerolled.count) re-rolled levels (all rolls included):  " + stats(rerolled.map(\.rec.totalMs)),
            "production time, levels served on their own seed:                     " + stats(served.filter { $0.rec.roll == 0 }.map(\.rec.totalMs)),
            ""], at: 0)
        C4Fixtures.evidence("c4c-endless-1000.txt", out.joined(separator: "\n"))
        C4Fixtures.evidence("c4c-endless-1000.jsonl", served.map(\.line).joined(separator: "\n") + "\n")
        XCTAssertEqual(invalid + unsolved + lost + outOfBand + boxOver + badRoute + badSeed, 0)
    }
}
