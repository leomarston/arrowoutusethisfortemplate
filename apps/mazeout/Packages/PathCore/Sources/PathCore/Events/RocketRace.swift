import Foundation

// C3 (SPEC-gameplay §11.3–§11.4; SPEC-social §4.5, D14; VERIFIED flows L54–L58, meta §5.3). The player's Rocket Race:
// - offered after the L54 win (reach L55); free "Start" (a claim of ∞ 30m, once per event day — the same-day re-offer showed
//   a plain "Start", DECISION); stage s: beat N = 5 / 7 / 9 levels before the 4 rivals;
// - every won level (first try or not) is +1; a failed level changes nothing;
// - the rivals move on their own clock (`RivalProvider.rocketRace`, SOC1): once one of them has N the race is lost ("You
//   lost the race!"), found at the player's next win (that win still shows on the lane) or home refresh; a tie at N goes to
//   the rival (DECISION);
// - the player's N-th win first → the stage prize (500 coins + ∞ 45m, …) as a claim and the next stage is offered at once;
//   the last stage won → no more races until the next event day; the race also ends (no winner) at the event day's end;
// - a lost / expired race can be re-joined after `retryCooldown` (0: at once, VERIFIED "Join" right after the loss).

public enum JoinError: Error, Equatable, Sendable {
    case locked
    case alreadyActive
    /// The last stage was won today: the next event day offers stage 1 again.
    case doneForToday
    case coolingDown(until: SocialTime)
    /// Sky Jump: `maxRunsPerDay` stage-1 runs already started today.
    case limitReached
    /// B1: the rotation does not feature this event this week for this player (a stale "Join" that raced the Monday roll, a
    /// notification, an old badge): "This event has ended." `next` = the start of its next week (nil: none in 26 weeks).
    case notLive(next: SocialTime?)
}

extension Events {
    /// "Start" on the Rocket Race offer: a new race at the next stage (+ the ∞ join claim the first time today).
    public static func joinRocketRace(_ s: inout PlayerState, now: Date, rules: EconomyRules) -> Result<RocketRun, JoinError> {
        let t = EconomyClock.social(&s, wall: now)
        _ = roll(&s, at: t, rivals: nil, rules: rules)
        let r = rules.events.rocketRace
        guard EventSchedule.isUnlocked(.rocketRace, level: s.level, rules: rules.events) else { return .failure(.locked) }
        guard s.events.rocket.active == nil else { return .failure(.alreadyActive) }
        guard EventRotation.isLive(.rocketRace, at: t, level: s.level, rules: rules.events) else {
            return .failure(.notLive(next: EventRotation.nextStart(of: .rocketRace, after: EventRotation.week(t, rules.events),
                                                                   level: s.level, rules: rules.events)))
        }
        let day = EventSchedule.day(t, rules.events.calendar)
        if s.events.rocket.doneDay == day { return .failure(.doneForToday) }
        if let c = s.events.rocket.cooldownUntil, c > t { return .failure(.coolingDown(until: c)) }
        let stage = max(1, min(r.stages, s.events.rocket.nextStage))
        s.events.rocket.raceCounter += 1
        let end = EventSchedule.dayStart(day + 1, rules.events.calendar)
        let run = RocketRun(instance: EventInstance(event: rocketInstanceID(stage: stage), index: s.events.rocket.raceCounter,
                                                    start: t, end: end),
                            joinedAt: t, stage: stage, progress: 0)
        s.events.rocket.active = run
        s.events.rocket.day = day
        s.events.rocket.lastResult = nil
        s.events.rocket.lastRun = nil
        s.events.rocket.lastEndedAt = nil
        if !r.joinGrant.isEmpty && (!r.joinGrantOncePerDay || s.events.rocket.joinGrantDay != day) {
            s.events.rocket.joinGrantDay = day
            addClaim(&s, .rocketRace, .rocketJoin, grant: r.joinGrant, value: stage, index: run.instance.index, at: t)
        }
        return .success(run)
    }

    /// The race instance's id for the world: "rocketRace" for stage 1, "rocketRace.N" for stage N (SOC1's convention, the
    /// ◆ `rocketRace` call has no stage argument).
    public static func rocketInstanceID(stage: Int) -> EventID {
        stage <= 1 ? .rocketRace : EventID("\(EventID.rocketRace.rawValue).\(stage)")
    }

