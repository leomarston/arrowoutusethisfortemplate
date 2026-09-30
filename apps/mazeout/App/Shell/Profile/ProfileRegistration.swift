import SwiftUI
import PathCore

// Kit component `profile` (kit/meta/profile): the Profile page (the router's `.profile` screen), the Username and Edit Profile
// popups in the popup host, their `-pc.popup username | editProfile` ids, their Loading warm-ups and the art the event-art
// policy must never release (Profile's stats draw event art). Named by RootView, S3Hooks.swift (S3Popups) and PopupHost until
// the kit decoupling step; GameComponents.swift lists it.

@MainActor enum ProfileRegistration {
    static func register() {
        ShellScreens.registerProfile { AnyView(ProfileView()) }
        ShellArt.registerKept { ProfileView.art }
        PopupPanels.register(PopupPanelProvider("profile", handles: { r in
            switch r {
            case .username, .editProfile: return true
            default: return false
            }
        }, make: { r, answer in
            if case .username = r { return AnyView(UsernamePopup(answer: answer)) }
            return AnyView(EditProfilePopup(answer: answer))
        }))
        DebugPopups.register { p, app in
            let popups = app.popups
            switch p.id {
            case PopupID.username.rawValue:
                if await DebugPopups.loopIfRequested(p, app: app, request: .username, style: PopupStyle(dim: .overPage)) { return true }
                let r = await popups.present(Popup<UsernameResult>(.username, style: PopupStyle(dim: .overPage), fallback: .close))
                Log.mark("popup", "username → \(r)")
            case PopupID.editProfile.rawValue:
                if await DebugPopups.loopIfRequested(p, app: app, request: .editProfile, style: PopupStyle(dim: .overPage)) { return true }
                let r = await popups.present(Popup<EditProfileResult>(.editProfile, style: PopupStyle(dim: .overPage), fallback: .close))
                Log.mark("popup", "editProfile → \(r)")
            default:
                return false
            }
            return true
        }
        ShellPrewarmItems.register(order: 120) { _, host in
            [ShellPrewarmItem("editProfile", ReferenceCanvas { EditProfilePopup(answer: PopupAnswer(id: -33, host: host)) }),
             ShellPrewarmItem("username", ReferenceCanvas { UsernamePopup(answer: PopupAnswer(id: -34, host: host), prewarm: true) })]
        }
        ShellPrewarmItems.register(order: 150) { _, _ in
            [ShellPrewarmItem("profile", ProfileView.prewarm().frame(width: 393, height: 852))]
        }
    }
}
