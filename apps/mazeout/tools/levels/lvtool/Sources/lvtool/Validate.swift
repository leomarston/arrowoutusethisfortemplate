import Foundation
import PathCore

// `lvtool check <levels dir> [--publish] [--rules App/Resources/Tuning/rules.json] [--art art/ui/out] [--report FILE]`
//
// --publish (PUBLISH B0; SPEC.md ruling 39 OD8): the folder is the SHIPPED form (lvtool bundle --publish), so the
// provenance check is inverted: no level may carry a capture or a "_" note (was: every recorded / video level names an
// existing capture file — that check now runs on design/levels.json: `lvtool selftest`, validate_levels.py, PathCore C4).
//
// The SPEC-gameplay §14.4 validator list (design/tools/validate_levels.py, the reference), run in Swift on the BUNDLE
// through the app's own reader (LevelLibrary.load + loadAuthored) and C2's rules (BoardState, Solver.greedy,
// HeadlessDriver) with the SHIPPED rules.json:
//   per level: values, structure (C1's structuralProblems), obstacles well formed, the full self-ray (through pipes),
//   greedy-solved by C2's Solver.greedy, every obstacle used in that solution (each pipe passed, box broken, door opened,
//   elevator activated), no dead end in 40 seeded random orders on non-monotone boards, the HeadlessDriver wins at 0.6 s
//   per tap with ≥ 20 % of the timer left, `metrics` equal the recomputed values, the capture file exists.
//   across levels: 1…N contiguous (the library's authoredCount), LevelLibrary.problems empty, each unlock card exactly at
//   its feature's first appearance, sessions and tutorials point at real levels and visible arrows, no two boards equal.
// C4's `Validator` (not written yet) will be the app's; this is CONTENT's gate until then.

let featureOf: [ObstacleKind: String] = [.tape: "linked", .door: "door", .pipe: "pipe", .box: "box", .curtain: "box",
                                         .elevator: "elevator", .corner: "corner"]
let prefixOf: [ObstacleKind: String] = [.tape: "t", .door: "d", .key: "k", .pipe: "p", .box: "b", .curtain: "c",
                                        .elevator: "e", .corner: "x"]

struct TracedSolve {
    var solved: Bool
    var rounds: Int
    var order: [[ArrowID]]
    var freeAtStart: Int
    var stuck: Int
    var pipesPassed: [ObstacleID: Int] = [:]
    var boxesBroken: Set<ObstacleID> = []
    var doorsOpened: Set<ObstacleID> = []
    var elevatorsActivated: Set<ObstacleID> = []
    var keysDispatched = 0
}

/// C2's greedy (Solver.greedy's loop, rewritten on the public API so every RuleEvent is seen). Must agree with
/// Solver.greedy (checked).
func tracedGreedy(_ level: LevelSpec, rules: RulesTuning) -> TracedSolve {
    let b = BoardState(level: level, rules: rules)
    var t = TracedSolve(solved: false, rounds: 0, order: [], freeAtStart: -1, stuck: 0)
    func note(_ evs: [RuleEvent]) {
        for e in evs {
            switch e {
            case .pipeUsed(let p, _): t.pipesPassed[p, default: 0] += 1
            case .counterBroken(let o, _): t.boxesBroken.insert(o)
            case .doorOpened(let d, _): t.doorsOpened.insert(d)
            case .elevatorActivated(let e, _): t.elevatorsActivated.insert(e)
            case .keyDispatched: t.keysDispatched += 1
            default: break
            }
        }
    }
    while !b.isCleared {
        let free = b.freeUnits()
        if t.freeAtStart < 0 { t.freeAtStart = free.count }
        if free.isEmpty {
            let doors = b.targetedDoors
            if !doors.isEmpty { for d in doors { note(b.ack(.doorBurst(d))) }; continue }
            break
        }
        var removed = 0
        for u in free {
            let r = b.resolve(tap: u[0])
            guard case .exit(let plan) = r else { continue }
            note(b.commit(r))
            t.order.append(plan.unit)
            removed += 1
        }
        for d in b.targetedDoors { note(b.ack(.doorBurst(d))) }
        if removed == 0 { break }
        t.rounds += 1
    }
    t.freeAtStart = max(0, t.freeAtStart)
    t.solved = b.isCleared
    t.stuck = b.remaining
    return t
}

