import XCTest
import AVFoundation
import UIKit
import PathCore
@testable import ArrowOut

/// AUDIO A3 (SPEC-architecture §12.2 A3; SPEC-motion-audio §11.2, §11.4–§11.6, §12). Hosted checks of A2's engine and haptics
/// on the simulator, on a PRIVATE engine: its own AVAudioEngine, its own PlayerStore directory and its own Haptics (the host
/// app's engine is not touched). Each step is `SoundCheck` (App/Audio/SoundBoard.swift), the same code the app runs with
/// `-pc.go soundboard -pc.lab selftest`; here every item must pass. What is heard is MEASURED with a tap on the engine's main
/// mixer output (`OutputMeter`), never assumed. Evidence: Documents/a3-evidence/<test>.txt in the app's container.
@MainActor final class AudioEngineTests: XCTestCase {
    /// One engine for the whole class (an AVAudioEngine per test would pile up running engines in the host process).
    private struct Rig {
        let engine: AudioEngine
        let haptics: Haptics
        let store: PlayerStore
        let meter: OutputMeter
    }
    private static var rig: Rig?

    private static func context(_ args: [String] = []) -> AppContext {
        let a = LaunchArgs(arguments: args)
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("a3-audio-\(UUID().uuidString)")
        let store = PlayerStore(args: a, now: Date(), bundle: .main, directory: dir, debounce: 0.05)
        return AppContext(args: a, tuning: Tuning.load(bundle: .main), clock: MotionClock(args: a), store: store, hud: HUDModel(),
                          anchors: AnchorRegistry(), perf: PerfMonitor(), latency: LatencyProbe(), bundle: .main)
    }

    private func booted() async throws -> Rig {
        if let r = Self.rig { return r }
        let ctx = Self.context()
        let e = AudioEngine(ctx)
        await e.warmUp()
        let r = Rig(engine: e, haptics: Haptics(ctx), store: ctx.store, meter: OutputMeter())
        Self.rig = r
        return r
    }

    private func makeCheck() async throws -> SoundCheck {
        let r = try await booted()
        XCTAssertTrue(r.store.state.settings.sound, "fresh settings: Sound ON (SPEC-motion-audio §11.4)")
        return SoundCheck(engine: r.engine, haptics: r.haptics, store: r.store, meter: r.meter)
    }

    private func assertAllPass(_ c: SoundCheck, _ name: String, file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertFalse(c.items.isEmpty, "\(name): no checks ran", file: file, line: line)
        for i in c.items { XCTAssertTrue(i.pass, "\(i.name): \(i.detail)", file: file, line: line) }
        Self.save(c.items.map { "\($0.pass ? "PASS" : "FAIL") \($0.name): \($0.detail)" }.joined(separator: "\n"), "\(name).txt")
    }

    // MARK: engine and cues

    /// §7.1: the session is up, the engine runs, the 9 files are decoded, 8 voices idle, the output reaches the mixer.
    func testEngineBootsWithEveryCueDecoded() async throws {
        let c = try await makeCheck()
        await c.checkEngine()
        let e = c.engine
        XCTAssertGreaterThan(e.ioBufferDuration, 0, "the session reports its IO buffer")
        XCTAssertGreaterThanOrEqual(e.outputLatency, e.ioBufferDuration, "outputLatency = io buffer + route latency")
        c.checkErrors()
        assertAllPass(c, "engine")
    }

    /// Every SoundID through the contract's `play`: one play each, and heard at the output at its file's own peak (±1.5 dB).
    func testEverySoundReachesTheOutputAtItsFilePeak() async throws {
        let c = try await makeCheck()
        await c.checkSounds()
        XCTAssertEqual(c.items.count, SoundID.allCases.count)
        c.checkErrors()
        assertAllPass(c, "sounds")
    }

    /// The shipped audio.json is SPEC-motion-audio §13.3 verbatim (no fallback used), every moment plays its mapped sound, and
    /// no in-level moment has one: `arrowTap` stays silent (v552 plays nothing on taps; SPEC.md §5 item 4).
    func testCueMomentsFollowTheSpecMap() async throws {
        let c = try await makeCheck()
        let map = c.engine.cues
        XCTAssertEqual(map.problems, [], "audio.json has every key of §13.3")
        XCTAssertEqual(map.cues, AudioCueMap.spec.cues)
        XCTAssertEqual(map.gains, AudioCueMap.spec.gains)
        XCTAssertEqual(map.haptics, AudioCueMap.spec.haptics)
        XCTAssertEqual(map.priority, AudioCueMap.spec.priority)
        XCTAssertNil(map.sound(for: .arrowTap))
        XCTAssertEqual(map.sound(for: .uiButton)?.id, .uiClick)
        XCTAssertEqual(map.sound(for: .homePayout)?.id, .coinCollect)
        XCTAssertEqual(map.sound(for: .unlockOverlay)?.id, .unlockChime)
        await c.checkMoments()
        c.checkErrors()
        assertAllPass(c, "moments")
    }

