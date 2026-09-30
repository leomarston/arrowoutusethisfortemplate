import SwiftUI
import UIKit
import PathCore

// WP0 → G1 (SPEC-architecture §3.2, §6.1, §8.5, §8.6). The composition root + the boot sequence. GAME owns this file from
// G1 on: the rules (C2's RulesTuning, C3's EconomyRules), the level library + C4's LevelProvider (authored levels, then the
// generated ones off the main thread, one level ahead), the offline social world (the events' RivalProvider), the launch
// reconcile (a killed attempt = a loss, refills), the level lifecycle forwarding (background hold + Pause on return) and
// the autoplayer. Owners plug their implementations in through the entry points of App/Contracts/* (BoardEntry,
// AudioEntry, ShellEntry, SocialEntry, GameEntry) without editing this file; the boot log names every default still in use.

/// The app-wide services every owner factory receives. Built before the owners' objects, so a factory can use any of them.
@MainActor struct AppContext {
    let args: LaunchArgs
    let tuning: Tuning
    let clock: MotionClock
    let store: PlayerStore
    let hud: HUDModel
    let anchors: AnchorRegistry
    let perf: PerfMonitor
    let latency: LatencyProbe
    let bundle: Bundle
}

/// Injected with `.environment(app)`; views read it with `@Environment(AppModel.self)`.
@MainActor @Observable final class AppModel {
    enum BootPhase: Equatable { case booting, ready }
    struct BootStep: Equatable { let name: String; let seconds: Double }

    let context: AppContext
    var args: LaunchArgs { context.args }
    var tuning: Tuning { context.tuning }
    var clock: MotionClock { context.clock }
    var store: PlayerStore { context.store }
    var hud: HUDModel { context.hud }
    var anchors: AnchorRegistry { context.anchors }
    var perf: PerfMonitor { context.perf }
    var latency: LatencyProbe { context.latency }
    var bundle: Bundle { context.bundle }

    let board: any BoardControlling            // created at boot, never destroyed (§5.1)
    let audio: any AudioPlaying
    let haptics: any HapticPlaying
    let router: any Routing
    let popups: any PopupPresenting
    let toasts: any ToastPresenting
    let shop: any StoreServicing
    let fx: any FXPlaying

    // G1: rules and content (§4.4–§4.14)
    /// C2's rule table (rules.json + `-pc.tune rules.*`).
    @ObservationIgnored let rules: RulesTuning
    /// C3's economy / lives / streak / Claw / shop / events table (rules.json C3 sections + social.json events).
    @ObservationIgnored let economy: EconomyRules
    /// The bundled levels (lazy decode; nil when bundle/Levels is missing or unreadable — logged).
    @ObservationIgnored let library: LevelLibrary?
    /// Authored levels, then the generated ones (C4, off the main thread, one level ahead).
    @ObservationIgnored let provider: LevelProvider?
    /// The offline world (the events' RivalProvider, §4.10–§4.11), built off the main thread during Loading.
    @ObservationIgnored private(set) var socialWorld: SocialWorld?
    @ObservationIgnored private var socialTask: Task<SocialWorld?, Never>?
    #if DEBUG || PC_MEASURE
    /// `-pc.autoplay 1`: the bot that plays through the real UI (§8.4). Debug / Measure only (Game/AutoPlayer.swift).
    @ObservationIgnored private(set) var autoplayer: AutoPlayer?
    #endif
    /// The running Play (set by GameController.start, cleared at its teardown).
    @ObservationIgnored weak var game: GameController?
    /// Template phase 2: the active puzzle module's app half and its board behind the generic contract
    /// (App/Contracts/PuzzleBoardContract.swift; `ActivePuzzle.entry` picks the module). Set once at the end of `init`.
    @ObservationIgnored private(set) var puzzle: (any PuzzlePlugin)!
    @ObservationIgnored private(set) var puzzleBoard: (any PuzzleBoard)!

