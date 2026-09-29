// Registers a font file with CTFontManager (process scope, like UIAppFonts) and checks that CoreText resolves the
// PostScript / family names to that file and not to a fallback.  usage: resolve FONT.ttf PSNAME
import Foundation
import CoreText
let url = URL(fileURLWithPath: CommandLine.arguments[1]); let ps = CommandLine.arguments[2]
var err: Unmanaged<CFError>?
let ok = CTFontManagerRegisterFontsForURL(url as CFURL, .process, &err)
print("registered:", ok, err.map { CFErrorCopyDescription($0.takeRetainedValue()) as String } ?? "")
let f = CTFontCreateWithName(ps as CFString, 20, nil)
let got = CTFontCopyPostScriptName(f) as String
let fam = CTFontCopyFamilyName(f) as String
let furl = CTFontCopyAttribute(f, kCTFontURLAttribute) as? URL
print("request \(ps) -> ps \(got), family \(fam), file \(furl?.lastPathComponent ?? "nil")", got == ps ? "OK" : "FALLBACK!")
for name in ["PC Display", "PCDisplay", "PCDisplay-Regular"] {
    let g = CTFontCreateWithName(name as CFString, 20, nil)
    print("request \(name) -> \(CTFontCopyPostScriptName(g) as String)")
}
// glyph check for the Turkish letters
let s = "İıĞğŞşÇçÖöÜü" as NSString
var chars = [UniChar](repeating: 0, count: s.length); s.getCharacters(&chars)
var glyphs = [CGGlyph](repeating: 0, count: s.length)
let all = CTFontGetGlyphsForCharacters(f, chars, &glyphs, s.length)
print("turkish glyphs all present:", all, glyphs)
