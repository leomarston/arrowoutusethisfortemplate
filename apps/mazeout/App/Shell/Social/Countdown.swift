import SwiftUI
import PathCore

// The event countdowns (kit decoupling step, docs/ROADMAP.md): ONE formatter (`Countdown`), the live ticking wrapper
// (`LiveCountdown` + its clock and schedule), the home's blue countdown chip and the ended-event word. Every event page, the
// home bars and badges, the win strips and the leaderboard's Weekly chip use them; they were in ClawBar.swift (owned by core
// because of that). Moved as they were; the home's parked-state reads go through `ShellScreens.home` (HomeLive / HomeTabStrip
// behind it) so the social chrome needs no home screen.

/// An event countdown. FIX-2 lane B (L28 / F-10 — the phone wins, v582 PH-0a build/p/PH0a/before-reset.png): ONE formatter for
/// every event countdown (the home chip and badges, the event pages, the win strips, the race bars): ≥ 1 day "3d 5h", ≥ 1 hour
/// "5h 13m" — always with its minutes ("19h 0m", as the win strip always read; was "19h" here), under an hour "mm:ss"
/// ("09:34", two-digit minutes like the lives pill; was "9m"). Floored. The "mm:ss" is digits and a colon in every language.
enum Countdown {
    /// The last hour: the text reads mm:ss and home ticks it every second (`LiveCountdown`).
    static let lastHour: Double = 3600

    static func text(_ seconds: Double) -> String {
        let s = max(0, Int(seconds.rounded(.down)))
        let d = s / 86_400, h = (s % 86_400) / 3600, m = (s % 3600) / 60
        if d > 0 { return String(localized: "\(d)d \(h)h") }
        if h > 0 { return String(localized: "\(h)h \(m)m") }
        return String(format: "%02d:%02d", m, s % 60)
    }
}

/// FIX-2 lane B (L28): an event countdown, live. The social clock counts whole seconds, so a countdown's text can only change
/// at a whole second of the wall clock: the view re-reads the clock on its own small TimelineView exactly there
/// (`CountdownSchedule`: once a second, on the second — not 4 polls a second landing up to 250 ms late), and its content is
/// equatable, so it re-renders only when the TEXT changes and nothing around it (bars, badges, rigs, the page) re-renders.
/// Where it runs (`CountdownClock`):
///  - `.home` (the home bars and badges): at or above an hour the event layer's 20 s tick is enough (the text has minute
///    resolution); in the LAST HOUR (+ one layer tick before it, so "1h 0m" → "59:59" lands on its second) it ticks. Parked
///    under a level (`HomeLive.active` false) the timeline pauses and reads the date home last drew (it never records one:
///    the layer's own parked-date logic is untouched).
///  - `.homeTab(tab)` (a chip on a home tab page, the Leaderboard's Weekly Cup): as `.home`, and paused while that tab page
///    is not drawn (`HomeTabStrip.shown`), so a hidden tab never re-renders.
///  - `.page` (the event pages, their offers and the win panel's strips — FIX-2 B review: they drew the time their page
///    last rendered, so "09:32" stood still, or moved in 5 s steps with the social refresh): always ticks, from the store's
///    clock (the minute values above an hour turn on time as well); a hidden warm-up copy (`socPrewarm`) draws once, static.
struct LiveCountdown<Content: View>: View {
    let ends: SocialTime
    /// The caller's clock reading (home: the event layer's tick; a page: its body time) — the static draw.
    let now: SocialTime
    var clock: CountdownClock = .home
    @ViewBuilder let content: (Double) -> Content
    @Environment(AppModel.self) private var app
    @Environment(\.socPrewarm) private var prewarm

    static func ticks(_ seconds: Double) -> Bool { seconds > -1 && seconds < Countdown.lastHour + 20 }

