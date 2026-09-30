import Foundation

// C3 (SPEC-architecture §4.10; SPEC-gameplay §11.3; SPEC-social §1.2, §4.1, §12). The event calendar and the events'
// values, on the rewind-safe world clock (`SocialTime`): days start at 07:00 UTC, weeks on Monday 07:00 UTC (VERIFIED 12
// countdowns, SPEC-social §1.2; D2). Which featured events run in a week is the rotation's (B1, EventRotation.swift; it
// replaces SPEC-social D3's "every event every day / week forever", which stays the plan with `rotation.enabled` off).

// MARK: - Event rules (social.json "unlocks" + "events")

/// The events' values. `unlocks` = social.json `unlocks` (SPEC-gameplay §11.3/§15 = SPEC-social D11). The rest are
/// SPEC-social §4/§12 values; their social.json layout (`events.*`, the property names below) is C3's proposal to SOC1
/// (the file is `{}` today): until SOC1 writes it, the compiled defaults apply.
public struct EventRules: Codable, Sendable, Equatable {

    public struct Calendar: Codable, Sendable, Equatable {
        /// The event-day anchor, a Monday 07:00 UTC (SPEC-social §2.1, D2, D4): game.yml social.calendar_epoch.
        public var epoch: Int64 = Int64(GameConfig.calendarEpoch)
        public var day: Int64 = 86_400
        public var week: Int64 = 604_800
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Calendar()
            epoch = try c.v(.epoch, d.epoch); day = try c.v(.day, d.day); week = try c.v(.week, d.week)
            if day <= 0 { day = d.day }
            if week <= 0 { week = d.week }
        }
    }

    public struct StreakRace: Codable, Sendable, Equatable {
        /// Coins by final rank (1-based). VERIFIED meta §5.1 (2000 / 1000 / 500 / 100 × 7; none from rank 11), SPEC-social D13.
        public var prizes: [Int] = [2000, 1000, 500, 100, 100, 100, 100, 100, 100, 100]
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = StreakRace()
            prizes = try c.v(.prizes, d.prizes)
        }
    }

    public struct Weekly: Codable, Sendable, Equatable {
        /// Podium coins. VERIFIED phone (meta §7, flows): 2000 / 1000 / 500.
        public var prizes: [Int] = [2000, 1000, 500]
        /// Score per won level. VERIFIED ("Score" = levels won this week since the contest unlocked, meta §7).
        public var pointsPerWin: Int = 1
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Weekly()
            prizes = try c.v(.prizes, d.prizes); pointsPerWin = try c.v(.pointsPerWin, d.pointsPerWin)
        }
    }

    public struct SkyJump: Codable, Sendable, Equatable {
        /// First-try wins in a row per stage: 5 / 7 VERIFIED (flows), 10 VERIFIED (phone sessions 2+3, SPEC.md §5.28).
        public var levels: [Int] = [5, 7, 10]
        /// Prize pools per stage (split among the winners): 5000 / 7000 / 10000 VERIFIED.
        public var pools: [Int] = [5000, 7000, 10000]
        /// A run lasts 24 h from joining. VERIFIED ("23h 58m" on the map right after Start).
        public var runSeconds: Int64 = 86_400
        /// A failed run can be re-joined after this. DECISION SPEC-social §4.6.
        public var retryCooldown: Int64 = 1_800
        /// Stage-1 runs per event day. DECISION SPEC-social §4.6.
        public var maxRunsPerDay: Int = 2
        /// Only first-try wins advance a run ("Pass N Levels in a row on first try"). VERIFIED text; a non-first-try win
        /// neither advances nor fails the run (DECISION).
        public var firstTryOnly: Bool = true
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = SkyJump()
            levels = try c.v(.levels, d.levels); pools = try c.v(.pools, d.pools)
            runSeconds = try c.v(.runSeconds, d.runSeconds); retryCooldown = try c.v(.retryCooldown, d.retryCooldown)
            maxRunsPerDay = try c.v(.maxRunsPerDay, d.maxRunsPerDay); firstTryOnly = try c.v(.firstTryOnly, d.firstTryOnly)
        }
        public func levels(stage: Int) -> Int { levels[Swift.max(0, Swift.min(levels.count - 1, stage - 1))] }
        public func pool(stage: Int) -> Int { pools.isEmpty ? 0 : pools[Swift.max(0, Swift.min(pools.count - 1, stage - 1))] }
        public var stages: Int { levels.count }
    }

    public struct RocketRace: Codable, Sendable, Equatable {
        /// Levels to beat per stage: 5 VERIFIED (flows), 7 / 9 DECISION (SPEC-social D14).
        public var levels: [Int] = [5, 7, 9]
        /// Stage prizes: 500 coins + ∞ 45m VERIFIED (the first offer's bubble), the others DECISION (SPEC-social D14).
        public var prizes: [Grant] = [Grant(coins: 500, unlimitedLives: 2_700), Grant(coins: 1_000, unlimitedLives: 5_400),
                                      Grant(coins: 2_000, unlimitedLives: 10_800)]
        /// "Start" grants ∞ 30m (a claim). VERIFIED flows (shots/164).
        public var joinGrant = Grant(unlimitedLives: 1_800)
        /// The join grant once per event day (DECISION: the same-day re-offer showed a plain "Start", meta §5.3).
        public var joinGrantOncePerDay: Bool = true
        /// A lost race can be re-joined after this (VERIFIED "Join" at once; SPEC-social D14: no cooldown).
        public var retryCooldown: Int64 = 0
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = RocketRace()
            levels = try c.v(.levels, d.levels); prizes = try c.v(.prizes, d.prizes)
            joinGrant = try c.v(.joinGrant, d.joinGrant); joinGrantOncePerDay = try c.v(.joinGrantOncePerDay, d.joinGrantOncePerDay)
            retryCooldown = try c.v(.retryCooldown, d.retryCooldown)
        }
        public func levels(stage: Int) -> Int { levels[Swift.max(0, Swift.min(levels.count - 1, stage - 1))] }
        public func prize(stage: Int) -> Grant { prizes.isEmpty ? Grant() : prizes[Swift.max(0, Swift.min(prizes.count - 1, stage - 1))] }
        public var stages: Int { levels.count }
    }

    /// EventID raw value → the level a player must have REACHED (`PlayerState.level`, the next level to play) for the event
    /// to appear; a won level counts for an event when its number is at least this. VERIFIED/DECISION SPEC-gameplay §11.3.
    /// The win-streak multiplier rides on the Streak Race's unlock (DECISION: the chips first appear with it).
    public var unlocks: [String: Int] = ["streakRace": 30, "clawChallenge": 33, "skyJump": 40, "weeklyContest": 50, "rocketRace": 55]
    public var calendar = Calendar()
    public var streakRace = StreakRace()
    public var weekly = Weekly()
    public var skyJump = SkyJump()
    public var rocketRace = RocketRace()
    /// B1 (PUBLISH item 14, ruling 38; events.md §4, §8.1): the weekly rotation of the featured events (EventRotation.swift).
    /// Compiled default OFF = the v552 plan (every unlocked event every week, Up & Away never); the shipped social.json
    /// turns it on, and the app turns it off again under -pc.uitest / -pc.capture unless a rotation scenario asks.
    public var rotation = Rotation()
    /// B1: Up & Away (EventID "balloonRise", the v582 rules of build/p/PH0/balloon.md; BalloonRise.swift).
    public var balloonRise = BalloonRise()

    public init() {}
    public static let `default` = EventRules()

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); let d = EventRules()
        unlocks = d.unlocks.merging(try c.v(.unlocks, [String: Int]())) { $1 }
        calendar = try c.v(.calendar, d.calendar)
        streakRace = try c.v(.streakRace, d.streakRace)
        weekly = try c.v(.weekly, d.weekly)
        skyJump = try c.v(.skyJump, d.skyJump)
        rocketRace = try c.v(.rocketRace, d.rocketRace)
        rotation = try c.v(.rotation, d.rotation)
        balloonRise = try c.v(.balloonRise, d.balloonRise)
    }

    /// The level an event appears at (nil: an id with no unlock entry never appears). Up & Away without its own entry takes
    /// the Claw's (events.md §4.4 DECISION: the two ladder events share the slot and its unlock; the compiled table keeps
    /// its five v552 rows, the shipped social.json names balloonRise 33 explicitly).
    public func unlockLevel(_ e: EventID) -> Int? {
        if let u = unlocks[e.rawValue] { return u }
        return e == .balloonRise ? unlocks[EventID.clawChallenge.rawValue] : nil
    }

    /// Reads social.json: `unlocks` (SPEC-gameplay §15) merged over the defaults, then `events` (C3's layout).
    public static func load(social: Data?) -> (rules: EventRules, problems: [String]) {
        guard let social, !social.isEmpty else { return (EventRules(), []) }
        guard let o = (try? JSONSerialization.jsonObject(with: social)) as? [String: Any] else {
            return (EventRules(), ["social.json is not a JSON object: event defaults apply"])
        }
        var obj = (o["events"] as? [String: Any]) ?? [:]
        if let u = o["unlocks"] as? [String: Any] {
            var merged = (obj["unlocks"] as? [String: Any]) ?? [:]
            for (k, v) in u { merged[k] = v }
            obj["unlocks"] = merged
        }
        do {
            let data = try JSONSerialization.data(withJSONObject: obj)
            return (try JSONDecoder().decode(EventRules.self, from: data), [])
        } catch {
            return (EventRules(), ["social.json event values do not decode: \(error)"])
        }
    }
}

