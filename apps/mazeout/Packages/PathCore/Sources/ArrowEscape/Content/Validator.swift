import Foundation
import GameCore

// C4 (SPEC-architecture §4.14; SPEC-gameplay §3.10, §3.11, §14.4). The content validator: design/tools/validate_levels.py
// ported check for check (same order, same messages where the Python's are deterministic), over the arrowcore mirror
// (ContentRules), so its verdict on a level equals the Python validator's. Since the content recast (2026-09-25, phone
// session 2) that includes: an obstacle lying wholly under a door may share the door's cells (v552 L69), a door's hidden
// arrow may poke out of it only where no ray reaches the stub and nothing lies there (v552 L62), no ray may reach the
// pipe/corner hop guard, and the repeated-board check is offset-free. On top of the reference list:
// - sprites (§4.14, with CONSISTENCY O-21 / O-23): tapes `tape{V|H}{lanes}`, doors `lockHex` (the shutter is drawn in
//   code), keys `keyOnArrow`, pipes `pipeMouth` + `pipeCounter`, boxes and curtains `boxRing`, corners
//   `cornerWedge` must exist in the catalogue given;
// - the GAME's rules (C2's BoardState): its greedy solver must clear the level and the HeadlessDriver must win it at
//   0.6 s per tap with ≥ 20 % of the timer left (§4.14 "a HeadlessDriver win at human speed"), so the content rules and
//   the game rules cannot drift apart unnoticed. These findings are tagged `.gameRules`.
// Messages never contain the words the release string gate forbids (SPEC.md §5 item 24): the reference's "bot" is
// written "0.6 s/tap driver" here.

/// One validator finding.
public struct Finding: Sendable, Equatable, CustomStringConvertible {
    public enum Severity: String, Sendable, Codable { case error, warning }
    public enum Area: String, Sendable, Codable {
        case schema, structure, obstacle, value, provenance, sprite, solver, metrics, content, gameRules
    }
    public var severity: Severity
    public var area: Area
    /// nil for document-level findings (numbering, unlocks, sessions, …).
    public var level: Int?
    public var message: String

    public init(_ severity: Severity, _ area: Area, level: Int?, _ message: String) {
        self.severity = severity; self.area = area; self.level = level; self.message = message
    }

    /// "L<n>: message" (the reference's format), or the message alone.
    public var description: String { (level.map { "L\($0): " } ?? "") + message }
}

/// The sprite ids an art folder provides (`art/ui/out/<id>@3x.png`, bundle `UI/<id>@3x.png`).
public struct SpriteCatalog: Sendable, Equatable {
    public var ids: Set<String>
    public init(ids: Set<String>) { self.ids = ids }

    /// Every `<id>@<n>x.png` / `<id>.png` in `folder` (names starting with "_" are skipped, as sync_art.sh does).
    public static func load(folder: URL) throws -> SpriteCatalog {
        var ids = Set<String>()
        for name in try FileManager.default.contentsOfDirectory(atPath: folder.path) where name.hasSuffix(".png") && !name.hasPrefix("_") {
            var base = String(name.dropLast(4))
            if let at = base.range(of: "@", options: .backwards) { base = String(base[..<at.lowerBound]) }
            ids.insert(base)
        }
        return SpriteCatalog(ids: ids)
    }

    public func contains(_ id: String) -> Bool { ids.contains(id) }
}

public enum Validator {

    public struct Options: Sendable {
        /// Which form of the content is checked (PUBLISH B0; SPEC.md ruling 39 OD8, "STRIP provenance from every shipped
        /// file"). `.source` = design/levels.json and its pinned copy: a recorded / video board must name the capture it
        /// was read from. `.publish` = the SHIPPED bundle (App/Resources/Levels, `lvtool bundle --publish`): the research
        /// trail is stripped, so a board must carry NO capture and no "_" comment key (the inverse check, as strict).
        public enum Provenance: String, Sendable { case source, publish }
        /// Random play orders checked on non-monotone levels (the reference: 40).
        public var randomOrders = 40
        /// Also require C2's greedy and the HeadlessDriver (0.6 s/tap) to clear the level.
        public var gameRules = true
        public var rules: RulesTuning = .default
        public var provenance: Provenance = .source
        public init(randomOrders: Int = 40, gameRules: Bool = true, rules: RulesTuning = .default, provenance: Provenance = .source) {
            self.randomOrders = randomOrders; self.gameRules = gameRules; self.rules = rules; self.provenance = provenance
        }
    }

    /// One level's result: findings and, when the level got that far, the recomputed metrics.
    public struct LevelReport: Sendable {
        public var level: Int
        public var findings: [Finding]
        public var measured: ContentRules.Measured?
        public var errors: [Finding] { findings.filter { $0.severity == .error } }
        public var warnings: [Finding] { findings.filter { $0.severity == .warning } }
        public var isValid: Bool { errors.isEmpty }
    }

    /// A whole content set (design/levels.json or a bundle folder).
    public struct Report: Sendable {
        public var levels: [LevelReport]
        public var findings: [Finding]              // every finding: per level, then document-level
        public var firstAppearance: [String: Int]   // feature → first level
        public var errors: [Finding] { findings.filter { $0.severity == .error } }
        public var warnings: [Finding] { findings.filter { $0.severity == .warning } }
    }

