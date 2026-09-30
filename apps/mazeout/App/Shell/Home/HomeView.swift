import SwiftUI
import PathCore

// SHELL S1 skeleton (SPEC-architecture §6.4; S3 completes: HomeScene, ClawBar, EventBadges, PayoutSequence). Z-order back →
// front = SPEC-ui §2.2.1 (shots 002 / 026 / 035 / 060, the scene lane's proof); A4 ART-INTEG: the D1 art of R2 CAST / R3 HOME
// (art/lanes/{cast,home}.handoff.json; ruling 46: the same composition, restyled — the ui.json rects unchanged except the
// station's and the centrepiece's, which are the new art's own frames):
//   1. the scene: `homeWorkshop` (full bleed), the boss's torso + head, `homeScaffold` (his station), the boss's arms,
//      `homeFloor`, `homeCabinet` + the signpost centrepiece (owner item 4) — placed with the aspect-FILL scene transform
//      (identity on the reference phone);
//   2. LEVEL caption + plate (green / red / purple) + the Play frame and button (+ Hard / Super Hard ribbon);
//   3. the two Diggers in front of the cabinet's lower corners;
//   4. the top bar; 6. the bottom nav. (5 Claw bar + event badges and 7 the payout: S3.)
// The level shown is `PlayerState.level` (the next level); its tag comes from the bundled level file (`HomeLevelInfo`).
// Tabs: shop (S3's page), home, leaderboard (SOCIAL's `SocialEntry.makeLeaderboard`). A2 FEEL-P (owner item 2; motion-catalog
// §3.1 / §6.1 / §11.3 R2, VERIFIED v552 + v582 60 Hz): a tab change PUSH-SLIDES — the three pages sit side by side in ONE strip
// and the strip moves (`HomeTabStrip`) along v582's measured curve (ui.json `transition.tabSlide.table`: 26 frames ≈ 0.433 s,
// ≈ D·(1 − t/0.488)^2.51), the same duration for a 2-page jump (Home passes through); the bottom nav stays still and its raised
// tab jumps on the tap's frame. A cut INTO home (a level, Profile, Loading) shows the tab at once. Was a hard cut (SPEC-ui §1.8,
// INFERRED from 1-fps shots).

struct HomeView: View {
    let tab: HomeTab
    /// FIX-A1: the pile-refill token (the router's; a new non-zero value refills the capsule machine's pile on this arrival).
    var refill = 0
    /// FIX-A1: set only where home is hosted outside the router (the S3 lab): arrives once with this entry on creation.
    /// Under the router, home is built once and parked between visits, and its arrival (entry + number) comes from
    /// `HomeLive` — so an arrival re-renders the few views that show what changed, not the whole screen.
    var labEntry: HomeEntry? = nil
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let strip = HomeTabStrip.shared
        let parts = HomeBuild.shared.limit                                          // FIX-2 A: built in slices behind Loading
        LayerStack {                                                                // FIX-A1: was a top-leading ZStack
            // A2: the three pages in ONE strip (page i at x = (i − position) · width), moved by `HomeTabStrip` (the tab push-slide).
            // S3 / FIX-A1 kept: every page stays built (the home scene, the puppets, the top bar; the Shop and Leaderboard pages
            // once mounted), and a page out of view is hidden (opacity 0: Core Animation draws nothing of it) — only the pages
            // the strip exposes during a slide are drawn (item 5: no other page flashes).
            LayerStack {
                HomeTabPage(page: .home, width: m.size.width) { HomeMainPage(refill: refill, parts: parts) }
                    .allowsHitTesting(tab == .home)
                    .accessibilityShown(tab == .home)
                // S3: the Shop and Leaderboard pages are built once home has been idle for a moment (hidden, render-server
                // animations unaffected), so a tab tap starts the slide, not a page build in the tap's frame; a page that is
                // sliding out stays mounted until the slide ends
                if parts >= HomeBuild.shop, tab == .shop || HomeLive.shared.tabsMounted || strip.shown.contains(.shop) {
                    HomeTabPage(page: .shop, width: m.size.width) { ShellScreens.tabPage(.shop) ?? AnyView(EmptyView()) }   // the shop component
                        .allowsHitTesting(tab == .shop).accessibilityShown(tab == .shop)
                }
                if parts >= HomeBuild.leaderboard,
                   tab == .leaderboard || HomeLive.shared.tabsMounted || strip.shown.contains(.leaderboard) {
                    HomeTabPage(page: .leaderboard, width: m.size.width) { ShellScreens.tabPage(.leaderboard) ?? AnyView(EmptyView()) }   // social-ui
                        .allowsHitTesting(tab == .leaderboard)
                        .accessibilityShown(tab == .leaderboard)
                }
            }
            if parts >= HomeBuild.nav {
                HomeNavBar(tab: tab) { selected in
                    guard selected != tab else { return }
                    PayoutSequence.cancel()                                         // S3: leaving home mid-queue
                    app.router.go(.home(.normal, tab: selected))
                }
                TrophyNewsBadge(tab: tab)                                           // S3 (Home/EventBadges.swift)
            }
            if parts >= HomeBuild.all { HomeArrival(tab: tab, labEntry: labEntry) }
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .clipped()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.home")
        .onDisappear { PayoutSequence.cancel() }
    }

