@preconcurrency import AVFoundation
import AudioToolbox
#if os(iOS)
import SwiftUI
import UIKit
import PathCore
#endif

// AUDIO A2 (SPEC-architecture §7.1, §7.4, §8.2; SPEC-motion-audio §11.2, §11.4, §11.5). Adapted from apps/matchfactory
// App/Audio/{AudioCore,AudioGraph,AudioRamps,AudioEngine}.swift (05424db), cut down to this game's needs: 9 one-shot cues,
// no variants, chains, jingles or loops in play, and no music (MA2).
//
// Layout of this file:
// - `AudioTicker`, `AudioGraph`, `AudioCore`: platform-neutral. tools/audio/engine_test.sh drives them on macOS with
//   AVAudioEngine's manual (offline) rendering.
// - `AudioEngine` (iOS only): the frozen `AudioPlaying` contract around `AudioCore`, the AVAudioSession and the app
//   lifecycle, plus the `AudioEntry` factory.
//
// The FEEL rules (OWNER 03:00, SPEC-architecture D8/§8.2/§10.2) this code keeps:
// - `play` is `scheduleBuffer(at: nil, options: .interrupts)` of a buffer decoded at boot, on a voice that is already
//   attached, connected and playing. There is no file I/O, no allocation (at unity gain) and no engine start on the call
//   path, so the caller fires it inside the handler of the visual event, before the Core Animation commit.
// - Nothing that can block runs on the main thread: the session, the graph build and every engine start or restart run on
//   one serial audio queue. Plays that arrive while that work is in flight are dropped and counted. The main thread never
//   waits for the audio engine (a stopped engine takes 50–150 ms to restart).

// MARK: - AudioTicker

/// Main-thread timed actions and gain ramps: the delayed SFX mute and the music cross-fades. The app ticks it from a
/// 120 Hz timer while anything is pending. The offline tests call `tick()` between render chunks, with a clock that
/// follows the rendered samples.
@MainActor final class AudioTicker {
    private struct Ramp {
        let from: Float
        let to: Float
        let start: Double
        let duration: Double
        let apply: (Float) -> Void
        let done: (() -> Void)?
    }

    let clock: () -> Double
    private let autoTick: Bool
    private var ramps: [Int: Ramp] = [:]
    private var actions: [Int: (at: Double, run: () -> Void)] = [:]
    private var nextToken = 1
    private var timer: Timer?

    init(clock: @escaping () -> Double, autoTick: Bool) {
        self.clock = clock
        self.autoTick = autoTick
    }

    var isIdle: Bool { ramps.isEmpty && actions.isEmpty }

    /// Runs `body` on a later tick, `delay` seconds from now.
    @discardableResult
    func after(_ delay: Double, _ body: @escaping () -> Void) -> Int {
        let t = token()
        actions[t] = (clock() + max(0, delay), body)
        ensureTimer()
        return t
    }

    /// An equal-power ramp (sin/cos quarter wave: a fade-in and a fade-out of the same length sum to constant power).
    /// `duration <= 0` applies `to` and calls `done` at once.
    @discardableResult
    func ramp(from: Float, to: Float, over duration: Double, apply: @escaping (Float) -> Void, done: (() -> Void)? = nil) -> Int? {
        guard duration > 0, from != to else {
            apply(to)
            done?()
            return nil
        }
        let t = token()
        apply(from)
        ramps[t] = Ramp(from: from, to: to, start: clock(), duration: duration, apply: apply, done: done)
        ensureTimer()
        return t
    }

    func cancel(_ token: Int?) {
        guard let token else { return }
        ramps[token] = nil
        actions[token] = nil
    }

    func reset() {
        ramps.removeAll()
        actions.removeAll()
    }

    func tick() {
        let now = clock()
        var finished: [() -> Void] = []
        for (t, r) in ramps {
            let u = Float(min(max((now - r.start) / r.duration, 0), 1))
            let v = r.to >= r.from ? r.from + (r.to - r.from) * sinf(u * .pi / 2) : r.to + (r.from - r.to) * cosf(u * .pi / 2)
            r.apply(u >= 1 ? r.to : v)
            if u >= 1 {
                ramps[t] = nil
                if let d = r.done { finished.append(d) }
            }
        }
        let due = actions.filter { $0.value.at <= now }.sorted { $0.value.at < $1.value.at }
        for d in due { actions[d.key] = nil }
        for f in finished { f() }
        for d in due { d.value.run() }
        if isIdle {
            timer?.invalidate()
            timer = nil
        }
    }

    private func token() -> Int {
        defer { nextToken += 1 }
        return nextToken
    }

    private func ensureTimer() {
        guard autoTick, timer == nil else { return }
        let t = Timer(timeInterval: 1.0 / 120, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated { self?.tick() }
        }
        RunLoop.main.add(t, forMode: .common)
        timer = t
    }
}

// MARK: - AudioGraph

