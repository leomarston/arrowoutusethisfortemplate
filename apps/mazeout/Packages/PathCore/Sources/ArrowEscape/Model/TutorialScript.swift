import Foundation
import GameCore

// C1 (SPEC-architecture §4.3, §8.4 TutorialDirector). One step of Levels/tutorials.json (MF-style steps). G2's
// TutorialDirector plays them; L1 writes the file. Example (VERIFIED tutorials §3, the FTUE's only in-board hint):
//   {"id":"tapToMove","level":1,"stage":0,"trigger":"stageReady","caption":"Tap to move!",
//    "hand":{"arrow":1,"at":[1.0,2.38]},"dismiss":"anyTap","holdTimer":false}
//
// tutorials.json: a bare array, or {"schema":1,"tutorials":[…]}. Unknown keys are ignored; required: id, level.
// `trigger` and `dismiss` are open sets (content may add values the director learns later).

// `TutorialTrigger` / `TutorialDismiss` moved to GameCore (Session/TutorialTypes.swift, template phase 2): the generic
// `TutorialStep` the shell plays uses them too.

/// Where the tutorial hand points: an arrow, and optionally the fingertip in CELL coordinates of the level
/// ([c, r] as fractions; [0, 0] = the centre of cell (0, 0)); nil = the middle of the arrow's path.
public struct TutorialHand: Codable, Sendable, Equatable {
    public var arrow: ArrowID
    public var at: [Double]?
    public init(arrow: ArrowID, at: [Double]? = nil) { self.arrow = arrow; self.at = at }
}

public struct TutorialScript: Codable, Sendable, Equatable {
    public var id: TutorialID
    /// The board's level number (for the "Levels 1-4" session: 1…4).
    public var level: Int
    /// 0-based stage within the session (StageSetup.stage); 0 for a one-board level.
    public var stage: Int
    public var trigger: TutorialTrigger
    /// Strings-table key of the caption ("Tap to move!"), nil = hand only.
    public var caption: String?
    public var hand: TutorialHand?
    public var dismiss: TutorialDismiss
    /// Keep the level timer frozen while the step is up (false for "Tap to move!": the timer starts at the first tap as
    /// always, VERIFIED tutorials §3/§8).
    public var holdTimer: Bool
    /// Input restriction while the step is up; nil = every arrow (the board's `allowedArrows`).
    public var allowedArrows: [ArrowID]?

    public init(id: TutorialID, level: Int, stage: Int = 0, trigger: TutorialTrigger = .stageReady, caption: String? = nil,
                hand: TutorialHand? = nil, dismiss: TutorialDismiss = .anyTap, holdTimer: Bool = false,
                allowedArrows: [ArrowID]? = nil) {
        self.id = id; self.level = level; self.stage = stage; self.trigger = trigger; self.caption = caption
        self.hand = hand; self.dismiss = dismiss; self.holdTimer = holdTimer; self.allowedArrows = allowedArrows
    }

    private enum K: String, CodingKey { case id, level, stage, trigger, caption, hand, dismiss, holdTimer, allowedArrows }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: K.self)
        id = try c.decode(TutorialID.self, forKey: .id)
        level = try c.decode(Int.self, forKey: .level)
        stage = try c.decodeIfPresent(Int.self, forKey: .stage) ?? 0
        trigger = try c.decodeIfPresent(TutorialTrigger.self, forKey: .trigger) ?? .stageReady
        caption = try c.decodeIfPresent(String.self, forKey: .caption)
        hand = try c.decodeIfPresent(TutorialHand.self, forKey: .hand)
        dismiss = try c.decodeIfPresent(TutorialDismiss.self, forKey: .dismiss) ?? .anyTap
        holdTimer = try c.decodeIfPresent(Bool.self, forKey: .holdTimer) ?? false
        allowedArrows = try c.decodeIfPresent([ArrowID].self, forKey: .allowedArrows)
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: K.self)
        try c.encode(id, forKey: .id)
        try c.encode(level, forKey: .level)
        try c.encode(stage, forKey: .stage)
        try c.encode(trigger, forKey: .trigger)
        try c.encodeIfPresent(caption, forKey: .caption)
        try c.encodeIfPresent(hand, forKey: .hand)
        try c.encode(dismiss, forKey: .dismiss)
        try c.encode(holdTimer, forKey: .holdTimer)
        try c.encodeIfPresent(allowedArrows, forKey: .allowedArrows)
    }

    /// tutorials.json in either form.
    public static func decodeList(_ data: Data) throws -> [TutorialScript] {
        let top = try JSONSerialization.jsonObject(with: data)
        if top is [Any] { return try JSONDecoder().decode([TutorialScript].self, from: data) }
        struct Wrapped: Decodable { var schema: Int?; var tutorials: [TutorialScript] }
        let w = try JSONDecoder().decode(Wrapped.self, from: data)
        if let s = w.schema, s > LevelJSON.bundleSchema { throw LevelJSONError.badValue("tutorials schema \(s) is newer than \(LevelJSON.bundleSchema)") }
        return w.tutorials
    }
}

extension TutorialScript {
    /// The generic step the shell's TutorialDirector plays (template phase 2): the hand's arrow and the allowed arrows become
    /// `PuzzleTarget`s (`ArrowID.target`); the fingertip stays in the level's cell coordinates (the board converts it).
    public var step: TutorialStep {
        TutorialStep(id: id, level: level, stage: stage, trigger: trigger, caption: caption,
                     hand: hand.map { TutorialStep.Hand(target: $0.arrow.target, at: $0.at) }, dismiss: dismiss,
                     holdTimer: holdTimer, allowedTargets: allowedArrows.map { $0.map(\.target) })
    }
}
