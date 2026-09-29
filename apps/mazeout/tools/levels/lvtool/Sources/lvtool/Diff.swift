import Foundation
import PathCore

// `lvtool diff <design/levels.json | levels dir> [--research research/levels] [--backfill design/tools/work/reveals] [--report FILE]`
//
// PUBLISH B0 (level re-order + provenance strip): a board's research file is found by its RESEARCH SLOT (researchSlot:
// its capture / `_from`), never by the level it ships at; the shipped bundle carries no provenance, so the diff reads
// design/levels.json (a bundle folder still works while its files carry their captures).
//
// L1 acceptance: "recorded levels equal their research JSON cell for cell after the reveal merge" (and the video levels
// equal their extraction). Every bundled level with source recorded/video is compared with the research file it was read
// from, imported by C1's reader (`LevelJSON.load(_:reveals:)`, the `pclevels import` path):
//   HARD (errors): every start-visible arrow (id, cells tail→head, dir); the elevator layer-2 arrows (id, cells, dir,
//     layer, hider); tape bundles (members); pipe cells, mouths and (video) counters; video box cells and counters;
//     elevator platforms; the arrows the phone's own open-state files (Lnnn-openK.json, merged by C1) show under a door;
//     grid size; timer and tag (a substitute keeps its phone slot's timer and tag, ORCH 19).
//   COMPLETIONS (listed, not errors): what the phone schema does not carry and LEVELS.md §2.2/§3 completed — box/pipe
//     counters, door rectangles and order, keys and arrows under doors (checked instead against the reveal backfill,
//     design/tools/work/reveals/Lnnn.json, id for id).

struct Diff {
    var errors: [String] = []
    var completions: [String] = []
    var checked: [String: Int] = [:]
}

func arrowKey(_ a: ArrowSpec) -> String { "\(cellsKey(a.cells))>\(a.dir.rawValue)" }

func researchFile(for l: LevelSpec, rslot: Int, research: String) -> String {
    if let cap = l.capture, let r = cap.range(of: #"V2/L0(3[2-8])-start\.png"#, options: .regularExpression) {
        let n = cap[r].dropFirst(3).prefix(4)                    // "L032"
        return "\(research)/video/V2-\(n).json"
    }
    return String(format: "%@/L%03d.json", research, rslot)
}

func phoneSlot(_ level: Int, research: String) -> [String: Any]? {
    let p = String(format: "%@/L%03d.json", research, level)
    guard let d = FileManager.default.contents(atPath: p) else { return nil }
    return (try? JSONSerialization.jsonObject(with: d)) as? [String: Any]
}

