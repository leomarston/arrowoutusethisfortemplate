import SwiftUI
import UIKit
import MessageUI
import UserNotifications
import PathCore

// SHELL S1 (SPEC-architecture §6.6 "meta: settings", §6.9; SPEC-ui §2.13 + correction C1, VERIFIED meta-029..037 / 132-136).
// v552's Settings is a FULL PAGE (like Profile), opened by the home gear: the page header "Settings" + the red X, a Notifications
// card with a pill toggle, a Sound / Music / Haptic card with three 66 pt green square toggles (OFF = a red slash over the
// glyph), a big green framed "Support" button and the blue "Terms" / "Privacy" pills. It is presented through the popup host
// (`PopupRequest.settings`: the frozen Screen enum has no settings case) and drawn full-screen, opaque, top-anchored — a hard
// cut in and out (SPEC-ui §1.8). Behaviour:
//   Notifications → PlayerState.settings.notifications (no iOS prompt, no toast, VERIFIED meta-032); OFF cancels the pending
//                   local notifications; ON while iOS denies them keeps it ON and shows "Allow notifications in iOS Settings."
//   Sound / Haptic → PlayerState.settings (never UserDefaults) → the SFX bus / the haptics gate, at once
//   Music          → INERT (SPEC-motion-audio MA2: v552's button stays OFF; no music ships): shown OFF, press + click, no change
//   Support → SPEC-gameplay §12.2 (CONSISTENCY U-6): a mail to the support address — the in-app composer when the device can
//             send mail, else a `mailto:` URL, else the Support page showing "Write to us at" + the address + Copy — never claims
//             a message was sent. The address is DATA (`game.json support.email`, U-6/C-7; the owner confirms it): while it is
//             absent, Support opens the offline Help page (SPEC-ui §2.13.1) and no address is shown anywhere.
//   Terms / Privacy → offline pages with SPEC-gameplay §16.10's texts in SPEC-ui §2.13.1's layout (U-6, S-13)
// Answer: X → .close.

