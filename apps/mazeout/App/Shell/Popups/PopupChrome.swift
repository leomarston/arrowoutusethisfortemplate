import SwiftUI

// SHELL S1 (SPEC-architecture §6.6, §6.11; design/ui-measure.md "Chrome layer recipes"; art/STYLE.md §B.1). The shared chrome
// of v552's popups, drawn in code at the measured frames (ui.json `frames.pause.*`, colours `colors.panel.*` …):
//   PopupPanelFrame   blue panel: 1 pt navy outline, ~18 pt bar, lighter corner bumpers + rivets at their ends, a dark groove
//                     lightening into the field (superellipse n 6.3, `xsec.pause.panel.*`)
//   PopupRibbon       the ARCHED yellow title ribbon (SPEC.md §5 item 14: both edges on a ≈1100 pt circle, end corners r 27)
//                     with the outlined title (auto-shrinks, min 0.7)
//   PopupCard         the cream card: navy line, brown→peach bevel, bright line, fill #F8E7D2 (r 24.4)
//   PopupCloseButton  the red X disc ⌀45 in a 3.7 pt blue ring (SPEC-ui §1.6.3)
//   PopupToggle       the ON pill (green track + blue knob right); OFF = knob left + a dark-navy track with "OFF" (SPEC-ui C5)
//   ChromeButtonFace  GlossyChrome's PanelButton layer recipe at ANY size and exponent (Quit, Play, the link buttons)
// The names avoid GlossyChrome's reserved symbols (PanelFrame, TitlePlate, CreamCard, CloseButton, PillToggle …: UI-ART's;
// when UI-ART ships them this file routes through them).

// MARK: - panel frame

struct PopupPanelFrame: View {
    var n: CGFloat = 6.3
    let t: Tokens
    /// The bumper arms (pt from each corner) and the rivet centres (relative to the panel), VERIFIED 007 at 370.6 x 399.
    var bumperArm = CGSize(width: 80, height: 87)
    var rivetInset = CGPoint(x: 12.2, y: 80.2)
    var rivetAlong: CGFloat = 73

    var body: some View { Rasterized("panel|\(n)|\(bumperArm.width)x\(bumperArm.height)|\(rivetInset.x),\(rivetInset.y)|\(rivetAlong)") { _ in art } }

    @ViewBuilder private var art: some View {
        GeometryReader { geo in
            let r = CGRect(origin: .zero, size: geo.size)
            let outer = Superellipse(n: n)
            let bar: CGFloat = 18.6
            ZStack(alignment: .topLeading) {
                outer.fill(t.color("panel.outline", Skin.popupsPopupChromePanelOutline))
                outer.fill(LinearGradient(colors: t.colors("panel.bar", [Skin.popupsPopupChromePanelBar0, Skin.popupsPopupChromePanelBar1]), startPoint: .top, endPoint: .bottom))
                    .padding(0.8)
                // corner bumpers: the outer shape in the lighter colour, masked to the four corner arms; the groove and the
                // field drawn next cover its inside, so only the bar ring shows it
                outer.fill(LinearGradient(colors: t.colors("panel.bumper", [Skin.popupsPopupChromePanelBumper0, Skin.popupsPopupChromePanelBumper1, Skin.popupsPopupChromePanelBumper2]), startPoint: .topLeading,
                                          endPoint: .bottomTrailing))
                    .padding(0.8)
                    .mask(CornerArms(arm: bumperArm))
                // groove + field with the inner shadow lightening over ~10 pt
                Superellipse(n: n).fill(t.color("panel.groove", Skin.popupsPopupChromePanelGroove)).padding(bar)
                ZStack {
                    Superellipse(n: n).fill(t.color("panel.field", Skin.popupsPopupChromePanelField))
                    Superellipse(n: n).stroke(t.color("panel.groove", Skin.popupsPopupChromePanelGroove), lineWidth: 16).blur(radius: 4.5)
                        .clipShape(Superellipse(n: n))
                    // FIX-2 B (F-19, V2: the phone's 1 pt light rim at the field edge, #298FF9 → D1 `colors.panel.fieldRim`): drawn
                    // over the inner shadow, inside the field (a 2 pt stroke clipped to the field = 1 pt)
                    Superellipse(n: n).stroke(t.color("panel.fieldRim", Skin.popupsPopupChromePanelFieldRim), lineWidth: 2)
                        .clipShape(Superellipse(n: n))
                }
                .padding(bar + 1.3)
                ForEach(Array(Rivet.all(in: r, inset: rivetInset, along: rivetAlong).enumerated()), id: \.offset) { _, p in
                    Rivet(t: t).frame(width: 13, height: 13).position(p)
                }
            }
        }
        .accessibilityHidden(true)
    }
}

