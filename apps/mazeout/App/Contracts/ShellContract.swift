import Foundation
import SwiftUI
import PathCore

// ◆ CONTRACT (SPEC-architecture §3.5, §6.1, §6.6, §6.8, §9.1). Written by the LEAD in WP0 and FROZEN: any change goes
// through the orchestrator (build/wp0/frozen-contracts.sha256).
// SHELL implements (Router, PopupHost, ToastCenter, StoreService / FakeStore, the FX host, RootView); SOCIAL (SOC2)
// plugs its event screens and the leaderboard tab in through `SocialEntry`; GAME and the LEAD call.

// MARK: - Navigation (§6.1): full-screen states, no NavigationStack

enum Screen: Equatable {
    case loading                                   // cold launch; the iOS notification prompt may sit over it (first launch)
    case home(HomeEntry, tab: HomeTab)             // the 3-tab bottom nav: shop · home · leaderboard
    case level(LevelLaunch)                        // the board + HUD
    case event(EventScreen)                        // full-screen event pages
    case profile
    case lab(LabID)                                // debug hosts (-pc.go boardlab | shelllab | soundboard | sociallab)

    /// The name the §9.3 log marks use: "loading", "home", "level(L32)", "event(claw)", "profile", "lab(boardlab)".
    var logName: String {
        switch self {
        case .loading: return "loading"
        case .home: return "home"
        case .level(let l): return "level(L\(l.levels.first ?? 0))"
        case .event(let e): return "event(\(e.rawValue))"
        case .profile: return "profile"
        case .lab(let id): return "lab(\(id.rawValue))"
        }
    }
}

enum HomeTab: String, CaseIterable, Sendable { case shop, home, leaderboard }

enum HomeEntry: Equatable {
    case normal
    case afterWin(WinSummary)                      // the coin payout (+ a new Hard / Super Hard look) on arrival
    case afterLoss
    case firstHome(WinSummary)                     // the FTUE's first home: +120 on the 1000 start (§6.2)
}

/// One Play: a session of 1…n stages ("Levels 1-4" is one launch with four levels).
struct LevelLaunch: Equatable, Hashable, Sendable {
    let session: String                            // SessionPlan.id
    let levels: [Int]
    let isRetry: Bool                              // Try Again: the same board
    let firstStage: Int                            // 0, or -pc.stage

    init(session: String, levels: [Int], isRetry: Bool = false, firstStage: Int = 0) {
        self.session = session; self.levels = levels; self.isRetry = isRetry; self.firstStage = firstStage
    }
}

struct WinSummary: Equatable {
    let levels: [Int]
    let reward: Int
    let tag: LevelTag
    let outcomes: [EventOutcome]                   // the event hooks' results (banners, claims, payouts)

    init(levels: [Int], reward: Int, tag: LevelTag, outcomes: [EventOutcome] = []) {
        self.levels = levels; self.reward = reward; self.tag = tag; self.outcomes = outcomes
    }
}

/// The full-screen event pages (`-pc.go event:<rawValue>`).
/// `balloonRise`: contract amend 4 (SPEC.md §5 item 42; events.md §8.1, the v582 rules in build/p/PH0/balloon.md) — the
/// Balloon Rise page (B1); its raw value equals the event's `EventID` string.
enum EventScreen: String, CaseIterable, Sendable { case claw, streakRace, rocketRace, skyJump, balloonRise }

/// Debug hosts (`-pc.go <rawValue>`).
enum LabID: String, CaseIterable, Sendable { case boardlab, shelllab, soundboard, sociallab }

@MainActor protocol Routing: AnyObject {
    var screen: Screen { get }
    /// Transitions with the §6.1 timings (hard cuts, cross-fades) are SHELL's. The router prints the §9.3 marks
    /// (`[PC][router] go level(L<n>)`, `level(L<n>) visible`, `home visible`, `[PC][launch] <screen> fully visible`).
    func go(_ screen: Screen)
}

