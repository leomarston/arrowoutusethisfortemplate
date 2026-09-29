import Foundation

// PathCore candidate: pure Foundation, no UIKit. Compiles and runs on macOS (swiftc) as well as iOS.

/// A cell on the hidden square grid. Row 0 is the top row. JSON: `[col, row]`.
struct Cell: Hashable {
    var c: Int
    var r: Int
    init(_ c: Int, _ r: Int) { self.c = c; self.r = r }
    static func + (a: Cell, d: Dir) -> Cell { Cell(a.c + d.dc, a.r + d.dr) }
}

extension Cell: Codable {
    init(from decoder: Decoder) throws {
        var u = try decoder.unkeyedContainer()
        c = try u.decode(Int.self)
        r = try u.decode(Int.self)
    }
    func encode(to encoder: Encoder) throws {
        var u = encoder.unkeyedContainer()
        try u.encode(c)
        try u.encode(r)
    }
}

enum Dir: String, Codable, CaseIterable {
    case up, down, left, right
    var dc: Int { self == .left ? -1 : (self == .right ? 1 : 0) }
    var dr: Int { self == .up ? -1 : (self == .down ? 1 : 0) }
    var reversed: Dir {
        switch self { case .up: return .down; case .down: return .up; case .left: return .right; case .right: return .left }
    }
    init?(from a: Cell, to b: Cell) {
        switch (b.c - a.c, b.r - a.r) {
        case (0, -1): self = .up
        case (0, 1): self = .down
        case (-1, 0): self = .left
        case (1, 0): self = .right
        default: return nil
        }
    }
}

/// One snake arrow: orthogonal steps through cell centres, TAIL first, HEAD last; the head points `dir`.
struct ArrowSpec: Codable, Hashable {
    var cells: [Cell]
    var dir: Dir
    var head: Cell { cells[cells.count - 1] }
    var tail: Cell { cells[0] }
}

/// Spike placeholder for the obstacle seen on L32 (4 parallel arrows tied by a pink tape). Rule UNKNOWN.
struct TapeSpec: Codable, Hashable {
    var cells: [Cell]
    var orientation: String
}

/// Level file (spike schema; see design/tech-spike.md "Level JSON schema" for the proposed real one).
struct LevelSpec: Codable {
    var id: Int
    var cols: Int
    var rows: Int
    var arrows: [ArrowSpec]
    var tapes: [TapeSpec]?
    /// Optional silhouette: `rows` strings of `cols` chars, '#' = playable cell.
    var mask: [String]?
    var timeLimit: Int?
    var hearts: Int?
    var source: String?

    var cellCount: Int { arrows.reduce(0) { $0 + $1.cells.count } }

    init(id: Int, cols: Int, rows: Int, arrows: [ArrowSpec], tapes: [TapeSpec]?, mask: [String]?, timeLimit: Int?,
         hearts: Int?, source: String?) {
        self.id = id; self.cols = cols; self.rows = rows; self.arrows = arrows; self.tapes = tapes
        self.mask = mask; self.timeLimit = timeLimit; self.hearts = hearts; self.source = source
    }

    private enum K: String, CodingKey {
        case id, level, cols, rows, arrows, tapes, obstacles, mask, timeLimit, timer_s, hearts, source, shot
    }
    private struct Obstacle: Decodable { var kind: String; var cells: [Cell] }

    /// Reads both the spike schema and the phone player's research/levels/Lnnn.json schema
    /// (`level`, `timer_s`, `obstacles[{kind: "tape_pink", cells}]`).
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: K.self)
        id = try c.decodeIfPresent(Int.self, forKey: .id) ?? c.decode(Int.self, forKey: .level)
        cols = try c.decode(Int.self, forKey: .cols)
        rows = try c.decode(Int.self, forKey: .rows)
        arrows = try c.decode([ArrowSpec].self, forKey: .arrows)
        if let t = try c.decodeIfPresent([TapeSpec].self, forKey: .tapes) {
            tapes = t
        } else if let obs = try c.decodeIfPresent([Obstacle].self, forKey: .obstacles) {
            tapes = obs.filter { $0.kind.hasPrefix("tape") }.map { o in
                let cs = Set(o.cells.map(\.c)).count, rs = Set(o.cells.map(\.r)).count
                return TapeSpec(cells: o.cells, orientation: rs > cs ? "vertical" : "horizontal")
            }
        } else { tapes = nil }
        mask = try c.decodeIfPresent([String].self, forKey: .mask)
        timeLimit = try c.decodeIfPresent(Int.self, forKey: .timeLimit) ?? c.decodeIfPresent(Int.self, forKey: .timer_s)
        hearts = try c.decodeIfPresent(Int.self, forKey: .hearts)
        source = try c.decodeIfPresent(String.self, forKey: .source) ?? c.decodeIfPresent(String.self, forKey: .shot)
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: K.self)
        try c.encode(id, forKey: .id); try c.encode(cols, forKey: .cols); try c.encode(rows, forKey: .rows)
        try c.encode(arrows, forKey: .arrows); try c.encodeIfPresent(tapes, forKey: .tapes)
        try c.encodeIfPresent(mask, forKey: .mask); try c.encodeIfPresent(timeLimit, forKey: .timeLimit)
        try c.encodeIfPresent(hearts, forKey: .hearts); try c.encodeIfPresent(source, forKey: .source)
    }

    /// Arrows tied by each tape (the tape covers one cell of each).
    func tapeBundles() -> [[Int]] {
        (tapes ?? []).map { t in
            let tc = Set(t.cells)
            return arrows.indices.filter { !Set(arrows[$0].cells).isDisjoint(with: tc) }
        }
    }

    func inGrid(_ p: Cell) -> Bool { p.c >= 0 && p.r >= 0 && p.c < cols && p.r < rows }
}

/// Deterministic RNG (SplitMix64) so a seed always gives the same synthetic board.
struct SplitMix64: RandomNumberGenerator {
    private var state: UInt64
    init(seed: UInt64) { state = seed }
    mutating func next() -> UInt64 {
        state &+= 0x9E37_79B9_7F4A_7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }
}