/// The AVAudioEngine node graph (SPEC-architecture §7.1):
///
///     8 × AVAudioPlayerNode ─▶ sfxBus ───┐
///     2 × AVAudioPlayerNode (music decks, only when music.enabled) ─▶ musicBus ─┴─▶ premix ─▶ AUPeakLimiter ─▶ mainMixer (−1 dB) ─▶ out
///
/// Gain staging (MF A2/A3, measured): every source reaches the buses at `nominal` (−6.02 dB per channel). Mono voices play
/// at `nominal / monoSpread`, because the way a mixer spreads mono onto stereo depends on the OUTPUT rate (−3.01 dB at
/// 44.1 kHz, 0 dB at 48 kHz). The limiter's pre-gain adds 6.02 dB + 1 dB back and the main mixer takes the 1 dB off, so the
/// chain is unity below full scale, with an output ceiling of −1 dBFS (attack 1 ms, release 50 ms). Overlapping cues
/// (coin payout + streak pops + claw ticks) therefore never clip.
/// DECISION (A2, measured in tools/audio/engine_test.sh): §7.1 drew an AVAudioUnitVarispeed after each player. It is left
/// out. No cue varies pitch (SPEC-motion-audio §11), and the offline test measured the varispeed as 48 frames (1.09 ms) of
/// fixed extra latency on every cue, plus 8 resamplers running all the time and a roll-off above 15 kHz. Without it a cue
/// leaves the graph 44 frames (1.0 ms, the limiter's look-ahead) after the render slice it was scheduled for.
///
/// Mixer and player rules (measured offline; tools/audio/engine_test.sh T3c, T8, T10–T13):
/// - A change of a mixer input's volume (a player's `volume`) or of a mixer's `outputVolume` only advances while non-silent
///   audio flows through it. A change made in silence is applied as a ≈ 20 ms ramp when the next sound starts, which softens
///   that sound's attack. An input at exactly volume 0 is switched off, and a transient that arrives later wakes it near full
///   level. So the buses stay at unity and nothing mutes or restores by volume in silence (see `AudioCore.setSound`).
/// - A buffer scheduled with `.interrupts` on a player that is PLAYING something starts about two slices late (the player
///   renders ahead). On a starved player it starts on the next slice. So a cue always goes to an idle voice, and a voice is
///   never kept busy on purpose.
/// - The limiter stops processing while its input is silent, so its 1 ms look-ahead can hold stale audio across a pause. It
///   is reset at every (re)start.
///
/// Every connection format is fixed here (mono 44.1 kHz voices, stereo 44.1 kHz decks), so a scheduled buffer can never
/// mismatch its node. It is not actor-isolated: it is built, reconnected, started, paused and stopped on `AudioCore.queue`,
/// and the main actor touches its nodes only while `AudioCore` is `.running` (no transition in flight).
final class AudioGraph: @unchecked Sendable {
    enum Mode: Equatable, Sendable {
        case realtime
        /// Manual offline rendering (tests): the engine renders on demand into buffers of this rate.
        case offline(sampleRate: Double)
    }

    enum GraphError: Error, CustomStringConvertible {
        case noOutput
        var description: String { "the audio output has no usable format (sample rate 0)" }
    }

    /// Per-channel level of every source at the buses (−6.02 dB).
    static let nominal: Float = 0.5
    static let ceilingDB: Float = -1
    /// Per output rate: the measured mono spread. Read and written on `AudioCore.queue` only.
    nonisolated(unsafe) private static var spreadCache: [Double: Float] = [:]

    let mode: Mode
    let engine = AVAudioEngine()
    let sfxBus = AVAudioMixerNode()
    let musicBus = AVAudioMixerNode()
    let premix = AVAudioMixerNode()
    let players: [AVAudioPlayerNode]
    let decks: [AVAudioPlayerNode]
    let voiceFormat = SoundBank.voiceFormat
    let musicFormat = AVAudioFormat(standardFormatWithSampleRate: 44_100, channels: 2)!
    private(set) var limiter: AVAudioUnitEffect?
    /// Fallback make-up stage (+6 dB, no ceiling) if the limiter component is missing.
    private(set) var makeup: AVAudioUnitEQ?
    private(set) var outputFormat: AVAudioFormat?
    private(set) var built = false
    private(set) var monoSpread: Float = 0.70710678
    /// A mono voice's player volume: `nominal` after the buses' mono-to-stereo spread.
    var monoVolume: Float { Self.nominal / monoSpread }

    init(mode: Mode, voices: Int, decks: Int) {
        self.mode = mode
        players = (0..<voices).map { _ in AVAudioPlayerNode() }
        self.decks = (0..<decks).map { _ in AVAudioPlayerNode() }
    }

    /// Attaches and connects every node. Throws (never raises) when there is no usable output.
    func build() throws {
        guard !built else { return }
        if case .offline(let rate) = mode {
            let f = AVAudioFormat(standardFormatWithSampleRate: rate, channels: 2)!
            try engine.enableManualRenderingMode(.offline, format: f, maximumFrameCount: 4096)
        }
        let out = try currentOutputFormat()
        outputFormat = out
        calibrate(out.sampleRate)
        for n in players { engine.attach(n) }
        for n in decks { engine.attach(n) }
        engine.attach(sfxBus)
        engine.attach(musicBus)
        engine.attach(premix)
        limiter = Self.makeLimiter()
        if let l = limiter {
            engine.attach(l)
        } else {
            let eq = AVAudioUnitEQ(numberOfBands: 1)
            eq.bands[0].bypass = true
            eq.globalGain = 20 * log10f(1 / Self.nominal)
            makeup = eq
            engine.attach(eq)
        }
        for p in players {
            engine.connect(p, to: sfxBus, fromBus: 0, toBus: sfxBus.nextAvailableInputBus, format: voiceFormat)
            p.volume = monoVolume
        }
        for d in decks {
            engine.connect(d, to: musicBus, fromBus: 0, toBus: musicBus.nextAvailableInputBus, format: musicFormat)
            d.volume = 0
        }
        musicBus.outputVolume = decks.isEmpty ? 0 : 1                // never changed later (the mixer volume rule)
        connectOutputChain(out)
        built = true
    }

    /// After `AVAudioEngineConfigurationChange` (the engine has stopped itself): re-make the chain after the buses with the
    /// hardware's current format, and re-apply the voices' volume for the new rate's mono spread.
    func reconnectOutput() throws {
        guard built else { return }
        let out = try currentOutputFormat()
        outputFormat = out
        calibrate(out.sampleRate)
        engine.disconnectNodeOutput(sfxBus)
        engine.disconnectNodeOutput(musicBus)
        engine.disconnectNodeOutput(premix)
        if let l = limiter { engine.disconnectNodeOutput(l) }
        if let m = makeup { engine.disconnectNodeOutput(m) }
        connectOutputChain(out)
        for p in players { p.volume = monoVolume }
    }

    func start() throws {
        if let l = limiter { AudioUnitReset(l.audioUnit, kAudioUnitScope_Global, 0) }   // no stale look-ahead audio
        engine.prepare()
        try engine.start()
    }

