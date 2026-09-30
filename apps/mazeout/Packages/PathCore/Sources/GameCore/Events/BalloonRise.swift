import Foundation

// C3 — B1 EVENTS-P: "Up & Away" (EventID "balloonRise"; our name, T1 / ruling 38), the original's v582 "Balloon Rise" RULES
// 1:1 (ruling 37b: rules stay, names / art are ours). Source: build/p/PH0/balloon.md (PH-0b, recorded on the owner's phone;
// SPEC.md ruling 42c fixed the EventOutcome shapes to it). Reference + golden trace: design/publish/tools/balloon_ref.py →
// fixtures/balloon_trace.json (BalloonRiseTests replays it).
// - ONE counter: levels won in a row. Each counted win adds +1 whatever the tag (VERIFIED: a Super Hard win gave +1).
// - ANY failed attempt (Level Failed, Quit, a killed app — `Events.onLoss`) resets it to 0: from 3 and from 1 (VERIFIED);
//   passed platforms do not protect it. A paid continue never reaches `onLoss`, so it keeps the counter (like the multiplier).
// - 10 platforms (2 5 8 13 20 28 36 46 77 120 wins in a row) each pay their chest ONCE per event: reaching 2 again after a
//   reset pays nothing (VERIFIED). The chest waits as a claim ("Tap to Claim" on home, like the Claw's steps). Paying the
//   last platform completes the event (`wins["balloonRise"]` += 1); the counter keeps counting past it (goal nil).
// - One event per event week in the rotation's ladder slot (EventRotation); the Monday roll resets the counter and the paid
//   platforms (earned claims stay). `best` = the best streak ever (the Profile's "max streak" tile, VERIFIED) survives rolls.
// - No rivals (VERIFIED): nothing here touches the social world.
// - The fail flow's bands carry no balloon wording (VERIFIED); after the last band step the app inserts the "fall" page when
//   the lost streak was ≥ `fallPageMinStreak` (DECISION 2: VERIFIED shown from 3, not from 1; "a platform was passed" and
//   "≥ 2" coincide because platform 1 sits at 2).

extension EventID {
    /// Up & Away (the original's v582 Balloon Rise). Declared in C3's own file: the ◆ IDs.swift contract is untouched.
    public static let balloonRise = EventID("balloonRise")
}

extension EventRules {
    /// social.json `events.balloonRise` (C3's layout).
    public struct BalloonRise: Codable, Sendable, Equatable {
        public struct Platform: Codable, Sendable, Equatable {
            /// Wins in a row that reach this platform.
            public var at: Int
            public var grant: Grant
            public init(at: Int, grant: Grant) { self.at = at; self.grant = grant }
        }

        /// VERIFIED balloon.md §4 (the chest (i) bubbles); platform 1's content was never shown: coins INFERRED from its open
        /// coin-chest art, 50 = DECISION (below platform 4's 100, the table's smallest coin prize). "hint" = the bulb,
        /// "freeze" = the hourglass.
        public var platforms: [Platform] = [
            Platform(at: 2, grant: .coins(50)),
            Platform(at: 5, grant: Grant(unlimitedLives: 900)),
            Platform(at: 8, grant: Grant(boosters: ["hint": 1])),
            Platform(at: 13, grant: .coins(100)),
            Platform(at: 20, grant: Grant(boosters: ["freeze": 1], unlimitedLives: 900)),
            Platform(at: 28, grant: Grant(coins: 150, unlimitedLives: 900)),
            Platform(at: 36, grant: Grant(boosters: ["hint": 1], unlimitedLives: 1800)),
            Platform(at: 46, grant: Grant(coins: 500, unlimitedLives: 3600)),
            Platform(at: 77, grant: Grant(boosters: ["freeze": 1], unlimitedLives: 3600)),
            Platform(at: 120, grant: Grant(coins: 1200, boosters: ["freeze": 1, "hint": 1], unlimitedLives: 3600)),
        ]
        /// The fail flow shows the fall page when the lost streak was at least this.
        public var fallPageMinStreak = 2

        public init() {}

        enum CodingKeys: String, CodingKey { case platforms, fallPageMinStreak }
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = BalloonRise()
            platforms = try c.v(.platforms, d.platforms)
            // strictly rising counts ≥ 1, or the defaults (a broken table never pays twice or never)
            let at = platforms.map(\.at)
            if at.isEmpty || at.first! < 1 || zip(at, at.dropFirst()).contains(where: { $0 >= $1 }) { platforms = d.platforms }
            fallPageMinStreak = try c.v(.fallPageMinStreak, d.fallPageMinStreak)
        }

        /// The next platform's count above `total` (nil after the last).
        public func goal(after total: Int) -> Int? { platforms.first(where: { $0.at > total })?.at }
    }
}

/// Up & Away's saved state (inside `EventsState`; additive: an old save decodes to the empty state).
public struct BalloonState: Codable, Sendable, Equatable {
    /// The event week this state belongs to (nil = not joined this week).
    public var week: Int?
    /// Levels won in a row in this event.
    public var streak = 0
    /// Platforms paid in this event (0…10): platform `paid + 1` is the next one that pays.
    public var paid = 0
    /// The best streak ever reached (the Profile's max-streak tile); kept across weeks.
    public var best = 0

