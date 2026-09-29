import XCTest
import CoreGraphics
import PathCore

/// C1 (SPEC-architecture §4.2, §4.17): the fit rule on all 30 recorded levels, zoom limits, centre/cell round trips, head
/// geometry per direction, exact arc length, and the hit geometry (the spike's 873 + 399 jittered points, head-apex taps,
/// the 15 pt radius, the right-hand tie).
final class GeometryTests: XCTestCase {

    // MARK: fit rule

    func testFitRuleReproducesAll30RecordedPitches() throws {
        let files = try C1Fixtures.recordedBaseFiles()
        XCTAssertEqual(files.count, 30, "research/levels holds L032…L061")
        var rows = ["level cols rows  recorded  fit      diff   | cell(0,0) on screen: recorded → ours (dx, dy)"]
        var worst = 0.0, dys: [Double] = []
        for url in files {
            let o = try C1Fixtures.jsonObject(url)
            let cols = (o["cols"] as? Int) ?? 0, rows0 = (o["rows"] as? Int) ?? 0
            let recorded = (o["pitch_pt"] as? Double) ?? .nan
            XCTAssertEqual(o["zoom"] as? String, "fit", url.lastPathComponent)
            let layout = BoardLayout.fit(grid: Grid(cols: cols, rows: rows0), play: Metrics.playRect)
            let diff = layout.pitch - recorded
            worst = max(worst, abs(diff))
            XCTAssertEqual(layout.pitch, recorded, accuracy: 0.03, "\(url.lastPathComponent) \(cols)×\(rows0)")
            // Where the board lands when centred in the play rect (B1 places it; reported, loosely checked).
            let org = (o["origin_pt"] as? [Double]) ?? [0, 0]
            let ours = layout.screenCentre(Cell(0, 0), in: Metrics.playRect)
            let dx = Double(ours.x) - org[0], dy = Double(ours.y) - org[1]
            dys.append(dy)
            XCTAssertEqual(dx, 0, accuracy: 0.6, "\(url.lastPathComponent) horizontal centring")
            XCTAssertEqual(dy, 0, accuracy: 1.2, "\(url.lastPathComponent) vertical centring")
            rows.append(String(format: "%@  %3d  %3d  %8.3f  %8.4f  %+.4f | (%.2f, %.2f) → (%.2f, %.2f) (%+.2f, %+.2f)",
                               String(url.lastPathComponent.prefix(4)), cols, rows0, recorded, layout.pitch, diff,
                               org[0], org[1], Double(ours.x), Double(ours.y), dx, dy))
        }
        rows.append(String(format: "worst |fit − recorded| = %.4f pt (limit 0.03); mean dy = %+.2f pt (ours minus recorded; motion.md §2.1: the original's board centre is 0.7 pt below the play-rect centre)",
                           worst, dys.reduce(0, +) / Double(max(1, dys.count))))
        C1Fixtures.evidence("fit-rule-30-levels.txt", rows.joined(separator: "\n") + "\n")
        XCTAssertLessThanOrEqual(worst, 0.03)
    }

