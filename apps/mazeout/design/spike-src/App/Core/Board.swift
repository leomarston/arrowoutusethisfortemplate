import Foundation

/// What a tap does (escape rule, GAMEPROMPT §10.9): the head's straight ray to the grid edge must be free of
/// every live arrow's cells; vacated cells (dots) never block.
enum TapOutcome: Equatable {
    case exits(arrow: Int)
    /// A taped bundle (L32): one tap sends every member out together.
    case exitsGroup(arrows: [Int], tape: Int)
    /// `gap` = empty cells strictly between the head and the blocker's first cell on the ray.
    case blocked(arrow: Int, blocker: Int, gap: Int)
    case ignored
}

/// Live board state over a flat occupancy grid (Int32 per cell, -1 empty). A tap costs O(ray length).
final class BoardState {
    let level: LevelSpec
    private(set) var occ: [Int32]
    private(set) var alive: [Bool]
    private(set) var aliveCount: Int
    /// Tape bundles: members leave together, only when every member's ray is clear (the some-clear case is
    /// UNKNOWN on the original; this is the conservative reading).
    let bundles: [[Int]]
    private(set) var bundleOf: [Int: Int] = [:]
    private(set) var bundleAlive: [Bool]

    init(level: LevelSpec) {
        self.level = level
        bundles = level.tapeBundles()
        bundleAlive = [Bool](repeating: true, count: bundles.count)
        occ = [Int32](repeating: -1, count: level.cols * level.rows)
        alive = [Bool](repeating: true, count: level.arrows.count)
        aliveCount = level.arrows.count
        for (i, a) in level.arrows.enumerated() {
            for p in a.cells { occ[p.r * level.cols + p.c] = Int32(i) }
        }
        for (b, m) in bundles.enumerated() { for a in m { bundleOf[a] = b } }
    }

    @inline(__always) func owner(_ p: Cell) -> Int? {
        guard level.inGrid(p) else { return nil }
        let v = occ[p.r * level.cols + p.c]
        return v < 0 ? nil : Int(v)
    }

    func firstBlocker(of arrow: Int) -> (blocker: Int, gap: Int)? {
        let a = level.arrows[arrow]
        var p = a.head + a.dir
        var gap = 0
        while level.inGrid(p) {
            let v = occ[p.r * level.cols + p.c]
            if v >= 0 && Int(v) != arrow { return (Int(v), gap) }
            gap += 1
            p = p + a.dir
        }
        return nil
    }

    func isFree(_ arrow: Int) -> Bool { alive[arrow] && firstBlocker(of: arrow) == nil }

    /// The unit a tap moves: the arrow, or its whole live tape bundle.
    func unit(of arrow: Int) -> [Int] {
        if let b = bundleOf[arrow], bundleAlive[b] { return bundles[b] }
        return [arrow]
    }

    func unitFree(_ arrow: Int) -> Bool { alive[arrow] && unit(of: arrow).allSatisfy { isFree($0) } }

    /// Resolves a tap. A free arrow leaves the occupancy at once (its exit animation is cosmetic).
    func tap(_ arrow: Int) -> TapOutcome {
        guard arrow >= 0, arrow < alive.count, alive[arrow] else { return .ignored }
        if let hit = firstBlocker(of: arrow) { return .blocked(arrow: arrow, blocker: hit.blocker, gap: hit.gap) }
        if let b = bundleOf[arrow], bundleAlive[b] {
            let members = bundles[b]
            if let stuck = members.first(where: { !isFree($0) }), let hit = firstBlocker(of: stuck) {
                return .blocked(arrow: arrow, blocker: hit.blocker, gap: 0)   // placeholder bump (rule UNKNOWN)
            }
            bundleAlive[b] = false
            for m in members { remove(m) }
            return .exitsGroup(arrows: members, tape: b)
        }
        remove(arrow)
        return .exits(arrow: arrow)
    }

    func remove(_ arrow: Int) {
        guard alive[arrow] else { return }
        alive[arrow] = false
        aliveCount -= 1
        for p in level.arrows[arrow].cells where occ[p.r * level.cols + p.c] == Int32(arrow) {
            occ[p.r * level.cols + p.c] = -1
        }
    }

    func freeArrows() -> [Int] { (0..<alive.count).filter { isFree($0) } }

    /// Greedy rounds decide solvability: removing an arrow only frees cells, so a free arrow stays free.
    static func greedy(_ level: LevelSpec) -> (order: [Int], stuck: [Int], rounds: Int) {
        let b = BoardState(level: level)
        var order: [Int] = []
        var rounds = 0
        while b.aliveCount > 0 {
            let free = (0..<b.alive.count).filter { b.unitFree($0) }
            if free.isEmpty { break }
            rounds += 1
            for a in free where b.alive[a] {
                if case let .exitsGroup(m, _) = b.tap(a) { order += m } else { order.append(a) }
            }
        }
        return (order, (0..<b.alive.count).filter { b.alive[$0] }, rounds)
    }

    /// Structural checks: steps orthogonal, no shared cells, last step matches dir, ray misses own body.
    static func validate(_ level: LevelSpec) -> [String] {
        var problems: [String] = []
        var seen = [Int: Int]()
        for (i, a) in level.arrows.enumerated() {
            if a.cells.count < 2 { problems.append("arrow \(i): < 2 cells") }
            for p in a.cells {
                if !level.inGrid(p) { problems.append("arrow \(i): \(p) outside grid") }
                let k = p.r * level.cols + p.c
                if let o = seen[k] { problems.append("arrow \(i) shares \(p) with \(o)") } else { seen[k] = i }
            }
            for (x, y) in zip(a.cells, a.cells.dropFirst()) where Dir(from: x, to: y) == nil {
                problems.append("arrow \(i): \(x)->\(y) not orthogonal")
            }
            if a.cells.count >= 2, Dir(from: a.cells[a.cells.count - 2], to: a.head) != a.dir {
                problems.append("arrow \(i): head dir mismatch")
            }
            let body = Set(a.cells)
            var p = a.head + a.dir
            while level.inGrid(p) {
                if body.contains(p) { problems.append("arrow \(i): ray crosses own body"); break }
                p = p + a.dir
            }
        }
        return problems
    }
}
