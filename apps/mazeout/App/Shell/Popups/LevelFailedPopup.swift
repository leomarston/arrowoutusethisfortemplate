import SwiftUI
import PathCore

// SHELL S2 (SPEC-ui §2.6.5; uim `failed.*`, VERIFIED 016 / 031 / meta-072 / 080 / 090 / 093). The end of the fail chain:
// the blue panel 10 · 198.2 · 373.3 · 464.4 (n 6.0), the ribbon with the level label ("Level 62"; "Level 1-4" for the FTUE
// session), the cream card 54.7 · 280.9 · 283.9 · 210.2 with the broken heart and "Level Failed!" (25 / −0.7 #622100), the
// framed green "Try Again" 90.4 · 517.1 · 212.5 · 88.4 (37.7 / −1.9), the X (361.3, 229.7) and, from the Streak Race unlock,
// the Streak Race strip under it with the lit chip sliding back to x1 (SPEC-motion-audio §5 "Fail panel"; a `PanelStrips` slot
// the streak-race component fills). The ribbon label (`PanelLabel`) is ui-chrome's (PopupChrome.swift).
// Answers: Try Again → .primary (GAME: the same board, the lives gate); X → .close (home; before the first home a retry,
// CONSISTENCY §21 item 17 — GAME's routing).

struct LevelFailedPopup: View {
    let levels: [Int]
    let reason: LossReason
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @State private var shownAt: Double?

    var body: some View {
        let t = app.tuning.ui.tokens
        let face = t.frame("failed.tryAgain", CGRect(90.4, 517.1, 212.5, 88.4))
        ZStack(alignment: .topLeading) {
            PopupPanelFrame(n: t.superellipseN("failed.panel", 6.04), t: t).placed(t.frame("failed.panel", CGRect(10.0, 198.2, 373.3, 464.4)))
            PopupCard(radius: t.radius("failed.card", 24.19), t: t).placed(t.frame("failed.card", CGRect(54.7, 280.9, 283.9, 210.2)))
            InkImage(art: .livesLost, ink: t.frame("failed.brokenHeart", CGRect(121.25, 302.45, 154.1, 122.0)))
            TokenText(id: "failed.caption.caption", source: .copy("Level Failed!"), style: .s2(25.0, -0.71, [Skin.popupsLevelFailedPopupLevelFailedPopupStyle0]),
                      baseline: 463.3, centreX: 196.8, maxWidth: 260)
            WellFramedButton(id: "popup.levelFailed.primary", title: "Try Again", colors: .green, frame: face,
                         well: t.frame("failed.tryAgainFrame", face.insetBy(dx: -11.3, dy: -8.7).offsetBy(dx: 0, dy: 0.2)),
                         n: t.superellipseN("failed.tryAgain", 4.6),
                         style: t.text("failed.tryAgain.label", .s2(37.7, -1.94, [Skin.popupsLevelFailedPopupFailedTryAgainLabel0, Skin.popupsLevelFailedPopupFailedTryAgainLabel1, Skin.popupsLevelFailedPopupFailedTryAgainLabel2], outline: Skin.popupsLevelFailedPopupFailedTryAgainLabelOutline, 1.6, drop: 1.83)),
                         baseline: CGFloat(t.number("text.failed.tryAgain.label.baseline", 570.1)),
                         centreX: CGFloat(t.number("text.failed.tryAgain.label.centreX", 196.5)),
                         maxWidth: t.textMaxWidth("failed.tryAgain.label", 176), t: t) { answer(PopupResult.primary) }
            PopupTitle(title: PanelLabel.resource(levels), frame: t.frame("failed.ribbon", CGRect(60.1, 171.1, 274.2, 90.4)), t: t,
                       baselineFromTop: CGFloat(t.number("text.failed.ribbon.title.baseline", 229.9)) - 171.1)
            PopupCloseButton(id: "popup.levelFailed.close", t: t) { answer(PopupResult.close) }
                .placed(t.frame("failed.closeDisc", CGRect(338.8, 207.2, 45, 45)))
            // the strip under the panel (a slot: the Streak Race's strip with its chip sliding back to x1, when that component is
            // in the game — `PanelStrips`, registered by StreakRaceRegistration)
            if let strip = PanelStrips.view(PanelStripContext(app: app, place: .levelFailed, level: levels.last ?? 0, outcomes: [],
                                                              shownAt: shownAt)) {
                strip
            }
        }
        .onAppear { shownAt = app.clock.gameTime() }
    }
}
