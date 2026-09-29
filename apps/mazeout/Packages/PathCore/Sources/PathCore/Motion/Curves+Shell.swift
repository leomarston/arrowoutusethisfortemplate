import Foundation

// C1 (SPEC-architecture §4.16). The measured motion of the HUD and the shell sequences, as data (see Curves.swift for the
// conventions). The SwiftUI side reads these through MotionClock (§5.12) so freeze/slow motion stay consistent.

// MARK: - HUD drop and booster slide

/// easeOutBack slides (motion.md §6.1 pass 2, hudfit_L48.txt; pass 1's springs are superseded: the L48 60 Hz trace shows
/// no undershoot). `value(τ)` = from + (to − from)·outBack((τ − delay)/duration, overshoot), τ = s since the level cut.
/// The measured endpoints are the pause button's top edge (HUD) and the left booster's right edge; S2 applies `progress`
/// to its own frames.
public struct SlideCurve: Codable, Sendable, Equatable, TunableParameters {
    public var delay: Double
    public var duration: Double
    public var overshoot: Double
    public var from: Double
    public var to: Double

    public init(delay: Double, duration: Double, overshoot: Double, from: Double, to: Double) {
        self.delay = delay; self.duration = duration; self.overshoot = overshoot; self.from = from; self.to = to
    }

    /// Top HUD: starts cut + 1.015 s, 0.3334 s, s = 3.441, pause-button top −48.92 → 68.5 pt (RMS 2.20, max 5.45 pt). C1
    /// re-fitted hudfit_L48's data: the analyst's rounded parameters (−49.9, 0.334, 3.42) give max 5.59.
    public static let hudDrop = SlideCurve(delay: 1.01497, duration: 0.33337, overshoot: 3.44069, from: -48.921, to: 68.5)
    /// Boosters: cut + 1.0923 s, 0.2089 s, s = 2.566, left booster right edge −22.2 → 67.0 pt (RMS 1.18, max 2.56 pt; the
    /// rounded −21.8/0.209/2.57 give max 3.20); the right booster mirrors it.
    public static let boosterSlide = SlideCurve(delay: 1.09233, duration: 0.20892, overshoot: 2.56562, from: -22.199, to: 67.0)

    /// 0 → 1 (with overshoot) τ s after the cut.
    public func progress(_ tau: Double) -> Double {
        guard tau > delay else { return 0 }
        return Easing.outBack((tau - delay) / duration, s: overshoot)
    }
    public func value(_ tau: Double) -> Double { from + (to - from) * progress(tau) }
    public var end: Double { delay + duration }
}

// MARK: - Pops that follow a measured scale track

/// A pop whose scale follows a measured key track from its first frame (it appears already large: no grow-in).
public struct PopTrackCurve: Codable, Sendable, Equatable, TunableParameters {
    public var track: KeyTrack
    /// When the first element pops, s after the level cut.
    public var delay: Double
    /// Extra delays of the following elements (hearts 2 and 3).
    public var stagger: [Double]

    public init(track: KeyTrack, delay: Double, stagger: [Double] = [0]) {
        self.track = track; self.delay = delay; self.stagger = stagger
    }

    /// The big "3:00" over the pill: 3.5× → 2.65 → 2.2 → 1.6 → 1.12 → 0.8 → 1.0 over 0.25 s (SPEC-architecture §4.16 =
    /// motion pass 1, L32). Pass 2 (L48, 60 Hz) saw it settle ≈ 0.19 s after it appeared; pops at HUD start + 0.32 s.
    public static let bigTimer = PopTrackCurve(
        track: KeyTrack([(0, 3.5), (0.0415, 2.65), (0.083, 2.2), (0.1245, 1.6), (0.166, 1.12), (0.2075, 0.8), (0.249, 1.0)],
                        interpolation: .monotoneCubic),
        delay: 1.339)
    /// Hearts: each pops in at ≈ 1.6× and settles through a 0.89× undershoot (mean of the 3 hearts of hud_intro_L48,
    /// 42 → 23.5 → 26.5 pt), 0.067 s after the timer; stagger 0.099 / 0.216 s.
    public static let heartPop = PopTrackCurve(
        track: KeyTrack([(0, 1.6163), (0.0167, 1.566), (0.0333, 1.4528), (0.05, 1.3333), (0.0667, 1.2264), (0.0833, 1.1006),
                         (0.1, 0.9685), (0.1167, 0.9057), (0.1333, 0.8868), (0.15, 0.9183), (0.1667, 0.9623),
                         (0.1833, 1.0252), (0.2, 1.0377), (0.2167, 1.0377), (0.2333, 1.0314), (0.25, 1.0094),
                         (0.2667, 1.0189), (0.2833, 1.0)], interpolation: .monotoneCubic),
        delay: 1.406, stagger: [0, 0.099, 0.216])

    /// Scale of element `i` τ s after the cut; nil before it appears.
    public func scaleAfterCut(_ tau: Double, element i: Int = 0) -> Double? {
        let t = tau - delay - (i < stagger.count ? stagger[i] : 0)
        guard t >= 0 else { return nil }
        return track(t)
    }
    /// Scale t s after the element's own first frame.
    public func callAsFunction(_ t: Double) -> Double { track(max(0, t)) }
}

