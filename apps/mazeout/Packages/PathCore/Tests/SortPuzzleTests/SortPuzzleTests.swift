import XCTest
import Foundation
import GameCore
import SortPuzzle   // not @testable: the module is used through its public API and the generic contract

/// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §6b): the second puzzle module.
///  - the generator and the solver agree with the independent Python reference (tools/sortpuzzle/ref.py → the goldens in
///    Tests/Fixtures/sortpuzzle_goldens.json, made from the shipped sort.json);
///  - every early level is solvable and the recorded solution replays to a solved board;
///  - a bot that knows only `PuzzleSession` wins levels (single- and multi-stage), `won` exactly once;
///  - "stuck" opens the config's chain, a continue adds a tube, declining ends in `lost(.stuck)` exactly once;
///  - the undo and extra-tube boosters; the contract conformance (capabilities, idle clock, no hearts, move projections).
final class SortPuzzleTests: XCTestCase {

    // MARK: fixtures (paths from #filePath: no SwiftPM resources in this package)

    static var testsDir: URL { URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent() }
    /// apps/<slug>/ (Tests → PathCore → Packages → the app folder).
    static var appDir: URL { testsDir.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent() }

    struct Golden: Decodable {
        let level: Int
        let tag: String
        let capacity: Int
        let colors: Int
        let tubes: [[Int]]
        let hash: String
        let solution: Int?
        let moves: [[Int]]?
    }

    struct GoldenSet: Decodable {
        let rules: SortRules
        let levels: [Golden]
    }

    struct GoldenDoc: Decodable {
        let rules: SortRules
        let levels: [Golden]
        let stress: GoldenSet
    }

    func goldens() throws -> GoldenDoc {
        let url = Self.testsDir.appendingPathComponent("Fixtures/sortpuzzle_goldens.json")
        return try JSONDecoder().decode(GoldenDoc.self, from: Data(contentsOf: url))
    }

    /// FNV-1a 64 over UTF-8 (ref.py `fnv1a64`), upper-case hex.
    static func fnvHex(_ s: String) -> String {
        var h: UInt64 = 0xCBF2_9CE4_8422_2325
        for b in s.utf8 { h ^= UInt64(b); h = h &* 0x0000_0100_0000_01B3 }
        return String(format: "%016llX", h)
    }

    func session(_ levels: [SortLevel], rules: SortRules = SortRules(), meta: MetaRules = MetaRules(),
                 streakActive: Bool = false, attempt: Int = 1) -> SortPuzzleSession {
        SortPuzzleModule.makeSession(stages: levels, setup: AttemptSetup(levels: levels.map(\.level), attemptIndex: attempt),
                                     meta: meta, rules: rules, streakActive: streakActive)
    }

    /// Start + intro: the session is `.ready`.
    func ready(_ s: any PuzzleSession) {
        _ = s.start()
        _ = s.ack(.introFinished)
    }

    static func metas(_ outputs: [SessionOutput]) -> [MetaEvent] { outputs.compactMap(\.metaEvent) }

    static func wins(_ outputs: [SessionOutput]) -> Int {
        metas(outputs).filter { if case .won = $0 { return true }; return false }.count
    }

    static func losses(_ outputs: [SessionOutput]) -> [LossReason] {
        metas(outputs).compactMap { if case .lost(let r) = $0 { return r }; return nil }
    }

    /// A 3-colour board of capacity 3 where pouring tube 0 into the empty tube 3 leaves no legal pour (stuck), while the
    /// board itself is solvable (tube 1 into tube 3 first).
    static let stuckLevel = SortLevel(level: 7, tag: .normal, capacity: 3, colors: 3,
                                      tubes: [[2, 1, 0], [0, 1, 2], [1, 0, 2], []])

    // MARK: the Python reference

