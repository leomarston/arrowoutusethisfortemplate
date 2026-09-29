import SwiftUI
import PathCore

// SOCIAL SOC2 (SPEC-ui §2.18 Sky Jump; uim `skyJump`, `skyOffer`, `skyMatch`, `skyTut`, `skyMap`, `skyWin`; SPEC-social §4.6,
// §14.2, §15.2 (stages 5 / 7 / 10, pools 5000 / 7000 / 10000); SPEC-motion-audio §9; VERIFIED 065-070, 074-096, meta-055):
//   SocSkyOffer     the purple panel (dim 0.90): "Sky Jump" lettering, the purple countdown chip, the prize scene with the live
//                   "PRIZE 5000" on the sign, the stage tray (chests; won stages checked) with "Pass N Levels in a row on first
//                   try …", the framed green "Start", the X. Start → C3 join → matching → tutorial (first run) → the map.
//   SocSkyMatching  dim 0.96: the lettering, the prize island, "Finding players on your level." with the counter 29 → 100
//                   over 1.5 s (easeOutQuad), the fan of 14 portraits popping in (the player's green), "Tap to Continue".
//   SocSkyTutorial  dim 0.95: Start with 100 players! · Beat N levels! · Win your share of P coins! · Advance to next stages
//                   for greater prizes! · the red warning card · Tap to Continue.
//   SocSkyMap       the map (event screen from the badge; `skyJump(.progress)` after a first-try win): the backdrop, the far
//                   islands, the prize island (live PRIZE), pads 1-4 with live numbers, the header plate (Stages dots · Levels
//                   k/N · Players left/100), the run's countdown, the player's portrait on its pad (hopping 0.5 s after a
//                   win), rival portraits; failed / expired: the cracked pad + "You failed the challenge!" + Continue.
//   SocSkyWin       "Congratulations!", the island, "You win!", the coin bowl counting up to the share in 1.0 s, the
//                   player's portrait, "You are sharing the reward with N other winners!", the winners' fan → the claim.
//                   A2 FEEL-P (owner item 8; motion-catalog §3.2 / §6.6, VERIFIED v552 60 Hz S3-skyjump3-win-claim): STAGED
//                   from S — letters left → right by S + 0.43, the island 0.28 → 1.05 at 0.60 → 1 at 0.68, "You win!" 0.88 →
//                   1.04 at 1.18 → 1.28, the bowl + number ≈ 0.95, the portrait 1.20 → 1.36, the number counts LINEARLY from
//                   S + 1.38 to 2.38 then a gold glow at 2.44, the sharing line 1.53 → 1.70, the winners from 1.61; taps count
//                   from 2.36 (was 0.6). ◉ rewardPop: the island lands 0.50, the glow 0.60, each winner 0.30 (§5.1 row 21).
// "Players" is the world's survivor curve of THIS attempt (a function of the player's first-try wins, not of time), the
// portraits are active world players with a portrait (SOC1 `skyJump(_:at:).shown`).

struct SocSkyOffer: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @Environment(\.socPrewarm) private var prewarm

    var body: some View {
        let t = app.tuning.ui.tokens
        let rules = ShellEconomy.rules(app)
        let status = Events.status(app.store.state, now: app.clock.wallClock(), rules: rules)
        let stage = status.skyJump?.stage ?? 1
        let goal = status.skyJump?.levels ?? rules.events.skyJump.levels(stage: stage)
        let pool = rules.events.skyJump.pool(stage: stage)
        let now = SocTime.now(app)
        ZStack(alignment: .topLeading) {
            Color.clear
            SocSkyPanel().placed(CGRect(10.3, 172.8, 372.6, 536.5))
            // the scene fills the field's width (the panel frame hides its sides; 330 x 190 at 344.6 / 330)
            ArtImage(art: .hopOfferScene, contentMode: .fill).frame(width: 344.6, height: 199).clipped()
                .placed(CGRect(24.3, 248, 344.6, 199))
            SocPrizeSignText(pool: pool, face: CGRect(85.1, 265.8, 104, 48))
            SocSkyLettering(frame: CGRect(66.7, 133.4, 266.9, 70.1))
            if let end = status.skyJump?.endsAt {                          // FIX-2 B review (L28): ticks; no run = no chip
                SocSkyChip(seconds: SocTime.left(end, now: now), live: (ends: end, now: now)).placed(CGRect(158.8, 209.5, 75.4, 23.4))
            }
            SocStageStrip(stage: stage, frame: CGRect(40.7, 455.4, 309.9, 105.8), goal: goal, space: false)
            FramedButton(id: "popup.skyJump.primary", title: "Start", colors: .green, frame: CGRect(89.7, 574.8, 212.5, 87.7),
                         well: CGRect(78.2, 566.1, 235.5, 106.4), n: 4.9,
                         style: .s2(44.3, -3.4, [0xFFFBF2], outline: 0x924500, 2.0, drop: 2.0),
                         baseline: 634.5, centreX: 196.0, maxWidth: 150, t: t) {
                answer(PopupResult.primary)
                SocialFlows.startSkyJump(app)
            }
            PopupCloseButton(id: "popup.skyJump.close", t: t) { answer(PopupResult.close) }
                .placed(CGRect(338.3, 176.5, 45, 45))
            WeekStartBanner(event: .skyJump, onCanvas: true)                    // B1: the week-start page's ribbon
        }
        .frame(width: 393, height: 852)
        .onAppear {
            Log.mark("event", "skyJump offer stage \(stage) (\(goal) levels, prize \(pool))")
            if !prewarm { EventAnnounce.opened(app, .skyJump) }                // B1: the home's NEW ribbon goes (not the Loading prewarm)
        }
    }
}

