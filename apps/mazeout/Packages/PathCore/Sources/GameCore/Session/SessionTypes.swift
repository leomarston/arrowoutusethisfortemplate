import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.5). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests). C2 implements the state machine (LevelSession,
// LevelClock) in its own files against these types.

/// The session's state machine (§4.5 diagram). Stages are 0-based.
public enum Phase: Equatable, Sendable {
    case intro(stage: Int)                 // the board builds in; the timer is frozen at the stage's limit
    case ready(stage: Int)                 // built; the timer shows its limit, frozen until the FIRST tap
    case playing(stage: Int)
    case stageClear(stage: Int)            // multi-board sessions: waiting for the stage transition ack
    case offer(ContinueOffer)              // a fail-chain step is up
    case won(WinResult)
    case lost(LossReason)
}

/// Why the level clock is held. Holds stack; the clock runs only with no hold (§4.6).
public enum HoldReason: String, Hashable, Codable, Sendable, CaseIterable {
    case intro, stageTransition, tutorial, unlockOverlay, popup, pause, offer, background, winSequence
}

/// Everything a session needs besides the boards.
public struct AttemptSetup: Codable, Sendable, Equatable {
    public var levels: [Int]                     // the session's levels
    public var attemptIndex: Int                 // 1-based count of starts of this session (first try = 1 with no loss)
    public var seed: UInt64                      // combo/hint tie-breaks only (the boards are fixed data)
    public var boosters: [BoosterID: Int]        // stock snapshot (the caller owns stock)
    public var firstStage: Int                   // 0, or -pc.stage

    public init(levels: [Int], attemptIndex: Int = 1, seed: UInt64 = 0, boosters: [BoosterID: Int] = [:], firstStage: Int = 0) {
        self.levels = levels; self.attemptIndex = attemptIndex; self.seed = seed; self.boosters = boosters
        self.firstStage = firstStage
    }
}

/// One step of a fail chain (RulesTuning.failChain, §4.5). The caller charges `price` before `acceptContinue()`.
public struct ContinueOffer: Codable, Sendable, Equatable {
    public enum Kind: String, Codable, Sendable, CaseIterable { case outOfTime, outOfHearts }
    public enum Grant: Codable, Sendable, Equatable { case addTime(Int), refillHearts(Int), none }
    public enum Warning: String, Codable, Sendable, CaseIterable { case none, streak, token, life }

    public var kind: Kind
    public var step: Int                         // 0-based position in the chain
    public var price: Int                        // coins (900 every step seen)
    public var grant: Grant
    public var warning: Warning
    public var isLast: Bool                      // declining it loses the level

    public init(kind: Kind, step: Int, price: Int, grant: Grant, warning: Warning = .none, isLast: Bool = false) {
        self.kind = kind; self.step = step; self.price = price; self.grant = grant; self.warning = warning
        self.isLast = isLast
    }
}

/// A won session (the win is banked at the tap, §4.5).
public struct WinResult: Codable, Sendable, Equatable {
    public var levels: [Int]
    public var tag: LevelTag
    public var timeLeft: Int
    public var heartsLeft: Int
    public var firstTry: Bool
    public var reward: Int
    public var bumps: Int

    public init(levels: [Int], tag: LevelTag, timeLeft: Int, heartsLeft: Int, firstTry: Bool, reward: Int, bumps: Int) {
        self.levels = levels; self.tag = tag; self.timeLeft = timeLeft; self.heartsLeft = heartsLeft
        self.firstTry = firstTry; self.reward = reward; self.bumps = bumps
    }
}

public enum LossReason: String, Codable, Sendable, CaseIterable { case timeUp, hearts, quit, killed }

/// A timer alert near 0 (thresholds PENDING-gameplay; the configured list is empty by default).
public enum TimerAlert: Codable, Sendable, Equatable { case threshold(Int) }

public enum TimeCause: String, Codable, Sendable, CaseIterable { case continueOffer, booster }
