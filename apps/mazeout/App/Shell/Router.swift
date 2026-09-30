import SwiftUI
import PathCore

// SHELL S1 (SPEC-architecture §6.1, §6.2, §9.1–§9.3). Full-screen states, no NavigationStack. AppModel.boot() (WP0 → G1)
// runs the boot behind Loading and calls `go(first)`; the router owns every transition after that, hosts the level through
// GAME's `LevelHosting` (GameEntry.makeLevel), presents `-pc.go settings` / `-pc.popup …` over the first screen, marks capture
// readiness, and prints the §9.3 marks EXACTLY:
//   [PC][router] go <screen>            (level_go: "go level(L<n>)")
//   [PC][router] level(L<n>) visible    (level_visible)
//   [PC][router] home visible           (home_visible)
//   [PC][launch] <screen> fully visible (first_screen: the first screen after Loading)
// First-run routing (§6.2, VERIFIED tutorials §1/§4): while `homeSeen == false` the screen after a win is the next level until
// `game.json ftue.chainUntilLevel` (7); then the first home. A loss before the first home retries. The router marks
// `homeSeen` when a home is first visible (the flag means exactly that).

@MainActor @Observable final class Router: Routing {
    /// The logical screen (the target of the latest transition).
    private(set) var screen: Screen = .loading
    /// What is drawn, bottom → top.
    private(set) var layers: [ScreenLayer] = [ScreenLayer(id: 0, screen: .loading, opacity: 1)]
    /// The running Play (one session) while a level is up.
    @ObservationIgnored private(set) var levelHost: (any LevelHosting)?
    @ObservationIgnored private(set) var levelView: AnyView?
    /// True once the first screen after Loading is fully visible.
    private(set) var firstScreenShown = false

    let ctx: AppContext
    let timing: ShellTiming
    @ObservationIgnored weak var app: AppModel?
    @ObservationIgnored private var nextLayerID = 1
    @ObservationIgnored private var queue: Task<Void, Never>?
    @ObservationIgnored private var busy = false

    /// True two frames after the Loading screen first presented (the popup pre-render starts then, behind it).
    private(set) var loadingPresented = false

    /// Set by a cut to home that follows a `HomeScene.requestRefill()` (the capsule machine's pile refills on that arrival).
    private(set) var homeRefill = 0
    /// More than one layer is visible (the Loading cross-fade).
    var isTransitioning: Bool { layers.filter { $0.opacity > 0 }.count > 1 }

    init(_ ctx: AppContext) {
        self.ctx = ctx
        self.timing = ShellTiming(ui: ctx.tuning.ui)
        ShellScreens.loading?.startArt()                    // the loading component's art, decoded off-main
        HomeArtPreload.start()                              // FIX-2 A: home's art decoded off-main before its slices
    }

    /// Called by the Loading screen's first appearance.
    func loadingAppeared() {
        guard !loadingPresented else { return }
        Task { @MainActor in
            await FrameWaiter.frames(2)
            Log.mark("launch", "loading visible")
            loadingPresented = true
        }
    }

    func attach(_ app: AppModel) {
        self.app = app
        ShellScreens.home?.attach(app.store)               // FIX-A1: home's view of the player state (parked home: frozen)
    }

    // MARK: Routing

    func go(_ target: Screen) {
        Log.mark("router", "go \(target.logName)")
        // FIX-2 A (A3-o0): back into a PARKED home whose copy of the player state is stale (a win's coins and level, a loss's
        // lives): the copy is refreshed first, on a frame where home is still hidden, and the cut follows one frame later —
        // so the cut's frame shows home instead of re-rendering its changed parts (the arrival after a win cost 33-39 ms,
        // almost all of it our own work). The answered popup stays drawn until the cut (A3's hand-over, the queued path).
        let prep = target.isHome && !screen.isHome && screen != .loading && layers.contains(where: { $0.screen.isHome })
            && (ShellScreens.home?.arrivalStale ?? false)
        // FIX-2 A-R: an event page whose art was released (RootView `EventArtPolicy`) decodes it off the main thread first —
        // only then; every other page opens at once (FIX-2 A's hidden draw before a first open delayed it by 80-90 ms)
        var decodeFirst: EventScreen?
        if case .event(let e) = target, screen != .loading, EventArtPolicy.needsDecode(e) { decodeFirst = e }
        // A hard cut with nothing queued runs NOW (Play → first board frame ≤ 50 ms, no await: §8.5, §10.2).
        if !prep, decodeFirst == nil, !busy, queue == nil, screen != .loading, !target.sameKind(screen) || target.isLevel,
           cutsHard(to: target) {
            perform(hardCutTo: target)
            return
        }
        let previous = queue
        let host = app?.popups as? PopupHost
        host?.handOverFollowsTransition()                   // A3: an answered popup stays drawn until this transition is done
        queue = Task { @MainActor [weak self] in
            await previous?.value
            guard let self else { host?.transitionDone(); return }
            self.busy = true
            if prep, ShellScreens.home?.prepareArrival() == true {
                Log.mark("router", "home copy refreshed a frame before the cut")
                await FrameWaiter.frames(1)
            }
            if let e = decodeFirst { await EventArtPolicy.decode(e) }
            await self.perform(target)
            self.busy = false
            self.queue = nil
            host?.transitionDone()
        }
    }