    func testGoldensMatchThePythonReference() throws {
        let doc = try goldens()
        for (name, rules, rows) in [("", doc.rules, doc.levels), ("stress ", doc.stress.rules, doc.stress.levels)] {
            XCTAssertFalse(rows.isEmpty)
            for g in rows {
                let l = SortGenerator.level(g.level, rules: rules)
                XCTAssertEqual(l.tubes, g.tubes, "\(name)L\(g.level) tubes")
                XCTAssertEqual(l.tag.rawValue, g.tag, "\(name)L\(g.level) tag")
                XCTAssertEqual(l.capacity, g.capacity, "\(name)L\(g.level) capacity")
                XCTAssertEqual(l.colors, g.colors, "\(name)L\(g.level) colours")
                XCTAssertEqual(Self.fnvHex(l.canonical), g.hash, "\(name)L\(g.level) hash of \(l.canonical)")
                let solution = SortSolver.solve(l.tubes, capacity: l.capacity, budget: rules.levels.solverBudget)
                XCTAssertEqual(solution?.count, g.solution, "\(name)L\(g.level) the solver's first solution")
                if let moves = g.moves {
                    XCTAssertEqual(solution?.map { [$0.from, $0.to] }, moves, "\(name)L\(g.level) the solution's pours")
                }
            }
        }
        XCTAssertTrue(doc.stress.levels.contains { $0.tubes.count == $0.colors * 2 },
                      "the stress set pins the last-resort deal (one empty tube per colour)")
    }

    func testRulesDefaultsAreTheShippedSortJSON() throws {
        let url = Self.appDir.appendingPathComponent("App/Resources/Tuning/sort.json")
        let data = try Data(contentsOf: url)
        let (rules, problems) = SortRules.load(json: data)
        XCTAssertEqual(problems, [])
        XCTAssertEqual(rules, SortRules(), "the Swift defaults are the shipped data (sort.json)")
        XCTAssertEqual(try goldens().rules, rules, "the goldens were made from the shipped sort.json (ref.py --check)")
        XCTAssertEqual(SortRules.load(json: nil).rules, SortRules.default)
        XCTAssertEqual(SortRules.load(json: Data("{\"play\":{\"maxExtraTubes\":5}}".utf8)).rules.play.maxExtraTubes, 5)
        XCTAssertFalse(SortRules.load(json: Data("[1]".utf8)).problems.isEmpty)
    }

    // MARK: the generator

    func testGeneratorIsDeterministicAndSaltDependent() {
        let rules = SortRules()
        for n in [1, 5, 17, 40, 99] {
            XCTAssertEqual(SortGenerator.level(n, rules: rules), SortGenerator.level(n, rules: rules), "L\(n)")
        }
        var other = rules
        other.levels.salt &+= 1
        XCTAssertNotEqual(SortGenerator.level(9, rules: rules).tubes, SortGenerator.level(9, rules: other).tubes)
        XCTAssertNotEqual(SortGenerator.level(9, rules: rules).tubes, SortGenerator.level(10, rules: rules).tubes)
    }

    func testFirstLevelsAreSolvableWellFormedAndFollowTheCurve() {
        let rules = SortRules()
        for n in 1...60 {
            let l = SortGenerator.level(n, rules: rules)
            let band = rules.levels.band(for: n)
            XCTAssertEqual(l.colors, band.colors, "L\(n)")
            XCTAssertEqual(l.capacity, band.capacity, "L\(n)")
            XCTAssertEqual(l.tubes.count, band.colors + band.empty, "L\(n): accepted at a normal deal")
            var counts: [Int: Int] = [:]
            for t in l.tubes {
                XCTAssertLessThanOrEqual(t.count, l.capacity)
                for u in t { counts[u, default: 0] += 1 }
            }
            XCTAssertEqual(counts.keys.sorted(), Array(0..<l.colors), "L\(n)")
            XCTAssertTrue(counts.values.allSatisfy { $0 == l.capacity }, "L\(n) \(counts)")
            XCTAssertFalse(l.tubes.contains { SortMechanics.isComplete($0, capacity: l.capacity) }, "L\(n): no complete tube dealt")
            guard let solution = SortSolver.solve(l.tubes, capacity: l.capacity, budget: rules.levels.solverBudget) else {
                XCTFail("L\(n) unsolvable within the budget"); continue
            }
            var state = l.tubes
            for m in solution {
                XCTAssertTrue(SortMechanics.canPour(state, from: m.from, to: m.to, capacity: l.capacity), "L\(n) \(m)")
                state = SortMechanics.apply(state, m, capacity: l.capacity)
            }
            XCTAssertTrue(SortMechanics.isSolved(state, capacity: l.capacity), "L\(n): the solution solves it")
            XCTAssertEqual(l.tag, rules.levels.tag(for: n))
        }
        XCTAssertEqual(rules.levels.tag(for: 10), .hard)
        XCTAssertEqual(rules.levels.tag(for: 25), .superHard)
        XCTAssertEqual(rules.levels.tag(for: 50), .superHard, "super hard wins a tie")
        XCTAssertEqual(rules.levels.tag(for: 11), .normal)
    }

