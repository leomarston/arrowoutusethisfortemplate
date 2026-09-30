import Foundation

// SOC1 (SPEC-architecture §4.11, SPEC-social §7 "Tuning", §12). `SocialConfig` = App/Resources/Tuning/social.json with
// compiled defaults. Tuning.swift ◆ decodes the WHOLE file into this type (falling back to `.default` if it throws), so
// every key is optional: a missing key keeps its default, never a crash.
//
// social.json is shared with C3 (Events/EventSchedule.swift `EventRules.load(social:)`), ONE source per value:
//   "worldModel"              which pinned world ships: "shipped" = the v2 international world (`SocialWorldModel.shipped`,
//                             PUBLISH B2; any name but "reference" / "calibrated" selects it) | "calibrated" (the v1 world
//                             SOC1-SOC1c calibrated to the phone; tests) | "reference" (the prototype)
//   "unlocks"                 EventID raw value → unlock level (C3 reads it too)
//   "events"                  C3's layout: prizes, Rocket/Sky stage levels, pools, cooldowns (SOC1 reads the parts
//                             the opponents need: weekly/streakRace prizes, skyJump levels+pools, rocketRace levels+prizes).
//                             The shipped file carries events.skyJump {levels [5, 7, 10], pools} (SOC1c: the phone's
//                             stage 3 = 10 levels / 10000), so C3's runs and the opponents' curves switch together.
//                             B1 (PUBLISH item 14): also events.rotation (the weekly rotation of the featured events) and
//                             events.balloonRise (Up & Away's platforms): C3's alone (the world does not read them — Up & Away
//                             has no rivals, and every board is independent of the calendar); carried here so the shipped
//                             file stays exactly what this type encodes (SocialNamesTests round trip).
//   "matchmaking"             SOC1: the Weekly / Streak Race group shapes (bands, arrivals)
//   "rocketBots"              SOC1: the rivals' rubber band (hold minutes, δ × the player's seconds per win); SOC1b:
//                             the lanes' roles, per-role holds and the sprinter's window
//   "skyBots"                 SOC1b: the Sky Jump survivor curve per stage [drop lo, drop hi, first step, winners lo, hi]
//   "lists", "refreshSeconds", "fallbackCountry"   SOC1: board shapes and refresh
// The world's population constants are code (SocialModel.swift); only the model NAME is data.

public struct SocialConfig: Codable, Sendable, Equatable {
    public var worldModel = "shipped"
    public var unlocks = SocialUnlocks()
    public var weekly = SocialGroupSpec.shippedWeekly
    public var streak = SocialGroupSpec.shippedStreak
    public var rocket = SocialRocketSpec.shipped
    public var sky = SocialSkySpec.shipped
    public var lists = SocialListShape()
    /// B1: C3's `events.rotation` / `events.balloonRise` as the shipped file carries them (`Self.shippedRotation`: the compiled
    /// C3 default is OFF, the shipped value decides).
    public var rotation = SocialConfig.shippedRotation
    public var balloonRise = EventRules.BalloonRise()
    /// Seconds between live refreshes of a visible board (SPEC-social §3.4).
    public var refreshSeconds = 5
    /// Home country when the device region is unknown.
    public var fallbackCountry = "US"

    // runtime (set by the app from SocialState before creating the world; never encoded)
    public var homeCountry: String? = nil
    public var homeOffsetMinutes: Int? = nil

    public init() {}
    public static let `default` = SocialConfig()

    /// The rotation block the app ships (design/publish/tools/rotation_ref.py CONFIG).
    public static let shippedRotation: EventRules.Rotation = {
        var r = EventRules.Rotation()
        r.enabled = true
        return r
    }()

    /// The reference prototype's event shapes (fixtures, tests).
    public static let reference: SocialConfig = {
        var c = SocialConfig()
        c.worldModel = "reference"
        c.weekly = .referenceWeekly
        c.streak = .referenceStreak
        c.rocket = .reference
        c.sky = .reference
        return c
    }()

    public var model: SocialWorldModel { SocialWorldModel.named(worldModel) }

    // ---------------------------------------------------------------- JSON

    enum CodingKeys: String, CodingKey {
        case worldModel, unlocks, events, matchmaking, rocketBots, skyBots, lists, refreshSeconds, fallbackCountry
    }

