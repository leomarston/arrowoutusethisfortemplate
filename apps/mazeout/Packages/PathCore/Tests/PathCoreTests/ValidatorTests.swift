import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// §4.14 / §4.17 ValidatorTests (C4): the validator = design/tools/validate_levels.py (the same findings, message for
/// message, on the reference's 15 negative controls), plus sprites and the game's own rules.
final class ValidatorTests: XCTestCase {

    // MARK: the reference's negative controls (validator_selftest.py), with the Python's own error lists

    func testNegativeControlsAreCaughtWithThePythonMessages() throws {
        let fx = try C4Fixtures.json("c4_negative_controls.json")
        let muts = try XCTUnwrap(fx["mutations"]?.arrayValue)
        XCTAssertEqual(muts.count, 20)                         // recast 2026-09-25: + corners, pipe under a door, poking arrow, L72 repeat, Corner card;
                                                               // content recast 2: + L86 / L101 repeats, a MIRRORED repeat, L93 hidden key, L102 platform
        var lines = ["validator_selftest.py's \(muts.count) mutations: Swift findings vs validate_levels.py's", ""]
        var caught = 0
        for m in muts {
            let name = m["mutation"]!.stringValue!
            let touched = m["levels"]!.arrayValue!.map { $0.intValue! }
            var specs = C4Fixtures.allLevels
            var ours: [String] = []
            for n in touched {
                let raw = m["level_json"]![String(n)]!
                let l = try JSONDecoder().decode(LevelSpec.self, from: ContentJSON.data(raw))
                specs[n - 1] = l
                ours += Validator.checkLevel(l, raw: raw, sprites: nil, options: Validator.Options(gameRules: false))
                    .errors.map(\.description)
            }
            let doc = C4Fixtures.doc
            ours += Validator.crossChecks(specs, authoredEnd: 150, unlocks: doc["unlocks"]?.arrayValue ?? [],
                                          sessions: doc["sessions"]?.arrayValue ?? [], tutorials: doc["tutorials"]?.arrayValue ?? [])
                .findings.filter { $0.severity == .error }.map(\.description)
            let py = m["python_errors"]!.arrayValue!.map { $0.stringValue! }
            if !ours.isEmpty { caught += 1 }
            XCTAssertFalse(ours.isEmpty, "MISSED: \(name)")
            XCTAssertEqual(ours, py, name)
            lines.append("\(ours.isEmpty ? "MISSED" : "CAUGHT")  \(ours == py ? "same findings as Python" : "DIFFERENT")  \(name)  \(ours.first ?? "")")
        }
        lines.append("")
        lines.append("\(caught)/\(muts.count) caught")
        C4Fixtures.evidence("c4-negative-controls.txt", lines.joined(separator: "\n"))
    }

    // MARK: clean content stays clean (a sample; the whole document in C4FullValidatorTests)

    func testSampleOfShippedLevelsIsValidUnderBothRuleBooks() throws {
        // FTUE board, tape (L7), box (L11), pipe (L21), elevator (L31), door (L33), a big Hard, the widest (L6: warning),
        // phone session 2 (recast): a door-hidden arrow poking out of its door (L62), a door + pipes (L63), pipes UNDER doors
        // (L69), the Corner unlock (L70), six corners (L76), a spare in a repeated slot (L75), designed boards;
        // phone session 3 (content recast 2): a corner under a door (L89), a door staircase with keys under doors (L93),
        // doors + tapes (L98), v552's elevator + corners (L102), stand-ins of repeated boards (L86 door, L100 elevator)
        // PUBLISH B0 (level re-order): the list names BOARDS by research slot; each is checked at the slot it ships at
        for n in [1, 6, 7, 11, 21, 31, 33, 34, 47, 62, 63, 69, 70, 75, 76, 86, 89, 93, 98, 100, 102, 131, 150].map(C4Fixtures.slot(research:)) {
            let l = C4Fixtures.level(n)
            let raw = C4Fixtures.doc["levels"]!.arrayValue![n - 1]
            let r = Validator.checkLevel(l, raw: raw, sprites: nil, options: Validator.Options())
            XCTAssertTrue(r.isValid, "L\(n): \(r.errors)")
            XCTAssertEqual(r.warnings.map(\.message), n == 6 ? ["cols 27 > 26: fit pitch below the 14.04 pt zoom floor"] : [], "L\(n)")
            XCTAssertEqual(r.measured?.bundle, l.metrics, "L\(n) metrics")
        }
    }

