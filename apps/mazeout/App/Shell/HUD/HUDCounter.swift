import SwiftUI
import PathCore

// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §8c, docs/SKIN.md §4). The HUD widgets a module declares besides the
// timer and the hearts (`PuzzleCapabilities.hud`), as counters in data slots of the HUD panel:
//   moves     moves left (`MetaEvent.movesChanged`)                           "12"
//   progress  Σ current / Σ target over the goals (`MetaEvent.goalProgress`)  "3/5"
//   goals     the first goal not reached yet (else the last)                  "12/20"
//   score     the goal whose id is "score": its current value                 "1250"
// A counter reuses the timer pill: the same recessed well (TimerWell) and the same text style (ui.json
// `text.hud.timerPill.timer`, skin colours). Its place is the slot of the widget's position in `capabilities.hud` (ui.json
// `frames.hud.slot<N>Pill` / `slot<N>Icon`; slot 1 = the timer's place, slot 2 = the hearts' place in the reference HUD, which
// keeps drawing its own timer and hearts at their measured frames). The icon is the OPTIONAL art slot `hud.<widget>.icon`:
// a skin maps it in skin/art.json when it has the art; without one the pill is centred in its slot (no stand-in art).
// The leaf reads the counter itself, so a counter write re-renders only that leaf (like HUDTimerLeaf).

enum HUDCounter {
    /// Slots the panel has (ui.json `frames.hud.slot<N>*`); a module declaring more counters shows the first ones.
    static let slots = 2
    /// The goal id the score widget reads.
    static let scoreGoal = "score"

    /// The widgets the timer and hearts views do not draw.
    static func isCounter(_ w: HUDWidget) -> Bool { w != .timer && w != .hearts }

    /// A counter and its 1-based slot.
    struct Placement: Equatable, Identifiable {
        let widget: HUDWidget
        let slot: Int
        var id: Int { slot }
    }

    /// The counters of a widget list with their slot (the widget's position in the list), within the panel's slots.
    static func placed(_ widgets: [HUDWidget]) -> [Placement] {
        var out: [Placement] = []
        for (i, w) in widgets.enumerated() where isCounter(w) && i < slots { out.append(Placement(widget: w, slot: i + 1)) }
        return out
    }

    /// The counter's text; nil = nothing to show yet (no event so far).
    static func text(_ w: HUDWidget, moves: Int?, goals: [GoalState]) -> String? {
        switch w {
        case .moves:
            return moves.map { "\(max(0, $0))" }
        case .progress:
            guard !goals.isEmpty else { return nil }
            let current = goals.reduce(0) { $0 + min(max(0, $1.current), max(0, $1.target)) }
            let target = goals.reduce(0) { $0 + max(0, $1.target) }
            return "\(current)/\(target)"
        case .goals:
            guard let g = goals.first(where: { $0.current < $0.target }) ?? goals.last else { return nil }
            return "\(max(0, g.current))/\(max(0, g.target))"
        case .score:
            return goals.first(where: { $0.id == scoreGoal }).map { "\($0.current)" }
        case .timer, .hearts:
            return nil
        }
    }

    /// The widget's optional icon (`hud.<widget>.icon`); nil when the skin maps no art to it.
    static func icon(_ w: HUDWidget) -> UIArt? { UIArt(rawValue: "hud." + w.rawValue + ".icon") }

    /// The compiled defaults of the slots (reference pt): slot 1 = the timer's stopwatch + pill, slot 2 = the hearts' place.
    static func pillDefault(_ slot: Int) -> CGRect {
        slot <= 1 ? CGRect(x: 112.4, y: 81.7, width: 73.4, height: 26.4) : CGRect(x: 221.2, y: 81.7, width: 73.4, height: 26.4)
    }

    static func iconDefault(_ slot: Int) -> CGRect {
        slot <= 1 ? CGRect(x: 92.7, y: 77.7, width: 29.0, height: 33.0) : CGRect(x: 201.5, y: 77.7, width: 29.0, height: 33.0)
    }

    /// The pill's frame: its slot frame, centred on the slot (icon + pill) when the widget has no icon art.
    static func pillFrame(pill: CGRect, icon: CGRect, hasIcon: Bool) -> CGRect {
        hasIcon ? pill : pill.offsetBy(dx: icon.union(pill).midX - pill.midX, dy: 0)
    }
}

/// One counter widget (see the file header). `scale` nil = the empty pill of the intro (the timer's `bigTimerKf` pop).
struct HUDCounterLeaf: View {
    let model: HUDModel
    let widget: HUDWidget
    let slot: Int
    let scale: Double?
    let t: Tokens
    let m: ShellMetrics

    var body: some View {
        let text = HUDCounter.text(widget, moves: model.movesLeft, goals: model.goals)
        let art = HUDCounter.icon(widget)
        let icon = t.rect("hud.slot\(slot)Icon", HUDCounter.iconDefault(slot), .top, m)
        let pill = HUDCounter.pillFrame(pill: t.rect("hud.slot\(slot)Pill", HUDCounter.pillDefault(slot), .top, m), icon: icon,
                                        hasIcon: art != nil)
        let style = t.text("hud.timerPill.timer", .s2(23.3, 0.25, [Skin.hudTimerPillHudTimerPillTimer0, Skin.hudTimerPillHudTimerPillTimer1, Skin.hudTimerPillHudTimerPillTimer2], outline: Skin.hudTimerPillHudTimerPillTimerOutline, 0.67, drop: 1.13))
            .sized(23.3 * m.s)
        let baseline = pill.minY + CGFloat(t.number("hud.counterBaseline", 22.4)) * m.s
        ZStack(alignment: .topLeading) {
            Rasterized("hudTimerPill", overflow: 1) { _ in TimerWell(radius: t.radius("hud.timerPill", 9.34) * m.s, t: t) }
                .placed(pill)
            if let scale, let text {
                GameText(verbatim: text, style: style, maxWidth: pill.width - 6)
                    .scaleEffect(CGFloat(scale), anchor: .center)
                    .at(pill.midX, style.capCentre(baseline: baseline))
            }
            if let art { InkImage(art: art, ink: icon) }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("hud.\(widget.rawValue)")
        .accessibilityValue(Text(verbatim: text ?? ""))
        .anchor(.custom("hud.\(widget.rawValue)"))
    }
}
