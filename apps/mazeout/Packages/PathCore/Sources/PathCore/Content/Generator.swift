import Foundation

// C4 (SPEC-architecture §4.14, D9; SPEC-gameplay §14.3; CONSISTENCY L-7, L-8). The level generator: a line-for-line port
// of design/tools/gen_levels.py, so the designed levels of design/levels.json (L84-L150 since the content recast of
// 2026-09-25) come out BYTE FOR BYTE and every endless level past the authored end is the same board the reference
// produces (GeneratorTests pins both).
//
// Per level n: a target from the curve's template (cycle position n mod 10, decade slot floor(n / 10) mod curve.slots);
// an obstacle plan (fork "plan"); candidates from forks "a<phase>.<attempt>": regions (doors, elevator, boxes, pipes +
// feeders, tapes, then corners on an empty margin line), snake tiling,
// preferred heads (plain peel + DAG head flips), the obstacle-aware peel (a removal WITNESS: solvable by construction),
// assembly (crop, renumber), the checks (structure, the greedy solver, bot ≥ 20 % of the timer) and the score; the best of
// `attempts` candidates wins, dropping the last obstacle kind when a plan is infeasible.
//
// Every random number is drawn from PathRandom in the reference's order; Python's integer `//`, its stable `sorted`, its
// short-circuit `and`/`or` (a draw that Python skips is skipped here too) and its float operations (one IEEE operation at
// a time) are reproduced exactly. Pure and thread-safe (no shared state): LevelProvider runs it on a background queue.

public enum Generator {

    /// Why a candidate was rejected (the reference's `Fail` messages).
    public struct Fail: Error, CustomStringConvertible, Equatable {
        public let reason: String
        public init(_ r: String) { reason = r }
        public var description: String { reason }
    }

    public struct Target: Sendable, Equatable {
        public var n: Int
        public var pos: Int
        public var tag: LevelTag
        public var template: Int
        public var units: Int
        public var rounds: Int
        public var free: Int
        public var cols: Int
        public var rows: Int
        public var templateTimer: Int
    }

    /// What the reference prints and stores in design/tools/work/designed.json `infos` (for the parity tests and
    /// `pclevels gen`).
    public struct Info: Sendable, Equatable {
        public var level: Int
        public var target: Target
        public var planned: [String]
        public var kinds: [String]
        public var units: Int
        public var rounds: Int
        public var free: Int
        public var arrows: Int
        public var cols: Int
        public var rows: Int
        public var meanLength: Double
        public var maxLength: Int
        public var timer: Int
        public var botLeft: Double
        public var density: Double
        /// round(score, 3)
        public var score: Double
        /// "<phase>.<attempt>" of the winning candidate.
        public var attempt: String
        public var shape: String?
        public var doorStyle: String?
        public var boxStyle: String?
        /// The margin sides the corners stand on (the reference's notes.corner_sides; nil when the plan has no corner).
        public var cornerSides: [String]?
        public var rejected: [String]
    }

    public struct Output: Sendable {
        public var level: LevelSpec
        public var info: Info
    }

    static let tagByPos: [Int: LevelTag] = [4: .hard, 9: .superHard]
    static let dirL: [Dir] = [.up, .down, .left, .right]

    // MARK: - entry point

    /// The level `n` of `curve` (the reference `generate`). Throws `Fail` only when no candidate survives any phase
    /// (the reference raises RuntimeError there; LevelProvider falls back, never crashes).
    public static func generate(level n: Int, curve: CurveSpec) throws -> Output {
        try generate(level: n, curve: curve, seed: PathRandom.levelSeed(level: n, salt: curve.salt))
    }

    /// A candidate gate: nil = accepted, else the reason it is refused.
    public typealias Gate = (LevelSpec) -> String?

    /// The same algorithm from an explicit seed (LevelProvider's re-rolls use `LevelProvider.rollSeed(levelSeed, k)`,
    /// SPEC.md §5.27), optionally
    /// GATED (SPEC-gameplay §14.3 runtime: "a candidate failing the validator retries with the next attempt fork; the
    /// level is never served unvalidated"). The gate runs on a candidate only when it would become the best so far; a
    /// refused candidate is rejected like a failed one ("gate: <reason>") and the attempt loop goes on. When the
    /// reference's winner passes the gate the result is identical to the ungated one (every candidate the reference
    /// scored below the winner would have been the winner), so the gate changes only levels whose reference output the
    /// validator refuses (L240, L254, L519, L580 and L617 of L151-L650 on the recast curve: dead ends).
    public static func generate(level n: Int, curve: CurveSpec, seed: UInt64, gate: Gate? = nil) throws -> Output {
        let rng0 = PathRandom(seed: seed)
        let tgt = try target(curve, n)
        let kinds = try obstaclePlan(curve, n, Rng(rng0.fork("plan")))
        var best: (s: Double, lvl: LevelSpec, m: ContentRules.Measured, notes: Notes, a: String)?
        var reasons: [String] = []
        var tried = kinds
        for phase in 0...kinds.count {
            tried = Array(kinds.prefix(kinds.count - phase))
            for a in 0..<curve.attempts {
                let rng = Rng(rng0.fork("a\(phase).\(a)"))
                let cand: (LevelSpec, ContentRules.Measured, Notes)
                do { cand = try buildCandidate(curve, tgt, tried, rng) } catch let f as Fail {
                    reasons.append(f.reason)
                    continue
                }
                let s = score(tgt, cand.1)
                if best == nil || s < best!.s {
                    if let gate {
                        var l = cand.0
                        l.seed = seed
                        l.metrics = cand.1.bundle
                        if let why = gate(l) { reasons.append("gate: " + why); continue }
                    }
                    best = (s, cand.0, cand.1, cand.2, "\(phase).\(a)")
                }
                if s < curve.goodEnough { break }
            }
            if best != nil { break }
        }
        guard var b = best else { throw Fail("L\(n): no candidate (\(reasons.prefix(8).joined(separator: ", ")))") }
        b.lvl.seed = seed
        b.lvl.metrics = b.m.bundle
        let info = Info(level: n, target: tgt, planned: kinds, kinds: tried, units: b.m.units, rounds: b.m.rounds,
                        free: b.m.freeAtStart, arrows: b.m.arrows, cols: b.lvl.cols, rows: b.lvl.rows,
                        meanLength: b.m.meanLength, maxLength: b.m.maxLength, timer: b.lvl.timerSeconds,
                        botLeft: b.m.botTimeLeft, density: b.m.density, score: ContentJSON.pyRound(b.s, 3), attempt: b.a,
                        shape: b.notes.shape, doorStyle: b.notes.doorStyle, boxStyle: b.notes.boxStyle,
                        cornerSides: b.notes.cornerSides, rejected: reasons)
        return Output(level: b.lvl, info: info)
    }

    // MARK: - targets (reference: growth, target_for, obstacle_plan, timer_for, score)

    static func growth(_ curve: CurveSpec, _ n: Int) -> Double {
        let steps = max(0, Silhouettes.floorDiv(n - curve.growth.from, 10))
        return min(curve.growth.cap, 1.0 + curve.growth.perDecade * Double(steps))
    }

    public static func target(_ curve: CurveSpec, _ n: Int) throws -> Target {
        let p = Silhouettes.floorMod(n, 10)
        let tag = tagByPos[p] ?? .normal
        guard curve.slots > 0 else { throw Fail("curve slots \(curve.slots)") }
        let slot = Silhouettes.floorMod(Silhouettes.floorDiv(n, 10), curve.slots)   // (n // 10) % curve.get('slots', 3)
        guard let tpl = curve.template(pos: p, slot: slot) else { throw Fail("no template for position \(p) slot \(slot)") }
        let gr = growth(curve, n)
        let half = 1.0 + (gr - 1.0) / 2.0
        return Target(n: n, pos: p, tag: tag, template: tpl.level,
                      units: Int(Double(tpl.units) * gr + 0.5),
                      rounds: Int(Double(tpl.rounds) * half + 0.5),
                      free: tpl.free,
                      cols: min(curve.maxCols, max(10, Int(Double(tpl.cols) * half + 0.5))),
                      rows: min(curve.maxRows, max(12, Int(Double(tpl.rows) * half + 0.5))),
                      templateTimer: tpl.timer)
    }

    static func obstaclePlan(_ curve: CurveSpec, _ n: Int, _ rng: Rng) throws -> [String] {
        let ob = curve.obstacles
        let unlocked = Set(ob.firstLevel.filter { $0.value <= n }.map(\.key))
        let cw = ob.countWeights
        var x = try rng.below(cw.reduce(0, +))
        var count = 0
        while count < cw.count && x >= cw[count] { x -= cw[count]; count += 1 }
        var kinds: [String] = []
        let pool = ob.kindOrder.filter { unlocked.contains($0) }
        for _ in 0..<count {
            let opts = pool.filter { !kinds.contains($0) }
            if opts.isEmpty { break }
            let ws = opts.map { ob.kindWeights[$0] ?? 0 }
            var y = try rng.below(ws.reduce(0, +))
            for (k, w) in zip(opts, ws) {
                if y < w { kinds.append(k); break }
                y -= w
            }
        }
        let order = ["door", "elevator", "box", "pipe", "tape", "corner"]   // big regions first, margins last
        return stableSorted(kinds) { (order.firstIndex(of: $0) ?? 99) < (order.firstIndex(of: $1) ?? 99) }
    }

