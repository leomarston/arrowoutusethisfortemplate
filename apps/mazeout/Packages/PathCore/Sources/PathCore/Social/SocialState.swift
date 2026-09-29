import Foundation

// SOC1 (SPEC-architecture §4.11, §4.12; SPEC-social §6). The player's OWN side of the world — the only social data that
// is stored. Everything about other players is derived. Additive-only evolution: every field decodes with a default
// (decodeIfPresent), so an old save always loads (§4.12). Keep `SocialState` Codable + Sendable + Equatable with `init()`,
// and `LedgerEntry` Codable + Sendable (◆ PlayerStanding carries it).
//
// The ledger is how the player's facts reach the ◆ SocialWorld calls (PlayerStanding.ledger):
//   .win         at = the win, level = the level won, score = the Streak Race points of the win (the chip lit before it)
//   .fail        at = the failed level's end (the multiplier reset), level = that level
//   .weeklyJoin  at = the moment the week's group formed (first Weekly tab open or first win of the week at L50+),
//                instance = the week index, ref + windows = the pace reference and play windows FROZEN at the join
//   .streakJoin  the same for the event day's Streak Race (instance = the event-day index)
// Join markers freeze a group forever: its members are recomputed from (install seed, instance, t0, ref, windows).

public enum LedgerKind: String, Codable, Sendable, Equatable {
    case win, fail, weeklyJoin, streakJoin
}

/// One timestamped fact about the player's play (a win, a fail, a group join).
public struct LedgerEntry: Codable, Sendable, Equatable, Hashable {
    public var at: SocialTime
    public var level: Int
    public var score: Int
    public var kind: LedgerKind = .win
    public var firstTry: Bool = true
    public var instance: Int? = nil
    public var ref: Double? = nil
    public var windows: [[Double]]? = nil

    public init(at: SocialTime, level: Int, score: Int) { self.at = at; self.level = level; self.score = score }

    public init(at: SocialTime, level: Int, score: Int, kind: LedgerKind, firstTry: Bool = true, instance: Int? = nil,
                ref: Double? = nil, windows: [[Double]]? = nil) {
        self.at = at; self.level = level; self.score = score; self.kind = kind; self.firstTry = firstTry
        self.instance = instance; self.ref = ref; self.windows = windows
    }

    enum CodingKeys: String, CodingKey { case at, level, score, kind, firstTry, instance, ref, windows }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        at = try c.decode(SocialTime.self, forKey: .at)
        level = try c.decodeIfPresent(Int.self, forKey: .level) ?? 0
        score = try c.decodeIfPresent(Int.self, forKey: .score) ?? 0
        kind = (try? c.decodeIfPresent(LedgerKind.self, forKey: .kind)) ?? .win
        firstTry = try c.decodeIfPresent(Bool.self, forKey: .firstTry) ?? true
        instance = try c.decodeIfPresent(Int.self, forKey: .instance)
        ref = try c.decodeIfPresent(Double.self, forKey: .ref)
        windows = try c.decodeIfPresent([[Double]].self, forKey: .windows)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(at, forKey: .at)
        try c.encode(level, forKey: .level)
        try c.encode(score, forKey: .score)
        if kind != .win { try c.encode(kind, forKey: .kind) }
        if !firstTry { try c.encode(firstTry, forKey: .firstTry) }
        try c.encodeIfPresent(instance, forKey: .instance)
        try c.encodeIfPresent(ref, forKey: .ref)
        try c.encodeIfPresent(windows, forKey: .windows)
    }
}

/// The player's own side of the world: name, avatar, country, the clock's high-water mark, the ledger (capped).
public struct SocialState: Codable, Sendable, Equatable {
    public var username: String?             // nil until chosen (display: SocialNames.userDefaultName(installSeed:))
    public var avatar = 0                    // 0 = the default silhouette
    public var country: String?              // ISO 3166 alpha-2 frozen at first launch (the device region); nil = unset
    public var highWater: Int64 = 0          // SocialClock: the latest effective time ever shown
    public var ledger: [LedgerEntry] = []
    // additive (SOC1)
    public var offsetMinutes: Int?           // the device's UTC offset at first launch (the LOCAL partition's rhythm)
    public var winsByDay: [Int: Int] = [:]   // wins per event day (last 16 days) — pace survives the ledger cap
    public var winsByWeek: [Int: Int] = [:]  // wins per event week (last 6 weeks)
    public var weeklyContestWins = 0         // Profile "Weekly Contest Wins"
    public var settledWeek: Int?             // last Weekly Contest settled (its prize shown)
    public var settledStreakDay: Int?        // last Streak Race settled

