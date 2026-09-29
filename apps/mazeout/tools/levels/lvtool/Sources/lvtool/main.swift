import Foundation
import PathCore

// lvtool (CONTENT, L1): see Package.swift for the command list. Run from apps/mazeout via tools/levels/lv.sh.

let usage = """
usage: lvtool <command> [args]            (paths relative to apps/mazeout)
  bundle <design/levels.json> <out dir> [--publish] [--check] [--manifest F]
                                                                     write / verify App/Resources/Levels (--publish: the
                                                                     shipped form, provenance stripped; PUBLISH B0)
  check <levels dir> [--rules F] [--art DIR] [--report F]           validate + C2 greedy + HeadlessDriver, every level
  freeset <levels dir> [--rules F] [--out F]                         free units of every start state (JSON)
  diff <levels dir> [--research DIR] [--backfill DIR] [--report F]  recorded/video levels vs their research JSON
  selftest <design/levels.json> [--rules F]                          negative controls (every mutation must be caught)
  decodebench <levels dir>                                           LevelLibrary.load + per-level decode cost
  endless [--from 151] [--count 1000] [--jobs 3] [--report F] [--out F.jsonl]   (L2) the served endless levels: solvable,
                                                                     curve-fitted, no repeats, renderable, deterministic
  consistency [--report F]                                           (L2) unlock cards, tutorial, session, tags, timers,
                                                                     strings and art of L1-L150 against the specs
  l2selftest                                                         (L2) negative controls of endless + consistency
"""

// MARK: freeset

/// The free units of every level's start state, and along C2's greedy trajectory the free units at the start of every
/// round (with the units the round removed, in order), for tools/levels/pathlib_rules.py to replay and compare.
func cmdFreeset(_ a: Args) throws -> Int32 {
    guard a.positional.count == 1 else { throw ToolError("usage: lvtool freeset <levels dir> [--rules F] [--out F]") }
    let (rules, _) = try loadRules(a.opt("rules", "App/Resources/Tuning/rules.json"))
    let lib = try LevelLibrary.load(folder: URL(fileURLWithPath: a.positional[0]))
    var out: [String: Any] = [:]
    var states = 0
    for n in lib.files.keys.sorted() {
        let l = try lib.loadAuthored(n)
        let b = BoardState(level: l, rules: rules)
        var rounds: [[String: Any]] = []
        var guardN = 0
        while !b.isCleared && guardN < 10_000 {
            guardN += 1
            let free = b.freeUnits()
            if free.isEmpty {
                let doors = b.targetedDoors
                if doors.isEmpty { break }
                for d in doors { b.ack(.doorBurst(d)) }
                continue
            }
            var removed: [[Int]] = []
            for u in free {
                let r = b.resolve(tap: u[0])
                guard case .exit(let plan) = r else { continue }
                b.commit(r)
                removed.append(plan.unit.map(\.raw))
            }
            for d in b.targetedDoors { b.ack(.doorBurst(d)) }
            rounds.append(["free": free.map { $0.map(\.raw) }, "removed": removed])
            states += 1
            if removed.isEmpty { break }
        }
        out[String(n)] = ["start": BoardState(level: l, rules: rules).freeUnits().map { $0.map(\.raw) },
                          "rounds": rounds, "cleared": b.isCleared]
    }
    let data = try reportJSON(["engine": "PathCore BoardState.freeUnits + C2 greedy trajectory", "levels": out])
    if let o = a.options["out"] { try writeData(data, o) } else { FileHandle.standardOutput.write(data) }
    print("freeset: \(out.count) levels, \(states) round-start states")
    return 0
}

// MARK: decode cost (FEEL: no level-start stall, SPEC.md §5.3)

/// LevelLibrary.load of the whole folder (the boot cost: index + small files), then every level decoded 20 times through
/// the app's path (LevelJSON.decodeBundle): median and worst per level, and the worst level.
func cmdDecodeBench(_ a: Args) throws -> Int32 {
    guard a.positional.count == 1 else { throw ToolError("usage: lvtool decodebench <levels dir>") }
    let url = URL(fileURLWithPath: a.positional[0])
    var loads: [Double] = []
    for _ in 0..<20 {
        let t = DispatchTime.now().uptimeNanoseconds
        _ = try LevelLibrary.load(folder: url)
        loads.append(Double(DispatchTime.now().uptimeNanoseconds - t) / 1e6)
    }
    let lib = try LevelLibrary.load(folder: url)
    var worst: (Int, Double) = (0, 0)
    var medians: [Double] = []
    for n in lib.files.keys.sorted() {
        let data = try Data(contentsOf: lib.files[n]!)
        var ts: [Double] = []
        for _ in 0..<20 {
            let t = DispatchTime.now().uptimeNanoseconds
            _ = try LevelJSON.decodeBundle(data)
            ts.append(Double(DispatchTime.now().uptimeNanoseconds - t) / 1e6)
        }
        ts.sort()
        medians.append(ts[10])
        if ts[10] > worst.1 { worst = (n, ts[10]) }
    }
    loads.sort()
    medians.sort()
    print(String(format: "decodebench (macOS, -O): LevelLibrary.load %.2f ms median (%.2f max); a level decode: median %.3f ms, p95 %.3f ms, worst level L%d %.3f ms",
                 loads[10], loads.last!, medians[medians.count / 2], medians[Int(Double(medians.count) * 0.95)], worst.0, worst.1))
    return 0
}