    static func timerFor(_ curve: CurveSpec, _ tag: LevelTag, units: Int, doors: Int, _ rng: Rng, templateTimer: Int?) -> Int {
        let t = curve.timers
        // the phone's timer at the template's position (1:40 ... 3:30), for every tag; no random draw
        if t.fromTemplate, let tt = templateTimer { return tt }
        if tag == .hard { return t.hard }
        if tag == .superHard { return t.superHard }
        let work = Double(units) * ContentRules.tapSeconds + Double(doors) * ContentRules.doorSeconds
        if work <= Double(t.short) * t.maxWorkShareShort && rng.chance(t.pShort) { return t.short }
        return t.normal
    }

    static func score(_ t: Target, _ m: ContentRules.Measured) -> Double {
        let a = Double(abs(m.units - t.units)) / max(1.0, Double(t.units))
        let b = Double(abs(m.rounds - t.rounds)) / max(1.0, Double(t.rounds))
        let c = 0.5 * Double(abs(m.freeAtStart - t.free)) / max(3.0, Double(t.free))
        return a + b + c
    }

    // MARK: - one candidate

    struct Notes { var shape: String?; var doorStyle: String?; var boxStyle: String?; var cornerSides: [String]? }

    static func buildCandidate(_ curve: CurveSpec, _ tgt: Target, _ kinds: [String], _ rng: Rng)
        throws -> (LevelSpec, ContentRules.Measured, Notes) {
        let W = tgt.cols, H = tgt.rows
        let lens = curve.lengths
        let total = lens.reduce(0) { $0 + $1.count }
        let sampleLen: (Rng) throws -> Int = { r in
            var x = try r.below(total)
            for (k, v) in lens {
                if x < v { return k }
                x -= v
            }
            return 2
        }
        let straight = curve.straight
        var shape: String?
        if Set(kinds).isSubset(of: ["tape"]) && rng.chance(curve.silhouette.p) {
            let shapes = curve.silhouette.shapes
            shape = shapes[try rng.below(shapes.count)]
        }
        var mask: Set<Cell>?
        if let s = shape {
            let flags = Silhouettes.mask(s, cols: W, rows: H)
            var m = Set<Cell>()
            for r in 0..<H { for c in 0..<W where flags[r * W + c] { m.insert(Cell(c, r)) } }
            mask = m
            if m.count < Silhouettes.floorDiv(W * H * 45, 100) { mask = nil; shape = nil }
        }
        let plan = try planRegions(rng, W, H, kinds)
        if let m = mask {
            for bundle in plan.tapes where bundle.contains(where: { $0.cells.contains { !m.contains($0) } }) {
                throw Fail("tape outside the silhouette")
            }
        }
        let allc = mask ?? rect(0, 0, W - 1, H - 1)
        let outCells = allc.subtracting(plan.used)
        let tiledArea = outCells.count + plan.doors.reduce(0) { $0 + $1.count } + (plan.elevator.map { 2 * $0.count } ?? 0)
        let budget = max(6, Silhouettes.floorDiv(tgt.units * curve.mergeFactor, 100) - plan.tapes.count)
        func share(_ area: Int) -> Int { max(1, Silhouettes.floorDiv(budget * area, max(1, tiledArea))) }

        var units: [Int: GUnit] = [:]
        var uid = 0
        func addSnakes(_ cells: Set<Cell>, _ region: Region, _ layer: Int) throws -> [[Cell]] {
            let sn = try merge(try tile(cells, W, H, rng, sampleLen, straight), rng, share(cells.count), curve.maxLength, W, H)
            for p in sn {
                units[uid] = GUnit(kind: .snake, cells: p, members: [], region: region, layer: layer)
                uid += 1
            }
            return sn
        }
        _ = try addSnakes(outCells, .out, 1)
        for (k, R) in plan.doors.enumerated() { _ = try addSnakes(R, .door(k), 1) }
        if let E = plan.elevator {
            let plat = try addSnakes(E, .plat, 1)
            if plat.count < 2 { throw Fail("platform too small") }
            _ = try addSnakes(E, .l2, 2)
        }
        for members in plan.tapes {
            units[uid] = GUnit(kind: .bundle, cells: [], members: members, region: .out, layer: 1)
            uid += 1
        }
        for f in plan.feeders {
            units[uid] = GUnit(kind: .fixed, cells: [], members: [f], region: .out, layer: 1)
            uid += 1
        }
        // preferred heads: plain peel + DAG search over the layer-1 snakes visible at the start
        var prefs: [[Int]: [Cell]] = [:]
        let outIDs = units.keys.sorted().filter { units[$0]!.kind == .snake && units[$0]!.region == .out }
        let base = outIDs.map { units[$0]!.cells }
        if let order = try plainPeel(W, H, base, rng), !order.isEmpty {
            let dag = Dag(order, W, H)
            try optimise(dag, rng, R: tgt.rounds, F: tgt.free, steps: curve.flipSteps)
            for i in outIDs { units.removeValue(forKey: i) }
            for a in dag.A {
                units[uid] = GUnit(kind: .snake, cells: a.cells, members: [], region: .out, layer: 1)
                uid += 1
                prefs[cellKey(a.cells, W)] = a.cells
            }
        }
        let totalVisible = units.values.filter { $0.region == .out }.count
        let peel = Peel(W, H, units, plan, rng, prefs, totalVisible)
        try peel.run()
        // notes.corner_sides only when set (the reference: `if plan.get('corner_sides')`)
        let sides = plan.cornerSides.flatMap { $0.isEmpty ? nil : $0 }
        return try assemble(peel, plan, tgt, curve, rng, Notes(shape: shape, doorStyle: plan.doorStyle, boxStyle: plan.boxStyle,
                                                               cornerSides: sides))
    }

    // MARK: - helpers

    /// A shared random stream (the reference passes one PathRandom object around).
    final class Rng {
        var r: PathRandom
        init(_ r: PathRandom) { self.r = r }
        func below(_ n: Int) throws -> Int {
            guard n > 0 else { throw Fail("below(\(n))") }
            return r.below(n)
        }
        func chance(_ p: Double) -> Bool { r.unit() < p }
        func shuffle<T>(_ a: inout [T]) { r.shuffle(&a) }
    }

    enum Region: Equatable, Hashable {
        case out, door(Int), plat, l2
    }

    struct GUnit {
        enum Kind { case snake, bundle, fixed }
        var kind: Kind
        var cells: [Cell]
        var members: [(cells: [Cell], dir: Dir)]
        var region: Region
        var layer: Int
        var allCells: [Cell] { kind == .snake ? cells : members.flatMap(\.cells) }
    }

    @inline(__always) static func step(_ c: Cell, _ d: Dir) -> Cell { Cell(c.c + d.dc, c.r + d.dr) }

    static func rect(_ c0: Int, _ r0: Int, _ c1: Int, _ r1: Int) -> Set<Cell> {
        var s = Set<Cell>()
        guard c1 >= c0, r1 >= r0 else { return s }
        for r in r0...r1 { for c in c0...c1 { s.insert(Cell(c, r)) } }
        return s
    }

    /// Stable sort (Python's `sorted`).
    static func stableSorted<T>(_ a: [T], by less: (T, T) -> Bool) -> [T] {
        a.enumerated().sorted { less($0.element, $1.element) || (!less($1.element, $0.element) && $0.offset < $1.offset) }
            .map(\.element)
    }

    /// Sort key of a set of in-grid cells (the reference's `frozenset(cells)`).
    static func cellKey(_ cells: [Cell], _ W: Int) -> [Int] { cells.map { $0.r * W + $0.c }.sorted() }

    // MARK: - tiling (reference: tile, merge)

    static func tile(_ cells: Set<Cell>, _ W: Int, _ H: Int, _ rng: Rng, _ sampleLen: (Rng) throws -> Int,
                     _ straight: Double) throws -> [[Cell]] {
        var free = [Bool](repeating: false, count: W * H)
        for c in cells { free[c.r * W + c.c] = true }
        func isFree(_ q: Cell) -> Bool { q.c >= 0 && q.r >= 0 && q.c < W && q.r < H && free[q.r * W + q.c] }
        var order = cells.sorted { ($0.r, $0.c) < ($1.r, $1.c) }
        rng.shuffle(&order)
        var snakes: [[Cell]] = []
        for s in order {
            if !free[s.r * W + s.c] { continue }
            let target = try sampleLen(rng)
            var path = [s]
            free[s.r * W + s.c] = false
            var d = dirL[try rng.below(4)]
            for end in 0..<2 {
                while path.count < target {
                    let cur = end == 0 ? path[path.count - 1] : path[0]
                    if path.count >= 2 {
                        d = end == 0 ? Dir(from: path[path.count - 2], to: path[path.count - 1])!
                                     : Dir(from: path[1], to: path[0])!
                    }
                    var turn: [Dir] = (d == .up || d == .down) ? [.left, .right] : [.up, .down]
                    if try rng.below(2) != 0 { turn.reverse() }
                    let opts = rng.chance(straight) ? [d] + turn : turn + [d]
                    var nxt: (Cell, Dir)?
                    for o in opts {
                        let q = step(cur, o)
                        if isFree(q) { nxt = (q, o); break }
                    }
                    guard let (q, o) = nxt else { break }
                    free[q.r * W + q.c] = false
                    if end == 0 { path.append(q) } else { path.insert(q, at: 0) }
                    d = o
                }
            }
            snakes.append(path)
        }
        var idx = [Int](repeating: -1, count: W * H)
        for (i, p) in snakes.enumerated() { for c in p { idx[c.r * W + c.c] = i } }
        for i in snakes.indices {
            if snakes[i].count != 1 { continue }
            let c = snakes[i][0]
            for d in dirL {
                let q = step(c, d)
                guard q.c >= 0, q.r >= 0, q.c < W, q.r < H else { continue }
                let j = idx[q.r * W + q.c]
                if j < 0 || j == i || snakes[j].count < 2 { continue }
                if snakes[j][0] == q {
                    snakes[j].insert(c, at: 0)
                } else if snakes[j][snakes[j].count - 1] == q {
                    snakes[j].append(c)
                } else {
                    continue
                }
                idx[c.r * W + c.c] = j
                snakes[i].removeAll()
                break
            }
        }
        return snakes.filter { $0.count >= 2 }
    }

