import SwiftUI
import PathCore

// GAME G1 (SPEC-architecture §8.4 FailFlowDirector; SPEC-gameplay §5, §7, §8; SPEC-motion-audio §4, §12.1, §15.3;
// CONSISTENCY T-4, B-11, X-1…X-5, X-23, T-31). The fail chain, driven by the session's `.offer` / `.lost` events:
//  - Out of Time!: the pill shows 0:00 for `game.json fail.zeroHoldSeconds` (1.61 s) with input locked, then the popup in
//    one frame; Out of Lives!: the popup `fail.heartsOutDelay` (0.60 s) after the last heart's contact (the heart break);
//    the `fail` haptic on that popup's frame; later steps (Continue? streak / token / life) follow at once;
//  - "Add Time" / "Add Lives" / "Play On" → the PayAction: `Economy.spend(900)` (short → the Shop over the popup, which
//    re-checks on return) → `session.acceptContinue()`; X → `session.declineContinue()` → the next step or `.lost`;
//  - `.lost(reason)` (the chain's end, a Quit): Level Failed (Try Again | X) — the loss is banked right after the panel's
//    first frame (S2: the Streak strip then slides x → x1): `Economy.finishAttempt(.lost)` + `Events.onLoss` + an immediate
//    save; Try Again = the same board through the lives gate; X = home, or a retry before the first home (T-31).
// The popups themselves are S2's (OutOfTimePopup, ContinuePopup, LevelFailedPopup).
// B1 (VERIFIED v582, build/p/PH0/balloon.md §5): when the failed attempt loses an Up & Away streak of ≥ 2
// (`balloonRise.fallPageMinStreak`), the chain's end first shows Up & Away's page by itself — the balloon falls to the ground —
// and its X leads to Level Failed (the bands themselves carry no balloon wording). A loss of 1 goes straight to Level Failed.
// Template phase 2: genre-agnostic — driven by the `.meta(.offer / .lost)` events of any module; the first step's delay is
// `fail.zeroHoldSeconds` for a clock that ran out (the pill shows 0:00) and `fail.heartsOutDelay` for every other kind; the
// popup's texts follow `ContinueOffer.Kind` (S2's OutOfTimePopup / ContinuePopup for time and hearts; template phase 5: the
// generic OfferPopup for `stuck` / `outOfMoves`, its texts by kind and its grant line by the grant).

@MainActor final class FailFlowDirector: GameDirector {
    unowned let game: GameController
    /// The loss was banked (once per Play).
    private(set) var lossBanked = false
    private(set) var offersShown: [ContinueOffer] = []

    init(_ game: GameController) { self.game = game }

    private var services: GameServices { game.services }
    private var zeroHold: Double { services.tuning.game.file.double("fail.zeroHoldSeconds", 1.61) }
    private var heartsOutDelay: Double { services.tuning.game.file.double("fail.heartsOutDelay", 0.60) }

    func handle(_ outputs: [SessionOutput], game: GameController) {
        for out in outputs {
            guard case .meta(let e) = out else { continue }
            switch e {
            case .offer(let o):
                Task { @MainActor [self, game] in
                    await offer(o)
                    withExtendedLifetime(game) {}
                }
            case .lost(let reason): lost(reason)
            default: break
            }
        }
    }

    // MARK: offers

    private func offer(_ o: ContinueOffer) async {
        guard let s = game.session else { return }
        let delay = o.step == 0 ? firstStepDelay(o.kind) : 0
        Log.mark("fail", "\(game.levelName) offer \(o.kind.rawValue) step \(o.step) (\(o.warning.rawValue)) in \(delay) s")
        if delay > 0 { guard await game.wait(gameSeconds: delay) else { return } }
        guard !game.isTornDown, case .offer(let now) = s.phase, now == o else { return }
        if o.step == 0 { services.haptics.play(.fail) }
        offersShown.append(o)
        let pay = payAction(o)
        let r: PopupResult
        if o.warning == .none {
            r = await services.popups.present(Popup<PopupResult>.outOfTime(o, pay: pay))
        } else {
            r = await services.popups.present(Popup<PopupResult>.continueOffer(o, pay: pay))
        }
        guard !game.isTornDown, case .offer(let still) = s.phase, still == o else { return }
        if r == .primary {
            Log.mark("fail", "\(game.levelName) continue \(o.kind.rawValue) step \(o.step): paid \(o.price), coins \(services.store.state.coins)")
            game.fanOut(s.acceptContinue(), origin: .director)
        } else {
            Log.mark("fail", "\(game.levelName) declined \(o.kind.rawValue) step \(o.step)")
            game.fanOut(s.declineContinue(), origin: .director)
        }
        game.updateInput()
    }

