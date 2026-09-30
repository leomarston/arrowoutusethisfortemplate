import SwiftUI
import UIKit
import PathCore

// SOCIAL SOC2 (SPEC-architecture §6.1 "SocialModel (wrapping SocialWorld + the rewind-safe clock)", §6.9, §10.2; CONSISTENCY
// V-29 / SPEC.md §5.21: "social = 0 ms main thread"; SPEC-social §3.4 live updates). The app side of the offline world:
//   - every world query (World / Country pages, the Weekly group, the Streak Race's 50 rows, the Rocket Race lanes, the Sky Jump
//     field) runs on ONE serial background queue against PathCore's immutable `SocialWorld` (thread-safe, SOC1); the main
//     thread only copies the player's state (a value), reads the clock, and swaps the finished snapshot in;
//   - text of the long lists is shaped on that queue too (SocType), so publishing a snapshot costs layer writes only;
//   - while a social surface is on screen it refreshes every `refreshSeconds` (5 s, social.json) — boards move on their own
//     clock (`-pc.clockRate` speeds it up for SocialLab) and nothing ever moves backwards (the SocialClock high-water mark);
//   - the home's event badges, the trophy "!" and the win panel's Rocket Race bar read the latest snapshots through the hooks
//     SHELL left for SOCIAL (`HomeEventHooks`, `RocketRaceStripSource`).
// The player's home country is frozen at the first social use from the device region (`Locale.current.region`, SPEC-social
// §2.3; `-pc.socialCountry <ISO>` overrides it for tests and captures).

/// Everything a background computation needs, captured on the main thread (values and thread-safe objects only).
struct SocInputs: @unchecked Sendable {
    let world: SocialWorld
    let state: PlayerState
    let now: SocialTime
    let me: PlayerStanding
    let config: SocialConfig
    let rules: EconomyRules
    let scale: CGFloat
    let captionLevel: String
    let captionScore: String
}

// MARK: - snapshots (immutable, built off the main thread)

struct SocWeeklySnap: Sendable {
    let week: Int
    let podium: [LeaderboardRow]           // ranks 1-3 (the player may stand on it)
    let prizes: [Int]
    let list: SocListContent               // ranks 4…10
    let myRank: Int
    let endsAt: SocialTime
    let computedAt: SocialTime
}

struct SocStreakSnap: Sendable {
    let day: Int
    let list: SocListContent               // all 50 rows
    let prizes: [Int]
    let endsAt: SocialTime
    let myRank: Int
    let myScore: Int
    let computedAt: SocialTime
}

struct SocRocketLane: Sendable, Equatable {
    let player: SimPlayer
    let progress: Int
    let rank: Int
    let isMe: Bool
}

struct SocRocketSnap: Sendable {
    let raceId: Int
    let stage: Int
    let goal: Int
    /// Lane order on the race page: the player first, then the rivals as the world orders them (SPEC-ui §2.17.3).
    let lanes: [SocRocketLane]
    /// "none" while running, "lost" / "won" / "expired" after (C3's `lastResult` for an ended race).
    let result: String
    let endsAt: SocialTime
    let computedAt: SocialTime
    var myRank: Int { lanes.first(where: \.isMe)?.rank ?? 0 }
    var leaderLane: Int? { lanes.firstIndex { $0.rank == 1 } }
}

struct SocSkySnap: Sendable {
    let attemptId: Int
    let stage: Int
    let goal: Int
    let progress: Int
    let alive: [Int]                       // "Players" after the player's k-th first-try win; alive[goal] = winners
    let pool: Int
    let share: Int
    let shown: [SimPlayer]                 // up to 14 portraits (the matching fan, the pads)
    let endsAt: SocialTime
    let result: String                     // "none" | "won" | "failed" | "expired"
    let computedAt: SocialTime
    var playersLeft: Int { alive[max(0, min(progress, goal))] }
    var winners: Int { alive[goal] }
}

/// The run a race page draws: the active run, or C3's persisted ended run (`EventsState` rocket / sky `lastRun`, which keeps
/// the join time and the player's final lane across a relaunch; INTEG for SOC2's C3 request).
struct SocRunMemo: Sendable, Equatable {
    let index: Int
    let stage: Int
    let joinedAt: SocialTime
    let end: SocialTime
    var progress: Int
}

