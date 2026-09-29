import XCTest
import UIKit
import PathCore
@testable import ArrowOut

/// B1 (SPEC-architecture §4.16, §5.2–§5.5): the board's own geometry and timing, pinned against the measured values.
@MainActor final class BoardGeometryTests: XCTestCase {
    let config = BoardConfig(Tuning.load(bundle: .main).board)

    // MARK: exit kinematics (motion §3.3 pass 2 table, the board.json defaults)

    func testExitKinematicsReproducesTheMeasuredTable() {
        let k = config.kinematics
        XCTAssertEqual(k, ExitKinematics.measured, "board.json carries C1's measured law")
        let table: [(Double, Double)] = [(0.5, 0.043), (1, 0.072), (2, 0.115), (3, 0.150), (4, 0.181), (5, 0.209), (6, 0.235),
                                         (8, 0.283), (10, 0.326), (12, 0.367), (15, 0.424), (20, 0.513), (25, 0.596),
                                         (30, 0.676), (40, 0.827)]
        for (d, t) in table {
            XCTAssertEqual(k.time(toTravel: d), t, accuracy: 0.003, "T(\(d))")
            XCTAssertEqual(k.s(k.time(toTravel: d)), d, accuracy: 1e-6, "round trip at \(d)")
        }
        XCTAssertEqual(k.v(0), 7.67, accuracy: 1e-9)
        XCTAssertEqual(k.time(toTravel: 0), 0)
    }

    // MARK: the filleted path

    func testStraightPathIsExact() {
        let p = ArrowPath(points: [CGPoint(x: 0, y: 0), CGPoint(x: 10, y: 0), CGPoint(x: 30, y: 0)], fillet: 2, startExtend: 1)
        XCTAssertEqual(p.length, 31, accuracy: 1e-9)
        XCTAssertEqual(p.point(at: 0).x, -1, accuracy: 1e-9)
        XCTAssertEqual(p.point(at: 16).x, 15, accuracy: 1e-9)
        XCTAssertEqual(p.point(at: 40).x, 39, accuracy: 1e-9, "beyond the end: straight on")
    }

    func testFilletedCornerShortensTheArcExactly() {
        let r: CGFloat = 2.5
        let p = ArrowPath(points: [CGPoint(x: 0, y: 0), CGPoint(x: 20, y: 0), CGPoint(x: 20, y: 20)], fillet: r)
        let expected = 40 - (2 - CGFloat.pi / 2) * r
        XCTAssertEqual(p.length, expected, accuracy: 1e-6)
        // the arc midpoint sits r(√2 − 1) inside the sharp corner along the diagonal
        let mid = p.point(at: (20 - r) + CGFloat.pi / 4 * r)
        let inset = r * (2.squareRoot() - 1) / 2.squareRoot()
        XCTAssertEqual(mid.x, 20 - inset, accuracy: 1e-6)
        XCTAssertEqual(mid.y, inset, accuracy: 1e-6)
        XCTAssertEqual(p.angle(at: 1), 0, accuracy: 1e-9)
        XCTAssertEqual(p.angle(at: p.length - 1), .pi / 2, accuracy: 1e-9)
    }

    func testUTurnKeepsBothFillets() {
        let p = ArrowPath(points: [CGPoint(x: 0, y: 0), CGPoint(x: 10, y: 0), CGPoint(x: 10, y: 10), CGPoint(x: 0, y: 10)],
                          fillet: 2)
        XCTAssertEqual(p.length, 30 - 2 * (2 - CGFloat.pi / 2) * 2, accuracy: 1e-6)
    }

    // MARK: the head (as measured on shot 003)

    func testHeadVisibleTipMatchesTheSpec() throws {
        let head = try XCTUnwrap(config.head, "board.json carries arrow.head")
        let pitch: CGFloat = 53.6
        for d in Dir.allCases {
            let spec = try XCTUnwrap(head[d])
            let box = HeadShape.path(pitch: pitch, dir: d, spec: spec).boundingBoxOfPath
            XCTAssertEqual(Double(box.maxX / pitch), spec.tip, accuracy: 0.004, "\(d) visible tip")
            XCTAssertEqual(Double(box.minX / pitch), spec.base, accuracy: 0.004, "\(d) base edge")
            XCTAssertEqual(Double(box.height / pitch), spec.width, accuracy: 0.01, "\(d) base width")
        }
        XCTAssertLessThan(head[.up]!.tip, head[.right]!.tip, "vertical heads sit lower on screen: up tips shorter")
        XCTAssertGreaterThan(head[.down]!.tip, head[.right]!.tip)
    }

    // MARK: layout and zoom limits (§4.2, §5.2; motion §6.7)

