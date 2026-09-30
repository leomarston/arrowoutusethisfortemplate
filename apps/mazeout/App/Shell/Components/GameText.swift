import SwiftUI
import CoreText
#if canImport(UIKit)
import UIKit
#endif

// SHELL S1 (SPEC-architecture §6.11, D15; design/fonts.md §5–§6). THE one outlined casual-game text: CoreText glyph paths of
// PCDisplay-Black (or -BlackItalic for event logos), drawn back to front (fonts.md §6 layer model):
//   1. drop    — the OUTLINE shape (glyph stroked 2·w with round joins + filled) in the drop colour, moved straight down, blur 0;
//   2. outline — the same shape in place (the outline sits OUTSIDE the full-weight glyph; the face is never eroded);
//   3. band    — "Paused" only: the glyph in the band colour moved down behind the face;
//   4. face    — the glyph filled with a vertical gradient (1 colour = flat) over the text's ink.
// Sizes/tracking/colours come from `GameTextStyle` values (ui.json `text.*`, SHELL's Tokens). Paths are cached per
// (string, font, size, tracking, fit). Copy is a `LocalizedStringResource`, never a `String` (memory
// localizedstringkey-not-string); `verbatim:` is for numbers, times and ids only.
// Portable: SwiftUI + CoreText only, compiles for iOS 18 AND macOS 14 (UI-ART's art/ui/tools/swiftui_render.swift compiles it
// next to GlossyChrome.swift; `GameText.registerFonts(in:)` registers the TTFs there).
// Fit: `maxWidth` shrinks one line to fit, never below `style.minScale` (0.7, SPEC.md §5 item 14: TR strings auto-shrink).
// Anchoring: the view's centre is the middle of the CAP HEIGHT at the first line's baseline and the middle of the advance
// box, so `position(x: centreX, y: style.capCentre(baseline:))` puts the baseline where the measurement says.

struct GameTextStyle: Hashable {
    enum Face: String, Hashable { case black, blackItalic }

    var size: CGFloat
    var tracking: CGFloat = 0
    var face: Face = .black
    /// Face fill, top → bottom; one colour = flat.
    var fill: [Color] = [.white]
    var outline: Color? = nil
    var outlineWidth: CGFloat = 0
    /// Drop distance (pt, straight down); the drop colour defaults to the outline colour.
    var drop: CGFloat = 0
    var dropColor: Color? = nil
    var band: Color? = nil
    var bandDY: CGFloat = 0
    var minScale: CGFloat = 0.7

    init(size: CGFloat, tracking: CGFloat = 0, face: Face = .black, fill: [Color] = [.white], outline: Color? = nil,
         outlineWidth: CGFloat = 0, drop: CGFloat = 0, dropColor: Color? = nil, band: Color? = nil, bandDY: CGFloat = 0,
         minScale: CGFloat = 0.7) {
        self.size = size; self.tracking = tracking; self.face = face; self.fill = fill; self.outline = outline
        self.outlineWidth = outlineWidth; self.drop = drop; self.dropColor = dropColor; self.band = band; self.bandDY = bandDY
        self.minScale = minScale
    }

    var postScriptName: String { face == .black ? GameText.blackPostScript : GameText.italicPostScript }

    /// The same style at another size (tracking, outline, drop and band scale with it: fonts.md "use the em value").
    func sized(_ newSize: CGFloat) -> GameTextStyle {
        guard size > 0 else { return self }
        let k = newSize / size
        var s = self
        s.size = newSize; s.tracking *= k; s.outlineWidth *= k; s.drop *= k; s.bandDY *= k
        return s
    }

    /// The y of the view centre for a baseline at `baseline` (cap middle above the baseline).
    func capCentre(baseline: CGFloat) -> CGFloat { baseline - GameText.capHeight(postScriptName: postScriptName, size: size) / 2 }
}

/// One laid-out line: glyph outlines in pt, y down, x = 0 at the start of the advance box, y = 0 on the baseline.
final class GameTextLayout {
    let text: String
    let path: CGPath
    let fontSize: CGFloat
    let tracking: CGFloat
    /// Advance width without the trailing tracking.
    let advance: CGFloat
    let ascent: CGFloat
    let descent: CGFloat
    let capHeight: CGFloat
    /// Ink bounds of the glyphs (pt, same space as `path`).
    let inkBounds: CGRect
    let glyphCount: Int
    /// PostScript name of every font CoreText actually drew with (fallback detection).
    let runFonts: Set<String>

    init(text: String, path: CGPath, fontSize: CGFloat, tracking: CGFloat, advance: CGFloat, ascent: CGFloat, descent: CGFloat,
         capHeight: CGFloat, glyphCount: Int, runFonts: Set<String>) {
        self.text = text; self.path = path; self.fontSize = fontSize; self.tracking = tracking; self.advance = advance
        self.ascent = ascent; self.descent = descent; self.capHeight = capHeight; self.glyphCount = glyphCount
        self.runFonts = runFonts
        let b = path.boundingBoxOfPath
        inkBounds = b.isNull ? CGRect(x: 0, y: -capHeight, width: max(advance, 1), height: capHeight) : b
    }

    /// FIX-2 A (V3-10): a count-bounded LRU (it was cleared whole past 800 entries: every visible string laid out again).
    static let cache = BoundedCache<String, GameTextLayout>(limit: 800)

    /// Lays out `text` (one line) in `postScriptName` at `size` with `tracking`; `maxWidth` shrinks it to fit, never below
    /// `minScale` × size.
    static func make(_ text: String, postScriptName: String, size: CGFloat, tracking: CGFloat, maxWidth: CGFloat? = nil,
                     minScale: CGFloat = 0.7) -> GameTextLayout {
        let key = "\(postScriptName)|\(size)|\(tracking)|\(maxWidth ?? -1)|\(minScale)|\(text)"
        if let hit = cache.get(key) { return hit }
        var layout = build(text, postScriptName: postScriptName, size: size, tracking: tracking)
        if let w = maxWidth, w > 0, layout.advance > w {
            FitLedger.note("gametext", text: text, need: w / layout.advance, floor: minScale, box: w)
            let k = max(minScale, (w / layout.advance * 1000).rounded(.down) / 1000)
            layout = build(text, postScriptName: postScriptName, size: size * k, tracking: tracking * k)
        }
        cache.set(key, layout, cost: 1)
        return layout
    }

    static func font(_ postScriptName: String, _ size: CGFloat) -> CTFont {
        CTFontCreateWithName(postScriptName as CFString, size, nil)
    }

