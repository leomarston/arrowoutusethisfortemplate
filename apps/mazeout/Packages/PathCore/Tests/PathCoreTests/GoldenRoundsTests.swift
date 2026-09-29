import XCTest
import Foundation
@testable import PathCore

/// §4.17 GoldenRoundsTests (C2): the golden test from REAL PLAY. Every arrow the phone bot tapped on the owner's phone
/// (research/bot/log.jsonl, result == "tapped", L32–L61; 1697 taps, no heart lost to a bot tap: research/levels.md) must be
/// FREE in our rules at the moment it was tapped: the bot planned each round from one screenshot and tapped its units in
/// dependency order, so each tap is checked on the state after every earlier tap (for the old one-batch rounds of L32 this
/// is the round-start state). The fixture (Tests/tools/golden_rounds.py) maps the log onto the completed recorded levels
/// (Tests/tools/c2_levels.py) and records what each run's first shot shows.
///
/// Replay rules (evidence, not rules, decide the state):
/// - a run starts FRESH at the level's first run, after a run that ended on a popup (guard_stop: the level ended), or when
///   its first shot shows an arrow the chain already removed; otherwise it CONTINUES the previous run;
/// - arrows live in the replay but absent from the run's first shot, and never tapped by the bot in that run, were removed
///   by unlogged hand taps (levels.md: L35 pipe arrows, L47 / L52 probes, L50 the 10th clear): each must be free too
///   (checked, in any order that works);
/// - doors a key is flying to burst before the next round (the bot re-read the board ≥ 0.45 s later, and never planned
///   through door cells).
final class GoldenRoundsTests: XCTestCase {

    struct GFile: Decodable { let levels: [GLevel]; let totals: [String: Int] }
    struct GLevel: Decodable { let level: Int; let runs: [GRun] }
    struct GRun: Decodable {
        let index: Int; let rows: [Int]; let shotRun: String; let ended: String; let endedWhy: String; let startUnknown: String
        let observed: GObs?; let taps: [GTap]; let unmapped: [GUnmapped]
    }
    struct GObs: Decodable { let round: Int; let file: String; let arrows: [Int]; let unmatched: Int }
    struct GTap: Decodable { let row: Int; let round: Int; let t: Double; let arrow: Int; let unit: Int }
    struct GUnmapped: Decodable { let row: Int; let round: Int; let cells: [[Int]]; let why: String }

    struct Outcome {
        var checked = 0, prelude = 0, fresh = 0, continued = 0, unmappedArtefacts = 0, unverifiable = 0
        var mismatches: [String] = []
        var drift: [String] = []
        var lines: [String] = []
    }

    /// Removes a unit the replay cannot resolve as an exit (diagnostics only: the test has already failed).
    func forceExit(_ b: BoardState, _ id: ArrowID) {
        guard let i = b.index[id] else { return }
        for m in b.unitIndices(i) where b.alive[m] { b.vacate(m); b.alive[m] = false; b.aliveCount -= 1 }
    }

    func describe(_ r: TapResolution) -> String {
        switch r {
        case .exit(let p): return "exit unit \(p.unit.map(\.raw))"
        case .bump(let p): return "BUMP into \(p.blocker) at \(p.contactPoint) after \(p.gapCells) empty cell(s)"
        case .ignored(let why): return "ignored (\(why.rawValue))"
        }
    }