    static func merge(_ input: [[Cell]], _ rng: Rng, _ targetUnits: Int, _ maxLen: Int, _ W: Int, _ H: Int) throws -> [[Cell]] {
        var snakes = input
        let deltas = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        // the reference's `ends` dict (cell -> [(snake, side)]): snakes are disjoint, so a cell ends at most one snake
        var endAt = [Int32](repeating: -1, count: W * H)
        var pairs: [(Int, Int, Int, Int)] = []
        while snakes.count > targetUnits {
            for k in endAt.indices { endAt[k] = -1 }
            for (i, p) in snakes.enumerated() {
                endAt[p[0].r * W + p[0].c] = Int32(i * 2)
                endAt[p[p.count - 1].r * W + p[p.count - 1].c] = Int32(i * 2 + 1)
            }
            pairs.removeAll(keepingCapacity: true)
            for (i, p) in snakes.enumerated() {
                for (side, c) in [(0, p[0]), (1, p[p.count - 1])] {
                    for dd in deltas {
                        let q = Cell(c.c + dd.0, c.r + dd.1)
                        guard q.c >= 0, q.r >= 0, q.c < W, q.r < H else { continue }
                        let e = Int(endAt[q.r * W + q.c])
                        if e < 0 { continue }
                        let j = e >> 1, sj = e & 1
                        if j > i && p.count + snakes[j].count <= maxLen { pairs.append((i, side, j, sj)) }
                    }
                }
            }
            if pairs.isEmpty { break }
            let (i, si, j, sj) = pairs[try rng.below(pairs.count)]
            let a = si == 1 ? snakes[i] : Array(snakes[i].reversed())
            let b = sj == 0 ? snakes[j] : Array(snakes[j].reversed())
            snakes[i] = a + b
            snakes.remove(at: j)
        }
        return snakes
    }

    // MARK: - preferred heads (reference: plain_peel, Dag, optimise)

    static func plainPeel(_ W: Int, _ H: Int, _ input: [[Cell]], _ rng: Rng) throws -> [(cells: [Cell], dir: Dir)]? {
        var snakes = input
        var owner = [Int32](repeating: -1, count: W * H)
        for (i, p) in snakes.enumerated() { for c in p { owner[c.r * W + c.c] = Int32(i) } }
        var alive = [Bool](repeating: true, count: snakes.count)
        var aliveCount = snakes.count
        // The reference re-tests clear(cells, d, i) for both orientations of every alive snake each round. Here each
        // orientation keeps `own` (its ray meets its own body: blocked for good) and `count` (alive other snakes' cells on
        // its ray); a cell → ray index updates the counts when a snake leaves. clear ⟺ !own && count == 0, the same test.
        var rayOwn: [[Bool]] = [], rayCount: [[Int]] = [], rayDir: [[Dir]] = []
        var version: [UInt32] = []
        var index = [[(snake: Int32, o: UInt8, v: UInt32)]](repeating: [], count: W * H)
        func build(_ i: Int) {
            let p = snakes[i]
            if i == rayOwn.count { rayOwn.append([false, false]); rayCount.append([0, 0]); rayDir.append([.up, .up]); version.append(0) }
            version[i] &+= 1
            for o in 0..<2 {
                let a = o == 0 ? p[p.count - 2] : p[1], h = o == 0 ? p[p.count - 1] : p[0]
                let d = Dir(from: a, to: h)!
                var own = false, count = 0
                var q = step(h, d)
                while q.c >= 0 && q.r >= 0 && q.c < W && q.r < H {
                    let k = q.r * W + q.c
                    let x = Int(owner[k])
                    if x == i { own = true } else if x >= 0 && alive[x] { count += 1 }
                    index[k].append((Int32(i), UInt8(o), version[i]))
                    q = step(q, d)
                }
                rayOwn[i][o] = own; rayCount[i][o] = count; rayDir[i][o] = d
            }
        }
        for i in snakes.indices { build(i) }
        // clear(piece, d, me[, extra]) for the split search: "q in own or q in extra" is "owner[q] == me" there
        func clearFrom(_ head: Cell, _ d: Dir, _ me: Int) -> Bool {
            var q = step(head, d)
            while q.c >= 0 && q.r >= 0 && q.c < W && q.r < H {
                let o = Int(owner[q.r * W + q.c])
                if o >= 0 && (o == me || alive[o]) { return false }
                q = step(q, d)
            }
            return true
        }
        var order: [(cells: [Cell], dir: Dir)] = []
        var cands: [(Int, Int)] = []
        while aliveCount > 0 {
            cands.removeAll(keepingCapacity: true)
            for i in 0..<snakes.count where alive[i] {
                for o in 0..<2 where !rayOwn[i][o] && rayCount[i][o] == 0 { cands.append((i, o)) }
            }
            if cands.isEmpty {
                // the reference tests pieces a = p[:k], reversed(a), b = p[k:], reversed(b) for every cut k; only the
                // HEAD and direction of a piece matter (every cell of the snake blocks), and reversed(a) / b have the
                // same head for every k (the snake's two ends), so they are walked once
                var best: [(Int, Int)] = []
                for i in 0..<snakes.count where alive[i] {
                    let p = snakes[i]
                    if p.count < 4 { continue }
                    let n = p.count
                    let ends = clearFrom(p[0], Dir(from: p[1], to: p[0])!, i) || clearFrom(p[n - 1], Dir(from: p[n - 2], to: p[n - 1])!, i)
                    for k in 2..<(n - 1) {
                        if ends || clearFrom(p[k - 1], Dir(from: p[k - 2], to: p[k - 1])!, i)
                            || clearFrom(p[k], Dir(from: p[k + 1], to: p[k])!, i) {
                            best.append((i, k))
                        }
                    }
                }
                if best.isEmpty { return nil }
                let (i, k) = best[try rng.below(best.count)]
                let p = snakes[i]
                let j = snakes.count
                snakes[i] = Array(p[..<k])
                snakes.append(Array(p[k...]))
                for c in snakes[j] { owner[c.r * W + c.c] = Int32(j) }
                alive.append(true)
                aliveCount += 1
                build(i)
                build(j)
                continue
            }
            let (i, o) = cands[try rng.below(cands.count)]
            alive[i] = false
            aliveCount -= 1
            let p = snakes[i]
            order.append((o == 0 ? p : Array(p.reversed()), rayDir[i][o]))
            for c in p {
                for e in index[c.r * W + c.c] {
                    let s = Int(e.snake)
                    if s != i && alive[s] && e.v == version[s] { rayCount[s][Int(e.o)] -= 1 }
                }
            }
        }
        return order
    }

    /// Dependency DAG of a plain board: an arrow depends on every arrow on its ray (reference: class Dag).
    ///
    /// The reference re-evaluates the whole DAG after every head flip (depth = the longest dependency chain, free = the
    /// arrows with no dependency, None on a cycle). Only the flipped arrow's out-edges change, so this port answers the
    /// same question incrementally: a cycle can only run through the flipped arrow (a new dependency that reaches it —
    /// pruned by depth, since a node that reaches it is strictly deeper in the old DAG), and only its ancestors' depths
    /// can change. The answers are the same numbers; GeneratorTests prove it on every designed level.
    final class Dag {
        /// Both orientations of every arrow (0 = as the plain peel left it, 1 = reversed): cells, direction, whether
        /// that ray meets its own body, and its dependencies (the arrows on the ray) in one flat buffer:
        /// `flat[start[2i+o] ..< start[2i+o+1]]`.
        let cellsO: [[[Cell]]]
        let dirO: [[Dir]]
        let selfO: [Bool]
        let flat: [Int32]
        let start: [Int32]
        var orient: [Int]
        var rdeps: [[Int32]]
        var depth: [Int32]
        var freeCount = 0
        // scratch
        private var stamp: [Int32]
        private var stampNow: Int32 = 0
        private var stack: [Int32] = []
        private var log: [(Int32, Int32)] = []

        var A: [(cells: [Cell], dir: Dir)] { (0..<orient.count).map { (cellsO[$0][orient[$0]], dirO[$0][orient[$0]]) } }

        init(_ arrows: [(cells: [Cell], dir: Dir)], _ W: Int, _ H: Int) {
            var owner = [Int32](repeating: -1, count: W * H)
            for (i, a) in arrows.enumerated() { for c in a.cells { owner[c.r * W + c.c] = Int32(i) } }
            var cO: [[[Cell]]] = [], dO: [[Dir]] = [], sO: [Bool] = [], fl: [Int32] = [], st: [Int32] = [0]
            for (i, a) in arrows.enumerated() {
                let r = Array(a.cells.reversed())
                let rd = Dir(from: r[r.count - 2], to: r[r.count - 1])!
                let cs: [[Cell]] = [a.cells, r], ds: [Dir] = [a.dir, rd]
                for o in 0..<2 {
                    var own = false
                    let s0 = fl.count
                    var q = step(cs[o][cs[o].count - 1], ds[o])
                    while q.c >= 0 && q.r >= 0 && q.c < W && q.r < H {
                        let x = owner[q.r * W + q.c]
                        if x == Int32(i) { own = true } else if x >= 0 && !fl[s0...].contains(x) { fl.append(x) }
                        q = step(q, ds[o])
                    }
                    st.append(Int32(fl.count))
                    sO.append(own)
                }
                cO.append(cs); dO.append(ds)
            }
            cellsO = cO; dirO = dO; selfO = sO; flat = fl; start = st
            let n = arrows.count
            orient = [Int](repeating: 0, count: n)
            rdeps = [[Int32]](repeating: [], count: n)
            depth = [Int32](repeating: 0, count: n)
            stamp = [Int32](repeating: 0, count: n)
        }

