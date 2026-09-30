import Foundation
import SwiftUI
import UIKit
import PathCore

// Template phase 2 (docs/architecture/PUZZLE-MODULE.md §2–§4, contract v1-candidate). What the Game layer (App/Game/*)
// talks to instead of the arrow-typed `BoardControlling` / `LevelSession`:
//   PuzzleBoard      the module's board (any rendering tech), hosted edge to edge; input comes back already hit-tested as a
//                    `PuzzleInput`, visual beats as `PuzzleAck`s;
//   PuzzlePlugin     the app half of a puzzle module: the session factory over the module's content, its capabilities
//                    (GameCore's `PuzzleModule`), tutorials and unlock cards in generic form, bot helpers;
//   ActivePuzzle     THE ONE PLACE a game picks its puzzle module.
// The feel budget stays binding: input → session → `present` synchronously in the board's release handler, one Core Animation
// transaction (the board's own), no hitch > 20 ms. The shell never sits between the finger and the first moving pixel.

// MARK: - The board

/// How a stage's board builds in (`PuzzleBoard.playIntro`). Moved from BoardContract.swift (the arrow board's contract) in the
/// kit decoupling step: the Game layer picks it, every board reads it (a board without a build-in treats both grow styles as
/// its own intro, SortPuzzleBoard). The case names are the reference board's (its arrows grow from their tails).
enum IntroStyle: Equatable {
    case growFromTails                 // the build-in (Curves.buildIn) with the HUD drop in SwiftUI
    case growFromTailsNoHUD            // the FTUE's first board: the HUD is already in place after the Loading cross-fade
    case none
}

/// Everything a board needs to build one stage.
struct StageContext {
    let stage: Int                     // 0-based
    let stages: Int
    let seed: UInt64                   // fx stream (per stage)
    let screen: CGSize                 // the screen the board lays out on (pt)
    let info: PuzzleStage              // the module's level travels in `info.content`
}

/// A board's own timing notes for the same-frame proof and the bench (nil for boards without them, e.g. test fakes).
struct BoardDiagnostics {
    var lastRippleAt: CFTimeInterval
    var lastPresentMs: Double
    var presentNotes: [String]
    var hitchesLoad: Int
    var hitchesPlay: Int
}

@MainActor protocol PuzzleBoardDelegate: AnyObject {
    /// The master clock (every display-link frame).
    func boardFrame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval)
    /// A released touch, hit-tested by the board (inside its release handler: answer synchronously).
    func boardInput(_ input: PuzzleInput, touchTimestamp: TimeInterval)
    /// A presentation-timed beat the rules wait for.
    func boardAck(_ ack: PuzzleAck)
    /// A purely visual beat with its own haptic (a burst); nothing for the rules.
    func boardFeedback(_ haptic: Haptic)
    func boardZoomChanged(scale: CGFloat)
    /// The Play's session (the board's probe reads its half from it).
    var activeSession: (any PuzzleSession)? { get }
}

/// The Game layer's board. One per app run (created at boot, never destroyed); commands before the first layout queue.
@MainActor protocol PuzzleBoard: AnyObject {
    var delegate: PuzzleBoardDelegate? { get set }
    var view: UIView { get }
    var inputEnabled: Bool { get set }
    /// Tutorial restriction; nil = every target.
    var allowedTargets: Set<PuzzleTarget>? { get set }
    /// Warm-up behind Loading (idempotent).
    func prepare() async
    /// Builds the stage (hidden until `playIntro`).
    func load(_ stage: StageContext)
    /// → `.introFinished`.
    func playIntro(_ style: IntroStyle)
    /// Animates what the session decided (the whole batch, in order; the board picks its own `.puzzle` events).
    func present(_ outputs: [SessionOutput])
    /// → `.stageTransitionDone`.
    func playStageTransition(to next: StageContext)
    /// The win's clear wave at W.
    func playClearWave()
    /// The tutorial hand's fingertip on screen: the target's anchor, offset by `at` in the board's own coordinates.
    func handPoint(for target: PuzzleTarget, at: [Double]?) -> CGPoint?
    /// Plays a tap on `target` through the board's real release handler (bots, debug jumps); false = not possible now
    /// (the caller then feeds the input to the delegate itself).
    func performTap(on target: PuzzleTarget) -> Bool
    /// Publishes the UI-test probe now (`-pc.uitest` / `-pc.probeFile`), e.g. on a timer start/stop edge.
    func publishProbe()
    var diagnostics: BoardDiagnostics? { get }
    /// Template phase 5 (additive, default false): the board feeds PerfMonitor / LatencyProbe itself (ArrowEscape's engine:
    /// its display link, the hitch and tap-latency logs). Every other board is metered by the Play from the delegate's
    /// `boardFrame` / `boardInput` (GameController's `BoardFrameMeter`).
    var metersFrames: Bool { get }
}