    func testDocumentChecksOnTheShippedDocument() throws {
        let doc = C4Fixtures.doc
        let (f, first) = Validator.crossChecks(C4Fixtures.allLevels, authoredEnd: 150, unlocks: doc["unlocks"]!.arrayValue!,
                                               sessions: doc["sessions"]!.arrayValue!, tutorials: doc["tutorials"]!.arrayValue!)
        XCTAssertEqual(f, [])
        XCTAssertEqual(first, ["linked": 7, "box": 11, "pipe": 21, "elevator": 31, "door": 33, "corner": 70])
    }

    // MARK: single findings on synthetic levels

    func lvl(_ arrows: [ArrowSpec], _ obstacles: [ObstacleSpec] = [], cols: Int = 6, rows: Int = 6, timer: Int = 180) -> LevelSpec {
        var l = LevelSpec(level: 900, source: .designed, cols: cols, rows: rows, timerSeconds: timer, arrows: arrows, obstacles: obstacles)
        l.metrics = nil
        return l
    }
    func a(_ id: Int, _ cells: [(Int, Int)], _ d: Dir, layer: Int = 1, hidden: String? = nil) -> ArrowSpec {
        ArrowSpec(id: ArrowID(id), cells: cells.map { Cell($0.0, $0.1) }, dir: d, layer: layer, hiddenBy: hidden.map { ObstacleID($0) })
    }
    func errors(_ l: LevelSpec, raw: JSONValue? = nil) -> [String] {
        Validator.checkLevel(l, raw: raw, sprites: nil, options: Validator.Options(gameRules: false)).errors.map(\.message)
    }

    func testStructureValuesAndProvenance() {
        XCTAssertEqual(errors(lvl([a(0, [(0, 0), (1, 1)], .right)])), ["arrow 0: step (0, 0)->(1, 1) not orthogonal",
                                                                        "arrow 0: dir right but last step None"])
        XCTAssertEqual(errors(lvl([a(0, [(0, 0), (1, 0)], .left)])), ["arrow 0: dir left but last step right",
                                                                   "arrow 0: ray crosses its own body at (0, 0)"])
        XCTAssertEqual(errors(lvl([a(0, [(0, 0), (1, 0)], .right)], timer: 30)), ["timer_s 30"])
        var v = lvl([a(0, [(0, 0), (1, 0)], .right)])
        v.source = .authored
        XCTAssertEqual(errors(v), ["no capture for a recorded level"])
        let raw = ContentJSON.value(lvl([a(0, [(0, 0), (1, 0)], .right)]), schema: true).setting("shape", .string("x"))
        XCTAssertEqual(errors(lvl([a(0, [(0, 0), (1, 0)], .right)]), raw: raw), ["unknown key shape"])
        XCTAssertEqual(errors(lvl([a(0, [(0, 0), (1, 0)], .right), a(1, [(3, 0), (2, 0)], .left)])),
                       ["greedy solver stuck with 2 units left (DFS: UNSOLVABLE)"])
    }

