import SwiftUI

// SHELL S1 (SPEC-architecture §10.2 "frames in the shell: 0 frames > 20 ms after warm-up"; D13). SwiftUI draws every gradient-
// filled non-rectangular shape (panel frames, ribbons, glossy button faces, wells, cards) and every Canvas on the CPU into a new
// backing store each time a view is created — a popup opening paid 40-60 ms of `CGContextDrawLinearGradient` on the main thread
// (S1 profile, build/s1/c2/popup-loop-sample-debug*.txt). Static chrome therefore renders ONCE per (key, size, scale) with
// ImageRenderer into a CGImage and is shown as an Image afterwards: a presentation only composites. The popup pre-render behind
// Loading (RootView `PopupPrewarm`) fills the cache for the S1 popups. Content must not depend on the parent's environment
// (pass tokens and sizes in); the key must name everything that changes the pixels.

@MainActor enum RasterCache {
    private static var cache: [String: CGImage] = [:]
    private static var order: [String] = []
    /// Cap on cached images (each popup's chrome is a handful; pages add a full-screen background per size). FIX-A1: 160 → 256
    /// — the Loading warm-up now renders every owner's popups and pages (170 before the first screen, build/fixa1) and the
    /// oldest entries were evicted before first use (the win ribbon re-rendered on the first win: an 82 ms frame).
    static var limit = 256

    static var count: Int { cache.count }
    /// Renders so far (a render after the first screen is a warm-up gap: logged when `logMisses`).
    static var misses = 0
    static var logMisses = false

    static func image<Content: View>(_ key: String, size: CGSize, scale: CGFloat, @ViewBuilder content: () -> Content) -> CGImage? {
        guard size.width >= 1, size.height >= 1 else { return nil }
        let full = "\(key)|\(Int((size.width * 10).rounded()))x\(Int((size.height * 10).rounded()))@\(scale)"
        if let hit = cache[full] { return hit }
        let r = ImageRenderer(content: content().frame(width: size.width, height: size.height))
        r.scale = scale
        r.isOpaque = false
        guard let img = r.cgImage else { return nil }
        misses += 1
        if logMisses { Log.mark("raster", "render \(full)") }
        if cache.count >= limit, let oldest = order.first { cache[oldest] = nil; order.removeFirst() }
        cache[full] = img
        order.append(full)
        return img
    }
}

/// A static chrome subtree rendered once (per key + size + display scale) and shown as an image. `overflow` (pt on every side)
/// keeps pixels a component draws OUTSIDE its frame on purpose (the X's ring and halo, toggle and pill wells, card shadows):
/// ImageRenderer clips to the rendered bounds, so the raster is made that much larger and centred on the frame.
struct Rasterized<Content: View>: View {
    let key: String
    let overflow: CGFloat
    @ViewBuilder var content: (CGSize) -> Content
    @Environment(\.displayScale) private var displayScale

    init(_ key: String, overflow: CGFloat = 0, @ViewBuilder content: @escaping (CGSize) -> Content) {
        self.key = key
        self.overflow = overflow
        self.content = content
    }

    var body: some View {
        GeometryReader { geo in
            let s = max(displayScale, 1)
            let size = geo.size, o = overflow
            let big = CGSize(width: size.width + 2 * o, height: size.height + 2 * o)
            if let img = RasterCache.image("\(key)|o\(o)", size: big, scale: s, content: {
                content(size).frame(width: size.width, height: size.height).frame(width: big.width, height: big.height)
            }) {
                Image(decorative: img, scale: s).resizable().frame(width: big.width, height: big.height)
                    .position(x: size.width / 2, y: size.height / 2)
            }
        }
        .accessibilityHidden(true)
    }
}

extension PanelButtonStyleColors {
    /// A short identity for raster keys (the palettes differ in their outline and first face colour).
    var rasterID: String { String(format: "%06X-%06X", outline, face.first?.0 ?? 0) }
}
