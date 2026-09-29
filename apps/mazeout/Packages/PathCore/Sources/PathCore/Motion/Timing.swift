import Foundation

// C1 (SPEC-architecture §4.16). Timing constants that are not a curve. Every value cites its measurement; the table is
// data (TunableParameters) so SPEC-motion-audio can replace a number without a code change. `Timing.x` reads the
// measured table.

public struct TimingTable: Codable, Sendable, Equatable, TunableParameters {
    /// Black → the exit colour after the release (s). colourramp.txt P01 + motion.md §3.2: 97 % by 0.09 s and already ≈ 1/3
    /// of the way on the first moved frame → an ease-out (`Curves.exitColour`: outQuad over 0.11 s), not linear. The
    /// architecture's 0.08 s (pass 1) is superseded by the pass-2 60 Hz measurement.
    public var exitColourRamp: Double = 0.11
    /// Last exit of a stage → the next board builds in ("Levels 1-4": VERIFIED tutorials §2, 5.08 → 5.80).
    public var stageGap: Double = 0.7
    /// Key-arrow tap → the door bursts (VERIFIED motion.md §5.2, 1 key; far doors: clips-needed #14).
    public var doorBurstAfterTap: Double = 1.14
    /// The last passing head leaves the far mouth → the pipe shatters (VERIFIED motion.md §5.3).
    public var pipeBreakAfterHeadLeaves: Double = 0.05
    /// Play click → the hard cut to the level (VERIFIED motion.md §6.1: +0.06 s; L49 +0.08).
    public var playCutAfterClick: Double = 0.06
    /// The level cut → the intro is done and the board takes taps (VERIFIED motion.md §6.1: cut + 1.83 s).
    public var introDone: Double = 1.83
    /// The win trigger (the last tail leaves its last cell) → the win panel (VERIFIED motion.md §6.6 v552: +3.94 s).
    public var winPanelAfterTrigger: Double = 3.94
    /// Popups appear and disappear on one frame (VERIFIED motion.md §6.3) — 0, kept explicit.
    public var popupAppear: Double = 0
    /// A button scales to 0.95 on touch-down, instantly (VERIFIED motion.md §6.3).
    public var buttonPressScale: Double = 0.95
    /// Continue press → the hard cut home (VERIFIED motion.md §6.3: ≈ 0.10 s after touch-down).
    public var continueCut: Double = 0.10

    public init() {}

    public static let measured = TimingTable()
}

public enum Timing {
    public static let table = TimingTable.measured
    public static let exitColourRamp = table.exitColourRamp
    public static let stageGap = table.stageGap
    public static let doorBurstAfterTap = table.doorBurstAfterTap
    public static let pipeBreakAfterHeadLeaves = table.pipeBreakAfterHeadLeaves
    public static let playCutAfterClick = table.playCutAfterClick
    public static let introDone = table.introDone
    public static let winPanelAfterTrigger = table.winPanelAfterTrigger
    public static let buttonPressScale = table.buttonPressScale
    public static let continueCut = table.continueCut
}
