import SwiftUI
import AppKit
import UniformTypeIdentifiers

func R(_ k: String) -> CGRect {
    let a = (Tokens().value("frames.pause." + k) as? [NSNumber])?.map { CGFloat($0.doubleValue) } ?? [0, 0, 10, 10]
    return CGRect(x: a[0], y: a[1], width: a[2], height: a[3])
}

extension View {
    func at(_ r: CGRect) -> some View { self.frame(width: r.width, height: r.height).offset(x: r.minX, y: r.minY) }
}

@MainActor func save(_ v: some View, _ path: String) {
    let r = ImageRenderer(content: v.frame(width: 393, height: 852, alignment: .topLeading))
    r.scale = 3
    r.isOpaque = false
    guard let cg = r.cgImage else { print("FAIL", path); return }
    let url = URL(fileURLWithPath: path)
    let dst = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dst, cg, nil)
    CGImageDestinationFinalize(dst)
    print("ok", path, cg.width, cg.height)
}

@main
struct Main {
    @MainActor static func main() {
        let out = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "."
        let t = Tokens()
        let shell = ZStack(alignment: .topLeading) {
            PopupPanelFrame(t: t).at(R("panel"))
            PopupCard(t: t).at(R("card"))
            ChromeButtonFace(colors: .green).at(R("resume"))
            ChromeButtonFace(colors: .red).at(R("quit"))
            PopupRibbon(t: t).at(R("ribbon"))
            PopupCloseButton(id: "x", t: t, action: {}).at(R("close"))
        }
        save(shell, out + "/pause_shell.png")
        let polish = ZStack(alignment: .topLeading) {
            PolishPanelFrame(t: t).at(R("panel"))
            PopupCard(t: t).at(R("card"))
            PolishButtonFace(colors: .green).at(R("resume"))
            PolishButtonFace(colors: .red).at(R("quit"))
            PolishRibbon(t: t).at(R("ribbon"))
            PolishCloseButton(t: t).at(R("close"))
        }
        save(polish, out + "/pause_polish.png")
    }
}
