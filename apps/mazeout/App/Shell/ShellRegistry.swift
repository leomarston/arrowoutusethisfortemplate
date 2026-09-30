import SwiftUI
import UIKit
import PathCore

// Kit decoupling step (docs/ROADMAP.md, docs/guides/KIT.md §3): the shell's hubs (PopupHost, RootView, Router, the FX host,
// S2Hooks) ask these registries for the panels, screens, effects, strips and warm-ups other components provide, instead of
// naming them. Each component registers itself from its own `<Name>Registration.swift` (`register()`), and the game lists
// the components it ships in ONE place: GameComponents.swift (`GameComponents.registerAll`). Removing a component = deleting
// its files and its line there; a component that is not registered is simply absent (its popup answers its fallback, its
// strip or screen is not drawn).
// Everything is installed lazily on the first question (`ComponentRegistry.installOnce`), so the order of boot, of unit tests
// and of previews never matters. Orders (`order:`) are explicit where the reference game's sequence matters (the Loading
// warm-up list, the win-panel strip priority): the registration list reproduces today's routing exactly.

@MainActor enum ComponentRegistry {
    private static var installed = false

    /// Registers every component of the game once (GameComponents.registerAll).
    static func installOnce() {
        guard !installed else { return }
        installed = true
        GameComponents.registerAll()
    }
}

// MARK: - popups: the panel of a request

/// One component's popup panels: which requests it draws, which of them are full pages, and the view.
struct PopupPanelProvider {
    let name: String
    let handles: @MainActor (PopupRequest) -> Bool
    let isPage: @MainActor (PopupRequest) -> Bool
    /// A page of this provider keeps its dim hand-over when it closes (the event pages: the Weekly tutorial → its intro, the
    /// Up & Away fall / Sky Jump progress / Rocket result pages → Level Failed or home). The player's own pages do not.
    let pagesHandOver: Bool
    /// The `popup.variant` value UI tests read (nil = the panel publishes none).
    let variant: (@MainActor (PopupRequest, AppModel) -> String)?
    let make: @MainActor (PopupRequest, PopupAnswer) -> AnyView

    init(_ name: String, handles: @escaping @MainActor (PopupRequest) -> Bool,
         isPage: @escaping @MainActor (PopupRequest) -> Bool = { _ in false }, pagesHandOver: Bool = false,
         variant: (@MainActor (PopupRequest, AppModel) -> String)? = nil,
         make: @escaping @MainActor (PopupRequest, PopupAnswer) -> AnyView) {
        self.name = name; self.handles = handles; self.isPage = isPage; self.pagesHandOver = pagesHandOver
        self.variant = variant; self.make = make
    }
}

@MainActor enum PopupPanels {
    private static var providers: [PopupPanelProvider] = []

    static func register(_ p: PopupPanelProvider) { providers.append(p) }

    /// The provider that draws `r` (the first registered one that handles it; every request has at most one owner).
    static func provider(for r: PopupRequest) -> PopupPanelProvider? {
        ComponentRegistry.installOnce()
        return providers.first { $0.handles(r) }
    }

    /// A full page drawn on the live screen (not the scaled popup canvas).
    static func isPage(_ r: PopupRequest) -> Bool {
        ComponentRegistry.installOnce()
        return providers.contains { $0.isPage(r) }
    }

    /// An event page (its dim hands over to what follows it).
    static func pageHandsOver(_ r: PopupRequest) -> Bool {
        ComponentRegistry.installOnce()
        return providers.contains { $0.pagesHandOver && $0.isPage(r) }
    }

    /// The `popup.variant` accessibility value of `r` ("" when its panel publishes none).
    static func variant(_ r: PopupRequest, app: AppModel) -> String {
        guard let p = provider(for: r), let v = p.variant else { return "" }
        return v(r, app)
    }
}

