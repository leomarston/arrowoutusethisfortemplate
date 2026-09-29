import Foundation

// C4 (SPEC-architecture §4.14; SPEC-gameplay §3, §14.3, §14.4). The content tools' board rules: a line-for-line Swift
// mirror of design/tools/arrowcore.py (Board, greedy, dfs, waves, metrics, structural_problems). The generator and the
// validator decide with THESE functions so that `Generator` reproduces design/levels.json byte for byte and `Validator`
// returns the Python validator's verdicts. The game itself plays by C2's `BoardState`; the Validator also runs C2's
// greedy and the HeadlessDriver on every level, so a disagreement between the two rule books cannot pass unnoticed.
//
// Faithfulness notes (each mirrors the Python exactly, including its orders):
// - arrows are indexed by ascending id (Python's `sorted(self.alive)`), obstacles in list order (the `O` dict);
// - a unit is the tape's ALIVE members (hidden ones included), sorted; units come in ascending first-member order;
// - the walk checks a locked door → pipe → corner → door/box → live arrow (layer 1, then 2; the unit ignored) → the
//   arrow's own body (recast 2026-09-25, v552 L69: an obstacle UNDER a locked door is inert until the door opens);
// - one pipe passage = −1 in walk order; 0 breaks; boxes lose one per arrow cleared (tape members each);
// - keys go to `opens` (if still closed and not targeted) else the lowest (order, id) door neither open nor targeted;
//   a targeted door opens before the next tap (`openPendingDoors`);
// - an elevator activates when every platform arrow has left.

/// Constants of the reference rules (arrowcore.py).
public enum ContentRules {
    /// HeadlessDriver human pace (SPEC-architecture §4.15).
    public static let tapSeconds = 0.6
    /// key tap → door burst (VERIFIED motion §5.2).
    public static let doorSeconds = 1.14
    /// pipe / corner loop guard (rules.json pipe.maxHops).
    public static let maxHops = 16
}

/// The immutable tables of one level (arrowcore `Board.S`).
final class RefStatic {
    let level: LevelSpec
    let cols: Int
    let rows: Int
    /// Arrow index = rank of its id (ascending).
    let n: Int
    let ids: [ArrowID]
    let arrowCells: [[Cell]]
    let head: [Cell]
    let dir: [Dir]
    let layer: [Int]
    let hiddenAtStart: [Bool]
    /// The arrow shares a cell of its layer with another one (invalid content): the own-body test falls back to a scan.
    let overlapped: [Bool]
    /// Occupancy per layer (1, 2): flat cell → arrow index (−1).
    let occ1: [Int32]
    let occ2: [Int32]
    // obstacles (list order)
    let obs: [ObstacleSpec]
    let obsIndex: [ObstacleID: Int]
    /// arrow → tape obstacle index (−1).
    let tapeOf: [Int]
    /// tape obstacle index → member arrow indices.
    let tapeMembers: [Int: [Int]]
    /// arrow → key obstacle indices (obstacle order).
    let keysOn: [[Int]]
    let doorCell: [Int32]
    let boxCell: [Int32]
    let pipeCell: [Int32]
    /// flat cell → (pipe index, out) of a mouth.
    let pipeEndPipe: [Int32]
    let pipeEndOut: [Dir?]
    /// pipe index → its two ends (cell, out) in `ends` order.
    let pipeEnds: [Int: [(Cell, Dir)]]
    let cornerCell: [Int32]
    /// elevator obstacle indices (obstacle order) and their platform arrow indices.
    let elevators: [(k: Int, platform: [Int], platformIDs: Set<ArrowID>)]
    let doors: [Int]
    let boxKinds: [Int]
    let pipes: [Int]
    /// obstacle index → arrow indices it reveals (`reveals`, unknown ids dropped).
    let reveals: [[Int]]