    /// Lives pill (SPEC-ui §2.2.2): full or unlimited → nothing; fewer than 5 → the More Lives popup (S3 builds its panel; until
    /// then the popup host answers its fallback in Release and shows the DEBUG pending panel).
    static func openLives(_ app: AppModel) {
        let s = app.store.state
        let rules = ShellEconomy.rules(app)                                          // S3: refills applied (C3)
        let unlimited = Economy.hasUnlimitedLives(s, now: app.clock.wallClock())
        guard Economy.livesCount(s, now: app.clock.wallClock(), rules: rules) < rules.lives.max, !unlimited else {
            Log.mark("home", "lives pill: full, nothing to do"); return
        }
        Task { @MainActor in _ = await app.popups.present(Popup<PopupResult>.noLives) }
    }

    /// The home screen's rasters, decoded before it shows.
    static let art: [UIArt] = [.homeBackdrop, .homeFloor, .homeStation, .homeStand, .currencyCoinIcon,
                               .hudPlusBadge, .livesHeart, .iconSettings, .navShopIcon, .navHomeIcon, .navLeaderboardIcon]

    /// The home rigs by slot (skin/art.json `rigs`; the scene's layers: skin/scenes.json `home`). A4 (R2 CAST): the D1 rigs carry
    /// the SAME layer names, groups, defaults and pivots as the rigs they replaced, so PuppetStage, the scene's rig part sets
    /// and the ui.json puppet tracks (keyed by the rig folder) apply unchanged.
    static let bossRig = ArtRig.homeCharacterMain.folder
    static let diggerLeftRig = ArtRig.homeCharacterLeft.folder
    static let diggerRightRig = ArtRig.homeCharacterRight.folder
    static let signpostRig = ArtRig.homeCentrepiece.folder

    /// A4 FEEL: every layer PNG of the rigs home draws (every rig slot of the skin: the characters, the centrepiece, the event
    /// badges, the Up & Away token), for the boot prewarm to decode OFF the main thread under Loading — PuppetView builds its
    /// layers from ArtStore's cache, so home's first build pays no PNG decode (Release sim before: a 240 ms main-thread frame at
    /// the Loading → home cut).
    @MainActor static func rigLayerPaths() -> [String] {
        ArtRig.allCases.compactMap { PuppetCache.rig($0.folder) }.flatMap { r in r.layers.map { r.path($0) } }
    }

    static func name(_ e: HomeEntry) -> String {
        switch e {
        case .normal: return "normal"
        case .afterWin(let w): return "afterWin(L\(w.levels.first ?? 0) +\(w.reward))"
        case .afterLoss: return "afterLoss"
        case .firstHome(let w): return "firstHome(+\(w.reward))"
        }
    }
}