    func testZoomLimitsL32AndTheCap() {
        let screen = CGSize(width: 393, height: 852)
        func level(_ cols: Int, _ rows: Int) -> LevelSpec {
            LevelSpec(level: 1, source: .designed, cols: cols, rows: rows, timerSeconds: 180,
                      arrows: [ArrowSpec(id: ArrowID(0), cells: [Cell(0, 0), Cell(1, 0)], dir: .right)])
        }
        let l32 = config.layout(for: level(20, 20), screen: screen)
        XCTAssertEqual(l32.pitch, 17.864, accuracy: 0.001)
        let z32 = config.zoomLimits(l32)
        XCTAssertEqual(Double(z32.min), 0.786, accuracy: 0.001, "pinch-out clamps at 0.786 x fit (14.04 pt)")
        XCTAssertEqual(Double(z32.max) * l32.pitch, 28.07, accuracy: 0.001, "pinch-in clamps at 28.07 pt per cell")
        let l50 = config.layout(for: level(10, 18), screen: screen)
        XCTAssertEqual(l50.pitch, 28.07, accuracy: 0.001, "L50 opens at the cap")
        XCTAssertEqual(config.zoomLimits(l50).max, 1, "a board at the cap cannot zoom in")
        let l59 = config.layout(for: level(26, 34), screen: screen)
        XCTAssertEqual(l59.pitch, 14.036, accuracy: 0.01)
        XCTAssertEqual(Double(config.zoomLimits(l59).min), 1, accuracy: 0.002, "a 26-column board cannot zoom out (motion §6.7)")
    }

    func testPanRangeCentresAndAllowsSlack() {
        // content smaller than the play rect: centred origin ± slack
        let (before, after) = BoardScrollView.range(a: 122, b: 755, length: 400, view: 852, slack: 120)
        let centred = (122 + 755) / 2.0 - 200
        XCTAssertEqual(Double(before), centred + 120, accuracy: 1e-9)         // max origin = inset.top
        XCTAssertEqual(Double(-(400 + after - 852)), centred - 120, accuracy: 1e-9)   // min origin
        // content larger than the play rect: its edges may come 'slack' inside the play rect
        let (b2, a2) = BoardScrollView.range(a: 122, b: 755, length: 1200, view: 852, slack: 120)
        XCTAssertEqual(Double(b2), 122 + 120, accuracy: 1e-9)
        XCTAssertEqual(Double(-(1200 + a2 - 852)), 755 - 1200 - 120, accuracy: 1e-9)
    }

    // MARK: hit test (§5.3)

    func testHitTestOwnersJitterTieAndRadius() throws {
        let level = LabBoards.hitBoard()
        let layout = config.layout(for: level, screen: CGSize(width: 393, height: 852))
        XCTAssertEqual(layout.pitch, 28.07, accuracy: 0.001)
        var hit = HitTester(level: level, layout: layout, metrics: config.arrowMetrics)
        for a in level.arrows { hit.insert(a.id, cells: a.cells) }
        func at(_ p: CGPoint) -> ArrowID? {
            hit.arrow(at: p, zoom: 1, radiusPt: config.hitRadius, tieTolerancePt: config.tieTolerance, tieTolerancePitch: config.tieTolerancePitch,
                      rightThenDown: config.tieRightThenDown)
        }
        var rng = PathRandom(seed: 5)
        for a in level.arrows {
            for c in a.cells {
                let o = layout.centre(c)
                for _ in 0..<20 {
                    let q = CGPoint(x: o.x + CGFloat(rng.unit() * 0.9 - 0.45) * CGFloat(layout.pitch),
                                    y: o.y + CGFloat(rng.unit() * 0.9 - 0.45) * CGFloat(layout.pitch))
                    XCTAssertEqual(at(q), a.id)
                }
            }
        }
        // the midpoint between the adjacent parallel arrows 0 (column 1) and 1 (column 2) goes to the right-hand one (L52a)
        let mid = CGPoint(x: (layout.centre(Cell(1, 3)).x + layout.centre(Cell(2, 3)).x) / 2, y: layout.centre(Cell(1, 3)).y)
        XCTAssertEqual(at(mid), ArrowID(1))
        XCTAssertEqual(at(CGPoint(x: mid.x - 0.5, y: mid.y)), ArrowID(1), "within the tie band: a whole-point touch rounding")
        XCTAssertEqual(at(CGPoint(x: mid.x - 1.2, y: mid.y)), ArrowID(0), "beyond the band the touched cell wins")
        XCTAssertEqual(at(CGPoint(x: mid.x - 2, y: mid.y)), ArrowID(0), "clearly nearer the left one")
        // the hit radius is 22 pt on screen (SPEC-gameplay §2.2, CONSISTENCY G-5, SPEC.md §5 item 29; board.json
        // input.hitRadiusPt; at zoom 1 max(0.5 × 28.07, 22) = 22): 15 pt above the isolated horizontal arrow 2 sends it
        // (L47c), so does 21 pt; 23 pt does not. The miss is the radius, not a neighbour: that point lies in the empty cell
        // (2, 6), and the nearest other stroke is arrow 1's tail end at (2, 4), 61.2 pt away (arrow 0 67.3, arrow 4 at
        // (5…6, 6) 84.4, arrow 3 104.1 pt; 23 pt below: row 8 is empty, arrow 4 98.5 pt) — build/corefinal/EVIDENCE.txt
        XCTAssertEqual(config.hitRadius, 22, accuracy: 1e-9, "board.json input.hitRadiusPt (G-5)")
        let c2 = layout.centre(Cell(2, 7))
        XCTAssertEqual(at(CGPoint(x: c2.x, y: c2.y - 15)), ArrowID(2))
        XCTAssertEqual(at(CGPoint(x: c2.x, y: c2.y - 21)), ArrowID(2))
        XCTAssertNil(at(CGPoint(x: c2.x, y: c2.y - 23)))
        XCTAssertNil(at(CGPoint(x: c2.x, y: c2.y + 23)), "below: row 8 is empty too")
        // the head tip area
        let h3 = layout.centre(Cell(5, 3))
        XCTAssertEqual(at(CGPoint(x: h3.x, y: h3.y - 0.3 * CGFloat(layout.pitch))), ArrowID(3))
        // an exited arrow is no longer hit
        hit.remove(ArrowID(2), cells: level.arrows[2].cells)
        XCTAssertNil(at(c2))
    }

