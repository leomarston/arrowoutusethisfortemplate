import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.3). Moved from ArrowEscape/Model/LevelSpec.swift (+ its JSON mapping from
// ArrowEscape/Model/LevelJSON.swift `LevelCoding.decodeSession` / `encode(_: SessionPlan, to:)`) in the kit decoupling step
// (docs/ROADMAP.md): a Play = a session of 1…n stages is generic, so the shell's game loop and every puzzle module name it
// from GameCore, not from the reference puzzle. Same type, same members, same JSON (sessions.json keys, key order, the
// "≥ 1 level" rule, `hearts` defaulting to "carry"): the move is source compatible through `import PathCore` / `GameCore`.
//
// sessions.json session: id, levels, hud_label?, panel_label?, reward?, stage_gap_s?, hearts ("carry" | "reset", default carry)

/// Whether hearts reset or carry between the stages of a multi-board session (PENDING-gameplay; default .carry).
public enum HeartsCarry: String, Codable, Sendable, CaseIterable { case reset, carry }

/// One Play = one session = 1…n stages (sessions.json; a level in no session is a one-stage session).
public struct SessionPlan: Codable, Sendable, Equatable {
    public var id: String
    public var levels: [Int]                      // [1, 2, 3, 4] (VERIFIED tutorials §2) or [n]
    public var hudLabel: String?                  // "Levels 1-4" (else "Level %lld"); a strings-table KEY, not display text
    public var panelLabel: String?                // "Level 1-4" (singular on the win panel, VERIFIED); a strings-table KEY
    public var reward: Int?                       // 80 (VERIFIED); nil = by tag
    public var stageGap: Double?                  // last clear → next board built: 0.7 s (VERIFIED tutorials §2)
    public var hearts: HeartsCarry                // PENDING-gameplay (no heart was lost in V1); default .carry

    public init(id: String, levels: [Int], hudLabel: String? = nil, panelLabel: String? = nil, reward: Int? = nil,
                stageGap: Double? = nil, hearts: HeartsCarry = .carry) {
        self.id = id; self.levels = levels; self.hudLabel = hudLabel; self.panelLabel = panelLabel
        self.reward = reward; self.stageGap = stageGap; self.hearts = hearts
    }

    /// The sessions.json key names (snake_case, as the bundle writes them).
    private struct Key: CodingKey, ExpressibleByStringLiteral {
        let stringValue: String
        init(stringLiteral value: String) { stringValue = value }
        init?(stringValue: String) { self.stringValue = stringValue }
        var intValue: Int? { nil }
        init?(intValue: Int) { return nil }
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Key.self)
        let levels = try c.decode([Int].self, forKey: "levels")
        guard !levels.isEmpty else {
            throw DecodingError.dataCorruptedError(forKey: "levels", in: c, debugDescription: "a session needs ≥ 1 level")
        }
        self.init(id: try c.decode(String.self, forKey: "id"),
                  levels: levels,
                  hudLabel: try c.decodeIfPresent(String.self, forKey: "hud_label"),
                  panelLabel: try c.decodeIfPresent(String.self, forKey: "panel_label"),
                  reward: try c.decodeIfPresent(Int.self, forKey: "reward"),
                  stageGap: try c.decodeIfPresent(Double.self, forKey: "stage_gap_s"),
                  hearts: try c.decodeIfPresent(HeartsCarry.self, forKey: "hearts") ?? .carry)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: Key.self)
        try c.encode(id, forKey: "id")
        try c.encode(levels, forKey: "levels")
        try c.encodeIfPresent(hudLabel, forKey: "hud_label")
        try c.encodeIfPresent(panelLabel, forKey: "panel_label")
        try c.encodeIfPresent(reward, forKey: "reward")
        try c.encodeIfPresent(stageGap, forKey: "stage_gap_s")
        try c.encode(hearts, forKey: "hearts")
    }
}
