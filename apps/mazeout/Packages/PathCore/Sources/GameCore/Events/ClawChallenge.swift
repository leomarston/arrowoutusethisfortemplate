import Foundation

// C3 (SPEC-gameplay §11.2; VERIFIED flows, levels bar readings L32–L61, meta §5.2; weekly per SPEC-social §4.1/§4.7).
// - One challenge per event week (ends Monday 07:00 UTC); a new week restarts at step 1 with 0 points.
// - Points per counted win = the multiplier before the win; a failed attempt removes no points (VERIFIED 122/500 kept).
// - The bar fills toward the current step's threshold; reaching it completes the step, the OVERFLOW CARRIES (240 − 200 = 40,
//   VERIFIED L38), and the step's reward waits as a claim ("Congratulations! … Tap to Claim" on the next home).
// - After the last step the bar stays full until the week ends (DECISION); completing the ladder is a "Claw Challenge Win".

extension Events {
    /// The threshold of the step being filled (nil when the ladder is complete).
    public static func clawTarget(_ c: ClawState, rules: EconomyRules) -> Int? {
        let l = rules.claw.ladder
        return c.step < l.count ? l[max(0, c.step)].threshold : nil
    }

    /// The reward of the step being filled (the icon at the end of the home bar).
    public static func clawNextReward(_ c: ClawState, rules: EconomyRules) -> Grant? {
        let l = rules.claw.ladder
        return c.step < l.count ? l[max(0, c.step)].grant : nil
    }

    /// The challenge instance of `t`'s week (`claw.period` "day" makes it daily).
    static func clawIndex(_ t: SocialTime, _ r: EconomyRules) -> Int {
        r.claw.period == "day" ? EventSchedule.day(t, r.events.calendar) : EventSchedule.week(t, r.events.calendar)
    }

    /// A new week (or day) ended the stored challenge: start empty (joined again by the next home visit or counted win).
    static func clawRoll(_ s: inout PlayerState, at t: SocialTime, _ r: EconomyRules) {
        if let w = s.events.claw.week, w != clawIndex(t, r) { s.events.claw = ClawState() }
    }

    static func clawJoin(_ s: inout PlayerState, at t: SocialTime, _ r: EconomyRules) {
        if s.events.claw.week == nil { s.events.claw = ClawState(week: clawIndex(t, r)) }
    }

    /// Adds `points` (a counted win's multiplier): the bar, completed steps with their claims.
    static func clawAdd(_ s: inout PlayerState, points: Int, at t: SocialTime, _ r: EconomyRules) -> [EventOutcome] {
        let ladder = r.claw.ladder
        guard points > 0, !ladder.isEmpty else { return [] }
        clawJoin(&s, at: t, r)
        var c = s.events.claw
        var steps: [EventOutcome] = []
        c.points += points
        while c.step < ladder.count, c.points >= ladder[c.step].threshold {
            c.points -= ladder[c.step].threshold
            c.step += 1
            let reward = ladder[c.step - 1].grant
            addClaim(&s, .clawChallenge, .clawStep, grant: reward, value: c.step, index: c.week ?? clawIndex(t, r), at: t)
            steps.append(.clawStep(step: c.step, reward: reward))
            if c.step == ladder.count { s.events.wins[EventID.clawChallenge.rawValue, default: 0] += 1 }
        }
        s.events.claw = c
        let target = clawTarget(c, rules: r) ?? ladder[ladder.count - 1].threshold
        let shown = c.step < ladder.count ? c.points : target
        return [.clawPoints(added: points, total: shown, target: target)] + steps
    }
}
