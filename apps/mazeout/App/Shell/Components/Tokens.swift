import SwiftUI

// SHELL S1 (SPEC-architecture §6.11 "Tokens / ShellLayout", §3.4 rule 4). Typed access to the geometry, colours, gradients and
// text styles in Tuning/ui.json (copied there from design/ui-tokens.json; the app never reads design/). Every call site passes
// the compiled default (the measured value), so a missing key never crashes; each miss is recorded (`Tokens.missing`) and
// logged once, and ShellTests require none on the S1 screens. `-pc.tune ui.<key>=v` overrides scalars.
// SKIN (docs/SKIN.md): ui.json's colour slots are "@<ui id>" references into skin/colors.json `ui`; Tuning.load resolves
// them (Tuning/ui-colors.json), so every read here sees "#RRGGBB" strings.

struct Tokens {
    let file: TuningFile

    init(_ file: TuningFile) { self.file = file }
    init(_ ui: UITuning) { self.file = ui.file }

    // MARK: misses

    private static let lock = NSLock()
    nonisolated(unsafe) private static var missed: Set<String> = []

    static var missing: Set<String> { lock.lock(); defer { lock.unlock() }; return missed }

    private func miss(_ key: String) {
        Self.lock.lock()
        let first = Self.missed.insert(key).inserted
        Self.lock.unlock()
        if first { Log.mark("tokens", "ui.json has no \(key): compiled default used") }
    }

    // MARK: geometry

    /// `frames.<id>` = [x, y, w, h] in reference pt.
    func frame(_ id: String, _ d: CGRect) -> CGRect {
        let v = file.doubles("frames." + id, [])
        guard v.count == 4 else { miss("frames." + id); return d }
        return CGRect(x: v[0], y: v[1], width: v[2], height: v[3])
    }

    /// `anchors.<id>` = top | bottom | centre.
    func anchor(_ id: String, _ d: ShellMetrics.Anchor) -> ShellMetrics.Anchor {
        guard let s = file.value("anchors." + id) as? String, let a = ShellMetrics.Anchor(rawValue: s) else {
            miss("anchors." + id); return d
        }
        return a
    }

    /// The frame mapped to the live screen with its anchor.
    func rect(_ id: String, _ d: CGRect, _ anchor: ShellMetrics.Anchor, _ m: ShellMetrics) -> CGRect {
        m.rect(frame(id, d), self.anchor(id, anchor))
    }

    /// `shapes.<id>.n` (superellipse exponent) or `.r` (corner radius).
    func superellipseN(_ id: String, _ d: CGFloat) -> CGFloat {
        guard file.has("shapes.\(id).n") else { miss("shapes.\(id).n"); return d }
        return CGFloat(file.double("shapes.\(id).n", Double(d)))
    }

    func radius(_ id: String, _ d: CGFloat) -> CGFloat {
        guard file.has("shapes.\(id).r") else { miss("shapes.\(id).r"); return d }
        return CGFloat(file.double("shapes.\(id).r", Double(d)))
    }

    func number(_ key: String, _ d: Double) -> Double {
        guard file.has(key) else { miss(key); return d }
        return file.double(key, d)
    }

    // MARK: memo (FIX-2 A, B1b-r0)

    /// Every read below walks the JSON (a key-path split + NSDictionary bridging per level) and re-parses hex strings; views
    /// call them in every body evaluation (B1b's roll flip: ~3 ms of `Tokens.text` in one frame). A tuning file never changes
    /// after load, so each (file, id, compiled default) is resolved once and memoised (`TuningFile.identity` keys the file:
    /// a test's `-pc.tune` overrides load a new file, never a stale value). `memoEnabled = false` = the uncached reads (tests).
    private struct TextKey: Hashable { let file: Int; let id: String; let d: GameTextStyle }
    private struct ColorKey: Hashable { let file: Int; let id: String; let d: UInt32 }
    private struct ColorsKey: Hashable { let file: Int; let id: String; let d: [UInt32] }
    private static let memoLock = NSLock()
    nonisolated(unsafe) private static var textMemo: [TextKey: GameTextStyle] = [:]
    nonisolated(unsafe) private static var colorMemo: [ColorKey: Color] = [:]
    nonisolated(unsafe) private static var colorsMemo: [ColorsKey: [Color]] = [:]
    nonisolated(unsafe) static var memoEnabled = true

