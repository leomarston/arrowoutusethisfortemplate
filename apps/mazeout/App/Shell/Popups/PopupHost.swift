import SwiftUI
import PathCore

// SHELL S1 (SPEC-architecture §6.6; adapted from apps/matchfactory PopupHost.swift, e10a076). A stack of popups: `present`
// pushes, awaits the answer, pops; stackable (a Shop over an offer, a claim over a win panel). The dim reaches its alpha in
// `style.dimFadeIn` (0 = one frame) and a popup disappears in one frame. A2 FEEL-P (owner item 8; motion-catalog §3.2, §6.2,
// §11.2-§11.3, VERIFIED v552 + v582 60 Hz; ruling 39 OD2): the PANEL enters with `PopupEntrance` — the boxed family PUNCHES
// (scale 1.022 → 0.967 → 1.000 over 0.133 s about its centre, per 60 Hz frame from ui.json `popup.punch`, Level Failed its own
// row), the band family (Quit Level?, Continue?) DROPS from above the screen (`popup.band.drop`, 18 frames: overshoot 28-32 pt,
// dip 6 pt, rest at +0.283 s); a band that replaces a band inside the fail chain only swaps its content (v582). Out of Time /
// Out of Lives, the win panel, Settings, pages, the unlock and claim screens keep their own (instant or staged) entrance. The dim
// alpha is the style's token in ui.json (`dim.popup` 0.90, `dim.unlock` 0.90, `dim.outOfTime` 0.94, `dim.skyMatch` 0.96).
// Panels are laid out on the virtual 393 x 852 canvas (ShellLayout). A request whose panel is not built yet shows a DEBUG
// "pending" panel; a Release build answers its fallback at once (never a stand-in on screen).

@MainActor @Observable final class PopupHost: PopupPresenting {
    struct Presented: Identifiable {
        let id: Int
        let request: PopupRequest
        let style: PopupStyle
        let shownAt: Double
        var entrance: PopupEntrance = .none
        /// A2: the band's exit while it runs (a fall keeps the popup in the stack; a rise is a ghost in `leaving`).
        var exit: PopupExit?
        var ghost = false
        /// A3: presented while a closing popup was still drawn (a hand-over) — its dim starts at its alpha (no fade-in from 0).
        var bridged = false
        /// A3: answered and out of the logical stack, still drawn until its successor is committed (`closing`).
        var closingDrawn = false
        let resolve: (Any?) -> Void                  // nil = the fallback
    }

    private(set) var stack: [Presented] = []
    /// A2: cancelled bands rising off the screen (drawn, not presented: no input, not `isPresenting`).
    private(set) var leaving: [Presented] = []

    /// A3 GLITCH (owner item 5: "when I open the pause menu or quit the game and go back to menu, for milliseconds other
    /// pages appear"). A hand-over is ATOMIC. The last popup, answered with an answer that goes ON to a successor
    /// (`expectsSuccessor`: Quit, a declined offer, Level Failed, the win panel, a claim, the event pages; never Resume or an X,
    /// which close in one frame as before), leaves the logical `stack` at once (callers see it closed) and its PANEL goes on
    /// the answer's frame as before, but its DIM stays drawn (no input, out of the accessibility
    /// tree; a full page — the Weekly tutorial's own darkening — stays whole) in `closing` until its successor is committed
    /// in the same transaction: the next popup (`present`), the next screen (the router's cut calls `endBridge()` inside its
    /// own transaction), or a queued router transition and then the popup after it (`handOverFollowsTransition` /
    /// `transitionDone`: the Weekly tutorial → the Leaderboard tab → its intro). When nothing follows, the dim goes
    /// `bridgeFrames` display frames later. Before, every chained step (Out of Lives! X → Continue?, the band's fall → Level
    /// Failed, Level Failed X → home, the win panel's Continue → home, Pause's Quit → Quit Level?, the tutorial → the intro)
    /// committed the pop on one run-loop turn and its successor turns later: the level showed UNDIMMED for one frame in
    /// between (blipscan, build/p/A3: whole-screen one-frame blips; counting main-actor turns instead of frames still missed
    /// the band → Level Failed and Level Failed → home chains, which take 4-8 ms of tasks, in r3).
    private(set) var closing: [Presented] = []
    /// Display frames the dim of an answered popup waits for a successor that is not a transaction of its own (the chains
    /// above take 4-8 ms: under a frame); after them it goes. The panel itself went on the answer's frame.
    static let bridgeFrames = 2
    /// The popup whose hand-over is pending (tests, the router).
    var bridgeID: Int? { closing.last?.id }
    /// Router transitions queued while a hand-over is pending (a tab change the flow awaits before its next popup, e.g. the
    /// Weekly tutorial → the Leaderboard tab → the intro): the closing popup waits for them, then for `bridgeFrames` frames.
    @ObservationIgnored private var pendingTransitions = 0
    @ObservationIgnored private var nextID = 0
    @ObservationIgnored let ui: UITuning
    /// A2: when a band popup last closed (a band presented right after it swaps its content instead of dropping again).
    @ObservationIgnored private var bandClosedAt: Double = -1

