import SwiftUI
import UIKit
import PathCore

// SHELL S3 (SPEC-architecture §6.6 "meta: username", §6.9; SPEC-ui §2.14.3 (DECISION on the v552 skin, flow VERIFIED V2 50-70 s);
// CONSISTENCY S-6 ("Username"), V-26 (3-16 characters, letters of any script, digits, "_", the blocklists; shake + red outline +
// the message)). Opened over the Profile page when the player has no name yet (not forced): the Edit Profile panel shortened
// to 10.3 · 250 · 372.6 · 330, the ribbon "Username", "Create your username:", the name field (280 × 48 at (196.5, 380)) with the
// keyboard up, the framed green "Continue", the X. Continue (or the keyboard's Done) with a valid name writes
// `SocialState.username` (saved) and answers `.saved(name)`; an invalid one shakes the field red and toasts the reason; X →
// `.close` (the `player_` default stays).

struct UsernamePopup: View {
    let answer: PopupAnswer
    /// The invisible render behind Loading: never takes the keyboard.
    var prewarm = false
    @Environment(AppModel.self) private var app
    @State private var name = ""
    @State private var invalid = false
    @State private var shake = 0
    @FocusState private var focused: Bool

    var body: some View {
        let t = app.tuning.ui.tokens
        let caption = GameTextStyle.s2(22, -0.5, [Skin.popupsUsernamePopupUsernamePopupCaption0])
        let cont = GameTextStyle.s2(38.9, -1.2, [Skin.popupsUsernamePopupUsernamePopupCont0, Skin.popupsUsernamePopupUsernamePopupCont1, Skin.popupsUsernamePopupUsernamePopupCont2], outline: Skin.popupsUsernamePopupUsernamePopupContOutline, 2.2, drop: 1.8)
        ZStack(alignment: .topLeading) {
            PopupPanelFrame(n: 5.8, t: t, bumperArm: CGSize(width: 70, height: 70), rivetInset: CGPoint(x: 12.7, y: 66), rivetAlong: 75)
                .placed(CGRect(10.3, 250.0, 372.6, 330.0))
            PopupCard(radius: 24, t: t).placed(CGRect(34.0, 304.0, 325.0, 114.0))
            GameText("Create your username:", style: caption, maxWidth: 290).at(196.5, caption.capCentre(baseline: 338.0))
            UsernameField(text: $name, invalid: invalid, focused: $focused) { submit() }
                .modifier(Shake(amount: CGFloat(shake)))
                .placed(CGRect(56.5, 356.0, 280.0, 48.0))
            WellFramedButton(id: "username.continue", title: "Continue", colors: .green, frame: CGRect(90.9, 426.8, 211.2, 86.4),
                             well: CGRect(79.6, 418.1, 233.9, 106.4), n: 4.8, style: cont, baseline: 482.0, centreX: 196.5,
                             maxWidth: 172, t: t) { submit() }
            PopupTitle(title: "Username", frame: CGRect(60.4, 211.6, 274.2, 90.4), t: t)
            PopupCloseButton(id: "popup.username.close", t: t) { focused = false; answer(UsernameResult.close) }
                .placed(CGRect(339.9, 261.2, 45, 45))
        }
        .frame(width: 393, height: 852, alignment: .topLeading)
        .onAppear {
            Usernames.warm()
            // the keyboard comes up after the popup's own first frame (its first presentation is iOS's cost, not the popup's)
            if !app.args.quietUI && !prewarm {
                Task { @MainActor in try? await Task.sleep(nanoseconds: 350_000_000); focused = true }
            }
        }
    }

    private func submit() {
        switch Usernames.check(name) {
        case .ok(let v):
            app.store.mutateAndSave { $0.social.username = v }
            focused = false
            Log.mark("profile", "username saved: \(v)")
            answer(UsernameResult.saved(v))
        case .bad(let why):
            invalid = true
            withAnimation(.linear(duration: 0.3)) { shake += 1 }
            app.toasts.show(why)
            Log.mark("profile", "username refused: '\(name)' \(String(localized: why))")
        }
    }
}

private struct UsernameField: View {
    @Binding var text: String
    let invalid: Bool
    var focused: FocusState<Bool>.Binding
    let submit: () -> Void

    var body: some View {
        ZStack {
            Rasterized("usernameWell|\(invalid)", overflow: 1) { _ in
                ZStack {
                    RoundedRectangle(cornerRadius: 14).fill(Color(hex: invalid ? Skin.popupsUsernamePopupUsernameFieldFillInvalid : Skin.popupsUsernamePopupUsernameFieldFillNotInvalid))
                    RoundedRectangle(cornerRadius: 13).fill(Color(hex: Skin.popupsUsernamePopupUsernameFieldFill)).padding(invalid ? 2.2 : 1)
                    RoundedRectangle(cornerRadius: 13)
                        .fill(LinearGradient(colors: [Color(hex: Skin.popupsUsernamePopupUsernameFieldColors0, 0.7), .clear], startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.3)))
                        .padding(invalid ? 2.2 : 1)
                }
            }
            TextField(text: $text, prompt: Text(verbatim: "")) { EmptyView() }
                .font(GameText.pageFont(25.4))
                .foregroundStyle(Color(hex: Skin.popupsUsernamePopupUsernameFieldForegroundStyle))
                .multilineTextAlignment(.center)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .submitLabel(.done)
                .onSubmit(submit)
                .focused(focused)
                .padding(.horizontal, 14)
                .accessibilityIdentifier("username.field")
        }
    }
}