/// `popup.variant` (value = the provider's variant): the layout a popup chose, for UI tests (a `.contain` container exposes
/// no value). The S2 panels (fail chain, win, unlock, claim) draw it over their panel, as S2Popups did.
struct PopupVariantMarker: View {
    let request: PopupRequest
    @Environment(AppModel.self) private var app
    var body: some View {
        Color.clear.frame(width: 1, height: 1)
            .accessibilityElement()
            .accessibilityIdentifier("popup.variant")
            .accessibilityValue(Text(verbatim: PopupPanels.variant(request, app: app)))
            .allowsHitTesting(false)
    }
}

extension View {
    /// The S2 panel frame: the panel with its `popup.variant` marker (S2Popups.make's ZStack).
    func popupVariantMarker(_ request: PopupRequest) -> some View {
        ZStack(alignment: .topLeading) {
            self
            PopupVariantMarker(request: request)
        }
    }
}

// MARK: - `-pc.popup <id>[:variant]` launchers

@MainActor enum DebugPopups {
    /// A component's `-pc.popup` launcher: true = it owned the id (and presented it).
    typealias Launcher = @MainActor (LaunchArgs.PopupArg, AppModel) async -> Bool
    private static var launchers: [Launcher] = []

    static func register(_ f: @escaping Launcher) { launchers.append(f) }

    /// Tries every registered launcher in order; false = no component owns `p.id`.
    static func present(_ p: LaunchArgs.PopupArg, app: AppModel) async -> Bool {
        ComponentRegistry.installOnce()
        for f in launchers {
            if await f(p, app) { return true }
        }
        return false
    }

    /// SHELL-private `-pc.s3PopupLoop N` (S3's panels): opens + closes `request` N times (0.8 s apart), each open's frames
    /// logged. True = the loop ran (the launcher is done).
    static func loopIfRequested(_ p: LaunchArgs.PopupArg, app: AppModel, request: PopupRequest, style: PopupStyle) async -> Bool {
        guard let n = app.args.raw["pc.s3PopupLoop"].flatMap(Int.init), n > 0, let host = app.popups as? PopupHost else { return false }
        for i in 0..<n {
            let probe = FrameProbe("popup \(p.id) loop \(i)")
            probe.start()
            Task { @MainActor in _ = await host.present(Popup<PopupResult>(request, style: style, fallback: .close)) }
            try? await Task.sleep(nanoseconds: 500_000_000)
            host.dismissAll()
            try? await Task.sleep(nanoseconds: 300_000_000)
            probe.stop()
        }
        return true
    }
}

// MARK: - the Loading warm-up: first presentations and boot hooks

@MainActor enum ShellPrewarmItems {
    private struct Entry {
        let order: Int
        let seq: Int
        let make: @MainActor (AppModel, PopupHost) -> [ShellPrewarmItem]
    }
    private static var entries: [Entry] = []

    /// A component's items for the staged first-presentation warm-up behind Loading. `order` places them in the one list
    /// (the chrome raster cache drops its OLDEST entries when full, so what a level needs is made last: the home / meta
    /// screens first, the in-play popups and the HUD last).
    static func register(order: Int, _ make: @escaping @MainActor (AppModel, PopupHost) -> [ShellPrewarmItem]) {
        entries.append(Entry(order: order, seq: entries.count, make: make))
    }

    static func items(_ app: AppModel) -> [ShellPrewarmItem] {
        ComponentRegistry.installOnce()
        let host = PopupHost(ui: app.tuning.ui)
        return entries.sorted { ($0.order, $0.seq) < ($1.order, $1.seq) }.flatMap { $0.make(app, host) }
    }
}

@MainActor enum ShellWarmUps {
    private struct Entry {
        let order: Int
        let seq: Int
        let run: @MainActor (AppModel) -> Void
    }
    private static var entries: [Entry] = []

    /// Work a component does once behind Loading, as the warm-up starts (the logo split, the store's start, the offers' Shop
    /// route).
    static func register(order: Int, _ run: @escaping @MainActor (AppModel) -> Void) {
        entries.append(Entry(order: order, seq: entries.count, run: run))
    }

