// Debug harness: compiled into Debug and Measure only (`#if DEBUG || PC_MEASURE`), never into the Release (store) build.
// tools/harness_gate.py (CI) fails when a harness type is used outside that gate.
#if DEBUG || PC_MEASURE
import Foundation
import PathCore

// B1 (SPEC-architecture §5.12 BoardLab, §5.9 warm-up). BoardLab's stand-in rules: the spike's Board.swift (flat Int32
// occupancy, the ray walk to the grid edge, tape bundles) producing the ◆ plan types (ExitPlan, BumpPlan) and the ◆
// SessionEvent stream the real engine consumes. It exists so the board can be driven and measured before C2's
// BoardState / LevelSession land; it is NOT the game's rules: only arrows and tapes (doors, pipes, boxes, elevators and
// corners are ignored, B2 extends the lab), no timer, no fail chain. GAME never uses it.

@MainActor final class LabRules {
    let level: LevelSpec
    private let cols: Int
    private let rows: Int
    private var occ: [Int32]
    private var alive: [Bool]
    private var index: [ArrowID: Int] = [:]
    private var tapeMembers: [ObstacleID: [Int]] = [:]
    private var tapeOf: [Int: ObstacleID] = [:]
    private var tapeAlive: Set<ObstacleID> = []
    private(set) var hearts: Int
    private(set) var marked: Set<ArrowID> = []
    private(set) var bumping: Set<ArrowID> = []
    private(set) var exits = 0
    private(set) var bumps = 0
    private(set) var liveCount: Int
    private(set) var combo = 0
    private var lastTap: Double = -10
    var comboWindow = 1.25                             // INFERRED motion §3.4

    init(level: LevelSpec) {
        self.level = level
        cols = level.cols
        rows = level.rows
        occ = [Int32](repeating: -1, count: max(1, level.cols * level.rows))
        alive = [Bool](repeating: true, count: level.arrows.count)
        liveCount = level.arrows.count
        hearts = level.hearts
        for (i, a) in level.arrows.enumerated() {
            index[a.id] = i
            if a.hiddenBy != nil || a.layer > 1 { alive[i] = false; liveCount -= 1; continue }
            for c in a.cells where inGrid(c) { occ[c.r * cols + c.c] = Int32(i) }
        }
        for o in level.obstacles where o.kind == .tape {
            let members = o.arrows.compactMap { index[$0] }
            guard members.count > 1 else { continue }
            tapeMembers[o.id] = members
            tapeAlive.insert(o.id)
            for m in members { tapeOf[m] = o.id }
        }
    }

    func inGrid(_ c: Cell) -> Bool { c.c >= 0 && c.r >= 0 && c.c < cols && c.r < rows }

    func isAlive(_ id: ArrowID) -> Bool { index[id].map { alive[$0] } ?? false }

    /// The first live occupant on the ray and the empty cells before it; nil = the ray is clear.
    func firstBlocker(_ i: Int) -> (blocker: Int, gap: Int, ray: [Cell])? {
        let a = level.arrows[i]
        var p = headCell(a) + a.dir
        var gap = 0
        var ray: [Cell] = []
        while inGrid(p) {
            let v = occ[p.r * cols + p.c]
            if v >= 0 && Int(v) != i { return (Int(v), gap, ray) }
            ray.append(p)
            gap += 1
            p = p + a.dir
        }
        return nil
    }

    func rayCells(_ i: Int) -> [Cell] {
        let a = level.arrows[i]
        var out: [Cell] = []
        var p = headCell(a) + a.dir
        while inGrid(p) { out.append(p); p = p + a.dir }
        return out
    }

    func unit(_ id: ArrowID) -> [ArrowID] {
        guard let i = index[id] else { return [id] }
        if let t = tapeOf[i], tapeAlive.contains(t), let m = tapeMembers[t] { return m.map { level.arrows[$0].id } }
        return [id]
    }

    func isFree(_ id: ArrowID) -> Bool {
        guard let i = index[id], alive[i] else { return false }
        return firstBlocker(i) == nil
    }

    func unitFree(_ id: ArrowID) -> Bool { unit(id).allSatisfy { isFree($0) } }

    /// Live arrows whose whole unit is free.
    func freeArrows() -> [ArrowID] {
        level.arrows.indices.filter { alive[$0] && !bumping.contains(level.arrows[$0].id) && unitFree(level.arrows[$0].id) }
            .map { level.arrows[$0].id }
    }