    func testFitTable() {
        // §4.2 table (VERIFIED levels, pitch at fit).
        let cases: [(Int, Int, Double)] = [(20, 20, 17.864), (25, 35, 14.556), (12, 18, 28.07), (16, 23, 21.83), (22, 30, 16.375),
                                           (24, 34, 15.115), (15, 19, 23.118), (10, 18, 28.07), (13, 16, 26.2), (26, 34, 14.036)]
        for (c, r, p) in cases {
            XCTAssertEqual(BoardLayout.fit(grid: Grid(cols: c, rows: r), play: Metrics.playRect).pitch, p, accuracy: 0.005, "\(c)×\(r)")
        }
        // The height term (a DECISION for boards taller than any recorded one): 20 × 40 would run under the HUD by width.
        let tall = BoardLayout.fit(grid: Grid(cols: 20, rows: 40), play: Metrics.playRect)
        XCTAssertEqual(tall.pitch, 633.0 / 42.0, accuracy: 1e-9)
        XCTAssertLessThanOrEqual(Double(tall.contentSize.height), 633.0 + 1e-9)
        // Content = one empty margin cell all round; origin = (1.5 p, 1.5 p).
        let l = BoardLayout.fit(grid: Grid(cols: 20, rows: 20), play: Metrics.playRect)
        XCTAssertEqual(Double(l.contentSize.width), 22 * l.pitch, accuracy: 1e-9)
        XCTAssertEqual(Double(l.contentSize.height), 22 * l.pitch, accuracy: 1e-9)
        XCTAssertEqual(Double(l.origin.x), 1.5 * l.pitch, accuracy: 1e-9)
        XCTAssertEqual(l.cols, 20)
        XCTAssertEqual(l.gridRect, CGRect(x: l.pitch, y: l.pitch, width: 20 * l.pitch, height: 20 * l.pitch))
    }

    // MARK: zoom

    func testZoomLimitsAreAbsolutePitches() {
        let play = Metrics.playRect
        // L50 (10 cols) opens at the 28.07 cap: cannot zoom in (VERIFIED levels L50, motion.md §6.7).
        let l50 = BoardLayout.fit(grid: Grid(cols: 10, rows: 18), play: play)
        XCTAssertEqual(l50.pitch, 28.07, accuracy: 1e-12)
        XCTAssertEqual(l50.maxZoom, 1, accuracy: 1e-12)
        XCTAssertEqual(l50.minZoom, 14.04 / 28.07, accuracy: 1e-12)
        // L32 / L47 (fit 17.86): pinch-out stops at 0.786 of fit = 14.04 pt (VERIFIED levels L47 0.783–0.786).
        let l32 = BoardLayout.fit(grid: Grid(cols: 20, rows: 20), play: play)
        XCTAssertEqual(l32.minZoom, Metrics.minZoomOfFit, accuracy: 0.001)
        XCTAssertEqual(l32.minZoom * l32.pitch, 14.04, accuracy: 1e-9)
        XCTAssertEqual(l32.maxZoom * l32.pitch, 28.07, accuracy: 1e-9)
        XCTAssertEqual(l32.maxZoom, 1.5713, accuracy: 0.0005)
        // A 26-col board (L54/L59, L062 at fit 14.0) cannot zoom out (motion.md §6.7: "L062 pinch 0.2 → stays 14.0").
        let l54 = BoardLayout.fit(grid: Grid(cols: 26, rows: 34), play: play)
        XCTAssertEqual(l54.minZoom, 1, accuracy: 1e-12)
        XCTAssertEqual(l54.maxZoom * l54.pitch, 28.07, accuracy: 1e-9)
        // Explicit limits (board.json may carry both).
        let custom = BoardLayout.fit(grid: Grid(cols: 20, rows: 20), play: play, maxPitch: 30, minPitch: 10)
        XCTAssertEqual(custom.maxZoom * custom.pitch, 30, accuracy: 1e-9)
        XCTAssertEqual(custom.minZoom * custom.pitch, 10, accuracy: 1e-9)
    }

    // MARK: centre / cell

