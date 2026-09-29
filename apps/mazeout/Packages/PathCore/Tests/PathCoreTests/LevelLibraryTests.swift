import XCTest
import Foundation
@testable import PathCore

/// §4.14 / §4.17 LevelLibraryTests (C4): `pclevels bundle` (ContentBundle) writes App/Resources/Levels from
/// design/levels.json (pinned: Fixtures/content/levels.json) byte for byte and the library loads it; every authored level is valid and won by the driver; the
/// LevelProvider serves authored levels, then validated generated ones, off the main thread, one level ahead.
final class LevelLibraryTests: XCTestCase {

    func tempDir(_ name: String) -> URL {
        let u = FileManager.default.temporaryDirectory.appendingPathComponent("c4-\(name)-\(UUID().uuidString)")
        try? FileManager.default.createDirectory(at: u, withIntermediateDirectories: true)
        return u
    }

    func testBundleIsByteForByteAndLoads() throws {
        let files = try ContentBundle.files(of: C4Fixtures.doc)
        XCTAssertEqual(files.count, 154)
        for (n, line) in C4Fixtures.rawLines {
            XCTAssertEqual(files[LevelLibrary.fileName(level: n)], Data((line + "\n").utf8), "L\(n)")
        }
        let a = tempDir("a"), b = tempDir("b")
        defer { try? FileManager.default.removeItem(at: a); try? FileManager.default.removeItem(at: b) }
        let s = try ContentBundle.write(C4Fixtures.doc, to: a)
        try ContentBundle.write(C4Fixtures.doc, to: b)
        XCTAssertEqual(s.levels, 150)
        XCTAssertEqual(s.authoredEnd, 150)
        for name in s.files {
            XCTAssertEqual(try Data(contentsOf: a.appendingPathComponent(name)), try Data(contentsOf: b.appendingPathComponent(name)), name)
        }
        let lib = try LevelLibrary.load(folder: a)
        XCTAssertEqual(lib.authoredCount, 150)
        XCTAssertEqual(lib.problems, [])
        XCTAssertEqual(lib.sessions.map(\.id), ["L1-4"])
        XCTAssertEqual(lib.unlocks.map(\.level), [7, 11, 21, 31, 33, 70])     // recast: + the Corner card at L70
        XCTAssertEqual(lib.tutorials.map(\.id.rawValue), ["tapToMove"])
        XCTAssertEqual(lib.curve, .default)
        XCTAssertEqual(lib.authored(65), C4Fixtures.level(65))
        XCTAssertEqual(try Data(contentsOf: a.appendingPathComponent("sessions.json")).prefix(24), Data("{\"schema\":1,\"sessions\":[".utf8))
    }

    /// When CONTENT has written App/Resources/Levels: the folder is the PUBLISH form of design/levels.json (PUBLISH B0; SPEC.md
    /// ruling 39 OD8 "STRIP provenance from every shipped file" — a requirement change, logged in PLAN.md). Was: "every file
    /// is one of the two `pclevels bundle` forms (as-is, or C1's encoded form)", both of which ship each board's research
    /// capture and "_" notes. Now, at least as strict: the folder holds exactly ContentBundle `.publish`'s files, every one
    /// byte for byte (tools/levels/lvtool `bundle --publish` writes the same bytes), each level decodes to the pinned level
    /// with only its capture removed (every gameplay field equal), and no level file carries a capture or a "_" key.
    /// FIX-2 lane B (N-01, the triage's plan): the publish form also drops `source` (recorded / video: where a board was read)
    /// and `metrics` (the bot's measurements, `bot_time_left`) — re-stated at least as strictly: every level decodes to the
    /// pinned level with capture, source and metrics removed (`LevelJSON.publishModel`: every gameplay field still equal),
    /// no level file carries any of the four, and the counts of what was stripped are pinned (99 captures, 99 research
    /// sources, 150 metrics blocks).
    func testTheAppBundleFolderIsABundleOfLevelsJSON() throws {
        let folder = C4Fixtures.appRoot.appendingPathComponent("App/Resources/Levels")
        let present = ((try? FileManager.default.contentsOfDirectory(atPath: folder.path)) ?? []).filter { $0.hasSuffix(".json") }
        guard !present.isEmpty else { throw XCTSkip("App/Resources/Levels holds no level files yet (CONTENT's L1/L2)") }
        let publish = try ContentBundle.files(of: C4Fixtures.doc, form: .publish)
        XCTAssertEqual(Set(present), Set(publish.keys), "the folder holds exactly the bundle's files")
        var stripped = 0, sources = 0, metrics = 0
        for name in present.sorted() {
            let d = try Data(contentsOf: folder.appendingPathComponent(name))
            XCTAssertEqual(d, publish[name], "\(name) is not the publish form of design/levels.json")
            if let n = LevelLibrary.levelNumber(fileName: name) {
                let pinned = C4Fixtures.level(n)
                if pinned.capture != nil { stripped += 1 }
                if pinned.source == .authored || pinned.source == .crafted { sources += 1 }
                if pinned.metrics != nil { metrics += 1 }
                let want = LevelJSON.publishModel(pinned)
                XCTAssertEqual(want.arrows, pinned.arrows, name)
                XCTAssertEqual(want.obstacles, pinned.obstacles, name)
                XCTAssertEqual(try LevelJSON.decodeBundle(d), want, name)
                let keys = try ContentJSON.parse(d).objectPairs?.map(\.0) ?? []
                XCTAssertFalse(keys.contains("capture"), "\(name) ships its capture")
                XCTAssertFalse(keys.contains("source"), "\(name) ships its source")
                XCTAssertFalse(keys.contains("metrics"), "\(name) ships its metrics")
                XCTAssertEqual(keys.filter { $0.hasPrefix("_") }, [], "\(name) ships comment keys")
                XCTAssertFalse(String(decoding: d, as: UTF8.self).contains("bot_"), "\(name) names the bot")
            }
        }
        XCTAssertEqual(stripped, 99, "the recorded / video boards: the 99 captures the publish form strips")
        XCTAssertEqual(sources, 99, "the 99 recorded / video sources the publish form strips")
        XCTAssertEqual(metrics, 150, "every level's metrics block, stripped")
        let lib = try LevelLibrary.load(folder: folder)
        XCTAssertEqual(lib.problems, [])
        XCTAssertEqual(lib.curve, .default, "the bundled curve.json is the compiled curve")
        C4Fixtures.evidence("c4-app-bundle-forms.txt", "App/Resources/Levels: \(present.count) files = ContentBundle .publish of design/levels.json; \(stripped) captures, \(sources) sources, \(metrics) metrics stripped")
    }

