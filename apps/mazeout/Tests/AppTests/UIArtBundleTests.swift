import Foundation
import ImageIO
import XCTest
import PathCore
@testable import ArrowOut

/// VERIFY V1 (SPEC-architecture §6.11 `UIArtBundleTests`, §12.2 V1: 0 missing art in the bundle; GP §14 / memory
/// never-ship-stand-in-content). A missing raster would draw the hatched DebugPlaceholder in Debug and nothing in Release:
///  - every `UIArt` case (tools/uiart_gen.py from art/MANIFEST.json) has its file and it decodes as a real image of a
///    plausible @3x size;
///  - every board sprite the engine asks for (BoardArt's warm-up list + every bundled level's tape and obstacle sprites, and
///    the validator's sprite ids) is in `UI/`;
///  - the home puppets' rigs load and every layer PNG and full render they name exists;
///  - every "UI/…png" / "Art/…png" path spelled in App/**/*.swift exists in the bundle;
///  - `UI/` and `Art/` hold only PNG / JSON and no `_*` scratch file (tools/sync_art.sh rules).
final class UIArtBundleTests: XCTestCase {

    private var resources: URL { Bundle.main.resourceURL! }

    func testEveryUIArtCaseIsInTheBundleAndDecodes() {
        XCTAssertEqual(ArtStore.missing(), [], "UIArt ids with no file in the bundle")
        var bad: [String] = []
        for art in UIArt.allCases {
            let url = resources.appendingPathComponent(art.path)
            guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
                  let props = CGImageSourceCopyPropertiesAtIndex(src, 0, nil) as? [CFString: Any],
                  let w = props[kCGImagePropertyPixelWidth] as? Int, let h = props[kCGImagePropertyPixelHeight] as? Int else {
                bad.append("\(art.rawValue): does not decode (\(art.path))"); continue
            }
            if w < 3 || h < 3 { bad.append("\(art.rawValue): \(w)x\(h) px") }
            if (props[kCGImagePropertyDPIWidth] as? Double).map({ $0 <= 0 }) == true { bad.append("\(art.rawValue): bad DPI") }
        }
        XCTAssertEqual(bad, [])
        XCTAssertGreaterThanOrEqual(UIArt.allCases.count, 150, "the generated list is the shipped set")
    }

