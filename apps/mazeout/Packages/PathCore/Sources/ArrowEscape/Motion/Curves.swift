import Foundation
import CoreGraphics
import GameCore

// C1 (SPEC-architecture §4.16). The measured motion of the board, as data. Each curve is a Codable parameter struct whose
// defaults are the measurement (`.measured`), with a `Curves.<name>` instance for the §4.16 call shape. Sources:
// research/motion.md (pass 2, v552 phone clips at 60 Hz, the interim authority for timings, SPEC.md §4), tutorials.md,
// video-flows.md, and the analyst's raw traces research/motion-tools/out/*.txt. Key tracks marked "mean of …" are the
// frame-by-frame averages printed by `python3 Packages/PathCore/Tests/tools/c1_motion_samples.py --tracks`; CurvesTests
// check every curve against the per-clip samples in Tests/Fixtures/c1_motion_samples.json. SPEC-motion-audio replaces
// values through `overridden(by:)` (Tunable.swift) or in this file together with the fixture.
// Times are seconds, distances pt (screen) unless a name says cells.

public enum Curves {
    public static let exitColour = ExitColourCurve.measured
    public static let ripple = RippleCurve.measured
    public static let bump = BumpCurve.measured
    public static let vignette = VignetteCurve.measured
    public static let buildIn = BuildInCurve.measured
    public static let introZoom = IntroZoomCurve.measured
    public static let clearWave = ClearWaveCurve.measured
    public static let keyFlight = KeyFlightCurve.measured
    public static let debris = DebrisCurve.door
    public static let boxShards = DebrisCurve.box
    public static let pipeShards = DebrisCurve.pipe
    public static let hudDrop = SlideCurve.hudDrop
    public static let boosterSlide = SlideCurve.boosterSlide
    public static let bigTimer = PopTrackCurve.bigTimer
    public static let heartPop = PopTrackCurve.heartPop
    public static let heartBreak = HeartBreakCurve.measured
    public static let unlockOverlay = UnlockOverlayCurve.measured
    public static let tutorial = TutorialHandCurve.measured
    public static let win = WinBeats.measured
    public static let coinFly = CoinFlyCurve.measured

    // The §4.16 names of the FTUE hint curves (t = s since the hand / caption appeared).
    /// Caption "Tap to move!" scale: 0.7 → 1.10 → 1.0 (ease-out-back, 0.16–0.20 s).
    public static func captionPop(_ t: Double) -> Double { tutorial.captionScale(t) }
    /// Hand scale-in about the fingertip: 0.24 → 1.0 (0.24 s ease-out).
    public static func handIn(_ t: Double) -> Double { t < 0 ? 0 : tutorial.handIn(t) }
    /// The hand for all t: scale-in, hold, then the press loop (period 2.1 s).
    public static func handLoop(_ t: Double) -> Double { tutorial.handScale(t) }
}

// MARK: - Exit colour

/// Black → the exit colour after the release: an ease-out 1 − (1 − u)^power over `duration`. colourramp.txt P01 (G channel
/// from the resting #0F0F0F to #10A2EF, fitted release 1.942): 0.33 on the first moved frame 22 ms after the release, 0.55 at
/// 38 ms, 0.74 at 55 ms, 0.88 at 71 ms, 0.97 at 88 ms → outQuad over 0.11 s fits within 0.03 (L33's frames too, one frame
/// after an unseen release; motion.md §3.2's L50 samples within their ±1 frame release uncertainty). motion.md reads the
/// ramp as "≈ linear over 0.09–0.10 s"; a line misses the first frames by 0.15.
public struct ExitColourCurve: Codable, Sendable, Equatable, TunableParameters {
    public var duration: Double = 0.11
    public var power: Double = 2
    public init() {}
    public static let measured = ExitColourCurve()
    /// Colour progress 0 (black) … 1 (the exit colour) t seconds after the release.
    public func callAsFunction(_ t: Double) -> Double {
        guard t > 0 else { return 0 }
        return Easing.power(t / duration, power)
    }
}

// MARK: - Tap ripple

