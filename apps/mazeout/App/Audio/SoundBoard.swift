// Debug harness: compiled into Debug and Measure only (`#if DEBUG || PC_MEASURE`), never into the Release (store) build.
// tools/harness_gate.py (CI) fails when a harness type is used outside that gate.
#if DEBUG || PC_MEASURE
#if os(iOS)
@preconcurrency import AVFoundation
import SwiftUI
import UIKit
import PathCore

// AUDIO A3 (SPEC-architecture §9.5 SoundBoard, §12.2 A3; SPEC-motion-audio §11.2, §11.6, §12, §15.5). The debug host
// `-pc.go soundboard`:
// - every SoundID (9), every cue moment (11, `audio.json cues`), every MusicID (2) and every Haptic (10) on a button;
// - a latency button: logs the §9.3 line `[PC][audio] latency io <ms> out <ms>` again, and handler → schedule for one click,
//   plus the time from the schedule to the click's first sample at the mixer output;
// - the Sound / Music / Haptic toggles, through `ShellSettings.toggle` (the same path as the Pause and Settings toggles);
// - the interruption hook: `AudioEngine.debugInterruption(began:)` runs the system's interruption path (simctl cannot
//   interrupt a simulator's audio session).
// `-pc.lab selftest` runs `SoundCheck` over all of it on the app's own engine and writes Documents/soundboard.json, then
// Documents/lab-ready.json, then prints `[PC][lab] soundboard:selftest done`. Tests/AudioEngineTests.swift runs the same
// checks on a private engine.
//
// Proof is MEASURED, not assumed: `OutputMeter` taps the engine's main mixer output (read only; the tap does not change
// what is heard) and reports the peak inside a host-time window, and the first sample above −60 dBFS. A cue passes when
// it reaches the output at its file's own peak (±1.5 dB; the chain is unity below the −1 dBFS ceiling, SPEC §7.1 / A2).
// Sound OFF passes when the output stays below −60 dBFS; Sound ON when the next click is back at full level at once.
// Every string here is verbatim (a debug host; nothing goes into the strings catalogue).

extension AudioEntry {
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? {
        name == LabID.soundboard.rawValue ? AnyView(SoundBoard(app: app)) : nil
    }
}

// MARK: - OutputMeter

/// A tap on the engine's main mixer output. Thread-safe: the tap block runs on AVAudioEngine's tap thread (not the render
/// thread); readers take the lock. Windows are in host seconds (`AVAudioTime.seconds(forHostTime:)`, the clock of
/// `CACurrentMediaTime`), matched against each tap buffer's own host time, so audio from before `arm` never counts.
final class OutputMeter: @unchecked Sendable {
    struct Reading: Sendable, CustomStringConvertible {
        /// Linear peak over every channel inside the window.
        var peak: Float = 0
        /// Host seconds of the first sample at or above the threshold inside the window.
        var onset: Double?
        /// Every sample of the window has been delivered.
        var covered = false
        /// The tap buffers carried valid host times (else the window is approximated by arrival time).
        var timed = true
        var buffers = 0
        var peakDB: Float { OutputMeter.db(peak) }
        var description: String {
            String(format: "peak %.1f dBFS%@, %d buffers%@", peakDB, onset == nil ? " (no onset)" : "", buffers,
                   timed ? "" : " (untimed)")
        }
    }

    static func db(_ v: Float) -> Float { v > 0 ? 20 * log10f(v) : -200 }
    static func hostNow() -> Double { AVAudioTime.seconds(forHostTime: mach_absolute_time()) }

    private let lock = NSLock()
    private var mixer: AVAudioMixerNode?
    private var engineID: ObjectIdentifier?
    private var armed = false
    private var from = 0.0
    private var to = 0.0
    private var threshold: Float = 0.001
    private var reading = Reading()
    private var totalBuffers = 0
    private var lastArrival = 0.0
    private var live: [(peak: Float, at: Double)] = []

    deinit { mixer?.removeTap(onBus: 0) }

    /// Installs the tap on `engine`'s main mixer (replacing any earlier tap of ours). Main thread, engine running.
    func attach(_ engine: AVAudioEngine) {
        detach()
        let m = engine.mainMixerNode
        m.removeTap(onBus: 0)                                     // a second tap on one bus raises
        m.installTap(onBus: 0, bufferSize: 1024, format: nil, block: Self.block(self))
        lock.lock()
        mixer = m
        engineID = ObjectIdentifier(engine)
        lastArrival = 0                                           // "feeding" only once a real buffer arrives
        lock.unlock()
    }

    func detach() {
        lock.lock()
        let m = mixer
        mixer = nil
        engineID = nil
        lock.unlock()
        m?.removeTap(onBus: 0)
    }

    /// True when the tap sits on `engine` and delivered a buffer within `within` seconds.
    func isFeeding(_ engine: AVAudioEngine, within: Double = 0.6) -> Bool {
        lock.lock(); defer { lock.unlock() }
        return engineID == ObjectIdentifier(engine) && Self.hostNow() - lastArrival < within
    }

    var buffersReceived: Int {
        lock.lock(); defer { lock.unlock() }
        return totalBuffers
    }

    /// Starts a window [from, to] (host seconds).
    func arm(from: Double, to: Double, threshold: Float = 0.001) {
        lock.lock(); defer { lock.unlock() }
        armed = true
        self.from = from
        self.to = to
        self.threshold = threshold
        reading = Reading()
    }

    func snapshot() -> Reading {
        lock.lock(); defer { lock.unlock() }
        return reading
    }

    /// Ends the window and returns what it saw.
    func disarm() -> Reading {
        lock.lock(); defer { lock.unlock() }
        armed = false
        return reading
    }

    /// The loudest tap buffer that ended within the last `seconds` (the live meter).
    func livePeakDB(over seconds: Double = 0.3) -> Float {
        lock.lock(); defer { lock.unlock() }
        let now = Self.hostNow()
        return Self.db(live.filter { now - $0.at <= seconds }.map(\.peak).max() ?? 0)
    }

    // MARK: tap thread

    private static func block(_ meter: OutputMeter) -> AVAudioNodeTapBlock {
        { buffer, when in meter.consume(buffer, when) }
    }

