import SwiftUI
import PathCore

// SOCIAL SOC2 (SPEC-architecture §6.6 social popups, §6.9, §8.4 EventsDirector; SPEC-social §4, §4.8; SPEC-ui §2.15.7,
// §2.17, §2.18; SPEC-motion-audio §6.5, §9). The event flows the social screens start themselves, all through C3's public
// state machines (`Events.join…`, `Events.claim`, `Events.refresh`) and the popup host:
//   Rocket Race   offer → Start: join (C3) → the ∞ 30m join claim (S2's claim overlay) → the tutorial (first join) → the race page
//   Sky Jump      offer → Start: join (C3) → "Finding players on your level." → the tutorial (first run) → the map
//   Weekly        the L50 forced tutorial (only the trophy tab answers) → the Weekly tab → the info overlay → the group joins
//   Streak Race   opening the page joins the day's race (the list auto-shows on the phone: the join happens there)
// World-side work (`Events.refresh` asks the world for races and settlements) runs OFF the main thread on a copy of the state
// and is applied only when the state did not change meanwhile (optimistic; the main thread compares and assigns).
// SocHooks installs the data SHELL asks SOCIAL for: the Rocket Race rank on the home badge, the trophy "!" news and the win
// panel's Rocket Race bar.

@MainActor enum SocHooks {
    static func install(_ app: AppModel, model: SocialModel) {
        // GAME G2's home queue routes to the SOC2 pages once they exist (EventsDirector `G2Hooks`); two claims get SOC2's
        // screen first — the Sky Jump "You win!" (VERIFIED 094 before the claim 095) and the Weekly result (SPEC-ui §2.15.8) —
        // then G2's claim overlay applies them as usual (the presenter answers false)
        G2Hooks.eventPagesInstalled = true
        G2Hooks.claimPresenter = { @MainActor app, claim in
            let r: PopupRequest
            switch claim.kind {
            case .skyJumpShare: r = .skyJump(.win)
            case .weeklyPrize: r = .custom(id: "weeklyResult", params: ["rank": "\(claim.value)", "prize": "\(claim.grant.coins)"])
            default: return false
            }
            guard PopupContent.hasPanel(r) else { return false }
            SocialModel.shared?.request(.sky)
            _ = await app.popups.present(Popup<PopupResult>(r, style: SocialPopups.style(r), fallback: .primary))
            return false
        }
        HomeEventHooks.rocketRank = { app in
            guard let m = SocialModel.shared, app.store.state.events.rocket.active != nil else { return nil }
            m.requestIfStale(.rocket, seconds: 15)
            return m.rocket.map { $0.result == "none" ? $0.myRank : nil } ?? nil
        }
        HomeEventHooks.leaderboardNews = { app in
            guard let m = SocialModel.shared, let seen = m.lastSeenWeeklyRank, let w = m.weekly else { return false }
            return w.myRank > seen
        }
        RocketRaceStripSource.provider = { app in
            guard let m = SocialModel.shared, let run = app.store.state.events.rocket.active else { return nil }
            m.requestIfStale(.rocket, seconds: 5)
            guard let snap = m.rocket, snap.raceId == run.instance.index else { return nil }
            // the player's own progress is read live (the win that opened this panel is already counted by C3)
            let mine = run.progress
            let rivals = snap.lanes.filter { !$0.isMe }
            let myRank = 1 + rivals.filter { $0.progress >= mine }.count
            var lanes = [RaceLaneVM(rank: myRank, name: app.store.state.social.displayName(installSeed: app.store.state.installSeed),
                                    avatar: app.store.state.social.avatar, progress: mine, isMe: true)]
            var r = 0
            for l in rivals {
                r += 1
                lanes.append(RaceLaneVM(rank: r >= myRank ? r + 1 : r, name: l.player.name, avatar: l.player.avatar,
                                        progress: l.progress, isMe: false))
            }
            let left = SocTime.left(run.instance.end, now: SocTime.now(app))
            return RocketRaceStripData(lanes: lanes, goal: snap.goal, timeLeft: Countdown.text(left), ends: run.instance.end)
        }
    }
}

