import XCTest
import Foundation
import PathCore      // public surface only

/// §4.15 / §4.17 HeadlessTests (C2): the driver wins every recorded level at 0.6 s per tap with ≥ 20 % time left;
/// mistakes cost hearts exactly as the rules say; runs are deterministic; the §4.1 cost targets.
final class HeadlessTests: XCTestCase {

    // MARK: every recorded level (completed with its obstacle evidence, Tests/tools/c2_levels.py)

    func testDriverWinsEveryRecordedLevel() throws {
        let all = try C2Fixtures.completed()
        XCTAssertEqual(all.keys.sorted(), C2Fixtures.recordedLevels)
        var lines = ["HeadlessDriver, 0.6 s per tap, strategy solver, no mistakes — every recorded level (research arrows + "
                     + "Fixtures/c2_recorded_levels.json obstacle evidence)", ""]
        for n in C2Fixtures.recordedLevels {
            let lv = try XCTUnwrap(all[n])
            let g = Solver.greedy(lv)
            let r = HeadlessDriver.play(level: lv, config: DriverConfig(tapInterval: 0.6))
            let kinds = Dictionary(grouping: lv.obstacles, by: \.kind).map { "\($0.key.rawValue)×\($0.value.count)" }.sorted()
            lines.append(String(format: "L%d  arrows %3d (hidden %2d)  greedy rounds %2d  WON %@  time left %5.1f / %d s (%3.0f%%)  hearts %d  taps %3d  %@",
                                n, lv.arrows.count, lv.arrows.filter { $0.hiddenBy != nil }.count, g.rounds, r.won ? "yes" : "NO",
                                r.remaining, lv.timerSeconds, 100 * r.timeLeftFraction, r.heartsLeft, r.taps,
                                kinds.joined(separator: " ")))
            XCTAssertTrue(g.solved, "L\(n): greedy stuck on \(g.stuck.count) arrows")
            XCTAssertTrue(r.won, "L\(n): the driver did not win (stuck \(r.stuck.count), phase \(r.phase))")
            XCTAssertGreaterThanOrEqual(r.timeLeftFraction, 0.2, "L\(n)")
            XCTAssertEqual(r.heartsLeft, lv.hearts, "L\(n)")
            XCTAssertEqual(r.bumps, 0, "L\(n)")
            if case .won(let w) = r.phase { XCTAssertEqual(w.levels, [n]) }
        }
        C2Fixtures.evidence("headless-recorded-levels.txt", lines.joined(separator: "\n"))
    }

    /// The raw research import (C1's path, obstacles incomplete) must at least end every run: won, stuck or lost.
    func testDriverSurvivesTheRawResearchImport() throws {
        for n in C2Fixtures.recordedLevels {
            let r = HeadlessDriver.play(level: try C2Fixtures.researchImport(n).level, config: DriverConfig(tapInterval: 0.6))
            XCTAssertTrue(r.won || !r.stuck.isEmpty || r.loss != nil, "L\(n): neither won, stuck nor lost")
        }
    }

    // MARK: mistakes cost hearts as the rules say

    func testAlwaysMistakenPlayerLosesOnHearts() throws {
        let lv = try XCTUnwrap(C2Fixtures.completed()[39])       // dense, no obstacles: plenty of blocked arrows
        let r = HeadlessDriver.play(level: lv, config: DriverConfig(tapInterval: 0.6, mistakes: 1, seed: 7))
        XCTAssertFalse(r.won)
        XCTAssertEqual(r.loss, .hearts)
        XCTAssertEqual(r.heartsLeft, 0)
        let lost = r.events.filter { if case .heartLost = $0 { return true }; return false }
        XCTAssertEqual(lost, [.heartLost(remaining: 2), .heartLost(remaining: 1), .heartLost(remaining: 0)])
        let offers = r.events.compactMap { e -> ContinueOffer? in if case .offer(let o) = e { return o }; return nil }
        XCTAssertEqual(offers.map(\.kind), [.outOfHearts, .outOfHearts])
        XCTAssertEqual(offers.map(\.warning), [.none, .life])
        XCTAssertEqual(r.events.last, .lost(.hearts))
        XCTAssertGreaterThanOrEqual(r.bumps, 3)                   // repeats on red arrows cost nothing
    }

    func testAcceptedContinueRefillsHearts() throws {
        let lv = try XCTUnwrap(C2Fixtures.completed()[39])
        let r = HeadlessDriver.play(level: lv, config: DriverConfig(tapInterval: 0.6, mistakes: 1, seed: 7,
                                                                    continues: .accept(max: 1)))
        let lost = r.events.filter { if case .heartLost = $0 { return true }; return false }.count
        XCTAssertEqual(lost, 6)                                   // 3, a refill to 3, 3 more
        XCTAssertEqual(r.events.filter { if case .continued = $0 { return true }; return false }.count, 1)
        XCTAssertEqual(r.loss, .hearts)
    }

    func testOccasionalMistakesStillWinAndAccountHearts() throws {
        let all = try C2Fixtures.completed()
        var bumped = 0
        for n in [32, 39, 44, 54, 59] {
            let lv = try XCTUnwrap(all[n])
            let r = HeadlessDriver.play(level: lv, config: DriverConfig(tapInterval: 0.6, mistakes: 0.03, seed: UInt64(n)))
            let lost = r.events.filter { if case .heartLost = $0 { return true }; return false }.count
            XCTAssertEqual(r.heartsLeft, lv.hearts - lost, "L\(n)")
            XCTAssertLessThanOrEqual(lost, r.bumps, "L\(n): a heart per first bump at most")
            bumped += r.bumps
            if lost < 3 { XCTAssertTrue(r.won, "L\(n): \(lost) hearts lost, should still win") }
        }
        XCTAssertGreaterThan(bumped, 0, "the mistake rate produced no bump at all")
    }