    var body: some View {
        let left = Double(ends.seconds - now.seconds)
        switch clock {
        case .home, .homeTab:
            if Self.ticks(left) {
                let home = ShellScreens.home                    // HomeLive / HomeTabStrip (the home component's hooks)
                let active = home?.isActive ?? true
                let shown: Bool = {
                    if case .homeTab(let tab) = clock { return home?.isTabShown(tab) ?? true }
                    return true
                }()
                TimelineView(CountdownSchedule(clock: app.clock, paused: !(active && shown))) { ctx in
                    let date = active ? ctx.date : (home?.eventsDrawnAt ?? ctx.date)
                    let t = EconomyClock.peekSocial(ShellScreens.homeState(app), wall: app.clock.wallClock(date))
                    LiveCountdownFrame(seconds: Double(ends.seconds - t.seconds), content: content).equatable()
                }
            } else {
                content(left)
            }
        case .page:
            if prewarm || left <= -1 {
                content(left)
            } else {
                TimelineView(CountdownSchedule(clock: app.clock, paused: false)) { ctx in
                    let t = EconomyClock.peekSocial(app.store.state, wall: app.clock.wallClock(ctx.date))
                    LiveCountdownFrame(seconds: Double(ends.seconds - t.seconds), content: content).equatable()
                }
            }
        }
    }
}

/// FIX-2 lane B (review of L28): where a `LiveCountdown` lives (its clock and when it pauses).
enum CountdownClock: Equatable { case home, homeTab(HomeTab), page }

/// FIX-2 lane B (review of L28): the moments a countdown's text can change — the wall clock's whole seconds (the social clock
/// is `max(⌊wall⌋, highWater)` and every event end is a whole second). `MotionClock.wallClock` maps a real date linearly (the
/// real time, or `-pc.now` running at `-pc.clockRate`, + `-pc.clockOffset`): `anchor` is a real date 3 ms after the wall
/// clock's next whole second (so ⌊wall⌋ there is already the new second) and `period` the real length of one wall second.
/// A stopped clock (capture mode, `-pc.clockRate 0`) or a paused countdown gives its start only: one draw, no ticks.
struct CountdownSchedule: TimelineSchedule {
    let anchor: Date
    /// Real seconds per wall second; 0 = the clock stands.
    let period: TimeInterval
    let paused: Bool

    @MainActor init(clock: MotionClock, paused: Bool) {
        let real = Date()
        let w0 = clock.wallClock(real).timeIntervalSince1970
        let rate = clock.wallClock(real.addingTimeInterval(1)).timeIntervalSince1970 - w0
        self.init(real: real, wall: w0, rate: rate, paused: paused)
    }

    /// `wall` = the wall clock at the real date `real` (seconds since 1970), `rate` = wall seconds per real second.
    init(real: Date, wall: Double, rate: Double, paused: Bool) {
        self.paused = paused
        guard rate > 1e-6 else { period = 0; anchor = real; return }
        period = 1 / rate
        anchor = real.addingTimeInterval((wall.rounded(.down) + 1 - wall) * period + 0.003)
    }

    func entries(from start: Date, mode: TimelineScheduleMode) -> AnyIterator<Date> {
        var first: Date? = start
        guard !paused, period > 0 else { return AnyIterator { defer { first = nil }; return first } }
        var next = anchor.addingTimeInterval(((start.timeIntervalSince(anchor) / period).rounded(.down) + 1) * period)
        return AnyIterator {
            if let f = first { first = nil; return f }
            defer { next = next.addingTimeInterval(period) }
            return next
        }
    }
}

/// Re-renders only when the countdown's TEXT changes (the timeline checks once a second, on the second).
private struct LiveCountdownFrame<Content: View>: View, Equatable {
    let seconds: Double
    let content: (Double) -> Content
    static func == (a: Self, b: Self) -> Bool { Countdown.text(a.seconds) == Countdown.text(b.seconds) }
    var body: some View { content(seconds) }
}