/// The home page itself (A2: a view of its own, so a tab change — which re-runs HomeView's body for the nav — does not
/// re-run the page's body: its inputs are unchanged, only its strip slot moves).
private struct HomeMainPage: View {
    let refill: Int
    /// FIX-2 A: how many of home's slices are built (`HomeBuild`; Int.max = all).
    var parts = Int.max
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        LayerStack {                                                                // FIX-A1: was a top-leading ZStack
            t.color("home.base", Skin.homeHomeViewHomeBase)
            if parts >= HomeBuild.scene { scene(t) }
            if parts >= HomeBuild.controls {
                HomeLevelControls()
                SceneLayer(size: m.size) {
                    ForEach(SkinScenes.homeFront.indices, id: \.self) { i in
                        HomeSceneLayerView(layer: SkinScenes.homeFront[i], t: t, refill: refill)
                    }
                }
                HomeReturnDimView(clock: app.clock).frame(width: m.size.width, height: m.size.height)   // S3: the home-return dim (MA §8.3 A1)
            }
            if parts >= HomeBuild.topBar {
                HomeTopBarView(onAvatar: { PayoutSequence.cancel(); app.router.go(.profile) },
                               onCoins: { app.router.go(.home(.normal, tab: .shop)) },
                               onLives: { HomeView.openLives(app) },
                               onSettings: { Task { @MainActor in _ = await app.popups.present(Popup<PopupResult>.settings) } })
            }
            if parts >= HomeBuild.events { HomeEventLayer() }                        // S3: Claw bar + event badges
        }
    }

    /// The scene (the back of home: its art, the main character, the centrepiece).
    @ViewBuilder private func scene(_ t: Tokens) -> some View {
            // back → front = skin/scenes.json `home.back` (SPEC-ui §2.2.1; R3 HOME "order_back_to_front"): the backdrop, the main
            // character's torso + head, his station, his arms (the hands rest on the rail), the floor, the stand, the centrepiece;
            // then the LEVEL plate and Play; `home.front` (the two characters in front of the stand's lower corners); the top bar.
            SceneLayer(size: m.size) {
                ForEach(SkinScenes.homeBack.indices, id: \.self) { i in
                    HomeSceneLayerView(layer: SkinScenes.homeBack[i], t: t, refill: refill)
                }
            }
    }
}

/// One layer of a home scene list (skin/scenes.json -> `SkinScenes`): a raster at its ui.json frame (or aspect-filled over its
/// rect), a puppet (whole, or the part set it names) at its rig placement, or the centrepiece rig at its frame.
private struct HomeSceneLayerView: View {
    let layer: SkinScenes.Layer
    let t: Tokens
    let refill: Int

    var body: some View {
        switch layer.kind {
        case .art(let art):
            if layer.fill {
                ArtImage(art: art, contentMode: .fill).frame(width: layer.rect.width, height: layer.rect.height)
            } else {
                ArtImage(art: art).placed(placedRect)
            }
        case .rig(let rig):
            Puppet(rigName: rig.folder, part: puppetPart)
        case .centrepiece(let rig):
            HomeSignpost(rigName: rig.folder, refill: refill)                        // A4: owner item 4 (Home/HomeScene.swift)
                .placed(placedRect)
        }
    }

    /// The layer's rect: its ui.json frames key (the scene data's rect is that key's default), or the rect itself.
    private var placedRect: CGRect { layer.frameKey.isEmpty ? layer.rect : t.frame(layer.frameKey, layer.rect) }

    private var puppetPart: PuppetPart {
        if !layer.only.isEmpty { return .only(Set(layer.only)) }
        if !layer.excluding.isEmpty { return .excluding(Set(layer.excluding)) }
        return .all
    }
}

/// FIX-2 A (A4-o1 / V3-08, "build home BEHIND Loading in slices"): home's first build cost ONE 156-185 ms main-thread frame
/// at the Loading → home cut (339-433 ms before A4). The router now mounts home hidden (parked, arrival 0) under Loading as the
/// warm-up starts and adds one slice per presented frame: the scene, the level controls + Diggers, the top bar, the event layer,
/// the nav bar, the Shop tab, the Leaderboard tab, the arrival hook. The cut only shows the built home. Any other home is built
/// whole (`limit` stays Int.max): the slices change WHEN home's parts are built, never what they draw.
@MainActor @Observable final class HomeBuild {
    static let shared = HomeBuild()
    static let scene = 1, controls = 2, topBar = 3, events = 4, nav = 5, shop = 6, leaderboard = 7, all = 8
    /// How many slices are mounted (Int.max: every part, the default).
    private(set) var limit = Int.max

