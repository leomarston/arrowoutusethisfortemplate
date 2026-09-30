import Foundation

// C3 (SPEC-gameplay §10.7, §11.3–§11.4; SPEC-social §4.3; VERIFIED meta §7, flows). The player's side of the Weekly Contest:
// - one contest per event week (Monday 07:00 UTC), from L50 (the forced tutorial on the first L50 Play is G2/SOC2's);
// - joined when the Weekly tab is opened (`joinWeekly`) or at the first counted win of the week;
// - score = +1 per counted win since joining (`events.weekly.pointsPerWin`; VERIFIED "Score" = levels won this week);
// - at the week end the contest waits in `toSettle`; GAME asks the world for the player's final rank
//   (`SocialWorld.page(.weekly(week:), …).myRank` — not part of ◆ RivalProvider) and calls `settleWeekly`: the podium pays
//   2000 / 1000 / 500 coins as a claim and rank 1 counts a Weekly Contest Win (`stats.weeklyContestWins`, Profile).

extension Events {
    /// Opening the Weekly tab at L50+: the player joins this week's contest. False when locked or already joined.
    @discardableResult
    public static func joinWeekly(_ s: inout PlayerState, now: Date, rules: EconomyRules) -> Bool {
        let t = EconomyClock.social(&s, wall: now)
        _ = roll(&s, at: t, rivals: nil, rules: rules)
        guard EventSchedule.isUnlocked(.weeklyContest, level: s.level, rules: rules.events), s.events.weekly.index == nil
        else { return false }
        joinWeeklyContest(&s, at: t, rules)
        return true
    }

    /// Joins the week's contest and records the join in the ledger (SOC1 forms the group at this moment).
    static func joinWeeklyContest(_ s: inout PlayerState, at t: SocialTime, _ r: EconomyRules) {
        let week = EventSchedule.week(t, r.events.calendar)
        guard s.events.weekly.index == nil else { return }
        contestJoin(&s.events.weekly, index: week, at: t)
        s.social.joinWeekly(week: week, level: s.level, at: t)
    }

    /// Ended weeks waiting for their final rank (GAME asks the world, then calls `settleWeekly`).
    public static func weeksToSettle(_ s: PlayerState) -> [ContestResult] {
        s.events.toSettle.filter { $0.event == .weeklyContest }
    }

    /// Settles an ended week with the player's final rank (1-based): the podium prize as a claim; rank 1 = a Weekly
    /// Contest Win. A week that is not waiting (never joined, already settled) changes nothing.
    @discardableResult
    public static func settleWeekly(_ s: inout PlayerState, week: Int, rank: Int, rules: EconomyRules) -> [EventOutcome] {
        guard let i = s.events.toSettle.firstIndex(where: { $0.event == .weeklyContest && $0.index == week }) else { return [] }
        s.events.toSettle.remove(at: i)
        if rank == 1 { s.stats.weeklyContestWins += 1 }
        let prizes = rules.events.weekly.prizes
        guard rank >= 1, rank <= prizes.count, prizes[rank - 1] > 0 else { return [] }
        let g = Grant.coins(prizes[rank - 1])
        let end = EventSchedule.weekStart(week + 1, rules.events.calendar)
        addClaim(&s, .weeklyContest, .weeklyPrize, grant: g, value: rank, index: week, at: end)
        return [.grant(g)]
    }
}