extension PuzzleBoard {
    var metersFrames: Bool { false }
}

/// Hosts the one app-lifetime board view edge to edge (BoardHostView adopts it and never re-creates it).
struct PuzzleBoardHost: UIViewRepresentable {
    let board: any PuzzleBoard

    func makeUIView(context: Context) -> BoardHostView {
        let v = BoardHostView()
        v.adopt(board.view)
        return v
    }

    func updateUIView(_ uiView: BoardHostView, context: Context) {
        uiView.adopt(board.view)
    }

    static func dismantleUIView(_ uiView: BoardHostView, coordinator: ()) {
        uiView.releaseHosted()
    }
}

// MARK: - The module's app half

@MainActor protocol PuzzlePlugin: AnyObject {
    /// GameCore `PuzzleModule.id` ("arrow-escape").
    var id: String { get }
    var capabilities: PuzzleCapabilities { get }
    /// The session's boards (content lookup + the module's launch-argument overrides); nil = a level is missing (logged; the
    /// Play is refused before the lives gate, so it costs no life).
    func stages(for plan: SessionPlan, args: LaunchArgs) -> [PuzzleStage]?
    /// The Play's session over `stages` (from `stages(for:args:)`).
    func makeSession(plan: SessionPlan, stages: [PuzzleStage], setup: AttemptSetup, streakActive: Bool) -> any PuzzleSession
    /// The module's tutorial steps and unlock cards (content).
    var tutorials: [TutorialStep] { get }
    var unlocks: [FeatureUnlock] { get }
    /// Targets a deliberate mistake could use right now, in board order (the autoplayer's mistakes, `-pc.lose hearts`).
    func mistakeTargets(_ session: any PuzzleSession, board: any PuzzleBoard) -> [PuzzleTarget]
    /// A headless won session for the first-win warm-up, run off the main thread (FIX-2 A, V3-01).
    func warmUpWin() -> @Sendable () -> WinResult?
    /// Template phase 5 (additive, default none): the module's boosters the shell has no built-in texts or economy for
    /// (their buy popup, the HUD corner's label, their stock and pack; from the module's data file).
    var moduleBoosters: [ModuleBooster] { get }
    /// Template phase 5 (additive, default nil): the continue popup's grant line for a grant the shell cannot word itself
    /// (a module action: "+1 Tube"); nil = the shell's generic line.
    func grantText(_ grant: ContinueOffer.Grant) -> LocalizedStringResource?
}

extension PuzzlePlugin {
    var moduleBoosters: [ModuleBooster] { [] }
    func grantText(_ grant: ContinueOffer.Grant) -> LocalizedStringResource? { nil }
    /// The module booster `id` (nil = a booster the shell words itself, or none).
    func moduleBooster(_ id: BoosterID) -> ModuleBooster? { moduleBoosters.first { $0.id == id } }
}

/// How a module plugs into the app (the WP0 entry-point pattern). Template phase 5: AppModel asks the ACTIVE module (and only
/// it) for its boot content, its app-lifetime engine and its boosters' economy, so a game never builds another module's
/// engine or level library.
@MainActor protocol PuzzleEntryPoint {
    static func makePlugin(_ app: AppModel) -> any PuzzlePlugin
    static func makeBoard(_ app: AppModel) -> any PuzzleBoard
    /// The module's content loaded at boot, before the services (default: no library, the bundle's Levels/sessions.json).
    static func loadContent(bundle: Bundle) -> PuzzleBootContent
    /// The module's app-lifetime engine behind its board, built where the services are (default: none).
    static func makeEngine(_ ctx: AppContext) -> (any BoardControlling)?
    /// The module's boosters from its data (default: none); AppModel and the shop's economy table add their stock and packs.
    static func moduleBoosters(bundle: Bundle, tune: [String: String]) -> [ModuleBooster]
}

