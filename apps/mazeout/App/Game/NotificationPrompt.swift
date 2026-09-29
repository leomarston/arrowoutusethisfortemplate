import Foundation
import UserNotifications
import PathCore

// GAME G2 (SPEC-architecture §6.10, §8.5 step 4; SPEC.md §5 item 5 "ask at the original's moment and USE them offline";
// SPEC-gameplay §10.1, §12.5; game.json `notifications.*`).
//  - The prompt: the iOS notification permission alert over the Loading screen on the FIRST launch (VERIFIED V2 3.0–6.0 s,
//    phone F00: declined → the game continues). Once per install (`flags.notificationPromptShown`, saved before asking). Either
//    answer continues; Loading stays up until it is answered (the boot awaits it). Suppressed under `-pc.uitest` / `-pc.capture`
//    unless `-pc.notif 1` (§9.1), and under `-pc.autoplay` unless `-pc.notif 1` (the bot cannot answer a system alert).
//  - The use (`LocalNotifications`): scheduled only while the game is in the background, only when Settings' Notifications is
//    ON and iOS authorised them; recomputed at every background, cancelled at every foreground (GP §12.5):
//      livesFull     at the moment lives regenerate to 5 (C3 `Economy.livesFullAt`), when lives are below 5
//      weeklyEnding  2 h (`notifications.weeklyEndingHours`) before the Weekly Contest's end (Monday 07:00 UTC), when the
//                    player joined this week's contest (L50+)
//    Title = Brand.name; bodies "Your lives are full! Time to play!" / "The Weekly Contest ends in 2 hours!". No badge, the
//    default sound, no server: `UNTimeIntervalNotificationTrigger` on the device.
//    B1 (events.md §6.4; ruling 38 "event notifications on (≤ 1/day, daytime)"): the weekly rotation's event notifications
//    from C3's pure planner `EventNotifications.plan` — eventStart (next week's new featured events) and eventEnding (the
//    ladder event with progress), only inside 10:00-21:00 LOCAL time, at most one event notification in any 24 h (the
//    Weekly Cup reminder and the last delivered one included; priority weeklyEnding > eventEnding > eventStart). What was
//    scheduled is recorded in the save; the next foreground learns which of them fired.
// Log: `[PC][notif] …`.

@MainActor enum NotificationPrompt {
    /// The app process hosts the unit tests (ArrowOutTests' TEST_HOST): no system prompt (it would consume the one-shot
    /// permission of the simulator's install). UI tests run the app in its own process, where XCTest is not loaded.
    static let isUnitTestHost: Bool = {
        let env = ProcessInfo.processInfo.environment
        return NSClassFromString("XCTestCase") != nil || env["XCTestConfigurationFilePath"] != nil || env["XCTestBundlePath"] != nil
    }()

    /// Boot step 4: asks once, on the first launch. Returns when the alert was answered (at once when nothing is asked).
    static func askIfNeeded(_ app: AppModel) async {
        let s = app.store.state
        guard !s.flags.notificationPromptShown else { return }
        guard app.tuning.game.notificationsAskOnFirstLaunch else {
            Log.mark("notif", "prompt off (game.json notifications.askOnFirstLaunch false)")
            return
        }
        let a = app.args
        guard !Self.isUnitTestHost else { Log.mark("notif", "prompt suppressed: the app is hosting unit tests"); return }
        guard a.notificationPromptAllowed, !a.autoplay || a.notif else {
            Log.mark("notif", "prompt suppressed (uitest/capture/autoplay without -pc.notif 1); still due on a real first launch")
            return
        }
        app.store.mutateAndSave { $0.flags.notificationPromptShown = true }
        Log.mark("notif", "prompt shown over Loading (first launch)")
        let center = UNUserNotificationCenter.current()
        do {
            let granted = try await center.requestAuthorization(options: [.alert, .sound])
            Log.mark("notif", "prompt answered: \(granted ? "allowed" : "not allowed")")
        } catch {
            Log.error("notif", "requestAuthorization: \(error)")
        }
    }
}

@MainActor enum LocalNotifications {
    static let livesFullID = "livesFull"
    static let weeklyEndingID = "weeklyEnding"

    /// What would be scheduled now (pure: tests call it): id → seconds from now.
    struct Plan: Equatable {
        var livesFullIn: TimeInterval?
        var weeklyEndingIn: TimeInterval?
        /// B1: the rotation's event notifications (eventStart / eventEnding), in firing order.
        var events: [EventNotifications.Item] = []
    }

