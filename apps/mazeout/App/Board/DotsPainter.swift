import UIKit
import PathCore

// B1 (SPEC-architecture §5.5 step 5; research/motion.md §2.3, pass 2, VERIFIED shot 003 + P02 + S1-L48-play-intro).
// The phone draws a #C5E1FF disc (⌀ 0.192 pitch) under EVERY cell an arrow occupies at level start; the arrow's stroke
// hides it and a vacated cell simply shows it (a never-occupied cell has none). So "a dot appears on the frame the tail
// leaves its cell" is the arrow uncovering a disc that was always there — which also gives the bluish fringe at the
// rounded outer corners (73 fringes on shot 003) and the dot grid visible under not-yet-drawn arrows in the intro.
// One CAShapeLayer per stage holds every disc (built at load, ≤ 1 ms); revealed arrows add theirs (B2 reveals). The
// dots layer never animates on the tap path (no per-exit dot layers, so P3's dropped-dash pitfall cannot happen).

@MainActor final class DotsPainter {
    let layer = CAShapeLayer()
    private var path = CGMutablePath()
    private var count = 0

    init() {
        layer.fillColor = UIColor(red: 1, green: 221 / 255, blue: 176 / 255, alpha: 1).cgColor
        layer.strokeColor = nil
    }

    var dotCount: Int { count }

    /// Clears and sizes the layer for a stage. Call inside a no-actions transaction.
    func reset(frame: CGRect, color: CGColor, scale: CGFloat) {
        path = CGMutablePath()
        count = 0
        layer.frame = frame
        layer.fillColor = color
        layer.contentsScale = scale
        layer.path = nil
    }

    /// Adds a disc under each cell. Call inside a no-actions transaction.
    func add(cells: [Cell], geo: BoardGeometry) {
        guard !cells.isEmpty else { return }
        let r = geo.dotDiameter / 2
        for c in cells {
            let p = geo.centre(c)
            path.addEllipse(in: CGRect(x: p.x - r, y: p.y - r, width: 2 * r, height: 2 * r))
        }
        count += cells.count
        layer.path = path.copy()
    }
}