    /// The player's lane rank among `lanes` (the rivals' rows; the player's own row, if the world sends one, is skipped):
    /// progress descending, a tie behind the rival.
    static func rocketRank(progress: Int, lanes: [RaceStanding]) -> Int {
        1 + lanes.filter { !$0.isMe && $0.score >= progress }.count
    }

    /// Ends the running race: lost (a rival has N), expired (the day ended), or nothing. Called before a win counts and
    /// by the home refresh.
    static func rocketCheck(_ s: inout PlayerState, at t: SocialTime, rivals: RivalProvider?, _ rules: EconomyRules) -> [EventOutcome] {
        guard let run = s.events.rocket.active else { return [] }
        let n = rules.events.rocketRace.levels(stage: run.stage)
        let at = min(t, run.instance.end)
        if let rivals {
            let lanes = rivals.rocketRace(run.instance, joinedAt: run.joinedAt, at: at)
            if lanes.contains(where: { !$0.isMe && $0.score >= n }) {
                return rocketEnd(&s, .lost, rank: rocketRank(progress: run.progress, lanes: lanes), at: t, rules)
            }
            if t >= run.instance.end {
                return rocketEnd(&s, .expired, rank: rocketRank(progress: run.progress, lanes: lanes), at: t, rules)
            }
        } else if t >= run.instance.end {
            return rocketEnd(&s, .expired, rank: 0, at: t, rules)
        }
        return []
    }

    static func rocketEnd(_ s: inout PlayerState, _ result: EventRunResult, rank: Int, at t: SocialTime,
                          _ rules: EconomyRules) -> [EventOutcome] {
        if let run = s.events.rocket.active { keepEnded(&s, run, at: t) }
        s.events.rocket.active = nil
        s.events.rocket.lastResult = result
        s.events.rocket.cooldownUntil = SocialTime(seconds: t.seconds + max(0, rules.events.rocketRace.retryCooldown))
        return [.rocketFinished(rank: rank, reward: nil)]
    }

    /// A won level during a race. The win counts on the lane (VERIFIED L57: the strip showed the player 3/5 while a rival
    /// had 5/5), then the race is judged at that moment: a rival at N → lost (a tie at N goes to the rival, DECISION);
    /// else the player's N-th win → the stage prize.
    static func rocketWin(_ s: inout PlayerState, at t: SocialTime, rivals: RivalProvider, _ rules: EconomyRules) -> [EventOutcome] {
        guard var run = s.events.rocket.active else { return [] }
        if t >= run.instance.end { return rocketCheck(&s, at: t, rivals: rivals, rules) }
        let r = rules.events.rocketRace
        let n = r.levels(stage: run.stage)
        run.progress += 1
        s.events.rocket.active = run
        let lanes = rivals.rocketRace(run.instance, joinedAt: run.joinedAt, at: t)
        if lanes.contains(where: { !$0.isMe && $0.score >= n }) {
            return [.rocketProgress(mine: run.progress)]
                + rocketEnd(&s, .lost, rank: rocketRank(progress: run.progress, lanes: lanes), at: t, rules)
        }
        guard run.progress >= n else { return [.rocketProgress(mine: run.progress)] }
        let prize = r.prize(stage: run.stage)
        let day = EventSchedule.day(t, rules.events.calendar)
        keepEnded(&s, run, at: t)
        s.events.rocket.active = nil
        s.events.rocket.lastResult = .won
        s.events.wins[EventID.rocketRace.rawValue, default: 0] += 1
        if run.stage >= r.stages { s.events.rocket.doneDay = day; s.events.rocket.nextStage = 1 } else {
            s.events.rocket.nextStage = run.stage + 1
        }
        s.events.rocket.day = day
        if !prize.isEmpty {
            addClaim(&s, .rocketRace, .rocketPrize, grant: prize, value: 1, index: run.instance.index, at: t)
        }
        return [.rocketProgress(mine: run.progress), .rocketFinished(rank: 1, reward: prize.isEmpty ? nil : prize)]
    }

    /// The ended race as it stood at its end (the result page rebuilds its final lanes from it after a relaunch).
    static func keepEnded(_ s: inout PlayerState, _ run: RocketRun, at t: SocialTime) {
        s.events.rocket.lastRun = run
        s.events.rocket.lastEndedAt = min(t, run.instance.end)
    }

    /// A new event day: the stage progression starts over (a running race keeps its own window).
    static func rocketRoll(_ s: inout PlayerState, day: Int) {
        guard s.events.rocket.day != day, s.events.rocket.active == nil else { return }
        s.events.rocket.day = day
        s.events.rocket.nextStage = 1
    }
}