    private func consume(_ buffer: AVAudioPCMBuffer, _ when: AVAudioTime) {
        let n = Int(buffer.frameLength)
        guard n > 0, let data = buffer.floatChannelData else { return }
        let channels = Int(buffer.format.channelCount)
        let rate = buffer.format.sampleRate
        let arrival = Self.hostNow()
        let start: Double? = when.isHostTimeValid ? AVAudioTime.seconds(forHostTime: when.hostTime) : nil
        var whole: Float = 0
        for c in 0..<channels {
            let p = data[c]
            for i in 0..<n { let v = abs(p[i]); if v > whole { whole = v } }
        }
        lock.lock(); defer { lock.unlock() }
        totalBuffers += 1
        lastArrival = arrival
        live.append((whole, start.map { $0 + Double(n) / rate } ?? arrival))
        if live.count > 64 { live.removeFirst(live.count - 64) }
        guard armed else { return }
        reading.buffers += 1
        var i0 = 0, i1 = n
        if let start {
            i0 = max(0, Int(((from - start) * rate).rounded(.up)))
            i1 = min(n, Int(((to - start) * rate).rounded(.down)) + 1)
            if start + Double(n) / rate >= to { reading.covered = true }
        } else {
            reading.timed = false
            if arrival < from { return }
            if arrival >= to + 0.1 { reading.covered = true }
        }
        guard i0 < i1 else { return }
        for i in i0..<i1 {
            var v: Float = 0
            for c in 0..<channels { let a = abs(data[c][i]); if a > v { v = a } }
            if v > reading.peak { reading.peak = v }
            if reading.onset == nil, v >= threshold {
                reading.onset = start.map { $0 + Double(i) / rate } ?? arrival
            }
        }
    }
}

// MARK: - SoundCheck

/// Every A3 acceptance check, runnable on any `AudioEngine` + `Haptics` + `PlayerStore` (the SoundBoard runs it on the
/// app's own; Tests/AudioEngineTests.swift on private ones). Each step appends `Item`s and logs `[PC][soundboard] PASS|FAIL`.
/// Settings are flipped with `ShellSettings.toggle(store:audio:haptics:…)` (the Pause/Settings path) and restored at the end.
@MainActor final class SoundCheck {
    struct Item: Codable, Sendable, Equatable {
        var name: String
        var pass: Bool
        var detail: String
    }

    struct Measurement: Sendable {
        var reading: OutputMeter.Reading
        /// Host seconds when the play call was made.
        var scheduledAt: Double
        /// The play call's own duration (handler → scheduled), µs.
        var handlerMicros: Double
        /// The first sample above −60 dBFS after the schedule, ms (nil: none in the window).
        var onsetMs: Double? { reading.onset.map { ($0 - scheduledAt) * 1000 } }
    }

    /// A cue at the output within this many dB of its file's own peak (A2: unity below the ceiling).
    static let levelTolerance: Float = 1.5
    /// "Silent": below −60 dBFS (a faded voice sits at −80 dB under its cue).
    static let silence: Float = 0.001

    let engine: AudioEngine
    let haptics: Haptics?
    let store: PlayerStore
    let meter: OutputMeter
    private(set) var items: [Item] = []
    /// Called after each item (the SoundBoard lists them live).
    var onItem: ((Item) -> Void)?
    private var errorsAtStart = 0

    init(engine: AudioEngine, haptics: Haptics?, store: PlayerStore, meter: OutputMeter = OutputMeter()) {
        self.engine = engine
        self.haptics = haptics
        self.store = store
        self.meter = meter
        errorsAtStart = engine.status.errors
    }

    var passed: Int { items.filter(\.pass).count }
    var allPassed: Bool { !items.isEmpty && items.allSatisfy(\.pass) }

    /// All steps in order; the settings are back to their starting values afterwards.
    @discardableResult
    func run() async -> [Item] {
        let saved = store.state.settings
        await checkEngine()
        await checkSounds()
        await checkMoments()
        checkMusicAPI()
        await checkHaptics()
        await checkLatency()
        await checkSoundToggle()
        await checkMusicToggle()
        await checkInterruption()
        restore(saved)
        checkErrors()
        return items
    }

    // MARK: steps

    /// The engine runs with every cue decoded, and the meter sees the output.
    func checkEngine() async {
        await engine.warmUp()
        let s = engine.status
        errorsAtStart = s.errors
        record("engine running", s.phase == .running && s.running, "\(s)")
        record("every SoundID decoded", s.loaded == SoundID.allCases.count && s.missing.isEmpty,
               "\(s.loaded)/\(SoundID.allCases.count) loaded, missing [\(s.missing.joined(separator: ","))], \(s.loadedBytes / 1024) KB")
        record("\(s.voices) idle voices", s.voices == engine.core.voiceCount && s.busy == 0, "voices \(s.busy)/\(s.voices) busy")
        let feeding = await ensureMeter()
        record("output meter on the main mixer", feeding && meter.buffersReceived > 0, "\(meter.buffersReceived) tap buffers so far")
    }

    /// Each SoundID through `play` (the contract call): scheduled at once, and heard at its file's peak.
    func checkSounds() async {
        await ensureMeter()
        for s in SoundID.allCases {
            let expected = Self.filePeak(engine.core.bank.buffer(s))
            let plays = engine.status.plays
            let m = await measure(window: engine.core.bank.duration(s) + 0.25) { engine.play(s) }
            let got = m.reading.peakDB
            let ok = engine.status.plays == plays + 1 && m.onsetMs != nil && abs(got - expected) <= Self.levelTolerance
            record("play \(s.rawValue)", ok, String(format: "out %.1f dBFS (file %.1f), onset %@, play call %.0f µs, %@", got, expected,
                                                    m.onsetMs.map { String(format: "%.1f ms", $0) } ?? "none",
                                                    m.handlerMicros, m.reading.description))
        }
    }

