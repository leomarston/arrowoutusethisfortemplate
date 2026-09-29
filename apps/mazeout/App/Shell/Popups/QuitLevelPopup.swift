import SwiftUI

// SHELL S1 (SPEC-architecture §6.6 "quitLevel"; SPEC-ui §2.5 + correction C2, VERIFIED meta-075 / meta-092). v552's Quit Level?
// is the full-width BAND popup of the Continue? family (BandPopupFrame): the yellow ribbon "Quit Level?" (the Paused title style
// shrunk to the 228 pt box → 43.3 pt), the red X, the cream strip with "You will lose a life!" (25.4 / −1.3 #622100 plain) over
// the broken heart, and a red "Quit" (43.2 pt) framed in a blue well. Opened by the HUD back button (also before the first tap)
// or Pause → Quit. Dim 0.90 (the style's). Answers: Quit → .primary, X → .close (back to the level, timer unchanged).

struct QuitLevelPopup: View {
    let answer: PopupAnswer
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        // a full-width band stretches edge to edge on phones wider than the 393 pt canvas (SPEC-ui §1.1)
        let extra = max(0, (m.size.width / max(m.popupScale, 0.01) - 393) / 2)
        let band = t.frame("quit.band", CGRect(0, 234.2, 393, 405)).insetBy(dx: -extra, dy: 0)
        let quit = t.frame("quit.quit", CGRect(91.1, 499.4, 211.2, 86.4))
        let message = t.text("quit.message", GameTextStyle(size: 25.4, tracking: -1.3, fill: [Color(hex: 0x5A2801)]))
        let msgAt = t.textPoint("quit.message", baseline: 344.0, centreX: 196.2)
        let label = t.text("quit.quit", GameTextStyle(size: 43.2, tracking: -0.5,
                                                      fill: [Color(hex: 0xFFFBF3), Color(hex: 0xFFF8E8), Color(hex: 0xFDF3DF)],
                                                      outline: Color(hex: 0x610B00), outlineWidth: 2.3, drop: 2.25))
        let labelAt = t.textPoint("quit.quit", baseline: 553.7, centreX: 198.0)
        ZStack(alignment: .topLeading) {
            BandPopupFrame(t: t).placed(band)
            // the raster carries padding: its visible heart fills the measured `quit.heart` box (122.8 × 97.4)
            ArtImage(art: .heartBroken).placed(t.frame("quit.heartArt", CGRect(131.7, 354.0, 127.0, 104.8)))
            GameText("You will lose a life!", style: message, maxWidth: t.textMaxWidth("quit.message", 340))
                .at(msgAt.x, message.capCentre(baseline: msgAt.baseline))
                .accessibilityIdentifier("popup.quitLevel.message")
            FramedButton(id: "popup.quitLevel.primary", title: "Quit", colors: .red, frame: quit,
                         well: t.frame("quit.quitFrame", CGRect(79.7, 490.7, 233.9, 106.4)), n: t.superellipseN("quit.quit", 4.5),
                         style: label, baseline: labelAt.baseline, centreX: labelAt.x, maxWidth: t.textMaxWidth("quit.quit", 170), t: t) {
                answer(PopupResult.primary)
            }
            PopupTitle(title: "Quit Level?", frame: t.frame("quit.ribbon", CGRect(60.1, 193.5, 274.2, 90.4)), t: t,
                       baselineFromTop: CGFloat(t.file.double("text.quit.title.baseline", 253.4)) - 193.5)
            PopupCloseButton(id: "popup.quitLevel.close", t: t) { answer(PopupResult.close) }
                .placed(t.frame("quit.closeDisc", CGRect(339.8, 218.7, 45, 45)))
        }
    }
}
