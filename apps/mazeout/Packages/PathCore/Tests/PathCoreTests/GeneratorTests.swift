import XCTest
import Foundation
import CryptoKit
@testable import GameCore
@testable import ArrowEscape

/// C4 test helpers (GeneratorTests, ValidatorTests, SolverTests, LevelLibraryTests). Paths from #filePath (no SwiftPM
/// resources, §2.4); evidence goes to $PC_EVIDENCE_DIR when set (build/c4/ in C4 runs).
/// The FULL acceptance runs (every designed level, 500 runtime levels against the Python reference, the timing) are
/// gated by PC_C4_FULL=1 and meant for a release build:
///   PC_C4_FULL=1 swift test -c release -Xswiftc -enable-testing --filter 'C4Full'
enum C4Fixtures {
    static var testsDir: URL { URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent() }
    /// apps/mazeout: the first ancestor holding design/levels.json (Packages/PathCore/Tests → ../../..).
    static let appRoot: URL = {
        var u = testsDir
        for _ in 0..<6 {
            u = u.deletingLastPathComponent()
            if FileManager.default.fileExists(atPath: u.appendingPathComponent("design/levels.json").path) { return u }
        }
        return testsDir.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    }()
    static func fixture(_ name: String) -> URL { testsDir.appendingPathComponent("Fixtures/\(name)") }
    /// The content is PINNED (hermetic, like C1's Fixtures/research): Fixtures/content/levels.json = design/levels.json and
    /// Fixtures/content/designed.json = design/tools/work/designed.json (gitignored there) as of the last
    /// `python3 design/tools/pin_fixtures.py` (MANIFEST.txt; `--check` says whether the pins are current).
    static var levelsJSON: URL { fixture("content/levels.json") }
    static var designedJSON: URL { fixture("content/designed.json") }

    static var full: Bool { ProcessInfo.processInfo.environment["PC_C4_FULL"] == "1" }

    /// design/levels.json, parsed once (lexemes kept).
    static let doc: JSONValue = {
        do { return try ContentJSON.parse(Data(contentsOf: levelsJSON)) } catch { fatalError("Fixtures/content/levels.json: \(error)") }
    }()

    /// The pinned levels.json's level lines exactly as written (one per level, the file's own bytes).
    static let rawLines: [Int: String] = {
        let text = (try? String(contentsOf: levelsJSON, encoding: .utf8)) ?? ""
        var out: [Int: String] = [:]
        for line in text.split(separator: "\n", omittingEmptySubsequences: false) where line.hasPrefix("    {") {
            var s = String(line.dropFirst(4))
            if s.hasSuffix(",") { s.removeLast() }
            if let v = try? ContentJSON.parse(s), let n = v["level"]?.intValue { out[n] = s }
        }
        return out
    }()

    static func level(_ n: Int) -> LevelSpec {
        let v = doc["levels"]!.arrayValue!.first { $0["level"]?.intValue == n }!
        return try! JSONDecoder().decode(LevelSpec.self, from: ContentJSON.data(v))
    }

    static let allLevels: [LevelSpec] = (doc["levels"]?.arrayValue ?? []).map {
        try! JSONDecoder().decode(LevelSpec.self, from: ContentJSON.data($0))
    }

