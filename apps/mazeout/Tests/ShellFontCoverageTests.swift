import XCTest
import CoreText
import UIKit
@testable import ArrowOut

/// SHELL S1 (SPEC-architecture §6.11 `FontCoverageTests`; design/fonts.md §7). Both bundled faces resolve to themselves through
/// UIAppFonts and render "ıİşŞğĞüÜöÖçÇ" (and the TR samples of the shell's copy) without any fallback run; exactly the two TTFs
/// ship. VERIFY (V1) adopts this class for its AppTests suite (keep ONE `FontCoverageTests` class).
@MainActor final class FontCoverageTests: XCTestCase {
    static let turkish = "ıİşŞğĞüÜöÖçÇ"

    func testBothFacesRenderTurkishWithoutFallback() throws {
        for ps in [GameText.blackPostScript, GameText.italicPostScript] {
            let ui = try XCTUnwrap(UIFont(name: ps, size: 20), "\(ps) is registered (UIAppFonts)")
            let font = ui as CTFont
            XCTAssertEqual(CTFontCopyPostScriptName(font) as String, ps, "\(ps) resolved to itself")
            let chars = Array(Self.turkish.utf16)
            var glyphs = [CGGlyph](repeating: 0, count: chars.count)
            XCTAssertTrue(CTFontGetGlyphsForCharacters(font, chars, &glyphs, chars.count), "\(ps) maps every Turkish letter")
            for (i, g) in glyphs.enumerated() {
                XCTAssertNotEqual(g, 0, "\(ps) has \(Array(Self.turkish)[i])")
                if g != 0 { XCTAssertNotNil(CTFontCreatePathForGlyph(font, g, nil), "\(ps) draws \(Array(Self.turkish)[i])") }
            }
            let layout = GameTextLayout.make(Self.turkish + " Duraklatıldı Yükleniyor Seviyeden Çık? 0123456789", postScriptName: ps,
                                             size: 25, tracking: 0)
            XCTAssertEqual(layout.runFonts, [ps], "GameText never leaves \(ps) for Turkish copy")
        }
    }

    func testExactlyTheTwoFontsShip() throws {
        let dir = try XCTUnwrap(Bundle.main.resourceURL).appendingPathComponent("Fonts")
        let ttf = try FileManager.default.contentsOfDirectory(atPath: dir.path).filter { $0.hasSuffix(".ttf") || $0.hasSuffix(".otf") }
        // the skin's faces (skin/fonts.json -> SkinFonts; tools/skin/build.py writes the same list into UIAppFonts)
        XCTAssertEqual(SkinFonts.files.count, 2, "one file per face role (black, blackItalic)")
        XCTAssertEqual(Set(ttf), Set(SkinFonts.files))
        let listed = Bundle.main.object(forInfoDictionaryKey: "UIAppFonts") as? [String] ?? []
        XCTAssertEqual(Set(listed), Set(SkinFonts.files.map { "Fonts/" + $0 }))
        XCTAssertTrue(FileManager.default.fileExists(atPath: dir.appendingPathComponent("OFL.txt").path), "OFL.txt ships with the fonts")
    }
}