/// Placeholder until SHELL's Router lands: holds the screen, no transitions.
@MainActor @Observable final class BasicRouter: Routing {
    private(set) var screen: Screen = .loading
    init() {}
    func go(_ screen: Screen) {
        Log.mark("router", "go \(screen.logName)")
        self.screen = screen
    }
}

// MARK: - Popups (§6.6): instant in and out; the dim reaches its alpha in 0–0.1 s

/// Popup ids. Raw values = the `-pc.popup <id>` names (§9.1) and the `popup.<id>` accessibility containers (§9.8).
enum PopupID: String, CaseIterable, Sendable {
    // level (S1)
    case pause, quitLevel
    // meta (S1)
    case settings
    // fail (S2)
    case outOfTime
    case continueOffer = "continue"
    case levelFailed
    // win (S2)
    case winPanel = "win"
    // first times (S2)
    case unlockOverlay = "unlock"
    case claimReward = "claim"
    // meta (S3)
    case username, editProfile, noLives, boosterBuy
    // social (SOC2)
    case weeklyContestTutorial = "weeklyTutorial"
    case weeklyContestIntro = "weeklyIntro"
    case clawInfo, skyJump, rocketRace
    case streakRaceBoard = "streakRace"
    // escape hatch
    case custom
}

/// Dim levels (VERIFIED uim): the numbers live in Tuning/ui.json `dim.<rawValue>` (0.90 / 0.90 / 0.94 / 0.96; WP0b added
/// info 0.95, weeklyTutorial 0.92, overPage 0.63 — SPEC-ui §1.3, CONSISTENCY §19 C-3).
enum DimToken: String, CaseIterable, Sendable { case popup, unlock, outOfTime, skyMatch, none, info, weeklyTutorial, overPage }

/// The unlock overlay's staggered beats in seconds (VERIFIED motion §5.3, tutorials §6); SHELL may read replacements
/// from Tuning/ui.json `unlock.*`.
struct UnlockBeats: Equatable, Sendable {  // SPEC-motion-audio §6.3 (CONSISTENCY T-25; SPEC.md §5 item 29, contract amend 2)
    var icon = 0.26                  // the icon pops (overshoot)
    var iconSettle = 0.54            // … and settles
    var title = 0.50
    var unlocked = 0.62              // "Unlocked!"
    var card = 0.78
    var sparkles = 1.14
    var dismissFade = 0.233          // contract amend 4 (SPEC.md §5 item 42; motion-catalog §6.7, v552): was 0.16
    var dismissMode = UnlockDismissMode.contentCut                     // contract amend 4 (the same)

    init(icon: Double = 0.26, iconSettle: Double = 0.54, title: Double = 0.50, unlocked: Double = 0.62, card: Double = 0.78,
         sparkles: Double = 1.14, dismissFade: Double = 0.233, dismissMode: UnlockDismissMode = .contentCut) {
        self.icon = icon; self.iconSettle = iconSettle; self.title = title; self.unlocked = unlocked; self.card = card
        self.sparkles = sparkles; self.dismissFade = dismissFade; self.dismissMode = dismissMode
    }
}

/// How the unlock overlay leaves after the dismiss tap (ui.json `unlock.dismissMode`; contract amend 4, motion-catalog §6.7):
/// `contentCut` = v552: the icon, title and card go in ONE frame, and the dim fades out LINEARLY over `dismissFade` (0.233 s);
/// `fade` = the pre-amend look: everything fades together over `dismissFade`.
enum UnlockDismissMode: String, Sendable { case contentCut, fade }

enum Entrance: Equatable, Sendable {
    case instant                     // every popup of v552 (VERIFIED motion §5.3)
    case staggered(UnlockBeats)      // the unlock overlay
}

