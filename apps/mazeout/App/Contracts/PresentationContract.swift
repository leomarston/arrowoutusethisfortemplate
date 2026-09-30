import Foundation
import SwiftUI
import PathCore

// ◆ CONTRACT (SPEC-architecture §3.5, §6.5, §6.7, §8.1). Written by the LEAD in WP0 and FROZEN: any change goes through
// the orchestrator (build/wp0/frozen-contracts.sha256).
// GAME writes the models (HUDModel only through its HUDWriter, ≤ 10 Hz); SHELL's views read them and implement the FX.
// HUD views never touch the session.

// MARK: - HUD model (§6.5)

/// One heart of the timer pill (3 slots; dim one by one from the right on a bump contact).
enum HeartSlotVM: String, Equatable, Sendable { case full, lost, empty }

enum BoosterSlotState: Equatable, Sendable {
    case stock(Int)                  // the badge count
    case empty                       // 0 left: tapping opens the buy popup
    case locked                      // not unlocked yet
    case active                      // its effect is running (freeze)

    /// The `hud.booster.<id>` accessibility value: "stock:n" | "empty" | "locked" | "active" (§9.8).
    var accessibilityValue: String {
        switch self {
        case .stock(let n): return "stock:\(n)"
        case .empty: return "empty"
        case .locked: return "locked"
        case .active: return "active"
        }
    }
}

/// One booster corner (left: freeze, right: hint on v552).
struct BoosterSlotVM: Identifiable, Equatable, Sendable {
    var id: BoosterID
    var state: BoosterSlotState
    /// Template phase 5 (additive): the corner's art slot (`BoosterSpec.icon`; nil = `booster.<id>.icon`) and, for a module
    /// booster the shell has no name for, its name's string key (the corner's label, and its face when the slot has no art).
    var icon: String?
    var nameKey: String?
    init(id: BoosterID, state: BoosterSlotState, icon: String? = nil, nameKey: String? = nil) {
        self.id = id; self.state = state; self.icon = icon; self.nameKey = nameKey
    }
}

/// The HUD intro (the top row drops, the boosters slide in, the big timer and the hearts pop; §6.5). Times are
/// `MotionClock.gameTime` seconds, so captures can freeze it.
enum HUDIntroPhase: Equatable, Sendable {
    case hidden                      // before the level screen shows (hard cut from home)
    case playing(start: Double)      // the intro runs from `start`
    case shown                       // at rest (also: the FTUE's first board, where the HUD is already in place)
}

/// Written ONLY by GAME's HUDWriter. Timer text is written only when the displayed second changes; hearts, boosters
/// and coins on their events; nothing on a tap frame (§8.2).
@MainActor @Observable final class HUDModel {
    var levelLabel: LocalizedStringResource?        // "Level 32" / "Levels 1-4" (hud.level); nil before a level
    var tag: LevelTag = .normal                      // the level tab / back / pause colours (the timer pill stays blue)
    var timerText = ""                               // "3:00"
    var timerSeconds = 0                             // hud.timer accessibility value
    var timerFrozen = true                           // before the first tap, during holds
    var hearts: [HeartSlotVM] = []
    var coins = 0
    var boosters: [BoosterSlotVM] = []
    var introPhase: HUDIntroPhase = .hidden
    var isVisible = false
    /// Template phase 5 (additive): the widgets the active module declares (`PuzzleCapabilities.hud`, in slot order); the
    /// default is the reference game's timer + hearts. The counters' values: moves left (`movesChanged`) and the goals
    /// (`goalProgress`; the progress / goals / score widgets read them).
    var widgets: [HUDWidget] = [.timer, .hearts]
    var movesLeft: Int?
    var goals: [GoalState] = []
    init() {}
}

// MARK: - Anchors (screen frames that FX, tutorials and flights aim at)

enum AnchorID: Hashable, Sendable {
    // home
    case avatar, coinPill, livesPill, settings, levelPlate, playButton, clawBar
    case eventBadge(EventID)
    case navTab(HomeTab)
    // HUD
    case hudCoins, back, levelTab, timerPill, hearts, pause
    case heart(Int)
    case booster(BoosterID)
    // popups, tutorials
    case popupButton(String)                         // "<popupID>.<button>", e.g. "continue.primary"
    case custom(String)
}

/// Global frames of the views FX, tutorials and the coin flight aim at.
@MainActor @Observable final class AnchorRegistry {
    private(set) var frames: [AnchorID: CGRect] = [:]
    init() {}
    func frame(_ id: AnchorID) -> CGRect? { frames[id] }
    func set(_ id: AnchorID, _ rect: CGRect) { if frames[id] != rect { frames[id] = rect } }
    func remove(_ id: AnchorID) { frames[id] = nil }
}

