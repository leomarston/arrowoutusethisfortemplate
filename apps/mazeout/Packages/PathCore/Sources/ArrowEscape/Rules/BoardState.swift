import Foundation
import GameCore

// C2 (SPEC-architecture §4.4). The logical board of one stage: flat Int32 occupancy (the spike's layout), per-arrow
// alive / visible / bumping / marked flags, tape units and the obstacles' state. `resolve` is pure; `commit` applies a
// resolution at the TAP (an arrow leaves the blocking grid when it is tapped, VERIFIED motion.md §3.1 P02); `ack` applies
// the presentation-timed facts the board reports (bump contact, bump finished, door burst). Used on the main actor by the
// app and freely by tests, the solver and the generator (on copies). Deterministic: no clocks, no randomness.

public final class BoardState {
    public let level: LevelSpec
    public let rules: RulesTuning
    public let grid: Grid

    // arrows (index = position in level.arrows)
    let ids: [ArrowID]
    let index: [ArrowID: Int]
    var alive: [Bool]             // not exited (live or hidden)
    var visible: [Bool]           // revealed (not under a door / box / curtain / inactive elevator layer)
    var bumping: [Bool]
    var marked: [Bool]
    var aliveCount: Int
    /// Flat occupancy of LIVE arrows (−1 empty); `extraOcc` holds a second live arrow on the same cell (layers).
    var occ: [Int32]
    var extraOcc: [Int: [Int32]] = [:]
    /// arrow → its tape obstacle index (−1 none).
    var tapeOf: [Int32]

    // obstacles
    var obs: [ObstacleRT]
    let obsIndex: [ObstacleID: Int]
    /// Blocking obstacle per cell (−1 none); `extraObs` for a second one on the same cell.
    var obsCell: [Int32]
    var extraObs: [Int: [Int32]] = [:]
    /// keys riding each arrow (arrow index → key obstacle indices).
    let keysOn: [Int: [Int]]

    /// Pending bumps: bumping arrow (the plan's arrow) → every arrow that moves with it, whether all were red already,
    /// and whether the contact was acked (one contact per bump).
    var pendingBumps: [Int: (members: [Int], repeat: Bool, contacted: Bool)] = [:]

    public init(level: LevelSpec, rules: RulesTuning = .default) {
        self.level = level
        self.rules = rules
        let g = level.grid
        grid = g
        let n = level.arrows.count
        ids = level.arrows.map(\.id)
        var idx: [ArrowID: Int] = [:]
        for (i, a) in level.arrows.enumerated() where idx[a.id] == nil { idx[a.id] = i }
        index = idx
        alive = [Bool](repeating: true, count: n)
        visible = level.arrows.map { $0.hiddenBy == nil }
        bumping = [Bool](repeating: false, count: n)
        marked = [Bool](repeating: false, count: n)
        aliveCount = n
        occ = [Int32](repeating: -1, count: max(1, g.count))
        tapeOf = [Int32](repeating: -1, count: n)

        var oi: [ObstacleID: Int] = [:]
        var list: [ObstacleRT] = []
        var keys: [Int: [Int]] = [:]
        for (k, o) in level.obstacles.enumerated() {
            if oi[o.id] == nil { oi[o.id] = k }
            let memberIdx = o.arrows.compactMap { idx[$0] }
            var hidden = Set(o.reveals.compactMap { idx[$0] })
            for (i, a) in level.arrows.enumerated() where a.hiddenBy == o.id { hidden.insert(i) }
            var tube: [Cell] = [], ends: [PipeEnd] = []
            if o.kind == .pipe { (tube, ends) = ObstacleRT.orderedTube(cells: o.cells, ends: o.ends) }
            let rt = ObstacleRT(id: o.id, kind: o.kind, cells: o.cells, counter: o.counter,
                                order: o.order ?? Int.max, opens: o.opens,
                                rider: o.kind == .key ? memberIdx.first : nil, members: memberIdx,
                                reveals: hidden.sorted(), tube: tube, ends: ends, turn: o.turn)
            if o.kind == .key, let r = rt.rider { keys[r, default: []].append(k) }
            list.append(rt)
        }
        // A counter kind with no counter: unlimited (the default) or broken at once.
        for k in list.indices where list[k].counter == nil {
            if list[k].kind == .pipe && !rules.pipe.missingCounterIsUnlimited { list[k].counter = 1 }
            if list[k].isCounterKind && !rules.box.missingCounterIsUnlimited { list[k].counter = 1 }
        }
        obs = list
        obsIndex = oi
        keysOn = keys
        obsCell = [Int32](repeating: -1, count: max(1, g.count))

        for (k, o) in obs.enumerated() {
            if o.kind == .tape { for m in o.members where tapeOf[m] < 0 { tapeOf[m] = Int32(k) } }
            let hides: Set<ObstacleKind> = [.door, .box, .curtain, .elevator]
            if hides.contains(o.kind) && !o.done { for r in o.reveals { visible[r] = false } }
            if o.blocksNow { for c in o.cells where g.inBounds(c) { addObstacle(Int32(k), at: g.index(c)) } }
        }
        for i in 0..<n where visible[i] { occupy(i) }
    }

