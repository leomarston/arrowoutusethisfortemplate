import UIKit
import PathCore

// B1 (SPEC-architecture §5.3). The board's hit test is C1's `HitGeometry` (PathCore §4.2: the spike's grid maths, VERIFIED
// 0 wrong of 873 + 399 jittered points): the owner of the touched cell; else the nearest centreline (the head-apex
// segment included: head taps work, VERIFIED L47b) within max(0.5·pitch, hitRadiusPt / zoom); exact ties → rightThenDown.
// The board adds what only it knows:
//  - which arrows are hittable now (resting or bumping, visible, active layer): `live`; exiting and hidden ones are not,
//    a bumping one stays (the core ignores it with IgnoreReason.bumping, so a tap on it never picks a neighbour);
//  - the L52a midpoint tie under touch quantisation (DECISION, board.json `input.tieTolerancePt` / `tieTolerancePitch`): a
//    release within min(1 pt / zoom, 0.03 · pitch) of the boundary between two different arrows' cells counts as their
//    midpoint, so the right-hand (then the lower) arrow wins whichever side of the line the touch was rounded to.

struct HitTester {
    private let geometry: HitGeometry
    private let layout: BoardLayout
    private let cols: Int
    private let rows: Int
    private var occ: [Int32]
    private var ids: [ArrowID]
    private var index: [ArrowID: Int] = [:]
    private var live: Set<ArrowID> = []
    /// Arrows that just started to exit, until their tail has left their own cells (CONSISTENCY G-9 / §21.16: a tap on
    /// a moving arrow is IGNORED, never re-targeted to a neighbour — a quick double tap must not fire a second arrow).
    private var movingUntil: [ArrowID: CFTimeInterval] = [:]

    init(level: LevelSpec, layout: BoardLayout, metrics: ArrowMetrics) {
        geometry = HitGeometry(arrows: level.arrows, layout: layout, metrics: metrics)
        self.layout = layout
        cols = level.cols
        rows = level.rows
        occ = [Int32](repeating: -1, count: max(1, level.cols * level.rows))
        ids = level.arrows.map(\.id)
        for (i, a) in level.arrows.enumerated() { index[a.id] = i }
    }

    /// Makes an arrow hittable (resting or bumping, visible, on the active layer).
    mutating func insert(_ id: ArrowID, cells: [Cell]) {
        guard let i = index[id] else { return }
        live.insert(id)
        for c in cells where c.c >= 0 && c.r >= 0 && c.c < cols && c.r < rows { occ[c.r * cols + c.c] = Int32(i) }
    }

    /// Keeps an exiting arrow as a hit candidate (reported, so the session ignores it with `.moving`) until `until`.
    mutating func markMoving(_ id: ArrowID, until: CFTimeInterval) {
        movingUntil[id] = until
        if movingUntil.count > 32 { movingUntil = movingUntil.filter { $0.value > until - 5 } }
    }

    /// Removes an arrow (it exited, or it is hidden).
    mutating func remove(_ id: ArrowID, cells: [Cell]) {
        guard let i = index[id] else { return }
        live.remove(id)
        for c in cells where c.c >= 0 && c.r >= 0 && c.c < cols && c.r < rows && occ[c.r * cols + c.c] == Int32(i) {
            occ[c.r * cols + c.c] = -1
        }
    }

    /// The live arrow occupying a cell.
    func owner(_ c: Cell) -> ArrowID? {
        guard c.c >= 0, c.r >= 0, c.c < cols, c.r < rows else { return nil }
        let v = occ[c.r * cols + c.c]
        return v < 0 ? nil : ids[Int(v)]
    }

    /// The arrow a release at content point `p` sends (nil = a miss).
    func arrow(at p: CGPoint, zoom: CGFloat, radiusPt: Double, tieTolerancePt: Double, tieTolerancePitch: Double = 0.03,
               rightThenDown: Bool, now: CFTimeInterval = 0) -> ArrowID? {
        let z = max(Double(zoom), 0.01)
        let c = layout.cell(at: p)
        if let o = owner(c), tieTolerancePt > 0, tieTolerancePitch > 0 {
            let tie = CGFloat(min(tieTolerancePt / z, tieTolerancePitch * layout.pitch))
            let cc = layout.centre(c)
            let half = CGFloat(layout.pitch) / 2
            if abs(p.x - (cc.x + half)) <= tie, let n = owner(Cell(c.c + 1, c.r)), n != o { return rightThenDown ? n : o }
            if abs(p.x - (cc.x - half)) <= tie, let n = owner(Cell(c.c - 1, c.r)), n != o { return rightThenDown ? o : n }
            if abs(p.y - (cc.y + half)) <= tie, let n = owner(Cell(c.c, c.r + 1)), n != o { return rightThenDown ? n : o }
            if abs(p.y - (cc.y - half)) <= tie, let n = owner(Cell(c.c, c.r - 1)), n != o { return rightThenDown ? o : n }
        }
        let r = HitGeometry.radius(pitch: layout.pitch, zoom: z, hitRadiusPt: radiusPt)
        let alive = live
        let moving = now > 0 ? movingUntil.filter { $0.value > now } : [:]
        return geometry.nearest(to: p, within: r, among: { alive.contains($0) || moving[$0] != nil },
                                tieBreak: rightThenDown ? .rightThenDown : .leftThenUp)
    }
}