    static func run(_ app: AppModel) {
        ComponentRegistry.installOnce()
        for e in entries.sorted(by: { ($0.order, $0.seq) < ($1.order, $1.seq) }) { e.run(app) }
    }
}

// MARK: - strips and slots other components draw inside a panel

/// Where a panel strip goes: under the win panel (the Rocket Race bar, Up & Away's strip or the Streak Race strip) or under
/// Level Failed (the Streak Race strip, its chip sliding back to x1).
enum PanelStripPlace: Equatable { case win, levelFailed }

struct PanelStripContext {
    let app: AppModel
    let place: PanelStripPlace
    /// The panel's level (the session's last level).
    let level: Int
    /// The win's event outcomes ([] on Level Failed).
    let outcomes: [EventOutcome]
    /// MotionClock game time of the panel's first frame; nil = at rest.
    let shownAt: Double?
}

@MainActor enum PanelStrips {
    private struct Entry {
        let order: Int
        let seq: Int
        let make: @MainActor (PanelStripContext) -> AnyView?
    }
    private static var entries: [Entry] = []

    /// A strip provider: nil = not drawn in this context. The first provider (by `order`) that draws wins (the reference game:
    /// the Rocket Race bar 10, Up & Away 20, the Streak Race 30).
    static func register(order: Int, _ make: @escaping @MainActor (PanelStripContext) -> AnyView?) {
        entries.append(Entry(order: order, seq: entries.count, make: make))
    }

    static func view(_ ctx: PanelStripContext) -> AnyView? {
        ComponentRegistry.installOnce()
        for e in entries.sorted(by: { ($0.order, $0.seq) < ($1.order, $1.seq) }) {
            if let v = e.make(ctx) { return v }
        }
        return nil
    }
}

/// Continue? (streak / life layouts): the multiplier chip row on the cream strip, with the current step lit (the Streak Race's
/// chips; not drawn when no component provides them).
@MainActor enum ContinueChips {
    private static var maker: (@MainActor (_ steps: [Int], _ lit: Int, _ frame: CGRect, _ t: Tokens) -> AnyView)?

    static func register(_ make: @escaping @MainActor (_ steps: [Int], _ lit: Int, _ frame: CGRect, _ t: Tokens) -> AnyView) {
        maker = make
    }

    static func view(steps: [Int], lit: Int, frame: CGRect, t: Tokens) -> AnyView? {
        ComponentRegistry.installOnce()
        return maker?(steps, lit, frame, t)
    }
}

// MARK: - screens

/// What the router, the root view and the social pages ask of the home screen without naming it (the home component
/// registers `ShellScreens.home`). Every member mirrors one of home's own calls (HomeLive / HomeTabStrip / HomeBuild /
/// HomeScene / PayoutSequence / HomeLevelInfo), so the router's parked-home choreography is unchanged.
@MainActor protocol HomeScreenHooks: AnyObject {
    /// The home screen for a layer (built once and parked; `refill` = the router's pile-refill token).
    func makeView(tab: HomeTab, refill: Int) -> AnyView
    /// The player state as home draws it (a frozen copy while home is parked under another screen).
    func state(_ app: AppModel) -> PlayerState
    /// false while home is parked (its timelines pause).
    var isActive: Bool { get }
    /// The event layer's last drawn timeline date (a parked home's countdowns stay at it).
    var eventsDrawnAt: Date? { get }
    /// A home tab page is drawn (during a slide: every page the strip exposes).
    func isTabShown(_ tab: HomeTab) -> Bool
    /// A writer that changed the store and a display counter in one turn (the Shop's coin fly) syncs home's copy now.
    func syncState()
    /// The capsule machine's pile refills on the next arrival.
    func requestRefill()
    func takeRefill() -> Bool
    // the router
    func attach(_ store: PlayerStore)
    var arrivalStale: Bool { get }
    @discardableResult func prepareArrival() -> Bool
    func mountTabs()
    func arrive(_ entry: HomeEntry, arrival: Int)
    func park()
    func resume()
    func slideTab(to tab: HomeTab, ui: UITuning)
    func jumpTab(to tab: HomeTab)
    func beginBuild()
    var isBuilding: Bool { get }
    func buildStep()
    func finishBuild()
    func cancelPayout()
    /// The next level's tag, read off the main thread before the level home shows after a win.
    func prefetchLevel(_ level: Int, args: LaunchArgs)
    /// Every layer image of the rigs home draws (decoded off the main thread under Loading).
    func rigLayerPaths() -> [String]
    /// `-pc.tabLoop` (measurement): the tab strip logs its commits.
    func probeTabCommits()
}

