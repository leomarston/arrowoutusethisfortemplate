import SwiftUI
import PathCore

// SOCIAL — B1 EVENTS-P (events.md §6; PUBLISH item 14 "it should feel like 'oh this week this challenge came'"). How a new
// week's featured events are announced on the device (no server: the calendar is C3's pure EventRotation):
//   - the week-start page: once per featured event per week the home queue (G2 `HomeQueue`) opens the event's own page (the
//     ladder: Treasure Climb / Up & Away) or offer (the race: Rocket Rally / Cloud Hop) with a "New Event!" ribbon ("Double
//     Event Week!" when both race events run) across its top and a "Let's Go!" button that clears it;
//   - the NEW ribbon on the home's featured badge / bar (S3) until the player opens that event this week (`opened`);
//   - keys in `PlayerState.flags.seen`, one per event and kind ("weekStart-<event>-<week>", "opened-<event>-<week>"): a new week
//     replaces the old key, so the save does not grow with the weeks.

@MainActor @Observable final class EventAnnounce {
    static let shared = EventAnnounce()

    struct Current: Equatable {
        var event: EventID
        var double: Bool
    }

    /// The week-start page on screen now (its ribbon reads this; nil = no ribbon).
    var current: Current?

    static func weekStartKey(_ e: EventID, week: Int) -> String { "weekStart-\(e.rawValue)-\(week)" }
    static func openedKey(_ e: EventID, week: Int) -> String { "opened-\(e.rawValue)-\(week)" }

    /// Inserts `key`, dropping the same kind's keys of other weeks.
    static func mark(_ app: AppModel, _ key: String) {
        guard !app.store.state.flags.seen.contains(key), let cut = key.lastIndex(of: "-") else { return }
        let prefix = String(key[...cut])
        app.store.mutateAndSave { st in
            st.flags.seen = st.flags.seen.filter { !$0.hasPrefix(prefix) }
            st.flags.seen.insert(key)
        }
    }

    /// The event's page / offer was opened this week (the home's NEW ribbon goes).
    static func opened(_ app: AppModel, _ e: EventID) {
        let week = EventRotation.week(SocTime.now(app), ShellEconomy.rules(app).events)
        mark(app, openedKey(e, week: week))
    }

    /// The home's NEW ribbon: the rotation runs, the event is featured and live for this player, not opened this week.
    static func isNew(_ app: AppModel, _ e: EventID, status: Events.Status) -> Bool {
        guard status.rotating, status.live.featured.contains(e), let w = status.week?.week else { return false }
        return !HomeLive.read(app).flags.seen.contains(openedKey(e, week: w))
    }
}

/// B1b (v582, events.md "PH-0a"): the player OPENED an ended event's result — the Finished bar's page, the Hot Streak page or
/// list, the Leaderboard tab — so its hold goes and the new instance shows in its slot (C3 `Events.openFinished`). Saved only
/// when there was a hold (every other open writes nothing).
@MainActor enum EventFinish {
    /// B1b FEEL: the ladder slot can switch kinds when a Finished bar is opened (Treasure Climb ⇄ Up & Away): both bars' tokens
    /// are decoded at launch, off the main thread, so the new week's bar never pays an image decode in the frame it appears
    /// (Up & Away's token only once R8's art exists; `ArtStore` is thread-safe and caches the decoded bitmap).
    static func preloadLadderArt() {
        let arts: [UIArt] = [.treasureToken, .iconStopwatchSmall, .coinBowl, .heartInfiniteSmall, .boosterFreeze, .boosterHint, .iconCheck]
            + [UpAwayArt.badge].compactMap(UpAwayArt.art)
        // A4: the badges and the Up & Away token are rigs now (their idle loops): their layers are decoded here too, so a badge
        // that appears on an idle home (the weekly roll, a Finished hold opened) builds from cached bitmaps
        let rigs = ["badge_upaway_rig"] + EventBadgeKind.allCases.map(\.rig)
        let layers = rigs.compactMap { PuppetCache.rig($0) }.flatMap { r in r.layers.map { r.path($0) } }
        DispatchQueue.global(qos: .utility).async {
            _ = ArtStore.preload(arts)
            for p in layers { _ = ArtStore.image(path: p) }
        }
    }

    static func open(_ app: AppModel, _ e: EventID) {
        let now = app.clock.wallClock()
        let rules = ShellEconomy.rules(app)
        let s = app.store.state
        guard Events.finished(s, at: EconomyClock.peekSocial(s, wall: now), rules: rules).contains(where: { $0.event == e }) else { return }
        if app.store.mutateAndSave({ Events.openFinished(&$0, e, now: now, rules: rules) }) {
            Log.mark("event", "\(e.rawValue): the ended event's result opened (its Finished hold goes)")
        }
    }
}

