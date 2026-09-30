import SwiftUI
import PathCore

// SHELL S1 (SPEC-architecture §6.1, §6.5 z-order, §9.2). The window's root, installed through `ShellEntry.makeRoot` (GameApp
// builds it once). Back → front: the router's screen layers (Loading / home / level / event / profile / lab), the FX host (CA
// layers), the popup host, the toasts, the capture-ready marker. It maps the 393 x 852 reference canvas to the live screen
// (ShellMetrics) and honours `.lab(<id>)` through `DebugScreens.make` (boardlab: BOARD, shelllab: SHELL, soundboard: AUDIO,
// sociallab: SOCIAL). While Loading is up it pre-renders every owner's popups and pages invisibly, one per frame (the SwiftUI
// first-presentation cost is paid behind Loading, §8.5 step 3; `PopupPrewarm`). The fixed light palette and the hidden
// status bar are GameApp's.

struct RootView: View {
    let app: AppModel
    let router: Router

    var body: some View {
        GeometryReader { proxy in
            let size = CGSize(width: proxy.size.width + proxy.safeAreaInsets.leading + proxy.safeAreaInsets.trailing,
                              height: proxy.size.height + proxy.safeAreaInsets.top + proxy.safeAreaInsets.bottom)
            let metrics = ShellMetrics(size: size, safeTop: proxy.safeAreaInsets.top, safeBottom: proxy.safeAreaInsets.bottom,
                                       popupUpscale: app.tuning.ui.popupUpscale)
            LayerStack {                                   // FIX-A1: was a ZStack(alignment: .topLeading); same placement
                LayerStack {
                    ForEach(router.layers.sorted { $0.id < $1.id }) { layer in
                        LayerView(app: app, router: router, layer: layer)
                            .opacity(layer.opacity)
                            .allowsHitTesting(layer.opacity > 0.5)
                            .accessibilityShown(layer.opacity >= 0.5)
                            .zIndex(Double(layer.id))
                    }
                }
                .frame(width: size.width, height: size.height)
                if router.screen == .loading && router.loadingPresented { PopupPrewarm(app: app) }
                PopupWarmLayer(app: app)                   // FIX-2 A (V3-14): a coming popup drawn once, invisibly
                if let fx = app.fx as? FXOverlay {
                    FXOverlayView(fx: fx).allowsHitTesting(false).frame(width: size.width, height: size.height).zIndex(1_000_000)
                }
                if let host = app.popups as? PopupHost { PopupLayer(host: host, app: app).zIndex(1_000_001) }
                if let toasts = app.toasts as? ToastCenter {
                    ToastLayer(center: toasts, tokens: app.tuning.ui.tokens, inLevel: router.screen.isLevel).zIndex(1_000_002)
                }
                CaptureReadyMarker().zIndex(1_000_003)
                if app.args.uitest {                                              // FIX-2 A-R (UI tests)
                    KeyboardWarmMarker().zIndex(1_000_004)
                    WarmProbe().frame(width: 2, height: 2).allowsHitTesting(false).zIndex(1_000_005)
                }
            }
            .frame(width: size.width, height: size.height, alignment: .topLeading)
            .environment(\.shellMetrics, metrics)
            .ignoresSafeArea()
        }
        .background(Color.black.ignoresSafeArea())
        .persistentSystemOverlays(.hidden)          // S3: the home indicator auto-hides like the original's (no bar in 202 / meta-012)
    }
}

extension View {
    /// FIX-A1: keeps or removes a whole subtree from accessibility (VoiceOver, XCUITest) — for a parked screen or a hidden
    /// tab page (opacity 0, still mounted). `accessibilityHidden(true)` on an ancestor does NOT hide descendants that carry
    /// their own accessibility modifiers (every button, every `.contain` screen root): a parked home stayed queryable
    /// under a level (`home.lives`, `home.play`, `nav.*` in the UI snapshot) and every XCUITest query walked it. Turning the
    /// `accessibilityEnabled` environment off for the subtree removes it (verified on the simulator's accessibility
    /// snapshot); shown, the inherited value is kept, so a hidden ancestor always wins.
    func accessibilityShown(_ shown: Bool) -> some View { modifier(AccessibilityShown(shown: shown)) }
}

