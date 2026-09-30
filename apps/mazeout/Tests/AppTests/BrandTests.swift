import Foundation
import XCTest
import PathCore
@testable import ArrowOut

/// VERIFY V1 (SPEC-architecture §6.11 `BrandTests`, §12.2 WP0 item 7 / V1; SPEC.md §2 "the copying line").
///  - The product name has ONE source: project.yml `PC_BRAND_NAME` → Info.plist `PCBrandName` / `CFBundleDisplayName` →
///    `Brand.name`; no Swift source, resource or catalogue value spells it (copy interpolates `Brand.name`), and the built
///    binary does not carry it as a literal.
///  - The original's names ("Maze", "MazeOut", "Arrow Jam", "Grand Games", "grandgames", "arrowjam") appear nowhere in the
///    built app — file names included. PUBLISH B2 (PLAN-P G4(c), stricter): there is NO exception any more. The social name
///    generator used to ship its blocklists and word lists as text (Social/*.txt + social_names.json, SOC1) and was exempt;
///    the shipped v2 bank (Social/social_names.json only, Tests/tools/soc_ship_names.py) stores those entries as hashes and
///    marks the unshowable tokens, so it carries none of the words; the test still proves no generated name shows them.
final class BrandTests: XCTestCase {
    /// The spec's list (§6.11), matched case-sensitively, plus the joined spellings matched case-insensitively.
    static let bannedExact = ["Maze", "MazeOut", "Arrow Jam", "Grand Games", "grandgames", "arrowjam"]
    static let bannedAnyCase = ["mazeout", "maze out", "arrowjam", "arrow jam", "grandgames", "grand games"]
    /// Files exempt from the scan: none (PUBLISH B2 — the name generator's data ships without the original's words).
    static let socialNameData: Set<String> = []

    private func brandFromProjectYML() throws -> String {
        let yml = try V1Repo.text("project.yml")
        let re = try NSRegularExpression(pattern: #"PC_BRAND_NAME:\s*"([^"]+)""#)
        let ns = yml as NSString
        let m = try XCTUnwrap(re.firstMatch(in: yml, range: NSRange(location: 0, length: ns.length)), "PC_BRAND_NAME in project.yml")
        return ns.substring(with: m.range(at: 1))
    }

    func testTheNameHasOneSource() throws {
        let brand = try brandFromProjectYML()
        XCTAssertEqual(brand, "Arrow Out", "the owner's product name (OWNER 02:33)")
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "PCBrandName") as? String, brand)
        XCTAssertEqual(Bundle.main.object(forInfoDictionaryKey: "CFBundleDisplayName") as? String, brand)
        XCTAssertEqual(Brand.name, brand)
        XCTAssertEqual(UIArt(rawValue: Brand.logoArtID), .logoMain, "the logo is the skin's logo slot")
        XCTAssertTrue(ArtStore.exists(.logoMain), "the logo is art, never text")
        // project.yml is the only file that spells it (sources, tools-generated code, the chrome, PathCore)
        var offenders: [String] = []
        let files = V1Repo.files("App", extensions: ["swift", "json", "tsv", "txt", "plist", "xcstrings", "storekit", "strings"])
            + V1Repo.files("art/ui/code", extensions: ["swift"]) + V1Repo.files("Packages/PathCore/Sources", extensions: ["swift"])
        let literal = try NSRegularExpression(pattern: #""(?:[^"\\\n]|\\.)*""#)
        for f in files {
            guard let text = try? String(contentsOf: f, encoding: .utf8) else { continue }
            // WP0 item 7: the exact spelling nowhere (comments included)
            if text.contains(brand) { offenders.append("\(V1Repo.relative(f)): \"\(brand)\""); continue }
            if f.pathExtension != "swift" {
                // data and copy files: any case (they ship)
                if text.range(of: brand, options: .caseInsensitive) != nil { offenders.append("\(V1Repo.relative(f)): any case") }
                continue
            }
            // Swift: any case inside a string literal (copy), comments stripped ("our ARROW OUT! logo" in a comment is fine)
            for line in text.components(separatedBy: "\n") {
                let code = line.components(separatedBy: "//").first ?? ""
                let ns = code as NSString
                for m in literal.matches(in: code, range: NSRange(location: 0, length: ns.length))
                where ns.substring(with: m.range).range(of: brand, options: .caseInsensitive) != nil {
                    offenders.append("\(V1Repo.relative(f)): \(ns.substring(with: m.range))")
                }
            }
        }
        XCTAssertEqual(offenders, [], "\"\(brand)\" spelled outside project.yml")
    }

