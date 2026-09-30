import SwiftUI
import PathCore

// SOCIAL SOC2 (SPEC-ui §2.16 Streak Race; SPEC-social §4.4, §13.3 (50 rows, prizes 2000 / 1000 / 500 / 100 × 7); VERIFIED
// meta-045..053, 102-106, 203). The event page (home badge → `Screen.event(.streakRace)`) and the same page as the auto-shown
// popup (`PopupID.streakRaceBoard`):
//   header art `workerRacers` (0 · 0 · 393 · 316.9), (i) → the info overlay, X → home
//   "Streak Race" lettering 40.0 · 298.9 · 313.6 · 54.7 (S2's StreakRaceLettering with its chequered flags)
//   the band 0 · 313.6 · 393 · 170 (rails + #2A5DEC field): the subtitle, the chips x1 … x100 with the current multiplier lit,
//   the countdown to 07:00 UTC; then the 50 rows (gold / silver / bronze / the player's green / cream; prize bowls on ranks
//   1-10; the flags score) scrolled to the player's row, which pins at the viewport edges.
// Opening the page joins the day's race (the phone's list auto-shows at the day's first home: the join happens there).
// B1b (v582 PH-0a): opening it (the badge, or the day's auto-shown list) is also opening the ended day's result: the home's
// "Finished" badge becomes the new day's countdown.

struct SocStreakPage: View {
    /// Set when shown as the popup (the X answers it); nil = the event screen (the X goes home).
    var answer: PopupAnswer? = nil
    @Environment(AppModel.self) private var app
    @Environment(\.socPrewarm) private var prewarm
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let model = SocialModel.install(app)
        let t = app.tuning.ui.tokens
        let k = m.s
        let snap = model.streak
        let now = SocTime.now(app)
        ZStack(alignment: .topLeading) {
            Color(hex: Skin.socialStreakRaceViewsSocStreakPage).frame(width: m.size.width, height: m.size.height)
            ZStack(alignment: .topLeading) {
                ArtImage(art: .streakHeader, contentMode: .fill).placed(CGRect(-18.2, 0, 429.4, 316.9)).clipped()
                LinearGradient(colors: [Color(hex: Skin.socialStreakRaceViewsSocStreakPageColors0), Color(hex: Skin.socialStreakRaceViewsSocStreakPageColors1)], startPoint: .top, endPoint: .bottom)
                    .placed(CGRect(0, 313.6, 393, 172))
                SocRails().placed(CGRect(0, 313.6, 393, 22))
                StreakRaceLettering(frame: CGRect(40.0, 298.9, 313.6, 54.7), t: t)
                let sub = GameTextStyle.s2(17.2, -0.5, [Skin.socialStreakRaceViewsSocStreakPageSub0, Skin.socialStreakRaceViewsSocStreakPageSub1], outline: Skin.socialStreakRaceViewsSocStreakPageSubOutline, 0.9, drop: 1.5)
                GameText("Beat levels without fail to get more rewards!", style: sub, maxWidth: 355).at(196.3, sub.capCentre(baseline: 373.8))
                StreakChipRow(steps: StreakStripSource.steps(app), lit: Double(app.store.state.events.streakStep), ring: 1,
                              frame: CGRect(11.7, 383.7, 372.6, 64.7), t: t)
                let end = snap?.endsAt ?? dayEnd(now)
                EventTimerChip(text: Countdown.text(SocTime.left(end, now: now)),
                               frame: CGRect(154.8, 452.7, 84.1, 29.0), textID: "streak.timer", t: t, live: (ends: end, now: now))   // FIX-2 B review: ticks
            }
            .frame(width: 393, height: 486, alignment: .topLeading)
            .scaleEffect(k, anchor: .topLeading)
            .frame(width: m.size.width, height: 486 * k, alignment: .topLeading)
            Group { if prewarm { Color.clear } else { SocListRepresentable(host: model.listHost(.streak), k: k) } }
                .frame(width: m.size.width, height: max(0, m.size.height - 485 * k))
                .offset(y: 485 * k)
            SocStreakChrome(answer: answer)
            SocReadyMarker(kind: .streak)
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .clipped()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("page.streakRace")
        .onAppear {
            guard !prewarm else { return }
            EventFinish.open(app, .streakRace)                  // B1b: the ended day's "Finished" badge goes (v582 PH-0a)
            model.appear(.streak)
            model.listHost(.streak).list.pageOpened()          // FIX-V2 F-04: open on the player's row, every open
            model.probeOpen("streakRace")
            SocialFlows.refreshEvents(app) { model.request(.streak) }
            Log.mark("event", "streakRace page visible")
        }
        .onDisappear { if !prewarm { model.disappear(.streak) } }
    }

