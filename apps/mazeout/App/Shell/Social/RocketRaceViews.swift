import SwiftUI
import PathCore

// SOCIAL SOC2 (SPEC-ui §2.17 Rocket Race; SPEC-social §4.5, §14.2 (lane roles), D14; SPEC-motion-audio §9; VERIFIED 163-168,
// 171, 176, 178, 183, 184, 189). Three pieces:
//   SocRocketOffer    the offer popup (dim 0.90): the space panel + `rocketOfferScene`, the "Rocket Race" lettering, the
//                     countdown, the first offer's prize bubble (500 + ∞ 45m), the stage strip (Stage 1/2/3 planets, the
//                     current one lit) with "Beat N Levels before others …", the framed green "Start" (+ ∞ on the day's first
//                     offer) and the X. Start → C3 join → the ∞ 30m claim → the tutorial (first join) → the race page.
//   SocRocketTutorial the first-join overlay (dim 0.95): Beat levels! → Finish race before others! → Win amazing rewards! →
//                     Advance to next stages for greater prizes! → Tap to Continue.
//   SocRocketPage     the race page (the event screen, and `rocketRace(.result)` as a popup page): the backdrop, the stage tag,
//                     the countdown, the lettering, the band text, five lanes (the player's red-yellow rocket in lane 1, the
//                     rivals in the world's order), each rocket at its progress with its counter bubble, the gold winged "1"
//                     over the leader, the name tiles. Lost / won: the winner's lane card (winged 1 + chest), the band text
//                     changes, the framed green "Continue".
// The lanes are C3's rivals exactly (the world's ◆ rocketRace call, the same one C3 judges the race by) + the player's C3
// progress; they refresh every 5 s while visible, the rockets rise to their new places in 0.60 s.

struct SocRocketOffer: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @Environment(\.socPrewarm) private var prewarm

    var body: some View {
        let t = app.tuning.ui.tokens
        let rules = ShellEconomy.rules(app)
        let status = Events.status(app.store.state, now: app.clock.wallClock(), rules: rules)
        let run = status.rocketRace
        let stage = run?.stage ?? 1
        let goal = run?.levels ?? rules.events.rocketRace.levels(stage: stage)
        let now = SocTime.now(app)
        let day = EventSchedule.day(now, rules.events.calendar)
        let firstToday = app.store.state.events.rocket.joinGrantDay != day
        let prize = rules.events.rocketRace.prize(stage: stage)
        ZStack(alignment: .topLeading) {
            Color.clear
            PopupPanelFrame(t: t).placed(CGRect(9.7, 180.2, 379.0, 527.1))
            ArtImage(art: .rallyOfferScene, contentMode: .fill)
                .frame(width: 330, height: 504)
                .clipShape(RoundedRectangle(cornerRadius: 34))
                .placed(CGRect(32, 188, 330, 504))
            SocRocketLettering(frame: CGRect(63.4, 114.1, 266.9, 126.1))
            if let end = run?.endsAt {                                    // FIX-2 B review (L28): ticks; no run = no chip
                EventTimerChip(text: Countdown.text(SocTime.left(end, now: now)), frame: CGRect(153.5, 233.5, 86.7, 29),
                               textID: "rocket.offer.timer", t: t, live: (ends: end, now: now))
            }
            if stage == 1 && firstToday && (prize.coins > 0 || prize.unlimitedLives > 0) {
                SocPrizeBubble(grant: prize).placed(CGRect(214.8, 333.6, 158.8, 83.4))
            }
            SocStageStrip(stage: stage, frame: CGRect(40.7, 453.7, 312.9, 107.4), goal: goal, space: true)
            FramedButton(id: "popup.rocketRace.primary", title: "Start", colors: .green, frame: CGRect(91.4, 575.2, 210.8, 86.7),
                         well: CGRect(79.9, 566.5, 233.8, 105.4), n: 4.6,
                         style: .s2(44.3, -3.4, [Skin.socialRocketRaceViewsSocRocketOfferStyle0], outline: Skin.socialRocketRaceViewsSocRocketOfferOutline, 2.0, drop: 2.0),
                         baseline: 634.0, centreX: firstToday ? 178 : 196.8, maxWidth: 130, t: t) {
                answer(PopupResult.primary)
                SocialFlows.startRocketRace(app)
            }
            if firstToday {
                ArtImage(art: .heartInfiniteSmall).placed(CGRect(236, 598, 46, 42)).allowsHitTesting(false)
            }
            PopupCloseButton(id: "popup.rocketRace.close", t: t) { answer(PopupResult.close) }
                .placed(CGRect(338.3, 176.5, 45, 45))
            WeekStartBanner(event: .rocketRace, onCanvas: true)                 // B1: the week-start page's ribbon
        }
        .frame(width: 393, height: 852)
        .onAppear {
            Log.mark("event", "rocketRace offer stage \(stage) (\(goal) levels)")
            if !prewarm { EventAnnounce.opened(app, .rocketRace) }             // B1: the home's NEW ribbon goes (not the Loading prewarm)
        }
    }
}

