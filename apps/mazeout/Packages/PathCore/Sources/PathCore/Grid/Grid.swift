import Foundation

// C1 (SPEC-architecture §4.2). The level's hidden square grid. `Grid(cols:rows:maskRows:)` is a FIXED entry point:
// the ◆ `LevelSpec.grid` calls it (SPEC.md §5 item 17). Row-major, row 0 = the top row (as `Cell`).

/// The level's hidden square grid, with an optional silhouette mask.
public struct Grid: Sendable, Equatable {
    public let cols: Int
    public let rows: Int
    /// Row-major playable flags; nil = every cell playable. From the JSON "mask" rows ('#' = playable).
    public let mask: [Bool]?

    /// `mask` must hold exactly cols × rows flags; any other length is ignored (every cell playable).
    public init(cols: Int, rows: Int, mask: [Bool]? = nil) {
        self.cols = max(0, cols)
        self.rows = max(0, rows)
        self.mask = (mask?.count == self.cols * self.rows) ? mask : nil
    }

    /// Mask rows as in the level JSON: one string per row, '#' = playable (anything else = outside the silhouette).
    /// A row shorter than `cols` is padded with "outside"; a mask with the wrong number of rows is ignored.
    public init(cols: Int, rows: Int, maskRows: [String]?) {
        guard let maskRows, maskRows.count == rows, cols > 0 else { self.init(cols: cols, rows: rows, mask: nil); return }
        var flags: [Bool] = []
        flags.reserveCapacity(cols * rows)
        for line in maskRows {
            let chars = Array(line.utf8)
            for c in 0..<cols { flags.append(c < chars.count && chars[c] == UInt8(ascii: "#")) }
        }
        self.init(cols: cols, rows: rows, mask: flags)
    }

    /// Inside the bounds (ignores the mask).
    @inline(__always) public func inBounds(_ c: Cell) -> Bool { c.c >= 0 && c.r >= 0 && c.c < cols && c.r < rows }

    /// Inside the bounds AND inside the silhouette.
    public func contains(_ c: Cell) -> Bool {
        guard inBounds(c) else { return false }
        guard let mask else { return true }
        return mask[index(c)]
    }

    /// Row-major index (the occupancy arrays' layout). Only meaningful for cells inside the bounds.
    @inline(__always) public func index(_ c: Cell) -> Int { c.r * cols + c.c }

    /// The cell of a row-major index (inverse of `index`).
    @inline(__always) public func cell(at index: Int) -> Cell { Cell(index % cols, index / cols) }

    /// cols × rows.
    public var count: Int { cols * rows }

    /// Number of playable cells (the silhouette's area).
    public var playableCount: Int { mask.map { $0.lazy.filter { $0 }.count } ?? count }

    /// Every playable cell, row-major.
    public var cells: [Cell] {
        var out: [Cell] = []
        out.reserveCapacity(playableCount)
        for r in 0..<rows { for c in 0..<cols where contains(Cell(c, r)) { out.append(Cell(c, r)) } }
        return out
    }

    /// Steps from `c` in `d` until the cell leaves the BOUNDS (the ray of an arrow runs to the grid edge, §4.4).
    /// Returns 0 when the next cell is already outside.
    public func stepsToEdge(from c: Cell, _ d: Dir) -> Int {
        switch d {
        case .right: return max(0, cols - 1 - c.c)
        case .left: return max(0, c.c)
        case .down: return max(0, rows - 1 - c.r)
        case .up: return max(0, c.r)
        }
    }

    /// The mask back as JSON rows ('#' playable, '.' outside); nil when every cell is playable.
    public var maskRows: [String]? {
        guard let mask else { return nil }
        return (0..<rows).map { r in String((0..<cols).map { mask[r * cols + $0] ? "#" : "." }) }
    }
}