    /// Entries memoised so far (tests).
    static var memoCount: Int {
        memoLock.lock(); defer { memoLock.unlock() }
        return textMemo.count + colorMemo.count + colorsMemo.count
    }

    // MARK: colours

    func color(_ id: String, _ d: UInt32) -> Color {
        guard Self.memoEnabled else { return colorUncached(id, d) }
        let key = ColorKey(file: file.identity, id: id, d: d)
        Self.memoLock.lock()
        if let hit = Self.colorMemo[key] { Self.memoLock.unlock(); return hit }
        Self.memoLock.unlock()
        let c = colorUncached(id, d)
        Self.memoLock.lock(); Self.colorMemo[key] = c; Self.memoLock.unlock()
        return c
    }

    func colorUncached(_ id: String, _ d: UInt32) -> Color {
        guard let s = file.value("colors." + id) as? String, let c = Color(hexString: s) else { miss("colors." + id); return Color(hex: d) }
        return c
    }

    /// A list of colours (top → bottom).
    func colors(_ id: String, _ d: [UInt32]) -> [Color] {
        guard Self.memoEnabled else { return colorsUncached(id, d) }
        let key = ColorsKey(file: file.identity, id: id, d: d)
        Self.memoLock.lock()
        if let hit = Self.colorsMemo[key] { Self.memoLock.unlock(); return hit }
        Self.memoLock.unlock()
        let c = colorsUncached(id, d)
        Self.memoLock.lock(); Self.colorsMemo[key] = c; Self.memoLock.unlock()
        return c
    }

    func colorsUncached(_ id: String, _ d: [UInt32]) -> [Color] {
        let list = file.strings("colors." + id, []).compactMap(Color.init(hexString:))
        guard !list.isEmpty else { miss("colors." + id); return d.map { Color(hex: $0) } }
        return list
    }

    /// `colors.<id>` or `gradients.<id>` as [[position, "#hex"], …]; positions > 1 are pt and are normalised by `span`.
    func stops(_ id: String, span: CGFloat = 1, _ d: [(Double, UInt32)]) -> [Gradient.Stop] {
        let raw = (file.value("gradients." + id) ?? file.value("colors." + id)) as? [Any]
        let parsed: [Gradient.Stop] = (raw ?? []).compactMap { item in
            guard let pair = item as? [Any], pair.count == 2, let pos = (pair[0] as? NSNumber)?.doubleValue,
                  let hex = pair[1] as? String, let c = Color(hexString: hex) else { return nil }
            return Gradient.Stop(color: c, location: span > 1 ? pos / Double(span) : pos)
        }
        guard !parsed.isEmpty, parsed.count == raw?.count else {
            miss("gradients/colors." + id)
            return d.map { Gradient.Stop(color: Color(hex: $0.1), location: span > 1 ? $0.0 / Double(span) : $0.0) }
        }
        return parsed
    }

    // MARK: text

    /// `text.<id>` → a GameText style (size, tracking, fill, outline, outlineWidth, drop, dropColor, band, bandDY, minScale).
    /// Memoised per (file, id, default) (FIX-2 A, B1b-r0).
    func text(_ id: String, _ d: GameTextStyle) -> GameTextStyle {
        guard Self.memoEnabled else { return textUncached(id, d) }
        let key = TextKey(file: file.identity, id: id, d: d)
        Self.memoLock.lock()
        if let hit = Self.textMemo[key] { Self.memoLock.unlock(); return hit }
        Self.memoLock.unlock()
        let s = textUncached(id, d)
        Self.memoLock.lock(); Self.textMemo[key] = s; Self.memoLock.unlock()
        return s
    }