/// Four corner rectangles (the bumper arms).
private struct CornerArms: Shape {
    var arm: CGSize
    func path(in r: CGRect) -> Path {
        var p = Path()
        let w = arm.width, h = arm.height
        for (x, y) in [(r.minX, r.minY), (r.maxX - w, r.minY), (r.minX, r.maxY - h), (r.maxX - w, r.maxY - h)] {
            p.addRect(CGRect(x: x, y: y, width: w, height: h))
        }
        return p
    }
}

private struct Rivet: View {
    let t: Tokens
    var body: some View {
        ZStack {
            Circle().fill(t.color("panel.rivetEdge", Skin.popupsPopupChromePanelRivetEdge))
            Circle().fill(RadialGradient(colors: [Color(hex: Skin.popupsPopupChromeRivetColors0), t.color("panel.rivet", Skin.popupsPopupChromePanelRivet), Color(hex: Skin.popupsPopupChromeRivetColors2)],
                                         center: UnitPoint(x: 0.4, y: 0.35), startRadius: 0, endRadius: 6)).padding(1.2)
        }
    }

    /// Rivet centres: on each side bar at `inset.y` from the top/bottom corners, and on the bottom bar at `along` from the sides.
    static func all(in r: CGRect, inset: CGPoint, along: CGFloat) -> [CGPoint] {
        [CGPoint(x: r.minX + inset.x, y: r.minY + inset.y), CGPoint(x: r.maxX - inset.x, y: r.minY + inset.y),
         CGPoint(x: r.minX + inset.x, y: r.maxY - inset.y), CGPoint(x: r.maxX - inset.x, y: r.maxY - inset.y),
         CGPoint(x: r.minX + along, y: r.maxY - inset.x), CGPoint(x: r.maxX - along, y: r.maxY - inset.x)]
    }
}

// MARK: - arched ribbon

/// A rounded rect whose top and bottom edges follow a circle of radius `bendRadius` (the middle higher than the ends).
struct ArchedBanner: Shape {
    var cornerRadius: CGFloat = 27
    var bendRadius: CGFloat = 1100
    /// The body thickness; the frame's extra height is the sag of the ends.
    var thickness: CGFloat? = nil

    func path(in r: CGRect) -> Path {
        let half = r.width / 2
        let sag = half * half / (2 * bendRadius)
        let h = thickness ?? max(1, r.height - sag)
        let body = CGRect(x: r.minX, y: r.minY, width: r.width, height: h)
        let flat = Path(roundedRect: body, cornerRadius: min(cornerRadius, h / 2), style: .circular)
        var out = Path()
        let cx = r.midX
        let bend = 2 * bendRadius
        let warp: (CGPoint) -> CGPoint = { (p: CGPoint) -> CGPoint in
            let dx: CGFloat = p.x - cx
            return CGPoint(x: p.x, y: p.y + dx * dx / bend)
        }
        // flatten to short segments and bend every point
        var last = CGPoint.zero
        flat.cgPath.applyWithBlock { el in
            let e = el.pointee
            switch e.type {
            case .moveToPoint:
                last = e.points[0]
                out.move(to: warp(last))
            case .addLineToPoint:
                let p = e.points[0]
                let steps = max(1, Int(abs(p.x - last.x) / 4))
                for i in 1...steps { out.addLine(to: warp(Self.lerp(last, p, CGFloat(i) / CGFloat(steps)))) }
                last = p
            case .addQuadCurveToPoint:
                let c = e.points[0], p = e.points[1]
                for i in 1...12 { out.addLine(to: warp(Self.quad(last, c, p, CGFloat(i) / 12))) }
                last = p
            case .addCurveToPoint:
                let c1 = e.points[0], c2 = e.points[1], p = e.points[2]
                for i in 1...12 { out.addLine(to: warp(Self.cubic(last, c1, c2, p, CGFloat(i) / 12))) }
                last = p
            case .closeSubpath:
                out.closeSubpath()
            @unknown default:
                break
            }
        }
        return out
    }

