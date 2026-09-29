import Foundation
import XCTest

// VERIFY V1 (SPEC-architecture §12.2 V1, §3.2 `Tests/AppTests/**`). Shared helpers of the AppTests suites: the repo root read
// through #filePath (hosted tests on the simulator can read the Mac's file system; ShellTests/SocialScreensTests do the same),
// the strings TSVs merged exactly as tools/strings/build.py merges them, printf specifier parsing, and the built app bundle.

enum V1Repo {
    /// apps/mazeout (this file is apps/mazeout/Tests/AppTests/V1Support.swift).
    static let root: URL = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
        .deletingLastPathComponent()

    static func url(_ relative: String) -> URL { root.appendingPathComponent(relative) }

    static func text(_ relative: String) throws -> String { try String(contentsOf: url(relative), encoding: .utf8) }

    /// Every file under `relative` (recursively) with one of `extensions`.
    static func files(_ relative: String, extensions: Set<String>) -> [URL] {
        guard let e = FileManager.default.enumerator(at: url(relative), includingPropertiesForKeys: nil) else { return [] }
        var out: [URL] = []
        for case let u as URL in e where extensions.contains(u.pathExtension) { out.append(u) }
        return out.sorted { $0.path < $1.path }
    }

    static func relative(_ u: URL) -> String {
        u.path.hasPrefix(root.path + "/") ? String(u.path.dropFirst(root.path.count + 1)) : u.path
    }
}

/// The app bundle the hosted tests run in (the Debug build of the scheme's test action).
enum V1Bundle {
    static var root: URL { Bundle.main.bundleURL }

    /// Every regular file of the .app, relative paths (folders recursed; code signature and frameworks included).
    static func allFiles() -> [String] {
        let base = root
        guard let e = FileManager.default.enumerator(at: base, includingPropertiesForKeys: [.isRegularFileKey]) else { return [] }
        var out: [String] = []
        for case let u as URL in e {
            if (try? u.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true {
                out.append(String(u.path.dropFirst(base.path.count + 1)))
            }
        }
        return out.sorted()
    }

    static func lproj(_ lang: String) -> Bundle? {
        Bundle.main.path(forResource: lang, ofType: "lproj").flatMap(Bundle.init(path:))
    }
}

/// One row of strings.tsv / requests/<role>.tsv (tools/strings/build.py `load`).
struct V1StringRow: Equatable {
    var file: String
    var line: Int
    var en: String
    var tr: String
}

enum V1Strings {
    static let tsv = "App/Resources/Strings/strings.tsv"
    static let requests = "App/Resources/Strings/requests"

    /// FIX-2 lane B (B1b-r3): App/Resources/Strings/keys.tsv — the identifier keys and the English text the catalogue ships for
    /// them (build.py `english`); every other key IS its English text.
    static let keyed: [String: String] = {
        guard let text = try? V1Repo.text("App/Resources/Strings/keys.tsv") else { return [:] }
        var out: [String: String] = [:]
        for line in text.components(separatedBy: "\n").dropFirst() where !line.isEmpty && !line.hasPrefix("#") {
            let c = line.components(separatedBy: "\t")
            if c.count == 3 { out[c[0]] = unescape(c[1]) }
        }
        return out
    }()

    /// The English text of a catalogue key.
    static func english(_ key: String) -> String { keyed[key] ?? key }

    /// build.py `unescape`: \n newline, \t tab, \\ backslash; nothing else is interpreted.
    static func unescape(_ cell: String) -> String {
        var out = ""
        var it = Array(cell)[...]
        while let c = it.first {
            it = it.dropFirst()
            if c == "\\", let n = it.first, "nt\\".contains(n) {
                out.append(n == "n" ? "\n" : n == "t" ? "\t" : "\\")
                it = it.dropFirst()
            } else {
                out.append(c)
            }
        }
        return out
    }

    /// One TSV file's rows (header checked; `#` comments and blank lines skipped). Malformed lines are returned as problems.
    static func load(_ relative: String) throws -> (rows: [V1StringRow], problems: [String]) {
        let lines = try V1Repo.text(relative).components(separatedBy: "\n")
        var rows: [V1StringRow] = [], problems: [String] = []
        guard lines.first?.components(separatedBy: "\t") == ["en", "tr", "context"] else {
            return ([], ["\(relative): the header is not en<TAB>tr<TAB>context"])
        }
        for (i, line) in lines.enumerated().dropFirst() {
            if line.trimmingCharacters(in: .whitespaces).isEmpty || line.hasPrefix("#") { continue }
            let cells = line.components(separatedBy: "\t")
            guard cells.count == 3 else { problems.append("\(relative):\(i + 1): \(cells.count) columns"); continue }
            rows.append(V1StringRow(file: relative, line: i + 1, en: unescape(cells[0]), tr: unescape(cells[1])))
        }
        return (rows, problems)
    }

