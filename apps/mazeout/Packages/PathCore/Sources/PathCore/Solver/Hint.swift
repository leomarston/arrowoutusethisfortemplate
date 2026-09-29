import Foundation

// C2 (SPEC-architecture §4.14, §4.9). The hint: the first unit of a solvable order from the LIVE board. The light-bulb
// booster highlights it (VERIFIED: one free arrow, research/boosters.md §1) and the AutoPlayer / HeadlessDriver tap it.
// Policy PENDING-gameplay (which free arrow the original picks is unobservable); ours is deterministic: the greedy order's
// first unit when the greedy solves the rest of the board, else the first free unit (C4's search improves the dead ends).
//
// CORE-2, SPEC.md ruling 31: the bulb shows SPEC-gameplay §6.3's `unblocksMost` unit through its own entry,
// `hintUnit(_:policy:)` (via `LevelSession.hint(policy:)` / `useBooster(_:hintPolicy:freezeFlightFromUse:)`, which only the
// app's BoosterDirector calls); `hintUnit(_:)` above stays the greedy one the HeadlessDriver's solver strategy taps.
// Any free unit is safe in this genre (removing an arrow only clears rays), so the policy is a helpfulness choice.

extension Solver {
    public static func hintUnit(_ board: BoardState) -> [ArrowID]? {
        let free = board.freeUnits()
        guard let first = free.first else { return nil }
        let g = greedy(from: board)
        if g.solved, let u = g.order.first, free.contains(u) { return u }
        return first
    }

    /// SPEC.md ruling 31: the hint unit under `policy` from the live board; nil = no unit is free right now (only while a
    /// door is opening or every free unit is mid-bump). `.unblocksMost` = `hintScores(board).first`.
    public static func hintUnit(_ board: BoardState, policy: RulesTuning.HintPolicy) -> [ArrowID]? {
        switch policy {
        case .unblocksMost: return hintScores(board).first?.unit
        }
    }

    /// One free unit scored for SPEC-gameplay §6.3's `unblocksMost`.
    public struct HintScore: Equatable, Sendable {
        /// The unit's members, sorted (a tape bundle is scored and hinted as a whole).
        public var unit: [ArrowID]
        /// Live arrows outside the unit whose ray passes over any of the unit's cells, each counted once.
        public var unblocks: Int
        /// The unit's length in cells (a bundle: every member's cells) — the first tie-break.
        public var cells: Int

        public init(unit: [ArrowID], unblocks: Int, cells: Int) { self.unit = unit; self.unblocks = unblocks; self.cells = cells }
    }

    /// Every unit free right now, scored and ranked for `unblocksMost` (SPEC-gameplay §6.3): the most arrows unblocked
    /// first; ties → the longer unit (DECISION for a bundle: all its members' cells); then the lower id (the unit's lowest
    /// member). An arrow's RAY is the rules' own walk (`BoardState.walk`) with every live arrow ignored: straight from the
    /// head, through pipe passages and corner turns, to the grid edge or the first blocking obstacle (a locked or
    /// key-targeted door, a standing box / curtain, a pipe's side, a corner's spring) — so an arrow behind another arrow
    /// still counts for every unit its ray crosses, and one behind a locked door does not count for what lies past the
    /// door. Hidden arrows are not live and count for nothing. Pure: explores a copy, `board` is not changed; nil-free
    /// (an empty list when nothing is free).
    public static func hintScores(_ board: BoardState) -> [HintScore] {
        board.unblockScores().sorted { a, b in
            if a.unblocks != b.unblocks { return a.unblocks > b.unblocks }
            if a.cells != b.cells { return a.cells > b.cells }
            return a.unit[0] < b.unit[0]
        }
    }
}

extension BoardState {
    /// `Solver.hintScores` before the ranking (the free units in `freeUnits()` order).
    func unblockScores() -> [Solver.HintScore] {
        let free = freeUnits()
        guard !free.isEmpty else { return [] }
        var unitOf = [Int](repeating: -1, count: ids.count)          // arrow index → its free unit (−1: not free)
        for (u, unit) in free.enumerated() { for a in unit { if let i = index[a] { unitOf[i] = u } } }
        // the rules' walk on a copy whose arrows never block: obstacles (doors, boxes, pipes, corners) as they stand now
        let open = copy()
        for k in open.occ.indices { open.occ[k] = -1 }
        open.extraOcc = [:]
        var unblocks = [Int](repeating: 0, count: free.count)
        var lastCounted = [Int](repeating: -1, count: free.count)    // the arrow last counted for each unit: once per unit
        for i in ids.indices where alive[i] && visible[i] {
            for c in open.walk(i, unit: [i], collect: true).cells where grid.inBounds(c) {
                let g = grid.index(c)
                var owners = occ[g] >= 0 ? [occ[g]] : []
                if let more = extraOcc[g] { owners += more }
                for o in owners {
                    let u = unitOf[Int(o)]
                    guard u >= 0, u != unitOf[i], lastCounted[u] != i else { continue }
                    lastCounted[u] = i
                    unblocks[u] += 1
                }
            }
        }
        return free.enumerated().map { u, unit in
            Solver.HintScore(unit: unit, unblocks: unblocks[u],
                             cells: unit.reduce(0) { $0 + (index[$1].map { level.arrows[$0].cells.count } ?? 0) })
        }
    }
}