    /// Each `audio.json cues.<moment>` plays its mapped sound; `arrowTap` (the owner's tap slot) plays nothing (v552, MA3).
    func checkMoments() async {
        let map = engine.cues
        for moment in CueMoment.allCases {
            let mapped = map.sound(for: moment)
            let plays = engine.status.plays
            let scheduled = engine.cue(moment)
            let delta = engine.status.plays - plays
            let ok = mapped == nil ? (!scheduled && delta == 0) : (scheduled && delta == 1 && engine.status.last == mapped?.id.rawValue)
            record("cue \(moment.rawValue)", ok, mapped.map { "→ \($0.id.rawValue) gain \($0.gain)" } ?? "→ silent (no cue by design)")
            try? await Task.sleep(nanoseconds: 60_000_000)          // > minRetrigger: three moments share uiClick
        }
        record("in-level moments silent", map.sound(for: .arrowTap) == nil && Set(map.cues.keys).isSubset(of: Self.shellMoments),
               "mapped: " + map.cues.keys.map(\.rawValue).sorted().joined(separator: ","))
        await settle(3.1)                                              // coinCollect is 2.9 s
    }

    /// MA2: no music. playMusic / stopMusic are no-ops, nothing is loaded, and the music bus carries nothing.
    func checkMusicAPI() {
        for m in MusicID.allCases { engine.playMusic(m, fade: 0) }
        let s = engine.status
        let g = engine.core.graph
        let silentBus = g.map { $0.decks.isEmpty ? $0.musicBus.outputVolume == 0 : true } ?? false
        record("music (MA2: none)", !s.musicEnabled && s.music == nil && engine.core.music.tracks.isEmpty && silentBus,
               "enabled \(s.musicEnabled), track \(s.music ?? "none"), decks \(g?.decks.count ?? -1), music bus volume \(g?.musicBus.outputVolume ?? -1)")
        engine.stopMusic(fade: 0)
    }

    /// Every Haptic through `play` fires once, from the run-loop flush (no explicit flush); the priority rule holds in one
    /// turn; the Haptic toggle gates it.
    func checkHaptics() async {
        guard let h = haptics else { record("haptics", false, "app.haptics is not the A2 Haptics"); return }
        if !store.state.settings.haptic { toggle(\.haptic, "haptic") }
        h.prepare()
        let probe = MainLoopProbe(haptics: h)
        defer { probe.remove() }
        for c in Haptic.allCases {
            let before = h.fired[c] ?? 0
            probe.mark()
            h.play(c)
            var waited = 0.0
            while (h.fired[c] ?? 0) == before && waited < 0.4 {
                try? await Task.sleep(nanoseconds: 2_000_000); waited += 0.002
            }
            try? await Task.sleep(nanoseconds: 40_000_000)          // > 1 frame before the next request
            let row = h.map.row(c)
            record("haptic \(c.rawValue)", (h.fired[c] ?? 0) == before + 1 && h.lastFired == c, "\(row); \(probe.report())")
        }
        // D8 (the haptic on the visual's frame): a request made in a CADisplayLink callback — inside the UI update, where the
        // board's beats and the release handler run — must fire before that update's frame is done (< 1 frame, 16.7 ms).
        var delays: [Double] = []
        for _ in 0..<5 { if let d = await probe.flushDelay(from: .displayLink, .tap) { delays.append(d) } }
        record("haptic flush within the frame (display-link request)", delays.count == 5 && (delays.max() ?? 99) < 1000.0 / 60,
               "delays " + delays.map { String(format: "%.2f", $0) }.joined(separator: ", ") + " ms (5 requests)")
        try? await Task.sleep(nanoseconds: 40_000_000)
        let tap = h.fired[.tap] ?? 0, lost = h.fired[.heartLost] ?? 0, dropped = h.dropped
        probe.mark()
        h.play(.tap)
        h.play(.heartLost)                                             // same turn: heartLost > tap (§12.2)
        var waited = 0.0
        while (h.fired[.heartLost] ?? 0) == lost && waited < 0.4 {
            try? await Task.sleep(nanoseconds: 2_000_000); waited += 0.002
        }
        try? await Task.sleep(nanoseconds: 40_000_000)
        record("haptic priority (one per frame)", (h.fired[.heartLost] ?? 0) == lost + 1 && (h.fired[.tap] ?? 0) == tap && h.dropped == dropped + 1,
               "tap + heartLost in one turn → heartLost, 1 dropped; \(probe.report())")
        toggle(\.haptic, "haptic")                                     // off
        let off = h.fired[.tap] ?? 0
        h.play(.tap)
        try? await Task.sleep(nanoseconds: 70_000_000)
        record("haptic toggle gates", !h.enabled && (h.fired[.tap] ?? 0) == off, "Haptic OFF: tap did not fire")
        toggle(\.haptic, "haptic")                                     // on
    }

    /// §9.3 `latency io <ms> out <ms>` (again, as at boot) + handler → schedule and schedule → first output sample.
    func checkLatency() async {
        let line = await logLatency()
        record("latency logged", line.io > 0, line.text)
    }

    /// The latency button: returns what it logged.
    @discardableResult
    func logLatency() async -> (io: Double, text: String) {
        let io = engine.ioBufferDuration * 1000
        let out = (engine.outputLatency - engine.ioBufferDuration) * 1000
        Log.mark("audio", String(format: "latency io %.1f out %.1f", io, out))
        _ = await ensureMeter()
        let m = await measure(window: 0.3) { engine.play(.uiClick) }
        let text = String(format: "io %.1f ms, out %.1f ms, play call %.0f µs, schedule → first output sample %@", io, out,
                          m.handlerMicros, m.onsetMs.map { String(format: "%.1f ms", $0) } ?? "none")
        Log.mark("audio", String(format: "latency handler→schedule %.0f µs, schedule→output %@ (uiClick; the route adds io %.1f + out %.1f ms)",
                                 m.handlerMicros, m.onsetMs.map { String(format: "%.1f ms", $0) } ?? "none", io, out))
        return (io, text)
    }

