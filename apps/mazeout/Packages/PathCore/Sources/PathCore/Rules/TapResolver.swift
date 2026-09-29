import Foundation

// C2 (SPEC-architecture §4.4, D4). A tap → a plan the board plays. Pure: nothing changes until `commit`.
//
// Conventions (with C1's Grid/ExitPath.swift):
// - ExitPath.cells = the body tail → head, then every cell the head passes (ray cells, tube cells in travel order,
//   corner cells) up to the grid edge. Segments: `.body(-(n-1)..<0)`, then `.ray`/`.tube`/`.corner` in head-travel cells
//   from 0; `toGridEdge` = the head's travel until its centre leaves the grid (last in-grid cell + 0.5).
// - A tube passage: `.enterTube` at the first mouth's OUTER edge (mouth centre − 0.5), `.leaveTube` at the far mouth's
//   outer edge (+ 0.5). `.pipeCount` at enter (default) or leave (`pipe.countAt`); `.pipeBreak` at leave (the board adds
//   the measured +0.05 s, Timing.pipeBreakAfterHeadLeaves).
// - `.keyReleased` at s = 0 (the ring vanishes at the tap, motion.md §5.2; the flight curve runs from the tap).
// - `.counterTick` / `.counterBreak` at s = 0 (the L50 box broke on the first-motion frame, motion.md §3.1) or, with
//   `box.countAt = leave`, when each member's head leaves the grid. `.elevatorEmptied` at s = 0.
// - Bump: `path` = the travelled part (body + passed cells, possibly through a tube), `toGridEdge` = the blocker cell's
//   near edge; `contactCells` = the head travel until its apex touches the blocker's edge (arrow: its stroke edge,
//   `bump.arrowEdgeInset` before the cell centre; obstacle: the cell edge); `contactPoint` = the blocker's cell.
// - A taped bundle exits only when EVERY member's ray is clear (VERIFIED L32 4/4); otherwise `tape.blockedPolicy`:
//   the whole bundle bumps (the plan of the member that makes contact first; every member turns red at contact).

extension BoardState {

    public func resolve(tap arrow: ArrowID) -> TapResolution {
        guard let i = index[arrow] else { return .ignored(.noArrow) }
        guard alive[i] else { return .ignored(.moving) }
        guard visible[i] else { return .ignored(.hidden) }
        let unit = unitIndices(i)
        if unit.contains(where: { bumping[$0] }) { return .ignored(.bumping) }
        var walks: [Int: Walk] = [:]
        var blocked: [Int] = []
        for m in unit {
            let w = walk(m, unit: unit, collect: true)
            walks[m] = w
            if w.blocked { blocked.append(m) }
        }
        if blocked.isEmpty { return .exit(exitPlan(tapped: i, unit: unit, walks: walks)) }
        func contact(_ m: Int) -> Double { contactCells(walks[m]!) }
        let firstContact = blocked.min { contact($0) != contact($1) ? contact($0) < contact($1) : ids[$0] < ids[$1] }!
        let who: Int
        switch rules.tape.blockedPolicy {
        case .bundleBumps: who = firstContact
        case .tappedBumps: who = blocked.contains(i) ? i : firstContact
        }
        return .bump(bumpPlan(who, walks[who]!))
    }

    func contactCells(_ w: Walk) -> Double {
        let inset = w.blockerIsArrow ? rules.bump.arrowEdgeInset : rules.bump.obstacleEdgeInset
        return max(0, w.blockerArc - inset - rules.bump.apex(w.dir))
    }

    func path(_ m: Int, _ w: Walk) -> ExitPath {
        let a = level.arrows[m]
        let n = a.cells.count
        return ExitPath(cells: a.cells + w.cells, segments: [.body(-Double(max(0, n - 1))..<0)] + w.segments,
                        toGridEdge: w.edge)
    }

    func bumpPlan(_ m: Int, _ w: Walk) -> BumpPlan {
        BumpPlan(arrow: ids[m], blocker: w.blocker!, gapCells: w.cells.count, path: path(m, w),
                 contactCells: contactCells(w), contactPoint: w.blockerCell)
    }

