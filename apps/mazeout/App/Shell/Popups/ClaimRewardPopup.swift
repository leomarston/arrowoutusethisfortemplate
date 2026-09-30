import SwiftUI
import PathCore

// SHELL S2 (SPEC-ui §2.11; uim `claim`, `claimCoins`, tok2 `claimBulb`; VERIFIED 033 / 034 / 095 / 100 / 164 / 172 / 173 / 197 /
// 198; SPEC-motion-audio §6.6). "Congratulations!" — no panel: the 0.90 dim, the title 10 · 151.8 · 373.7 · 53.4 (45.2 / −0.8, a gold
// face #FFDD13 → #FFB700, outline #B24900 0.9, a 1.8 drop; top-anchored), the reward centred at (197, ≈ 411) — unlimited lives
// (`heartInfinite` 74 × 65 + "30m" / "1h" 27.6 / −1.0 white outlined #B30400) · coins (`coinPileSmall` 77 × 60 + the amount 27.2
// white outlined #09066D) · a booster (its icon + "x1" 15.2 white outlined #09066D) — several parts side by side, gold twinkles
// around it (VERIFIED 033: sparkles, no rays), and "Tap to Claim" 96.7 · 673.9 (31.5 / −0.5 white outlined #3A007C). The reward
// pops (0.30 s, 1.15) at S + 0.10. Tap anywhere → ♪ uiClick → .primary (the claim is applied by GAME / SOC2; coins fly home).
// A2 FEEL-P (owner item 8; motion-catalog §3.2 / §6.6, VERIFIED on v552's Sky Jump claim, INFERRED shared by every claim until
// R8): the title's letters pop in LEFT → RIGHT (`LetterPopTitle`, 27 ms apart, each 0.5 → 1.15 → 1 over 0.12 s: the last
// is in by S + 0.43); ◉ rewardPop when the reward lands (S + 0.40, motion-catalog §5.1 row 21).

struct ClaimRewardPopup: View {
    let grant: Grant
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?
    @State private var beats = BeatOnce()

    var body: some View {
        let t = app.tuning.ui.tokens
        let items = ClaimItem.items(grant)
        TimelineView(.animation(minimumInterval: nil, paused: shownAt == nil)) { ctx in
            let u = shownAt.map { app.clock.sequenceTime("claim", app.clock.gameTime(ctx.date) - $0) } ?? 0
            let pop = UnlockTiming.pop(u, at: 0.10, from: 0.2, over: 1.15, rise: 0.18, total: 0.30)
            ZStack(alignment: .topLeading) {
                Color.clear
                LetterPopTitle(text: ClaimTitle.text(app.tuning.ui.tokens, id: "claim.title.title"),
                               style: ClaimTitle.style(app.tuning.ui.tokens, id: "claim.title.title",
                                                       .s2(45.2, -0.83, [Skin.popupsClaimRewardPopupClaimRewardPopupStyle0, Skin.popupsClaimRewardPopupClaimRewardPopupStyle1, Skin.popupsClaimRewardPopupClaimRewardPopupStyle2], outline: Skin.popupsClaimRewardPopupClaimRewardPopupOutline, 0.94, drop: 1.81)),
                               baseline: 187.4, centreX: 196.8, maxWidth: 360, u: u)
                    .accessibilityIdentifier("claim.title.title")
                let _ = beats.fire("rewardLand", at: 0.40, u: u) { app.haptics.play(.rewardPop) }
                if let pop {
                    ClaimRewardRow(items: items, t: t).equatable()
                        .scaleEffect(CGFloat(pop), anchor: UnitPoint(x: 197.0 / 393, y: 411.0 / 852))
                    ClaimSparkles(u: u, t: t)
                }
                TokenText(id: "claim.tap.tap", source: .copy("Tap to Claim"),
                          style: .s2(31.5, -0.48, [Skin.popupsClaimRewardPopupClaimRewardPopupStyle0V2], outline: Skin.popupsClaimRewardPopupClaimRewardPopupOutlineV2, 1.23, drop: 1.17),
                          baseline: 701.9, centreX: 195.8, maxWidth: 300)
            }
        }
        .frame(width: 393, height: 852)
        .contentShape(Rectangle())
        .onTapGesture { claim() }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("claim.tap")
        .accessibilityAddTraits(.isButton)
        .onAppear { shownAt = app.clock.gameTime() }
    }