    var building: Bool { limit < Self.all }

    func begin() { limit = 0 }
    func step() { if limit < Self.all { limit += 1 } }
    func finish() { if limit != Int.max { limit = Int.max } }
}

/// The LEVEL plate and Play for the next level: the only part of the home page that shows the level, so a new level
/// re-renders these two, not the page (FIX-A1).
private struct HomeLevelControls: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        let level = HomeLive.read(app).level
        let tag = HomeLevelInfo.tag(for: level, args: app.args)
        HomeLevelPlate(level: level, tag: tag)
        HomePlayButton(level: level, tag: tag) {
            if WeeklyTutorialGate.interceptsPlay(app) { return }                    // G2: the first Play at L50 (Game/EventsDirector.swift)
            app.router.go(.level(app.levelLaunch(for: level)))
        }
    }
}

/// Home's arrival work (FIX-A1: home is built once and parked between visits, so this runs on each ARRIVAL, a new
/// `HomeLive.arrival`, not on creation): the art check, the log line, the payout queue (S3), and once per launch the hidden
/// Shop / Leaderboard pages after the first idle stretch (`HomeTabsPremount`). Draws nothing.
private struct HomeArrival: View {
    let tab: HomeTab
    let labEntry: HomeEntry?
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let arrival = labEntry == nil ? HomeLive.shared.arrival : 1
        Color.clear
            .frame(width: 0, height: 0)
            .allowsHitTesting(false)
            .accessibilityHidden(true)
            .onChange(of: arrival, initial: true) {
                guard arrival != 0 else { return }                                   // built hidden, not arrived (FIX-A1)
                let entry = labEntry ?? HomeLive.shared.entry
                let level = HomeLive.read(app).level
                ArtStore.preload(HomeView.art)
                if HomeLive.shared.tabsMounted { HomeTabStrip.shared.warmUp() }          // A2: the pages drawn once
                Log.mark("home", "L\(level) \(HomeLevelInfo.tag(for: level, args: app.args).rawValue) tab \(tab.rawValue) entry \(HomeView.name(entry))")
                if tab == .home { PayoutSequence.arrive(app: app, entry: entry, metrics: m) }  // S3 (Home/PayoutSequence.swift)
            }
            // S3 (Home/HomeScene.swift): once per launch, on the first arrival that stays idle long enough
            .task(id: arrival) {
                if arrival != 0, !HomeLive.shared.tabsMounted, await HomeTabsPremount.wait(app) {
                    HomeLive.shared.mountTabs()
                    await FrameWaiter.frames(1)
                    HomeTabStrip.shared.warmUp()                                        // A2: the pages drawn once
                }
            }
    }
}

/// A4: the signpost centrepiece (R3), its idle loop and its refill (a light tick per board landing, `rewardPop` = R3's
/// "light 0.45": the home reward beats' own light style, motion-catalog §5.1 row 20).
private struct HomeSignpost: View {
    /// The centrepiece's rig folder (skin/scenes.json's `centrepiece` slot; ui.json puppet.<folder> + its `refill`).
    let rigName: String
    let refill: Int
    @Environment(AppModel.self) private var app

    var body: some View {
        if let rig = PuppetCache.rig(rigName) {
            let freeze = app.clock.freezeAt.flatMap { $0.sequence == "puppets" ? $0.t : nil }
            let file = app.tuning.ui.file
            HomeCentrepiece(rig: rig, motion: PuppetMotion(file, rig: rigName),
                            steps: SignpostRefill(file, rig: rigName), refill: refill, clock: app.clock,
                            animate: !app.args.capture || freeze != nil, freezeAt: freeze,
                            tick: { [app] k in app.haptics.play(.rewardPop, intensity: k) })
                .accessibilityHidden(true)
        }
    }
}

