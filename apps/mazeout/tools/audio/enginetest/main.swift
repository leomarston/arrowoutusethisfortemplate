import AVFoundation
import Foundation

// AUDIO A2 (SPEC-architecture §12.2 A2 acceptance). tools/audio/engine_test.sh builds and runs this on macOS, with no
// simulator. It drives the real App/Audio code (AudioCore + AudioGraph + AudioTicker + SoundBank + MusicPlayer + AudioCues)
// through AVAudioEngine's manual (offline) rendering. Every cue goes through the real graph and is compared sample by sample
// with the WAV that A1 rendered. The main assertion: the offset from `play()` (the scheduling call) to the cue's first
// sample in the output is at most ONE IO buffer (0.005 s, audio.json engine.ioBuffer). It is measured at 44.1 kHz and at
// the device's 48 kHz. Adapted from apps/matchfactory tools/audio/enginetest (05424db).
//
// Timing model. On a device the render thread pulls a fixed slice (one IO buffer) every 5 ms, independently of the main
// thread, so a slice starts 0–5 ms after `play()` schedules a cue. AVAudioPlayerNode takes a scheduled buffer through an
// asynchronous hand-off, which T3c measures at under 10 µs. So the harness lets `gapMicros` (200 µs) of wall time pass before
// each render call, and renders whole slices only. Rendering at once with zero wall time is a case no device produces, and
// it makes the hand-off look like a one-slice delay (T3c reports how often).

let appRoot = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : FileManager.default.currentDirectoryPath)
let soundsDir = appRoot.appendingPathComponent("App/Resources/Sounds")
let musicDir = appRoot.appendingPathComponent("App/Resources/Music")
let audioJSONURL = appRoot.appendingPathComponent("App/Resources/Tuning/audio.json")
let outDir = appRoot.appendingPathComponent("build/a2")

final class ClockBox { var frames: Int64 = 0; let rate: Double; init(_ r: Double) { rate = r }; var seconds: Double { Double(frames) / rate } }

nonisolated(unsafe) var results: [(name: String, ok: Bool, detail: String)] = []
func check(_ name: String, _ ok: Bool, _ detail: String) {
    results.append((name, ok, detail))
    print("\(ok ? "PASS" : "FAIL")  \(name): \(detail)")
}
func db(_ x: Float) -> Float { 20 * log10f(max(x, 1e-12)) }

let audioJSON: [String: Any] = {
    guard let d = try? Data(contentsOf: audioJSONURL), let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else {
        print("FAIL  cannot read \(audioJSONURL.path)")
        exit(1)
    }
    return o
}()
let ioBufferSeconds = (AudioCueMap.dotted(audioJSON, "engine.ioBuffer") as? NSNumber)?.doubleValue ?? 0.005
let voiceCount = (AudioCueMap.dotted(audioJSON, "engine.voices") as? NSNumber)?.intValue ?? 8

@MainActor final class Harness {
    let clock: ClockBox
    let core: AudioCore
    let chunk: AVAudioFrameCount
    /// Wall time between a schedule and the next render slice (see the timing model above).
    var gapMicros: useconds_t = 200
    var left: [Float] = []
    var right: [Float] = []
    private var out: AVAudioPCMBuffer?

    /// `chunk` = one IO buffer at `rate` (a realtime-like render size).
    init(rate: Double, musicEnabled: Bool = false) {
        let c = ClockBox(rate)
        clock = c
        chunk = AVAudioFrameCount((ioBufferSeconds * rate).rounded())
        core = AudioCore(mode: .offline(sampleRate: rate), soundsDirectory: soundsDir, musicDirectory: musicDir,
                         voices: voiceCount, musicEnabled: musicEnabled, musicCrossfade: 0.3,
                         clock: { c.seconds }, autoTick: false)
    }

    func boot(bank: SoundBank) async {
        core.install(bank)
        await core.bringUp("boot")
    }

    var frame: Int { Int(clock.frames) }
    var rate: Double { clock.rate }

    /// Renders `seconds`, rounded UP to whole IO-buffer slices (a realtime device renders fixed slices), ticking the ticker
    /// before each slice.
    func render(_ seconds: Double) {
        let total = Int((seconds * clock.rate / Double(chunk)).rounded(.up)) * Int(chunk)
        if gapMicros > 0 { usleep(gapMicros) }
        var done = 0
        while done < total {
            core.tick()
            guard let engine = core.graph?.engine else { fatalError("no engine") }
            if out == nil || out!.format != engine.manualRenderingFormat {
                out = AVAudioPCMBuffer(pcmFormat: engine.manualRenderingFormat, frameCapacity: 4096)
            }
            let n = AVAudioFrameCount(min(Int(chunk), total - done))
            let st: AVAudioEngineManualRenderingStatus
            do { st = try engine.renderOffline(n, to: out!) } catch { fatalError("render: \(error)") }
            let ch = out!.floatChannelData!
            if st == .success {
                left.append(contentsOf: UnsafeBufferPointer(start: ch[0], count: Int(n)))
                right.append(contentsOf: UnsafeBufferPointer(start: ch[1], count: Int(n)))
            } else {                                              // a stopped engine renders nothing: record silence
                left.append(contentsOf: [Float](repeating: 0, count: Int(n)))
                right.append(contentsOf: [Float](repeating: 0, count: Int(n)))
            }
            done += Int(n)
            clock.frames += Int64(n)
        }
    }

