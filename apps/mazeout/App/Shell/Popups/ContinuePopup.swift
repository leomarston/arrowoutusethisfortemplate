import SwiftUI
import PathCore

// SHELL S2 (SPEC-ui §2.6.3-§2.6.4, §1.6.7, §1.6.17; uim `continueStreak.*`, `continueLife.*`, tok2 `continueToken.*`; VERIFIED 014 /
// 015 / meta-070 / meta-071 / meta-089 / 113). "Continue?" — the full-width band popup of the Quit Level? family (S1's
// BandPopupFrame 0 · 233.2 · 393 · 404.8, cream strip 313.3-470), the ribbon "Continue?" (49 shrunk to the 228 box → 46.6), the X at
// (362.5, 237.4), the coin group 12.7 · 96.1 · 105.1 · 41.4 at the top left, and the framed green "Play On" + coin + price
// (79.7 · 498.4 · 233.9 · 88.1). The cream strip carries the step's warning (`ContinueOffer.warning`, rules.json failChain):
//   streak  "You will lose your streak!" (22.9 / −0.34 #622100) + the cream chips x1 … x100 with the current multiplier lit
//   token   (the Claw Challenge runs, multiplier > x1) the hex token + "You will lose **N** tokens" / "and your streak!" (21 pt, N
//           red #DE0002) + the blue chevron chips with the current one orange-gold
//   life    "You will lose a life!" (26.1 / −1.59) over the broken heart
// A `.none` warning is the chain's first step: Out of Time! / Out of Lives! (OutOfTimePopup; CONSISTENCY ID-11 hearts-out).
// Answers: Play On → `pay()` → .primary when paid (else it stays); X → .close. Appears complete in one frame.

struct ContinuePopup: View {
    enum Variant: String { case streak, token, life, time, hearts }

    let offer: ContinueOffer
    let pay: PayAction
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m
    @State private var paying = false

    /// `-pc.popup continue:<variant>` forces the layout (capture of a state the player's data would not show).
    @MainActor static var forced: Variant?

    @MainActor static func variant(_ offer: ContinueOffer, app: AppModel) -> Variant {
        if let forced { return forced }
        return variant(offer, clawRunning: offer.warning == .token && clawRunning(app))
    }

    /// The layout of an offer (rules.json failChain `warning`; the token step shows the streak layout while the Claw is not running).
    static func variant(_ offer: ContinueOffer, clawRunning: Bool) -> Variant {
        switch offer.warning {
        case .none: return offer.kind == .outOfHearts ? .hearts : .time
        case .life: return .life
        case .streak: return .streak
        case .token: return clawRunning ? .token : .streak
        }
    }

    /// The Claw Challenge runs from its unlock (social.json `unlocks.clawChallenge`, L33) and the multiplier is above x1.
    @MainActor static func clawRunning(_ app: AppModel) -> Bool {
        let s = app.store.state
        return s.level >= app.tuning.social.file.int("unlocks.clawChallenge", 33) && s.events.streakStep > 0
    }

    var body: some View {
        let v = Self.variant(offer, app: app)
        switch v {
        case .time, .hearts:
            OutOfTimePopup(offer: ContinueOffer(kind: v == .hearts ? .outOfHearts : .outOfTime, step: offer.step, price: offer.price,
                                                grant: offer.grant, warning: offer.warning, isLast: offer.isLast),
                           pay: pay, answer: answer, popupID: "continue")
        case .streak, .token, .life:
            band(v)
        }
    }