private struct AccessibilityShown: ViewModifier {
    let shown: Bool
    @Environment(\.accessibilityEnabled) private var inherited
    func body(content: Content) -> some View {
        content.environment(\.accessibilityEnabled, shown ? inherited : false).accessibilityHidden(!shown)
    }
}

/// FIX-A1: the root's, the screen layers' and home's container: every child placed at the origin with the full size
/// proposed (exactly what the top-leading ZStacks did here), and nothing asked of a child's alignment or priority. A ZStack
/// asks every child for its explicit alignment and layout priority whenever its children change, and those queries walked
/// the whole (parked) home and level trees — 9-12 ms of every Play cut (Time Profiler, build/fixa1/trace/loop-v4.trace:
/// `_ZStackLayout.sizeThatFits` → `LayoutProxy.layoutPriority` → `explicitAlignment`).
struct LayerStack: Layout {
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        proposal.replacingUnspecifiedDimensions()
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let p = ProposedViewSize(bounds.size)
        for s in subviews { s.place(at: bounds.origin, anchor: .topLeading, proposal: p) }
    }

    // No alignment guides: the default implementation merges every subview's (a walk of each whole screen tree).
    func explicitAlignment(of guide: HorizontalAlignment, in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews,
                           cache: inout ()) -> CGFloat? { nil }
    func explicitAlignment(of guide: VerticalAlignment, in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews,
                           cache: inout ()) -> CGFloat? { nil }
}

/// One full-screen state. Home persists once built (parked, hidden, under other screens: Router `cutLayers`, FIX-A1).
private struct LayerView: View {
    let app: AppModel
    let router: Router
    let layer: ScreenLayer

    var body: some View {
        switch layer.screen {
        case .loading:
            LoadingScreen().onAppear { router.loadingAppeared() }
        case .home(_, let tab):
            // home is built once and parked (hidden) under other screens; its arrivals come from HomeLive (Router)
            HomeView(tab: tab, refill: router.homeRefill)
        case .level(let launch):
            if let view = router.levelView { view } else {
                // unreachable: Router.prepare sets levelView before any level layer mounts. F3-A (ruling 52(a)): the WP0
                // placeholder is Debug-only; a store build would draw nothing and log it
                #if DEBUG
                PlaceholderLevel(launch: launch).makeView()
                #else
                Color.clear.onAppear { Log.error("router", "\(Screen.level(launch).logName) has no level view") }
                #endif
            }
        case .event(let e):
            SocialEntry.makeEventScreen(e, app: app)
        case .profile:
            ProfileView()                                                           // S3 (Profile/ProfileView.swift)
        case .lab(let id):
            if let lab = DebugScreens.make(id.rawValue, app: app) { lab } else {
                NotInstalledView(text: "-pc.go \(id.rawValue): that owner's debug screen is not installed")
            }
        }
    }
}

/// One first-presentation warm-up item: a name for the log and the view rendered once, invisibly, behind Loading.
struct ShellPrewarmItem {
    let name: String
    let view: AnyView
    init<V: View>(_ name: String, _ view: V) {
        self.name = name
        self.view = AnyView(view)
    }
}

/// FIX-2 A (V3-06): the FIRST keyboard of a process cost one 205-305 ms main-thread frame (the Username popup's field, and so
/// the first Profile open: 540-665 ms; V3) — UIKit loads the keyboard's input system, layouts and dictionaries on first use.
/// Behind Loading an off-screen UITextField with the username field's traits (no autocapitalisation, no autocorrection)
/// becomes first responder and resigns in the SAME run-loop turn: the input system is loaded, no keyboard is ever committed
/// on screen (UI test: no keyboard on Loading / home). Once per process (`-pc.keyboardWarm 0` turns it off).
@MainActor enum KeyboardWarm {
    private static var done = false

