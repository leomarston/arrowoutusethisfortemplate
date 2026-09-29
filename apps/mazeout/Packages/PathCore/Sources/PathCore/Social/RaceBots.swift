import Foundation

// SOC1 (SPEC-social §4; reference design/social/tools/socialsim/events.py, bit for bit).
// The opponents of the Weekly Contest, Streak Race, Rocket Race and Sky Jump are members of the shared World: identity
// (name, avatar, country) from the World, event progress = their World levels won after the event starts, so an
// opponent asleep in its own timezone does not move. Everything is re-derivable from the install seed + the event
// instance id + the user's own stored facts (t0, pace reference, play windows). Nothing about opponents is stored.
// Type names carry a `Social` prefix: C3 owns the event STATE MACHINES (Events/*: Streak, StreakRace, RocketRace …).

/// The win-streak multiplier (x1 x5 x10 x25 x100) shared by the Streak Race, the Claw Challenge and the fail flow.
/// A win scores STEPS[step] points and then advances the step; a failed level resets to x1 (events.Streak).
public struct SocialWinStreak: Sendable, Equatable, Codable {
    public static let steps = [1, 5, 10, 25, 100]
    public var step: Int
    public init(step: Int = 0) { self.step = step }
    public mutating func win() -> Int {
        let pts = Self.steps[max(0, min(step, 4))]
        if step < 4 { step += 1 }
        return pts
    }
    public mutating func fail() { step = 0 }
}

/// The user's pace from its win history (events.user_pace): daily levels on active days (median of the last 14 days),
/// median seconds per win in play, weekly levels (median of the last 4 completed weeks).
public struct SocialPace: Sendable, Equatable {
    public var daily: Double, secondsPerWin: Double, weekly: Double

    /// `wins` = (time, level, firstTry), in time order.
    public static func of(wins: [(t: Double, level: Int, firstTry: Bool)], at t: Double, defaultDaily: Double = 15.0) -> SocialPace {
        let recent = wins.filter { t - 14.0 * Double(SocialCalendar.day) <= $0.t && $0.t <= t }
        var days: [Int: Int] = [:]
        for w in recent { days[SocialCalendar.eventDay(w.t), default: 0] += 1 }
        let daily = days.values.sorted()
        let dailyRef = daily.isEmpty ? defaultDaily : Double(daily[daily.count / 2])
        var gaps: [Double] = []
        if recent.count > 1 {
            for i in 1..<recent.count {
                let g = recent[i].t - recent[i - 1].t
                if g >= 20 && g <= 900 { gaps.append(g) }
            }
        }
        gaps.sort()
        let spw = gaps.isEmpty ? 120.0 : gaps[gaps.count / 2]
        var weeks: [Int: Int] = [:]
        for w in wins where w.t <= t { weeks[SocialCalendar.eventWeek(w.t), default: 0] += 1 }
        let cur = SocialCalendar.eventWeek(t)
        let past = weeks.filter { cur - 4 <= $0.key && $0.key < cur }.map(\.value).sorted()
        let weeklyRef = past.isEmpty ? dailyRef * 5.0 : Double(past[past.count / 2])
        return SocialPace(daily: dailyRef, secondsPerWin: min(max(spw, 45.0), 600.0), weekly: weeklyRef)
    }
}

// ------------------------------------------------------------------------------------------------ matchmaking

extension SocialPopulation {
    /// Deterministic rejection sampling of distinct World members joined by t (events.sample_members).
    func sampleMembers(_ t: Double, _ keySeed: UInt64, _ label: Label, _ count: Int, maxTries: Int = 6000,
                       accept: (SocialCohort, Int, Int) -> Bool) -> [(SocialCohort, Int)] {
        var out: [(SocialCohort, Int)] = []
        var seen = Set<Int>()
        let total = gidLimit(t)
        if total <= 0 { return out }
        for a in 0..<maxTries {
            let g = SocialHash.below(keySeed, label, total, a)
            if seen.contains(g) { continue }
            guard let (c, j) = find(g) else { continue }
            if accept(c, j, a) {
                seen.insert(g)
                out.append((c, j))
                if out.count == count { break }
            }
        }
        return out
    }

