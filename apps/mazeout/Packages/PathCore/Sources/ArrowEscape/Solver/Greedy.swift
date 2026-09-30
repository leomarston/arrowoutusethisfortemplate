import Foundation
import GameCore

// C2 (SPEC-architecture §4.14). The greedy solver (the spike's): each round removes every unit that is free at the
// round's start (each unit re-resolved just before its removal, so a pipe consumed earlier in the round is respected);
// the doors whose keys left in a round burst before the next one (the board's 1.14 s). Exact for monotone boards
// (removals only free cells); boards with non-monotone obstacles (a pipe whose last passage changes a ray, an elevator)
// are C4's `Solver.solve` (bounded DFS). `rounds` is the dependency depth (the difficulty metric).

public enum Solver {}

public struct GreedyResult: Sendable, Equatable {
    /// Rounds that removed at least one unit (the dependency depth).
    public var rounds: Int
    /// Units in removal order (each unit's members sorted).
    public var order: [[ArrowID]]
    /// Units removed per round.
    public var roundSizes: [Int]
    /// Arrows left (live + hidden) when nothing was free any more; empty = solved.
    public var stuck: [ArrowID]
    /// Free units at the start.
    public var freeAtStart: Int

    public var solved: Bool { stuck.isEmpty }

    public init(rounds: Int, order: [[ArrowID]], roundSizes: [Int], stuck: [ArrowID], freeAtStart: Int) {
        self.rounds = rounds; self.order = order; self.roundSizes = roundSizes; self.stuck = stuck
        self.freeAtStart = freeAtStart
    }
}

extension Solver {
    /// Greedy solve of a level from its start state.
    public static func greedy(_ level: LevelSpec, rules: RulesTuning = .default) -> GreedyResult {
        greedy(from: BoardState(level: level, rules: rules))
    }

    /// Greedy solve from any board state (explores a copy; `board` is not changed). Arrows mid-bump count as at rest.
    public static func greedy(from board: BoardState) -> GreedyResult {
        let b = board.copy()
        b.settleTransients()
        var rounds = 0
        var order: [[ArrowID]] = []
        var sizes: [Int] = []
        var freeAtStart = -1
        while !b.isCleared {
            let free = b.freeUnits()
            if freeAtStart < 0 { freeAtStart = free.count }
            if free.isEmpty {
                if b.burstTargetedDoors() { continue }
                break
            }
            var removed = 0
            for u in free {
                let r = b.resolve(tap: u[0])
                guard case .exit(let plan) = r else { continue }
                b.commit(r)
                order.append(plan.unit)
                removed += 1
            }
            b.burstTargetedDoors()
            if removed == 0 { break }
            rounds += 1
            sizes.append(removed)
        }
        return GreedyResult(rounds: rounds, order: order, roundSizes: sizes,
                            stuck: b.isCleared ? [] : (b.live + b.hidden).sorted(), freeAtStart: max(0, freeAtStart))
    }
}

extension BoardState {
    /// Arrows mid-bump are back at rest (their contact is assumed taken); used on solver copies only.
    func settleTransients() {
        for i in bumping.indices { bumping[i] = false }
        pendingBumps = [:]
    }

    /// Opens every door a key is flying to (the solver skips the 1.14 s flight). Returns whether any opened.
    @discardableResult
    func burstTargetedDoors() -> Bool {
        var any = false
        for k in obs.indices where obs[k].kind == .door && obs[k].door == .targeted {
            _ = ack(.doorBurst(obs[k].id))
            any = true
        }
        return any
    }

    /// Doors a key is flying to (waiting for the board's burst ack).
    public var targetedDoors: [ObstacleID] {
        obs.filter { $0.kind == .door && $0.door == .targeted }.map(\.id)
    }
}