        @inline(__always) func depRange(_ i: Int, _ o: Int) -> Range<Int> { Int(start[2 * i + o])..<Int(start[2 * i + o + 1]) }

        /// Full evaluation (the reference `evaluate`): (depth, free) or nil on a cycle; fills `depth`, `rdeps`,
        /// `freeCount` for the incremental steps.
        func evaluate() -> (Int, Int)? {
            let n = orient.count
            if n == 0 { return (0, 0) }
            for i in 0..<n { rdeps[i].removeAll(keepingCapacity: true) }
            var indeg = [Int32](repeating: 0, count: n)
            for i in 0..<n {
                let r = depRange(i, orient[i])
                indeg[i] = Int32(r.count)
                for k in r { rdeps[Int(flat[k])].append(Int32(i)) }
            }
            var queue: [Int32] = []
            queue.reserveCapacity(n)
            var free = 0
            for i in 0..<n where indeg[i] == 0 { queue.append(Int32(i)); free += 1; depth[i] = 1 }
            var head = 0
            var best: Int32 = 0
            while head < queue.count {
                let v = Int(queue[head]); head += 1
                if depth[v] > best { best = depth[v] }
                for u in rdeps[v] {
                    let ui = Int(u)
                    indeg[ui] -= 1
                    if indeg[ui] == 0 { depth[ui] = depthOf(ui, orient[ui]); queue.append(u) }
                }
            }
            if queue.count != n { return nil }
            freeCount = free
            return (Int(best), free)
        }

        @inline(__always) func depthOf(_ u: Int, _ o: Int) -> Int32 {
            flat.withUnsafeBufferPointer { f in
                depth.withUnsafeBufferPointer { dp in
                    var m: Int32 = 0
                    for k in Int(start[2 * u + o])..<Int(start[2 * u + o + 1]) where dp[Int(f[k])] > m { m = dp[Int(f[k])] }
                    return m + 1
                }
            }
        }

        /// Does any dependency in `flat[r]` reach `target`? (old depths prune: a node that reaches `target` is strictly
        /// deeper than it.)
        func reaches(_ r: Range<Int>, _ target: Int) -> Bool {
            let dt = depth[target]
            stampNow &+= 1
            if stampNow == 0 { for k in stamp.indices { stamp[k] = 0 }; stampNow = 1 }
            stack.removeAll(keepingCapacity: true)
            let now = stampNow
            return flat.withUnsafeBufferPointer { f in
                start.withUnsafeBufferPointer { st in
                    depth.withUnsafeBufferPointer { dp in
                        orient.withUnsafeBufferPointer { ori in
                            stamp.withUnsafeMutableBufferPointer { sp in
                                for k in r {
                                    let w = Int(f[k])
                                    if dp[w] > dt && sp[w] != now { sp[w] = now; stack.append(Int32(w)) }
                                }
                                while let v32 = stack.popLast() {
                                    let v = Int(v32)
                                    let o = ori[v]
                                    for k in Int(st[2 * v + o])..<Int(st[2 * v + o + 1]) {
                                        let w = Int(f[k])
                                        if w == target { return true }
                                        if dp[w] > dt && sp[w] != now { sp[w] = now; stack.append(Int32(w)) }
                                    }
                                }
                                return false
                            }
                        }
                    }
                }
            }
        }

        @inline(__always) func unlink(_ i: Int, _ r: Range<Int>) {
            for k in r {
                let w = Int(flat[k])
                let j = rdeps[w].firstIndex(of: Int32(i))!
                rdeps[w].swapAt(j, rdeps[w].count - 1)
                rdeps[w].removeLast()
            }
        }

        /// The reference loop body after `i` was drawn: flip (impossible when the new ray meets the body), evaluate
        /// (a cycle = None), keep when `accept` says so, else undo. Returns whether the flip was kept.
        func tryFlip(_ i: Int, accept: ((Int, Int)) -> Bool) -> Bool {
            let oOld = orient[i], o = 1 - oOld
            if selfO[2 * i + o] { return false }
            let newR = depRange(i, o), oldR = depRange(i, oOld)
            if reaches(newR, i) { return false }
            unlink(i, oldR)
            for k in newR { rdeps[Int(flat[k])].append(Int32(i)) }
            orient[i] = o
            let oldFree = freeCount
            freeCount += (newR.isEmpty ? 1 : 0) - (oldR.isEmpty ? 1 : 0)
            log.removeAll(keepingCapacity: true)
            let nd = depthOf(i, o)
            if nd != depth[i] {
                log.append((Int32(i), depth[i]))
                depth[i] = nd
                stack.removeAll(keepingCapacity: true)
                stack.append(Int32(i))
                while let v = stack.popLast() {
                    for u in rdeps[Int(v)] {
                        let ui = Int(u)
                        let x = depthOf(ui, orient[ui])
                        if x != depth[ui] { log.append((u, depth[ui])); depth[ui] = x; stack.append(u) }
                    }
                }
            }
            var best: Int32 = 0
            for x in depth where x > best { best = x }
            if accept((Int(best), freeCount)) { return true }
            for (u, old) in log.reversed() { depth[Int(u)] = old }
            unlink(i, newR)
            for k in oldR { rdeps[Int(flat[k])].append(Int32(i)) }
            orient[i] = oOld
            freeCount = oldFree
            return false
        }
    }

    static func optimise(_ dag: Dag, _ rng: Rng, R: Int, F: Int, steps: Int) throws {
        guard let cur = dag.evaluate() else { return }
        func cost(_ e: (Int, Int)) -> Double {
            Double(abs(e.0 - R)) / max(1.0, Double(R)) + Double(abs(e.1 - F)) / max(3.0, Double(F))
        }
        var best = cost(cur)
        let n = dag.orient.count
        for _ in 0..<max(0, steps) {
            if best < 0.04 || n == 0 { break }
            let i = try rng.below(n)
            _ = dag.tryFlip(i) { e in
                let c = cost(e)
                if c <= best { best = c; return true }
                return false
            }
        }
    }

    // MARK: - regions (reference: door_layout, box_layout, pipe_shape, plan_regions)

    struct Plan {
        var doors: [Set<Cell>] = []
        var doorStyle: String?
        var boxes: [Set<Cell>] = []
        var boxStyle: String?
        var pipes: [[Cell]] = []
        var feeders: [(cells: [Cell], dir: Dir)] = []
        var tapes: [[(cells: [Cell], dir: Dir)]] = []
        var elevator: Set<Cell>?
        /// Corners in placement order (the reference's plan['corners']: (cell, turn)).
        var corners: [(cell: Cell, turn: CornerTurn)] = []
        /// The margin sides they stand on (plan['corner_sides']; nil = no corner kind in the plan).
        var cornerSides: [String]?
        var used = Set<Cell>()
    }

    // MARK: corners (reference: FACING_TURN, CORNER_SIDES, OPPOSITE, corner_layout)

    /// The margin sides in the reference's order (CORNER_SIDES), shuffled per layout.
    static let cornerSideOrder = ["right", "left", "bottom", "top"]
    static let oppositeSide = ["right": "left", "left": "right", "bottom": "top", "top": "bottom"]

    /// The two turns a corner on `side` may take: FACING_TURN of the side's two facings, in the reference's order
    /// (right (-1,-1) (-1,1); left (1,-1) (1,1); bottom (-1,-1) (1,-1); top (-1,1) (1,1)) with FACING_TURN
    /// (1,-1) downRight, (-1,-1) downLeft, (1,1) upRight, (-1,1) upLeft: the plate faces the board.
    static func cornerFacings(_ side: String) -> [CornerTurn] {
        switch side {
        case "right": return [.downLeft, .upLeft]
        case "left": return [.downRight, .upRight]
        case "bottom": return [.downLeft, .downRight]
        default: return [.upLeft, .upRight]                 // top
        }
    }

    /// Corners on an EMPTY margin line of the board, facing it (v552 L76/L79/L80/L82: 1-3 corners per side beside the arrow
    /// block; a ray leaving the block there turns along the margin, and a second corner can send it back in). One side
    /// with probability 0.6, else two; two sides are ADJACENT (never opposite: a ray can never come back round, so no
    /// corner loop exists). A line excludes both end cells and is skipped when any of its cells is already used.
    /// Returns (sides, the margin cells reserved, corners in placement order).
    static func cornerLayout(_ rng: Rng, _ W: Int, _ H: Int, _ used: Set<Cell>) throws
        -> (sides: [String], margin: Set<Cell>, corners: [(cell: Cell, turn: CornerTurn)]) {
        let nSides = rng.chance(0.6) ? 1 : 2
        var order = cornerSideOrder
        rng.shuffle(&order)
        var margin = Set<Cell>()
        var corners: [(cell: Cell, turn: CornerTurn)] = []
        var sides: [String] = []
        for side in order {
            if sides.count >= nSides { break }
            if let first = sides.first, oppositeSide[side] == first { continue }
            var line: [Cell] = []
            if side == "right" || side == "left" {
                let x = side == "right" ? W - 1 : 0
                if H - 1 > 1 { for r in 1..<(H - 1) { line.append(Cell(x, r)) } }
            } else {
                let y = side == "bottom" ? H - 1 : 0
                if W - 1 > 1 { for c in 1..<(W - 1) { line.append(Cell(c, y)) } }
            }
            if line.count < 3 || line.contains(where: { used.contains($0) || margin.contains($0) }) { continue }
            let k = 1 + (try rng.below(3))
            var picks: [Int] = []
            for _ in 0..<(4 * k) {
                if picks.count >= k { break }
                let i = try rng.below(line.count)
                if !picks.contains(i) { picks.append(i) }
            }
            let facings = cornerFacings(side)
            for i in picks.sorted() {
                corners.append((line[i], facings[try rng.below(2)]))
            }
            margin.formUnion(line)
            sides.append(side)
        }
        return (sides, margin, corners)
    }

