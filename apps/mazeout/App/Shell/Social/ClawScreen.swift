import SwiftUI
import PathCore

// SOCIAL SOC2 (SPEC-ui §2.19 Claw Challenge; uim `claw.*`, `clawInfo.*`; SPEC-gameplay §11.2 (the ladder, C3's EconomyRules);
// SPEC-social §4.7; SPEC-motion-audio §9; VERIFIED 021-025, meta-039..044, 103). The Claw Challenge page (the home Claw bar →
// `Screen.event(.claw)`) and its (i) overlay:
//   header `clawHeaderArt` 0 · 0 · 393 · 243.5, (i), X; "Claw Challenge" lettering 43.4 · 208.5 · 306.9 · 58.4; the band
//   0 · 233.5 · 393 · 200.2 (#2569F3, gold rails): the countdown chip, the subtitle, the chevron chips x1 … x100 (the current
//   multiplier lit orange-gold), the progress bar (hex token, "n/target", the next reward); then the 20-step ladder (scrolls,
//   navy ground): a rail with numbered nodes (locked lilac / next with a glow / done gold) and reward cards (∞ + duration,
//   coins, boosters; a padlock on locked cards, a green check on done ones), node pitch 121.8, step 1 at the bottom.
// The first open auto-scrolls from step 1 to step 20 in 1.8 s (easeInOutSine); later opens centre the current step.
// Everything is C3's Claw state (`Events.status(…).claw`), read-only here; claims are made on home (GAME).
// B1b (v582 PH-0a): opened from the home's "Finished" bar, the page shows the ENDED week's ladder as it stood (the chip reads
// "Finished") — opening it is opening the result: C3 drops the hold, and the home shows this week's ladder event on return.

struct SocClawPage: View {
    @Environment(\.socPrewarm) private var prewarm
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m
    @State private var appearedAt: Double?
    /// B1b: the ended week's bar this page opened on (kept after its hold was dropped at the open).
    @State private var held: Events.ClawStatus?