    private(set) var bootPhase: BootPhase = .booting
    /// PostScript name → registered (UIAppFonts), checked at boot.
    private(set) var fonts: [String: Bool] = [:]
    @ObservationIgnored private(set) var bootSteps: [BootStep] = []
    /// SHELL's root (or the WP0 placeholder), built exactly once at the end of `init`: the App body re-evaluates on
    /// scene-phase changes and must not rebuild it.
    @ObservationIgnored private(set) var rootView = AnyView(EmptyView())
    @ObservationIgnored private var bootStarted = false
    @ObservationIgnored let launchUptime: TimeInterval
    /// The scene went to the background since the last `.active` (G2: an inactive moment is not a background, §8.6).
    @ObservationIgnored private var wasInBackground = false
    @ObservationIgnored private let sessions: [SessionPlan]

    /// The fonts every text role uses (design/fonts.md; Info.plist UIAppFonts).
    nonisolated static let fontNames = SkinFonts.postScriptNames              // skin/fonts.json

    init(args: LaunchArgs = .current, bundle: Bundle = .main) {
        let t0 = ProcessInfo.processInfo.systemUptime
        launchUptime = t0
        let version = bundle.infoDictionary?["CFBundleShortVersionString"] as? String ?? "?"
        let build = bundle.infoDictionary?["CFBundleVersion"] as? String ?? "?"
        let argText = args.raw.sorted { $0.key < $1.key }.map { "-\($0.key) \($0.value)" }.joined(separator: " ")
        Log.mark("boot", "\(Brand.name) \(version) (\(build)) args: \(argText.isEmpty ? "none" : argText)")

        let clock = MotionClock(args: args)
        // B1: the weekly event rotation runs the v552 plan under -pc.uitest / -pc.capture unless a rotation scenario asks
        // (EventRotationPolicy); Up & Away waits for its art in Release
        let tuning = Tuning.load(bundle: bundle, tune: EventRotationPolicy.tune(args))
        let (rules, ruleProblems) = RulesTuning.load(json: tuning.rules.data, overrides: tuning.rules.overrides)
        var (economy, econProblems) = EconomyRules.load(rules: tuning.rules.data, social: tuning.social.file.data,
                                                        overrides: tuning.rules.overrides)
        EventRotationPolicy.apply(&economy)
        for p in ruleProblems + econProblems { Log.error("tuning", p) }
        self.rules = rules
        self.economy = economy
        let t1 = ProcessInfo.processInfo.systemUptime

        // 1. The player's state (+ the launch reconcile: refills, the end of ∞, a killed attempt = a loss, §8.5 / §8.6).
        let now = clock.wallClock()
        let store = PlayerStore(args: args, now: now, bundle: bundle, homeSeenFromLevel: tuning.game.ftueChainUntilLevel,
                                rules: economy)
        let notices = store.mutateAndSave { Economy.reconcileOnLaunch(&$0, now: now, rules: economy) }
        for n in notices { Log.mark("store", "launch reconcile: \(Self.describe(n))") }
        let t2 = ProcessInfo.processInfo.systemUptime

        // 2. The level library (index + small files; levels decode lazily) and the provider.
        var library: LevelLibrary?
        if let folder = bundle.resourceURL?.appendingPathComponent("Levels") {
            do {
                let lib = try LevelLibrary.load(folder: folder)
                for p in lib.problems { Log.error("levels", p) }
                library = lib
            } catch {
                Log.error("levels", "\(error)")
            }
        }
        self.library = library
        let provider = library.map { LevelProvider(library: $0) }
        provider?.onProduced = { r in
            Log.mark("level", String(format: "generated L%d in %.1f ms (%@, seeds %d, validate %.1f ms)", r.level, r.totalMs,
                                     r.route.rawValue, r.seedsTried, r.validateMs))
        }
        self.provider = provider
        sessions = library?.sessions ?? Self.loadSessions(bundle: bundle)
        let t3 = ProcessInfo.processInfo.systemUptime

        context = AppContext(args: args, tuning: tuning, clock: clock, store: store, hud: HUDModel(),
                             anchors: AnchorRegistry(), perf: PerfMonitor(hitchMs: tuning.board.hitchMs),
                             latency: LatencyProbe(), bundle: bundle)

        board = BoardEntry.makeBoard(context)
        audio = AudioEntry.makeAudio(context)
        haptics = AudioEntry.makeHaptics(context)
        router = ShellEntry.makeRouter(context)
        popups = ShellEntry.makePopups(context)
        toasts = ShellEntry.makeToasts(context)
        shop = ShellEntry.makeStore(context)
        fx = ShellEntry.makeFX(context)

        audio.apply(settings: store.state.settings)
        haptics.enabled = store.state.settings.haptic
        let t4 = ProcessInfo.processInfo.systemUptime
        bootSteps = [BootStep(name: "tuning", seconds: t1 - t0), BootStep(name: "store", seconds: t2 - t1),
                     BootStep(name: "levels", seconds: t3 - t2), BootStep(name: "services", seconds: t4 - t3)]
        Log.mark("boot", "tuning files: \(tuning.loadedFiles.joined(separator: ",")) · levels: authored "
                 + "\(library?.authoredCount ?? 0), sessions \(sessions.count), unlocks \(library?.unlocks.count ?? 0), "
                 + "tutorials \(library?.tutorials.count ?? 0) · lives refill \(Int(economy.lives.refillSeconds)) s · "
                 + "bundle: \(Self.bundleSummary(bundle).map { "\($0.0) \($0.1)" }.joined(separator: ", "))")

        // The world (≈ 0.5 MB of names) is parsed off the main thread while Loading covers the screen.
        let seed = store.state.installSeed
        let config = tuning.social.config
        let socialFolder = bundle.resourceURL?.appendingPathComponent("Social")
        let home = Self.socialHome(store.state.social.country, forced: args.raw["pc.socialCountry"], config: config)
        socialTask = Task.detached(priority: .utility) { () -> SocialWorld? in
            Self.makeWorld(seed: seed, config: config, folder: socialFolder, home: home, warm: true)
        }
        #if DEBUG || PC_MEASURE
        if args.autoplay { autoplayer = AutoPlayer(args: args, tuning: tuning) }
        #else
        if args.autoplay { Log.error("autoplay", "-pc.autoplay: no autoplayer in this build (Release); it runs in Debug / Measure") }
        #endif
        puzzle = ActivePuzzle.entry.makePlugin(self)
        puzzleBoard = ActivePuzzle.entry.makeBoard(self)
        Log.mark("boot", "puzzle module \(puzzle.id) (contract v\(PuzzleContract.version)): "
                 + "boosters \(puzzle.capabilities.boosters.map(\.id.rawValue).joined(separator: ",")), "
                 + "HUD \(puzzle.capabilities.hud.map(\.rawValue).joined(separator: ","))")
        rootView = ShellEntry.makeRoot(self)
    }

