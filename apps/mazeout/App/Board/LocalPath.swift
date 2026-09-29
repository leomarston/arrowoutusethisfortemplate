import UIKit
import PathCore

// B1 (SPEC-architecture §5.4, §5.11 P4; the spike's Geometry.swift + ArrowNode.swift LocalPath, generalised).
// Board-side drawing geometry in CONTENT space (pt at fit zoom). It reads PathCore's C1 values (`Metrics`, `BoardLayout`)
// and adds the look knobs motion.md pass 2 measured on the phone (centre-line fillet, tail extension) from board.json.
// C1's ArrowGeometry/HitGeometry are not written yet; when they land, the rest/exit polylines can come from there.

/// A path in its own tight frame: every shape layer's frame hugs its path so off-screen arrows are culled at max zoom (P4).
struct LocalPath {
    let frame: CGRect
    let path: CGPath

    init(_ path: CGPath, pad: CGFloat) {
        let box = path.boundingBoxOfPath.insetBy(dx: -pad, dy: -pad).integral
        frame = box
        var t = CGAffineTransform(translationX: -box.minX, y: -box.minY)
        self.path = path.copy(using: &t) ?? path
    }

    func local(_ p: CGPoint) -> CGPoint { CGPoint(x: p.x - frame.minX, y: p.y - frame.minY) }
}

/// A polyline through cell centres whose 90° corners are filleted with radius R, measured by arc length. The stroke of
/// an arrow is this path (round cap, round join); `strokeStart/End` fractions and the head's position come from the same
/// arc-length parametrisation, so a moving body keeps its rounded corners and its exact length.
struct ArrowPath {
    enum Piece {
        case line(a: CGPoint, b: CGPoint, length: CGFloat)
        case arc(centre: CGPoint, radius: CGFloat, a0: CGFloat, sweep: CGFloat, length: CGFloat)

        var length: CGFloat {
            switch self {
            case .line(_, _, let l): return l
            case .arc(_, _, _, _, let l): return l
            }
        }
    }

    let pieces: [Piece]
    let length: CGFloat
    let cgPath: CGPath
    /// The vertices after collinear points were merged (tail start, corners, end).
    let vertices: [CGPoint]

    /// `points`: tail → … (cell centres); `startExtend`: the path starts this far behind points[0] (tail extension);
    /// `fillet`: the corner radius (clamped to half of each adjacent segment).
    init(points raw: [CGPoint], fillet: CGFloat, startExtend: CGFloat = 0) {
        var pts: [CGPoint] = []
        for p in raw {
            if let last = pts.last, abs(last.x - p.x) < 1e-6, abs(last.y - p.y) < 1e-6 { continue }
            if pts.count >= 2 {
                let a = pts[pts.count - 2], b = pts[pts.count - 1]
                let cross = (b.x - a.x) * (p.y - b.y) - (b.y - a.y) * (p.x - b.x)
                let dot = (b.x - a.x) * (p.x - b.x) + (b.y - a.y) * (p.y - b.y)
                if abs(cross) < 1e-6 && dot > 0 { pts[pts.count - 1] = p; continue }
            }
            pts.append(p)
        }
        if pts.count == 1 { pts.append(CGPoint(x: pts[0].x + 0.001, y: pts[0].y)) }
        if startExtend > 0, pts.count >= 2 {
            let d = Self.unit(pts[0], pts[1])
            pts[0] = CGPoint(x: pts[0].x - d.dx * startExtend, y: pts[0].y - d.dy * startExtend)
        }
        vertices = pts

        var pieces: [Piece] = []
        let path = CGMutablePath()
        path.move(to: pts[0])
        var cursor = pts[0]
        for i in 1..<pts.count {
            let b = pts[i]
            if i < pts.count - 1 {
                let a = pts[i - 1], c = pts[i + 1]
                let lin = Self.dist(a, b), lout = Self.dist(b, c)
                // the previous corner already consumed up to R of this segment: at most half of each remains
                let r = min(fillet, lin * 0.5, lout * 0.5)
                if r > 0.01 {
                    let din = Self.unit(a, b), dout = Self.unit(b, c)
                    let s = CGPoint(x: b.x - din.dx * r, y: b.y - din.dy * r)
                    let e = CGPoint(x: b.x + dout.dx * r, y: b.y + dout.dy * r)
                    let centre = CGPoint(x: s.x + dout.dx * r, y: s.y + dout.dy * r)
                    let cross = din.dx * dout.dy - din.dy * dout.dx
                    let sweep: CGFloat = cross > 0 ? .pi / 2 : -.pi / 2
                    let a0 = atan2(s.y - centre.y, s.x - centre.x)
                    let l1 = Self.dist(cursor, s)
                    if l1 > 1e-6 { pieces.append(.line(a: cursor, b: s, length: l1)) }
                    let arcLen = abs(sweep) * r
                    pieces.append(.arc(centre: centre, radius: r, a0: a0, sweep: sweep, length: arcLen))
                    path.addLine(to: s)
                    path.addArc(center: centre, radius: r, startAngle: a0, endAngle: a0 + sweep, clockwise: sweep < 0)
                    cursor = e
                    continue
                }
            }
            let l = Self.dist(cursor, b)
            if l > 1e-6 { pieces.append(.line(a: cursor, b: b, length: l)) }
            path.addLine(to: b)
            cursor = b
        }
        self.pieces = pieces
        self.length = pieces.reduce(0) { $0 + $1.length }
        cgPath = path
    }

