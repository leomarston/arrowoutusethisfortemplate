import SwiftUI
import PathCore

// SHELL S3: where the S3 panels plug into S1's shell (one-line hooks in PopupHost.swift `PopupContent`, Router.swift
// `DebugPopupLauncher`, RootView.swift `PopupPrewarm`, ShellLab.swift `ShellDebugScreens`, HomeView / HomeTopBar / RootView
// for the home, Shop, Leaderboard shell and Profile). Nothing here changes a ◆ contract.
//   S3Popups   the panels of username, editProfile, noLives, boosterBuy and the closable Shop page (`.custom("shop")`), and the
//              `-pc.popup` debug launcher for them: `username`, `editProfile`, `noLives`, `boosterBuy:<freeze|hint>`,
//              `shop[:bundles|coins]`
//   S3Hooks    the boot warm-up (the offers' coin group → the closable Shop, S2's `S2Hooks.shopOpener`)

@MainActor enum S3Hooks {
    static func warmUp(_ app: AppModel) {
        S2Hooks.shopOpener = { app in ShopPage.openOver(app, section: .coins) }
        if let store = app.shop as? ShopStore { Task { @MainActor in await store.start() } }
    }
}

@MainActor enum S3Popups {
    static func hasPanel(_ request: PopupRequest) -> Bool {
        switch request {
        case .username, .editProfile, .noLives, .boosterBuy: return true
        case .custom(let id, _): return id == ShopPage.popupID
        default: return false
        }
    }

    /// The closable Shop is a full page (no dim, live-screen layout).
    static func isPage(_ request: PopupRequest) -> Bool {
        if case .custom(let id, _) = request { return id == ShopPage.popupID }
        return false
    }

    @ViewBuilder static func make(_ request: PopupRequest, answer: PopupAnswer) -> some View {
        switch request {
        case .username: UsernamePopup(answer: answer)
        case .editProfile: EditProfilePopup(answer: answer)
        case .noLives: NoLivesPopup(answer: answer)
        case .boosterBuy(let b): BoosterBuyPopup(booster: b, answer: answer)
        case .custom(let id, let params) where id == ShopPage.popupID:
            ShopView(closable: true, initialSection: ShopSection(rawValue: params["section"] ?? "") ?? .top,
                     onClose: { answer(PopupResult.close) })
        default: EmptyView()
        }
    }

    /// `-pc.popup <id>[:variant]` for the S3 ids (SPEC-architecture §9.1). Returns false for an id S3 does not own.
    static func debugPresent(_ p: LaunchArgs.PopupArg, app: AppModel) async -> Bool {
        let popups = app.popups
        // SHELL-private `-pc.s3PopupLoop N`: open + close the popup N times (0.8 s apart), each open's frames logged
        if let n = app.args.raw["pc.s3PopupLoop"].flatMap(Int.init), n > 0, let host = popups as? PopupHost,
           let request = request(p) {
            for i in 0..<n {
                let probe = FrameProbe("popup \(p.id) loop \(i)")
                probe.start()
                Task { @MainActor in _ = await host.present(Popup<PopupResult>(request, style: style(request), fallback: .close)) }
                try? await Task.sleep(nanoseconds: 500_000_000)
                host.dismissAll()
                try? await Task.sleep(nanoseconds: 300_000_000)
                probe.stop()
            }
            return true
        }
        switch p.id {
        case PopupID.username.rawValue:
            let r = await popups.present(Popup<UsernameResult>(.username, style: PopupStyle(dim: .overPage), fallback: .close))
            Log.mark("popup", "username → \(r)")
        case PopupID.editProfile.rawValue:
            let r = await popups.present(Popup<EditProfileResult>(.editProfile, style: PopupStyle(dim: .overPage), fallback: .close))
            Log.mark("popup", "editProfile → \(r)")
        case PopupID.noLives.rawValue:
            let r = await popups.present(Popup<PopupResult>.noLives)
            Log.mark("popup", "noLives → \(r)")
        case PopupID.boosterBuy.rawValue:
            let r = await popups.present(Popup<PopupResult>.boosterBuy(BoosterID(p.variant ?? "freeze")))
            Log.mark("popup", "boosterBuy → \(r)")
        case ShopPage.popupID:
            let r = await popups.present(Popup<PopupResult>(.custom(id: ShopPage.popupID, params: ["section": p.variant ?? "top"]),
                                                            style: PopupStyle(dim: .none), fallback: .close))
            Log.mark("popup", "shop page → \(r)")
        default:
            return false
        }
        return true
    }

    private static func request(_ p: LaunchArgs.PopupArg) -> PopupRequest? {
        switch p.id {
        case PopupID.username.rawValue: return .username
        case PopupID.editProfile.rawValue: return .editProfile
        case PopupID.noLives.rawValue: return .noLives
        case PopupID.boosterBuy.rawValue: return .boosterBuy(BoosterID(p.variant ?? "freeze"))
        case ShopPage.popupID: return .custom(id: ShopPage.popupID, params: ["section": p.variant ?? "top"])
        default: return nil
        }
    }

    private static func style(_ r: PopupRequest) -> PopupStyle {
        switch r {
        case .username, .editProfile: return PopupStyle(dim: .overPage)
        case .custom: return PopupStyle(dim: .none)
        default: return .standard
        }
    }

    /// Rendered once, invisibly, behind Loading (the first presentation's SwiftUI + raster cost is paid there), one item per
    /// frame (RootView `PopupPrewarm` stages every owner's list; FIX-A1).
    static func prewarm(_ app: AppModel) -> [ShellPrewarmItem] {
        let host = PopupHost(ui: app.tuning.ui)
        return [
            ShellPrewarmItem("noLives", ReferenceCanvas { NoLivesPopup(answer: PopupAnswer(id: -31, host: host)) }),
            ShellPrewarmItem("boosterBuy", ReferenceCanvas { BoosterBuyPopup(booster: .freeze, answer: PopupAnswer(id: -32, host: host)) }),
            ShellPrewarmItem("editProfile", ReferenceCanvas { EditProfilePopup(answer: PopupAnswer(id: -33, host: host)) }),
            ShellPrewarmItem("username", ReferenceCanvas { UsernamePopup(answer: PopupAnswer(id: -34, host: host), prewarm: true) }),
            ShellPrewarmItem("shop", ShopView.prewarm(app)),
            ShellPrewarmItem("profile", ProfileView.prewarm().frame(width: 393, height: 852)),
            ShellPrewarmItem("leaderboardShell", LeaderboardPageShell()),
        ]
    }
}
