import Foundation

// C1 (SPEC-architecture §4.3, §8.4 UnlockDirector). Moved from ArrowEscape/Model/FeatureUnlock.swift in the kit decoupling
// step (docs/ROADMAP.md): a feature's first-appearance card is generic (any module lists its own in Levels/unlocks.json and
// the shell's UnlockDirector shows it), so the type lives in GameCore. Same members, same JSON. The list reader
// `FeatureUnlock.decodeList` (the bundle schema check) stays with the module that owns the bundle format (ArrowEscape).
// One row of Levels/unlocks.json: the first Play of `level` shows this feature's unlock overlay ("<Title>! / Unlocked! /
// card", VERIFIED tutorials §6). The texts are strings-table KEYS in English (the original's UI is English, D20).
//
// unlocks.json: a bare array, or {"schema":1,"unlocks":[…]}:
//   {"feature":"<id>","level":7,"title":"<Title>!","card":"<CAPS> sentence","caps":"<CAPS>","icon":"<art id>"}

public struct FeatureUnlock: Codable, Sendable, Equatable {
    public var feature: FeatureID
    public var level: Int
    /// The overlay's title (strings-table key).
    public var title: String
    /// The card sentence (strings-table key); `caps` is the part drawn in the blue caps colour.
    public var card: String
    public var caps: String?
    /// Art id of the overlay icon (art/MANIFEST.json).
    public var icon: String?

    public init(feature: FeatureID, level: Int, title: String, card: String, caps: String? = nil, icon: String? = nil) {
        self.feature = feature; self.level = level; self.title = title; self.card = card; self.caps = caps; self.icon = icon
    }

    private enum K: String, CodingKey { case feature, level, title, card, caps, icon }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: K.self)
        feature = try c.decode(FeatureID.self, forKey: .feature)
        level = try c.decode(Int.self, forKey: .level)
        title = try c.decode(String.self, forKey: .title)
        card = try c.decode(String.self, forKey: .card)
        caps = try c.decodeIfPresent(String.self, forKey: .caps)
        icon = try c.decodeIfPresent(String.self, forKey: .icon)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: K.self)
        try c.encode(feature, forKey: .feature)
        try c.encode(level, forKey: .level)
        try c.encode(title, forKey: .title)
        try c.encode(card, forKey: .card)
        try c.encodeIfPresent(caps, forKey: .caps)
        try c.encodeIfPresent(icon, forKey: .icon)
    }
}