    private static func build(_ text: String, postScriptName: String, size: CGFloat, tracking: CGFloat) -> GameTextLayout {
        // B3: PC Display + the bold fallback cascade (FontCascade); every run's glyphs become paths below, so the outline,
        // drop and band follow a fallback glyph exactly as they follow a PC Display one.
        let face = FontCascade.face(for: text)
        let font = FontCascade.font(postScriptName, size, face: face)
        var attrs: [NSAttributedString.Key: Any] = [
            NSAttributedString.Key(kCTFontAttributeName as String): font,
            NSAttributedString.Key(kCTKernAttributeName as String): tracking,
        ]
        if let lang = FontCascade.language(for: text, face: face) {
            attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = lang
        }
        let line = CTLineCreateWithAttributedString(NSAttributedString(string: text.isEmpty ? " " : text, attributes: attrs))
        let typographic = CGFloat(CTLineGetTypographicBounds(line, nil, nil, nil))
        let advance = max(0, typographic - CGFloat(CTLineGetTrailingWhitespaceWidth(line)) - (text.isEmpty ? 0 : tracking))
        let path = CGMutablePath()
        var count = 0
        var fonts: Set<String> = []
        // B3: the fallback faces have no italic; under PC Display Black Italic (the event letterings) their glyphs take the
        // italic's slant, so a CJK / Greek / Arabic lettering leans with its Latin neighbours
        let slant = CTFontGetSlantAngle(font)
        let oblique = slant != 0 ? CGAffineTransform(a: 1, b: 0, c: tan(-slant * .pi / 180), d: 1, tx: 0, ty: 0) : nil
        for run in CTLineGetGlyphRuns(line) as! [CTRun] {
            let runAttrs = CTRunGetAttributes(run) as NSDictionary
            let runFont: CTFont = runAttrs[kCTFontAttributeName as String].map { $0 as! CTFont } ?? font
            let runName = CTFontCopyPostScriptName(runFont) as String
            fonts.insert(runName)
            let shear = runName != postScriptName ? oblique : nil
            let n = CTRunGetGlyphCount(run)
            var ids = [CGGlyph](repeating: 0, count: n)
            var pos = [CGPoint](repeating: .zero, count: n)
            CTRunGetGlyphs(run, CFRange(location: 0, length: n), &ids)
            CTRunGetPositions(run, CFRange(location: 0, length: n), &pos)
            for k in 0..<n {
                guard let gp = CTFontCreatePathForGlyph(runFont, ids[k], nil), !gp.isEmpty else { continue }
                let t = CGAffineTransform(translationX: pos[k].x, y: 0).scaledBy(x: 1, y: -1)
                path.addPath(gp, transform: shear.map { $0.concatenating(t) } ?? t)
                count += 1
            }
        }
        return GameTextLayout(text: text, path: path, fontSize: size, tracking: tracking, advance: advance,
                              ascent: CTFontGetAscent(font), descent: CTFontGetDescent(font), capHeight: CTFontGetCapHeight(font),
                              glyphCount: count, runFonts: fonts)
    }
}

struct GameText: View {
    /// The skin's faces (skin/fonts.json -> SkinData.generated.swift).
    static let blackPostScript = SkinFonts.black
    static let italicPostScript = SkinFonts.blackItalic

    let text: String
    let style: GameTextStyle
    var maxWidth: CGFloat?

    /// Language copy (resolved through the strings catalogue).
    init(_ resource: LocalizedStringResource, style: GameTextStyle, maxWidth: CGFloat? = nil) {
        self.text = String(localized: resource)
        self.style = style
        self.maxWidth = maxWidth
    }

    /// Non-language text only: numbers, times, ids.
    init(verbatim: String, style: GameTextStyle, maxWidth: CGFloat? = nil) {
        self.text = verbatim
        self.style = style
        self.maxWidth = maxWidth
    }

    var layout: GameTextLayout {
        GameTextLayout.make(text, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking,
                            maxWidth: maxWidth, minScale: style.minScale)
    }

    /// Outline, drop and band scaled with any shrink.
    var effective: GameTextStyle {
        let l = layout
        return l.fontSize == style.size ? style : style.sized(l.fontSize)
    }

    @Environment(\.displayScale) private var displayScale
    /// FIX-A1: inside the Loading warm-up a missing raster is made off the main thread (see `gameTextDeferred`).
    @Environment(\.gameTextDeferred) private var deferred

    /// The raster's size and the layout's origin inside it: the frame is centred on the advance's middle and the cap middle
    /// (`capStyle` = the unshrunk style whose cap height sets the middle). FIX-2 B: shared with `GlyphRunText`.
    static func rasterGeometry(_ l: GameTextLayout, style st: GameTextStyle, capStyle: GameTextStyle) -> (size: CGSize, origin: CGPoint) {
        let pad = st.outlineWidth + 1.5
        let halfW = max(l.advance / 2, l.advance / 2 - l.inkBounds.minX, l.inkBounds.maxX - l.advance / 2) + pad
        let centreY = -GameText.capHeight(postScriptName: capStyle.postScriptName, size: capStyle.size) / 2   // cap middle (unshrunk)
        let up = max(l.ascent, -l.inkBounds.minY) + pad - (-centreY)
        let down = max(l.descent, l.inkBounds.maxY) + pad + max(st.drop, st.bandDY) - centreY
        let halfH = max(up, down)
        let size = CGSize(width: halfW * 2, height: halfH * 2)
        return (size, CGPoint(x: size.width / 2 - l.advance / 2, y: size.height / 2 - centreY))
    }

    /// FIX-2 A (V3-04): makes the rasters of `texts` exactly as `GameText(verbatim:style:maxWidth:)` draws them at `scale` (same
    /// layout, fit, geometry and key), OFF the main thread, for those not cached yet — the HUD timer asks for its next seconds,
    /// so a tick composites a cached image instead of rasterising the new time on the main thread (3-11 ms a tick, V3).
    static func prefetch(verbatim texts: [String], style: GameTextStyle, maxWidth: CGFloat?, scale: CGFloat) {
        for text in texts {
            let l = GameTextLayout.make(text, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking,
                                        maxWidth: maxWidth, minScale: style.minScale)
            let st = l.fontSize == style.size ? style : style.sized(l.fontSize)
            let g = rasterGeometry(l, style: st, capStyle: style)
            _ = GameTextRaster.cachedOrPrefetch(l, style: st, size: g.size, origin: g.origin, scale: max(scale, 1))
        }
    }

