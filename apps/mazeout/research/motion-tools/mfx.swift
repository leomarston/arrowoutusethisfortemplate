import AVFoundation
import CoreImage
import AppKit
import UniformTypeIdentifiers

// mfx — motion-analysis extractor for phone recordings.
//   mfx info IN.mov
//   mfx frames IN.mov OUTDIR FPS START END WIDTH [x y w h]   (crop in POINTS of a 393-wide screen; jpg frames named f<ms>.jpg)
//   mfx raw IN.mov OUT.bin FPS START END WIDTH [x y w h]     (uint8 RGB frames; header: magic,w,h,n then float64 times, then pixels)
//   mfx audio IN.mov OUT.wav [START END]                      (mono 16-bit PCM at the source rate)
//   mfx pts IN.mov                                            (every video sample PTS + gaps > 30 ms; ignores the edit list)
//   env MFX_SEEK=1: frames/raw seek to START via reader.timeRange (for normal mp4s; NOT for phone rec movies)
// NOTE (mazeout): phone 'rec' movies carry an edit list much shorter than the samples, so frames/raw do NOT clamp to
// asset.duration and never set reader.timeRange: every decoded sample is filtered by its REAL presentation time instead.

let args = CommandLine.arguments
func die(_ s: String) -> Never { FileHandle.standardError.write((s + "\n").data(using: .utf8)!); exit(1) }
guard args.count >= 3 else { die("usage: mfx info|frames|raw|audio ...") }
let cmd = args[1]
let asset = AVURLAsset(url: URL(fileURLWithPath: args[2]))
let ciContext = CIContext(options: [.workingColorSpace: CGColorSpace(name: CGColorSpace.sRGB)!, .useSoftwareRenderer: false])

func videoTrack() -> AVAssetTrack {
    guard let t = asset.tracks(withMediaType: .video).first else { die("no video track") }
    return t
}

if cmd == "pts" {
    let reader = try! AVAssetReader(asset: asset)
    let out = AVAssetReaderTrackOutput(track: videoTrack(), outputSettings: nil)
    reader.add(out); reader.startReading()
    var ts: [Double] = []
    while let sb = out.copyNextSampleBuffer() {
        let t = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sb))
        if t.isFinite && CMSampleBufferGetNumSamples(sb) > 0 { ts.append(t) }
    }
    ts.sort()
    print(String(format: "samples %d pts %.3f..%.3f edit-list %.3f", ts.count, ts.first ?? -1, ts.last ?? -1, CMTimeGetSeconds(asset.duration)))
    var g: [String] = []
    for i in 1..<max(1, ts.count) where ts[i] - ts[i-1] > 0.030 { g.append(String(format: "%.3f+%.0fms", ts[i-1], (ts[i]-ts[i-1])*1000)) }
    print("gaps>30ms: " + g.joined(separator: " "))
    exit(0)
}

if cmd == "info" {
    let d = CMTimeGetSeconds(asset.duration)
    let v = videoTrack()
    print(String(format: "duration %.3f s, video %@ %.2f fps", d, NSStringFromSize(v.naturalSize), v.nominalFrameRate))
    for a in asset.tracks(withMediaType: .audio) {
        if let f = a.formatDescriptions.first {
            let asbd = CMAudioFormatDescriptionGetStreamBasicDescription(f as! CMAudioFormatDescription)!.pointee
            print("audio \(asbd.mSampleRate) Hz, \(asbd.mChannelsPerFrame) ch")
        }
    }
    exit(0)
}

func readFrames(fps: Double, start: Double, end: Double, width: Int, crop: CGRect?, handle: (Double, CGImage) -> Void) {
    let track = videoTrack()
    let reader = try! AVAssetReader(asset: asset)
    let e = end
    let out = AVAssetReaderTrackOutput(track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
    out.alwaysCopiesSampleData = false
    reader.add(out)
    // MFX_SEEK=1 (constant-frame-rate files such as the owner's YouTube mp4s, no short edit list): seek with a timeRange
    // instead of decoding from 0. Never use it on the phone 'rec' movies (their edit list is shorter than the samples).
    if ProcessInfo.processInfo.environment["MFX_SEEK"] == "1" {
        let s0 = max(0, start - 1.0)
        reader.timeRange = CMTimeRange(start: CMTime(seconds: s0, preferredTimescale: 600), end: CMTime(seconds: end + 0.2, preferredTimescale: 600))
    }
    reader.startReading()
    var nextT = start
    let step = 1.0 / fps
    let srcW = track.naturalSize.width
    let ptScale = srcW / 393.0
    while let sb = out.copyNextSampleBuffer() {
        let t = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sb))
        if !t.isFinite { continue }
        if t > e + 0.001 { continue }
        if t + 0.004 < nextT { continue }
        guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
        var img = CIImage(cvPixelBuffer: pb)
        let H = img.extent.height
        if let c = crop {
            // points (top-left origin) -> pixels (bottom-left origin)
            let r = CGRect(x: c.origin.x * ptScale, y: H - (c.origin.y + c.height) * ptScale, width: c.width * ptScale, height: c.height * ptScale)
            img = img.cropped(to: r).transformed(by: CGAffineTransform(translationX: -r.origin.x, y: -r.origin.y))
        }
        let s = CGFloat(width) / img.extent.width
        img = img.transformed(by: CGAffineTransform(scaleX: s, y: s))
        let ext = CGRect(x: 0, y: 0, width: CGFloat(width), height: (img.extent.height).rounded())
        if let cg = ciContext.createCGImage(img, from: ext) { handle(t, cg) }
        while nextT <= t + 0.004 { nextT += step }
    }
}

