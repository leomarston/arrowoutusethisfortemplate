import XCTest
import PathCore

/// C1 (SPEC-architecture §4.3, §4.17): every research level (phone + video) decodes with an unknown-key report and 0
/// errors; the obstacle mapping on the levels whose rules C2 tests; the reveal merge; the bundle v1 round trip; sessions,
/// unlocks, tutorials and the LevelLibrary.
final class LevelJSONTests: XCTestCase {

    // MARK: the research corpora

    /// Keyed by the path under research/ (the same file name exists in two video folders); the corpus is the frozen copy in
    /// Tests/Fixtures/research (C1Fixtures.researchRoot, MANIFEST.txt).
    private func importAll(_ files: [URL]) -> (ok: [String: ImportedLevel], errors: [String]) {
        var ok: [String: ImportedLevel] = [:], errors: [String] = []
        let root = C1Fixtures.researchRoot.path + "/"
        for url in files {
            let key = url.path.hasPrefix(root) ? String(url.path.dropFirst(root.count)) : url.lastPathComponent
            do { ok[key] = try LevelJSON.load(Data(contentsOf: url)) } catch { errors.append("\(key): \(error)") }
        }
        return (ok, errors)
    }

    private func reportText(_ title: String, _ r: [String: ImportedLevel], _ errors: [String]) -> String {
        var unknown = Set<String>(), dropped = Set<String>()
        var lines = ["# \(title): \(r.count) decoded, \(errors.count) errors"]
        lines += errors.map { "ERROR \($0)" }
        for (name, imp) in r.sorted(by: { $0.key < $1.key }) {
            unknown.formUnion(imp.report.unknownKeys)
            dropped.formUnion(imp.report.droppedKeys)
            let l = imp.level
            let kinds = Dictionary(grouping: l.obstacles, by: \.kind).map { "\($0.key.rawValue)×\($0.value.count)" }.sorted()
            lines.append("\(name): L\(l.level) \(l.source.rawValue) \(l.cols)×\(l.rows) timer \(l.timerSeconds) tag \(l.tag.rawValue) arrows \(l.arrows.count) [\(kinds.joined(separator: " "))]")
            if !imp.report.droppedObstacles.isEmpty { lines.append("    dropped blobs: \(imp.report.droppedObstacles.joined(separator: ", "))") }
            for w in imp.report.warnings { lines.append("    warning: \(w)") }
            if !imp.report.revealFiles.isEmpty { lines.append("    reveals: \(imp.report.revealFiles.joined(separator: ", "))") }
        }
        lines.insert("UNKNOWN keys (never applied): " + (unknown.isEmpty ? "none" : unknown.sorted().joined(separator: ", ")), at: 1)
        lines.insert("research-only keys dropped: " + dropped.sorted().joined(separator: ", "), at: 2)
        return lines.joined(separator: "\n") + "\n"
    }

    func testEveryResearchLevelsFileDecodes() throws {
        let files = try C1Fixtures.researchLevelFiles()
        XCTAssertGreaterThanOrEqual(files.count, 40, "research/levels: 30 recorded levels + their -openK reveal states (+ video-sourced)")
        let (ok, errors) = importAll(files)
        XCTAssertEqual(errors, [], "0 errors")
        XCTAssertEqual(ok.count, files.count)
        XCTAssertEqual(ok.values.filter { $0.report.schema == .phone }.count, 40, "the 40 phone files (30 levels + 10 reveal states)")
        for (name, imp) in ok {
            let recorded = ((try? C1Fixtures.jsonObject(C1Fixtures.research(name)))?["source"] as? String) == "recorded"
            XCTAssertEqual(imp.report.schema, recorded ? .phone : .video, name)
            XCTAssertEqual(imp.level.source, recorded ? .authored : .crafted, name)
            XCTAssertFalse(imp.level.arrows.isEmpty, name)
        }
        // The 30 base levels carry their timers; the reveal snapshots do not (their base does).
        for url in try C1Fixtures.recordedBaseFiles() {
            XCTAssertGreaterThan(ok["levels/\(url.lastPathComponent)"]?.level.timerSeconds ?? 0, 0, url.lastPathComponent)
        }
        C1Fixtures.evidence("import-report-research-levels.txt", reportText("research/levels (phone schema + video-sourced files)", ok, errors))
    }

