// Scratch stubs so the shell's PopupChrome structs (copied read-only into chrome_shell.swift) render on macOS.
import SwiftUI
import Foundation

struct Tokens {
    static var json: [String: Any] = {
        let p = "/Users/yago/Downloads/app-factory/apps/mazeout/App/Resources/Tuning/ui.json"
        guard let d = FileManager.default.contents(atPath: p), let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return [:] }
        return o
    }()
    func value(_ path: String) -> Any? {
        var cur: Any? = Tokens.json
        for k in path.split(separator: ".") { cur = (cur as? [String: Any])?[String(k)] }
        return cur
    }
    func strings(_ path: String) -> [String] {
        switch value(path) {
        case let a as [Any]: let s = a.compactMap { $0 as? String }; return s.count == a.count ? s : []
        case let s as String: return s.split(separator: ";").map(String.init)
        default: return []
        }
    }
    func color(_ id: String, _ d: UInt32) -> Color {
        if let s = value("colors." + id) as? String, let c = Color(hexString: s) { return c }
        return Color(hex: d)
    }
    func colors(_ id: String, _ d: [UInt32]) -> [Color] {
        let l = strings("colors." + id).compactMap(Color.init(hexString:))
        return l.isEmpty ? d.map { Color(hex: $0) } : l
    }
    func number(_ k: String, _ d: Double) -> Double { (value(k) as? NSNumber)?.doubleValue ?? d }
}

extension Color {
    init?(hexString: String) {
        var s = hexString.trimmingCharacters(in: .whitespaces)
        if s.hasPrefix("#") { s.removeFirst() }
        guard s.count == 6 || s.count == 8, let v = UInt64(s, radix: 16) else { return nil }
        if s.count == 6 { self.init(hex: UInt32(v)) } else { self.init(hex: UInt32(v >> 8), Double(v & 0xFF) / 255) }
    }
}

struct Rasterized<Content: View>: View {
    let key: String
    let overflow: CGFloat
    @ViewBuilder var content: (CGSize) -> Content
    init(_ key: String, overflow: CGFloat = 0, @ViewBuilder content: @escaping (CGSize) -> Content) {
        self.key = key; self.overflow = overflow; self.content = content
    }
    var body: some View { GeometryReader { geo in content(geo.size).frame(width: geo.size.width, height: geo.size.height) } }
}

struct GameButton<Content: View>: View {
    let id: String
    var label: String?
    let action: () -> Void
    @ViewBuilder var content: Content
    init(id: String, label: String? = nil, action: @escaping () -> Void, @ViewBuilder content: () -> Content) {
        self.id = id; self.label = label; self.action = action; self.content = content()
    }
    var body: some View { content }
}

extension PanelButtonStyleColors {
    var rasterID: String { String(format: "%06X-%06X", outline, face.first?.0 ?? 0) }
}
