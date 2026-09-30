import Foundation
import GameCore

// ◆ CONTRACT (SPEC-architecture §3.5, §4.3). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests).
//
// The MODEL is frozen here; the JSON MAPPING is not. Every Codable body below delegates to `LevelCoding`
// (Model/LevelJSON.swift, owned by C1), so C1 can follow whatever key names SPEC-gameplay freezes for the bundle schema
// (§4.3: "the exact obstacle field names are PENDING-gameplay") without touching this file. Likewise `LevelSpec.grid`
// calls C1's `Grid(cols:rows:maskRows:)`. Helpers (head, tail, …) go in EXTENSIONS in C1's files.

/// One snake arrow: orthogonal steps through cell centres, TAIL first, HEAD last; the head points `dir`.
public struct ArrowSpec: Codable, Sendable, Equatable {
    public var id: ArrowID
    public var cells: [Cell]                      // tail → head, orthogonally adjacent, ≥ 2 cells (VERIFIED min 2)
    public var dir: Dir                           // head direction = the last segment's direction (validator)
    public var layer: Int                         // 1; 2 = under an elevator platform (video V2 L31+)
    public var hiddenBy: ObstacleID?              // door / box / curtain / elevator that hides it until it opens

    public init(id: ArrowID, cells: [Cell], dir: Dir, layer: Int = 1, hiddenBy: ObstacleID? = nil) {
        self.id = id; self.cells = cells; self.dir = dir; self.layer = layer; self.hiddenBy = hiddenBy
    }

    public init(from decoder: Decoder) throws { self = try LevelCoding.decodeArrow(from: decoder) }
    public func encode(to encoder: Encoder) throws { try LevelCoding.encode(self, to: encoder) }
}

public enum ObstacleKind: String, Codable, Sendable, CaseIterable {
    case tape, door, key, pipe, box, curtain, elevator, corner
}

/// One mouth of a pipe: the cell it sits on and the direction an arrow LEAVES through it.
public struct PipeEnd: Codable, Sendable, Equatable {
    public var cell: Cell
    public var out: Dir
    public init(cell: Cell, out: Dir) { self.cell = cell; self.out = out }
}

/// A corner wedge's turn, named incoming → outgoing (§4.4).
public enum CornerTurn: String, Codable, Sendable, CaseIterable {
    case upRight, upLeft, downRight, downLeft
}

public struct ObstacleSpec: Codable, Sendable, Equatable {
    public var id: ObstacleID
    public var kind: ObstacleKind
    public var cells: [Cell]                      // covered cells; pipe: ordered mouth → mouth; key: the 2 cells it hangs on
    public var arrows: [ArrowID]                  // tape members · the key's arrow · the elevator's platform arrows
    public var ends: [PipeEnd]                    // pipe only: 2 mouths
    public var counter: Int?                      // pipe passes left · box/curtain clears left
    public var counterAt: [Double]?               // pipe counter box centre in cells (e.g. [7.5, 0], STYLE §A.2)
    public var order: Int?                        // door opening order (keys go to the lowest-order locked door)
    public var opens: ObstacleID?                 // key → explicit door (nil = next by order)
    public var turn: CornerTurn?
    public var reveals: [ArrowID]                 // arrows hidden under it (door / box / curtain / elevator layer 2)
    public var sprite: String?                    // art id override; nil = derived (tapeV4, doorW4H8, …)

    public init(id: ObstacleID, kind: ObstacleKind, cells: [Cell] = [], arrows: [ArrowID] = [], ends: [PipeEnd] = [],
                counter: Int? = nil, counterAt: [Double]? = nil, order: Int? = nil, opens: ObstacleID? = nil,
                turn: CornerTurn? = nil, reveals: [ArrowID] = [], sprite: String? = nil) {
        self.id = id; self.kind = kind; self.cells = cells; self.arrows = arrows; self.ends = ends
        self.counter = counter; self.counterAt = counterAt; self.order = order; self.opens = opens
        self.turn = turn; self.reveals = reveals; self.sprite = sprite
    }

    public init(from decoder: Decoder) throws { self = try LevelCoding.decodeObstacle(from: decoder) }
    public func encode(to encoder: Encoder) throws { try LevelCoding.encode(self, to: encoder) }
}