    func testEveryVideoExtractDecodes() throws {
        let files = try C1Fixtures.videoExtractFiles()
        XCTAssertGreaterThanOrEqual(files.count, 48, "V1-L001…L020 + V2-L011…L038")
        let (ok, errors) = importAll(files)
        XCTAssertEqual(errors, [], "0 errors")
        XCTAssertEqual(ok.count, files.count)
        for (name, imp) in ok {
            XCTAssertEqual(imp.report.schema, .video, name)
            XCTAssertEqual(imp.level.source, .crafted, name)
        }
        C1Fixtures.evidence("import-report-video.txt", reportText("research/video-frames/work/extract (video schema)", ok, errors))
    }

    func testTheReportListsUnknownAndDroppedKeys() throws {
        let json = """
        {"level": 99, "source": "recorded", "shot": "x.png", "cols": 4, "rows": 3, "mask": null, "timer_s": 150, "hearts": 3,
         "tag": "Hard Level", "zoom": "fit", "reader": "bot", "sparkle": 1,
         "arrows": [{"id": 0, "cells": [[0,0],[1,0]], "dir": "right", "colour": "red"}],
         "obstacles": [{"kind": "box_part", "cells": [], "bbox_px": [0,0,1,1], "mean_rgb": [1,2,3]},
                       {"kind": "spring", "cells": [[3,2]], "shape": "coil"}],
         "taped_arrow_ids": [], "pipes": [], "door_cells": []}
        """
        let imp = try LevelJSON.load(Data(json.utf8))
        XCTAssertEqual(imp.report.unknownKeys, ["arrows[].colour", "obstacles[].shape", "sparkle"])
        XCTAssertEqual(imp.report.droppedKeys, ["obstacles[].mean_rgb", "reader", "zoom"])
        XCTAssertEqual(imp.report.droppedObstacles, ["box_part ×1", "spring ×1"])
        XCTAssertTrue(imp.report.warnings.contains { $0.contains("unknown kind \"spring\"") })
        XCTAssertEqual(imp.level.tag, .hard)
        XCTAssertEqual(imp.level.timerSeconds, 150)
        XCTAssertFalse(imp.report.isClean)
        XCTAssertTrue(imp.report.description.contains("UNKNOWN keys: arrows[].colour"))
        // A structural problem is reported, never thrown.
        let bad = try LevelJSON.load(Data("""
        {"level": 1, "source": "recorded", "cols": 3, "rows": 3, "timer_s": 180,
         "arrows": [{"id": 0, "cells": [[0,0],[2,0]], "dir": "right"}, {"id": 1, "cells": [[0,2],[1,2]], "dir": "left"}],
         "obstacles": []}
        """.utf8))
        XCTAssertTrue(bad.report.warnings.contains { $0.contains("not orthogonal") })
        XCTAssertTrue(bad.report.warnings.contains { $0.contains("dir left but") })
        XCTAssertThrowsError(try LevelJSON.load(Data("[1,2]".utf8)))
        XCTAssertThrowsError(try LevelJSON.load(Data("{\"source\": \"recorded\", \"cols\": 2}".utf8)))
    }

    // MARK: obstacle mapping on the levels C2's rules tests use

    private func phone(_ name: String, reveals: [String] = []) throws -> ImportedLevel {
        try LevelJSON.load(C1Fixtures.data(C1Fixtures.research("levels/\(name)")),
                           reveals: reveals.map { try C1Fixtures.data(C1Fixtures.research("levels/\($0)")) })
    }