/// The grey tap disc (motion.md §3.1, VERIFIED 3 clips): drawn on the release frame at r 11 pt, luminance 180 on white,
/// growing to ≈ 22 pt while fading to 250, gone after 0.25 s. Tracks = mean of ripple_L33 / _P02A / _L35 per 1/60 s.
public struct RippleCurve: Codable, Sendable, Equatable, TunableParameters {
    public var radius = KeyTrack([(0, 11.0), (0.0167, 12.0), (0.0333, 13.25), (0.05, 14.5), (0.0667, 15.67), (0.0833, 16.67),
                                  (0.1, 17.67), (0.1167, 18.67), (0.1333, 19.33), (0.15, 20.25), (0.1667, 20.75),
                                  (0.1833, 21.17), (0.2, 21.5), (0.2167, 21.83), (0.2333, 21.83)], interpolation: .monotoneCubic)
    public var luminance = KeyTrack([(0, 180.0), (0.0167, 184.0), (0.0333, 191.0), (0.05, 199.0), (0.0667, 207.3),
                                     (0.0833, 215.0), (0.1, 220.7), (0.1167, 226.7), (0.1333, 232.3), (0.15, 237.0),
                                     (0.1667, 242.0), (0.1833, 246.0), (0.2, 248.0), (0.2167, 249.3), (0.2333, 250.0)],
                                    interpolation: .monotoneCubic)
    /// Visible for t in [0, life).
    public var life: Double = 0.25
    public init() {}
    public static let measured = RippleCurve()

    public struct Frame: Equatable, Sendable {
        public var radius: Double
        /// Disc luminance on white (0…255): fill = white · luminance/255 (the board draws it as grey with alpha
        /// 1 − luminance/255 over the white board).
        public var luminance: Double
        public var visible: Bool
    }
    public func callAsFunction(_ t: Double) -> Frame {
        Frame(radius: radius(t), luminance: luminance(t), visible: t >= 0 && t < life)
    }
}

// MARK: - Bump (v552)

/// A wrong tap (motion.md §4, VERIFIED 2 v552 clips at 60 Hz; phone wins over YT-B, OWNER 02:55). τ = s since CONTACT.
/// - out: the arrow slides along its own path at CONSTANT speed from the release to contact; duration
///   T_out = outBase + outPerCell · contactCells (law over 3 observations: 3.58 c → 0.165 s, 1.36 c → 0.107 s, YT-B 0.41 c
///   → 0.084 s); no hold;
/// - back: ease-out power 2 over `back` (bump-1 0.144 s RMS 0.87 pt; bump-2 ≈ 0.137 s);
/// - the tapped arrow turns #EE0912 from τ ≈ 0.017 (S-shaped, done ≈ 0.12) and STAYS red;
/// - the blocker flashes the same red (τ 0.02 → 0.12) and returns to black by τ 0.33 (blockerflash_L47.txt);
/// - the ✖ badge on the contact point: large (1.4×) and transparent at τ 0.017 → 1.0 opaque by 0.13, holds to 0.33,
///   shrinks to 0.5 and fades by 0.43 (alpha = the badge-centre pixel of blockerflash_L47.txt).
public struct BumpCurve: Codable, Sendable, Equatable, TunableParameters {
    public var outBase: Double = 0.075
    public var outPerCell: Double = 0.025
    public var back: Double = 0.14
    public var backPower: Double = 2
    /// Marked-red progress (R / 238) per 1/60 s after contact (motion.md §4 row "tapped arrow colour").
    public var mark = KeyTrack([(0, 0), (1.0 / 60, 13.0 / 238), (2.0 / 60, 30.0 / 238), (3.0 / 60, 93.0 / 238),
                                (4.0 / 60, 140.0 / 238), (5.0 / 60, 190.0 / 238), (6.0 / 60, 221.0 / 238),
                                (7.0 / 60, 235.0 / 238), (8.0 / 60, 237.0 / 238), (0.2, 1)], interpolation: .monotoneCubic)
    /// Blocker red progress (R / 237), blockerflash_L47.txt.
    public var blocker = KeyTrack([(0, 0), (0.017, 0.051), (0.034, 0.203), (0.05, 0.388), (0.067, 0.599), (0.083, 0.789),
                                   (0.1, 0.937), (0.117, 1.0), (0.133, 0.987), (0.167, 0.882), (0.183, 0.793),
                                   (0.2, 0.675), (0.217, 0.553), (0.233, 0.43), (0.25, 0.308), (0.267, 0.19),
                                   (0.283, 0.097), (0.3, 0.034), (0.333, 0)], interpolation: .monotoneCubic)
    /// Badge opacity, blockerflash_L47.txt badge-centre G: (254 − G) / 216.
    public var badgeAlpha = KeyTrack([(0.017, 0), (0.034, 0.153), (0.05, 0.227), (0.067, 0.551), (0.083, 0.681),
                                      (0.1, 0.838), (0.117, 0.958), (0.133, 1.0), (0.333, 1.0), (0.35, 0.94),
                                      (0.366, 0.75), (0.383, 0.481), (0.4, 0.236), (0.416, 0.069), (0.433, 0)],
                                     interpolation: .monotoneCubic)
    /// Badge scale (motion.md §4: ≈ 1.4× → 1.0 by 0.12, → 0.5 at 0.43).
    public var badgeScale = KeyTrack([(0.017, 1.4), (0.12, 1.0), (0.33, 1.0), (0.43, 0.5)])
    public var badgeFrom: Double = 0.017
    public var badgeUntil: Double = 0.433
    /// #EE0912 (motion.md §4; lossless shot 110).
    public var red: String = "#EE0912"
    public init() {}
    public static let measured = BumpCurve()