// MARK: - the model

@MainActor @Observable final class SocialModel {
    enum Surface: String, CaseIterable, Sendable { case world, country, weekly, streak, rocket, sky }

    private(set) static var shared: SocialModel?

    @ObservationIgnored weak var app: AppModel?
    var weekly: SocWeeklySnap?
    var streak: SocStreakSnap?
    var rocket: SocRocketSnap?
    var sky: SocSkySnap?
    /// The lists' pill states (drawn by SwiftUI over the CA lists).
    var jumps: [SocListKind: SocJump] = [:]
    /// True while a list's pinned player row sits at the bottom edge (the Country "Top" pill moves above it).
    var pinnedBottom: [SocListKind: Bool] = [:]
    /// Bumped when a list got a new snapshot (tests / capture readiness).
    var listVersion: [SocListKind: Int] = [:]
    /// The Weekly rank the Leaderboard showed last (the trophy "!" when it dropped, SPEC-social §3.4).
    @ObservationIgnored var lastSeenWeeklyRank: Int?

    @ObservationIgnored private(set) var lists: [SocListKind: SocListHost] = [:]
    @ObservationIgnored private let queue = DispatchQueue(label: "com.manycode.arrowout.social", qos: .userInitiated)
    @ObservationIgnored private var inFlight: Set<Surface> = []
    @ObservationIgnored private var dirty: Set<Surface> = []
    /// When a view-body hook last asked for each surface (`requestIfStale`): at most one ask a second, whatever comes back.
    @ObservationIgnored var lastAsked: [Surface: CFTimeInterval] = [:]
    @ObservationIgnored private var visible: [Surface: Int] = [:]
    @ObservationIgnored private var timer: Timer?
    @ObservationIgnored private(set) var config: SocialConfig
    /// Wall seconds spent on the main thread publishing snapshots (SocialLab / tests read it).
    @ObservationIgnored private(set) var mainPublishMs: [Double] = []
    @ObservationIgnored private(set) var workerMs: [Surface: Double] = [:]
    /// When the last snapshot was published (CACurrentMediaTime; the scroll bench correlates slow frames with it).
    @ObservationIgnored private(set) var lastPublishAt: CFTimeInterval = 0

    private init(app: AppModel) {
        self.app = app
        config = app.tuning.social.config
        SocType.turkish = GameText.isTurkish
    }

    /// The one model (created at the first social use; idempotent). Installs the SHELL hooks and freezes the home country.
    @discardableResult
    static func install(_ app: AppModel) -> SocialModel {
        if let m = shared, m.app === app { return m }
        let m = SocialModel(app: app)
        shared = m
        SocHooks.install(app, model: m)
        // the social screens' rasters decoded OFF the main thread now (behind Loading), so no page's first frame decodes a
        // full-screen backdrop on the main thread (SPEC-architecture §10.2 "no first-presentation stall")
        DispatchQueue.global(qos: .utility).async { ArtStore.preload(SocialModel.art) }
        // observed state (the store, the shell's tab) changes after the current view update, never inside it
        Task { @MainActor in
            m.freezeHomeCountry()
            if case .leaderboard(let sub)? = app.args.go, let sub, let tab = LeaderboardShellState.Tab(rawValue: sub) {
                LeaderboardShellState.shared.tab = tab
            }
            SocScenario.applyIfRequested(app)
            for _ in 0..<100 where app.socialWorld == nil { try? await Task.sleep(nanoseconds: 50_000_000) }
            SocialFlows.settleEndedWeeks(app)
            Log.mark("social", "SocialModel installed (country \(app.store.state.social.country ?? "-"), refresh \(m.config.refreshSeconds) s)")
            #if DEBUG || PC_MEASURE
            if app.args.raw["pc.lab"] == "open" { SocOpenBench.run(app) }        // SocialLab.swift (Debug / Measure only)
            #else
            if app.args.raw["pc.lab"] == "open" {
                Log.error("social", "-pc.lab open: no open bench in this build (Release); labs run in Debug / Measure")
            }
            #endif
        }
        return m
    }