    init(_ l: LevelSpec) {
        level = l
        cols = l.cols
        rows = l.rows
        // Python's A dict: one entry per id (the last arrow wins its values, at the first position — irrelevant here
        // because valid content has unique ids; the validator reports duplicates before any board is built).
        var byID: [ArrowID: ArrowSpec] = [:]
        for a in l.arrows { byID[a.id] = a }
        let sortedIDs = byID.keys.sorted()
        n = sortedIDs.count
        ids = sortedIDs
        var idx: [ArrowID: Int] = [:]
        for (i, id) in sortedIDs.enumerated() { idx[id] = i }
        let arrows = sortedIDs.map { byID[$0]! }
        arrowCells = arrows.map(\.cells)
        head = arrows.map { $0.cells.last ?? Cell(0, 0) }
        dir = arrows.map(\.dir)
        layer = arrows.map { $0.layer == 2 ? 2 : 1 }
        hiddenAtStart = arrows.map { $0.hiddenBy != nil }
        let size = max(1, cols * rows)
        var o1 = [Int32](repeating: -1, count: size), o2 = o1
        var over = [Bool](repeating: false, count: n)
        // occupancy in the level's LIST order (Python: `for aid, a in A.items()`, later arrows overwrite)
        var listOrder: [Int] = []
        var seen = Set<ArrowID>()
        for a in l.arrows where seen.insert(a.id).inserted { listOrder.append(idx[a.id]!) }
        for i in listOrder {
            for c in arrowCells[i] where c.c >= 0 && c.r >= 0 && c.c < cols && c.r < rows {
                let k = c.r * cols + c.c
                if layer[i] == 1 {
                    if o1[k] >= 0 && o1[k] != Int32(i) { over[Int(o1[k])] = true; over[i] = true }
                    o1[k] = Int32(i)
                } else {
                    if o2[k] >= 0 && o2[k] != Int32(i) { over[Int(o2[k])] = true; over[i] = true }
                    o2[k] = Int32(i)
                }
            }
        }
        occ1 = o1; occ2 = o2; overlapped = over

        obs = l.obstacles
        var oi: [ObstacleID: Int] = [:]
        for (k, o) in l.obstacles.enumerated() { oi[o.id] = k }
        obsIndex = oi
        var tOf = [Int](repeating: -1, count: n)
        var tMem: [Int: [Int]] = [:]
        var kOn = [[Int]](repeating: [], count: n)
        var dC = [Int32](repeating: -1, count: size), bC = dC, pC = dC, peP = dC, cC = dC
        var peO = [Dir?](repeating: nil, count: size)
        var pEnds: [Int: [(Cell, Dir)]] = [:]
        var elev: [(Int, [Int], Set<ArrowID>)] = []
        var ds: [Int] = [], bs: [Int] = [], ps: [Int] = []
        var rev = [[Int]](repeating: [], count: l.obstacles.count)
        let C = l.cols, R = l.rows
        func inG(_ c: Cell) -> Bool { c.c >= 0 && c.r >= 0 && c.c < C && c.r < R }
        for (k, o) in l.obstacles.enumerated() {
            rev[k] = o.reveals.compactMap { idx[$0] }
            switch o.kind {
            case .tape:
                for a in o.arrows { if let i = idx[a] { tOf[i] = k } }
                tMem[k] = o.arrows.compactMap { idx[$0] }
            case .key:
                for a in o.arrows { if let i = idx[a] { kOn[i].append(k) } }
            case .door:
                ds.append(k)
                for c in o.cells where inG(c) { dC[c.r * C + c.c] = Int32(k) }
            case .box, .curtain:
                bs.append(k)
                for c in o.cells where inG(c) { bC[c.r * C + c.c] = Int32(k) }
            case .pipe:
                ps.append(k)
                for c in o.cells where inG(c) { pC[c.r * C + c.c] = Int32(k) }
                if o.ends.count == 2 {
                    for e in o.ends where inG(e.cell) {
                        peP[e.cell.r * C + e.cell.c] = Int32(k)
                        peO[e.cell.r * C + e.cell.c] = e.out
                    }
                    pEnds[k] = o.ends.map { ($0.cell, $0.out) }
                }
            case .elevator:
                let plat = o.arrows.compactMap { idx[$0] }
                elev.append((k, plat, Set(o.arrows)))
            case .corner:
                for c in o.cells where inG(c) { cC[c.r * C + c.c] = Int32(k) }
            }
        }
        tapeOf = tOf; tapeMembers = tMem; keysOn = kOn
        doorCell = dC; boxCell = bC; pipeCell = pC; pipeEndPipe = peP; pipeEndOut = peO; pipeEnds = pEnds
        cornerCell = cC
        elevators = elev.map { (k: $0.0, platform: $0.1, platformIDs: $0.2) }
        doors = ds; boxKinds = bs; pipes = ps
        reveals = rev
    }