    static func run(_ app: AppModel) {
        guard !done, app.args.raw["pc.keyboardWarm"] != "0", let window = BoardEngine.keyWindow() else { return }
        done = true
        let t0 = CACurrentMediaTime()
        let cpu0 = clock_gettime_nsec_np(CLOCK_THREAD_CPUTIME_ID)
        let field = UITextField(frame: CGRect(x: -400, y: -400, width: 10, height: 10))
        field.autocapitalizationType = .none
        field.autocorrectionType = .no
        field.spellCheckingType = .no
        field.alpha = 0.01                                  // off-screen and near-transparent (a disabled field cannot become first responder)
        CATransaction.begin(); CATransaction.setDisableActions(true)
        window.addSubview(field)
        let became = field.becomeFirstResponder()
        field.resignFirstResponder()
        field.removeFromSuperview()
        CATransaction.commit()
        Log.mark("warmup", String(format: "keyboard input system warmed (first responder %@) in %.1f ms (cpu %.1f)",
                                  became ? "yes" : "no", (CACurrentMediaTime() - t0) * 1000,
                                  Double(clock_gettime_nsec_np(CLOCK_THREAD_CPUTIME_ID) &- cpu0) / 1e6))
        KeyboardWarmProbe.shared.result = became ? "warmed" : "noFirstResponder"
    }
}

/// FIX-2 A-R: what the keyboard warm-up did in this process, for the UI test (`warmup.keyboard`, `-pc.uitest` only): its "no
/// keyboard ever shows" check is only meaningful once the warm-up really made a field first responder.
@MainActor @Observable final class KeyboardWarmProbe {
    static let shared = KeyboardWarmProbe()
    var result: String?
}

private struct KeyboardWarmMarker: View {
    var body: some View {
        if let r = KeyboardWarmProbe.shared.result {
            Color.clear.frame(width: 1, height: 1)
                .accessibilityElement()
                .accessibilityIdentifier("warmup.keyboard")
                .accessibilityValue(Text(verbatim: r))
                .allowsHitTesting(false)
        }
    }
}

/// FIX-2 A (V3-14): a popup that is about to be presented (the win panel, due at W + 4.034 s) is rendered ONCE, invisibly, a
/// moment before — with its real content (the level number, the reward, the tier) and its glyph rasters made off the main
/// thread (`gameTextDeferred`), like the Loading warm-up does for every popup with stand-in data. The panel's first frame then
/// composites cached rasters: the win panel's first presentation per process drew "Level 20", "Perfect!" ×3, "Rewards:",
/// "20" and "Continue" on the main thread (~22 ms of a 62 ms frame, build/p/FIX2/A/tp/v2-tp1) and every later one its new
/// "Level N" (~4 ms). The warm copy answers nothing and leaves after a few frames.
/// FIX-2 A-R: the copy is a WARM COPY (`shellWarmCopy`): WinPanel's appearance hands the celebration's dim over and logs the
/// panel — on the hidden copy at W+2.6 that removed the 0.894 dim 1.4 s before the real panel (the board full-bright from W+2.6
/// to W+4.03 on every win, review-A). And it is out of the accessibility tree (`accessibilityShown(false)`: a hidden ancestor
/// does not hide `win.continue` / `win.close`, which carry their own identifiers).
@MainActor @Observable final class PopupWarm {
    static let shared = PopupWarm()
    private(set) var item: (request: PopupRequest, style: PopupStyle)?
    @ObservationIgnored private var token = 0
    /// Warm copies drawn in this process (UI tests: `shell.warmProbe`).
    @ObservationIgnored private(set) var count = 0

    /// `hold`: keep the copy mounted until `cancel` (`-pc.popupWarm`, the UI test of the copy's accessibility).
    func warm(_ request: PopupRequest, style: PopupStyle, hold: Bool = false) {
        token += 1
        let tk = token
        item = (request, style)
        count += 1
        Log.mark("popup", "warm \(request.id.rawValue) (hidden\(hold ? ", held" : ""))")
        guard !hold else { return }
        Task { @MainActor [weak self] in
            await FrameWaiter.frames(3)
            var waited = 0
            while GameTextRaster.pendingCount > 0, waited < 60 {
                await FrameWaiter.frames(1)
                waited += 1
            }
            guard let self, tk == self.token else { return }
            self.item = nil
        }
    }