    var body: some View {
        let t = app.tuning.ui.tokens
        let rules = ShellEconomy.rules(app)
        let status = Events.status(app.store.state, now: app.clock.wallClock(), rules: rules)
        let ended = held ?? status.finished.claw
        let claw = ended ?? status.claw
        let now = SocTime.now(app)
        let k = m.s
        ZStack(alignment: .topLeading) {
            Color(hex: 0x003135).frame(width: m.size.width, height: m.size.height)
            SocClawLadder(ladder: rules.claw.ladder, doneSteps: (claw?.step ?? 1) - 1, complete: claw?.complete ?? false,
                          firstOpen: !app.store.state.flags.seen.contains("social.clawLadder"))
                .frame(width: 393, height: (m.size.height - 433.7 * k) / k)
                .scaleEffect(k, anchor: .topLeading)
                .frame(width: m.size.width, height: m.size.height - 433.7 * k, alignment: .topLeading)
                .offset(y: 433.7 * k)
            ZStack(alignment: .topLeading) {
                ArtImage(art: .treasureHeader, contentMode: .fill).placed(CGRect(0, 0, 393, 243.5)).clipped()
                LinearGradient(colors: [Color(hex: 0x008680), Color(hex: 0x00807B)], startPoint: .top, endPoint: .bottom)
                    .placed(CGRect(0, 233.5, 393, 200.2))
                SocRails(gold: true).placed(CGRect(0, 233.5, 393, 14))
                SocEventLogo(title: "Treasure Climb", frame: CGRect(43.4, 208.5, 306.9, 58.4), size: 40)
                // FIX-2 B review (L28): the chip ticks on its own (`LiveCountdown`); with no ladder of this player's to count
                // down (the Claw is not this week's event: a debug `-pc.go`), no chip — not a stale "00:00"
                if ended != nil {
                    EventTimerChip(text: EventWord.finished, frame: CGRect(162.8, 262.9, 67.7, 23), textID: "claw.timer", t: t)
                } else if let end = claw?.endsAt ?? (status.live.ladder == .clawChallenge ? status.week?.end : nil) {
                    EventTimerChip(text: Countdown.text(SocTime.left(end, now: now)), frame: CGRect(162.8, 262.9, 67.7, 23),
                                   textID: "claw.timer", t: t, live: (ends: end, now: now))
                }
                let sub = GameTextStyle.s2(17.2, -0.27, [0xF8F0E9, 0xF6EADB, 0xF6E4CA], outline: 0x073A3E, 1.1, drop: 0.7)
                GameText("Beat levels without fail to get more rewards!", style: sub, maxWidth: 367).at(196.8, sub.capCentre(baseline: 306.5))
                SocChevronChips(steps: StreakStripSource.steps(app), lit: app.store.state.events.streakStep)
                    .placed(CGRect(18.3, 315.3, 347, 55))
                SocClawProgress(points: claw?.points ?? 0, target: claw?.target ?? 1, reward: claw?.nextReward)
                    .placed(CGRect(23.4, 380.3, 347, 41.7))
            }
            .frame(width: 393, height: 434, alignment: .topLeading)
            .scaleEffect(k, anchor: .topLeading)
            .frame(width: m.size.width, height: 434 * k, alignment: .topLeading)
            GameButton(id: "claw.info", label: "Info", action: {
                Task { @MainActor in _ = await app.popups.present(Popup<PopupResult>(.clawInfo, style: PopupStyle(dim: .unlock, closesOnTapAnywhere: true), fallback: .close)) }
            }) { SocInfoDisc() }
            .placed(m.rect(CGRect(4.7, 52.0, 40.4, 40.4), .top))
            PopupCloseButton(id: "event.claw.close", t: t, halo: true) { EventPageShell<EmptyView>.close(app) }
                .placed(m.rect(CGRect(333.0, 49.1, 45, 45), .top))
            ComingNextFooter()                                                 // B1: the last day's "Coming next" teaser
            WeekStartBanner(event: .clawChallenge)                             // B1: the week-start page's ribbon
            SocReadyWhen(ready: true, name: "event:claw")
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .clipped()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("page.claw")
        .accessibilityValue(Text(verbatim: ended != nil ? "finished" : "live"))
        .onAppear {
            guard !prewarm else { return }
            Log.mark("event", "claw page visible (\(claw?.accessibilityValue ?? "locked")\(ended != nil ? ", the ended week" : ""))")
            if let ended {
                held = ended                                                   // B1b: the result is opened: the hold goes
                EventFinish.open(app, .clawChallenge)
            } else {
                EventAnnounce.opened(app, .clawChallenge)                      // B1: the home's NEW ribbon goes
            }
            SocialModel.install(app).probeOpen("claw")
            if !app.store.state.flags.seen.contains("social.clawLadder") {
                Task { @MainActor in
                    try? await Task.sleep(nanoseconds: 2_200_000_000)
                    app.store.mutateAndSave { _ = $0.flags.seen.insert("social.clawLadder") }
                }
            }
        }
    }
}

/// The chevron chips (blue arrows #00A2FC → #008CFD on a dark track #031A6F; the lit one orange-gold #FED902 → #FFB700, rim
/// #FF7A00, `role.chipLabelLit`).
struct SocChevronChips: View {
    let steps: [Int]
    let lit: Int

    var body: some View {
        GeometryReader { geo in
            let n = max(1, steps.count)
            let w = geo.size.width / CGFloat(n), h = geo.size.height
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 8).fill(Color(hex: 0x002B2E))
                ForEach(0..<n, id: \.self) { i in
                    let on = i == min(lit, n - 1)
                    SocChevron(on: on, first: i == 0)
                        .frame(width: w + 8, height: h - 6)
                        .position(x: w * (CGFloat(i) + 0.5), y: h / 2)
                    let st: GameTextStyle = on ? .s2(25.7, -1.6, [0xFFFFFF], outline: 0x7D0C02, 1.8, drop: 0.9)
                                               : .s2(22.4, -0.8, [0xFFFFFF], outline: 0x00383C, 1.5, drop: 0.8)
                    GameText(verbatim: "x\(steps[i])", style: st, maxWidth: w - 8).position(x: w * (CGFloat(i) + 0.5) + 3, y: h / 2)
                }
            }
        }
        .accessibilityElement()
        .accessibilityIdentifier("claw.multiplier")
        .accessibilityValue(Text(verbatim: "x\(steps.indices.contains(lit) ? steps[lit] : 1)"))
    }
}

