import SwiftUI
import UIKit
import PathCore

// SOCIAL SOC2 (SPEC-ui §2.15.6 Weekly Contest info, §2.15.7 the L50 forced tutorial, §2.15.8 the Weekly result; SPEC-social §1.1,
// §4.3; SPEC-motion-audio §6.5; VERIFIED 130-133, meta-016/017, S1-weekly-contest-open):
//   SocWeeklyTutorial  (PopupID.weeklyContestTutorial, a full page so its hole follows the live nav bar): dim 0.92 over home with
//                      the trophy tab drawn undimmed and highlighted (#117FFB), the cream card "Tap to compete in / Weekly
//                      Contest!", the big yellow arrow pointing DOWN at the tab (pops, then bobs 8 pt). ONLY the tab answers
//                      (`PopupStyle.inputLock`: every other button is locked; the tab clears the lock for itself).
//   SocWeeklyInfo      (PopupID.weeklyContestIntro, the (i)): dim 0.90; "Weekly Contest"; Beat Levels! · Contest with others!
//                      (the mini podium with the store's marketing names Max / Neo / James, never translated) · Win Rewards! ·
//                      Compete against your friends! / There is a new contest every week! · Tap to Continue.
//   SocWeeklyResult    (`.custom("weeklyResult")`, NEW, DECISION): the claim overlay's layout with "Weekly Contest", the rank hex
//                      (1-3) or the plain rank, "You finished #n!", the prize for the podium, "Tap to Claim" / "Tap to Continue".

struct SocWeeklyTutorial: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m
    @State private var shownAt: Double?

    // FIX-2 lane B (L26, the lock leaked once in 8 runs): the input lock no longer lives inside the per-frame TimelineView. Only
    // the bobbing pointer (no hit testing) is re-evaluated every frame; the 0.92 dim, the trophy tab and the card are built once.
    // The dim is a UIKit view (`TutorialTouchSwallow`) whose hitTest claims every touch outside the tab's hole — taps, double
    // taps, drags, a second touch sequence — so no touch can reach home's buttons under the page or a SwiftUI gesture whose state
    // a body rebuild could reset; inside the hole it answers nil and the tab (drawn above it) takes the touch.
    var body: some View {
        let hole = m.rect(CGRect(279.2, 772.3, 93.7, 80.4), .bottom)
        ZStack(alignment: .topLeading) {
            Color.black.opacity(0.92).frame(width: m.size.width, height: m.size.height)
                .allowsHitTesting(false)
                .accessibilityHidden(true)
            TutorialTouchSwallow(hole: hole)
                .frame(width: m.size.width, height: m.size.height)
                .accessibilityHidden(true)
            GameButton(id: "weekly.tutorial.tab", label: "Leaderboard", action: { answer(PopupResult.primary) }) {
                ZStack {
                    Rectangle().fill(LinearGradient(colors: [Color(hex: 0x00A395), Color(hex: 0x009288)], startPoint: .top, endPoint: .bottom))
                    ArtImage(art: .navCup).frame(width: 72, height: 66)
                }
            }
            .environment(\.tapsLocked, false)
            .placed(hole)
            ReferenceCanvas {
                ZStack(alignment: .topLeading) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 14.5).fill(Color(hex: 0x00827B))
                        RoundedRectangle(cornerRadius: 12.5).fill(Color(hex: 0xF4E8D4)).padding(2.5)
                        SocTwoLines(text: "Tap to join the Weekly Cup!", centreX: 141, baselines: [33.3, 64.0], box: 235, size: 26,
                                    faceHex: 0x05292B, hotHex: 0x05292B, outline: nil, greedy: true)
                    }
                    .frame(width: 281.9, height: 82.1)
                    .placed(CGRect(55.7, 514.8, 281.9, 82.1))
                    .accessibilityElement(children: .ignore)
                    .accessibilityIdentifier("weekly.tutorial.card")
                    .accessibilityLabel(Text("Tap to join the Weekly Cup!"))
                    .allowsHitTesting(false)
                }
                .frame(width: 393, height: 852, alignment: .topLeading)
            }
            .allowsHitTesting(false)
            TimelineView(.animation(minimumInterval: nil, paused: shownAt == nil)) { ctx in
                let u = shownAt.map { app.clock.gameTime(ctx.date) - $0 } ?? 0
                let bob = u > 0.16 ? 8 * (0.5 - 0.5 * cos((u - 0.16) / 0.9 * 2 * .pi)) : 0
                SocPopIn(u: u, start: 0, duration: 0.16, overshoot: 1.12, anchor: .bottom) {
                    ArtImage(art: .pointerArrowDown)
                }
                .frame(width: 78 * m.s, height: 104 * m.s)
                .position(x: hole.midX, y: hole.minY - 74 * m.s + CGFloat(bob) * m.s)
            }
            .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
            .allowsHitTesting(false)
            .accessibilityHidden(true)
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("weekly.tutorial")
        .onAppear { shownAt = app.clock.gameTime(); Log.mark("tutorial", "show weeklyContest") }
    }
}