    @inline(__always) func inGrid(_ c: Cell) -> Bool { c.c >= 0 && c.r >= 0 && c.c < cols && c.r < rows }
    /// The arrow index of an id (ids are sorted ascending).
    func index(of id: ArrowID) -> Int? {
        var lo = 0, hi = n
        while lo < hi {
            let mid = (lo + hi) / 2
            if ids[mid] < id { lo = mid + 1 } else { hi = mid }
        }
        return lo < n && ids[lo] == id ? lo : nil
    }
    @inline(__always) func flat(_ c: Cell) -> Int { c.r * cols + c.c }
}

/// A blocker found by a walk.
enum RefBlocker: Equatable {
    case arrow(Int)           // arrow index
    case obstacle(Int)        // obstacle index
}

/// One event of `commitExit` (arrowcore's event tuples; only the kinds the tools inspect carry payloads).
enum RefEvent: Equatable {
    case pipeCount(Int, Int)
    case pipeBreak(Int)
    case counter(Int, Int)
    case boxBreak(Int)
    case keyDispatched(Int, Int)
    case elevatorActivated(Int)
    case doorOpened(Int)
}

/// The mutable state of one board (arrowcore `Board`); a value type, so `copy()` is a plain assignment.
struct RefBoard {
    let S: RefStatic
    var alive: [Bool]
    var aliveCount: Int
    var hidden: [Bool]
    var doorOpen: [Bool]
    var doorTargeted: [Bool]
    var pendingDoors: [Int] = []
    /// per obstacle: pipe counter / box counter (nil = unlimited or not that kind).
    var pipeCtr: [Int?]
    var pipeBroken: [Bool]
    var boxCtr: [Int?]
    var boxBroken: [Bool]
    var elevActive: [Bool]

    init(_ s: RefStatic) {
        S = s
        alive = [Bool](repeating: true, count: s.n)
        aliveCount = s.n
        hidden = s.hiddenAtStart
        let m = s.obs.count
        doorOpen = [Bool](repeating: false, count: m)
        doorTargeted = doorOpen
        pipeBroken = doorOpen
        boxBroken = doorOpen
        elevActive = doorOpen
        pipeCtr = s.obs.map { $0.kind == .pipe ? $0.counter : nil }
        boxCtr = s.obs.map { ($0.kind == .box || $0.kind == .curtain) ? $0.counter : nil }
    }

    init(_ level: LevelSpec) { self.init(RefStatic(level)) }

    // MARK: queries

    @inline(__always) func live(_ i: Int) -> Bool { alive[i] && !hidden[i] }

    /// The tape's alive members (sorted), or [i].
    func unit(_ i: Int) -> [Int] {
        let t = S.tapeOf[i]
        guard t >= 0 else { return [i] }
        return (S.tapeMembers[t] ?? []).filter { alive[$0] }.sorted()
    }

    func units() -> [[Int]] {
        var seen = [Bool](repeating: false, count: S.n)
        var out: [[Int]] = []
        for i in 0..<S.n where alive[i] && !seen[i] && !hidden[i] {
            let u = unit(i)
            for m in u { seen[m] = true }
            out.append(u)
        }
        return out
    }

    /// The head's ray: blocker (nil = reaches the grid edge) and the pipes passed, in order.
    func walk(_ a: Int, ignore: [Int]) -> (blocker: RefBlocker?, passages: [Int]) {
        var none: [Int32] = []
        return walk(a, ignore: ignore, touched: &none, record: false)
    }

    /// The walk, recording every cell it examined when `record` (the greedy's cache watches them).
    func walk(_ a: Int, ignore: [Int], touched: inout [Int32], record: Bool) -> (blocker: RefBlocker?, passages: [Int]) {
        var none: RefTrace?
        return walk(a, ignore: ignore, touched: &touched, record: record, trace: &none)
    }

    /// What arrowcore's walk also returns (the validator's stub and loop checks read them): `cells` = the cells the head
    /// passes, in order, until the grid edge or the blocker (excluded; a pipe passage adds its two mouths), `corners` =
    /// the corner turns taken.
    struct RefTrace {
        var cells: [Cell] = []
        var corners = 0
    }

    /// The walk with its trace (arrowcore `walk`'s cells / corners).
    func walkTrace(_ a: Int, ignore: [Int] = []) -> (blocker: RefBlocker?, passages: [Int], trace: RefTrace) {
        var none: [Int32] = []
        var t: RefTrace? = RefTrace()
        let w = walk(a, ignore: ignore, touched: &none, record: false, trace: &t)
        return (w.blocker, w.passages, t!)
    }

