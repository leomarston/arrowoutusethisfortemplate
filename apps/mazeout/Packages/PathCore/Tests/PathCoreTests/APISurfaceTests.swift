import XCTest
import Foundation
import PathCore   // deliberately NOT @testable: only the public surface is visible here, so an access change fails too

/// SPEC-architecture §3.5 / §4.17: the frozen-contract check. Every public member of every ◆ PathCore type is pinned
/// twice:
/// 1. a typed reference (`let _: (A) -> B = X.member`, key paths for stored properties), so a changed signature, label,
///    type or mutability fails to COMPILE;
/// 2. a real construction / call, so the member also runs.
/// WP0 wrote this skeleton for the ◆ files it wrote (Cell, Dir, IDs, LevelSpec, Plans, SessionTypes, SessionEvent,
/// PlayerState, EventTypes, SocialAPI). C2 COMPLETED it (the BoardState / LevelSession / LevelClock / ComboTracker surface
/// of §4.4–§4.7, plus RulesTuning, Solver and HeadlessDriver) and owns it afterwards. Never `@testable`.
final class APISurfaceTests: XCTestCase {

    // MARK: Grid/Cell.swift, Grid/Dir.swift

    func testCellAndDirSurface() {
        let _: (Int, Int) -> Cell = Cell.init(_:_:)
        let _: (Int, Int) -> Cell = Cell.init(c:r:)
        let _: WritableKeyPath<Cell, Int> = \.c
        let _: WritableKeyPath<Cell, Int> = \.r
        let _: (Cell, Dir) -> Cell = (+)
        let _: (Cell) -> (Dir, Int) -> Cell = Cell.moved(_:by:)
        let _: KeyPath<Cell, String> = \.description
        XCTAssertEqual(Dir.allCases, [.up, .down, .left, .right])
        let _: KeyPath<Dir, Int> = \.dc
        let _: KeyPath<Dir, Int> = \.dr
        let _: KeyPath<Dir, Dir> = \.opposite
        let _: KeyPath<Dir, Double> = \.angle
        let _: KeyPath<Dir, Bool> = \.isHorizontal
        let _: (Cell, Cell) -> Dir? = Dir.init(from:to:)
        XCTAssertEqual(Cell(0, 0).moved(.right, by: 2), Cell(c: 2, r: 0))
        XCTAssertEqual(Dir(rawValue: "up"), .up)
    }

    // MARK: Model/IDs.swift

    func testIDsSurface() {
        let _: (Int) -> ArrowID = ArrowID.init(_:)
        let _: KeyPath<ArrowID, Int> = \.raw
        let _: (String) -> ObstacleID = ObstacleID.init(_:)
        let _: KeyPath<ObstacleID, String> = \.raw
        let _: (String) -> BoosterID = BoosterID.init(_:)
        let _: (String) -> BoosterID? = BoosterID.init(rawValue:)
        let _: KeyPath<BoosterID, String> = \.rawValue
        let _: [BoosterID] = [.freeze, .hint]
        let _: (String) -> FeatureID = FeatureID.init(_:)
        let _: [FeatureID] = [.linked, .door, .pipe, .box, .curtain, .elevator, .corner]
        let _: (String) -> TutorialID = TutorialID.init(_:)
        let _: KeyPath<TutorialID, String> = \.rawValue
        let _: (String) -> EventID = EventID.init(_:)
        let _: [EventID] = [.streakRace, .clawChallenge, .skyJump, .rocketRace, .weeklyContest]
        XCTAssertEqual(LevelTag.allCases, [.normal, .hard, .superHard])
        let _: (String?) -> LevelTag? = LevelTag.init(label:)
        // FIX-3 B (SPEC.md ruling 55(c), contract amend 7): the cases were renamed neutral (.recorded → .authored, .video →
        // .crafted; same order, same count). Pinned as strongly as before, plus the raw values of THIS build (macOS,
        // PC_RESEARCH): the content pipeline's spellings, so design/levels.json, research/ and every tool output are
        // unchanged. The iOS app's neutral raw values are pinned by Tests/AppTests/LevelsBundleTests.
        XCTAssertEqual(LevelSource.allCases, [.authored, .crafted, .designed, .generated])
        XCTAssertEqual(LevelSource.allCases.map(\.rawValue), ["recorded", "video", "designed", "generated"])
        let _: (String) -> StringIDKey = StringIDKey.init(_:)
        XCTAssertEqual(LevelTag(label: "Super Hard"), .superHard)
        XCTAssertEqual(ObstacleID("d0"), "d0")
    }

    // MARK: Model/LevelSpec.swift