/// One home puppet at its rig placement (inside the scene canvas).
private struct Puppet: View {
    let rigName: String
    var part: PuppetPart = .all
    @Environment(AppModel.self) private var app

    var body: some View {
        if let rig = PuppetCache.rig(rigName) {
            let freeze = app.clock.freezeAt.flatMap { $0.sequence == "puppets" ? $0.t : nil }
            PuppetStage(rig: rig, motion: PuppetMotion(app.tuning.ui.file, rig: rigName), clock: app.clock,
                        animate: !app.args.capture || freeze != nil, freezeAt: freeze, part: part)
                .placed(CGRect(origin: rig.placement, size: rig.frame))
                .accessibilityHidden(true)
        }
    }
}

/// Rigs parsed once per launch.
@MainActor enum PuppetCache {
    private static var rigs: [String: PuppetRig] = [:]
    static func rig(_ name: String) -> PuppetRig? {
        if let r = rigs[name] { return r }
        do {
            let r = try PuppetRig.load(name)
            rigs[name] = r
            return r
        } catch {
            Log.error("home", "puppet \(name): \(error)")
            return nil
        }
    }
}

/// The next level's difficulty tag for the home look: the bundled level file's `tag` (L1 CONTENT ships them); a SHELL-private
/// launch flag `-pc.homeTag normal|hard|superHard` overrides it for captures while the level files are not bundled yet.
enum HomeLevelInfo {
    private static let lock = NSLock()
    nonisolated(unsafe) private static var cache: [Int: LevelTag] = [:]

    static func tag(for level: Int, args: LaunchArgs, bundle: Bundle = .main) -> LevelTag {
        if let raw = args.raw["pc.homeTag"], let t = LevelTag(label: raw) { return t }
        lock.lock(); defer { lock.unlock() }
        if let t = cache[level] { return t }
        var tag = LevelTag.normal
        for name in [String(format: "level_%04d", level), String(format: "level_%03d", level)] {
            if let url = bundle.url(forResource: name, withExtension: "json", subdirectory: "Levels"),
               let data = try? Data(contentsOf: url),
               let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                tag = LevelTag(label: obj["tag"] as? String) ?? .normal
                break
            }
        }
        cache[level] = tag
        return tag
    }

    /// FIX-2 A: a level's tag read OFF the main thread ahead of its home. The home arrival after a win read the NEXT level's
    /// file from disk (+ a JSON parse) in the arrival frame, under HomeLevelControls (build/p/FIX2/A/tp/base-tp1); the router
    /// calls this at the level cut, seconds before that home.
    static func prefetch(_ level: Int, args: LaunchArgs, bundle: Bundle = .main) {
        lock.lock()
        let have = cache[level] != nil
        lock.unlock()
        guard !have, level > 0 else { return }
        DispatchQueue.global(qos: .utility).async { _ = tag(for: level, args: args, bundle: bundle) }
    }

    /// Whether a level's tag is cached (tests).
    static func isCached(_ level: Int) -> Bool {
        lock.lock(); defer { lock.unlock() }
        return cache[level] != nil
    }
}

// MARK: - the tab push-slide (A2 FEEL-P, owner item 2)

/// The home tab strip's position (motion-catalog §6.1 / §11.3 R2). `position` is the strip's page index at x = 0 (shop 0, home 1,
/// leaderboard 2); the router moves it — animated on a tab change while home is up (`slide`), at once on a cut into home
/// (`jump`) — in the same main-actor turn as the tab itself, so the raised tab and the first moving frame share one commit.
/// Each page is placed by `StripSlot` from the ANIMATED position (x = (index − position) · width); `shown` says which pages are
/// drawn (never animated). The motion is SwiftUI's interpolation of that one value with `TabSlideCurve`; no page body runs
/// per frame (only the three slot modifiers, which set a transform). A sliding-out page stays built until the slide ends.
@MainActor @Observable final class HomeTabStrip {
    static let shared = HomeTabStrip()
    private(set) var position: CGFloat = 1
    /// The pages drawn: the current one at rest; during a slide every page the strip exposes on the way (both ends and, on a
    /// 2-page jump, Home in the middle). Set with no animation at the slide's start and back at its end.
    private(set) var shown: Set<HomeTab> = [.home]
    /// Set for a few frames at the first home arrival: every page is drawn once in place at alpha 0.002 (the first
    /// presentation of the Shop / Leaderboard layers is paid under the Loading cross-fade, not in a slide's first frames).
    private(set) var warming = false
    @ObservationIgnored private var warmed = false
    @ObservationIgnored private(set) var sliding = false
    @ObservationIgnored private var generation = 0
    @ObservationIgnored private var target: HomeTab = .home
    @ObservationIgnored private var waiters: [CheckedContinuation<Void, Never>] = []
    /// Measurement only (`-pc.tabLoop`): log the slide's first-turn cost (the SwiftUI update + the commit), `[PC][perf] cut …`.
    @ObservationIgnored var probeCommits = false

