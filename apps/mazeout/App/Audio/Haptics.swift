#if os(iOS)
import UIKit
import PathCore

// AUDIO A2 (SPEC-architecture §7.3; SPEC-motion-audio §12, MA13). Adapted from apps/matchfactory App/Audio/Haptics.swift
// (05424db). Every row is a DECISION (vibration cannot be recorded) and is DATA: `Tuning/audio.json haptics.<case>` (style +
// intensity) and `hapticPriority`, read once at launch into `AudioCueMap`.
//
// | Haptic | moment (who calls) | audio.json (ruling 39 OD4, contract amend 4 = motion-catalog §5.1) |
// |---|---|---|
// | tap | an accepted arrow tap, exit or bump: the release frame (GAME, with the ripple and the mover) | rigid 0.70 |
// | heartLost | a bump contact that costs a heart (the contact frame) | error |
// | bumpContact | a bump contact that costs no heart (a red arrow's re-bump) | heavy 0.85 |
// | fail | the Out of Time! / Out of Lives! popup's first frame | warning |
// | clear | the board-clear wave start (each stage's W) | medium 0.80 |
// | win | the OUT! slam (W + 1.688), once per win | heavy 1.00 |
// | burst | door burst, pipe shatter, box break (replaces `tap` on the box-break tap frame) | medium 0.65 |
// | button | every UI button release that clicks (+ the celebration skip tap) | rigid 0.60 |
// | play | the home Play button's release | rigid 0.75 |
// | booster | a booster use (bulb camera start / hourglass spawn) | medium 0.60 |
// | coinLand | each coin landing on the pill | soft 0.45 |
// | logoLetter | the five ARROW letters land (W + 0.815 … 0.947, rising 0.55 → 0.70 per beat: ui.json `win.haptics`) | rigid 0.70 |
// | logoSwell | OUT! turns solid (W + 1.139) | light 0.45 |
// | logoBounce | the logo's rebound after the slam (W + 1.828) | rigid 0.40 |
// | firework | each firework burst (W + 2.365 … 3.595) | soft 0.35 |
// | rewardPop | home reward beats (Claw token, merge, Streak flag) and claim beats | light 0.40 |
// | keyTurn | a key turns in its lock | rigid 0.45 |
// A2 FEEL-P: `play(_:intensity:)` (contract amend 4) replaces the row's intensity for one request (impact styles only); the
// arbiter still picks one haptic per frame by priority, and the winner fires with its own request's intensity.
// `-pc.hapticLog 1` logs every fired haptic: `[PC][haptic] fire <case> <style> <intensity> at <uptime>` (the G3 beat log).
//
// The feel rules: every generator is created and `prepare()`d at launch, prepared again at each level start (`prepare()`,
// GAME) and right after each fire (the Taptic Engine idles after ~2 s). One haptic per display frame, and the highest
// priority wins (`HapticArbiter`, SPEC-motion-audio §12.2). The winner fires at the end of the caller's run-loop turn,
// before Core Animation commits the frame, so it still leaves in the same turn as the visual (SPEC-architecture D8).
// Gated by `enabled` = `PlayerState.settings.haptic` (the Pause and Settings toggles); iOS "System Haptics" off silences
// them system-wide.

extension AudioEntry {
    static func makeHaptics(_ ctx: AppContext) -> any HapticPlaying { Haptics(ctx) }
}

@MainActor final class Haptics: HapticPlaying {
    /// Core Animation commits in a main run-loop observer (before waiting / exit) of order 2,000,000; ours runs first.
    nonisolated static let flushOrder = 1_999_000

    let map: AudioCueMap
    var enabled: Bool {
        didSet {
            guard enabled != oldValue else { return }
            if enabled { prepare() } else { arbiter.clear() }
        }
    }

    private var arbiter: HapticArbiter
    /// A2: per-request intensity overrides of this run-loop turn (the latest request of each case wins).
    private var intensities: [Haptic: Double] = [:]
    private let logFires: Bool
    private var impacts: [HapticStyle: UIImpactFeedbackGenerator] = [:]
    private let notification = UINotificationFeedbackGenerator()
    private var observer: CFRunLoopObserver?
    /// Per case: how many times it fired (SoundBoard, tests).
    private(set) var fired: [Haptic: Int] = [:]
    private(set) var lastFired: Haptic?
    /// The intensity the last fired impact used (tests; nil for notification styles).
    private(set) var lastIntensity: Double?

