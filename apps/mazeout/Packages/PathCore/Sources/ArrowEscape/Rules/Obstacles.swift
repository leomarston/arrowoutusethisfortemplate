import Foundation
import GameCore

// C2 (SPEC-architecture §4.4). The obstacles' runtime state inside a BoardState, and the core-level rule events the
// session maps onto the ◆ SessionEvent stream.
//
// | obstacle | blocks a ray | lifecycle |
// | tape     | never (members are ordinary arrows) | leaves with its bundle (one tap sends every member iff all are clear) |
// | door     | while locked or targeted | a key arrow's exit targets it; it opens on the board's `.doorBurst` ack |
// | key      | never (hangs on its arrow) | released when its arrow exits: goes to `opens`, else the lowest-order free door |
// | pipe     | tube cells always; a mouth entered against its `out` is a passage | −1 per passage at the tap; 0 = broken |
// | box      | while its counter > 0 | −1 per arrow cleared anywhere, at the tap; 0 = broken, `reveals` go live |
// | curtain  | as box (the video skin) | as box |
// | elevator | never (INFERRED; `elevator.emptyCellsBlock`) | the last platform arrow's tap activates it: layer 2 goes live |
// | corner   | from a side it does not accept | static; a ray from an accepting side turns 90° |

/// A logical change of the board (the session maps these onto `SessionEvent`; they happen at the tap or at an ack).
public enum RuleEvent: Equatable, Sendable {
    case keyDispatched(key: ObstacleID, door: ObstacleID)
    case doorOpened(ObstacleID, revealed: [ArrowID])
    case pipeUsed(ObstacleID, remaining: Int)
    case pipeBroken(ObstacleID)
    case counterChanged(ObstacleID, remaining: Int)
    case counterBroken(ObstacleID, revealed: [ArrowID])
    case elevatorActivated(ObstacleID, revealed: [ArrowID])
    /// The board reported the bump's contact frame; `repeat` = every bumping arrow was already red (costs no heart when
    /// `RulesTuning.bump.repeatOnMarkedCostsHeart` is false). Consumed by the session (never forwarded).
    case bumpContact(ArrowID, repeat: Bool)
    case arrowMarked(ArrowID)
}

/// A presentation-timed fact the board reports back (the session forwards the matching `SessionAck`s).
public enum RuleAck: Equatable, Sendable {
    case bumpContact(ArrowID)
    case bumpFinished(ArrowID)
    case doorBurst(ObstacleID)
}

/// A door's state.
public enum DoorState: String, Codable, Sendable, CaseIterable {
    case locked      // blocks; no key is on its way
    case targeted    // a key is flying to it; still blocks until the burst ack
    case open        // cells empty, revealed arrows live
}

/// One obstacle at run time.
struct ObstacleRT: Sendable {
    let id: ObstacleID
    let kind: ObstacleKind
    let cells: [Cell]
    /// door: lock state.
    var door: DoorState = .locked
    /// pipe passes left · box/curtain clears left; nil = unlimited (data without a counter).
    var counter: Int?
    /// pipe / box / curtain broken · tape gone · key used · elevator activated.
    var done = false
    /// door opening order (nil order sorts last, then by declaration).
    let order: Int
    /// key → explicit door.
    let opens: ObstacleID?
    /// key: the arrow it hangs on (index).
    let rider: Int?
    /// tape members · elevator platform arrows (indices).
    let members: [Int]
    /// arrows hidden under it (indices): door / box / curtain / elevator.
    var reveals: [Int]
    /// pipe: the tube cells ordered from `ends[0]` to `ends[1]` (empty = no usable mouths: every cell just blocks).
    let tube: [Cell]
    /// pipe: exactly the two mouths, in tube order, or empty.
    let ends: [PipeEnd]
    let turn: CornerTurn?

    /// Blocks rays right now (at its cells).
    var blocksNow: Bool {
        switch kind {
        case .door: return door != .open
        case .box, .curtain, .pipe: return !done
        case .corner: return true
        case .tape, .key, .elevator: return false
        }
    }

    var isCounterKind: Bool { kind == .box || kind == .curtain }
}

extension ObstacleRT {
    /// Orders a pipe's cells mouth → mouth. The ◆ model says `cells` are ordered, but research imports may not be: walk
    /// the 4-connected cell set from the first end; a branchy set falls back to a BFS shortest path between the mouths.
    static func orderedTube(cells: [Cell], ends: [PipeEnd]) -> (tube: [Cell], ends: [PipeEnd]) {
        guard ends.count == 2, ends[0].cell != ends[1].cell else { return ([], []) }
        let set = Set(cells)
        guard set.contains(ends[0].cell), set.contains(ends[1].cell) else { return ([], []) }
        if cells.first == ends[0].cell, cells.last == ends[1].cell, Self.isPath(cells) { return (cells, ends) }
        if cells.first == ends[1].cell, cells.last == ends[0].cell, Self.isPath(cells) { return (cells, [ends[1], ends[0]]) }
        // BFS from end 0 to end 1 inside the set.
        var prev: [Cell: Cell] = [:]
        var queue = [ends[0].cell]
        var seen: Set<Cell> = [ends[0].cell]
        var k = 0
        while k < queue.count {
            let c = queue[k]; k += 1
            if c == ends[1].cell { break }
            for d in Dir.allCases {
                let n = c + d
                if set.contains(n), !seen.contains(n) { seen.insert(n); prev[n] = c; queue.append(n) }
            }
        }
        guard seen.contains(ends[1].cell) else { return ([], []) }
        var path = [ends[1].cell]
        while let p = prev[path[path.count - 1]] { path.append(p) }
        return (path.reversed(), ends)
    }

    static func isPath(_ cells: [Cell]) -> Bool {
        guard cells.count >= 1 else { return false }
        for (a, b) in zip(cells, cells.dropFirst()) where Dir(from: a, to: b) == nil { return false }
        return Set(cells).count == cells.count
    }

    /// A corner accepts a ray moving `d` and turns it (named incoming → outgoing; the reverse path works too).
    static func cornerTurn(_ t: CornerTurn, _ d: Dir) -> Dir? {
        let (i, o): (Dir, Dir)
        switch t {
        case .upRight: (i, o) = (.up, .right)
        case .upLeft: (i, o) = (.up, .left)
        case .downRight: (i, o) = (.down, .right)
        case .downLeft: (i, o) = (.down, .left)
        }
        if d == i { return o }
        if d == o.opposite { return i.opposite }
        return nil
    }
}