    // MARK: the rules

    func testPourRules() {
        let c = 4
        let tubes = [[0, 1, 1], [2, 1], [], [0, 0, 0, 0], [2]]
        XCTAssertTrue(SortMechanics.canPour(tubes, from: 0, to: 1, capacity: c), "onto the same colour")
        XCTAssertEqual(SortMechanics.pourCount(tubes, from: 0, to: 1, capacity: c), 2, "the top run, as many as fit")
        XCTAssertTrue(SortMechanics.canPour(tubes, from: 0, to: 2, capacity: c), "into an empty tube")
        XCTAssertFalse(SortMechanics.canPour(tubes, from: 0, to: 4, capacity: c), "onto another colour")
        XCTAssertFalse(SortMechanics.canPour(tubes, from: 1, to: 3, capacity: c), "into a full tube")
        XCTAssertFalse(SortMechanics.canPour(tubes, from: 2, to: 1, capacity: c), "from an empty tube")
        XCTAssertFalse(SortMechanics.canPour(tubes, from: 0, to: 0, capacity: c))
        XCTAssertFalse(SortMechanics.canPour(tubes, from: 0, to: 9, capacity: c))
        XCTAssertEqual(SortMechanics.apply(tubes, SortMove(0, 1), capacity: c)[0], [0])
        XCTAssertEqual(SortMechanics.apply(tubes, SortMove(0, 1), capacity: c)[1], [2, 1, 1, 1])
        XCTAssertTrue(SortMechanics.isComplete([0, 0, 0, 0], capacity: c))
        XCTAssertFalse(SortMechanics.isComplete([0, 0, 0], capacity: c))
        XCTAssertTrue(SortMechanics.isSolved([[1, 1], [], [0, 0]], capacity: 2))
        XCTAssertFalse(SortMechanics.isSolved([[1, 0], [], [0, 1]], capacity: 2))
        XCTAssertFalse(SortMechanics.hasLegalMove([[0, 1], [1, 0]], capacity: 2))
        XCTAssertEqual(SortSolver.solve([[1, 1], [0, 0]], capacity: 2, budget: 10), [], "already solved")
        XCTAssertNil(SortSolver.solve([[0, 1], [1, 0]], capacity: 2, budget: 100), "no pour at all")
        XCTAssertEqual(SortMechanics.key([[1], [0, 2]]), SortMechanics.key([[0, 2], [1]]), "a multiset of tubes")
    }

    // MARK: the bot, through the contract only

