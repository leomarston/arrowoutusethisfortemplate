import SwiftUI
import PathCore

// SHELL S1 (SPEC-architecture §6.4 item 3; design/ui-measure.md `home.playFrame`, `home.playButton*`, `home.hardRibbon`,
// `home.superHardRibbon`; VERIFIED 026 / 035 / 060). The blue outer frame (superellipse n 4.4, 228.2 x 103.8) around the glossy
// button (n 4.7, 211.2 x 86.7; GlossyChrome's PanelButton layer recipe: green / red / purple faces) with "Play" (48.8 / −3.25).
// Hard: red face + the red "Hard Level" ribbon on the frame's top edge; Super Hard: purple + "Super Hard". Play is static (no
// pulse, VERIFIED motion §6.5); it presses to 0.95 on touch-down and fires on release (GameButton).

struct HomePlayButton: View {
    let level: Int
    let tag: LevelTag
    let action: () -> Void
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let frame = t.rect("home.playFrame", CGRect(82.7, 622.2, 228.2, 103.8), .bottom, m)
        let button = t.rect("home.playButton", CGRect(91.1, 628.2, 211.2, 86.7), .bottom, m)
        let (colors, textID): (PanelButtonStyleColors, String) = {
            switch tag {
            case .normal: return (.green, "home.play")
            case .hard: return (.red, "home.playHard")
            case .superHard: return (ChromePalette.purple, "home.playSuperHard")
            }
        }()
        let fallbackOutline: UInt32 = tag == .normal ? 0x924500 : tag == .hard ? 0x610B00 : 0x5C0B32
        let label = t.text(textID, GameTextStyle(size: 48.8, tracking: -3.25, fill: [Color(hex: 0xFFFBF2)],
                                                 outline: Color(hex: fallbackOutline), outlineWidth: 2.2, drop: 2.2))
            .sized(48.8 * m.s)
        let base = m.point(CGPoint(x: 197.0, y: 686.3), .bottom)
        let frameColors = t.colors("home.playFrame", [0x006963, 0x38B2A2, 0x38AD9D, 0x00857E])
        return ZStack(alignment: .topLeading) {
            Superellipse(n: t.superellipseN("home.playFrame", 4.4))
                .fill(LinearGradient(stops: [.init(color: frameColors[0], location: 0),
                                             .init(color: frameColors[min(1, frameColors.count - 1)], location: 0.07),
                                             .init(color: frameColors[min(2, frameColors.count - 1)], location: 0.93),
                                             .init(color: frameColors[frameColors.count - 1], location: 1)],
                                     startPoint: .top, endPoint: .bottom))
                .placed(frame)
                .accessibilityHidden(true)
            // A2 (motion-catalog §5.1 row 17, ruling 39 OD4): Play clicks with its own stronger haptic (`play`, rigid 0.75)
            GameButton(id: "home.play", label: "Play", value: "\(level)", haptic: .play, action: action) {
                ZStack(alignment: .topLeading) {
                    ChromeButtonFace(colors: colors, n: t.superellipseN("home.playButton", 4.7),
                                     sideInset: CGFloat(t.number("layout.playFaceSideInset", 4)))
                    GameText("Play", style: label, maxWidth: button.width - 36 * m.s)
                        .at(base.x - button.minX, label.capCentre(baseline: base.y) - button.minY)
                }
                .frame(width: button.width, height: button.height, alignment: .topLeading)
            }
            .placed(button)
            .anchor(.playButton)
            if tag != .normal { DifficultyTag(tag: tag).placed(t.rect("home.hardRibbon", CGRect(136.8, 620.5, 120.1, 30), .bottom, m)) }
        }
    }
}

/// The "Hard Level" / "Super Hard" ribbon on the Play frame's top edge (a banner with slanted ends; PENDING-ui for its
/// exact shading, VERIFIED face and text).
struct DifficultyTag: View {
    let tag: LevelTag
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let hard = tag == .hard
        let face = hard ? t.colors("home.ribbonHard", [0xEE5E4A, 0xD03726, 0xA91A0F]) : t.colors("home.ribbonSuperHard", [0xD32D7C, 0x9B1960, 0x6D1840])
        let outline = hard ? t.color("home.ribbonHardOutline", 0x610B00) : t.color("home.ribbonSuperHardOutline", 0x5C0B32)
        let style = hard
            ? t.text("home.hardRibbon", GameTextStyle(size: 17, tracking: 0.2, fill: [Color(hex: 0xFFFAEF)], outline: Color(hex: 0x610B00),
                                                      outlineWidth: 1.58, drop: 0.35))
            : t.text("home.superHardRibbon", GameTextStyle(size: 15.8, tracking: -0.43, fill: [Color(hex: 0xFFFAEF)],
                                                           outline: Color(hex: 0x5C0B32), outlineWidth: 0.93, drop: 0.88))
        GeometryReader { geo in
            let w = geo.size.width, h = geo.size.height
            ZStack(alignment: .topLeading) {
                TagBanner().fill(outline)
                TagBanner().fill(LinearGradient(colors: face, startPoint: .top, endPoint: .bottom)).padding(1.2)
                GameText(hard ? "Hard Level" : "Super Hard", style: style.sized(style.size * m.s), maxWidth: w - 18)
                    .at(w / 2, style.sized(style.size * m.s).capCentre(baseline: h * 19 / 30))
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("home.tagRibbon")
        .accessibilityLabel(Text(hard ? "Hard Level" : "Super Hard"))
    }
}

/// A banner whose bottom corners are cut inwards (the tag ribbon's slanted ends).
private struct TagBanner: Shape {
    func path(in r: CGRect) -> Path {
        let cut = r.height * 0.28, rad = r.height * 0.18
        var p = Path()
        p.move(to: CGPoint(x: r.minX + rad, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX - rad, y: r.minY))
        p.addQuadCurve(to: CGPoint(x: r.maxX, y: r.minY + rad), control: CGPoint(x: r.maxX, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX - cut, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX + cut, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX, y: r.minY + rad))
        p.addQuadCurve(to: CGPoint(x: r.minX + rad, y: r.minY), control: CGPoint(x: r.minX, y: r.minY))
        p.closeSubpath()
        return p
    }
}
