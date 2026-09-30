import SwiftUI
import PathCore

// SHELL S3 (SPEC-architecture §6.4 items 5-6; SPEC-ui §2.2.3, §2.2.4, §2.2.6 NewsBadge; VERIFIED meta-001 / 070 / 168 / 173 / 202 /
// 204). The home's event layer: the Claw bar and the left badge column (Streak Race · Rocket Race · Sky Jump, packed from the
// top in that order; slot tops 190.8 / 293.6 / 390.3, 73.4 pt higher without the Claw bar), each an `eventBadge*` render with
// its live pedestal text — the Streak countdown (≈ 16 pt white, outline #16388C), "Join" (≈ 13 pt white, outline #380E66) or,
// once joined, the run's countdown + the rank / levels won on the art — and the trophy tab's red "!" NewsBadge.
// Everything is read from C3's `Events.status` at the wall clock (read-only; nothing is joined or rolled). The countdowns have
// minute resolution: one TimelineView tick every 20 s re-reads the status (0 main-thread work between ticks). Data SOCIAL owns
// (the Rocket Race rank, the leaderboard's "news") comes through `HomeEventHooks`, which SOC2 sets; unset = not shown.
// B1 (the weekly rotation, events.md §4.2 / §6.1): C3's status hides the featured events that are not live this week, so the
// column packs up by itself; the ladder slot is the Treasure Climb bar OR Up & Away's bar (BalloonBar.swift). While the
// rotation runs: the NEW ribbon on a featured badge / the bar's token until that event is opened this week, the ×2 gem on both
// race badges in a Double Event Week, and a badge that appears while home is on screen springs in (0 → 1.08 → 1, 0.35 s) — an
// outgoing one fades out in 0.2 s. FIX-2 lane B (L28, the phone wins — v582 PH-0a): no red / pulsing last day any more; in an
// event's LAST HOUR the chip and the badge pedestals read mm:ss ("09:34") and tick every second on their own small timeline
// (`LiveCountdown`, ClawBar.swift) while the layer keeps its 20 s tick.
// B1b (v582, events.md "PH-0a", VERIFIED across the Monday 07:00 UTC roll on the owner's phone): an ended event the player took
// part in does not vanish at the roll — its badge stays and reads "Finished" (the Hot Streak pedestal; the ladder bar keeps its
// final numbers and its timer chip reads "Finished") and the trophy tab gets the red "!" for the ended Weekly Cup, until the
// player opens the result (C3 `Events.Status.finished`, EventFinished.swift); then the new instance shows in that slot.

@MainActor enum HomeEventHooks {
    /// The player's live Rocket Race rank (1-5) while a race runs (SOC2: the race lanes' standings). nil = not drawn.
    static var rocketRank: ((AppModel) -> Int?)?
    /// Extra leaderboard news for the trophy "!" (SOC2: the Weekly rank dropped since the tab was last opened, SPEC-social §3.4).
    static var leaderboardNews: ((AppModel) -> Bool)?
}

/// The Claw bar + the badge column, re-read every 20 s.
struct HomeEventLayer: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        // FIX-A1: a parked home (hidden under a level) reads the state copy and a frozen date: its ticks find the same
        // content (equatable: nothing re-renders) and parking changes nothing here
        TimelineView(.periodic(from: .now, by: 20)) { ctx in
            let now = app.clock.wallClock(HomeLive.shared.eventsClock(ctx.date))
            let s = HomeLive.read(app)
            let rules = ShellEconomy.rules(app)
            let status = Events.status(s, now: now, rules: rules)
            let t = EconomyClock.peekSocial(s, wall: now)
            let news = Set(status.live.featured.filter { EventAnnounce.isNew(app, $0, status: status) }.map(\.rawValue))
            HomeEventContent(status: status, now: t, news: news).equatable()
        }
    }
}

private struct HomeEventContent: View, Equatable {
    let status: Events.Status
    let now: SocialTime
    /// B1: the featured events still showing their NEW ribbon this week.
    var news: Set<String> = []