    /// Release → contact.
    public func outDuration(contactCells c: Double) -> Double { outBase + outPerCell * max(0, c) }
    /// Release → back at rest.
    public func duration(contactCells c: Double) -> Double { outDuration(contactCells: c) + back }

    /// Travel along the arrow's own path (cells) t seconds after the release.
    public func travel(_ t: Double, contactCells c: Double) -> Double {
        let tOut = outDuration(contactCells: c)
        if t <= 0 { return 0 }
        if t <= tOut { return c * t / tOut }
        return c * (1 - Easing.power((t - tOut) / back, backPower))
    }

    /// The tapped arrow's red progress τ s after contact (stays 1 afterwards: marked for the rest of the level).
    public func markRed(_ tau: Double) -> Double { tau <= 0 ? 0 : min(1, max(0, mark(tau))) }
    /// The blocker's red flash τ s after contact.
    public func blockerRed(_ tau: Double) -> Double { tau <= 0 || tau >= blocker.end ? 0 : min(1, max(0, blocker(tau))) }
    /// The ✖ badge τ s after contact.
    public func badge(_ tau: Double) -> (scale: Double, alpha: Double, visible: Bool) {
        let visible = tau >= badgeFrom && tau < badgeUntil
        return (badgeScale(tau), visible ? min(1, max(0, badgeAlpha(tau))) : 0, visible)
    }
}

// MARK: - Red vignette

/// The four screen edges tint red on contact (motion.md §4, VERIFIED both v552 clips identical): alpha(τ, d) =
/// edge(τ) · depth(d), d = distance from the screen edge in pt. edge = bumpfx_v552 S1-L47 left edge at x 0.2 pt
/// (1 − G/254); depth = the analyst's table (0, 5, 10, 20, 30, 45 pt) normalised to 1 at the edge, extended past 45 pt with
/// their e^(−d/27) law (DECISION, beyond the table).
public struct VignetteCurve: Codable, Sendable, Equatable, TunableParameters {
    public var edge = KeyTrack([(0, 0.4173), (0.017, 0.4173), (0.034, 0.4134), (0.05, 0.4016), (0.067, 0.3819),
                                (0.083, 0.3543), (0.1, 0.3307), (0.117, 0.3071), (0.133, 0.2756), (0.167, 0.2126),
                                (0.183, 0.1811), (0.2, 0.1496), (0.217, 0.1181), (0.233, 0.0906), (0.25, 0.0669),
                                (0.267, 0.0472), (0.283, 0.0315), (0.3, 0.0118), (0.333, 0)], interpolation: .monotoneCubic)
    public var depth = KeyTrack([(0, 1), (5, 0.881), (10, 0.738), (20, 0.524), (30, 0.381), (45, 0.190), (60, 0.109),
                                 (80, 0.051), (100, 0.024), (130, 0)], interpolation: .monotoneCubic)
    public var colour: String = "#FF0000"
    public init() {}
    public static let measured = VignetteCurve()
    public var duration: Double { edge.end }
    public func alpha(_ tau: Double, depth d: Double) -> Double {
        guard tau >= 0, tau < edge.end else { return 0 }
        return max(0, edge(tau)) * max(0, depth(max(0, d)))
    }
}

// MARK: - Level intro: board zoom-out + arrows drawing in

/// The board opens at `from`× its fit scale about its centre and eases to 1 over `duration`:
/// scale = 1 + (from − 1)·(1 − τ/duration)^power (introfit_L48: A 0.4931, D 1.3501, n 3.0049, RMS 0.29 pt; τ from the cut).
public struct IntroZoomCurve: Codable, Sendable, Equatable, TunableParameters {
    public var from: Double = 1.4931
    public var duration: Double = 1.3501
    public var power: Double = 3.0049
    public init() {}
    public static let measured = IntroZoomCurve()
    public func callAsFunction(_ tau: Double) -> Double {
        let u = min(max(tau / duration, 0), 1)
        return 1 + (from - 1) * pow(1 - u, power)
    }
}

