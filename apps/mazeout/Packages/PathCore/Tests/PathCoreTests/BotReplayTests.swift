import XCTest
import Foundation
@testable import GameCore
@testable import ArrowEscape

/// The phone bot's WINNING taps replayed under PathCore's rules (content recast 2026-09-25; C4b). The session-2 bot
/// (research/bot/go2.py + corners.py) tapped only arrows it read as free and won L069 (three pipes under doors) and every
/// corner level of v552 (L073, L076, L079, L080, L082: 18 corners) with 3/3 hearts: on the phone every one of its taps
/// was an exit, so under the right rules every logged tap must EXIT. design/tools/replay_log.py checks that under
/// arrowcore; this is the same replay, from the same pinned inputs (Fixtures/c4b_bot_replay.json, written by
/// Tests/tools/c4b_bot_replay.py from research/bot/log.jsonl), under the GAME's rules (C2's BoardState: doors burst
/// before the next tap, as the solver does) and under C4's content mirror (RefBoard).
///
/// Mapping (replay_log.py): a logged unit's cells are in that round's read frame; the one integer shift (dx −3…3,
/// dy −20…20, the first best) that matches the most logged units to arrows maps them all; start-visible arrows the log
/// never taps (tapped by hand before the bot started) are removed first while they are free; logged units matching no
/// arrow (the bot's mid-exit misreads; its tap still hit an arrow) are counted, not replayed.
final class BotReplayTests: XCTestCase {

    struct Tap { var round: Int?; var t: Double; var cells: [Cell] }

