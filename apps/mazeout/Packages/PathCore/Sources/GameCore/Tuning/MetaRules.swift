import Foundation

// Template phase 1 (docs/ROADMAP.md): the META half of the core's rule table, split out of ArrowEscape's `RulesTuning`
// (SPEC-architecture §4.5, §4.8, §4.9) so the economy and the shell's fail flow read no puzzle rules. The keys are the
// same rules.json keys (`failChain`, `rewards`, `boosters`) and `RulesTuning` keeps them under the same Swift names
// (`RulesTuning.FailStep` … are typealiases of the types below), so the JSON and the behaviour are unchanged.
// Decoding is tolerant like every tuning table: a missing key keeps its default.

public struct MetaRules: Codable, Sendable, Equatable {

    // MARK: fail chain (§4.5)

    /// What "Play On" / "Add Time" / "Add Lives" gives on one step.
    public enum StepGrant: String, Codable, Sendable, CaseIterable { case addTime, refillHearts, none }

    /// One popup of a fail chain. The caller charges `price` before `acceptContinue()`.
    public struct FailStep: Codable, Sendable, Equatable {
        public var price: Int
        public var grant: StepGrant
        /// Seconds (addTime) or hearts (refillHearts).
        public var amount: Int
        public var warning: ContinueOffer.Warning
        /// Shown only while the streak multiplier is above x1 (VERIFIED research/fail.md §1: "B is skipped when the
        /// multiplier is already x1"); the session reads `LevelSession.streakActive`.
        public var onlyWithStreak: Bool

        public init(price: Int, grant: StepGrant, amount: Int, warning: ContinueOffer.Warning = .none,
                    onlyWithStreak: Bool = false) {
            self.price = price; self.grant = grant; self.amount = amount; self.warning = warning
            self.onlyWithStreak = onlyWithStreak
        }

        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            price = try c.v(.price, 900)
            grant = try c.v(.grant, .none)
            amount = try c.v(.amount, 0)
            warning = try c.v(.warning, .none)
            onlyWithStreak = try c.v(.onlyWithStreak, false)
        }