    func peak(from: Int, to: Int? = nil) -> Float {
        let end = min(to ?? left.count, left.count)
        guard from < end else { return 0 }
        var p: Float = 0
        for i in from..<end { p = max(p, abs(left[i]), abs(right[i])) }
        return p
    }

    /// Waits (the main actor free) until `cond` holds or `timeout` seconds pass.
    func wait(_ timeout: Double = 3, _ cond: () -> Bool) async -> Bool {
        let t0 = Date()
        while !cond() {
            if Date().timeIntervalSince(t0) > timeout { return false }
            try? await Task.sleep(nanoseconds: 2_000_000)
        }
        return true
    }
}

func samples(_ b: AVAudioPCMBuffer, channel: Int = 0) -> [Float] {
    Array(UnsafeBufferPointer(start: b.floatChannelData![channel], count: Int(b.frameLength)))
}

func sound(_ s: SoundID) -> [Float] {
    samples(try! SoundBank.decode(soundsDir.appendingPathComponent("\(s.rawValue).wav")))
}

/// The file resampled to `rate` (AVAudioConverter), for the 48 kHz comparisons.
func sound(_ s: SoundID, rate: Double) -> [Float] {
    let src = try! SoundBank.decode(soundsDir.appendingPathComponent("\(s.rawValue).wav"))
    if rate == SoundBank.sampleRate { return samples(src) }
    let f = AVAudioFormat(standardFormatWithSampleRate: rate, channels: 1)!
    return samples(try! SoundBank.convert(src, to: f))
}

/// The lag (0...maxLag) that best aligns out[start + lag ...] with ref (highest normalised correlation), with the
/// least-squares gain and the correlation there.
func align(_ out: [Float], start: Int, _ ref: [Float], maxLag: Int = 600, window: Int = 8192) -> (lag: Int, gain: Float, rho: Float) {
    let n = min(window, ref.count)
    var best = (lag: 0, rho: -Float.infinity, gain: Float(1))
    for lag in 0...maxLag {
        var xy: Float = 0, yy: Float = 0, xx: Float = 0
        for i in 0..<n where start + lag + i < out.count { let o = out[start + lag + i]; xy += o * ref[i]; yy += ref[i] * ref[i]; xx += o * o }
        let rho = xx > 0 && yy > 0 ? xy / sqrtf(xx * yy) : 0
        if rho > best.rho { best = (lag, rho, yy > 0 ? xy / yy : 0) }
    }
    return (best.lag, best.gain, best.rho)
}

/// 5-tap binomial low-pass (−53 dB at 19 kHz). The SFX voices pass the varispeed: a flat 48-frame delay up to 15 kHz that
/// rolls off above 19 kHz (MF measured). So SFX are compared below that.
func lowpass(_ x: [Float]) -> [Float] {
    guard x.count > 4 else { return x }
    var y = [Float](repeating: 0, count: x.count)
    for i in 2..<(x.count - 2) { y[i] = (x[i - 2] + 4 * x[i - 1] + 6 * x[i] + 4 * x[i + 1] + x[i + 2]) / 16 }
    return y
}

/// SFX: align, then the max error of the low-passed signals over the whole file (unity gain assumed).
func matchSFX(_ out: [Float], start: Int, _ ref: [Float], gain: Float = 1) -> (lag: Int, gainDB: Float, rho: Float, err: Float) {
    let a = align(out, start: start, ref)
    let end = min(out.count, start + a.lag + ref.count)
    let o = lowpass(Array(out[(start + a.lag)..<end]))
    let r = lowpass(ref.map { $0 * gain })
    var e: Float = 0
    for i in 0..<min(o.count, r.count) { e = max(e, abs(o[i] - r[i])) }
    return (a.lag, db(a.gain), a.rho, e)
}

/// A moving average of `n` taps (a crude low-pass: first null at rate / n).
func boxcar(_ x: [Float], _ n: Int) -> [Float] {
    guard x.count > n else { return x }
    var y = [Float](repeating: 0, count: x.count)
    var acc: Float = 0
    for i in 0..<x.count {
        acc += x[i]
        if i >= n { acc -= x[i - n] }
        y[i] = acc / Float(n)
    }
    return y
}