// MARK: - Heart break (bump)

/// The rightmost red heart breaks on contact (motion.md §4, VERIFIED both v552 clips): the halves rise and fall on one
/// parabola dy = −v0·τ + ½gτ² (v0 115 pt/s, g 960 pt/s² → the 7 pt rise peaks at τ 0.12; bumpfx_v552 heart centroid),
/// tilt outward ±tilt by 0.12, spread to ±spread, fade 0.30 → 0.40; the empty slot shows from 0.05.
public struct HeartBreakCurve: Codable, Sendable, Equatable, TunableParameters {
    public var v0: Double = 115
    public var gravity: Double = 960
    public var tiltDegrees: Double = 25
    public var tiltBy: Double = 0.12
    public var spread: Double = 15
    public var spreadBy: Double = 0.40
    public var fadeFrom: Double = 0.30
    public var fadeTo: Double = 0.40
    public var slotFrom: Double = 0.05
    public init() {}
    public static let measured = HeartBreakCurve()

    public func dy(_ tau: Double) -> Double { tau <= 0 ? 0 : -v0 * tau + 0.5 * gravity * tau * tau }
    public func tilt(_ tau: Double) -> Double { tiltDegrees * min(1, max(0, tau / tiltBy)) }
    public func spreadX(_ tau: Double) -> Double { spread * Easing.outQuad(tau / spreadBy) }
    public func alpha(_ tau: Double) -> Double {
        if tau <= fadeFrom { return 1 }
        return max(0, 1 - (tau - fadeFrom) / (fadeTo - fadeFrom))
    }
    public var duration: Double { fadeTo }
}

// MARK: - Unlock overlay

/// One staggered pop: hidden before `start`, `startScale` → `peakScale` at `peakAt` (ease-out), → 1 at `settleAt`.
public struct PopBeat: Codable, Sendable, Equatable {
    public var start: Double
    public var peakAt: Double
    public var peakScale: Double
    public var settleAt: Double
    public var startScale: Double

    public init(start: Double, peakAt: Double, peakScale: Double, settleAt: Double, startScale: Double = 0.2) {
        self.start = start; self.peakAt = peakAt; self.peakScale = peakScale; self.settleAt = settleAt; self.startScale = startScale
    }

    /// nil before the element appears.
    public func scale(_ t: Double) -> Double? {
        if t < start { return nil }
        if t < peakAt { return startScale + (peakScale - startScale) * Easing.outQuad((t - start) / (peakAt - start)) }
        if t < settleAt { return peakScale + (1 - peakScale) * Easing.inOutQuad((t - peakAt) / (settleAt - peakAt)) }
        return 1
    }
}

/// The "<Name>! / Unlocked! / card" overlay (tutorials.md §6, V1 L7 at 25 fps; t = s since the Play tap; the dim is instant).
/// Overshoot sizes the video did not resolve (title, card) are DECISION 1.1 (PENDING-motion-audio).
public struct UnlockOverlayCurve: Codable, Sendable, Equatable, TunableParameters {
    public var icon = PopBeat(start: 0.26, peakAt: 0.42, peakScale: 1.3, settleAt: 0.54)
    public var title = PopBeat(start: 0.50, peakAt: 0.62, peakScale: 1.1, settleAt: 0.66)
    public var unlocked = PopBeat(start: 0.62, peakAt: 0.70, peakScale: 1.0, settleAt: 0.70)
    public var card = PopBeat(start: 0.78, peakAt: 0.90, peakScale: 1.1, settleAt: 0.94)
    /// Gold/white sparkles loop around the icon from here until dismissed.
    public var sparklesFrom: Double = 1.14
    /// Tap anywhere → the overlay fades (motion.md §6.3: 0.25 s; tutorials.md §6 reads ≈ 0.16 s — open, see the C1 report).
    public var dismissFade: Double = 0.25
    public init() {}
    public static let measured = UnlockOverlayCurve()
}

// MARK: - "Tap to move!" caption and hand

