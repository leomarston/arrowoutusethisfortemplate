import Foundation

// SOC1 (SPEC-architecture §3.5 item 17, §4.11; SPEC-social §3-§4). `SocialEngine` is the implementation the ◆ SocialWorld
// delegates every call to: its initialiser and the eight method signatures below are FIXED (the ◆ file calls exactly
// them). Everything else here is SOC1's.
//
// Boards (SPEC-social §3.1): World and Country = level ↓ then progress ↓ (the player leads its own level group:
// rank = 1 + #players with level >= level+1); Weekly = the player's 10-player group, score ↓ then the moment it was
// reached ↑. Rows are exact: ranks are counts over the whole simulated world (hundreds of thousands to millions),
// computed per cohort by binary search.
//
// How the player's facts arrive (PlayerStanding): `level` = the level to play next (the home LEVEL plate); `ledger` =
// SocialState's ledger (wins with their Streak Race points, fails, the Weekly / Streak Race join markers).
// Conventions of the ◆ race calls (C3 builds the EventInstance):
//   streakRace(instance, …)  instance.index = the event day; the group is the one of the ledger's .streakJoin marker for
//                            that day, else it forms at instance.start (C3: the day start) with the pace derived from
//                            the ledger's 7 days before it.
//   page(.weekly(week), …)   the group of the ledger's .weeklyJoin marker for the week, else the one formed at the
//                            week's first counted win (level >= the Weekly unlock); none yet → an empty page.
//   rocketRace(instance, …)  instance.index = the race id (a counter); the stage is 1, or N from an EventID spelled
//                            "rocketRace.N"; the ◆ call has no user win times, so the rubber band only uses the hold
//                            (use `rocketLanes(…)` for the full rule and the player's lane).
//   skyJump(run, …)          run.instance.index = the attempt id; run.stage = the 1-based stage (C3; 0 reads as 1);
//                            run.progress = first-try wins in a row in this stage.

final class SocialEngine: @unchecked Sendable {
    let installSeed: UInt64
    let config: SocialConfig
    let names: NameBank
    let shared: SocialPopulation

    /// Serialises every query: the populations' exact memos are single-user (SocialPopulation). Recursive, because the
    /// entry points call each other.
    let lock = NSRecursiveLock()
    private var locals: [String: SocialPopulation] = [:]
    private var groups: [String: SocialGroupContest] = [:]
    private var groupOrder: [String] = []
    private var lastWeeklyMe: [Int: PlayerStanding] = [:]
    private var races: [String: SocialRocketRace] = [:]

    /// The player's own row id in every board (never a simulated id).
    static let meId: UInt64 = .max
    /// The most rows one page call returns (pages are for screens, not dumps).
    static let maxPageRows = 1000

    init(installSeed: UInt64, config: SocialConfig, names: NameBank) {
        self.installSeed = installSeed; self.config = config; self.names = names
        shared = SocialPopulation(model: config.model, names: names)
    }

    // ------------------------------------------------------------------ populations

    /// The population a player from `country` sees: the shared world, plus a device-only LOCAL partition when the
    /// country is not in the table (SPEC-social §2.3; the shared part stays byte-identical).
    /// v2 (M3 + M4; socialsim/v2.py world_for_home): every region code the table, an alias or a numeric region knows plays
    /// on the shared world; only a 2-letter code nobody knows gets a LOCAL partition, keyed by its ISO, at offset 0 with
    /// the culture 'en' (static: never the device's clock or language).
    func population(for country: String) -> SocialPopulation {
        if let intl = config.model.intl {
            let home = config.model.homeBoard(forRegion: country, fallback: config.fallbackCountry)
            guard home.local, intl.localByISO else { return shared }
            lock.lock(); defer { lock.unlock() }
            if let p = locals[home.iso] { return p }
            let p = SocialPopulation(model: config.model, local: SocialLocalPartition(iso: home.iso, offsetMinutes: 0, culture: "en"),
                                     names: names)
            locals[home.iso] = p
            return p
        }
        let iso = country.uppercased()
        if config.model.countries.contains(where: { $0.iso == iso }) { return shared }
        lock.lock(); defer { lock.unlock() }
        if let p = locals[iso] { return p }
        let off = (config.homeCountry?.uppercased() == iso ? config.homeOffsetMinutes : nil) ?? 0
        let lp = SocialLocalPartition(iso: iso, offsetMinutes: off, culture: SocialWorldModel.extraCulture[iso] ?? "en")
        let p = SocialPopulation(model: config.model, local: lp, names: names)
        locals[iso] = p
        return p
    }