    /// Puts every voice into the playing state with an empty queue. A voice is then triggered by scheduling with
    /// `.interrupts`, which sounds on the next render slice. A player's very first buffer starts one slice late (measured
    /// offline by MF), so that slice is spent here, at boot, on 64 frames of `silence`, not on the first real cue.
    func primeVoices(_ silence: AVAudioPCMBuffer) {
        guard engine.isRunning else { return }
        for p in players {
            p.stop()
            p.play()
            p.scheduleBuffer(silence, at: nil, options: .interrupts, completionHandler: nil)
        }
    }

    var isRunning: Bool { engine.isRunning }
    func pause() { engine.pause() }
    func stop() { engine.stop() }
    var sampleRate: Double { outputFormat?.sampleRate ?? 0 }

    // MARK: private

    private func connectOutputChain(_ out: AVAudioFormat) {
        engine.connect(sfxBus, to: premix, fromBus: 0, toBus: 0, format: out)
        engine.connect(musicBus, to: premix, fromBus: 0, toBus: 1, format: out)
        let main = engine.mainMixerNode
        if let l = limiter {
            engine.connect(premix, to: l, format: out)
            engine.connect(l, to: main, format: out)
            main.outputVolume = powf(10, Self.ceilingDB / 20)
        } else if let m = makeup {
            engine.connect(premix, to: m, format: out)
            engine.connect(m, to: main, format: out)
            main.outputVolume = 1
        }
    }

    private func currentOutputFormat() throws -> AVAudioFormat {
        switch mode {
        case .offline(let rate):
            return AVAudioFormat(standardFormatWithSampleRate: rate, channels: 2)!
        case .realtime:
            let hw = engine.outputNode.outputFormat(forBus: 0)
            guard hw.sampleRate > 0 else { throw GraphError.noOutput }
            return AVAudioFormat(standardFormatWithSampleRate: hw.sampleRate, channels: 2)!
        }
    }

    /// Sets `monoSpread` for a bus output at `rate`: measured once per rate, else MF's measured values (0.7071 at 44.1 kHz,
    /// 1.0 at 48 kHz and 96 kHz).
    private func calibrate(_ rate: Double) {
        if let cached = Self.spreadCache[rate] {
            monoSpread = cached
            return
        }
        let measured = Self.measureMonoSpread(outputRate: rate)
        monoSpread = measured ?? (abs(rate - 44_100) < 1 ? 0.70710678 : 1)
        Self.spreadCache[rate] = monoSpread
        Log.mark("audio", String(format: "mixer mono spread at %.0f Hz: %+.2f dB (%@) -> voice volume %.4f",
                                 rate, 20 * log10f(monoSpread), measured == nil ? "fallback" : "measured", monoVolume))
    }

    /// Plays a 0.5-amplitude 441 Hz tone through a copy of the voice path (mono 44.1 kHz player → mixer with a stereo
    /// output at `outputRate` → main mixer) in manual offline rendering and reads the per-channel output peak.
    /// nil when the engine cannot run or the result is implausible.
    private static func measureMonoSpread(outputRate: Double) -> Float? {
        let rate = SoundBank.sampleRate
        guard let stereo = AVAudioFormat(standardFormatWithSampleRate: outputRate, channels: 2),
              let mono = AVAudioFormat(standardFormatWithSampleRate: rate, channels: 1) else { return nil }
        let engine = AVAudioEngine()
        do { try engine.enableManualRenderingMode(.offline, format: stereo, maximumFrameCount: 4096) } catch { return nil }
        let player = AVAudioPlayerNode()
        let mixer = AVAudioMixerNode()
        engine.attach(player)
        engine.attach(mixer)
        engine.connect(player, to: mixer, fromBus: 0, toBus: 0, format: mono)
        engine.connect(mixer, to: engine.mainMixerNode, format: stereo)
        let frames: AVAudioFrameCount = 16_384
        guard let tone = AVAudioPCMBuffer(pcmFormat: mono, frameCapacity: frames), let t = tone.floatChannelData,
              let out = AVAudioPCMBuffer(pcmFormat: stereo, frameCapacity: 4096) else { return nil }
        tone.frameLength = frames
        for i in 0..<Int(frames) { t[0][i] = 0.5 * sinf(2 * .pi * Float(i % 100) / 100) }   // 441 Hz: 100 samples a period
        engine.prepare()
        do { try engine.start() } catch { return nil }
        defer { engine.stop() }
        player.scheduleBuffer(tone, at: nil, options: [], completionHandler: nil)
        player.play()
        var peaks: [Float] = [0, 0]
        for pass in 0..<4 {
            guard let status = try? engine.renderOffline(4096, to: out), status == .success,
                  let o = out.floatChannelData, out.format.channelCount == 2 else { return nil }
            if pass == 0 { continue }                                  // a player's first buffer can start a cycle late
            for c in 0..<2 { for i in 0..<Int(out.frameLength) { peaks[c] = max(peaks[c], abs(o[c][i])) } }
        }
        let spread = (peaks[0] + peaks[1]) / 2 / 0.5
        guard spread > 0.3, spread < 1.5, abs(peaks[0] - peaks[1]) < 0.01 else { return nil }
        return spread
    }

    /// Apple's AUPeakLimiter. nil when the component is missing, so construction never raises.
    private static func makeLimiter() -> AVAudioUnitEffect? {
        var desc = AudioComponentDescription(componentType: kAudioUnitType_Effect,
                                             componentSubType: kAudioUnitSubType_PeakLimiter,
                                             componentManufacturer: kAudioUnitManufacturer_Apple,
                                             componentFlags: 0, componentFlagsMask: 0)
        guard AudioComponentFindNext(nil, &desc) != nil else { return nil }
        let l = AVAudioUnitEffect(audioComponentDescription: desc)
        let preGain = 20 * log10f(1 / nominal) - ceilingDB           // +6.02 dB nominal make-up, +1 dB for the ceiling
        AudioUnitSetParameter(l.audioUnit, kLimiterParam_AttackTime, kAudioUnitScope_Global, 0, 0.001, 0)
        AudioUnitSetParameter(l.audioUnit, kLimiterParam_DecayTime, kAudioUnitScope_Global, 0, 0.050, 0)
        AudioUnitSetParameter(l.audioUnit, kLimiterParam_PreGain, kAudioUnitScope_Global, 0, preGain, 0)
        return l
    }
}