    private func video(_ name: String) throws -> ImportedLevel {
        try LevelJSON.load(C1Fixtures.data(C1Fixtures.research("video-frames/work/extract/\(name)")))
    }

    func testL32TapesBindTheirFourArrows() throws {
        let imp = try phone("L032.json")
        let l = imp.level
        XCTAssertEqual(l.level, 32)
        XCTAssertEqual([l.cols, l.rows, l.timerSeconds, l.hearts], [20, 20, 180, 3])
        XCTAssertEqual(l.tag, .normal)
        XCTAssertEqual(l.arrows.count, 53)
        XCTAssertEqual(l.arrowCells, 399)
        XCTAssertEqual(l.capture, "research/shots/003-L32-start.png")
        let tapes = l.obstacles.filter { $0.kind == .tape }
        XCTAssertEqual(tapes.map(\.id), ["t0", "t1", "t2", "t3"])
        XCTAssertTrue(tapes.allSatisfy { $0.arrows.count == 4 }, "each tape binds 4 parallel arrows (levels L32)")
        XCTAssertEqual(Set(tapes.flatMap(\.arrows)).map(\.raw).sorted(), [0, 1, 2, 3, 7, 12, 13, 15, 42, 44, 45, 46, 47, 48, 50, 52])
        XCTAssertEqual(tapes[0].arrows, [ArrowID(0), ArrowID(1), ArrowID(2), ArrowID(3)])
        XCTAssertEqual(l.structuralProblems(), [])
        XCTAssertEqual(imp.report.warnings, [], "L32 maps exactly")
    }

    func testL35PipeMouthsAndL50Box() throws {
        let l35 = try phone("L035.json").level
        let pipes = l35.obstacles.filter { $0.kind == .pipe }
        XCTAssertEqual(pipes.count, 1)
        XCTAssertEqual(pipes[0].cells.count, 15)
        XCTAssertEqual(pipes[0].cells.first, Cell(6, 0))
        XCTAssertEqual(pipes[0].cells.last, Cell(11, 9))
        XCTAssertEqual(pipes[0].ends, [PipeEnd(cell: Cell(6, 0), out: .left), PipeEnd(cell: Cell(11, 9), out: .down)])
        XCTAssertNil(pipes[0].counter, "the phone JSON carries no counters (levels.md: 2)")

        let imp50 = try phone("L050.json")
        let boxes = imp50.level.obstacles.filter { $0.kind == .box }
        XCTAssertEqual(boxes.count, 1)
        XCTAssertEqual(Set(boxes[0].cells), Set((0..<10).flatMap { c in (15...17).map { Cell(c, $0) } }),
                       "the L50 box spans the full 10 × 3 block of its bounding box")
        XCTAssertTrue(imp50.report.droppedObstacles.contains("box_part ×6"))
        XCTAssertTrue(imp50.report.warnings.contains { $0.contains("counter missing") })
    }

    func testL33DoorStaircaseAndKeys() throws {
        let imp = try phone("L033.json")
        let doors = imp.level.obstacles.filter { $0.kind == .door }
        // levels.md L33: 5 doors in a staircase, heights growing left → right, opened strictly left → right.
        XCTAssertEqual(doors.count, 5)
        XCTAssertEqual(doors.map(\.cells.count), [16, 32, 48, 64, 80])
        XCTAssertEqual(doors.map(\.order), [0, 1, 2, 3, 4])
        XCTAssertEqual(doors.map { $0.cells.map(\.c).min()! }, [0, 4, 8, 12, 16])
        let keys = imp.level.obstacles.filter { $0.kind == .key }
        XCTAssertEqual(keys.count, 2)
        for k in keys {
            XCTAssertEqual(k.arrows.count, 1, "a key hangs on one arrow")
            let arrow = imp.level.arrow(k.arrows[0])!
            XCTAssertTrue(Set(k.cells).isSubset(of: Set(arrow.cells)), "the key's cells lie on its arrow")
        }
        XCTAssertTrue(imp.report.warnings.contains { $0.contains("reconstruction") }, "the door split is reported as a guess")
    }

