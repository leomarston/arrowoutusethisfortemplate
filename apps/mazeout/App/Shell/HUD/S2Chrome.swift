import SwiftUI
import PathCore

// SHELL S2 (SPEC-ui §1.4, §1.6, §2.3, §2.6, §2.7). The pieces the S2 screens share, drawn in code at the measured frames:
//   ArtInk            where each raster's VISIBLE pixels sit inside its canvas (alpha bbox, measured on art/ui/out @3x), so a
//                     raster is placed by the frame SPEC-ui measured on the phone, not by its padded canvas
//   InkImage          a raster whose visible pixels fill a measured frame (aspect kept, centred)
//   TokenText         a GameText placed by its ui.json `text.<id>` style + baseline / centre-x (compiled defaults = SPEC-ui)
//   RingedText        GameText with extra outline rings (Out of Time!/Out of Lives! double outline, the unlock title's
//                     layered blue outline): the rings are further GameText layers, outermost first, the drop on the outermost
//   TierSquareButton  the 40 pt HUD square button (back / pause) in the tier colour: GlossyChrome's BlueSquareButton recipe
//                     with a palette (blue = its numbers; red #EC0911, purple #9100E4 faces, SPEC-ui §1.6.1)
//   OfferCoinGroup    the fail offers' top-left coin group (coin + pill + green +), above the dim (SPEC-ui §2.6)
//   PriceButton       a framed wide green button: label + coin + price ("Add Time 900", "Play On 900", "Add Lives 900")
// Names avoid GlossyChrome's reserved symbols (CoinPill, TimerPill, BoosterButton, CountBadge, PanelFrame, StreakChips …).

// MARK: - raster ink boxes

enum ArtInk {
    /// Alpha bbox of the @3x file as fractions of its canvas (x0, y0, x1, y1), alpha > 24/255.
    static let boxes: [UIArt: (Double, Double, Double, Double)] = [
        .heartHUD: (0.0108, 0.0123, 0.9892, 0.9877),
        .heartHUDLost: (0.0215, 0.0000, 0.9785, 1.0000),
        .heartHUDHalves: (0.0215, 0.0494, 1.0000, 0.9877),
        .iconStopwatch: (0.0606, 0.0101, 0.9394, 1.0000),
        .iconCoin: (0.0444, 0.0333, 0.9556, 0.9778),
        .iconPlusGreen: (0.0500, 0.0333, 0.9500, 0.9667),
        .boosterFreeze: (0.1786, 0.1429, 0.8214, 0.8631),
        .boosterHint: (0.2321, 0.1012, 0.7679, 0.8988),
        .stopwatchBig: (0.0415, 0.0133, 0.9526, 0.9881),
        .heartBroken: (0.0146, 0.0480, 0.9854, 0.9520),
        .coinStackReward: (0.0212, 0.1100, 0.9939, 0.8900),
        .tutorialHand: (0.0654, 0.0343, 0.9150, 0.9412),
        .heartLives: (0.0000, 0.0208, 1.0000, 0.9479),
        .treasureToken: (0.0500, 0.1083, 0.9500, 0.9250),       // A4: R8's D1 token (was iconHexArrow), measured by this table's rule
        .iconCheckeredFlag: (0.0778, 0.0729, 0.9778, 1.0000),
        .heartInfinite: (0.0725, 0.0913, 0.9239, 0.8889),
        .coinPileSmall: (0.0245, 0.1607, 0.9755, 0.9405),
        .sparkleTwinkle: (0.0833, 0.0833, 0.9167, 0.9167),
        .unlockIconPipe: (0.0214, 0.0323, 0.9380, 0.9812),
        .unlockIconLinked: (0.0583, 0.1394, 0.9417, 0.8818),
        .unlockIconBox: (0.0354, 0.0448, 0.9646, 0.9851),
        .unlockIconDoor: (0.0722, 0.0485, 0.9361, 0.9848),
        .unlockIconElevator: (0.0083, 0.1424, 0.9917, 0.8727),
        .iconStopwatchSmall: (0.0556, 0.0000, 0.9444, 1.0000),
        .rankBadgeGold: (0.0278, 0.0370, 0.9722, 0.9630),
        .logoArrowOut: (0.0283, 0.0071, 0.9771, 0.9845),
    ]

