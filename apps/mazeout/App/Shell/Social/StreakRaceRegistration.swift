import SwiftUI
import PathCore

// Kit component `streak-race` (kit/social-events/streak-race): what the Streak Race draws inside other components' panels, as
// slots — the strip under the win panel and under Level Failed (`PanelStrips`, order 30: after the Rocket Race bar and Up &
// Away's strip), the multiplier chips on Continue? (`ContinueChips`). The fail flow and the win panel named StreakStrip /
// StreakChipRow until the kit decoupling step. GameComponents.swift lists it. Its page and popups are the events engine's
// (SocialPopups / SocialEntry).

@MainActor enum StreakRaceRegistration {
    static func register() {
        PanelStrips.register(order: 30) { c in
            let lost = c.place == .levelFailed
            guard let strip = StreakStripSource.data(c.app, level: c.level, outcomes: c.outcomes, lost: lost) else { return nil }
            return AnyView(StreakStrip(data: strip, shownAt: c.shownAt))
        }
        ContinueChips.register { steps, lit, frame, t in
            AnyView(StreakChipRow(steps: steps, lit: Double(lit), ring: 1, frame: frame, t: t, onCream: true))
        }
    }
}