    // ------------------------------------------------------------------ rows

    func simPlayer(_ W: SocialPopulation, _ c: SocialCohort, _ j: Int) -> SimPlayer {
        let (nm, st) = W.name(c, j)
        return SimPlayer(id: UInt64(W.gid(c, j)), name: nm, country: W.isoOf(c, j), avatar: W.avatar(c, j, style: st))
    }

    func meRow(_ me: PlayerStanding, rank: Int, value: Int) -> LeaderboardRow {
        LeaderboardRow(rank: rank, player: SimPlayer(id: Self.meId, name: me.name, country: me.country, avatar: me.avatar),
                       value: value, isMe: true)
    }

    // ------------------------------------------------------------------ ◆ entry points

    func page(_ kind: LeaderboardKind, me: PlayerStanding, at: SocialTime, ranks: ClosedRange<Int>) -> LeaderboardPage {
        lock.lock(); defer { lock.unlock() }
        switch kind {
        case .world: return levelBoard(iso: nil, me: me, at: at, ranks: ranks)
        case .country(let iso): return levelBoard(iso: iso.uppercased(), me: me, at: at, ranks: ranks)
        case .weekly(let week):
            guard let st = weeklyStandings(week: week, me: me, at: at) else { return LeaderboardPage(rows: [], myRank: 0, total: 0) }
            let rows = st.rows.filter { ranks.contains($0.rank) }
            return LeaderboardPage(rows: rows, myRank: st.myRank, total: st.rows.count)
        }
    }

    func page(_ kind: LeaderboardKind, me: PlayerStanding, at: SocialTime, around: Int, radius: Int) -> LeaderboardPage {
        lock.lock(); defer { lock.unlock() }
        let r = max(0, radius)
        let lo = max(1, around - r)
        return page(kind, me: me, at: at, ranks: lo...max(lo, around + r))
    }

    func weeklyPodium(week: Int, at: SocialTime) -> [LeaderboardRow] {
        lock.lock(); defer { lock.unlock() }
        // ◆ gives no player here: the podium of the group the player's last Weekly page showed (SOC2 should prefer
        // `weeklyBoard(week:me:at:)`, which returns the podium and the rows in one call)
        guard let me = lastWeeklyMe[week], let st = weeklyStandings(week: week, me: me, at: at) else { return [] }
        return Array(st.rows.prefix(3))
    }

    func player(_ id: UInt64) -> SimPlayer {
        lock.lock(); defer { lock.unlock() }
        if id == Self.meId {
            return SimPlayer(id: id, name: SocialNames.userDefaultName(installSeed: installSeed), country: "", avatar: 0)
        }
        let W = id >= (1 << 40) ? (lock.withLock { locals.values.first }) ?? shared : shared
        guard id < UInt64(Int.max), let (c, j) = W.find(Int(id)) else {
            return SimPlayer(id: id, name: "", country: "", avatar: 0)
        }
        return simPlayer(W, c, j)
    }

    func streakRace(_ instance: EventInstance, player: PlayerStanding, at: SocialTime) -> [RaceStanding] {
        lock.lock(); defer { lock.unlock() }
        let day = instance.index
        let key = SocialState.groupKey(in: player.ledger, kind: .streakJoin, instance: day)
            ?? derivedKey(ledger: player.ledger, instance: day, t0: Double(instance.start.seconds), weekly: false)
        let st = groupStandings(spec: config.streak, key: key, me: player, at: at)
        return st.rows.map { RaceStanding(rank: $0.rank, player: $0.player, score: $0.value, isMe: $0.isMe) }
    }