    func testSampleOfAuthoredLevelsIsWonByTheDriver() {
        // PUBLISH B0 (level re-order): the list names BOARDS by research slot; each is played at the slot it ships at
        for n in [1, 2, 3, 4, 7, 11, 21, 31, 33, 44, 59, 63, 64, 69, 70, 79, 100, 150].map(C4Fixtures.slot(research:)) {
            let l = C4Fixtures.level(n)
            var c = DriverConfig(tapInterval: 0.6)
            c.recordEvents = false
            let r = HeadlessDriver.play(level: l, config: c)
            XCTAssertTrue(r.won, "L\(n)")
            XCTAssertGreaterThanOrEqual(r.timeLeftFraction, 0.2, "L\(n)")
        }
    }

    // MARK: LevelProvider

    func library(_ upTo: Int) -> LevelLibrary {
        let doc = C4Fixtures.doc
        let unlocks = (try? FeatureUnlock.decodeList(ContentJSON.data(doc["unlocks"]!))) ?? []
        return LevelLibrary(levels: Array(C4Fixtures.allLevels.prefix(upTo)), sessions: [], unlocks: unlocks,
                            curveJSON: ContentJSON.data(doc["curve"]!))
    }

    func testProviderServesAuthoredThenGeneratedOneLevelAhead() throws {
        let p = LevelProvider(library: library(150))
        XCTAssertEqual(p.authoredEnd, 150)
        XCTAssertEqual(p.level(150), C4Fixtures.level(150))                   // authored: as bundled
        XCTAssertTrue(p.isReady(150))
        XCTAssertFalse(p.isReady(151))
        let produced = expectation(description: "L151 produced off the main thread")
        let offMain = Locked(false)
        p.onProduced = { rec in
            if rec.level == 151 { offMain.set(!Thread.isMainThread); produced.fulfill() }
        }
        p.levelStarted(150)                                                    // one level ahead: L151
        wait(for: [produced], timeout: 240)
        XCTAssertTrue(offMain.get())
        XCTAssertTrue(p.isReady(151))
        let l = p.level(151)
        XCTAssertEqual(l.level, 151)
        XCTAssertEqual(l.source, .generated)
        XCTAssertEqual(l.seed, PathRandom.levelSeed(level: 151, salt: CurveSpec.default.salt))
        XCTAssertTrue(Validator.checkLevel(l, raw: nil, sprites: nil, options: Validator.Options()).isValid)
        let rec = try XCTUnwrap(p.records.first { $0.level == 151 })
        XCTAssertEqual(rec.route, .generated)
        XCTAssertEqual(rec.seedsTried, 1)
        // the same board for every player: a second provider, and the generator itself
        var ref = try Generator.generate(level: 151, curve: .default).level
        ref.source = .generated
        XCTAssertEqual(l, ref)
        XCTAssertEqual(LevelProvider(library: library(150)).level(151), l)
    }