    /// The door a released key flies to: its explicit `opens` door while that one is still locked and not chosen in this
    /// plan, else the lowest-`order` locked door (declaration order breaks ties). VERIFIED L33 (left → right).
    func doorFor(key k: Int, excluding: Set<Int>) -> Int? {
        if let o = obs[k].opens, let d = obsIndex[o], obs[d].kind == .door, obs[d].door == .locked, !excluding.contains(d) {
            return d
        }
        var best: Int?
        for d in obs.indices where obs[d].kind == .door && obs[d].door == .locked && !excluding.contains(d) {
            if let b = best, (obs[b].order, b) <= (obs[d].order, d) { continue }
            best = d
        }
        return best
    }

    func exitPlan(tapped i: Int, unit: [Int], walks: [Int: Walk]) -> ExitPlan {
        let order = unit.sorted { ids[$0] < ids[$1] }
        var paths: [ArrowID: ExitPath] = [:]
        for m in order { paths[ids[m]] = path(m, walks[m]!) }
        var beats: [PlanBeat] = []
        // keys
        var chosen = Set<Int>()
        for m in order {
            for k in keysOn[m] ?? [] where !obs[k].done {
                guard let d = doorFor(key: k, excluding: chosen) else { continue }
                chosen.insert(d)
                beats.append(.keyReleased(key: obs[k].id, door: obs[d].id, s: 0))
            }
        }
        // pipes and corners
        var left: [Int: Int] = [:]
        var brokeHere = Set<Int>()
        for m in order {
            let w = walks[m]!
            for (k, enter, leave) in w.pipes {
                let p = obs[k].id
                beats.append(.enterTube(p, ids[m], s: enter))
                beats.append(.leaveTube(p, ids[m], s: leave))
                guard let c0 = obs[k].counter else { continue }
                let c = max(0, (left[k] ?? c0) - 1)
                left[k] = c
                beats.append(.pipeCount(p, remaining: c, s: rules.pipe.countAt == .enter ? enter : leave))
                if c == 0 && !brokeHere.contains(k) {
                    brokeHere.insert(k)
                    beats.append(.pipeBreak(p, s: leave))
                }
            }
            for (k, at) in w.corners { beats.append(.corner(obs[k].id, ids[m], s: at)) }
        }
        // boxes / curtains: every arrow cleared anywhere
        for k in obs.indices where obs[k].isCounterKind && !obs[k].done {
            guard let c0 = obs[k].counter else { continue }
            switch rules.box.countAt {
            case .tap:
                let c = max(0, c0 - order.count)
                beats.append(.counterTick(obs[k].id, remaining: c, s: 0))
                if c == 0 { beats.append(.counterBreak(obs[k].id, s: 0)) }
            case .leave:
                var c = c0
                for m in order where c > 0 {
                    c -= 1
                    let s = walks[m]!.edge
                    beats.append(.counterTick(obs[k].id, remaining: c, s: s))
                    if c == 0 { beats.append(.counterBreak(obs[k].id, s: s)) }
                }
            }
        }
        // an elevator emptied by this unit
        let gone = Set(order)
        for k in obs.indices where obs[k].kind == .elevator && !obs[k].done && !obs[k].members.isEmpty {
            if obs[k].members.allSatisfy({ !alive[$0] || gone.contains($0) }) {
                beats.append(.elevatorEmptied(obs[k].id, s: 0))
            }
        }
        // stable sort by s
        let sorted = beats.enumerated().sorted { $0.element.s != $1.element.s ? $0.element.s < $1.element.s : $0.offset < $1.offset }
            .map(\.element)
        let t = tapeOf[i]
        let tape: ObstacleID? = (t >= 0 && !obs[Int(t)].done && order.count > 1) ? obs[Int(t)].id : nil
        return ExitPlan(tapped: ids[i], unit: order.map { ids[$0] }, tape: tape, paths: paths, beats: sorted, combo: 1)
    }
}
