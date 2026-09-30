import XCTest
import UIKit
@testable import ArrowOut
import PathCore
import SortPuzzle

/// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §8c): the shell gaps a second genre needed, closed while ArrowEscape
/// stays the active module. SortPuzzle is driven through its plugin, its real board and the unchanged GameController:
///  - the HUD shows the widgets the module declares (`capabilities.hud`): no timer and no hearts for SortPuzzle, its progress
///    counter in slot 1, fed by `goalProgress` (never written on a tap frame); the reference HUD model is unchanged;
///  - a `stuck` / `outOfMoves` offer gets its own popup texts (title, body, button) and a grant line from the grant
///    ("+1 Tube" worded by the module, "+5 Moves" by the shell), in the string catalogue; timer / hearts keep OutOfTimePopup;
///  - module boosters (`undo`, `extraTube`): stock, packs and texts from sort.json, the corners built from the declared list,
///    no art in the skin → the name face (optional slots), the reference boosters' art and labels unchanged;
///  - only the active module's content / engine is built (the entry points' boot hooks), and a board that does not meter its
///    own frames is metered by the Play's generic frame hook (`boardFrame` → PerfMonitor / LatencyProbe).
@MainActor final class ModuleShellTests: XCTestCase {

    static let screen = CGSize(width: 393, height: 852)

    func sortRules() -> SortRules {
        SortPuzzlePlugin.loadRules(TuningFile.load(SortPuzzleEntry.tuningFile, bundle: .main, tune: [:]))
    }

    func makeBoard() -> SortPuzzleBoard {
        SortPuzzleBoard(tuning: SortBoardTuning(file: TuningFile.load(SortPuzzleEntry.tuningFile, bundle: .main, tune: [:])))
    }

    /// The reference economy (rules.json + social.json), as AppModel loads it before a module's boosters are added.
    func referenceEconomy(_ tuning: Tuning) -> EconomyRules {
        EconomyRules.load(rules: tuning.rules.data, social: tuning.social.file.data, overrides: tuning.rules.overrides).rules
    }

    struct Rig {
        let game: GameController
        let board: SortPuzzleBoard
        let store: PlayerStore
        let hud: HUDModel
        let perf: PerfMonitor
        let popups: GameControllerTests.FakePopups
    }

    /// The unchanged GameController over SortPuzzle's plugin (+ its sort.json boosters) and real board, the economy with the
    /// module's boosters added as AppModel adds them, and G2's BoosterDirector.
    func makeRig(levels: [Int] = [2]) -> Rig {
        let args = LaunchArgs(pairs: ["pc.seed": "7", "pc.coins": "5000"])
        let tuning = Tuning.load(bundle: .main)
        let rules = RulesTuning.load(json: tuning.rules.data, overrides: tuning.rules.overrides).rules
        let boosters = SortPuzzleEntry.moduleBoosters(bundle: .main, tune: [:])
        var economy = referenceEconomy(tuning)
        economy.addModuleBoosters(boosters)
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("tpl5-\(UUID().uuidString)")
        let store = PlayerStore(args: args, now: Date(), bundle: .main, directory: dir, rules: economy, debounce: 0.05)
        let log = GameControllerTests.Recorder()
        let board = makeBoard()
        let popups = GameControllerTests.FakePopups(log)
        let hud = HUDModel()
        let perf = PerfMonitor()
        let plugin = SortPuzzlePlugin(rules: sortRules(), meta: rules.meta, boosters: boosters)
        let plan = SessionPlan(id: "S\(levels[0])", levels: levels)
        let services = GameServices(
            args: args, tuning: tuning, rules: rules.meta, economy: economy, clock: MotionClock(args: args), store: store, hud: hud,
            board: board, puzzle: plugin,
            audio: GameControllerTests.FakeAudio(log), haptics: GameControllerTests.FakeHaptics(log), popups: popups,
            fx: GameControllerTests.FakeFX(log), router: GameControllerTests.FakeRouter(), latency: LatencyProbe(), perf: perf,
            plan: { _ in plan },
            rivals: { SocialWorld(installSeed: 7, config: .default, names: NameBank()) },
            screenSize: { ModuleShellTests.screen },
            screenAfterWin: { .home(.afterWin($0), tab: .home) },
            screenAfterLoss: { GameServices.defaultAfterLoss($0, tryAgain: $1, homeSeen: true) },
            levelStarted: { _ in }, app: nil)
        let game = GameController(LevelLaunch(session: plan.id, levels: plan.levels), services: services,
                                  directors: { [BoosterDirector($0)] })
        return Rig(game: game, board: board, store: store, hud: hud, perf: perf, popups: popups)
    }