    init(_ ctx: AppContext) { ui = ctx.tuning.ui }
    init(ui: UITuning) { self.ui = ui }

    var isPresenting: Bool { !stack.isEmpty }
    var topID: PopupID? { stack.last?.request.id }

    func present<R>(_ popup: Popup<R>) async -> R {
        #if !DEBUG
        guard PopupContent.hasPanel(popup.request) else {
            Log.error("popup", "\(popup.request.id.rawValue): no panel built yet; answering the fallback")
            return popup.fallback
        }
        #endif
        nextID += 1
        let id = nextID
        Log.mark("popup", "present \(popup.request.id.rawValue) #\(id) (stack \(stack.count + 1))")
        let now = ProcessInfo.processInfo.systemUptime
        var entrance = PopupEntrance.make(popup.request, ui: ui)
        if case .drop = entrance, now - bandClosedAt <= ui.file.double("popup.band.swapWithin", 0.15) {
            entrance = .none                                                         // A2: a band → band step swaps its content
        }
        if entrance != .none { Log.mark("popup", "entrance \(popup.request.id.rawValue) \(entrance.name)") }
        return await withCheckedContinuation { (cont: CheckedContinuation<R, Never>) in
            let once = Once()
            let fallback = popup.fallback
            var entry = Presented(id: id, request: popup.request, style: popup.style,
                                  shownAt: now, entrance: entrance) { [weak self] answer in
                once.run {
                    self?.pop(id, answer: answer)
                    cont.resume(returning: (answer as? R) ?? fallback)
                }
            }
            var t = Transaction(); t.disablesAnimations = true
            withTransaction(t) {
                // A3: the closing popup is replaced by this one in the same transaction (no frame between them)
                if !closing.isEmpty {
                    entry.bridged = true
                    Log.mark("popup", "hand-over #\(closing.map(\.id).map(String.init).joined()) → \(popup.request.id.rawValue) #\(id)")
                    closing.removeAll()
                    pendingTransitions = 0
                }
                stack.append(entry)
            }
        }
    }