    func testJitteredInCellTapsKeepTheirOwnerOnBothSpikeBoards() throws {
        // the spike's check (873 + 399 jittered in-cell points, 0 wrong) with the tie band in place
        for level in [LabBoards.synthetic(cols: 40, rows: 40, seed: 7, meanLength: 3.0, id: 9040),
                      try XCTUnwrap(LabBoards.level("L032", bundle: .main))] {
            let layout = config.layout(for: level, screen: CGSize(width: 393, height: 852))
            var hit = HitTester(level: level, layout: layout, metrics: config.arrowMetrics)
            for a in level.arrows { hit.insert(a.id, cells: a.cells) }
            var rng = PathRandom(seed: 99)
            var wrong = 0, total = 0
            for a in level.arrows {
                for c in a.cells {
                    let o = layout.centre(c)
                    let q = CGPoint(x: o.x + CGFloat(rng.unit() * 0.9 - 0.45) * CGFloat(layout.pitch),
                                    y: o.y + CGFloat(rng.unit() * 0.9 - 0.45) * CGFloat(layout.pitch))
                    total += 1
                    if hit.arrow(at: q, zoom: 1, radiusPt: config.hitRadius, tieTolerancePt: config.tieTolerance,
                                 tieTolerancePitch: config.tieTolerancePitch, rightThenDown: true) != a.id { wrong += 1 }
                }
            }
            XCTAssertEqual(wrong, 0, "\(total) jittered points on L\(level.level)")
        }
    }

    // MARK: lab boards and stand-in rules

    func testSyntheticHeartIsTheSpikeBoard() {
        let l = LabBoards.synthetic(cols: 40, rows: 40, seed: 7, meanLength: 3.0, id: 9040)
        XCTAssertEqual(l.arrows.count, 304, "the spike's 304-arrow board (tech-spike.md)")
        XCTAssertEqual(l.arrows.reduce(0) { $0 + $1.cells.count }, 873)
        let rules = LabRules(level: l)
        let order = rules.greedyOrder()
        let copy = LabRules(level: l)
        for id in order { _ = copy.tap(id, at: 0) }
        XCTAssertEqual(copy.liveCount, 0, "solvable by construction")
        XCTAssertEqual(copy.bumps, 0)
    }

    func testL032FixtureDecodes() throws {
        let l = try XCTUnwrap(LabBoards.level("L032", bundle: .main))
        XCTAssertEqual(l.arrows.count, 53)
        XCTAssertEqual(l.arrows.reduce(0) { $0 + $1.cells.count }, 399)
        let tapes = l.obstacles.filter { $0.kind == .tape }
        XCTAssertEqual(tapes.count, 4)
        XCTAssertTrue(tapes.allSatisfy { $0.arrows.count == 4 })
        XCTAssertEqual(Set(tapes.map(TapeLayer.spriteID)), ["tapeV4", "tapeH4"])
        let rules = LabRules(level: l)
        let copy = LabRules(level: l)
        for id in rules.greedyOrder() { _ = copy.tap(id, at: 0) }
        XCTAssertEqual(copy.liveCount, 0)
    }

    func testBumpPlanContactGeometry() throws {
        let l = LabBoards.warmBoard()
        let rules = LabRules(level: l)
        guard case .bump(let plan) = rules.resolve(ArrowID(8)) else { return XCTFail("arrow 8 is blocked by arrow 9") }
        XCTAssertEqual(plan.gapCells, 2)
        XCTAssertEqual(plan.blocker, .arrow(ArrowID(9)))
        XCTAssertEqual(plan.contactPoint, Cell(4, 6))
        XCTAssertEqual(plan.contactCells, 3 - Metrics.headApexPast(.right) - Metrics.stroke / 2, accuracy: 1e-9)
        guard case .exit(let tape) = rules.resolve(ArrowID(2)) else { return XCTFail("the bundle is free") }
        XCTAssertEqual(tape.unit.count, 4)
        XCTAssertEqual(tape.tape, ObstacleID("t0"))
    }
}