// MARK: - AudioCore

/// Everything the engine decides: the voices and their stealing, the buses and the Sound/Music settings, suspend and
/// restart. Main actor only. The render thread never calls back into it.
@MainActor final class AudioCore {
    /// One SFX voice: a player on the SFX bus, reused round robin (the oldest is stolen when all 8 are busy).
    @MainActor final class Voice {
        let index: Int
        let player: AVAudioPlayerNode
        fileprivate(set) var sound: SoundID?
        fileprivate(set) var startedAt: Double = -.infinity
        fileprivate var busyUntil: Double = -.infinity
        /// Faded by Sound OFF: its cue plays on at −80 dB until it ends; then its volume is restored (`AudioCore.restore`).
        fileprivate(set) var faded = false

        init(index: Int, player: AVAudioPlayerNode) {
            self.index = index
            self.player = player
        }

        func isBusy(_ now: Double) -> Bool { busyUntil > now }
    }

    enum Phase: String {
        case cold          // nothing built yet (before warmUp)
        case starting      // a build / start / restart is running on the audio queue
        case running
        case suspended     // background or an interruption
        case failed        // the last start threw; the next play retries (rate-limited)
    }

    struct Status: CustomStringConvertible {
        var phase = Phase.cold
        var running = false
        var sampleRate: Double = 0
        var limiter = false
        var soundOn = true
        var musicOn = false
        var musicEnabled = false
        var music: String?
        var busy = 0
        var voices = 0
        var loaded = 0
        var loadedBytes = 0
        var missing: [String] = []
        var plays = 0
        var drops = 0
        var steals = 0
        var restarts = 0
        var errors = 0
        var suspended: [String] = []
        var last: String?

        var description: String {
            "phase=\(phase.rawValue) running=\(running) sr=\(Int(sampleRate)) limiter=\(limiter) sound=\(soundOn)"
                + " music=\(musicOn)\(musicEnabled ? "" : " (disabled)") track=\(music ?? "none") voices=\(busy)/\(voices)"
                + " sounds=\(loaded) (\(loadedBytes / 1024) KB) missing=\(missing.count) plays=\(plays) drops=\(drops)"
                + " steals=\(steals) restarts=\(restarts) errors=\(errors)"
                + (suspended.isEmpty ? "" : " suspended=\(suspended.joined(separator: ","))") + " last=\(last ?? "none")"
        }
    }

    /// The one serial queue for everything that can block: the session, the graph build, engine start/pause/stop.
    nonisolated static let queue = DispatchQueue(label: "com.manycode.arrowout.audio", qos: .userInitiated)
    /// Sound OFF (SPEC-architecture §7.1 mutes the SFX bus; done per voice here, see AudioGraph's rules). New sounds are
    /// refused at once. After `muteDelay` (so the toggle's own 35 ms click is heard whole) every voice that still sounds
    /// fades by its volume to `fadeFloor` (≈ 20 ms, no click). Its cue plays on, inaudible, to its natural end. Then the
    /// voice, idle, plays `pump` while its volume returns to unity. So Sound ON is instant and at full level, and no cue ever
    /// lands on a voice that is still ramping.
    nonisolated static let muteDelay = 0.06
    /// −80 dB, not 0: an input at exactly 0 is switched off by the mixer, and a transient that arrives later wakes it with its
    /// ramp restarted near full level (measured: a coin clink at −14 dBFS).
    nonisolated static let fadeFloor: Float = 1e-4
    /// The buffer an idle voice plays while its volume ramps back: 60 ms of ±1e-7 (−140 dBFS, below a 24-bit LSB, 0 in
    /// 16-bit). An all-zero buffer is flagged as silence and the mixer would skip it, so the ramp would not advance.
    nonisolated static let pumpSeconds = 0.06
    nonisolated static let pumpLevel: Float = 1e-7
    /// A faded voice is restored this long after its cue's scheduled end (`busyUntil` already adds 20 ms), so the pump never
    /// cuts a tail that a large render slice (a Bluetooth route) still plays. Until then the voice counts as busy.
    nonisolated static let restoreMargin = 0.03
    /// A retrigger of the same sound sooner than this is dropped: one release handled by two call sites must not double
    /// (+6 dB) the click. The fastest real repeat is the Claw count-up tick, 0.057 s apart (SPEC-motion-audio §8.5).
    nonisolated static let minRetrigger = 0.015

    let mode: AudioGraph.Mode
    let soundsDirectory: URL?
    let musicDirectory: URL?
    let voiceCount: Int
    let clock: () -> Double
    let ticker: AudioTicker
    let music: MusicPlayer

    private(set) var graph: AudioGraph?
    private(set) var bank: SoundBank = .empty
    private(set) var voices: [Voice] = []
    private(set) var phase: Phase = .cold
    private(set) var suspendReasons: Set<String> = []
    private(set) var soundOn = true
    private(set) var musicOn = false
    /// The track the game wants (playMusic); restored after a restart.
    private(set) var desiredMusic: MusicID?
    private var transition: Task<Void, Never>?
    private var roundRobin = 0
    private var lastTrigger: [SoundID: Double] = [:]
    private var derived: [String: AVAudioPCMBuffer] = [:]
    private let pump: AVAudioPCMBuffer
    private let silence: AVAudioPCMBuffer
    private var sfxMuteToken: Int?
    private var lastKick: Double = -.infinity

    // counters
    private(set) var errorLog: [String] = []
    private(set) var errorCount = 0
    private(set) var plays = 0
    private(set) var drops = 0
    private(set) var steals = 0
    private(set) var restarts = 0
    private(set) var lastPlayed: String?

