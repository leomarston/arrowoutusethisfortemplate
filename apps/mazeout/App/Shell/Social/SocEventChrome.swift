import SwiftUI
import PathCore

// The event pages' shared chrome (kit decoupling step, docs/ROADMAP.md): helpers every event draws that used to live in one
// event's own file, so taking one event took the others. Moved here as they were (same views, same tokens, same data):
//   SocInfoTitle, SocWarningCard            from StreakRaceViews.swift (the (i) overlays' title, the broken-heart card)
//   SocInfoDisc, SocReadyMarker, SocReadyWhen, SocReady
//                                           from LeaderboardViews.swift (the blue (i) disc, the capture-ready markers)
//   SocGrantText, SocStageStrip, SocRulesText
//                                           from RocketRaceViews.swift (durations, the offers' stage strip + rules line;
//                                           the strip's tile art is now passed in by each event)
//   EventTimerChip                          from StreakBanner.swift (the cream countdown chip)
//   SocRewardIcon                           from ClawScreen.swift (a ladder reward: ∞ heart / coins / booster)
// The two-line highlighted text (SocTwoLines) is ui-chrome's (Components/TwoLineText.swift): the booster popup draws it too.

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

/// The cream warning card with the broken heart (Streak (i), Sky Jump tutorial).
struct SocWarningCard: View {
    let text: LocalizedStringResource
    let frame: CGRect
    var body: some View {
        ZStack(alignment: .topLeading) {
            RoundedRectangle(cornerRadius: 8.7).fill(Color(hex: Skin.socialStreakRaceViewsSocWarningCardFill)).offset(y: 1.5)
            RoundedRectangle(cornerRadius: 8.7).fill(Color(hex: Skin.socialStreakRaceViewsSocWarningCardFillV2))
            ArtImage(art: .livesLost).placed(CGRect(8, frame.height / 2 - 25, 54, 50))
            SocTwoLines(text: text, centreX: (frame.width + 60) / 2, baselines: [frame.height / 2 - 3, frame.height / 2 + 16],
                        box: frame.width - 72, size: 16.4, faceHex: Skin.socialStreakRaceViewsSocWarningCardFaceHex, hotHex: Skin.socialStreakRaceViewsSocWarningCardHotHex, outline: nil, hot: "fail", greedy: true,
                        breakAt: 165)
        }
        .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        .placed(frame)
    }
}

/// The blue (i) disc (SPEC-ui §1.6.20: #00A1FC, a white "i" outlined navy).
struct SocInfoDisc: View {
    var body: some View {
        Rasterized("socInfoDisc", overflow: 1) { size in
            ZStack {
                Circle().fill(Color(hex: Skin.socialLeaderboardViewsSocInfoDiscFill))
                Circle().fill(LinearGradient(colors: [Color(hex: Skin.socialLeaderboardViewsSocInfoDiscColors0), Color(hex: Skin.socialLeaderboardViewsSocInfoDiscColors1), Color(hex: Skin.socialLeaderboardViewsSocInfoDiscColors2)],
                                             startPoint: .top, endPoint: .bottom)).padding(1.5)
                Capsule().fill(Color.white).frame(width: size.width * 0.14, height: size.height * 0.36).offset(y: size.height * 0.1)
                Circle().fill(Color.white).frame(width: size.width * 0.16, height: size.width * 0.16).offset(y: -size.height * 0.2)
            }
        }
        .padding(8)
    }
}

/// Writes Documents/social-ready.json once the list shows a snapshot (captures wait for it; `-pc.capture 1` only), and
/// exposes `social.ready` (value = the list kind) for UI tests.
struct SocReadyMarker: View {
    let kind: SocListKind
    @Environment(AppModel.self) private var app

    var body: some View {
        let model = SocialModel.install(app)
        let v = model.listVersion[kind] ?? 0
        Color.clear.frame(width: 1, height: 1)
            .accessibilityElement()
            .accessibilityIdentifier("social.ready")
            .accessibilityValue(Text(verbatim: v > 0 ? kind.rawValue : "pending"))
            .onChange(of: v) { _, nv in if nv == 1 { SocReady.mark("leaderboard:\(kind.rawValue)", app: app) } }
            .onAppear { if v > 0 { SocReady.mark("leaderboard:\(kind.rawValue)", app: app) } }
    }
}

/// Marks the social ready file once `ready` holds (the event pages: their snapshot arrived).
struct SocReadyWhen: View {
    let ready: Bool
    let name: String
    @Environment(AppModel.self) private var app
    @State private var done = false
    var body: some View {
        Color.clear.frame(width: 1, height: 1)
            .accessibilityElement()
            .accessibilityIdentifier("social.ready")
            .accessibilityValue(Text(verbatim: ready ? name : "pending"))
            .onAppear { if ready && !done { done = true; SocReady.mark(name, app: app) } }
            .onChange(of: ready) { _, r in if r && !done { done = true; SocReady.mark(name, app: app) } }
    }
}

