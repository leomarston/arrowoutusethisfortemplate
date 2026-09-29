// ocr IMAGE [x0 y0 x1 y1 in pt of a 393-wide screen]  → one line per recognised text: "x y w h | text" (pt, top-left origin)
import Foundation
import Vision
import AppKit
let args = CommandLine.arguments
guard args.count >= 2, let img = NSImage(contentsOfFile: args[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("usage: ocr IMAGE [x0 y0 x1 y1]"); exit(1) }
let W = Double(cg.width), H = Double(cg.height), S = W / 393.0
var crop = cg
var ox = 0.0, oy = 0.0
if args.count >= 6, let x0 = Double(args[2]), let y0 = Double(args[3]), let x1 = Double(args[4]), let y1 = Double(args[5]) {
    ox = x0; oy = y0
    crop = cg.cropping(to: CGRect(x: x0 * S, y: y0 * S, width: (x1 - x0) * S, height: (y1 - y0) * S))!
}
let cw = Double(crop.width) / S, ch = Double(crop.height) / S
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false
req.recognitionLanguages = ["en-US", "tr-TR"]
let h = VNImageRequestHandler(cgImage: crop, options: [:])
try? h.perform([req])
var rows: [(Double, Double, Double, Double, String)] = []
for o in req.results ?? [] {
    guard let c = o.topCandidates(1).first else { continue }
    let b = o.boundingBox
    rows.append((ox + b.minX * cw, oy + (1 - b.maxY) * ch, b.width * cw, b.height * ch, c.string))
}
rows.sort { abs($0.1 - $1.1) > 6 ? $0.1 < $1.1 : $0.0 < $1.0 }
for r in rows { print(String(format: "%5.0f %5.0f %4.0f %3.0f | ", r.0, r.1, r.2, r.3) + r.4) }