    func testRevealMergeAddsHiddenArrowsUnderDoors() throws {
        let base = try phone("L047.json")
        XCTAssertEqual(base.report.revealFiles, ["L047-open1.json", "L047-open2.json"])
        let merged = try phone("L047.json", reveals: base.report.revealFiles)
        let l = merged.level
        let hidden = l.arrows.filter { $0.hiddenBy != nil }
        XCTAssertGreaterThan(hidden.count, 0)
        XCTAssertEqual(Set(l.arrows.map(\.id)).count, l.arrows.count, "ids stay unique")
        XCTAssertEqual(l.arrows.count, base.level.arrows.count + hidden.count)
        for a in hidden {
            let door = l.obstacle(a.hiddenBy!)!
            XCTAssertEqual(door.kind, .door)
            XCTAssertTrue(door.reveals.contains(a.id))
            XCTAssertGreaterThan(Set(a.cells).intersection(door.cells).count, 0)
        }
        XCTAssertEqual(l.startArrows.count, base.level.arrows.count)
        // Every base level with reveal files merges without an error.
        var lines: [String] = []
        for url in try C1Fixtures.recordedBaseFiles() {
            let b = try LevelJSON.load(Data(contentsOf: url))
            guard !b.report.revealFiles.isEmpty else { continue }
            let m = try phone(url.lastPathComponent, reveals: b.report.revealFiles)
            let n = m.level.arrows.filter { $0.hiddenBy != nil }.count
            lines.append("\(url.lastPathComponent) + \(b.report.revealFiles.joined(separator: ", ")): \(b.level.arrows.count) visible + \(n) hidden")
            for w in m.report.warnings where w.hasPrefix("open") || w.hasPrefix("structure (merged)") { lines.append("    \(w)") }
            // Doors hide arrows (L47/L49/L53/L54/L58); the L56/L57 box-break states reveal none (levels.md: no arrows sat
            // under the boxes, as on L50/L51).
            let hasDoor = b.level.obstacles.contains { $0.kind == .door }
            if hasDoor { XCTAssertGreaterThan(n, 0, url.lastPathComponent) } else { XCTAssertEqual(n, 0, url.lastPathComponent) }
        }
        C1Fixtures.evidence("reveal-merge.txt", lines.joined(separator: "\n") + "\n")
    }

    func testVideoCountersPipesAndElevators() throws {
        let v11 = try video("V1-L011.json").level
        XCTAssertEqual(v11.source, .crafted)
        let curtains = v11.obstacles.filter { $0.kind == .curtain }
        XCTAssertEqual(curtains.map(\.counter), [8, 13], "VERIFIED tutorials §6: 8 → 7 → …, 13 → 12 …")
        XCTAssertEqual(curtains.map(\.cells.count), [9, 9], "3 × 3 blocks from blocker_cells")

        let v21 = try video("V2-L021.json").level
        let pipe = v21.obstacles.first { $0.kind == .pipe }!
        XCTAssertEqual(pipe.counter, 2)
        XCTAssertEqual(pipe.ends.count, 2)

        let imp31 = try video("V2-L031.json")
        let v31 = imp31.level
        let elevators = v31.obstacles.filter { $0.kind == .elevator }
        XCTAssertEqual(elevators.count, 1)
        XCTAssertEqual(elevators[0].arrows.map(\.raw), [9, 10, 12, 15, 17, 18, 19, 21, 24])
        let layer2 = v31.arrows.filter { $0.layer == 2 }
        XCTAssertFalse(layer2.isEmpty)
        XCTAssertTrue(layer2.allSatisfy { $0.hiddenBy == "e0" })
        XCTAssertEqual(Set(elevators[0].reveals), Set(layer2.map(\.id)))
        XCTAssertFalse(imp31.report.droppedKeys.isEmpty)
    }

