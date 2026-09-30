import Foundation
import GameCore

// C1 (SPEC-architecture §4.3). The two RESEARCH readers: the phone schema (research/levels/Lnnn.json, research/bot/bot.py)
// and the video schema (research/video-frames/work/extract/V?-Lnnn.json, research/video-tools/vextract.py). Both map
// onto the one model; `pclevels import` (C4) and the recorded-vs-bundle diff test (L1) call them through
// `LevelJSON.load(_:reveals:)`.
//
// What maps exactly: level, source, capture (shot/frame), cols, rows, mask, timer_s, hearts, tag, every arrow (id, cells,
// dir, layer), tapes (members = the arrows crossing the band), keys (the arrow they hang on), pipes from `pipes[]`
// (ordered cells, mouths, counter when the video carries it), video counters, elevators (platform arrows, layer-2 arrows).
// What is RECONSTRUCTED (and said so in the report's warnings): door rectangles and their order (the phone JSON has only
// the union `door_cells` or blob bounding boxes), box areas from blob bounding boxes, counters the phone JSON does not
// carry. `design/levels.json` (SPEC-gameplay) is the authority for obstacles; the import is the authority for arrows.

// FIX-2 lane B (N-01): research only — compiled for the macOS content tools and tests (Package.swift PC_RESEARCH), never
// into the iOS app.
#if PC_RESEARCH
enum LevelImport {

    // MARK: key vocabulary (anything else is reported as UNKNOWN)

    /// Top-level keys carried into the model or used to derive it.
    static let usedTop: Set<String> = ["level", "source", "shot", "frame", "cols", "rows", "mask", "arrows", "obstacles",
                                       "timer_s", "hearts", "tag", "pipes", "door_cells", "blocker_cells", "elevators",
                                       "taped_arrow_ids", "origin_pt", "pitch_pt", "fit_px", "reveals"]
    /// Top-level research-only keys (dropped on purpose).
    static let researchTop: Set<String> = ["zoom", "stroke_pt", "anomalies", "occlusion_inferred", "reader", "note", "video",
                                           "t", "verify", "reveal",
                                           // video-sourced research/levels files (content metadata for design/levels.json):
                                           "label", "session", "reward_coins", "tutorial", "video_play", "intro_popup", "batchB",
                                           "checks", "video_alt"]
    static let usedArrow: Set<String> = ["id", "cells", "dir", "layer", "under_elevator"]
    static let usedObstacle: Set<String> = ["kind", "cells", "counter", "arrow_ids", "bbox_px"]
    static let researchObstacle: Set<String> = ["mean_rgb"]
    static let usedPipe: Set<String> = ["cells", "ends", "counter"]
    static let usedEnd: Set<String> = ["cell", "out"]
    static let usedElevator: Set<String> = ["cells", "arrow_ids", "hidden_arrow_ids"]
    static let researchElevator: Set<String> = ["t_active", "reveal_frame_t", "reveal_frame"]
    static let usedFitPx: Set<String> = ["pitch"]

    /// Capture px per pt when the JSON has no `fit_px`: phone shots are 1178 px on the 393 pt screen (§0.3).
    static let phonePxPerPt = 1178.0 / 393.0
    /// The owner's videos are 592 px wide (§0.3).
    static let videoPxPerPt = 592.0 / 393.0

    // MARK: reading