func parseCrop(_ from: Int) -> CGRect? {
    guard args.count >= from + 4 else { return nil }
    let v = args[from..<(from + 4)].map { CGFloat(Double($0)!) }
    return CGRect(x: v[0], y: v[1], width: v[2], height: v[3])
}

if cmd == "frames" {
    let outDir = args[3]
    let fps = Double(args[4])!, start = Double(args[5])!, end = Double(args[6])!, width = Int(args[7])!
    try? FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)
    var n = 0
    readFrames(fps: fps, start: start, end: end, width: width, crop: parseCrop(8)) { t, cg in
        let url = URL(fileURLWithPath: String(format: "%@/f%07d.jpg", outDir, Int((t * 1000).rounded())))
        let dest = CGImageDestinationCreateWithURL(url as CFURL, UTType.jpeg.identifier as CFString, 1, nil)!
        CGImageDestinationAddImage(dest, cg, [kCGImageDestinationLossyCompressionQuality: 0.88] as CFDictionary)
        CGImageDestinationFinalize(dest)
        n += 1
    }
    print("wrote \(n) frames")
    exit(0)
}

if cmd == "raw" {
    let outPath = args[3]
    let fps = Double(args[4])!, start = Double(args[5])!, end = Double(args[6])!, width = Int(args[7])!
    var times: [Double] = []
    var pixels = Data()
    var W = 0, Hh = 0
    readFrames(fps: fps, start: start, end: end, width: width, crop: parseCrop(8)) { t, cg in
        W = cg.width; Hh = cg.height
        var buf = [UInt8](repeating: 0, count: W * Hh * 4)
        let ctx = CGContext(data: &buf, width: W, height: Hh, bitsPerComponent: 8, bytesPerRow: W * 4,
                            space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
        ctx.draw(cg, in: CGRect(x: 0, y: 0, width: W, height: Hh))
        var rgb = [UInt8](repeating: 0, count: W * Hh * 3)
        for i in 0..<(W * Hh) { rgb[i * 3] = buf[i * 4]; rgb[i * 3 + 1] = buf[i * 4 + 1]; rgb[i * 3 + 2] = buf[i * 4 + 2] }
        pixels.append(contentsOf: rgb)
        times.append(t)
    }
    var header = Data()
    var hdr: [Int32] = [0x4D465831, Int32(W), Int32(Hh), Int32(times.count)]
    header.append(Data(bytes: &hdr, count: 16))
    header.append(Data(bytes: &times, count: times.count * 8))
    try! (header + pixels).write(to: URL(fileURLWithPath: outPath))
    print("raw \(times.count) frames \(W)x\(Hh)")
    exit(0)
}

if cmd == "audio" {
    // Reads EVERY audio sample (no timeRange: the phone edit list is short). The WAV's t=0 is media PTS 0: silence is
    // prepended up to the first sample's PTS, so wav time == video PTS. With START END the WAV covers [START, END] of PTS
    // (its t=0 is then START). Prints the first/last audio PTS.
    let outPath = args[3]
    guard let track = asset.tracks(withMediaType: .audio).first else { die("no audio") }
    let reader = try! AVAssetReader(asset: asset)
    let f = track.formatDescriptions.first as! CMAudioFormatDescription
    let sr = CMAudioFormatDescriptionGetStreamBasicDescription(f)!.pointee.mSampleRate
    let out = AVAssetReaderTrackOutput(track: track, outputSettings: [
        AVFormatIDKey: kAudioFormatLinearPCM, AVLinearPCMBitDepthKey: 16, AVLinearPCMIsFloatKey: false,
        AVLinearPCMIsBigEndianKey: false, AVLinearPCMIsNonInterleaved: false, AVNumberOfChannelsKey: 1, AVSampleRateKey: sr])
    reader.add(out)
    reader.startReading()
    var pcm = Data()
    var first = -1.0
    while let sb = out.copyNextSampleBuffer() {
        let t = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sb))
        if first < 0 && t.isFinite {
            first = t
            let pad = max(0, Int((t * sr).rounded()))
            pcm.append(Data(count: pad * 2))
        }
        if let bb = CMSampleBufferGetDataBuffer(sb) {
            var len = 0; var ptr: UnsafeMutablePointer<Int8>?
            CMBlockBufferGetDataPointer(bb, atOffset: 0, lengthAtOffsetOut: nil, totalLengthOut: &len, dataPointerOut: &ptr)
            if let p = ptr { pcm.append(Data(bytes: p, count: len)) }
        }
    }
    let total = Double(pcm.count) / 2 / sr
    if args.count >= 6 {
        let s = Double(args[4])!, e = Double(args[5])!
        let a = max(0, Int(s * sr)) * 2, b = min(pcm.count / 2, Int(e * sr)) * 2
        pcm = a < b ? pcm.subdata(in: a..<b) : Data()
    }
    var wav = Data()
    func u32(_ v: UInt32) { var x = v; wav.append(Data(bytes: &x, count: 4)) }
    func u16(_ v: UInt16) { var x = v; wav.append(Data(bytes: &x, count: 2)) }
    wav.append("RIFF".data(using: .ascii)!); u32(UInt32(36 + pcm.count)); wav.append("WAVE".data(using: .ascii)!)
    wav.append("fmt ".data(using: .ascii)!); u32(16); u16(1); u16(1); u32(UInt32(sr)); u32(UInt32(sr) * 2); u16(2); u16(16)
    wav.append("data".data(using: .ascii)!); u32(UInt32(pcm.count)); wav.append(pcm)
    try! wav.write(to: URL(fileURLWithPath: outPath))
    print(String(format: "audio %.0f Hz, first PTS %.3f, media end %.3f s, wrote %.2f s", sr, first, total, Double(pcm.count) / 2 / sr))
    exit(0)
}
die("unknown command \(cmd)")
