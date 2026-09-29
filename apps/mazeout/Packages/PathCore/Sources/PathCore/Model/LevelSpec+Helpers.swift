import Foundation

// C1 (SPEC-architecture §4.3). Helpers over the ◆ level model (extensions only: the ◆ file is frozen).

extension ArrowSpec {
    public var head: Cell { cells[cells.count - 1] }
    public var tail: Cell { cells[0] }
    public var length: Int { cells.count }
    /// The direction of the last step (what `dir` must equal, validator), nil for a single cell.
    public var lastStepDir: Dir? { cells.count >= 2 ? Dir(from: cells[cells.count - 2], to: cells[cells.count - 1]) : nil }
}

extension LevelSpec {
    public func arrow(_ id: ArrowID) -> ArrowSpec? { arrows.first { $0.id == id } }
    public func obstacle(_ id: ObstacleID) -> ObstacleSpec? { obstacles.first { $0.id == id } }
    /// Arrows visible at the start (not hidden by an obstacle, layer 1).
    public var startArrows: [ArrowSpec] { arrows.filter { $0.hiddenBy == nil && $0.layer == 1 } }
    /// Σ cells of every arrow.
    public var arrowCells: Int { arrows.reduce(0) { $0 + $1.cells.count } }

    /// Geometry-level problems (C1's share of the validator, §4.14; C4's Validator adds obstacles, sprites and the
    /// solver): ≥ 2 cells, orthogonal steps, `dir` = the last step, inside the grid bounds, no cell of the same layer
    /// shared by two arrows, the head's ray never meets its own body, unique ids. Empty = structurally sound.
    public func structuralProblems() -> [String] {
        var out: [String] = []
        let g = grid
        var seenIDs = Set<ArrowID>()
        var occupied: [Int: [Int: ArrowID]] = [:]            // layer → cell index → arrow
        for a in arrows {
            if !seenIDs.insert(a.id).inserted { out.append("arrow \(a.id.raw): duplicate id") }
            if a.cells.count < 2 { out.append("arrow \(a.id.raw): \(a.cells.count) cell(s), needs ≥ 2") }
            for (x, y) in zip(a.cells, a.cells.dropFirst()) where Dir(from: x, to: y) == nil {
                out.append("arrow \(a.id.raw): step \(x)→\(y) is not orthogonal")
            }
            if let last = a.lastStepDir, last != a.dir {
                out.append("arrow \(a.id.raw): dir \(a.dir.rawValue) but the last step goes \(last.rawValue)")
            }
            for c in a.cells {
                if !g.inBounds(c) { out.append("arrow \(a.id.raw): \(c) outside the \(cols)×\(rows) grid"); continue }
                let k = g.index(c)
                if let other = occupied[a.layer]?[k], other != a.id {
                    out.append("arrow \(a.id.raw) shares \(c) with arrow \(other.raw) (layer \(a.layer))")
                } else {
                    occupied[a.layer, default: [:]][k] = a.id
                }
            }
            if a.cells.count >= 1 {
                let body = Set(a.cells)
                var p = a.head + a.dir
                while g.inBounds(p) {
                    if body.contains(p) { out.append("arrow \(a.id.raw): its ray crosses its own body at \(p)"); break }
                    p = p + a.dir
                }
            }
        }
        return out
    }
}
