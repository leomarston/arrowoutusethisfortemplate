import UIKit
import PathCore

// B2 (SPEC-architecture §5.6 "door + lock"; CONSISTENCY O-23 / §21.11: doors are a CODE-DRAWN 9-SLICE SHUTTER + the
// `lockHex` sprite, so every size renders — L1–150 need 48 sizes, the runtime generator any; art/STYLE.md §A.2 "Door").
// The 9-slice source is our own art pipeline's `doorW4H8` (drawn at the design pitch 32 pt = 96 px per cell, anchor = the
// block's top-left at (3, 3) pt): its header rows (0–1: frame top, rivets, purple inner frame, the first slat), one
// middle slat row (row 2: STYLE "ONE PER CELL ROW, seam on every row boundary") and its foot row (row 7 + the baked
// shadow). A door of W × H cells = the top slice + (H − 3) copies of the slat row (a CAReplicatorLayer, one per cell
// row) + the foot slice; each slice stretches only horizontally between fixed posts (contentsCenter; contentsScale =
// 96 px / pitch keeps the posts and rivets at their measured pitch fractions). The lock sits on the door's vertical centre
// line 0.18 p below the block centre (STYLE: 0.17–0.20, "use 0.18").
// Burst (SPEC-motion-audio §3.5.2 #7–#9, at the key's computed burst time, render-exact): the door and its lock vanish,
// a white flash on the lock (r 0.9 p, 0 → 1 → 0 over 0.216 s), ≈ 60 door shards.

@MainActor final class BoardArt {
    let cache: SpriteCache
    private(set) var doorTop: CGImage?
    private(set) var doorMid: CGImage?
    private(set) var doorBottom: CGImage?
    private(set) var doorWhole: CGImage?
    /// Source px per cell of the door slices and the fixed post width in px.
    private(set) var doorCellPx: CGFloat = 96
    private(set) var doorMarginPx: CGFloat = 9
    private(set) var doorPostPx: CGFloat = 78
    private(set) var keyOnly: CGImage?
    private var built = false

    static let names = ["doorW4H8", "lockHex", "keyOnArrow", "pipeMouth", "pipeCounter", "doorShards", "pipeShards",
                        "boardTrailStar", "boxRing"] + CornerNode.spriteIDs      // FIX-2 A (L02): the 8 facing layers + cornerWedge

    init(cache: SpriteCache) { self.cache = cache }

    func image(_ id: String) -> CGImage? { cache.image(id) }

    /// Crops the door slices and filters the key-only image (once; warm-up).
    func build() {
        guard !built else { return }
        built = true
        if let d = cache.image("doorW4H8") {
            doorWhole = d
            let w = CGFloat(d.width), h = CGFloat(d.height)
            // 4 × 8 cells + a margin all round: cell px from the width
            let margin = (w - 4 * ((h - w) / 4)) / 2                    // h − w = 4 cells
            let cell = (h - w) / 4
            doorCellPx = cell
            doorMarginPx = margin
            doorPostPx = margin + 0.72 * cell
            let topH = margin + 2 * cell
            doorTop = d.cropping(to: CGRect(x: 0, y: 0, width: w, height: topH.rounded()))
            doorMid = d.cropping(to: CGRect(x: 0, y: topH.rounded(), width: w, height: cell.rounded()))
            let bottomY = (margin + 7 * cell).rounded()
            doorBottom = d.cropping(to: CGRect(x: 0, y: bottomY, width: w, height: h - bottomY))
        }
        if let k = cache.image("keyOnArrow") { keyOnly = Self.withoutRibbon(k) }
    }

    /// The key sprite without its ribbon loop (the hanger vanishes at the tap, MA §3.5.2 #1): only the GOLD pixels stay
    /// (r ≥ g ≥ b + 25: #FFC93A … #B35A00 and their bevels); the ribbon (#C020FF…#D948FF), its white highlights and the
    /// grey drop shadow go (a flying key casts no board shadow).
    static func withoutRibbon(_ img: CGImage) -> CGImage? {
        let w = img.width, h = img.height
        guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                                  space: CGColorSpaceCreateDeviceRGB(),
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
        ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
        guard let data = ctx.data else { return nil }
        let px = data.bindMemory(to: UInt8.self, capacity: w * h * 4)
        for i in 0..<(w * h) {
            let r = Int(px[4 * i]), g = Int(px[4 * i + 1]), b = Int(px[4 * i + 2]), a = Int(px[4 * i + 3])
            guard a > 0 else { continue }
            let gold = r > 70 && r >= g && g >= b + 25
            if !gold { px[4 * i] = 0; px[4 * i + 1] = 0; px[4 * i + 2] = 0; px[4 * i + 3] = 0 }
        }
        return ctx.makeImage()
    }
}

@MainActor final class DoorNode {
    let id: ObstacleID
    let spec: ObstacleSpec
    /// The door's cell block (content space).
    let block: CGRect
    let root = CALayer()
    let lock = CALayer()
    let lockCentre: CGPoint
    /// Where a key's tip goes: the keyhole (STYLE: keyhole circle at y −0.20 of the lock).
    let keyhole: CGPoint
    var state = "locked"
    /// The arrows under it (attached, still covered, from the key's dispatch on).
    var revealsAttached = false