    func testBotWinsTheFirstLevelsThroughTheContract() {
        let rules = SortRules()
        for n in 1...25 {
            let s: any PuzzleSession = session([SortGenerator.level(n, rules: rules)])
            let o = SortBot.play(s)
            XCTAssertNotNil(o.result, "L\(n) won")
            XCTAssertNil(o.lost)
            XCTAssertEqual(Self.wins(o.outputs), 1, "L\(n): won exactly once")
            XCTAssertTrue(s.isFinished)
            if case .won(let r) = s.phase {
                XCTAssertEqual(r.levels, [n])
                XCTAssertEqual(r.reward, MetaRules().rewards.reward(for: rules.levels.tag(for: n)))
                XCTAssertEqual(r.bumps, 0, "the plan never pours illegally")
                XCTAssertEqual(r.stats["pours"].map { Int($0) }, SortSolver.solve(SortGenerator.level(n, rules: rules).tubes,
                               capacity: 4, budget: rules.play.hintBudget)?.count, "L\(n): the bot follows the solver's plan")
            } else {
                XCTFail("L\(n) phase \(s.phase)")
            }
            XCTAssertFalse(Self.metas(o.outputs).contains { if case .offer = $0 { return true }; return false },
                           "the plan never gets stuck")
            // after the win: nothing else happens
            XCTAssertEqual(SessionOutput.sortEvents(s.input(.select(PuzzleTarget(0)), at: 99)), [.ignored(tube: 0)])
            XCTAssertTrue(s.quit().isEmpty)
            XCTAssertTrue(s.acceptContinue().isEmpty)
            XCTAssertTrue(s.declineContinue().isEmpty)
        }
    }

    func testMultiStageSessionOneWin() {
        let rules = SortRules()
        let stages = [SortGenerator.level(3, rules: rules), SortGenerator.level(4, rules: rules),
                      SortGenerator.level(5, rules: rules)]
        let s = session(stages)
        XCTAssertEqual(s.stageCount, 3)
        let o = SortBot.play(s)
        let metas = Self.metas(o.outputs)
        XCTAssertEqual(metas.filter { if case .stageCleared = $0 { return true }; return false }.count, 2)
        XCTAssertEqual(metas.filter { if case .stageAdvanced = $0 { return true }; return false }.count, 2)
        XCTAssertEqual(metas.filter { if case .stageLoaded = $0 { return true }; return false }.count, 3)
        XCTAssertEqual(metas.filter { if case .timerStarted = $0 { return true }; return false }.count, 3,
                       "each stage's first selection")
        XCTAssertEqual(Self.wins(o.outputs), 1)
        XCTAssertEqual(o.result?.levels, [3, 4, 5])
        XCTAssertEqual(s.stage, 2)
        // a session that starts at stage 1 (-pc.stage)
        let late = SortPuzzleModule.makeSession(stages: stages, setup: AttemptSetup(levels: [3, 4, 5], firstStage: 1),
                                                meta: MetaRules(), rules: rules)
        XCTAssertEqual(late.stage, 1)
        XCTAssertEqual(Self.metas(late.start()), [.stageLoaded(stage: 1, of: 3, level: 4)])
    }

    // MARK: stuck, continue, lost

    func testStuckOpensTheChainAndAnExtraTubeContinues() {
        let s = session([Self.stuckLevel])
        ready(s)
        XCTAssertEqual(s.phase, .ready(stage: 0))
        var out = s.input(.select(PuzzleTarget(0)), at: 1)
        XCTAssertEqual(Self.metas(out), [.timerStarted(stage: 0)])
        XCTAssertEqual(SessionOutput.sortEvents(out), [.selected(tube: 0, count: 1)])
        XCTAssertEqual(s.phase, .playing(stage: 0))
        out = s.input(.select(PuzzleTarget(3)), at: 2)
        XCTAssertEqual(SessionOutput.sortEvents(out), [.poured(from: 0, to: 3, count: 1, color: 0)])
        guard case .offer(let o)? = Self.metas(out).last else { return XCTFail("stuck → an offer: \(out)") }
        XCTAssertEqual(o.kind, .stuck)
        XCTAssertEqual(o.step, 0)
        XCTAssertEqual(o.grant, .puzzleAction(id: SortPuzzleModule.extraTubeAction, amount: 1), "sort.json's default chain")
        XCTAssertEqual(o.price, 900)
        XCTAssertEqual(s.phase, .offer(o))
        XCTAssertNil(s.hint(), "no hint while the offer is up")
        XCTAssertEqual(SessionOutput.sortEvents(s.input(.select(PuzzleTarget(1)), at: 3)), [.ignored(tube: 1)])
        XCTAssertFalse(s.canUseBooster(SortPuzzleModule.undo), "boosters wait for the offer")

        out = s.acceptContinue()
        XCTAssertEqual(Self.metas(out), [.continued(o)])
        XCTAssertEqual(SessionOutput.sortEvents(out), [.tubesAdded(count: 1, total: 5)])
        XCTAssertEqual(s.tubes.count, 5)
        XCTAssertEqual(s.phase, .playing(stage: 0))
        let rest = SortBot.play(s)
        XCTAssertEqual(Self.wins(rest.outputs), 1)
        if case .won(let r) = s.phase {
            XCTAssertEqual(r.stats["tubesAdded"], 1)
        } else {
            XCTFail("won after the extra tube: \(s.phase)")
        }
    }