    private static func lerp(_ a: CGPoint, _ b: CGPoint, _ k: CGFloat) -> CGPoint {
        CGPoint(x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k)
    }

    private static func quad(_ a: CGPoint, _ c: CGPoint, _ b: CGPoint, _ k: CGFloat) -> CGPoint {
        lerp(lerp(a, c, k), lerp(c, b, k), k)
    }

    private static func cubic(_ a: CGPoint, _ c1: CGPoint, _ c2: CGPoint, _ b: CGPoint, _ k: CGFloat) -> CGPoint {
        lerp(quad(a, c1, c2, k), quad(c1, c2, b, k), k)
    }
}

struct PopupRibbon: View {
    let t: Tokens
    /// The frame height of the measured ribbon (90.4) = the body (≈ 84) + the ends' sag.
    var body: some View { Rasterized("ribbon") { _ in art } }

    @ViewBuilder private var art: some View {
        GeometryReader { geo in
            let r = CGRect(origin: .zero, size: geo.size)
            let sag = (r.width / 2) * (r.width / 2) / 2200
            let thick = r.height - sag
            ZStack(alignment: .topLeading) {
                ArchedBanner(thickness: thick).fill(LinearGradient(colors: [t.color("ribbon.outlineTop", Skin.popupsPopupChromeRibbonOutlineTop),
                                                                            t.color("ribbon.outlineBottom", Skin.popupsPopupChromeRibbonOutlineBottom)],
                                                                   startPoint: .top, endPoint: .bottom))
                ArchedBanner(cornerRadius: 26, thickness: thick - 2).fill(t.color("ribbon.shade", Skin.popupsPopupChromeRibbonShade))
                    .frame(width: r.width - 2, height: r.height - 2).offset(x: 1, y: 1)
                ArchedBanner(cornerRadius: 25, thickness: thick - 8.5).fill(t.color("ribbon.highlight", Skin.popupsPopupChromeRibbonHighlight))
                    .frame(width: r.width - 3, height: r.height - 8.5).offset(x: 1.5, y: 1.2)
                ArchedBanner(cornerRadius: 24, thickness: thick - 12)
                    .fill(LinearGradient(colors: t.colors("ribbon.face", [Skin.popupsPopupChromeRibbonFace0, Skin.popupsPopupChromeRibbonFace1]), startPoint: .top, endPoint: .bottom))
                    .frame(width: r.width - 4, height: r.height - 12).offset(x: 2, y: 4.5)
            }
        }
        .accessibilityHidden(true)
    }
}

/// The ribbon + its title (SPEC-ui §1.4 "Ribbon titles": the Paused style, box 228, shrink ≥ 0.7). The baseline sits
/// `ribbon.baselineFromTop` (57.0: fonts.md Paused 247.5 − 190.5) below the ribbon top unless a popup passes its measured one
/// (Quit Level? 253.4 − 193.5 = 59.9 at its shrunk 43.3 pt).
struct PopupTitle: View {
    let title: LocalizedStringResource
    let frame: CGRect
    let t: Tokens
    var baselineFromTop: CGFloat? = nil