    /// strings.tsv + every requests/*.tsv, merged as build.py `load_all` does: a strings.tsv row wins; two request rows with
    /// the same key must agree (a disagreement is a problem).
    static func merged() throws -> (rows: [V1StringRow], problems: [String]) {
        var (rows, problems) = try load(tsv)
        var byKey = Dictionary(rows.map { ($0.en, $0) }, uniquingKeysWith: { a, _ in a })
        let dir = V1Repo.url(requests)
        let names = (try FileManager.default.contentsOfDirectory(atPath: dir.path)).filter { $0.hasSuffix(".tsv") }.sorted()
        var requested: [String: V1StringRow] = [:]
        for name in names {
            let rel = requests + "/" + name
            if ((try? FileManager.default.attributesOfItem(atPath: V1Repo.url(rel).path)[.size] as? Int) ?? 0) == 0 { continue }
            let (rr, pp) = try load(rel)
            problems += pp
            for r in rr where byKey[r.en] == nil {
                if let prior = requested[r.en] {
                    if prior.tr != r.tr { problems.append("requests disagree on \(r.en.debugDescription): \(prior.file) vs \(r.file)") }
                    continue
                }
                requested[r.en] = r
            }
        }
        for k in requested.keys.sorted() { rows.append(requested[k]!); byKey[k] = requested[k] }
        return (rows, problems)
    }
}

/// printf specifiers Swift emits for interpolations (build.py SPEC_RE): %lld, %@, %d, %f, %.1f, %02lld … with an optional n$.
enum V1Format {
    static let re = try! NSRegularExpression(pattern: #"%(?:(\d+)\$)?(?:[-+ 0#]*\d*(?:\.\d+)?)(lld|ld|d|u|llu|@|f|lf|e|g|s|c)"#)

    struct Arg: Equatable { var position: Int?; var type: String }

    static func norm(_ t: String) -> String { ["ld": "lld", "d": "lld", "u": "lld", "llu": "lld", "lf": "f"][t] ?? t }

    /// Arguments in TEXT order.
    static func args(_ s: String) -> [Arg] {
        let t = s.replacingOccurrences(of: "%%", with: "")
        let ns = t as NSString
        return re.matches(in: t, range: NSRange(location: 0, length: ns.length)).map { m in
            let pos = m.range(at: 1).location == NSNotFound ? nil : Int(ns.substring(with: m.range(at: 1)))
            return Arg(position: pos, type: norm(ns.substring(with: m.range(at: 2))))
        }
    }

    /// Types in ARGUMENT order (positions resolved), or nil when the string mixes positional and plain specifiers, uses a
    /// position with two types, or skips a position.
    static func resolvedTypes(_ s: String) -> [String]? {
        let a = args(s)
        guard a.contains(where: { $0.position != nil }) else { return a.map(\.type) }
        guard a.allSatisfy({ $0.position != nil }) else { return nil }
        var by: [Int: String] = [:]
        for x in a {
            if let t = by[x.position!], t != x.type { return nil }
            by[x.position!] = x.type
        }
        guard by.keys.sorted() == Array(1...max(1, by.count)) else { return nil }
        return (1...by.count).map { by[$0]! }
    }

    /// The text with every specifier replaced by "%<argument index>" (positions resolved): two strings that print the same
    /// arguments in the same places compare equal whether or not one of them spells the positions.
    static func canonical(_ s: String) -> String {
        let ns = s as NSString
        var out = "", last = 0, next = 1
        for m in re.matches(in: s, range: NSRange(location: 0, length: ns.length)) {
            out += ns.substring(with: NSRange(location: last, length: m.range.location - last))
            let pos = m.range(at: 1).location == NSNotFound ? nil : Int(ns.substring(with: m.range(at: 1)))
            let whole = ns.substring(with: m.range)
            let flags = whole.replacingOccurrences(of: #"^%(\d+\$)?"#, with: "", options: .regularExpression)
            out += "%\(pos ?? next)$" + flags
            if pos == nil { next += 1 }
            last = m.range.location + m.range.length
        }
        return out + ns.substring(from: last)
    }
}

extension XCTestCase {
    /// Attaches a text report that stays in the result bundle (the evidence build/v1 archives).
    func v1Attach(_ name: String, _ text: String) {
        let a = XCTAttachment(string: text)
        a.name = name
        a.lifetime = .keepAlways
        add(a)
    }
}