    func testLevelSpecSurface() {
        let _: (ArrowID, [Cell], Dir, Int, ObstacleID?) -> ArrowSpec = ArrowSpec.init(id:cells:dir:layer:hiddenBy:)
        let _: WritableKeyPath<ArrowSpec, ArrowID> = \.id
        let _: WritableKeyPath<ArrowSpec, [Cell]> = \.cells
        let _: WritableKeyPath<ArrowSpec, Dir> = \.dir
        let _: WritableKeyPath<ArrowSpec, Int> = \.layer
        let _: WritableKeyPath<ArrowSpec, ObstacleID?> = \.hiddenBy
        XCTAssertEqual(ObstacleKind.allCases, [.tape, .door, .key, .pipe, .box, .curtain, .elevator, .corner])
        let _: (Cell, Dir) -> PipeEnd = PipeEnd.init(cell:out:)
        let _: WritableKeyPath<PipeEnd, Cell> = \.cell
        let _: WritableKeyPath<PipeEnd, Dir> = \.out
        XCTAssertEqual(CornerTurn.allCases, [.upRight, .upLeft, .downRight, .downLeft])
        let _: (ObstacleID, ObstacleKind, [Cell], [ArrowID], [PipeEnd], Int?, [Double]?, Int?, ObstacleID?, CornerTurn?,
                [ArrowID], String?) -> ObstacleSpec =
            ObstacleSpec.init(id:kind:cells:arrows:ends:counter:counterAt:order:opens:turn:reveals:sprite:)
        let _: WritableKeyPath<ObstacleSpec, ObstacleID> = \.id
        let _: WritableKeyPath<ObstacleSpec, ObstacleKind> = \.kind
        let _: WritableKeyPath<ObstacleSpec, [Cell]> = \.cells
        let _: WritableKeyPath<ObstacleSpec, [ArrowID]> = \.arrows
        let _: WritableKeyPath<ObstacleSpec, [PipeEnd]> = \.ends
        let _: WritableKeyPath<ObstacleSpec, Int?> = \.counter
        let _: WritableKeyPath<ObstacleSpec, [Double]?> = \.counterAt
        let _: WritableKeyPath<ObstacleSpec, Int?> = \.order
        let _: WritableKeyPath<ObstacleSpec, ObstacleID?> = \.opens
        let _: WritableKeyPath<ObstacleSpec, CornerTurn?> = \.turn
        let _: WritableKeyPath<ObstacleSpec, [ArrowID]> = \.reveals
        let _: WritableKeyPath<ObstacleSpec, String?> = \.sprite
        let _: (Int, Int, Int, Int, Double, Double?) -> LevelMetrics =
            LevelMetrics.init(rounds:freeAtStart:arrows:cells:meanLength:botTimeLeft:)
        let _: WritableKeyPath<LevelMetrics, Int> = \.rounds
        let _: WritableKeyPath<LevelMetrics, Int> = \.freeAtStart
        let _: WritableKeyPath<LevelMetrics, Int> = \.arrows
        let _: WritableKeyPath<LevelMetrics, Int> = \.cells
        let _: WritableKeyPath<LevelMetrics, Double> = \.meanLength
        let _: WritableKeyPath<LevelMetrics, Double?> = \.botTimeLeft
        let _: (Int, LevelSource, String?, Int, Int, [String]?, Int, Int, LevelTag, [ArrowSpec], [ObstacleSpec], FeatureID?,
                UInt64?, LevelMetrics?) -> LevelSpec =
            LevelSpec.init(level:source:capture:cols:rows:mask:timerSeconds:hearts:tag:arrows:obstacles:unlock:seed:metrics:)
        let _: WritableKeyPath<LevelSpec, Int> = \.level
        let _: WritableKeyPath<LevelSpec, LevelSource> = \.source
        let _: WritableKeyPath<LevelSpec, String?> = \.capture
        let _: WritableKeyPath<LevelSpec, Int> = \.cols
        let _: WritableKeyPath<LevelSpec, Int> = \.rows
        let _: WritableKeyPath<LevelSpec, [String]?> = \.mask
        let _: WritableKeyPath<LevelSpec, Int> = \.timerSeconds
        let _: WritableKeyPath<LevelSpec, Int> = \.hearts
        let _: WritableKeyPath<LevelSpec, LevelTag> = \.tag
        let _: WritableKeyPath<LevelSpec, [ArrowSpec]> = \.arrows
        let _: WritableKeyPath<LevelSpec, [ObstacleSpec]> = \.obstacles
        let _: WritableKeyPath<LevelSpec, FeatureID?> = \.unlock
        let _: WritableKeyPath<LevelSpec, UInt64?> = \.seed
        let _: WritableKeyPath<LevelSpec, LevelMetrics?> = \.metrics
        let _: KeyPath<LevelSpec, Grid> = \.grid
        XCTAssertEqual(HeartsCarry.allCases, [.reset, .carry])
        let _: (String, [Int], String?, String?, Int?, Double?, HeartsCarry) -> SessionPlan =
            SessionPlan.init(id:levels:hudLabel:panelLabel:reward:stageGap:hearts:)
        let _: WritableKeyPath<SessionPlan, String> = \.id
        let _: WritableKeyPath<SessionPlan, [Int]> = \.levels
        let _: WritableKeyPath<SessionPlan, String?> = \.hudLabel
        let _: WritableKeyPath<SessionPlan, String?> = \.panelLabel
        let _: WritableKeyPath<SessionPlan, Int?> = \.reward
        let _: WritableKeyPath<SessionPlan, Double?> = \.stageGap
        let _: WritableKeyPath<SessionPlan, HeartsCarry> = \.hearts

        let level = LevelSpec(level: 7, source: .crafted, cols: 4, rows: 4, timerSeconds: 180,
                              arrows: [ArrowSpec(id: ArrowID(0), cells: [Cell(0, 0), Cell(1, 0)], dir: .right)],
                              obstacles: [ObstacleSpec(id: "t0", kind: .tape, arrows: [ArrowID(0)])])
        XCTAssertEqual(level.grid.cols, 4)
        XCTAssertEqual(level.hearts, 3)
        XCTAssertEqual(level.tag, .normal)
        XCTAssertEqual(SessionPlan(id: "L7", levels: [7]).hearts, .carry)
    }

    // MARK: Rules/Plans.swift

    func testPlansSurface() {
        let a = ArrowID(1), o = ObstacleID("p0")
        let resolutions: [TapResolution] = [.ignored(.noArrow)]
        XCTAssertEqual(resolutions.count, 1)
        XCTAssertEqual(IgnoreReason.allCases, [.noArrow, .hidden, .moving, .bumping, .inputLocked, .notPlaying])
        let segments: [PathSegment] = [.body(0..<2), .ray(2..<5), .tube(o, 5..<9), .corner("x0", at: 9)]
        let _: ([Cell], [PathSegment], Double) -> ExitPath = ExitPath.init(cells:segments:toGridEdge:)
        let path = ExitPath(cells: [Cell(0, 0), Cell(1, 0)], segments: segments, toGridEdge: 9)
        let _: WritableKeyPath<ExitPath, [Cell]> = \.cells
        let _: WritableKeyPath<ExitPath, [PathSegment]> = \.segments
        let _: WritableKeyPath<ExitPath, Double> = \.toGridEdge
        let beats: [PlanBeat] = [
            .keyReleased(key: "k0", door: "d0", s: 0.5), .enterTube(o, a, s: 5), .leaveTube(o, a, s: 9),
            .pipeCount(o, remaining: 1, s: 5), .pipeBreak(o, s: 9), .corner("x0", a, s: 9),
            .counterTick("b0", remaining: 3, s: 0), .counterBreak("b0", s: 0), .elevatorEmptied("e0", s: 0),
        ]
        let _: KeyPath<PlanBeat, Double> = \.s
        XCTAssertEqual(beats.map(\.s), [0.5, 5, 9, 5, 9, 9, 0, 0, 0])
        let _: (ArrowID, [ArrowID], ObstacleID?, [ArrowID: ExitPath], [PlanBeat], Int) -> ExitPlan =
            ExitPlan.init(tapped:unit:tape:paths:beats:combo:)
        let exit = ExitPlan(tapped: a, unit: [a], tape: nil, paths: [a: path], beats: beats, combo: 1)
        let _: WritableKeyPath<ExitPlan, ArrowID> = \.tapped
        let _: WritableKeyPath<ExitPlan, [ArrowID]> = \.unit
        let _: WritableKeyPath<ExitPlan, ObstacleID?> = \.tape
        let _: WritableKeyPath<ExitPlan, [ArrowID: ExitPath]> = \.paths
        let _: WritableKeyPath<ExitPlan, [PlanBeat]> = \.beats
        let _: WritableKeyPath<ExitPlan, Int> = \.combo
        let blockers: [Blocker] = [.arrow(a), .obstacle(o)]
        let _: (ArrowID, Blocker, Int, ExitPath, Double, Cell) -> BumpPlan =
            BumpPlan.init(arrow:blocker:gapCells:path:contactCells:contactPoint:)
        let bump = BumpPlan(arrow: a, blocker: blockers[0], gapCells: 0, path: path, contactCells: 0.3, contactPoint: Cell(2, 0))
        let _: WritableKeyPath<BumpPlan, ArrowID> = \.arrow
        let _: WritableKeyPath<BumpPlan, Blocker> = \.blocker
        let _: WritableKeyPath<BumpPlan, Int> = \.gapCells
        let _: WritableKeyPath<BumpPlan, ExitPath> = \.path
        let _: WritableKeyPath<BumpPlan, Double> = \.contactCells
        let _: WritableKeyPath<BumpPlan, Cell> = \.contactPoint
        XCTAssertNotEqual(TapResolution.exit(exit), TapResolution.bump(bump))
    }

    // MARK: Session/SessionTypes.swift, Session/SessionEvent.swift

