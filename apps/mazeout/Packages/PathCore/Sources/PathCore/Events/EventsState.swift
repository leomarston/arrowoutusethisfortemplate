import Foundation

// C3 (SPEC-architecture §4.10, §4.12; SPEC-gameplay §11; SPEC-social §4). The events' saved state inside
// `PlayerState.events`. ADDITIVE-ONLY (§4.12): every field has a default and decodes with `decodeIfPresent`, so an old save
// (the frozen v1 fixture's `"events": {}`) keeps decoding forever; a rename or a removal needs a Migration.
// Only the PLAYER's own facts are stored (step, points, scores, joins, runs, claims). Opponents are derived by the social
// world (SOC1, `RivalProvider`) from the install seed + these facts.
// `EventInstance` and `SkyJumpRun` appear in ◆ RivalProvider's signatures: keep them Sendable with these fields.

/// The events' saved state (streak multiplier, Claw, Streak Race, Weekly Contest, Rocket Race, Sky Jump, claims).
public struct EventsState: Codable, Sendable, Equatable {
    /// The win-streak multiplier: an index into `rules.streak.steps` (0 = x1). One global value (SPEC-gameplay §11.1).
    public var streakStep = 0
    public var claw = ClawState()
    /// The Streak Race of the current event day (`index` = day).
    public var streakRace = ContestState()
    /// The Weekly Contest of the current event week (`index` = week).
    public var weekly = ContestState()
    public var rocket = RocketState()
    public var sky = SkyJumpState()
    /// Rewards waiting for "Tap to Claim" on home (Claw steps, prizes, shares, the Rocket Race join ∞).
    public var claims: [EventClaim] = []
    public var nextClaimID = 1
    /// Ended contests whose final rank is not known yet (settled by `Events.refresh` / `Events.settleWeekly`).
    public var toSettle: [ContestResult] = []
    /// Event wins for the Profile ("Streak Race Wins", "Rocket Race Wins", "Sky Jump Wins", "Claw Challenge Wins";
    /// VERIFIED meta §2), EventID raw value → count. Weekly Contest wins are `PlayerState.stats.weeklyContestWins`.
    public var wins: [String: Int] = [:]
    /// Economy bookkeeping the frozen `ActiveAttempt` has no room for: the running attempt started under ∞ lives, so it
    /// took no life and a win refunds none (VERIFIED fail.md §2 #1: ∞ is checked at the level start).
    public var attemptFree = false
    /// B1: Up & Away (the v582 Balloon Rise rules; BalloonRise.swift). Additive: an old save decodes to the empty state.
    public var balloon = BalloonState()
    /// B1: the event notifications scheduled at the last background and the last one delivered (the ≤ 1 per 24 h cap,
    /// EventNotifications.swift). Additive.
    public var notify = EventNotifyState()
    /// B1b: the ended instances the player took part in, held as "Finished" until their result is opened (v582 PH-0a;
    /// EventFinished.swift). Additive; never stored while the rotation is off.
    public var finished: [FinishedEvent] = []

    public init() {}

    enum CodingKeys: String, CodingKey {
        case streakStep, claw, streakRace, weekly, rocket, sky, claims, nextClaimID, toSettle, wins, attemptFree, balloon, notify,
             finished
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); let d = EventsState()
        streakStep = try c.v(.streakStep, d.streakStep)
        claw = try c.v(.claw, d.claw)
        streakRace = try c.v(.streakRace, d.streakRace)
        weekly = try c.v(.weekly, d.weekly)
        rocket = try c.v(.rocket, d.rocket)
        sky = try c.v(.sky, d.sky)
        claims = try c.v(.claims, d.claims)
        nextClaimID = try c.v(.nextClaimID, d.nextClaimID)
        toSettle = try c.v(.toSettle, d.toSettle)
        wins = try c.v(.wins, d.wins)
        attemptFree = try c.v(.attemptFree, d.attemptFree)
        balloon = try c.v(.balloon, d.balloon)
        notify = try c.v(.notify, d.notify)
        finished = try c.v(.finished, d.finished)
    }

    /// Every field as before; B1's two blocks (and B1b's holds) only when they hold something, so a save that never met them
    /// re-encodes byte-identically (like the optional fields).
    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(streakStep, forKey: .streakStep)
        try c.encode(claw, forKey: .claw)
        try c.encode(streakRace, forKey: .streakRace)
        try c.encode(weekly, forKey: .weekly)
        try c.encode(rocket, forKey: .rocket)
        try c.encode(sky, forKey: .sky)
        try c.encode(claims, forKey: .claims)
        try c.encode(nextClaimID, forKey: .nextClaimID)
        try c.encode(toSettle, forKey: .toSettle)
        try c.encode(wins, forKey: .wins)
        try c.encode(attemptFree, forKey: .attemptFree)
        if balloon != BalloonState() { try c.encode(balloon, forKey: .balloon) }
        if notify != EventNotifyState() { try c.encode(notify, forKey: .notify) }
        if !finished.isEmpty { try c.encode(finished, forKey: .finished) }
    }
}

