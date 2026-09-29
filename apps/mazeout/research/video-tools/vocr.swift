// vocr — Vision text reader for video frames (model: apps/matchfactory/tools/bench/hudocr.swift).
// Build: swiftc -O -o vocr vocr.swift
//
//   vocr [--crop x y w h] [--scale S] [--fast] [--lang en-US] IMG...
//     --crop  region in PIXELS of the image (top-left origin); default = whole image
//     --scale upscale the (cropped) region by S before recognition (small HUD text reads better at 2-3x)
// Output: one JSON object per image, one line each:
//   {"file": ..., "lines": ["Level 12", ...], "words": [{"s": "Level 12", "conf": 0.98, "box": [x, y, w, h]}, ...]}
// Boxes are in PIXELS of the original image (top-left origin). Rows are grouped top to bottom, words left to right.

import Foundation
import Vision
import CoreGraphics
import ImageIO

var args = Array(CommandLine.arguments.dropFirst())
var crop: CGRect? = nil
var scale: CGFloat = 1
var fast = false
var langs = ["en-US"]
var files: [String] = []
var i = 0
while i < args.count {
    switch args[i] {
    case "--crop":
        let v = args[(i + 1)...(i + 4)].map { CGFloat(Double($0)!) }
        crop = CGRect(x: v[0], y: v[1], width: v[2], height: v[3]); i += 5
    case "--scale": scale = CGFloat(Double(args[i + 1])!); i += 2
    case "--fast": fast = true; i += 1
    case "--lang": langs = args[i + 1].split(separator: ",").map(String.init); i += 2
    default: files.append(args[i]); i += 1
    }
}

func upscale(_ img: CGImage, _ s: CGFloat) -> CGImage {
    if s == 1 { return img }
    let w = Int(CGFloat(img.width) * s), h = Int(CGFloat(img.height) * s)
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.interpolationQuality = .high
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
    return ctx.makeImage()!
}

for path in files {
    let url = URL(fileURLWithPath: path)
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let full = CGImageSourceCreateImageAtIndex(src, 0, nil) else {
        print("{\"file\": \"\(path)\", \"error\": \"unreadable\"}"); continue
    }
    var region = CGRect(x: 0, y: 0, width: full.width, height: full.height)
    var img = full
    if let c = crop, let cc = full.cropping(to: c.integral) { img = cc; region = c.integral }
    img = upscale(img, scale)
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = fast ? .fast : .accurate
    req.usesLanguageCorrection = false
    req.recognitionLanguages = langs
    req.minimumTextHeight = 0
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    try? handler.perform([req])
    var rows: [(y: CGFloat, words: [(x: CGFloat, s: String)])] = []
    var words: [[String: Any]] = []
    for o in req.results ?? [] {
        guard let cand = o.topCandidates(1).first else { continue }
        let b = o.boundingBox        // normalised, bottom-left origin, in the (cropped) image
        let bx = region.minX + b.minX * region.width
        let by = region.minY + (1 - b.maxY) * region.height
        words.append(["s": cand.string, "conf": Double(cand.confidence),
                      "box": [Int(bx), Int(by), Int(b.width * region.width), Int(b.height * region.height)]])
        if let k = rows.firstIndex(where: { abs($0.y - b.midY) < b.height * 0.5 }) {
            rows[k].words.append((b.minX, cand.string))
        } else {
            rows.append((b.midY, [(b.minX, cand.string)]))
        }
    }
    let lines = rows.sorted { $0.y > $1.y }.map { $0.words.sorted { $0.x < $1.x }.map(\.s).joined(separator: " ") }
    let obj: [String: Any] = ["file": path, "lines": lines, "words": words]
    if let d = try? JSONSerialization.data(withJSONObject: obj), let s = String(data: d, encoding: .utf8) { print(s) }
}