extension PuzzleEntryPoint {
    static func loadContent(bundle: Bundle) -> PuzzleBootContent {
        PuzzleBootContent(library: nil, provider: nil, sessions: AppModel.loadSessions(bundle: bundle))
    }
    static func makeEngine(_ ctx: AppContext) -> (any BoardControlling)? { nil }
    static func moduleBoosters(bundle: Bundle, tune: [String: String]) -> [ModuleBooster] { [] }
}

/// What the active module loads at boot (ArrowEscape: its level library, the C4 provider and the session plans).
struct PuzzleBootContent {
    var library: LevelLibrary?
    var provider: LevelProvider?
    var sessions: [SessionPlan]
}

/// Template phase 5: a booster a module declares that the shell has no built-in texts or economy for (SortPuzzle's `undo`,
/// `extraTube`). From the module's data file (`boosters.<id>`: startStock, packCount, price, name, description); `name` and
/// `description` are string-catalogue keys (strings.tsv, 13 languages).
struct ModuleBooster: Equatable, Sendable {
    var id: BoosterID
    var startStock: Int
    var pack: EconomyRules.BoosterPack
    var name: String
    var description: String

    var nameResource: LocalizedStringResource { LocalizedStringResource(String.LocalizationValue(name)) }
    var descriptionResource: LocalizedStringResource { LocalizedStringResource(String.LocalizationValue(description)) }

    /// The `boosters.<id>` entries of a module's data file for `ids` (capabilities order); an entry without a price, a pack
    /// count or its texts is left out (logged: the booster then has no shop economy).
    static func list(_ file: TuningFile, ids: [BoosterID]) -> [ModuleBooster] {
        ids.compactMap { (id: BoosterID) -> ModuleBooster? in
            let k = "boosters.\(id.rawValue)."
            guard file.has("boosters.\(id.rawValue)") else { return nil }
            guard file.has(k + "price"), file.has(k + "packCount"), let name = file.value(k + "name") as? String,
                  let text = file.value(k + "description") as? String, !name.isEmpty, !text.isEmpty else {
                Log.error("tuning", "\(file.name).json boosters.\(id.rawValue): price, packCount, name and description are required")
                return nil
            }
            return ModuleBooster(id: id, startStock: max(0, file.int(k + "startStock", 0)),
                                 pack: EconomyRules.BoosterPack(count: max(0, file.int(k + "packCount", 0)),
                                                                price: max(0, file.int(k + "price", 0))),
                                 name: name, description: text)
        }
    }
}

extension EconomyRules {
    /// Adds a module's boosters to the table: their start stock and their own pack, only for ids the table does not list
    /// (rules.json wins). Without module boosters (ArrowEscape) the table is untouched.
    mutating func addModuleBoosters(_ list: [ModuleBooster]) {
        for b in list where economy.startBoosters[b.id.rawValue] == nil && economy.boosterPacks[b.id.rawValue] == nil {
            economy.startBoosters[b.id.rawValue] = b.startStock
            economy.boosterPacks[b.id.rawValue] = b.pack
        }
    }
}

/// THE ONE LINE A NEW GAME CHANGES: the active puzzle module's entry point (its app half lives next to its board; ArrowEscape's
/// is App/Board/ArrowEscapePlugin.swift). Keep game.yml `puzzle.module` equal to the plugin's `id` (AppModel logs both).
/// Template phase 5: every module's app half is compiled in (SortPuzzle: App/Puzzles/SortPuzzle/); the compilation condition
/// `PC_PUZZLE_SORT` (SWIFT_ACTIVE_COMPILATION_CONDITIONS) selects SortPuzzle without editing this file.
@MainActor enum ActivePuzzle {
    #if PC_PUZZLE_SORT
    static let entry: any PuzzleEntryPoint.Type = SortPuzzleEntry.self
    #else
    static let entry: any PuzzleEntryPoint.Type = ArrowEscapeEntry.self
    #endif
}