    /// Expected levels per calendar day of a member at time t (full activity, lapsed phase, or 0).
    func expectedDaily(_ c: SocialCohort, _ j: Int, _ t0: Double?) -> Double {
        let mb = member(c, j)
        var t = t0
        if let tt = t0, lagMin != 0 { t = tt - lag(c, j) }            // v2 M10: the member's own clock
        let full = mb.lam * c.arch.rho
        if let hE = c.hE, let t = t, mb.J <= t && t < hE && t < mb.T1 { return full * (1.0 + c.hb) }   // the honeymoon rate
        guard let t = t else { return full }
        if mb.J <= t && t < mb.T1 { return full }
        if let T2 = mb.T2, let R = c.R, R <= t && t < T2 { return full }
        if mb.T1 <= t && t < lapseEnd(c, mb.u, mb.T1) {
            return full * SocialWorldModel.lapseDayP * SocialWorldModel.lapseVolume
        }
        return 0.0
    }

    /// Joined and either active or in the lapsed phase (may still come back this week).
    func playingAt(_ c: SocialCohort, _ j: Int, _ t: Double) -> Bool {
        expectedDaily(c, j, t) > 0.0 && member(c, j).J <= t - lag(c, j)
    }

    func activeAt(_ c: SocialCohort, _ j: Int, _ t0: Double) -> Bool {
        let mb = member(c, j)
        let t = t0 - lag(c, j)
        if t < mb.J { return false }
        if t < mb.T1 { return true }
        if let T2 = mb.T2, let R = c.R { return R <= t && t < T2 }
        return false
    }

    /// Earliest time in [tLo, tHi] with level >= target (nil if not reached by tHi); bisection to 1 s.
    func firstTimeReaching(_ c: SocialCohort, _ j: Int, _ target: Int, _ tLo: Double, _ tHi: Double) -> Double? {
        if level(c, j, tHi) < target { return nil }
        if level(c, j, tLo) >= target { return tLo }
        var lo = tLo, hi = tHi
        while hi - lo > 1.0 {
            let mid = (lo + hi) / 2.0
            if level(c, j, mid) >= target { hi = mid } else { lo = mid }
        }
        return hi
    }
}

// ------------------------------------------------------------------------------------------------ group contests

/// One matchmaking band: `count` members whose expected pace / the user's reference is in [lo, hi]; `sameHours` prefers
/// players who were playing during the user's last 3 sessions (visible live duels).
public struct SocialBand: Sendable, Equatable, Codable {
    public var count: Int, lo: Double, hi: Double, sameHours: Bool
    public init(_ count: Int, _ lo: Double, _ hi: Double, _ sameHours: Bool) {
        self.count = count; self.lo = lo; self.hi = hi; self.sameHours = sameHours
    }
}

/// How a group contest forms and fills (GroupContest's parameters).
public struct SocialGroupSpec: Sendable, Equatable {
    public enum Kind: String, Sendable, Codable { case weekly, streak }
    public enum Early: Sendable, Equatable {
        case hashed                     // 6 + below(7) members arrive early (the reference Weekly)
        case fraction(Double)           // floor(n·share + u01) early (1.0 = everyone is already there)
        case elapsedDay                 // share = the elapsed fraction of the event day (the reference Streak Race)
    }
    public var kind: Kind
    public var bands: [SocialBand]
    public var minLevel: Int
    public var minTarget: Double        // the reference pace never goes below this (levels per week / per day)
    public var earlyHours: Double
    public var early: Early
    public var lastArrivalBeforeEnd: Double   // seconds before the window end after which nobody arrives
    public var prizes: [Int]
    /// When set, the `sameHours` preference matches players who play in [t0 − before, t0 + after] (online around the
    /// join, like a server grouping players who enter at the same moment) instead of during the player's last sessions.
    public var matchWindow: (before: Double, after: Double)? = nil
    /// When true, `sameHours` matches players who play during the contest's own window (the event day): a daily race is
    /// made of people who open the game that day. Takes precedence over `matchWindow`.
    public var matchEventWindow = false
    /// When true, a member arrives no later than its first win in the contest window (it joins the race when it plays),
    /// so a member who played before its drawn arrival still scores that play.
    public var arriveByFirstPlay = false
    /// When true, a member's pace for the bands is its levels per PLAYED day (expected daily / ρ), the same unit as the
    /// player's reference (median wins per active day); the reference compared per-active-day with per-calendar-day.
    public var expectedPerPlayDay = false
    /// When true, every member arrives at the join with 0 points (phone session 2: the Streak Race the player joins
    /// starts with all 49 rivals at 0). Takes precedence over `early` / `arriveByFirstPlay`.
    public var arriveAtJoin = false
    /// When true, equal scores are listed by the name's case- and accent-insensitive key (phone session 2: the Streak
    /// Race lists ties alphabetically); else by the moment the score was reached (the Weekly: earlier first).
    public var tieByName = false
    /// Streak Race: a member's chance to fail before each win = lo + span × u01 (events.StreakRace.FAIL_Q).
    public var failQ: (lo: Double, span: Double) = (0.06, 0.24)

