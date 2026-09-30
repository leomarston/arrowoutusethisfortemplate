import SwiftUI
import PathCore

// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §8c). The first step of a fail chain whose kind has no measured popup of
// its own: every `ContinueOffer.Kind` but Out of Time! / Out of Lives! (which stay OutOfTimePopup, unchanged). One generic
// popup driven by the offer: the kind chooses the title, the one-line body, the button and the prop's art slot; the grant
// chooses the grant line ("+1 Tube", "+5 Moves"; a module words its own actions through `PuzzlePlugin.grantText`). It is the
// Out of Time! layout — the dim, the blue glow, the title, the prop, the grant, the framed green button + coin + price, the X,
// the coin group — with the same ui.json frames and text styles (`outOfTime.*`), so a reskin tunes both at once. The prop is
// the OPTIONAL art slot `popup.<kind>.icon` (skin/art.json maps it when the skin has the art); without art the body text takes
// the prop's place (no stand-in art). Answers as OutOfTimePopup: the button → `pay()` → .primary when paid; X → .close.

/// The texts of a continue offer, chosen by its kind and its grant.
struct OfferTexts {
    var title: LocalizedStringResource
    /// The line in the prop's place (nil = none: the reference kinds).
    var body: LocalizedStringResource?
    var button: LocalizedStringResource
    /// "+1 Tube", "+5 Moves", "+30 sec"; nil = no grant line (`.none`).
    var grant: LocalizedStringResource?
    /// The prop's art slot (`popup.<kind>.icon`; optional in the skin).
    var iconSlot: String

    @MainActor static func of(_ offer: ContinueOffer, puzzle: (any PuzzlePlugin)?) -> OfferTexts {
        let grant = grantLine(offer.grant, puzzle: puzzle)
        let slot = "popup." + offer.kind.rawValue + ".icon"
        switch offer.kind {
        case .outOfTime:
            return OfferTexts(title: LocalizedStringResource("Out of Time!"), body: nil,
                              button: LocalizedStringResource("Add Time"), grant: grant, iconSlot: slot)
        case .outOfHearts:
            return OfferTexts(title: LocalizedStringResource("Out of Lives!"), body: nil,
                              button: LocalizedStringResource("Add Lives"), grant: grant, iconSlot: slot)
        case .outOfMoves:
            return OfferTexts(title: LocalizedStringResource("Out of Moves!"),
                              body: LocalizedStringResource("Keep going with a few more moves!"),
                              button: LocalizedStringResource("Add Moves"), grant: grant, iconSlot: slot)
        case .stuck:
            return OfferTexts(title: LocalizedStringResource("No Moves Left!"),
                              body: LocalizedStringResource("You are stuck! Keep going with a little help."),
                              button: LocalizedStringResource("Play On"), grant: grant, iconSlot: slot)
        }
    }

    /// The grant line: the module's own wording of its grant first, else the shell's.
    @MainActor static func grantLine(_ g: ContinueOffer.Grant, puzzle: (any PuzzlePlugin)?) -> LocalizedStringResource? {
        if let text = puzzle?.grantText(g) { return text }
        switch g {
        case .addTime(let n): return n == 30 ? LocalizedStringResource("+30 sec") : LocalizedStringResource("+\(n) sec")
        case .refillHearts(let n): return n == 3 ? LocalizedStringResource("+3 Lives") : LocalizedStringResource("+\(n)")
        case .addMoves(let n): return n == 1 ? LocalizedStringResource("+1 Move") : LocalizedStringResource("+\(n) Moves")
        case .puzzleAction(_, let n): return LocalizedStringResource("+\(n)")
        case .none: return nil
        }
    }
}

struct OfferPopup: View {
    let offer: ContinueOffer
    let pay: PayAction
    let answer: PopupAnswer
    /// The container id's suffix: "outOfTime" (PopupRequest.outOfTime) or "continue" (a continueOffer with no warning).
    var popupID = "outOfTime"
    @Environment(AppModel.self) private var app
    @State private var paying = false

    /// The kinds this popup serves: every kind without its own measured popup.
    static func handles(_ kind: ContinueOffer.Kind) -> Bool { kind != .outOfTime && kind != .outOfHearts }

