import Foundation
import GameCore

// C2 (SPEC-architecture §4.4). THE blocking rule (VERIFIED spike + research/levels.md): walk from the head's next cell in
// its direction to the grid edge; the first live occupant blocks. Vacated cells never block. Obstacles on the way:
// a locked (or targeted, not yet burst) door and a standing box / curtain block; a pipe tube blocks except a MOUTH
// entered against its `out` direction, which carries the ray through the tube and out of the other mouth in that mouth's
// `out` direction (chained pipes allowed); a corner turns a ray from an accepting side and blocks the others; pipe
// passages and corner turns share the `pipe.maxHops` guard (arrowcore MAX_HOPS: the 17th hop blocks, so a corner or pipe
// cycle can never freeze a walk). A LOCKED DOOR BLOCKS FIRST: an obstacle lying under a door (v552 L69: pipes under
// doors) does nothing until the door's burst, whatever the order of the level's obstacle list (content recast
// 2026-09-25, SPEC.md §5 item 26). Members of the moving unit (a tape bundle) never block each other; an arrow's own
// body never blocks it (the validator rejects such content). Arc positions are in cells of the HEAD's travel from its
// resting cell centre.

extension BoardState {

    struct Walk {
        var blocked = false
        var blocker: Blocker?
        var blockerIsArrow = false
        var blockerCell = Cell(0, 0)
        /// Arc of the blocker cell's centre.
        var blockerArc = 0.0
        /// The head's direction at the end of the walk (after tubes / corners).
        var dir: Dir
        /// Cells the head passes after its resting cell (rays, tubes, corners), excluding a blocker cell.
        var cells: [Cell] = []
        /// `.ray` / `.tube` / `.corner` segments after the body.
        var segments: [PathSegment] = []
        /// Tube passages: obstacle index, head arc entering the first mouth's outer edge, leaving the far mouth's edge.
        var pipes: [(k: Int, enter: Double, leave: Double)] = []
        var corners: [(k: Int, at: Double)] = []
        /// Clear: the head's travel until its centre leaves the grid (toGridEdge). Blocked: the blocker cell's near edge.
        var edge = 0.0

        init(dir: Dir) { self.dir = dir }
    }

    /// Whether arrow `i`'s ray (moving with `unit`) is clear right now.
    @inline(__always) func isClear(_ i: Int, unit: [Int]) -> Bool { !walk(i, unit: unit, collect: false).blocked }

    /// The walk of arrow `i`'s head. `collect` = build cells / segments / beats (a plan); false = only the verdict.
    func walk(_ i: Int, unit: [Int], collect: Bool) -> Walk {
        let a = level.arrows[i]
        var d = a.dir
        var w = Walk(dir: d)
        guard var p = a.cells.last else { w.edge = 0.5; return w }
        var arc = 0.0
        var segStart = 0.0
        var hops = 0
        func block(_ b: Blocker, isArrow: Bool, at q: Cell) {
            w.blocked = true
            w.blocker = b
            w.blockerIsArrow = isArrow
            w.blockerCell = q
            w.blockerArc = arc
            w.edge = arc - 0.5
            w.dir = d
            if collect && w.edge > segStart { w.segments.append(.ray(segStart..<w.edge)) }
        }
        while true {
            let q = p + d
            if !grid.inBounds(q) {
                w.edge = arc + 0.5
                w.dir = d
                if collect && w.edge > segStart { w.segments.append(.ray(segStart..<w.edge)) }
                return w
            }
            arc += 1
            let qi = grid.index(q)
            let ob = obsCell[qi]
            if ob >= 0 {
                var k = Int(ob)
                // a door on the cell is still blocking (an opened door leaves the cell's obstacle stack): it blocks
                // before the pipe / corner / box under it
                if obs[k].kind != .door, let more = extraObs[qi], let dk = more.first(where: { obs[Int($0)].kind == .door }) {
                    k = Int(dk)
                }
                let o = obs[k]
                switch o.kind {
                case .pipe:
                    var entry: Int?
                    if o.ends.count == 2 {
                        if o.ends[0].cell == q && o.ends[0].out == d.opposite { entry = 0 }
                        else if o.ends[1].cell == q && o.ends[1].out == d.opposite { entry = 1 }
                    }
                    guard let e = entry, hops < rules.pipe.maxHops else {
                        block(.obstacle(o.id), isArrow: false, at: q)
                        return w
                    }
                    let tubeCount = o.tube.count
                    let enter = arc - 0.5
                    if collect {
                        if enter > segStart { w.segments.append(.ray(segStart..<enter)) }
                        if e == 0 { w.cells.append(contentsOf: o.tube) } else { w.cells.append(contentsOf: o.tube.reversed()) }
                    }
                    arc += Double(tubeCount - 1)
                    let leave = arc + 0.5
                    if collect {
                        w.segments.append(.tube(o.id, enter..<leave))
                        w.pipes.append((k, enter, leave))
                    }
                    segStart = leave
                    let other = o.ends[1 - e]
                    p = other.cell
                    d = other.out
                    hops += 1
                    continue
                case .corner:
                    guard let t = o.turn, let nd = ObstacleRT.cornerTurn(t, d), hops < rules.pipe.maxHops else {
                        block(.obstacle(o.id), isArrow: false, at: q)
                        return w
                    }
                    hops += 1
                    if collect {
                        if arc > segStart { w.segments.append(.ray(segStart..<arc)) }
                        w.segments.append(.corner(o.id, at: arc))
                        w.corners.append((k, arc))
                        w.cells.append(q)
                    }
                    segStart = arc
                    p = q
                    d = nd
                    continue
                default:
                    block(.obstacle(o.id), isArrow: false, at: q)
                    return w
                }
            }
            let oc = occ[qi]
            if oc >= 0 && Int(oc) != i {
                if !unit.contains(Int(oc)) {
                    block(.arrow(ids[Int(oc)]), isArrow: true, at: q)
                    return w
                }
                if let more = extraOcc[qi], let other = more.first(where: { Int($0) != i && !unit.contains(Int($0)) }) {
                    block(.arrow(ids[Int(other)]), isArrow: true, at: q)
                    return w
                }
            }
            if collect { w.cells.append(q) }
            p = q
        }
    }
}
