import UIKit
import CoreText

// B1 (SPEC-architecture §5.6 "Digits", D16). Counter digits as CoreText glyph paths of PCDisplay-Black (crisp at every
// zoom in a CAShapeLayer; no CATextLayer, §5.11 rule 11). Cached per string at a 100 pt reference size, scaled by the
// caller; "0"…"99" are built during the warm-up so B2's counters never lay out text on the tap path.

@MainActor final class DigitGlyphs {
    static let shared = DigitGlyphs()
    static let referenceSize: CGFloat = 100
    private var cache: [String: CGPath] = [:]
    private var font: CTFont?

    var cachedCount: Int { cache.count }

    /// The glyph outline of `text` at the reference size: origin at the text's visual centre, y DOWN (layer space).
    func path(_ text: String) -> CGPath {
        if let p = cache[text] { return p }
        let p = build(text)
        cache[text] = p
        return p
    }

    /// Builds "0"…"99" (warm-up).
    func warm() {
        for i in 0...99 { _ = path(String(i)) }
    }

    private func build(_ text: String) -> CGPath {
        if font == nil {
            font = CTFontCreateWithName("PCDisplay-Black" as CFString, Self.referenceSize, nil)
        }
        guard let font else { return CGMutablePath() }
        let attr = NSAttributedString(string: text, attributes: [NSAttributedString.Key(kCTFontAttributeName as String): font])
        let line = CTLineCreateWithAttributedString(attr)
        let out = CGMutablePath()
        let runs = (CTLineGetGlyphRuns(line) as? [CTRun]) ?? []
        for run in runs {
            let n = CTRunGetGlyphCount(run)
            var glyphs = [CGGlyph](repeating: 0, count: n)
            var positions = [CGPoint](repeating: .zero, count: n)
            CTRunGetGlyphs(run, CFRange(location: 0, length: n), &glyphs)
            CTRunGetPositions(run, CFRange(location: 0, length: n), &positions)
            for i in 0..<n {
                guard let g = CTFontCreatePathForGlyph(font, glyphs[i], nil) else { continue }
                // glyph space is y up: flip, then place at the run position
                let t = CGAffineTransform(a: 1, b: 0, c: 0, d: -1, tx: positions[i].x, ty: -positions[i].y)
                out.addPath(g, transform: t)
            }
        }
        let box = out.boundingBoxOfPath
        var centre = CGAffineTransform(translationX: -box.midX, y: -box.midY)
        return out.copy(using: &centre) ?? out
    }
}