    var body: some View {
        let style = t.text("popup.title", GameTextStyle(size: 49.2, tracking: -1.0, fill: [.white], outline: Color(hex: Skin.popupsPopupChromePopupTitleOutline),
                                                         outlineWidth: 1.87, drop: 3.15, band: Color(hex: Skin.popupsPopupChromePopupTitleBand), bandDY: 1.5))
        let base = baselineFromTop ?? CGFloat(t.number("ribbon.baselineFromTop", 57.0))
        ZStack(alignment: .topLeading) {
            PopupRibbon(t: t).placed(frame)
            GameText(title, style: style, maxWidth: t.textMaxWidth("popup.title", 228))
                .at(frame.midX, style.capCentre(baseline: frame.minY + base))
                .accessibilityIdentifier("popup.title")
        }
    }
}

// MARK: - cream card

struct PopupCard: View {
    var radius: CGFloat = 24.4
    let t: Tokens

    var body: some View { Rasterized("card|\(radius)", overflow: 2) { _ in art } }

    @ViewBuilder private var art: some View {
        let bevel = t.colors("card.bevel", [Skin.popupsPopupChromeCardBevel0, Skin.popupsPopupChromeCardBevel1, Skin.popupsPopupChromeCardBevel2])
        ZStack {
            RoundedRectangle(cornerRadius: radius).fill(t.color("card.outline", Skin.popupsPopupChromeCardOutline))
            RoundedRectangle(cornerRadius: radius - 1).fill(bevel[0]).padding(1)
            RoundedRectangle(cornerRadius: radius - 2.5).fill(bevel[min(1, bevel.count - 1)]).padding(2.5).blur(radius: 0.6)
            RoundedRectangle(cornerRadius: radius - 4.3).fill(bevel[bevel.count - 1]).padding(4.3).blur(radius: 0.4)
            RoundedRectangle(cornerRadius: radius - 5.7).fill(t.color("card.line", Skin.popupsPopupChromeCardLine)).padding(5.7)
            RoundedRectangle(cornerRadius: radius - 6.8).fill(t.color("card.fill", Skin.popupsPopupChromeCardFill)).padding(6.8)
        }
        .accessibilityHidden(true)
    }
}

// MARK: - close X

/// SPEC-ui §1.6.3: the placed frame is the red DISC (⌀45); the blue ring (3.7 pt, outer ⌀52.4, a dark outer line) is drawn
/// outside it, plus a soft dark halo to ⌀58 on page headers. Face #FF3B3C with a 1.3 pt dark-red rim; the glyph X #FFE9E9 with a
/// 1 pt #890E0E outline and a dark drop. The hit area extends to 56 pt (SPEC-ui §1.7).
struct PopupCloseButton: View {
    let id: String
    let t: Tokens
    var halo = false
    let action: () -> Void

    var body: some View {
        GameButton(id: id, label: "Close", action: action) {
            Rasterized("close|\(halo)", overflow: 8) { _ in closeArt }
        }
        .contentShape(Circle().inset(by: -6))
    }