    private func dayEnd(_ now: SocialTime) -> SocialTime {
        let r = ShellEconomy.rules(app).events.calendar
        return EventSchedule.dayStart(EventSchedule.day(now, r) + 1, r)
    }
}

/// The (i) and the X: the event screen's shell (X → home) or, as the popup, an X that answers it.
private struct SocStreakChrome: View {
    let answer: PopupAnswer?
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        ZStack(alignment: .topLeading) {
            GameButton(id: "streak.info", label: "Info", action: { SocialPopups.showInfo(app, "streakInfo") }) { SocInfoDisc() }
                .placed(m.rect(CGRect(5.3, 50.0, 40, 40), .top))
            PopupCloseButton(id: "event.streakRace.close", t: t, halo: true) {
                Log.mark("social", "streakRace close (\(answer == nil ? "page" : "popup"))")
                if let answer { answer(PopupResult.close) } else { EventPageShell<EmptyView>.close(app) }
            }
            .placed(m.rect(CGRect(332.8, 49.6, 45, 45), .top))
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
    }
}

/// The Streak Race (i) overlay (meta-053): dim 0.95; the maze icon + "Beat levels without losing!", the chips x5 [x10] x25 +
/// "Increase your score multiplier!", three mini rows + "Earn more flags than others!", the warning card with the broken heart
/// "If you fail a level the multiplier will reset!", "Tap to Continue". Staggered pops (SPEC-motion-audio §6.5).
struct SocStreakInfo: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?

    var body: some View {
        TimelineView(.animation(minimumInterval: nil, paused: shownAt.map { app.clock.gameTime() - $0 > 1.4 } ?? true)) { ctx in
            let u = shownAt.map { app.clock.gameTime(ctx.date) - $0 } ?? 0
            ZStack(alignment: .topLeading) {
                Color.clear
                SocPopIn(u: u, start: 0.18, duration: 0.10, overshoot: 1.10, at: CGPoint(x: 196.8, y: 83.3 - 13)) { SocInfoTitle(title: "Hot Streak", baseline: 83.3) }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 52.7 + 115.1 / 2, y: 133.1 + 115.4 / 2)) {
                    ArtImage(art: .infoPathIcon).placed(CGRect(52.7, 133.1, 115.1, 115.4))
                }
                SocPopIn(u: u, start: 0.35, at: CGPoint(x: 111, y: 271.7 - 6)) {
                    SocTwoLines(text: "Beat levels without losing!", centreX: 111, baselines: [271.7, 291.4], box: 110, greedy: true)
                }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 234 + 40 / 2, y: 218 + 43 / 2)) {
                    ArtImage(art: .pointerArrowYellow).placed(CGRect(237, 232, 40, 45))
                }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 165 + 207 / 2, y: 348 + 64 / 2)) {
                    SocMiniChips(steps: [5, 10, 25]).placed(CGRect(165, 345, 208, 70))
                }
                SocPopIn(u: u, start: 0.58, at: CGPoint(x: 270, y: 423.9 - 6)) {
                    SocTwoLines(text: "Increase your score multiplier!", centreX: 270, baselines: [423.9, 443.5], box: 170, greedy: true)
                }
                SocPopIn(u: u, start: 0.72, at: CGPoint(x: 234 + 40 / 2, y: 512 + 43 / 2)) {
                    ArtImage(art: .pointerArrowYellow).scaleEffect(x: -1, y: 1).placed(CGRect(234, 512, 40, 45))
                }
                SocPopIn(u: u, start: 0.72, at: CGPoint(x: 17 + 180 / 2, y: 479.4 + 120 / 2)) { SocMiniRows().placed(CGRect(14, 482, 184, 132)) }
                SocPopIn(u: u, start: 0.72, at: CGPoint(x: 112, y: 623.0 - 6)) {
                    SocTwoLines(text: "Earn more flags than others!", centreX: 112, baselines: [623.0, 642.4], box: 130, greedy: true)
                }
                SocPopIn(u: u, start: 0.88, at: CGPoint(x: 59.4 + 274.6 / 2, y: 690.6 + 55.4 / 2)) { SocWarningCard(text: "If you fail a level the multiplier will reset!", frame: CGRect(59.4, 690.6, 274.6, 55.4)) }
                if u >= 1.10 { SocTapTo(text: "Tap to Continue", baseline: 793.4).opacity(min(1, (u - 1.10) / 0.15)) }
            }
            .frame(width: 393, height: 852)
        }
        .contentShape(Rectangle())
        .onTapGesture { answer(PopupResult.close) }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("streak.info.overlay")
        .onAppear { shownAt = app.clock.gameTime() }
    }
}