    static func plan(_ s: PlayerState, now: Date, rules: EconomyRules, tuning: GameTuning, zone: TimeZone = .current) -> Plan {
        var p = Plan()
        guard s.settings.notifications else { return p }
        if tuning.file.bool("notifications.livesFull", true), let at = Economy.livesFullAt(s, now: now, rules: rules) {
            // `at` is on the rewind-safe economy clock (max(wall, high-water)); the wall clock reaches it at the same moment
            let dt = at.timeIntervalSince(now)
            if dt > 1 { p.livesFullIn = dt }
        }
        // B1: the Weekly Cup reminder and the event notifications share one planner (its cap counts them together)
        let hours = tuning.file.double("notifications.weeklyEndingHours", 2)
        let items = EventNotifications.plan(s, now: now, rules: rules, zone: zone, weeklyEndingHours: hours)
        if let w = items.first(where: { $0.kind == .weeklyEnding }) {
            let dt = Double(w.at) - now.timeIntervalSince1970
            if dt > 1 { p.weeklyEndingIn = dt }
        }
        if tuning.file.bool("notifications.events", true) { p.events = items.filter { $0.kind != .weeklyEnding } }
        return p
    }

    /// The event notification's body (our event names, events.md §6.4 / T1's strings).
    static func body(_ it: EventNotifications.Item) -> String {
        let names = it.events.map(EventNames.name)
        switch it.kind {
        case .eventStart:
            if it.double {
                return String(localized: "Double Event Week! \(String(localized: EventNames.name(.rocketRace))) and \(String(localized: EventNames.name(.skyJump))) are both on!")
            }
            return String(localized: "\(String(localized: names.first ?? "Up & Away")) has started! Beat levels to win amazing rewards!")
        case .eventEnding:
            let n = String(localized: names.first ?? "Up & Away")
            return it.threeHours ? String(localized: "\(n) ends in 3 hours!") : String(localized: "\(n) ends soon!")
        case .weeklyEnding:
            return String(localized: "The Weekly Cup ends in 2 hours!")
        }
    }

    /// Backgrounded: schedules this plan (when Settings' Notifications is ON and iOS allows them).
    static func reschedule(_ app: AppModel) {
        let s = app.store.state
        let p = plan(s, now: app.clock.wallClock(), rules: app.economy, tuning: app.tuning.game)
        let center = UNUserNotificationCenter.current()
        center.removeAllPendingNotificationRequests()
        guard s.settings.notifications else { Log.mark("notif", "background: Notifications OFF in Settings, nothing scheduled"); return }
        guard p.livesFullIn != nil || p.weeklyEndingIn != nil || !p.events.isEmpty else {
            Log.mark("notif", "background: nothing to schedule"); return
        }
        let title = Brand.name
        let lives = String(localized: "Your lives are full! Time to play!")
        let weekly = String(localized: "The Weekly Cup ends in 2 hours!")
        Task { @MainActor in
            let status = await center.notificationSettings().authorizationStatus
            guard status == .authorized || status == .provisional || status == .ephemeral else {
                Log.mark("notif", "background: iOS has not authorised notifications (\(status.rawValue)), nothing scheduled")
                return
            }
            var lines: [String] = []
            if let dt = p.livesFullIn {
                await add(center, id: livesFullID, title: title, body: lives, after: dt)
                lines.append(String(format: "livesFull in %.0f s", dt))
            }
            if let dt = p.weeklyEndingIn {
                await add(center, id: weeklyEndingID, title: title, body: weekly, after: dt)
                lines.append(String(format: "weeklyEnding in %.0f s", dt))
            }
            var recorded: [EventNotifications.Item] = []
            if let dt = p.weeklyEndingIn {
                recorded.append(.init(kind: .weeklyEnding, at: Int64(app.clock.wallClock().timeIntervalSince1970 + dt), events: [.weeklyContest]))
            }
            for it in p.events {
                let dt = Double(it.at) - app.clock.wallClock().timeIntervalSince1970
                guard dt > 1 else { continue }
                await add(center, id: it.kind.rawValue, title: title, body: body(it), after: dt)
                lines.append(String(format: "%@ %@ in %.0f s", it.kind.rawValue, it.events.map(\.rawValue).joined(separator: "+"), dt))
                recorded.append(it)
            }
            app.store.mutateAndSave { EventNotifications.record(&$0, recorded) }
            Log.mark("notif", "background: scheduled " + lines.joined(separator: ", "))
        }
    }

    private static func add(_ center: UNUserNotificationCenter, id: String, title: String, body: String, after dt: TimeInterval) async {
        let c = UNMutableNotificationContent()
        c.title = title
        c.body = body
        c.sound = .default
        let req = UNNotificationRequest(identifier: id, content: c,
                                        trigger: UNTimeIntervalNotificationTrigger(timeInterval: max(1, dt), repeats: false))
        do { try await center.add(req) } catch { Log.error("notif", "add \(id): \(error)") }
    }

    /// Foreground: the game is open, nothing is pending. B1: the event notifications that fired while away count in the cap.
    static func cancelAll(_ app: AppModel? = nil) {
        let center = UNUserNotificationCenter.current()
        center.removeAllPendingNotificationRequests()
        center.removeAllDeliveredNotifications()
        if let app, !app.store.state.events.notify.pending.isEmpty {
            let now = app.clock.wallClock()
            app.store.mutateAndSave { EventNotifications.foreground(&$0, now: now) }
        }
    }
}
