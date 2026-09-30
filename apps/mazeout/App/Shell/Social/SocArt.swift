import UIKit
import CoreGraphics

// SOCIAL SOC2 (SPEC-ui §1.5 `row.*` palette, §1.6.11 RankRow, §1.6.12 AvatarFrame, §2.16 row content). The static pieces of
// the CA list rows drawn ONCE with CoreGraphics (any thread; the social worker warms them with the first page) and shared by
// every row as layer contents: the five row faces (cream, the player's green, the Streak Race gold / silver / bronze), the
// avatar tiles (9 portraits × blue / green frame), the Streak Race score pills and the separator dots. Nothing here is a
// stand-in: the portraits are the shipped avatar renders (`Avatars`, S3), the frame recipe is AvatarFrameTile's (S3).

enum SocRowLook: Int, Sendable, CaseIterable {
    case cream, me, gold, silver, bronze

    /// Face gradient top → bottom, the top highlight, the lower lip gradient, the outline (SPEC-ui §1.5; VERIFIED meta-013 /
    /// meta-045 / store 6; outlines INFERRED from the captures' 1 pt dark edge).
    var colours: (face: [UInt32], highlight: UInt32, lip: [UInt32], outline: UInt32) {
        switch self {
        case .cream: return ([Skin.socialSocArtSocRowLookColoursCream0, Skin.socialSocArtSocRowLookColoursCream1, Skin.socialSocArtSocRowLookColoursCream2], Skin.socialSocArtSocRowLookColoursCream, [Skin.socialSocArtSocRowLookColoursCream0V2, Skin.socialSocArtSocRowLookColoursCream1V2], Skin.socialSocArtSocRowLookColoursCreamV2)
        case .me: return ([Skin.socialSocArtSocRowLookColoursMe0, Skin.socialSocArtSocRowLookColoursMe1, Skin.socialSocArtSocRowLookColoursMe2], Skin.socialSocArtSocRowLookColoursMe, [Skin.socialSocArtSocRowLookColoursMe0V2, Skin.socialSocArtSocRowLookColoursMe1V2], Skin.socialSocArtSocRowLookColoursMeV2)
        case .gold: return ([Skin.socialSocArtSocRowLookColoursGold0, Skin.socialSocArtSocRowLookColoursGold1, Skin.socialSocArtSocRowLookColoursGold2], Skin.socialSocArtSocRowLookColoursGold, [Skin.socialSocArtSocRowLookColoursGold0V2, Skin.socialSocArtSocRowLookColoursGold1V2], Skin.socialSocArtSocRowLookColoursGoldV2)
        case .silver: return ([Skin.socialSocArtSocRowLookColoursSilver0, Skin.socialSocArtSocRowLookColoursSilver1, Skin.socialSocArtSocRowLookColoursSilver2], Skin.socialSocArtSocRowLookColoursSilver, [Skin.socialSocArtSocRowLookColoursSilver0V2, Skin.socialSocArtSocRowLookColoursSilver1V2], Skin.socialSocArtSocRowLookColoursSilverV2)
        case .bronze: return ([Skin.socialSocArtSocRowLookColoursBronze0, Skin.socialSocArtSocRowLookColoursBronze1, Skin.socialSocArtSocRowLookColoursBronze2], Skin.socialSocArtSocRowLookColoursBronze, [Skin.socialSocArtSocRowLookColoursBronze0V2, Skin.socialSocArtSocRowLookColoursBronze1V2], Skin.socialSocArtSocRowLookColoursBronzeV2)
        }
    }

    /// The Streak Race score pill (SPEC-ui §2.16: a darker shade of the row; gold/silver/bronze VERIFIED store 6, the others
    /// INFERRED the same ~25 % darker shade).
    var pill: UInt32 {
        switch self {
        case .cream: return Skin.socialSocArtSocRowLookPillCream
        case .me: return Skin.socialSocArtSocRowLookPillMe
        case .gold: return Skin.socialSocArtSocRowLookPillGold
        case .silver: return Skin.socialSocArtSocRowLookPillSilver
        case .bronze: return Skin.socialSocArtSocRowLookPillBronze
        }
    }
}

enum SocArt {
    private static let lock = NSLock()
    nonisolated(unsafe) private static var images: [String: CGImage] = [:]

    private static func cached(_ key: String, _ make: () -> CGImage?) -> CGImage? {
        lock.lock()
        if let hit = images[key] { lock.unlock(); return hit }
        lock.unlock()
        guard let img = make() else { return nil }
        lock.lock(); images[key] = img; lock.unlock()
        return img
    }

    static func context(_ size: CGSize, _ scale: CGFloat) -> CGContext? {
        let w = max(1, Int((size.width * scale).rounded(.up))), h = max(1, Int((size.height * scale).rounded(.up)))
        guard let space = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: space,
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
        ctx.translateBy(x: 0, y: CGFloat(h))
        ctx.scaleBy(x: scale, y: -scale)          // y down, pt units
        ctx.setShouldAntialias(true)
        ctx.interpolationQuality = .high
        return ctx
    }