/// "Rocket" / "Race" in two lines with the rocket badge, tilted −4° (our lettering of the event name; MANIFEST route B1).
struct SocRocketLettering: View {
    let frame: CGRect
    var body: some View {
        ZStack(alignment: .topLeading) {
            // the blue badge behind the lettering (VERIFIED 163 / 167: a rounded plate, light rim, deep blue face)
            RoundedRectangle(cornerRadius: frame.height * 0.16).fill(Color(hex: Skin.socialRocketRaceViewsSocRocketLetteringFill))
                .frame(width: frame.width * 0.74, height: frame.height * 0.86).offset(x: frame.width * 0.05, y: frame.height * 0.07)
            RoundedRectangle(cornerRadius: frame.height * 0.14)
                .fill(LinearGradient(colors: [Color(hex: Skin.socialRocketRaceViewsSocRocketLetteringColors0), Color(hex: Skin.socialRocketRaceViewsSocRocketLetteringColors1)], startPoint: .top, endPoint: .bottom))
                .frame(width: frame.width * 0.74 - 5, height: frame.height * 0.86 - 5).offset(x: frame.width * 0.05 + 2.5, y: frame.height * 0.07 + 2.5)
            SocEventLogo(title: "Rocket Rally", frame: CGRect(0, 0, frame.width * 0.82, frame.height), size: frame.height * 0.42,
                         yellowFirst: false, twoLines: true)
            ArtImage(art: .rallyRocketMine).rotationEffect(.degrees(80))
                .placed(CGRect(frame.width * 0.72, frame.height * 0.44, frame.height * 0.34, frame.height * 0.48))
        }
        .rotationEffect(.degrees(-4))
        .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        .placed(frame)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("Rocket Rally"))
    }
}

/// The first offer's cream bubble: the coin bowl + amount "+" the ∞ heart + duration.
struct SocPrizeBubble: View {
    let grant: Grant
    var body: some View {
        let amount = GameTextStyle.s2(14.5, -0.3, [Skin.socialRocketRaceViewsSocPrizeBubbleAmount0], outline: Skin.socialRocketRaceViewsSocPrizeBubbleAmountOutline, 1.3, drop: 0.6)
        let dur = GameTextStyle.s2(12.5, -0.3, [Skin.socialRocketRaceViewsSocPrizeBubbleDur0], outline: Skin.socialRocketRaceViewsSocPrizeBubbleDurOutline, 1.2, drop: 0.5)
        let plus = GameTextStyle.s2(22, 0, [Skin.socialRocketRaceViewsSocPrizeBubblePlus0], outline: Skin.socialRocketRaceViewsSocPrizeBubblePlusOutline, 1.5)
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 10.7).fill(Color(hex: Skin.socialRocketRaceViewsSocPrizeBubbleFill)).offset(y: 1.5)
            RoundedRectangle(cornerRadius: 10.7).fill(Color(hex: Skin.socialRocketRaceViewsSocPrizeBubbleFillV2))
            if grant.coins > 0 {
                ArtImage(art: .coinBowl).placed(CGRect(8, 8, 66, 55))
                GameText(verbatim: "\(grant.coins)", style: amount, maxWidth: 48).at(41, amount.capCentre(baseline: 58))
            }
            GameText(verbatim: "+", style: plus).at(80, plus.capCentre(baseline: 50))
            if grant.unlimitedLives > 0 {
                ArtImage(art: .heartInfiniteSmall).placed(CGRect(94, 14, 52, 47))
                GameText(verbatim: SocGrantText.duration(grant.unlimitedLives), style: dur, maxWidth: 40).at(120, dur.capCentre(baseline: 60))
            }
        }
        .frame(width: 158.8, height: 83.4, alignment: .topLeading)
    }
}

