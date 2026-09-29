// tools/vstream.swift — stream every decoded video frame of a movie as raw BGRA to stdout (T10: blipscan / feelstrip).
//
//   vstream IN.mov|IN.mp4 WIDTH [START END]
//
// stdout: 16-byte header (Int32 LE: 0x56535431 'VST1', width, height, 0), then per frame: Float64 LE presentation time (s)
// followed by width*height*4 bytes BGRA (rows top-down, no padding). The decoder scales (VideoToolbox), so a small WIDTH is
// cheap. Like research/motion-tools/mfx (phone 'rec' movies carry an edit list shorter than their samples): NO timeRange is
// set and nothing is clamped to asset.duration — every sample is decoded and filtered by its real presentation time.
// env VSTREAM_SEEK=1: seek with reader.timeRange (constant-frame-rate files such as the owner's mp4s; NOT the phone movies).
// Decoding stops 1 s past END (presentation order is monotonic well within that).
// Build: swiftc -O -o build/tools/vstream tools/vstream.swift   (tools/blipscan.py builds it on first use)
import AVFoundation
import Foundation

func die(_ s: String) -> Never { FileHandle.standardError.write((s + "\n").data(using: .utf8)!); exit(1) }
let args = CommandLine.arguments
guard args.count >= 3, let width = Int(args[2]), width > 0 else { die("usage: vstream IN.mov WIDTH [START END]") }
let start = args.count >= 5 ? Double(args[3]) ?? 0 : 0
let end = args.count >= 5 ? Double(args[4]) ?? 1e9 : 1e9
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
guard let track = asset.tracks(withMediaType: .video).first else { die("no video track") }
let nat = track.naturalSize
var height = Int((Double(width) * Double(nat.height) / Double(nat.width)).rounded())
if height % 2 == 1 { height += 1 }
let reader: AVAssetReader
do { reader = try AVAssetReader(asset: asset) } catch { die("reader: \(error)") }
let out = AVAssetReaderTrackOutput(track: track, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
    kCVPixelBufferWidthKey as String: width,
    kCVPixelBufferHeightKey as String: height,
])
out.alwaysCopiesSampleData = false
reader.add(out)
if ProcessInfo.processInfo.environment["VSTREAM_SEEK"] == "1" && end < 1e8 {
    reader.timeRange = CMTimeRange(start: CMTime(seconds: max(0, start - 1.0), preferredTimescale: 600),
                                   end: CMTime(seconds: end + 0.5, preferredTimescale: 600))
}
guard reader.startReading() else { die("startReading failed: \(String(describing: reader.error))") }
let so = FileHandle.standardOutput
var hdr: [Int32] = [0x5653_5431, Int32(width), Int32(height), 0]
so.write(Data(bytes: &hdr, count: 16))
var row = [UInt8](repeating: 0, count: width * 4)
while let sb = out.copyNextSampleBuffer() {
    var t = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sb))
    if t.isFinite && t > end + 1.0 { break }
    if !t.isFinite || t < start - 0.0005 || t > end + 0.0005 { continue }
    guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
    CVPixelBufferLockBaseAddress(pb, .readOnly)
    let w = CVPixelBufferGetWidth(pb), h = CVPixelBufferGetHeight(pb), bpr = CVPixelBufferGetBytesPerRow(pb)
    guard w == width, h == height, let base = CVPixelBufferGetBaseAddress(pb) else {
        CVPixelBufferUnlockBaseAddress(pb, .readOnly)
        die("unexpected buffer \(CVPixelBufferGetWidth(pb))x\(CVPixelBufferGetHeight(pb))")
    }
    var frame = Data(capacity: 8 + width * height * 4)
    frame.append(Data(bytes: &t, count: 8))
    for y in 0..<height {
        memcpy(&row, base.advanced(by: y * bpr), width * 4)
        frame.append(contentsOf: row)
    }
    CVPixelBufferUnlockBaseAddress(pb, .readOnly)
    so.write(frame)
}
if reader.status == .failed { die("decode failed: \(String(describing: reader.error))") }