    private var closeArt: some View {
        GeometryReader { geo in
                let d = min(geo.size.width, geo.size.height)
                let ring = d * 52.4 / 45
                ZStack {
                    if halo { Circle().fill(Color.black.opacity(0.35)).frame(width: d * 58 / 45, height: d * 58 / 45).blur(radius: 2.5) }
                    Circle().fill(t.color("close.ringOuter", Skin.popupsPopupChromeCloseRingOuter)).frame(width: ring, height: ring)
                    Circle().fill(LinearGradient(colors: t.colors("close.ring", [Skin.popupsPopupChromeCloseRing0, Skin.popupsPopupChromeCloseRing1, Skin.popupsPopupChromeCloseRing2]), startPoint: .top,
                                                 endPoint: .bottom))
                        .frame(width: ring - 1.4, height: ring - 1.4)
                    Circle().fill(LinearGradient(colors: t.colors("close.rim", [Skin.popupsPopupChromeCloseRim0, Skin.popupsPopupChromeCloseRim1]), startPoint: .top, endPoint: .bottom))
                        .frame(width: d, height: d)
                    Circle().fill(RadialGradient(colors: t.colors("close.face", [Skin.popupsPopupChromeCloseFace0, Skin.popupsPopupChromeCloseFace1, Skin.popupsPopupChromeCloseFace2, Skin.popupsPopupChromeCloseFace3]),
                                                 center: UnitPoint(x: 0.5, y: 0.34), startRadius: 0, endRadius: d * 0.52))
                        .frame(width: d - 2.6, height: d - 2.6)
                    Ellipse().fill(Color.white.opacity(0.22)).frame(width: d * 0.5, height: d * 0.2).offset(y: -d * 0.28)
                    CrossGlyph(t: t).frame(width: d * 0.56, height: d * 0.56).offset(y: -d * 0.01)
                }
                .frame(width: d, height: d)
        }
    }
}

private struct CrossGlyph: View {
    let t: Tokens
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let bar = RoundedRectangle(cornerRadius: w * 0.13)
            ZStack {
                ForEach([45.0, -45.0], id: \.self) { a in       // drop
                    bar.fill(t.color("close.glyphOutline", Skin.popupsPopupChromeCloseGlyphOutline)).frame(width: w * 1.04, height: w * 0.4).rotationEffect(.degrees(a))
                        .offset(y: w * 0.05)
                }
                ForEach([45.0, -45.0], id: \.self) { a in       // outline
                    bar.fill(t.color("close.glyphOutline", Skin.popupsPopupChromeCloseGlyphOutline)).frame(width: w * 1.04, height: w * 0.4).rotationEffect(.degrees(a))
                }
                ForEach([45.0, -45.0], id: \.self) { a in       // face
                    bar.fill(t.color("close.glyph", Skin.popupsPopupChromeCloseGlyph)).frame(width: w * 0.93, height: w * 0.29).rotationEffect(.degrees(a))
                }
            }
            .frame(width: w, height: w)
        }
    }
}

// MARK: - ON / OFF toggle

struct PopupToggle: View {
    enum Well { case cream, blue }
    let id: String
    let isOn: Bool
    let t: Tokens
    var well: Well = .cream
    let action: () -> Void
    /// A2 FEEL-P (owner item 8 / ruling 46; motion-catalog §11.3 R6, VERIFIED v582 60 Hz): the knob SLIDES 0.249 s
    /// easeInOutQuad (`toggle.slide`) and the track + its ON / OFF label flip in one frame when the knob's centre passes 26.5 %
    /// of its travel from the OFF end (`toggle.flipAt`: 68-78 % of the way turning OFF, 22-32 % turning ON on v582); no press
    /// scale. Frame-locked (a TimelineView that runs only while the knob moves); the track and the knob are two rasters.
    @State private var shownOn: Bool?                      // the state drawn at rest (set with the slide, never before it)
    @State private var slide: ToggleSlide?