    /// The canvas rect that puts `art`'s visible pixels onto `ink` (aspect kept: the visible box is fitted and centred).
    static func canvas(_ art: UIArt, ink: CGRect) -> CGRect {
        let b = boxes[art] ?? (0, 0, 1, 1)
        let size = art.sizePt
        let vw = CGFloat(b.2 - b.0) * size.width, vh = CGFloat(b.3 - b.1) * size.height
        guard vw > 0, vh > 0 else { return ink }
        let k = min(ink.width / vw, ink.height / vh)
        let cw = size.width * k, ch = size.height * k
        let vcx = CGFloat(b.0 + b.2) / 2 * cw, vcy = CGFloat(b.1 + b.3) / 2 * ch
        return CGRect(x: ink.midX - vcx, y: ink.midY - vcy, width: cw, height: ch)
    }
}

/// A raster whose visible pixels fill `ink` (reference pt in the parent's top-leading space).
struct InkImage: View {
    let art: UIArt
    let ink: CGRect
    var body: some View { ArtImage(art: art).placed(ArtInk.canvas(art, ink: ink)) }
}

// MARK: - text

/// Hex-list style shorthand for the compiled defaults (SPEC-ui / ui-tokens values).
extension GameTextStyle {
    static func s2(_ size: CGFloat, _ tracking: CGFloat, _ fill: [UInt32], outline: UInt32? = nil, _ width: CGFloat = 0,
                   drop: CGFloat = 0, dropColor: UInt32? = nil, face: Face = .black) -> GameTextStyle {
        GameTextStyle(size: size, tracking: tracking, face: face, fill: fill.map { Color(hex: $0) }, outline: outline.map { Color(hex: $0) },
                      outlineWidth: outline == nil ? 0 : width, drop: drop, dropColor: dropColor.map { Color(hex: $0) })
    }
}

/// What a label shows: language copy (resolved through the strings catalogue) or a number/time (verbatim).
enum TextSource: Equatable {
    case copy(LocalizedStringResource)
    case number(String)

    static func == (a: TextSource, b: TextSource) -> Bool {
        switch (a, b) {
        case (.copy(let x), .copy(let y)): return x.key == y.key && String(localized: x) == String(localized: y)
        case (.number(let x), .number(let y)): return x == y
        default: return false
        }
    }
}

/// A GameText placed by its ui.json `text.<id>` style, baseline and centre-x (reference pt in the parent).
struct TokenText: View {
    let id: String
    let source: TextSource
    let style: GameTextStyle
    let baseline: CGFloat
    let centreX: CGFloat
    var maxWidth: CGFloat? = nil
    /// Extra outline rings (outermost first): colour + TOTAL width from the glyph edge; the drop goes on the outermost ring.
    var rings: [(UInt32, CGFloat)] = []
    /// The rings' offset below the face and the inner outline's 3D extrusion (VERIFIED 013's title: +1.2 / +2.4).
    var ringDY: CGFloat = 0
    var innerDY: CGFloat = 0
    @Environment(AppModel.self) private var app

    var body: some View {
        let t = app.tuning.ui.tokens
        let st = t.text(id, style)
        let p = t.textPoint(id, baseline: baseline, centreX: centreX)
        RingedText(source: source, style: st, rings: t.rings(id, rings), maxWidth: t.textMaxWidth(id, maxWidth),
                   ringDY: ringDY == 0 ? 0 : CGFloat(t.number("text.\(id).ringDY", Double(ringDY))),
                   innerDY: innerDY == 0 ? 0 : CGFloat(t.number("text.\(id).innerDY", Double(innerDY))))
            .at(p.x, st.capCentre(baseline: p.baseline))
            .accessibilityIdentifier(id)
    }
}

