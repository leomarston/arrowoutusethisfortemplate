import SwiftUI
import UIKit
import PathCore

// SHELL S3 (SPEC-architecture §6.6 "meta: editProfile"; SPEC-ui §2.14.2; SPEC-gameplay §13; CONSISTENCY U-28 (the popup writes
// the name itself through PlayerStore; ◆ EditProfileResult carries only the avatar), V-26 (3-16 characters); VERIFIED meta-003 /
// meta-004 / meta-005). Over the Profile page with the 0.63 dim: the tall blue panel (5.7 · 132.1 · 382.0 · 638.9), the ribbon
// "Edit Profile", the X; card 1 = the chosen avatar + the name field (#F6D8C0 well, the name #70200D, a pencil badge; tap →
// the keyboard); card 2 = the 3 × 3 portrait grid (default + 8, the chosen one framed green with a check); the framed green
// "Save". Save writes the avatar and — if it was edited and passes the username rules — the name, then answers
// `.saved(avatar:)`; an invalid name shakes the field, outlines it red and toasts the reason (nothing saved). X saves nothing.

struct EditProfilePopup: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var avatar: Int = -1
    @State private var name = ""
    @State private var editing = false
    @State private var invalid = false
    @State private var shake = 0
    @FocusState private var focused: Bool

    var body: some View {
        let t = app.tuning.ui.tokens
        let s = app.store.state
        let current = avatar < 0 ? s.social.avatar : avatar
        let shown = name.isEmpty ? s.social.displayName(installSeed: s.installSeed) : name
        let saveStyle = GameTextStyle.s2(49.1, -1.71, [Skin.popupsEditProfilePopupEditProfilePopupSaveStyle0, Skin.popupsEditProfilePopupEditProfilePopupSaveStyle1, Skin.popupsEditProfilePopupEditProfilePopupSaveStyle2], outline: Skin.popupsEditProfilePopupEditProfilePopupSaveStyleOutline, 3.27, drop: 1.87)
        ZStack(alignment: .topLeading) {
            PopupPanelFrame(n: 6.5, t: t, rivetInset: CGPoint(x: 13.1, y: 78.8), rivetAlong: 75.3).placed(CGRect(5.7, 132.1, 382.0, 638.9))
            PopupCard(radius: 17.9, t: t).placed(CGRect(59.1, 204.2, 275.2, 97.7))
            AvatarFrameTile(index: current, n: 3.5, ring: 0.085).placed(CGRect(69.4, 211.5, 79.4, 80.1))
            NameField(text: $name, shown: shown, editing: editing, invalid: invalid, focused: $focused) {
                editing = true
                if name.isEmpty { name = s.social.username ?? "" }
                focused = true
            }
            .modifier(Shake(amount: CGFloat(shake)))
            .placed(CGRect(157.1, 229.2, 171.8, 43.0))
            PopupCard(radius: 16.9, t: t).placed(CGRect(57.7, 329.9, 277.9, 270.6))
            ForEach(0..<Avatars.count, id: \.self) { i in
                let x: [CGFloat] = [67.4, 156.5, 247.5], y: [CGFloat] = [338.6, 427.4, 514.4]
                GameButton(id: "editProfile.avatar.\(i)", label: "Edit Profile", value: i == current ? "selected" : nil,
                           action: { avatar = i }) {
                    AvatarFrameTile(index: i, selected: i == current, n: 3.4, ring: 0.085)
                }
                .placed(i == current ? CGRect(x[i % 3], y[i / 3] + 1, 86.1, 84.1).offsetBy(dx: 0, dy: 0)
                                     : CGRect(x[i % 3], y[i / 3], 79.7, 80.1))
            }
            let sel = CGPoint(x: [67.4, 156.5, 247.5][current % 3], y: [338.6, 427.4, 514.4][current / 3])
            ArtImage(art: .iconCheckBadge).placed(CGRect(sel.x + 46.0, sel.y + 51.7, 40, 33.4)).allowsHitTesting(false)
            WellFramedButton(id: "editProfile.save", title: "Save", colors: .green, frame: CGRect(91.4, 630.2, 210.5, 86.7),
                             well: CGRect(80.1, 621.9, 233.2, 108.4), n: 4.8, style: saveStyle, baseline: 690.0, centreX: 196.7,
                             maxWidth: 172, t: t) { save() }
            PopupTitle(title: "Edit Profile", frame: CGRect(60.4, 93.7, 274.2, 90.4), t: t, baselineFromTop: 55.7)
            PopupCloseButton(id: "popup.editProfile.close", t: t) { answer(EditProfileResult.close) }
                .placed(CGRect(336.3, 137.6, 45, 45))
        }
        .frame(width: 393, height: 852, alignment: .topLeading)
        .onAppear { Usernames.warm() }
    }

    private func save() {
        let s = app.store.state
        let chosen = avatar < 0 ? s.social.avatar : avatar
        var newName: String?
        let typed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        if editing, !typed.isEmpty, typed != (s.social.username ?? "") {
            switch Usernames.check(typed) {
            case .ok(let v): newName = v
            case .bad(let why):
                invalid = true
                withAnimation(.linear(duration: 0.3)) { shake += 1 }
                app.toasts.show(why)
                Log.mark("profile", "editProfile save refused: '\(typed)' \(String(localized: why))")
                return
            }
        }
        app.store.mutateAndSave {
            $0.social.avatar = chosen
            if let newName { $0.social.username = newName }
        }
        focused = false
        Log.mark("profile", "editProfile saved: avatar \(chosen) name \(newName ?? "(unchanged)")")
        answer(EditProfileResult.saved(avatar: chosen))
    }
}

