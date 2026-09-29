import Foundation
import XCTest
@testable import ArrowOut

/// VERIFY V1 (SPEC-architecture §3.3, §6.11, §12.2 V1 `StringsCoverageTests`; SPEC.md §5.24; memories
/// localizedstringkey-not-string, reordered-args-need-positional, strings-escape-decode).
///  1. Every English literal the UI hands to a text callee (the `callees` + `labelled` lists of tools/strings/sources.json,
///     the same scan as coverage.py) in App/**/*.swift and art/ui/code/*.swift has a row in strings.tsv + requests/*.tsv.
///  2. Every merged row is in the BUILT app's catalogue: en.lproj gives the English text and tr.lproj the Turkish text of the
///     row (a stale Localizable.xcstrings — requests not merged by tools/strings/build.py — fails here).
///  3. Argument ORDER: every Turkish value prints the same arguments with the same types as the English key, and a
///     translation with 2+ arguments spells the positions (%1$@) so a reorder can never print the wrong value.
///  4. The bundled data's copy keys (tutorials captions, unlock titles/cards, session labels) resolve in both languages.
///  5. Honesty (SPEC.md §5.24): no user-facing string in either language says "simulat"/"simüle"/"bot "/"online".
final class StringsCoverageTests: XCTestCase {

    private var merged: [V1StringRow] = []

    override func setUpWithError() throws {
        let (rows, problems) = try V1Strings.merged()
        XCTAssertEqual(problems, [], "the strings TSVs are well-formed and request rows agree")
        merged = rows
        XCTAssertGreaterThan(merged.count, 150, "strings.tsv + requests/*.tsv carry the game's copy")
    }

    // MARK: 1. code literals

    /// coverage.py `swift_literal_to_key`: escapes decoded, every interpolation `\(…)` → one placeholder.
    static func key(ofSwiftLiteral lit: String) -> String {
        var out = ""
        var i = lit.startIndex
        while i < lit.endIndex {
            let ch = lit[i]
            let n = lit.index(after: i)
            if ch == "\\", n < lit.endIndex {
                let esc = lit[n]
                if esc == "(" {
                    var depth = 1
                    var j = lit.index(after: n)
                    while j < lit.endIndex, depth > 0 {
                        if lit[j] == "(" { depth += 1 } else if lit[j] == ")" { depth -= 1 }
                        j = lit.index(after: j)
                    }
                    out.append("\u{0}")
                    i = j
                    continue
                }
                let map: [Character: Character] = ["n": "\n", "t": "\t", "\"": "\"", "\\": "\\", "'": "'"]
                out.append(map[esc] ?? esc)
                i = lit.index(after: n)
                continue
            }
            out.append(ch)
            i = n
        }
        return out
    }

