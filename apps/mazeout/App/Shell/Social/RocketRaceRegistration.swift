import SwiftUI
import PathCore

// Kit component `rocket-race` (kit/social-events/rocket-race): the race bar under the win panel while a race runs, as a slot
// (`PanelStrips`, order 10: it wins over Up & Away's and the Streak Race's strips). The win panel named RocketRaceStrip until
// the kit decoupling step. GameComponents.swift lists it. Its pages are the events engine's (SocialPopups / SocialEntry); the
// bar's data is set by the engine (`RocketRaceStripSource.provider`, SocHooks / EventsDirector).

@MainActor enum RocketRaceRegistration {
    static func register() {
        PanelStrips.register(order: 10) { c in
            guard c.place == .win, let race = RocketRaceStripSource.provider?(c.app) else { return nil }
            return AnyView(RocketRaceStrip(data: race, shownAt: c.shownAt))
        }
    }
}