    func testSessionTypesSurface() {
        let offer = ContinueOffer(kind: .outOfTime, step: 0, price: 900, grant: .addTime(30), warning: .none, isLast: false)
        let _: (ContinueOffer.Kind, Int, Int, ContinueOffer.Grant, ContinueOffer.Warning, Bool) -> ContinueOffer =
            ContinueOffer.init(kind:step:price:grant:warning:isLast:)
        let _: WritableKeyPath<ContinueOffer, ContinueOffer.Kind> = \.kind
        let _: WritableKeyPath<ContinueOffer, Int> = \.step
        let _: WritableKeyPath<ContinueOffer, Int> = \.price
        let _: WritableKeyPath<ContinueOffer, ContinueOffer.Grant> = \.grant
        let _: WritableKeyPath<ContinueOffer, ContinueOffer.Warning> = \.warning
        let _: WritableKeyPath<ContinueOffer, Bool> = \.isLast
        // template phase 2 (PUZZLE-MODULE.md §1): additive cases, the two original ones first and unchanged
        XCTAssertEqual(ContinueOffer.Kind.allCases, [.outOfTime, .outOfHearts, .outOfMoves, .stuck])
        XCTAssertEqual(ContinueOffer.Kind.allCases.map(\.rawValue), ["outOfTime", "outOfHearts", "outOfMoves", "stuck"])
        XCTAssertEqual(ContinueOffer.Kind.allCases.map(\.lossReason), [.timeUp, .hearts, .outOfMoves, .stuck])
        let _: [ContinueOffer.Grant] = [.addTime(30), .refillHearts(3), .none]
        let _: [ContinueOffer.Grant] = [.addMoves(5), .puzzleAction(id: "shuffle", amount: 1)]
        XCTAssertEqual(ContinueOffer.Warning.allCases, [.none, .streak, .token, .life])

        let win = WinResult(levels: [32], tag: .normal, timeLeft: 120, heartsLeft: 3, firstTry: true, reward: 20, bumps: 0)
        let _: ([Int], LevelTag, Int, Int, Bool, Int, Int) -> WinResult =
            WinResult.init(levels:tag:timeLeft:heartsLeft:firstTry:reward:bumps:)
        let _: WritableKeyPath<WinResult, [Int]> = \.levels
        let _: WritableKeyPath<WinResult, LevelTag> = \.tag
        let _: WritableKeyPath<WinResult, Int> = \.timeLeft
        let _: WritableKeyPath<WinResult, Int> = \.heartsLeft
        let _: WritableKeyPath<WinResult, Bool> = \.firstTry
        let _: WritableKeyPath<WinResult, Int> = \.reward
        let _: WritableKeyPath<WinResult, Int> = \.bumps
        // template phase 2, additive
        let _: WritableKeyPath<WinResult, Int?> = \.stars
        let _: WritableKeyPath<WinResult, [String: Double]> = \.stats
        let _: ([Int], LevelTag, Int, Int, Bool, Int, Int, Int?, [String: Double]) -> WinResult =
            WinResult.init(levels:tag:timeLeft:heartsLeft:firstTry:reward:bumps:stars:stats:)
        XCTAssertNil(win.stars)
        XCTAssertEqual(win.stats, [:])
        let oldJSON = #"{"levels":[32],"tag":"normal","timeLeft":120,"heartsLeft":3,"firstTry":true,"reward":20,"bumps":0}"#
        XCTAssertEqual(try? JSONDecoder().decode(WinResult.self, from: Data(oldJSON.utf8)), win, "results without the new keys decode")
        let rated = WinResult(levels: [1], tag: .hard, timeLeft: 0, heartsLeft: 0, firstTry: false, reward: 60, bumps: 0, stars: 3,
                              stats: ["movesLeft": 4])
        XCTAssertEqual(try? JSONDecoder().decode(WinResult.self, from: JSONEncoder().encode(rated)), rated)

        let phases: [Phase] = [.intro(stage: 0), .ready(stage: 0), .playing(stage: 0), .stageClear(stage: 0),
                               .offer(offer), .won(win), .lost(.timeUp)]
        XCTAssertEqual(phases.count, 7)
        XCTAssertEqual(HoldReason.allCases, [.intro, .stageTransition, .tutorial, .unlockOverlay, .popup, .pause, .offer,
                                             .background, .winSequence])
        // template phase 2: additive cases after the original four
        XCTAssertEqual(LossReason.allCases, [.timeUp, .hearts, .quit, .killed, .outOfMoves, .stuck])
        XCTAssertEqual(TimeCause.allCases, [.continueOffer, .booster])
        let _: [TimerAlert] = [.threshold(10)]

        let _: ([Int], Int, UInt64, [BoosterID: Int], Int) -> AttemptSetup =
            AttemptSetup.init(levels:attemptIndex:seed:boosters:firstStage:)
        let setup = AttemptSetup(levels: [1, 2, 3, 4], attemptIndex: 1, seed: 7, boosters: [.freeze: 3, .hint: 3], firstStage: 0)
        let _: WritableKeyPath<AttemptSetup, [Int]> = \.levels
        let _: WritableKeyPath<AttemptSetup, Int> = \.attemptIndex
        let _: WritableKeyPath<AttemptSetup, UInt64> = \.seed
        let _: WritableKeyPath<AttemptSetup, [BoosterID: Int]> = \.boosters
        let _: WritableKeyPath<AttemptSetup, Int> = \.firstStage
        XCTAssertEqual(setup.boosters[.hint], 3)

        let acks: [SessionAck] = [.introFinished, .bumpContact(ArrowID(1)), .bumpFinished(ArrowID(1)), .doorBurst("d0"),
                                  .lastExitLeftBoard, .stageTransitionDone]
        XCTAssertEqual(acks.count, 6)

        let _: ([Int], Int, String, Double, Bool, Int, [ArrowID], [[ArrowID]], [ObstacleID: Int], Int) -> SessionSnapshot =
            SessionSnapshot.init(levels:stage:phase:remaining:timerStarted:hearts:live:free:counters:combo:)
        let snap = SessionSnapshot(levels: [32], stage: 0, phase: "playing", remaining: 178, timerStarted: true, hearts: 3,
                                   live: [ArrowID(13)], free: [[ArrowID(13)]], counters: ["p0": 2], combo: 0)
        let _: WritableKeyPath<SessionSnapshot, [Int]> = \.levels
        let _: WritableKeyPath<SessionSnapshot, Int> = \.stage
        let _: WritableKeyPath<SessionSnapshot, String> = \.phase
        let _: WritableKeyPath<SessionSnapshot, Double> = \.remaining
        let _: WritableKeyPath<SessionSnapshot, Bool> = \.timerStarted
        let _: WritableKeyPath<SessionSnapshot, Int> = \.hearts
        let _: WritableKeyPath<SessionSnapshot, [ArrowID]> = \.live
        let _: WritableKeyPath<SessionSnapshot, [[ArrowID]]> = \.free
        let _: WritableKeyPath<SessionSnapshot, [ObstacleID: Int]> = \.counters
        let _: WritableKeyPath<SessionSnapshot, Int> = \.combo
        XCTAssertEqual(snap.counters["p0"], 2)

        // Every SessionEvent case with its labels.
        let exit = ExitPlan(tapped: ArrowID(1), unit: [ArrowID(1)], paths: [:])
        let bump = BumpPlan(arrow: ArrowID(1), blocker: .arrow(ArrowID(2)), gapCells: 0,
                            path: ExitPath(cells: [], segments: [], toGridEdge: 0), contactCells: 0, contactPoint: Cell(0, 0))
        let events: [SessionEvent] = [
            .stageLoaded(stage: 0, of: 4, level: 1), .timerArmed(stage: 0, seconds: 180), .timerStarted(stage: 0),
            .exited(exit), .bumped(bump), .tapIgnored(nil, .hidden), .tapIgnored(ArrowID(1), .moving),
            .heartLost(remaining: 2), .arrowMarked(ArrowID(1)), .keyDispatched(key: "k0", door: "d0"),
            .doorOpened("d0", revealed: [ArrowID(5)]), .pipeUsed("p0", remaining: 1), .pipeBroken("p0"),
            .counterChanged("b0", remaining: 9), .counterBroken("b0", revealed: []), .elevatorActivated("e0", revealed: []),
            .timerAlert(.threshold(10)), .timeAdded(seconds: 30, cause: .continueOffer), .freezeStarted(seconds: 10),
            .freezeEnded, .boosterUsed(.freeze), .hintShown([ArrowID(3)]), .stageCleared(stage: 0), .stageAdvanced(to: 1),
            .offer(offer), .continued(offer), .won(win), .lost(.quit),
        ]
        XCTAssertEqual(events.count, 28)
    }

