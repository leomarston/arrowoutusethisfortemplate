import Foundation
import GameCore

// C2 (SPEC-architecture §4.4–§4.9, §14). Every rule knob of the core as DATA: compiled defaults here, overridable by
// `bundle/Tuning/rules.json` (GAME: `tuning.rules.decode(RulesTuning.self)`, or `RulesTuning.load(json:overrides:)` to
// apply the `-pc.tune rules.<key>=v` pairs as well). Decoding is tolerant: a missing key keeps its default, an unknown key
// is ignored (`RulesTuning.unknownKeys(in:)` lists them), so a content-spec edit never crashes the app.
//
// Tags on each default: VERIFIED (source) · INFERRED · DECISION · PENDING-<spec> (the content spec replaces the value).

public struct RulesTuning: Codable, Sendable, Equatable {

    // MARK: tape (Linked Arrows, §4.4)

    /// What a tap on a taped bundle does when at least one member's ray is blocked.
    public enum TapeBlockedPolicy: String, Codable, Sendable, CaseIterable {
        /// The whole bundle slides toward the first contact and back; every member turns red; ONE heart.
        /// VERIFIED for "every ray blocked" (research/fail.md §3, META-L062-tape-blocked-bump); the some-clear case is
        /// PENDING-gameplay and follows the same unit rule by default (the bundle always moves as one).
        case bundleBumps
        /// The tapped member bumps alone (the architecture's first placeholder, §4.4).
        case tappedBumps
    }

