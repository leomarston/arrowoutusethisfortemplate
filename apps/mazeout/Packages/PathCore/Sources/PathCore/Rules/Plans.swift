import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.4). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests).
// What the core hands the board (D4: the core resolves a tap into a plan; the board plays the plan). Arc positions are
// in CELLS of the leading head's travel; the board converts them to time with ExitKinematics (§4.16, D5).

public enum TapResolution: Equatable, Sendable {
    case exit(ExitPlan)
    case bump(BumpPlan)
    case ignored(IgnoreReason)
}

public enum IgnoreReason: String, Codable, Sendable, CaseIterable {
    case noArrow, hidden, moving, bumping, inputLocked, notPlaying
}

public enum PathSegment: Equatable, Sendable {
    case body(Range<Double>)                              // arc range in cells of the HEAD's travel
    case ray(Range<Double>)
    case tube(ObstacleID, Range<Double>)
    case corner(ObstacleID, at: Double)
}

public struct ExitPath: Equatable, Sendable {
    public var cells: [Cell]                              // body tail → head, then every cell the head passes to the grid edge
    public var segments: [PathSegment]
    public var toGridEdge: Double                         // head travel (cells) until the head leaves the grid;
                                                          // the board extends the last direction to the SCREEN edge (D5)
    public init(cells: [Cell], segments: [PathSegment], toGridEdge: Double) {
        self.cells = cells; self.segments = segments; self.toGridEdge = toGridEdge
    }
}

public enum PlanBeat: Equatable, Sendable {               // s = the leading head's travel in cells when it happens
    case keyReleased(key: ObstacleID, door: ObstacleID, s: Double)
    case enterTube(ObstacleID, ArrowID, s: Double)
    case leaveTube(ObstacleID, ArrowID, s: Double)
    case pipeCount(ObstacleID, remaining: Int, s: Double) // visible counter change (PENDING-motion-audio: at enter or leave)
    case pipeBreak(ObstacleID, s: Double)                 // the board adds the measured +0.05 s (motion §4.3)
    case corner(ObstacleID, ArrowID, s: Double)
    case counterTick(ObstacleID, remaining: Int, s: Double)   // box/curtain (PENDING-motion-audio: at the tap or at the leave)
    case counterBreak(ObstacleID, s: Double)
    case elevatorEmptied(ObstacleID, s: Double)

    /// The beat's arc position (cells of the leading head's travel).
    public var s: Double {
        switch self {
        case .keyReleased(_, _, let s), .enterTube(_, _, let s), .leaveTube(_, _, let s), .pipeCount(_, _, let s),
             .pipeBreak(_, let s), .corner(_, _, let s), .counterTick(_, _, let s), .counterBreak(_, let s),
             .elevatorEmptied(_, let s):
            return s
        }
    }
}

public struct ExitPlan: Equatable, Sendable {
    public var tapped: ArrowID
    public var unit: [ArrowID]                            // [tapped] or the whole tape bundle
    public var tape: ObstacleID?
    public var paths: [ArrowID: ExitPath]
    public var beats: [PlanBeat]                          // sorted by s
    public var combo: Int                                 // 1-based combo index (§4.7)

    public init(tapped: ArrowID, unit: [ArrowID], tape: ObstacleID? = nil, paths: [ArrowID: ExitPath],
                beats: [PlanBeat] = [], combo: Int = 1) {
        self.tapped = tapped; self.unit = unit; self.tape = tape; self.paths = paths; self.beats = beats; self.combo = combo
    }
}

public enum Blocker: Equatable, Sendable {
    case arrow(ArrowID)
    case obstacle(ObstacleID)
}

public struct BumpPlan: Equatable, Sendable {
    public var arrow: ArrowID
    public var blocker: Blocker
    public var gapCells: Int                              // empty cells between head and blocker (0 is common: spike P9)
    public var path: ExitPath                             // the travelled part (may pass through a tube)
    public var contactCells: Double                       // head travel to contact: apex touches the blocker's stroke edge
    public var contactPoint: Cell                         // where the ✖ badge sits (VERIFIED obstacles "BUMP")

    public init(arrow: ArrowID, blocker: Blocker, gapCells: Int, path: ExitPath, contactCells: Double, contactPoint: Cell) {
        self.arrow = arrow; self.blocker = blocker; self.gapCells = gapCells; self.path = path
        self.contactCells = contactCells; self.contactPoint = contactPoint
    }
}
