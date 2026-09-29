import UIKit
import CoreText
import QuartzCore

// SOCIAL SOC2 (SPEC-architecture §6.9, §10.2 "social = 0 ms main thread"; SPEC-ui §1.4 text roles `role.row*`). The text of the
// long social lists (Leaderboard World / Country / Weekly rows, the Streak Race's 50 rows) is shaped OFF the main thread with
// CoreText into glyph outlines (`SocShaped`, immutable, thread-safe caches) and drawn by the render server as CAShapeLayers
// (`SocLabelLayer`: drop → outline → face, the GameText layer model of fonts.md §6 with flat colours). A row entering the
// viewport therefore costs a few layer property writes on the main thread — no CoreText, no bitmap, no SwiftUI graph — which
// is what keeps a 200-row fling inside the 16.7 ms frame (SPEC-architecture §10.2 "shell … 200-row leaderboard scroll").
// Numbers (ranks, levels, scores, prizes) are composed from a per-style digit cache, so the 0.30 s count-ups of the live
// updates (SPEC-motion-audio §9) never touch CoreText either.

/// A flat-colour text style for the CA labels (GameText's roles, SPEC-ui §1.4).
struct SocStyle: Hashable, Sendable {
    var size: CGFloat
    var tracking: CGFloat = 0
    var italic = false
    var face: UInt32
    var outline: UInt32? = nil
    var width: CGFloat = 0
    var drop: CGFloat = 0
    /// Fit box (pt); nil = never shrinks.
    var maxWidth: CGFloat? = nil
    /// Shrink floor (SPEC.md §5.14: 0.7); a name that still does not fit is cut with "…" (SPEC-ui role.rowName).
    var minScale: CGFloat = 0.7

    var postScriptName: String { italic ? "PCDisplay-BlackItalic" : "PCDisplay-Black" }

    func scaled(_ k: CGFloat) -> SocStyle {
        var s = self
        s.size *= k; s.tracking *= k; s.width *= k; s.drop *= k
        if let m = maxWidth { s.maxWidth = m * k }
        return s
    }
}

/// One shaped line: glyph outlines in pt, y DOWN, x = 0 at the advance start, y = 0 on the baseline. Immutable.
final class SocShaped: @unchecked Sendable {
    let text: String
    let path: CGPath
    let advance: CGFloat
    /// The style actually drawn (outline and drop shrink with the text).
    let style: SocStyle
    let capHeight: CGFloat

    init(text: String, path: CGPath, advance: CGFloat, style: SocStyle, capHeight: CGFloat) {
        self.text = text; self.path = path; self.advance = advance; self.style = style; self.capHeight = capHeight
    }

    static let empty = SocShaped(text: "", path: CGMutablePath(), advance: 0, style: SocStyle(size: 1, face: 0), capHeight: 0)
}

/// CoreText shaping with thread-safe caches (any thread; the social worker shapes whole pages ahead of the main thread).
enum SocType {
    private static let lock = NSLock()
    nonisolated(unsafe) private static var cache: [String: SocShaped] = [:]
    nonisolated(unsafe) private static var digitCache: [String: DigitSet] = [:]
    /// Set once on the main thread at install (CoreText then applies the TRK i/İ forms, as GameText does).
    nonisolated(unsafe) static var turkish = false

    private final class DigitSet: @unchecked Sendable {
        let paths: [CGPath]          // "0"…"9", then "#"
        let advances: [CGFloat]
        let capHeight: CGFloat
        init(paths: [CGPath], advances: [CGFloat], capHeight: CGFloat) { self.paths = paths; self.advances = advances; self.capHeight = capHeight }
    }

    static var cachedCount: Int { lock.lock(); defer { lock.unlock() }; return cache.count }

    /// Language-independent text (names, numbers as text) shaped once per (text, style).
    static func shape(_ text: String, _ style: SocStyle) -> SocShaped {
        let key = "\(style.hashValue)|\(text)"
        lock.lock()
        if let hit = cache[key] { lock.unlock(); return hit }
        lock.unlock()
        let out = build(text, style)
        lock.lock()
        if cache.count > 3000 { cache.removeAll(keepingCapacity: true) }
        cache[key] = out
        lock.unlock()
        return out
    }