/// The segmented purple frame (SPEC-ui uim `skyJump.panel`: frame #5F3AD5, rivets #8D6DE9, the sky #2387F2; r_top ≈ 57,
/// r_bottom ≈ 80, approximated as a rounded rect as uim suggests).
struct SocSkyPanel: View {
    var body: some View {
        Rasterized("skyPanel") { size in
            ZStack {
                RoundedRectangle(cornerRadius: 62).fill(Color(hex: 0x6D1542))
                RoundedRectangle(cornerRadius: 61)
                    .fill(LinearGradient(colors: [Color(hex: 0xD1588B), Color(hex: 0xA2286B), Color(hex: 0x851953)], startPoint: .top, endPoint: .bottom))
                    .padding(1)
                RoundedRectangle(cornerRadius: 48)
                    .fill(LinearGradient(colors: [Color(hex: 0x00978B), Color(hex: 0x54C4BB), Color(hex: 0xFAD8E2)], startPoint: .top, endPoint: .bottom))
                    .padding(14)
                ForEach(0..<4, id: \.self) { i in
                    Circle().fill(Color(hex: 0xD1588B)).frame(width: 12, height: 12)
                        .position(x: i % 2 == 0 ? 20 : size.width - 20, y: i < 2 ? 90 : size.height - 90)
                }
            }
        }
    }
}

/// "Sky" white + "Jump" yellow in the italic lettering with a purple outline (VERIFIED 065 / 069).
struct SocSkyLettering: View {
    let frame: CGRect
    var body: some View {
        SocEventLogo(title: "Cloud Hop", frame: frame, size: frame.height * 0.72, yellowFirst: false, outline: 0x7A184B, extrusion: 0x601138)
    }
}

/// The purple countdown chip of the Sky Jump screens (#865FF8, white text outlined #380E66, the stopwatch at its left).
/// FIX-2 lane B (review of L28): given the run's end (`live`) the chip ticks on its own (`LiveCountdown`, the page clock), the
/// time drawn from cached per-glyph rasters (`GlyphRunText`).
struct SocSkyChip: View {
    let seconds: Double
    /// The run's end and the caller's clock reading; nil = the static `seconds`.
    var live: (ends: SocialTime, now: SocialTime)? = nil

    var body: some View {
        if let live {
            LiveCountdown(ends: live.ends, now: live.now, clock: .page) { s in chip(s) }
        } else {
            chip(seconds)
        }
    }

    private func chip(_ seconds: Double) -> some View {
        let st = GameTextStyle.s2(13.2, -0.3, [0xFFFFFF], outline: 0x49142B, 1.0, drop: 0.6)
        return GeometryReader { geo in
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: geo.size.height / 2).fill(Color(hex: 0xD64387))
                    .frame(width: geo.size.width - 10, height: geo.size.height).offset(x: 10)
                ArtImage(art: .iconStopwatchSmall).frame(width: geo.size.height * 0.95, height: geo.size.height * 1.02).offset(x: -2, y: -1)
                GlyphRunText(text: Countdown.text(seconds), style: st, maxWidth: geo.size.width - 26)
                    .position(x: geo.size.width / 2 + 9, y: geo.size.height / 2)
            }
        }
        .accessibilityElement()
        .accessibilityIdentifier("event.skyJump.timer")
        .accessibilityValue(Text(verbatim: Countdown.text(seconds)))
    }
}

/// The live "PRIZE" / pool text on the baked sign face (art/lanes/scene.md live-text anchors; the coin disc sits at the face's
/// left end, the text right of it).
struct SocPrizeSignText: View {
    let pool: Int
    let face: CGRect
    var body: some View {
        let h = face.height
        let st = GameTextStyle.s2(h * 0.30, -0.2, [0xFFFFFF], outline: 0x7A3D00, max(0.8, h * 0.025), drop: 0.4)
        let x = face.midX
        ZStack(alignment: .topLeading) {
            GameText("PRIZE", style: st, maxWidth: face.width).at(x, st.capCentre(baseline: face.minY + h * 0.44))
            GameText(verbatim: "\(pool)", style: st, maxWidth: face.width).at(x, st.capCentre(baseline: face.minY + h * 0.84))
        }
        // the baked sign rises to the right (measured on the renders: its green face's centroid sits at (93.9, 49.1) of the
        // 260 × 256 island, (105, 41.4) of the 330 × 190 popup scene)
        .rotationEffect(.degrees(-20), anchor: UnitPoint(x: face.midX / 393, y: face.midY / 852))
    }
}

// MARK: - matching

struct SocSkyMatching: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?

    var body: some View {
        let model = SocialModel.install(app)
        let snap = model.sky
        let pool = snap?.pool ?? ShellEconomy.rules(app).events.skyJump.pool(stage: 1)
        let me = app.store.state.social.avatar
        TimelineView(.animation(minimumInterval: nil, paused: shownAt.map { app.clock.gameTime() - $0 > 2.2 } ?? true)) { ctx in
            let u: Double = shownAt.map { app.clock.gameTime(ctx.date) - $0 } ?? 0
            SocSkyMatchingContent(u: u, pool: pool, shown: snap?.shown ?? [], me: me)
        }
        .contentShape(Rectangle())
        .onTapGesture { if let s = shownAt, app.clock.gameTime() - s >= 1.5 { answer(PopupResult.close) } }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("sky.matching")
        .onAppear {
            shownAt = app.clock.gameTime()
            model.request(.sky)
        }
    }
}