/// Every arrow draws itself tail → head at once from the level cut (motion.md §6.1 v552, 24 arrows; the per-cell law is
/// INFERRED ±0.05 s): 50 % drawn at t50 = t50Base + t50PerCell·n, 98 % at t98 = t98Base + t98PerCell·n (n = cells). Between
/// them the ink prefix grows linearly (introdraw2_L48: a constant draw rate after a small first-frame jump), so
/// fraction(τ) = f0 + τ/D with D = (t98 − t50)/0.48 and f0 = 0.5 − t50/D. The head appears when the stroke reaches it; the
/// cell dots show under the undrawn part. Long arrows (> 20 cells) finish ≈ 0.1 s earlier than the law (arrow 23: 42 cells).
public struct BuildInCurve: Codable, Sendable, Equatable, TunableParameters {
    public var t50Base: Double = 0.132
    public var t50PerCell: Double = 0.01075
    public var t98Base: Double = 0.320
    public var t98PerCell: Double = 0.02164
    public init() {}
    public static let measured = BuildInCurve()

    public func t50(cells n: Int) -> Double { t50Base + t50PerCell * Double(n) }
    public func t98(cells n: Int) -> Double { t98Base + t98PerCell * Double(n) }
    /// Seconds from the cut until the arrow is fully drawn.
    public func duration(cells n: Int) -> Double {
        let d = (t98(cells: n) - t50(cells: n)) / 0.48
        return (1 - (0.5 - t50(cells: n) / d)) * d
    }
    /// Drawn fraction of the arrow's length (tail first) τ s after the cut.
    public func fraction(_ tau: Double, cells n: Int) -> Double {
        guard tau >= 0 else { return 0 }
        let d = (t98(cells: n) - t50(cells: n)) / 0.48
        let f0 = 0.5 - t50(cells: n) / d
        return min(1, max(0, f0 + tau / d))
    }
}

// MARK: - Board-clear wave

/// The win / stage-clear dot wave (motion.md §6.6 v552: a colour ring expands from the board centre through the cell dots,
/// centre dots warm at +0.06 s, the outer ring violet at +0.41 s, all settled back to #C5E1FF by +0.51 s; tutorials §2 for
/// the stage clear). A dot at normalised distance ρ (0 = the board centre, 1 = the farthest dot) lights when the front
/// reaches it at τ = ρ·front, stays lit `glow` s, then fades back over `fade` s; its hue runs warm → violet with ρ.
public struct ClearWaveCurve: Codable, Sendable, Equatable, TunableParameters {
    public var front: Double = 0.41
    public var glow: Double = 0.03
    public var fade: Double = 0.07
    /// Hue (degrees) at the centre and at the rim (yellow-orange → violet).
    public var hueCentre: Double = 45
    public var hueRim: Double = 285
    public init() {}
    public static let measured = ClearWaveCurve()
    public var duration: Double { front + glow + fade }
    /// Light level 0…1 of a dot at distance ρ, τ s after the trigger.
    public func light(_ tau: Double, rho: Double) -> Double {
        let start = min(max(rho, 0), 1) * front
        let t = tau - start
        if t < 0 { return 0 }
        if t <= glow { return 1 }
        return max(0, 1 - (t - glow) / fade)
    }
    public func hue(rho: Double) -> Double { hueCentre + (hueRim - hueCentre) * min(max(rho, 0), 1) }
}

// MARK: - Key → door

/// A key flying to its door (motion.md §5.2, keytrack_L33.txt; 1 key, far doors clips-needed #14). t = s since the key
/// arrow's release. The key hangs where it was; sags 8.6 pt, floats up 41 pt to an apex (measured track, relative to the
/// resting spot), then dives to the lock as a parabola with g = 7650 pt/s² (the dive lasts √(2Δy/g); a lock above the apex
/// uses a straight ease-in of `diveFallback` s), shrinks into the keyhole (`insert`), turns (`turnFrom`…`turnTo`), and the
/// door bursts at `burst` (1.14 s after the tap).
public struct KeyFlightCurve: Codable, Sendable, Equatable, TunableParameters {
    /// y offset (pt, + down) from the resting spot during the sag and the float (keytrack_L33, release 0.52).
    public var hover = KeyTrack([(0.229, 0), (0.245, 2.6), (0.262, 5.1), (0.279, 7.2), (0.295, 8.4), (0.312, 8.6),
                                 (0.329, 7.2), (0.345, 4.8), (0.362, 2.5), (0.379, -3.4), (0.395, -8.6), (0.412, -13.0),
                                 (0.445, -22.6), (0.462, -26.4), (0.478, -29.3), (0.495, -31.5), (0.512, -32.6),
                                 (0.528, -32.8), (0.545, -32.5)], interpolation: .monotoneCubic)
    public var diveStart: Double = 0.554
    public var gravity: Double = 7650
    public var diveFallback: Double = 0.21
    public var insert: Double = 0.15
    public var insertScale: Double = 0.49
    public var turnFrom: Double = 1.011
    public var turnTo: Double = 1.111
    public var turnDegrees: Double = 60
    public var burst: Double = 1.14
    public init() {}
    public static let measured = KeyFlightCurve()