    /// Answers the popup `id` (the panels call this through `PopupAnswer`). A2 (motion-catalog §11.2, VERIFIED v582): a band
    /// leaves as v582's does — cancelled (X on Quit Level?, Play On on Continue?) it RISES off the top as a non-interactive
    /// ghost while its dim fades linearly 0.30 s, and it is answered at once (the level resumes under it); going on with the
    /// fail (Quit, X on the last Continue?) it FALLS off the bottom after a 2-frame lift, the dim stays, input stays blocked, and
    /// it is answered once it is gone + `popup.band.exit.nextAfter` (the next screen follows it, as on v582). X on a Continue?
    /// that another Continue? follows swaps the content (no exit).
    func answer(_ id: Int, _ value: Any?) {
        guard let i = stack.firstIndex(where: { $0.id == id }), stack[i].exit == nil else { return }
        let p = stack[i]
        guard let exit = PopupExit.make(p.request, answer: value, ui: ui) else { p.resolve(value); return }
        Log.mark("popup", "exit \(p.request.id.rawValue) #\(id) \(exit.name)")
        var t = Transaction(); t.disablesAnimations = true
        switch exit {
        case .rise:
            var g = p
            g.exit = exit
            g.ghost = true
            withTransaction(t) {
                leaving.append(g)
                p.resolve(value)                                                     // pops it from `stack` in this transaction
            }
            Task { @MainActor [weak self] in
                try? await Task.sleep(nanoseconds: UInt64((exit.duration + 0.02) * 1_000_000_000))
                var t = Transaction(); t.disablesAnimations = true
                withTransaction(t) { self?.leaving.removeAll { $0.id == id } }
            }
        case .fall:
            withTransaction(t) { stack[i].exit = exit }
            let wait = exit.duration + ui.file.double("popup.band.exit.nextAfter", 0.10)
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: UInt64(wait * 1_000_000_000))
                p.resolve(value)
            }
        }
    }

    /// A2: popups whose dim is fading out (id → seconds, linear): the unlock card's contentCut dismiss (motion-catalog §6.7).
    private(set) var dimFading: [Int: Double] = [:]

    /// Fades popup `id`'s dim linearly to 0 over `seconds` (the panel answers when it is done; the dim goes with the popup).
    func fadeDim(_ id: Int, over seconds: Double) {
        dimFading[id] = max(0.001, seconds)
        Log.mark("popup", "dim fade #\(id) \(String(format: "%.3f", seconds)) s linear")
    }

    func dismissAll() {
        for p in stack.reversed() { p.resolve(nil) }
    }

    private func pop(_ id: Int, answer: Any? = nil) {
        let dimWasFading = dimFading[id] != nil
        dimFading[id] = nil
        guard let i = stack.firstIndex(where: { $0.id == id }) else { return }
        var t = Transaction(); t.disablesAnimations = true
        var handsOver = false
        let p = withTransaction(t) { () -> Presented in
            let p = stack.remove(at: i)
            // A3: the last popup's dim stays until its successor (see `closing`); the event pages stay whole (the Weekly
            // tutorial's own darkening → its intro; the Up & Away fall / Sky Jump progress / Rocket result pages → Level Failed
            // or home). Not: the player's own pages (Settings, Support / Terms / Privacy, the Shop — nothing follows them, they
            // close in one frame as before), a dim that faded out on purpose (the unlock card's content cut), or a band rising
            // away (its ghost is already drawn in `leaving`)
            if stack.isEmpty, Self.expectsSuccessor(p.request, answer: answer), !dimWasFading,
               !leaving.contains(where: { $0.id == id }), !PopupContent.isPage(p.request) || PopupPanels.pageHandsOver(p.request) {
                var c = p
                c.closingDrawn = true
                closing = [c]
                handsOver = true
            }
            return p
        }
        if PopupEntrance.isBand(p.request, ui: ui) { bandClosedAt = ProcessInfo.processInfo.systemUptime }
        Log.mark("popup", "close \(p.request.id.rawValue) #\(id)")
        if handsOver {
            pendingTransitions = 0
            endHandOverAfterFrames(id)
        }
    }

    /// Ends the hand-over of `id` when nothing has followed after `bridgeFrames` display frames and no router transition is
    /// pending (a pending one calls `transitionDone`, which starts the count again).
    private func endHandOverAfterFrames(_ id: Int) {
        Task { @MainActor [weak self] in
            // two 60 Hz frames of wall time (a display link here would add a run-loop source for a mere wait)
            try? await Task.sleep(nanoseconds: UInt64(Double(Self.bridgeFrames) / 60 * 1_000_000_000))
            guard let self, self.closing.contains(where: { $0.id == id }), self.pendingTransitions == 0 else { return }
            Log.mark("popup", "hand-over #\(id) → nothing after \(Self.bridgeFrames) frames")
            self.endBridge()
        }
        // safety net: never held longer than half a second (a transition that never reports back)
        Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: 500_000_000)
            guard let self, self.closing.contains(where: { $0.id == id }) else { return }
            self.pendingTransitions = 0
            self.endBridge("held 0.5 s: released")
        }
    }

    /// A3: whether this answer goes on to a successor (another popup, the next screen) — only those are handed over. Every
    /// other answer (Resume, an X, Settings, the offers taken) closes in ONE frame, panel and dim together, as v552 does.
    static func expectsSuccessor(_ r: PopupRequest, answer: Any?) -> Bool {
        let a = answer as? PopupResult
        switch r {
        case .pause: return a == .secondary                              // Quit → Quit Level?
        case .quitLevel: return a == .primary                            // Quit → the band falls → Level Failed
        case .outOfTime, .continueOffer: return a != .primary            // declined → the next offer, or Level Failed
        case .levelFailed, .winPanel: return true                        // → home, or the next board (Try Again, the FTUE chain)
        case .claimReward: return true                                   // → the next claim, or home's queue
        case .weeklyContestTutorial: return true                         // → the Leaderboard tab → its intro
        case .skyJump(let page): return page == .progress                // the progress page → home
        case .rocketRace(let page): return page == .result
        case .custom(let id, _): return id == "balloonFall"              // Up & Away's fall page → Level Failed
        default: return false
        }
    }

    /// A3 (the router): a transition was queued while a hand-over is pending.
    func handOverFollowsTransition() {
        guard !closing.isEmpty else { return }
        pendingTransitions += 1
    }

    /// A3 (the router): a queued transition is done; the hand-over's successor now has `bridgeFrames` frames to arrive.
    func transitionDone() {
        guard pendingTransitions > 0 else { return }
        pendingTransitions -= 1
        if pendingTransitions == 0, let id = closing.last?.id { endHandOverAfterFrames(id) }
    }

    /// A3: removes the closing popup (the router calls it inside a screen cut's transaction: the new screen replaces it).
    func endBridge(_ why: String? = nil) {
        guard !closing.isEmpty else { return }
        if let why { Log.mark("popup", "hand-over #\(closing.map(\.id).map(String.init).joined()) → \(why)") }
        pendingTransitions = 0
        var t = Transaction(); t.disablesAnimations = true
        withTransaction(t) { closing.removeAll() }
    }

    func dimAlpha(_ style: PopupStyle) -> Double { ui.dim(style.dim) }
}