/// FIX-2 lane B (L26): a forced tutorial's input lock as a UIKit view. `hitTest` returns the view itself for every point outside
/// `hole` (so UIKit delivers the whole touch sequence to it and it drops it: no SwiftUI gesture and no view under the page ever
/// sees it) and nil inside `hole` (the touch goes on to the tutorial's target drawn there). No gesture recognizer, no state:
/// nothing a SwiftUI body rebuild can reset between the touch-down and the touch-up.
struct TutorialTouchSwallow: UIViewRepresentable {
    let hole: CGRect

    func makeUIView(context: Context) -> SwallowView {
        let v = SwallowView()
        v.backgroundColor = .clear
        v.isMultipleTouchEnabled = true
        v.hole = hole
        return v
    }

    func updateUIView(_ v: SwallowView, context: Context) { v.hole = hole }

    final class SwallowView: UIView {
        var hole: CGRect = .zero
        /// Touches claimed so far (tests / logs).
        private(set) var swallowed = 0

        override func hitTest(_ point: CGPoint, with event: UIEvent?) -> UIView? {
            guard bounds.contains(point), !hole.contains(point) else { return nil }
            return self
        }

        // claimed touches end here: not forwarded up the responder chain
        override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) { swallowed += touches.count }
        override func touchesMoved(_ touches: Set<UITouch>, with event: UIEvent?) {}
        override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {}
        override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent?) {}
    }
}

