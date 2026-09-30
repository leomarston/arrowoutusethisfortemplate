import Foundation
import CoreGraphics
import GameCore

// C1 (SPEC-architecture §4.2, §4.4, D5). Geometry over the ◆ `ExitPath` (Rules/Plans.swift): the polyline through its
// cells, arc-length parametrised, extended straight past its last cell (the board runs the last direction on to the
// SCREEN edge, D5). C2's tap resolver builds the paths (tubes, corners); `ExitPath.plain` is the obstacle-free case.
//
// Conventions (C1; the ◆ comments leave the arc origin open):
// - `cells` = the arrow's body tail → head, then every cell the head passes. Consecutive cells are orthogonal neighbours
//   (a tube's cells are listed in travel order), so the arc length between cell i and cell i+1 is exactly 1 cell.
// - Arc parameter `u` (content pt, or cells in `PathTrack`): 0 = the TAIL cell centre at rest. After a head travel s,
//   a body point that sat at arc a (0 ≤ a ≤ bodyLength) is at u = a + s. The head starts at u = bodyLength.
// - Segment ranges (`PathSegment`) are in cells of the HEAD's travel: the body is `-(n-1)..<0`, the ray starts at 0.

extension ExitPath {
    /// The obstacle-free exit of `arrow` on `grid`: body, then straight on to the grid edge. `toGridEdge` = the head's
    /// travel until its CENTRE leaves the grid (the last in-grid cell centre + 0.5 cell).
    public static func plain(arrow: ArrowSpec, grid: Grid) -> ExitPath {
        let n = arrow.cells.count
        var cells = arrow.cells
        let head = arrow.cells[n - 1]
        let steps = grid.stepsToEdge(from: head, arrow.dir)
        if steps > 0 { for k in 1...steps { cells.append(head.moved(arrow.dir, by: k)) } }
        let edge = Double(steps) + 0.5
        return ExitPath(cells: cells,
                        segments: [.body(-Double(n - 1)..<0), .ray(0..<edge)],
                        toGridEdge: edge)
    }

    /// Cells of the body (from the `.body` segment), else 1.
    public var bodyCellCount: Int {
        for s in segments { if case .body(let r) = s { return Int((-r.lowerBound).rounded()) + 1 } }
        return 1
    }

    /// Arc length of the listed cells (cells − 1).
    public var cellArcLength: Double { Double(max(0, cells.count - 1)) }

    /// The direction the path finally leaves in (the last step), or nil for a single cell.
    public var exitDirection: Dir? {
        guard cells.count >= 2 else { return nil }
        return Dir(from: cells[cells.count - 2], to: cells[cells.count - 1])
    }
}

/// An arc-length parametrised polyline in CELL units (independent of zoom): the corners of an `ExitPath` (or of an
/// arrow's body) with their arc positions. `point(at:)` extends the last direction past the end and the first one
/// before the start. Build once per mover, sample per frame.
public struct PathTrack: Sendable, Equatable {
    /// Corner positions in cell coordinates (c, r as Doubles), tail first; collinear points removed.
    public let corners: [CGPoint]
    /// Arc position (cells) of each corner; `arc[0] == 0`.
    public let arc: [Double]
    /// Direction of each straight run (corners.count − 1 entries; one entry for a single-cell path).
    public let runs: [Dir]

    public init(cells: [Cell], fallback: Dir = .right) {
        precondition(!cells.isEmpty, "PathTrack needs at least one cell")
        var pts: [CGPoint] = [CGPoint(x: cells[0].c, y: cells[0].r)]
        var arcs: [Double] = [0]
        var dirs: [Dir] = []
        var u = 0.0
        for i in 1..<cells.count {
            let d = Dir(from: cells[i - 1], to: cells[i]) ?? dirs.last ?? fallback
            u += 1
            if let last = dirs.last, last == d {
                pts[pts.count - 1] = CGPoint(x: cells[i].c, y: cells[i].r)
                arcs[arcs.count - 1] = u
            } else {
                dirs.append(d)
                pts.append(CGPoint(x: cells[i].c, y: cells[i].r))
                arcs.append(u)
            }
        }
        if dirs.isEmpty { dirs = [fallback] }
        corners = pts; arc = arcs; runs = dirs
    }

    public init(path: ExitPath) { self.init(cells: path.cells, fallback: path.exitDirection ?? .right) }

    /// Arc length of the listed polyline (cells).
    public var length: Double { arc[arc.count - 1] }

    /// The point at arc `u` (cells) in cell coordinates; before 0 / after `length` the first / last run continues.
    public func point(at u: Double) -> CGPoint {
        let n = corners.count
        if n == 1 || u <= 0 { return Self.step(corners[0], runs[0], u) }
        if u >= arc[n - 1] { return Self.step(corners[n - 1], runs[runs.count - 1], u - arc[n - 1]) }
        var i = 1
        while arc[i] < u { i += 1 }                         // arc[i-1] < u ≤ arc[i]
        return Self.step(corners[i - 1], runs[i - 1], u - arc[i - 1])
    }

    @inline(__always) static func step(_ p: CGPoint, _ d: Dir, _ k: Double) -> CGPoint {
        CGPoint(x: Double(p.x) + Double(d.dc) * k, y: Double(p.y) + Double(d.dr) * k)
    }

    /// The direction of travel at arc `u`: the run that contains u (a corner belongs to the run that LEAVES it).
    public func direction(at u: Double) -> Dir {
        if u < 0 || corners.count == 1 { return runs[0] }
        var i = 0
        while i + 1 < arc.count - 1 && arc[i + 1] <= u { i += 1 }
        return runs[min(i, runs.count - 1)]
    }

    /// Arc positions (cells) of the interior corners (turns), for keyframes at every turn.
    public var turnArcs: [Double] { arc.count > 2 ? Array(arc[1..<(arc.count - 1)]) : [] }
}