/// Runs a closure at most once (continuation guards).
final class Once: @unchecked Sendable {
    private var done = false
    private let lock = NSLock()
    func run(_ body: () -> Void) {
        lock.lock()
        let first = !done
        done = true
        lock.unlock()
        if first { body() }
    }
}

/// What a panel needs to answer its popup.
struct PopupAnswer {
    let id: Int
    let host: PopupHost
    @MainActor func callAsFunction(_ value: Any?) { host.answer(id, value) }
}

struct PopupLayer: View {
    let host: PopupHost
    let app: AppModel

    var body: some View {
        ZStack(alignment: .topLeading) {
            // A2: the presented popups AND the cancelled bands rising away, in one list keyed by id: a band that is answered
            // moves from `stack` to `leaving` and keeps its view (no rebuild on the exit's first frame). A3: + the answered popup
            // still drawn until its successor is committed (`closing`), the same view
            ForEach((host.stack + host.leaving + host.closing).sorted { $0.id < $1.id }) { p in
                PopupContainer(presented: p, answer: PopupAnswer(id: p.id, host: host), app: app, dimAlpha: host.dimAlpha(p.style))
                    .zIndex(Double(p.id))
            }
        }
        .transaction { $0.animation = nil }
    }
}

/// Dim + panel of one popup.
private struct PopupContainer: View {
    let presented: PopupHost.Presented
    let answer: PopupAnswer
    let app: AppModel
    let dimAlpha: Double
    @State private var dimOn = false
    @State private var exitClock = ExitClock()
    /// A2: out of the accessibility tree until the entrance has landed (UI tests and VoiceOver meet the panel at rest: XCUITest
    /// resolved a button mid-drop and tapped where it no longer was — A2's UI run 4, ShellUITests.testQuitLevelPopupAnswersQuit).
    @State private var landed = false

