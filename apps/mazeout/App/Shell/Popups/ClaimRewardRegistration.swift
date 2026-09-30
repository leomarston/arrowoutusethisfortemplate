import SwiftUI
import PathCore

// Kit component `claim-reward` (kit/popups/claim-reward): the claim screen in the popup host, its
// `-pc.popup claim[:coins|hint|freeze|lives]` id and its Loading warm-ups (two claims, the staged title letters). Moved as they
// were from S2Popups (HUD/S2Hooks.swift) in the kit decoupling step; GameComponents.swift lists it.

@MainActor enum ClaimRewardRegistration {
    static func register() {
        PopupPanels.register(PopupPanelProvider("claim-reward", handles: { r in
            if case .claimReward = r { return true }
            return false
        }, make: { r, answer in
            guard case .claimReward(let grant) = r else { return AnyView(EmptyView().popupVariantMarker(r)) }
            return AnyView(ClaimRewardPopup(grant: grant, answer: answer).popupVariantMarker(r))
        }))
        DebugPopups.register { p, app in
            guard p.id == PopupID.claimReward.rawValue else { return false }
            let g: Grant
            switch p.variant ?? "lives" {
            case "coins": g = .coins(200)
            case "hint": g = .booster(.hint, 1)
            case "freeze": g = .booster(.freeze, 1)
            default: g = .unlimited(1800)
            }
            let r = await app.popups.present(Popup<PopupResult>.claimReward(g))
            Log.mark("popup", "claim → \(r)")
            return true
        }
        // G2's request (the first claim popup took 31.7 ms present → visible in Debug): the claim screen's graph and rasters
        ShellPrewarmItems.register(order: 430) { _, host in
            [ShellPrewarmItem("claim.coins", ReferenceCanvas {
                 ClaimRewardPopup(grant: .coins(200), answer: PopupAnswer(id: -18, host: host))
             }),
             ShellPrewarmItem("claim.unlimited", ReferenceCanvas {
                 ClaimRewardPopup(grant: .unlimited(1800), answer: PopupAnswer(id: -19, host: host))
             })]
        }
        ShellPrewarmItems.register(order: 450) { app, _ in [letters(app)] }
    }

    /// A2: the staged claim titles draw one GameText per letter: every letter's raster (the claim's style and the Sky Jump win's)
    /// is made here, all letters at rest, not in the claim's first frames.
    private static func letters(_ app: AppModel) -> ShellPrewarmItem {
        let claimTitle = ClaimTitle.style(app.tuning.ui.tokens, id: "claim.title.title",
                                          .s2(45.2, -0.83, [Skin.hudS2HooksS2PopupsPrewarmClaimTitleStyle0, Skin.hudS2HooksS2PopupsPrewarmClaimTitleStyle1, Skin.hudS2HooksS2PopupsPrewarmClaimTitleStyle2], outline: Skin.hudS2HooksS2PopupsPrewarmClaimTitleOutline, 0.94, drop: 1.81))
        let skyTitle = GameTextStyle.s2(45.5, -1.0, [Skin.hudS2HooksS2PopupsPrewarmSkyTitle0, Skin.hudS2HooksS2PopupsPrewarmSkyTitle1, Skin.hudS2HooksS2PopupsPrewarmSkyTitle2], outline: Skin.hudS2HooksS2PopupsPrewarmSkyTitleOutline, 0.9, drop: 1.8)
        return ShellPrewarmItem("claim.letters", ReferenceCanvas {
            LetterPopTitle(text: String(localized: "Congratulations!"), style: claimTitle, baseline: 187.4, centreX: 196.8,
                           maxWidth: 360, u: 5)
            LetterPopTitle(text: String(localized: "Congratulations!"), style: skyTitle, baseline: 122.8, centreX: 196.8,
                           maxWidth: 360, u: 5)
        })
    }
}
