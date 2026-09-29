import SwiftUI

// SHELL S2 (SPEC-ui §2.3.1 `hud.stopwatch` + `hud.timerPill`, VERIFIED 003/036/061; SPEC-motion-audio §3.6 rows 8-9, §4). The
// stopwatch 92.7 · 77.7 · 29 · 33 (`iconStopwatch`) beside the recessed pill 112.4 · 81.7 · 73.4 · 26.4 (rr 9.3, well #6C94DC,
// a dark top inner shadow #618AD4, a light lower rim #D7E8FD) with "m:ss" 23.3 / +0.25 (face #F7F7F9 → #E2E3EA, outline #081E5E
// 0.67, drop 1.13). ALWAYS blue; no colour, pulse or scale near 0 (VERIFIED fail §2). The text is written only when the
// displayed second changes (GAME's HUDWriter), so this view re-renders ≤ 1 Hz in play. During the intro (K + 1.015 … 1.339) the
// pill is EMPTY, then the text pops `hudIntro.bigTimerKf`; after Add Time (+30 sec) it pops 1.3 → 1.0 (`hud.addTimePop`).
// The file is named after the SPEC-architecture tree; the view is `HUDTimerPill` (GlossyChrome reserves `TimerPill`).

struct HUDTimerPill: View, Equatable {
    let text: String
    /// nil = the empty pill of the intro; else the text's scale (1 at rest).
    let scale: Double?
    let t: Tokens
    let m: ShellMetrics

    static func == (a: HUDTimerPill, b: HUDTimerPill) -> Bool { a.text == b.text && a.scale == b.scale && a.m == b.m }

    @Environment(\.displayScale) private var displayScale

    /// "m:ss" → seconds (nil for anything else).
    static func seconds(_ text: String) -> Int? {
        let p = text.split(separator: ":")
        guard p.count == 2, let m = Int(p[0]), let s = Int(p[1]) else { return nil }
        return m * 60 + s
    }

    var body: some View {
        let pill = t.rect("hud.timerPill", CGRect(112.4, 81.7, 73.4, 26.4), .top, m)
        let watch = t.rect("hud.stopwatch", CGRect(92.7, 77.7, 29, 33), .top, m)
        let style = t.text("hud.timerPill.timer", .s2(23.3, 0.25, [0xF7F7F9, 0xEDEDF2, 0xE2E3EA], outline: 0x04292C, 0.67, drop: 1.13))
            .sized(23.3 * m.s)
        let p = t.textPoint("hud.timerPill.timer", baseline: 104.1, centreX: 152.3)
        let at = m.point(CGPoint(x: p.x, y: p.baseline), .top)
        // FIX-2 A (V3-04): the next two seconds' rasters are made off the main thread now, so the next ticks composite
        let _ = Self.seconds(text).map { now in
            GameText.prefetch(verbatim: [now - 1, now - 2].filter { $0 >= 0 }.map(HUDWriter.text), style: style,
                              maxWidth: pill.width - 6, scale: displayScale)
        }
        ZStack(alignment: .topLeading) {
            Rasterized("hudTimerPill", overflow: 1) { _ in TimerWell(radius: t.radius("hud.timerPill", 9.34) * m.s, t: t) }
                .placed(pill)
            if let scale, !text.isEmpty {
                GameText(verbatim: text, style: style, maxWidth: pill.width - 6)
                    .scaleEffect(CGFloat(scale), anchor: .center)
                    .at(at.x, style.capCentre(baseline: at.y))
            }
            InkImage(art: .iconStopwatch, ink: watch)
        }
    }
}

/// The recessed timer well (grad.hud.timerPill, VERIFIED 003).
private struct TimerWell: View {
    let radius: CGFloat
    let t: Tokens

    var body: some View {
        RoundedRectangle(cornerRadius: radius, style: .continuous)
            .fill(LinearGradient(stops: t.stops("hud.timerPillWell", [(0, 0x57ADA5), (0.05, 0x48978D), (0.2, 0x50A197),
                                                                       (0.9, 0x50A197), (0.95, 0x4A988E), (0.965, 0x59A49B),
                                                                       (0.985, 0xBADAD3), (1.0, 0xDAECE7)]),
                                 startPoint: .top, endPoint: .bottom))
    }
}