    /// A deep copy (the solver and the generator explore on copies).
    public func copy() -> BoardState { BoardState(copying: self) }

    init(copying s: BoardState) {
        level = s.level; rules = s.rules; grid = s.grid; ids = s.ids; index = s.index
        alive = s.alive; visible = s.visible; bumping = s.bumping; marked = s.marked; aliveCount = s.aliveCount
        occ = s.occ; extraOcc = s.extraOcc; tapeOf = s.tapeOf
        obs = s.obs; obsIndex = s.obsIndex; obsCell = s.obsCell; extraObs = s.extraObs; keysOn = s.keysOn
        pendingBumps = s.pendingBumps
    }

    // MARK: public queries

    /// Tappable now: alive and revealed (bumping arrows included: they are on the board).
    public var live: [ArrowID] { (0..<ids.count).filter { alive[$0] && visible[$0] }.map { ids[$0] }.sorted() }
    /// Alive but not yet revealed (under a door / box / curtain / an inactive elevator layer).
    public var hidden: [ArrowID] { (0..<ids.count).filter { alive[$0] && !visible[$0] }.map { ids[$0] }.sorted() }
    /// No live and no hidden arrow left.
    public var isCleared: Bool { aliveCount == 0 }
    /// Arrows not yet exited (live + hidden).
    public var remaining: Int { aliveCount }

    /// The live arrow on `cell` (nil = empty, hidden, exited or outside).
    public func owner(of cell: Cell) -> ArrowID? {
        guard grid.inBounds(cell) else { return nil }
        let o = occ[grid.index(cell)]
        return o >= 0 ? ids[Int(o)] : nil
    }

    public func isAlive(_ a: ArrowID) -> Bool { index[a].map { alive[$0] } ?? false }
    public func isLive(_ a: ArrowID) -> Bool { index[a].map { alive[$0] && visible[$0] } ?? false }
    public func isMarked(_ a: ArrowID) -> Bool { index[a].map { marked[$0] } ?? false }
    public func isBumping(_ a: ArrowID) -> Bool { index[a].map { bumping[$0] } ?? false }
    /// Red arrows (bumped this level).
    public var markedArrows: [ArrowID] { (0..<ids.count).filter { marked[$0] }.map { ids[$0] }.sorted() }

    /// The unit a tap on `a` would move: its live tape bundle, or [a]; sorted.
    public func unit(of a: ArrowID) -> [ArrowID] {
        guard let i = index[a] else { return [] }
        return unitIndices(i).map { ids[$0] }.sorted()
    }

    /// Pipe / box / curtain counters still standing (nil counters omitted), by obstacle id.
    public var counters: [ObstacleID: Int] {
        var out: [ObstacleID: Int] = [:]
        for o in obs where (o.kind == .pipe || o.isCounterKind) && !o.done { if let c = o.counter { out[o.id] = c } }
        return out
    }

    public func doorState(_ d: ObstacleID) -> DoorState? {
        guard let k = obsIndex[d], obs[k].kind == .door else { return nil }
        return obs[k].door
    }

    /// Pipe / box / curtain broken, tape gone, key used, elevator activated.
    public func isDone(_ o: ObstacleID) -> Bool { obsIndex[o].map { obs[$0].done } ?? false }