    private var frameTime = 9_000.0
    func frames(_ r: Rig, _ n: Int, dt: Double = 1.0 / 60) {
        for _ in 0..<n {
            frameTime += dt
            r.board.advance(dt)
            r.game.boardFrame(timestamp: frameTime, targetTimestamp: frameTime + dt)
        }
    }

    /// Plays the session's hint until one pour has landed in the session's history.
    func pourOnce(_ r: Rig) throws {
        let s = try XCTUnwrap(r.game.session as? SortPuzzleSession)
        var taps = 0
        while s.history.isEmpty && taps < 6 {
            frames(r, 1)
            let t = try XCTUnwrap(s.hint())
            XCTAssertTrue(r.board.performTap(on: t))
            taps += 1
        }
        XCTAssertEqual(s.history.count, 1, "one pour")
    }

    // MARK: 1. the HUD from the capabilities

    func testHUDWidgetListFollowsTheCapabilities() {
        // the reference game: the HUD model's default IS ArrowEscape's declaration (timer + hearts, no counter)
        XCTAssertEqual(HUDModel().widgets, ArrowEscapeModule.capabilities.hud)
        XCTAssertEqual(HUDCounter.placed(ArrowEscapeModule.capabilities.hud), [])
        // SortPuzzle: the progress counter in slot 1 (the timer's place), no timer, no hearts
        XCTAssertEqual(SortPuzzleModule.capabilities.hud, [.progress])
        XCTAssertEqual(HUDCounter.placed(SortPuzzleModule.capabilities.hud), [HUDCounter.Placement(widget: .progress, slot: 1)])
        // other genres: a counter takes its position's slot; beyond the panel's slots nothing is drawn
        XCTAssertEqual(HUDCounter.placed([.timer, .moves]), [HUDCounter.Placement(widget: .moves, slot: 2)])
        XCTAssertEqual(HUDCounter.placed([.moves, .goals, .score]),
                       [HUDCounter.Placement(widget: .moves, slot: 1), HUDCounter.Placement(widget: .goals, slot: 2)])
        // the counters' texts from the generic events' values
        let goals = [GoalState(id: "red", current: 12, target: 20), GoalState(id: "blue", current: 20, target: 20)]
        XCTAssertEqual(HUDCounter.text(.moves, moves: 7, goals: []), "7")
        XCTAssertNil(HUDCounter.text(.moves, moves: nil, goals: []), "no movesChanged yet: an empty pill")
        XCTAssertEqual(HUDCounter.text(.progress, moves: nil, goals: goals), "32/40")
        XCTAssertEqual(HUDCounter.text(.goals, moves: nil, goals: goals), "12/20", "the first goal not reached")
        XCTAssertEqual(HUDCounter.text(.score, moves: nil, goals: [GoalState(id: HUDCounter.scoreGoal, current: 1250, target: 0)]),
                       "1250")
        XCTAssertNil(HUDCounter.text(.timer, moves: 3, goals: goals), "timer / hearts have their own views")
        // art: optional slots (none mapped in this skin: the pill centres in its slot); the timer's slot follows the same rule
        XCTAssertNil(HUDCounter.icon(.progress))
        XCTAssertNil(HUDCounter.icon(.moves))
        XCTAssertEqual(HUDCounter.icon(.timer), .hudTimerIcon, "hud.<widget>.icon is the naming the timer's art already uses")
        // sizes are data: ui.json frames.hud.slot<N>*, anchored to the top like the panel
        let t = Tuning.load(bundle: .main).ui.tokens
        for n in 1...HUDCounter.slots {
            XCTAssertEqual(t.frame("hud.slot\(n)Pill", .zero), HUDCounter.pillDefault(n), "frames.hud.slot\(n)Pill")
            XCTAssertEqual(t.frame("hud.slot\(n)Icon", .zero), HUDCounter.iconDefault(n), "frames.hud.slot\(n)Icon")
            XCTAssertEqual(t.anchor("hud.slot\(n)Pill", .centre), .top)
        }
        XCTAssertEqual(t.frame("hud.slot1Pill", .zero), t.frame("hud.timerPill", .zero), "slot 1 is the timer pill's place")
        XCTAssertEqual(t.number("hud.counterBaseline", 0), 22.4, accuracy: 1e-9)
        let pill = HUDCounter.pillDefault(1), icon = HUDCounter.iconDefault(1)
        XCTAssertEqual(HUDCounter.pillFrame(pill: pill, icon: icon, hasIcon: true), pill)
        XCTAssertEqual(HUDCounter.pillFrame(pill: pill, icon: icon, hasIcon: false).midX, icon.union(pill).midX, accuracy: 1e-9)
    }

