import Foundation
import GameCore

// C4 (SPEC-architecture §4.14). The exact solver over the GAME's rules (C2's BoardState): the greedy first (a witness when
// it clears the board); on a monotone board (no counted pipe, no inactive elevator: removals only ever free cells) a
// greedy failure is final; otherwise a bounded depth-first search with a memo over the full board state, trying the
// moves that break nothing first. `.undecided` when the node budget runs out (never guessed).

public enum SolveResult: Sendable, Equatable {
    /// A clearing order (units, each sorted).
    case solved([[ArrowID]])
    case unsolvable
    /// The budget ran out after `nodes` states.
    case undecided(nodes: Int)

    public var isSolved: Bool { if case .solved = self { return true }; return false }
    public var order: [[ArrowID]]? { if case .solved(let o) = self { return o }; return nil }
}

extension Solver {

    /// Greedy, then (non-monotone boards only) the bounded search. `budget` = search nodes.
    public static func solve(_ level: LevelSpec, budget: Int = 200_000, rules: RulesTuning = .default) -> SolveResult {
        solve(from: BoardState(level: level, rules: rules), budget: budget)
    }

    /// The same from any board state (explores copies; `board` is not changed).
    public static func solve(from board: BoardState, budget: Int = 200_000) -> SolveResult {
        let g = greedy(from: board)
        if g.solved { return .solved(g.order) }
        if board.isMonotone { return .unsolvable }
        return search(from: board, budget: budget)
    }

    /// The bounded search alone (no greedy shortcut): SolverTests compare it with the greedy on monotone boards.
    public static func search(from board: BoardState, budget: Int = 200_000) -> SolveResult {
        let start = board.copy()
        start.settleTransients()
        var seen = Set<[Int]>()
        var nodes = 0
        var exhausted = false
        var path: [[ArrowID]] = []
        func rec(_ b: BoardState) -> Bool {
            if b.isCleared { return true }
            nodes += 1
            if nodes > budget { exhausted = true; return false }
            let key = b.searchKey()
            if !seen.insert(key).inserted { return false }
            let free = b.freeUnits()
            if free.isEmpty {
                let c = b.copy()
                return c.burstTargetedDoors() ? rec(c) : false
            }
            // moves that break nothing (no pipe breaks, no elevator activates) first, then by first member
            var moves: [(breaks: Bool, unit: [ArrowID], r: TapResolution)] = []
            for u in free {
                let r = b.resolve(tap: u[0])
                guard case .exit(let plan) = r else { continue }
                let breaks = plan.beats.contains {
                    switch $0 { case .pipeBreak, .elevatorEmptied: return true; default: return false }
                }
                moves.append((breaks, u, r))
            }
            moves.sort { ($0.breaks ? 1 : 0, $0.unit[0]) < ($1.breaks ? 1 : 0, $1.unit[0]) }
            for m in moves {
                let c = b.copy()
                c.commit(m.r)
                c.burstTargetedDoors()
                path.append(m.unit)
                if rec(c) { return true }
                if exhausted { return false }
                path.removeLast()
            }
            return false
        }
        let ok = rec(start)
        if exhausted { return .undecided(nodes: nodes) }
        return ok ? .solved(path) : .unsolvable
    }
}

extension BoardState {
    /// No obstacle that can make a free unit blocked again: every counted pipe is broken and every elevator active.
    /// (Doors, boxes and curtains only ever open; their hidden arrows lie under their own cells, validator.)
    public var isMonotone: Bool {
        !obs.contains { o in
            (o.kind == .pipe && !o.done && o.counter != nil) || (o.kind == .elevator && !o.done && !o.members.isEmpty)
        }
    }

    /// The search memo key: alive and revealed arrows, every obstacle's state.
    func searchKey() -> [Int] {
        var k: [Int] = []
        k.reserveCapacity(alive.count / 30 + obs.count * 3 + 2)
        var word = 0, bit = 0
        for i in alive.indices {
            if alive[i] { word |= 1 << bit }
            bit += 1
            if visible[i] { word |= 1 << bit }
            bit += 1
            if bit >= 60 { k.append(word); word = 0; bit = 0 }
        }
        k.append(word)
        for o in obs {
            k.append((o.done ? 1 : 0) | (o.door == .locked ? 0 : o.door == .targeted ? 2 : 4))
            k.append(o.counter ?? Int.min)
        }
        return k
    }
}
