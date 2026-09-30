import SwiftUI
import PathCore

// Kit component `balloon-rise` (kit/social-events/balloon-rise): Up & Away's strip under the win panel while it runs, as a slot
// (`PanelStrips`, order 20: B1, it replaces the Hot Streak strip; VERIFIED v582, balloon.md §5). The win panel named
// BalloonStrip until the kit decoupling step. GameComponents.swift lists it. Its page, (i) and fall page are the events
// engine's (SocialPopups / SocialEntry); its home bar is placed by the event badges (EventBadges.swift).

@MainActor enum BalloonRiseRegistration {
    static func register() {
        PanelStrips.register(order: 20) { c in
            guard c.place == .win, let balloon = BalloonStripSource.data(c.app, outcomes: c.outcomes) else { return nil }
            return AnyView(BalloonStrip(data: balloon, shownAt: c.shownAt))
        }
    }
}