    /// Sound OFF: a cue already sounding goes silent (after the 60 ms that lets the toggle's own click finish), new cues are
    /// refused and nothing reaches the output; Sound ON: the next cue is at full level at once.
    func checkSoundToggle() async {
        if !store.state.settings.sound { toggle(\.sound, "sound") }
        await settle(0.2)
        _ = await ensureMeter()
        let t0 = OutputMeter.hostNow()
        engine.play(.coinCollect)                                      // 2.9 s: glitter, then 5 clinks at 1.12…1.46 s
        meter.arm(from: t0, to: t0 + 0.45)
        try? await Task.sleep(nanoseconds: 450_000_000)
        let before = await collect()
        toggle(\.sound, "sound")                                       // OFF at ≈ 0.45 s
        let off = OutputMeter.hostNow()
        meter.arm(from: off + 0.2, to: t0 + 2.9)                        // covers the clinks
        let plays = engine.status.plays
        for s in SoundID.allCases { engine.play(s) }                   // refused while OFF
        _ = engine.cue(.uiButton)
        try? await Task.sleep(nanoseconds: UInt64(max(0, t0 + 2.9 - OutputMeter.hostNow()) * 1e9))
        let during = await collect()
        record("Sound OFF silences the SFX output",
               before.peakDB > -20 && during.peak < Self.silence && engine.status.plays == plays && !engine.status.soundOn,
               String(format: "coin before %.1f dBFS → after OFF %.1f dBFS (clinks included); %d plays refused", before.peakDB,
                      during.peakDB, SoundID.allCases.count + 1))
        await settle(0.3)                                              // the faded voice restores (cue end + 30 ms + pump)
        toggle(\.sound, "sound")                                       // ON
        let expected = Self.filePeak(engine.core.bank.buffer(.uiClick))
        let m = await measure(window: 0.3) { engine.play(.uiClick) }
        record("Sound ON is instant at full level", engine.status.soundOn && abs(m.reading.peakDB - expected) <= Self.levelTolerance,
               String(format: "first click after ON %.1f dBFS (file %.1f), onset %@", m.reading.peakDB, expected,
                      m.onsetMs.map { String(format: "%.1f ms", $0) } ?? "none"))
    }

    /// The Music toggle flips the setting; the music bus carries nothing either way (MA2: the inert button, U-7).
    func checkMusicToggle() async {
        await ensureMeter()
        let start = store.state.settings.music
        var ok = true
        var notes: [String] = []
        for _ in 0..<2 {
            let now = toggle(\.music, "music")
            let m = await measure(window: 0.3) {}
            let s = engine.status
            let busSilent = engine.core.graph.map { $0.decks.isEmpty && $0.musicBus.outputVolume == 0 } ?? false
            ok = ok && s.musicOn == now && s.music == nil && m.reading.peak < Self.silence && busSilent
            notes.append(String(format: "music %@: output %.1f dBFS, bus volume %.0f", now ? "ON" : "OFF", m.reading.peakDB,
                                engine.core.graph?.musicBus.outputVolume ?? -1))
        }
        record("Music toggle: music bus silent", ok && store.state.settings.music == start, notes.joined(separator: "; "))
    }

    /// `debugInterruption(began: true)` stops the engine as the system does; nothing plays. The end re-activates the session
    /// and restarts the engine and the idle voices: the first cue after it is heard at full level.
    func checkInterruption() async {
        if !store.state.settings.sound { toggle(\.sound, "sound") }
        await ensureMeter()
        let restarts = engine.status.restarts
        engine.debugInterruption(began: true)
        var waited = 0.0
        while (engine.status.phase != .suspended || engine.status.running) && waited < 2 {
            try? await Task.sleep(nanoseconds: 50_000_000); waited += 0.05
        }
        let down = engine.status
        let drops = down.drops
        let m0 = await measure(window: 0.3) { engine.play(.uiClick) }
        record("interruption began: engine stopped", down.phase == .suspended && !down.running && engine.status.drops == drops + 1
               && m0.reading.peak < Self.silence,
               String(format: "phase %@, running %@, click dropped, output %.1f dBFS", down.phase.rawValue, down.running ? "yes" : "no",
                      m0.reading.peakDB))
        let t = OutputMeter.hostNow()
        engine.debugInterruption(began: false)
        waited = 0
        while !(engine.status.phase == .running && engine.status.running) && waited < 3 {
            try? await Task.sleep(nanoseconds: 50_000_000); waited += 0.05
        }
        let up = engine.status
        let back = (OutputMeter.hostNow() - t) * 1000
        let feeding = await ensureMeter()
        let expected = Self.filePeak(engine.core.bank.buffer(.uiClick))
        let m = await measure(window: 0.3) { engine.play(.uiClick) }
        record("interruption ended: engine + idle voices restarted",
               up.phase == .running && up.running && up.restarts == restarts + 1 && up.busy == 0 && up.voices == engine.core.voiceCount
               && feeding && abs(m.reading.peakDB - expected) <= Self.levelTolerance && m.onsetMs != nil,
               String(format: "back in %.0f ms, restarts %d → %d, voices %d/%d busy, first click %.1f dBFS (file %.1f), onset %@", back,
                      restarts, up.restarts, up.busy, up.voices, m.reading.peakDB, expected,
                      m.onsetMs.map { String(format: "%.1f ms", $0) } ?? "none"))
    }

    /// No engine error was logged while the checks ran.
    func checkErrors() {
        let s = engine.status
        let new = Array(engine.core.errorLog.suffix(max(0, s.errors - errorsAtStart)))
        record("no engine error", s.errors == errorsAtStart && s.missing.isEmpty,
               "errors \(s.errors) (at start \(errorsAtStart))" + (new.isEmpty ? "" : ": " + new.joined(separator: " | ")))
    }

    // MARK: helpers

    /// The moments that belong to the shell (UI clicks, the unlock chime, the home-return cues); every in-level event has none.
    static let shellMoments: Set<CueMoment> = [.uiButton, .celebrationSkip, .dismissTap, .unlockOverlay, .homePayout, .clawToken,
                                               .clawMerge, .clawTick, .clawComplete, .streakPop]

    /// The loudest sample of a decoded buffer, dBFS.
    static func filePeak(_ b: AVAudioPCMBuffer?) -> Float {
        guard let b, let d = b.floatChannelData else { return -200 }
        var p: Float = 0
        for c in 0..<Int(b.format.channelCount) { for i in 0..<Int(b.frameLength) { p = max(p, abs(d[c][i])) } }
        return OutputMeter.db(p)
    }