    /// `-pc.popupWarm win`: a warm copy of the win panel (the player's level, Normal, reward 20) held over the first screen.
    static func debugHold(_ id: String, app: AppModel) {
        guard id == PopupID.winPanel.rawValue else {
            Log.error("popup", "-pc.popupWarm \(id): only the win panel is warmed ahead (win)")
            return
        }
        let p = Popup<PopupResult>.winPanel(WinSummary(levels: [app.store.state.level], reward: 20, tag: .normal))
        shared.warm(p.request, style: p.style, hold: true)
    }

    /// The real presentation came first: drop the warm copy now.
    func cancel() {
        token += 1
        if item != nil { item = nil }
    }
}

private struct PopupWarmLayer: View {
    let app: AppModel
    @State private var host: PopupHost?

    var body: some View {
        if let w = PopupWarm.shared.item {
            ReferenceCanvas {
                PopupContent.make(w.request, style: w.style, answer: PopupAnswer(id: -9, host: host ?? PopupHost(ui: app.tuning.ui)),
                                  app: app)
            }
            .environment(\.gameTextDeferred, true)
            .environment(\.shellWarmCopy, true)             // FIX-2 A-R: no dim hand-over, no panel log (WinPanel)
            .opacity(0.001)
            .allowsHitTesting(false)
            .accessibilityShown(false)                       // FIX-2 A-R: was accessibilityHidden(true) (leaked win.continue)
            if app.args.uitest {
                // the UI test's proof that the copy IS mounted while it asserts none of its elements can be found
                Color.clear.frame(width: 1, height: 1)
                    .accessibilityElement()
                    .accessibilityIdentifier("popupWarm.mounted")
                    .accessibilityValue(Text(verbatim: w.request.id.rawValue))
                    .allowsHitTesting(false)
            }
        }
    }
}

/// FIX-2 A-R (`-pc.uitest` only): `shell.warmProbe` = "dim=<the running celebration's dim as drawn | none> warms=<warm copies
/// drawn in this process> mounted=<0|1>", computed when XCUITest asks (nothing per frame): the UI test that the win panel's
/// warm copy never takes the celebration's dim away.
private struct WarmProbe: UIViewRepresentable {
    func makeUIView(context: Context) -> WarmProbeView { WarmProbeView() }
    func updateUIView(_ uiView: WarmProbeView, context: Context) {}
}

final class WarmProbeView: UIView {
    override init(frame: CGRect) {
        super.init(frame: frame)
        isUserInteractionEnabled = false
        backgroundColor = .clear
        isAccessibilityElement = true
        accessibilityIdentifier = "shell.warmProbe"
        accessibilityLabel = "shell.warmProbe"
        accessibilityTraits = .staticText
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }

    override var accessibilityValue: String? {
        get { "dim=\(S2FX.celebrationDimProbe()) warms=\(PopupWarm.shared.count) mounted=\(PopupWarm.shared.item == nil ? 0 : 1)" }
        set {}
    }
}

private struct ShellWarmCopyKey: EnvironmentKey { static let defaultValue = false }

extension EnvironmentValues {
    /// FIX-2 A-R: this subtree is a hidden warm-up copy (the win panel's `PopupWarm`, the Loading `PopupPrewarm`): a view with
    /// side effects on appearing (WinPanel: the celebration dim hand-over, the `[PC][win] panel` log) skips them.
    var shellWarmCopy: Bool {
        get { self[ShellWarmCopyKey.self] }
        set { self[ShellWarmCopyKey.self] = newValue }
    }
}