    func testCentreCellRoundTripAndCellSquares() {
        for (c, r) in [(20, 20), (10, 18), (26, 34), (13, 16), (40, 40)] {
            let l = BoardLayout.fit(grid: Grid(cols: c, rows: r), play: Metrics.playRect)
            for rr in 0..<r {
                for cc in 0..<c {
                    let cell = Cell(cc, rr)
                    let p = l.centre(cell)
                    XCTAssertEqual(l.cell(at: p), cell)
                    // Every point strictly inside the square maps to the cell.
                    for (fx, fy) in [(-0.499, -0.499), (0.499, 0.499), (-0.499, 0.499), (0.499, -0.499), (0.25, -0.4)] {
                        let q = CGPoint(x: Double(p.x) + fx * l.pitch, y: Double(p.y) + fy * l.pitch)
                        XCTAssertEqual(l.cell(at: q), cell, "\(c)×\(r) \(cell) (\(fx), \(fy))")
                    }
                }
            }
            // A point exactly on a boundary belongs to the cell to the right / below (the L52 midpoint → right).
            let mid = CGPoint(x: Double(l.centre(Cell(3, 3)).x) + 0.5 * l.pitch, y: Double(l.centre(Cell(3, 3)).y))
            XCTAssertEqual(l.cell(at: mid), Cell(4, 3))
            // Cell centres are one pitch apart, cell (0,0) at (1.5 p, 1.5 p).
            XCTAssertEqual(Double(l.centre(Cell(0, 0)).x), 1.5 * l.pitch, accuracy: 1e-9)
            XCTAssertEqual(Double(l.centre(Cell(5, 0)).x) - Double(l.centre(Cell(4, 0)).x), l.pitch, accuracy: 1e-9)
            XCTAssertEqual(Double(l.centre(Cell(0, 5)).y) - Double(l.centre(Cell(0, 4)).y), l.pitch, accuracy: 1e-9)
            // Outside the grid still maps (negative cells for the margin).
            XCTAssertEqual(l.cell(at: CGPoint(x: 0.1, y: 0.1)), Cell(-1, -1))
            XCTAssertEqual(l.point(cellX: 2.5, cellY: 1), CGPoint(x: Double(l.origin.x) + 2.5 * l.pitch, y: Double(l.origin.y) + l.pitch))
        }
    }

    // MARK: head geometry

    func testHeadApexPerDirection() {
        let l = BoardLayout.fit(grid: Grid(cols: 20, rows: 20), play: Metrics.playRect)
        let p = l.pitch
        let c = Cell(10, 10)
        let expected: [Dir: Double] = [.right: 0.36, .left: 0.36, .up: 0.30, .down: 0.435]   // STYLE §A
        for d in Dir.allCases {
            XCTAssertEqual(Metrics.headApexPast(d), expected[d]!, accuracy: 1e-12, "\(d)")
            let g = ArrowGeometry(cells: [c.moved(d.opposite, by: 2), c.moved(d.opposite, by: 1), c], dir: d, layout: l)
            let centre = l.centre(c)
            XCTAssertEqual(g.headCentre, centre)
            XCTAssertEqual(Double(g.apex.x), Double(centre.x) + Double(d.dc) * expected[d]! * p, accuracy: 1e-9, "\(d)")
            XCTAssertEqual(Double(g.apex.y), Double(centre.y) + Double(d.dr) * expected[d]! * p, accuracy: 1e-9, "\(d)")
            // Head-local triangle: the sharp visible tip exactly at +apexPast·p on +x, the flat base at apex − 0.61 p,
            // width 0.616 p (the rounded base corners shave < 2r).
            let box = g.headPath().boundingBoxOfPath
            let r = Metrics.headCornerRadius * p
            XCTAssertEqual(Double(box.maxX), expected[d]! * p, accuracy: 1e-6, "\(d) apex")
            XCTAssertEqual(Double(box.minX), (expected[d]! - Metrics.headLength) * p, accuracy: 1e-6, "\(d) base")
            XCTAssertEqual(Double(box.height), Metrics.headBase * p, accuracy: 2 * r, "\(d) width")
            XCTAssertLessThanOrEqual(Double(box.height), Metrics.headBase * p + 1e-9)
            XCTAssertEqual(Double(box.midY), 0, accuracy: 1e-3, "\(d) perpendicular centring (CG arc approximation noise < 0.001 pt)")
            // The transform puts the head-local apex on the content apex.
            let a = CGPoint(x: expected[d]! * p, y: 0).applying(g.headTransform)
            XCTAssertEqual(Double(a.x), Double(g.apex.x), accuracy: 1e-9)
            XCTAssertEqual(Double(a.y), Double(g.apex.y), accuracy: 1e-9)
        }
        // STYLE §A: the vertical heads sit ≈ 1.2 pt (3.6 px) LOWER on screen than the horizontal rule predicts, at L32's
        // 17.88 pt pitch: ↑ apex 0.06 p nearer the centre, ↓ apex 0.075 p further.
        XCTAssertEqual((Metrics.headApexPast(.right) - Metrics.headApexPast(.up)) * 17.88, 1.2, accuracy: 0.2)
        XCTAssertEqual((Metrics.headApexPast(.down) - Metrics.headApexPast(.right)) * 17.88, 1.2, accuracy: 0.2)
        XCTAssertEqual(Metrics.stroke, 0.22)
        XCTAssertEqual(Metrics.dotDiameter, 0.192)
        XCTAssertEqual(Metrics.headBase, 0.616)
        XCTAssertEqual(Metrics.headLength, 0.61)
    }