    init(spec: ObstacleSpec, geo: BoardGeometry, art: BoardArt, scale: CGFloat) {
        id = spec.id
        self.spec = spec
        let p = geo.pitch
        let cs = spec.cells.isEmpty ? [Cell(0, 0)] : spec.cells
        let minC = cs.map(\.c).min()!, maxC = cs.map(\.c).max()!
        let minR = cs.map(\.r).min()!, maxR = cs.map(\.r).max()!
        let tl = geo.centre(Cell(minC, minR))
        block = CGRect(x: tl.x - p / 2, y: tl.y - p / 2, width: CGFloat(maxC - minC + 1) * p, height: CGFloat(maxR - minR + 1) * p)
        let rows = maxR - minR + 1
        let k = p / art.doorCellPx                                   // content pt per source px
        let m = art.doorMarginPx * k
        let outer = block.insetBy(dx: -m, dy: -m)
        root.frame = outer
        let w = outer.width
        let centerX = art.doorPostPx / CGFloat(art.doorWhole?.width ?? 402)
        let centre = CGRect(x: centerX, y: 0, width: max(0.01, 1 - 2 * centerX), height: 1)
        func slice(_ img: CGImage?, y: CGFloat, h: CGFloat) -> CALayer {
            let l = CALayer()
            l.contents = img
            l.contentsScale = 1 / k
            l.contentsCenter = centre
            l.contentsGravity = .resize
            l.frame = CGRect(x: 0, y: y, width: w, height: h)
            return l
        }
        if rows >= 3, let top = art.doorTop, let mid = art.doorMid, let bottom = art.doorBottom {
            let topH = CGFloat(top.height) * k
            root.addSublayer(slice(top, y: 0, h: topH))
            let middle = rows - 3
            if middle > 0 {
                let rep = CAReplicatorLayer()
                rep.frame = CGRect(x: 0, y: topH, width: w, height: CGFloat(middle) * p)
                rep.instanceCount = middle
                rep.instanceTransform = CATransform3DMakeTranslation(0, p, 0)
                rep.addSublayer(slice(mid, y: 0, h: p))
                root.addSublayer(rep)
            }
            let bh = CGFloat(bottom.height) * k
            root.addSublayer(slice(bottom, y: outer.height - bh, h: bh))
        } else if let whole = art.doorWhole {
            let l = CALayer()
            l.contents = whole
            l.contentsGravity = .resize
            l.frame = CGRect(origin: .zero, size: outer.size)
            root.addSublayer(l)
        }
        lockCentre = CGPoint(x: block.midX, y: block.midY + 0.18 * p)
        keyhole = CGPoint(x: lockCentre.x, y: lockCentre.y - 0.20 * p)
        if let li = art.image("lockHex") {
            lock.contents = li
            lock.contentsGravity = .resize
            lock.bounds = CGRect(x: 0, y: 0, width: CGFloat(li.width) * p / 96, height: CGFloat(li.height) * p / 96)
            lock.position = CGPoint(x: lockCentre.x - outer.minX, y: lockCentre.y - outer.minY)
            root.addSublayer(lock)
        }
        root.contentsScale = scale
    }

    /// Hides the door + lock at `at` seconds after `begin` (render-exact) and plays the lock flash in `fxRoot`.
    func burst(begin: CFTimeInterval, at: Double, fxRoot: CALayer, fx: EffectsConfig, pitch p: CGFloat) {
        state = "opening"
        Anim.switchOpacity(root, from: 1, to: 0, begin: begin, at: at, key: "burst")
        // FIX-V2 F-05: a soft white GLOW (the phone's burst flash reads as a bright bloom ≈ 1.6 × the key.flashPitch radius, its
        // core solid to ~0.35 of it), not a hard disc
        let r = CGFloat(fx.lockFlashPitch) * p * 1.6
        let flash = CAGradientLayer()
        flash.type = .radial
        flash.colors = [UIColor.white.cgColor, UIColor.white.cgColor, UIColor(red: 1, green: 0.95, blue: 0.81, alpha: 0.6).cgColor,
                        UIColor(red: 1, green: 0.81, blue: 0.42, alpha: 0).cgColor]
        flash.zPosition = 100                                           // over the debris (same parent as the shard pool)
        flash.locations = [0, 0.3, 0.55, 1]
        flash.startPoint = CGPoint(x: 0.5, y: 0.5)
        flash.endPoint = CGPoint(x: 1, y: 1)
        flash.bounds = CGRect(x: 0, y: 0, width: 2 * r, height: 2 * r)
        flash.actions = ["position": NSNull(), "bounds": NSNull()]
        flash.position = lockCentre
        flash.opacity = 0
        let d = max(0.05, fx.lockFlashDur)
        let a = Anim.keyframes("opacity", [0, 1, 0], times: [0, min(0.017, d / 3), d], duration: d, begin: begin + at)
        a.fillMode = .forwards
        flash.add(a, forKey: "flash")
        fxRoot.addSublayer(flash)
        Anim.beat(on: flash, key: "flashEnd", begin: begin + at, delay: d + 0.02) { [weak flash] _ in
            CATransaction.begin(); CATransaction.setDisableActions(true)
            flash?.removeFromSuperlayer()
            CATransaction.commit()
        }
    }