    // MARK: boot (§8.5)

    /// Runs once, behind the Loading screen: warm-ups in parallel (audio, haptics, the board, fonts, the first levels,
    /// the social world), the Loading minimum, then the first screen. Step 4 is G2's (G2App: the first launch's writes and
    /// the notification prompt over Loading, which Loading waits for; the home queue and the event glue are installed).
    func boot() async {
        guard !bootStarted else { return }
        bootStarted = true
        let start = ProcessInfo.processInfo.systemUptime
        Log.mark("boot", "boot sequence started (\(String(format: "%.3f", start - launchUptime)) s after launch)")

        // 4 (started now, over Loading): G2's first-launch writes and the notification prompt (FTUEDirector, NotificationPrompt)
        let prompt = G2App.bootBegan(self)

        // 3. Warm-ups in parallel, capped (§6.1: Loading stays until the boot finishes, cap ui.loading.capSeconds).
        haptics.prepare()
        fonts = Dictionary(uniqueKeysWithValues: Self.fontNames.map { ($0, UIFont(name: $0, size: 12) != nil) })
        Log.mark("boot", "fonts " + Self.fontNames.map { "\($0) \(fonts[$0] == true ? "ok" : "MISSING")" }.joined(separator: ", "))
        for (name, ok) in fonts where !ok { Log.error("boot", "font \(name) is not registered (UIAppFonts)") }
        prefetchLevels(around: store.state.level)
        let cap = tuning.ui.loadingCapSeconds
        // the world is picked up whenever its parse ends (never built on the main thread when a hook first needs it)
        if let social = socialTask {
            Task { @MainActor [weak self] in
                if let w = await social.value, self?.socialWorld == nil { self?.socialWorld = w }
            }
        }
        let warm = Task { @MainActor [audio, board] in
            async let a: Void = audio.warmUp()
            async let b: Void = board.prepare()
            _ = await (a, b)
        }
        // FIX-B (V1 ShellS2UITests:31, Loading up 29 s): a REAL race. The former withTaskGroup never capped: it awaits every
        // child before returning and `await warm.value` ignores cancellation (V3 r2 log: "warmup 8.800 s" at the 4 s cap).
        let finished = await Self.completes(warm, within: cap)
        if !finished {
            // the board's frame-paced part ends now; its sprite decode + art (the level needs them) finish first; the audio
            // engine keeps booting in the background (a cue before it runs is dropped, never late)
            let t0 = ProcessInfo.processInfo.systemUptime
            await (board as? BoardEngine)?.hurryWarmUp()
            Log.error("launch", String(format: "boot work hit the %.1f s cap: warm-up still running; the board's rest took %.3f s "
                                       + "more, audio continues in the background (§6.1)", cap, ProcessInfo.processInfo.systemUptime - t0))
        }
        let warmed = ProcessInfo.processInfo.systemUptime
        bootSteps.append(BootStep(name: "warmup", seconds: warmed - start))

        // The Loading minimum (ui.json loading.minSeconds), measured from launch.
        let minimum = tuning.ui.loadingMinSeconds
        let shown = warmed - launchUptime
        if shown < minimum { try? await Task.sleep(nanoseconds: UInt64((minimum - shown) * 1_000_000_000)) }
        let end = ProcessInfo.processInfo.systemUptime
        bootSteps.append(BootStep(name: "loadingHold", seconds: end - warmed))

        // 4 (end): Loading stays up while the iOS notification alert is (first launch only).
        await G2App.bootEnding(self, prompt: prompt)

        // 5. The first screen.
        let first = firstScreen()
        let steps = bootSteps.map { "\($0.name) \(String(format: "%.3f", $0.seconds)) s" }.joined(separator: " ")
        Log.mark("launch", "cold launch summary \(steps) total \(String(format: "%.3f", end - launchUptime)) s → \(first.logName)")
        bootPhase = .ready
        router.go(first)
        if let p = args.popup {
            Log.mark("boot", "-pc.popup \(p.id)\(p.variant.map { ":" + $0 } ?? ""): presented by SHELL's router (§9.1)")
        }
        #if DEBUG || PC_MEASURE
        autoplayer?.start(self)
        #endif
    }

