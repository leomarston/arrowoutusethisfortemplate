import XCTest
import Foundation
@testable import PathCore

/// Non-monotone fixtures (C4): boards where the order matters.
enum SolverFixtures {
    static func a(_ id: Int, _ cells: [(Int, Int)], _ d: Dir, layer: Int = 1, hidden: String? = nil) -> ArrowSpec {
        ArrowSpec(id: ArrowID(id), cells: cells.map { Cell($0.0, $0.1) }, dir: d, layer: layer, hiddenBy: hidden.map { ObstacleID($0) })
    }

    /// The elevator trap. Platform (2,2)-(3,3); P (0) on the platform leaves right; Q (1) crosses the platform's empty
    /// lower row; L (2) waits on layer 2 under that row, facing Q. Tap Q first: solved. Tap P first: the elevator
    /// activates, L blocks Q and Q blocks L — stuck. C2's greedy (every free unit per round, in id order) taps P first.
    static let elevatorTrap = LevelSpec(
        level: 901, source: .designed, cols: 6, rows: 6, timerSeconds: 180, tag: .normal,
        arrows: [a(0, [(2, 2), (3, 2)], .right), a(1, [(0, 3), (1, 3)], .right), a(2, [(3, 3), (2, 3)], .left, layer: 2, hidden: "e0")],
        obstacles: [ObstacleSpec(id: "e0", kind: .elevator, cells: [Cell(2, 2), Cell(2, 3), Cell(3, 2), Cell(3, 3)],
                                 arrows: [ArrowID(0)], reveals: [ArrowID(2)])])

    /// Two arrows facing each other: unsolvable, monotone.
    static let faceOff = LevelSpec(level: 902, source: .designed, cols: 4, rows: 1, timerSeconds: 180,
                                   arrows: [a(0, [(0, 0), (1, 0)], .right), a(1, [(3, 0), (2, 0)], .left)])

    /// The trap plus a face-off under the platform's reach: unsolvable whatever the order, non-monotone.
    static let hopeless = LevelSpec(
        level: 903, source: .designed, cols: 6, rows: 7, timerSeconds: 180, tag: .normal,
        arrows: elevatorTrap.arrows + [a(3, [(0, 6), (1, 6)], .right), a(4, [(3, 6), (2, 6)], .left)],
        obstacles: elevatorTrap.obstacles)
}

/// §4.14 / §4.17 SolverTests (C4): the search = the greedy on monotone boards; it solves the non-monotone fixtures the
/// greedy cannot; the content rules (arrowcore mirror) and the game rules (BoardState) agree on the shipped levels.
final class SolverTests: XCTestCase {

    func replay(_ l: LevelSpec, _ order: [[ArrowID]]) -> Bool {
        let b = BoardState(level: l)
        for u in order {
            let r = b.resolve(tap: u[0])
            guard case .exit = r else { return false }
            b.commit(r)
            b.burstTargetedDoors()
        }
        return b.isCleared
    }

    func testSearchSolvesTheElevatorTrapTheGreedyCannot() throws {
        let l = SolverFixtures.elevatorTrap
        let g = Solver.greedy(l)
        XCTAssertFalse(g.solved)                                   // P first: stuck
        XCTAssertEqual(g.stuck, [ArrowID(1), ArrowID(2)])
        XCTAssertFalse(BoardState(level: l).isMonotone)
        let s = Solver.solve(l)
        let order = try XCTUnwrap(s.order)
        XCTAssertEqual(order.first, [ArrowID(1)])                 // Q before P
        XCTAssertTrue(replay(l, order))
        // the content rules' greedy prefers moves that break nothing: it clears the trap too
        XCTAssertTrue(ContentRules.greedy(l).ok)
        XCTAssertTrue(ContentRules.dfs(l).ok)
    }

    func testUnsolvableAndUndecided() {
        XCTAssertEqual(Solver.solve(SolverFixtures.faceOff), .unsolvable)
        XCTAssertEqual(Solver.search(from: BoardState(level: SolverFixtures.faceOff)), .unsolvable)
        XCTAssertEqual(Solver.solve(SolverFixtures.hopeless), .unsolvable)
        XCTAssertFalse(ContentRules.dfs(SolverFixtures.hopeless).ok)
        if case .undecided = Solver.search(from: BoardState(level: SolverFixtures.hopeless), budget: 2) {} else {
            XCTFail("a 2-node budget must end undecided")
        }
    }

    /// Monotone boards: the search's verdict is the greedy's (sample here; every level in C4FullSolverTests).
    func testSearchEqualsGreedyOnMonotoneBoards() {
        // PUBLISH B0 (level re-order): the list names BOARDS by research slot; each is checked at the slot it ships at
        for n in [1, 2, 7, 11, 19, 25, 29, 33, 39, 47, 54, 64, 70, 74, 75, 79, 150].map(C4Fixtures.slot(research:)) {
            let l = C4Fixtures.level(n)
            let b = BoardState(level: l)
            guard b.isMonotone else { continue }
            let g = Solver.greedy(l)
            let s = Solver.search(from: b)
            XCTAssertEqual(g.solved, s.isSolved, "L\(n)")
            if let o = s.order { XCTAssertTrue(replay(l, o), "L\(n)") }
        }
    }

    func testBothRuleBooksAgreeOnTheSample() {
        // PUBLISH B0 (level re-order): the list names BOARDS by research slot; each is checked at the slot it ships at
        for n in [1, 6, 7, 11, 21, 31, 33, 35, 42, 48, 51, 62, 63, 64, 69, 70, 76, 82, 89, 93, 98, 102, 103, 131].map(C4Fixtures.slot(research:)) {
            let l = C4Fixtures.level(n)
            XCTAssertTrue(Solver.greedy(l).solved || Solver.solve(l).isSolved, "L\(n): game rules")
            XCTAssertTrue(ContentRules.greedy(l).ok, "L\(n): content rules")
        }
    }
}

final class C4FullSolverTests: XCTestCase {
    override func setUpWithError() throws {
        guard C4Fixtures.full else { throw XCTSkip("PC_C4_FULL=1") }
    }

    func testEveryShippedLevel() {
        var lines = ["L1-L150: content greedy (arrowcore mirror) · game greedy (BoardState) · search · monotone", ""]
        for l in C4Fixtures.allLevels {
            let cg = ContentRules.greedy(l).ok
            let b = BoardState(level: l)
            let g = Solver.greedy(l)
            let s = Solver.search(from: b)
            XCTAssertTrue(cg, "L\(l.level)")
            XCTAssertTrue(s.isSolved, "L\(l.level)")
            if b.isMonotone { XCTAssertEqual(g.solved, s.isSolved, "L\(l.level)") }
            lines.append("L\(l.level)  content \(cg ? "solved" : "STUCK")  game greedy \(g.solved ? "solved" : "stuck")  search \(s.isSolved ? "solved" : "\(s)")  \(b.isMonotone ? "monotone" : "non-monotone")")
        }
        C4Fixtures.evidence("c4-solver-every-level.txt", lines.joined(separator: "\n"))
    }
}