    /// The point `u` pt along the path (clamped; beyond the end it continues straight along the last direction).
    func point(at u: CGFloat) -> CGPoint {
        var t = max(0, u)
        for piece in pieces {
            let l = piece.length
            if t <= l || piece.length == 0 {
                switch piece {
                case let .line(a, b, len):
                    let f = len > 0 ? t / len : 0
                    return CGPoint(x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f)
                case let .arc(c, r, a0, sweep, len):
                    let ang = a0 + sweep * (len > 0 ? t / len : 0)
                    return CGPoint(x: c.x + r * cos(ang), y: c.y + r * sin(ang))
                }
            }
            t -= l
        }
        let end = vertices[vertices.count - 1]
        let d = Self.unit(vertices[vertices.count - 2], end)
        return CGPoint(x: end.x + d.dx * t, y: end.y + d.dy * t)
    }

    /// The tangent direction (radians, screen space, y down) at `u` pt along the path.
    func angle(at u: CGFloat) -> CGFloat {
        var t = max(0, u)
        for piece in pieces {
            if t <= piece.length {
                switch piece {
                case let .line(a, b, _): return atan2(b.y - a.y, b.x - a.x)
                case let .arc(_, _, a0, sweep, len):
                    let ang = a0 + sweep * (len > 0 ? t / len : 0)
                    return ang + (sweep > 0 ? .pi / 2 : -.pi / 2)
                }
            }
            t -= piece.length
        }
        let n = vertices.count
        return atan2(vertices[n - 1].y - vertices[n - 2].y, vertices[n - 1].x - vertices[n - 2].x)
    }

    static func dist(_ a: CGPoint, _ b: CGPoint) -> CGFloat { hypot(b.x - a.x, b.y - a.y) }

    static func unit(_ a: CGPoint, _ b: CGPoint) -> CGVector {
        let l = max(dist(a, b), 1e-9)
        return CGVector(dx: (b.x - a.x) / l, dy: (b.y - a.y) / l)
    }
}

/// The arrow head: an isosceles triangle pointing +x in head-local space, apex `headApexPast(dir)` past the head cell
/// centre, base `Metrics.headBase` wide, `Metrics.headLength` long, corners rounded `Metrics.headCornerRadius` (all × pitch,
/// PathCore C1, VERIFIED STYLE §A). Rotated to the direction by the layer transform.
enum HeadShape {
    static func path(pitch p: CGFloat, dir: Dir, spec: HeadSpec? = nil) -> CGPath {
        let apex: CGFloat, len: CGFloat, half: CGFloat, r: CGFloat
        if let s = spec {
            // every measure is VISIBLE: solve the sharp triangle whose rounded outline shows `tip`, `base` and `width`
            var a = s.sharpApex
            var w = s.width
            for _ in 0..<6 {
                let probe = triangle(apex: CGFloat(a) * p, len: CGFloat(a - s.base) * p, half: CGFloat(w) * p / 2,
                                     r: CGFloat(s.corner) * p).boundingBoxOfPath
                w += s.width - Double(probe.height / p)
                a += s.tip - Double(probe.maxX / p)
            }
            apex = CGFloat(a) * p
            len = CGFloat(a - s.base) * p
            half = CGFloat(w) * p / 2
            r = CGFloat(s.corner) * p
        } else {
            apex = CGFloat(Metrics.headApexPast(dir)) * p
            len = CGFloat(Metrics.headLength) * p
            half = CGFloat(Metrics.headBase) * p / 2
            r = CGFloat(Metrics.headCornerRadius) * p
        }
        return triangle(apex: apex, len: len, half: half, r: r)
    }