struct PopupStyle: Equatable, Sendable {
    var dim: DimToken
    var dimFadeIn: Double = 0.0      // 0–0.1 s (VERIFIED motion §5.3)
    var entrance: Entrance = .instant
    var closesOnTapAnywhere = false  // unlock overlay, claim screens, "Tap to Continue" pages
    var holdsLevelTimer = true       // GAME adds HoldReason.popup while any popup is up in a level
    var inputLock = false            // forced tutorials (the Weekly Contest arrow at the trophy tab)

    init(dim: DimToken, dimFadeIn: Double = 0.0, entrance: Entrance = .instant, closesOnTapAnywhere: Bool = false,
         holdsLevelTimer: Bool = true, inputLock: Bool = false) {
        self.dim = dim; self.dimFadeIn = dimFadeIn; self.entrance = entrance; self.closesOnTapAnywhere = closesOnTapAnywhere
        self.holdsLevelTimer = holdsLevelTimer; self.inputLock = inputLock
    }

    static let standard = PopupStyle(dim: .popup)
    static let outOfTime = PopupStyle(dim: .outOfTime)
    static let unlock = PopupStyle(dim: .unlock, entrance: .staggered(UnlockBeats()), closesOnTapAnywhere: true)
    static let tapToContinue = PopupStyle(dim: .popup, closesOnTapAnywhere: true)
    static let skyMatch = PopupStyle(dim: .skyMatch)
}

/// Pays a continue offer's price; true = paid (it may put the Shop over the offer and re-check on close, §8.4).
typealias PayAction = @MainActor () async -> Bool

enum SkyJumpPage: String, CaseIterable, Sendable { case join, offer, matching, tutorial, progress, win }
enum RocketRacePage: String, CaseIterable, Sendable { case offer, tutorial, result }

/// Every popup and its parameters (copy and layout from SPEC-ui). SHELL switches over this to build the panel.
enum PopupRequest {
    case pause                                             // Sound, Haptic toggles, Resume, Quit, X
    case quitLevel                                         // "Quit Level?" / "You will lose a life!" / Quit / X
    case settings                                          // Sound, Music, Haptic, Notifications (+ offline states)
    case outOfTime(ContinueOffer, pay: PayAction)          // "Out of Time!" +30 sec, Add Time 900
    case continueOffer(ContinueOffer, pay: PayAction)      // "Continue?" variants: streak / token / life / hearts-out
    case levelFailed(levels: [Int], reason: LossReason)    // "Level Failed" + Try Again
    case winPanel(WinSummary)                              // normal / Hard / Super Hard + banner or race bar
    case unlockOverlay(FeatureID)                          // title, "Unlocked!", icon, card; tap anywhere
    case claimReward(Grant)                                // "Congratulations!" … "Tap to Claim"
    case username                                          // "Create your username:"
    case editProfile                                       // 3 × 3 avatars + Save
    case noLives
    case boosterBuy(BoosterID)
    case weeklyContestTutorial                             // the arrow at the trophy tab, input locked
    case weeklyContestIntro
    case clawInfo
    case skyJump(SkyJumpPage)
    case rocketRace(RocketRacePage)
    case streakRaceBoard
    case custom(id: String, params: [String: String])      // a new popup without a contract change

    var id: PopupID {
        switch self {
        case .pause: return .pause
        case .quitLevel: return .quitLevel
        case .settings: return .settings
        case .outOfTime: return .outOfTime
        case .continueOffer: return .continueOffer
        case .levelFailed: return .levelFailed
        case .winPanel: return .winPanel
        case .unlockOverlay: return .unlockOverlay
        case .claimReward: return .claimReward
        case .username: return .username
        case .editProfile: return .editProfile
        case .noLives: return .noLives
        case .boosterBuy: return .boosterBuy
        case .weeklyContestTutorial: return .weeklyContestTutorial
        case .weeklyContestIntro: return .weeklyContestIntro
        case .clawInfo: return .clawInfo
        case .skyJump: return .skyJump
        case .rocketRace: return .rocketRace
        case .streakRaceBoard: return .streakRaceBoard
        case .custom: return .custom
        }
    }
}