    /// The tap is on the engine now running and buffers flow (re-attached after a rebuild or a stop).
    @discardableResult
    func ensureMeter() async -> Bool {
        guard engine.core.isRunning, !engine.core.isTransitioning, let g = engine.core.graph else { return false }
        if meter.isFeeding(g.engine) { return true }
        meter.attach(g.engine)
        var waited = 0.0
        while !meter.isFeeding(g.engine, within: 0.3) && waited < 1.5 {
            try? await Task.sleep(nanoseconds: 50_000_000); waited += 0.05
        }
        return meter.isFeeding(g.engine)
    }

    /// Arms a window from now, runs `action` (the play call, timed), waits for the window to be delivered.
    func measure(window: Double, _ action: () -> Void) async -> Measurement {
        let t0 = OutputMeter.hostNow()
        meter.arm(from: t0, to: t0 + window)
        let h0 = OutputMeter.hostNow()
        action()
        let h1 = OutputMeter.hostNow()
        try? await Task.sleep(nanoseconds: UInt64(window * 1e9))
        let r = await collect()
        return Measurement(reading: r, scheduledAt: h0, handlerMicros: (h1 - h0) * 1e6)
    }

    /// Waits (≤ 1 s) until the armed window has been delivered, then disarms.
    func collect() async -> OutputMeter.Reading {
        var waited = 0.0
        while !meter.snapshot().covered && waited < 1.0 {
            try? await Task.sleep(nanoseconds: 40_000_000); waited += 0.04
        }
        return meter.disarm()
    }

    private func settle(_ seconds: Double) async { try? await Task.sleep(nanoseconds: UInt64(seconds * 1e9)) }

    @discardableResult
    private func toggle(_ key: WritableKeyPath<PlayerState.Settings, Bool>, _ name: String) -> Bool {
        ShellSettings.toggle(store: store, audio: engine, haptics: haptics ?? SilentHaptics(), key, name: name)
    }

    private func restore(_ s: PlayerState.Settings) {
        if store.state.settings.sound != s.sound { toggle(\.sound, "sound") }
        if store.state.settings.music != s.music { toggle(\.music, "music") }
        if store.state.settings.haptic != s.haptic { toggle(\.haptic, "haptic") }
    }

    private func record(_ name: String, _ pass: Bool, _ detail: String) {
        let item = Item(name: name, pass: pass, detail: detail)
        items.append(item)
        if pass { Log.mark("soundboard", "PASS \(name): \(detail)") } else { Log.error("soundboard", "FAIL \(name): \(detail)") }
        onItem?(item)
    }
}

// MARK: - MainLoopProbe

/// Watches the main run loop right after `Haptics`' flush observer (order 1,999,000) and before Core Animation's commit
/// observer (2,000,000): when a haptic fired, in which pass, how long after `mark()`, and how many passes went by without
/// one. It answers A2's open question for A3: does the end-of-turn flush run in the same turn as the request?
@MainActor final class MainLoopProbe {
    private var observer: CFRunLoopObserver?
    private weak var haptics: Haptics?
    private var markedAt = 0.0
    private var lastTotal = 0
    private var passes = 0
    private var waitingPasses = 0
    private var firedAt: Double?
    private var firedActivity = ""
    private var passesBeforeFire = 0

    init(haptics: Haptics) {
        self.haptics = haptics
        lastTotal = haptics.fired.values.reduce(0, +)
        let activities = CFRunLoopActivity.beforeWaiting.rawValue | CFRunLoopActivity.exit.rawValue
        let obs = CFRunLoopObserverCreateWithHandler(kCFAllocatorDefault, activities, true, Haptics.flushOrder + 500) { [weak self] _, act in
            MainActor.assumeIsolated { self?.pass(act) }
        }
        CFRunLoopAddObserver(CFRunLoopGetMain(), obs, .commonModes)
        observer = obs
    }

    func remove() {
        if let o = observer { CFRunLoopRemoveObserver(CFRunLoopGetMain(), o, .commonModes) }
        observer = nil
    }

    /// Call right before `haptics.play`.
    func mark() {
        markedAt = CACurrentMediaTime()
        passes = 0
        waitingPasses = 0
        firedAt = nil
        passesBeforeFire = 0
        lastTotal = haptics?.fired.values.reduce(0, +) ?? 0
    }

    private func pass(_ act: CFRunLoopActivity) {
        passes += 1
        if act == .beforeWaiting { waitingPasses += 1 }
        let total = haptics?.fired.values.reduce(0, +) ?? 0
        if total != lastTotal, firedAt == nil {
            firedAt = CACurrentMediaTime()
            firedActivity = act == .beforeWaiting ? "beforeWaiting" : "exit"
            passesBeforeFire = passes - 1
        }
        lastTotal = total
    }

    var fireDelayMs: Double? { firedAt.map { ($0 - markedAt) * 1000 } }

