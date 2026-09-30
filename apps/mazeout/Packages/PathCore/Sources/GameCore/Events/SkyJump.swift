import Foundation

// C3 (SPEC-gameplay §11.3–§11.4; SPEC-social §4.6, D15; VERIFIED flows L39–L44, meta §5.4). The player's Sky Jump run:
// - offered after the L39 win (reach L40); a free "Start" begins a run that lasts 24 h (VERIFIED "23h 58m");
// - stage s: N = 5 / 7 / 9 FIRST-TRY wins in a row; a non-first-try win neither advances nor fails the run (DECISION: the
//   text says "in a row on first try"); a failed attempt (not a paid continue) fails the run ("If you fail a level, you
//   will fail the challenge!"), and so does the 24 h window running out;
// - the N-th win wins the stage: the pool (5000 / 7000 / 10000) is shared by the winners the world reports
//   (`RivalProvider.skyJump(run, at:).winners`, SOC1; VERIFIED 5000 / 7 = 714) → a claim; the next stage is offered at once;
//   the last stage → no more runs until the next event day;
// - a failed run can be re-joined after 30 min, at most 2 stage-1 runs per event day; a new event day starts at stage 1
//   (DECISION, SPEC-social §4.6).
// "Players" left and the portraits are SOC1's (`SkyJumpField`).
// B1: "Start" works only in the weeks the rotation features Sky Jump for this player (`JoinError.notLive`); a run joined
// before the Monday roll keeps its own 24 h and its win pays (events.md §4.5).

extension Events {
    /// "Start" on the Sky Jump offer: a new 24 h run at the next stage.
    public static func joinSkyJump(_ s: inout PlayerState, now: Date, rules: EconomyRules) -> Result<SkyJumpRun, JoinError> {
        let t = EconomyClock.social(&s, wall: now)
        _ = roll(&s, at: t, rivals: nil, rules: rules)
        let r = rules.events.skyJump
        guard EventSchedule.isUnlocked(.skyJump, level: s.level, rules: rules.events) else { return .failure(.locked) }
        guard s.events.sky.active == nil else { return .failure(.alreadyActive) }
        guard EventRotation.isLive(.skyJump, at: t, level: s.level, rules: rules.events) else {
            return .failure(.notLive(next: EventRotation.nextStart(of: .skyJump, after: EventRotation.week(t, rules.events),
                                                                   level: s.level, rules: rules.events)))
        }
        let day = EventSchedule.day(t, rules.events.calendar)
        if s.events.sky.doneDay == day { return .failure(.doneForToday) }
        if let c = s.events.sky.cooldownUntil, c > t { return .failure(.coolingDown(until: c)) }
        let stage = max(1, min(r.stages, s.events.sky.nextStage))
        if stage == 1 && s.events.sky.runsToday >= r.maxRunsPerDay { return .failure(.limitReached) }
        s.events.sky.attemptCounter += 1
        if stage == 1 { s.events.sky.runsToday += 1 }
        let inst = EventInstance(event: .skyJump, index: s.events.sky.attemptCounter, start: t,
                                 end: SocialTime(seconds: t.seconds + r.runSeconds))
        let run = SkyJumpRun(instance: inst, joinedAt: t, stage: stage, progress: 0)
        s.events.sky.active = run
        s.events.sky.day = day
        s.events.sky.lastResult = nil
        s.events.sky.lastRun = nil
        s.events.sky.lastEndedAt = nil
        return .success(run)
    }

    /// A won level during a run.
    static func skyWin(_ s: inout PlayerState, firstTry: Bool, at t: SocialTime, rivals: RivalProvider,
                       _ rules: EconomyRules) -> [EventOutcome] {
        guard var run = s.events.sky.active else { return [] }
        let r = rules.events.skyJump
        guard firstTry || !r.firstTryOnly else { return [] }
        run.progress += 1
        let n = r.levels(stage: run.stage)
        guard run.progress >= n else {
            s.events.sky.active = run
            return [.skyJumpProgress(levels: run.progress, of: n)]
        }
        let field = rivals.skyJump(run, at: t)
        let winners = max(1, field.winners)                       // the player is one of them
        let share = r.pool(stage: run.stage) / winners
        let day = EventSchedule.day(t, rules.events.calendar)
        keepEnded(&s, run, at: t)
        s.events.sky.active = nil
        s.events.sky.lastResult = .won
        s.events.wins[EventID.skyJump.rawValue, default: 0] += 1
        if run.stage >= r.stages { s.events.sky.doneDay = day; s.events.sky.nextStage = 1 } else {
            s.events.sky.nextStage = run.stage + 1
        }
        if share > 0 {
            addClaim(&s, .skyJump, .skyJumpShare, grant: .coins(share), value: winners, index: run.instance.index, at: t)
        }
        return [.skyJumpProgress(levels: run.progress, of: n), .skyJumpWon(share: share, winners: winners)]
    }

    /// The run fails (a failed attempt, or its 24 h ran out): the cooldown starts, the next run is stage 1 again.
    static func skyFail(_ s: inout PlayerState, _ result: EventRunResult, at t: SocialTime, _ rules: EconomyRules) -> [EventOutcome] {
        guard let run = s.events.sky.active else { return [] }
        keepEnded(&s, run, at: t)
        s.events.sky.active = nil
        s.events.sky.lastResult = result
        s.events.sky.nextStage = 1
        s.events.sky.cooldownUntil = SocialTime(seconds: t.seconds + max(0, rules.events.skyJump.retryCooldown))
        return [.skyJumpFailed]
    }

    /// The ended run as it stood at its end (the result pages rebuild the field from it after a relaunch).
    static func keepEnded(_ s: inout PlayerState, _ run: SkyJumpRun, at t: SocialTime) {
        s.events.sky.lastRun = run
        s.events.sky.lastEndedAt = min(t, run.instance.end)
    }

    /// A new event day (the run cap and the stage progression start over) and the 24 h window.
    static func skyRoll(_ s: inout PlayerState, at t: SocialTime, day: Int, _ rules: EconomyRules) -> [EventOutcome] {
        var out: [EventOutcome] = []
        if let run = s.events.sky.active, t >= run.instance.end { out += skyFail(&s, .expired, at: t, rules) }
        if s.events.sky.day != day && s.events.sky.active == nil {
            s.events.sky.day = day
            s.events.sky.runsToday = 0
            s.events.sky.nextStage = 1
        }
        return out
    }
}
