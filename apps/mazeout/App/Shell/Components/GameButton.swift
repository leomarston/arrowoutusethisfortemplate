import SwiftUI

// SHELL S1 (SPEC-architecture §6.11; SPEC-motion-audio §6.1 / MA8: "scale 0.95 on touch-down, instant, held; action + click +
// haptic on RELEASE; back to 1.0 instantly"). The click is `audio.json cues.uiButton`; the haptic is `ui.json button.haptic`
// ("button": `.rigid` 0.60 since ruling 39 OD4 / contract amend 4, was `.light` 0.50), or the button's own `haptic` (Play). `clicks:
// false` drops both the sound and the haptic (the win panel's Continue takes its own haptic, S2). While a forced tutorial
// locks input (`PopupStyle.inputLock`) every button except the tutorial's target ignores taps silently.

private struct TapsLockedKey: EnvironmentKey { static let defaultValue = false }

extension EnvironmentValues {
    /// Set by an input-locked popup; the tutorial target resets it to false for itself.
    var tapsLocked: Bool {
        get { self[TapsLockedKey.self] }
        set { self[TapsLockedKey.self] = newValue }
    }
}

@MainActor enum GameButtonFeedback {
    /// The haptic a UI button plays on release, if the contract has the named case.
    static func haptic(_ app: AppModel) -> Haptic? {
        Haptic(rawValue: app.tuning.ui.file.string("button.haptic", "button"))
    }
}

/// Scale on touch-down in one frame (no animation in either direction), held until release.
struct PressStyle: ButtonStyle {
    var scale: CGFloat = 0.95
    var enabled = true
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed && enabled ? scale : 1)
            .transaction { $0.animation = nil }
    }
}

struct GameButton<Content: View>: View {
    let id: String
    /// Accessibility label (the visible title); nil for icon buttons.
    var label: LocalizedStringResource?
    var value: String?
    var enabled = true
    var clicks = true
    /// A2 (motion-catalog §5.1 row 17): a per-button haptic instead of `button.haptic` (Play: `.play`).
    var haptic: Haptic?
    /// A2 (motion-catalog §11.3 R6, VERIFIED v582): false = no press scale (the Pause toggles do not shrink).
    var presses = true
    let action: () -> Void
    @ViewBuilder var content: Content

    @Environment(\.tapsLocked) private var locked
    @Environment(AppModel.self) private var app

    init(id: String, label: LocalizedStringResource? = nil, value: String? = nil, enabled: Bool = true, clicks: Bool = true,
         haptic: Haptic? = nil, presses: Bool = true, action: @escaping () -> Void, @ViewBuilder content: () -> Content) {
        self.id = id; self.label = label; self.value = value; self.enabled = enabled; self.clicks = clicks
        self.haptic = haptic; self.presses = presses; self.action = action; self.content = content()
    }

    var body: some View {
        Button {
            guard enabled, !locked else { return }
            if clicks, let cue = app.tuning.audio.cue("uiButton") { app.audio.play(cue, gain: Float(app.tuning.audio.gain(cue))) }
            if clicks, let h = haptic ?? GameButtonFeedback.haptic(app) { app.haptics.play(h) }
            action()
        } label: { content.contentShape(Rectangle()) }
            .buttonStyle(PressStyle(scale: presses ? CGFloat(app.tuning.ui.buttonPressScale) : 1, enabled: enabled && !locked))
            .accessibilityIdentifier(id)
            .modifier(ButtonAccessibility(label: label, value: value))
    }
}

private struct ButtonAccessibility: ViewModifier {
    let label: LocalizedStringResource?
    let value: String?
    func body(content: Content) -> some View {
        let labelled = Group {
            if let label { content.accessibilityLabel(Text(label)) } else { content }
        }
        if let value { labelled.accessibilityValue(Text(verbatim: value)) } else { labelled }
    }
}