    public init(from decoder: Decoder) throws {
        let d = SocialConfig()
        let c = try decoder.container(keyedBy: CodingKeys.self)
        worldModel = (try? c.decodeIfPresent(String.self, forKey: .worldModel)) ?? d.worldModel
        unlocks = (try? c.decodeIfPresent(SocialUnlocks.self, forKey: .unlocks)) ?? d.unlocks
        let ev = (try? c.decodeIfPresent(EventsDTO.self, forKey: .events)) ?? nil
        let mm = (try? c.decodeIfPresent(MatchmakingDTO.self, forKey: .matchmaking)) ?? nil
        weekly = mm?.weekly?.spec(d.weekly) ?? d.weekly
        streak = mm?.streak?.spec(d.streak) ?? d.streak
        weekly.minLevel = unlocks.weeklyContest
        streak.minLevel = unlocks.streakRace
        if let p = ev?.weekly?.prizes { weekly.prizes = p }
        if let p = ev?.streakRace?.prizes { streak.prizes = p }
        if let l = ev?.skyJump?.levels, !l.isEmpty { sky.levels = l }
        if let p = ev?.skyJump?.pools, !p.isEmpty { sky.pools = p }
        if let l = ev?.rocketRace?.levels, !l.isEmpty { rocket.levels = l }
        if let p = ev?.rocketRace?.prizes, !p.isEmpty {
            rocket.prizes = p.map { (coins: $0.coins ?? 0, infiniteMinutes: Int(($0.unlimitedLives ?? 0) / 60)) }
        }
        rotation = ev?.rotation ?? d.rotation
        balloonRise = ev?.balloonRise ?? d.balloonRise
        if let rb = (try? c.decodeIfPresent(RocketBotsDTO.self, forKey: .rocketBots)) ?? nil {
            if let h = rb.holdMinutes, h.count == 2 { rocket.holdMinutes = (h[0], h[1]) }
            if let x = rb.delta, x.count == 2 { rocket.delta = (x[0], x[1]) }
            if let r = rb.roles, r.count == 4 { rocket.roles = r }
            if let hr = rb.holdByRole {
                var m: [String: (lo: Double, hi: Double)] = [:]
                for (k, v) in hr where v.count == 2 { m[k] = (v[0], v[1]) }
                rocket.holdByRole = m.isEmpty ? nil : m
            }
            if let v = rb.sprintMinutes { rocket.sprintMinutes = v }
        }
        if let sb = (try? c.decodeIfPresent(SkyBotsDTO.self, forKey: .skyBots)) ?? nil, let d = sb.drops {
            let parsed = d.compactMap { r -> SocialSkySpec.Drops? in
                r.count == 5 ? SocialSkySpec.Drops(r[0], r[1], Int(r[2]), Int(r[3]), Int(r[4])) : nil
            }
            sky.drops = parsed.isEmpty ? nil : parsed
        }
        lists = (try? c.decodeIfPresent(SocialListShape.self, forKey: .lists)) ?? d.lists
        refreshSeconds = (try? c.decodeIfPresent(Int.self, forKey: .refreshSeconds)) ?? d.refreshSeconds
        fallbackCountry = (try? c.decodeIfPresent(String.self, forKey: .fallbackCountry)) ?? d.fallbackCountry
    }