    static let levelKeys: Set<String> = ["schema", "level", "source", "capture", "cols", "rows", "mask", "timer_s", "hearts",
                                         "tag", "arrows", "obstacles", "unlock", "seed", "metrics"]
    static let arrowKeys: Set<String> = ["id", "cells", "dir", "layer", "hidden_by"]
    static let obstacleKeys: Set<String> = ["id", "kind", "cells", "arrows", "ends", "counter", "counter_at", "order", "opens",
                                            "turn", "reveals", "sprite"]
    static let prefix: [ObstacleKind: String] = [.tape: "t", .door: "d", .key: "k", .pipe: "p", .box: "b", .curtain: "c",
                                                 .elevator: "e", .corner: "x"]
    /// The unlock feature of an obstacle kind (a key belongs to its door).
    public static let featureOf: [ObstacleKind: String] = [.tape: "linked", .door: "door", .pipe: "pipe", .box: "box",
                                                          .curtain: "box", .elevator: "elevator", .corner: "corner"]

    // MARK: - one level (§4.14 API)

    /// Every finding for one level (errors and warnings).
    public static func check(_ level: LevelSpec, sprites: SpriteCatalog?) -> [Finding] {
        checkLevel(level, raw: nil, sprites: sprites, options: Options()).findings
    }