/// The Loading screen (its view and its art's lifetime).
struct LoadingScreenHooks {
    let makeView: @MainActor () -> AnyView
    /// Decodes Loading's art off the main thread (the router's first act).
    let startArt: @MainActor () -> Void
    /// Loading never shows again this launch: its art goes.
    let releaseArt: @MainActor () -> Void
}

@MainActor enum ShellScreens {
    private static var _home: (any HomeScreenHooks)?
    private static var _loading: LoadingScreenHooks?
    private static var _profile: (@MainActor () -> AnyView)?
    private static var _toastLayer: (@MainActor (AppModel, _ inLevel: Bool) -> AnyView?)?
    typealias ViewMaker = @MainActor () -> AnyView
    private static var tabPages: [HomeTab: ViewMaker] = [:]

    static func registerHome(_ hooks: any HomeScreenHooks) { _home = hooks }
    static func registerLoading(_ hooks: LoadingScreenHooks) { _loading = hooks }
    static func registerProfile(_ make: @escaping @MainActor () -> AnyView) { _profile = make }
    static func registerToastLayer(_ make: @escaping @MainActor (AppModel, _ inLevel: Bool) -> AnyView?) { _toastLayer = make }
    /// A home tab page other than home itself (the Shop tab, the Leaderboard tab).
    static func registerTabPage(_ tab: HomeTab, _ make: @escaping @MainActor () -> AnyView) { tabPages[tab] = make }

    static var home: (any HomeScreenHooks)? { ComponentRegistry.installOnce(); return _home }
    static var loading: LoadingScreenHooks? { ComponentRegistry.installOnce(); return _loading }

    static func profileView() -> AnyView? { ComponentRegistry.installOnce(); return _profile?() }
    static func toastLayer(_ app: AppModel, inLevel: Bool) -> AnyView? { ComponentRegistry.installOnce(); return _toastLayer?(app, inLevel) }
    static func tabPage(_ tab: HomeTab) -> AnyView? { ComponentRegistry.installOnce(); return tabPages[tab]?() }

    /// Home's view of the player state; the store's when no home is registered.
    static func homeState(_ app: AppModel) -> PlayerState { home?.state(app) ?? app.store.state }
}

/// The rasters the shell keeps or decodes ahead for the screens other components provide.
@MainActor enum ShellArt {
    private struct Entry {
        let order: Int
        let seq: Int
        let art: @MainActor () -> [UIArt]
    }
    typealias ArtList = @MainActor () -> [UIArt]
    private static var keptLists: [ArtList] = []
    private static var preloadLists: [Entry] = []

    /// Art a screen other than the event pages draws (home, the Shop tab, Profile): never released by `EventArtPolicy`.
    static func registerKept(_ art: @escaping @MainActor () -> [UIArt]) { keptLists.append(art) }
    /// Art decoded off the main thread from the router's creation (home's slices then pay no decode). `order` = the decode
    /// order (the reference game: the Shop page's art 10, home's 20).
    static func registerPreload(order: Int, _ art: @escaping @MainActor () -> [UIArt]) {
        preloadLists.append(Entry(order: order, seq: preloadLists.count, art: art))
    }

    static var kept: [UIArt] {
        ComponentRegistry.installOnce()
        return keptLists.flatMap { $0() }
    }

    static var preload: [UIArt] {
        ComponentRegistry.installOnce()
        return preloadLists.sorted { ($0.order, $0.seq) < ($1.order, $1.seq) }.flatMap { $0.art() }
    }
}