    /// Every raster the social screens draw (UIArtBundleTests-style check in SocialScreensTests).
    nonisolated static let art: [UIArt] = [
        .leaderboardPodium, .rank1Badge, .rank2Badge, .rank3Badge, .rewardCoinBowl, .socialScoreChip, .eventStreakRaceHeader,
        .eventRocketRaceBackdrop, .eventRocketRaceOffer, .eventRocketRaceRacerMine, .eventRocketRaceRacerOther, .rank1Wings, .eventRocketRaceStage1, .eventRocketRaceStage2, .eventRocketRaceStage3,
        .rewardChest1, .rewardChest2, .rewardChest3, .eventSkyJumpBackdrop, .eventSkyJumpPlatform, .eventSkyJumpPlatformFar, .eventSkyJumpPlatformFar2,
        .eventSkyJumpPad, .eventSkyJumpOffer, .eventClawChallengeHeader, .iconInfo, .iconPointer, .iconPointerDown, .livesLost,
        .fxSunburst, .iconLock, .iconCheck, .eventClawChallengeToken, .livesUnlimited, .livesUnlimitedSmall, .boosterFreezeIcon, .boosterHintIcon,
        .rewardCoinsSmall, .navLeaderboardIcon, .hudTimerIconSmall, .iconFinishFlag,
    ] + Avatars.arts + UpAwayArt.ids.compactMap { UIArt(rawValue: $0) }      // B1: Up & Away's art once R8 ships it
      + [.eventBalloonRiseCloudA, .eventBalloonRiseCloudB]                                      // A4: R8's optional clouds on the Up & Away page

    private func freezeHomeCountry() {
        guard let app else { return }
        let forced = app.args.raw["pc.socialCountry"].map { $0.uppercased() }
        if let forced, forced.count == 2, app.store.state.social.country != forced {
            app.store.mutateAndSave { $0.social.country = forced }
            return
        }
        if app.store.state.social.country == nil {
            // B2 (M3): the device region resolved on the world's region map (a territory → its board's country, a numeric
            // region → its representative; an unknown 2-letter code stays itself = its own LOCAL board)
            let home = config.model.homeBoard(forRegion: Locale.current.region?.identifier, fallback: config.fallbackCountry)
            let off = TimeZone.current.secondsFromGMT() / 60
            app.store.mutateAndSave { $0.social.setHomeIfNeeded(region: home.iso, offsetMinutes: off, fallback: self.config.fallbackCountry) }
        }
    }

    // MARK: lists

    func listHost(_ kind: SocListKind) -> SocListHost {
        if let h = lists[kind] { return h }
        let scale = UIScreen.main.scale
        let spec: SocListView.Spec
        switch kind {
        case .world:
            spec = .init(kind: .world, geo: .leaderboard, firstTop: 17.2, bottomPad: 90, pinTop: nil, pinBottom: nil,
                         opensAtMe: false, jump: .bottom)
        case .country:
            spec = .init(kind: .country, geo: .leaderboard, firstTop: 17.2, bottomPad: 90, pinTop: 10.4, pinBottom: 569,
                         opensAtMe: true, jump: .top)
        case .weekly:
            // the list viewport starts at 500 (190 + 310); rank 4 sits at the top (505.7). FIX-V2 F-03: 13.4 pt under the last
            // row, not 90 (VERIFIED 132 / 476 / 502 weekly-bottom: the last row's face 686.2-752.2 over a 771.7 viewport end)
            spec = .init(kind: .weekly, geo: .leaderboard, firstTop: 5.7, bottomPad: 13.4, pinTop: 3.8, pinBottom: 259,
                         opensAtMe: true, jump: .none)
        case .streak:
            spec = .init(kind: .streak, geo: .streakRace, firstTop: 0.7, bottomPad: 40, pinTop: 0.9, pinBottom: 364,
                         opensAtMe: true, jump: .none)
        }
        let list = SocListView(spec: spec, scale: scale)
        list.onJump = { [weak self] j in self?.jumps[kind] = j }
        list.onPinBottom = { [weak self] b in self?.pinnedBottom[kind] = b }
        let host = SocListHost(list)
        lists[kind] = host
        return host
    }

