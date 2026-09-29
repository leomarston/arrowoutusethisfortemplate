import UIKit
import PathCore

// B1 (SPEC-architecture §5.6 "tape", §5.5 step 7; art/STYLE.md §A.2). Linked arrows: the pink tape sprite
// `tape{V|H}{lanes}` (art/ui/out, drawn at the 32 pt design pitch, scaled by pitch/32) centred on the bundle's cell block,
// OVER its arrows (tapeRoot). When the bundle exits the sprite rides with it (one common translation).

@MainActor enum TapeLayer {
    /// The sprite id of a tape obstacle: the override, else `tapeV<n>` for a band spanning one column (vertical on
    /// screen, the arrows run horizontally through it), `tapeH<n>` for a band spanning one row.
    static func spriteID(_ o: ObstacleSpec) -> String {
        if let s = o.sprite { return s }
        let cols = Set(o.cells.map(\.c)).count
        let rows = Set(o.cells.map(\.r)).count
        let lanes = max(o.cells.count, o.arrows.count)
        return rows >= cols ? "tapeV\(lanes)" : "tapeH\(lanes)"
    }

    /// One layer per tape obstacle (nil sprite → skipped, logged by the cache). Call inside a no-actions transaction.
    static func build(_ level: LevelSpec, geo: BoardGeometry, cache: SpriteCache, scale: CGFloat) -> [ObstacleID: CALayer] {
        var out: [ObstacleID: CALayer] = [:]
        for o in level.obstacles where o.kind == .tape && !o.cells.isEmpty {
            guard let img = cache.image(spriteID(o)) else { continue }
            let pts = o.cells.map(geo.centre)
            let minX = pts.map(\.x).min()!, maxX = pts.map(\.x).max()!
            let minY = pts.map(\.y).min()!, maxY = pts.map(\.y).max()!
            let k = geo.pitch / 32                                // the sprite's design pitch is 32 pt per cell
            let l = CALayer()
            l.contents = img
            l.contentsGravity = .resize
            l.contentsScale = scale
            l.bounds = CGRect(x: 0, y: 0, width: CGFloat(img.width) / 3 * k, height: CGFloat(img.height) / 3 * k)
            l.position = CGPoint(x: (minX + maxX) / 2, y: (minY + maxY) / 2)
            out[o.id] = l
        }
        return out
    }

    /// The tape sprites a level needs (preload).
    static func spriteIDs(_ level: LevelSpec) -> [String] {
        level.obstacles.filter { $0.kind == .tape }.map(spriteID)
    }
}