    public static func == (a: SocialGroupSpec, b: SocialGroupSpec) -> Bool {
        a.kind == b.kind && a.bands == b.bands && a.minLevel == b.minLevel && a.minTarget == b.minTarget
            && a.earlyHours == b.earlyHours && a.early == b.early && a.lastArrivalBeforeEnd == b.lastArrivalBeforeEnd
            && a.prizes == b.prizes && a.matchWindow?.before == b.matchWindow?.before && a.matchWindow?.after == b.matchWindow?.after
            && a.matchEventWindow == b.matchEventWindow && a.arriveByFirstPlay == b.arriveByFirstPlay
            && a.expectedPerPlayDay == b.expectedPerPlayDay && a.arriveAtJoin == b.arriveAtJoin && a.tieByName == b.tieByName
            && a.failQ == b.failQ
    }

    public var groupSize: Int { 1 + bands.reduce(0) { $0 + $1.count } }

    /// events.WeeklyContest: 50 players, arrivals over the first day or two.
    public static let referenceWeekly = SocialGroupSpec(
        kind: .weekly,
        bands: [SocialBand(1, 1.05, 1.70, false), SocialBand(5, 0.92, 1.18, true), SocialBand(8, 0.70, 0.92, true),
                SocialBand(12, 0.45, 0.70, false), SocialBand(13, 0.20, 0.45, false), SocialBand(10, 0.04, 0.20, false)],
        minLevel: 50, minTarget: 35.0, earlyHours: 6.0, early: .hashed, lastArrivalBeforeEnd: 12 * 3600,
        prizes: [2000, 1000, 500])

    /// events.StreakRace: 20 players.
    public static let referenceStreak = SocialGroupSpec(
        kind: .streak,
        bands: [SocialBand(2, 1.15, 2.00, false), SocialBand(4, 0.90, 1.15, true), SocialBand(5, 0.60, 0.90, true),
                SocialBand(5, 0.30, 0.60, false), SocialBand(3, 0.08, 0.30, false)],
        minLevel: 30, minTarget: 8.0, earlyHours: 24.0, early: .elapsedDay, lastArrivalBeforeEnd: 2 * 3600,
        prizes: [2000, 1000, 500, 100, 100, 100, 100, 100, 100, 100])

    /// SHIPPED Weekly Contest (phone v552, research/meta.md §7 + phone-meta-progress 06:39): a 10-PLAYER group that is
    /// complete the moment the user joins (at the join the list ended at the user, rank 10, score 0; ranks 7-9 had
    /// 1, 1, 0; podium 4, 4, 3) — so every member arrived within the quarter hour before the user — and whose rivals
    /// were ONLINE. Bands keep the reference's shape scaled to 9 members (phone session 2: the rivals ran at ~[2.3 1.4 .85
    /// .82 .68 .68 .56 .18 .12] × the player's own progress); SOC1b: the two idle members are online at the join too
    /// (Boo +6 and Mema +4 in the first 85 min, then nothing all day). All match players around the join (−30 … +90 min).
    public static let shippedWeekly = SocialGroupSpec(
        kind: .weekly,
        bands: [SocialBand(1, 1.10, 1.80, true), SocialBand(2, 0.90, 1.20, true), SocialBand(2, 0.65, 0.90, true),
                SocialBand(2, 0.40, 0.65, true), SocialBand(2, 0.08, 0.40, true)],
        minLevel: 50, minTarget: 35.0, earlyHours: 0.25, early: .fraction(1.0), lastArrivalBeforeEnd: 12 * 3600,
        prizes: [2000, 1000, 500], matchWindow: (before: 1800, after: 5400))