extension SocialModel {
    /// Recomputes `s` when its snapshot is older than `seconds` of world time (home badges re-read every 20 s).
    func requestIfStale(_ s: Surface, seconds: Int64) {
        guard let app else { return }
        let now = SocTime.now(app)
        let at: SocialTime? = {
            switch s {
            case .rocket: return rocket?.computedAt
            case .sky: return sky?.computedAt
            case .streak: return streak?.computedAt
            case .weekly: return weekly?.computedAt
            default: return nil
            }
        }()
        guard at.map({ now.seconds - $0.seconds >= seconds }) ?? true else { return }
        // Called from view bodies (the home Rocket badge, the win panel's race bar): each publish re-renders the caller, so a
        // snapshot that stays stale (nil while a run is being set up, a fast -pc.clockRate) must not become a request loop
        // (measured: ~50 rocket publishes in 0.5 s at launch before this guard).
        let t = ProcessInfo.processInfo.systemUptime
        if let last = lastAsked[s], t - last < 1.0 { return }
        lastAsked[s] = t
        request(s)
    }
}

@MainActor enum SocialFlows {
    // MARK: world-side event upkeep (off the main thread)

    /// `Events.refresh` (joins today's Streak Race and the week's Claw, ends a Rocket Race a rival finished, settles ended Streak
    /// Races from the world's final standings) computed on a background copy, applied if the state is unchanged.
    static func refreshEvents(_ app: AppModel, home: Bool = true, then: (() -> Void)? = nil) {
        guard let world = app.socialWorld else { then?(); return }
        let before = app.store.state
        let wall = app.clock.wallClock()
        let rules = ShellEconomy.rules(app)
        let fallback = SocialModel.shared?.config.fallbackCountry ?? "US"
        DispatchQueue.global(qos: .userInitiated).async {
            var s = before
            let me = s.social.standing(installSeed: s.installSeed, level: s.level, fallbackCountry: fallback)
            let out = Events.refresh(&s, now: wall, rivals: world, me: me, rules: rules, home: home)
            // Weekly Contests that ended: the final rank from the world, then C3's settlement (podium prize claim, a win)
            settleWeeks(&s, world: world, rules: rules, fallback: fallback)
            let changed = s != before
            let after = s
            DispatchQueue.main.async {
                MainActor.assumeIsolated {
                    if changed {
                        if app.store.state == before {
                            app.store.mutateAndSave { $0 = after }
                            SocOpenProbe.mark("events refresh applied")
                            if !out.isEmpty { Log.mark("event", "refresh \(out.count) outcome(s)") }
                        } else {
                            Log.mark("social", "event refresh skipped: the state changed meanwhile (next open retries)")
                        }
                    }
                    then?()
                }
            }
        }
    }

    /// Weekly Contests that ended (C3 `Events.weeksToSettle`): the player's final rank from the world at the week's last
    /// second, then C3's settlement (the podium prize as a claim, rank 1 = a Weekly Contest Win on the Profile). Off the main
    /// thread; applied only if the state did not change meanwhile. Run at the first social use (boot) and with every refresh.
    static func settleEndedWeeks(_ app: AppModel) {
        guard let world = app.socialWorld, !Events.weeksToSettle(app.store.state).isEmpty else { return }
        let before = app.store.state
        let rules = ShellEconomy.rules(app)
        let fallback = SocialModel.shared?.config.fallbackCountry ?? "US"
        DispatchQueue.global(qos: .utility).async {
            var s = before
            settleWeeks(&s, world: world, rules: rules, fallback: fallback)
            let after = s
            DispatchQueue.main.async {
                MainActor.assumeIsolated {
                    guard after != before, app.store.state == before else { return }
                    app.store.mutateAndSave { $0 = after }
                    SocOpenProbe.mark("weekly settle applied")
                    Log.mark("event", "weeklyContest settled \(Events.weeksToSettle(before).map { "w\($0.index)" }.joined(separator: ","))")
                }
            }
        }
    }

    /// The pure part of `settleEndedWeeks` (off the main thread): every ended week takes its final rank from the world's group
    /// board one second before the week's end, then C3 settles it (the podium prize as a claim; rank 1 = the Profile's
    /// "Weekly Contest Wins").
    nonisolated static func settleWeeks(_ s: inout PlayerState, world: SocialWorld, rules: EconomyRules, fallback: String) {
        for res in Events.weeksToSettle(s) {
            let end = EventSchedule.weekStart(res.index + 1, rules.events.calendar)
            let me = s.social.standing(installSeed: s.installSeed, level: s.level, fallbackCountry: fallback)
            if let b = world.weeklyBoard(week: res.index, me: me, at: SocialTime(seconds: end.seconds - 1)), b.myRank > 0 {
                _ = Events.settleWeekly(&s, week: res.index, rank: b.myRank, rules: rules)
            }
        }
    }

