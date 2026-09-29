// CoreText renderer used for the font comparison (same text engine iOS uses).
// Usage: ctrender jobs.json outdir   (optional per job: "track": extra advance after every glyph, render px)
// jobs.json: [{"id":..,"font":path,"ps":postscriptName|null,"axes":{"wght":700,"opsz":16}|null,
//             "cap":targetCapHeightPx (already x SS),"text":..,"H":canvasHeightPx,"base":baselineFromTopPx,"x":leftPenX}]
// Font size is chosen so that the measured bounding height of glyph 'H' equals `cap`.
// Writes <id>.raw (8-bit coverage, width x H) and prints one JSON line per job with width, size and metrics.
import Foundation
import CoreText
import CoreGraphics

func tag(_ s: String) -> Int { var v = 0; for c in s.utf8 { v = (v << 8) | Int(c) }; return v }

struct Job: Decodable { let id: String; let font: String; let ps: String?; let axes: [String: Double]?
    let cap: Double; let text: String; let H: Int; let base: Double; let x: Double; let track: Double? }

let args = CommandLine.arguments
let jobs = try! JSONDecoder().decode([Job].self, from: Data(contentsOf: URL(fileURLWithPath: args[1])))
let outdir = args[2]
var descCache: [String: [CTFontDescriptor]] = [:]

func descriptor(_ j: Job) -> CTFontDescriptor {
    let arr: [CTFontDescriptor]
    if let c = descCache[j.font] { arr = c } else {
        arr = CTFontManagerCreateFontDescriptorsFromURL(URL(fileURLWithPath: j.font) as CFURL) as! [CTFontDescriptor]
        descCache[j.font] = arr
    }
    var d = arr[0]
    if let ps = j.ps {
        for x in arr { if (CTFontDescriptorCopyAttribute(x, kCTFontNameAttribute) as! String) == ps { d = x } }
    }
    if let axes = j.axes {
        var v: [NSNumber: NSNumber] = [:]
        for (k, val) in axes { v[NSNumber(value: tag(k))] = NSNumber(value: val) }
        d = CTFontDescriptorCreateCopyWithAttributes(d, [kCTFontVariationAttribute: v] as CFDictionary)
    }
    return d
}

func glyphHeight(_ f: CTFont, _ ch: UniChar) -> Double {
    var c = ch; var g: CGGlyph = 0
    CTFontGetGlyphsForCharacters(f, &c, &g, 1)
    var r = CGRect.zero
    CTFontGetBoundingRectsForGlyphs(f, .horizontal, &g, &r, 1)
    return Double(r.height)
}

for j in jobs {
    let d = descriptor(j)
    let ref = CTFontCreateWithFontDescriptor(d, 1000, nil)
    let capU = glyphHeight(ref, UniChar(UnicodeScalar("H").value))
    let xU = glyphHeight(ref, UniChar(UnicodeScalar("x").value))
    let size = j.cap / capU * 1000
    let font = CTFontCreateWithFontDescriptor(d, CGFloat(size), nil)
    var at: [NSAttributedString.Key: Any] = [kCTFontAttributeName as NSAttributedString.Key: font,
        kCTForegroundColorFromContextAttributeName as NSAttributedString.Key: true]
    if let t = j.track { at[kCTKernAttributeName as NSAttributedString.Key] = NSNumber(value: t) }   // tracking in render px (SwiftUI .tracking)
    let attr = NSAttributedString(string: j.text, attributes: at)
    let line = CTLineCreateWithAttributedString(attr)
    let adv = CTLineGetTypographicBounds(line, nil, nil, nil)
    let W = Int(ceil(j.x + adv + j.cap)) + 8
    let ctx = CGContext(data: nil, width: W, height: j.H, bitsPerComponent: 8, bytesPerRow: W,
                        space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue)!
    ctx.setFillColor(gray: 0, alpha: 1); ctx.fill(CGRect(x: 0, y: 0, width: W, height: j.H))
    ctx.setShouldAntialias(true); ctx.setShouldSmoothFonts(false)
    ctx.setAllowsFontSubpixelPositioning(true); ctx.setShouldSubpixelPositionFonts(true)
    ctx.setAllowsFontSubpixelQuantization(false); ctx.setShouldSubpixelQuantizeFonts(false)
    ctx.setFillColor(gray: 1, alpha: 1)
    ctx.textPosition = CGPoint(x: j.x, y: Double(j.H) - j.base)
    CTLineDraw(line, ctx)
    let buf = Data(bytes: ctx.data!, count: W * j.H)
    try! buf.write(to: URL(fileURLWithPath: "\(outdir)/\(j.id).raw"))
    let psn = CTFontCopyPostScriptName(font) as String
    let o: [String: Any] = ["id": j.id, "W": W, "H": j.H, "size": size, "ps": psn, "capU": capU, "xU": xU,
        "os2cap": Double(CTFontGetCapHeight(ref)), "os2x": Double(CTFontGetXHeight(ref)), "adv": adv]
    print(String(data: try! JSONSerialization.data(withJSONObject: o), encoding: .utf8)!)
}