    init(_ ctx: AppContext) {
        logFires = ctx.args.raw["pc.hapticLog"] != nil
        map = AudioCueMap(lookup: { ctx.tuning.audio.file.value($0) })
        arbiter = HapticArbiter(map: map)                          // frame window 1/60 s (the owner's iPhone 15)
        enabled = ctx.store.state.settings.haptic
        for style in Set(Haptic.allCases.map { map.row($0).style }) where style.isImpact {
            impacts[style] = UIImpactFeedbackGenerator(style: Self.impactStyle(style))
        }
        installObserver()
        Log.mark("haptic", "map " + Haptic.allCases.map { "\($0.rawValue)=\(map.row($0))" }.joined(separator: " ")
                 + " · priority " + map.priority.map(\.rawValue).joined(separator: ">"))
    }

    // MARK: HapticPlaying

    /// Readies every generator in use (boot, level start). A cheap no-op when haptics are off.
    func prepare() {
        guard enabled else { return }
        for g in impacts.values { g.prepare() }
        notification.prepare()
    }

    /// Asks for `h` on this frame. The highest-priority request of the run-loop turn fires at its end, before the commit.
    func play(_ h: Haptic) {
        guard enabled, map.row(h).style != .none else { return }
        intensities[h] = nil
        arbiter.request(h)
    }

    /// Contract amend 4: one beat at its own intensity (0…1), e.g. the rising logo letter clicks.
    func play(_ h: Haptic, intensity: Double) {
        guard enabled, map.row(h).style != .none else { return }
        intensities[h] = min(1, max(0, intensity))
        arbiter.request(h)
    }

    // MARK: private

    private func installObserver() {
        let activities = CFRunLoopActivity.beforeWaiting.rawValue | CFRunLoopActivity.exit.rawValue
        let obs = CFRunLoopObserverCreateWithHandler(kCFAllocatorDefault, activities, true, Self.flushOrder) { [weak self] _, _ in
            MainActor.assumeIsolated { self?.flush() }
        }
        CFRunLoopAddObserver(CFRunLoopGetMain(), obs, .commonModes)
        observer = obs
    }

    /// The flush the run-loop observer runs at the end of every main run-loop turn. Unit tests that do not spin the run
    /// loop call it directly after `play`.
    func flushPending() { flush() }

    /// Requests dropped by the one-per-frame rule (SoundBoard, tests).
    var dropped: Int { arbiter.dropped }

    private func flush() {
        guard arbiter.pending != nil else { return }
        let overrides = intensities
        intensities.removeAll()
        guard enabled else { arbiter.clear(); return }
        guard let h = arbiter.flush(now: CACurrentMediaTime()) else { return }
        fire(h, intensity: overrides[h])
    }

    private func fire(_ h: Haptic, intensity: Double? = nil) {
        let row = map.row(h)
        let level = intensity ?? row.intensity
        switch row.style {
        case .light, .medium, .heavy, .rigid, .soft:
            guard let g = impacts[row.style] else { return }
            g.impactOccurred(intensity: CGFloat(level))
            g.prepare()
            lastIntensity = level
        case .success:
            notification.notificationOccurred(.success)
            notification.prepare()
        case .warning:
            notification.notificationOccurred(.warning)
            notification.prepare()
        case .error:
            notification.notificationOccurred(.error)
            notification.prepare()
        case .none:
            return
        }
        if !row.style.isImpact { lastIntensity = nil }
        fired[h, default: 0] += 1
        lastFired = h
        if logFires {
            Log.mark("haptic", String(format: "fire %@ %@ %.2f at %.4f", h.rawValue, row.style.rawValue,
                                      row.style.isImpact ? level : 0, CACurrentMediaTime()))
        }
    }

    private static func impactStyle(_ s: HapticStyle) -> UIImpactFeedbackGenerator.FeedbackStyle {
        switch s {
        case .light: return .light
        case .medium: return .medium
        case .heavy: return .heavy
        case .rigid: return .rigid
        default: return .soft
        }
    }
}
#endif