/// GameText with outline rings behind it. `style` is the face + its own (innermost) outline; each ring is a GameText layer
/// with the ring colour as its outline at the ring's total width; the drop is drawn only by the outermost layer.
struct RingedText: View {
    let source: TextSource
    let style: GameTextStyle
    var rings: [(Color, CGFloat)] = []
    var maxWidth: CGFloat? = nil
    var ringDY: CGFloat = 0
    var innerDY: CGFloat = 0

    var body: some View {
        ZStack {
            ForEach(Array(rings.enumerated()), id: \.offset) { i, ring in
                layer(ringStyle(ring, outermost: i == 0)).offset(y: ringDY)
            }
            if innerDY != 0, let o = style.outline {
                layer(extrusion(o)).offset(y: innerDY)
            }
            layer(rings.isEmpty ? style : noDrop(style))
        }
    }

    private func extrusion(_ c: Color) -> GameTextStyle {
        var s = style
        s.fill = [c]
        s.band = nil
        s.drop = 0
        return s
    }

    private func ringStyle(_ ring: (Color, CGFloat), outermost: Bool) -> GameTextStyle {
        var s = style
        s.fill = [ring.0]
        s.outline = ring.0
        s.outlineWidth = ring.1
        s.band = nil
        if outermost {
            s.dropColor = style.dropColor ?? style.outline
        } else {
            s.drop = 0
        }
        return s
    }

    private func noDrop(_ s: GameTextStyle) -> GameTextStyle { var s = s; s.drop = 0; return s }

    @ViewBuilder private func layer(_ s: GameTextStyle) -> some View {
        switch source {
        case .copy(let r): GameText(r, style: s, maxWidth: maxWidth)
        case .number(let n): GameText(verbatim: n, style: s, maxWidth: maxWidth)
        }
    }
}

extension Tokens {
    /// `text.<id>.rings` = [["#hex", width], …] (outermost first), else the compiled default.
    func rings(_ id: String, _ d: [(UInt32, CGFloat)]) -> [(Color, CGFloat)] {
        if let raw = file.value("text.\(id).rings") as? [Any] {
            let parsed: [(Color, CGFloat)] = raw.compactMap { item in
                guard let pair = item as? [Any], pair.count == 2, let hex = pair[0] as? String, let c = Color(hexString: hex),
                      let w = (pair[1] as? NSNumber)?.doubleValue else { return nil }
                return (c, CGFloat(w))
            }
            if parsed.count == raw.count { return parsed }
        }
        return d.map { (Color(hex: $0.0), $0.1) }
    }

    /// `numbers.<id>` = [a, b, …] (any list of pt/seconds), else the default.
    func list(_ id: String, _ d: [Double]) -> [Double] {
        let v = file.doubles(id, [])
        return v.count == d.count ? v : d
    }
}

// MARK: - the HUD square button in the tier colour

struct TierPalette: Equatable {
    var shadow: UInt32, outer: [(UInt32, Double)], side: UInt32, face: [UInt32], rim: [(UInt32, Double)]
    var glyph: UInt32, glyphLine: UInt32
    /// The pause bars' tinted foot (VERIFIED 003 #7CB7DB, 036 #9A5454, 061 #AB54EF at y 96) and the bar outline (#072884,
    /// #650000, #4C0088 at y 97.5).
    var barFoot: [UInt32] = [0xB6D5CC, 0x81BBB0]
    var barLine: UInt32? = nil

    static func == (a: TierPalette, b: TierPalette) -> Bool { a.shadow == b.shadow && a.face == b.face && a.glyph == b.glyph }

