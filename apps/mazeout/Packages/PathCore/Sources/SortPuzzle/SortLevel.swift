import Foundation
import GameCore

// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §6b): the second puzzle module, a colour-sorting puzzle written only
// against GameCore's contract. Tubes hold coloured units (bottom → top, colour indices 0 ..< colors); the player picks a
// source tube, then a target; the source's top run (the same colour) pours onto an empty tube or onto its own colour, as
// many units as fit. A level is won when every tube is empty or full of one colour. No timer, no hearts: the one way to
// fail is "stuck" (no legal pour left), which opens the config's `stuck` fail chain (default: an extra empty tube).
// Original design: the levels are generated from a seed (SortGenerator), the colours are the skin's tokens.

/// One board: `tubes[i]` bottom → top, every colour exactly `capacity` times.
public struct SortLevel: Codable, Sendable, Equatable {
    public var level: Int
    public var tag: LevelTag
    /// Units per tube (every tube, extra tubes too).
    public var capacity: Int
    public var colors: Int
    public var tubes: [[Int]]

    public init(level: Int, tag: LevelTag, capacity: Int, colors: Int, tubes: [[Int]]) {
        self.level = level; self.tag = tag; self.capacity = capacity; self.colors = colors; self.tubes = tubes
    }

    /// For the logs ("5 colours, 7 tubes").
    public var summary: String { "\(colors) colours, \(tubes.count) tubes" }

    /// The text the golden hash is taken over (tools/sortpuzzle/ref.py `canonical`):
    /// "<level>|<tag>|c<capacity>|k<colors>|" + the tubes joined by "/", their units by ",".
    public var canonical: String {
        "\(level)|\(tag.rawValue)|c\(capacity)|k\(colors)|"
            + tubes.map { t in t.map { u in String(u) }.joined(separator: ",") }.joined(separator: "/")
    }
}

/// The module's own rules (App/Resources/Tuning/sort.json; the board's section is the app's). Tolerant decoding: a missing
/// key keeps its default, and the defaults below ARE the shipped file (SortPuzzleTests checks it).
public struct SortRules: Codable, Sendable, Equatable {

    /// One step of the difficulty curve: from level `from` on (until the next band).
    public struct Band: Codable, Sendable, Equatable {
        public var from: Int
        public var colors: Int
        public var capacity: Int
        /// Empty tubes dealt with the level.
        public var empty: Int

        public init(from: Int, colors: Int, capacity: Int, empty: Int) {
            self.from = from; self.colors = colors; self.capacity = capacity; self.empty = empty
        }
    }

    /// The generator (SortGenerator; tools/sortpuzzle/ref.py mirrors it).
    public struct Levels: Codable, Sendable, Equatable {
        /// PathRandom.levelSeed(level:salt:): the same board for every player.
        public var salt: UInt64 = 20_260_930
        /// Deals tried before the last-resort deal (one empty tube per colour).
        public var maxAttempts: Int = 48
        /// States the solver may expand to accept a deal.
        public var solverBudget: Int = 20_000
        /// Every n-th level is tagged hard / super hard (0 = never); super hard wins a tie.
        public var hardEvery: Int = 10
        public var superHardEvery: Int = 25
        public var curve: [Band] = Levels.defaultCurve

        public static let defaultCurve: [Band] = [
            Band(from: 1, colors: 3, capacity: 4, empty: 2), Band(from: 4, colors: 4, capacity: 4, empty: 2),
            Band(from: 9, colors: 5, capacity: 4, empty: 2), Band(from: 16, colors: 6, capacity: 4, empty: 2),
            Band(from: 26, colors: 7, capacity: 4, empty: 2), Band(from: 40, colors: 8, capacity: 4, empty: 2),
            Band(from: 60, colors: 9, capacity: 4, empty: 2), Band(from: 85, colors: 10, capacity: 4, empty: 2),
        ]

        public init() {}

        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Levels()
            salt = try c.v(.salt, d.salt)
            maxAttempts = try c.v(.maxAttempts, d.maxAttempts)
            solverBudget = try c.v(.solverBudget, d.solverBudget)
            hardEvery = try c.v(.hardEvery, d.hardEvery)
            superHardEvery = try c.v(.superHardEvery, d.superHardEvery)
            let bands = try c.v(.curve, d.curve)
            curve = bands.isEmpty ? d.curve : bands
        }

        /// The band of `level`: the last one starting at or before it (the first band below its start).
        public func band(for level: Int) -> Band {
            var pick = curve.first ?? Levels.defaultCurve[0]
            for b in curve where b.from <= level { pick = b }
            return pick
        }

        public func tag(for level: Int) -> LevelTag {
            if superHardEvery > 0 && level % superHardEvery == 0 { return .superHard }
            if hardEvery > 0 && level % hardEvery == 0 { return .hard }
            return .normal
        }
    }

    /// In-play numbers.
    public struct Play: Codable, Sendable, Equatable {
        /// States the solver may expand for a hint (bots, debug jumps).
        public var hintBudget: Int = 20_000
        /// Extra-tube boosters per stage (the fail chain's extra tubes do not count).
        public var maxExtraTubes: Int = 2

        public init() {}

        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Play()
            hintBudget = try c.v(.hintBudget, d.hintBudget)
            maxExtraTubes = try c.v(.maxExtraTubes, d.maxExtraTubes)
        }
    }

    public var levels = Levels()
    public var play = Play()
    /// This module's fail chains (ContinueOffer.Kind raw value → steps). rules.json `failChain` wins for a kind it lists
    /// (`meta(over:)`); the default is the `stuck` chain: three steps, each an extra empty tube.
    public var failChain: [String: [MetaRules.FailStep]] = SortRules.defaultFailChain

    public static let defaultFailChain: [String: [MetaRules.FailStep]] = [
        ContinueOffer.Kind.stuck.rawValue: [
            MetaRules.FailStep(price: 900, grant: .none, amount: 1, warning: .none, action: SortPuzzleModule.extraTubeAction),
            MetaRules.FailStep(price: 900, grant: .none, amount: 1, warning: .token, onlyWithStreak: true,
                               action: SortPuzzleModule.extraTubeAction),
            MetaRules.FailStep(price: 900, grant: .none, amount: 1, warning: .life, action: SortPuzzleModule.extraTubeAction),
        ],
    ]

    public static let `default` = SortRules()

    public init() {}

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); let d = SortRules()
        levels = try c.v(.levels, d.levels)
        play = try c.v(.play, d.play)
        failChain = try c.v(.failChain, d.failChain)
    }

    /// Decodes sort.json (nil or empty = the defaults). Never throws: an undecodable file gives the defaults and the problem.
    public static func load(json: Data?) -> (rules: SortRules, problems: [String]) {
        guard let json, !json.isEmpty else { return (SortRules(), []) }
        do {
            return (try JSONDecoder().decode(SortRules.self, from: json), [])
        } catch {
            return (SortRules(), ["sort.json: \(error)"])
        }
    }

    /// The meta rules a session uses: `base` (rules.json) plus this module's fail chains for the kinds `base` has none of.
    public func meta(over base: MetaRules) -> MetaRules {
        var m = base
        for (kind, steps) in failChain where m.failChain[kind] == nil { m.failChain[kind] = steps }
        return m
    }
}
