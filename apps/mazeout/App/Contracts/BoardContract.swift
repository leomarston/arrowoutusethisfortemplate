import Foundation
import SwiftUI
import UIKit
import PathCore

// ◆ CONTRACT (SPEC-architecture §3.5, §5.10, §9.4). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256). BOARD implements (BoardEngine); GAME drives it.
// The engine QUEUES commands that arrive before its first layout and replays them after, and never awaits the layout of a
// view that is not in a window (GP §13 boot hang). One engine for the whole app run: created at boot, never destroyed.

@MainActor protocol BoardControlling: AnyObject {
    var delegate: BoardDelegate? { get set }
    var view: UIView { get }                                    // the BoardContainerView
    var inputEnabled: Bool { get set }
    var allowedArrows: Set<ArrowID>? { get set }                // tutorial restriction; nil = all
    var zoomScale: CGFloat { get }
    var pitchOnScreen: CGFloat { get }
    var isSettled: Bool { get }                                 // no mover, no transition, intro done (capture readiness)
    func prepare() async                                        // §5.9 warm-up behind Loading, idempotent
    func preload(_ levels: [LevelSpec])                         // background sprite decode for the next levels
    func load(_ stage: StageSetup)                              // build the rest layers (hidden until playIntro)
    func playIntro(_ style: IntroStyle)
    func present(_ events: [SessionEvent])                      // exits, bumps, marks, reveals, counters, hint, freeze
    func playStageTransition(to next: StageSetup)
    func playClearWave()
    func clear()
    func setHint(_ arrows: [ArrowID])                           // [] clears
    func screenPoint(of arrow: ArrowID) -> CGPoint?             // the arrow's hand anchor (tutorial) in screen pt
    func tapPoint(of arrow: ArrowID) -> CGPoint?                // a safe on-screen tap point (not under HUD/boosters)
    func setFrozen(_ frozen: Bool)                              // capture freeze (§5.12)
    func setTimeScale(_ k: Double)                              // slow motion
    func probe() -> BoardProbeData                              // §9.4
}

@MainActor protocol BoardDelegate: AnyObject {
    func boardFrame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval)      // the master clock (every frame)
    func boardReleased(arrow: ArrowID?, contentPoint: CGPoint, touchTimestamp: TimeInterval)
    func boardBeat(_ beat: BoardBeat)
    func boardZoomChanged(scale: CGFloat)
}

/// Presentation-timed facts, reported from animation delegates on the frame they happen (never timers, §5.5).
enum BoardBeat: Equatable {
    case introFinished
    case bumpContact(ArrowID)
    case bumpFinished(ArrowID)
    case doorBurst(ObstacleID)
    case pipeBroken(ObstacleID)
    case counterBroken(ObstacleID)
    case exitLeftBoard(ArrowID)
    case exitFinished(ArrowID)
    case lastExitLeftBoard
    case stageTransitionDone
    case clearWaveFinished
}

/// Everything the board needs to build one stage.
struct StageSetup {
    let level: LevelSpec
    let layout: BoardLayout
    let stage: Int                     // 0-based
    let stages: Int
    let seed: UInt64                   // fx stream (star jitter, shards)

    init(level: LevelSpec, layout: BoardLayout, stage: Int, stages: Int, seed: UInt64) {
        self.level = level; self.layout = layout; self.stage = stage; self.stages = stages; self.seed = seed
    }
}

enum IntroStyle: Equatable {
    case growFromTails                 // the build-in (Curves.buildIn) with the HUD drop in SwiftUI
    case growFromTailsNoHUD            // the FTUE's first board: the HUD is already in place after the Loading cross-fade
    case none
}

/// The §9.4 `board.probe` JSON (accessibilityValue under -pc.uitest 1, Documents/probe.json under -pc.probeFile 1).
/// Keys are EXACT (VERIFY parses them). The board fills its half (zoom, pitch, settled, moving, fps, arrows' x/y/red,
/// obstacles' state); GAME merges the session's half (lvl, stage, stages, phase, t, timerStarted, hearts, combo, free,
/// unit, hidden, counters) before publishing.
struct BoardProbeData: Codable, Equatable {
    struct Arrow: Codable, Equatable {
        var id: Int
        var x: Double                  // board.tapPoint(of:) in screen pt (visible, not under the HUD or boosters)
        var y: Double
        var free: Bool                 // from the session's rules
        var unit: [Int]                // the tap unit (tape bundle)
        var red: Bool                  // marked by a bump

