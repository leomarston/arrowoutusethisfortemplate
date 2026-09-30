import SwiftUI
import PathCore

// SHELL S3, shell side of the Leaderboard and the event pages (SPEC-architecture §6.9; SPEC-ui §2.15.1-§2.15.2, §2.16-§2.19 page
// frames, §1.6.3 / §1.6.15 / §1.6.20; CONSISTENCY U-30: SegmentTabs, RankRow, TimerChip… stay UI-ART's GlossyChrome names, so
// these carry their own). SOC2 fills the bodies (`App/Shell/Social/**`, SocialEntry); SHELL owns the frame around them:
//   LeaderboardPageShell  `Screen.home(_, tab: .leaderboard)`: the navy page, the header "Leaderboard" (no X), the tab strip
//                         (Weekly | World | the player's frozen home country, localised; the curated short name below 0.7 scale,
//                         `ui.json lb.countryShort`), the Weekly countdown chip under the Weekly tab on every tab (hidden while
//                         the Weekly Contest is locked), and the tab body: "Reach level 50 to compete in Weekly Contest!" while
//                         Weekly is locked, else SOCIAL's `SocialEntry.makeLeaderboard(app:)`, which reads the selected tab from
//                         `LeaderboardShellState.shared.tab`. Tab switch = a hard cut; each tab keeps its scroll (SOC2's views).
//   EventPageShell        the common frame of the Claw / Streak Race / Rocket Race / Sky Jump pages: the content, the (i)
//                         button when given, the red X at the page-header place (355.3, 72.1) → home, where the capsule
//                         machine's pile refills (SPEC-ui §2.2.8).
//   PageTimerChip         the cream countdown chip with the small stopwatch (SPEC-ui §1.6.15 page variant).
//   PageInfoButton        the blue (i) disc.

@MainActor @Observable final class LeaderboardShellState {
    static let shared = LeaderboardShellState()
    enum Tab: String, CaseIterable { case weekly, world, country }
    var tab: Tab = .weekly
}

struct LeaderboardPageShell: View {
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let state = LeaderboardShellState.shared
        let now = app.clock.wallClock()
        // FIX-2 A: the Leaderboard TAB is part of home: home's parked-aware state proxy, not the store — parked under a level it
        // re-renders nothing on the level's store writes (the attempt at Play, the win at the clearing tap)
        let st = HomeLive.read(app)
        let status = Events.status(st, now: now, rules: ShellEconomy.rules(app))
        let weekly = status.weekly
        let bodyTop = m.y(190, .top), bodyBottom = m.y(771.7, .bottom)
        ZStack(alignment: .topLeading) {
            ShellPageBackground(t: t).frame(width: m.size.width, height: m.size.height)
            Group {
                if state.tab == .weekly && weekly == nil {
                    WeeklyLockedText().frame(width: m.size.width, height: max(0, bodyBottom - bodyTop))
                } else {
                    SocialEntry.makeLeaderboard(app: app).frame(width: m.size.width, height: max(0, bodyBottom - bodyTop))
                }
            }
            .offset(y: bodyTop)
            .accessibilityElement(children: .contain)
            .accessibilityIdentifier("lb.body")
            TopCanvas { LeaderboardTabStrip(state: state) }
            if let w = weekly {
                let s = EconomyClock.peekSocial(st, wall: now)
                PageTimerChip(seconds: Double(w.endsAt.seconds - s.seconds), id: "lb.timer",
                              live: (ends: w.endsAt, now: s, clock: .homeTab(.leaderboard)))            // FIX-2 B review: ticks in the last hour
                    .placed(m.rect(CGRect(26.7, 166.8, 86.7, 27.0), .top))
            }
            ShellPageHeader(t: t)
            PageTitle(title: "Leaderboard", t: t)
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .clipped()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.leaderboard")
        .onAppear { Log.mark("leaderboard", "open tab \(state.tab.rawValue) (weekly \(weekly == nil ? "locked" : "open"))") }
    }
}

/// The band (#167AFA, lower lip #143BB7 → #00163E) with the three tabs (selected green, 8 pt wider; others deep blue).
private struct LeaderboardTabStrip: View {
    let state: LeaderboardShellState
    @Environment(AppModel.self) private var app