    func testObstacleFindings() {
        // a door that is not a rectangle, its hidden arrow poking out of it, no key
        let door = ObstacleSpec(id: "d0", kind: .door, cells: [Cell(0, 2), Cell(1, 2), Cell(0, 3)], order: 0, reveals: [ArrowID(1)])
        // (every expected list below is validate_levels.check_level's output on the same level; since the content recast
        // (2026-09-25, v552 L62) a door's hidden arrow MAY poke out of the door where no ray reaches it and nothing lies:
        // the poke cases are testDoorStubsMayPokeOutOnlyWhereNoRayReaches)
        XCTAssertEqual(errors(lvl([a(0, [(4, 0), (5, 0)], .right), a(1, [(0, 2), (1, 2), (2, 2)], .right, hidden: "d0")], [door])),
                       ["door d0 is not a rectangle", "door d0 smaller than 2x2", "0 keys for 1 doors"])
        // …but a BOX's hidden arrow still may not stick out
        let box = ObstacleSpec(id: "b0", kind: .box, cells: [Cell(0, 2), Cell(1, 2)], counter: 1, reveals: [ArrowID(1)])
        XCTAssertEqual(errors(lvl([a(0, [(4, 0), (5, 0)], .right), a(1, [(0, 2), (1, 2), (2, 2)], .right, hidden: "b0")], [box])),
                       ["box b0: hidden arrow 1 sticks out"])
        // a pipe whose ends are not its extremities, counter 0, counter badge off the tube
        let pipe = ObstacleSpec(id: "p0", kind: .pipe, cells: [Cell(0, 3), Cell(1, 3), Cell(2, 3)],
                                ends: [PipeEnd(cell: Cell(1, 3), out: .left), PipeEnd(cell: Cell(2, 3), out: .right)], counter: 0, counterAt: [5, 5])
        let p = errors(lvl([a(0, [(4, 0), (5, 0)], .right)], [pipe]))
        XCTAssertEqual(p, ["pipe p0 ends [[1, 3], [2, 3]] are not its extremities", "pipe p0 counter 0", "pipe p0 counter_at [5.0, 5.0] not on the tube"])
        // a key off its rider; an elevator whose hidden arrow is on layer 1
        let key = ObstacleSpec(id: "k0", kind: .key, cells: [Cell(3, 3), Cell(4, 3)], arrows: [ArrowID(0)])
        let door2 = ObstacleSpec(id: "d0", kind: .door, cells: [Cell(0, 4), Cell(1, 4), Cell(0, 5), Cell(1, 5)], order: 0)
        XCTAssertTrue(errors(lvl([a(0, [(4, 0), (5, 0)], .right)], [key, door2])).contains("key k0 cells [(3, 3), (4, 3)] not on its rider"))
        let elev = ObstacleSpec(id: "e0", kind: .elevator, cells: [Cell(0, 0), Cell(1, 0), Cell(0, 1), Cell(1, 1)], arrows: [ArrowID(0)],
                                reveals: [ArrowID(1)])
        let el = errors(lvl([a(0, [(0, 0), (1, 0)], .right), a(1, [(0, 1), (1, 1)], .right, hidden: "e0")], [elev]))
        XCTAssertEqual(el, ["elevator e0: hidden arrow 1 not on layer 2"])
    }

    // MARK: the content recast's validator rules (2026-09-25; each expected list = validate_levels.check_level's output)

    /// v552 L62: a door-hidden arrow drawn poking out of its door is allowed only where no ray can reach the stub while the
    /// door is shut and nothing else lies there.
    func testDoorStubsMayPokeOutOnlyWhereNoRayReaches() {
        let door = ObstacleSpec(id: "d0", kind: .door, cells: [Cell(0, 2), Cell(1, 2), Cell(0, 3), Cell(1, 3)], order: 0, reveals: [ArrowID(1)])
        let key = ObstacleSpec(id: "k0", kind: .key, cells: [Cell(4, 0), Cell(5, 0)], arrows: [ArrowID(0)])
        let hidden = a(1, [(0, 2), (1, 2), (2, 2)], .right, hidden: "d0")          // pokes out at (2, 2)
        // arrow 2 below the stub, pointing up: its ray reaches (2, 2)
        XCTAssertEqual(errors(lvl([a(0, [(4, 0), (5, 0)], .right), hidden, a(2, [(2, 5), (2, 4)], .up)], [door, key])),
                       ["door d0: hidden arrow 1 pokes out at [(2, 2)], which arrow 2's ray can reach"])
        // a visible arrow lying on the stub
        XCTAssertEqual(errors(lvl([a(0, [(4, 0), (5, 0)], .right), hidden, a(2, [(2, 2), (3, 2)], .right)], [door, key])),
                       ["arrow 2 shares (2, 2) with 1 (layer 1)", "door d0: hidden arrow 1 pokes out onto an occupied cell (2, 2)"])
        // no ray reaches it: allowed
        XCTAssertEqual(errors(lvl([a(0, [(4, 0), (5, 0)], .right), hidden, a(2, [(4, 5), (5, 5)], .right)], [door, key])), [])
    }

