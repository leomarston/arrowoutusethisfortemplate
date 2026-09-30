import SwiftUI
import UIKit
import PathCore

// GAME G2 (SPEC-architecture §8.4 BoosterDirector, §4.9; SPEC-gameplay §6; SPEC-motion-audio §3.10, anchor B = the booster's
// release; CONSISTENCY K-1…K-16). The two corners of v552: left the frozen HOURGLASS (`freeze`), right the BULB (`hint`), 3 each
// at install (C3). A corner tap (S2's GameButton: press 0.95, ♪ uiClick + ◉ button on release) reaches `boosterTapped`:
//   stock > 0, its own effect not running → C3 `Economy.useBooster` (stock − 1, saved) + C2 `session.useBooster` → the events
//     fanned out through the §8.1 order (board, haptics, audio, HUD, FX, directors) + ◉ booster; the badge shows n − 1 at once;
//   hourglass → the level clock freezes AT B for `boosters.freezeFlight + freezeSeconds` (1.6 + 10 s of running time, C2) and
//     S2's HUD freeze plays (`fx .custom("freeze")`: the icy hourglass pops at (192, 612), rises, flies to the stopwatch; at
//     B + 1.60 the frost and the "10" … "1" countdown tray under the timer pill). The timer resumes on the session's
//     `.freezeEnded` (the tray retracts on that frame: the effect is stopped there if it still runs).
//     Used BEFORE the first tap (SPEC.md ruling 30, K-4 RESOLVED 21:12 — overrules G2's "the flight waits for the first tap"):
//     the stock is taken at B and the hourglass FLIES AT ONCE (the tap answers immediately); the frost, the iced stopwatch and
//     the tray come at B + 1.60 as usual but the tray HOLDS "10" with a full bar; the first board tap starts the timer and the
//     10 s countdown (never before B + 1.60). FIX-A2: CORE-2's entry `useBooster(_:hintPolicy:freezeFlightFromUse: true)` does
//     `clock.freeze(freezeTotal, lead: freezeFlight)`: the core counts the flight from B itself (like all clock time it stops
//     under holds) and the 10 s wait for the first tap (`clock.freezeWaitsForFirstTap` is true exactly while the tray holds
//     "10"), so the session's `.freezeEnded` lands on the tray's end — B + 1.60 + 10 s when the tap came during the flight,
//     tap + 10 s after it — with no app-side bookkeeping (the old `session.tick(flown)` workaround is gone);
//   the HUD freeze follows the session's holds (FIX-A2, G2's request "freeze HUD effect pausable"): while any clock hold is on
//     (Pause, a popup, an offer, a tutorial with holdTimer, the app in the background) the flight, the tray and the frost stand
//     still (`fx .custom("freezeHold")`, checked every display-link frame; the background edge at once), so they end with C2's
//     freeze however long the Play was held;
//   bulb → the rules' hint policy (rules.json `boosters.hintPolicy` unblocksMost, SPEC.md ruling 31: CORE-2's
//     `session.hint(policy:)` / `useBooster(_:hintPolicy:freezeFlightFromUse:)`; `session.hint()` stays greedy for BoardLab and
//     the HeadlessDriver) goes to the board (`.hintShown`): max zoom centred on it in 0.80 s, the green blink, green until it
//     exits, then back to fit (B2). No free unit (a door still opening) → nothing happens and no stock is taken. The timer does
//     not start;
//   the booster whose effect runs is inert (no stock taken); the other stays usable (GP §6.1, K-7);
//   stock 0 → S3's booster popup ("Time Freeze" / "Hint", "Buy x3 [coin] 900", C3 `Economy.buyBooster`); the timer holds while
//     it is up (the popup host); after a purchase the badge shows the new stock and the player taps again (GP §6.4).
// Log: `[PC][booster] <id> …` for every decision.
// Template phase 2: genre-agnostic. The corners are the module's `BoosterSpec`s (capabilities order); `.freezeTimer` runs the
// shell's freeze flow above (the session freezes its clock); every other effect (ArrowEscape's bulb = `.puzzleAction("hint")`)
// asks the session first (`canUseBooster`: no stock is taken when it would do nothing), then `useBooster`. A booster whose
// outputs carry hint targets stays inert until one of them leaves play (a puzzle event's `removedTargets`).

@MainActor final class BoosterDirector: GameDirector {
    unowned let game: GameController

    /// The freeze effect's state in this Play.
    enum Freeze: Equatable { case idle, pendingFirstTap, running }
    private(set) var freeze: Freeze = .idle
    private var freezeFX: FXHandle?
    /// FIX-A2: the HUD freeze is held (its flight, tray and frost stand still) — mirrors the session's clock holds.
    private var fxHeld = false
    /// The app is in the background: the effect holds at once (the display link, which re-checks the holds, stops there).
    private var inBackground = false
    private var holdWatch: Task<Void, Never>?
    private var lifecycle: [NSObjectProtocol] = []
    /// The hinted targets until one of them leaves (the hint booster is inert meanwhile).
    private(set) var hinted: [PuzzleTarget]?
    private var buying = false