    /// The full per-level check. `raw` (the level's JSON object) adds the schema checks the typed model cannot see
    /// (unknown keys, missing keys, value types); generated levels are checked without it.
    public static func checkLevel(_ l: LevelSpec, raw: JSONValue?, sprites: SpriteCatalog?, options: Options) -> LevelReport {
        var out: [Finding] = []
        let L = l.level
        func E(_ a: Finding.Area, _ m: String) { out.append(Finding(.error, a, level: L, m)) }
        func W(_ a: Finding.Area, _ m: String) { out.append(Finding(.warning, a, level: L, m)) }
        func t(_ c: Cell) -> String { "(\(c.c), \(c.r))" }
        func list(_ xs: [Int]) -> String { "[" + xs.map(String.init).joined(separator: ", ") + "]" }

        // schema (raw)
        if let raw {
            for (k, _) in raw.objectPairs ?? [] where !levelKeys.contains(k) && !k.hasPrefix("_") { E(.schema, "unknown key \(k)") }
            // FIX-2 B (N-01): `source` is the research form's (design/levels.json); the publish form must NOT carry it
            let required = ["level", "cols", "rows", "timer_s", "hearts", "tag", "arrows", "obstacles"] + (options.provenance == .source ? ["source"] : [])
            for k in required where raw[k] == nil {
                E(.schema, "missing \(k)")
                return LevelReport(level: L, findings: out, measured: nil)
            }
            if let s = raw["source"]?.stringValue, LevelSource(rawValue: s) == nil { E(.provenance, "source \(s)") }   // FIX-3 B: the raw values, no literals
            if let s = raw["tag"]?.stringValue, !["normal", "hard", "superHard"].contains(s) { E(.value, "tag \(s)") }
            else if raw["tag"]?.stringValue == nil { E(.value, "tag \(raw["tag"].map(ContentJSON.write) ?? "None")") }
        }
        switch options.provenance {
        case .source:
            if (l.source == .authored || l.source == .crafted) && (l.capture ?? "").isEmpty { E(.provenance, "no capture for a \(l.source.rawValue) level") }
        case .publish:                              // PUBLISH B0: what ships must not say where a board came from
            if l.capture != nil { E(.provenance, "capture in the publish form") }
            for (k, _) in raw?.objectPairs ?? [] where k.hasPrefix("_") { E(.provenance, "comment key \(k) in the publish form") }
            // FIX-2 B (N-01): nor how it was read (`source` recorded / video) or measured (`metrics`, the bot's time left)
            for k in ["source", "metrics"] where raw?[k] != nil { E(.provenance, "\(k) in the publish form") }
            if raw == nil, l.source != .designed || l.metrics != nil { E(.provenance, "source / metrics in the publish form") }
        }
        if !(60...600).contains(l.timerSeconds) { E(.value, "timer_s \(l.timerSeconds)") }
        if l.hearts != 3 { E(.value, "hearts \(l.hearts)") }
        if !(2...40).contains(l.cols) || !(2...40).contains(l.rows) { E(.value, "grid \(l.cols)x\(l.rows)") }
        if l.cols > 26 { W(.value, "cols \(l.cols) > 26: fit pitch below the 14.04 pt zoom floor") }
        if let raw, let arr = raw["arrows"]?.arrayValue {
            for a in arr { for (k, _) in a.objectPairs ?? [] where !arrowKeys.contains(k) { E(.schema, "arrow \(a["id"].map(ContentJSON.write) ?? "None") unknown key \(k)") } }
        }
        for p in ContentRules.structuralProblems(l) { E(.structure, p) }

        var A: [ArrowID: ArrowSpec] = [:]
        for a in l.arrows { A[a.id] = a }
        var O: [ObstacleID: ObstacleSpec] = [:]
        var oOrder: [ObstacleID] = []
        let rawObs = raw?["obstacles"]?.arrayValue
        for (n, o) in l.obstacles.enumerated() {
            if let ro = rawObs?[safe: n] {
                for (k, _) in ro.objectPairs ?? [] where !obstacleKeys.contains(k) { E(.schema, "obstacle \(o.id.raw) unknown key \(k)") }
            }
            if O[o.id] != nil { E(.obstacle, "duplicate obstacle id \(o.id.raw)") } else { oOrder.append(o.id) }
            if !o.id.raw.hasPrefix(prefix[o.kind]!) { W(.obstacle, "obstacle \(o.id.raw) id prefix vs kind \(o.kind.rawValue)") }
            O[o.id] = o
        }
        // (door, hidden arrow, its cells outside the door): a door-hidden arrow may poke out of its door (v552 L62's humps)
        var stubs: [(door: ObstacleID, arrow: ArrowID, out: Set<Cell>)] = []
        var visibleCells: [Cell: ArrowID] = [:]
        for a in l.arrows where a.hiddenBy == nil && a.layer == 1 { for c in a.cells { visibleCells[c] = a.id } }
        var hiderCells: [Cell: ObstacleID] = [:]
        let hiders: Set<ObstacleKind> = [.door, .box, .curtain, .pipe, .corner]
        // an obstacle lying wholly inside a door is UNDER it (v552 L69: pipes under doors): it may share the door's cells
        let doorSets: [(ObstacleID, Set<Cell>)] = oOrder.compactMap { O[$0]!.kind == .door ? ($0, Set(O[$0]!.cells)) : nil }
        var under: [ObstacleID: ObstacleID] = [:]
        for id in oOrder where [.box, .curtain, .pipe, .corner].contains(O[id]!.kind) {
            let cs = Set(O[id]!.cells)
            if let host = doorSets.first(where: { cs.isSubset(of: $0.1) }) { under[id] = host.0 }
        }
        // doors first (the reference: sorted(O.values(), key=0 if door else 1), stable), so a door owns its cells
        let checkOrder = oOrder.filter { O[$0]!.kind == .door } + oOrder.filter { O[$0]!.kind != .door }
        for id in checkOrder {
            let o = O[id]!
            let k = o.kind
            let cs = o.cells
            if hiders.contains(k) || k == .elevator {
                for c in cs {
                    if !(0 <= c.c && c.c < l.cols && 0 <= c.r && c.r < l.rows) { E(.obstacle, "\(k.rawValue) \(id.raw) cell \(t(c)) outside the grid") }
                    if hiders.contains(k), let v = visibleCells[c] { E(.obstacle, "\(k.rawValue) \(id.raw) covers visible arrow \(v.raw) at \(t(c))") }
                    if k != .elevator {
                        if let h = hiderCells[c], under[id] != h { E(.obstacle, "\(k.rawValue) \(id.raw) overlaps \(h.raw) at \(t(c))") }
                        if hiderCells[c] == nil { hiderCells[c] = id }
                    }
                }
            }
            let rawO = rawObs?.first { $0["id"]?.stringValue == id.raw }
            switch k {
            case .tape:
                let mem = o.arrows
                if !(2...4).contains(mem.count) { E(.obstacle, "tape \(id.raw) binds \(mem.count) arrows") }
                let ms = mem.map { A[$0] }
                if ms.contains(where: { $0 == nil }) { E(.obstacle, "tape \(id.raw): unknown member"); continue }
                let members = ms.map { $0! }
                let dirs = Set(members.map(\.dir)), lens = Set(members.map(\.cells.count))
                if dirs.count != 1 || lens.count != 1 {
                    E(.obstacle, "tape \(id.raw) members differ (dirs \(dirs.map(\.rawValue).sorted()), lengths \(lens.sorted()))")
                }
                for m in members where zip(m.cells, m.cells.dropFirst()).contains(where: { Dir(from: $0, to: $1) != m.dir }) {
                    E(.obstacle, "tape \(id.raw) member \(m.id.raw) is not straight")
                }
                let ties = Set(members.compactMap { $0.cells.count >= 2 ? $0.cells[$0.cells.count - 2] : nil })
                if cs.count != mem.count || ties != Set(cs) {
                    E(.obstacle, "tape \(id.raw) tie cells [\(cs.map(t).joined(separator: ", "))] are not each member's cell behind the head")
                }
                if Set(members.map { $0.hiddenBy?.raw ?? "" }).count != 1 { E(.obstacle, "tape \(id.raw) members hidden differently") }
            case .door, .box, .curtain:
                if !isRect(cs) { E(.obstacle, "\(k.rawValue) \(id.raw) is not a rectangle") }
                if k == .door && cs.count < 4 { E(.obstacle, "door \(id.raw) smaller than 2x2") }
                let rv = Set(o.reveals)
                let hid = Set(l.arrows.filter { $0.hiddenBy == id }.map(\.id))
                if rv != hid {
                    E(.obstacle, "\(k.rawValue) \(id.raw) reveals \(list(rv.map(\.raw).sorted())) != arrows hidden by it \(list(hid.map(\.raw).sorted()))")
                }
                let cset = Set(cs)
                for aid in hid.sorted() {
                    let outCells = Set(A[aid]!.cells).subtracting(cset)
                    if outCells.isEmpty { continue }
                    if k != .door { E(.obstacle, "\(k.rawValue) \(id.raw): hidden arrow \(aid.raw) sticks out") }
                    else { stubs.append((id, aid, outCells)) }
                }
                if k == .box || k == .curtain {
                    let rawInt = rawO?["counter"].map { $0.intValue != nil } ?? true
                    if o.counter == nil || !rawInt || o.counter! < 1 {
                        E(.obstacle, "\(k.rawValue) \(id.raw) counter \(o.counter.map(String.init) ?? "None")")
                    } else if o.counter! >= l.arrows.count {
                        E(.obstacle, "\(k.rawValue) \(id.raw) counter \(o.counter!) >= \(l.arrows.count) arrows (never breaks)")
                    }
                }
            case .key:
                if o.arrows.count != 1 || A[o.arrows[0]] == nil {
                    E(.obstacle, "key \(id.raw) rider \(list(o.arrows.map(\.raw)))")
                    continue
                }
                let rc = Set(A[o.arrows[0]]!.cells)
                if cs.count != 2 || !Set(cs).isSubset(of: rc) { E(.obstacle, "key \(id.raw) cells [\(cs.map(t).joined(separator: ", "))] not on its rider") }
                if let d = o.opens, O[d] == nil && !l.obstacles.contains(where: { $0.id == d }) { E(.obstacle, "key \(id.raw) opens unknown \(d.raw)") }
            case .pipe:
                let ends = o.ends
                if ends.count != 2 { E(.obstacle, "pipe \(id.raw) has \(ends.count) ends"); continue }
                if zip(cs, cs.dropFirst()).contains(where: { Dir(from: $0, to: $1) == nil }) || Set(cs).count != cs.count {
                    E(.obstacle, "pipe \(id.raw) cells are not an ordered 4-connected path")
                } else if cs.isEmpty || [ends[0].cell, ends[1].cell] != [cs[0], cs[cs.count - 1]] {
                    E(.obstacle, "pipe \(id.raw) ends [\(ends.map { "[\($0.cell.c), \($0.cell.r)]" }.joined(separator: ", "))] are not its extremities")
                } else if cs.count >= 2 && (ends[0].out != Dir(from: cs[1], to: cs[0]) || ends[1].out != Dir(from: cs[cs.count - 2], to: cs[cs.count - 1])) {
                    E(.obstacle, "pipe \(id.raw) mouth directions do not continue the tube")
                }
                let rawInt = rawO?["counter"].map { $0.intValue != nil } ?? true
                if o.counter == nil || !rawInt || !(1...9).contains(o.counter!) { E(.obstacle, "pipe \(id.raw) counter \(o.counter.map(String.init) ?? "None")") }
                if let at = o.counterAt, at.count >= 2, !cs.isEmpty,
                   cs.map({ abs(at[0] - Double($0.c)) + abs(at[1] - Double($0.r)) }).min()! <= 1.0 {
                    // on the tube
                } else {
                    E(.obstacle, "pipe \(id.raw) counter_at \(o.counterAt.map { "[" + $0.map(ContentJSON.pyRepr).joined(separator: ", ") + "]" } ?? "None") not on the tube")
                }
            case .elevator:
                if !isRect(cs) { E(.obstacle, "elevator \(id.raw) is not a rectangle") }
                let cset = Set(cs)
                let plat = Set(l.arrows.filter { $0.layer == 1 && $0.hiddenBy == nil && Set($0.cells).isSubset(of: cset) }.map(\.id))
                if Set(o.arrows) != plat {
                    E(.obstacle, "elevator \(id.raw) platform \(list(o.arrows.map(\.raw))) != layer-1 arrows inside \(list(plat.map(\.raw).sorted()))")
                }
                let l2 = Set(l.arrows.filter { $0.hiddenBy == id }.map(\.id))
                if Set(o.reveals) != l2 { E(.obstacle, "elevator \(id.raw) reveals != its layer-2 arrows") }
                for aid in l2.sorted() where A[aid]!.layer != 2 { E(.obstacle, "elevator \(id.raw): hidden arrow \(aid.raw) not on layer 2") }
            case .corner:
                if cs.count != 1 || o.turn == nil { E(.obstacle, "corner \(id.raw)") }
            }
        }
        let doors = oOrder.compactMap { O[$0] }.filter { $0.kind == .door }
        let keys = oOrder.compactMap { O[$0] }.filter { $0.kind == .key }
        if keys.count != doors.count { E(.obstacle, "\(keys.count) keys for \(doors.count) doors") }
        let orders = doors.map { $0.order ?? -1 }.sorted()
        if orders != Array(0..<doors.count) { E(.obstacle, "door orders \(list(orders))") }
        for a in l.arrows { if let hb = a.hiddenBy, O[hb] == nil { E(.obstacle, "arrow \(a.id.raw) hidden by unknown \(hb.raw)") } }
        // A hidden arrow may poke out of its door (drawn there at the start, as v552 L62 shows) only where no ray can reach
        // it while the door is shut: then whether a hidden cell blocks is moot (the rules keep hidden arrows inert).
        if !stubs.isEmpty {
            let S = RefStatic(l)
            for st in stubs {
                // (the reference iterates a Python set here; sorted (column, row) is our deterministic order)
                for c in st.out.sorted(by: { ($0.c, $0.r) < ($1.c, $1.r) }) where visibleCells[c] != nil || hiderCells[c] != nil {
                    E(.obstacle, "door \(st.door.raw): hidden arrow \(st.arrow.raw) pokes out onto an occupied cell \(t(c))")
                }
                // every other door open, every box broken, the arrows alone one at a time (pipes intact)
                var bb = RefBoard(S)
                for i in 0..<S.n { bb.hidden[i] = false; bb.alive[i] = false }
                for d in S.doors where S.obs[d].id != st.door { bb.doorOpen[d] = true }
                for x in S.boxKinds { bb.boxBroken[x] = true }
                for a in l.arrows where a.hiddenBy != st.door {
                    guard let i = S.index(of: a.id) else { continue }
                    var one = bb
                    one.alive[i] = true
                    let hit = Set(one.walkTrace(i).trace.cells).intersection(st.out)
                    if !hit.isEmpty {
                        let cells = hit.sorted { ($0.c, $0.r) < ($1.c, $1.r) }.map(t).joined(separator: ", ")
                        E(.obstacle, "door \(st.door.raw): hidden arrow \(st.arrow.raw) pokes out at [\(cells)], which arrow \(a.id.raw)'s ray can reach")
                        break
                    }
                }
            }
        }
        // sprites (§4.14 + CONSISTENCY O-21 / O-23)
        if let sprites {
            for o in l.obstacles {
                for sid in spriteIDs(o) where !sprites.contains(sid) {
                    E(.sprite, "\(o.kind.rawValue) \(o.id.raw) needs sprite \(sid), which the catalogue lacks")
                }
            }
        }
        if out.contains(where: { $0.severity == .error }) { return LevelReport(level: L, findings: out, measured: nil) }

        // the full self-ray check (through pipes / corners): from an empty board the walk never meets the arrow itself
        let S = RefStatic(l)
        var b0 = RefBoard(S)
        for i in 0..<S.n { b0.hidden[i] = false; b0.alive[i] = false }
        for d in S.doors { b0.doorOpen[d] = true }
        for x in S.boxKinds { b0.boxBroken[x] = true }
        for i in 0..<S.n {
            var bb = b0
            bb.alive[i] = true
            if bb.walk(i, ignore: []).blocker == .arrow(i) { E(.structure, "arrow \(S.ids[i].raw): its ray meets its own body (through a pipe/corner)") }
        }
        // no ray can loop: from an empty board (every door open, every box broken), with every pipe intact and with every
        // pipe broken, no walk may reach the pipe/corner hop guard (a corner or pipe cycle would freeze a game walk
        // without one)
        if l.obstacles.contains(where: { $0.kind == .pipe || $0.kind == .corner }) {
            for broken in [false, true] {
                var bl = b0
                if broken { for p in S.pipes { bl.pipeBroken[p] = true } }
                for a in l.arrows {
                    guard let i = S.index(of: a.id) else { continue }
                    var one = bl
                    one.alive[i] = true
                    let w = one.walkTrace(i)
                    if w.passages.count + w.trace.corners >= ContentRules.maxHops {
                        E(.structure, "arrow \(a.id.raw): its ray loops through pipes/corners")
                        break
                    }
                }
            }
        }
        // solvable with the greedy solver; the obstacles are all used
        let g = ContentRules.greedy(RefBoard(S))
        if !g.ok {
            let d = ContentRules.dfs(l, budget: 150_000)
            E(.solver, "greedy solver stuck with \(g.stuck.count) units left (DFS: \(d.ok ? "solvable" : (d.exhausted ? "undecided" : "UNSOLVABLE")))")
            return LevelReport(level: L, findings: out, measured: nil)
        }
        var b = RefBoard(S)
        var usedPipes = Set<Int>(), usedBoxes = Set<Int>(), usedDoors = Set<Int>(), usedElev = Set<Int>()
        for u in g.order {
            guard let a = S.ids.firstIndex(of: u[0]), case .exit(let unit, let p) = b.resolve(a) else { continue }
            for ps in p { for q in ps { usedPipes.insert(q) } }
            var ev = b.commitExit(unit, p)
            ev += b.openPendingDoors()
            for e in ev {
                switch e {
                case .boxBreak(let x): usedBoxes.insert(x)
                case .doorOpened(let x): usedDoors.insert(x)
                case .elevatorActivated(let x): usedElev.insert(x)
                default: break
                }
            }
        }
        for id in oOrder {
            guard let k = S.obsIndex[id] else { continue }
            let o = S.obs[k]
            switch o.kind {
            case .pipe where !usedPipes.contains(k): E(.solver, "pipe \(id.raw) is never passed in the solution")
            case .box where !usedBoxes.contains(k), .curtain where !usedBoxes.contains(k): E(.solver, "box \(id.raw) never breaks in the solution")
            case .door where !usedDoors.contains(k): E(.solver, "door \(id.raw) never opens")
            case .elevator where !usedElev.contains(k): E(.solver, "elevator \(id.raw) never activates")
            default: break
            }
        }
        // no dead end: seeded random play orders must all clear a non-monotone board (SPEC-gameplay §3.11)
        if l.obstacles.contains(where: { $0.kind == .pipe || $0.kind == .elevator || $0.kind == .corner }) {
            var rng = PathRandom(seed: UInt64(bitPattern: Int64(1000 + L)))
            for _ in 0..<options.randomOrders {
                let r = RefResolver(RefBoard(S))
                while !r.b.cleared {
                    let fu = r.freeUnits()
                    if fu.isEmpty {
                        if !r.b.pendingDoors.isEmpty { r.openPendingDoors(); continue }
                        E(.solver, "dead end: a random play order gets stuck with \(r.b.aliveCount) arrows left")
                        break
                    }
                    let (u, p) = fu[rng.below(fu.count)]
                    r.commitExit(u, p)
                    r.openPendingDoors()
                }
                if !r.b.cleared { break }
            }
        }
        let m = ContentRules.metrics(l, board: RefBoard(S))
        if m.botTimeLeft < 0.2 * Double(l.timerSeconds) {
            E(.metrics, "the 0.6 s/tap driver keeps only \(String(format: "%.0f", m.botTimeLeft)) s of \(l.timerSeconds)")
        }
        if let lm = l.metrics {
            let bm = m.bundle
            var pairs: [(String, String, String, Bool)] = [
                ("rounds", String(lm.rounds), String(bm.rounds), lm.rounds == bm.rounds),
                ("free_at_start", String(lm.freeAtStart), String(bm.freeAtStart), lm.freeAtStart == bm.freeAtStart),
                ("arrows", String(lm.arrows), String(bm.arrows), lm.arrows == bm.arrows),
                ("cells", String(lm.cells), String(bm.cells), lm.cells == bm.cells),
                ("mean_length", ContentJSON.pyRepr(lm.meanLength), ContentJSON.pyRepr(bm.meanLength), lm.meanLength == bm.meanLength),
            ]
            if let k = LevelCoding.botTimeKey {             // FIX-2 B (N-01): the research metric, macOS tools only
                let stored: String = lm.botTimeLeft.map(ContentJSON.pyRepr) ?? "None"
                let recomputed: String = ContentJSON.pyRepr(bm.botTimeLeft ?? 0)
                pairs.append((k, stored, recomputed, lm.botTimeLeft == bm.botTimeLeft))
            }
            if let bad = pairs.first(where: { !$0.3 }) { E(.metrics, "metrics.\(bad.0) \(bad.1) != recomputed \(bad.2)") }
        }
        // the game's own rules (C2): its greedy clears the level and the HeadlessDriver wins it at 0.6 s per tap
        if options.gameRules {
            let cg = Solver.greedy(l, rules: options.rules)
            if !cg.solved { out.append(Finding(.error, .gameRules, level: L, "the game's greedy solver is stuck with \(cg.stuck.count) arrows left")) }
            // a seeded human-like player: any free unit at 0.6 s per tap (the greedy above already proved the level
            // solvable under these rules; this proves a human-pace win through the session's modelled beats and that a
            // random order does not dead-end under the game's rules either)
            let r = HeadlessDriver.play(level: l, rules: options.rules, config: {
                var c = DriverConfig(strategy: .randomFree, tapInterval: ContentRules.tapSeconds,
                                     seed: UInt64(bitPattern: Int64(1000 + L)))
                c.recordEvents = false
                return c
            }())
            if !r.won {
                out.append(Finding(.error, .gameRules, level: L, "the 0.6 s/tap driver does not win under the game's rules (stuck \(r.stuck.count), \(r.loss.map { "\($0)" } ?? "no loss"))"))
            } else if r.timeLeftFraction < 0.2 {
                out.append(Finding(.error, .gameRules, level: L, String(format: "the 0.6 s/tap driver wins with only %.0f %% of the timer left", 100 * r.timeLeftFraction)))
            }
        }
        return LevelReport(level: L, findings: out, measured: m)
    }

