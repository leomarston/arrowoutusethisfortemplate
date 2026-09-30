import SwiftUI
import PathCore

// SHELL S3 (SPEC-architecture §6.6 "meta: noLives"; SPEC-ui §2.9 More Lives; SPEC-gameplay §8.2-§8.4, §9.5; VERIFIED meta-095,
// text frames tok2 `text2.moreLives.*`). "More Lives": the blue panel, the ribbon, the red X, a cream card with a white sunburst
// behind the big glossy heart (the live count + a "+"), "Time to next live:" and the peach timer capsule (stopwatch + "27:04",
// ticking once a second), the framed green "Refill [coin] 900" — the only offer — and the coin group at the top left (→ the
// Shop over the popup). A1 (owner item 9, ruling 37(d), release-plan §4.2; SUPERSEDES SPEC.md §5.18): the rewarded-video
// "+1 Live" button and its offline ad slot are gone, and the panel ends under the one button exactly as BoosterBuyPopup's
// does (10.3 · 164.5 · 372.6 · 425.0, was 541.8; X, ribbon, heart, timer and Refill keep their places).
// Opened by the lives pill (lives < 5) and by Play / Try Again at 0 lives (GAME). Answers:
//   Refill (coins ≥ 900) → Economy.refillLives (lives = 5, coins − 900, saved) → .primary; short of coins → the Shop opens over
//     the popup (SPEC-gameplay §9.5) and the popup stays (the player taps Refill again)
//   X → .close; the lives back at 5 while it is open (the refill clock) → it closes itself with .primary (SPEC-ui DECISION)

struct NoLivesPopup: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app

    var body: some View {
        let t = app.tuning.ui.tokens
        let rules = ShellEconomy.rules(app)
        let price = rules.lives.refillPrice
        ZStack(alignment: .topLeading) {
            PopupPanelFrame(n: 5.8, t: t, rivetInset: CGPoint(x: 12.7, y: 82.5), rivetAlong: 75).placed(CGRect(10.3, 164.5, 372.6, 425.0))
            PopupCard(radius: 24, t: t).placed(CGRect(59.4, 242.5, 275.2, 182.8))
            SunburstRays(centre: CGPoint(x: 138.3, y: 55.0), rays: 16)
                .frame(width: 275.2 - 13.6, height: 182.8 - 13.6)
                .clipShape(RoundedRectangle(cornerRadius: 17.2))
                .placed(CGRect(66.2, 249.3, 261.6, 169.2))
            TimelineView(.periodic(from: .now, by: 1)) { ctx in
                LivesCardContent(now: app.clock.wallClock(ctx.date), rules: rules) { answer(PopupResult.primary) }
            }
            PriceButton(id: "popup.noLives.refill", label: "Refill", price: price,
                        face: CGRect(80.7, 451.7, 231.9, 86.4), well: CGRect(69.4, 443.0, 254.5, 104.1), n: 4.8,
                        labelID: "moreLives.refill.label",
                        labelStyle: .s2(35.5, -0.92, [Skin.popupsNoLivesPopupNoLivesPopupLabelStyle0, Skin.popupsNoLivesPopupNoLivesPopupLabelStyle1, Skin.popupsNoLivesPopupNoLivesPopupLabelStyle2], outline: Skin.popupsNoLivesPopupNoLivesPopupOutline, 1.52, drop: 1.84),
                        labelAt: (140.3, 505.7),
                        priceID: "moreLives.refill.price",
                        priceStyle: .s2(35.7, 1.1, [Skin.popupsNoLivesPopupNoLivesPopupPriceStyle0, Skin.popupsNoLivesPopupNoLivesPopupPriceStyle1, Skin.popupsNoLivesPopupNoLivesPopupPriceStyle2], outline: Skin.popupsNoLivesPopupNoLivesPopupOutline, 1.61, drop: 1.8),
                        priceAt: (264.9, 505.7),
                        coin: CGRect(190.0, 472.0, 34, 34),
                        wellInset: OfferWell.tightInset) { refill(price) }
            PopupTitle(title: "More Lives", frame: CGRect(60.4, 136.8, 274.2, 90.4), t: t, baselineFromTop: 59.3)
            PopupCloseButton(id: "popup.noLives.close", t: t) { answer(PopupResult.close) }
                .placed(CGRect(339.9, 175.7, 45, 45))
            OfferCoinGroup(frame: CGRect(13.0, 64.7, 105.1, 41.4), coins: CoinPillDisplay.shared.shown(app.store.state),
                           textID: "moreLives.coinGroup.digits")
        }
        .frame(width: 393, height: 852, alignment: .topLeading)
    }

    private func refill(_ price: Int) {
        let rules = ShellEconomy.rules(app)
        let ok = app.store.mutateAndSave { Economy.refillLives(&$0, now: app.clock.wallClock(), rules: rules) }
        Log.mark("popup", "noLives refill → \(ok ? "lives 5, coins \(app.store.state.coins)" : "refused (coins \(app.store.state.coins) < \(price) or full)")")
        if ok { answer(PopupResult.primary); return }
        if app.store.state.coins < price { ShopPage.openOver(app, section: .coins) }
    }
}