    init(mode: AudioGraph.Mode, soundsDirectory: URL?, musicDirectory: URL?, voices: Int, musicEnabled: Bool,
         musicCrossfade: Double, clock: @escaping () -> Double, autoTick: Bool) {
        self.mode = mode
        self.soundsDirectory = soundsDirectory
        self.musicDirectory = musicDirectory
        voiceCount = max(1, voices)
        self.clock = clock
        let t = AudioTicker(clock: clock, autoTick: autoTick)
        ticker = t
        music = MusicPlayer(enabled: musicEnabled, crossfade: musicCrossfade, ticker: t)
        let frames = AVAudioFrameCount(Self.pumpSeconds * SoundBank.sampleRate)
        let b = AVAudioPCMBuffer(pcmFormat: SoundBank.voiceFormat, frameCapacity: frames)!
        b.frameLength = frames
        let d = b.floatChannelData![0]
        for i in 0..<Int(frames) { d[i] = i % 2 == 0 ? Self.pumpLevel : -Self.pumpLevel }
        pump = b
        let z = AVAudioPCMBuffer(pcmFormat: SoundBank.voiceFormat, frameCapacity: 64)!
        z.frameLength = 64
        z.floatChannelData![0].update(repeating: 0, count: 64)
        silence = z
    }

    var isRunning: Bool { phase == .running && (graph?.isRunning ?? false) }
    var isTransitioning: Bool { transition != nil }

    // MARK: warm-up (off the main thread)

    /// Decodes `Sounds/*.wav` on a background queue.
    nonisolated static func decode(_ directory: URL?) async -> SoundBank {
        await withCheckedContinuation { (cont: CheckedContinuation<SoundBank, Never>) in
            DispatchQueue.global(qos: .userInitiated).async { cont.resume(returning: SoundBank.load(directory: directory)) }
        }
    }

    /// Takes the decoded sounds. Every problem is logged as an error (the boot log is the A3 check).
    func install(_ b: SoundBank) {
        bank = b
        for p in b.problems { fail("sound file \(p)") }
        if !b.missing.isEmpty { fail("missing Sounds/<id>.wav for \(b.missing.map(\.rawValue).joined(separator: ", "))") }
        if !b.extras.isEmpty { Log.mark("audio", "ignored files in Sounds/: \(b.extras.joined(separator: ", "))") }
        derived.removeAll()
    }

    /// Builds the graph (the first time, or a new one with `rebuild`), reconnects the output chain (`reconnect`, after a
    /// route change), starts the engine and primes every voice, all on `queue`. Waits for a transition already in flight
    /// and returns at once when the engine already runs. The main thread never blocks on it.
    func bringUp(_ reason: String, rebuild: Bool = false, reconnect: Bool = false) async {
        while let t = transition { await t.value }                  // the task clears `transition` itself before it ends
        guard suspendReasons.isEmpty else { return }
        if !rebuild, !reconnect, isRunning { return }
        let t = Task { @MainActor [self] in
            await self.performBringUp(reason, rebuild: rebuild, reconnect: reconnect)
            self.transition = nil
        }
        transition = t                                                // set before the task can run (no suspension point)
        await t.value
    }

    private func performBringUp(_ reason: String, rebuild: Bool, reconnect: Bool) async {
        let t0 = clock()
        let first = graph == nil
        // A graph whose build threw is never reused: attaching its nodes again would raise.
        let needBuild = first || rebuild || graph?.built == false
        let old = needBuild ? graph : nil
        let g = needBuild ? AudioGraph(mode: mode, voices: voiceCount, decks: music.enabled ? 2 : 0) : graph!
        phase = .starting
        for v in voices { v.sound = nil; v.busyUntil = -.infinity }
        music.detach()
        let silence = self.silence
        let error: String? = await withCheckedContinuation { (cont: CheckedContinuation<String?, Never>) in
            Self.queue.async {
                old?.stop()
                do {
                    if needBuild {
                        try g.build()
                    } else if reconnect {
                        g.stop()
                        try g.reconnectOutput()
                    }
                    if !g.isRunning { try g.start() }
                    g.primeVoices(silence)
                    cont.resume(returning: nil)
                } catch {
                    cont.resume(returning: "\(error)")
                }
            }
        }
        if needBuild {
            graph = g
            voices = g.players.enumerated().map { Voice(index: $0.offset, player: $0.element) }
            roundRobin = 0
        }
        if !first { restarts += 1 }
        if let error {
            phase = .failed
            fail("engine start (\(reason)) failed: \(error)")
            return
        }
        guard suspendReasons.isEmpty else {
            // suspended while it started (before the graph existed, `suspend` had nothing to pause): pause it now
            phase = .suspended
            Self.queue.async { g.pause() }
            return
        }
        phase = .running
        for v in voices where v.faded { restore(v) }                 // faded when it stopped: its cue is gone, restore now
        music.attach(g.decks)
        if musicOn, let m = desiredMusic { music.start(m, fadeIn: first ? 0 : 0.3) }
        let ms = (clock() - t0) * 1000
        Log.mark("audio", String(format: "engine %@ (%@) in %.0f ms: %@", first ? "started" : "restarted", reason, ms, status.description))
    }

    /// Non-blocking: an engine found stopped behind our back (no notification seen) restarts on the audio queue.
    /// Rate-limited to once a second. The sound that noticed it is dropped.
    func kickIfStopped() {
        guard suspendReasons.isEmpty, transition == nil, phase == .running || phase == .failed,
              !(graph?.isRunning ?? false) || phase == .failed else { return }
        let now = clock()
        guard now - lastKick > 1 else { return }
        lastKick = now
        Task { @MainActor [self] in await self.bringUp("engine found stopped") }
    }

    /// Background or an interruption pauses everything (`stopEngine` = the system already stopped it). Reasons nest
    /// (background during a call); the engine restarts when the last one ends (`resume`).
    func suspend(_ reason: String, stopEngine: Bool = false) {
        let first = suspendReasons.isEmpty
        suspendReasons.insert(reason)
        guard first else { return }
        if phase == .running { phase = .suspended }
        music.cutAll()
        for v in voices { v.sound = nil; v.busyUntil = -.infinity }
        if let g = graph {
            Self.queue.async { if stopEngine { g.stop() } else { g.pause() } }
        }
        Log.mark("audio", "suspended (\(reason))")
    }

    func resume(_ reason: String) async {
        guard suspendReasons.remove(reason) != nil, suspendReasons.isEmpty else { return }
        await bringUp("\(reason) ended")
    }