    /// Awaits every queued transition (tests, debug flows).
    func settle() async { await queue?.value }

    // MARK: first-run routing (§6.2)

    /// The screen after a won Play: the FTUE chain's next level while home was never seen and the next level is below
    /// `ftue.chainUntilLevel`, else home (the first home carries the FTUE payout). GAME calls it after the win panel's
    /// Continue, with `PlayerState.level` already advanced to the next level.
    func screenAfterWin(_ summary: WinSummary) -> Screen {
        guard let app else { return .home(.afterWin(summary), tab: .home) }
        let s = app.store.state
        if !s.homeSeen {
            if s.level < app.tuning.game.ftueChainUntilLevel { return .level(app.levelLaunch(for: s.level)) }
            return .home(.firstHome(summary), tab: .home)
        }
        return .home(.afterWin(summary), tab: .home)
    }

    /// The screen after a lost Play: Try Again = the same board (VERIFIED levels L32); X = home, except before the first
    /// home, where a loss retries (§6.2).
    func screenAfterLoss(_ launch: LevelLaunch, tryAgain: Bool) -> Screen {
        let retry = LevelLaunch(session: launch.session, levels: launch.levels, isRetry: true, firstStage: launch.firstStage)
        if tryAgain { return .level(retry) }
        if let app, !app.store.state.homeSeen { return .level(retry) }
        return .home(.afterLoss, tab: .home)
    }

    // MARK: transitions

    private func cutsHard(to target: Screen) -> Bool {
        switch target {
        case .loading: return false
        default: return true
        }
    }

    private func perform(_ target: Screen) async {
        let from = screen
        if from == .loading {
            await crossFadeOutOfLoading(to: target)
            return
        }
        if target.sameKind(from), !target.isLevel {
            // Home tab switch / entry change: swap in place (HomeView keeps its identity).
            screen = target
            if let i = layers.lastIndex(where: { $0.screen.sameKind(target) }) { layers[i].screen = target }
            if let tab = target.homeTab { ShellScreens.home?.slideTab(to: tab, ui: timing.ui) }   // A2: the tab push-slide
            await visible(target)
            return
        }
        perform(hardCutTo: target)
        await FrameWaiter.frames(1)
    }