/// The answer of most popups (§6.6): primary = the main button (Resume, Play On, Add Time, Try Again, Continue, Claim,
/// Quit on quitLevel), secondary = the second button (Quit on pause), close = X / tap outside / dismissed.
enum PopupResult: Equatable, Sendable { case primary, secondary, close }
enum UsernameResult: Equatable, Sendable { case saved(String), close }
enum EditProfileResult: Equatable, Sendable { case saved(avatar: Int), close }

/// A typed popup request. `fallback` is the answer when no popup UI exists (the placeholder host) or the host is torn
/// down. SHELL's panel returns its answer as `Any`; the host casts it to R (`answer as? R ?? fallback`).
struct Popup<R> {
    let request: PopupRequest
    var style: PopupStyle
    let fallback: R
    init(_ request: PopupRequest, style: PopupStyle, fallback: R) {
        self.request = request; self.style = style; self.fallback = fallback
    }
}

extension Popup where R == PopupResult {
    static var pause: Popup { Popup(.pause, style: .standard, fallback: .primary) }
    static var quitLevel: Popup { Popup(.quitLevel, style: .standard, fallback: .close) }
    static var settings: Popup { Popup(.settings, style: .standard, fallback: .close) }
    static func outOfTime(_ offer: ContinueOffer, pay: @escaping PayAction) -> Popup {
        Popup(.outOfTime(offer, pay: pay), style: .outOfTime, fallback: .close)
    }
    static func continueOffer(_ offer: ContinueOffer, pay: @escaping PayAction) -> Popup {
        Popup(.continueOffer(offer, pay: pay), style: .standard, fallback: .close)
    }
    static func levelFailed(levels: [Int], reason: LossReason) -> Popup {
        Popup(.levelFailed(levels: levels, reason: reason), style: .standard, fallback: .close)
    }
    static func winPanel(_ summary: WinSummary) -> Popup { Popup(.winPanel(summary), style: .standard, fallback: .primary) }
    static func unlockOverlay(_ feature: FeatureID) -> Popup { Popup(.unlockOverlay(feature), style: .unlock, fallback: .close) }
    static func claimReward(_ grant: Grant) -> Popup { Popup(.claimReward(grant), style: .tapToContinue, fallback: .primary) }
    static var noLives: Popup { Popup(.noLives, style: .standard, fallback: .close) }
    static func boosterBuy(_ booster: BoosterID) -> Popup { Popup(.boosterBuy(booster), style: .standard, fallback: .close) }
    static var weeklyContestTutorial: Popup {
        Popup(.weeklyContestTutorial, style: PopupStyle(dim: .popup, holdsLevelTimer: false, inputLock: true), fallback: .primary)
    }
    static var weeklyContestIntro: Popup { Popup(.weeklyContestIntro, style: .tapToContinue, fallback: .close) }
    static var clawInfo: Popup { Popup(.clawInfo, style: .tapToContinue, fallback: .close) }
    static func skyJump(_ page: SkyJumpPage) -> Popup {
        Popup(.skyJump(page), style: page == .matching ? .skyMatch : .standard, fallback: .close)
    }
    static func rocketRace(_ page: RocketRacePage) -> Popup { Popup(.rocketRace(page), style: .standard, fallback: .close) }
    static var streakRaceBoard: Popup { Popup(.streakRaceBoard, style: .standard, fallback: .close) }
}

extension Popup where R == UsernameResult {
    static var username: Popup { Popup(.username, style: .standard, fallback: .close) }
}

extension Popup where R == EditProfileResult {
    static var editProfile: Popup { Popup(.editProfile, style: .standard, fallback: .close) }
}

