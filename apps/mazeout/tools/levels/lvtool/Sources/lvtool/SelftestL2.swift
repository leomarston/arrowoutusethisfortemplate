import Foundation
import PathCore

// `lvtool l2selftest [--levels App/Resources/Levels] [--rules …] [--art art/ui/out] [--strings …] [--catalog …]`
//
// Negative controls for CONTENT's L2 tests (GAMEPROMPT §8.3): each mutation breaks ONE thing in a real served endless level
// or in the real L1-L150 content, and must be caught by the check it targets (the finding has to come from that check,
// not from an unrelated one). A MISSED mutation = a weak test.

struct L2Mutation {
    let name: String
    let run: () -> [String]           // the targeted check's findings on the mutated input
}

func cmdL2Selftest(_ a: Args) throws -> Int32 {
    let root = FileManager.default.currentDirectoryPath
    let (rules, _) = try loadRules(a.opt("rules", "App/Resources/Tuning/rules.json"))
    let lib = try LevelLibrary.load(folder: URL(fileURLWithPath: a.opt("levels", "App/Resources/Levels")))
    let curve = lib.curve
    let art = artCatalog(a.opt("art", "art/ui/out"))
    let base = try loadContentSet(a)

    // real served endless levels
    var served: [Int: LevelSpec] = [:]
    for n in 151...190 { served[n] = LevelProvider.produce(n, curve: curve, library: lib, options: Validator.Options()).0 }
    func firstWith(_ k: ObstacleKind, where f: (ObstacleSpec) -> Bool = { _ in true }) -> LevelSpec {
        served.keys.sorted().map { served[$0]! }.first { $0.obstacles.contains { $0.kind == k && f($0) } }!
    }
    let tapeL = firstWith(.tape), doorL = firstWith(.door), boxL = firstWith(.box), pipeL = firstWith(.pipe)
    let cornerL = firstWith(.corner)                    // F3-B: corners ship (ruling 26), the endless range serves them
    func check(_ l: LevelSpec, route: String = "generated", art: Set<String> = art) -> [String] {
        endlessCheck(l, n: l.level, route: route, curve: curve, rules: rules, art: art, root: root).errors
    }
    func only(_ xs: [String], _ marker: String) -> [String] { xs.filter { $0.contains(marker) } }

    var muts: [L2Mutation] = []
    // --- endless: repeats
    muts.append(L2Mutation(name: "endless: L152 given L151's board (exact repeat)") {
        var b = served[152]!; let s = served[151]!
        b.arrows = s.arrows; b.obstacles = s.obstacles; b.cols = s.cols; b.rows = s.rows
        return repeatScan([s, b], checked: [152]).exact
    })
    muts.append(L2Mutation(name: "endless: L152 = L151 mirrored left-right (repeat up to symmetry)") {
        var b = served[152]!; let s = served[151]!
        b.cols = s.cols; b.rows = s.rows; b.obstacles = []
        b.arrows = s.arrows.map { var x = $0; x.cells = x.cells.map { Cell(s.cols - 1 - $0.c, $0.r) }; x.dir = Dir(from: x.cells[x.cells.count - 2], to: x.cells.last!) ?? x.dir; return x }
        return repeatScan([s, b], checked: [152]).shape
    })
    muts.append(L2Mutation(name: "endless: L152 = L151 minus one arrow, shifted 2 cells right (near repeat)") {
        var b = served[152]!; let s = served[151]!
        b.arrows = Array(s.arrows.dropFirst()).map { var x = $0; x.cells = x.cells.map { Cell($0.c + 2, $0.r) }; return x }
        b.obstacles = []; b.cols = s.cols + 2; b.rows = s.rows
        return repeatScan([s, b], checked: [152]).near
    })
    // --- endless: route, cadence, timer, curve band, solvability
    muts.append(L2Mutation(name: "endless: L151 served by the fallback route") { only(check(served[151]!, route: "fallback"), "fallback") })
    muts.append(L2Mutation(name: "endless: L154 (Hard slot) tagged normal") { var l = served[154]!; l.tag = .normal; return only(check(l), "the cadence says") })
    muts.append(L2Mutation(name: "endless: L155 given a 2:00 timer (a Super Hard timer on a normal level)") { var l = served[155]!; l.timerSeconds = 120; return only(check(l), "normal timer") })
    // F3-B: the template timer rule (curve.timers.fromTemplate) must refuse a Hard level off its template's recorded timer
    muts.append(L2Mutation(name: "endless: L154 (Hard) off its template's recorded timer") {
        var l = served[154]!; l.timerSeconds = l.timerSeconds == 180 ? 150 : 180; return only(check(l), "Hard timer")
    })
    muts.append(L2Mutation(name: "endless: L155 renumbered into the Hard slot L164 (off its curve band)") { var l = served[155]!; l.level = 164; return only(check(l), "curve band") })
    muts.append(L2Mutation(name: "endless: a deadlock added to L151 (two arrows face each other)") {
        var l = served[151]!
        let occupied = Set(l.arrows.flatMap(\.cells)).union(l.obstacles.flatMap(\.cells))
        for x in l.arrows {
            let d = x.dir.opposite
            let c1 = x.head + x.dir, c2 = c1 + x.dir
            guard l.grid.inBounds(c1), l.grid.inBounds(c2), !occupied.contains(c1), !occupied.contains(c2) else { continue }
            l.arrows.append(ArrowSpec(id: ArrowID(9000), cells: [c2, c1], dir: d))
            l.metrics = nil
            return only(check(l), "stuck")
        }
        // PUBLISH B0: the served L151 is tiled edge to edge (no free cell in front of any head), so the search above found no
        // spot and this mutation returned nothing: a silent MISSED (before B0 too). The pair then goes into a new empty
        // column on the right: A (x,0)->(x,1) down and B (x,3)->(x,2) up, each head facing the other.
        let x = l.cols
        l.cols += 1
        let next = (l.arrows.map(\.id.raw).max() ?? 0) + 1
        l.arrows.append(ArrowSpec(id: ArrowID(next), cells: [Cell(x, 0), Cell(x, 1)], dir: .down))
        l.arrows.append(ArrowSpec(id: ArrowID(next + 1), cells: [Cell(x, 3), Cell(x, 2)], dir: .up))
        l.metrics = nil
        return only(check(l), "stuck")
    })
    // --- endless: renderability
    muts.append(L2Mutation(name: "endless: a door squeezed to 2 rows") {
        var l = doorL
        let k = l.obstacles.firstIndex { $0.kind == .door }!
        let cs = l.obstacles[k].cells, r0 = cs.map(\.r).min()!
        l.obstacles[k].cells = cs.filter { $0.r < r0 + 2 }
        return renderProblems(l, art: art).errors.filter { $0.contains("below 3x3") }
    })
    muts.append(L2Mutation(name: "endless: a box counter of 100") {
        var l = boxL; let k = l.obstacles.firstIndex { $0.kind == .box }!; l.obstacles[k].counter = 100
        return renderProblems(l, art: art).errors.filter { $0.contains("1-99") }
    })
    muts.append(L2Mutation(name: "endless: a pipe counter of 10") {
        var l = pipeL; let k = l.obstacles.firstIndex { $0.kind == .pipe }!; l.obstacles[k].counter = 10
        return renderProblems(l, art: art).errors.filter { $0.contains("1-9") }
    })
    muts.append(L2Mutation(name: "endless: the tape sprites missing from the art") {
        renderProblems(tapeL, art: art.filter { !$0.hasPrefix("tape") }).errors.filter { $0.contains("sprite tape") }
    })
    muts.append(L2Mutation(name: "endless: a tape tie with a 5th lane") {
        var l = tapeL; let k = l.obstacles.firstIndex { $0.kind == .tape }!
        let cs = l.obstacles[k].cells; let d = Dir(from: cs[0], to: cs.count > 1 ? cs[1] : cs[0] + .right) ?? .right
        l.obstacles[k].cells.append(cs.last! + d)
        return renderProblems(l, art: art).errors.filter { $0.contains("tape") }
    })
    // F3-B (2026-09-29): was "a corner obstacle" (any corner refused: "corners are not shipped"). Corners ship since ruling 26,
    // so the render check now asks what CornerNode needs: its facing's sprites and one cell with a turn.
    muts.append(L2Mutation(name: "endless: a served corner's facing sprites missing from the art") {
        renderProblems(cornerL, art: art.filter { !($0.hasPrefix("corner") && ($0.hasSuffix("Spring") || $0.hasSuffix("Plate"))) })
            .errors.filter { $0.contains("sprite corner") }
    })
    muts.append(L2Mutation(name: "endless: a served corner stretched to 2 cells") {
        var l = cornerL; let k = l.obstacles.firstIndex { $0.kind == .corner }!
        let c = l.obstacles[k].cells[0]; l.obstacles[k].cells.append(Cell(c.c == 0 ? 1 : c.c - 1, c.r))
        return renderProblems(l, art: art).errors.filter { $0.contains("one cell with a turn") }
    })
    muts.append(L2Mutation(name: "endless: a 27-column grid (below the 14.04 pt zoom floor)") {
        var l = served[151]!; l.cols = 27
        return only(check(l), "zoom floor")
    })
    muts.append(L2Mutation(name: "endless: an unlock card on a generated level") { var l = served[151]!; l.unlock = FeatureID(rawValue: "door"); return only(check(l), "unlock card") })

    // --- consistency (L1-L150 + strings + art)
    func cons(_ f: (inout ContentSet) -> Void, _ marker: String) -> [String] {
        var c = base
        f(&c)
        return consistencyErrors(c, rules: rules).errors.filter { $0.contains(marker) }
    }
    func idx(_ n: Int) -> Int { n - 1 }
    muts.append(L2Mutation(name: "consistency: the Linked card moved to L8") {
        cons({ c in
            let k = c.unlocks.firstIndex { $0.feature.rawValue == "linked" }!
            c.unlocks[k].level = 8; c.levels[idx(8)].unlock = c.levels[idx(7)].unlock; c.levels[idx(7)].unlock = nil
        }, "linked")
    })
    muts.append(L2Mutation(name: "consistency: the Box card retitled \"Crate!\" (no strings row)") {
        cons({ c in let k = c.unlocks.firstIndex { $0.feature.rawValue == "box" }!; c.unlocks[k].title = "Crate!" }, "Crate!")
    })
    muts.append(L2Mutation(name: "consistency: the \"Box!\" title's strings row deleted") { cons({ c in c.strings["Box!"] = nil }, "has no EN/TR row") })
    muts.append(L2Mutation(name: "consistency: the tutorial hand on a missing arrow") {
        cons({ c in c.tutorials[0].hand = TutorialHand(arrow: ArrowID(99), at: [0.89, 1.06]) }, "tutorial hand")
    })
    muts.append(L2Mutation(name: "consistency: the tutorial hand on a blocked arrow (L1 given a deadlock at arrow 1)") {
        cons({ c in
            var l = c.levels[idx(1)]
            let k = l.arrows.firstIndex { $0.id == ArrowID(1) }!
            l.arrows[k].cells = [Cell(1, 3), Cell(1, 2)]
            l.arrows.append(ArrowSpec(id: ArrowID(3), cells: [Cell(1, 0), Cell(1, 1)], dir: .down))
            c.levels[idx(1)] = l
        }, "NOT free")
    })
    muts.append(L2Mutation(name: "consistency: the tutorial on stage 1") { cons({ c in c.tutorials[0].stage = 1 }, "stage") })
    muts.append(L2Mutation(name: "consistency: the TR Linked card without its caps run") {
        cons({ c in c.strings["LINKED ARROWS move together!"] = "bağlı oklar birlikte hareket eder!" }, "upper-case run")
    })
    muts.append(L2Mutation(name: "consistency: a stale catalogue (Box! = \"Sandık!\")") { cons({ c in c.catalog["Box!"] = "Sandık!" }, "catalogue stale") })
    muts.append(L2Mutation(name: "consistency: the Pipe card icon missing from the art") { cons({ c in c.art.remove("unlockIconPipe") }, "unlockIconPipe") })
    muts.append(L2Mutation(name: "consistency: curve firstLevel box 12 (the generator's schedule off the card)") {
        cons({ c in
            var ob = c.curve.obstacles; ob.firstLevel["box"] = 12; c.curve.obstacles = ob
        }, "firstLevel")
    })
    muts.append(L2Mutation(name: "consistency: L44 tagged normal") { cons({ c in c.levels[idx(44)].tag = .normal }, "L44: tag") })
    muts.append(L2Mutation(name: "consistency: an extra Box card on L12") { cons({ c in c.levels[idx(12)].unlock = FeatureID(rawValue: "box") }, "L12") })
    muts.append(L2Mutation(name: "consistency: the Levels 1-4 reward 70") { cons({ c in c.sessions[0].reward = 70 }, "reward") })
    // PUBLISH B0: re-targeted from L74 (a RECORDED board since the content recast, whose timer the designed-level rule does
    // not govern: the mutation found nothing, a silent MISSED before B0 too) to the designed Hard L124 (template timer 2:00)
    // F3-B: the design row moves with the bundle (the provenance now comes from design/levels.json, which bundle --check keeps
    // byte-equal), so the finding must come from the template rule itself, not from the new bundle-vs-design timer check
    muts.append(L2Mutation(name: "consistency: the designed Hard L124 at 3:30") {
        cons({ c in c.levels[idx(124)].timerSeconds = 210; c.design[124] = DesignRow(source: c.design[124]!.source, from: c.design[124]!.from, timer: 210) },
             "L124: designed hard level with timer 210")
    })
    muts.append(L2Mutation(name: "consistency: the bundled L124 timer off its design row") { cons({ c in c.levels[idx(124)].timerSeconds = 210 }, "!= the design's") })
    muts.append(L2Mutation(name: "consistency: the L33 door squeezed to 2 rows") {
        cons({ c in
            let k = c.levels[idx(33)].obstacles.firstIndex { $0.kind == .door }!
            let cs = c.levels[idx(33)].obstacles[k].cells, r0 = cs.map(\.r).min()!
            c.levels[idx(33)].obstacles[k].cells = cs.filter { $0.r < r0 + 2 }
        }, "below 3x3")
    })
    muts.append(L2Mutation(name: "consistency: social.json Weekly Contest at L49") { cons({ c in c.social?["weeklyContest"] = 49 }, "social.json") })
    // F3-B: was "a corner in L100" (any corner refused). Corners ship from their card at L70 (ruling 26), so a corner BEFORE
    // L70 must be caught as an early first appearance, and the pinned card itself must hold.
    muts.append(L2Mutation(name: "consistency: a corner in L60 (before its card at L70)") {
        cons({ c in c.levels[idx(60)].obstacles.append(ObstacleSpec(id: ObstacleID("x0"), kind: .corner, cells: [Cell(0, 0)], turn: .upRight)) }, "corner")
    })
    muts.append(L2Mutation(name: "consistency: the Corner card retitled \"Turn!\"") {
        cons({ c in let k = c.unlocks.firstIndex { $0.feature.rawValue == "corner" }!; c.unlocks[k].title = "Turn!" }, "Turn!")
    })
    muts.append(L2Mutation(name: "consistency: the stand-in L101 given its template's 2:30, not its phone slot's 3:00") {
        cons({ c in c.levels[idx(101)].timerSeconds = 150; c.design[101] = DesignRow(source: "designed", from: c.design[101]?.from, timer: 150) }, "stand-in")
    })
    muts.append(L2Mutation(name: "consistency: the recorded L58 read as designed (the publish form's provenance)") {
        cons({ c in c.design[58] = DesignRow(source: "designed", from: nil, timer: c.design[58]!.timer) }, "L58: designed")
    })
    muts.append(L2Mutation(name: "consistency: social.json Balloon Rise at L34 (off the Claw's top-bar slot)") { cons({ c in c.social?["balloonRise"] = 34 }, "social.json") })

    // the unmutated inputs must be clean for every targeted check (else a CAUGHT proves nothing)
    let cleanEndless = [151, 152, 154, 155].flatMap { check(served[$0]!) }
    let cleanRender = [tapeL, doorL, boxL, pipeL, cornerL].flatMap { renderProblems($0, art: art).errors }
    let cleanRepeats = repeatScan([served[151]!, served[152]!], checked: [152])
    let cleanCons = consistencyErrors(base, rules: rules).errors
    var ok = cleanEndless.isEmpty && cleanRender.isEmpty && cleanRepeats.exact.isEmpty && cleanRepeats.shape.isEmpty && cleanRepeats.near.isEmpty && cleanCons.isEmpty
    print("baseline (unmutated): endless \(cleanEndless.count), render \(cleanRender.count), repeats \(cleanRepeats.exact.count + cleanRepeats.shape.count + cleanRepeats.near.count), consistency \(cleanCons.count) finding(s)\(ok ? "" : "  <- must be 0")")
    for x in (cleanEndless + cleanRender + cleanCons).prefix(10) { print("  baseline: \(x)") }
    print("mutation sources: tape L\(tapeL.level), door L\(doorL.level), box L\(boxL.level), pipe L\(pipeL.level), corner L\(cornerL.level)")
    var caught = 0
    for m in muts {
        let f = m.run()
        if !f.isEmpty { caught += 1 }
        print("\(f.isEmpty ? "MISSED" : "CAUGHT") \(m.name)\(f.first.map { "  [\($0)]" } ?? "")")
    }
    print("l2selftest: \(caught)/\(muts.count) mutations caught")
    ok = ok && caught == muts.count
    return ok ? 0 : 1
}