    func testDeterministicAndRandomStrategy() throws {
        let lv = try XCTUnwrap(C2Fixtures.completed()[46])
        let a = HeadlessDriver.play(level: lv, config: DriverConfig(strategy: .randomFree, tapInterval: 0.5, mistakes: 0.05, seed: 3))
        let b = HeadlessDriver.play(level: lv, config: DriverConfig(strategy: .randomFree, tapInterval: 0.5, mistakes: 0.05, seed: 3))
        XCTAssertEqual(a.events, b.events)
        XCTAssertEqual(a.remaining, b.remaining)
        let c = HeadlessDriver.play(level: lv, config: DriverConfig(strategy: .randomFree, tapInterval: 0.5, seed: 4))
        XCTAssertTrue(c.won, "a random free order wins too")
    }

    /// Levels 1-4 style: four boards in one session, one win, the stage gaps modelled (VERIFIED tutorials §2).
    func testMultiStageSessionThroughTheDriver() throws {
        let all = try C2Fixtures.completed()
        let stages = [32, 35, 50, 52].map { all[$0]! }
        let s = LevelSession(plan: SessionPlan(id: "S", levels: stages.map(\.level), reward: 80), stages: stages,
                             setup: AttemptSetup(levels: stages.map(\.level)))
        let r = HeadlessDriver.play(s)
        XCTAssertTrue(r.won)
        guard case .won(let w) = r.phase else { return XCTFail("not won") }
        XCTAssertEqual(w.reward, 80)
        XCTAssertEqual(w.levels, [32, 35, 50, 52])
        XCTAssertEqual(r.events.filter { if case .stageAdvanced = $0 { return true }; return false }.count, 3)
        XCTAssertEqual(r.events.filter { if case .timerStarted = $0 { return true }; return false }.count, 4)
    }

    // MARK: §4.1 cost targets (macOS -O; a debug build gets a 10× margin)

    /// A dense solvable board built by reverse construction (each new arrow's ray is clear of the ones already placed,
    /// so removing them in reverse order always works): ≈ 300 arrows on 44 × 52, like the spike's densest board (304).
    static func denseBoard(seed: UInt64, target: Int = 304) -> LevelSpec {
        var rng = PathRandom(seed: seed)
        let cols = 44, rows = 52
        var occ = Set<Cell>()
        var arrows: [ArrowSpec] = []
        var tries = 0
        while arrows.count < target && tries < 600_000 {
            tries += 1
            var c = Cell(rng.below(cols), rng.below(rows))
            guard !occ.contains(c) else { continue }
            var cells = [c]
            var d = Dir.allCases[rng.below(4)]
            let len = 2 + rng.below(4)
            var ok = true
            for k in 1..<len {
                if k > 1 && rng.below(3) == 0 { d = rng.below(2) == 0 ? (d.isHorizontal ? .up : .left) : (d.isHorizontal ? .down : .right) }
                let n = c + d
                if n.c < 0 || n.r < 0 || n.c >= cols || n.r >= rows || occ.contains(n) || cells.contains(n) { ok = false; break }
                cells.append(n); c = n
            }
            guard ok, cells.count >= 2, let dir = Dir(from: cells[cells.count - 2], to: cells[cells.count - 1]) else { continue }
            var p = cells[cells.count - 1] + dir
            var clear = true
            while p.c >= 0 && p.r >= 0 && p.c < cols && p.r < rows {
                if occ.contains(p) || cells.contains(p) { clear = false; break }
                p = p + dir
            }
            guard clear else { continue }
            arrows.append(ArrowSpec(id: ArrowID(arrows.count), cells: cells, dir: dir))
            occ.formUnion(cells)
        }
        return LevelSpec(level: 999, source: .generated, cols: cols, rows: rows, timerSeconds: 600, arrows: arrows)
    }

    #if DEBUG
    static let margin = 10.0
    #else
    static let margin = 1.0
    #endif

    func testCostTargets() {
        let lv = Self.denseBoard(seed: 42)
        XCTAssertEqual(lv.arrows.count, 304)
        XCTAssertEqual(lv.structuralProblems(), [])
        var best = Double.infinity
        var g: GreedyResult?
        for _ in 0..<5 {
            let t0 = DispatchTime.now().uptimeNanoseconds
            g = Solver.greedy(lv)
            best = min(best, Double(DispatchTime.now().uptimeNanoseconds - t0) / 1e6)
        }
        XCTAssertTrue(g!.solved)
        let b = BoardState(level: lv)
        var worst = 0.0, sum = 0.0, n = 0
        for unit in g!.order {
            let t0 = DispatchTime.now().uptimeNanoseconds
            let r = b.resolve(tap: unit[0])
            b.commit(r)
            let us = Double(DispatchTime.now().uptimeNanoseconds - t0) / 1e3
            worst = max(worst, us); sum += us; n += 1
        }
        XCTAssertTrue(b.isCleared)
        let text = String(format: "cost targets (%@): %d-arrow board 44x52, greedy %d rounds: best of 5 %.2f ms (target <= 20 ms); "
                          + "resolve+commit over %d taps: mean %.1f us, worst %.1f us (target <= 50 us)",
                          Self.margin == 1 ? "-O" : "debug", lv.arrows.count, g!.rounds, best, n, sum / Double(n), worst)
        print(text)
        C2Fixtures.evidence(Self.margin == 1 ? "cost-release.txt" : "cost-debug.txt", text)
        XCTAssertLessThanOrEqual(best, 20 * Self.margin)
        XCTAssertLessThanOrEqual(sum / Double(n), 50 * Self.margin)
    }
}