enum SocGrantText {
    /// "30m", "45m", "1h", "1h 30m", "3h" (the claim / bubble durations, SPEC-ui §2.11).
    static func duration(_ s: TimeInterval) -> String {
        let m = Int(s / 60)
        if m < 60 { return String(localized: "\(m)m") }
        let h = m / 60, r = m % 60
        return r == 0 ? String(localized: "\(h)h") : String(localized: "\(h)h \(r)m")
    }
}

/// The stage strip (rr 21.7): three tiles "Stage 1/2/3" with their planets (Rocket) or chests (Sky Jump), the current stage lit
/// #008CFF, won stages checked; under them the navy rules strip "Beat N Levels before others …" / "Pass N Levels …".
struct SocStageStrip: View {
    let stage: Int
    let frame: CGRect
    let goal: Int
    /// true: the Rocket Race planets + rules; false: the Sky Jump chests + rules (purple tray).
    var space = true

    var body: some View {
        let label = GameTextStyle.s2(space ? 15.2 : 18, -0.46, [Skin.socialRocketRaceViewsSocStageStripLabel0], outline: Skin.socialRocketRaceViewsSocStageStripLabelOutline, space ? 1.3 : 1.8, drop: 0)
        let tileW = (frame.width - 8) / 3
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 21.7).fill(Color(hex: space ? Skin.socialRocketRaceViewsSocStageStripFillSpace : Skin.socialRocketRaceViewsSocStageStripFillNotSpace))
            ForEach(1...3, id: \.self) { s in
                let x = 4 + CGFloat(s - 1) * tileW
                ZStack(alignment: .topLeading) {
                    RoundedRectangle(cornerRadius: 14)
                        .fill(Color(hex: s == stage ? (space ? Skin.socialRocketRaceViewsSocStageStripFillStageSpace : Skin.socialRocketRaceViewsSocStageStripFillStageNotSpace) : (space ? Skin.socialRocketRaceViewsSocStageStripFillNotStageSpace : Skin.socialRocketRaceViewsSocStageStripFillNotStageNotSpace)))
                        .frame(width: tileW - 4, height: frame.height * 0.52)
                        .offset(x: 2, y: 4)
                    if space {
                        ArtImage(art: s == 1 ? .planetStage1 : s == 2 ? .planetStage2 : .planetStage3)
                            .frame(width: s == 3 ? 76 : 44, height: 44).position(x: tileW / 2, y: 26)
                    } else {
                        ArtImage(art: s == 1 ? .stageChestGreen : s == 2 ? .stageChestBlue : .stageChestPink)
                            .frame(width: 52, height: 39).position(x: tileW / 2, y: 26)
                        if s < stage { ArtImage(art: .iconCheck).frame(width: 39.4, height: 31.7).position(x: 30, y: 22) }
                    }
                    GameText("Stage \(s)", style: label, maxWidth: tileW - 10).at(tileW / 2, label.capCentre(baseline: frame.height * 0.47))
                }
                .frame(width: tileW, height: frame.height, alignment: .topLeading)
                .offset(x: x)
            }
            SocRulesText(space: space, goal: goal, width: frame.width - 20)
                .position(x: frame.width / 2, y: frame.height * 0.78)
        }
        .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        .placed(frame)
    }
}