    func rocketRace(_ instance: EventInstance, joinedAt: SocialTime, at: SocialTime) -> [RaceStanding] {
        lock.lock(); defer { lock.unlock() }
        let stage = Self.stage(of: instance.event)
        let lanes = rocketLanes(raceId: instance.index, stage: stage, joinedAt: joinedAt, secondsPerWin: 120,
                                userWins: nil, me: nil, at: at)
        return lanes.lanes.filter { !$0.isMe }
    }

    func skyJump(_ run: SkyJumpRun, at: SocialTime) -> SkyJumpField {
        lock.lock(); defer { lock.unlock() }
        let sj = SocialSkyJump(installSeed: installSeed, attemptId: run.instance.index, stage: max(1, run.stage), spec: config.sky)
        let step = max(0, min(run.progress, sj.N))
        let left = step >= sj.N ? sj.alive[sj.N] : sj.alive[step]
        return SkyJumpField(total: 100, left: left, winners: step >= sj.N ? sj.alive[sj.N] : 0,
                            shown: skyShown(attemptId: run.instance.index, at: Double(run.joinedAt.seconds)))
    }

    static func stage(of event: EventID) -> Int {
        let parts = event.rawValue.split(separator: ".")
        if parts.count == 2, let n = Int(parts[1].filter(\.isNumber)), n >= 1 { return n }
        return 1
    }

    // ------------------------------------------------------------------ World / Country

    func levelBoard(iso requested: String?, me: PlayerStanding, at: SocialTime, ranks: ClosedRange<Int>) -> LeaderboardPage {
        let W = population(for: me.country)
        let t = Double(at.seconds)
        W.extend(to: t)
        // v2: a territory / numeric region code plays on its board's country (IC -> ES); v1 keeps the code
        let iso = requested.map { config.model.boardCountry($0) }
        let includeMe = iso == nil || iso == config.model.boardCountry(me.country)
        let others = W.joined(t, iso: iso)
        let myRank = includeMe ? W.rankOfLevel(me.level, t, iso: iso) : 0
        let total = others + (includeMe ? 1 : 0)
        let a = max(1, ranks.lowerBound), b = min(total, ranks.upperBound, a + Self.maxPageRows - 1)
        guard a <= b else { return LeaderboardPage(rows: [], myRank: myRank, total: total) }
        // the other players' 0-based positions in the (P ↓, gid ↑) order that ranks a…b cover (the player's own rank
        // is not one of them: rows above it are positions r−1, rows below it r−2)
        let otherRanks = (a...b).filter { !(includeMe && $0 == myRank) }
        func pos(_ r: Int) -> Int { includeMe && r > myRank ? r - 2 : r - 1 }
        var refs: [SocialPopulation.Ref] = []
        if let f = otherRanks.first, let l = otherRanks.last {
            refs = othersInOrder(W, t: t, iso: iso, from: pos(f), through: pos(l), meLevel: me.level,
                                 myRank: includeMe ? myRank : nil)
        }
        var rows: [LeaderboardRow] = []
        rows.reserveCapacity(b - a + 1)
        var k = 0
        for r in a...b {
            if includeMe && r == myRank { rows.append(meRow(me, rank: r, value: me.level)); continue }
            guard k < refs.count else { break }
            let ref = refs[k]; k += 1
            rows.append(LeaderboardRow(rank: r, player: simPlayer(W, ref.c, ref.j), value: 1 + SocialHash.floorInt(ref.P),
                                       isMe: false))
        }
        return LeaderboardPage(rows: rows, myRank: myRank, total: total)
    }

