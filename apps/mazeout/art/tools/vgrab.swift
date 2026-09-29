import AVFoundation
import AppKit
// grab IN OUTDIR START END STEP WIDTH  -> OUTDIR/t_<sec>.jpg (seek-based, tolerance 0.1 s)
let a = CommandLine.arguments
let url = URL(fileURLWithPath: a[1]); let out = a[2]
let t0 = Double(a[3])!, t1 = Double(a[4])!, st = Double(a[5])!, w = Double(a[6])!
try? FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)
let asset = AVURLAsset(url: url)
let g = AVAssetImageGenerator(asset: asset)
g.appliesPreferredTrackTransform = true
g.maximumSize = CGSize(width: w, height: w * 4)
g.requestedTimeToleranceBefore = CMTime(seconds: 0.1, preferredTimescale: 600)
g.requestedTimeToleranceAfter = CMTime(seconds: 0.1, preferredTimescale: 600)
var t = t0
while t <= t1 {
    if let cg = try? g.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil) {
        let rep = NSBitmapImageRep(cgImage: cg)
        if let d = rep.representation(using: .jpeg, properties: [.compressionFactor: 0.8]) {
            try? d.write(to: URL(fileURLWithPath: String(format: "%@/t_%07.1f.jpg", out, t)))
        }
    }
    t += st
}
print("done")