    static func == (a: HomeEventContent, b: HomeEventContent) -> Bool { a.status == b.status && a.now == b.now && a.news == b.news }

    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let slots = t.file.doubles("layout.eventBadgeSlots", [190.8, 293.6, 390.3])
        let held = status.finished
        let lift = status.claw == nil && status.balloon == nil && held.ladder == nil
            ? CGFloat(t.number("home.eventColumnNoClawLift", 73.4)) : 0
        let badges = EventBadgeKind.visible(status)
        let double = status.rotating && status.live.race.count > 1
        // B1b: an ended ladder event holds the slot ("Finished") until its page is opened. ONE branch per bar kind, so the roll
        // (live → Finished) and the open (Finished → this week's bar of the same kind) keep the bar's identity: only its chip /
        // numbers change in that frame (FEEL: no view tree rebuilt on an idle home)
        let clawShown = held.claw ?? (held.balloon == nil ? status.claw : nil)
        let balloonShown = held.balloon ?? status.balloon
        ZStack(alignment: .topLeading) {
            if !FinishedPrewarm.done { FinishedPrewarm(t: t) }
            // B1b FEEL: while the slot holds last week's bar, the texts this week's bar will draw (its "n/target" and its
            // countdown) are made OFF the main thread, so opening the Finished page and coming back swaps bars without drawing
            // glyphs in that frame (Release sim before: one 69 ms frame at that return; the bars' images are decoded at launch,
            // EventFinish.preloadLadderArt). Only plain texts: a hidden copy of a bar would publish its anchors and its button.
            if held.ladder != nil, let next = Self.nextBarTexts(status) {
                ZStack {
                    ClawValueText(text: next.value, t: t, origin: .zero)
                    GlyphRunText(text: Countdown.text(Double(next.ends.seconds - now.seconds)),
                                 style: CountdownChip.textStyle(t), maxWidth: 54)
                }
                .environment(\.gameTextDeferred, true)
                .opacity(0)
                .allowsHitTesting(false)
                .accessibilityHidden(true)
            }
            if let claw = clawShown {
                let ended = held.claw != nil
                ClawBar(claw: claw, multiplier: status.multiplier, now: now,
                        isNew: !ended && news.contains(EventID.clawChallenge.rawValue), finished: ended)
            } else if let balloon = balloonShown {
                let ended = held.balloon != nil
                BalloonBar(balloon: balloon, multiplier: status.multiplier, now: now,
                           isNew: !ended && news.contains(EventID.balloonRise.rawValue), finished: ended)
            }
            ForEach(Array(badges.enumerated()), id: \.element) { i, kind in
                ZStack(alignment: .topLeading) {
                    EventBadge(kind: kind, status: status, now: now, t: t)
                    if kind != .streakRace {
                        if news.contains(kind.rawValue) { NewRibbon().placed(CGRect(44, -4, 40, 18)).allowsHitTesting(false) }
                        if double { DoubleGem().placed(CGRect(-4, -2, 30, 26)).allowsHitTesting(false) }
                    }
                }
                .frame(width: 80, height: 84, alignment: .topLeading)
                .transition(.asymmetric(insertion: .scale(scale: 0.01).animation(.spring(duration: 0.35, bounce: 0.45)),
                                        removal: .opacity.animation(.linear(duration: 0.2))))
                .placed(m.rect(CGRect(x: 6.7, y: CGFloat(slots[min(i, slots.count - 1)]) - lift - 0.6, width: 80, height: 84), .top))
            }
        }
    }

    /// B1b: the value text and the end of this week's ladder bar (what ClawBar / BalloonBar will draw once the hold goes).
    static func nextBarTexts(_ s: Events.Status) -> (value: String, ends: SocialTime)? {
        if let c = s.claw { return ("\(c.points)/\(c.target)", c.endsAt) }
        if let b = s.balloon { return (b.goal.map { "\(b.streak)/\($0)" } ?? "\(b.streak)", b.endsAt) }
        return nil
    }
}