    /// v552 L69: a pipe lying WHOLLY under a door shares the door's cells (it acts from the burst on: the walk meets the
    /// locked door first, so the arrow above the mouth is not free at the start: 2 waves, 1 free); moved half out of the
    /// door it overlaps it.
    func testAPipeUnderADoor() throws {
        let door = ObstacleSpec(id: "d0", kind: .door, cells: (3...5).flatMap { r in (0...5).map { Cell($0, r) } }, order: 0)
        let key = ObstacleSpec(id: "k0", kind: .key, cells: [Cell(4, 0), Cell(5, 0)], arrows: [ArrowID(1)])
        func pipe(_ r0: Int) -> ObstacleSpec {
            ObstacleSpec(id: "p0", kind: .pipe, cells: [Cell(2, r0), Cell(2, r0 + 1), Cell(3, r0 + 1), Cell(3, r0)],
                         ends: [PipeEnd(cell: Cell(2, r0), out: .up), PipeEnd(cell: Cell(3, r0), out: .up)], counter: 1,
                         counterAt: [2.0, Double(r0) + 0.5])
        }
        let arrows = [a(0, [(2, 0), (2, 1)], .down), a(1, [(4, 0), (5, 0)], .right)]
        let under = lvl(arrows, [door, key, pipe(3)])
        let rep = Validator.checkLevel(under, raw: nil, sprites: nil, options: Validator.Options())
        XCTAssertEqual(rep.errors, [])
        XCTAssertEqual(rep.measured?.bundle, LevelMetrics(rounds: 2, freeAtStart: 1, arrows: 2, cells: 4, meanLength: 2.0, botTimeLeft: 177.7))
        XCTAssertEqual(errors(lvl(arrows, [door, key, pipe(2)])), ["pipe p0 overlaps d0 at (2, 3)", "pipe p0 overlaps d0 at (3, 3)"])
    }

    /// No ray may reach the pipe/corner hop guard (16): a staircase of 15 corners is fine, 16 hops is a finding (once with
    /// the pipes intact, once broken), and at 17 the 17th corner blocks (the guard) so the level is also stuck.
    func testRayLoopGuard() {
        func stair(_ n: Int) -> LevelSpec {
            let xs = (0..<n).map { j -> ObstacleSpec in
                let k = j / 2
                return ObstacleSpec(id: ObstacleID("x\(j)"), kind: .corner, cells: [j % 2 == 0 ? Cell(2 + k, k) : Cell(2 + k, k + 1)],
                                    turn: j % 2 == 0 ? .upLeft : .downRight)
            }
            return lvl([a(0, [(0, 0), (1, 0)], .right)], xs, cols: 12, rows: 12)
        }
        XCTAssertEqual(errors(stair(15)), [])
        XCTAssertEqual(errors(stair(16)), ["arrow 0: its ray loops through pipes/corners", "arrow 0: its ray loops through pipes/corners"])
        XCTAssertEqual(errors(stair(17)), ["arrow 0: its ray loops through pipes/corners", "arrow 0: its ray loops through pipes/corners",
                                           "greedy solver stuck with 1 units left (DFS: UNSOLVABLE)"])
    }

    /// The repeat check is offset-free (v552 L72 = L52 read in another frame): a shifted copy of a board repeats it.
    func testBoardKeyIsOffsetFree() {
        let l = C4Fixtures.level(14)
        var shifted = l
        shifted.level = 72
        shifted.cols += 3; shifted.rows += 5
        shifted.arrows = l.arrows.map { var x = $0; x.cells = x.cells.map { Cell($0.c + 3, $0.r + 5) }; return x }
        XCTAssertEqual(Validator.boardKey(l), Validator.boardKey(shifted))
        var turned = shifted
        turned.arrows[0].dir = turned.arrows[0].dir.opposite
        XCTAssertNotEqual(Validator.boardKey(l), Validator.boardKey(turned))
    }

