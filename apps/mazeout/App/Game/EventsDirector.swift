import SwiftUI
import UIKit
import PathCore

// GAME G2 (SPEC-architecture §8.4 EventsDirector, §6.4 "home auto-sequences"; SPEC-gameplay §9.3, §11; SPEC-social §4.8;
// SPEC-motion-audio §8.3–§8.4; CONSISTENCY W-15 (the SOC/GP/MA/UI order wins), W-16…W-24).
// C3's hooks themselves run where the attempt is banked (G1: WinDirector `Events.onWin`, FailFlowDirector `Events.onLoss`, one
// mutation with `Economy.finishAttempt`); this file presents what they produced and keeps the world moving:
//   per Play (`EventsDirector`)
//     - the `[PC][event] <id> <outcome>` marks of every banked attempt (§9.3);
//     - after the win panel's Continue: (1) the Sky Jump progress page while a run is active (SOC2's `.skyJump(.progress)`),
//       then the router's next screen (home, or the FTUE chain's next level);
//     - the rating prompt becomes due after the L34 win (`RatingDirector`, shown on that home after the queue);
//   per home arrival (`HomeQueue`, app-lifetime; the router's screen is observed, no SHELL edit)
//     - `Events.refresh(home: true)`: rolls the calendar, joins the day's Streak Race and the week's Claw, settles ended races
//       into claims (saved);
//     - waits for S3's home-return sequence (segments A Claw token → B Streak strip → C coins, `PayoutSequence`);
//     - then the queue, one popup at a time and only while home stays on screen: (2) claims in the order they were earned
//       ("Congratulations! … Tap to Claim", S2's claim popup → C3 `Events.claim` → coins fly with segment C, MA §8.4; ∞ lives
//       show on the pill), (3) the Rocket Race result page after a lost race, (4) offers (Rocket Race after L55, Sky Jump after
//       L40, once per event day), (5) the day's Streak Race list (first home of the event day after L30), (6) the Claw
//       Challenge's first-open page after the L32 win — (3)–(6) are SOC2's screens and are skipped (logged) until SOC2's
//       panels / pages exist (`PopupContent.hasPanel`, `G2Hooks.eventPagesInstalled`); then (7) the rating prompt (a game
//       that adds an attribution SDK puts its one-time tracking prompt after it: docs/recipes/ad-attribution.md);
//     - a foreground on home refreshes the same way (§8.6).
//     - B1 (PUBLISH item 14; events.md §6.2) while the weekly rotation runs: after the claims and the Rocket result, the
//       WEEK-START pages — once per featured event per week, the event's own page (the ladder: Treasure Climb / Up & Away,
//       which takes the screen, so it ends the visit's queue) or offer (the race: Rocket Rally / Cloud Hop) with the "New
//       Event!" ribbon (EventAnnounce); then the daily offers and the Hot Streak list. At most `rotation.announceCap` (2)
//       UNREQUESTED pages per home visit (week-start pages + daily offers + the list); the rest wait for the next visit.
//       The ladder's week-start page is also its first-open intro (the v552 "Claw first-open page after the L32 win").
//       With the rotation off (the v552 plan, and every -pc.uitest / -pc.capture run without a rotation scenario) the queue
//       is exactly the v552 one.
//     - B1b (v582 PH-0a: the ended events read "Finished" until their result is opened, EventFinished.swift): while the ladder
//       slot holds last week's ended event, this week's ladder week-start page waits (the player opens the Finished bar first;
//       its page's X brings home back, and that arrival shows the new week's page). Opening the Leaderboard tab is opening the
//       ended Weekly Cup's result (its red "!" goes).
//   `EventsGlue` feeds S2's win-panel Rocket Race bar and S3's home Rocket badge rank from C3's run + SOC1's rivals, and gives
//   SOC2's offer panels their "Start" (`joinRocketRace` / `joinSkyJump`: C3's join, saved, the join claim shown) (P1 glue).

/// SOC2 flips these on when its screens exist (the queue then routes to them instead of skipping).
@MainActor enum G2Hooks {
    /// SOC2's full-screen event pages (`SocialEntry.makeEventScreen`) are installed: the Claw first-open page is shown.
    static var eventPagesInstalled = false
    /// SOC2 presents some claims itself (e.g. the Weekly / Streak Race result screens): return true to take the claim.
    static var claimPresenter: ((AppModel, EventClaim) async -> Bool)?
}

@MainActor final class EventsDirector: GameDirector {
    unowned let game: GameController