    static func research(_ o: [String: Any]) throws -> ImportedLevel {
        let schema = try LevelJSON.schema(of: o)
        var rep = ImportReport(schema: schema)
        var unknown = Set<String>(), dropped = Set<String>()
        func classify(_ obj: [String: Any], used: Set<String>, research: Set<String>, path: String) {
            for k in obj.keys {
                if used.contains(k) { continue }
                if research.contains(k) { dropped.insert(path + k) } else { unknown.insert(path + k) }
            }
        }
        classify(o, used: usedTop, research: researchTop, path: "")

        guard let level = int(o["level"]) else { throw LevelJSONError.missing("level") }
        guard let cols = int(o["cols"]), let rows = int(o["rows"]), cols > 0, rows > 0 else {
            throw LevelJSONError.missing("cols/rows")
        }
        let source = (o["source"] as? String).flatMap(LevelSource.init(rawValue:)) ?? (schema == .video ? .crafted : .authored)
        let capture = (o["shot"] as? String) ?? (o["frame"] as? String)
        let mask = o["mask"] as? [String]
        let timer: Int
        if let t = int(o["timer_s"]) { timer = t } else {
            timer = 0
            rep.warnings.append("timer_s is null → 0 (a reveal snapshot; the base level carries the timer)")
        }
        let hearts = int(o["hearts"]) ?? 3
        var tag = LevelTag.normal
        if let t = o["tag"] as? String {
            if let parsed = LevelTag(label: t) { tag = parsed } else { rep.warnings.append("tag \"\(t)\" not understood → normal") }
        }
        if let files = o["reveals"] as? [String] { rep.revealFiles = files }

        // arrows
        var arrows: [ArrowSpec] = []
        var underElevator: [ArrowID: Int] = [:]
        for (i, any) in ((o["arrows"] as? [Any]) ?? []).enumerated() {
            guard let a = any as? [String: Any] else { rep.warnings.append("arrows[\(i)] is not an object → skipped"); continue }
            classify(a, used: usedArrow, research: [], path: "arrows[].")
            guard let idRaw = int(a["id"]) else { throw LevelJSONError.missing("arrows[\(i)].id") }
            let cs = cells(a["cells"])
            guard !cs.isEmpty else { rep.warnings.append("arrow \(idRaw) has no cells → skipped"); continue }
            var dir = (a["dir"] as? String).flatMap(Dir.init(rawValue:))
            if dir == nil {
                dir = cs.count >= 2 ? Dir(from: cs[cs.count - 2], to: cs[cs.count - 1]) : nil
                rep.warnings.append("arrow \(idRaw): dir missing → \(dir?.rawValue ?? "right") from its last step")
            }
            let layer = int(a["layer"]) ?? 1
            let id = ArrowID(idRaw)
            if let u = int(a["under_elevator"]) { underElevator[id] = u }
            arrows.append(ArrowSpec(id: id, cells: cs, dir: dir ?? .right, layer: layer))
        }
        var owner: [Cell: ArrowID] = [:]
        for a in arrows where a.layer == 1 { for c in a.cells { owner[c] = a.id } }

        // geometry for bounding boxes: capture px → cells
        let pitchPt = double(o["pitch_pt"])
        let originPt = (o["origin_pt"] as? [Any]).flatMap { v -> (Double, Double)? in
            guard v.count == 2, let x = double(v[0]), let y = double(v[1]) else { return nil }
            return (x, y)
        }
        var pxPerPt = schema == .video ? videoPxPerPt : phonePxPerPt
        if let fit = o["fit_px"] as? [String: Any] {
            // Everything in fit_px but `pitch` is the capture fit's own bookkeeping (the lanes keep annotating it).
            classify(fit, used: usedFitPx, research: Set(fit.keys).subtracting(usedFitPx), path: "fit_px.")
            if let fp = double(fit["pitch"]), let pp = pitchPt, pp > 0 { pxPerPt = fp / pp }
        }
        func bboxCells(_ blob: [String: Any]) -> [Cell] {
            guard let b = blob["bbox_px"] as? [Any], b.count == 4, let x0 = double(b[0]), let y0 = double(b[1]),
                  let x1 = double(b[2]), let y1 = double(b[3]), let p = pitchPt, let org = originPt else { return [] }
            var out: [Cell] = []
            for r in 0..<rows {
                for c in 0..<cols {
                    let px = (org.0 + Double(c) * p) * pxPerPt, py = (org.1 + Double(r) * p) * pxPerPt
                    if px >= x0 && px <= x1 && py >= y0 && py <= y1 { out.append(Cell(c, r)) }
                }
            }
            return out
        }

        // obstacle blobs by kind
        var blobs: [String: [[String: Any]]] = [:]
        var blobOrder: [String] = []
        for (i, any) in ((o["obstacles"] as? [Any]) ?? []).enumerated() {
            guard let b = any as? [String: Any] else { rep.warnings.append("obstacles[\(i)] is not an object → skipped"); continue }
            classify(b, used: usedObstacle, research: researchObstacle, path: "obstacles[].")
            let kind = (b["kind"] as? String) ?? "unknown"
            if blobs[kind] == nil { blobOrder.append(kind) }
            blobs[kind, default: []].append(b)
        }
        var obstacles: [ObstacleSpec] = []

        // tapes
        for (i, b) in (blobs["tape_pink"] ?? []).enumerated() {
            let cs = cells(b["cells"])
            let band = Set(cs)
            let members = arrows.filter { $0.layer == 1 && !band.isDisjoint(with: $0.cells) }.map(\.id).sorted()
            if members.count < 2 { rep.warnings.append("tape t\(i) binds \(members.count) arrow(s)") }
            obstacles.append(ObstacleSpec(id: ObstacleID("t\(i)"), kind: .tape, cells: cs, arrows: members))
        }
        let tapedIDs = Set(((o["taped_arrow_ids"] as? [Any]) ?? []).compactMap(int).map(ArrowID.init))
        let tapeMembers = Set(obstacles.filter { $0.kind == .tape }.flatMap(\.arrows))
        if tapedIDs != tapeMembers {
            rep.warnings.append("taped_arrow_ids \(tapedIDs.map(\.raw).sorted()) ≠ tape members \(tapeMembers.map(\.raw).sorted())")
        }

        // doors: union → rectangles (heuristic), ordered leftmost, then lowest
        let doorBlobs = blobs["door"] ?? []
        let doorCellsJSON = cells(o["door_cells"])
        var doorRects: [[Cell]] = []
        if !doorCellsJSON.isEmpty {
            doorRects = splitIntoRectangles(Set(doorCellsJSON))
            rep.warnings.append("doors: \(doorRects.count) rectangle(s) split from door_cells (\(doorCellsJSON.count) cells) by column bands — split and order are a reconstruction (levels.json decides)")
        } else if !doorBlobs.isEmpty {
            var rects: [Set<Cell>] = []
            for b in doorBlobs {
                var cs = Set(bboxCells(b))
                if cs.isEmpty { cs = Set(cells(b["cells"])) }
                if cs.isEmpty { continue }
                if let k = rects.firstIndex(where: { !$0.isDisjoint(with: cs) }) {
                    rects[k].formUnion(cs)
                    rep.warnings.append("doors: two door blobs overlap → merged")
                } else { rects.append(cs) }
            }
            doorRects = rects.map { $0.sorted { ($0.r, $0.c) < ($1.r, $1.c) } }
            rep.warnings.append("doors: \(doorRects.count) rectangle(s) from blob bounding boxes — cells and order are a reconstruction (levels.json decides)")
        }
        doorRects.sort { a, b in
            let (ac, ar) = (a.map(\.c).min() ?? 0, a.map(\.r).max() ?? 0)
            let (bc, br) = (b.map(\.c).min() ?? 0, b.map(\.r).max() ?? 0)
            return ac != bc ? ac < bc : ar > br
        }
        for (i, rect) in doorRects.enumerated() {
            let covered = Set(rect).intersection(owner.keys)
            if !covered.isEmpty { rep.warnings.append("door d\(i) covers \(covered.count) cell(s) of visible arrows") }
            obstacles.append(ObstacleSpec(id: ObstacleID("d\(i)"), kind: .door, cells: rect, order: i))
        }

        // keys: the arrow they hang on
        for (i, b) in (blobs["key"] ?? []).enumerated() {
            let cs = cells(b["cells"])
            var votes: [ArrowID: Int] = [:]
            for c in cs { if let a = owner[c] { votes[a, default: 0] += 1 } }
            let rider = votes.max { $0.value != $1.value ? $0.value < $1.value : $0.key > $1.key }?.key
            if rider == nil { rep.warnings.append("key k\(i) hangs on no arrow") }
            obstacles.append(ObstacleSpec(id: ObstacleID("k\(i)"), kind: .key, cells: cs, arrows: rider.map { [$0] } ?? []))
        }
        if !(blobs["key"] ?? []).isEmpty && doorRects.isEmpty { rep.warnings.append("keys without doors") }

        // pipes: pipes[] entries are authoritative; blobs they do not cover are kept without mouths
        var pipeCells = Set<Cell>()
        var pipeCount = 0
        let pipeBlobs = blobs["pipe"] ?? []
        for (i, any) in ((o["pipes"] as? [Any]) ?? []).enumerated() {
            guard let p = any as? [String: Any] else { rep.warnings.append("pipes[\(i)] is not an object → skipped"); continue }
            classify(p, used: usedPipe, research: [], path: "pipes[].")
            let cs = cells(p["cells"])
            var ends: [PipeEnd] = []
            for e in (p["ends"] as? [Any]) ?? [] {
                guard let ed = e as? [String: Any] else { continue }
                classify(ed, used: usedEnd, research: [], path: "pipes[].ends[].")
                if let c = cell(ed["cell"]), let d = (ed["out"] as? String).flatMap(Dir.init(rawValue:)) { ends.append(PipeEnd(cell: c, out: d)) }
            }
            var counter = int(p["counter"])
            if counter == nil {
                counter = pipeBlobs.first { !Set(cells($0["cells"])).isDisjoint(with: cs) }.flatMap { int($0["counter"]) }
            }
            let id = ObstacleID("p\(pipeCount)")
            if ends.count != 2 { rep.warnings.append("pipe \(id) has \(ends.count) mouth(s)") }
            if counter == nil { rep.warnings.append("pipe \(id): counter missing (not in the phone JSON; levels.md / levels.json)") }
            obstacles.append(ObstacleSpec(id: id, kind: .pipe, cells: cs, ends: ends, counter: counter))
            pipeCells.formUnion(cs)
            pipeCount += 1
        }
        for b in pipeBlobs {
            let cs = cells(b["cells"])
            guard !cs.isEmpty, Set(cs).isDisjoint(with: pipeCells) else { continue }
            let id = ObstacleID("p\(pipeCount)")
            rep.warnings.append("pipe \(id): a blob with no pipes[] entry → no mouths, \(cs.count) cell(s) (reader gap)")
            obstacles.append(ObstacleSpec(id: id, kind: .pipe, cells: cs, counter: int(b["counter"])))
            pipeCells.formUnion(cs)
            pipeCount += 1
        }

        // boxes and curtains: the blocker area around each blob; the counter from the blob (video) or missing (phone)
        let blockerComponents = components(Set(cells(o["blocker_cells"])))
        var counterCount: [ObstacleKind: Int] = [:]
        for (kindKey, kind, prefix) in [("box", ObstacleKind.box, "b"), ("curtain", ObstacleKind.curtain, "c")] {
            for b in blobs[kindKey] ?? [] {
                let blobCells = Set(cells(b["cells"]))
                var area = Set<Cell>()
                for comp in blockerComponents where !comp.isDisjoint(with: blobCells) { area.formUnion(comp) }
                if area.isEmpty { area = Set(bboxCells(b)) }
                if area.isEmpty { area = blobCells }
                let n = counterCount[kind, default: 0]
                counterCount[kind] = n + 1
                let id = ObstacleID("\(prefix)\(n)")
                let counter = int(b["counter"])
                if counter == nil { rep.warnings.append("\(kind.rawValue) \(id): counter missing (not in the phone JSON; levels.md / levels.json)") }
                if blockerComponents.isEmpty { rep.warnings.append("\(kind.rawValue) \(id): \(area.count) cell(s) from its bounding box (reconstruction)") }
                obstacles.append(ObstacleSpec(id: id, kind: kind, cells: area.sorted { ($0.r, $0.c) < ($1.r, $1.c) }, counter: counter))
            }
        }

        // elevators (video): elevators[] is authoritative; the blob list only confirms
        let elevatorList = (o["elevators"] as? [Any]) ?? []
        for (i, any) in elevatorList.enumerated() {
            guard let e = any as? [String: Any] else { rep.warnings.append("elevators[\(i)] is not an object → skipped"); continue }
            classify(e, used: usedElevator, research: researchElevator, path: "elevators[].")
            let id = ObstacleID("e\(i)")
            let platform = ((e["arrow_ids"] as? [Any]) ?? []).compactMap(int).map(ArrowID.init).sorted()
            let hidden = ((e["hidden_arrow_ids"] as? [Any]) ?? []).compactMap(int).map(ArrowID.init).sorted()
            obstacles.append(ObstacleSpec(id: id, kind: .elevator, cells: cells(e["cells"]), arrows: platform, reveals: hidden))
            for k in arrows.indices where hidden.contains(arrows[k].id) || underElevator[arrows[k].id] == i && arrows[k].layer > 1 {
                arrows[k].hiddenBy = id
            }
        }
        let elevatorBlobs = (blobs["elevator"] ?? []).count
        if elevatorBlobs != elevatorList.count {
            rep.warnings.append("\(elevatorBlobs) elevator blob(s) vs \(elevatorList.count) elevators[] entr(ies)")
        }
        for a in arrows where a.layer > 1 && a.hiddenBy == nil {
            rep.warnings.append("arrow \(a.id.raw) is on layer \(a.layer) under no elevator")
        }

        // dropped blobs
        let mappedKinds: Set<String> = ["tape_pink", "door", "key", "pipe", "box", "curtain", "elevator"]
        for k in blobOrder where !mappedKinds.contains(k) {
            let n = blobs[k]?.count ?? 0
            rep.droppedObstacles.append("\(k) ×\(n)")
            if k != "box_part" { rep.warnings.append("\(n) obstacle blob(s) of unknown kind \"\(k)\" dropped") }
        }

        let spec = LevelSpec(level: level, source: source, capture: capture, cols: cols, rows: rows, mask: mask,
                             timerSeconds: timer, hearts: hearts, tag: tag, arrows: arrows, obstacles: obstacles)
        for p in spec.structuralProblems() { rep.warnings.append("structure: \(p)") }
        rep.unknownKeys = unknown.sorted()
        rep.droppedKeys = dropped.sorted()
        return ImportedLevel(level: spec, report: rep)
    }

