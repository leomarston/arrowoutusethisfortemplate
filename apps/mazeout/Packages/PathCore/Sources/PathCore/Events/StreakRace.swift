import Foundation

// C3 (SPEC-gameplay §11.3–§11.4; SPEC-social §4.4; VERIFIED meta §5.1, flows). The player's side of the daily Streak Race:
// - one race per event day (07:00 UTC → 07:00 UTC), from L30; joined at the first home of the day (the list auto-shows) or
//   at the first counted win;
// - a counted win adds the multiplier before the win (the flags), a failed attempt adds nothing;
// - when the day ends the race waits in `toSettle`; `Events.refresh` asks the world (`RivalProvider.streakRace` at the race
//   end) for the final standings: rank r pays `events.streakRace.prizes[r − 1]` coins as a claim (2000 / 1000 / 500 /
//   100 × 7, none from 11). No standings from the world (an empty list) → no prize: a rank is never invented.
// The group, the rivals and their scores are SOC1's.

extension Events {
    /// Closes a contest that belongs to an earlier day / week: a joined one waits for its final rank. A contest from a
    /// LATER day / week (only after the clock's one-time rebase) is dropped: it cannot be settled honestly.
    static func contestRoll(_ c: inout ContestState, current index: Int, event: EventID, toSettle: inout [ContestResult]) {
        guard let i = c.index, i != index else { return }
        if i < index {
            toSettle.append(ContestResult(event: event, index: i, score: c.score, joinedAt: c.joinedAt, lastScoreAt: c.lastScoreAt))
        }
        c = ContestState()
    }

    static func contestJoin(_ c: inout ContestState, index: Int, at t: SocialTime) {
        if c.index == nil { c = ContestState(index: index, joinedAt: t, score: 0, lastScoreAt: nil) }
    }

    /// Joins the event day's race and records the join in the ledger (SOC1 forms the group at this moment).
    static func joinStreakRace(_ s: inout PlayerState, at t: SocialTime, _ r: EconomyRules) {
        let day = EventSchedule.day(t, r.events.calendar)
        guard s.events.streakRace.index == nil else { return }
        contestJoin(&s.events.streakRace, index: day, at: t)
        s.social.joinStreak(day: day, level: s.level, at: t)
    }

    /// The day's race standing of the player at `t`, as the world ranks it (the player's row), or nil without standings.
    public static func streakRaceStandings(_ s: PlayerState, now: Date, rivals: RivalProvider, me: PlayerStanding,
                                           rules: EconomyRules) -> [RaceStanding] {
        let t = EconomyClock.peekSocial(s, wall: now)
        guard let inst = EventSchedule.instance(.streakRace, at: t, rules: rules.events) else { return [] }
        return rivals.streakRace(inst, player: me, at: t)
    }

    /// Final rank of the player from a race's rows: the world's own row for the player when present, else the player's
    /// score placed among the rivals (a tie ranks behind the rival, who reached it first). nil without rows.
    static func rank(of score: Int, in rows: [RaceStanding]) -> Int? {
        if rows.isEmpty { return nil }
        if let me = rows.first(where: { $0.isMe }) { return me.rank }
        return 1 + rows.filter { !$0.isMe && $0.score >= score }.count
    }

    static func settleStreakRace(_ s: inout PlayerState, _ res: ContestResult, rivals: RivalProvider, me: PlayerStanding,
                                 _ r: EconomyRules) -> [EventOutcome] {
        guard let inst = EventSchedule.instance(.streakRace, index: res.index, rules: r.events) else { return [] }
        let rows = rivals.streakRace(inst, player: me, at: inst.end)
        guard let rank = rank(of: res.score, in: rows) else { return [] }
        if rank == 1 { s.events.wins[EventID.streakRace.rawValue, default: 0] += 1 }
        let prizes = r.events.streakRace.prizes
        guard rank >= 1, rank <= prizes.count, prizes[rank - 1] > 0 else { return [] }
        let g = Grant.coins(prizes[rank - 1])
        addClaim(&s, .streakRace, .streakRacePrize, grant: g, value: rank, index: res.index, at: inst.end)
        return [.grant(g)]
    }
}