    // MARK: Economy/PlayerState.swift

    func testPlayerStateSurface() {
        var s = PlayerState()
        let _: () -> PlayerState = PlayerState.init
        let _: (UInt64, Date) -> PlayerState = PlayerState.init(installSeed:installDate:)
        let _: WritableKeyPath<PlayerState, Int> = \.version
        let _: WritableKeyPath<PlayerState, UInt64> = \.installSeed
        let _: WritableKeyPath<PlayerState, Date> = \.installDate
        let _: WritableKeyPath<PlayerState, Int> = \.level
        let _: WritableKeyPath<PlayerState, Bool> = \.homeSeen
        let _: WritableKeyPath<PlayerState, Int> = \.coins
        let _: WritableKeyPath<PlayerState, Int> = \.pendingCoinFly
        let _: WritableKeyPath<PlayerState, LivesState> = \.lives
        let _: WritableKeyPath<PlayerState, Date?> = \.unlimitedLivesUntil
        let _: WritableKeyPath<PlayerState, [String: Int]> = \.boosters
        let _: WritableKeyPath<PlayerState, Set<String>> = \.unlocksSeen
        let _: WritableKeyPath<PlayerState, Set<String>> = \.tutorialsDone
        let _: WritableKeyPath<PlayerState, [Int: Int]> = \.attempts
        let _: WritableKeyPath<PlayerState, ActiveAttempt?> = \.activeAttempt
        let _: WritableKeyPath<PlayerState, PlayerState.Stats> = \.stats
        let _: WritableKeyPath<PlayerState, EventsState> = \.events
        let _: WritableKeyPath<PlayerState, SocialState> = \.social
        let _: WritableKeyPath<PlayerState, PlayerState.Settings> = \.settings
        let _: WritableKeyPath<PlayerState, PlayerState.Flags> = \.flags
        let _: WritableKeyPath<PlayerState, Set<String>> = \.processedTransactions

        let _: (Int, Int, Int, Int, Double) -> PlayerState.Stats =
            PlayerState.Stats.init(wins:losses:firstTryWins:weeklyContestWins:playSeconds:)
        let _: WritableKeyPath<PlayerState.Stats, Int> = \.wins
        let _: WritableKeyPath<PlayerState.Stats, Int> = \.losses
        let _: WritableKeyPath<PlayerState.Stats, Int> = \.firstTryWins
        let _: WritableKeyPath<PlayerState.Stats, Int> = \.weeklyContestWins
        let _: WritableKeyPath<PlayerState.Stats, Double> = \.playSeconds
        let _: (Bool, Bool, Bool, Bool, String?) -> PlayerState.Settings =
            PlayerState.Settings.init(sound:music:haptic:notifications:trail:)
        let _: WritableKeyPath<PlayerState.Settings, Bool> = \.sound
        let _: WritableKeyPath<PlayerState.Settings, Bool> = \.music
        let _: WritableKeyPath<PlayerState.Settings, Bool> = \.haptic
        let _: WritableKeyPath<PlayerState.Settings, Bool> = \.notifications
        let _: WritableKeyPath<PlayerState.Settings, String?> = \.trail
        let _: (Bool, Bool, Bool, Set<String>) -> PlayerState.Flags =
            PlayerState.Flags.init(ratingPromptShown:notificationPromptShown:weeklyIntroSeen:seen:)
        let _: WritableKeyPath<PlayerState.Flags, Bool> = \.ratingPromptShown
        let _: WritableKeyPath<PlayerState.Flags, Bool> = \.notificationPromptShown
        let _: WritableKeyPath<PlayerState.Flags, Bool> = \.weeklyIntroSeen
        let _: WritableKeyPath<PlayerState.Flags, Set<String>> = \.seen
        let _: (Int, Date?) -> LivesState = LivesState.init(count:anchor:)
        let _: WritableKeyPath<LivesState, Int> = \.count
        let _: WritableKeyPath<LivesState, Date?> = \.anchor
        let _: (String, [Int], Int, Date, Int) -> ActiveAttempt = ActiveAttempt.init(session:levels:attemptIndex:startedAt:stage:)
        let _: WritableKeyPath<ActiveAttempt, String> = \.session
        let _: WritableKeyPath<ActiveAttempt, [Int]> = \.levels
        let _: WritableKeyPath<ActiveAttempt, Int> = \.attemptIndex
        let _: WritableKeyPath<ActiveAttempt, Date> = \.startedAt
        let _: WritableKeyPath<ActiveAttempt, Int> = \.stage

        s.coins -= 900
        s.settings.haptic = false
        s.flags.seen.insert("weeklyTutorial")
        XCTAssertEqual(s.coins, 100)
        XCTAssertEqual(PlayerState(installSeed: 9, installDate: Date(timeIntervalSince1970: 0)).installSeed, 9)
    }

    // MARK: Events/EventTypes.swift

    /// A conforming stub proves RivalProvider's exact requirement signatures.
    private struct StubRivals: RivalProvider {
        func streakRace(_ instance: EventInstance, player: PlayerStanding, at: SocialTime) -> [RaceStanding] { [] }
        func rocketRace(_ instance: EventInstance, joinedAt: SocialTime, at: SocialTime) -> [RaceStanding] { [] }
        func skyJump(_ run: SkyJumpRun, at: SocialTime) -> SkyJumpField { SkyJumpField(total: 100, left: 100, winners: 0) }
    }

