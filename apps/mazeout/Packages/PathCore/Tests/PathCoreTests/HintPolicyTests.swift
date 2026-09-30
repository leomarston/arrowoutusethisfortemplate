import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// CORE-2, SPEC.md ruling 31: the bulb's `unblocksMost` unit (SPEC-gameplay §6.3) through its own entry —
/// `Solver.hintUnit(_:policy:)`, `Solver.hintScores(_:)`, `LevelSession.hint(policy:)` and
/// `useBooster(_:hintPolicy:freezeFlightFromUse:)` — while `hint()` / `Solver.hintUnit(_:)` and the HeadlessDriver's solver
/// strategy stay greedy. Rule: among the units free now, the one whose exit unblocks the most OTHER live arrows (arrows
/// whose ray passes over its cells, each counted once per unit); ties → the longer unit (a bundle: all members' cells) →
/// the lower id. The ray is the rules' walk with arrows ignored (pipes carry it, corners turn it, blocking obstacles end it).
/// Every expectation is worked out by hand in the comment above its board (cells are (column, row), row 0 at the top).
final class HintPolicyTests: XCTestCase {
    typealias F = C2Fixtures
    let a0 = ArrowID(0), a1 = ArrowID(1), a2 = ArrowID(2), a3 = ArrowID(3), a4 = ArrowID(4), a5 = ArrowID(5)

    func score(_ u: [ArrowID], _ unblocks: Int, _ cells: Int) -> Solver.HintScore {
        Solver.HintScore(unit: u, unblocks: unblocks, cells: cells)
    }

    /// 6 × 4. a0 (0,3)(1,3) → free, nobody's ray crosses it: unblocks 0. a1 (4,1)(4,0) ↑ free; a2 (0,1)(1,1) → and
    /// a3 (0,0)(1,0) → both run into a1 (rows 1 and 0 of column 4): unblocks 2. Greedy's first unit = the lowest free id a0.
    func differing() -> LevelSpec {
        F.level(6, 4, [F.arrow(0, [(0, 3), (1, 3)], .right), F.arrow(1, [(4, 1), (4, 0)], .up),
                       F.arrow(2, [(0, 1), (1, 1)], .right), F.arrow(3, [(0, 0), (1, 0)], .right)], n: 40)
    }

    // MARK: the two policies differ; the greedy entries do not move

    func testThePoliciesDifferOnABoardAndTheGreedyEntriesStayGreedy() throws {
        let b = BoardState(level: differing())
        XCTAssertEqual(b.freeUnits(), [[a0], [a1]])
        XCTAssertEqual(Solver.hintScores(b), [score([a1], 2, 2), score([a0], 0, 2)])
        XCTAssertEqual(Solver.hintUnit(b, policy: .unblocksMost), [a1], "unblocksMost: a1 frees a2 and a3")
        XCTAssertEqual(Solver.hintUnit(b), [a0], "greedy: the first unit of the greedy order (lowest free id)")

        let s = LevelSession(plan: SessionPlan(id: "D", levels: [40]), stages: [differing()], setup: AttemptSetup(levels: [40]))
        _ = s.start(); _ = s.ack(.introFinished)
        XCTAssertEqual(s.hint(), [a0], "session.hint() stays greedy")
        XCTAssertEqual(s.hint(policy: .unblocksMost), [a1])
        XCTAssertEqual(s.useBooster(.hint), [.boosterUsed(.hint), .hintShown([a0])], "the plain entry: greedy")
        XCTAssertEqual(s.useBooster(.hint, hintPolicy: .unblocksMost, freezeFlightFromUse: true),
                       [.boosterUsed(.hint), .hintShown([a1])], "the ruled entry: unblocksMost")
        XCTAssertEqual(s.phase, .ready(stage: 0), "the bulb never starts the timer")
        XCTAssertFalse(s.clock.started)
        XCTAssertEqual(s.clock.freezeRemaining, 0, "a bulb freezes nothing")
        // after a1 left, a0 a2 a3 are free, none crosses another (2 cells each): the lowest id
        _ = s.tap(a1, at: 0)
        XCTAssertEqual(Solver.hintScores(s.board), [score([a0], 0, 2), score([a2], 0, 2), score([a3], 0, 2)])
        XCTAssertEqual(s.hint(policy: .unblocksMost), [a0])

        // the HeadlessDriver's solver strategy taps the greedy unit (SPEC.md ruling 31: no pinned driver test moves)
        let r = HeadlessDriver.play(level: differing(), config: DriverConfig(tapInterval: 0.6))
        XCTAssertTrue(r.won)
        let firstExit = try XCTUnwrap(r.events.compactMap { e -> ArrowID? in if case .exited(let p) = e { return p.tapped }; return nil }.first)
        XCTAssertEqual(firstExit, a0)
    }