struct SettingsPopup: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let s = app.store.state.settings
        let r = { (id: String, d: CGRect) in t.rect("settings." + id, d, .top, m) }
        let label = t.text("settings.label", GameTextStyle(size: 22.9, tracking: 0.1, fill: [.white], outline: Color(hex: Skin.popupsSettingsPopupSettingsLabelOutline),
                                                           outlineWidth: 1.15, drop: 1.15))
        let lst = label.sized(label.size * m.s)
        let f = t.file
        let notifAt = m.point(CGPoint(x: f.double("text.settings.label.notifLeft", 83.4), y: f.double("text.settings.label.notifBaseline", 189.6)), .top)
        let rowBase = m.y(CGFloat(f.double("text.settings.label.rowBaseline", 290.4)), .top)
        let centres = f.doubles("text.settings.label.rowCentres", [90.6, 195.7, 300.4]).map { m.point(CGPoint(x: $0, y: 0), .top).x }
        let notifWord = GameText("Notifications", style: lst, maxWidth: CGFloat(f.double("text.settings.label.notifBox", 150)) * m.s)
        let support = t.text("settings.support", GameTextStyle(size: 30.6, tracking: -0.6,
                                                               fill: [Color(hex: Skin.popupsSettingsPopupSettingsSupportFill0), Color(hex: Skin.popupsSettingsPopupSettingsSupportFill1), Color(hex: Skin.popupsSettingsPopupSettingsSupportFill2)],
                                                               outline: Color(hex: Skin.popupsSettingsPopupSettingsSupportOutline), outlineWidth: 1.42, drop: 1.2))
        let link = t.text("settings.link", GameTextStyle(size: 22.3, fill: [.white], outline: Color(hex: Skin.popupsSettingsPopupSettingsLinkOutline), outlineWidth: 1.1, drop: 1.2))
        let supportFace = r("support", CGRect(102.8, 438.4, 188.8, 77.4))
        let supportBase = m.y(485.9, .top), supportCX = m.point(CGPoint(x: 197.7, y: 0), .top).x
        ZStack(alignment: .topLeading) {
            ShellPageBackground(t: t).frame(width: m.size.width, height: m.size.height)
            // notifications
            BlueCard(radius: t.radius("settings.notifCard", 23.7) * m.s, t: t).placed(r("notifCard", CGRect(19.0, 134.1, 355.3, 95.7)))
            OutlinedArt(art: .iconBell, outline: Color(hex: Skin.popupsSettingsPopupSettingsPopupOutline)).placed(r("bell", CGRect(44.0, 164.5, 30.7, 38.4)).insetBy(dx: 1.3, dy: 1.3))
            notifWord.at(notifAt.x + notifWord.layout.advance / 2, lst.capCentre(baseline: notifAt.y))
            PopupToggle(id: "settings.toggle.notifications", isOn: s.notifications, t: t, well: .blue) {
                SettingsPopup.toggleNotifications(app)
            }
            .placed(r("notifToggle", CGRect(234.9, 161.1, 122.8, 41.7)))
            // sound · music · haptic
            BlueCard(radius: t.radius("settings.audioCard", 23.6) * m.s, t: t).placed(r("audioCard", CGRect(19.0, 248.5, 355.3, 152.5)))
            ForEach(Array(zip([LocalizedStringResource("Sound"), "Music", "Haptic"], centres).enumerated()), id: \.offset) { _, pair in
                GameText(pair.0, style: lst, maxWidth: CGFloat(f.double("text.settings.label.rowBox", 90)) * m.s)
                    .at(pair.1, lst.capCentre(baseline: rowBase))
            }
            ShellSquareToggle(id: "settings.toggle.sound", glyph: .iconSound, isOn: s.sound, t: t) {
                ShellSettings.toggle(app, \.sound, name: "settings.toggle.sound")
            }
            .placed(r("sound", CGRect(58.0, 312.3, 66.1, 65.7)))
            ShellSquareToggle(id: "settings.toggle.music", glyph: .iconMusic, isOn: SettingsPopup.musicShown(app), t: t) {
                SettingsPopup.tapMusic(app)
            }
            .placed(r("music", CGRect(162.1, 311.9, 65.7, 65.7)))
            ShellSquareToggle(id: "settings.toggle.haptic", glyph: .iconHaptic, isOn: s.haptic, t: t) {
                ShellSettings.toggle(app, \.haptic, name: "settings.toggle.haptic")
            }
            .placed(r("haptic", CGRect(266.9, 311.6, 66.1, 65.7)))
            // support, terms, privacy
            if app.tuning.ui.settingsShowsLinks {
                FramedButton(id: "settings.support", title: "Support", colors: .green, frame: supportFace,
                             well: r("supportFrame", CGRect(93.7, 433.0, 206.2, 94.4)), n: t.superellipseN("settings.support", 4.6),
                             style: support.sized(support.size * m.s), baseline: supportBase, centreX: supportCX,
                             maxWidth: (t.textMaxWidth("settings.support", 150) ?? 150) * m.s, t: t) {
                    SettingsPopup.openSupport(app)
                }
                PillLinkButton(id: "settings.terms", title: "Terms", style: link.sized(link.size * m.s),
                               maxWidth: (t.textMaxWidth("settings.link", 95) ?? 95) * m.s, t: t) {
                    SettingsPopup.open(.terms, app: app)
                }
                .placed(r("terms", CGRect(53.0, 552.1, 121.8, 49.0)))
                PillLinkButton(id: "settings.privacy", title: "Privacy", style: link.sized(link.size * m.s),
                               maxWidth: (t.textMaxWidth("settings.link", 95) ?? 95) * m.s, t: t) {
                    SettingsPopup.open(.privacy, app: app)
                }
                .placed(r("privacy", CGRect(218.5, 552.1, 121.8, 49.0)))
            }
            ShellPageHeader(t: t)
            PageTitle(title: "Settings", t: t)
            PopupCloseButton(id: "popup.settings.close", t: t, halo: true) { answer(PopupResult.close) }
                .placed(r("closeDisc", CGRect(325.2, 49.0, 45, 45)))
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("page.settings")
    }

    // MARK: behaviour

    /// MA2: the Music button is inert and shows OFF (v552: 4 attempts, meta §4); `settings.musicInert` false makes it a real
    /// toggle of PlayerState.settings.music (for the day music ships).
    static func musicShown(_ app: AppModel) -> Bool { musicShown(ui: app.tuning.ui, settings: app.store.state.settings) }

    static func musicShown(ui: UITuning, settings: PlayerState.Settings) -> Bool {
        ui.file.bool("settings.musicInert", true) ? false : settings.music
    }

    static func tapMusic(_ app: AppModel) { tapMusic(ui: app.tuning.ui, store: app.store, audio: app.audio, haptics: app.haptics) }

    static func tapMusic(ui: UITuning, store: PlayerStore, audio: any AudioPlaying, haptics: any HapticPlaying) {
        if ui.file.bool("settings.musicInert", true) {
            Log.mark("settings", "settings.toggle.music inert (no music ships, SPEC-motion-audio MA2)")
        } else {
            ShellSettings.toggle(store: store, audio: audio, haptics: haptics, \.music, name: "settings.toggle.music")
        }
    }

    static func toggleNotifications(_ app: AppModel) {
        let on = ShellSettings.toggle(app, \.notifications, name: "settings.toggle.notifications")
        let center = UNUserNotificationCenter.current()
        if !on {
            center.removeAllPendingNotificationRequests()
            return
        }
        let toasts = app.toasts
        Task { @MainActor in
            let status = await center.notificationSettings().authorizationStatus
            if status == .denied { toasts.show("Allow notifications in iOS Settings.") }
        }
    }

    /// The support address, or nil (`game.json support.email`, GAME's file; CONSISTENCY U-6).
    static func supportEmail(_ app: AppModel) -> String? {
        let e = app.tuning.game.file.string("support.email", "").trimmingCharacters(in: .whitespaces)
        return e.isEmpty ? nil : e
    }

    static func openSupport(_ app: AppModel) {
        guard let email = supportEmail(app) else { open(.support, app: app); return }
        let subject = String(localized: "\(Brand.name) Support")
        let body = String(localized: "Please describe your issue above. We will get back to you as soon as possible.") + "\n\n"
            + String(localized: "Version : \(InfoPage.version)") + "\n" + String(localized: "Level : \(app.store.state.level)")
        if MFMailComposeViewController.canSendMail(), let top = UIApplication.shared.topViewController {
            Log.mark("settings", "support: mail composer")
            MailComposer.shared.present(from: top, to: email, subject: subject, body: body)
            return
        }
        var c = URLComponents()
        c.scheme = "mailto"; c.path = email
        c.queryItems = [URLQueryItem(name: "subject", value: subject), URLQueryItem(name: "body", value: body)]
        guard let url = c.url else { open(.support, app: app); return }
        UIApplication.shared.open(url) { ok in
            Log.mark("settings", "support: mailto \(ok ? "opened" : "unavailable: the Support page shows the address")")
            if !ok { Task { @MainActor in open(.support, app: app) } }
        }
    }

    static func open(_ page: InfoPage.Kind, app: AppModel) {
        Log.mark("settings", "open \(page.rawValue)")
        Task { @MainActor in
            _ = await app.popups.present(Popup<PopupResult>(.custom(id: page.popupID, params: [:]), style: PopupStyle(dim: .none),
                                                            fallback: .close))
        }
    }
}