    /// Housekeeping for the offline tests (the app's ticker runs its own timer).
    func tick() { ticker.tick() }

    // MARK: settings (SPEC-architecture §7.1 Sound off / Music off; done per voice and per deck, see AudioGraph's rules)

    func setSettings(sound: Bool, music on: Bool) {
        setSound(sound)
        setMusic(on)
    }

    func setSound(_ on: Bool) {
        guard on != soundOn else { return }
        soundOn = on
        ticker.cancel(sfxMuteToken)
        sfxMuteToken = nil
        // ON: nothing to undo. A faded cue stays faded to its end (a muted sound never resumes mid-way), and new cues take
        // the idle voices.
        if !on {
            sfxMuteToken = ticker.after(Self.muteDelay) { [weak self] in
                guard let self else { return }
                self.sfxMuteToken = nil
                guard !self.soundOn, self.isRunning else { return }
                let now = self.clock()
                for v in self.voices where v.sound != nil && v.isBusy(now) && !v.faded {
                    v.player.volume = Self.fadeFloor                   // fades while it still plays
                    v.faded = true
                    let restoreAt = v.busyUntil + Self.restoreMargin
                    v.busyUntil = restoreAt
                    self.ticker.after(restoreAt - now) { [weak self, weak v] in
                        guard let self, let v, v.faded, v.busyUntil == restoreAt else { return }
                        self.restore(v)
                    }
                }
            }
        }
        Log.mark("audio", "sound \(on ? "on" : "off")")
    }

    /// A faded voice whose cue has ended (it is idle, so the pump starts on the next slice): plays the inaudible pump and
    /// returns its volume to unity while the pump plays. The voice stays busy until the pump ends.
    private func restore(_ v: Voice) {
        guard v.faded else { return }
        v.faded = false
        guard isRunning, let g = graph else { return }               // a restart restores it (performBringUp)
        if !v.player.isPlaying { v.player.play() }
        v.player.scheduleBuffer(pump, at: nil, options: .interrupts, completionHandler: nil)
        v.player.volume = g.monoVolume
        v.sound = nil
        v.busyUntil = clock() + Self.pumpSeconds + 0.005
    }

    func setMusic(_ on: Bool) {
        guard on != musicOn else { return }
        musicOn = on
        guard music.enabled else { return }                        // MA2: no music; the setting changes nothing audible
        if on {
            if let m = desiredMusic, isRunning { music.start(m, fadeIn: music.crossfade) }
        } else {
            music.stop(fade: 0.15, done: nil)                        // the decks fade by their own volume, then stop
        }
        Log.mark("audio", "music \(on ? "on" : "off")")
    }

    // MARK: sounds

    /// SPEC-architecture §7.4 `play`. `gain` is linear (clamped to +12 dB; the limiter holds the ceiling). It is baked into
    /// a cached copy of the buffer, so a voice's volume never changes between triggers (a mixer input glides volume
    /// changes over ≈ 12 ms, which would soften the next attack). Returns whether the sound was scheduled.
    @discardableResult
    func play(_ s: SoundID, gain: Float = 1) -> Bool {
        guard soundOn else { return false }                          // Sound OFF: silent by choice, not a drop
        let now = clock()
        guard phase == .running, let g = graph, g.isRunning else {
            drops += 1
            kickIfStopped()
            return false
        }
        if let last = lastTrigger[s], now - last < Self.minRetrigger { drops += 1; return false }
        guard let buffer = shaped(s, gain: gain) else { return false }   // missing file (logged at boot) or silent gain
        lastTrigger[s] = now
        let v = allocate(now)
        if v.faded {                                                  // stolen while faded (all 8 busy): audible again
            v.faded = false
            v.player.volume = g.monoVolume                           // its ramp softens this cue's first ≈ 20 ms
        }
        v.sound = s
        v.startedAt = now
        v.busyUntil = now + Double(buffer.frameLength) / SoundBank.sampleRate + 0.02
        if !v.player.isPlaying { v.player.play() }                   // the engine runs (checked above)
        v.player.scheduleBuffer(buffer, at: nil, options: .interrupts, completionHandler: nil)
        plays += 1
        lastPlayed = s.rawValue
        return true
    }

    // MARK: music (MA2 / §11.5: disabled; playMusic and stopMusic are then no-ops)

    func playMusic(_ m: MusicID, fade: Double) {
        guard music.enabled else { music.noteDisabled("playMusic(\(m.rawValue))"); return }
        desiredMusic = m
        guard musicOn, isRunning else { return }
        music.start(m, fadeIn: fade)
    }

    func stopMusic(fade: Double) {
        guard music.enabled else { music.noteDisabled("stopMusic"); return }
        desiredMusic = nil
        music.stop(fade: fade, done: nil)
    }

    // MARK: status

    var status: Status {
        var s = Status()
        let now = clock()
        s.phase = phase
        s.running = graph?.isRunning ?? false
        s.sampleRate = graph?.sampleRate ?? 0
        s.limiter = graph?.limiter != nil
        s.soundOn = soundOn
        s.musicOn = musicOn
        s.musicEnabled = music.enabled
        s.music = music.playing?.rawValue
        s.busy = voices.filter { $0.isBusy(now) }.count
        s.voices = voices.count
        s.loaded = bank.buffers.count
        s.loadedBytes = bank.bytes
        s.missing = bank.missing.map(\.rawValue)
        s.plays = plays
        s.drops = drops
        s.steals = steals
        s.restarts = restarts
        s.errors = errorCount
        s.suspended = suspendReasons.sorted()
        s.last = lastPlayed
        return s
    }

    func fail(_ message: String) {
        errorCount += 1
        errorLog.append(message)
        if errorLog.count > 50 { errorLog.removeFirst(errorLog.count - 50) }
        Log.error("audio", message)
    }

    // MARK: private

