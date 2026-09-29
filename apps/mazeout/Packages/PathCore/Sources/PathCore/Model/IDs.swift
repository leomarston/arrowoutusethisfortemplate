import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.3). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests). Real code: identifiers only.
// The string identifiers are open sets: content (levels.json, unlocks.json, tutorials.json, Tuning) may carry ids that
// have no named constant below; the constants are only the ids the architecture already knows.

/// An arrow of one level. JSON: the number in `"id"`.
public struct ArrowID: Hashable, Comparable, Codable, Sendable, CustomStringConvertible {
    public let raw: Int
    public init(_ raw: Int) { self.raw = raw }
    public static func < (a: ArrowID, b: ArrowID) -> Bool { a.raw < b.raw }
    public var description: String { "a\(raw)" }
    public init(from decoder: Decoder) throws { raw = try decoder.singleValueContainer().decode(Int.self) }
    public func encode(to encoder: Encoder) throws { var c = encoder.singleValueContainer(); try c.encode(raw) }
}

/// An obstacle of one level: "t0" tape, "d0" door, "k0" key, "p0" pipe, "b0" box, "c0" curtain, "e0" elevator,
/// "x0" corner (the prefix is a convention, the kind lives in `ObstacleSpec.kind`).
public struct ObstacleID: Hashable, Comparable, Codable, Sendable, CodingKeyRepresentable, ExpressibleByStringLiteral,
                          CustomStringConvertible {
    public let raw: String
    public init(_ raw: String) { self.raw = raw }
    public init(stringLiteral value: String) { raw = value }
    public static func < (a: ObstacleID, b: ObstacleID) -> Bool { a.raw < b.raw }
    public var description: String { raw }
    public init(from decoder: Decoder) throws { raw = try decoder.singleValueContainer().decode(String.self) }
    public func encode(to encoder: Encoder) throws { var c = encoder.singleValueContainer(); try c.encode(raw) }
    public var codingKey: CodingKey { StringIDKey(raw) }
    public init?<T: CodingKey>(codingKey: T) { raw = codingKey.stringValue }
}

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

    public static let linked = FeatureID("linked")       // taped bundles (VERIFIED tutorials §6, V1 L7)
    public static let door = FeatureID("door")           // doors + keys
    public static let pipe = FeatureID("pipe")
    public static let box = FeatureID("box")             // phone skin
    public static let curtain = FeatureID("curtain")     // video V1 skin
    public static let elevator = FeatureID("elevator")
    public static let corner = FeatureID("corner")
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

/// Where a level's content comes from (SPEC.md §5 item 7).
/// FIX-3 B (SPEC.md ruling 55(c), V1A-G8-3; contract amend 7): the case names are neutral, and so are the raw values the
/// iOS app compiles — the store binary names no way a board was made (its case names ship as reflection metadata, its
/// raw values as literals). The content pipeline's own spellings ("recorded" / "video": design/levels.json, research/,
/// lvtool, pclevels and the Python tools read and write them) are the raw values of the macOS build only (PC_RESEARCH,
/// Package.swift), so every content file and tool output stays byte for byte what it was. The shipped levels carry no
/// "source" (FIX-2 B, N-01) and decode as .designed.
public enum LevelSource: String, Codable, Sendable, CaseIterable {
    #if PC_RESEARCH
    case authored = "recorded"  // read on the owner's phone (v552), L32…L61
    case crafted = "video"      // read from the owner's videos, L1…L31 (+ the substitutes and spares)
    #else
    case authored
    case crafted
    #endif
    case designed     // authored in design/levels.json in the recorded curve
    case generated    // made at runtime by the solver-gated generator
}

/// The coding key of the string identifiers (dictionaries keyed by an ID encode as JSON objects).
public struct StringIDKey: CodingKey, Sendable {
    public let stringValue: String
    public init(_ s: String) { stringValue = s }
    public init?(stringValue: String) { self.stringValue = stringValue }
    public var intValue: Int? { nil }
    public init?(intValue: Int) { return nil }
}