    // MARK: reveal merge (phone Lnnn-openK.json)

    /// Adds the arrows that appear in the later states (each an Lnnn-openK.json, "cells in the START json frame") as
    /// arrows hidden by the door (or box / curtain) whose cells hold most of them; that obstacle's `reveals` lists them.
    /// A state that shows no new arrow adds nothing (L56/L57: the boxes hid none).
    static func mergeReveals(base: ImportedLevel, states: [ImportedLevel]) -> ImportedLevel {
        var level = base.level
        var rep = base.report
        var knownSets: [Set<Cell>] = level.arrows.map { Set($0.cells) }
        var nextID = (level.arrows.map(\.id.raw).max() ?? -1) + 1
        let hiders: Set<ObstacleKind> = [.door, .box, .curtain]
        let doorIdx = level.obstacles.indices.filter { hiders.contains(level.obstacles[$0].kind) }
        var added = 0
        for (k, st) in states.enumerated() {
            for a in st.level.arrows {
                let s = Set(a.cells)
                if knownSets.contains(s) { continue }
                if knownSets.contains(where: { !$0.isDisjoint(with: s) }) {
                    rep.warnings.append("open\(k + 1): arrow \(a.id.raw) overlaps a known arrow but differs → skipped (re-read)")
                    continue
                }
                var best: Int?, bestN = 0
                for d in doorIdx {
                    let n = s.intersection(level.obstacles[d].cells).count
                    if n > bestN { bestN = n; best = d }
                }
                let id = ArrowID(nextID)
                nextID += 1
                var hidden = a
                hidden.id = id
                hidden.layer = 1
                if let d = best {
                    hidden.hiddenBy = level.obstacles[d].id
                    level.obstacles[d].reveals.append(id)
                    if bestN < s.count {
                        rep.warnings.append("open\(k + 1): revealed arrow \(id.raw) lies only \(bestN)/\(s.count) inside \(level.obstacles[d].kind.rawValue) \(level.obstacles[d].id)")
                    }
                } else {
                    rep.warnings.append("open\(k + 1): arrow \(id.raw) appears outside every door/box (kept visible)")
                }
                level.arrows.append(hidden)
                knownSets.append(s)
                added += 1
            }
        }
        rep.warnings.append("reveals merged: \(states.count) state(s), \(added) hidden arrow(s) added")
        for p in level.structuralProblems() where !rep.warnings.contains("structure: \(p)") { rep.warnings.append("structure (merged): \(p)") }
        return ImportedLevel(level: level, report: rep)
    }