    // MARK: visibility + refresh

    func appear(_ s: Surface) {
        visible[s, default: 0] += 1
        request(s)
        startTimer()
    }

    func disappear(_ s: Surface) {
        visible[s] = max(0, (visible[s] ?? 0) - 1)
        if visible[s] == 0 { visible[s] = nil }
        if visible.isEmpty { timer?.invalidate(); timer = nil }
    }

    private func startTimer() {
        guard timer == nil else { return }
        let period = max(1, Double(config.refreshSeconds))
        timer = Timer.scheduledTimer(withTimeInterval: period, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated { self?.tick() }
        }
    }

    private func tick() {
        for s in visible.keys where isOnScreen(s) { request(s) }
    }

    /// True when the surface's screen is the router's current one (HomeView keeps the Leaderboard page mounted behind the
    /// home tab; it must not refresh there).
    func isOnScreen(_ s: Surface) -> Bool {
        guard let app else { return false }
        // FIX-A1 (cross-owner fix, reported): the list surfaces are shown ONLY on home's Leaderboard tab (and SocialLab).
        // Home is now kept mounted — parked, hidden — under event, level and profile screens (Router `cutLayers`), so its
        // hidden Leaderboard page must not count as on screen there: before this, an event page (`case .event: true`) made
        // the hidden Weekly tab join the contest and the lists refresh, and a popup over a level did the same.
        let list = s == .world || s == .country || s == .weekly
        switch app.router.screen {
        case .home(_, let tab):
            switch s {
            case .world, .country, .weekly: return tab == .leaderboard
            default: return app.popups.isPresenting
            }
        case .event: return !list
        case .lab: return s == .world || s == .country      // SocialLab's scroll bench lists; never a Weekly join from a lab
        default: return !list && app.popups.isPresenting
        }
    }

    /// Queues a background recomputation of `s` (coalesced: one in flight per surface, one more after it if asked again).
    func request(_ s: Surface) {
        guard !inFlight.contains(s) else { dirty.insert(s); return }
        guard let inputs = captureInputs() else {
            // the world is still being built off the main thread (Loading): try again shortly
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in MainActor.assumeIsolated { self?.request(s) } }
            return
        }
        inFlight.insert(s)
        queue.async { [weak self] in
            let t0 = CACurrentMediaTime()
            let result = SocCompute.run(s, inputs)
            let ms = (CACurrentMediaTime() - t0) * 1000
            DispatchQueue.main.async {
                MainActor.assumeIsolated {
                    guard let self else { return }
                    self.workerMs[s] = ms
                    self.publish(result)
                    self.inFlight.remove(s)
                    if self.dirty.remove(s) != nil { self.request(s) }
                }
            }
        }
    }

    /// Times the presented frames of a social screen's first 1.5 s (S1's FrameProbe): `[PC][perf] social:<name> open frames
    /// <n> max <ms> ms over20 <k>` — the evidence that no screen's first presentation stalls (SPEC-architecture §10.2).
    func probeOpen(_ name: String, _ s: Surface? = nil) {
        // only a screen really on screen (not the Leaderboard page pre-rendered behind Loading or mounted behind home)
        if let s, !isOnScreen(s) { return }
        let p = SocOpenProbe("social:\(name) open")
        p.begin()
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 1_500_000_000)
            p.end()
        }
    }

    /// Recompute every surface now (after a join / a win / a clock change).
    func requestAll(_ ss: [Surface] = Surface.allCases) { for s in ss { request(s) } }

    func captureInputs() -> SocInputs? {
        guard let app, let world = app.socialWorld else { return nil }
        let s = app.store.state
        let wall = app.clock.wallClock()
        let now = EconomyClock.peekSocial(s, wall: wall)
        // the world shown is the high-water mark from now on (SPEC-social §5 "raised on every read": a clock set back later
        // freezes the boards instead of rewinding them); written at most once a minute of world time
        if now.seconds - s.social.highWater >= 60 {
            DispatchQueue.main.async { [weak app] in
                MainActor.assumeIsolated {
                    guard let app else { return }
                    app.store.mutateAndSave { st in _ = EconomyClock.social(&st, wall: wall) }
                }
            }
        }
        let me = s.social.standing(installSeed: s.installSeed, level: s.level, fallbackCountry: config.fallbackCountry)
        return SocInputs(world: world, state: s, now: now, me: me, config: config, rules: ShellEconomy.rules(app),
                         scale: UIScreen.main.scale, captionLevel: String(localized: "Level"),
                         captionScore: String(localized: "Score"))
    }

    private func publish(_ r: SocCompute.Result) {
        let t0 = CACurrentMediaTime()
        switch r {
        case .list(let c):
            listHost(c.kind).list.apply(c)
            listVersion[c.kind, default: 0] += 1
        case .weekly(let w):
            weekly = w
            if let w {
                listHost(.weekly).list.apply(w.list)
                listVersion[.weekly, default: 0] += 1
            }
        case .streak(let s):
            streak = s
            if let s {
                listHost(.streak).list.apply(s.list)
                listVersion[.streak, default: 0] += 1
            }
        case .rocket(let r):
            rocket = r
        case .sky(let s):
            sky = s
        }
        let ms = (CACurrentMediaTime() - t0) * 1000
        SocOpenProbe.mark(String(format: "publish %@ %.1f ms", r.name, ms))
        lastPublishAt = CACurrentMediaTime()
        mainPublishMs.append(ms)
        if mainPublishMs.count > 200 { mainPublishMs.removeFirst(mainPublishMs.count - 200) }
    }
}

