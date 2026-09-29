import Cocoa
import WebKit

// Usage: swift svg2png.swift <in.svg> <out.png> [size]
let args = CommandLine.arguments
guard args.count >= 3 else { fputs("usage: svg2png in.svg out.png [size]\n", stderr); exit(2) }
let inPath = args[1], outPath = args[2]
let size = args.count > 3 ? (Double(args[3]) ?? 512) : 512
let svg = (try? String(contentsOfFile: inPath, encoding: .utf8)) ?? ""

let app = NSApplication.shared
app.setActivationPolicy(.accessory)

final class Snap: NSObject, WKNavigationDelegate {
    let web: WKWebView
    let out: String
    init(size: Double, out: String) {
        let cfg = WKWebViewConfiguration()
        web = WKWebView(frame: NSRect(x: 0, y: 0, width: size, height: size), configuration: cfg)
        web.setValue(false, forKey: "drawsBackground")   // transparent
        self.out = out
        super.init()
        web.navigationDelegate = self
    }
    func webView(_ w: WKWebView, didFinish nav: WKNavigation!) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
            let cfg = WKSnapshotConfiguration()
            cfg.afterScreenUpdates = true
            w.takeSnapshot(with: cfg) { img, err in
                guard let img = img, let tiff = img.tiffRepresentation,
                      let rep = NSBitmapImageRep(data: tiff),
                      let png = rep.representation(using: .png, properties: [:]) else {
                    fputs("snapshot failed: \(String(describing: err))\n", stderr); exit(1)
                }
                try? png.write(to: URL(fileURLWithPath: self.out))
                exit(0)
            }
        }
    }
}
let snap = Snap(size: size, out: outPath)
let html = "<!doctype html><html><head><meta charset='utf-8'><style>*{margin:0;padding:0}html,body{width:\(Int(size))px;height:\(Int(size))px;background:transparent;overflow:hidden}svg{width:\(Int(size))px;height:\(Int(size))px;display:block}</style></head><body>\(svg)</body></html>"
snap.web.loadHTMLString(html, baseURL: nil)
app.run()