/// The info overlays' title (FIX-V2 F-07: `role.infoTitle` re-measured — SPEC-ui's 42 pt flat #E3F7FF + navy extrusion did
/// not match its own evidence). Two looks (ink boxes fitted on meta-053 / 166 / 025 / 068 / meta-017, re-checked on captures):
///   .event  (Streak Race, Rocket Race, Sky Jump, Claw Challenge) 36.5 pt / −1.0: face #E3F7FF with a 1.8 pt #7EBFFF band
///           under it, a 1.3 pt #001B8B outline extruded 3.5 pt, a #25BDFF rim 4.4 pt out (1.1 low, dropped 1.9) and a
///           #001B8B edge 5.0 pt out (1.3 low, dropped 4.8) — meta-053 profiles: top 1.3 navy / 1.7 cyan, bottom 1.8 band /
///           3.0 navy / 2.6 cyan / 3.7 navy; "Claw Challenge" ink 268.2 pt wide;
///   .weekly (Weekly Contest, meta-017) 35.4 pt / −1.0: cream face #FFFCF6 → #FFF3DD, a 1.1 pt #022880 outline extruded 3.5,
///           a #007FFF rim 4.1 pt out over a #00A2F5 top light (1.2 pt high) and a #003DFF foot (7.3 pt under the ink); the
///           ink sits 2.8 pt right of the centre line (68.4 → 330.3).
struct SocInfoTitle: View {
    enum Look { case event, weekly }
    let title: LocalizedStringResource
    var baseline: CGFloat = 82.6
    var look: Look = .event

    private struct Layer { let hex: UInt32; let width: CGFloat; let dy: CGFloat; let drop: CGFloat }

    private func faceStyle(_ size: CGFloat) -> GameTextStyle {
        var face = GameTextStyle.s2(size, -1.0, look == .weekly ? [Skin.socialStreakRaceViewsSocInfoTitleFaceStyleFaceWeekly0, Skin.socialStreakRaceViewsSocInfoTitleFaceStyleFaceWeekly1] : [Skin.socialStreakRaceViewsSocInfoTitleFaceStyleFaceNotWeekly0])
        if look == .event { face.band = Color(hex: Skin.socialStreakRaceViewsSocInfoTitleFaceStyle); face.bandDY = 1.8 }
        return face
    }

    var body: some View {
        let size: CGFloat = look == .weekly ? 35.4 : 36.5
        let face = faceStyle(size)
        let layers: [Layer] = look == .weekly
            ? [Layer(hex: Skin.socialStreakRaceViewsSocInfoTitle0, width: 4.1, dy: 1.5, drop: 1.7), Layer(hex: Skin.socialStreakRaceViewsSocInfoTitle1, width: 4.1, dy: -1.2, drop: 0),
               Layer(hex: Skin.socialStreakRaceViewsSocInfoTitle2, width: 4.1, dy: 0.5, drop: 1.6), Layer(hex: Skin.socialStreakRaceViewsSocInfoTitle3, width: 1.1, dy: 0, drop: 3.5)]
            : [Layer(hex: Skin.socialStreakRaceViewsSocInfoTitle0V2, width: 5.0, dy: 1.3, drop: 4.8), Layer(hex: Skin.socialStreakRaceViewsSocInfoTitle1V2, width: 4.4, dy: 1.1, drop: 1.9),
               Layer(hex: Skin.socialStreakRaceViewsSocInfoTitle2V2, width: 1.3, dy: 0, drop: 3.5)]
        let box: CGFloat = 300
        ZStack {
            ForEach(Array(layers.enumerated()), id: \.offset) { _, l in
                GameText(title, style: GameTextStyle.s2(size, -1.0, [l.hex], outline: l.hex, l.width, drop: l.drop, dropColor: l.hex),
                         maxWidth: box)
                    .offset(y: l.dy)
            }
            GameText(title, style: face, maxWidth: box)
        }
        .at(look == .weekly ? 199.3 : 196.8, face.capCentre(baseline: baseline))
    }
}