    /// A free voice round robin, else the oldest (stolen: `.interrupts` replaces what it was playing).
    private func allocate(_ now: Double) -> Voice {
        for k in 0..<voices.count {
            let v = voices[(roundRobin + k) % voices.count]
            if !v.isBusy(now) {
                roundRobin = (v.index + 1) % voices.count
                return v
            }
        }
        steals += 1
        let v = voices.filter { !$0.faded }.min { $0.startedAt < $1.startedAt } ?? voices.min { $0.startedAt < $1.startedAt }!
        roundRobin = (v.index + 1) % voices.count
        return v
    }

    /// The buffer for `s` with `gain` baked in (quantised to 0.1 dB, cached). Unity → the decoded buffer itself.
    /// nil for a missing file or a gain below −60 dB.
    private func shaped(_ s: SoundID, gain: Float) -> AVAudioPCMBuffer? {
        guard let src = bank.buffer(s) else { return nil }
        let gdb = (20 * log10f(max(gain, 1e-6)) * 10).rounded() / 10
        guard gdb > -60 else { return nil }
        if gdb == 0 { return src }
        let key = "\(s.rawValue)|\(gdb)"
        if let hit = derived[key] { return hit }
        let g = powf(10, min(gdb, 12) / 20)
        guard let copy = AVAudioPCMBuffer(pcmFormat: src.format, frameCapacity: src.frameLength),
              let from = src.floatChannelData, let to = copy.floatChannelData else { return src }
        copy.frameLength = src.frameLength
        let n = Int(src.frameLength)
        for c in 0..<Int(src.format.channelCount) {
            for i in 0..<n { to[c][i] = from[c][i] * g }
        }
        if derived.count >= 32 { derived.removeAll() }
        derived[key] = copy
        return copy
    }
}

// MARK: - AudioEngine (iOS: the contract, the session, the lifecycle)

#if os(iOS)

extension AudioEntry {
    static func makeAudio(_ ctx: AppContext) -> any AudioPlaying { AudioEngine(ctx) }
}

extension AudioPlaying {
    /// Plays the sound `audio.json` maps to `moment` (`cues.<moment>`) at its gain (`gain.<id>`), on this frame. A moment
    /// mapped to "" (every in-level moment; `arrowTap` by default) plays nothing. Returns whether a sound was scheduled.
    /// Named `cue` because SoundID and CueMoment share case names (`.clawToken`).
    @discardableResult
    func cue(_ moment: CueMoment) -> Bool {
        (self as? AudioEngine)?.cue(moment) ?? false
    }
}

/// SPEC-architecture §7.1:
/// - `AVAudioSession` `.ambient` (mixes with other audio, obeys the silent switch), preferred IO buffer `engine.ioBuffer`
///   (0.005 s), activated in `warmUp`, behind the Loading screen.
/// - The engine starts in `warmUp` and is never stopped in play. Background and interruptions pause it, and the return
///   restarts it on the audio queue (the main thread never waits).
/// - Capture mode (`-pc.capture 1`) is fully muted: no session, no engine (§9.2).
/// - `[PC][audio] latency io <ms> out <ms>` is logged at boot and after a route change (§7.1, §9.3, the §10.2 budget).
@MainActor final class AudioEngine: AudioPlaying {
    let core: AudioCore
    let cues: AudioCueMap
    let muted: Bool
    /// io buffer + route latency (§10 probe), updated at boot and on route changes.
    private(set) var outputLatency: TimeInterval = 0
    private(set) var ioBufferDuration: TimeInterval = 0
    private(set) var hardwareRate: Double = 0
    private let preferredIOBuffer: Double
    private var warmTask: Task<Void, Never>?
    private var observers: [NSObjectProtocol] = []
    private var configChangePending = false

    private struct SessionInfo: Sendable {
        var problems: [String] = []
        var sampleRate: Double = 0
        var ioBuffer: Double = 0
        var outputLatency: Double = 0
    }

    init(_ ctx: AppContext) {
        muted = ctx.args.audioMuted
        let t = ctx.tuning.audio
        cues = AudioCueMap(lookup: { t.file.value($0) })
        preferredIOBuffer = min(max(t.ioBufferDuration, 0.002), 0.05)
        let res = ctx.bundle.resourceURL
        core = AudioCore(mode: .realtime,
                         soundsDirectory: res?.appendingPathComponent("Sounds", isDirectory: true),
                         musicDirectory: res?.appendingPathComponent("Music", isDirectory: true),
                         voices: min(max(t.voices, 1), 16), musicEnabled: t.musicEnabled,
                         musicCrossfade: t.musicCrossfade,
                         clock: { ProcessInfo.processInfo.systemUptime }, autoTick: true)
        for p in cues.problems { Log.error("audio", "audio.json: \(p)") }
        let mapped = CueMoment.allCases.map { m in "\(m.rawValue)=\(cues.sound(for: m)?.id.rawValue ?? "-")" }
        Log.mark("audio", (muted ? "capture mode: muted (no session, no engine); " : "")
                 + "\(core.voiceCount) voices, music \(t.musicEnabled ? "enabled" : "disabled"), cues " + mapped.joined(separator: " "))
    }

    // MARK: AudioPlaying

    /// Session + decode + engine, once, behind the Loading screen. Later calls only make sure the engine runs.
    func warmUp() async {
        guard !muted else { return }
        if let t = warmTask {
            await t.value
            core.kickIfStopped()
            return
        }
        let t = Task { @MainActor in await self.boot() }
        warmTask = t
        await t.value
    }

    func play(_ s: SoundID, gain: Float) {
        guard !muted else { return }
        core.play(s, gain: gain)
    }

    func playMusic(_ m: MusicID, fade: Double) {
        guard !muted else { return }
        core.playMusic(m, fade: fade)
    }

    func stopMusic(fade: Double) {
        guard !muted else { return }
        core.stopMusic(fade: fade)
    }

    func apply(settings: PlayerState.Settings) {
        core.setSettings(sound: settings.sound, music: settings.music)
    }

    // MARK: beyond the contract

    /// `AudioPlaying.cue(_:)`.
    @discardableResult
    func cue(_ moment: CueMoment) -> Bool {
        guard !muted, let c = cues.sound(for: moment) else { return false }
        return core.play(c.id, gain: c.gain)
    }

