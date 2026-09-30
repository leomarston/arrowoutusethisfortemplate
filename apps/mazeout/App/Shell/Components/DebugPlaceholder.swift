#if DEBUG
import SwiftUI

// SHELL S1 (SPEC-architecture §6.11, §12.2 V1; GP §14 "never ship stand-in content"). DEBUG BUILDS ONLY: the whole file is
// compiled out of Release, so no placeholder can reach the shipped binary. V1 proves it with
// `strings ArrowOut | grep -c "PC-DEBUG-PLACEHOLDER"` = 0 on the Release binary (and > 0 on Debug as the control).

/// The hatched stand-in drawn where an art file is still missing (the art lanes' `todo` ids), with its id.
struct DebugPlaceholder: View {
    static let marker = "PC-DEBUG-PLACEHOLDER"
    let name: String

    var body: some View {
        GeometryReader { geo in
            let r = CGRect(origin: .zero, size: geo.size)
            ZStack {
                Rectangle().fill(Color(hex: Skin.componentsDebugPlaceholderDebugPlaceholderFill, 0.55))
                Canvas { ctx, size in
                    var hatch = Path()
                    var x: CGFloat = -size.height
                    while x < size.width {
                        hatch.move(to: CGPoint(x: x, y: size.height)); hatch.addLine(to: CGPoint(x: x + size.height, y: 0)); x += 8
                    }
                    ctx.stroke(hatch, with: .color(.white.opacity(0.35)), lineWidth: 1.5)
                }
                Rectangle().stroke(Color.black.opacity(0.35), style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
                if r.width > 30 && r.height > 12 {
                    Text(verbatim: name)
                        .font(.system(size: min(10, max(6, r.width / 10)), weight: .bold, design: .monospaced))
                        .foregroundStyle(.black.opacity(0.6))
                        .lineLimit(2)
                        .minimumScaleFactor(0.5)
                        .padding(2)
                }
            }
        }
        .allowsHitTesting(false)
        .accessibilityElement(children: .ignore)
        .accessibilityIdentifier("debug.placeholder")
        .accessibilityLabel(Text(verbatim: "\(Self.marker) \(name)"))
    }
}
#endif