    // MARK: ties

    /// 8 × 5. a0 (2,1)(2,0) ↑ free, 2 cells; a1 (5,2)(5,1)(5,0) ↑ free, 3 cells; a2 (2,4)(2,3) ↑ runs into a0, a3 (5,4)(5,3) ↑
    /// into a1: one each → the longer a1 (although its id is higher). `short` a1 = (5,1)(5,0): 2 cells each → the lower id a0.
    func tie(short: Bool) -> LevelSpec {
        F.level(8, 5, [F.arrow(0, [(2, 1), (2, 0)], .up),
                       F.arrow(1, short ? [(5, 1), (5, 0)] : [(5, 2), (5, 1), (5, 0)], .up),
                       F.arrow(2, [(2, 4), (2, 3)], .up), F.arrow(3, [(5, 4), (5, 3)], .up)])
    }

    func testTiesGoToTheLongerUnitThenToTheLowerId() {
        let long = BoardState(level: tie(short: false))
        XCTAssertEqual(Solver.hintScores(long), [score([a1], 1, 3), score([a0], 1, 2)])
        XCTAssertEqual(Solver.hintUnit(long, policy: .unblocksMost), [a1])
        XCTAssertEqual(Solver.hintUnit(long), [a0], "greedy differs here too")
        let short = BoardState(level: tie(short: true))
        XCTAssertEqual(Solver.hintScores(short), [score([a0], 1, 2), score([a1], 1, 2)])
        XCTAssertEqual(Solver.hintUnit(short, policy: .unblocksMost), [a0])
    }

    // MARK: a tape bundle is one unit

    /// 6 × 6. The bundle a0 (1,3)(1,2) ↑ + a1 (2,3)(2,2) ↑ under tape t0 (RulesTests' tie cells) is free (columns 1-2 above
    /// are empty). a2 (4,2)(3,2) ← crosses BOTH members (2,2) and (1,2): counted once; a3 (1,5)(1,4) ↑ crosses a0: the
    /// bundle unblocks 2, 4 cells. a4 (5,1)(5,0) ↑ free, a5 (5,5)(5,4) ↑ runs into it: 1.
    func bundled() -> LevelSpec {
        F.level(6, 6, [F.arrow(0, [(1, 3), (1, 2)], .up), F.arrow(1, [(2, 3), (2, 2)], .up),
                       F.arrow(2, [(4, 2), (3, 2)], .left), F.arrow(3, [(1, 5), (1, 4)], .up),
                       F.arrow(4, [(5, 1), (5, 0)], .up), F.arrow(5, [(5, 5), (5, 4)], .up)],
                [ObstacleSpec(id: "t0", kind: .tape, cells: F.cells([(1, 2), (2, 2)]), arrows: [a0, a1])])
    }

    func testABundleIsScoredAndHintedAsAWholeAndAnArrowCountsOncePerUnit() {
        let b = BoardState(level: bundled())
        XCTAssertEqual(b.freeUnits(), [[a0, a1], [a4]])
        XCTAssertEqual(Solver.hintScores(b), [score([a0, a1], 2, 4), score([a4], 1, 2)])
        XCTAssertEqual(Solver.hintUnit(b, policy: .unblocksMost), [a0, a1], "every member green")
    }

    // MARK: the ray is the rules' walk with the arrows ignored