/// B1b FEEL: the rasters the roll's flip draws first — the word "Finished" in the Hot Streak pedestal's and the ladder chip's
/// exact styles — are made once per launch, off the main thread, while home is first built (under Loading), so the flip on an
/// idle home composites cached images instead of drawing glyphs in its frame (Debug probe before: 39 + 27 ms at the flip).
private struct FinishedPrewarm: View {
    @MainActor static var done = false
    let t: Tokens
    var body: some View {
        ZStack {
            GlyphRunText(text: EventWord.finished, style: CountdownChip.textStyle(t), maxWidth: CountdownChip.finishedMaxWidth(t))
            GameText(verbatim: EventWord.finished, style: EventBadge.pedestalStyle(t, blue: true), maxWidth: EventBadge.finishedMaxWidth(t))
            // the chip's face
            CountdownChip(seconds: 0, t: t, id: "prewarm.chip", finished: true).frame(width: 80, height: 25.7)
        }
        .environment(\.gameTextDeferred, true)
        .opacity(0)
        .allowsHitTesting(false)
        .accessibilityHidden(true)
        .onAppear { Task { @MainActor in try? await Task.sleep(nanoseconds: 3_000_000_000); FinishedPrewarm.done = true } }
    }
}

enum EventBadgeKind: String, CaseIterable, Hashable {
    case streakRace, rocketRace, skyJump

    /// The column order (SPEC-ui §2.2.4): Streak, Rocket, Sky Jump; absent ones pack up.
    static func visible(_ s: Events.Status) -> [EventBadgeKind] {
        var out: [EventBadgeKind] = []
        if s.streakRace != nil || s.finished.streakRace != nil { out.append(.streakRace) }      // B1b: or its Finished hold
        if s.rocketRace != nil { out.append(.rocketRace) }
        if s.skyJump != nil { out.append(.skyJump) }
        return out
    }

    /// A4 (R3 HOME, art/lanes/home.handoff.json "badges"): the D1 badge's full render (the preload and the fallback)…
    var art: UIArt {
        switch self {
        case .streakRace: return .eventStreakRaceBadge
        case .rocketRace: return .eventRocketRaceBadge
        case .skyJump: return .eventSkyJumpBadge
        }
    }

    /// … and its layers (body / moving part / smoke), looped by ui.json `puppet.<rig>` (OD5 / ruling 39, motion-catalog §6.4:
    /// the pennants wave, the rocket lifts off in its exhaust, the drum hops; the phases stagger them).
    var rig: String {
        switch self {
        case .streakRace: return ArtRig.eventStreakRaceBadge.folder
        case .rocketRace: return ArtRig.eventRocketRaceBadge.folder
        case .skyJump: return ArtRig.eventSkyJumpBadge.folder
        }
    }
}

/// One badge (80 × 84 pt art frame; the pedestal text is live).
struct EventBadge: View {
    let kind: EventBadgeKind
    let status: Events.Status
    let now: SocialTime
    let t: Tokens
    @Environment(AppModel.self) private var app
    @Environment(\.displayScale) private var displayScale

    var body: some View {
        let state = badgeState
        GameButton(id: "home.event.\(kind.rawValue)", label: label, value: state.value, action: open) {
            ZStack(alignment: .topLeading) {
                if let rig = PuppetCache.rig(kind.rig) {
                    // A4: the badge as its rig (idle loop on the render server); the number on the art rides the moving part
                    let freeze = app.clock.freezeAt.flatMap { $0.sequence == "puppets" ? $0.t : nil }
                    BadgePuppet(rig: rig, motion: PuppetMotion(app.tuning.ui.file, rig: kind.rig), clock: app.clock,
                                animate: !app.args.capture || freeze != nil, freezeAt: freeze,
                                rider: state.onArt.flatMap { rider($0) })
                        .frame(width: 80, height: 84)
                        .accessibilityHidden(true)
                    pedestal(state)
                } else {
                    ArtImage(art: kind.art).frame(width: 80, height: 84)
                    pedestal(state)
                    if let n = state.onArt { artNumber(n) }
                }
            }
            .frame(width: 80, height: 84, alignment: .topLeading)
        }
        .anchor(.custom("home.event.\(kind.rawValue)"))
    }

