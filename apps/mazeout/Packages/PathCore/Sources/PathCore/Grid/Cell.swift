import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.2). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests). Real code, not a stub: it is tiny and final.
// Owners add helpers in EXTENSIONS in their own files, never here.

/// A cell of the board's hidden square grid. Column `c` grows to the right, row `r` grows DOWN (row 0 = the top row).
/// JSON: `[c, r]` (every schema: phone, video, bundle).
public struct Cell: Hashable, Codable, Sendable, CustomStringConvertible {
    public var c: Int
    public var r: Int

    public init(_ c: Int, _ r: Int) { self.c = c; self.r = r }
    public init(c: Int, r: Int) { self.c = c; self.r = r }

    /// The orthogonal neighbour one step in `d`.
    public static func + (a: Cell, d: Dir) -> Cell { Cell(a.c + d.dc, a.r + d.dr) }

    /// `n` steps in `d` (n may be 0 or negative).
    public func moved(_ d: Dir, by n: Int = 1) -> Cell { Cell(c + d.dc * n, r + d.dr * n) }

    public var description: String { "[\(c),\(r)]" }

    public init(from decoder: Decoder) throws {
        var u = try decoder.unkeyedContainer()
        c = try u.decode(Int.self)
        r = try u.decode(Int.self)
    }

    public func encode(to encoder: Encoder) throws {
        var u = encoder.unkeyedContainer()
        try u.encode(c)
        try u.encode(r)
    }
}
