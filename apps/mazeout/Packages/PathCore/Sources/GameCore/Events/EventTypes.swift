import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.10). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests).
// C3 implements the event state machines (EventsState and friends, in its own files) against these types; the opponents
// come from the social world (SOC1) behind `RivalProvider`, so C3 is testable with a stub provider.
// `Grant`, `EventInstance` and `SkyJumpRun` are C3's types (Economy/Grant.swift, Events/EventsState.swift).

/// What a won session tells the event hooks.
public struct WinContext: Sendable, Equatable {
    public var levels: [Int]
    public var tag: LevelTag
    public var firstTry: Bool
    public var now: Date

    public init(levels: [Int], tag: LevelTag, firstTry: Bool, now: Date) {
        self.levels = levels; self.tag = tag; self.firstTry = firstTry; self.now = now
    }
}

/// What a lost session tells the event hooks.
public struct LossContext: Sendable, Equatable {
    public var levels: [Int]
    public var reason: LossReason
    public var now: Date

    public init(levels: [Int], reason: LossReason, now: Date) {
        self.levels = levels; self.reason = reason; self.now = now
    }
}

/// One visible consequence of a finished attempt for the events (the post-level screens and banners read these).
public enum EventOutcome: Codable, Sendable, Equatable {
    case multiplier(from: Int, to: Int)                 // x1 x5 x10 x25 x100
    case clawPoints(added: Int, total: Int, target: Int)
    case clawStep(step: Int, reward: Grant)
    case streakRaceScore(Int)
    case skyJumpProgress(levels: Int, of: Int)
    case skyJumpWon(share: Int, winners: Int)
    case skyJumpFailed
    case rocketProgress(mine: Int)
    case rocketFinished(rank: Int, reward: Grant?)
    case weeklyScore(Int)
    case grant(Grant)
    // Balloon Rise — contract amend 4 (SPEC.md §5 item 42). The v582 rules (build/p/PH0/balloon.md, VERIFIED on the phone;
    // they replace events.md §5's inferred puffs/balloons model): ONE counter = levels won in a row (+1 per won level, any
    // tag); ANY failed level resets it to 0; platforms at fixed counts each pay their chest once per event.
    case balloonStreak(added: Int, total: Int, goal: Int?)  // a win: the counter total − added → total; goal = the next
                                                           // platform's count (nil = every platform passed)
    case balloonStep(step: Int, reward: Grant)             // platform `step` (1-based) reached for the first time this event
    case balloonFell(from: Int)                            // a failed level reset the counter from `from` (> 0) to 0
}

/// The opponents of the races (implemented by `SocialWorld`, SOC1).
public protocol RivalProvider: Sendable {
    /// The Streak Race board: 50 rows, the player included (v552: a 50-row ranking; CONSISTENCY V-5, §19 C-8).
    func streakRace(_ instance: EventInstance, player: PlayerStanding, at: SocialTime) -> [RaceStanding]
    /// The Rocket Race lanes: the 4 rivals.
    func rocketRace(_ instance: EventInstance, joinedAt: SocialTime, at: SocialTime) -> [RaceStanding]
    /// The Sky Jump field of a run: players left, winners.
    func skyJump(_ run: SkyJumpRun, at: SocialTime) -> SkyJumpField
}

/// One row of a race (Streak Race, Rocket Race).
public struct RaceStanding: Codable, Sendable, Equatable, Hashable {
    public var rank: Int                     // 1-based
    public var player: SimPlayer             // the player's own row carries their name / avatar / country
    public var score: Int                    // tokens (Streak Race) or levels beaten (Rocket Race)
    public var isMe: Bool

    public init(rank: Int, player: SimPlayer, score: Int, isMe: Bool) {
        self.rank = rank; self.player = player; self.score = score; self.isMe = isMe
    }
}

/// The Sky Jump field at a moment ("Finding players on your level." 29/100 → 100/100; 100 players drop per round).
public struct SkyJumpField: Codable, Sendable, Equatable {
    public var total: Int                    // players who started the run
    public var left: Int                     // still in
    public var winners: Int                  // finished the last stage (the prize splits among them)
    public var shown: [SimPlayer]            // the few opponents drawn on the screens

    public init(total: Int, left: Int, winners: Int, shown: [SimPlayer] = []) {
        self.total = total; self.left = left; self.winners = winners; self.shown = shown
    }
}