    private func claim() {
        if let cue = app.tuning.audio.cue("uiButton") { app.audio.play(cue, gain: Float(app.tuning.audio.gain(cue))) }
        if let h = GameButtonFeedback.haptic(app) { app.haptics.play(h) }
        answer(PopupResult.primary)
    }
}

// MARK: - A2: the staged title and the once-per-beat helper

/// A title whose letters pop in one by one, left → right (v552 Sky Jump claim: 16 letters, the right edge 43 → 376 pt by
/// S + 0.43; each letter grows 26 → 49 pt tall). Same look as one GameText line: the letters are the line's own advances
/// (kerning and tracking included), shrunk as a whole to `maxWidth` like GameText does.
struct LetterPopTitle: View {
    let text: String
    let style: GameTextStyle
    let baseline: CGFloat
    let centreX: CGFloat
    let maxWidth: CGFloat
    let u: Double
    var step = 0.027
    var duration = 0.12
    var from = 0.5
    var overshoot = 1.15

    var body: some View {
        let chars = Array(text)
        let full = GameTextLayout.make(text, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking).advance
        let k = min(1, maxWidth / max(full, 1))
        let st = style.sized(style.size * k)
        let left = centreX - full * k / 2
        ZStack(alignment: .topLeading) {
            ForEach(Array(chars.enumerated()), id: \.offset) { i, ch in
                if ch != " ", let s = Self.scale(u, at: Double(i) * step, duration: duration, from: from, overshoot: overshoot) {
                    let x0 = i == 0 ? 0 : Self.adv(String(chars[..<i]), style) + style.tracking
                    let w = Self.adv(String(ch), style)
                    GameText(verbatim: String(ch), style: st)
                        .scaleEffect(CGFloat(s))
                        .at(left + (x0 + w / 2) * k, st.capCentre(baseline: baseline))
                }
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(verbatim: text))
    }

    static func adv(_ s: String, _ st: GameTextStyle) -> CGFloat {
        GameTextLayout.make(s, postScriptName: st.postScriptName, size: st.size, tracking: st.tracking).advance
    }

    /// nil before the letter's beat; from → overshoot (ease-out, 60 %) → 1 (smoothstep).
    static func scale(_ u: Double, at: Double, duration: Double, from: Double, overshoot: Double) -> Double? {
        let t = u - at
        guard t >= 0 else { return nil }
        guard t < duration else { return 1 }
        let x = t / duration
        if x < 0.6 { let q = x / 0.6; return from + (overshoot - from) * (1 - (1 - q) * (1 - q)) }
        let q = (x - 0.6) / 0.4
        return overshoot + (1 - overshoot) * (q * q * (3 - 2 * q))
    }
}

/// The claim title's text and style from the strings table / ui.json (what TokenText reads for the same id).
@MainActor enum ClaimTitle {
    static func text(_ t: Tokens, id: String) -> String { String(localized: "Congratulations!") }
    static func style(_ t: Tokens, id: String, _ d: GameTextStyle) -> GameTextStyle { t.text(id, d) }
}

/// Fires each named beat once, on the first evaluation at or after its time, and only near it (a late first frame does not
/// replay old beats). A reference type kept in @State: a view body may call it every frame.
@MainActor final class BeatOnce {
    private var done: Set<String> = []
    func fire(_ name: String, at: Double, u: Double, window: Double = 0.1, _ action: () -> Void) {
        guard u >= at, !done.contains(name) else { return }
        done.insert(name)
        if u - at <= window { action() }
    }
}

/// One part of a grant as the claim screen draws it.
struct ClaimItem: Equatable {
    enum Kind: Equatable { case unlimited(Double), coins(Int), booster(String, Int) }
    let kind: Kind

    static func items(_ g: Grant) -> [ClaimItem] {
        var out: [ClaimItem] = []
        if g.unlimitedLives > 0 { out.append(ClaimItem(kind: .unlimited(g.unlimitedLives))) }
        if g.coins > 0 { out.append(ClaimItem(kind: .coins(g.coins))) }
        for (id, n) in g.boosters.sorted(by: { $0.key < $1.key }) where n > 0 { out.append(ClaimItem(kind: .booster(id, n))) }
        return out
    }

