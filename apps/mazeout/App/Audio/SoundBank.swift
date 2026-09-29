@preconcurrency import AVFoundation

// AUDIO A2 (SPEC-architecture §7.1; SPEC-motion-audio §11.2–§11.4). Adapted from apps/matchfactory App/Audio/SoundBank.swift
// (05424db): our 9 one-shot cues have no variants, sized runs or chains (tools/audio/manifest.json lists none). It is
// platform-neutral, so the offline tests (tools/audio/engine_test.sh) run it on macOS.

/// Every `Sounds/<SoundID>.wav` decoded once to Float32, off the main thread, behind the Loading screen
/// (SPEC-architecture §7.1: "a few hundred KB total"). After `load` it never changes, so the decode thread hands it to the
/// main actor whole. A play is then `scheduleBuffer` of one of these buffers, with no file I/O and no allocation.
final class SoundBank: @unchecked Sendable {
    /// The one format every SFX voice plays: mono, 44.1 kHz, Float32. It is also the voices' connection format, so a
    /// scheduled buffer can never mismatch its node. A mismatch raises an Objective-C exception, not a Swift error.
    static let sampleRate: Double = 44_100
    static let voiceFormat = AVAudioFormat(standardFormatWithSampleRate: 44_100, channels: 1)!

    let buffers: [SoundID: AVAudioPCMBuffer]
    /// `*.wav` files in the folder that are not a SoundID (ignored; tools/audio/check.py fails on them in the source tree).
    let extras: [String]
    /// Files that failed to decode ("name.wav: why").
    let problems: [String]
    /// Decode time (seconds), for the warm-up log.
    let seconds: Double

    static let empty = SoundBank(buffers: [:], extras: [], problems: [], seconds: 0)

    init(buffers: [SoundID: AVAudioPCMBuffer], extras: [String], problems: [String], seconds: Double) {
        self.buffers = buffers
        self.extras = extras
        self.problems = problems
        self.seconds = seconds
    }

    var isEmpty: Bool { buffers.isEmpty }
    /// SoundIDs with no file.
    var missing: [SoundID] { SoundID.allCases.filter { buffers[$0] == nil } }
    /// Decoded size (Float32).
    var bytes: Int { buffers.values.reduce(0) { $0 + Int($1.frameLength) * Int($1.format.channelCount) * 4 } }

    func buffer(_ s: SoundID) -> AVAudioPCMBuffer? { buffers[s] }

    func duration(_ s: SoundID) -> Double { buffers[s].map { Double($0.frameLength) / Self.sampleRate } ?? 0 }

    // MARK: loading (any thread)

    enum BankError: Error, CustomStringConvertible {
        case empty, noBuffer, noConverter, convert(String)
        var description: String {
            switch self {
            case .empty: return "empty file"
            case .noBuffer: return "could not allocate a buffer"
            case .noConverter: return "no converter to mono 44.1 kHz"
            case .convert(let why): return "conversion failed: \(why)"
            }
        }
    }

    /// Decodes `<directory>/<SoundID>.wav` for every SoundID (the bundle's `Sounds/`).
    static func load(directory: URL?) -> SoundBank {
        let t0 = ProcessInfo.processInfo.systemUptime
        guard let directory,
              let urls = try? FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        else { return SoundBank(buffers: [:], extras: [], problems: ["no Sounds folder in the bundle"], seconds: 0) }
        var buffers: [SoundID: AVAudioPCMBuffer] = [:]
        var extras: [String] = []
        var problems: [String] = []
        for url in urls.sorted(by: { $0.lastPathComponent < $1.lastPathComponent }) where url.pathExtension.lowercased() == "wav" {
            let name = url.deletingPathExtension().lastPathComponent
            guard let id = SoundID(rawValue: name) else { extras.append(url.lastPathComponent); continue }
            do { buffers[id] = try decode(url) } catch { problems.append("\(name).wav: \(error)") }
        }
        return SoundBank(buffers: buffers, extras: extras, problems: problems,
                         seconds: ProcessInfo.processInfo.systemUptime - t0)
    }

    /// One file as mono 44.1 kHz Float32. A1's files are mono 44.1 kHz 16-bit, which AVAudioFile reads as Float32 directly;
    /// anything else is converted and down-mixed.
    static func decode(_ url: URL) throws -> AVAudioPCMBuffer {
        let file = try AVAudioFile(forReading: url)
        let format = file.processingFormat
        guard file.length > 0 else { throw BankError.empty }
        guard let raw = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(file.length)) else { throw BankError.noBuffer }
        try file.read(into: raw)
        guard raw.frameLength > 0 else { throw BankError.empty }
        if format.channelCount == 1, format.sampleRate == sampleRate, format.commonFormat == .pcmFormatFloat32, !format.isInterleaved {
            return raw
        }
        return try convert(raw, to: voiceFormat)
    }

    private final class FedOnce { var fed = false }

    static func convert(_ input: AVAudioPCMBuffer, to format: AVAudioFormat) throws -> AVAudioPCMBuffer {
        guard let converter = AVAudioConverter(from: input.format, to: format) else { throw BankError.noConverter }
        converter.downmix = true
        let ratio = format.sampleRate / input.format.sampleRate
        let capacity = AVAudioFrameCount(Double(input.frameLength) * ratio) + 1024
        guard let out = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: capacity) else { throw BankError.noBuffer }
        let once = FedOnce()
        var error: NSError?
        let status = converter.convert(to: out, error: &error) { _, inputStatus in
            if once.fed {
                inputStatus.pointee = .endOfStream
                return nil
            }
            once.fed = true
            inputStatus.pointee = .haveData
            return input
        }
        if status == .error { throw BankError.convert(error?.localizedDescription ?? "unknown") }
        guard out.frameLength > 0 else { throw BankError.empty }
        return out
    }
}