    init(_ game: GameController) { self.game = game }

    private var services: GameServices { game.services }

    func handle(_ outputs: [SessionOutput], game: GameController) {
        for out in outputs {
            guard case .meta(let e) = out else { continue }
            if case .won = e {
                // G1 banked the win in the same batch (WinDirector ran before this director): log its outcomes
                let outcomes = game.win.outcomes
                if outcomes.isEmpty { Log.mark("event", "\(game.levelName) won: no event counted (below the unlocks)") }
                for o in outcomes { Log.mark("event", Self.describe(o)) }
            }
            if case .lost(let r) = e {
                let st = services.store.state
                let m = Events.status(st, now: services.clock.wallClock(), rules: services.economy).multiplier
                Log.mark("event", "\(game.levelName) lost (\(r.rawValue)): multiplier x\(m) until the loss is banked (→ x1), "
                         + "Sky Jump \(st.events.sky.active == nil ? "no run" : "run active until the loss is banked")")
            }
        }
    }

    func afterWin(_ summary: WinSummary, game: GameController) async {
        let s = services
        let after = s.tuning.game.ratingAfterLevel
        if summary.levels.contains(after) { HomeQueue.shared.ratingDue = true }
        guard s.store.state.homeSeen else { return }
        let status = Events.status(s.store.state, now: s.clock.wallClock(), rules: s.economy)
        if let sky = status.skyJump, sky.progress != nil {
            let req = PopupRequest.skyJump(.progress)
            if PopupContent.hasPanel(req) {
                Log.mark("event", "skyJump progress page \(sky.progress ?? 0)/\(sky.levels) before home")
                _ = await s.popups.present(Popup<PopupResult>.skyJump(.progress))
            } else {
                Log.mark("event", "skyJump progress \(sky.progress ?? 0)/\(sky.levels): SOC2's progress page not installed, skipped")
            }
        }
    }

    // MARK: log helpers

    /// The log line of an outcome (moved to core's EventOutcomeLog in the kit decoupling step: the win flow logs it too).
    static func describe(_ o: EventOutcome) -> String { EventOutcomeLog.describe(o) }
}

// MARK: - the Weekly Contest tutorial on the first Play at L50

/// SPEC-gameplay §10.7, SPEC-social §4.3 (VERIFIED phone shots/130-133): the FIRST Play tap on the LEVEL 50 home is intercepted
/// by the forced Weekly Contest step — SOC2's `SocialFlows.weeklyTutorial` (dim + "Tap to compete in Weekly Contest!" with only
/// the trophy tab live → the Weekly tab → the info overlay → the join). Once per install: the info overlay sets
/// `flags.weeklyIntroSeen` (as does opening the Weekly (i) first); after that Play starts the level. A save that passed L50
/// without it gets it at its next Play. Off in UI tests / captures unless `-pc.tutorials force`, like every tutorial.
@MainActor enum WeeklyTutorialGate {
    private static var running = false

    /// Home's Play: true = the tutorial took this tap (the level does not start).
    static func interceptsPlay(_ app: AppModel) -> Bool {
        guard !running, isDue(app) else { return false }
        running = true
        PayoutSequence.cancel()                                                     // as when home's tab changes
        Log.mark("event", "weeklyContest tutorial: the first Play at L\(app.store.state.level) is intercepted")
        Task { @MainActor in
            await SocialFlows.weeklyTutorial(app)
            running = false
            Log.mark("event", "weeklyContest tutorial done (intro seen \(app.store.state.flags.weeklyIntroSeen))")
        }
        return true
    }

    /// L50+ (the Weekly Contest's unlock), not seen yet, SOC2's panel installed, tutorials allowed.
    static func isDue(_ app: AppModel) -> Bool {
        let s = app.store.state
        guard TutorialDirector.allowed(app.args), !s.flags.weeklyIntroSeen,
              EventSchedule.isUnlocked(.weeklyContest, level: s.level, rules: ShellEconomy.rules(app).events) else { return false }
        return PopupContent.hasPanel(.weeklyContestTutorial)
    }
}

// MARK: - the home queue (app lifetime)

@MainActor final class HomeQueue {
    static let shared = HomeQueue()

    private weak var app: AppModel?
    private var task: Task<Void, Never>?
    private var onHomeTab = false
    /// The queue is running (the autoplayer and tests read it).
    private(set) var busy = false
    /// Set by the L34 win's Continue; the rating prompt closes that home's queue.
    var ratingDue = false
    /// Every step the queue took (tests; the last 200).
    private(set) var trail: [String] = []