    var body: some View {
        let l = layout
        let st = effective
        // Rasterised ONCE per (text, style, fit, scale) with CoreGraphics and cached: a popup or page opening only composites
        // images (a Canvas re-rasterised every label on the main thread at every presentation: 50-60 ms frames, S1 profile).
        let (size, origin) = Self.rasterGeometry(l, style: st, capStyle: style)
        let scale = max(displayScale, 1)
        Group {
            if let img = deferred ? GameTextRaster.cachedOrPrefetch(l, style: st, size: size, origin: origin, scale: scale)
                                  : GameTextRaster.image(l, style: st, size: size, origin: origin, scale: scale) {
                Image(decorative: img, scale: max(displayScale, 1)).resizable().interpolation(.high)
            } else {
                Color.clear
            }
        }
        .frame(width: size.width, height: size.height)
        .allowsHitTesting(false)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(verbatim: text))
        .accessibilityAddTraits(.isStaticText)
    }

    /// Draws a layout (origin: advance start, baseline) with the §6 passes.
    static func draw(_ l: GameTextLayout, style: GameTextStyle, in ctx: inout GraphicsContext) {
        let p = Path(l.path)
        let w = style.outlineWidth
        let joins = StrokeStyle(lineWidth: 2 * w, lineCap: .round, lineJoin: .round)
        if style.drop > 0, let dc = style.dropColor ?? style.outline ?? style.fill.last {
            var c = ctx
            c.translateBy(x: 0, y: style.drop)
            if w > 0 { c.stroke(p, with: .color(dc), style: joins) }
            c.fill(p, with: .color(dc))
        }
        if let oc = style.outline, w > 0 {
            ctx.stroke(p, with: .color(oc), style: joins)
            ctx.fill(p, with: .color(oc))
        }
        if let band = style.band, style.bandDY > 0 {
            var c = ctx
            c.translateBy(x: 0, y: style.bandDY)
            c.fill(p, with: .color(band))
        }
        if style.fill.count > 1 {
            let b = l.inkBounds
            ctx.fill(p, with: .linearGradient(Gradient(colors: style.fill), startPoint: CGPoint(x: 0, y: b.minY),
                                              endPoint: CGPoint(x: 0, y: b.maxY)))
        } else {
            ctx.fill(p, with: .color(style.fill.first ?? .white))
        }
    }

    // MARK: font helpers (portable)

    nonisolated(unsafe) private static var capCache: [String: CGFloat] = [:]
    private static let capLock = NSLock()

    /// Cap height of the face at `size` (pt).
    static func capHeight(postScriptName: String, size: CGFloat) -> CGFloat {
        capLock.lock(); defer { capLock.unlock() }
        if let per = capCache[postScriptName] { return per * size }
        let per = CTFontGetCapHeight(GameTextLayout.font(postScriptName, 100)) / 100
        capCache[postScriptName] = per
        return per * size
    }

    /// B3: PC Display with the bold fallback cascade as a SwiftUI font, for the few SwiftUI `Text` / `TextField` runs (the
    /// Terms / Privacy pages, the username fields): a CJK / Arabic / Greek … glyph there is as heavy as in GameText.
    static func pageFont(_ size: CGFloat) -> Font {
        Font(FontCascade.font(blackPostScript, size, face: FontCascade.appFace))
    }

    /// True when the resolved app language is Turkish (CoreText then applies the TRK i/İ forms).
    static var isTurkish: Bool {
        (Bundle.main.preferredLocalizations.first ?? Locale.current.language.languageCode?.identifier ?? "en").hasPrefix("tr")
    }

    /// Registers the TTFs of a folder for this process (the macOS art renderer; the app uses UIAppFonts).
    static func registerFonts(in directory: URL) {
        let files = (try? FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)) ?? []
        for url in files where url.pathExtension.lowercased() == "ttf" {
            CTFontManagerRegisterFontsForURL(url as CFURL, .process, nil)
        }
    }
}

/// FIX-A1: true inside the Loading warm-up (RootView `PopupPrewarm`): a GameText whose raster the cache does not hold yet
/// draws nothing and has the raster made OFF the main thread (`GameTextRaster.cachedOrPrefetch`). The warm-up items are
/// invisible — only the cache matters — so a warm-up frame pays the view graph, not the glyph strokes (a fresh install's
/// warm-up spent 185 ms of its one long frame in `strokeFill`, build/feel/trace/fresh-launch.trace).
private struct GameTextDeferredKey: EnvironmentKey { static let defaultValue = false }
extension EnvironmentValues {
    var gameTextDeferred: Bool {
        get { self[GameTextDeferredKey.self] }
        set { self[GameTextDeferredKey.self] = newValue }
    }
}

/// GameText's pixels: the §6 passes drawn with CoreGraphics into a bitmap once per key, cached. FIX-2 A (V3-10): a BYTE-bounded
/// LRU (`byteLimit`, 64 MB of bitmaps). It was cleared whole past 400 entries — the raster memory cycled 5-20 MB and every
/// visible string was rasterised again on the main thread after each clear (V3: the home footprint dropped 18 MB at L12, then
/// climbed ~1 MB a level).
enum GameTextRaster {
    struct Key: Hashable {
        let text: String; let font: String; let size: CGFloat; let tracking: CGFloat; let style: GameTextStyle
        let w: CGFloat; let h: CGFloat; let ox: CGFloat; let oy: CGFloat; let scale: CGFloat
        var pass: Pass = .all
        var faceSpan: ClosedRange<CGFloat>? = nil
    }

    /// FIX-2 lane B (L28): one of the §6 passes alone, so a run of glyph rasters can be composited pass by pass in the whole
    /// raster's painter's order (every drop, then every outline, every band, every face — `GlyphRunText`). `.all` = the label.
    enum Pass: Hashable, CaseIterable { case all, drop, outline, band, face }
    // FIX-2 A: 16 MB evicted the Loading warm-up's popup rasters (V3-07). FIX-2 A-R: 64 MB — at 32 MB only 101-108 of the
    // warm-up's rasters were left when home came up (the count-bounded cache before FIX-2 A kept all 317-326), so an event
    // page's or a popup's first open drew its labels on the main thread again (Up & Away from the home queue: 45-48 misses, cut
    // 68-96 ms CPU vs 41-70 before FIX-2 A); at 64 MB 254-259 are left (20 misses, cut 40-69 ms), in play +5-7 MB footprint.
    // `-pc.glyphMB N` sets it for an A/B (build/p/FIX2/A-R/perf/ab4-*).
    static let byteLimit: Int = {
        let a = ProcessInfo.processInfo.arguments
        if let i = a.firstIndex(of: "-pc.glyphMB"), i + 1 < a.count, let mb = Int(a[i + 1]), mb > 0 { return mb * 1_048_576 }
        return 64 * 1_048_576
    }()
    static let cache = BoundedCache<Key, CGImage>(limit: byteLimit)
    private static let lock = NSLock()

    static var count: Int { cache.count }
    /// The bitmaps' bytes held now.
    static var bytes: Int { cache.totalCost }

    static func cost(_ img: CGImage) -> Int { img.bytesPerRow * img.height }

    static func image(_ l: GameTextLayout, style: GameTextStyle, size: CGSize, origin: CGPoint, scale: CGFloat,
                      pass: Pass = .all, faceSpan: ClosedRange<CGFloat>? = nil) -> CGImage? {
        let key = Key(text: l.text, font: style.postScriptName, size: l.fontSize, tracking: l.tracking, style: style,
                      w: size.width, h: size.height, ox: origin.x, oy: origin.y, scale: scale, pass: pass, faceSpan: faceSpan)
        if let hit = cache.get(key) { return hit }
        let t0 = logMisses ? CACurrentMediaTime() : 0
        guard let img = draw(l, style: style, colors: Colors(style), size: size, origin: origin, scale: scale, pass: pass,
                             faceSpan: faceSpan) else { return nil }
        cache.set(key, img, cost: cost(img))
        if logMisses, Thread.isMainThread {
            Log.mark("raster", String(format: "glyph miss \"%@\" %.1f pt %.2f ms on the main thread", l.text, l.fontSize,
                                      (CACurrentMediaTime() - t0) * 1000))
        }
        return img
    }