    /// Writes SOC1's keys + the `events` values it reads (the shipped social.json is generated from this, and a test
    /// keeps the file and the compiled defaults equal).
    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(worldModel, forKey: .worldModel)
        try c.encode(unlocks, forKey: .unlocks)
        try c.encode(MatchmakingDTO(weekly: GroupDTO(weekly), streak: GroupDTO(streak)), forKey: .matchmaking)
        try c.encode(RocketBotsDTO(holdMinutes: [rocket.holdMinutes.lo, rocket.holdMinutes.hi],
                                   delta: [rocket.delta.lo, rocket.delta.hi], roles: rocket.roles,
                                   holdByRole: rocket.holdByRole?.mapValues { [$0.lo, $0.hi] },
                                   sprintMinutes: rocket.sprintMinutes), forKey: .rocketBots)
        try c.encode(SkyBotsDTO(drops: sky.drops?.map { [$0.lo, $0.hi, Double($0.first), Double($0.wlo), Double($0.whi)] }),
                     forKey: .skyBots)
        // the one C3 `events` value the shipped file carries (SOC1c): Sky Jump's stage levels and pools, read by C3's
        // EventRules (the runs) and by the opponents' survivor curves — one source, so both switch together
        try c.encode(EventsOut(skyJump: .init(levels: sky.levels, pools: sky.pools), rotation: rotation, balloonRise: balloonRise),
                     forKey: .events)
        try c.encode(lists, forKey: .lists)
        try c.encode(refreshSeconds, forKey: .refreshSeconds)
        try c.encode(fallbackCountry, forKey: .fallbackCountry)
    }

    struct MatchmakingDTO: Codable { var weekly: GroupDTO?; var streak: GroupDTO? }
    struct RocketBotsDTO: Codable {
        var holdMinutes: [Double]?; var delta: [Double]?
        var roles: [String]?; var holdByRole: [String: [Double]]?; var sprintMinutes: Double?
    }
    struct SkyBotsDTO: Codable { var drops: [[Double]]? }
    struct EventsOut: Encodable {
        struct Sky: Encodable { var levels: [Int]; var pools: [Int] }
        var skyJump: Sky
        var rotation: EventRules.Rotation
        var balloonRise: EventRules.BalloonRise
    }

    struct GroupDTO: Codable {
        var bands: [[Double]]?              // [count, lo, hi, sameHours 0/1]
        var minTarget: Double?
        var earlyHours: Double?
        var early: String?                  // "hashed" | "elapsedDay" | a fraction written as text ("1.0")
        var lastArrivalBeforeEndHours: Double?
        var matchWindowMinutes: [Double]?   // [before, after] the join; absent = the player's last sessions
        var matchEventWindow: Bool?         // true = players who play during the contest window (the event day)
        var arriveByFirstPlay: Bool?        // true = a member arrives no later than its first win in the window
        var expectedPerPlayDay: Bool?       // true = bands compare levels per PLAYED day (the player's unit)
        var arriveAtJoin: Bool?             // true = every member arrives at the join with 0 points
        var tieByName: Bool?                // true = equal scores are listed alphabetically
        var failQ: [Double]?                // Streak Race: [lo, span], a member's fail chance per win = lo + span × u01

        init(_ s: SocialGroupSpec) {
            bands = s.bands.map { [Double($0.count), $0.lo, $0.hi, $0.sameHours ? 1 : 0] }
            minTarget = s.minTarget; earlyHours = s.earlyHours
            switch s.early {
            case .hashed: early = "hashed"
            case .elapsedDay: early = "elapsedDay"
            case .fraction(let f): early = String(f)
            }
            lastArrivalBeforeEndHours = s.lastArrivalBeforeEnd / 3600
            matchWindowMinutes = s.matchWindow.map { [$0.before / 60, $0.after / 60] }
            matchEventWindow = s.matchEventWindow
            arriveByFirstPlay = s.arriveByFirstPlay
            expectedPerPlayDay = s.expectedPerPlayDay
            arriveAtJoin = s.arriveAtJoin
            tieByName = s.tieByName
            failQ = [s.failQ.lo, s.failQ.span]
        }

        func spec(_ d: SocialGroupSpec) -> SocialGroupSpec {
            var s = d
            if let b = bands {
                let parsed = b.compactMap { r -> SocialBand? in
                    r.count >= 3 && r[0] >= 0 ? SocialBand(Int(r[0]), r[1], r[2], r.count > 3 && r[3] != 0) : nil
                }
                if !parsed.isEmpty { s.bands = parsed }
            }
            if let v = minTarget { s.minTarget = v }
            if let v = earlyHours { s.earlyHours = v }
            if let e = early {
                if e == "hashed" { s.early = .hashed } else if e == "elapsedDay" { s.early = .elapsedDay }
                else if let f = Double(e) { s.early = .fraction(f) }
            }
            if let v = lastArrivalBeforeEndHours { s.lastArrivalBeforeEnd = v * 3600 }
            if let w = matchWindowMinutes { s.matchWindow = w.count == 2 ? (w[0] * 60, w[1] * 60) : nil }
            if let v = matchEventWindow { s.matchEventWindow = v }
            if let v = arriveByFirstPlay { s.arriveByFirstPlay = v }
            if let v = expectedPerPlayDay { s.expectedPerPlayDay = v }
            if let v = arriveAtJoin { s.arriveAtJoin = v }
            if let v = tieByName { s.tieByName = v }
            if let v = failQ, v.count == 2 { s.failQ = (v[0], v[1]) }
            return s
        }
    }

    /// The parts of C3's `events` block the opponents need (C3 owns the layout; everything optional).
    struct EventsDTO: Decodable {
        struct Prizes: Decodable { var prizes: [Int]? }
        struct Sky: Decodable { var levels: [Int]?; var pools: [Int]? }
        struct GrantDTO: Decodable { var coins: Int?; var unlimitedLives: Double? }
        struct Rocket: Decodable { var levels: [Int]?; var prizes: [GrantDTO]? }
        var weekly: Prizes?
        var streakRace: Prizes?
        var skyJump: Sky?
        var rocketRace: Rocket?
        var rotation: EventRules.Rotation?
        var balloonRise: EventRules.BalloonRise?
        enum CodingKeys: String, CodingKey { case weekly, streakRace, skyJump, rocketRace, rotation, balloonRise }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            weekly = try? c.decodeIfPresent(Prizes.self, forKey: .weekly)
            streakRace = try? c.decodeIfPresent(Prizes.self, forKey: .streakRace)
            skyJump = try? c.decodeIfPresent(Sky.self, forKey: .skyJump)
            rocketRace = try? c.decodeIfPresent(Rocket.self, forKey: .rocketRace)
            rotation = try? c.decodeIfPresent(EventRules.Rotation.self, forKey: .rotation)
            balloonRise = try? c.decodeIfPresent(EventRules.BalloonRise.self, forKey: .balloonRise)
        }
    }
}