// MARK: - The calendar

public enum EventSchedule {
    /// floor-division that rounds toward −∞ (Swift `/` truncates toward 0; times before the epoch stay correct).
    static func floorDiv(_ a: Int64, _ b: Int64) -> Int64 { let q = a / b; return (a % b != 0 && (a < 0) != (b < 0)) ? q - 1 : q }

    /// Event day index of `t` (day 0 = the epoch's day; days start 07:00 UTC).
    public static func day(_ t: SocialTime, _ c: EventRules.Calendar = .init()) -> Int { Int(floorDiv(t.seconds - c.epoch, c.day)) }
    /// Event week index of `t` (weeks start Monday 07:00 UTC).
    public static func week(_ t: SocialTime, _ c: EventRules.Calendar = .init()) -> Int { Int(floorDiv(t.seconds - c.epoch, c.week)) }
    public static func dayStart(_ d: Int, _ c: EventRules.Calendar = .init()) -> SocialTime { SocialTime(seconds: c.epoch + Int64(d) * c.day) }
    public static func weekStart(_ w: Int, _ c: EventRules.Calendar = .init()) -> SocialTime { SocialTime(seconds: c.epoch + Int64(w) * c.week) }

    /// The running instance of a calendar event at `t`: the Streak Race of the event day, the Claw Challenge and the Weekly
    /// Contest (and Up & Away) of the event week. Rocket Race and Sky Jump instances start when the player joins (`Events.join…`):
    /// nil here.
    public static func instance(_ e: EventID, at t: SocialTime, rules r: EventRules = .init()) -> EventInstance? {
        switch e {
        case .streakRace:
            let d = day(t, r.calendar)
            return EventInstance(event: e, index: d, start: dayStart(d, r.calendar), end: dayStart(d + 1, r.calendar))
        case .clawChallenge, .weeklyContest, .balloonRise:
            let w = week(t, r.calendar)
            return EventInstance(event: e, index: w, start: weekStart(w, r.calendar), end: weekStart(w + 1, r.calendar))
        default:
            return nil
        }
    }

    /// The instance of a calendar event with this index (day or week).
    public static func instance(_ e: EventID, index i: Int, rules r: EventRules = .init()) -> EventInstance? {
        switch e {
        case .streakRace:
            return EventInstance(event: e, index: i, start: dayStart(i, r.calendar), end: dayStart(i + 1, r.calendar))
        case .clawChallenge, .weeklyContest, .balloonRise:
            return EventInstance(event: e, index: i, start: weekStart(i, r.calendar), end: weekStart(i + 1, r.calendar))
        default:
            return nil
        }
    }

    /// The event is visible for a player who has reached `level` (PlayerState.level, the next level to play).
    public static func isUnlocked(_ e: EventID, level: Int, rules r: EventRules = .init()) -> Bool {
        guard let u = r.unlockLevel(e) else { return false }
        return level >= u
    }

    /// A won level counts for the event (its number is at least the unlock level: the Claw's first-open screen follows the
    /// L32 win, which scores nothing; the L33 win scores — VERIFIED levels.md bar "0/1" → step 1).
    public static func counts(_ e: EventID, wonLevel: Int, rules r: EventRules = .init()) -> Bool {
        isUnlocked(e, level: wonLevel, rules: r)
    }
}
