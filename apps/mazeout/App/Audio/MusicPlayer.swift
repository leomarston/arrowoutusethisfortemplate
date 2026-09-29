@preconcurrency import AVFoundation

// AUDIO A2 (SPEC-architecture §7.1 musicBus; SPEC-motion-audio §11.4, §11.5 MA2). Platform-neutral: the offline tests run it
// on macOS.
//
// DECISION (MA2, VERIFIED meta §4): this game has NO music. `Tuning/audio.json music.enabled` is false, so:
// - the graph attaches no decks, `loadTracks` reads nothing, and `Music/` ships empty (A1's check.py fails on any file there);
// - `playMusic` / `stopMusic` are no-ops (logged once), and the Music setting changes nothing audible (the inert button).
// The decks below exist so that turning music on is a data change plus A1's files, not new code. They are exercised by the
// offline test with a synthesised in-memory loop (never shipped).

/// The music bus's two decks (SPEC-architecture §7.1): each track is one looping stereo 44.1 kHz buffer, and a new track
/// cross-fades over `crossfade` (0.3 s, `audio.json music.crossfade`).
@MainActor final class MusicPlayer {
    @MainActor final class Deck {
        let index: Int
        let player: AVAudioPlayerNode
        fileprivate(set) var id: MusicID?
        fileprivate(set) var gain: Float = 0
        fileprivate var ramp: Int?
        fileprivate var generation = 0

        init(index: Int, player: AVAudioPlayerNode) {
            self.index = index
            self.player = player
        }
    }

    /// The music file format: stereo, 44.1 kHz (the decks' connection format).
    nonisolated static let trackFormat = AVAudioFormat(standardFormatWithSampleRate: 44_100, channels: 2)!

    let enabled: Bool
    let crossfade: Double
    private let ticker: AudioTicker
    private(set) var tracks: [MusicID: AVAudioPCMBuffer] = [:]
    private(set) var decks: [Deck] = []
    /// The deck that is (or is becoming) audible.
    private(set) var current: Deck?
    private var loggedDisabled = false

    init(enabled: Bool, crossfade: Double, ticker: AudioTicker) {
        self.enabled = enabled
        self.crossfade = max(0, crossfade)
        self.ticker = ticker
    }

    /// The audible track.
    var playing: MusicID? { current?.id }

    /// Decodes `Music/<MusicID>.wav` for every MusicID, off the main thread; nothing when music is disabled.
    nonisolated static func loadTracks(directory: URL?, enabled: Bool) async -> (tracks: [MusicID: AVAudioPCMBuffer], problems: [String]) {
        guard enabled else { return ([:], []) }
        return await withCheckedContinuation { cont in
            DispatchQueue.global(qos: .utility).async {
                var tracks: [MusicID: AVAudioPCMBuffer] = [:]
                var problems: [String] = []
                for m in MusicID.allCases {
                    guard let url = directory?.appendingPathComponent("\(m.rawValue).wav") else { problems.append("no Music folder"); break }
                    do { tracks[m] = try decode(url) } catch { problems.append("\(m.rawValue).wav: \(error)") }
                }
                cont.resume(returning: (tracks, problems))
            }
        }
    }

    /// One track as stereo 44.1 kHz Float32 (converted when needed).
    nonisolated static func decode(_ url: URL) throws -> AVAudioPCMBuffer {
        let file = try AVAudioFile(forReading: url)
        guard file.length > 0,
              let raw = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: AVAudioFrameCount(file.length))
        else { throw SoundBank.BankError.empty }
        try file.read(into: raw)
        let f = raw.format
        if f.channelCount == 2, f.sampleRate == 44_100, f.commonFormat == .pcmFormatFloat32, !f.isInterleaved { return raw }
        return try SoundBank.convert(raw, to: trackFormat)
    }

    func install(_ t: [MusicID: AVAudioPCMBuffer], problems: [String]) {
        tracks = t
        for p in problems { Log.error("audio", "music file \(p)") }
    }

    /// Takes the graph's deck players after a (re)build or restart. Every deck starts silent and stopped.
    func attach(_ players: [AVAudioPlayerNode]) {
        decks = players.enumerated().map { Deck(index: $0.offset, player: $0.element) }
        current = nil
        for d in decks { apply(d, 0) }
    }

    /// Forgets the decks while the engine is being rebuilt or restarted (their players must not be touched).
    func detach() {
        for d in decks { ticker.cancel(d.ramp) }
        decks = []
        current = nil
    }

    /// Starts `id` from its beginning on a free deck, fading in over `fadeIn` (0 = at once); an audible deck fades out over
    /// `crossfade`. The caller guarantees the engine runs (a player's `play()` on a stopped engine raises). Already audible:
    /// nothing changes.
    @discardableResult
    func start(_ id: MusicID, fadeIn: Double) -> Bool {
        guard enabled, !decks.isEmpty else { return false }
        if current?.id == id { return true }
        guard let buffer = tracks[id] else {
            Log.error("audio", "music \(id.rawValue): no decoded Music/\(id.rawValue).wav")
            return false
        }
        let old = current
        if let o = old { fadeOut(o, over: crossfade, done: nil) }
        let d = decks.first { $0 !== old && $0.id == nil } ?? decks.first { $0 !== old } ?? decks[0]
        cut(d)
        d.generation += 1
        d.id = id
        apply(d, fadeIn > 0 ? 0 : 1)
        d.player.scheduleBuffer(buffer, at: nil, options: [.interrupts, .loops], completionHandler: nil)
        d.player.play()
        if fadeIn > 0 { d.ramp = ticker.ramp(from: 0, to: 1, over: fadeIn, apply: { [weak self, weak d] v in if let d { self?.apply(d, v) } }) }
        current = d
        Log.mark("audio", "music \(id.rawValue) (fade \(String(format: "%.2f", fadeIn)) s)")
        return true
    }

    /// Fades the audible track out; `done` runs when it is silent (at once when nothing plays).
    func stop(fade: Double, done: (() -> Void)?) {
        guard let d = current else { done?(); return }
        current = nil
        fadeOut(d, over: fade, done: done)
    }

    /// Stops both decks at once (suspend, restart, Music off after its fade).
    func cutAll() {
        for d in decks { cut(d) }
        current = nil
    }

    func noteDisabled(_ call: String) {
        guard !loggedDisabled else { return }
        loggedDisabled = true
        Log.mark("audio", "\(call): music is disabled (audio.json music.enabled = false, SPEC-motion-audio MA2): no-op")
    }

    // MARK: private

    private func fadeOut(_ d: Deck, over t: Double, done: (() -> Void)?) {
        guard d.id != nil else { done?(); return }
        ticker.cancel(d.ramp)
        let gen = d.generation
        d.ramp = ticker.ramp(from: d.gain, to: 0, over: max(t, 0.005),
                             apply: { [weak self, weak d] v in if let d { self?.apply(d, v) } },
                             done: { [weak self, weak d] in
                                 guard let self, let d, d.generation == gen else { done?(); return }
                                 self.cut(d)
                                 done?()
                             })
    }

    private func cut(_ d: Deck) {
        ticker.cancel(d.ramp)
        d.ramp = nil
        d.generation += 1
        if d.id != nil || d.player.isPlaying { d.player.stop() }
        d.id = nil
        apply(d, 0)
        if current === d { current = nil }
    }

    private func apply(_ d: Deck, _ gain: Float) {
        d.gain = gain
        d.player.volume = AudioGraph.nominal * gain                 // stereo decks reach the bus at `nominal`, like the voices
    }
}