    /// The §9.3 latency line and the latency button: io buffer + route latency, the play call's cost, and the time from the
    /// schedule to the first output sample.
    func testLatencyIsLogged() async throws {
        let c = try await makeCheck()
        await c.checkLatency()
        c.checkErrors()
        assertAllPass(c, "latency")
    }

    // MARK: settings

    /// Sound OFF: a sounding cue goes silent (its clinks never reach the output), new cues are refused; Sound ON: the next click
    /// is at full level at once. The toggle is ShellSettings.toggle, the Pause/Settings path.
    func testSoundToggleMutesTheSFXOutput() async throws {
        let c = try await makeCheck()
        await c.checkSoundToggle()
        XCTAssertTrue(c.store.state.settings.sound, "back ON")
        c.checkErrors()
        assertAllPass(c, "sound-toggle")
    }

    /// MA2: no music. playMusic/stopMusic are no-ops, the music bus has no decks and volume 0, and the Music toggle only flips
    /// the setting (the inert button, CONSISTENCY U-7).
    func testMusicIsNoneAndTheMusicBusSilent() async throws {
        let c = try await makeCheck()
        c.checkMusicAPI()
        await c.checkMusicToggle()
        c.checkErrors()
        assertAllPass(c, "music")
    }

    // MARK: robustness

    /// The interruption hook: `began` stops the engine as the system does (a play is dropped, nothing is heard); the end
    /// re-activates the session and restarts the engine and the idle voices, and the next click is heard at full level.
    func testDebugInterruptionRestartsTheEngineAndTheIdleVoices() async throws {
        let c = try await makeCheck()
        await c.checkInterruption()
        c.checkErrors()
        assertAllPass(c, "interruption")
    }

    // MARK: haptics

    /// Every Haptic fires once through the run-loop flush; tap + heartLost in one turn → heartLost; the toggle gates.
    func testEveryHapticFiresThroughTheRunLoopFlush() async throws {
        let c = try await makeCheck()
        await c.checkHaptics()
        XCTAssertTrue(c.store.state.settings.haptic, "back ON")
        assertAllPass(c, "haptics")
    }

    /// SPEC-motion-audio §12.2 without the run loop: in one turn the highest priority wins; within one frame of a fired haptic
    /// only a higher one fires.
    func testHapticPriorityWithinOneFrame() async throws {
        let h = try await booted().haptics
        h.enabled = true
        let fired = h.fired
        for x in [Haptic.button, .coinLand, .tap, .burst, .booster] { h.play(x) }
        h.flushPending()
        XCTAssertEqual(h.lastFired, .burst, "burst > booster > coinLand > tap > button")
        XCTAssertEqual((h.fired[.burst] ?? 0) - (fired[.burst] ?? 0), 1)
        for x in [Haptic.button, .coinLand, .tap, .booster] {
            XCTAssertEqual(h.fired[x] ?? 0, fired[x] ?? 0, "\(x) lost the turn")
        }
        h.play(.tap)                                                   // same frame, lower than burst: dropped
        h.flushPending()
        XCTAssertEqual(h.lastFired, .burst)
        h.play(.heartLost)                                             // same frame, higher: fires
        h.flushPending()
        XCTAssertEqual(h.lastFired, .heartLost)
        try await Task.sleep(nanoseconds: 40_000_000)                  // > 1 frame
        h.play(.button)
        h.flushPending()
        XCTAssertEqual(h.lastFired, .button, "a later frame fires anything")
    }

    // MARK: capture mode

    /// §9.2: capture mode is fully muted: no session, no engine, plays are no-ops.
    func testCaptureModeIsMuted() async {
        let e = AudioEngine(Self.context(["-pc.capture", "1"]))
        XCTAssertTrue(e.muted)
        await e.warmUp()
        e.play(.uiClick)
        XCTAssertFalse(e.cue(.uiButton))
        let s = e.status
        XCTAssertEqual(s.phase, .cold, "\(s)")
        XCTAssertFalse(s.running)
        XCTAssertEqual(s.plays, 0)
    }

    // MARK: evidence

    private static func save(_ text: String, _ name: String) {
        guard let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else { return }
        let dir = docs.appendingPathComponent("a3-evidence", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try? text.write(to: dir.appendingPathComponent(name), atomically: true, encoding: .utf8)
    }
}
