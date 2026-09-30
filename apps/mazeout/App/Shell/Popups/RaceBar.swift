import SwiftUI
import PathCore

// SHELL S2 (SPEC-ui §2.7.4 "Rocket Race bar", tok2 `raceBar.*`; VERIFIED 171 / 176). While a Rocket Race is joined it replaces
// the Streak Race strip under the win panel (same entrance: SPEC-motion-audio §5 row 16; the player's counter pops 1.25 → 1.0
// at P + 0.40, DECISION):
//   band   0 · 687.2 · 393 · 165.5 (bottom): rail #01B4FF with rivets, field #2B5DEF, a chequered finish strip at x 377-393
//   plate  135.1 · 689.9 · 123.1 · 25.4 yellow rr 6, "Rocket Race" 17.8 white outlined #800100; timer chip 313.6 · 685.9 · 73.4 · 29.4
//   tiles  5 cream tiles 59.7 × 96.4 (se n 5.3), top 736.6, x 8.7 / 80.0 / 154.7 / 228.7 / 302.3, ordered by rank DESCENDING
//          left → right (the leader beside the finish); the player's tile green 65.7 × 107.1, top 730.6. Each: a rank bubble ⌀25 on
//          the top edge (the leader's the gold badge), the avatar (44 pt frame), the name 15.3 pt #622100 (box 54), "n/5"
// The lanes come from the Rocket Race (SOC1's `RivalProvider.rocketRace` + the player's progress) through
// `RocketRaceStripSource.provider`, which GAME / SOC2 set; without a joined race there is no bar.
// The view is `RocketRaceStrip` (GlossyChrome reserves `RaceBar`, `RaceLane`, `AvatarFrame`).

struct RaceLaneVM: Equatable {
    var rank: Int
    var name: String
    var avatar: Int
    var progress: Int
    var isMe: Bool
}

struct RocketRaceStripData: Equatable {
    var lanes: [RaceLaneVM]          // any order; drawn by rank, descending left → right
    var goal: Int = 5
    var timeLeft: String
    /// FIX-2 B (review of L28): the race's end — the bar's chip then ticks (the win panel can stay up for minutes).
    var ends: SocialTime? = nil
}

@MainActor enum RocketRaceStripSource {
    /// Set by the owner of the race state (GAME's EventsDirector / SOC2's SocialModel): nil or a nil answer = no race joined.
    static var provider: ((AppModel) -> RocketRaceStripData?)?
}

struct RocketRaceStrip: View {
    let data: RocketRaceStripData
    let shownAt: Double?
    @Environment(AppModel.self) private var app

    var body: some View {
        let f = app.tuning.ui.file
        let slideAt = f.double("win.stripAt", 3.95) - f.double("win.panelAt", 3.94)
        let slideDur = f.double("win.stripDur", 0.13)
        let popAt = f.double("win.chipAt", 4.34) - f.double("win.panelAt", 3.94)
        TimelineView(.animation(minimumInterval: nil, paused: shownAt == nil)) { ctx in
            let u = shownAt.map { app.clock.sequenceTime("strip", app.clock.gameTime(ctx.date) - $0) } ?? 99
            let slide = Easing.outCubic((u - slideAt) / slideDur)
            let pop = u < popAt ? 1.25 : 1.25 - 0.25 * Easing.outBack((u - popAt) / 0.25)
            RaceBody(data: data, mePop: u < popAt + 0.3 ? pop : 1, t: app.tuning.ui.tokens)
                .offset(y: CGFloat((1 - slide) * f.double("win.raceRise", 166)))
        }
    }
}

private struct RaceBody: View {
    let data: RocketRaceStripData
    let mePop: Double
    let t: Tokens
    @Environment(AppModel.self) private var app