    static func doorLayout(_ rng: Rng, _ W: Int, _ H: Int, _ nHint: Int) throws -> (String, [Set<Cell>]) {
        let styles = nHint == 1 ? ["bottomBand", "topBand", "middleBand"]
            : ["stackedBottom", "leftHalf2", "quadrants2", "ring4", "staircase", "twoBottomOneTop", "bottomBand", "topBand"]
        let style = styles[try rng.below(styles.count)]
        let h = max(4, Silhouettes.floorDiv(H * (30 + (try rng.below(20))), 100))
        switch style {
        case "bottomBand": return (style, [rect(0, H - h, W - 1, H - 1)])
        case "topBand": return (style, [rect(0, 0, W - 1, h - 1)])
        case "middleBand":
            let r0 = Silhouettes.floorDiv(H - h, 2)
            return (style, [rect(0, r0, W - 1, r0 + h - 1)])
        case "stackedBottom":
            let h2 = max(4, Silhouettes.floorDiv(h, 2) + 1)
            return (style, [rect(0, H - h2, W - 1, H - 1), rect(0, H - 2 * h2, W - 1, H - h2 - 1)])
        case "leftHalf2":
            let w = max(4, Silhouettes.floorDiv(W, 2))
            return (style, [rect(0, 0, w - 1, Silhouettes.floorDiv(H, 2) - 1), rect(0, Silhouettes.floorDiv(H, 2), w - 1, H - 1)])
        case "quadrants2":
            return (style, [rect(0, 0, Silhouettes.floorDiv(W, 2) - 1, Silhouettes.floorDiv(H, 2) - 1),
                            rect(Silhouettes.floorDiv(W, 2), Silhouettes.floorDiv(H, 2), W - 1, H - 1)])
        case "ring4":
            let t = 4
            return (style, [rect(t + 1, H - t, W - t - 2, H - 1), rect(0, t + 2, t, H - t - 3),
                            rect(W - t - 1, t + 2, W - 1, H - t - 3), rect(t + 1, 0, W - t - 2, t - 1)])
        case "staircase":
            let k = 3 + (try rng.below(3))
            let w = max(4, Silhouettes.floorDiv(W, k))
            var out: [Set<Cell>] = []
            for i in 0..<k {
                let c0 = i * w
                if c0 + 3 >= W { break }
                let c1 = i == k - 1 ? W - 1 : min(W - 1, (i + 1) * w - 1)
                let hh = max(4, Silhouettes.floorDiv(H * (i + 1), k + 1))
                out.append(rect(c0, H - hh, c1, H - 1))
            }
            return (style, out)
        default:                                            // twoBottomOneTop (L37)
            let half = Silhouettes.floorDiv(H, 2)
            return (style, [rect(0, half, Silhouettes.floorDiv(W, 2) - 1, H - 1), rect(Silhouettes.floorDiv(W, 2), half, W - 1, H - 1),
                            rect(0, 0, W - 1, half - 1)])
        }
    }

    static func boxLayout(_ rng: Rng, _ W: Int, _ H: Int) throws -> (String, [Set<Cell>]) {
        let style = ["corner", "bottomBar", "pairCorners", "staircase", "side"][try rng.below(5)]
        switch style {
        case "corner":
            let w = 3 + (try rng.below(6)), h = 3 + (try rng.below(6))
            let c0 = (try rng.below(2)) != 0 ? 0 : W - w
            let r0 = (try rng.below(2)) != 0 ? 0 : H - h
            return (style, [rect(c0, r0, c0 + w - 1, r0 + h - 1)])
        case "bottomBar":
            return (style, [rect(0, H - 3, W - 1, H - 1)])
        case "pairCorners":
            let w = 3 + (try rng.below(5)), h = 3 + (try rng.below(5))
            return (style, [rect(0, 0, w - 1, h - 1), rect(W - w, H - h, W - 1, H - 1)])
        case "staircase":
            let k = 3 + (try rng.below(2))
            let w = max(3, Silhouettes.floorDiv(W, k + 1))
            return (style, (0..<k).map { i in rect(W - (k - i) * w, H - 3 * (i + 1), W - (k - i) * w + w - 1, H - 1) })
        default:                                            // side
            let w = 3, h = 3 + (try rng.below(4))
            let c0 = (try rng.below(2)) != 0 ? 0 : W - w
            let r0 = Silhouettes.floorDiv(H - h, 2)
            return (style, [rect(c0, r0, c0 + w - 1, r0 + h - 1)])
        }
    }

    static func pipeShape(_ rng: Rng, _ W: Int, _ H: Int) throws -> (String, [Cell]) {
        let kind = ["capTop", "uSide", "uBottom", "lCorner"][try rng.below(4)]
        switch kind {
        case "capTop":
            let w = 4 + (try rng.below(3)), h = 4 + (try rng.below(2))
            let c0 = try rng.below(max(1, W - w))
            var p: [Cell] = []
            for r in stride(from: h - 1, through: 0, by: -1) { p.append(Cell(c0, r)) }
            for c in (c0 + 1)..<(c0 + w) { p.append(Cell(c, 0)) }
            for r in 1..<h { p.append(Cell(c0 + w - 1, r)) }
            return (kind, p)
        case "uSide":
            let w = 4, h = 5
            let left = (try rng.below(2)) == 0
            let c0 = left ? 0 : W - w
            let r0 = 1 + (try rng.below(max(1, H - h - 1)))
            var p: [Cell] = []
            if left {
                for i in 0..<w { p.append(Cell(c0 + w - 1 - i, r0)) }
                for i in 1..<h { p.append(Cell(c0, r0 + i)) }
                for i in 1..<w { p.append(Cell(c0 + i, r0 + h - 1)) }
            } else {
                for i in 0..<w { p.append(Cell(c0 + i, r0)) }
                for i in 1..<h { p.append(Cell(c0 + w - 1, r0 + i)) }
                for i in 1..<w { p.append(Cell(c0 + w - 1 - i, r0 + h - 1)) }
            }
            return (kind, p)
        case "uBottom":
            let w = 3 + (try rng.below(4)), h = 4
            let c0 = try rng.below(max(1, W - w))
            let r1 = H - 1
            var p: [Cell] = []
            for i in 0..<h { p.append(Cell(c0, r1 - h + 1 + i)) }
            for c in (c0 + 1)..<(c0 + w) { p.append(Cell(c, r1)) }
            for i in 1..<h { p.append(Cell(c0 + w - 1, r1 - i)) }
            return (kind, p)
        default:                                            // lCorner
            let w = 5 + (try rng.below(4)), h = 6 + (try rng.below(5))
            var p: [Cell] = []
            for i in 0..<w { p.append(Cell(W - w + i, 0)) }
            for r in 1..<h { p.append(Cell(W - 1, r)) }
            return (kind, p)
        }
    }

    static func inGrid(_ c: Cell, _ W: Int, _ H: Int) -> Bool { c.c >= 0 && c.r >= 0 && c.c < W && c.r < H }