    /// Every unit whose tap would EXIT now (sorted members; bumping units excluded), ordered by first member id.
    public func freeUnits() -> [[ArrowID]] {
        var out: [[ArrowID]] = []
        var seenTape = Set<Int32>()
        for i in 0..<ids.count where alive[i] && visible[i] && !bumping[i] {
            let t = tapeOf[i]
            if t >= 0 && !obs[Int(t)].done {
                if seenTape.contains(t) { continue }
                seenTape.insert(t)
            }
            let u = unitIndices(i)
            if u.contains(where: { bumping[$0] }) { continue }
            if u.allSatisfy({ isClear($0, unit: u) }) { out.append(u.map { ids[$0] }.sorted()) }
        }
        return out.sorted { $0[0] < $1[0] }
    }

    /// Whether a tap on `a` would exit now (no plan is built).
    public func isFree(_ a: ArrowID) -> Bool {
        guard let i = index[a], alive[i], visible[i], !bumping[i] else { return false }
        let u = unitIndices(i)
        if u.contains(where: { bumping[$0] }) { return false }
        return u.allSatisfy { isClear($0, unit: u) }
    }

    // MARK: commit (at the tap)

    /// Applies a resolution returned by `resolve(tap:)` on this state: an exit removes its unit from the blocking grid,
    /// dispatches keys, consumes pipes, ticks every box / curtain, activates an emptied elevator; a bump only marks the
    /// unit as bumping (the heart and the red mark come with the contact ack). Returns the logical events in order.
    @discardableResult
    public func commit(_ r: TapResolution) -> [RuleEvent] {
        switch r {
        case .ignored: return []
        case .bump(let plan): return commitBump(plan)
        case .exit(let plan): return commitExit(plan)
        }
    }

    func commitBump(_ plan: BumpPlan) -> [RuleEvent] {
        guard let a = index[plan.arrow] else { return [] }
        var members = [a]
        if rules.tape.blockedPolicy == .bundleBumps { members = unitIndices(a) }
        for m in members { bumping[m] = true }
        pendingBumps[a] = (members, members.allSatisfy { marked[$0] }, false)
        return []
    }

    func commitExit(_ plan: ExitPlan) -> [RuleEvent] {
        var events: [RuleEvent] = []
        let unit = plan.unit.compactMap { index[$0] }.filter { alive[$0] }
        guard !unit.isEmpty else { return [] }
        // 1. the unit leaves the blocking grid
        for i in unit {
            vacate(i)
            alive[i] = false
            bumping[i] = false
            aliveCount -= 1
            let t = tapeOf[i]
            if t >= 0 { obs[Int(t)].done = true }
        }
        // 2. keys (from the plan's beats, in order)
        for b in plan.beats {
            guard case let .keyReleased(key, door, _) = b, let k = obsIndex[key], let d = obsIndex[door] else { continue }
            obs[k].done = true
            if obs[d].door == .locked { obs[d].door = .targeted }
            events.append(.keyDispatched(key: key, door: door))
        }
        // keys riding the unit with no door left simply leave with their arrow
        for i in unit { for k in keysOn[i] ?? [] where !obs[k].done { obs[k].done = true } }
        // 3. pipes: one passage per .enterTube beat
        var passes: [Int: Int] = [:]
        var pipeOrder: [Int] = []
        for b in plan.beats {
            guard case let .enterTube(p, _, _) = b, let k = obsIndex[p] else { continue }
            if passes[k] == nil { pipeOrder.append(k) }
            passes[k, default: 0] += 1
        }
        for k in pipeOrder where !obs[k].done {
            guard let c = obs[k].counter else { continue }                 // unlimited: no counter to show
            let left = max(0, c - passes[k, default: 0])
            obs[k].counter = left
            events.append(.pipeUsed(obs[k].id, remaining: left))
            if left == 0 { breakObstacle(k); events.append(.pipeBroken(obs[k].id)) }
        }
        // 4. boxes / curtains: every arrow cleared anywhere
        for k in obs.indices where obs[k].isCounterKind && !obs[k].done {
            guard let c = obs[k].counter else { continue }
            let left = max(0, c - unit.count)
            obs[k].counter = left
            events.append(.counterChanged(obs[k].id, remaining: left))
            if left == 0 {
                let revealed = breakObstacle(k)
                events.append(.counterBroken(obs[k].id, revealed: revealed))
            }
        }
        // 5. an elevator whose platform is now empty activates
        for k in obs.indices where obs[k].kind == .elevator && !obs[k].done {
            guard !obs[k].members.isEmpty, obs[k].members.allSatisfy({ !alive[$0] }) else { continue }
            let revealed = breakObstacle(k)
            events.append(.elevatorActivated(obs[k].id, revealed: revealed))
        }
        return events
    }

