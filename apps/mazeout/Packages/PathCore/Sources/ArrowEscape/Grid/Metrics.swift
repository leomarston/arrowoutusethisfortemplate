import Foundation
import CoreGraphics
import GameCore

// C1 (SPEC-architecture §4.2). Arrow geometry as ratios of the lattice pitch, plus the fit / zoom constants.
//
// Sources (every value is pinned by GeometryTests):
// - STYLE §A (art/STYLE.md, L32 at 3 zooms, 37 heads): stroke 0.215–0.233 → 0.22; head base 0.616, length 0.61, corner
//   r 0.047; apex past the head-cell centre ← → 0.36, ↑ 0.30, ↓ 0.435 (the vertical heads sit 1.2 pt lower: an anchor
//   offset in the original, "copy the per-direction values"); dots 0.192 #C5E1FF.
// - research/motion.md §2 (pass 2, 8 levels): stroke 0.221; outer-corner centre-line fillet R ≈ 0.125; the head tip at
//   +0.39 and its base at −0.22 averaged over all directions (spread 0.369–0.395). This DISAGREES with STYLE's per-direction
//   apex by up to 0.09 pitch; SPEC.md §4 makes STYLE the fallback for geometry until SPEC-ui lands, so the defaults below are
//   STYLE's and the pass-2 reading is `ArrowMetrics.motionPass2` (B1's L32-vs-shot-003 overlay decides; C1 open issue).
// - Zoom: motion.md §6.7 (pass 2) — both limits are ABSOLUTE pitches, 14.04 … 28.07 pt (L32/L47 pinch-out → 14.04, L062
//   at fit 14.0 cannot zoom out, L50 opens at the 28.07 cap). `minZoomOfFit` 0.786 (levels L47) is the same limit seen
//   from a 17.87 pt fit; `BoardLayout.minZoom` uses the absolute rule.

/// The measured look of a resting arrow, in pitch units (data: B1 may override it from board.json; SPEC-ui wins later).
public struct ArrowMetrics: Codable, Sendable, Equatable, TunableParameters {
    public var stroke: Double
    public var headBase: Double
    public var headLength: Double
    /// Radius of the two BASE corners.
    public var headCornerRadius: Double
    /// Radius of the tip: 0 = sharp (motion.md §2.2 pass 2: "tip sharp"), so the visible tip sits exactly at the measured
    /// apex distance (STYLE §A and motion.md both measured the VISIBLE tip).
    public var headTipRadius: Double
    /// Apex past the head-cell centre along the head direction, per direction.
    public var apexRight: Double
    public var apexLeft: Double
    public var apexUp: Double
    public var apexDown: Double
    /// Outer-corner fillet of the CENTRE line (0 = sharp polyline + round join, the architecture's recipe §5.4; motion.md
    /// §2.2 measured ≈ 0.125). Rendering only: the kinematics always use the sharp polyline (exact arc length).
    public var cornerFillet: Double
    public var dotDiameter: Double

    public init(stroke: Double, headBase: Double, headLength: Double, headCornerRadius: Double, headTipRadius: Double = 0,
                apexRight: Double, apexLeft: Double, apexUp: Double, apexDown: Double, cornerFillet: Double, dotDiameter: Double) {
        self.stroke = stroke; self.headBase = headBase; self.headLength = headLength
        self.headCornerRadius = headCornerRadius; self.headTipRadius = headTipRadius
        self.apexRight = apexRight; self.apexLeft = apexLeft
        self.apexUp = apexUp; self.apexDown = apexDown; self.cornerFillet = cornerFillet; self.dotDiameter = dotDiameter
    }

    /// STYLE §A (VERIFIED L32, 37 heads) — the default (SPEC.md §4: STYLE is the geometry fallback).
    public static let style = ArrowMetrics(stroke: 0.22, headBase: 0.616, headLength: 0.61, headCornerRadius: 0.047,
                                           apexRight: 0.36, apexLeft: 0.36, apexUp: 0.30, apexDown: 0.435,
                                           cornerFillet: 0, dotDiameter: 0.192)

    /// research/motion.md §2.2 (pass 2, 8 levels, no per-direction split): tip +0.39, base −0.22 (length 0.61), width
    /// 0.61, stroke 0.221, centre-line fillet 0.125. Kept for the B1 overlay comparison; not the default.
    public static let motionPass2 = ArrowMetrics(stroke: 0.221, headBase: 0.61, headLength: 0.61, headCornerRadius: 0.047,
                                                 apexRight: 0.39, apexLeft: 0.39, apexUp: 0.39, apexDown: 0.39,
                                                 cornerFillet: 0.125, dotDiameter: 0.192)

    public static let `default` = ArrowMetrics.style

    public func apexPast(_ d: Dir) -> Double {
        switch d {
        case .right: return apexRight
        case .left: return apexLeft
        case .up: return apexUp
        case .down: return apexDown
        }
    }
}

/// Arrow geometry as ratios of the lattice pitch, plus the fit / zoom constants (VERIFIED STYLE §A, spike, levels).
public enum Metrics {
    public static let stroke = ArrowMetrics.style.stroke                 // 0.215 at fit, 0.226 at 1.57×, 0.233 at 0.79×
    public static let headBase = ArrowMetrics.style.headBase             // 33 px at a 53.59 px pitch
    public static let headLength = ArrowMetrics.style.headLength
    public static let headCornerRadius = ArrowMetrics.style.headCornerRadius
    /// How far the head apex sits past the head cell centre, per direction (STYLE §A: ← → 0.36, ↑ 0.30, ↓ 0.435).
    public static func headApexPast(_ d: Dir) -> Double { ArrowMetrics.style.apexPast(d) }
    public static let dotDiameter = ArrowMetrics.style.dotDiameter      // #C5E1FF discs
    /// pt: the zoom cap = the fit cap (levels L47 probe; L50 opens at the cap; motion.md §6.7 28.07/28.09/28.04).
    public static let maxPitch = 28.07
    /// pt: the absolute zoom floor (motion.md §6.7 pass 2: L32/L47 pinch-out → 14.04; L062 at fit 14.0 stays at 14.0).
    public static let minPitch = 14.04
    /// levels L47 (0.783–0.786): the floor seen from a 17.87 pt fit (= 14.04 / 17.864). `BoardLayout.minZoom` uses
    /// `minPitch` so a board whose fit is already near the floor cannot zoom out (L062).
    public static let minZoomOfFit = 0.786
    /// HUD bottom … booster top (VERIFIED spike): the rect the board is fitted and centred in.
    public static let playRect = CGRect(x: 0, y: 122, width: 393, height: 633)
    /// The reference screen (the owner's iPhone 15, §0.3).
    public static let screenSize = CGSize(width: 393, height: 852)
    /// Where the middle of the cell grid lands on screen, averaged over the 30 recorded levels (motion.md §2.1: x 196.5,
    /// y 439.2 ± 0.2 pt). The play rect's centre is (196.5, 438.5): the original sits 0.7 pt lower (B1 decides whether
    /// to copy the offset; GeometryTests report the residual per level).
    public static let measuredBoardCentre = CGPoint(x: 196.5, y: 439.2)
}