    // MARK: arc length

    func testArcLengthIsExactAlongTheSharpPolyline() {
        let l = BoardLayout.fit(grid: Grid(cols: 20, rows: 20), play: Metrics.playRect)
        let p = l.pitch
        // A snake: → → ↓ ↓ ← ↓ → → (head right).
        let cells = [Cell(2, 2), Cell(3, 2), Cell(4, 2), Cell(4, 3), Cell(4, 4), Cell(3, 4), Cell(3, 5), Cell(4, 5), Cell(5, 5)]
        let arrow = ArrowSpec(id: ArrowID(0), cells: cells, dir: .right)
        let g = ArrowGeometry(arrow: arrow, layout: l)
        XCTAssertEqual(g.bodyLength, 8 * p, accuracy: 1e-9)
        XCTAssertEqual(g.polyline.count, 6, "tail, 4 turns, head")
        let path = ExitPath.plain(arrow: arrow, grid: Grid(cols: 20, rows: 20))
        // The tail passes cell i's centre at travel i·p, and the head goes on straight past the grid edge.
        for (i, c) in path.cells.enumerated() {
            let q = g.point(along: Double(i) * p, on: path)
            XCTAssertEqual(Double(q.x), Double(l.centre(c).x), accuracy: 1e-9, "cell \(i)")
            XCTAssertEqual(Double(q.y), Double(l.centre(c).y), accuracy: 1e-9, "cell \(i)")
        }
        let far = g.point(along: (Double(path.cells.count - 1) + 7.25) * p, on: path)
        XCTAssertEqual(Double(far.x), Double(l.centre(Cell(19, 5)).x) + 7.25 * p, accuracy: 1e-9)
        XCTAssertEqual(Double(far.y), Double(l.centre(Cell(19, 5)).y), accuracy: 1e-9)
        // Midway along a run.
        let mid = g.point(along: 3.5 * p, on: path)
        XCTAssertEqual(Double(mid.x), Double(l.centre(Cell(4, 3)).x), accuracy: 1e-9)
        XCTAssertEqual(Double(mid.y), Double(l.centre(Cell(4, 3)).y) + 0.5 * p, accuracy: 1e-9)
        // Tangents: a corner belongs to the run that leaves it.
        XCTAssertEqual(g.tangent(along: 0, on: path), .right)
        XCTAssertEqual(g.tangent(along: 2 * p, on: path), .down)
        XCTAssertEqual(g.tangent(along: 4.5 * p, on: path), .left)
        XCTAssertEqual(g.tangent(along: 100 * p, on: path), .right)
        // A body point at arc a after a head travel s is at a + s: the head (a = bodyLength) after s = 3 cells.
        let head3 = g.point(along: g.bodyLength + 3 * p, on: path)
        XCTAssertEqual(Double(head3.x), Double(l.centre(Cell(8, 5)).x), accuracy: 1e-9)
        // The resting body path runs through the polyline only (P4: short paths cull).
        XCTAssertEqual(g.bodyPath().boundingBoxOfPath.minX, l.centre(Cell(2, 2)).x)
        XCTAssertEqual(g.bodyPath().boundingBoxOfPath.maxX, l.centre(Cell(5, 5)).x)
    }