// MARK: - the background computations (pure; any thread)

enum SocCompute {
    enum Result: @unchecked Sendable {
        case list(SocListContent)
        case weekly(SocWeeklySnap?)
        case streak(SocStreakSnap?)
        case rocket(SocRocketSnap?)
        case sky(SocSkySnap?)
    }

    static func run(_ s: SocialModel.Surface, _ i: SocInputs) -> Result {
        switch s {
        case .world: let c = worldList(i); SocArt.warm(c, scale: i.scale); return .list(c)
        case .country: let c = countryList(i); SocArt.warm(c, scale: i.scale); return .list(c)
        case .weekly: let w = weekly(i); if let w { SocArt.warm(w.list, scale: i.scale) }; return .weekly(w)
        case .streak: let st = streak(i); if let st { SocArt.warm(st.list, scale: i.scale) }; return .streak(st)
        case .rocket: return .rocket(rocket(i).0)
        case .sky: return .sky(sky(i).0)
        }
    }

    static func rows(_ kind: SocListKind, _ rows: [LeaderboardRow], caption: String?) -> [SocListItem] {
        rows.map { .row(SocRowBuilder.row(kind, rank: $0.rank, player: $0.player, value: $0.value, isMe: $0.isMe, caption: caption)) }
    }

    /// World: ranks 1-100, then "• • •" and the player's R ± 10 (SPEC-social §3.3, CONSISTENCY V-19). Opens at the top.
    static func worldList(_ i: SocInputs) -> SocListContent {
        let L = i.config.lists
        let top = i.world.page(.world, me: i.me, at: i.now, ranks: 1...max(1, L.worldTop))
        var items = rows(.world, top.rows, caption: i.captionLevel)
        let R = top.myRank
        if R > L.worldTop {
            let lo = max(L.worldTop + 1, R - L.window)
            if lo > L.worldTop + 1 { items.append(.separator) }
            let around = i.world.page(.world, me: i.me, at: i.now, ranks: lo...(R + L.window))
            items += rows(.world, around.rows, caption: i.captionLevel)
        }
        return SocListContent(kind: .world, items: items, myRank: R, total: top.total, computedAt: i.now)
    }