    func testStuckDeclinedEndsLostExactlyOnce() {
        for streak in [false, true] {
            let s = session([Self.stuckLevel], streakActive: streak)
            ready(s)
            var all = s.input(.select(PuzzleTarget(0)), at: 1) + s.input(.select(PuzzleTarget(3)), at: 2)
            var offers = 0
            while case .offer = s.phase {
                offers += 1
                all += s.declineContinue()
            }
            XCTAssertEqual(offers, streak ? 3 : 2, "the streak step only with a running streak")
            XCTAssertEqual(Self.losses(all), [.stuck], "lost exactly once")
            XCTAssertEqual(s.phase, .lost(.stuck))
            XCTAssertTrue(s.declineContinue().isEmpty)
            XCTAssertTrue(s.quit().isEmpty, "a finished session has nothing to quit")
            XCTAssertEqual(Self.wins(all), 0)
        }
    }

    func testAChainOfTheConfigWinsOverTheModulesDefault() {
        var meta = MetaRules()
        meta.failChain["stuck"] = [MetaRules.FailStep(price: 300, grant: .none, amount: 2, action: SortPuzzleModule.undoAction)]
        let s = session([Self.stuckLevel], meta: meta)
        ready(s)
        _ = s.input(.select(PuzzleTarget(0)), at: 1)
        let out = s.input(.select(PuzzleTarget(3)), at: 2)
        guard case .offer(let o)? = Self.metas(out).last else { return XCTFail("\(out)") }
        XCTAssertEqual(o.price, 300)
        XCTAssertEqual(o.grant, .puzzleAction(id: SortPuzzleModule.undoAction, amount: 2))
        XCTAssertTrue(o.isLast)
        let after = s.acceptContinue()
        XCTAssertEqual(SessionOutput.sortEvents(after), [.undone(from: 3, to: 0, count: 1)], "the stuck pour taken back")
        XCTAssertEqual(s.tubes, Self.stuckLevel.tubes)
        XCTAssertEqual(s.phase, .playing(stage: 0))
    }

    func testQuitLosesOnce() {
        let s = session([SortGenerator.level(1, rules: SortRules())])
        XCTAssertTrue(s.quit().isEmpty, "not started")
        ready(s)
        XCTAssertEqual(Self.metas(s.quit()), [.lost(.quit)])
        XCTAssertTrue(s.quit().isEmpty)
        XCTAssertTrue(s.isFinished)
    }

    // MARK: selection and boosters