/// "Beat 5 Levels before others to win and advance to next stages for greater prizes!" (Rocket) / "Pass 5 Levels in a row on
/// first try and advance to next stages!" (Sky Jump): 14.6 pt white outlined #0A2176, the "N Levels" run yellow #FFC400, two lines.
struct SocRulesText: View {
    let space: Bool
    let goal: Int
    let width: CGFloat
    var body: some View {
        let text: LocalizedStringResource = space ? "Beat \(goal) Levels before others to win and advance to next stages for greater prizes!"
                                                  : "Pass \(goal) Levels in a row on first try and advance to next stages!"
        SocTwoLines(text: text, centreX: width / 2 + 10, baselines: [-4, 13.5], box: width, size: 14.6, faceHex: Skin.socialRocketRaceViewsSocRulesTextFaceHex,
                    hotHex: Skin.socialRocketRaceViewsSocRulesTextHotHex, outline: Skin.socialRocketRaceViewsSocRulesTextOutline, hot: "\(goal) Levels")
            .frame(width: width + 20, height: 1)
    }
}

// MARK: - tutorial

struct SocRocketTutorial: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?

    var body: some View {
        TimelineView(.animation(minimumInterval: nil, paused: shownAt.map { app.clock.gameTime() - $0 > 1.4 } ?? true)) { ctx in
            let u = shownAt.map { app.clock.gameTime(ctx.date) - $0 } ?? 0
            ZStack(alignment: .topLeading) {
                Color.clear
                SocPopIn(u: u, start: 0.18, duration: 0.10, overshoot: 1.10, at: CGPoint(x: 196.8, y: 83.2 - 13)) { SocInfoTitle(title: "Rocket Rally", baseline: 83.2) }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 45 + 113 / 2, y: 119 + 113 / 2)) { ArtImage(art: .infoPathIcon).placed(CGRect(45, 119, 113, 113)) }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 100, y: 248 - 6)) { SocTwoLines(text: "Beat levels!", centreX: 100, baselines: [248], box: 170) }
                SocPopIn(u: u, start: 0.50, at: CGPoint(x: 200 + 38 / 2, y: 160 + 41 / 2)) { ArtImage(art: .pointerArrowYellow).placed(CGRect(196, 145, 40, 45)) }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 255 + 80 / 2, y: 200 + 115 / 2)) { ArtImage(art: .rallyRocketMine).placed(CGRect(255, 200, 80, 115)) }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 295, y: 330 - 6)) {
                    SocTwoLines(text: "Finish race before others!", centreX: 295, baselines: [330, 349.5], box: 150, greedy: true)
                }
                SocPopIn(u: u, start: 0.66, at: CGPoint(x: 245 + 38 / 2, y: 375 + 41 / 2)) { ArtImage(art: .pointerArrowYellow).scaleEffect(x: -1, y: 1).placed(CGRect(242, 318, 40, 45)) }
                SocPopIn(u: u, start: 0.72, at: CGPoint(x: 104.5, y: 412.5)) {
                    ZStack {
                        ArtImage(art: .coinPileSmall).frame(width: 110, height: 86).offset(x: -46, y: 20)
                        ArtImage(art: .coinPileSmall).frame(width: 110, height: 86).offset(x: 52, y: 22)
                        ArtImage(art: .stageChestPink).frame(width: 112, height: 84).offset(y: -10)
                    }
                    .frame(width: 193, height: 115)
                    .position(x: 104.5, y: 412.5)
                }
                SocPopIn(u: u, start: 0.72, at: CGPoint(x: 107, y: 494 - 6)) {
                    SocTwoLines(text: "Win amazing rewards!", centreX: 107, baselines: [494], box: 280, hot: "rewards")
                }
                SocPopIn(u: u, start: 0.80, at: CGPoint(x: 118 + 38 / 2, y: 525 + 41 / 2)) { ArtImage(art: .pointerArrowYellow).placed(CGRect(118, 540, 40, 45)) }
                SocPopIn(u: u, start: 0.88, at: CGPoint(x: 281, y: 580)) {
                    ZStack(alignment: .topLeading) {
                        ArtImage(art: .planetStage1).placed(CGRect(0, 50, 44, 44))
                        ArtImage(art: .planetStage2).placed(CGRect(50, 28, 52, 52))
                        ArtImage(art: .planetStage3).placed(CGRect(86, 0, 104, 60))
                    }
                    .frame(width: 190, height: 100, alignment: .topLeading)
                    .placed(CGRect(186, 530, 190, 100))
                }
                SocPopIn(u: u, start: 0.88, at: CGPoint(x: 270, y: 652 - 6)) {
                    SocTwoLines(text: "Advance to next stages for greater prizes!", centreX: 270, baselines: [652, 671.5], box: 230, hot: "prizes")
                }
                if u >= 1.10 { SocTapTo(text: "Tap to Continue", baseline: 793.4).opacity(min(1, (u - 1.10) / 0.15)) }
            }
            .frame(width: 393, height: 852)
        }
        .contentShape(Rectangle())
        .onTapGesture { answer(PopupResult.close) }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("rocket.tutorial")
        .onAppear { shownAt = app.clock.gameTime() }
    }
}