/// FIX-2 A (V3-09, "purge event backdrops on page leave, off-main re-decode on next open"): the event PAGES' art (the Rocket
/// Rally and Cloud Hop backdrops alone are 11.5 MB each; with the Up & Away tower, the offer scenes and headers ≈ 60 MB of the
/// 142 MB of decoded art, build/p/FIX2/A/perf/v5-win8.log `[PC][memory]`) was decoded at launch and kept for the whole session,
/// whether or not the player can see those events. Kept now: the art of the events this player can open this week (unlocked
/// and featured); the rest is released on home's idle check. Only art no mounted view shows and no other screen draws: the
/// event pages are separate screens (their layers leave with them), and `kept` (home, the Shop tab, Profile) is never released.
/// Off in UI tests / captures.
/// FIX-2 A-R (review-A): an id drawn by more than one event is listed under EACH of them and released only when none of them
/// can be opened — the stage chests (Rocket Rally, Cloud Hop, Up & Away) were listed under Rocket Rally only, so every return
/// home released them and the Up & Away page decoded them again on the main thread (v8-pages6: "event art released:
/// rocketRace (0.2 MB)" after every visit); Profile's "Rocket Rally Wins" stat draws `rallyRocketMine` (`kept`). Art released
/// earlier is decoded again OFF the main thread: on home's idle check once its event can be opened again (a level-up unlock, a
/// new week), and by the router before the cut to its page if a tap comes first (`needsDecode`).
/// (FIX-2 A's ScreenWarm — each event page drawn once, hidden, before its first open — is gone: it delayed the page it
/// warmed by 80-90 ms, its hidden draws cost home 27-39 ms frames, and the page the home queue opens cost as much as before.)
@MainActor enum EventArtPolicy {
    /// Every raster the event's own screens draw (its page, its offer, its stage chests).
    static func art(_ e: EventID) -> [UIArt] {
        switch e {
        case .rocketRace: return [.eventRocketRaceBackdrop, .eventRocketRaceOffer, .eventRocketRaceRacerMine, .eventRocketRaceRacerOther, .eventRocketRaceStage1, .eventRocketRaceStage2,
                                  .eventRocketRaceStage3, .rewardChest1, .rewardChest2, .rewardChest3, .rank1Wings]
        case .skyJump: return [.eventSkyJumpBackdrop, .eventSkyJumpPlatform, .eventSkyJumpPlatformFar, .eventSkyJumpPlatformFar2, .eventSkyJumpPad, .eventSkyJumpOffer,
                               .rewardChest1, .rewardChest2, .rewardChest3]
        case .balloonRise: return [.eventBalloonRiseHero, .eventBalloonRiseTowerTop, .eventBalloonRiseTowerShaft, .eventBalloonRiseTowerFoot, .eventBalloonRiseLedge, .eventBalloonRiseCloudA,
                                   .eventBalloonRiseCloudB, .rewardChest3, .rewardChest2, .rewardChest1]
        case .clawChallenge: return [.eventClawChallengeHeader]
        case .streakRace: return [.eventStreakRaceHeader]
        default: return []
        }
    }

    static func art(_ screen: EventScreen) -> [UIArt] { art(event(of: screen)) }

    static func event(of screen: EventScreen) -> EventID {
        switch screen {
        case .claw: return .clawChallenge
        case .streakRace: return .streakRace
        case .rocketRace: return .rocketRace
        case .skyJump: return .skyJump
        case .balloonRise: return .balloonRise
        }
    }

    static let managed: [EventID] = [.rocketRace, .skyJump, .balloonRise, .clawChallenge, .streakRace]

    /// Never released: art a screen other than the event pages draws (home, the Shop tab, Profile).
    static var kept: Set<UIArt> { Set(HomeView.art + ShopView.art + ProfileView.art) }

    /// The art to release when `openable` are the events the player can open now: the other events' art that no openable
    /// event and no `kept` screen draws.
    static func releasable(openable: Set<EventID>) -> [UIArt] {
        var keep = kept
        for e in openable { keep.formUnion(art(e)) }
        var out: [UIArt] = [], seen: Set<UIArt> = []
        for e in managed where !openable.contains(e) {
            for a in art(e) where !keep.contains(a) && seen.insert(a).inserted { out.append(a) }
        }
        return out
    }