/// The level at which each social feature unlocks, keyed like C3's `EventRules.unlocks` (EventID raw values; SPEC-social
/// §1.3, D11: the phone's first appearances).
public struct SocialUnlocks: Codable, Sendable, Equatable {
    public var streakRace = 30, clawChallenge = 33, skyJump = 40, weeklyContest = 50, rocketRace = 55
    /// B1: Up & Away takes the Claw's unlock (events.md §4.4 DECISION); C3 reads it from the same `unlocks` block.
    public var balloonRise = 33
    public init() {}
    enum CodingKeys: String, CodingKey { case streakRace, clawChallenge, skyJump, weeklyContest, rocketRace, balloonRise }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let d = SocialUnlocks()
        streakRace = (try? c.decodeIfPresent(Int.self, forKey: .streakRace)) ?? d.streakRace
        clawChallenge = (try? c.decodeIfPresent(Int.self, forKey: .clawChallenge)) ?? d.clawChallenge
        skyJump = (try? c.decodeIfPresent(Int.self, forKey: .skyJump)) ?? d.skyJump
        weeklyContest = (try? c.decodeIfPresent(Int.self, forKey: .weeklyContest)) ?? d.weeklyContest
        rocketRace = (try? c.decodeIfPresent(Int.self, forKey: .rocketRace)) ?? d.rocketRace
        balloonRise = (try? c.decodeIfPresent(Int.self, forKey: .balloonRise)) ?? d.balloonRise
    }
}

/// The shape of the World / Country lists (SPEC-social §3.3; phone: World pages load on scroll, Country opens at the
/// player's row and is continuous from rank 1).
public struct SocialListShape: Codable, Sendable, Equatable {
    public var worldTop = 100              // rows 1…worldTop, then a separator and the player's window
    public var window = 10                 // rows either side of the player
    public var countryContinuousUpTo = 600 // Country is one continuous list 1…R+window when the player's rank R <= this
    public var maxTopRows = 5000           // deepest rank served by a top-k merge (deeper ranges use level bisection)
    public init() {}
    enum CodingKeys: String, CodingKey { case worldTop, window, countryContinuousUpTo, maxTopRows }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let d = SocialListShape()
        worldTop = (try? c.decodeIfPresent(Int.self, forKey: .worldTop)) ?? d.worldTop
        window = (try? c.decodeIfPresent(Int.self, forKey: .window)) ?? d.window
        countryContinuousUpTo = (try? c.decodeIfPresent(Int.self, forKey: .countryContinuousUpTo)) ?? d.countryContinuousUpTo
        maxTopRows = (try? c.decodeIfPresent(Int.self, forKey: .maxTopRows)) ?? d.maxTopRows
    }
}