    // MARK: area helpers

    /// 4-connected components.
    static func components(_ area: Set<Cell>) -> [Set<Cell>] {
        var left = area
        var out: [Set<Cell>] = []
        while let seed = left.min(by: { ($0.r, $0.c) < ($1.r, $1.c) }) {
            var comp: Set<Cell> = [seed]
            var stack = [seed]
            left.remove(seed)
            while let c = stack.popLast() {
                for d in Dir.allCases {
                    let n = c + d
                    if left.remove(n) != nil { comp.insert(n); stack.append(n) }
                }
            }
            out.append(comp)
        }
        return out
    }

    /// Splits a union of door cells into rectangles: per 4-connected component, consecutive columns with identical
    /// vertical runs form one band; each run of a band is one rectangle. Exact for a staircase (L33) and for a ring of
    /// four doors (L34); two doors stacked with equal widths come out as one (the report says it is a reconstruction).
    static func splitIntoRectangles(_ area: Set<Cell>) -> [[Cell]] {
        var rects: [[Cell]] = []
        for comp in components(area) {
            let cs = comp.map(\.c), rs = comp.map(\.r)
            guard let c0 = cs.min(), let c1 = cs.max(), let r0 = rs.min(), let r1 = rs.max() else { continue }
            func runs(_ c: Int) -> [ClosedRange<Int>] {
                var out: [ClosedRange<Int>] = []
                var start: Int?
                for r in r0...(r1 + 1) {
                    let inside = r <= r1 && comp.contains(Cell(c, r))
                    if inside, start == nil { start = r }
                    if !inside, let s = start { out.append(s...(r - 1)); start = nil }
                }
                return out
            }
            var bandStart = c0
            var bandRuns = runs(c0)
            for c in (c0 + 1)...(c1 + 1) {
                let next = c <= c1 ? runs(c) : []
                if c > c1 || next != bandRuns {
                    for run in bandRuns {
                        var rect: [Cell] = []
                        for r in run { for cc in bandStart..<c { rect.append(Cell(cc, r)) } }
                        rects.append(rect)
                    }
                    bandStart = c
                    bandRuns = next
                }
            }
        }
        return rects
    }

    // MARK: JSONSerialization value helpers

    static func int(_ v: Any?) -> Int? {
        guard let n = v as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID() else { return nil }
        let d = n.doubleValue
        guard d.rounded() == d, abs(d) < 9.0e15 else { return nil }
        return n.intValue
    }

    static func double(_ v: Any?) -> Double? {
        guard let n = v as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID() else { return nil }
        return n.doubleValue
    }

    static func cell(_ v: Any?) -> Cell? {
        guard let a = v as? [Any], a.count == 2, let c = int(a[0]), let r = int(a[1]) else { return nil }
        return Cell(c, r)
    }

    static func cells(_ v: Any?) -> [Cell] { ((v as? [Any]) ?? []).compactMap(cell) }
}
#endif