    func walk(_ a: Int, ignore: [Int], touched: inout [Int32], record: Bool, trace: inout RefTrace?)
        -> (blocker: RefBlocker?, passages: [Int]) {
        var passages: [Int] = []
        var c = S.head[a]
        var d = S.dir[a]
        var hops = 0
        let cols = S.cols, rows = S.rows
        while true {
            let n = Cell(c.c + d.dc, c.r + d.dr)
            if n.c < 0 || n.r < 0 || n.c >= cols || n.r >= rows { return (nil, passages) }
            let k = n.r * cols + n.c
            if record { touched.append(Int32(k)) }
            // a locked door blocks first: an obstacle UNDER it (v552 L69's pipes) is inert until the burst
            let dk0 = Int(S.doorCell[k])
            if dk0 >= 0 && !doorOpen[dk0] { return (.obstacle(dk0), passages) }
            let p = Int(S.pipeCell[k])
            if p >= 0 && !pipeBroken[p] {
                if S.pipeEndPipe[k] == Int32(p), let out = S.pipeEndOut[k], out == d.opposite {
                    hops += 1
                    if hops > ContentRules.maxHops { return (.obstacle(p), passages) }
                    passages.append(p)
                    // pipe_other[(p, n)]: the OTHER end of this pipe
                    // Python builds pipe_other[(p, e0)] = e1 THEN pipe_other[(p, e1)] = e0 (the later write wins
                    // when both mouths share a cell)
                    let ends = S.pipeEnds[p]!
                    let other = ends[1].0 == n ? ends[0] : ends[1]
                    if trace != nil { trace!.cells.append(n); trace!.cells.append(other.0) }
                    c = other.0
                    d = other.1
                    continue
                }
                return (.obstacle(p), passages)
            }
            let kc = Int(S.cornerCell[k])
            if kc >= 0 {
                guard let t = S.obs[kc].turn, let nd = ContentRules.cornerTurn(t, d) else { return (.obstacle(kc), passages) }
                hops += 1
                if hops > ContentRules.maxHops { return (.obstacle(kc), passages) }
                if trace != nil { trace!.corners += 1; trace!.cells.append(n) }
                c = n
                d = nd
                continue
            }
            let dk = Int(S.doorCell[k])
            if dk >= 0 && !doorOpen[dk] { return (.obstacle(dk), passages) }
            let bk = Int(S.boxCell[k])
            if bk >= 0 && !boxBroken[bk] { return (.obstacle(bk), passages) }
            let x1 = Int(S.occ1[k])
            if x1 >= 0 && !ignore.contains(x1) && live(x1) { return (.arrow(x1), passages) }
            let x2 = Int(S.occ2[k])
            if x2 >= 0 && !ignore.contains(x2) && live(x2) { return (.arrow(x2), passages) }
            let own = (S.layer[a] == 1 ? x1 : x2) == a || (S.overlapped[a] && S.arrowCells[a].contains(n))
            if own { return (.arrow(a), passages) }
            if trace != nil { trace!.cells.append(n) }
            c = n
        }
    }

    enum Resolution {
        case exit(unit: [Int], passages: [[Int]])
        case bump(unit: [Int], blocker: RefBlocker)
        case ignored
    }

    func resolve(_ a: Int) -> Resolution {
        guard alive[a], !hidden[a] else { return .ignored }
        let u = unit(a)
        var walks: [[Int]] = []
        walks.reserveCapacity(u.count)
        for m in u {
            let w = walk(m, ignore: u)
            if let b = w.blocker { return .bump(unit: u, blocker: b) }
            walks.append(w.passages)
        }
        return .exit(unit: u, passages: walks)
    }

    func freeUnits() -> [(unit: [Int], passages: [[Int]])] {
        var out: [(unit: [Int], passages: [[Int]])] = []
        for u in units() {
            if case .exit(let unit, let p) = resolve(u[0]) { out.append((unit, p)) }
        }
        return out
    }

    var cleared: Bool { aliveCount == 0 }

    // MARK: mutation

