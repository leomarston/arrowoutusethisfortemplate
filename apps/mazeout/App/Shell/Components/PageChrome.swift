import SwiftUI

// SHELL S1 (SPEC-ui §1.6.7-§1.6.14, §2.5, §2.13; VERIFIED meta-029/030/032 Settings, meta-075 Quit Level?). The chrome of v552's
// full pages and band popups, drawn in code at the measured frames (colours sampled on the captures; ui.json `colors.page.*`,
// `colors.settings.*`, `colors.band.*`, `colors.well.*`). Reused by S2 (the Continue? band family) and S3 (Profile, Shop pages):
//   ShellPageHeader   the light-blue header (0 → 104.4 pt), highlight line, lip and shadow; paints from y 0 (under the island)
//   ShellPageBackground the navy page ground (#0B2176 → #091B68) with the faint rotated-arrow pattern (our 64 pt tile, INFERRED)
//   PageTitle         `role.pageTitle` (37 / −1.0, face #E3F7FF, outline #022880, a 4.8 pt extrusion)
//   BlueCard          the Settings cards (dark outline, lighter top rim, #0B80FD → #2A60EF face, dark bottom bevel)
//   ButtonWell        the blue well around framed buttons (the home Play-frame recipe; Support, Quit, Refill …)
//   ShellSquareToggle 66 pt green square toggle (GlossyChrome's PanelButton recipe) in a dark-blue well; OFF = a red slash
//   PillLinkButton    the blue Terms / Privacy pills in a 3 pt navy well
//   BandPopupFrame    the full-width band of Quit Level? / Continue? (rails with light bumper ends + rivets, lips, fields,
//                     the cream strip)
//   RecolouredGlyph   an icon raster recoloured by its luminance (face) and silhouette (outline): the cream Pause glyphs drawn
//                     white on the green squares until UI-ART ships white variants
// Names avoid GlossyChrome's reserved symbols (PanelFrame, TitlePlate, CreamCard, CloseButton, PillToggle …) and the names
// CONSISTENCY U-30 may still hand to UI-ART (PageHeader, PageBackground, SquareToggle, BandPopup): S1's carry a `Shell` prefix or
// a distinct name until the orchestrator assigns them.

// MARK: - page

struct ShellPageHeader: View {
    let t: Tokens
    @Environment(\.shellMetrics) private var m

    var body: some View {
        // Measured on the reference canvas: body 0 → 103.1, highlight line → 104.4, lip → 110.4, shadow → 115 (top-anchored).
        // The metrics are read HERE (the raster renders outside this environment).
        let bottom = m.y(115, .top), width = m.size.width
        Rasterized("pageheader|\(width)|\(bottom)") { _ in Self.art(t: t, width: width, bottom: bottom) }
            .frame(width: width, height: bottom)
            .allowsHitTesting(false)
    }

    private static func art(t: Tokens, width: CGFloat, bottom: CGFloat) -> some View {
        let k = bottom / 115
        let stops = t.stops("page.headerStops", [(0, Skin.componentsPageChromePageHeaderStops0), (0.556, Skin.componentsPageChromePageHeaderStops1), (0.95, Skin.componentsPageChromePageHeaderStops2)])
        return ZStack(alignment: .topLeading) {
            LinearGradient(stops: stops, startPoint: .top, endPoint: .bottom)
                .frame(width: width, height: 103.1 * k)
            t.color("page.hiLine", Skin.componentsPageChromePageHiLine).frame(width: width, height: 1.3 * k).offset(y: 103.1 * k)
            LinearGradient(colors: t.colors("page.lip", [Skin.componentsPageChromePageLip0, Skin.componentsPageChromePageLip1]), startPoint: .top, endPoint: .bottom)
                .frame(width: width, height: 6.0 * k).offset(y: 104.4 * k)
            LinearGradient(colors: [t.color("page.shadow", Skin.componentsPageChromePageShadow), t.color("page.shadow", Skin.componentsPageChromePageShadow).opacity(0)],
                           startPoint: .top, endPoint: .bottom)
                .frame(width: width, height: 4.6 * k).offset(y: 110.4 * k)
        }
        .frame(width: width, height: bottom, alignment: .topLeading)
    }
}

