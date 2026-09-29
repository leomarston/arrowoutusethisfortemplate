import Foundation
import CoreGraphics

// C1 (SPEC-architecture §4.2, D6). The board's content space at fit zoom. The ◆ BoardContract's `StageSetup.layout`
// carries it.
//
// Fit rule: pitch = min(play.w / (cols + 2), play.h / (rows + 2), maxPitch) — one empty margin cell all round. It
// reproduces all 30 recorded pitches (L32–L61) within 0.022 pt (GeometryTests). On every recorded board the WIDTH term
// binds (motion.md §2.1 reads the rule as width-only); the height term is the architecture's DECISION for boards taller
// than any recorded one, so a generated board never runs under the HUD.
//
// Zoom (motion.md §6.7 pass 2, VERIFIED): the limits are ABSOLUTE pitches — max 28.07 pt (a 12-col board opens at the cap
// and cannot zoom in), min 14.04 pt (L32/L47 at fit 17.87 zoom out to 0.786×; L062 at fit 14.0 cannot zoom out).

/// The board's content space at fit zoom: one empty margin cell all round.
public struct BoardLayout: Sendable, Equatable {
    /// pt per cell at fit = min(play.w/(cols+2), play.h/(rows+2), maxPitch).
    public let pitch: Double
    /// (cols+2, rows+2) × pitch.
    public let contentSize: CGSize
    /// Centre of cell (0,0) in content space = (1.5 p, 1.5 p).
    public let origin: CGPoint
    /// The absolute zoom cap in pt per cell (28.07).
    public let maxPitch: Double
    /// The absolute zoom floor in pt per cell (14.04).
    public let minPitch: Double
    /// The grid this layout was fitted for (0 × 0 for a hand-made layout).
    public let cols: Int
    public let rows: Int

    public init(pitch: Double, contentSize: CGSize, origin: CGPoint, maxPitch: Double = Metrics.maxPitch,
                minPitch: Double = Metrics.minPitch, cols: Int = 0, rows: Int = 0) {
        self.pitch = pitch; self.contentSize = contentSize; self.origin = origin
        self.maxPitch = maxPitch; self.minPitch = minPitch; self.cols = cols; self.rows = rows
    }

    public static func fit(grid: Grid, play: CGRect, maxPitch: Double = Metrics.maxPitch) -> BoardLayout {
        fit(grid: grid, play: play, maxPitch: maxPitch, minPitch: Metrics.minPitch)
    }

    /// The fit with an explicit zoom floor (board.json may carry both limits).
    public static func fit(grid: Grid, play: CGRect, maxPitch: Double, minPitch: Double) -> BoardLayout {
        let w = Double(play.width) / Double(grid.cols + 2)
        let h = Double(play.height) / Double(grid.rows + 2)
        let p = min(w, h, maxPitch)
        let size = CGSize(width: Double(grid.cols + 2) * p, height: Double(grid.rows + 2) * p)
        return BoardLayout(pitch: p, contentSize: size, origin: CGPoint(x: 1.5 * p, y: 1.5 * p), maxPitch: maxPitch,
                           minPitch: minPitch, cols: grid.cols, rows: grid.rows)
    }

    /// Centre of a cell in content space.
    @inline(__always) public func centre(_ c: Cell) -> CGPoint {
        CGPoint(x: Double(origin.x) + Double(c.c) * pitch, y: Double(origin.y) + Double(c.r) * pitch)
    }

    /// A point given in CELL coordinates (fractional column, row; (0, 0) = the centre of cell (0,0)) in content space.
    public func point(cellX x: Double, cellY y: Double) -> CGPoint {
        CGPoint(x: Double(origin.x) + x * pitch, y: Double(origin.y) + y * pitch)
    }

    /// The cell whose square contains `p` (content space; may lie outside the grid). A point exactly on a boundary
    /// belongs to the cell to its right / below (floor), so the midpoint between two columns resolves right (L52).
    @inline(__always) public func cell(at p: CGPoint) -> Cell {
        // + 1e-9 cell: a point ON a boundary (up to floating-point noise) resolves right / down deterministically.
        let x = (Double(p.x) - Double(origin.x)) / pitch + 0.5 + 1e-9
        let y = (Double(p.y) - Double(origin.y)) / pitch + 0.5 + 1e-9
        return Cell(Int(x.rounded(.down)), Int(y.rounded(.down)))
    }

    /// The grid's cells as a rect in content space (without the margin): (p, p) … (p·(cols+1), p·(rows+1)).
    public var gridRect: CGRect { CGRect(x: pitch, y: pitch, width: Double(cols) * pitch, height: Double(rows) * pitch) }

    /// The scroll view's minimum zoom (relative to fit): the absolute floor, never above 1 (a board whose fit pitch is
    /// at or below the floor cannot zoom out). At a 17.864 pt fit this is 0.786 = `Metrics.minZoomOfFit`.
    public var minZoom: Double { min(1, minPitch / pitch) }
    /// The scroll view's maximum zoom (relative to fit): an absolute 28.07 pt per cell, never below 1.
    public var maxZoom: Double { max(1, maxPitch / pitch) }

    /// Where the content's top-left lands when the content is centred in `play` at zoom 1 (screen pt).
    public func centredOrigin(in play: CGRect) -> CGPoint {
        CGPoint(x: Double(play.midX) - Double(contentSize.width) / 2, y: Double(play.midY) - Double(contentSize.height) / 2)
    }

    /// The screen position of a cell centre when the content is centred in `play` at zoom 1.
    public func screenCentre(_ c: Cell, in play: CGRect) -> CGPoint {
        let o = centredOrigin(in: play), p = centre(c)
        return CGPoint(x: o.x + p.x, y: o.y + p.y)
    }
}