@MainActor enum SocReady {
    /// After two presented frames: the social ready file (capture mode) + a log mark.
    static func mark(_ screen: String, app: AppModel) {
        Task { @MainActor in
            if app.args.raw["pc.socialScenario"] != nil { for _ in 0..<80 where !ScenarioReady.done { try? await Task.sleep(nanoseconds: 25_000_000) } }
            await FrameWaiter.frames(2)
            CaptureReady.mark(screen: screen, app: app, file: "social-ready.json")
        }
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
/// Shared by the Rocket Race and Sky Jump offers; each passes its own tile art (`tile`: stage 1…3 and the tile's width,
/// drawn in the tile's coordinates between its plate and its "Stage n" label), so the event art stays in the event's file
/// (RocketRaceViews.swift / SkyJumpViews.swift) and neither event needs the other.
struct SocStageStrip<Tile: View>: View {
    let stage: Int
    let frame: CGRect
    let goal: Int
    /// true: the Rocket Race planets + rules; false: the Sky Jump chests + rules (purple tray).
    var space = true
    @ViewBuilder let tile: (_ stage: Int, _ tileWidth: CGFloat) -> Tile

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
                    tile(s, tileW)
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

/// A cream event countdown chip with the small stopwatch overlapping its left end (SPEC-ui §1.6.15).
/// FIX-2 lane B (review of L28): given the countdown's end (`live`), the chip ticks on its own — `LiveCountdown`'s page clock,
/// on every second, with the text drawn from cached per-glyph rasters (`GlyphRunText`: "09:34" composes, anything else is a
/// GameText); without it the chip draws `text` as given ("Finished", a lab). Before, every page drew the time of its last
/// render: "09:32" stood still on the pages (build/p/FIX2/review-B/ticks).
struct EventTimerChip: View {
    let text: String
    let frame: CGRect
    let textID: String
    let t: Tokens
    /// The countdown's end and the caller's clock reading; nil = the static `text`.
    var live: (ends: SocialTime, now: SocialTime)? = nil

    var body: some View {
        Group {
            if let live {
                LiveCountdown(ends: live.ends, now: live.now, clock: .page) { s in chip(Countdown.text(s)) }
            } else {
                chip(text)
            }
        }
        .placed(frame)
    }

    private func chip(_ text: String) -> some View {
        let style = t.text(textID, .s2(15.0, -0.6, [Skin.popupsStreakBannerEventTimerChipChipStyleText0]))
        let k = frame.height / 28
        return ZStack(alignment: .topLeading) {
            Rasterized("timerChip", overflow: 2) { _ in
                ZStack {
                    RoundedRectangle(cornerRadius: 11.8, style: .continuous).fill(Color(hex: Skin.popupsStreakBannerEventTimerChipChipFill))
                    RoundedRectangle(cornerRadius: 10.8, style: .continuous).fill(t.color("event.timerChip", Skin.popupsStreakBannerEventTimerChip)).padding(1.2)
                }
            }
            .frame(width: frame.width - 10 * k, height: frame.height).offset(x: 10 * k)
            GlyphRunText(text: text, style: style.sized(style.size * k), maxWidth: frame.width - 26 * k)
                .at(frame.width / 2 + 9 * k, style.sized(style.size * k).capCentre(baseline: frame.height * 19.5 / 28))
            InkImage(art: .hudTimerIconSmall, ink: CGRect(-3 * k, -0.5 * k, 26 * k, 28 * k))
        }
        .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("event.timer")
        .accessibilityValue(Text(verbatim: text))
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
                    ArtImage(art: small ? .livesUnlimitedSmall : .livesUnlimited).frame(width: w, height: h * 0.9)
                    let st = GameTextStyle.s2(small ? 11 : 16, -0.3, [Skin.socialClawScreenSocRewardIconSt0], outline: Skin.socialClawScreenSocRewardIconStOutline, small ? 1.0 : 1.4, drop: 0.5)
                    GameText(verbatim: SocGrantText.duration(grant.unlimitedLives), style: st, maxWidth: w * 0.8).offset(y: h * 0.28)
                } else if grant.coins > 0 {
                    ArtImage(art: .rewardCoinBowl).frame(width: w, height: h * 0.9)
                    let st = GameTextStyle.s2(small ? 10.5 : 13.5, -0.2, [Skin.socialClawScreenSocRewardIconSt0], outline: Skin.socialClawScreenSocRewardIconStOutlineV2, small ? 1.0 : 1.3, drop: 0.5)
                    GameText(verbatim: "\(grant.coins)", style: st, maxWidth: w * 0.7).offset(y: h * 0.24)
                } else if let b = grant.boosters.first(where: { $0.value > 0 }) {
                    ArtImage(art: b.key == "freeze" ? .boosterFreezeIcon : .boosterHintIcon).frame(width: w * 0.8, height: h * 0.9)
                    let st = GameTextStyle.s2(small ? 11 : 15.2, 0, [Skin.socialClawScreenSocRewardIconSt0], outline: Skin.socialClawScreenSocRewardIconStOutlineV3, 1.2, drop: 0.5)
                    GameText(verbatim: "x\(b.value)", style: st).offset(x: w * 0.28, y: h * 0.3)
                }
            }
            .frame(width: w, height: h)
        }
    }
}