    var body: some View {
        // B2: the board's country (a territory plays on its parent's board: IC -> ES) in the app's language
        let country = CountryName.label(HomeLive.read(app).social.country.map { app.tuning.social.config.model.boardCountry($0) },
                                        short: app.tuning.ui.file.value("lb.countryShort") as? [String: Any])
        ZStack(alignment: .topLeading) {
            LinearGradient(colors: [Color(hex: Skin.pagesSocialShellsLeaderboardTabStripColors0), Color(hex: Skin.pagesSocialShellsLeaderboardTabStripColors1)], startPoint: .top, endPoint: .bottom)
                .frame(width: 393, height: 76.7).position(x: 196.5, y: 110.1 + 38.35)
            LinearGradient(colors: [Color(hex: Skin.pagesSocialShellsLeaderboardTabStripColors0V2), Color(hex: Skin.pagesSocialShellsLeaderboardTabStripColors1V2)], startPoint: .top, endPoint: .bottom)
                .frame(width: 393, height: 4).position(x: 196.5, y: 188)
            tab(.weekly, "Weekly", centre: 72.7)
            tab(.world, "World", centre: 196.1)
            tab(.country, nil, centre: 319.6, verbatim: country)
        }
    }

    /// A tab centred on its measured centre; the selected one is 8 pt wider (125.4 vs 117.4, VERIFIED meta-013).
    private func tab(_ id: LeaderboardShellState.Tab, _ title: LocalizedStringResource?, centre: CGFloat, verbatim: String? = nil) -> some View {
        let on = state.tab == id
        let st = GameTextStyle.s2(23, -0.4, [Skin.pagesSocialShellsLeaderboardTabStripTabSt0, Skin.pagesSocialShellsLeaderboardTabStripTabSt1], outline: on ? Skin.pagesSocialShellsLeaderboardTabStripTabStOutlineOn : Skin.pagesSocialShellsLeaderboardTabStripTabStOutlineNotOn, 1.5, drop: 1.0)
        let w: CGFloat = on ? 125.4 : 117.4
        let frame = CGRect(centre - w / 2, 122.4, w, on ? 52.4 : 52.0)
        return GameButton(id: "leaderboard.tab.\(id.rawValue)", label: title, value: on ? "selected" : nil,   // §9.8 id
                          action: { if state.tab != id { state.tab = id } }) {
            ZStack {
                TabFace(on: on)
                if let title { GameText(title, style: st, maxWidth: 100) } else { GameText(verbatim: verbatim ?? "", style: st, maxWidth: 100) }
            }
        }
        .placed(frame)
    }
}

private struct TabFace: View {
    let on: Bool
    var body: some View {
        Rasterized("lbTab|\(on)", overflow: 1) { _ in
            ZStack {
                RoundedRectangle(cornerRadius: on ? 24 : 17).fill(Color(hex: Skin.pagesSocialShellsTabFaceFill))
                RoundedRectangle(cornerRadius: on ? 23 : 16)
                    .fill(LinearGradient(colors: on ? [Color(hex: Skin.pagesSocialShellsTabFaceColorsOn0), Color(hex: Skin.pagesSocialShellsTabFaceColorsOn1), Color(hex: Skin.pagesSocialShellsTabFaceColorsOn2)]
                                                    : [Color(hex: Skin.pagesSocialShellsTabFaceColorsNotOn0), Color(hex: Skin.pagesSocialShellsTabFaceColorsNotOn1), Color(hex: Skin.pagesSocialShellsTabFaceColorsNotOn2)],
                                         startPoint: .top, endPoint: .bottom))
                    .padding(1)
                RoundedRectangle(cornerRadius: on ? 21 : 14)
                    .fill(LinearGradient(colors: on ? [Color(hex: Skin.pagesSocialShellsTabFaceColorsOn0V2), Color(hex: Skin.pagesSocialShellsTabFaceColorsOn1)] : [Color(hex: Skin.pagesSocialShellsTabFaceColorsNotOn0V2), Color(hex: Skin.pagesSocialShellsTabFaceColorsNotOn1V2)],
                                         startPoint: .top, endPoint: .bottom))
                    .padding(EdgeInsets(top: 2, leading: 2.5, bottom: 5, trailing: 2.5))
            }
        }
    }
}

