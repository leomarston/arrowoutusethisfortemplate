import Foundation
import PathCore

// `lvtool endless [--levels App/Resources/Levels] [--from 151] [--count 1000] [--rules App/Resources/Tuning/rules.json]
//                 [--art art/ui/out] [--jobs 3] [--report F.json] [--out F.jsonl] [--no-rerun]`
//
// CONTENT (L2) tests of the ENDLESS levels, the ones the game generates past the authored end (SPEC-gameplay §14.2-§14.3,
// SPEC-architecture D9 / §4.14; CONSISTENCY L-7, L-8, O-21, O-23). Every level n of the range is taken exactly as the game
// serves it: `LevelProvider.produce(n, curve: library.curve, library:, options: Validator.Options())` on the BUNDLED
// content (App/Resources/Levels incl. curve.json), i.e. what a `LevelProvider(library:)` hands the board. Then:
//   solvable      CONTENT's own §14.4 list on C2's rules with the SHIPPED rules.json (`checkLevel`, the gate L1 runs on
//                 L1-L150: structure, obstacles, C2 greedy clears it, every obstacle used, no dead end in 40 random orders
//                 on non-monotone boards, the HeadlessDriver wins at 0.6 s/tap with >= 20 % of the timer and 0 bumps,
//                 metrics = recomputed) + C4's exact search (`Solver.solve` = .solved); never the fallback route (that
//                 would be a renumbered authored board, i.e. a repeat and stand-in content).
//   curve-fitted  C4's `Difficulty.assess` inside its bands (cadence tag, the tag's timer, grid inside the target and the
//                 cap, units / waves / free-at-start against the curve target, time share); independently here: the tag
//                 of position n mod 10 (4 Hard, 9 Super Hard), `curve.timers` (the template's recorded timer when fromTemplate), the grid caps, obstacle kinds only from the
//                 curve's unlocked kinds (corners too since ruling 26, never more than 2 kinds); across the range: the obstacle mix
//                 against the curve's plan weights (0 / 1 / 2 kinds and each kind's share, +-10 points), the Hard / Super
//                 Hard counts, and a per-position table against the recorded templates.
//   no repeats    no two boards equal across L1-L150 + the range: exactly (heads + cells, L1's key), up to translation +
//                 the 8 symmetries of the grid (rotations / mirrors), and no near-repeat (>= 50 % of the arrows
//                 identical in place, Jaccard on translation-normalised arrow paths).
//   renderable    `renderProblems`: every sprite the board layers request exists in art/ui/out (App/Board TapeLayer /
//                 ObstacleSet / BoardArt ids) and every obstacle has a size the code-drawn art draws faithfully: doors
//                 >= 3 x 3 (the 9-slice shutter needs 3 rows; the lockHex sprite is 2.28 x 2.13 cells), box counters
//                 1-99 (DigitGlyphs warms "0"..."99"; 2 digits fit the ring well), pipe counters 1-9 (one digit in the
//                 pipeCounter badge), tapes 2-4 lanes in one straight band across their arrows, keys on 2 adjacent cells
//                 of their rider, elevators >= 2 x 2, the fit pitch >= the 14.04 pt zoom floor (cols <= 26).
//   deterministic every level produced a second time is byte-identical (canonical JSON line).
//   provider      a real `LevelProvider(library:)`: prefetch / levelStarted / level(n) give the same boards off-main.
// The served levels are written as canonical lines (--out) for tools/levels/endless_py.py (the Python validator's
// independent verdict) and tools/levels/sheets.py (contact sheets). Exit 1 on any failure.

let zoomFloorPt = 393.0 / 28.0          // SPEC-gameplay §2.1: the pitch never goes below 14.04 pt (= a 26-column fit)

/// The fit pitch of a board (SPEC-architecture D6): min(393 / (cols + 2), 633 / (rows + 2), 28.07) pt.
func fitPitch(cols: Int, rows: Int) -> Double { min(393.0 / Double(cols + 2), 633.0 / Double(rows + 2), 28.07) }

