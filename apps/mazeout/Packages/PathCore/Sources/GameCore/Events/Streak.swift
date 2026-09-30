import Foundation

// C3 (SPEC-gameplay §11.1; SPEC-social §4.2; VERIFIED flows, economy §5, levels L32–L61). The win-streak multiplier shared
// by the Streak Race, the Claw Challenge and the fail flow ("You will lose your streak!"):
// - steps x1 → x5 → x10 → x25 → x100 (`rules.streak.steps`); x100 stays;
// - a WON attempt scores the multiplier lit BEFORE the win, then steps up one (any win: after a fail the retry's win scores
//   x1 and steps to x5, VERIFIED L47/L52: Claw 140 → 141);
// - a FAILED attempt (time, hearts, quit, kill) → x1; a paid continue keeps it (it never reaches `onLoss`);
// - it moves only on levels that count for the Streak Race (`unlocks.streakRace`, L30: the chips first appear with it,
//   DECISION).

extension Events {
    /// The multiplier value (1, 5, 10, 25, 100) of a step index.
    static func stepValue(_ step: Int, _ r: EconomyRules) -> Int {
        let steps = r.streak.steps
        return steps[max(0, min(steps.count - 1, step))]
    }

    /// The current multiplier (x1…x100).
    public static func multiplier(_ s: PlayerState, rules: EconomyRules) -> Int { stepValue(s.events.streakStep, rules) }

    /// A counted win: the points it scores (the multiplier before the win) and the step change.
    static func streakWin(_ e: inout EventsState, _ r: EconomyRules) -> (points: Int, from: Int, to: Int) {
        let from = stepValue(e.streakStep, r)
        e.streakStep = min(max(0, e.streakStep) + 1, r.streak.steps.count - 1)
        return (from, from, stepValue(e.streakStep, r))
    }

    /// A failed attempt: back to x1. Returns the change (nil when already at x1).
    static func streakFail(_ e: inout EventsState, _ r: EconomyRules) -> (from: Int, to: Int)? {
        guard e.streakStep != 0 else { return nil }
        let from = stepValue(e.streakStep, r)
        e.streakStep = 0
        return (from, stepValue(0, r))
    }
}
