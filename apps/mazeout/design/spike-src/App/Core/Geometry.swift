import CoreGraphics
import Foundation

/// Measured on the original (iPhone 15 shot 003, L32 at fit: pitch 53.5 px = 17.85 pt @3x, 20x20 board).
/// Every length is a ratio of the cell pitch so zoom and board size never change the look.
enum Metrics {
    static var strokeRatio: CGFloat = 12.0 / 53.5          // 0.224  (black #000000, round caps + joins)
    static var headApexRatio: CGFloat = 20.25 / 53.5       // apex ahead of the head-cell centre
    static var headBaseRatio: CGFloat = 11.25 / 53.5       // flat base behind the head-cell centre
    static var headHalfWidthRatio: CGFloat = 16.5 / 53.5   // base width 33 px
    static var headCornerRatio: CGFloat = 1.6 / 53.5       // slightly rounded corners
    static var dotDiameterRatio: CGFloat = 10.3 / 53.5     // vacated-cell dot, #C5E1FF
    /// Fit rule seen on L32: pitch = width / (cols + 2)  (393 / 22 = 17.86 pt, measured 17.85)
    static var fitMarginCells: CGFloat = 1
}

/// Board space = the zoomable content at zoomScale 1 ("fit").
struct BoardLayout {
    let pitch: CGFloat
    let origin: CGPoint      // centre of cell (0,0)
    let contentSize: CGSize
    let cols: Int
    let rows: Int

    /// `play` = the rect the board must fit in (between HUD and booster bar), in content coordinates.
    init(cols: Int, rows: Int, content: CGSize, play: CGRect) {
        self.cols = cols
        self.rows = rows
        let m = 2 * Metrics.fitMarginCells
        pitch = min(play.width / (CGFloat(cols) + m), play.height / (CGFloat(rows) + m))
        contentSize = content
        origin = CGPoint(x: play.midX - CGFloat(cols - 1) * pitch / 2,
                         y: play.midY - CGFloat(rows - 1) * pitch / 2)
    }

    func centre(_ p: Cell) -> CGPoint {
        CGPoint(x: origin.x + CGFloat(p.c) * pitch, y: origin.y + CGFloat(p.r) * pitch)
    }
    func cell(at pt: CGPoint) -> Cell {
        Cell(Int(((pt.x - origin.x) / pitch).rounded()), Int(((pt.y - origin.y) / pitch).rounded()))
    }
    var boardRect: CGRect {
        CGRect(x: origin.x - pitch / 2, y: origin.y - pitch / 2, width: CGFloat(cols) * pitch, height: CGFloat(rows) * pitch)
    }
}

/// One arrow's drawing geometry. Corners are sharp polyline vertices drawn with round joins (the original's
/// outer corner radius equals the half-width, inner corner sharp), so arc length along the path is exact:
/// the tail passes cell i's centre at travel i * pitch.
struct ArrowGeometry {
    let corners: [CGPoint]       // tail, bends, head (collinear points removed)
    let dir: CGVector
    let dirAngle: CGFloat
    let headCentre: CGPoint
    let pitch: CGFloat
    let cellCount: Int
    var bodyLength: CGFloat { CGFloat(cellCount - 1) * pitch }
    var width: CGFloat { pitch * Metrics.strokeRatio }

    init(spec: ArrowSpec, layout: BoardLayout) {
        pitch = layout.pitch
        cellCount = spec.cells.count
        let pts = spec.cells.map(layout.centre)
        var s = [pts[0]]
        if pts.count > 2 {
            for i in 1..<(pts.count - 1) {
                let a = pts[i - 1], b = pts[i], c = pts[i + 1]
                if abs((b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)) > 1e-6 { s.append(b) }
            }
        }
        s.append(pts[pts.count - 1])
        corners = s
        dir = CGVector(dx: CGFloat(spec.dir.dc), dy: CGFloat(spec.dir.dr))
        dirAngle = atan2(dir.dy, dir.dx)
        headCentre = pts[pts.count - 1]
    }

    /// The resting stroke: body only (a short path keeps the layer's bounds tight so off-screen arrows cull).
    var restPath: CGPath {
        let p = CGMutablePath()
        p.addLines(between: corners)
        return p
    }

    /// Body + straight ray of `ray` points past the head: trimmed with strokeStart/strokeEnd during the exit.
    func exitPath(ray: CGFloat) -> CGPath {
        let p = CGMutablePath()
        p.addLines(between: corners + [headPosition(ray)])
        return p
    }

