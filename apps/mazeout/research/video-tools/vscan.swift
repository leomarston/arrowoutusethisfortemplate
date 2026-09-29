// vscan — streaming per-frame feature scanner for the owner's gameplay videos (no frames written to disk).
// Build: swiftc -O -o vscan vscan.swift
//
//   vscan V1|V2|path START END FPS > out.jsonl        (FPS 0 = every decoded frame)
//
// Seeks with AVAssetReader.timeRange (the owner's mp4s are constant-frame-rate, no short edit list), decodes BGRA at full
// res (592x1280) and prints one JSON object per sampled frame. All coordinates are FULL-RES PIXELS (top-left origin);
// the per-pixel work samples every 2nd pixel in x and y ("samples" below = half-res pixels).
//   t      presentation time (s)
//   lum    mean luma of the frame (0-255)
//   bg     fraction of the play band (y 200-1120) that is the light-blue board background (239,245,255 +-)
//   dark   fraction of the frame with max(R,G,B) < 70 (popups / win splash / dim overlays)
//   gbot   fraction of green (booster buttons) in y 1120-1260
//   ink    blue-stroke samples in the play band y 180-1130 (B>200, R<100, 70<G<180)
//   ibox   bounding box of the ink samples [x0,y0,x1,y1] (full-res px) or null
//   col    saturated NON-blue samples in the play band (obstacles, exit trails, particles)
//   hrt    red fraction in the 3 HUD heart slots (x 325/379/433, y 133; 30x30 px boxes)
//   btn    mean RGB of the HUD back button (x 38-62, y 120-146): blue = normal, red = Hard, purple = Super Hard
//   tch    touch-indicator blobs [[cx, cy, samples], ...]: grey (B-R<22, 150<mean<234, sat<34) round blobs in y 170-1262
//          whose bbox is 12-36 samples wide and tall and area 50-800 samples (the iOS screen-recording touch disc); only
//          TRANSIENT grey counts (not grey in the frame 0.25-0.3 s earlier), so static grey art never forms a blob
//   tmr    timer-digit signature: mean luma of 8x2 blocks over x 190-282, y 116-150 (changes when the timer ticks)

import AVFoundation
import CoreVideo
import Foundation