private struct SocChevron: View {
    let on: Bool
    let first: Bool
    var body: some View {
        Rasterized("chev|\(on)|\(first)") { size in
            let shape = SocChevronShape(first: first)
            ZStack {
                shape.fill(Color(hex: on ? 0xFF7A00 : 0x0E4B4E))
                shape.fill(LinearGradient(colors: on ? [Color(hex: 0xFED902), Color(hex: 0xFFB700)] : [Color(hex: 0x29AD9E), Color(hex: 0x009C8F)],
                                          startPoint: .top, endPoint: .bottom))
                    .padding(2)
            }
        }
    }
}

private struct SocChevronShape: Shape {
    let first: Bool
    func path(in r: CGRect) -> Path {
        var p = Path()
        let tip: CGFloat = r.height * 0.28
        p.move(to: CGPoint(x: r.minX + (first ? 0 : 0), y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX - tip, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX, y: r.midY))
        p.addLine(to: CGPoint(x: r.maxX - tip, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX, y: r.maxY))
        if !first { p.addLine(to: CGPoint(x: r.minX + tip, y: r.midY)) }
        p.closeSubpath()
        return p
    }
}

/// The progress bar: frame #019CFB, navy track #082894, green fill #77EE28 (rr 6.8), "n/target" 21.2 white outlined #061E79,
/// the hex token at the left, the next reward at the right (uim `claw.progress*`).
private struct SocClawProgress: View {
    let points: Int
    let target: Int
    let reward: Grant?
    var body: some View {
        let st = GameTextStyle.s2(21.2, 0.63, [0xFFFFFF], outline: 0x003034, 1.0, drop: 0.6)
        let f = CGFloat(min(1, Double(points) / Double(max(1, target))))
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 10).fill(Color(hex: 0x1FA899)).frame(width: 347, height: 41.7)
            RoundedRectangle(cornerRadius: 8).fill(Color(hex: 0x003D42)).frame(width: 295, height: 29).offset(x: 26, y: 6.3)
            RoundedRectangle(cornerRadius: 6.8).fill(Color(hex: 0xF7CF68)).frame(width: max(0, 291 * f), height: 25).offset(x: 28, y: 8.3)
            GameText(verbatim: "\(points)/\(target)", style: st, maxWidth: 200).position(x: 173.5, y: 20.8)
            ArtImage(art: .treasureToken).placed(CGRect(4.3, 3.4, 37.7, 35.4))
            if let reward { SocRewardIcon(grant: reward, small: true).placed(CGRect(303.5, -0.3, 40.4, 35.7)) }
        }
        .frame(width: 347, height: 41.7, alignment: .topLeading)
        .accessibilityElement()
        .accessibilityIdentifier("claw.progress")
        .accessibilityValue(Text(verbatim: "\(points)/\(target)"))
    }
}

/// A reward as the Claw draws it: ∞ heart + duration, coin bowl + amount, booster + "xN".
struct SocRewardIcon: View {
    let grant: Grant
    var small = false
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            ZStack {
                if grant.unlimitedLives > 0 {
                    ArtImage(art: small ? .heartInfiniteSmall : .heartInfinite).frame(width: w, height: h * 0.9)
                    let st = GameTextStyle.s2(small ? 11 : 16, -0.3, [0xFFFFFF], outline: 0xAE190B, small ? 1.0 : 1.4, drop: 0.5)
                    GameText(verbatim: SocGrantText.duration(grant.unlimitedLives), style: st, maxWidth: w * 0.8).offset(y: h * 0.28)
                } else if grant.coins > 0 {
                    ArtImage(art: .coinBowl).frame(width: w, height: h * 0.9)
                    let st = GameTextStyle.s2(small ? 10.5 : 13.5, -0.2, [0xFFFFFF], outline: 0x7D0C02, small ? 1.0 : 1.3, drop: 0.5)
                    GameText(verbatim: "\(grant.coins)", style: st, maxWidth: w * 0.7).offset(y: h * 0.24)
                } else if let b = grant.boosters.first(where: { $0.value > 0 }) {
                    ArtImage(art: b.key == "freeze" ? .boosterFreeze : .boosterHint).frame(width: w * 0.8, height: h * 0.9)
                    let st = GameTextStyle.s2(small ? 11 : 15.2, 0, [0xFFFFFF], outline: 0x002226, 1.2, drop: 0.5)
                    GameText(verbatim: "x\(b.value)", style: st).offset(x: w * 0.28, y: h * 0.3)
                }
            }
            .frame(width: w, height: h)
        }
    }
}

