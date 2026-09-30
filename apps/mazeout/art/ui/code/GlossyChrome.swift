// GlossyChrome.swift — route B, "SwiftUI in code" variant of the glossy UI chrome (art spike, 2026-09-25).
// Pure SwiftUI (iOS 17 / macOS 14): the same file renders in the app and in art/ui/tools/swiftui_render.swift
// (ImageRenderer, macOS) for the side-by-side sheets. Every number is the SVG variant's (art/ui/src/gen_chrome.py)
// divided by 3: measured on runner shots 003 (HUD) and 007 (Paused panel). See art/STYLE.md §B.
import SwiftUI

// MARK: shapes

/// |x/a|^n + |y/b|^n = 1 — the pillow squircle of every glossy button (n 3.5 square HUD buttons, 4 wide buttons).
struct Superellipse: Shape {
    var n: CGFloat = 4
    func path(in r: CGRect) -> Path {
        var p = Path()
        let a = r.width / 2, b = r.height / 2, cx = r.midX, cy = r.midY
        let N = 160
        for i in 0..<N {
            let t = CGFloat(i) / CGFloat(N) * 2 * .pi
            let c = cos(t), s = sin(t)
            let pt = CGPoint(x: cx + a * copysign(pow(abs(c), 2 / n), c), y: cy + b * copysign(pow(abs(s), 2 / n), s))
            if i == 0 { p.move(to: pt) } else { p.addLine(to: pt) }
        }
        p.closeSubpath()
        return p
    }
}

/// The glossy heart outline: the union of two ellipses leaning +-48 deg toward the tip (art/ui/src/shapes.py HEART2,
/// fitted on shot 003's HUD heart, silhouette IoU 0.981): rx 0.46 w, ry 0.38 h, centres (0.5 +- 0.105) w, 0.485 h,
/// plus a tip wedge (base y 0.89 h, half-width 0.21 w, apex at h).
struct GlossyHeartShape: Shape {
    func path(in r: CGRect) -> Path {
        let w = r.width, h = r.height
        func lobe(_ cx: CGFloat, _ deg: CGFloat) -> CGPath {
            let rx = 0.46 * w, ry = 0.38 * h
            var t = CGAffineTransform(translationX: r.minX + cx * w, y: r.minY + 0.485 * h).rotated(by: deg * .pi / 180)
            return CGPath(ellipseIn: CGRect(x: -rx, y: -ry, width: 2 * rx, height: 2 * ry), transform: &t)
        }
        let tip = CGMutablePath()
        tip.addLines(between: [CGPoint(x: r.minX + 0.29 * w, y: r.minY + 0.89 * h), CGPoint(x: r.minX + 0.71 * w, y: r.minY + 0.89 * h),
                               CGPoint(x: r.minX + 0.5 * w, y: r.maxY)])
        tip.closeSubpath()
        return Path(lobe(0.395, 48).union(lobe(0.605, -48)).union(tip))
    }
}

extension Color {
    init(hex: UInt32, _ a: Double = 1) {
        self.init(.sRGB, red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255,
                  blue: Double(hex & 0xFF) / 255, opacity: a)
    }
}

// MARK: the square blue HUD button (pause, back, settings): 40 x 40 pt body in a 44 x 44 frame

struct BlueSquareButton<Glyph: View>: View {
    @ViewBuilder var glyph: () -> Glyph
    var body: some View {
        let shape = Superellipse(n: 3.5)
        let face = Superellipse(n: 3.5)
        ZStack {
            shape.fill(Color(hex: Skin.artGlossyChromeBlueSquareButtonFill, 0.8)).blur(radius: 0.93).offset(y: 1)
            shape.fill(LinearGradient(stops: [.init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops0), location: 0), .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops1), location: 0.1),
                                              .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops2), location: 0.86), .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops3), location: 0.9),
                                              .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops4), location: 0.94), .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops5), location: 0.97),
                                              .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops6), location: 1)], startPoint: .top, endPoint: .bottom))
            shape.fill(LinearGradient(stops: [.init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops0V2, 0.6), location: 0), .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops1V2, 0), location: 0.09),
                                              .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops2V2, 0), location: 0.91), .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops3V2, 0.6), location: 1)],
                                      startPoint: .leading, endPoint: .trailing))
            ZStack {
                face.fill(LinearGradient(colors: [Color(hex: Skin.artGlossyChromeBlueSquareButtonColors0), Color(hex: Skin.artGlossyChromeBlueSquareButtonColors1)], startPoint: .top, endPoint: .bottom))
                face.stroke(LinearGradient(stops: [.init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops0V3), location: 0), .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops1V3), location: 0.07),
                                                   .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops2V3), location: 0.14), .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops3V3), location: 0.6),
                                                   .init(color: Color(hex: Skin.artGlossyChromeBlueSquareButtonStops4V2), location: 1)],
                                           startPoint: .top, endPoint: .bottom), lineWidth: 2.33).blur(radius: 0.23).clipShape(face)
            }
            .frame(width: 32, height: 34).position(x: 20, y: 2 + 17)
            glyph()
        }
        .frame(width: 40, height: 40)
        .offset(y: -0.67)
        .frame(width: 44, height: 44)
    }
}