    func testExitPathPlainAndPathTrack() {
        let grid = Grid(cols: 12, rows: 9)
        let up = ArrowSpec(id: ArrowID(1), cells: [Cell(5, 6), Cell(5, 5), Cell(5, 4)], dir: .up)
        let path = ExitPath.plain(arrow: up, grid: grid)
        XCTAssertEqual(path.cells, [Cell(5, 6), Cell(5, 5), Cell(5, 4), Cell(5, 3), Cell(5, 2), Cell(5, 1), Cell(5, 0)])
        XCTAssertEqual(path.toGridEdge, 4.5, accuracy: 1e-12)
        XCTAssertEqual(path.segments, [.body(-2..<0), .ray(0..<4.5)])
        XCTAssertEqual(path.bodyCellCount, 3)
        XCTAssertEqual(path.cellArcLength, 6)
        XCTAssertEqual(path.exitDirection, .up)
        // A head already on the edge: no ray cells, the head leaves the grid after half a cell.
        let edge = ExitPath.plain(arrow: ArrowSpec(id: ArrowID(2), cells: [Cell(10, 0), Cell(11, 0)], dir: .right), grid: grid)
        XCTAssertEqual(edge.cells, [Cell(10, 0), Cell(11, 0)])
        XCTAssertEqual(edge.toGridEdge, 0.5)
        // PathTrack in cell units.
        let t = PathTrack(cells: [Cell(0, 0), Cell(1, 0), Cell(2, 0), Cell(2, 1), Cell(2, 2), Cell(1, 2)])
        XCTAssertEqual(t.length, 5)
        XCTAssertEqual(t.corners.count, 4)
        XCTAssertEqual(t.turnArcs, [2, 4])
        XCTAssertEqual(t.runs, [.right, .down, .left])
        XCTAssertEqual(t.point(at: 2.5), CGPoint(x: 2, y: 0.5))
        XCTAssertEqual(t.point(at: 6), CGPoint(x: 0, y: 2))           // past the end: the last run continues
        XCTAssertEqual(t.point(at: -1), CGPoint(x: -1, y: 0))         // before the start: the first run, backwards
        XCTAssertEqual(t.direction(at: 2), .down)
        XCTAssertEqual(t.direction(at: 1.99), .right)
        XCTAssertEqual(PathTrack(cells: [Cell(3, 3)]).point(at: 0), CGPoint(x: 3, y: 3))
    }

    // MARK: hit geometry

    private func jitteredHits(_ level: LevelSpec, seed: UInt64, spread: Double) -> (total: Int, wrong: Int) {
        let l = BoardLayout.fit(grid: level.grid, play: Metrics.playRect)
        let hit = HitGeometry(arrows: level.arrows, layout: l)
        var rng = PathRandom(seed: seed)
        var total = 0, wrong = 0
        let r = HitGeometry.radius(pitch: l.pitch, zoom: 1)
        for a in level.arrows {
            for c in a.cells {
                let o = l.centre(c)
                let q = CGPoint(x: Double(o.x) + rng.double(in: -spread...spread) * l.pitch,
                                y: Double(o.y) + rng.double(in: -spread...spread) * l.pitch)
                total += 1
                if hit.nearest(to: q, within: r, among: { _ in true }, tieBreak: .rightThenDown) != a.id { wrong += 1 }
            }
        }
        return (total, wrong)
    }