    func replay(_ gl: GLevel, _ level: LevelSpec) -> Outcome {
        var o = Outcome()
        var board: BoardState?
        var previous: GRun?
        for run in gl.runs {
            // a run whose start state no evidence shows: its taps are unverifiable (never checked against a guess);
            // the next run is judged on its own evidence
            if !run.startUnknown.isEmpty {
                o.unverifiable += run.taps.count + run.unmapped.count
                o.lines.append("  run \(run.index): \(run.taps.count) taps UNVERIFIABLE — \(run.startUnknown)")
                board = nil
                previous = run
                continue
            }
            // fresh or continue
            var why = ""
            if board == nil { why = previous == nil ? "first run" : "after an unverifiable run" }
            else if previous?.ended == "guard_stop" { why = "the previous run ended on a popup (\(previous!.endedWhy))" }
            else if let obs = run.observed, let b = board,
                    let back = obs.arrows.map(ArrowID.init).first(where: { !b.isAlive($0) }) {
                why = "its first shot shows arrow \(back.raw), which the chain removed"
            }
            if !why.isEmpty { board = BoardState(level: level); o.fresh += 1 } else { o.continued += 1 }
            let b = board!
            b.burstTargetedDoors()
            o.lines.append("  run \(run.index) \(run.shotRun.isEmpty ? "-" : run.shotRun): " + (why.isEmpty ? "continues" : "fresh (\(why))")
                           + ", \(run.taps.count) taps, ended \(run.ended.isEmpty ? "-" : run.ended)")
            // unlogged removals before the run
            if let obs = run.observed {
                let seen = Set(obs.arrows.map(ArrowID.init))
                let tappedLater = Set(run.taps.map { ArrowID($0.arrow) })
                var missing = b.live.filter { !seen.contains($0) && !tappedLater.contains($0) }
                var progress = true
                while progress && !missing.isEmpty {
                    progress = false
                    for a in missing where b.isLive(a) && b.isFree(a) {
                        let r = b.resolve(tap: a)
                        b.commit(r)
                        b.burstTargetedDoors()
                        o.prelude += 1
                        progress = true
                        o.lines.append("    before the run (absent from \(obs.file)): arrow \(a.raw) free → removed")
                    }
                    missing = missing.filter { b.isLive($0) }
                }
                for a in missing {
                    o.mismatches.append("L\(gl.level) run \(run.index): arrow \(a.raw) is absent from \(obs.file) (removed by hand) "
                                        + "but is not free in our rules: \(describe(b.resolve(tap: a)))")
                    forceExit(b, a)
                }
                for a in seen where b.isAlive(a) && !b.isLive(a) {
                    o.drift.append("L\(gl.level) run \(run.index): \(obs.file) shows arrow \(a.raw), still hidden in the replay")
                }
            }
            // the bot's taps, round by round
            var round = -1
            for tap in run.taps {
                if tap.round != round { round = tap.round; b.burstTargetedDoors() }
                let id = ArrowID(tap.arrow)
                let r = b.resolve(tap: id)
                o.checked += 1
                switch r {
                case .exit(let plan) where plan.unit.count == tap.unit:
                    b.commit(r)
                case .exit(let plan):
                    o.mismatches.append("L\(gl.level) run \(run.index) round \(tap.round) log row \(tap.row): arrow \(tap.arrow) "
                                        + "left as a unit of \(plan.unit.count), the bot tapped a unit of \(tap.unit)")
                    b.commit(r)
                default:
                    o.mismatches.append("L\(gl.level) run \(run.index) round \(tap.round) log row \(tap.row): arrow \(tap.arrow) "
                                        + "was tapped by the bot but our rules say \(describe(r))")
                    forceExit(b, id)
                }
            }
            for u in run.unmapped {
                if u.cells.count < 2 { o.unmappedArtefacts += 1 } else {
                    o.mismatches.append("L\(gl.level) run \(run.index) log row \(u.row): tap on cells \(u.cells) maps to no arrow (\(u.why))")
                }
                o.lines.append("    unmapped log row \(u.row): \(u.cells.count)-cell read \(u.cells) — \(u.why)")
            }
            previous = run
        }
        return o
    }

    func testEveryBotTapIsFreeInOurRules() throws {
        let file = try JSONDecoder().decode(GFile.self, from: C2Fixtures.data(C2Fixtures.fixture("c2_golden_rounds.json")))
        let levels = try C2Fixtures.completed()
        XCTAssertEqual(file.levels.map(\.level), Array(32...61))
        XCTAssertEqual(file.totals["taps"], 1697, "every tapped row of the log is in the fixture")
        var total = Outcome()
        var report = ["GoldenRoundsTests — research/bot/log.jsonl replayed on Fixtures/c2_recorded_levels.json", ""]
        for gl in file.levels {
            let lv = try XCTUnwrap(levels[gl.level])
            let o = replay(gl, lv)
            report.append("L\(gl.level): \(o.checked) bot taps checked, \(o.prelude) hand removals checked, "
                          + "\(o.mismatches.count) mismatches")
            report += o.lines
            report += o.mismatches.map { "    MISMATCH " + $0 }
            report += o.drift.map { "    drift " + $0 }
            total.checked += o.checked; total.prelude += o.prelude; total.fresh += o.fresh; total.continued += o.continued
            total.unmappedArtefacts += o.unmappedArtefacts; total.unverifiable += o.unverifiable
            total.mismatches += o.mismatches; total.drift += o.drift
        }
        report.insert("TOTAL: \(total.checked) bot taps + \(total.prelude) hand removals checked; \(total.mismatches.count) mismatches; "
                      + "\(total.drift.count) drift; \(total.unmappedArtefacts) unmapped 1-cell reader artefacts; "
                      + "\(total.unverifiable) taps unverifiable (start state unknown); "
                      + "runs \(total.fresh) fresh / \(total.continued) continued", at: 1)
        let text = report.joined(separator: "\n")
        C2Fixtures.evidence("golden-rounds.txt", text)
        if !total.mismatches.isEmpty || !total.drift.isEmpty { print(text) }
        XCTAssertEqual(total.mismatches, [], "golden mismatches (the list above)")
        XCTAssertEqual(total.drift, [])
        XCTAssertEqual(total.checked + total.unmappedArtefacts + total.unverifiable, 1697)
        XCTAssertEqual(total.unverifiable, 9, "only L32 attempt 1 (hand play before the handover) is unverifiable")
        XCTAssertLessThanOrEqual(total.unmappedArtefacts, 2)
    }
}