    func testEventTypesSurface() {
        let now = Date(timeIntervalSince1970: 1_790_000_000)
        let _: ([Int], LevelTag, Bool, Date) -> WinContext = WinContext.init(levels:tag:firstTry:now:)
        let _: WritableKeyPath<WinContext, [Int]> = \.levels
        let _: WritableKeyPath<WinContext, LevelTag> = \.tag
        let _: WritableKeyPath<WinContext, Bool> = \.firstTry
        let _: WritableKeyPath<WinContext, Date> = \.now
        let _: ([Int], LossReason, Date) -> LossContext = LossContext.init(levels:reason:now:)
        let _: WritableKeyPath<LossContext, [Int]> = \.levels
        let _: WritableKeyPath<LossContext, LossReason> = \.reason
        let _: WritableKeyPath<LossContext, Date> = \.now
        XCTAssertTrue(WinContext(levels: [32], tag: .hard, firstTry: true, now: now).firstTry)
        XCTAssertEqual(LossContext(levels: [32], reason: .hearts, now: now).reason, .hearts)

        let g = Grant(coins: 100)
        let outcomes: [EventOutcome] = [
            .multiplier(from: 1, to: 5), .clawPoints(added: 5, total: 205, target: 300), .clawStep(step: 2, reward: g),
            .streakRaceScore(10), .skyJumpProgress(levels: 3, of: 5), .skyJumpWon(share: 714, winners: 7), .skyJumpFailed,
            .rocketProgress(mine: 2), .rocketFinished(rank: 1, reward: g), .rocketFinished(rank: 3, reward: nil),
            .weeklyScore(4), .grant(g),
            // contract amend 4 (SPEC.md §5 item 42): Balloon Rise, the v582 rules (build/p/PH0/balloon.md)
            .balloonStreak(added: 1, total: 3, goal: 5), .balloonStreak(added: 1, total: 121, goal: nil),
            .balloonStep(step: 1, reward: g), .balloonFell(from: 3),
        ]
        XCTAssertEqual(outcomes.count, 16)
        let _: (Int, Int, Int?) -> EventOutcome = EventOutcome.balloonStreak(added:total:goal:)
        let _: (Int, Grant) -> EventOutcome = EventOutcome.balloonStep(step:reward:)
        let _: (Int) -> EventOutcome = EventOutcome.balloonFell(from:)
        // the new cases round-trip through Codable (saves and the fixtures carry outcomes), the optional goal included
        let data = try! JSONEncoder().encode(outcomes)
        XCTAssertEqual(try! JSONDecoder().decode([EventOutcome].self, from: data), outcomes)

        let me = SimPlayer(id: 0, name: "player_abc1234", country: "TR", avatar: 0)
        let _: (Int, SimPlayer, Int, Bool) -> RaceStanding = RaceStanding.init(rank:player:score:isMe:)
        let _: WritableKeyPath<RaceStanding, Int> = \.rank
        let _: WritableKeyPath<RaceStanding, SimPlayer> = \.player
        let _: WritableKeyPath<RaceStanding, Int> = \.score
        let _: WritableKeyPath<RaceStanding, Bool> = \.isMe
        XCTAssertTrue(RaceStanding(rank: 1, player: me, score: 10, isMe: true).isMe)
        let _: (Int, Int, Int, [SimPlayer]) -> SkyJumpField = SkyJumpField.init(total:left:winners:shown:)
        let _: WritableKeyPath<SkyJumpField, Int> = \.total
        let _: WritableKeyPath<SkyJumpField, Int> = \.left
        let _: WritableKeyPath<SkyJumpField, Int> = \.winners
        let _: WritableKeyPath<SkyJumpField, [SimPlayer]> = \.shown

        let provider: any RivalProvider = StubRivals()
        let t = SocialTime(seconds: 1_790_000_000)
        let inst = EventInstance(event: .skyJump, index: 0, start: t, end: SocialTime(seconds: t.seconds + 86_400))
        XCTAssertEqual(provider.skyJump(SkyJumpRun(instance: inst, joinedAt: t), at: t).total, 100)
    }

    // MARK: Social/SocialAPI.swift

    func testSocialAPISurface() {
        let _: (Int64) -> SocialTime = SocialTime.init(seconds:)
        let _: KeyPath<SocialTime, Int64> = \.seconds
        XCTAssertTrue(SocialTime(seconds: 1) < SocialTime(seconds: 2))
        let kinds: [LeaderboardKind] = [.weekly(week: 21), .world, .country("TR")]
        XCTAssertEqual(kinds.count, 3)
        let _: (UInt64, String, String, Int) -> SimPlayer = SimPlayer.init(id:name:country:avatar:)
        let _: WritableKeyPath<SimPlayer, UInt64> = \.id
        let _: WritableKeyPath<SimPlayer, String> = \.name
        let _: WritableKeyPath<SimPlayer, String> = \.country
        let _: WritableKeyPath<SimPlayer, Int> = \.avatar
        let _: (Int, SimPlayer, Int, Bool) -> LeaderboardRow = LeaderboardRow.init(rank:player:value:isMe:)
        let _: WritableKeyPath<LeaderboardRow, Int> = \.rank
        let _: WritableKeyPath<LeaderboardRow, SimPlayer> = \.player
        let _: WritableKeyPath<LeaderboardRow, Int> = \.value
        let _: WritableKeyPath<LeaderboardRow, Bool> = \.isMe
        let _: ([LeaderboardRow], Int, Int) -> LeaderboardPage = LeaderboardPage.init(rows:myRank:total:)
        let _: WritableKeyPath<LeaderboardPage, [LeaderboardRow]> = \.rows
        let _: WritableKeyPath<LeaderboardPage, Int> = \.myRank
        let _: WritableKeyPath<LeaderboardPage, Int> = \.total
        let _: (String, Int, String, Int, [LedgerEntry]) -> PlayerStanding = PlayerStanding.init(name:avatar:country:level:ledger:)
        let _: WritableKeyPath<PlayerStanding, String> = \.name
        let _: WritableKeyPath<PlayerStanding, Int> = \.avatar
        let _: WritableKeyPath<PlayerStanding, String> = \.country
        let _: WritableKeyPath<PlayerStanding, Int> = \.level
        let _: WritableKeyPath<PlayerStanding, [LedgerEntry]> = \.ledger

        let _: (UInt64, SocialConfig, NameBank) -> SocialWorld = SocialWorld.init(installSeed:config:names:)
        let _: (SocialWorld) -> (LeaderboardKind, PlayerStanding, SocialTime, ClosedRange<Int>) -> LeaderboardPage =
            SocialWorld.page(_:me:at:ranks:)
        let _: (SocialWorld) -> (LeaderboardKind, PlayerStanding, SocialTime, Int, Int) -> LeaderboardPage =
            SocialWorld.page(_:me:at:around:radius:)
        let _: (SocialWorld) -> (Int, SocialTime) -> [LeaderboardRow] = SocialWorld.weeklyPodium(week:at:)
        let _: (SocialWorld) -> (UInt64) -> SimPlayer = SocialWorld.player(_:)
        let _: (SocialWorld) -> (EventInstance, PlayerStanding, SocialTime) -> [RaceStanding] = SocialWorld.streakRace(_:player:at:)
        let _: (SocialWorld) -> (EventInstance, SocialTime, SocialTime) -> [RaceStanding] = SocialWorld.rocketRace(_:joinedAt:at:)
        let _: (SocialWorld) -> (SkyJumpRun, SocialTime) -> SkyJumpField = SocialWorld.skyJump(_:at:)
        let _: (Date, inout Int64) -> SocialTime = SocialClock.now(wall:highWater:)

        let world = SocialWorld(installSeed: 1, config: SocialConfig(), names: NameBank())
        let me = PlayerStanding(name: "player_abc1234", avatar: 0, country: "TR", level: 32, ledger: [])
        let t = SocialTime(seconds: 1_790_000_000)
        _ = world.page(.world, me: me, at: t, ranks: 1...50)
        _ = world.page(.country("TR"), me: me, at: t, around: 1, radius: 10)
        _ = world.weeklyPodium(week: 21, at: t)
        _ = world.player(7)
        let rivals: any RivalProvider = world
        _ = rivals.streakRace(EventInstance(event: .streakRace, index: 0, start: t, end: t), player: me, at: t)
        var high: Int64 = 0
        XCTAssertEqual(SocialClock.now(wall: Date(timeIntervalSince1970: 5), highWater: &high).seconds, 5)
    }

    // MARK: Rules (C2, §4.4): BoardState, RuleEvent, RuleAck, RulesTuning