    /// Out of Time!: the pill holds 0:00 first; every other chain (hearts, moves, stuck) opens after the break's beat.
    private func firstStepDelay(_ kind: ContinueOffer.Kind) -> Double {
        kind == .outOfTime ? zeroHold : heartsOutDelay
    }

    /// The offer's price: spent at once when the player has it (an immediate save), else the Shop over the popup (the popup
    /// stays and re-checks on the next press).
    private func payAction(_ o: ContinueOffer) -> PayAction {
        { @MainActor [weak game] in
            guard let game, !game.isTornDown else { return false }
            let s = game.services
            let paid = s.store.mutateAndSave { Economy.spend(&$0, o.price) }
            if paid {
                game.hudWriter.setCoins(s.store.state.coins)
                return true
            }
            Log.mark("fail", "\(game.levelName) \(o.price) coins needed, \(s.store.state.coins) held: the Shop over the offer")
            if let app = s.app { S2Hooks.openShop(app) }
            return false
        }
    }

    // MARK: the end

    private func lost(_ reason: LossReason) {
        guard !lossBanked else { return }
        Log.mark("fail", "\(game.levelName) lost: \(reason.rawValue)")
        services.board.inputEnabled = false
        let levels = game.plan.levels
        let popups = services.popups
        let fall = Self.balloonFall(services)
        Task { @MainActor [self, game] in
            defer { withExtendedLifetime(game) {} }
            if let from = fall {
                Log.mark("fail", "\(game.levelName) Up & Away fall page from \(from)")
                let r = PopupRequest.custom(id: "balloonFall", params: ["from": "\(from)"])
                _ = await popups.present(Popup<PopupResult>(r, style: PopupStyle(dim: .none), fallback: .close))
                guard !game.isTornDown else { return }
            }
            let panel = Task { @MainActor in await popups.present(Popup<PopupResult>.levelFailed(levels: levels, reason: reason)) }
            _ = await game.wait(frames: 1)
            bankLoss(reason)
            let r = await panel.value
            guard !game.isTornDown else { return }
            for d in game.directors { await d.afterLoss(reason, game: game) }
            guard !game.isTornDown else { return }
            let tryAgain = r == .primary
            Log.mark("fail", "\(game.levelName) Level Failed → \(tryAgain ? "Try Again" : "X")")
            services.router.go(services.screenAfterLoss(game.launch, tryAgain))
        }
    }

    /// B1: the Up & Away streak this failed attempt is about to lose, when it earns the fall page (nil otherwise).
    static func balloonFall(_ s: GameServices) -> Int? {
        let status = Events.status(s.store.state, now: s.clock.wallClock(), rules: s.economy)
        guard let b = status.balloon, b.streak >= s.economy.events.balloonRise.fallPageMinStreak else { return nil }
        return b.streak
    }

    /// The failed attempt (C3): the life stays spent, the streak → x1, a Sky Jump run fails; an immediate save.
    func bankLoss(_ reason: LossReason) {
        guard !lossBanked else { return }
        lossBanked = true
        let s = services
        let now = s.clock.wallClock()
        let levels = game.plan.levels
        let outcomes = s.store.mutateAndSave { st -> [EventOutcome] in
            Economy.finishAttempt(&st, outcome: .lost(reason), now: now, rules: s.economy)
            return Events.onLoss(&st, LossContext(levels: levels, reason: reason, now: now), rules: s.economy)
        }
        let st = s.store.state
        Log.mark("fail", "\(game.levelName) loss banked: lives \(st.lives.count), streak step \(st.events.streakStep), "
                 + "losses \(st.stats.losses)\(outcomes.isEmpty ? "" : ", events \(outcomes.count)")")
        game.writeBench(outcome: "lost:\(reason.rawValue)")
    }
}