    static func isRect(_ cells: [Cell]) -> Bool {
        let cs = Set(cells)
        guard !cs.isEmpty else { return false }
        let xs = cs.map(\.c), ys = cs.map(\.r)
        return cs.count == (xs.max()! - xs.min()! + 1) * (ys.max()! - ys.min()! + 1)
    }

    /// The sprite ids an obstacle needs from the art (§5.6; doors and boxes per CONSISTENCY O-23 / O-21).
    public static func spriteIDs(_ o: ObstacleSpec) -> [String] {
        switch o.kind {
        case .tape:
            if let s = o.sprite { return [s] }
            guard !o.cells.isEmpty else { return [] }
            let cols = Set(o.cells.map(\.c)).count, rows = Set(o.cells.map(\.r)).count
            let lanes = o.cells.count
            return [rows >= cols ? "tapeV\(lanes)" : "tapeH\(lanes)"]      // App/Board/TapeLayer.spriteID
        case .door: return ["lockHex"]
        case .key: return ["keyOnArrow"]
        case .pipe: return ["pipeMouth", "pipeCounter"]
        case .box: return ["boxRing"]
        case .curtain: return ["boxRing"]             // FIX-2 B: a curtain wears the BOX skin (ruling 11, App ObstacleSet); curtainCrate is NOT SHIPPED
        case .corner: return ["cornerWedge"]
        case .elevator: return []
        }
    }