    /// Other players at 0-based positions from…through of the (P ↓, gid ↑) order.
    func othersInOrder(_ W: SocialPopulation, t: Double, iso: String?, from: Int, through: Int, meLevel: Int,
                       myRank: Int?) -> [SocialPopulation.Ref] {
        guard from <= through, through >= 0 else { return [] }
        let lo = max(0, from)
        if through < config.lists.maxTopRows {
            return Array(W.top(t, through + 1, iso: iso).dropFirst(lo))
        }
        // deep: the players around a level boundary. `countAtLeast(x+1)` players have level > x; the next ones (level
        // <= x, P ↓) are neighbours(x).below.
        let x: Int
        if let mr = myRank, abs(lo - (mr - 1)) <= 10_000 || abs(through - (mr - 1)) <= 10_000 {
            x = meLevel
        } else {
            x = levelAtPosition(W, t: t, iso: iso, position: lo)
        }
        // positions 0 ..< aboveCount have level > x (the player's own rank already counted them when x is its level)
        let aboveCount = (x == meLevel && myRank != nil) ? myRank! - 1 : W.countAtLeast(x + 1, t, iso: iso)
        var out: [SocialPopulation.Ref] = []
        let nAbove = lo < aboveCount ? aboveCount - lo : 0
        let nBelow = through >= aboveCount ? through - aboveCount + 1 : 0
        let (above, below) = W.neighbours(x, t, above: nAbove, below: nBelow, iso: iso)   // above[0] = position aboveCount − 1
        if nAbove > 0 {
            out.append(contentsOf: above.prefix(nAbove).reversed().prefix(through - lo + 1))   // positions lo … aboveCount − 1
        }
        if nBelow > 0 {
            out.append(contentsOf: below.dropFirst(max(lo, aboveCount) - aboveCount))
        }
        return out
    }

    /// The level of the player at 0-based position `position` (bisection on countAtLeast).
    func levelAtPosition(_ W: SocialPopulation, t: Double, iso: String?, position: Int) -> Int {
        var lo = 1, hi = 1
        while W.countAtLeast(hi, t, iso: iso) > position { lo = hi; hi *= 2 }
        while hi - lo > 1 {
            let mid = (lo + hi) / 2
            if W.countAtLeast(mid, t, iso: iso) > position { lo = mid } else { hi = mid }
        }
        return lo
    }

    // ------------------------------------------------------------------ group contests

    /// The group key of a join the ledger has no marker for: the pace from the ledger's 7 days before t0 (the oldest
    /// entries are the first the cap trims, so the key holds while those 7 days are in the ledger; the marker path
    /// freezes it for good — SocialState.joinWeekly / joinStreak).
    func derivedKey(ledger: [LedgerEntry], instance: Int, t0: Double, weekly: Bool) -> SocialGroupKey {
        var s = SocialState()
        s.ledger = ledger.filter { Double($0.at.seconds) < t0 && Double($0.at.seconds) >= t0 - 7 * 86_400 }
        let p = s.pace(at: t0)
        return SocialGroupKey(instance: instance, t0: t0, ref: weekly ? p.weekly : p.daily, windows: s.playWindows(before: t0))
    }

    func group(spec: SocialGroupSpec, key: SocialGroupKey, W: SocialPopulation) -> SocialGroupContest {
        let id = "\(spec.kind.rawValue)|\(key.instance)|\(key.t0)|\(key.ref)|\(key.windows)|\(ObjectIdentifier(W).hashValue)"
        lock.lock()
        if let g = groups[id] { lock.unlock(); return g }
        lock.unlock()
        let g = SocialGroupContest(W: W, installSeed: installSeed, spec: spec, key: key)
        lock.lock()
        groups[id] = g
        groupOrder.append(id)
        if groupOrder.count > 8 { groups[groupOrder.removeFirst()] = nil }
        lock.unlock()
        return g
    }