    // MARK: acks (presentation-timed)

    @discardableResult
    public func ack(_ a: RuleAck) -> [RuleEvent] {
        switch a {
        case .bumpContact(let id):
            guard let i = index[id], let pb = pendingBumps[i], !pb.contacted else { return [] }
            pendingBumps[i]?.contacted = true
            var out: [RuleEvent] = [.bumpContact(id, repeat: pb.repeat)]
            for m in pb.members where !marked[m] {
                marked[m] = true
                out.append(.arrowMarked(ids[m]))
            }
            return out
        case .bumpFinished(let id):
            guard let i = index[id] else { return [] }
            if let pb = pendingBumps.removeValue(forKey: i) {
                for m in pb.members { bumping[m] = false }
            } else {
                bumping[i] = false
            }
            return []
        case .doorBurst(let d):
            guard let k = obsIndex[d], obs[k].kind == .door, obs[k].door != .open else { return [] }
            obs[k].door = .open
            let revealed = breakObstacle(k)
            return [.doorOpened(d, revealed: revealed)]
        }
    }

    // MARK: internals

    /// Tape members that are still on the board, or the arrow alone.
    func unitIndices(_ i: Int) -> [Int] {
        let t = tapeOf[i]
        guard t >= 0, !obs[Int(t)].done else { return [i] }
        let m = obs[Int(t)].members.filter { alive[$0] && visible[$0] }
        return m.contains(i) ? m : [i]
    }

    /// Clears an obstacle's cells from the blocking grid and reveals its hidden arrows (door open, pipe / box broken,
    /// elevator activated). Returns the revealed arrow ids.
    @discardableResult
    func breakObstacle(_ k: Int) -> [ArrowID] {
        obs[k].done = true
        for c in obs[k].cells where grid.inBounds(c) { removeObstacle(Int32(k), at: grid.index(c)) }
        var revealed: [ArrowID] = []
        for r in obs[k].reveals where alive[r] && !visible[r] {
            visible[r] = true
            occupy(r)
            revealed.append(ids[r])
        }
        return revealed.sorted()
    }

    func occupy(_ i: Int) {
        for c in level.arrows[i].cells where grid.inBounds(c) {
            let k = grid.index(c)
            if occ[k] < 0 { occ[k] = Int32(i) } else if occ[k] != Int32(i) { extraOcc[k, default: []].append(Int32(i)) }
        }
    }

    func vacate(_ i: Int) {
        for c in level.arrows[i].cells where grid.inBounds(c) {
            let k = grid.index(c)
            if occ[k] == Int32(i) {
                if var more = extraOcc[k], !more.isEmpty {
                    occ[k] = more.removeFirst()
                    extraOcc[k] = more.isEmpty ? nil : more
                } else { occ[k] = -1 }
            } else if var more = extraOcc[k] {
                more.removeAll { $0 == Int32(i) }
                extraOcc[k] = more.isEmpty ? nil : more
            }
        }
    }

    func addObstacle(_ k: Int32, at cell: Int) {
        if obsCell[cell] < 0 { obsCell[cell] = k } else if obsCell[cell] != k { extraObs[cell, default: []].append(k) }
    }

    func removeObstacle(_ k: Int32, at cell: Int) {
        if obsCell[cell] == k {
            if var more = extraObs[cell], !more.isEmpty {
                obsCell[cell] = more.removeFirst()
                extraObs[cell] = more.isEmpty ? nil : more
            } else { obsCell[cell] = -1 }
        } else if var more = extraObs[cell] {
            more.removeAll { $0 == k }
            extraObs[cell] = more.isEmpty ? nil : more
        }
    }
}
