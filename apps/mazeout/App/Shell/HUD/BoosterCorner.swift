import SwiftUI
import PathCore

// SHELL S2 (SPEC-ui §2.3.2; uim `booster.*`, VERIFIED 003). Two bottom corners, bottom-anchored and flush to the screen edges:
//   tray    0 · 753.3 · 82.7 · 81.1 (left) / 310.6 · 753.3 · 82.4 · 81.1 (right): the HUD's light-blue material (#BDDCFF face,
//           a dark #5F84C9 outline, a light inner rim #97BBF2 → #D3E7FD, a soft grey shadow), its outer corners off-screen
//   button  57.4 × 56.4 at (14.3, 764) / (321.6, 764): the green glossy face (se n 3.3) in a #648DD7 well
//   icon    left the icy hourglass `boosterFreeze` (34.4 × 38 drawn), right the bulb `boosterHint` (26 × 39)
//   badge   red ⌀24.5 at (53, 801.7) / (360.2, 801.7) with the count 16.9 pt (#FFFBF3 → #FFF2D9, outline #69000C 0.7);
//           stock 0 → a green "+" badge (tap → the booster info popup, GAME's BoosterDirector); `.active` keeps the look
//           (the badge already shows n − 1), `.locked` is never used on v552 (CONSISTENCY Y-1)
// A booster does not start the timer. The tap goes to GAME (`HUDActions.booster`); the press is the shared GameButton
// (scale 0.95 on touch-down, click + haptic on release). The file is named after the SPEC-architecture tree; the views are
// `BoosterCornerView` (GlossyChrome reserves `BoosterButton` / `CountBadge`).
// Template phase 5: any declared booster. Its icon is the art slot `BoosterSpec.icon` or `booster.<id>.icon` (the reference's
// hourglass and bulb are exactly those slots); a module booster whose slot has no art in the skin shows its NAME on the green
// face instead (the name's string key from the module's data; no stand-in art), and it is the corner's accessibility label.

struct BoosterCornerView: View, Equatable {
    enum Side { case left, right }
    let slot: BoosterSlotVM
    let side: Side
    let t: Tokens
    let m: ShellMetrics
    let action: (BoosterID) -> Void

    static func == (a: BoosterCornerView, b: BoosterCornerView) -> Bool { a.slot == b.slot && a.side == b.side && a.m == b.m }

    var body: some View {
        let left = side == .left
        let tray = t.rect(left ? "booster.trayLeft" : "booster.trayRight",
                          left ? CGRect(0, 753.3, 82.7, 81.1) : CGRect(310.6, 753.3, 82.4, 81.1), .bottom, m)
        let button = t.rect(left ? "booster.buttonLeft" : "booster.buttonRight",
                            left ? CGRect(14.3, 764.0, 57.4, 56.4) : CGRect(321.6, 764.0, 57.4, 56.4), .bottom, m)
        let icon = t.rect(left ? "booster.iconLeft" : "booster.iconRight",
                          left ? CGRect(25.7, 773.3, 34.4, 38.0) : CGRect(337.3, 773.0, 26.0, 39.0), .bottom, m)
        let badge = t.rect(left ? "booster.badgeLeft" : "booster.badgeRight",
                           left ? CGRect(53.0, 801.7, 24.7, 24.4) : CGRect(360.2, 801.7, 24.7, 24.4), .bottom, m)
        let art = BoosterArt.icon(slot)
        ZStack(alignment: .topLeading) {
            Rasterized("boosterTray|\(left)", overflow: 3) { _ in BoosterTray(left: left, t: t) }
                .placed(tray)
            GameButton(id: "hud.booster.\(slot.id.rawValue)", label: BoosterArt.label(slot),
                       value: slot.state.accessibilityValue, enabled: slot.state != .locked, action: { action(slot.id) }) {
                ZStack(alignment: .topLeading) {
                    Rasterized("boosterWell", overflow: 3) { _ in BoosterWell(t: t) }
                        .frame(width: button.width, height: button.height)
                    if let art {
                        InkImage(art: art, ink: icon.offsetBy(dx: -button.minX, dy: -button.minY))
                    } else {
                        nameFace(CGRect(x: 0, y: 0, width: button.width, height: button.height))
                    }
                    badgeView(badge.offsetBy(dx: -button.minX, dy: -button.minY))
                }
                .frame(width: button.width, height: button.height, alignment: .topLeading)
            }
            .placed(button)
            .anchor(.booster(slot.id))
        }
    }