    func testBoardStateSurface() {
        let level = LevelSpec(level: 1, source: .designed, cols: 6, rows: 3, timerSeconds: 180, arrows: [
            ArrowSpec(id: ArrowID(0), cells: [Cell(0, 1), Cell(1, 1)], dir: .right),
            ArrowSpec(id: ArrowID(1), cells: [Cell(4, 0), Cell(4, 1), Cell(4, 2)], dir: .down),
        ])
        let _: (LevelSpec, RulesTuning) -> BoardState = BoardState.init(level:rules:)
        let b = BoardState(level: level, rules: .default)
        let _: KeyPath<BoardState, LevelSpec> = \.level
        let _: KeyPath<BoardState, RulesTuning> = \.rules
        let _: KeyPath<BoardState, Grid> = \.grid
        let _: KeyPath<BoardState, [ArrowID]> = \.live
        let _: KeyPath<BoardState, [ArrowID]> = \.hidden
        let _: KeyPath<BoardState, Bool> = \.isCleared
        let _: KeyPath<BoardState, Int> = \.remaining
        let _: KeyPath<BoardState, [ArrowID]> = \.markedArrows
        let _: KeyPath<BoardState, [ObstacleID: Int]> = \.counters
        let _: KeyPath<BoardState, [ObstacleID]> = \.targetedDoors
        let _: (BoardState) -> (Cell) -> ArrowID? = BoardState.owner(of:)
        let _: (BoardState) -> (ArrowID) -> TapResolution = BoardState.resolve(tap:)
        let _: (BoardState) -> (TapResolution) -> [RuleEvent] = BoardState.commit(_:)
        let _: (BoardState) -> (RuleAck) -> [RuleEvent] = BoardState.ack(_:)
        let _: (BoardState) -> () -> [[ArrowID]] = BoardState.freeUnits
        let _: (BoardState) -> () -> BoardState = BoardState.copy
        let _: (BoardState) -> (ArrowID) -> Bool = BoardState.isFree(_:)
        let _: (BoardState) -> (ArrowID) -> Bool = BoardState.isAlive(_:)
        let _: (BoardState) -> (ArrowID) -> Bool = BoardState.isLive(_:)
        let _: (BoardState) -> (ArrowID) -> Bool = BoardState.isMarked(_:)
        let _: (BoardState) -> (ArrowID) -> Bool = BoardState.isBumping(_:)
        let _: (BoardState) -> (ArrowID) -> [ArrowID] = BoardState.unit(of:)
        let _: (BoardState) -> (ObstacleID) -> DoorState? = BoardState.doorState(_:)
        let _: (BoardState) -> (ObstacleID) -> Bool = BoardState.isDone(_:)
        XCTAssertEqual(b.owner(of: Cell(0, 1)), ArrowID(0))
        XCTAssertEqual(b.freeUnits(), [[ArrowID(1)]])
        let r = b.resolve(tap: ArrowID(1))
        XCTAssertEqual(b.copy().commit(r), [])
        XCTAssertEqual(b.ack(.doorBurst("d9")), [])
        XCTAssertEqual(DoorState.allCases, [.locked, .targeted, .open])
        let events: [RuleEvent] = [.keyDispatched(key: "k0", door: "d0"), .doorOpened("d0", revealed: []),
                                   .pipeUsed("p0", remaining: 1), .pipeBroken("p0"), .counterChanged("b0", remaining: 2),
                                   .counterBroken("b0", revealed: []), .elevatorActivated("e0", revealed: []),
                                   .bumpContact(ArrowID(0), repeat: false), .arrowMarked(ArrowID(0))]
        XCTAssertEqual(events.count, 9)
        let acks: [RuleAck] = [.bumpContact(ArrowID(0)), .bumpFinished(ArrowID(0)), .doorBurst("d0")]
        XCTAssertEqual(acks.count, 3)
    }

    func testRulesTuningSurface() {
        let _: () -> RulesTuning = RulesTuning.init
        let r = RulesTuning.default
        let _: WritableKeyPath<RulesTuning, RulesTuning.Tape> = \.tape
        let _: WritableKeyPath<RulesTuning, RulesTuning.Bump> = \.bump
        let _: WritableKeyPath<RulesTuning, RulesTuning.Pipe> = \.pipe
        let _: WritableKeyPath<RulesTuning, RulesTuning.Box> = \.box
        let _: WritableKeyPath<RulesTuning, RulesTuning.Elevator> = \.elevator
        let _: WritableKeyPath<RulesTuning, RulesTuning.Hit> = \.hit
        let _: WritableKeyPath<RulesTuning, RulesTuning.Combo> = \.combo
        let _: WritableKeyPath<RulesTuning, RulesTuning.Clock> = \.clock
        let _: WritableKeyPath<RulesTuning, RulesTuning.Session> = \.session
        let _: WritableKeyPath<RulesTuning, [String: [RulesTuning.FailStep]]> = \.failChain
        let _: WritableKeyPath<RulesTuning, RulesTuning.Rewards> = \.rewards
        let _: WritableKeyPath<RulesTuning, RulesTuning.Boosters> = \.boosters
        let _: WritableKeyPath<RulesTuning.Tape, RulesTuning.TapeBlockedPolicy> = \.blockedPolicy
        let _: WritableKeyPath<RulesTuning.Bump, Bool> = \.repeatOnMarkedCostsHeart
        let _: WritableKeyPath<RulesTuning.Bump, Bool> = \.startsTimer
        let _: WritableKeyPath<RulesTuning.Bump, Double> = \.arrowEdgeInset
        let _: WritableKeyPath<RulesTuning.Bump, Double> = \.obstacleEdgeInset
        let _: WritableKeyPath<RulesTuning.Bump, [String: Double]?> = \.apexPast
        let _: (RulesTuning.Bump) -> (Dir) -> Double = RulesTuning.Bump.apex(_:)
        let _: WritableKeyPath<RulesTuning.Pipe, RulesTuning.PipeCountMoment> = \.countAt
        let _: WritableKeyPath<RulesTuning.Pipe, Bool> = \.missingCounterIsUnlimited
        let _: WritableKeyPath<RulesTuning.Pipe, Bool> = \.bumpConsumes
        let _: WritableKeyPath<RulesTuning.Pipe, Int> = \.maxHops
        let _: WritableKeyPath<RulesTuning.Box, RulesTuning.BoxCountMoment> = \.countAt
        let _: WritableKeyPath<RulesTuning.Box, Bool> = \.missingCounterIsUnlimited
        let _: WritableKeyPath<RulesTuning.Elevator, Bool> = \.emptyCellsBlock
        let _: WritableKeyPath<RulesTuning.Hit, Double> = \.radiusPt
        let _: WritableKeyPath<RulesTuning.Hit, TieBreak> = \.tieBreak
        let _: WritableKeyPath<RulesTuning.Combo, Double> = \.window
        let _: WritableKeyPath<RulesTuning.Combo, Bool> = \.bumpBreaks
        let _: WritableKeyPath<RulesTuning.Clock, [Int]> = \.alerts
        let _: WritableKeyPath<RulesTuning.Clock, Bool> = \.emptyTapStartsTimer
        let _: WritableKeyPath<RulesTuning.Session, [HoldReason]> = \.inputLockingHolds
        let _: (Int, RulesTuning.StepGrant, Int, ContinueOffer.Warning, Bool) -> RulesTuning.FailStep =
            RulesTuning.FailStep.init(price:grant:amount:warning:onlyWithStreak:)
        let _: KeyPath<RulesTuning.FailStep, ContinueOffer.Grant> = \.offerGrant
        let _: WritableKeyPath<RulesTuning.Rewards, Int> = \.normal
        let _: (RulesTuning.Rewards) -> (LevelTag) -> Int = RulesTuning.Rewards.reward(for:)
        let _: WritableKeyPath<RulesTuning.Boosters, [String: RulesTuning.BoosterAction]> = \.actions
        let _: WritableKeyPath<RulesTuning.Boosters, Double> = \.freezeSeconds
        let _: WritableKeyPath<RulesTuning.Boosters, Double> = \.freezeFlight
        let _: WritableKeyPath<RulesTuning.Boosters, Bool> = \.freezeRunsBeforeStart
        let _: WritableKeyPath<RulesTuning.Boosters, Int> = \.hintUnits
        let _: WritableKeyPath<RulesTuning.Boosters, RulesTuning.HintPolicy> = \.hintPolicy
        let _: KeyPath<RulesTuning.Boosters, Double> = \.freezeTotal
        let _: (RulesTuning.Boosters) -> (BoosterID) -> RulesTuning.BoosterAction = RulesTuning.Boosters.action(_:)
        let _: (RulesTuning) -> (ContinueOffer.Kind, Bool) -> [ContinueOffer] = RulesTuning.chain(_:streakActive:)
        let _: (Data?, [String: String]) -> (rules: RulesTuning, problems: [String]) = RulesTuning.load(json:overrides:)
        let _: (Data) -> [String] = RulesTuning.unknownKeys(in:)
        XCTAssertEqual(RulesTuning.TapeBlockedPolicy.allCases, [.bundleBumps, .tappedBumps])
        XCTAssertEqual(RulesTuning.PipeCountMoment.allCases, [.enter, .leave])
        XCTAssertEqual(RulesTuning.BoxCountMoment.allCases, [.tap, .leave])
        XCTAssertEqual(RulesTuning.StepGrant.allCases, [.addTime, .refillHearts, .none])
        XCTAssertEqual(RulesTuning.BoosterAction.allCases, [.freezeTimer, .hint, .none])
        XCTAssertEqual(RulesTuning.HintPolicy.allCases, [.unblocksMost])
        XCTAssertEqual(RulesTuning.defaultFailChain.count, 2)
        XCTAssertEqual(r.chain(.outOfTime, streakActive: true).count, 3)
        XCTAssertEqual(r.boosters.freezeTotal, 11.6)                     // 10 s + the ruled 1.6 s flight (SPEC.md §5 item 29)
        XCTAssertEqual(r.rewards.reward(for: .hard), 60)
    }