    @discardableResult
    mutating func commitExit(_ u: [Int], _ passages: [[Int]]) -> [RefEvent] {
        var ev: [RefEvent] = []
        for m in u where alive[m] { alive[m] = false; aliveCount -= 1 }
        for ps in passages {
            for p in ps {
                if pipeBroken[p] { continue }
                guard var c = pipeCtr[p] else { continue }     // unlimited
                c -= 1
                pipeCtr[p] = c
                ev.append(.pipeCount(p, c))
                if c <= 0 { pipeBroken[p] = true; ev.append(.pipeBreak(p)) }
            }
        }
        let n = u.count
        for b in S.boxKinds {
            if boxBroken[b] { continue }
            guard var c = boxCtr[b] else { continue }
            c -= n
            boxCtr[b] = c
            ev.append(.counter(b, max(c, 0)))
            if c <= 0 {
                boxBroken[b] = true
                reveal(b)
                ev.append(.boxBreak(b))
            }
        }
        for m in u {
            for k in S.keysOn[m] {
                if let d = keyTarget(k) {
                    doorTargeted[d] = true
                    pendingDoors.append(d)
                    ev.append(.keyDispatched(k, d))
                }
            }
        }
        for e in S.elevators where !elevActive[e.k] {
            // Python: `plat and not (plat & self.alive)` over the listed ids (an id the level lacks is never alive)
            if !e.platformIDs.isEmpty && !e.platform.contains(where: { alive[$0] }) {
                elevActive[e.k] = true
                reveal(e.k)
                ev.append(.elevatorActivated(e.k))
            }
        }
        return ev
    }

    func keyTarget(_ k: Int) -> Int? {
        if let o = S.obs[k].opens {
            guard let d = S.obsIndex[o] else { return nil }
            return (!doorOpen[d] && !doorTargeted[d]) ? d : nil
        }
        var best: Int?
        for d in S.doors where !doorOpen[d] && !doorTargeted[d] {
            guard let b = best else { best = d; continue }
            let od = S.obs[d].order ?? 0, ob = S.obs[b].order ?? 0
            if od < ob || (od == ob && S.obs[d].id.raw < S.obs[b].id.raw) { best = d }
        }
        return best
    }

    mutating func reveal(_ k: Int) { for a in S.reveals[k] { hidden[a] = false } }

    @discardableResult
    mutating func openPendingDoors() -> [RefEvent] {
        var ev: [RefEvent] = []
        for d in pendingDoors where !doorOpen[d] {
            doorOpen[d] = true
            reveal(d)
            ev.append(.doorOpened(d))
        }
        pendingDoors = []
        return ev
    }

    /// The DFS memo key: alive set, pipe counters, doors open or pending, active elevators.
    func stateKey() -> [Int] {
        var k: [Int] = []
        k.reserveCapacity(S.n / 60 + S.obs.count * 2 + 2)
        var word = 0, bit = 0
        for a in alive { if a { word |= 1 << bit }; bit += 1; if bit == 60 { k.append(word); word = 0; bit = 0 } }
        k.append(word)
        for p in S.pipes { k.append(pipeCtr[p] ?? Int.min) }
        for d in S.doors { k.append(doorOpen[d] || pendingDoors.contains(d) ? 1 : 0) }
        for e in S.elevators { k.append(elevActive[e.k] ? 1 : 0) }
        return k
    }
}

/// A board plus a cache of unit resolutions (greedy and waves). The reference re-resolves every unit before each tap; a
/// resolution depends only on the unit's members' alive/hidden flags and the state of the cells its walks examined, so
/// it is kept per first member until one of those cells changes (an arrow leaving or revealed, a pipe or box breaking, a
/// door opening) or a member changes state. Same free lists, same orders.
final class RefResolver {
    var b: RefBoard
    let S: RefStatic
    var cache: [RefBoard.Resolution?]
    var watch: [[Int32]]
    var touched: [Int32] = []
    var seen: [Bool]

    init(_ board: RefBoard) {
        b = board
        S = board.S
        cache = [RefBoard.Resolution?](repeating: nil, count: S.n)
        watch = [[Int32]](repeating: [], count: max(1, S.cols * S.rows))
        seen = [Bool](repeating: false, count: S.n)
    }

    @inline(__always) func markCell(_ k: Int) {
        for a in watch[k] { cache[Int(a)] = nil }
        watch[k].removeAll(keepingCapacity: true)
    }

    func markArrow(_ a: Int) {
        for c in S.arrowCells[a] where S.inGrid(c) { markCell(S.flat(c)) }
        cache[a] = nil
        let t = S.tapeOf[a]
        if t >= 0 { for m in S.tapeMembers[t] ?? [] { cache[m] = nil } }
    }

    func markObstacle(_ k: Int) {
        for c in S.obs[k].cells where S.inGrid(c) { markCell(S.flat(c)) }
        for a in S.reveals[k] { markArrow(a) }
    }

