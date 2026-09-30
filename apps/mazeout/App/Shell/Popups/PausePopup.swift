import SwiftUI
import PathCore

// SHELL S1 (SPEC-architecture §6.6 "level: pause (Sound, Haptic toggles, Resume, Quit, X)"; design/ui-measure.md `pause`,
// shot 007 VERIFIED). Answers: Resume → .primary, Quit → .secondary (GAME then asks `quitLevel`), X → .close.
// The toggles write `PlayerState.settings` through the PlayerStore (never UserDefaults, D11) and apply at once to the audio
// bus and the haptics gate (§6.9).

struct PausePopup: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app

    var body: some View {
        let t = app.tuning.ui.tokens
        let panel = t.frame("pause.panel", CGRect(11.3, 228.9, 370.6, 399))
        let s = app.store.state.settings
        ZStack(alignment: .topLeading) {
            PopupPanelFrame(n: t.superellipseN("pause.panel", 6.31), t: t).placed(panel)
            PopupCard(radius: t.radius("pause.card", 24.44), t: t).placed(t.frame("pause.card", CGRect(51.4, 299.6, 287.9, 165.8)))
            SettingRow(icon: .glyphSound, label: "Sound", key: \.sound, id: "pause.toggle.sound",
                       iconFrame: t.frame("pause.iconSound", CGRect(73.4, 331.6, 31.4, 28.7)),
                       toggle: t.frame("pause.toggleSound", CGRect(206.5, 328.6, 116.1, 37.4)), baseline: 354.3, isOn: s.sound)
            SettingRow(icon: .glyphHaptic, label: "Haptic", key: \.haptic, id: "pause.toggle.haptic",
                       iconFrame: t.frame("pause.iconHaptic", CGRect(72.4, 403.3, 33, 31.7)),
                       toggle: t.frame("pause.toggleHaptic", CGRect(206.5, 401.7, 116.1, 37.4)), baseline: 427.6, isOn: s.haptic)
            PanelPairButton(id: "popup.pause.primary", title: "Resume", colors: .green, textID: "pause.resume",
                            frame: t.frame("pause.resume", CGRect(60.4, 486.1, 125.1, 89.1)), baseline: 539.5, centreX: 123.6,
                            fallback: GameTextStyle(size: 30.5, tracking: -1.0,
                                                    fill: [Color(hex: Skin.popupsPausePopupPausePopupFill0), Color(hex: Skin.popupsPausePopupPausePopupFill1), Color(hex: Skin.popupsPausePopupPausePopupFill2)],
                                                    outline: Color(hex: Skin.popupsPausePopupPausePopupOutline), outlineWidth: 1.42, drop: 1.06)) {
                answer(PopupResult.primary)
            }
            PanelPairButton(id: "popup.pause.secondary", title: "Quit", colors: .red, textID: "pause.quit",
                            frame: t.frame("pause.quit", CGRect(206.5, 486.1, 125.1, 89.1)), baseline: 540.8, centreX: 269.1,
                            fallback: GameTextStyle(size: 30.5, tracking: -0.5,
                                                    fill: [Color(hex: Skin.popupsPausePopupPausePopupFill0), Color(hex: Skin.popupsPausePopupPausePopupFill1V2), Color(hex: Skin.popupsPausePopupPausePopupFill2V2)],
                                                    outline: Color(hex: Skin.popupsPausePopupPausePopupOutlineV2), outlineWidth: 1.47, drop: 1.4)) {
                answer(PopupResult.secondary)
            }
            PopupTitle(title: "Paused", frame: t.frame("pause.ribbon", CGRect(60.1, 190.5, 274.2, 90.4)), t: t)
            PopupCloseButton(id: "popup.pause.close", t: t) { answer(PopupResult.close) }
                .placed(t.frame("pause.close", CGRect(338.6, 234.2, 45.4, 45)))
        }
    }
}