/// A localised sentence broken into centred lines at the word boundary that balances them, one word highlighted: `hot` (a
/// localised highlight word, e.g. "fail" / "kaybedersen") where it occurs, else the first word (SPEC-ui §2.16 (i); DECISION:
/// without a captured highlight the first word is lit in every language).
struct SocTwoLines: View {
    let text: LocalizedStringResource
    let centreX: CGFloat
    let baselines: [CGFloat]
    let box: CGFloat
    var size: CGFloat = 16
    var faceHex: UInt32 = Skin.socialStreakRaceViewsSocTwoLinesFaceHex
    var hotHex: UInt32 = Skin.socialStreakRaceViewsSocTwoLinesHotHex
    var outline: UInt32? = Skin.socialStreakRaceViewsSocTwoLinesOutline
    var hot: LocalizedStringResource? = nil
    /// Fill the first line up to `box` (the phone's breaks for most lines), instead of balancing the two lines.
    var greedy = false
    /// The greedy break width when it differs from the fit box (a first line that may run wider than the second fits).
    var breakAt: CGFloat? = nil
    /// Already-resolved text (numbers formatted without grouping, `SocText.plain`), used instead of `text` / `hot`.
    var resolved: String? = nil
    var hotResolved: String? = nil

    var body: some View {
        let full = resolved ?? String(localized: text)
        // B3: the highlight run is resolved first so a CJK break never falls inside it (LineUnits keep)
        let hotWord = hotResolved ?? hot.map { String(localized: $0) }
        let keep = hotWord.map { [$0] } ?? []
        let lines = greedy ? SocTwoLines.greedyOrBalanced(full, size: size, breakAt: breakAt ?? box, box: box, parts: baselines.count,
                                                          keep: keep)
                           : SocTwoLines.split(full, size: size, parts: baselines.count, keep: keep)
        let hotLine = hotWord.flatMap { h in lines.firstIndex { $0.localizedCaseInsensitiveContains(h) } } ?? 0
        ZStack(alignment: .topLeading) {
            ForEach(Array(lines.enumerated()), id: \.offset) { i, line in
                SocHotLine(line: line, hotWord: hotWord.map { line.localizedCaseInsensitiveContains($0) ? $0 : nil }
                               ?? (i == hotLine ? LineUnits.units(line).first?.text : nil),
                           centreX: centreX, baseline: baselines[min(i, baselines.count - 1)], size: size, box: box,
                           face: faceHex, hot: hotHex, outline: outline)
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(verbatim: full))
    }

    /// The phone's greedy break while its second line still fits `box`; a longer translation (TR "Bir seviyede / kaybedersen
    /// mücadeleyi kaybedersin!") would shrink that second line, so it gets the balanced break instead.
    static func greedyOrBalanced(_ s: String, size: CGFloat, breakAt: CGFloat, box: CGFloat, parts: Int,
                                 keep: [String] = []) -> [String] {
        let g = greedy(s, size: size, box: breakAt, parts: parts, keep: keep)
        guard g.count > 1 else { return g }
        let second = GameTextLayout.make(g[1], postScriptName: GameText.blackPostScript, size: size, tracking: 0).advance
        return second > box ? split(s, size: size, parts: parts, keep: keep) : g
    }

    /// The first line takes as many words as fit in `box`, the rest go on the second.
    /// B3: words = `LineUnits` (the old space split for the space-separated languages; dictionary words in ja / zh-Hans).
    static func greedy(_ s: String, size: CGFloat, box: CGFloat, parts: Int, keep: [String] = []) -> [String] {
        let words = LineUnits.units(s, keep: keep)
        guard parts > 1, words.count > 1 else { return [s] }
        var n = 1
        while n < words.count - 0 {
            let w = GameTextLayout.make(LineUnits.join(words[..<(n + 1)]), postScriptName: GameText.blackPostScript,
                                        size: size, tracking: 0).advance
            if w > box || n + 1 == words.count { break }
            n += 1
        }
        return [LineUnits.join(words[..<n]), LineUnits.join(words[n...])]
    }

    /// Splits at the word boundary whose longest line is the shortest (at most `parts` lines, 1 or 2).
    static func split(_ s: String, size: CGFloat, parts: Int, keep: [String] = []) -> [String] {
        let words = LineUnits.units(s, keep: keep)
        guard parts > 1, words.count > 1 else { return [s] }
        func w(_ x: ArraySlice<TextUnit>) -> CGFloat {
            GameTextLayout.make(LineUnits.join(x), postScriptName: GameText.blackPostScript, size: size, tracking: 0).advance
        }
        var best: (CGFloat, [String]) = (.greatestFiniteMagnitude, [s])
        for i in 1..<words.count {
            let a = words[..<i], b = words[i...]
            let cost = max(w(a), w(b))
            if cost < best.0 { best = (cost, [LineUnits.join(a), LineUnits.join(b)]) }
        }
        return best.1
    }
}

/// One centred line, `hotWord` (if any, case-insensitive) in the highlight colour.
struct SocHotLine: View {
    let line: String
    let hotWord: String?
    let centreX: CGFloat
    let baseline: CGFloat
    let size: CGFloat
    let box: CGFloat
    let face: UInt32
    let hot: UInt32
    let outline: UInt32?