    /// SHIPPED Streak Race (phone v552): a 50-ROW ranking, prizes 2000/1000/500/100×7 (ranks 1-10). Phone session 2 §D:
    /// the race the player joins starts with every rival at 0, listed alphabetically; ~2/3 of them score within the first
    /// hour (17 still at 0 at +69 min, 11 at +4 h) and equal scores stay listed alphabetically. Members = players who win
    /// a level within 2 h after the join (+ 8 idle ones); their pace per PLAYED day against the player's wins per active
    /// day (floored at 4). The phone's leaders ran long unbroken x100 streaks: a heavier top band and a 2-12 % fail chance
    /// per win (reference 6-30 %).
    public static let shippedStreak = SocialGroupSpec(
        kind: .streak,
        bands: [SocialBand(5, 1.20, 2.20, true), SocialBand(10, 0.75, 1.20, true), SocialBand(14, 0.40, 0.75, true),
                SocialBand(12, 0.10, 0.40, true), SocialBand(8, 0.02, 0.10, false)],
        minLevel: 30, minTarget: 4.0, earlyHours: 24.0, early: .elapsedDay, lastArrivalBeforeEnd: 12 * 3600,
        prizes: [2000, 1000, 500, 100, 100, 100, 100, 100, 100, 100], matchWindow: (before: 0, after: 7200),
        expectedPerPlayDay: true, arriveAtJoin: true, tieByName: true, failQ: (0.02, 0.10))
}

/// What fixes a group forever: the event instance, the moment the user joined, the user's pace reference and its last
/// play windows at that moment (stored by the app; SPEC-social §6).
public struct SocialGroupKey: Sendable, Equatable, Hashable, Codable {
    public var instance: Int              // week index (Weekly) or event-day index (Streak Race)
    public var t0: Double                 // the user's join moment
    public var ref: Double                // the user's reference pace at the join (weekly or daily levels)
    public var windows: [[Double]]        // the user's last play windows before the join ([start, end])
    public init(instance: Int, t0: Double, ref: Double, windows: [[Double]] = []) {
        self.instance = instance; self.t0 = t0; self.ref = ref; self.windows = windows
    }
}

/// One row of a group standing: a member (index into `members`) or the user (member == nil).
public struct SocialStandingRow: Sendable, Equatable {
    public var member: Int?
    public var score: Int
    public var reached: Double
}

/// A group contest instance (GroupContest + WeeklyContest / StreakRace of the reference).
final class SocialGroupContest: @unchecked Sendable {
    let W: SocialPopulation
    let spec: SocialGroupSpec
    let key: SocialGroupKey
    let S: UInt64
    let t0: Double, ws: Double, we: Double, ref: Double
    var members: [(SocialCohort, Int)] = []
    var arrive: [Double] = []
    var base: [Int] = []
    // Streak Race
    var s0: [Int] = []
    var q: [Double] = []
    private var ptsCache: [[Int]] = []      // cumulative points after k wins, per member (pure function; lazily extended)
    private let cacheLock = NSLock()