    func strokeStart(_ s: CGFloat, ray: CGFloat) -> CGFloat { s / (bodyLength + ray) }
    func strokeEnd(_ s: CGFloat, ray: CGFloat) -> CGFloat { (s + bodyLength) / (bodyLength + ray) }
    func headPosition(_ s: CGFloat) -> CGPoint { CGPoint(x: headCentre.x + dir.dx * s, y: headCentre.y + dir.dy * s) }

    /// The point `u` along tail -> head -> ray (u = travel for the tail).
    func point(along u: CGFloat) -> CGPoint {
        var t = max(0, u)
        for i in 1..<corners.count {
            let a = corners[i - 1], b = corners[i]
            let l = hypot(b.x - a.x, b.y - a.y)
            if t <= l { return CGPoint(x: a.x + (b.x - a.x) * t / l, y: a.y + (b.y - a.y) * t / l) }
            t -= l
        }
        return headPosition(t)
    }

    /// Straight runs of tail -> head -> head + ray, as (start, end, arc length at start).
    func runs(ray: CGFloat) -> [(CGPoint, CGPoint, CGFloat)] {
        var out: [(CGPoint, CGPoint, CGFloat)] = []
        var u: CGFloat = 0
        let pts = corners + [headPosition(ray)]
        for i in 1..<pts.count {
            out.append((pts[i - 1], pts[i], u))
            u += hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y)
        }
        return out
    }

    /// Travel at which the tail's round cap has fully left `visible` (board space).
    func exitTravel(leaving visible: CGRect) -> CGFloat {
        let h = headCentre
        let toEdge: CGFloat
        if dir.dx > 0 { toEdge = visible.maxX - h.x } else if dir.dx < 0 { toEdge = h.x - visible.minX }
        else if dir.dy > 0 { toEdge = visible.maxY - h.y } else { toEdge = h.y - visible.minY }
        return bodyLength + max(0, toEdge) + width
    }

    /// Travel at which the head's apex touches the blocker's stroke `gap + 1` cells ahead.
    func contactTravel(gap: Int) -> CGFloat {
        max(0.05 * pitch, (CGFloat(gap + 1) - Metrics.headApexRatio) * pitch - width / 2)
    }

    /// Head triangle in head-local space (+x = direction), rounded corners.
    static func headPath(pitch: CGFloat) -> CGPath {
        let a = CGPoint(x: Metrics.headApexRatio * pitch, y: 0)
        let b = CGPoint(x: -Metrics.headBaseRatio * pitch, y: -Metrics.headHalfWidthRatio * pitch)
        let c = CGPoint(x: -Metrics.headBaseRatio * pitch, y: Metrics.headHalfWidthRatio * pitch)
        let r = Metrics.headCornerRatio * pitch
        let p = CGMutablePath()
        p.move(to: CGPoint(x: b.x, y: 0))
        p.addArc(tangent1End: c, tangent2End: a, radius: r)
        p.addArc(tangent1End: a, tangent2End: b, radius: r)
        p.addArc(tangent1End: b, tangent2End: c, radius: r)
        p.closeSubpath()
        return p
    }
}

/// Travel over time: optional constant acceleration from rest, then constant speed `v` (board pt/s).
struct TravelProfile {
    let v: CGFloat
    let accel: Double     // seconds to reach v (0 = constant speed from the first frame)

    var accelDistance: CGFloat { v * CGFloat(accel) / 2 }

    func time(toReach s: CGFloat) -> Double {
        guard s > 0 else { return 0 }
        if accel > 0, s <= accelDistance { return accel * Double((s / accelDistance).squareRoot()) }
        return (accel > 0 ? accel : 0) + Double((s - (accel > 0 ? accelDistance : 0)) / v)
    }

    func travel(at t: Double) -> CGFloat {
        guard t > 0 else { return 0 }
        if accel > 0, t <= accel { let k = CGFloat(t / accel); return accelDistance * k * k }
        return (accel > 0 ? accelDistance : 0) + v * CGFloat(t - max(accel, 0))
    }
}

/// Hit test fallback: squared distance from p to segment ab.
@inline(__always) func dist2(_ p: CGPoint, _ a: CGPoint, _ b: CGPoint) -> CGFloat {
    let abx = b.x - a.x, aby = b.y - a.y, apx = p.x - a.x, apy = p.y - a.y
    let l2 = abx * abx + aby * aby
    let t = l2 > 0 ? min(1, max(0, (apx * abx + apy * aby) / l2)) : 0
    let dx = apx - t * abx, dy = apy - t * aby
    return dx * dx + dy * dy
}