    /// The document's repeat check (SPEC.md §5 item 28, content recast 2 = design/tools/repeats.py): a board repeats an
    /// earlier one when its START-VISIBLE arrows, or ALL its arrows, are the earlier board's up to a shift and the 8
    /// symmetries of the square (head directions mapped with the cells); a different head is a different board; the FIRST
    /// occurrence is named. (WP0c/core-final: the mutation checks showed nothing pinned the heads or either key alone.)
    func testRepeatCheckUnderTheSquareSymmetriesKeepsHeadsAndBothKeys() throws {
        func repeats(_ specs: [LevelSpec]) -> [String] {
            Validator.crossChecks(specs, authoredEnd: 150, unlocks: [], sessions: [], tutorials: []).findings
                .map(\.message).filter { $0.contains(" repeats ") }
        }
        // (x, y) -> (a x + b y, c x + d y), written out here independently of Validator.squareSymmetries
        let syms: [(Int, Int, Int, Int)] = [(1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, -1), (0, 1, -1, 0),
                                            (-1, 0, 0, 1), (1, 0, 0, -1), (0, 1, 1, 0), (0, -1, -1, 0)]
        func dir(_ x: Int, _ y: Int) -> Dir { y == -1 ? .up : y == 1 ? .down : x == -1 ? .left : .right }
        func image(_ l: LevelSpec, _ m: (Int, Int, Int, Int), level: Int) -> LevelSpec {
            var o = l
            o.level = level
            o.arrows = l.arrows.map { ar in
                var x = ar
                x.cells = ar.cells.map { Cell(m.0 * $0.c + m.1 * $0.r + 50, m.2 * $0.c + m.3 * $0.r + 60) }   // + a shift
                x.dir = dir(m.0 * ar.dir.dc + m.1 * ar.dir.dr, m.2 * ar.dir.dc + m.3 * ar.dir.dr)
                return x
            }
            return o
        }
        // a door level: some layer-1 arrows start hidden under a door, so the two keys differ
        func underADoor(_ a: ArrowSpec) -> Bool { a.hiddenBy != nil && a.layer <= 1 }
        let l = try XCTUnwrap(C4Fixtures.allLevels.first { $0.arrows.contains(where: underADoor) && $0.arrows.contains { $0.hiddenBy == nil } })
        let k = Validator.canonicalKeys(l)
        XCTAssertNotEqual(k.visible, k.full)
        // every symmetry image (shifted) has both keys of the original and is named a repeat of it (the first occurrence,
        // never of an earlier image)
        let images = syms.enumerated().map { image(l, $0.element, level: 900 + $0.offset) }
        for (i, im) in images.enumerated() {
            XCTAssertEqual(Validator.canonicalKeys(im).visible, k.visible, "symmetry \(i)")
            XCTAssertEqual(Validator.canonicalKeys(im).full, k.full, "symmetry \(i)")
        }
        XCTAssertEqual(repeats([l] + images), (900..<908).map { "L\($0) repeats L\(l.level)" })
        // a different head on a start-visible arrow: a different board under both keys
        var turned = l
        turned.level = 901
        let v = try XCTUnwrap(turned.arrows.firstIndex { $0.hiddenBy == nil && $0.layer <= 1 })
        turned.arrows[v].dir = turned.arrows[v].dir.opposite
        XCTAssertNotEqual(Validator.canonicalKeys(turned).visible, k.visible)
        XCTAssertNotEqual(Validator.canonicalKeys(turned).full, k.full)
        XCTAssertEqual(repeats([l, turned]), [])
        // the start-visible arrows alone repeat (what is under the doors differs): named by the visible key
        var underDoor = l
        underDoor.level = 902
        let h = try XCTUnwrap(underDoor.arrows.firstIndex(where: underADoor))
        underDoor.arrows[h].dir = underDoor.arrows[h].dir.opposite
        XCTAssertEqual(Validator.canonicalKeys(underDoor).visible, k.visible)
        XCTAssertNotEqual(Validator.canonicalKeys(underDoor).full, k.full)
        XCTAssertEqual(repeats([l, underDoor]), ["L902 repeats L\(l.level)"])
        // every arrow repeats but another set starts visible (a hidden arrow shown): named by the every-layer key
        var shown = l
        shown.level = 903
        shown.arrows[h].hiddenBy = nil
        XCTAssertNotEqual(Validator.canonicalKeys(shown).visible, k.visible)
        XCTAssertEqual(Validator.canonicalKeys(shown).full, k.full)
        XCTAssertEqual(repeats([l, shown]), ["L903 repeats L\(l.level)"])
    }

