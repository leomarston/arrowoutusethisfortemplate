import XCTest
import Foundation
@testable import PathCore

/// C2 test helpers shared by RulesTests, SessionTests, ClockTests, ComboTests, GoldenRoundsTests and HeadlessTests.
/// Paths from #filePath (no SwiftPM resources, §2.4). Reports go to $PC_EVIDENCE_DIR when set (build/c2/ in C2 runs).
enum C2Fixtures {
    /// Packages/PathCore/Tests
    static var testsDir: URL { URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent() }
    /// apps/mazeout
    static var appRoot: URL { testsDir.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent() }
    static func fixture(_ name: String) -> URL { testsDir.appendingPathComponent("Fixtures/\(name)") }
    /// The frozen research corpus (C1's Fixtures/research, MANIFEST.txt: L032-L061 + their -openK states at 4a06449, byte-identical
    /// to research/levels): hermetic, so phone sessions adding L062+ files (or a disk clean-up) never move these tests.
    static func research(_ path: String) -> URL { testsDir.appendingPathComponent("Fixtures/research/\(path)") }

    static func data(_ url: URL) throws -> Data { try Data(contentsOf: url) }

    /// (Fixtures/research/)levels/L0NN.json merged with its L0NN-openK.json reveal states (C1's import path, unpatched).
    static func researchImport(_ n: Int) throws -> ImportedLevel {
        let dir = research("levels")
        let base = String(format: "L%03d", n)
        let opens = try FileManager.default.contentsOfDirectory(atPath: dir.path)
            .filter { $0.hasPrefix(base + "-open") && $0.hasSuffix(".json") }.sorted()
        return try LevelJSON.load(data(dir.appendingPathComponent(base + ".json")),
                                  reveals: opens.map { try data(dir.appendingPathComponent($0)) })
    }

    static let recordedLevels = Array(32...61)

    /// The COMPLETED recorded levels (Tests/tools/c2_levels.py → Fixtures/c2_recorded_levels.json): the research arrows
    /// plus the obstacle data the phone JSON lacks, each value cited in the file's provenance.
    static func completed() throws -> [Int: LevelSpec] {
        struct File: Decodable { let levels: [LevelSpec] }
        let f = try JSONDecoder().decode(File.self, from: data(fixture("c2_recorded_levels.json")))
        return Dictionary(uniqueKeysWithValues: f.levels.map { ($0.level, $0) })
    }

    static func evidence(_ name: String, _ text: String) {
        guard let dir = ProcessInfo.processInfo.environment["PC_EVIDENCE_DIR"], !dir.isEmpty else { return }
        let url = URL(fileURLWithPath: dir).appendingPathComponent(name)
        try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? Data(text.utf8).write(to: url)
    }

    // MARK: tiny level builder

    static func arrow(_ id: Int, _ cells: [(Int, Int)], _ dir: Dir, layer: Int = 1, hiddenBy: ObstacleID? = nil) -> ArrowSpec {
        ArrowSpec(id: ArrowID(id), cells: cells.map { Cell($0.0, $0.1) }, dir: dir, layer: layer, hiddenBy: hiddenBy)
    }

    static func level(_ cols: Int, _ rows: Int, _ arrows: [ArrowSpec], _ obstacles: [ObstacleSpec] = [], timer: Int = 180,
                      n: Int = 1, tag: LevelTag = .normal) -> LevelSpec {
        LevelSpec(level: n, source: .designed, cols: cols, rows: rows, timerSeconds: timer, tag: tag, arrows: arrows,
                  obstacles: obstacles)
    }

    static func cells(_ list: [(Int, Int)]) -> [Cell] { list.map { Cell($0.0, $0.1) } }
}

extension TapResolution {
    var exitPlan: ExitPlan? { if case .exit(let p) = self { return p }; return nil }
    var bumpPlan: BumpPlan? { if case .bump(let p) = self { return p }; return nil }
    var ignoreReason: IgnoreReason? { if case .ignored(let r) = self { return r }; return nil }
}

/// §4.4 row by row on small boards (every expectation is computed by hand in the comment next to it).
final class RulesTests: XCTestCase {
    typealias F = C2Fixtures
    let a0 = ArrowID(0), a1 = ArrowID(1), a2 = ArrowID(2), a3 = ArrowID(3), a4 = ArrowID(4), a5 = ArrowID(5)

    // MARK: the blocking rule

    /// A (0,1)→(1,1) → right; B vertical at column 4 crosses row 1. A's ray (2,1) (3,1) (4,1)=B.
    func crossing() -> LevelSpec {
        F.level(6, 3, [F.arrow(0, [(0, 1), (1, 1)], .right), F.arrow(1, [(4, 0), (4, 1), (4, 2)], .down)])
    }

    func testRayStopsAtTheFirstLiveOccupant() {
        let b = BoardState(level: crossing())
        let bump = b.resolve(tap: a0).bumpPlan
        XCTAssertEqual(bump?.blocker, .arrow(a1))
        XCTAssertEqual(bump?.gapCells, 2)                                 // (2,1) and (3,1) are empty
        XCTAssertEqual(bump?.contactPoint, Cell(4, 1))
        // contact = blocker arc 3 − stroke half 0.11 − apex(→) 0.36 = 2.53 (bump-1: 3 empty cells → 3.5 cells, motion §4)
        XCTAssertEqual(bump?.contactCells ?? 0, 3 - 0.11 - Metrics.headApexPast(.right), accuracy: 1e-9)
        XCTAssertEqual(bump?.path.cells, F.cells([(0, 1), (1, 1), (2, 1), (3, 1)]))
        XCTAssertEqual(bump?.path.toGridEdge ?? 0, 2.5, accuracy: 1e-9)   // the blocker cell's near edge
        XCTAssertEqual(b.freeUnits(), [[a1]])
        XCTAssertFalse(b.isFree(a0))
        XCTAssertTrue(b.isFree(a1))
    }