    func apply(_ ev: [RefEvent]) {
        for e in ev {
            switch e {
            case .pipeBreak(let x), .boxBreak(let x), .elevatorActivated(let x), .doorOpened(let x): markObstacle(x)
            default: break
            }
        }
    }

    func resolve(_ a: Int) -> RefBoard.Resolution {
        if let r = cache[a] { return r }
        touched.removeAll(keepingCapacity: true)
        let r: RefBoard.Resolution
        if !b.alive[a] || b.hidden[a] {
            r = .ignored
        } else {
            let t = S.tapeOf[a]
            let u = t >= 0 ? b.unit(a) : [a]
            var walks: [[Int]] = []
            var bump: RefBlocker?
            for m in u {
                let w = b.walk(m, ignore: u, touched: &touched, record: true)
                if let x = w.blocker { bump = x; break }
                walks.append(w.passages)
            }
            r = bump.map { .bump(unit: u, blocker: $0) } ?? .exit(unit: u, passages: walks)
        }
        for k in touched { watch[Int(k)].append(Int32(a)) }
        cache[a] = r
        return r
    }

    /// arrowcore `free_units` (units in ascending first-member order, each resolved at its first member).
    func freeUnits() -> [(unit: [Int], passages: [[Int]])] {
        var fu: [(unit: [Int], passages: [[Int]])] = []
        for i in 0..<S.n { seen[i] = false }
        for i in 0..<S.n where b.alive[i] && !seen[i] && !b.hidden[i] {
            let lead: Int
            if S.tapeOf[i] >= 0 {
                let u = b.unit(i)
                for m in u { seen[m] = true }
                lead = u[0]
            } else {
                seen[i] = true
                lead = i
            }
            if case .exit(let unit, let p) = resolve(lead) { fu.append((unit, p)) }
        }
        return fu
    }

    @discardableResult
    func commitExit(_ u: [Int], _ p: [[Int]]) -> [RefEvent] {
        let ev = b.commitExit(u, p)
        for a in u { markArrow(a) }
        apply(ev)
        return ev
    }

    @discardableResult
    func openPendingDoors() -> [RefEvent] {
        let ev = b.openPendingDoors()
        apply(ev)
        return ev
    }
}

extension ContentRules {
    static func cornerTurn(_ t: CornerTurn, _ d: Dir) -> Dir? {
        // arrowcore CORNER: 'upRight': {up: right, left: down}, 'upLeft': {up: left, right: down},
        // 'downRight': {down: right, left: up}, 'downLeft': {down: left, right: up}
        switch (t, d) {
        case (.upRight, .up): return .right
        case (.upRight, .left): return .down
        case (.upLeft, .up): return .left
        case (.upLeft, .right): return .down
        case (.downRight, .down): return .right
        case (.downRight, .left): return .up
        case (.downLeft, .down): return .left
        case (.downLeft, .right): return .up
        default: return nil
        }
    }

    /// 1 if exiting `u` breaks a pipe or activates an elevator (arrowcore `_nonmonotone`: commit on a copy and look for
    /// pipeBreak / elevatorActivated). Evaluated without the copy: the same pipe decrements in walk order, and the same
    /// "every listed platform arrow is gone" test.
    static func nonMonotone(_ b: RefBoard, _ u: [Int], _ p: [[Int]]) -> Int {
        var used: [Int: Int] = [:]
        for ps in p {
            for q in ps where !b.pipeBroken[q] {
                guard let c0 = b.pipeCtr[q] else { continue }
                let k = (used[q] ?? 0) + 1
                if c0 - k <= 0 { return 1 }
                used[q] = k
            }
        }
        for e in b.S.elevators where !b.elevActive[e.k] && !e.platformIDs.isEmpty {
            if !e.platform.contains(where: { b.alive[$0] && !u.contains($0) }) { return 1 }
        }
        return 0
    }

    /// Stable sort of free units by (non-monotone, first member id).
    static func monotoneFirst(_ b: RefBoard, _ fu: [(unit: [Int], passages: [[Int]])]) -> [(unit: [Int], passages: [[Int]])] {
        if b.S.pipes.isEmpty && b.S.elevators.isEmpty { return fu }       // every key is (0, first id): already sorted
        let keyed = fu.enumerated().map { (nonMonotone(b, $0.element.unit, $0.element.passages), $0.element.unit[0], $0.offset, $0.element) }
        return keyed.sorted { ($0.0, $0.1, $0.2) < ($1.0, $1.1, $1.2) }.map(\.3)
    }