    /// A4: the number on the art as a raster riding the rig layer it sits on (R3's live anchors on the D1 renders: the Rocket
    /// Rally porthole (40, 30.45), the Cloud Hop drum's tag (40, 32.63)), in the same GameText style as before.
    private func rider(_ n: Int) -> PuppetRider? {
        let (layer, centre, st) = riderSpec
        let r = GameTextRider.raster("\(n)", style: st, scale: max(displayScale, 1))
        return r.map { PuppetRider(layer: layer, image: $0.image, size: $0.size, centre: centre, scale: max(displayScale, 1),
                                   key: "\(n)") }
    }

    private var riderSpec: (String, CGPoint, GameTextStyle) {
        if kind == .rocketRace {
            return ("rocket", CGPoint(x: 40.0, y: 30.45), GameTextStyle.s2(20, 0, [Skin.homeEventBadgesEventBadgeRiderSpec0], outline: Skin.homeEventBadgesEventBadgeRiderSpecOutline, 1.6, drop: 1.0))
        }
        return ("drum", CGPoint(x: 40.0, y: 32.63), GameTextStyle.s2(15.6, 0, [Skin.homeEventBadgesEventBadgeRiderSpec0], outline: Skin.homeEventBadgesEventBadgeRiderSpecOutlineV2, 1.4, drop: 0.8))
    }

    private var label: LocalizedStringResource {
        switch kind {
        case .streakRace: return "Hot Streak"
        case .rocketRace: return "Rocket Rally"
        case .skyJump: return "Cloud Hop"
        }
    }

    struct BadgeState {
        var join: Bool
        var countdown: Double?
        /// FIX-2 B: the instance's end (the pedestal ticks mm:ss in its last hour, `LiveCountdown`).
        var ends: SocialTime?
        var onArt: Int?
        var value: String
        /// B1b: the ended instance waits for its result to be opened ("Finished" on the pedestal).
        var finished = false
    }

    private var badgeState: BadgeState {
        switch kind {
        case .streakRace:
            if status.finished.streakRace != nil {
                return BadgeState(join: false, countdown: nil, onArt: nil, value: "finished", finished: true)
            }
            let left = Double((status.streakRace?.endsAt.seconds ?? now.seconds) - now.seconds)
            return BadgeState(join: false, countdown: left, ends: status.streakRace?.endsAt, onArt: nil, value: "timer:" + Countdown.text(left))
        case .rocketRace:
            guard let r = status.rocketRace, r.progress != nil else { return BadgeState(join: true, countdown: nil, onArt: nil, value: "join") }
            let left = Double(r.endsAt.seconds - now.seconds)
            let rank = HomeEventHooks.rocketRank?(app)
            return BadgeState(join: false, countdown: left, ends: r.endsAt, onArt: rank,
                              value: rank.map { "rank:\($0)" } ?? "timer:" + Countdown.text(left))
        case .skyJump:
            guard let r = status.skyJump, let won = r.progress else { return BadgeState(join: true, countdown: nil, onArt: nil, value: "join") }
            let left = Double(r.endsAt.seconds - now.seconds)
            return BadgeState(join: false, countdown: left, ends: r.endsAt, onArt: won, value: "won:\(won) timer:" + Countdown.text(left))
        }
    }

    /// The pedestal plate's live text (VERIFIED crops `homeInf/*Badge.png`, 202 / 070).
    @ViewBuilder private func pedestal(_ s: BadgeState) -> some View {
        let blue = kind == .streakRace
        if s.join {
            let st = t.text("home.eventBadge.join", .s2(10.8, -0.3, [Skin.homeEventBadgesHomeEventBadgeJoin0], outline: Skin.homeEventBadgesHomeEventBadgeJoinOutline, 0.9, drop: 0.9))
            GameText("Join", style: st, maxWidth: 50).at(40.6, st.capCentre(baseline: CGFloat(t.number("home.eventBadge.textBaseline", 71.0))))
        } else if let c = s.countdown {
            let st = Self.pedestalStyle(t, blue: blue)
            let y = st.capCentre(baseline: CGFloat(t.number("home.eventBadge.textBaseline", 71.0)))
            if let ends = s.ends {
                // FIX-2 B (L28): mm:ss ticking every second in the last hour, on the pedestal's own small timeline
                LiveCountdown(ends: ends, now: now) { left in
                    GlyphRunText(text: Countdown.text(left), style: st, maxWidth: 62).at(40.6, y)
                }
            } else {
                GlyphRunText(text: Countdown.text(c), style: st, maxWidth: 62).at(40.6, y)
            }
        } else if s.finished {
            // B1b (v582 PH-0a): the countdown's place and style, the word instead of the time, fitted inside the plate like
            // v582's (≈ 41 pt wide on the 1178 px shot: at most 44 pt)
            let st = Self.pedestalStyle(t, blue: blue)
            GameText(verbatim: EventWord.finished, style: st, maxWidth: Self.finishedMaxWidth(t))      // FIX-2 B: event.finished
                .at(40.6, st.capCentre(baseline: CGFloat(t.number("home.eventBadge.textBaseline", 71.0))))
        }
    }