    func testExitPathToTheGridEdge() throws {
        let b = BoardState(level: crossing())
        let plan = try XCTUnwrap(b.resolve(tap: a1).exitPlan)
        XCTAssertEqual(plan.unit, [a1])
        XCTAssertNil(plan.tape)
        let p = try XCTUnwrap(plan.paths[a1])
        XCTAssertEqual(p.cells, F.cells([(4, 0), (4, 1), (4, 2)]))       // the head is on the last row
        XCTAssertEqual(p.toGridEdge, 0.5, accuracy: 1e-9)
        XCTAssertEqual(p.segments, [.body(-2..<0), .ray(0..<0.5)])
        XCTAssertEqual(p, ExitPath.plain(arrow: crossing().arrows[1], grid: crossing().grid))   // C1's obstacle-free case
    }

    /// The walk reaches the grid edge: a blocker on the LAST in-grid cell still blocks.
    func testBlockerOnTheLastCellOfTheRay() {
        let lv = F.level(5, 2, [F.arrow(0, [(0, 0), (1, 0)], .right), F.arrow(1, [(4, 1), (4, 0)], .up)])
        let b = BoardState(level: lv)
        XCTAssertEqual(b.resolve(tap: a0).bumpPlan?.blocker, .arrow(a1))
        XCTAssertEqual(b.resolve(tap: a0).bumpPlan?.gapCells, 2)
        b.commit(b.resolve(tap: a1))
        XCTAssertEqual(b.resolve(tap: a0).exitPlan?.paths[a0]?.toGridEdge, 3.5)
    }

    /// Queued taps (VERIFIED motion §3.1 P02): B leaves the blocking grid AT ITS TAP, before any ack.
    func testQueuedTapFreesAtTheTap() {
        let b = BoardState(level: crossing())
        b.commit(b.resolve(tap: a1))
        XCTAssertEqual(b.owner(of: Cell(4, 1)), nil)                     // vacated cells (dots) never block
        let plan = b.resolve(tap: a0).exitPlan
        XCTAssertNotNil(plan)
        XCTAssertEqual(plan?.paths[a0]?.cells.last, Cell(5, 1))
        XCTAssertEqual(plan?.paths[a0]?.toGridEdge ?? 0, 4.5, accuracy: 1e-9)
        XCTAssertEqual(b.resolve(tap: a1).ignoreReason, .moving)        // already on its way out
        b.commit(b.resolve(tap: a0))
        XCTAssertTrue(b.isCleared)
    }

    func testGapZeroContact() {
        // A (0,0)(1,0) → right, B vertical at column 2: adjacent → gap 0, contact 1 − 0.11 − 0.36 = 0.53 (fail.md §3 ≈ 0.5)
        let lv = F.level(4, 2, [F.arrow(0, [(0, 0), (1, 0)], .right), F.arrow(1, [(2, 1), (2, 0)], .up)])
        let bump = BoardState(level: lv).resolve(tap: a0).bumpPlan
        XCTAssertEqual(bump?.gapCells, 0)
        XCTAssertEqual(bump?.contactCells ?? 0, 0.53, accuracy: 0.001)
        XCTAssertEqual(bump?.path.segments, [.body(-1..<0), .ray(0..<0.5)])   // up to the blocker cell's near edge
        XCTAssertEqual(bump?.path.cells, F.cells([(0, 0), (1, 0)]))
    }

    func testOwnBodyNeverBlocksAndUnknownIDs() {
        let b = BoardState(level: crossing())
        XCTAssertEqual(b.resolve(tap: ArrowID(99)).ignoreReason, .noArrow)
        XCTAssertEqual(b.owner(of: Cell(0, 1)), a0)
        XCTAssertEqual(b.owner(of: Cell(-1, 0)), nil)
        XCTAssertEqual(b.live, [a0, a1])
        XCTAssertEqual(b.hidden, [])
    }

    // MARK: bumps and marks

    /// A bump changes nothing logical at the tap; the contact ack marks it red; a red arrow is still an ordinary arrow
    /// (VERIFIED levels.md L47/L48); a bumping arrow cannot be re-tapped (DECISION).
    func testBumpMarkAndMarkedArrowStaysTappable() throws {
        let b = BoardState(level: crossing())
        let r = b.resolve(tap: a0)
        XCTAssertEqual(b.commit(r), [])
        XCTAssertTrue(b.isBumping(a0))
        XCTAssertEqual(b.resolve(tap: a0).ignoreReason, .bumping)
        XCTAssertFalse(b.isMarked(a0))
        XCTAssertEqual(b.ack(.bumpContact(a0)), [.bumpContact(a0, repeat: false), .arrowMarked(a0)])
        XCTAssertTrue(b.isMarked(a0))
        XCTAssertEqual(b.ack(.bumpFinished(a0)), [])
        XCTAssertFalse(b.isBumping(a0))
        // a second bump of the red arrow is a repeat (no heart, fail.md §3)
        b.commit(b.resolve(tap: a0))
        XCTAssertEqual(b.ack(.bumpContact(a0)), [.bumpContact(a0, repeat: true)])
        b.ack(.bumpFinished(a0))
        b.commit(b.resolve(tap: a1))
        XCTAssertNotNil(b.resolve(tap: a0).exitPlan)                      // red, free → it leaves
        XCTAssertEqual(b.markedArrows, [a0])
    }

    // MARK: tape (Linked Arrows)

    /// Two parallel ↑ arrows at columns 1 and 2 under one tape; C blocks column 2 at row 0.
    func taped(blocked: Bool) -> LevelSpec {
        var arrows = [F.arrow(0, [(1, 3), (1, 2)], .up), F.arrow(1, [(2, 3), (2, 2)], .up)]
        if blocked { arrows.append(F.arrow(2, [(3, 0), (2, 0)], .left)) }
        return F.level(5, 4, arrows, [ObstacleSpec(id: "t0", kind: .tape, cells: F.cells([(1, 2), (2, 2)]), arrows: [a0, a1])])
    }