@MainActor protocol PopupPresenting: AnyObject {
    var isPresenting: Bool { get }
    var topID: PopupID? { get }
    /// Pushes, awaits the user's answer, pops; stackable (a Shop over an offer, a claim over a win panel).
    func present<R>(_ popup: Popup<R>) async -> R
    func dismissAll()
}

/// Placeholder until SHELL's PopupHost lands: answers every popup with its fallback at once.
@MainActor final class ImmediatePopupHost: PopupPresenting {
    var isPresenting: Bool { false }
    var topID: PopupID? { nil }
    func present<R>(_ popup: Popup<R>) async -> R {
        Log.mark("popup", "\(popup.request.id.rawValue): no popup host installed, answering the fallback")
        return popup.fallback
    }
    func dismissAll() {}
}

// MARK: - Toasts (§6.6): one at a time, the newest replaces

@MainActor protocol ToastPresenting: AnyObject {
    func show(_ text: LocalizedStringResource)
}

/// Placeholder until SHELL's ToastCenter lands: logs the text.
@MainActor final class LogToasts: ToastPresenting {
    func show(_ text: LocalizedStringResource) { Log.mark("toast", String(localized: text)) }
}

// MARK: - Store (§6.8): FakeStore everywhere; StoreKit 2 only on the scheme's Run action with ArrowOut.storekit

struct StoreProductInfo: Equatable, Sendable, Identifiable {
    let id: String                    // com.manycode.arrowout.<id>
    let displayName: String           // from StoreKit / the catalogue (already localised data, not a code literal)
    let displayPrice: String
    init(id: String, displayName: String, displayPrice: String) {
        self.id = id; self.displayName = displayName; self.displayPrice = displayPrice
    }
}

enum PurchaseOutcome: Equatable, Sendable {
    case granted                      // verified: grant applied, transaction id recorded, finished
    case cancelled                    // .userCancelled RETURNS (it does not throw)
    case pending
    case failed(String)
}

@MainActor protocol StoreServicing: AnyObject {
    var products: [StoreProductInfo] { get }
    /// FakeStore: true, and the shop shows "Test store: nothing is charged".
    var isTestStore: Bool { get }
    /// Loads products and starts listening to Transaction.updates (unfinished transactions are granted once).
    func start() async
    func purchase(_ productID: String) async -> PurchaseOutcome
}

/// Placeholder until SHELL's StoreService / FakeStore land: sells nothing.
@MainActor final class UnavailableStore: StoreServicing {
    var products: [StoreProductInfo] { [] }
    var isTestStore: Bool { true }
    func start() async {}
    func purchase(_ productID: String) async -> PurchaseOutcome { .failed("store not installed") }
}

// MARK: - Entry points (how SHELL and SOCIAL plug in without editing LEAD files)
//
// SHELL declares, in its OWN files, any subset of:
//     extension ShellEntry {
//         static func makeRoot(_ app: AppModel) -> AnyView { AnyView(RootView(app: app)) }
//         static func makeRouter(_ ctx: AppContext) -> any Routing { Router(ctx) }
//         static func makePopups(_ ctx: AppContext) -> any PopupPresenting { PopupHost(ctx) }
//         static func makeToasts(_ ctx: AppContext) -> any ToastPresenting { ToastCenter(ctx) }
//         static func makeStore(_ ctx: AppContext) -> any StoreServicing { … FakeStore(ctx) … }
//         static func makeFX(_ ctx: AppContext) -> any FXPlaying { FXOverlay(ctx) }
//         static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? { name == "shelllab" ? … : nil }
//     }
// SOCIAL (SOC2) declares, in its OWN files:
//     extension SocialEntry {
//         static func makeEventScreen(_ screen: EventScreen, app: AppModel) -> AnyView { … }
//         static func makeLeaderboard(app: AppModel) -> AnyView { … }
//         static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? { name == "sociallab" ? … : nil }
//     }
// A static member declared on the concrete enum wins over the protocol-extension default. Keep the signatures EXACT: a
// typo silently keeps the default, and the boot log names every default still in use. RootView must honour
// `.lab(<id>)` through `DebugScreens.make(id.rawValue, app:)`.

