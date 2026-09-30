import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.8, §4.12, D11). Written by the LEAD in WP0 and FROZEN: any change goes through
// the orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests).
//
// The ONE save file, schema v1 (`Application Support/Save/player.json`). Every field has a default and decoding
// tolerates missing keys (additive-only evolution: a new field decodes from an old file with its default; a rename or a
// removal needs a Migration + a version bump). A key that is present with the WRONG type throws, so the store can keep
// the file aside as corrupt and fall back to the backup (§4.12) instead of silently resetting a value.
// Sub-states owned by their modules (`EventsState` in Events/, `SocialState` in Social/) are not frozen but follow the
// same additive-only rule. The JSON keys are the Swift property names below.

public struct PlayerState: Codable, Sendable, Equatable {
    public var version = 1
    public var installSeed: UInt64 = 0               // random at first launch (or -pc.seed); feeds the social world
    public var installDate = Date(timeIntervalSince1970: 0)
    public var level = 1                             // next level to play (1 = the "Levels 1-4" session; then 5, 6, …)
    public var homeSeen = false                      // first home after the L6 win (VERIFIED tutorials §1)
    public var coins = 1000                          // VERIFIED start (vflows §8: 1000 + 80 + 6 × 20 = 1200 at L11)
    public var pendingCoinFly = 0                    // won and banked, not yet flown on home (+120 on the first home)
    public var lives = LivesState()                  // count 5, anchor nil
    public var unlimitedLivesUntil: Date?
    public var boosters: [String: Int] = [:]         // BoosterID.rawValue → stock
    public var unlocksSeen: Set<String> = []         // FeatureID.rawValue
    public var tutorialsDone: Set<String> = []       // TutorialID.rawValue
    public var attempts: [Int: Int] = [:]            // session's first level → starts
    public var activeAttempt: ActiveAttempt?         // non-nil at launch = the app was killed mid-level
    public var stats = Stats()
    public var events = EventsState()                // PathCore/Events (additive-only)
    public var social = SocialState()                // PathCore/Social: username, avatar, country, clock high-water, ledger
    public var settings = Settings()
    public var flags = Flags()
    public var processedTransactions: Set<String> = []

    public init() {}

    public init(installSeed: UInt64, installDate: Date) {
        self.installSeed = installSeed
        self.installDate = installDate
    }

    // MARK: sub-states (frozen with the aggregate)

    /// General stats (Profile: "First Try Wins", "Weekly Contest Wins"; VERIFIED vflows §9.2).
    public struct Stats: Codable, Sendable, Equatable {
        public var wins = 0
        public var losses = 0
        public var firstTryWins = 0
        public var weeklyContestWins = 0
        public var playSeconds: Double = 0

        public init(wins: Int = 0, losses: Int = 0, firstTryWins: Int = 0, weeklyContestWins: Int = 0, playSeconds: Double = 0) {
            self.wins = wins; self.losses = losses; self.firstTryWins = firstTryWins
            self.weeklyContestWins = weeklyContestWins; self.playSeconds = playSeconds
        }