    func testHitGeometrySpikeBoards873And399Points() throws {
        let l32 = try LevelJSON.load(C1Fixtures.data(C1Fixtures.research("levels/L032.json"))).level
        let synth = try LevelJSON.decodeBundle(C1Fixtures.data(C1Fixtures.fixture("c1_synth_heart_seed7.json")))
        XCTAssertEqual(synth.arrows.count, 304)
        XCTAssertEqual(synth.arrowCells, 873)
        XCTAssertEqual(l32.arrowCells, 399)
        let a = jitteredHits(l32, seed: 99, spread: 0.45)
        let b = jitteredHits(synth, seed: 99, spread: 0.45)
        XCTAssertEqual(a.total, 399); XCTAssertEqual(a.wrong, 0)
        XCTAssertEqual(b.total, 873); XCTAssertEqual(b.wrong, 0)
        // Harder than the spike: anywhere in the square, three seeds.
        for seed: UInt64 in [1, 2, 3] {
            XCTAssertEqual(jitteredHits(l32, seed: seed, spread: 0.499).wrong, 0)
            XCTAssertEqual(jitteredHits(synth, seed: seed, spread: 0.499).wrong, 0)
        }
        C1Fixtures.evidence("hit-test-spike-boards.txt",
                            "L32: \(a.total) jittered in-cell points (±0.45 p, seed 99), wrong \(a.wrong)\n" +
                            "synthetic heart 40×40 (304 arrows): \(b.total) points, wrong \(b.wrong)\n" +
                            "±0.499 p, seeds 1-3: 0 wrong on both boards\n")
    }

    private func singleArrowLevel(_ arrows: [ArrowSpec], cols: Int = 20, rows: Int = 20) -> (HitGeometry, BoardLayout) {
        let l = BoardLayout.fit(grid: Grid(cols: cols, rows: rows), play: Metrics.playRect)
        return (HitGeometry(arrows: arrows, layout: l), l)
    }

    func testHeadApexTapsNeedTheApexSegment() {
        for d in Dir.allCases {
            let head = Cell(10, 10)
            let arrow = ArrowSpec(id: ArrowID(7), cells: [head.moved(d.opposite, by: 2), head.moved(d.opposite, by: 1), head], dir: d)
            let (hit, l) = singleArrowLevel([arrow])
            let apexPast = Metrics.headApexPast(d)
            // A tap 0.4 p beyond the apex, in the empty cell ahead, with a 0.5 p radius: 0.4 p from the apex segment,
            // (apexPast + 0.4) p ≥ 0.7 p from the body polyline. Only the apex segment can catch it.
            let k = (apexPast + 0.4) * l.pitch
            let q = CGPoint(x: Double(l.centre(head).x) + Double(d.dc) * k, y: Double(l.centre(head).y) + Double(d.dr) * k)
            XCTAssertEqual(l.cell(at: q), head + d, "the tap is in the next cell")
            XCTAssertEqual(hit.nearest(to: q, within: 0.5 * l.pitch, among: { _ in true }, tieBreak: .rightThenDown), ArrowID(7), "\(d)")
            let beyond = (apexPast + 0.55) * l.pitch
            let q2 = CGPoint(x: Double(l.centre(head).x) + Double(d.dc) * beyond, y: Double(l.centre(head).y) + Double(d.dr) * beyond)
            XCTAssertNil(hit.nearest(to: q2, within: 0.5 * l.pitch, among: { _ in true }, tieBreak: .rightThenDown), "\(d)")
            // The head triangle itself is in the head cell.
            let tip = CGPoint(x: Double(l.centre(head).x) + Double(d.dc) * (apexPast - 0.01) * l.pitch,
                              y: Double(l.centre(head).y) + Double(d.dr) * (apexPast - 0.01) * l.pitch)
            XCTAssertEqual(hit.nearest(to: tip, within: 0, among: { _ in true }, tieBreak: .rightThenDown), ArrowID(7))
        }
    }