    /// The system's interruption path, callable from the SoundBoard (simctl cannot interrupt; SPEC-architecture §12.2 A3).
    /// `began` stops the engine as the system does; the end re-activates the session and restarts the engine and the idle
    /// voices.
    func debugInterruption(began: Bool) {
        guard !muted, warmTask != nil else { return }
        handleInterruption(began: began)
    }

    var status: AudioCore.Status { core.status }

    // MARK: boot

    private func boot() async {
        let t0 = ProcessInfo.processInfo.systemUptime
        let io = preferredIOBuffer, sounds = core.soundsDirectory, musicDir = core.musicDirectory, musicOn = core.music.enabled
        async let session = Self.activateSession(configure: true, ioBuffer: io)
        async let decoded = AudioCore.decode(sounds)
        async let tracks = MusicPlayer.loadTracks(directory: musicDir, enabled: musicOn)
        let info = await session
        for p in info.problems { core.fail("session: \(p)") }
        record(info)
        core.install(await decoded)
        let t = await tracks
        core.music.install(t.tracks, problems: t.problems)
        await core.bringUp("boot")
        installObservers()
        logLatency()
        let s = ProcessInfo.processInfo.systemUptime - t0
        Log.mark("warmup", String(format: "audio %.3f s", s))
    }

    private func record(_ info: SessionInfo) {
        hardwareRate = info.sampleRate
        ioBufferDuration = info.ioBuffer
        outputLatency = info.ioBuffer + info.outputLatency
    }

    private func logLatency() {
        Log.mark("audio", String(format: "latency io %.1f out %.1f", ioBufferDuration * 1000, (outputLatency - ioBufferDuration) * 1000))
        let total = outputLatency * 1000
        Log.mark("audio", String(format: "route %.0f Hz, io buffer + output = %.1f ms (budget 16.7 ms: %@)", hardwareRate, total,
                                 total <= 16.7 ? "within" : "OVER; the hardware route sets it"))
    }

    nonisolated private static func activateSession(configure: Bool, ioBuffer: Double) async -> SessionInfo {
        await withCheckedContinuation { (cont: CheckedContinuation<SessionInfo, Never>) in
            AudioCore.queue.async {
                let s = AVAudioSession.sharedInstance()
                var info = SessionInfo()
                if configure {
                    do { try s.setCategory(.ambient, mode: .default, options: []) } catch { info.problems.append("category: \(error)") }
                    do { try s.setPreferredIOBufferDuration(ioBuffer) } catch { info.problems.append("IO buffer: \(error)") }
                }
                do { try s.setActive(true) } catch { info.problems.append("activate: \(error)") }
                info.sampleRate = s.sampleRate
                info.ioBuffer = s.ioBufferDuration
                info.outputLatency = s.outputLatency
                cont.resume(returning: info)
            }
        }
    }

    // MARK: notifications (SPEC-architecture §7.1 robustness)

    private func handleInterruption(began: Bool) {
        if began {
            core.suspend("interruption", stopEngine: true)
        } else {
            Task { @MainActor in
                let info = await Self.activateSession(configure: false, ioBuffer: self.preferredIOBuffer)
                for p in info.problems { self.core.fail("session: \(p)") }
                self.record(info)
                await self.core.resume("interruption")
            }
        }
    }

    private func installObservers() {
        guard observers.isEmpty else { return }
        let nc = NotificationCenter.default
        let session = AVAudioSession.sharedInstance()

        observers.append(nc.addObserver(forName: AVAudioSession.interruptionNotification, object: session, queue: .main) { [weak self] n in
            let raw = n.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt
            let began = raw.flatMap(AVAudioSession.InterruptionType.init(rawValue:)) == .began
            MainActor.assumeIsolated {
                Log.mark("audio", "interruption \(began ? "began" : "ended")")
                self?.handleInterruption(began: began)
            }
        })
        observers.append(nc.addObserver(forName: AVAudioSession.mediaServicesWereResetNotification, object: session, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self else { return }
                Log.mark("audio", "media services were reset: rebuilding the engine")
                Task { @MainActor in
                    let info = await Self.activateSession(configure: true, ioBuffer: self.preferredIOBuffer)
                    for p in info.problems { self.core.fail("session: \(p)") }
                    self.record(info)
                    await self.core.bringUp("media services reset", rebuild: true)
                }
            }
        })
        observers.append(nc.addObserver(forName: AVAudioSession.routeChangeNotification, object: session, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self else { return }
                Task { @MainActor in
                    let info = await Self.activateSession(configure: false, ioBuffer: self.preferredIOBuffer)
                    self.record(info)
                    self.logLatency()
                }
            }
        })
        observers.append(nc.addObserver(forName: .AVAudioEngineConfigurationChange, object: nil, queue: .main) { [weak self] n in
            let sender = (n.object as AnyObject?).map(ObjectIdentifier.init)
            MainActor.assumeIsolated { self?.configurationChanged(sender) }
        })
        observers.append(nc.addObserver(forName: UIApplication.didEnterBackgroundNotification, object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated { self?.core.suspend("background") }
        })
        observers.append(nc.addObserver(forName: UIApplication.willEnterForegroundNotification, object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self else { return }
                Task { @MainActor in
                    let info = await Self.activateSession(configure: false, ioBuffer: self.preferredIOBuffer)
                    for p in info.problems { self.core.fail("session: \(p)") }
                    self.record(info)
                    await self.core.resume("background")
                }
            }
        })
    }

    /// The engine stops itself when the output's sample rate or channel count changes (a route change). Coalesced: a burst of
    /// notifications restarts once, with the output chain reconnected in the new format.
    private func configurationChanged(_ sender: ObjectIdentifier?) {
        guard let engine = core.graph?.engine, sender == nil || sender == ObjectIdentifier(engine) else { return }
        guard !configChangePending else { return }
        configChangePending = true
        core.ticker.after(0.05) { [weak self] in
            guard let self else { return }
            self.configChangePending = false
            guard self.core.suspendReasons.isEmpty, !(self.core.graph?.isRunning ?? true) else { return }
            Task { @MainActor in await self.core.bringUp("configuration change", reconnect: true) }
        }
    }
}

#endif