    /// Opened (the session's ack came back): hidden for good.
    func markOpen() {
        state = "open"
        root.opacity = 0
    }

    /// The shard spawn points and looks (60 over the block). FIX-V2 F-05 (S1-L33-key-first 1.68-2.00): chunky 3-D pieces
    /// (ShardArt) with grey drop shadows — mostly the blue slats' shards over the door's inside (55 %), orange (25 %) and
    /// purple (20 %) frame bits near its edge — not the flat 16 pt atlas flecks.
    func shardSpawn(count: Int, pitch p: CGFloat, rng: inout FXRandom) -> ([CGPoint], [ShardPool.Look]) {
        var pts: [CGPoint] = []
        var looks: [ShardPool.Look] = []
        for i in 0..<count {
            let f = Double(i) / Double(max(1, count))
            let atlas = f < 0.55 ? "sh3d.doorB" : (f < 0.80 ? "sh3d.doorO" : "sh3d.doorP")
            if f < 0.55 {
                pts.append(CGPoint(x: block.minX + (0.15 + 0.7 * CGFloat(rng.unit())) * block.width,
                                   y: block.minY + (0.15 + 0.8 * CGFloat(rng.unit())) * block.height))
            } else {
                // along the frame: a random edge, then a point on it
                let u = CGFloat(rng.unit()), e = Int(rng.unit() * 4)
                let x = e < 2 ? block.minX + u * block.width : (e == 2 ? block.minX + 0.08 * block.width : block.maxX - 0.08 * block.width)
                let y = e < 2 ? (e == 0 ? block.minY + 0.08 * block.height : block.maxY - 0.08 * block.height) : block.minY + u * block.height
                pts.append(CGPoint(x: x, y: y))
            }
            let s = CGFloat(f < 0.55 ? rng.range(0.42, 0.70) : rng.range(0.50, 0.85)) * p
            looks.append(ShardPool.Look(image: atlas, rect: ShardArt.rect(Int(rng.unit() * Double(ShardArt.cells))),
                                        size: CGSize(width: s, height: s), angle: CGFloat(rng.range(-0.8, 0.8)),
                                        shadow: atlas + ".shadow", shadowDY: 0.18 * p))
        }
        return (pts, looks)
    }

    /// FIX-V2 F-05: the door's own FRAME breaks into ~1-cell pieces cut from the door art (only the border ring of a cell
    /// grid over the door: the orange frame with its rivets and the purple inner frame; the slats go as the blue shards) and
    /// the lock hex into four chunks — the phone's big orange / purple pieces around the flash.
    func chunkSpawn(art: BoardArt, pitch p: CGFloat) -> ([CGPoint], [ShardPool.Look]) {
        var pts: [CGPoint] = []
        var looks: [ShardPool.Look] = []
        let outer = root.frame
        if art.doorWhole != nil {
            let cols = max(3, min(6, Int((outer.width / p).rounded())))
            let rows = max(3, min(8, Int((outer.height / p).rounded())))
            let cw = outer.width / CGFloat(cols), ch = outer.height / CGFloat(rows)
            for r in 0..<rows {
                for c in 0..<cols where r == 0 || r == rows - 1 || c == 0 || c == cols - 1 {
                    pts.append(CGPoint(x: outer.minX + (CGFloat(c) + 0.5) * cw, y: outer.minY + (CGFloat(r) + 0.5) * ch))
                    looks.append(ShardPool.Look(image: "doorW4H8",
                                                rect: CGRect(x: CGFloat(c) / CGFloat(cols), y: CGFloat(r) / CGFloat(rows),
                                                             width: 1 / CGFloat(cols), height: 1 / CGFloat(rows)),
                                                size: CGSize(width: cw * 0.94, height: ch * 0.94),
                                                angle: CGFloat((r * 7 + c * 3) % 5 - 2) * 0.06))
                }
            }
        }
        if lock.contents != nil {
            // the lock hex in four chunks (the phone's big purple lock pieces), each nudged a little off its quarter
            let b = lock.bounds.size
            for k in 0..<4 {
                let sx: CGFloat = k % 2 == 0 ? -1 : 1, sy: CGFloat = k < 2 ? -1 : 1
                pts.append(CGPoint(x: lockCentre.x + sx * b.width * 0.27, y: lockCentre.y + sy * b.height * 0.27))
                looks.append(ShardPool.Look(image: "lockHex", rect: CGRect(x: k % 2 == 0 ? 0 : 0.5, y: k < 2 ? 0 : 0.5, width: 0.5, height: 0.5),
                                            size: CGSize(width: b.width * 0.5, height: b.height * 0.5), angle: sx * sy * 0.22))
            }
        }
        return (pts, looks)
    }
}