    /// FIX-2 A (measurement, `-pc.frameWatch`): log every glyph raster made on the main thread after the first screen (the
    /// first-presentation hunt: which label a page draws that no warm-up made).
    nonisolated(unsafe) static var logMisses = false

    /// FIX-2 B: whether `style` draws anything in `pass` (a glyph run skips the empty passes).
    static func draws(_ pass: Pass, _ style: GameTextStyle) -> Bool {
        switch pass {
        case .all, .face: return true
        case .drop: return style.drop > 0 && (style.dropColor ?? style.outline ?? style.fill.last) != nil
        case .outline: return style.outline != nil && style.outlineWidth > 0
        case .band: return style.band != nil && style.bandDY > 0
        }
    }

    /// FIX-A1 (the warm-up): the cached raster, or nil after queueing its render on a background queue (once per key).
    /// The colours are resolved here, on the caller's thread; the bitmap is drawn with CoreGraphics only.
    /// FIX-2 B review: also for one pass of a glyph run (`GlyphRunText` inside a warm-up); the defaults = the whole label.
    static func cachedOrPrefetch(_ l: GameTextLayout, style: GameTextStyle, size: CGSize, origin: CGPoint, scale: CGFloat,
                                 pass: Pass = .all, faceSpan: ClosedRange<CGFloat>? = nil) -> CGImage? {
        let key = Key(text: l.text, font: style.postScriptName, size: l.fontSize, tracking: l.tracking, style: style,
                      w: size.width, h: size.height, ox: origin.x, oy: origin.y, scale: scale, pass: pass, faceSpan: faceSpan)
        if let hit = cache.get(key) { return hit }
        lock.lock()
        if pending.contains(key) { lock.unlock(); return nil }
        pending.insert(key)
        lock.unlock()
        let colors = Colors(style)
        queue.async {
            let img = draw(l, style: style, colors: colors, size: size, origin: origin, scale: scale, pass: pass, faceSpan: faceSpan)
            if let img { cache.set(key, img, cost: cost(img)) }
            lock.lock()
            pending.remove(key)
            lock.unlock()
        }
        return nil
    }

    /// Renders queued by `cachedOrPrefetch` and not finished yet.
    static var pendingCount: Int { lock.lock(); defer { lock.unlock() }; return pending.count }

    nonisolated(unsafe) private static var pending: Set<Key> = []
    private static let queue = DispatchQueue(label: "com.manycode.arrowout.gametext", qos: .userInitiated)

    /// A style's colours as CGColors (resolved once, before any drawing).
    private struct Colors {
        let drop: CGColor?
        let outline: CGColor?
        let band: CGColor?
        let fill: [CGColor]
        init(_ style: GameTextStyle) {
            drop = style.drop > 0 ? (style.dropColor ?? style.outline ?? style.fill.last).map(GameTextRaster.cg) : nil
            outline = (style.outline != nil && style.outlineWidth > 0) ? style.outline.map(GameTextRaster.cg) : nil
            band = (style.band != nil && style.bandDY > 0) ? style.band.map(GameTextRaster.cg) : nil
            fill = style.fill.map(GameTextRaster.cg)
        }
    }

    private static func cg(_ c: Color) -> CGColor { c.resolve(in: EnvironmentValues()).cgColor }

    static func render(_ l: GameTextLayout, style: GameTextStyle, size: CGSize, origin: CGPoint, scale: CGFloat) -> CGImage? {
        draw(l, style: style, colors: Colors(style), size: size, origin: origin, scale: scale)
    }

    private static func draw(_ l: GameTextLayout, style: GameTextStyle, colors: Colors, size: CGSize, origin: CGPoint,
                             scale: CGFloat, pass: Pass = .all, faceSpan: ClosedRange<CGFloat>? = nil) -> CGImage? {
        let W = max(1, Int((size.width * scale).rounded(.up))), H = max(1, Int((size.height * scale).rounded(.up)))
        guard let space = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: 0, space: space,
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
        ctx.setShouldAntialias(true)
        ctx.interpolationQuality = .high
        // y down, pt units, origin at the advance start on the baseline
        ctx.translateBy(x: 0, y: CGFloat(H))
        ctx.scaleBy(x: scale, y: -scale)
        ctx.translateBy(x: origin.x, y: origin.y)
        let path = l.path
        let w = style.outlineWidth
        func strokeFill(_ color: CGColor, dy: CGFloat, stroke: Bool) {
            ctx.saveGState()
            ctx.translateBy(x: 0, y: dy)
            if stroke && w > 0 {
                ctx.addPath(path)
                ctx.setLineWidth(2 * w); ctx.setLineJoin(.round); ctx.setLineCap(.round)
                ctx.setStrokeColor(color)
                ctx.strokePath()
            }
            ctx.addPath(path)
            ctx.setFillColor(color)
            ctx.fillPath()
            ctx.restoreGState()
        }
        if pass == .all || pass == .drop, let dc = colors.drop { strokeFill(dc, dy: style.drop, stroke: true) }
        if pass == .all || pass == .outline, let oc = colors.outline { strokeFill(oc, dy: 0, stroke: true) }
        if pass == .all || pass == .band, let band = colors.band { strokeFill(band, dy: style.bandDY, stroke: false) }
        guard pass == .all || pass == .face else { return ctx.makeImage() }
        // B3: an EMPTY path (a one-word lettering's empty second word) must not clip to nothing and paint the gradient over
        // the whole bitmap (the white bar after German "Siegesserie" / "Wochenpokal")
        if path.isEmpty {
            // nothing to fill
        } else if colors.fill.count > 1, let g = CGGradient(colorsSpace: space, colors: colors.fill as CFArray, locations: nil) {
            // FIX-2 B: a glyph of a run spans the gradient over the WHOLE run's ink (`faceSpan`), as the run's own raster would
            let b = faceSpan.map { CGRect(x: 0, y: $0.lowerBound, width: 1, height: $0.upperBound - $0.lowerBound) } ?? l.inkBounds
            ctx.saveGState()
            ctx.addPath(path)
            ctx.clip()
            ctx.drawLinearGradient(g, start: CGPoint(x: 0, y: b.minY), end: CGPoint(x: 0, y: b.maxY), options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
            ctx.restoreGState()
        } else {
            strokeFill(colors.fill.first ?? cg(.white), dy: 0, stroke: false)
        }
        return ctx.makeImage()
    }
}

// MARK: - B3 L10N-APP: the bold fallback cascade and the CJK line units

/// B3 (PLAN-P §4.4; SPEC.md ruling 38 "a bold fallback font chain"; design/publish/social-intl.md P2): PC Display (Nunito wght
/// 1000) draws Latin (Vietnamese included) and Cyrillic. Every other script comes from a cascade of the HEAVIEST faces the
/// system has, so a fallback glyph is as black as its PC Display neighbours (GameText and SocType turn each run's glyphs into
/// paths, so the outline, drop and band follow the fallback glyphs):
///   the system's own Black fallback cascade (CTFontCopyDefaultCascadeListForLanguages on the Black system font, public API),
///   in the face's language order — measured on iOS 26 (build/p/B3, cascade probe): Japanese Hiragino Sans W8, Chinese
///   PingFang SC HEAVY (the public PingFang names stop at Semibold), Korean Apple SD Gothic Neo Bold (iOS has no Heavy),
///   Greek / Georgian / Armenian / Hebrew / Arabic in SF Black, Thai Thonburi Bold — heavier than or equal to the named
///   public faces everywhere;
///   then the named public faces (Hiragino Sans W8, PingFang SC Semibold, Apple SD Gothic Neo Bold, Helvetica Neue Bold,
///   Geeza Pro Bold, Arial Hebrew Bold, Thonburi Bold, Noto Sans Armenian Bold) — the whole chain where the system cascade
///   is unavailable (a macOS tool compiling this file).
/// Han ideographs are shared by Japanese and Chinese, so the cascade LANGUAGE is picked per string (`face(for:)`): kana →
/// Japanese; Hangul → Korean; Han only → Japanese in a Japanese UI when Hiragino has every ideograph (a Japanese word or
/// name), else Chinese (a Chinese name: Hiragino lacks about one in four of the name bank's simplified ideographs, and one
/// name must not mix two faces). A named face the system lacks is left out (it would match a substitute face).
enum FontCascade {
    enum Face: Int, CaseIterable { case ja, zh, ko }