    /// The player's score in a group: the Weekly counts the wins since the join; the Streak Race sums the wins' points.
    static func userScore(_ ledger: [LedgerEntry], kind: SocialGroupSpec.Kind, from t0: Double, until: Double,
                          windowEnd: Double) -> (score: Int, reached: Double) {
        var score = 0
        var reached = t0
        for e in ledger where e.kind == .win {
            let t = Double(e.at.seconds)
            guard t >= t0, t <= until, t < windowEnd else { continue }
            let add = kind == .weekly ? 1 : e.score
            if add > 0 { score += add; reached = max(reached, t) }
        }
        return (score, reached)
    }

    struct GroupStandings { let rows: [LeaderboardRow]; let myRank: Int; let prizes: [Int]; let endsAt: Double }

    func groupStandings(spec: SocialGroupSpec, key: SocialGroupKey, me: PlayerStanding, at: SocialTime) -> GroupStandings {
        lock.lock(); defer { lock.unlock() }
        let W = population(for: me.country)
        let g = group(spec: spec, key: key, W: W)
        let t = Double(at.seconds)
        let (score, reached) = Self.userScore(me.ledger, kind: spec.kind, from: key.t0, until: t, windowEnd: g.we)
        var rows: [LeaderboardRow] = []
        var myRank = 0
        for (k, r) in g.standings(t, userScore: score, userReached: reached, userName: me.name).enumerated() {
            if let i = r.member {
                let (c, j) = g.members[i]
                rows.append(LeaderboardRow(rank: k + 1, player: simPlayer(W, c, j), value: r.score, isMe: false))
            } else {
                myRank = k + 1
                rows.append(meRow(me, rank: k + 1, value: r.score))
            }
        }
        return GroupStandings(rows: rows, myRank: myRank, prizes: spec.prizes, endsAt: g.we)
    }

    /// The week's group key: its join marker, else the week's first counted win (the auto-join), else nil.
    func weeklyKey(week: Int, ledger: [LedgerEntry]) -> SocialGroupKey? {
        if let k = SocialState.groupKey(in: ledger, kind: .weeklyJoin, instance: week) { return k }
        let ws = SocialCalendar.eventWeekStart(week), we = SocialCalendar.eventWeekStart(week + 1)
        guard let first = ledger.first(where: {
            $0.kind == .win && $0.level >= config.unlocks.weeklyContest && Int($0.at.seconds) >= ws && Int($0.at.seconds) < we
        }) else { return nil }
        return derivedKey(ledger: ledger, instance: week, t0: Double(first.at.seconds), weekly: true)
    }

    func weeklyStandings(week: Int, me: PlayerStanding, at: SocialTime) -> GroupStandings? {
        lock.lock(); defer { lock.unlock() }
        guard let key = weeklyKey(week: week, ledger: me.ledger) else { return nil }
        lastWeeklyMe[week] = me
        return groupStandings(spec: config.weekly, key: key, me: me, at: at)
    }

    // ------------------------------------------------------------------ Rocket Race / Sky Jump

    struct RocketLanes { let lanes: [RaceStanding]; let N: Int; let result: SocialRocketRace.Result; let resultAt: Double }