private struct AnchorModifier: ViewModifier {
    let id: AnchorID
    @Environment(AnchorRegistry.self) private var registry: AnchorRegistry?
    func body(content: Content) -> some View {
        content
            .onGeometryChange(for: CGRect.self, of: { $0.frame(in: .global) }, action: { registry?.set(id, $0) })
            .onDisappear { registry?.remove(id) }
    }
}

extension View {
    /// Publishes this view's global frame under `id` in the environment's AnchorRegistry.
    func anchor(_ id: AnchorID) -> some View { modifier(AnchorModifier(id: id)) }
}

// MARK: - FX (§6.4 step 7, §6.7; Core Animation layers, not per-frame SwiftUI, D13)

enum FXEffect {
    /// The win celebration: the "ARROW" sign, the arrow sign, "OUT!" slam, the dim, confetti, two rockets; the win
    /// panel is due at +3.36 s; a tap anywhere skips to the end (`skip`). Silent (VERIFIED sounds §1).
    case celebration(LevelTag)
    case confetti(in: CGRect)
    case fireworks(in: CGRect)
    /// The home payout: "+N" over the level plate, `coins` coins fly `from` → `to`, each arrival adds N/coins.
    case coinFly(amount: Int, coins: Int, from: CGPoint, to: CGPoint)
    case sparkles(at: CGPoint)
    /// Escape hatch: a new effect without a contract change (SHELL documents the ids it accepts).
    case custom(id: String, params: [String: Double])
}

struct FXHandle: Hashable, Sendable {
    let id: Int
    init(id: Int) { self.id = id }
}

@MainActor protocol FXPlaying: AnyObject {
    @discardableResult func play(_ effect: FXEffect) -> FXHandle
    /// Returns when the effect has finished (or at once after `skip`/`stop`, or for an unknown handle).
    func finished(_ handle: FXHandle) async
    /// Jumps to the effect's end state (celebration tap-to-skip).
    func skip(_ handle: FXHandle)
    func stop(_ handle: FXHandle)
    func stopAll()
    var isPlaying: Bool { get }
}

/// Placeholder until SHELL's FX host lands: every effect finishes at once.
@MainActor final class NullFX: FXPlaying {
    private var next = 0
    func play(_ effect: FXEffect) -> FXHandle { next += 1; return FXHandle(id: next) }
    func finished(_ handle: FXHandle) async {}
    func skip(_ handle: FXHandle) {}
    func stop(_ handle: FXHandle) {}
    func stopAll() {}
    var isPlaying: Bool { false }
}

// MARK: - Level hosting (how SHELL shows a level without knowing GAME's types)

/// One Play (one session), created per LevelLaunch. SHELL's router hard-cuts to the level (§6.1): `start()` builds the
/// session and loads the board synchronously (no await, no spinner, §8.5), then `makeView()` is shown; `teardown()`
/// when the level screen goes away.
@MainActor protocol LevelHosting: AnyObject {
    var launch: LevelLaunch { get }
    /// false = refused (e.g. no lives: GAME has already routed to its popup); the router stays where it is.
    func start() -> Bool
    func makeView() -> AnyView
    func teardown()
}

// GAME installs itself by declaring, in its OWN file:
//     extension GameEntry {
//         static func makeLevel(_ launch: LevelLaunch, app: AppModel) -> any LevelHosting { GameController(launch, app: app) }
//     }
// A static member declared on the concrete enum wins over the protocol-extension default below; keep the signature EXACT.
@MainActor protocol GameEntryPoint {
    static func makeLevel(_ launch: LevelLaunch, app: AppModel) -> any LevelHosting
}

// F3-A (SPEC.md ruling 52(a), N-02; contract amend 5): the WP0 placeholder default is Debug-only. In a Release or Measure build
// GameEntry MUST declare makeLevel (GAME's GameController.swift does), or the build fails.
#if DEBUG
extension GameEntryPoint {
    static func makeLevel(_ launch: LevelLaunch, app: AppModel) -> any LevelHosting {
        Log.mark("boot", "GameEntry.makeLevel: default (placeholder level)")
        return PlaceholderLevel(launch: launch)
    }
}
#endif

@MainActor enum GameEntry: GameEntryPoint {}

#if DEBUG
/// Placeholder until GAME lands: a white board-coloured screen with a plain label (no game content).
@MainActor final class PlaceholderLevel: LevelHosting {
    let launch: LevelLaunch
    init(launch: LevelLaunch) { self.launch = launch }
    func start() -> Bool { true }
    func makeView() -> AnyView {
        AnyView(ZStack {
            Color.white
            Text(verbatim: "level \(launch.levels.map(String.init).joined(separator: "-")): GAME not installed")
                .font(.system(size: 13, weight: .medium, design: .monospaced))
                .foregroundStyle(.black.opacity(0.5))
        }.ignoresSafeArea())
    }
    func teardown() {}
}
#endif