    // MARK: - a content set

    /// design/levels.json (the whole document).
    public static func checkDocument(_ doc: JSONValue, sprites: SpriteCatalog? = nil, options: Options = Options()) -> Report {
        let rawLevels = doc["levels"]?.arrayValue ?? []
        var levels: [(LevelSpec?, JSONValue)] = []
        var decodeErrors: [Finding] = []
        for r in rawLevels {
            do { levels.append((try JSONDecoder().decode(LevelSpec.self, from: ContentJSON.data(r)), r)) } catch {
                decodeErrors.append(Finding(.error, .schema, level: r["level"]?.intValue, "does not decode: \(error)"))
                levels.append((nil, r))
            }
        }
        let end = doc["authoredEnd"]?.intValue ?? rawLevels.count
        return checkSet(levels: levels, authoredEnd: end, unlocks: doc["unlocks"]?.arrayValue ?? [],
                        sessions: doc["sessions"]?.arrayValue ?? [], tutorials: doc["tutorials"]?.arrayValue ?? [],
                        extra: decodeErrors, sprites: sprites, options: options)
    }

    /// A bundle folder (App/Resources/Levels: level_NNNN.json, sessions.json, unlocks.json, tutorials.json).
    public static func checkFolder(_ folder: URL, sprites: SpriteCatalog? = nil, options: Options = Options()) throws -> Report {
        let fm = FileManager.default
        var files: [(Int, URL)] = []
        for name in try fm.contentsOfDirectory(atPath: folder.path) {
            if let n = LevelLibrary.levelNumber(fileName: name) { files.append((n, folder.appendingPathComponent(name))) }
        }
        files.sort { $0.0 < $1.0 }
        var levels: [(LevelSpec?, JSONValue)] = []
        var extra: [Finding] = []
        for (n, url) in files {
            let data = try Data(contentsOf: url)
            let raw = (try? ContentJSON.parse(data)) ?? .null
            do {
                let l = try LevelJSON.decodeBundle(data)
                if l.level != n { extra.append(Finding(.error, .content, level: n, "\(url.lastPathComponent) holds level \(l.level)")) }
                levels.append((l, raw))
            } catch {
                extra.append(Finding(.error, .schema, level: n, "does not decode: \(error)"))
                levels.append((nil, raw))
            }
        }
        func arr(_ name: String, _ key: String) -> [JSONValue] {
            guard let d = try? Data(contentsOf: folder.appendingPathComponent(name)), let v = try? ContentJSON.parse(d) else { return [] }
            return v.arrayValue ?? v[key]?.arrayValue ?? []
        }
        return checkSet(levels: levels, authoredEnd: files.last?.0 ?? 0, unlocks: arr("unlocks.json", "unlocks"),
                        sessions: arr("sessions.json", "sessions"), tutorials: arr("tutorials.json", "tutorials"),
                        extra: extra, sprites: sprites, options: options)
    }

