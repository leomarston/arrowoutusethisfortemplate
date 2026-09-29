import AVFoundation
import AppKit

// frames <in.mov> <outdir> <fps> [start] [end] — exact frames of a phone recording as PNGs
// (named by milliseconds), for measuring animation timing. Also prints the video's real fps.
let a = CommandLine.arguments
guard a.count >= 4, let fps = Double(a[3]) else { print("usage: frames in.mov outdir fps [start] [end]"); exit(1) }
let asset = AVURLAsset(url: URL(fileURLWithPath: a[1]))
let duration = CMTimeGetSeconds(asset.duration)
let start = a.count > 4 ? Double(a[4]) ?? 0 : 0
let end = min(a.count > 5 ? Double(a[5]) ?? duration : duration, duration)
if let track = asset.tracks(withMediaType: .video).first {
    print(String(format: "video %.2fs, nominal %.1f fps, %@", duration, track.nominalFrameRate, NSStringFromSize(track.naturalSize)))
}
try? FileManager.default.createDirectory(atPath: a[2], withIntermediateDirectories: true)
let gen = AVAssetImageGenerator(asset: asset)
gen.requestedTimeToleranceBefore = .zero
gen.requestedTimeToleranceAfter = .zero
var t = start, n = 0
while t <= end {
    if let cg = try? gen.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil) {
        let rep = NSBitmapImageRep(cgImage: cg)
        let name = String(format: "%@/f%07d.png", a[2], Int((t * 1000).rounded()))
        try? rep.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: name))
        n += 1
    }
    t += 1 / fps
}
print("wrote \(n) frames to \(a[2])")