/// Validator / generator output (§4.14).
public struct LevelMetrics: Codable, Sendable, Equatable {
    public var rounds: Int
    public var freeAtStart: Int
    public var arrows: Int
    public var cells: Int
    public var meanLength: Double
    public var botTimeLeft: Double?

    public init(rounds: Int, freeAtStart: Int, arrows: Int, cells: Int, meanLength: Double, botTimeLeft: Double? = nil) {
        self.rounds = rounds; self.freeAtStart = freeAtStart; self.arrows = arrows; self.cells = cells
        self.meanLength = meanLength; self.botTimeLeft = botTimeLeft
    }

    public init(from decoder: Decoder) throws { self = try LevelCoding.decodeMetrics(from: decoder) }
    public func encode(to encoder: Encoder) throws { try LevelCoding.encode(self, to: encoder) }
}

/// One board (one stage of a session).
public struct LevelSpec: Codable, Sendable, Equatable {
    public var level: Int
    public var source: LevelSource
    public var capture: String?                   // research shot / video frame the level was read from
    public var cols: Int
    public var rows: Int
    public var mask: [String]?                    // rows of the silhouette, '#' = playable; nil = all playable
    public var timerSeconds: Int                  // JSON "timer_s" (3:00, 2:30, 2:00, 3:30 seen; VERIFIED levels)
    public var hearts: Int                        // 3 everywhere (VERIFIED)
    public var tag: LevelTag
    public var arrows: [ArrowSpec]
    public var obstacles: [ObstacleSpec]
    public var unlock: FeatureID?                 // the first Play of this level shows this feature's unlock overlay
    public var seed: UInt64?                      // generated levels
    public var metrics: LevelMetrics?

    public init(level: Int, source: LevelSource, capture: String? = nil, cols: Int, rows: Int, mask: [String]? = nil,
                timerSeconds: Int, hearts: Int = 3, tag: LevelTag = .normal, arrows: [ArrowSpec],
                obstacles: [ObstacleSpec] = [], unlock: FeatureID? = nil, seed: UInt64? = nil, metrics: LevelMetrics? = nil) {
        self.level = level; self.source = source; self.capture = capture; self.cols = cols; self.rows = rows
        self.mask = mask; self.timerSeconds = timerSeconds; self.hearts = hearts; self.tag = tag; self.arrows = arrows
        self.obstacles = obstacles; self.unlock = unlock; self.seed = seed; self.metrics = metrics
    }

    /// The level's grid (C1's `Grid(cols:rows:maskRows:)`).
    public var grid: Grid { Grid(cols: cols, rows: rows, maskRows: mask) }

    public init(from decoder: Decoder) throws { self = try LevelCoding.decodeLevel(from: decoder) }
    public func encode(to encoder: Encoder) throws { try LevelCoding.encode(self, to: encoder) }
}

/// Whether hearts reset or carry between the stages of a multi-board session (PENDING-gameplay; default .carry).
public enum HeartsCarry: String, Codable, Sendable, CaseIterable { case reset, carry }

/// One Play = one session = 1…n stages (sessions.json; a level in no session is a one-stage session).
public struct SessionPlan: Codable, Sendable, Equatable {
    public var id: String
    public var levels: [Int]                      // [1, 2, 3, 4] (VERIFIED tutorials §2) or [n]
    public var hudLabel: String?                  // "Levels 1-4" (else "Level %lld"); a strings-table KEY, not display text
    public var panelLabel: String?                // "Level 1-4" (singular on the win panel, VERIFIED); a strings-table KEY
    public var reward: Int?                       // 80 (VERIFIED); nil = by tag
    public var stageGap: Double?                  // last exit → next board built: 0.7 s (VERIFIED tutorials §2)
    public var hearts: HeartsCarry                // PENDING-gameplay (no heart was lost in V1); default .carry

    public init(id: String, levels: [Int], hudLabel: String? = nil, panelLabel: String? = nil, reward: Int? = nil,
                stageGap: Double? = nil, hearts: HeartsCarry = .carry) {
        self.id = id; self.levels = levels; self.hudLabel = hudLabel; self.panelLabel = panelLabel
        self.reward = reward; self.stageGap = stageGap; self.hearts = hearts
    }

    public init(from decoder: Decoder) throws { self = try LevelCoding.decodeSession(from: decoder) }
    public func encode(to encoder: Encoder) throws { try LevelCoding.encode(self, to: encoder) }
}