    var body: some View {
        GameButton(id: id, value: isOn ? "on" : "off", presses: false, action: action) {
            TimelineView(.animation(minimumInterval: nil, paused: slide == nil)) { ctx in
                let p = slide?.position(ctx.date) ?? ((shownOn ?? isOn) ? 1 : 0)     // 0 = the OFF end, 1 = the ON end
                let trackOn = p > CGFloat(t.number("toggle.flipAt", 0.265))
                GeometryReader { geo in
                    let w = geo.size.width, h = geo.size.height
                    let knobW = w * 60.4 / 116.1
                    ZStack(alignment: .topLeading) {
                        Rasterized("toggleTrack|\(trackOn)|\(well)|\(String(localized: "ON"))|\(String(localized: "OFF"))", overflow: 5) { _ in
                            trackArt(on: trackOn)
                        }
                        Rasterized("toggleKnob|\(well)", overflow: 1) { _ in knobArt }
                            .frame(width: knobW, height: h)
                            .offset(x: p * (w - knobW))
                    }
                }
            }
        }
        .onChange(of: isOn) { old, new in
            let now = Date()
            let from = slide?.position(now) ?? (old ? 1 : 0)
            let dur = t.number("toggle.slide", 0.249)
            let s = ToggleSlide(from: from, to: new ? 1 : 0, start: now, duration: dur * Double(abs((new ? 1 : 0) - from)))
            slide = s
            shownOn = new
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: UInt64((s.duration + 0.05) * 1_000_000_000))
                if slide == s { slide = nil }
            }
        }
    }

    /// The well, the track (ON green / OFF navy) and its label — everything but the knob.
    private func trackArt(on isOn: Bool) -> some View {
            GeometryReader { geo in
                let w = geo.size.width, h = geo.size.height
                let knobW = w * 60.4 / 116.1
                let on = t.text("pause.toggleOn", GameTextStyle(size: 21, tracking: -0.75,
                                                                fill: [Color(hex: Skin.popupsPopupChromePauseToggleOnFill0), Color(hex: Skin.popupsPopupChromePauseToggleOnFill1), Color(hex: Skin.popupsPopupChromePauseToggleOnFill2)],
                                                                outline: Color(hex: Skin.popupsPopupChromePauseToggleOnOutline), outlineWidth: 1.0, drop: 1.01))
                // SPEC-ui C5 (VERIFIED meta-032): OFF = the knob on the LEFT, the right part a dark-navy track carrying "OFF"
                let off = t.text("pause.toggleOff", GameTextStyle(size: 21, tracking: -0.75, fill: [Color(hex: Skin.popupsPopupChromePauseToggleOffFill0)],
                                                                  outline: Color(hex: Skin.popupsPopupChromePauseToggleOffOutline), outlineWidth: 1.0, drop: 1.0))
                let k = h / 37.4
                ZStack(alignment: .topLeading) {
                    // the recessed well around the pill: light on the cream Pause card, dark blue on the Settings card
                    RoundedRectangle(cornerRadius: 12 * k)
                        .fill(LinearGradient(colors: well == .cream
                                             ? [Color(hex: Skin.popupsPopupChromePopupToggleTrackArtColorsCream0), t.color("toggle.well", Skin.popupsPopupChromeToggleWell), Color(hex: Skin.popupsPopupChromePopupToggleTrackArtColorsCream2)]
                                             : [Color(hex: Skin.popupsPopupChromePopupToggleTrackArtColorsNotCream0), Color(hex: Skin.popupsPopupChromePopupToggleTrackArtColorsNotCream1), Color(hex: Skin.popupsPopupChromePopupToggleTrackArtColorsNotCream2)],
                                             startPoint: .top, endPoint: .bottom))
                        .frame(width: w + (well == .blue ? 3 : 7), height: h + (well == .blue ? 3 : 7))
                        .offset(x: well == .blue ? -1.5 : -3.5, y: well == .blue ? -1.5 : -3.5)
                    if isOn {
                        // on the blue card the pill's rim is navy (VERIFIED meta-029); on the cream Pause card dark green (007)
                        RoundedRectangle(cornerRadius: 9 * k).fill(well == .blue ? Color(hex: Skin.popupsPopupChromePopupToggleTrackArtFill) : t.color("toggle.onEdge", Skin.popupsPopupChromeToggleOnEdge))
                        RoundedRectangle(cornerRadius: 8.5 * k)
                            .fill(LinearGradient(colors: t.colors("toggle.onTrack", [Skin.popupsPopupChromeToggleOnTrack0, Skin.popupsPopupChromeToggleOnTrack1, Skin.popupsPopupChromeToggleOnTrack2]), startPoint: .top,
                                                 endPoint: .bottom))
                            .padding(EdgeInsets(top: 1, leading: 1, bottom: 2.5, trailing: 1))
                        let st = on.sized(on.size * k)
                        GameText("ON", style: st, maxWidth: (w - knobW - 6)).at(w * 29.7 / 116.1, st.capCentre(baseline: h * 24.6 / 37.4))   // VERIFIED 007
                    } else {
                        RoundedRectangle(cornerRadius: 9 * k).fill(Color(hex: Skin.popupsPopupChromePopupToggleTrackArtFill))
                        RoundedRectangle(cornerRadius: 8.5 * k).fill(t.color("toggle.offTrack", Skin.popupsPopupChromeToggleOffTrack))
                            .padding(EdgeInsets(top: 1.2, leading: 1, bottom: 1.2, trailing: 1.2))
                        let st = off.sized(off.size * k)
                        // B3: the fit box is the navy part right of the knob less 1 pt (SPEC-ui measured the OFF label box at
                        // 53 of 116.1), not the track minus 6 pt: TR "KAPALI" needed 0.65 there (floor 0.70); "OFF" fits either way
                        GameText("OFF", style: st, maxWidth: w - knobW - 1)
                            .at(knobW + (w - knobW) / 2, st.capCentre(baseline: h * 24.6 / 37.4))
                    }
                }
            }
    }

    /// The knob (its own raster: it slides over the track).
    private var knobArt: some View {
        GeometryReader { geo in
            let k = geo.size.height / 37.4
            ZStack {
                RoundedRectangle(cornerRadius: 9.3 * k).fill(t.color("toggle.knobEdge", Skin.popupsPopupChromeToggleKnobEdge))
                RoundedRectangle(cornerRadius: 8.5 * k)
                    .fill(LinearGradient(colors: t.colors("toggle.knob", [Skin.popupsPopupChromeToggleKnob0, Skin.popupsPopupChromeToggleKnob1, Skin.popupsPopupChromeToggleKnob2]), startPoint: .top,
                                         endPoint: .bottom))
                    .padding(EdgeInsets(top: 1, leading: 1, bottom: 3, trailing: 1))
                RoundedRectangle(cornerRadius: 4).fill(Color.white.opacity(0.25)).frame(height: 3).padding(.horizontal, 8)
                    .frame(maxHeight: .infinity, alignment: .top).padding(.top, 3)
            }
        }
    }
}