    static func planRegions(_ rng: Rng, _ W: Int, _ H: Int, _ kinds: [String]) throws -> Plan {
        var plan = Plan()
        func fits<S: Sequence>(_ cells: S) -> Bool where S.Element == Cell {
            cells.allSatisfy { inGrid($0, W, H) && !plan.used.contains($0) }
        }
        func disjoint(_ rects: [Set<Cell>]) -> Bool {
            for i in rects.indices { for j in (i + 1)..<rects.count where !rects[i].isDisjoint(with: rects[j]) { return false } }
            return true
        }
        for k in kinds {
            switch k {
            case "door":
                let nHint = rng.chance(0.4) ? 1 : 2
                var ok = false
                for _ in 0..<4 {
                    let (style, all) = try doorLayout(rng, W, H, nHint)
                    let rects = all.filter { $0.count >= 16 }
                    if !rects.isEmpty && rects.allSatisfy({ fits($0) }) && disjoint(rects) {
                        plan.doors = rects
                        plan.doorStyle = style
                        for r in rects { plan.used.formUnion(r) }
                        ok = true
                        break
                    }
                }
                if !ok { throw Fail("door layout") }
            case "elevator":
                var ok = false
                for _ in 0..<8 {
                    let w = min(W - 2, 6 + (try rng.below(7)))
                    let h = min(H - 2, 4 + (try rng.below(4)))
                    let c0 = 1 + (try rng.below(max(1, W - w - 1)))
                    let r0 = 1 + (try rng.below(max(1, H - h - 1)))
                    let R = rect(c0, r0, c0 + w - 1, r0 + h - 1)
                    if fits(R) {
                        plan.elevator = R
                        plan.used.formUnion(R)
                        ok = true
                        break
                    }
                }
                if !ok { throw Fail("elevator layout") }
            case "box":
                var ok = false
                for _ in 0..<6 {
                    let (style, rects) = try boxLayout(rng, W, H)
                    if !rects.isEmpty && rects.allSatisfy({ fits($0) }) && disjoint(rects) {
                        plan.boxes = rects
                        plan.boxStyle = style
                        for r in rects { plan.used.formUnion(r) }
                        ok = true
                        break
                    }
                }
                if !ok { throw Fail("box layout") }
            case "pipe":
                let want = 1 + (rng.chance(0.4) ? 1 : 0) + (rng.chance(0.15) ? 1 : 0)
                for _ in 0..<(10 * want) {
                    if plan.pipes.count >= want { break }
                    let (_, path) = try pipeShape(rng, W, H)
                    if Set(path).count != path.count || !fits(path) { continue }
                    // the mouths must face a board cell that is free for arrows
                    var okm = true
                    for (m, prev) in [(path[0], path[1]), (path[path.count - 1], path[path.count - 2])] {
                        let out = Dir(from: prev, to: m)!
                        let q = step(m, out)
                        if !inGrid(q, W, H) || plan.used.contains(q) { okm = false }
                    }
                    if !okm { continue }
                    // FEEDERS in front of ONE mouth, pointing into it; the other mouth's lane stays free
                    let entry = try rng.below(2)
                    let (m, prev) = entry == 0 ? (path[0], path[1]) : (path[path.count - 1], path[path.count - 2])
                    let out = Dir(from: prev, to: m)!
                    let wantPass = [2, 3, 3, 4, 4, 5][try rng.below(6)]
                    var lane: [Cell] = []
                    let pathSet = Set(path)
                    var q = step(m, out)
                    while inGrid(q, W, H) && !plan.used.contains(q) && !pathSet.contains(q) {
                        lane.append(q)
                        q = step(q, out)
                    }
                    var feeders: [(cells: [Cell], dir: Dir)] = []
                    var kk = 0
                    while feeders.count < wantPass {
                        let L = 2 + (try rng.below(3))
                        if kk + L > lane.count { break }
                        let seg = Array(lane[kk..<(kk + L)])              // nearest the mouth first
                        feeders.append((Array(seg.reversed()), out.opposite))  // tail far, head next to the mouth
                        kk += L
                    }
                    if feeders.isEmpty { continue }
                    plan.pipes.append(path)
                    plan.feeders.append(contentsOf: feeders)
                    plan.used.formUnion(path)
                    for f in feeders { plan.used.formUnion(f.cells) }
                }
                if plan.pipes.isEmpty { throw Fail("pipe layout") }
            case "tape":
                let want = 1 + (try rng.below(4))
                for _ in 0..<(8 * want) {
                    if plan.tapes.count >= want { break }
                    let lanes = 2 + (try rng.below(3))
                    let L = rng.chance(0.75) ? 4 : 3
                    let d = dirL[try rng.below(4)]
                    let horiz = d == .left || d == .right
                    let (bw, bh) = horiz ? (L, lanes) : (lanes, L)
                    if bw > W || bh > H { continue }
                    let c0 = try rng.below(W - bw + 1)
                    let r0 = try rng.below(H - bh + 1)
                    let R = rect(c0, r0, c0 + bw - 1, r0 + bh - 1)
                    if !fits(R) { continue }
                    var members: [(cells: [Cell], dir: Dir)] = []
                    for lane in 0..<lanes {
                        var cells: [Cell]
                        if horiz {
                            cells = (0..<L).map { Cell(c0 + $0, r0 + lane) }
                            if d == .left { cells.reverse() }
                        } else {
                            cells = (0..<L).map { Cell(c0 + lane, r0 + $0) }
                            if d == .up { cells.reverse() }
                        }
                        members.append((cells, d))
                    }
                    plan.tapes.append(members)
                    plan.used.formUnion(R)
                }
                if plan.tapes.isEmpty { throw Fail("tape layout") }
            case "corner":
                let (sides, margin, corners) = try cornerLayout(rng, W, H, plan.used)
                if corners.isEmpty { throw Fail("corner layout") }
                plan.corners = corners
                plan.cornerSides = sides
                plan.used.formUnion(margin)
            default:
                break
            }
        }
        return plan
    }

    // MARK: - the obstacle-aware peel (reference: class Peel)

    struct Opt {
        var oriented: (cells: [Cell], dir: Dir)?
        var passes: [Int]
    }

    final class Peel {
        let W: Int, H: Int
        let rng: Rng
        let plan: Plan
        var U: [GUnit?]
        var alive: [Bool]
        var pref: [[Cell]?]                     // the unit's preferred oriented cells (reference: prefs[frozenset])
        let prefs: [[Int]: [Cell]]
        let nd: Int
        var doorOpen: [Bool]
        var riders: [Int?]
        var doorCell: [Int32]
        var boxCell: [Int32]
        var boxBroken: [Bool]
        var boxC: [Int?]
        var pipeCell: [Int32]
        var pipeEndPipe: [Int32]
        var pipeEndOut: [Dir?]
        var pipeEnds: [[(Cell, Dir)]]
        var pipeBroken: [Bool]
        var pipePass: [Int]
        var pipeC: [Int?]
        /// flat cell → the corner's turn (the reference's `self.corner`); corners never change state.
        var cornerAt: [CornerTurn?]
        var elevActive = false
        var occ1: [Int32]
        var occ2: [Int32]
        var count = 0
        let totalVisible: Int
        var orient: [Int: (cells: [Cell], dir: Dir)] = [:]
        var witness: [Int] = []
        var nextID: Int
        var hasPlat: Bool
        /// options(i) cached until a cell its rays examined changes state (the reference recomputes every step).
        var optCache: [[Opt]?]
        var watch: [[Int32]]
        var touched: [Int32] = []

        init(_ W: Int, _ H: Int, _ units: [Int: GUnit], _ plan: Plan, _ rng: Rng, _ prefs: [[Int]: [Cell]], _ totalVisible: Int) {
            self.W = W; self.H = H; self.rng = rng; self.plan = plan; self.prefs = prefs
            self.totalVisible = totalVisible
            let top = (units.keys.max() ?? -1) + 1
            nextID = top
            U = [GUnit?](repeating: nil, count: top)
            alive = [Bool](repeating: false, count: top)
            pref = [[Cell]?](repeating: nil, count: top)
            for (i, u) in units {
                U[i] = u
                alive[i] = true
                if u.kind == .snake { pref[i] = prefs[Generator.cellKey(u.cells, W)] }
            }
            hasPlat = units.values.contains { $0.region == .plat }
            nd = plan.doors.count
            doorOpen = [Bool](repeating: false, count: nd)
            riders = [Int?](repeating: nil, count: nd)
            let size = W * H
            doorCell = [Int32](repeating: -1, count: size)
            for (k, R) in plan.doors.enumerated() { for c in R { doorCell[c.r * W + c.c] = Int32(k) } }
            boxCell = [Int32](repeating: -1, count: size)
            for (j, R) in plan.boxes.enumerated() { for c in R { boxCell[c.r * W + c.c] = Int32(j) } }
            boxBroken = [Bool](repeating: false, count: plan.boxes.count)
            boxC = [Int?](repeating: nil, count: plan.boxes.count)
            pipeCell = [Int32](repeating: -1, count: size)
            pipeEndPipe = [Int32](repeating: -1, count: size)
            pipeEndOut = [Dir?](repeating: nil, count: size)
            pipeEnds = []
            for (p, path) in plan.pipes.enumerated() {
                for c in path { pipeCell[c.r * W + c.c] = Int32(p) }
                let e0 = (path[0], Dir(from: path[1], to: path[0])!)
                let e1 = (path[path.count - 1], Dir(from: path[path.count - 2], to: path[path.count - 1])!)
                pipeEndPipe[e0.0.r * W + e0.0.c] = Int32(p); pipeEndOut[e0.0.r * W + e0.0.c] = e0.1
                pipeEndPipe[e1.0.r * W + e1.0.c] = Int32(p); pipeEndOut[e1.0.r * W + e1.0.c] = e1.1
                pipeEnds.append([e0, e1])
            }
            pipeBroken = [Bool](repeating: false, count: plan.pipes.count)
            pipePass = [Int](repeating: 0, count: plan.pipes.count)
            pipeC = [Int?](repeating: nil, count: plan.pipes.count)
            cornerAt = [CornerTurn?](repeating: nil, count: size)
            for x in plan.corners { cornerAt[x.cell.r * W + x.cell.c] = x.turn }
            occ1 = [Int32](repeating: -1, count: size)
            occ2 = occ1
            optCache = [[Opt]?](repeating: nil, count: top)
            watch = [[Int32]](repeating: [], count: size)
            for (i, u) in units {
                for c in u.allCells {
                    if u.layer == 1 { occ1[c.r * W + c.c] = Int32(i) } else { occ2[c.r * W + c.c] = Int32(i) }
                }
            }
        }

        func visible(_ i: Int) -> Bool {
            switch U[i]!.region {
            case .door(let k): return doorOpen[k]
            case .l2: return elevActive
            default: return true
            }
        }

        func blocked(_ k: Int, _ me: Int) -> Bool {
            let d = Int(doorCell[k])
            if d >= 0 && !doorOpen[d] { return true }
            let b = Int(boxCell[k])
            if b >= 0 && !boxBroken[b] { return true }
            let o1 = Int(occ1[k])
            if o1 >= 0 && o1 != me && alive[o1] { return true }
            let o2 = Int(occ2[k])
            if o2 >= 0 && o2 != me && alive[o2] && elevActive { return true }
            return false
        }