    func rocketLanes(raceId: Int, stage: Int, joinedAt: SocialTime, secondsPerWin: Double, userWins: [Double]?,
                     me: PlayerStanding?, at: SocialTime) -> RocketLanes {
        lock.lock(); defer { lock.unlock() }
        let W = population(for: me?.country ?? (config.homeCountry ?? config.fallbackCountry))
        let rid = "\(raceId)|\(stage)|\(joinedAt.seconds)|\(secondsPerWin)|\(ObjectIdentifier(W).hashValue)"
        let rr: SocialRocketRace
        if let hit = races[rid] {
            rr = hit
        } else {
            rr = SocialRocketRace(W: W, installSeed: installSeed, raceId: raceId, stage: stage, t0: Double(joinedAt.seconds),
                                  secondsPerWin: secondsPerWin, spec: config.rocket)
            if races.count >= 8 { races.removeAll() }
            races[rid] = rr
        }
        let t = Double(at.seconds)
        let wins = (userWins ?? []).filter { $0 >= rr.t0 && $0 <= t }.sorted()
        let nm1: Double? = wins.count >= rr.N - 1 ? wins[rr.N - 2] : nil
        // rows: (progress ↓, then the moment it was reached ↑)
        var rows: [(score: Int, reach: Double, player: SimPlayer, isMe: Bool)] = []
        for i in rr.rivals.indices {
            let p = rr.rivalProgress(i, t, userNminus1: nm1)
            let (c, j) = rr.rivals[i]
            let reach: Double
            if p >= rr.N, let f = rr.finishTime(i, userNminus1: nm1) { reach = f }
            else if p > 0 { reach = W.firstTimeReaching(c, j, rr.base[i] + p, rr.t0, min(t, rr.end)) ?? t }
            else { reach = rr.t0 }
            rows.append((p, reach, simPlayer(W, c, j), false))
        }
        if let me = me {
            let p = min(wins.count, rr.N)
            rows.append((p, p > 0 ? wins[p - 1] : rr.t0,
                         SimPlayer(id: Self.meId, name: me.name, country: me.country, avatar: me.avatar), true))
        }
        rows.sort { $0.score != $1.score ? $0.score > $1.score : ($0.reach != $1.reach ? $0.reach < $1.reach : $0.isMe) }
        let lanes = rows.enumerated().map { RaceStanding(rank: $0.offset + 1, player: $0.element.player, score: $0.element.score,
                                                          isMe: $0.element.isMe) }
        let out = rr.outcome(userTimes: wins)
        let settled = out.result == .win || out.at <= t
        return RocketLanes(lanes: lanes, N: rr.N, result: settled ? out.result : .none, resultAt: out.at)
    }

    /// The portraits of the "Finding players on your level." fan and the map pads: up to 14 active World players with a
    /// portrait (avatar != 0), fixed per attempt (a Swift-side DECISION; the reference models only the counts).
    func skyShown(attemptId: Int, at t: Double) -> [SimPlayer] {
        let W = population(for: config.homeCountry ?? config.fallbackCountry)
        let S = SocialHash.h64(installSeed, SocialLabels.skyShown, attemptId)
        var out: [SimPlayer] = []
        let got = W.sampleMembers(t, S, SocialLabels.skyShown, 14, maxTries: 600) { c, j, _ in
            guard W.activeAt(c, j, t) else { return false }
            let (_, st) = W.name(c, j)
            return W.avatar(c, j, style: st) != 0
        }
        for (c, j) in got { out.append(simPlayer(W, c, j)) }
        return out
    }
}

// ---------------------------------------------------------------------------------------------------------------------
// Public helpers beyond the ◆ surface (SOC2 and GAME use these; the ◆ calls above are their narrow forms).

/// A group contest board with its prizes and end.
public struct SocialGroupBoard: Sendable, Equatable {
    public var rows: [LeaderboardRow]           // every row, rank 1…n, the player's row isMe
    public var myRank: Int
    public var prizes: [Int]                    // coins for ranks 1…prizes.count
    public var endsAt: SocialTime
    public var prize: Int { myRank >= 1 && myRank <= prizes.count ? prizes[myRank - 1] : 0 }
}

/// The Rocket Race lanes with the player's own lane and the race result so far.
public struct SocialRocketBoard: Sendable, Equatable {
    public var lanes: [RaceStanding]            // 5 lanes: progress ↓, then earlier reach; rank 1 = the gold "1"
    public var levels: Int                      // N of the stage
    public var result: String                   // "win" | "lose" | "none" (still running)
    public var resultAt: SocialTime             // when the race was decided (or the day end)
}

extension SocialWorld {
    /// The Weekly Contest board of `week` (nil until the week's group formed: SocialState.joinWeekly).
    public func weeklyBoard(week: Int, me: PlayerStanding, at: SocialTime) -> SocialGroupBoard? {
        guard let st = engine.weeklyStandings(week: week, me: me, at: at) else { return nil }
        return SocialGroupBoard(rows: st.rows, myRank: st.myRank, prizes: st.prizes, endsAt: SocialTime(seconds: Int64(st.endsAt)))
    }

