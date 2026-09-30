import Foundation

// C3 (SPEC-architecture §4.10, §8.4 EventsDirector; SPEC-gameplay §11.4; SPEC-social §4). The events' pure state machines
// over `PlayerState.events`, advanced by the attempt hooks and by wall time; the opponents come from the social world behind
// ◆ `RivalProvider` (a stub in tests).
//
// What each finished attempt reports (SPEC-gameplay §11.4):
//   | hook   | multiplier            | Streak Race   | Claw          | Sky Jump              | Weekly | Rocket Race |
//   | won    | scores it, steps up   | + multiplier  | + multiplier  | +1 if first try (run) | +1     | +1 (race)   |
//   | failed | → x1                  | —             | —             | the run fails         | —      | —           |
// A won level counts for an event from its unlock level on (`EventSchedule.counts`); the multiplier rides on the Streak
// Race's unlock. Every hook first rolls the calendar (a new day / week closes the old contest, a new Claw week restarts).
// B1 (PUBLISH item 14): a FEATURED event (Claw / Up & Away / Rocket / Sky) acts only in the weeks the rotation makes it live
// for this player (`EventRotation.live`, events.md §4; the compiled default = the v552 plan, every week): the Claw scores and
// joins only in its weeks, Up & Away (BalloonRise.swift) only in its own, the joins refuse with `JoinError.notLive`, and a
// Sky Jump run joined before the roll keeps its own 24 h and pays (events.md §4.5).
// All times are the rewind-safe `EconomyClock` (the ◆ SocialClock over `social.highWater`): a device clock set back never
// rewinds a score, a run, a countdown or a week.
//
// GAME calls, in one `store.mutate` with the Economy call:  win → `Economy.finishAttempt(.won)` + `Events.onWin`;
// Level Failed / Quit → `finishAttempt(.lost)` + `Events.onLoss`; home visit / foreground → `Events.refresh`;
// "Tap to Claim" → `Events.claim`; the fail flow's step B → `Events.continueWarning`.

public enum Events {

    // MARK: hooks

    /// A won attempt (at the tap, banked with `Economy.finishAttempt`). Also records the win in the player's ledger
    /// (`SocialState.recordWin`, SOC1's cap) with the Streak Race points it scored — the world ranks the player from it.
    public static func onWin(_ s: inout PlayerState, _ ctx: WinContext, rivals: RivalProvider, rules: EconomyRules) -> [EventOutcome] {
        let t = EconomyClock.social(&s, wall: ctx.now)
        var out = roll(&s, at: t, rivals: rivals, rules: rules)
        let level = ctx.levels.first ?? s.level
        let ev = rules.events
        var points = 0
        // B1b: the holds this win moves past (EventFinished.swift DECISION: it scores their new instance)
        var movedOn: Set<EventID> = []
        if EventSchedule.counts(.streakRace, wonLevel: level, rules: ev) {
            let w = streakWin(&s.events, rules)
            points = w.points
            if w.from != w.to { out.append(.multiplier(from: w.from, to: w.to)) }
            joinStreakRace(&s, at: t, rules)
            s.events.streakRace.score += points
            s.events.streakRace.lastScoreAt = t
            out.append(.streakRaceScore(s.events.streakRace.score))
            movedOn.insert(.streakRace)
        }
        let live = EventRotation.live(at: t, level: s.level, rules: ev)
        if EventSchedule.counts(.clawChallenge, wonLevel: level, rules: ev), live.contains(.clawChallenge) {
            out += clawAdd(&s, points: points, at: t, rules)
            movedOn.formUnion([.clawChallenge, .balloonRise])                  // one ladder slot
        }
        if EventSchedule.counts(.balloonRise, wonLevel: level, rules: ev), live.contains(.balloonRise) {
            out += balloonWin(&s, at: t, rules)
            movedOn.formUnion([.clawChallenge, .balloonRise])
        }
        dropFinished(&s, movedOn)
        if EventSchedule.counts(.weeklyContest, wonLevel: level, rules: ev) {
            joinWeeklyContest(&s, at: t, rules)
            s.events.weekly.score += ev.weekly.pointsPerWin
            s.events.weekly.lastScoreAt = t
            out.append(.weeklyScore(s.events.weekly.score))
        }
        out += skyWin(&s, firstTry: ctx.firstTry, at: t, rivals: rivals, rules)
        if s.events.rocket.active != nil { out += rocketWin(&s, at: t, rivals: rivals, rules) }
        s.social.recordWin(level: ctx.levels.max() ?? level, firstTry: ctx.firstTry, points: points, at: t)
        return out
    }