/// The 20-step ladder (step 1 at the bottom). A SwiftUI list of 20 static cards: its views are built once on open.
private struct SocClawLadder: View {
    @Environment(\.socPrewarm) private var prewarm
    let ladder: [EconomyRules.ClawStep]
    let doneSteps: Int
    let complete: Bool
    let firstOpen: Bool
    @State private var scrolled = false

    var body: some View {
        let pitch: CGFloat = 121.8
        let n = ladder.count
        ScrollViewReader { proxy in
            ScrollView(.vertical, showsIndicators: false) {
                ZStack(alignment: .topLeading) {
                    // the rail (x 63.4-83.4, #00A6FC with #0035AE edges)
                    Color(hex: 0x004B4F).frame(width: 20, height: pitch * CGFloat(n) + 40).offset(x: 63.4)
                    Color(hex: 0x31B0A0).frame(width: 16, height: pitch * CGFloat(n) + 40).offset(x: 65.4)
                    ForEach(0..<n, id: \.self) { i in
                        let step = n - i                           // top → bottom: 20 … 1
                        let y = CGFloat(i) * pitch + 20
                        SocClawRow(step: step, grant: ladder[step - 1].grant,
                                   state: step <= doneSteps || (complete && step == n) ? .done : (step == doneSteps + 1 ? .next : .locked))
                            .frame(width: 393, height: pitch, alignment: .topLeading)
                            .offset(y: y)
                            .id(step)
                    }
                }
                .frame(width: 393, height: pitch * CGFloat(n) + 60, alignment: .topLeading)
            }
            .onAppear {
                guard !prewarm, !scrolled else { return }
                scrolled = true
                let current = min(n, doneSteps + 1)
                if firstOpen {
                    proxy.scrollTo(1, anchor: .bottom)
                    Task { @MainActor in
                        try? await Task.sleep(nanoseconds: 250_000_000)
                        withAnimation(.timingCurve(0.37, 0, 0.63, 1, duration: 1.8)) { proxy.scrollTo(n, anchor: .top) }
                    }
                } else {
                    proxy.scrollTo(current, anchor: .center)
                }
            }
        }
    }
}

private struct SocClawRow: View {
    enum StepState { case locked, next, done }
    let step: Int
    let grant: Grant
    let state: StepState