    /// GlossyChrome BlueSquareButton's numbers (VERIFIED 003).
    static let blue = TierPalette(shadow: 0x212B2B,
                                  outer: [(0x00625D, 0), (0x006864, 0.1), (0x006C68, 0.86), (0x007B76, 0.9), (0x006864, 0.94),
                                          (0x005F5B, 0.97), (0x005050, 1)],
                                  side: 0x004148, face: [0x00A293, 0x009C8F],
                                  rim: [(0x62CDBF, 0), (0x50C3B5, 0.07), (0x009E90, 0.14), (0x00998C, 0.6), (0x009C8F, 1)],
                                  glyph: 0xF3FDF9, glyphLine: 0x003B3F)
    /// Hard (VERIFIED 036 grad.hud.pauseButtonHard: face #EC0911, rim #FC777A → #FD5357, lip #A3010F → #780109).
    static let red = TierPalette(shadow: 0x370E05,
                                 outer: [(0x88160D, 0), (0x9F1D12, 0.1), (0xA92014, 0.86), (0xB72B1D, 0.9), (0x9D170D, 0.94),
                                         (0x85130B, 0.97), (0x740E05, 1)],
                                 side: 0x660C03, face: [0xEC6552, 0xE64D39, 0xDD3624],
                                 rim: [(0xED8272, 0), (0xED7866, 0.07), (0xE2523F, 0.14), (0xDE3F2D, 0.6), (0xDD3624, 1)],
                                 glyph: 0xFFF5F5, glyphLine: 0x86251D, barFoot: [0xC39891, 0x925950], barLine: 0x610B00)
    /// Super Hard (VERIFIED 061 grad.hud.pauseButtonSuperHard: face #9100E4, rim #B751FC, lip #6909B1 → #480683).
    static let purple = TierPalette(shadow: 0x2B131C,
                                    outer: [(0x751545, 0), (0x8A1653, 0.1), (0x96125A, 0.86), (0xA51666, 0.9), (0x891351, 0.94),
                                            (0x741243, 0.97), (0x601036, 1)],
                                    side: 0x4F0E2B, face: [0xCE0077, 0xC70074, 0xBA006E],
                                    rim: [(0xEE3A89, 0), (0xE62D84, 0.07), (0xCD0D77, 0.14), (0xC20172, 0.6), (0xBA006E, 1)],
                                    glyph: 0xFFF6F9, glyphLine: 0x65173C, barFoot: [0xF18FB3, 0xDE4286], barLine: 0x640D38)

    static func of(_ tag: LevelTag) -> TierPalette {
        switch tag {
        case .normal: return .blue
        case .hard: return .red
        case .superHard: return .purple
        }
    }

    var key: String { String(format: "%06X", face.last ?? 0) }
}

/// The 40 × 40 pt body in a 44 × 44 frame (GlossyChrome BlueSquareButton's geometry), glyph `back` or `pause`.
struct TierSquareButton: View {
    enum Glyph: String { case back, pause }
    let palette: TierPalette
    let glyph: Glyph

    var body: some View {
        Rasterized("tierSquare|\(palette.key)|\(glyph.rawValue)", overflow: 2) { _ in art }
            .frame(width: 44, height: 44)
    }

    private var art: some View {
        let shape = Superellipse(n: 3.5)
        let p = palette
        return ZStack {
            shape.fill(Color(hex: p.shadow, 0.8)).blur(radius: 0.93).offset(y: 1)
            shape.fill(LinearGradient(stops: p.outer.map { .init(color: Color(hex: $0.0), location: $0.1) }, startPoint: .top, endPoint: .bottom))
            shape.fill(LinearGradient(stops: [.init(color: Color(hex: p.side, 0.6), location: 0), .init(color: Color(hex: p.side, 0), location: 0.09),
                                              .init(color: Color(hex: p.side, 0), location: 0.91), .init(color: Color(hex: p.side, 0.6), location: 1)],
                                      startPoint: .leading, endPoint: .trailing))
            ZStack {
                shape.fill(LinearGradient(colors: p.face.map { Color(hex: $0) }, startPoint: .top, endPoint: .bottom))
                shape.stroke(LinearGradient(stops: p.rim.map { .init(color: Color(hex: $0.0), location: $0.1) }, startPoint: .top, endPoint: .bottom),
                             lineWidth: 2.33).blur(radius: 0.23).clipShape(shape)
            }
            .frame(width: 32, height: 34).position(x: 20, y: 19)
            glyphView
        }
        .frame(width: 40, height: 40)
        .offset(y: -0.67)
        .frame(width: 44, height: 44)
    }