/// The correlation of the RMS envelopes (windows of `window` frames) of out[start…] and ref, over the reference's length.
func envelopeRho(_ out: [Float], start: Int, _ ref: [Float], window: Int) -> Float {
    func env(_ x: [Float], _ from: Int, _ n: Int) -> [Float] {
        stride(from: 0, to: n - window, by: window).map { w in
            var e: Float = 0
            for i in 0..<window where from + w + i < x.count { e += x[from + w + i] * x[from + w + i] }
            return sqrtf(e / Float(window))
        }
    }
    let a = env(out, start, ref.count), b = env(ref, 0, ref.count)
    var ab: Float = 0, aa: Float = 0, bb: Float = 0
    for i in 0..<min(a.count, b.count) { ab += a[i] * b[i]; aa += a[i] * a[i]; bb += b[i] * b[i] }
    return aa > 0 && bb > 0 ? ab / sqrtf(aa * bb) : 0
}

/// 20·log10(rms(out[start…]) / rms(ref)) over the reference's length.
func rmsRatioDB(_ out: [Float], start: Int, _ ref: [Float]) -> Float {
    var so: Double = 0, sr: Double = 0
    for i in 0..<ref.count where start + i < out.count { so += Double(out[start + i] * out[start + i]); sr += Double(ref[i] * ref[i]) }
    return sr > 0 && so > 0 ? Float(10 * log10(so / sr)) : -.infinity
}

/// The first index with |x| above `threshold`, from `from`.
func onset(_ x: [Float], from: Int = 0, threshold: Float = 1e-3) -> Int? {
    var i = from
    while i < x.count { if abs(x[i]) > threshold { return i }; i += 1 }
    return nil
}

struct CueRow: Codable { let id: String; let rate: Int; let lagFrames: Int; let lagMs: Double; let ioBufferFrames: Int; let gainDB: Double; let rho: Double; let maxErr: Double; let outPeakDBFS: Double; let filePeakDBFS: Double }
nonisolated(unsafe) var cueRows: [CueRow] = []

// MARK: - tests