    public struct Tape: Codable, Sendable, Equatable {
        public var blockedPolicy: TapeBlockedPolicy = .bundleBumps
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Tape()
            blockedPolicy = try c.v(.blockedPolicy, d.blockedPolicy)
        }
    }

    // MARK: bump (§4.4, §4.5, §5.5)

    public struct Bump: Codable, Sendable, Equatable {
        /// A blocked arrow that is ALREADY red (bumped before) bumps again but costs no heart. VERIFIED 1 clean observation
        /// (research/fail.md §3, 05:33); PENDING-gameplay.
        public var repeatOnMarkedCostsHeart: Bool = false
        /// The first bump starts the level timer like a first successful tap. VERIFIED (research/fail.md §3, 05:22).
        public var startsTimer: Bool = true
        /// Contact geometry: the head apex stops at the blocker's stroke edge. An arrow blocker's edge sits this far before
        /// its cell centre (half the stroke, Metrics.stroke / 2 = 0.11 cells); VERIFIED: gap 0 → ≈ 0.5 cell of travel
        /// (fail.md §3), bump-1 3 empty cells → 3.5 cells (motion.md §4).
        public var arrowEdgeInset: Double = 0.11
        /// An obstacle blocker (door, box, pipe tube, corner side) starts at its cell's near edge (DECISION: sprites fill
        /// their cells).
        public var obstacleEdgeInset: Double = 0.5
        /// Per-direction head apex past the head cell centre (cells); nil = `Metrics.headApexPast(_:)` (C1, STYLE §A).
        public var apexPast: [String: Double]? = nil
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Bump()
            repeatOnMarkedCostsHeart = try c.v(.repeatOnMarkedCostsHeart, d.repeatOnMarkedCostsHeart)
            startsTimer = try c.v(.startsTimer, d.startsTimer)
            arrowEdgeInset = try c.v(.arrowEdgeInset, d.arrowEdgeInset)
            obstacleEdgeInset = try c.v(.obstacleEdgeInset, d.obstacleEdgeInset)
            apexPast = try c.decodeIfPresent([String: Double].self, forKey: .apexPast) ?? d.apexPast
        }

        /// The head apex past the head cell centre for a head travelling `d` (cells).
        public func apex(_ d: Dir) -> Double { apexPast?[d.rawValue] ?? Metrics.headApexPast(d) }
    }

    // MARK: pipe (§4.4)

    /// When a pipe's visible counter changes (RULED: CONSISTENCY O-15, SPEC-gameplay §3.6, SPEC-motion-audio §13.4).
    public enum PipeCountMoment: String, Codable, Sendable, CaseIterable { case enter, leave }

    public struct Pipe: Codable, Sendable, Equatable {
        /// PlanBeat.pipeCount at the head entering the mouth or leaving the far mouth (default, O-15; SPEC.md §5 item 29).
        public var countAt: PipeCountMoment = .leave
        /// A pipe with no counter in the data never breaks (DECISION: the phone JSON carries none; levels.json supplies them).
        public var missingCounterIsUnlimited: Bool = true
        /// A ray that passes a pipe and is blocked after the far mouth is a bump that consumes nothing (DECISION,
        /// PENDING-gameplay).
        public var bumpConsumes: Bool = false
        /// Loop guard for chained pipes: after this many tube passages in one ray the ray is blocked by the pipe.
        public var maxHops: Int = 16
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Pipe()
            countAt = try c.v(.countAt, d.countAt)
            missingCounterIsUnlimited = try c.v(.missingCounterIsUnlimited, d.missingCounterIsUnlimited)
            bumpConsumes = try c.v(.bumpConsumes, d.bumpConsumes)
            maxHops = try c.v(.maxHops, d.maxHops)
        }
    }

    // MARK: box / curtain (§4.4)

    /// When a box counter ticks: at the tap (VERIFIED: the L50 box shattered on the tapped arrow's first-motion frame,
    /// motion.md §3.1) or when the arrow's head leaves the grid.
    public enum BoxCountMoment: String, Codable, Sendable, CaseIterable { case tap, leave }

    public struct Box: Codable, Sendable, Equatable {
        public var countAt: BoxCountMoment = .tap
        /// A box/curtain with no counter in the data never breaks (DECISION, as for pipes).
        public var missingCounterIsUnlimited: Bool = true
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Box()
            countAt = try c.v(.countAt, d.countAt)
            missingCounterIsUnlimited = try c.v(.missingCounterIsUnlimited, d.missingCounterIsUnlimited)
        }
    }

    // MARK: elevator (§4.4)

    public struct Elevator: Codable, Sendable, Equatable {
        /// Empty platform cells block rays (INFERRED: they do not; PENDING-gameplay).
        public var emptyCellsBlock: Bool = false
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Elevator()
            emptyCellsBlock = try c.v(.emptyCellsBlock, d.emptyCellsBlock)
        }
    }

    // MARK: hit test (§4.2, §5.3) — read by BOARD/GAME; the core does not hit-test

    public struct Hit: Codable, Sendable, Equatable {
        /// Screen-space tolerance around a stroke (pt). RULED 22 pt (SPEC-gameplay §2.2, CONSISTENCY G-5; SPEC.md §5 item
        /// 29) from VERIFIED ≥ 15 pt (research/levels.md L47 probe c) and 12-22 pt video taps; board.json input.hitRadiusPt.
        public var radiusPt: Double = 22
        /// VERIFIED once: the exact midpoint between two strokes sent the right-hand one (levels.md L52).
        public var tieBreak: TieBreak = .rightThenDown
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Hit()
            radiusPt = try c.v(.radiusPt, d.radiusPt)
            tieBreak = try c.v(.tieBreak, d.tieBreak)
        }
    }

    // MARK: combo ladder (§4.7)

    public struct Combo: Codable, Sendable, Equatable {
        /// A tap within this many seconds of the previous exit tap continues the streak. INFERRED motion.md §3.4 (84 % over
        /// 1630 video taps at 1.20–1.25 s); v552 check VERIFIED (taps 0.58 / 0.75 s apart → blue, blue, violet).
        public var window: Double = 1.25
        /// A bump resets the streak (PENDING-motion-audio, clips-needed #10).
        public var bumpBreaks: Bool = true
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Combo()
            window = try c.v(.window, d.window)
            bumpBreaks = try c.v(.bumpBreaks, d.bumpBreaks)
        }
    }

    // MARK: clock (§4.6)

    public struct Clock: Codable, Sendable, Equatable {
        /// Seconds at which `.timerAlert(.threshold(n))` fires (PENDING-gameplay/motion-audio, clips-needed #3).
        public var alerts: [Int] = []
        /// A tap on an empty board point starts the timer (DECISION: no; only an arrow tap — exit or bump — does).
        public var emptyTapStartsTimer: Bool = false
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Clock()
            alerts = try c.v(.alerts, d.alerts)
            emptyTapStartsTimer = try c.v(.emptyTapStartsTimer, d.emptyTapStartsTimer)
        }
    }

    // MARK: session (§4.5)

    public struct Session: Codable, Sendable, Equatable {
        /// Holds during which an arrow tap is ignored as `.inputLocked` (the tutorial hold keeps input: "Tap to move!").
        public var inputLockingHolds: [HoldReason] = [.intro, .stageTransition, .unlockOverlay, .popup, .pause, .offer,
                                                      .background, .winSequence]
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Session()
            inputLockingHolds = try c.v(.inputLockingHolds, d.inputLockingHolds)
        }
    }

    // MARK: fail chain, rewards, boosters (§4.5, §4.8, §4.9) — template phase 1: the meta half of this table

    // The shell's knobs (fail chain, win rewards, booster actions) are `MetaRules` (GameCore), which the economy reads;
    // this table keeps the same rules.json keys (`failChain`, `rewards`, `boosters`) and the same Swift names.
    public typealias StepGrant = MetaRules.StepGrant
    public typealias FailStep = MetaRules.FailStep
    public typealias Rewards = MetaRules.Rewards
    public typealias BoosterAction = MetaRules.BoosterAction
    public typealias HintPolicy = MetaRules.HintPolicy
    public typealias Boosters = MetaRules.Boosters

    // MARK: the whole table

    public var tape = Tape()
    public var bump = Bump()
    public var pipe = Pipe()
    public var box = Box()
    public var elevator = Elevator()
    public var hit = Hit()
    public var combo = Combo()
    public var clock = Clock()
    public var session = Session()
    /// ContinueOffer.Kind raw value → the chain, in order. VERIFIED texts/prices research/fail.md §1 (v552, L62):
    /// time: "Out of Time!" (+30 sec, Add Time 900) → [streak > x1: "Continue? You will lose 100 token and your streak!"
    /// (Play On 900)] → "Continue? You will lose a life!" (Play On 900) → Level Failed.
    /// hearts: "Out of Lives!" (+3 Lives, Add Lives 900) → the same two "Continue?" steps.
    /// What "Play On" grants on the later steps: PENDING-gameplay (DECISION: the same grant as the first step).
    public var failChain: [String: [FailStep]] = RulesTuning.defaultFailChain
    public var rewards = Rewards()
    public var boosters = Boosters()

    public init() {}

    public static let `default` = RulesTuning()

    public static let defaultFailChain: [String: [FailStep]] = MetaRules.defaultFailChain

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); let d = RulesTuning()
        tape = try c.v(.tape, d.tape)
        bump = try c.v(.bump, d.bump)
        pipe = try c.v(.pipe, d.pipe)
        box = try c.v(.box, d.box)
        elevator = try c.v(.elevator, d.elevator)
        hit = try c.v(.hit, d.hit)
        combo = try c.v(.combo, d.combo)
        clock = try c.v(.clock, d.clock)
        session = try c.v(.session, d.session)
        failChain = try c.v(.failChain, d.failChain)
        rewards = try c.v(.rewards, d.rewards)
        boosters = try c.v(.boosters, d.boosters)
    }

    /// The chain of `kind` as offered to a player with (`streakActive`) or without a running streak multiplier: steps
    /// that need a streak are dropped when there is none; `isLast` marks the final step (`MetaRules.chain`).
    public func chain(_ kind: ContinueOffer.Kind, streakActive: Bool) -> [ContinueOffer] {
        meta.chain(kind, streakActive: streakActive)
    }

    /// The meta half of this table (fail chain, rewards, boosters) as GameCore's `MetaRules`.
    public var meta: MetaRules {
        get { MetaRules(failChain: failChain, rewards: rewards, boosters: boosters) }
        set { failChain = newValue.failChain; rewards = newValue.rewards; boosters = newValue.boosters }
    }

    // MARK: loading

    /// Decodes `json` (nil or empty = the defaults) after applying dotted overrides (`"combo.window": "1.2"`, the
    /// `-pc.tune rules.combo.window=1.2` pairs without the "rules." prefix; list values separated by ';'). Returns the
    /// defaults and the problem when the result does not decode (never throws, never crashes the caller).
    public static func load(json: Data?, overrides: [String: String] = [:]) -> (rules: RulesTuning, problems: [String]) {
        var problems: [String] = []
        var obj: [String: Any] = [:]
        if let json, !json.isEmpty {
            if let o = (try? JSONSerialization.jsonObject(with: json)) as? [String: Any] { obj = o } else {
                problems.append("rules.json is not a JSON object: defaults apply")
            }
        }
        for (key, raw) in overrides.sorted(by: { $0.key < $1.key }) {
            let parts = key.split(separator: ".").map(String.init)
            guard !parts.isEmpty else { continue }
            obj = setPath(obj, parts[...], overrideValue(raw))
        }
        do {
            let data = try JSONSerialization.data(withJSONObject: obj)
            return (try JSONDecoder().decode(RulesTuning.self, from: data), problems)
        } catch {
            problems.append("rules.json does not decode: \(error)")
            return (RulesTuning(), problems)
        }
    }

    /// Top-level and nested keys of `json` that the table does not know (reported, never applied).
    public static func unknownKeys(in json: Data) -> [String] {
        guard let over = (try? JSONSerialization.jsonObject(with: json)) as? [String: Any],
              let base = (try? JSONSerialization.jsonObject(with: JSONEncoder().encode(RulesTuning()))) as? [String: Any]
        else { return [] }
        var out: [String] = []
        func walk(_ o: [String: Any], _ b: [String: Any], _ path: String) {
            for (k, v) in o where !k.hasPrefix("_") {
                guard let bv = b[k] else { out.append(path + k); continue }
                // dictionaries keyed by data (failChain, boosters.actions) are open maps: do not descend
                if path.isEmpty && k == "failChain" { continue }
                if path == "boosters." && k == "actions" { continue }
                if let ov = v as? [String: Any], let bo = bv as? [String: Any] { walk(ov, bo, path + k + ".") }
            }
        }
        walk(over, base, "")
        return out.sorted()
    }

    static func overrideValue(_ raw: String) -> Any { TuningJSON.overrideValue(raw) }

    static func setPath(_ obj: [String: Any], _ parts: ArraySlice<String>, _ value: Any) -> [String: Any] {
        TuningJSON.setPath(obj, parts, value)
    }
}