    func start(_ app: AppModel) {
        guard self.app == nil else { return }
        self.app = app
        observe()
        EventFinishProbe.run(app)                                           // B1b: measurement only (-pc.finishedProbe)
        EventFinish.preloadLadderArt()                                      // B1b FEEL: the ladder slot's tokens decoded at launch
    }

    private func observe() {
        guard let app else { return }
        let screen = withObservationTracking { app.router.screen } onChange: { [weak self] in
            Task { @MainActor in self?.observe() }
        }
        changed(screen)
    }

    private func changed(_ screen: Screen) {
        var entry: HomeEntry?
        if case .home(let e, .home) = screen { entry = e }
        // B1b: the Leaderboard tab shows the Weekly Cup: its ended week's hold ("!") goes
        if case .home(_, .leaderboard) = screen, let app { EventFinish.open(app, .weeklyContest) }
        if let entry, !onHomeTab { arrived(entry) }
        if entry == nil, onHomeTab { task?.cancel(); task = nil }
        onHomeTab = entry != nil
    }

    private func arrived(_ entry: HomeEntry) {
        task?.cancel()
        // FIX-2 A (A3-o0 / A4-o1): the queue's first step (a store refresh of the events) runs two frames AFTER the arrival, not
        // in the arrival's own frame (at the Loading → home cut it added ~10-20 ms to that frame)
        task = Task { @MainActor [weak self] in
            await FrameWaiter.frames(2)
            guard !Task.isCancelled else { return }
            await self?.run(entry)
        }
    }

    /// §8.6 foreground: a refresh on the wall clock (on home: the queue again).
    func foreground() {
        guard let app, app.router.screen.isHome, !busy else { return }
        if case .home(_, .home) = app.router.screen { arrived(.normal) } else { refresh(app) }
    }

    private func note(_ s: String) {
        trail.append(s)
        if trail.count > 200 { trail.removeFirst() }
        Log.mark("homequeue", s)
    }

    /// A "not installed yet" line once per run (not at every home arrival).
    private var notedOnce: Set<String> = []
    private func noteOnce(_ s: String) {
        guard notedOnce.insert(s).inserted else { return }
        note(s + " (logged once per run)")
    }

    private func stillHome(_ app: AppModel) -> Bool {
        guard !Task.isCancelled, case .home(_, .home) = app.router.screen else { return false }
        return true
    }

    @discardableResult
    private func refresh(_ app: AppModel) -> [EventOutcome] {
        let now = app.clock.wallClock()
        let rivals = app.rivals
        let rules = app.economy
        let before = app.store.state.events.claims.count
        let out = app.store.mutateAndSave { s -> [EventOutcome] in
            let me = s.social.standing(installSeed: s.installSeed, level: s.level)
            return Events.refresh(&s, now: now, rivals: rivals, me: me, rules: rules, home: true)
        }
        let claims = app.store.state.events.claims.count
        if !out.isEmpty || claims != before {
            note("refresh: \(out.map(EventsDirector.describe).joined(separator: "; ")) claims \(before) → \(claims)")
        }
        return out
    }

