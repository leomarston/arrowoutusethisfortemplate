import Foundation
import GameCore

// SortPuzzle's rules, solver and level generator. Pure functions over `[[Int]]` tubes (bottom → top). The solver and the
// generator are mirrored statement by statement by tools/sortpuzzle/ref.py (the goldens in Tests/Fixtures): change both.

/// A pour: the top run of tube `from` onto tube `to`.
public struct SortMove: Hashable, Codable, Sendable, CustomStringConvertible {
    public var from: Int
    public var to: Int
    public init(_ from: Int, _ to: Int) { self.from = from; self.to = to }
    public var description: String { "\(from)>\(to)" }
}

public enum SortMechanics {
    /// Units of the top colour on top of each other (0 for an empty tube).
    public static func topRun(_ t: [Int]) -> Int {
        guard let top = t.last else { return 0 }
        var n = 0
        for u in t.reversed() {
            if u != top { break }
            n += 1
        }
        return n
    }

    /// Full of one colour.
    public static func isComplete(_ t: [Int], capacity c: Int) -> Bool { t.count == c && topRun(t) == c }

    /// Every tube empty or complete (every colour has exactly `capacity` units, so each colour sits in one tube).
    public static func isSolved(_ tubes: [[Int]], capacity c: Int) -> Bool {
        tubes.allSatisfy { $0.isEmpty || isComplete($0, capacity: c) }
    }

    /// The rules' legality: a non-empty source, a target with room whose top is the source's colour (or empty).
    public static func canPour(_ tubes: [[Int]], from s: Int, to d: Int, capacity c: Int) -> Bool {
        guard s != d, tubes.indices.contains(s), tubes.indices.contains(d) else { return false }
        guard let top = tubes[s].last, tubes[d].count < c else { return false }
        guard let under = tubes[d].last else { return true }
        return under == top
    }

    /// Units a legal pour moves: the source's top run, as many as fit.
    public static func pourCount(_ tubes: [[Int]], from s: Int, to d: Int, capacity c: Int) -> Int {
        max(0, min(topRun(tubes[s]), c - tubes[d].count))
    }

    /// The tubes after a legal pour.
    public static func apply(_ tubes: [[Int]], _ m: SortMove, capacity c: Int) -> [[Int]] {
        var out = tubes
        let n = pourCount(tubes, from: m.from, to: m.to, capacity: c)
        let moved = Array(out[m.from].suffix(n))
        out[m.from].removeLast(n)
        out[m.to].append(contentsOf: moved)
        return out
    }

    /// Every legal pour in (from, to) order.
    public static func legalMoves(_ tubes: [[Int]], capacity c: Int) -> [SortMove] {
        var out: [SortMove] = []
        for s in tubes.indices {
            for d in tubes.indices where canPour(tubes, from: s, to: d, capacity: c) { out.append(SortMove(s, d)) }
        }
        return out
    }

    /// "Stuck" is the absence of any legal pour.
    public static func hasLegalMove(_ tubes: [[Int]], capacity c: Int) -> Bool {
        for s in tubes.indices {
            for d in tubes.indices where canPour(tubes, from: s, to: d, capacity: c) { return true }
        }
        return false
    }

    /// The solver's moves: legal pours minus the pointless ones (a complete source, a whole-tube pour into an empty tube,
    /// any empty target but the first); pours onto a tube first, then into the empty one (ref.py `useful_moves`).
    public static func usefulMoves(_ tubes: [[Int]], capacity c: Int) -> [SortMove] {
        let firstEmpty = tubes.firstIndex(where: { $0.isEmpty }) ?? -1
        var onto: [SortMove] = []
        var intoEmpty: [SortMove] = []
        for s in tubes.indices {
            let src = tubes[s]
            guard let top = src.last else { continue }
            let run = topRun(src)
            if src.count == c && run == c { continue }
            for d in tubes.indices where d != s {
                let dst = tubes[d]
                if dst.count >= c { continue }
                if let under = dst.last {
                    if under == top { onto.append(SortMove(s, d)) }
                } else {
                    if run == src.count || d != firstEmpty { continue }
                    intoEmpty.append(SortMove(s, d))
                }
            }
        }
        return onto + intoEmpty
    }

