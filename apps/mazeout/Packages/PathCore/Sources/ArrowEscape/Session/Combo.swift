import Foundation
import GameCore

// C2 (SPEC-architecture §4.7, D23). The exit colour ladder. An exit tapped within `window` seconds of the previous exit
// tap continues the streak; the index goes into `ExitPlan.combo` and the board maps it to a painter through board.json
// `combo.ladder` (default solid, solid, violet, rainbow…; the last entry repeats). INFERRED motion.md §3.4 (84 % of 1630
// video taps at W = 1.20–1.25 s); v552 check VERIFIED (taps 0.58 / 0.75 s apart → blue, blue, violet).
// Whether a bump breaks the streak is PENDING-motion-audio (`bumpBreaks`, default true); ignored taps never count.

public struct ComboTracker: Codable, Sendable, Equatable {
    public var window: Double = 1.25
    public var bumpBreaks: Bool = true
    /// The current streak length (0 = none yet).
    public private(set) var count: Int = 0
    /// The time of the streak's last exit tap.
    public private(set) var lastTap: TimeInterval?

    public init(window: Double = 1.25, bumpBreaks: Bool = true) {
        self.window = window
        self.bumpBreaks = bumpBreaks
    }

    /// Registers a tap at `t` (the session's clock of taps). An exit returns its 1-based index in the streak; a bump
    /// returns 0 (and resets the streak when `bumpBreaks`).
    public mutating func register(tapAt t: TimeInterval, isBump: Bool) -> Int {
        if isBump {
            if bumpBreaks { reset() }
            return 0
        }
        if let last = lastTap, t - last <= window, t >= last { count += 1 } else { count = 1 }
        lastTap = t
        return count
    }

    /// The index the next exit would get at `t` (no change).
    public func peek(at t: TimeInterval) -> Int {
        if let last = lastTap, t - last <= window, t >= last { return count + 1 }
        return 1
    }

    public mutating func reset() {
        count = 0
        lastTap = nil
    }
}