    @ViewBuilder private var glyphView: some View {
        switch glyph {
        case .pause:
            HStack(spacing: 4) { bar; bar }.frame(width: 16, height: 20.33).position(x: 20, y: 20.5)
        case .back:
            // VERIFIED 003 / 036 / 061: a white triangle with a darker extrusion down-right, no outline on its lit edges
            ZStack {
                BackTriangle().fill(Color(hex: palette.glyphLine, 0.85)).offset(x: 0.9, y: 1.7)
                BackTriangle().fill(LinearGradient(colors: [Color(hex: palette.glyph), Color(hex: palette.glyph), Color(hex: palette.glyph, 0.92)],
                                                   startPoint: .top, endPoint: .bottom))
            }
            .frame(width: 17.5, height: 21)
            .position(x: 18.4, y: 19.6)
        }
    }

    private var bar: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 2.33, style: .continuous).fill(Color(hex: palette.barLine ?? palette.glyphLine))
            ZStack(alignment: .bottom) {
                Color(hex: palette.glyph)
                VStack(spacing: 0) { Color(hex: palette.barFoot[0]).frame(height: 1.33); Color(hex: palette.barFoot[1]).frame(height: 1.0) }
            }
            .clipShape(RoundedRectangle(cornerRadius: 1.5, style: .continuous)).padding(1)
        }
        .frame(width: 6, height: 20.33)
    }
}

/// ◀ with rounded corners, pointing left.
private struct BackTriangle: Shape {
    func path(in r: CGRect) -> Path {
        let a = CGPoint(x: r.minX, y: r.midY), b = CGPoint(x: r.maxX, y: r.minY), c = CGPoint(x: r.maxX, y: r.maxY)
        var p = Path()
        let rad: CGFloat = 2.6
        p.move(to: mid(a, b))
        p.addArc(tangent1End: b, tangent2End: c, radius: rad)
        p.addArc(tangent1End: c, tangent2End: a, radius: rad)
        p.addArc(tangent1End: a, tangent2End: b, radius: rad)
        p.closeSubpath()
        return p
    }
    private func mid(_ p: CGPoint, _ q: CGPoint) -> CGPoint { CGPoint(x: (p.x + q.x) / 2, y: (p.y + q.y) / 2) }
}

// MARK: - the fail offers' coin group

/// Coin + light pill + green "+" (SPEC-ui §2.6: 12.7 · 62.4 · 108.4 · 44.4 on Out of Time / Lives; 12.7 · 96.1 · 105.1 ·
/// 41.4 on Continue?; digits 21.4 / +0.44 #093896). The same proportions as the home coin group (S1, VERIFIED 002), scaled to
/// the frame. Tapping it opens the Shop as a closable page over the offer (SPEC-ui §2.6.6) through `S2Hooks.openShop`.
struct OfferCoinGroup: View {
    let frame: CGRect
    let coins: Int
    let textID: String
    @Environment(AppModel.self) private var app

    var body: some View {
        let t = app.tuning.ui.tokens
        let k = frame.width / 108.4
        // VERIFIED 013 / 014 / meta-088 (the popup group is not the home group): pill 0 … 35.6 tall with a 3 pt blue base, its
        // right edge 0.7 inside the frame; coin gold 13.3 … 46.7 · 62.7 … 95.7 on 013; the plus's green 36 … 55 · 83.1 … 102.1
        let pill = CGRect(33.35 * k, 0, 74.4 * k, 35.6 * k)
        let digits = t.text(textID, .s2(21.4, 0.44, [0x00474D])).sized(21.4 * k)
        GameButton(id: "popup.coins", label: "Shop", value: "\(coins)", action: { S2Hooks.openShop(app) }) {
            ZStack(alignment: .topLeading) {
                OfferPill(t: t).placed(pill)
                GameText(verbatim: "\(coins)", style: digits, maxWidth: 58 * k)
                    .at(pill.minX + 38.4 * k, digits.capCentre(baseline: 25.0 * k))
                InkImage(art: .iconCoin, ink: CGRect(-1.1 * k, -0.4 * k, 37.0 * k, 38.3 * k))
                InkImage(art: .iconPlusGreen, ink: CGRect(21.9 * k, 18.7 * k, 22.3 * k, 23.1 * k))
            }
            .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        }
        .placed(frame)
        .anchor(.custom("popup.coins"))
    }
}

