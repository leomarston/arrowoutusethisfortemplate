import Foundation
import PathCore

// Small helpers shared by the subcommands.

struct ToolError: Error, CustomStringConvertible {
    let description: String
    init(_ s: String) { description = s }
}

func readData(_ path: String) throws -> Data {
    do { return try Data(contentsOf: URL(fileURLWithPath: path)) } catch { throw ToolError("cannot read \(path): \(error)") }
}

func jsonObject(_ data: Data, _ what: String) throws -> Any {
    do { return try JSONSerialization.jsonObject(with: data) } catch { throw ToolError("\(what) is not JSON: \(error)") }
}

func writeData(_ data: Data, _ path: String) throws {
    let url = URL(fileURLWithPath: path)
    try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    try data.write(to: url, options: .atomic)
}

/// Pretty JSON for reports (sorted keys so two runs diff cleanly).
func reportJSON(_ obj: Any) throws -> Data {
    var d = try JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys, .prettyPrinted, .withoutEscapingSlashes])
    d.append(0x0A)
    return d
}

/// Command-line options: positional arguments plus `--key value` / `--flag`.
struct Args {
    var positional: [String] = []
    var options: [String: String] = [:]
    var flags: Set<String> = []

    init(_ argv: [String], flags known: Set<String> = []) {
        var i = 0
        while i < argv.count {
            let a = argv[i]
            if a.hasPrefix("--") {
                let k = String(a.dropFirst(2))
                if known.contains(k) || i + 1 >= argv.count || argv[i + 1].hasPrefix("--") {
                    flags.insert(k)
                } else {
                    options[k] = argv[i + 1]
                    i += 1
                }
            } else {
                positional.append(a)
            }
            i += 1
        }
    }

    func opt(_ k: String, _ d: String) -> String { options[k] ?? d }
}

func loadRules(_ path: String) throws -> (RulesTuning, [String]) {
    let data = try readData(path)
    let (rules, problems) = RulesTuning.load(json: data)
    return (rules, problems)
}

extension LevelSpec {
    /// Units at the start: every arrow, a tape bundle counted once.
    var unitCount: Int {
        let tapes = obstacles.filter { $0.kind == .tape }
        return arrows.count - tapes.reduce(0) { $0 + max(0, $1.arrows.count - 1) }
    }
}

func cellKey(_ c: Cell) -> String { "\(c.c),\(c.r)" }
func cellsKey(_ cs: [Cell]) -> String { cs.map(cellKey).joined(separator: " ") }

// MARK: board identity after the level re-order (PUBLISH B0)

/// PUBLISH item 12 (SPEC.md rulings 37e + 39 OD8; design/publish/level-reorder.md §9): after the level re-order a level
/// NUMBER names a slot, not a board. A board is named by its RESEARCH SLOT, read from its own provenance in design/levels.json
/// (design/tools/level_order.py `rslot`, ported): a phone board = the number in its capture (research/shots/NNN-L0nn-…,
/// research/bot/tmp/L0nn-…), a video board = the video's number (research/video-frames/V1|V2/L0nn-…), a V2 substitute /
/// designed stand-in = the phone slot its `_from` names ("the phone's L81"); a generated board (L106+) has none and never
/// moves. The shipped bundle carries no provenance (the publish form), so every research lookup reads design/levels.json.
func researchSlot(source: String?, capture: String?, from: String?) -> Int? {
    func first(_ pattern: String, _ s: String, group: Int) -> Int? {
        guard let rx = try? NSRegularExpression(pattern: pattern),
              let m = rx.firstMatch(in: s, range: NSRange(s.startIndex..., in: s)),
              let r = Range(m.range(at: group), in: s) else { return nil }
        return Int(s[r])
    }
    let cap = capture ?? "", frm = from ?? ""
    if frm.hasPrefix("V2-L") || frm.hasPrefix("designed stand-in") { return first(#"the phone's L0*(\d+)\b"#, frm, group: 1) }
    if source == "recorded" { return first(#"[/-]L0*(\d+)-"#, cap, group: 1) }
    if source == "video" { return first(#"/(V[12])/L0*(\d+)-"#, cap, group: 2) }
    return nil
}

/// research slot → the level it ships at, for every board of a levels.json (asserts no research slot is named twice).
func researchSlots(_ raw: [[String: Any]]) throws -> [Int: Int] {
    var out: [Int: Int] = [:]
    for r in raw {
        guard let n = r["level"] as? Int,
              let s = researchSlot(source: r["source"] as? String, capture: r["capture"] as? String, from: r["_from"] as? String) else { continue }
        if let prev = out[s] { throw ToolError("research slot \(s) named twice (L\(prev) and L\(n))") }
        out[s] = n
    }
    return out
}