    /// The Streak Race board of an event day for an explicit group key (SocialState.joinStreak / streakKey).
    public func streakBoard(key: SocialGroupKey, me: PlayerStanding, at: SocialTime) -> SocialGroupBoard {
        let st = engine.groupStandings(spec: engine.config.streak, key: key, me: me, at: at)
        return SocialGroupBoard(rows: st.rows, myRank: st.myRank, prizes: st.prizes, endsAt: SocialTime(seconds: Int64(st.endsAt)))
    }

    /// The Rocket Race with the full fairness rule (the player's own win times since joining) and the player's lane.
    public func rocketBoard(raceId: Int, stage: Int, joinedAt: SocialTime, secondsPerWin: Double, userWins: [SocialTime],
                            me: PlayerStanding, at: SocialTime) -> SocialRocketBoard {
        let r = engine.rocketLanes(raceId: raceId, stage: stage, joinedAt: joinedAt, secondsPerWin: secondsPerWin,
                                   userWins: userWins.map { Double($0.seconds) }, me: me, at: at)
        return SocialRocketBoard(lanes: r.lanes, levels: r.N, result: r.result.rawValue,
                                 resultAt: SocialTime(seconds: Int64(r.resultAt.rounded(.up))))
    }

    /// The Sky Jump survivor curve of an attempt (alive[k] after the player's k-th first-try win; the last = winners).
    public func skyJumpCurve(attemptId: Int, stage: Int) -> SocialSkyJump {
        SocialSkyJump(installSeed: engine.installSeed, attemptId: attemptId, stage: stage, spec: engine.config.sky)
    }

    /// Rank the player would have on World (iso nil) or a Country board at `level`.
    public func rank(level: Int, country: String?, me: PlayerStanding, at: SocialTime) -> Int {
        engine.lock.lock(); defer { engine.lock.unlock() }
        let W = engine.population(for: me.country)
        let t = Double(at.seconds)
        W.extend(to: t)
        return W.rankOfLevel(level, t, iso: country.map { engine.config.model.boardCountry($0) })
    }

    /// Players in the world (World) or a country at `at` (the board's population).
    public func population(country: String?, me: PlayerStanding, at: SocialTime) -> Int {
        engine.lock.lock(); defer { engine.lock.unlock() }
        let W = engine.population(for: me.country)
        let t = Double(at.seconds)
        W.extend(to: t)
        return W.joined(t, iso: country.map { engine.config.model.boardCountry($0) })
    }

    /// The ISO of the Country board a stored home country (or device region code) plays on: v2 resolves a territory or a
    /// numeric region to its board's country (IC -> ES, GU -> US); v1 keeps the code. The Country tab names this country.
    public func boardCountry(_ code: String) -> String { engine.config.model.boardCountry(code) }

    /// The config the world runs on.
    public var config: SocialConfig { engine.config }
    public var installSeed: UInt64 { engine.installSeed }

    /// Builds the cohort table up to `at` (the launch warm-up calls this behind Loading, off the main thread), and the home
    /// country's LOCAL partition when it has one (config.homeCountry).
    public func warmUp(to at: SocialTime) {
        warmUp(to: at, country: engine.config.homeCountry)
    }

    /// Builds the cohort table up to `at` for a player from `country` (the shared world, plus the device-only LOCAL
    /// partition of a region code no table knows — v2 M4: built behind Loading, never cold on the first board open) and
    /// that country's unit index (the Country board's first query).
    public func warmUp(to at: SocialTime, country: String?) {
        engine.lock.lock(); defer { engine.lock.unlock() }
        let t = Double(at.seconds) + 2 * 86_400
        engine.shared.extend(to: t)
        guard let country else { return }
        let W = engine.population(for: country)
        if W !== engine.shared { W.extend(to: t) }
        if engine.config.model.intl != nil { _ = W.isoUnits(engine.config.model.boardCountry(country)) }
    }
}
