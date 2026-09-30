import Foundation
import GameCore

// ◆ CONTRACT (SPEC-architecture §3.5, §4.5), split out of GameCore/Session/SessionTypes.swift in template phase 1: the two
// session types that name arrows and obstacles (the board's acks and the probe's snapshot). FROZEN like SessionTypes.swift
// (APISurfaceTests); PUZZLE-MODULE.md §1 replaces them with generic ones in phase 2.

/// Presentation-timed facts the board reports back (§4.5, D4).
public enum SessionAck: Equatable, Sendable {
    case introFinished
    case bumpContact(ArrowID)
    case bumpFinished(ArrowID)
    case doorBurst(ObstacleID)
    case lastExitLeftBoard
    case stageTransitionDone
}

/// The probe's source (§9.4).
public struct SessionSnapshot: Codable, Sendable, Equatable {
    public var levels: [Int]
    public var stage: Int
    public var phase: String
    public var remaining: Double
    public var timerStarted: Bool
    public var hearts: Int
    public var live: [ArrowID]
    public var free: [[ArrowID]]
    public var counters: [ObstacleID: Int]
    public var combo: Int

    public init(levels: [Int], stage: Int, phase: String, remaining: Double, timerStarted: Bool, hearts: Int,
                live: [ArrowID], free: [[ArrowID]], counters: [ObstacleID: Int], combo: Int) {
        self.levels = levels; self.stage = stage; self.phase = phase; self.remaining = remaining
        self.timerStarted = timerStarted; self.hearts = hearts; self.live = live; self.free = free
        self.counters = counters; self.combo = combo
    }
}