/// One knob slide (A2): easeInOutQuad from `from` to `to` over `duration` (the full travel = `toggle.slide`).
struct ToggleSlide: Equatable {
    let from: CGFloat
    let to: CGFloat
    let start: Date
    let duration: Double

    func position(_ now: Date) -> CGFloat {
        let u = duration <= 0 ? 1 : min(1, max(0, now.timeIntervalSince(start) / duration))
        let e = u < 0.5 ? 2 * u * u : 1 - pow(-2 * u + 2, 2) / 2
        return from + (to - from) * CGFloat(e)
    }
}

// MARK: - wide glossy button face (GlossyChrome's PanelButton recipe, any size)

enum ChromePalette {
    /// Super Hard purple (grad.home.playButtonSuperHard: outline #230D63, face #AB54ED → #8300CF, bottom #31005E).
    static let purple = PanelButtonStyleColors(outline: Skin.popupsPopupChromeChromePalettePurpleOutline, edgeDark: Skin.popupsPopupChromeChromePalettePurpleEdgeDark,
                                               rim: [(Skin.popupsPopupChromeChromePalettePurpleRim0, 0), (Skin.popupsPopupChromeChromePalettePurpleRim1, 0.55), (Skin.popupsPopupChromeChromePalettePurpleRim2, 0.84), (Skin.popupsPopupChromeChromePalettePurpleRim3, 0.9),
                                                     (Skin.popupsPopupChromeChromePalettePurpleRim4, 0.96), (Skin.popupsPopupChromeChromePalettePurpleRim5, 1)],
                                               face: [(Skin.popupsPopupChromeChromePalettePurpleFace0, 0), (Skin.popupsPopupChromeChromePalettePurpleFace1, 0.07), (Skin.popupsPopupChromeChromePalettePurpleFace2, 0.1), (Skin.popupsPopupChromeChromePalettePurpleFace3, 0.3),
                                                      (Skin.popupsPopupChromeChromePalettePurpleFace4, 0.65), (Skin.popupsPopupChromeChromePalettePurpleFace5, 1)],
                                               edge: Skin.popupsPopupChromeChromePalettePurpleEdge, glare: Skin.popupsPopupChromeChromePalettePurpleGlare)
    /// Blue link buttons (Terms / Privacy: V2's settings skin, recoloured to v552's HUD blue; PENDING-ui).
    static let blue = PanelButtonStyleColors(outline: Skin.popupsPopupChromeChromePaletteBlueOutline, edgeDark: Skin.popupsPopupChromeChromePaletteBlueEdgeDark,
                                             rim: [(Skin.popupsPopupChromeChromePaletteBlueRim0, 0), (Skin.popupsPopupChromeChromePaletteBlueRim1, 0.55), (Skin.popupsPopupChromeChromePaletteBlueRim2, 0.84), (Skin.popupsPopupChromeChromePaletteBlueRim3, 0.9),
                                                   (Skin.popupsPopupChromeChromePaletteBlueRim4, 0.96), (Skin.popupsPopupChromeChromePaletteBlueRim5, 1)],
                                             face: [(Skin.popupsPopupChromeChromePaletteBlueFace0, 0), (Skin.popupsPopupChromeChromePaletteBlueFace1, 0.07), (Skin.popupsPopupChromeChromePaletteBlueFace2, 0.1), (Skin.popupsPopupChromeChromePaletteBlueFace3, 0.3),
                                                    (Skin.popupsPopupChromeChromePaletteBlueFace4, 0.65), (Skin.popupsPopupChromeChromePaletteBlueFace5, 1)],
                                             edge: Skin.popupsPopupChromeChromePaletteBlueEdge, glare: Skin.popupsPopupChromeChromePaletteBlueGlare)
}