    /// Canonical form for matching a literal against a TSV key: every specifier / `{name}` / interpolation → "\0".
    static func canon(_ s: String) -> String {
        var t = s.replacingOccurrences(of: #"\{\w+\}"#, with: "\u{0}", options: .regularExpression)
        let ns = t as NSString
        t = V1Format.re.stringByReplacingMatches(in: t, range: NSRange(location: 0, length: ns.length), withTemplate: "\u{0}")
        return t
    }

    func testEveryUILiteralHasARow() throws {
        let cfgData = try Data(contentsOf: V1Repo.url("tools/strings/sources.json"))
        let cfg = try XCTUnwrap(JSONSerialization.jsonObject(with: cfgData) as? [String: Any])
        let callees = cfg["callees"] as? [String] ?? ["Text", "Button", "Label", "Toggle", "LocalizedStringKey"]
        let lab = cfg["labelled"] as? [String: Any] ?? [:]
        let labels = lab["labels"] as? [String] ?? []
        let labDirs = (lab["dirs"] as? [String] ?? []).map { V1Repo.url($0).path + "/" }
        let labSkip = (lab["skip_files"] as? [String] ?? []).compactMap { try? NSRegularExpression(pattern: $0) }

        let names = callees.map(NSRegularExpression.escapedPattern(for:)).joined(separator: "|")
        let litRE = try NSRegularExpression(pattern:
            #"(?:\b(?:"# + names + #")\s*\(\s*(?:(?:text|marked|title|label|key|resource)\s*:\s*)?|String\s*\(\s*localized\s*:\s*|LocalizedStringResource\s*\(\s*)"((?:[^"\\\n]|\\.)*)""#)
        let labRE = labels.isEmpty ? nil : try NSRegularExpression(pattern:
            #"\b(?:"# + labels.map(NSRegularExpression.escapedPattern(for:)).joined(separator: "|") + #")\s*:\s*"((?:[^"\\\n]|\\.)*)""#)
        let identRE = try NSRegularExpression(pattern: #"^[a-z][A-Za-z0-9_]*(?:[.:/-][A-Za-z0-9_\\()]+)*$"#)
        let verbatimRE = try NSRegularExpression(pattern: #"verbatim:\s*"(?:[^"\\]|\\.)*""#)

        let keys = Set(merged.map { Self.canon($0.en) })
        var scanned = 0
        var missing: [String] = []
        let files = V1Repo.files("App", extensions: ["swift"]) + V1Repo.files("art/ui/code", extensions: ["swift"])
        XCTAssertGreaterThan(files.count, 100)
        for f in files {
            let path = f.path
            let useLab = labRE != nil && labDirs.contains { path.hasPrefix($0) }
                && !labSkip.contains { $0.firstMatch(in: f.lastPathComponent, range: NSRange(location: 0, length: (f.lastPathComponent as NSString).length)) != nil }
            let text = try String(contentsOf: f, encoding: .utf8)
            for (no, raw) in text.components(separatedBy: "\n").enumerated() {
                if raw.trimmingCharacters(in: .whitespaces).hasPrefix("//") { continue }
                var line = raw
                if line.contains("verbatim:") {
                    line = verbatimRE.stringByReplacingMatches(in: line, range: NSRange(location: 0, length: (line as NSString).length), withTemplate: "")
                }
                let ns = line as NSString
                var hits = litRE.matches(in: line, range: NSRange(location: 0, length: ns.length)).map { ns.substring(with: $0.range(at: 1)) }
                if useLab, let labRE, !line.contains("Log."), !line.contains("accessibilityIdentifier") {
                    hits += labRE.matches(in: line, range: NSRange(location: 0, length: ns.length)).map { ns.substring(with: $0.range(at: 1)) }
                        .filter { identRE.firstMatch(in: $0, range: NSRange(location: 0, length: ($0 as NSString).length)) == nil }
                }
                for lit in hits {
                    let key = Self.key(ofSwiftLiteral: lit)
                    guard key.replacingOccurrences(of: "\u{0}", with: "").rangeOfCharacter(from: .letters) != nil else { continue }
                    scanned += 1
                    if !keys.contains(Self.canon(key)) {
                        missing.append("\(V1Repo.relative(f)):\(no + 1) \(key.replacingOccurrences(of: "\u{0}", with: "%").debugDescription)")
                    }
                }
            }
        }
        v1Attach("code-literals", "scanned \(scanned) literals in \(files.count) files; missing \(missing.count)\n" + missing.joined(separator: "\n"))
        XCTAssertGreaterThan(scanned, 150, "the scan found the UI's copy")
        XCTAssertEqual(missing, [], "English literals with no strings.tsv / requests row (they would ship untranslated)")
    }

    // MARK: 2. the built catalogue

    func testEveryRowIsInTheBuiltCatalogueInBothLanguages() throws {
        let en = try XCTUnwrap(V1Bundle.lproj("en"), "en.lproj in the app")
        let tr = try XCTUnwrap(V1Bundle.lproj("tr"), "tr.lproj in the app")
        let sentinel = "\u{1}MISSING\u{1}"
        var missingTR: [String] = [], wrongTR: [String] = [], wrongEN: [String] = []
        for r in merged {
            let e = en.localizedString(forKey: r.en, value: sentinel, table: nil)
            // FIX-2 B (B1b-r3): an identifier key (keys.tsv) ships its declared English text; every other key IS its English
            let english = V1Strings.english(r.en)
            if e == sentinel || V1Format.canonical(e) != V1Format.canonical(english) { wrongEN.append("\(r.file):\(r.line) \(r.en.debugDescription) → \(e.debugDescription)") }
            let t = tr.localizedString(forKey: r.en, value: sentinel, table: nil)
            if t == sentinel { missingTR.append("\(r.file):\(r.line) \(r.en.debugDescription)"); continue }
            if V1Format.canonical(t) != V1Format.canonical(r.tr) {
                wrongTR.append("\(r.file):\(r.line) \(r.en.debugDescription): bundle \(t.debugDescription) ≠ tsv \(r.tr.debugDescription)")
            }
        }
        v1Attach("catalogue", "rows \(merged.count)\nmissing TR \(missingTR.count):\n\(missingTR.joined(separator: "\n"))\n"
                 + "wrong TR \(wrongTR.count):\n\(wrongTR.joined(separator: "\n"))\nwrong EN \(wrongEN.count):\n\(wrongEN.joined(separator: "\n"))")
        XCTAssertEqual(missingTR, [], "rows absent from the built catalogue (Localizable.xcstrings not regenerated by tools/strings/build.py?)")
        XCTAssertEqual(wrongTR, [], "the built TR value differs from the TSV")
        XCTAssertEqual(wrongEN, [], "the built EN value differs from its key (or from keys.tsv's English for an identifier key)")
    }

    // MARK: 3. argument order

    func testArgumentTypesAndOrderAgreeInBothLanguages() throws {
        let tr = try XCTUnwrap(V1Bundle.lproj("tr"))
        var bad: [String] = []
        var withArgs = 0
        for r in merged {
            guard let te = V1Format.resolvedTypes(r.en) else { bad.append("en \(r.en.debugDescription): malformed specifiers"); continue }
            if te.isEmpty { continue }
            withArgs += 1
            for (name, value) in [("tsv tr", r.tr), ("bundle tr", tr.localizedString(forKey: r.en, value: r.tr, table: nil))] {
                guard let tt = V1Format.resolvedTypes(value) else { bad.append("\(name) \(value.debugDescription): malformed specifiers"); continue }
                if tt != te { bad.append("\(r.file):\(r.line) \(name): types \(tt) ≠ en \(te) (\(r.en.debugDescription) / \(value.debugDescription))") }
                let a = V1Format.args(value)
                // positions stated once 2+ arguments exist in the shipped value, and never mixed
                if name == "bundle tr", a.count >= 2, a.contains(where: { $0.position == nil }) {
                    bad.append("\(r.file):\(r.line) bundle tr \(value.debugDescription): 2+ arguments without positions")
                }
                // a plain (non-positional) value must keep en's order (it can only print them in order)
                if a.allSatisfy({ $0.position == nil }), a.map(\.type) != te {
                    bad.append("\(r.file):\(r.line) \(name) reorders arguments without positions")
                }
            }
        }
        v1Attach("argument-order", "rows with arguments: \(withArgs)\n" + bad.joined(separator: "\n"))
        XCTAssertGreaterThan(withArgs, 10)
        XCTAssertEqual(bad, [])
    }

    /// The reorder guard proves itself on a known reordered string: TR "Sürüm %1$@ · Seviye %2$lld" prints its arguments
    /// where English does, and a hand-made plain-order swap is caught.
    func testArgumentOrderGuardCatchesASwap() {
        XCTAssertEqual(V1Format.resolvedTypes("Sürüm %1$@ · Seviye %2$lld"), ["@", "lld"])
        XCTAssertEqual(V1Format.resolvedTypes("Seviye %2$lld · Sürüm %1$@"), ["@", "lld"], "a positional reorder keeps the types")
        XCTAssertEqual(V1Format.resolvedTypes("Seviye %lld · Sürüm %@"), ["lld", "@"], "a plain swap changes the types → caught")
        XCTAssertNil(V1Format.resolvedTypes("%1$@ %lld"), "mixed specifiers are refused")
        XCTAssertEqual(V1Format.canonical("%lld:%02lld"), V1Format.canonical("%1$lld:%2$02lld"))
        XCTAssertNotEqual(V1Format.canonical("%lld:%02lld"), V1Format.canonical("%2$lld:%1$02lld"))
    }

    // MARK: 4. data copy

    func testBundledDataCopyResolvesInBothLanguages() throws {
        let en = try XCTUnwrap(V1Bundle.lproj("en")), tr = try XCTUnwrap(V1Bundle.lproj("tr"))
        let folder = try XCTUnwrap(Bundle.main.resourceURL).appendingPathComponent("Levels")
        var keys: [String] = []
        func walk(_ o: Any, _ wanted: Set<String>) {
            if let d = o as? [String: Any] {
                for (k, v) in d { if wanted.contains(k), let s = v as? String { keys.append(s) } else { walk(v, wanted) } }
            } else if let a = o as? [Any] { a.forEach { walk($0, wanted) } }
        }
        for (file, wanted) in [("tutorials.json", ["caption"]), ("unlocks.json", ["title", "card"]), ("sessions.json", ["hud_label", "panel_label"])] {
            let obj = try JSONSerialization.jsonObject(with: Data(contentsOf: folder.appendingPathComponent(file)))
            walk(obj, Set(wanted))
        }
        XCTAssertGreaterThanOrEqual(keys.count, 15, "tutorial caption + 6 unlock titles and cards + the session labels")
        let sentinel = "\u{1}MISSING\u{1}"
        let rowsByKey = Dictionary(merged.map { ($0.en, $0) }, uniquingKeysWith: { a, _ in a })
        for k in keys {
            XCTAssertNotEqual(en.localizedString(forKey: k, value: sentinel, table: nil), sentinel, "EN \(k)")
            let t = tr.localizedString(forKey: k, value: sentinel, table: nil)
            XCTAssertNotEqual(t, sentinel, "TR \(k)")
            XCTAssertNotEqual(t, k, "TR \(k) is translated")
            XCTAssertEqual(t, rowsByKey[k]?.tr, "TR \(k) = its row")
        }
    }

    // MARK: 5. honesty (SPEC.md §5.24)

    func testNoUserFacingStringMentionsASimulationBotsOrOnline() throws {
        let banned = ["simulat", "simüle", "bot ", "online", "çevrimiçi"]
        var hits: [String] = []
        for lang in ["en", "tr"] {
            let url = try XCTUnwrap(Bundle.main.url(forResource: "Localizable", withExtension: "strings", subdirectory: nil, localization: lang))
            let dict = try XCTUnwrap(NSDictionary(contentsOf: url) as? [String: String], "\(lang) Localizable.strings")
            XCTAssertGreaterThan(dict.count, 150)
            for (k, v) in dict {
                for b in banned where k.lowercased().contains(b) || v.lowercased().contains(b) { hits.append("\(lang): \(k.debugDescription) = \(v.debugDescription) [\(b)]") }
            }
        }
        for r in merged {
            for b in banned where r.en.lowercased().contains(b) || r.tr.lowercased().contains(b) { hits.append("\(r.file):\(r.line) [\(b)]") }
        }
        XCTAssertEqual(hits, [], "user-facing copy never mentions a simulation, bots or being online")
    }
}