    /// Idle main run loop over `seconds`: beforeWaiting/exit passes, display-link ticks and the longest gap between passes.
    static func idleStats(seconds: Double) async -> String {
        final class Box { var times: [Double] = []; var ticks = 0 }
        let box = Box()
        let obs = CFRunLoopObserverCreateWithHandler(kCFAllocatorDefault, CFRunLoopActivity.beforeWaiting.rawValue, true, 1_999_500) { _, _ in
            box.times.append(CACurrentMediaTime())
        }
        CFRunLoopAddObserver(CFRunLoopGetMain(), obs, .commonModes)
        let tick = LinkTarget { box.ticks += 1 }
        let link = CADisplayLink(target: tick, selector: #selector(LinkTarget.fire))
        link.add(to: .main, forMode: .common)
        try? await Task.sleep(nanoseconds: UInt64(seconds * 1e9))
        link.invalidate()
        CFRunLoopRemoveObserver(CFRunLoopGetMain(), obs, .commonModes)
        let gaps = zip(box.times.dropFirst(), box.times).map { ($0 - $1) * 1000 }
        return String(format: "%.1f s idle: %d beforeWaiting passes, %d display-link ticks, longest gap %.1f ms", seconds, box.times.count,
                      box.ticks, gaps.max() ?? 0)
    }

    /// Where the request comes from, for `flushDelay(from:)`.
    enum Origin: String, CaseIterable { case displayLink, mainQueue, timer, task }

    /// Requests `h` from `origin` and returns how long after the request the flush fired it (ms), or nil within 300 ms.
    func flushDelay(from origin: Origin, _ h: Haptic) async -> Double? {
        guard let hp = haptics else { return nil }
        try? await Task.sleep(nanoseconds: 40_000_000)                // > 1 frame since the last haptic
        let request = { [weak self] in
            self?.mark()
            hp.play(h)
        }
        switch origin {
        case .displayLink:
            var fired = false
            let t = LinkTarget {}
            let link = CADisplayLink(target: t, selector: #selector(LinkTarget.fire))
            t.body = { if !fired { fired = true; request() } }
            link.add(to: .main, forMode: .common)
            try? await Task.sleep(nanoseconds: 300_000_000)
            link.invalidate()
        case .mainQueue:
            DispatchQueue.main.async { MainActor.assumeIsolated { request() } }
            try? await Task.sleep(nanoseconds: 300_000_000)
        case .timer:
            let timer = Timer(timeInterval: 0.01, repeats: false) { _ in MainActor.assumeIsolated { request() } }
            RunLoop.main.add(timer, forMode: .common)
            try? await Task.sleep(nanoseconds: 300_000_000)
        case .task:
            request()
            try? await Task.sleep(nanoseconds: 300_000_000)
        }
        return fireDelayMs
    }

    func report() -> String {
        guard let d = fireDelayMs else { return "not fired; \(passes) run-loop passes (\(waitingPasses) beforeWaiting) since the request" }
        return String(format: "flushed %.2f ms after the request, in pass %d (%@)", d, passesBeforeFire + 1, firedActivity)
    }
}

/// A CADisplayLink target (the link retains it) that runs a closure on each tick.
final class LinkTarget: NSObject {
    var body: () -> Void
    init(_ body: @escaping () -> Void) { self.body = body }
    @objc func fire() { body() }
}

// MARK: - SoundBoard (the screen)

@MainActor @Observable final class SoundBoardModel {
    @ObservationIgnored private(set) weak var app: AppModel?
    @ObservationIgnored let meter = OutputMeter()
    var lastPeak: [SoundID: Float] = [:]
    var lastOnset: [SoundID: Double] = [:]
    var results: [SoundCheck.Item] = []
    /// Each file's peak (dBFS) and length (s), read once from the decoded bank (the grid never scans samples).
    var files: [SoundID: (peak: Float, seconds: Double)] = [:]
    /// Moment → mapped sound ("" = silent) and the music switch, copied once the engine is up (observed, so the lazy grids
    /// redraw; `app` itself is not observed).
    var moments: [CueMoment: String] = [:]
    var musicEnabled = false
    var checking = false
    var latency = ""
    var note = ""

    var engine: AudioEngine? { app?.audio as? AudioEngine }
    var haptics: Haptics? { app?.haptics as? Haptics }

    func start(_ app: AppModel) async {
        self.app = app
        guard let e = engine else {
            note = "app.audio is not the A2 AudioEngine"
            finishIdle(app)
            return
        }
        guard !e.muted else {
            note = "capture mode: audio muted (no session, no engine)"
            finishIdle(app)
            return
        }
        await e.warmUp()
        files = Dictionary(uniqueKeysWithValues: SoundID.allCases.map {
            ($0, (SoundCheck.filePeak(e.core.bank.buffer($0)), e.core.bank.duration($0)))
        })
        moments = Dictionary(uniqueKeysWithValues: CueMoment.allCases.map { ($0, e.cues.sound(for: $0)?.id.rawValue ?? "") })
        musicEnabled = e.status.musicEnabled
        await check().ensureMeter()
        if app.args.lab == "background" {
            watchForeground()
            finishIdle(app)
        } else if app.args.lab == "loop" {
            await loopReport()
            CaptureReady.mark(screen: "soundboard:loop", app: app, file: "lab-ready.json")
            Log.mark("lab", "soundboard:loop done")
        } else if app.args.lab == "selftest" || app.args.lab == "haptics" {
            await selfTest(hapticsOnly: app.args.lab == "haptics")
        } else {
            finishIdle(app)
        }
    }

    func stop() {
        meter.detach()
        if let o = foregroundObserver { NotificationCenter.default.removeObserver(o) }
        foregroundObserver = nil
    }

    @ObservationIgnored private var foregroundObserver: NSObjectProtocol?

    /// `-pc.lab background`: after every return to the foreground (A2's background → resume path), wait for the engine and
    /// measure one click at the output; logs `[PC][soundboard] PASS|FAIL foreground return …`.
    func watchForeground() {
        foregroundObserver = NotificationCenter.default.addObserver(forName: UIApplication.didBecomeActiveNotification, object: nil,
                                                                    queue: .main) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self else { return }
                Task { @MainActor in await self.checkAfterForeground() }
            }
        }
    }

    private func checkAfterForeground() async {
        guard let e = engine, !checking else { return }
        var waited = 0.0
        while !(e.status.phase == .running && e.status.running) && waited < 3 {
            try? await Task.sleep(nanoseconds: 50_000_000); waited += 0.05
        }
        let c = check()
        let feeding = await c.ensureMeter()
        let expected = SoundCheck.filePeak(e.core.bank.buffer(.uiClick))
        let m = await c.measure(window: 0.3) { e.play(.uiClick) }
        let s = e.status
        let ok = feeding && s.running && abs(m.reading.peakDB - expected) <= SoundCheck.levelTolerance && m.onsetMs != nil
        let detail = String(format: "restarts %d, click %.1f dBFS (file %.1f), onset %@, errors %d", s.restarts, m.reading.peakDB, expected,
                            m.onsetMs.map { String(format: "%.1f ms", $0) } ?? "none", s.errors)
        if ok { Log.mark("soundboard", "PASS foreground return: " + detail) } else { Log.error("soundboard", "FAIL foreground return: " + detail) }
    }

    /// `-pc.lab loop`: the main run loop's idle rhythm, and the haptic flush delay per request origin (3 trials each).
    func loopReport() async {
        guard let h = haptics else { return }
        Log.mark("soundboard", "loop " + (await MainLoopProbe.idleStats(seconds: 2)))
        let probe = MainLoopProbe(haptics: h)
        defer { probe.remove() }
        for origin in MainLoopProbe.Origin.allCases {
            var delays: [String] = []
            for _ in 0..<3 {
                let d = await probe.flushDelay(from: origin, .tap)
                delays.append(d.map { String(format: "%.2f", $0) } ?? "none")
            }
            Log.mark("soundboard", "loop flush delay from \(origin.rawValue): \(delays.joined(separator: ", ")) ms")
        }
    }