    /// The managed events this player can open now (unlocked, and featured / live / just finished this week).
    static func openable(_ app: AppModel) -> Set<EventID> {
        let st = Events.status(app.store.state, now: app.clock.wallClock(), rules: ShellEconomy.rules(app))
        let level = app.store.state.level
        var out: Set<EventID> = []
        for e in managed {
            let visible: Bool
            switch e {
            case .rocketRace: visible = st.rocketRace != nil || st.live.contains(e)
            case .skyJump: visible = st.skyJump != nil || st.live.contains(e)
            case .balloonRise: visible = st.balloon != nil || st.live.contains(e) || st.finished.ladder == e
            case .clawChallenge: visible = st.claw != nil || st.live.contains(e) || st.finished.ladder == e
            case .streakRace: visible = st.streakRace != nil || st.live.contains(e)
            default: visible = true
            }
            if visible && EventSchedule.isUnlocked(e, level: level, rules: app.economy.events) { out.insert(e) }
        }
        return out
    }

    /// Paths released by this policy and not decoded again by it since.
    private static var released: Set<String> = []

    /// Home's idle check: releases the art of the events this player cannot open now, and decodes again (off the main thread)
    /// the released art of the events that can be opened now.
    static func apply(_ app: AppModel) {
        guard !app.args.quietUI, app.router.screen.isHome || app.router.screen.isLevel else { return }
        let open = openable(app)
        let paths = releasable(openable: open).map(\.path).filter { ArtStore.isCached(path: $0) }
        if !paths.isEmpty {
            released.formUnion(paths)
            let names = managed.filter { e in !open.contains(e) && art(e).contains { paths.contains($0.path) } }.map(\.rawValue)
            let bytes = ArtStore.purge(paths: paths)
            Log.mark("memory", String(format: "event art released: %@ (%.1f MB; not openable now)", names.joined(separator: ", "),
                                      Double(bytes) / 1_048_576))
        }
        let back = Array(Set(open.flatMap { art($0) })).filter { released.contains($0.path) }
        if !back.isEmpty {
            released.subtract(back.map(\.path))
            Task.detached(priority: .utility) { ArtStore.preload(back) }
            Log.mark("memory", "event art of \(open.map(\.rawValue).sorted().joined(separator: ", ")) decoded again off the main thread (\(back.count) ids)")
        }
    }

    /// Whether the page's art was released and not decoded again (the router then decodes it before the cut).
    static func needsDecode(_ screen: EventScreen) -> Bool { art(screen).contains { released.contains($0.path) } }

    /// Decodes a page's art off the main thread (before it is drawn).
    static func decode(_ screen: EventScreen) async {
        let arts = art(screen)
        released.subtract(arts.map(\.path))
        let t0 = ProcessInfo.processInfo.systemUptime
        _ = await Task.detached(priority: .userInitiated) { ArtStore.preload(arts) }.value
        Log.mark("memory", String(format: "event art of %@ decoded off the main thread before its page in %.0f ms", screen.rawValue,
                                  (ProcessInfo.processInfo.systemUptime - t0) * 1000))
    }
}

/// FIX-2 A (A4-o1): home's rasters (the Shop page's, home's, every home rig layer) decoded OFF the main thread from the moment
/// the router exists (like LoadingArt), so home's slices behind Loading pay no decode. ArtStore is thread-safe and keeps them.
@MainActor enum HomeArtPreload {
    private static var started = false
    private(set) static var finished = false

    static func start() {
        guard !started else { return }
        started = true
        let art = ShopView.art + HomeView.art
        let rigLayers = HomeView.rigLayerPaths()
        let t0 = ProcessInfo.processInfo.systemUptime
        Task.detached(priority: .userInitiated) {
            ArtStore.preload(art)
            for p in rigLayers { _ = ArtStore.image(path: p) }
            let ms = (ProcessInfo.processInfo.systemUptime - t0) * 1000
            await MainActor.run {
                HomeArtPreload.finished = true
                Log.mark("warmup", String(format: "home art %d + %d rig layers decoded off-main in %.0f ms", art.count, rigLayers.count, ms))
            }
        }
    }

    /// Returns when the decode is done (or after `timeout` s: home then decodes what is missing, as before).
    static func wait(timeout: Double) async {
        guard started else { return }
        let end = ProcessInfo.processInfo.systemUptime + timeout
        while !finished, ProcessInfo.processInfo.systemUptime < end { await FrameWaiter.frames(1) }
    }
}