/// `rslot` = the board's research slot (researchSlot); the findings are named by the level the board ships at.
func diffLevel(_ b: LevelSpec, rslot: Int, research: String, backfill: String) throws -> Diff {
    var d = Diff()
    func E(_ s: String) { d.errors.append("L\(b.level): \(s)") }
    func C(_ s: String) { d.completions.append("L\(b.level): \(s)") }
    let path = researchFile(for: b, rslot: rslot, research: research)
    let data = try readData(path)
    var opens: [Data] = []
    if b.source == .authored {
        let dir = (path as NSString).deletingLastPathComponent
        let base = ((path as NSString).lastPathComponent as NSString).deletingPathExtension
        let names = (try? FileManager.default.contentsOfDirectory(atPath: dir)) ?? []
        for n in names.filter({ $0.hasPrefix(base + "-open") && $0.hasSuffix(".json") }).sorted() {
            opens.append(try readData("\(dir)/\(n)"))
        }
    }
    let base = try LevelJSON.load(data)                               // start state only
    let merged = opens.isEmpty ? base : try LevelJSON.load(data, reveals: opens)
    let r = base.level
    d.checked["research_file"] = 1

    // grid
    if (r.cols, r.rows) != (b.cols, b.rows) {
        E("grid \(b.cols)x\(b.rows) vs research \(r.cols)x\(r.rows)")
    }
    // visible arrows: id, cells, dir
    let bv = Dictionary(b.arrows.filter { $0.hiddenBy == nil && $0.layer == 1 }.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
    let rv = Dictionary(r.arrows.filter { $0.hiddenBy == nil && $0.layer == 1 }.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
    if Set(bv.keys) != Set(rv.keys) {
        let onlyB = Set(bv.keys).subtracting(rv.keys).map(\.raw).sorted(), onlyR = Set(rv.keys).subtracting(bv.keys).map(\.raw).sorted()
        E("visible arrow ids differ: bundle-only \(onlyB), research-only \(onlyR)")
    }
    var same = 0
    for (id, a) in bv { if let x = rv[id] { if x.cells == a.cells && x.dir == a.dir { same += 1 } else { E("arrow \(id.raw) differs: \(arrowKey(a)) vs research \(arrowKey(x))") } } }
    d.checked["visible_arrows"] = bv.count
    d.checked["visible_arrows_equal"] = same

    // elevator layer-2 arrows (video): id for id
    let bl2 = b.arrows.filter { $0.layer == 2 }
    let rl2 = Dictionary(r.arrows.filter { $0.layer == 2 }.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
    if bl2.count != rl2.count { E("layer-2 arrows: \(bl2.count) vs research \(rl2.count)") }
    for a in bl2 {
        guard let x = rl2[a.id] else { E("layer-2 arrow \(a.id.raw) not in research"); continue }
        if x.cells != a.cells || x.dir != a.dir || x.hiddenBy != a.hiddenBy { E("layer-2 arrow \(a.id.raw) differs") }
    }
    d.checked["layer2_arrows"] = bl2.count

    // tapes: member sets (+ tie cells)
    func tapes(_ l: LevelSpec) -> Set<String> {
        Set(l.obstacles.filter { $0.kind == .tape }.map { $0.arrows.map(\.raw).sorted().map(String.init).joined(separator: ",") })
    }
    let bt = Set(b.obstacles.filter { $0.kind == .tape && $0.arrows.allSatisfy { id in bv[id] != nil } }
                  .map { $0.arrows.map(\.raw).sorted().map(String.init).joined(separator: ",") })
    if bt != tapes(r) { E("tape bundles \(bt.sorted()) vs research \(tapes(r).sorted())") }
    d.checked["tapes"] = bt.count

    // pipes: matched by cell overlap. A research pipe WITH mouths (pipes[] / video) must equal the bundle's cells, mouths
    // and (video) counter. One WITHOUT mouths (the phone reader wrote no pipes[] from L47 on: a bare blob) must contain the
    // bundle's tube; the mouths come from the tube shape and extra blob cells were dropped (LEVELS.md §2.2, L48/L49/L56).
    let bps = b.obstacles.filter { $0.kind == .pipe }, rps = r.obstacles.filter { $0.kind == .pipe }
    if bps.count != rps.count { E("pipes: \(bps.count) vs research \(rps.count)") }
    var usedR = Set<Int>()
    for p in bps {
        let pc = Set(p.cells.map(cellKey))
        let best = rps.indices.filter { !usedR.contains($0) }
            .max { Set(rps[$0].cells.map(cellKey)).intersection(pc).count < Set(rps[$1].cells.map(cellKey)).intersection(pc).count }
        guard let k = best, !Set(rps[k].cells.map(cellKey)).isDisjoint(with: pc) else { E("pipe \(p.id.raw) has no research counterpart"); continue }
        usedR.insert(k)
        let x = rps[k], xc = Set(x.cells.map(cellKey))
        let ends = Set(p.ends.map { "\(cellKey($0.cell))\($0.out.rawValue)" }), xe = Set(x.ends.map { "\(cellKey($0.cell))\($0.out.rawValue)" })
        if x.ends.isEmpty {
            if !pc.isSubset(of: xc) { E("pipe \(p.id.raw) tube leaves the research blob") }
            let dropped = xc.subtracting(pc).sorted()
            C("pipe \(p.id.raw): mouths \(ends.sorted()) from the tube shape (the research blob has no mouths)" + (dropped.isEmpty ? "" : "; blob cells \(dropped) dropped (not tube)"))
        } else {
            if pc != xc { E("pipe \(p.id.raw) cells differ from research") }
            if ends != xe { E("pipe \(p.id.raw) mouths \(ends.sorted()) vs research \(xe.sorted())") }
        }
        if let n = x.counter { if n != p.counter { E("pipe \(p.id.raw) counter \(p.counter ?? -1) vs research \(n)") } }
        else { C("pipe \(p.id.raw) counter \(p.counter ?? -1) (the research JSON has none; levels.md, LEVELS.md §2.2)") }
    }
    d.checked["pipes"] = bps.count

    // boxes / curtains
    let bb = b.obstacles.filter { $0.kind == .box || $0.kind == .curtain }
    let rb = r.obstacles.filter { $0.kind == .box || $0.kind == .curtain }
    if b.source == .crafted {
        let bs = Set(bb.map { "\(Set($0.cells.map(cellKey)).sorted().joined(separator: ";"))#\($0.counter ?? -1)" })
        let rs = Set(rb.map { "\(Set($0.cells.map(cellKey)).sorted().joined(separator: ";"))#\($0.counter ?? -1)" })
        if bs != rs { E("boxes (cells#counter) differ: \(bb.count) vs research \(rb.count)") }
    } else if !bb.isEmpty || !rb.isEmpty {
        // the phone reader's raw box blobs (cells), not C1's bounding-box area: the L57 staircase of four touching boxes
        // is one 150-cell blob whose bounding box is larger
        var ru = Set<String>()
        if let o = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] {
            for ob in (o["obstacles"] as? [[String: Any]]) ?? [] where (ob["kind"] as? String) == "box" {
                for c in (ob["cells"] as? [[Int]]) ?? [] { ru.insert("\(c[0]),\(c[1])") }
            }
        }
        let bu = Set(bb.flatMap { $0.cells.map(cellKey) })
        if bu != ru { E("box area differs from the research blobs (\(bu.count) vs \(ru.count) cells)") }
        C("boxes \(bb.map { "\($0.id.raw)=\($0.counter ?? -1)" }.joined(separator: " ")) — counters\(bb.count != rb.count ? " and the split into \(bb.count) boxes" : "") from levels.md/shots (the phone JSON has none)")
    }
    d.checked["boxes"] = bb.count

    // elevators (video)
    let be = b.obstacles.filter { $0.kind == .elevator }, re = r.obstacles.filter { $0.kind == .elevator }
    let es = Set(be.map { "\(Set($0.cells.map(cellKey)).sorted())|\($0.arrows.map(\.raw).sorted())|\($0.reveals.map(\.raw).sorted())" })
    let ers = Set(re.map { "\(Set($0.cells.map(cellKey)).sorted())|\($0.arrows.map(\.raw).sorted())|\($0.reveals.map(\.raw).sorted())" })
    if es != ers { E("elevators differ (\(be.count) vs research \(re.count))") }
    d.checked["elevators"] = be.count

    // timer + tag (ORCH 19: a substitute keeps its phone slot's timer and tag)
    var wantTimer = r.timerSeconds, wantTag = r.tag
    let isSubstitute = b.capture?.contains("V2/L03") == true && (rslot == 35 || rslot == 45 || rslot == 51 || rslot == 52)
    if isSubstitute, let slot = phoneSlot(rslot, research: research) {
        wantTimer = (slot["timer_s"] as? Int) ?? wantTimer
        let t = slot["tag"] as? String
        wantTag = t.flatMap { LevelTag(label: $0) } ?? .normal
        d.checked["substitute_uses_phone_slot"] = 1
    }
    if rslot >= 62 && rslot <= 64 {
        // spares: 3:00; L64 takes the Hard slot (CONSISTENCY L-2, ruled)
        wantTimer = 180
        wantTag = rslot == 64 ? .hard : .normal
    }
    if b.timerSeconds != wantTimer { E("timer \(b.timerSeconds) vs \(wantTimer)") }
    if b.tag != wantTag { E("tag \(b.tag.rawValue) vs \(wantTag.rawValue)") }

    // doors and what they hide (recorded)
    let hiddenByDoor = b.arrows.filter { a in a.hiddenBy.map { h in b.obstacles.first { $0.id == h }?.kind == .door } ?? false }
    if b.source == .authored {
        // the phone's own open-state files, merged by C1: every arrow they show must be in the bundle (visible or hidden)
        if !opens.isEmpty {
            let bundleSets = Set(b.arrows.map(arrowKey))
            let revealed = merged.level.arrows.filter { $0.hiddenBy != nil }
            var found = 0
            for a in revealed { if bundleSets.contains(arrowKey(a)) { found += 1 } else { E("open-state arrow \(arrowKey(a)) is not in the bundle") } }
            d.checked["open_state_files"] = opens.count
            d.checked["open_state_arrows_found"] = found
            d.checked["open_state_arrows"] = revealed.count
        }
        // the reveal backfill: id for id
        let bf = String(format: "%@/L%03d.json", backfill, rslot)
        if let bdata = FileManager.default.contents(atPath: bf), let o = (try? JSONSerialization.jsonObject(with: bdata)) as? [String: Any] {
            let doors = (o["doors"] as? [[String: Any]]) ?? []
            let hidden = (o["hidden"] as? [[String: Any]]) ?? []
            let bDoors = b.obstacles.filter { $0.kind == .door }.sorted { ($0.order ?? 0) < ($1.order ?? 0) }
            if doors.count != bDoors.count { E("doors \(bDoors.count) vs backfill \(doors.count)") }
            let byOrder = Dictionary(doors.compactMap { d -> (Int, Set<String>)? in
                guard let ord = d["order"] as? Int, let cs = d["cells"] as? [[Int]] else { return nil }
                return (ord, Set(cs.map { "\($0[0]),\($0[1])" }))
            }, uniquingKeysWith: { a, _ in a })
            let orders = byOrder.keys.sorted()
            for (i, door) in bDoors.enumerated() where i < orders.count {
                if Set(door.cells.map(cellKey)) != byOrder[orders[i]] { E("door \(door.id.raw) (order \(door.order ?? -1)) cells differ from the backfill's door \(orders[i])") }
            }
            var eq = 0
            for h in hidden {
                guard let id = h["id"] as? Int, let cs = h["cells"] as? [[Int]], let dir = h["dir"] as? String else { continue }
                guard let a = b.arrows.first(where: { $0.id == ArrowID(id) }) else { E("backfill hidden arrow \(id) missing"); continue }
                if a.cells.map({ [$0.c, $0.r] }) != cs || a.dir.rawValue != dir { E("hidden arrow \(id) differs from the backfill") }
                else if a.hiddenBy == nil { E("hidden arrow \(id) is visible in the bundle") }
                else { eq += 1 }
            }
            if hidden.count != hiddenByDoor.count { E("arrows under doors \(hiddenByDoor.count) vs backfill \(hidden.count)") }
            d.checked["backfill_hidden_equal"] = eq
            d.checked["door_hidden_arrows"] = hiddenByDoor.count
            C("\(bDoors.count) door(s), their order, keys and \(hiddenByDoor.count) arrows under them: reconstructed from the bot's round shots (LEVELS.md §3), equal to the backfill")
        } else if !hiddenByDoor.isEmpty || b.obstacles.contains(where: { $0.kind == .door }) {
            E("door level without a backfill file \(bf)")
        }
        // start-visible keys: rider
        let rKeys = Set(r.obstacles.filter { $0.kind == .key && !$0.arrows.isEmpty }.map { $0.arrows[0].raw })
        let bKeys = Set(b.obstacles.filter { $0.kind == .key }.compactMap { k -> Int? in
            guard let rider = k.arrows.first, bv[rider] != nil else { return nil }
            return rider.raw
        })
        if !rKeys.isSubset(of: bKeys) { C("keys on start arrows \(bKeys.sorted()) vs research reader \(rKeys.sorted()) (LEVELS.md §3 notes: L49's key)") }
    }
    return d
}

func cmdDiff(_ a: Args) throws -> Int32 {
    guard a.positional.count == 1 else { throw ToolError("usage: lvtool diff <design/levels.json | levels dir> [--research research/levels] [--backfill design/tools/work/reveals] [--report F]") }
    let research = a.opt("research", "research/levels"), backfill = a.opt("backfill", "design/tools/work/reveals")
    // (board, its research slot): design/levels.json carries the provenance; a bundle folder only while it keeps captures
    var boards: [(LevelSpec, Int?)] = []
    if a.positional[0].hasSuffix(".json") {
        let src = try Content.load(a.positional[0])
        for (r, l) in zip(src.raw, src.levels) {
            boards.append((l, researchSlot(source: r["source"] as? String, capture: r["capture"] as? String, from: r["_from"] as? String)))
        }
    } else {
        let lib = try LevelLibrary.load(folder: URL(fileURLWithPath: a.positional[0]))
        for n in lib.files.keys.sorted() {
            let l = try lib.loadAuthored(n)
            boards.append((l, researchSlot(source: l.source.rawValue, capture: l.capture, from: nil)))
        }
    }
    var errs: [String] = [], comps: [String] = []
    var rows: [[String: Any]] = []
    var nRec = 0, nVid = 0
    for (l, rs) in boards {
        let n = l.level
        guard l.source == .authored || l.source == .crafted else { continue }
        guard let rslot = rs else {
            errs.append("L\(n): no provenance to find its research file (the publish form strips it: run diff on design/levels.json)")
            continue
        }
        if l.source == .authored { nRec += 1 } else { nVid += 1 }
        let d = try diffLevel(l, rslot: rslot, research: research, backfill: backfill)
        errs += d.errors; comps += d.completions
        var row: [String: Any] = d.checked
        row["level"] = n; row["research_slot"] = rslot; row["source"] = l.source.rawValue
        row["research"] = researchFile(for: l, rslot: rslot, research: research)
        row["equal"] = d.errors.isEmpty
        rows.append(row)
    }
    let report: [String: Any] = ["recorded_levels": nRec, "video_levels": nVid, "errors": errs, "completions": comps, "table": rows]
    if let rp = a.options["report"] { try writeData(try reportJSON(report), rp) }
    let eq = rows.filter { ($0["equal"] as? Bool) == true }.count
    print("diff: \(nRec) recorded + \(nVid) video levels vs their research JSON (C1 import + reveal merge): \(eq)/\(rows.count) equal; \(errs.count) error(s); \(comps.count) documented completion(s)")
    for e in errs.prefix(60) { print("ERROR \(e)") }
    return errs.isEmpty ? 0 : 1
}