    /// The pedestal's countdown style (B1b: shared with the Finished prewarm, so both hit the same GameText raster).
    static func pedestalStyle(_ t: Tokens, blue: Bool) -> GameTextStyle {
        t.text(blue ? "home.eventBadge.streakTimer" : "home.eventBadge.timer",
               .s2(13.0, -0.35, [Skin.homeEventBadgesEventBadgePedestalStyleText0], outline: blue ? Skin.homeEventBadgesEventBadgePedestalStyleOutlineBlue : Skin.homeEventBadgesEventBadgePedestalStyleOutlineNotBlue, 1.0, drop: 0.9))
    }
    /// B1b: the width "Finished" is fitted to on the pedestal (v582's ≈ 41 pt, PH-0a).
    static func finishedMaxWidth(_ t: Tokens) -> CGFloat { CGFloat(t.number("home.eventBadge.finishedMaxWidth", 44)) }

    /// The number drawn on the art: the Rocket Race rank on the hex (white 20 pt, outline #0F2C80) or the Sky Jump levels won
    /// on the drum (15.6 pt, outline #DB2B6E) (VERIFIED 173 "4", 070 "0").
    @ViewBuilder private func artNumber(_ n: Int) -> some View {
        if kind == .rocketRace {
            let st = GameTextStyle.s2(20, 0, [Skin.homeEventBadgesEventBadgeArtNumberSt0], outline: Skin.homeEventBadgesEventBadgeArtNumberStOutline, 1.6, drop: 1.0)
            GameText(verbatim: "\(n)", style: st).at(40.6, st.capCentre(baseline: 39))
        } else {
            let st = GameTextStyle.s2(15.6, 0, [Skin.homeEventBadgesEventBadgeArtNumberSt0], outline: Skin.homeEventBadgesEventBadgeArtNumberStOutlineV2, 1.4, drop: 0.8)
            GameText(verbatim: "\(n)", style: st).at(40.2, st.capCentre(baseline: 40.5))
        }
    }

    private func open() {
        switch kind {
        case .streakRace:
            app.router.go(.event(.streakRace))
        case .rocketRace:
            if status.rocketRace?.progress != nil { app.router.go(.event(.rocketRace)) } else {
                Task { @MainActor in _ = await app.popups.present(Popup<PopupResult>.rocketRace(.offer)) }
            }
        case .skyJump:
            if status.skyJump?.progress != nil { app.router.go(.event(.skyJump)) } else {
                Task { @MainActor in _ = await app.popups.present(Popup<PopupResult>.skyJump(.offer)) }
            }
        }
    }
}