/// A random play order (any free unit, uniformly, PathRandom-seeded; doors burst right after the key's tap). Returns the
/// arrows left when it got stuck, or 0.
func randomOrderStuck(_ level: LevelSpec, rules: RulesTuning, rng: inout PathRandom) -> Int {
    let b = BoardState(level: level, rules: rules)
    while !b.isCleared {
        let free = b.freeUnits()
        if free.isEmpty {
            let doors = b.targetedDoors
            if doors.isEmpty { return b.remaining }
            for d in doors { b.ack(.doorBurst(d)) }
            continue
        }
        let u = free[rng.below(free.count)]
        b.commit(b.resolve(tap: u[0]))
        for d in b.targetedDoors { b.ack(.doorBurst(d)) }
    }
    return 0
}

func isRect(_ cells: [Cell]) -> Bool {
    let s = Set(cells)
    guard !s.isEmpty else { return false }
    let cs = s.map(\.c), rs = s.map(\.r)
    return s.count == (cs.max()! - cs.min()! + 1) * (rs.max()! - rs.min()! + 1)
}

/// The head's ray on the static board (doors / boxes open, every other arrow gone, pipes whole): does it meet the arrow's
/// own body, straight or after a pipe? (SPEC-architecture §4.4: "the ray of an arrow never meets its own body".)
func selfRayHitsOwnBody(_ a: ArrowSpec, _ l: LevelSpec) -> Bool {
    let g = l.grid
    var pipeAt: [Cell: Int] = [:]
    var mouth: [Cell: (Int, Dir)] = [:]
    var other: [String: (Cell, Dir)] = [:]
    for (k, o) in l.obstacles.enumerated() where o.kind == .pipe && o.ends.count == 2 {
        for c in o.cells { pipeAt[c] = k }
        mouth[o.ends[0].cell] = (k, o.ends[0].out)
        mouth[o.ends[1].cell] = (k, o.ends[1].out)
        other["\(k)|\(cellKey(o.ends[0].cell))"] = (o.ends[1].cell, o.ends[1].out)
        other["\(k)|\(cellKey(o.ends[1].cell))"] = (o.ends[0].cell, o.ends[0].out)
    }
    let own = Set(a.cells)
    var c = a.head, d = a.dir, hops = 0
    while true {
        let n = c + d
        guard g.inBounds(n) else { return false }
        if let p = pipeAt[n] {
            guard let m = mouth[n], m.0 == p, m.1 == d.opposite, let o = other["\(p)|\(cellKey(n))"] else { return false }
            hops += 1
            if hops > 16 { return false }
            (c, d) = o
            continue
        }
        if own.contains(n) { return true }
        c = n
    }
}

/// Can another arrow's ray reach a door stub (`out` = the hidden arrow's cells outside its shut door `door`)? As the reference
/// (validate_levels.py) and C4's Validator ask it, here on C2's own rules: every other door open, every box / curtain broken,
/// each arrow not hidden by `door` alone on the board (visible, layer 1), pipes and corners intact, `door` shut. Returns the
/// first arrow (id order) whose travelled cells (after its own body: the ray, tubes, corner turns, up to its blocker or the
/// grid edge) meet a stub cell, with those cells; nil = unreachable.
func stubReach(_ l: LevelSpec, rules: RulesTuning, door: ObstacleID, out: Set<Cell>) -> (ArrowID, [Cell])? {
    guard var shut = l.obstacles.first(where: { $0.id == door }) else { return nil }
    shut.reveals = []
    let keep = l.obstacles.filter { $0.kind == .pipe || $0.kind == .corner }
    for a in l.arrows.sorted(by: { $0.id.raw < $1.id.raw }) where a.hiddenBy != door {
        var one = a
        one.hiddenBy = nil
        one.layer = 1
        var s = l
        s.arrows = [one]
        s.obstacles = [shut] + keep
        s.unlock = nil
        s.metrics = nil
        let b = BoardState(level: s, rules: rules)
        var cells: [Cell] = []
        switch b.resolve(tap: one.id) {
        case .exit(let plan): cells = plan.paths[one.id]?.cells ?? []
        case .bump(let plan): cells = plan.path.cells
        default: break
        }
        let own = Set(one.cells)
        let hit = Set(cells.filter { !own.contains($0) }).intersection(out)
        if !hit.isEmpty { return (a.id, hit.sorted { ($0.c, $0.r) < ($1.c, $1.r) }) }
    }
    return nil
}

struct LevelCheck {
    var errors: [String] = []
    var warnings: [String] = []
    var row: [String: Any] = [:]
}