    /// Where the app goes after Loading: `-pc.go`, else the FTUE rule (a fresh install goes straight into the first
    /// session, VERIFIED tutorials §1), else home.
    func firstScreen() -> Screen {
        switch args.go {
        case .home?, .settings?: return .home(.normal, tab: .home)
        case .shop?: return .home(.normal, tab: .shop)
        case .leaderboard?: return .home(.normal, tab: .leaderboard)
        case .profile?: return .profile
        case .level?: return .level(levelLaunch(for: store.state.level))
        case .event(let e)?: return EventScreen(rawValue: e).map { .event($0) } ?? .home(.normal, tab: .home)
        case .lab(let name)?:
            #if DEBUG || PC_MEASURE
            return LabID(rawValue: name).map { .lab($0) } ?? .home(.normal, tab: .home)
            #else
            // the labs are Debug / Measure only: the store build ignores `-pc.go <lab>` and starts as with no `-pc.go`
            Log.error("boot", "-pc.go \(name): no debug screen in this build (Release); labs run in Debug / Measure")
            return store.state.homeSeen ? .home(.normal, tab: .home) : .level(levelLaunch(for: store.state.level))
            #endif
        case nil: return store.state.homeSeen ? .home(.normal, tab: .home) : .level(levelLaunch(for: store.state.level))
        }
    }