    func testHUDWriterWidgetsAndCountersNeverOnATapFrame() throws {
        let hud = HUDModel()
        let w = HUDWriter(hud: hud, publishHz: 10)
        var fields: [String] = []
        w.onWrite = { fields.append($0) }
        // the reference cut: timer + hearts are the model's default, so nothing new is written
        w.begin(label: "Level 1", tag: .normal, seconds: 180, hearts: 3, maxHearts: 3, coins: 10, boosters: [], intro: .shown)
        XCTAssertFalse(fields.contains("widgets") || fields.contains("movesLeft") || fields.contains("goals"), "\(fields)")
        XCTAssertEqual(hud.widgets, [.timer, .hearts])
        // a module's cut writes its widgets once
        fields = []
        w.begin(label: "Level 2", tag: .normal, seconds: 0, hearts: nil, maxHearts: 0, coins: 10, boosters: [], intro: .shown,
                widgets: SortPuzzleModule.capabilities.hud)
        XCTAssertEqual(hud.widgets, [.progress])
        XCTAssertEqual(fields.filter { $0 == "widgets" }.count, 1)
        XCTAssertTrue(hud.hearts.isEmpty)
        // counters: on their event, except on a tap frame (§8.2), where the next tick writes them
        let plugin = SortPuzzlePlugin(rules: sortRules(), meta: MetaRules())
        let plan = SessionPlan(id: "S1", levels: [1])
        let stages = try XCTUnwrap(plugin.stages(for: plan, args: LaunchArgs()))
        let session = plugin.makeSession(plan: plan, stages: stages, setup: AttemptSetup(levels: [1]), streakActive: false)
        let g = [GoalState(id: SortPuzzleModule.progressGoal, current: 1, target: 3)]
        fields = []
        w.apply([.meta(.goalProgress(g)), .meta(.movesChanged(left: 9))], session: session, onTapFrame: true)
        XCTAssertEqual(fields, [], "nothing on the tap frame")
        XCTAssertTrue(hud.goals.isEmpty)
        w.tick(session: session, now: 1, gameTime: 1)
        XCTAssertEqual(hud.goals, g)
        XCTAssertEqual(hud.movesLeft, 9)
        fields = []
        w.apply([.meta(.movesChanged(left: 8))], session: session, onTapFrame: false)
        XCTAssertEqual(hud.movesLeft, 8, "a batch that is not a tap frame writes at once")
        XCTAssertEqual(fields, ["movesLeft"])
        // the next cut clears them
        w.begin(label: "Level 3", tag: .normal, seconds: 0, hearts: nil, maxHearts: 0, coins: 10, boosters: [], intro: .shown,
                widgets: [.progress])
        XCTAssertNil(hud.movesLeft)
        XCTAssertTrue(hud.goals.isEmpty)
    }