struct ChromeButtonFace: View {
    var colors: PanelButtonStyleColors = .green
    var n: CGFloat = 4.6
    /// The face's side inset at the 89 pt reference height (PanelButton 7.67; the home Play face runs almost to its sides:
    /// grad.home.playButton / shot 026 → 4).
    var sideInset: CGFloat = 7.67

    var body: some View { Rasterized("face|\(colors.rasterID)|\(n)|\(sideInset)") { _ in art } }

    @ViewBuilder private var art: some View {
        GeometryReader { geo in
            let W = geo.size.width, H = geo.size.height
            let shape = Superellipse(n: n), face = Superellipse(n: n + 0.5)
            let grad = { (st: [(UInt32, Double)]) in
                LinearGradient(stops: st.map { .init(color: Color(hex: $0.0), location: $0.1) }, startPoint: .top, endPoint: .bottom)
            }
            // PanelButton's face inset on its 125 x 89 body is (7.67, 1, 7.67, 11) pt: it scales with the HEIGHT (the lip and
            // the rim keep their thickness on a wider button: Play 211 x 87, Quit 212 x 88 read the same as Resume).
            let u = H / 89
            let fx = sideInset * u, top = 1 * u, bottom = 11 * u
            ZStack(alignment: .topLeading) {
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
                        .padding(EdgeInsets(top: H * 0.06, leading: 1.33, bottom: H * 0.052, trailing: 1.33))
                        .mask(LinearGradient(stops: [.init(color: .white, location: 0), .init(color: .white.opacity(0.55), location: 0.22),
                                                     .init(color: .clear, location: 0.55)], startPoint: .top, endPoint: .bottom))
                }
                .frame(width: W - 2 * fx, height: H - top - bottom)
                .offset(x: fx, y: top)
            }
        }
        .accessibilityHidden(true)
    }
}
