import Foundation
import CoreGraphics

// C1 (SPEC-architecture §4.2, §5.3). The spike's grid-maths hit test (design/spike-src/App/Render/BoardView.swift
// `arrow(at:)`, VERIFIED 0 wrong on 873 + 399 jittered in-cell points, 0.35 µs per query), moved into the core:
// 1. the owner of the touched cell, if `live`;
// 2. else the nearest CENTRELINE within `r` among the live owners of the cells around the touch — the body polyline AND
//    the head segment out to the apex (head taps work, VERIFIED levels L47b); only cells within ceil(r/p)+1 are read,
//    never a scan over all arrows;
// 3. equal distances resolve by `tieBreak` (rightThenDown: VERIFIED once, the midpoint between two parallel free arrows
//    sent the right-hand one, levels L52).
// The radius is the caller's: `HitGeometry.radius(pitch:zoom:)` = max(0.5·pitch, 15 pt / zoom) (§5.3; ≥ 15 pt VERIFIED
// L47c, the true limit PENDING-gameplay → board.json input.hitRadiusPt).

public enum TieBreak: String, Codable, Sendable, CaseIterable { case rightThenDown, leftThenUp }

public struct HitGeometry: Sendable {
    public let layout: BoardLayout
    public let cols: Int
    public let rows: Int
    /// Per cell (row-major over the bounding grid): the arrows occupying it (usually one; two where an elevator's
    /// layer-2 arrow lies under a platform arrow).
    let owners: [[ArrowID]]
    /// Per arrow (dense index): its centreline segments in content space (a, b), the head-apex segment last.
    let segments: [[(CGPoint, CGPoint)]]
    let index: [ArrowID: Int]
    let ids: [ArrowID]

    public init(arrows: [ArrowSpec], layout: BoardLayout) {
        self.init(arrows: arrows, layout: layout, metrics: .default)
    }

    public init(arrows: [ArrowSpec], layout: BoardLayout, metrics: ArrowMetrics) {
        self.layout = layout
        var maxC = layout.cols - 1, maxR = layout.rows - 1
        for a in arrows { for c in a.cells { maxC = max(maxC, c.c); maxR = max(maxR, c.r) } }
        cols = max(0, maxC + 1); rows = max(0, maxR + 1)
        var own = [[ArrowID]](repeating: [], count: cols * rows)
        var segs: [[(CGPoint, CGPoint)]] = []
        var idx: [ArrowID: Int] = [:]
        var list: [ArrowID] = []
        for a in arrows {
            guard idx[a.id] == nil, !a.cells.isEmpty else { continue }
            idx[a.id] = list.count
            list.append(a.id)
            for c in a.cells where c.c >= 0 && c.r >= 0 { own[c.r * cols + c.c].append(a.id) }
            let g = ArrowGeometry(cells: a.cells, dir: a.dir, layout: layout, metrics: metrics)
            var s: [(CGPoint, CGPoint)] = []
            let pl = g.polyline
            if pl.count > 1 { for k in 1..<pl.count { s.append((pl[k - 1], pl[k])) } }
            s.append((g.headCentre, g.apex))                          // the head out to its apex
            segs.append(s)
        }
        owners = own; segments = segs; index = idx; ids = list
    }

    /// The §5.3 radius in content pt: max(0.5·pitch, hitRadiusPt / zoom).
    public static func radius(pitch: Double, zoom: Double, hitRadiusPt: Double = 15) -> Double {
        max(0.5 * pitch, hitRadiusPt / max(zoom, 1e-6))
    }

    /// The arrow a release at content point `p` hits, or nil. `live` excludes hidden, inactive-layer and moving arrows.
    public func nearest(to p: CGPoint, within r: Double, among live: (ArrowID) -> Bool, tieBreak: TieBreak) -> ArrowID? {
        let c = layout.cell(at: p)
        if c.c >= 0, c.r >= 0, c.c < cols, c.r < rows {
            for o in owners[c.r * cols + c.c] where live(o) { return o }
        }
        guard r > 0 else { return nil }
        let r2 = r * r
        let eps = 1e-9 * layout.pitch * layout.pitch
        let reach = Int((r / layout.pitch).rounded(.up)) + 1
        var best: ArrowID?
        var bestD = r2
        var bestQ = CGPoint.zero
        var seen = Set<ArrowID>()
        let r0 = max(0, c.r - reach), r1 = min(rows - 1, c.r + reach)
        let c0 = max(0, c.c - reach), c1 = min(cols - 1, c.c + reach)
        guard r0 <= r1, c0 <= c1 else { return nil }
        for rr in r0...r1 {
            for cc in c0...c1 {
                for o in owners[rr * cols + cc] where !seen.contains(o) {
                    seen.insert(o)
                    guard live(o), let i = index[o] else { continue }
                    for (a, b) in segments[i] {
                        let (d, q) = HitGeometry.distance2(p, a, b)
                        if d > bestD + eps { continue }
                        if best == nil || d < bestD - eps {
                            best = o; bestD = d; bestQ = q
                        } else if HitGeometry.prefers(q, over: bestQ, tieBreak, eps: 1e-6 * layout.pitch) {
                            best = o; bestD = min(d, bestD); bestQ = q
                        }
                    }
                }
            }
        }
        return best
    }

    /// Distance² from p to segment ab and the nearest point on it.
    @inline(__always) static func distance2(_ p: CGPoint, _ a: CGPoint, _ b: CGPoint) -> (Double, CGPoint) {
        let ax = Double(a.x), ay = Double(a.y)
        let abx = Double(b.x) - ax, aby = Double(b.y) - ay
        let apx = Double(p.x) - ax, apy = Double(p.y) - ay
        let l2 = abx * abx + aby * aby
        let t = l2 > 0 ? min(1, max(0, (apx * abx + apy * aby) / l2)) : 0
        let qx = ax + t * abx, qy = ay + t * aby
        let dx = Double(p.x) - qx, dy = Double(p.y) - qy
        return (dx * dx + dy * dy, CGPoint(x: qx, y: qy))
    }

    /// Tie rule between two equally near candidates by where their nearest points lie.
    @inline(__always) static func prefers(_ q: CGPoint, over b: CGPoint, _ tie: TieBreak, eps: Double) -> Bool {
        let dx = Double(q.x) - Double(b.x), dy = Double(q.y) - Double(b.y)
        switch tie {
        case .rightThenDown: return dx > eps || (abs(dx) <= eps && dy > eps)
        case .leftThenUp: return dx < -eps || (abs(dx) <= eps && dy < -eps)
        }
    }
}
