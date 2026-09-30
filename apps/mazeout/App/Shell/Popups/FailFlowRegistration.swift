import SwiftUI
import PathCore

// Kit component `fail-flow` (kit/popups/fail-flow): its panels in the popup host, its `-pc.popup` ids and its Loading
// warm-up renders. Moved as they were from S2Popups (HUD/S2Hooks.swift) in the kit decoupling step; GameComponents.swift
// lists it. The Streak Race strip under Level Failed and the chips on Continue? are slots (`PanelStrips`, `ContinueChips`)
// the streak-race component fills, so the fail flow alone needs no event.

@MainActor enum FailFlowRegistration {
    static func register() {
        PopupPanels.register(PopupPanelProvider("fail-flow", handles: { r in
            switch r {
            case .outOfTime, .continueOffer, .levelFailed: return true
            default: return false
            }
        }, variant: { r, app in
            // SPEC-ui §6: `popup.continue` = streak | token | life | hearts | time
            switch r {
            case .continueOffer(let offer, _): return ContinuePopup.variant(offer, app: app).rawValue
            case .outOfTime(let offer, _):
                // template phase 5: a kind without a measured popup (OfferPopup) reports its own name
                return OfferPopup.handles(offer.kind) ? offer.kind.rawValue : (offer.kind == .outOfHearts ? "hearts" : "time")
            case .levelFailed(_, let reason): return reason.rawValue
            default: return ""
            }
        }, make: { r, answer in AnyView(panel(r, answer: answer).popupVariantMarker(r)) }))
        DebugPopups.register { p, app in await debugPresent(p, app: app) }
        ShellPrewarmItems.register(order: 400) { _, host in prewarm(host) }
    }

    @ViewBuilder private static func panel(_ request: PopupRequest, answer: PopupAnswer) -> some View {
        switch request {
        case .outOfTime(let offer, let pay):
            if OfferPopup.handles(offer.kind) {
                OfferPopup(offer: offer, pay: pay, answer: answer)                 // template phase 5: stuck, outOfMoves
            } else {
                OutOfTimePopup(offer: offer, pay: pay, answer: answer)
            }
        case .continueOffer(let offer, let pay): ContinuePopup(offer: offer, pay: pay, answer: answer)
        case .levelFailed(let levels, let reason): LevelFailedPopup(levels: levels, reason: reason, answer: answer)
        default: EmptyView()
        }
    }

    /// `-pc.popup outOfTime | continue[:streak|token|life|hearts|time] | levelFailed` (fixed, honest parameters: the player's
    /// state + the rules' prices). False for an id this component does not own.
    private static func debugPresent(_ p: LaunchArgs.PopupArg, app: AppModel) async -> Bool {
        let popups = app.popups
        let price = Int(app.tuning.rules.double("failChain.outOfTime.0.price", 900))
        let pay: PayAction = { @MainActor in
            // the debug launcher never spends: it reports what the real PayAction would get
            Log.mark("popup", "debug pay: coins \(app.store.state.coins) ≥ \(price) → \(app.store.state.coins >= price)")
            return false
        }
        switch p.id {
        case PopupID.outOfTime.rawValue:
            let offer = ContinueOffer(kind: .outOfTime, step: 0, price: price, grant: .addTime(30))
            let r = await popups.present(Popup<PopupResult>.outOfTime(offer, pay: pay))
            Log.mark("popup", "outOfTime → \(r)")
        case PopupID.continueOffer.rawValue:
            let v = ContinuePopup.Variant(rawValue: p.variant ?? "streak") ?? .streak
            ContinuePopup.forced = v
            let offer: ContinueOffer
            switch v {
            case .hearts, .time:
                offer = ContinueOffer(kind: v == .hearts ? .outOfHearts : .outOfTime, step: 0, price: price,
                                      grant: v == .hearts ? .refillHearts(3) : .addTime(30))
            case .life: offer = ContinueOffer(kind: .outOfTime, step: 2, price: price, grant: .addTime(30), warning: .life, isLast: true)
            case .token: offer = ContinueOffer(kind: .outOfTime, step: 1, price: price, grant: .addTime(30), warning: .token)
            case .streak: offer = ContinueOffer(kind: .outOfTime, step: 1, price: price, grant: .addTime(30), warning: .streak)
            }
            let r = await popups.present(Popup<PopupResult>.continueOffer(offer, pay: pay))
            ContinuePopup.forced = nil
            Log.mark("popup", "continue:\(v.rawValue) → \(r)")
        case PopupID.levelFailed.rawValue:
            let r = await popups.present(Popup<PopupResult>.levelFailed(levels: app.levelLaunch(for: app.store.state.level).levels,
                                                                        reason: .timeUp))
            Log.mark("popup", "levelFailed → \(r)")
        default:
            return false
        }
        return true
    }

    /// Rendered once, invisibly, behind Loading (the first presentation's SwiftUI + raster cost is paid there).
    private static func prewarm(_ host: PopupHost) -> [ShellPrewarmItem] {
        let offer = ContinueOffer(kind: .outOfTime, step: 1, price: 900, grant: .addTime(30), warning: .streak)
        let pay: PayAction = { false }
        return [
            ShellPrewarmItem("outOfTime", ReferenceCanvas {
                OutOfTimePopup(offer: ContinueOffer(kind: .outOfTime, step: 0, price: 900, grant: .addTime(30)), pay: pay,
                               answer: PopupAnswer(id: -11, host: host))
            }),
            ShellPrewarmItem("outOfHearts", ReferenceCanvas {
                OutOfTimePopup(offer: ContinueOffer(kind: .outOfHearts, step: 0, price: 900, grant: .refillHearts(3)), pay: pay,
                               answer: PopupAnswer(id: -12, host: host))
            }),
            ShellPrewarmItem("continue", ReferenceCanvas { ContinuePopup(offer: offer, pay: pay, answer: PopupAnswer(id: -13, host: host)) }),
            ShellPrewarmItem("levelFailed", ReferenceCanvas {
                LevelFailedPopup(levels: [32], reason: .timeUp, answer: PopupAnswer(id: -14, host: host))
            }),
        ]
    }
}