    private static func triangle(apex: CGFloat, len: CGFloat, half: CGFloat, r: CGFloat) -> CGPath {
        let a = CGPoint(x: apex, y: 0)
        let b = CGPoint(x: apex - len, y: -half)
        let c = CGPoint(x: apex - len, y: half)
        let path = CGMutablePath()
        path.move(to: CGPoint(x: apex - len, y: 0))
        path.addArc(tangent1End: c, tangent2End: a, radius: r)
        path.addArc(tangent1End: a, tangent2End: b, radius: r)
        path.addArc(tangent1End: b, tangent2End: c, radius: r)
        path.closeSubpath()
        return path
    }
}

/// One stage's drawing geometry: pitch, stroke width, fillet, head paths per direction and the path builders.
struct BoardGeometry {
    let layout: BoardLayout
    let pitch: CGFloat
    let lineWidth: CGFloat
    let fillet: CGFloat
    let tailExtend: CGFloat
    let dotDiameter: CGFloat
    private let heads: [Dir: CGPath]

    init(layout: BoardLayout, config: BoardConfig, screenScale: CGFloat) {
        self.layout = layout
        let p = CGFloat(layout.pitch)
        pitch = p
        var w = CGFloat(Metrics.stroke) * p
        if config.strokeSnapPx, screenScale > 0 {
            // the original draws the stroke in whole device pixels (motion §2.2: 0.221·pitch rounded to 1/3 pt)
            w = max(1 / screenScale, (w * screenScale).rounded() / screenScale)
        }
        lineWidth = w
        fillet = CGFloat(config.cornerFillet) * p
        tailExtend = CGFloat(config.tailExtend) * p
        dotDiameter = CGFloat(Metrics.dotDiameter) * p
        var h: [Dir: CGPath] = [:]
        for d in Dir.allCases { h[d] = HeadShape.path(pitch: p, dir: d, spec: config.head?[d]) }
        heads = h
    }

    func centre(_ c: Cell) -> CGPoint { layout.centre(c) }

    func headPath(_ d: Dir) -> CGPath { heads[d] ?? HeadShape.path(pitch: pitch, dir: d) }

    /// The head's visible tip past the head cell centre (pt): the hit test's apex point.
    func headTip(_ d: Dir, config: BoardConfig) -> CGFloat {
        CGFloat(config.head?[d]?.tip ?? Metrics.headApexPast(d)) * pitch
    }

    /// Half the size of the head layer's bounds (covers the triangle in every direction).
    var headExtent: CGFloat { pitch * 0.75 }

    /// The resting stroke of an arrow (tail extension + filleted corners, ends at the head cell centre).
    func restPath(_ a: ArrowSpec) -> ArrowPath {
        ArrowPath(points: a.cells.map(centre), fillet: fillet, startExtend: tailExtend)
    }

    /// The path an exit or bump slides along: the arrow's cells, then `cells` beyond (the plan's ray/tube cells), then a
    /// straight extension of `extend` pt in the last direction (to the far rect).
    func movingPath(_ a: ArrowSpec, beyond cells: [Cell], extend: CGFloat) -> ArrowPath {
        var pts = a.cells.map(centre)
        pts.append(contentsOf: cells.map(centre))
        if extend > 0 {
            let n = pts.count
            let d = n >= 2 ? ArrowPath.unit(pts[n - 2], pts[n - 1]) : dirVector(a.dir)
            let e = pts[n - 1]
            pts.append(CGPoint(x: e.x + d.dx * extend, y: e.y + d.dy * extend))
        }
        return ArrowPath(points: pts, fillet: fillet, startExtend: tailExtend)
    }

    /// Distance from `p` along `d` to the edge of `rect` (≥ 0).
    static func distanceToEdge(from p: CGPoint, dir d: CGVector, in rect: CGRect) -> CGFloat {
        if d.dx > 0.5 { return max(0, rect.maxX - p.x) }
        if d.dx < -0.5 { return max(0, p.x - rect.minX) }
        if d.dy > 0.5 { return max(0, rect.maxY - p.y) }
        return max(0, p.y - rect.minY)
    }
}

// No extensions on PathCore types here (C1 adds `head`/`tail` helpers in its own files; a same-named app extension
// would make every call ambiguous). Board code uses these free helpers instead.
@inline(__always) func headCell(_ a: ArrowSpec) -> Cell { a.cells[a.cells.count - 1] }
@inline(__always) func dirVector(_ d: Dir) -> CGVector { CGVector(dx: CGFloat(d.dc), dy: CGFloat(d.dr)) }
