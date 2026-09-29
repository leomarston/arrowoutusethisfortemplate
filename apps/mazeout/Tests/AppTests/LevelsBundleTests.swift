import Foundation
import XCTest
import PathCore
@testable import ArrowOut

/// VERIFY V1 (SPEC-architecture §12.2 V1 `LevelsBundleTests`; SPEC.md §5.19, §5.23, §5.26, §5.28). The level content the
/// BUILT app ships (bundle/Levels, bundle/UI):
///  - every level file L1…L150 decodes, carries its own number, and C4's validator finds 0 errors on the whole folder
///    (schema, geometry, solvability — greedy + the HeadlessDriver —, unlock cards at first appearances, sessions/tutorials
///    pointing at real content, no board twice) with the bundle's sprites resolving;
///  - the library the app loads at boot has no problems, the "Levels 1-4" session pays 80, the tutorial and the unlock
///    cards sit where the rulings put them (Linked L7, Box L11, Pipe L21, Elevator L31, Door L33, Corner L70);
///  - the bundle equals design/levels.json (the content source of truth) level for level.
/// PUBLISH B0 (SPEC.md ruling 39 OD8, "STRIP provenance from every shipped file"; requirement change, logged in PLAN.md):
/// the bundle is the PUBLISH form, so the validator runs with `provenance: .publish` — every shipped board must carry NO
/// research capture and no "_" note (was: every recorded / video board must name its capture; that check now runs on
/// design/levels.json, the source, in PathCore's C4 suites and design/tools/validate_levels.py).
final class LevelsBundleTests: XCTestCase {

    private var folder: URL { Bundle.main.resourceURL!.appendingPathComponent("Levels") }

    func testEveryBundledLevelDecodesAndValidatesWithItsSprites() throws {
        let sprites = try SpriteCatalog.load(folder: Bundle.main.resourceURL!.appendingPathComponent("UI"))
        let (rules, problems) = RulesTuning.load(json: Tuning.load(bundle: .main).rules.data, overrides: [:])
        XCTAssertEqual(problems, [])
        let t0 = Date()
        let report = try Validator.checkFolder(folder, sprites: sprites,
                                               options: Validator.Options(randomOrders: 8, gameRules: true, rules: rules, provenance: .publish))
        let dt = Date().timeIntervalSince(t0)
        let errors = report.errors.map(\.description)
        v1Attach("validator", "levels \(report.levels.count) in \(String(format: "%.1f", dt)) s; errors \(errors.count); warnings \(report.warnings.count)\n"
                 + (errors + report.warnings.map(\.description)).joined(separator: "\n"))
        XCTAssertEqual(report.levels.count, 150, "L1-L150 are authored (SPEC.md §5.23)")
        XCTAssertEqual(errors, [], "validator errors on the shipped levels")
        XCTAssertTrue(report.levels.allSatisfy(\.isValid))
        // first appearances = the unlock levels (rulings 19 / 26)
        XCTAssertEqual(report.firstAppearance["linked"], 7)
        XCTAssertEqual(report.firstAppearance["box"], 11)
        XCTAssertEqual(report.firstAppearance["pipe"], 21)
        XCTAssertEqual(report.firstAppearance["elevator"], 31)
        XCTAssertEqual(report.firstAppearance["door"], 33)
        XCTAssertEqual(report.firstAppearance["corner"], 70)
    }