/// The blue HUD-style countdown chip (SPEC-ui §1.6.15 home variant: #0095FD, white text outlined #0F2C80 1.0) with the small
/// stopwatch over its left end. FIX-2 lane B (L28, the phone wins): the chip stays BLUE in the event's last day and hour, with
/// no pulse (v582 PH-0a: "09:34" on the blue chip; B1's red face + "Last day" pulse are gone), and ticks mm:ss in the last hour.
struct CountdownChip: View {
    let seconds: Double
    let t: Tokens
    let id: String
    /// B1b (v582 PH-0a, VERIFIED): the event ended and waits for its result to be opened — the same blue chip reads "Finished".
    var finished = false
    /// FIX-2 B: the event's end and the layer's tick — the last hour then ticks every second (`LiveCountdown`); nil = static.
    var live: (ends: SocialTime, now: SocialTime)?
    /// The chip's text style (B1b: shared with the Finished prewarm, so both hit the same GameText raster).
    static func textStyle(_ t: Tokens) -> GameTextStyle {
        t.text("home.clawTimerChip.timer", .s2(16.3, -0.3, [Skin.homeClawBarHomeClawTimerChipTimer0], outline: Skin.homeClawBarHomeClawTimerChipTimerOutline, 1.0, drop: 0.9))
    }
    /// B1b: the width "Finished" is fitted to (v582's ≈ 47 pt, PH-0a).
    static func finishedMaxWidth(_ t: Tokens) -> CGFloat { CGFloat(t.number("home.clawTimerChip.finishedMaxWidth", 47)) }

    var body: some View {
        if !finished, let live {
            LiveCountdown(ends: live.ends, now: live.now) { s in chip(s) }
        } else {
            chip(seconds)
        }
    }

    private func chip(_ seconds: Double) -> some View {
        let text = finished ? EventWord.finished : Countdown.text(seconds)
        let st = Self.textStyle(t)
        let face: [Color] = [Color(hex: Skin.homeClawBarCountdownChipChipFace0), t.color("clawChip.face", Skin.homeClawBarClawChipFace), Color(hex: Skin.homeClawBarCountdownChipChipFace2)]
        return ZStack(alignment: .topLeading) {
            Rasterized("clawChip|false") { _ in
                ZStack {
                    RoundedRectangle(cornerRadius: 5.5).fill(Color(hex: Skin.homeClawBarCountdownChipChipFill))
                    RoundedRectangle(cornerRadius: 4.8)
                        .fill(LinearGradient(colors: face, startPoint: .top, endPoint: .bottom))
                        .padding(0.9)
                }
            }
            .placed(CGRect(x: 17.4, y: 4.4, width: 61.1, height: 17.8))
            ArtImage(art: .hudTimerIconSmall).placed(CGRect(x: 0, y: 0, width: 24, height: 25.7))
            // B1b: "Finished" fitted inside the chip's face like v582's (≈ 47 pt wide on the 1178 px PH-0a shot)
            GlyphRunText(text: text, style: st, maxWidth: finished ? Self.finishedMaxWidth(t) : 54)
                .at(48.3, st.capCentre(baseline: 18.5))
        }
        .frame(width: 80, height: 25.7, alignment: .topLeading)
        .accessibilityElement()
        .accessibilityIdentifier(id)
        .accessibilityValue(Text(verbatim: finished ? "finished" : text))
    }
}

/// FIX-2 lane B (B1b-r3): the ended-event word. v582 shows "Finished" on an ended event's badge, chip and page; the lives pill's
/// "Finished" (a life arrived) is another key, so a language can say "ended" here and "ready" / "full" there
/// (strings.tsv `event.finished`, English in keys.tsv; ja 終了, ko 종료, zh-Hans 已结束, es Terminó, pt-BR Acabou …).
enum EventWord {
    static var finished: String { String(localized: "event.finished", defaultValue: "Finished") }
}