    /// A checker bound to the app's engine, store and haptics, sharing this screen's meter.
    func check() -> SoundCheck {
        let c = SoundCheck(engine: engine!, haptics: haptics, store: app!.store, meter: meter)
        c.onItem = { [weak self] item in self?.results.append(item) }
        return c
    }

    func play(_ s: SoundID) {
        guard let e = engine, !checking else { engine?.play(s); return }
        Task {
            let c = check()
            await c.ensureMeter()
            let m = await c.measure(window: e.core.bank.duration(s) + 0.2) { e.play(s) }
            lastPeak[s] = m.reading.peakDB
            lastOnset[s] = m.onsetMs
        }
    }

    func runLatency() {
        guard engine != nil, !checking else { return }
        Task {
            let r = await check().logLatency()
            latency = r.text
        }
    }

    /// `hapticsOnly` (`-pc.lab haptics`): the haptic step alone.
    func selfTest(hapticsOnly: Bool = false) async {
        guard let app, engine != nil, !checking else { return }
        checking = true
        results = []
        let c = check()
        if hapticsOnly { await c.checkHaptics() } else { await c.run() }
        checking = false
        let scenario = hapticsOnly ? "haptics" : "selftest"
        let report: [String: Any] = [
            "t": ProcessInfo.processInfo.systemUptime, "pass": c.passed, "total": c.items.count, "allPassed": c.allPassed,
            "status": engine?.status.description ?? "",
            "items": c.items.map { ["name": $0.name, "pass": $0.pass, "detail": $0.detail] as [String: Any] },
        ]
        Self.writeDocument("soundboard.json", report)
        Log.mark("lab", "soundboard:\(scenario) \(c.passed)/\(c.items.count) pass")
        CaptureReady.mark(screen: "soundboard:\(scenario)", app: app, file: "lab-ready.json")
        Log.mark("lab", "soundboard:\(scenario) done")
    }

    private func finishIdle(_ app: AppModel) {
        CaptureReady.mark(screen: "soundboard", app: app, file: "lab-ready.json")
        Log.mark("lab", "soundboard done")
    }

    static func writeDocument(_ name: String, _ json: [String: Any]) {
        guard let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first,
              let data = try? JSONSerialization.data(withJSONObject: json, options: [.prettyPrinted, .sortedKeys]) else { return }
        try? data.write(to: docs.appendingPathComponent(name), options: .atomic)
    }
}

struct SoundBoard: View {
    let app: AppModel
    @State private var model = SoundBoardModel()
    @Environment(\.shellMetrics) private var metrics

    private static let ink = Color.white
    private static let panel = Color.white.opacity(0.08)
    private static let accent = Color(red: 0.26, green: 0.62, blue: 1.0)