        /// (clear?, passages). `wholeUnit`: every cell of unit `me` blocks (a snake's own body, or a split piece plus
        /// the half that stays); else only `own` (a bundle member's own cells) does.
        func ray(_ own: [Cell], _ d0: Dir, _ me: Int, wholeUnit: Bool, record: Bool = false) -> (Bool, [Int]) {
            var c = own[own.count - 1]
            var d = d0
            var passages: [Int] = []
            var hops = 0
            let layerOcc = U[me]!.layer == 1 ? occ1 : occ2
            while true {
                let q = Cell(c.c + d.dc, c.r + d.dr)
                if q.c < 0 || q.r < 0 || q.c >= W || q.r >= H { return (true, passages) }
                let k = q.r * W + q.c
                if record { touched.append(Int32(k)) }
                let p = Int(pipeCell[k])
                if p >= 0 && !pipeBroken[p] {
                    if pipeEndPipe[k] == Int32(p), let out = pipeEndOut[k], out == d.opposite, hops < ContentRules.maxHops {
                        hops += 1
                        passages.append(p)
                        let other = pipeEnds[p][1].0 == q ? pipeEnds[p][0] : pipeEnds[p][1]
                        c = other.0
                        d = other.1
                        continue
                    }
                    return (false, passages)
                }
                if let t = cornerAt[k] {                     // arrowcore.walk: a corner turns the ray or blocks it
                    guard let nd = ContentRules.cornerTurn(t, d), hops < ContentRules.maxHops else { return (false, passages) }
                    hops += 1
                    c = q
                    d = nd
                    continue
                }
                if layerOcc[k] == Int32(me) && (wholeUnit || own.contains(q)) { return (false, passages) }
                if blocked(k, me) { return (false, passages) }
                c = q
            }
        }

        /// `ray(piece, d, me, wholeUnit: true).0` for a piece whose head is `head` (the cells before it only matter as
        /// cells of `me`, which all block).
        func rayClear(_ head: Cell, _ d0: Dir, _ me: Int) -> Bool {
            var c = head
            var d = d0
            var hops = 0
            let layerOcc = U[me]!.layer == 1 ? occ1 : occ2
            while true {
                let q = Cell(c.c + d.dc, c.r + d.dr)
                if q.c < 0 || q.r < 0 || q.c >= W || q.r >= H { return true }
                let k = q.r * W + q.c
                let p = Int(pipeCell[k])
                if p >= 0 && !pipeBroken[p] {
                    if pipeEndPipe[k] == Int32(p), let out = pipeEndOut[k], out == d.opposite, hops < ContentRules.maxHops {
                        hops += 1
                        let other = pipeEnds[p][1].0 == q ? pipeEnds[p][0] : pipeEnds[p][1]
                        c = other.0
                        d = other.1
                        continue
                    }
                    return false
                }
                if let t = cornerAt[k] {
                    guard let nd = ContentRules.cornerTurn(t, d), hops < ContentRules.maxHops else { return false }
                    hops += 1
                    c = q
                    d = nd
                    continue
                }
                if layerOcc[k] == Int32(me) || blocked(k, me) { return false }
                c = q
            }
        }

        func options(_ i: Int) -> [Opt] {
            if let o = optCache[i] { return o }
            touched.removeAll(keepingCapacity: true)
            let out = computeOptions(i)
            for k in touched { watch[Int(k)].append(Int32(i)) }
            optCache[i] = out
            return out
        }

        func computeOptions(_ i: Int) -> [Opt] {
            let u = U[i]!
            if u.kind != .snake {
                var passes: [Int] = []
                for m in u.members {
                    let (ok, ps) = ray(m.cells, m.dir, i, wholeUnit: false, record: true)
                    if !ok { return [] }
                    passes += ps
                }
                return [Opt(oriented: nil, passes: passes)]
            }
            var out: [Opt] = []
            for cells in [u.cells, Array(u.cells.reversed())] {
                let d = Dir(from: cells[cells.count - 2], to: cells[cells.count - 1])!
                let (ok, ps) = ray(cells, d, i, wholeUnit: true, record: true)
                if ok { out.append(Opt(oriented: (cells, d), passes: ps)) }
            }
            return out
        }

        /// A cell's blocking state changed: every cached option list that examined it is recomputed on next use.
        @inline(__always) func mark(_ k: Int) {
            for u in watch[k] { optCache[Int(u)] = nil }
            watch[k].removeAll(keepingCapacity: true)
        }
        func mark<S: Sequence>(_ cells: S) where S.Element == Cell { for c in cells { mark(c.r * W + c.c) } }

        func candidates() -> [(Int, [Opt])] {
            var res: [(Int, [Opt])] = []
            for i in 0..<U.count where alive[i] && visible(i) {
                let opts = options(i)
                if !opts.isEmpty { res.append((i, opts)) }
            }
            return res
        }

        func anyCandidate() -> Bool {
            for i in 0..<U.count where alive[i] && visible(i) { if !options(i).isEmpty { return true } }
            return false
        }

        func remove(_ i: Int, _ opt: Opt) {
            if let o = opt.oriented { orient[i] = o }
            alive[i] = false
            witness.append(i)
            let u = U[i]!
            count += u.kind == .snake ? 1 : u.members.count
            for p in opt.passes { pipePass[p] += 1 }
            mark(u.allCells)
            for k in 0..<nd where riders[k] == i { doorOpen[k] = true; mark(plan.doors[k]) }
            if hasPlat && !elevActive {
                var anyAlive = false
                for x in 0..<U.count where alive[x] && U[x]?.region == .plat { anyAlive = true; break }
                if !anyAlive { elevActive = true; if let e = plan.elevator { mark(e) } }
            }
        }

        func split() throws -> Bool {
            var best: [(Int, Int)] = []
            for i in 0..<U.count where alive[i] {
                let u = U[i]!
                if u.kind != .snake || !visible(i) { continue }
                let p = u.cells
                if p.count < 4 { continue }
                // as in plainPeel: only the piece's head and direction matter (the whole snake blocks), and two of the
                // four pieces have the snake's ends as heads for every cut
                let n = p.count
                let ends = rayClear(p[0], Dir(from: p[1], to: p[0])!, i) || rayClear(p[n - 1], Dir(from: p[n - 2], to: p[n - 1])!, i)
                for k in 2..<(n - 1) {
                    if ends || rayClear(p[k - 1], Dir(from: p[k - 2], to: p[k - 1])!, i)
                        || rayClear(p[k], Dir(from: p[k + 1], to: p[k])!, i) {
                        best.append((i, k))
                    }
                }
            }
            if best.isEmpty { return false }
            let (i, k) = best[try rng.below(best.count)]
            var u = U[i]!
            let p = u.cells
            let j = nextID
            nextID += 1
            let piece = GUnit(kind: .snake, cells: Array(p[k...]), members: [], region: u.region, layer: u.layer)
            u.cells = Array(p[..<k])
            U[i] = u
            pref[i] = prefs[Generator.cellKey(u.cells, W)]
            U.append(piece)
            alive.append(true)
            pref.append(prefs[Generator.cellKey(piece.cells, W)])
            optCache[i] = nil
            optCache.append(nil)
            for c in piece.cells {
                if u.layer == 1 { occ1[c.r * W + c.c] = Int32(j) } else { occ2[c.r * W + c.c] = Int32(j) }
            }
            return true
        }

        /// Nothing can move: break the box or pipe whose break frees something (counter = the count so far).
        func tryBreak() -> Bool {
            for j in 0..<boxBroken.count {
                if boxBroken[j] || count < 1 { continue }
                boxBroken[j] = true
                mark(plan.boxes[j])
                if anyCandidate() { boxC[j] = count; return true }
                boxBroken[j] = false
                mark(plan.boxes[j])
            }
            for p in 0..<pipeBroken.count {
                if pipeBroken[p] || pipePass[p] < 1 { continue }
                pipeBroken[p] = true
                mark(plan.pipes[p])
                if anyCandidate() { pipeC[p] = pipePass[p]; return true }
                pipeBroken[p] = false
                mark(plan.pipes[p])
            }
            return false
        }

        func run() throws {
            var guardCount = 0
            while alive.contains(true) {
                guardCount += 1
                if guardCount > 6000 { throw Fail("peel guard") }
                var cands = candidates()
                if cands.isEmpty {
                    if tryBreak() { continue }
                    if try split() { continue }
                    throw Fail("peel stuck")
                }
                // moves that keep a snake's PREFERRED head come first
                var prefd: [(Int, [Opt])] = []
                for (i, opts) in cands {
                    let u = U[i]!
                    if u.kind != .snake { prefd.append((i, opts)); continue }
                    let pc = pref[i]
                    let po = pc == nil ? [] : opts.filter { $0.oriented!.cells == pc! }
                    if !po.isEmpty || pc == nil { prefd.append((i, po.isEmpty ? opts : po)) }
                }
                if !prefd.isEmpty { cands = prefd }
                // a key rider for the next locked door
                if let nxt = riders.firstIndex(where: { $0 == nil }) {
                    let thr = Silhouettes.floorDiv(totalVisible * (5 + 18 * nxt), 100)
                    let snakes = cands.filter { U[$0.0]!.kind == .snake }
                    if !snakes.isEmpty && (count >= thr || cands.count <= 2) {
                        var pool = snakes
                        if nxt > 0 && rng.chance(0.5) {
                            let prev = snakes.filter { U[$0.0]!.region == .door(nxt - 1) }
                            if !prev.isEmpty { pool = prev }
                        }
                        let (i, opts) = pool[try rng.below(pool.count)]
                        riders[nxt] = i
                        remove(i, try pickOption(i, opts))
                        continue
                    }
                }
                let piped = cands.filter { c in c.1.contains { !$0.passes.isEmpty } }
                var chosen: (Int, [Opt])
                if !piped.isEmpty && rng.chance(0.6) {
                    chosen = piped[try rng.below(piped.count)]
                    let withPasses = chosen.1.filter { !$0.passes.isEmpty }
                    if !withPasses.isEmpty { chosen.1 = withPasses }
                } else {
                    chosen = cands[try rng.below(cands.count)]
                }
                remove(chosen.0, try pickOption(chosen.0, chosen.1))
            }
        }