/// Sprite ids the board layers request for one obstacle (App/Board/ObstacleSet.spriteIDs, TapeLayer.spriteID).
func boardSpriteIDs(_ o: ObstacleSpec) -> [String] {
    switch o.kind {
    case .tape:
        if let s = o.sprite { return [s] }
        let cols = Set(o.cells.map(\.c)).count, rows = Set(o.cells.map(\.r)).count
        let lanes = max(o.cells.count, o.arrows.count)
        return [rows >= cols ? "tapeV\(lanes)" : "tapeH\(lanes)"]
    case .door: return ["doorW4H8", "lockHex", "doorShards"]
    case .key: return ["keyOnArrow"]
    case .pipe: return ["pipeMouth", "pipeCounter", "pipeShards"]
    case .box, .curtain: return ["boxRing"]
    // F3-B (2026-09-29): corners ship (SPEC.md ruling 26, SPEC-gameplay §3.9; card at L70). App/Board/ObstacleSet.spriteIDs
    // draws the facing's own spring + plate (FIX-2 A, L02: CornerNode.layerIDs) plus the rotated `cornerWedge` fallback.
    case .corner:
        guard let t = o.turn else { return ["cornerWedge"] }
        let facing: String
        switch t {
        case .upRight: facing = "UpRight"
        case .upLeft: facing = "UpLeft"
        case .downLeft: facing = "DownLeft"
        case .downRight: facing = "DownRight"
        }
        return ["corner\(facing)Spring", "corner\(facing)Plate", "cornerWedge"]
    case .elevator: return []
    }
}

func artCatalog(_ dir: String) -> Set<String> {
    let names = (try? FileManager.default.contentsOfDirectory(atPath: dir)) ?? []
    return Set(names.filter { $0.hasSuffix("@3x.png") && !$0.hasPrefix("_") }.map { String($0.dropLast("@3x.png".count)) })
}

func blockSize(_ cs: [Cell]) -> (w: Int, h: Int) {
    guard !cs.isEmpty else { return (0, 0) }
    let xs = cs.map(\.c), ys = cs.map(\.r)
    return (xs.max()! - xs.min()! + 1, ys.max()! - ys.min()! + 1)
}