    public struct GreedyOutcome: Sendable, Equatable {
        public var ok: Bool
        /// Units in tap order (arrow ids, each unit sorted).
        public var order: [[ArrowID]]
        /// The units left when stuck.
        public var stuck: [[ArrowID]]
        public var doors: Int
    }

    /// arrowcore `greedy`: one free unit at a time (monotone taps first, then the lowest id); doors open before the next tap.
    public static func greedy(_ level: LevelSpec, preferMonotone: Bool = true) -> GreedyOutcome {
        greedy(RefBoard(level), preferMonotone: preferMonotone)
    }

    static func greedy(_ start: RefBoard, preferMonotone: Bool = true) -> GreedyOutcome {
        let r = RefResolver(start)
        let S = r.S
        var order: [[ArrowID]] = []
        var doors = 0
        while !r.b.cleared {
            var fu = r.freeUnits()
            if fu.isEmpty {
                if !r.b.pendingDoors.isEmpty { doors += r.openPendingDoors().count; continue }
                return GreedyOutcome(ok: false, order: order, stuck: r.b.units().map { $0.map { S.ids[$0] } }, doors: doors)
            }
            if preferMonotone && fu.count > 1 { fu = monotoneFirst(r.b, fu) }
            let (u, p) = fu[0]
            r.commitExit(u, p)
            doors += r.openPendingDoors().count
            order.append(u.map { S.ids[$0] })
        }
        return GreedyOutcome(ok: true, order: order, stuck: [], doors: doors)
    }

    public struct DFSOutcome: Sendable, Equatable {
        public var ok: Bool
        public var order: [[ArrowID]]
        public var nodes: Int
        public var exhausted: Bool
    }

    /// arrowcore `dfs`: exact search with a memo over the full state (budget = nodes).
    public static func dfs(_ level: LevelSpec, budget: Int = 200_000) -> DFSOutcome {
        var seen = Set<[Int]>()
        var nodes = 0
        var path: [[Int]] = []
        var exhausted = false
        func rec(_ b: RefBoard) -> Bool {
            if b.cleared { return true }
            nodes += 1
            if nodes > budget { exhausted = true; return false }
            let k = b.stateKey()
            if seen.contains(k) { return false }
            seen.insert(k)
            var fu = b.freeUnits()
            if fu.isEmpty && !b.pendingDoors.isEmpty {
                var b2 = b
                b2.openPendingDoors()
                return rec(b2)
            }
            fu = monotoneFirst(b, fu)
            for (u, p) in fu {
                var b2 = b
                b2.commitExit(u, p)
                b2.openPendingDoors()
                path.append(u)
                if rec(b2) { return true }
                if exhausted { return false }
                path.removeLast()
            }
            return false
        }
        let b0 = RefBoard(level)
        let ok = rec(b0)
        if exhausted { return DFSOutcome(ok: false, order: [], nodes: nodes, exhausted: true) }
        return DFSOutcome(ok: ok, order: ok ? path.map { $0.map { b0.S.ids[$0] } } : [], nodes: nodes, exhausted: false)
    }

    /// arrowcore `waves`: each wave taps every unit free at its start (re-resolved before each tap); doors dispatched in
    /// a wave open at its end. (waves, units per wave, ok).
    static func waves(_ start: RefBoard) -> (count: Int, perWave: [Int], ok: Bool) {
        let r = RefResolver(start)
        var per: [Int] = []
        var guardCount = 0
        while !r.b.cleared {
            guardCount += 1
            if guardCount > 5000 { return (per.count, per, false) }
            let fu = r.freeUnits()
            if fu.isEmpty {
                if !r.b.pendingDoors.isEmpty { r.openPendingDoors(); continue }
                return (per.count, per, false)
            }
            var n = 0
            for (u, _) in fu {
                guard case .exit(let unit, let p) = r.resolve(u[0]) else { continue }
                r.commitExit(unit, p)
                n += 1
            }
            r.openPendingDoors()
            per.append(n)
        }
        return (per.count, per, true)
    }

    /// arrowcore `metrics` (the bundle's LevelMetrics plus the extras the generator and the curve fit use).
    public struct Measured: Sendable, Equatable {
        public var rounds: Int
        public var freeAtStart: Int
        public var arrows: Int
        public var cells: Int
        public var meanLength: Double
        public var botTimeLeft: Double
        public var units: Int
        public var visibleUnits: Int
        public var maxLength: Int
        public var density: Double
        public var waves: [Int]
        public var wavesOK: Bool