    /// Loading → the first screen: mount it invisibly on top, let it render, cross-fade, drop Loading.
    private func crossFadeOutOfLoading(to target: Screen) async {
        // FIX-A1: the staged first-presentation warm-up (RootView `PopupPrewarm`) finishes under Loading first — never past
        // `loading.capSeconds` from launch (the boot's own cap): Loading's minimum is untouched, it only ends when both are done
        if let app { await ShellPrewarm.wait(until: app.launchUptime + app.tuning.ui.loadingCapSeconds) }
        // FIX-A1: home's hidden Shop / Leaderboard pages are built with home, under the opaque Loading view, instead of on
        // an idle home frame ~1.8 s after the first arrival (34-65 ms, build/fixa1/runs/base0-loop-1). Not in UI tests or
        // captures (HomeTabsPremount's rule: they open the pages themselves).
        if target.isLevel || target.isHome, let app, !app.args.quietUI { ShellScreens.home?.mountTabs() }
        // FIX-A1: when the first screen is a level (the FTUE's first board), home is built here, hidden, a frame BEFORE the
        // level starts (its cut K and intro stay exactly as they were): the first home arrival then shows a built screen
        // instead of building it (a 165 ms frame at the first home, build/feel)
        if target.isLevel, !layers.contains(where: { $0.screen.isHome }) {
            mountHiddenHome()
            await FrameWaiter.frames(1)
        }
        ShellScreens.home?.finishBuild()                   // FIX-2 A: a slice the Loading cap cut off is built now
        guard prepare(target) else {
            Log.error("router", "\(target.logName) refused to start from Loading: going home")
            await crossFadeOutOfLoading(to: .home(.normal, tab: .home))
            return
        }
        let id: Int
        if case .home(let entry, _) = target, let i = layers.firstIndex(where: { $0.screen.isHome }) {
            // a home already built hidden (the first level was refused): it fades in, no second home
            ShellScreens.home?.prepareArrival()            // FIX-2 A: the parked copy takes the boot's writes first
            layers[i].screen = target
            layers[i].arrival = nextLayerID
            nextLayerID += 1
            id = layers[i].id
            ShellScreens.home?.arrive(entry, arrival: layers[i].arrival)
        } else {
            id = mount(target, opacity: 0)
            if case .home(let entry, _) = target { ShellScreens.home?.arrive(entry, arrival: id) }
        }
        if let tab = target.homeTab { ShellScreens.home?.jumpTab(to: tab) }        // A2: a cut into home shows its tab at once
        screen = target
        await FrameWaiter.frames(2)                        // the first screen builds under the opaque Loading view
        let duration = timing.fromLoading(to: target)
        let start = ProcessInfo.processInfo.systemUptime
        if duration > 0 {
            await withCheckedContinuation { (cont: CheckedContinuation<Void, Never>) in
                withAnimation(.linear(duration: duration), completionCriteria: .logicallyComplete) {
                    if let i = layers.firstIndex(where: { $0.id == id }) { layers[i].opacity = 1 }
                } completion: { cont.resume() }
            }
        } else if let i = layers.firstIndex(where: { $0.id == id }) {
            layers[i].opacity = 1
        }
        layers.removeAll { $0.id != id && !($0.screen.isHome && $0.opacity == 0) }       // Loading goes; a parked home stays
        Log.mark("router", "cross-fade loading → \(target.logName) \(String(format: "%.3f", ProcessInfo.processInfo.systemUptime - start)) s (spec \(duration))")
        await FrameWaiter.frames(1)
        ShellScreens.loading?.releaseArt()                  // FIX-2 A (V3-09): Loading never shows again this launch
        Log.mark("launch", "\(target.logName) fully visible")
        Log.mark("raster", "\(RasterCache.misses) chrome rasters rendered before the first screen; later renders are logged")
        RasterCache.logMisses = true
        GameTextRaster.logMisses = ctx.args.raw["pc.frameWatch"] != nil      // FIX-2 A: measurement runs only
        if ctx.args.raw["pc.artDump"] != nil {                               // FIX-2 A (V3-09): what the decoded art holds
            Task { @MainActor in
                for _ in 0..<6 {
                    try? await Task.sleep(nanoseconds: 10_000_000_000)
                    let top = ArtStore.largest(24).map { String(format: "%@ %.1f", ($0.0 as NSString).lastPathComponent, Double($0.1) / 1_048_576) }
                    Log.mark("memory", String(format: "art %.1f MB (glyphs %.1f MB, %d, evicted %d) top: ", Double(ArtStore.bytes) / 1_048_576,
                                              Double(GameTextRaster.bytes) / 1_048_576, GameTextRaster.count,
                                              GameTextRaster.cache.evictions) + top.joined(separator: ", "))
                }
            }
        }
        await visible(target)
        firstScreenShown = true
        await afterFirstScreen()
    }