    var body: some View {
        ZStack(alignment: .top) {
            Color(red: 0.07, green: 0.10, blue: 0.18)
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        header
                        section("Sounds (SoundID)") { sounds }
                        section("Cue moments (audio.json cues)") { moments }
                        section("Haptics") { hapticsGrid }.id("haptics")
                        section("Music (MusicID)") { music }
                        section("Settings") { toggles }
                        section("Engine") { tools }
                        if !model.results.isEmpty { section("Self-test") { results } }
                    }
                    .padding(.horizontal, 14)
                    .padding(.top, metrics.safeTop + 4)
                    .padding(.bottom, metrics.safeBottom + 24)
                }
                .onAppear {
                    // `-pc.lab tools`: open scrolled to the lower half (haptics, music, settings, engine) for captures.
                    if app.args.lab == "tools" { proxy.scrollTo("haptics", anchor: .top) }
                }
            }
        }
        .frame(width: metrics.size.width, height: metrics.size.height)
        .foregroundStyle(Self.ink)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.soundboard")
        .task { await model.start(app) }
        .onDisappear { model.stop() }
    }

    // MARK: sections

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(verbatim: "SoundBoard").font(.system(size: 26, weight: .heavy, design: .rounded))
            TimelineView(.periodic(from: .now, by: 0.25)) { _ in
                let status = model.engine?.status.description ?? model.note
                VStack(alignment: .leading, spacing: 4) {
                    Text(verbatim: status)
                        .font(.system(size: 10.5, weight: .medium, design: .monospaced))
                        .opacity(0.8)
                        .accessibilityIdentifier("soundboard.status")
                    meterBar(model.meter.livePeakDB())
                }
            }
            if !model.note.isEmpty { Text(verbatim: model.note).font(.system(size: 12, weight: .semibold)).foregroundStyle(.orange) }
        }
    }

    private func meterBar(_ db: Float) -> some View {
        let u = CGFloat(min(max((db + 60) / 60, 0), 1))
        return HStack(spacing: 8) {
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.white.opacity(0.12))
                    Capsule().fill(db > -3 ? Color.red : Self.accent).frame(width: max(4, g.size.width * u))
                }
            }
            .frame(height: 8)
            Text(verbatim: db < -99 ? "−∞ dBFS" : String(format: "%.1f dBFS", db))
                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                .frame(width: 84, alignment: .trailing)
        }
        .accessibilityElement()
        .accessibilityIdentifier("soundboard.meter")
        .accessibilityValue(Text(verbatim: String(format: "%.1f", db)))
    }

    private var sounds: some View {
        grid(SoundID.allCases, id: \.rawValue) { s in
            let file = model.files[s]?.peak
            let dur = model.files[s]?.seconds ?? 0
            let last = model.lastPeak[s].map { String(format: "out %.1f", $0) } ?? "out –"
            tile(s.rawValue, detail: String(format: "%.2fs %.1fdB\n%@%@", dur, file ?? -200, last,
                                            model.lastOnset[s].map { String(format: " %.0fms", $0) } ?? ""),
                 id: "soundboard.sound.\(s.rawValue)", value: model.lastPeak[s].map { String(format: "%.1f", $0) }) { model.play(s) }
        }
    }

    private var moments: some View {
        grid(CueMoment.allCases, id: \.rawValue) { m in
            let mapped = model.moments[m] ?? ""
            tile(m.rawValue, detail: model.moments.isEmpty ? "…" : mapped.isEmpty ? "→ silent" : "→ \(mapped)",
                 id: "soundboard.moment.\(m.rawValue)", value: mapped.isEmpty ? "silent" : mapped) { _ = model.engine?.cue(m) }
        }
    }

    private var hapticsGrid: some View {
        TimelineView(.periodic(from: .now, by: 0.25)) { _ in
            grid(Haptic.allCases, id: \.rawValue) { h in
                let row = model.haptics.map { "\($0.map.row(h))" } ?? "–"
                let n = model.haptics?.fired[h] ?? 0
                tile(h.rawValue, detail: "\(row)\nfired \(n)", id: "soundboard.haptic.\(h.rawValue)", value: "\(n)") {
                    model.haptics?.play(h)
                }
            }
        }
    }

    private var music: some View {
        let enabled = model.musicEnabled
        return VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                ForEach(MusicID.allCases, id: \.rawValue) { m in
                    tile(m.rawValue, detail: enabled ? "play" : "no-op", id: "soundboard.music.\(m.rawValue)", value: nil) {
                        model.engine?.playMusic(m, fade: 0.3)
                    }
                }
                tile("stop", detail: enabled ? "fade 0.3 s" : "no-op", id: "soundboard.music.stop", value: nil) {
                    model.engine?.stopMusic(fade: 0.3)
                }
            }
            if !enabled {
                Text(verbatim: "music.enabled = false (SPEC-motion-audio §11.5 MA2): the game has no music; the Music button is inert.")
                    .font(.system(size: 11)).opacity(0.7)
            }
        }
    }

    private var toggles: some View {
        TimelineView(.periodic(from: .now, by: 0.25)) { _ in
            let s = app.store.state.settings
            HStack(spacing: 8) {
                toggleTile("Sound", on: s.sound, id: "soundboard.toggle.sound") { _ = ShellSettings.toggle(app, \.sound, name: "sound") }
                toggleTile("Music", on: s.music, id: "soundboard.toggle.music") { _ = ShellSettings.toggle(app, \.music, name: "music") }
                toggleTile("Haptic", on: s.haptic, id: "soundboard.toggle.haptic") { _ = ShellSettings.toggle(app, \.haptic, name: "haptic") }
            }
        }
    }

    private var tools: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                tile("Latency", detail: "log io/out + call", id: "soundboard.latency", value: nil) { model.runLatency() }
                tile("Interrupt", detail: "began", id: "soundboard.interrupt.began", value: nil) {
                    model.engine?.debugInterruption(began: true)
                }
                tile("Interrupt", detail: "ended", id: "soundboard.interrupt.ended", value: nil) {
                    model.engine?.debugInterruption(began: false)
                }
            }
            tile(model.checking ? "Self-test running…" : "Run self-test", detail: "every check, ~40 s",
                 id: "soundboard.selftest", value: model.checking ? "running" : nil) {
                Task { await model.selfTest() }
            }
            if !model.latency.isEmpty {
                Text(verbatim: model.latency).font(.system(size: 11, design: .monospaced)).opacity(0.85)
                    .accessibilityIdentifier("soundboard.latency.text")
            }
        }
    }

    private var results: some View {
        let pass = model.results.filter(\.pass).count
        return VStack(alignment: .leading, spacing: 5) {
            Text(verbatim: "\(pass)/\(model.results.count) pass" + (model.checking ? " …" : ""))
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(pass == model.results.count ? Color.green : Color.red)
                .accessibilityIdentifier("soundboard.result")
                .accessibilityValue(Text(verbatim: "\(pass)/\(model.results.count)"))
            ForEach(Array(model.results.enumerated()), id: \.offset) { _, item in
                HStack(alignment: .firstTextBaseline, spacing: 6) {
                    Text(verbatim: item.pass ? "✓" : "✗").foregroundStyle(item.pass ? Color.green : Color.red)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(verbatim: item.name).font(.system(size: 12, weight: .semibold))
                        Text(verbatim: item.detail).font(.system(size: 10, design: .monospaced)).opacity(0.7)
                    }
                }
            }
        }
    }

    // MARK: pieces

    private func section<C: View>(_ title: String, @ViewBuilder _ content: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(verbatim: title.uppercased()).font(.system(size: 11, weight: .bold)).opacity(0.6)
            content()
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Self.panel, in: RoundedRectangle(cornerRadius: 12))
    }

    private func grid<T, V: View>(_ items: [T], id: KeyPath<T, String>, @ViewBuilder _ cell: @escaping (T) -> V) -> some View {
        LazyVGrid(columns: [GridItem(.flexible(), spacing: 8), GridItem(.flexible(), spacing: 8), GridItem(.flexible(), spacing: 8)],
                  spacing: 8) {
            ForEach(items, id: id) { cell($0) }
        }
    }

    private func tile(_ title: String, detail: String, id: String, value: String?, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 2) {
                Text(verbatim: title).font(.system(size: 13, weight: .bold)).lineLimit(1).minimumScaleFactor(0.7)
                Text(verbatim: detail).font(.system(size: 9.5, design: .monospaced)).opacity(0.7).lineLimit(3).minimumScaleFactor(0.8)
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 7)
            .frame(maxWidth: .infinity, minHeight: 50, alignment: .leading)
            .background(Self.accent.opacity(0.28), in: RoundedRectangle(cornerRadius: 9))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(id)
        .accessibilityValue(Text(verbatim: value ?? ""))
    }

    private func toggleTile(_ title: String, on: Bool, id: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                Text(verbatim: title).font(.system(size: 13, weight: .bold))
                Spacer(minLength: 4)
                Text(verbatim: on ? "ON" : "OFF").font(.system(size: 12, weight: .heavy))
                    .foregroundStyle(on ? Color.green : Color.red)
            }
            .padding(.horizontal, 10)
            .frame(maxWidth: .infinity, minHeight: 40)
            .background(Self.accent.opacity(0.28), in: RoundedRectangle(cornerRadius: 9))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(id)
        .accessibilityValue(Text(verbatim: on ? "on" : "off"))
    }
}
#endif
#endif