        /// The subset the bundle schema carries (arrowcore `bundle_metrics`).
        public var bundle: LevelMetrics {
            LevelMetrics(rounds: rounds, freeAtStart: freeAtStart, arrows: arrows, cells: cells, meanLength: meanLength,
                         botTimeLeft: botTimeLeft)
        }
    }

    public static func metrics(_ level: LevelSpec) -> Measured {
        metrics(level, board: RefBoard(level))
    }

    static func metrics(_ l: LevelSpec, board b: RefBoard, waves precomputed: (count: Int, perWave: [Int], ok: Bool)? = nil) -> Measured {
        let lens = l.arrows.map(\.cells.count)
        let units0 = b.units()
        let free0 = b.freeUnits().count
        let tapes = l.obstacles.filter { $0.kind == .tape }
        let nUnits = l.arrows.count - tapes.reduce(0) { $0 + ($1.arrows.count - 1) }
        let w = precomputed ?? waves(b)
        let doors = l.obstacles.filter { $0.kind == .door }.count
        var occupied = Set<Int>()
        let span = max(1, l.cols * l.rows) + 1
        for a in l.arrows {
            let layer = a.layer
            for c in a.cells {
                // (layer, cell) pairs; cells outside the grid get their own keys (invalid content only)
                let inside = c.c >= 0 && c.r >= 0 && c.c < l.cols && c.r < l.rows
                let key = inside ? layer * span + c.r * l.cols + c.c : -(abs(layer) * 1_000_003 + (c.c & 0xFFFF) * 65_537 + (c.r & 0xFFFF))
                occupied.insert(key)
            }
        }
        let cells = occupied.count
        let bot = Double(l.timerSeconds) - (Double(nUnits) * tapSeconds + Double(doors) * doorSeconds)
        let mean = Double(lens.reduce(0, +)) / Double(max(1, lens.count))
        return Measured(rounds: w.count, freeAtStart: free0, arrows: l.arrows.count, cells: cells,
                        meanLength: ContentJSON.pyRound(mean, 3), botTimeLeft: ContentJSON.pyRound(bot, 1),
                        units: nUnits, visibleUnits: units0.count, maxLength: lens.max() ?? 0,
                        density: ContentJSON.pyRound(Double(cells) / Double(l.cols * l.rows), 3),
                        waves: w.perWave, wavesOK: w.ok)
    }

    /// arrowcore `structural_problems`, message for message (Python tuple syntax for cells).
    public static func structuralProblems(_ l: LevelSpec) -> [String] {
        var out: [String] = []
        let cols = l.cols, rows = l.rows
        var ids = Set<ArrowID>()
        var occ: [Int: [Cell: Int]] = [1: [:], 2: [:]]
        func t(_ c: Cell) -> String { "(\(c.c), \(c.r))" }
        for a in l.arrows {
            let cs = a.cells
            let aid = a.id.raw
            if ids.contains(a.id) { out.append("arrow \(aid): duplicate id") }
            ids.insert(a.id)
            if cs.count < 2 { out.append("arrow \(aid): \(cs.count) cell(s)") }
            for (x, y) in zip(cs, cs.dropFirst()) where Dir(from: x, to: y) == nil {
                out.append("arrow \(aid): step \(t(x))->\(t(y)) not orthogonal")
            }
            if Set(cs).count != cs.count { out.append("arrow \(aid): crosses itself") }
            if cs.count >= 2 {
                let last = Dir(from: cs[cs.count - 2], to: cs[cs.count - 1])
                if last != a.dir { out.append("arrow \(aid): dir \(a.dir.rawValue) but last step \(last?.rawValue ?? "None")") }
            }
            let layer = a.layer == 0 ? 1 : a.layer
            for c in cs {
                if !(0 <= c.c && c.c < cols && 0 <= c.r && c.r < rows) { out.append("arrow \(aid): \(t(c)) outside \(cols)x\(rows)") }
                if let o = occ[layer]?[c] { out.append("arrow \(aid) shares \(t(c)) with \(o) (layer \(layer))") }
                occ[layer, default: [:]][c] = aid
            }
            let own = Set(cs)
            if let h = cs.last {
                var p = h + a.dir
                while 0 <= p.c && p.c < cols && 0 <= p.r && p.r < rows {
                    if own.contains(p) { out.append("arrow \(aid): ray crosses its own body at \(t(p))"); break }
                    p = p + a.dir
                }
            }
        }
        return out
    }
}