    private func run(_ entry: HomeEntry) async {
        guard let app else { return }
        busy = true
        let t0 = ProcessInfo.processInfo.systemUptime
        defer {
            busy = false
            note(String(format: "done after %.2f s%@", ProcessInfo.processInfo.systemUptime - t0, Task.isCancelled ? " (home left)" : ""))
        }
        note("arrival (\(HomeView.name(entry))): claims \(app.store.state.events.claims.count), rating due \(ratingDue)")
        refresh(app)
        await waitForPayout(app)
        guard stillHome(app) else { return }

        // (2) claims, in the order they were earned
        guard await presentClaims(app) else { return }

        // (3)–(6) SOC2's screens
        let now = app.clock.wallClock()
        let status = Events.status(app.store.state, now: now, rules: app.economy)
        let t = EconomyClock.peekSocial(app.store.state, wall: now)
        let day = EventSchedule.day(t, app.economy.events.calendar)
        // The daily offers, the Streak board and the Claw first-open page are unasked-for intros: off in UI tests / captures
        // unless -pc.tutorials force, like every tutorial (SPEC.md ruling 33). Results and claims always run.
        let dailyPages = TutorialDirector.allowed(app.args)
        // B1: the lost race's result is the player's own news: shown even when Rocket Rally is not featured after the roll
        if app.store.state.events.rocket.lastResult == .lost, EventSchedule.isUnlocked(.rocketRace, level: app.store.state.level,
                                                                                          rules: app.economy.events) {
            await soc2(app, .rocketRace(.result), once: "rocketResult-\(app.store.state.events.rocket.raceCounter)")
        }
        if status.rotating {
            guard await rotationPages(app, status: status, day: day, dailyPages: dailyPages) else { return }
            guard stillHome(app) else { return }
            await closeVisit(app)
            return
        }
        if dailyPages, let rocket = status.rocketRace, rocket.joinable { await soc2(app, .rocketRace(.offer), once: "rocketOffer-\(day)") }
        if dailyPages, let sky = status.skyJump, sky.joinable { await soc2(app, .skyJump(.offer), once: "skyOffer-\(day)") }
        if dailyPages, status.streakRace != nil { await soc2(app, .streakRaceBoard, once: "streakList-\(day)") }
        if dailyPages, status.claw != nil, !app.store.state.flags.seen.contains("clawIntro") {   // a first-open intro: ruling 33
            if !G2Hooks.eventPagesInstalled {
                noteOnce("clawChallenge first-open page: SOC2's page not installed, skipped (stays due)")
            } else if stillHome(app) {
                app.store.mutateAndSave { $0.flags.seen.insert("clawIntro") }
                note("clawChallenge first-open page")
                app.router.go(.event(.claw))
                return
            } else {
                note("clawChallenge first-open page: home was left before it, skipped (stays due)")
                return
            }
        }

        // (7) the rating prompt after the L34 win
        guard stillHome(app) else { return }
        await closeVisit(app)
    }

    /// The visit's last step: (7) the rating prompt after the L34 win.
    private func closeVisit(_ app: AppModel) async {
        if RatingDirector.requestIfDue(app, due: ratingDue) { ratingDue = false }
    }

    /// B1: the rotation's unrequested pages (week-start pages, daily offers, the Hot Streak list), at most `announceCap` per
    /// visit. false = the visit's queue ends here (a ladder page took the screen, or home was left).
    private func rotationPages(_ app: AppModel, status: Events.Status, day: Int, dailyPages: Bool) async -> Bool {
        guard dailyPages, let week = status.week?.week else { return true }
        var budget = max(0, app.economy.events.rotation.announceCap)
        let seen = { (k: String) in app.store.state.flags.seen.contains(k) }
        // (3a) the ladder's week-start page (its first-open intro too): the page takes the screen. B1b: not while the slot
        // still holds last week's ended event ("Finished" until the player opens it; stays due)
        if let held = status.finished.ladder, status.live.ladder != nil {
            note("ladder week-start page waits: \(held.rawValue) of last week still reads Finished")
        } else if let lad = status.live.ladder, budget > 0, !seen(EventAnnounce.weekStartKey(lad, week: week)) {
            guard G2Hooks.eventPagesInstalled else {
                noteOnce("\(lad.rawValue) week-start page: SOC2's pages not installed, skipped (stays due)")
                return true
            }
            guard await idle(app) else { return false }
            EventAnnounce.mark(app, EventAnnounce.weekStartKey(lad, week: week))
            if lad == .clawChallenge { app.store.mutateAndSave { _ = $0.flags.seen.insert("clawIntro") } }
            EventAnnounce.shared.current = .init(event: lad, double: false)
            note("week-start page \(lad.rawValue) (week \(week))")
            app.router.go(.event(lad == .clawChallenge ? .claw : .balloonRise))
            return false
        }
        // (3b) the race's week-start offers (both on a Double Event Week; the ribbon names it)
        let double = status.live.race.count > 1
        for e in status.live.race where budget > 0 && !seen(EventAnnounce.weekStartKey(e, week: week)) {
            // the offer while it can start (a Cloud Hop run that crossed the roll keeps its own page: no week-start offer)
            guard let run = e == .rocketRace ? status.rocketRace : status.skyJump, run.joinable else { continue }
            let req: PopupRequest = e == .rocketRace ? .rocketRace(.offer) : .skyJump(.offer)
            guard PopupContent.hasPanel(req), await idle(app) else { continue }
            EventAnnounce.mark(app, EventAnnounce.weekStartKey(e, week: week))
            // the week-start offer is also today's offer
            EventAnnounce.mark(app, (e == .rocketRace ? "rocketOffer-" : "skyOffer-") + "\(day)")
            budget -= 1
            EventAnnounce.shared.current = .init(event: e, double: double)
            note("week-start offer \(e.rawValue) (week \(week)\(double ? ", double" : ""))")
            _ = await app.popups.present(Popup<PopupResult>(req, style: SocialPopups.style(req), fallback: .close))
            EventAnnounce.shared.current = nil
            guard stillHome(app) else { return false }
        }
        // (4) the daily offers, (5) the day's Hot Streak list — inside the same budget
        if budget > 0, let rocket = status.rocketRace, rocket.joinable, !seen("rocketOffer-\(day)") {
            budget -= 1
            await soc2(app, .rocketRace(.offer), once: "rocketOffer-\(day)")
        }
        if budget > 0, let sky = status.skyJump, sky.joinable, !seen("skyOffer-\(day)") {
            budget -= 1
            await soc2(app, .skyJump(.offer), once: "skyOffer-\(day)")
        }
        if budget > 0, status.streakRace != nil, !seen("streakList-\(day)") {
            budget -= 1
            await soc2(app, .streakRaceBoard, once: "streakList-\(day)")
        }
        if budget == 0 { note("announce cap reached (\(app.economy.events.rotation.announceCap) pages this visit)") }
        return stillHome(app)
    }