/// The FTUE hint (tutorials.md §3 + hand_YTA.txt, YT-A 25 fps; v552's FTUE INFERRED identical). t = s since the hand's
/// first frame (the caption appears on the same frame). The hand scales about its fingertip: in 0.24 → 1.0 (0.24 s),
/// hold, then a loop of press 1.0 → 0.53 (0.48 s) + release (0.36 s) + hold, period `period` (one cycle seen; the loop
/// period is INFERRED 2.1 s). On the dismissing tap: caption scales out, hand fades (`out` tracks, t = s since the tap).
public struct TutorialHandCurve: Codable, Sendable, Equatable, TunableParameters {
    public var captionIn = KeyTrack([(0, 0.7), (0.04, 0.98), (0.08, 1.10), (0.12, 1.05), (0.16, 1.0)], interpolation: .monotoneCubic)
    public var captionOut = KeyTrack([(0, 1.0), (0.04, 0.70), (0.08, 0.54), (0.12, 0.29), (0.16, 0.12), (0.20, 0)], interpolation: .monotoneCubic)
    public var handIn = KeyTrack([(0, 0.2449), (0.04, 0.4286), (0.08, 0.5918), (0.12, 0.7857), (0.16, 0.8673), (0.2, 0.9694),
                                  (0.24, 1.0)], interpolation: .monotoneCubic)
    public var press = KeyTrack([(0, 1.0), (0.04, 0.9796), (0.08, 0.9592), (0.12, 0.9286), (0.16, 0.8776), (0.2, 0.8469),
                                 (0.24, 0.7755), (0.28, 0.7347), (0.32, 0.6939), (0.36, 0.6327), (0.4, 0.5918),
                                 (0.44, 0.5510), (0.48, 0.5306)], interpolation: .monotoneCubic)
    public var release = KeyTrack([(0, 0.5306), (0.04, 0.5510), (0.08, 0.6122), (0.12, 0.6531), (0.16, 0.7347), (0.2, 0.7959),
                                   (0.24, 0.8469), (0.28, 0.9184), (0.32, 0.9592), (0.36, 1.0)], interpolation: .monotoneCubic)
    public var handOutAlpha = KeyTrack([(0, 1.0), (0.04, 0.70), (0.08, 0.45), (0.12, 0.20), (0.16, 0)])
    /// The first press starts this long after the hand appears (VERIFIED: 0.80 → 1.36).
    public var firstPress: Double = 0.56
    public var period: Double = 2.1
    public init() {}
    public static let measured = TutorialHandCurve()

    public func captionScale(_ t: Double) -> Double { t < 0 ? 0 : captionIn(t) }

    /// Hand scale t s after it appeared (loops forever).
    public func handScale(_ t: Double) -> Double {
        if t < 0 { return 0 }
        if t < handIn.end { return handIn(t) }
        if t < firstPress { return 1 }
        let c = (t - firstPress).truncatingRemainder(dividingBy: period)
        if c < press.end { return press(c) }
        if c < press.end + release.end { return release(c - press.end) }
        return 1
    }
}

// MARK: - Win celebration

/// The v552 win beats (motion.md §6.6, S1-L50-win-seq-1 at 60 Hz; t = s since the trigger = the last tail leaves its
/// last cell). A tap during the celebration shows the panel at once (VERIFIED YT-A; v552 not re-tested).
public struct WinBeats: Codable, Sendable, Equatable, TunableParameters {
    public var dotWave: Double = 0.0
    public var dotWaveEnd: Double = 0.51
    public var signIn: Double = 0.41
    public var signSettled: Double = 0.64
    public var letters: Double = 0.59
    public var arrowSign: Double = 0.64
    public var arrowSignSettled: Double = 0.87
    public var outSmall: Double = 0.94
    public var outHuge: Double = 1.07
    public var outShrink: Double = 1.47
    public var outSettled: Double = 1.64
    public var dimFrom: Double = 1.24
    public var dimFor: Double = 0.333
    /// Black overlay alpha at the end of the dim (luminance 255 → ≈ 40, winscan_v552).
    public var dimAlpha: Double = 0.85
    public var confetti: Double = 1.47
    public var fireworks: Double = 1.64
    public var layerCleared: Double = 3.90
    public var panel: Double = 3.94
    public init() {}
    public static let measured = WinBeats()

    /// The background dim (black overlay alpha) t s after the trigger (linear, winscan_v552 bgLum).
    public func dim(_ t: Double) -> Double { dimAlpha * min(1, max(0, (t - dimFrom) / dimFor)) }
}

// MARK: - Coins flying to the pill

/// The home payout (motion.md §6.5 v552: 5 coins lift from the machine ≈ 0.10 s apart, each lands ≈ 0.21 s later and
/// adds reward/5 to the pill, e.g. 3854 → 3874 in +4 steps; video-flows §6 V1 first home: "+120" appears, 1000 → 1024 →
/// … → 1120). t = s since the first coin lifts.
public struct CoinFlyCurve: Codable, Sendable, Equatable, TunableParameters {
    public var coins: Int = 5
    public var spacing: Double = 0.10
    public var flight: Double = 0.21
    public init() {}
    public static let measured = CoinFlyCurve()

    /// When coin i (0-based) lifts off and lands.
    public func lift(_ i: Int) -> Double { Double(i) * spacing }
    public func arrival(_ i: Int) -> Double { lift(i) + flight }
    public var duration: Double { arrival(coins - 1) }

    /// What each arrival adds (the total split exactly; any remainder goes to the last coin).
    public func increments(total: Int) -> [Int] {
        guard coins > 0 else { return [] }
        let base = total / coins
        var out = [Int](repeating: base, count: coins)
        out[coins - 1] += total - base * coins
        return out
    }

    /// The pill's value t s after the first lift, counting from `start`.
    public func pill(_ t: Double, start: Int, total: Int) -> Int {
        var v = start
        for (i, inc) in increments(total: total).enumerated() where t >= arrival(i) { v += inc }
        return v
    }
}