/// FIX-A1: the state of the Loading warm-up (the router holds Loading until it is done, capped).
@MainActor enum ShellPrewarm {
    private(set) static var started = false
    private(set) static var done = false
    /// Every item (each owner's hook returns its list). Order: the home / meta screens first, the in-play popups and the HUD
    /// last — the chrome raster cache drops its OLDEST entries when full, so what a level needs is made last.
    static func items(_ app: AppModel) -> [ShellPrewarmItem] {
        let host = PopupHost(ui: app.tuning.ui)
        var list: [ShellPrewarmItem] = []
        list += S3Popups.prewarm(app)                                                // S3 hook (Popups/S3Hooks.swift)
        list += SocialPopups.prewarm(app)                                            // SOC2 hook (Social/SocialPopups.swift)
        list += [
            ShellPrewarmItem("settings", ReferenceCanvas { SettingsPopup(answer: PopupAnswer(id: -2, host: host)) }),
            ShellPrewarmItem("quitLevel", ReferenceCanvas { QuitLevelPopup(answer: PopupAnswer(id: -3, host: host)) }),
            ShellPrewarmItem("pause", ReferenceCanvas { PausePopup(answer: PopupAnswer(id: -1, host: host)) }),
        ]
        list += S2Popups.prewarm(app)                                                // S2 hook (HUD/S2Hooks.swift)
        return list
    }

    /// When the warm-up must be done: the router's Loading cap (launch + `loading.capSeconds`), less a margin for the drain.
    static func deadline(_ app: AppModel) -> Double { app.launchUptime + app.tuning.ui.loadingCapSeconds - 0.35 }

    fileprivate static func begin() -> Bool {
        guard !started else { return false }
        started = true
        return true
    }

    fileprivate static func finish() { done = true }

    /// Awaited by the router before it leaves Loading: returns when the warm-up is done, or at `deadline` (uptime), or
    /// when no warm-up started within the first frames (a launch that never showed Loading).
    static func wait(until deadline: Double) async {
        var frames = 0
        while !done, ProcessInfo.processInfo.systemUptime < deadline {
            if !started && frames > 30 { return }
            await FrameWaiter.frames(1)
            frames += 1
        }
        if !done { Log.error("warmup", "Loading warm-up still running at the Loading cap: the first screen goes up anyway") }
    }
}

/// The first-presentation warm-up behind Loading (§8.5 step 3, SPEC-architecture §10.2 "no first-presentation stall"):
/// every popup and page of the owners' lists is rendered once, invisibly, so its SwiftUI graph, glyph rasters, chrome
/// rasters and art are paid here and not on its first real presentation. FIX-A1: STAGED — one item mounts per presented
/// frame and leaves two frames later (it has then been committed and drawn once; the caches keep what it made), so no frame
/// carries the whole list (it was ONE 0.6-2.3 s frame that froze the Loading dots) and no frame pays a big unmount when
/// Loading goes. GameText rasters are made off the main thread here (`gameTextDeferred`): the item is invisible, only the
/// cache matters. The router holds Loading until the list is done (capped at `loading.capSeconds` from launch).
private struct PopupPrewarm: View {
    let app: AppModel
    @State private var items: [ShellPrewarmItem] = []
    @State private var mounted: Range<Int> = 0..<0

    var body: some View {
        ZStack {
            ForEach(Array(mounted), id: \.self) { i in
                if i < items.count { items[i].view }
            }
        }
        .environment(\.gameTextDeferred, true)
        .environment(\.shellWarmCopy, true)                 // FIX-2 A-R: a warm copy (the win tiers carry `prewarm: true` too)
        .opacity(0.001)
        .allowsHitTesting(false)
        .accessibilityShown(false)                           // FIX-2 A-R: was accessibilityHidden(true) (ids leaked)
        .task { await run() }
    }