    /// A failed attempt (Level Failed by time or hearts, Quit, a killed app): the multiplier → x1, a Sky Jump run fails,
    /// Up & Away's counter → 0 (B1, v582 VERIFIED). Claw points, Streak Race / Weekly scores and a Rocket Race's progress are
    /// untouched (VERIFIED fail.md §7).
    public static func onLoss(_ s: inout PlayerState, _ ctx: LossContext, rules: EconomyRules) -> [EventOutcome] {
        let t = EconomyClock.social(&s, wall: ctx.now)
        var out = roll(&s, at: t, rivals: nil, rules: rules)
        if let f = streakFail(&s.events, rules) { out.append(.multiplier(from: f.from, to: f.to)) }
        out += balloonFail(&s, at: t, rules)
        out += skyFail(&s, .failed, at: t, rules)
        s.social.recordFail(level: ctx.levels.first ?? s.level, at: t)
        return out
    }

    /// Wall time (home visit, foreground, a periodic tick): rolls the calendar, ends a Rocket Race a rival has finished or
    /// whose day ended, fails a Sky Jump run whose 24 h ran out, settles ended Streak Races from the world's final standings,
    /// and — `home` — joins the day's Streak Race and the week's ladder event (Claw or Up & Away) once unlocked and live.
    public static func refresh(_ s: inout PlayerState, now: Date, rivals: RivalProvider, me: PlayerStanding,
                               rules: EconomyRules, home: Bool = true) -> [EventOutcome] {
        let t = EconomyClock.social(&s, wall: now)
        var out = roll(&s, at: t, rivals: rivals, rules: rules)
        out += rocketCheck(&s, at: t, rivals: rivals, rules)
        let races = s.events.toSettle.filter { $0.event == .streakRace }
        s.events.toSettle.removeAll { $0.event == .streakRace }
        for res in races { out += settleStreakRace(&s, res, rivals: rivals, me: me, rules) }
        if home {
            let ev = rules.events
            if EventSchedule.isUnlocked(.streakRace, level: s.level, rules: ev) { joinStreakRace(&s, at: t, rules) }
            let live = EventRotation.live(at: t, level: s.level, rules: ev)
            if live.contains(.clawChallenge) { clawJoin(&s, at: t, rules) }
            if live.contains(.balloonRise) { balloonJoin(&s, at: t, rules) }
        }
        return out
    }

    /// Calendar roll at `t`: closes contests of earlier days / weeks (they wait in `toSettle`), restarts the Claw on a new
    /// week, expires Sky Jump runs and Rocket Races, resets the per-day stage progressions.
    static func roll(_ s: inout PlayerState, at t: SocialTime, rivals: RivalProvider?, rules: EconomyRules) -> [EventOutcome] {
        let day = EventSchedule.day(t, rules.events.calendar)
        rollCalendar(&s, at: t, rules)
        var out: [EventOutcome] = []
        if let run = s.events.rocket.active, t >= run.instance.end { out += rocketCheck(&s, at: t, rivals: rivals, rules) }
        rocketRoll(&s, day: day)
        out += skyRoll(&s, at: t, day: day, rules)
        return out
    }

    /// The roll of the calendar events (no world query): B1b first holds the joined instances that ended ("Finished",
    /// EventFinished.swift; only while the rotation runs), then — as before — the contests of earlier days / weeks wait in
    /// `toSettle` and a new week restarts the ladder events.
    static func rollCalendar(_ s: inout PlayerState, at t: SocialTime, _ rules: EconomyRules) {
        let c = rules.events.calendar
        holdFinished(&s, at: t, rules)
        contestRoll(&s.events.streakRace, current: EventSchedule.day(t, c), event: .streakRace, toSettle: &s.events.toSettle)
        contestRoll(&s.events.weekly, current: EventSchedule.week(t, c), event: .weeklyContest, toSettle: &s.events.toSettle)
        clawRoll(&s, at: t, rules)
        balloonRoll(&s, at: t, rules)
    }