    static func index(_ t: HomeTab) -> Int { HomeTab.allCases.firstIndex(of: t) ?? 1 }

    /// A cut into home: the tab at once, no motion.
    func jump(to tab: HomeTab) {
        generation += 1
        target = tab
        sliding = false
        var t = Transaction(); t.disablesAnimations = true
        withTransaction(t) {
            if position != CGFloat(Self.index(tab)) { position = CGFloat(Self.index(tab)) }
            if shown != [tab] { shown = [tab] }
        }
        resumeWaiters()
    }

    /// A tab change while home is up: the push-slide from wherever the strip is (a tap during a slide retargets from the
    /// current position: SwiftUI adds the new offset animation to the running one).
    func slide(to tab: HomeTab, ui: UITuning) {
        guard tab != target else { return }
        let from = target
        let probe = CutProbe.start(.home(.normal, tab: tab), enabled: probeCommits)
        probe?.finishAfterCommit()
        generation += 1
        let gen = generation
        target = tab
        sliding = true
        let lo = min(Self.index(from), Self.index(tab)), hi = max(Self.index(from), Self.index(tab))
        let range = Set(HomeTab.allCases[lo...hi])
        if !range.isSubset(of: shown) {
            var t = Transaction(); t.disablesAnimations = true
            withTransaction(t) { shown.formUnion(range) }                   // drawn from the first moving frame
        }
        let curve = TabSlideCurve(duration: ui.tabSlideDuration, power: ui.tabSlidePower, lead: ui.tabSlideLead, table: ui.tabSlideTable)
        Log.mark("home", "tab slide \(from.rawValue) → \(tab.rawValue) (\(String(format: "%.3f", ui.tabSlideDuration)) s, p \(ui.tabSlidePower))")
        withAnimation(Animation(curve)) { position = CGFloat(Self.index(tab)) }
        Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(max(0, ui.tabSlideDuration - ui.tabSlideLead) * 1_000_000_000))
            await FrameWaiter.frames(1)
            guard let self, gen == self.generation else { return }
            self.sliding = false
            if self.shown != [tab] {
                var t = Transaction(); t.disablesAnimations = true
                withTransaction(t) { self.shown = [tab] }
            }
            Log.mark("home", "tab slide done \(tab.rawValue)")
            self.resumeWaiters()
        }
    }

    /// Once per launch, at the first home arrival with the tab pages built: each hidden page is drawn in place for 3 frames
    /// at alpha 0.002 (invisible), so Core Animation has rendered its layers before the first slide shows them.
    func warmUp() {
        guard !warmed else { return }
        warmed = true
        var t = Transaction(); t.disablesAnimations = true
        withTransaction(t) { warming = true }
        Task { @MainActor [weak self] in
            await FrameWaiter.frames(3)
            var t = Transaction(); t.disablesAnimations = true
            withTransaction(t) { self?.warming = false }
            Log.mark("home", "tab pages drawn once (warm-up)")
        }
    }

    /// Returns once no slide runs (a popup queued behind a tab tap shows when the slide has settled: v552's Weekly Contest
    /// dim came on the frame after the slide, motion-catalog §3.1).
    func settled() async {
        guard sliding else { return }
        await withCheckedContinuation { (c: CheckedContinuation<Void, Never>) in waiters.append(c) }
    }

    private func resumeWaiters() {
        let w = waiters
        waiters.removeAll()
        for c in w { c.resume() }
    }
}