// MARK: - the race page

struct SocRocketPage: View {
    @Environment(\.socPrewarm) private var prewarm
    /// As the result popup page (`rocketRace(.result)`): Continue answers it.
    var answer: PopupAnswer? = nil
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let model = SocialModel.install(app)
        let t = app.tuning.ui.tokens
        let snap = model.rocket
        let now = SocTime.now(app)
        // an ended race with no saved run (a save from before C3 kept `lastRun`): the result text + Continue, no lanes
        let result = snap?.result ?? (app.store.state.events.rocket.active == nil ? (app.store.state.events.rocket.lastResult?.rawValue ?? "none") : "none")
        let ended = result != "none"
        ZStack(alignment: .topLeading) {
            Color(hex: Skin.socialRocketRaceViewsSocRocketPage).frame(width: m.size.width, height: m.size.height)
            ArtImage(art: .rallyBackdrop, contentMode: .fill).frame(width: m.size.width, height: m.size.height).clipped()
            ReferenceCanvas {
                ZStack(alignment: .topLeading) {
                    SocStageTag(stage: snap?.stage ?? 1).placed(CGRect(0, 196.2, 61.4, 23.4))
                    if let end = snap?.endsAt {                           // FIX-2 B review (L28): ticks; no race = no chip
                        EventTimerChip(text: Countdown.text(SocTime.left(end, now: now)), frame: CGRect(318.9, 190.2, 74.1, 36.7),
                                       textID: "rocket.timer", t: t, live: (ends: end, now: now))
                    }
                    LinearGradient(colors: [Color(hex: Skin.socialRocketRaceViewsSocRocketPageColors0), Color(hex: Skin.socialRocketRaceViewsSocRocketPageColors1)], startPoint: .top, endPoint: .bottom)
                        .placed(CGRect(0, 226.9, 393, 110.1))
                    SocRails().placed(CGRect(0, 226.9, 393, 16))
                    SocRocketLettering(frame: CGRect(93.4, 166.8, 203.5, 106.8))
                    SocRocketBandText(result: result, goal: snap?.goal ?? ShellEconomy.rules(app).events.rocketRace.levels(stage: 1))
                        .frame(width: 393, height: 110).placed(CGRect(0, 226.9, 393, 110.1))
                    SocRocketLanes(snap: snap)
                    if ended {
                        LinearGradient(colors: [Color(hex: Skin.socialRocketRaceViewsSocRocketPageColors0V2), Color(hex: Skin.socialRocketRaceViewsSocRocketPageColors1V2)], startPoint: .top, endPoint: .bottom)
                            .placed(CGRect(0, 717.3, 393, 135.4))
                        FramedButton(id: "event.rocketRace.continue", title: "Continue", colors: .green,
                                     frame: CGRect(91.4, 741.3, 210.5, 86.4), well: CGRect(80.0, 732.6, 233.3, 104.1), n: 4.6,
                                     style: .s2(38.9, 0.05, [Skin.socialRocketRaceViewsSocRocketPageStyle0, Skin.socialRocketRaceViewsSocRocketPageStyle1], outline: Skin.socialRocketRaceViewsSocRocketPageOutline, 2.0, drop: 2.0),
                                     baseline: 798.0, centreX: 196.6, maxWidth: 172, t: t) { finish() }
                    }
                }
                .frame(width: 393, height: 852, alignment: .topLeading)
            }
            // (i) → the tutorial; X → home (SPEC-ui §2.17.3: (i) (25.4, 70.1), X (355.3, 72.1))
            GameButton(id: "rocket.info", label: "Info", action: {
                Task { @MainActor in
                    _ = await app.popups.present(Popup<PopupResult>(.rocketRace(.tutorial),
                                                                    style: PopupStyle(dim: .info, closesOnTapAnywhere: true), fallback: .close))
                }
            }) { SocInfoDisc() }
            .placed(m.rect(CGRect(5.3, 50.0, 40, 40), .top))
            if !ended {
                PopupCloseButton(id: "event.rocketRace.close", t: t, halo: true) { finish() }
                    .placed(m.rect(CGRect(332.8, 49.6, 45, 45), .top))
            }
            SocReadyWhen(ready: snap != nil || ended, name: "event:rocketRace")
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .clipped()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("page.rocketRace")
        .onAppear {
            guard !prewarm else { return }
            model.appear(.rocket)
            model.probeOpen("rocketRace")
            SocialFlows.refreshEvents(app) { model.request(.rocket) }
            Log.mark("event", "rocketRace page visible (\(snap?.result ?? "no race"))")
        }
        .onDisappear { if !prewarm { model.disappear(.rocket) } }
    }