    static let greek = "HelveticaNeue-Bold"
    static let cjk: [Face: String] = [.ja: "HiraginoSans-W8", .zh: "PingFangSC-Semibold", .ko: "AppleSDGothicNeo-Bold"]
    static let tail = ["GeezaPro-Bold", "ArialHebrew-Bold", "Thonburi-Bold", "NotoSansArmenian-Bold"]

    /// The language the app runs in (the catalogue's resolved localization: "ja", "zh-Hans", "pt-BR" …).
    static let appLanguage: String =
        Bundle.main.preferredLocalizations.first ?? Locale.current.language.languageCode?.identifier ?? "en"

    /// The CJK order of a string with no kana, Hangul or Han (Latin, digits, punctuation): the app's own.
    static let appFace: Face = face(ofLanguage: appLanguage)

    /// The named public faces of a face's chain, in order, restricted to the faces this system has.
    static func names(_ face: Face) -> [String] { resolved[face] ?? [] }

    private static let resolved: [Face: [String]] = {
        var out: [Face: [String]] = [:]
        for f in Face.allCases {
            let order: [Face] = f == .ja ? [.ja, .zh, .ko] : f == .zh ? [.zh, .ja, .ko] : [.ko, .ja, .zh]
            out[f] = ([greek] + order.compactMap { cjk[$0] } + tail).filter(available)
        }
        return out
    }()

    /// The CoreText language of a face's cascade.
    static func language(of face: Face) -> String { face == .ja ? "ja" : face == .ko ? "ko" : "zh-Hans" }

    /// The whole cascade of a face: the system's Black fallback cascade for the face's language, then the named faces.
    static func cascade(_ face: Face) -> [CTFontDescriptor] {
        var list: [CTFontDescriptor] = []
        #if canImport(UIKit)
        let black = UIFont.systemFont(ofSize: 20, weight: .black) as CTFont
        list = (CTFontCopyDefaultCascadeListForLanguages(black, [language(of: face)] as CFArray) as? [CTFontDescriptor]) ?? []
        #endif
        return list + names(face).map { CTFontDescriptorCreateWithNameAndSize($0 as CFString, 0) }
    }

    /// True when the system has a face with exactly this PostScript name.
    static func available(_ name: String) -> Bool {
        let d = CTFontDescriptorCreateWithNameAndSize(name as CFString, 0)
        guard let m = CTFontDescriptorCreateMatchingFontDescriptor(d, nil) else { return false }
        return (CTFontDescriptorCopyAttribute(m, kCTFontNameAttribute) as? String) == name
    }

    private static let lock = NSLock()
    nonisolated(unsafe) private static var descriptors: [String: CTFontDescriptor] = [:]

    /// `postScriptName` (PC Display) at `size` with the cascade of `face`.
    static func font(_ postScriptName: String, _ size: CGFloat, face: Face) -> CTFont {
        let key = "\(face.rawValue)|\(postScriptName)"
        lock.lock()
        if let d = descriptors[key] { lock.unlock(); return CTFontCreateWithFontDescriptor(d, size, nil) }
        lock.unlock()
        let attrs: [CFString: Any] = [kCTFontNameAttribute: postScriptName, kCTFontCascadeListAttribute: cascade(face)]
        let d = CTFontDescriptorCreateWithAttributes(attrs as CFDictionary)
        lock.lock(); descriptors[key] = d; lock.unlock()
        return CTFontCreateWithFontDescriptor(d, size, nil)
    }

    /// The scripts that decide a string's CJK order.
    struct Scripts: Equatable { var kana = false, hangul = false, han = false; var cjk: Bool { kana || hangul || han } }

    static func scripts(_ s: String) -> Scripts {
        var r = Scripts()
        for u in s.unicodeScalars {
            switch u.value {
            case 0x3041...0x30FF, 0x31F0...0x31FF, 0xFF66...0xFF9F: r.kana = true
            case 0xAC00...0xD7AF, 0x1100...0x11FF, 0x3130...0x318F: r.hangul = true
            case 0x4E00...0x9FFF, 0x3400...0x4DBF, 0xF900...0xFAFF, 0x20000...0x2FFFF: r.han = true
            default: break
            }
        }
        return r
    }

    /// The CJK order for `text` (see the type's note) in an app running in `language` (default: this app's).
    static func face(for text: String, language: String? = nil) -> Face {
        let app = language.map(face(ofLanguage:)) ?? appFace
        let s = scripts(text)
        if s.kana { return .ja }
        if s.hangul { return .ko }
        if s.han { return app == .ja && hiraginoHas(text) ? .ja : .zh }
        return app
    }

    static func face(ofLanguage l: String) -> Face { l.hasPrefix("ja") ? .ja : l.hasPrefix("ko") ? .ko : .zh }