    /// The uncached read (the memo's source; TokensTests compares the two).
    func textUncached(_ id: String, _ d: GameTextStyle) -> GameTextStyle {
        guard file.value("text." + id) != nil else { miss("text." + id); return d }
        let k = "text." + id + "."
        var s = d
        s.size = CGFloat(file.double(k + "size", Double(d.size)))
        s.tracking = CGFloat(file.double(k + "tracking", Double(d.tracking)))
        let fill = file.strings(k + "fill", []).compactMap(Color.init(hexString:))
        if !fill.isEmpty { s.fill = fill }
        if let o = file.value(k + "outline") as? String { s.outline = Color(hexString: o) }
        s.outlineWidth = CGFloat(file.double(k + "outlineWidth", s.outline == nil ? 0 : Double(d.outlineWidth)))
        s.drop = CGFloat(file.double(k + "drop", Double(d.drop)))
        if let dc = file.value(k + "dropColor") as? String { s.dropColor = Color(hexString: dc) }
        if let b = file.value(k + "band") as? String { s.band = Color(hexString: b) }
        s.bandDY = CGFloat(file.double(k + "bandDY", Double(d.bandDY)))
        s.minScale = CGFloat(file.double(k + "minScale", Double(d.minScale)))
        if file.string(k + "face", d.face.rawValue) == "blackItalic" { s.face = .blackItalic }
        return s
    }

    /// `text.<id>.maxWidth` (shrink-to-fit width in pt), nil = no fit.
    func textMaxWidth(_ id: String, _ d: CGFloat?) -> CGFloat? {
        file.has("text.\(id).maxWidth") ? CGFloat(file.double("text.\(id).maxWidth", 0)) : d
    }

    /// `text.<id>.baseline` / `.centreX` / `.left` (reference pt).
    func textPoint(_ id: String, baseline: CGFloat, centreX: CGFloat) -> (x: CGFloat, baseline: CGFloat) {
        (CGFloat(file.double("text.\(id).centreX", Double(centreX))), CGFloat(file.double("text.\(id).baseline", Double(baseline))))
    }
}

extension UITuning {
    var tokens: Tokens { Tokens(self) }
    var buttonPressScale: Double { file.double("button.pressScale", 0.95) }       // VERIFIED motion §6.3
    var loadingDotsPeriod: Double { file.double("loading.dotsPeriod", 0.4) }      // PENDING-ui
    // A2 FEEL-P (owner item 2; motion-catalog §11.3 R2, VERIFIED v582 60 Hz): the home tab push-slide, remaining = D·(1 − u)^power,
    // u = t / duration (the retired `transition.homeTabs` 0 was a hard cut). `lead` = the part of a frame the first presented
    // frame is ahead (v582's first moving frame is 34 pt in).
    var tabSlidePower: Double { file.double("transition.tabSlide.power", 2.51) }
    var tabSlideLead: Double { file.double("transition.tabSlide.lead", 0) }
    /// The measured v582 curve itself: the remaining fraction of the distance per 60 Hz frame from the last still frame
    /// (the mean of 5 slides measured with build/p/A2/slide_measure.py: 4 one-page + the 2-page jump, SD 0.2 pt); empty =
    /// the power model. With a table the slide lasts (count − 1) / 60 s.
    var tabSlideTable: [Double] { file.doubles("transition.tabSlide.table", []) }
    var tabSlideDuration: Double {
        let table = tabSlideTable
        return table.count > 1 ? Double(table.count - 1) / 60 : file.double("transition.tabSlide.duration", 0.488)
    }
    var toastIn: Double { file.double("toast.in", 0.08) }
    var toastOut: Double { file.double("toast.out", 0.27) }
    var toastHomeY: Double { file.double("toast.homeY", 390) }
    var toastPanelY: Double { file.double("toast.panelY", 110) }
    var popupUpscale: Bool { file.bool("layout.popupUpscale", false) }
    var settingsShowsLinks: Bool { file.bool("settings.links", true) }
}

extension Color {
    /// "#RRGGBB" or "#RRGGBBAA".
    init?(hexString: String) {
        var s = hexString.trimmingCharacters(in: .whitespaces)
        if s.hasPrefix("#") { s.removeFirst() }
        guard s.count == 6 || s.count == 8, let v = UInt64(s, radix: 16) else { return nil }
        if s.count == 6 {
            self.init(hex: UInt32(v))
        } else {
            self.init(hex: UInt32(v >> 8), Double(v & 0xFF) / 255)
        }
    }
}