    /// 8 × 6. a0 (0,1)(1,1) → is stopped by a1 (2,1)(3,1) →, which is stopped by a2 (4,2)(4,1)(4,0) ↑ (free, 3 cells); a0's
    /// ray to the edge crosses a1 AND a2: a2 unblocks 2 (a0 and a1). a3 (6,5)…(6,2) ↑ free, 4 cells; a4 (4,4)(5,4) → runs
    /// into it: 1. (Counting only the FIRST arrow on each ray would tie them at 1 and pick the longer a3.)
    func behind() -> LevelSpec {
        F.level(8, 6, [F.arrow(0, [(0, 1), (1, 1)], .right), F.arrow(1, [(2, 1), (3, 1)], .right),
                       F.arrow(2, [(4, 2), (4, 1), (4, 0)], .up), F.arrow(3, [(6, 5), (6, 4), (6, 3), (6, 2)], .up),
                       F.arrow(4, [(4, 4), (5, 4)], .right)])
    }

    func testAnArrowWaitingBehindAnotherStillCounts() {
        let b = BoardState(level: behind())
        XCTAssertEqual(b.freeUnits(), [[a2], [a3]])
        XCTAssertEqual(Solver.hintScores(b), [score([a2], 2, 3), score([a3], 1, 4)])
        XCTAssertEqual(Solver.hintUnit(b, policy: .unblocksMost), [a2])
    }

    /// 7 × 5 (RulesTests' pipe board + a2). a0 (0,1)(1,1) → enters p0's mouth (3,1) against its `out` ←, travels the tube
    /// (3,1)(4,1)(4,2)(4,3), leaves the far mouth ↓ and meets a1 (3,4)(4,4)(5,4) → at (4,4): a1 (free, 3 cells) unblocks 1.
    /// a2 (3,3)…(0,3) ← free, 4 cells, crossed by nobody: 0. (A straight ray would tie them at 0 and pick the longer a2.)
    func piped() -> LevelSpec {
        F.level(7, 5, [F.arrow(0, [(0, 1), (1, 1)], .right), F.arrow(1, [(3, 4), (4, 4), (5, 4)], .right),
                       F.arrow(2, [(3, 3), (2, 3), (1, 3), (0, 3)], .left)], [
            ObstacleSpec(id: "p0", kind: .pipe, cells: F.cells([(3, 1), (4, 1), (4, 2), (4, 3)]),
                         ends: [PipeEnd(cell: Cell(3, 1), out: .left), PipeEnd(cell: Cell(4, 3), out: .down)], counter: 2),
        ])
    }

    func testAPipeCarriesTheRay() {
        let b = BoardState(level: piped())
        XCTAssertEqual(b.freeUnits(), [[a1], [a2]])
        XCTAssertEqual(Solver.hintScores(b), [score([a1], 1, 3), score([a2], 0, 4)])
        XCTAssertEqual(Solver.hintUnit(b, policy: .unblocksMost), [a1])
        XCTAssertEqual(b.counters["p0"], 2, "scoring passes no pipe (it explores a copy)")
    }

    /// 7 × 4. a0 (0,1)(1,1) → meets the LOCKED door d0 ((2,1)(3,1)) at (2,1): its ray ends there, so a1 (4,2)(4,1)(4,0) ↑
    /// (free, 3 cells; on a0's straight line past the door) unblocks 0; a3 (3,3)…(6,3) → free, 4 cells: 0 → tie → the longer
    /// a3. The door hides a2 (2,1)(3,1) →, whose ray WOULD meet a1 at (4,1): hidden, not live, it counts for nothing.
    func doored() -> LevelSpec {
        F.level(7, 4, [F.arrow(0, [(0, 1), (1, 1)], .right), F.arrow(1, [(4, 2), (4, 1), (4, 0)], .up),
                       F.arrow(2, [(2, 1), (3, 1)], .right, hiddenBy: "d0"), F.arrow(3, [(3, 3), (4, 3), (5, 3), (6, 3)], .right)],
                [ObstacleSpec(id: "d0", kind: .door, cells: F.cells([(2, 1), (3, 1)]), order: 0, reveals: [a2])])
    }