private struct SocSkyMatchingContent: View {
    let u: Double
    let pool: Int
    let shown: [SimPlayer]
    let me: Int

    var body: some View {
        let k: Double = min(1, u / 1.5)
        let eased: Double = 1 - (1 - k) * (1 - k)
        let count: Int = 29 + Int((71 * eased).rounded(.down))
        ZStack(alignment: .topLeading) {
            Color.clear
            SocSkyLettering(frame: CGRect(63.4, 76.7, 270.2, 73.4))
            ArtImage(art: .hopIsland).placed(CGRect(47, 138, 300, 295))
            // the island's live sign face (art/lanes/scene.md: 44..104 x 9..40 of the 260 x 256 frame) at 300 / 260
            SocPrizeSignText(pool: pool, face: CGRect(125.6, 174.7, 69, 35))
            SocFindingBubble(count: count).placed(CGRect(63.1, 470.7, 267.2, 96.4))
            SocAvatarFan(players: shown, meAvatar: me, u: u, frame: CGRect(24, 588.2, 341, 139.1))
            if u >= 1.6 {
                let st = GameTextStyle.s2(20.3, -0.77, [0xF6E9D8])
                GameText("Tap to Continue", style: st, maxWidth: 300).at(196.5, st.capCentre(baseline: 796)).opacity(min(1, (u - 1.6) / 0.15))
            }
        }
        .frame(width: 393, height: 852)
    }
}

/// "Finding players on your level." (white head, outlined #380E66) over the cream counter "n/100" (33 pt #622200).
private struct SocFindingBubble: View {
    let count: Int
    var body: some View {
        let head = GameTextStyle.s2(17.8, -0.05, [0xFFFFFF], outline: 0x49142B, 1.1, drop: 0.7)
        let counter = GameTextStyle.s2(33, 0.56, [0x5A2801])
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 12).fill(Color(hex: 0x90245E)).frame(width: 267.2, height: 38)
            RoundedRectangle(cornerRadius: 10).fill(Color(hex: 0xAB7D4C)).frame(width: 267.2, height: 56).offset(y: 34)
            RoundedRectangle(cornerRadius: 10).fill(Color(hex: 0xF4E8D4)).frame(width: 267.2, height: 54).offset(y: 34)
            Path { p in p.move(to: CGPoint(x: 90, y: 87)); p.addLine(to: CGPoint(x: 104, y: 96.4)); p.addLine(to: CGPoint(x: 112, y: 87)) }
                .fill(Color(hex: 0xF4E8D4))
            GameText("Finding players on your level.", style: head, maxWidth: 250).at(133.6, head.capCentre(baseline: 25))
            GameText(verbatim: "\(count)/100", style: counter, maxWidth: 200).at(133.6, counter.capCentre(baseline: 74))
                .accessibilityIdentifier("event.skyJump.finding")
                .accessibilityValue(Text(verbatim: "\(count)/100"))
        }
        .frame(width: 267.2, height: 96.4, alignment: .topLeading)
    }
}

/// The fan of portraits (two overlapping rows, the player's green tile in front at the centre; VERIFIED 067), popping in one by
/// one.
struct SocAvatarFan: View {
    let players: [SimPlayer]
    let meAvatar: Int
    let u: Double
    let frame: CGRect
    var showMe = true
    /// Tile size; the spacing follows it (the matching fan 58 pt, the tutorial's small fan 30 pt).
    var tile: CGFloat = 58
    /// Horizontal step between neighbours as a fraction of the tile (the tutorial's small fan overlaps more).
    var spread: CGFloat = 0.78

    var body: some View {
        let back = Array(players.prefix(7)), front = Array(players.dropFirst(7).prefix(6))
        let step = tile * spread
        ZStack(alignment: .topLeading) {
            ForEach(Array(back.enumerated()), id: \.offset) { i, p in
                SocPopIn(u: u, start: 0.10 + Double(i) * 0.10) {
                    SocAvatar(index: p.avatar).frame(width: tile, height: tile)
                }
                .position(x: frame.width / 2 + (CGFloat(i) - CGFloat(back.count - 1) / 2) * step, y: tile * 0.55)
            }
            ForEach(Array(front.enumerated()), id: \.offset) { i, p in
                SocPopIn(u: u, start: 0.10 + Double(i + 7) * 0.10) {
                    SocAvatar(index: p.avatar).frame(width: tile, height: tile)
                }
                .position(x: frame.width / 2 + (CGFloat(i) - 2.5) * step * 1.05 + (i >= 3 ? tile * 0.28 : -tile * 0.28), y: tile * 1.05)
            }
            if showMe {
                SocPopIn(u: u, start: 0.10) { SocAvatar(index: meAvatar, me: true).frame(width: tile * 1.14, height: tile * 1.1) }
                    .position(x: frame.width / 2, y: tile * 1.68)
            }
        }
        .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        .placed(frame)
    }
}

// MARK: - tutorial