    private var claimsRunning = false

    /// Every pending claim, one popup at a time, while home stays up. false = home was left.
    @discardableResult
    func presentClaims(_ app: AppModel) async -> Bool {
        guard !claimsRunning else { return stillHome(app) }                  // one presenter at a time (queue vs a join)
        claimsRunning = true
        defer { claimsRunning = false }
        var tried: Set<Int> = []
        while let claim = app.store.state.events.claims.sorted(by: { $0.id < $1.id }).first(where: { !tried.contains($0.id) }) {
            tried.insert(claim.id)
            guard await idle(app) else { return false }
            if let own = G2Hooks.claimPresenter, await own(app, claim) { note("claim \(claim.id) taken by SOC2"); continue }
            note("claim \(claim.id) \(claim.event.rawValue) \(claim.kind.rawValue): \(claim.grant)")
            let r = await app.popups.present(Popup<PopupResult>.claimReward(claim.grant))
            guard !Task.isCancelled else { return false }
            apply(claim, answer: r, app: app)
            if claim.grant.coins > 0 { await waitForPayout(app, expectStart: false) }
        }
        return stillHome(app)
    }

    private func apply(_ claim: EventClaim, answer: PopupResult, app: AppModel) {
        let now = app.clock.wallClock()
        let coinsBefore = app.store.state.coins
        let g = app.store.mutateAndSave { Events.claim(&$0, id: claim.id, now: now) }
        guard let g else { note("claim \(claim.id): already claimed"); return }
        note("claimed \(claim.id) (\(answer)): coins \(coinsBefore) → \(app.store.state.coins), boosters "
             + app.store.state.boosters.sorted { $0.key < $1.key }.map { "\($0.key)=\($0.value)" }.joined(separator: ",")
             + (g.unlimitedLives > 0 ? ", ∞ +\(Int(g.unlimitedLives)) s" : ""))
        guard g.coins > 0, stillHome(app) else { return }
        // MA §8.4: a claim's coins fly with segment C (C0 = the claim popup's close); the pill counts up as they land
        PayoutSequence.play(PayoutPlan(claw: nil, streak: nil, coins: g.coins), app: app, metrics: Self.metrics(app), status: nil)
    }

    /// A SOC2 popup once per key (skipped with a log while SOC2's panel does not exist).
    private func soc2(_ app: AppModel, _ req: PopupRequest, once key: String) async {
        guard !app.store.state.flags.seen.contains(key) else { return }
        guard PopupContent.hasPanel(req) else {
            noteOnce("\(req.id.rawValue): SOC2's panel not installed, skipped")
            return
        }
        guard await idle(app) else { return }
        // one key per kind ("rocketOffer-<day>" replaces yesterday's): the save does not grow with the days played
        let kind = key.split(separator: "-").first.map(String.init) ?? key
        app.store.mutateAndSave { st in
            st.flags.seen = st.flags.seen.filter { !$0.hasPrefix(kind + "-") }
            st.flags.seen.insert(key)
        }
        note("\(req.id.rawValue) (\(key))")
        _ = await app.popups.present(Popup<PopupResult>(req, style: .standard, fallback: .close))
    }