/// The popups' coin pill (VERIFIED 013 at x 100 / y 80): a navy hairline, a pale #DEEEFF face with a white inner highlight,
/// and a blue 3D base ~3 pt deep at the bottom, ~2 pt at the right.
struct OfferPill: View {
    let t: Tokens
    var body: some View { Rasterized("offerPill", overflow: 1) { size in art(size) } }

    private func art(_ size: CGSize) -> some View {
        let r = size.height * 0.36
        return ZStack {
            RoundedRectangle(cornerRadius: r, style: .continuous).fill(t.color("offer.pillLine", 0x233B3D))
            RoundedRectangle(cornerRadius: r - 0.6, style: .continuous)
                .fill(LinearGradient(colors: t.colors("offer.pillBase", [0x62A9A0, 0x22746E]), startPoint: .top, endPoint: .bottom))
                .padding(0.6)
            RoundedRectangle(cornerRadius: r - 1.5, style: .continuous).fill(t.color("offer.pillFace", 0xE0F0EB))
                .overlay(RoundedRectangle(cornerRadius: r - 1.5, style: .continuous).strokeBorder(Color(hex: 0xEFF6F4), lineWidth: 0.9))
                .padding(EdgeInsets(top: 0.9, leading: 1.2, bottom: 3.4, trailing: 2.4))
        }
    }
}

// MARK: - the popups' button well

/// The recessed blue well around a popup's framed button (measured on 013 / 014 / 016: a soft dark rim ~2 pt inside the token
/// frame, dark blue #024ABF at the rim easing into cyan #00A7F9 by ~5 pt at the sides, ~3 pt at the top and ~6 pt at the
/// bottom, and a soft navy shadow spilling ~3 pt under the frame). Distinct from S1's page `ButtonWell` (hard navy outline).
struct OfferWell: View {
    /// shadow, rim, deep (the dark band at the rim), core (the bright ring against the face)
    struct Palette: Equatable {
        let shadow, rim, deep, core: UInt32
        static let blue = Palette(shadow: 0x143739, rim: 0x114246, deep: 0x00615B, core: 0x35B1A1)
        static let red = Palette(shadow: 0x440B00, rim: 0x4B0C00, deep: 0x7F110A, core: 0xDB6150)
        static let purple = Palette(shadow: 0x380C1E, rim: 0x50102C, deep: 0x711241, core: 0xD6277C)
        var key: String { String(format: "%06X%06X", deep, core) }
    }
    /// Where the well's body sits inside its token frame: the band / fail / win frames include the halo (VERIFIED 014 / 016 /
    /// 020: rim ~2.4 pt in), the Out of Time / Out of Lives frames are the body itself (VERIFIED 013 / meta-088).
    static let haloInset = EdgeInsets(top: 1.8, leading: 2.4, bottom: -0.8, trailing: 2.4)
    static let tightInset = EdgeInsets(top: 0.4, leading: 0.3, bottom: 0, trailing: 0.3)
    var n: CGFloat = 4.8
    var palette: Palette = .blue
    var inset: EdgeInsets = OfferWell.haloInset
    let t: Tokens

    var body: some View {
        Rasterized("offerWell|\(n)|\(palette.key)|\(inset.top),\(inset.leading),\(inset.bottom)", overflow: 5) { _ in art }
    }