struct SocSkyTutorial: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?

    var body: some View {
        let model = SocialModel.install(app)
        let rules = ShellEconomy.rules(app)
        let stage = model.sky?.stage ?? 1
        let goal = model.sky?.goal ?? rules.events.skyJump.levels(stage: stage)
        let pool = model.sky?.pool ?? rules.events.skyJump.pool(stage: stage)
        TimelineView(.animation(minimumInterval: nil, paused: shownAt.map { app.clock.gameTime() - $0 > 1.4 } ?? true)) { ctx in
            let u = shownAt.map { app.clock.gameTime(ctx.date) - $0 } ?? 0
            ZStack(alignment: .topLeading) {
                Color.clear
                SocPopIn(u: u, start: 0.18, duration: 0.10, overshoot: 1.10, at: CGPoint(x: 196.8, y: 82.9 - 13)) { SocInfoTitle(title: "Cloud Hop", baseline: 82.9) }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 35.7 + 176.1 / 2, y: 150 + 110 / 2)) {
                    SocAvatarFan(players: Array((model.sky?.shown ?? []).prefix(13)), meAvatar: app.store.state.social.avatar, u: 1,
                                 frame: CGRect(35.7, 172, 176.1, 96), tile: 38, spread: 0.52)
                }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 122.8, y: 284.5 - 6)) {
                    SocTwoLines(text: "Start with 100 players!", centreX: 122.8, baselines: [284.5], box: 200, hot: "100 players")
                }
                SocPopIn(u: u, start: 0.50, at: CGPoint(x: 228 + 38 / 2, y: 200 + 41 / 2)) { ArtImage(art: .pointerArrowYellow).placed(CGRect(236, 212, 42, 46)) }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 269.6 + 96.1 / 2, y: 271.9 + 96.1 / 2)) { ArtImage(art: .infoPathIcon).placed(CGRect(269.6, 271.9, 96.1, 96.1)) }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 315.5, y: 393.5 - 6)) {
                    SocTwoLines(text: "Beat \(goal) levels!", centreX: 315.5, baselines: [393.5], box: 115, size: 17.2, hot: "\(goal) levels!")
                }
                SocPopIn(u: u, start: 0.66, at: CGPoint(x: 220 + 38 / 2, y: 410 + 41 / 2)) { ArtImage(art: .pointerArrowYellow).scaleEffect(x: -1, y: 1).placed(CGRect(222, 428, 42, 46)) }
                SocPopIn(u: u, start: 0.72, at: CGPoint(x: 47.7 + 154.1 / 2, y: 356 + 152 / 2)) {
                    ArtImage(art: .hopIsland).placed(CGRect(47.7, 356, 154.1, 152))
                    SocPrizeSignText(pool: pool, face: CGRect(88, 375, 35.6, 17.8))
                }
                SocPopIn(u: u, start: 0.72, at: CGPoint(x: 128, y: 526.5 - 6)) {
                    SocTwoLines(text: "Win your share of \(pool) coins!", centreX: 128, baselines: [526.5, 549], box: 180, size: 19.7,
                                greedy: true, resolved: SocText.plain({ "Win your share of \($0) coins!" }, pool),
                                hotResolved: SocText.plain({ "\($0) coins" }, pool))
                }
                SocPopIn(u: u, start: 0.80, at: CGPoint(x: 42.4 + 309.6 / 2, y: 582.2 + 60.7 / 2)) { SocStageTray().placed(CGRect(42.4, 582.2, 309.6, 60.7)) }
                SocPopIn(u: u, start: 0.80, at: CGPoint(x: 196.2, y: 673 - 6)) {
                    SocTwoLines(text: "Advance to next stages for greater prizes!", centreX: 196.2, baselines: [673], box: 340, size: 16.5,
                                hot: "greater prizes")
                }
                SocPopIn(u: u, start: 0.88, at: CGPoint(x: 47.4 + 298.9 / 2, y: 697.9 + 61.1 / 2)) {
                    SocWarningCard(text: "If you fail a level, you will fail the challenge!", frame: CGRect(47.4, 697.9, 298.9, 61.1))
                }
                if u >= 1.10 {
                    let st = GameTextStyle.s2(12.2, 0.24, [0xF6E9D8])
                    GameText("Tap to Continue", style: st, maxWidth: 200).at(196.6, st.capCentre(baseline: 792.7)).opacity(min(1, (u - 1.10) / 0.15))
                }
            }
            .frame(width: 393, height: 852)
        }
        .contentShape(Rectangle())
        .onTapGesture { answer(PopupResult.close) }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("sky.tutorial")
        .onAppear { shownAt = app.clock.gameTime() }
    }
}

/// The three chests on a purple tray (the tutorial's "stages" item).
private struct SocStageTray: View {
    var body: some View {
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 18).fill(Color(hex: 0xE25190))
            ForEach(0..<3, id: \.self) { i in
                RoundedRectangle(cornerRadius: 12).fill(Color(hex: i == 0 ? 0xE7639B : 0xC93D81))
                    .frame(width: 96, height: 50).offset(x: 6 + CGFloat(i) * 101.2, y: 5)
                ArtImage(art: i == 0 ? .stageChestGreen : i == 1 ? .stageChestBlue : .stageChestPink)
                    .frame(width: 52, height: 39).offset(x: 28 + CGFloat(i) * 101.2, y: 10)
            }
        }
    }
}

// MARK: - the map

struct SocSkyMap: View {
    @Environment(\.socPrewarm) private var prewarm
    /// As the progress popup page (`skyJump(.progress)`): "Tap to Continue" answers it and there is no X.
    var answer: PopupAnswer? = nil
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m
    @State private var hopFrom: Int?
    @State private var hopStart: Double = 0