        public var offerGrant: ContinueOffer.Grant {
            switch grant {
            case .addTime: return .addTime(amount)
            case .refillHearts: return .refillHearts(amount)
            case .none: return .none
            }
        }
    }

    // MARK: rewards (§4.8; WinResult.reward)

    public struct Rewards: Codable, Sendable, Equatable {
        /// Coins per win by tag. VERIFIED research/flows + levels.md: normal 20, Hard 60, Super Hard 100.
        public var normal: Int = 20
        public var hard: Int = 60
        public var superHard: Int = 100
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Rewards()
            normal = try c.v(.normal, d.normal)
            hard = try c.v(.hard, d.hard)
            superHard = try c.v(.superHard, d.superHard)
        }
        public func reward(for tag: LevelTag) -> Int {
            switch tag {
            case .normal: return normal
            case .hard: return hard
            case .superHard: return superHard
            }
        }
    }

    // MARK: boosters (§4.9: the session hook; stock is the caller's)

    /// What a booster does inside the session (C3's `BoosterRule` owns price/stock; GAME maps it here).
    public enum BoosterAction: String, Codable, Sendable, CaseIterable { case freezeTimer, hint, none }

    /// Which free unit the bulb hints (SPEC-gameplay §6.3, DECISION; the key's home is rules.json per CONSISTENCY K-8).
    public enum HintPolicy: String, Codable, Sendable, CaseIterable {
        /// Among the units free right now, the one whose exit unblocks the most other arrows; ties → the longer arrow → the
        /// lower id; a tape bundle as a whole.
        case unblocksMost
    }

    public struct Boosters: Codable, Sendable, Equatable {
        /// BoosterID raw value → its action. VERIFIED v552: left hourglass = freeze, right bulb = hint (research/boosters.md).
        public var actions: [String: BoosterAction] = ["freeze": .freezeTimer, "hint": .hint]
        /// The freeze's visible countdown (s). VERIFIED research/boosters.md §2 ("Freeze = 10 s").
        public var freezeSeconds: Double = 10
        /// The hourglass flight before the countdown; the clock is frozen during it too. RULED 1.6 s (CONSISTENCY K-3,
        /// SPEC-motion-audio §3.10.2, §13.4; SPEC.md §5 item 29) from VERIFIED ≈ 1.5 s (boosters.md §2).
        public var freezeFlight: Double = 1.6
        /// A freeze counts down only while the timer has started (DECISION: never wasted before the first tap).
        public var freezeRunsBeforeStart: Bool = false
        /// Units highlighted by one hint (VERIFIED: one arrow, research/boosters.md §1).
        public var hintUnits: Int = 1
        /// rules.json `boosters.hintPolicy` (K-8; SPEC.md §5 item 29 asks for its reader). Read and carried here;
        /// `Solver.hintUnit` does not branch on it yet (its choice is still the greedy order's first free unit, which the
        /// HeadlessDriver's solver strategy also taps).
        public var hintPolicy: HintPolicy = .unblocksMost
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Boosters()
            actions = try c.v(.actions, d.actions)
            freezeSeconds = try c.v(.freezeSeconds, d.freezeSeconds)
            freezeFlight = try c.v(.freezeFlight, d.freezeFlight)
            freezeRunsBeforeStart = try c.v(.freezeRunsBeforeStart, d.freezeRunsBeforeStart)
            hintUnits = try c.v(.hintUnits, d.hintUnits)
            hintPolicy = try c.v(.hintPolicy, d.hintPolicy)
        }
        public func action(_ b: BoosterID) -> BoosterAction { actions[b.rawValue] ?? .none }
        /// Total clock freeze for one hourglass (flight + countdown).
        public var freezeTotal: Double { max(0, freezeFlight) + max(0, freezeSeconds) }
    }

    // MARK: the table

    /// ContinueOffer.Kind raw value → the chain, in order (see `defaultFailChain`).
    public var failChain: [String: [FailStep]] = MetaRules.defaultFailChain
    public var rewards = Rewards()
    public var boosters = Boosters()

    public init() {}

    public init(failChain: [String: [FailStep]], rewards: Rewards, boosters: Boosters) {
        self.failChain = failChain; self.rewards = rewards; self.boosters = boosters
    }

    public static let `default` = MetaRules()

    /// VERIFIED texts/prices research/fail.md §1 (v552, L62): time: "Out of Time!" (+30 sec, Add Time 900) → [streak > x1:
    /// "Continue? You will lose 100 token and your streak!" (Play On 900)] → "Continue? You will lose a life!" (Play On 900)
    /// → Level Failed. hearts: "Out of Lives!" (+3 Lives, Add Lives 900) → the same two "Continue?" steps.
    public static let defaultFailChain: [String: [FailStep]] = [
        ContinueOffer.Kind.outOfTime.rawValue: [
            FailStep(price: 900, grant: .addTime, amount: 30, warning: .none),
            FailStep(price: 900, grant: .addTime, amount: 30, warning: .token, onlyWithStreak: true),
            FailStep(price: 900, grant: .addTime, amount: 30, warning: .life),
        ],
        ContinueOffer.Kind.outOfHearts.rawValue: [
            FailStep(price: 900, grant: .refillHearts, amount: 3, warning: .none),
            FailStep(price: 900, grant: .refillHearts, amount: 3, warning: .token, onlyWithStreak: true),
            FailStep(price: 900, grant: .refillHearts, amount: 3, warning: .life),
        ],
    ]

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); let d = MetaRules()
        failChain = try c.v(.failChain, d.failChain)
        rewards = try c.v(.rewards, d.rewards)
        boosters = try c.v(.boosters, d.boosters)
    }

    /// The chain of `kind` as offered to a player with (`streakActive`) or without a running streak multiplier: steps
    /// that need a streak are dropped when there is none; `isLast` marks the final step.
    public func chain(_ kind: ContinueOffer.Kind, streakActive: Bool) -> [ContinueOffer] {
        let steps = (failChain[kind.rawValue] ?? []).filter { streakActive || !$0.onlyWithStreak }
        return steps.enumerated().map { i, s in
            ContinueOffer(kind: kind, step: i, price: s.price, grant: s.offerGrant, warning: s.warning,
                          isLast: i == steps.count - 1)
        }
    }
}