    var body: some View {
        let band = t.frame("raceBar.band", CGRect(0, 687.2, 393, 165.5))
        let xs = t.list("raceBar.tileX", [8.7, 80.0, 154.7, 228.7, 302.3]).map { CGFloat($0) }
        let lanes = data.lanes.sorted { $0.rank > $1.rank }
        ZStack(alignment: .topLeading) {
            Rasterized("raceBand") { _ in RaceBand(t: t) }.placed(band.insetBy(dx: -40, dy: 0))
            RacePlate(frame: t.frame("raceBar.plate", CGRect(135.1, 689.9, 123.1, 25.4)), t: t)
            EventTimerChip(text: data.timeLeft, frame: t.frame("raceBar.timer", CGRect(313.6, 685.9, 73.4, 29.4)), textID: "raceBar.timer.t", t: t,
                           live: data.ends.map { (ends: $0, now: SocTime.now(app)) })
            ForEach(Array(lanes.prefix(xs.count).enumerated()), id: \.offset) { i, lane in
                RaceTile(lane: lane, goal: data.goal, x: xs[i], leader: lane.rank == 1, pop: lane.isMe ? mePop : 1, t: t)
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("race.bar")
    }
}

private struct RaceBand: View {
    let t: Tokens
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            let side: CGFloat = 40
            ZStack(alignment: .topLeading) {
                t.color("raceBar.outline", Skin.popupsRaceBarRaceBarOutline).frame(width: w, height: h)
                t.color("raceBar.rail", Skin.popupsRaceBarRaceBarRail).frame(width: w, height: 17).offset(y: 1.3)
                LinearGradient(colors: [Color(hex: Skin.popupsRaceBarRaceBandColors0), Color(hex: Skin.popupsRaceBarRaceBandColors1)], startPoint: .top, endPoint: .bottom)
                    .frame(width: w - 2 * (side + 80), height: 17).offset(x: side + 80, y: 1.3)
                ForEach([side + 35, w - side - 35], id: \.self) { x in
                    Circle().fill(RadialGradient(colors: [Color(hex: Skin.popupsRaceBarRaceBandColors0V2), Color(hex: Skin.popupsRaceBarRaceBandColors1V2)], center: UnitPoint(x: 0.42, y: 0.38),
                                                 startRadius: 0, endRadius: 6))
                        .overlay(Circle().stroke(Color(hex: Skin.popupsRaceBarRaceBandStroke), lineWidth: 1.2))
                        .frame(width: 11.5, height: 11.5).position(x: x, y: 9.8)
                }
                t.color("band.railLine", Skin.popupsRaceBarBandRailLine).frame(width: w, height: 1.3).offset(y: 18.3)
                LinearGradient(colors: t.colors("raceBar.field", [Skin.popupsRaceBarRaceBarField0, Skin.popupsRaceBarRaceBarField1, Skin.popupsRaceBarRaceBarField2]), startPoint: .top, endPoint: .bottom)
                    .frame(width: w, height: h - 19.6).offset(y: 19.6)
                Chequer(t: t).frame(width: 16, height: h - 19.6).offset(x: side + 377, y: 19.6)
            }
            .frame(width: w, height: h, alignment: .topLeading)
        }
    }
}

private struct Chequer: View {
    let t: Tokens
    var body: some View {
        Canvas { ctx, size in
            let s: CGFloat = 5.4
            var y: CGFloat = 0, row = 0
            ctx.fill(Path(CGRect(origin: .zero, size: size)), with: .color(.white))
            while y < size.height {
                var x: CGFloat = row % 2 == 0 ? 0 : s
                while x < size.width {
                    ctx.fill(Path(CGRect(x: x, y: y, width: s, height: s)), with: .color(t.color("raceBar.chequer", Skin.popupsRaceBarRaceBarChequer)))
                    x += 2 * s
                }
                y += s; row += 1
            }
        }
    }
}