    static func checkSet(levels: [(LevelSpec?, JSONValue)], authoredEnd end: Int, unlocks: [JSONValue], sessions: [JSONValue],
                         tutorials: [JSONValue], extra: [Finding], sprites: SpriteCatalog?, options: Options) -> Report {
        var findings = extra
        var reports: [LevelReport] = []
        func E(_ a: Finding.Area, _ m: String) { findings.append(Finding(.error, a, level: nil, m)) }
        let nums = levels.map { $0.0?.level ?? $0.1["level"]?.intValue ?? -1 }
        if nums != Array(0..<end).map({ $0 + 1 }) { E(.content, "level numbers are not 1..\(end)") }
        // per level (independent: run concurrently, reported in order)
        var slots = [LevelReport?](repeating: nil, count: levels.count)
        let lock = NSLock()
        DispatchQueue.concurrentPerform(iterations: levels.count) { i in
            guard let l = levels[i].0 else { return }
            let r = checkLevel(l, raw: levels[i].1, sprites: sprites, options: options)
            lock.lock(); slots[i] = r; lock.unlock()
        }
        for r in slots.compactMap({ $0 }) { reports.append(r); findings.append(contentsOf: r.findings) }
        let specs = levels.compactMap(\.0)
        let (cross, first) = crossChecks(specs, authoredEnd: end, unlocks: unlocks, sessions: sessions, tutorials: tutorials)
        findings.append(contentsOf: cross)
        return Report(levels: reports, findings: findings, firstAppearance: first)
    }