    /// The state as a multiset of tubes (the solver visits each once): sorted tubes, each unit a byte, 255 after a tube.
    public static func key(_ tubes: [[Int]]) -> [UInt8] {
        var out: [UInt8] = []
        for t in tubes.sorted(by: { $0.lexicographicallyPrecedes($1) }) {
            for u in t { out.append(UInt8(truncatingIfNeeded: u)) }
            out.append(255)
        }
        return out
    }
}

/// Bounded depth-first search (ref.py `solve`). `budget` = states expanded; nil = no solution found within it.
public enum SortSolver {
    public static func solve(_ start: [[Int]], capacity c: Int, budget: Int) -> [SortMove]? {
        if SortMechanics.isSolved(start, capacity: c) { return [] }
        var visited: Set<[UInt8]> = [SortMechanics.key(start)]
        var expanded = 1
        var frames: [SolverFrame] = [SolverFrame(state: start, moves: SortMechanics.usefulMoves(start, capacity: c), next: 0)]
        var path: [SortMove] = []
        while let top = frames.last {
            if top.next >= top.moves.count {
                frames.removeLast()
                if !path.isEmpty { path.removeLast() }
                continue
            }
            let m = top.moves[top.next]
            frames[frames.count - 1].next += 1
            let next = SortMechanics.apply(top.state, m, capacity: c)
            let k = SortMechanics.key(next)
            if visited.contains(k) { continue }
            visited.insert(k)
            path.append(m)
            if SortMechanics.isSolved(next, capacity: c) { return path }
            if expanded >= budget { return nil }
            expanded += 1
            frames.append(SolverFrame(state: next, moves: SortMechanics.usefulMoves(next, capacity: c), next: 0))
        }
        return nil
    }

    struct SolverFrame {
        let state: [[Int]]
        let moves: [SortMove]
        var next: Int
    }
}

/// Seeded, deterministic level generation (ref.py `generate`): the same level for every player and every run.
public enum SortGenerator {
    /// Deals `colors` × `capacity` units at random into full tubes (+ the band's empty tubes) until a deal has no complete
    /// tube and the solver solves it within `solverBudget`; after `maxAttempts` deals, the last one with one empty tube per
    /// colour (always solvable: every unit can go straight onto its colour's tube).
    public static func level(_ n: Int, rules: SortRules) -> SortLevel {
        let lv = rules.levels
        let b = lv.band(for: n)
        let k = max(0, b.colors), c = max(0, b.capacity), e = max(0, b.empty)
        var rng = PathRandom(seed: PathRandom.levelSeed(level: n, salt: lv.salt))
        var last: [[Int]] = []
        for _ in 0..<max(1, lv.maxAttempts) {
            var units: [Int] = []
            units.reserveCapacity(k * c)
            for colour in 0..<k {
                for _ in 0..<c { units.append(colour) }
            }
            rng.shuffle(&units)
            var tubes: [[Int]] = (0..<k).map { i in Array(units[(i * c)..<((i + 1) * c)]) }
            tubes += Array(repeating: [Int](), count: e)
            last = tubes
            if tubes.prefix(k).contains(where: { SortMechanics.isComplete($0, capacity: c) }) { continue }
            if SortSolver.solve(tubes, capacity: c, budget: lv.solverBudget) != nil {
                return SortLevel(level: n, tag: lv.tag(for: n), capacity: c, colors: k, tubes: tubes)
            }
        }
        let fallback = Array(last.prefix(k)) + Array(repeating: [Int](), count: max(e, k))
        return SortLevel(level: n, tag: lv.tag(for: n), capacity: c, colors: k, tubes: fallback)
    }
}