/// The measured tab-slide curve (v582 R2, motion-catalog §11.3). With `table` (ui.json `transition.tabSlide.table`, the
/// default): the v582 slides themselves — the remaining fraction per 60 Hz frame from the last still frame, linearly
/// interpolated between frames (1- and 2-page slides share it within 0.0025). Without: the fitted model, remaining =
/// D·(1 − u)^p, u = t / T (T 0.488 s, p 2.51: RMS 0.62 pt). `lead` (ui.json, s): SwiftUI draws an animation's first frame at
/// t = 0 in the turn of the change (the frame of the raised tab's jump), where v582's first frame already shows the page 34 pt in.
/// A one-frame lead matched v582 frame for frame (≤ 0.35 pt, A2's slide_measure) but put the incoming page's first draw into the
/// tab change's frame: in Release on the sim 8 of 20 slides then had one 28-40 ms first frame (lead 0: 0 and 4 of 20), so the
/// shipped lead is 0 — the page follows the tab one frame later, on v582's curve.
struct TabSlideCurve: CustomAnimation {
    let duration: Double
    let power: Double
    let lead: Double
    var table: [Double] = []

    func progress(_ time: TimeInterval) -> Double? {
        let t = max(0, time + lead)
        if table.count > 1 {
            let x = t * 60
            if x >= Double(table.count - 1) { return nil }
            let i = Int(x), f = x - Double(i)
            return 1 - (table[i] + (table[i + 1] - table[i]) * f)
        }
        let u = t / max(duration, 0.001)
        if u >= 1 { return nil }
        return 1 - pow(1 - u, power)
    }

    func animate<V: VectorArithmetic>(value: V, time: TimeInterval, context: inout AnimationContext<V>) -> V? {
        guard let p = progress(time) else { return nil }
        return value.scaled(by: p)
    }
}

/// One page's place in the strip, from the strip's ANIMATED position: x = (index − position) · width (`pinned`: in place, for
/// the warm-up draw). Only the transform is animated; whether the page is drawn is `HomeTabStrip.shown`, never animated.
private struct StripSlot: ViewModifier, Animatable {
    var position: CGFloat
    let index: CGFloat
    let width: CGFloat
    var pinned = false

    var animatableData: CGFloat {
        get { position }
        set { position = newValue }
    }

    func body(content: Content) -> some View {
        content.offset(x: pinned ? 0 : (index - position) * width)
    }
}

/// One page of the strip: placed by `StripSlot`, drawn while the strip shows it (alpha 0.002 in place during the warm-up).
private struct HomeTabPage<Content: View>: View {
    let page: HomeTab
    let width: CGFloat
    @ViewBuilder let content: Content

    var body: some View {
        let strip = HomeTabStrip.shared
        let shown = strip.shown.contains(page)
        let warm = strip.warming && !shown
        content
            .modifier(StripSlot(position: strip.position, index: CGFloat(HomeTabStrip.index(page)), width: width, pinned: warm))
            .animation(nil) { $0.opacity(shown ? 1 : (warm ? 0.002 : 0)) }
    }
}

// MARK: - the parked home (FIX-A1)