    func testASortPlayShowsItsProgressAndNoFrozenTimer() throws {
        let r = makeRig()
        XCTAssertTrue(r.game.start())
        frames(r, 60)
        XCTAssertEqual(r.game.session?.phase, .ready(stage: 0))
        XCTAssertEqual(r.hud.widgets, [.progress], "the HUD shows SortPuzzle's declaration: no timer pill")
        XCTAssertFalse(r.hud.widgets.contains(.timer))
        XCTAssertTrue(r.hud.hearts.isEmpty)
        let level = try XCTUnwrap(r.game.currentStage?.content as? SortLevel)
        let goal = try XCTUnwrap(r.hud.goals.first, "goalProgress at ready")
        XCTAssertEqual(goal.id, SortPuzzleModule.progressGoal)
        XCTAssertEqual(goal.target, level.colors)
        XCTAssertEqual(HUDCounter.text(.progress, moves: r.hud.movesLeft, goals: r.hud.goals), "\(goal.current)/\(level.colors)")
    }

    // MARK: 2. fail popups per ContinueOffer.Kind

    func testStuckPopupTextsAndGrantLine() throws {
        let plugin = SortPuzzlePlugin(rules: sortRules(), meta: MetaRules())
        let stuck = ContinueOffer(kind: .stuck, step: 0, price: 900, grant: .puzzleAction(id: SortPuzzleModule.extraTubeAction, amount: 1))
        XCTAssertTrue(OfferPopup.handles(.stuck))
        XCTAssertTrue(OfferPopup.handles(.outOfMoves))
        XCTAssertFalse(OfferPopup.handles(.outOfTime), "Out of Time! stays OutOfTimePopup")
        XCTAssertFalse(OfferPopup.handles(.outOfHearts), "Out of Lives! stays OutOfTimePopup")
        XCTAssertEqual(ContinuePopup.variant(stuck, clawRunning: false), .time, "the first step keeps the instant offer layout")

        let texts = OfferTexts.of(stuck, puzzle: plugin)
        XCTAssertEqual(texts.title.key, "No Moves Left!")
        XCTAssertEqual(texts.body?.key, "You are stuck! Keep going with a little help.")
        XCTAssertEqual(texts.button.key, "Play On")
        XCTAssertEqual(texts.grant?.key, "+1 Tube", "the module words its own rescue")
        XCTAssertEqual(texts.grant.map { String(localized: $0) }, "+1 Tube")
        XCTAssertEqual(texts.iconSlot, "popup.stuck.icon")
        XCTAssertNil(UIArt(rawValue: texts.iconSlot), "no stuck art in this skin: the body takes the prop's place")
        let two = OfferTexts.grantLine(.puzzleAction(id: SortPuzzleModule.extraTubeAction, amount: 2), puzzle: plugin)
        XCTAssertEqual(two?.key, "+%lld Tubes")
        XCTAssertEqual(two.map { String(localized: $0) }, "+2 Tubes")

        let moves = OfferTexts.of(ContinueOffer(kind: .outOfMoves, step: 0, price: 900, grant: .addMoves(5)), puzzle: nil)
        XCTAssertEqual(moves.title.key, "Out of Moves!")
        XCTAssertEqual(moves.button.key, "Add Moves")
        XCTAssertEqual(moves.grant.map { String(localized: $0) }, "+5 Moves", "the shell words addMoves")
        XCTAssertEqual(OfferTexts.grantLine(.addMoves(1), puzzle: nil).map { String(localized: $0) }, "+1 Move")
        XCTAssertEqual(OfferTexts.grantLine(.addTime(45), puzzle: nil).map { String(localized: $0) }, "+45 sec")
        XCTAssertEqual(OfferTexts.grantLine(.addTime(30), puzzle: nil)?.key, "+30 sec", "the reference grant keeps its row")
        XCTAssertEqual(OfferTexts.grantLine(.puzzleAction(id: "shuffle", amount: 3), puzzle: plugin)?.key, "+%lld",
                       "a module action the module does not word: the plain amount")
        XCTAssertNil(OfferTexts.grantLine(.none, puzzle: plugin))

        // every new key is in the catalogue, in English and translated (13 languages: strings.tsv + l10n/*.tsv)
        let keys = ["No Moves Left!", "Out of Moves!", "You are stuck! Keep going with a little help.", "Keep going with a few more moves!",
                    "Add Moves", "+1 Move", "+%lld Moves", "+%lld sec", "+1 Tube", "+%lld Tubes", "Undo", "Extra Tube",
                    "Take back your last move!", "Add an empty tube to the board!"]
        let missing = "\u{1}missing"
        for k in keys { XCTAssertNotEqual(Bundle.main.localizedString(forKey: k, value: missing, table: nil), missing, k) }
        let de = try XCTUnwrap(Bundle.main.path(forResource: "de", ofType: "lproj").flatMap(Bundle.init(path:)), "de.lproj")
        XCTAssertEqual(de.localizedString(forKey: "No Moves Left!", value: missing, table: nil), "Keine Züge mehr!")
        let tr = try XCTUnwrap(Bundle.main.path(forResource: "tr", ofType: "lproj").flatMap(Bundle.init(path:)), "tr.lproj")
        XCTAssertEqual(tr.localizedString(forKey: "+1 Tube", value: missing, table: nil), "+1 Tüp")
    }