    // MARK: Session (C2, §4.5–§4.7): LevelSession, LevelClock, ClockEvent, ComboTracker

    func testLevelSessionSurface() {
        let level = LevelSpec(level: 5, source: .designed, cols: 4, rows: 1, timerSeconds: 120,
                              arrows: [ArrowSpec(id: ArrowID(0), cells: [Cell(0, 0), Cell(1, 0)], dir: .right)])
        let plan = SessionPlan(id: "L5", levels: [5])
        let _: (SessionPlan, [LevelSpec], AttemptSetup, RulesTuning) -> LevelSession = LevelSession.init(plan:stages:setup:rules:)
        let s = LevelSession(plan: plan, stages: [level], setup: AttemptSetup(levels: [5]))   // rules: .default
        let _: KeyPath<LevelSession, Phase> = \.phase
        let _: KeyPath<LevelSession, Int> = \.stage
        let _: KeyPath<LevelSession, BoardState> = \.board
        let _: KeyPath<LevelSession, LevelClock> = \.clock
        let _: KeyPath<LevelSession, Int> = \.hearts
        let _: KeyPath<LevelSession, SessionPlan> = \.plan
        let _: KeyPath<LevelSession, [LevelSpec]> = \.stages
        let _: KeyPath<LevelSession, AttemptSetup> = \.setup
        let _: KeyPath<LevelSession, RulesTuning> = \.rules
        let _: KeyPath<LevelSession, ComboTracker> = \.combo
        let _: KeyPath<LevelSession, Bool> = \.started
        let _: KeyPath<LevelSession, Int> = \.bumps
        let _: KeyPath<LevelSession, Int> = \.heartsLost
        let _: KeyPath<LevelSession, Int> = \.taps
        let _: ReferenceWritableKeyPath<LevelSession, Bool> = \.streakActive
        let _: KeyPath<LevelSession, LevelSpec> = \.level
        let _: KeyPath<LevelSession, Bool> = \.isFinished
        let _: KeyPath<LevelSession, LevelTag> = \.tag
        let _: (LevelSession) -> () -> [SessionEvent] = LevelSession.start
        let _: (LevelSession) -> (ArrowID?, TimeInterval) -> [SessionEvent] = LevelSession.tap(_:at:)
        let _: (LevelSession) -> (Double) -> [SessionEvent] = LevelSession.tick(_:)
        let _: (LevelSession) -> (SessionAck) -> [SessionEvent] = LevelSession.ack(_:)
        let _: (LevelSession) -> (HoldReason) -> Void = LevelSession.hold(_:)
        let _: (LevelSession) -> (HoldReason) -> Void = LevelSession.release(_:)
        let _: (LevelSession) -> (BoosterID) -> [SessionEvent] = LevelSession.useBooster(_:)
        // CORE-2 (SPEC.md rulings 30 + 31): the app's booster entry and the bulb's policy hint
        let _: (LevelSession) -> (BoosterID, RulesTuning.HintPolicy, Bool) -> [SessionEvent] =
            LevelSession.useBooster(_:hintPolicy:freezeFlightFromUse:)
        let _: (LevelSession) -> (RulesTuning.HintPolicy) -> [ArrowID]? = LevelSession.hint(policy:)
        let _: (LevelSession) -> () -> [SessionEvent] = LevelSession.acceptContinue
        let _: (LevelSession) -> () -> [SessionEvent] = LevelSession.declineContinue
        let _: (LevelSession) -> () -> [SessionEvent] = LevelSession.quit
        let _: (LevelSession) -> () -> [ArrowID]? = LevelSession.hint
        let _: (LevelSession) -> () -> SessionSnapshot = LevelSession.snapshot
        let _: (LevelSession) -> (ContinueOffer.Kind) -> [ContinueOffer] = LevelSession.chain(_:)
        XCTAssertEqual(s.start(), [.stageLoaded(stage: 0, of: 1, level: 5)])
        XCTAssertEqual(s.ack(.introFinished), [.timerArmed(stage: 0, seconds: 120)])
        s.hold(.pause); s.release(.pause)
        XCTAssertEqual(s.hint(), [ArrowID(0)])
        XCTAssertEqual(s.hint(policy: .unblocksMost), [ArrowID(0)])
        XCTAssertEqual(s.tick(1), [])
        XCTAssertEqual(s.tap(ArrowID(0), at: 0).last,
                       .won(WinResult(levels: [5], tag: .normal, timeLeft: 120, heartsLeft: 3, firstTry: true, reward: 20, bumps: 0)))
        XCTAssertEqual(s.acceptContinue(), [])
        XCTAssertEqual(s.declineContinue(), [])
        XCTAssertEqual(s.quit(), [])
        XCTAssertEqual(s.useBooster(.freeze), [])
        XCTAssertEqual(s.useBooster(.freeze, hintPolicy: .unblocksMost, freezeFlightFromUse: true), [])
        XCTAssertEqual(s.snapshot().phase, "won")
    }