    func testPhoneBotWinningTapsExitUnderTheGameRules() throws {
        let fx = try C4Fixtures.json("c4b_bot_replay.json")
        let content = try String(contentsOf: C4Fixtures.levelsJSON, encoding: .utf8)
        XCTAssertEqual(fx["content_sha256"]?.stringValue, C4Fixtures.sha256(content), "the pin is of another levels.json")
        let levels = try XCTUnwrap(fx["levels"]?.arrayValue)
        XCTAssertEqual(levels.compactMap { $0["level"]?.intValue }, [69, 73, 76, 79, 80, 82])
        var lines = ["The phone bot's winning taps (research/bot/log.jsonl via Fixtures/c4b_bot_replay.json) replayed under PathCore:",
                     "C2's BoardState (the game) and C4's RefBoard (the arrowcore mirror); every mapped tap must exit.", ""]
        var cornerTurns = 0, bumps = 0
        for lv in levels {
            let n = lv["level"]!.intValue!
            // PUBLISH B0 (level re-order): n is the LOG's (v552's) number; the board ships at the fixture's `slot`, which
            // must be where the board's own provenance puts it (the same board, never the one now numbered n)
            let slot = try XCTUnwrap(lv["slot"]?.intValue, "L\(n): the fixture names the slot the board ships at")
            XCTAssertEqual(slot, C4Fixtures.slot(research: n), "L\(n): the fixture's slot is not the board's")
            let level = C4Fixtures.level(slot)
            let py = lv["python"]!
            let taps = lv["taps"]!.arrayValue!.map { r in
                Tap(round: r["round"]?.intValue, t: r["t"]!.doubleValue!,
                    cells: r["cells"]!.arrayValue!.map { Cell($0.arrayValue![0].intValue!, $0.arrayValue![1].intValue!) })
            }
            XCTAssertEqual(level.obstacles.filter { $0.kind == .corner }.count, lv["corners"]!.intValue!, "L\(n)")
            // the mapping
            var known: [Set<Cell>: ArrowID] = [:]
            for a in level.arrows { known[Set(a.cells)] = a.id }
            var shift = (0, 0), bestCount = -1
            for dx in -3...3 {
                for dy in -20...20 {
                    let k = taps.filter { t in known[Set(t.cells.map { Cell($0.c + dx, $0.r + dy) })] != nil }.count
                    if k > bestCount { shift = (dx, dy); bestCount = k }
                }
            }
            XCTAssertEqual([shift.0, shift.1], py["shift"]!.arrayValue!.map { $0.intValue! }, "L\(n) shift")
            func arrow(_ t: Tap) -> ArrowID? { known[Set(t.cells.map { Cell($0.c + shift.0, $0.r + shift.1) })] }
            // the units the log taps (tape bundles whole, arrowcore's unit) and the arrows tapped by hand first
            let S = RefStatic(level)
            let rb0 = RefBoard(S)
            var logged = Set<ArrowID>()
            for t in taps { if let id = arrow(t), let i = S.ids.firstIndex(of: id) { for m in rb0.unit(i) { logged.insert(S.ids[m]) } } }
            let hand = level.arrows.filter { !logged.contains($0.id) && $0.hiddenBy == nil }.map(\.id)
            XCTAssertEqual(hand.map(\.raw), py["hand"]!.arrayValue!.map { $0.intValue! }, "L\(n) hand taps")
            // the order: rounds (round, t // 30) by their first tap, log order inside
            var groupOf: [String: Int] = [:]
            var groups: [(first: Double, taps: [Tap])] = []
            for t in taps {
                let key = "\(t.round.map(String.init) ?? "None")|\(Int(t.t) / 30)"
                if let g = groupOf[key] { groups[g].taps.append(t); groups[g].first = min(groups[g].first, t.t) } else {
                    groupOf[key] = groups.count
                    groups.append((t.t, [t]))
                }
            }
            let ordered = groups.enumerated().sorted { ($0.element.first, $0.offset) < ($1.element.first, $1.offset) }.flatMap(\.element.taps)
            // the game's rules
            let b = BoardState(level: level)
            for id in hand {
                let r = b.resolve(tap: id)
                if case .exit = r { b.commit(r); _ = b.burstTargetedDoors() }
            }
            var exits = 0, unmatched = 0, problems: [String] = [], turns = 0, tubes = 0
            for t in ordered {
                guard let id = arrow(t) else { unmatched += 1; continue }
                let r = b.resolve(tap: id)
                guard case .exit(let plan) = r else { problems.append("round \(t.round ?? -1): arrow \(id.raw) -> \(r)"); continue }
                for p in plan.paths.values {
                    for s in p.segments {
                        if case .corner = s { turns += 1 }
                        if case .tube = s { tubes += 1 }
                    }
                }
                b.commit(r)
                _ = b.burstTargetedDoors()
                exits += 1
            }
            XCTAssertEqual(problems, [], "L\(n): logged winning taps that do not exit under the game's rules")
            XCTAssertEqual(exits, py["exits"]!.intValue!, "L\(n) exits")
            XCTAssertEqual(unmatched, py["unmatched"]!.intValue!, "L\(n) unmatched")
            XCTAssertEqual(b.remaining, py["left"]!.intValue!, "L\(n) arrows left")
            if b.remaining > 0 { XCTAssertTrue(Solver.greedy(from: b.copy()).solved, "L\(n): the rest can be cleared") }
            if n == 69 { XCTAssertGreaterThan(tubes, 0, "L69: the replay goes through the pipes") }
            else { XCTAssertGreaterThan(turns, 0, "L\(n): the replay turns at corners") }
            cornerTurns += turns
            bumps += problems.count
            // C4's content mirror (arrowcore)
            let rr = RefResolver(RefBoard(S))
            for id in hand {
                if case .exit(let u, let p) = rr.resolve(S.ids.firstIndex(of: id)!) { rr.commitExit(u, p); rr.openPendingDoors() }
            }
            var refExits = 0, refProblems = 0
            for t in ordered {
                guard let id = arrow(t), let i = S.ids.firstIndex(of: id) else { continue }
                guard case .exit(let u, let p) = rr.resolve(i) else { refProblems += 1; continue }
                rr.commitExit(u, p)
                rr.openPendingDoors()
                refExits += 1
            }
            XCTAssertEqual(refProblems, 0, "L\(n): content rules")
            XCTAssertEqual(refExits, exits, "L\(n): content rules")
            XCTAssertEqual(rr.b.aliveCount, b.remaining, "L\(n): content rules")
            lines.append("L\(n): \(taps.count) logged taps, shift (\(shift.0), \(shift.1)), removed by hand first \(hand.map(\.raw)); "
                         + "game rules: \(exits) exit, \(problems.count) bump, \(unmatched) misread, \(turns) corner turns, \(tubes) tube passages, "
                         + "\(b.remaining) left; content rules: \(refExits) exit, \(refProblems) bump")
        }
        lines.append("")
        lines.append("logged taps that do not exit: \(bumps) (must be 0); corner turns taken on the way: \(cornerTurns)")
        C4Fixtures.evidence("c4b-bot-replay.txt", lines.joined(separator: "\n"))
        XCTAssertGreaterThan(cornerTurns, 18)
    }
}