        init(id: Int, x: Double, y: Double, free: Bool = false, unit: [Int] = [], red: Bool = false) {
            self.id = id; self.x = x; self.y = y; self.free = free; self.unit = unit; self.red = red
        }
    }

    struct Obstacle: Codable, Equatable {
        var id: String
        var k: String                  // ObstacleKind raw value
        var n: Int?                    // counter (pipe passes / box clears left)
        var state: String?             // door: locked | opening | open; elevator: idle | active

        init(id: String, k: String, n: Int? = nil, state: String? = nil) {
            self.id = id; self.k = k; self.n = n; self.state = state
        }
    }

    var lvl = 0
    var stage = 0
    var stages = 1
    var phase = ""
    var t = 0.0                        // remaining seconds
    var timerStarted = false
    var hearts = 0
    var zoom = 1.0
    var pitch = 0.0                    // pt per cell on screen
    var settled = false
    var moving = 0                     // arrows in motion
    var combo = 0
    var fps = 0.0
    var arrows: [Arrow] = []
    var hidden: [Int] = []
    var obstacles: [Obstacle] = []

    init() {}

    /// Compact JSON with sorted keys (the accessibilityValue / probe.json text).
    func json() -> String {
        let e = JSONEncoder()
        e.outputFormatting = [.sortedKeys]
        return (try? e.encode(self)).map { String(decoding: $0, as: UTF8.self) } ?? "{}"
    }
}

// MARK: - Entry point (how BOARD plugs in without editing LEAD files)
//
// BOARD installs the one app-lifetime engine by declaring, in its OWN file:
//     extension BoardEntry {
//         static func makeBoard(_ ctx: AppContext) -> any BoardControlling { BoardEngine(ctx) }
//         static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? { name == "boardlab" ? AnyView(BoardLab(app: app)) : nil }
//     }
// A static member declared on the concrete enum wins over the protocol-extension default below. Keep the signatures
// EXACT: a typo silently keeps the default, and the boot log names every default still in use.

@MainActor protocol BoardEntryPoint {
    static func makeBoard(_ ctx: AppContext) -> any BoardControlling
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView?
}

extension BoardEntryPoint {
    // F3-A (SPEC.md ruling 52(a), N-02; contract amend 5): the WP0 placeholder default is Debug-only. In a Release or Measure
    // build BoardEntry MUST declare makeBoard (BOARD's BoardHost.swift does), or the build fails — no store build can fall
    // back to a placeholder board.
    #if DEBUG
    static func makeBoard(_ ctx: AppContext) -> any BoardControlling {
        Log.mark("boot", "BoardEntry.makeBoard: default (placeholder board)")
        return PlaceholderBoard()
    }
    #endif
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? { nil }
}

@MainActor enum BoardEntry: BoardEntryPoint {}

#if DEBUG
/// Placeholder until BOARD lands: a white view that accepts every command and does nothing.
@MainActor final class PlaceholderBoard: BoardControlling {
    weak var delegate: BoardDelegate?
    let view: UIView = {
        let v = UIView()
        v.backgroundColor = .white
        v.accessibilityIdentifier = "board"
        return v
    }()
    var inputEnabled = false
    var allowedArrows: Set<ArrowID>?
    var zoomScale: CGFloat { 1 }
    var pitchOnScreen: CGFloat { 0 }
    var isSettled: Bool { true }
    func prepare() async {}
    func preload(_ levels: [LevelSpec]) {}
    func load(_ stage: StageSetup) {}
    func playIntro(_ style: IntroStyle) { delegate?.boardBeat(.introFinished) }
    func present(_ events: [SessionEvent]) {}
    func playStageTransition(to next: StageSetup) { delegate?.boardBeat(.stageTransitionDone) }
    func playClearWave() { delegate?.boardBeat(.clearWaveFinished) }
    func clear() {}
    func setHint(_ arrows: [ArrowID]) {}
    func screenPoint(of arrow: ArrowID) -> CGPoint? { nil }
    func tapPoint(of arrow: ArrowID) -> CGPoint? { nil }
    func setFrozen(_ frozen: Bool) {}
    func setTimeScale(_ k: Double) {}
    func probe() -> BoardProbeData { var p = BoardProbeData(); p.settled = true; return p }
}
#endif