    /// PUBLISH B0 (item 12; SPEC.md rulings 37e + 39 OD8; design/publish/level-reorder.md §9): since the level re-order
    /// (design/level-order.json) a level NUMBER names a slot, not a board. A board is named by its RESEARCH SLOT, read from
    /// its own provenance in the pinned levels.json (design/tools/level_order.py `rslot`, ported): a phone board by the
    /// number in its capture (research/shots/NNN-L0nn-…, research/bot/tmp/L0nn-…), a video board by the video's number
    /// (research/video-frames/V1|V2/L0nn-…), a V2 substitute / designed stand-in by the phone slot its `_from` names ("the
    /// phone's L81"); a generated board (L106-L150) has none and never moves. research slot → the slot it ships at.
    static let researchSlots: [Int: Int] = {
        func first(_ pattern: String, _ s: String, group: Int) -> Int? {
            let rx = try! NSRegularExpression(pattern: pattern)
            guard let m = rx.firstMatch(in: s, range: NSRange(s.startIndex..., in: s)),
                  let r = Range(m.range(at: group), in: s) else { return nil }
            return Int(s[r])
        }
        var out: [Int: Int] = [:]
        for v in doc["levels"]?.arrayValue ?? [] {
            let n = v["level"]!.intValue!
            let src = v["source"]?.stringValue ?? "", cap = v["capture"]?.stringValue ?? "", from = v["_from"]?.stringValue ?? ""
            let r: Int?
            if from.hasPrefix("V2-L") || from.hasPrefix("designed stand-in") { r = first(#"the phone's L0*(\d+)\b"#, from, group: 1) }
            else if src == "recorded" { r = first(#"[/-]L0*(\d+)-"#, cap, group: 1) }
            else if src == "video" { r = first(#"/(V[12])/L0*(\d+)-"#, cap, group: 2) }
            else { r = nil }
            guard let r else { continue }
            precondition(out[r] == nil, "research slot \(r) named twice (L\(out[r]!) and L\(n))")
            out[r] = n
        }
        return out
    }()

    /// The slot the board of research slot `n` ships at (a generated board past L105: `n` itself, it never moves).
    static func slot(research n: Int) -> Int {
        if let s = researchSlots[n] { return s }
        precondition(n > 105, "no board has research slot \(n)")
        return n
    }

    /// The pinned designed.json (the reference generator's levels + infos of the designed range L106-L150 since content recast 2).
    static let designed: JSONValue? = {
        guard let d = try? Data(contentsOf: designedJSON) else { return nil }
        return try? ContentJSON.parse(d)
    }()

    static func json(_ name: String) throws -> JSONValue { try ContentJSON.parse(Data(contentsOf: fixture(name))) }

    static func sha256(_ s: String) -> String { SHA256.hash(data: Data(s.utf8)).map { String(format: "%02x", $0) }.joined() }

    static func evidence(_ name: String, _ text: String) {
        guard let dir = ProcessInfo.processInfo.environment["PC_EVIDENCE_DIR"], !dir.isEmpty else { return }
        let url = URL(fileURLWithPath: dir).appendingPathComponent(name)
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? Data(text.utf8).write(to: url)
    }

    /// Thread CPU seconds (timing under a loaded machine: wall time and CPU time are both reported).
    static func cpuNow() -> Double {
        var t = timespec()
        clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t)
        return Double(t.tv_sec) + Double(t.tv_nsec) / 1e9
    }

    static func wallNow() -> Double { Double(DispatchTime.now().uptimeNanoseconds) / 1e9 }

    /// A diverse, cheap sample of designed levels (content recast 2: v552 L84-L105 are recorded, the designed range is
    /// L106-L150): pipe (L106), elevator + box (107), Super Hard box with a 2:00 template timer (109), corners on two sides
    /// (110), Hard door band with a 3:00 template timer (114), box staircase + tape with a rejected candidate (115), pipe +
    /// corners on two sides (116), door band + corner with rejected candidates (117), cross silhouette (118), Hard door with
    /// the 2:00 template timer of v552's L84 (124), oval silhouette (135), elevator + corners (140), corner (150). None needed
    /// the gate (only L136 did).
    static let sample = [106, 107, 109, 110, 114, 115, 116, 117, 118, 124, 135, 140, 150]

    /// The designed levels whose reference winner the validator refused (their line = the GATED generator's).
    static let gated: Set<Int> = {
        Set((designed?["infos"]?.arrayValue ?? []).compactMap { i in
            (i["rejected"]?.arrayValue ?? []).contains { $0.stringValue?.hasPrefix("gate: ") == true } ? i["level"]?.intValue : nil
        })
    }()

    /// build_levels.py's gate: validate_levels.check_level (content rules, no game rules) on the candidate as "generated".
    static let contentGate: Generator.Gate = { cand in
        var c = cand
        c.source = .generated
        let rep = Validator.checkLevel(c, raw: nil, sprites: nil, options: Validator.Options(gameRules: false))
        return rep.isValid ? nil : rep.errors.first.map(\.message) ?? "invalid"
    }

    /// Level n as the designed range holds it: the reference, gated where build_levels gated it.
    static func designedLevel(_ n: Int, curve: CurveSpec = .default) throws -> Generator.Output {
        gated.contains(n) ? try Generator.generate(level: n, curve: curve, seed: PathRandom.levelSeed(level: n, salt: curve.salt), gate: contentGate)
                          : try Generator.generate(level: n, curve: curve)
    }

    /// First and last designed level of the pinned content.
    static let designedRange: ClosedRange<Int> = {
        let ns = (designed?["levels"]?.arrayValue ?? []).compactMap { $0["level"]?.intValue }
        return (ns.min() ?? 106)...(ns.max() ?? 150)
    }()
}

final class GeneratorTests: XCTestCase {

    // MARK: the curve and the numeric primitives

    func testCompiledCurveIsTheLevelsJSONCurve() throws {
        let c = try XCTUnwrap(C4Fixtures.doc["curve"])
        XCTAssertEqual(ContentJSON.write(CurveSpec.default.json), ContentJSON.write(c))
        let parsed = try CurveSpec(json: c)
        XCTAssertEqual(parsed, .default)
        XCTAssertEqual(parsed.salt, 15177990143040770677)
        XCTAssertEqual(parsed.templates.count, 70)             // content recast 2: L30-L99, 7 decade slots
        XCTAssertEqual(parsed.lengths.first?.length, 2)
        XCTAssertEqual(parsed.attempts, 10)
        XCTAssertEqual(parsed.authoredEnd, 150)
    }

    func testLevelSeedsMatchPython() throws {
        let x = try C4Fixtures.json("c4_reference_extras.json")
        for s in try XCTUnwrap(x["level_seeds"]?.arrayValue) {
            XCTAssertEqual(PathRandom.levelSeed(level: s["level"]!.intValue!, salt: CurveSpec.default.salt), s["seed"]!.uint64Value!)
        }
    }

    func testPythonRoundAndRepr() throws {
        let x = try C4Fixtures.json("c4_reference_extras.json")
        let rows = try XCTUnwrap(x["rounds"]?.arrayValue)
        XCTAssertGreaterThan(rows.count, 150)
        for r in rows {
            let v = Double(r["x"]!.stringValue!)!
            XCTAssertEqual(ContentJSON.pyRepr(v), r["repr"]!.stringValue!, "repr(\(v))")
            XCTAssertEqual(ContentJSON.pyRepr(ContentJSON.pyRound(v, 1)), r["r1"]!.stringValue!, "round(\(v), 1)")
            XCTAssertEqual(ContentJSON.pyRepr(ContentJSON.pyRound(v, 3)), r["r3"]!.stringValue!, "round(\(v), 3)")
        }
    }

    func testSilhouettesMatchPython() throws {
        let x = try C4Fixtures.json("c4_reference_extras.json")
        let masks = try XCTUnwrap(x["masks"]?.arrayValue)
        XCTAssertEqual(masks.count, 32)
        for m in masks {
            let W = m["cols"]!.intValue!, H = m["rows"]!.intValue!, shape = m["shape"]!.stringValue!
            let flags = Silhouettes.mask(shape, cols: W, rows: H)
            let rows = (0..<H).map { r in String((0..<W).map { flags[r * W + $0] ? "#" : "." }) }
            XCTAssertEqual(rows, m["rows_text"]!.arrayValue!.map { $0.stringValue! }, "\(shape) \(W)x\(H)")
        }
    }

    func testCanonicalJSONRoundTripsEveryLevelLine() throws {
        XCTAssertEqual(C4Fixtures.rawLines.count, 150)
        for (n, line) in C4Fixtures.rawLines {
            XCTAssertEqual(ContentJSON.write(try ContentJSON.parse(line)), line, "L\(n)")
        }
    }

    func testTargetsAndPlansMatchTheReferenceInfos() throws {
        let d = try XCTUnwrap(C4Fixtures.designed, "Fixtures/content/designed.json (design/tools/pin_fixtures.py)")
        for info in try XCTUnwrap(d["infos"]?.arrayValue) {
            let n = info["level"]!.intValue!
            let t = try Generator.target(.default, n)
            let rt = info["target"]!
            XCTAssertEqual([t.units, t.rounds, t.free, t.cols, t.rows, t.template, t.templateTimer, t.pos],
                           ["units", "rounds", "free", "cols", "rows", "template", "template_timer", "pos"].map { rt[$0]!.intValue! }, "L\(n)")
            XCTAssertEqual(t.tag.rawValue, rt["tag"]!.stringValue!)
            let plan = try Generator.obstaclePlan(.default, n, Generator.Rng(PathRandom(seed: PathRandom.levelSeed(level: n, salt: CurveSpec.default.salt)).fork("plan")))
            XCTAssertEqual(plan, info["planned"]!.arrayValue!.map { $0.stringValue! }, "L\(n)")
        }
    }

    // MARK: byte for byte (sample; the full range is C4FullTests)

    func testSampleOfDesignedLevelsIsByteForByte() throws {
        for n in C4Fixtures.sample {
            let o = try Generator.generate(level: n, curve: .default)
            let expected = try XCTUnwrap(C4Fixtures.rawLines[n])
            XCTAssertEqual(ContentJSON.line(o.level, schema: true), expected, "L\(n) differs from the pinned levels.json")
            if let d = C4Fixtures.designed, let info = d["infos"]?.arrayValue?.first(where: { $0["level"]?.intValue == n }) {
                XCTAssertEqual(ContentJSON.write(ContentJSON.value(o.info)), ContentJSON.write(info), "L\(n) info")
            }
        }
    }

    func testGenerationIsDeterministicAndPure() throws {
        let a = try Generator.generate(level: 135, curve: .default)
        let b = try Generator.generate(level: 135, curve: .default)
        XCTAssertEqual(ContentJSON.line(a.level, schema: false), ContentJSON.line(b.level, schema: false))
        // concurrent generation (the provider's queue) gives the same bytes
        var lines = [String](repeating: "", count: 4)
        let lock = NSLock()
        DispatchQueue.concurrentPerform(iterations: 4) { i in
            let o = try! Generator.generate(level: [135, 75, 135, 75][i], curve: .default)
            lock.lock(); lines[i] = ContentJSON.line(o.level, schema: false); lock.unlock()
        }
        XCTAssertEqual(lines[0], lines[2])
        XCTAssertEqual(lines[1], lines[3])
        XCTAssertNotEqual(lines[0], lines[1])
        XCTAssertEqual(lines[0], ContentJSON.line(a.level, schema: false))
    }

    // MARK: the content recast's generator changes (C4b: slots, template timers, corners)

    /// `slots` (floor(n / 10) mod slots) and `timers.fromTemplate` (every tag takes its template's timer, no draw); a
    /// curve without them decodes with the reference's defaults (3 slots, the fixed timers).
    func testDecadeSlotsAndTemplateTimers() throws {
        let c = CurveSpec.default
        XCTAssertEqual(c.slots, 7)                                 // content recast 2: templates L30-L99
        XCTAssertTrue(c.timers.fromTemplate)
        let old = try CurveSpec(json: c.json.removing("slots").setting("timers", c.json["timers"]!.removing("fromTemplate")))
        XCTAssertEqual(old.slots, 3)
        XCTAssertFalse(old.timers.fromTemplate)
        // L124: slot 12 mod 7 = 5 -> the template at position 4 of slot 5 is v552's L84 (Hard, 2:00); 3 slots would give L34
        let t124 = try Generator.target(c, 124)
        XCTAssertEqual([t124.template, t124.templateTimer], [84, 120])
        XCTAssertEqual(try Generator.target(old, 124).template, 34)
        XCTAssertEqual(C4Fixtures.level(124).timerSeconds, 120)
        for n in [106, 119, 131, 137, 149] {                      // slot rotation over the designed range
            XCTAssertEqual(try Generator.target(c, n).template, 30 + 10 * ((n / 10) % 7) + n % 10, "L\(n)")
            XCTAssertEqual(C4Fixtures.level(n).timerSeconds, try Generator.target(c, n).templateTimer, "L\(n) timer")
        }
        // fromTemplate: the template's timer whatever the tag, and the random stream is left untouched
        let r1 = Generator.Rng(PathRandom(seed: 42)), r2 = Generator.Rng(PathRandom(seed: 42))
        XCTAssertEqual(Generator.timerFor(c, .superHard, units: 3, doors: 0, r1, templateTimer: 210), 210)
        XCTAssertEqual(Generator.timerFor(c, .normal, units: 3, doors: 0, r1, templateTimer: 100), 100)
        XCTAssertEqual(try r1.below(1 << 30), try r2.below(1 << 30))
        // without it: the tag's timer, and a Normal level draws for the short timer
        XCTAssertEqual(Generator.timerFor(old, .hard, units: 3, doors: 0, r1, templateTimer: 100), old.timers.hard)
        _ = Generator.timerFor(old, .normal, units: 3, doors: 0, r1, templateTimer: 100)
        XCTAssertNotEqual(try r1.below(1 << 30), try r2.below(1 << 30))
        // the provider's allowed timers follow the template
        XCTAssertEqual(Difficulty.allowedTimers(.hard, curve: c, templateTimer: 100), [100])
        XCTAssertEqual(Difficulty.allowedTimers(.hard, curve: old, templateTimer: 100), [old.timers.hard])
    }

    /// Corners come LAST in the layout order (they take an empty margin line after every region), and only once unlocked
    /// (L70); the designed plans are the reference's (testTargetsAndPlansMatchTheReferenceInfos covers every one).
    func testCornerIsPlannedLast() throws {
        let c = CurveSpec.default
        XCTAssertEqual(c.obstacles.firstLevel["corner"], 70)
        var withCorner = 0
        for n in 60...400 {
            let plan = try Generator.obstaclePlan(c, n, Generator.Rng(PathRandom(seed: PathRandom.levelSeed(level: n, salt: c.salt)).fork("plan")))
            if n < 70 { XCTAssertFalse(plan.contains("corner"), "L\(n)") }
            if let i = plan.firstIndex(of: "corner") { XCTAssertEqual(i, plan.count - 1, "L\(n): \(plan)"); withCorner += 1 }
        }
        XCTAssertGreaterThan(withCorner, 50)
    }

    /// gen_levels.corner_layout, case for case (Fixtures/c4b_corner_layouts.json: 288 seeds × boards × used cells): the
    /// same sides, margin, corners and the same number of random draws; plus the layout's own promises.
    func testCornerLayoutMatchesTheReference() throws {
        let fx = try C4Fixtures.json("c4b_corner_layouts.json")
        let cases = try XCTUnwrap(fx["cases"]?.arrayValue)
        XCTAssertEqual(cases.count, 288)
        func cell(_ v: JSONValue) -> Cell { Cell(v.arrayValue![0].intValue!, v.arrayValue![1].intValue!) }
        var placed = 0, twoSided = 0, failed = 0
        for c in cases {
            let W = c["cols"]!.intValue!, H = c["rows"]!.intValue!
            let used = Set(c["used"]!.arrayValue!.map(cell))
            let rng = Generator.Rng(PathRandom(seed: c["seed"]!.uint64Value!))
            let got = try Generator.cornerLayout(rng, W, H, used)
            let tag = "seed \(c["seed"]!.intValue!) \(W)x\(H) \(c["used_name"]!.stringValue!)"
            XCTAssertEqual(got.sides, c["sides"]!.arrayValue!.map { $0.stringValue! }, tag)
            XCTAssertEqual(got.margin, Set(c["margin"]!.arrayValue!.map(cell)), tag)
            XCTAssertEqual(got.corners.map { "\($0.cell.c),\($0.cell.r) \($0.turn.rawValue)" },
                           c["corners"]!.arrayValue!.map { "\(cell($0["cell"]!).c),\(cell($0["cell"]!).r) \($0["turn"]!.stringValue!)" }, tag)
            XCTAssertEqual(try rng.below(1 << 30), c["next"]!.intValue!, tag + ": a different number of draws")
            // promises: 1 or 2 sides, never opposite; margin lines exclude the end cells and every used cell; 1-3 corners
            // per side on its line, each turning a ray that leaves the board toward that side along the margin
            XCTAssertLessThanOrEqual(got.sides.count, 2, tag)
            if got.sides.count == 2 { XCTAssertNotEqual(Generator.oppositeSide[got.sides[0]], got.sides[1], tag); twoSided += 1 }
            XCTAssertTrue(got.margin.isDisjoint(with: used), tag)
            for m in got.margin { XCTAssertFalse([Cell(0, 0), Cell(W - 1, 0), Cell(0, H - 1), Cell(W - 1, H - 1)].contains(m), tag) }
            XCTAssertEqual(Set(got.corners.map(\.cell)).count, got.corners.count, tag)
            for x in got.corners {
                XCTAssertTrue(got.margin.contains(x.cell), tag)
                let (out, along): (Dir, Set<Dir>) = x.cell.c == W - 1 ? (.right, [.up, .down]) : x.cell.c == 0 ? (.left, [.up, .down])
                    : x.cell.r == H - 1 ? (.down, [.left, .right]) : (.up, [.left, .right])
                XCTAssertTrue(ContentRules.cornerTurn(x.turn, out).map(along.contains) ?? false, "\(tag): \(x) does not face the board")
            }
            for side in got.sides {
                let onSide = got.corners.filter { x in
                    switch side { case "right": return x.cell.c == W - 1; case "left": return x.cell.c == 0
                    case "bottom": return x.cell.r == H - 1; default: return x.cell.r == 0 }
                }
                XCTAssertTrue((1...3).contains(onSide.count), "\(tag): \(side) has \(onSide.count) corners")
            }
            if got.corners.isEmpty { failed += 1 } else { placed += 1 }
        }
        XCTAssertGreaterThan(placed, 150)
        XCTAssertGreaterThan(twoSided, 30)
        XCTAssertGreaterThan(failed, 20)                          // too-short or used lines: the reference's "corner layout" failure
    }

    /// The peel's rays (the removal witness) turn at corners like arrowcore's walk: a corner turns a ray arriving from an
    /// accepting side and blocks any other; its turns share the pipes' 16-hop guard; and the split search (a stuck peel
    /// cutting a snake) sees the corners too.
    func testThePeelTurnsAtCornersAndSharesTheHopGuard() throws {
        func peel(_ W: Int, _ H: Int, _ snake: [Cell], box: Cell, corners: [(Cell, CornerTurn)], pipe: [Cell]? = nil) -> Generator.Peel {
            var plan = Generator.Plan()
            plan.boxes = [[box]]                                   // an unbroken box (nothing has left: it cannot break)
            plan.corners = corners.map { (cell: $0.0, turn: $0.1) }
            if let p = pipe { plan.pipes = [p] }
            let u = Generator.GUnit(kind: .snake, cells: snake, members: [], region: .out, layer: 1)
            return Generator.Peel(W, H, [0: u], plan, Generator.Rng(PathRandom(seed: 7)), [:], 1)
        }
        // a snake along row 1, its left end held by the box at (0,1), a corner on the right margin at (5,1):
        // upLeft accepts → (turns ↓, off the 3-row grid); downRight does not (the ray is blocked)
        let line = [Cell(1, 1), Cell(2, 1), Cell(3, 1), Cell(4, 1)]
        let open = peel(6, 3, line, box: Cell(0, 1), corners: [(Cell(5, 1), .upLeft)])
        XCTAssertEqual(open.options(0).map { $0.oriented!.cells }, [line])
        let shut = peel(6, 3, line, box: Cell(0, 1), corners: [(Cell(5, 1), .downRight)])
        XCTAssertTrue(shut.options(0).isEmpty)
        XCTAssertFalse(try shut.split())                           // no cut frees a piece: the corner shuts the only way out
        XCTAssertTrue(try open.split())
        // the hop guard: a staircase of n corners ((x0+k, k) upLeft, (x0+k, k+1) downRight) after the head, optionally a
        // straight pipe first (hop 1): 16 hops pass, the 17th blocks
        func stair(_ n: Int, pipe: Bool) -> Generator.Peel {
            let x0 = pipe ? 5 : 3
            let cs = (0..<n).map { j -> (Cell, CornerTurn) in
                j % 2 == 0 ? (Cell(x0 + j / 2, j / 2), .upLeft) : (Cell(x0 + j / 2, j / 2 + 1), .downRight)
            }
            return peel(x0 + n / 2 + 4, n / 2 + 4, [Cell(1, 0), Cell(2, 0)], box: Cell(0, 0), corners: cs,
                        pipe: pipe ? [Cell(3, 0), Cell(4, 0)] : nil)
        }
        XCTAssertEqual(stair(16, pipe: false).options(0).count, 1)
        XCTAssertTrue(stair(17, pipe: false).options(0).isEmpty)
        XCTAssertEqual(stair(15, pipe: true).options(0).first?.passes, [0])     // 1 passage + 15 turns = 16 hops
        XCTAssertTrue(stair(16, pipe: true).options(0).isEmpty)                  // 17: blocked
    }

    /// A designed corner level end to end: the corners are emitted after the elevator as x<i> with their turn, on the
    /// board's margin, every one on some ray of the level, and notes.corner_sides is in the info only when set.
    func testDesignedCornerLevelsCarryTheirCorners() throws {
        for n in [110, 116, 140] {                                  // content recast 2: designed corner levels L106-L150
            let o = try Generator.generate(level: n, curve: .default)
            let xs = o.level.obstacles.filter { $0.kind == .corner }
            XCTAssertFalse(xs.isEmpty, "L\(n)")
            XCTAssertEqual(xs.map(\.id.raw), (0..<xs.count).map { "x\($0)" }, "L\(n)")
            XCTAssertEqual(o.level.obstacles.suffix(xs.count).map(\.kind), xs.map(\.kind), "L\(n): corners come last")
            XCTAssertTrue(xs.allSatisfy { $0.cells.count == 1 && $0.turn != nil }, "L\(n)")
            let sides = try XCTUnwrap(o.info.cornerSides, "L\(n)")
            XCTAssertTrue((1...2).contains(sides.count))
            XCTAssertEqual(ContentJSON.value(o.info)["notes"]?["corner_sides"]?.arrayValue?.compactMap(\.stringValue), sides)
        }
        let plain = try Generator.generate(level: 121, curve: .default)      // door only: no corner_sides key at all
        XCTAssertNil(plain.info.cornerSides)
        XCTAssertNil(ContentJSON.value(plain.info)["notes"]?["corner_sides"])
    }

    func testAGeneratedLevelDecodesAsABundleLevel() throws {
        let o = try Generator.generate(level: 131, curve: .default)
        let data = Data(ContentJSON.line(o.level, schema: true).utf8)
        let back = try LevelJSON.decodeBundle(data)
        XCTAssertEqual(back, o.level)
        XCTAssertEqual(back.seed, PathRandom.levelSeed(level: 131, salt: CurveSpec.default.salt))
        XCTAssertTrue(try LevelJSON.inspectBundle(data).unknownKeys.isEmpty)
    }
}

/// The full acceptance (PC_C4_FULL=1, release build). Evidence: $PC_EVIDENCE_DIR/c4-*.txt.
final class C4FullTests: XCTestCase {

    override func setUpWithError() throws {
        guard C4Fixtures.full else { throw XCTSkip("PC_C4_FULL=1 runs the full C4 acceptance (release build recommended)") }
    }

    /// Every designed level (L106-L150 since content recast 2) = its pinned levels.json line and its pinned designed.json record
    /// (level and the reference's info); a level build_levels had to gate is generated gated (C4Fixtures.designedLevel).
    func testEveryDesignedLevelIsByteForByte() throws {
        var lines = ["Swift Generator vs the pinned levels.json (with \"schema\":1) and designed.json, L\(C4Fixtures.designedRange.lowerBound)-L\(C4Fixtures.designedRange.upperBound)", ""]
        var bad = 0
        let designedLevels = C4Fixtures.designed?["levels"]?.arrayValue ?? []
        let infos = C4Fixtures.designed?["infos"]?.arrayValue ?? []
        for n in C4Fixtures.designedRange {
            let t0 = C4Fixtures.wallNow(), c0 = C4Fixtures.cpuNow()
            let o = try C4Fixtures.designedLevel(n)
            let ms = (C4Fixtures.wallNow() - t0) * 1000, cpu = (C4Fixtures.cpuNow() - c0) * 1000
            var verdicts: [String] = []
            do {
                let ok = ContentJSON.line(o.level, schema: true) == C4Fixtures.rawLines[n]
                verdicts.append(ok ? "levels.json =" : "levels.json DIFFERS")
                if !ok { bad += 1 }
                XCTAssertTrue(ok, "L\(n)")
            }
            if let dl = designedLevels.first(where: { $0["level"]?.intValue == n }) {
                let ok = ContentJSON.line(o.level, schema: false) == ContentJSON.write(dl)
                let okInfo = infos.first { $0["level"]?.intValue == n }.map { ContentJSON.write($0) == ContentJSON.write(ContentJSON.value(o.info)) } ?? false
                verdicts.append(ok ? "designed.json =" : "designed.json DIFFERS")
                verdicts.append(okInfo ? "info =" : "info DIFFERS")
                if !ok || !okInfo { bad += 1 }
                XCTAssertTrue(ok && okInfo, "L\(n) vs designed.json")
            }
            lines.append(String(format: "L%d  %@  attempt %@  rejected %d  %.1f ms wall %.1f ms cpu", n, verdicts.joined(separator: "  "),
                                o.info.attempt, o.info.rejected.count, ms, cpu))
        }
        lines.append("")
        lines.append("mismatches: \(bad)")
        C4Fixtures.evidence("c4-designed-byte-for-byte.txt", lines.joined(separator: "\n"))
        XCTAssertEqual(bad, 0)
    }

    /// L151-L650 (500 runtime levels). The REFERENCE algorithm (ungated Generator): byte-identical to gen_levels.py (the
    /// SHA-256 of its canonical line, Fixtures/c4_runtime_reference.json), byte-identical across two runs, and our
    /// Validator's content verdict = validate_levels.check_level's (the reference's own output fails it on 2 levels of
    /// recast 2's curve: the dead ends L416 L517). What the game SERVES (LevelProvider.produce: the validator-gated generator + the SPEC.md §5.27 band gate):
    /// valid under both rule books, solvable, won by the driver, inside the curve bands, and identical to the reference
    /// wherever the reference is valid AND in band; the valid reference boards outside the bands (recast 2's curve: L162
    /// L210 L257 L322 L363 L441 L442 L596 L642 by units / waves / free, and the Box counter above the ring's 99: L354) are
    /// exactly the re-rolled ones (EndlessFixtures).
    /// Timing per level for both.
    func testRuntimeLevelsAgainstTheReference() throws {
        let ref = try C4Fixtures.json("c4_runtime_reference.json")
        XCTAssertEqual(ref["curve_sha256"]?.stringValue, C4Fixtures.sha256(ContentJSON.write(CurveSpec.default.json)))
        let rows = try XCTUnwrap(ref["levels"]?.arrayValue)
        XCTAssertEqual(rows.count, 500)
        struct Row { var n: Int; var line: String; var info: Generator.Info; var genMs: Double; var genCpu: Double }
        func pass() throws -> [Row] {
            try rows.map { r in
                let n = r["level"]!.intValue!
                let t0 = C4Fixtures.wallNow(), c0 = C4Fixtures.cpuNow()
                let o = try Generator.generate(level: n, curve: .default)
                return Row(n: n, line: ContentJSON.line(o.level, schema: false), info: o.info,
                           genMs: (C4Fixtures.wallNow() - t0) * 1000, genCpu: (C4Fixtures.cpuNow() - c0) * 1000)
            }
        }
        let run1 = try pass()
        let run2 = try pass()
        var out: [String] = []
        var shaBad = 0, repeatBad = 0, verdictBad = 0, refInvalid: [Int] = [], refOutOfBand: [Int] = []
        var served: [(n: Int, ms: Double, cpu: Double, rec: LevelProvider.Record)] = []
        var servedInvalid = 0, servedUnsolved = 0, servedLost = 0, outOfBand = 0, servedDiffers: [Int] = []
        for (k, r) in rows.enumerated() {
            let a = run1[k], b = run2[k]
            let shaOK = C4Fixtures.sha256(a.line) == r["sha256"]?.stringValue && a.line.utf8.count == r["bytes"]?.intValue
            if !shaOK { shaBad += 1 }
            if a.line != b.line { repeatBad += 1 }
            XCTAssertTrue(shaOK, "L\(a.n) differs from the Python reference")
            XCTAssertEqual(a.line, b.line, "L\(a.n) differs between two runs")
            XCTAssertEqual(a.info.attempt, r["attempt"]?.stringValue, "L\(a.n) attempt")
            XCTAssertEqual(a.info.rejected, r["rejected"]?.arrayValue?.compactMap(\.stringValue), "L\(a.n) rejected")
            // the reference output under our validator = under the Python validator
            let refLevel = try LevelJSON.decodeBundle(Data(a.line.utf8))
            let rep = Validator.checkLevel(refLevel, raw: try ContentJSON.parse(a.line).setting("schema", .int(1)), sprites: nil,
                                           options: Validator.Options(gameRules: false))
            let pyErrors = r["errors"]?.arrayValue?.compactMap(\.stringValue) ?? []
            let ours = rep.errors.map(\.description)
            if pyErrors != ours { verdictBad += 1 }
            XCTAssertEqual(ours, pyErrors, "L\(a.n): validator verdict differs from the Python's")
            if !pyErrors.isEmpty { refInvalid.append(a.n) }
            // the reference output against the bands (SPEC.md §5.27): a valid one outside them must be re-rolled
            let refAssess = try Difficulty.assess(refLevel)
            if pyErrors.isEmpty && !refAssess.inBand { refOutOfBand.append(a.n) }
            // what the game serves
            let t0 = C4Fixtures.wallNow(), c0 = C4Fixtures.cpuNow()
            let (l, rec) = LevelProvider.produce(a.n, curve: .default, library: nil, options: Validator.Options())
            let sms = (C4Fixtures.wallNow() - t0) * 1000, scpu = (C4Fixtures.cpuNow() - c0) * 1000
            served.append((a.n, sms, scpu, rec))
            let full = Validator.checkLevel(l, raw: nil, sprites: nil, options: Validator.Options())
            if !full.isValid { servedInvalid += 1 }
            XCTAssertTrue(full.isValid, "served L\(a.n): \(full.errors)")
            XCTAssertNotEqual(rec.route, .fallback, "L\(a.n) fell back")
            if !Solver.solve(l).isSolved { servedUnsolved += 1 }
            var dc = DriverConfig(tapInterval: 0.6); dc.recordEvents = false
            let drive = HeadlessDriver.play(level: l, config: dc)
            if !drive.won { servedLost += 1 }
            XCTAssertTrue(drive.won, "L\(a.n) not won by the driver")
            let assess = try Difficulty.assess(l)
            if !assess.violations.isEmpty { outOfBand += 1 }
            XCTAssertTrue(assess.violations.isEmpty, "L\(a.n) out of band: \(assess.violations)")
            var asRef = l
            asRef.source = .designed
            let same = ContentJSON.line(asRef, schema: false) == a.line
            if !same { servedDiffers.append(a.n) }
            if pyErrors.isEmpty && refAssess.inBand { XCTAssertTrue(same, "L\(a.n): the gated output differs from a VALID, IN-BAND reference output") }
            if pyErrors.isEmpty && !refAssess.inBand {
                XCTAssertFalse(same, "L\(a.n): an out-of-band reference output was served")
                XCTAssertEqual(rec.route, .retried, "L\(a.n)")
            }
            out.append(String(format: "L%d %@ %@ %@ ref %@ · served %@ %@ %@ · units %d/%d waves %d/%d free %d/%d %dx%d t%d · gen %.1f ms (cpu %.1f) · served %.1f ms (cpu %.1f; validate %.1f)%@",
                              a.n, shaOK ? "=py" : "DIFF", a.line == b.line ? "=rerun" : "RERUN-DIFF", pyErrors == ours ? "=verdict" : "VERDICT-DIFF",
                              pyErrors.isEmpty ? (refAssess.inBand ? "valid" : "valid OUT-OF-BAND(" + refAssess.violations.joined(separator: "; ") + ")")
                                               : "INVALID(" + (pyErrors.first ?? "") + ")",
                              same ? "=ref" : rec.roll > 0 ? "RE-ROLLED(roll \(rec.roll))" : "OTHER-ATTEMPT",
                              full.isValid ? "valid" : "INVALID", drive.won ? "won" : "LOST",
                              assess.measured.units, assess.target.units, assess.measured.rounds, assess.target.rounds,
                              assess.measured.freeAtStart, assess.target.free, l.cols, l.rows, l.timerSeconds,
                              a.genMs, a.genCpu, sms, scpu, rec.validateMs,
                              assess.violations.isEmpty ? "" : "  OUT OF BAND: " + assess.violations.joined(separator: "; ")))
        }
        func stats(_ v: [Double]) -> String {
            let s = v.sorted()
            return String(format: "mean %.1f  p50 %.1f  p95 %.1f  p99 %.1f  max %.1f ms", s.reduce(0, +) / Double(s.count), s[s.count / 2],
                          s[Int(Double(s.count) * 0.95)], s[Int(Double(s.count) * 0.99)], s.last!)
        }
        out.insert(contentsOf: [
            "L151-L650 — the reference algorithm (ungated Generator) vs design/tools/gen_levels.py + validate_levels.check_level, and what the game serves (LevelProvider.produce: the validator-gated generator)", "",
            "reference: python mismatches \(shaBad) · rerun mismatches \(repeatBad) · verdict mismatches \(verdictBad) · reference outputs the validator refuses: \(refInvalid.map { "L\($0)" })",
            "valid reference outputs outside the bands (re-rolled, SPEC.md §5.27): \(refOutOfBand.map { "L\($0)" })",
            "served: invalid \(servedInvalid) · unsolved \(servedUnsolved) · not won by the 0.6 s/tap driver \(servedLost) · out of band \(outOfBand) · fell back \(served.filter { $0.rec.route == .fallback }.count) · differs from the reference \(servedDiffers.map { "L\($0)" })",
            "generation, ungated (wall, run 1):  " + stats(run1.map(\.genMs)),
            "generation, ungated (thread CPU):   " + stats(run1.map(\.genCpu)),
            "generation, ungated (wall, run 2):  " + stats(run2.map(\.genMs)),
            "served = gated generation + validation (wall):  " + stats(served.map(\.ms)),
            "served (thread CPU):                            " + stats(served.map(\.cpu)),
            "of which validation (wall):                     " + stats(served.map(\.rec.validateMs)),
            ""], at: 0)
        C4Fixtures.evidence("c4-runtime-levels.txt", out.joined(separator: "\n"))
        XCTAssertEqual(shaBad + repeatBad + verdictBad + servedInvalid + servedUnsolved + servedLost + outOfBand, 0)
        XCTAssertEqual(Set(servedDiffers), Set(refInvalid).union(refOutOfBand))
        // exactly EndlessFixtures' band re-rolls (units / waves / free) and Box re-rolls (counters above 99)
        XCTAssertEqual(refOutOfBand, Array(Set(EndlessFixtures.bandRerolls.keys).union(EndlessFixtures.boxRerolls.keys)).sorted())
    }

    /// The bands are the designed range's own envelope (L106-L150 since content recast 2), widened by 25 % of its width.
    func testBandsAreTheDesignedEnvelope() throws {
        var ur: [Double] = [], rr: [Double] = [], fd: [Int] = []
        for n in C4Fixtures.designedRange {
            let a = try Difficulty.assess(C4Fixtures.level(n), bands: DifficultyBands(unitsRatio: 0...100, roundsRatio: 0...100, freeDelta: -1000...1000, minTimeShare: 0.2))
            XCTAssertTrue(a.violations.isEmpty, "L\(n): \(a.violations)")
            ur.append(a.unitsRatio); rr.append(a.roundsRatio); fd.append(a.measured.freeAtStart - a.target.free)
        }
        func widen(_ lo: Double, _ hi: Double) -> (Double, Double) { (lo - 0.25 * (hi - lo), hi + 0.25 * (hi - lo)) }
        let u = widen(ur.min()!, ur.max()!), r = widen(rr.min()!, rr.max()!)
        let b = DifficultyBands.designed
        XCTAssertEqual(b.unitsRatio.lowerBound, u.0, accuracy: 0.001)
        XCTAssertEqual(b.unitsRatio.upperBound, u.1, accuracy: 0.001)
        XCTAssertEqual(b.roundsRatio.lowerBound, r.0, accuracy: 0.001)
        XCTAssertEqual(b.roundsRatio.upperBound, r.1, accuracy: 0.001)
        let f = (Double(fd.min()!), Double(fd.max()!))
        XCTAssertEqual(Double(b.freeDelta.lowerBound), (f.0 - 0.25 * (f.1 - f.0)).rounded(.down))
        XCTAssertEqual(Double(b.freeDelta.upperBound), (f.1 + 0.25 * (f.1 - f.0)).rounded(.up))
    }
}