    /// The §4.16 call shape `Curves.keyFlight(t, from:, to:)` = `position(t, from:, to:)`.
    public func callAsFunction(_ t: Double, from: CGPoint, to: CGPoint) -> CGPoint { position(t, from: from, to: to) }

    /// Where the dive ends, for a lock at `to` (points relative to the resting spot are fine).
    public func diveEnd(from: CGPoint, to: CGPoint) -> Double { diveStart + diveDuration(from: from, to: to) }

    public func diveDuration(from: CGPoint, to: CGPoint) -> Double {
        let apexY = Double(from.y) + hover(diveStart)
        let dy = Double(to.y) - apexY
        return dy > 1 ? (2 * dy / gravity).squareRoot() : diveFallback
    }

    /// The key's position t s after the release (from = its resting spot, to = the keyhole).
    public func position(_ t: Double, from: CGPoint, to: CGPoint) -> CGPoint {
        let fx = Double(from.x), fy = Double(from.y)
        if t <= diveStart { return CGPoint(x: fx, y: fy + (t < hover.start ? 0 : hover(t))) }
        let apexY = fy + hover(diveStart)
        let dur = diveDuration(from: from, to: to)
        let u = min(1, (t - diveStart) / dur)
        let dy = Double(to.y) - apexY
        let y: Double = dy > 1 ? apexY + 0.5 * gravity * pow(u * dur, 2) : apexY + dy * u * u
        return CGPoint(x: fx + (Double(to.x) - fx) * u, y: u >= 1 ? Double(to.y) : y)
    }

    /// Scale (1 while flying, shrinking into the keyhole after the dive).
    public func scale(_ t: Double, from: CGPoint, to: CGPoint) -> Double {
        let end = diveEnd(from: from, to: to)
        guard t > end else { return 1 }
        return 1 - (1 - insertScale) * Easing.outQuad((t - end) / insert)
    }

    /// Extra rotation (degrees) of the turn in the lock.
    public func turn(_ t: Double) -> Double {
        turnDegrees * Easing.inOutQuad((t - turnFrom) / (turnTo - turnFrom))
    }
}

// MARK: - Debris and shards

/// Pieces that pop up and fall: dy(t) = −v·t + ½·g·t² with v = √(2·g·pop), fading from `fadeStart` to `life`; sideways
/// speed up to `sideways` pt/s (the board seeds each piece from the "fx" stream).
public struct DebrisCurve: Codable, Sendable, Equatable, TunableParameters {
    public var pop: Double
    public var gravity: Double
    public var sideways: Double
    public var fadeStart: Double
    public var life: Double

    public init(pop: Double, gravity: Double, sideways: Double, fadeStart: Double, life: Double) {
        self.pop = pop; self.gravity = gravity; self.sideways = sideways; self.fadeStart = fadeStart; self.life = life
    }

    /// Door burst (motion.md §5.2: ≈ 60 pieces pop ≈ 14 pt, fall g ≈ 1000 (INFERRED), life ≈ 0.9 s; sideways DECISION).
    public static let door = DebrisCurve(pop: 14, gravity: 1000, sideways: 120, fadeStart: 0.6, life: 0.9)
    /// Box break (motion.md §5.4 VERIFIED: from rest, g 1250–1300, sideways ≈ 180 pt/s, fade from 0.35, gone 0.67 s).
    public static let box = DebrisCurve(pop: 0, gravity: 1275, sideways: 180, fadeStart: 0.35, life: 0.67)
    /// Pipe break (motion.md §5.3: 22–55 blobs, g ≈ 1000 (INFERRED), gone ≈ 1.4 s; sideways DECISION).
    public static let pipe = DebrisCurve(pop: 0, gravity: 1000, sideways: 120, fadeStart: 1.0, life: 1.42)

    public var popSpeed: Double { (2 * gravity * max(0, pop)).squareRoot() }
    /// Vertical offset (pt, + down) t s after the break.
    public func dy(_ t: Double) -> Double {
        guard t > 0 else { return 0 }
        return -popSpeed * t + 0.5 * gravity * t * t
    }
    public func alpha(_ t: Double) -> Double {
        if t <= fadeStart { return 1 }
        return max(0, 1 - (t - fadeStart) / (life - fadeStart))
    }
}
