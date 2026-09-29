// VERIFY (GAMEPROMPT §3.5 "OCR", §8.3 "Performance"): reads text out of simulator or phone screenshots with Vision
// (VNRecognizeTextRequest). tools/bench/bench.py compiles it on demand to read the board's debug HUD (`-pc.hud debug`:
// fps / p95 / p99 over the last 600 frames, the in-app footprint), so the bench samples frame times without touching the
// app process. Also usable for HUD numbers in research shots (the timer "3:00", coins "2240", "Level 32").
// Host-only macOS CLI:  swiftc -O -o build/bench/.tools/hudocr tools/bench/hudocr.swift
//
// usage: hudocr [--full | --crop x,y,w,h] <png>...   ->  one JSON object per line: {"file": ..., "lines": ["...", ...]}
// The crop is in points of the 393 pt-wide reference screen (scaled by the image width / 393). Default crop: the band
// (0, 95, 260, 60), where Match Factory drew its debug HUD; bench.py passes HUD_CROP, BOARD's real HUD position.
// Adapted from apps/matchfactory/tools/bench/hudocr.swift (05424db): only the --crop option is new (design/REUSE.md).

import Foundation
import Vision
import CoreGraphics
import ImageIO

func lines(in url: URL, fullFrame: Bool, cropPt: CGRect) -> [String] {
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let full = CGImageSourceCreateImageAtIndex(src, 0, nil) else { return [] }
    let scale = CGFloat(full.width) / 393.0                       // reference width in pt
    let crop = CGRect(x: cropPt.minX * scale, y: cropPt.minY * scale,
                      width: cropPt.width * scale, height: cropPt.height * scale).integral
    guard let img = fullFrame ? full : full.cropping(to: crop) else { return [] }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    req.recognitionLanguages = ["en-US"]
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    try? handler.perform([req])
    // Vision may return one observation per word: group them into rows (top row first), each row left to right.
    var rows: [(y: CGFloat, words: [(x: CGFloat, s: String)])] = []
    for o in req.results ?? [] {
        guard let s = o.topCandidates(1).first?.string else { continue }
        let b = o.boundingBox
        if let i = rows.firstIndex(where: { abs($0.y - b.midY) < b.height * 0.5 }) {
            rows[i].words.append((b.minX, s))
        } else {
            rows.append((b.midY, [(b.minX, s)]))
        }
    }
    return rows.sorted { $0.y > $1.y }.map { $0.words.sorted { $0.x < $1.x }.map(\.s).joined(separator: " ") }
}

var args = Array(CommandLine.arguments.dropFirst())
var fullFrame = false
var cropPt = CGRect(x: 0, y: 95, width: 260, height: 60)
var paths: [String] = []
var i = 0
while i < args.count {
    let a = args[i]
    if a == "--full" {
        fullFrame = true
    } else if a == "--crop", i + 1 < args.count {
        let v = args[i + 1].split(separator: ",").compactMap { Double($0.trimmingCharacters(in: .whitespaces)) }
        guard v.count == 4 else { FileHandle.standardError.write("hudocr: --crop wants x,y,w,h in pt\n".data(using: .utf8)!); exit(64) }
        cropPt = CGRect(x: v[0], y: v[1], width: v[2], height: v[3])
        i += 1
    } else {
        paths.append(a)
    }
    i += 1
}
if paths.isEmpty {
    FileHandle.standardError.write("usage: hudocr [--full | --crop x,y,w,h] <png>...\n".data(using: .utf8)!)
    exit(64)
}
for path in paths {
    let url = URL(fileURLWithPath: path)
    let obj: [String: Any] = ["file": path, "lines": lines(in: url, fullFrame: fullFrame, cropPt: cropPt)]
    if let data = try? JSONSerialization.data(withJSONObject: obj), let s = String(data: data, encoding: .utf8) {
        print(s)
    }
}
