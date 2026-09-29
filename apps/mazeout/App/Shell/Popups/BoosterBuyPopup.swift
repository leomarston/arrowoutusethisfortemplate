import SwiftUI
import PathCore

// SHELL S3 (SPEC-architecture §6.6 "meta: boosterBuy"; SPEC-gameplay §6.4 + CONSISTENCY K-6 (GP's popup wins; SPEC-ui §2.10 supplies
// the panel geometry: the More Lives frame); strings S-5 / S-24). A booster tapped at 0 stock opens (the level timer held by GAME):
// the blue panel, the ribbon with the booster's name ("Time Freeze" / "Hint"), the cream sunburst card holding the booster icon
// at 110 pt and its one line ("Freeze the timer for 10 seconds!" / "Find an arrow that can move!"), one framed green
// "Buy x3 [coin] 900" button (rules.json `economy.boosterPack`), the red X and the coin group. Buy with ≥ 900 coins → coins
// − 900, stock + 3 (Economy.buyBooster, saved) → .primary (the player taps the booster again to use it); short of coins → the
// Shop opens over the popup (scrolled to Coins) and the popup stays to re-check; X → .close. The panel is shortened to end
// under the one button (DECISION: the More Lives height would leave an empty field).

struct BoosterBuyPopup: View {
    let booster: BoosterID
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app

    var body: some View {
        let t = app.tuning.ui.tokens
        let pack = ShellEconomy.rules(app).economy.boosterPack
        let freeze = booster == .freeze
        let line = GameTextStyle.s2(21, -0.6, [0x5A2801])
        let buy = GameTextStyle.s2(35.5, -0.92, [0xFFFBF3, 0xFFF7E7, 0xFDF3DF], outline: 0x924500, 1.52, drop: 1.84)
        let count = GameTextStyle.s2(24.0, -0.6, [0xFFFBF3, 0xFFF7E7, 0xFDF3DF], outline: 0x924500, 1.3, drop: 1.2)
        let priceStyle = GameTextStyle.s2(35.7, 1.1, [0xFFFBF3, 0xFFF7E6, 0xFDF3DF], outline: 0x924500, 1.61, drop: 1.8)
        let face = CGRect(80.7, 451.7, 231.9, 86.4)
        ZStack(alignment: .topLeading) {
            PopupPanelFrame(n: 5.8, t: t, rivetInset: CGPoint(x: 12.7, y: 82.5), rivetAlong: 75).placed(CGRect(10.3, 164.5, 372.6, 425.0))
            PopupCard(radius: 24, t: t).placed(CGRect(59.4, 242.5, 275.2, 182.8))
            SunburstRays(centre: CGPoint(x: 130.8, y: 62.0), rays: 16)
                .frame(width: 261.6, height: 169.2)
                .clipShape(RoundedRectangle(cornerRadius: 17.2))
                .placed(CGRect(66.2, 249.3, 261.6, 169.2))
            ArtImage(art: freeze ? .boosterFreeze : .boosterHint).placed(CGRect(142.0, 256.0, 110, 110))
            // B3: one line (EN/TR, as before); a translation that would need < 0.70 on one line takes two balanced lines
            // (SPEC-ui's 2-line frame for this copy), 12.5 pt above and below the one-line baseline
            let desc = String(localized: freeze ? "Freeze the timer for 10 seconds!" : "Find an arrow that can move!")
            let descLines = Self.descriptionLines(desc, style: line, width: 262)
            ForEach(Array(descLines.enumerated()), id: \.offset) { i, l in
                GameText(verbatim: l, style: line, maxWidth: 262)
                    .at(196.5, line.capCentre(baseline: descLines.count == 1 ? 398.0 : 385.5 + 25.0 * CGFloat(i)))
            }
            OfferWell(n: 4.6, inset: OfferWell.tightInset, t: t).placed(CGRect(69.4, 443.0, 254.5, 104.1))
            GameButton(id: "popup.boosterBuy.buy", label: "Buy", value: "\(pack.count)x\(pack.price)", action: { buyPack(pack) }) {
                ZStack(alignment: .topLeading) {
                    ChromeButtonFace(colors: .green, n: 4.8)
                    // "Buy" + "x3" as one run, centred left of the coin.
                    // B3 L10N-APP: the two shrink TOGETHER to the 118 pt group (floor 0.70, FitLedger): the old maxWidth 92
                    // on "Buy" alone let a long translation push "x3" onto the coin (DE touched it, TR ran over it). EN fits
                    // at scale 1 and draws exactly as before.
                    let buyText = String(localized: "Buy"), countText = "x\(pack.count)"
                    let k = Self.groupScale(buyText, countText, buy: buy, count: count, width: 118)
                    let buyK = k < 1 ? buy.sized(buy.size * k) : buy, countK = k < 1 ? count.sized(count.size * k) : count
                    HStack(alignment: .center, spacing: 4) {
                        GameText(verbatim: buyText, style: buyK)
                        GameText(verbatim: countText, style: countK)       // on the same baseline as "Buy"
                            .offset(y: (GameText.capHeight(postScriptName: buyK.postScriptName, size: buyK.size)
                                        - GameText.capHeight(postScriptName: countK.postScriptName, size: countK.size)) / 2)
                    }
                    .frame(width: 118, height: 60)
                    .position(x: 143.5 - face.minX, y: buy.capCentre(baseline: 505.7) - face.minY)
                    ArtImage(art: .iconCoin).placed(CGRect(203.5 - face.minX, 472.0 - face.minY, 34, 34))
                    GameText(verbatim: "\(pack.price)", style: priceStyle).at(272.0 - face.minX, priceStyle.capCentre(baseline: 505.7) - face.minY)
                }
                .frame(width: face.width, height: face.height, alignment: .topLeading)
            }
            .placed(face)
            PopupTitle(title: freeze ? "Time Freeze" : "Hint", frame: CGRect(60.4, 136.8, 274.2, 90.4), t: t, baselineFromTop: 59.3)
            PopupCloseButton(id: "popup.boosterBuy.close", t: t) { answer(PopupResult.close) }
                .placed(CGRect(339.9, 175.7, 45, 45))
            OfferCoinGroup(frame: CGRect(13.0, 64.7, 105.1, 41.4), coins: CoinPillDisplay.shared.shown(app.store.state),
                           textID: "boosterBuy.coinGroup.digits")
        }
        .frame(width: 393, height: 852, alignment: .topLeading)
    }