struct PauseGlyph: View {
    var body: some View {
        HStack(spacing: 4) { bar; bar }.frame(width: 16, height: 20.33).position(x: 20, y: 10.33 + 10.17)
    }
    var bar: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 2.33, style: .continuous).fill(Color(hex: Skin.artGlossyChromePauseGlyphBarFill))
            ZStack(alignment: .bottom) {
                Color(hex: Skin.artGlossyChromePauseGlyphBar)
                VStack(spacing: 0) { Color(hex: Skin.artGlossyChromePauseGlyphBarV2).frame(height: 1.33); Color(hex: Skin.artGlossyChromePauseGlyphBarV3).frame(height: 1.0) }
            }
            .clipShape(RoundedRectangle(cornerRadius: 1.5, style: .continuous)).padding(1)
        }
        .frame(width: 6, height: 20.33)
    }
}

// MARK: the glossy HUD heart: 29.3 x 25.3 pt in a 31 x 27 frame

struct HeartHUD: View {
    var body: some View {
        let s = GlossyHeartShape()
        ZStack {
            s.fill(Color(hex: Skin.artGlossyChromeHeartHUDFill, 0.6)).blur(radius: 0.67).offset(y: 0.33)
            s.fill(EllipticalGradient(stops: [.init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops0), location: 0), .init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops1), location: 0.25),
                                              .init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops2), location: 0.55), .init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops3), location: 0.8),
                                              .init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops4), location: 1)],
                                      center: UnitPoint(x: 0.39, y: 0.37), startRadiusFraction: 0, endRadiusFraction: 0.62))
            s.fill(LinearGradient(stops: [.init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops0V2, 0.8), location: 0), .init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops1V2, 0), location: 0.14),
                                          .init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops2V2, 0), location: 0.78), .init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops3V2, 0.45), location: 1)],
                                  startPoint: .top, endPoint: .bottom))
            ZStack {
                Ellipse().fill(RadialGradient(stops: [.init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops0V3, 0.95), location: 0), .init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops1V3, 0.55), location: 0.45),
                                                      .init(color: Color(hex: Skin.artGlossyChromeHeartHUDStops2V3, 0), location: 1)], center: .center, startRadius: 0, endRadius: 3.33))
                    .frame(width: 6.67, height: 4.67).rotationEffect(.degrees(-38)).blur(radius: 0.3).position(x: 9, y: 8.33)
                Path { p in p.move(to: CGPoint(x: 21, y: 2.67)); p.addQuadCurve(to: CGPoint(x: 27.33, y: 8.67), control: CGPoint(x: 26.33, y: 3)) }
                    .stroke(Color(hex: Skin.artGlossyChromeHeartHUDStroke, 0.7), style: StrokeStyle(lineWidth: 0.8, lineCap: .round)).blur(radius: 0.3)
                s.stroke(Color(hex: Skin.artGlossyChromeHeartHUDStrokeV2), lineWidth: 1.67).blur(radius: 0.23)
            }
            .clipShape(s)
            s.stroke(Color(hex: Skin.artGlossyChromeHeartHUDStrokeV3), lineWidth: 0.53)
        }
        .frame(width: 29.33, height: 25.33)
        .offset(y: -0.33)
        .frame(width: 31, height: 27)
    }
}

// MARK: the big glossy panel button (Resume green, Quit red): 125 x 89 pt body in a 127 x 91 frame; the label is live text