// MARK: selftest (negative controls)

func cmdSelftest(_ a: Args) throws -> Int32 {
    guard a.positional.count == 1 else { throw ToolError("usage: lvtool selftest <design/levels.json> [--rules F]") }
    let (rules, _) = try loadRules(a.opt("rules", "App/Resources/Tuning/rules.json"))
    let src = try Content.load(a.positional[0])
    let root = FileManager.default.currentDirectoryPath

    struct Mut { let name: String; let apply: (inout [LevelSpec], inout [FeatureUnlock], inout [TutorialScript], inout [SessionPlan]) -> Void }
    // PUBLISH B0 (level re-order, design/level-order.json): every level-numbered target below names a BOARD by its research
    // slot (the number it was read as), found through the board's own provenance (researchSlots); since the re-order it may
    // ship at another level, printed as "[ships at Lk]". L1-L33 and L70 never move.
    let slotOf = try researchSlots(src.raw)
    func idx(_ n: Int) -> Int { (slotOf[n] ?? n) - 1 }
    func at(_ n: Int) -> String { let s = slotOf[n] ?? n; return s == n ? "" : " [ships at L\(s)]" }
    var muts: [Mut] = []
    muts.append(Mut(name: "L13 box counter 28 -> 29 (tight)") { lv, _, _, _ in
        for k in lv[idx(13)].obstacles.indices where lv[idx(13)].obstacles[k].kind == .box && lv[idx(13)].obstacles[k].counter == 28 { lv[idx(13)].obstacles[k].counter = 29 }
    })
    muts.append(Mut(name: "L29 arrow 67 reversed") { lv, _, _, _ in
        if let k = lv[idx(29)].arrows.firstIndex(where: { $0.id == ArrowID(67) }) {
            let cs = Array(lv[idx(29)].arrows[k].cells.reversed())
            lv[idx(29)].arrows[k].cells = cs
            lv[idx(29)].arrows[k].dir = Dir(from: cs[cs.count - 2], to: cs[cs.count - 1]) ?? .up
        }
    })
    muts.append(Mut(name: "L7 unlock card removed") { lv, _, _, _ in lv[idx(7)].unlock = nil })
    muts.append(Mut(name: "L21 pipe counter 0") { lv, _, _, _ in
        for k in lv[idx(21)].obstacles.indices where lv[idx(21)].obstacles[k].kind == .pipe { lv[idx(21)].obstacles[k].counter = 0 }
    })
    muts.append(Mut(name: "L33 door reveals one arrow short") { lv, _, _, _ in
        if let k = lv[idx(33)].obstacles.firstIndex(where: { $0.kind == .door }) { lv[idx(33)].obstacles[k].reveals.removeFirst() }
    })
    muts.append(Mut(name: "L47 hidden key k1 removed (a door can never open)" + at(47)) { lv, _, _, _ in
        lv[idx(47)].obstacles.removeAll { $0.kind == .key && $0.id == ObstacleID("k1") }
    })
    muts.append(Mut(name: "L32 tape tie moved off the cell behind the head") { lv, _, _, _ in
        if let k = lv[idx(32)].obstacles.firstIndex(where: { $0.kind == .tape }) { lv[idx(32)].obstacles[k].cells[0].r += 1 }
    })
    muts.append(Mut(name: "L35 given the video L21 board (a repeated board)" + at(35)) { lv, _, _, _ in
        let twin = lv[idx(21)]
        lv[idx(35)].arrows = twin.arrows; lv[idx(35)].obstacles = twin.obstacles
        lv[idx(35)].cols = twin.cols; lv[idx(35)].rows = twin.rows; lv[idx(35)].metrics = twin.metrics
    })
    // PUBLISH B0: re-targeted from L64 (v552 L64 has no box since the content recast: the mutation changed nothing and only
    // looked CAUGHT through an unrelated baseline finding) to v552 L62's boxes, as design/tools/validator_selftest.py does
    muts.append(Mut(name: "L62 box counter = its arrow count (never breaks)" + at(62)) { lv, _, _, _ in
        let n = lv[idx(62)].arrows.count
        for k in lv[idx(62)].obstacles.indices where lv[idx(62)].obstacles[k].kind == .box { lv[idx(62)].obstacles[k].counter = n }
    })
    muts.append(Mut(name: "L31 elevator platform list one short") { lv, _, _, _ in
        if let k = lv[idx(31)].obstacles.firstIndex(where: { $0.kind == .elevator }) { lv[idx(31)].obstacles[k].arrows.removeFirst() }
    })
    muts.append(Mut(name: "tutorial hand on a missing arrow") { _, _, tu, _ in tu[0].hand = TutorialHand(arrow: ArrowID(999), at: nil) })
    muts.append(Mut(name: "tutorial on the wrong stage (L1 as stage 1)") { _, _, tu, _ in tu[0].stage = 1 })
    muts.append(Mut(name: "unlock card moved to L8") { lv, un, _, _ in
        if let k = un.firstIndex(where: { $0.feature.rawValue == "linked" }) { un[k].level = 8 }
        lv[idx(8)].unlock = lv[idx(7)].unlock; lv[idx(7)].unlock = nil
    })
    muts.append(Mut(name: "L33 an arrow under a door made visible") { lv, _, _, _ in
        if let k = lv[idx(33)].arrows.firstIndex(where: { $0.hiddenBy != nil }) { lv[idx(33)].arrows[k].hiddenBy = nil }
    })
    muts.append(Mut(name: "L50 metrics.rounds off by one" + at(50)) { lv, _, _, _ in lv[idx(50)].metrics?.rounds += 1 })
    muts.append(Mut(name: "L59 timer 2:00 -> 1:00 (the bot cannot keep 20 %)" + at(59)) { lv, _, _, _ in lv[idx(59)].timerSeconds = 60 })
    muts.append(Mut(name: "session L1-4 lists level 151") { _, _, _, se in se[0].levels = [148, 149, 150, 151] })
    // F3-B (2026-09-29): the door rules `check` gained (Validate.swift: obstacles under a door, door stubs) must still refuse
    // what they do not allow. v552 L69 = three pipes under doors, v552 L62 = the key arrow's 4-cell stub over door d0's frame.
    muts.append(Mut(name: "v552 L69 door d0 two columns narrower: pipe p0 half outside it, so not under it" + at(69)) { lv, _, _, _ in
        let i = idx(69)
        guard let k = lv[i].obstacles.firstIndex(where: { $0.id == ObstacleID("d0") }) else { return }
        let c1 = lv[i].obstacles[k].cells.map(\.c).max()!
        lv[i].obstacles[k].cells.removeAll { $0.c >= c1 - 1 }
    })
    muts.append(Mut(name: "v552 L69 a 1-cell box added under door d0 on a cell of pipe p0 (two obstacles under one door on one cell)" + at(69)) { lv, _, _, _ in
        let i = idx(69)
        guard let p = lv[i].obstacles.first(where: { $0.id == ObstacleID("p0") }) else { return }
        lv[i].obstacles.append(ObstacleSpec(id: ObstacleID("b9"), kind: .box, cells: [p.cells[p.cells.count / 2]], counter: 1))
    })
    muts.append(Mut(name: "v552 L69 a 1-cell box added under door d0 on a cell of an arrow d0 hides" + at(69)) { lv, _, _, _ in
        let i = idx(69)
        guard let a = lv[i].arrows.first(where: { $0.hiddenBy == ObstacleID("d0") }) else { return }
        lv[i].obstacles.append(ObstacleSpec(id: ObstacleID("b9"), kind: .box, cells: [a.cells[0]], counter: 1))
    })
    muts.append(Mut(name: "v552 L62 arrow 23 reversed: its ray now runs into the key arrow's stub over door d0" + at(62)) { lv, _, _, _ in
        let i = idx(62)
        guard let k = lv[i].arrows.firstIndex(where: { $0.id == ArrowID(23) }) else { return }
        let cs = Array(lv[i].arrows[k].cells.reversed())
        lv[i].arrows[k].cells = cs
        lv[i].arrows[k].dir = Dir(from: cs[cs.count - 2], to: cs[cs.count - 1]) ?? .right
    })
    muts.append(Mut(name: "v552 L62 a 1-cell box dropped on a cell of the key arrow's stub (a stub onto an occupied cell)" + at(62)) { lv, _, _, _ in
        let i = idx(62)
        let doors = lv[i].obstacles.filter { $0.kind == .door }
        for a in lv[i].arrows {
            guard let d = doors.first(where: { $0.id == a.hiddenBy }) else { continue }
            if let c = a.cells.first(where: { !d.cells.contains($0) }) {
                lv[i].obstacles.append(ObstacleSpec(id: ObstacleID("b9"), kind: .box, cells: [c], counter: 1))
                return
            }
        }
    })

    func findings(_ lv: [LevelSpec], _ un: [FeatureUnlock], _ tu: [TutorialScript], _ se: [SessionPlan]) -> [String] {
        let lib = LevelLibrary(levels: lv, sessions: se, unlocks: un, tutorials: tu)
        var errs: [String] = []
        for l in lv { errs += checkLevel(l, rules: rules, root: root).errors }
        return errs + crossChecks(levels: lv, lib: lib)
    }
    // PUBLISH B0: a mutation is CAUGHT only by a finding the UNMUTATED content does not have. Was: by any finding, so one
    // baseline error (a research frame missing on this disk: "L1: capture … not found") made every mutation look CAUGHT.
    let base = Set(findings(src.levels, src.unlocks, src.tutorials, src.sessions))
    print("selftest baseline (unmutated): \(base.count) finding(s) — a mutation counts only by a finding not in this list")
    for b in base.sorted().prefix(8) { print("  baseline: \(b)") }
    var caught = 0
    for m in muts {
        var lv = src.levels, un = src.unlocks, tu = src.tutorials, se = src.sessions
        m.apply(&lv, &un, &tu, &se)
        let errs = findings(lv, un, tu, se).filter { !base.contains($0) }
        let ok = !errs.isEmpty
        if ok { caught += 1 }
        print("\(ok ? "CAUGHT" : "MISSED") \(m.name)\(errs.first.map { "  [\($0)]" } ?? "")")
    }
    // the research diff must catch a moved arrow, a dropped arrow under a door and a changed timer
    var dcaught = 0
    let research = "research/levels", backfill = "design/tools/work/reveals"
    var diffMuts: [(String, Int, LevelSpec)] = []          // (name, research slot, mutated board)
    var m1 = src.levels[idx(40)]
    if let k = m1.arrows.firstIndex(where: { $0.cells.count >= 3 }) { m1.arrows[k].cells.removeFirst() }
    diffMuts.append(("L40 an arrow one cell shorter" + at(40), 40, m1))
    var m2 = src.levels[idx(58)]; if let k = m2.arrows.firstIndex(where: { $0.hiddenBy != nil }) { m2.arrows.remove(at: k) }
    diffMuts.append(("L58 one arrow under the door dropped" + at(58), 58, m2))
    var m3 = src.levels[idx(45)]; m3.timerSeconds = 180
    diffMuts.append(("L45 substitute given the video's 3:00 instead of the phone slot's 2:30" + at(45), 45, m3))
    var m4 = src.levels[idx(12)]; if let k = m4.obstacles.firstIndex(where: { $0.kind == .box }) { m4.obstacles[k].counter = (m4.obstacles[k].counter ?? 0) + 1 }
    diffMuts.append(("L12 video box counter +1" + at(12), 12, m4))
    for (name, rs, l) in diffMuts {
        // CAUGHT only by a finding the unmutated board's diff does not have (PUBLISH B0, as above)
        let clean = Set(try diffLevel(src.levels[idx(rs)], rslot: rs, research: research, backfill: backfill).errors)
        let d = try diffLevel(l, rslot: rs, research: research, backfill: backfill)
        let new = d.errors.filter { !clean.contains($0) }
        let ok = !new.isEmpty
        if ok { dcaught += 1 }
        print("\(ok ? "CAUGHT" : "MISSED") diff: \(name)\(new.first.map { "  [\($0)]" } ?? "")")
    }
    print("selftest: \(caught)/\(muts.count) validator mutations caught, \(dcaught)/\(diffMuts.count) diff mutations caught")
    return caught == muts.count && dcaught == diffMuts.count ? 0 : 1
}

// MARK: dispatch

let argv = Array(CommandLine.arguments.dropFirst())
guard let cmd = argv.first else { print(usage); exit(64) }
let args = Args(Array(argv.dropFirst()), flags: ["check", "publish"])
do {
    let code: Int32
    switch cmd {
    case "bundle": code = try cmdBundle(args)
    case "check": code = try cmdCheck(args)
    case "freeset": code = try cmdFreeset(args)
    case "diff": code = try cmdDiff(args)
    case "selftest": code = try cmdSelftest(args)
    case "decodebench": code = try cmdDecodeBench(args)
    case "endless": code = try cmdEndless(Args(Array(argv.dropFirst()), flags: ["no-rerun"]))
    case "consistency": code = try cmdConsistency(args)
    case "l2selftest": code = try cmdL2Selftest(args)
    default: print(usage); code = 64
    }
    exit(code)
} catch {
    FileHandle.standardError.write(Data("lvtool \(cmd): \(error)\n".utf8))
    exit(1)
}