/// One settings row on a cream card: the glyph, the plain brown label left-aligned at the measured ink edge, the toggle.
struct SettingRow: View {
    let icon: UIArt
    let label: LocalizedStringResource
    let key: WritableKeyPath<PlayerState.Settings, Bool>
    let id: String
    let iconFrame: CGRect
    let toggle: CGRect
    let baseline: CGFloat
    let isOn: Bool
    /// The label's left ink edge; nil = the Paused card's measured 114.4 (`text.pause.rowLabel.left`).
    var labelLeft: CGFloat? = nil
    @Environment(AppModel.self) private var app

    var body: some View {
        let t = app.tuning.ui.tokens
        let style = t.text("pause.rowLabel", GameTextStyle(size: 25.5, tracking: 0, fill: [Color(hex: Skin.popupsPausePopupPauseRowLabelFill0)]))
        let left = labelLeft ?? CGFloat(app.tuning.ui.file.double("text.pause.rowLabel.left", 114.4))
        let text = GameText(label, style: style, maxWidth: toggle.minX - left - 6)
        ZStack(alignment: .topLeading) {
            ArtImage(art: icon).placed(iconFrame)
            text.at(left + text.layout.advance / 2, style.capCentre(baseline: baseline))
            PopupToggle(id: id, isOn: isOn, t: t) { ShellSettings.toggle(app, key, name: id) }.placed(toggle)
        }
    }
}

/// The 125 x 89 glossy Resume / Quit pair (GlossyChrome's PanelButton body) with a live GameText label.
struct PanelPairButton: View {
    let id: String
    let title: LocalizedStringResource
    let colors: PanelButtonStyleColors
    let textID: String
    let frame: CGRect
    let baseline: CGFloat
    let centreX: CGFloat
    let fallback: GameTextStyle
    let action: () -> Void
    @Environment(AppModel.self) private var app

    var body: some View {
        let t = app.tuning.ui.tokens
        let style = t.text(textID, fallback)
        GameButton(id: id, label: title, action: action) {
            ZStack(alignment: .topLeading) {
                Rasterized("panelButton|\(colors.rasterID)", overflow: 3) { _ in PanelButton(colors: colors, label: nil) }
                    .frame(width: frame.width, height: frame.height)
                GameText(title, style: style, maxWidth: t.textMaxWidth(textID, 100))
                    .at(centreX - frame.minX, style.capCentre(baseline: baseline) - frame.minY)
            }
            .frame(width: frame.width, height: frame.height, alignment: .topLeading)
        }
        .placed(frame)
    }
}

/// Settings writes (Pause + Settings popups): PlayerState only, applied to the engines at once.
@MainActor enum ShellSettings {
    @discardableResult
    static func toggle(_ app: AppModel, _ key: WritableKeyPath<PlayerState.Settings, Bool>, name: String) -> Bool {
        toggle(store: app.store, audio: app.audio, haptics: app.haptics, key, name: name)
    }

    /// Flips one setting in PlayerState (saved at once, off the main thread) and applies it to the buses / haptics gate.
    @discardableResult
    static func toggle(store: PlayerStore, audio: any AudioPlaying, haptics: any HapticPlaying,
                       _ key: WritableKeyPath<PlayerState.Settings, Bool>, name: String) -> Bool {
        let value = store.mutateAndSave { s -> Bool in
            s.settings[keyPath: key].toggle()
            return s.settings[keyPath: key]
        }
        let settings = store.state.settings
        let hapticTurnedOn = key == \PlayerState.Settings.haptic && value && !haptics.enabled
        audio.apply(settings: settings)
        haptics.enabled = settings.haptic
        // A2 (motion-catalog §5.1 row 18, the toggle-order fix): the button's own haptic was asked for BEFORE this action, while
        // haptics were still off, so it was dropped; switching Haptic ON now answers with that click, after enabling
        if hapticTurnedOn { haptics.play(.button) }
        Log.mark("settings", "\(name) \(value ? "on" : "off")")
        return value
    }
}