    func testTheLibraryTheAppLoadsHasTheRuledSessionTutorialAndCards() throws {
        let lib = try LevelLibrary.load(folder: folder)
        XCTAssertEqual(lib.problems, [])
        XCTAssertEqual(lib.authoredCount, 150)
        let s = lib.session(containing: 1)
        XCTAssertEqual(s.levels, [1, 2, 3, 4], "\"Levels 1-4\" is one session of four boards")
        XCTAssertEqual(lib.session(containing: 3).levels, [1, 2, 3, 4])
        XCTAssertEqual(lib.nextLevel(after: s), 5)
        let sessions = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: folder.appendingPathComponent("sessions.json"))) as? [String: Any])
        let l14 = try XCTUnwrap((sessions["sessions"] as? [[String: Any]])?.first)
        XCTAssertEqual(l14["reward"] as? Int, 80, "the session pays 80 (CONSISTENCY X-14/X-15)")
        XCTAssertEqual(l14["hud_label"] as? String, "Levels 1-4")
        XCTAssertEqual(l14["panel_label"] as? String, "Level 1-4")
        let tut = lib.tutorials(level: 1, stage: 0)
        XCTAssertEqual(tut.map(\.id.rawValue), ["tapToMove"])
        XCTAssertEqual(tut.first?.caption, "Tap to move!")
        let cards = lib.unlocks.map { "\($0.feature.rawValue)@\($0.level)" }
        XCTAssertEqual(cards, ["linked@7", "box@11", "pipe@21", "elevator@31", "door@33", "corner@70"])
        XCTAssertEqual(lib.unlock(at: 33)?.title, "Door!")
        XCTAssertEqual(lib.unlock(at: 33)?.card, "Collect the KEY to open the DOOR!", "ruling 19's Door card")
        XCTAssertEqual(lib.unlock(at: 11)?.card, "Clear required amount of arrows to break the BOX!")
        XCTAssertEqual(lib.unlock(at: 70)?.card, "Arrows turn when they hit the CORNER!")
        for u in lib.unlocks { XCTAssertEqual(try lib.loadAuthored(u.level).unlock, u.feature, "L\(u.level) carries its card") }
        // tags of the video range (ruling 19): Hard L19, L25; Super Hard L29
        XCTAssertEqual(try lib.loadAuthored(19).tag, .hard)
        XCTAssertEqual(try lib.loadAuthored(25).tag, .hard)
        XCTAssertEqual(try lib.loadAuthored(29).tag, .superHard)
        for n in 1...150 { XCTAssertEqual(try lib.loadAuthored(n).hearts, 3, "L\(n) hearts") }
    }

    /// FIX-2 lane B (N-01, the review's release tell): every level file the BUILT app carries is the publish form — no
    /// research key at the top level (`capture`, `source` recorded / video, `metrics` with the bot's `bot_time_left`, "_"
    /// notes) and no "bot_" anywhere; each decodes as a designed board with no capture and no metrics. The same rule over the
    /// pre-N-01 files (build/p/FIX2/B-R/orig/Levels) flags all 150 (build/p/FIX2/B-R/n01-negative.txt).
    func testEveryShippedLevelFileIsThePublishForm() throws {
        let names = try FileManager.default.contentsOfDirectory(atPath: folder.path).filter { $0.hasPrefix("level_") }.sorted()
        XCTAssertEqual(names.count, 150)
        var bad: [String] = []
        for name in names {
            let data = try Data(contentsOf: folder.appendingPathComponent(name))
            let o = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any], name)
            let research = o.keys.filter { ["capture", "source", "metrics"].contains($0) || $0.hasPrefix("_") }.sorted()
            if !research.isEmpty { bad.append("\(name): \(research)") }
            if String(decoding: data, as: UTF8.self).contains("bot_") { bad.append("\(name): bot_") }
            let l = try JSONDecoder().decode(LevelSpec.self, from: data)
            if l.source != .designed || l.capture != nil || l.metrics != nil { bad.append("\(name): decodes with provenance") }
        }
        XCTAssertEqual(bad, [], "research keys in the shipped levels")
    }

    /// design/levels.json is the source of truth (SPEC.md §5.23): the bundle is its output, level for level.
    func testTheBundleEqualsDesignLevelsJSON() throws {
        let data = try Data(contentsOf: V1Repo.url("design/levels.json"))
        let doc = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let raw = try XCTUnwrap(doc["levels"] as? [[String: Any]])
        XCTAssertEqual(raw.count, 150)
        let lib = try LevelLibrary.load(folder: folder)
        var differ: [Int] = []
        for r in raw {
            // FIX-3 B (SPEC.md ruling 55(c)): design/levels.json spells `source` the content pipeline's way ("recorded" /
            // "video"), which since the neutral LevelSource rename is a raw value of the macOS tools' PathCore only — this
            // iOS build cannot decode it. The comparison below never read `source`, so dropping it first keeps the test as
            // strong as it was (every compared field still comes from the design file); the neutral names are pinned below.
            var r = r
            r["source"] = nil
            let d = try JSONSerialization.data(withJSONObject: r)
            let spec = try JSONDecoder().decode(LevelSpec.self, from: d)
            let shipped = try lib.loadAuthored(spec.level)
            if shipped.arrows != spec.arrows || shipped.obstacles != spec.obstacles || shipped.cols != spec.cols
                || shipped.rows != spec.rows || shipped.mask != spec.mask || shipped.timerSeconds != spec.timerSeconds
                || shipped.tag != spec.tag || shipped.unlock != spec.unlock || shipped.hearts != spec.hearts {
                differ.append(spec.level)
            }
        }
        XCTAssertEqual(differ, [], "bundled levels that differ from design/levels.json")
    }

    /// FIX-3 B (SPEC.md ruling 55(c), V1A-G8-3): the app's LevelSource names no way a board was made — neutral case names
    /// AND raw values in this (iOS) build, where the content pipeline's spellings are not compiled (PC_RESEARCH is macOS-
    /// only; PathCore's APISurfaceTests pin the macOS spellings) — so a level that says "recorded" / "video" does not even
    /// decode here, while every shipped level (no `source`) decodes as .designed (testEveryShippedLevelFileIsThePublishForm).
    func testTheShippedLevelSourceNamesAreNeutral() throws {
        XCTAssertEqual(LevelSource.allCases, [.authored, .crafted, .designed, .generated])
        XCTAssertEqual(LevelSource.allCases.map(\.rawValue), ["authored", "crafted", "designed", "generated"])
        for word in ["recorded", "video"] {
            XCTAssertNil(LevelSource(rawValue: word), word)
            let json = Data(#"{"level":1,"source":"\#(word)","cols":2,"rows":1,"timer_s":180,"hearts":3,"tag":"normal","arrows":[{"id":0,"cells":[[0,0],[1,0]],"dir":"right"}],"obstacles":[]}"#.utf8)
            XCTAssertThrowsError(try JSONDecoder().decode(LevelSpec.self, from: json), word)
        }
        // control: the same board with a neutral source, and without one, decodes
        let ok = #"{"level":1,"cols":2,"rows":1,"timer_s":180,"hearts":3,"tag":"normal","arrows":[{"id":0,"cells":[[0,0],[1,0]],"dir":"right"}],"obstacles":[]}"#
        XCTAssertEqual(try JSONDecoder().decode(LevelSpec.self, from: Data(ok.utf8)).source, .designed)
        let crafted = ok.replacingOccurrences(of: #"{"level":1,"#, with: #"{"level":1,"source":"crafted","#)
        XCTAssertEqual(try JSONDecoder().decode(LevelSpec.self, from: Data(crafted.utf8)).source, .crafted)
    }

    /// The boards past the authored end come from the runtime generator (SPEC.md §5.23/§5.27): L151 is served, valid and
    /// deterministic (two providers agree).
    func testTheFirstGeneratedLevelIsServedValidAndDeterministic() throws {
        let lib = try LevelLibrary.load(folder: folder)
        let a = LevelProvider(library: lib).level(151)
        let b = LevelProvider(library: lib).level(151)
        XCTAssertEqual(a.level, 151)
        XCTAssertEqual(a.arrows, b.arrows, "deterministic per level number")
        XCTAssertEqual(a.obstacles, b.obstacles)
        let errors = Validator.check(a, sprites: try SpriteCatalog.load(folder: Bundle.main.resourceURL!.appendingPathComponent("UI")))
            .filter { $0.severity == .error }
        XCTAssertEqual(errors.map(\.description), [])
    }

    /// FIX-2 lane B (L29, G4(c) release blocker): the Release bundle drops BoardLab's lab fixtures (project.yml Release
    /// EXCLUDED_SOURCE_FILE_NAMES = lab_L*.json labb_L*.json — verbatim phone readings with research/ capture paths;
    /// release_gates.sh gate 7 proves they are gone). That is safe only while every numbered lab name resolves to the SHIPPED
    /// level first: each LabBoards "L0NN" loads exactly Levels/level_00NN.json (equal LevelSpec, no capture) — in this Debug
    /// bundle AND in a bundle shaped like Release (Levels/ and no fixture) — and the crafted boards the warm-up ('warmfx') and
    /// the input tests use need no file at all.
    func testLabBoardNamesResolveToTheShippedLevels() throws {
        let numbered = LabBoards.names.filter { $0.first == "L" }
        XCTAssertGreaterThanOrEqual(numbered.count, 18, "L001…L054")
        XCTAssertTrue(numbered.contains("L032") && numbered.contains("L050"))
        // a Release-shaped bundle: the shipped Levels/ only
        let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("fix2-release-shape-\(UUID().uuidString).bundle")
        try FileManager.default.createDirectory(at: tmp, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: tmp) }
        try FileManager.default.copyItem(at: folder, to: tmp.appendingPathComponent("Levels"))
        let releaseShape = try XCTUnwrap(Bundle(url: tmp))
        XCTAssertNil(releaseShape.url(forResource: "lab_L032", withExtension: "json"), "no fixture in the Release shape")
        for name in numbered {
            let n = try XCTUnwrap(Int(name.dropFirst()), name)
            let file = String(format: "level_%04d", n)
            let url = try XCTUnwrap(Bundle.main.url(forResource: file, withExtension: "json", subdirectory: "Levels"), "\(file) ships")
            let shipped = try JSONDecoder().decode(LevelSpec.self, from: Data(contentsOf: url))
            XCTAssertNil(shipped.capture, "\(file): the publish form carries no capture")
            for (bundle, label) in [(Bundle.main, "Debug"), (releaseShape, "Release shape")] {
                let lab = try XCTUnwrap(LabBoards.level(name, bundle: bundle), "\(name) (\(label))")
                XCTAssertEqual(lab, shipped, "\(name) (\(label)) resolves to Levels/\(file).json, not a lab fixture")
                XCTAssertNil(lab.capture, "\(name) (\(label)): no research capture")
            }
        }
        for name in ["warmfx", "warm", "hit", "synth40", "synth12", "corner"] {
            XCTAssertNotNil(LabBoards.level(name, bundle: releaseShape), "\(name) is crafted in code")
        }
    }
}