    var body: some View {
        let style = presented.style
        ZStack(alignment: .topLeading) {
            // a full page is opaque and draws no dim (CONSISTENCY U-5: `DimToken.none` for the Settings page)
            let fadeOut = answer.host.dimFading[presented.id]
            Color.black.opacity(PopupContent.isPage(presented.request) ? 0
                                : (dimOn || style.dimFadeIn <= 0 || presented.bridged ? dimAlpha : 0))   // A3: bridged = no fade-in
                .modifier(DimFadeOut(active: fadeOut != nil, duration: fadeOut ?? 0))           // A2: the linear dim fade-out
                .modifier(ExitEffect(exit: presented.exit, clock: exitClock, part: .dim))        // A2: a rising band's dim
                .contentShape(Rectangle())
                .onTapGesture { if style.closesOnTapAnywhere && !style.inputLock { answer(nil) } }
                .accessibilityHidden(true)
            if presented.closingDrawn && !PopupContent.isPage(presented.request) {
                EmptyView()     // A3: answered, waiting for its successor: the dim only (the panel went on the answer's frame)
            } else if PopupContent.isPage(presented.request) {
                // full pages (Settings, Support/Terms/Privacy) lay out on the live screen with top anchors (SPEC-ui §1.1)
                PopupContent.make(presented.request, style: style, answer: answer, app: app)
                    .environment(\.tapsLocked, style.inputLock)
            } else {
                ReferenceCanvas {
                    PopupContent.make(presented.request, style: style, answer: answer, app: app)
                        .modifier(PopupEntranceEffect(entrance: presented.entrance))              // A2: punch / band drop
                        .modifier(ExitEffect(exit: presented.exit, clock: exitClock, part: .panel))  // A2: band exits
                }
                .environment(\.tapsLocked, style.inputLock)
            }
        }
        .ignoresSafeArea()
        .allowsHitTesting(presented.exit == nil && !presented.closingDrawn)               // A2 / A3: leaving takes no input
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier(PopupContent.containerID(presented.request))
        .accessibilityShown(!presented.ghost && !presented.closingDrawn && (landed || presented.entrance == .none))   // A2, A3
        .task {
            guard presented.entrance != .none, !landed else { return }
            await FrameWaiter.frames(1)
            try? await Task.sleep(nanoseconds: UInt64((presented.entrance.duration + 0.02) * 1_000_000_000))
            landed = true
        }
        .onAppear {
            if style.dimFadeIn > 0 { withAnimation(.linear(duration: style.dimFadeIn)) { dimOn = true } } else { dimOn = true }
            guard !presented.ghost else { return }
            let id = presented.request.id.rawValue, t0 = presented.shownAt
            Task { @MainActor in
                await FrameWaiter.frames(1)
                let ms = (ProcessInfo.processInfo.systemUptime - t0) * 1000
                Log.mark("popup", "visible \(id) \(String(format: "%.1f", ms)) ms after present (dim \(String(format: "%.2f", dimAlpha)))")
            }
        }
    }
}

/// A2: the dim's linear fade-out (Animatable: SwiftUI interpolates `level` 1 → 0 over the duration; the popup layer's own
/// no-animation transaction does not reach this change).
private struct DimFadeOut: ViewModifier {
    let active: Bool
    let duration: Double
    func body(content: Content) -> some View {
        content.modifier(DimLevel(level: active ? 0 : 1)).animation(active ? .linear(duration: duration) : nil, value: active)
    }
}

private struct DimLevel: ViewModifier, Animatable {
    var level: Double
    var animatableData: Double {
        get { level }
        set { level = newValue }
    }
    func body(content: Content) -> some View { content.opacity(level) }
}

// MARK: - A2: the panel entrance (punch / band drop)

/// How a popup's panel enters (motion-catalog §6.2 / §11.2 / §11.3). Keyed per 60 Hz frame from the popup's first frame F.
enum PopupEntrance: Equatable {
    case none
    /// Scale of the panel per frame about `anchor` (reference pt: the panel's centre).
    case punch([Double], anchor: CGPoint)
    /// The band's vertical offset from rest in pt per frame (negative = above).
    case drop([Double])

    var name: String {
        switch self {
        case .none: return "none"
        case .punch(let k, _): return "punch \(k.first ?? 1)→\(k.min() ?? 1)→\(k.last ?? 1) \(k.count) frames"
        case .drop(let k): return "drop \(k.first ?? 0) pt, \(k.count) frames"
        }
    }

    /// The data key of a request: its PopupID, the page for the event popups ("skyJump.offer"), the layout for Continue?
    /// ("continue" = the band; "continue.time" / "continue.hearts" = the Out of Time layout, instant).
    static func key(_ r: PopupRequest) -> String {
        switch r {
        case .skyJump(let p): return "skyJump.\(p.rawValue)"
        case .rocketRace(let p): return "rocketRace.\(p.rawValue)"
        case .continueOffer(let offer, _):
            // ContinuePopup's layout with the Claw not running: no warning = the Out of Time layout (`continue.time` /
            // `continue.hearts`, instant); a streak / token / life warning = the band (kit decoupling: the host names no panel)
            guard offer.warning == .none else { return "continue" }
            return offer.kind == .outOfHearts ? "continue.hearts" : "continue.time"
        case .custom(let id, _): return id
        default: return r.id.rawValue
        }
    }

    static func isBand(_ r: PopupRequest, ui: UITuning) -> Bool {
        ui.file.strings("popup.band.ids", []).contains(key(r))
    }

