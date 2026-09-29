import AVFoundation
let asset = AVURLAsset(url: URL(fileURLWithPath: CommandLine.arguments[1]))
for tr in asset.tracks {
    print("track \(tr.mediaType.rawValue) timeRange \(CMTimeGetSeconds(tr.timeRange.start))..\(CMTimeGetSeconds(tr.timeRange.end))")
    for s in tr.segments {
        let m = s.timeMapping
        print(String(format: "  seg src %.3f+%.3f -> tgt %.3f+%.3f empty=%d", CMTimeGetSeconds(m.source.start), CMTimeGetSeconds(m.source.duration), CMTimeGetSeconds(m.target.start), CMTimeGetSeconds(m.target.duration), s.isEmpty ? 1 : 0))
    }
    let r = try! AVAssetReader(asset: asset)
    let o = AVAssetReaderTrackOutput(track: tr, outputSettings: nil)
    r.add(o); r.startReading()
    var a = 1e9, b = -1e9, n = 0
    while let sb = o.copyNextSampleBuffer() {
        let t = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sb))
        let d = CMTimeGetSeconds(CMSampleBufferGetDuration(sb))
        if t.isFinite { a = min(a, t); b = max(b, t + (d.isFinite ? d : 0)); n += 1 }
    }
    print(String(format: "  raw samples %d pts %.3f..%.3f", n, a, b))
}
