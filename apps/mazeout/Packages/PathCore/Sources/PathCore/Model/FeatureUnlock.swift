import Foundation

// C1 (SPEC-architecture §4.3, §8.4 UnlockDirector). One row of Levels/unlocks.json: the first Play of `level` shows this
// feature's unlock overlay ("<Title>! / Unlocked! / card", VERIFIED tutorials §6). The texts are strings-table KEYS in
// English (the original's UI is English, D20); which features/levels ship is PENDING-gameplay (L1 writes the file).
//
// unlocks.json: a bare array, or {"schema":1,"unlocks":[…]}:
//   {"feature":"linked","level":7,"title":"Linked Arrows!","card":"LINKED ARROWS move together!",
//    "caps":"LINKED ARROWS","icon":"unlockIconLinked"}

public struct FeatureUnlock: Codable, Sendable, Equatable {
    public var feature: FeatureID
    public var level: Int
    /// "Linked Arrows!", "Pipe!", "Box!" (strings-table key).
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

    /// unlocks.json in either form.
    public static func decodeList(_ data: Data) throws -> [FeatureUnlock] {
        let top = try JSONSerialization.jsonObject(with: data)
        if top is [Any] { return try JSONDecoder().decode([FeatureUnlock].self, from: data) }
        struct Wrapped: Decodable { var schema: Int?; var unlocks: [FeatureUnlock] }
        let w = try JSONDecoder().decode(Wrapped.self, from: data)
        if let s = w.schema, s > LevelJSON.bundleSchema { throw LevelJSONError.badValue("unlocks schema \(s) is newer than \(LevelJSON.bundleSchema)") }
        return w.unlocks
    }
}