    /// The world clock stepped back (SPEC-social §5: a repaired clock > 30 days in the future rebases once): runs and races
    /// stamped in the abandoned future end, cooldowns reaching into it are cleared, ended contests of later days / weeks
    /// are not settled, and the running ones are dropped at the next roll (`contestRoll`). Claims already earned stay.
    /// An ended run is kept like every other end (`keepEnded`: `lastRun` + `lastEndedAt`, CORE-2 / INTEG review) so its
    /// result page draws its final lanes; it is judged at `from`, the abandoned clock's last moment (the high-water mark
    /// before the step; capped at the run's window end like every end) — the moment it was last live, in the same timeline
    /// as its own join time and window. (`t` lies before the run's join: the world would draw its field before the start.)
    static func rebase(_ s: inout PlayerState, to t: SocialTime, from last: SocialTime) {
        if let run = s.events.sky.active, run.instance.start > t {
            keepEnded(&s, run, at: last)
            s.events.sky.active = nil; s.events.sky.lastResult = .expired
        }
        if let run = s.events.rocket.active, run.instance.start > t {
            keepEnded(&s, run, at: last)
            s.events.rocket.active = nil; s.events.rocket.lastResult = .expired
        }
        if let c = s.events.sky.cooldownUntil, c > t { s.events.sky.cooldownUntil = nil }
        if let c = s.events.rocket.cooldownUntil, c > t { s.events.rocket.cooldownUntil = nil }
        s.events.toSettle.removeAll { res in
            switch res.event {
            case .streakRace: return EventSchedule.dayStart(res.index) > t
            default: return EventSchedule.weekStart(res.index) > t
            }
        }
        // B1b: a hold of the abandoned future (its instance has not ended at `t`) goes, like its unsettled contest
        s.events.finished.removeAll { f in
            f.event == .streakRace ? EventSchedule.dayStart(f.index + 1) > t : EventSchedule.weekStart(f.index + 1) > t
        }
    }

    // MARK: claims

    static func addClaim(_ s: inout PlayerState, _ e: EventID, _ k: EventClaim.Kind, grant: Grant, value: Int, index: Int,
                         at t: SocialTime) {
        let id = max(1, s.events.nextClaimID)
        s.events.nextClaimID = id + 1
        s.events.claims.append(EventClaim(id: id, event: e, kind: k, grant: grant, value: value, index: index, at: t))
    }

    /// "Tap to Claim": applies the claim's grant (`Economy.grant`, ∞ stacking at the effective time) and removes it.
    /// nil for an unknown / already claimed id.
    @discardableResult
    public static func claim(_ s: inout PlayerState, id: Int, now: Date) -> Grant? {
        guard let i = s.events.claims.firstIndex(where: { $0.id == id }) else { return nil }
        let c = s.events.claims.remove(at: i)
        Economy.grant(&s, c.grant, now: now)
        // B1b: claiming an ended contest's rank prize is opening its result (v582: the claim, then the new week)
        switch c.kind {
        case .streakRacePrize: s.events.finished.removeAll { $0.event == .streakRace && $0.index == c.index }
        case .weeklyPrize: s.events.finished.removeAll { $0.event == .weeklyContest && $0.index == c.index }
        default: break
        }
        return c.grant
    }

    // MARK: the fail flow (SPEC-gameplay §7.1 step B)

    public struct StreakWarning: Equatable, Sendable {
        /// The multiplier is above x1: step B ("Continue? … your streak!") is shown (`LevelSession.streakActive`).
        public var streakActive: Bool
        /// While the Claw Challenge runs: "You will lose %lld token and your streak!" with this number (the multiplier =
        /// the Claw points the next win would add); nil → "You will lose your streak!".
        public var tokens: Int?
        public var multiplier: Int
    }