/// The Claw Challenge of one event week (SPEC-gameplay §11.2).
public struct ClawState: Codable, Sendable, Equatable {
    /// The week this challenge belongs to (nil = not started this week).
    public var week: Int?
    /// Points toward the current step's threshold (the home bar "122/500").
    public var points = 0
    /// Completed steps (0…20); the current step is `step + 1`.
    public var step = 0

    public init(week: Int? = nil, points: Int = 0, step: Int = 0) { self.week = week; self.points = points; self.step = step }

    enum CodingKeys: String, CodingKey { case week, points, step }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        week = try c.decodeIfPresent(Int.self, forKey: .week)
        points = try c.v(.points, 0); step = try c.v(.step, 0)
    }
}

/// A ranked group contest the player scores in (Streak Race per day, Weekly Contest per week).
public struct ContestState: Codable, Sendable, Equatable {
    /// Day (Streak Race) or week (Weekly) index; nil = not joined in the current one.
    public var index: Int?
    public var joinedAt: SocialTime?
    public var score = 0
    /// The moment of the last scoring win (ties: the earlier reach ranks first, SPEC-social §4.3).
    public var lastScoreAt: SocialTime?

    public init(index: Int? = nil, joinedAt: SocialTime? = nil, score: Int = 0, lastScoreAt: SocialTime? = nil) {
        self.index = index; self.joinedAt = joinedAt; self.score = score; self.lastScoreAt = lastScoreAt
    }

    enum CodingKeys: String, CodingKey { case index, joinedAt, score, lastScoreAt }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        index = try c.decodeIfPresent(Int.self, forKey: .index)
        joinedAt = try c.decodeIfPresent(SocialTime.self, forKey: .joinedAt)
        score = try c.v(.score, 0)
        lastScoreAt = try c.decodeIfPresent(SocialTime.self, forKey: .lastScoreAt)
    }
}

/// An ended contest waiting for its final rank.
public struct ContestResult: Codable, Sendable, Equatable {
    public var event: EventID
    public var index: Int
    public var score: Int
    public var joinedAt: SocialTime?
    public var lastScoreAt: SocialTime?

    public init(event: EventID, index: Int, score: Int, joinedAt: SocialTime?, lastScoreAt: SocialTime?) {
        self.event = event; self.index = index; self.score = score; self.joinedAt = joinedAt; self.lastScoreAt = lastScoreAt
    }
}

/// One run of a timed event (its id and window on the world clock).
public struct EventInstance: Codable, Sendable, Equatable, Hashable {
    public var event: EventID
    public var index: Int                    // day / week index (calendar events), race / attempt counter (joined events)
    public var start: SocialTime
    public var end: SocialTime

    public init(event: EventID, index: Int, start: SocialTime, end: SocialTime) {
        self.event = event; self.index = index; self.start = start; self.end = end
    }
}

/// The player's Sky Jump run. `stage` is 1-based (1…3); `progress` = first-try wins in a row in this stage.
public struct SkyJumpRun: Codable, Sendable, Equatable, Hashable {
    public var instance: EventInstance
    public var joinedAt: SocialTime
    public var stage: Int
    public var progress: Int

    public init(instance: EventInstance, joinedAt: SocialTime, stage: Int = 1, progress: Int = 0) {
        self.instance = instance; self.joinedAt = joinedAt; self.stage = stage; self.progress = progress
    }
}

/// The player's Rocket Race. `stage` is 1-based; `progress` = levels beaten since joining.
public struct RocketRun: Codable, Sendable, Equatable, Hashable {
    public var instance: EventInstance
    public var joinedAt: SocialTime
    public var stage: Int
    public var progress: Int

    public init(instance: EventInstance, joinedAt: SocialTime, stage: Int = 1, progress: Int = 0) {
        self.instance = instance; self.joinedAt = joinedAt; self.stage = stage; self.progress = progress
    }
}

/// How a joined race / run ended (the post-level screens and the offers read it).
public enum EventRunResult: String, Codable, Sendable { case won, lost, expired, failed }

public struct RocketState: Codable, Sendable, Equatable {
    public var active: RocketRun?
    public var raceCounter = 0
    /// The event day the stage progression below belongs to.
    public var day: Int?
    /// The stage the next join starts (1…3); back to 1 on a new event day.
    public var nextStage = 1
    /// The event day on which the last stage was won (no more races until the next day).
    public var doneDay: Int?
    /// The event day whose join grant (∞ 30m) was given.
    public var joinGrantDay: Int?
    public var cooldownUntil: SocialTime?
    public var lastResult: EventRunResult?
    /// The race that ended last, as it stood at its end (INTEG for SOC2's result page): its window, join time, stage and the
    /// player's FINAL lane (`progress`). The rivals' final lanes are the world's (`RivalProvider.rocketRace`), a pure function
    /// of this run's instance + join time and `lastEndedAt`, so only the player's facts are kept (as everywhere in C3) and a
    /// relaunch rebuilds the same lanes. nil = no race ended since joining (or a save from before this field).
    public var lastRun: RocketRun?
    /// When C3 judged `lastRun` over (the win, the check that found a rival at N, or the day's end; at most the window's end).
    public var lastEndedAt: SocialTime?