    /// The checks across levels (the reference `main`): unlock cards exactly at each feature's first appearance,
    /// unlocks.json, sessions and tutorials pointing at real content, no two boards identical.
    public static func crossChecks(_ specs: [LevelSpec], authoredEnd end: Int, unlocks: [JSONValue], sessions: [JSONValue],
                                   tutorials: [JSONValue]) -> (findings: [Finding], firstAppearance: [String: Int]) {
        var findings: [Finding] = []
        func E(_ a: Finding.Area, _ m: String) { findings.append(Finding(.error, a, level: nil, m)) }
        // unlock cards at first appearance
        var first: [String: Int] = [:]
        for l in specs { for o in l.obstacles { if let f = featureOf[o.kind], first[f] == nil { first[f] = l.level } } }
        var unl: [String: JSONValue] = [:]
        for u in unlocks { if let f = u["feature"]?.stringValue { unl[f] = u } }
        let byNumber = Dictionary(specs.map { ($0.level, $0) }, uniquingKeysWith: { a, _ in a })
        for (f, n) in first.sorted(by: { $0.value < $1.value }) {
            let lv = byNumber[n]
            if lv?.unlock?.rawValue != f { E(.content, "L\(n): first \(f) but unlock=\(lv?.unlock?.rawValue ?? "None")") }
            if unl[f] == nil || unl[f]?["level"]?.intValue != n {
                E(.content, "unlocks.json: \(f) should be at L\(n) (\(unl[f]?["level"]?.intValue.map(String.init) ?? "None"))")
            }
        }
        for l in specs { if let u = l.unlock, first[u.rawValue] != l.level { E(.content, "L\(l.level): unlock \(u.rawValue) is not a first appearance") } }
        for f in unl.keys.sorted() where first[f] == nil { E(.content, "unlocks.json: \(f) never appears") }
        for s in sessions {
            for n in s["levels"]?.arrayValue?.compactMap(\.intValue) ?? [] where !(1...max(1, end)).contains(n) {
                E(.content, "session \(s["id"]?.stringValue ?? "?") level \(n)")
            }
        }
        for t in tutorials {
            guard let n = t["level"]?.intValue, let lv = byNumber[n] else { continue }
            if let hand = t["hand"], hand.isTruthy, let a = hand["arrow"]?.intValue, !lv.arrows.contains(where: { $0.id.raw == a }) {
                E(.content, "tutorial \(t["id"]?.stringValue ?? "?") points at a missing arrow")
            }
        }
        // no repeated board (SPEC.md §5 item 28, content recast 2: design/tools/repeats.py): offset-free and under the 8
        // symmetries of the square, on the start-visible arrows OR on every layer; the FIRST occurrence is named
        var firstVisible: [[[Int]]: Int] = [:], firstFull: [[[Int]]: Int] = [:]
        for l in specs {
            let k = canonicalKeys(l)
            if let prev = [firstVisible[k.visible], firstFull[k.full]].compactMap({ $0 }).min() {
                E(.content, "L\(l.level) repeats L\(prev)")
                continue                                   // a repeat is never the first occurrence of anything
            }
            firstVisible[k.visible] = l.level
            firstFull[k.full] = l.level
        }
        return (findings, first)
    }