    public static func continueWarning(_ s: PlayerState, now: Date, rules: EconomyRules) -> StreakWarning {
        let m = multiplier(s, rules: rules)
        let active = s.events.streakStep > 0 && EventSchedule.isUnlocked(.streakRace, level: s.level, rules: rules.events)
        // B1: the token line only while the Claw runs THIS week (an Up & Away week has no token; v582's bands carry no
        // balloon wording, VERIFIED balloon.md §5 — its fall page follows the bands instead)
        let clawRunning = EventRotation.isLive(.clawChallenge, at: EconomyClock.peekSocial(s, wall: now), level: s.level, rules: rules.events)
            && clawTarget(s.events.claw, rules: rules) != nil
        return StreakWarning(streakActive: active, tokens: active && clawRunning ? m : nil, multiplier: m)
    }

    // MARK: status (home bar, badges, offers)

    public struct ClawStatus: Equatable, Sendable {
        public var step: Int                 // 1-based step being filled (21 = the ladder is complete)
        public var points: Int
        public var target: Int
        public var nextReward: Grant?
        public var complete: Bool
        public var endsAt: SocialTime
        /// `home.claw` accessibility value "n/target xM" (SPEC-architecture §9.8).
        public var accessibilityValue: String
    }

    public struct ContestStatus: Equatable, Sendable {
        public var index: Int
        public var joined: Bool
        public var score: Int
        public var endsAt: SocialTime
    }

    public struct RunStatus: Equatable, Sendable {
        /// The offer's "Start" works now.
        public var joinable: Bool
        public var why: JoinError?
        /// The stage a join would start (or the running stage).
        public var stage: Int
        public var levels: Int
        public var progress: Int?
        /// The running race / run's end, else the event day's end (the offer's countdown).
        public var endsAt: SocialTime
        public var lastResult: EventRunResult?
    }

    public struct Status: Equatable, Sendable {
        public var multiplier: Int
        public var streakRace: ContestStatus?
        public var claw: ClawStatus?
        public var weekly: ContestStatus?
        public var rocketRace: RunStatus?
        public var skyJump: RunStatus?
        public var claims: [EventClaim]
        /// B1: Up & Away while it is live this week (nil otherwise).
        public var balloon: BalloonStatus? = nil
        /// B1: this week's calendar picks (the same for every player; independent of the kill switch).
        public var week: WeekPlan? = nil
        /// B1: what THIS player sees this week (segmentation, unlocks, the kill switch).
        public var live = LiveEvents()
        /// B1: what this player will see next week (the "Coming next" teaser, the week-start notification).
        public var nextLive = LiveEvents()
        /// B1: the rotation is on (false = the v552 plan).
        public var rotating = false
        /// B1b: the ended instances the player took part in and has not opened yet (v582 "Finished", EventFinished.swift): the
        /// home shows these in their slot in place of the new instance. Empty while the rotation is off.
        public var finished = FinishedStatus()
    }

