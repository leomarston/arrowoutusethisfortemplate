// svgr: rasterise SVG files with WebKit (transparent background), several per process.
//   svgr job.json      where job.json = [{"svg": "/abs/in.svg", "out": "/abs/out.png", "w": 393, "h": 852}, ...]
// The page is laid out at w x h CSS px; the snapshot comes back at the screen's backing scale (usually 2x), and
// art/ui/tools/svg.py resizes it to the exact target size (so every SVG is supersampled).
import Cocoa
import WebKit

struct Entry: Decodable { let svg: String; let out: String; let w: Double; let h: Double }

let args = CommandLine.arguments
guard args.count >= 2, let data = FileManager.default.contents(atPath: args[1]),
      let jobs = try? JSONDecoder().decode([Entry].self, from: data) else {
    fputs("usage: svgr job.json\n", stderr); exit(2)
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)

final class Runner: NSObject, WKNavigationDelegate {
    var queue: [Entry]
    var web: WKWebView?
    var current: Entry?
    init(_ q: [Entry]) { queue = q }

    func next() {
        guard !queue.isEmpty else { exit(0) }
        let e = queue.removeFirst()
        current = e
        let svg = (try? String(contentsOfFile: e.svg, encoding: .utf8)) ?? ""
        let cfg = WKWebViewConfiguration()
        let w = WKWebView(frame: NSRect(x: 0, y: 0, width: e.w, height: e.h), configuration: cfg)
        w.setValue(false, forKey: "drawsBackground")
        w.navigationDelegate = self
        web = w
        let W = Int(e.w), H = Int(e.h)
        let html = "<!doctype html><html><head><meta charset='utf-8'><style>*{margin:0;padding:0}html,body{width:\(W)px;height:\(H)px;background:transparent;overflow:hidden}svg{width:\(W)px;height:\(H)px;display:block}</style></head><body>\(svg)</body></html>"
        w.loadHTMLString(html, baseURL: URL(fileURLWithPath: (e.svg as NSString).deletingLastPathComponent + "/"))
    }

    func webView(_ w: WKWebView, didFinish nav: WKNavigation!) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
            let cfg = WKSnapshotConfiguration()
            cfg.afterScreenUpdates = true
            w.takeSnapshot(with: cfg) { img, err in
                guard let e = self.current, let img = img, let tiff = img.tiffRepresentation,
                      let rep = NSBitmapImageRep(data: tiff),
                      let png = rep.representation(using: .png, properties: [:]) else {
                    fputs("snapshot failed: \(String(describing: err))\n", stderr); exit(1)
                }
                try? png.write(to: URL(fileURLWithPath: e.out))
                print("ok \(e.out)")
                self.next()
            }
        }
    }
}

let runner = Runner(jobs)
runner.next()
app.run()
