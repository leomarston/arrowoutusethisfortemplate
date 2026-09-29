// textmask — renders ONE line of caption text with CoreText into an 8-bit alpha mask (PNG) and prints its metrics as JSON.
//
// Why CoreText and not PIL/FreeType: the zh-Hans face (PingFang SC Heavy, the in-app cascade's face) ships in Apple's
// 'hvgl' outline format, which FreeType cannot open; CoreText also gives the same per-character font fallback, shaping
// and kerning as the app's GameText cascade on iOS.
//
// Font choice per character = the app's cascade: a character the primary face (PCDisplay-Black) has a glyph for is drawn
// in it; any other character is drawn in the first --cascade face that has it. A space takes the face of the run before it.
//
// Usage (compose.py builds and calls this; you normally never run it by hand):
//   textmask --text "Arrow Out" --size 120 --primary /path/PCDisplay-Black.ttf \
//            [--cascade "/path/font.ttc|PostScriptName|wght"]... --out mask.png
//   (--cascade: file | PostScript name inside the file (or a registered system name when the file is '-') | optional
//    'wght' axis value for variable faces, e.g. 900 = PingFang SC Heavy)
// stdout JSON (pixels, y measured DOWN from the top of the PNG):
//   w, h, baseline, advance, ink [x0,y0,x1,y1], optical [y0,y1] (Latin runs: cap-height box; cascade runs: their ink),
//   runs [{text, font}]
import CoreText
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
    exit(2)
}

var text = "", size: CGFloat = 100, primaryPath = "", outPath = ""
var cascadeSpecs: [String] = []
var args = Array(CommandLine.arguments.dropFirst())
while !args.isEmpty {
    let k = args.removeFirst()
    guard !args.isEmpty else { fail("missing value for \(k)") }
    let v = args.removeFirst()
    switch k {
    case "--text": text = v
    case "--size": size = CGFloat(Double(v) ?? 100)
    case "--primary": primaryPath = v
    case "--cascade": cascadeSpecs.append(v)
    case "--out": outPath = v
    default: fail("unknown option \(k)")
    }
}
if text.isEmpty || primaryPath.isEmpty || outPath.isEmpty { fail("need --text, --primary, --out") }

func descriptors(_ path: String) -> [CTFontDescriptor] {
    let url = URL(fileURLWithPath: path) as CFURL
    guard let arr = CTFontManagerCreateFontDescriptorsFromURL(url) as? [CTFontDescriptor], !arr.isEmpty else {
        fail("cannot load fonts from \(path)")
    }
    return arr
}

func psName(_ d: CTFontDescriptor) -> String {
    (CTFontDescriptorCopyAttribute(d, kCTFontNameAttribute) as? String) ?? ""
}

func makeFont(spec: String) -> CTFont {
    let parts = spec.components(separatedBy: "|")
    let path = parts[0]
    let name = parts.count > 1 ? parts[1] : ""
    var font: CTFont
    if path == "-" {
        font = CTFontCreateWithName(name as CFString, size, nil)
        if (CTFontCopyPostScriptName(font) as String) != name { fail("system font \(name) not found") }
    } else {
        let ds = descriptors(path)
        guard let d = name.isEmpty ? ds.first : ds.first(where: { psName($0) == name }) else {
            fail("face \(name) not in \(path): \(ds.map(psName))")
        }
        font = CTFontCreateWithFontDescriptor(d, size, nil)
    }
    if parts.count > 2, let w = Double(parts[2]) {
        let wghtTag = 0x77676874  // 'wght'
        let vd = CTFontDescriptorCreateWithAttributes([kCTFontVariationAttribute: [wghtTag: w]] as CFDictionary)
        font = CTFontCreateCopyWithAttributes(font, size, nil, vd)
    }
    return font
}

let primary = CTFontCreateWithFontDescriptor(descriptors(primaryPath)[0], size, nil)
let cascade = cascadeSpecs.map { makeFont(spec: $0) }

func has(_ font: CTFont, _ ch: Character) -> Bool {
    let u = Array(String(ch).utf16)
    var glyphs = [CGGlyph](repeating: 0, count: u.count)
    return CTFontGetGlyphsForCharacters(font, u, &glyphs, u.count) && !glyphs.contains(0)
}