    /// A one-frame cut: the new screen replaces everything (home is parked under it, FIX-A1: `cutLayers`). A level leaving
    /// is torn down FIRST (one board engine for the whole app: the next level must load on a clean board).
    private func perform(hardCutTo target: Screen) {
        let probe = CutProbe.start(target, enabled: ctx.args.raw["pc.frameWatch"] != nil)
        let leavingLevel = screen.isLevel
        if screen.isHome, !target.isHome {
            ShellScreens.home?.cancelPayout()
            ShellScreens.home?.park()
        }
        if leavingLevel, let old = levelHost {
            Log.mark("router", "teardown \(old.launch.levels.first.map { "L\($0)" } ?? "?")")
            old.teardown()
            levelHost = nil
            if !parkLevel { levelView = nil }          // FIX-2 A (V3-05): parked, the torn-down Play's screen stays mounted
        }
        probe?.mark("teardown")
        var target = target
        if target.isLevel, !prepare(target) {
            // Refused (no lives: GAME has already put its popup up). From home: stay. From a torn-down level: home.
            Log.mark("router", "\(target.logName) refused to start: \(leavingLevel ? "home" : "staying on \(screen.logName)")")
            guard leavingLevel else { ShellScreens.home?.resume(); return }
            target = .home(.afterLoss, tab: .home)
        }
        probe?.mark("prepare")
        var t = Transaction(); t.disablesAnimations = true
        withTransaction(t) {
            (app?.popups as? PopupHost)?.endBridge("cut to \(target.logName)")   // A3: an answered popup goes on the new screen's frame
            layers = cutLayers(to: target)
            if case .home(let entry, let tab) = target, let h = layers.first(where: { $0.screen.isHome }) {
                ShellScreens.home?.arrive(entry, arrival: h.arrival)
                ShellScreens.home?.jumpTab(to: tab)                                 // A2: a cut into home shows its tab at once
            }
            screen = target
        }
        probe?.finishAfterCommit()
        Task { @MainActor [weak self] in
            await FrameWaiter.frames(1)
            await self?.visible(target)
        }
    }

    /// Builds what `target` needs before it is shown: a level starts its session and loads its board synchronously.
    private func prepare(_ target: Screen) -> Bool {
        guard case .level(let launch) = target, let app else { return true }
        let host = GameEntry.makeLevel(launch, app: app)
        guard host.start() else { return false }
        levelHost = host
        levelView = host.makeView()
        // FIX-2 A: the level home shows after a win, its tag read off the main thread now (not in the arrival frame)
        if let last = launch.levels.last { ShellScreens.home?.prefetchLevel(last + 1, args: app.args) }
        return true
    }

    @discardableResult
    private func mount(_ target: Screen, opacity: Double) -> Int {
        let layer = ScreenLayer(id: nextLayerID, screen: target, opacity: opacity, arrival: nextLayerID)
        nextLayerID += 1
        layers.append(layer)
        return layer.id
    }

    /// FIX-A1 (SPEC-architecture §10.2 "level start: 0 frames > 20 ms from Play", "frames in the shell"). Home is built
    /// ONCE and then PARKED — kept mounted, hidden (opacity 0: Core Animation draws nothing of it; no hit testing, and
    /// out of the accessibility tree: `accessibilityShown`) — under whatever screen replaces it; a cut back shows it again
    /// with a new `arrival` (HomeView's arrival work runs on that value, `HomeLive.arrive`). A level → level cut (Try
    /// Again, the FTUE chain) keeps the level layer's identity: the next Play's screen updates it in place and the board
    /// view never leaves its host. Measured before (Release sim, build/fixa1/runs/base0-*): every Play 33-74 ms (+ a 20-29 ms
    /// frame) — home torn down and the level built in one frame; every home arrival 34-165 ms and its hidden Shop /
    /// Leaderboard pages rebuilt 34-53 ms ~1.8 s later. A parked home does no work in a level: its views read the player
    /// state through `HomeLive` (a copy while parked), its countdowns are frozen, and its hidden Leaderboard page is not
    /// "on screen" for SOC2 (SocialModel.isOnScreen). Keeping the level screen parked across home visits too was measured
    /// and dropped: same Play cost (median 33 ms either way, build/fixa1/runs/xab.txt), so it is rebuilt per Play as before.
    /// FIX-2 A (V3-05): the level screen is PARKED between Plays like home — its layer stays mounted, hidden (opacity 0: nothing
    /// drawn, no input, out of the accessibility tree), holding the last Play's (torn-down) GameScreen; the next Play updates
    /// that same view in place (a new GameController, the app-lifetime board and HUD model) instead of building the whole level
    /// screen — board host, HUD, tutorial layer — inside the Play cut's commit (15-23 ms of our main thread per Play on the
    /// Release simulator, build/p/FIX2/A/tp/v2-tp1). FIX-A1 measured this once as no gain, when the Play cut also re-rendered
    /// home's hidden Shop / Leaderboard tabs and walked the HUD's alignment guides; both are gone now. `-pc.parkLevel 0` = the
    /// old per-Play rebuild (the A/B).
    private var parkLevel: Bool { ctx.args.raw["pc.parkLevel"] != "0" }