    var body: some View {
        let ow: CGFloat = outline == nil ? 0 : 1.0
        let dr: CGFloat = outline == nil ? 0 : 0.8
        let plain = GameTextStyle.s2(size, 0, [face], outline: outline, ow, drop: dr)
        let hotSt = GameTextStyle.s2(size, 0, [hot], outline: outline, ow, drop: dr)
        let r = hotWord.flatMap { line.range(of: $0, options: [.caseInsensitive]) }
        let parts: [(String, Bool)] = r.map { [(String(line[..<$0.lowerBound]), false), (String(line[$0]), true),
                                               (String(line[$0.upperBound...]), false)] } ?? [(line, false)]
        // advances that keep the spaces at the segment edges (GameTextLayout drops trailing whitespace)
        let spaceW = GameTextLayout.make("a a", postScriptName: plain.postScriptName, size: size, tracking: 0).advance
            - GameTextLayout.make("aa", postScriptName: plain.postScriptName, size: size, tracking: 0).advance
        let widths: [CGFloat] = parts.map { seg in
            let core = seg.0.trimmingCharacters(in: .whitespaces)
            let lead = seg.0.prefix { $0 == " " }.count, trail = seg.0.reversed().prefix { $0 == " " }.count
            let w = core.isEmpty ? 0 : GameTextLayout.make(core, postScriptName: plain.postScriptName, size: size, tracking: 0).advance
            return w + CGFloat(lead + trail) * spaceW
        }
        let total = widths.reduce(0, +)
        let fit = min(1, box / max(total, 1))
        let _ = FitLedger.note("socline", text: line, need: box / max(total, 1))
        let pa = plain.sized(size * fit), ph = hotSt.sized(size * fit)
        let x0 = centreX - total * fit / 2
        ZStack(alignment: .topLeading) {
            ForEach(Array(parts.enumerated()), id: \.offset) { i, p in
                let core = p.0.trimmingCharacters(in: .whitespaces)
                if !core.isEmpty {
                    let lead = CGFloat(p.0.prefix { $0 == " " }.count) * spaceW
                    let trail = CGFloat(p.0.reversed().prefix { $0 == " " }.count) * spaceW
                    let before = widths[..<i].reduce(0, +) + lead
                    let st = p.1 ? ph : pa
                    GameText(verbatim: core, style: st).at(x0 + (before + (widths[i] - lead - trail) / 2) * fit, st.capCentre(baseline: baseline))
                }
            }
        }
    }
}

/// Three mini race rows (gold / silver / bronze) with a yellow up arrow at the left (the (i) overlay's "flags" item).
private struct SocMiniRows: View {
    var body: some View {
        let looks: [(UInt32, UInt32, Int, UIArt, Int)] = [(Skin.socialStreakRaceViewsSocMiniRowsLooks0, Skin.socialStreakRaceViewsSocMiniRowsLooks0V2, 16, .rankBadgeGold, 5), (Skin.socialStreakRaceViewsSocMiniRowsLooks1, Skin.socialStreakRaceViewsSocMiniRowsLooks1V2, 15, .rankBadgeSilver, 6),
                                                         (Skin.socialStreakRaceViewsSocMiniRowsLooks2, Skin.socialStreakRaceViewsSocMiniRowsLooks2V2, 12, .rankBadgeBronze, 4)]
        ZStack(alignment: .topLeading) {
            ForEach(0..<3, id: \.self) { i in
                let (face, lip, score, badge, avatar) = looks[i]
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 7).fill(Color(hex: lip)).offset(y: 2.5)
                    RoundedRectangle(cornerRadius: 7).fill(Color(hex: face))
                    ZStack {
                        ArtImage(art: badge)
                        GameText(verbatim: "\(i + 1)", style: .s2(13, 0, [Skin.socialStreakRaceViewsSocMiniRowsStyle0], outline: [Skin.socialStreakRaceViewsSocMiniRowsOutline0, Skin.socialStreakRaceViewsSocMiniRowsOutline1, Skin.socialStreakRaceViewsSocMiniRowsOutline2][i], 1.1, drop: 0.4))
                    }
                    .frame(width: 26, height: 26).offset(x: 6)
                    SocAvatar(index: avatar).frame(width: 32, height: 32).offset(x: 36)
                    RoundedRectangle(cornerRadius: 6).fill(Color(hex: lip)).frame(width: 36, height: 20).offset(x: 118)
                    ArtImage(art: .scoreChip).frame(width: 22, height: 25).offset(x: 104)
                    GameText(verbatim: "\(score)", style: .s2(15, 0, [Skin.socialStreakRaceViewsSocMiniRowsStyle0], outline: Skin.socialStreakRaceViewsSocMiniRowsOutline, 1.2, drop: 0.5)).offset(x: 129)
                }
                .frame(width: 162, height: 36)
                .offset(x: 20 + (i == 0 ? 0 : 6), y: CGFloat(i) * 43)
            }
            ArtImage(art: .pointerArrowDown).rotationEffect(.degrees(180)).frame(width: 24, height: 33).offset(x: 3, y: 24)
        }
        .frame(width: 184, height: 132, alignment: .topLeading)
    }
}