    /// The CoreText language of a laid-out string: the CJK face's language when the string has CJK (locale glyph forms),
    /// else Turkish in a Turkish UI (the TRK i/İ forms, as before B3).
    static func language(for text: String, face: Face) -> String? {
        if scripts(text).cjk { return language(of: face) }
        return appLanguage.hasPrefix("tr") ? "tr" : nil
    }

    private static let hiragino = CTFontCreateWithName((cjk[.ja] ?? "HiraginoSans-W8") as CFString, 12, nil)

    /// True when Hiragino has a glyph for every Han ideograph of `text`.
    static func hiraginoHas(_ text: String) -> Bool {
        for u in text.unicodeScalars where scripts(String(u)).han {
            var utf16 = Array(String(u).utf16)
            var glyphs = [CGGlyph](repeating: 0, count: utf16.count)
            if !CTFontGetGlyphsForCharacters(hiragino, &utf16, &glyphs, utf16.count) { return false }
        }
        return true
    }
}

/// One unit a line may break after; `space`: a U+0020 follows it in the source text.
struct TextUnit: Hashable {
    var text: String
    var space: Bool
    /// FIX-2 B (B3-o4): the source had an explicit U+200B break after this unit (`join` puts it back: the round trip holds).
    var zeroWidthBreak = false
}

/// B3 (CJK line breaking; T2's open issue "word-split layouts split on U+0020 only"): the units a line may break between.
/// Space-separated text gives its words — exactly the old `split(separator: " ")`, so the EN/TR layouts do not move, and
/// Korean breaks at its spaces like the Latin languages. A chunk with kana or Han is cut into CoreFoundation's word tokens
/// (Japanese or Chinese dictionary), then glued back by the kinsoku rules: no line starts with a closing mark, a small kana
/// or the long-vowel mark, no line ends with an opening bracket, digits and Latin letters stay together, and in Japanese a
/// run of hiragana (a particle, okurigana) stays with the word before it (bunsetsu-like breaks: "レベルに / 失敗すると").
/// `keep` substrings (a highlight run) and `**…**` runs never break inside a CJK chunk.
enum LineUnits {
    static let noStart: Set<Character> = Set("、。，．・：；？！゛゜ヽヾゝゞ々〻ー’”）〕］｝〉》」』】〙〗〟｠»‐゠–〜～…‥ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ!),.:;?]}%")
    static let noEnd: Set<Character> = Set("（〔［｛〈《「『【〘〖〝｟«‘“([{")

    private static let lock = NSLock()
    nonisolated(unsafe) private static var cache: [String: [TextUnit]] = [:]

    /// `language`: the app language whose dictionary cuts a Han-only chunk (default: this app's; tests pass the one they
    /// measure). A chunk with kana is always cut as Japanese.
    static func units(_ s: String, keep: [String] = [], language: String? = nil) -> [TextUnit] {
        let jaApp = FontCascade.face(ofLanguage: language ?? FontCascade.appLanguage) == .ja
        let key = (jaApp ? "j" : "z") + keep.joined(separator: "\u{1}") + "\u{2}" + s
        lock.lock()
        if let hit = cache[key] { lock.unlock(); return hit }
        lock.unlock()
        let chunks = s.split(separator: " ").map(String.init)
        var out: [TextUnit] = []
        for (i, chunk) in chunks.enumerated() {
            let last = i == chunks.count - 1
            // FIX-2 B (B3-o4): U+200B (zero width space) is an EXPLICIT unit break the table can place where the tokenizer
            // would not split (zh-Hans "Hot Streak" = 火热 + U+200B + 连胜: two colours in the lettering, like "Hot" + "Streak");
            // it never reaches the drawn text (the units carry the parts, `join` puts no space between them)
            var pieces: [String] = [], marked = Set<Int>()
            for part in chunk.split(separator: "\u{200B}", omittingEmptySubsequences: true).map(String.init) {
                if !pieces.isEmpty { marked.insert(pieces.count - 1) }
                let sc = FontCascade.scripts(part)
                pieces += (sc.kana || sc.han) ? segment(part, keep: keep, japanese: sc.kana || jaApp) : [part]
            }
            if pieces.isEmpty { pieces = [chunk]; marked = [] }
            for (j, p) in pieces.enumerated() {
                out.append(TextUnit(text: p, space: j == pieces.count - 1 && !last, zeroWidthBreak: marked.contains(j)))
            }
        }
        lock.lock()
        if cache.count > 2000 { cache.removeAll() }
        cache[key] = out
        lock.unlock()
        return out
    }

    /// The units back as text (a space where the source had one; none after the last unit).
    static func join<C: Collection>(_ units: C) -> String where C.Element == TextUnit {
        var s = ""
        let n = units.count
        for (i, u) in units.enumerated() { s += u.text + (u.space && i < n - 1 ? " " : "") + (u.zeroWidthBreak && i < n - 1 ? "\u{200B}" : "") }
        return s
    }

    /// The text without its `**` run markers (what is measured and read aloud).
    static func plain(_ s: String) -> String { s.replacingOccurrences(of: "**", with: "") }