    private func cutLayers(to target: Screen) -> [ScreenLayer] {
        let arrival = nextLayerID
        nextLayerID += 1
        var out: [ScreenLayer] = []
        var placed = false
        let keepLevel = target.isLevel || (parkLevel && levelView != nil)
        for var l in layers where l.screen.isHome || (l.screen.isLevel && keepLevel) {
            if target.isHome, l.screen.isHome {
                if ShellScreens.home?.takeRefill() == true { homeRefill = arrival }
                l.screen = target; l.opacity = 1; l.arrival = arrival; placed = true
            } else if target.isLevel, l.screen.isLevel {
                l.screen = target; l.opacity = 1; l.arrival = arrival; placed = true
            } else {
                l.opacity = 0
            }
            out.append(l)
        }
        if !placed {
            if target.isHome, ShellScreens.home?.takeRefill() == true { homeRefill = arrival }
            out.append(ScreenLayer(id: arrival, screen: target, opacity: 1, arrival: arrival))
        }
        return out
    }

    /// FIX-2 A (A4-o1 / V3-08): home is built BEHIND Loading as the warm-up starts — mounted hidden and parked (arrival 0),
    /// then one `HomeBuild` slice per presented frame — so the cut out of Loading shows a built home instead of building all of
    /// it in one frame (156-185 ms main thread on the Release simulator, 339-433 ms before A4). Only for a launch whose first
    /// screen needs home (home, a level — the FTUE's first board parks home under it anyway — or a home tab); a debug host or a
    /// page (`-pc.go profile | event | settings | lab`) builds nothing extra.
    func buildHomeBehindLoading() async {
        guard screen == .loading, let app, !layers.contains(where: { $0.screen.isHome }) else { return }
        switch app.args.go {
        case nil, .home?, .level?, .shop?, .leaderboard?: break
        default: return
        }
        let t0 = ProcessInfo.processInfo.systemUptime
        ShellScreens.home?.beginBuild()
        mountHiddenHome()
        if !app.args.quietUI { ShellScreens.home?.mountTabs() }    // the Shop / Leaderboard tabs are two of the slices
        var slices = 0
        while ShellScreens.home?.isBuilding == true, screen == .loading {
            await FrameWaiter.frames(1)
            ShellScreens.home?.buildStep()
            slices += 1
        }
        await FrameWaiter.frames(1)
        ShellScreens.home?.finishBuild()
        Log.mark("warmup", String(format: "home built behind Loading: %d slices over %.3f s", slices,
                                  ProcessInfo.processInfo.systemUptime - t0))
    }

    /// Home, built hidden under Loading (not arrived: arrival 0) when the first screen is a level.
    private func mountHiddenHome() {
        guard !layers.contains(where: { $0.screen.isHome }) else { return }
        ShellScreens.home?.park()
        layers.insert(ScreenLayer(id: nextLayerID, screen: .home(.normal, tab: .home), opacity: 0, arrival: 0), at: 0)
        nextLayerID += 1
    }

    private func visible(_ target: Screen) async {
        switch target {
        case .level: Log.mark("router", "\(target.logName) visible")
        case .home:
            Log.mark("router", "home visible")
            if let app, !app.store.state.homeSeen { app.store.mutateAndSave { $0.homeSeen = true } }
            // FIX-2 A (V3-09): once home has been idle, the art of events not openable now is released (and released art of
            // events openable again is decoded off the main thread)
            if let app, !app.args.quietUI {
                Task { @MainActor [weak self] in
                    try? await Task.sleep(nanoseconds: 2_500_000_000)
                    guard let self, self.screen.isHome else { return }
                    EventArtPolicy.apply(app)
                }
            }
        default: Log.mark("router", "\(target.logName) visible")
        }
    }

    // MARK: after the first screen: -pc.go settings, -pc.popup, capture readiness (§9.1, §9.2)