    /// Ledger cap (SPEC-architecture §4.12: last 400 entries + aggregates); join markers of the current and previous
    /// instance are never dropped.
    public static let ledgerCap = 400

    public init() {}

    enum CodingKeys: String, CodingKey {
        case username, avatar, country, highWater, ledger, offsetMinutes, winsByDay, winsByWeek, weeklyContestWins
        case settledWeek, settledStreakDay
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        username = try c.decodeIfPresent(String.self, forKey: .username)
        avatar = try c.decodeIfPresent(Int.self, forKey: .avatar) ?? 0
        country = try c.decodeIfPresent(String.self, forKey: .country)
        highWater = try c.decodeIfPresent(Int64.self, forKey: .highWater) ?? 0
        ledger = try c.decodeIfPresent([LedgerEntry].self, forKey: .ledger) ?? []
        offsetMinutes = try c.decodeIfPresent(Int.self, forKey: .offsetMinutes)
        winsByDay = try c.decodeIfPresent([Int: Int].self, forKey: .winsByDay) ?? [:]
        winsByWeek = try c.decodeIfPresent([Int: Int].self, forKey: .winsByWeek) ?? [:]
        weeklyContestWins = try c.decodeIfPresent(Int.self, forKey: .weeklyContestWins) ?? 0
        settledWeek = try c.decodeIfPresent(Int.self, forKey: .settledWeek)
        settledStreakDay = try c.decodeIfPresent(Int.self, forKey: .settledStreakDay)
    }

    // ------------------------------------------------------------------ identity

    /// The name the boards show for the player: the chosen username, else its own `player_` name.
    public func displayName(installSeed: UInt64) -> String {
        username ?? SocialNames.userDefaultName(installSeed: installSeed)
    }

    /// Freezes the home country at first launch (`Locale.current.region`, fallback US) — like an account's registration
    /// country (SPEC-social §2.3).
    public mutating func setHomeIfNeeded(region: String?, offsetMinutes: Int, fallback: String = "US") {
        if country == nil {
            let r = (region ?? "").uppercased()
            country = r.count == 2 ? r : fallback
        }
        if self.offsetMinutes == nil { self.offsetMinutes = offsetMinutes }
    }

    /// The player as the world needs them (◆ PlayerStanding).
    public func standing(installSeed: UInt64, level: Int, fallbackCountry: String = "US") -> PlayerStanding {
        PlayerStanding(name: displayName(installSeed: installSeed), avatar: avatar, country: country ?? fallbackCountry,
                       level: level, ledger: ledger)
    }

    // ------------------------------------------------------------------ recording

    /// A won level. `points` = the Streak Race points of this win (the multiplier chip lit BEFORE it, C3's streak).
    public mutating func recordWin(level: Int, firstTry: Bool, points: Int, at: SocialTime) {
        ledger.append(LedgerEntry(at: at, level: level, score: points, kind: .win, firstTry: firstTry))
        winsByDay[SocialCalendar.eventDay(Int(at.seconds)), default: 0] += 1
        winsByWeek[SocialCalendar.eventWeek(Int(at.seconds)), default: 0] += 1
        trim(now: at)
    }

    /// A failed level (the fail chain ended in "Level Failed" or Quit): the multiplier reset.
    public mutating func recordFail(level: Int, at: SocialTime) {
        ledger.append(LedgerEntry(at: at, level: level, score: 0, kind: .fail))
        trim(now: at)
    }

    /// The week's Weekly Contest group forms (idempotent: the first join of a week wins).
    @discardableResult
    public mutating func joinWeekly(week: Int, level: Int, at: SocialTime) -> SocialGroupKey {
        if let k = weeklyKey(week: week) { return k }
        let t = Double(at.seconds)
        let key = SocialGroupKey(instance: week, t0: t, ref: pace(at: t).weekly, windows: playWindows(before: t))
        ledger.append(LedgerEntry(at: at, level: level, score: 0, kind: .weeklyJoin, instance: week, ref: key.ref,
                                  windows: key.windows))
        trim(now: at)
        return key
    }

    /// The event day's Streak Race group forms (idempotent).
    @discardableResult
    public mutating func joinStreak(day: Int, level: Int, at: SocialTime) -> SocialGroupKey {
        if let k = streakKey(day: day) { return k }
        let t = Double(at.seconds)
        let key = SocialGroupKey(instance: day, t0: t, ref: pace(at: t).daily, windows: playWindows(before: t))
        ledger.append(LedgerEntry(at: at, level: level, score: 0, kind: .streakJoin, instance: day, ref: key.ref,
                                  windows: key.windows))
        trim(now: at)
        return key
    }