    /// No art for the booster's slot: its name on the green face (the badge count's text style, shrunk to the face).
    private func nameFace(_ face: CGRect) -> some View {
        let style = t.text("booster.badge.count", .s2(16.9, 0, [Skin.hudBoosterCornerBoosterBadgeCount0, Skin.hudBoosterCornerBoosterBadgeCount1, Skin.hudBoosterCornerBoosterBadgeCount2], outline: Skin.hudBoosterCornerBoosterBadgeCountOutline, 0.71, drop: 0.56))
            .sized(CGFloat(t.number("modules.booster.labelSize", 15)) * m.s)
        return GameText(BoosterArt.label(slot), style: style,
                        maxWidth: face.width - CGFloat(t.number("modules.booster.labelInset", 8)) * m.s)
            .at(face.midX, style.capCentre(baseline: face.midY + style.size * 0.36))
    }

    @ViewBuilder private func badgeView(_ r: CGRect) -> some View {
        switch slot.state {
        case .stock(let n):
            let style = t.text("booster.badge.count", .s2(16.9, 0, [Skin.hudBoosterCornerBoosterBadgeCount0, Skin.hudBoosterCornerBoosterBadgeCount1, Skin.hudBoosterCornerBoosterBadgeCount2], outline: Skin.hudBoosterCornerBoosterBadgeCountOutline, 0.71, drop: 0.56))
                .sized(16.9 * m.s)
            ZStack {
                Rasterized("boosterBadge", overflow: 2) { _ in RedBadge(t: t) }
                GameText(verbatim: n > 99 ? "99+" : "\(n)", style: style, maxWidth: r.width - 4)
                    .position(x: r.width / 2 + 0.2 * m.s, y: style.capCentre(baseline: r.height * 18.1 / 24.4))
            }
            .placed(r)
        case .active:
            EmptyView()
        case .empty, .locked:
            ArtImage(art: .hudPlusBadge).placed(r.insetBy(dx: -1.5, dy: -1.5))
        }
    }
}

/// The tray (VERIFIED xsec.booster.trayLeft, 003): its outer corners run off-screen; a dark #5F84C9 outline, a darker side rim
/// #97BBF2 (≈ 3.4 pt), a bright top edge, the face #BDDCFF, a 4.7 pt lower lip #517CC9 → #87ACEC, a soft grey shadow below.
private struct BoosterTray: View {
    let left: Bool
    let t: Tokens

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            let r = CGFloat(t.radius("booster.tray", 24))
            let off: CGFloat = 40                         // the part beyond the screen edge
            let x = left ? -off : 0
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: r, style: .continuous).fill(t.color("booster.trayShadow", Skin.hudBoosterCornerBoosterTrayShadow).opacity(0.4))
                    .frame(width: w + off, height: h).offset(x: x, y: 2.6).blur(radius: 1.4)
                RoundedRectangle(cornerRadius: r, style: .continuous).fill(t.color("booster.trayOutline", Skin.hudBoosterCornerBoosterTrayOutline))
                    .frame(width: w + off, height: h).offset(x: x)
                RoundedRectangle(cornerRadius: r - 0.6, style: .continuous)
                    .fill(LinearGradient(stops: [.init(color: Color(hex: Skin.hudBoosterCornerBoosterTrayStops0), location: 0), .init(color: t.color("booster.trayRim", Skin.hudBoosterCornerBoosterTrayRim), location: 0.08),
                                                 .init(color: Color(hex: Skin.hudBoosterCornerBoosterTrayStops2), location: 0.9), .init(color: Color(hex: Skin.hudBoosterCornerBoosterTrayStops3), location: 1)],
                                         startPoint: .top, endPoint: .bottom))
                    .frame(width: w + off - 1.2, height: h - 1.2).offset(x: x + 0.6, y: 0.6)
                RoundedRectangle(cornerRadius: max(1, r - 3.4), style: .continuous)
                    .fill(LinearGradient(stops: t.stops("booster.trayFace", [(0, Skin.hudBoosterCornerBoosterTrayFace0), (0.012, Skin.hudBoosterCornerBoosterTrayFace1), (0.025, Skin.hudBoosterCornerBoosterTrayFace2), (0.045, Skin.hudBoosterCornerBoosterTrayFace3),
                                                                             (0.935, Skin.hudBoosterCornerBoosterTrayFace4), (0.945, Skin.hudBoosterCornerBoosterTrayFace5), (0.97, Skin.hudBoosterCornerBoosterTrayFace6), (1, Skin.hudBoosterCornerBoosterTrayFace7)]),
                                         startPoint: .top, endPoint: .bottom))
                    .frame(width: w + off - 6.8, height: h - 1.2).offset(x: x + 3.4, y: 0.6)
            }
            .frame(width: w, height: h, alignment: .topLeading)
            .clipped()
        }
    }
}