    private func finish() {
        if let answer { answer(PopupResult.primary); return }
        let won = SocialModel.shared?.rocket?.result == "won"
        EventPageShell<EmptyView>.close(app)
        guard won else { return }
        // the stage prize, then the next stage's offer at once (SPEC-social §4.5)
        Task { @MainActor in
            await SocialFlows.claimAll(app, kinds: [.rocketPrize])
            let st = Events.status(app.store.state, now: app.clock.wallClock(), rules: ShellEconomy.rules(app))
            if st.rocketRace?.joinable == true { _ = await app.popups.present(Popup<PopupResult>.rocketRace(.offer)) }
        }
    }
}

/// The yellow "Stage 1" tab flush left (15.2 pt #622200 plain).
struct SocStageTag: View {
    let stage: Int
    var body: some View {
        let st = GameTextStyle.s2(15.2, -0.85, [Skin.socialRocketRaceViewsSocStageTagSt0])
        ZStack {
            UnevenRoundedRectangle(topLeadingRadius: 0, bottomLeadingRadius: 0, bottomTrailingRadius: 9, topTrailingRadius: 9)
                .fill(LinearGradient(colors: [Color(hex: Skin.socialRocketRaceViewsSocStageTagColors0), Color(hex: Skin.socialRocketRaceViewsSocStageTagColors1)], startPoint: .top, endPoint: .bottom))
            GameText("Stage \(stage)", style: st, maxWidth: 56)
        }
    }
}