func die(_ s: String) -> Never { FileHandle.standardError.write((s + "\n").data(using: .utf8)!); exit(1) }
let ownerDir = "/Users/yago/Downloads/app-factory/apps/mazeout/research/video/owner/"
let alias = ["V1": ownerDir + "V1-levels-01-20.mp4", "V2": ownerDir + "V2-levels-11-38.mp4"]
let a = CommandLine.arguments
guard a.count >= 5 else { die("usage: vscan V START END FPS") }
let path = alias[a[1]] ?? a[1]
let start = Double(a[2])!, end = Double(a[3])!, fps = Double(a[4])!
let asset = AVURLAsset(url: URL(fileURLWithPath: path))
guard let track = asset.tracks(withMediaType: .video).first else { die("no video") }
let reader = try! AVAssetReader(asset: asset)
let out = AVAssetReaderTrackOutput(track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
out.alwaysCopiesSampleData = false
reader.add(out)
reader.timeRange = CMTimeRange(start: CMTime(seconds: max(0, start - 0.5), preferredTimescale: 600),
                               end: CMTime(seconds: end + 0.1, preferredTimescale: 600))
reader.startReading()

var nextT = start
let step = fps > 0 ? 1.0 / fps : 0
var outBuf = ""
var greyHist: [(Double, [UInt8])] = []      // grey masks of the last ~0.35 s (static grey art is subtracted from the touch mask)
func flush() { FileHandle.standardOutput.write(outBuf.data(using: .utf8)!); outBuf = "" }

while let sb = out.copyNextSampleBuffer() {
    let t = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sb))
    if !t.isFinite || t > end + 0.0005 { continue }
    if t + 0.004 < nextT { continue }
    if step > 0 { while nextT <= t + 0.004 { nextT += step } }
    guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
    CVPixelBufferLockBaseAddress(pb, .readOnly)
    let W = CVPixelBufferGetWidth(pb), H = CVPixelBufferGetHeight(pb)
    let bpr = CVPixelBufferGetBytesPerRow(pb)
    let base = CVPixelBufferGetBaseAddress(pb)!.assumingMemoryBound(to: UInt8.self)
    @inline(__always) func px(_ x: Int, _ y: Int) -> (Int, Int, Int) {
        let p = base + y * bpr + x * 4
        return (Int(p[2]), Int(p[1]), Int(p[0]))   // BGRA -> RGB
    }
    let sw = W / 2, sh = H / 2
    var lumSum = 0, n = 0, darkN = 0
    var bgN = 0, bandN = 0, inkN = 0, colN = 0, gN = 0, gTot = 0
    var ix0 = Int.max, iy0 = Int.max, ix1 = -1, iy1 = -1
    var grey = [UInt8](repeating: 0, count: sw * sh)
    for sy in 0..<sh {
        let y = sy * 2
        for sx in 0..<sw {
            let x = sx * 2
            let (r, g, b) = px(x, y)
            let mx = max(r, max(g, b)), mn = min(r, min(g, b))
            lumSum += (r * 299 + g * 587 + b * 114) / 1000; n += 1
            if mx < 70 { darkN += 1 }
            if y >= 200 && y < 1120 {
                bandN += 1
                if abs(r - 239) < 14 && abs(g - 245) < 12 && b > 243 { bgN += 1 }
            }
            if y >= 180 && y < 1130 {
                let isInk = b > 200 && r < 100 && g > 70 && g < 180
                if isInk {
                    inkN += 1
                    if x < ix0 { ix0 = x }; if x > ix1 { ix1 = x }
                    if y < iy0 { iy0 = y }; if y > iy1 { iy1 = y }
                } else if mx - mn > 90 && !(b >= r && b >= g && b - r > 120) {
                    colN += 1
                }
            }
            if y >= 170 && y < 1262 {
                let mean = (r + g + b) / 3
                if b - r < 22 && b - r > -12 && mean > 150 && mean < 234 && mx - mn < 34 { grey[sy * sw + sx] = 1 }
            }
            if y >= 1120 && y < 1260 {
                gTot += 1
                if g > 150 && r < 130 && b < 110 { gN += 1 }
            }
        }
    }
    // hearts
    var hrt: [Double] = []
    for cx in [325, 379, 433] {
        var red = 0, tot = 0
        for y in stride(from: 118, to: 148, by: 2) { for x in stride(from: cx - 15, to: cx + 15, by: 2) {
            let (r, g, b) = px(x, y); tot += 1
            if r > 190 && g < 90 && b < 100 { red += 1 }
        } }
        hrt.append(Double(red) / Double(tot))
    }
    var tmr: [Int] = []
    for by in 0..<2 { for bx in 0..<8 {
        var sum = 0, cnt = 0
        for y in stride(from: 116 + by * 17, to: 116 + by * 17 + 17, by: 1) { for x in stride(from: 190 + bx * 11, to: 190 + bx * 11 + 11, by: 1) {
            let (r, g, b) = px(x, y); sum += (r + g + b) / 3; cnt += 1 } }
        tmr.append(sum / cnt)
    } }
    var br = 0, bgc = 0, bb = 0, bn = 0
    for y in stride(from: 120, to: 146, by: 2) { for x in stride(from: 38, to: 62, by: 2) {
        let (r, g, b) = px(x, y); br += r; bgc += g; bb += b; bn += 1
    } }
    CVPixelBufferUnlockBaseAddress(pb, .readOnly)
    // touch blobs: 4-connected components on the grey mask
    var tch: [String] = []
    // keep only TRANSIENT grey: pixels that were not grey (+-1 sample) in the frame >= 0.3 s ago (static grey art: box shadows,
    // bombs, HUD chrome). The touch disc lives ~0.1-0.25 s, so it survives; static greys vanish.
    greyHist.append((t, grey))
    var ref: [UInt8]? = nil
    while greyHist.count > 1 && greyHist[1].0 <= t - 0.3 { greyHist.removeFirst() }
    if greyHist.count > 1 && greyHist[0].0 <= t - 0.25 { ref = greyHist[0].1 }
    if let old = ref {
        var cur = grey
        for y in 0..<sh { for x in 0..<sw where cur[y * sw + x] == 1 {
            var hit = false
            for dy in -1...1 { for dx in -1...1 {
                let nx = x + dx, ny = y + dy
                if nx >= 0 && ny >= 0 && nx < sw && ny < sh && old[ny * sw + nx] == 1 { hit = true }
            } }
            if hit { cur[y * sw + x] = 0 }
        } }
        grey = cur
    }
    // close gaps (an arrow stroke under the disc splits it): dilate by 3 samples, label the dilated mask, measure the original
    var dil = [UInt8](repeating: 0, count: sw * sh)
    var tmp = [UInt8](repeating: 0, count: sw * sh)
    let R = 3
    for y in 0..<sh { var run = 0; var x = 0
        // horizontal max filter
        while x < sw { if grey[y * sw + x] == 1 { let a0 = max(0, x - R), a1 = min(sw - 1, x + R); for k in a0...a1 { tmp[y * sw + k] = 1 } }; x += 1 }
        _ = run; run = 0 }
    for x in 0..<sw { for y in 0..<sh where tmp[y * sw + x] == 1 {
        let a0 = max(0, y - R), a1 = min(sh - 1, y + R); for k in a0...a1 { dil[k * sw + x] = 1 } } }
    var seen = [Bool](repeating: false, count: sw * sh)
    var stack: [Int] = []
    for i in 0..<(sw * sh) where dil[i] == 1 && !seen[i] {
        seen[i] = true; stack.removeAll(keepingCapacity: true); stack.append(i)
        var cnt = 0, sxs = 0, sys = 0, x0 = Int.max, x1 = -1, y0 = Int.max, y1 = -1
        var tot = 0
        while let j = stack.popLast() {
            let x = j % sw, y = j / sw
            tot += 1
            if grey[j] == 1 {
                cnt += 1; sxs += x; sys += y
                if x < x0 { x0 = x }; if x > x1 { x1 = x }; if y < y0 { y0 = y }; if y > y1 { y1 = y }
            }
            if tot > 8000 { continue }
            for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
                let nx = x + dx, ny = y + dy
                if nx < 0 || ny < 0 || nx >= sw || ny >= sh { continue }
                let k = ny * sw + nx
                if dil[k] == 1 && !seen[k] { seen[k] = true; stack.append(k) }
            }
        }
        let bw = x1 - x0 + 1, bh = y1 - y0 + 1
        if cnt >= 50 && cnt <= 800 && bw >= 12 && bw <= 36 && bh >= 12 && bh <= 36 && tot < 8000 {
            let fill = Double(cnt) / Double(bw * bh)
            if fill > 0.35 {
                tch.append(String(format: "[%d,%d,%d]", Int(Double(sxs) / Double(cnt) * 2), Int(Double(sys) / Double(cnt) * 2), cnt))
            }
        }
    }
    let ibox = ix1 >= 0 ? "[\(ix0),\(iy0),\(ix1),\(iy1)]" : "null"
    outBuf += String(format: "{\"t\":%.3f,\"lum\":%.1f,\"bg\":%.3f,\"dark\":%.3f,\"gbot\":%.3f,\"ink\":%d,\"ibox\":%@,\"col\":%d,\"hrt\":[%.2f,%.2f,%.2f],\"btn\":[%d,%d,%d],\"tch\":[%@],\"tmr\":[%@]}\n",
                     t, Double(lumSum) / Double(n), Double(bgN) / Double(max(1, bandN)), Double(darkN) / Double(n),
                     Double(gN) / Double(max(1, gTot)), inkN, ibox, colN, hrt[0], hrt[1], hrt[2],
                     br / bn, bgc / bn, bb / bn, tch.joined(separator: ","), tmr.map(String.init).joined(separator: ","))
    if outBuf.count > 1 << 16 { flush() }
}
flush()