    @ViewBuilder private var art: some View {
        let shape = Superellipse(n: n)
        let body = inset
        ZStack {
            shape.fill(Color(hex: palette.shadow)).padding(body).offset(y: 1.8).blur(radius: 1.2).opacity(0.75)
            shape.fill(Color(hex: palette.rim)).padding(body).blur(radius: 0.45)
            ZStack {
                shape.fill(Color(hex: palette.deep))
                shape.fill(Color(hex: palette.core))
                    .padding(EdgeInsets(top: 2.2, leading: 4.4, bottom: 6.0, trailing: 4.4))
                    .blur(radius: 1.6)
            }
            .mask(shape.padding(1.0))
            .padding(body)
        }
        .accessibilityHidden(true)
    }
}

/// S2's framed green button without a price ("Try Again"): FramedButton's layout on the popup well.
struct WellFramedButton: View {
    let id: String
    let title: LocalizedStringResource
    let colors: PanelButtonStyleColors
    let frame: CGRect
    let well: CGRect
    let n: CGFloat
    let style: GameTextStyle
    let baseline: CGFloat
    let centreX: CGFloat
    var maxWidth: CGFloat? = nil
    let t: Tokens
    let action: () -> Void

    var body: some View {
        ZStack(alignment: .topLeading) {
            OfferWell(n: n - 0.2, t: t).placed(well)
            GameButton(id: id, label: title, action: action) {
                ZStack(alignment: .topLeading) {
                    ChromeButtonFace(colors: colors, n: n)
                    GameText(title, style: style, maxWidth: maxWidth)
                        .at(centreX - frame.minX, style.capCentre(baseline: baseline) - frame.minY)
                }
                .frame(width: frame.width, height: frame.height, alignment: .topLeading)
            }
            .placed(frame)
        }
    }
}

// MARK: - the framed wide green button with a price

/// Label + coin + price on a framed green button (SPEC-ui §1.6.2 "wide"): the blue well, the glossy face, the label and the
/// price in the green-outlined cream style, the coin icon between them.
struct PriceButton: View {
    let id: String
    let label: LocalizedStringResource
    let price: Int
    let face: CGRect
    let well: CGRect
    let n: CGFloat
    let labelID: String
    let labelStyle: GameTextStyle
    let labelAt: (x: CGFloat, baseline: CGFloat)
    let priceID: String
    let priceStyle: GameTextStyle
    let priceAt: (x: CGFloat, baseline: CGFloat)
    let coin: CGRect
    var wellInset: EdgeInsets = OfferWell.haloInset
    let action: () -> Void
    @Environment(AppModel.self) private var app

    var body: some View {
        let t = app.tuning.ui.tokens
        let ls = t.text(labelID, labelStyle), ps = t.text(priceID, priceStyle)
        let lp = t.textPoint(labelID, baseline: labelAt.baseline, centreX: labelAt.x)
        let pp = t.textPoint(priceID, baseline: priceAt.baseline, centreX: priceAt.x)
        ZStack(alignment: .topLeading) {
            OfferWell(n: n - 0.2, inset: wellInset, t: t).placed(well)
            GameButton(id: id, label: label, value: "\(price)", action: action) {
                ZStack(alignment: .topLeading) {
                    ChromeButtonFace(colors: .green, n: n)
                    GameText(label, style: ls, maxWidth: t.textMaxWidth(labelID, max(40, coin.minX - face.minX - 14)))
                        .at(lp.x - face.minX, ls.capCentre(baseline: lp.baseline) - face.minY)
                    InkImage(art: .iconCoin, ink: coin.offsetBy(dx: -face.minX, dy: -face.minY))
                    GameText(verbatim: "\(price)", style: ps)
                        .at(pp.x - face.minX, ps.capCentre(baseline: pp.baseline) - face.minY)
                }
                .frame(width: face.width, height: face.height, alignment: .topLeading)
            }
            .placed(face)
        }
    }
}