struct SocWeeklyInfo: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?

    var body: some View {
        TimelineView(.animation(minimumInterval: nil, paused: shownAt.map { app.clock.gameTime() - $0 > 1.4 } ?? true)) { ctx in
            let u = shownAt.map { app.clock.gameTime(ctx.date) - $0 } ?? 0
            let bob = u > 0.88 ? 8 * (0.5 - 0.5 * cos((u - 0.88) / 0.9 * 2 * .pi)) : 0
            ZStack(alignment: .topLeading) {
                Color.clear
                SocPopIn(u: u, start: 0.18, duration: 0.10, overshoot: 1.10, at: CGPoint(x: 199.3, y: 83.4 - 12)) { SocInfoTitle(title: "Weekly Cup", baseline: 83.4, look: .weekly) }
                SocPopIn(u: u, start: 0.35, duration: 0.16, overshoot: 1.12, at: CGPoint(x: 37.4 + 115.1 / 2, y: 153.5 + 115.1 / 2)) {
                    ArtImage(art: .infoPathIcon).placed(CGRect(37.4, 153.5, 115.1, 115.1))
                }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 95, y: 289.2 - 6)) { SocTwoLines(text: "Beat Levels!", centreX: 95, baselines: [289.2], box: 170) }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 192.8 + 37.7 / 2, y: 203.2 + 36.7 / 2)) {
                    ArtImage(art: .pointerArrowYellow)
                        .placed(CGRect(200 + CGFloat(bob) * 0.6, 208 + CGFloat(bob) * 0.6, 40, 45))
                }
                SocPopIn(u: u, start: 0.72, duration: 0.25, overshoot: 1.08, at: CGPoint(x: 148.1 + 220.9 / 2, y: 293 + 160 / 2)) { SocMiniPodium().placed(CGRect(148.1, 293, 220.9, 160)) }
                SocPopIn(u: u, start: 0.72, at: CGPoint(x: 258.5, y: 464.9 - 6)) { SocTwoLines(text: "Contest with others!", centreX: 258.5, baselines: [464.9], box: 250, hotHex: 0xF6E9D8) }
                SocPopIn(u: u, start: 0.88, at: CGPoint(x: 229.2 + 36.7 / 2, y: 498.8 + 37.7 / 2)) {
                    ArtImage(art: .pointerArrowYellow).scaleEffect(x: -1, y: 1)
                        .placed(CGRect(226 - CGFloat(bob) * 0.6, 505 + CGFloat(bob) * 0.6, 40, 45))
                }
                SocPopIn(u: u, start: 0.88, at: CGPoint(x: 128.4, y: 567)) {
                    ZStack {
                        ArtImage(art: .coinPileSmall).frame(width: 110, height: 90).offset(x: -40, y: 8)
                        ArtImage(art: .coinPileSmall).frame(width: 110, height: 90).offset(x: 42, y: 10)
                        ArtImage(art: .coinPileSmall).frame(width: 120, height: 98).offset(y: -8)
                    }
                    .frame(width: 191.5, height: 83.7)
                    .position(x: 128.4, y: 567)
                }
                SocPopIn(u: u, start: 0.88, at: CGPoint(x: 128.4, y: 642.4 - 6)) { SocTwoLines(text: "Win Rewards!", centreX: 128.4, baselines: [642.4], box: 180, hot: "Rewards!") }
                SocPopIn(u: u, start: 1.0, at: CGPoint(x: 28.7 + 57.0 / 2, y: 686.2 + 53.4 / 2)) { ArtImage(art: .navCup).placed(CGRect(28.7, 686.2, 57.0, 53.4)) }
                SocPopIn(u: u, start: 1.0, at: CGPoint(x: 96, y: 712.4 - 6)) {
                    SocInfoLine(text: "The top 3 win prizes!", centreX: 96, baseline: 712.4, size: 16, maxWidth: 280, alignLeft: true)
                }
                SocPopIn(u: u, start: 1.0, at: CGPoint(x: 96, y: 731.1 - 6)) {
                    SocInfoLine(text: "There is a new contest every week!", centreX: 96, baseline: 731.1, size: 16, maxWidth: 280, alignLeft: true)
                }
                if u >= 1.10 { SocTapTo(text: "Tap to Continue", baseline: 793.8).opacity(min(1, (u - 1.10) / 0.15)) }
            }
            .frame(width: 393, height: 852)
        }
        .contentShape(Rectangle())
        .onTapGesture { answer(PopupResult.close) }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("weekly.info")
        .onAppear {
            shownAt = app.clock.gameTime()
            if !app.store.state.flags.weeklyIntroSeen {
                Task { @MainActor in app.store.mutateAndSave { $0.flags.weeklyIntroSeen = true } }
            }
        }
    }
}

/// The info overlay's mini podium: our podium art at 0.57 with three portraits and the store's marketing names and prizes
/// (static, never translated; SPEC-ui §2.15.6).
private struct SocMiniPodium: View {
    var body: some View {
        let k: CGFloat = 0.57
        let name = GameTextStyle.s2(14, -0.2, [0xF6E9D8], outline: 0x7D0C02, 1.2, drop: 0.5)
        let lilacName = GameTextStyle.s2(14, -0.2, [0xEBF6F2], outline: 0x153032, 1.2, drop: 0.5)
        let amt = GameTextStyle.s2(9.5, -0.2, [0xF6E9D8], outline: 0x7D0C02, 0.9, drop: 0.3)
        // VERIFIED meta-017: the portraits stand on the blocks, names / bowls on the fronts (frame 148.1 · 305 · 220.9 · 160)
        let slots: [(String, Int, Int, CGRect, CGFloat, Bool)] = [
            ("Max", 1000, 2, CGRect(19, 20, 50, 50), 101, true),
            ("Neo", 2000, 5, CGRect(87, 3, 48, 48), 87, false),
            ("James", 500, 6, CGRect(159, 30, 48, 48), 105, false),
        ]
        ZStack(alignment: .topLeading) {
            ArtImage(art: .cupPodium).placed(CGRect(0, 160 - 206 * k, 389 * k, 206 * k))
            ForEach(0..<slots.count, id: \.self) { i in
                let s = slots[i]
                SocAvatar(index: s.2).placed(s.3)
                GameText(verbatim: s.0, style: s.5 ? lilacName : name, maxWidth: 60).at(s.3.midX, name.capCentre(baseline: s.4))
                ArtImage(art: .coinBowl).placed(CGRect(s.3.midX - 19, s.4 + 7, 38, 32))
                GameText(verbatim: "\(s.1)", style: amt, maxWidth: 30).at(s.3.midX, amt.capCentre(baseline: s.4 + 33))
            }
        }
        .frame(width: 220.9, height: 160, alignment: .topLeading)
    }
}