    static func make(_ r: PopupRequest, ui: UITuning) -> PopupEntrance {
        let f = ui.file, k = key(r)
        if f.strings("popup.band.ids", []).contains(k) {
            let base = k.split(separator: ".").first.map(String.init) ?? k
            let keys = f.doubles("popup.band.drop.\(k)", f.doubles("popup.band.drop.\(base)", []))
            return keys.count > 1 ? .drop(keys) : .none
        }
        if f.strings("popup.punch.ids", []).contains(k) {
            let id = r.id.rawValue
            let keys = f.doubles("popup.punch.byId.\(k)", f.doubles("popup.punch.byId.\(id)", f.doubles("popup.punch.keys", [])))
            let a = f.doubles("popup.punch.anchor.\(id)", f.doubles("popup.punch.anchorDefault", [196.5, 426]))
            return keys.count > 1 && a.count == 2 ? .punch(keys, anchor: CGPoint(x: a[0], y: a[1])) : .none
        }
        return .none
    }

    /// The keyed value at `t` seconds from F (linear between frames; the last key after the end).
    static func value(_ keys: [Double], at t: Double) -> Double {
        guard let last = keys.last else { return 0 }
        let x = max(0, t) * 60
        let i = Int(x)
        if i >= keys.count - 1 { return last }
        return keys[i] + (keys[i + 1] - keys[i]) * (x - Double(i))
    }

    var duration: Double {
        switch self {
        case .none: return 0
        case .punch(let k, _), .drop(let k): return Double(max(0, k.count - 1)) / 60
        }
    }
}

/// How a band leaves (motion-catalog §11.2, VERIFIED v582 S4-R1a/b, S4-PH0b, S4-R5): the band's y offset from rest per 60 Hz
/// frame from the first frame after the answer (the first entry is already moved, as on v582), and for a rise the dim's linear
/// fade. ui.json `popup.band.exit`.
enum PopupExit: Equatable {
    case rise([Double], dimFade: Double)
    case fall([Double])

    var keys: [Double] { switch self { case .rise(let k, _), .fall(let k): return k } }
    var duration: Double { Double(keys.count) / 60 }
    var name: String {
        switch self {
        case .rise(let k, let d): return "rise \(k.count) frames, dim \(d) s"
        case .fall(let k): return "fall \(k.count) frames"
        }
    }

    static func make(_ r: PopupRequest, answer: Any?, ui: UITuning) -> PopupExit? {
        guard PopupEntrance.isBand(r, ui: ui) else { return nil }
        let f = ui.file
        let rise = PopupExit.rise(f.doubles("popup.band.exit.rise", []), dimFade: f.double("popup.band.exit.riseDim", 0.30))
        let fall = PopupExit.fall(f.doubles("popup.band.exit.fall", []))
        guard rise.keys.count > 1, fall.keys.count > 1 else { return nil }
        let a = answer as? PopupResult
        switch r {
        case .quitLevel:
            return a == .primary ? fall : rise                                       // Quit goes on; X / dismissed cancels
        case .continueOffer(let offer, _):
            if a == .primary { return rise }                                         // DECISION (unrecorded): the level goes on
            return offer.isLast ? fall : nil                                         // a next Continue? step swaps the content
        default:
            return nil
        }
    }

    func offset(at t: Double) -> Double {
        let k = keys
        let i = Int(max(0, t) * 60)
        return i < k.count ? k[i] : (k.last ?? 0)
    }

    func dim(at t: Double) -> Double {
        guard case .rise(_, let d) = self else { return 1 }
        return max(0, 1 - t / max(d, 0.001))
    }
}

/// A band exit on the dim or on the panel canvas, frame-locked (paused while no exit runs).
private struct ExitEffect: ViewModifier {
    enum Part { case dim, panel }
    let exit: PopupExit?
    let clock: ExitClock
    let part: Part

    func body(content: Content) -> some View {
        TimelineView(.animation(minimumInterval: nil, paused: exit == nil)) { ctx in
            let t = exit == nil ? 0 : clock.t(ctx.date)
            switch part {
            case .dim: content.opacity(exit?.dim(at: t) ?? 1)
            case .panel: content.offset(y: exit?.offset(at: t) ?? 0)
            }
        }
    }
}

/// The exit's clock: 0 on the first frame asked for, shared by the dim and the panel of one popup.
@MainActor private final class ExitClock {
    private var start: Date?
    func t(_ date: Date) -> Double {
        if start == nil { start = date }
        return date.timeIntervalSince(start ?? date)
    }
}