    /// The UIArt ids the code actually draws (`.caseName` / `UIArt.caseName` / `"caseName"` in App/**/*.swift outside the
    /// generated list): each has its file. (The strict test above also covers ids no screen uses.)
    func testEveryUIArtIdTheCodeUsesIsInTheBundle() throws {
        let cases = Dictionary(uniqueKeysWithValues: UIArt.allCases.map { ($0.rawValue, $0) })
        let re = try NSRegularExpression(pattern: #"(?:\.|UIArt\.|")([a-z][A-Za-z0-9]+)\b"#)
        var used = Set<UIArt>()
        for f in V1Repo.files("App", extensions: ["swift"]) where f.lastPathComponent != "UIArt.swift" {
            let text = try String(contentsOf: f, encoding: .utf8)
            let ns = text as NSString
            for m in re.matches(in: text, range: NSRange(location: 0, length: ns.length)) {
                if let a = cases[ns.substring(with: m.range(at: 1))] { used.insert(a) }
            }
        }
        XCTAssertGreaterThan(used.count, 60, "the scan finds the art the screens draw")
        let missing = used.filter { !ArtStore.exists($0) }.map(\.rawValue).sorted()
        v1Attach("uiart-used", "used \(used.count) of \(UIArt.allCases.count); missing: \(missing)\nunused ids: "
                 + Set(UIArt.allCases).subtracting(used).map(\.rawValue).sorted().joined(separator: ", "))
        XCTAssertEqual(missing, [], "art a screen draws that the bundle lacks (it would show a placeholder in Debug, nothing in Release)")
    }

    @MainActor func testEveryBoardSpriteOfEveryBundledLevelResolves() throws {
        let ui = resources.appendingPathComponent("UI")
        let catalog = try SpriteCatalog.load(folder: ui)
        var needed = Set(BoardArt.names)
        let library = try LevelLibrary.load(folder: resources.appendingPathComponent("Levels"))
        var levels = 0
        for n in 1...library.authoredCount {
            let l = try library.loadAuthored(n)
            levels += 1
            needed.formUnion(TapeLayer.spriteIDs(l))
            needed.formUnion(ObstacleSet.spriteIDs(l))
            for o in l.obstacles { needed.formUnion(Validator.spriteIDs(o)) }
        }
        XCTAssertEqual(levels, library.authoredCount)
        XCTAssertGreaterThanOrEqual(levels, 150)
        // FIX-2 A (L02): the corner's 8 per-facing layers (spring + plate × 4 turns) are among the checked sprites
        for t in CornerTurn.allCases {
            let ids = CornerNode.layerIDs(t)
            XCTAssertTrue(needed.contains(ids.spring) && needed.contains(ids.plate), "\(t): \(ids)")
        }
        let missing = needed.filter { !catalog.contains($0) }.sorted()
        XCTAssertEqual(missing, [], "board sprites the engine or validator asks for that UI/ lacks")
        for id in needed.sorted() {
            XCTAssertTrue(FileManager.default.fileExists(atPath: ui.appendingPathComponent("\(id)@3x.png").path), "UI/\(id)@3x.png")
        }
        let cache = SpriteCache(capMB: 64, bundle: .main)
        for id in needed.sorted() { XCTAssertNotNil(cache.image(id), "SpriteCache decodes \(id)") }
    }

    @MainActor func testHomePuppetRigsLoadWithEveryLayer() throws {
        let home = try V1Repo.text("App/Shell/Home/HomeView.swift")
        let re = try NSRegularExpression(pattern: #"rigName:\s*"([^"]+)""#)
        let ns = home as NSString
        let names = Set(re.matches(in: home, range: NSRange(location: 0, length: ns.length)).map { ns.substring(with: $0.range(at: 1)) })
        XCTAssertGreaterThanOrEqual(names.count, 3, "the scientist and the two workers")
        for name in names.sorted() {
            let rig = try PuppetRig.load(name)
            XCTAssertFalse(rig.layers.isEmpty, name)
            for l in rig.layers {
                XCTAssertTrue(FileManager.default.fileExists(atPath: resources.appendingPathComponent(rig.path(l)).path), "\(name): \(rig.path(l))")
            }
            if let full = rig.fullPath {
                XCTAssertTrue(FileManager.default.fileExists(atPath: resources.appendingPathComponent(full).path), "\(name): \(full)")
            }
        }
    }

    func testEveryArtPathSpelledInTheCodeExists() throws {
        let re = try NSRegularExpression(pattern: #""((?:UI|Art)/[A-Za-z0-9_./-]+\.(?:png|json))""#)
        var checked = 0
        var missing: [String] = []
        for f in V1Repo.files("App", extensions: ["swift"]) {
            let text = try String(contentsOf: f, encoding: .utf8)
            let ns = text as NSString
            for m in re.matches(in: text, range: NSRange(location: 0, length: ns.length)) {
                let path = ns.substring(with: m.range(at: 1))
                checked += 1
                if !FileManager.default.fileExists(atPath: resources.appendingPathComponent(path).path) { missing.append("\(V1Repo.relative(f)): \(path)") }
            }
        }
        v1Attach("art-paths", "checked \(checked)\n" + missing.joined(separator: "\n"))
        XCTAssertEqual(missing, [])
    }

    func testArtFoldersHoldOnlyShippedFiles() throws {
        var bad: [String] = []
        var pngs = 0
        for folder in ["UI", "Art"] {
            let root = resources.appendingPathComponent(folder)
            guard let e = FileManager.default.enumerator(at: root, includingPropertiesForKeys: [.isRegularFileKey]) else {
                XCTFail("\(folder)/ missing from the bundle"); continue
            }
            for case let u as URL in e where (try? u.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true {
                let name = u.lastPathComponent
                if name.hasPrefix("_") { bad.append("\(folder)/…/\(name): scratch file") }
                if !["png", "json"].contains(u.pathExtension.lowercased()) { bad.append("\(folder)/…/\(name): not PNG/JSON") }
                if u.pathExtension == "png" { pngs += 1 }
            }
        }
        XCTAssertEqual(bad, [])
        XCTAssertGreaterThan(pngs, 150)
    }

    // MARK: FIX-2 lane B (A4-r2 / A4-r6): retired, provenance-only and build-only art never ships

    /// tools/uiart_gen.py's ONE rule, read from the same files: an art/MANIFEST.json entry with status 'not-shipped' or notes
    /// starting 'NOT SHIPPED', or an id listed in tools/art_build_only.txt.
    static func neverShipped() throws -> [(id: String, file: String)] {
        let json = try JSONSerialization.jsonObject(with: Data(contentsOf: V1Repo.url("art/MANIFEST.json"))) as? [String: Any]
        let entries = try XCTUnwrap(json?["entries"] as? [[String: Any]], "art/MANIFEST.json entries")
        let buildOnly = Set(try V1Repo.text("tools/art_build_only.txt").components(separatedBy: "\n").map {
            String($0.split(separator: "#", maxSplits: 1, omittingEmptySubsequences: false).first ?? "").trimmingCharacters(in: .whitespaces)
        }.filter { !$0.isEmpty })
        let ids = Set(entries.compactMap { $0["id"] as? String })
        XCTAssertEqual(buildOnly.subtracting(ids), [], "tools/art_build_only.txt names only manifest ids")
        return entries.compactMap { e in
            guard let id = e["id"] as? String else { return nil }
            let retired = (e["status"] as? String) == "not-shipped" || ((e["notes"] as? String) ?? "").hasPrefix("NOT SHIPPED")
            return retired || buildOnly.contains(id) ? (id, (e["file"] as? String) ?? "") : nil
        }
    }

    /// The bundle paths a manifest file would occupy (tools/sync_art.sh): art/ui/out → UI/, art/out → Art/ (+ its `<stem>.json`
    /// sidecar); a path with no extension is a rig folder (every file under it).
    static func bundlePaths(_ file: String) -> [String] {
        let f = file.hasSuffix("/") ? String(file.dropLast()) : file
        if f.hasPrefix("art/ui/out/") { return ["UI/" + f.dropFirst("art/ui/out/".count)] }
        guard f.hasPrefix("art/out/") else { return [] }
        let rel = String(f.dropFirst("art/out/".count))
        if (rel as NSString).pathExtension.isEmpty { return ["Art/\(rel)/"] }
        let stem = rel.hasSuffix("@3x.png") ? String(rel.dropLast("@3x.png".count)) : (rel as NSString).deletingPathExtension
        return ["Art/\(rel)", "Art/\(stem).json"]
    }

    /// What of the never-shipped set is in `files` (bundle-relative) or has a UIArt case in `cases`.
    static func leaks(files: Set<String>, cases: Set<String>, never: [(id: String, file: String)]) -> [String] {
        var out: [String] = []
        for (id, file) in never {
            if cases.contains(id) { out.append("UIArt.\(id)") }
            for p in bundlePaths(file) {
                if p.hasSuffix("/") ? files.contains(where: { $0.hasPrefix(p) }) : files.contains(p) { out.append(p) }
            }
        }
        return out.sorted()
    }

    /// Every regular file under the bundle's UI/ and Art/, bundle-relative ("UI/boxRing@3x.png").
    private var artFiles: Set<String> {
        var out = Set<String>()
        for folder in ["UI", "Art"] {
            let root = resources.appendingPathComponent(folder)
            guard let e = FileManager.default.enumerator(at: root, includingPropertiesForKeys: [.isRegularFileKey]) else { continue }
            for case let u as URL in e where (try? u.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true {
                out.insert(folder + "/" + String(u.path.dropFirst(root.path.count + 1)))
            }
        }
        return out
    }

    func testNoNotShippedArtShips() throws {
        let never = try Self.neverShipped()
        XCTAssertGreaterThanOrEqual(never.count, 70, "the 48 retired ids + the provenance-only ids + tools/art_build_only.txt")
        for id in ["unlockIconCurtain", "boosterDome", "boosterPointer", "curtainCrate", "frostCracks", "prizeSign", "rankBadgePlain",
                   "digBalloon", "digClawPair", "digRacers", "arrowGlossyRed", "arrowGlossyCyan", "appIcon"] {
            XCTAssertTrue(never.contains { $0.id == id }, "\(id) is retired / build-only")
        }
        let files = artFiles, cases = Set(UIArt.allCases.map(\.rawValue))
        XCTAssertGreaterThan(files.count, 200, "the scan sees the bundle's art")
        XCTAssertEqual(Self.leaks(files: files, cases: cases, never: never), [], "retired / provenance-only / build-only art in the app")
        // negative control: keeping ONE id (its case and its file, the A4 finding) is caught — and so is a build-only render
        XCTAssertEqual(Self.leaks(files: files.union(["UI/unlockIconCurtain@3x.png", "Art/char_digBalloon.json"]),
                                  cases: cases.union(["unlockIconCurtain"]), never: never),
                       ["Art/char_digBalloon.json", "UI/unlockIconCurtain@3x.png", "UIArt.unlockIconCurtain"])
    }

    /// Stronger than `testArtFoldersHoldOnlyShippedFiles`: EVERY file of UI/ and Art/ is something the code can draw — a PNG is
    /// a UIArt case's path, a layer of the rig whose folder holds it, or a rig's full render; a JSON is a loadable rig's rig.json
    /// or an Art/char_*.json placement sidecar (tools/sync_art.sh ships nothing else).
    @MainActor func testEveryBundledArtFileIsDrawnByTheCode() throws {
        var allowed = Set(UIArt.allCases.map(\.path))
        var rigs = 0
        let artRoot = resources.appendingPathComponent("Art")
        for name in try FileManager.default.contentsOfDirectory(atPath: artRoot.path) where name.hasSuffix("_rig") {
            let rig = try PuppetRig.load(name)
            rigs += 1
            allowed.insert("Art/\(name)/rig.json")
            for l in rig.layers { allowed.insert(rig.path(l)) }
            if let full = rig.fullPath { allowed.insert(full) }
        }
        XCTAssertGreaterThanOrEqual(rigs, 8, "the boss, two Diggers, the signpost and the four badge rigs")
        func unexplained(_ files: Set<String>) -> [String] {
            files.filter { f in
                if allowed.contains(f) { return false }
                let name = (f as NSString).lastPathComponent
                return !(f.hasPrefix("Art/") && f.split(separator: "/").count == 2 && name.hasPrefix("char_") && name.hasSuffix(".json"))
            }.sorted()
        }
        let files = artFiles
        XCTAssertEqual(unexplained(files), [], "bundled art no code draws (retire it in the manifest or list it in tools/art_build_only.txt)")
        // negative control: a dead render left in Art/ is caught
        XCTAssertEqual(unexplained(files.union(["Art/arrowGlossyRed@3x.png"])), ["Art/arrowGlossyRed@3x.png"])
    }
}