    /// "30m", "1h", "1h 30m" (the countdown strings of the strings table).
    static func duration(_ s: Double) -> String {
        let m = Int((s / 60).rounded())
        if m >= 60 { return m % 60 == 0 ? String(localized: "\(m / 60)h") : String(localized: "\(m / 60)h \(m % 60)m") }
        return String(localized: "\(m)m")
    }
}

private struct ClaimRewardRow: View, Equatable {
    let items: [ClaimItem]
    let t: Tokens
    static func == (a: ClaimRewardRow, b: ClaimRewardRow) -> Bool { a.items == b.items }

    var body: some View {
        let pitch: CGFloat = 104
        let x0 = 197 - pitch * CGFloat(max(0, items.count - 1)) / 2
        ZStack(alignment: .topLeading) {
            ForEach(Array(items.enumerated()), id: \.offset) { i, item in
                itemView(item, cx: x0 + CGFloat(i) * pitch)
            }
        }
    }

    @ViewBuilder private func itemView(_ item: ClaimItem, cx: CGFloat) -> some View {
        let dx = cx - 197
        switch item.kind {
        case .unlimited(let s):
            InkImage(art: .heartInfinite, ink: t.frame("claim.heart", CGRect(159.8, 374.4, 74.1, 64.7)).offsetBy(dx: dx, dy: 0))
            TokenText(id: "claim.amount.amt", source: .number(ClaimItem.duration(s)),
                      style: .s2(27.6, -1.03, [Skin.popupsClaimRewardPopupClaimRewardRowItemViewUnlimitedStyle0], outline: Skin.popupsClaimRewardPopupClaimRewardRowItemViewUnlimitedOutline, 1.61, drop: 1.16), baseline: 459.7, centreX: 196.5 + dx)
        case .coins(let n):
            InkImage(art: .coinPileSmall, ink: t.frame("claimCoins.coins", CGRect(158.5, 382.7, 76.7, 60.1)).offsetBy(dx: dx, dy: 0))
            TokenText(id: "claimCoins.amount.amt", source: .number("\(n)"),
                      style: .s2(27.2, -1.0, [Skin.popupsClaimRewardPopupClaimRewardRowItemViewCoinsStyle0], outline: Skin.popupsClaimRewardPopupClaimRewardRowItemViewCoinsOutline, 2.61, drop: 0.25), baseline: 460.4, centreX: 196.5 + dx)
        case .booster(let id, let n):
            InkImage(art: id == BoosterID.freeze.rawValue ? .boosterFreeze : .boosterHint,
                     ink: t.frame("claimBulb.icon", CGRect(174.8, 377.0, 43.7, 63.4)).offsetBy(dx: dx, dy: 0))
            TokenText(id: "claimBulb.amount.x", source: .number("x\(n)"),
                      style: .s2(15.2, 0.3, [Skin.popupsClaimRewardPopupClaimRewardRowItemViewBoosterStyle0], outline: Skin.popupsClaimRewardPopupClaimRewardRowItemViewBoosterOutline, 1.3, drop: 0.6), baseline: 448.3, centreX: 195.3 + dx)
        }
    }
}

/// Gold twinkles around the reward (VERIFIED 033/034: small gold sparkles), the unlock-twinkle rule in gold.
private struct ClaimSparkles: View {
    let u: Double
    let t: Tokens
    var body: some View {
        let every = 0.12, life = 0.7
        let newest = Int(max(0, u) / every)
        ZStack(alignment: .topLeading) {
            ForEach(max(0, newest - 6)...newest, id: \.self) { i in
                let age = u - Double(i) * every
                if age >= 0 && age < life {
                    let a = Double((i * 2654435761) % 1000) / 1000 * 2 * .pi
                    let r = 36 + Double((i * 40503) % 30)
                    let k = age / life
                    let s = k < 0.4 ? k / 0.4 : (1 - k) / 0.6
                    ArtImage(art: .sparkleTwinkle)
                        .colorMultiply(Color(hex: Skin.popupsClaimRewardPopupClaimSparklesColorMultiply))
                        .frame(width: 10, height: 10)
                        .scaleEffect(CGFloat(s))
                        .position(x: 197 + CGFloat(cos(a) * r), y: 411 + CGFloat(sin(a) * r * 0.85))
                }
            }
        }
        .allowsHitTesting(false)
    }
}