    func testABlockingObstacleEndsTheRayAndHiddenArrowsDoNotCount() {
        let b = BoardState(level: doored())
        XCTAssertEqual(b.live, [a0, a1, a3])
        XCTAssertEqual(b.freeUnits(), [[a1], [a3]])
        XCTAssertEqual(Solver.hintScores(b), [score([a3], 0, 4), score([a1], 0, 3)])
        XCTAssertEqual(Solver.hintUnit(b, policy: .unblocksMost), [a3])
    }

    // MARK: nothing free

    /// a0 (0,0)(1,0) → against a locked door with no key: nothing is free → nil, like the greedy entry; the ruled bulb
    /// shows nothing (the app takes no stock).
    func testNothingFreeIsNil() {
        let lv = F.level(5, 1, [F.arrow(0, [(0, 0), (1, 0)], .right)],
                         [ObstacleSpec(id: "d0", kind: .door, cells: F.cells([(3, 0)]), order: 0)])
        let b = BoardState(level: lv)
        XCTAssertEqual(b.freeUnits(), [])
        XCTAssertEqual(Solver.hintScores(b), [])
        XCTAssertNil(Solver.hintUnit(b, policy: .unblocksMost))
        XCTAssertNil(Solver.hintUnit(b))
        let s = LevelSession(plan: SessionPlan(id: "N", levels: [1]), stages: [lv], setup: AttemptSetup(levels: [1]))
        _ = s.start(); _ = s.ack(.introFinished)
        XCTAssertNil(s.hint(policy: .unblocksMost))
        XCTAssertEqual(s.useBooster(.hint, hintPolicy: .unblocksMost, freezeFlightFromUse: true), [.boosterUsed(.hint), .hintShown([])])
    }

    /// Mid-bump units are not free (the board's own `freeUnits`), so they are never hinted; a live arrow mid-bump still
    /// counts for the unit its ray crosses.
    func testABumpingUnitIsNeverHinted() {
        let b = BoardState(level: differing())
        b.commit(b.resolve(tap: a2))                                     // a2 bumps into a1
        XCTAssertTrue(b.isBumping(a2))
        XCTAssertEqual(Solver.hintScores(b), [score([a1], 2, 2), score([a0], 0, 2)], "a2 mid-bump still waits on a1")
        b.commit(b.resolve(tap: a1))                                     // a1 leaves while a2 is still mid-bump
        XCTAssertEqual(b.freeUnits(), [[a0], [a3]])
        XCTAssertEqual(Solver.hintScores(b).map(\.unit), [[a0], [a3]], "the bumping a2 has a clear ray but is not free")
        _ = b.ack(.bumpContact(a2)); _ = b.ack(.bumpFinished(a2))
        XCTAssertEqual(Solver.hintScores(b).map(\.unit), [[a0], [a2], [a3]], "back at rest: free, 0 each, 2 cells each → by id")
    }

    // MARK: every authored level