    // MARK: bundle v1

    func testBundleRoundTripOverTheWholeCorpus() throws {
        var n = 0
        for url in try C1Fixtures.researchLevelFiles() + C1Fixtures.videoExtractFiles() {
            let level = try LevelJSON.load(Data(contentsOf: url)).level
            let bytes = try LevelJSON.encodeBundle(level)
            let back = try LevelJSON.decodeBundle(bytes)
            XCTAssertEqual(back, level, url.lastPathComponent)
            XCTAssertEqual(try LevelJSON.encodeBundle(back), bytes, "\(url.lastPathComponent): canonical bytes are stable")
            XCTAssertEqual(try LevelJSON.schema(of: bytes), .bundle)
            XCTAssertEqual(try LevelJSON.inspectBundle(bytes).unknownKeys, [], url.lastPathComponent)
            let viaLoad = try LevelJSON.load(bytes)
            XCTAssertEqual(viaLoad.level, level)
            n += 1
        }
        XCTAssertGreaterThanOrEqual(n, 88)
        // The merged levels (hidden arrows, reveals) round-trip too.
        let merged = try phone("L053.json", reveals: ["L053-open1.json", "L053-open2.json"]).level
        XCTAssertEqual(try LevelJSON.decodeBundle(LevelJSON.encodeBundle(merged)), merged)
    }

    func testBundleSchemaDetails() throws {
        let json = """
        {"schema": 1, "level": 7, "source": "video", "capture": "V1 76.4", "cols": 6, "rows": 4, "timer_s": 180,
         "tag": "Super Hard", "_note": "comment",
         "arrows": [{"id": 0, "cells": [[0,0],[1,0]], "dir": "right"},
                    {"id": 1, "cells": [[2,2],[2,3]], "dir": "down", "layer": 2, "hidden_by": "e0"}],
         "obstacles": [{"id": "t0", "kind": "tape", "cells": [[0,0]], "arrows": [0], "extra": true},
                       {"id": "p0", "kind": "pipe", "cells": [[5,0],[5,1]], "ends": [{"cell": [5,0], "out": "up"}, {"cell": [5,1], "out": "down"}],
                        "counter": 3, "counter_at": [5.5, 0]}],
         "unlock": "linked", "seed": 18446744073709551615,
         "metrics": {"rounds": 2, "free_at_start": 1, "arrows": 2, "cells": 4, "mean_length": 2.0}}
        """
        let data = Data(json.utf8)
        let l = try LevelJSON.decodeBundle(data)
        XCTAssertEqual(l.tag, .superHard)
        XCTAssertEqual(l.hearts, 3, "hearts default")
        XCTAssertEqual(l.arrows[1].layer, 2)
        XCTAssertEqual(l.arrows[1].hiddenBy, "e0")
        XCTAssertEqual(l.obstacles[1].counterAt, [5.5, 0])
        XCTAssertEqual(l.unlock, .linked)
        XCTAssertEqual(l.seed, UInt64.max)
        XCTAssertEqual(l.metrics?.freeAtStart, 1)
        XCTAssertNil(l.metrics?.botTimeLeft)
        XCTAssertEqual(try LevelJSON.inspectBundle(data).unknownKeys, ["obstacles[].extra"], "\"_note\" is a comment")
        // Layer 1 and empty lists are omitted on encode; layer 2 is kept.
        let enc = String(decoding: try LevelJSON.encodeBundle(l), as: UTF8.self)
        XCTAssertTrue(enc.hasSuffix("}\n"))
        XCTAssertFalse(enc.contains("\"layer\":1"))
        XCTAssertTrue(enc.contains("\"layer\":2"))
        XCTAssertTrue(enc.contains("\"hidden_by\":\"e0\""))
        XCTAssertFalse(enc.contains("\\/"), "slashes are not escaped")
        XCTAssertTrue(enc.contains("\"tag\":\"superHard\""))
        // A newer schema is refused; a missing required key throws.
        XCTAssertThrowsError(try LevelJSON.decodeBundle(Data(json.replacingOccurrences(of: "\"schema\": 1", with: "\"schema\": 2").utf8)))
        XCTAssertThrowsError(try LevelJSON.decodeBundle(Data("{\"schema\":1,\"level\":1,\"cols\":2,\"rows\":2}".utf8)))
    }