    init(W: SocialPopulation, installSeed: UInt64, spec: SocialGroupSpec, key: SocialGroupKey) {
        typealias H = SocialHash
        self.W = W; self.spec = spec; self.key = key
        let kindLabel = spec.kind == .weekly ? SocialLabels.weekly : SocialLabels.streak
        S = H.h64(installSeed, kindLabel, key.instance)
        t0 = key.t0
        if spec.kind == .weekly {
            ws = Double(SocialCalendar.eventWeekStart(key.instance)); we = ws + Double(SocialCalendar.week)
        } else {
            ws = Double(SocialCalendar.eventDayStart(key.instance)); we = ws + Double(SocialCalendar.day)
        }
        ref = max(spec.minTarget, key.ref)
        W.extend(to: max(t0, we) + 2 * 86_400)
        var taken = Set<Int>()
        var slot = 0
        let windows: [[Double]] = spec.matchEventWindow ? [[ws, we]]
            : spec.matchWindow.map { [[key.t0 - $0.before, key.t0 + $0.after]] } ?? Array(key.windows.suffix(3))
        let t0 = self.t0, ref = self.ref, minLevel = spec.minLevel, weekly = spec.kind == .weekly
        let perPlayDay = spec.expectedPerPlayDay
        func expected(_ c: SocialCohort, _ j: Int) -> Double {
            if perPlayDay { return W.expectedDaily(c, j, t0) / c.arch.rho }
            return weekly ? W.expectedDaily(c, j, t0) * 7.0 : W.expectedDaily(c, j, t0)
        }
        for band in spec.bands {
            for _ in 0..<band.count {
                var got = W.sampleMembers(t0, S, SocialLabels.cand(slot), 1) { c, j, a in
                    if taken.contains(W.gid(c, j)) || !W.playingAt(c, j, t0) || W.level(c, j, t0) < minLevel { return false }
                    let r = expected(c, j) / ref
                    if r < band.lo || r > band.hi { return false }
                    if band.sameHours && !windows.isEmpty && a < 1500 {
                        // prefer players who were playing while the user was (same hours = visible live duels)
                        return windows.contains { w in W.level(c, j, w[1]) > W.level(c, j, w[0]) }
                    }
                    return true
                }
                if got.isEmpty {
                    got = W.sampleMembers(t0, S, SocialLabels.any(slot), 1) { c, j, _ in
                        !taken.contains(W.gid(c, j)) && W.playingAt(c, j, t0) && W.level(c, j, t0) >= minLevel
                    }
                }
                if let g = got.first { members.append(g); taken.insert(W.gid(g.0, g.1)) }
                slot += 1
            }
        }
        // arrivals
        var order = Array(members.indices)
        order.sort { H.h64(S, SocialLabels.order, $0) < H.h64(S, SocialLabels.order, $1) }
        let nEarly: Int
        switch spec.early {
        case .hashed: nEarly = 6 + H.below(S, SocialLabels.early, 7)
        case .fraction(let share): nEarly = H.floorInt(Double(members.count) * share + H.u01(S, SocialLabels.early))
        case .elapsedDay:
            let share = min(1.0, max(0.0, (t0 - ws) / Double(SocialCalendar.day)))
            nEarly = H.floorInt(Double(members.count) * share + H.u01(S, SocialLabels.early))
        }
        arrive = [Double](repeating: 0, count: members.count)
        let lo = max(ws, t0 - spec.earlyHours * 3600)
        let last = max(t0, we - spec.lastArrivalBeforeEnd)
        for (rankI, i) in order.enumerated() {
            if rankI < nEarly {
                arrive[i] = lo + (t0 - lo) * H.u01(S, SocialLabels.arrE, i)
            } else {
                let x = H.u01(S, SocialLabels.arrL, i)
                arrive[i] = t0 + (last - t0) * x * x
            }
        }
        if spec.arriveAtJoin {
            for i in members.indices { arrive[i] = t0 }        // everyone starts at 0 with the player
        } else if spec.arriveByFirstPlay {
            for i in members.indices {
                let (c, j) = members[i]
                if let f = W.firstTimeReaching(c, j, W.level(c, j, ws) + 1, ws, we), f - 1.0 < arrive[i] {
                    arrive[i] = max(ws, f - 1.0)
                }
            }
        }
        base = members.indices.map { W.level(members[$0].0, members[$0].1, arrive[$0]) }
        if spec.kind == .streak {
            for i in members.indices {
                let x = H.u01(S, SocialLabels.s0, i)
                s0.append(x < 0.5 ? 0 : x < 0.7 ? 1 : x < 0.82 ? 2 : x < 0.9 ? 3 : 4)
                q.append(spec.failQ.lo + spec.failQ.span * H.u01(S, SocialLabels.q, i))
            }
            ptsCache = members.indices.map { _ in [0] }
        }
    }

    /// Member i's score at t; nil before it arrived.
    func memberScore(_ i: Int, _ t: Double) -> Int? {
        if t < arrive[i] { return nil }
        let (c, j) = members[i]
        let n = max(0, W.level(c, j, min(t, we)) - base[i])
        if spec.kind == .weekly { return n }
        return streakPoints(i, n)
    }

    /// Points after n wins of member i: each win adds the chip lit before it; a fail (own probability) resets to x1.
    func streakPoints(_ i: Int, _ n: Int) -> Int {
        cacheLock.lock(); defer { cacheLock.unlock() }
        var cum = ptsCache[i]
        if cum.count <= n {
            // replay from the start (the step is not cached; cheap and exact)
            var s = s0[i]
            var pts = 0
            cum = [0]
            for k in 0..<n {
                if SocialHash.u01(S, SocialLabels.fail, i, k) < q[i] { s = 0 }
                pts += SocialWinStreak.steps[s]
                if s < 4 { s += 1 }
                cum.append(pts)
            }
            ptsCache[i] = cum
        }
        return cum[n]
    }

    /// The moment member i reached its current score (bisection on the monotone score).
    func reached(_ i: Int, _ t: Double) -> Double {
        guard let s = memberScore(i, t) else { return arrive[i] }
        var lo = arrive[i]
        if s == 0 { return lo }
        var hi = min(t, we)
        while hi - lo > 1.0 {
            let mid = (lo + hi) / 2.0
            if (memberScore(i, mid) ?? 0) >= s { hi = mid } else { lo = mid }
        }
        return hi
    }