    /// repeats.py's keys (content recast 2): each arrow as [dir index, x, y, x, y, …] (its cells sorted) after one of the 8
    /// symmetries of the square maps every cell and the head direction, the board shifted to its min column / min row, the
    /// arrows sorted; the smallest of the 8 images is the key (two boards related by a symmetry have the same 8 images, so
    /// the same smallest one). `visible` = the arrows visible at the start (no hider, layer 1), `full` = every arrow.
    static func canonicalKeys(_ l: LevelSpec) -> (visible: [[Int]], full: [[Int]]) {
        let visible: [ArrowSpec] = l.arrows.filter { $0.hiddenBy == nil && $0.layer <= 1 }
        return (symmetryKey(visible), symmetryKey(l.arrows))
    }

    /// The dihedral group D4 on (x, y): (a, b, c, d) maps (x, y) to (a·x + b·y, c·x + d·y) — repeats.py's SYMS order.
    static let squareSymmetries: [[Int]] = [[1, 0, 0, 1], [0, -1, 1, 0], [-1, 0, 0, -1], [0, 1, -1, 0],
                                            [-1, 0, 0, 1], [1, 0, 0, -1], [0, 1, 1, 0], [0, -1, -1, 0]]

    static func symmetryKey(_ arrows: [ArrowSpec]) -> [[Int]] {
        if arrows.isEmpty { return [] }
        var best: [[Int]] = []
        for (k, m) in squareSymmetries.enumerated() {
            let a: Int = m[0], b: Int = m[1], c: Int = m[2], d: Int = m[3]
            var dirs: [Int] = []
            var cellLists: [[(Int, Int)]] = []
            var x0: Int = Int.max, y0: Int = Int.max
            for ar in arrows {
                let v: (Int, Int)
                switch ar.dir {
                case .up: v = (0, -1)
                case .down: v = (0, 1)
                case .left: v = (-1, 0)
                case .right: v = (1, 0)
                }
                let vx: Int = a * v.0 + b * v.1
                let vy: Int = c * v.0 + d * v.1
                let di: Int = vy == -1 ? 0 : vy == 1 ? 1 : vx == -1 ? 2 : 3
                dirs.append(di)
                var cs: [(Int, Int)] = []
                for cell in ar.cells {
                    let x: Int = a * cell.c + b * cell.r
                    let y: Int = c * cell.c + d * cell.r
                    x0 = min(x0, x)
                    y0 = min(y0, y)
                    cs.append((x, y))
                }
                cellLists.append(cs)
            }
            var img: [[Int]] = []
            for (i, cs) in cellLists.enumerated() {
                let shifted: [(Int, Int)] = cs.map { (p: (Int, Int)) -> (Int, Int) in (p.0 - x0, p.1 - y0) }
                let sorted: [(Int, Int)] = shifted.sorted { (p: (Int, Int), q: (Int, Int)) -> Bool in p.0 != q.0 ? p.0 < q.0 : p.1 < q.1 }
                var row: [Int] = [dirs[i]]
                for p in sorted { row.append(p.0); row.append(p.1) }
                img.append(row)
            }
            img.sort { (p: [Int], q: [Int]) -> Bool in p.lexicographicallyPrecedes(q) }
            if k == 0 || img.lexicographicallyPrecedes(best, by: { (p: [Int], q: [Int]) -> Bool in p.lexicographicallyPrecedes(q) }) {
                best = img
            }
        }
        return best
    }

    /// The reference's `board_key`, offset-free (recast 2026-09-25: v552 repeats boards cell for cell 20 levels later, and a
    /// repeat read in another frame must still be caught): the set of (head, dir) and every arrow cell, shifted to the
    /// board's top-left arrow cell (min column, min row of all arrow cells).
    static func boardKey(_ l: LevelSpec) -> [Int] {
        let all = l.arrows.flatMap(\.cells)
        guard let x0 = all.map(\.c).min(), let y0 = all.map(\.r).min() else { return [] }
        var s = Set<Int>()
        for a in l.arrows {
            if let h = a.cells.last {
                let d = Dir.allCases.firstIndex(of: a.dir)!
                s.insert(1 << 40 | ((h.c - x0) & 0xFFFF) << 20 | ((h.r - y0) & 0xFFFF) << 4 | d)
            }
            for c in a.cells { s.insert(2 << 40 | ((c.c - x0) & 0xFFFF) << 20 | ((c.r - y0) & 0xFFFF) << 4) }
        }
        return s.sorted()
    }
}

extension Array {
    subscript(safe i: Int) -> Element? { i >= 0 && i < count ? self[i] : nil }
}