/// The green booster face (VERIFIED 003 columns): the measured frame is its dark outline #0B3B03; outside it a ≈ 2.3 pt #648DD7
/// well; inside a rim darkening outwards (≈ 3.4 pt at the sides), the face #12E912 → #04CD04 with a light glare line near the
/// top, and a ≈ 4.8 pt darker lower lip.
private struct BoosterWell: View {
    let t: Tokens
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            let n = t.superellipseN("booster.button", 3.3)
            let shape = Superellipse(n: n)
            // VERIFIED 003 at y 790 / x 43: a light edge, the #648DD7 well ~2 pt outside the token frame, the #0C3A00 outline ON
            // the frame (14.3 / 764.0), a green rim ~3.3 pt at the sides, the face's highlight ~2.6 pt under the top. Every layer
            // carries an explicit size: an unframed shape would take the ZStack's size (the well's) and grow the button 2.7 pt.
            ZStack {
                shape.fill(t.color("booster.wellEdge", Skin.hudBoosterCornerBoosterWellEdge)).frame(width: w + 5.2, height: h + 5.2)
                shape.fill(t.color("booster.well", Skin.hudBoosterCornerBoosterWell)).frame(width: w + 4.0, height: h + 4.0)
                shape.fill(t.color("booster.outline", Skin.hudBoosterCornerBoosterOutline)).frame(width: w, height: h)
                shape.fill(LinearGradient(colors: t.colors("booster.rim", [Skin.hudBoosterCornerBoosterRim0, Skin.hudBoosterCornerBoosterRim1, Skin.hudBoosterCornerBoosterRim2]), startPoint: .top, endPoint: .bottom))
                    .padding(1.0)
                    .frame(width: w, height: h)
                Superellipse(n: n + 0.3)
                    .fill(LinearGradient(stops: t.stops("booster.face", [(0, Skin.hudBoosterCornerBoosterFace0), (0.035, Skin.hudBoosterCornerBoosterFace1), (0.075, Skin.hudBoosterCornerBoosterFace2), (0.6, Skin.hudBoosterCornerBoosterFace3),
                                                                         (1, Skin.hudBoosterCornerBoosterFace4)]),
                                         startPoint: .top, endPoint: .bottom))
                    .padding(EdgeInsets(top: 2.4, leading: 4.4, bottom: 5.8, trailing: 4.4))
                    .blur(radius: 0.5)
                    .frame(width: w, height: h)
            }
            .frame(width: w, height: h)
        }
    }
}

/// The red stock badge (#FF4344, a thin light ring and a dark-red outline).
private struct RedBadge: View {
    let t: Tokens
    var body: some View {
        ZStack {
            Circle().fill(t.color("booster.badgeOutline", Skin.hudBoosterCornerBoosterBadgeOutline))
            Circle().fill(RadialGradient(colors: t.colors("booster.badge", [Skin.hudBoosterCornerBoosterBadge0, Skin.hudBoosterCornerBoosterBadge1, Skin.hudBoosterCornerBoosterBadge2]),
                                         center: UnitPoint(x: 0.45, y: 0.35), startRadius: 0, endRadius: 12))
                .padding(1.2)
        }
    }
}

/// Template phase 5: a booster's art slot and name, for any declared booster.
enum BoosterArt {
    /// `BoosterSpec.icon`, else `booster.<id>.icon`; nil when the skin maps no art to it (the reference's freeze / hint map
    /// their hourglass and bulb).
    static func icon(_ slot: BoosterSlotVM) -> UIArt? { icon(id: slot.id, slot: slot.icon) }

    static func icon(id: BoosterID, slot: String?) -> UIArt? { UIArt(rawValue: slot ?? ("booster." + id.rawValue + ".icon")) }

    /// The corner's label: the reference's "Time Freeze" / "Hint", a module booster's name (its string key), else its id.
    static func label(_ slot: BoosterSlotVM) -> LocalizedStringResource {
        if slot.id == .freeze { return "Time Freeze" }
        if slot.id == .hint { return "Hint" }
        return LocalizedStringResource(String.LocalizationValue(slot.nameKey ?? slot.id.rawValue))
    }
}