    // MARK: 3. module boosters in the shell

    func testModuleBoostersComeFromTheModulesDataAndTheReferenceEconomyIsUnchanged() {
        let list = SortPuzzleEntry.moduleBoosters(bundle: .main, tune: [:])
        XCTAssertEqual(list.map(\.id), [SortPuzzleModule.undo, SortPuzzleModule.extraTube], "capabilities order")
        XCTAssertEqual(list.map(\.startStock), [3, 3])
        XCTAssertEqual(list.map(\.pack), [EconomyRules.BoosterPack(count: 3, price: 900), EconomyRules.BoosterPack(count: 3, price: 900)])
        XCTAssertEqual(list.map(\.name), ["Undo", "Extra Tube"])
        XCTAssertEqual(list.map(\.description), ["Take back your last move!", "Add an empty tube to the board!"])
        XCTAssertEqual(SortPuzzleEntry.moduleBoosters(bundle: .main, tune: ["sort.boosters.undo.price": "450"]).first?.pack.price, 450,
                       "-pc.tune sort.boosters.*")
        XCTAssertEqual(ArrowEscapeEntry.moduleBoosters(bundle: .main, tune: [:]), [], "the reference module has none")
        XCTAssertEqual(SortPuzzlePlugin(rules: sortRules(), meta: MetaRules(), boosters: list).moduleBooster(SortPuzzleModule.undo), list[0])

        let reference = referenceEconomy(Tuning.load(bundle: .main))
        var same = reference
        same.addModuleBoosters(ArrowEscapeEntry.moduleBoosters(bundle: .main, tune: [:]))
        XCTAssertEqual(same, reference, "ArrowEscape active: the economy table is untouched")
        XCTAssertEqual(reference.economy.startBoosters, ["freeze": 3, "hint": 3])
        var merged = reference
        merged.addModuleBoosters(list)
        XCTAssertEqual(merged.economy.startBoosters, ["freeze": 3, "hint": 3, "undo": 3, "extraTube": 3])
        XCTAssertEqual(merged.boosterPack(for: .freeze), reference.economy.boosterPack)
        XCTAssertEqual(merged.boosterPack(for: SortPuzzleModule.undo), list[0].pack)
        XCTAssertEqual(Set(merged.boosterRules().map(\.id)), Set([BoosterID.freeze, .hint, SortPuzzleModule.undo, SortPuzzleModule.extraTube]))
        XCTAssertEqual(merged.boosterRules().filter { [BoosterID.freeze, BoosterID.hint].contains($0.id) }, reference.boosterRules())
        var listed = reference
        listed.economy.startBoosters["undo"] = 9
        listed.addModuleBoosters(list)
        XCTAssertEqual(listed.economy.startBoosters["undo"], 9, "rules.json wins for an id it lists")
        XCTAssertNil(listed.economy.boosterPacks["undo"])

        var s = Economy.freshState(installSeed: 1, installDate: Date(), rules: merged)
        XCTAssertEqual(Economy.stock(s, SortPuzzleModule.extraTube), 3)
        s.boosters["extraTube"] = 0
        s.coins = 1000
        XCTAssertTrue(Economy.buyBooster(&s, SortPuzzleModule.extraTube, rules: merged), "sold in its own pack at 0 stock")
        XCTAssertEqual(Economy.stock(s, SortPuzzleModule.extraTube), 3)
        XCTAssertEqual(s.coins, 100)
    }