    init(_ game: GameController) { self.game = game }

    private var services: GameServices { game.services }
    private var store: PlayerStore { services.store }

    // MARK: the tap

    func boosterTapped(_ id: BoosterID, game: GameController) -> Bool {
        guard let session = game.session, !game.isTornDown else { return true }
        let live: Bool
        switch session.phase { case .ready, .playing: live = true; default: live = false }
        guard live, game.introDone, !game.paused, !services.popups.isPresenting, !game.synthetic, !buying else {
            Log.mark("booster", "\(id.rawValue) ignored (phase \(session.phase.logName), intro \(game.introDone), "
                     + "popup \(services.popups.isPresenting), paused \(game.paused))")
            return true
        }
        guard let spec = game.capabilities.booster(id) else {
            Log.mark("booster", "\(id.rawValue): not one of the puzzle's boosters (no action)")
            return true
        }
        switch spec.effect {
        case .freezeTimer: useFreeze(id, session)
        case .addTime, .addMoves, .puzzleAction: useAction(id, session)
        }
        return true
    }

    private func stock(_ id: BoosterID) -> Int { Economy.stock(store.state, id) }

    private func useFreeze(_ id: BoosterID, _ session: any PuzzleSession) {
        guard freeze == .idle else { Log.mark("booster", "\(id.rawValue) inert: its freeze is running"); return }
        guard stock(id) > 0 else { buy(id); return }
        guard store.mutateAndSave({ Economy.useBooster(&$0, id) }) else { buy(id); return }
        let before = session.clock.remaining
        // CORE-2 / ruling 30: the flight (lead) counts from B even before the first tap, the 10 s countdown from that tap
        let outputs = session.useBooster(id)
        game.fanOut(outputs, origin: .director)
        services.haptics.play(.booster)
        refreshSlots()
        let started = session.clock.started
        freeze = started ? .running : .pendingFirstTap
        Log.mark("booster", "\(id.rawValue) used: stock \(stock(id)), clock frozen at \(String(format: "%.2f", before)) s for "
                 + "\(String(format: "%.1f", session.clock.freezeRemaining)) s of running time"
                 + (started ? "; the HUD freeze starts now (B)"
                            : String(format: "; before the first tap: the flight now (%.2f s counted from B), the tray holds \"10\" "
                                     + "until the first tap (ruling 30)", session.clock.freezeLead)))
        startFreezeFX(hold: !started)
    }

    private func startFreezeFX(hold: Bool) {
        let seconds = services.rules.boosters.freezeSeconds
        freezeFX = services.fx.play(.custom(id: "freeze", params: ["seconds": seconds, "hold": hold ? 1 : 0]))
        Log.mark("booster", "freeze FX: flight + frost + " + (hold ? "tray holding \"\(Int(seconds))\"" : "countdown \(seconds) s")
                 + " (tray at B + \(services.rules.boosters.freezeFlight))")
        fxHeld = false
        watchHolds()
    }

    /// Ruling 30: the first board tap after a pre-start freeze starts the held tray's countdown. The core already counted the
    /// flight from B (CORE-2's lead), so what is left of C2's freeze is the flight's rest + the 10 s: nothing to adjust here.
    private func firstTapAfterPreStartFreeze() {
        guard let session = game.session else { return }
        if let h = freezeFX { services.fx.play(.custom(id: "freezeGo", params: ["handle": Double(h.id)])) }
        Log.mark("booster", String(format: "freeze: the first tap starts the countdown — %.2f s of freeze left (%.2f s of it the "
                                   + "flight's rest), timer %.2f s", session.clock.freezeRemaining, session.clock.freezeLead,
                                   session.clock.remaining))
    }

    // MARK: the HUD freeze follows the session's holds (FIX-A2)

    /// Every display-link frame while the effect runs: hold / resume it on the edges of the session's clock holds. The
    /// background edge comes from the app's lifecycle notification (no frames there).
    private func watchHolds() {
        holdWatch?.cancel()
        observeLifecycle()
        holdWatch = Task { @MainActor [weak self, weak game] in
            while !Task.isCancelled {
                guard let self, let game, self.freezeFX != nil, !game.isTornDown else { return }
                self.syncFreezeHold()
                guard await game.wait(frames: 1) else { return }
            }
        }
    }

    private func syncFreezeHold() {
        guard let h = freezeFX, let session = game.session else { return }
        let holds = session.clock.holds
        let held = inBackground || !holds.isEmpty
        guard held != fxHeld else { return }
        fxHeld = held
        services.fx.play(.custom(id: "freezeHold", params: ["handle": Double(h.id), "on": held ? 1 : 0]))
        let why: String = inBackground ? "background" : holds.map(\.rawValue).sorted().joined(separator: "+")
        let what: String = held ? "held (\(why))" : "resumed"
        Log.mark("booster", "freeze FX \(what): " + String(format: "%.2f s of freeze left", session.clock.freezeRemaining))
    }