/// What the board could not draw faithfully (empty = every obstacle and the grid render). `pitchIsError` false turns the
/// zoom-floor finding into a warning (the authored L6, VERIFIED at 13.55 pt in the video).
func renderProblems(_ l: LevelSpec, art: Set<String>) -> (errors: [String], warnings: [String]) {
    var e: [String] = [], w: [String] = []
    let A = Dictionary(l.arrows.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
    var needed = Set<String>(["boardTrailStar"])
    for o in l.obstacles {
        for s in boardSpriteIDs(o) { needed.insert(s) }
        let (bw, bh) = blockSize(o.cells)
        switch o.kind {
        case .tape:
            let lanes = o.cells.count
            if !(2...4).contains(lanes) || o.arrows.count != lanes { e.append("tape \(o.id.raw): \(lanes) tie cells / \(o.arrows.count) members (sprites exist for 2-4 lanes)") }
            let dirs = Set(o.arrows.compactMap { A[$0]?.dir })
            let horizontal = dirs.allSatisfy { $0 == .left || $0 == .right }
            let vertical = dirs.allSatisfy { $0 == .up || $0 == .down }
            if horizontal && !(bw == 1 && bh == lanes) { e.append("tape \(o.id.raw): the band across horizontal arrows is \(bw)x\(bh), not 1x\(lanes)") }
            if vertical && !(bh == 1 && bw == lanes) { e.append("tape \(o.id.raw): the band across vertical arrows is \(bw)x\(bh), not \(lanes)x1") }
            if !horizontal && !vertical { e.append("tape \(o.id.raw): members point in crossing directions") }
        case .door:
            if bw < 3 || bh < 3 { e.append("door \(o.id.raw) \(bw)x\(bh): below 3x3 (the 9-slice shutter needs 3 rows; lockHex is 2.28 x 2.13 cells)") }
        case .box, .curtain:
            guard let c = o.counter else { e.append("box \(o.id.raw) without a counter"); break }
            if !(1...99).contains(c) { e.append("box \(o.id.raw) counter \(c): outside 1-99 (DigitGlyphs warms 0...99; 2 digits fit the ring)") }
            if min(bw, bh) < 1 { e.append("box \(o.id.raw) empty") }
        case .pipe:
            if let c = o.counter { if !(1...9).contains(c) { e.append("pipe \(o.id.raw) counter \(c): outside 1-9 (one digit in the badge)") } }
            else { e.append("pipe \(o.id.raw) without a counter") }
            if o.cells.count < 2 || o.ends.count != 2 { e.append("pipe \(o.id.raw): \(o.cells.count) cells, \(o.ends.count) mouths") }
            if let at = o.counterAt, at.count == 2 {
                let d = o.cells.map { abs(at[0] - Double($0.c)) + abs(at[1] - Double($0.r)) }.min() ?? 99
                if d > 1.0 { e.append("pipe \(o.id.raw) counter badge \(at) off the tube") }
            } else { e.append("pipe \(o.id.raw) without counter_at") }
        case .key:
            guard o.arrows.count == 1, let rider = A[o.arrows[0]] else { e.append("key \(o.id.raw) without its rider"); break }
            if o.cells.count != 2 || Dir(from: o.cells[0], to: o.cells[1]) == nil || !Set(o.cells).isSubset(of: Set(rider.cells)) {
                e.append("key \(o.id.raw) is not on 2 adjacent cells of arrow \(rider.id.raw)")
            }
        case .elevator:
            if bw < 2 || bh < 2 { e.append("elevator \(o.id.raw) \(bw)x\(bh): below 2x2 (two door halves + the 0.22 p rim)") }
        case .corner:
            // was: "corners are not shipped (SPEC-gameplay §3.9; no cornerWedge art)" (before the recast shipped them, ruling 26).
            // Now what CornerNode draws faithfully: ONE cell with a turn (its facing's sprites are required above)
            if o.cells.count != 1 || o.turn == nil { e.append("corner \(o.id.raw): \(o.cells.count) cells, turn \(o.turn?.rawValue ?? "nil") (one cell with a turn)") }
        }
    }
    for s in needed.sorted() where !art.contains(s) { e.append("sprite \(s) missing from the art catalogue") }
    let p = fitPitch(cols: l.cols, rows: l.rows)
    if p + 1e-9 < zoomFloorPt { w.append(String(format: "fit pitch %.2f pt below the 14.04 pt zoom floor (%dx%d)", p, l.cols, l.rows)) }
    return (e, w)
}

// MARK: board identity

/// Translation-normalised arrow paths ("c,r c,r …", tail → head), relative to the board's own min column / row.
func arrowPaths(_ l: LevelSpec) -> [String] {
    let all = l.arrows.flatMap(\.cells)
    guard !all.isEmpty else { return [] }
    let c0 = all.map(\.c).min()!, r0 = all.map(\.r).min()!
    return l.arrows.map { a in a.cells.map { "\($0.c - c0),\($0.r - r0)" }.joined(separator: " ") }
}

/// The board up to translation and the 8 symmetries of the square grid: the smallest of the 8 sorted path lists.
func shapeKey(_ l: LevelSpec) -> String {
    let all = l.arrows.flatMap(\.cells)
    guard !all.isEmpty else { return "" }
    var best: String?
    for t in 0..<8 {
        func f(_ c: Cell) -> (Int, Int) {
            switch t {
            case 0: return (c.c, c.r)
            case 1: return (-c.r, c.c)
            case 2: return (-c.c, -c.r)
            case 3: return (c.r, -c.c)
            case 4: return (-c.c, c.r)
            case 5: return (c.c, -c.r)
            case 6: return (c.r, c.c)
            default: return (-c.r, -c.c)
            }
        }
        let mapped = all.map(f)
        let x0 = mapped.map(\.0).min()!, y0 = mapped.map(\.1).min()!
        let paths = l.arrows.map { a in a.cells.map { c -> String in let (x, y) = f(c); return "\(x - x0),\(y - y0)" }.joined(separator: " ") }.sorted()
        let k = paths.joined(separator: "|")
        if best == nil || k < best! { best = k }
    }
    return best!
}

/// For every level: the most similar other level (Jaccard of translation-normalised arrow paths).
func nearestTwins(_ levels: [LevelSpec]) -> [Int: (other: Int, jaccard: Double)] {
    let sets = levels.map { Set(arrowPaths($0)) }
    var index: [String: [Int]] = [:]
    for (i, s) in sets.enumerated() { for p in s { index[p, default: []].append(i) } }
    var out: [Int: (Int, Double)] = [:]
    for (i, s) in sets.enumerated() {
        var shared: [Int: Int] = [:]
        for p in s { for j in index[p]! where j != i { shared[j, default: 0] += 1 } }
        var best = (other: 0, jaccard: 0.0)
        for (j, k) in shared {
            let jac = Double(k) / Double(s.count + sets[j].count - k)
            if jac > best.jaccard { best = (levels[j].level, jac) }
        }
        out[levels[i].level] = best
    }
    return out
}

let nearRepeatLimit = 0.5

/// Repeats among `levels`, reported for the levels in `checked`: exact (heads + cells), up to translation + the 8 grid
/// symmetries, and near (>= `nearRepeatLimit` of the arrows identical in place).
func repeatScan(_ levels: [LevelSpec], checked: Set<Int>) -> (exact: [String], shape: [String], near: [String], twins: [Int: (other: Int, jaccard: Double)]) {
    var exact: [String: Int] = [:], shape: [String: Int] = [:]
    var ex: [String] = [], sh: [String] = [], near: [String] = []
    for l in levels {
        let k = boardKey(l), s = shapeKey(l)
        if let o = exact[k] { if checked.contains(l.level) || checked.contains(o) { ex.append("L\(l.level) = L\(o)") } }
        else if let o = shape[s] { if checked.contains(l.level) || checked.contains(o) { sh.append("L\(l.level) ≅ L\(o) (translated / rotated / mirrored)") } }
        if exact[k] == nil { exact[k] = l.level }
        if shape[s] == nil { shape[s] = l.level }
    }
    let twins = nearestTwins(levels)
    for l in levels where checked.contains(l.level) {
        let t = twins[l.level]!
        if t.jaccard >= nearRepeatLimit { near.append(String(format: "L%d ~ L%d (%.0f %% of the arrows identical in place)", l.level, t.other, 100 * t.jaccard)) }
    }
    return (ex, sh, near, twins)
}

// MARK: one endless level

struct EndlessResult {
    var level: LevelSpec
    var route: String
    var seedsTried: Int
    var totalMs: Double
    var errors: [String] = []
    var warnings: [String] = []
    var row: [String: Any] = [:]
    var line: String = ""
}

let cadence: [Int: LevelTag] = [4: .hard, 9: .superHard]

/// Every per-level check (the selftest runs it on mutated levels too).
func endlessCheck(_ l: LevelSpec, n: Int, route: String, curve: CurveSpec, rules: RulesTuning, art: Set<String>, root: String) -> (errors: [String], warnings: [String], row: [String: Any]) {
    var errs: [String] = [], warns: [String] = []
    func E(_ s: String) { errs.append("L\(n): \(s)") }
    var row: [String: Any] = ["level": n, "route": route, "tag": l.tag.rawValue, "timer_s": l.timerSeconds, "cols": l.cols, "rows": l.rows,
                              "arrows": l.arrows.count, "units": l.unitCount]
    // identity and provenance
    if route == LevelProvider.Record.Route.fallback.rawValue { E("served by the fallback (a renumbered authored level: a repeat, stand-in content)") }
    if l.level != n { E("level field \(l.level)") }
    if l.source != .generated { E("source \(l.source.rawValue), expected generated") }
    if l.unlock != nil { E("carries an unlock card (\(l.unlock!.rawValue)); cards exist only at the first appearances in L1-L150") }
    if l.seed == nil { warns.append("L\(n): no seed recorded") }
    // solvable: CONTENT's §14.4 list on C2's rules (shipped rules.json) + C4's exact search
    let c = checkLevel(l, rules: rules, root: root)
    for x in c.errors { errs.append(x) }
    for x in c.warnings where !x.contains("fit pitch below") && !x.contains("cols") { warns.append(x) }
    for (k, v) in c.row { row[k] = v }
    switch Solver.solve(l, rules: rules) {
    case .solved(let order): row["search"] = "solved"; row["search_units"] = order.count
    case .unsolvable: E("C4's search: UNSOLVABLE"); row["search"] = "unsolvable"
    case .undecided(let nodes): E("C4's search: undecided after \(nodes) states"); row["search"] = "undecided"
    }
    // curve fit: C4's bands + independent checks
    do {
        let a = try Difficulty.assess(l, curve: curve)
        for v in a.violations { E("curve band: \(v)") }
        row["target_units"] = a.target.units; row["target_rounds"] = a.target.rounds; row["target_free"] = a.target.free
        row["target_cols"] = a.target.cols; row["target_rows"] = a.target.rows; row["template"] = a.target.template
        row["units_ratio"] = (a.unitsRatio * 1000).rounded() / 1000; row["rounds_ratio"] = (a.roundsRatio * 1000).rounded() / 1000
        row["measured_rounds"] = a.measured.rounds; row["measured_free"] = a.measured.freeAtStart
    } catch { E("no curve target: \(error)") }
    let wantTag = cadence[((n % 10) + 10) % 10] ?? .normal
    if l.tag != wantTag { E("tag \(l.tag.rawValue), the cadence says \(wantTag.rawValue)") }
    let t = curve.timers
    let tagName = l.tag == .hard ? "Hard" : l.tag == .superHard ? "Super Hard" : "normal"
    if t.fromTemplate {
        // F3-B (2026-09-29): the recast's curve sets `timers.fromTemplate` (SPEC.md ruling 27, SPEC-gameplay §14.3: "timers from
        // the templates"): the generator (Generator.timerFor = the reference gen_levels.timer_for) gives EVERY tag the recorded
        // timer of the position's template (1:40 … 3:30), so a Hard level is not held to curve.timers.hard any more (this check
        // still asked for it: 127 false failures, the same 127 on the B0 run of 09-28 next to 739 corner ones). Independent of C4's allowedTimers: the timer
        // is looked up in the curve's own template list.
        if let tg = try? Generator.target(curve, n), let rec = curve.templates.first(where: { $0.level == tg.template }) {
            if l.timerSeconds != rec.timer {
                E("\(tagName) timer \(l.timerSeconds) != \(rec.timer), the recorded timer of its template L\(rec.level) (curve.timers.fromTemplate)")
            }
        } else { E("\(tagName) timer: no curve template for the position (curve.timers.fromTemplate)") }
    } else {
        switch l.tag {
        case .hard: if l.timerSeconds != t.hard { E("Hard timer \(l.timerSeconds) != \(t.hard)") }
        case .superHard: if l.timerSeconds != t.superHard { E("Super Hard timer \(l.timerSeconds) != \(t.superHard)") }
        case .normal: if ![t.normal, t.short].contains(l.timerSeconds) { E("normal timer \(l.timerSeconds) not in {\(t.normal), \(t.short)}") }
        }
    }
    if l.cols > curve.maxCols || l.rows > curve.maxRows { E("grid \(l.cols)x\(l.rows) beyond the curve cap \(curve.maxCols)x\(curve.maxRows)") }
    let kinds = Set(l.obstacles.map(\.kind).filter { $0 != .key }.map(\.rawValue))
    row["kinds"] = kinds.sorted()
    for k in kinds {
        guard let first = curve.obstacles.firstLevel[k], curve.obstacles.kindOrder.contains(k) else { E("obstacle kind \(k) is not in the curve"); continue }
        if n < first { E("obstacle kind \(k) before its unlock level \(first)") }
    }
    if kinds.count > curve.obstacles.countWeights.count - 1 { E("\(kinds.count) obstacle kinds (the curve plans at most \(curve.obstacles.countWeights.count - 1))") }
    if l.mask != nil { warns.append("L\(n): mask set") }
    // renderable
    let r = renderProblems(l, art: art)
    for x in r.errors { E("render: \(x)") }
    for x in r.warnings { E("render: \(x)") }      // a generated board must fit the zoom floor (only the authored L6 may not)
    row["fit_pitch"] = (fitPitch(cols: l.cols, rows: l.rows) * 100).rounded() / 100
    return (errs, warns, row)
}

func percentile(_ xs: [Double], _ p: Double) -> Double {
    guard !xs.isEmpty else { return 0 }
    let s = xs.sorted()
    return s[min(s.count - 1, Int((Double(s.count - 1) * p).rounded()))]
}

/// Expected share of levels carrying kind k under the curve's plan (count weights, kinds without replacement).
func plannedKindShare(_ ob: CurveSpec.Obstacles) -> [String: Double] {
    let cw = ob.countWeights.map(Double.init)
    let tot = cw.reduce(0, +)
    let p1 = cw.count > 1 ? cw[1] / tot : 0, p2 = cw.count > 2 ? cw[2] / tot : 0
    let W = Double(ob.kindWeights.values.reduce(0, +))
    var out: [String: Double] = [:]
    for (k, wk) in ob.kindWeights {
        let w = Double(wk)
        var second = 0.0
        for (j, wj) in ob.kindWeights where j != k { second += (Double(wj) / W) * (w / (W - Double(wj))) }
        out[k] = p1 * (w / W) + p2 * (w / W + second)
    }
    return out
}

func cmdEndless(_ a: Args) throws -> Int32 {
    let root = FileManager.default.currentDirectoryPath
    let levelsDir = a.opt("levels", "App/Resources/Levels")
    let from = Int(a.opt("from", "151")) ?? 151
    let count = Int(a.opt("count", "1000")) ?? 1000
    let jobs = max(1, Int(a.opt("jobs", "3")) ?? 3)
    let (rules, rp) = try loadRules(a.opt("rules", "App/Resources/Tuning/rules.json"))
    let artDir = a.opt("art", "art/ui/out")
    let art = artCatalog(artDir)
    let lib = try LevelLibrary.load(folder: URL(fileURLWithPath: levelsDir))
    var fails: [String] = []
    var notes: [String] = []
    for p in rp { notes.append("rules.json: \(p)") }
    guard lib.curveJSON != nil else { throw ToolError("\(levelsDir)/curve.json is missing: the provider would use CurveSpec.default") }
    let curve = lib.curve
    if curve != CurveSpec.default { notes.append("the bundled curve differs from C4's compiled CurveSpec.default (the bundle wins at runtime)") }
    guard from > lib.authoredCount else { throw ToolError("--from \(from) is inside the authored range 1…\(lib.authoredCount)") }
    let range = Array(from..<(from + count))
    let t0 = Date()

    // 1. produce + check every level (jobs threads, each a strided slice; production is pure per n)
    var results = [EndlessResult?](repeating: nil, count: range.count)
    let lock = NSLock()
    DispatchQueue.concurrentPerform(iterations: jobs) { j in
        var i = j
        while i < range.count {
            let n = range[i]
            let (l, rec) = LevelProvider.produce(n, curve: curve, library: lib, options: Validator.Options())
            let chk = endlessCheck(l, n: n, route: rec.route.rawValue, curve: curve, rules: rules, art: art, root: root)
            var r = EndlessResult(level: l, route: rec.route.rawValue, seedsTried: rec.seedsTried, totalMs: rec.totalMs)
            r.errors = chk.errors; r.warnings = chk.warnings; r.row = chk.row
            r.row["seeds_tried"] = rec.seedsTried
            r.row["served_ms"] = (rec.totalMs * 10).rounded() / 10
            r.row["refused"] = rec.refused
            r.line = ContentJSON.line(l, schema: true)
            lock.lock(); results[i] = r; lock.unlock()
            i += jobs
        }
    }
    let rs = results.map { $0! }
    for r in rs { fails += r.errors }
    let tProduce = Date().timeIntervalSince(t0)

    // 2. determinism: every level produced again must be byte-identical
    var rerunDiffs: [Int] = []
    if !a.flags.contains("no-rerun") {
        var again = [String](repeating: "", count: range.count)
        DispatchQueue.concurrentPerform(iterations: jobs) { j in
            var i = j
            while i < range.count {
                let (l, _) = LevelProvider.produce(range[i], curve: curve, library: lib, options: Validator.Options())
                let s = ContentJSON.line(l, schema: true)
                lock.lock(); again[i] = s; lock.unlock()
                i += jobs
            }
        }
        for (i, r) in rs.enumerated() where again[i] != r.line { rerunDiffs.append(range[i]) }
        for n in rerunDiffs { fails.append("L\(n): a second production differs (not deterministic)") }
    }

    // 3. no repeats across the authored L1-L150 and the range
    var authored: [LevelSpec] = []
    for n in 1...lib.authoredCount { authored.append(try lib.loadAuthored(n)) }
    let everything = authored + rs.map(\.level)
    let rep = repeatScan(everything, checked: Set(range))
    let (exactRepeats, shapeRepeats, nearRepeats, twins) = (rep.exact, rep.shape, rep.near, rep.twins)
    for x in exactRepeats + shapeRepeats { fails.append("repeat: \(x)") }
    for x in nearRepeats { fails.append("near-repeat: \(x)") }
    let nearLimit = nearRepeatLimit
    let genJ = rs.map { twins[$0.level.level]!.jaccard }
    let maxTwin = rs.max { twins[$0.level.level]!.jaccard < twins[$1.level.level]!.jaccard }.map { ($0.level.level, twins[$0.level.level]!) }

    // 4. population fit: obstacle mix, cadence counts, per-position table
    let N = Double(rs.count)
    var kindCount: [String: Int] = [:]
    var perCount = [0, 0, 0, 0]
    for r in rs {
        let ks = (r.row["kinds"] as? [String]) ?? []
        perCount[min(3, ks.count)] += 1
        for k in ks { kindCount[k, default: 0] += 1 }
    }
    let cw = curve.obstacles.countWeights.map(Double.init), cwT = cw.reduce(0, +)
    var mixRows: [[String: Any]] = []
    for (i, w) in cw.enumerated() {
        let got = Double(perCount[i]) / N, want = w / cwT
        mixRows.append(["kinds": i, "served": (got * 1000).rounded() / 10, "planned": (want * 1000).rounded() / 10])
        if abs(got - want) > 0.10 { fails.append(String(format: "mix: %d kind(s) on %.1f %% of the levels, planned %.1f %% (> 10 points off)", i, 100 * got, 100 * want)) }
    }
    if perCount[3] > 0 { fails.append("mix: \(perCount[3]) level(s) with 3+ obstacle kinds") }
    let planned = plannedKindShare(curve.obstacles)
    var kindRows: [[String: Any]] = []
    for k in curve.obstacles.kindOrder {
        let got = Double(kindCount[k] ?? 0) / N, want = planned[k] ?? 0
        kindRows.append(["kind": k, "served": (got * 1000).rounded() / 10, "planned": (want * 1000).rounded() / 10])
        if abs(got - want) > 0.10 { fails.append(String(format: "mix: %@ on %.1f %% of the levels, planned %.1f %% (> 10 points off)", k, 100 * got, 100 * want)) }
    }
    let hard = rs.filter { $0.level.tag == .hard }.count, superHard = rs.filter { $0.level.tag == .superHard }.count
    let expHard = range.filter { ($0 % 10) == 4 }.count, expSuper = range.filter { ($0 % 10) == 9 }.count
    if hard != expHard || superHard != expSuper { fails.append("cadence: \(hard) Hard / \(superHard) Super Hard, expected \(expHard) / \(expSuper)") }
    let normals = rs.filter { $0.level.tag == .normal }
    let shortShare = Double(normals.filter { $0.level.timerSeconds == curve.timers.short }.count) / Double(max(1, normals.count))
    var posRows: [[String: Any]] = []
    for p in 0..<10 {
        let g = rs.filter { $0.level.level % 10 == p }
        func med(_ f: (EndlessResult) -> Double) -> Double { percentile(g.map(f), 0.5) }
        let tpl = (0..<3).compactMap { curve.template(pos: p, slot: $0) }
        posRows.append(["pos": p, "levels": g.count, "tag": (cadence[p] ?? .normal).rawValue,
                        "units_median": med { Double($0.level.unitCount) },
                        "target_units_median": med { Double(($0.row["target_units"] as? Int) ?? 0) },
                        "rounds_median": med { Double(($0.row["rounds"] as? Int) ?? 0) },
                        "target_rounds_median": med { Double(($0.row["target_rounds"] as? Int) ?? 0) },
                        "free_median": med { Double(($0.row["free_at_start"] as? Int) ?? 0) },
                        "cols_median": med { Double($0.level.cols) }, "rows_median": med { Double($0.level.rows) },
                        "templates": tpl.map { "L\($0.level) \($0.units)u/\($0.rounds)w/\($0.free)f \($0.cols)x\($0.rows)" }])
    }

    // 5. a real LevelProvider: the off-main protocol returns the same boards (and never falls back)
    var providerNotes: [String] = []
    do {
        let p = LevelProvider(library: lib)
        let last = lib.authoredCount
        p.levelStarted(last)                                   // the last authored level starts: prefetch L(last+1)
        p.prefetch(from + 1)
        let l1 = p.level(last + 1), l2 = p.level(from + 1)
        let want1 = last + 1 == from ? rs[0].line : ContentJSON.line(LevelProvider.produce(last + 1, curve: curve, library: lib, options: Validator.Options()).0, schema: true)
        if ContentJSON.line(l1, schema: true) != want1 { fails.append("provider: level(\(last + 1)) differs from produce") }
        if count > 1, ContentJSON.line(l2, schema: true) != rs[1].line { fails.append("provider: level(\(from + 1)) differs from produce") }
        if p.level(last).source == .generated { fails.append("provider: the authored L\(last) came back generated") }
        p.levelStarted(1)                                       // Levels 1-4: next is L5, authored: nothing to generate
        let recs = p.records
        if recs.contains(where: { $0.route == .fallback }) { fails.append("provider: a fallback production") }
        if recs.contains(where: { $0.level <= last }) { fails.append("provider: generated an authored level") }
        providerNotes.append("LevelProvider(library:): levelStarted(\(last)) prefetched L\(last + 1); level(\(last + 1)), level(\(from + 1)) = produce; \(recs.count) productions, routes \(Set(recs.map(\.route.rawValue)).sorted())")
    }

    // 6. report
    let served = rs.map(\.totalMs)
    let routes = Dictionary(grouping: rs, by: \.route).mapValues(\.count)
    let seconds = Date().timeIntervalSince(t0)
    let summary: [String: Any] = [
        "range": "L\(from)-L\(from + count - 1)", "levels": rs.count, "levels_dir": levelsDir,
        "curve": "bundled curve.json (\(curve == CurveSpec.default ? "= CurveSpec.default" : "differs from CurveSpec.default"))",
        "rules": a.opt("rules", "App/Resources/Tuning/rules.json"), "art": artDir, "jobs": jobs,
        "routes": routes, "failures": fails, "notes": notes + providerNotes,
        "determinism": rerunDiffs.isEmpty ? "all \(rs.count) byte-identical on a second production" : "differs: \(rerunDiffs)",
        "repeats": ["exact": exactRepeats, "shape": shapeRepeats, "near_limit_jaccard": nearLimit, "near": nearRepeats,
                    "max_jaccard": maxTwin.map { ["level": $0.0, "other": $0.1.other, "jaccard": ($0.1.jaccard * 1000).rounded() / 1000] } ?? [:],
                    "jaccard_p50": (percentile(genJ, 0.5) * 1000).rounded() / 1000, "jaccard_p95": (percentile(genJ, 0.95) * 1000).rounded() / 1000],
        "mix_counts": mixRows, "mix_kinds": kindRows,
        "cadence": ["hard": hard, "superHard": superHard, "normal": normals.count, "normal_short_timer_share": (shortShare * 1000).rounded() / 1000],
        "positions": posRows,
        "served_ms": ["p50": percentile(served, 0.5), "p95": percentile(served, 0.95), "max": served.max() ?? 0,
                      "note": "wall ms per production with \(jobs) threads sharing the CPU (a contended upper bound)"],
        "seconds": (seconds * 10).rounded() / 10, "produce_seconds": (tProduce * 10).rounded() / 10,
        "table": rs.map(\.row),
    ]
    if let rp = a.options["report"] { try writeData(try reportJSON(summary), rp) }
    if let o = a.options["out"] { try writeData(Data((rs.map(\.line).joined(separator: "\n") + "\n").utf8), o) }

    print("endless: L\(from)-L\(from + count - 1) (\(rs.count) levels) as LevelProvider serves them from \(levelsDir) (curve.json \(curve == CurveSpec.default ? "= CurveSpec.default" : "≠ default")); \(String(format: "%.1f", seconds)) s on \(jobs) threads")
    print("  routes: \(routes.sorted { $0.key < $1.key }.map { "\($0.key) \($0.value)" }.joined(separator: ", "))")
    print("  solvable: C2 greedy + HeadlessDriver (0.6 s/tap, ≥ 20 %) + no dead end + C4 search: \(rs.filter { ($0.row["greedy_solved"] as? Bool) == true && ($0.row["driver_won"] as? Bool) == true && ($0.row["search"] as? String) == "solved" }.count)/\(rs.count)")
    print("  driver time left: min \(String(format: "%.1f", (rs.compactMap { $0.row["driver_time_left_fraction"] as? Double }.min() ?? 0) * 100)) % of the timer")
    print("  determinism: \(rerunDiffs.isEmpty ? "\(rs.count)/\(rs.count) byte-identical on a second production" : "\(rerunDiffs.count) differ")")
    print("  repeats: exact \(exactRepeats.count), up to symmetry \(shapeRepeats.count), near (≥ \(Int(nearLimit * 100)) % arrows in place) \(nearRepeats.count); most similar pair \(maxTwin.map { String(format: "L%d ~ L%d %.1f %%", $0.0, $0.1.other, 100 * $0.1.jaccard) } ?? "-"); Jaccard p50 \(String(format: "%.3f", percentile(genJ, 0.5))) p95 \(String(format: "%.3f", percentile(genJ, 0.95)))")
    print("  cadence: \(hard) Hard, \(superHard) Super Hard, \(normals.count) normal (2:30 on \(String(format: "%.1f", shortShare * 100)) % of the normals)")
    print("  obstacle kinds per level (served vs planned %): " + mixRows.map { "\($0["kinds"]!): \($0["served"]!) vs \($0["planned"]!)" }.joined(separator: " · "))
    print("  kind shares (served vs planned %): " + kindRows.map { "\($0["kind"]!) \($0["served"]!) vs \($0["planned"]!)" }.joined(separator: " · "))
    print(String(format: "  served ms (%d threads, contended): p50 %.1f  p95 %.1f  max %.1f", jobs, percentile(served, 0.5), percentile(served, 0.95), served.max() ?? 0))
    for n in providerNotes { print("  \(n)") }
    for n in notes { print("  note: \(n)") }
    print("  per position (median units / target, waves / target, free, grid):")
    for r in posRows {
        print(String(format: "    p%d %-9@ n=%3d  units %5.1f / %5.1f  waves %4.1f / %4.1f  free %4.1f  grid %2.0fx%2.0f   templates %@",
                     r["pos"] as! Int, r["tag"] as! String, r["levels"] as! Int, r["units_median"] as! Double, r["target_units_median"] as! Double,
                     r["rounds_median"] as! Double, r["target_rounds_median"] as! Double, r["free_median"] as! Double,
                     r["cols_median"] as! Double, r["rows_median"] as! Double, (r["templates"] as! [String]).joined(separator: ", ")))
    }
    print("endless: \(fails.count) failure(s)")
    for f in fails.prefix(80) { print("FAIL \(f)") }
    return fails.isEmpty ? 0 : 1
}
