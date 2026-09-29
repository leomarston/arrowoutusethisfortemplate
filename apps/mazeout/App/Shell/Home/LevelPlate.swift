import SwiftUI
import PathCore

// SHELL S1 (SPEC-architecture §6.4 item 3; design/ui-measure.md `home.levelCaption`, `home.levelPlate*` VERIFIED 026 / 035 / 060).
// The outlined "LEVEL" caption over the plate with the next level's number: green (normal), red (Hard), purple (Super Hard).
// The plate: a rounded rect r 14.8 with a 12-stop column (grad.home.levelPlate: dark-green outline, face #08CF01 → #06B401,
// bottom lip #077701). The Hard / Super Hard faces are measured (#C2090E / #7400B6); their shading follows the green column
// (colors.home.plateFace*, PENDING-ui).

struct HomeLevelPlate: View {
    let level: Int
    let tag: LevelTag
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        let plate = t.rect("home.levelPlate", CGRect(147.5, 536.8, 98.4, 32.4), .bottom, m)
        let caption = t.text("home.levelCaption", GameTextStyle(size: 14.1, tracking: -1.5, fill: [.white],
                                                                outline: Color(hex: 0x00434A), outlineWidth: 0.82, drop: 0.76))
        let numberID: String = tag == .hard ? "home.levelNumberHard" : tag == .superHard ? "home.levelNumberSuperHard" : "home.levelNumber"
        let number = t.text(numberID, GameTextStyle(size: 30.6, tracking: -1.5, fill: [.white], outline: Color(hex: 0x924500),
                                                    outlineWidth: 2.14, drop: 0.5))
        let face: [Color]
        let outline: Color
        switch tag {
        case .normal:
            face = t.colors("home.plateFace", [0xFFAA1C, 0xFC9D10, 0xE4830A, 0xA1500A]); outline = t.color("home.plateOutline", 0x954709)
        case .hard:
            face = t.colors("home.plateFaceHard", [0xD83A28, 0xB92517, 0x9F140A, 0x660B02]); outline = t.color("home.plateOutlineHard", 0x660B02)
        case .superHard:
            face = t.colors("home.plateFaceSuperHard", [0xAE1A6A, 0x901456, 0x751344, 0x4B1029])
            outline = t.color("home.plateOutlineSuperHard", 0x4B1029)
        }
        let r = t.radius("home.levelPlate", 14.85) * m.s
        let cap = m.point(CGPoint(x: 196.0, y: 531.8), .bottom)
        let num = m.point(CGPoint(x: 196.5, y: 563.1), .bottom)
        return ZStack(alignment: .topLeading) {
            GameText("LEVEL", style: caption.sized(caption.size * m.s), maxWidth: 90 * m.s)
                .at(cap.x, caption.sized(caption.size * m.s).capCentre(baseline: cap.y))
                .accessibilityIdentifier("home.levelCaption")
            ZStack {
                RoundedRectangle(cornerRadius: r).fill(outline)
                RoundedRectangle(cornerRadius: max(0, r - 1))
                    .fill(LinearGradient(stops: [.init(color: face[0], location: 0), .init(color: face[min(1, face.count - 1)], location: 0.3),
                                                 .init(color: face[min(2, face.count - 1)], location: 0.93),
                                                 .init(color: face[face.count - 1], location: 1)], startPoint: .top, endPoint: .bottom))
                    .padding(EdgeInsets(top: 2.2, leading: 1.2, bottom: 1, trailing: 1.2))   // 026: ~2.3 pt dark rim on top
                RoundedRectangle(cornerRadius: max(0, r - 3)).fill(Color.white.opacity(0.18)).frame(height: 3).padding(.horizontal, 10)
                    .frame(maxHeight: .infinity, alignment: .top).padding(.top, 2.5)
            }
            .placed(plate)
            .anchor(.levelPlate)
            GameText(verbatim: "\(level)", style: number.sized(number.size * m.s), maxWidth: (plate.width - 12))
                .at(num.x, number.sized(number.size * m.s).capCentre(baseline: num.y))
        }
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("home.level")
        .accessibilityLabel(Text("Level \(level)"))
        .accessibilityValue(Text(verbatim: "\(level)|\(tag.rawValue)"))
    }
}