        enum CodingKeys: String, CodingKey { case wins, losses, firstTryWins, weeklyContestWins, playSeconds }

        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            wins = try c.value(.wins, 0)
            losses = try c.value(.losses, 0)
            firstTryWins = try c.value(.firstTryWins, 0)
            weeklyContestWins = try c.value(.weeklyContestWins, 0)
            playSeconds = try c.value(.playSeconds, 0)
        }
    }

    /// The Settings / Pause toggles (never UserDefaults, D11).
    public struct Settings: Codable, Sendable, Equatable {
        public var sound = true                      // SFX bus
        public var music = true                      // music bus
        public var haptic = true
        public var notifications = true              // local-notification scheduling (§6.9)
        public var trail: String?                    // debug trail override: "solid" | "rainbow" | "ladder"; nil = board.json

        public init(sound: Bool = true, music: Bool = true, haptic: Bool = true, notifications: Bool = true, trail: String? = nil) {
            self.sound = sound; self.music = music; self.haptic = haptic; self.notifications = notifications; self.trail = trail
        }

        enum CodingKeys: String, CodingKey { case sound, music, haptic, notifications, trail }

        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            sound = try c.value(.sound, true)
            music = try c.value(.music, true)
            haptic = try c.value(.haptic, true)
            notifications = try c.value(.notifications, true)
            trail = try c.decodeIfPresent(String.self, forKey: .trail)
        }
    }

    /// One-time markers. `seen` holds any further marker by name, so a new one-time moment needs no contract change.
    public struct Flags: Codable, Sendable, Equatable {
        public var ratingPromptShown = false
        public var notificationPromptShown = false
        public var weeklyIntroSeen = false
        public var seen: Set<String> = []

        public init(ratingPromptShown: Bool = false, notificationPromptShown: Bool = false, weeklyIntroSeen: Bool = false,
                    seen: Set<String> = []) {
            self.ratingPromptShown = ratingPromptShown; self.notificationPromptShown = notificationPromptShown
            self.weeklyIntroSeen = weeklyIntroSeen; self.seen = seen
        }

        enum CodingKeys: String, CodingKey { case ratingPromptShown, notificationPromptShown, weeklyIntroSeen, seen }

        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            ratingPromptShown = try c.value(.ratingPromptShown, false)
            notificationPromptShown = try c.value(.notificationPromptShown, false)
            weeklyIntroSeen = try c.value(.weeklyIntroSeen, false)
            seen = try c.value(.seen, [])
        }
    }

    // MARK: coding

    enum CodingKeys: String, CodingKey {
        case version, installSeed, installDate, level, homeSeen, coins, pendingCoinFly, lives, unlimitedLivesUntil,
             boosters, unlocksSeen, tutorialsDone, attempts, activeAttempt, stats, events, social, settings, flags,
             processedTransactions
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        version = try c.value(.version, 1)
        installSeed = try c.value(.installSeed, 0)
        installDate = try c.value(.installDate, Date(timeIntervalSince1970: 0))
        level = try c.value(.level, 1)
        homeSeen = try c.value(.homeSeen, false)
        coins = try c.value(.coins, 1000)
        pendingCoinFly = try c.value(.pendingCoinFly, 0)
        lives = try c.value(.lives, LivesState())
        unlimitedLivesUntil = try c.decodeIfPresent(Date.self, forKey: .unlimitedLivesUntil)
        boosters = try c.value(.boosters, [:])
        unlocksSeen = try c.value(.unlocksSeen, [])
        tutorialsDone = try c.value(.tutorialsDone, [])
        attempts = try c.value(.attempts, [:])
        activeAttempt = try c.decodeIfPresent(ActiveAttempt.self, forKey: .activeAttempt)
        stats = try c.value(.stats, Stats())
        events = try c.value(.events, EventsState())
        social = try c.value(.social, SocialState())
        settings = try c.value(.settings, Settings())
        flags = try c.value(.flags, Flags())
        processedTransactions = try c.value(.processedTransactions, [])
    }
}

/// Lives (max 5, VERIFIED). `anchor` = the start of the RUNNING refill period; nil while full (the chain rules are C3's,
/// §4.8; the refill interval is PENDING-gameplay).
public struct LivesState: Codable, Sendable, Equatable {
    public var count = 5
    public var anchor: Date?

    public init(count: Int = 5, anchor: Date? = nil) { self.count = count; self.anchor = anchor }

    enum CodingKeys: String, CodingKey { case count, anchor }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        count = try c.value(.count, 5)
        anchor = try c.decodeIfPresent(Date.self, forKey: .anchor)
    }
}

/// The attempt in progress (written at start, cleared at the finish). Non-nil at launch = the app was killed mid-level
/// (`Economy.reconcileOnLaunch` applies the kill rule, §8.6).
public struct ActiveAttempt: Codable, Sendable, Equatable {
    public var session: String                       // SessionPlan.id
    public var levels: [Int]
    public var attemptIndex: Int
    public var startedAt: Date
    public var stage = 0

    public init(session: String, levels: [Int], attemptIndex: Int, startedAt: Date, stage: Int = 0) {
        self.session = session; self.levels = levels; self.attemptIndex = attemptIndex; self.startedAt = startedAt
        self.stage = stage
    }

    enum CodingKeys: String, CodingKey { case session, levels, attemptIndex, startedAt, stage }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        session = try c.value(.session, "")
        levels = try c.value(.levels, [])
        attemptIndex = try c.value(.attemptIndex, 1)
        startedAt = try c.value(.startedAt, Date(timeIntervalSince1970: 0))
        stage = try c.value(.stage, 0)
    }
}

private extension KeyedDecodingContainer {
    /// Missing key → `fallback`; present with the wrong type → throws (the store treats the file as corrupt).
    func value<T: Decodable>(_ key: Key, _ fallback: T) throws -> T {
        try decodeIfPresent(T.self, forKey: key) ?? fallback
    }
}