    /// Break positions inside one space-free CJK chunk → its pieces.
    static func segment(_ chunk: String, keep: [String], japanese: Bool) -> [String] {
        let ns = chunk as NSString
        let n = ns.length
        guard n > 1 else { return [chunk] }
        var cuts = Set<Int>()
        let locale = Locale(identifier: japanese ? "ja" : "zh-Hans") as CFLocale
        let tok = CFStringTokenizerCreate(nil, chunk as CFString, CFRange(location: 0, length: n), kCFStringTokenizerUnitWordBoundary, locale)
        var starts: [Int: Int] = [:]                    // token start → token end
        while CFStringTokenizerAdvanceToNextToken(tok) != [] {
            let r = CFStringTokenizerGetCurrentTokenRange(tok)
            cuts.insert(r.location); cuts.insert(r.location + r.length)
            starts[r.location] = r.location + r.length
        }
        // a character the tokenizer skipped (punctuation) is its own piece: cut on both sides of it
        var covered = [Bool](repeating: false, count: n)
        for (a, b) in starts { for k in a..<min(b, n) { covered[k] = true } }
        for k in 0..<n where !covered[k] { cuts.insert(k); cuts.insert(k + 1) }
        // protected ranges: `**…**` runs and the keep substrings
        var protected: [NSRange] = []
        var from = 0
        while true {
            let a = ns.range(of: "**", options: [], range: NSRange(location: from, length: n - from))
            if a.location == NSNotFound { break }
            let bFrom = a.location + 2
            let b = bFrom < n ? ns.range(of: "**", options: [], range: NSRange(location: bFrom, length: n - bFrom)) : NSRange(location: NSNotFound, length: 0)
            if b.location == NSNotFound { break }
            protected.append(NSRange(location: a.location, length: b.location + 2 - a.location))
            from = b.location + 2
        }
        for k in keep where !k.isEmpty {
            var f = 0
            while f < n {
                let r = ns.range(of: k, options: [.caseInsensitive], range: NSRange(location: f, length: n - f))
                if r.location == NSNotFound { break }
                protected.append(r)
                f = r.location + max(r.length, 1)
            }
        }
        func char(_ i: Int) -> Character? {
            guard i >= 0, i < n else { return nil }
            let r = ns.rangeOfComposedCharacterSequence(at: i)
            return Character(ns.substring(with: r))
        }
        func isHiragana(_ i: Int, _ j: Int) -> Bool {
            guard i < j else { return false }
            for k in i..<j { let c = ns.character(at: k); if !(0x3041...0x309F).contains(Int(c)) { return false } }
            return true
        }
        // an ASCII run ("x1", "1-4", "+30", "100%", a placeholder) never breaks
        func asciiGraph(_ c: Character?) -> Bool { c.map { $0.isASCII && $0 != " " && ($0.asciiValue ?? 0) > 0x20 && $0 != "*" } ?? false }
        func isHanOrKatakana(_ c: Character?) -> Bool {
            guard let u = c?.unicodeScalars.first?.value else { return false }
            return (0x4E00...0x9FFF).contains(u) || (0x3400...0x4DBF).contains(u) || (0x30A0...0x30FF).contains(u)
        }
        let sorted = cuts.filter { $0 > 0 && $0 < n }.sorted()
        var keepCuts: [Int] = []
        for p in sorted {
            // never inside a surrogate pair / composed sequence
            if ns.rangeOfComposedCharacterSequence(at: p).location != p { continue }
            let next = char(p), prev = char(p - 1)
            if let c = next, noStart.contains(c) { continue }
            if let c = prev, noEnd.contains(c) { continue }
            if asciiGraph(prev) && asciiGraph(next) { continue }
            if !japanese, let c = next, zhNoStart.contains(c) { continue }
            if prev == "*" || next == "*" {
                // a `**` marker belongs to the piece it opens / closes: only its outer edge may break
                if protected.contains(where: { p == $0.location || p == $0.location + $0.length }) == false { continue }
            }
            if protected.contains(where: { p > $0.location && p < $0.location + $0.length }) { continue }
            if japanese, let end = starts[p], isHiragana(p, end) {
                // a particle / okurigana stays with the word before it — but not after a sentence end, and the honorific
                // prefixes お / ご stay with the word they open (ご記入, お宝)
                let token = ns.substring(with: NSRange(location: p, length: end - p))
                let sentenceEnd = prev.map { "。！？!?".contains($0) } ?? false
                let prefix = (token == "お" || token == "ご") && isHanOrKatakana(char(end))
                if !sentenceEnd && !prefix { continue }
            }
            keepCuts.append(p)
        }
        var pieces: [String] = []
        var a = 0
        for p in keepCuts + [n] where p > a {
            pieces.append(ns.substring(with: NSRange(location: a, length: p - a)))
            a = p
        }
        return mergeSingles(pieces)
    }

    /// Chinese particles that never open a line (they close the phrase before them).
    static let zhNoStart: Set<Character> = Set("的了吗呢吧着过们")
    /// Japanese one-character prefixes that stay with the word after them (お宝, 超ハード, 本ゲーム, 一発).
    static let jaPrefixes: Set<String> = ["お", "ご", "超", "本", "各", "全", "新", "再", "一", "第", "毎", "約", "非", "未", "無", "不", "最", "総", "両"]

    /// Japanese and Chinese: a lone one-character piece is not a unit of its own — a prefix joins the next piece, anything
    /// else (名, 中, 数, 的: a suffix) the previous one, the first piece the next (寻 + 宝 → 寻宝, the event title's first word).
    static func mergeSingles(_ pieces: [String]) -> [String] {
        var out: [String] = []
        var carry = ""
        for (i, p) in pieces.enumerated() {
            let piece = carry + p
            carry = ""
            let single = piece.count == 1 && FontCascade.scripts(piece).cjk
            if single && i < pieces.count - 1 && (jaPrefixes.contains(piece) || out.isEmpty) {
                carry = piece
            } else if single && !out.isEmpty && !jaPrefixes.contains(piece) {
                out[out.count - 1] += piece
            } else {
                out.append(piece)
            }
        }
        if !carry.isEmpty { if out.isEmpty { out.append(carry) } else { out[out.count - 1] += carry } }
        return out
    }
}

/// B3 fit sweep (measurement only, `-pc.fitLog 1`; off otherwise — one Bool test per layout miss): every text a layout had
/// to shrink below the 0.70 floor of SPEC.md §5.14 (`need` = box / natural width) or could not fit at all is logged once as
/// `[PC][fit] <id> need <k> floor <f> lang <l> | <text>` and kept in Documents/fit-ledger.json, which the 13-language sweep
/// (build/p/B3) reads after each screen.
enum FitLedger {
    static let enabled = ProcessInfo.processInfo.arguments.contains("-pc.fitLog")
    private static let lock = NSLock()
    nonisolated(unsafe) private static var seen: [String: [String: Any]] = [:]

    static func note(_ id: String, text: String, need: CGFloat, floor: CGFloat = 0.70, box: CGFloat? = nil) {
        guard enabled, need < 0.70 else { return }
        let key = id + "|" + text
        lock.lock()
        if seen[key] != nil { lock.unlock(); return }
        var entry: [String: Any] = ["id": id, "text": text, "need": Double((need * 1000).rounded() / 1000), "floor": Double(floor),
                                    "lang": FontCascade.appLanguage]
        if let box { entry["box"] = Double((box * 10).rounded() / 10) }
        seen[key] = entry
        let all = Array(seen.values)
        lock.unlock()
        Log.mark("fit", "\(id) need \(String(format: "%.3f", need)) floor \(String(format: "%.2f", floor)) lang \(FontCascade.appLanguage) | \(text)")
        if let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first,
           let data = try? JSONSerialization.data(withJSONObject: all, options: [.sortedKeys]) {
            try? data.write(to: docs.appendingPathComponent("fit-ledger.json"), options: .atomic)
        }
    }
}

/// FIX-2 A (V3-09 / V3-10): a thread-safe least-recently-used cache bounded by a total cost (bytes, or 1 per entry for a count
/// bound). Past the limit the least recently used entries go until the total is at `trimTo` × limit (amortised: one sort per
/// trim, not per insert). Pinned keys are never evicted (art on screen).
final class BoundedCache<Key: Hashable, Value>: @unchecked Sendable {        // every mutable member behind `lock`
    private let lock = NSLock()
    private var map: [Key: (value: Value, cost: Int, stamp: UInt64)] = [:]
    private var clock: UInt64 = 0
    private var cost = 0
    private var pins: [Key: Int] = [:]
    private(set) var evictions = 0
    let limit: Int
    let trimTo: Double

    init(limit: Int, trimTo: Double = 0.75) {
        self.limit = max(1, limit)
        self.trimTo = min(1, max(0, trimTo))
    }