    func testFifteenPointRadius() {
        // An isolated vertical arrow on L32's board; taps to its right at 14.9 / 15.1 pt (zoom 1: r = max(0.5 p, 15)).
        let arrow = ArrowSpec(id: ArrowID(3), cells: [Cell(10, 12), Cell(10, 11), Cell(10, 10), Cell(10, 9)], dir: .up)
        let (hit, l) = singleArrowLevel([arrow])
        XCTAssertEqual(HitGeometry.radius(pitch: l.pitch, zoom: 1), 15, accuracy: 1e-12)
        let y = Double(l.centre(Cell(10, 11)).y)
        let x0 = Double(l.centre(Cell(10, 11)).x)
        let r1 = HitGeometry.radius(pitch: l.pitch, zoom: 1)
        XCTAssertEqual(hit.nearest(to: CGPoint(x: x0 + 14.9, y: y), within: r1, among: { _ in true }, tieBreak: .rightThenDown), ArrowID(3))
        XCTAssertNil(hit.nearest(to: CGPoint(x: x0 + 15.1, y: y), within: r1, among: { _ in true }, tieBreak: .rightThenDown))
        // Zoom 2: 15 pt on screen = 7.5 content pt < 0.5 p = 8.93 → the half-cell floor wins.
        let r2 = HitGeometry.radius(pitch: l.pitch, zoom: 2)
        XCTAssertEqual(r2, 0.5 * l.pitch, accuracy: 1e-12)
        XCTAssertEqual(hit.nearest(to: CGPoint(x: x0 + 0.5 * l.pitch - 0.05, y: y), within: r2, among: { _ in true }, tieBreak: .rightThenDown), ArrowID(3))
        XCTAssertNil(hit.nearest(to: CGPoint(x: x0 + 0.5 * l.pitch + 0.05, y: y), within: r2, among: { _ in true }, tieBreak: .rightThenDown))
        // Zoom 0.786: 15 pt = 19.08 content pt.
        let r3 = HitGeometry.radius(pitch: l.pitch, zoom: 0.786)
        XCTAssertEqual(r3, 15 / 0.786, accuracy: 1e-9)
        XCTAssertEqual(hit.nearest(to: CGPoint(x: x0 + 19.0, y: y), within: r3, among: { _ in true }, tieBreak: .rightThenDown), ArrowID(3))
        // A custom radius (board.json input.hitRadiusPt).
        XCTAssertEqual(HitGeometry.radius(pitch: l.pitch, zoom: 1, hitRadiusPt: 20), 20)
    }

    func testMidpointTieGoesRight() {
        // Two parallel vertical free arrows two columns apart; the tap in the empty column between them is a tie.
        let left = ArrowSpec(id: ArrowID(1), cells: [Cell(4, 8), Cell(4, 7), Cell(4, 6)], dir: .up)
        let right = ArrowSpec(id: ArrowID(2), cells: [Cell(6, 8), Cell(6, 7), Cell(6, 6)], dir: .up)
        let (hit, l) = singleArrowLevel([left, right])
        let q = l.centre(Cell(5, 7))
        let r = HitGeometry.radius(pitch: l.pitch, zoom: 1) + l.pitch       // wide enough to reach both
        XCTAssertEqual(hit.nearest(to: q, within: r, among: { _ in true }, tieBreak: .rightThenDown), ArrowID(2), "VERIFIED L52: right")
        XCTAssertEqual(hit.nearest(to: q, within: r, among: { _ in true }, tieBreak: .leftThenUp), ArrowID(1))
        // Horizontal pair: the tie goes DOWN under rightThenDown.
        let top = ArrowSpec(id: ArrowID(3), cells: [Cell(10, 2), Cell(11, 2), Cell(12, 2)], dir: .right)
        let bottom = ArrowSpec(id: ArrowID(4), cells: [Cell(10, 4), Cell(11, 4), Cell(12, 4)], dir: .right)
        let (hit2, l2) = singleArrowLevel([top, bottom])
        XCTAssertEqual(hit2.nearest(to: l2.centre(Cell(11, 3)), within: r, among: { _ in true }, tieBreak: .rightThenDown), ArrowID(4))
        XCTAssertEqual(hit2.nearest(to: l2.centre(Cell(11, 3)), within: r, among: { _ in true }, tieBreak: .leftThenUp), ArrowID(3))
        // Adjacent columns: the exact boundary belongs to the right-hand cell (its owner, before any distance).
        let a = ArrowSpec(id: ArrowID(5), cells: [Cell(8, 8), Cell(8, 7)], dir: .up)
        let b = ArrowSpec(id: ArrowID(6), cells: [Cell(9, 8), Cell(9, 7)], dir: .up)
        let (hit3, l3) = singleArrowLevel([a, b])
        let boundary = CGPoint(x: Double(l3.centre(Cell(8, 8)).x) + 0.5 * l3.pitch, y: Double(l3.centre(Cell(8, 8)).y))
        XCTAssertEqual(hit3.nearest(to: boundary, within: 15, among: { _ in true }, tieBreak: .rightThenDown), ArrowID(6))
    }