    func testSessionsUnlocksAndTutorials() throws {
        let s = try LevelJSON.decodeSessions(Data("""
        {"schema":1,"sessions":[{"id":"L1-4","levels":[1,2,3,4],"hud_label":"Levels 1-4","panel_label":"Level 1-4",
         "reward":80,"stage_gap_s":0.7,"hearts":"carry"}]}
        """.utf8))
        XCTAssertEqual(s, [SessionPlan(id: "L1-4", levels: [1, 2, 3, 4], hudLabel: "Levels 1-4", panelLabel: "Level 1-4",
                                       reward: 80, stageGap: 0.7, hearts: .carry)])
        XCTAssertEqual(try LevelJSON.decodeSessions(LevelJSON.encodeSessions(s)), s)
        let bare = try LevelJSON.decodeSessions(Data("[{\"id\":\"x\",\"levels\":[9]}]".utf8))
        XCTAssertEqual(bare[0].hearts, .carry)
        XCTAssertNil(bare[0].reward)
        XCTAssertThrowsError(try LevelJSON.decodeSessions(Data("[{\"id\":\"x\",\"levels\":[]}]".utf8)))
        XCTAssertThrowsError(try LevelJSON.decodeSessions(Data("{\"schema\":2,\"sessions\":[]}".utf8)))

        let u = try FeatureUnlock.decodeList(Data("""
        [{"feature":"linked","level":7,"title":"Linked Arrows!","card":"LINKED ARROWS move together!",
          "caps":"LINKED ARROWS","icon":"unlockIconLinked"},
         {"feature":"pipe","level":35,"title":"Pipe!","card":"Pass arrows through the PIPE to break it!"}]
        """.utf8))
        XCTAssertEqual(u.map(\.feature), [.linked, .pipe])
        XCTAssertEqual(u[0].caps, "LINKED ARROWS")
        XCTAssertNil(u[1].icon)
        XCTAssertEqual(try FeatureUnlock.decodeList(Data("{\"schema\":1,\"unlocks\":[]}".utf8)), [])
        XCTAssertEqual(try JSONDecoder().decode(FeatureUnlock.self, from: JSONEncoder().encode(u[0])), u[0])
        XCTAssertThrowsError(try FeatureUnlock.decodeList(Data("[{\"feature\":\"pipe\",\"level\":35}]".utf8)), "title/card required")

        let t = try TutorialScript.decodeList(Data("""
        {"schema":1,"tutorials":[{"id":"tapToMove","level":1,"stage":0,"trigger":"stageReady","caption":"Tap to move!",
          "hand":{"arrow":1,"at":[1.0,2.38]},"dismiss":"anyTap","holdTimer":false}, {"id":"x","level":5}]}
        """.utf8))
        XCTAssertEqual(t[0].hand, TutorialHand(arrow: ArrowID(1), at: [1.0, 2.38]))
        XCTAssertEqual(t[0].caption, "Tap to move!")
        XCTAssertFalse(t[0].holdTimer)
        XCTAssertEqual(t[1].trigger, .stageReady)
        XCTAssertEqual(t[1].dismiss, .anyTap)
        XCTAssertEqual(t[1].stage, 0)
        XCTAssertNil(t[1].allowedArrows)
        XCTAssertEqual(try JSONDecoder().decode(TutorialScript.self, from: JSONEncoder().encode(t[0])), t[0])
        XCTAssertEqual(TutorialTrigger(rawValue: "someNewTrigger").rawValue, "someNewTrigger", "open set")
    }