// MARK: - Support / Terms / Privacy (SPEC-ui §2.13.1 layout; SPEC-gameplay §12.3/§12.4/§16.10 texts, CONSISTENCY U-6 / S-13)

/// A full page: PageHeader with the title + X, the navy ground, a cream scroll card 19 · 126 · 355 · (to 34 pt above the bottom
/// safe inset), rr 23.7, body 17 pt #622100 plain, headings 21 pt, left-aligned, 20 pt insets, line height 1.3. No network, no
/// web view. `%@` = `Brand.name`; the support address comes from `game.json support.email` and every line naming it is left out
/// while none is configured.
struct InfoPage: View {
    enum Kind: String, CaseIterable {
        case support, terms, privacy
        var popupID: String { "page." + rawValue }
        init?(popupID: String) { self.init(rawValue: popupID.replacingOccurrences(of: "page.", with: "")) }
    }

    let kind: Kind
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let f = t.file
        let card = t.rect("page.card", CGRect(19, 126, 355, 658), .top, m)
        let bottom = m.size.height - m.safeBottom - 34 * m.s
        let body = CGFloat(f.double("text.page.body.size", 17)) * m.s
        let heading = CGFloat(f.double("text.page.body.heading", 21)) * m.s
        let colour = Color(hexString: f.string("text.page.body.colour", Skin.popupsSettingsPopupTextPageBodyColourHex)) ?? Color(hex: Skin.popupsSettingsPopupInfoPageColour)
        let inset = CGFloat(f.double("text.page.body.inset", 20)) * m.s
        let lineGap = body * (CGFloat(f.double("text.page.body.lineHeight", 1.3)) - 1)
        let email = SettingsPopup.supportEmail(app)
        ZStack(alignment: .topLeading) {
            ShellPageBackground(t: t).frame(width: m.size.width, height: m.size.height)
            ZStack {
                RoundedRectangle(cornerRadius: 23.7 * m.s).fill(Color(hex: Skin.popupsSettingsPopupInfoPageFill))
                RoundedRectangle(cornerRadius: 22.7 * m.s).fill(t.color("card.fill", Skin.popupsSettingsPopupCardFill)).padding(1.2)
                ScrollView(.vertical, showsIndicators: false) {
                    VStack(alignment: .leading, spacing: 14 * m.s) {
                        ForEach(Array(sections(email: email).enumerated()), id: \.offset) { _, sec in
                            VStack(alignment: .leading, spacing: 5 * m.s) {
                                if let h = sec.heading {
                                    Text(h).font(GameText.pageFont(heading)).foregroundStyle(colour)
                                }
                                Text(sec.body).font(GameText.pageFont(body)).foregroundStyle(colour)
                                    .lineSpacing(lineGap).fixedSize(horizontal: false, vertical: true)
                            }
                        }
                        if kind == .support, let email { contact(email, body: body, colour: colour) }
                        if kind == .support {
                            Text("Version \(Self.version) · Level \(app.store.state.level)")
                                .font(GameText.pageFont(body * 0.82)).foregroundStyle(colour.opacity(0.7))
                                .accessibilityIdentifier("page.support.version")
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(inset)
                    .tint(Color(hex: Skin.popupsSettingsPopupInfoPageTint))     // A5: the auto-detected email link in D1 teal (was the system blue)
                }
                .padding(1.2)
                .clipShape(RoundedRectangle(cornerRadius: 22.7 * m.s))
            }
            .frame(width: card.width, height: max(0, bottom - card.minY))
            .offset(x: card.minX, y: card.minY)
            ShellPageHeader(t: t)
            PageTitle(title: title, t: t)
            PopupCloseButton(id: "page.\(kind.rawValue).close", t: t, halo: true) { answer(PopupResult.close) }
                .placed(t.rect("settings.closeDisc", CGRect(325.2, 49.0, 45, 45), .top, m))
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("page.\(kind.rawValue)")
    }

    /// "Write to us at" + the address + Copy (→ toast "Copied"): the Support page when no mail route opened (GP §12.2).
    @ViewBuilder private func contact(_ email: String, body: CGFloat, colour: Color) -> some View {
        VStack(alignment: .leading, spacing: 6 * m.s) {
            Text("Write to us at").font(GameText.pageFont(body)).foregroundStyle(colour)
            HStack(spacing: 10 * m.s) {
                Text(verbatim: email).font(GameText.pageFont(body)).foregroundStyle(Color(hex: Skin.popupsSettingsPopupInfoPageContactForegroundStyle))
                    .textSelection(.enabled)
                GameButton(id: "page.support.copy", label: "Copy", action: {
                    UIPasteboard.general.string = email
                    app.toasts.show("Copied")
                }) {
                    Text("Copy").font(GameText.pageFont(body * 0.9)).foregroundStyle(.white)
                        .padding(.horizontal, 12 * m.s).padding(.vertical, 5 * m.s)
                        .background(Capsule().fill(Color(hex: Skin.popupsSettingsPopupInfoPageContactFill)))
                }
            }
        }
    }

    private var title: LocalizedStringResource {
        switch kind {
        case .support: return "Support"
        case .terms: return "Terms"
        case .privacy: return "Privacy"
        }
    }

    private struct Section { let heading: LocalizedStringResource?; let body: LocalizedStringResource }

    private func sections(email: String?) -> [Section] {
        let name = Brand.name
        switch kind {
        case .support:
            // the offline Help page (SPEC-ui §2.13.1; numbers = SPEC-gameplay §8.1 lives, boosters.freezeSeconds 10)
            return [
                Section(heading: "How to play", body: "Tap an arrow to send it out along its path. If something is in the way it bumps back and you lose a heart. Clear every arrow before the time runs out!"),
                Section(heading: "Lives", body: "Starting a level uses a life; winning gives it back. A new life arrives every 30 minutes."),
                Section(heading: "Boosters", body: "The hourglass freezes the timer for 10 seconds. The bulb shows an arrow that can move."),
                Section(heading: "Your progress", body: "Your progress and coins are saved only on this device. Deleting the game erases them."),
            ]
        case .terms:
            var list = [
                Section(heading: nil, body: "\(name) is a puzzle game."),
                Section(heading: nil, body: "Coins, lives, boosters and other items in the game have no money value and cannot be exchanged or refunded outside the game."),
                Section(heading: nil, body: "Purchases are made through Apple and follow the App Store terms. We never see your payment details."),
                Section(heading: nil, body: "The game is provided as is. We may update the game and these terms."),
            ]
            if let email { list.append(Section(heading: nil, body: "Questions? Write to \(email)")) }
            return list
        case .privacy:
            // A game that adds an attribution SDK must add paragraphs here saying what it sends (docs/recipes/ad-attribution.md).
            var list = [
                Section(heading: nil, body: "\(name) has no accounts and shows no ads."),
                Section(heading: nil, body: "Your progress, settings and profile name are stored only on this device."),
                Section(heading: nil, body: "The game works offline. Purchases are processed by Apple. Our purchase service, RevenueCat, receives an anonymous ID and your purchase records."),
                Section(heading: nil, body: "Notifications are scheduled on your device and can be turned off in Settings."),
            ]
            if let email {
                list.append(Section(heading: nil, body: "If you write to support, we use your message only to answer you."))
                list.append(Section(heading: nil, body: "Contact: \(email)"))
            }
            return list
        }
    }

    static var version: String { Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "?" }
}

/// The in-app mail composer (no network needed to compose; iOS sends it). Dismisses itself; never reports "sent".
@MainActor final class MailComposer: NSObject, MFMailComposeViewControllerDelegate {
    static let shared = MailComposer()

    func present(from host: UIViewController, to address: String, subject: String, body: String) {
        let vc = MFMailComposeViewController()
        vc.mailComposeDelegate = self
        vc.setToRecipients([address])
        vc.setSubject(subject)
        vc.setMessageBody(body, isHTML: false)
        host.present(vc, animated: true)
    }

    nonisolated func mailComposeController(_ controller: MFMailComposeViewController, didFinishWith result: MFMailComposeResult,
                                           error: Error?) {
        Task { @MainActor in controller.dismiss(animated: true) }
    }
}

extension UIApplication {
    /// The front-most view controller of the key window (for system sheets).
    var topViewController: UIViewController? {
        let scene = connectedScenes.compactMap { $0 as? UIWindowScene }.first { $0.activationState == .foregroundActive }
            ?? connectedScenes.compactMap { $0 as? UIWindowScene }.first
        var top = scene?.windows.first { $0.isKeyWindow }?.rootViewController ?? scene?.windows.first?.rootViewController
        while let next = top?.presentedViewController { top = next }
        return top
    }
}