    func testClockAndComboSurface() {
        let _: (Int, [Int], Bool) -> LevelClock = LevelClock.init(limit:alerts:freezeRunsBeforeStart:)
        var c = LevelClock(limit: 90)
        let _: KeyPath<LevelClock, Int> = \.limit
        let _: KeyPath<LevelClock, Double> = \.remaining
        let _: KeyPath<LevelClock, Bool> = \.started
        let _: KeyPath<LevelClock, Set<HoldReason>> = \.holds
        let _: KeyPath<LevelClock, Double> = \.freezeRemaining
        let _: KeyPath<LevelClock, [Int]> = \.alerts
        let _: WritableKeyPath<LevelClock, Bool> = \.freezeRunsBeforeStart
        let _: KeyPath<LevelClock, Bool> = \.isRunning
        let _: KeyPath<LevelClock, Int> = \.displayedSeconds
        let _: KeyPath<LevelClock, Bool> = \.isFrozen
        let _: KeyPath<LevelClock, Bool> = \.isExpired
        let _: KeyPath<LevelClock, Double> = \.freezeLead                 // CORE-2, ruling 30
        let _: KeyPath<LevelClock, Bool> = \.freezeWaitsForFirstTap
        // mutating members: pinned through closures (a mutating method cannot be referenced unapplied)
        let _: (inout LevelClock) -> Void = { $0.startOnFirstTap() }
        let _: (inout LevelClock, Double) -> [ClockEvent] = { $0.tick($1) }
        let _: (inout LevelClock, HoldReason) -> Void = { $0.hold($1) }
        let _: (inout LevelClock, HoldReason) -> Void = { $0.release($1) }
        let _: (inout LevelClock, Double) -> Void = { $0.freeze($1) }
        let _: (inout LevelClock, Double, Double) -> Void = { $0.freeze($1, lead: $2) }
        let _: (inout LevelClock, Int) -> Void = { $0.add($1) }
        c.startOnFirstTap(); c.hold(.popup); c.release(.popup); c.freeze(1); c.add(5)
        XCTAssertEqual(c.tick(2), [.freezeEnded])
        XCTAssertEqual(c.remaining, 94)
        var led = LevelClock(limit: 10)
        led.freeze(2, lead: 1)
        XCTAssertEqual(led.freezeLead, 1)
        XCTAssertEqual(led.tick(1.5), [])
        XCTAssertTrue(led.freezeWaitsForFirstTap)
        XCTAssertEqual(led.freezeRemaining, 1)
        let clockEvents: [ClockEvent] = [.expired, .freezeEnded, .alert(10)]
        XCTAssertEqual(clockEvents.count, 3)

        let _: (Double, Bool) -> ComboTracker = ComboTracker.init(window:bumpBreaks:)
        var k = ComboTracker()
        let _: WritableKeyPath<ComboTracker, Double> = \.window
        let _: WritableKeyPath<ComboTracker, Bool> = \.bumpBreaks
        let _: KeyPath<ComboTracker, Int> = \.count
        let _: KeyPath<ComboTracker, TimeInterval?> = \.lastTap
        let _: (inout ComboTracker, TimeInterval, Bool) -> Int = { $0.register(tapAt: $1, isBump: $2) }
        let _: (ComboTracker) -> (TimeInterval) -> Int = ComboTracker.peek(at:)
        let _: (inout ComboTracker) -> Void = { $0.reset() }
        XCTAssertEqual(k.register(tapAt: 0, isBump: false), 1)
        XCTAssertEqual(k.peek(at: 1), 2)
        k.reset()
        XCTAssertEqual(k.count, 0)
    }

    // MARK: Solver (C2 greedy + hint, §4.14) and HeadlessDriver (§4.15)

    func testSolverAndDriverSurface() {
        let level = LevelSpec(level: 5, source: .designed, cols: 4, rows: 1, timerSeconds: 120,
                              arrows: [ArrowSpec(id: ArrowID(0), cells: [Cell(0, 0), Cell(1, 0)], dir: .right)])
        let _: (LevelSpec, RulesTuning) -> GreedyResult = Solver.greedy(_:rules:)
        let _: (BoardState) -> GreedyResult = Solver.greedy(from:)
        let _: (BoardState) -> [ArrowID]? = Solver.hintUnit(_:)
        // CORE-2, ruling 31
        let _: (BoardState, RulesTuning.HintPolicy) -> [ArrowID]? = Solver.hintUnit(_:policy:)
        let _: (BoardState) -> [Solver.HintScore] = Solver.hintScores(_:)
        let _: ([ArrowID], Int, Int) -> Solver.HintScore = Solver.HintScore.init(unit:unblocks:cells:)
        let _: WritableKeyPath<Solver.HintScore, [ArrowID]> = \.unit
        let _: WritableKeyPath<Solver.HintScore, Int> = \.unblocks
        let _: WritableKeyPath<Solver.HintScore, Int> = \.cells
        let _: (Int, [[ArrowID]], [Int], [ArrowID], Int) -> GreedyResult = GreedyResult.init(rounds:order:roundSizes:stuck:freeAtStart:)
        let g = Solver.greedy(level)
        let _: WritableKeyPath<GreedyResult, Int> = \.rounds
        let _: WritableKeyPath<GreedyResult, [[ArrowID]]> = \.order
        let _: WritableKeyPath<GreedyResult, [Int]> = \.roundSizes
        let _: WritableKeyPath<GreedyResult, [ArrowID]> = \.stuck
        let _: WritableKeyPath<GreedyResult, Int> = \.freeAtStart
        let _: KeyPath<GreedyResult, Bool> = \.solved
        XCTAssertEqual(g, GreedyResult(rounds: 1, order: [[ArrowID(0)]], roundSizes: [1], stuck: [], freeAtStart: 1))
        XCTAssertEqual(Solver.hintUnit(BoardState(level: level)), [ArrowID(0)])
        XCTAssertEqual(Solver.hintUnit(BoardState(level: level), policy: .unblocksMost), [ArrowID(0)])
        XCTAssertEqual(Solver.hintScores(BoardState(level: level)), [Solver.HintScore(unit: [ArrowID(0)], unblocks: 0, cells: 2)])

        let _: (DriverConfig.Strategy, Double, Double, UInt64, DriverConfig.ContinuePolicy) -> DriverConfig =
            DriverConfig.init(strategy:tapInterval:mistakes:seed:continues:)
        var cfg = DriverConfig()
        let _: WritableKeyPath<DriverConfig, DriverConfig.Strategy> = \.strategy
        let _: WritableKeyPath<DriverConfig, Double> = \.tapInterval
        let _: WritableKeyPath<DriverConfig, Double> = \.mistakes
        let _: WritableKeyPath<DriverConfig, UInt64> = \.seed
        let _: WritableKeyPath<DriverConfig, DriverConfig.ContinuePolicy> = \.continues
        let _: WritableKeyPath<DriverConfig, Double> = \.introDuration
        let _: WritableKeyPath<DriverConfig, Double> = \.stageGap
        let _: WritableKeyPath<DriverConfig, Double> = \.doorBurst
        let _: WritableKeyPath<DriverConfig, BumpCurve> = \.bump
        let _: WritableKeyPath<DriverConfig, ExitKinematics> = \.exits
        let _: WritableKeyPath<DriverConfig, Double> = \.maxSeconds
        let _: WritableKeyPath<DriverConfig, Bool> = \.recordEvents
        XCTAssertEqual(DriverConfig.Strategy.allCases, [.solver, .randomFree])
        cfg.continues = .accept(max: 1)
        let _: (LevelSpec, RulesTuning, DriverConfig) -> DriverResult = HeadlessDriver.play(level:rules:config:)
        let _: (LevelSession, DriverConfig) -> DriverResult = HeadlessDriver.play(_:config:)
        let r = HeadlessDriver.play(level: level, rules: .default, config: cfg)
        let _: WritableKeyPath<DriverResult, Bool> = \.won
        let _: WritableKeyPath<DriverResult, Int> = \.timeLeft
        let _: WritableKeyPath<DriverResult, Double> = \.remaining
        let _: WritableKeyPath<DriverResult, Double> = \.timeLeftFraction
        let _: WritableKeyPath<DriverResult, Int> = \.heartsLeft
        let _: WritableKeyPath<DriverResult, Int> = \.bumps
        let _: WritableKeyPath<DriverResult, Int> = \.taps
        let _: WritableKeyPath<DriverResult, [SessionEvent]> = \.events
        let _: WritableKeyPath<DriverResult, Phase> = \.phase
        let _: WritableKeyPath<DriverResult, Double> = \.elapsed
        let _: WritableKeyPath<DriverResult, [ArrowID]> = \.stuck
        let _: WritableKeyPath<DriverResult, LossReason?> = \.loss
        XCTAssertTrue(r.won)
        XCTAssertEqual(r.timeLeft, 120)
    }
}