// Assign a face index to every character (-1 = primary, i = cascade[i]); spaces follow the run before them.
let chars = Array(text)
var faceOf: [Int?] = chars.map { ch in
    if ch == " " { return nil }
    if has(primary, ch) { return -1 }
    for (i, f) in cascade.enumerated() where has(f, ch) { return i }
    fail("no face has a glyph for '\(ch)' (U+\(String(ch.unicodeScalars.first!.value, radix: 16)))")
}
for i in faceOf.indices where faceOf[i] == nil {
    faceOf[i] = (i > 0 ? faceOf[i - 1] : nil) ?? faceOf[(i + 1)...].compactMap { $0 }.first ?? -1
}

let attr = NSMutableAttributedString(string: text)
attr.addAttribute(NSAttributedString.Key(kCTForegroundColorAttributeName as String),
                  value: CGColor(gray: 1, alpha: 1), range: NSRange(location: 0, length: (text as NSString).length))
var runsOut: [[String: String]] = []
var utf16Pos = 0
var i = 0
while i < chars.count {
    var j = i
    while j < chars.count && faceOf[j] == faceOf[i] { j += 1 }
    let piece = String(chars[i..<j])
    let len = piece.utf16.count
    let font = faceOf[i]! == -1 ? primary : cascade[faceOf[i]!]
    attr.addAttribute(NSAttributedString.Key(kCTFontAttributeName as String), value: font,
                      range: NSRange(location: utf16Pos, length: len))
    runsOut.append(["text": piece, "font": CTFontCopyPostScriptName(font) as String])
    utf16Pos += len
    i = j
}
let line = CTLineCreateWithAttributedString(attr)
var ascent: CGFloat = 0, descent: CGFloat = 0, leading: CGFloat = 0
let advance = CGFloat(CTLineGetTypographicBounds(line, &ascent, &descent, &leading))
let pad = ceil(size * 0.35)
let W = Int(ceil(advance + 2 * pad)), H = Int(ceil(ascent + descent + 2 * pad))
guard let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: 0,
                          space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue) else {
    fail("no context")
}
ctx.setFillColor(gray: 0, alpha: 1)
ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
ctx.setFillColor(gray: 1, alpha: 1)
ctx.setShouldAntialias(true)
ctx.setAllowsFontSmoothing(false)
ctx.setShouldSmoothFonts(false)
let originY = pad + descent  // baseline in CG (bottom-up) coordinates
ctx.textPosition = CGPoint(x: pad, y: originY)
CTLineDraw(line, ctx)

// Optical box: Latin (primary) runs contribute their cap-height box, cascade runs their ink.
ctx.textPosition = CGPoint(x: pad, y: originY)  // CTLineDraw advanced it; image bounds are measured from it
let baselineTop = CGFloat(H) - originY  // baseline measured from the top
var optTop = CGFloat.greatestFiniteMagnitude, optBot = -CGFloat.greatestFiniteMagnitude
for run in (CTLineGetGlyphRuns(line) as! [CTRun]) {
    let attrs = CTRunGetAttributes(run) as NSDictionary
    let f = attrs[kCTFontAttributeName as String] as! CTFont
    let r = CTRunGetStringRange(run)
    let s = (text as NSString).substring(with: NSRange(location: r.location, length: r.length))
    if s.trimmingCharacters(in: .whitespaces).isEmpty { continue }
    if (CTFontCopyPostScriptName(f) as String) == (CTFontCopyPostScriptName(primary) as String) {
        optTop = min(optTop, baselineTop - CTFontGetCapHeight(f))
        optBot = max(optBot, baselineTop)
    } else {
        let b = CTRunGetImageBounds(run, ctx, CFRange(location: 0, length: 0))
        optTop = min(optTop, CGFloat(H) - b.maxY)
        optBot = max(optBot, CGFloat(H) - b.minY)
    }
}
let ink = CTLineGetImageBounds(line, ctx)

guard let img = ctx.makeImage(),
      let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: outPath) as CFURL,
                                                 UTType.png.identifier as CFString, 1, nil) else { fail("cannot write \(outPath)") }
CGImageDestinationAddImage(dest, img, nil)
if !CGImageDestinationFinalize(dest) { fail("cannot finalize \(outPath)") }

let out: [String: Any] = [
    "w": W, "h": H, "baseline": Double(baselineTop), "advance": Double(advance), "pad": Double(pad),
    "ink": [Double(ink.minX), Double(CGFloat(H) - ink.maxY), Double(ink.maxX), Double(CGFloat(H) - ink.minY)],
    "optical": [Double(optTop), Double(optBot)],
    "runs": runsOut,
]
let data = try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys])
print(String(data: data, encoding: .utf8)!)
