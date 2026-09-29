// vgrab — random-access frame grabber for the owner's gameplay videos (constant-frame-rate mp4, 592x1280).
// Build: swiftc -O -o vgrab vgrab.swift        (the binary is gitignored via research/video-tools/.gitignore)
//
//   vgrab V OUTDIR [opts] T[:NAME] T[:NAME] ...      grab exact frames (AVAssetImageGenerator, tolerance 0)
//   vgrab V OUTDIR [opts] @times.txt                 same, one "T[ NAME]" per line
//   vgrab V info                                     duration / size / fps
//   opts: --width W   (default: full 592)           --crop x y w h   (FULL-RES PIXELS, top-left origin)
//         --jpg        (default png)                  --quiet
// V may be a path or the alias V1 / V2 (the owner's videos under research/video/owner/).
// Output: OUTDIR/NAME.png (NAME defaults to t<ms>, e.g. t0123450.png). Prints one line per frame:
//   <requested> <actual> <path>
// Zero tolerance = the decoder rolls forward from the previous keyframe, so every requested time is honoured to the frame
// (actual = the presentation time of the frame shown at the requested time). Random access costs ~20-80 ms per frame.

import AVFoundation
import AppKit
import UniformTypeIdentifiers

func die(_ s: String) -> Never { FileHandle.standardError.write((s + "\n").data(using: .utf8)!); exit(1) }

let here = URL(fileURLWithPath: CommandLine.arguments[0]).deletingLastPathComponent()
let ownerDir = "/Users/yago/Downloads/app-factory/apps/mazeout/research/video/owner/"
let alias = ["V1": ownerDir + "V1-levels-01-20.mp4", "V2": ownerDir + "V2-levels-11-38.mp4"]

var args = Array(CommandLine.arguments.dropFirst())
guard args.count >= 2 else { die("usage: vgrab V1|V2|path OUTDIR [--width W] [--crop x y w h] [--jpg] T[:NAME]... | @file") }
let vpath = alias[args[0]] ?? args[0]
let asset = AVURLAsset(url: URL(fileURLWithPath: vpath), options: [AVURLAssetPreferPreciseDurationAndTimingKey: true])
guard let track = asset.tracks(withMediaType: .video).first else { die("no video track in \(vpath)") }

if args[1] == "info" {
    print(String(format: "duration %.3f s  size %.0fx%.0f  fps %.3f", CMTimeGetSeconds(asset.duration),
                 track.naturalSize.width, track.naturalSize.height, track.nominalFrameRate))
    exit(0)
}

let outDir = args[1]
var width: Int? = nil
var crop: CGRect? = nil
var jpg = false
var quiet = false
var reqs: [(Double, String?)] = []
var i = 2
while i < args.count {
    let a = args[i]
    if a == "--width" { width = Int(args[i + 1]); i += 2; continue }
    if a == "--crop" {
        let v = args[(i + 1)...(i + 4)].map { CGFloat(Double($0)!) }
        crop = CGRect(x: v[0], y: v[1], width: v[2], height: v[3]); i += 5; continue
    }
    if a == "--jpg" { jpg = true; i += 1; continue }
    if a == "--quiet" { quiet = true; i += 1; continue }
    if a.hasPrefix("@") {
        guard let txt = try? String(contentsOfFile: String(a.dropFirst()), encoding: .utf8) else { die("cannot read \(a)") }
        for line in txt.split(separator: "\n") {
            let p = line.split(separator: " ", omittingEmptySubsequences: true)
            guard let first = p.first, let t = Double(first) else { continue }
            reqs.append((t, p.count > 1 ? String(p[1]) : nil))
        }
        i += 1; continue
    }
    let p = a.split(separator: ":", maxSplits: 1)
    guard let t = Double(p[0]) else { die("bad time \(a)") }
    reqs.append((t, p.count > 1 ? String(p[1]) : nil))
    i += 1
}
try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)

let gen = AVAssetImageGenerator(asset: asset)
gen.requestedTimeToleranceBefore = .zero
gen.requestedTimeToleranceAfter = .zero
gen.appliesPreferredTrackTransform = true
let fps = Double(track.nominalFrameRate)

func save(_ cg: CGImage, _ path: String) {
    let url = URL(fileURLWithPath: path)
    let type = jpg ? UTType.jpeg.identifier : UTType.png.identifier
    guard let dest = CGImageDestinationCreateWithURL(url as CFURL, type as CFString, 1, nil) else { die("cannot write \(path)") }
    CGImageDestinationAddImage(dest, cg, jpg ? ([kCGImageDestinationLossyCompressionQuality: 0.9] as CFDictionary) : nil)
    CGImageDestinationFinalize(dest)
}

func transform(_ cg: CGImage) -> CGImage {
    var img = cg
    if let c = crop, let cc = img.cropping(to: c.integral) { img = cc }
    if let w = width, w != img.width {
        let h = Int((Double(img.height) * Double(w) / Double(img.width)).rounded())
        let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                            space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
        ctx.interpolationQuality = .high
        ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
        img = ctx.makeImage()!
    }
    return img
}

for (t, name) in reqs {
    // aim at the middle of the frame interval so float rounding never lands on the neighbour frame
    let tt = CMTime(seconds: t, preferredTimescale: 60000)
    var actual = CMTime.zero
    do {
        let cg = try gen.copyCGImage(at: tt, actualTime: &actual)
        let nm = name ?? String(format: "t%07d", Int((t * 1000).rounded()))
        let path = outDir + "/" + nm + (jpg ? ".jpg" : ".png")
        save(transform(cg), path)
        if !quiet { print(String(format: "%.3f %.3f %@", t, CMTimeGetSeconds(actual), path)) }
    } catch {
        FileHandle.standardError.write("grab failed at \(t): \(error)\n".data(using: .utf8)!)
    }
}
_ = fps
_ = here