    /// Standings at t: score ↓, then the moment it was reached ↑ (the user, who just joined, sits last among its
    /// equals only through its later reach moment; exact ties put the user first, as the reference's tuple sort).
    /// With `spec.tieByName` and the user's name, equal scores are ordered by the name's case- and accent-insensitive key
    /// (code-point order, = Python's str order), then the reach moment, then the index (events.standings_by_name).
    func standings(_ t: Double, userScore: Int, userReached: Double, userName: String? = nil) -> [SocialStandingRow] {
        if spec.tieByName, let un = userName {
            var rows: [(Int, [UInt32], Double, Int)] = []
            for i in members.indices {
                guard let s = memberScore(i, t) else { continue }
                rows.append((-s, Self.sortKey(W.name(members[i].0, members[i].1).name), reached(i, t), i))
            }
            rows.append((-userScore, Self.sortKey(un), userReached, -1))
            rows.sort { a, b in
                if a.0 != b.0 { return a.0 < b.0 }
                if a.1 != b.1 { return a.1.lexicographicallyPrecedes(b.1) }
                return a.2 != b.2 ? a.2 < b.2 : a.3 < b.3
            }
            return rows.map { SocialStandingRow(member: $0.3 < 0 ? nil : $0.3, score: -$0.0, reached: $0.2) }
        }
        var rows: [(Int, Double, Int)] = []
        for i in members.indices {
            guard let s = memberScore(i, t) else { continue }
            rows.append((-s, reached(i, t), i))
        }
        rows.append((-userScore, userReached, -1))
        rows.sort { a, b in a.0 != b.0 ? a.0 < b.0 : (a.1 != b.1 ? a.1 < b.1 : a.2 < b.2) }
        return rows.map { SocialStandingRow(member: $0.2 < 0 ? nil : $0.2, score: -$0.0, reached: $0.1) }
    }

    /// data.key(name) as Unicode scalar values (Python compares str by code point).
    static func sortKey(_ name: String) -> [UInt32] { SocialNames.key(name).unicodeScalars.map(\.value) }
}

// ------------------------------------------------------------------------------------------------ Rocket Race

public struct SocialRocketSpec: Sendable, Equatable {
    public var levels: [Int]                       // N per stage
    public var holdMinutes: (lo: Double, hi: Double)
    public var delta: (lo: Double, hi: Double)     // × the user's median seconds per win
    public var prizes: [(coins: Int, infiniteMinutes: Int)]
    /// The four lanes' roles (events.RocketRace.ROLES): 'sprint' beats N levels within sprintMinutes × N/5 at its own
    /// pace, 'hot' ≥ 2 levels in 20 min, 'busy' ≥ 1, 'steady' 1-3, 'warm' none in 20 min but ≥ 2 within 150, else idle.
    public var roles: [String] = ["hot", "hot", "warm", "idle"]
    /// Hold minutes per role (nil = `holdMinutes` for every lane).
    public var holdByRole: [String: (lo: Double, hi: Double)]? = nil
    public var sprintMinutes = 15.0
    public static let reference = SocialRocketSpec(levels: [5, 7, 9], holdMinutes: (14.0, 40.0), delta: (0.45, 1.85),
                                                   prizes: [(500, 45), (1000, 90), (2000, 180)])
    /// SHIPPED (phone session 2 §E + S1): one rival finishes 5 levels 6, 8, 15-20 and 19 min after the join, the others
    /// are at [3,2,1], [3,1,1], [4,3,1] then, and the (slow) player lost all four: a sprinter held until 6-19 min.
    public static let shipped: SocialRocketSpec = {
        var r = reference
        r.roles = ["sprint", "hot", "steady", "steady"]
        r.holdByRole = ["sprint": (6.0, 19.0), "hot": (14.0, 40.0), "steady": (14.0, 40.0)]
        r.sprintMinutes = 15.0
        return r
    }()
    public static func == (a: SocialRocketSpec, b: SocialRocketSpec) -> Bool {
        func holds(_ x: SocialRocketSpec) -> [String] {
            (x.holdByRole ?? [:]).sorted { $0.key < $1.key }.map { "\($0.key)=\($0.value.lo),\($0.value.hi)" }
        }
        return a.levels == b.levels && a.holdMinutes == b.holdMinutes && a.delta == b.delta
            && a.prizes.map(\.coins) == b.prizes.map(\.coins) && a.prizes.map(\.infiniteMinutes) == b.prizes.map(\.infiniteMinutes)
            && a.roles == b.roles && (a.holdByRole == nil) == (b.holdByRole == nil) && holds(a) == holds(b)
            && a.sprintMinutes == b.sprintMinutes
    }
}