    private static func build(_ text: String, _ style: SocStyle) -> SocShaped {
        var line = layout(text, style.postScriptName, style.size, style.tracking)
        var st = style
        if let w = style.maxWidth, w > 0, line.advance > w {
            FitLedger.note("soc", text: text, need: w / line.advance, floor: style.minScale)
            let k = max(style.minScale, (w / line.advance * 1000).rounded(.down) / 1000)
            st = style.scaled(k)
            st.maxWidth = style.maxWidth
            line = layout(text, st.postScriptName, st.size, st.tracking)
            if line.advance > w + 0.5 && text.count > 1 {
                // still too wide at the floor: cut with an ellipsis (SPEC-ui role.rowName "then truncate …")
                var chars = Array(text)
                while chars.count > 1 {
                    chars.removeLast()
                    let candidate = String(chars).trimmingCharacters(in: .whitespaces) + "…"
                    let l = layout(candidate, st.postScriptName, st.size, st.tracking)
                    if l.advance <= w || chars.count == 1 { line = l; break }
                }
            }
        }
        let cap = CTFontGetCapHeight(font(st.postScriptName, st.size))
        return SocShaped(text: text, path: line.path, advance: line.advance, style: st, capHeight: cap)
    }

    private static func font(_ name: String, _ size: CGFloat) -> CTFont { CTFontCreateWithName(name as CFString, size, nil) }

    private static func layout(_ text: String, _ name: String, _ size: CGFloat, _ tracking: CGFloat) -> (path: CGPath, advance: CGFloat) {
        // B3: PC Display + the bold fallback cascade (GameText.swift FontCascade): a native-script name (ja/ko/zh, Arabic,
        // Greek, Thai, Hebrew …) is drawn in a heavy face, and its outline and drop follow the fallback glyph paths.
        let face = FontCascade.face(for: text)
        let f = FontCascade.font(name, size, face: face)
        var attrs: [NSAttributedString.Key: Any] = [
            NSAttributedString.Key(kCTFontAttributeName as String): f,
            NSAttributedString.Key(kCTKernAttributeName as String): tracking,
        ]
        if FontCascade.scripts(text).cjk, let lang = FontCascade.language(for: text, face: face) {
            attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = lang
        } else if turkish {
            attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = "tr"
        }
        let line = CTLineCreateWithAttributedString(NSAttributedString(string: text.isEmpty ? " " : text, attributes: attrs))
        let typographic = CGFloat(CTLineGetTypographicBounds(line, nil, nil, nil))
        let advance = max(0, typographic - CGFloat(CTLineGetTrailingWhitespaceWidth(line)) - (text.isEmpty ? 0 : tracking))
        let path = CGMutablePath()
        for run in CTLineGetGlyphRuns(line) as! [CTRun] {
            let attrs = CTRunGetAttributes(run) as NSDictionary
            let rf: CTFont = attrs[kCTFontAttributeName as String].map { $0 as! CTFont } ?? f
            let n = CTRunGetGlyphCount(run)
            var ids = [CGGlyph](repeating: 0, count: n)
            var pos = [CGPoint](repeating: .zero, count: n)
            CTRunGetGlyphs(run, CFRange(location: 0, length: n), &ids)
            CTRunGetPositions(run, CFRange(location: 0, length: n), &pos)
            for k in 0..<n {
                guard let gp = CTFontCreatePathForGlyph(rf, ids[k], nil), !gp.isEmpty else { continue }
                path.addPath(gp, transform: CGAffineTransform(translationX: pos[k].x, y: 0).scaledBy(x: 1, y: -1))
            }
        }
        return (path, advance)
    }

    // MARK: numbers from the digit cache

    private static func digits(_ style: SocStyle) -> DigitSet {
        let key = "\(style.postScriptName)|\(style.size)"
        lock.lock()
        if let hit = digitCache[key] { lock.unlock(); return hit }
        lock.unlock()
        let f = font(style.postScriptName, style.size)
        var paths: [CGPath] = []
        var adv: [CGFloat] = []
        for ch in Array("0123456789#") {
            var u = Array(String(ch).utf16)
            var g = [CGGlyph](repeating: 0, count: u.count)
            CTFontGetGlyphsForCharacters(f, &u, &g, u.count)
            var a = CGSize.zero
            CTFontGetAdvancesForGlyphs(f, .horizontal, &g, &a, 1)
            let p = CTFontCreatePathForGlyph(f, g[0], nil).map { gp -> CGPath in
                var t = CGAffineTransform(scaleX: 1, y: -1)
                return gp.copy(using: &t) ?? gp
            } ?? CGMutablePath()
            paths.append(p); adv.append(a.width)
        }
        let set = DigitSet(paths: paths, advances: adv, capHeight: CTFontGetCapHeight(f))
        lock.lock(); digitCache[key] = set; lock.unlock()
        return set
    }

