import Foundation
import CoreGraphics

// C1 (SPEC-architecture §4.2, §5.4). The spike's Geometry.swift (design/spike-src/App/Core/Geometry.swift), generalised to
// the ◆ ExitPath. The body is the SHARP polyline through the cell centres (drawn with round joins, §5.4), so arc length is
// exact: the tail passes cell i's centre at travel i·pitch (VERIFIED spike: 399/399 L32 dots at the right cells).

/// One arrow's drawing geometry in content space (pt at fit zoom).
public struct ArrowGeometry: Sendable {
    public let cells: [Cell]
    public let dir: Dir
    public let pitch: Double
    public let metrics: ArrowMetrics
    /// Cell centres tail → head, collapsed to corners (sharp polyline).
    public let polyline: [CGPoint]
    /// (cells − 1) × pitch: arc length is exact (tail passes cell i at travel i·p).
    public let bodyLength: Double
    public let headCentre: CGPoint
    let layoutOrigin: CGPoint

    public init(cells: [Cell], dir: Dir, layout: BoardLayout) {
        self.init(cells: cells, dir: dir, layout: layout, metrics: .default)
    }

    public init(cells: [Cell], dir: Dir, layout: BoardLayout, metrics: ArrowMetrics) {
        precondition(!cells.isEmpty, "ArrowGeometry needs at least one cell")
        self.cells = cells
        self.dir = dir
        self.pitch = layout.pitch
        self.metrics = metrics
        self.layoutOrigin = layout.origin
        let pts = cells.map(layout.centre)
        var corners = [pts[0]]
        if pts.count > 2 {
            for i in 1..<(pts.count - 1) {
                let a = pts[i - 1], b = pts[i], c = pts[i + 1]
                let cross = (Double(b.x) - Double(a.x)) * (Double(c.y) - Double(b.y)) - (Double(b.y) - Double(a.y)) * (Double(c.x) - Double(b.x))
                if abs(cross) > 1e-9 * layout.pitch * layout.pitch { corners.append(b) }
            }
        }
        if pts.count > 1 { corners.append(pts[pts.count - 1]) }
        polyline = corners
        bodyLength = Double(cells.count - 1) * layout.pitch
        headCentre = pts[pts.count - 1]
    }

    public init(arrow: ArrowSpec, layout: BoardLayout, metrics: ArrowMetrics = .default) {
        self.init(cells: arrow.cells, dir: arrow.dir, layout: layout, metrics: metrics)
    }

    /// Stroke width in content pt.
    public var strokeWidth: Double { metrics.stroke * pitch }

    /// How far the head apex sits past the head-cell centre, in content pt.
    public var apexDistance: Double { metrics.apexPast(dir) * pitch }

    /// The head apex in content space.
    public var apex: CGPoint {
        CGPoint(x: Double(headCentre.x) + Double(dir.dc) * apexDistance, y: Double(headCentre.y) + Double(dir.dr) * apexDistance)
    }

    /// The resting body path (polyline only: a short path keeps the layer's frame tight so off-screen arrows cull, P4).
    public func bodyPath() -> CGPath {
        let p = CGMutablePath()
        if polyline.count == 1 { p.move(to: polyline[0]); p.addLine(to: polyline[0]) } else { p.addLines(between: polyline) }
        return p
    }

    /// Isosceles triangle in HEAD-LOCAL space: +x = the head direction, origin = the head-cell centre; apex at
    /// (+headApexPast(dir)·p, 0) (the visible tip: sharp by default), base at apex − headLength·p, width headBase·p, base
    /// corners rounded headCornerRadius·p.
    /// Place it with `headTransform` (translate to `headCentre`, rotate by `dir.angle`).
    public func headPath() -> CGPath {
        ArrowGeometry.headPath(pitch: pitch, apexPast: metrics.apexPast(dir), metrics: metrics)
    }

    public static func headPath(pitch: Double, apexPast: Double, metrics: ArrowMetrics = .default) -> CGPath {
        let ax = apexPast * pitch
        let bx = (apexPast - metrics.headLength) * pitch
        let hw = metrics.headBase * pitch / 2
        let r = metrics.headCornerRadius * pitch
        let rt = metrics.headTipRadius * pitch
        let a = CGPoint(x: ax, y: 0), b = CGPoint(x: bx, y: -hw), c = CGPoint(x: bx, y: hw)
        let p = CGMutablePath()
        p.move(to: CGPoint(x: bx, y: 0))
        p.addArc(tangent1End: c, tangent2End: a, radius: r)
        if rt > 0 { p.addArc(tangent1End: a, tangent2End: b, radius: rt) } else { p.addLine(to: a) }
        p.addArc(tangent1End: b, tangent2End: c, radius: r)
        p.closeSubpath()
        return p
    }

    /// Head-local → content: rotate by `dir.angle`, then translate to `headCentre`.
    public var headTransform: CGAffineTransform {
        CGAffineTransform(translationX: headCentre.x, y: headCentre.y).rotated(by: CGFloat(dir.angle))
    }

    // MARK: along an ExitPath

    /// The point at arc `u` (content pt) along `path`, measured from the TAIL cell centre at rest; past the path's last
    /// cell the last direction continues (to the screen edge, D5). A body point at arc a after a head travel s is at
    /// u = a + s; the head is at u = bodyLength + s.
    public func point(along u: Double, on path: ExitPath) -> CGPoint {
        let q = PathTrack(path: path).point(at: u / pitch)
        return CGPoint(x: Double(layoutOrigin.x) + Double(q.x) * pitch, y: Double(layoutOrigin.y) + Double(q.y) * pitch)
    }

    /// The direction of travel at arc `u` (content pt) along `path` (a corner belongs to the run that leaves it).
    public func tangent(along u: Double, on path: ExitPath) -> Dir {
        PathTrack(path: path).direction(at: u / pitch)
    }

    /// Head travel (content pt) at which the apex touches the blocker's stroke edge `gap + 1` cells ahead on a straight
    /// ray (the spike's `contactTravel`; gap 0 is common, P9). Never below 0.05 cell.
    public func contactTravel(gap: Int) -> Double {
        max(0.05 * pitch, (Double(gap + 1) - metrics.apexPast(dir)) * pitch - strokeWidth / 2)
    }
}
