// ctfit (B3 L10N-APP, tools/strings/l10n_review.py): the ink width of one line of text in PC Display WITH the app's bold
// fallback cascade (App/Shell/Components/GameText.swift `FontCascade`: the same chain, the same per-string CJK order), so the
// 13-language fit rule measures a Japanese / Korean / Chinese / Greek … line with the glyphs the app draws.
//   xcrun swiftc -O -o build/strings/bin/ctfit tools/strings/ctfit.swift
//   build/strings/bin/ctfit jobs.json     -> one JSON line per job
// job: {"id", "font": path of PCDisplay-Black.ttf, "text", "size", "track", "lang": the app language ("ja", "zh-Hans", …)}
// out: {"id", "inkX0", "inkX1", "advance", "fonts": [PostScript names drawn]}
// Derived from design/ui-crops/_tools/ctmeasure.swift (never edited).
import Foundation
import CoreText
import CoreGraphics
import AppKit

struct Job: Decodable { let id: String; let font: String; let text: String; let size: Double; let track: Double?; let lang: String? }

enum Face: Int { case ja, zh, ko }
let greek = "HelveticaNeue-Bold"
let cjk: [Face: String] = [.ja: "HiraginoSans-W8", .zh: "PingFangSC-Semibold", .ko: "AppleSDGothicNeo-Bold"]
let tail = ["GeezaPro-Bold", "ArialHebrew-Bold", "Thonburi-Bold", "NotoSansArmenian-Bold"]

func available(_ name: String) -> Bool {
    let d = CTFontDescriptorCreateWithNameAndSize(name as CFString, 0)
    guard let m = CTFontDescriptorCreateMatchingFontDescriptor(d, nil) else { return false }
    return (CTFontDescriptorCopyAttribute(m, kCTFontNameAttribute) as? String) == name
}

func names(_ f: Face) -> [String] {
    let order: [Face] = f == .ja ? [.ja, .zh, .ko] : f == .zh ? [.zh, .ja, .ko] : [.ko, .ja, .zh]
    return ([greek] + order.compactMap { cjk[$0] } + tail).filter(available)
}

struct Scripts { var kana = false, hangul = false, han = false }
func scripts(_ s: String) -> Scripts {
    var r = Scripts()
    for u in s.unicodeScalars {
        switch u.value {
        case 0x3041...0x30FF, 0x31F0...0x31FF, 0xFF66...0xFF9F: r.kana = true
        case 0xAC00...0xD7AF, 0x1100...0x11FF, 0x3130...0x318F: r.hangul = true
        case 0x4E00...0x9FFF, 0x3400...0x4DBF, 0xF900...0xFAFF, 0x20000...0x2FFFF: r.han = true
        default: break
        }
    }
    return r
}
let hiragino = CTFontCreateWithName("HiraginoSans-W8" as CFString, 12, nil)
func hiraginoHas(_ text: String) -> Bool {
    for u in text.unicodeScalars where scripts(String(u)).han {
        var utf16 = Array(String(u).utf16)
        var g = [CGGlyph](repeating: 0, count: utf16.count)
        if !CTFontGetGlyphsForCharacters(hiragino, &utf16, &g, utf16.count) { return false }
    }
    return true
}
func face(_ text: String, lang: String) -> Face {
    let app: Face = lang.hasPrefix("ja") ? .ja : lang.hasPrefix("ko") ? .ko : .zh
    let s = scripts(text)
    if s.kana { return .ja }
    if s.hangul { return .ko }
    if s.han { return app == .ja && hiraginoHas(text) ? .ja : .zh }
    return app
}

let jobs = try! JSONDecoder().decode([Job].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
var registered = Set<String>()
for j in jobs {
    if !registered.contains(j.font) {
        CTFontManagerRegisterFontsForURL(URL(fileURLWithPath: j.font) as CFURL, .process, nil)
        registered.insert(j.font)
    }
    let d0 = (CTFontManagerCreateFontDescriptorsFromURL(URL(fileURLWithPath: j.font) as CFURL) as! [CTFontDescriptor])[0]
    let psName = CTFontDescriptorCopyAttribute(d0, kCTFontNameAttribute) as! String
    let lang = j.lang ?? "en"
    let f = face(j.text, lang: lang)
    // the app's chain (GameText.swift FontCascade.cascade): the system's Black fallback cascade for the face's language, then
    // the named public faces (on macOS the system cascade reaches Apple SD Gothic Neo Heavy, which iOS lacks: Korean widths
    // differ by a hair; Tests/AppTests/L10nTests.swift measures on iOS)
    let black = NSFont.systemFont(ofSize: 20, weight: .black) as CTFont
    let cascadeLang = f == .ja ? "ja" : f == .ko ? "ko" : "zh-Hans"
    let system = (CTFontCopyDefaultCascadeListForLanguages(black, [cascadeLang] as CFArray) as? [CTFontDescriptor]) ?? []
    let cascade = system + names(f).map { CTFontDescriptorCreateWithNameAndSize($0 as CFString, 0) }
    let desc = CTFontDescriptorCreateWithAttributes([kCTFontNameAttribute: psName, kCTFontCascadeListAttribute: cascade] as CFDictionary)
    let font = CTFontCreateWithFontDescriptor(desc, CGFloat(j.size), nil)
    var attrs: [NSAttributedString.Key: Any] = [NSAttributedString.Key(kCTFontAttributeName as String): font]
    if let t = j.track { attrs[NSAttributedString.Key(kCTKernAttributeName as String)] = t }
    let sc = scripts(j.text)
    if sc.kana || sc.hangul || sc.han {
        attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = f == .ja ? "ja" : f == .ko ? "ko" : "zh-Hans"
    } else if lang.hasPrefix("tr") {
        attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = "tr"
    }
    let line = CTLineCreateWithAttributedString(NSAttributedString(string: j.text.isEmpty ? " " : j.text, attributes: attrs))
    var x0 = Double.infinity, x1 = -Double.infinity
    var fonts = Set<String>()
    for run in CTLineGetGlyphRuns(line) as! [CTRun] {
        let cnt = CTRunGetGlyphCount(run)
        var glyphs = [CGGlyph](repeating: 0, count: cnt); var pos = [CGPoint](repeating: .zero, count: cnt)
        CTRunGetGlyphs(run, CFRange(location: 0, length: cnt), &glyphs)
        CTRunGetPositions(run, CFRange(location: 0, length: cnt), &pos)
        let rf = (CTRunGetAttributes(run) as NSDictionary)[kCTFontAttributeName as String] as! CTFont
        fonts.insert(CTFontCopyPostScriptName(rf) as String)
        for i in 0..<cnt {
            guard let p = CTFontCreatePathForGlyph(rf, glyphs[i], nil) else { continue }
            let b = p.boundingBoxOfPath
            if b.isNull || b.width == 0 { continue }
            x0 = min(x0, Double(pos[i].x + b.minX)); x1 = max(x1, Double(pos[i].x + b.maxX))
        }
    }
    let adv = CTLineGetTypographicBounds(line, nil, nil, nil)
    let out: [String: Any] = ["id": j.id, "inkX0": x0.isFinite ? x0 : 0, "inkX1": x1.isFinite ? x1 : 0, "advance": adv,
                              "fonts": fonts.sorted()]
    print(String(data: try! JSONSerialization.data(withJSONObject: out), encoding: .utf8)!)
}