    /// Pad number plates (centres) of pads 1-4 on the reference canvas (VERIFIED 080 / 069; uim `skyMap.padBadge` pad 1) and
    /// their scale (the far ones smaller).
    /// FIX-2 B (F-17): the header plate is inset like the phone's (080: x 13.0 → 380.0 pt on the 1178 px shot), not full width.
    static let headerPlate = CGRect(13, 103.4, 367, 103.4)
    static let plates: [(CGPoint, CGFloat)] = [(CGPoint(x: 220.0, y: 750.0), 1.12), (CGPoint(x: 297.0, y: 675.0), 1.04),
                                               (CGPoint(x: 189.0, y: 615.0), 0.95), (CGPoint(x: 107.5, y: 558.0), 0.93)]

    var body: some View {
        let model = SocialModel.install(app)
        let t = app.tuning.ui.tokens
        let snap = model.sky
        let now = SocTime.now(app)
        let failed = snap.map { $0.result == "failed" || $0.result == "expired" } ?? false
        ZStack(alignment: .topLeading) {
            ArtImage(art: .hopBackdrop, contentMode: .fill).frame(width: m.size.width, height: m.size.height).clipped()
            ReferenceCanvas {
                TimelineView(.animation(minimumInterval: nil, paused: app.clock.gameTime() - hopStart > 0.8)) { ctx in
                    let u = app.clock.gameTime(ctx.date) - hopStart
                    ZStack(alignment: .topLeading) {
                        ArtImage(art: .hopIslandFar).placed(CGRect(6, 222, 166, 158))
                        ArtImage(art: .hopIslandFar2).placed(CGRect(213, 214, 144, 132))
                        // the small stepping pads between the islands (VERIFIED 069 / 080; decoration, no numbers)
                        ForEach(0..<3, id: \.self) { i in
                            let c = [CGPoint(x: 182, y: 330), CGPoint(x: 236, y: 320), CGPoint(x: 287, y: 410)][i]
                            ArtImage(art: .hopPad).frame(width: 44, height: 41).position(c)
                        }
                        ArtImage(art: .hopIsland).placed(CGRect(66, 306, 260, 256))
                        SocPrizeSignText(pool: snap?.pool ?? 5000, face: CGRect(134, 338, 60, 30))
                        pads(snap, failed: failed)
                        players(snap, u: u)
                        header(snap, now: now)
                        if failed {
                            SocFailedCard().placed(CGRect(47.4, 439.5, 298.9, 61.1))
                            FramedButton(id: "event.skyJump.continue", title: "Continue", colors: .green,
                                         frame: CGRect(91.4, 741.3, 210.5, 86.4), well: CGRect(80.0, 732.6, 233.3, 104.1), n: 4.6,
                                         style: .s2(38.9, 0.05, [0xFFFFFF, 0xF9F0E1], outline: 0x924500, 2.0, drop: 2.0),
                                         baseline: 798.0, centreX: 196.6, maxWidth: 172, t: t) { close() }
                        } else if answer != nil {
                            let st = GameTextStyle.s2(20.3, -0.77, [0xF6E9D8], outline: 0x90245E, 1.0, drop: 0.8)
                            GameText("Tap to Continue", style: st, maxWidth: 300).at(196.5, st.capCentre(baseline: 792))
                        }
                    }
                    .frame(width: 393, height: 852, alignment: .topLeading)
                }
            }
            GameButton(id: "sky.info", label: "Info", action: {
                Task { @MainActor in
                    _ = await app.popups.present(Popup<PopupResult>(.skyJump(.tutorial), style: PopupStyle(dim: .info, closesOnTapAnywhere: true),
                                                                    fallback: .close))
                }
            }) { SocInfoDisc() }
            .placed(m.rect(CGRect(4.7, 52.0, 40.4, 40.4), .top))
            if answer == nil && !failed {
                PopupCloseButton(id: "event.skyJump.close", t: t, halo: true) { close() }
                    .placed(m.rect(CGRect(333.0, 49.1, 45, 45), .top))
            }
            SocReadyWhen(ready: snap != nil, name: "event:skyJump")
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .clipped()
        .contentShape(Rectangle())
        .onTapGesture { if answer != nil && !failed { close() } }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("page.skyJump")
        .onAppear {
            guard !prewarm else { return }
            model.appear(.sky)
            model.probeOpen("skyJump")
            model.request(.sky)
            if answer != nil, let p = snap?.progress, p > 0 { hopFrom = p - 1; hopStart = app.clock.gameTime() }
            Log.mark("event", "skyJump map visible (\(snap.map { "\($0.progress)/\($0.goal) players \($0.playersLeft)" } ?? "no run"))")
        }
        .onDisappear { if !prewarm { model.disappear(.sky) } }
    }

    private func close() {
        if let answer { answer(PopupResult.close) } else { EventPageShell<EmptyView>.close(app) }
    }

    /// Pad index of a progress value: pad 1 at the start, one pad per first-try win, the island from the 5th step; for the
    /// longer stages the pads show a sliding window of level numbers (DECISION: stages 2-3 were only seen from the offer).
    private func padNumber(_ slot: Int, _ snap: SocSkyJumpWindow) -> Int { snap.first + slot }

    @ViewBuilder private func pads(_ snap: SocSkySnap?, failed: Bool) -> some View {
        let w = SocSkyJumpWindow(progress: snap?.progress ?? 0, goal: snap?.goal ?? 5)
        ForEach(0..<4, id: \.self) { i in
            let (c, k) = Self.plates[i]
            let size = CGSize(width: 112 * k, height: 104 * k)
            let origin = CGPoint(x: c.x - 56.5 * k, y: c.y - 62.5 * k)
            let n = padNumber(i, w)
            if n <= w.goal - 1 || w.goal <= 4 {
                ZStack(alignment: .topLeading) {
                    ArtImage(art: .hopPad)
                        .opacity(failed && i == w.slot ? 0.6 : 1)
                    let st = GameTextStyle.s2(28.5 * k, 0, [0xFEF5F7], outline: 0x7C181A, 2.4 * k)
                    GameText(verbatim: "\(n)", style: st, maxWidth: 40 * k).at(56.5 * k, st.capCentre(baseline: 62.5 * k + st.size * 0.36))
                }
                .frame(width: size.width, height: size.height, alignment: .topLeading)
                .placed(CGRect(origin: origin, size: size))
            }
        }
    }

    @ViewBuilder private func players(_ snap: SocSkySnap?, u: Double) -> some View {
        if let s = snap {
            let w = SocSkyJumpWindow(progress: s.progress, goal: s.goal)
            let target = avatarCentre(slot: w.slot, island: w.onIsland)
            let fromSlot = hopFrom.map { SocSkyJumpWindow(progress: $0, goal: s.goal) }
            let p = hopFrom == nil ? 1 : min(1, max(0, u / 0.5))
            let e = p < 0.5 ? 2 * p * p : 1 - pow(-2 * p + 2, 2) / 2
            let from = fromSlot.map { avatarCentre(slot: $0.slot, island: $0.onIsland) } ?? target
            let x = from.x + (target.x - from.x) * CGFloat(e)
            let y = from.y + (target.y - from.y) * CGFloat(e) - 60 * CGFloat(4 * e * (1 - e))
            // rivals: 2 on the player's pad (behind), 2 one pad behind (SPEC-social §4.6, VERIFIED 088)
            ForEach(Array(s.shown.prefix(2).enumerated()), id: \.offset) { i, pl in
                SocAvatar(index: pl.avatar).frame(width: 60, height: 58).position(x: target.x - 22 + CGFloat(i) * 12, y: target.y - 8)
            }
            if w.slot > 0 {
                let back = avatarCentre(slot: w.slot - 1, island: false)
                ForEach(Array(s.shown.dropFirst(2).prefix(2).enumerated()), id: \.offset) { i, pl in
                    SocAvatar(index: pl.avatar).frame(width: 60, height: 58).position(x: back.x - 10 + CGFloat(i) * 16, y: back.y)
                }
            }
            SocAvatar(index: app.store.state.social.avatar, me: true).frame(width: 71.1, height: 69.1).position(x: x, y: y)
                .accessibilityElement()
                .accessibilityIdentifier("event.skyJump.me")
                .accessibilityValue(Text(verbatim: "\(s.progress)/\(s.goal)"))
        }
    }

    private func avatarCentre(slot: Int, island: Bool) -> CGPoint {
        if island { return CGPoint(x: 205, y: 420) }
        let (c, _) = Self.plates[max(0, min(3, slot))]
        return CGPoint(x: c.x, y: c.y - 64)                  // VERIFIED 080 (pad 2) / 088 (pad 4): the tile ≈ 64 pt above the plate
    }

    @ViewBuilder private func header(_ snap: SocSkySnap?, now: SocialTime) -> some View {
        let label = GameTextStyle.s2(17.9, -0.04, [0xFFFFFF], outline: 0x5A2801, 1.7, drop: 0.6)
        let value = GameTextStyle.s2(20.7, 0.67, [0xFFFFFF], outline: 0x5A2801, 1.9, drop: 0.9)
        SocSkyLettering(frame: CGRect(63.4, 44, 270.2, 66))
        SocSkyHeaderPlate().placed(Self.headerPlate)
        SocStatPlate().placed(CGRect(40, 131.4, 96.1, 48.7))
        SocStatPlate().placed(CGRect(143.5, 126.8, 103.4, 60.1))
        SocStatPlate().placed(CGRect(250.2, 126.8, 106.8, 60.1))
        GameText("Stages", style: label, maxWidth: 85).at(88, label.capCentre(baseline: 150))
        SocStageDots(stage: snap?.stage ?? 1).placed(CGRect(55, 158, 66, 14))
        GameText("Levels", style: label, maxWidth: 85).at(195.2, label.capCentre(baseline: 147.5))
        GameText(verbatim: "\(snap?.progress ?? 0)/\(snap?.goal ?? 5)", style: value, maxWidth: 80).at(195.2, value.capCentre(baseline: 175))
            .accessibilityIdentifier("event.skyJump.levels")
        GameText("Players", style: label, maxWidth: 90).at(303.6, label.capCentre(baseline: 147.5))
        GameText(verbatim: "\(snap?.playersLeft ?? 100)/100", style: value, maxWidth: 90).at(303.6, value.capCentre(baseline: 175))
            .accessibilityElement()
            .accessibilityIdentifier("event.skyJump.players")
            .accessibilityValue(Text(verbatim: "\(snap?.playersLeft ?? 100)"))
        if let end = snap?.endsAt {                                        // FIX-2 B review (L28): ticks; no run = no chip
            SocSkyChip(seconds: SocTime.left(end, now: now), live: (ends: end, now: now)).placed(CGRect(158.8, 199, 75.4, 23.4))
        }
    }
}

/// Which pads a run's progress shows: the player stands on pad `progress + 1` (VERIFIED 080: one win → pad 2; 088: pad 4) and
/// on the prize island for the stage's last level; 5-level stages show pads 1-4, the longer ones (7 / 10) a window of four
/// consecutive level numbers that follows the player (DECISION: stages 2-3 were only seen from their offers).
struct SocSkyJumpWindow {
    let progress: Int
    let goal: Int
    /// The first pad's level number.
    var first: Int { max(1, min(progress, goal - 4)) }
    /// The pad the player stands on (0-3).
    var slot: Int { max(0, min(3, progress + 1 - first)) }
    var onIsland: Bool { progress >= goal - 1 }
}

private struct SocSkyHeaderPlate: View {
    var body: some View {
        Rasterized("skyHeader") { size in
            ZStack {
                Superellipse(n: 4.2).fill(Color(hex: 0x6D1542))
                Superellipse(n: 4.2).fill(LinearGradient(colors: [Color(hex: 0xD1588B), Color(hex: 0xA2286B)], startPoint: .top, endPoint: .bottom))
                    .padding(1.2)
                Superellipse(n: 4.2).fill(Color(hex: 0xDBA86F)).padding(EdgeInsets(top: 12, leading: 14, bottom: 12, trailing: 14))
                Superellipse(n: 4.2).fill(Color(hex: 0xE8C699)).padding(EdgeInsets(top: 14, leading: 16, bottom: 16, trailing: 16))
            }
        }
    }
}

private struct SocStatPlate: View {
    var body: some View {
        Rasterized("skyStat") { _ in
            ZStack {
                RoundedRectangle(cornerRadius: 11.5).fill(Color(hex: 0xBA8446))
                RoundedRectangle(cornerRadius: 11.5).fill(Color(hex: 0xDEAE75)).padding(1.5)
            }
        }
    }
}

/// "Stages": three dots on a line, the reached ones purple.
private struct SocStageDots: View {
    let stage: Int
    var body: some View {
        ZStack {
            Capsule().fill(Color(hex: 0xB27D44)).frame(height: 3)
            HStack(spacing: 0) {
                ForEach(1...3, id: \.self) { s in
                    Circle().fill(Color(hex: s <= stage ? 0xAE2570 : 0xB27D44)).frame(width: 12, height: 12)
                    if s < 3 { Spacer(minLength: 0) }
                }
            }
        }
    }
}

/// "You failed the challenge!" (26 pt #DE0002 on cream; the tutorial's warning geometry).
private struct SocFailedCard: View {
    var body: some View {
        let st = GameTextStyle.s2(26, -0.5, [0xD12D1C])
        ZStack {
            RoundedRectangle(cornerRadius: 11.2).fill(Color(hex: 0xC59C71)).offset(y: 1.5)
            RoundedRectangle(cornerRadius: 11.2).fill(Color(hex: 0xF4E8D4))
            GameText("You failed the challenge!", style: st, maxWidth: 280)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("event.skyJump.failed")
    }
}

// MARK: - stage won

struct SocSkyWin: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?
    @State private var beats = BeatOnce()

