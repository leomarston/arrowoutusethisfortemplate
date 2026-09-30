import SwiftUI
import PathCore

// Kit component `events-engine` (kit/social-events/events-engine): the event popups in the popup host (SocialPopups: the
// Weekly Contest steps, the Claw (i), the Sky Jump and Rocket Race pages, the Streak Race board, the custom event ids), their
// `-pc.popup` ids and Loading warm-ups, and the social pages' link to the engine (`SocialEvents.engine`: the leaderboard and
// the social model reach SocialFlows through it). SocialPopups was named by PopupHost, the router and RootView until the kit
// decoupling step; GameComponents.swift lists it. The event pages the engine presents are still wired in its own hubs
// (SocialPopups, SocialEntry, EventBadges, EventsDirector: `kit.py rdeps <event>` prints the lines).

@MainActor enum EventsEngineRegistration {
    static func register() {
        SocialEvents.register(SocialFlowsEngine())
        PopupPanels.register(PopupPanelProvider("events-engine", handles: { SocialPopups.hasPanel($0) },
                                                isPage: { SocialPopups.isPage($0) }, pagesHandOver: true,
                                                make: { r, answer in AnyView(SocialPopups.make(r, answer: answer)) }))
        DebugPopups.register { p, app in await SocialPopups.debugPresent(p, app: app) }
        ShellPrewarmItems.register(order: 200) { app, _ in SocialPopups.prewarm(app) }
    }
}

/// The events engine as the social pages see it (social-ui's `SocialEventsEngine`): SocialFlows' upkeep and joins.
@MainActor final class SocialFlowsEngine: SocialEventsEngine {
    func installHooks(_ app: AppModel, model: SocialModel) { SocHooks.install(app, model: model) }
    func settleEndedWeeks(_ app: AppModel) { SocialFlows.settleEndedWeeks(app) }
    func refreshEvents(_ app: AppModel, home: Bool, then: (() -> Void)?) { SocialFlows.refreshEvents(app, home: home, then: then) }
    func joinWeeklyIfNeeded(_ app: AppModel) -> Bool { SocialFlows.joinWeeklyIfNeeded(app) }
}