struct SocWeeklyResult: View {
    let rank: Int
    let prize: Int
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?

    var body: some View {
        TimelineView(.animation(minimumInterval: nil, paused: shownAt.map { app.clock.gameTime() - $0 > 1.2 } ?? true)) { ctx in
            let u = shownAt.map { app.clock.gameTime(ctx.date) - $0 } ?? 0
            let gold = rank >= 1 && rank <= 3
            let title: GameTextStyle = gold ? .s2(45.2, -0.8, [0xFFDD13, 0xFFC302, 0xFFB700], outline: 0xB24900, 0.9, drop: 1.8)
                                            : .s2(42, -1.0, [0xEBF6F2], outline: 0x00373B, 1.0, drop: 4.8)
            let line = GameTextStyle.s2(26, -0.5, [0xFFFFFF], outline: 0x00373B, 1.4, drop: 1.2)
            let k = min(1, u / 0.8)
            ZStack(alignment: .topLeading) {
                Color.clear
                GameText("Weekly Cup", style: title, maxWidth: 360).at(196.5, title.capCentre(baseline: 187.4))
                SocPopIn(u: u, start: 0.10, duration: 0.30, overshoot: 1.15, at: CGPoint(x: 196.5, y: 330)) {
                    ZStack {
                        if gold {
                            ArtImage(art: rank == 1 ? .rankBadgeGold : rank == 2 ? .rankBadgeSilver : .rankBadgeBronze)
                            GameText(verbatim: "\(rank)", style: .s2(32, 0, [0xFFFFFF], outline: rank == 1 ? 0x985316 : rank == 2 ? 0x325653 : 0x8C2D18, 2.2, drop: 1.0))
                        } else {
                            GameText(verbatim: "\(rank)", style: .s2(44, 0, [0xFFFAEF], outline: 0x002226, 2.6, drop: 1.0))
                        }
                    }
                    .frame(width: 64, height: 64)
                    .position(x: 196.5, y: 330)
                }
                GameText("You finished #\(rank)!", style: line, maxWidth: 300).at(196.5, line.capCentre(baseline: 479))
                if prize > 0 {
                    ArtImage(art: .coinPileSmall).placed(CGRect(158.5, 512, 76.7, 60.1))
                    let am = GameTextStyle.s2(27.6, -0.31, [0xFFFFFF], outline: 0x002226, 2.7, drop: 0.2)
                    GameText(verbatim: "\(Int(Double(prize) * (1 - (1 - k) * (1 - k))))", style: am, maxWidth: 120)
                        .at(196.8, am.capCentre(baseline: 590))
                }
                let tap = GameTextStyle.s2(31.5, -0.48, [0xFFFFFF], outline: 0x56092E, 1.2, drop: 1.2)
                GameText("Tap to Continue", style: tap, maxWidth: 330).at(196.5, tap.capCentre(baseline: 701.9))
            }
            .frame(width: 393, height: 852)
        }
        .contentShape(Rectangle())
        .onTapGesture { answer(PopupResult.primary) }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("weekly.result")
        .accessibilityValue(Text(verbatim: "\(rank)"))
        .onAppear { shownAt = app.clock.gameTime() }
    }
}