/// The band sentence: racing "Beat N levels before others to finish the race", lost / won lines (19.7 / −0.4 white outlined
/// #0F2C80 1.3, the "N levels" run yellow; baselines 292.3 / 314.4; box 345).
private struct SocRocketBandText: View {
    let result: String
    let goal: Int
    var body: some View {
        let text: LocalizedStringResource
        switch result {
        case "lost", "expired": text = "You lost the race! Try again to win amazing rewards!"
        case "won": text = "You won the race! Claim your amazing rewards!"
        default: text = "Beat \(goal) levels before others to finish the race"
        }
        return SocTwoLines(text: text, centreX: 196.5, baselines: [292.3 - 226.9, 314.4 - 226.9], box: 362, size: 19.7,
                           faceHex: Skin.socialRocketRaceViewsSocRocketBandTextFaceHex, hotHex: result == "none" ? Skin.socialRocketRaceViewsSocRocketBandTextHotHexResult : Skin.socialRocketRaceViewsSocRocketBandTextHotHexNotResult, outline: Skin.socialRocketRaceViewsSocRocketBandTextOutline,
                           hot: "\(goal) levels", greedy: true)
    }
}

/// Five lanes: dividers, rockets at their progress (top = 630.5 − 44.5·n while racing), counter bubbles, the leader's winged
/// "1", the name tiles; after the race the winner's lane card with the chest (183).
private struct SocRocketLanes: View {
    let snap: SocRocketSnap?
    @State private var shown: [Int] = []
    @State private var animFrom: [Int] = []
    @State private var animStart: Double = 0
    @Environment(AppModel.self) private var app

    var body: some View {
        let lanes = snap?.lanes ?? []
        let ended = (snap?.result ?? "none") != "none"
        let goal = snap?.goal ?? 5
        let centres: [CGFloat] = [39.3, 117.9, 196.5, 275.1, 353.7]
        let tileTop: CGFloat = ended ? 617 : 751.6
        TimelineView(.animation(minimumInterval: nil, paused: app.clock.gameTime() - animStart > 0.7)) { ctx in
            let u = min(1, max(0, (app.clock.gameTime(ctx.date) - animStart) / 0.60))
            let e = u < 0.5 ? 2 * u * u : 1 - pow(-2 * u + 2, 2) / 2
            ZStack(alignment: .topLeading) {
                ForEach(1..<5, id: \.self) { i in
                    Color(hex: Skin.socialRocketRaceViewsSocRocketLanes).frame(width: 2, height: 515).position(x: CGFloat(i) * 78.6, y: 336.9 + 257.5)
                }
                ForEach(Array(lanes.prefix(5).enumerated()), id: \.offset) { i, lane in
                    let cx = centres[i]
                    let from = i < animFrom.count ? Double(animFrom[i]) : Double(lane.progress)
                    let p = from + (Double(lane.progress) - from) * e
                    let winner = ended && lane.progress >= goal && !lane.isMe && snap?.result != "won"
                        || ended && lane.isMe && snap?.result == "won"
                    let top: CGFloat = ended ? 515 - 19.5 * CGFloat(p) : 630.5 - 44.5 * CGFloat(p)
                    if winner {
                        SocWinnerCard().placed(CGRect(cx - 36.7, 333.6, 73.4, 93.4))
                    } else {
                        ArtImage(art: lane.isMe ? .rallyRocketMine : .rallyRocketOther).placed(CGRect(cx - 36.5, top, 73, 103.4))
                        SocCounterBubble(n: lane.progress).placed(CGRect(cx - 17, top - 26.6, 34, 31.7))
                    }
                    if !ended && lane.rank == 1 && lane.progress > 0 {
                        ZStack {
                            ArtImage(art: .rankWings1)
                            GameText(verbatim: "1", style: .s2(20, 0, [Skin.socialRocketRaceViewsSocRocketLanesStyle0], outline: Skin.socialRocketRaceViewsSocRocketLanesOutline, 1.6, drop: 0.8))
                                .offset(y: -0.8)
                        }
                        .placed(CGRect(cx - 26, 339.0, 52, 38))
                    }
                    SocNameTile(player: lane.player, me: lane.isMe).placed(lane.isMe
                        ? CGRect(cx - 32.85, tileTop - 3, 65.7, 88.4) : CGRect(cx - 29.7, tileTop, 59.4, 82.4))
                        .accessibilityElement(children: .ignore)
                        .accessibilityIdentifier("event.rocketRace.lane.\(i)")
                        .accessibilityLabel(Text(verbatim: lane.player.name))
                        .accessibilityValue(Text(verbatim: "\(lane.progress)/\(goal)"))
                }
            }
            .frame(width: 393, height: 852, alignment: .topLeading)
        }
        .onAppear { shown = lanes.map(\.progress); animFrom = shown; animStart = app.clock.gameTime() }
        .onChange(of: lanes.map(\.progress)) { old, new in
            animFrom = old.count == new.count ? old : new
            shown = new
            animStart = app.clock.gameTime()
        }
    }
}