    /// Live arrows that would bump (with their gap).
    func blockedArrows() -> [(ArrowID, Int)] {
        level.arrows.indices.compactMap { i in
            guard alive[i], let b = firstBlocker(i) else { return nil }
            return (level.arrows[i].id, b.gap)
        }
    }

    func resolve(_ id: ArrowID) -> TapResolution {
        guard let i = index[id] else { return .ignored(.noArrow) }
        guard alive[i] else { return .ignored(.moving) }
        if bumping.contains(id) { return .ignored(.bumping) }
        let members = unit(id)
        let memberIdx = members.compactMap { index[$0] }
        // a bundle leaves only when every member's ray is clear; else the first blocked member bumps (lab choice;
        // the game's rule is PENDING-gameplay)
        let stuck = memberIdx.first { firstBlocker($0) != nil }
        if let s = stuck, let b = firstBlocker(s) {
            let a = level.arrows[s]
            let contact = Double(b.gap + 1) - Metrics.headApexPast(a.dir) - Metrics.stroke / 2
            let path = ExitPath(cells: a.cells + b.ray, segments: [.body(-Double(a.cells.count - 1)..<0),
                                                                   .ray(0..<Double(b.gap))], toGridEdge: 0)
            return .bump(BumpPlan(arrow: a.id, blocker: .arrow(level.arrows[b.blocker].id), gapCells: b.gap, path: path,
                                  contactCells: max(0.05, contact), contactPoint: headCell(a).moved(a.dir, by: b.gap + 1)))
        }
        var paths: [ArrowID: ExitPath] = [:]
        for m in memberIdx {
            let a = level.arrows[m]
            let ray = rayCells(m)
            paths[a.id] = ExitPath(cells: a.cells + ray,
                                   segments: [.body(-Double(a.cells.count - 1)..<0), .ray(0..<(Double(ray.count) + 0.5))],
                                   toGridEdge: Double(ray.count) + 0.5)
        }
        let tape = tapeOf[i].flatMap { tapeAlive.contains($0) ? $0 : nil }
        return .exit(ExitPlan(tapped: id, unit: members, tape: members.count > 1 ? tape : nil, paths: paths, combo: max(1, combo)))
    }

    /// A tap (nil = empty board point): resolve + commit; returns the events in causal order.
    func tap(_ id: ArrowID?, at t: Double) -> [SessionEvent] {
        guard let id else { return [.tapIgnored(nil, .noArrow)] }
        switch resolve(id) {
        case .ignored(let r):
            return [.tapIgnored(id, r)]
        case .bump(let plan):
            bumping.insert(plan.arrow)
            bumps += 1
            combo = 0
            lastTap = t
            return [.bumped(plan)]
        case .exit(var plan):
            combo = (t - lastTap <= comboWindow) ? combo + 1 : 1
            lastTap = t
            plan.combo = combo
            for m in plan.unit { remove(m) }
            if let tp = plan.tape { tapeAlive.remove(tp) }
            exits += plan.unit.count
            return [.exited(plan)]
        }
    }

    /// The board's contact ack: the heart and the mark (the session's §8.3 behaviour).
    func contact(_ id: ArrowID) -> [SessionEvent] {
        hearts = max(0, hearts - 1)
        marked.insert(id)
        return [.heartLost(remaining: hearts), .arrowMarked(id)]
    }

    func bumpFinished(_ id: ArrowID) { bumping.remove(id) }

    private func remove(_ id: ArrowID) {
        guard let i = index[id], alive[i] else { return }
        alive[i] = false
        liveCount -= 1
        for c in level.arrows[i].cells where inGrid(c) && occ[c.r * cols + c.c] == Int32(i) { occ[c.r * cols + c.c] = -1 }
    }

    /// Greedy rounds on a copy: every unit free at the start of a round leaves (the spike's solver; exact for these
    /// monotone lab boards). Returns one tap per unit, in order.
    func greedyOrder() -> [ArrowID] {
        let copy = LabRules(level: level)
        var order: [ArrowID] = []
        while copy.liveCount > 0 {
            let free = copy.freeArrows()
            if free.isEmpty { break }
            var taken = Set<ArrowID>()
            for a in free where copy.isAlive(a) && !taken.contains(a) {
                let u = copy.unit(a)
                guard copy.unitFree(a) else { continue }
                u.forEach { taken.insert($0) }
                order.append(a)
                _ = copy.tap(a, at: 0)
            }
        }
        return order
    }
}
#endif