    static func cg(_ v: UInt32, _ a: CGFloat = 1) -> CGColor { UIColor(socHex: v, a).cgColor }

    static func gradient(_ stops: [UInt32]) -> CGGradient? {
        CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB), colors: stops.map { cg($0) } as CFArray, locations: nil)
    }

    /// A superellipse |x/a|^n + |y/b|^n = 1 over `r` (GlossyChrome's `Superellipse` recipe, as a CGPath for any thread).
    static func superellipse(_ r: CGRect, n: CGFloat) -> CGPath {
        let p = CGMutablePath()
        let a = r.width / 2, b = r.height / 2, cx = r.midX, cy = r.midY
        let steps = 96
        for i in 0...steps {
            let t = CGFloat(i) / CGFloat(steps) * 2 * .pi
            let c = cos(t), s = sin(t)
            let x = cx + a * (c < 0 ? -1 : 1) * pow(abs(c), 2 / n)
            let y = cy + b * (s < 0 ? -1 : 1) * pow(abs(s), 2 / n)
            if i == 0 { p.move(to: CGPoint(x: x, y: y)) } else { p.addLine(to: CGPoint(x: x, y: y)) }
        }
        p.closeSubpath()
        return p
    }

    // MARK: row faces

    /// A row face + lip (`size` = the face width × face height + the 4 pt lip; rr 10). The player's row is drawn at its own
    /// larger size (383.3 × 66.4, SPEC-ui `lb.rowMe`).
    static func rowFace(_ look: SocRowLook, size: CGSize, lip: CGFloat = 4, scale: CGFloat) -> CGImage? {
        cached("row|\(look.rawValue)|\(size.width)x\(size.height)|\(lip)@\(scale)") {
            guard let ctx = context(size, scale) else { return nil }
            let c = look.colours
            let face = CGRect(x: 0.5, y: 0.5, width: size.width - 1, height: size.height - lip - 0.5)
            let lipRect = CGRect(x: 0.5, y: lip, width: size.width - 1, height: size.height - lip - 0.5)
            let r: CGFloat = 10
            // lip (visible below the face) + outline
            ctx.addPath(CGPath(roundedRect: lipRect.insetBy(dx: -0.5, dy: -0.5), cornerWidth: r + 0.5, cornerHeight: r + 0.5, transform: nil))
            ctx.setFillColor(cg(c.outline)); ctx.fillPath()
            ctx.saveGState()
            ctx.addPath(CGPath(roundedRect: lipRect, cornerWidth: r, cornerHeight: r, transform: nil)); ctx.clip()
            if let g = gradient(c.lip) {
                ctx.drawLinearGradient(g, start: CGPoint(x: 0, y: lipRect.minY), end: CGPoint(x: 0, y: lipRect.maxY), options: [])
            }
            ctx.restoreGState()
            ctx.addPath(CGPath(roundedRect: face.insetBy(dx: -0.5, dy: -0.5), cornerWidth: r + 0.5, cornerHeight: r + 0.5, transform: nil))
            ctx.setFillColor(cg(c.outline)); ctx.fillPath()
            ctx.saveGState()
            ctx.addPath(CGPath(roundedRect: face, cornerWidth: r, cornerHeight: r, transform: nil)); ctx.clip()
            if let g = gradient(c.face) {
                ctx.drawLinearGradient(g, start: CGPoint(x: 0, y: face.minY), end: CGPoint(x: 0, y: face.maxY), options: [])
            }
            // the top highlight line
            ctx.setFillColor(cg(c.highlight))
            ctx.fill(CGRect(x: face.minX, y: face.minY, width: face.width, height: 1.6))
            ctx.restoreGState()
            return ctx.makeImage()
        }
    }

    // MARK: avatar tiles

    /// The portrait inside its blue (others) or green (the player) superellipse frame (AvatarFrameTile's recipe).
    static func avatarTile(_ index: Int, me: Bool, size: CGSize, scale: CGFloat) -> CGImage? {
        cached("avatar|\(index)|\(me)|\(size.width)x\(size.height)@\(scale)") {
            guard let ctx = context(size, scale) else { return nil }
            let n: CGFloat = 3.5
            let full = CGRect(origin: .zero, size: size)
            let ringT = size.width * 0.075
            let dark: UInt32 = me ? Skin.socialSocArtSocArtAvatarTileDarkMe : Skin.socialSocArtSocArtAvatarTileDarkNotMe
            let ring: [UInt32] = me ? [Skin.socialSocArtSocArtAvatarTileRing0, Skin.socialSocArtSocArtAvatarTileRing1, Skin.socialSocArtSocArtAvatarTileRing2] : [Skin.socialSocArtSocArtAvatarTileRing0V2, Skin.socialSocArtSocArtAvatarTileRing1V2, Skin.socialSocArtSocArtAvatarTileRing2V2]
            ctx.addPath(superellipse(full.insetBy(dx: 0.2, dy: 0.2), n: n)); ctx.setFillColor(cg(dark)); ctx.fillPath()
            ctx.saveGState()
            ctx.addPath(superellipse(full.insetBy(dx: 1.2, dy: 1.2), n: n)); ctx.clip()
            if let g = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB), colors: ring.map { cg($0) } as CFArray,
                                  locations: [0, 0.12, 1]) {
                ctx.drawLinearGradient(g, start: CGPoint(x: 0, y: 0), end: CGPoint(x: 0, y: size.height), options: [])
            }
            ctx.restoreGState()
            let inner = full.insetBy(dx: ringT, dy: ringT)
            let innerPath = superellipse(inner, n: n + 0.3)
            if let img = ArtStore.image(Avatars.art(index), maxPixel: Int((max(inner.width, inner.height) * scale).rounded(.up)) + 2)?.cgImage {
                ctx.saveGState()
                ctx.addPath(innerPath); ctx.clip()
                // aspect-fill the square portrait into the inner tile; CG draws images y-up, so flip locally
                let side = max(inner.width, inner.height)
                let dst = CGRect(x: inner.midX - side / 2, y: inner.midY - side / 2, width: side, height: side)
                ctx.translateBy(x: 0, y: dst.minY * 2 + dst.height)
                ctx.scaleBy(x: 1, y: -1)
                ctx.draw(img, in: dst)
                ctx.restoreGState()
            }
            ctx.addPath(innerPath)
            ctx.setStrokeColor(cg(me ? Skin.socialSocArtSocArtAvatarTileSetStrokeColorMe : Skin.socialSocArtSocArtAvatarTileSetStrokeColorNotMe))
            ctx.setLineWidth(max(1, size.width * 0.012))
            ctx.strokePath()
            return ctx.makeImage()
        }
    }

    // MARK: art ids

    /// A shipped raster as a CGImage (ArtStore's thread-safe decode), nil when missing (never a stand-in).
    static func art(_ a: UIArt, maxPixel: Int? = nil) -> CGImage? { ArtStore.image(a, maxPixel: maxPixel)?.cgImage }

    // MARK: small shapes

    /// The Streak Race score pill (rr 9) in the row's darker shade.
    static func pill(_ look: SocRowLook, size: CGSize, scale: CGFloat) -> CGImage? {
        cached("pill|\(look.rawValue)|\(size.width)x\(size.height)@\(scale)") {
            guard let ctx = context(size, scale) else { return nil }
            let r = CGRect(origin: .zero, size: size).insetBy(dx: 0.5, dy: 0.5)
            let rad = size.height * 0.34
            ctx.addPath(CGPath(roundedRect: r, cornerWidth: rad, cornerHeight: rad, transform: nil))
            ctx.setFillColor(cg(look.pill)); ctx.fillPath()
            ctx.saveGState()
            ctx.addPath(CGPath(roundedRect: r, cornerWidth: rad, cornerHeight: rad, transform: nil)); ctx.clip()
            ctx.setFillColor(cg(Skin.socialSocArtSocArtPillSetFillColor, 0.18))
            ctx.fill(CGRect(x: r.minX, y: r.minY, width: r.width, height: 2.2))     // a dark inner top shadow
            ctx.restoreGState()
            return ctx.makeImage()
        }
    }

    /// "• • •" (SPEC-ui §2.15.4: 3 cream dots ⌀6, centred, row height 36).
    static func separator(width: CGFloat, scale: CGFloat) -> CGImage? {
        cached("sep|\(width)@\(scale)") {
            let size = CGSize(width: width, height: 36)
            guard let ctx = context(size, scale) else { return nil }
            ctx.setFillColor(cg(Skin.socialSocArtSocArtSeparatorSetFillColor))
            for i in -1...1 {
                ctx.fillEllipse(in: CGRect(x: width / 2 + CGFloat(i) * 16 - 3, y: 15, width: 6, height: 6))
            }
            return ctx.makeImage()
        }
    }

    /// Renders / decodes everything a list snapshot's rows will point at, ON THE CALLING (worker) THREAD, so the main thread
    /// only hands cached images to layers (the first display of a face, a portrait or a badge never rasterises on main).
    static func warm(_ c: SocListContent, scale: CGFloat) {
        let geo: SocRowGeometry = c.kind == .streak ? .streakRace : .leaderboard
        var looks = Set<Int>(), avatars = Set<String>()
        for r in c.rows {
            if r.isMe {
                _ = rowFace(.me, size: CGSize(width: geo.meW, height: geo.meH), scale: scale)
            } else if looks.insert(r.look.rawValue).inserted {
                _ = rowFace(r.look, size: CGSize(width: geo.faceW, height: geo.faceH), scale: scale)
            }
            if avatars.insert("\(r.avatar)").inserted {
                _ = avatarTile(r.avatar, me: false, size: CGSize(width: 53, height: 53.4), scale: scale)
            }
            if r.isMe || c.kind == .streak { _ = pill(r.isMe ? .me : r.look, size: CGSize(width: 53.4, height: 33.4), scale: scale) }
        }
        for a in [UIArt.rankBadgeGold, .rankBadgeSilver, .rankBadgeBronze, .coinBowl, .scoreChip] { _ = art(a) }
        _ = separator(width: 393, scale: scale)
    }

    static func purge() {
        lock.lock(); images.removeAll(); lock.unlock()
    }
}
