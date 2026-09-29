// frames2 <in.mov> <outdir> [fps=30] [start=0] [end=1e9] [scale=1.0]
// Decodes EVERY video sample with AVAssetReader (ignores the movie's edit list / asset.duration, which the phone
// capture writes too short) and saves PNGs named by presentation time in ms (t%07d.png), at most `fps` per second.
// Also prints the PTS range and every gap > 100 ms (static screen = no frames from the capture device).
import AVFoundation
import CoreImage
import AppKit
let a = CommandLine.arguments
guard a.count >= 3 else { print("usage: frames2 in.mov outdir [fps] [start] [end] [scale]"); exit(1) }
let fps = a.count > 3 ? Double(a[3])! : 30
let t0 = a.count > 4 ? Double(a[4])! : 0
let t1 = a.count > 5 ? Double(a[5])! : 1e9
let scale = a.count > 6 ? Double(a[6])! : 1.0
let asset = AVURLAsset(url: URL(fileURLWithPath: a[1]))
guard let vt = asset.tracks(withMediaType: .video).first else { print("no video"); exit(2) }
let r = try! AVAssetReader(asset: asset)
let o = AVAssetReaderTrackOutput(track: vt, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
r.add(o); r.startReading()
try? FileManager.default.createDirectory(atPath: a[2], withIntermediateDirectories: true)
let ctx = CIContext()
var frames: [(Double, CVPixelBuffer)] = []
var all: [Double] = []
var lastSaved = -1e9
var n = 0
while let sb = o.copyNextSampleBuffer() {
    let t = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sb))
    guard t.isFinite, let px = CMSampleBufferGetImageBuffer(sb) else { continue }
    all.append(t)
    if t < t0 || t > t1 { continue }
    if t - lastSaved < 1.0 / fps - 0.002 { continue }
    lastSaved = t
    var ci = CIImage(cvPixelBuffer: px)
    if scale != 1.0 { ci = ci.transformed(by: CGAffineTransform(scaleX: scale, y: scale)) }
    if let cg = ctx.createCGImage(ci, from: ci.extent) {
        let rep = NSBitmapImageRep(cgImage: cg)
        let name = String(format: "%@/t%07d.png", a[2], Int((t * 1000).rounded()))
        try? rep.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: name))
        n += 1
    }
}
all.sort()
var gaps: [String] = []
for i in 1..<max(1, all.count) where all[i] - all[i-1] > 0.1 { gaps.append(String(format: "%.3f-%.3f", all[i-1], all[i])) }
print(String(format: "samples %d pts %.3f..%.3f (edit-list duration %.3f) wrote %d frames", all.count, all.first ?? -1, all.last ?? -1, CMTimeGetSeconds(asset.duration), n))
print("gaps>100ms:", gaps.joined(separator: " "))