    var body: some View {
        let node = CGRect(46, 30, 54.7, 55.4)
        let card = CGRect(149.1, 18.3, 185.8, 78.7)
        let num = GameTextStyle.s2(26.1, 0, [0xFFFFFF], outline: state == .done ? 0x7D0C02 : 0x1A3132, state == .done ? 1.8 : 2.3, drop: 0.4)
        ZStack(alignment: .topLeading) {
            Color(hex: 0x095F5A).frame(width: card.minX - node.maxX + 4, height: 2).offset(x: node.maxX - 2, y: node.midY - 1)
            if state == .next {
                ArtImage(art: .sunburstRays).frame(width: 90, height: 90).position(x: node.midX, y: node.midY).opacity(0.8)
            }
            ZStack {
                Circle().fill(Color(hex: 0x10A898))
                Circle().fill(LinearGradient(colors: state == .done ? [Color(hex: 0xFFC400), Color(hex: 0xFF9A00)]
                                                                   : [Color(hex: 0x9ACFCC), Color(hex: 0x7DC2C0)],
                                             startPoint: .top, endPoint: .bottom))
                    .padding(4)
                GameText(verbatim: "\(step)", style: num)
            }
            .placed(node)
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 20).fill(Color(hex: 0x004B4F))
                RoundedRectangle(cornerRadius: 18).fill(Color(hex: 0x22A596)).padding(1.2)
                RoundedRectangle(cornerRadius: 16).fill(Color(hex: 0xF4E8D4)).padding(4)
                ArtImage(art: .sunburstRays).frame(width: 177.8, height: 70.7).clipShape(RoundedRectangle(cornerRadius: 16)).offset(x: 4, y: 4)
                if state == .done {
                    ArtImage(art: .iconCheck).frame(width: 53.7, height: 46.4).position(x: card.width / 2, y: card.height / 2)
                } else {
                    SocRewardIcon(grant: grant).frame(width: 74, height: 60).position(x: card.width / 2, y: card.height / 2)
                    ArtImage(art: .padlockGold).frame(width: 36.4, height: 44.7).position(x: card.width - 17, y: card.height - 12)
                }
            }
            .frame(width: card.width, height: card.height, alignment: .topLeading)
            .placed(card)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("event.claw.step.\(step)")
        .accessibilityValue(Text(verbatim: state == .done ? "done" : state == .next ? "next" : "locked"))
    }
}

// MARK: - (i)

/// The Claw (i) overlay (uim `clawInfo`, dim 0.90): the maze icon + "Beat levels without losing!", the chips +
/// "Increase your score multiplier!", the coins, "Tap to Continue"; staggered pops.
struct SocClawInfo: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?

    var body: some View {
        TimelineView(.animation(minimumInterval: nil, paused: shownAt.map { app.clock.gameTime() - $0 > 1.4 } ?? true)) { ctx in
            let u = shownAt.map { app.clock.gameTime(ctx.date) - $0 } ?? 0
            ZStack(alignment: .topLeading) {
                Color.clear
                SocPopIn(u: u, start: 0.18, duration: 0.10, overshoot: 1.10, at: CGPoint(x: 196.8, y: 82.9 - 13)) { SocInfoTitle(title: "Treasure Climb", baseline: 82.9) }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 57.4 + 105.8 / 2, y: 138.8 + 105.4 / 2)) { ArtImage(art: .infoPathIcon).placed(CGRect(57.4, 138.8, 105.8, 105.4)) }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 111.7, y: 270.5 - 6)) {
                    SocTwoLines(text: "Beat levels without losing!", centreX: 111.7, baselines: [270.5, 290.5], box: 110, greedy: true)
                }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 190 + 40 / 2, y: 240 + 43 / 2)) { ArtImage(art: .pointerArrowYellow).placed(CGRect(234, 236, 40, 45)) }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 166.8 + 197.2 / 2, y: 338.6 + 62.4 / 2)) {
                    SocChevronChips(steps: [5, 10, 25], lit: 1).placed(CGRect(166.8, 338.6, 197.2, 62.4))
                }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 262.7, y: 423.5 - 6)) {
                    SocTwoLines(text: "Increase your score multiplier!", centreX: 262.7, baselines: [423.5, 443.5], box: 170, greedy: true)
                }
                SocPopIn(u: u, start: 0.72, at: CGPoint(x: 190 + 40 / 2, y: 465 + 43 / 2)) { ArtImage(art: .pointerArrowYellow).scaleEffect(x: -1, y: 1).placed(CGRect(234, 488, 40, 45)) }
                SocPopIn(u: u, start: 0.88, at: CGPoint(x: 89.7 + 75.4 / 2, y: 523.4 + 62 / 2)) { ArtImage(art: .coinPileSmall).placed(CGRect(89.7, 523.4, 75.4, 62)) }
                if u >= 1.10 { SocTapTo(text: "Tap to Continue", baseline: 793.4).opacity(min(1, (u - 1.10) / 0.15)) }
            }
            .frame(width: 393, height: 852)
        }
        .contentShape(Rectangle())
        .onTapGesture { answer(PopupResult.close) }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("claw.info.overlay")
        .onAppear { shownAt = app.clock.gameTime() }
    }
}