/// "Reach level 50 / to compete in / Weekly Contest!" (26 / −0.5 white outlined #022880 1.4, centre y 430, box 330; three lines
/// broken from one key).
private struct WeeklyLockedText: View {
    var body: some View {
        let st = GameTextStyle.s2(26, -0.5, [Skin.pagesSocialShellsWeeklyLockedTextSt0], outline: Skin.pagesSocialShellsWeeklyLockedTextStOutline, 1.4, drop: 1.2)
        let full = String(localized: "Reach level 50 to join the Weekly Cup!")
        let lines = Self.lines(full)
        VStack(spacing: 4) {
            ForEach(Array(lines.enumerated()), id: \.offset) { _, l in GameText(verbatim: l, style: st, maxWidth: 330) }
        }
        .offset(y: 430 - 190 - (771.7 - 190) / 2)
        .accessibilityElement()
        .accessibilityIdentifier("lb.weekly.locked")
        .accessibilityLabel(Text(verbatim: full))
    }

    /// Three lines at word boundaries (the layout breaks one key, SPEC-social §10 "layout"): the split whose widest line is the
    /// narrowest, a line never ending on an ordinal ("50." belongs with "seviyeye"): EN "Reach level 50 / to compete in /
    /// Weekly Contest!", TR "Haftalık Yarışmaya / katılmak için / 50. seviyeye ulaş!".
    static func lines(_ s: String) -> [String] {
        // B3: words = LineUnits (the old space split; dictionary words in ja / zh-Hans, which have no spaces)
        let words = LineUnits.units(s)
        guard words.count >= 3 else { return [s] }
        let st = GameTextStyle.s2(26, -0.5, [Skin.pagesSocialShellsWeeklyLockedTextLinesSt0])
        func width(_ w: ArraySlice<TextUnit>) -> CGFloat {
            GameTextLayout.make(LineUnits.join(w), postScriptName: st.postScriptName, size: st.size, tracking: st.tracking).advance
        }
        // an ordinal ("50.") reads with the next word; a cardinal at a line end is fine ("Reach level 50")
        func endsOnNumber(_ w: ArraySlice<TextUnit>) -> Bool {
            w.last.map { ($0.text.first?.isNumber ?? false) && $0.text.hasSuffix(".") } ?? false
        }
        var best: (CGFloat, [String])?
        for i in 1..<(words.count - 1) {
            for j in (i + 1)..<words.count {
                let parts = [words[..<i], words[i..<j], words[j...]]
                var cost = parts.map(width).max() ?? 0
                if endsOnNumber(parts[0]) || endsOnNumber(parts[1]) { cost += 1000 }
                if best == nil || cost < best!.0 { best = (cost, parts.map { LineUnits.join($0) }) }
            }
        }
        return best?.1 ?? [s]
    }
}

/// The player's frozen home country (its board's ISO) as a tab label: the region's name in the APP's language, a curated
/// short name when that would shrink below 0.7 (`ui.json lb.countryShort` {ISO: {language: name}} for the 13 app
/// languages), else the ISO code.
/// PUBLISH B2 (social-intl P2-1): the name follows the language the app runs in (Bundle.main.preferredLocalizations, so a
/// per-app language of Deutsch on an English device says "Türkei"), and the English "Turkey" override applies to an
/// English UI only (German "Türkei", Japanese "トルコ": iOS's name in that language).
enum CountryName {
    /// English names the phone reference shows where iOS's English region name differs (the EN Country tab reads "Turkey";
    /// iOS 16+ says "Türkiye").
    static let englishNames: [String: String] = ["TR": "Turkey"]

    /// The .lproj the app runs in ("en", "tr", "de", "pt-BR", "zh-Hans" …).
    static var appLanguage: String { Bundle.main.preferredLocalizations.first ?? "en" }

    /// The tab's country name: the English override in an English UI, else the region's name in `language`.
    static func name(_ code: String, language: String) -> String {
        if language.hasPrefix("en"), let en = englishNames[code] { return en }
        return Locale(identifier: language).localizedString(forRegionCode: code) ?? code
    }

    /// The curated short name of `code` for `language` (exact .lproj name, then its base language), if any.
    static func short(_ code: String, language: String, table: [String: Any]?) -> String? {
        guard let m = table?[code] as? [String: String] else { return nil }
        return m[language] ?? m[String(language.prefix { $0 != "-" })]
    }