    var body: some View {
        let claim: EventClaim? = app.store.state.events.claims.first { $0.kind == .skyJumpShare }
        let snap: SocSkySnap? = SocialModel.shared?.sky
        let share: Int = claim.map { $0.grant.coins } ?? snap?.share ?? 0
        let winners: Int = claim.map { $0.value } ?? snap?.winners ?? 1
        let shown: [SimPlayer] = snap?.shown ?? []
        let fan = min(4, max(0, winners - 1))
        TimelineView(.animation(minimumInterval: nil, paused: shownAt.map { app.clock.gameTime() - $0 > 3.2 } ?? true)) { ctx in
            let u: Double = shownAt.map { app.clock.gameTime(ctx.date) - $0 } ?? 0
            SocSkyWinContent(u: u, pool: snap?.pool ?? share * max(1, winners), share: share, winners: winners, shown: shown,
                             avatar: app.store.state.social.avatar)
            // A2: the claim's reward beats vibrate on their frame (motion-catalog §5.1 row 21)
            let _ = beats.fire("island", at: SocSkyWinContent.islandLand, u: u) { app.haptics.play(.rewardPop, intensity: 0.50) }
            let _ = beats.fire("glow", at: SocSkyWinContent.glowAt, u: u) { app.haptics.play(.rewardPop, intensity: 0.60) }
            let _ = (0..<fan).map { i in
                beats.fire("winner\(i)", at: SocSkyWinContent.winnerAt(i), u: u) { app.haptics.play(.rewardPop, intensity: 0.30) }
            }
        }
        .contentShape(Rectangle())
        .onTapGesture {
            // A2 (motion-catalog §6.6, DECISION: v552's order): the claim answers once "Tap to Claim" would show (S + 2.36)
            if let s = shownAt, app.clock.gameTime() - s >= SocSkyWinContent.acceptFrom { answer(PopupResult.primary) }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("sky.win")
        .onAppear { shownAt = app.clock.gameTime() }
    }
}

private struct SocSkyWinContent: View {
    let u: Double
    let pool: Int
    let share: Int
    let winners: Int
    let shown: [SimPlayer]
    let avatar: Int