    func testSelectionRefusalAndUndoBooster() {
        let level = SortLevel(level: 2, tag: .normal, capacity: 2, colors: 2, tubes: [[0, 1], [1, 0], []])
        let s = session([level])
        ready(s)
        XCTAssertFalse(s.canUseBooster(SortPuzzleModule.undo), "nothing to undo yet")
        XCTAssertEqual(SessionOutput.sortEvents(s.input(.select(PuzzleTarget(2)), at: 1)), [.ignored(tube: 2)],
                       "an empty tube lifts nothing")
        XCTAssertEqual(s.phase, .ready(stage: 0), "…and does not start the stage")
        XCTAssertEqual(SessionOutput.sortEvents(s.input(.tap(nil), at: 1)), [.ignored(tube: nil)])
        _ = s.input(.select(PuzzleTarget(0)), at: 1)
        XCTAssertEqual(SessionOutput.sortEvents(s.input(.select(PuzzleTarget(0)), at: 2)), [.deselected(tube: 0)])
        _ = s.input(.select(PuzzleTarget(0)), at: 3)
        let refused = s.input(.select(PuzzleTarget(1)), at: 4)
        XCTAssertEqual(SessionOutput.sortEvents(refused), [.refused(from: 0, to: 1)], "a full tube")
        XCTAssertEqual(refused.compactMap(\.move), [PuzzleMove(target: PuzzleTarget(1), failed: true)])
        XCTAssertNil(s.selection, "a refusal drops the selection")
        let poured = s.input(.tap(PuzzleTarget(0)), at: 5) + s.input(.tap(PuzzleTarget(2)), at: 6)
        XCTAssertEqual(poured.compactMap(\.move), [PuzzleMove(target: PuzzleTarget(2), failed: false)])
        XCTAssertEqual(s.tubes, [[0], [1, 0], [1]])
        XCTAssertTrue(s.canUseBooster(SortPuzzleModule.undo))
        _ = s.input(.select(PuzzleTarget(1)), at: 7)                    // a lift pending when the undo comes
        let undo = s.useBooster(SortPuzzleModule.undo)
        XCTAssertEqual(Self.metas(undo), [.boosterUsed(SortPuzzleModule.undo)])
        XCTAssertEqual(SessionOutput.sortEvents(undo), [.deselected(tube: 1), .undone(from: 2, to: 0, count: 1)])
        XCTAssertEqual(s.tubes, level.tubes)
        XCTAssertFalse(s.canUseBooster(SortPuzzleModule.undo))
        XCTAssertTrue(s.useBooster(SortPuzzleModule.undo).isEmpty, "nothing to undo: no output")
        XCTAssertEqual(s.undos, 1)
        XCTAssertFalse(s.canUseBooster(BoosterID("freeze")), "not one of this module's boosters")
    }

    func testExtraTubeBoosterIsCappedPerStage() {
        var rules = SortRules()
        rules.play.maxExtraTubes = 2
        let l = SortGenerator.level(4, rules: rules)
        let s = session([l], rules: rules)
        XCTAssertFalse(s.canUseBooster(SortPuzzleModule.extraTube), "not before the intro")
        ready(s)
        for i in 1...2 {
            XCTAssertTrue(s.canUseBooster(SortPuzzleModule.extraTube))
            let out = s.useBooster(SortPuzzleModule.extraTube)
            XCTAssertEqual(SessionOutput.sortEvents(out), [.tubesAdded(count: 1, total: l.tubes.count + i)])
        }
        XCTAssertFalse(s.canUseBooster(SortPuzzleModule.extraTube))
        XCTAssertTrue(s.useBooster(SortPuzzleModule.extraTube).isEmpty)
        XCTAssertEqual(s.phase, .ready(stage: 0), "a booster does not start the stage")
        XCTAssertEqual(Self.wins(SortBot.play(s).outputs), 1, "still winnable with the extra tubes")
    }

    func testDragIsBothPicks() {
        let level = SortLevel(level: 2, tag: .normal, capacity: 2, colors: 2, tubes: [[0, 1], [1, 0], []])
        let s = session([level])
        ready(s)
        _ = s.input(.select(PuzzleTarget(1)), at: 1)                    // another tube lifted first
        let out = s.input(.drag(from: PuzzleTarget(0), to: PuzzleTarget(2)), at: 2)
        XCTAssertEqual(SessionOutput.sortEvents(out), [.deselected(tube: 1), .selected(tube: 0, count: 1),
                                                       .poured(from: 0, to: 2, count: 1, color: 1)])
    }

    // MARK: the contract