    func testCopyThatNamesTheGameInterpolatesTheBrand() throws {
        let brand = try brandFromProjectYML()
        for lang in ["en", "tr"] {
            let url = try XCTUnwrap(Bundle.main.url(forResource: "Localizable", withExtension: "strings", subdirectory: nil, localization: lang))
            let dict = try XCTUnwrap(NSDictionary(contentsOf: url) as? [String: String])
            let spelled = dict.filter { $0.key.localizedCaseInsensitiveContains(brand) || $0.value.localizedCaseInsensitiveContains(brand) }
            XCTAssertEqual(spelled.count, 0, "\(lang): \(spelled)")
            // the Terms / Privacy / Support copy names the game through %@ (SPEC-gameplay §16.10)
            XCTAssertNotNil(dict["%@ is a puzzle game."], "\(lang): the Terms line takes Brand.name")
        }
        XCTAssertEqual(String(format: NSLocalizedString("%@ is a puzzle game.", comment: ""), Brand.name), "\(brand) is a puzzle game.")
    }

    func testNoFileNameCarriesTheOriginalsNames() {
        let files = V1Bundle.allFiles()
        XCTAssertGreaterThan(files.count, 300, "the whole .app is listed")
        let tokenMO = try! NSRegularExpression(pattern: #"(^|[^a-z])mo([^a-z]|$)"#)
        var bad: [String] = []
        for f in files {
            let name = f.lowercased()
            if ["maze", "grand", "arrowjam", "arrow jam"].contains(where: { name.contains($0) }) { bad.append(f) }
            let last = (name as NSString).lastPathComponent
            if tokenMO.firstMatch(in: last, range: NSRange(location: 0, length: (last as NSString).length)) != nil { bad.append(f) }
        }
        XCTAssertEqual(bad, [], "neutral file names (SPEC.md §2: never maze/mo/grand/arrowjam)")
        // the repo's own sources too (WP0 item 7: no file NAME contains them)
        var repoBad: [String] = []
        for dir in ["App", "Packages/PathCore/Sources", "Tests", "UITests", "art/ui/out", "art/ui/code"] {
            for f in V1Repo.files(dir, extensions: ["swift", "json", "png", "txt", "tsv", "plist", "xcstrings", "wav", "ttf"]) {
                let n = f.lastPathComponent.lowercased()
                if ["maze", "grand", "arrowjam"].contains(where: { n.contains($0) }) { repoBad.append(V1Repo.relative(f)) }
            }
        }
        XCTAssertEqual(repoBad, [])
    }

    /// Scans the built app's binaries and text resources for the original's names.
    func testTheBuiltAppNeverSaysTheOriginalsNames() throws {
        let brand = try brandFromProjectYML()
        var hits: [String] = []
        var allowed: [String] = []
        var scanned = 0
        for rel in V1Bundle.allFiles() {
            let ext = (rel as NSString).pathExtension.lowercased()
            let isBinary = rel == "ArrowOut" || rel == "ArrowOut.debug.dylib"
            guard isBinary || ["json", "txt", "tsv", "strings", "plist", "stringsdict"].contains(ext) else { continue }
            if rel.hasPrefix("_CodeSignature") { continue }
            let data = try Data(contentsOf: V1Bundle.root.appendingPathComponent(rel))
            // binaries: printable runs (what `strings` sees); text: the file as UTF-8
            let text: String
            if isBinary || ext == "plist" || ext == "strings" {
                // the build machine's source paths (#file in assertion / log messages) name the INTERNAL folder apps/mazeout
                // (SPEC.md §5.1: folder and branch are internal); they are counted, not matched
                let runs = Self.printableRuns(data)
                let paths = runs.filter { $0.contains("/apps/mazeout/") }
                if !paths.isEmpty { allowed.append("\(rel): \(paths.count) source path(s) under the internal folder apps/mazeout/") }
                text = runs.filter { !$0.contains("/apps/mazeout/") }.joined(separator: "\n")
            } else {
                text = String(decoding: data, as: UTF8.self)
            }
            scanned += 1
            var found = Self.bannedExact.filter { text.contains($0) } + Self.bannedAnyCase.filter { text.range(of: $0, options: .caseInsensitive) != nil }
            if isBinary, text.contains(brand) { found.append("\(brand) (a literal in the binary: Brand reads Info.plist)") }
            if found.isEmpty { continue }
            let line = "\(rel): \(Array(Set(found)).sorted())"
            if Self.socialNameData.contains(rel) { allowed.append(line) } else { hits.append(line) }
        }
        v1Attach("brand-scan", "scanned \(scanned) files\nhits:\n\(hits.joined(separator: "\n"))\nallowed (the name generator's blocklists / word lists):\n\(allowed.joined(separator: "\n"))")
        XCTAssertGreaterThan(scanned, 150)
        XCTAssertEqual(hits, [], "the original's names in the built app")
    }

    /// The generator blocks the original's names (the hashed blocklist entries, the marked tokens and the "maze" stem across
    /// token boundaries), so no generated nickname on any board shows them (a 3 000-name sample of the World list + Turkey's
    /// and the US's lists). B2: sampled at the capture date + 19 weeks — the same world age as before, since the shipped v2
    /// world starts 19 weeks later (at the capture date itself it is 18 days old and Turkey's board holds a few hundred).
    func testNoGeneratedNicknameShowsTheOriginalsNames() throws {
        let folder = try XCTUnwrap(Bundle.main.resourceURL).appendingPathComponent("Social")
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: folder.path).filter { !$0.hasPrefix(".") }, ["social_names.json"])
        let names = try NameBank.load(folder: folder)
        let world = SocialWorld(installSeed: 1, config: Tuning.load(bundle: .main).social.config, names: names)
        let me = PlayerStanding(name: "player_1", avatar: 0, country: "TR", level: 62, ledger: [])
        let at = SocialTime(seconds: Int64(LaunchArgs.captureDate.timeIntervalSince1970) + 19 * 604_800)
        var seen: [String] = []
        for kind in [LeaderboardKind.world, .country("TR"), .country("US")] {
            var start = 1
            while start <= 1000 {
                let page = world.page(kind, me: me, at: at, ranks: start...(start + 99))
                seen += page.rows.map(\.player.name)
                start += 100
            }
        }
        XCTAssertGreaterThan(seen.count, 2500)
        let bad = seen.filter { n in (Self.bannedAnyCase + ["maze"]).contains { n.range(of: $0, options: .caseInsensitive) != nil } }
        XCTAssertEqual(bad, [], "generated nicknames with the original's names")
    }

    /// `strings`-like printable ASCII/UTF-8 runs of ≥ 4 bytes.
    static func printableRuns(_ data: Data, min: Int = 4) -> [String] {
        var out: [String] = []
        var run: [UInt8] = []
        func flush() { if run.count >= min { out.append(String(decoding: run, as: UTF8.self)) }; run.removeAll(keepingCapacity: true) }
        for b in data {
            if (b >= 0x20 && b < 0x7F) || b >= 0x80 || b == 0x09 { run.append(b) } else { flush() }
        }
        flush()
        return out
    }
}
