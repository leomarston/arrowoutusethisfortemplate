#!/usr/bin/env swift
//
//  textpng.swift — render a line of text to a transparent PNG using CoreText.
//
//  Why this exists: PIL cannot do complex text layout. Its wheels ship without
//  Raqm/HarfBuzz, so Indic vowel reordering (ि displays BEFORE the consonant it
//  follows in memory), conjunct ligatures, Thai mark stacking and Arabic/Nastaliq
//  joining all come out wrong — and wrong in a way that still renders, so a
//  pixel-count check calls it a pass. CoreText is the engine iOS itself uses:
//  it shapes every script correctly and falls back through the system font
//  cascade automatically, so there is no per-script font table to maintain.
//
//  Usage:
//    textpng --text "..." --size 90 --out cap.png [--locale ja] [--color FFFFFF]
//            [--weight heavy|bold|semibold|regular] [--maxwidth 1100] [--minsize 40]
//
//  Prints "<width>x<height>" of the rendered image to stdout.
//
import CoreGraphics
import CoreText
import Foundation
import ImageIO
import UniformTypeIdentifiers

func arg(_ name: String) -> String? {
    let a = CommandLine.arguments
    guard let i = a.firstIndex(of: "--" + name), i + 1 < a.count else { return nil }
    return a[i + 1]
}

guard let text = arg("text"), let outPath = arg("out") else {
    FileHandle.standardError.write("usage: textpng --text T --out F [--size N] …\n".data(using: .utf8)!)
    exit(2)
}
let requested = CGFloat(Double(arg("size") ?? "90") ?? 90)
let minSize   = CGFloat(Double(arg("minsize") ?? "24") ?? 24)
let maxWidth  = CGFloat(Double(arg("maxwidth") ?? "0") ?? 0)
let locale    = arg("locale")
let weight    = arg("weight") ?? "heavy"
let hex       = arg("color") ?? "FFFFFF"

func color(_ h: String) -> CGColor {
    var v: UInt64 = 0xFFFFFF
    Scanner(string: h.replacingOccurrences(of: "#", with: "")).scanHexInt64(&v)
    return CGColor(red: CGFloat((v >> 16) & 0xFF) / 255,
                   green: CGFloat((v >> 8) & 0xFF) / 255,
                   blue: CGFloat(v & 0xFF) / 255, alpha: 1)
}

let ctWeight: CGFloat = {
    switch weight {
    case "regular":  return 0.0
    case "semibold": return 0.3
    case "bold":     return 0.4
    default:         return 0.56          // heavy — matches SF Pro Display Heavy
    }
}()

/// Build an attributed line. `kCTLanguageAttributeName` matters for Han: without it
/// CoreText may pick the Japanese glyph shapes for a Simplified Chinese string.
func makeLine(_ size: CGFloat) -> CTLine {
    let base = CTFontCreateUIFontForLanguage(.system, size, locale as CFString?)
        ?? CTFontCreateWithName("Helvetica" as CFString, size, nil)
    let traits: [CFString: Any] = [kCTFontWeightTrait: ctWeight]
    let desc = CTFontDescriptorCreateWithAttributes([
        kCTFontTraitsAttribute: traits,
    ] as CFDictionary)
    let font = CTFontCreateCopyWithAttributes(base, size, nil, desc)

    var attrs: [CFString: Any] = [
        kCTFontAttributeName: font,
        kCTForegroundColorAttributeName: color(hex),
    ]
    if let locale { attrs[kCTLanguageAttributeName] = locale as CFString }
    let attributed = CFAttributedStringCreate(nil, text as CFString, attrs as CFDictionary)!
    return CTLineCreateWithAttributedString(attributed)
}

// Shrink to fit if a max width was given — same behaviour as the Python `fit()`.
var size = requested
var line = makeLine(size)
if maxWidth > 0 {
    while size > minSize {
        let w = CGFloat(CTLineGetTypographicBounds(line, nil, nil, nil))
        if w <= maxWidth { break }
        size -= 2
        line = makeLine(size)
    }
}

var ascent: CGFloat = 0, descent: CGFloat = 0, leading: CGFloat = 0
let width = CGFloat(CTLineGetTypographicBounds(line, &ascent, &descent, &leading))
// Indic and Thai stack marks well above the nominal ascent; pad generously or they clip.
let padX: CGFloat = 8, padY: CGFloat = max(10, size * 0.28)
let w = Int(ceil(width + padX * 2))
let h = Int(ceil(ascent + descent + padY * 2))
guard w > 0, h > 0 else { FileHandle.standardError.write("empty text\n".data(using: .utf8)!); exit(3) }

let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                    space: CGColorSpaceCreateDeviceRGB(),
                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.setAllowsAntialiasing(true)
ctx.setShouldSmoothFonts(true)
ctx.textPosition = CGPoint(x: padX, y: descent + padY)
CTLineDraw(line, ctx)

guard let image = ctx.makeImage(),
      let dest = CGImageDestinationCreateWithURL(
        URL(fileURLWithPath: outPath) as CFURL, UTType.png.identifier as CFString, 1, nil)
else { exit(4) }
CGImageDestinationAddImage(dest, image, nil)
guard CGImageDestinationFinalize(dest) else { exit(5) }
print("\(w)x\(h)")