    func testContractConformance() {
        XCTAssertEqual(SortPuzzleModule.id, "sort-puzzle")
        XCTAssertEqual(SortPuzzleModule.contractVersion, PuzzleContract.version)
        let c = SortPuzzleModule.capabilities
        XCTAssertEqual(c.failRules, [.custom("stuck")])
        XCTAssertEqual(c.inputs, [.select2, .drag])
        XCTAssertEqual(c.boosters.map(\.id), [SortPuzzleModule.undo, SortPuzzleModule.extraTube])
        XCTAssertEqual(c.booster(SortPuzzleModule.undo)?.effect, .puzzleAction("undo"))
        XCTAssertEqual(c.hud, [.progress])
        XCTAssertFalse(c.zoomable)
        XCTAssertTrue(c.multiStageSessions)

        let l = SortGenerator.level(1, rules: SortRules())
        let st = SortPuzzleModule.stage(l)
        XCTAssertNil(st.timerSeconds)
        XCTAssertNil(st.hearts)
        XCTAssertEqual(st.level, 1)
        XCTAssertEqual(st.content as? SortLevel, l)

        let s: any PuzzleSession = session([l])
        XCTAssertNil(s.hearts)
        XCTAssertEqual(s.clock.limit, 0)
        XCTAssertEqual(Self.metas(s.start()), [.stageLoaded(stage: 0, of: 1, level: 1)])
        XCTAssertTrue(s.start().isEmpty, "start once")
        XCTAssertEqual(s.phase, .intro(stage: 0))
        XCTAssertNil(s.hint(), "no hint during the intro")
        XCTAssertEqual(Self.metas(s.ack(.introFinished)),
                       [.timerArmed(stage: 0, seconds: 0), .goalProgress([GoalState(id: "sorted", current: 0, target: 3)])])
        XCTAssertTrue(s.ack(.introFinished).isEmpty)
        XCTAssertNotNil(s.hint())
        s.hold(.popup)
        XCTAssertTrue(s.tick(1_000).isEmpty, "no clock rule: time changes nothing")
        s.release(.popup)
        XCTAssertTrue(s.tick(1_000).isEmpty)
        XCTAssertFalse(s.clock.isRunning)
        XCTAssertFalse(s.clock.isExpired && s.clock.started, "the idle clock never expires")
        XCTAssertTrue(s.input(.swap(PuzzleTarget(0), PuzzleTarget(1)), at: 1).isEmpty)
        XCTAssertTrue(s.input(.custom(id: "x", targets: []), at: 1).isEmpty)
        XCTAssertTrue(s.ack(.contact(Beat())).isEmpty)
        XCTAssertTrue(s.ack(.beat(Beat())).isEmpty)
        XCTAssertTrue(s.ack(.boardCleared).isEmpty)
        XCTAssertTrue(s.ack(.stageTransitionDone).isEmpty, "not in a stage clear")

        // a completed tube reports progress
        let two = SortLevel(level: 3, tag: .hard, capacity: 2, colors: 2, tubes: [[0, 1], [0, 1], []])
        let t = session([two], attempt: 2)
        ready(t)
        var out: [SessionOutput] = []
        for pick in [0, 2, 1, 2, 1, 0] { out += t.input(.select(PuzzleTarget(pick)), at: 1) }
        XCTAssertTrue(Self.metas(out).contains(.goalProgress([GoalState(id: "sorted", current: 1, target: 2)])), "\(out)")
        XCTAssertTrue(SessionOutput.sortEvents(out).contains(.tubeCompleted(tube: 2, color: 1)))
        guard case .won(let r)? = Self.metas(out).last else { return XCTFail("won: \(out)") }
        XCTAssertFalse(r.firstTry, "attempt 2")
        XCTAssertEqual(r.tag, .hard)
        XCTAssertEqual(r.reward, MetaRules().rewards.hard)
        XCTAssertEqual(r.timeLeft, 0)
        XCTAssertEqual(r.heartsLeft, 0)
    }

    func testWarmUpWinIsLevelOnesWin() {
        let r = SortPuzzleModule.warmUpWin(meta: MetaRules(), rules: SortRules())
        XCTAssertEqual(r?.levels, [1])
        XCTAssertEqual(r?.bumps, 0)
    }

    struct Beat: PuzzleBeat {}
}