    private func afterFirstScreen() async {
        guard let app else { return }
        if case .settings? = app.args.go {
            Task { @MainActor in _ = await app.popups.present(Popup<PopupResult>.settings) }
        }
        if let p = app.args.popup {
            DebugPopupLauncher.present(p, app: app)
        }
        if let w = app.args.raw["pc.popupWarm"], !w.isEmpty { PopupWarm.debugHold(w, app: app) }   // FIX-2 A-R (UI test)
        #if DEBUG || PC_MEASURE
        if let n = app.args.raw["pc.tabLoop"].flatMap(Int.init), n > 0 { DebugTabLoop.run(n, app: app, router: self) }   // A2
        if let plan = app.args.raw["pc.glitchRun"], !plan.isEmpty { GlitchRun.start(plan, app: app, router: self) }   // A3
        #else
        // F3-A (ruling 52(a)): the store build has no measurement harness; a run that asks for it must not pass silently
        for flag in ["pc.tabLoop", "pc.glitchRun"] where app.args.raw[flag] != nil {
            Log.error("glitch", "-\(flag): not in this build (Release); measurement runs use the Measure configuration")
        }
        #endif
        await CaptureReady.markWhenReady(app: app, router: self)
    }
}

extension ShellEntry {
    static func makeRouter(_ ctx: AppContext) -> any Routing { Router(ctx) }
}

// MARK: - `-pc.popup <id>[:variant]` (§9.1)

/// Presents one popup over the first screen. S1 builds pause, quitLevel and settings; every other id is presented through
/// its typed request as soon as its panel exists (S2 / S3 / SOC2 extend this switch), and is refused with a log until then.
@MainActor enum DebugPopupLauncher {
    static func present(_ p: LaunchArgs.PopupArg, app: AppModel) {
        let popups = app.popups
        Log.mark("popup", "-pc.popup \(p.id)\(p.variant.map { ":" + $0 } ?? "")")
        Task { @MainActor in
            // S1-private `-pc.popupDelay S`: present S seconds after the first screen (a warm presentation, like a tap)
            var probe: FrameProbe?
            if let d = app.args.raw["pc.popupDelay"].flatMap(Double.init), d > 0 {
                try? await Task.sleep(nanoseconds: UInt64(max(0, d - 0.3) * 1_000_000_000))
                probe = FrameProbe("popup \(p.id) open")
                probe?.start()
                try? await Task.sleep(nanoseconds: 300_000_000)
                Task { @MainActor in
                    try? await Task.sleep(nanoseconds: 1_000_000_000)
                    probe?.stop()
                }
            }
            // S1-private `-pc.popupLoop N`: open and close the popup N times (profiling the open; logs each open's worst frame)
            if let n = app.args.raw["pc.popupLoop"].flatMap(Int.init), n > 0, let host = popups as? PopupHost {
                for i in 0..<n {
                    let probe = FrameProbe("popup \(p.id) loop \(i)")
                    probe.start()
                    Task { @MainActor in
                        switch p.id {
                        case PopupID.settings.rawValue: _ = await host.present(Popup<PopupResult>.settings)
                        case PopupID.quitLevel.rawValue: _ = await host.present(Popup<PopupResult>.quitLevel)
                        default: _ = await host.present(Popup<PopupResult>.pause)
                        }
                    }
                    try? await Task.sleep(nanoseconds: 400_000_000)
                    host.dismissAll()
                    try? await Task.sleep(nanoseconds: 200_000_000)
                    probe.stop()
                }
                return
            }
            // A2 (measurement only): `-pc.popupAnswer primary|close` answers the top popup `-pc.popupAnswerAfter S` (1.5 s) after
            // it shows, as its button would — the band exits (rise on close, fall on Quit) can be recorded without a touch
            if let a = app.args.raw["pc.popupAnswer"], let host = popups as? PopupHost {
                let after = app.args.raw["pc.popupAnswerAfter"].flatMap(Double.init) ?? 1.5
                Task { @MainActor in
                    for _ in 0..<300 where host.stack.isEmpty { try? await Task.sleep(nanoseconds: 16_000_000) }
                    try? await Task.sleep(nanoseconds: UInt64(after * 1_000_000_000))
                    guard let top = host.stack.last else { return }
                    Log.mark("popup", "-pc.popupAnswer \(a) → \(top.request.id.rawValue) #\(top.id)")
                    host.answer(top.id, a == "primary" ? PopupResult.primary : PopupResult.close)
                }
            }
            switch p.id {
            case PopupID.pause.rawValue:
                let r = await popups.present(Popup<PopupResult>.pause)
                Log.mark("popup", "pause → \(r)")
            case PopupID.quitLevel.rawValue:
                let r = await popups.present(Popup<PopupResult>.quitLevel)
                Log.mark("popup", "quitLevel → \(r)")
            case PopupID.settings.rawValue:
                let r = await popups.present(Popup<PopupResult>.settings)
                Log.mark("popup", "settings → \(r)")
            default:
                // every other id: the component that registered it (`DebugPopups`: the offline pages `page.*` are the settings
                // component's; the fail chain, win, unlock and claim S2's; the S3 popups and the Shop; the event popups)
                if await DebugPopups.present(p, app: app) { return }
                Log.error("popup", "-pc.popup \(p.id): no panel built yet (S1 builds pause, quitLevel, settings, page.*)")
            }
        }
    }
}