/// x5 [x10 lit] x25 on a cream strip, the lit chip green in its gold ring (the (i) overlay's multiplier item, meta-053).
private struct SocMiniChips: View {
    let steps: [Int]
    var body: some View {
        let plain = GameTextStyle.s2(27.4, -1.5, [Skin.socialStreakRaceViewsSocMiniChipsPlain0])
        let lit = GameTextStyle.s2(31, -2.4, [Skin.socialStreakRaceViewsSocMiniChipsLit0], outline: Skin.socialStreakRaceViewsSocMiniChipsLitOutline, 1.9, drop: 1.6)
        ZStack {
            RoundedRectangle(cornerRadius: 10).fill(Color(hex: Skin.socialStreakRaceViewsSocMiniChipsFill)).frame(height: 56)
                .shadow(color: Color(hex: Skin.socialStreakRaceViewsSocMiniChipsShadow, 0.8), radius: 10)
            HStack(spacing: 0) {
                GameText(verbatim: "x\(steps[0])", style: plain).frame(width: 58)
                ZStack {
                    RoundedRectangle(cornerRadius: 12).fill(Color(hex: Skin.socialStreakRaceViewsSocMiniChipsFillV2)).frame(width: 84, height: 66)
                    RoundedRectangle(cornerRadius: 9.8)
                        .fill(LinearGradient(colors: [Color(hex: Skin.socialStreakRaceViewsSocMiniChipsColors0), Color(hex: Skin.socialStreakRaceViewsSocMiniChipsColors1)], startPoint: .top, endPoint: .bottom))
                        .frame(width: 70, height: 52)
                    GameText(verbatim: "x\(steps[1])", style: lit)
                }
                .frame(width: 92)
                GameText(verbatim: "x\(steps[2])", style: plain).frame(width: 58)
            }
        }
    }
}

/// The cream warning card with the broken heart (Streak (i), Sky Jump tutorial).
struct SocWarningCard: View {
    let text: LocalizedStringResource
    let frame: CGRect
    var body: some View {
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 8.7).fill(Color(hex: Skin.socialStreakRaceViewsSocWarningCardFill)).offset(y: 1.5)
            RoundedRectangle(cornerRadius: 8.7).fill(Color(hex: Skin.socialStreakRaceViewsSocWarningCardFillV2))
            ArtImage(art: .heartBroken).placed(CGRect(8, frame.height / 2 - 25, 54, 50))
            SocTwoLines(text: text, centreX: (frame.width + 60) / 2, baselines: [frame.height / 2 - 3, frame.height / 2 + 16],
                        box: frame.width - 72, size: 16.4, faceHex: Skin.socialStreakRaceViewsSocWarningCardFaceHex, hotHex: Skin.socialStreakRaceViewsSocWarningCardHotHex, outline: nil, hot: "fail", greedy: true,
                        breakAt: 165)
        }
        .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        .placed(frame)
    }
}