    func testDeadEndIsFound() {
        // SolverFixtures.elevatorTrap: the reference greedy (monotone moves first) clears it, but a random order that taps
        // the platform arrow first activates the elevator and strands two arrows facing each other
        XCTAssertEqual(errors(SolverFixtures.elevatorTrap), ["dead end: a random play order gets stuck with 2 arrows left"])
        // the same tube without the trap: no finding
        let pipe = ObstacleSpec(id: "p0", kind: .pipe, cells: [Cell(1, 2), Cell(1, 3), Cell(2, 3), Cell(3, 3), Cell(3, 2)],
                                ends: [PipeEnd(cell: Cell(1, 2), out: .up), PipeEnd(cell: Cell(3, 2), out: .up)], counter: 1,
                                counterAt: [1.0, 2.5])
        XCTAssertEqual(errors(lvl([a(0, [(1, 0), (1, 1)], .down)], [pipe])), [])
    }

    // MARK: provenance per form (PUBLISH B0; SPEC.md ruling 39 OD8)

    /// `.source` (design/levels.json) demands a recorded / video board's capture; `.publish` (the shipped bundle,
    /// App/Resources/Levels) demands that it is gone and that no "_" note ships. Each form's check catches the other's board.
    func testProvenanceCheckPerForm() throws {
        let src = C4Fixtures.level(C4Fixtures.slot(research: 47))
        XCTAssertEqual(src.source, .authored)
        XCTAssertNotNil(src.capture)
        var pub = src
        pub.capture = nil
        let source = Validator.Options(randomOrders: 1, gameRules: false)
        let publish = Validator.Options(randomOrders: 1, gameRules: false, provenance: .publish)
        func prov(_ l: LevelSpec, _ raw: JSONValue?, _ o: Validator.Options) -> [String] {
            Validator.checkLevel(l, raw: raw, sprites: nil, options: o).findings.filter { $0.area == .provenance }.map(\.message)
        }
        XCTAssertEqual(prov(src, nil, source), [])
        XCTAssertEqual(prov(pub, nil, source), ["no capture for a recorded level"])
        // FIX-2 lane B (N-01): the publish form is now the level WITHOUT capture, source and metrics (`publishModel`, what
        // `encodePublish` writes). Re-stated at the same strength — the shipped model passes, and each of the old forms is
        // caught — with new negative controls: a board stripped of its capture only (the old publish form) still says
        // "recorded" and carries the bot's metrics, and its bytes name both keys.
        let shipped = LevelJSON.publishModel(src)
        XCTAssertNotNil(src.metrics)
        XCTAssertEqual(prov(shipped, nil, publish), [])
        XCTAssertEqual(prov(pub, nil, publish), ["source / metrics in the publish form"])
        XCTAssertEqual(prov(src, nil, publish), ["capture in the publish form", "source / metrics in the publish form"])
        var bytes = try LevelJSON.encodePublish(src)
        XCTAssertEqual(try LevelJSON.decodeBundle(bytes), shipped, "the publish bytes decode to the publish model")
        XCTAssertEqual(prov(shipped, try ContentJSON.parse(bytes), publish), [])
        let old = try LevelJSON.encodeBundle(pub)
        XCTAssertEqual(prov(pub, try ContentJSON.parse(old), publish), ["source in the publish form", "metrics in the publish form"])
        bytes.insert(contentsOf: Data(#""_from":"a research note","#.utf8), at: bytes.startIndex + 1)
        XCTAssertEqual(prov(shipped, try ContentJSON.parse(bytes), publish), ["comment key _from in the publish form"])
    }

    // MARK: sprites (§4.14 with CONSISTENCY O-21 / O-23)

    func testSpriteCheck() throws {
        let l = C4Fixtures.level(C4Fixtures.slot(research: 47))   // doors, keys, tapes (v552 L47's board; PUBLISH B0: ships at L37)
        XCTAssertTrue(l.capture?.contains("-L047-") == true, "the board read from v552 L47")
        let needed = Set(l.obstacles.flatMap(Validator.spriteIDs))
        XCTAssertTrue(needed.contains("lockHex") && needed.contains("keyOnArrow"))
        XCTAssertTrue(needed.contains { $0.hasPrefix("tape") })
        XCTAssertEqual(Validator.check(l, sprites: SpriteCatalog(ids: needed)).filter { $0.area == .sprite }, [])
        var less = needed
        less.remove("lockHex")
        let f = Validator.check(l, sprites: SpriteCatalog(ids: less)).filter { $0.area == .sprite }
        XCTAssertFalse(f.isEmpty)
        XCTAssertTrue(f.allSatisfy { $0.message.contains("lockHex") })
        XCTAssertEqual(Validator.spriteIDs(ObstacleSpec(id: "b0", kind: .box, cells: [Cell(0, 0)])), ["boxRing"])
        XCTAssertEqual(Validator.spriteIDs(ObstacleSpec(id: "t0", kind: .tape, cells: [Cell(0, 0), Cell(0, 1), Cell(0, 2)])), ["tapeV3"])
        XCTAssertEqual(Validator.spriteIDs(ObstacleSpec(id: "t0", kind: .tape, cells: [Cell(0, 0), Cell(1, 0)])), ["tapeH2"])
        // the art folder the app bundles: the catalogue loads (@3x names) and holds every tape the content needs
        let art = try SpriteCatalog.load(folder: C4Fixtures.appRoot.appendingPathComponent("art/ui/out"))
        XCTAssertTrue(art.contains("lockHex") && art.contains("tapeV4") && art.contains("pipeMouth"))
    }

    // MARK: the game's rules gate

    func testGameRulesGateRunsTheDriver() {
        // 12 arrows in a column that must leave one by one: 12 × 0.6 s fits 180 s easily…
        let arrows = (0..<12).map { i in a(i, [(0, i + 1), (1, i + 1)], .right) }
        var l = lvl(arrows, cols: 3, rows: 14)
        XCTAssertEqual(Validator.checkLevel(l, raw: nil, sprites: nil, options: Validator.Options()).errors, [])
        // …but not a 60 s timer with a Hard-sized board: both rule books refuse it
        l = lvl((0..<90).map { i in a(i, [(0, i), (1, i)], .right) }, cols: 3, rows: 90, timer: 60)
        let e = Validator.checkLevel(l, raw: nil, sprites: nil, options: Validator.Options()).errors
        XCTAssertTrue(e.contains { $0.area == .value && $0.message == "grid 3x90" })
    }
}

/// The whole document (PC_C4_FULL=1): our verdict = the Python validator's on design/levels.json (0 errors, the L6 warning,
/// the same metric table), with the game's rules on every level.
final class C4FullValidatorTests: XCTestCase {
    override func setUpWithError() throws {
        guard C4Fixtures.full else { throw XCTSkip("PC_C4_FULL=1 runs the whole-document validation") }
    }

    func testWholeDocumentMatchesThePythonValidator() throws {
        let t0 = C4Fixtures.wallNow()
        let rep = Validator.checkDocument(C4Fixtures.doc)
        let s = C4Fixtures.wallNow() - t0
        XCTAssertEqual(rep.errors, [])
        XCTAssertEqual(rep.warnings.map(\.description), ["L6: cols 27 > 26: fit pitch below the 14.04 pt zoom floor"])
        XCTAssertEqual(rep.firstAppearance, ["linked": 7, "box": 11, "pipe": 21, "elevator": 31, "door": 33, "corner": 70])
        XCTAssertEqual(rep.levels.count, 150)
        var lines = [String(format: "Validator.checkDocument(Fixtures/content/levels.json): %d levels, %d errors, %d warnings, %.1f s (8 threads)",
                            rep.levels.count, rep.errors.count, rep.warnings.count, s), ""]
        for r in rep.levels {
            let m = try XCTUnwrap(r.measured)
            XCTAssertEqual(m.bundle, C4Fixtures.level(r.level).metrics, "L\(r.level)")
            lines.append("L\(r.level) rounds \(m.rounds) free \(m.freeAtStart) units \(m.units) arrows \(m.arrows) bot_time_left \(ContentJSON.pyRepr(m.botTimeLeft))")
        }
        C4Fixtures.evidence("c4-validate-levels-json.txt", lines.joined(separator: "\n"))
    }
}