// MARK: - `-pc.tabLoop N` (A2 FEEL-P measurement: N home tab slides, each under a FrameProbe)
// F3-A (ruling 52(a)): Debug + Measure only, like GlitchRun (which drives it for `-pc.glitchRun tabs:N`).

#if DEBUG || PC_MEASURE

/// Runs N tab changes through the router, exactly as the nav's tabs do, cycling 1- and 2-page slides (home → shop → leaderboard
/// → home → leaderboard → shop → home …), `-pc.tabLoopGap S` apart (default 1.2 s; `-pc.tabLoopDelay S` before the first,
/// default 1.5 s). Logs `[PC][perf] tab slide k a → b frames n max ms over20 k` over the slide + 0.2 s, and the tap time
/// `[PC][home] tabLoop k a → b at <uptime>` (the recordings' anchor). Measurement only: nothing runs without the flag.
@MainActor enum DebugTabLoop {
    static func run(_ n: Int, app: AppModel, router: Router) {
        let order: [HomeTab] = [.shop, .leaderboard, .home, .leaderboard, .shop, .home]
        let gap = app.args.raw["pc.tabLoopGap"].flatMap(Double.init) ?? 1.2
        let delay = app.args.raw["pc.tabLoopDelay"].flatMap(Double.init) ?? 1.5
        let slide = app.tuning.ui.tabSlideDuration
        ShellScreens.home?.probeTabCommits()
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            // the home queue's pages (daily offers, the Streak board) are answered first: the slides run on a bare home
            var quiet = 0.0
            while quiet < 2.0 {
                if app.popups.isPresenting { (app.popups as? PopupHost)?.dismissAll(); quiet = 0 } else { quiet += 0.25 }
                try? await Task.sleep(nanoseconds: 250_000_000)
            }
            var over = 0, worst = 0.0
            for k in 0..<n {
                guard let from = router.screen.homeTab else { Log.error("home", "tabLoop: home is not up"); return }
                let to = order[k % order.count] == from ? order[(k + 1) % order.count] : order[k % order.count]
                let probe = FrameProbe("tab slide \(k) \(from.rawValue) → \(to.rawValue)")
                probe.start()
                Log.mark("home", String(format: "tabLoop %d %@ → %@ at %.4f", k, from.rawValue, to.rawValue, CACurrentMediaTime()))
                if let cue = app.tuning.audio.cue("uiButton") { app.audio.play(cue, gain: Float(app.tuning.audio.gain(cue))) }
                if let h = GameButtonFeedback.haptic(app) { app.haptics.play(h) }
                router.go(.home(.normal, tab: to))
                try? await Task.sleep(nanoseconds: UInt64((slide + 0.2) * 1_000_000_000))
                let r = probe.stopResult()
                over += r.over20; worst = max(worst, r.max)
                try? await Task.sleep(nanoseconds: UInt64(max(0.05, gap - slide - 0.2) * 1_000_000_000))
            }
            Log.mark("perf", String(format: "tabLoop %d slides: frames over 20 ms %d, worst %.1f ms", n, over, worst))
        }
    }
}
#endif

// MARK: - capture readiness (§9.2)

@MainActor @Observable final class CaptureReadyState {
    var screen: String?
}

@MainActor enum CaptureReady {
    static let state = CaptureReadyState()

