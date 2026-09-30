import Foundation

// C2 (SPEC-architecture §4.6). The level timer of one stage. Frozen at its limit until the FIRST arrow tap (VERIFIED
// research/levels.md L33/L35, tutorials §8; a bump starts it too, fail.md §3); a pinch/zoom/pan never starts it. Holds
// stack (pause, popups and offers, unlock overlays, tutorials with holdTimer, stage transitions, win sequence, background)
// and keep `remaining` constant. The freeze booster stops it for `freezeRemaining` seconds. Time enters only through
// `tick(dt)` (deterministic; the app feeds the display link's dt).
//
// CORE-2, SPEC.md ruling 30 (K-4): a freeze may carry a LEAD (`freeze(_:lead:)`, `freezeLead`) — its first seconds, the
// hourglass flight B → B + `boosters.freezeFlight`, which count down from the use even before the first tap, while the rest
// (the 10 s countdown) waits for the first tap as before (never wasted). Once the timer has started the whole freeze counts,
// lead first, so a lead changes nothing for a freeze used mid-level. Holds stop the lead like every other clock time.

public enum ClockEvent: Equatable, Sendable {
    case expired                 // remaining reached 0 while running
    case freezeEnded
    case alert(Int)              // remaining crossed a configured threshold (seconds)
}

public struct LevelClock: Equatable, Sendable {
    public private(set) var limit: Int
    public private(set) var remaining: Double
    public private(set) var started: Bool = false
    public private(set) var holds: Set<HoldReason> = []
    public private(set) var freezeRemaining: Double = 0
    /// Ruling 30: the leading part of `freezeRemaining` that counts down even before the first tap (the hourglass flight of
    /// a `freeze(_:lead:)`); always ≤ `freezeRemaining`, 0 for a plain `freeze(_:)` and once the flight is over.
    public private(set) var freezeLead: Double = 0
    /// Alert thresholds (s), each fired once when `remaining` crosses it (PENDING-gameplay; default none).
    public private(set) var alerts: [Int]
    /// A freeze counts down before the first tap too (RulesTuning.boosters.freezeRunsBeforeStart).
    public var freezeRunsBeforeStart: Bool
    var fired: Set<Int> = []
    var expiredSent = false

    public init(limit: Int, alerts: [Int] = [], freezeRunsBeforeStart: Bool = false) {
        self.limit = limit
        remaining = Double(max(0, limit))
        self.alerts = alerts.sorted(by: >)
        self.freezeRunsBeforeStart = freezeRunsBeforeStart
    }

    public var isRunning: Bool { started && holds.isEmpty && freezeRemaining <= 0 && remaining > 0 }
    /// The HUD value: whole seconds rounded UP (DECISION; tutorials §8: the first tick 0.1–1.0 s after the tap).
    public var displayedSeconds: Int { Int((remaining - 1e-9).rounded(.up)).clamped(0, Int.max) }
    public var isFrozen: Bool { freezeRemaining > 0 }
    /// Ruling 30: a freeze is set and nothing of it counts before the first tap any more (its lead, the flight, is over or
    /// there was none): the rest waits for the first tap — with the hourglass's ruled freeze the HUD tray holds "10" with a
    /// full bar. False while a lead still counts, once the timer has started and with `freezeRunsBeforeStart`.
    public var freezeWaitsForFirstTap: Bool { !started && !freezeRunsBeforeStart && freezeRemaining > 0 && freezeLead <= 0 }
    public var isExpired: Bool { remaining <= 0 }

    public mutating func startOnFirstTap() { started = true }

    public mutating func tick(_ dt: Double) -> [ClockEvent] {
        guard dt > 0, holds.isEmpty else { return [] }
        var out: [ClockEvent] = []
        var t = dt
        if freezeRemaining > 0 {
            // the whole freeze counts once the timer runs (or with freezeRunsBeforeStart); before the first tap only its lead
            let countable = started || freezeRunsBeforeStart ? freezeRemaining : min(freezeLead, freezeRemaining)
            if countable > 0 {
                let used = min(t, countable)
                freezeRemaining -= used
                freezeLead -= used                           // the lead is the freeze's leading part: it goes first
                if freezeLead <= 1e-12 { freezeLead = 0 }
                t -= used
                if freezeRemaining <= 1e-12 { freezeRemaining = 0; freezeLead = 0; out.append(.freezeEnded) }
            }
        }
        guard started, freezeRemaining <= 0, t > 0, remaining > 0 else { return out }
        let before = remaining
        remaining = max(0, remaining - t)
        for a in alerts where !fired.contains(a) && before > Double(a) && remaining <= Double(a) && a > 0 {
            fired.insert(a)
            out.append(.alert(a))
        }
        if remaining <= 0 && !expiredSent {
            expiredSent = true
            out.append(.expired)
        }
        return out
    }

    public mutating func hold(_ r: HoldReason) { holds.insert(r) }
    public mutating func release(_ r: HoldReason) { holds.remove(r) }
    /// Freezes the clock for `s` more seconds (stacks).
    public mutating func freeze(_ s: Double) { freeze(s, lead: 0) }
    /// Ruling 30: freezes the clock for `s` more seconds (stacks), of which the first `lead` (clamped to 0…`s`) count down
    /// from now even before the first tap; the rest counts once the timer has started. A lead adds to one still flying.
    public mutating func freeze(_ s: Double, lead: Double) {
        guard s > 0 else { return }
        freezeRemaining += s
        freezeLead = min(freezeRemaining, freezeLead + min(s, max(0, lead)))
    }
    /// Adds `s` seconds (a continue's +30 s); re-arms the expiry and the alerts above the new value.
    public mutating func add(_ s: Int) {
        guard s > 0 else { return }
        remaining += Double(s)
        expiredSent = false
        fired = fired.filter { Double($0) >= remaining }
    }
}

extension Comparable {
    func clamped(_ lo: Self, _ hi: Self) -> Self { min(max(self, lo), hi) }
}