/// 5 lanes: the first to beat N levels after joining wins the stage. Rivals are World members in or near a session; a
/// rival that would reach N is HELD at N−1 until min(t0 + hold, userReachedNminus1 + δ) (rubber band, events.RocketRace).
final class SocialRocketRace: @unchecked Sendable {
    let W: SocialPopulation
    let t0: Double, stage: Int, N: Int, S: UInt64, end: Double
    var rivals: [(SocialCohort, Int)] = []
    var base: [Int] = []
    var hold: [Double] = []
    var delta: [Double] = []
    var natural: [Double?] = []

    init(W: SocialPopulation, installSeed: UInt64, raceId: Int, stage: Int, t0: Double, secondsPerWin: Double,
         spec: SocialRocketSpec = .reference) {
        typealias H = SocialHash
        self.W = W; self.t0 = t0; self.stage = stage
        N = spec.levels[max(0, min(stage - 1, spec.levels.count - 1))]
        S = H.h64(installSeed, SocialLabels.rocket, raceId)
        end = Double(SocialCalendar.eventDayStart(SocialCalendar.eventDay(t0) + 1))
        W.extend(to: end + 2 * 86_400)
        let roles = spec.roles
        let N = self.N
        let sprint = spec.sprintMinutes * 60.0 * Double(N) / 5.0
        for (ri, role) in roles.enumerated() {
            let chosen = rivals
            var got = W.sampleMembers(t0, S, SocialLabels.cand(ri), 1) { c, j, _ in
                if !W.activeAt(c, j, t0) { return false }
                let L0 = W.level(c, j, t0)
                let ok: Bool
                switch role {
                case "sprint": ok = W.level(c, j, t0 + sprint) - L0 >= N
                case "hot": ok = W.level(c, j, t0 + 20 * 60) - L0 >= 2
                case "busy": ok = W.level(c, j, t0 + 20 * 60) - L0 >= 1
                case "steady": let g = W.level(c, j, t0 + 20 * 60) - L0; ok = g >= 1 && g <= 3
                case "warm": ok = W.level(c, j, t0 + 20 * 60) == L0 && W.level(c, j, t0 + 150 * 60) - L0 >= 2
                default: ok = W.level(c, j, t0 + 180 * 60) == L0
                }
                return ok && !chosen.contains { $0.0 === c && $0.1 == j }
            }
            if got.isEmpty {   // fallback: any active member
                got = W.sampleMembers(t0, S, SocialLabels.any(ri), 1) { c, j, _ in W.activeAt(c, j, t0) }
            }
            if let g = got.first { rivals.append(g) }
        }
        base = rivals.map { W.level($0.0, $0.1, t0) }
        for i in 0..<rivals.count {
            let h = spec.holdByRole.flatMap { $0[roles[min(i, roles.count - 1)]] } ?? spec.holdMinutes
            hold.append(t0 + (h.lo + (h.hi - h.lo) * H.u01(S, SocialLabels.hold, i)) * 60)
            delta.append(secondsPerWin * (spec.delta.lo + (spec.delta.hi - spec.delta.lo) * H.u01(S, SocialLabels.delta, i)))
        }
        for (i, r) in rivals.enumerated() {
            natural.append(W.firstTimeReaching(r.0, r.1, base[i] + N, t0, end))
        }
    }

    /// When rival i finishes (nil = never before the day ends), given the moment the user reached N−1 (if it did).
    func finishTime(_ i: Int, userNminus1: Double?) -> Double? {
        guard let nat = natural[i] else { return nil }
        var gate = hold[i]
        if let u = userNminus1 { gate = min(gate, u + delta[i]) }
        let f = max(nat, gate)
        return f <= end ? f : nil
    }

    func rivalProgress(_ i: Int, _ t: Double, userNminus1: Double?) -> Int {
        let (c, j) = rivals[i]
        if let f = finishTime(i, userNminus1: userNminus1), t >= f { return N }
        let n = W.level(c, j, min(t, end)) - base[i]
        return max(0, min(n, N - 1))
    }

    public enum Result: String, Sendable { case win, lose, none }

