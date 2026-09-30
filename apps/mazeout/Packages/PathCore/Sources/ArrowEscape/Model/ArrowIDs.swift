import Foundation
import GameCore

// ◆ CONTRACT (SPEC-architecture §3.5, §4.3), split out of GameCore/Model/IDs.swift in template phase 1: the identifiers
// that belong to the arrow puzzle (ArrowEscape). FROZEN like IDs.swift (APISurfaceTests).

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

/// The arrow puzzle's features with a first-time unlock overlay (FeatureID is GameCore's open set).
extension FeatureID {
    public static let linked = FeatureID("linked")       // taped bundles (VERIFIED tutorials §6, V1 L7)
    public static let door = FeatureID("door")           // doors + keys
    public static let pipe = FeatureID("pipe")
    public static let box = FeatureID("box")             // phone skin
    public static let curtain = FeatureID("curtain")     // video V1 skin
    public static let elevator = FeatureID("elevator")
    public static let corner = FeatureID("corner")
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