    func testLiveFilterExcludesHiddenAndMovingArrows() {
        let a = ArrowSpec(id: ArrowID(1), cells: [Cell(5, 5), Cell(6, 5)], dir: .right)
        let b = ArrowSpec(id: ArrowID(2), cells: [Cell(5, 6), Cell(6, 6)], dir: .right)
        let (hit, l) = singleArrowLevel([a, b])
        let onA = l.centre(Cell(5, 5))
        XCTAssertEqual(hit.nearest(to: onA, within: 15, among: { _ in true }, tieBreak: .rightThenDown), ArrowID(1))
        // A gone: the tap on its cell falls through to the nearest live arrow within the radius (B, one pitch away).
        XCTAssertEqual(hit.nearest(to: onA, within: l.pitch * 1.01, among: { $0 != ArrowID(1) }, tieBreak: .rightThenDown), ArrowID(2))
        XCTAssertNil(hit.nearest(to: onA, within: l.pitch * 0.99, among: { $0 != ArrowID(1) }, tieBreak: .rightThenDown))
        XCTAssertNil(hit.nearest(to: onA, within: 50, among: { _ in false }, tieBreak: .rightThenDown))
        // Layer 2 under a platform arrow: the cell has two owners; the live one answers.
        let platform = ArrowSpec(id: ArrowID(10), cells: [Cell(2, 2), Cell(3, 2)], dir: .right)
        let under = ArrowSpec(id: ArrowID(11), cells: [Cell(2, 2), Cell(2, 3)], dir: .down, layer: 2, hiddenBy: "e0")
        let (hit2, l2) = singleArrowLevel([platform, under])
        XCTAssertEqual(hit2.nearest(to: l2.centre(Cell(2, 2)), within: 15, among: { $0 == ArrowID(10) }, tieBreak: .rightThenDown), ArrowID(10))
        XCTAssertEqual(hit2.nearest(to: l2.centre(Cell(2, 2)), within: 15, among: { $0 == ArrowID(11) }, tieBreak: .rightThenDown), ArrowID(11))
    }

    func testHitCost() throws {
        let synth = try LevelJSON.decodeBundle(C1Fixtures.data(C1Fixtures.fixture("c1_synth_heart_seed7.json")))
        let l = BoardLayout.fit(grid: synth.grid, play: Metrics.playRect)
        let hit = HitGeometry(arrows: synth.arrows, layout: l)
        var rng = PathRandom(seed: 5)
        let r = HitGeometry.radius(pitch: l.pitch, zoom: 1)
        let pts = (0..<100_000).map { _ in
            CGPoint(x: rng.double(in: 0...Double(l.contentSize.width)), y: rng.double(in: 0...Double(l.contentSize.height)))
        }
        let t0 = Date()
        var hits = 0
        for q in pts where hit.nearest(to: q, within: r, among: { _ in true }, tieBreak: .rightThenDown) != nil { hits += 1 }
        let us = Date().timeIntervalSince(t0) / Double(pts.count) * 1e6
        C1Fixtures.evidence("hit-test-cost.txt", String(format: "synthetic 40×40, 100k random points: %.3f µs/query (debug build), %d hits\n", us, hits))
        XCTAssertGreaterThan(hits, 30_000)
        XCTAssertLessThan(us, 50, "a hit query must stay far below a frame (spike Release: 0.35 µs)")
    }
}