private struct RacePlate: View {
    let frame: CGRect
    let t: Tokens
    var body: some View {
        let style = t.text("raceBar.plate.t", .s2(17.8, -0.31, [Skin.popupsRaceBarRaceBarPlateT0], outline: Skin.popupsRaceBarRaceBarPlateTOutline, 1.3, drop: 1.0))
        ZStack {
            Rasterized("racePlate", overflow: 2) { _ in
                ZStack {
                    RoundedRectangle(cornerRadius: 6, style: .continuous).fill(Color(hex: Skin.popupsRaceBarRacePlateFill))
                    RoundedRectangle(cornerRadius: 5.2, style: .continuous)
                        .fill(LinearGradient(colors: [Color(hex: Skin.popupsRaceBarRacePlateColors0), Color(hex: Skin.popupsRaceBarRacePlateColors1), Color(hex: Skin.popupsRaceBarRacePlateColors2)],
                                             startPoint: .top, endPoint: .bottom))
                        .padding(1.2)
                }
            }
            GameText("Rocket Rally", style: style, maxWidth: frame.width - 10)
                .position(x: frame.width / 2, y: style.capCentre(baseline: frame.height * 18.2 / 25.4))
        }
        .frame(width: frame.width, height: frame.height)
        .placed(frame)
    }
}

private struct RaceTile: View {
    let lane: RaceLaneVM
    let goal: Int
    let x: CGFloat
    let leader: Bool
    let pop: Double
    let t: Tokens