    @ViewBuilder private func band(_ v: Variant) -> some View {
        let t = app.tuning.ui.tokens
        let key = v == .life ? "continueLife" : "continueStreak"
        let steps = StreakStripSource.steps(app)
        let step = max(0, min(steps.count - 1, app.store.state.events.streakStep))
        // a full-width band stretches edge to edge on phones wider than the 393 pt canvas (SPEC-ui §1.1; S1's Quit Level? rule)
        let extra = max(0, (m.size.width / max(m.popupScale, 0.01) - 393) / 2)
        ZStack(alignment: .topLeading) {
            BandPopupFrame(t: t, creamTop: 80.1, creamBottom: 236.8)
                .placed(t.frame("continue.band", CGRect(0, 233.2, 393, 404.8)).insetBy(dx: -extra, dy: 0))
            switch v {
            case .life:
                TokenText(id: "continueLife.message.msg", source: .copy("You will lose a life!"), style: .s2(26.1, -1.59, [0x5A2801]),
                          baseline: 346.0, centreX: 196.2, maxWidth: 340)
                InkImage(art: .heartBroken, ink: t.frame("continueLife.brokenHeart", CGRect(132.65, 359.25, 128.6, 101.8)))
            case .token:
                InkImage(art: .treasureToken, ink: t.frame("continueToken.token", CGRect(50.0, 322.0, 55.0, 53.0)))
                TokenLine(multiplier: steps[step], t: t)
                TokenText(id: "continueToken.texts.l2", source: .copy("and your streak!"), style: .s2(21.1, -0.34, [0x5A2801]),
                          baseline: 369.1, centreX: 222.5, maxWidth: 235)
                ChevronChipRow(steps: steps, lit: step, frame: t.frame("continueToken.chips", CGRect(30.0, 390.3, 343.6, 53.4)), t: t)
            default:
                TokenText(id: "continueStreak.message.msg", source: .copy("You will lose your streak!"), style: .s2(22.9, -0.54, [0x5A2801]),
                          baseline: 347.7, centreX: 196.2, maxWidth: 340)
                StreakChipRow(steps: steps, lit: Double(step), ring: 1,
                              frame: t.frame("continueStreak.chips", CGRect(8.0, 372.0, 376.7, 66.4)), t: t, onCream: true)
            }
            PriceButton(id: "popup.continue.primary", label: "Play On", price: offer.price,
                        // one face for every variant: 015 (life) measures pixel-identical to 014 (streak) — green 88.7 · 499.8 ·
                        // 215.8 · 76.4 on both — so uim's continueLife.playOn (80.7 · 500.4 · 231.9 · 85.1) is not used
                        face: t.frame("continueStreak.playOn", CGRect(79.7, 498.4, 233.9, 88.1)),
                        well: t.frame(key + ".playOnFrame", CGRect(68.4, 489.7, 256.5, 105.5)),
                        n: t.superellipseN("continueStreak.playOn", 5.0),
                        labelID: key + ".playOn.label",
                        labelStyle: .s2(31.0, 0.4, [0xFFFBF1, 0xFFF7E5, 0xFDF3DF], outline: 0x924500, 2.16, drop: 0.73),
                        labelAt: (147.5, 550.3),
                        priceID: key + ".playOn.price",
                        priceStyle: .s2(31.6, 0.71, [0xFFFBF3, 0xFFF7E6, 0xFDF3DF], outline: 0x924500, 2.07, drop: 0.92),
                        priceAt: (273.6, 551.1),
                        coin: t.frame(key + ".playOnCoin", CGRect(213.0, 529.2, 26.5, 26.5))) { buy() }
            PopupTitle(title: "Continue?", frame: t.frame("continueStreak.ribbon", CGRect(60.1, 193.5, 274.2, 90.4)), t: t,
                       baselineFromTop: CGFloat(t.number("text.continue.title.baseline", 254.7)) - 193.5)
            PopupCloseButton(id: "popup.continue.close", t: t) { answer(PopupResult.close) }
                .placed(t.frame("continueStreak.closeDisc", CGRect(340.0, 214.9, 45, 45)))
            OfferCoinGroup(frame: t.frame("continueStreak.coinGroup", CGRect(12.7, 96.1, 105.1, 41.4)), coins: app.store.state.coins,
                           textID: "continueStreak.coinGroup.digits")
        }
    }

    private func buy() {
        guard !paying else { return }
        paying = true
        Task { @MainActor in
            let paid = await pay()
            paying = false
            Log.mark("popup", "continue pay → \(paid ? "paid" : "not paid")")
            if paid { answer(PopupResult.primary) }
        }
    }
}

/// "You will lose **N** tokens" (ruling 52(e) EN grammar) — one line of runs, the number red (#DE0002), centred at the measured centre-x.
private struct TokenLine: View {
    let multiplier: Int
    let t: Tokens

    var body: some View {
        let style = t.text("continueToken.texts.l1", .s2(21.0, -0.29, [0x5A2801]))
        let p = t.textPoint("continueToken.texts.l1", baseline: 343.4, centreX: 223.7)
        let full = String(localized: "You will lose \(multiplier) tokens")
        RunsText(text: full, highlight: "\(multiplier)", highlightColor: t.color("continueToken.red", 0xD12D1C), style: style,
                 maxWidth: t.textMaxWidth("continueToken.texts.l1", 245))
            .at(p.x, style.capCentre(baseline: p.baseline))
            .accessibilityIdentifier("continueToken.texts.l1")
    }
}