    static func label(_ iso: String?, short table: [String: Any]?, language: String = appLanguage) -> String {
        let code = (iso ?? Locale.current.region?.identifier ?? "US").uppercased()
        let name = Self.name(code, language: language)
        let st = GameTextStyle.s2(23, -0.4, [Skin.pagesSocialShellsCountryNameLabelSt0])
        let w = GameTextLayout.make(name, postScriptName: st.postScriptName, size: st.size, tracking: st.tracking).advance
        guard w * 0.7 > 100 else { return name }
        return short(code, language: language, table: table) ?? code
    }
}

/// The common frame of the full-screen event pages; the X goes home (and the machine's pile refills there).
struct EventPageShell<Content: View>: View {
    var onInfo: (() -> Void)? = nil
    var infoFrame = CGRect(5.3, 50.0, 40, 40)
    @ViewBuilder var content: Content
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        ZStack(alignment: .topLeading) {
            content
            if let onInfo {
                PageInfoButton(action: onInfo).placed(m.rect(infoFrame, .top))
            }
            PopupCloseButton(id: "event.close", t: t, halo: true) { EventPageShell.close(app) }
                .placed(m.rect(CGRect(332.8, 49.6, 45, 45), .top))
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
    }

    static func close(_ app: AppModel) {
        HomeScene.requestRefill()
        app.router.go(.home(.normal, tab: .home))
    }
}

/// The blue (i) disc (SPEC-ui §1.6.20: #00A1FC, a white "i" outlined navy).
struct PageInfoButton: View {
    let action: () -> Void
    var body: some View {
        GameButton(id: "event.info", label: "Info", action: action) {
            Rasterized("infoDisc", overflow: 1) { size in
                ZStack {
                    Circle().fill(Color(hex: Skin.pagesSocialShellsPageInfoButtonFill))
                    Circle().fill(LinearGradient(colors: [Color(hex: Skin.pagesSocialShellsPageInfoButtonColors0), Color(hex: Skin.pagesSocialShellsPageInfoButtonColors1), Color(hex: Skin.pagesSocialShellsPageInfoButtonColors2)],
                                                 startPoint: .top, endPoint: .bottom)).padding(1.5)
                    Capsule().fill(Color.white).frame(width: size.width * 0.14, height: size.height * 0.36).offset(y: size.height * 0.1)
                    Circle().fill(Color.white).frame(width: size.width * 0.16, height: size.width * 0.16).offset(y: -size.height * 0.2)
                }
            }
            .padding(5)
        }
    }
}

/// The cream countdown chip (#FAE7D2 rr 12, text #622200 plain 15.4 pt, `iconStopwatchSmall` over its left end).
/// FIX-2 lane B (review of L28): given the countdown's end (`live`) the chip ticks on its own (`LiveCountdown`: `.page` on an
/// event page, `.homeTab(.leaderboard)` on the Leaderboard tab), the time drawn from cached per-glyph rasters (`GlyphRunText`).
struct PageTimerChip: View {
    let seconds: Double
    let id: String
    /// B1b (v582 PH-0a): an ended event's page — the chip reads "Finished".
    var finished = false
    /// The countdown's end, the caller's clock reading and where the chip lives; nil = the static `seconds`.
    var live: (ends: SocialTime, now: SocialTime, clock: CountdownClock)? = nil

    var body: some View {
        if !finished, let live {
            LiveCountdown(ends: live.ends, now: live.now, clock: live.clock) { s in chip(Countdown.text(s)) }
        } else {
            chip(finished ? EventWord.finished : Countdown.text(seconds))          // FIX-2 B: event.finished (B1b-r3)
        }
    }

    private func chip(_ text: String) -> some View {
        let st = GameTextStyle.s2(15.4, -0.3, [Skin.pagesSocialShellsPageTimerChipChipSt0])
        return ZStack(alignment: .topLeading) {
            Rasterized("pageChip") { _ in RoundedRectangle(cornerRadius: 12).fill(Color(hex: Skin.pagesSocialShellsPageTimerChipChipFill)) }
                .placed(CGRect(x: 12, y: 1.5, width: 74.7, height: 24))
            ArtImage(art: .hudTimerIconSmall).placed(CGRect(x: 0, y: 0, width: 24, height: 25.7))
            GlyphRunText(text: text, style: st, maxWidth: 56).at(52, st.capCentre(baseline: 19.0))
        }
        .frame(width: 86.7, height: 27, alignment: .topLeading)
        .accessibilityElement()
        .accessibilityIdentifier(id)
        .accessibilityValue(Text(verbatim: finished ? "finished" : text))
    }
}