    /// Country: one continuous list 1…R+10 while R ≤ 600 (VERIFIED Turkey #455, CONSISTENCY V-20), else like World. Opens
    /// centred on the player's row.
    static func countryList(_ i: SocInputs) -> SocListContent {
        let L = i.config.lists
        let iso = i.me.country.uppercased()
        let head = i.world.page(.country(iso), me: i.me, at: i.now, ranks: 1...1)
        let R = head.myRank
        var items: [SocListItem]
        if R <= L.countryContinuousUpTo {
            let p = i.world.page(.country(iso), me: i.me, at: i.now, ranks: 1...max(1, R + L.window))
            items = rows(.country, p.rows, caption: i.captionLevel)
        } else {
            let p = i.world.page(.country(iso), me: i.me, at: i.now, ranks: 1...L.worldTop)
            items = rows(.country, p.rows, caption: i.captionLevel)
            items.append(.separator)
            let around = i.world.page(.country(iso), me: i.me, at: i.now, ranks: (R - L.window)...(R + L.window))
            items += rows(.country, around.rows, caption: i.captionLevel)
        }
        return SocListContent(kind: .country, items: items, myRank: R, total: head.total, computedAt: i.now)
    }

    /// The player's Weekly Contest group (10 players; podium 1-3 + the list from rank 4). nil until the week's group formed.
    static func weekly(_ i: SocInputs) -> SocWeeklySnap? {
        let week = EventSchedule.week(i.now, i.rules.events.calendar)
        guard let b = i.world.weeklyBoard(week: week, me: i.me, at: i.now) else { return nil }
        let podium = Array(b.rows.prefix(3))
        let rest = Array(b.rows.dropFirst(3))
        let list = SocListContent(kind: .weekly, items: rows(.weekly, rest, caption: i.captionScore), myRank: b.myRank,
                                  total: b.rows.count, computedAt: i.now)
        return SocWeeklySnap(week: week, podium: podium, prizes: b.prizes, list: list, myRank: b.myRank, endsAt: b.endsAt,
                             computedAt: i.now)
    }

    /// Today's Streak Race: 50 rows with their prizes (2000 / 1000 / 500 / 100 × 7, VERIFIED meta-045..052).
    static func streak(_ i: SocInputs) -> SocStreakSnap? {
        let ev = i.rules.events
        guard EventSchedule.isUnlocked(.streakRace, level: i.state.level, rules: ev),
              let inst = EventSchedule.instance(.streakRace, at: i.now, rules: ev) else { return nil }
        let day = inst.index
        var lbRows: [LeaderboardRow]
        var prizes = ev.streakRace.prizes
        var endsAt = inst.end
        if let key = i.state.social.streakKey(day: day) {
            let b = i.world.streakBoard(key: key, me: i.me, at: i.now)
            lbRows = b.rows; prizes = b.prizes; endsAt = b.endsAt
        } else {
            lbRows = i.world.streakRace(inst, player: i.me, at: i.now).map {
                LeaderboardRow(rank: $0.rank, player: $0.player, value: $0.score, isMe: $0.isMe)
            }
        }
        let items: [SocListItem] = lbRows.map { r in
            let prize = r.rank >= 1 && r.rank <= prizes.count ? prizes[r.rank - 1] : 0
            return .row(SocRowBuilder.row(.streak, rank: r.rank, player: r.player, value: r.value, isMe: r.isMe, prize: prize,
                                          caption: nil))
        }
        let me = lbRows.first(where: \.isMe)
        let list = SocListContent(kind: .streak, items: items, myRank: me?.rank ?? 0, total: lbRows.count, computedAt: i.now)
        return SocStreakSnap(day: day, list: list, prizes: prizes, endsAt: endsAt, myRank: me?.rank ?? 0, myScore: me?.value ?? 0,
                             computedAt: i.now)
    }