/// A single line drawn as runs: the first occurrence of `highlight` in `text` in another face colour (the red token count, the
/// blue CAPS word of the unlock cards). Shrinks to `maxWidth` as one unit (min scale of the style).
struct RunsText: View {
    let text: String
    let highlight: String
    let highlightColor: Color
    let style: GameTextStyle
    var maxWidth: CGFloat? = nil

    var body: some View {
        let whole = GameTextLayout.make(text, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking,
                                        maxWidth: maxWidth, minScale: style.minScale)
        let st = whole.fontSize == style.size ? style : style.sized(whole.fontSize)
        let parts = Self.split(text, highlight)
        let layouts = parts.map { GameTextLayout.make($0.0, postScriptName: st.postScriptName, size: st.size, tracking: st.tracking) }
        // GameTextLayout drops trailing whitespace from the advance: add it back per run (the space's advance + tracking)
        let space = GameTextLayout.make("x x", postScriptName: st.postScriptName, size: st.size, tracking: st.tracking).advance
            - GameTextLayout.make("xx", postScriptName: st.postScriptName, size: st.size, tracking: st.tracking).advance
        let widths = layouts.map { l -> CGFloat in
            let trailing = CGFloat(l.text.reversed().prefix { $0 == " " }.count)
            return l.text.isEmpty ? 0 : l.advance + st.tracking + trailing * space
        }
        let total = widths.reduce(0, +) - st.tracking
        ZStack(alignment: .topLeading) {
            ForEach(Array(parts.enumerated()), id: \.offset) { i, part in
                if !part.0.isEmpty {
                    GameText(verbatim: part.0, style: runStyle(st, part.1))
                        .position(x: widths.prefix(i).reduce(0, +) + layouts[i].advance / 2, y: 1)
                }
            }
        }
        .frame(width: max(1, total), height: 2, alignment: .topLeading)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(verbatim: text))
    }

    private func runStyle(_ st: GameTextStyle, _ highlighted: Bool) -> GameTextStyle {
        var s = st
        if highlighted { s.fill = [highlightColor] }
        return s
    }

    /// [(run, highlighted)] with the leading/trailing spaces kept on the plain runs.
    static func split(_ text: String, _ highlight: String) -> [(String, Bool)] {
        guard !highlight.isEmpty, let r = text.range(of: highlight) else { return [(text, false)] }
        return [(String(text[..<r.lowerBound]), false), (String(text[r]), true), (String(text[r.upperBound...]), false)]
    }
}

/// The blue chevron chips on a dark track (SPEC-ui §1.6.17, VERIFIED meta-070): x1 x5 x10 x25 x100, the lit one orange-gold.
struct ChevronChipRow: View {
    let steps: [Int]
    let lit: Int
    let frame: CGRect
    let t: Tokens

    var body: some View {
        let k = frame.height / 53.4
        // VERIFIED meta-070 (y 404-426 / 428): label centres 65.0 · 133.9 · 199.0 · 261.5 · 329.6; the chip bodies 67 pt wide
        // (faces 52.7 at y 428) centred at 67.6 · 133.2 · 197.5 · 262.3 · 327.2; the lit one 84 wide, 1.7 pt left of its slot
        // (its face 294.6 … 361 at y 428)
        let centres = t.list("continueToken.chipCentres", [65.0, 133.9, 199.0, 261.5, 329.6]).map { (CGFloat($0) - frame.minX) }
        let bodies = t.list("continueToken.chipBodies", [67.6, 133.2, 197.5, 262.3, 327.2]).map { (CGFloat($0) - frame.minX) }
        let plain = t.text("continueToken.chips.x1", .s2(22.3, -1.67, [0xFFFFFF], outline: 0x00383C, 1.5, drop: 0.74)).sized(22.3 * k)
        let lightStyle = t.text("continueToken.chips.x100", .s2(22.6, -0.08, [0xFFFFFF], outline: 0x7D0C02, 1.6, drop: 0.71)).sized(22.6 * k)
        let base = frame.height * 32.3 / 53.4
        ZStack(alignment: .topLeading) {
            // the navy track ends under the last chip's body (VERIFIED meta-070: with x100 lit it never shows past the gold chip)
            let lastLit = lit == min(steps.count, centres.count) - 1
            // the track: a pale hairline, navy, 30.7 · 393.3 … 439.3 (VERIFIED meta-070 at y 416 / x 98)
            Rasterized("chevTrack|\(lastLit)", overflow: 1) { _ in
                ZStack {
                    RoundedRectangle(cornerRadius: 9, style: .continuous).fill(Color(hex: 0xD0E3DB))
                    RoundedRectangle(cornerRadius: 8.4, style: .continuous).fill(t.color("continueToken.track", 0x002B2E)).padding(0.6)
                }
            }
            .frame(width: frame.width - (lastLit ? 29 : 7) * k, height: frame.height - 7.4 * k).offset(x: 0.1 * k, y: 2.4 * k)
            ForEach(0..<min(steps.count, centres.count), id: \.self) { i in
                if i != lit {
                    Chevron(lit: false, notched: i > 0).frame(width: 67 * k, height: 43 * k).position(x: bodies[min(i, bodies.count - 1)], y: frame.height / 2)
                    GameText(verbatim: "x\(steps[i])", style: plain, maxWidth: 56 * k).at(centres[i], plain.capCentre(baseline: base))
                }
            }
            if lit < min(steps.count, centres.count) {
                Chevron(lit: true, notched: lit > 0).frame(width: 84 * k, height: 53.4 * k).position(x: bodies[min(lit, bodies.count - 1)] - 1.7 * k, y: frame.height / 2)
                GameText(verbatim: "x\(steps[lit])", style: lightStyle, maxWidth: 64 * k).at(centres[lit], lightStyle.capCentre(baseline: base))
            }
        }
        .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        .placed(frame)
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("continueToken.chips")
        .accessibilityValue(Text(verbatim: "x\(steps[max(0, min(steps.count - 1, lit))])"))
    }
}

