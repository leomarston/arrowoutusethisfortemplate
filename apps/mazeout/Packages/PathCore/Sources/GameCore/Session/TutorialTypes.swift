import Foundation

// C1 (SPEC-architecture §4.3, §8.4 TutorialDirector), moved from ArrowEscape/Model/TutorialScript.swift in template phase 2:
// the open sets of tutorial triggers and dismissals (content may add values the director learns later). Generic: the
// module's tutorial data (ArrowEscape's `TutorialScript`) and the shell's `TutorialStep` share them.

public struct TutorialTrigger: RawRepresentable, Hashable, Codable, Sendable, ExpressibleByStringLiteral {
    public let rawValue: String
    public init(rawValue: String) { self.rawValue = rawValue }
    public init(stringLiteral value: String) { rawValue = value }
    /// The stage's board is built and the intro finished (the timer is still frozen).
    public static let stageReady = TutorialTrigger(rawValue: "stageReady")
    /// Right after the player's first tap of the stage.
    public static let firstTap = TutorialTrigger(rawValue: "firstTap")
    /// After the unlock overlay of the level is dismissed.
    public static let afterUnlock = TutorialTrigger(rawValue: "afterUnlock")
}

public struct TutorialDismiss: RawRepresentable, Hashable, Codable, Sendable, ExpressibleByStringLiteral {
    public let rawValue: String
    public init(rawValue: String) { self.rawValue = rawValue }
    public init(stringLiteral value: String) { rawValue = value }
    /// The first accepted move on ANY target dismisses it (Arrow Out's "Tap to move!": no input restriction observable).
    public static let anyTap = TutorialDismiss(rawValue: "anyTap")
    /// Only a move on the hand's target (input restricted to it).
    public static let targetTap = TutorialDismiss(rawValue: "targetTap")
    /// A tap anywhere on the screen.
    public static let tapAnywhere = TutorialDismiss(rawValue: "tapAnywhere")
}