    /// The session that contains `level` (bundle Levels/sessions.json), else a one-stage session.
    func levelLaunch(for level: Int, isRetry: Bool = false) -> LevelLaunch {
        if let plan = sessions.first(where: { $0.levels.contains(level) }) {
            let firstStage = args.stage.map { min(max($0, 0), plan.levels.count - 1) } ?? plan.levels.firstIndex(of: level) ?? 0
            return LevelLaunch(session: plan.id, levels: plan.levels, isRetry: isRetry, firstStage: firstStage)
        }
        return LevelLaunch(session: "L\(level)", levels: [level], isRetry: isRetry, firstStage: 0)
    }

    /// True when `task` ends within `seconds`, false at `seconds` (the task keeps running). Two racers, one answer.
    static func completes(_ task: Task<Void, Never>, within seconds: Double) async -> Bool {
        await withCheckedContinuation { (c: CheckedContinuation<Bool, Never>) in
            let once = Once()
            Task { @MainActor in await task.value; once.run { c.resume(returning: true) } }
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: UInt64(max(0, seconds) * 1_000_000_000))
                once.run { c.resume(returning: false) }
            }
        }
    }

    // MARK: levels (C1 library, C4 provider)

    /// The session plan of a launch: its sessions.json entry, else a one-stage session.
    func sessionPlan(for launch: LevelLaunch) -> SessionPlan {
        if let p = sessions.first(where: { $0.id == launch.session }) { return p }
        if let first = launch.levels.first, let p = sessions.first(where: { $0.levels.contains(first) }) { return p }
        return SessionPlan(id: launch.session, levels: launch.levels)
    }

    /// Level n: authored (decoded once, cached) or generated (validated, off the main thread one level ahead).
    func level(_ n: Int) -> LevelSpec? {
        guard let provider else { return nil }
        return provider.level(n)
    }

    /// One level ahead (C4 request, L1 request): the generated levels of the next session start generating on the
    /// provider's queue, the authored ones are decoded (and cached) on a utility queue, and the board decodes their
    /// sprites — so no level start parses JSON or generates on the main thread.
    func prefetchLevels(around level: Int) {
        guard let library, let provider else { return }
        let here = library.session(containing: max(1, level))
        let next = library.session(containing: library.nextLevel(after: here))
        let levels = Array(Set(here.levels + next.levels)).sorted()
        for n in levels where provider.isGenerated(n) { provider.prefetch(n) }
        let authored = levels.filter { !provider.isGenerated($0) }
        Task { @MainActor [weak self] in
            let specs = await Task.detached(priority: .utility) { authored.compactMap { library.authored($0) } }.value
            self?.board.preload(specs)
        }
    }

    // MARK: the social world (the events' opponents)

    /// The world for the event hooks. Built off the main thread during Loading; if a hook needs it before that finished
    /// (a very early win), it is built here once (logged).
    var rivals: RivalProvider {
        if let w = socialWorld { return w }
        let t0 = ProcessInfo.processInfo.systemUptime
        let home = Self.socialHome(store.state.social.country, forced: args.raw["pc.socialCountry"], config: tuning.social.config)
        let w = Self.makeWorld(seed: store.state.installSeed, config: tuning.social.config,
                               folder: bundle.resourceURL?.appendingPathComponent("Social"), home: home, warm: false) ?? SocialWorld(
                                   installSeed: store.state.installSeed, config: tuning.social.config, names: NameBank())
        socialWorld = w
        Log.mark("social", String(format: "world built on demand in %.1f ms", (ProcessInfo.processInfo.systemUptime - t0) * 1000))
        return w
    }

    /// B2: the home country the world is built for — the frozen one, else what SocialModel will freeze (`-pc.socialCountry`,
    /// else the device region resolved on the model's region map: a territory → its board's country, a numeric region → its
    /// representative, an unknown 2-letter code → itself = a LOCAL partition).
    nonisolated static func socialHome(_ frozen: String?, forced: String?, config: SocialConfig) -> String {
        if let forced, forced.count == 2 { return forced.uppercased() }
        if let frozen { return frozen }
        return config.model.homeBoard(forRegion: Locale.current.region?.identifier, fallback: config.fallbackCountry).iso
    }

    /// The world, with the home country passed in (B2, social-intl §6.4: an unknown code's LOCAL partition is keyed by it and
    /// built HERE, behind Loading, never cold on the first board open). `warm` also builds the cohort table to now and the
    /// home country's board index (the launch path, off the main thread).
    nonisolated private static func makeWorld(seed: UInt64, config: SocialConfig, folder: URL?, home: String, warm: Bool) -> SocialWorld? {
        let t0 = ProcessInfo.processInfo.systemUptime
        var names = NameBank()
        if let folder {
            do { names = try NameBank.load(folder: folder) } catch {
                Log.error("social", "Social/social_names.json: \(error) — the world's players keep their player_ names")
            }
        }
        var cfg = config
        cfg.homeCountry = home
        let w = SocialWorld(installSeed: seed, config: cfg, names: names)
        let t1 = ProcessInfo.processInfo.systemUptime
        if warm { w.warmUp(to: SocialTime(seconds: Int64(Date().timeIntervalSince1970)), country: home) }
        Log.mark("social", String(format: "world ready in %.1f ms (names %@, home %@, warm-up %.1f ms)", (t1 - t0) * 1000,
                                  names.isEmpty ? "empty" : "loaded", home, (ProcessInfo.processInfo.systemUptime - t1) * 1000))
        return w
    }

    // MARK: lifecycle (§8.6)

    func scenePhaseChanged(_ phase: ScenePhase) {
        switch phase {
        case .background:
            Log.mark("app", "background")
            wasInBackground = true
            game?.appDidEnterBackground()
            store.saveNow()
            store.flush()
        case .active:
            // G2: `.active` also follows a mere `.inactive` moment (the first launch's notification alert, Control Centre):
            // only a real return from the background holds the level and brings up Pause (§8.6). Found by the fresh-install
            // no-argument FTUE test: answering the alert paused "Levels 1-4" under a Pause popup.
            Log.mark("app", wasInBackground ? "active (back from the background)" : "active (after an inactive moment: no Pause)")
            if wasInBackground { game?.appDidBecomeActive() }
            wasInBackground = false
        default:
            break
        }
        G2App.sceneChanged(self, phase)                     // G2: local notifications, the events' refresh on foreground
    }

    // MARK: helpers

    private static func describe(_ n: LaunchNotice) -> String {
        switch n {
        case .clockBehind(let s): return "the device clock is \(s) s behind the high-water mark"
        case .livesRefilled(let a, let b): return "lives \(a) → \(b)"
        case .unlimitedEnded: return "unlimited lives ended"
        case .killedAttempt(let levels, let loss, let out):
            return "killed attempt L\(levels.first ?? 0) \(loss ? "counted as a loss" : "forgotten") (\(out.count) event outcomes)"
        }
    }

    private static func loadSessions(bundle: Bundle) -> [SessionPlan] {
        struct File: Decodable { let sessions: [SessionPlan] }
        guard let url = bundle.url(forResource: "sessions", withExtension: "json", subdirectory: "Levels") else { return [] }
        do { return try JSONDecoder().decode(File.self, from: Data(contentsOf: url)).sessions } catch {
            Log.error("boot", "Levels/sessions.json does not decode: \(error)")
            return []
        }
    }

    /// File counts of the bundle's resource folders (boot log, WP0 placeholder).
    static func bundleSummary(_ bundle: Bundle) -> [(String, Int)] {
        guard let root = bundle.resourceURL else { return [] }
        return ["UI", "Art", "Tuning", "Fonts", "Levels", "Social", "Sounds", "Music"].map { folder in
            let dir = root.appendingPathComponent(folder)
            let items = (try? FileManager.default.subpathsOfDirectory(atPath: dir.path)) ?? []
            return (folder, items.filter { !$0.hasPrefix(".") && !$0.contains("/.") && !$0.hasSuffix("/") }
                .filter { ($0 as NSString).pathExtension != "" }.count)
        }
    }
}
