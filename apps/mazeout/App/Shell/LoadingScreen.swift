import SwiftUI

// SHELL S1 (SPEC-architecture §6.3; research/tutorials.md §1 VERIFIED; design/ui-measure.md `loading`, research/kickoff/state.png).
// The cover for the boot sequence and the warm-ups (§5.9, §8.5): full-bleed `loadingBackdrop`, the loading characters
// (Art/char_loading_layout.json places each render so its eyes sit on the original's), our "ARROW OUT!" logo (`logoArrowOut`)
// at `loading.logo`, and "Loading" with cycling dots at `loading.label`. Its only animation is a periodic TimelineView on the
// dots (`loading.dotsPeriod` 0.4 s), cheap enough that the warm-up's frames are not starved. The dots cycle ".", "..", "..."
// (3 states, CONSISTENCY T-16); the word never moves (its left edge is fixed).
// The scene art (backdrop, characters) is placed with an aspect-FILL transform of the 393 x 852 reference (identity on the
// reference phone); the logo and the label use the measured anchors.

struct LoadingScreen: View {
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let t = app.tuning.ui.tokens
        // SPEC-ui C3: the captured #CCCCCC / #681E1A were the colours under the iOS alert's 0.80 dim: the face is white,
        // the outline #82251F
        let style = t.text("loading.label", GameTextStyle(size: 26.8, tracking: -0.5, fill: [Color(hex: 0xFFFFFF)],
                                                          outline: Color(hex: 0x7E2A1C), outlineWidth: 0.88, drop: 0.39))
        let word = GameText("Loading", style: style, maxWidth: 220)
        let label = t.textPoint("loading.label", baseline: 792.7, centreX: 187.2)
        let origin = m.point(CGPoint(x: label.x, y: label.baseline), t.anchor("loading.label", .bottom))
        let left = origin.x - word.layout.advance * m.s / 2
        ZStack(alignment: .topLeading) {
            t.color("loading.base", 0xB7A587)
            if LoadingArt.shared.ready {
                SceneLayer(size: m.size) {
                    ArtImage(art: .loadingBackdrop, contentMode: .fill).frame(width: 393, height: 852)
                    ForEach(LoadingLayout.shared.characters, id: \.file) { c in
                        PathImage(path: "Art/" + c.file).placed(c.frame)
                    }
                }
                ArtImage(art: .logoArrowOut).placed(t.rect("loading.logo", CGRect(20, 66.7, 206.8, 160.1), .top, m))
            }
            ZStack(alignment: .topLeading) {
                word.at(word.layout.advance / 2, style.capCentre(baseline: 0))
                // FIX-2 A (R4-r4 / V3-20): the dots cycle on the RENDER SERVER (three pre-rastered states, discrete opacity keys),
                // so the warm-up's long main-thread frames behind Loading never freeze them (the TimelineView stalled with every
                // slow warm-up frame). Same glyphs, same place, same 0.4 s states.
                LoadingDots(style: style, wordAdvance: word.layout.advance, period: app.tuning.ui.loadingDotsPeriod)
                    .frame(width: 0, height: 0)
            }
            .frame(width: 0, height: 0, alignment: .topLeading)
            .scaleEffect(m.s, anchor: .topLeading)
            .position(x: left, y: origin.y)
            .accessibilityElement(children: .ignore)
            .accessibilityIdentifier("loading.label")
            .accessibilityLabel(Text("Loading"))
        }
        .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
        .clipped()
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen.loading")
    }

    /// ".", "..", "..." cycling every `period` (3 states: ARCH §6.3 / SPEC-ui §2.1 VERIFIED; CONSISTENCY T-16).
    static func dots(at date: Date, period: Double) -> String {
        let n = Int(date.timeIntervalSinceReferenceDate / max(period, 0.05)) % 3 + 1
        return String(repeating: ".", count: n)
    }
}

/// FIX-2 A: ".", "..", "..." — each drawn exactly as `GameText(verbatim:style:)` draws it at the old position (centred on the
/// word's advance + its own half advance, on the cap middle) — shown in turn by a repeating discrete opacity animation.
struct LoadingDots: UIViewRepresentable {
    let style: GameTextStyle
    let wordAdvance: CGFloat
    let period: Double
    @Environment(\.displayScale) private var displayScale