        func pickOption(_ i: Int, _ opts: [Opt]) throws -> Opt {
            if opts.count == 1 { return opts[0] }
            if U[i]!.kind == .snake, let p = pref[i] {
                for o in opts where o.oriented!.cells == p { return o }
            }
            return opts[try rng.below(opts.count)]
        }
    }

    // MARK: - assembly (reference: key_cells, assemble, crop, renumber)

    static func keyCells(_ cells: [Cell]) -> [Cell] {
        // the reference's loop returns at i == 0: the rider's first two cells
        for i in 0..<(cells.count - 1) {
            if i == 0 || Dir(from: cells[i - 1], to: cells[i]) == Dir(from: cells[i], to: cells[i + 1]) {
                return [cells[i], cells[i + 1]]
            }
        }
        return [cells[0], cells[1]]
    }

    struct RawArrow { var id: Int; var cells: [Cell]; var dir: Dir; var hiddenBy: String?; var layer: Int }
    struct RawObstacle {
        var id: String; var kind: ObstacleKind; var cells: [Cell]; var arrows: [Int]? = nil; var ends: [PipeEnd]? = nil
        var counter: Int? = nil; var counterAt: [Double]? = nil; var order: Int? = nil; var reveals: [Int]? = nil
        var turn: CornerTurn? = nil
    }

    static func assemble(_ peel: Peel, _ plan: Plan, _ tgt: Target, _ curve: CurveSpec, _ rng: Rng, _ notes: Notes)
        throws -> (LevelSpec, ContentRules.Measured, Notes) {
        var arrows: [RawArrow] = []
        var obst: [RawObstacle] = []
        var ids: [Int: Int] = [:]
        var nid = 0
        var tapes: [(cells: [Cell], arrows: [Int])] = []
        var platform: [Int] = [], l2: [Int] = []
        var doorReveals = [[Int]](repeating: [], count: peel.nd)
        for i in peel.witness {
            let u = peel.U[i]!
            if u.kind == .fixed {
                let m = u.members[0]
                arrows.append(RawArrow(id: nid, cells: m.cells, dir: m.dir, hiddenBy: nil, layer: 1))
                ids[i] = nid
                nid += 1
                continue
            }
            if u.kind == .bundle {
                var mids: [Int] = []
                for m in u.members {
                    arrows.append(RawArrow(id: nid, cells: m.cells, dir: m.dir, hiddenBy: nil, layer: 1))
                    mids.append(nid)
                    nid += 1
                }
                tapes.append((u.members.map { $0.cells[$0.cells.count - 2] }, mids))
                continue
            }
            guard let o = peel.orient[i] else { throw Fail("unoriented snake") }
            var rec = RawArrow(id: nid, cells: o.cells, dir: o.dir, hiddenBy: nil, layer: 1)
            switch u.region {
            case .door(let k):
                rec.hiddenBy = "d\(k)"
                doorReveals[k].append(nid)
            case .l2:
                rec.hiddenBy = "e0"
                rec.layer = 2
                l2.append(nid)
            case .plat:
                platform.append(nid)
            case .out:
                break
            }
            ids[i] = nid
            arrows.append(rec)
            nid += 1
        }
        func sortedCells(_ R: Set<Cell>) -> [Cell] { R.sorted { ($0.c, $0.r) < ($1.c, $1.r) } }
        for (t, tp) in tapes.enumerated() {
            obst.append(RawObstacle(id: "t\(t)", kind: .tape, cells: tp.cells, arrows: tp.arrows))
        }
        for (k, R) in plan.doors.enumerated() {
            var rec = RawObstacle(id: "d\(k)", kind: .door, cells: sortedCells(R), order: k)
            if !doorReveals[k].isEmpty { rec.reveals = doorReveals[k].sorted() }
            obst.append(rec)
        }
        for k in 0..<peel.nd {
            guard let r = peel.riders[k], let rider = ids[r] else { throw Fail("door \(k) has no rider") }
            let rc = arrows.first { $0.id == rider }!.cells
            obst.append(RawObstacle(id: "k\(k)", kind: .key, cells: keyCells(rc), arrows: [rider]))
        }
        for (p, path) in plan.pipes.enumerated() {
            if peel.pipePass[p] < 1 { throw Fail("unused pipe") }
            let C = peel.pipeC[p] ?? peel.pipePass[p]
            if C > 9 { throw Fail("pipe counter \(C)") }
            let ends = [PipeEnd(cell: path[0], out: Dir(from: path[1], to: path[0])!),
                        PipeEnd(cell: path[path.count - 1], out: Dir(from: path[path.count - 2], to: path[path.count - 1])!)]
            obst.append(RawObstacle(id: "p\(p)", kind: .pipe, cells: path, ends: ends, counter: C,
                                    counterAt: [Double(path[0].c + path[1].c) / 2.0, Double(path[0].r + path[1].r) / 2.0]))
        }
        let total = arrows.count
        for (j, R) in plan.boxes.enumerated() {
            var C: Int
            if let c = peel.boxC[j] {
                C = c
            } else {                                        // never needed: breaks late (55-95 % of the level)
                C = max(1, Silhouettes.floorDiv(total * (55 + (try rng.below(41))), 100))
                C = min(C, total - 1)
            }
            obst.append(RawObstacle(id: "b\(j)", kind: .box, cells: sortedCells(R), counter: C))
        }
        if let E = plan.elevator {
            obst.append(RawObstacle(id: "e0", kind: .elevator, cells: sortedCells(E), arrows: platform.sorted(), reveals: l2.sorted()))
        }
        for (i, x) in plan.corners.enumerated() {
            obst.append(RawObstacle(id: "x\(i)", kind: .corner, cells: [x.cell], turn: x.turn))
        }
        // crop
        var xs: [Int] = [], ys: [Int] = []
        for a in arrows { for c in a.cells { xs.append(c.c); ys.append(c.r) } }
        for o in obst { for c in o.cells { xs.append(c.c); ys.append(c.r) } }
        let c0 = xs.min()!, r0 = ys.min()!
        func sh(_ c: Cell) -> Cell { Cell(c.c - c0, c.r - r0) }
        for i in arrows.indices { arrows[i].cells = arrows[i].cells.map(sh) }
        for i in obst.indices {
            obst[i].cells = obst[i].cells.map(sh)
            if let e = obst[i].ends { obst[i].ends = e.map { PipeEnd(cell: sh($0.cell), out: $0.out) } }
            if let at = obst[i].counterAt { obst[i].counterAt = [at[0] - Double(c0), at[1] - Double(r0)] }
        }
        let cols = xs.max()! - c0 + 1, rows = ys.max()! - r0 + 1
        // renumber: visible arrows in reading order of their heads, then the hidden ones by hider
        let order = stableSorted(arrows) { a, b in
            let ka = (a.hiddenBy == nil ? 0 : 1, a.hiddenBy ?? "", a.cells[a.cells.count - 1].r, a.cells[a.cells.count - 1].c)
            let kb = (b.hiddenBy == nil ? 0 : 1, b.hiddenBy ?? "", b.cells[b.cells.count - 1].r, b.cells[b.cells.count - 1].c)
            return ka < kb
        }
        var m: [Int: Int] = [:]
        for (i, a) in order.enumerated() { m[a.id] = i }
        let specArrows = order.enumerated().map { i, a in
            ArrowSpec(id: ArrowID(i), cells: a.cells, dir: a.dir, layer: a.layer, hiddenBy: a.hiddenBy.map { ObstacleID($0) })
        }
        let specObstacles = obst.map { o -> ObstacleSpec in
            ObstacleSpec(id: ObstacleID(o.id), kind: o.kind, cells: o.cells,
                         arrows: (o.arrows ?? []).map { m[$0]! }.sorted().map { ArrowID($0) },
                         ends: o.ends ?? [], counter: o.counter, counterAt: o.counterAt, order: o.order, turn: o.turn,
                         reveals: (o.reveals ?? []).map { m[$0]! }.sorted().map { ArrowID($0) })
        }
        var lvl = LevelSpec(level: tgt.n, source: .designed, capture: nil, cols: cols, rows: rows, mask: nil, timerSeconds: 180,
                            hearts: 3, tag: tgt.tag, arrows: specArrows, obstacles: specObstacles)
        let probs = ContentRules.structuralProblems(lvl)
        if let p = probs.first { throw Fail("structure: " + p) }
        let s = RefStatic(lvl)
        // On a monotone board (no pipe, elevator or corner; hidden arrows lie inside their hiders, as every generated
        // one does) an exit only ever frees cells, so every removal order reaches the same end: the greedy solves it
        // exactly when the waves do (computed below anyway). Otherwise the reference greedy runs.
        let monotone = s.pipes.isEmpty && s.elevators.isEmpty && !lvl.obstacles.contains { $0.kind == .corner }
        let waves = ContentRules.waves(RefBoard(s))
        if monotone ? !waves.ok : !ContentRules.greedy(RefBoard(s)).ok { throw Fail("greedy stuck") }
        let doors = peel.nd
        // the reference computes the full metrics here but only reads `_units` (arrows minus the tape extras)
        let units = lvl.arrows.count - lvl.obstacles.filter { $0.kind == .tape }.reduce(0) { $0 + ($1.arrows.count - 1) }
        lvl.timerSeconds = timerFor(curve, tgt.tag, units: units, doors: doors, rng, templateTimer: tgt.templateTimer)
        let m1 = ContentRules.metrics(lvl, board: RefBoard(s), waves: waves)   // the tables do not depend on the timer
        if m1.botTimeLeft < 0.2 * Double(lvl.timerSeconds) { throw Fail("time") }
        return (lvl, m1, notes)
    }
}

extension Silhouettes {
    /// Python's `%` for a positive modulus.
    @inline(__always) static func floorMod(_ a: Int, _ b: Int) -> Int { a - floorDiv(a, b) * b }
}