struct ShellPageBackground: View {
    let t: Tokens

    var body: some View { Rasterized("pagebg") { _ in art } }

    @ViewBuilder private var art: some View {
        let ground = t.colors("page.bgNavy", [Skin.componentsPageChromePageBgNavy0, Skin.componentsPageChromePageBgNavy1])
        ZStack {
            LinearGradient(colors: ground, startPoint: .top, endPoint: .bottom)
            Canvas(opaque: false, rendersAsynchronously: false) { ctx, size in
                // our pattern: a 64 pt tile of three rotated arrow glyphs, ≈ 5 % darker than the ground (INFERRED meta-029)
                let ink = GraphicsContext.Shading.color(t.color("page.pattern", Skin.componentsPageChromePagePattern))
                let arrow = Path { p in
                    p.move(to: CGPoint(x: -9, y: 3)); p.addLine(to: CGPoint(x: 2, y: 3)); p.addLine(to: CGPoint(x: 2, y: 9))
                    p.addLine(to: CGPoint(x: 11, y: 0)); p.addLine(to: CGPoint(x: 2, y: -9)); p.addLine(to: CGPoint(x: 2, y: -3))
                    p.addLine(to: CGPoint(x: -9, y: -3)); p.closeSubpath()
                }
                let marks: [(CGFloat, CGFloat, Double, CGFloat)] = [(14, 18, -35, 1.3), (46, 30, 120, 1.0), (26, 52, 200, 1.15)]
                var y: CGFloat = 0
                while y < size.height {
                    var x: CGFloat = (Int(y / 64) % 2 == 0) ? 0 : -32
                    while x < size.width {
                        for (mx, my, deg, s) in marks {
                            var c = ctx
                            c.translateBy(x: x + mx, y: y + my)
                            c.rotate(by: .degrees(deg))
                            c.scaleBy(x: s, y: s)
                            c.fill(arrow, with: ink)
                        }
                        x += 64
                    }
                    y += 64
                }
            }
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

struct PageTitle: View {
    let title: LocalizedStringResource
    let t: Tokens
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let base = t.text("page.title", GameTextStyle(size: 37, tracking: -1.0, fill: [Color(hex: Skin.componentsPageChromePageTitleFill0)], outline: Color(hex: Skin.componentsPageChromePageTitleOutline),
                                                       outlineWidth: 1.0, drop: 4.8))
        let st = base.sized(base.size * m.s)
        let p = t.textPoint("page.title", baseline: 85.5, centreX: 196.5)
        let pt = m.point(CGPoint(x: p.x, y: p.baseline), .top)
        GameText(title, style: st, maxWidth: (t.textMaxWidth("page.title", 260) ?? 260) * m.s)
            .at(pt.x, st.capCentre(baseline: pt.y))
            .accessibilityAddTraits(.isHeader)
    }
}

// MARK: - cards, wells, toggles, pills

struct BlueCard: View {
    var radius: CGFloat = 23.7
    let t: Tokens

    var body: some View { Rasterized("bluecard|\(radius)", overflow: 4) { _ in art } }

    @ViewBuilder private var art: some View {
        let face = t.colors("settings.cardTop", [Skin.componentsPageChromeSettingsCardTop0, Skin.componentsPageChromeSettingsCardTop1]) + t.colors("settings.cardLow", [Skin.componentsPageChromeSettingsCardLow0, Skin.componentsPageChromeSettingsCardLow1])
        ZStack {
            RoundedRectangle(cornerRadius: radius).fill(Color(hex: Skin.componentsPageChromeBlueCardArtFill)).offset(y: 2.2)
            RoundedRectangle(cornerRadius: radius).fill(t.color("settings.cardOutline", Skin.componentsPageChromeSettingsCardOutline))
            RoundedRectangle(cornerRadius: radius - 1)
                .fill(LinearGradient(colors: [t.color("settings.cardLine", Skin.componentsPageChromeSettingsCardLine), Color(hex: Skin.componentsPageChromeBlueCardArtColors1), Color(hex: Skin.componentsPageChromeBlueCardArtColors2)],
                                     startPoint: .top, endPoint: .bottom))
                .padding(1)
            RoundedRectangle(cornerRadius: radius - 4)
                .fill(LinearGradient(stops: [.init(color: face[0], location: 0), .init(color: face[1], location: 0.38),
                                             .init(color: face[2], location: 0.55), .init(color: face[3], location: 1)],
                                     startPoint: .top, endPoint: .bottom))
                .padding(EdgeInsets(top: 4, leading: 4, bottom: 7, trailing: 4))
        }
        .accessibilityHidden(true)
    }
}

/// The blue well around a framed button (the home Play-frame recipe: #0E58C3 → #00A9FB at the top, #00A4F7 → #0071F3 at the
/// bottom, a dark navy outline).
struct ButtonWell: View {
    var n: CGFloat = 4.4
    let t: Tokens

    var body: some View { Rasterized("well|\(n)") { _ in art } }

    @ViewBuilder private var art: some View {
        let top = t.colors("well.top", [Skin.componentsPageChromeWellTop0, Skin.componentsPageChromeWellTop1]), bottom = t.colors("well.bottom", [Skin.componentsPageChromeWellBottom0, Skin.componentsPageChromeWellBottom1])
        ZStack {
            Superellipse(n: n).fill(Color(hex: Skin.componentsPageChromeButtonWellArtFill))
            Superellipse(n: n)
                .fill(LinearGradient(stops: [.init(color: top[0], location: 0), .init(color: top[1], location: 0.07),
                                             .init(color: bottom[0], location: 0.9), .init(color: bottom[1], location: 1)],
                                     startPoint: .top, endPoint: .bottom))
                .padding(1)
        }
        .accessibilityHidden(true)
    }
}

/// A green framed button with a live label (Support, the band popups' Quit …): the well + ChromeButtonFace + GameText.
struct FramedButton: View {
    let id: String
    let title: LocalizedStringResource
    let colors: PanelButtonStyleColors
    let frame: CGRect            // the button face (reference pt, in the parent)
    let well: CGRect
    let n: CGFloat
    let style: GameTextStyle
    let baseline: CGFloat        // reference pt
    let centreX: CGFloat
    var maxWidth: CGFloat? = nil
    let t: Tokens
    let action: () -> Void

    var body: some View {
        ZStack(alignment: .topLeading) {
            ButtonWell(t: t).placed(well)
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

/// Settings' Sound / Music / Haptic: a green square (the PanelButton recipe at 66 pt) in a dark-blue well, a white glyph, and
/// when OFF a red diagonal slash (#FF2626 core, #CD0000 edge, 6 pt, rounded caps) — the button itself stays green.
struct ShellSquareToggle: View {
    let id: String
    let glyph: UIArt
    let isOn: Bool
    let t: Tokens
    let action: () -> Void

    var body: some View {
        GameButton(id: id, value: isOn ? "on" : "off", action: action) {
            Rasterized("square|\(glyph.rawValue)|\(isOn)", overflow: 6) { _ in squareArt }
        }
    }

    private var squareArt: some View {
            GeometryReader { geo in
                let w = geo.size.width, h = geo.size.height
                ZStack {
                    // the well: 4.15 pt around the button, a light outer rim, dark blue inside
                    Superellipse(n: 3.6).fill(Color(hex: Skin.componentsPageChromeShellSquareToggleSquareArtFill)).frame(width: w + 8.3, height: h + 7.4)
                    Superellipse(n: 3.6).fill(LinearGradient(colors: [Color(hex: Skin.componentsPageChromeShellSquareToggleSquareArtColors0), Color(hex: Skin.componentsPageChromeShellSquareToggleSquareArtColors1), Color(hex: Skin.componentsPageChromeShellSquareToggleSquareArtColors2)],
                                                             startPoint: .top, endPoint: .bottom))
                        .frame(width: w + 6.3, height: h + 5.4)
                    ChromeButtonFace(colors: .green, n: t.superellipseN("settings.sound", 3.6), sideInset: 6)
                    RecolouredGlyph(art: glyph, face: Color(hex: Skin.componentsPageChromeShellSquareToggleSquareArtFace), outline: Color(hex: Skin.componentsPageChromeShellSquareToggleSquareArtOutline))
                        .frame(width: 42 * w / 66.1, height: 42 * w / 66.1)
                        .offset(y: -3 * h / 65.7)
                    if !isOn { Slash(t: t).frame(width: 48 * w / 66.1, height: 44 * w / 66.1).offset(y: -3 * h / 65.7) }
                }
                .frame(width: w, height: h)
            }
    }

    private struct Slash: View {
        let t: Tokens
        var body: some View {
            GeometryReader { geo in
                let w = geo.size.width, h = geo.size.height
                let line = Path { p in p.move(to: CGPoint(x: w - 3, y: 3)); p.addLine(to: CGPoint(x: 3, y: h - 3)) }
                ZStack {
                    line.stroke(t.color("settings.slashEdge", Skin.componentsPageChromeSettingsSlashEdge), style: StrokeStyle(lineWidth: 7.5, lineCap: .round))
                    line.stroke(t.color("settings.slash", Skin.componentsPageChromeSettingsSlash), style: StrokeStyle(lineWidth: 4.8, lineCap: .round))
                    line.stroke(Color.white.opacity(0.35), style: StrokeStyle(lineWidth: 1.2, lineCap: .round)).offset(x: -0.8, y: -0.8)
                }
            }
            .accessibilityHidden(true)
        }
    }
}

/// The blue Terms / Privacy pill in its 3 pt navy well (SPEC-ui §2.13; VERIFIED meta-029 column x 80).
struct PillLinkButton: View {
    let id: String
    let title: LocalizedStringResource
    let style: GameTextStyle
    var maxWidth: CGFloat? = nil
    let t: Tokens
    let action: () -> Void

    var body: some View {
        GameButton(id: id, label: title, action: action) {
            Rasterized("pill|\(String(localized: title))|\(style.size)|\(maxWidth ?? 0)", overflow: 5) { _ in pillArt }
        }
    }

    private var pillArt: some View {
            GeometryReader { geo in
                let w = geo.size.width, h = geo.size.height
                let n = t.superellipseN("settings.terms", 4.5)
                ZStack(alignment: .topLeading) {
                    Superellipse(n: n).fill(t.color("settings.pillWell", Skin.componentsPageChromeSettingsPillWell)).frame(width: w + 6, height: h + 6).offset(x: -3, y: -3)
                    Superellipse(n: n).fill(LinearGradient(colors: [Color(hex: Skin.componentsPageChromePillLinkButtonPillArtColors0), Color(hex: Skin.componentsPageChromePillLinkButtonPillArtColors1)], startPoint: .top,
                                                           endPoint: .bottom))
                    Superellipse(n: n + 0.4)
                        .fill(LinearGradient(colors: [Color(hex: Skin.componentsPageChromePillLinkButtonPillArtColors0V2), Color(hex: Skin.componentsPageChromePillLinkButtonPillArtColors1V2), t.color("settings.pill", Skin.componentsPageChromeSettingsPill),
                                                      Color(hex: Skin.componentsPageChromePillLinkButtonPillArtColors3)],
                                             startPoint: .top, endPoint: .bottom))
                        .frame(width: w - 2, height: h - 6.5).offset(x: 1, y: 1)
                    GameText(title, style: style, maxWidth: maxWidth).at(w / 2, style.capCentre(baseline: h * 32.5 / 49))
                }
            }
    }
}

/// A light icon raster with a dark outline around its silhouette (a 12-direction dilation; the Settings bell).
struct OutlinedArt: View {
    let art: UIArt
    let outline: Color
    var width: CGFloat = 1.3

    var body: some View { Rasterized("outlined|\(art.rawValue)|\(width)", overflow: 3) { _ in outlinedArt } }

    private var outlinedArt: some View {
        ZStack {
            ForEach(0..<12, id: \.self) { i in
                let a = Double(i) / 12 * 2 * .pi
                outline.mask(ArtImage(art: art)).offset(x: cos(a) * width, y: sin(a) * width)
            }
            ArtImage(art: art)
        }
        .accessibilityHidden(true)
    }
}

/// An icon raster recoloured: the silhouette in `outline`, the light parts (luminance, contrast-boosted) in `face`.
struct RecolouredGlyph: View {
    let art: UIArt
    let face: Color
    let outline: Color

    var body: some View {
        ZStack {
            outline.mask(ArtImage(art: art))
            face.mask(ArtImage(art: art).contrast(3.2).luminanceToAlpha())
        }
        .accessibilityHidden(true)
    }
}

// MARK: - band popup (Quit Level?, Continue?)

/// The full-width band: rails (light bumper ends 0-64 / 329-393 with rivets, a darker middle), dark lips, blue fields, the
/// navy line + cream edge, the cream strip 313.3-470 (VERIFIED meta-075 columns x 20/33/100/196). Drawn in a frame whose
/// height is the band's 405 pt; `creamTop`/`creamBottom` are offsets from the band top.
struct BandPopupFrame: View {
    let t: Tokens
    var creamTop: CGFloat = 79.1          // 313.3 − 234.2
    var creamBottom: CGFloat = 235.8      // 470.0 − 234.2

    var body: some View { Rasterized("band|\(creamTop)|\(creamBottom)") { _ in art } }

    @ViewBuilder private var art: some View {
        GeometryReader { geo in
            let W = geo.size.width, H = geo.size.height
            let bump = CGFloat(t.number("colors.band.bumperLen", 64))
            let rail = { (y: CGFloat, h: CGFloat, hiTop: Bool) -> AnyView in
                AnyView(ZStack(alignment: .topLeading) {
                    LinearGradient(colors: t.colors("band.railMid", [Skin.componentsPageChromeBandRailMid0, Skin.componentsPageChromeBandRailMid1]), startPoint: .top, endPoint: .bottom)
                        .frame(width: W, height: h)
                    ForEach([CGFloat(0), W - bump], id: \.self) { x in
                        ZStack(alignment: .top) {
                            t.color("band.bumper", Skin.componentsPageChromeBandBumper)
                            t.color("band.bumperHi", Skin.componentsPageChromeBandBumperHi).frame(height: 1.2).frame(maxHeight: .infinity, alignment: hiTop ? .top : .bottom)
                        }
                        .frame(width: bump, height: h)
                        .overlay(alignment: x == 0 ? .trailing : .leading) { Color(hex: Skin.componentsPageChromeBandPopupFrameRail).frame(width: 1.6) }
                        .offset(x: x)
                    }
                    ForEach(t.file.doubles("colors.band.rivetX", [55, 338]).map { CGFloat($0) }, id: \.self) { rx in
                        BandRivet(t: t).frame(width: 13, height: 13).position(x: rx < 196.5 ? rx : W - (393 - rx), y: h / 2)
                    }
                }
                .frame(width: W, height: h, alignment: .topLeading)
                .offset(y: y))
            }
            ZStack(alignment: .topLeading) {
                t.color("band.outline", Skin.componentsPageChromeBandOutline).frame(width: W, height: H)
                // top rail 0.5 … 21.8, its lines
                t.color("band.railLine", Skin.componentsPageChromeBandRailLine).frame(width: W, height: 1.3).offset(y: 0.5)
                rail(1.8, 20.0, false)
                t.color("band.railLine", Skin.componentsPageChromeBandRailLine).frame(width: W, height: 1.0).offset(y: 21.8)
                // dark lip 22.8 → 30.8, blue field → 70.8
                LinearGradient(colors: t.colors("band.lip", [Skin.componentsPageChromeBandLip0, Skin.componentsPageChromeBandLip1]), startPoint: .top, endPoint: .bottom)
                    .frame(width: W, height: 8.0).offset(y: 22.8)
                t.color("band.field", Skin.componentsPageChromeBandField).frame(width: W, height: 40).offset(y: 30.8)
                // navy line + dark line + cream edge → the cream strip
                t.color("band.line", Skin.componentsPageChromeBandLine).frame(width: W, height: 2.7).offset(y: creamTop - 8.4)
                t.color("band.lineDark", Skin.componentsPageChromeBandLineDark).frame(width: W, height: 1.2).offset(y: creamTop - 5.7)
                LinearGradient(colors: t.colors("band.creamEdge", [Skin.componentsPageChromeBandCreamEdge0, Skin.componentsPageChromeBandCreamEdge1]), startPoint: .top, endPoint: .bottom)
                    .frame(width: W, height: 4.5).offset(y: creamTop - 4.5)
                t.color("band.cream", Skin.componentsPageChromeBandCream).frame(width: W, height: creamBottom - creamTop).offset(y: creamTop)
                LinearGradient(colors: [Color(hex: Skin.componentsPageChromeBandPopupFrameArtColors0), Color(hex: Skin.componentsPageChromeBandPopupFrameArtColors1)], startPoint: .top, endPoint: .bottom)
                    .frame(width: W, height: 5.3).offset(y: creamBottom)
                t.color("band.line", Skin.componentsPageChromeBandLine).frame(width: W, height: 1.5).offset(y: creamBottom + 5.3)
                t.color("band.lineDark", Skin.componentsPageChromeBandLineDark).frame(width: W, height: 1.2).offset(y: creamBottom + 6.8)
                // lower field → the bottom lip → the bottom rail
                t.color("band.field", Skin.componentsPageChromeBandField).frame(width: W, height: H - 32.3 - creamBottom - 8.0).offset(y: creamBottom + 8.0)
                LinearGradient(colors: t.colors("band.lowLip", [Skin.componentsPageChromeBandLowLip0, Skin.componentsPageChromeBandLowLip1]), startPoint: .top, endPoint: .bottom)
                    .frame(width: W, height: 8.5).offset(y: H - 32.3)
                t.color("band.outline", Skin.componentsPageChromeBandOutline).frame(width: W, height: 1.5).offset(y: H - 23.8)
                rail(H - 22.3, 19.3, true)
                t.color("band.railLine", Skin.componentsPageChromeBandRailLine).frame(width: W, height: 1.5).offset(y: H - 3.0)
            }
            .frame(width: W, height: H, alignment: .topLeading)
            .clipped()
        }
        .accessibilityHidden(true)
    }
}

private struct BandRivet: View {
    let t: Tokens
    var body: some View {
        ZStack {
            Circle().fill(Color(hex: Skin.componentsPageChromeBandRivetFill))
            Circle().fill(RadialGradient(colors: [Color(hex: Skin.componentsPageChromeBandRivetColors0), Color(hex: Skin.componentsPageChromeBandRivetColors1), t.color("band.rivet", Skin.componentsPageChromeBandRivet)],
                                         center: UnitPoint(x: 0.42, y: 0.38), startRadius: 0, endRadius: 6)).padding(1.2)
        }
    }
}