    /// VERIFIED L32 4/4: one tap on any member sends the whole bundle iff every member's ray is clear.
    func testTapeAllClearSendsTheBundle() throws {
        let b = BoardState(level: taped(blocked: false))
        let plan = try XCTUnwrap(b.resolve(tap: a1).exitPlan)
        XCTAssertEqual(plan.tapped, a1)
        XCTAssertEqual(plan.unit, [a0, a1])
        XCTAssertEqual(plan.tape, "t0")
        XCTAssertEqual(Set(plan.paths.keys), [a0, a1])
        XCTAssertEqual(b.unit(of: a0), [a0, a1])
        XCTAssertEqual(b.freeUnits(), [[a0, a1]])
        b.commit(.exit(plan))
        XCTAssertTrue(b.isCleared)
        XCTAssertTrue(b.isDone("t0"))                                     // the tape left with its bundle
    }

    /// One member blocked → the WHOLE bundle bumps (VERIFIED all-blocked, fail.md §3; some-clear PENDING → same rule):
    /// the plan of the member that makes contact first; every member turns red at contact; one contact.
    func testTapeSomeBlockedBumpsTheBundle() throws {
        let b = BoardState(level: taped(blocked: true))
        let r = b.resolve(tap: a0)                                        // the tapped member itself is clear
        let bump = try XCTUnwrap(r.bumpPlan)
        XCTAssertEqual(bump.arrow, a1)
        XCTAssertEqual(bump.blocker, .arrow(a2))
        XCTAssertEqual(bump.gapCells, 1)
        b.commit(r)
        XCTAssertTrue(b.isBumping(a0) && b.isBumping(a1))
        XCTAssertEqual(b.resolve(tap: a0).ignoreReason, .bumping)
        XCTAssertEqual(b.ack(.bumpContact(a1)), [.bumpContact(a1, repeat: false), .arrowMarked(a0), .arrowMarked(a1)])
        b.ack(.bumpFinished(a1))
        XCTAssertFalse(b.isBumping(a0))
        XCTAssertFalse(b.isFree(a0))                                      // a free member alone never leaves
        b.commit(b.resolve(tap: a2))
        XCTAssertEqual(b.resolve(tap: a0).exitPlan?.unit, [a0, a1])
    }

    func testTapeTappedBumpsPolicy() throws {
        var rules = RulesTuning()
        rules.tape.blockedPolicy = .tappedBumps
        let b = BoardState(level: taped(blocked: true), rules: rules)
        let r = b.resolve(tap: a1)
        XCTAssertEqual(r.bumpPlan?.arrow, a1)
        b.commit(r)
        XCTAssertTrue(b.isBumping(a1))
        XCTAssertFalse(b.isBumping(a0))
        XCTAssertEqual(b.ack(.bumpContact(a1)), [.bumpContact(a1, repeat: false), .arrowMarked(a1)])
    }

    // MARK: doors and keys

    /// Row 0: K (1,0)→(0,0) ← carries key k0. Doors d0 (order 0) at (3,2) and d1 (order 1) at (4,2) hide H0 and
    /// H1; A ↓ at (3,0)(3,1) aims into d0. Keys go to the lowest-order locked door (VERIFIED L33 left → right).
    func doors(explicit: ObstacleID? = nil) -> LevelSpec {
        F.level(6, 4, [
            F.arrow(0, [(1, 0), (0, 0)], .left),
            F.arrow(1, [(3, 0), (3, 1)], .down),
            F.arrow(2, [(3, 2), (3, 3)], .down, hiddenBy: "d0"),
            F.arrow(3, [(4, 2), (4, 3)], .down, hiddenBy: "d1"),
            F.arrow(4, [(5, 1), (5, 0)], .up),
        ], [
            ObstacleSpec(id: "d1", kind: .door, cells: F.cells([(4, 2), (4, 3)]), order: 1, reveals: [a3]),
            ObstacleSpec(id: "d0", kind: .door, cells: F.cells([(3, 2), (3, 3)]), order: 0, reveals: [a2]),
            ObstacleSpec(id: "k0", kind: .key, cells: F.cells([(0, 0), (1, 0)]), arrows: [a0], opens: explicit),
        ])
    }

    func testDoorBlocksUntilTheBurstAck() throws {
        let b = BoardState(level: doors())
        XCTAssertEqual(b.live, [a0, a1, a4])
        XCTAssertEqual(b.hidden, [a2, a3])
        XCTAssertEqual(b.resolve(tap: a1).bumpPlan?.blocker, .obstacle("d0"))
        XCTAssertEqual(b.resolve(tap: a1).bumpPlan?.contactCells ?? 0, 1 - 0.5 - Metrics.headApexPast(.down), accuracy: 1e-9)
        XCTAssertEqual(b.resolve(tap: a2).ignoreReason, .hidden)
        let r = b.resolve(tap: a0)
        let plan = try XCTUnwrap(r.exitPlan)
        XCTAssertEqual(plan.beats, [.keyReleased(key: "k0", door: "d0", s: 0)])
        XCTAssertEqual(b.commit(r), [.keyDispatched(key: "k0", door: "d0")])
        XCTAssertEqual(b.doorState("d0"), .targeted)
        // still blocking during the ≈ 1.14 s flight (VERIFIED motion §5.2): the door opens only on the board's burst
        XCTAssertEqual(b.resolve(tap: a1).bumpPlan?.blocker, .obstacle("d0"))
        XCTAssertEqual(b.ack(.doorBurst("d0")), [.doorOpened("d0", revealed: [a2])])
        XCTAssertEqual(b.doorState("d0"), .open)
        XCTAssertEqual(b.doorState("d1"), .locked)
        XCTAssertEqual(b.ack(.doorBurst("d0")), [])                      // idempotent
        XCTAssertEqual(b.resolve(tap: a1).bumpPlan?.blocker, .arrow(a2))  // the revealed arrow is live and blocks
        XCTAssertNotNil(b.resolve(tap: a2).exitPlan)
        XCTAssertFalse(b.isCleared)                                       // d1 still hides a3
    }