    private func run() async {
        guard ShellPrewarm.begin() else { return }
        // FIX-2 A (V3-06): the text input system first — ONE long frame (≈ 130 ms main-thread CPU on the Release simulator)
        // early behind Loading, where the dots keep cycling on the render server (LoadingDots), not next to the cut
        KeyboardWarm.run(app)
        await FrameWaiter.frames(1)
        S2Hooks.warmUp(app)
        S3Hooks.warmUp(app)
        // FIX-2 A (A4-o1): home first, in slices, hidden under Loading (the cut out of Loading then only shows it) — once its
        // art is decoded off the main thread (started with the router: HomeArtPreload)
        await HomeArtPreload.wait(timeout: 1.0)
        await (app.router as? Router)?.buildHomeBehindLoading()
        // the rasters the Shop page and home show, decoded off the main thread before their items mount (ArtStore is
        // thread-safe; they are decoded and kept anyway once shown)
        let art = ShopView.art + HomeView.art
        let rigLayers = HomeView.rigLayerPaths()                            // A4 FEEL: the home rigs' layers too
        Task.detached(priority: .userInitiated) {
            ArtStore.preload(art)
            for p in rigLayers { _ = ArtStore.image(path: p) }
        }
        let list = ShellPrewarm.items(app)
        items = list
        let t0 = ProcessInfo.processInfo.systemUptime
        let deadline = ShellPrewarm.deadline(app)
        var staged = 0
        var frameS = 1.0 / 60
        var last = t0
        while staged < list.count, !Task.isCancelled {
            // one item per frame; up to 3 when the frames are cheap (< 30 ms) but too few remain before the Loading cap —
            // never when frames are slow: the Loading dots must keep moving (an item the cap cuts off is logged and pays
            // its first presentation later)
            let now = ProcessInfo.processInfo.systemUptime
            let framesLeft = max(1, (deadline - now) / max(frameS, 1.0 / 120))
            let wanted = Int((Double(list.count - staged) / framesLeft).rounded(.up))
            let n = min(list.count - staged, frameS < 0.030 ? min(3, max(1, wanted)) : 1)
            let lower = max(0, staged - 1)
            staged += n
            mounted = lower..<staged
            Log.mark("warmup", "prewarm \(staged)/\(list.count) \(list[(staged - n)..<staged].map(\.name).joined(separator: "+")) "
                     + "(chrome rasters so far \(RasterCache.count))")
            await FrameWaiter.frames(1)
            let t = ProcessInfo.processInfo.systemUptime
            frameS = 0.7 * frameS + 0.3 * (t - last)
            last = t
        }
        // the last items leave one per frame too; then the off-main glyph rasters finish
        while !mounted.isEmpty, !Task.isCancelled {
            mounted = (mounted.lowerBound + 1)..<mounted.upperBound
            await FrameWaiter.frames(1)
        }
        var waited = 0
        while GameTextRaster.pendingCount > 0, waited < 120, !Task.isCancelled {
            await FrameWaiter.frames(1)
            waited += 1
        }
        ShellPrewarm.finish()
        Task { @MainActor in                                    // FIX-2 A (V3-09): once the first screen is up
            for _ in 0..<600 where !(app.router.screen.isHome || app.router.screen.isLevel) {
                try? await Task.sleep(nanoseconds: 50_000_000)
            }
            try? await Task.sleep(nanoseconds: 1_500_000_000)
            EventArtPolicy.apply(app)
        }
        Log.mark("warmup", String(format: "prewarm %d/%d items staged over %.3f s (glyph rasters %d cached, %d pending; chrome rasters %d)",
                                  staged, list.count, ProcessInfo.processInfo.systemUptime - t0, GameTextRaster.count,
                                  GameTextRaster.pendingCount, RasterCache.count))
    }
}

extension ShellEntry {
    static func makeRoot(_ app: AppModel) -> AnyView {
        guard let router = app.router as? Router else {
            // unreachable: ShellEntry.makeRouter (Router.swift) always makes SHELL's Router. F3-A (ruling 52(a)): the WP0 boot
            // placeholder is Debug-only; a store build shows the launch colour and logs it
            #if DEBUG
            Log.error("boot", "ShellEntry.makeRoot: the router is not SHELL's Router; keeping the WP0 placeholder")
            return AnyView(BootPlaceholderView(app: app))
            #else
            Log.error("boot", "ShellEntry.makeRoot: the router is not SHELL's Router")
            return AnyView(Color("LaunchBackground").ignoresSafeArea())
            #endif
        }
        router.attach(app)
        return AnyView(RootView(app: app, router: router))
    }
}
