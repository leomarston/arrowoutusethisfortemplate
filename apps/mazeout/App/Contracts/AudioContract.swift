import Foundation
import SwiftUI
import PathCore

// ◆ CONTRACT (SPEC-architecture §3.5, §7.4). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256). AUDIO implements (AudioEngine, Haptics); GAME and SHELL call.
//
// tools/audio/specs.py PARSES the two enums below (the source of truth for which files exist): keep each enum's cases
// on `case` lines BEFORE its `var bus`, and keep `var bus` a one-line `return`. A1 renders exactly these files:
// `Sounds/<rawValue>.wav` (mono 44.1 kHz 16-bit) for every SoundID, `Music/<rawValue>.wav` for every MusicID.
// The case lists are SPEC-motion-audio §11.2 / §12.1 / §15.1 (WP0b amendment, additive only: SPEC.md §5 item 21,
// CONSISTENCY §19 C-1/C-2): v552 is silent in play except the UI click, the coin collect, the unlock chime and the
// home-return cues clawToken … streakPop (VERIFIED v552); `tapTick` is the slot for the owner's tap-sound question
// (§7.2, SPEC.md §5 item 4: unmapped unless the owner asks). Callers fire a sound on the frame of its visual event
// (§8.2). The event → cue map and the haptic map are DATA (Tuning/audio.json), not code.

enum AudioBus: String, Sendable, CaseIterable { case sfx, music }

enum SoundID: String, CaseIterable, Sendable {
    case uiClick, coinCollect, unlockChime, tapTick
    case clawToken, clawMerge, clawTick, clawComplete, streakPop
    var bus: AudioBus { return .sfx }
}

enum MusicID: String, CaseIterable, Sendable {
    case home, level
    var bus: AudioBus { return .music }
}

@MainActor protocol AudioPlaying: AnyObject {
    func warmUp() async                                                // session, engine, decode, idle voices
    func play(_ s: SoundID, gain: Float)
    func playMusic(_ m: MusicID, fade: Double)
    func stopMusic(fade: Double)
    func apply(settings: PlayerState.Settings)
    var outputLatency: TimeInterval { get }                            // io buffer + route latency (probe, §10)
}

extension AudioPlaying {
    /// Unity gain.
    func play(_ s: SoundID) { play(s, gain: 1) }
}

/// The haptic moments (§7.3 + SPEC-motion-audio §12.1: heartLost, button, booster, coinLand added by WP0b; the generator
/// per moment and its intensity are data in Tuning/audio.json `haptics`).
/// Contract amend 4 (SPEC.md §5 item 42; design/publish/motion-catalog.md §5.1 rows 5, 10, 11, 13, 14, 17, 20-22): the win-logo
/// beats `logoLetter` (A·R·R·O·W land), `logoSwell` (OUT! turns solid), `logoBounce` (the rebound after the slam), `firework`
/// (the bursts), the home/claim reward beats `rewardPop`, the key turning in its lock `keyTurn`, and `play` (the Play button's
/// stronger click; every other button stays `button`).
enum Haptic: String, CaseIterable, Sendable {
    case tap, bumpContact, fail, clear, win, burst, heartLost, button, booster, coinLand
    case logoLetter, logoBounce, firework, rewardPop, logoSwell, keyTurn, play
}

@MainActor protocol HapticPlaying: AnyObject {
    func prepare()                                                     // (re)prepare the generators (level start, boot)
    func play(_ h: Haptic)
    /// Contract amend 4 (motion-catalog §5.2): one beat at its own intensity (0…1), e.g. the five rising `logoLetter` clicks
    /// 0.55 → 0.70 from ui.json `win.haptics`. It replaces the row's intensity for impact styles only (notification styles
    /// have none). The default below ignores the override and plays the row: AUDIO's `Haptics` implements it (A2).
    func play(_ h: Haptic, intensity: Double)
    var enabled: Bool { get set }                                      // PlayerState.settings.haptic
}

extension HapticPlaying {
    /// Default for players that have no per-beat intensity (placeholders, test fakes): the row's own intensity.
    func play(_ h: Haptic, intensity: Double) { play(h) }
}

// MARK: - Entry point (how AUDIO plugs in without editing LEAD files)
//
// AUDIO installs its engine by declaring, in its OWN file:
//     extension AudioEntry {
//         static func makeAudio(_ ctx: AppContext) -> any AudioPlaying { AudioEngine(ctx) }
//         static func makeHaptics(_ ctx: AppContext) -> any HapticPlaying { Haptics(ctx) }
//         static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? { name == "soundboard" ? AnyView(SoundBoard(app: app)) : nil }
//     }
// A static member declared on the concrete enum wins over the protocol-extension default below. Keep the signatures
// EXACT: a typo silently keeps the default, and the boot log names every default still in use.

@MainActor protocol AudioEntryPoint {
    static func makeAudio(_ ctx: AppContext) -> any AudioPlaying
    static func makeHaptics(_ ctx: AppContext) -> any HapticPlaying
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView?
}

extension AudioEntryPoint {
    static func makeAudio(_ ctx: AppContext) -> any AudioPlaying {
        Log.mark("boot", "AudioEntry.makeAudio: default (silent)")
        return SilentAudio()
    }
    static func makeHaptics(_ ctx: AppContext) -> any HapticPlaying {
        Log.mark("boot", "AudioEntry.makeHaptics: default (none)")
        return SilentHaptics()
    }
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? { nil }
}

@MainActor enum AudioEntry: AudioEntryPoint {}

/// Placeholder until AUDIO lands: plays nothing.
@MainActor final class SilentAudio: AudioPlaying {
    func warmUp() async {}
    func play(_ s: SoundID, gain: Float) {}
    func playMusic(_ m: MusicID, fade: Double) {}
    func stopMusic(fade: Double) {}
    func apply(settings: PlayerState.Settings) {}
    var outputLatency: TimeInterval { 0 }
}

/// Placeholder until AUDIO lands: no vibration.
@MainActor final class SilentHaptics: HapticPlaying {
    var enabled = true
    func prepare() {}
    func play(_ h: Haptic) {}
}