    // MARK: LevelLibrary

    func testLevelLibraryLoadsLazily() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("c1-library-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        func level(_ n: Int) -> LevelSpec {
            LevelSpec(level: n, source: .designed, cols: 4, rows: 4, timerSeconds: 180,
                      arrows: [ArrowSpec(id: ArrowID(0), cells: [Cell(0, 0), Cell(1, 0)], dir: .right)])
        }
        for n in [1, 2, 3, 4, 6] {
            try LevelJSON.encodeBundle(level(n)).write(to: dir.appendingPathComponent(LevelLibrary.fileName(level: n)))
        }
        // A file whose name and content disagree.
        try LevelJSON.encodeBundle(level(3)).write(to: dir.appendingPathComponent("level_0009.json"))
        try LevelJSON.encodeSessions([SessionPlan(id: "L1-4", levels: [1, 2, 3, 4], reward: 80, stageGap: 0.7)])
            .write(to: dir.appendingPathComponent("sessions.json"))
        try Data("[{\"feature\":\"linked\",\"level\":4,\"title\":\"Linked Arrows!\",\"card\":\"c\"}]".utf8)
            .write(to: dir.appendingPathComponent("unlocks.json"))
        try Data("[{\"id\":\"tapToMove\",\"level\":1,\"caption\":\"Tap to move!\"}]".utf8)
            .write(to: dir.appendingPathComponent("tutorials.json"))
        try Data("{\"salt\": 1}".utf8).write(to: dir.appendingPathComponent("curve.json"))
        try Data("ignored".utf8).write(to: dir.appendingPathComponent("README.txt"))

        let lib = try LevelLibrary.load(folder: dir)
        XCTAssertEqual(lib.authoredCount, 4, "level 5 is missing: the authored run ends at 4")
        XCTAssertTrue(lib.problems.contains { $0.contains("levels missing below 9: 5, 7, 8") })
        XCTAssertEqual(lib.files.count, 6)
        XCTAssertEqual(lib.session(containing: 3).id, "L1-4")
        XCTAssertEqual(lib.session(containing: 6), SessionPlan(id: "L6", levels: [6]))
        XCTAssertEqual(lib.nextLevel(after: lib.session(containing: 2)), 5)
        XCTAssertEqual(lib.authored(2), level(2))
        XCTAssertEqual(lib.authored(2), level(2), "cached")
        XCTAssertNil(lib.authored(5))
        XCTAssertNil(lib.authored(9))
        XCTAssertThrowsError(try lib.loadAuthored(9)) { XCTAssertTrue(String(describing: $0).contains("holds level 3")) }
        XCTAssertEqual(lib.unlock(at: 4)?.feature, .linked)
        XCTAssertNil(lib.unlock(at: 3))
        XCTAssertEqual(lib.tutorials(level: 1).map(\.id), ["tapToMove"])
        XCTAssertEqual(lib.tutorials(level: 1, stage: 1), [])
        XCTAssertEqual(lib.curveJSON, Data("{\"salt\": 1}".utf8))
        XCTAssertEqual(LevelLibrary.levelNumber(fileName: "level_0061.json"), 61)
        XCTAssertEqual(LevelLibrary.levelNumber(fileName: "level_61.json"), 61)
        XCTAssertNil(LevelLibrary.levelNumber(fileName: "level_x1.json"))
        XCTAssertNil(LevelLibrary.levelNumber(fileName: "sessions.json"))
        XCTAssertEqual(LevelLibrary.fileName(level: 7), "level_0007.json")

        // Concurrent first use decodes safely.
        DispatchQueue.concurrentPerform(iterations: 64) { i in _ = lib.authored(1 + i % 4) }
        XCTAssertEqual(lib.authored(4), level(4))