    public init(week: Int? = nil, streak: Int = 0, paid: Int = 0, best: Int = 0) {
        self.week = week; self.streak = streak; self.paid = paid; self.best = best
    }

    enum CodingKeys: String, CodingKey { case week, streak, paid, best }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        week = try c.decodeIfPresent(Int.self, forKey: .week)
        streak = try c.v(.streak, 0); paid = try c.v(.paid, 0); best = try c.v(.best, 0)
    }
}

extension Events {
    /// The Up & Away instance (event week) of `t`.
    static func balloonIndex(_ t: SocialTime, _ r: EconomyRules) -> Int { EventSchedule.week(t, r.events.calendar) }

    /// A new week ended the stored event: start empty (joined again by the next home visit or counted win); `best` stays.
    static func balloonRoll(_ s: inout PlayerState, at t: SocialTime, _ r: EconomyRules) {
        if let w = s.events.balloon.week, w != balloonIndex(t, r) { s.events.balloon = BalloonState(best: s.events.balloon.best) }
    }

    static func balloonJoin(_ s: inout PlayerState, at t: SocialTime, _ r: EconomyRules) {
        if s.events.balloon.week == nil { s.events.balloon = BalloonState(week: balloonIndex(t, r), best: s.events.balloon.best) }
    }

    /// A counted win while Up & Away is live: +1, the platforms it reaches for the first time this event (claims).
    static func balloonWin(_ s: inout PlayerState, at t: SocialTime, _ r: EconomyRules) -> [EventOutcome] {
        balloonJoin(&s, at: t, r)
        let rules = r.events.balloonRise
        var b = s.events.balloon
        b.streak += 1
        b.best = max(b.best, b.streak)
        var steps: [EventOutcome] = []
        while b.paid < rules.platforms.count, b.streak >= rules.platforms[b.paid].at {
            b.paid += 1
            let reward = rules.platforms[b.paid - 1].grant
            addClaim(&s, .balloonRise, .balloonStep, grant: reward, value: b.paid, index: b.week ?? balloonIndex(t, r), at: t)
            steps.append(.balloonStep(step: b.paid, reward: reward))
            if b.paid == rules.platforms.count { s.events.wins[EventID.balloonRise.rawValue, default: 0] += 1 }
        }
        s.events.balloon = b
        return [.balloonStreak(added: 1, total: b.streak, goal: rules.goal(after: b.streak))] + steps
    }

    /// A failed attempt: the counter of this week's event → 0 (nothing when it is already 0 or the player never joined).
    static func balloonFail(_ s: inout PlayerState, at t: SocialTime, _ r: EconomyRules) -> [EventOutcome] {
        guard s.events.balloon.week == balloonIndex(t, r), s.events.balloon.streak > 0 else { return [] }
        let from = s.events.balloon.streak
        s.events.balloon.streak = 0
        return [.balloonFell(from: from)]
    }

    /// The fail flow's "fall" page: the lost streak when `outcomes` (of `onLoss`) reset one of at least
    /// `fallPageMinStreak`; nil = no page (balloon.md §5: shown from 3, not from 1).
    public static func balloonFallPage(_ outcomes: [EventOutcome], rules: EconomyRules) -> Int? {
        for o in outcomes {
            if case .balloonFell(let from) = o, from >= rules.events.balloonRise.fallPageMinStreak { return from }
        }
        return nil
    }

    /// Up & Away as the home bar, the page, the win-panel strip and the Profile read it.
    public struct BalloonStatus: Equatable, Sendable {
        public var streak: Int
        /// The next platform's count above the streak (nil past the last).
        public var goal: Int?
        /// Platforms paid this event (0…n).
        public var paid: Int
        /// The platforms' counts (2 … 120).
        public var platforms: [Int]
        /// The goal platform's reward while it is unpaid (the bar's right end); nil when it was paid or there is none.
        public var nextReward: Grant?
        /// Every platform paid this event.
        public var complete: Bool
        public var best: Int
        public var endsAt: SocialTime
        /// `home.balloon` accessibility value "streak/goal" ("streak" past the last platform).
        public var accessibilityValue: String
    }

    static func balloonStatus(_ s: PlayerState, at t: SocialTime, _ r: EconomyRules) -> BalloonStatus {
        let w = balloonIndex(t, r)
        return balloonStatus(s.events.balloon.week == w ? s.events.balloon : BalloonState(best: s.events.balloon.best), week: w, r)
    }

    /// The status of week `w`'s state `b` (the running week's, or B1b's held one as it stood at its end).
    static func balloonStatus(_ b: BalloonState, week w: Int, _ r: EconomyRules) -> BalloonStatus {
        let rules = r.events.balloonRise
        let goal = rules.goal(after: b.streak)
        var next: Grant?
        if let goal, let i = rules.platforms.firstIndex(where: { $0.at == goal }), i >= b.paid { next = rules.platforms[i].grant }
        return BalloonStatus(streak: b.streak, goal: goal, paid: b.paid, platforms: rules.platforms.map(\.at), nextReward: next,
                             complete: b.paid >= rules.platforms.count, best: b.best,
                             endsAt: EventSchedule.weekStart(w + 1, r.events.calendar),
                             accessibilityValue: goal.map { "\(b.streak)/\($0)" } ?? "\(b.streak)")
    }
}