    public init() {}

    enum CodingKeys: String, CodingKey {
        case active, raceCounter, day, nextStage, doneDay, joinGrantDay, cooldownUntil, lastResult, lastRun, lastEndedAt
    }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        active = try c.decodeIfPresent(RocketRun.self, forKey: .active)
        raceCounter = try c.v(.raceCounter, 0)
        day = try c.decodeIfPresent(Int.self, forKey: .day)
        nextStage = try c.v(.nextStage, 1)
        doneDay = try c.decodeIfPresent(Int.self, forKey: .doneDay)
        joinGrantDay = try c.decodeIfPresent(Int.self, forKey: .joinGrantDay)
        cooldownUntil = try c.decodeIfPresent(SocialTime.self, forKey: .cooldownUntil)
        lastResult = try c.decodeIfPresent(EventRunResult.self, forKey: .lastResult)
        lastRun = try c.decodeIfPresent(RocketRun.self, forKey: .lastRun)
        lastEndedAt = try c.decodeIfPresent(SocialTime.self, forKey: .lastEndedAt)
    }
}

public struct SkyJumpState: Codable, Sendable, Equatable {
    public var active: SkyJumpRun?
    public var attemptCounter = 0
    /// The event day `runsToday` / `nextStage` belong to.
    public var day: Int?
    /// Stage-1 runs started on `day` (capped by `skyJump.maxRunsPerDay`).
    public var runsToday = 0
    public var nextStage = 1
    public var doneDay: Int?
    public var cooldownUntil: SocialTime?
    public var lastResult: EventRunResult?
    /// The run that ended last, as it stood at its end (INTEG for SOC2's map / "You win!" pages): its window, join time,
    /// stage and the player's FINAL progress. The field (survivor curve, portraits) is the world's, a pure function of this
    /// run and `lastEndedAt` (`RivalProvider.skyJump`), so a relaunch rebuilds the same result. nil = no run ended since
    /// joining (or a save from before this field).
    public var lastRun: SkyJumpRun?
    /// When C3 judged `lastRun` over (the N-th win, the failed attempt, or the 24 h window; at most the window's end).
    public var lastEndedAt: SocialTime?

    public init() {}

    enum CodingKeys: String, CodingKey {
        case active, attemptCounter, day, runsToday, nextStage, doneDay, cooldownUntil, lastResult, lastRun, lastEndedAt
    }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        active = try c.decodeIfPresent(SkyJumpRun.self, forKey: .active)
        attemptCounter = try c.v(.attemptCounter, 0)
        day = try c.decodeIfPresent(Int.self, forKey: .day)
        runsToday = try c.v(.runsToday, 0)
        nextStage = try c.v(.nextStage, 1)
        doneDay = try c.decodeIfPresent(Int.self, forKey: .doneDay)
        cooldownUntil = try c.decodeIfPresent(SocialTime.self, forKey: .cooldownUntil)
        lastResult = try c.decodeIfPresent(EventRunResult.self, forKey: .lastResult)
        lastRun = try c.decodeIfPresent(SkyJumpRun.self, forKey: .lastRun)
        lastEndedAt = try c.decodeIfPresent(SocialTime.self, forKey: .lastEndedAt)
    }
}

/// A reward waiting for "Tap to Claim" (SPEC-gameplay §11.2; SPEC-social §4.8 presentation order).
public struct EventClaim: Codable, Sendable, Equatable, Identifiable {
    public enum Kind: String, Codable, Sendable {
        case clawStep, streakRacePrize, weeklyPrize, skyJumpShare, rocketPrize, rocketJoin
        /// B1: an Up & Away platform's chest (`value` = the platform, 1-based; `index` = the event week).
        case balloonStep
    }
    public var id: Int
    public var event: EventID
    public var kind: Kind
    public var grant: Grant
    /// Claw step (1-based), final rank (Streak Race / Weekly / Rocket Race), winners (Sky Jump), stage (Rocket join),
    /// platform (Up & Away, 1-based).
    public var value: Int
    /// Week / day / race / run index.
    public var index: Int
    public var at: SocialTime

    public init(id: Int, event: EventID, kind: Kind, grant: Grant, value: Int, index: Int, at: SocialTime) {
        self.id = id; self.event = event; self.kind = kind; self.grant = grant; self.value = value; self.index = index; self.at = at
    }
}