struct PanelButtonStyleColors {
    var outline: UInt32, edgeDark: UInt32, rim: [(UInt32, Double)], face: [(UInt32, Double)], edge: UInt32, glare: UInt32
    static let green = PanelButtonStyleColors(outline: Skin.artGlossyChromePanelButtonStyleColorsGreenOutline, edgeDark: Skin.artGlossyChromePanelButtonStyleColorsGreenEdgeDark,
                                              rim: [(Skin.artGlossyChromePanelButtonStyleColorsGreenRim0, 0), (Skin.artGlossyChromePanelButtonStyleColorsGreenRim1, 0.55), (Skin.artGlossyChromePanelButtonStyleColorsGreenRim2, 0.84), (Skin.artGlossyChromePanelButtonStyleColorsGreenRim3, 0.9), (Skin.artGlossyChromePanelButtonStyleColorsGreenRim4, 0.96), (Skin.artGlossyChromePanelButtonStyleColorsGreenRim5, 1)],
                                              face: [(Skin.artGlossyChromePanelButtonStyleColorsGreenFace0, 0), (Skin.artGlossyChromePanelButtonStyleColorsGreenFace1, 0.07), (Skin.artGlossyChromePanelButtonStyleColorsGreenFace2, 0.1), (Skin.artGlossyChromePanelButtonStyleColorsGreenFace3, 0.3), (Skin.artGlossyChromePanelButtonStyleColorsGreenFace4, 0.65), (Skin.artGlossyChromePanelButtonStyleColorsGreenFace5, 1)],
                                              edge: Skin.artGlossyChromePanelButtonStyleColorsGreenEdge, glare: Skin.artGlossyChromePanelButtonStyleColorsGreenGlare)
    static let red = PanelButtonStyleColors(outline: Skin.artGlossyChromePanelButtonStyleColorsRedOutline, edgeDark: Skin.artGlossyChromePanelButtonStyleColorsRedEdgeDark,
                                            rim: [(Skin.artGlossyChromePanelButtonStyleColorsRedRim0, 0), (Skin.artGlossyChromePanelButtonStyleColorsRedRim1, 0.55), (Skin.artGlossyChromePanelButtonStyleColorsRedRim2, 0.84), (Skin.artGlossyChromePanelButtonStyleColorsRedRim3, 0.9), (Skin.artGlossyChromePanelButtonStyleColorsRedRim4, 0.96), (Skin.artGlossyChromePanelButtonStyleColorsRedRim5, 1)],
                                            face: [(Skin.artGlossyChromePanelButtonStyleColorsRedFace0, 0), (Skin.artGlossyChromePanelButtonStyleColorsRedFace1, 0.07), (Skin.artGlossyChromePanelButtonStyleColorsRedFace2, 0.1), (Skin.artGlossyChromePanelButtonStyleColorsRedFace3, 0.3), (Skin.artGlossyChromePanelButtonStyleColorsRedFace4, 0.65), (Skin.artGlossyChromePanelButtonStyleColorsRedFace5, 1)],
                                            edge: Skin.artGlossyChromePanelButtonStyleColorsRedEdge, glare: Skin.artGlossyChromePanelButtonStyleColorsRedGlare)
}

struct PanelButton: View {
    var colors: PanelButtonStyleColors = .green
    var label: String? = nil
    var body: some View {
        let shape = Superellipse(n: 4), face = Superellipse(n: 4.5)
        let grad = { (st: [(UInt32, Double)]) in LinearGradient(stops: st.map { .init(color: Color(hex: $0.0), location: $0.1) }, startPoint: .top, endPoint: .bottom) }
        ZStack {
            shape.fill(Color(hex: colors.outline))
            ZStack {
                shape.fill(grad(colors.rim))
                shape.stroke(Color(hex: colors.edgeDark, 0.75), lineWidth: 4).blur(radius: 1.33).clipShape(shape)
            }
            .padding(1)
            ZStack {
                face.fill(grad(colors.face))
                face.stroke(Color(hex: colors.edge), lineWidth: 3.67).blur(radius: 0.4).clipShape(face)
                    .mask(LinearGradient(stops: [.init(color: .white.opacity(0.9), location: 0), .init(color: .white.opacity(0.6), location: 0.5),
                                                 .init(color: .white.opacity(0.2), location: 1)], startPoint: .top, endPoint: .bottom))
                face.stroke(Color(hex: colors.glare, 0.85), lineWidth: 1.5)
                    .padding(EdgeInsets(top: 5.33, leading: 1.33, bottom: 4.67, trailing: 1.33))
                    .mask(LinearGradient(stops: [.init(color: .white, location: 0), .init(color: .white.opacity(0.55), location: 0.22),
                                                 .init(color: .clear, location: 0.55)], startPoint: .top, endPoint: .bottom))
            }
            .frame(width: 109.67, height: 77).position(x: 62.5, y: 1 + 38.5)
            if let label { OutlinedLabel(text: label, size: 27).position(x: 62.5, y: 40) }
        }
        .frame(width: 125, height: 89)
        .frame(width: 127, height: 91)
    }
}

/// Outlined casual-game text (cream fill, dark outline, a drop of the outline colour) — font is a placeholder until
/// the fonts lane picks the OFL match.
struct OutlinedLabel: View {
    var text: String
    var size: CGFloat
    var fill = Color(hex: Skin.artGlossyChromeOutlinedLabelFill)
    var outline = Color(hex: Skin.artGlossyChromeOutlinedLabelOutline)
    var body: some View {
        let f = Font.custom("Arial Rounded MT Bold", size: size)
        ZStack {
            ForEach(0..<16, id: \.self) { i in
                let a = Double(i) / 16 * 2 * .pi
                Text(text).font(f).foregroundStyle(outline).offset(x: cos(a) * 1.6, y: sin(a) * 1.6 + 1.3)
            }
            ForEach(0..<16, id: \.self) { i in
                let a = Double(i) / 16 * 2 * .pi
                Text(text).font(f).foregroundStyle(outline).offset(x: cos(a) * 1.6, y: sin(a) * 1.6)
            }
            Text(text).font(f).foregroundStyle(fill)
        }
    }
}
