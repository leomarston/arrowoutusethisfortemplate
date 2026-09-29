// swiftui_render: render the SwiftUI chrome views (art/ui/code/*.swift) to @3x PNGs with ImageRenderer (macOS 14+).
//   swiftc -O -parse-as-library -o build/ui-art/swiftuirender art/ui/code/GlossyChrome.swift art/ui/tools/swiftui_render.swift
//   build/ui-art/swiftuirender OUTDIR            -> OUTDIR/<case>.png (exact frame x 3, transparent)
import SwiftUI
import AppKit
import UniformTypeIdentifiers

@main
struct Main {
    @MainActor
    static func main() {
        let out = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "."
        try? FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)
        let cases: [(String, AnyView)] = [
            ("pauseButton", AnyView(BlueSquareButton { PauseGlyph() })),
            ("heartHUD", AnyView(HeartHUD())),
            ("buttonGreen", AnyView(PanelButton(colors: .green))),
            ("buttonRed", AnyView(PanelButton(colors: .red))),
            ("buttonGreen_labelled", AnyView(PanelButton(colors: .green, label: "Resume"))),
        ]
        for (name, view) in cases {
            let r = ImageRenderer(content: view)
            r.scale = 3
            r.isOpaque = false
            guard let cg = r.cgImage else { print("FAIL \(name)"); continue }
            let url = URL(fileURLWithPath: out).appendingPathComponent("\(name).png")
            guard let dst = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil) else { continue }
            CGImageDestinationAddImage(dst, cg, nil)
            CGImageDestinationFinalize(dst)
            print("ok \(name) \(cg.width)x\(cg.height)")
        }
    }
}