@MainActor func runTests() async {
    // T0: the cue and haptic tables from the REAL audio.json (SPEC-motion-audio §13.3)
    let map = AudioCueMap(lookup: { AudioCueMap.dotted(audioJSON, $0) })
    var t0Bad: [String] = []
    for m in CueMoment.allCases {
        let want = AudioCueMap.specCues[m].flatMap { $0.isEmpty ? nil : SoundID(rawValue: $0) }
        if map.sound(for: m)?.id != want { t0Bad.append("cue \(m.rawValue)") }
    }
    for s in SoundID.allCases where map.gains[s] != (AudioCueMap.specGains[s] ?? 1) { t0Bad.append("gain \(s.rawValue)") }
    for h in Haptic.allCases where map.row(h) != AudioCueMap.specHaptics[h] { t0Bad.append("haptic \(h.rawValue)=\(map.row(h))") }
    if map.priority != AudioCueMap.specPriority { t0Bad.append("priority \(map.priority.map(\.rawValue))") }
    check("T0 audio.json = SPEC-motion-audio §13.3 (11 moments, 9 gains, 10 haptic rows, priority)", t0Bad.isEmpty && map.problems.isEmpty,
          "mismatches \(t0Bad), problems \(map.problems); arrowTap → \(map.sound(for: .arrowTap).map { $0.id.rawValue } ?? "silent"), tapTick gain \(map.gains[.tapTick] ?? -1)")
    let spec = AudioCueMap.spec
    check("T0 the compiled §13.3 fallback equals the shipped file", spec.problems.isEmpty && spec.priority == map.priority
          && Haptic.allCases.allSatisfy { spec.row($0) == map.row($0) } && CueMoment.allCases.allSatisfy { spec.sound(for: $0)?.id == map.sound(for: $0)?.id },
          "fallback problems \(spec.problems)")
    let broken: [String: Any] = ["cues": ["uiButton": "noSuchSound", "arrowTap": "tapTick"], "gain": ["uiClick": "x"],
                                 "haptics": ["tap": ["style": "wobble", "intensity": 3.0]], "hapticPriority": ["win", "tap", "win", "nope"]]
    let bm = AudioCueMap(lookup: { AudioCueMap.dotted(broken, $0) })
    check("T0 a broken audio.json never crashes: unknown ids silent, bad rows fall back, priority completed",
          bm.sound(for: .uiButton) == nil && bm.sound(for: .arrowTap)?.id == .tapTick && bm.gains[.uiClick] == 1
          && bm.row(.tap) == HapticRow(style: .rigid, intensity: 1.0) && bm.priority.prefix(2) == [.win, .tap]
          && Set(bm.priority) == Set(Haptic.allCases) && bm.priority.count == Haptic.allCases.count && !bm.problems.isEmpty,
          "\(bm.problems.count) problems reported, e.g. \(bm.problems.prefix(3))")

    // T1: the bank
    let d0 = Date()
    let bank = SoundBank.load(directory: soundsDir)
    let decodeMS = Date().timeIntervalSince(d0) * 1000
    let formatsOK = bank.buffers.values.allSatisfy { $0.format.channelCount == 1 && $0.format.sampleRate == 44_100 && $0.format.commonFormat == .pcmFormatFloat32 }
    check("T1 bank decodes every SoundID (mono 44.1 kHz Float32)", bank.buffers.count == SoundID.allCases.count && bank.problems.isEmpty
          && bank.missing.isEmpty && bank.extras.isEmpty && formatsOK,
          "\(bank.buffers.count)/\(SoundID.allCases.count) files, problems \(bank.problems), missing \(bank.missing.map(\.rawValue)), extras \(bank.extras), \(bank.bytes / 1024) KB Float32, decoded in \(String(format: "%.1f", decodeMS)) ms")

    // T2: graph (44.1 kHz)
    let h = Harness(rate: 44_100)
    await h.boot(bank: bank)
    let io441 = Int(h.chunk)
    check("T2 graph builds and starts (offline 44.1 kHz)", h.core.isRunning && h.core.graph?.limiter != nil
          && h.core.voices.count == voiceCount && h.core.graph?.decks.isEmpty == true && h.core.errorCount == 0,
          "phase \(h.core.phase.rawValue), limiter \(h.core.graph?.limiter != nil), voices \(h.core.voices.count), decks \(h.core.graph?.decks.count ?? -1) (music disabled), IO buffer \(io441) frames, errors \(h.core.errorCount)")

    // T3: every cue through the graph: scheduled-to-output offset <= one IO buffer, unity gain, sample match
    h.render(0.05)
    var worstLag = 0
    for s in SoundID.allCases {
        h.render(0.02)
        let start = h.frame
        let before = h.peak(from: max(0, start - io441), to: start)
        let ok = h.core.play(s, gain: 1)
        let ref = sound(s)
        h.render(Double(ref.count) / 44_100 + 0.1)
        let mL = matchSFX(h.left, start: start, ref), mR = matchSFX(h.right, start: start, ref)
        worstLag = max(worstLag, mL.lag)
        let outPeak = db(h.peak(from: start)), filePeak = db(ref.map(abs).max()!)
        cueRows.append(CueRow(id: s.rawValue, rate: 44_100, lagFrames: mL.lag, lagMs: Double(mL.lag) / 44.1, ioBufferFrames: io441,
                              gainDB: Double(mL.gainDB), rho: Double(mL.rho), maxErr: Double(mL.err), outPeakDBFS: Double(outPeak), filePeakDBFS: Double(filePeak)))
        check("T3 \(s.rawValue) @44.1k: offset <= 1 IO buffer, unity, sample match",
              ok && before < 1e-6 && mL.lag <= io441 && mR.lag == mL.lag && abs(mL.gainDB) < 0.05 && abs(mR.gainDB) < 0.05
              && mL.err < 2e-3 && mR.err < 2e-3 && mL.rho > 0.999 && abs(outPeak - filePeak) < 0.1,
              String(format: "offset %d frames = %.2f ms (limit %d = %.2f ms), gain L %+.3f R %+.3f dB, rho %.5f, max err (<15 kHz) %.1e, peak out %.2f / file %.2f dBFS",
                     mL.lag, Double(mL.lag) / 44.1, io441, Double(io441) / 44.1, mL.gainDB, mR.gainDB, mL.rho, mL.err, outPeak, filePeak))
    }

    // T3b: the same at the device's output rate (48 kHz): the mixers resample, the mono spread differs (0 dB at 48 kHz)
    let h48 = Harness(rate: 48_000)
    await h48.boot(bank: bank)
    let io48 = Int(h48.chunk)
    h48.render(0.05)
    for s in SoundID.allCases {
        h48.render(0.02)
        let start = h48.frame
        let ok = h48.core.play(s, gain: 1)
        let ref = sound(s, rate: 48_000)
        h48.render(Double(ref.count) / 48_000 + 0.1)
        // Two different resamplers (the mixer's and AVAudioConverter's) disagree by a fraction of a sample. An integer lag
        // cannot express that, and it costs waveform correlation above a few kHz (the coin glitter is 5.5–7.5 kHz, the tapTick
        // tick 3–6 kHz). So: the lag is taken on both signals low-passed (a 16-tap boxcar at 48 kHz); the shape is compared
        // phase-insensitively (the correlation of the 1 ms RMS envelopes over the whole cue); the level is the RMS ratio.
        // The sample-exact comparison is T3 at 44.1 kHz.
        let lpRef = boxcar(ref, 16)
        let a = align(boxcar(h48.left, 16), start: start, lpRef)
        let aR = align(boxcar(h48.right, 16), start: start, lpRef)
        let gdb = rmsRatioDB(h48.left, start: start + a.lag, ref), gdbR = rmsRatioDB(h48.right, start: start + a.lag, ref)
        let envRho = envelopeRho(h48.left, start: start + a.lag, ref, window: 48)
        let outPeak = db(h48.peak(from: start)), filePeak = db(sound(s).map(abs).max()!)
        worstLag = max(worstLag, Int((Double(a.lag) * 44_100 / 48_000).rounded()))
        cueRows.append(CueRow(id: s.rawValue, rate: 48_000, lagFrames: a.lag, lagMs: Double(a.lag) / 48, ioBufferFrames: io48,
                              gainDB: Double(gdb), rho: Double(envRho), maxErr: -1, outPeakDBFS: Double(outPeak), filePeakDBFS: Double(filePeak)))
        check("T3b \(s.rawValue) @48k: offset <= 1 IO buffer, unity level, same envelope",
              ok && a.lag <= io48 && aR.lag == a.lag && abs(gdb) < 0.1 && abs(gdbR) < 0.1 && envRho > 0.999 && abs(outPeak - filePeak) < 0.35,
              String(format: "offset %d frames = %.2f ms (limit %d = %.2f ms), level (RMS) L %+.3f R %+.3f dB, 1 ms envelope rho %.5f, peak out %.2f / file %.2f dBFS, mono spread %.4f",
                     a.lag, Double(a.lag) / 48, io48, Double(io48) / 48, gdb, gdbR, envRho, outPeak, filePeak, h48.core.graph?.monoSpread ?? -1))
    }

    // T3c: the hand-off race (see the timing model): a slice rendered with no wall time after the schedule may start the
    // cue one slice late; with >= 20 µs in between, never. On a device a schedule lands within that window of a slice
    // boundary in roughly 10 µs / 5 ms = 0.2 % of cases.
    func lateCount(gap: useconds_t, plays: Int) -> Int {
        h.gapMicros = gap
        var late = 0
        for _ in 0..<plays {
            h.render(0.03)
            let st = h.frame
            h.core.play(.uiClick)
            h.render(0.06)
            if matchSFX(h.left, start: st, sound(.uiClick)).lag > worstLag { late += 1 }
        }
        h.gapMicros = 200
        return late
    }
    let late0 = lateCount(gap: 0, plays: 48), late20 = lateCount(gap: 20, plays: 48)
    check("T3c scheduling hand-off: no late start once >= 20 us separate the schedule from the next slice", late20 == 0,
          "late by one slice: \(late20)/48 at 20 us; (informational) \(late0)/48 with zero wall time, a case a device cannot produce")

    // T4: a gain below unity is baked in exactly (gain.tapTick 0.6 = -4.44 dB)
    h.render(0.1)
    var start = h.frame
    h.core.play(.tapTick, gain: 0.6)
    h.render(0.15)
    let m4 = matchSFX(h.left, start: start, sound(.tapTick), gain: 0.6)
    check("T4 gain.tapTick 0.6 is baked in exactly", abs(m4.gainDB - db(0.6)) < 0.05 && m4.err < 2e-3,
          String(format: "measured %+.3f dB (want %+.3f), err %.1e", m4.gainDB, db(0.6), m4.err))

    // T5: the home-return overlap never clips (limiter ceiling -1 dBFS)
    h.render(0.1)
    start = h.frame
    for s in [SoundID.coinCollect, .streakPop, .clawToken, .clawMerge, .unlockChime] { h.core.play(s) }
    h.render(3.0)
    let p5 = db(h.peak(from: start))
    let finite = !h.left[start...].contains { !$0.isFinite }
    check("T5 5 loud cues at once stay under the -1 dBFS ceiling", p5 <= -0.95 && finite,
          String(format: "output peak %.2f dBFS (the sum would reach %.2f dBFS)", p5,
                 db([SoundID.coinCollect, .streakPop, .clawToken, .clawMerge, .unlockChime].map { sound($0).map(abs).max()! }.reduce(0, +))))

    // T6: 8 voices, the 9th steals the oldest; no crash
    h.render(0.2)
    let steals0 = h.core.steals
    for s in [SoundID.unlockChime, .coinCollect, .clawMerge, .clawToken, .streakPop, .clawComplete, .uiClick, .clawTick] { h.core.play(s) }
    let busy8 = h.core.status.busy
    h.core.play(.tapTick)
    let stole = h.core.steals - steals0
    let stolenVoiceHolds = h.core.voices.first { $0.sound == .tapTick }?.index
    h.render(3.0)
    check("T6 8 voices round robin; a 9th cue steals the oldest", busy8 == voiceCount && stole == 1 && stolenVoiceHolds != nil
          && h.core.status.busy == 0,
          "busy after 8 plays \(busy8)/\(voiceCount), steals +\(stole), tapTick took voice \(stolenVoiceHolds.map(String.init) ?? "none"), all free after 3 s: \(h.core.status.busy == 0)")

    // T7: the same cue twice within 15 ms plays once (no +6 dB click)
    h.render(0.1)
    start = h.frame
    let drops7 = h.core.drops
    let first = h.core.play(.uiClick)
    let second = h.core.play(.uiClick)
    h.render(0.1)
    let m7 = matchSFX(h.left, start: start, sound(.uiClick))
    check("T7 a double trigger within 15 ms plays one click", first && !second && h.core.drops == drops7 + 1 && abs(m7.gainDB) < 0.05,
          String(format: "second play %@, level %+.3f dB", second ? "PLAYED" : "dropped", m7.gainDB))

    // T8: Sound OFF: the toggle's own click is heard whole; a long cue that still sounds fades to -80 dB (no step) and plays
    // on inaudibly to its end; new cues are refused; the voice is then restored while idle, so the first cue after Sound ON
    // is at full level at once. The buses are never touched (see AudioGraph's rules).
    h.render(0.1)
    start = h.frame
    h.core.play(.coinCollect)
    h.render(1.20)                                                // into the clinks (1.12–1.46 s): the loudest part
    let offAt = h.frame
    h.core.play(.uiClick)
    h.core.setSound(false)
    let refused = !h.core.play(.clawToken)
    h.render(1.9)                                                 // past the coin's end (+1.7 s) and its voice's pump
    var clickOnly = h.left                                        // the click as heard = output minus the coin cue, up to the mute
    let coin = sound(.coinCollect)
    for i in 0..<coin.count where start + 44 + i < clickOnly.count { clickOnly[start + 44 + i] -= coin[i] }
    let m8 = matchSFX(Array(clickOnly[0..<(offAt + Int(0.05 * 44_100))]), start: offAt, sound(.uiClick))
    let muteEnd = offAt + Int((AudioCore.muteDelay + 0.035) * 44_100)   // the fade starts on the first slice after 60 ms
    let quiet = h.peak(from: muteEnd)
    var step: Float = 0                                           // the largest sample step while it fades
    for i in (offAt + 1)..<muteEnd { step = max(step, abs(h.left[i] - h.left[i - 1])) }
    var fileStep: Float = 0
    for i in 1..<coin.count { fileStep = max(fileStep, abs(coin[i] - coin[i - 1])) }
    let unityVoices = h.core.voices.allSatisfy { $0.player.volume == h.core.graph?.monoVolume && !$0.faded }
    let busAtUnity = h.core.graph?.sfxBus.outputVolume == 1
    let busyAfter = h.core.status.busy
    h.core.setSound(true)
    let s8 = h.frame
    let back = h.core.play(.clawTick)                             // at once, in the first slice after ON
    h.render(0.1)
    let m8b = matchSFX(h.left, start: s8, sound(.clawTick))
    check("T8 Sound OFF: click whole, a sounding cue fades to -80 dB without a step, new cues refused; ON is instant at unity",
          refused && abs(m8.gainDB) < 0.05 && m8.err < 2e-3 && quiet < 2e-4 && step <= fileStep * 1.05 && unityVoices && busAtUnity
          && busyAfter == 0 && back && abs(m8b.gainDB) < 0.05 && m8b.err < 2e-3 && m8b.lag <= io441,
          String(format: "click %+.3f dB err %.1e; after the fade (%.0f ms) peak %.1f dBFS until the coin's end; largest step while fading %.4f (the coin file's own %.4f); voices back at unity %@, buses untouched %@; first cue after ON %+.3f dB err %.1e offset %d",
                 m8.gainDB, m8.err, (AudioCore.muteDelay + 0.035) * 1000, db(quiet), step, fileStep, unityVoices ? "yes" : "NO", busAtUnity ? "yes" : "NO", m8b.gainDB, m8b.err, m8b.lag))

    // T9: music disabled (MA2): playMusic/stopMusic are no-ops, the Music setting changes nothing audible
    h.render(0.1)
    start = h.frame
    let errs9 = h.core.errorCount
    h.core.setMusic(true)
    h.core.playMusic(.home, fade: 0.3)
    h.render(0.5)
    h.core.stopMusic(fade: 0.3)
    h.core.setMusic(false)
    check("T9 music disabled: playMusic/stopMusic are no-ops, silent, no error", h.core.music.playing == nil && h.peak(from: start) < 1e-6
          && h.core.errorCount == errs9 && h.core.graph?.musicBus.outputVolume == 0 && h.core.desiredMusic == nil,
          "track \(h.core.music.playing?.rawValue ?? "none"), peak \(h.peak(from: start)), musicBus \(h.core.graph?.musicBus.outputVolume ?? -1)")

    // T10: an engine stopped behind our back restarts off the main thread; the cue that noticed is dropped
    h.render(0.1)
    h.core.graph?.engine.stop()
    let r10 = h.core.restarts
    let noticed = h.core.play(.uiClick)
    let restarted = await h.wait { h.core.isRunning && !h.core.isTransitioning }
    h.render(0.05)
    start = h.frame
    let played10 = h.core.play(.uiClick)
    h.render(0.1)
    let m10 = matchSFX(h.left, start: start, sound(.uiClick))
    check("T10 engine found stopped: async restart, voices primed, the next cue plays at the same latency",
          !noticed && restarted && h.core.restarts == r10 + 1 && played10 && m10.lag <= io441 && abs(m10.gainDB) < 0.05 && m10.err < 2e-3,
          String(format: "first play dropped %@, restarted %@, offset %d frames, gain %+.3f dB", !noticed ? "yes" : "NO", restarted ? "yes" : "NO", m10.lag, m10.gainDB))

    // T11: an interruption (the system stops the engine) and its end restart the engine and the idle voices
    h.core.suspend("interruption", stopEngine: true)
    let dropped11 = !h.core.play(.uiClick)
    await h.core.resume("interruption")
    h.render(0.05)
    start = h.frame
    let played11 = h.core.play(.streakPop)
    h.render(0.3)
    let m11 = matchSFX(h.left, start: start, sound(.streakPop))
    check("T11 interruption began/ended: suspended, restarted, the next cue plays",
          dropped11 && played11 && h.core.isRunning && m11.lag <= io441 && abs(m11.gainDB) < 0.05 && m11.err < 2e-3,
          String(format: "during: dropped %@; after: offset %d frames, gain %+.3f dB, restarts %d", dropped11 ? "yes" : "NO", m11.lag, m11.gainDB, h.core.restarts))

    // T12: a configuration change (route): reconnect the output chain and restart
    await h.core.bringUp("configuration change", reconnect: true)
    h.render(0.05)
    start = h.frame
    let played12 = h.core.play(.clawComplete)
    h.render(0.3)
    let m12 = matchSFX(h.left, start: start, sound(.clawComplete))
    check("T12 configuration change: output chain reconnected, cue plays", played12 && m12.lag <= io441 && abs(m12.gainDB) < 0.05 && m12.err < 2e-3,
          String(format: "offset %d frames, gain %+.3f dB", m12.lag, m12.gainDB))

    // T13: media services reset: a new engine and graph
    let oldGraph = h.core.graph.map { ObjectIdentifier($0) }
    await h.core.bringUp("media services reset", rebuild: true)
    h.render(0.05)
    start = h.frame
    let played13 = h.core.play(.clawToken)
    h.render(0.9)
    let m13 = matchSFX(h.left, start: start, sound(.clawToken))
    check("T13 media services reset: rebuilt graph, cue plays", played13 && h.core.graph.map { ObjectIdentifier($0) } != oldGraph
          && h.core.voices.count == voiceCount && m13.lag <= io441 && abs(m13.gainDB) < 0.05 && m13.err < 2e-3,
          String(format: "new graph %@, offset %d frames, gain %+.3f dB, errors %d", h.core.graph.map { ObjectIdentifier($0) } != oldGraph ? "yes" : "NO", m13.lag, m13.gainDB, h.core.errorCount))

    // T14: play() cost on the calling thread (schedule only; the tap-frame budget is handler→commit <= 4 ms)
    var costs: [Double] = []
    let order = SoundID.allCases
    for i in 0..<900 {
        h.clock.frames += 2_000                                   // 45 ms apart: no retrigger drop
        let t = DispatchTime.now().uptimeNanoseconds
        h.core.play(order[i % order.count])
        costs.append(Double(DispatchTime.now().uptimeNanoseconds - t) / 1000)
    }
    costs.sort()
    let med = costs[costs.count / 2], p99 = costs[costs.count * 99 / 100], mx = costs.last!
    h.core.suspend("test end", stopEngine: true)
    check("T14 play() cost (macOS, offline engine)", med < 50 && p99 < 250,
          String(format: "900 plays: median %.1f us, p99 %.1f us, max %.1f us", med, p99, mx))

    // T15: music decks work when enabled (a synthesised in-memory loop; nothing shipped), cross-fade, Music off
    let hm = Harness(rate: 44_100, musicEnabled: true)
    func tone(_ hz: Float, _ seconds: Double) -> AVAudioPCMBuffer {
        let n = AVAudioFrameCount(seconds * 44_100)
        let b = AVAudioPCMBuffer(pcmFormat: MusicPlayer.trackFormat, frameCapacity: n)!
        b.frameLength = n
        for c in 0..<2 { for i in 0..<Int(n) { b.floatChannelData![c][i] = 0.5 * sinf(2 * .pi * hz * Float(i) / 44_100) } }
        return b
    }
    hm.core.music.install([.home: tone(441, 1.0), .level: tone(882, 1.0)], problems: [])
    await hm.boot(bank: bank)
    hm.core.setMusic(true)
    hm.core.playMusic(.home, fade: 0)
    hm.render(0.5)
    let homeLevel = db(hm.peak(from: Int(0.1 * 44_100)))
    hm.core.playMusic(.level, fade: 0.3)
    hm.render(0.6)
    let x0 = hm.frame - Int(0.2 * 44_100)
    let seg = Array(hm.left[x0..<hm.frame])
    let ref882 = (0..<seg.count).map { 0.5 * sinf(2 * .pi * 882 * Float($0) / 44_100) }
    let a15 = align(seg, start: 0, ref882, maxLag: 60, window: seg.count - 60)
    let decksPlaying = hm.core.music.decks.filter { $0.id != nil }.count
    hm.core.setMusic(false)
    hm.render(0.4)
    let offPeak = hm.peak(from: hm.frame - Int(0.15 * 44_100))
    check("T15 music (enabled only in this test): unity loop, 0.3 s cross-fade to one deck, Music off silences",
          abs(homeLevel - db(0.5)) < 0.2 && a15.rho > 0.99 && decksPlaying == 1 && hm.core.music.playing == nil && offPeak < 1e-5,
          String(format: "home level %.2f dBFS (file %.2f), after the fade: 882 Hz rho %.4f, decks playing %d, after Music off peak %.1e",
                 homeLevel, db(0.5), a15.rho, decksPlaying, offPeak))
    hm.core.suspend("test end", stopEngine: true)

    // T16: the haptic arbiter (SPEC-motion-audio §12.2): one per frame, highest priority wins, escalation never swallowed
    var arb = HapticArbiter(map: map)
    arb.request(.tap); arb.request(.burst)
    let a1 = arb.flush(now: 1.000)                                // box-break tap frame: burst replaces tap
    arb.request(.bumpContact); arb.request(.heartLost)
    let a2 = arb.flush(now: 1.100)                                // heart loss wins over the contact thud
    arb.request(.button)
    let a3 = arb.flush(now: 1.105)                                // < 1 frame after heartLost, lower: dropped
    arb.request(.fail)
    let a4 = arb.flush(now: 1.200)
    arb.request(.win)
    let a5 = arb.flush(now: 1.205)                                // < 1 frame after fail, lower (win < fail): dropped
    arb.request(.coinLand)
    let a6 = arb.flush(now: 1.300)
    arb.request(.heartLost)
    let a7 = arb.flush(now: 1.305)                                // < 1 frame but outranks coinLand: fires
    let a8 = arb.flush(now: 1.400)                                // nothing pending
    let got = [a1, a2, a3, a4, a5, a6, a7, a8]
    let want: [Haptic?] = [.burst, .heartLost, nil, .fail, nil, .coinLand, .heartLost, nil]
    check("T16 haptic arbiter: priority per turn, one per frame, escalation fires", got == want && arb.fired == 5,
          "got \(got.map { $0?.rawValue ?? "-" }), fired \(arb.fired), dropped \(arb.dropped)")

    // report
    let enc = JSONEncoder()
    enc.outputFormatting = [.prettyPrinted, .sortedKeys]
    try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
    try? enc.encode(cueRows).write(to: outDir.appendingPathComponent("cue-latency.json"))
    print(String(format: "worst scheduled-to-output offset over both rates: %.2f ms; one IO buffer = %.2f ms",
                 Double(worstLag) / 44.1, ioBufferSeconds * 1000))
}

Task { @MainActor in
    await runTests()
    let failed = results.filter { !$0.ok }
    print("\(results.count - failed.count)/\(results.count) passed")
    exit(failed.isEmpty ? 0 : 1)
}
dispatchMain()