    func makeUIView(context: Context) -> UIView {
        let v = UIView(frame: .zero)
        v.clipsToBounds = false
        v.isUserInteractionEnabled = false
        let scale = max(displayScale, 1)
        let cycle = 3 * max(0.05, period)
        let now = CACurrentMediaTime()
        // the state at this instant, as the wall-clock formula chose it (the cycle stays in phase with `dots(at:period:)`)
        let phase = Date().timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: cycle)
        for n in 1...3 {
            let text = String(repeating: ".", count: n)
            let l = GameTextLayout.make(text, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking,
                                        maxWidth: nil, minScale: style.minScale)
            let st = l.fontSize == style.size ? style : style.sized(l.fontSize)
            let g = GameText.rasterGeometry(l, style: st, capStyle: style)
            let layer = CALayer()
            layer.contents = GameTextRaster.image(l, style: st, size: g.size, origin: g.origin, scale: scale)
            layer.contentsScale = scale
            let centre = CGPoint(x: wordAdvance + l.advance / 2, y: style.capCentre(baseline: 0))
            layer.frame = CGRect(x: centre.x - g.size.width / 2, y: centre.y - g.size.height / 2, width: g.size.width,
                                 height: g.size.height)
            layer.opacity = 0
            let a = CAKeyframeAnimation(keyPath: "opacity")
            a.values = (1...3).map { $0 == n ? 1 : 0 }
            a.keyTimes = [0, NSNumber(value: 1.0 / 3), NSNumber(value: 2.0 / 3), 1]
            a.calculationMode = .discrete
            a.duration = cycle
            a.repeatCount = .greatestFiniteMagnitude
            a.beginTime = now - phase
            a.isRemovedOnCompletion = false
            layer.add(a, forKey: "dots")
            v.layer.addSublayer(layer)
        }
        return v
    }

    func updateUIView(_ uiView: UIView, context: Context) {}
}

/// The Loading art decoded OFF the main thread from the moment the router exists (AppModel.init), so the Loading screen's
/// first frame is cheap (the launch colour is already the screen's base colour); the art appears as soon as it is decoded.
@MainActor @Observable final class LoadingArt {
    static let shared = LoadingArt()
    private(set) var ready = false
    @ObservationIgnored private var started = false

    /// Every bundle path the Loading screen draws.
    static var paths: [String] {
        [UIArt.loadingBackdrop.path, UIArt.logoArrowOut.path] + LoadingLayout.shared.characters.map { "Art/" + $0.file }
    }

    /// FIX-2 A (V3-09): Loading shows once per launch; once its layer is gone its decoded art (the full-bleed backdrop alone is
    /// ~12 MB) is released instead of staying resident for the whole session (V3: LoadingScreen's art never released).
    func release() {
        let bytes = ArtStore.purge(paths: Self.paths)
        Log.mark("warmup", String(format: "loading art released (%.1f MB)", Double(bytes) / 1_048_576))
    }

    func start() {
        guard !started else { return }
        started = true
        let t0 = ProcessInfo.processInfo.systemUptime
        Task.detached(priority: .userInitiated) {
            let paths = await LoadingArt.paths
            var found = 0
            for p in paths where ArtStore.image(path: p) != nil { found += 1 }
            let n = found
            await MainActor.run {
                LoadingArt.shared.ready = true
                Log.mark("warmup", "loading art \(n)/\(paths.count) decoded \(String(format: "%.3f", ProcessInfo.processInfo.systemUptime - t0)) s")
            }
        }
    }
}

/// The loading characters' placement (Art/char_loading_layout.json: frame top-left in reference pt, z back → front).
struct LoadingLayout {
    struct Character { let file: String; let frame: CGRect; let z: Int }
    let characters: [Character]

    static let shared = LoadingLayout.load()

    static func load(bundle: Bundle = .main) -> LoadingLayout {
        guard let url = bundle.resourceURL?.appendingPathComponent("Art/char_loading_layout.json"),
              let data = try? Data(contentsOf: url),
              let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let chars = root["characters"] as? [String: [String: Any]] else {
            Log.mark("loading", "Art/char_loading_layout.json missing: no loading characters")
            return LoadingLayout(characters: [])
        }
        let list: [Character] = chars.values.compactMap { c in
            guard let file = c["file"] as? String, let f = c["frame_pt"] as? [Double], f.count == 2,
                  let x = (c["x"] as? NSNumber)?.doubleValue, let y = (c["y"] as? NSNumber)?.doubleValue else { return nil }
            return Character(file: file, frame: CGRect(x, y, f[0], f[1]), z: (c["z"] as? Int) ?? 0)
        }
        return LoadingLayout(characters: list.sorted { $0.z < $1.z })
    }
}

/// Full-bleed scene art authored on the 393 x 852 reference: scaled to FILL the screen, centred (identity on the reference).
struct SceneLayer<Content: View>: View {
    let size: CGSize
    @ViewBuilder var content: Content

    var body: some View {
        let k = max(size.width / 393, size.height / 852)
        ZStack(alignment: .topLeading) { content }
            .frame(width: 393, height: 852, alignment: .topLeading)
            .scaleEffect(k, anchor: .center)
            .frame(width: size.width, height: size.height)
            .clipped()
            .allowsHitTesting(false)
    }
}