/// The cream counter bubble over a rocket (digit 18 pt #0F2C80).
private struct SocCounterBubble: View {
    let n: Int
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 6).fill(Color(hex: Skin.socialRocketRaceViewsSocCounterBubbleFill)).offset(y: 1)
            RoundedRectangle(cornerRadius: 6).fill(Color(hex: Skin.socialRocketRaceViewsSocCounterBubbleFillV2))
            GameText(verbatim: "\(n)", style: .s2(18, 0, [Skin.socialRocketRaceViewsSocCounterBubbleStyle0]))
        }
    }
}

/// The winner's lane card: the gold winged "1" over a chest (183).
private struct SocWinnerCard: View {
    var body: some View {
        ZStack(alignment: .top) {
            RoundedRectangle(cornerRadius: 10).fill(Color(hex: Skin.socialRocketRaceViewsSocWinnerCardFill)).offset(y: 2)
            RoundedRectangle(cornerRadius: 10).fill(Color(hex: Skin.socialRocketRaceViewsSocWinnerCardFillV2))
            ZStack {
                ArtImage(art: .rankWings1)
                GameText(verbatim: "1", style: .s2(18, 0, [Skin.socialRocketRaceViewsSocWinnerCardStyle0], outline: Skin.socialRocketRaceViewsSocWinnerCardOutline, 1.5, drop: 0.7))
            }
            .frame(width: 50, height: 36).offset(y: 5)
            ArtImage(art: .stageChestBlue).frame(width: 60, height: 45).offset(y: 42)
        }
    }
}

/// A name tile under a lane: cream (the player's green), the portrait (44 pt frame) and the name (9-15 pt #622200, box 52).
struct SocNameTile: View {
    let player: SimPlayer
    let me: Bool
    var body: some View {
        let st = GameTextStyle.s2(15.3, -0.4, [me ? Skin.socialRocketRaceViewsSocNameTileStMe0 : Skin.socialRocketRaceViewsSocNameTileStNotMe0], outline: me ? Skin.socialRocketRaceViewsSocNameTileStOutlineMe : nil, me ? 1.2 : 0)
        GeometryReader { geo in
            ZStack(alignment: .top) {
                RoundedRectangle(cornerRadius: 12).fill(Color(hex: me ? Skin.socialRocketRaceViewsSocNameTileFillMe : Skin.socialRocketRaceViewsSocNameTileFillNotMe)).offset(y: 2)
                RoundedRectangle(cornerRadius: 12)
                    .fill(LinearGradient(colors: me ? [Color(hex: Skin.socialRocketRaceViewsSocNameTileColorsMe0), Color(hex: Skin.socialRocketRaceViewsSocNameTileColorsMe1)] : [Color(hex: Skin.socialRocketRaceViewsSocNameTileColorsNotMe0), Color(hex: Skin.socialRocketRaceViewsSocNameTileColorsNotMe1)],
                                         startPoint: .top, endPoint: .bottom))
                SocAvatar(index: player.avatar, me: me).frame(width: 44, height: 44).offset(y: 7)
                GameText(verbatim: player.name, style: { var x = st; x.minScale = 0.5; return x }(), maxWidth: min(54, geo.size.width - 6))
                    .position(x: geo.size.width / 2, y: geo.size.height - 16)
            }
        }
    }
}