    /// L1-L150 (the pinned design/levels.json): tapping the `unblocksMost` unit every time clears every board with no bump
    /// ("any free unit is safe", SPEC.md ruling 31); the hinted unit is always free, `hintUnit(policy:)` = `hintScores.first`,
    /// and scoring never changes the board. Evidence: hint-policy-authored.txt (where the two policies differ at the start).
    func testUnblocksMostAutoplayClearsEveryAuthoredLevel() throws {
        let levels = C4Fixtures.allLevels
        XCTAssertEqual(levels.count, 150)
        var lines = ["unblocksMost autoplay over the authored L1-L150 (every tap = Solver.hintScores(board).first; a door whose "
                     + "key left bursts when nothing else is free, like the greedy solver)", ""]
        var differ = 0
        for lv in levels {
            let b = BoardState(level: lv)
            let startLive = b.live, startFree = b.freeUnits()
            let greedy = Solver.hintUnit(b)
            let first = Solver.hintScores(b)
            XCTAssertEqual(b.live, startLive, "L\(lv.level): scoring changed the board")
            XCTAssertEqual(b.freeUnits(), startFree, "L\(lv.level)")
            XCTAssertEqual(Solver.hintUnit(b, policy: .unblocksMost), first.first?.unit, "L\(lv.level)")
            if greedy != first.first?.unit { differ += 1 }
            var taps = 0, bursts = 0
            while !b.isCleared {
                let scores = Solver.hintScores(b)
                guard let best = scores.first else {
                    if b.burstTargetedDoors() { bursts += 1; continue }
                    XCTFail("L\(lv.level): nothing free with \(b.remaining) arrows left"); break
                }
                XCTAssertTrue(b.freeUnits().contains(best.unit), "L\(lv.level)")
                let r = b.resolve(tap: best.unit[0])
                guard case .exit(let plan) = r, plan.unit == best.unit else { XCTFail("L\(lv.level): the hinted unit did not exit whole"); break }
                b.commit(r)
                taps += 1
                if taps > lv.arrows.count { XCTFail("L\(lv.level): runaway"); break }
            }
            XCTAssertTrue(b.isCleared, "L\(lv.level)")
            lines.append(String(format: "L%03d  arrows %3d  taps %3d  door bursts %d  start: unblocksMost a%@ (unblocks %d) %@ greedy a%@",
                                lv.level, lv.arrows.count, taps, bursts,
                                first.first.map { $0.unit.map { "\($0.raw)" }.joined(separator: "+") } ?? "-", first.first?.unblocks ?? 0,
                                greedy == first.first?.unit ? "=" : "≠",
                                greedy.map { $0.map { "\($0.raw)" }.joined(separator: "+") } ?? "-"))
        }
        lines.append("")
        lines.append("start boards where the policies differ: \(differ) of \(levels.count)")
        C2Fixtures.evidence("hint-policy-authored.txt", lines.joined(separator: "\n"))
        XCTAssertGreaterThan(differ, 0, "the new policy is not the greedy one in disguise")
    }

    /// The cost of one bulb tap (the scoring runs on the main thread in the app): the densest authored start board and the
    /// 304-arrow synthetic 40 × 40 heart (the feel soak's board, c1_synth_heart_seed7.json). Evidence only (hint-policy-cost.txt);
    /// the verdict is the device's (V3 / D1), not this build configuration's.
    func testScoringCostOnTheDensestBoards() throws {
        let authored = try XCTUnwrap(C4Fixtures.allLevels.max { $0.arrows.count < $1.arrows.count })
        let synth = try LevelJSON.decodeBundle(C2Fixtures.data(C2Fixtures.fixture("c1_synth_heart_seed7.json")))
        XCTAssertEqual(synth.arrows.count, 304)
        var lines: [String] = []
        for (name, lv) in [("L\(authored.level) (densest authored)", authored), ("synthetic heart 40x40", synth)] {
            let b = BoardState(level: lv)
            var times: [Double] = []
            var last: [Solver.HintScore] = []
            for _ in 0..<20 {
                let t0 = DispatchTime.now().uptimeNanoseconds
                last = Solver.hintScores(b)
                times.append(Double(DispatchTime.now().uptimeNanoseconds - t0) / 1e6)
            }
            XCTAssertEqual(Solver.hintScores(b), last, "deterministic")
            XCTAssertFalse(last.isEmpty, name)
            times.sort()
            lines.append(String(format: "Solver.hintScores, %@ start board: %d arrows, %d free units: median %.3f ms, max %.3f ms over 20 runs; "
                                + "best unit a%@ unblocks %d", name, lv.arrows.count, last.count, times[times.count / 2], times.last ?? 0,
                                last[0].unit.map { "\($0.raw)" }.joined(separator: "+"), last[0].unblocks))
        }
        #if DEBUG
        lines.append("configuration: debug (swift test default)")
        #else
        lines.append("configuration: release")
        #endif
        C2Fixtures.evidence("hint-policy-cost.txt", lines.joined(separator: "\n"))
    }
}