/// B1b FEEL measurement (`-pc.finishedProbe <idleSeconds>`; nothing runs without the flag): once home is up (+2 s), a FrameProbe
/// over `idleSeconds` of the idle home (a run started before the Monday roll with `-pc.clockRate` covers the badges' flip to
/// "Finished" and the trophy "!"); then, while the ladder slot holds an ended event, its page opens exactly as the bar's tap does
/// (`router.go`) and closes with its X's call, each under its own probe (the page's first open, and the return where the new
/// week's bar replaces the Finished one). Logs `[PC][perf] finished … frames n max ms over20 k`.
@MainActor enum EventFinishProbe {
    static func run(_ app: AppModel) {
        guard let idle = app.args.raw["pc.finishedProbe"].flatMap(Double.init), idle > 0 else { return }
        Task { @MainActor in
            for _ in 0..<600 where !app.router.screen.isHome { try? await Task.sleep(nanoseconds: 50_000_000) }
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            let p = FrameProbe("finished idle home \(Int(idle)) s")
            p.start()
            try? await Task.sleep(nanoseconds: UInt64(idle * 1_000_000_000))
            p.stop()
            // a first round trip (Profile and back) pays the session's FIRST return home, which costs more whatever the page;
            // then the Finished bar's page (its first open), then — the baseline — the same kind of open of this week's live
            // ladder page (the cut every event page pays), each open + close under its own probe
            let warm = FrameProbe("warm-up round trip home → profile → home")
            warm.start()
            app.router.go(.profile)
            try? await Task.sleep(nanoseconds: 1_200_000_000)
            app.router.go(.home(.normal, tab: .home))
            try? await Task.sleep(nanoseconds: 1_500_000_000)
            warm.stop()
            for kind in ["finished", "live"] {
                let st = Events.status(app.store.state, now: app.clock.wallClock(), rules: ShellEconomy.rules(app))
                guard let lad = kind == "finished" ? st.finished.ladder : st.live.ladder else {
                    Log.mark("perf", "finished probe: no \(kind) ladder event (nothing to open)"); continue
                }
                let open = FrameProbe("\(kind) page open \(lad.rawValue)")
                open.start()
                app.router.go(.event(lad == .clawChallenge ? .claw : .balloonRise))
                try? await Task.sleep(nanoseconds: 1_500_000_000)
                open.stop()
                let back = FrameProbe("\(kind) page close → home")
                back.start()
                EventPageShell<EmptyView>.close(app)
                try? await Task.sleep(nanoseconds: 1_500_000_000)
                back.stop()
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            }
        }
    }
}

/// The week-start ribbon + "Let's Go!" over an event page or offer while it is the queue's week-start page.
struct WeekStartBanner: View {
    let event: EventID
    /// Inside a popup's 393 × 852 canvas (the race offers: the ribbon above the panel, their own "Start" stays the button);
    /// false = over a full page (scaled to the screen, with "Let's Go!").
    var onCanvas = false
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m
    /// FIX-2 lane B: a hidden warm-up copy of the page (the Loading prewarm, FIX-2 A's `ScreenWarm` a few frames before the cut)
    /// draws the ribbon for its glyph rasters but must never END the live announcement when it unmounts.
    @Environment(\.socPrewarm) private var prewarm

    var body: some View {
        if let c = EventAnnounce.shared.current, c.event == event || (c.double && ["rocketRace", "skyJump"].contains(event.rawValue)) {
            let t = app.tuning.ui.tokens
            let ribbon = GameTextStyle.s2(26, -0.8, [0xFFFFFF, 0xFFF2D2], outline: 0x891D0A, 1.6, drop: 1.6, face: .blackItalic)
            ZStack(alignment: .topLeading) {
                ZStack {
                    WeekStartRibbonShape().fill(Color(hex: 0x891D0A)).offset(y: 2.5)
                    WeekStartRibbonShape().fill(LinearGradient(colors: [Color(hex: 0xFF8A3D), Color(hex: 0xDE4E32)],
                                                               startPoint: .top, endPoint: .bottom))
                    GameText(c.double ? "Double Event Week!" : "New Event!", style: ribbon, maxWidth: 250)
                }
                .frame(width: 300, height: 50)
                .placed(CGRect(46.5, onCanvas ? 62 : 150, 300, 50))
                .allowsHitTesting(false)
                if !onCanvas {
                    FramedButton(id: "event.letsGo", title: "Let's Go!", colors: .green, frame: CGRect(106, 700, 181, 66),
                                 well: CGRect(97, 693, 199, 80), n: 4.9, style: .s2(32, -2.2, [0xFFFBF2], outline: 0x924500, 1.8, drop: 1.8),
                                 baseline: 745, centreX: 196.5, maxWidth: 150, t: t) {
                        EventAnnounce.shared.current = nil
                        Log.mark("event", "week-start \(event.rawValue): Let's Go!")
                    }
                }
            }
            .frame(width: 393, height: 852, alignment: .topLeading)
            .scaleEffect(onCanvas ? 1 : m.s, anchor: .topLeading)
            .frame(width: onCanvas ? 393 : m.size.width, height: onCanvas ? 852 : m.size.height, alignment: .topLeading)
            .accessibilityElement(children: .contain)
            .accessibilityIdentifier("event.weekStart")
            .accessibilityValue(Text(verbatim: c.double ? "double" : "new"))
            .onDisappear {                                   // the page / offer closed (X): the ribbon belongs to that one visit
                // B1b: only THIS page's / offer's own announcement. On a Double Event Week the first offer's banner also matches
                // the second offer's `current` (both race events read it), and since A3's popup hand-over (PopupHost `closing`)
                // the first offer leaves the view tree only when the second is committed — its onDisappear then came after the
                // second's `current` was set and cleared the second offer's ribbon (EventsRotationUITests:48, b7/b8)
                // FIX-2 B: not a warm-up copy's disappearance (ScreenWarm mounts the page the home queue opens, hidden, for a few
                // frames AFTER EventsDirector set `current` — its unmount cleared the real page's ribbon: EventsRotationUITests:36
                // / :237 on the FIX-2 tree)
                if !prewarm, EventAnnounce.shared.current?.event == event { EventAnnounce.shared.current = nil }
            }
        }
    }
}

