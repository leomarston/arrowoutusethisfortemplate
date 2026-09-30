import Foundation
import SwiftUI
import UIKit
import XCTest
@testable import ArrowOut

/// SKIN (docs/SKIN.md, ROADMAP phase 3): the UI's colours are skin tokens. skin/colors.json (palette + tokens) is the
/// source; tools/skin/build.py generates `Skin` (App/Shell/Components/SkinColors.generated.swift) and the id -> constant
/// table this test reads (SkinColorsTable.generated.swift). The Linux CI job runs `build.py --check` (the generated files
/// are fresh) and `--check-literals` (no colour literal left in the UI sources); this test proves the COMPILED constants
/// are the JSON's colours, name by name, so a hand edit of the generated file or a stale build cannot slip through.
final class SkinColorsTests: XCTestCase {
    private struct Doc {
        var palette: [String: String]
        var tokens: [String: String]
    }

    private func loadDoc() throws -> Doc {
        let data = try Data(contentsOf: V1Repo.url("skin/colors.json"))
        let obj = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any], "skin/colors.json is an object")
        let palette = try XCTUnwrap(obj["palette"] as? [String: String], "palette: name -> #RRGGBB")
        let tokens = try XCTUnwrap(obj["tokens"] as? [String: String], "tokens: id -> palette name or #RRGGBB")
        return Doc(palette: palette, tokens: tokens)
    }

    private static func parseHex(_ s: String) -> UInt32? {
        guard s.count == 7, s.hasPrefix("#") else { return nil }
        return UInt32(s.dropFirst(), radix: 16)
    }

    private func resolve(_ doc: Doc, _ id: String) -> String? {
        guard let v = doc.tokens[id] else { return nil }
        return v.hasPrefix("#") ? v : doc.palette[v]
    }

    func testPaletteAndTokensAreWellFormed() throws {
        let doc = try loadDoc()
        XCTAssertGreaterThan(doc.palette.count, 100, "the palette holds the UI's colours")
        XCTAssertGreaterThan(doc.tokens.count, 1000, "every colour the UI code draws is a token")
        for (name, hex) in doc.palette {
            XCTAssertNotNil(Self.parseHex(hex), "palette \(name): \(hex) is not #RRGGBB")
            XCTAssertEqual(hex, hex.uppercased(), "palette \(name): upper-case hex")
        }
        for (id, v) in doc.tokens {
            XCTAssertNotNil(resolve(doc, id).flatMap(Self.parseHex), "token \(id) -> \(v) resolves to no colour")
        }
    }

    /// Every UInt32 constant equals its token's colour in colors.json, and the two sets of ids are the same.
    func testCompiledConstantsEqualColorsJSON() throws {
        let doc = try loadDoc()
        let rgb = SkinColorsTable.rgb(), hex = SkinColorsTable.hex()
        let jsonRGB = Set(doc.tokens.keys.filter { !$0.hasSuffix(".hex") })
        let jsonHex = Set(doc.tokens.keys.filter { $0.hasSuffix(".hex") })
        XCTAssertEqual(Set(rgb.keys).subtracting(jsonRGB).sorted(), [], "constants the JSON lacks (run tools/skin/build.py)")
        XCTAssertEqual(jsonRGB.subtracting(rgb.keys).sorted(), [], "tokens without a constant (run tools/skin/build.py)")
        XCTAssertEqual(Set(hex.keys), jsonHex, "String (.hex) tokens")
        var wrong: [String] = []
        for (id, value) in rgb {
            guard let want = resolve(doc, id).flatMap(Self.parseHex) else { wrong.append(id); continue }
            if value != want { wrong.append(String(format: "%@ = 0x%06X, JSON 0x%06X", id, value, want)) }
        }
        for (id, value) in hex where resolve(doc, id) != value {
            wrong.append("\(id) = \(value), JSON \(resolve(doc, id) ?? "nil")")
        }
        XCTAssertEqual(wrong.sorted(), [], "compiled skin constants that differ from skin/colors.json")
    }

    /// The String tokens parse as the colour tuning files use them (Color(hexString:) / UIColor(hexString:)).
    func testHexStringTokensParse() {
        for (id, value) in SkinColorsTable.hex() {
            XCTAssertNotNil(Color(hexString: value), id)
            XCTAssertNotNil(UIColor(hexString: value), id)
        }
    }

    /// The call sites read the skin, not a copy: a few shipping values traced back to their tokens in colors.json (the
    /// glossy panel buttons' outlines, the toast plate's String and UInt32 twins). Skin-agnostic: holds for any skin.
    func testCallSitesReadTheSkin() throws {
        let doc = try loadDoc()
        func json(_ id: String) -> UInt32? { resolve(doc, id).flatMap(Self.parseHex) }
        XCTAssertEqual(PanelButtonStyleColors.green.outline, json("art.glossyChrome.panelButtonStyleColors.green.outline"))
        XCTAssertEqual(PanelButtonStyleColors.red.outline, json("art.glossyChrome.panelButtonStyleColors.red.outline"))
        XCTAssertEqual(PanelButtonStyleColors.green.face.map { $0.0 },
                       (0..<6).map { json("art.glossyChrome.panelButtonStyleColors.green.face.\($0)") ?? 0 })
        XCTAssertEqual(Skin.componentsToastToastPlateHex, resolve(doc, "components.toast.toast.plate.hex"))
        XCTAssertEqual(Color(hex: Skin.componentsToastToastLayerFill),
                       Color(hexString: resolve(doc, "components.toast.toastLayer.fill") ?? ""))
    }

    /// The Mac-side twin of `build.py --check-literals` (line comments stripped, like the other source scans here): no
    /// 0xRRGGBB literal left in the skinned UI sources except the allow-list's non-colours.
    func testNoColourHexLiteralsLeftInTheUISources() throws {
        let allowData = try Data(contentsOf: V1Repo.url("tools/skin/literal_allowlist.json"))
        let allowObj = try XCTUnwrap(JSONSerialization.jsonObject(with: allowData) as? [String: Any])
        let allow = (allowObj["allow"] as? [[String: String]] ?? []).map { ($0["file"] ?? "", $0["literal"] ?? "") }
        let re = try NSRegularExpression(pattern: #"(?<![0-9A-Za-z_])0x[0-9A-Fa-f]{6}(?![0-9A-Fa-f_])"#)
        var files = V1Repo.files("App/Shell", extensions: ["swift"]) + V1Repo.files("App/FX", extensions: ["swift"])
        files.append(V1Repo.url("art/ui/code/GlossyChrome.swift"))
        var left: [String] = []
        for url in files where url.lastPathComponent != "SkinColors.generated.swift" {
            let rel = V1Repo.relative(url)
            let lines = try String(contentsOf: url, encoding: .utf8).components(separatedBy: "\n")
            for (i, line) in lines.enumerated() {
                let code = line.range(of: "//").map { String(line[..<$0.lowerBound]) } ?? line
                let ns = code as NSString
                for m in re.matches(in: code, range: NSRange(location: 0, length: ns.length)) {
                    let lit = ns.substring(with: m.range)
                    if !allow.contains(where: { rel.hasSuffix($0.0) && $0.1 == lit }) { left.append("\(rel):\(i + 1) \(lit)") }
                }
            }
        }
        XCTAssertGreaterThan(files.count, 60)
        XCTAssertEqual(left, [], "colour literals outside skin/colors.json (run tools/skin/codemod.py)")
    }
}