    /// Opening the Weekly tab at L50+ joins this week's contest (C3; no world query). True when it joined now.
    @discardableResult
    static func joinWeeklyIfNeeded(_ app: AppModel) -> Bool {
        let rules = ShellEconomy.rules(app)
        let wall = app.clock.wallClock()
        guard EventSchedule.isUnlocked(.weeklyContest, level: app.store.state.level, rules: rules.events),
              app.store.state.events.weekly.index == nil else { return false }
        let joined = app.store.mutateAndSave { Events.joinWeekly(&$0, now: wall, rules: rules) }
        if joined { Log.mark("event", "weeklyContest joined") }
        return joined
    }

    // MARK: Rocket Race

    /// "Start" on the Rocket Race offer: join, the ∞ join claim, the first-time tutorial, then the race page.
    static func startRocketRace(_ app: AppModel) {
        let rules = ShellEconomy.rules(app)
        let wall = app.clock.wallClock()
        let result = app.store.mutateAndSave { Events.joinRocketRace(&$0, now: wall, rules: rules) }
        switch result {
        case .failure(let e):
            Log.mark("event", "rocketRace join refused: \(e)")
            if case .notLive = e { app.toasts.show("This event has ended.") }  // B1: a stale Join that raced the Monday roll
            return
        case .success(let run):
            Log.mark("event", "rocketRace joined race \(run.instance.index) stage \(run.stage)")
            SocialModel.shared?.request(.rocket)
            Task { @MainActor in
                await claimAll(app, kinds: [.rocketJoin])
                if !app.store.state.flags.seen.contains("social.rocketRace") {
                    _ = await app.popups.present(Popup<PopupResult>(.rocketRace(.tutorial), style: PopupStyle(dim: .info, closesOnTapAnywhere: true),
                                                                    fallback: .close))
                    app.store.mutateAndSave { $0.flags.seen.insert("social.rocketRace") }
                }
                app.router.go(.event(.rocketRace))
            }
        }
    }

    // MARK: Sky Jump

    /// "Start" on the Sky Jump offer: join (C3), the matching screen, the first-time tutorial, then the map.
    static func startSkyJump(_ app: AppModel) {
        let rules = ShellEconomy.rules(app)
        let wall = app.clock.wallClock()
        let result = app.store.mutateAndSave { Events.joinSkyJump(&$0, now: wall, rules: rules) }
        switch result {
        case .failure(let e):
            Log.mark("event", "skyJump join refused: \(e)")
            if case .notLive = e { app.toasts.show("This event has ended.") }  // B1: a stale Join that raced the Monday roll
        case .success(let run):
            Log.mark("event", "skyJump joined attempt \(run.instance.index) stage \(run.stage)")
            SocialModel.shared?.request(.sky)
            Task { @MainActor in
                _ = await app.popups.present(Popup<PopupResult>.skyJump(.matching))
                if !app.store.state.flags.seen.contains("social.skyJump") {
                    _ = await app.popups.present(Popup<PopupResult>(.skyJump(.tutorial), style: PopupStyle(dim: .info, closesOnTapAnywhere: true),
                                                                    fallback: .close))
                    app.store.mutateAndSave { $0.flags.seen.insert("social.skyJump") }
                }
                app.router.go(.event(.skyJump))
            }
        }
    }

    // MARK: Weekly Contest (the L50 forced tutorial, SPEC-ui §2.15.7)

    /// The forced step: only the trophy tab answers; then the Weekly tab, the info overlay, the join.
    static func weeklyTutorial(_ app: AppModel) async {
        _ = await app.popups.present(Popup<PopupResult>.weeklyContestTutorial)
        LeaderboardShellState.shared.tab = .weekly
        app.router.go(.home(.normal, tab: .leaderboard))
        // A2 (motion-catalog §3.1, v552): the queued popup shows once the tab slide has settled, not over the moving page
        await (app.router as? Router)?.settle()
        await HomeTabStrip.shared.settled()
        _ = await app.popups.present(Popup<PopupResult>.weeklyContestIntro)
        joinWeeklyIfNeeded(app)
        app.store.mutateAndSave { $0.flags.weeklyIntroSeen = true }
        SocialModel.shared?.request(.weekly)
    }

    // MARK: claims

    /// Presents and applies every claim of these kinds ("Congratulations! … Tap to Claim", S2's overlay; the grant is C3's).
    static func claimAll(_ app: AppModel, kinds: Set<EventClaim.Kind>) async {
        while let c = app.store.state.events.claims.first(where: { kinds.contains($0.kind) }) {
            _ = await app.popups.present(Popup<PopupResult>.claimReward(c.grant))
            let now = app.clock.wallClock()
            app.store.mutateAndSave { _ = Events.claim(&$0, id: c.id, now: now) }
            Log.mark("event", "claimed \(c.kind.rawValue) #\(c.id)")
        }
    }
}