    /// Waits until the screen is ready (fonts registered, the first screen's art decoded by its onAppear, the board settled
    /// in a level, the requested `-pc.freezeAt` reached, the popup presented), then 2 more frames, then publishes
    /// `capture.ready` and — in capture mode — writes Documents/capture-ready.json.
    static func markWhenReady(app: AppModel, router: Router) async {
        var waited = 0.0
        func tick() async { try? await Task.sleep(nanoseconds: 50_000_000); waited += 0.05 }
        if app.args.popup != nil { while app.popups.topID == nil && waited < 3 { await tick() } }
        if router.screen.isLevel { while !(app.board?.isSettled ?? true) && waited < 12 { await tick() } }
        if app.args.freezeAt != nil { while app.clock.frozenAt == nil && waited < 15 { await tick() } }
        await FrameWaiter.frames(2)
        let name = router.screen.logName + (app.popups.topID.map { "+popup:\($0.rawValue)" } ?? "")
        mark(screen: name, app: app)
    }

    static func mark(screen: String, app: AppModel, file: String = "capture-ready.json") {
        state.screen = screen
        Log.mark("capture", "ready \(screen)")
        guard app.args.capture || file != "capture-ready.json" else { return }
        let lang = Bundle.main.preferredLocalizations.first ?? "en"
        let payload: [String: Any] = ["screen": screen, "t": ProcessInfo.processInfo.systemUptime, "lang": lang,
                                      "frozen": app.clock.isFrozen]
        guard let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first,
              let data = try? JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys]) else { return }
        try? data.write(to: docs.appendingPathComponent(file), options: .atomic)
    }
}

struct CaptureReadyMarker: View {
    var body: some View {
        if let s = CaptureReady.state.screen {
            Color.clear.frame(width: 1, height: 1)
                .accessibilityElement()
                .accessibilityIdentifier("capture.ready")
                .accessibilityValue(Text(verbatim: s))
                .allowsHitTesting(false)
        }
    }
}

/// FIX-A1 (measurement only, `-pc.frameWatch 1`): one hard cut's main-thread cost split into the router's steps and the
/// SwiftUI update + layout + Core Animation commit that follows in the same run-loop turn:
///     `[PC][perf] cut <screen> teardown <ms> prepare <ms> commit <ms> total <ms> footprint <MB> cpu <ms>` (A3: main-thread CPU)
@MainActor final class CutProbe {
    private let name: String
    private let t0 = CACurrentMediaTime()
    private let cpu0 = clock_gettime_nsec_np(CLOCK_THREAD_CPUTIME_ID)   // A3: the main thread's CPU time (load-independent)
    private var last: CFTimeInterval
    private var parts: [(String, Double)] = []

    private init(_ name: String) { self.name = name; last = t0 }

    static func start(_ target: Screen, enabled: Bool) -> CutProbe? { enabled ? CutProbe(target.logName) : nil }

    func mark(_ step: String) {
        let now = CACurrentMediaTime()
        parts.append((step, (now - last) * 1000))
        last = now
    }

    /// Logs once the run loop is about to sleep (after UIKit's layout and the CA commit, which run before it).
    func finishAfterCommit() {
        let obs = CFRunLoopObserverCreateWithHandler(nil, CFRunLoopActivity.beforeWaiting.rawValue, false, Int.max) { [self] o, _ in
            CFRunLoopRemoveObserver(CFRunLoopGetMain(), o, .commonModes)
            let now = CACurrentMediaTime()
            let steps = parts.map { "\($0.0) \(String(format: "%.1f", $0.1))" }.joined(separator: " ")
            Log.mark("perf", "cut \(name) \(steps) commit \(String(format: "%.1f", (now - last) * 1000)) total "
                     + String(format: "%.1f", (now - t0) * 1000) + String(format: " footprint %.0f MB", PerfMonitor.footprintMB())
                     + String(format: " cpu %.1f", Double(clock_gettime_nsec_np(CLOCK_THREAD_CPUTIME_ID) &- cpu0) / 1e6)
                     // FIX-2 A (V3-09 / V3-10): the decoded art and the glyph rasters held
                     + String(format: " art %.1f MB glyphs %.1f MB", Double(ArtStore.bytes) / 1_048_576,
                              Double(GameTextRaster.bytes) / 1_048_576))
        }
        CFRunLoopAddObserver(CFRunLoopGetMain(), obs, .commonModes)
    }
}