    private func observeLifecycle() {
        guard lifecycle.isEmpty else { return }
        let nc = NotificationCenter.default
        lifecycle.append(nc.addObserver(forName: UIApplication.didEnterBackgroundNotification, object: nil, queue: .main) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self else { return }
                self.inBackground = true
                self.syncFreezeHold()
            }
        })
        lifecycle.append(nc.addObserver(forName: UIApplication.willEnterForegroundNotification, object: nil, queue: .main) { [weak self] _ in
            // the next frame re-checks the session's holds (the return to the level brings up Pause, §8.6)
            MainActor.assumeIsolated { self?.inBackground = false }
        })
    }

    private func stopWatchingHolds() {
        holdWatch?.cancel()
        holdWatch = nil
        for o in lifecycle { NotificationCenter.default.removeObserver(o) }
        lifecycle = []
        fxHeld = false
        inBackground = false
    }

    /// A booster the session runs (ArrowEscape's bulb: the rules' hint policy, SPEC.md ruling 31 — the board zooms to the unit,
    /// blinks it green until it exits, then back to fit; no free unit (a door still opening) → nothing, no stock taken).
    private func useAction(_ id: BoosterID, _ session: any PuzzleSession) {
        if let h = hinted, !h.isEmpty {
            Log.mark("booster", "\(id.rawValue) inert: \(h.map(\.description).joined(separator: "+")) still hinted")
            return
        }
        guard session.canUseBooster(id) else {
            Log.mark("booster", "\(id.rawValue): nothing to do right now (nothing happens, no stock taken)")
            return
        }
        guard stock(id) > 0 else { buy(id); return }
        guard store.mutateAndSave({ Economy.useBooster(&$0, id) }) else { buy(id); return }
        let outputs = session.useBooster(id)
        for case .puzzle(let p) in outputs {
            if let targets = p.hintTargets, !targets.isEmpty { hinted = targets }
        }
        game.fanOut(outputs, origin: .director)
        services.haptics.play(.booster)
        refreshSlots()
        Log.mark("booster", "\(id.rawValue) used: stock \(stock(id))"
                 + (hinted.map { ", hinted " + $0.map(\.description).joined(separator: "+") } ?? "")
                 + " (the timer \(session.clock.started ? "keeps running" : "still frozen"))")
    }

    /// 0 stock: S3's booster popup (Buy x3 for 900; short of coins it opens the Shop over itself). The timer holds while it is up.
    private func buy(_ id: BoosterID) {
        buying = true
        Log.mark("booster", "\(id.rawValue) at 0 stock: the booster popup")
        let popups = services.popups
        Task { @MainActor [weak self, game] in
            let r = await popups.present(Popup<PopupResult>.boosterBuy(id))
            guard let self, !game.isTornDown else { return }
            self.buying = false
            self.refreshSlots()
            Log.mark("booster", "\(id.rawValue) popup → \(r): stock \(self.stock(id)), coins \(self.store.state.coins)")
        }
    }

    /// The module's corners from the stock (0 → the "+" badge).
    private func refreshSlots() {
        let slots = game.capabilities.boosters.map { spec -> BoosterSlotVM in
            let n = Economy.stock(store.state, spec.id)
            return BoosterSlotVM(id: spec.id, state: n > 0 ? .stock(n) : .empty)
        }
        game.hudWriter.setBoosters(slots)
    }

    // MARK: the session's side

    func handle(_ outputs: [SessionOutput], game: GameController) {
        for o in outputs {
            switch o {
            case .meta(.timerStarted(_)):
                if freeze == .pendingFirstTap {
                    freeze = .running
                    firstTapAfterPreStartFreeze()
                }
            case .meta(.freezeEnded):
                // the effect ends on its own clock at the same moment (B + 1.60 + 10: frost fade 0.30 s, tray up 0.15 s)
                endFreeze("the session's freeze ended: the timer resumes", stopFX: false)
            case .meta(.stageCleared(_)), .meta(.won(_)), .meta(.lost(_)):
                endFreeze("the stage ended", stopFX: true)
                hinted = nil
            case .meta(.stageAdvanced(_)):
                refreshSlots()
            case .puzzle(let p):
                let gone = p.removedTargets
                if let h = hinted, !gone.isEmpty, !Set(gone).isDisjoint(with: h) {
                    hinted = nil
                    Log.mark("booster", "hinted \(gone.map(\.description).joined(separator: "+")) left: the hint booster is usable again")
                }
            default:
                break
            }
        }
    }

    private func endFreeze(_ why: String, stopFX: Bool) {
        guard freeze != .idle else { return }
        freeze = .idle
        stopWatchingHolds()
        if let h = freezeFX {
            if stopFX { services.fx.stop(h) }
            freezeFX = nil
        }
        Log.mark("booster", "freeze over (\(why))")
    }

    func teardown(_ game: GameController) {
        stopWatchingHolds()
        if let h = freezeFX { services.fx.stop(h); freezeFX = nil }
        freeze = .idle
        hinted = nil
    }
}