@MainActor protocol ShellEntryPoint {
    static func makeRoot(_ app: AppModel) -> AnyView
    static func makeRouter(_ ctx: AppContext) -> any Routing
    static func makePopups(_ ctx: AppContext) -> any PopupPresenting
    static func makeToasts(_ ctx: AppContext) -> any ToastPresenting
    static func makeStore(_ ctx: AppContext) -> any StoreServicing
    static func makeFX(_ ctx: AppContext) -> any FXPlaying
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView?
}

extension ShellEntryPoint {
    // F3-A (SPEC.md ruling 52(a), N-02; contract amend 5): the WP0 boot placeholder default is Debug-only. In a Release or
    // Measure build ShellEntry MUST declare makeRoot (SHELL's RootView.swift does), or the build fails.
    #if DEBUG
    static func makeRoot(_ app: AppModel) -> AnyView {
        Log.mark("boot", "ShellEntry.makeRoot: default (WP0 boot placeholder)")
        return AnyView(BootPlaceholderView(app: app))
    }
    #endif
    static func makeRouter(_ ctx: AppContext) -> any Routing {
        Log.mark("boot", "ShellEntry.makeRouter: default"); return BasicRouter()
    }
    static func makePopups(_ ctx: AppContext) -> any PopupPresenting {
        Log.mark("boot", "ShellEntry.makePopups: default"); return ImmediatePopupHost()
    }
    static func makeToasts(_ ctx: AppContext) -> any ToastPresenting {
        Log.mark("boot", "ShellEntry.makeToasts: default"); return LogToasts()
    }
    static func makeStore(_ ctx: AppContext) -> any StoreServicing {
        Log.mark("boot", "ShellEntry.makeStore: default"); return UnavailableStore()
    }
    static func makeFX(_ ctx: AppContext) -> any FXPlaying {
        Log.mark("boot", "ShellEntry.makeFX: default"); return NullFX()
    }
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? { nil }
}

@MainActor enum ShellEntry: ShellEntryPoint {}

@MainActor protocol SocialEntryPoint {
    static func makeEventScreen(_ screen: EventScreen, app: AppModel) -> AnyView
    static func makeLeaderboard(app: AppModel) -> AnyView
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView?
}

extension SocialEntryPoint {
    static func makeEventScreen(_ screen: EventScreen, app: AppModel) -> AnyView {
        AnyView(NotInstalledView(text: "event \(screen.rawValue): SOCIAL not installed"))
    }
    static func makeLeaderboard(app: AppModel) -> AnyView {
        AnyView(NotInstalledView(text: "leaderboard: SOCIAL not installed"))
    }
    static func makeDebugScreen(_ name: String, app: AppModel) -> AnyView? { nil }
}

@MainActor enum SocialEntry: SocialEntryPoint {}

/// The owners' debug hosts reachable with `-pc.go <name>` (boardlab: BOARD, shelllab: SHELL, soundboard: AUDIO,
/// sociallab: SOCIAL).
@MainActor enum DebugScreens {
    static func make(_ name: String, app: AppModel) -> AnyView? {
        BoardEntry.makeDebugScreen(name, app: app)
            ?? ShellEntry.makeDebugScreen(name, app: app)
            ?? AudioEntry.makeDebugScreen(name, app: app)
            ?? SocialEntry.makeDebugScreen(name, app: app)
    }
}

/// A plain, honest "not built yet" screen for the defaults above (never game content).
struct NotInstalledView: View {
    let text: String
    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()
            Text(verbatim: text)
                .font(.system(size: 13, weight: .medium, design: .monospaced))
                .foregroundStyle(.black.opacity(0.5))
        }
    }
}