    /// What the home shows at `now` (nil = the event is still locked or, for a featured event, not live this week — a Sky
    /// Jump run joined before the roll still shows until it ends). Read-only: nothing is joined or rolled in `s`.
    public static func status(_ s: PlayerState, now: Date, rules: EconomyRules) -> Status {
        var c = s
        let t = EconomyClock.social(&c, wall: now)
        _ = roll(&c, at: t, rivals: nil, rules: rules)
        let ev = rules.events
        let cal = ev.calendar
        let day = EventSchedule.day(t, cal)
        let dayEnd = EventSchedule.dayStart(day + 1, cal)
        func contest(_ e: EventID, _ st: ContestState, _ index: Int, _ end: SocialTime) -> ContestStatus? {
            guard EventSchedule.isUnlocked(e, level: c.level, rules: ev) else { return nil }
            return ContestStatus(index: index, joined: st.index == index, score: st.index == index ? st.score : 0, endsAt: end)
        }
        let week = EventSchedule.week(t, cal)
        let rw = EventRotation.week(t, ev)
        let live = EventRotation.live(week: rw, level: c.level, rules: ev)
        var claw: ClawStatus?
        if live.contains(.clawChallenge), !rules.claw.ladder.isEmpty {
            let idx = clawIndex(t, rules)
            let end = rules.claw.period == "day" ? EventSchedule.dayStart(idx + 1, cal) : EventSchedule.weekStart(idx + 1, cal)
            claw = clawStatus(c.events.claw, endsAt: end, multiplier: multiplier(c, rules: rules), rules: rules)
        }
        var rocket: RunStatus?
        if EventSchedule.isUnlocked(.rocketRace, level: c.level, rules: ev), live.contains(.rocketRace) || c.events.rocket.active != nil {
            let rs = c.events.rocket
            let why: JoinError? = rs.active != nil ? .alreadyActive
                : !live.contains(.rocketRace) ? .notLive(next: EventRotation.nextStart(of: .rocketRace, after: rw, level: c.level, rules: ev))
                : rs.doneDay == day ? .doneForToday
                : (rs.cooldownUntil.map { $0 > t } ?? false) ? .coolingDown(until: rs.cooldownUntil!) : nil
            let stage = rs.active?.stage ?? max(1, min(ev.rocketRace.stages, rs.nextStage))
            rocket = RunStatus(joinable: why == nil, why: why, stage: stage, levels: ev.rocketRace.levels(stage: stage),
                               progress: rs.active?.progress, endsAt: rs.active?.instance.end ?? dayEnd, lastResult: rs.lastResult)
        }
        var sky: RunStatus?
        if EventSchedule.isUnlocked(.skyJump, level: c.level, rules: ev), live.contains(.skyJump) || c.events.sky.active != nil {
            let ss = c.events.sky
            let stage = ss.active?.stage ?? max(1, min(ev.skyJump.stages, ss.nextStage))
            let why: JoinError? = ss.active != nil ? .alreadyActive
                : !live.contains(.skyJump) ? .notLive(next: EventRotation.nextStart(of: .skyJump, after: rw, level: c.level, rules: ev))
                : ss.doneDay == day ? .doneForToday
                : (ss.cooldownUntil.map { $0 > t } ?? false) ? .coolingDown(until: ss.cooldownUntil!)
                : (stage == 1 && ss.runsToday >= ev.skyJump.maxRunsPerDay) ? .limitReached : nil
            sky = RunStatus(joinable: why == nil, why: why, stage: stage, levels: ev.skyJump.levels(stage: stage),
                            progress: ss.active?.progress, endsAt: ss.active?.instance.end ?? dayEnd, lastResult: ss.lastResult)
        }
        return Status(multiplier: multiplier(c, rules: rules),
                      streakRace: contest(.streakRace, c.events.streakRace, day, dayEnd),
                      claw: claw,
                      weekly: contest(.weeklyContest, c.events.weekly, week, EventSchedule.weekStart(week + 1, cal)),
                      rocketRace: rocket, skyJump: sky, claims: c.events.claims,
                      balloon: live.contains(.balloonRise) ? balloonStatus(c, at: t, rules) : nil,
                      week: EventRotation.plan(week: rw, rules: ev), live: live,
                      nextLive: EventRotation.live(week: rw + 1, level: c.level, rules: ev), rotating: ev.rotation.enabled,
                      finished: finishedStatus(c, multiplier: multiplier(c, rules: rules), rules: rules))
    }

    /// A Treasure Climb bar from a ladder state (the running week's, or B1b's held one as it stood at its end).
    static func clawStatus(_ cs: ClawState, endsAt end: SocialTime, multiplier m: Int, rules: EconomyRules) -> ClawStatus {
        let target = clawTarget(cs, rules: rules) ?? rules.claw.ladder[rules.claw.ladder.count - 1].threshold
        let complete = cs.step >= rules.claw.ladder.count
        let points = complete ? target : cs.points
        return ClawStatus(step: cs.step + 1, points: points, target: target, nextReward: clawNextReward(cs, rules: rules),
                          complete: complete, endsAt: end, accessibilityValue: "\(points)/\(target) x\(m)")
    }
}