    /// The running (or the last ended) Rocket Race. The rivals are exactly the lanes C3 judges the race by (the ◆
    /// `rocketRace` call: the world's hold rule, no rubber band on the player's wins), the player's lane is C3's progress; a
    /// tie ranks behind the rival (C3 `rocketRank`). An ended race is C3's persisted `lastRun` (its join time, window and the
    /// player's final lane) drawn at its end moment (`lastEndedAt`), so a relaunch shows the same final lanes. `memo` is
    /// ignored (C3 persists the ended run now; the parameter stays so the lab / test call sites compile unchanged).
    static func rocket(_ i: SocInputs, memo _: SocRunMemo? = nil) -> (SocRocketSnap?, SocRunMemo?) {
        let rs = i.state.events.rocket
        var run: SocRunMemo
        var result = "none"
        var endedAt: SocialTime?
        if let a = rs.active {
            run = SocRunMemo(index: a.instance.index, stage: a.stage, joinedAt: a.joinedAt, end: a.instance.end, progress: a.progress)
        } else if let last = rs.lastResult, let e = rs.lastRun, e.instance.index == rs.raceCounter {
            run = SocRunMemo(index: e.instance.index, stage: e.stage, joinedAt: e.joinedAt, end: e.instance.end, progress: e.progress)
            result = last.rawValue
            endedAt = rs.lastEndedAt
            if last == .won { run.progress = i.rules.events.rocketRace.levels(stage: e.stage) }
        } else {
            return (nil, nil)
        }
        let goal = i.rules.events.rocketRace.levels(stage: run.stage)
        // FIX-A2 (CORE-2 / INTEG review): an ended race is drawn at C3's `lastEndedAt` alone (C3 keeps it within the race's
        // window, after its join). `min(now, …)` drew a race ended by a clock rebase at the repaired clock's `now`, BEFORE its
        // join (no lanes); in normal play `lastEndedAt` ≤ now, so nothing else changes. A running race: now, capped at its end.
        var at = endedAt ?? SocialTime(seconds: min(i.now.seconds, run.end.seconds))
        if result == "lost" {
            // the lanes as they stood when the first rival finished (later arrivals are not part of the result, 183)
            let b = i.world.rocketBoard(raceId: run.index, stage: run.stage, joinedAt: run.joinedAt, secondsPerWin: 120, userWins: [],
                                        me: i.me, at: at)
            if b.result == "lose" { at = SocialTime(seconds: min(at.seconds, b.resultAt.seconds)) }
        }
        let inst = EventInstance(event: Events.rocketInstanceID(stage: run.stage), index: run.index, start: run.joinedAt, end: run.end)
        let rivals = i.world.rocketRace(inst, joinedAt: run.joinedAt, at: at).filter { !$0.isMe }
        let myRank = 1 + rivals.filter { $0.score >= run.progress }.count
        var lanes: [SocRocketLane] = [SocRocketLane(player: SimPlayer(id: .max, name: i.me.name, country: i.me.country, avatar: i.me.avatar),
                                                    progress: min(run.progress, goal), rank: myRank, isMe: true)]
        // rivals keep the world's order (progress ↓, earlier reach first); ranks skip the player's slot
        var r = 0
        for lane in rivals {
            r += 1
            let rank = r >= myRank ? r + 1 : r
            lanes.append(SocRocketLane(player: lane.player, progress: min(lane.score, goal), rank: rank, isMe: false))
        }
        return (SocRocketSnap(raceId: run.index, stage: run.stage, goal: goal, lanes: lanes, result: result, endsAt: run.end,
                              computedAt: i.now), run)
    }