    func testBoosterCornersAreTheDeclaredListAndUndoRunsThroughTheShell() throws {
        // the reference corners: the same art and labels as before (freeze left, hint right)
        let freeze = BoosterSlotVM(id: .freeze, state: .stock(3)), hint = BoosterSlotVM(id: .hint, state: .stock(3))
        XCTAssertEqual(BoosterArt.icon(freeze), .boosterFreezeIcon)
        XCTAssertEqual(BoosterArt.icon(hint), .boosterHintIcon)
        XCTAssertEqual(BoosterArt.label(freeze).key, "Time Freeze")
        XCTAssertEqual(BoosterArt.label(hint).key, "Hint")

        let r = makeRig()
        XCTAssertTrue(r.game.start())
        frames(r, 60)
        let slots = r.hud.boosters
        XCTAssertEqual(slots.map(\.id), [SortPuzzleModule.undo, SortPuzzleModule.extraTube], "the corners: the declared list")
        XCTAssertEqual(slots.map(\.state), [.stock(3), .stock(3)], "sort.json's start stock at install")
        XCTAssertEqual(slots.map(\.nameKey), ["Undo", "Extra Tube"])
        for slot in slots { XCTAssertNil(BoosterArt.icon(slot), "\(slot.id): no art in this skin (optional slot): the name face") }
        XCTAssertEqual(BoosterArt.label(slots[0]).key, "Undo")
        XCTAssertEqual(String(localized: BoosterArt.label(slots[1])), "Extra Tube")

        try pourOnce(r)
        let s = try XCTUnwrap(r.game.session as? SortPuzzleSession)
        let tubes = s.tubes
        r.game.boosterTapped(SortPuzzleModule.undo)
        XCTAssertTrue(s.history.isEmpty, "undo took the pour back")
        XCTAssertNotEqual(s.tubes, tubes)
        XCTAssertEqual(Economy.stock(r.store.state, SortPuzzleModule.undo), 2, "one taken from stock")
        XCTAssertEqual(r.hud.boosters.first?.state, .stock(2), "the corner's badge")
        r.game.boosterTapped(SortPuzzleModule.undo)
        XCTAssertEqual(Economy.stock(r.store.state, SortPuzzleModule.undo), 2, "nothing to undo: no stock taken")
        XCTAssertTrue(r.popups.presented.isEmpty)
    }

    // MARK: 4. only the active module is built; frames from the generic hook

    func testOnlyTheActiveModulesContentAndEngineAreBuilt() throws {
        #if !PC_PUZZLE_SORT
        XCTAssertEqual(ObjectIdentifier(ActivePuzzle.entry), ObjectIdentifier(ArrowEscapeEntry.self))
        #endif
        // ArrowEscape: the level library + provider + its session plans (what AppModel built before, now only when active)
        let arrow = ArrowEscapeEntry.loadContent(bundle: .main)
        let library = try XCTUnwrap(arrow.library, "the bundle's Levels")
        XCTAssertNotNil(arrow.provider)
        XCTAssertEqual(arrow.sessions, library.sessions)
        // SortPuzzle: no arrow library, no provider, no engine
        let sort = SortPuzzleEntry.loadContent(bundle: .main)
        XCTAssertNil(sort.library)
        XCTAssertNil(sort.provider)
        XCTAssertEqual(sort.sessions, AppModel.loadSessions(bundle: .main))
        let args = LaunchArgs()
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("tpl5-ctx-\(UUID().uuidString)")
        let ctx = AppContext(args: args, tuning: Tuning.load(bundle: .main), clock: MotionClock(args: args),
                             store: PlayerStore(args: args, now: Date(), bundle: .main, directory: dir, debounce: 0.05), hud: HUDModel(),
                             anchors: AnchorRegistry(), perf: PerfMonitor(), latency: LatencyProbe(), bundle: .main)
        XCTAssertNil(SortPuzzleEntry.makeEngine(ctx), "a sort game builds no arrow engine")
    }