func checkLevel(_ l: LevelSpec, rules: RulesTuning, root: String, publish: Bool = false) -> LevelCheck {
    var r = LevelCheck()
    func E(_ s: String) { r.errors.append("L\(l.level): \(s)") }
    func W(_ s: String) { r.warnings.append("L\(l.level): \(s)") }

    // values + provenance
    if publish {
        if l.capture != nil { E("capture in the publish form") }
        // FIX-2 B (N-01): nor its source (decodes as .designed when absent) or metrics
        if l.source != .designed { E("source \(l.source.rawValue) in the publish form") }
        if l.metrics != nil { E("metrics in the publish form") }
    } else if l.source == .authored || l.source == .crafted {
        if let cap = l.capture {
            if !FileManager.default.fileExists(atPath: (root as NSString).appendingPathComponent(cap)) { E("capture \(cap) not found") }
        } else { E("no capture for a \(l.source.rawValue) level") }
    }
    // PUBLISH B0: the provenance findings above do not stop the board checks below (the early return is for a malformed
    // board). Before, a research frame missing on this disk (38 video frames are) skipped the solver on those levels, so
    // `lvtool selftest`'s L13 / L29 mutations were never really checked.
    let provenanceFindings = r.errors.count
    if !(60...600).contains(l.timerSeconds) { E("timer_s \(l.timerSeconds)") }
    if l.hearts != 3 { E("hearts \(l.hearts)") }
    if !(2...40).contains(l.cols) || !(2...40).contains(l.rows) { E("grid \(l.cols)x\(l.rows)") }
    if l.cols > 26 { W("cols \(l.cols) > 26: fit pitch below the 14.04 pt zoom floor") }
    if l.mask != nil { W("mask set (every shipped level has mask null)") }

    // structure (C1)
    for p in l.structuralProblems() { E(p) }

    // obstacles
    let A = Dictionary(l.arrows.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
    var O: [ObstacleID: ObstacleSpec] = [:]
    for o in l.obstacles {
        if O[o.id] != nil { E("duplicate obstacle id \(o.id.raw)") }
        if let p = prefixOf[o.kind], !o.id.raw.hasPrefix(p) { W("obstacle \(o.id.raw) id prefix vs kind \(o.kind.rawValue)") }
        O[o.id] = o
    }
    var visibleCells: [Cell: ArrowID] = [:]
    for a in l.arrows where a.hiddenBy == nil && a.layer == 1 { for c in a.cells { visibleCells[c] = a.id } }
    var hiderCells: [Cell: ObstacleID] = [:]
    let g = l.grid
    // F3-B (2026-09-29): the two door rules of SPEC-gameplay §3.5 / SPEC.md ruling 26 that C4's Validator and the reference
    // (design/tools/validate_levels.py) already had and this check lacked (it reported 40 errors on L58 / L59 / L99, whose
    // boards are the recorded v552 L62 / L69 / L89 as designed, and skipped their solve):
    //  (1) an obstacle lying WHOLLY inside a door is UNDER it (pipes under doors, L59; a corner under a door, L99): it may
    //      share that door's cells, nothing else's. C2's RayWalk lets the locked door block first. Doors are checked first so
    //      a door owns its cells whatever the order of the obstacle list. A partial overlap, two non-door hiders on one
    //      cell, or any hider on a visible arrow is still an error.
    //  (2) a door-hidden arrow may poke out of its door (the humps of L58's key arrow over the bottom door's frame) only onto
    //      cells no visible arrow or hider holds, and only where no other arrow's ray can reach them while that door is shut
    //      (`stubReach`, on C2's rules): the rules keep a hidden arrow inert, so a reachable stub would be drawn but passed
    //      through. A box / curtain arrow sticking out is still an error.
    var stubs: [(door: ObstacleID, arrow: ArrowID, out: Set<Cell>)] = []
    let doorSets: [(ObstacleID, Set<Cell>)] = l.obstacles.filter { $0.kind == .door }.map { ($0.id, Set($0.cells)) }
    var under: [ObstacleID: ObstacleID] = [:]
    for o in l.obstacles where [.box, .curtain, .pipe, .corner].contains(o.kind) {
        if let host = doorSets.first(where: { Set(o.cells).isSubset(of: $0.1) }) { under[o.id] = host.0 }
    }
    let doorsFirst = l.obstacles.filter { $0.kind == .door } + l.obstacles.filter { $0.kind != .door }
    var underCells: [Cell: ObstacleID] = [:]          // two obstacles under the same door may not share a cell either
    for o in doorsFirst {
        let cs = o.cells
        if [.door, .box, .curtain, .pipe, .corner, .elevator].contains(o.kind) {
            for c in cs {
                if !g.inBounds(c) { E("\(o.kind.rawValue) \(o.id.raw) cell \(c) outside the grid") }
                if o.kind != .elevator, let v = visibleCells[c] { E("\(o.kind.rawValue) \(o.id.raw) covers visible arrow \(v.raw) at \(c)") }
                if o.kind != .elevator {
                    if let h = hiderCells[c], under[o.id] != h { E("\(o.kind.rawValue) \(o.id.raw) overlaps \(h.raw) at \(c)") }
                    if hiderCells[c] == nil { hiderCells[c] = o.id }
                    if under[o.id] != nil {
                        if let u = underCells[c] { E("\(o.kind.rawValue) \(o.id.raw) overlaps \(u.raw) at \(c) (both under \(under[o.id]!.raw))") }
                        underCells[c] = o.id
                    }
                }
            }
        }
        switch o.kind {
        case .tape:
            if !(2...4).contains(o.arrows.count) { E("tape \(o.id.raw) binds \(o.arrows.count) arrows") }
            let ms = o.arrows.compactMap { A[$0] }
            guard ms.count == o.arrows.count else { E("tape \(o.id.raw): unknown member"); continue }
            if Set(ms.map(\.dir)).count != 1 || Set(ms.map(\.cells.count)).count != 1 {
                E("tape \(o.id.raw) members differ in direction or length")
            }
            for m in ms where zip(m.cells, m.cells.dropFirst()).contains(where: { Dir(from: $0, to: $1) != m.dir }) {
                E("tape \(o.id.raw) member \(m.id.raw) is not straight")
            }
            let ties = Set(ms.compactMap { $0.cells.count >= 2 ? $0.cells[$0.cells.count - 2] : nil })
            if cs.count != o.arrows.count || ties != Set(cs) { E("tape \(o.id.raw) tie cells are not each member's cell behind the head") }
            if Set(ms.map { $0.hiddenBy?.raw ?? "" }).count != 1 { E("tape \(o.id.raw) members hidden differently") }
        case .door, .box, .curtain:
            if !isRect(cs) { E("\(o.kind.rawValue) \(o.id.raw) is not a rectangle") }
            if o.kind == .door && cs.count < 4 { E("door \(o.id.raw) smaller than 2x2") }
            let hid = Set(l.arrows.filter { $0.hiddenBy == o.id }.map(\.id))
            if Set(o.reveals) != hid { E("\(o.kind.rawValue) \(o.id.raw) reveals \(o.reveals.map(\.raw).sorted()) != arrows hidden by it \(hid.map(\.raw).sorted())") }
            for h in hid.sorted(by: { $0.raw < $1.raw }) {
                let out = Set(A[h]!.cells).subtracting(cs)
                if out.isEmpty { continue }
                if o.kind == .door { stubs.append((o.id, h, out)) }                     // rule (2) above
                else { E("\(o.kind.rawValue) \(o.id.raw): hidden arrow \(h.raw) sticks out") }
            }
            if o.kind != .door {
                if let c = o.counter {
                    if c < 1 { E("\(o.kind.rawValue) \(o.id.raw) counter \(c)") }
                    if c >= l.arrows.count { E("\(o.kind.rawValue) \(o.id.raw) counter \(c) >= \(l.arrows.count) arrows (never breaks)") }
                } else { E("\(o.kind.rawValue) \(o.id.raw) has no counter") }
            }
        case .key:
            guard o.arrows.count == 1, let rider = A[o.arrows[0]] else { E("key \(o.id.raw) rider \(o.arrows.map(\.raw))"); continue }
            if cs.count != 2 || !Set(cs).isSubset(of: Set(rider.cells)) { E("key \(o.id.raw) cells \(cs) not on its rider") }
            if let op = o.opens, O[op] == nil && !l.obstacles.contains(where: { $0.id == op }) { E("key \(o.id.raw) opens unknown \(op.raw)") }
        case .pipe:
            guard o.ends.count == 2 else { E("pipe \(o.id.raw) has \(o.ends.count) ends"); continue }
            if zip(cs, cs.dropFirst()).contains(where: { Dir(from: $0, to: $1) == nil }) || Set(cs).count != cs.count || cs.count < 2 {
                E("pipe \(o.id.raw) cells are not an ordered 4-connected path")
            } else if [o.ends[0].cell, o.ends[1].cell] != [cs[0], cs[cs.count - 1]] {
                E("pipe \(o.id.raw) ends are not its extremities")
            } else if o.ends[0].out != Dir(from: cs[1], to: cs[0]) || o.ends[1].out != Dir(from: cs[cs.count - 2], to: cs[cs.count - 1]) {
                E("pipe \(o.id.raw) mouth directions do not continue the tube")
            }
            if let c = o.counter { if !(1...9).contains(c) { E("pipe \(o.id.raw) counter \(c)") } } else { E("pipe \(o.id.raw) has no counter") }
            if let at = o.counterAt, at.count == 2 {
                let dmin = cs.map { abs(at[0] - Double($0.c)) + abs(at[1] - Double($0.r)) }.min() ?? 99
                if dmin > 1.0 { E("pipe \(o.id.raw) counter_at \(at) not on the tube") }
            } else { E("pipe \(o.id.raw) counter_at missing") }
        case .elevator:
            if !isRect(cs) { E("elevator \(o.id.raw) is not a rectangle") }
            let inside = Set(cs)
            let plat = Set(l.arrows.filter { $0.layer == 1 && $0.hiddenBy == nil && Set($0.cells).isSubset(of: inside) }.map(\.id))
            if Set(o.arrows) != plat { E("elevator \(o.id.raw) platform \(o.arrows.map(\.raw).sorted()) != layer-1 arrows inside \(plat.map(\.raw).sorted())") }
            let l2 = Set(l.arrows.filter { $0.hiddenBy == o.id }.map(\.id))
            if Set(o.reveals) != l2 { E("elevator \(o.id.raw) reveals != its layer-2 arrows") }
            for h in l2 where A[h]!.layer != 2 { E("elevator \(o.id.raw): hidden arrow \(h.raw) not on layer 2") }
        case .corner:
            if cs.count != 1 || o.turn == nil { E("corner \(o.id.raw)") }
        }
    }
    let doors = l.obstacles.filter { $0.kind == .door }
    let keys = l.obstacles.filter { $0.kind == .key }
    if keys.count != doors.count { E("\(keys.count) keys for \(doors.count) doors") }
    if doors.map({ $0.order ?? -1 }).sorted() != Array(0..<doors.count) { E("door orders \(doors.map { $0.order ?? -1 }.sorted())") }
    for a in l.arrows { if let h = a.hiddenBy, O[h] == nil { E("arrow \(a.id.raw) hidden by unknown \(h.raw)") } }
    // rule (1): after the burst the door's arrows and the obstacle under it are live together, so none may share a cell
    for (oid, d) in under.sorted(by: { $0.key.raw < $1.key.raw }) {
        let cs = Set(O[oid]!.cells)
        for a in l.arrows where a.hiddenBy == d {
            if let c = a.cells.first(where: { cs.contains($0) }) { E("\(O[oid]!.kind.rawValue) \(oid.raw) under \(d.raw) shares \(c) with arrow \(a.id.raw) hidden by it") }
        }
    }
    for st in stubs {                                                                    // rule (2) above
        for c in st.out.sorted(by: { ($0.c, $0.r) < ($1.c, $1.r) }) where visibleCells[c] != nil || hiderCells[c] != nil {
            E("door \(st.door.raw): hidden arrow \(st.arrow.raw) pokes out onto an occupied cell \(c)")
        }
        if let (by, hit) = stubReach(l, rules: rules, door: st.door, out: st.out) {
            E("door \(st.door.raw): hidden arrow \(st.arrow.raw) pokes out at \(hit), which arrow \(by.raw)'s ray can reach")
        }
    }
    r.row["door_stubs"] = stubs.map { "\($0.door.raw):\($0.arrow.raw)x\($0.out.count)" }
    r.row["under_doors"] = under.keys.map(\.raw).sorted()
    if r.errors.count > provenanceFindings { return r }

    for a in l.arrows where selfRayHitsOwnBody(a, l) { E("arrow \(a.id.raw): its ray meets its own body (through a pipe)") }

    // C2's greedy: solved, equal to Solver.greedy, every obstacle used
    let t = tracedGreedy(l, rules: rules)
    let g2 = Solver.greedy(l, rules: rules)
    if g2.solved != t.solved || g2.rounds != t.rounds || g2.order != t.order { E("traced greedy differs from Solver.greedy (tool bug)") }
    r.row["greedy_solved"] = g2.solved
    r.row["rounds"] = g2.rounds
    r.row["free_at_start"] = g2.freeAtStart
    r.row["units"] = l.unitCount
    r.row["arrows"] = l.arrows.count
    if !g2.solved {
        E("C2's greedy solver is stuck with \(g2.stuck.count) arrows left")
        return r
    }
    for o in l.obstacles {
        switch o.kind {
        case .pipe where (t.pipesPassed[o.id] ?? 0) == 0: E("pipe \(o.id.raw) is never passed in the solution")
        case .box, .curtain: if !t.boxesBroken.contains(o.id) { E("box \(o.id.raw) never breaks in the solution") }
        case .door: if !t.doorsOpened.contains(o.id) { E("door \(o.id.raw) never opens") }
        case .elevator: if !t.elevatorsActivated.contains(o.id) { E("elevator \(o.id.raw) never activates") }
        default: break
        }
    }

    // no dead end on the non-monotone boards
    if l.obstacles.contains(where: { [.pipe, .elevator, .corner].contains($0.kind) }) {
        var rng = PathRandom(seed: UInt64(1000 + l.level))
        var stuckRuns = 0
        for _ in 0..<40 where randomOrderStuck(l, rules: rules, rng: &rng) > 0 { stuckRuns += 1 }
        r.row["random_orders_stuck"] = stuckRuns
        if stuckRuns > 0 { E("dead end: \(stuckRuns) of 40 random play orders get stuck") }
    }

    // the bot: C2's HeadlessDriver at 0.6 s per tap (solver strategy, modelled acks) keeps ≥ 20 % of the timer
    let drv = HeadlessDriver.play(level: l, rules: rules, config: DriverConfig(strategy: .solver, tapInterval: 0.6))
    r.row["driver_won"] = drv.won
    r.row["driver_time_left_s"] = (drv.remaining * 10).rounded() / 10
    r.row["driver_time_left_fraction"] = (drv.timeLeftFraction * 1000).rounded() / 1000
    r.row["driver_bumps"] = drv.bumps
    if !drv.won { E("HeadlessDriver did not win (phase \(drv.phase), stuck \(drv.stuck.count))") }
    else if drv.timeLeftFraction < 0.2 { E("HeadlessDriver won with only \(Int(drv.remaining)) s of \(l.timerSeconds) left") }
    if drv.bumps != 0 { E("HeadlessDriver (solver strategy, no mistakes) bumped \(drv.bumps) time(s)") }

    // metrics = recomputed
    let units = l.unitCount
    let cells = Set(l.arrows.flatMap { a in a.cells.map { "\(a.layer):\(cellKey($0))" } }).count
    let mean = Double(l.arrows.reduce(0) { $0 + $1.cells.count }) / Double(max(1, l.arrows.count))
    let botLeft = Double(l.timerSeconds) - (Double(units) * 0.6 + Double(doors.count) * 1.14)
    if let m = l.metrics {
        if m.rounds != g2.rounds { E("metrics.rounds \(m.rounds) != C2 greedy rounds \(g2.rounds)") }
        if m.freeAtStart != g2.freeAtStart { E("metrics.free_at_start \(m.freeAtStart) != \(g2.freeAtStart)") }
        if m.arrows != l.arrows.count { E("metrics.arrows \(m.arrows) != \(l.arrows.count)") }
        if m.cells != cells { E("metrics.cells \(m.cells) != \(cells)") }
        // the source rounds mean_length to 3 decimals (Python, half-even): 9.6875 is stored as 9.688
        if abs(m.meanLength - mean) > 0.0005 + 1e-9 { E("metrics.mean_length \(m.meanLength) != \(mean)") }
        if let b = m.botTimeLeft, abs(b - botLeft) > 0.05 + 1e-9 { E("metrics.bot_time_left \(b) != \(botLeft)") }
    } else if !publish { E("no metrics") }      // FIX-2 B (N-01): the publish form ships none (recomputed below)
    if botLeft < 0.2 * Double(l.timerSeconds) { E("bot formula keeps only \(Int(botLeft)) s of \(l.timerSeconds)") }
    return r
}

/// Heads (cell + dir) and every occupied cell: two boards with the same key are the same board.
func boardKey(_ l: LevelSpec) -> String {
    let heads = l.arrows.map { "\(cellKey($0.head))\($0.dir.rawValue)" }.sorted()
    let cells = Set(l.arrows.flatMap { $0.cells.map(cellKey) }).sorted()
    return heads.joined(separator: ";") + "|" + cells.joined(separator: ";")
}

func crossChecks(levels: [LevelSpec], lib: LevelLibrary) -> [String] {
    var errs: [String] = []
    let n = levels.count
    if levels.map(\.level) != Array(1...max(1, n)) { errs.append("levels are not 1…\(n)") }
    if lib.authoredCount != n { errs.append("LevelLibrary.authoredCount \(lib.authoredCount) != \(n)") }
    for p in lib.problems { errs.append("LevelLibrary: \(p)") }
    var first: [String: Int] = [:]
    for l in levels { for o in l.obstacles { if let f = featureOf[o.kind], first[f] == nil { first[f] = l.level } } }
    let unlocks = Dictionary(lib.unlocks.map { ($0.feature.rawValue, $0) }, uniquingKeysWith: { a, _ in a })
    if unlocks.count != lib.unlocks.count { errs.append("unlocks.json lists a feature twice") }
    for (f, lv) in first.sorted(by: { $0.value < $1.value }) {
        if levels[lv - 1].unlock?.rawValue != f { errs.append("L\(lv): first \(f) but unlock=\(levels[lv - 1].unlock?.rawValue ?? "nil")") }
        if unlocks[f]?.level != lv { errs.append("unlocks.json: \(f) should be at L\(lv) (\(unlocks[f]?.level.description ?? "missing"))") }
    }
    for l in levels { if let u = l.unlock, first[u.rawValue] != l.level { errs.append("L\(l.level): unlock \(u.rawValue) is not a first appearance") } }
    for u in lib.unlocks where first[u.feature.rawValue] == nil { errs.append("unlocks.json: \(u.feature.rawValue) never appears") }
    for s in lib.sessions { for lv in s.levels where !(1...n).contains(lv) { errs.append("session \(s.id) level \(lv)") } }
    for t in lib.tutorials {
        guard (1...n).contains(t.level) else { errs.append("tutorial \(t.id.rawValue) at level \(t.level)"); continue }
        let lv = levels[t.level - 1]
        let session = lib.session(containing: t.level)
        if let idx = session.levels.firstIndex(of: t.level), idx != t.stage {
            errs.append("tutorial \(t.id.rawValue): stage \(t.stage) but level \(t.level) is stage \(idx) of \(session.id)")
        }
        if let h = t.hand {
            guard let a = lv.arrows.first(where: { $0.id == h.arrow }) else { errs.append("tutorial \(t.id.rawValue) points at a missing arrow"); continue }
            if a.hiddenBy != nil || a.layer != 1 { errs.append("tutorial \(t.id.rawValue) points at a hidden arrow") }
        }
        if let allowed = t.allowedArrows { for x in allowed where !lv.arrows.contains(where: { $0.id == x }) { errs.append("tutorial \(t.id.rawValue) allows a missing arrow") } }
    }
    var seen: [String: Int] = [:]
    for l in levels {
        let k = boardKey(l)
        if let o = seen[k] { errs.append("L\(l.level) repeats L\(o)") }
        seen[k] = l.level
    }
    return errs
}

/// Art ids the bundled boards draw (the `pclevels needs` list, SPEC-architecture §4.14): tapes by orientation/lanes,
/// keys, locks, pipes, box rings, unlock icons. Doors and box slabs are code-drawn at any size (CONSISTENCY O-21/O-23).
func artNeeds(_ levels: [LevelSpec], _ lib: LevelLibrary) -> [String: [Int]] {
    var need: [String: Set<Int>] = [:]
    for l in levels {
        for o in l.obstacles {
            switch o.kind {
            case .tape:
                let dirs = o.arrows.compactMap { id in l.arrows.first { $0.id == id }?.dir }
                let horizontalArrows = dirs.first.map { $0 == .left || $0 == .right } ?? true
                need["tape\(horizontalArrows ? "V" : "H")\(o.arrows.count)", default: []].insert(l.level)
            case .key: need["keyOnArrow", default: []].insert(l.level)
            case .door: need["lockHex", default: []].insert(l.level); need["doorShards", default: []].insert(l.level)
            case .pipe: need["pipeMouth", default: []].insert(l.level); need["pipeCounter", default: []].insert(l.level)
            case .box, .curtain: need["boxRing", default: []].insert(l.level)
            default: break
            }
        }
    }
    for u in lib.unlocks { if let i = u.icon { need[i, default: []].insert(u.level) } }
    return need.mapValues { $0.sorted() }
}

func cmdCheck(_ a: Args) throws -> Int32 {
    guard a.positional.count == 1 else { throw ToolError("usage: lvtool check <levels dir> [--publish] [--rules F] [--art DIR] [--report F]") }
    let dir = a.positional[0]
    let publish = a.flags.contains("publish")
    let root = FileManager.default.currentDirectoryPath
    let (rules, rp) = try loadRules(a.opt("rules", "App/Resources/Tuning/rules.json"))
    let lib = try LevelLibrary.load(folder: URL(fileURLWithPath: dir))
    var levels: [LevelSpec] = []
    var errs: [String] = [], warns: [String] = []
    for p in rp { warns.append("rules.json: \(p)") }
    let files = lib.files.keys.sorted()
    for n in files {
        do { levels.append(try lib.loadAuthored(n)) } catch { errs.append("L\(n): does not decode: \(error)") }
        if let url = lib.files[n] {
            let data = try Data(contentsOf: url)
            let rep = try LevelJSON.inspectBundle(data)
            if !rep.unknownKeys.isEmpty { errs.append("L\(n): unknown keys \(rep.unknownKeys)") }
            if publish, let o = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                let notes = o.keys.filter { $0.hasPrefix("_") }.sorted()
                if !notes.isEmpty { errs.append("L\(n): comment keys \(notes) in the publish form") }
            }
        }
    }
    var rows: [[String: Any]] = []
    let t0 = Date()
    for l in levels {
        let r = checkLevel(l, rules: rules, root: root, publish: publish)
        errs += r.errors; warns += r.warnings
        var row = r.row
        row["level"] = l.level
        row["source"] = l.source.rawValue
        row["tag"] = l.tag.rawValue
        row["timer_s"] = l.timerSeconds
        row["ok"] = r.errors.isEmpty
        rows.append(row)
    }
    errs += crossChecks(levels: levels, lib: lib)
    let needs = artNeeds(levels, lib)
    let artDir = a.opt("art", "art/ui/out")
    var needRows: [[String: Any]] = []
    var missingArt: [String] = []
    for (id, lv) in needs.sorted(by: { $0.key < $1.key }) {
        let present = FileManager.default.fileExists(atPath: "\(artDir)/\(id)@3x.png")
        if !present { missingArt.append(id) }
        needRows.append(["id": id, "levels": lv, "present_in_\(artDir.replacingOccurrences(of: "/", with: "_"))": present])
    }
    let solvedCount = rows.filter { ($0["greedy_solved"] as? Bool) == true }.count
    let wonCount = rows.filter { ($0["driver_won"] as? Bool) == true }.count
    let report: [String: Any] = [
        "levels_dir": dir, "levels": levels.count, "authoredCount": lib.authoredCount,
        "rules": a.opt("rules", "App/Resources/Tuning/rules.json"),
        "rules_used": ["hit.radiusPt": rules.hit.radiusPt, "pipe.countAt": rules.pipe.countAt.rawValue,
                       "tape.blockedPolicy": rules.tape.blockedPolicy.rawValue, "box.countAt": rules.box.countAt.rawValue,
                       "elevator.emptyCellsBlock": rules.elevator.emptyCellsBlock],
        "errors": errs, "warnings": warns, "greedy_solved": solvedCount, "driver_won": wonCount,
        "sessions": lib.sessions.map(\.id), "unlocks": lib.unlocks.map { "\($0.feature.rawValue)@L\($0.level)" },
        "tutorials": lib.tutorials.map { "\($0.id.rawValue)@L\($0.level)/stage\($0.stage)" },
        "art_needs": needRows, "art_missing": missingArt, "table": rows,
        "seconds": (Date().timeIntervalSince(t0) * 10).rounded() / 10,
    ]
    if let rp = a.options["report"] { try writeData(try reportJSON(report), rp) }
    print("check: \(levels.count) levels decoded by LevelLibrary (authoredCount \(lib.authoredCount)); C2 greedy solved \(solvedCount)/\(levels.count); HeadlessDriver won \(wonCount)/\(levels.count); \(errs.count) error(s), \(warns.count) warning(s)")
    for e in errs.prefix(60) { print("ERROR \(e)") }
    for w in warns.prefix(20) { print("WARN  \(w)") }
    print("art needs: \(needs.count) ids; missing in \(artDir): \(missingArt.isEmpty ? "none" : missingArt.joined(separator: ", "))")
    return errs.isEmpty ? 0 : 1
}
