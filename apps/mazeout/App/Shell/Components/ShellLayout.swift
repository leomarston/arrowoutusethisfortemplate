import SwiftUI

// SHELL S1 (SPEC-architecture §6.12; SPEC.md §5 item 14; design/ui-measure.md "How to read"). Every screen is authored in
// points on the 393 x 852 reference canvas (the owner's iPhone 15: safe top 59, safe bottom 34) and mapped to the live
// screen (adapted from apps/matchfactory ShellLayout.swift, e10a076):
//   - horizontal measures × s, s = W / 393;
//   - top-anchored blocks:    y' = safeTop + (y − 59) × s   (the top bar, the HUD);
//   - bottom-anchored blocks: y' = H − safeBottom − (852 − 34 − y) × s   (Play, the nav bar, the booster corners);
//   - popups and full-screen overlays: a virtual 393 x 852 canvas scaled by min(1, W/393, H/852) and centred — popups scale
//     only BELOW 393 pt (SPEC.md §5 item 14; `layout.popupUpscale` true lets them grow on wider phones).
// On the reference phone every mapping is the identity, so the measured frames are the frames on screen.
// ShellLayout also publishes the level's play rect (HUD bottom … booster top) for `BoardLayout.fit` (§6.12).

struct ShellMetrics: Equatable {
    static let reference = CGSize(width: 393, height: 852)
    static let refSafeTop: CGFloat = 59
    static let refSafeBottom: CGFloat = 34

    var size: CGSize = ShellMetrics.reference
    var safeTop: CGFloat = ShellMetrics.refSafeTop
    var safeBottom: CGFloat = ShellMetrics.refSafeBottom
    var popupUpscale = false

    /// Horizontal scale of anchored blocks.
    var s: CGFloat { size.width / Self.reference.width }
    /// Scale of the virtual popup canvas.
    var popupScale: CGFloat {
        let k = min(size.width / Self.reference.width, size.height / Self.reference.height)
        return popupUpscale ? k : min(1, k)
    }

    enum Anchor: String { case top, bottom, centre }

    func y(_ y: CGFloat, _ anchor: Anchor) -> CGFloat {
        switch anchor {
        case .top: return safeTop + (y - Self.refSafeTop) * s
        case .bottom: return size.height - safeBottom - (Self.reference.height - Self.refSafeBottom - y) * s
        case .centre: return popupPoint(CGPoint(x: 0, y: y)).y
        }
    }

    func rect(_ r: CGRect, _ anchor: Anchor) -> CGRect {
        switch anchor {
        case .centre:
            let k = popupScale
            let o = popupPoint(r.origin)
            return CGRect(x: o.x, y: o.y, width: r.width * k, height: r.height * k)
        default:
            return CGRect(x: r.minX * s, y: y(r.minY, anchor), width: r.width * s, height: r.height * s)
        }
    }

    func point(_ p: CGPoint, _ anchor: Anchor) -> CGPoint {
        anchor == .centre ? popupPoint(p) : CGPoint(x: p.x * s, y: y(p.y, anchor))
    }

    /// Maps a point of the virtual popup canvas to the screen.
    func popupPoint(_ p: CGPoint) -> CGPoint {
        let k = popupScale
        let ox = (size.width - Self.reference.width * k) / 2
        let oy = (size.height - Self.reference.height * k) / 2
        return CGPoint(x: ox + p.x * k, y: oy + p.y * k)
    }

    /// The level's play rect in screen pt: from the HUD's bottom (top-anchored) to the booster trays' top
    /// (bottom-anchored). The reference values are `layout.playRect` in ui.json (§4.2: 122 … 755 pt, VERIFIED fit rule).
    func playRect(top: CGFloat, bottom: CGFloat) -> CGRect {
        let y0 = y(top, .top), y1 = y(bottom, .bottom)
        return CGRect(x: 0, y: y0, width: size.width, height: max(0, y1 - y0))
    }
}

private struct ShellMetricsKey: EnvironmentKey { static let defaultValue = ShellMetrics() }

extension EnvironmentValues {
    var shellMetrics: ShellMetrics {
        get { self[ShellMetricsKey.self] }
        set { self[ShellMetricsKey.self] = newValue }
    }
}

extension CGRect {
    init(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat) { self.init(x: x, y: y, width: w, height: h) }
    var centre: CGPoint { CGPoint(x: midX, y: midY) }
}

extension View {
    /// Frames and positions a view at a rect in its parent's top-leading coordinates (the parent is a full-size ZStack).
    func placed(_ r: CGRect) -> some View {
        frame(width: max(r.width, 0), height: max(r.height, 0)).position(x: r.midX, y: r.midY)
    }

    /// Frames a view at a reference rect mapped with the live metrics and an anchor.
    func placed(_ r: CGRect, _ anchor: ShellMetrics.Anchor, _ m: ShellMetrics) -> some View { placed(m.rect(r, anchor)) }

    /// Positions a view's centre at a point of its parent (reference canvas inside `ReferenceCanvas`).
    func at(_ x: CGFloat, _ y: CGFloat) -> some View { position(x: x, y: y) }
}

/// A virtual 393 x 852 canvas scaled by `ShellMetrics.popupScale` and centred (popups, full-screen overlays, labs).
struct ReferenceCanvas<Content: View>: View {
    @Environment(\.shellMetrics) private var metrics
    @ViewBuilder var content: Content

    var body: some View {
        let k = metrics.popupScale
        ZStack(alignment: .topLeading) { content }
            .frame(width: ShellMetrics.reference.width, height: ShellMetrics.reference.height, alignment: .topLeading)
            .scaleEffect(k, anchor: .center)
            .frame(width: metrics.size.width, height: metrics.size.height)
    }
}

/// A full-screen block whose children are placed with reference rects and anchors on the live screen.
struct AnchoredCanvas<Content: View>: View {
    @Environment(\.shellMetrics) private var metrics
    @ViewBuilder var content: Content

    var body: some View {
        ZStack(alignment: .topLeading) { content }
            .frame(width: metrics.size.width, height: metrics.size.height, alignment: .topLeading)
    }
}