/// The recessed name field (#F6D8C0, inner shadow, rr 12.9) with the name #70200D (25.4 pt, left x 168) and the pencil badge;
/// a TextField while editing.
private struct NameField: View {
    @Binding var text: String
    let shown: String
    let editing: Bool
    let invalid: Bool
    var focused: FocusState<Bool>.Binding
    let begin: () -> Void

    var body: some View {
        let style = GameTextStyle.s2(25.4, 0.1, [Skin.popupsEditProfilePopupNameFieldStyle0])
        ZStack(alignment: .topLeading) {
            Rasterized("nameWell|\(invalid)", overflow: 1) { _ in
                ZStack {
                    RoundedRectangle(cornerRadius: 12.9).fill(Color(hex: invalid ? Skin.popupsEditProfilePopupNameFieldFillInvalid : Skin.popupsEditProfilePopupNameFieldFillNotInvalid))
                    RoundedRectangle(cornerRadius: 12).fill(Color(hex: Skin.popupsEditProfilePopupNameFieldFill)).padding(invalid ? 2 : 1)
                    RoundedRectangle(cornerRadius: 12)
                        .fill(LinearGradient(colors: [Color(hex: Skin.popupsEditProfilePopupNameFieldColors0, 0.7), .clear], startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.3)))
                        .padding(invalid ? 2 : 1)
                }
            }
            if editing {
                TextField(text: $text, prompt: Text(verbatim: shown).foregroundStyle(Color(hex: Skin.popupsEditProfilePopupNameFieldForegroundStyle, 0.4))) { EmptyView() }
                    .font(GameText.pageFont(25.4))
                    .foregroundStyle(Color(hex: Skin.popupsEditProfilePopupNameFieldForegroundStyle))
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .submitLabel(.done)
                    .focused(focused)
                    .frame(width: 118, height: 36)
                    .position(x: 11 + 59, y: 21.5)
                    .accessibilityIdentifier("editProfile.nameField")
            } else {
                LeftText(text: shown, style: style, left: 11.0, baseline: 31.8, box: 115)
            }
            GameButton(id: "editProfile.namePencil", label: "Edit Profile", action: begin) { ArtImage(art: .iconPencil) }
                .placed(CGRect(131.8, 7.0, 31.7, 32.0))
        }
        .contentShape(Rectangle())
        .onTapGesture { if !editing { begin() } }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("editProfile.name")
    }
}

/// A horizontal shake (the invalid name, SPEC-ui §2.14.3).
struct Shake: GeometryEffect {
    var amount: CGFloat
    var animatableData: CGFloat {
        get { amount }
        set { amount = newValue }
    }
    func effectValue(size: CGSize) -> ProjectionTransform {
        ProjectionTransform(CGAffineTransform(translationX: 8 * sin(amount * .pi * 6), y: 0))
    }
}

/// The username rules (CONSISTENCY V-26: 3-16 characters, letters of any script, digits, "_"; the social blocklists), with the
/// name bank loaded once off the main thread.
@MainActor enum Usernames {
    enum Verdict { case ok(String), bad(LocalizedStringResource) }
    private static var bank: NameBank?
    private static var loading = false

    static func warm() {
        guard bank == nil, !loading else { return }
        loading = true
        let folder = Bundle.main.resourceURL?.appendingPathComponent("Social")
        Task.detached(priority: .utility) {
            let b = folder.flatMap { try? NameBank.load(folder: $0) } ?? NameBank()
            await MainActor.run { bank = b; loading = false; Log.mark("profile", "name bank ready (\(b.isEmpty ? "EMPTY" : "loaded"))") }
        }
    }

    static func check(_ raw: String) -> Verdict {
        let s = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        // B2 (social-intl P2-4): 2 characters suffice for Han, Hangul and kana (민수, 小明, 太郎); 3 elsewhere
        // B3: the toast states the range that applies to what was typed (a 1-character 小 hears "2-16", not "3-16")
        let lengths = SocialNames.usernameLengths(s)
        guard lengths.contains(s.count) else {
            return .bad(lengths.lowerBound == 2 ? "Name must be 2-16 characters" : "Name must be 3-16 characters")
        }
        if bank == nil, let folder = Bundle.main.resourceURL?.appendingPathComponent("Social") {
            bank = (try? NameBank.load(folder: folder)) ?? NameBank()        // first use before the warm-up finished
        }
        guard let v = SocialNames.validateUsername(s, bank: bank ?? NameBank()) else { return .bad("This name is not allowed") }
        return .ok(v)
    }
}