    /// A non-negative integer composed from cached digit outlines ("#" prefix optional), shrunk to `maxWidth` with no floor
    /// (a number cannot be rewritten; SPEC-ui role.rowValue "5-6 digits shrink in box 70").
    static func number(_ n: Int, _ style: SocStyle, prefix: String = "") -> SocShaped {
        let text = prefix + String(max(0, n))
        let set = digits(style)
        let path = CGMutablePath()
        var x: CGFloat = 0
        for (i, ch) in text.enumerated() {
            let idx: Int
            if ch == "#" { idx = 10 } else if let d = ch.wholeNumberValue { idx = d } else { continue }
            if i > 0 { x += style.tracking }
            path.addPath(set.paths[idx], transform: CGAffineTransform(translationX: x, y: 0))
            x += set.advances[idx]
        }
        var st = style
        var out: CGPath = path
        var adv = x
        if let w = style.maxWidth, w > 0, x > w {
            let k = (w / x * 1000).rounded(.down) / 1000
            var t = CGAffineTransform(scaleX: k, y: k)
            out = path.copy(using: &t) ?? path
            adv = x * k
            st = style.scaled(k)
            st.maxWidth = style.maxWidth
        }
        return SocShaped(text: text, path: out, advance: adv, style: st, capHeight: set.capHeight * (adv / max(x, 0.001)))
    }

    /// Cap height of the black face at `size` (for baseline placement of centred text).
    static func capHeight(_ size: CGFloat, italic: Bool = false) -> CGFloat {
        CTFontGetCapHeight(font(italic ? "PCDisplay-BlackItalic" : "PCDisplay-Black", size))
    }
}

// MARK: - the CA label

extension UIColor {
    convenience init(socHex v: UInt32, _ a: CGFloat = 1) {
        self.init(red: CGFloat((v >> 16) & 0xFF) / 255, green: CGFloat((v >> 8) & 0xFF) / 255, blue: CGFloat(v & 0xFF) / 255, alpha: a)
    }
}

/// Three shape layers (drop, outline, face) for one shaped label. Created once per row slot, re-pointed on reuse.
final class SocLabelLayer {
    let drop = CAShapeLayer()
    let outline = CAShapeLayer()
    let face = CAShapeLayer()
    private(set) var shaped: SocShaped?

    init(in parent: CALayer, scale: CGFloat) {
        for l in [drop, outline, face] {
            l.contentsScale = scale
            l.anchorPoint = .zero
            l.bounds = .zero
            l.lineJoin = .round
            l.lineCap = .round
            l.actions = ["position": NSNull(), "path": NSNull(), "fillColor": NSNull(), "strokeColor": NSNull(),
                         "hidden": NSNull(), "lineWidth": NSNull(), "opacity": NSNull(), "transform": NSNull()]
            parent.addSublayer(l)
        }
    }

    /// Colour override for the player's green row (white face, dark green outline / caption; VERIFIED meta-013 / meta-026).
    var tint: (face: UInt32, outline: UInt32?)?

    /// Places the label with its advance box starting at `origin.x` and its baseline at `origin.y` (parent coordinates).
    func set(_ s: SocShaped?, origin: CGPoint) {
        shaped = s
        guard let s, !s.text.isEmpty else {
            drop.isHidden = true; outline.isHidden = true; face.isHidden = true
            return
        }
        var st = s.style
        if let t = tint { st.face = t.face; if st.outline != nil { st.outline = t.outline ?? st.outline } }
        let hasOutline = st.outline != nil && st.width > 0
        face.path = s.path
        face.fillColor = UIColor(socHex: st.face).cgColor
        face.position = origin
        face.isHidden = false
        if hasOutline, let oc = st.outline {
            let c = UIColor(socHex: oc).cgColor
            outline.path = s.path
            outline.fillColor = c
            outline.strokeColor = c
            outline.lineWidth = 2 * st.width
            outline.position = origin
            outline.isHidden = false
        } else {
            outline.isHidden = true
        }
        if st.drop > 0, let dc = st.outline ?? Optional(st.face) {
            let c = UIColor(socHex: dc).cgColor
            drop.path = s.path
            drop.fillColor = c
            drop.strokeColor = hasOutline ? c : nil
            drop.lineWidth = hasOutline ? 2 * st.width : 0
            drop.position = CGPoint(x: origin.x, y: origin.y + st.drop)
            drop.isHidden = false
        } else {
            drop.isHidden = true
        }
    }

    /// Centred on `centreX` with the baseline at `baseline`.
    func set(_ s: SocShaped?, centreX: CGFloat, baseline: CGFloat) {
        set(s, origin: CGPoint(x: centreX - (s?.advance ?? 0) / 2, y: baseline))
    }

    /// Right-aligned: the advance box ends at `rightX`.
    func set(_ s: SocShaped?, rightX: CGFloat, baseline: CGFloat) {
        set(s, origin: CGPoint(x: rightX - (s?.advance ?? 0), y: baseline))
    }
}