    var body: some View {
        let me = lane.isMe
        let tile = me ? CGRect(x - 3, 730.6, 65.7, 107.1) : CGRect(x, 736.6, 59.7, 96.4)
        let name = t.text(me ? "raceBar.tileMe.n" : "raceBar.tileOther.n",
                          me ? .s2(15.1, -0.3, [Skin.popupsRaceBarRaceTileNameText0]) : .s2(15.3, 0.05, [Skin.popupsRaceBarRaceTileNameText0V2]))
        let prog = t.text(me ? "raceBar.tileMe.p" : "raceBar.tileOther.p",
                          me ? .s2(17.5, 0.3, [Skin.popupsRaceBarRaceTileProgText0], outline: Skin.popupsRaceBarRaceTileProgOutline, 1.0, drop: 0.6) : .s2(17.5, 0.3, [Skin.popupsRaceBarRaceTileProgText0V2], outline: Skin.popupsRaceBarRaceTileProgOutlineV2, 1.0, drop: 0.6))
        let rank = t.text("raceBar.rankBubble.r", .s2(16.8, 0, [Skin.popupsRaceBarRaceBarRankBubbleR0], outline: Skin.popupsRaceBarRaceBarRankBubbleROutline, 1.3, drop: 0.87))
        ZStack(alignment: .topLeading) {
            Rasterized("raceTile|\(me)", overflow: 3) { _ in TileFace(me: me) }.placed(tile)
            AvatarPortrait(index: lane.avatar, me: me).placed(CGRect(tile.midX - 22, tile.minY + 13.5, 44, 44))
            GameText(verbatim: lane.name, style: name, maxWidth: 54).at(tile.midX, name.capCentre(baseline: tile.minY + (me ? 73.2 : 69.6)))
            Capsule().fill(Color(hex: me ? Skin.popupsRaceBarRaceTileFillMe : Skin.popupsRaceBarRaceTileFillNotMe)).frame(width: 44, height: 20)
                .position(x: tile.midX, y: tile.minY + (me ? 88.5 : 83.3))
            GameText(verbatim: "\(lane.progress)/\(goal)", style: prog, maxWidth: 40)
                .scaleEffect(CGFloat(pop))
                .at(tile.midX, prog.capCentre(baseline: tile.minY + (me ? 94.4 : 89.0)))
            if leader {
                InkImage(art: .rankBadgeGold, ink: CGRect(tile.midX - 16, tile.minY - 19, 32, 32))
                GameText(verbatim: "1", style: rank).at(tile.midX, rank.capCentre(baseline: tile.minY + 2.5))
            } else {
                ZStack {
                    Circle().fill(Color(hex: Skin.popupsRaceBarRaceTileFill))
                    Circle().fill(LinearGradient(colors: [Color(hex: Skin.popupsRaceBarRaceTileColors0), Color(hex: Skin.popupsRaceBarRaceTileColors1)], startPoint: .top, endPoint: .bottom))
                        .padding(1.3)
                    Circle().fill(Color(hex: me ? Skin.popupsRaceBarRaceTileFillMeV2 : Skin.popupsRaceBarRaceTileFillNotMeV2)).padding(4.2)
                }
                .frame(width: 25, height: 25).position(x: tile.midX, y: tile.minY - 3)
                GameText(verbatim: "\(lane.rank)", style: rank).at(tile.midX, rank.capCentre(baseline: tile.minY + 2.8))
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("event.rocketRace.lane.\(lane.rank)")
        .accessibilityValue(Text(verbatim: "\(lane.progress)/\(goal)"))
    }
}

private struct TileFace: View {
    let me: Bool
    var body: some View {
        ZStack {
            Superellipse(n: 5.3).fill(Color(hex: me ? Skin.popupsRaceBarTileFaceFillMe : Skin.popupsRaceBarTileFaceFillNotMe))
            Superellipse(n: 5.3)
                .fill(LinearGradient(colors: me ? [Color(hex: Skin.popupsRaceBarTileFaceColorsMe0), Color(hex: Skin.popupsRaceBarTileFaceColorsMe1), Color(hex: Skin.popupsRaceBarTileFaceColorsMe2)]
                                              : [Color(hex: Skin.popupsRaceBarTileFaceColorsNotMe0), Color(hex: Skin.popupsRaceBarTileFaceColorsNotMe1), Color(hex: Skin.popupsRaceBarTileFaceColorsNotMe2)],
                                     startPoint: .top, endPoint: .bottom))
                .padding(EdgeInsets(top: 1.2, leading: 1.2, bottom: 3.2, trailing: 1.2))
        }
    }
}

/// A player's portrait in the blue AvatarFrame ring (the player's own in green): index 0 = the default silhouette, 1…8 = the
/// shipped portraits (SPEC-ui §2.14.2 index table: Walkie, CapGlasses, Detective, Burger, Scientist, Party, BoxHead, Notebook).
struct AvatarPortrait: View {
    let index: Int
    var me = false

    static let files = SkinNames.avatarPortraits                           // skin/names.json

    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            ZStack {
                Superellipse(n: 3.5).fill(Color(hex: me ? Skin.popupsRaceBarAvatarPortraitFillMe : Skin.popupsRaceBarAvatarPortraitFillNotMe))
                Superellipse(n: 3.5)
                    .fill(LinearGradient(colors: me ? [Color(hex: Skin.popupsRaceBarAvatarPortraitColorsMe0), Color(hex: Skin.popupsRaceBarAvatarPortraitColorsMe1)] : [Color(hex: Skin.popupsRaceBarAvatarPortraitColorsNotMe0), Color(hex: Skin.popupsRaceBarAvatarPortraitColorsNotMe1)],
                                         startPoint: .top, endPoint: .bottom))
                    .padding(1)
                Group {
                    if index >= 1 && index <= Self.files.count {
                        PathImage(path: "Art/char_avatar\(Self.files[index - 1])@3x.png", maxPixel: Int(w * 3))
                    } else {
                        DefaultSilhouette()
                    }
                }
                .clipShape(Superellipse(n: 3.8))
                .padding(w * 0.1)
            }
        }
    }
}

/// The default silhouette (#627F92 on #7B98AC, SPEC-ui §1.6.12).
struct DefaultSilhouette: View {
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            ZStack {
                Color(hex: Skin.popupsRaceBarDefaultSilhouette)
                Circle().fill(Color(hex: Skin.popupsRaceBarDefaultSilhouetteFill)).frame(width: w * 0.46, height: w * 0.46).offset(y: -h * 0.1)
                Ellipse().fill(Color(hex: Skin.popupsRaceBarDefaultSilhouetteFill)).frame(width: w * 0.98, height: h * 0.62).offset(y: h * 0.44)
            }
        }
    }
}