    public func weeklyKey(week: Int) -> SocialGroupKey? { Self.groupKey(in: ledger, kind: .weeklyJoin, instance: week) }
    public func streakKey(day: Int) -> SocialGroupKey? { Self.groupKey(in: ledger, kind: .streakJoin, instance: day) }

    static func groupKey(in ledger: [LedgerEntry], kind: LedgerKind, instance: Int) -> SocialGroupKey? {
        guard let e = ledger.first(where: { $0.kind == kind && $0.instance == instance }) else { return nil }
        return SocialGroupKey(instance: instance, t0: Double(e.at.seconds), ref: e.ref ?? 0, windows: e.windows ?? [])
    }

    // ------------------------------------------------------------------ pace (SocialPace from the aggregates)

    /// The player's pace at t: the reference's user_pace, fed by the per-day / per-week aggregates (they survive the
    /// ledger cap) and the recent wins (seconds per win).
    public func pace(at t: Double) -> SocialPace {
        let today = SocialCalendar.eventDay(t)
        // per day / week: the larger of the aggregate and the ledger's own count (C3 may append wins to the ledger
        // directly, without the aggregates; the aggregates keep what the cap dropped)
        var byDay = winsByDay, byWeek = winsByWeek
        var ledDay: [Int: Int] = [:], ledWeek: [Int: Int] = [:]
        for e in ledger where e.kind == .win && Double(e.at.seconds) <= t {
            ledDay[SocialCalendar.eventDay(Int(e.at.seconds)), default: 0] += 1
            ledWeek[SocialCalendar.eventWeek(Int(e.at.seconds)), default: 0] += 1
        }
        byDay.merge(ledDay) { max($0, $1) }
        byWeek.merge(ledWeek) { max($0, $1) }
        let dayCounts = byDay.filter { $0.key > today - 14 && $0.key <= today }.map(\.value).sorted()
        let daily = dayCounts.isEmpty ? 15.0 : Double(dayCounts[dayCounts.count / 2])
        let wins = ledger.filter { $0.kind == .win && Double($0.at.seconds) <= t && Double($0.at.seconds) >= t - 14 * 86_400 }
        var gaps: [Double] = []
        if wins.count > 1 {
            for i in 1..<wins.count {
                let g = Double(wins[i].at.seconds - wins[i - 1].at.seconds)
                if g >= 20 && g <= 900 { gaps.append(g) }
            }
        }
        gaps.sort()
        let spw = gaps.isEmpty ? 120.0 : gaps[gaps.count / 2]
        let cur = SocialCalendar.eventWeek(t)
        let past = byWeek.filter { cur - 4 <= $0.key && $0.key < cur }.map(\.value).sorted()
        let weekly = past.isEmpty ? daily * 5.0 : Double(past[past.count / 2])
        return SocialPace(daily: daily, secondsPerWin: min(max(spw, 45.0), 600.0), weekly: weekly)
    }

    /// The player's last play windows before t, derived from the wins: consecutive wins less than 20 minutes apart
    /// form one session [first win − 2 min, last win].
    public func playWindows(before t: Double, count: Int = 3) -> [[Double]] {
        let wins = ledger.filter { $0.kind == .win && Double($0.at.seconds) < t }.map { Double($0.at.seconds) }
        var out: [[Double]] = []
        var start: Double? = nil, last = 0.0
        for w in wins {
            if let s = start, w - last <= 1200 { _ = s; last = w; continue }
            if let s = start { out.append([s - 120, last]) }
            start = w; last = w
        }
        if let s = start { out.append([s - 120, last]) }
        return Array(out.suffix(count))
    }

    // ------------------------------------------------------------------ the cap

    mutating func trim(now: SocialTime) {
        let t = Int(now.seconds)
        let day = SocialCalendar.eventDay(t), week = SocialCalendar.eventWeek(t)
        winsByDay = winsByDay.filter { $0.key > day - 16 }
        winsByWeek = winsByWeek.filter { $0.key > week - 6 }
        guard ledger.count > Self.ledgerCap else { return }
        func keep(_ e: LedgerEntry) -> Bool {
            switch e.kind {
            case .weeklyJoin: return (e.instance ?? .min) >= week - 1
            case .streakJoin: return (e.instance ?? .min) >= day - 1
            default: return false
            }
        }
        var excess = ledger.count - Self.ledgerCap
        var out: [LedgerEntry] = []
        out.reserveCapacity(Self.ledgerCap)
        for e in ledger {
            if excess > 0 && !keep(e) { excess -= 1; continue }
            out.append(e)
        }
        ledger = out
    }
}