    /// B3: the description as one line while it fits `width` at ≥ 0.70, else the two-line break whose wider line is narrowest.
    static func descriptionLines(_ text: String, style: GameTextStyle, width: CGFloat) -> [String] {
        func adv(_ s: String) -> CGFloat {
            GameTextLayout.make(s, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking).advance
        }
        guard adv(text) * 0.70 > width else { return [text] }
        let two = SocTwoLines.split(text, size: style.size, parts: 2)
        let w = two.map(adv).max() ?? 0
        FitLedger.note("boosterBuy.desc2", text: text, need: width / max(w, 1))
        return two
    }

    /// B3: the one scale of the "Buy" + "x3" group that fits `width` (GameText's frame: the ink box + the outline pad + 1.5 pt
    /// per side, 4 pt apart in the HStack), 1 when it fits; a need below 0.70 is logged by FitLedger (-pc.fitLog).
    static func groupScale(_ a: String, _ b: String, buy: GameTextStyle, count: GameTextStyle, width: CGFloat) -> CGFloat {
        func frame(_ t: String, _ st: GameTextStyle) -> (variable: CGFloat, constant: CGFloat) {
            let l = GameTextLayout.make(t, postScriptName: st.postScriptName, size: st.size, tracking: st.tracking)
            let half = max(l.advance / 2, l.advance / 2 - l.inkBounds.minX, l.inkBounds.maxX - l.advance / 2)
            return (2 * (half + st.outlineWidth), 2 * 1.5)
        }
        let fa = frame(a, buy), fb = frame(b, count)
        let constant = fa.constant + fb.constant + 4
        let variable = fa.variable + fb.variable
        guard variable + constant > width else { return 1 }
        let k = (width - constant) / max(variable, 1)
        FitLedger.note("boosterBuy.group", text: a + " " + b, need: k)
        return max(0.70, k)
    }

    private func buyPack(_ pack: EconomyRules.BoosterPack) {
        let rules = ShellEconomy.rules(app)
        let ok = app.store.mutateAndSave { Economy.buyBooster(&$0, booster, rules: rules) }
        Log.mark("popup", "boosterBuy \(booster.rawValue) → \(ok ? "bought x\(pack.count), stock \(app.store.state.boosters[booster.rawValue] ?? 0)" : "refused (coins \(app.store.state.coins))")")
        if ok { answer(PopupResult.primary); return }
        if app.store.state.coins < pack.price { ShopPage.openOver(app, section: .coins) }
    }
}