/// Plays a `PopupEntrance` on the panel canvas (never on the dim), FRAME-LOCKED: a TimelineView gives each presented frame its
/// display time, so frame k after F shows key k exactly (v552 / v582 are keyed per 60 Hz frame; a time-based SwiftUI animation
/// lands up to half a frame off that grid, measured). The first frame shows key 0 (the panel is whole at once, no wait); the
/// timeline pauses once the keys are done. Only the modifier runs per frame, never the panel's body.
private struct PopupEntranceEffect: ViewModifier {
    let entrance: PopupEntrance
    @State private var clock = EntranceClock()
    @State private var done = false

    func body(content: Content) -> some View {
        switch entrance {
        case .none:
            content
        case .punch, .drop:
            TimelineView(.animation(minimumInterval: nil, paused: done)) { ctx in
                content.modifier(KeyedEntrance(t: done ? entrance.duration : clock.t(ctx.date), entrance: entrance))
            }
            .task {
                // key 0 is held until the popup's first frame is on screen (a presentation's first commit can miss its
                // vsync: measured, the first frame then showed key 1); from the next frame on, frame k shows key k
                await FrameWaiter.frames(1)
                clock.arm()
                try? await Task.sleep(nanoseconds: UInt64((entrance.duration + 0.1) * 1_000_000_000))
                done = true
            }
        }
    }
}

/// The entrance's clock: 0 until armed (the first frame F is on screen), then F + one frame on the next frame asked for and the
/// frames' display times after.
@MainActor private final class EntranceClock {
    private var start: Date?
    private var armed = false
    func arm() { armed = true }
    func t(_ date: Date) -> Double {
        guard armed else { return 0 }
        if start == nil { start = date.addingTimeInterval(-1.0 / 60) }
        return date.timeIntervalSince(start ?? date)
    }
}

private struct KeyedEntrance: ViewModifier {
    let t: Double
    let entrance: PopupEntrance

    func body(content: Content) -> some View {
        switch entrance {
        case .punch(let keys, let a):
            content.scaleEffect(PopupEntrance.value(keys, at: t), anchor: UnitPoint(x: a.x / 393, y: a.y / 852))
        case .drop(let keys):
            content.offset(y: PopupEntrance.value(keys, at: t))
        case .none:
            content
        }
    }
}

/// The panel for each request: the component that registered it (ShellRegistry.swift `PopupPanels`; the reference game's
/// list is GameComponents.swift: pause, quitLevel, settings + the offline pages `.custom("page.support" | "page.terms" |
/// "page.privacy")`, the fail chain, the win panel, the unlock and claim screens, the S3 popups and the closable Shop, the
/// event popups). A request no component draws gets the DEBUG pending panel (Release answers its fallback: `present`).
@MainActor enum PopupContent {
    static func hasPanel(_ request: PopupRequest) -> Bool { PopupPanels.provider(for: request) != nil }

    /// `popup.<id>` (§9.8); a custom page is `popup.page.<name>`.
    static func containerID(_ request: PopupRequest) -> String {
        if case .custom(let id, _) = request { return "popup." + id }
        return "popup." + request.id.rawValue
    }

    /// Full-screen pages drawn on the live screen (not the scaled popup canvas).
    static func isPage(_ request: PopupRequest) -> Bool { PopupPanels.isPage(request) }

    @ViewBuilder static func make(_ request: PopupRequest, style: PopupStyle, answer: PopupAnswer, app: AppModel) -> some View {
        if let provider = PopupPanels.provider(for: request) {
            provider.make(request, answer)
        } else {
            PendingPopupPanel(id: request.id, answer: answer)
        }
    }
}

/// A popup whose panel is not built yet (DEBUG only: Release answers the fallback before presenting).
private struct PendingPopupPanel: View {
    let id: PopupID
    let answer: PopupAnswer

    var body: some View {
        #if DEBUG
        ZStack(alignment: .topLeading) {
            DebugPlaceholder(name: "popup \(id.rawValue): panel not built yet (tap to close)").placed(CGRect(40, 330, 313, 190))
                .contentShape(Rectangle())
                .onTapGesture { answer(nil) }
        }
        #else
        Color.clear
        #endif
    }
}

extension ShellEntry {
    static func makePopups(_ ctx: AppContext) -> any PopupPresenting { PopupHost(ctx) }
}