    /// The running (or the last ended) Sky Jump run: the survivor curve of the attempt, the portraits, the pool. An ended run
    /// is C3's persisted `lastRun` (join time, window, the player's final progress), its field drawn at its end moment
    /// (`lastEndedAt`), so a relaunch keeps the result. `memo` is ignored (see `rocket`).
    static func sky(_ i: SocInputs, memo _: SocRunMemo? = nil) -> (SocSkySnap?, SocRunMemo?) {
        let ss = i.state.events.sky
        let ev = i.rules.events.skyJump
        var run: SocRunMemo
        var result = "none"
        var endedAt: SocialTime?
        if let a = ss.active {
            run = SocRunMemo(index: a.instance.index, stage: a.stage, joinedAt: a.joinedAt, end: a.instance.end, progress: a.progress)
        } else if let last = ss.lastResult, let e = ss.lastRun, e.instance.index == ss.attemptCounter {
            run = SocRunMemo(index: e.instance.index, stage: e.stage, joinedAt: e.joinedAt, end: e.instance.end, progress: e.progress)
            result = last.rawValue
            endedAt = ss.lastEndedAt
            if last == .won { run.progress = ev.levels(stage: e.stage) }
        } else if ss.lastResult == .won, let c = i.state.events.claims.last(where: { $0.kind == .skyJumpShare }) {
            // a save from before C3 kept the ended run: the attempt from the share claim, the stage it paid for
            let stage = ss.nextStage > 1 ? ss.nextStage - 1 : ev.stages
            run = SocRunMemo(index: c.index, stage: stage, joinedAt: SocialTime(seconds: c.at.seconds - 3600), end: c.at,
                             progress: ev.levels(stage: stage))
            result = "won"
        } else {
            return (nil, nil)
        }
        let curve = i.world.skyJumpCurve(attemptId: run.index, stage: run.stage)
        let goal = curve.N
        let sjRun = SkyJumpRun(instance: EventInstance(event: .skyJump, index: run.index, start: run.joinedAt, end: run.end),
                               joinedAt: run.joinedAt, stage: run.stage, progress: min(run.progress, goal))
        let field = i.world.skyJump(sjRun, at: endedAt ?? i.now)             // FIX-A2: an ended run at `lastEndedAt` (see `rocket`)
        let pool = ev.pool(stage: run.stage)
        let winners = max(1, curve.alive[goal])
        return (SocSkySnap(attemptId: run.index, stage: run.stage, goal: goal, progress: min(run.progress, goal), alive: curve.alive,
                           pool: pool, share: pool / winners, shown: field.shown, endsAt: run.end, result: result,
                           computedAt: i.now), run)
    }
}

extension SocCompute.Result {
    /// A short name for probe logs.
    var name: String {
        switch self {
        case .list(let c): return "\(c.kind)"
        case .weekly: return "weekly"
        case .streak: return "streak"
        case .rocket: return "rocket"
        case .sky: return "sky"
        }
    }
}

/// SOC2's first-open probe: S1's FrameProbe line (same format: frames, max, frames > 20 ms over 1.5 s) plus WHEN each slow
/// frame ended (offset from the open) and SOC2's main-thread work of that window (publishes, state applies), so a
/// first-presentation stall can be traced to its cause instead of guessed at.
@MainActor final class SocOpenProbe: NSObject {
    private static var marks: [(CFTimeInterval, String)] = []
    /// Every probe's lines in order (SocOpenBench writes them out).
    static var results: [String] = []
    /// A SOC2 main-thread event (kept: the last 64).
    static func mark(_ what: String) {
        marks.append((CACurrentMediaTime(), what))
        if marks.count > 64 { marks.removeFirst(marks.count - 64) }
    }

    private let label: String
    private var link: CADisplayLink?
    private var start: CFTimeInterval = 0
    private var last: CFTimeInterval = 0
    private var frames: [(end: CFTimeInterval, ms: Double)] = []

    init(_ label: String) { self.label = label }

    func begin() {
        start = CACurrentMediaTime()
        let l = CADisplayLink(target: self, selector: #selector(tick(_:)))
        l.add(to: .main, forMode: .common)
        link = l
    }

    @objc private func tick(_ l: CADisplayLink) {
        if last > 0 { frames.append((l.timestamp, (l.timestamp - last) * 1000)) }
        last = l.timestamp
    }

    func end() {
        link?.invalidate(); link = nil
        let slow = frames.filter { $0.ms > 20 }
        let line = "\(label) frames \(frames.count) max \(String(format: "%.1f", frames.map(\.ms).max() ?? 0)) ms over20 \(slow.count)"
        Log.mark("perf", line)
        SocOpenProbe.results.append(line)
        guard !slow.isEmpty else { return }
        let t0 = start
        func at(_ t: CFTimeInterval) -> String { String(format: "%+.3f s", t - t0) }
        let s = slow.map { String(format: "%.1f ms ending ", $0.ms) + at($0.end) }.joined(separator: ", ")
        let m = SocOpenProbe.marks.filter { $0.0 >= t0 - 0.5 }.map { "\($0.1) at \(at($0.0))" }.joined(separator: "; ")
        let detail = "\(label) opened at \(String(format: "%.3f", t0)) · slow: \(s) · SOC2 main: \(m.isEmpty ? "none" : m)"
        Log.mark("perf", detail)
        SocOpenProbe.results.append("  " + detail)
    }
}