    var body: some View {
        let t = app.tuning.ui.tokens
        let texts = OfferTexts.of(offer, puzzle: app.puzzle)
        let kind = offer.kind.rawValue
        let icon = UIArt(rawValue: texts.iconSlot)
        let prop = t.frame("outOfTime.stopwatch", CGRect(91.7, 273.6, 208.2, 220.9))
        let grantStyle = GameTextStyle.s2(61.0, -0.75, [Skin.popupsOutOfTimePopupOutOfTimePopupStyle0V2], outline: Skin.popupsOutOfTimePopupOutOfTimePopupOutlineNotHearts,
                                          2.1, drop: 2.62)
        ZStack(alignment: .topLeading) {
            OfferGlow(hearts: false, t: t)
                .placed(t.frame("outOfTime.glow", CGRect(26, 214, 340, 340)))
                .allowsHitTesting(false)
            OfferLine(styleID: "outOfTime.title", id: "offer.\(kind).title", source: .copy(texts.title),
                      style: .s2(51.6, -1.04, [Skin.popupsOutOfTimePopupOutOfTimePopupStyle0, Skin.popupsOutOfTimePopupOutOfTimePopupStyle1, Skin.popupsOutOfTimePopupOutOfTimePopupStyle2], outline: Skin.popupsOutOfTimePopupOutOfTimePopupOutline, 1.5,
                                 drop: 5.2, dropColor: Skin.popupsOutOfTimePopupOutOfTimePopupDropColor),
                      baseline: 215.2, centreX: 196.7, maxWidth: 345, rings: [(Skin.popupsOutOfTimePopupOutOfTimePopupRings0, 5.8)],
                      ringDY: 1.4, innerDY: 2.4)
            if let icon {
                InkImage(art: icon, ink: prop)
            } else if let line = texts.body {
                OfferBody(text: String(localized: line), frame: prop, id: "offer.\(kind).body", style: grantStyle, t: t)
            }
            if let grant = texts.grant {
                OfferLine(styleID: "outOfTime.grant", id: "offer.\(kind).grant", source: .copy(grant), style: grantStyle,
                          baseline: 554.7, centreX: 197.5, maxWidth: 345)
            }
            PriceButton(id: "popup.\(popupID).primary", label: texts.button, price: offer.price,
                        face: t.frame("outOfTime.addTimeFace", CGRect(79.7, 632.9, 233.9, 88.1)),
                        well: t.frame("outOfTime.addTime", CGRect(71.7, 627.5, 249.9, 104.1)),
                        n: t.superellipseN("outOfTime.button", 5.1),
                        labelID: "outOfTime.button.label",
                        labelStyle: .s2(23.1, 0.22, [Skin.popupsOutOfTimePopupOutOfTimePopupLabelStyle0, Skin.popupsOutOfTimePopupOutOfTimePopupLabelStyle1, Skin.popupsOutOfTimePopupOutOfTimePopupLabelStyle2], outline: Skin.popupsOutOfTimePopupOutOfTimePopupOutlineV2, 1.17, drop: 1.05),
                        labelAt: (156.0, 684.3),
                        priceID: "outOfTime.button.price",
                        priceStyle: .s2(26.2, 0.52, [Skin.popupsOutOfTimePopupOutOfTimePopupPriceStyle0, Skin.popupsOutOfTimePopupOutOfTimePopupPriceStyle1, Skin.popupsOutOfTimePopupOutOfTimePopupPriceStyle2], outline: Skin.popupsOutOfTimePopupOutOfTimePopupOutlineV2, 1.62, drop: 0.86),
                        priceAt: (267.6, 685.9),
                        coin: t.frame("outOfTime.button.coin", CGRect(216.2, 666.3, 25.8, 25.8)),
                        wellInset: OfferWell.tightInset) { buy() }
            OfferCoinGroup(frame: t.frame("outOfTime.coinGroup", CGRect(12.7, 62.4, 108.4, 44.4)), coins: app.store.state.coins,
                           textID: "outOfTime.coinGroup.digits")
            PopupCloseButton(id: "popup.\(popupID).close", t: t) { answer(PopupResult.close) }
                .placed(t.frame("outOfTime.closeDisc", CGRect(327.5, 53.0, 45, 45)))
        }
    }

    private func buy() {
        guard !paying else { return }
        paying = true
        Task { @MainActor in
            let paid = await pay()
            paying = false
            Log.mark("popup", "offer \(offer.kind.rawValue) pay → \(paid ? "paid" : "not paid")")
            if paid { answer(PopupResult.primary) }
        }
    }
}

/// A line placed by another popup's ui.json text style (`styleID`: size, fill, rings, baseline, centre) under its own
/// accessibility id (TokenText uses one id for both).
private struct OfferLine: View {
    let styleID: String
    let id: String
    let source: TextSource
    let style: GameTextStyle
    let baseline: CGFloat
    let centreX: CGFloat
    var maxWidth: CGFloat? = nil
    var rings: [(UInt32, CGFloat)] = []
    var ringDY: CGFloat = 0
    var innerDY: CGFloat = 0
    @Environment(AppModel.self) private var app

    var body: some View {
        let t = app.tuning.ui.tokens
        let st = t.text(styleID, style)
        let p = t.textPoint(styleID, baseline: baseline, centreX: centreX)
        RingedText(source: source, style: st, rings: t.rings(styleID, rings), maxWidth: t.textMaxWidth(styleID, maxWidth),
                   ringDY: ringDY == 0 ? 0 : CGFloat(t.number("text.\(styleID).ringDY", Double(ringDY))),
                   innerDY: innerDY == 0 ? 0 : CGFloat(t.number("text.\(styleID).innerDY", Double(innerDY))))
            .at(p.x, st.capCentre(baseline: p.baseline))
            .accessibilityIdentifier(id)
    }
}

/// The body in the prop's place: the grant's style at ui.json `modules.offer.bodySize`, one line or two balanced lines
/// (the booster popup's rule, `SocTwoLines.descriptionLines`), centred on the prop's frame.
private struct OfferBody: View {
    let text: String
    let frame: CGRect
    let id: String
    let style: GameTextStyle
    let t: Tokens

    var body: some View {
        let st = style.sized(CGFloat(t.number("modules.offer.bodySize", 30)))
        let width = CGFloat(t.number("modules.offer.bodyMaxWidth", 330))
        let gap = CGFloat(t.number("modules.offer.bodyLineGap", 40))
        let lines = SocTwoLines.descriptionLines(text, style: st, width: width)
        ZStack(alignment: .topLeading) {
            ForEach(Array(lines.enumerated()), id: \.offset) { i, line in
                GameText(verbatim: line, style: st, maxWidth: width)
                    .at(frame.midX, st.capCentre(baseline: frame.midY + (CGFloat(i) - CGFloat(lines.count - 1) / 2) * gap
                                                 + st.size * 0.36))
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier(id)
        .accessibilityLabel(Text(verbatim: text))
    }
}