    /// userTimes: sorted times of the user's wins since joining.
    func outcome(userTimes: [Double]) -> (result: Result, at: Double) {
        let nm1: Double? = userTimes.count >= N - 1 ? userTimes[N - 2] : nil
        var rivalFirst: Double? = nil
        for i in rivals.indices {
            if let f = finishTime(i, userNminus1: nm1), rivalFirst == nil || f < rivalFirst! { rivalFirst = f }
        }
        let u: Double? = userTimes.count >= N ? userTimes[N - 1] : nil
        if let u = u, u <= end, rivalFirst == nil || u < rivalFirst! { return (.win, u) }
        if let r = rivalFirst { return (.lose, r) }
        return (.none, end)
    }
}

// ------------------------------------------------------------------------------------------------ Sky Jump

public struct SocialSkySpec: Sendable, Equatable {
    public var levels: [Int]
    public var pools: [Int]
    /// Shipped survivor curve per stage (nil = the reference's proportional hazard): a per-attempt drop d in [lo, hi],
    /// each step d ± 1, from the user's step `first` on; winners in [wlo, whi] (events.SKY_DROPS).
    public struct Drops: Sendable, Equatable {
        public var lo: Double, hi: Double, first: Int, wlo: Int, whi: Int
        public init(_ lo: Double, _ hi: Double, _ first: Int, _ wlo: Int, _ whi: Int) {
            self.lo = lo; self.hi = hi; self.first = first; self.wlo = wlo; self.whi = whi
        }
    }
    public var drops: [Drops]? = nil
    public static let reference = SocialSkySpec(levels: [5, 7, 9], pools: [5000, 7000, 10000])
    /// SHIPPED (phone: stage 1 100 82 64 ? 47 → 7 winners; stage 2 100 100 88 75 62 49 36 → 15 winners share 7000;
    /// stage 3 = 10 levels / PRIZE 10000 (sessions 2 and 3): 100 100 91 83 75 66 57 48 40 32 → 7 winners, 10000/7 = 1428):
    /// 8-13 of 100 drop per level (stage 3: 8-9). SOC1c: stage 3 = 10 levels (social.json `events.skyJump.levels`, which
    /// C3's EventRules reads too), drop 7.5-9.5, winners 5-9.
    public static let shipped = SocialSkySpec(levels: [5, 7, 10], pools: [5000, 7000, 10000],
                                           drops: [Drops(10.0, 16.0, 1, 5, 10), Drops(11.0, 14.0, 2, 12, 18), Drops(7.5, 9.5, 2, 5, 9)])
}

/// 100 players; beat N levels in a row on the first try within 24 h. "Players" is a function of the USER's step (phone:
/// 100 → 82 → 64 → … → 47, then 7 winners sharing 5000 → 714).
public struct SocialSkyJump: Sendable, Equatable {
    public let N: Int, pool: Int
    public let alive: [Int]        // alive[k] = "Players" after the user's k-th win; alive[N] = winners
    public let share: Int

    public init(installSeed: UInt64, attemptId: Int, stage: Int, spec: SocialSkySpec = .reference) {
        typealias H = SocialHash
        let S = H.h64(installSeed, SocialLabels.sky, attemptId)
        let s = max(0, min(stage - 1, spec.levels.count - 1))
        N = spec.levels[s]; pool = spec.pools[s]
        if let drops = spec.drops, !drops.isEmpty {
            // events.SkyJump._absolute
            let dr = drops[min(s, drops.count - 1)]
            let d = dr.lo + (dr.hi - dr.lo) * H.u01(S, SocialLabels.hazd)
            var al = [100]
            for k in 1..<max(1, N) {
                let drop = k < dr.first ? 0 : H.roundHalfUp(d + 2.0 * H.u01(S, SocialLabels.haz, k) - 1.0)
                al.append(max(2, al[al.count - 1] - max(0, drop)))
            }
            let w = dr.wlo + H.floorInt(Double(dr.whi - dr.wlo + 1) * H.u01(S, SocialLabels.win))
            al.append(max(2, min(w, al[al.count - 1] - 1)))
            self.alive = al
            share = pool / al[al.count - 1]
            return
        }
        var alive = [100]
        for k in 1..<N {
            let h = 0.13 + 0.12 * H.u01(S, SocialLabels.haz, k)
            let drop = H.roundHalfUp(Double(alive[alive.count - 1] - 1) * h)
            alive.append(alive[alive.count - 1] - drop)
        }
        var others = 2 + H.floorInt(10.0 * (H.u01(S, SocialLabels.w1) + H.u01(S, SocialLabels.w2)) / 2.0)
        others = min(others, alive[alive.count - 1] - 1)
        alive.append(1 + others)
        self.alive = alive
        share = pool / alive[alive.count - 1]
    }
}
