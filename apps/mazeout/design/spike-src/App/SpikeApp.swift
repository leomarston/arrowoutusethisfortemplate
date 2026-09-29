import SwiftUI
import UIKit

@main
struct SpikeApp: App {
    init() { _ = Bench.appInit }
    var body: some Scene {
        WindowGroup {
            BoardHost()
                .ignoresSafeArea()
                .statusBarHidden(false)
        }
    }
}

/// UIKit board hosted in SwiftUI (the shell stays SwiftUI; the board is one UIView subtree).
struct BoardHost: UIViewRepresentable {
    func makeUIView(context: Context) -> HostView { HostView(level: LevelLoader.load()) }
    func updateUIView(_ uiView: HostView, context: Context) {}
}

final class HostView: UIView {
    let board: BoardView
    let label = UILabel()
    var bench: Bench?

    init(level: LevelSpec) {
        board = BoardView(level: level)
        super.init(frame: .zero)
        backgroundColor = .white
        addSubview(board)
        label.font = .monospacedSystemFont(ofSize: 13, weight: .semibold)
        label.textColor = UIColor(white: 0.25, alpha: 1)
        label.textAlignment = .center
        label.accessibilityIdentifier = "hud"
        addSubview(label)
        board.onChange = { [weak self] in self?.refresh() }
        board.onReady = { [weak self] in
            guard let self else { return }
            self.refresh()
            let b = Bench(board: self.board)
            b.onRefresh = { [weak self] in self?.refresh() }
            self.bench = b
            DispatchQueue.main.async { b.run() }
        }
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }

    override func layoutSubviews() {
        super.layoutSubviews()
        board.frame = bounds
        label.frame = CGRect(x: 0, y: 70, width: bounds.width, height: 20)
        label.adjustsFontSizeToFitWidth = true
    }

    func refresh() {
        guard let s = board.state else { return }
        var t = "L\(board.level.id)  hearts \(board.hearts)  arrows \(s.aliveCount)/\(board.level.arrows.count)"
        if UserDefaults.standard.bool(forKey: "pc.uitest") {
            t += String(format: " zoom %.2f", board.zoom)
            if let p = board.freeArrowWindowPoint() { t += String(format: " free %.1f,%.1f", p.x, p.y) }
        }
        label.text = t
    }
}

enum LevelLoader {
    static func load() -> LevelSpec {
        let t = Tunables.shared
        if t.level == "synth" {
            let l = Generator.synthetic(cols: 40, rows: 40, seed: t.seed, meanLength: t.synthMean)
            if let d = try? JSONEncoder().encode(l) {
                try? d.write(to: URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("synthetic.json"))
            }
            return l
        }
        let tmp = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(t.level + ".json")
        let url: URL? = FileManager.default.fileExists(atPath: tmp.path) ? tmp : Bundle.main.url(forResource: t.level, withExtension: "json")
        guard let url, let data = try? Data(contentsOf: url), let l = try? JSONDecoder().decode(LevelSpec.self, from: data) else {
            fatalError("level \(t.level) missing or malformed")
        }
        return l
    }
}