    func testKeyWithExplicitDoor() throws {
        let b = BoardState(level: doors(explicit: "d1"))
        XCTAssertEqual(b.resolve(tap: a0).exitPlan?.beats, [.keyReleased(key: "k0", door: "d1", s: 0)])
    }

    // MARK: pipes

    /// A (0,1)(1,1) → right enters mouth (3,1) [out ←]; tube (3,1)(4,1)(4,2)(4,3); far mouth (4,3) [out ↓] → off the
    /// grid. B (6,2)(5,2) ← meets the tube's side at (4,2). Counter 2 (cells listed unordered on purpose).
    func piped(counter: Int? = 2, extra: [ArrowSpec] = []) -> LevelSpec {
        F.level(7, 4, [F.arrow(0, [(0, 1), (1, 1)], .right), F.arrow(1, [(6, 2), (5, 2)], .left)] + extra, [
            ObstacleSpec(id: "p0", kind: .pipe, cells: F.cells([(4, 3), (4, 2), (3, 1), (4, 1)]),
                         ends: [PipeEnd(cell: Cell(4, 3), out: .down), PipeEnd(cell: Cell(3, 1), out: .left)], counter: counter),
        ])
    }

    func testPipePassageAndCounter() throws {
        let b = BoardState(level: piped())
        XCTAssertEqual(b.resolve(tap: a1).bumpPlan?.blocker, .obstacle("p0"))      // a tube side blocks
        let r = b.resolve(tap: a0)
        let plan = try XCTUnwrap(r.exitPlan)
        let p = try XCTUnwrap(plan.paths[a0])
        // body, (2,1), then the tube in travel order, then off the grid below (4,3): arcs (2,1)=1 … (4,3)=5
        XCTAssertEqual(p.cells, F.cells([(0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (4, 2), (4, 3)]))
        XCTAssertEqual(p.segments, [.body(-1..<0), .ray(0..<1.5), .tube("p0", 1.5..<5.5)])
        XCTAssertEqual(p.toGridEdge, 5.5, accuracy: 1e-9)
        // the default: the counter changes as the head leaves the far mouth (pipe.countAt = leave, O-15)
        XCTAssertEqual(RulesTuning.default.pipe.countAt, .leave)
        XCTAssertEqual(plan.beats, [.enterTube("p0", a0, s: 1.5), .leaveTube("p0", a0, s: 5.5),
                                    .pipeCount("p0", remaining: 1, s: 5.5)])
        XCTAssertEqual(b.commit(r), [.pipeUsed("p0", remaining: 1)])     // −1 at the tap
        XCTAssertEqual(b.counters["p0"], 1)
        XCTAssertFalse(b.isDone("p0"))
        // the counter change at the near mouth instead (pipe.countAt = enter)
        var rules = RulesTuning(); rules.pipe.countAt = .enter
        XCTAssertEqual(BoardState(level: piped(), rules: rules).resolve(tap: a0).exitPlan?.beats,
                       [.enterTube("p0", a0, s: 1.5), .pipeCount("p0", remaining: 1, s: 1.5), .leaveTube("p0", a0, s: 5.5)])
    }

    /// At 0 the pipe breaks at the tap (logical) and its cells become empty (VERIFIED L35 2 → 1 → 0).
    func testPipeBreaksAtZeroAndItsCellsEmpty() throws {
        let b = BoardState(level: piped(counter: 1))
        let r = b.resolve(tap: a0)
        XCTAssertEqual(r.exitPlan?.beats.last, .pipeBreak("p0", s: 5.5))
        XCTAssertEqual(b.commit(r), [.pipeUsed("p0", remaining: 0), .pipeBroken("p0")])
        XCTAssertTrue(b.isDone("p0"))
        XCTAssertNil(b.counters["p0"])
        let after = try XCTUnwrap(b.resolve(tap: a1).exitPlan)          // broken: the tube cells are empty now
        XCTAssertEqual(after.paths[a1]?.cells.last, Cell(0, 2))
        XCTAssertEqual(after.beats, [])
    }

    /// A pipe with no counter in the data never breaks (DECISION; the phone JSON carries none).
    func testPipeWithoutCounterIsUnlimited() {
        let b = BoardState(level: piped(counter: nil))
        XCTAssertEqual(b.commit(b.resolve(tap: a0)), [])
        XCTAssertFalse(b.isDone("p0"))
        XCTAssertEqual(b.resolve(tap: a1).bumpPlan?.blocker, .obstacle("p0"))
    }

    /// A ray blocked after the far mouth is a bump that consumes nothing (DECISION, PENDING-gameplay).
    func testPipeBumpConsumesNothing() throws {
        let lv = F.level(7, 5, [F.arrow(0, [(0, 1), (1, 1)], .right), F.arrow(1, [(3, 4), (4, 4), (5, 4)], .right)], [
            ObstacleSpec(id: "p0", kind: .pipe, cells: F.cells([(3, 1), (4, 1), (4, 2), (4, 3)]),
                         ends: [PipeEnd(cell: Cell(3, 1), out: .left), PipeEnd(cell: Cell(4, 3), out: .down)], counter: 2),
        ])
        let b = BoardState(level: lv)
        let r = b.resolve(tap: a0)
        let bump = try XCTUnwrap(r.bumpPlan)
        XCTAssertEqual(bump.blocker, .arrow(a1))                          // (4,4) below the far mouth
        XCTAssertEqual(bump.path.segments, [.body(-1..<0), .ray(0..<1.5), .tube("p0", 1.5..<5.5)])
        XCTAssertEqual(bump.gapCells, 5)                                  // (2,1) + 4 tube cells
        XCTAssertEqual(bump.contactCells, 6 - 0.11 - Metrics.headApexPast(.down), accuracy: 1e-9)
        XCTAssertEqual(b.commit(r), [])
        XCTAssertEqual(b.counters["p0"], 2)
    }

    /// Chained pipes (the ray leaves one mouth straight into the next) and the loop guard.
    func testChainedPipesAndTheHopGuard() throws {
        // p0 straight (2,1)[←]…(3,1)[→]; p1 (4,1)[←]…(4,2)[↓] → off the 3-row grid
        let lv = F.level(6, 3, [F.arrow(0, [(0, 1), (1, 1)], .right)], [
            ObstacleSpec(id: "p0", kind: .pipe, cells: F.cells([(2, 1), (3, 1)]),
                         ends: [PipeEnd(cell: Cell(2, 1), out: .left), PipeEnd(cell: Cell(3, 1), out: .right)], counter: 1),
            ObstacleSpec(id: "p1", kind: .pipe, cells: F.cells([(4, 1), (4, 2)]),
                         ends: [PipeEnd(cell: Cell(4, 1), out: .left), PipeEnd(cell: Cell(4, 2), out: .down)], counter: 1),
        ])
        let plan = try XCTUnwrap(BoardState(level: lv).resolve(tap: a0).exitPlan)
        XCTAssertEqual(plan.paths[a0]?.segments, [.body(-1..<0), .ray(0..<0.5), .tube("p0", 0.5..<2.5), .tube("p1", 2.5..<4.5)])
        XCTAssertEqual(plan.paths[a0]?.toGridEdge, 4.5)
        XCTAssertEqual(plan.beats.filter { if case .pipeBreak = $0 { return true }; return false },
                       [.pipeBreak("p0", s: 2.5), .pipeBreak("p1", s: 4.5)])
        var rules = RulesTuning(); rules.pipe.maxHops = 1
        XCTAssertEqual(BoardState(level: lv, rules: rules).resolve(tap: a0).bumpPlan?.blocker, .obstacle("p1"))
        // a pipe without two mouths is only a wall
        let wall = F.level(5, 2, [F.arrow(0, [(0, 0), (1, 0)], .right)],
                           [ObstacleSpec(id: "p0", kind: .pipe, cells: F.cells([(3, 0), (3, 1)]), counter: 1)])
        XCTAssertEqual(BoardState(level: wall).resolve(tap: a0).bumpPlan?.blocker, .obstacle("p0"))
    }

    // MARK: box / curtain

    /// Every arrow cleared ANYWHERE lowers every box by 1 at the tap (VERIFIED L50 10/10, L51 all together); at 0 it
    /// breaks, its cells empty and the arrows under it go live. Tape members count one each.
    func testBoxesCountDownTogether() throws {
        let lv = F.level(6, 4, [
            F.arrow(0, [(0, 0), (1, 0)], .left), F.arrow(1, [(0, 1), (1, 1)], .left),
            F.arrow(2, [(5, 3), (4, 3)], .left),                                   // aims into box b0 at (3,3)
            F.arrow(3, [(2, 3), (3, 3)], .right, hiddenBy: "b0"),
        ], [
            ObstacleSpec(id: "b0", kind: .box, cells: F.cells([(2, 3), (3, 3)]), counter: 2, reveals: [a3]),
            ObstacleSpec(id: "c0", kind: .curtain, cells: F.cells([(5, 0)]), counter: 3),
        ])
        let b = BoardState(level: lv)
        XCTAssertEqual(b.resolve(tap: a2).bumpPlan?.blocker, .obstacle("b0"))
        var r = b.resolve(tap: a0)
        XCTAssertEqual(r.exitPlan?.beats, [.counterTick("b0", remaining: 1, s: 0), .counterTick("c0", remaining: 2, s: 0)])
        XCTAssertEqual(b.commit(r), [.counterChanged("b0", remaining: 1), .counterChanged("c0", remaining: 2)])
        r = b.resolve(tap: a1)
        XCTAssertEqual(r.exitPlan?.beats, [.counterTick("b0", remaining: 0, s: 0), .counterBreak("b0", s: 0),
                                           .counterTick("c0", remaining: 1, s: 0)])
        XCTAssertEqual(b.commit(r), [.counterChanged("b0", remaining: 0), .counterBroken("b0", revealed: [a3]),
                                     .counterChanged("c0", remaining: 1)])
        XCTAssertTrue(b.isLive(a3))
        XCTAssertEqual(b.resolve(tap: a2).bumpPlan?.blocker, .arrow(a3))
        XCTAssertEqual(b.counters, ["c0": 1])
    }

    // MARK: elevator (video V2 L31+)

    func testElevatorActivatesWhenThePlatformEmpties() throws {
        let lv = F.level(5, 3, [
            F.arrow(0, [(1, 1), (0, 1)], .left), F.arrow(1, [(2, 1), (2, 0)], .up),
            F.arrow(2, [(1, 1), (2, 1)], .right, layer: 2, hiddenBy: "e0"),
        ], [ObstacleSpec(id: "e0", kind: .elevator, cells: F.cells([(0, 1), (1, 1), (2, 1)]), arrows: [a0, a1], reveals: [a2])])
        let b = BoardState(level: lv)
        XCTAssertEqual(b.hidden, [a2])
        var r = b.resolve(tap: a0)
        XCTAssertEqual(r.exitPlan?.beats, [])
        XCTAssertEqual(b.commit(r), [])
        r = b.resolve(tap: a1)
        XCTAssertEqual(r.exitPlan?.beats, [.elevatorEmptied("e0", s: 0)])
        XCTAssertEqual(b.commit(r), [.elevatorActivated("e0", revealed: [a2])])   // layer 2 live at once (V2 L32)
        XCTAssertNotNil(b.resolve(tap: a2).exitPlan)
    }

    // MARK: corner (INFERRED web §3; supported for content)

    func testCornerTurnsFromAcceptingSidesOnly() throws {
        // x0 at (2,1), turn upRight: a ray moving ↑ leaves →, and the reverse: ← leaves ↓; ↓ and → are blocked
        let lv = F.level(5, 4, [F.arrow(0, [(4, 1), (3, 1)], .left), F.arrow(1, [(2, 3), (2, 2)], .up),
                                F.arrow(2, [(0, 0), (1, 0), (2, 0)], .down)],
                         [ObstacleSpec(id: "x0", kind: .corner, cells: [Cell(2, 1)], turn: .upRight)])
        let b = BoardState(level: lv)
        XCTAssertEqual(b.resolve(tap: a2).bumpPlan?.blocker, .obstacle("x0"))
        let up = try XCTUnwrap(b.resolve(tap: a1).bumpPlan)                // ↑ turns → into A's head
        XCTAssertEqual(up.blocker, .arrow(a0))
        XCTAssertEqual(up.path.cells, F.cells([(2, 3), (2, 2), (2, 1)]))
        XCTAssertEqual(up.path.segments, [.body(-1..<0), .ray(0..<1), .corner("x0", at: 1), .ray(1..<1.5)])
        let left = try XCTUnwrap(b.resolve(tap: a0).bumpPlan)              // ← turns ↓ into B's head
        XCTAssertEqual(left.blocker, .arrow(a1))
        XCTAssertEqual(left.contactCells, 2 - 0.11 - Metrics.headApexPast(.down), accuracy: 1e-9)
    }

    func testCornerPathAndBeat() throws {
        let lv = F.level(5, 4, [F.arrow(1, [(2, 3), (2, 2)], .up)],
                         [ObstacleSpec(id: "x0", kind: .corner, cells: [Cell(2, 1)], turn: .upRight)])
        let plan = try XCTUnwrap(BoardState(level: lv).resolve(tap: a1).exitPlan)
        let p = try XCTUnwrap(plan.paths[a1])
        XCTAssertEqual(p.cells, F.cells([(2, 3), (2, 2), (2, 1), (3, 1), (4, 1)]))
        XCTAssertEqual(p.segments, [.body(-1..<0), .ray(0..<1), .corner("x0", at: 1), .ray(1..<3.5)])
        XCTAssertEqual(plan.beats, [.corner("x0", a1, s: 1)])
        XCTAssertEqual(PathTrack(path: p).direction(at: 3), .right)
    }

    /// Corner turns share the pipes' hop guard (`pipe.maxHops`, arrowcore MAX_HOPS 16: the 17th hop blocks), so a ray can
    /// never loop for ever. A staircase of n corners: (2+k, k) upLeft (→ turns ↓), (2+k, k+1) downRight (↓ turns →).
    func testCornerTurnsShareThePipeHopGuard() throws {
        func stair(_ n: Int, dx: Int = 0, pipe: Bool = false) -> LevelSpec {
            var obs = (0..<n).map { j -> ObstacleSpec in
                let k = j / 2
                return ObstacleSpec(id: ObstacleID("x\(j)"), kind: .corner, cells: [j % 2 == 0 ? Cell(2 + dx + k, k) : Cell(2 + dx + k, k + 1)],
                                    turn: j % 2 == 0 ? .upLeft : .downRight)
            }
            if pipe {                                                   // a straight tube (2,0)[←]…(3,0)[→] before the stairs
                obs.insert(ObstacleSpec(id: "p0", kind: .pipe, cells: F.cells([(2, 0), (3, 0)]),
                                        ends: [PipeEnd(cell: Cell(2, 0), out: .left), PipeEnd(cell: Cell(3, 0), out: .right)]), at: 0)
            }
            return F.level(14, 12, [F.arrow(0, [(0, 0), (1, 0)], .right)], obs)
        }
        let p16 = try XCTUnwrap(BoardState(level: stair(16)).resolve(tap: a0).exitPlan?.paths[a0])     // 16 hops: through
        XCTAssertEqual(p16.segments.filter { if case .corner = $0 { return true }; return false }.count, 16)
        XCTAssertEqual(BoardState(level: stair(17)).resolve(tap: a0).bumpPlan?.blocker, .obstacle("x16"))   // the 17th blocks
        // the content rules' walk (arrowcore) says the same
        XCTAssertNil(RefBoard(stair(16)).walk(0, ignore: []).blocker)
        XCTAssertEqual(RefBoard(stair(17)).walk(0, ignore: []).blocker, .obstacle(16))
        // SHARED with pipes: with maxHops 2, the pipe is hop 1, x0 hop 2, and x1 blocks (separate counters would let x1 pass)
        var rules = RulesTuning(); rules.pipe.maxHops = 2
        XCTAssertEqual(BoardState(level: stair(4, dx: 2, pipe: true), rules: rules).resolve(tap: a0).bumpPlan?.blocker, .obstacle("x1"))
        XCTAssertEqual(BoardState(level: stair(4, dx: 2), rules: rules).resolve(tap: a0).bumpPlan?.blocker, .obstacle("x2"))
    }

    // MARK: a locked door blocks before the obstacle under it (content recast 2026-09-25, SPEC.md §5 item 26, v552 L069)

    /// L069 hides three pipes under its doors. Built from L069's own data: its door d0 drawn tight around p0 (rows 28-33,
    /// so p0's mouths (1,28) and (6,28) sit on the door's top edge), its key arrow 13 (column 1, head at (1,25), pointing
    /// down at the mouth (1,28)) and a free key arrow. While d0 is shut — locked, and still while its key flies — the ray
    /// stops at the door and the pipe does nothing, whatever the order of the obstacle list and under both rule books;
    /// after the burst the same ray runs through p0 (counter 2 → 1) and out of (6,28) upward.
    func testLockedDoorBlocksBeforeThePipeUnderIt_L069() throws {
        let l69 = C4Fixtures.level(C4Fixtures.slot(research: 69))      // PUBLISH B0: v552 L69's board ships at L59
        XCTAssertTrue(l69.capture?.contains("-L069-") == true, "the board read from v552 L69")
        let d0 = try XCTUnwrap(l69.obstacles.first { $0.id == "d0" })
        let p0 = try XCTUnwrap(l69.obstacles.first { $0.id == "p0" })
        XCTAssertTrue(Set(p0.cells).isSubset(of: Set(d0.cells)), "L069: p0 lies under d0")
        XCTAssertEqual(p0.ends, [PipeEnd(cell: Cell(1, 28), out: .up), PipeEnd(cell: Cell(6, 28), out: .up)])
        let a13 = try XCTUnwrap(l69.arrows.first { $0.id == ArrowID(13) })
        XCTAssertEqual(a13.dir, .down)
        XCTAssertEqual(a13.cells.last, Cell(1, 25))
        var tight = d0
        tight.cells = d0.cells.filter { $0.r >= 28 }
        tight.reveals = []
        let arrows = [ArrowSpec(id: a0, cells: a13.cells, dir: a13.dir), F.arrow(1, [(24, 0), (25, 0)], .right)]
        let key = ObstacleSpec(id: "k0", kind: .key, cells: F.cells([(24, 0), (25, 0)]), arrows: [a1])
        for obstacles in [[tight, key, p0], [p0, key, tight]] {          // doors listed first (as L069) and pipes first
            let lv = F.level(l69.cols, l69.rows, arrows, obstacles)
            let order = obstacles.map(\.id.raw).joined(separator: ",")
            let b = BoardState(level: lv)
            let bump = try XCTUnwrap(b.resolve(tap: a0).bumpPlan, order)
            XCTAssertEqual(bump.blocker, .obstacle("d0"), order)
            XCTAssertEqual(bump.path.cells.last, Cell(1, 27), order)     // (1,26), (1,27), then the door's edge at the mouth
            XCTAssertFalse(bump.path.segments.contains { if case .tube = $0 { return true }; return false }, order)
            let S = RefStatic(lv)
            XCTAssertEqual(RefBoard(S).walk(0, ignore: []).blocker, .obstacle(S.obsIndex["d0"]!), order)
            XCTAssertEqual(ContentRules.metrics(lv).rounds, 2, order)    // the key first, then arrow 13 through the pipe
            XCTAssertEqual(ContentRules.metrics(lv).freeAtStart, 1, order)
            // the key: d0 targeted — still shut until the burst
            XCTAssertEqual(b.commit(b.resolve(tap: a1)), [.keyDispatched(key: "k0", door: "d0")])
            XCTAssertEqual(b.resolve(tap: a0).bumpPlan?.blocker, .obstacle("d0"), order)
            XCTAssertEqual(b.ack(.doorBurst("d0")), [.doorOpened("d0", revealed: [])])
            let r = b.resolve(tap: a0)
            let plan = try XCTUnwrap(r.exitPlan, order)
            let path = try XCTUnwrap(plan.paths[a0])
            XCTAssertTrue(path.segments.contains { if case .tube(let id, _) = $0 { return id == "p0" }; return false }, order)
            XCTAssertEqual(path.cells.last, Cell(6, 0), order)             // out of (6,28) and up column 6 off the grid
            XCTAssertEqual(b.commit(r), [.pipeUsed("p0", remaining: 1)], order)
            // content rules: with d0 open the walk passes p0
            var rb = RefBoard(S)
            rb.doorOpen[S.obsIndex["d0"]!] = true
            let w = rb.walk(0, ignore: [])
            XCTAssertNil(w.blocker, order)
            XCTAssertEqual(w.passages, [S.obsIndex["p0"]!], order)
        }
    }

    /// The shipped L069 does not depend on its obstacle list's order either: pipes listed before the doors give the same
    /// free arrows at the start, the same solution and a HeadlessDriver win.
    func testL069IsTheSameWithThePipesListedFirst() {
        let l = C4Fixtures.level(C4Fixtures.slot(research: 69))        // PUBLISH B0: v552 L69's board ships at L59
        XCTAssertTrue(l.capture?.contains("-L069-") == true, "the board read from v552 L69")
        XCTAssertEqual(l.obstacles.filter { $0.kind == .pipe }.count, 3, "v552 L69 hides three pipes under its doors")
        var re = l
        re.obstacles = l.obstacles.filter { $0.kind == .pipe } + l.obstacles.filter { $0.kind != .pipe }
        XCTAssertEqual(BoardState(level: re).freeUnits(), BoardState(level: l).freeUnits())
        let g1 = Solver.greedy(l), g2 = Solver.greedy(re)
        XCTAssertTrue(g1.solved)
        XCTAssertEqual(g1.order, g2.order)
        XCTAssertEqual(ContentRules.metrics(re).bundle, l.metrics)
        var c = DriverConfig(tapInterval: 0.6)
        c.recordEvents = false
        XCTAssertTrue(HeadlessDriver.play(level: re, config: c).won)
    }

    /// A corner under a door waits for the burst too: door (0,3)-(5,5), corner x0 on its top edge at (2,3) (downRight: ↓
    /// turns →), arrow A above it pointing down, a key arrow K.
    func testCornerUnderADoorWaitsForTheBurst() throws {
        let door = ObstacleSpec(id: "d0", kind: .door, cells: (3...5).flatMap { r in (0...5).map { Cell($0, r) } }, order: 0)
        let x0 = ObstacleSpec(id: "x0", kind: .corner, cells: [Cell(2, 3)], turn: .downRight)
        let key = ObstacleSpec(id: "k0", kind: .key, cells: F.cells([(4, 0), (5, 0)]), arrows: [a1])
        let arrows = [F.arrow(0, [(2, 0), (2, 1)], .down), F.arrow(1, [(4, 0), (5, 0)], .right)]
        for obstacles in [[door, key, x0], [x0, key, door]] {
            let lv = F.level(6, 6, arrows, obstacles)
            let b = BoardState(level: lv)
            let bump = try XCTUnwrap(b.resolve(tap: a0).bumpPlan)
            XCTAssertEqual(bump.blocker, .obstacle("d0"))
            XCTAssertEqual(bump.path.cells.last, Cell(2, 2))              // stopped at the door's edge: no turn at x0
            XCTAssertFalse(bump.path.segments.contains { if case .corner = $0 { return true }; return false })
            let S = RefStatic(lv)
            XCTAssertEqual(RefBoard(S).walk(0, ignore: []).blocker, .obstacle(S.obsIndex["d0"]!))
            b.commit(b.resolve(tap: a1))
            b.ack(.doorBurst("d0"))
            let p = try XCTUnwrap(b.resolve(tap: a0).exitPlan?.paths[a0])
            XCTAssertEqual(Array(p.cells.suffix(4)), F.cells([(2, 3), (3, 3), (4, 3), (5, 3)]))
            XCTAssertTrue(p.segments.contains(.corner("x0", at: 2)))
        }
    }

    // MARK: copies, units, tuning

    func testCopyIsIndependent() {
        let b = BoardState(level: crossing())
        let c = b.copy()
        c.commit(c.resolve(tap: a1))
        XCTAssertTrue(b.isLive(a1))
        XCTAssertFalse(c.isAlive(a1))
        XCTAssertEqual(b.freeUnits(), [[a1]])
        XCTAssertEqual(c.freeUnits(), [[a0]])
    }

    func testRulesTuningDecodesTolerantly() throws {
        let empty = try JSONDecoder().decode(RulesTuning.self, from: Data("{}".utf8))
        XCTAssertEqual(empty, RulesTuning.default)
        let partial = try JSONDecoder().decode(RulesTuning.self, from: Data(#"{"combo":{"window":1.2},"lives":{"refillSeconds":1800}}"#.utf8))
        XCTAssertEqual(partial.combo.window, 1.2)
        XCTAssertTrue(partial.combo.bumpBreaks)
        XCTAssertEqual(RulesTuning.unknownKeys(in: Data(#"{"combo":{"windw":1},"lives":{}}"#.utf8)), ["combo.windw", "lives"])
        let (tuned, problems) = RulesTuning.load(json: Data(#"{"rewards":{"hard":61}}"#.utf8),
                                                 overrides: ["combo.window": "1.1", "clock.alerts": "10;5", "tape.blockedPolicy": "tappedBumps"])
        XCTAssertEqual(problems, [])
        XCTAssertEqual(tuned.rewards.hard, 61)
        XCTAssertEqual(tuned.combo.window, 1.1)
        XCTAssertEqual(tuned.clock.alerts, [10, 5])
        XCTAssertEqual(tuned.tape.blockedPolicy, .tappedBumps)
        XCTAssertEqual(RulesTuning.load(json: Data("[1]".utf8)).problems.count, 1)
        // the shipped rules.json decodes (it also carries the sections C3's EconomyRules decodes: economy, lives, streak,
        // claw, shop — SPEC-gameplay §15; boosters.hintPolicy, CONSISTENCY K-8, is read by RulesTuning since WP0c)
        let shipped = try C2Fixtures.data(C2Fixtures.appRoot.appendingPathComponent("App/Resources/Tuning/rules.json"))
        XCTAssertEqual(RulesTuning.load(json: shipped).problems, [])
        // WP0b applied the CONSISTENCY §20 data corrections to the file and WP0c (SPEC.md §5 item 29) moved the compiled
        // defaults to the same ruled values (pipe.countAt leave O-15, hit.radiusPt 22 G-5, boosters.freezeFlight 1.6 K-3,
        // boosters.hintPolicy unblocksMost K-8): the shipped file IS the compiled defaults
        XCTAssertEqual(RulesTuning.load(json: shipped).rules, RulesTuning.default, "rules.json = the compiled defaults")
        let d = RulesTuning.default
        XCTAssertEqual(d.pipe.countAt, .leave)
        XCTAssertEqual(d.hit.radiusPt, 22)
        XCTAssertEqual(d.boosters.freezeFlight, 1.6)
        XCTAssertEqual(d.boosters.hintPolicy, .unblocksMost)
        XCTAssertEqual(RulesTuning.unknownKeys(in: shipped), ["claw", "economy", "lives", "shop", "streak"])
        // the hintPolicy reader: a value it does not know is a decode problem (defaults apply), like every enum knob
        XCTAssertEqual(try JSONDecoder().decode(RulesTuning.self, from: Data(#"{"boosters":{"hintPolicy":"unblocksMost"}}"#.utf8)).boosters.hintPolicy,
                       .unblocksMost)
        XCTAssertEqual(RulesTuning.load(json: Data(#"{"boosters":{"hintPolicy":"random"}}"#.utf8)).problems.count, 1)
        // round trip
        let enc = try JSONEncoder().encode(RulesTuning.default)
        XCTAssertEqual(try JSONDecoder().decode(RulesTuning.self, from: enc), RulesTuning.default)
    }

    func testFailChainFilter() {
        let r = RulesTuning.default
        let noStreak = r.chain(.outOfTime, streakActive: false)
        XCTAssertEqual(noStreak.map(\.warning), [.none, .life])
        XCTAssertEqual(noStreak.map(\.isLast), [false, true])
        XCTAssertEqual(noStreak.first?.grant, .addTime(30))
        XCTAssertEqual(noStreak.map(\.price), [900, 900])
        let streak = r.chain(.outOfHearts, streakActive: true)
        XCTAssertEqual(streak.map(\.warning), [.none, .token, .life])
        XCTAssertEqual(streak.map(\.step), [0, 1, 2])
        XCTAssertEqual(streak.first?.grant, .refillHearts(3))
    }
}