    // A2: the v552 beats (motion-catalog §3.2 "Claim", seconds from S)
    static let islandAt = 0.28, islandPeak = 0.60, islandLand = 0.68, youWinAt = 0.88, youWinPeak = 1.18, youWinLand = 1.28
    static let bowlAt = 0.95, meAt = 1.20, countFrom = 1.38, countFor = 1.0, glowAt = 2.44, shareAt = 1.53, winnersAt = 1.61
    static let acceptFrom = 2.36
    /// SocAvatarFan pops its tiles 0.10 s apart from its own u = 0.10.
    static func winnerAt(_ i: Int) -> Double { winnersAt + Double(i) * 0.10 }

    /// 0 → peak (ease-out) at `peakAt` → 1 (smoothstep) at `land`; nil before `at`.
    static func grow(_ u: Double, at: Double, peakAt: Double, land: Double, peak: Double) -> Double? {
        guard u >= at else { return nil }
        if u >= land { return 1 }
        if u < peakAt { let q = (u - at) / max(0.001, peakAt - at); return peak * (1 - (1 - q) * (1 - q)) }
        let q = (u - peakAt) / max(0.001, land - peakAt)
        return peak + (1 - peak) * (q * q * (3 - 2 * q))
    }

    var body: some View {
        // the number counts LINEARLY from S + 1.38 for 1.0 s (v552: 0 → 1428 at ≈ 1430/s); 0 before
        let k: Double = min(1, max(0, (u - Self.countFrom) / Self.countFor))
        let amount: Int = Int((Double(share) * k).rounded(.down))
        let others: Int = max(0, winners - 1)
        let title = GameTextStyle.s2(45.5, -1.0, [0xFFDD13, 0xFFC302, 0xFFB700], outline: 0xB24900, 0.9, drop: 1.8)
        let yw = GameTextStyle.s2(29.5, -0.03, [0xFFD102, 0xFFCC01, 0xFFC201])
        let am = GameTextStyle.s2(29.9, -0.73, [0xF6E9D8], outline: 0x620B00, 2.2, drop: 1.1)
        let island = Self.grow(u, at: Self.islandAt, peakAt: Self.islandPeak, land: Self.islandLand, peak: 1.05)
        let youWin = Self.grow(u, at: Self.youWinAt, peakAt: Self.youWinPeak, land: Self.youWinLand, peak: 1.04)
        ZStack(alignment: .topLeading) {
            Color.clear
            LetterPopTitle(text: String(localized: "Congratulations!"), style: title, baseline: 122.8, centreX: 196.8, maxWidth: 360, u: u)
            // before its beat an element is drawn at 0.1 % (invisible): its art and text are on screen from S, so no beat
            // pays a first draw (measured: the island's first draw was a 52 ms frame at its beat)
            ZStack(alignment: .topLeading) {
                ArtImage(art: .hopIsland).placed(CGRect(75, 136, 243, 239))
                SocPrizeSignText(pool: pool, face: CGRect(138.6, 165.9, 56, 28))
            }
            .scaleEffect(CGFloat(island ?? 0.001), anchor: UnitPoint(x: 196.5 / 393, y: 255.5 / 852))
            GameText("You win!", style: yw, maxWidth: 250).scaleEffect(CGFloat(youWin ?? 0.001)).at(197.8, yw.capCentre(baseline: 372))
            SkyStagePop(u: u, start: Self.bowlAt, at: CGPoint(x: 197, y: 435)) {
                ZStack(alignment: .topLeading) {
                    ArtImage(art: .coinBowl).placed(CGRect(139.1, 386.3, 115.8, 97.4))
                    SkyWinGlow(u: u - Self.glowAt).frame(width: 393, height: 852)
                    GameText(verbatim: "\(amount)", style: am, maxWidth: 90).at(196.8, am.capCentre(baseline: 473))
                        .accessibilityIdentifier("sky.win.amount")
                }
            }
            SkyStagePop(u: u, start: Self.meAt, at: CGPoint(x: 196.3, y: 537.5)) {
                SocAvatar(index: avatar, me: true).placed(CGRect(157.8, 500.1, 77.1, 74.7))
            }
            SkyStagePop(u: u, start: Self.shareAt, duration: 0.17, overshoot: 1.05, at: CGPoint(x: 196.5, y: 622)) {
                SocTwoLines(text: "You are sharing the reward with \(others) other winners!", centreX: 196.5,
                            baselines: [611.5, 633.5], box: 330, size: 21, faceHex: 0xF6E9D8, hotHex: 0xF6E9D8, outline: nil, greedy: true,
                            breakAt: 345)
            }
            SocAvatarFan(players: Array(shown.prefix(min(4, others))), meAvatar: 0, u: max(0, u - (Self.winnersAt - 0.10)),
                         frame: CGRect(113.4, 667.2, 208.5, 91.7), showMe: false, tile: 56)
        }
        .frame(width: 393, height: 852)
    }
}

/// SocPopIn's pop, but drawn at 0.1 % before its beat (not absent): the first draw happens at S, not on the beat's frame.
private struct SkyStagePop<Content: View>: View {
    let u: Double
    let start: Double
    var duration = 0.16
    var overshoot = 1.12
    let at: CGPoint
    @ViewBuilder var content: Content
    var body: some View {
        let k = SocPop.scale(u, at: start, duration: duration, overshoot: overshoot) ?? 0.001
        content.scaleEffect(CGFloat(max(k, 0.001)), anchor: UnitPoint(x: at.x / 393, y: at.y / 852))
    }
}

/// The gold glow burst on the coin bowl when the count lands (v552 S + 2.44: a bright gold flash over the plate, ≈ 0.3 s).
private struct SkyWinGlow: View {
    let u: Double
    var body: some View {
        if u >= 0 && u < 0.35 {
            let a = u < 0.08 ? u / 0.08 : max(0, 1 - (u - 0.08) / 0.27)
            RadialGradient(colors: [Color(hex: 0xFFF6B0).opacity(0.95), Color(hex: 0xFFD23A).opacity(0.55), .clear],
                           center: .center, startRadius: 2, endRadius: 70)
                .frame(width: 150, height: 120)
                .opacity(a)
                .blendMode(.screen)
                .position(x: 197, y: 440)
                .allowsHitTesting(false)
        }
    }
}
