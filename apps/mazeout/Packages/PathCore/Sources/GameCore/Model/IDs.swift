import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.3). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests). Real code: identifiers only.
// The string identifiers are open sets: content (levels.json, unlocks.json, tutorials.json, Tuning) may carry ids that
// have no named constant below; the constants are only the ids the architecture already knows.
// Template phase 1: the genre-agnostic ids live here (GameCore); the arrow puzzle's own ids (ArrowID, ObstacleID,
// LevelSource) and its feature constants (FeatureID.linked, .door, …) moved to ArrowEscape/Model/ArrowIDs.swift.

/// A booster. v552 has two (VERIFIED items, PLAN DECISION 02:50): the frozen hourglass and the light bulb.
public struct BoosterID: RawRepresentable, Hashable, Codable, Sendable, CodingKeyRepresentable, ExpressibleByStringLiteral,
                         CustomStringConvertible {
    public let rawValue: String
    public init(rawValue: String) { self.rawValue = rawValue }
    public init(_ raw: String) { rawValue = raw }
    public init(stringLiteral value: String) { rawValue = value }
    public var description: String { rawValue }
    public var codingKey: CodingKey { StringIDKey(rawValue) }
    public init?<T: CodingKey>(codingKey: T) { rawValue = codingKey.stringValue }

    /// Left slot: the frozen hourglass (freezes the level timer).
    public static let freeze = BoosterID("freeze")
    /// Right slot: the light bulb (highlights a free unit).
    public static let hint = BoosterID("hint")
}

/// A feature with a first-time unlock overlay ("Linked Arrows!", "Pipe! Unlocked!", …; unlocks.json `feature`).
public struct FeatureID: RawRepresentable, Hashable, Codable, Sendable, CodingKeyRepresentable, ExpressibleByStringLiteral,
                         CustomStringConvertible {
    public let rawValue: String
    public init(rawValue: String) { self.rawValue = rawValue }
    public init(_ raw: String) { rawValue = raw }
    public init(stringLiteral value: String) { rawValue = value }
    public var description: String { rawValue }
    public var codingKey: CodingKey { StringIDKey(rawValue) }
    public init?<T: CodingKey>(codingKey: T) { rawValue = codingKey.stringValue }
}

/// A tutorial script (tutorials.json `id`).
public struct TutorialID: RawRepresentable, Hashable, Codable, Sendable, CodingKeyRepresentable, ExpressibleByStringLiteral,
                          CustomStringConvertible {
    public let rawValue: String
    public init(rawValue: String) { self.rawValue = rawValue }
    public init(_ raw: String) { rawValue = raw }
    public init(stringLiteral value: String) { rawValue = value }
    public var description: String { rawValue }
    public var codingKey: CodingKey { StringIDKey(rawValue) }
    public init?<T: CodingKey>(codingKey: T) { rawValue = codingKey.stringValue }
}

/// A live-ops style event of the offline world (SPEC-architecture §4.10).
public struct EventID: RawRepresentable, Hashable, Codable, Sendable, CodingKeyRepresentable, ExpressibleByStringLiteral,
                       CustomStringConvertible {
    public let rawValue: String
    public init(rawValue: String) { self.rawValue = rawValue }
    public init(_ raw: String) { rawValue = raw }
    public init(stringLiteral value: String) { rawValue = value }
    public var description: String { rawValue }
    public var codingKey: CodingKey { StringIDKey(rawValue) }
    public init?<T: CodingKey>(codingKey: T) { rawValue = codingKey.stringValue }

    public static let streakRace = EventID("streakRace")
    public static let clawChallenge = EventID("clawChallenge")
    public static let skyJump = EventID("skyJump")
    public static let rocketRace = EventID("rocketRace")
    public static let weeklyContest = EventID("weeklyContest")
}

/// Level difficulty tag. Encodes as its raw value; DECODES every spelling the schemas use:
/// JSON null / "normal" → .normal, "Hard Level" / "hard" / "Hard" → .hard, "Super Hard" / "superHard" → .superHard.
public enum LevelTag: String, Codable, Sendable, CaseIterable {
    case normal, hard, superHard

    /// Any schema spelling (case and spaces ignored); nil for an unknown word.
    public init?(label: String?) {
        guard let label else { self = .normal; return }
        let k = label.lowercased().replacingOccurrences(of: " ", with: "").replacingOccurrences(of: "_", with: "")
        switch k {
        case "", "normal", "null", "none": self = .normal
        case "hard", "hardlevel": self = .hard
        case "superhard", "superhardlevel": self = .superHard
        default: return nil
        }
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .normal; return }
        let s = try c.decode(String.self)
        guard let t = LevelTag(label: s) else {
            throw DecodingError.dataCorruptedError(in: c, debugDescription: "unknown level tag \"\(s)\"")
        }
        self = t
    }
}

/// The coding key of the string identifiers (dictionaries keyed by an ID encode as JSON objects).
public struct StringIDKey: CodingKey, Sendable {
    public let stringValue: String
    public init(_ s: String) { stringValue = s }
    public init?(stringValue: String) { self.stringValue = stringValue }
    public var intValue: Int? { nil }
    public init?(intValue: Int) { return nil }
}