    func testABoardWithoutItsOwnMeterIsMeteredThroughBoardFrame() throws {
        XCTAssertFalse(makeBoard().metersFrames)
        #if DEBUG
        let arrowBoard = ArrowPuzzleBoard(engine: PlaceholderBoard(), tuning: Tuning.load(bundle: .main).board)
        XCTAssertTrue(arrowBoard.metersFrames, "ArrowEscape's engine meters its own display link (unchanged)")
        #endif

        let r = makeRig()
        let meter = try XCTUnwrap(r.game.frameMeter, "SortPuzzleBoard is metered by the Play")
        XCTAssertTrue(r.game.start())
        frames(r, 30)
        XCTAssertEqual(r.perf.totalFrames, 29, "every frame after the first reaches PerfMonitor through boardFrame")
        XCTAssertEqual(r.perf.framesOverBudget, 0)
        frames(r, 1, dt: 0.05)
        XCTAssertEqual(r.perf.framesOverBudget, 1, "a 50 ms frame is a hitch")
        XCTAssertEqual(meter.hitches, 1)
        frames(r, 30)
        let s = try XCTUnwrap(r.game.session)
        let t = try XCTUnwrap(s.hint())
        XCTAssertTrue(r.board.performTap(on: t))
        XCTAssertEqual(meter.tapLabel.target, "\(t.raw)", "the tap's release starts the latency sample (boardInput)")
        XCTAssertEqual(meter.tapLabel.level, 2)
    }

    func testTheReferenceBoardAddsNoSecondMeter() {
        #if DEBUG
        let args = LaunchArgs(pairs: ["pc.seed": "7"])
        let tuning = Tuning.load(bundle: .main)
        let rules = RulesTuning.load(json: tuning.rules.data, overrides: tuning.rules.overrides).rules
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("tpl5-arrow-\(UUID().uuidString)")
        let economy = referenceEconomy(tuning)
        let store = PlayerStore(args: args, now: Date(), bundle: .main, directory: dir, rules: economy, debounce: 0.05)
        let log = GameControllerTests.Recorder()
        let board = ArrowPuzzleBoard(engine: PlaceholderBoard(), tuning: tuning.board)
        let services = GameServices(
            args: args, tuning: tuning, rules: rules.meta, economy: economy, clock: MotionClock(args: args), store: store,
            hud: HUDModel(), board: board, puzzle: ArrowEscapePlugin(rules: rules, level: { _ in nil }),
            audio: GameControllerTests.FakeAudio(log), haptics: GameControllerTests.FakeHaptics(log),
            popups: GameControllerTests.FakePopups(log), fx: GameControllerTests.FakeFX(log), router: GameControllerTests.FakeRouter(),
            latency: LatencyProbe(), perf: PerfMonitor(), plan: { l in SessionPlan(id: l.session, levels: l.levels) },
            rivals: { SocialWorld(installSeed: 7, config: .default, names: NameBank()) },
            screenSize: { ModuleShellTests.screen },
            screenAfterWin: { .home(.afterWin($0), tab: .home) },
            screenAfterLoss: { GameServices.defaultAfterLoss($0, tryAgain: $1, homeSeen: true) },
            levelStarted: { _ in }, app: nil)
        let game = GameController(LevelLaunch(session: "L1", levels: [1]), services: services, directors: { _ in [] })
        XCTAssertNil(game.frameMeter, "the engine's display link stays the only meter: same frames, same logs")
        XCTAssertEqual(game.boosterSlot(BoosterSpec(id: .freeze, effect: .freezeTimer), stock: 3),
                       BoosterSlotVM(id: .freeze, state: .stock(3)), "the reference corner's view model is unchanged")
        #endif
    }
}