    var count: Int { lock.lock(); defer { lock.unlock() }; return map.count }
    var totalCost: Int { lock.lock(); defer { lock.unlock() }; return cost }

    func get(_ key: Key) -> Value? {
        lock.lock(); defer { lock.unlock() }
        guard var e = map[key] else { return nil }
        clock &+= 1
        e.stamp = clock
        map[key] = e
        return e.value
    }

    /// Stores `value`; evicts the least recently used unpinned entries when the total passes the limit.
    func set(_ key: Key, _ value: Value, cost c: Int) {
        lock.lock(); defer { lock.unlock() }
        clock &+= 1
        if let old = map[key] { cost -= old.cost }
        map[key] = (value, max(0, c), clock)
        cost += max(0, c)
        if cost > limit { trim(to: Int(Double(limit) * trimTo)) }
    }

    func contains(_ key: Key) -> Bool { lock.lock(); defer { lock.unlock() }; return map[key] != nil }

    func remove(_ key: Key) {
        lock.lock(); defer { lock.unlock() }
        if let old = map.removeValue(forKey: key) { cost -= old.cost }
    }

    /// Drops every entry whose key matches (pinned ones too: the caller knows nothing shows them).
    func removeAll(where match: (Key) -> Bool) {
        lock.lock(); defer { lock.unlock() }
        for k in map.keys where match(k) {
            if let old = map.removeValue(forKey: k) { cost -= old.cost }
        }
    }

    func removeAll() {
        lock.lock(); defer { lock.unlock() }
        map.removeAll()
        cost = 0
    }

    /// Pins a key (counted: every pin needs its unpin); a pinned entry is never evicted by the limit.
    func pin(_ key: Key) { lock.lock(); pins[key, default: 0] += 1; lock.unlock() }
    func unpin(_ key: Key) {
        lock.lock(); defer { lock.unlock() }
        if let n = pins[key] { pins[key] = n > 1 ? n - 1 : nil }
    }

    private func trim(to target: Int) {
        let order = map.sorted { $0.value.stamp < $1.value.stamp }
        for (k, e) in order {
            if cost <= target { break }
            if pins[k] != nil { continue }
            map.removeValue(forKey: k)
            cost -= e.cost
            evictions += 1
        }
    }
}

// MARK: - FIX-2 lane B (L28): a label composed from cached per-glyph rasters

/// A countdown's "mm:ss" (the last hour of an event, v582 PH-0a: "09:34") changes every second. As one GameText each second
/// is a NEW raster drawn on the main thread (V3: the HUD timer's 3-11 ms per tick) that also pushes older labels out of the
/// shared raster cache. `GlyphRunText` draws such a run (digits and ':' only — `composable`) from ONE raster per character
/// and pass, made once per style (11 characters × the style's passes), composited pass by pass in the whole raster's
/// painter's order — every glyph's drop, then every outline, every band, every face — so a neighbour's outline never covers
/// a face (PC Display's digits sit closer than the 1 pt outline: "14" overlaps by 0.1 pt). Geometry = GameText of the whole
/// string: the run is centred on its advance middle and the cap middle (so `.at(x, capCentre)` places it the same way), each
/// glyph at its advance (+ the tracking between glyphs: CoreText with an explicit kern adds no pair kerning), and the
/// whole run's fit (`maxWidth` → the same shrink rule as GameTextLayout.make). Anything else draws as a plain GameText.
struct GlyphRunText: View {
    let text: String
    let style: GameTextStyle
    var maxWidth: CGFloat?
    @Environment(\.displayScale) private var displayScale
    /// FIX-2 B review: inside a warm-up (a page drawn hidden, `ScreenWarm`) a missing glyph raster is made OFF the main
    /// thread, like GameText's (the warm-up waits for `GameTextRaster.pendingCount`); on screen it is made at once.
    @Environment(\.gameTextDeferred) private var deferred

    static func composable(_ s: String) -> Bool { !s.isEmpty && s.unicodeScalars.allSatisfy { ("0"..."9").contains($0) || $0 == ":" } }

    struct Glyph { let layout: GameTextLayout; let dx: CGFloat }

    /// The style after the run's fit, and each glyph's layout with its advance-middle offset from the run's advance middle.
    static func run(_ text: String, style: GameTextStyle, maxWidth: CGFloat?) -> (style: GameTextStyle, glyphs: [Glyph]) {
        func layouts(_ st: GameTextStyle) -> [GameTextLayout] {
            text.map { GameTextLayout.make(String($0), postScriptName: st.postScriptName, size: st.size, tracking: st.tracking) }
        }
        var st = style
        var ls = layouts(st)
        let total0 = ls.reduce(0) { $0 + $1.advance } + st.tracking * CGFloat(max(0, ls.count - 1))
        if let w = maxWidth, w > 0, total0 > w {                        // GameTextLayout.make's shrink rule, on the whole run
            let k = max(style.minScale, (w / total0 * 1000).rounded(.down) / 1000)
            st = style.sized(style.size * k)
            ls = layouts(st)
        }
        let total = ls.reduce(0) { $0 + $1.advance } + st.tracking * CGFloat(max(0, ls.count - 1))
        var x: CGFloat = 0
        var out: [Glyph] = []
        for l in ls {
            out.append(Glyph(layout: l, dx: x + l.advance / 2 - total / 2))
            x += l.advance + st.tracking
        }
        return (st, out)
    }

    var body: some View {
        if Self.composable(text) {
            let scale = max(displayScale, 1)
            let (st, glyphs) = Self.run(text, style: style, maxWidth: maxWidth)
            let top = glyphs.map(\.layout.inkBounds.minY).min() ?? 0
            let span = top...max(top, glyphs.map(\.layout.inkBounds.maxY).max() ?? 0)     // the run's ink, top to bottom
            let passes = GameTextRaster.Pass.allCases.filter { $0 != .all && GameTextRaster.draws($0, st) }
            ZStack {
                ForEach(passes, id: \.self) { pass in
                    ForEach(Array(glyphs.enumerated()), id: \.offset) { _, g in
                        let (size, origin) = GameText.rasterGeometry(g.layout, style: st, capStyle: style)
                        let face = pass == .face ? span : nil
                        if let img = deferred
                            ? GameTextRaster.cachedOrPrefetch(g.layout, style: st, size: size, origin: origin, scale: scale, pass: pass, faceSpan: face)
                            : GameTextRaster.image(g.layout, style: st, size: size, origin: origin, scale: scale, pass: pass, faceSpan: face) {
                            Image(decorative: img, scale: scale).resizable().interpolation(.high)
                                .frame(width: size.width, height: size.height)
                                .offset(x: (g.dx * scale).rounded() / scale)
                        }
                    }
                }
            }
            .allowsHitTesting(false)
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(Text(verbatim: text))
            .accessibilityAddTraits(.isStaticText)
        } else {
            GameText(verbatim: text, style: style, maxWidth: maxWidth)
        }
    }
}