    /// Home is up and nothing covers it (a popup the player opened is answered first).
    private func idle(_ app: AppModel) async -> Bool {
        var n = 0
        while stillHome(app), app.popups.isPresenting || PayoutSequence.running, n < 36_000 {
            await FrameWaiter.frames(1)
            n += 1
        }
        return stillHome(app)
    }

    /// S3's home-return sequence (A/B/C) starts a few frames after the cut and ends with its "end" beat.
    private func waitForPayout(_ app: AppModel, expectStart: Bool = true) async {
        var n = 0
        if expectStart {
            while !PayoutSequence.running, n < 30, stillHome(app) { await FrameWaiter.frames(1); n += 1 }
        }
        n = 0
        while PayoutSequence.running, n < 1200, stillHome(app) { await FrameWaiter.frames(1); n += 1 }
    }

    static func metrics(_ app: AppModel) -> ShellMetrics {
        guard let w = GameServices.keyWindow() else { return ShellMetrics() }
        return ShellMetrics(size: w.bounds.size, safeTop: w.safeAreaInsets.top, safeBottom: w.safeAreaInsets.bottom,
                            popupUpscale: app.tuning.ui.popupUpscale)
    }
}

// MARK: - glue for S2's win-panel Rocket Race bar and S3's home badge

@MainActor enum EventsGlue {
    static func install(_ app: AppModel) {
        if RocketRaceStripSource.provider == nil { RocketRaceStripSource.provider = { rocketStrip($0) } }
        if HomeEventHooks.rocketRank == nil {
            HomeEventHooks.rocketRank = { a in rocketLanes(a)?.lanes.first(where: \.isMe)?.rank }
        }
    }

    /// The running race's five lanes: the four rivals (SOC1's world, their own clock) + the player; ranks by progress, a tie
    /// behind the rival (C3's rule).
    static func rocketLanes(_ app: AppModel) -> (lanes: [RaceLaneVM], goal: Int, endsAt: SocialTime)? {
        let s = app.store.state
        guard let run = s.events.rocket.active else { return nil }
        let t = EconomyClock.peekSocial(s, wall: app.clock.wallClock())
        let goal = app.economy.events.rocketRace.levels(stage: run.stage)
        let rivals = app.rivals.rocketRace(run.instance, joinedAt: run.joinedAt, at: t).filter { !$0.isMe }
        let me = s.social.standing(installSeed: s.installSeed, level: s.level)
        var rows: [RaceLaneVM] = rivals.map { RaceLaneVM(rank: 0, name: $0.player.name, avatar: $0.player.avatar,
                                                         progress: min(goal, $0.score), isMe: false) }
        rows.append(RaceLaneVM(rank: 0, name: me.name, avatar: me.avatar, progress: min(goal, run.progress), isMe: true))
        rows.sort { a, b in a.progress != b.progress ? a.progress > b.progress : (!a.isMe && b.isMe) }
        for i in rows.indices { rows[i].rank = i + 1 }
        return (rows, goal, run.instance.end)
    }

    /// SOC2's Rocket Race offer "Start": C3's join (saved) + the ∞ 30m join claim shown at once (SPEC-social §4.5).
    @discardableResult
    static func joinRocketRace(_ app: AppModel) -> Result<RocketRun, JoinError> {
        let now = app.clock.wallClock()
        let rules = app.economy
        let r = app.store.mutateAndSave { Events.joinRocketRace(&$0, now: now, rules: rules) }
        Log.mark("event", "rocketRace join → \(r)")
        if case .success = r { Task { @MainActor in _ = await HomeQueue.shared.presentClaims(app) } }
        return r
    }

    /// SOC2's Sky Jump offer "Start": C3's join (saved; a run lasts 24 h, stage N first-try wins in a row).
    @discardableResult
    static func joinSkyJump(_ app: AppModel) -> Result<SkyJumpRun, JoinError> {
        let now = app.clock.wallClock()
        let rules = app.economy
        let r = app.store.mutateAndSave { Events.joinSkyJump(&$0, now: now, rules: rules) }
        Log.mark("event", "skyJump join → \(r)")
        return r
    }

    static func rocketStrip(_ app: AppModel) -> RocketRaceStripData? {
        guard let r = rocketLanes(app) else { return nil }
        let t = EconomyClock.peekSocial(app.store.state, wall: app.clock.wallClock())
        return RocketRaceStripData(lanes: r.lanes, goal: r.goal, timeLeft: Countdown.text(Double(r.endsAt.seconds - t.seconds)),
                                   ends: r.endsAt)                    // FIX-2 B (review of L28): the bar's chip ticks
    }
}