    func testProviderGeneratesPastAShorterBundleAndCachesLRU() {
        // content recast 2: L62-L105 are phone recordings (or stand-ins); the first designed level is L106
        let p = LevelProvider(library: library(105), cacheLimit: 2)
        XCTAssertEqual(p.authoredEnd, 105)
        XCTAssertTrue(p.isGenerated(106))
        let l106 = p.level(106)
        var expected = C4Fixtures.level(106)                                  // the designed L106 IS the generated L106
        expected.source = .generated
        XCTAssertEqual(l106, expected)
        XCTAssertTrue(p.isReady(106))
        _ = p.level(135)
        _ = p.level(150)
        XCTAssertFalse(p.isReady(106))                                        // evicted (limit 2)
        XCTAssertTrue(p.isReady(150))
    }

    /// The reference's own L517 is a dead end (content recast 2's curve, 2026-09-25; its other one, L416, is refused too but its next attempt falls outside the bands and is re-rolled; was L240 on recast 1's curve, L630 on the 09:01 curve) (validate_levels.py says so too, Fixtures/c4_runtime_reference.json): the
    /// gate refuses it and the provider serves the next valid attempt instead.
    func testProviderRefusesTheReferenceDeadEnd() throws {
        let refRow = try XCTUnwrap(C4Fixtures.json("c4_runtime_reference.json")["levels"]?.arrayValue?.first { $0["level"]?.intValue == 517 })
        let pyErrors = refRow["errors"]!.arrayValue!.map { $0.stringValue! }
        XCTAssertEqual(pyErrors, ["L517: dead end: a random play order gets stuck with 5 arrows left"])
        let ref = try Generator.generate(level: 517, curve: .default)
        XCTAssertEqual(C4Fixtures.sha256(ContentJSON.line(ref.level, schema: false)), refRow["sha256"]!.stringValue!)
        XCTAssertEqual(Validator.checkLevel(ref.level, raw: nil, sprites: nil, options: Validator.Options(gameRules: false)).errors.map(\.description),
                       pyErrors)
        let (served, rec) = LevelProvider.produce(517, curve: .default, library: nil, options: Validator.Options())
        XCTAssertEqual(rec.route, .generated)
        XCTAssertTrue(rec.refused.contains { $0.contains("gate: dead end") }, "\(rec.refused)")
        XCTAssertTrue(Validator.checkLevel(served, raw: nil, sprites: nil, options: Validator.Options()).isValid)
        XCTAssertNotEqual(served.arrows, ref.level.arrows)
        XCTAssertEqual(served.seed, ref.level.seed)                             // same seed: the next attempt fork
    }

    func testProviderNeverCrashes() {
        // a curve whose every candidate fails (no silhouette space: 1 attempt, impossible growth) falls back to the
        // nearest authored level of the same tag, renumbered, and says so
        var bad = CurveSpec.default
        bad.attempts = 0
        let (l, rec) = LevelProvider.produce(154, curve: bad, library: library(150), options: Validator.Options())
        XCTAssertEqual(rec.route, .fallback)
        XCTAssertEqual(l.level, 154)
        XCTAssertEqual(l.tag, .hard)
        XCTAssertEqual(l.source, .generated)
        XCTAssertEqual(l.arrows, C4Fixtures.level(144).arrows)                // L144: the last authored Hard level
        let (m, rec2) = LevelProvider.produce(155, curve: bad, library: nil, options: Validator.Options())
        XCTAssertEqual(rec2.route, .fallback)
        XCTAssertTrue(Validator.checkLevel(m, raw: nil, sprites: nil, options: Validator.Options()).isValid)
    }
}

/// A tiny thread-safe box for test flags.
final class Locked<T>: @unchecked Sendable {
    private var v: T
    private let l = NSLock()
    init(_ v: T) { self.v = v }
    func get() -> T { l.lock(); defer { l.unlock() }; return v }
    func set(_ x: T) { l.lock(); v = x; l.unlock() }
}

final class C4FullLibraryTests: XCTestCase {
    override func setUpWithError() throws {
        guard C4Fixtures.full else { throw XCTSkip("PC_C4_FULL=1") }
    }

    func testEveryAuthoredLevelIsValidAndWonByTheDriver() {
        var lines = ["L1-L150: Validator (content + game rules) and the HeadlessDriver at 0.6 s per tap", ""]
        for l in C4Fixtures.allLevels {
            let rep = Validator.checkLevel(l, raw: nil, sprites: nil, options: Validator.Options())
            var c = DriverConfig(tapInterval: 0.6)
            c.recordEvents = false
            let r = HeadlessDriver.play(level: l, config: c)
            XCTAssertTrue(rep.isValid, "L\(l.level): \(rep.errors)")
            XCTAssertTrue(r.won, "L\(l.level)")
            lines.append(String(format: "L%d  %@  %@  time left %.1f / %d s (%.0f%%)  taps %d", l.level, rep.isValid ? "valid" : "INVALID",
                                r.won ? "WON" : "NOT WON", r.remaining, l.timerSeconds, 100 * r.timeLeftFraction, r.taps))
        }
        C4Fixtures.evidence("c4-authored-levels-driver.txt", lines.joined(separator: "\n"))
    }
}