        // A malformed small file fails the load with its name; a missing folder too.
        try Data("{".utf8).write(to: dir.appendingPathComponent("tutorials.json"))
        XCTAssertThrowsError(try LevelLibrary.load(folder: dir)) { XCTAssertTrue(String(describing: $0).contains("tutorials.json")) }
        XCTAssertThrowsError(try LevelLibrary.load(folder: dir.appendingPathComponent("nope")))

        // In memory; a session that lists a level with no file is a problem.
        let mem = LevelLibrary(levels: [level(1), level(2)], sessions: [SessionPlan(id: "S", levels: [2, 3])])
        XCTAssertEqual(mem.authoredCount, 2)
        XCTAssertEqual(mem.authored(1), level(1))
        XCTAssertTrue(mem.problems.contains { $0.contains("lists level 3") })
    }

    // MARK: structure

    func testStructuralProblemsCatchEveryKind() {
        let l = LevelSpec(level: 1, source: .designed, cols: 5, rows: 5, timerSeconds: 180, arrows: [
            ArrowSpec(id: ArrowID(0), cells: [Cell(0, 0)], dir: .right),                                   // < 2 cells
            ArrowSpec(id: ArrowID(1), cells: [Cell(1, 1), Cell(3, 1)], dir: .right),                        // jump
            ArrowSpec(id: ArrowID(2), cells: [Cell(0, 3), Cell(1, 3)], dir: .up),                           // dir ≠ last step
            ArrowSpec(id: ArrowID(3), cells: [Cell(4, 4), Cell(5, 4)], dir: .right),                        // outside
            ArrowSpec(id: ArrowID(4), cells: [Cell(1, 1), Cell(1, 2)], dir: .down),                         // shares (1,1)
            ArrowSpec(id: ArrowID(5), cells: [Cell(2, 4), Cell(2, 3), Cell(3, 3), Cell(3, 4), Cell(3, 2)], dir: .up),   // jump
            ArrowSpec(id: ArrowID(4), cells: [Cell(0, 4), Cell(1, 4)], dir: .right),                        // duplicate id
        ])
        let p = l.structuralProblems().joined(separator: "\n")
        XCTAssertTrue(p.contains("arrow 0: 1 cell(s)"))
        XCTAssertTrue(p.contains("arrow 1: step [1,1]→[3,1] is not orthogonal"))
        XCTAssertTrue(p.contains("arrow 2: dir up but the last step goes right"))
        XCTAssertTrue(p.contains("arrow 3: [5,4] outside"))
        XCTAssertTrue(p.contains("arrow 4 shares [1,1] with arrow 1"))
        XCTAssertTrue(p.contains("arrow 4: duplicate id"))
        let crossing = LevelSpec(level: 1, source: .designed, cols: 4, rows: 4, timerSeconds: 180, arrows: [
            ArrowSpec(id: ArrowID(0), cells: [Cell(0, 0), Cell(1, 0), Cell(1, 1), Cell(0, 1), Cell(0, 2), Cell(1, 2), Cell(2, 2), Cell(2, 1)], dir: .up),
        ])
        XCTAssertEqual(crossing.structuralProblems(), [])
        let ownBody = LevelSpec(level: 1, source: .designed, cols: 4, rows: 4, timerSeconds: 180, arrows: [
            ArrowSpec(id: ArrowID(0), cells: [Cell(2, 0), Cell(3, 0), Cell(3, 1), Cell(2, 1), Cell(1, 1), Cell(1, 0)], dir: .up),
            ArrowSpec(id: ArrowID(1), cells: [Cell(0, 3), Cell(0, 2), Cell(1, 2), Cell(2, 2), Cell(2, 3), Cell(1, 3)], dir: .left),
        ])
        XCTAssertEqual(ownBody.structuralProblems(), ["arrow 1: its ray crosses its own body at [0,3]"])
    }
}
