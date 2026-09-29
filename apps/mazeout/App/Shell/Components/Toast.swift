import SwiftUI

// SHELL S1 (SPEC-architecture §6.6 "ToastCenter.show(_ text: LocalizedStringResource): one at a time, newest replaces";
// SPEC-ui §2.20, DECISION — v552 shows no toast anywhere). A plate (#0B2176 at α 0.92, rr 16, a 1.5 pt #00B4FF border) around
// one or two lines of `role.toast` (18 pt white, outline #022880 1.0, drop 1.0, box 330, two lines max), padding 16 × 10, centred
// in x; its centre at y 390 (centre-anchored) on home and pages, and 110 pt below the top safe inset inside a level
// (`toast.homeY` / `toast.panelY`). Fade in `toast.in` 0.08 s, hold `toast.hold` 2.0 s, fade out `toast.out` 0.27 s (SPEC-motion-
// audio §6.6). Above popups (z 5). The TimelineView runs only while a toast is up. a11y `toast` (label).

@MainActor @Observable final class ToastCenter: ToastPresenting {
    struct Item: Equatable {
        let id: Int
        let text: String
        /// nil = the default place for the current screen (home/pages or a level).
        let y: CGFloat?
        let shownAt: Date
    }

    private(set) var current: Item?
    @ObservationIgnored private var next = 0
    @ObservationIgnored private var removal: Task<Void, Never>?
    @ObservationIgnored let ui: UITuning

    init(_ ctx: AppContext) { ui = ctx.tuning.ui }
    init(ui: UITuning) { self.ui = ui }

    var total: Double { ui.toastIn + ui.toastHold + ui.toastOut }

    func show(_ text: LocalizedStringResource) { show(text, y: nil) }

    /// `y`: the plate centre on the 393 x 852 canvas (centre-anchored); nil = the screen's default.
    func show(_ text: LocalizedStringResource, y: CGFloat?) {
        let resolved = String(localized: text)
        next += 1
        let item = Item(id: next, text: resolved, y: y, shownAt: Date())
        current = item
        Log.mark("toast", resolved)
        removal?.cancel()
        let life = total
        removal = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: UInt64(life * 1_000_000_000))
            guard !Task.isCancelled, let self, self.current?.id == item.id else { return }
            self.current = nil
        }
    }

    /// Alpha `t` seconds after the toast appeared (pure): a linear fade in, the hold, a linear fade out.
    func alpha(_ t: Double) -> Double {
        let tin = max(ui.toastIn, 0.001), hold = ui.toastHold, tout = max(ui.toastOut, 0.001)
        if t < 0 { return 0 }
        if t < tin { return t / tin }
        if t < tin + hold { return 1 }
        return max(0, 1 - (t - tin - hold) / tout)
    }

    /// Greedy word wrap into at most two lines of `maxWidth` (the last line keeps the rest and shrinks, min 0.7).
    nonisolated static func wrap(_ text: String, style: GameTextStyle, maxWidth: CGFloat) -> [String] {
        func width(_ s: String) -> CGFloat {
            GameTextLayout.make(s, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking).advance
        }
        guard width(text) > maxWidth else { return [text] }
        // B3: words = LineUnits (the old space split; dictionary words in ja / zh-Hans, which have no spaces)
        let words = LineUnits.units(text)
        var first = ""
        var i = 0
        while i < words.count {
            let candidate = LineUnits.join(words[..<(i + 1)])
            if width(candidate) > maxWidth && !first.isEmpty { break }
            first = candidate
            i += 1
        }
        let rest = LineUnits.join(words[i...])
        return rest.isEmpty ? [first] : [first, rest]
    }
}

struct ToastLayer: View {
    let center: ToastCenter
    let tokens: Tokens
    let inLevel: Bool
    @Environment(\.shellMetrics) private var m

    var body: some View {
        AnchoredCanvas {
            if let item = center.current {
                let f = tokens.file
                let base = tokens.text("toast", GameTextStyle(size: 18, fill: [.white], outline: Color(hex: 0x00373B), outlineWidth: 1.0, drop: 1.0))
                let style = base.sized(base.size * m.s)
                let box = CGFloat(f.double("toast.maxWidth", 330)) * m.s
                let lines = ToastCenter.wrap(item.text, style: style, maxWidth: box)
                let lineH = style.size * CGFloat(f.double("text.toast.lineHeight", 1.2))
                let padX = CGFloat(f.double("toast.padX", 16)) * m.s, padY = CGFloat(f.double("toast.padY", 10)) * m.s
                let widest = lines.map { GameText(verbatim: $0, style: style, maxWidth: box).layout.advance }.max() ?? 0
                let plateW = min(widest, box) + 2 * padX, plateH = CGFloat(lines.count) * lineH + 2 * padY
                let y: CGFloat = item.y.map { m.y($0, .centre) }
                    ?? (inLevel ? m.y(CGFloat(ShellMetrics.refSafeTop) + CGFloat(f.double("toast.panelY", 110)), .top)
                                : m.y(CGFloat(f.double("toast.homeY", 390)), .centre))
                TimelineView(.animation) { ctx in
                    let a = center.alpha(ctx.date.timeIntervalSince(item.shownAt))
                    ZStack {
                        RoundedRectangle(cornerRadius: CGFloat(f.double("toast.radius", 16)) * m.s)
                            .fill((Color(hexString: f.string("toast.plate", "#003135")) ?? Color(hex: 0x003135))
                                .opacity(f.double("toast.plateAlpha", 0.92)))
                        RoundedRectangle(cornerRadius: CGFloat(f.double("toast.radius", 16)) * m.s)
                            .strokeBorder(Color(hexString: f.string("toast.border", "#40BCAC")) ?? Color(hex: 0x40BCAC),
                                          lineWidth: CGFloat(f.double("toast.borderWidth", 1.5)))
                        ZStack {
                            ForEach(Array(lines.enumerated()), id: \.offset) { i, line in
                                GameText(verbatim: line, style: style, maxWidth: box)
                                    .position(x: plateW / 2, y: style.capCentre(baseline: padY + CGFloat(i) * lineH + style.size * 0.93))
                            }
                        }
                        .frame(width: plateW, height: plateH)
                    }
                    .frame(width: plateW, height: plateH)
                    .opacity(a)
                }
                .id(item.id)
                .position(x: m.size.width / 2, y: y)
                .accessibilityElement(children: .ignore)
                .accessibilityIdentifier("toast")
                .accessibilityLabel(Text(verbatim: item.text))
            }
        }
        .allowsHitTesting(false)
    }
}

extension ShellEntry {
    static func makeToasts(_ ctx: AppContext) -> any ToastPresenting { ToastCenter(ctx) }
}