/// One chevron chip: a rounded body pointing right, the left edge notched (the first chip's left edge is flat, VERIFIED
/// meta-070). The lit chip has a thick orange rim with a darker 3D base and a soft shadow.
private struct Chevron: View {
    let lit: Bool
    var notched = true
    var body: some View {
        Rasterized("chevron|\(lit)|\(notched)", overflow: 3) { _ in
            ZStack {
                if lit {
                    ChevronShape(notched: notched).fill(Color.black.opacity(0.35)).blur(radius: 1.4).offset(y: 1.2)
                }
                ChevronShape(notched: notched)
                    .fill(LinearGradient(colors: lit ? [Color(hex: 0xF58A10), Color(hex: 0xE06A00), Color(hex: 0xB04E00)]
                                                     : [Color(hex: 0x00454D), Color(hex: 0x00454D)],
                                         startPoint: .top, endPoint: .bottom))
                ChevronShape(notched: notched)
                    .fill(LinearGradient(colors: lit ? [Color(hex: 0xFFE84A), Color(hex: 0xFED902), Color(hex: 0xFFB700)]
                                                     : [Color(hex: 0x45BEAF), Color(hex: 0x29AD9E), Color(hex: 0x009C8F)],
                                         startPoint: .top, endPoint: .bottom))
                    .padding(lit ? EdgeInsets(top: 2.6, leading: 3.4, bottom: 4.6, trailing: 3.8)
                                 : EdgeInsets(top: 1.6, leading: 2.2, bottom: 3.2, trailing: 2.6))
            }
        }
    }
}

private struct ChevronShape: Shape {
    var notched = true
    func path(in r: CGRect) -> Path {
        let tip = r.height * 0.36, notch = r.height * 0.22
        var p = Path()
        p.move(to: CGPoint(x: r.minX + 4, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX - tip, y: r.minY))
        p.addQuadCurve(to: CGPoint(x: r.maxX - tip + 5, y: r.minY + 4), control: CGPoint(x: r.maxX - tip + 3, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX - 1, y: r.midY - 3))
        p.addQuadCurve(to: CGPoint(x: r.maxX - 1, y: r.midY + 3), control: CGPoint(x: r.maxX + 1.5, y: r.midY))
        p.addLine(to: CGPoint(x: r.maxX - tip + 5, y: r.maxY - 4))
        p.addQuadCurve(to: CGPoint(x: r.maxX - tip, y: r.maxY), control: CGPoint(x: r.maxX - tip + 3, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX + 4, y: r.maxY))
        p.addQuadCurve(to: CGPoint(x: r.minX + 1, y: r.maxY - 4), control: CGPoint(x: r.minX, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX + (notched ? notch : 0), y: r.midY))
        p.addLine(to: CGPoint(x: r.minX + 1, y: r.minY + 4))
        p.addQuadCurve(to: CGPoint(x: r.minX + 4, y: r.minY), control: CGPoint(x: r.minX, y: r.minY))
        p.closeSubpath()
        return p
    }
}