/// The heart with the live count, the caption and the ticking timer capsule (re-evaluated once a second).
private struct LivesCardContent: View {
    let now: Date
    let rules: EconomyRules
    let full: () -> Void
    @Environment(AppModel.self) private var app

    var body: some View {
        let s = app.store.state
        let count = Economy.livesCount(s, now: now, rules: rules)
        let left = Economy.countdown(s, now: now, rules: rules) ?? 0
        let unlimited = Economy.hasUnlimitedLives(s, now: now)
        let countStyle = GameTextStyle.s2(50.3, 0, [Skin.popupsNoLivesPopupLivesCardContentCountStyle0], outline: Skin.popupsNoLivesPopupLivesCardContentCountStyleOutline, 1.7, drop: 1.2)
        let caption = GameTextStyle.s2(25.4, -0.7, [Skin.popupsNoLivesPopupLivesCardContentCaption0])
        let timer = GameTextStyle.s2(25.4, -0.73, [Skin.popupsNoLivesPopupLivesCardContentTimer0], outline: Skin.popupsNoLivesPopupLivesCardContentTimerOutline, 0.94, drop: 0.6)
        ZStack(alignment: .topLeading) {
            ArtImage(art: .heartLivesBig).placed(CGRect(146.9, 250.5, 100, 90))
            GameText(verbatim: "\(count)", style: countStyle).at(146.9 + 49.3, countStyle.capCentre(baseline: 311.0))
                .accessibilityIdentifier("popup.noLives.count")
            GameText(verbatim: "+", style: countStyle.sized(46)).at(146.9 + 80.8, 250.5 + 76.0)
            // B3: fitted inside the 261.6 pt cream card (was 270: TR / SL ran edge to edge); EN fits at 1.0 either way
            GameText("Time to next life:", style: caption, maxWidth: 250).at(196.5, caption.capCentre(baseline: 369.0))
            TimerCapsule().placed(CGRect(138.1, 377.0, 120.1, 44.4))
            ArtImage(art: .iconStopwatch).placed(CGRect(125.0, 382.2, 34, 34))
            GameText(verbatim: LivesText.clock(left), style: timer, maxWidth: 90).at(213.5, timer.capCentre(baseline: 410.9))
                .accessibilityIdentifier("popup.noLives.timer")
        }
        .onChange(of: count >= rules.lives.max || unlimited) { _, isFull in
            if isFull { Log.mark("popup", "noLives: lives back at \(count), closing"); full() }
        }
    }
}

/// The recessed peach capsule (rr 22: face #E7A17C, top inner shadow #B56340 → #D5A189, a light lower rim #FAEDE7).
private struct TimerCapsule: View {
    var body: some View {
        Rasterized("livesTimerCapsule", overflow: 1) { size in
            let r = size.height / 2
            ZStack {
                RoundedRectangle(cornerRadius: r).fill(Color(hex: Skin.popupsNoLivesPopupTimerCapsuleFill))
                RoundedRectangle(cornerRadius: r).fill(Color(hex: Skin.popupsNoLivesPopupTimerCapsuleFillV2)).padding(EdgeInsets(top: 0, leading: 0.5, bottom: 1.6, trailing: 0.5))
                RoundedRectangle(cornerRadius: r)
                    .fill(LinearGradient(stops: [.init(color: Color(hex: Skin.popupsNoLivesPopupTimerCapsuleStops0), location: 0), .init(color: Color(hex: Skin.popupsNoLivesPopupTimerCapsuleStops1, 0.6), location: 0.22),
                                                 .init(color: .clear, location: 0.4)], startPoint: .top, endPoint: .bottom))
                    .padding(EdgeInsets(top: 0, leading: 0.5, bottom: 1.6, trailing: 0.5))
            }
        }
    }
}

/// Code-drawn sunburst rays (#FFFFFA on the cream card, `rays` wedges from `centre`).
struct SunburstRays: View {
    let centre: CGPoint
    var rays = 16
    var colour = Color(hex: Skin.popupsNoLivesPopupSunburstRaysColour)
    var body: some View {
        Rasterized("sunburst|\(rays)|\(centre.x),\(centre.y)") { size in
            Path { p in
                let r = max(size.width, size.height) * 1.5
                for i in 0..<rays {
                    let a0 = Double(i) / Double(rays) * 2 * .pi, a1 = a0 + .pi / Double(rays)
                    p.move(to: centre)
                    p.addLine(to: CGPoint(x: centre.x + r * CGFloat(cos(a0)), y: centre.y + r * CGFloat(sin(a0))))
                    p.addLine(to: CGPoint(x: centre.x + r * CGFloat(cos(a1)), y: centre.y + r * CGFloat(sin(a1))))
                    p.closeSubpath()
                }
            }
            .fill(colour.opacity(0.85))
        }
    }
}