/// A ribbon with notched tails.
private struct WeekStartRibbonShape: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path()
        let n = r.height * 0.32
        p.move(to: CGPoint(x: r.minX, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX - n, y: r.midY))
        p.addLine(to: CGPoint(x: r.maxX, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX + n, y: r.midY))
        p.closeSubpath()
        return p
    }
}

/// FIX-2 lane B (review of L28): the teaser's "Starts in 5h 12m" / "Starts in 09:33" line (T1's key, one GameText in the
/// language's word order). While it ticks, the next two seconds' labels are rasterised OFF the main thread one tick ahead
/// (`GameText.prefetch`, the HUD timer's way), so a tick only composites a cached image.
private struct StartsInLine: View {
    let seconds: Double
    let style: GameTextStyle
    @Environment(\.displayScale) private var displayScale

    static func text(_ seconds: Double) -> String { String(localized: "Starts in \(Countdown.text(seconds))") }

    var body: some View {
        let _ = GameText.prefetch(verbatim: [seconds - 1, seconds - 2].filter { $0 >= 0 }.map(Self.text), style: style, maxWidth: 300,
                                  scale: displayScale)
        GameText(verbatim: Self.text(seconds), style: style, maxWidth: 300)
    }
}

/// Our event names (ruling 38 / T1; the internal EventID raw values never change: they live in saves).
enum EventNames {
    static func name(_ e: EventID) -> LocalizedStringResource {
        switch e.rawValue {
        case "streakRace": return "Hot Streak"
        case "weeklyContest": return "Weekly Cup"
        case "clawChallenge": return "Treasure Climb"
        case "rocketRace": return "Rocket Rally"
        case "skyJump": return "Cloud Hop"
        default: return "Up & Away"
        }
    }
}

/// events.md §6.3: in a featured ladder event's last `teaserHours` (24 h) its page's footer names next week's pick for this
/// player — "Coming next: Up & Away" · "Starts in 5h 12m" (T1's two keys). Nothing while the rotation is off.
struct ComingNextFooter: View {
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let rules = ShellEconomy.rules(app)
        let status = Events.status(app.store.state, now: app.clock.wallClock(), rules: rules)
        let now = SocTime.now(app)
        let left = Double((status.week?.end.seconds ?? now.seconds) - now.seconds)
        if status.rotating, left > 0, left < Double(rules.events.rotation.teaserHours) * 3600,
           let next = status.nextLive.ladder, let end = status.week?.end {
            let st = GameTextStyle.s2(17, -0.4, [0xFFFFFF], outline: 0x02464D, 1.2, drop: 0.9)
            let name = String(localized: EventNames.name(next))
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 16).fill(Color(hex: 0x002629, 0.82)).frame(width: 330, height: 62).offset(x: 31.5, y: 0)
                GameText("Coming next: \(name)", style: st, maxWidth: 300).position(x: 196.5, y: st.capCentre(baseline: 25))
                // FIX-2 B review (L28): "Starts in 09:33" ticks on its own like every event countdown (it stood still)
                LiveCountdown(ends: end, now: now, clock: .page) { s in StartsInLine(seconds: s, style: st.sized(15)) }
                    .position(x: 196.5, y: st.sized(15).capCentre(baseline: 50))
            }
            .frame(width: 393, height: 62, alignment: .topLeading)
            .scaleEffect(m.s, anchor: .topLeading)
            .frame(width: m.size.width, height: 62 * m.s, alignment: .topLeading)
            .position(x: m.size.width / 2, y: m.size.height - 62 * m.s / 2 - m.safeBottom - 12)
            .allowsHitTesting(false)
            .accessibilityElement(children: .ignore)
            .accessibilityIdentifier("event.comingNext")
            .accessibilityValue(Text(verbatim: next.rawValue))
        }
    }
}