/// The trophy tab's red "!" (SPEC-ui §1.6.19 / §2.2.6: ⌀15.7 at (332.6, 778.7), dark-red outline #760F16). SPEC-social §3.4
/// DECISION: shown while a Weekly / Streak Race result is claimable, or when SOC2 reports news (the Weekly rank dropped since the
/// tab was last opened); hidden on the Leaderboard tab itself. B1b (v582 PH-0a, VERIFIED: the "!" appears AT the Monday roll on
/// an idle home): also while the ended Weekly Cup the player took part in is held (until the Leaderboard is opened or its
/// prize claimed) — re-read every 20 s like the event layer, so it appears at the roll without a home visit.
struct TrophyNewsBadge: View {
    let tab: HomeTab
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    static func hasNews(_ app: AppModel, now: Date) -> Bool {
        if app.args.raw["pc.lbNews"] == "1" { return true }                  // SHELL-private capture flag (the 202 look)
        let s = HomeLive.read(app)
        if s.events.claims.contains(where: { $0.kind == .weeklyPrize || $0.kind == .streakRacePrize }) { return true }
        let held = Events.finished(s, at: EconomyClock.peekSocial(s, wall: now), rules: ShellEconomy.rules(app))
        if held.contains(where: { $0.event == .weeklyContest }) { return true }
        return HomeEventHooks.leaderboardNews?(app) ?? false
    }

    /// B1b FEEL: the dot's raster is made once while home is first built (the "!" can first appear AT the roll on an idle home).
    @MainActor static var warmed = false

    var body: some View {
        if tab != .leaderboard {
            TimelineView(.periodic(from: .now, by: 20)) { ctx in
                let r = m.rect(app.tuning.ui.tokens.frame("home.newsBadge", CGRect(332.6, 778.7, 15.7, 15.0)), .bottom)
                if Self.hasNews(app, now: app.clock.wallClock(HomeLive.shared.eventsClock(ctx.date))) {
                    NewsDot().frame(width: r.width + 2, height: r.width + 2).position(x: r.midX, y: r.midY)
                        .accessibilityElement()
                        .accessibilityIdentifier("nav.leaderboard.news")
                } else if !Self.warmed {
                    NewsDot().frame(width: r.width + 2, height: r.width + 2).position(x: r.midX, y: r.midY)
                        .opacity(0)
                        .accessibilityHidden(true)
                        .onAppear { TrophyNewsBadge.warmed = true }
                }
            }
            .allowsHitTesting(false)
        }
    }
}

private struct NewsDot: View {
    var body: some View {
        Rasterized("newsDot", overflow: 1) { size in
            ZStack {
                Circle().fill(Color(hex: Skin.homeEventBadgesNewsDotFill))
                Circle().fill(RadialGradient(colors: [Color(hex: Skin.homeEventBadgesNewsDotColors0), Color(hex: Skin.homeEventBadgesNewsDotColors1), Color(hex: Skin.homeEventBadgesNewsDotColors2)],
                                             center: UnitPoint(x: 0.45, y: 0.35), startRadius: 0, endRadius: size.width * 0.5))
                    .padding(1.1)
                Capsule().fill(Color.white).frame(width: size.width * 0.16, height: size.height * 0.40).offset(y: -size.height * 0.08)
                Circle().fill(Color.white).frame(width: size.width * 0.17, height: size.width * 0.17).offset(y: size.height * 0.24)
            }
        }
    }
}

/// A4: a GameText label as ONE raster with its size, laid out exactly as `GameText` lays itself out (its frame is centred on
/// the advance's middle and the cap middle), for a CALayer that must move on the render server (`PuppetRider`).
@MainActor enum GameTextRider {
    static func raster(_ text: String, style: GameTextStyle, maxWidth: CGFloat? = nil, scale: CGFloat) -> (image: CGImage, size: CGSize)? {
        let g = GameText(verbatim: text, style: style, maxWidth: maxWidth)
        let l = g.layout
        let st = g.effective
        let pad = st.outlineWidth + 1.5
        let halfW = max(l.advance / 2, l.advance / 2 - l.inkBounds.minX, l.inkBounds.maxX - l.advance / 2) + pad
        let centreY = -GameText.capHeight(postScriptName: style.postScriptName, size: style.size) / 2
        let up = max(l.ascent, -l.inkBounds.minY) + pad - (-centreY)
        let down = max(l.descent, l.inkBounds.maxY) + pad + max(st.drop, st.bandDY) - centreY
        let halfH = max(up, down)
        let size = CGSize(width: halfW * 2, height: halfH * 2)
        let origin = CGPoint(x: size.width / 2 - l.advance / 2, y: size.height / 2 - centreY)
        return GameTextRaster.image(l, style: st, size: size, origin: origin, scale: scale).map { ($0, size) }
    }
}