/// The player state home's views read, through this proxy. Home is built once and PARKED (hidden, still mounted) under
/// every other screen (Router `cutLayers`); Observation re-renders a view when anything its body read changes, so if
/// home's views read the store itself, every store write during a level (the attempt, a booster, the win) would re-render
/// the hidden home in a play frame. This proxy follows the store only while home is shown: parked, it keeps the last
/// copy and its readers stay untouched; `resume()` on the next arrival brings the live state back in one change.
@MainActor @Observable final class HomeLive {
    static let shared = HomeLive()
    private(set) var state: PlayerState?
    /// false while home is parked (its timelines pause on it).
    private(set) var active = true
    /// The latest arrival (the router's layer number; 0 = built hidden, not arrived) and its entry (the payout's source).
    private(set) var arrival = 0
    @ObservationIgnored private(set) var entry: HomeEntry = .normal
    /// The hidden Shop / Leaderboard pages are built (once per launch: they stay with home).
    private(set) var tabsMounted = false
    @ObservationIgnored private weak var store: PlayerStore?
    @ObservationIgnored private var generation = 0
    /// The countdowns' clock: live while home is shown; while parked, frozen at the values they last drew (the lives pill's
    /// wall time, the event layer's timeline date), so a parked home draws no new time string and parking re-renders
    /// nothing (these are not observed: reading them registers no dependency).
    @ObservationIgnored var livesDrawnAt: Date?
    @ObservationIgnored var eventsDrawnAt: Date?
    @ObservationIgnored private var frozenLives: Date?
    @ObservationIgnored private var frozenEvents: Date?

    /// The lives pill's wall clock (records what it drew while live).
    func livesClock(_ app: AppModel) -> Date {
        if let f = frozenLives { return f }
        let now = app.clock.wallClock()
        livesDrawnAt = now
        return now
    }

    /// The event layer's timeline date (records what it drew while live).
    func eventsClock(_ date: Date) -> Date {
        if let f = frozenEvents { return f }
        eventsDrawnAt = date
        return date
    }

    /// What home's views read (the store itself until the router attached the proxy: previews, labs).
    static func read(_ app: AppModel) -> PlayerState { shared.state ?? app.store.state }

    /// The router, once at launch.
    func attach(_ store: PlayerStore) {
        self.store = store
        state = store.state
        follow()
    }

    /// Home is parked: keep the copy, stop following, pause the timelines.
    func park() {
        guard active else { return }
        frozenLives = livesDrawnAt ?? Date()
        frozenEvents = eventsDrawnAt ?? Date()
        active = false
        generation += 1
    }

    /// Home shows again: the live state (one change) and follow the store.
    func resume() {
        guard let store else { return }
        frozenLives = nil
        frozenEvents = nil
        if !active { active = true }
        // FIX-2 A (A3-o0): only a CHANGED state is written — every reader of `state` (the top bar, the level controls, the
        // event layer, the Shop and Leaderboard tabs) re-renders on a write, equal or not; `prepareArrival` has usually
        // written it a frame before the cut
        if state != store.state { state = store.state }
        generation += 1
        follow()
    }

    /// FIX-2 A (A3-o0, "pre-apply home model changes a run-loop turn before the cut"): while home is still PARKED (hidden
    /// under the level / page it returns from), its copy takes the live state now, so the re-render of what changed (coins,
    /// level, badges) is paid in a frame where home is invisible, and the cut's frame only shows it. Timelines stay frozen
    /// (they resume at the arrival). No-op while home is shown.
    @discardableResult
    func prepareArrival() -> Bool {
        guard !active, let store, state != store.state else { return false }
        state = store.state
        return true
    }

    /// Parked with a copy that differs from the store (the router refreshes it a frame before the cut).
    var arrivalStale: Bool {
        guard !active, let store else { return false }
        return state != store.state
    }

    /// The router: home is shown as a new arrival (a hard cut, or the cross-fade out of Loading).
    func arrive(_ entry: HomeEntry, arrival: Int) {
        resume()
        self.entry = entry
        self.arrival = arrival
    }

    /// Now, not a turn later: a writer that changes the store AND a display counter in one turn (the payout takes the
    /// banked coins and sets the coins in flight — `CoinPillDisplay.shown` subtracts both) syncs here, so home never draws
    /// one frame of the new counter against the old state.
    func sync() {
        guard active, let store, state != store.state else { return }
        state = store.state
    }

    func mountTabs() { if !tabsMounted { tabsMounted = true; Log.mark("home", "tab pages mounted (hidden)") } }

    private func follow() {
        guard let store, active else { return }
        let gen = generation
        withObservationTracking { _ = store.state } onChange: { [weak self] in
            Task { @MainActor [weak self] in
                guard let self, self.active, gen == self.generation else { return }
                if self.state != store.state { self.state = store.state }
                self.follow()
            }
        }
    }
}
